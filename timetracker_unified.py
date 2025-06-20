# timetracker_unified.py - TimeTracker Pro avec Intégration Complète Bons de Travail
# Version Unifiée - Fusion complète selon fusion_bt_timetracker_specs.md

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, time, date
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Any
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimeTrackerUnified:
    """
    TimeTracker Pro - Interface Unifiée avec Intégration Complète Bons de Travail
    
    Remplace TimeTrackerERP + GestionnaireBonsTravail + InterfaceBT
    Interface unique pour : Pointage + Gestion BTs + Suivi + Analytics
    """
    
    def __init__(self, erp_db):
        """
        Initialise le TimeTracker unifié avec toutes les fonctionnalités BT intégrées
        
        Args:
            erp_db: Instance de base de données ERP
        """
        self.db = erp_db
        
        # Initialiser les composants intégrés
        self._init_timetracker_base()
        self._init_bt_integration()
        
        logger.info("TimeTracker Unifié initialisé avec intégration BT complète")
    
    def _init_timetracker_base(self):
        """Initialise les fonctionnalités TimeTracker de base"""
        pass
    
    def _init_bt_integration(self):
        """Initialise l'intégration BT complète"""
        # Créer l'infrastructure BT si nécessaire
        self._ensure_bt_infrastructure()
    
    def _ensure_bt_infrastructure(self):
        """S'assurer que toute l'infrastructure BT est en place"""
        try:
            # Vérifier et corriger les colonnes projects
            self._check_and_fix_projects_columns()
            
            # Créer les tables BT spécialisées si manquantes
            self._create_bt_tables()
            
            logger.info("✅ Infrastructure BT vérifiée/créée")
            
        except Exception as e:
            logger.warning(f"Avertissement infrastructure BT: {e}")
    
    def _check_and_fix_projects_columns(self):
        """Vérifier et ajouter les colonnes manquantes dans la table projects"""
        try:
            schema_query = "PRAGMA table_info(projects)"
            columns = self.db.execute_query(schema_query)
            existing_columns = [col['name'] for col in columns]
            
            columns_added = False
            
            if 'date_debut_reel' not in existing_columns:
                self.db.execute_update("ALTER TABLE projects ADD COLUMN date_debut_reel DATE")
                columns_added = True
            
            if 'date_fin_reel' not in existing_columns:
                self.db.execute_update("ALTER TABLE projects ADD COLUMN date_fin_reel DATE")
                columns_added = True
            
            if columns_added:
                logger.info("🔧 Colonnes de dates réelles ajoutées à projects")
                
        except Exception as e:
            logger.error(f"Erreur vérification colonnes projects: {e}")
    
    def _create_bt_tables(self):
        """Créer les tables spécifiques aux BT si elles n'existent pas"""
        try:
            # Table des assignations d'employés aux BT
            self.db.execute_update("""
                CREATE TABLE IF NOT EXISTS bt_assignations (
                    id INTEGER PRIMARY KEY,
                    bt_id INTEGER NOT NULL,
                    employe_id INTEGER NOT NULL,
                    date_assignation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    statut TEXT DEFAULT 'ASSIGNÉ',
                    role_bt TEXT DEFAULT 'MEMBRE_ÉQUIPE',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bt_id) REFERENCES formulaires(id) ON DELETE CASCADE,
                    FOREIGN KEY (employe_id) REFERENCES employees(id)
                )
            """)
            
            # Table des réservations de postes de travail
            self.db.execute_update("""
                CREATE TABLE IF NOT EXISTS bt_reservations_postes (
                    id INTEGER PRIMARY KEY,
                    bt_id INTEGER NOT NULL,
                    work_center_id INTEGER NOT NULL,
                    date_reservation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date_prevue DATE,
                    date_liberation TIMESTAMP,
                    statut TEXT DEFAULT 'RÉSERVÉ',
                    priorite TEXT DEFAULT 'NORMAL',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bt_id) REFERENCES formulaires(id) ON DELETE CASCADE,
                    FOREIGN KEY (work_center_id) REFERENCES work_centers(id)
                )
            """)
            
            # Table de suivi de l'avancement des BT
            self.db.execute_update("""
                CREATE TABLE IF NOT EXISTS bt_avancement (
                    id INTEGER PRIMARY KEY,
                    bt_id INTEGER NOT NULL,
                    operation_id INTEGER,
                    pourcentage_realise REAL DEFAULT 0.0,
                    temps_reel REAL DEFAULT 0.0,
                    date_debut_reel TIMESTAMP,
                    date_fin_reel TIMESTAMP,
                    notes_avancement TEXT,
                    updated_by INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bt_id) REFERENCES formulaires(id) ON DELETE CASCADE,
                    FOREIGN KEY (operation_id) REFERENCES operations(id),
                    FOREIGN KEY (updated_by) REFERENCES employees(id)
                )
            """)
            
            # Index pour optimisation
            self.db.execute_update("CREATE INDEX IF NOT EXISTS idx_bt_assignations_bt ON bt_assignations(bt_id)")
            self.db.execute_update("CREATE INDEX IF NOT EXISTS idx_bt_assignations_employe ON bt_assignations(employe_id)")
            self.db.execute_update("CREATE INDEX IF NOT EXISTS idx_bt_reservations_bt ON bt_reservations_postes(bt_id)")
            
            logger.info("✅ Tables BT créées/vérifiées avec succès")
            
        except Exception as e:
            logger.error(f"Erreur création tables BT: {e}")
    
    # ========================================================================
    # MÉTHODES TIMETRACKER DE BASE (conservées et enrichies)
    # ========================================================================
    
    def get_all_employees(self) -> List[Dict]:
        """Récupère tous les employés actifs depuis la base ERP"""
        try:
            rows = self.db.execute_query('''
                SELECT e.id, e.prenom, e.nom, e.email, e.telephone, e.poste, 
                       e.departement, e.statut, e.salaire, e.charge_travail, e.date_embauche,
                       COUNT(pa.project_id) as projets_assignes,
                       COUNT(bta.bt_id) as bts_assignes
                FROM employees e
                LEFT JOIN project_assignments pa ON e.id = pa.employee_id
                LEFT JOIN bt_assignations bta ON e.id = bta.employe_id AND bta.statut = 'ASSIGNÉ'
                WHERE e.statut = 'ACTIF' 
                GROUP BY e.id
                ORDER BY e.prenom, e.nom
            ''')
            
            employees = []
            for row in rows:
                emp = dict(row)
                emp['name'] = f"{emp['prenom']} {emp['nom']}"
                emp['employee_code'] = f"EMP{emp['id']:03d}"
                emp['full_name_with_role'] = f"{emp['name']} - {emp.get('poste', 'N/A')} ({emp.get('departement', 'N/A')})"
                employees.append(emp)
            
            return employees
        except Exception as e:
            logger.error(f"Erreur récupération employés: {e}")
            return []
    
    def get_active_projects(self) -> List[Dict]:
        """Récupère tous les projets actifs avec informations BT"""
        try:
            rows = self.db.execute_query('''
                SELECT p.id, p.nom_projet, p.client_nom_cache, p.statut, p.prix_estime,
                       p.bd_ft_estime, p.date_prevu, p.description,
                       c.nom as company_name, c.secteur,
                       COUNT(DISTINCT o.id) as total_operations,
                       COUNT(DISTINCT f.id) as total_bts,
                       COALESCE(SUM(te.total_hours), 0) as timetracker_hours,
                       COALESCE(SUM(te.total_cost), 0) as timetracker_revenue
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                LEFT JOIN operations o ON p.id = o.project_id
                LEFT JOIN formulaires f ON p.id = f.project_id AND f.type_formulaire = 'BON_TRAVAIL'
                LEFT JOIN time_entries te ON p.id = te.project_id AND te.total_cost IS NOT NULL
                WHERE p.statut IN ('À FAIRE', 'EN COURS', 'EN ATTENTE') 
                GROUP BY p.id
                ORDER BY p.nom_projet
            ''')
            
            projects = []
            for row in rows:
                proj = dict(row)
                proj['project_name'] = proj['nom_projet']
                proj['client_name'] = proj['client_nom_cache'] or proj.get('company_name', 'Client Inconnu')
                proj['project_code'] = f"PROJ{proj['id']:04d}"
                proj['display_name'] = f"{proj['project_name']} - {proj['client_name']}"
                projects.append(proj)
            
            return projects
        except Exception as e:
            logger.error(f"Erreur récupération projets: {e}")
            return []
    
    def get_employee_current_entry(self, employee_id: int) -> Optional[Dict]:
        """Vérifie si l'employé a une entrée en cours avec détails BT"""
        try:
            rows = self.db.execute_query('''
                SELECT te.*, p.nom_projet as project_name, p.client_nom_cache as client_name,
                       o.description as task_name, o.sequence_number,
                       wc.nom as work_center_name, wc.departement as work_center_dept,
                       f.numero_document as bt_numero, f.priorite as bt_priorite
                FROM time_entries te
                JOIN projects p ON te.project_id = p.id
                LEFT JOIN operations o ON te.operation_id = o.id
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                LEFT JOIN formulaires f ON te.formulaire_bt_id = f.id
                WHERE te.employee_id = ? AND te.punch_out IS NULL
                ORDER BY te.punch_in DESC
                LIMIT 1
            ''', (employee_id,))
            
            if rows:
                entry = dict(rows[0])
                entry['task_name'] = entry['task_name'] or 'Tâche générale'
                entry['client_name'] = entry['client_name'] or 'Client Inconnu'
                
                # Calcul du temps écoulé en temps réel
                punch_in_time = datetime.fromisoformat(entry['punch_in'])
                elapsed_seconds = (datetime.now() - punch_in_time).total_seconds()
                entry['elapsed_hours'] = elapsed_seconds / 3600
                entry['estimated_cost'] = entry['elapsed_hours'] * entry['hourly_rate']
                
                # Informations BT si applicable
                if entry['bt_numero']:
                    entry['is_bt_work'] = True
                    entry['bt_context'] = f"BT {entry['bt_numero']} ({entry['bt_priorite']})"
                else:
                    entry['is_bt_work'] = False
                
                return entry
            return None
        except Exception as e:
            logger.error(f"Erreur récupération entrée courante employé {employee_id}: {e}")
            return None
    
    def punch_in(self, employee_id: int, project_id: int, operation_id: int = None, 
                 bt_id: int = None, notes: str = "") -> int:
        """Enregistre un punch in enrichi avec support BT"""
        try:
            # Vérifier s'il n'y a pas déjà un punch in actif
            current_entry = self.get_employee_current_entry(employee_id)
            if current_entry:
                raise ValueError(f"L'employé a déjà un pointage actif depuis {current_entry['punch_in']}")
            
            # Obtenir le taux horaire
            hourly_rate = 95.0  # Taux par défaut
            if operation_id:
                rate_rows = self.db.execute_query('''
                    SELECT wc.cout_horaire 
                    FROM operations o
                    LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                    WHERE o.id = ?
                ''', (operation_id,))
                if rate_rows and rate_rows[0]['cout_horaire']:
                    hourly_rate = rate_rows[0]['cout_horaire']
            
            # Enrichir les notes si BT
            if bt_id:
                bt_info = self.get_bt_details_for_timetracker(bt_id)
                if bt_info:
                    notes = f"BT {bt_info['numero_document']} - {notes}".strip()
            
            # Créer l'entrée de temps avec timestamp précis
            punch_in_time = datetime.now()
            entry_id = self.db.execute_insert('''
                INSERT INTO time_entries 
                (employee_id, project_id, operation_id, formulaire_bt_id, punch_in, notes, hourly_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (employee_id, project_id, operation_id, bt_id, punch_in_time.isoformat(), notes, hourly_rate))
            
            logger.info(f"Punch in créé - Employé: {employee_id}, Projet: {project_id}, BT: {bt_id}, Entry: {entry_id}")
            return entry_id
            
        except Exception as e:
            logger.error(f"Erreur punch in: {e}")
            raise
    
    def punch_out(self, employee_id: int, notes: str = "") -> Dict:
        """Enregistre un punch out avec calculs détaillés et mise à jour BT"""
        try:
            # Trouver l'entrée active
            current_entry = self.get_employee_current_entry(employee_id)
            if not current_entry:
                raise ValueError("Aucun pointage actif trouvé pour cet employé")
            
            # Calculer les heures et le coût
            punch_in_time = datetime.fromisoformat(current_entry['punch_in'])
            punch_out_time = datetime.now()
            total_seconds = (punch_out_time - punch_in_time).total_seconds()
            total_hours = total_seconds / 3600
            total_cost = total_hours * current_entry['hourly_rate']
            
            # Mettre à jour l'entrée
            updated_notes = f"{current_entry.get('notes', '')} | Fin: {notes}".strip(' |')
            
            self.db.execute_update('''
                UPDATE time_entries 
                SET punch_out = ?, total_hours = ?, total_cost = ?, notes = ?
                WHERE id = ?
            ''', (punch_out_time.isoformat(), total_hours, total_cost, updated_notes, current_entry['id']))
            
            # Mise à jour de l'avancement BT si applicable
            if current_entry.get('formulaire_bt_id'):
                self._update_bt_progress_from_timetracker(current_entry['formulaire_bt_id'], total_hours)
            
            # Retourner les détails de la session
            session_details = {
                'entry_id': current_entry['id'],
                'total_hours': total_hours,
                'total_cost': total_cost,
                'hourly_rate': current_entry['hourly_rate'],
                'project_name': current_entry['project_name'],
                'task_name': current_entry['task_name'],
                'bt_context': current_entry.get('bt_context'),
                'punch_in': punch_in_time,
                'punch_out': punch_out_time
            }
            
            logger.info(f"Punch out complété - Entry: {current_entry['id']}, Heures: {total_hours:.2f}, BT: {current_entry.get('formulaire_bt_id')}")
            return session_details
            
        except Exception as e:
            logger.error(f"Erreur punch out: {e}")
            raise
    
    # ========================================================================
    # MÉTHODES BONS DE TRAVAIL INTÉGRÉES
    # ========================================================================
    
    def creer_bon_travail_integre(self, data: Dict) -> Optional[int]:
        """Crée un BT avec intégration TimeTracker automatique"""
        try:
            # Validation spécifique BT
            from formulaires.utils.validations import valider_bon_travail
            is_valid, erreurs = valider_bon_travail(data)
            if not is_valid:
                for erreur in erreurs:
                    st.error(f"❌ {erreur}")
                return None
            
            # Enrichissement des données BT
            data['type_formulaire'] = 'BON_TRAVAIL'
            
            # Métadonnées BT avec intégration TimeTracker
            metadonnees_bt = {
                'temps_estime_total': data.get('temps_estime_total', 0),
                'cout_main_oeuvre_estime': data.get('cout_main_oeuvre_estime', 0),
                'date_creation_bt': datetime.now().isoformat(),
                'version_bt': '3.0_unified',  # Version unifiée
                'timetracker_integration': True,
                'auto_assignation_enabled': True
            }
            
            data['metadonnees_json'] = json.dumps(metadonnees_bt)
            
            # Création du formulaire de base
            bt_id = self._create_formulaire_bt(data)
            
            if bt_id:
                # Insérer les opérations dans la table 'operations'
                operations_creees_ids = self._inserer_operations_bt(bt_id, data)
                
                # Actions post-création avec intégration TimeTracker
                self._post_creation_bt_unified(bt_id, data, operations_creees_ids)
                
                logger.info(f"✅ BT #{bt_id} créé avec intégration TimeTracker")
            
            return bt_id
            
        except Exception as e:
            st.error(f"Erreur création BT: {e}")
            logger.error(f"❌ Erreur détaillée création BT: {e}")
            return None
    
    def _create_formulaire_bt(self, data: Dict) -> int:
        """Crée l'entrée formulaire pour le BT"""
        query = """
            INSERT INTO formulaires 
            (numero_document, type_formulaire, employee_id, company_id, project_id,
             statut, priorite, date_creation, date_echeance, montant_total, notes, metadonnees_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data.get('numero_document'),
            data['type_formulaire'],
            data.get('employee_id'),
            data.get('company_id'),
            data.get('project_id'),
            data.get('statut', 'BROUILLON'),
            data.get('priorite', 'NORMAL'),
            data.get('date_creation', datetime.now().date()),
            data.get('date_echeance'),
            data.get('montant_total', 0),
            data.get('notes', ''),
            data.get('metadonnees_json', '{}')
        )
        
        return self.db.execute_insert(query, params)
    
    def _inserer_operations_bt(self, bt_id: int, data: Dict) -> List[int]:
        """Insère les opérations BT avec préparation TimeTracker"""
        operations_creees_ids = []
        operations_data = data.get('operations_detaillees', [])
        project_id = data.get('project_id')
        
        if not operations_data:
            logger.info(f"ℹ️ Aucune opération détaillée pour BT #{bt_id}")
            return []
        
        for i, op_data in enumerate(operations_data):
            if not op_data.get('description'):
                continue
            
            work_center_id = self._resolve_work_center_id(op_data.get('poste_travail'))
            
            try:
                query = """
                    INSERT INTO operations 
                    (project_id, formulaire_bt_id, work_center_id, description, 
                     temps_estime, ressource, statut, poste_travail, sequence_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    project_id,
                    bt_id,
                    work_center_id,
                    op_data.get('description'),
                    op_data.get('temps_prevu', 0.0),
                    op_data.get('assigne'),
                    op_data.get('statut', 'À FAIRE'),
                    op_data.get('poste_travail'),
                    (i + 1) * 10
                )
                
                op_id = self.db.execute_insert(query, params)
                if op_id:
                    operations_creees_ids.append(op_id)
                    logger.info(f"✅ Opération '{op_data.get('description')}' insérée avec ID #{op_id}")
            
            except Exception as e:
                st.error(f"Impossible d'insérer l'opération '{op_data.get('description')}': {e}")
                continue
        
        logger.info(f"✅ {len(operations_creees_ids)} opération(s) insérée(s) pour BT #{bt_id}")
        return operations_creees_ids
    
    def _resolve_work_center_id(self, poste_nom: str) -> Optional[int]:
        """Résout l'ID d'un poste de travail par son nom"""
        if not poste_nom:
            return None
        
        poste_clean = poste_nom.split(' (')[0].strip()
        wc_result = self.db.execute_query(
            "SELECT id FROM work_centers WHERE nom = ?", (poste_clean,)
        )
        return wc_result[0]['id'] if wc_result else None
    
    def _post_creation_bt_unified(self, bt_id: int, data: Dict, operations_creees_ids: List[int] = None):
        """Actions post-création BT avec intégration TimeTracker"""
        try:
            # 1. Assignation automatique aux employés avec préparation TimeTracker
            employes_assignes = data.get('employes_assignes', [])
            if employes_assignes:
                self._assigner_employes_bt_unified(bt_id, employes_assignes)
            
            # 2. Réservation des postes de travail
            work_centers = data.get('work_centers_utilises', [])
            if work_centers:
                wc_ids_to_reserve = [self._resolve_work_center_id(wc) for wc in work_centers]
                wc_ids_to_reserve = [wc_id for wc_id in wc_ids_to_reserve if wc_id]
                self._reserver_postes_travail(bt_id, wc_ids_to_reserve, data.get('date_echeance'))
            
            # 3. Initialisation du suivi d'avancement avec TimeTracker
            if operations_creees_ids:
                self._initialiser_avancement_bt_unified(bt_id, operations_creees_ids)
            
            # 4. Mise à jour du statut du projet
            if data.get('project_id'):
                self._mettre_a_jour_statut_projet_unified(data['project_id'], bt_id)
            
            # 5. Notification aux employés assignés (pour pointage)
            self._notify_employees_bt_assignment(bt_id, employes_assignes)
            
            logger.info(f"✅ Actions post-création BT #{bt_id} terminées avec intégration TimeTracker")
                
        except Exception as e:
            st.warning(f"Actions post-création BT partiellement échouées: {e}")
            logger.error(f"⚠️ Erreur post-création BT: {e}")
    
    def _assigner_employes_bt_unified(self, bt_id: int, employes_ids: List[int]):
        """Assigne des employés au BT avec préparation TimeTracker"""
        try:
            assignations_creees = 0
            
            for employe_id in employes_ids:
                # Vérifier si l'employé existe
                employe_exists = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM employees WHERE id = ?",
                    (employe_id,)
                )
                
                if employe_exists and employe_exists[0]['count'] > 0:
                    query = """
                        INSERT INTO bt_assignations (bt_id, employe_id, date_assignation, statut, role_bt)
                        VALUES (?, ?, CURRENT_TIMESTAMP, 'ASSIGNÉ', 'MEMBRE_ÉQUIPE')
                    """
                    self.db.execute_insert(query, (bt_id, employe_id))
                    assignations_creees += 1
                    
                    # Préparer les notifications TimeTracker
                    self._prepare_timetracker_notification(bt_id, employe_id)
                else:
                    st.warning(f"Employé ID {employe_id} non trouvé - assignation ignorée")
            
            if assignations_creees > 0:
                logger.info(f"✅ {assignations_creees} employé(s) assigné(s) au BT #{bt_id} avec intégration TimeTracker")
                
        except Exception as e:
            st.warning(f"Erreur assignation employés: {e}")
            logger.error(f"❌ Erreur assignation employés BT: {e}")
    
    def _prepare_timetracker_notification(self, bt_id: int, employe_id: int):
        """Prépare les notifications TimeTracker pour un employé assigné"""
        try:
            # Stocker dans session state pour affichage dans l'interface
            if 'bt_notifications' not in st.session_state:
                st.session_state.bt_notifications = {}
            
            if employe_id not in st.session_state.bt_notifications:
                st.session_state.bt_notifications[employe_id] = []
            
            st.session_state.bt_notifications[employe_id].append({
                'bt_id': bt_id,
                'type': 'ASSIGNATION',
                'timestamp': datetime.now().isoformat(),
                'read': False
            })
            
        except Exception as e:
            logger.error(f"Erreur préparation notification TimeTracker: {e}")
    
    def _reserver_postes_travail(self, bt_id: int, work_centers: List[int], date_prevue: Optional[str]):
        """Réserve des postes de travail pour le BT"""
        try:
            reservations_creees = 0
            
            for wc_id in work_centers:
                poste_exists = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM work_centers WHERE id = ?",
                    (wc_id,)
                )
                
                if poste_exists and poste_exists[0]['count'] > 0:
                    query = """
                        INSERT INTO bt_reservations_postes 
                        (bt_id, work_center_id, date_reservation, date_prevue, statut)
                        VALUES (?, ?, CURRENT_TIMESTAMP, ?, 'RÉSERVÉ')
                    """
                    self.db.execute_insert(query, (bt_id, wc_id, date_prevue))
                    reservations_creees += 1
                else:
                    st.warning(f"Poste de travail ID {wc_id} non trouvé")
            
            if reservations_creees > 0:
                logger.info(f"✅ {reservations_creees} poste(s) réservé(s) pour BT #{bt_id}")
                
        except Exception as e:
            st.warning(f"Erreur réservation postes: {e}")
            logger.error(f"❌ Erreur réservation postes BT: {e}")
    
    def _initialiser_avancement_bt_unified(self, bt_id: int, operations_ids: List[int]):
        """Initialise le suivi d'avancement BT avec intégration TimeTracker"""
        try:
            avancements_crees = 0
            
            for operation_id in operations_ids:
                operation_exists = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM operations WHERE id = ?",
                    (operation_id,)
                )
                
                if operation_exists and operation_exists[0]['count'] > 0:
                    query = """
                        INSERT INTO bt_avancement 
                        (bt_id, operation_id, pourcentage_realise, temps_reel)
                        VALUES (?, ?, 0.0, 0.0)
                    """
                    self.db.execute_insert(query, (bt_id, operation_id))
                    avancements_crees += 1
            
            if avancements_crees > 0:
                logger.info(f"✅ Suivi avancement TimeTracker initialisé pour {avancements_crees} opération(s)")
                
        except Exception as e:
            logger.error(f"❌ Erreur initialisation avancement: {e}")
    
    def _mettre_a_jour_statut_projet_unified(self, project_id: int, bt_id: int):
        """Met à jour le statut du projet avec intégration TimeTracker"""
        try:
            # Vérifier si c'est le premier BT du projet
            query = """
                SELECT COUNT(*) as count FROM formulaires 
                WHERE project_id = ? AND type_formulaire = 'BON_TRAVAIL'
            """
            result = self.db.execute_query(query, (project_id,))
            
            if result and result[0]['count'] == 1:  # Premier BT
                try:
                    query_update = """
                        UPDATE projects 
                        SET statut = 'EN COURS', 
                            date_debut_reel = CURRENT_DATE,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND statut = 'À FAIRE'
                    """
                    affected = self.db.execute_update(query_update, (project_id,))
                    
                    if affected > 0:
                        st.info(f"✅ Projet #{project_id} automatiquement démarré (EN COURS)")
                        logger.info(f"✅ Projet #{project_id} mis à jour: À FAIRE → EN COURS")
                        
                except Exception as e_col:
                    if "no such column" in str(e_col).lower():
                        # Mise à jour basique si colonnes manquantes
                        query_update_basic = """
                            UPDATE projects 
                            SET statut = 'EN COURS', updated_at = CURRENT_TIMESTAMP
                            WHERE id = ? AND statut = 'À FAIRE'
                        """
                        affected = self.db.execute_update(query_update_basic, (project_id,))
                        
                        if affected > 0:
                            st.info(f"✅ Projet #{project_id} marqué EN COURS")
                    else:
                        raise e_col
            
        except Exception as e:
            st.warning(f"Erreur mise à jour projet: {e}")
            logger.error(f"❌ Erreur mise à jour projet #{project_id}: {e}")
    
    def _notify_employees_bt_assignment(self, bt_id: int, employes_ids: List[int]):
        """Notifie les employés de leur assignation pour pointage"""
        try:
            bt_info = self.get_bt_details_complets(bt_id)
            if not bt_info:
                return
            
            for employe_id in employes_ids:
                # Ajouter notification dans session state
                if 'employee_notifications' not in st.session_state:
                    st.session_state.employee_notifications = {}
                
                if employe_id not in st.session_state.employee_notifications:
                    st.session_state.employee_notifications[employe_id] = []
                
                notification = {
                    'type': 'BT_ASSIGNMENT',
                    'bt_id': bt_id,
                    'bt_numero': bt_info.get('numero_document'),
                    'message': f"Nouveau BT assigné: {bt_info.get('numero_document')}",
                    'timestamp': datetime.now().isoformat(),
                    'read': False,
                    'priority': bt_info.get('priorite', 'NORMAL')
                }
                
                st.session_state.employee_notifications[employe_id].append(notification)
            
            logger.info(f"✅ Notifications envoyées à {len(employes_ids)} employé(s) pour BT #{bt_id}")
            
        except Exception as e:
            logger.error(f"Erreur notifications employés: {e}")
    
    # ========================================================================
    # MÉTHODES INTÉGRATION BT ↔ TIMETRACKER
    # ========================================================================
    
    def get_bts_assignes_employe(self, employee_id: int) -> List[Dict]:
        """Récupère les BTs assignés à un employé avec stats TimeTracker"""
        try:
            query = '''
                SELECT f.id as bt_id, f.numero_document, f.statut as bt_statut, 
                       f.priorite, f.date_creation, f.date_echeance, f.notes,
                       p.nom_projet, p.client_nom_cache,
                       bta.date_assignation, bta.statut as assignation_statut,
                       c.nom as company_nom,
                       -- Stats TimeTracker pour ce BT et cet employé
                       COALESCE(SUM(te.total_hours), 0) as heures_pointees,
                       COALESCE(SUM(te.total_cost), 0) as cout_total,
                       COUNT(te.id) as nb_pointages,
                       -- Progression globale du BT
                       COALESCE(AVG(ba.pourcentage_realise), 0) as progression_avg
                FROM bt_assignations bta
                JOIN formulaires f ON bta.bt_id = f.id
                LEFT JOIN projects p ON f.project_id = p.id  
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN time_entries te ON f.id = te.formulaire_bt_id AND te.employee_id = ?
                LEFT JOIN bt_avancement ba ON f.id = ba.bt_id
                WHERE bta.employe_id = ? 
                AND bta.statut = 'ASSIGNÉ'
                AND f.statut NOT IN ('TERMINÉ', 'ANNULÉ')
                GROUP BY f.id, bta.id
                ORDER BY 
                    CASE f.priorite 
                        WHEN 'CRITIQUE' THEN 1
                        WHEN 'URGENT' THEN 2
                        ELSE 3
                    END,
                    f.date_echeance ASC
            '''
            rows = self.db.execute_query(query, (employee_id, employee_id))
            
            bts = []
            for row in rows:
                bt = dict(row)
                bt['progression_timetracker'] = min(100, bt['progression_avg'])
                bt['urgent'] = bt['priorite'] in ['URGENT', 'CRITIQUE']
                bts.append(bt)
            
            return bts
            
        except Exception as e:
            st.error(f"Erreur récupération BTs assignés: {e}")
            return []
    
    def get_bt_details_for_timetracker(self, bt_id: int) -> Optional[Dict]:
        """Récupère les détails d'un BT pour le pointage TimeTracker"""
        try:
            query = '''
                SELECT f.*, p.nom_projet, c.nom as company_nom,
                       COUNT(DISTINCT bta.employe_id) as nb_employes_assignes,
                       COUNT(DISTINCT btr.work_center_id) as nb_postes_reserves,
                       COALESCE(AVG(ba.pourcentage_realise), 0) as progression_avg
                FROM formulaires f
                LEFT JOIN projects p ON f.project_id = p.id
                LEFT JOIN companies c ON f.company_id = c.id  
                LEFT JOIN bt_assignations bta ON f.id = bta.bt_id AND bta.statut = 'ASSIGNÉ'
                LEFT JOIN bt_reservations_postes btr ON f.id = btr.bt_id AND btr.statut = 'RÉSERVÉ'
                LEFT JOIN bt_avancement ba ON f.id = ba.bt_id
                WHERE f.id = ? AND f.type_formulaire = 'BON_TRAVAIL'
                GROUP BY f.id
            '''
            result = self.db.execute_query(query, (bt_id,))
            
            if result:
                bt_details = dict(result[0])
                bt_details['progression_globale'] = bt_details['progression_avg']
                return bt_details
            return None
            
        except Exception as e:
            st.error(f"Erreur récupération détails BT: {e}")
            return None
    
    def punch_in_sur_bt_enhanced(self, employee_id: int, bt_id: int, notes: str = "") -> int:
        """Démarre un pointage optimisé sur un Bon de Travail"""
        try:
            # Récupérer les infos du BT
            bt_details = self.get_bt_details_for_timetracker(bt_id)
            if not bt_details:
                raise ValueError("BT non trouvé")
            
            # Vérifier l'assignation
            assignation = self.db.execute_query(
                "SELECT id FROM bt_assignations WHERE bt_id = ? AND employe_id = ? AND statut = 'ASSIGNÉ'",
                (bt_id, employee_id)
            )
            if not assignation:
                raise ValueError("Employé non assigné à ce BT")
            
            # Récupérer la première opération disponible du BT
            operation_id = self._get_next_operation_for_bt(bt_id, employee_id)
            
            # Démarrer le pointage avec intégration BT
            entry_id = self.punch_in(
                employee_id=employee_id,
                project_id=bt_details.get('project_id'),
                operation_id=operation_id,
                bt_id=bt_id,
                notes=f"Pointage BT {bt_details['numero_document']} - {notes}".strip()
            )
            
            # Marquer le début du travail sur le BT
            self._mark_bt_work_started(bt_id, employee_id, entry_id)
            
            return entry_id
            
        except Exception as e:
            st.error(f"Erreur punch in BT: {e}")
            raise
    
    def _get_next_operation_for_bt(self, bt_id: int, employee_id: int) -> Optional[int]:
        """Récupère la prochaine opération à traiter pour un BT"""
        try:
            # Chercher une opération non terminée pour ce BT
            query = """
                SELECT o.id
                FROM operations o
                LEFT JOIN bt_avancement ba ON o.id = ba.operation_id
                WHERE o.formulaire_bt_id = ?
                AND (ba.pourcentage_realise IS NULL OR ba.pourcentage_realise < 100)
                ORDER BY o.sequence_number
                LIMIT 1
            """
            result = self.db.execute_query(query, (bt_id,))
            return result[0]['id'] if result else None
            
        except Exception as e:
            logger.error(f"Erreur récupération prochaine opération BT: {e}")
            return None
    
    def _mark_bt_work_started(self, bt_id: int, employee_id: int, entry_id: int):
        """Marque le début du travail sur un BT"""
        try:
            # Mettre à jour le statut du BT si c'est le premier pointage
            first_work = self.db.execute_query(
                "SELECT COUNT(*) as count FROM time_entries WHERE formulaire_bt_id = ? AND total_cost IS NOT NULL",
                (bt_id,)
            )
            
            if first_work and first_work[0]['count'] == 0:
                # Premier travail sur ce BT
                self.db.execute_update(
                    "UPDATE formulaires SET statut = 'EN COURS' WHERE id = ? AND statut = 'VALIDÉ'",
                    (bt_id,)
                )
                logger.info(f"✅ BT #{bt_id} marqué EN COURS (premier pointage)")
            
        except Exception as e:
            logger.error(f"Erreur marquage début travail BT: {e}")
    
    def _update_bt_progress_from_timetracker(self, bt_id: int, hours_worked: float):
        """Met à jour la progression du BT basée sur les heures TimeTracker"""
        try:
            # Récupérer le temps total estimé pour le BT
            bt_info = self.db.execute_query(
                "SELECT metadonnees_json FROM formulaires WHERE id = ?",
                (bt_id,)
            )
            
            if not bt_info:
                return
            
            metadonnees = {}
            try:
                metadonnees = json.loads(bt_info[0]['metadonnees_json'] or '{}')
            except:
                pass
            
            temps_estime_total = metadonnees.get('temps_estime_total', 0)
            
            if temps_estime_total > 0:
                # Calculer le pourcentage basé sur les heures totales pointées
                total_hours_query = """
                    SELECT COALESCE(SUM(total_hours), 0) as total_worked
                    FROM time_entries 
                    WHERE formulaire_bt_id = ? AND total_cost IS NOT NULL
                """
                result = self.db.execute_query(total_hours_query, (bt_id,))
                total_worked = result[0]['total_worked'] if result else 0
                
                # Calculer la progression (plafonné à 100%)
                progression = min(100, (total_worked / temps_estime_total) * 100)
                
                # Mettre à jour l'avancement global du BT
                self._update_bt_global_progress(bt_id, progression)
                
                logger.info(f"✅ Progression BT #{bt_id} mise à jour: {progression:.1f}%")
            
        except Exception as e:
            logger.error(f"Erreur mise à jour progression BT: {e}")
    
    def _update_bt_global_progress(self, bt_id: int, progression: float):
        """Met à jour la progression globale du BT"""
        try:
            # Mettre à jour ou créer un enregistrement de progression globale
            existing = self.db.execute_query(
                "SELECT id FROM bt_avancement WHERE bt_id = ? AND operation_id IS NULL",
                (bt_id,)
            )
            
            if existing:
                # Mettre à jour
                self.db.execute_update(
                    "UPDATE bt_avancement SET pourcentage_realise = ?, updated_at = CURRENT_TIMESTAMP WHERE bt_id = ? AND operation_id IS NULL",
                    (progression, bt_id)
                )
            else:
                # Créer
                self.db.execute_insert(
                    "INSERT INTO bt_avancement (bt_id, pourcentage_realise) VALUES (?, ?)",
                    (bt_id, progression)
                )
            
        except Exception as e:
            logger.error(f"Erreur mise à jour progression globale BT: {e}")
    
    def get_statistiques_bt_timetracker(self, bt_id: int = None) -> Dict:
        """Statistiques TimeTracker pour les BTs (global ou spécifique)"""
        try:
            if bt_id:
                # Stats pour un BT spécifique
                query = '''
                    SELECT 
                        COUNT(*) as nb_pointages,
                        COUNT(DISTINCT employee_id) as nb_employes_distinct,
                        COALESCE(SUM(total_hours), 0) as total_heures,
                        COALESCE(SUM(total_cost), 0) as total_cout,
                        COALESCE(AVG(total_hours), 0) as moyenne_heures_session,
                        MIN(punch_in) as premier_pointage,
                        MAX(punch_out) as dernier_pointage
                    FROM time_entries 
                    WHERE formulaire_bt_id = ? AND total_cost IS NOT NULL
                '''
                result = self.db.execute_query(query, (bt_id,))
            else:
                # Stats globales des BTs
                query = '''
                    SELECT 
                        COUNT(*) as nb_pointages,
                        COUNT(DISTINCT employee_id) as nb_employes_distinct,
                        COUNT(DISTINCT formulaire_bt_id) as nb_bts_avec_pointages,
                        COALESCE(SUM(total_hours), 0) as total_heures,
                        COALESCE(SUM(total_cost), 0) as total_cout,
                        COALESCE(AVG(total_hours), 0) as moyenne_heures_session
                    FROM time_entries 
                    WHERE formulaire_bt_id IS NOT NULL AND total_cost IS NOT NULL
                '''
                result = self.db.execute_query(query)
            
            return dict(result[0]) if result else {}
            
        except Exception as e:
            st.error(f"Erreur stats BT TimeTracker: {e}")
            return {}
    
    def get_bt_dashboard_unifie(self, employee_id: int = None) -> Dict:
        """Dashboard unifié BTs avec données TimeTracker intégrées"""
        try:
            # Statistiques globales
            stats_globales = self.get_statistiques_bt_timetracker()
            
            # BTs par statut avec données TimeTracker
            query_status = """
                SELECT 
                    f.statut,
                    COUNT(f.id) as count,
                    COALESCE(SUM(te.total_hours), 0) as total_hours,
                    COALESCE(SUM(te.total_cost), 0) as total_cost
                FROM formulaires f
                LEFT JOIN time_entries te ON f.id = te.formulaire_bt_id AND te.total_cost IS NOT NULL
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                GROUP BY f.statut
            """
            stats_status = self.db.execute_query(query_status)
            
            # BTs par priorité
            query_priority = """
                SELECT 
                    f.priorite,
                    COUNT(f.id) as count,
                    COALESCE(AVG(ba.pourcentage_realise), 0) as avg_progress
                FROM formulaires f
                LEFT JOIN bt_avancement ba ON f.id = ba.bt_id
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                GROUP BY f.priorite
            """
            stats_priority = self.db.execute_query(query_priority)
            
            # Top employés BT (si spécifique)
            top_employees = []
            if employee_id:
                query_emp = """
                    SELECT 
                        e.prenom || ' ' || e.nom as nom,
                        COUNT(te.id) as nb_pointages,
                        COALESCE(SUM(te.total_hours), 0) as total_hours,
                        COALESCE(SUM(te.total_cost), 0) as total_cost
                    FROM employees e
                    JOIN time_entries te ON e.id = te.employee_id
                    WHERE te.formulaire_bt_id IS NOT NULL AND te.total_cost IS NOT NULL
                    AND e.id = ?
                    GROUP BY e.id
                """
                result = self.db.execute_query(query_emp, (employee_id,))
                top_employees = [dict(row) for row in result]
            
            dashboard = {
                'stats_globales': stats_globales,
                'stats_par_statut': [dict(row) for row in stats_status],
                'stats_par_priorite': [dict(row) for row in stats_priority],
                'top_employees': top_employees,
                'timestamp': datetime.now().isoformat()
            }
            
            return dashboard
            
        except Exception as e:
            st.error(f"Erreur dashboard BT unifié: {e}")
            return {}
    
    def workflow_bt_complet(self, bt_id: int) -> Dict:
        """Workflow complet : Création → Pointage → Suivi → Finalisation"""
        try:
            bt_details = self.get_bt_details_complets(bt_id)
            if not bt_details:
                return {'error': 'BT non trouvé'}
            
            # Déterminer l'étape actuelle
            current_stage = self._determine_bt_stage(bt_details)
            
            # Récupérer les données de workflow
            workflow_data = {
                'bt_id': bt_id,
                'current_stage': current_stage,
                'bt_details': bt_details,
                'assignations': bt_details.get('assignations', []),
                'timetracker_sessions': self.get_sessions_timetracker_bt(bt_id),
                'operations_progress': self._get_operations_progress_bt(bt_id),
                'next_actions': self._get_next_actions_bt(bt_id, current_stage),
                'workflow_history': self._get_workflow_history_bt(bt_id)
            }
            
            return workflow_data
            
        except Exception as e:
            logger.error(f"Erreur workflow BT #{bt_id}: {e}")
            return {'error': str(e)}
    
    def _determine_bt_stage(self, bt_details: Dict) -> str:
        """Détermine l'étape actuelle du workflow BT"""
        statut = bt_details.get('statut', 'BROUILLON')
        nb_assignations = len(bt_details.get('assignations', []))
        
        # Récupérer les sessions TimeTracker
        sessions = self.get_sessions_timetracker_bt(bt_details['id'])
        has_timetracker_work = len(sessions) > 0
        
        if statut == 'BROUILLON':
            return 'creation'
        elif statut == 'VALIDÉ' and nb_assignations == 0:
            return 'assignation'
        elif statut == 'VALIDÉ' and nb_assignations > 0 and not has_timetracker_work:
            return 'demarrage'
        elif statut == 'EN COURS' or has_timetracker_work:
            return 'execution'
        elif statut == 'TERMINÉ':
            return 'finalisation'
        else:
            return 'unknown'
    
    def _get_operations_progress_bt(self, bt_id: int) -> List[Dict]:
        """Récupère la progression des opérations d'un BT"""
        try:
            query = """
                SELECT 
                    o.id, o.description, o.sequence_number, o.temps_estime,
                    ba.pourcentage_realise, ba.temps_reel,
                    COALESCE(SUM(te.total_hours), 0) as heures_timetracker
                FROM operations o
                LEFT JOIN bt_avancement ba ON o.id = ba.operation_id
                LEFT JOIN time_entries te ON o.id = te.operation_id AND te.formulaire_bt_id = ?
                WHERE o.formulaire_bt_id = ?
                GROUP BY o.id
                ORDER BY o.sequence_number
            """
            rows = self.db.execute_query(query, (bt_id, bt_id))
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur progression opérations BT: {e}")
            return []
    
    def _get_next_actions_bt(self, bt_id: int, current_stage: str) -> List[str]:
        """Détermine les prochaines actions possibles pour le BT"""
        actions = []
        
        if current_stage == 'creation':
            actions = ['Valider le BT', 'Assigner des employés', 'Modifier les détails']
        elif current_stage == 'assignation':
            actions = ['Assigner des employés', 'Démarrer le travail', 'Réserver des postes']
        elif current_stage == 'demarrage':
            actions = ['Commencer le pointage', 'Voir les employés assignés', 'Modifier les opérations']
        elif current_stage == 'execution':
            actions = ['Suivre l\'avancement', 'Ajouter des heures', 'Marquer opérations terminées']
        elif current_stage == 'finalisation':
            actions = ['Voir le rapport final', 'Archiver le BT', 'Analyser les performances']
        
        return actions
    
    def _get_workflow_history_bt(self, bt_id: int) -> List[Dict]:
        """Récupère l'historique du workflow d'un BT"""
        try:
            # Historique des changements de statut
            query = """
                SELECT 
                    fv.date_validation,
                    fv.ancien_statut,
                    fv.nouveau_statut,
                    fv.commentaires,
                    e.prenom || ' ' || e.nom as employee_nom
                FROM formulaire_validations fv
                LEFT JOIN employees e ON fv.employee_id = e.id
                WHERE fv.formulaire_id = ?
                ORDER BY fv.date_validation DESC
            """
            rows = self.db.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur historique workflow BT: {e}")
            return []
    
    def get_sessions_timetracker_bt(self, bt_id: int) -> List[Dict]:
        """Récupère toutes les sessions TimeTracker d'un BT"""
        try:
            query = '''
                SELECT 
                    te.*,
                    e.prenom || ' ' || e.nom as employee_name,
                    e.poste as employee_poste,
                    e.departement as employee_dept
                FROM time_entries te
                JOIN employees e ON te.employee_id = e.id
                WHERE te.formulaire_bt_id = ?
                ORDER BY te.punch_in DESC
            '''
            rows = self.db.execute_query(query, (bt_id,))
            sessions = [dict(row) for row in rows]
            
            logger.info(f"✅ {len(sessions)} session(s) TimeTracker récupérée(s) pour BT #{bt_id}")
            return sessions
            
        except Exception as e:
            logger.error(f"Erreur récupération sessions TimeTracker BT #{bt_id}: {e}")
            return []
    
    def get_bt_details_complets(self, bt_id: int) -> Optional[Dict]:
        """Récupère tous les détails complets d'un BT avec intégration TimeTracker"""
        try:
            # Détails de base du BT
            query = """
                SELECT f.*, p.nom_projet as project_nom, e.prenom || ' ' || e.nom as employee_nom
                FROM formulaires f
                LEFT JOIN projects p ON f.project_id = p.id
                LEFT JOIN employees e ON f.employee_id = e.id
                WHERE f.id = ? AND f.type_formulaire = 'BON_TRAVAIL'
            """
            result = self.db.execute_query(query, (bt_id,))
            
            if not result:
                return None
            
            bt_details = dict(result[0])
            
            # Enrichissement avec données BT + TimeTracker
            bt_details['assignations'] = self._get_assignations_bt(bt_id)
            bt_details['reservations_postes'] = self._get_reservations_postes_bt(bt_id)
            bt_details['avancement_detaille'] = self._get_avancement_detaille_bt(bt_id)
            bt_details['operations_reelles'] = self._get_operations_bt(bt_id)
            bt_details['timetracker_stats'] = self.get_statistiques_bt_timetracker(bt_id)
            bt_details['timetracker_sessions'] = self.get_sessions_timetracker_bt(bt_id)
            bt_details['workflow_data'] = self.workflow_bt_complet(bt_id)
            
            # Calculer avancement global avec TimeTracker
            bt_details['avancement'] = self._calculer_avancement_bt_unifie(bt_id)
            
            logger.info(f"✅ Détails complets récupérés pour BT #{bt_id} avec intégration TimeTracker")
            return bt_details
            
        except Exception as e:
            st.error(f"Erreur récupération détails BT: {e}")
            logger.error(f"❌ Erreur détails BT #{bt_id}: {e}")
            return None
    
    def _get_assignations_bt(self, bt_id: int) -> List[Dict]:
        """Récupère les assignations d'employés pour un BT"""
        try:
            query = """
                SELECT 
                    a.*,
                    e.prenom || ' ' || e.nom as employe_nom,
                    e.poste, e.departement, e.email
                FROM bt_assignations a
                JOIN employees e ON a.employe_id = e.id
                WHERE a.bt_id = ?
                ORDER BY a.date_assignation
            """
            rows = self.db.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur récupération assignations BT #{bt_id}: {e}")
            return []
    
    def _get_reservations_postes_bt(self, bt_id: int) -> List[Dict]:
        """Récupère les réservations de postes pour un BT"""
        try:
            query = """
                SELECT 
                    r.*,
                    w.nom as poste_nom, w.departement, w.categorie
                FROM bt_reservations_postes r
                JOIN work_centers w ON r.work_center_id = w.id
                WHERE r.bt_id = ?
                ORDER BY r.date_prevue
            """
            rows = self.db.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur récupération réservations BT #{bt_id}: {e}")
            return []
    
    def _get_avancement_detaille_bt(self, bt_id: int) -> List[Dict]:
        """Récupère l'avancement détaillé de toutes les opérations du BT"""
        try:
            query = """
                SELECT 
                    a.*,
                    o.sequence_number, o.description as operation_description, o.temps_estime,
                    e.prenom || ' ' || e.nom as updated_by_nom
                FROM bt_avancement a
                LEFT JOIN operations o ON a.operation_id = o.id
                LEFT JOIN employees e ON a.updated_by = e.id
                WHERE a.bt_id = ?
                ORDER BY o.sequence_number
            """
            rows = self.db.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur avancement détaillé BT #{bt_id}: {e}")
            return []
    
    def _get_operations_bt(self, bt_id: int) -> List[Dict]:
        """Récupère les opérations réelles d'un BT depuis la table operations"""
        try:
            query = """
                SELECT 
                    o.*,
                    wc.nom as work_center_nom,
                    wc.departement as work_center_dept
                FROM operations o
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE o.formulaire_bt_id = ?
                ORDER BY o.sequence_number
            """
            rows = self.db.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur récupération opérations BT #{bt_id}: {e}")
            return []
    
    def _calculer_avancement_bt_unifie(self, bt_id: int) -> Dict:
        """Calcule l'avancement d'un BT en combinant opérations et TimeTracker"""
        try:
            # Avancement basé sur les opérations réelles
            operations = self._get_operations_bt(bt_id)
            if not operations:
                return {'pourcentage': 0, 'operations_terminees': 0, 'operations_totales': 0, 'source': 'aucune_operation'}
            
            operations_terminees = 0
            for operation in operations:
                if operation.get('statut') == 'TERMINÉ':
                    operations_terminees += 1
            
            operations_totales = len(operations)
            pourcentage_operations = (operations_terminees / operations_totales * 100) if operations_totales > 0 else 0
            
            # Avancement basé sur TimeTracker (heures)
            timetracker_stats = self.get_statistiques_bt_timetracker(bt_id)
            total_heures_pointees = timetracker_stats.get('total_heures', 0)
            
            # Récupérer le temps estimé total
            bt_info = self.db.execute_query(
                "SELECT metadonnees_json FROM formulaires WHERE id = ?",
                (bt_id,)
            )
            
            temps_estime_total = 0
            if bt_info:
                try:
                    metadonnees = json.loads(bt_info[0]['metadonnees_json'] or '{}')
                    temps_estime_total = metadonnees.get('temps_estime_total', 0)
                except:
                    pass
            
            pourcentage_timetracker = 0
            if temps_estime_total > 0:
                pourcentage_timetracker = min(100, (total_heures_pointees / temps_estime_total) * 100)
            
            # Combinaison intelligente des deux méthodes
            if pourcentage_timetracker > 0 and pourcentage_operations > 0:
                # Moyenne pondérée (70% TimeTracker, 30% opérations)
                pourcentage_final = (pourcentage_timetracker * 0.7) + (pourcentage_operations * 0.3)
                source = 'combine'
            elif pourcentage_timetracker > 0:
                pourcentage_final = pourcentage_timetracker
                source = 'timetracker'
            else:
                pourcentage_final = pourcentage_operations
                source = 'operations'
            
            return {
                'pourcentage': round(pourcentage_final, 1),
                'operations_terminees': operations_terminees,
                'operations_totales': operations_totales,
                'pourcentage_operations': round(pourcentage_operations, 1),
                'pourcentage_timetracker': round(pourcentage_timetracker, 1),
                'heures_pointees': total_heures_pointees,
                'temps_estime_total': temps_estime_total,
                'source': source
            }
            
        except Exception as e:
            logger.error(f"Erreur calcul avancement BT unifié #{bt_id}: {e}")
            return {'pourcentage': 0, 'operations_terminees': 0, 'operations_totales': 0, 'erreur': str(e)}
    
    # ========================================================================
    # MÉTHODES CONSERVÉES TIMETRACKER (pour compatibilité)
    # ========================================================================
    
    def get_employee_by_id(self, employee_id: int) -> Optional[Dict]:
        """Récupère un employé par son ID avec statistiques BT"""
        try:
            emp_rows = self.db.execute_query('''
                SELECT e.*, 
                       COUNT(DISTINCT pa.project_id) as projets_assignes,
                       COUNT(DISTINCT bta.bt_id) as bts_assignes
                FROM employees e
                LEFT JOIN project_assignments pa ON e.id = pa.employee_id
                LEFT JOIN bt_assignations bta ON e.id = bta.employe_id AND bta.statut = 'ASSIGNÉ'
                WHERE e.id = ? AND e.statut = 'ACTIF'
                GROUP BY e.id
            ''', (employee_id,))
            
            if not emp_rows:
                return None
            
            emp = dict(emp_rows[0])
            emp['name'] = f"{emp['prenom']} {emp['nom']}"
            emp['employee_code'] = f"EMP{emp['id']:03d}"
            
            # Statistiques TimeTracker enrichies avec BT
            stats_rows = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total_entries,
                    COALESCE(SUM(total_hours), 0) as total_hours,
                    COALESCE(SUM(total_cost), 0) as total_revenue,
                    COALESCE(AVG(hourly_rate), 0) as avg_hourly_rate,
                    COUNT(CASE WHEN formulaire_bt_id IS NOT NULL THEN 1 END) as bt_entries
                FROM time_entries 
                WHERE employee_id = ? AND total_cost IS NOT NULL
            ''', (employee_id,))
            
            if stats_rows:
                stats = dict(stats_rows[0])
                emp.update({
                    'timetracker_total_entries': stats['total_entries'],
                    'timetracker_total_hours': stats['total_hours'],
                    'timetracker_total_revenue': stats['total_revenue'],
                    'timetracker_avg_rate': stats['avg_hourly_rate'],
                    'timetracker_bt_entries': stats['bt_entries']
                })
            
            return emp
        except Exception as e:
            logger.error(f"Erreur récupération employé {employee_id}: {e}")
            return None
    
    def get_timetracker_statistics_unified(self) -> Dict:
        """Statistiques globales TimeTracker avec intégration BT"""
        try:
            stats = {}
            
            # Employés actifs
            emp_result = self.db.execute_query("SELECT COUNT(*) as count FROM employees WHERE statut = 'ACTIF'")
            stats['total_employees'] = emp_result[0]['count'] if emp_result else 0
            
            # Pointages actifs (avec distinction BT)
            active_result = self.db.execute_query("""
                SELECT 
                    COUNT(*) as total_active,
                    COUNT(CASE WHEN formulaire_bt_id IS NOT NULL THEN 1 END) as active_on_bt
                FROM time_entries 
                WHERE punch_out IS NULL
            """)
            if active_result:
                stats['active_entries'] = active_result[0]['total_active']
                stats['active_entries_bt'] = active_result[0]['active_on_bt']
            
            # Statistiques du jour (avec BT)
            today = datetime.now().strftime('%Y-%m-%d')
            daily_result = self.db.execute_query('''
                SELECT 
                    COALESCE(SUM(total_hours), 0.0) as hours,
                    COALESCE(SUM(total_cost), 0.0) as revenue,
                    COUNT(DISTINCT employee_id) as unique_employees,
                    COUNT(*) as total_entries,
                    COUNT(CASE WHEN formulaire_bt_id IS NOT NULL THEN 1 END) as bt_entries,
                    COALESCE(SUM(CASE WHEN formulaire_bt_id IS NOT NULL THEN total_cost ELSE 0 END), 0) as bt_revenue
                FROM time_entries 
                WHERE DATE(punch_in) = ? AND total_cost IS NOT NULL
            ''', (today,))
            
            if daily_result:
                stats.update({
                    'total_hours_today': daily_result[0]['hours'],
                    'total_revenue_today': daily_result[0]['revenue'],
                    'active_employees_today': daily_result[0]['unique_employees'],
                    'total_entries_today': daily_result[0]['total_entries'],
                    'bt_entries_today': daily_result[0]['bt_entries'],
                    'bt_revenue_today': daily_result[0]['bt_revenue']
                })
            
            # Statistiques BT spécifiques
            bt_stats = self.get_statistiques_bt_timetracker()
            stats['bt_statistics'] = bt_stats
            
            # Taux horaire moyen
            if stats.get('total_hours_today', 0) > 0:
                stats['avg_hourly_rate_today'] = stats['total_revenue_today'] / stats['total_hours_today']
            else:
                stats['avg_hourly_rate_today'] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur statistiques TimeTracker unifiées: {e}")
            return {}
    
    def get_employee_time_entries(self, employee_id: int, limit: int = 50, date_filter: str = None) -> List[Dict]:
        """Récupère les entrées d'un employé avec indication BT"""
        try:
            base_query = '''
                SELECT te.*, p.nom_projet as project_name, p.client_nom_cache as client_name,
                       o.description as task_name, o.sequence_number,
                       wc.nom as work_center_name,
                       f.numero_document as bt_numero, f.priorite as bt_priorite
                FROM time_entries te
                JOIN projects p ON te.project_id = p.id
                LEFT JOIN operations o ON te.operation_id = o.id
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                LEFT JOIN formulaires f ON te.formulaire_bt_id = f.id
                WHERE te.employee_id = ?
            '''
            
            params = [employee_id]
            
            if date_filter:
                base_query += ' AND DATE(te.punch_in) = ?'
                params.append(date_filter)
            
            base_query += ' ORDER BY te.punch_in DESC LIMIT ?'
            params.append(limit)
            
            rows = self.db.execute_query(base_query, tuple(params))
            
            entries = []
            for row in rows:
                entry = dict(row)
                entry['task_name'] = entry['task_name'] or 'Tâche générale'
                entry['client_name'] = entry['client_name'] or 'Client Inconnu'
                
                # Enrichissement avec contexte BT
                if entry['bt_numero']:
                    entry['is_bt_work'] = True
                    entry['bt_context'] = f"BT {entry['bt_numero']} ({entry['bt_priorite']})"
                    entry['work_type'] = 'Bon de Travail'
                else:
                    entry['is_bt_work'] = False
                    entry['work_type'] = 'Projet général'
                
                # Formater les dates
                punch_in = datetime.fromisoformat(entry['punch_in'])
                entry['punch_in_formatted'] = punch_in.strftime('%Y-%m-%d %H:%M:%S')
                
                if entry['punch_out']:
                    punch_out = datetime.fromisoformat(entry['punch_out'])
                    entry['punch_out_formatted'] = punch_out.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    entry['punch_out_formatted'] = 'En cours...'
                    elapsed = (datetime.now() - punch_in).total_seconds() / 3600
                    entry['elapsed_hours'] = elapsed
                
                entries.append(entry)
            
            return entries
        except Exception as e:
            logger.error(f"Erreur récupération historique employé {employee_id}: {e}")
            return []
    
    def get_project_operations(self, project_id: int) -> List[Dict]:
        """Récupère les opérations d'un projet avec statistiques BT et TimeTracker"""
        try:
            rows = self.db.execute_query('''
                SELECT o.id, o.description, o.temps_estime, o.poste_travail, o.sequence_number,
                       o.formulaire_bt_id,
                       wc.nom as work_center_name, wc.cout_horaire, wc.departement,
                       COALESCE(SUM(te.total_hours), 0) as actual_hours,
                       COALESCE(SUM(te.total_cost), 0) as actual_cost,
                       COUNT(te.id) as timetracker_entries,
                       f.numero_document as bt_numero
                FROM operations o
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                LEFT JOIN time_entries te ON o.id = te.operation_id AND te.total_cost IS NOT NULL
                LEFT JOIN formulaires f ON o.formulaire_bt_id = f.id
                WHERE o.project_id = ? 
                GROUP BY o.id
                ORDER BY o.sequence_number, o.description
            ''', (project_id,))
            
            operations = []
            for row in rows:
                op = dict(row)
                op['task_name'] = op['description'] or f"Opération {op['sequence_number']}"
                op['task_code'] = f"OP{op['id']:03d}"
                op['hourly_rate'] = op['cout_horaire'] or 95.0
                op['estimated_hours'] = op['temps_estime'] or 0
                
                # Calcul progression
                if op['estimated_hours'] > 0:
                    op['completion_percentage'] = min(100, (op['actual_hours'] / op['estimated_hours']) * 100)
                else:
                    op['completion_percentage'] = 0
                
                # Contexte BT si applicable
                if op['bt_numero']:
                    op['is_bt_operation'] = True
                    op['bt_context'] = f"BT {op['bt_numero']}"
                else:
                    op['is_bt_operation'] = False
                
                operations.append(op)
            
            return operations
        except Exception as e:
            logger.error(f"Erreur récupération opérations projet {project_id}: {e}")
            return []


