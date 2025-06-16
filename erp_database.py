# erp_database.py - Gestionnaire Base de Données SQLite Unifié
# ERP Production DG Inc. - Migration JSON → SQLite + Module Formulaires

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
    
    NOUVEAU : Module Formulaires
    - formulaires → table formulaires (BT, BA, BC, DP, EST)
    - formulaire_lignes → détails des documents
    - formulaire_validations → historique et traçabilité
    """
    
    def __init__(self, db_path: str = "erp_production_dg.db"):
        self.db_path = db_path
        self.backup_dir = "backup_json"
        self.init_database()
        logger.info(f"ERPDatabase initialisé : {db_path}")
    
    def init_database(self):
        """Initialise toutes les tables de la base de données ERP avec module Formulaires"""
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
            
            # =========================================================================
            # NOUVEAU MODULE FORMULAIRES - TABLES PRINCIPALES
            # =========================================================================
            
            # 14. FORMULAIRES PRINCIPAUX (BT, BA, BC, DP, EST)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS formulaires (
                    id INTEGER PRIMARY KEY,
                    type_formulaire TEXT NOT NULL CHECK(type_formulaire IN 
                        ('BON_TRAVAIL', 'BON_ACHAT', 'BON_COMMANDE', 'DEMANDE_PRIX', 'ESTIMATION')),
                    numero_document TEXT UNIQUE NOT NULL,
                    project_id INTEGER,
                    company_id INTEGER,
                    employee_id INTEGER,
                    statut TEXT DEFAULT 'BROUILLON' CHECK(statut IN 
                        ('BROUILLON', 'VALIDÉ', 'ENVOYÉ', 'APPROUVÉ', 'TERMINÉ', 'ANNULÉ')),
                    priorite TEXT DEFAULT 'NORMAL' CHECK(priorite IN ('NORMAL', 'URGENT', 'CRITIQUE')),
                    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date_echeance DATE,
                    date_validation TIMESTAMP,
                    montant_total REAL DEFAULT 0.0,
                    notes TEXT,
                    metadonnees_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (company_id) REFERENCES companies(id),
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                )
            ''')
            
            # 15. LIGNES DE DÉTAIL DES FORMULAIRES
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS formulaire_lignes (
                    id INTEGER PRIMARY KEY,
                    formulaire_id INTEGER NOT NULL,
                    sequence_ligne INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    code_article TEXT,
                    quantite REAL NOT NULL DEFAULT 0,
                    unite TEXT DEFAULT 'UN',
                    prix_unitaire REAL DEFAULT 0.0,
                    montant_ligne REAL DEFAULT 0.0,
                    reference_materiau INTEGER,
                    reference_operation INTEGER,
                    notes_ligne TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (formulaire_id) REFERENCES formulaires(id) ON DELETE CASCADE,
                    FOREIGN KEY (reference_materiau) REFERENCES materials(id),
                    FOREIGN KEY (reference_operation) REFERENCES operations(id)
                )
            ''')
            
            # 16. HISTORIQUE ET VALIDATIONS DES FORMULAIRES
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS formulaire_validations (
                    id INTEGER PRIMARY KEY,
                    formulaire_id INTEGER NOT NULL,
                    employee_id INTEGER,
                    type_validation TEXT NOT NULL CHECK(type_validation IN 
                        ('CREATION', 'MODIFICATION', 'VALIDATION', 'APPROBATION', 'ENVOI', 'CHANGEMENT_STATUT', 'ANNULATION')),
                    ancien_statut TEXT,
                    nouveau_statut TEXT,
                    commentaires TEXT,
                    date_validation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    signature_digitale TEXT,
                    FOREIGN KEY (formulaire_id) REFERENCES formulaires(id) ON DELETE CASCADE,
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                )
            ''')
            
            # 17. PIÈCES JOINTES AUX FORMULAIRES (pour futures fonctionnalités)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS formulaire_pieces_jointes (
                    id INTEGER PRIMARY KEY,
                    formulaire_id INTEGER NOT NULL,
                    nom_fichier TEXT NOT NULL,
                    type_fichier TEXT,
                    taille_fichier INTEGER,
                    chemin_fichier TEXT,
                    description TEXT,
                    uploaded_by INTEGER,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (formulaire_id) REFERENCES formulaires(id) ON DELETE CASCADE,
                    FOREIGN KEY (uploaded_by) REFERENCES employees(id)
                )
            ''')
            
            # 18. TEMPLATES DE FORMULAIRES (pour standardisation)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS formulaire_templates (
                    id INTEGER PRIMARY KEY,
                    type_formulaire TEXT NOT NULL,
                    nom_template TEXT NOT NULL,
                    description TEXT,
                    template_json TEXT,
                    est_actif BOOLEAN DEFAULT TRUE,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES employees(id)
                )
            ''')
            
            # =========================================================================
            # INDEX POUR PERFORMANCE OPTIMALE
            # =========================================================================
            
            # Index tables existantes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_client ON projects(client_company_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_operations_project ON operations(project_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_project ON materials(project_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_entries_employee ON time_entries(employee_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_entries_project ON time_entries(project_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_competences_employee ON employee_competences(employee_id)')
            
            # Index pour module formulaires
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_type ON formulaires(type_formulaire)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_statut ON formulaires(statut)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_project ON formulaires(project_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_company ON formulaires(company_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_employee ON formulaires(employee_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_numero ON formulaires(numero_document)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_date ON formulaires(date_creation)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_priorite ON formulaires(priorite)')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaire_lignes_formulaire ON formulaire_lignes(formulaire_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaire_lignes_sequence ON formulaire_lignes(formulaire_id, sequence_ligne)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaire_lignes_materiau ON formulaire_lignes(reference_materiau)')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaire_validations_formulaire ON formulaire_validations(formulaire_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaire_validations_employee ON formulaire_validations(employee_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaire_validations_date ON formulaire_validations(date_validation)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaire_validations_type ON formulaire_validations(type_validation)')
            
            # =========================================================================
            # VUES POUR REQUÊTES COMPLEXES FRÉQUENTES
            # =========================================================================
            
            # Vue complète des formulaires avec toutes les jointures
            cursor.execute('''
                CREATE VIEW IF NOT EXISTS view_formulaires_complets AS
                SELECT 
                    f.*,
                    c.nom as company_nom,
                    c.secteur as company_secteur,
                    c.adresse as company_adresse,
                    e.prenom || ' ' || e.nom as employee_nom,
                    e.poste as employee_poste,
                    e.departement as employee_departement,
                    p.nom_projet as project_nom,
                    p.statut as project_statut,
                    p.priorite as project_priorite,
                    COUNT(fl.id) as nombre_lignes,
                    COALESCE(SUM(fl.montant_ligne), 0) as montant_calcule,
                    MAX(fv.date_validation) as derniere_action,
                    (SELECT COUNT(*) FROM formulaire_validations fv2 WHERE fv2.formulaire_id = f.id) as nombre_validations
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN employees e ON f.employee_id = e.id  
                LEFT JOIN projects p ON f.project_id = p.id
                LEFT JOIN formulaire_lignes fl ON f.id = fl.formulaire_id
                LEFT JOIN formulaire_validations fv ON f.id = fv.formulaire_id
                GROUP BY f.id
            ''')
            
            # Vue des formulaires en attente par employé
            cursor.execute('''
                CREATE VIEW IF NOT EXISTS view_formulaires_en_attente AS
                SELECT 
                    f.*,
                    e.prenom || ' ' || e.nom as responsable_nom,
                    p.nom_projet as project_nom,
                    c.nom as company_nom,
                    CASE 
                        WHEN f.date_echeance < DATE('now') THEN 'RETARD'
                        WHEN f.date_echeance <= DATE('now', '+3 days') THEN 'URGENT'
                        ELSE 'NORMAL'
                    END as urgence_echeance
                FROM formulaires f
                LEFT JOIN employees e ON f.employee_id = e.id
                LEFT JOIN projects p ON f.project_id = p.id
                LEFT JOIN companies c ON f.company_id = c.id
                WHERE f.statut IN ('BROUILLON', 'VALIDÉ', 'ENVOYÉ')
                ORDER BY 
                    CASE f.priorite 
                        WHEN 'CRITIQUE' THEN 1
                        WHEN 'URGENT' THEN 2
                        WHEN 'NORMAL' THEN 3
                    END,
                    f.date_echeance ASC
            ''')
            
            # =========================================================================
            # TRIGGERS POUR AUTOMATISATION
            # =========================================================================
            
            # Trigger pour mise à jour automatique des montants lors d'insertion
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS trigger_update_formulaire_montant_insert
                AFTER INSERT ON formulaire_lignes
                FOR EACH ROW
                BEGIN
                    UPDATE formulaire_lignes 
                    SET montant_ligne = NEW.quantite * NEW.prix_unitaire
                    WHERE id = NEW.id;
                    
                    UPDATE formulaires 
                    SET montant_total = (
                        SELECT COALESCE(SUM(quantite * prix_unitaire), 0) 
                        FROM formulaire_lignes 
                        WHERE formulaire_id = NEW.formulaire_id
                    ),
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = NEW.formulaire_id;
                END;
            ''')
            
            # Trigger pour mise à jour des montants lors de modification
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS trigger_update_formulaire_montant_update
                AFTER UPDATE ON formulaire_lignes
                FOR EACH ROW
                BEGIN
                    UPDATE formulaire_lignes 
                    SET montant_ligne = NEW.quantite * NEW.prix_unitaire
                    WHERE id = NEW.id;
                    
                    UPDATE formulaires 
                    SET montant_total = (
                        SELECT COALESCE(SUM(quantite * prix_unitaire), 0) 
                        FROM formulaire_lignes 
                        WHERE formulaire_id = NEW.formulaire_id
                    ),
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = NEW.formulaire_id;
                END;
            ''')
            
            # Trigger pour mise à jour des montants lors de suppression
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS trigger_update_formulaire_montant_delete
                AFTER DELETE ON formulaire_lignes
                FOR EACH ROW
                BEGIN
                    UPDATE formulaires 
                    SET montant_total = (
                        SELECT COALESCE(SUM(quantite * prix_unitaire), 0) 
                        FROM formulaire_lignes 
                        WHERE formulaire_id = OLD.formulaire_id
                    ),
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = OLD.formulaire_id;
                END;
            ''')
            
            # Trigger pour validation automatique des numéros de documents
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS trigger_validate_numero_document
                BEFORE INSERT ON formulaires
                FOR EACH ROW
                BEGIN
                    SELECT CASE 
                        WHEN NEW.type_formulaire = 'BON_TRAVAIL' AND NEW.numero_document NOT LIKE 'BT-%' THEN
                            RAISE(ABORT, 'Numéro Bon de Travail doit commencer par BT-')
                        WHEN NEW.type_formulaire = 'BON_ACHAT' AND NEW.numero_document NOT LIKE 'BA-%' THEN
                            RAISE(ABORT, 'Numéro Bon d''Achat doit commencer par BA-')
                        WHEN NEW.type_formulaire = 'BON_COMMANDE' AND NEW.numero_document NOT LIKE 'BC-%' THEN
                            RAISE(ABORT, 'Numéro Bon de Commande doit commencer par BC-')
                        WHEN NEW.type_formulaire = 'DEMANDE_PRIX' AND NEW.numero_document NOT LIKE 'DP-%' THEN
                            RAISE(ABORT, 'Numéro Demande de Prix doit commencer par DP-')
                        WHEN NEW.type_formulaire = 'ESTIMATION' AND NEW.numero_document NOT LIKE 'EST-%' THEN
                            RAISE(ABORT, 'Numéro Estimation doit commencer par EST-')
                    END;
                END;
            ''')
            
            # Trigger pour mise à jour automatique du champ updated_at
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS trigger_formulaires_updated_at
                AFTER UPDATE ON formulaires
                FOR EACH ROW
                BEGIN
                    UPDATE formulaires 
                    SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = NEW.id;
                END;
            ''')
            
            conn.commit()
            logger.info("Base de données ERP initialisée avec succès - Module Formulaires inclus")
    
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
            'project_assignments', 'time_entries',
            # Nouvelles tables formulaires
            'formulaires', 'formulaire_lignes', 'formulaire_validations',
            'formulaire_pieces_jointes', 'formulaire_templates'
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
                
                # NOUVELLES VÉRIFICATIONS MODULE FORMULAIRES
                
                # Formulaires → Projects
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM formulaires f
                    WHERE f.project_id IS NOT NULL 
                    AND f.project_id NOT IN (SELECT id FROM projects)
                ''')
                checks['formulaires_projects_fk'] = cursor.fetchone()['orphans'] == 0
                
                # Formulaires → Companies
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM formulaires f
                    WHERE f.company_id IS NOT NULL 
                    AND f.company_id NOT IN (SELECT id FROM companies)
                ''')
                checks['formulaires_companies_fk'] = cursor.fetchone()['orphans'] == 0
                
                # Formulaires → Employees
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM formulaires f
                    WHERE f.employee_id IS NOT NULL 
                    AND f.employee_id NOT IN (SELECT id FROM employees)
                ''')
                checks['formulaires_employees_fk'] = cursor.fetchone()['orphans'] == 0
                
                # Formulaire_lignes → Formulaires
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM formulaire_lignes fl
                    WHERE fl.formulaire_id NOT IN (SELECT id FROM formulaires)
                ''')
                checks['formulaire_lignes_formulaires_fk'] = cursor.fetchone()['orphans'] == 0
                
                # Formulaire_validations → Formulaires
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM formulaire_validations fv
                    WHERE fv.formulaire_id NOT IN (SELECT id FROM formulaires)
                ''')
                checks['formulaire_validations_formulaires_fk'] = cursor.fetchone()['orphans'] == 0
                
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
            'total_records': 0,
            'formulaires_info': {}
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
            
            # Informations spécifiques aux formulaires
            if 'formulaires' in tables:
                cursor.execute('''
                    SELECT type_formulaire, COUNT(*) as count 
                    FROM formulaires 
                    GROUP BY type_formulaire
                ''')
                for row in cursor.fetchall():
                    info['formulaires_info'][row['type_formulaire']] = row['count']
        
        return info
    
    # =========================================================================
    # MÉTHODES SPÉCIFIQUES AU MODULE FORMULAIRES
    # =========================================================================
    
    def get_formulaires_statistics(self) -> Dict[str, Any]:
        """Retourne des statistiques complètes sur les formulaires"""
        try:
            stats = {
                'total_formulaires': 0,
                'par_type': {},
                'par_statut': {},
                'montant_total': 0.0,
                'tendances_mensuelles': {},
                'en_retard': 0,
                'en_attente_validation': 0
            }
            
            # Statistiques globales
            query = '''
                SELECT 
                    type_formulaire,
                    statut,
                    COUNT(*) as count,
                    SUM(montant_total) as total_montant,
                    strftime('%Y-%m', date_creation) as mois
                FROM formulaires
                GROUP BY type_formulaire, statut, mois
                ORDER BY mois DESC
            '''
            
            rows = self.execute_query(query)
            
            for row in rows:
                # Par type
                type_form = row['type_formulaire']
                if type_form not in stats['par_type']:
                    stats['par_type'][type_form] = {'count': 0, 'montant': 0.0}
                stats['par_type'][type_form]['count'] += row['count']
                stats['par_type'][type_form]['montant'] += row['total_montant'] or 0
                
                # Par statut
                statut = row['statut']
                if statut not in stats['par_statut']:
                    stats['par_statut'][statut] = 0
                stats['par_statut'][statut] += row['count']
                
                # Totaux
                stats['total_formulaires'] += row['count']
                stats['montant_total'] += row['total_montant'] or 0
                
                # Tendances mensuelles
                mois = row['mois']
                if mois and mois not in stats['tendances_mensuelles']:
                    stats['tendances_mensuelles'][mois] = {'count': 0, 'montant': 0.0}
                if mois:
                    stats['tendances_mensuelles'][mois]['count'] += row['count']
                    stats['tendances_mensuelles'][mois]['montant'] += row['total_montant'] or 0
            
            # Formulaires en retard
            query_retard = '''
                SELECT COUNT(*) as count FROM formulaires 
                WHERE date_echeance < DATE('now') 
                AND statut NOT IN ('TERMINÉ', 'ANNULÉ')
            '''
            result = self.execute_query(query_retard)
            stats['en_retard'] = result[0]['count'] if result else 0
            
            # Formulaires en attente de validation
            query_attente = '''
                SELECT COUNT(*) as count FROM formulaires 
                WHERE statut IN ('BROUILLON', 'VALIDÉ')
            '''
            result = self.execute_query(query_attente)
            stats['en_attente_validation'] = result[0]['count'] if result else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur statistiques formulaires: {e}")
            return {}
    
    def get_formulaires_en_attente_validation(self, employee_id: int = None) -> List[Dict]:
        """Retourne les formulaires en attente de validation"""
        try:
            query = '''
                SELECT * FROM view_formulaires_en_attente
                WHERE 1=1
            '''
            
            params = []
            if employee_id:
                query += " AND employee_id = ?"
                params.append(employee_id)
            
            query += " LIMIT 50"  # Limiter pour performance
            
            rows = self.execute_query(query, tuple(params))
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur formulaires en attente: {e}")
            return []
    
    def get_formulaire_with_details(self, formulaire_id: int) -> Dict:
        """Récupère un formulaire avec tous ses détails (vue complète)"""
        try:
            query = '''
                SELECT * FROM view_formulaires_complets
                WHERE id = ?
            '''
            result = self.execute_query(query, (formulaire_id,))
            if not result:
                return {}
            
            formulaire = dict(result[0])
            
            # Ajouter les lignes de détail
            query_lignes = '''
                SELECT * FROM formulaire_lignes 
                WHERE formulaire_id = ? 
                ORDER BY sequence_ligne
            '''
            lignes = self.execute_query(query_lignes, (formulaire_id,))
            formulaire['lignes'] = [dict(ligne) for ligne in lignes]
            
            # Ajouter l'historique des validations
            query_validations = '''
                SELECT fv.*, e.prenom || ' ' || e.nom as validator_nom,
                       e.poste as validator_poste
                FROM formulaire_validations fv
                LEFT JOIN employees e ON fv.employee_id = e.id
                WHERE fv.formulaire_id = ?
                ORDER BY fv.date_validation DESC
            '''
            validations = self.execute_query(query_validations, (formulaire_id,))
            formulaire['validations'] = [dict(val) for val in validations]
            
            return formulaire
            
        except Exception as e:
            logger.error(f"Erreur récupération formulaire détaillé: {e}")
            return {}
    
    def export_formulaire_data(self, formulaire_id: int) -> Dict:
        """Exporte toutes les données d'un formulaire pour génération PDF/Excel"""
        try:
            formulaire = self.get_formulaire_with_details(formulaire_id)
            if not formulaire:
                return {}
            
            # Enrichir avec données pour export
            export_data = {
                'formulaire': formulaire,
                'export_date': datetime.now().isoformat(),
                'export_by': 'System',  # À enrichir avec utilisateur courant
                'formatted_data': {
                    'numero_complet': formulaire.get('numero_document', ''),
                    'type_libelle': self._get_type_formulaire_libelle(formulaire.get('type_formulaire', '')),
                    'montant_total_formate': f"{formulaire.get('montant_total', 0):,.2f} $ CAD",
                    'statut_couleur': self._get_statut_couleur(formulaire.get('statut', '')),
                    'priorite_icon': self._get_priorite_icon(formulaire.get('priorite', ''))
                }
            }
            
            return export_data
            
        except Exception as e:
            logger.error(f"Erreur export formulaire: {e}")
            return {}
    
    def _get_type_formulaire_libelle(self, type_formulaire: str) -> str:
        """Retourne le libellé complet d'un type de formulaire"""
        libelles = {
            'BON_TRAVAIL': 'Bon de Travail',
            'BON_ACHAT': "Bon d'Achats",
            'BON_COMMANDE': 'Bon de Commande',
            'DEMANDE_PRIX': 'Demande de Prix',
            'ESTIMATION': 'Estimation'
        }
        return libelles.get(type_formulaire, type_formulaire)
    
    def _get_statut_couleur(self, statut: str) -> str:
        """Retourne la couleur associée à un statut"""
        couleurs = {
            'BROUILLON': '#f59e0b',
            'VALIDÉ': '#3b82f6',
            'ENVOYÉ': '#8b5cf6',
            'APPROUVÉ': '#10b981',
            'TERMINÉ': '#059669',
            'ANNULÉ': '#ef4444'
        }
        return couleurs.get(statut, '#6b7280')
    
    def _get_priorite_icon(self, priorite: str) -> str:
        """Retourne l'icône associée à une priorité"""
        icons = {
            'NORMAL': '🟢',
            'URGENT': '🟡',
            'CRITIQUE': '🔴'
        }
        return icons.get(priorite, '⚪')
    
    def dupliquer_formulaire(self, formulaire_id: int, nouveau_type: str = None) -> int:
        """Duplique un formulaire existant avec nouveau numéro"""
        try:
            # Récupérer le formulaire original avec détails
            formulaire_original = self.get_formulaire_with_details(formulaire_id)
            if not formulaire_original:
                return None
            
            # Déterminer le nouveau type ou garder l'original
            type_formulaire = nouveau_type or formulaire_original['type_formulaire']
            
            # Générer nouveau numéro
            nouveau_numero = self._generer_numero_document(type_formulaire)
            
            # Créer le nouveau formulaire
            query_insert = '''
                INSERT INTO formulaires 
                (type_formulaire, numero_document, project_id, company_id, employee_id,
                 statut, priorite, date_echeance, notes, metadonnees_json)
                VALUES (?, ?, ?, ?, ?, 'BROUILLON', ?, ?, ?, ?)
            '''
            
            nouveau_id = self.execute_insert(query_insert, (
                type_formulaire,
                nouveau_numero,
                formulaire_original.get('project_id'),
                formulaire_original.get('company_id'),
                formulaire_original.get('employee_id'),
                formulaire_original.get('priorite'),
                formulaire_original.get('date_echeance'),
                f"Copie de {formulaire_original.get('numero_document', '')} - {formulaire_original.get('notes', '')}",
                formulaire_original.get('metadonnees_json')
            ))
            
            # Dupliquer les lignes de détail
            if nouveau_id and formulaire_original.get('lignes'):
                for ligne in formulaire_original['lignes']:
                    query_ligne = '''
                        INSERT INTO formulaire_lignes
                        (formulaire_id, sequence_ligne, description, code_article,
                         quantite, unite, prix_unitaire, reference_materiau, notes_ligne)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    '''
                    self.execute_insert(query_ligne, (
                        nouveau_id,
                        ligne['sequence_ligne'],
                        ligne['description'],
                        ligne.get('code_article'),
                        ligne['quantite'],
                        ligne['unite'],
                        ligne['prix_unitaire'],
                        ligne.get('reference_materiau'),
                        ligne.get('notes_ligne')
                    ))
            
            # Enregistrer l'action de duplication
            self._enregistrer_validation(
                nouveau_id, 
                formulaire_original.get('employee_id'), 
                'CREATION',
                f"Formulaire dupliqué depuis {formulaire_original.get('numero_document', '')}"
            )
            
            return nouveau_id
            
        except Exception as e:
            logger.error(f"Erreur duplication formulaire: {e}")
            return None
    
    def _generer_numero_document(self, type_formulaire: str) -> str:
        """Génère un numéro de document automatique"""
        try:
            prefixes = {
                'BON_TRAVAIL': 'BT',
                'BON_ACHAT': 'BA',
                'BON_COMMANDE': 'BC',
                'DEMANDE_PRIX': 'DP',
                'ESTIMATION': 'EST'
            }
            
            prefix = prefixes.get(type_formulaire, 'DOC')
            annee = datetime.now().year
            
            # Récupérer le dernier numéro pour ce type et cette année
            query = '''
                SELECT numero_document FROM formulaires 
                WHERE type_formulaire = ? AND numero_document LIKE ?
                ORDER BY id DESC LIMIT 1
            '''
            pattern = f"{prefix}-{annee}-%"
            result = self.execute_query(query, (type_formulaire, pattern))
            
            if result:
                last_num = result[0]['numero_document']
                sequence = int(last_num.split('-')[-1]) + 1
            else:
                sequence = 1
            
            return f"{prefix}-{annee}-{sequence:03d}"
            
        except Exception as e:
            logger.error(f"Erreur génération numéro document: {e}")
            return f"ERR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def _enregistrer_validation(self, formulaire_id: int, employee_id: int, type_validation: str, commentaires: str):
        """Enregistre une validation dans l'historique"""
        try:
            query = '''
                INSERT INTO formulaire_validations
                (formulaire_id, employee_id, type_validation, commentaires)
                VALUES (?, ?, ?, ?)
            '''
            self.execute_insert(query, (formulaire_id, employee_id, type_validation, commentaires))
        except Exception as e:
            logger.error(f"Erreur enregistrement validation: {e}")

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
