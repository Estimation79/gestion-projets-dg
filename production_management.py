import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import json
import uuid
from typing import Dict, List, Optional, Any
import logging

# Import pour export PDF des Bons de Travail
try:
    from bt_pdf_export import export_bt_pdf_streamlit
    PDF_EXPORT_AVAILABLE = True
except ImportError:
    PDF_EXPORT_AVAILABLE = False
    logging.warning("Module bt_pdf_export non disponible. Export PDF désactivé.")

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _synchroniser_bt_operations(bt_id: int, db):
    """
    Synchronise les lignes d'un Bon de Travail avec la table 'operations'.
    VERSION CORRIGÉE : Adaptation à la structure réelle de la base de données
    """
    try:
        # Récupérer les informations du BT depuis la table formulaires
        bt_result = db.execute_query('''
            SELECT f.*, p.id as project_id_found
            FROM formulaires f
            LEFT JOIN projects p ON f.project_id = p.id
            WHERE f.id = ? AND f.type_formulaire = 'BON_TRAVAIL'
        ''', (bt_id,))
        
        if not bt_result:
            logger.warning(f"BT #{bt_id} non trouvé pour synchronisation")
            return
        
        bt_data = dict(bt_result[0])
        project_id = bt_data.get('project_id')
        
        if not project_id:
            logger.warning(f"Le BT #{bt_id} n'est pas lié à un projet. Impossible de créer des opérations.")
            return

        # Récupérer les tâches (lignes avec sequence_ligne < 1000)
        tasks_result = db.execute_query('''
            SELECT * FROM formulaire_lignes 
            WHERE formulaire_id = ? AND sequence_ligne < 1000
            ORDER BY sequence_ligne
        ''', (bt_id,))
        
        if not tasks_result:
            logger.info(f"Aucune tâche trouvée pour le BT #{bt_id}")
            return

        # Supprimer les anciennes opérations liées à ce BT pour éviter les doublons
        db.execute_query("DELETE FROM operations WHERE formulaire_bt_id = ?", (bt_id,))
        logger.info(f"Anciennes opérations pour BT #{bt_id} purgées avant synchronisation.")
        
        operations_creees = 0
        
        for task in tasks_result:
            task_data = dict(task)
            
            # Récupérer les données de la tâche depuis le JSON stocké dans notes_ligne
            task_details = {}
            try:
                task_details = json.loads(task_data.get('notes_ligne', '{}'))
            except json.JSONDecodeError:
                pass

            operation_name = task_details.get('operation')
            if not operation_name:
                continue # Ignorer les lignes sans poste/opération défini

            # Chercher le work_center_id correspondant au nom de l'opération
            wc_result = db.execute_query('''
                SELECT id FROM work_centers WHERE nom = ? LIMIT 1
            ''', (operation_name,))
            
            work_center_id = wc_result[0]['id'] if wc_result else None
            
            if not work_center_id:
                logger.warning(f"Poste de travail '{operation_name}' non trouvé pour synchronisation")
                continue

            # CORRECTION: Adapter aux colonnes réelles de votre base
            # Insérer la nouvelle opération avec les colonnes qui existent
            op_id = db.execute_insert('''
                INSERT INTO operations 
                (project_id, work_center_id, formulaire_bt_id, sequence_number, 
                 description, temps_estime, ressource, statut, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id,
                work_center_id,
                bt_id,
                task_data.get('sequence_ligne', 1),
                f"{operation_name} - {task_details.get('description', '')}",
                task_data.get('prix_unitaire', 0.0),  # Heures prévues
                task_details.get('assigned_to', ''),
                _convertir_statut_bt_vers_operation(task_details.get('status', 'pending')),
                json.dumps({
                    'operation_source': operation_name,
                    'bt_task_description': task_details.get('description', ''),
                    'fournisseur': task_details.get('fournisseur', '-- Interne --'),
                    'date_debut_prevue': task_details.get('start_date', ''),
                    'date_fin_prevue': task_details.get('end_date', '')
                })
            ))
            
            if op_id:
                operations_creees += 1
        
        if operations_creees > 0:
            logger.info(f"✅ {operations_creees} opération(s) synchronisée(s) pour le BT #{bt_id}.")
            st.toast(f"🔄 {operations_creees} opération(s) synchronisée(s) pour le Kanban.", icon="✅")

    except Exception as e:
        logger.error(f"Erreur critique lors de la synchronisation des opérations du BT #{bt_id}: {e}")
        st.error(f"Erreur de synchronisation Kanban: {e}")

def _convertir_statut_bt_vers_operation(statut_bt: str) -> str:
    """Convertit un statut de tâche BT vers un statut d'opération"""
    conversion = {
        'pending': 'À FAIRE',
        'in-progress': 'EN COURS',
        'completed': 'TERMINÉ',
        'on-hold': 'EN PAUSE'
    }
    return conversion.get(statut_bt, 'À FAIRE')

class GestionnaireBonsTravail:
    """
    Gestionnaire principal pour les Bons de Travail
    Reproduit les fonctionnalités du fichier HTML en version Streamlit
    VERSION CORRIGÉE pour résoudre les problèmes de rechargement
    VERSION FINALE avec support complet de modification
    NOUVELLE VERSION avec support fournisseurs/sous-traitants
    VERSION PDF avec export professionnel
    VERSION SUPPRESSION avec suppression sécurisée complète
    VERSION KANBAN avec synchronisation automatique
    """
    
    def __init__(self, db):
        self.db = db
        self.init_session_state()
    
    def init_session_state(self):
        """Initialise les variables de session pour les BT"""
        if 'bt_current_form_data' not in st.session_state:
            st.session_state.bt_current_form_data = self.get_empty_bt_form()
        
        if 'bt_task_counter' not in st.session_state:
            st.session_state.bt_task_counter = 1
            
        if 'bt_material_counter' not in st.session_state:
            st.session_state.bt_material_counter = 1
            
        if 'bt_mode' not in st.session_state:
            st.session_state.bt_mode = 'create'  # 'create', 'edit', 'view'
            
        if 'bt_selected_id' not in st.session_state:
            st.session_state.bt_selected_id = None
            
        if 'bt_show_success' not in st.session_state:
            st.session_state.bt_show_success = False
        
        # Variables pour la suppression
        if 'bt_confirm_delete' not in st.session_state:
            st.session_state.bt_confirm_delete = None
        
        if 'bt_delete_confirmed' not in st.session_state:
            st.session_state.bt_delete_confirmed = False

    def get_empty_bt_form(self) -> Dict:
        """Retourne un formulaire BT vide - MODIFIÉ pour supporter l'auto-sélection"""
        today = datetime.now().strftime('%Y-%m-%d')
        return {
            'numero_document': self.generate_bt_number(),
            'project_id': '',  # AJOUT : ID du projet sélectionné
            'project_name': '',
            'client_name': '',
            'client_company_id': None,  # AJOUT : ID de l'entreprise cliente
            'project_manager': '',
            'priority': 'NORMAL',
            'start_date': today,
            'end_date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
            'work_instructions': '',
            'safety_notes': '',
            'quality_requirements': '',
            'tasks': [self.get_empty_task()],
            'materials': [self.get_empty_material()],
            'created_by': 'Utilisateur'
        }
    
    def get_empty_task(self) -> Dict:
        """Retourne une tâche vide - MODIFIÉ pour inclure fournisseur"""
        return {
            'operation': '',
            'description': '',
            'quantity': 1,  # int pour cohérence avec st.number_input
            'planned_hours': 0.0,  # float pour heures
            'actual_hours': 0.0,   # float pour heures
            'assigned_to': '',
            'fournisseur': '-- Interne --',  # NOUVEAU : Fournisseur/Sous-traitant
            'status': 'pending',
            'start_date': '',
            'end_date': ''
        }
    
    def get_empty_material(self) -> Dict:
        """Retourne un matériau vide - MODIFIÉ pour inclure fournisseur"""
        return {
            'name': '',
            'description': '',
            'quantity': 1.0,  # float pour cohérence avec st.number_input et step=0.1
            'unit': 'pcs',
            'fournisseur': '-- Interne --',  # NOUVEAU : Fournisseur/Sous-traitant
            'available': 'yes',
            'notes': ''
        }
    
    def get_fournisseurs_actifs(self) -> List[str]:
        """Récupère la liste des fournisseurs actifs depuis la base de données"""
        try:
            query = '''
                SELECT c.nom as company_name, f.code_fournisseur
                FROM companies c
                JOIN fournisseurs f ON c.id = f.company_id
                WHERE f.est_actif = TRUE
                ORDER BY c.nom
            '''
            results = self.db.execute_query(query)
            
            fournisseurs = []
            for row in results:
                name = row['company_name']
                if row['code_fournisseur']:
                    name += f" ({row['code_fournisseur']})"
                fournisseurs.append(name)
            
            return fournisseurs
            
        except Exception as e:
            logger.error(f"Erreur récupération fournisseurs: {e}")
            # Fallback avec quelques fournisseurs par défaut
            return [
                'Metallurgie Québec Inc.',
                'Soudage Spécialisé Ltée',
                'Traitement Thermique DG',
                'Usinage Précision Plus',
                'Peinture Industrielle QC'
            ]
    
    def generate_bt_number(self) -> str:
        """Génère un numéro de BT automatique"""
        try:
            year = datetime.now().year
            
            # Compter les BT existants pour cette année
            count_result = self.db.execute_query(
                "SELECT COUNT(*) as count FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL' AND numero_document LIKE ?",
                (f"BT-{year}-%",)
            )
            
            if count_result:
                count = count_result[0]['count'] + 1
            else:
                count = 1
            
            return f"BT-{year}-{count:03d}"
            
        except Exception as e:
            logger.error(f"Erreur génération numéro BT: {e}")
            return f"BT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def save_bon_travail(self, form_data: Dict) -> Optional[int]:
        """
        Sauvegarde un bon de travail dans la base
        VERSION CORRIGÉE : Conditions de sauvegarde améliorées
        MODIFIÉ : Support des fournisseurs dans les tâches et matériaux
        VERSION KANBAN : Synchronisation automatique avec table operations
        """
        try:
            # Créer le formulaire principal
            formulaire_data = {
                'type_formulaire': 'BON_TRAVAIL',
                'numero_document': form_data['numero_document'],
                'project_id': form_data.get('project_id'),  # AJOUT : Lien vers projet
                'company_id': form_data.get('client_company_id'),  # AJOUT : Lien vers entreprise
                'statut': 'BROUILLON',
                'priorite': form_data['priority'],
                'date_echeance': form_data['end_date'],
                'notes': form_data.get('work_instructions', ''),
                'metadonnees_json': json.dumps({
                    'project_id': form_data.get('project_id', ''),
                    'project_name': form_data['project_name'],
                    'client_name': form_data['client_name'],
                    'client_company_id': form_data.get('client_company_id'),
                    'project_manager': form_data['project_manager'],
                    'start_date': form_data['start_date'],
                    'safety_notes': form_data.get('safety_notes', ''),
                    'quality_requirements': form_data.get('quality_requirements', ''),
                    'created_by': form_data.get('created_by', 'Utilisateur')
                })
            }
            
            # Insérer le formulaire
            bt_id = self.db.execute_insert('''
                INSERT INTO formulaires 
                (type_formulaire, numero_document, project_id, company_id, statut, priorite, date_echeance, notes, metadonnees_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                formulaire_data['type_formulaire'],
                formulaire_data['numero_document'],
                formulaire_data['project_id'],
                formulaire_data['company_id'],
                formulaire_data['statut'],
                formulaire_data['priorite'],
                formulaire_data['date_echeance'],
                formulaire_data['notes'],
                formulaire_data['metadonnees_json']
            ))
            
            if not bt_id:
                return None
            
            # CORRECTION: Sauvegarder les tâches avec condition améliorée + fournisseur
            for i, task in enumerate(form_data.get('tasks', []), 1):
                # CORRECTION: Au moins l'opération OU la description doit être remplie
                if task.get('operation') or task.get('description'):
                    # CORRECTION: Gérer les cas où operation ou description est vide
                    operation = task.get('operation', '').strip()
                    description = task.get('description', '').strip()
                    
                    # Format de description amélioré
                    if operation and description:
                        full_description = f"{operation} - {description}"
                    elif operation:
                        full_description = f"{operation}"
                    elif description:
                        full_description = f"TÂCHE - {description}"
                    else:
                        continue  # Ignorer les tâches complètement vides
                    
                    self.db.execute_insert('''
                        INSERT INTO formulaire_lignes 
                        (formulaire_id, sequence_ligne, description, quantite, prix_unitaire, notes_ligne)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        bt_id, i, 
                        full_description,  # Description formatée
                        task['quantity'], 
                        task['planned_hours'],  # Utiliser planned_hours comme "prix"
                        json.dumps({
                            'operation': operation,  # CORRECTION: Stocker explicitement
                            'description': description,  # CORRECTION: Stocker explicitement
                            'actual_hours': task['actual_hours'],
                            'assigned_to': task['assigned_to'],
                            'fournisseur': task.get('fournisseur', '-- Interne --'),  # NOUVEAU
                            'status': task['status'],
                            'start_date': task.get('start_date', ''),
                            'end_date': task.get('end_date', '')
                        })
                    ))
            
            # Sauvegarder les matériaux comme lignes spéciales + fournisseur
            for i, material in enumerate(form_data.get('materials', []), 1000):  # Commencer à 1000 pour différencier
                if material['name']:  # Seulement si le matériau a un nom
                    self.db.execute_insert('''
                        INSERT INTO formulaire_lignes 
                        (formulaire_id, sequence_ligne, description, quantite, unite, notes_ligne)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        bt_id, i, 
                        f"MATERIAU: {material['name']} - {material['description']}", 
                        material['quantity'], 
                        material['unit'],
                        json.dumps({
                            'type': 'material',
                            'fournisseur': material.get('fournisseur', '-- Interne --'),  # NOUVEAU
                            'available': material['available'],
                            'notes': material.get('notes', '')
                        })
                    ))
            
            # Enregistrer l'action dans l'historique
            self.db.execute_insert('''
                INSERT INTO formulaire_validations
                (formulaire_id, type_validation, commentaires)
                VALUES (?, 'CREATION', ?)
            ''', (bt_id, f"Bon de Travail créé par {form_data.get('created_by', 'Utilisateur')}"))
            
            logger.info(f"Bon de Travail {formulaire_data['numero_document']} sauvegardé avec ID {bt_id}")

            # NOUVEAU : Synchronisation automatique avec le Kanban
            _synchroniser_bt_operations(bt_id, self.db)

            return bt_id
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde BT: {e}")
            return None
    
    def update_bon_travail(self, bt_id: int, form_data: Dict) -> bool:
        """
        Met à jour un bon de travail existant dans la base
        NOUVELLE FONCTION : Gestion des modifications BT
        MODIFIÉ : Support des fournisseurs
        VERSION KANBAN : Synchronisation automatique avec table operations
        """
        try:
            # Mettre à jour le formulaire principal
            update_result = self.db.execute_query('''
                UPDATE formulaires 
                SET numero_document = ?,
                    project_id = ?,
                    company_id = ?,
                    priorite = ?,
                    date_echeance = ?,
                    notes = ?,
                    metadonnees_json = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND type_formulaire = 'BON_TRAVAIL'
            ''', (
                form_data['numero_document'],
                form_data.get('project_id'),
                form_data.get('client_company_id'),
                form_data['priority'],
                form_data['end_date'],
                form_data.get('work_instructions', ''),
                json.dumps({
                    'project_id': form_data.get('project_id', ''),
                    'project_name': form_data['project_name'],
                    'client_name': form_data['client_name'],
                    'client_company_id': form_data.get('client_company_id'),
                    'project_manager': form_data['project_manager'],
                    'start_date': form_data['start_date'],
                    'safety_notes': form_data.get('safety_notes', ''),
                    'quality_requirements': form_data.get('quality_requirements', ''),
                    'created_by': form_data.get('created_by', 'Utilisateur')
                }),
                bt_id
            ))
            
            # Supprimer toutes les anciennes lignes
            self.db.execute_query('''
                DELETE FROM formulaire_lignes WHERE formulaire_id = ?
            ''', (bt_id,))
            
            # Réinsérer les tâches mises à jour avec fournisseur
            for i, task in enumerate(form_data.get('tasks', []), 1):
                # Seulement si l'opération OU la description est remplie
                if task.get('operation') or task.get('description'):
                    operation = task.get('operation', '').strip()
                    description = task.get('description', '').strip()
                    
                    # Format de description amélioré
                    if operation and description:
                        full_description = f"{operation} - {description}"
                    elif operation:
                        full_description = f"{operation}"
                    elif description:
                        full_description = f"TÂCHE - {description}"
                    else:
                        continue
                    
                    self.db.execute_insert('''
                        INSERT INTO formulaire_lignes 
                        (formulaire_id, sequence_ligne, description, quantite, prix_unitaire, notes_ligne)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        bt_id, i, 
                        full_description,
                        task['quantity'], 
                        task['planned_hours'],
                        json.dumps({
                            'operation': operation,
                            'description': description,
                            'actual_hours': task['actual_hours'],
                            'assigned_to': task['assigned_to'],
                            'fournisseur': task.get('fournisseur', '-- Interne --'),  # NOUVEAU
                            'status': task['status'],
                            'start_date': task.get('start_date', ''),
                            'end_date': task.get('end_date', '')
                        })
                    ))
            
            # Réinsérer les matériaux mis à jour avec fournisseur
            for i, material in enumerate(form_data.get('materials', []), 1000):
                if material['name']:
                    self.db.execute_insert('''
                        INSERT INTO formulaire_lignes 
                        (formulaire_id, sequence_ligne, description, quantite, unite, notes_ligne)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        bt_id, i, 
                        f"MATERIAU: {material['name']} - {material['description']}", 
                        material['quantity'], 
                        material['unit'],
                        json.dumps({
                            'type': 'material',
                            'fournisseur': material.get('fournisseur', '-- Interne --'),  # NOUVEAU
                            'available': material['available'],
                            'notes': material.get('notes', '')
                        })
                    ))
            
            # Enregistrer l'action dans l'historique
            self.db.execute_insert('''
                INSERT INTO formulaire_validations
                (formulaire_id, type_validation, commentaires)
                VALUES (?, 'MODIFICATION', ?)
            ''', (bt_id, f"Bon de Travail modifié par {form_data.get('created_by', 'Utilisateur')}"))
            
            logger.info(f"Bon de Travail {form_data['numero_document']} (ID: {bt_id}) mis à jour avec succès")

            # NOUVEAU : Synchronisation automatique avec le Kanban
            _synchroniser_bt_operations(bt_id, self.db)

            return True
            
        except Exception as e:
            logger.error(f"Erreur mise à jour BT {bt_id}: {e}")
            return False
    
    def delete_bon_travail(self, bt_id: int) -> bool:
        """
        Supprime complètement un bon de travail et toutes ses données associées
        NOUVELLE FONCTION : Suppression sécurisée avec nettoyage complet
        VERSION KANBAN : Suppression des opérations synchronisées
        """
        try:
            # Vérifier que le BT existe
            bt_data = self.load_bon_travail(bt_id)
            if not bt_data:
                logger.error(f"BT {bt_id} non trouvé pour suppression")
                return False
            
            # Commencer une transaction pour assurer la cohérence
            # Note: SQLite supporte les transactions implicites
            
            # 1. Supprimer les validations/historique
            self.db.execute_query('''
                DELETE FROM formulaire_validations 
                WHERE formulaire_id = ?
            ''', (bt_id,))
            
            # 2. Supprimer les lignes (tâches et matériaux)
            self.db.execute_query('''
                DELETE FROM formulaire_lignes 
                WHERE formulaire_id = ?
            ''', (bt_id,))
            
            # 3. Supprimer les entrées TimeTracker associées (si existantes)
            self.db.execute_query('''
                DELETE FROM time_entries 
                WHERE formulaire_bt_id = ?
            ''', (bt_id,))
            
            # 4. NOUVEAU : Supprimer les opérations synchronisées avec le Kanban
            self.db.execute_query('''
                DELETE FROM operations 
                WHERE formulaire_bt_id = ?
            ''', (bt_id,))
            
            # 5. Supprimer le formulaire principal
            result = self.db.execute_query('''
                DELETE FROM formulaires 
                WHERE id = ? AND type_formulaire = 'BON_TRAVAIL'
            ''', (bt_id,))
            
            # Enregistrer l'action de suppression dans les logs
            logger.info(f"Bon de Travail {bt_data['numero_document']} (ID: {bt_id}) supprimé avec succès")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur suppression BT {bt_id}: {e}")
            return False

    def get_bt_delete_impact(self, bt_id: int) -> Dict:
        """
        Analyse l'impact de la suppression d'un BT
        NOUVELLE FONCTION : Analyse des dépendances avant suppression
        VERSION KANBAN : Inclut les opérations synchronisées
        """
        try:
            # Récupérer les informations du BT
            bt_data = self.load_bon_travail(bt_id)
            if not bt_data:
                return {'exists': False}
            
            # Compter les lignes associées
            lignes_count = self.db.execute_query('''
                SELECT COUNT(*) as count FROM formulaire_lignes 
                WHERE formulaire_id = ?
            ''', (bt_id,))
            
            # Compter les entrées TimeTracker
            timetracker_count = self.db.execute_query('''
                SELECT COUNT(*) as count, COALESCE(SUM(total_hours), 0) as total_hours,
                       COALESCE(SUM(total_cost), 0) as total_cost
                FROM time_entries 
                WHERE formulaire_bt_id = ?
            ''', (bt_id,))
            
            # Compter les validations
            validations_count = self.db.execute_query('''
                SELECT COUNT(*) as count FROM formulaire_validations 
                WHERE formulaire_id = ?
            ''', (bt_id,))
            
            # NOUVEAU : Compter les opérations Kanban synchronisées
            operations_count = self.db.execute_query('''
                SELECT COUNT(*) as count FROM operations 
                WHERE formulaire_bt_id = ?
            ''', (bt_id,))
            
            impact = {
                'exists': True,
                'bt_info': {
                    'numero_document': bt_data['numero_document'],
                    'project_name': bt_data['project_name'],
                    'client_name': bt_data['client_name'],
                    'statut': bt_data.get('statut', 'BROUILLON')
                },
                'lignes_count': lignes_count[0]['count'] if lignes_count else 0,
                'timetracker_sessions': timetracker_count[0]['count'] if timetracker_count else 0,
                'timetracker_hours': timetracker_count[0]['total_hours'] if timetracker_count else 0,
                'timetracker_cost': timetracker_count[0]['total_cost'] if timetracker_count else 0,
                'validations_count': validations_count[0]['count'] if validations_count else 0,
                'operations_count': operations_count[0]['count'] if operations_count else 0
            }
            
            # Évaluer le niveau de risque
            if impact['timetracker_sessions'] > 0:
                impact['risk_level'] = 'HIGH'
                impact['risk_message'] = "⚠️ ATTENTION: Ce BT contient des données TimeTracker (heures pointées)"
            elif impact['operations_count'] > 0:
                impact['risk_level'] = 'MEDIUM'
                impact['risk_message'] = f"⚠️ Ce BT est synchronisé avec le Kanban ({impact['operations_count']} opération(s))"
            elif impact['lignes_count'] > 5:
                impact['risk_level'] = 'MEDIUM'
                impact['risk_message'] = "⚠️ Ce BT contient plusieurs tâches/matériaux"
            else:
                impact['risk_level'] = 'LOW'
                impact['risk_message'] = "✅ Suppression à faible risque"
            
            return impact
            
        except Exception as e:
            logger.error(f"Erreur analyse impact suppression BT {bt_id}: {e}")
            return {'exists': False, 'error': str(e)}
    
    def load_bon_travail(self, bt_id: int) -> Optional[Dict]:
        """
        Charge un bon de travail depuis la base
        VERSION CORRIGÉE : Parsing amélioré pour operation/description
        MODIFIÉ : Support des fournisseurs
        """
        try:
            # Récupérer le formulaire principal
            bt_result = self.db.execute_query('''
                SELECT * FROM formulaires 
                WHERE id = ? AND type_formulaire = 'BON_TRAVAIL'
            ''', (bt_id,))
            
            if not bt_result:
                return None
            
            bt_data = dict(bt_result[0])
            
            # Parser les métadonnées
            metadonnees = {}
            try:
                metadonnees = json.loads(bt_data.get('metadonnees_json', '{}'))
            except:
                pass
            
            # Récupérer les lignes (tâches et matériaux)
            lignes_result = self.db.execute_query('''
                SELECT * FROM formulaire_lignes 
                WHERE formulaire_id = ? 
                ORDER BY sequence_ligne
            ''', (bt_id,))
            
            tasks = []
            materials = []
            
            for ligne in lignes_result:
                ligne_data = dict(ligne)
                notes_data = {}
                try:
                    notes_data = json.loads(ligne_data.get('notes_ligne', '{}'))
                except:
                    pass
                
                if ligne_data['sequence_ligne'] >= 1000:  # Matériaux
                    # Extraire le nom du matériau de la description
                    desc = ligne_data['description']
                    if desc.startswith('MATERIAU: '):
                        desc = desc[10:]  # Enlever "MATERIAU: "
                    
                    name_desc = desc.split(' - ', 1)
                    material = {
                        'name': name_desc[0] if name_desc else desc,
                        'description': name_desc[1] if len(name_desc) > 1 else '',
                        'quantity': ligne_data.get('quantite', 1.0),
                        'unit': ligne_data.get('unite', 'pcs'),
                        'fournisseur': notes_data.get('fournisseur', '-- Interne --'),  # NOUVEAU
                        'available': notes_data.get('available', 'yes'),
                        'notes': notes_data.get('notes', '')
                    }
                    materials.append(material)
                    
                else:  # Tâches - LOGIQUE CORRIGÉE
                    # CORRECTION: Récupérer depuis notes_data en priorité
                    if 'operation' in notes_data and 'description' in notes_data:
                        # Nouveau format avec données explicites
                        operation = notes_data.get('operation', '')
                        description = notes_data.get('description', '')
                    else:
                        # Fallback: parser l'ancienne description
                        desc = ligne_data['description']
                        if ' - ' in desc:
                            op_desc = desc.split(' - ', 1)
                            operation = op_desc[0]
                            description = op_desc[1] if len(op_desc) > 1 else ''
                        else:
                            # Cas simple
                            if desc.startswith('TÂCHE - '):
                                operation = ''
                                description = desc.replace('TÂCHE - ', '')
                            else:
                                operation = desc
                                description = ''
                    
                    task = {
                        'operation': operation,
                        'description': description,
                        'quantity': ligne_data.get('quantite', 1),
                        'planned_hours': ligne_data.get('prix_unitaire', 0.0),
                        'actual_hours': notes_data.get('actual_hours', 0.0),
                        'assigned_to': notes_data.get('assigned_to', ''),
                        'fournisseur': notes_data.get('fournisseur', '-- Interne --'),  # NOUVEAU
                        'status': notes_data.get('status', 'pending'),
                        'start_date': notes_data.get('start_date', ''),
                        'end_date': notes_data.get('end_date', '')
                    }
                    tasks.append(task)
            
            # Construire le formulaire complet
            form_data = {
                'id': bt_data['id'],
                'numero_document': bt_data['numero_document'],
                'project_id': metadonnees.get('project_id', ''),  # AJOUT
                'project_name': metadonnees.get('project_name', ''),
                'client_name': metadonnees.get('client_name', ''),
                'client_company_id': metadonnees.get('client_company_id'),  # AJOUT
                'project_manager': metadonnees.get('project_manager', ''),
                'priority': bt_data.get('priorite', 'NORMAL'),
                'start_date': metadonnees.get('start_date', ''),
                'end_date': bt_data.get('date_echeance', ''),
                'work_instructions': bt_data.get('notes', ''),
                'safety_notes': metadonnees.get('safety_notes', ''),
                'quality_requirements': metadonnees.get('quality_requirements', ''),
                'tasks': tasks if tasks else [self.get_empty_task()],
                'materials': materials if materials else [self.get_empty_material()],
                'created_by': metadonnees.get('created_by', 'Utilisateur'),
                'statut': bt_data.get('statut', 'BROUILLON'),
                'date_creation': bt_data.get('created_at', ''),
                'date_modification': bt_data.get('updated_at', '')
            }
            
            return form_data
            
        except Exception as e:
            logger.error(f"Erreur chargement BT {bt_id}: {e}")
            return None
    
    def get_all_bons_travail(self) -> List[Dict]:
        """Récupère tous les bons de travail"""
        try:
            results = self.db.execute_query('''
                SELECT f.*, 
                       COUNT(fl.id) as nb_lignes,
                       COALESCE(SUM(CASE WHEN fl.sequence_ligne < 1000 THEN fl.prix_unitaire ELSE 0 END), 0) as total_heures_prevues
                FROM formulaires f
                LEFT JOIN formulaire_lignes fl ON f.id = fl.formulaire_id
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                GROUP BY f.id
                ORDER BY f.created_at DESC
            ''')
            
            bons = []
            for row in results:
                row_data = dict(row)
                
                # Parser les métadonnées
                metadonnees = {}
                try:
                    metadonnees = json.loads(row_data.get('metadonnees_json', '{}'))
                except:
                    pass
                
                bon = {
                    'id': row_data['id'],
                    'numero_document': row_data['numero_document'],
                    'project_name': metadonnees.get('project_name', 'N/A'),
                    'client_name': metadonnees.get('client_name', 'N/A'),
                    'project_manager': metadonnees.get('project_manager', 'Non assigné'),
                    'priorite': row_data.get('priorite', 'NORMAL'),
                    'statut': row_data.get('statut', 'BROUILLON'),
                    'date_creation': row_data.get('created_at', ''),
                    'date_echeance': row_data.get('date_echeance', ''),
                    'nb_lignes': row_data.get('nb_lignes', 0),
                    'total_heures_prevues': row_data.get('total_heures_prevues', 0.0)
                }
                bons.append(bon)
            
            return bons
            
        except Exception as e:
            logger.error(f"Erreur récupération BTs: {e}")
            return []
    
    def get_bt_statistics(self) -> Dict:
        """Récupère les statistiques des BT"""
        try:
            # Statistiques de base
            stats_result = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total_bt,
                    COUNT(CASE WHEN statut = 'BROUILLON' THEN 1 END) as brouillons,
                    COUNT(CASE WHEN statut = 'VALIDÉ' THEN 1 END) as valides,
                    COUNT(CASE WHEN statut = 'EN COURS' THEN 1 END) as en_cours,
                    COUNT(CASE WHEN statut = 'TERMINÉ' THEN 1 END) as termines,
                    COUNT(CASE WHEN priorite = 'CRITIQUE' THEN 1 END) as critiques,
                    COUNT(CASE WHEN priorite = 'URGENT' THEN 1 END) as urgents
                FROM formulaires 
                WHERE type_formulaire = 'BON_TRAVAIL'
            ''')
            
            if stats_result:
                stats = dict(stats_result[0])
            else:
                stats = {
                    'total_bt': 0, 'brouillons': 0, 'valides': 0, 
                    'en_cours': 0, 'termines': 0, 'critiques': 0, 'urgents': 0
                }
            
            # Statistiques TimeTracker
            tt_stats_result = self.db.execute_query('''
                SELECT 
                    COUNT(DISTINCT te.formulaire_bt_id) as bt_avec_pointages,
                    COUNT(te.id) as total_sessions,
                    COALESCE(SUM(te.total_hours), 0) as total_heures,
                    COALESCE(SUM(te.total_cost), 0) as total_cout
                FROM time_entries te
                WHERE te.formulaire_bt_id IS NOT NULL
            ''')
            
            if tt_stats_result:
                tt_stats = dict(tt_stats_result[0])
                stats.update(tt_stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur statistiques BT: {e}")
            return {}

class GestionnairePostes:
    """Gestionnaire pour les postes de travail intégré"""
    
    def __init__(self, db):
        self.db = db
        self.init_session_state()
    
    def init_session_state(self):
        """Initialise les variables de session pour les postes"""
        if 'wc_action' not in st.session_state:
            st.session_state.wc_action = 'list'  # 'list', 'create', 'edit', 'view'
        if 'wc_selected_id' not in st.session_state:
            st.session_state.wc_selected_id = None
        if 'wc_confirm_delete' not in st.session_state:
            st.session_state.wc_confirm_delete = None

def apply_dg_styles():
    """Applique les styles DG Inc. cohérents avec le HTML"""
    st.markdown("""
    <style>
    /* Variables DG Inc. */
    :root {
        --primary-color: #00A971;
        --primary-color-darker: #00673D;
        --primary-color-darkest: #004C2E;
        --primary-color-lighter: #DCFCE7;
        --background-color: #F9FAFB;
        --secondary-background-color: #FFFFFF;
        --text-color: #374151;
        --text-color-light: #6B7280;
        --border-color: #E5E7EB;
        --border-radius-md: 0.5rem;
        --box-shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    
    /* Header DG style */
    .dg-header {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-color-darker) 100%);
        color: white;
        padding: 25px 30px;
        border-radius: 12px 12px 0 0;
        margin: -1rem -1rem 1rem -1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .dg-logo-container {
        display: flex;
        align-items: center;
        gap: 15px;
    }
    
    .dg-logo-box {
        background-color: white;
        width: 60px;
        height: 40px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .dg-logo-text {
        font-family: 'Segoe UI', sans-serif;
        font-weight: 800;
        font-size: 20px;
        color: var(--primary-color);
        letter-spacing: 1px;
    }
    
    .dg-company-name {
        font-weight: 600;
        font-size: 24px;
        color: white;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    .dg-contact {
        text-align: right;
        color: rgba(255, 255, 255, 0.95);
        font-size: 14px;
        line-height: 1.4;
    }
    
    /* Section d'information */
    .dg-info-section {
        background: linear-gradient(to right, #e6f7f1, #ffffff);
        padding: 20px;
        border-radius: var(--border-radius-md);
        margin-bottom: 25px;
        border-left: 5px solid var(--primary-color);
        box-shadow: var(--box-shadow-md);
    }
    
    .dg-info-title {
        color: var(--primary-color-darker);
        margin: 0 0 15px 0;
        font-size: 24px;
        font-weight: 600;
        display: flex;
        align-items: center;
    }
    
    /* Styles pour les formulaires */
    .dg-form-container {
        background-color: var(--secondary-background-color);
        border-radius: 12px;
        box-shadow: var(--box-shadow-md);
        padding: 20px;
        margin: 10px 0;
    }
    
    /* Badges de statut */
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-block;
    }
    
    .status-brouillon { background: #fef3c7; color: #92400e; }
    .status-valide { background: #dbeafe; color: #1e40af; }
    .status-en-cours { background: #e0e7ff; color: #3730a3; }
    .status-termine { background: #d1fae5; color: #065f46; }
    .status-annule { background: #fee2e2; color: #991b1b; }
    
    .priority-critique { background: #fee2e2; color: #991b1b; }
    .priority-urgent { background: #fef3c7; color: #92400e; }
    .priority-normal { background: #d1fae5; color: #065f46; }
    
    /* Styles postes de travail */
    .wc-card {
        background: var(--primary-color-lighter);
        border-radius: var(--border-radius-md);
        padding: 20px;
        margin: 10px 0;
        box-shadow: var(--box-shadow-md);
        border-left: 4px solid var(--primary-color);
    }
    
    .wc-status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-block;
    }
    
    .wc-status-actif { background: #d1fae5; color: #065f46; }
    .wc-status-maintenance { background: #fef3c7; color: #92400e; }
    .wc-status-inactif { background: #fee2e2; color: #991b1b; }
    
    /* Tables */
    .dg-table {
        border: 1px solid var(--border-color);
        border-radius: var(--border-radius-md);
        overflow: hidden;
    }
    
    /* Boutons DG */
    .dg-btn-primary {
        background: linear-gradient(90deg, var(--primary-color) 0%, var(--primary-color-darker) 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: var(--border-radius-md);
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s;
    }
    
    .dg-btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: var(--box-shadow-md);
    }
    
    /* Navigation */
    .dg-nav-container {
        background: white;
        padding: 15px 0;
        border-bottom: 2px solid var(--border-color);
        margin-bottom: 20px;
        border-radius: var(--border-radius-md);
        box-shadow: var(--box-shadow-md);
    }
    
    /* Validation tasks */
    .task-valid { border-left: 4px solid #10b981; }
    .task-invalid { border-left: 4px solid #ef4444; }
    
    /* Style pour dropdown fournisseur */
    .supplier-dropdown {
        background-color: #f0f9ff;
        border: 1px solid #0ea5e9;
        border-radius: 4px;
    }
    
    /* Masquer les éléments Streamlit */
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .stApp > header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

def show_dg_header():
    """Affiche l'en-tête DG Inc. comme dans le HTML"""
    st.markdown("""
    <div class="dg-header">
        <div class="dg-logo-container">
            <div class="dg-logo-box">
                <div class="dg-logo-text">DG</div>
            </div>
            <div class="dg-company-name">Desmarais & Gagné inc.</div>
        </div>
        <div class="dg-contact">
            565 rue Maisonneuve<br>
            Granby, QC J2G 3H5<br>
            Tél.: (450) 372-9630<br>
            Téléc.: (450) 372-8122
        </div>
    </div>
    """, unsafe_allow_html=True)

def show_main_navigation():
    """Navigation principale simplifiée entre BT et Postes"""
    st.markdown('<div class="dg-nav-container">', unsafe_allow_html=True)
    
    # Mode principal : BT ou Postes
    if 'main_mode' not in st.session_state:
        st.session_state.main_mode = 'bt'  # 'bt' ou 'postes'
    
    nav_col1, nav_col2, nav_col3 = st.columns(3)
    
    with nav_col1:
        if st.button("🔧 Bons de Travail", use_container_width=True, 
                     type="primary" if st.session_state.main_mode == 'bt' else "secondary",
                     key="main_nav_bt"):
            st.session_state.main_mode = 'bt'
            # Aller vers la gestion des BT au lieu de la création
            st.session_state.bt_mode = 'manage'
            st.rerun()
    
    with nav_col2:
        if st.button("🏭 Postes de Travail", use_container_width=True,
                     type="primary" if st.session_state.main_mode == 'postes' else "secondary",
                     key="main_nav_postes"):
            st.session_state.main_mode = 'postes'
            st.session_state.wc_action = 'list'
            st.rerun()
    
    with nav_col3:
        if st.button("📊 Statistiques Globales", use_container_width=True, 
                     key="main_nav_stats"):
            if st.session_state.main_mode == 'bt':
                st.session_state.bt_mode = 'stats'
            else:
                st.session_state.wc_action = 'stats'
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# ================== FONCTIONS BONS DE TRAVAIL ==================

def show_bt_navigation():
    """Navigation secondaire pour les BT"""
    nav_col1, nav_col2, nav_col3 = st.columns(3)
    
    with nav_col1:
        if st.button("🔧 Nouveau Bon", use_container_width=True, 
                     type="primary" if st.session_state.bt_mode == 'create' else "secondary",
                     key="bt_nav_create"):
            st.session_state.bt_mode = 'create'
            st.session_state.bt_current_form_data = st.session_state.gestionnaire_bt.get_empty_bt_form()
            st.session_state.bt_selected_id = None
            st.rerun()
    
    with nav_col2:
        if st.button("📋 Gestion BT", use_container_width=True,
                     type="primary" if st.session_state.bt_mode == 'manage' else "secondary",
                     key="bt_nav_manage"):
            st.session_state.bt_mode = 'manage'
            st.rerun()
    
    with nav_col3:
        if st.button("📊 Stats BT", use_container_width=True,
                     type="primary" if st.session_state.bt_mode == 'stats' else "secondary",
                     key="bt_nav_stats"):
            st.session_state.bt_mode = 'stats'
            st.rerun()

def show_bt_form_section():
    """Section principale du formulaire BT avec auto-sélection client"""
    gestionnaire = st.session_state.gestionnaire_bt
    form_data = st.session_state.bt_current_form_data
    
    # Titre de section
    mode_text = "Modifier" if st.session_state.bt_mode == 'edit' else "Créer"
    if st.session_state.bt_mode == 'view':
        mode_text = "Visualiser"
    
    st.markdown(f"""
    <div class="dg-info-section">
        <h2 class="dg-info-title">🔧 {mode_text} Bon de Travail</h2>
        <p><strong>Date de création:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
        <p><strong>N° Bon de Travail:</strong> {form_data['numero_document']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Informations générales
    with st.container():
        st.markdown("### 📋 Informations Générales")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # === NOUVELLE LOGIQUE : Sélection de projet depuis la base ===
            try:
                # Récupérer tous les projets avec leurs clients
                projets_db = st.session_state.erp_db.execute_query('''
                    SELECT p.id, p.nom_projet, p.client_nom_cache, p.client_company_id,
                           c.nom as client_company_nom
                    FROM projects p
                    LEFT JOIN companies c ON p.client_company_id = c.id
                    WHERE p.statut NOT IN ('TERMINÉ', 'ANNULÉ')
                    ORDER BY p.nom_projet
                ''')
                
                # Préparer les options pour la dropdown
                projet_options = [("", "Sélectionner un projet...")]
                for projet in projets_db:
                    projet_options.append((
                        projet['id'], 
                        f"{projet['nom_projet']} (ID: {projet['id']})"
                    ))
                
                # Trouver l'index du projet actuellement sélectionné
                current_project_id = form_data.get('project_id', '')
                project_index = 0
                if current_project_id:
                    for i, (pid, _) in enumerate(projet_options):
                        if str(pid) == str(current_project_id):
                            project_index = i
                            break
                
                # Dropdown de sélection de projet
                if st.session_state.bt_mode == 'view':
                    # Mode visualisation - lecture seule
                    st.markdown("**Nom du projet *:**")
                    current_project_name = next((name for pid, name in projet_options if str(pid) == str(current_project_id)), form_data.get('project_name', 'N/A'))
                    st.text_input("Projet:", value=current_project_name, disabled=True, key="bt_project_view")
                else:
                    # Mode édition
                    selected_project_id = st.selectbox(
                        "Nom du projet *:",
                        options=[pid for pid, _ in projet_options],
                        index=project_index,
                        format_func=lambda pid: next((name for p_id, name in projet_options if p_id == pid), "Sélectionner..."),
                        key="bt_project_select"
                    )
                    
                    # Mise à jour automatique du client quand le projet change
                    if selected_project_id and selected_project_id != form_data.get('project_id', ''):
                        # Trouver le projet sélectionné
                        projet_selectionne = next((p for p in projets_db if p['id'] == selected_project_id), None)
                        
                        if projet_selectionne:
                            # Mettre à jour les données du formulaire
                            form_data['project_id'] = selected_project_id
                            form_data['project_name'] = projet_selectionne['nom_projet']
                            
                            # AUTO-SÉLECTION DU CLIENT
                            if projet_selectionne['client_company_nom']:
                                form_data['client_name'] = projet_selectionne['client_company_nom']
                                form_data['client_company_id'] = projet_selectionne['client_company_id']
                            elif projet_selectionne['client_nom_cache']:
                                form_data['client_name'] = projet_selectionne['client_nom_cache']
                            
                            # Message de confirmation
                            if form_data.get('client_name'):
                                st.success(f"✅ Client auto-détecté: **{form_data['client_name']}**")
                            
                            st.rerun()  # Recharger pour mettre à jour l'affichage
                    
                    # Stocker le nom du projet pour compatibilité
                    if selected_project_id:
                        projet_selectionne = next((p for p in projets_db if p['id'] == selected_project_id), None)
                        if projet_selectionne:
                            form_data['project_name'] = projet_selectionne['nom_projet']
                            form_data['project_id'] = selected_project_id
                
            except Exception as e:
                st.warning(f"⚠️ Erreur chargement projets: {e}")
                # Fallback vers champ texte libre
                if st.session_state.bt_mode == 'view':
                    st.text_input("Nom du projet *:", value=form_data.get('project_name', ''), disabled=True, key="bt_project_fallback_view")
                else:
                    form_data['project_name'] = st.text_input(
                        "Nom du projet *:", 
                        value=form_data.get('project_name', ''),
                        placeholder="Nom du projet"
                    )
            
            # === CLIENT - Affichage avec auto-détection ===
            client_display = form_data.get('client_name', '')
            
            if st.session_state.bt_mode == 'view':
                # Mode visualisation - lecture seule
                st.text_input("Client *:", value=client_display, disabled=True, key="bt_client_view")
            else:
                # Mode édition
                if client_display:
                    # Client auto-détecté - Affichage en lecture seule avec option de modification
                    st.markdown("**Client (auto-détecté) *:**")
                    
                    client_col1, client_col2 = st.columns([3, 1])
                    with client_col1:
                        st.text_input(
                            "Client détecté:",
                            value=client_display,
                            disabled=True,
                            key="bt_client_auto"
                        )
                    
                    with client_col2:
                        if st.button("✏️ Modifier", key="bt_modify_client", help="Modifier le client"):
                            form_data['client_name'] = ""
                            form_data['client_company_id'] = None
                            st.rerun()
                    
                    # Affichage info client
                    st.info(f"💡 Client auto-détecté depuis le projet: **{client_display}**")
                
                else:
                    # Pas de client auto-détecté - Sélection manuelle
                    try:
                        # Récupérer les entreprises clients
                        clients_db = st.session_state.erp_db.execute_query('''
                            SELECT id, nom FROM companies 
                            WHERE type_company IN ('CLIENT', 'PROSPECT') OR type_company IS NULL
                            ORDER BY nom
                        ''')
                        
                        client_options = [("", "Sélectionner un client...")]
                        for client in clients_db:
                            client_options.append((client['id'], client['nom']))
                        
                        selected_client_id = st.selectbox(
                            "Client *:",
                            options=[cid for cid, _ in client_options],
                            format_func=lambda cid: next((name for c_id, name in client_options if c_id == cid), "Sélectionner..."),
                            key="bt_client_select"
                        )
                        
                        if selected_client_id:
                            client_selectionne = next((c for c in clients_db if c['id'] == selected_client_id), None)
                            if client_selectionne:
                                form_data['client_name'] = client_selectionne['nom']
                                form_data['client_company_id'] = selected_client_id
                    
                    except Exception as e:
                        st.warning(f"⚠️ Erreur chargement clients: {e}")
                        # Fallback vers champ texte libre
                        form_data['client_name'] = st.text_input(
                            "Client *:", 
                            value=form_data.get('client_name', ''),
                            placeholder="Nom du client"
                        )
            
            # Chargé de projet
            try:
                employees = st.session_state.gestionnaire_employes.employes if hasattr(st.session_state, 'gestionnaire_employes') else []
                employee_options = [''] + [f"{emp.get('prenom', '')} {emp.get('nom', '')}" for emp in employees if emp.get('statut') == 'ACTIF']
            except:
                employee_options = ['', 'Jean Martin', 'Marie Dubois', 'Pierre Gagnon', 'Louise Tremblay']
            
            current_manager = form_data.get('project_manager', '')
            manager_index = employee_options.index(current_manager) if current_manager in employee_options else 0
            
            if st.session_state.bt_mode == 'view':
                st.text_input("Chargé de projet:", value=current_manager, disabled=True, key="bt_manager_view")
            else:
                form_data['project_manager'] = st.selectbox(
                    "Chargé de projet:",
                    options=employee_options,
                    index=manager_index
                )
        
        with col2:
            # Priorité et dates
            priority_options = ['NORMAL', 'URGENT', 'CRITIQUE']
            priority_labels = {
                'NORMAL': '🟢 Normal',
                'URGENT': '🟡 Urgent', 
                'CRITIQUE': '🔴 Critique'
            }
            
            current_priority = form_data.get('priority', 'NORMAL')
            priority_index = priority_options.index(current_priority) if current_priority in priority_options else 0
            
            if st.session_state.bt_mode == 'view':
                st.text_input("Priorité:", value=priority_labels.get(current_priority, current_priority), disabled=True, key="bt_priority_view")
            else:
                form_data['priority'] = st.selectbox(
                    "Priorité:",
                    options=priority_options,
                    index=priority_index,
                    format_func=lambda x: priority_labels.get(x, x)
                )
            
            # Dates
            start_date_value = datetime.strptime(form_data.get('start_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date()
            end_date_value = datetime.strptime(form_data.get('end_date', (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')), '%Y-%m-%d').date()
            
            if st.session_state.bt_mode == 'view':
                st.text_input("Date de début prévue:", value=start_date_value.strftime('%Y-%m-%d'), disabled=True, key="bt_start_view")
                st.text_input("Date de fin prévue:", value=end_date_value.strftime('%Y-%m-%d'), disabled=True, key="bt_end_view")
            else:
                form_data['start_date'] = st.date_input(
                    "Date de début prévue:",
                    value=start_date_value
                ).strftime('%Y-%m-%d')
                
                form_data['end_date'] = st.date_input(
                    "Date de fin prévue:",
                    value=end_date_value
                ).strftime('%Y-%m-%d')

def show_tasks_section():
    """
    Section des tâches et opérations
    VERSION CORRIGÉE : Validation visuelle améliorée + Types numériques corrigés
    NOUVELLE VERSION : Ajout dropdown Fournisseur/Sous-traitant
    """
    form_data = st.session_state.bt_current_form_data
    gestionnaire = st.session_state.gestionnaire_bt
    
    st.markdown("### 📋 Tâches et Opérations")
    
    # Operations disponibles (en fonction des postes de travail)
    try:
        # Récupérer les postes de travail disponibles
        postes = st.session_state.erp_db.execute_query(
            "SELECT nom FROM work_centers WHERE statut = 'ACTIF' ORDER BY nom"
        )
        operation_options = [''] + [poste['nom'] for poste in postes]
    except:
        operation_options = [
            '', 'Programmation CNC', 'Découpe plasma', 'Poinçonnage', 
            'Soudage TIG', 'Assemblage', 'Meulage', 'Polissage', 'Emballage'
        ]
    
    # NOUVEAU : Récupérer les fournisseurs actifs
    fournisseurs_actifs = gestionnaire.get_fournisseurs_actifs()
    fournisseurs_options = ['-- Interne --'] + fournisseurs_actifs
    
    # Employés disponibles
    try:
        employees = st.session_state.gestionnaire_employes.employes if hasattr(st.session_state, 'gestionnaire_employes') else []
        employee_options = [''] + [f"{emp.get('prenom', '')} {emp.get('nom', '')}" for emp in employees if emp.get('statut') == 'ACTIF']
    except:
        employee_options = ['', 'Technicien 1', 'Technicien 2', 'Soudeur 1', 'Soudeur 2', 'Programmeur CNC']
    
    status_options = ['pending', 'in-progress', 'completed', 'on-hold']
    status_labels = {
        'pending': 'En attente',
        'in-progress': 'En cours', 
        'completed': 'Terminé',
        'on-hold': 'En pause'
    }
    
    if 'tasks' not in form_data or not form_data['tasks']:
        form_data['tasks'] = [st.session_state.gestionnaire_bt.get_empty_task()]
    
    # Affichage des tâches avec validation améliorée
    tasks_to_remove = []
    
    for i, task in enumerate(form_data['tasks']):
        # AMÉLIORATION: Indicateur de validation
        task_valid = bool(task.get('operation') or task.get('description'))
        title_icon = "🟢" if task_valid else "🔴"
        
        task_title = f"{title_icon} Tâche {i+1}"
        if task.get('operation'):
            task_title += f" - {task['operation']}"
        elif task.get('description'):
            task_title += f" - {task['description'][:30]}..."
        
        # NOUVEAU : Afficher le fournisseur dans le titre si pas interne
        if task.get('fournisseur') and task['fournisseur'] != '-- Interne --':
            task_title += f" 🏢 {task['fournisseur'][:20]}"
        
        # Classe CSS selon validation
        validation_class = "task-valid" if task_valid else "task-invalid"
        
        with st.expander(task_title, expanded=True):
            # AJOUT: Message de validation
            if not task_valid and st.session_state.bt_mode != 'view':
                st.warning("⚠️ Cette tâche ne sera pas sauvegardée (opération OU description requise)")
            
            task_col1, task_col2, task_col3 = st.columns([2, 1, 1])
            
            with task_col1:
                # Opération
                op_index = operation_options.index(task.get('operation', '')) if task.get('operation', '') in operation_options else 0
                
                if st.session_state.bt_mode == 'view':
                    st.text_input("Poste/Opération:", value=task.get('operation', ''), disabled=True, key=f"task_op_view_{i}")
                else:
                    task['operation'] = st.selectbox(
                        "Poste/Opération:", 
                        options=operation_options,
                        index=op_index,
                        key=f"task_op_{i}"
                    )
                
                # NOUVEAU : Fournisseur/Sous-traitant
                fournisseur_index = fournisseurs_options.index(task.get('fournisseur', '-- Interne --')) if task.get('fournisseur', '-- Interne --') in fournisseurs_options else 0
                
                if st.session_state.bt_mode == 'view':
                    st.text_input("Fournisseur/Sous-traitant:", value=task.get('fournisseur', '-- Interne --'), disabled=True, key=f"task_fournisseur_view_{i}")
                else:
                    task['fournisseur'] = st.selectbox(
                        "Fournisseur/Sous-traitant:", 
                        options=fournisseurs_options,
                        index=fournisseur_index,
                        key=f"task_fournisseur_{i}",
                        help="Sélectionnez '-- Interne --' pour une opération réalisée en interne, ou choisissez un fournisseur pour la sous-traitance"
                    )
                
                # Description
                if st.session_state.bt_mode == 'view':
                    st.text_input("Description:", value=task.get('description', ''), disabled=True, key=f"task_desc_view_{i}")
                else:
                    task['description'] = st.text_input(
                        "Description:", 
                        value=task.get('description', ''),
                        placeholder="Description détaillée de la tâche",
                        key=f"task_desc_{i}"
                    )
            
            with task_col2:
                # Quantité
                if st.session_state.bt_mode == 'view':
                    st.text_input("Quantité:", value=str(task.get('quantity', 1)), disabled=True, key=f"task_qty_view_{i}")
                else:
                    task['quantity'] = st.number_input(
                        "Quantité:", 
                        value=int(task.get('quantity', 1)),
                        min_value=1,
                        step=1,
                        key=f"task_qty_{i}"
                    )
                
                # Heures prévues
                if st.session_state.bt_mode == 'view':
                    st.text_input("Heures prévues:", value=f"{task.get('planned_hours', 0.0):.2f}", disabled=True, key=f"task_planned_view_{i}")
                else:
                    task['planned_hours'] = st.number_input(
                        "Heures prévues:", 
                        value=float(task.get('planned_hours', 0.0)),
                        min_value=0.0,
                        step=0.25,
                        key=f"task_planned_{i}"
                    )
                
                # Heures réelles
                if st.session_state.bt_mode == 'view':
                    st.text_input("Heures réelles:", value=f"{task.get('actual_hours', 0.0):.2f}", disabled=True, key=f"task_actual_view_{i}")
                else:
                    task['actual_hours'] = st.number_input(
                        "Heures réelles:", 
                        value=float(task.get('actual_hours', 0.0)),
                        min_value=0.0,
                        step=0.25,
                        key=f"task_actual_{i}"
                    )
            
            with task_col3:
                # Assigné à - Modifier selon le type (interne/externe)
                if task.get('fournisseur') == '-- Interne --':
                    # Opération interne - montrer les employés
                    assigned_index = employee_options.index(task.get('assigned_to', '')) if task.get('assigned_to', '') in employee_options else 0
                    
                    if st.session_state.bt_mode == 'view':
                        st.text_input("Assigné à:", value=task.get('assigned_to', ''), disabled=True, key=f"task_assigned_view_{i}")
                    else:
                        task['assigned_to'] = st.selectbox(
                            "Assigné à:", 
                            options=employee_options,
                            index=assigned_index,
                            key=f"task_assigned_{i}"
                        )
                else:
                    # Sous-traitance - champ libre pour contact externe
                    if st.session_state.bt_mode == 'view':
                        st.text_input("Contact externe:", value=task.get('assigned_to', ''), disabled=True, key=f"task_contact_view_{i}")
                    else:
                        task['assigned_to'] = st.text_input(
                            "Contact externe:", 
                            value=task.get('assigned_to', ''),
                            placeholder="Nom du contact chez le fournisseur",
                            key=f"task_contact_{i}"
                        )
                
                # Statut
                status_index = status_options.index(task.get('status', 'pending')) if task.get('status', 'pending') in status_options else 0
                
                if st.session_state.bt_mode == 'view':
                    st.text_input("Statut:", value=status_labels.get(task.get('status', 'pending'), task.get('status', 'pending')), disabled=True, key=f"task_status_view_{i}")
                else:
                    task['status'] = st.selectbox(
                        "Statut:", 
                        options=status_options,
                        index=status_index,
                        format_func=lambda x: status_labels.get(x, x),
                        key=f"task_status_{i}"
                    )
                
                # Dates
                if st.session_state.bt_mode == 'view':
                    st.text_input("Date début:", value=task.get('start_date', ''), disabled=True, key=f"task_start_view_{i}")
                    st.text_input("Date fin:", value=task.get('end_date', ''), disabled=True, key=f"task_end_view_{i}")
                else:
                    if task.get('start_date'):
                        try:
                            start_date = datetime.strptime(task['start_date'], '%Y-%m-%d').date()
                        except:
                            start_date = None
                    else:
                        start_date = None
                    
                    task['start_date'] = st.date_input(
                        "Date début:", 
                        value=start_date,
                        key=f"task_start_{i}"
                    )
                    if task['start_date']:
                        task['start_date'] = task['start_date'].strftime('%Y-%m-%d')
                    
                    if task.get('end_date'):
                        try:
                            end_date = datetime.strptime(task['end_date'], '%Y-%m-%d').date()
                        except:
                            end_date = None
                    else:
                        end_date = None
                    
                    task['end_date'] = st.date_input(
                        "Date fin:", 
                        value=end_date,
                        key=f"task_end_{i}"
                    )
                    if task['end_date']:
                        task['end_date'] = task['end_date'].strftime('%Y-%m-%d')
                
                # Bouton supprimer (seulement en mode édition)
                if st.session_state.bt_mode != 'view' and len(form_data['tasks']) > 1:
                    if st.button("🗑️ Supprimer", key=f"del_task_{i}", type="secondary"):
                        tasks_to_remove.append(i)
    
    # Supprimer les tâches marquées
    if st.session_state.bt_mode != 'view':
        for i in reversed(tasks_to_remove):
            form_data['tasks'].pop(i)
            st.rerun()
        
        # Bouton ajouter tâche
        col_add, col_total = st.columns([1, 2])
        with col_add:
            if st.button("➕ Ajouter une tâche", type="secondary", key="add_task_btn"):
                form_data['tasks'].append(st.session_state.gestionnaire_bt.get_empty_task())
                st.rerun()
        
        with col_total:
            # Totaux avec répartition interne/externe
            total_planned = sum(task.get('planned_hours', 0) for task in form_data['tasks'])
            total_actual = sum(task.get('actual_hours', 0) for task in form_data['tasks'])
            
            # NOUVEAU : Calcul répartition interne/externe
            internal_planned = sum(task.get('planned_hours', 0) for task in form_data['tasks'] if task.get('fournisseur') == '-- Interne --')
            external_planned = total_planned - internal_planned
            
            st.markdown(f"""
            **Totaux:** 
            - Heures prévues: **{total_planned:.2f}h** (Interne: {internal_planned:.2f}h, Externe: {external_planned:.2f}h)
            - Heures réelles: **{total_actual:.2f}h**
            """)
    else:
        # Mode visualisation - afficher seulement les totaux avec répartition
        total_planned = sum(task.get('planned_hours', 0) for task in form_data['tasks'])
        total_actual = sum(task.get('actual_hours', 0) for task in form_data['tasks'])
        
        # Calcul répartition interne/externe
        internal_planned = sum(task.get('planned_hours', 0) for task in form_data['tasks'] if task.get('fournisseur') == '-- Interne --')
        external_planned = total_planned - internal_planned
        
        st.markdown(f"""
        **Totaux:** 
        - Heures prévues: **{total_planned:.2f}h** (Interne: {internal_planned:.2f}h, Externe: {external_planned:.2f}h)
        - Heures réelles: **{total_actual:.2f}h**
        """)

def show_materials_section():
    """
    Section des matériaux et outils - VERSION CORRIGÉE types numériques
    NOUVELLE VERSION : Ajout dropdown Fournisseur pour matériaux
    """
    form_data = st.session_state.bt_current_form_data
    gestionnaire = st.session_state.gestionnaire_bt
    
    st.markdown("### 📝 Matériaux et Outils Requis")
    
    # NOUVEAU : Récupérer les fournisseurs actifs
    fournisseurs_actifs = gestionnaire.get_fournisseurs_actifs()
    fournisseurs_options = ['-- Interne --'] + fournisseurs_actifs
    
    unit_options = ['pcs', 'kg', 'm', 'm2', 'l', 'h']
    unit_labels = {
        'pcs': 'Pièces', 'kg': 'Kilogrammes', 'm': 'Mètres', 
        'm2': 'Mètres²', 'l': 'Litres', 'h': 'Heures'
    }
    
    available_options = ['yes', 'no', 'partial', 'ordered']
    available_labels = {
        'yes': '✅ Disponible',
        'no': '❌ Non disponible', 
        'partial': '⚠️ Partiellement',
        'ordered': '📦 Commandé'
    }
    
    if 'materials' not in form_data or not form_data['materials']:
        form_data['materials'] = [st.session_state.gestionnaire_bt.get_empty_material()]
    
    # Affichage des matériaux
    materials_to_remove = []
    
    for i, material in enumerate(form_data['materials']):
        # NOUVEAU : Titre avec fournisseur
        material_title = f"Matériau/Outil {i+1}"
        if material['name']:
            material_title += f" - {material['name']}"
        if material.get('fournisseur') and material['fournisseur'] != '-- Interne --':
            material_title += f" 🏢 {material['fournisseur'][:20]}"
        
        with st.expander(material_title, expanded=True):
            mat_col1, mat_col2, mat_col3 = st.columns([2, 1, 1])
            
            with mat_col1:
                if st.session_state.bt_mode == 'view':
                    st.text_input("Nom du matériau/outil:", value=material.get('name', ''), disabled=True, key=f"mat_name_view_{i}")
                    st.text_input("Description:", value=material.get('description', ''), disabled=True, key=f"mat_desc_view_{i}")
                else:
                    material['name'] = st.text_input(
                        "Nom du matériau/outil:", 
                        value=material.get('name', ''),
                        placeholder="Nom du matériau/outil",
                        key=f"mat_name_{i}"
                    )
                    
                    material['description'] = st.text_input(
                        "Description:", 
                        value=material.get('description', ''),
                        placeholder="Description détaillée",
                        key=f"mat_desc_{i}"
                    )
                
                # NOUVEAU : Fournisseur pour matériau
                fournisseur_mat_index = fournisseurs_options.index(material.get('fournisseur', '-- Interne --')) if material.get('fournisseur', '-- Interne --') in fournisseurs_options else 0
                
                if st.session_state.bt_mode == 'view':
                    st.text_input("Fournisseur:", value=material.get('fournisseur', '-- Interne --'), disabled=True, key=f"mat_fournisseur_view_{i}")
                else:
                    material['fournisseur'] = st.selectbox(
                        "Fournisseur:", 
                        options=fournisseurs_options,
                        index=fournisseur_mat_index,
                        key=f"mat_fournisseur_{i}",
                        help="Sélectionnez '-- Interne --' pour un matériau en stock, ou choisissez un fournisseur pour un achat externe"
                    )
            
            with mat_col2:
                if st.session_state.bt_mode == 'view':
                    st.text_input("Quantité:", value=f"{material.get('quantity', 1.0):.1f}", disabled=True, key=f"mat_qty_view_{i}")
                    unit_display = unit_labels.get(material.get('unit', 'pcs'), material.get('unit', 'pcs'))
                    st.text_input("Unité:", value=unit_display, disabled=True, key=f"mat_unit_view_{i}")
                else:
                    material['quantity'] = st.number_input(
                        "Quantité:", 
                        value=float(material.get('quantity', 1.0)),
                        min_value=0.1,
                        step=0.1,
                        key=f"mat_qty_{i}"
                    )
                    
                    unit_index = unit_options.index(material.get('unit', 'pcs')) if material.get('unit', 'pcs') in unit_options else 0
                    material['unit'] = st.selectbox(
                        "Unité:", 
                        options=unit_options,
                        index=unit_index,
                        format_func=lambda x: unit_labels.get(x, x),
                        key=f"mat_unit_{i}"
                    )
            
            with mat_col3:
                if st.session_state.bt_mode == 'view':
                    avail_display = available_labels.get(material.get('available', 'yes'), material.get('available', 'yes'))
                    st.text_input("Disponibilité:", value=avail_display, disabled=True, key=f"mat_avail_view_{i}")
                    st.text_area("Notes:", value=material.get('notes', ''), disabled=True, height=100, key=f"mat_notes_view_{i}")
                else:
                    available_index = available_options.index(material.get('available', 'yes')) if material.get('available', 'yes') in available_options else 0
                    material['available'] = st.selectbox(
                        "Disponibilité:", 
                        options=available_options,
                        index=available_index,
                        format_func=lambda x: available_labels.get(x, x),
                        key=f"mat_avail_{i}"
                    )
                    
                    material['notes'] = st.text_area(
                        "Notes:", 
                        value=material.get('notes', ''),
                        placeholder="Notes spéciales",
                        height=100,
                        key=f"mat_notes_{i}"
                    )
                
                # Bouton supprimer (seulement en mode édition)
                if st.session_state.bt_mode != 'view' and len(form_data['materials']) > 1:
                    if st.button("🗑️ Supprimer", key=f"del_mat_{i}", type="secondary"):
                        materials_to_remove.append(i)
    
    # Supprimer les matériaux marqués
    if st.session_state.bt_mode != 'view':
        for i in reversed(materials_to_remove):
            form_data['materials'].pop(i)
            st.rerun()
        
        # Bouton ajouter matériau
        if st.button("➕ Ajouter un matériau/outil", type="secondary", key="add_material_btn"):
            form_data['materials'].append(st.session_state.gestionnaire_bt.get_empty_material())
            st.rerun()

def show_instructions_section():
    """Section des instructions et notes"""
    form_data = st.session_state.bt_current_form_data
    
    st.markdown("### 📄 Instructions et Notes")
    
    if st.session_state.bt_mode == 'view':
        st.text_area("Instructions de travail:", value=form_data.get('work_instructions', ''), disabled=True, height=100, key="work_inst_view")
        st.text_area("Notes de sécurité:", value=form_data.get('safety_notes', ''), disabled=True, height=80, key="safety_notes_view")
        st.text_area("Exigences qualité:", value=form_data.get('quality_requirements', ''), disabled=True, height=80, key="quality_req_view")
    else:
        form_data['work_instructions'] = st.text_area(
            "Instructions de travail:",
            value=form_data.get('work_instructions', ''),
            placeholder="Instructions détaillées pour l'exécution du travail...",
            height=100
        )
        
        form_data['safety_notes'] = st.text_area(
            "Notes de sécurité:",
            value=form_data.get('safety_notes', ''),
            placeholder="Consignes de sécurité particulières...",
            height=80
        )
        
        form_data['quality_requirements'] = st.text_area(
            "Exigences qualité:",
            value=form_data.get('quality_requirements', ''),
            placeholder="Standards et contrôles qualité requis...",
            height=80
        )

def show_bt_actions():
    """
    Boutons d'action pour le BT
    VERSION FINALE : Support complet de la modification des BT + Export PDF intégré
    VERSION KANBAN : Notification de synchronisation
    """
    st.markdown("---")
    
    # Mode visualisation - boutons différents
    if st.session_state.bt_mode == 'view':
        action_col1, action_col2, action_col3, action_col4 = st.columns(4)
        
        with action_col1:
            if st.button("✏️ Modifier ce BT", type="primary", use_container_width=True, key="bt_edit_current_btn"):
                st.session_state.bt_mode = 'edit'
                st.rerun()
        
        with action_col2:
            if st.button("🖨️ Imprimer", use_container_width=True, key="bt_print_view_btn"):
                st.info("📋 Fonction d'impression en développement")
        
        with action_col3:
            # NOUVEAU : Export PDF fonctionnel
            if st.button("📄 Exporter PDF", use_container_width=True, key="bt_pdf_view_btn"):
                if PDF_EXPORT_AVAILABLE:
                    export_bt_pdf_streamlit(st.session_state.bt_current_form_data)
                else:
                    st.error("❌ Module d'export PDF non disponible. Installez: pip install reportlab")
        
        with action_col4:
            if st.button("📋 Retour Gestion", use_container_width=True, key="bt_back_manage_btn"):
                st.session_state.bt_mode = 'manage'
                st.rerun()
    
    else:
        # Mode création/édition - boutons normaux
        action_col1, action_col2, action_col3, action_col4 = st.columns(4)
        
        form_data = st.session_state.bt_current_form_data
        gestionnaire = st.session_state.gestionnaire_bt
        
        with action_col1:
            # Texte du bouton selon le mode
            if st.session_state.bt_mode == 'edit':
                button_text = "💾 Sauvegarder Modifications"
            else:
                button_text = "💾 Sauvegarder Bon de Travail"
            
            if st.button(button_text, type="primary", use_container_width=True, key="bt_save_btn"):
                # Validation
                if not form_data.get('project_name'):
                    st.error("❌ Le nom du projet est obligatoire")
                    return
                
                if not form_data.get('client_name'):
                    st.error("❌ Le nom du client est obligatoire")
                    return
                
                # Sauvegarder selon le mode
                if st.session_state.bt_mode == 'edit' and form_data.get('id'):
                    # MODIFICATION
                    success = gestionnaire.update_bon_travail(form_data['id'], form_data)
                    if success:
                        st.success(f"✅ Bon de Travail {form_data['numero_document']} modifié avec succès!")
                        st.info("🔄 Synchronisation automatique avec le Kanban effectuée")
                        
                        # Recharger le BT modifié
                        try:
                            reloaded_data = gestionnaire.load_bon_travail(form_data['id'])
                            if reloaded_data:
                                st.session_state.bt_current_form_data = reloaded_data
                                st.session_state.bt_mode = 'view'
                                st.info("✅ BT rechargé en mode visualisation")
                            else:
                                st.warning("⚠️ BT modifié mais rechargement échoué")
                        except Exception as e:
                            st.warning(f"⚠️ BT modifié mais erreur rechargement: {e}")
                        
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la modification")
                else:
                    # CRÉATION
                    bt_id = gestionnaire.save_bon_travail(form_data)
                    if bt_id:
                        st.success(f"✅ Bon de Travail {form_data['numero_document']} créé avec succès!")
                        st.info("🔄 Synchronisation automatique avec le Kanban effectuée")
                        
                        # Recharger le BT au lieu de réinitialiser
                        try:
                            reloaded_data = gestionnaire.load_bon_travail(bt_id)
                            if reloaded_data:
                                st.session_state.bt_current_form_data = reloaded_data
                                st.session_state.bt_mode = 'view'
                                st.session_state.bt_selected_id = bt_id
                                st.info("✅ BT rechargé en mode visualisation")
                            else:
                                st.warning("⚠️ BT créé mais rechargement échoué")
                        except Exception as e:
                            st.warning(f"⚠️ BT créé mais erreur rechargement: {e}")
                        
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la création")
        
        with action_col2:
            if st.button("🖨️ Imprimer", use_container_width=True, key="bt_print_btn"):
                st.info("📋 Fonction d'impression en développement")
        
        with action_col3:
            # NOUVEAU : Export PDF fonctionnel
            if st.button("📄 Exporter PDF", use_container_width=True, key="bt_pdf_btn"):
                if PDF_EXPORT_AVAILABLE:
                    # Vérifier que le BT a les infos minimales pour l'export
                    if not form_data.get('project_name') or not form_data.get('client_name'):
                        st.warning("⚠️ Veuillez remplir au moins le projet et le client avant l'export PDF")
                    else:
                        export_bt_pdf_streamlit(form_data)
                else:
                    st.error("❌ Module d'export PDF non disponible. Installez: pip install reportlab")
        
        with action_col4:
            if st.button("🗑️ Nouveau Bon", use_container_width=True, key="bt_new_btn"):
                if st.session_state.get('bt_form_has_changes', False):
                    if st.button("⚠️ Confirmer - Perdre les modifications", type="secondary", key="bt_confirm_new_btn"):
                        st.session_state.bt_current_form_data = gestionnaire.get_empty_bt_form()
                        st.session_state.bt_form_has_changes = False
                        st.session_state.bt_mode = 'create'
                        st.rerun()
                else:
                    st.session_state.bt_current_form_data = gestionnaire.get_empty_bt_form()
                    st.session_state.bt_mode = 'create'
                    st.rerun()

def show_bt_delete_confirmation():
    """
    Affiche la boîte de dialogue de confirmation de suppression
    NOUVELLE FONCTION : Interface de confirmation sécurisée
    VERSION KANBAN : Inclut les opérations synchronisées
    """
    if not st.session_state.bt_confirm_delete:
        return
    
    bt_id = st.session_state.bt_confirm_delete
    gestionnaire = st.session_state.gestionnaire_bt
    
    # Analyser l'impact de la suppression
    impact = gestionnaire.get_bt_delete_impact(bt_id)
    
    if not impact.get('exists'):
        st.error("❌ Bon de Travail non trouvé")
        st.session_state.bt_confirm_delete = None
        return
    
    bt_info = impact['bt_info']
    risk_level = impact.get('risk_level', 'LOW')
    
    # Couleur selon le niveau de risque
    if risk_level == 'HIGH':
        alert_color = 'error'
        warning_icon = '🚨'
    elif risk_level == 'MEDIUM':
        alert_color = 'warning'
        warning_icon = '⚠️'
    else:
        alert_color = 'info'
        warning_icon = '🗑️'
    
    # Affichage de la confirmation
    with st.container():
        if alert_color == 'error':
            st.error(f"""
            {warning_icon} **CONFIRMATION DE SUPPRESSION - RISQUE ÉLEVÉ**
            
            **Bon de Travail à supprimer :**
            - **N°:** {bt_info['numero_document']}
            - **Projet:** {bt_info['project_name']}
            - **Client:** {bt_info['client_name']}
            - **Statut:** {bt_info['statut']}
            
            **⚠️ DONNÉES QUI SERONT SUPPRIMÉES :**
            - **{impact['lignes_count']} tâche(s)/matériau(x)**
            - **{impact['timetracker_sessions']} session(s) TimeTracker** ({impact['timetracker_hours']:.1f}h, {impact['timetracker_cost']:,.0f}$)
            - **{impact['operations_count']} opération(s) Kanban synchronisée(s)**
            - **{impact['validations_count']} validation(s)/historique**
            
            {impact['risk_message']}
            
            **🚨 CETTE ACTION EST IRRÉVERSIBLE ! 🚨**
            """)
        elif alert_color == 'warning':
            st.warning(f"""
            {warning_icon} **CONFIRMATION DE SUPPRESSION**
            
            **Bon de Travail à supprimer :**
            - **N°:** {bt_info['numero_document']}
            - **Projet:** {bt_info['project_name']}
            - **Client:** {bt_info['client_name']}
            
            **Données qui seront supprimées :**
            - {impact['lignes_count']} tâche(s)/matériau(x)
            - {impact['operations_count']} opération(s) Kanban
            - {impact['validations_count']} validation(s)
            
            {impact['risk_message']}
            """)
        else:
            st.info(f"""
            {warning_icon} **Confirmation de suppression**
            
            **Bon de Travail :** {bt_info['numero_document']} - {bt_info['project_name']}
            
            **Données à supprimer :** {impact['lignes_count']} ligne(s), {impact['operations_count']} opération(s) Kanban
            
            {impact['risk_message']}
            """)
        
        # Étape de confirmation selon le niveau de risque
        if risk_level == 'HIGH':
            # Confirmation à deux étapes pour risque élevé
            if not st.session_state.bt_delete_confirmed:
                st.markdown("**📝 Veuillez taper 'SUPPRIMER' pour confirmer :**")
                confirm_text = st.text_input(
                    "Confirmation requise:",
                    placeholder="Tapez SUPPRIMER en majuscules",
                    key="bt_delete_confirm_text"
                )
                
                if confirm_text == "SUPPRIMER":
                    st.session_state.bt_delete_confirmed = True
                    st.rerun()
            else:
                st.success("✅ Confirmation reçue. Vous pouvez maintenant procéder à la suppression.")
        
        # Boutons d'action
        col_delete, col_cancel = st.columns(2)
        
        with col_delete:
            # Activer le bouton selon le niveau de risque
            delete_enabled = True
            if risk_level == 'HIGH' and not st.session_state.bt_delete_confirmed:
                delete_enabled = False
                button_text = "❌ Confirmation requise"
            else:
                button_text = f"🗑️ SUPPRIMER DÉFINITIVEMENT"
            
            if st.button(
                button_text, 
                type="primary" if delete_enabled else "secondary",
                disabled=not delete_enabled,
                use_container_width=True, 
                key="bt_confirm_delete_final_btn"
            ):
                # Procéder à la suppression
                if gestionnaire.delete_bon_travail(bt_id):
                    st.success(f"✅ Bon de Travail {bt_info['numero_document']} supprimé avec succès !")
                    st.info("🔄 Toutes les données associées (TimeTracker, opérations Kanban) ont été supprimées")
                    
                    # Nettoyer les variables de session
                    st.session_state.bt_confirm_delete = None
                    st.session_state.bt_delete_confirmed = False
                    
                    # Retourner à la liste
                    st.session_state.bt_mode = 'manage'
                    
                    # Recharger la page après un court délai
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la suppression. Veuillez réessayer.")
        
        with col_cancel:
            if st.button("❌ Annuler", use_container_width=True, key="bt_cancel_delete_btn"):
                st.session_state.bt_confirm_delete = None
                st.session_state.bt_delete_confirmed = False
                st.rerun()

def show_bt_management():
    """Interface de gestion des bons de travail avec suppression"""
    gestionnaire = st.session_state.gestionnaire_bt
    
    st.markdown("### 📋 Gestion des Bons de Travail")
    
    # Afficher la confirmation de suppression si nécessaire
    if st.session_state.bt_confirm_delete:
        show_bt_delete_confirmation()
        return  # Ne pas afficher le reste pendant la confirmation
    
    # Récupérer tous les BT
    bons = gestionnaire.get_all_bons_travail()
    
    if not bons:
        st.info("📋 Aucun bon de travail trouvé. Créez votre premier bon !")
        return
    
    # Filtres
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        statuts = ['TOUS'] + list(set(bon['statut'] for bon in bons))
        statut_filter = st.selectbox("Filtrer par statut:", statuts)
    
    with filter_col2:
        priorities = ['TOUTES'] + list(set(bon['priorite'] for bon in bons))
        priority_filter = st.selectbox("Filtrer par priorité:", priorities)
    
    with filter_col3:
        search_term = st.text_input("🔍 Rechercher:", placeholder="Projet, client, numéro...")
    
    # Appliquer les filtres
    filtered_bons = bons
    
    if statut_filter != 'TOUS':
        filtered_bons = [b for b in filtered_bons if b['statut'] == statut_filter]
    
    if priority_filter != 'TOUTES':
        filtered_bons = [b for b in filtered_bons if b['priorite'] == priority_filter]
    
    if search_term:
        search_lower = search_term.lower()
        filtered_bons = [
            b for b in filtered_bons 
            if search_lower in b['numero_document'].lower() 
            or search_lower in b['project_name'].lower()
            or search_lower in b['client_name'].lower()
        ]
    
    st.markdown(f"**{len(filtered_bons)} bon(s) trouvé(s)**")
    
    # Affichage en tableau
    if filtered_bons:
        for bon in filtered_bons:
            with st.expander(f"🔧 {bon['numero_document']} - {bon['project_name']}", expanded=False):
                detail_col1, detail_col2, detail_col3 = st.columns(3)
                
                with detail_col1:
                    st.markdown(f"""
                    **Client:** {bon['client_name']}  
                    **Chargé de projet:** {bon['project_manager']}  
                    **Nb. lignes:** {bon['nb_lignes']}
                    """)
                
                with detail_col2:
                    statut_class = f"status-{bon['statut'].lower().replace(' ', '-').replace('é', 'e')}"
                    priority_class = f"priority-{bon['priorite'].lower()}"
                    
                    st.markdown(f"""
                    **Statut:** <span class="status-badge {statut_class}">{bon['statut']}</span>  
                    **Priorité:** <span class="status-badge {priority_class}">{bon['priorite']}</span>  
                    **Heures prévues:** {bon['total_heures_prevues']:.1f}h
                    """, unsafe_allow_html=True)
                
                with detail_col3:
                    st.markdown(f"""
                    **Créé le:** {bon['date_creation'][:10] if bon['date_creation'] else 'N/A'}  
                    **Échéance:** {bon['date_echeance'] if bon['date_echeance'] else 'N/A'}
                    """)
                
                # Actions
                action_detail_col1, action_detail_col2, action_detail_col3 = st.columns(3)
                
                with action_detail_col1:
                    if st.button("👁️ Voir", key=f"view_{bon['id']}"):
                        form_data = gestionnaire.load_bon_travail(bon['id'])
                        if form_data:
                            st.session_state.bt_current_form_data = form_data
                            st.session_state.bt_mode = 'view'
                            st.session_state.bt_selected_id = bon['id']
                            st.rerun()
                
                with action_detail_col2:
                    if st.button("✏️ Modifier", key=f"edit_{bon['id']}"):
                        form_data = gestionnaire.load_bon_travail(bon['id'])
                        if form_data:
                            st.session_state.bt_current_form_data = form_data
                            st.session_state.bt_mode = 'edit'
                            st.session_state.bt_selected_id = bon['id']
                            st.rerun()
                
                with action_detail_col3:
                    # MISE À JOUR : Bouton suppression fonctionnel
                    if st.button("🗑️ Supprimer", key=f"del_{bon['id']}", type="secondary"):
                        st.session_state.bt_confirm_delete = bon['id']
                        st.session_state.bt_delete_confirmed = False
                        st.rerun()

def show_bt_statistics():
    """Affichage des statistiques des BT"""
    gestionnaire = st.session_state.gestionnaire_bt
    
    st.markdown("### 📊 Statistiques des Bons de Travail")
    
    stats = gestionnaire.get_bt_statistics()
    
    if not stats or stats.get('total_bt', 0) == 0:
        st.info("📊 Aucune donnée statistique disponible")
        return
    
    # Métriques principales
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    
    with metric_col1:
        st.metric("📋 Total BT", stats.get('total_bt', 0))
    
    with metric_col2:
        st.metric("🟢 En cours", stats.get('en_cours', 0))
    
    with metric_col3:
        st.metric("✅ Terminés", stats.get('termines', 0))
    
    with metric_col4:
        st.metric("🔴 Urgents", stats.get('urgents', 0) + stats.get('critiques', 0))
    
    # Graphiques
    if stats.get('total_bt', 0) > 0:
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Graphique par statut
            statut_data = {
                'Statut': ['Brouillons', 'Validés', 'En cours', 'Terminés'],
                'Nombre': [
                    stats.get('brouillons', 0),
                    stats.get('valides', 0), 
                    stats.get('en_cours', 0),
                    stats.get('termines', 0)
                ]
            }
            
            fig_statut = px.pie(
                values=statut_data['Nombre'],
                names=statut_data['Statut'],
                title="📈 Répartition par Statut",
                color_discrete_sequence=['#fef3c7', '#dbeafe', '#e0e7ff', '#d1fae5']
            )
            fig_statut.update_layout(height=400)
            st.plotly_chart(fig_statut, use_container_width=True)
        
        with chart_col2:
            # Graphique par priorité
            priority_data = {
                'Priorité': ['Normal', 'Urgent', 'Critique'],
                'Nombre': [
                    stats.get('total_bt', 0) - stats.get('urgents', 0) - stats.get('critiques', 0),
                    stats.get('urgents', 0),
                    stats.get('critiques', 0)
                ]
            }
            
            fig_priority = px.bar(
                x=priority_data['Priorité'],
                y=priority_data['Nombre'],
                title="📊 Répartition par Priorité",
                color=priority_data['Priorité'],
                color_discrete_map={
                    'Normal': '#10b981',
                    'Urgent': '#f59e0b', 
                    'Critique': '#ef4444'
                }
            )
            fig_priority.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_priority, use_container_width=True)
    
    # Statistiques TimeTracker
    if stats.get('bt_avec_pointages', 0) > 0:
        st.markdown("---")
        st.markdown("### ⏱️ Intégration TimeTracker")
        
        tt_col1, tt_col2, tt_col3, tt_col4 = st.columns(4)
        
        with tt_col1:
            st.metric("🔧 BT avec pointages", stats.get('bt_avec_pointages', 0))
        
        with tt_col2:
            st.metric("📊 Sessions total", stats.get('total_sessions', 0))
        
        with tt_col3:
            st.metric("⏱️ Heures total", f"{stats.get('total_heures', 0):.1f}h")
        
        with tt_col4:
            st.metric("💰 Coût total", f"{stats.get('total_cout', 0):,.0f}$")

# ================== FONCTIONS POSTES DE TRAVAIL ==================

def show_work_centers_navigation():
    """Navigation secondaire pour les postes"""
    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
    
    with nav_col1:
        if st.button("📋 Liste Postes", use_container_width=True,
                     type="primary" if st.session_state.wc_action == 'list' else "secondary",
                     key="wc_nav_list"):
            st.session_state.wc_action = 'list'
            st.session_state.wc_selected_id = None
            st.rerun()
    
    with nav_col2:
        if st.button("➕ Nouveau Poste", use_container_width=True,
                     type="primary" if st.session_state.wc_action == 'create' else "secondary",
                     key="wc_nav_create"):
            st.session_state.wc_action = 'create'
            st.session_state.wc_selected_id = None
            st.rerun()
    
    with nav_col3:
        if st.button("📊 Stats Postes", use_container_width=True,
                     type="primary" if st.session_state.wc_action == 'stats' else "secondary",
                     key="wc_nav_stats"):
            st.session_state.wc_action = 'stats'
            st.rerun()
    
    with nav_col4:
        if st.button("📈 Analyses", use_container_width=True,
                     type="primary" if st.session_state.wc_action == 'analysis' else "secondary",
                     key="wc_nav_analysis"):
            st.session_state.wc_action = 'analysis'
            st.rerun()

def show_work_centers_list():
    """Affiche la liste des postes de travail"""
    st.markdown("### 🏭 Liste des Postes de Travail")
    
    # Récupérer tous les postes
    try:
        postes = st.session_state.erp_db.execute_query('''
            SELECT wc.*, 
                   COUNT(DISTINCT o.id) as nb_operations,
                   COALESCE(SUM(te.total_hours), 0) as total_heures,
                   COALESCE(SUM(te.total_cost), 0) as total_revenus
            FROM work_centers wc
            LEFT JOIN operations o ON wc.id = o.work_center_id
            LEFT JOIN time_entries te ON o.id = te.operation_id AND te.total_cost IS NOT NULL
            GROUP BY wc.id
            ORDER BY wc.nom
        ''')
        postes = [dict(p) for p in postes]
    except Exception as e:
        st.error(f"Erreur chargement postes: {e}")
        return
    
    if not postes:
        st.info("🏭 Aucun poste de travail configuré. Commencez par créer votre premier poste !")
        if st.button("➕ Créer le premier poste", type="primary", key="create_first_wc_btn"):
            st.session_state.wc_action = 'create'
            st.rerun()
        return
    
    # Filtres
    st.markdown("#### 🔍 Filtres")
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        departements = ['TOUS'] + sorted(list(set(p['departement'] for p in postes if p['departement'])))
        dept_filter = st.selectbox("Département:", departements)
    
    with filter_col2:
        categories = ['TOUS'] + sorted(list(set(p['categorie'] for p in postes if p['categorie'])))
        cat_filter = st.selectbox("Catégorie:", categories)
    
    with filter_col3:
        search_term = st.text_input("🔍 Rechercher:", placeholder="Nom, type machine...")
    
    # Appliquer filtres
    postes_filtres = postes
    if dept_filter != 'TOUS':
        postes_filtres = [p for p in postes_filtres if p['departement'] == dept_filter]
    if cat_filter != 'TOUS':
        postes_filtres = [p for p in postes_filtres if p['categorie'] == cat_filter]
    if search_term:
        search_lower = search_term.lower()
        postes_filtres = [p for p in postes_filtres if 
                         search_lower in p['nom'].lower() or 
                         search_lower in (p['type_machine'] or '').lower()]
    
    st.markdown(f"**{len(postes_filtres)} poste(s) trouvé(s)**")
    
    # Affichage des postes
    for poste in postes_filtres:
        with st.container():
            st.markdown('<div class="wc-card">', unsafe_allow_html=True)
            
            # En-tête du poste
            header_col1, header_col2, header_col3 = st.columns([3, 2, 1])
            
            with header_col1:
                # Nom et type
                st.markdown(f"### 🏭 {poste['nom']}")
                st.markdown(f"**Type:** {poste['type_machine'] or 'N/A'}")
                st.markdown(f"**Département:** {poste['departement']} | **Catégorie:** {poste['categorie']}")
            
            with header_col2:
                # Statut
                statut_class = f"wc-status-{poste['statut'].lower()}" if poste['statut'] else "wc-status-actif"
                st.markdown(f'<span class="wc-status-badge {statut_class}">{poste["statut"]}</span>', unsafe_allow_html=True)
                
                # Capacité et opérateurs
                st.markdown(f"**Capacité:** {poste['capacite_theorique']}h/jour")
                st.markdown(f"**Opérateurs:** {poste['operateurs_requis']}")
                st.markdown(f"**Coût:** {poste['cout_horaire']:.0f}$/h")
            
            with header_col3:
                # Métriques d'utilisation
                st.metric("Opérations", poste['nb_operations'])
                st.metric("Heures", f"{poste['total_heures']:.0f}h")
                st.metric("Revenus", f"{poste['total_revenus']:,.0f}$")
            
            # Compétences requises
            if poste['competences_requises']:
                st.markdown(f"**🎯 Compétences:** {poste['competences_requises']}")
            
            # Localisation
            if poste['localisation']:
                st.markdown(f"**📍 Localisation:** {poste['localisation']}")
            
            # Actions
            action_col1, action_col2, action_col3, action_col4 = st.columns(4)
            
            with action_col1:
                if st.button("👁️ Voir", key=f"view_wc_{poste['id']}", use_container_width=True):
                    st.session_state.wc_action = 'view'
                    st.session_state.wc_selected_id = poste['id']
                    st.rerun()
            
            with action_col2:
                if st.button("✏️ Modifier", key=f"edit_wc_{poste['id']}", use_container_width=True):
                    st.session_state.wc_action = 'edit'
                    st.session_state.wc_selected_id = poste['id']
                    st.rerun()
            
            with action_col3:
                if st.button("📊 Analytics", key=f"analytics_wc_{poste['id']}", use_container_width=True):
                    st.session_state.wc_action = 'view_analytics'
                    st.session_state.wc_selected_id = poste['id']
                    st.rerun()
            
            with action_col4:
                if st.button("🗑️ Supprimer", key=f"delete_wc_{poste['id']}", type="secondary", use_container_width=True):
                    st.session_state.wc_confirm_delete = poste['id']
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Confirmation de suppression
    if st.session_state.wc_confirm_delete:
        show_delete_confirmation(st.session_state.wc_confirm_delete)

def show_work_center_form(poste_data=None):
    """Formulaire d'ajout/modification de poste - VERSION CORRIGÉE types numériques"""
    is_edit = poste_data is not None
    title = "✏️ Modifier Poste" if is_edit else "➕ Nouveau Poste"
    
    st.markdown(f"### {title}")
    
    with st.form("work_center_form"):
        # Informations de base
        st.markdown("#### 📋 Informations Générales")
        
        col1, col2 = st.columns(2)
        
        with col1:
            nom = st.text_input(
                "Nom du poste *:", 
                value=poste_data.get('nom', '') if is_edit else '',
                placeholder="Ex: Robot ABB GMAW Station 1"
            )
            
            departements = ['PRODUCTION', 'USINAGE', 'QUALITE', 'LOGISTIQUE', 'MAINTENANCE', 'COMMERCIAL']
            dept_index = departements.index(poste_data['departement']) if is_edit and poste_data.get('departement') in departements else 0
            departement = st.selectbox("Département *:", departements, index=dept_index)
            
            categories = ['ROBOTIQUE', 'CNC', 'MANUEL', 'INSPECTION', 'ASSEMBLAGE', 'FINITION', 'TRANSPORT']
            cat_index = categories.index(poste_data['categorie']) if is_edit and poste_data.get('categorie') in categories else 0
            categorie = st.selectbox("Catégorie *:", categories, index=cat_index)
        
        with col2:
            type_machine = st.text_input(
                "Type de machine:", 
                value=poste_data.get('type_machine', '') if is_edit else '',
                placeholder="Ex: Robot de soudage 6 axes"
            )
            
            capacite_theorique = st.number_input(
                "Capacité théorique (h/jour):", 
                value=float(poste_data.get('capacite_theorique', 8.0)) if is_edit else 8.0,
                min_value=0.1, 
                max_value=24.0, 
                step=0.5
            )
            
            operateurs_requis = st.number_input(
                "Opérateurs requis:", 
                value=int(poste_data.get('operateurs_requis', 1)) if is_edit else 1,
                min_value=1, 
                max_value=10, 
                step=1
            )
        
        # Coûts et statut
        st.markdown("#### 💰 Coûts et Statut")
        
        col3, col4 = st.columns(2)
        
        with col3:
            cout_horaire = st.number_input(
                "Coût horaire ($):", 
                value=float(poste_data.get('cout_horaire', 50.0)) if is_edit else 50.0,
                min_value=0.0, 
                step=5.0
            )
            
            statuts = ['ACTIF', 'MAINTENANCE', 'INACTIF']
            statut_index = statuts.index(poste_data['statut']) if is_edit and poste_data.get('statut') in statuts else 0
            statut = st.selectbox("Statut:", statuts, index=statut_index)
        
        with col4:
            localisation = st.text_input(
                "Localisation:", 
                value=poste_data.get('localisation', '') if is_edit else '',
                placeholder="Ex: Atelier A - Zone 2"
            )
        
        # Compétences
        st.markdown("#### 🎯 Compétences Requises")
        competences_requises = st.text_area(
            "Compétences requises:", 
            value=poste_data.get('competences_requises', '') if is_edit else '',
            placeholder="Ex: Soudage GMAW, Programmation Robot ABB, Lecture de plans",
            height=100
        )
        
        # Boutons
        col_submit, col_cancel = st.columns(2)
        
        with col_submit:
            submitted = st.form_submit_button(
                "💾 Sauvegarder" if is_edit else "➕ Créer Poste", 
                use_container_width=True, type="primary"
            )
        
        with col_cancel:
            cancelled = st.form_submit_button("❌ Annuler", use_container_width=True)
        
        if submitted:
            # Validation
            if not nom:
                st.error("❌ Le nom du poste est obligatoire")
                return
            
            if not departement:
                st.error("❌ Le département est obligatoire")
                return
            
            # Données du poste
            work_center_data = {
                'nom': nom,
                'departement': departement,
                'categorie': categorie,
                'type_machine': type_machine,
                'capacite_theorique': capacite_theorique,
                'operateurs_requis': operateurs_requis,
                'cout_horaire': cout_horaire,
                'competences_requises': competences_requises,
                'statut': statut,
                'localisation': localisation
            }
            
            try:
                if is_edit:
                    # Modification
                    success = st.session_state.erp_db.update_work_center(
                        st.session_state.wc_selected_id, 
                        work_center_data
                    )
                    if success:
                        st.success(f"✅ Poste {nom} modifié avec succès !")
                        st.session_state.wc_action = 'list'
                        st.session_state.wc_selected_id = None
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la modification")
                else:
                    # Création
                    poste_id = st.session_state.erp_db.add_work_center(work_center_data)
                    if poste_id:
                        st.success(f"✅ Poste {nom} créé avec succès ! ID: {poste_id}")
                        st.session_state.wc_action = 'list'
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la création")
                        
            except Exception as e:
                st.error(f"❌ Erreur: {e}")
        
        if cancelled:
            st.session_state.wc_action = 'list'
            st.session_state.wc_selected_id = None
            st.rerun()

def show_work_center_details(poste_id):
    """Affiche les détails d'un poste"""
    try:
        poste = st.session_state.erp_db.get_work_center_by_id(poste_id)
        if not poste:
            st.error("❌ Poste non trouvé")
            return
        
        st.markdown(f"### 👁️ Détails - {poste['nom']}")
        
        # Informations générales
        st.markdown('<div class="wc-card">', unsafe_allow_html=True)
        
        detail_col1, detail_col2, detail_col3 = st.columns(3)
        
        with detail_col1:
            st.markdown("#### 📋 Informations")
            st.markdown(f"**Nom:** {poste['nom']}")
            st.markdown(f"**Département:** {poste['departement']}")
            st.markdown(f"**Catégorie:** {poste['categorie']}")
            st.markdown(f"**Type:** {poste.get('type_machine', 'N/A')}")
            st.markdown(f"**Localisation:** {poste.get('localisation', 'N/A')}")
        
        with detail_col2:
            st.markdown("#### ⚙️ Capacités")
            st.markdown(f"**Capacité:** {poste['capacite_theorique']}h/jour")
            st.markdown(f"**Opérateurs:** {poste['operateurs_requis']}")
            st.markdown(f"**Coût horaire:** {poste['cout_horaire']:.0f}$/h")
            
            statut_class = f"wc-status-{poste['statut'].lower()}"
            st.markdown(f"**Statut:** <span class='wc-status-badge {statut_class}'>{poste['statut']}</span>", unsafe_allow_html=True)
        
        with detail_col3:
            st.markdown("#### 📊 Utilisation")
            st.markdown(f"**Opérations:** {poste.get('operations_count', 0)}")
            st.markdown(f"**Heures totales:** {poste.get('total_hours_tracked', 0):.0f}h")
            st.markdown(f"**Revenus générés:** {poste.get('total_revenue_generated', 0):,.0f}$")
            st.markdown(f"**Employés uniques:** {poste.get('unique_employees_used', 0)}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Compétences
        if poste.get('competences_requises'):
            st.markdown("#### 🎯 Compétences Requises")
            st.info(poste['competences_requises'])
        
        # Actions
        action_col1, action_col2 = st.columns(2)
        
        with action_col1:
            if st.button("✏️ Modifier ce poste", use_container_width=True, type="primary", key="edit_this_wc_btn"):
                st.session_state.wc_action = 'edit'
                st.rerun()
        
        with action_col2:
            if st.button("📋 Retour à la liste", use_container_width=True, key="back_to_wc_list_btn"):
                st.session_state.wc_action = 'list'
                st.session_state.wc_selected_id = None
                st.rerun()
        
    except Exception as e:
        st.error(f"❌ Erreur chargement détails: {e}")

def show_work_centers_statistics():
    """Affiche les statistiques des postes de travail"""
    st.markdown("### 📊 Statistiques des Postes de Travail")
    
    try:
        stats = st.session_state.erp_db.get_work_centers_statistics()
        
        if not stats or stats.get('total_work_centers', 0) == 0:
            st.info("📊 Aucune donnée statistique disponible")
            return
        
        # Métriques principales
        st.markdown("#### 🎯 Vue d'Ensemble")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🏭 Total Postes", stats.get('total_work_centers', 0))
        
        with col2:
            actifs = stats.get('by_status', {}).get('ACTIF', 0)
            st.metric("⚡ Postes Actifs", actifs)
        
        with col3:
            capacite = stats.get('capacity_analysis', {}).get('capacite_totale_heures_jour', 0)
            st.metric("🕐 Capacité Totale", f"{capacite:.0f}h/j")
        
        with col4:
            cout_total = stats.get('capacity_analysis', {}).get('cout_total_theorique_jour', 0)
            st.metric("💰 Coût Théorique", f"{cout_total:,.0f}$/j")
        
        # Graphiques
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Répartition par département
            dept_data = stats.get('by_department', {})
            if dept_data:
                dept_names = list(dept_data.keys())
                dept_counts = [dept_data[dept]['count'] for dept in dept_names]
                
                fig_dept = px.pie(
                    values=dept_counts,
                    names=dept_names,
                    title="📊 Répartition par Département",
                    color_discrete_sequence=['#00A971', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']
                )
                fig_dept.update_layout(height=400)
                st.plotly_chart(fig_dept, use_container_width=True)
        
        with chart_col2:
            # Répartition par catégorie
            cat_data = stats.get('by_category', {})
            if cat_data:
                cat_names = list(cat_data.keys())
                cat_counts = [cat_data[cat]['count'] for cat in cat_names]
                
                fig_cat = px.bar(
                    x=cat_names,
                    y=cat_counts,
                    title="📈 Répartition par Catégorie",
                    color=cat_names,
                    color_discrete_sequence=['#00A971', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']
                )
                fig_cat.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_cat, use_container_width=True)
        
        # Intégration TimeTracker
        tt_stats = stats.get('timetracker_integration', {})
        if tt_stats and tt_stats.get('total_pointages', 0) > 0:
            st.markdown("#### ⏱️ Intégration TimeTracker")
            
            tt_col1, tt_col2, tt_col3, tt_col4 = st.columns(4)
            
            with tt_col1:
                st.metric("Postes avec pointages", tt_stats.get('postes_avec_pointages', 0))
            with tt_col2:
                st.metric("Total pointages", tt_stats.get('total_pointages', 0))
            with tt_col3:
                st.metric("Heures totales", f"{tt_stats.get('total_heures', 0):.0f}h")
            with tt_col4:
                st.metric("Employés distincts", tt_stats.get('employes_ayant_pointe', 0))
        
    except Exception as e:
        st.error(f"❌ Erreur statistiques: {e}")

def show_work_centers_analysis():
    """Analyse avancée des postes de travail"""
    st.markdown("### 📈 Analyses Avancées")
    
    analysis_tab1, analysis_tab2 = st.tabs(["🔍 Analyse d'Utilisation", "⚠️ Goulots d'Étranglement"])
    
    with analysis_tab1:
        show_utilization_analysis()
    
    with analysis_tab2:
        show_bottleneck_analysis()

def show_utilization_analysis():
    """Analyse d'utilisation des postes"""
    st.markdown("#### 🔍 Analyse d'Utilisation")
    
    # Sélection de période
    period_days = st.selectbox("📅 Période d'analyse:", [7, 14, 30, 90], index=2)
    
    try:
        analysis = st.session_state.erp_db.get_work_center_utilization_analysis(period_days)
        
        if not analysis:
            st.info("📊 Aucune donnée d'utilisation disponible")
            return
        
        # Tableau d'analyse
        df_data = []
        for wc in analysis:
            df_data.append({
                'Poste': wc['nom'],
                'Département': wc['departement'],
                'Catégorie': wc['categorie'],
                'Capacité (h/j)': wc['capacite_theorique'],
                'Heures Réelles': f"{wc['heures_reelles']:.1f}h",
                'Utilisation %': f"{wc['taux_utilisation_pct']:.1f}%",
                'Classification': wc['classification_utilisation'],
                'Revenus': f"{wc['revenus_generes']:,.0f}$",
                'Employés': wc['employes_distincts'],
                'Projets': wc['projets_touches']
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Graphique d'utilisation
            fig_util = px.bar(
                df, 
                x='Poste', 
                y='Utilisation %',
                color='Classification',
                title=f"Taux d'Utilisation des Postes ({period_days} derniers jours)",
                color_discrete_map={
                    'TRÈS_FAIBLE': '#ef4444',
                    'FAIBLE': '#f59e0b', 
                    'MOYENNE': '#3b82f6',
                    'ÉLEVÉE': '#10b981'
                }
            )
            fig_util.update_layout(height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig_util, use_container_width=True)
    
    except Exception as e:
        st.error(f"❌ Erreur analyse utilisation: {e}")

def show_bottleneck_analysis():
    """Analyse des goulots d'étranglement"""
    st.markdown("#### ⚠️ Goulots d'Étranglement")
    
    try:
        bottlenecks = st.session_state.erp_db.get_work_center_capacity_bottlenecks()
        
        if not bottlenecks:
            st.success("✅ Aucun goulot d'étranglement détecté ! Votre production est bien équilibrée.")
            return
        
        # Affichage des goulots
        for bottleneck in bottlenecks:
            level = bottleneck['niveau_goulot']
            
            # Couleur selon le niveau
            if level == 'CRITIQUE':
                alert_type = 'error'
                icon = '🚨'
            elif level == 'ÉLEVÉ':
                alert_type = 'warning'
                icon = '⚠️'
            else:
                alert_type = 'info'
                icon = '📊'
            
            with st.container():
                if alert_type == 'error':
                    st.error(f"""
                    {icon} **GOULOT CRITIQUE** - {bottleneck['nom']}
                    
                    - **Charge:** {bottleneck['taux_charge_planifiee_pct']:.1f}% 
                    - **Opérations en attente:** {bottleneck['operations_en_attente']}
                    - **Pointages actifs:** {bottleneck['pointages_actifs']}
                    - **Département:** {bottleneck['departement']}
                    """)
                elif alert_type == 'warning':
                    st.warning(f"""
                    {icon} **GOULOT ÉLEVÉ** - {bottleneck['nom']}
                    
                    - **Charge:** {bottleneck['taux_charge_planifiee_pct']:.1f}%
                    - **Opérations en attente:** {bottleneck['operations_en_attente']}
                    - **Département:** {bottleneck['departement']}
                    """)
                else:
                    st.info(f"""
                    {icon} **Charge Modérée** - {bottleneck['nom']}
                    
                    - **Charge:** {bottleneck['taux_charge_planifiee_pct']:.1f}%
                    - **Département:** {bottleneck['departement']}
                    """)
                
                # Recommandations
                if bottleneck.get('recommandations'):
                    st.markdown("**🎯 Recommandations:**")
                    for rec in bottleneck['recommandations']:
                        st.markdown(f"- {rec}")
        
        # Graphique des charges
        if bottlenecks:
            bottleneck_names = [b['nom'] for b in bottlenecks]
            bottleneck_charges = [b['taux_charge_planifiee_pct'] for b in bottlenecks]
            bottleneck_levels = [b['niveau_goulot'] for b in bottlenecks]
            
            fig_bottleneck = px.bar(
                x=bottleneck_names,
                y=bottleneck_charges,
                color=bottleneck_levels,
                title="📊 Analyse des Goulots d'Étranglement",
                labels={'x': 'Postes', 'y': 'Charge (%)'},
                color_discrete_map={
                    'CRITIQUE': '#ef4444',
                    'ÉLEVÉ': '#f59e0b',
                    'MODÉRÉ': '#3b82f6',
                    'FAIBLE': '#10b981'
                }
            )
            fig_bottleneck.add_hline(y=100, line_dash="dash", line_color="red", 
                                   annotation_text="Capacité Maximum")
            fig_bottleneck.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_bottleneck, use_container_width=True)
    
    except Exception as e:
        st.error(f"❌ Erreur analyse goulots: {e}")

def show_delete_confirmation(poste_id):
    """Confirmation de suppression"""
    try:
        poste = st.session_state.erp_db.get_work_center_by_id(poste_id)
        if not poste:
            st.session_state.wc_confirm_delete = None
            return
        
        st.error(f"""
        ⚠️ **CONFIRMATION DE SUPPRESSION**
        
        Êtes-vous sûr de vouloir supprimer le poste **{poste['nom']}** ?
        
        Cette action est **irréversible** et supprimera :
        - Le poste de travail
        - Toutes les opérations associées
        - Toutes les réservations
        
        **⚠️ ATTENTION :** Cette action peut affecter vos projets en cours !
        """)
        
        col_confirm, col_cancel = st.columns(2)
        
        with col_confirm:
            if st.button("🗑️ CONFIRMER LA SUPPRESSION", type="primary", use_container_width=True, key="confirm_delete_wc_btn"):
                try:
                    if st.session_state.erp_db.delete_work_center(poste_id):
                        st.success(f"✅ Poste {poste['nom']} supprimé avec succès !")
                        st.session_state.wc_confirm_delete = None
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la suppression")
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
        
        with col_cancel:
            if st.button("❌ Annuler", use_container_width=True, key="cancel_delete_wc_btn"):
                st.session_state.wc_confirm_delete = None
                st.rerun()
    
    except Exception as e:
        st.error(f"❌ Erreur: {e}")

# ================== FONCTION PRINCIPALE ==================

def show_production_management_page():
    """
    Page principale du module de gestion des bons de travail et postes de travail
    VERSION NETTOYÉE : Navigation simplifiée et code organisé
    - Suppression des éléments debug et TimeTracker
    - Navigation principale simplifiée (3 boutons au lieu de 6)
    - Code nettoyé et maintien de toutes les fonctionnalités essentielles
    """
    
    # Appliquer les styles DG
    apply_dg_styles()
    
    # Initialiser les gestionnaires si nécessaires
    if 'gestionnaire_bt' not in st.session_state:
        if 'erp_db' in st.session_state:
            st.session_state.gestionnaire_bt = GestionnaireBonsTravail(st.session_state.erp_db)
        else:
            st.error("❌ Base de données ERP non disponible")
            return
    
    if 'gestionnaire_postes' not in st.session_state:
        if 'erp_db' in st.session_state:
            st.session_state.gestionnaire_postes = GestionnairePostes(st.session_state.erp_db)
        else:
            st.error("❌ Base de données ERP non disponible")
            return
    
    # Afficher l'en-tête DG
    show_dg_header()
    
    # Navigation principale simplifiée
    show_main_navigation()
    
    # Gestion des messages de succès
    if st.session_state.get('bt_show_success'):
        st.success("✅ Bon de Travail sauvegardé avec succès!")
        st.session_state.bt_show_success = False
    
    # Affichage selon le mode principal
    main_mode = st.session_state.get('main_mode', 'bt')
    
    if main_mode == 'bt':
        # Mode Bons de Travail
        show_bt_navigation()
        
        bt_mode = st.session_state.get('bt_mode', 'create')
        
        if bt_mode in ['create', 'edit', 'view']:
            # Mode formulaire
            if bt_mode == 'view':
                st.info("👁️ Mode visualisation - Formulaire en lecture seule")
            
            with st.container():
                show_bt_form_section()
                show_tasks_section()
                show_materials_section() 
                show_instructions_section()
                show_bt_actions()
        
        elif bt_mode == 'manage':
            # Mode gestion BT
            show_bt_management()
        
        elif bt_mode == 'stats':
            # Mode statistiques BT
            show_bt_statistics()
    
    elif main_mode == 'postes':
        # Mode Postes de Travail
        show_work_centers_navigation()
        
        wc_action = st.session_state.get('wc_action', 'list')
        
        if wc_action == 'list':
            show_work_centers_list()
        
        elif wc_action == 'create':
            show_work_center_form()
        
        elif wc_action == 'edit':
            if st.session_state.wc_selected_id:
                try:
                    poste_data = st.session_state.erp_db.get_work_center_by_id(st.session_state.wc_selected_id)
                    if poste_data:
                        show_work_center_form(poste_data)
                    else:
                        st.error("❌ Poste non trouvé")
                        st.session_state.wc_action = 'list'
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
                    st.session_state.wc_action = 'list'
            else:
                st.session_state.wc_action = 'list'
                st.rerun()
        
        elif wc_action == 'view':
            if st.session_state.wc_selected_id:
                show_work_center_details(st.session_state.wc_selected_id)
            else:
                st.session_state.wc_action = 'list'
                st.rerun()
        
        elif wc_action == 'stats':
            show_work_centers_statistics()
        
        elif wc_action == 'analysis':
            show_work_centers_analysis()
    
    # Footer DG simplifié
    st.markdown("---")
    
    # Message selon le mode
    if main_mode == 'bt':
        footer_message = "📋 Bons de Travail"
        footer_color = "var(--text-color-light)"
    else:
        footer_message = "🏭 Postes de Travail"
        footer_color = "var(--text-color-light)"
    
    st.markdown(f"""
    <div style='text-align:center;color:{footer_color};padding:20px 0;'>
        <p><strong>🏭 Desmarais & Gagné Inc.</strong> - Système de Gestion Production</p>
        <p>📞 (450) 372-9630 | 📧 info@dg-inc.com | 🌐 Interface intégrée ERP Production</p>
        <p><em>Mode actuel: {footer_message}</em></p>
        {f'<p><strong>🔄 Synchronisation Kanban:</strong> {"✅ Automatique" if main_mode == "bt" else "N/A"}</p>' if main_mode == 'bt' else ''}
        {f'<p><strong>📄 Export PDF:</strong> {"✅ Disponible" if PDF_EXPORT_AVAILABLE else "❌ Non disponible"}</p>' if main_mode == 'bt' else ''}
    </div>
    """, unsafe_allow_html=True)

# Point d'entrée principal
if __name__ == "__main__":
    show_production_management_page()