# ========================================================================
# FONCTION PRINCIPALE D'INTERFACE UNIFIÉE
# ========================================================================

def show_timetracker_unified_interface():
    """
    Interface principale TimeTracker Pro avec intégration complète BT
    Remplace show_timetracker_interface() et render_bons_travail_tab()
    """
    
    # Vérifier l'accès à la base ERP
    if 'erp_db' not in st.session_state:
        st.error("❌ Accès TimeTracker Pro nécessite une session ERP active")
        st.info("Veuillez redémarrer l'application ERP.")
        return
    
    # Initialiser le TimeTracker unifié
    if 'timetracker_unified' not in st.session_state:
        st.session_state.timetracker_unified = TimeTrackerUnified(st.session_state.erp_db)
    
    tt_unified = st.session_state.timetracker_unified
    
    # En-tête TimeTracker Pro unifié
    st.markdown("""
    <div class='project-header' style='background: linear-gradient(135deg, #00A971 0%, #00673D 100%); color: white; padding: 25px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);'>
        <h1 style='margin: 0; text-align: center; font-size: 2.2em;'>⏱️ TimeTracker Pro - Interface Unifiée</h1>
        <p style='margin: 8px 0 0 0; text-align: center; font-size: 1.1em; opacity: 0.95;'>🔧 Pointage • Bons de Travail • Analytics • Productivité</p>
        <p style='margin: 5px 0 0 0; text-align: center; font-size: 0.9em; opacity: 0.8;'>🗄️ Architecture SQLite Unifiée • Intégration Complète BT ↔ TimeTracker</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Statistiques en temps réel unifiées
    stats = tt_unified.get_timetracker_statistics_unified()
    
    # Métriques principales avec distinction BT
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("👥 Employés Actifs", stats.get('total_employees', 0))
    with col2:
        active_total = stats.get('active_entries', 0)
        active_bt = stats.get('active_entries_bt', 0)
        st.metric("🟢 Pointages Actifs", f"{active_total} ({active_bt} BT)")
    with col3:
        st.metric("⏱️ Heures Aujourd'hui", f"{stats.get('total_hours_today', 0):.1f}h")
    with col4:
        total_rev = stats.get('total_revenue_today', 0)
        bt_rev = stats.get('bt_revenue_today', 0)
        st.metric("💰 Revenus Jour", f"{total_rev:.0f}$ ({bt_rev:.0f}$ BT)")
    with col5:
        total_entries = stats.get('total_entries_today', 0)
        bt_entries = stats.get('bt_entries_today', 0)
        st.metric("📊 Pointages Jour", f"{total_entries} ({bt_entries} BT)")
    
    # Navigation TimeTracker Pro Unifiée
    tab_pointage, tab_gestion_bt, tab_analytics, tab_productivite, tab_admin, tab_system = st.tabs([
        "🕐 Pointage & BTs",
        "🔧 Gestion BTs", 
        "📊 Analytics Unifiés",
        "🏭 Productivité",
        "⚙️ Administration",
        "ℹ️ Système"
    ])
    
    with tab_pointage:
        show_pointage_bts_unified_interface(tt_unified)
    
    with tab_gestion_bt:
        show_gestion_bts_interface(tt_unified)
    
    with tab_analytics:
        show_analytics_unified_interface(tt_unified)
    
    with tab_productivite:
        show_productivity_unified_interface(tt_unified)
    
    with tab_admin:
        show_admin_unified_interface(tt_unified)
    
    with tab_system:
        show_system_unified_interface()


def show_pointage_bts_unified_interface(tt_unified: TimeTrackerUnified):
    """Interface principale fusionnée Pointage + BTs"""
    
    st.markdown("### 🕐 Interface de Pointage avec Bons de Travail Intégrés")
    
    # Récupération des employés
    employees = tt_unified.get_all_employees()
    
    if not employees:
        st.warning("⚠️ Aucun employé actif trouvé dans l'ERP.")
        return
    
    # Sélecteur d'employé enrichi
    employee_options = {emp['id']: emp['full_name_with_role'] for emp in employees}
    
    selected_employee_id = st.selectbox(
        "👤 Sélectionner l'employé:",
        options=list(employee_options.keys()),
        format_func=lambda x: employee_options[x],
        key="timetracker_unified_employee_selector"
    )
    
    if not selected_employee_id:
        return
    
    employee = tt_unified.get_employee_by_id(selected_employee_id)
    current_entry = tt_unified.get_employee_current_entry(selected_employee_id)
    
    # Section STATUS EMPLOYÉ avec BTs assignés
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Informations employé avec stats BT
        st.markdown(f"""
        <div class='info-card' style='background: linear-gradient(135deg, #e6f7f1 0%, #d0f0e6 100%); border-left: 4px solid #00A971;'>
            <h4>👤 {employee['name']}</h4>
            <p><strong>💼 Poste:</strong> {employee.get('poste', 'N/A')}</p>
            <p><strong>🏢 Département:</strong> {employee.get('departement', 'N/A')}</p>
            <p><strong>📋 Projets:</strong> {employee.get('projets_assignes', 0)}</p>
            <p><strong>🔧 BTs Assignés:</strong> {employee.get('bts_assignes', 0)}</p>
            <p><strong>📊 Charge:</strong> {employee.get('charge_travail', 'N/A')}%</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Status pointage avec contexte BT
        if current_entry:
            alert_style = "border-left: 4px solid #10b981; background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);"
            if current_entry['elapsed_hours'] > 8:
                alert_style = "border-left: 4px solid #f59e0b; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);"
            
            st.markdown(f"""
            <div class='info-card' style='{alert_style}'>
                <h4>🟢 POINTÉ ACTUELLEMENT</h4>
                <p><strong>📋 Projet:</strong> {current_entry['project_name']}</p>
                <p><strong>🔧 Type:</strong> {current_entry.get('work_type', 'N/A')}</p>
                {f"<p><strong>🔧 Contexte BT:</strong> {current_entry.get('bt_context', '')}</p>" if current_entry.get('is_bt_work') else ""}
                <p><strong>🕐 Début:</strong> {datetime.fromisoformat(current_entry['punch_in']).strftime('%H:%M:%S')}</p>
                <p><strong>⏱️ Durée:</strong> {current_entry['elapsed_hours']:.2f}h</p>
                <p><strong>💰 Coût estimé:</strong> {current_entry['estimated_cost']:.2f}$ CAD</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='info-card' style='border-left: 4px solid #f59e0b; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);'>
                <h4>🟡 DISPONIBLE POUR POINTAGE</h4>
                <p>Sélectionnez un projet, une tâche ou un Bon de Travail pour commencer</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # PANNEAU BTS ASSIGNÉS - NOUVEAU
        render_bts_assignes_panel(tt_unified, selected_employee_id)
    
    # Section actions de pointage
    if current_entry:
        # Interface punch out
        st.markdown("---")
        st.markdown("#### 🔴 Terminer le pointage")
        
        with st.form("punch_out_unified_form"):
            notes_out = st.text_area(
                "📝 Notes de fin (optionnel):", 
                placeholder="Travail accompli, difficultés, prochaines étapes...",
                height=100
            )
            
            col_out1, col_out2 = st.columns(2)
            with col_out1:
                if st.form_submit_button("🔴 PUNCH OUT", use_container_width=True):
                    try:
                        session_details = tt_unified.punch_out(selected_employee_id, notes_out)
                        
                        success_msg = f"""
                        ✅ **Punch out enregistré !**
                        
                        📊 **Résumé de session:**
                        - ⏱️ Durée: {session_details['total_hours']:.2f}h
                        - 💰 Coût: {session_details['total_cost']:.2f}$ CAD
                        - 📋 Projet: {session_details['project_name']}
                        """
                        
                        if session_details.get('bt_context'):
                            success_msg += f"\n- 🔧 {session_details['bt_context']}"
                        
                        st.success(success_msg)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erreur punch out: {str(e)}")
            
            with col_out2:
                if st.form_submit_button("⏸️ Pause", use_container_width=True):
                    try:
                        session_details = tt_unified.punch_out(selected_employee_id, f"Pause. {notes_out}".strip())
                        st.info(f"⏸️ Pause enregistrée. Durée: {session_details['total_hours']:.2f}h")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erreur pause: {str(e)}")
    
    else:
        # Interface punch in unifiée (projet OU BT)
        st.markdown("---")
        st.markdown("#### 📋 Nouveau Pointage")
        
        # Mode de pointage
        pointage_mode = st.radio(
            "Mode de pointage:",
            ["🔧 Sur un Bon de Travail", "📋 Sur un projet général"],
            horizontal=True,
            key="pointage_mode_unified"
        )
        
        if pointage_mode == "🔧 Sur un Bon de Travail":
            render_bt_punch_in_interface(tt_unified, selected_employee_id)
        else:
            render_project_punch_in_interface(tt_unified, selected_employee_id)
    
    # Historique unifié avec distinction BT
    st.markdown("---")
    render_unified_history_interface(tt_unified, selected_employee_id)


def render_bts_assignes_panel(tt_unified: TimeTrackerUnified, employee_id: int):
    """Panneau des BTs assignés avec actions directes"""
    
    bts_assignes = tt_unified.get_bts_assignes_employe(employee_id)
    
    with st.expander(f"🔧 {len(bts_assignes)} Bon(s) de Travail Assigné(s)", expanded=True):
        if not bts_assignes:
            st.info("Aucun Bon de Travail assigné actuellement")
            return
        
        for bt in bts_assignes:
            # Déterminer la couleur selon la priorité
            if bt['priorite'] == 'CRITIQUE':
                priorite_color = "#ef4444"
                priorite_icon = "🔴"
            elif bt['priorite'] == 'URGENT':
                priorite_color = "#f59e0b"
                priorite_icon = "🟡"
            else:
                priorite_color = "#10b981"
                priorite_icon = "🟢"
            
            # Card BT avec progression
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"""
                <div style='border-left: 4px solid {priorite_color}; padding: 10px; margin-bottom: 10px; background: white; border-radius: 6px;'>
                    <h6 style='margin: 0; color: {priorite_color};'>{priorite_icon} BT {bt['numero_document']}</h6>
                    <p style='margin: 2px 0; font-size: 0.9em;'><strong>Projet:</strong> {bt.get('nom_projet', 'N/A')[:30]}...</p>
                    <p style='margin: 2px 0; font-size: 0.9em;'><strong>Échéance:</strong> {bt.get('date_echeance', 'N/A')}</p>
                    <div style='background: #e5e7eb; border-radius: 10px; height: 20px; margin: 5px 0;'>
                        <div style='background: {priorite_color}; height: 100%; width: {bt.get("progression_timetracker", 0)}%; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: 600;'>
                            {bt.get("progression_timetracker", 0):.0f}%
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.metric("⏱️ Heures", f"{bt['heures_pointees']:.1f}h", help="Heures déjà pointées sur ce BT")
                st.metric("💰 Coût", f"{bt['cout_total']:.0f}$", help="Coût total généré")
            
            with col3:
                # Vérifier si l'employé n'est pas déjà en pointage
                current_entry = tt_unified.get_employee_current_entry(employee_id)
                
                if not current_entry:
                    if st.button("▶️ Pointer", key=f"start_bt_{bt['bt_id']}", use_container_width=True, type="primary"):
                        try:
                            entry_id = tt_unified.punch_in_sur_bt_enhanced(employee_id, bt['bt_id'])
                            st.success(f"✅ Pointage démarré sur BT {bt['numero_document']}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur: {e}")
                else:
                    st.info("Déjà en pointage", icon="⏱️")
                
                if st.button("👁️ Détails", key=f"details_bt_{bt['bt_id']}", use_container_width=True):
                    st.session_state.bt_details_modal = bt['bt_id']
                    st.rerun()


def render_bt_punch_in_interface(tt_unified: TimeTrackerUnified, employee_id: int):
    """Interface de pointage spécialisée pour les BTs"""
    
    bts_assignes = tt_unified.get_bts_assignes_employe(employee_id)
    
    if not bts_assignes:
        st.warning("⚠️ Aucun Bon de Travail assigné. Contactez votre superviseur.")
        return
    
    with st.form("bt_punch_in_form"):
        st.markdown("**🔧 Pointage sur Bon de Travail:**")
        
        # Sélection du BT
        bt_options = {
            bt['bt_id']: f"BT {bt['numero_document']} - {bt.get('nom_projet', 'N/A')} ({bt['priorite']})"
            for bt in bts_assignes
        }
        
        selected_bt_id = st.selectbox(
            "Bon de Travail:",
            options=list(bt_options.keys()),
            format_func=lambda x: bt_options[x],
            key="bt_selection_punch_in"
        )
        
        if selected_bt_id:
            # Afficher les détails du BT sélectionné
            selected_bt = next(bt for bt in bts_assignes if bt['bt_id'] == selected_bt_id)
            
            col_bt1, col_bt2, col_bt3 = st.columns(3)
            with col_bt1:
                st.metric("📊 Progression", f"{selected_bt.get('progression_timetracker', 0):.0f}%")
            with col_bt2:
                st.metric("⏱️ Heures pointées", f"{selected_bt['heures_pointees']:.1f}h")
            with col_bt3:
                st.metric("💰 Coût généré", f"{selected_bt['cout_total']:.0f}$")
        
        # Notes de début
        notes_bt = st.text_area(
            "📝 Notes de début (optionnel):",
            placeholder="Objectifs de la session, plan de travail...",
            height=80,
            key="bt_notes_punch_in"
        )
        
        # Bouton de pointage
        if st.form_submit_button("🔧 DÉMARRER POINTAGE BT", use_container_width=True, type="primary"):
            if selected_bt_id:
                try:
                    entry_id = tt_unified.punch_in_sur_bt_enhanced(employee_id, selected_bt_id, notes_bt)
                    
                    selected_bt = next(bt for bt in bts_assignes if bt['bt_id'] == selected_bt_id)
                    
                    st.success(f"""
                    ✅ **Pointage BT démarré !**
                    
                    📊 **Détails:**
                    - 🔧 BT: {selected_bt['numero_document']}
                    - 📋 Projet: {selected_bt.get('nom_projet', 'N/A')}
                    - 🆔 Entry ID: {entry_id}
                    - 🕐 Heure début: {datetime.now().strftime('%H:%M:%S')}
                    """)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur démarrage pointage BT: {str(e)}")


def render_project_punch_in_interface(tt_unified: TimeTrackerUnified, employee_id: int):
    """Interface de pointage pour projets généraux"""
    
    projects = tt_unified.get_active_projects()
    
    if not projects:
        st.warning("❌ Aucun projet actif disponible.")
        return
    
    with st.form("project_punch_in_form"):
        st.markdown("**📋 Pointage sur projet général:**")
        
        # Sélection du projet
        project_options = {
            p['id']: f"{p['project_name']} - {p['client_name']} (BTs: {p['total_bts']})"
            for p in projects
        }
        
        selected_project_id = st.selectbox(
            "Projet:",
            options=list(project_options.keys()),
            format_func=lambda x: project_options[x],
            key="project_selection_punch_in"
        )
        
        # Sélection de l'opération
        selected_operation_id = None
        if selected_project_id:
            operations = tt_unified.get_project_operations(selected_project_id)
            
            if operations:
                operation_options = {
                    op['id']: f"OP{op['sequence_number']:02d} - {op['task_name']} ({op['hourly_rate']:.0f}$/h)"
                    for op in operations
                }
                
                selected_operation_id = st.selectbox(
                    "Opération/Tâche:",
                    options=[None] + list(operation_options.keys()),
                    format_func=lambda x: "🔧 Tâche générale (95$/h)" if x is None else operation_options[x],
                    key="operation_selection_punch_in"
                )
        
        # Notes
        notes_project = st.text_area(
            "📝 Notes de début:",
            placeholder="Objectifs, plan de travail, outils nécessaires...",
            height=80,
            key="project_notes_punch_in"
        )
        
        # Bouton de pointage
        if st.form_submit_button("📋 DÉMARRER POINTAGE PROJET", use_container_width=True):
            if selected_project_id:
                try:
                    entry_id = tt_unified.punch_in(employee_id, selected_project_id, selected_operation_id, None, notes_project)
                    
                    selected_project = next(p for p in projects if p['id'] == selected_project_id)
                    
                    st.success(f"""
                    ✅ **Pointage projet démarré !**
                    
                    📊 **Détails:**
                    - 📋 Projet: {selected_project['project_name']}
                    - 👤 Client: {selected_project['client_name']}
                    - 🆔 Entry ID: {entry_id}
                    - 🕐 Heure début: {datetime.now().strftime('%H:%M:%S')}
                    """)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur pointage projet: {str(e)}")


def render_unified_history_interface(tt_unified: TimeTrackerUnified, employee_id: int):
    """Historique unifié avec distinction BT/Projet"""
    
    st.markdown("#### 📊 Historique de Pointage")
    
    # Filtres
    hist_col1, hist_col2, hist_col3 = st.columns(3)
    with hist_col1:
        limit_entries = st.selectbox("Nombre d'entrées:", [10, 25, 50], index=0)
    with hist_col2:
        date_filter = st.date_input("Filtrer par date:", value=None)
    with hist_col3:
        work_type_filter = st.selectbox("Type de travail:", ["Tous", "Bons de Travail", "Projets généraux"])
    
    # Récupérer les entrées
    date_filter_str = date_filter.strftime('%Y-%m-%d') if date_filter else None
    entries = tt_unified.get_employee_time_entries(employee_id, limit_entries, date_filter_str)
    
    # Filtrer par type de travail
    if work_type_filter == "Bons de Travail":
        entries = [e for e in entries if e.get('is_bt_work')]
    elif work_type_filter == "Projets généraux":
        entries = [e for e in entries if not e.get('is_bt_work')]
    
    if entries:
        # Métriques de l'historique
        total_hours = sum(e.get('total_hours', 0) for e in entries if e.get('total_hours'))
        total_cost = sum(e.get('total_cost', 0) for e in entries if e.get('total_cost'))
        bt_entries = len([e for e in entries if e.get('is_bt_work')])
        
        hist_met_col1, hist_met_col2, hist_met_col3, hist_met_col4 = st.columns(4)
        with hist_met_col1:
            st.metric("📊 Entrées", len(entries))
        with hist_met_col2:
            st.metric("🔧 Entrées BT", bt_entries)
        with hist_met_col3:
            st.metric("⏱️ Total Heures", f"{total_hours:.1f}h")
        with hist_met_col4:
            st.metric("💰 Total Revenus", f"{total_cost:.0f}$")
        
        # Tableau des entrées
        df_history = []
        for entry in entries:
            # Déterminer l'icône et couleur selon le type
            if entry.get('is_bt_work'):
                type_icon = "🔧"
                type_color = "#00A971"
                work_detail = entry.get('bt_context', 'BT')
            else:
                type_icon = "📋"
                type_color = "#3b82f6"
                work_detail = "Projet général"
            
            punch_in = datetime.fromisoformat(entry['punch_in'])
            
            if entry['punch_out']:
                punch_out_str = datetime.fromisoformat(entry['punch_out']).strftime('%H:%M:%S')
                duration_str = f"{entry['total_hours']:.2f}h"
                cost_str = f"{entry['total_cost']:.2f}$"
                status = "✅ Terminé"
            else:
                punch_out_str = "En cours..."
                elapsed = entry.get('elapsed_hours', 0)
                duration_str = f"{elapsed:.2f}h (en cours)"
                cost_str = f"{elapsed * entry['hourly_rate']:.2f}$ (estimé)"
                status = "🟢 En cours"
            
            df_history.append({
                '📅 Date': punch_in.strftime('%Y-%m-%d'),
                '🕐 Début': punch_in.strftime('%H:%M:%S'),
                '🕑 Fin': punch_out_str,
                f'{type_icon} Type': work_detail,
                '📋 Projet': entry['project_name'],
                '🔧 Tâche': entry['task_name'],
                '⏱️ Durée': duration_str,
                '💰 Coût': cost_str,
                '🚦 Statut': status
            })
        
        st.dataframe(pd.DataFrame(df_history), use_container_width=True)
        
    else:
        message = "Aucun historique de pointage"
        if date_filter_str:
            message += f" pour le {date_filter_str}"
        if work_type_filter != "Tous":
            message += f" ({work_type_filter.lower()})"
        st.info(message + ".")


def show_gestion_bts_interface(tt_unified: TimeTrackerUnified):
    """Interface complète de gestion des BTs dans TimeTracker"""
    
    st.markdown("### 🔧 Gestion Complète des Bons de Travail")
    
    # Navigation BT
    bt_action = st.radio(
        "Actions BT:",
        ["📋 Dashboard & Liste", "➕ Créer Nouveau BT", "📊 Statistiques BTs", "📈 Productivité BTs"],
        horizontal=True,
        key="bt_action_unified"
    )
    
    if bt_action == "📋 Dashboard & Liste":
        render_bt_dashboard_unifie(tt_unified)
    elif bt_action == "➕ Créer Nouveau BT":
        render_bt_creation_unifiee(tt_unified)
    elif bt_action == "📊 Statistiques BTs":
        render_bt_stats_unifiees(tt_unified)
    elif bt_action == "📈 Productivité BTs":
        render_bt_productivite_unifiee(tt_unified)


def render_bt_dashboard_unifie(tt_unified: TimeTrackerUnified):
    """Dashboard BTs avec données TimeTracker intégrées"""
    
    st.markdown("#### 📋 Dashboard Bons de Travail Unifié")
    
    # Récupérer le dashboard unifié
    dashboard = tt_unified.get_bt_dashboard_unifie()
    
    if not dashboard:
        st.warning("Aucune donnée de BT disponible")
        return
    
    # Métriques globales BT + TimeTracker
    stats_globales = dashboard.get('stats_globales', {})
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🔧 Pointages BT", stats_globales.get('nb_pointages', 0))
    with col2:
        st.metric("👥 Employés", stats_globales.get('nb_employes_distinct', 0))
    with col3:
        st.metric("⏱️ Heures Totales", f"{stats_globales.get('total_heures', 0):.1f}h")
    with col4:
        st.metric("💰 Revenus BT", f"{stats_globales.get('total_cout', 0):.0f}$")
    with col5:
        st.metric("📋 BTs avec Pointages", stats_globales.get('nb_bts_avec_pointages', 0))
    
    # Graphiques de répartition
    col_graph1, col_graph2 = st.columns(2)
    
    with col_graph1:
        # Répartition par statut
        stats_status = dashboard.get('stats_par_statut', [])
        if stats_status:
            fig_status = px.pie(
                values=[s['count'] for s in stats_status],
                names=[s['statut'] for s in stats_status],
                title="📊 Répartition BTs par Statut"
            )
            st.plotly_chart(fig_status, use_container_width=True)
    
    with col_graph2:
        # Répartition par priorité
        stats_priority = dashboard.get('stats_par_priorite', [])
        if stats_priority:
            fig_priority = px.bar(
                x=[s['priorite'] for s in stats_priority],
                y=[s['count'] for s in stats_priority],
                title="🎯 BTs par Priorité"
            )
            st.plotly_chart(fig_priority, use_container_width=True)
    
    # Liste des BTs récents avec TimeTracker
    st.markdown("---")
    st.markdown("#### 🔧 Bons de Travail Récents")
    
    # Récupérer les BTs avec données TimeTracker
    bts_list = tt_unified._get_bts_with_timetracker_data()
    
    if bts_list:
        for bt in bts_list[:10]:  # Limiter à 10
            render_bt_card_enrichie(bt)
    else:
        st.info("Aucun Bon de Travail trouvé")


def render_bt_creation_unifiee(tt_unified: TimeTrackerUnified):
    """Interface de création BT unifiée avec intégration TimeTracker"""
    
    st.markdown("#### ➕ Créer un Nouveau Bon de Travail")
    
    # Gestion du succès
    if st.session_state.get('bt_creation_success_unified'):
        success_info = st.session_state.bt_creation_success_unified
        
        st.success(f"✅ Bon de Travail {success_info['numero']} créé avec intégration TimeTracker!")
        
        col_next1, col_next2, col_next3 = st.columns(3)
        
        with col_next1:
            if st.button("📋 Voir Dashboard", use_container_width=True):
                st.session_state.bt_creation_success_unified = None
                st.rerun()
        
        with col_next2:
            if st.button("👁️ Voir Détails", use_container_width=True):
                st.session_state.selected_bt_details = success_info['bt_id']
                st.session_state.bt_creation_success_unified = None
                st.rerun()
        
        with col_next3:
            if st.button("➕ Créer un Autre", use_container_width=True):
                st.session_state.bt_creation_success_unified = None
                st.rerun()
        
        return
    
    # Récupération des données
    projets = tt_unified.get_active_projects()
    employes = tt_unified.get_all_employees()
    
    if not projets or not employes:
        st.error("❌ Données insuffisantes pour créer un BT (projets ou employés manquants)")
        return
    
    # Formulaire de création BT
    with st.form("bt_creation_unified_form", clear_on_submit=True):
        st.markdown("**📝 Informations Générales**")
        
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            # Génération du numéro BT
            numero_bt = f"BT{datetime.now().strftime('%Y%m%d')}{len(projets):03d}"
            st.text_input("Numéro BT", value=numero_bt, disabled=True)
            
            # Projet obligatoire
            projet_options = [(p['id'], f"#{p['id']} - {p['project_name']}") for p in projets]
            projet_id = st.selectbox(
                "Projet *",
                options=[p[0] for p in projet_options],
                format_func=lambda x: next((p[1] for p in projet_options if p[0] == x), ""),
                help="Projet obligatoire pour les Bons de Travail"
            )
        
        with col_info2:
            # Responsable
            employe_options = [(e['id'], f"{e['name']} - {e.get('poste', 'N/A')}") for e in employes]
            employe_id = st.selectbox(
                "Responsable *",
                options=[e[0] for e in employe_options],
                format_func=lambda x: next((e[1] for e in employe_options if e[0] == x), "")
            )
            
            priorite = st.selectbox("Priorité", ["NORMAL", "URGENT", "CRITIQUE"], index=0)
        
        # Dates
        col_dates = st.columns(2)
        with col_dates[0]:
            date_debut = st.date_input("Date début", datetime.now().date())
        with col_dates[1]:
            date_fin = st.date_input("Date fin", datetime.now().date() + timedelta(days=7))
        
        # Instructions
        st.markdown("**📋 Instructions de Travail**")
        instructions = st.text_area(
            "Description du travail à effectuer:",
            placeholder="Description détaillée des tâches, objectifs, contraintes...",
            height=150
        )
        
        # Assignation d'employés
        st.markdown("**👥 Assignation d'Employés**")
        employes_assignes = st.multiselect(
            "Employés assignés:",
            options=[e['id'] for e in employes],
            format_func=lambda x: next((e['name'] for e in employes if e['id'] == x), ""),
            help="Employés qui pourront pointer sur ce BT"
        )
        
        # Estimation
        st.markdown("**⏱️ Estimation**")
        col_est1, col_est2 = st.columns(2)
        with col_est1:
            temps_estime = st.number_input("Temps estimé (heures)", min_value=0.0, step=0.5, value=8.0)
        with col_est2:
            cout_estime = st.number_input("Coût estimé main d'œuvre ($)", min_value=0.0, step=50.0, value=760.0)
        
        # Boutons de soumission
        col_submit1, col_submit2 = st.columns(2)
        
        with col_submit1:
            if st.form_submit_button("🔧 Créer Bon de Travail", use_container_width=True, type="primary"):
                if not projet_id or not employe_id or not instructions:
                    st.error("❌ Veuillez remplir tous les champs obligatoires")
                else:
                    # Construire les données BT
                    data = {
                        'numero_document': numero_bt,
                        'type_formulaire': 'BON_TRAVAIL',
                        'project_id': projet_id,
                        'employee_id': employe_id,
                        'statut': 'VALIDÉ',  # Prêt pour pointage
                        'priorite': priorite,
                        'date_creation': date_debut,
                        'date_echeance': date_fin,
                        'description': instructions,
                        'notes': f"""=== BON DE TRAVAIL UNIFIÉ ===
Numéro: {numero_bt}
Projet: {next((p['project_name'] for p in projets if p['id'] == projet_id), 'N/A')}
Responsable: {next((e['name'] for e in employes if e['id'] == employe_id), 'N/A')}

Instructions: {instructions}

=== INTÉGRATION TIMETRACKER ===
Temps estimé: {temps_estime}h
Coût estimé: {cout_estime}$
Employés assignés: {len(employes_assignes)} personne(s)
""",
                        'employes_assignes': employes_assignes,
                        'temps_estime_total': temps_estime,
                        'cout_main_oeuvre_estime': cout_estime,
                        'operations_detaillees': [
                            {
                                'description': f"Exécution BT {numero_bt}",
                                'temps_prevu': temps_estime,
                                'statut': 'À FAIRE',
                                'assigne': next((e['name'] for e in employes if e['id'] == employe_id), 'N/A')
                            }
                        ]
                    }
                    
                    # Créer le BT avec intégration
                    bt_id = tt_unified.creer_bon_travail_integre(data)
                    
                    if bt_id:
                        st.session_state.bt_creation_success_unified = {
                            'bt_id': bt_id,
                            'numero': numero_bt,
                            'urgent': priorite in ['URGENT', 'CRITIQUE']
                        }
                        st.rerun()
        
        with col_submit2:
            if st.form_submit_button("🔄 Réinitialiser", use_container_width=True):
                st.rerun()


def render_bt_stats_unifiees(tt_unified: TimeTrackerUnified):
    """Statistiques BTs unifiées avec TimeTracker"""
    
    st.markdown("#### 📊 Statistiques Bons de Travail Unifiées")
    
    # Statistiques globales
    stats_bt = tt_unified.get_statistiques_bt_timetracker()
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Total Pointages BT", stats_bt.get('nb_pointages', 0))
    with col2:
        st.metric("👥 Employés Actifs BT", stats_bt.get('nb_employes_distinct', 0))
    with col3:
        st.metric("⏱️ Heures Totales BT", f"{stats_bt.get('total_heures', 0):.1f}h")
    with col4:
        st.metric("💰 Revenus BT", f"{stats_bt.get('total_cout', 0):.0f}$ CAD")
    
    # Graphiques d'analyse
    st.markdown("#### 📈 Analyse des Performances")
    
    # Récupérer les données pour graphiques
    bts_data = tt_unified._get_bt_performance_data()
    
    if bts_data:
        col_graph1, col_graph2 = st.columns(2)
        
        with col_graph1:
            # Évolution des heures par BT
            fig_hours = px.bar(
                x=[bt['numero_document'] for bt in bts_data],
                y=[bt['total_hours'] for bt in bts_data],
                title="⏱️ Heures par Bon de Travail",
                labels={'x': 'Bons de Travail', 'y': 'Heures'}
            )
            st.plotly_chart(fig_hours, use_container_width=True)
        
        with col_graph2:
            # Efficacité par BT (temps réel vs estimé)
            efficiency_data = []
            for bt in bts_data:
                if bt['temps_estime'] > 0:
                    efficiency = (bt['total_hours'] / bt['temps_estime']) * 100
                    efficiency_data.append({
                        'BT': bt['numero_document'],
                        'Efficacité': min(200, efficiency)  # Plafonner à 200%
                    })
            
            if efficiency_data:
                fig_efficiency = px.bar(
                    x=[e['BT'] for e in efficiency_data],
                    y=[e['Efficacité'] for e in efficiency_data],
                    title="📊 Efficacité (% temps réel vs estimé)",
                    labels={'x': 'Bons de Travail', 'y': 'Efficacité (%)'}
                )
                fig_efficiency.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="100% = Dans les temps")
                st.plotly_chart(fig_efficiency, use_container_width=True)
    
    # Tableau détaillé
    st.markdown("#### 📋 Détail par Bon de Travail")
    
    if bts_data:
        df_bt_stats = pd.DataFrame([
            {
                'BT': bt['numero_document'],
                'Statut': bt['statut'],
                'Heures Pointées': f"{bt['total_hours']:.1f}h",
                'Heures Estimées': f"{bt['temps_estime']:.1f}h",
                'Revenus': f"{bt['total_cost']:.0f}$",
                'Employés': bt['nb_employes'],
                'Progression': f"{bt['progression']:.0f}%"
            }
            for bt in bts_data
        ])
        
        st.dataframe(df_bt_stats, use_container_width=True)
    else:
        st.info("Aucune donnée de performance BT disponible")


def render_bt_productivite_unifiee(tt_unified: TimeTrackerUnified):
    """Analyse de productivité BT avec TimeTracker"""
    
    st.markdown("#### 📈 Productivité Bons de Travail")
    
    # Période d'analyse
    col_period1, col_period2 = st.columns(2)
    with col_period1:
        periode_jours = st.selectbox("Période d'analyse:", [7, 15, 30, 60, 90], index=2)
    
    with col_period2:
        if st.button("📊 Générer Rapport Productivité", use_container_width=True):
            # Générer le rapport de productivité BT
            rapport = tt_unified._generer_rapport_productivite_bt(periode_jours)
            
            if rapport:
                st.success(f"✅ Rapport généré pour {rapport['periode']}")
                
                # Métriques du rapport
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                
                with col_r1:
                    st.metric("🔧 BTs Terminés", rapport.get('total_bt_termines', 0))
                with col_r2:
                    st.metric("⏱️ Durée Moyenne", f"{rapport.get('duree_moyenne_globale', 0):.1f}j")
                with col_r3:
                    st.metric("👥 Employés Actifs", len(rapport.get('employes', [])))
                with col_r4:
                    st.metric("💰 Revenus Générés", f"{rapport.get('revenus_totaux', 0):.0f}$")
                
                # Top performers
                if rapport.get('employes'):
                    st.markdown("#### 🏆 Top Performers")
                    
                    col_top1, col_top2 = st.columns(2)
                    
                    with col_top1:
                        st.markdown("**🔧 Plus de BTs terminés:**")
                        top_bt = sorted(rapport['employes'], key=lambda x: x['nb_bt_termines'], reverse=True)[:5]
                        for i, emp in enumerate(top_bt, 1):
                            st.markdown(f"{i}. {emp['employe_nom']} - {emp['nb_bt_termines']} BTs")
                    
                    with col_top2:
                        st.markdown("**⚡ Plus efficaces:**")
                        top_eff = sorted(rapport['employes'], key=lambda x: x.get('duree_moyenne', 999))[:5]
                        for i, emp in enumerate(top_eff, 1):
                            st.markdown(f"{i}. {emp['employe_nom']} - {emp.get('duree_moyenne', 0):.1f}j/BT")
                
                # Recommandations
                if rapport.get('recommandations'):
                    st.markdown("#### 💡 Recommandations")
                    for rec in rapport['recommandations']:
                        st.info(rec)
            else:
                st.warning("Aucune donnée pour cette période")
    
    # Conseils d'optimisation
    st.markdown("#### 💡 Conseils d'Optimisation DG Inc.")
    
    conseils = [
        "📊 Suivez l'avancement des BTs en temps réel via TimeTracker",
        "👥 Équilibrez la charge de travail entre les employés",
        "⏱️ Comparez temps réels vs estimations pour améliorer la planification",
        "🔧 Optimisez l'assignation des postes de travail",
        "📈 Utilisez les données TimeTracker pour ajuster les estimations futures",
        "🎯 Priorisez les BTs critiques et urgents",
        "📞 Maintenez une communication efficace avec l'équipe"
    ]
    
    for conseil in conseils:
        st.markdown(f"- {conseil}")


def render_bt_card_enrichie(bt: Dict):
    """Affiche une card BT enrichie avec données TimeTracker"""
    
    # Déterminer les couleurs
    priorite_color = {"CRITIQUE": "#ef4444", "URGENT": "#f59e0b", "NORMAL": "#10b981"}.get(bt.get('priorite'), "#6b7280")
    statut_color = {"TERMINÉ": "#059669", "EN COURS": "#3b82f6", "VALIDÉ": "#f59e0b"}.get(bt.get('statut'), "#6b7280")
    
    # Progression
    progression = bt.get('progression', 0)
    
    st.markdown(f"""
    <div style='border: 1px solid #e5e7eb; border-left: 4px solid {priorite_color}; border-radius: 8px; padding: 15px; margin: 10px 0; background: white;'>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>
            <h4 style='margin: 0; color: {priorite_color};'>BT {bt.get('numero_document', 'N/A')}</h4>
            <span style='background: {statut_color}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 600;'>
                {bt.get('statut', 'N/A')}
            </span>
        </div>
        
        <div style='display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 10px;'>
            <div>
                <strong>📋 Projet:</strong><br>
                <span>{bt.get('nom_projet', 'N/A')[:25]}...</span>
            </div>
            <div>
                <strong>👤 Responsable:</strong><br>
                <span>{bt.get('employee_nom', 'N/A')[:20]}...</span>
            </div>
            <div>
                <strong>🏁 Échéance:</strong><br>
                <span>{bt.get('date_echeance', 'N/A')}</span>
            </div>
        </div>
        
        <div style='display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 10px; margin-bottom: 10px; background: #f8f9fa; padding: 8px; border-radius: 4px;'>
            <div style='text-align: center;'>
                <strong>⏱️ Heures TT:</strong><br>
                <span>{bt.get('timetracker_hours', 0):.1f}h</span>
            </div>
            <div style='text-align: center;'>
                <strong>💰 Revenus TT:</strong><br>
                <span>{bt.get('timetracker_revenue', 0):.0f}$</span>
            </div>
            <div style='text-align: center;'>
                <strong>👥 Employés:</strong><br>
                <span>{bt.get('nb_employes_assignes', 0)}</span>
            </div>
            <div style='text-align: center;'>
                <strong>📊 Progression:</strong><br>
                <span>{progression:.0f}%</span>
            </div>
        </div>
        
        <div style='background: #e5e7eb; border-radius: 10px; height: 20px; margin: 10px 0;'>
            <div style='background: {priorite_color}; height: 100%; width: {progression}%; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: 600;'>
                {progression:.0f}%
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Boutons d'action
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
    
    with col_btn1:
        if st.button("👁️ Voir", key=f"voir_bt_card_{bt.get('id')}", use_container_width=True):
            st.session_state.selected_bt_details = bt.get('id')
            st.rerun()
    
    with col_btn2:
        if st.button("⏱️ TimeTracker", key=f"tt_bt_card_{bt.get('id')}", use_container_width=True):
            st.session_state.bt_timetracker_focus = bt.get('id')
            st.rerun()
    
    with col_btn3:
        if bt.get('statut') in ['VALIDÉ', 'EN COURS'] and progression >= 90:
            if st.button("✅ Terminer", key=f"terminer_bt_card_{bt.get('id')}", use_container_width=True):
                if tt_unified._marquer_bt_termine(bt.get('id'), 1, "Marqué terminé depuis dashboard"):
                    st.success("✅ BT terminé!")
                    st.rerun()
        else:
            st.button("✅ Terminer", disabled=True, use_container_width=True, help="BT pas prêt")
    
    with col_btn4:
        if st.button("📊 Analytics", key=f"analytics_bt_card_{bt.get('id')}", use_container_width=True):
            st.session_state.bt_analytics_focus = bt.get('id')
            st.rerun()


def show_analytics_unified_interface(tt_unified: TimeTrackerUnified):
    """Analytics fusionnés BTs + TimeTracker"""
    
    st.markdown("### 📊 Analytics Unifiés - BTs & TimeTracker")
    
    # Sélection de période
    col_period1, col_period2, col_period3 = st.columns(3)
    
    with col_period1:
        period_preset = st.selectbox("Période:", ["7 jours", "30 jours", "3 mois", "Personnalisée"])
    
    if period_preset == "Personnalisée":
        with col_period2:
            start_date = st.date_input("Du:", datetime.now().date() - timedelta(days=30))
        with col_period3:
            end_date = st.date_input("Au:", datetime.now().date())
    else:
        period_days = {"7 jours": 7, "30 jours": 30, "3 mois": 90}[period_preset]
        start_date = datetime.now().date() - timedelta(days=period_days)
        end_date = datetime.now().date()
    
    # Analytics fusionnés
    analytics_data = tt_unified._get_unified_analytics(start_date, end_date)
    
    # Métriques unifiées
    col_metrics1, col_metrics2, col_metrics3, col_metrics4 = st.columns(4)
    
    with col_metrics1:
        st.metric("⏱️ Total Heures", f"{analytics_data.get('total_hours', 0):.1f}h")
    with col_metrics2:
        st.metric("💰 Total Revenus", f"{analytics_data.get('total_revenue', 0):.0f}$")
    with col_metrics3:
        bt_hours = analytics_data.get('bt_hours', 0)
        total_hours = analytics_data.get('total_hours', 1)
        bt_percentage = (bt_hours / total_hours * 100) if total_hours > 0 else 0
        st.metric("🔧 % Heures BT", f"{bt_percentage:.1f}%")
    with col_metrics4:
        avg_efficiency = analytics_data.get('avg_efficiency', 0)
        st.metric("📊 Efficacité Moy.", f"{avg_efficiency:.1f}%")
    
    # Graphiques d'analyse
    col_graph1, col_graph2 = st.columns(2)
    
    with col_graph1:
        # Évolution quotidienne
        daily_data = analytics_data.get('daily_breakdown', [])
        if daily_data:
            fig_daily = px.line(
                x=[d['date'] for d in daily_data],
                y=[d['total_hours'] for d in daily_data],
                title="📈 Évolution Quotidienne des Heures",
                labels={'x': 'Date', 'y': 'Heures'}
            )
            # Ajouter les heures BT
            fig_daily.add_scatter(
                x=[d['date'] for d in daily_data],
                y=[d['bt_hours'] for d in daily_data],
                name='Heures BT',
                line=dict(color='#00A971')
            )
            st.plotly_chart(fig_daily, use_container_width=True)
    
    with col_graph2:
        # Répartition par type de travail
        work_types = analytics_data.get('work_type_breakdown', {})
        if work_types:
            fig_types = px.pie(
                values=list(work_types.values()),
                names=list(work_types.keys()),
                title="🔧 Répartition par Type de Travail"
            )
            st.plotly_chart(fig_types, use_container_width=True)
    
    # Tableau de performance par employé
    st.markdown("#### 👥 Performance par Employé")
    
    employee_stats = analytics_data.get('employee_performance', [])
    if employee_stats:
        df_employees = pd.DataFrame([
            {
                'Employé': emp['name'],
                'Heures Totales': f"{emp['total_hours']:.1f}h",
                'Heures BT': f"{emp['bt_hours']:.1f}h",
                '% BT': f"{(emp['bt_hours']/emp['total_hours']*100) if emp['total_hours'] > 0 else 0:.1f}%",
                'Revenus': f"{emp['total_revenue']:.0f}$",
                'BTs Travaillés': emp.get('bt_count', 0),
                'Efficacité': f"{emp.get('efficiency', 0):.1f}%"
            }
            for emp in employee_stats
        ])
        
        st.dataframe(df_employees, use_container_width=True)
    
    # Analyse de rentabilité
    st.markdown("#### 💰 Analyse de Rentabilité")
    
    profitability = analytics_data.get('profitability_analysis', {})
    
    col_profit1, col_profit2, col_profit3 = st.columns(3)
    
    with col_profit1:
        st.metric(
            "💰 Revenus BT",
            f"{profitability.get('bt_revenue', 0):.0f}$",
            help="Revenus générés par les Bons de Travail"
        )
    
    with col_profit2:
        st.metric(
            "📊 Marge Estimée",
            f"{profitability.get('estimated_margin', 0):.1f}%",
            help="Marge estimée basée sur les coûts de main d'œuvre"
        )
    
    with col_profit3:
        roi = profitability.get('roi_timetracker', 0)
        st.metric(
            "📈 ROI TimeTracker",
            f"{roi:.1f}%",
            help="Retour sur investissement du système TimeTracker"
        )


def show_productivity_unified_interface(tt_unified: TimeTrackerUnified):
    """Interface de productivité unifiée"""
    
    st.markdown("### 🏭 Productivité Unifiée - BTs & Projets")
    
    # Mode d'analyse
    analysis_mode = st.radio(
        "Mode d'analyse:",
        ["👥 Par Employé", "🔧 Par Bon de Travail", "📋 Par Projet", "🏭 Par Poste de Travail"],
        horizontal=True
    )
    
    if analysis_mode == "👥 Par Employé":
        render_employee_productivity_analysis(tt_unified)
    elif analysis_mode == "🔧 Par Bon de Travail":
        render_bt_productivity_analysis(tt_unified)
    elif analysis_mode == "📋 Par Projet":
        render_project_productivity_analysis(tt_unified)
    elif analysis_mode == "🏭 Par Poste de Travail":
        render_workstation_productivity_analysis(tt_unified)


def render_employee_productivity_analysis(tt_unified: TimeTrackerUnified):
    """Analyse de productivité par employé"""
    
    st.markdown("#### 👥 Productivité par Employé")
    
    employees = tt_unified.get_all_employees()
    employee_productivity = []
    
    for emp in employees:
        # Récupérer les stats de productivité
        productivity_stats = tt_unified._get_employee_productivity_stats(emp['id'])
        
        if productivity_stats['total_hours'] > 0:
            employee_productivity.append({
                'id': emp['id'],
                'name': emp['name'],
                'departement': emp.get('departement', 'N/A'),
                'total_hours': productivity_stats['total_hours'],
                'bt_hours': productivity_stats['bt_hours'],
                'total_revenue': productivity_stats['total_revenue'],
                'bt_revenue': productivity_stats['bt_revenue'],
                'efficiency': productivity_stats['efficiency'],
                'bt_count': productivity_stats['bt_count']
            })
    
    if employee_productivity:
        # Top performers
        col_top1, col_top2, col_top3 = st.columns(3)
        
        with col_top1:
            st.markdown("**🏆 Plus d'heures:**")
            top_hours = sorted(employee_productivity, key=lambda x: x['total_hours'], reverse=True)[:5]
            for i, emp in enumerate(top_hours, 1):
                st.markdown(f"{i}. {emp['name']} - {emp['total_hours']:.1f}h")
        
        with col_top2:
            st.markdown("**💰 Plus de revenus:**")
            top_revenue = sorted(employee_productivity, key=lambda x: x['total_revenue'], reverse=True)[:5]
            for i, emp in enumerate(top_revenue, 1):
                st.markdown(f"{i}. {emp['name']} - {emp['total_revenue']:.0f}$")
        
        with col_top3:
            st.markdown("**🔧 Plus de BTs:**")
            top_bt = sorted(employee_productivity, key=lambda x: x['bt_count'], reverse=True)[:5]
            for i, emp in enumerate(top_bt, 1):
                st.markdown(f"{i}. {emp['name']} - {emp['bt_count']} BTs")
        
        # Graphique de comparaison
        if len(employee_productivity) > 1:
            fig_comparison = px.scatter(
                x=[emp['total_hours'] for emp in employee_productivity],
                y=[emp['total_revenue'] for emp in employee_productivity],
                hover_name=[emp['name'] for emp in employee_productivity],
                title="💰 Revenus vs Heures par Employé",
                labels={'x': 'Heures Totales', 'y': 'Revenus Totaux ($)'}
            )
            st.plotly_chart(fig_comparison, use_container_width=True)
        
        # Tableau détaillé
        df_productivity = pd.DataFrame([
            {
                'Employé': emp['name'],
                'Département': emp['departement'],
                'Heures Totales': f"{emp['total_hours']:.1f}h",
                'Heures BT': f"{emp['bt_hours']:.1f}h",
                'Revenus Totaux': f"{emp['total_revenue']:.0f}$",
                'Revenus BT': f"{emp['bt_revenue']:.0f}$",
                'BTs Travaillés': emp['bt_count'],
                'Efficacité': f"{emp['efficiency']:.1f}%"
            }
            for emp in employee_productivity
        ])
        
        st.dataframe(df_productivity, use_container_width=True)


def render_bt_productivity_analysis(tt_unified: TimeTrackerUnified):
    """Analyse de productivité par BT"""
    
    st.markdown("#### 🔧 Productivité par Bon de Travail")
    
    bt_performance = tt_unified._get_bt_performance_data()
    
    if bt_performance:
        # Métriques BT
        col_bt1, col_bt2, col_bt3, col_bt4 = st.columns(4)
        
        total_bts = len(bt_performance)
        completed_bts = len([bt for bt in bt_performance if bt['statut'] == 'TERMINÉ'])
        avg_efficiency = sum(bt.get('efficiency', 0) for bt in bt_performance) / len(bt_performance)
        total_bt_revenue = sum(bt.get('total_cost', 0) for bt in bt_performance)
        
        with col_bt1:
            st.metric("🔧 Total BTs", total_bts)
        with col_bt2:
            st.metric("✅ BTs Terminés", completed_bts)
        with col_bt3:
            st.metric("📊 Efficacité Moy.", f"{avg_efficiency:.1f}%")
        with col_bt4:
            st.metric("💰 Revenus BTs", f"{total_bt_revenue:.0f}$")
        
        # Graphique d'efficacité
        efficiency_data = [bt for bt in bt_performance if bt.get('efficiency', 0) > 0]
        if efficiency_data:
            fig_efficiency = px.bar(
                x=[bt['numero_document'] for bt in efficiency_data],
                y=[bt['efficiency'] for bt in efficiency_data],
                title="📊 Efficacité par Bon de Travail (% temps réel vs estimé)",
                labels={'x': 'Bons de Travail', 'y': 'Efficacité (%)'}
            )
            fig_efficiency.add_hline(y=100, line_dash="dash", line_color="red")
            st.plotly_chart(fig_efficiency, use_container_width=True)
        
        # Tableau BT
        df_bt_performance = pd.DataFrame([
            {
                'BT': bt['numero_document'],
                'Statut': bt['statut'],
                'Temps Estimé': f"{bt['temps_estime']:.1f}h",
                'Temps Réel': f"{bt['total_hours']:.1f}h",
                'Efficacité': f"{bt.get('efficiency', 0):.1f}%",
                'Revenus': f"{bt.get('total_cost', 0):.0f}$",
                'Employés': bt.get('nb_employes', 0),
                'Progression': f"{bt.get('progression', 0):.0f}%"
            }
            for bt in bt_performance
        ])
        
        st.dataframe(df_bt_performance, use_container_width=True)


def show_admin_unified_interface(tt_unified: TimeTrackerUnified):
    """Interface d'administration unifiée"""
    
    st.markdown("### ⚙️ Administration TimeTracker Pro")
    
    # Vue d'ensemble
    stats = tt_unified.get_timetracker_statistics_unified()
    employees = tt_unified.get_all_employees()
    projects = tt_unified.get_active_projects()
    
    # Métriques d'administration
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("👥 Employés", len(employees))
    with col2:
        st.metric("📋 Projets", len(projects))
    with col3:
        st.metric("🟢 Pointages Actifs", stats.get('active_entries', 0))
    with col4:
        st.metric("🔧 Pointages BT Actifs", stats.get('active_entries_bt', 0))
    with col5:
        st.metric("💰 Revenus Jour", f"{stats.get('total_revenue_today', 0):.0f}$")
    
    # Onglets d'administration
    admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
        "👥 Employés & BTs", "🔧 Gestion BTs", "📊 Monitoring", "🛠️ Outils"
    ])
    
    with admin_tab1:
        render_admin_employees_bt_tab(tt_unified, employees)
    
    with admin_tab2:
        render_admin_bt_management_tab(tt_unified)
    
    with admin_tab3:
        render_admin_monitoring_tab(tt_unified)
    
    with admin_tab4:
        render_admin_tools_tab(tt_unified)


