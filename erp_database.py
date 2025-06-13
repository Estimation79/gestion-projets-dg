# erp_database.py - Gestionnaire Base de Données SQLite Unifié
# ERP Production DG Inc. - Migration JSON → SQLite

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
import shutil
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ERPDatabase:
    """
    Gestionnaire de base de données SQLite unifié pour ERP Production DG Inc.
    
    Remplace tous les fichiers JSON par une base de données relationnelle cohérente :
    - projets_data.json → tables projects, operations, materials
    - crm_data.json → tables companies, contacts, interactions  
    - employees_data.json → tables employees, employee_competences
    - inventaire_v2.json → tables inventory_items, inventory_history
    - timetracker.db → intégration dans base principale
    """
    
    def __init__(self, db_path: str = "erp_production_dg.db"):
        self.db_path = db_path
        self.backup_dir = "backup_json"
        self.init_database()
        logger.info(f"ERPDatabase initialisé : {db_path}")
    
    def init_database(self):
        """Initialise toutes les tables de la base de données ERP"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Activer les clés étrangères
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # 1. ENTREPRISES (CRM)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY,
                    nom TEXT NOT NULL,
                    secteur TEXT,
                    adresse TEXT,
                    site_web TEXT,
                    contact_principal_id INTEGER,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 2. CONTACTS (CRM)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY,
                    prenom TEXT NOT NULL,
                    nom_famille TEXT NOT NULL,
                    email TEXT,
                    telephone TEXT,
                    company_id INTEGER,
                    role_poste TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies(id)
                )
            ''')
            
            # 3. PROJETS (Core ERP)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY,
                    nom_projet TEXT NOT NULL,
                    client_company_id INTEGER,
                    client_contact_id INTEGER,
                    client_nom_cache TEXT,
                    client_legacy TEXT,
                    statut TEXT DEFAULT 'À FAIRE',
                    priorite TEXT DEFAULT 'MOYEN',
                    tache TEXT,
                    date_soumis DATE,
                    date_prevu DATE,
                    bd_ft_estime REAL,
                    prix_estime REAL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_company_id) REFERENCES companies(id),
                    FOREIGN KEY (client_contact_id) REFERENCES contacts(id)
                )
            ''')
            
            # 4. EMPLOYÉS (RH)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY,
                    prenom TEXT NOT NULL,
                    nom TEXT NOT NULL,
                    email TEXT UNIQUE,
                    telephone TEXT,
                    poste TEXT,
                    departement TEXT,
                    statut TEXT DEFAULT 'ACTIF',
                    type_contrat TEXT DEFAULT 'CDI',
                    date_embauche DATE,
                    salaire REAL,
                    manager_id INTEGER,
                    charge_travail INTEGER DEFAULT 80,
                    notes TEXT,
                    photo_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (manager_id) REFERENCES employees(id)
                )
            ''')
            
            # 5. COMPÉTENCES EMPLOYÉS
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employee_competences (
                    id INTEGER PRIMARY KEY,
                    employee_id INTEGER,
                    nom_competence TEXT,
                    niveau TEXT,
                    certifie BOOLEAN DEFAULT FALSE,
                    date_obtention DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                )
            ''')
            
            # 6. POSTES DE TRAVAIL (61 unités)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS work_centers (
                    id INTEGER PRIMARY KEY,
                    nom TEXT NOT NULL,
                    departement TEXT,
                    categorie TEXT,
                    type_machine TEXT,
                    capacite_theorique REAL,
                    operateurs_requis INTEGER,
                    cout_horaire REAL,
                    competences_requises TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 7. OPÉRATIONS (Gammes)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER,
                    work_center_id INTEGER,
                    sequence_number INTEGER,
                    description TEXT,
                    temps_estime REAL,
                    ressource TEXT,
                    statut TEXT DEFAULT 'À FAIRE',
                    poste_travail TEXT,
                    operation_legacy_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (work_center_id) REFERENCES work_centers(id)
                )
            ''')
            
            # 8. MATÉRIAUX/BOM
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER,
                    material_legacy_id INTEGER,
                    code_materiau TEXT,
                    designation TEXT,
                    quantite REAL,
                    unite TEXT,
                    prix_unitaire REAL,
                    fournisseur TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            ''')
            
            # 9. INVENTAIRE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory_items (
                    id INTEGER PRIMARY KEY,
                    nom TEXT NOT NULL,
                    type_produit TEXT,
                    quantite_imperial TEXT,
                    quantite_metric REAL,
                    limite_minimale_imperial TEXT,
                    limite_minimale_metric REAL,
                    quantite_reservee_imperial TEXT,
                    quantite_reservee_metric REAL,
                    statut TEXT,
                    description TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 10. HISTORIQUE INVENTAIRE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory_history (
                    id INTEGER PRIMARY KEY,
                    inventory_item_id INTEGER,
                    action TEXT,
                    quantite_avant TEXT,
                    quantite_apres TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inventory_item_id) REFERENCES inventory_items(id)
                )
            ''')
            
            # 11. INTERACTIONS CRM
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY,
                    contact_id INTEGER,
                    company_id INTEGER,
                    type_interaction TEXT,
                    date_interaction DATETIME,
                    resume TEXT,
                    details TEXT,
                    resultat TEXT,
                    suivi_prevu DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (contact_id) REFERENCES contacts(id),
                    FOREIGN KEY (company_id) REFERENCES companies(id)
                )
            ''')
            
            # 12. ASSIGNATIONS PROJETS-EMPLOYÉS
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_assignments (
                    project_id INTEGER,
                    employee_id INTEGER,
                    role_projet TEXT,
                    date_assignation DATE DEFAULT CURRENT_DATE,
                    PRIMARY KEY (project_id, employee_id),
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                )
            ''')
            
            # 13. TIME ENTRIES (TimeTracker Unifié)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS time_entries (
                    id INTEGER PRIMARY KEY,
                    employee_id INTEGER,
                    project_id INTEGER,
                    operation_id INTEGER,
                    punch_in TIMESTAMP,
                    punch_out TIMESTAMP,
                    total_hours REAL,
                    hourly_rate REAL,
                    total_cost REAL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id),
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (operation_id) REFERENCES operations(id)
                )
            ''')
            
            # INDEX pour performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_client ON projects(client_company_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_operations_project ON operations(project_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_project ON materials(project_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_entries_employee ON time_entries(employee_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_entries_project ON time_entries(project_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_competences_employee ON employee_competences(employee_id)')
            
            conn.commit()
            logger.info("Base de données ERP initialisée avec succès")
    
    def backup_json_files(self):
        """Sauvegarde tous les fichiers JSON avant migration"""
        json_files = [
            "projets_data.json",
            "crm_data.json", 
            "employees_data.json",
            "inventaire_v2.json",
            "timetracker.db"
        ]
        
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for file in json_files:
            if os.path.exists(file):
                backup_name = f"{self.backup_dir}/{file}.backup_{backup_timestamp}"
                shutil.copy2(file, backup_name)
                logger.info(f"Sauvegarde créée : {backup_name}")
        
        logger.info(f"Sauvegarde JSON complète dans {self.backup_dir}")
    
    def get_connection(self) -> sqlite3.Connection:
        """Retourne une connexion à la base de données"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def execute_query(self, query: str, params: tuple = None) -> List[sqlite3.Row]:
        """Exécute une requête SELECT et retourne les résultats"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Exécute une requête INSERT/UPDATE/DELETE et retourne le nombre de lignes affectées"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.rowcount
    
    def execute_insert(self, query: str, params: tuple = None) -> int:
        """Exécute un INSERT et retourne l'ID de la nouvelle ligne"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.lastrowid
    
    def get_table_count(self, table_name: str) -> int:
        """Retourne le nombre d'enregistrements dans une table"""
        result = self.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
        return result[0]['count'] if result else 0
    
    def get_migration_status(self) -> Dict[str, int]:
        """Retourne le statut de migration de toutes les tables"""
        tables = [
            'companies', 'contacts', 'projects', 'employees', 
            'employee_competences', 'work_centers', 'operations',
            'materials', 'inventory_items', 'interactions',
            'project_assignments', 'time_entries'
        ]
        
        status = {}
        for table in tables:
            status[table] = self.get_table_count(table)
        
        return status
    
    def validate_integrity(self) -> Dict[str, bool]:
        """Valide l'intégrité des relations entre tables"""
        checks = {}
        
        try:
            # Vérifier les clés étrangères
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Projects → Companies
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM projects p
                    WHERE p.client_company_id IS NOT NULL 
                    AND p.client_company_id NOT IN (SELECT id FROM companies)
                ''')
                checks['projects_companies_fk'] = cursor.fetchone()['orphans'] == 0
                
                # Operations → Projects
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM operations o
                    WHERE o.project_id NOT IN (SELECT id FROM projects)
                ''')
                checks['operations_projects_fk'] = cursor.fetchone()['orphans'] == 0
                
                # Materials → Projects
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM materials m
                    WHERE m.project_id NOT IN (SELECT id FROM projects)
                ''')
                checks['materials_projects_fk'] = cursor.fetchone()['orphans'] == 0
                
                # Employees hierarchy
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM employees e
                    WHERE e.manager_id IS NOT NULL 
                    AND e.manager_id NOT IN (SELECT id FROM employees)
                ''')
                checks['employees_hierarchy_fk'] = cursor.fetchone()['orphans'] == 0
                
        except Exception as e:
            logger.error(f"Erreur validation intégrité: {e}")
            checks['error'] = str(e)
        
        return checks
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Retourne des informations sur le schéma de la base"""
        info = {
            'database_file': self.db_path,
            'file_size_mb': round(os.path.getsize(self.db_path) / (1024*1024), 2) if os.path.exists(self.db_path) else 0,
            'tables': {},
            'total_records': 0
        }
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Liste des tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row['name'] for row in cursor.fetchall()]
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                count = cursor.fetchone()['count']
                info['tables'][table] = count
                info['total_records'] += count
        
        return info

# Utilitaires pour conversion mesures impériales (préservation fonction existante)
def convertir_pieds_pouces_fractions_en_valeur_decimale(mesure_str: str) -> float:
    """
    Convertit une mesure impériale en valeur décimale
    Préserve la fonction existante du système
    """
    try:
        import re
        from fractions import Fraction
        from math import gcd
        
        mesure_str = str(mesure_str).strip().lower()
        mesure_str = mesure_str.replace('"', '"').replace("''", "'")
        mesure_str = mesure_str.replace('ft', "'").replace('pieds', "'").replace('pied', "'")
        mesure_str = mesure_str.replace('in', '"').replace('pouces', '"').replace('pouce', '"')
        
        if mesure_str == "0":
            return 0.0
        
        total_pieds = 0.0
        
        # Pattern pour parsing
        pattern = re.compile(
            r"^\s*(?:(?P<feet>\d+(?:\.\d+)?)\s*(?:'|\sft|\spieds?)?)?"
            r"\s*(?:(?P<inches>\d+(?:\.\d+)?)\s*(?:\"|\sin|\spouces?)?)?"
            r"\s*(?:(?P<frac_num>\d+)\s*\/\s*(?P<frac_den>\d+)\s*(?:\"|\sin|\spouces?)?)?\s*$"
        )
        
        match = pattern.match(mesure_str)
        
        if match and (match.group('feet') or match.group('inches') or match.group('frac_num')):
            pieds = float(match.group('feet')) if match.group('feet') else 0.0
            pouces = float(match.group('inches')) if match.group('inches') else 0.0
            
            if match.group('frac_num') and match.group('frac_den'):
                num, den = int(match.group('frac_num')), int(match.group('frac_den'))
                if den != 0:
                    pouces += num / den
            
            total_pieds = pieds + (pouces / 12.0)
        
        return total_pieds
        
    except Exception:
        return 0.0

def convertir_imperial_vers_metrique(mesure_imperial: str) -> float:
    """Convertit une mesure impériale en mètres"""
    pieds = convertir_pieds_pouces_fractions_en_valeur_decimale(mesure_imperial)
    return pieds * 0.3048  # 1 pied = 0.3048 mètres
