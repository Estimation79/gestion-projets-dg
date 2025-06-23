# production_management.py - Gestion des Bons de Travail - Desmarais & Gagné Inc.
# MISE À JOUR MAJEURE : Intégration complète avec erp_database.py
# NOUVEAUTÉ : Utilisation des employés, clients, projets et postes de travail de la base ERP
# Interface inspirée du fichier Bons_travail R00.html

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import json
import uuid
from typing import Dict, List, Optional, Any
import logging

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GestionnaireBonsTravail:
    """
    Gestionnaire principal pour les Bons de Travail
    AMÉLIORÉ : Intégration complète avec ERP Database
    Reproduit les fonctionnalités du fichier HTML en version Streamlit avec données ERP
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

    # NOUVEAU : Méthodes d'intégration ERP complètes
    def get_employees_from_db(self) -> List[Dict]:
        """Récupère les employés actifs depuis la base ERP"""
        try:
            query = '''
                SELECT id, prenom, nom, poste, departement, statut
                FROM employees 
                WHERE statut = 'ACTIF'
                ORDER BY prenom, nom
            '''
            employees = self.db.execute_query(query)
            return [dict(emp) for emp in employees]
        except Exception as e:
            logger.error(f"Erreur récupération employés: {e}")
            return []
    
    def get_projects_from_db(self) -> List[Dict]:
        """Récupère les projets depuis la base ERP"""
        try:
            query = '''
                SELECT p.id, p.nom_projet, p.client_nom_cache, p.statut, p.priorite,
                       p.client_company_id, c.nom as client_company_nom
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE p.statut NOT IN ('TERMINÉ', 'ANNULÉ')
                ORDER BY p.nom_projet
            '''
            projects = self.db.execute_query(query)
            return [dict(proj) for proj in projects]
        except Exception as e:
            logger.error(f"Erreur récupération projets: {e}")
            return []
    
    def get_companies_from_db(self) -> List[Dict]:
        """Récupère les entreprises/clients depuis la base CRM"""
        try:
            query = '''
                SELECT id, nom, secteur, type_company, adresse
                FROM companies 
                WHERE type_company IN ('CLIENT', 'PROSPECT', 'FOURNISSEUR')
                ORDER BY nom
            '''
            companies = self.db.execute_query(query)
            return [dict(comp) for comp in companies]
        except Exception as e:
            logger.error(f"Erreur récupération entreprises: {e}")
            return []
    
    def get_work_centers_from_db(self) -> List[Dict]:
        """Récupère les postes de travail depuis la base ERP"""
        try:
            query = '''
                SELECT id, nom, departement, categorie, type_machine, statut
                FROM work_centers 
                WHERE statut = 'ACTIF'
                ORDER BY departement, nom
            '''
            work_centers = self.db.execute_query(query)
            return [dict(wc) for wc in work_centers]
        except Exception as e:
            logger.error(f"Erreur récupération postes: {e}")
            return []

    def get_empty_bt_form(self) -> Dict:
        """Retourne un formulaire BT vide avec support ERP"""
        today = datetime.now().strftime('%Y-%m-%d')
        return {
            'numero_document': self.generate_bt_number(),
            'project_id': None,  # NOUVEAU: ID du projet ERP
            'project_name': '',
            'client_id': None,   # NOUVEAU: ID du client ERP
            'client_name': '',
            'project_manager_id': None,  # NOUVEAU: ID de l'employé ERP
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
        """Retourne une tâche vide avec support ERP"""
        return {
            'operation': '',
            'work_center_id': None,  # NOUVEAU: ID du poste de travail ERP
            'description': '',
            'quantity': 1,
            'planned_hours': 0.0,
            'actual_hours': 0.0,
            'assigned_to_id': None,  # NOUVEAU: ID de l'employé assigné ERP
            'assigned_to': '',
            'status': 'pending',
            'start_date': '',
            'end_date': ''
        }
    
    def get_empty_material(self) -> Dict:
        """Retourne un matériau vide"""
        return {
            'name': '',
            'description': '',
            'quantity': 1.0,
            'unit': 'pcs',
            'available': 'yes',
            'notes': ''
        }
    
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
        """Sauvegarde un bon de travail dans la base - AMÉLIORÉ avec intégration ERP complète"""
        try:
            # Créer le formulaire principal avec liens ERP
            formulaire_data = {
                'type_formulaire': 'BON_TRAVAIL',
                'numero_document': form_data['numero_document'],
                'project_id': form_data.get('project_id'),  # NOUVEAU: Lien vers projet ERP
                'company_id': form_data.get('client_id'),   # NOUVEAU: Lien vers client ERP
                'employee_id': form_data.get('project_manager_id'),  # NOUVEAU: Lien vers employé ERP
                'statut': 'BROUILLON',
                'priorite': form_data['priority'],
                'date_echeance': form_data['end_date'],
                'notes': form_data.get('work_instructions', ''),
                'metadonnees_json': json.dumps({
                    'project_name': form_data['project_name'],
                    'client_name': form_data['client_name'],
                    'project_manager': form_data['project_manager'],
                    'start_date': form_data['start_date'],
                    'safety_notes': form_data.get('safety_notes', ''),
                    'quality_requirements': form_data.get('quality_requirements', ''),
                    'created_by': form_data.get('created_by', 'Utilisateur')
                })
            }
            
            # Insérer le formulaire avec liens ERP
            bt_id = self.db.execute_insert('''
                INSERT INTO formulaires 
                (type_formulaire, numero_document, project_id, company_id, employee_id,
                 statut, priorite, date_echeance, notes, metadonnees_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                formulaire_data['type_formulaire'],
                formulaire_data['numero_document'], 
                formulaire_data.get('project_id'),
                formulaire_data.get('company_id'),
                formulaire_data.get('employee_id'),
                formulaire_data['statut'],
                formulaire_data['priorite'],
                formulaire_data['date_echeance'],
                formulaire_data['notes'],
                formulaire_data['metadonnees_json']
            ))
            
            if not bt_id:
                return None
            
            # NOUVEAU: Créer les opérations dans la table operations si un projet est lié
            if form_data.get('project_id'):
                for i, task in enumerate(form_data.get('tasks', []), 1):
                    if task['description']:
                        # Créer une opération liée au BT
                        operation_id = self.db.execute_insert('''
                            INSERT INTO operations 
                            (project_id, work_center_id, formulaire_bt_id, sequence_number, 
                             description, temps_estime, ressource, statut, poste_travail)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            form_data['project_id'],
                            task.get('work_center_id'),
                            bt_id,
                            i,
                            f"{task['operation']} - {task['description']}", 
                            task['planned_hours'],
                            task['assigned_to'],
                            'À FAIRE',
                            task['operation']
                        ))
                        
                        # NOUVEAU: Assigner l'employé au BT si spécifié
                        if task.get('assigned_to_id'):
                            self.db.execute_insert('''
                                INSERT INTO bt_assignations (bt_id, employe_id, notes_assignation)
                                VALUES (?, ?, ?)
                            ''', (bt_id, task['assigned_to_id'], f"Assigné à la tâche: {task['description']}"))
                        
                        # NOUVEAU: Réserver le poste de travail si spécifié
                        if task.get('work_center_id') and task.get('start_date'):
                            self.db.execute_insert('''
                                INSERT INTO bt_reservations_postes (bt_id, work_center_id, date_prevue, notes_reservation)
                                VALUES (?, ?, ?, ?)
                            ''', (bt_id, task['work_center_id'], task['start_date'], f"Réservé pour: {task['operation']}"))
            
            # Sauvegarder les tâches comme lignes de formulaire (système existant)
            for i, task in enumerate(form_data.get('tasks', []), 1):
                if task['description']:
                    self.db.execute_insert('''
                        INSERT INTO formulaire_lignes 
                        (formulaire_id, sequence_ligne, description, quantite, prix_unitaire, notes_ligne)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        bt_id, i, 
                        f"{task['operation']} - {task['description']}", 
                        task['quantity'], 
                        task['planned_hours'],
                        json.dumps({
                            'operation': task['operation'],
                            'work_center_id': task.get('work_center_id'),
                            'assigned_to_id': task.get('assigned_to_id'),
                            'actual_hours': task['actual_hours'],
                            'assigned_to': task['assigned_to'],
                            'status': task['status'],
                            'start_date': task.get('start_date', ''),
                            'end_date': task.get('end_date', '')
                        })
                    ))
            
            # Sauvegarder les matériaux comme lignes spéciales
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
                            'available': material['available'],
                            'notes': material.get('notes', '')
                        })
                    ))
            
            # Enregistrer l'action dans l'historique
            self.db.execute_insert('''
                INSERT INTO formulaire_validations
                (formulaire_id, employee_id, type_validation, commentaires)
                VALUES (?, ?, 'CREATION', ?)
            ''', (bt_id, form_data.get('project_manager_id'), f"Bon de Travail créé par {form_data.get('created_by', 'Utilisateur')}"))
            
            logger.info(f"Bon de Travail {formulaire_data['numero_document']} sauvegardé avec ID {bt_id}")
            return bt_id
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde BT: {e}")
            return None
    
    def load_bon_travail(self, bt_id: int) -> Optional[Dict]:
        """Charge un bon de travail depuis la base - AMÉLIORÉ avec intégration ERP"""
        try:
            # Récupérer le formulaire principal avec informations ERP
            bt_result = self.db.execute_query('''
                SELECT f.*, 
                       p.nom_projet as project_name_db,
                       c.nom as client_name_db,
                       e.prenom || ' ' || e.nom as project_manager_db
                FROM formulaires f
                LEFT JOIN projects p ON f.project_id = p.id
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN employees e ON f.employee_id = e.id
                WHERE f.id = ? AND f.type_formulaire = 'BON_TRAVAIL'
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
                    desc = ligne_data['description']
                    if desc.startswith('MATERIAU: '):
                        desc = desc[10:]
                    
                    name_desc = desc.split(' - ', 1)
                    material = {
                        'name': name_desc[0] if name_desc else desc,
                        'description': name_desc[1] if len(name_desc) > 1 else '',
                        'quantity': ligne_data.get('quantite', 1.0),
                        'unit': ligne_data.get('unite', 'pcs'),
                        'available': notes_data.get('available', 'yes'),
                        'notes': notes_data.get('notes', '')
                    }
                    materials.append(material)
                    
                else:  # Tâches
                    desc = ligne_data['description']
                    op_desc = desc.split(' - ', 1)
                    
                    task = {
                        'operation': op_desc[0] if op_desc else '',
                        'work_center_id': notes_data.get('work_center_id'),  # NOUVEAU
                        'description': op_desc[1] if len(op_desc) > 1 else desc,
                        'quantity': ligne_data.get('quantite', 1),
                        'planned_hours': ligne_data.get('prix_unitaire', 0.0),
                        'actual_hours': notes_data.get('actual_hours', 0.0),
                        'assigned_to_id': notes_data.get('assigned_to_id'),  # NOUVEAU
                        'assigned_to': notes_data.get('assigned_to', ''),
                        'status': notes_data.get('status', 'pending'),
                        'start_date': notes_data.get('start_date', ''),
                        'end_date': notes_data.get('end_date', '')
                    }
                    tasks.append(task)
            
            # Construire le formulaire complet avec données ERP
            form_data = {
                'id': bt_data['id'],
                'numero_document': bt_data['numero_document'],
                'project_id': bt_data.get('project_id'),  # NOUVEAU
                'project_name': bt_data.get('project_name_db') or metadonnees.get('project_name', ''),
                'client_id': bt_data.get('company_id'),    # NOUVEAU
                'client_name': bt_data.get('client_name_db') or metadonnees.get('client_name', ''),
                'project_manager_id': bt_data.get('employee_id'),  # NOUVEAU
                'project_manager': bt_data.get('project_manager_db') or metadonnees.get('project_manager', ''),
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
        """Récupère tous les bons de travail avec informations ERP"""
        try:
            results = self.db.execute_query('''
                SELECT f.*, 
                       p.nom_projet as project_name_db,
                       c.nom as client_name_db,
                       e.prenom || ' ' || e.nom as project_manager_db,
                       COUNT(fl.id) as nb_lignes,
                       COALESCE(SUM(CASE WHEN fl.sequence_ligne < 1000 THEN fl.prix_unitaire ELSE 0 END), 0) as total_heures_prevues
                FROM formulaires f
                LEFT JOIN projects p ON f.project_id = p.id
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN employees e ON f.employee_id = e.id
                LEFT JOIN formulaire_lignes fl ON f.id = fl.formulaire_id
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                GROUP BY f.id
                ORDER BY f.created_at DESC
            ''')
            
            bons = []
            for row in results:
                row_data = dict(row)
                
                # Parser les métadonnées pour fallback
                metadonnees = {}
                try:
                    metadonnees = json.loads(row_data.get('metadonnees_json', '{}'))
                except:
                    pass
                
                bon = {
                    'id': row_data['id'],
                    'numero_document': row_data['numero_document'],
                    'project_id': row_data.get('project_id'),
                    'project_name': row_data.get('project_name_db') or metadonnees.get('project_name', 'N/A'),
                    'client_id': row_data.get('company_id'),
                    'client_name': row_data.get('client_name_db') or metadonnees.get('client_name', 'N/A'),
                    'project_manager': row_data.get('project_manager_db') or metadonnees.get('project_manager', 'Non assigné'),
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

def apply_dg_styles():
    """Applique les styles DG Inc. cohérents avec le HTML"""
    st.markdown("""
    <style>
    /* Variables DG Inc. */
    :root {
        --primary-color: #00A971;
        --primary-color-darker: #00673D;
        --primary-color-darkest: #004C2E;
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
    
    /* Info boxes ERP */
    .erp-info-box {
        background: linear-gradient(to right, #e6f7f1, #f0fdf4);
        border: 1px solid var(--primary-color);
        border-radius: var(--border-radius-md);
        padding: 12px;
        margin: 8px 0;
        font-size: 14px;
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

def show_bt_navigation():
    """Navigation principale comme dans le HTML"""
    st.markdown('<div class="dg-nav-container">', unsafe_allow_html=True)
    
    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
    
    with nav_col1:
        if st.button("🔧 Nouveau Bon de Travail", use_container_width=True, type="primary"):
            st.session_state.bt_mode = 'create'
            st.session_state.bt_current_form_data = st.session_state.gestionnaire_bt.get_empty_bt_form()
            st.session_state.bt_selected_id = None
            st.rerun()
    
    with nav_col2:
        if st.button("📋 Gestion des Bons", use_container_width=True):
            st.session_state.bt_mode = 'manage'
            st.rerun()
    
    with nav_col3:
        if st.button("📊 Statistiques", use_container_width=True):
            st.session_state.bt_mode = 'stats'
            st.rerun()
    
    with nav_col4:
        if st.button("⏱️ TimeTracker Pro", use_container_width=True):
            st.session_state.page_redirect = "timetracker_pro_page"
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_bt_form_section():
    """Section principale du formulaire BT - AMÉLIORÉE avec intégration ERP complète"""
    gestionnaire = st.session_state.gestionnaire_bt
    form_data = st.session_state.bt_current_form_data
    
    # Titre de section
    mode_text = "Modifier" if st.session_state.bt_mode == 'edit' else "Créer"
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
            # AMÉLIORATION: Sélection de projet depuis la base ERP
            projects = gestionnaire.get_projects_from_db()
            if projects:
                project_options = [{'id': None, 'display': '-- Nouveau projet --'}] + [
                    {'id': p['id'], 'display': f"{p['nom_projet']} ({p['client_nom_cache'] or p['client_company_nom'] or 'N/A'})"}
                    for p in projects
                ]
                
                # Trouver l'index actuel
                current_project_id = form_data.get('project_id')
                project_index = 0
                for i, option in enumerate(project_options):
                    if option['id'] == current_project_id:
                        project_index = i
                        break
                
                selected_project = st.selectbox(
                    "Projet ERP:",
                    options=range(len(project_options)),
                    index=project_index,
                    format_func=lambda i: project_options[i]['display']
                )
                
                selected_project_data = project_options[selected_project]
                
                if selected_project_data['id']:
                    # Projet existant sélectionné
                    form_data['project_id'] = selected_project_data['id']
                    selected_proj = next(p for p in projects if p['id'] == selected_project_data['id'])
                    form_data['project_name'] = selected_proj['nom_projet']
                    form_data['client_name'] = selected_proj['client_nom_cache'] or selected_proj['client_company_nom'] or ''
                    form_data['client_id'] = selected_proj.get('client_company_id')
                    
                    # Afficher les infos du projet sélectionné
                    st.markdown(f"""
                    <div class="erp-info-box">
                        📋 <strong>Projet:</strong> {selected_proj['nom_projet']} | 
                        🏢 <strong>Client:</strong> {form_data['client_name']} | 
                        🚦 <strong>Statut:</strong> {selected_proj['statut']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Nouveau projet
                    form_data['project_id'] = None
                    form_data['project_name'] = st.text_input(
                        "Nom du projet *:", 
                        value=form_data.get('project_name', ''),
                        placeholder="Nom du nouveau projet"
                    )
                    
                    # AMÉLIORATION: Sélection de client depuis la base CRM
                    companies = gestionnaire.get_companies_from_db()
                    if companies:
                        client_options = [{'id': None, 'display': '-- Sélectionner un client --'}] + [
                            {'id': c['id'], 'display': f"{c['nom']} ({c['type_company']})"}
                            for c in companies
                        ]
                        
                        current_client_id = form_data.get('client_id')
                        client_index = 0
                        for i, option in enumerate(client_options):
                            if option['id'] == current_client_id:
                                client_index = i
                                break
                        
                        selected_client = st.selectbox(
                            "Client ERP:",
                            options=range(len(client_options)),
                            index=client_index,
                            format_func=lambda i: client_options[i]['display']
                        )
                        
                        selected_client_data = client_options[selected_client]
                        
                        if selected_client_data['id']:
                            form_data['client_id'] = selected_client_data['id']
                            selected_comp = next(c for c in companies if c['id'] == selected_client_data['id'])
                            form_data['client_name'] = selected_comp['nom']
                        else:
                            form_data['client_id'] = None
                            form_data['client_name'] = st.text_input(
                                "Nom du client *:", 
                                value=form_data.get('client_name', ''),
                                placeholder="Nom du nouveau client"
                            )
                    else:
                        form_data['client_name'] = st.text_input(
                            "Client *:", 
                            value=form_data.get('client_name', ''),
                            placeholder="Nom du client"
                        )
            else:
                # Pas de projets ERP, utiliser les champs libres
                form_data['project_name'] = st.text_input(
                    "Nom du projet *:", 
                    value=form_data.get('project_name', ''),
                    placeholder="Nom du projet"
                )
                
                form_data['client_name'] = st.text_input(
                    "Client *:", 
                    value=form_data.get('client_name', ''),
                    placeholder="Nom du client"
                )
            
            # AMÉLIORATION: Sélection du chargé de projet depuis la base employés
            employees = gestionnaire.get_employees_from_db()
            if employees:
                employee_options = [{'id': None, 'display': '-- Sélectionner un employé --'}] + [
                    {'id': emp['id'], 'display': f"{emp['prenom']} {emp['nom']} ({emp['poste']})"}
                    for emp in employees
                ]
                
                current_manager_id = form_data.get('project_manager_id')
                manager_index = 0
                for i, option in enumerate(employee_options):
                    if option['id'] == current_manager_id:
                        manager_index = i
                        break
                
                selected_manager = st.selectbox(
                    "Chargé de projet:",
                    options=range(len(employee_options)),
                    index=manager_index,
                    format_func=lambda i: employee_options[i]['display']
                )
                
                selected_manager_data = employee_options[selected_manager]
                
                if selected_manager_data['id']:
                    form_data['project_manager_id'] = selected_manager_data['id']
                    selected_emp = next(e for e in employees if e['id'] == selected_manager_data['id'])
                    form_data['project_manager'] = f"{selected_emp['prenom']} {selected_emp['nom']}"
                else:
                    form_data['project_manager_id'] = None
                    form_data['project_manager'] = ''
            else:
                form_data['project_manager'] = st.text_input(
                    "Chargé de projet:",
                    value=form_data.get('project_manager', ''),
                    placeholder="Nom du chargé de projet"
                )
        
        with col2:
            priority_options = ['NORMAL', 'URGENT', 'CRITIQUE']
            priority_labels = {
                'NORMAL': '🟢 Normal',
                'URGENT': '🟡 Urgent', 
                'CRITIQUE': '🔴 Critique'
            }
            
            current_priority = form_data.get('priority', 'NORMAL')
            priority_index = priority_options.index(current_priority) if current_priority in priority_options else 0
            
            form_data['priority'] = st.selectbox(
                "Priorité:",
                options=priority_options,
                index=priority_index,
                format_func=lambda x: priority_labels.get(x, x)
            )
            
            form_data['start_date'] = st.date_input(
                "Date de début prévue:",
                value=datetime.strptime(form_data.get('start_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date()
            ).strftime('%Y-%m-%d')
            
            form_data['end_date'] = st.date_input(
                "Date de fin prévue:",
                value=datetime.strptime(form_data.get('end_date', (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')), '%Y-%m-%d').date()
            ).strftime('%Y-%m-%d')

def show_tasks_section():
    """Section des tâches et opérations - AMÉLIORÉE avec intégration ERP complète"""
    form_data = st.session_state.bt_current_form_data
    gestionnaire = st.session_state.gestionnaire_bt
    
    st.markdown("### 📋 Tâches et Opérations")
    
    # AMÉLIORATION: Récupérer les postes de travail depuis la base ERP
    work_centers = gestionnaire.get_work_centers_from_db()
    work_center_options = [{'id': None, 'display': '-- Sélectionner un poste --'}]
    
    if work_centers:
        work_center_options.extend([
            {'id': wc['id'], 'display': f"{wc['nom']} ({wc['departement']})"}
            for wc in work_centers
        ])
    
    # AMÉLIORATION: Récupérer les employés depuis la base ERP
    employees = gestionnaire.get_employees_from_db()
    employee_options = [{'id': None, 'display': '-- Sélectionner un employé --'}]
    
    if employees:
        employee_options.extend([
            {'id': emp['id'], 'display': f"{emp['prenom']} {emp['nom']} ({emp['poste']})"}
            for emp in employees
        ])
    
    status_options = ['pending', 'in-progress', 'completed', 'on-hold']
    status_labels = {
        'pending': 'En attente',
        'in-progress': 'En cours', 
        'completed': 'Terminé',
        'on-hold': 'En pause'
    }
    
    if 'tasks' not in form_data or not form_data['tasks']:
        form_data['tasks'] = [gestionnaire.get_empty_task()]
    
    # Affichage des tâches
    tasks_to_remove = []
    
    for i, task in enumerate(form_data['tasks']):
        with st.expander(f"Tâche {i+1}" + (f" - {task['operation']}" if task['operation'] else ""), expanded=True):
            task_col1, task_col2, task_col3 = st.columns([2, 1, 1])
            
            with task_col1:
                # AMÉLIORATION: Poste de travail depuis la base ERP
                current_wc_id = task.get('work_center_id')
                wc_index = 0
                for idx, option in enumerate(work_center_options):
                    if option['id'] == current_wc_id:
                        wc_index = idx
                        break
                
                selected_wc = st.selectbox(
                    "Poste de travail:", 
                    options=range(len(work_center_options)),
                    index=wc_index,
                    format_func=lambda idx: work_center_options[idx]['display'],
                    key=f"task_wc_{i}"
                )
                
                selected_wc_data = work_center_options[selected_wc]
                task['work_center_id'] = selected_wc_data['id']
                
                if selected_wc_data['id']:
                    selected_wc_obj = next(wc for wc in work_centers if wc['id'] == selected_wc_data['id'])
                    task['operation'] = selected_wc_obj['nom']
                    
                    # Afficher les infos du poste sélectionné
                    st.markdown(f"""
                    <div class="erp-info-box">
                        🏭 <strong>Poste:</strong> {selected_wc_obj['nom']} | 
                        🏢 <strong>Département:</strong> {selected_wc_obj['departement']} | 
                        🔧 <strong>Type:</strong> {selected_wc_obj.get('type_machine', 'N/A')}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    task['operation'] = st.text_input(
                        "Opération:", 
                        value=task.get('operation', ''),
                        placeholder="Nom de l'opération",
                        key=f"task_op_{i}"
                    )
                
                # Description
                task['description'] = st.text_input(
                    "Description:", 
                    value=task.get('description', ''),
                    placeholder="Description détaillée de la tâche",
                    key=f"task_desc_{i}"
                )
            
            with task_col2:
                # Quantité
                task['quantity'] = st.number_input(
                    "Quantité:", 
                    value=task.get('quantity', 1),
                    min_value=1,
                    key=f"task_qty_{i}"
                )
                
                # Heures prévues
                task['planned_hours'] = st.number_input(
                    "Heures prévues:", 
                    value=task.get('planned_hours', 0.0),
                    min_value=0.0,
                    step=0.25,
                    key=f"task_planned_{i}"
                )
                
                # Heures réelles
                task['actual_hours'] = st.number_input(
                    "Heures réelles:", 
                    value=task.get('actual_hours', 0.0),
                    min_value=0.0,
                    step=0.25,
                    key=f"task_actual_{i}"
                )
            
            with task_col3:
                # AMÉLIORATION: Assigné à depuis la base employés
                current_emp_id = task.get('assigned_to_id')
                emp_index = 0
                for idx, option in enumerate(employee_options):
                    if option['id'] == current_emp_id:
                        emp_index = idx
                        break
                
                selected_emp = st.selectbox(
                    "Assigné à:", 
                    options=range(len(employee_options)),
                    index=emp_index,
                    format_func=lambda idx: employee_options[idx]['display'],
                    key=f"task_assigned_{i}"
                )
                
                selected_emp_data = employee_options[selected_emp]
                task['assigned_to_id'] = selected_emp_data['id']
                
                if selected_emp_data['id']:
                    selected_emp_obj = next(e for e in employees if e['id'] == selected_emp_data['id'])
                    task['assigned_to'] = f"{selected_emp_obj['prenom']} {selected_emp_obj['nom']}"
                    
                    # Afficher les infos de l'employé sélectionné
                    st.markdown(f"""
                    <div class="erp-info-box">
                        👤 <strong>{selected_emp_obj['prenom']} {selected_emp_obj['nom']}</strong> | 
                        💼 <strong>Poste:</strong> {selected_emp_obj['poste']} | 
                        🏢 <strong>Département:</strong> {selected_emp_obj['departement']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    task['assigned_to'] = ''
                
                # Statut
                status_index = status_options.index(task.get('status', 'pending')) if task.get('status', 'pending') in status_options else 0
                task['status'] = st.selectbox(
                    "Statut:", 
                    options=status_options,
                    index=status_index,
                    format_func=lambda x: status_labels.get(x, x),
                    key=f"task_status_{i}"
                )
                
                # Dates
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
                
                # Bouton supprimer
                if len(form_data['tasks']) > 1:
                    if st.button("🗑️ Supprimer", key=f"del_task_{i}", type="secondary"):
                        tasks_to_remove.append(i)
    
    # Supprimer les tâches marquées
    for i in reversed(tasks_to_remove):
        form_data['tasks'].pop(i)
        st.rerun()
    
    # Bouton ajouter tâche
    col_add, col_total = st.columns([1, 2])
    with col_add:
        if st.button("➕ Ajouter une tâche", type="secondary"):
            form_data['tasks'].append(gestionnaire.get_empty_task())
            st.rerun()
    
    with col_total:
        # Totaux
        total_planned = sum(task.get('planned_hours', 0) for task in form_data['tasks'])
        total_actual = sum(task.get('actual_hours', 0) for task in form_data['tasks'])
        
        st.markdown(f"""
        **Totaux:** 
        - Heures prévues: **{total_planned:.2f}h**
        - Heures réelles: **{total_actual:.2f}h**
        """)

def show_materials_section():
    """Section des matériaux et outils"""
    form_data = st.session_state.bt_current_form_data
    
    st.markdown("### 📝 Matériaux et Outils Requis")
    
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
        with st.expander(f"Matériau/Outil {i+1}" + (f" - {material['name']}" if material['name'] else ""), expanded=True):
            mat_col1, mat_col2, mat_col3 = st.columns([2, 1, 1])
            
            with mat_col1:
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
            
            with mat_col2:
                material['quantity'] = st.number_input(
                    "Quantité:", 
                    value=material.get('quantity', 1.0),
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
                
                # Bouton supprimer
                if len(form_data['materials']) > 1:
                    if st.button("🗑️ Supprimer", key=f"del_mat_{i}", type="secondary"):
                        materials_to_remove.append(i)
    
    # Supprimer les matériaux marqués
    for i in reversed(materials_to_remove):
        form_data['materials'].pop(i)
        st.rerun()
    
    # Bouton ajouter matériau
    if st.button("➕ Ajouter un matériau/outil", type="secondary"):
        form_data['materials'].append(st.session_state.gestionnaire_bt.get_empty_material())
        st.rerun()

def show_instructions_section():
    """Section des instructions et notes"""
    form_data = st.session_state.bt_current_form_data
    
    st.markdown("### 📄 Instructions et Notes")
    
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
    """Boutons d'action pour le BT"""
    st.markdown("---")
    
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    
    form_data = st.session_state.bt_current_form_data
    gestionnaire = st.session_state.gestionnaire_bt
    
    with action_col1:
        if st.button("💾 Sauvegarder Bon de Travail", type="primary", use_container_width=True):
            # Validation
            if not form_data.get('project_name'):
                st.error("❌ Le nom du projet est obligatoire")
                return
            
            if not form_data.get('client_name'):
                st.error("❌ Le nom du client est obligatoire")
                return
            
            # Sauvegarder
            if st.session_state.bt_mode == 'edit' and form_data.get('id'):
                # TODO: Implémenter la modification
                st.success("✅ Modification en cours de développement")
            else:
                bt_id = gestionnaire.save_bon_travail(form_data)
                if bt_id:
                    st.success(f"✅ Bon de Travail {form_data['numero_document']} sauvegardé avec succès!")
                    st.session_state.bt_show_success = True
                    
                    # Réinitialiser le formulaire
                    st.session_state.bt_current_form_data = gestionnaire.get_empty_bt_form()
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la sauvegarde")
    
    with action_col2:
        if st.button("🖨️ Imprimer", use_container_width=True):
            st.info("📋 Fonction d'impression en développement")
    
    with action_col3:
        if st.button("📄 Exporter PDF", use_container_width=True):
            st.info("📄 Fonction PDF en développement")
    
    with action_col4:
        if st.button("🗑️ Nouveau Bon", use_container_width=True):
            if st.session_state.get('bt_form_has_changes', False):
                if st.button("⚠️ Confirmer - Perdre les modifications", type="secondary"):
                    st.session_state.bt_current_form_data = gestionnaire.get_empty_bt_form()
                    st.session_state.bt_form_has_changes = False
                    st.rerun()
            else:
                st.session_state.bt_current_form_data = gestionnaire.get_empty_bt_form()
                st.rerun()

def show_bt_management():
    """Interface de gestion des bons de travail"""
    gestionnaire = st.session_state.gestionnaire_bt
    
    st.markdown("### 📋 Gestion des Bons de Travail")
    
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
                    
                    # Afficher les liens ERP si disponibles
                    if bon.get('project_id'):
                        st.markdown(f"🔗 **Projet ERP:** ID #{bon['project_id']}")
                    if bon.get('client_id'):
                        st.markdown(f"🔗 **Client ERP:** ID #{bon['client_id']}")
                
                # Actions
                action_detail_col1, action_detail_col2, action_detail_col3, action_detail_col4 = st.columns(4)
                
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
                    if st.button("⏱️ TimeTracker", key=f"tt_{bon['id']}"):
                        st.session_state.timetracker_redirect_to_bt = True
                        st.session_state.formulaire_project_preselect = bon['id']
                        st.session_state.page_redirect = "timetracker_pro_page"
                        st.rerun()
                
                with action_detail_col4:
                    if st.button("🗑️ Supprimer", key=f"del_{bon['id']}", type="secondary"):
                        st.error("🗑️ Fonction de suppression en développement")

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

def show_production_management_page():
    """
    Page principale du module de gestion des bons de travail
    VERSION INTÉGRÉE ERP COMPLÈTE
    Reproduit l'interface du fichier HTML avec intégration ERP
    """
    
    # Appliquer les styles DG
    apply_dg_styles()
    
    # Initialiser le gestionnaire si nécessaire
    if 'gestionnaire_bt' not in st.session_state:
        if 'erp_db' in st.session_state:
            st.session_state.gestionnaire_bt = GestionnaireBonsTravail(st.session_state.erp_db)
        else:
            st.error("❌ Base de données ERP non disponible")
            return
    
    # Afficher l'en-tête DG
    show_dg_header()
    
    # Navigation principale
    show_bt_navigation()
    
    # Gestion des messages de succès
    if st.session_state.get('bt_show_success'):
        st.success("✅ Bon de Travail sauvegardé avec succès!")
        st.session_state.bt_show_success = False
    
    # Affichage selon le mode
    mode = st.session_state.get('bt_mode', 'create')
    
    if mode in ['create', 'edit', 'view']:
        # Mode formulaire
        if mode == 'view':
            st.info("👁️ Mode visualisation - Formulaire en lecture seule")
        
        with st.container():
            show_bt_form_section()
            show_tasks_section()
            show_materials_section() 
            show_instructions_section()
            
            if mode != 'view':
                show_bt_actions()
    
    elif mode == 'manage':
        # Mode gestion
        show_bt_management()
    
    elif mode == 'stats':
        # Mode statistiques
        show_bt_statistics()
    
    # Footer DG
    st.markdown("---")
    st.markdown("""
    <div style='text-align:center;color:var(--text-color-light);padding:20px 0;'>
        <p><strong>🏭 Desmarais & Gagné Inc.</strong> - Système de Gestion des Bons de Travail ERP</p>
        <p>📞 (450) 372-9630 | 📧 info@dg-inc.com | 🌐 Interface intégrée ERP Production</p>
        <p><em>Version intégrée avec base de données ERP complète</em></p>
    </div>
    """, unsafe_allow_html=True)

# Point d'entrée principal
if __name__ == "__main__":
    show_production_management_page()