def render_admin_employees_bt_tab(tt_unified: TimeTrackerUnified, employees: List[Dict]):
    """Onglet administration employés avec BTs"""
    
    st.markdown("#### 👥 Gestion Employés & Bons de Travail")
    
    if employees:
        df_employees = []
        for emp in employees:
            current_entry = tt_unified.get_employee_current_entry(emp['id'])
            bts_assignes = tt_unified.get_bts_assignes_employe(emp['id'])
            
            status = "🟢 Pointé"
            current_work = ""
            session_duration = ""
            
            if current_entry:
                session_duration = f"{current_entry['elapsed_hours']:.1f}h"
                if current_entry.get('is_bt_work'):
                    current_work = f"🔧 {current_entry.get('bt_context', 'BT')}"
                else:
                    current_work = f"📋 {current_entry['project_name'][:20]}..."
            else:
                status = "🟡 Libre"
            
            df_employees.append({
                '👤 Nom': emp['name'],
                '💼 Poste': emp.get('poste', 'N/A'),
                '🏢 Département': emp.get('departement', 'N/A'),
                '🔧 BTs Assignés': len(bts_assignes),
                '🚦 Statut': status,
                '⏱️ Durée Session': session_duration or 'N/A',
                '🔧 Travail Actuel': current_work or 'Aucun'
            })
        
        st.dataframe(pd.DataFrame(df_employees), use_container_width=True)


