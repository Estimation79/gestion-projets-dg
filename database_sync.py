# --- START OF FILE database_sync.py ---

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import streamlit as st
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseSync:
    """
    Gestionnaire de synchronisation entre l'ERP Production DG Inc. (JSON) 
    et TimeTracker Pro D&G (SQLite)
    
    Fonctionnalités:
    - Migration projets ERP JSON → SQLite TimeTracker
    - Sync employés ERP ↔ TimeTracker
    - Mapping 34 postes TimeTracker → 61 postes ERP
    - Bridge temps réel entre systèmes
    """
    
    def __init__(self, db_path: str = "timetracker.db"):
        self.db_path = db_path
        self.connection = None
        
        # Mapping des départements TimeTracker vers ERP
        self.mapping_departements = {
            'Soudage': 'PRODUCTION',
            'Découpe et Perçage': 'PRODUCTION', 
            'Formage et Assemblage': 'PRODUCTION',
            'Finition': 'PRODUCTION',
            'Préparation et Programmation': 'USINAGE',
            'Manutention et Cisaillage': 'LOGISTIQUE',
            'Contrôle Qualité': 'QUALITE',
            'Expédition': 'LOGISTIQUE'
        }
        
        # Initialiser la base TimeTracker
        self.init_timetracker_database()
    
    def __enter__(self):
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()
    
    def init_timetracker_database(self):
        """Initialise la base de données TimeTracker avec les tables nécessaires"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table des employés
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    password_hash TEXT,
                    role TEXT DEFAULT 'employee',
                    is_active INTEGER DEFAULT 1,
                    email TEXT,
                    poste TEXT,
                    salaire REAL,
                    date_embauche TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    erp_sync_id INTEGER,
                    last_sync TIMESTAMP
                )
            ''')
            
            # Table des projets
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_code TEXT UNIQUE NOT NULL,
                    project_name TEXT NOT NULL,
                    client_name TEXT,
                    requires_task_selection INTEGER DEFAULT 1,
                    erp_project_id INTEGER,
                    status TEXT DEFAULT 'À FAIRE',
                    start_date TEXT,
                    end_date TEXT,
                    estimated_price REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_sync TIMESTAMP
                )
            ''')
            
            # Table des tâches/postes de travail
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    task_code TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    task_category TEXT,
                    hourly_rate REAL DEFAULT 95.0,
                    estimated_hours REAL DEFAULT 0,
                    erp_poste_id TEXT,
                    sequence_number INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            ''')
            
            # Table des entrées de temps
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS time_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER,
                    project_id INTEGER,
                    task_id INTEGER,
                    punch_in TIMESTAMP,
                    punch_out TIMESTAMP,
                    notes TEXT,
                    total_hours REAL,
                    hourly_rate REAL,
                    total_cost REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees (id),
                    FOREIGN KEY (project_id) REFERENCES projects (id),
                    FOREIGN KEY (task_id) REFERENCES project_tasks (id)
                )
            ''')
            
            # Table des assignations employé-tâche
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employee_task_assignments (
                    employee_id INTEGER,
                    project_id INTEGER,
                    task_id INTEGER,
                    skill_level TEXT DEFAULT 'INTERMÉDIAIRE',
                    hourly_rate_override REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (employee_id, project_id, task_id),
                    FOREIGN KEY (employee_id) REFERENCES employees (id),
                    FOREIGN KEY (project_id) REFERENCES projects (id),
                    FOREIGN KEY (task_id) REFERENCES project_tasks (id)
                )
            ''')
            
            # Table de mapping des postes ERP ↔ TimeTracker
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS poste_mapping (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    erp_poste_code TEXT NOT NULL,
                    erp_poste_nom TEXT,
                    timetracker_task_code TEXT NOT NULL,
                    timetracker_task_name TEXT,
                    hourly_rate REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Index pour performances
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_employees_code ON employees(employee_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_code ON projects(project_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_entries_employee ON time_entries(employee_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_entries_project ON time_entries(project_id)')
            
            conn.commit()
            logger.info("Base de données TimeTracker initialisée avec succès")
    
    def sync_employees_erp_to_timetracker(self, gestionnaire_employes) -> Tuple[int, int]:
        """
        Synchronise les employés de l'ERP vers TimeTracker
        
        Returns:
            Tuple[int, int]: (nombre_ajoutés, nombre_mis_à_jour)
        """
        added_count = 0
        updated_count = 0
        
        with self as sync_db:
            cursor = sync_db.connection.cursor()
            
            for employe_erp in gestionnaire_employes.employes:
                employee_code = f"ERP-{employe_erp['id']}"
                name = f"{employe_erp.get('prenom', '')} {employe_erp.get('nom', '')}".strip()
                
                # Vérifier si l'employé existe déjà
                cursor.execute(
                    'SELECT id FROM employees WHERE employee_code = ? OR erp_sync_id = ?',
                    (employee_code, employe_erp['id'])
                )
                existing = cursor.fetchone()
                
                employee_data = {
                    'employee_code': employee_code,
                    'name': name,
                    'role': 'admin' if employe_erp.get('poste', '').lower() in ['manager', 'directeur', 'chef'] else 'employee',
                    'email': employe_erp.get('email', ''),
                    'poste': employe_erp.get('poste', ''),
                    'salaire': employe_erp.get('salaire', 0),
                    'date_embauche': employe_erp.get('date_embauche', ''),
                    'erp_sync_id': employe_erp['id'],
                    'last_sync': datetime.now().isoformat()
                }
                
                if existing:
                    # Mise à jour
                    cursor.execute('''
                        UPDATE employees 
                        SET name = ?, role = ?, email = ?, poste = ?, 
                            salaire = ?, date_embauche = ?, last_sync = ?
                        WHERE id = ?
                    ''', (
                        employee_data['name'], employee_data['role'],
                        employee_data['email'], employee_data['poste'],
                        employee_data['salaire'], employee_data['date_embauche'],
                        employee_data['last_sync'], existing['id']
                    ))
                    updated_count += 1
                    logger.info(f"Employé mis à jour: {name}")
                else:
                    # Ajout
                    cursor.execute('''
                        INSERT INTO employees 
                        (employee_code, name, role, email, poste, salaire, 
                         date_embauche, erp_sync_id, last_sync)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        employee_data['employee_code'], employee_data['name'],
                        employee_data['role'], employee_data['email'],
                        employee_data['poste'], employee_data['salaire'],
                        employee_data['date_embauche'], employee_data['erp_sync_id'],
                        employee_data['last_sync']
                    ))
                    added_count += 1
                    logger.info(f"Employé ajouté: {name}")
            
            sync_db.connection.commit()
        
        return added_count, updated_count
    
    def sync_projects_erp_to_timetracker(self, gestionnaire_projets) -> Tuple[int, int]:
        """
        Synchronise les projets de l'ERP vers TimeTracker
        
        Returns:
            Tuple[int, int]: (nombre_ajoutés, nombre_mis_à_jour)
        """
        added_count = 0
        updated_count = 0
        
        with self as sync_db:
            cursor = sync_db.connection.cursor()
            
            for projet_erp in gestionnaire_projets.projets:
                project_code = f"ERP-{projet_erp['id']}"
                
                # Vérifier si le projet existe déjà
                cursor.execute(
                    'SELECT id FROM projects WHERE project_code = ? OR erp_project_id = ?',
                    (project_code, projet_erp['id'])
                )
                existing = cursor.fetchone()
                
                project_data = {
                    'project_code': project_code,
                    'project_name': projet_erp.get('nom_projet', ''),
                    'client_name': projet_erp.get('client_nom_cache', projet_erp.get('client', '')),
                    'erp_project_id': projet_erp['id'],
                    'status': projet_erp.get('statut', 'À FAIRE'),
                    'start_date': projet_erp.get('date_soumis', ''),
                    'end_date': projet_erp.get('date_prevu', ''),
                    'estimated_price': self._parse_price(projet_erp.get('prix_estime', 0)),
                    'last_sync': datetime.now().isoformat()
                }
                
                if existing:
                    # Mise à jour
                    cursor.execute('''
                        UPDATE projects 
                        SET project_name = ?, client_name = ?, status = ?,
                            start_date = ?, end_date = ?, estimated_price = ?, last_sync = ?
                        WHERE id = ?
                    ''', (
                        project_data['project_name'], project_data['client_name'],
                        project_data['status'], project_data['start_date'],
                        project_data['end_date'], project_data['estimated_price'],
                        project_data['last_sync'], existing['id']
                    ))
                    project_id = existing['id']
                    updated_count += 1
                    logger.info(f"Projet mis à jour: {project_data['project_name']}")
                else:
                    # Ajout
                    cursor.execute('''
                        INSERT INTO projects 
                        (project_code, project_name, client_name, erp_project_id,
                         status, start_date, end_date, estimated_price, last_sync)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        project_data['project_code'], project_data['project_name'],
                        project_data['client_name'], project_data['erp_project_id'],
                        project_data['status'], project_data['start_date'],
                        project_data['end_date'], project_data['estimated_price'],
                        project_data['last_sync']
                    ))
                    project_id = cursor.lastrowid
                    added_count += 1
                    logger.info(f"Projet ajouté: {project_data['project_name']}")
                
                # Synchroniser les opérations du projet comme tâches TimeTracker
                self._sync_project_operations(cursor, projet_erp, project_id)
            
            sync_db.connection.commit()
        
        return added_count, updated_count
    
    def _sync_project_operations(self, cursor, projet_erp, project_id):
        """Synchronise les opérations d'un projet ERP vers les tâches TimeTracker"""
        operations = projet_erp.get('operations', [])
        
        # Supprimer les anciennes tâches du projet
        cursor.execute('DELETE FROM project_tasks WHERE project_id = ?', (project_id,))
        
        for operation in operations:
            poste_travail = operation.get('poste_travail', 'Non assigné')
            
            # Déterminer la catégorie et le taux horaire basé sur le poste
            category, hourly_rate = self._categorize_poste_travail(poste_travail)
            
            cursor.execute('''
                INSERT INTO project_tasks 
                (project_id, task_code, task_name, task_category, hourly_rate,
                 estimated_hours, erp_poste_id, sequence_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id,
                operation.get('sequence', f"OP-{operation.get('id', '')}"),
                f"{poste_travail} - {operation.get('description', '')}",
                category,
                hourly_rate,
                operation.get('temps_estime', 0),
                operation.get('id', ''),
                int(operation.get('sequence', 0)) if operation.get('sequence', '').isdigit() else 0
            ))
    
    def _categorize_poste_travail(self, poste_travail: str) -> Tuple[str, float]:
        """
        Catégorise un poste de travail ERP et retourne la catégorie TimeTracker
        et le taux horaire approprié
        """
        poste_lower = poste_travail.lower()
        
        # Mapping basé sur les 34 postes TimeTracker réels
        if any(mot in poste_lower for mot in ['soudage', 'soudure', 'robot', 'tig', 'mig', 'gmaw']):
            return 'Soudage', 125.0
        elif any(mot in poste_lower for mot in ['plasma', 'oxycoupage', 'poinçon', 'découpe', 'laser']):
            return 'Découpe et Perçage', 115.0
        elif any(mot in poste_lower for mot in ['plieuse', 'roulage', 'assemblage', 'formage']):
            return 'Formage et Assemblage', 110.0
        elif any(mot in poste_lower for mot in ['ébavurage', 'meulage', 'polissage', 'finition']):
            return 'Finition', 95.0
        elif any(mot in poste_lower for mot in ['programmation', 'progr', 'dessin', 'cnc']):
            return 'Préparation et Programmation', 105.0
        elif any(mot in poste_lower for mot in ['shear', 'manutention', 'cisaillage']):
            return 'Manutention et Cisaillage', 95.0
        elif any(mot in poste_lower for mot in ['contrôle', 'qualité', 'inspection']):
            return 'Contrôle Qualité', 85.0
        elif any(mot in poste_lower for mot in ['emballage', 'expédition', 'transport']):
            return 'Expédition', 90.0
        else:
            return 'Autre', 95.0
    
    def create_poste_mapping(self, gestionnaire_postes) -> int:
        """
        Crée le mapping entre les postes ERP et les tâches TimeTracker
        
        Returns:
            int: Nombre de mappings créés
        """
        mapping_count = 0
        
        with self as sync_db:
            cursor = sync_db.connection.cursor()
            
            # Vider la table de mapping existante
            cursor.execute('DELETE FROM poste_mapping')
            
            # Obtenir tous les postes de l'ERP
            for poste_erp in gestionnaire_postes.postes:
                # Déterminer le poste TimeTracker équivalent
                timetracker_task = self._map_erp_to_timetracker_task(poste_erp)
                
                if timetracker_task:
                    cursor.execute('''
                        INSERT INTO poste_mapping 
                        (erp_poste_code, erp_poste_nom, timetracker_task_code, 
                         timetracker_task_name, hourly_rate)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        poste_erp.get('code', ''),
                        poste_erp.get('nom', ''),
                        timetracker_task['code'],
                        timetracker_task['name'],
                        timetracker_task['rate']
                    ))
                    mapping_count += 1
            
            sync_db.connection.commit()
        
        logger.info(f"Créé {mapping_count} mappings de postes")
        return mapping_count
    
    def _map_erp_to_timetracker_task(self, poste_erp: Dict) -> Optional[Dict]:
        """Mappe un poste ERP vers une tâche TimeTracker équivalente"""
        nom_poste = poste_erp.get('nom', '').lower()
        
        # Mapping des 61 postes ERP vers les 34 postes TimeTracker
        mapping_table = {
            # Soudage
            'robot': {'code': 'ROBOT_ABB', 'name': 'Robot ABB GMAW', 'rate': 140.0},
            'soudage': {'code': 'SOUDURE_MIG', 'name': 'Soudage MIG/MAG', 'rate': 125.0},
            'soudure': {'code': 'SOUDURE_TIG', 'name': 'Soudage TIG', 'rate': 135.0},
            
            # Découpe
            'laser': {'code': 'LASER_CNC', 'name': 'Découpe Laser CNC', 'rate': 135.0},
            'plasma': {'code': 'PLASMA_CNC', 'name': 'Découpe Plasma CNC', 'rate': 125.0},
            'poinçon': {'code': 'POINCONNAGE', 'name': 'Poinçonnage CNC', 'rate': 120.0},
            
            # Usinage
            'centre': {'code': 'CENTRE_USINAGE', 'name': 'Centre d\'usinage CNC', 'rate': 130.0},
            'tour': {'code': 'TOUR_CNC', 'name': 'Tour CNC', 'rate': 125.0},
            'fraisage': {'code': 'FRAISAGE_CNC', 'name': 'Fraisage CNC', 'rate': 125.0},
            
            # Formage
            'pliage': {'code': 'PLIEUSE_CNC', 'name': 'Plieuse CNC', 'rate': 115.0},
            'plieuse': {'code': 'PLIEUSE_CNC', 'name': 'Plieuse CNC', 'rate': 115.0},
            'roulage': {'code': 'ROULAGE', 'name': 'Roulage tôle', 'rate': 110.0},
            
            # Assemblage
            'assemblage': {'code': 'ASSEMBLAGE', 'name': 'Assemblage général', 'rate': 105.0},
            
            # Programmation
            'programmation': {'code': 'PROGR_CNC', 'name': 'Programmation CNC', 'rate': 105.0},
            'dessin': {'code': 'DESSIN_CAO', 'name': 'Dessin CAO', 'rate': 100.0},
            
            # Contrôle
            'contrôle': {'code': 'XINSP_PARTIE', 'name': 'Inspection pièce', 'rate': 85.0},
            'métrologie': {'code': 'X_INSPEC_FIN', 'name': 'Inspection finale', 'rate': 85.0},
            
            # Finition
            'ébavurage': {'code': 'ÉBAVURAGE', 'name': 'Ébavurage', 'rate': 95.0},
            'meulage': {'code': 'MEULAGE', 'name': 'Meulage', 'rate': 95.0},
            'polissage': {'code': 'POLISSAGE', 'name': 'Polissage', 'rate': 95.0},
            
            # Logistique
            'manutention': {'code': 'MANUTENTION', 'name': 'Manutention', 'rate': 85.0},
            'emballage': {'code': 'EMBALLAGE', 'name': 'Emballage', 'rate': 90.0},
            'expédition': {'code': 'EXPEDITION', 'name': 'Expédition', 'rate': 90.0}
        }
        
        for keyword, task_info in mapping_table.items():
            if keyword in nom_poste:
                return task_info
        
        # Mapping par défaut
        return {'code': 'GENERAL', 'name': 'Opération générale', 'rate': 95.0}
    
    def _parse_price(self, prix_str) -> float:
        """Parse une chaîne de prix vers un float"""
        try:
            if isinstance(prix_str, (int, float)):
                return float(prix_str)
            
            # Nettoyer la chaîne
            prix_clean = str(prix_str).replace(' ', '').replace('€', '').replace('$', '').replace(',', '')
            return float(prix_clean) if prix_clean else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def get_sync_statistics(self) -> Dict:
        """Retourne les statistiques de synchronisation"""
        stats = {
            'employees': 0,
            'projects': 0,
            'tasks': 0,
            'time_entries': 0,
            'poste_mappings': 0,
            'last_sync': None,
            'total_revenue': 0.0
        }
        
        with self as sync_db:
            cursor = sync_db.connection.cursor()
            
            # Compter les enregistrements
            cursor.execute('SELECT COUNT(*) FROM employees')
            stats['employees'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM projects')
            stats['projects'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM project_tasks')
            stats['tasks'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM time_entries')
            stats['time_entries'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM poste_mapping')
            stats['poste_mappings'] = cursor.fetchone()[0]
            
            # Dernière synchronisation
            cursor.execute('''
                SELECT MAX(last_sync) FROM (
                    SELECT last_sync FROM employees
                    UNION ALL
                    SELECT last_sync FROM projects
                ) 
            ''')
            last_sync = cursor.fetchone()[0]
            if last_sync:
                stats['last_sync'] = last_sync
            
            # Revenus total des entrées de temps
            cursor.execute('SELECT SUM(total_cost) FROM time_entries WHERE total_cost IS NOT NULL')
            revenue = cursor.fetchone()[0]
            stats['total_revenue'] = revenue if revenue else 0.0
        
        return stats
    
    def full_sync(self, gestionnaire_projets, gestionnaire_employes, gestionnaire_postes) -> Dict:
        """
        Effectue une synchronisation complète ERP → TimeTracker
        
        Returns:
            Dict: Rapport de synchronisation
        """
        sync_report = {
            'start_time': datetime.now().isoformat(),
            'employees': {'added': 0, 'updated': 0},
            'projects': {'added': 0, 'updated': 0},
            'poste_mappings': 0,
            'success': False,
            'errors': []
        }
        
        try:
            logger.info("Début de la synchronisation complète ERP → TimeTracker")
            
            # 1. Synchroniser les employés
            emp_added, emp_updated = self.sync_employees_erp_to_timetracker(gestionnaire_employes)
            sync_report['employees']['added'] = emp_added
            sync_report['employees']['updated'] = emp_updated
            
            # 2. Synchroniser les projets
            proj_added, proj_updated = self.sync_projects_erp_to_timetracker(gestionnaire_projets)
            sync_report['projects']['added'] = proj_added
            sync_report['projects']['updated'] = proj_updated
            
            # 3. Créer les mappings de postes
            mappings_created = self.create_poste_mapping(gestionnaire_postes)
            sync_report['poste_mappings'] = mappings_created
            
            sync_report['success'] = True
            sync_report['end_time'] = datetime.now().isoformat()
            
            logger.info(f"Synchronisation terminée avec succès: {sync_report}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation: {str(e)}")
            sync_report['errors'].append(str(e))
            sync_report['success'] = False
            sync_report['end_time'] = datetime.now().isoformat()
        
        return sync_report
    
    def backup_timetracker_data(self, backup_path: str = None) -> str:
        """
        Crée une sauvegarde de la base TimeTracker
        
        Returns:
            str: Chemin du fichier de sauvegarde
        """
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"timetracker_backup_{timestamp}.db"
        
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Sauvegarde créée: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde: {str(e)}")
            raise
    
    def export_timetracker_data_to_json(self, export_path: str = None) -> str:
        """
        Exporte toutes les données TimeTracker vers JSON
        
        Returns:
            str: Chemin du fichier JSON exporté
        """
        if not export_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f"timetracker_export_{timestamp}.json"
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'employees': [],
            'projects': [],
            'tasks': [],
            'time_entries': [],
            'poste_mappings': []
        }
        
        with self as sync_db:
            cursor = sync_db.connection.cursor()
            
            # Exporter les employés
            cursor.execute('SELECT * FROM employees')
            for row in cursor.fetchall():
                export_data['employees'].append(dict(row))
            
            # Exporter les projets
            cursor.execute('SELECT * FROM projects')
            for row in cursor.fetchall():
                export_data['projects'].append(dict(row))
            
            # Exporter les tâches
            cursor.execute('SELECT * FROM project_tasks')
            for row in cursor.fetchall():
                export_data['tasks'].append(dict(row))
            
            # Exporter les entrées de temps
            cursor.execute('SELECT * FROM time_entries')
            for row in cursor.fetchall():
                export_data['time_entries'].append(dict(row))
            
            # Exporter les mappings
            cursor.execute('SELECT * FROM poste_mapping')
            for row in cursor.fetchall():
                export_data['poste_mappings'].append(dict(row))
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Données exportées vers: {export_path}")
        return export_path


def show_sync_interface():
    """Interface Streamlit pour la synchronisation"""
    st.markdown("### 🔄 Synchronisation ERP ↔ TimeTracker")
    
    if 'database_sync' not in st.session_state:
        st.session_state.database_sync = DatabaseSync()
    
    sync_manager = st.session_state.database_sync
    
    # Statistiques actuelles
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Statistiques TimeTracker")
        stats = sync_manager.get_sync_statistics()
        
        st.metric("👥 Employés", stats['employees'])
        st.metric("📋 Projets", stats['projects'])
        st.metric("🔧 Tâches", stats['tasks'])
        st.metric("⏱️ Entrées Temps", stats['time_entries'])
        st.metric("🔗 Mappings Postes", stats['poste_mappings'])
        
        if stats['last_sync']:
            st.info(f"🕒 Dernière sync: {stats['last_sync'][:19]}")
        
        if stats['total_revenue'] > 0:
            st.success(f"💰 Revenus total: {stats['total_revenue']:,.2f}$ CAD")
    
    with col2:
        st.markdown("#### ⚙️ Actions de Synchronisation")
        
        if st.button("🔄 Synchronisation Complète", use_container_width=True):
            with st.spinner("Synchronisation en cours..."):
                try:
                    gestionnaire_projets = st.session_state.gestionnaire
                    gestionnaire_employes = st.session_state.gestionnaire_employes
                    gestionnaire_postes = st.session_state.gestionnaire_postes
                    
                    report = sync_manager.full_sync(
                        gestionnaire_projets, 
                        gestionnaire_employes, 
                        gestionnaire_postes
                    )
                    
                    if report['success']:
                        st.success("✅ Synchronisation réussie !")
                        st.json({
                            "Employés ajoutés": report['employees']['added'],
                            "Employés mis à jour": report['employees']['updated'],
                            "Projets ajoutés": report['projects']['added'],
                            "Projets mis à jour": report['projects']['updated'],
                            "Mappings créés": report['poste_mappings']
                        })
                    else:
                        st.error("❌ Erreurs lors de la synchronisation")
                        for error in report['errors']:
                            st.error(error)
                except Exception as e:
                    st.error(f"Erreur: {str(e)}")
        
        st.markdown("---")
        
        if st.button("💾 Créer Sauvegarde", use_container_width=True):
            try:
                backup_path = sync_manager.backup_timetracker_data()
                st.success(f"✅ Sauvegarde créée: {backup_path}")
            except Exception as e:
                st.error(f"Erreur sauvegarde: {str(e)}")
        
        if st.button("📤 Exporter JSON", use_container_width=True):
            try:
                export_path = sync_manager.export_timetracker_data_to_json()
                st.success(f"✅ Export créé: {export_path}")
            except Exception as e:
                st.error(f"Erreur export: {str(e)}")
    
    # Section des mappings de postes
    st.markdown("---")
    st.markdown("#### 🔗 Mappings Postes ERP ↔ TimeTracker")
    
    with sync_manager as sync_db:
        cursor = sync_db.connection.cursor()
        cursor.execute('''
            SELECT erp_poste_code, erp_poste_nom, timetracker_task_code, 
                   timetracker_task_name, hourly_rate
            FROM poste_mapping 
            ORDER BY hourly_rate DESC
        ''')
        mappings = cursor.fetchall()
    
    if mappings:
        import pandas as pd
        df_mappings = pd.DataFrame(mappings, columns=[
            'Code ERP', 'Poste ERP', 'Code TimeTracker', 
            'Tâche TimeTracker', 'Taux ($/h)'
        ])
        st.dataframe(df_mappings, use_container_width=True)
    else:
        st.info("Aucun mapping créé. Lancez une synchronisation complète.")


# --- END OF FILE database_sync.py ---