def render_admin_bt_management_tab(tt_unified: TimeTrackerUnified):
    """Onglet gestion administrative des BTs"""
    
    st.markdown("#### 🔧 Gestion Administrative des BTs")
    
    # Actions administratives
    col_action1, col_action2, col_action3 = st.columns(3)
    
    with col_action1:
        if st.button("📊 Recalculer Progressions BT", use_container_width=True):
            count = tt_unified._recalculate_all_bt_progress()
            st.success(f"✅ {count} progressions BT recalculées")
    
    with col_action2:
        if st.button("🔄 Synchroniser BT ↔ TimeTracker", use_container_width=True):
            tt_unified._sync_bt_timetracker_data()
            st.success("✅ Synchronisation terminée")
    
    with col_action3:
        if st.button("🧹 Nettoyer Sessions BT Vides", use_container_width=True):
            cleaned = tt_unified._cleanup_empty_bt_sessions()
            st.success(f"✅ {cleaned} session(s) nettoyée(s)")
    
    # Statistiques BT globales
    st.markdown("#### 📊 Statistiques BT Globales")
    
    bt_global_stats = tt_unified.get_statistiques_bt_timetracker()
    
    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
    with col_stats1:
        st.metric("📊 Pointages BT", bt_global_stats.get('nb_pointages', 0))
    with col_stats2:
        st.metric("⏱️ Heures BT", f"{bt_global_stats.get('total_heures', 0):.1f}h")
    with col_stats3:
        st.metric("💰 Revenus BT", f"{bt_global_stats.get('total_cout', 0):.0f}$")
    with col_stats4:
        st.metric("👥 Employés BT", bt_global_stats.get('nb_employes_distinct', 0))


def show_system_unified_interface():
    """Interface système unifiée"""
    
    st.markdown("### ℹ️ Système TimeTracker Pro Unifié")
    
    st.success("""
    🎉 **TimeTracker Pro - Architecture Unifiée Active !**
    
    ✅ Intégration complète Bons de Travail ↔ TimeTracker réussie
    ✅ Interface unique pour pointage, gestion BTs, analytics et productivité
    ✅ Base SQLite unifiée avec synchronisation temps réel
    ✅ Workflow seamless : Création BT → Assignation → Pointage → Suivi → Finalisation
    """)
    
    # Informations sur l'intégration
    if 'erp_db' in st.session_state:
        db_info = st.session_state.erp_db.get_schema_info()
        
        col_sys1, col_sys2, col_sys3, col_sys4 = st.columns(4)
        with col_sys1:
            st.metric("📊 Tables", len(db_info['tables']))
        with col_sys2:
            bt_records = db_info['tables'].get('formulaires', 0)
            st.metric("🔧 Formulaires BT", bt_records)
        with col_sys3:
            tt_records = db_info['tables'].get('time_entries', 0)
            st.metric("⏱️ Entrées TimeTracker", tt_records)
        with col_sys4:
            bt_assignations = db_info['tables'].get('bt_assignations', 0)
            st.metric("👥 Assignations BT", bt_assignations)
        
        # Fonctionnalités intégrées
        st.markdown("#### 🚀 Fonctionnalités Intégrées")
        
        fonctionnalites = [
            "✅ Pointage direct sur Bons de Travail depuis TimeTracker",
            "✅ Dashboard unifié avec métriques BT + TimeTracker",
            "✅ Création BT avec auto-assignation et préparation TimeTracker",
            "✅ Suivi temps réel de l'avancement BT via heures pointées",
            "✅ Analytics fusionnés projets généraux + BTs",
            "✅ Workflow complet BT intégré dans TimeTracker",
            "✅ Notifications employés pour nouveaux BTs assignés",
            "✅ Progression automatique basée sur TimeTracker",
            "✅ Interface administrative unifiée",
            "✅ Export et reporting combinés"
        ]
        
        for fonctionnalite in fonctionnalites:
            st.markdown(fonctionnalite)
        
        # Bénéfices utilisateur
        st.markdown("#### 🎯 Bénéfices Utilisateur")
        
        benefices = [
            "🚀 **Interface unique** - Plus de navigation entre modules",
            "⚡ **Workflow fluide** - Création BT → Pointage → Suivi → Finalisation seamless",
            "📊 **Données enrichies** - Analytics BT + TimeTracker fusionnés",
            "🔧 **Productivité** - Moins de clics, plus d'efficacité",
            "👁️ **Vision globale** - Tout le travail dans une seule vue",
            "📈 **Meilleur suivi** - Progression temps réel basée sur pointages",
            "💰 **ROI optimisé** - Données précises pour facturation et coûts"
        ]
        
        for benefice in benefices:
            st.markdown(benefice)


# ========================================================================
# MÉTHODES UTILITAIRES POUR LES INTERFACES
# ========================================================================

def _get_bts_with_timetracker_data(self) -> List[Dict]:
    """Récupère les BTs avec leurs données TimeTracker intégrées"""
    try:
        query = """
            SELECT 
                f.id, f.numero_document, f.statut, f.priorite, f.date_creation, f.date_echeance,
                p.nom_projet, e.prenom || ' ' || e.nom as employee_nom,
                COUNT(DISTINCT bta.employe_id) as nb_employes_assignes,
                COALESCE(SUM(te.total_hours), 0) as timetracker_hours,
                COALESCE(SUM(te.total_cost), 0) as timetracker_revenue,
                COALESCE(AVG(ba.pourcentage_realise), 0) as progression
            FROM formulaires f
            LEFT JOIN projects p ON f.project_id = p.id
            LEFT JOIN employees e ON f.employee_id = e.id
            LEFT JOIN bt_assignations bta ON f.id = bta.bt_id AND bta.statut = 'ASSIGNÉ'
            LEFT JOIN time_entries te ON f.id = te.formulaire_bt_id AND te.total_cost IS NOT NULL
            LEFT JOIN bt_avancement ba ON f.id = ba.bt_id
            WHERE f.type_formulaire = 'BON_TRAVAIL'
            GROUP BY f.id
            ORDER BY f.date_creation DESC
        """
        rows = self.db.execute_query(query)
        return [dict(row) for row in rows]
        
    except Exception as e:
        logger.error(f"Erreur récupération BTs avec TimeTracker: {e}")
        return []

TimeTrackerUnified._get_bts_with_timetracker_data = _get_bts_with_timetracker_data


def _get_bt_performance_data(self) -> List[Dict]:
    """Récupère les données de performance des BTs"""
    try:
        query = """
            SELECT 
                f.id, f.numero_document, f.statut, f.priorite, f.metadonnees_json,
                COALESCE(SUM(te.total_hours), 0) as total_hours,
                COALESCE(SUM(te.total_cost), 0) as total_cost,
                COUNT(DISTINCT te.employee_id) as nb_employes,
                COALESCE(AVG(ba.pourcentage_realise), 0) as progression
            FROM formulaires f
            LEFT JOIN time_entries te ON f.id = te.formulaire_bt_id AND te.total_cost IS NOT NULL
            LEFT JOIN bt_avancement ba ON f.id = ba.bt_id
            WHERE f.type_formulaire = 'BON_TRAVAIL'
            GROUP BY f.id
        """
        rows = self.db.execute_query(query)
        
        performance_data = []
        for row in rows:
            bt = dict(row)
            
            # Récupérer le temps estimé
            temps_estime = 0
            try:
                metadonnees = json.loads(bt.get('metadonnees_json', '{}'))
                temps_estime = metadonnees.get('temps_estime_total', 0)
            except:
                pass
            
            bt['temps_estime'] = temps_estime
            
            # Calculer l'efficacité
            if temps_estime > 0 and bt['total_hours'] > 0:
                bt['efficiency'] = (temps_estime / bt['total_hours']) * 100
            else:
                bt['efficiency'] = 0
            
            performance_data.append(bt)
        
        return performance_data
        
    except Exception as e:
        logger.error(f"Erreur données performance BT: {e}")
        return []

TimeTrackerUnified._get_bt_performance_data = _get_bt_performance_data


def _generer_rapport_productivite_bt(self, periode_jours: int) -> Dict:
    """Génère un rapport de productivité BT avec TimeTracker"""
    try:
        date_debut = datetime.now() - timedelta(days=periode_jours)
        
        # Rapport employés BT
        query = """
            SELECT 
                e.prenom || ' ' || e.nom as employe_nom,
                e.poste, e.departement,
                COUNT(DISTINCT f.id) as nb_bt_termines,
                COALESCE(SUM(te.total_hours), 0) as total_heures,
                COALESCE(SUM(te.total_cost), 0) as total_revenus,
                COALESCE(AVG(te.total_hours), 0) as moyenne_heures_bt
            FROM employees e
            JOIN time_entries te ON e.id = te.employee_id
            JOIN formulaires f ON te.formulaire_bt_id = f.id
            WHERE f.type_formulaire = 'BON_TRAVAIL'
            AND f.statut = 'TERMINÉ'
            AND te.punch_in >= ?
            AND te.total_cost IS NOT NULL
            GROUP BY e.id
            ORDER BY nb_bt_termines DESC
        """
        
        rows = self.db.execute_query(query, (date_debut.isoformat(),))
        employes = [dict(row) for row in rows]
        
        # Calculs globaux
        total_bt_termines = sum(emp['nb_bt_termines'] for emp in employes)
        duree_moyenne_globale = sum(emp['moyenne_heures_bt'] for emp in employes) / len(employes) if employes else 0
        revenus_totaux = sum(emp['total_revenus'] for emp in employes)
        
        rapport = {
            'periode': f"{periode_jours} derniers jours",
            'date_generation': datetime.now().isoformat(),
            'employes': employes,
            'total_bt_termines': total_bt_termines,
            'duree_moyenne_globale': duree_moyenne_globale,
            'revenus_totaux': revenus_totaux,
            'recommandations': self._generer_recommandations_bt(employes)
        }
        
        return rapport
        
    except Exception as e:
        logger.error(f"Erreur rapport productivité BT: {e}")
        return {}

TimeTrackerUnified._generer_rapport_productivite_bt = _generer_rapport_productivite_bt


def _generer_recommandations_bt(self, employes_data: List[Dict]) -> List[str]:
    """Génère des recommandations basées sur les données BT"""
    recommandations = []
    
    if not employes_data:
        return ["Aucune donnée suffisante pour générer des recommandations"]
    
    # Analyse de la répartition des BTs
    nb_bt_values = [emp['nb_bt_termines'] for emp in employes_data]
    if len(nb_bt_values) > 1:
        max_bt = max(nb_bt_values)
        min_bt = min(nb_bt_values)
        
        if max_bt - min_bt > 3:
            recommandations.append("📊 Équilibrer la répartition des Bons de Travail entre employés")
    
    # Analyse des heures moyennes
    heures_moyennes = [emp['moyenne_heures_bt'] for emp in employes_data]
    if heures_moyennes:
        moy_globale = sum(heures_moyennes) / len(heures_moyennes)
        heures_max = max(heures_moyennes)
        
        if heures_max > moy_globale * 1.5:
            recommandations.append("⏱️ Identifier les BTs qui prennent plus de temps que la moyenne")
    
    # Recommandations générales
    if len(employes_data) >= 5:
        recommandations.append("👥 Excellente répartition de l'équipe sur les BTs")
    elif len(employes_data) < 3:
        recommandations.append("👥 Considérer l'assignation de plus d'employés aux BTs")
    
    recommandations.append("🔧 Utiliser TimeTracker pour optimiser l'estimation des futurs BTs")
    recommandations.append("📈 Analyser les données de progression pour améliorer la planification")
    
    return recommandations

TimeTrackerUnified._generer_recommandations_bt = _generer_recommandations_bt


# Point d'entrée principal pour l'application
if __name__ == "__main__":
    st.error("❌ Ce module doit être importé par app.py")
    st.info("Utilisez show_timetracker_unified_interface() depuis votre application principale.")