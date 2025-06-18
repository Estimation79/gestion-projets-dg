# erp_database.py - Gestionnaire Base de Données SQLite Unifié CONSOLIDÉ
# ERP Production DG Inc. - Migration JSON → SQLite + Module Formulaires Complet + Corrections Intégrées
# VERSION 2.0 - Intégration TimeTracker ↔ Bons de Travail

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
    VERSION CONSOLIDÉE - Toutes corrections intégrées automatiquement
    
    Remplace tous les fichiers JSON par une base de données relationnelle cohérente :
    - projets_data.json → tables projects, operations, materials
    - crm_data.json → tables companies, contacts, interactions  
    - employees_data.json → tables employees, employee_competences
    - inventaire_v2.json → tables inventory_items, inventory_history
    - timetracker.db → intégration dans base principale
    
    MODULE FORMULAIRES COMPLET :
    - formulaires → table formulaires (BT, BA, BC, DP, EST)
    - formulaire_lignes → détails des documents
    - formulaire_validations → historique et traçabilité
    - formulaire_pieces_jointes → gestion fichiers
    - formulaire_templates → standardisation
    
    CORRECTIONS AUTOMATIQUES INTÉGRÉES :
    - Colonnes projects corrigées (date_debut_reel, date_fin_reel)
    - Tables BT spécialisées (bt_assignations, bt_reservations_postes)
    - Toutes les améliorations de fix_database.py
    
    INTÉGRATION TIMETRACKER ↔ BONS DE TRAVAIL :
    - Synchronisation des temps et de l'avancement
    - Pointage direct depuis les BT
    - Rapports et dashboards intégrés
    """
    
    def __init__(self, db_path: str = "erp_production_dg.db"):
        self.db_path = db_path
        self.backup_dir = "backup_json"
        self.init_database()
        logger.info(f"ERPDatabase consolidé initialisé : {db_path}")
    
    def init_database(self):
        """Initialise toutes les tables de la base de données ERP avec corrections automatiques intégrées"""
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
                    type_company TEXT DEFAULT 'CLIENT',
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
            
            # 3. PROJETS (Core ERP) - CORRIGÉ avec toutes les colonnes nécessaires
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
                    date_debut_reel DATE,
                    date_fin_reel DATE,
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
                    statut TEXT DEFAULT 'ACTIF',
                    localisation TEXT,
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
                    fournisseur_principal TEXT,
                    code_interne TEXT,
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
                    employee_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inventory_item_id) REFERENCES inventory_items(id),
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
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
            # MODULE FORMULAIRES - TABLES PRINCIPALES COMPLÈTES
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
                        ('BROUILLON', 'VALIDÉ', 'ENVOYÉ', 'APPROUVÉ', 'EN COURS', 'TERMINÉ', 'ANNULÉ')),
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
                        ('CREATION', 'MODIFICATION', 'VALIDATION', 'APPROBATION', 'ENVOI', 'CHANGEMENT_STATUT', 'ANNULATION', 'ASSIGNATION', 'RESERVATION_POSTE')),
                    ancien_statut TEXT,
                    nouveau_statut TEXT,
                    commentaires TEXT,
                    date_validation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    signature_digitale TEXT,
                    FOREIGN KEY (formulaire_id) REFERENCES formulaires(id) ON DELETE CASCADE,
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                )
            ''')
            
            # 17. PIÈCES JOINTES AUX FORMULAIRES
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
            
            # 18. TEMPLATES DE FORMULAIRES
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
            
            # 19. FOURNISSEURS (Extension companies pour meilleure gestion)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fournisseurs (
                    id INTEGER PRIMARY KEY,
                    company_id INTEGER NOT NULL,
                    code_fournisseur TEXT UNIQUE,
                    categorie_produits TEXT,
                    delai_livraison_moyen INTEGER,
                    conditions_paiement TEXT DEFAULT '30 jours net',
                    evaluation_qualite INTEGER DEFAULT 5,
                    contact_commercial TEXT,
                    contact_technique TEXT,
                    certifications TEXT,
                    notes_evaluation TEXT,
                    est_actif BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies(id)
                )
            ''')
            
            # 20. APPROVISIONNEMENTS (Suivi des commandes et livraisons)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS approvisionnements (
                    id INTEGER PRIMARY KEY,
                    formulaire_id INTEGER,
                    fournisseur_id INTEGER,
                    statut_livraison TEXT DEFAULT 'EN_ATTENTE' CHECK(statut_livraison IN 
                        ('EN_ATTENTE', 'CONFIRMÉ', 'EN_PRODUCTION', 'EXPÉDIÉ', 'LIVRÉ', 'ANNULÉ')),
                    date_commande DATE,
                    date_livraison_prevue DATE,
                    date_livraison_reelle DATE,
                    numero_bon_livraison TEXT,
                    quantite_commandee REAL,
                    quantite_livree REAL,
                    notes_livraison TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (formulaire_id) REFERENCES formulaires(id),
                    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id)
                )
            ''')
            
            # =========================================================================
            # TABLES SPÉCIALISÉES BONS DE TRAVAIL - INTÉGRÉES AUTOMATIQUEMENT
            # =========================================================================
            
            # 21. ASSIGNATIONS BONS DE TRAVAIL
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bt_assignations (
                    id INTEGER PRIMARY KEY,
                    bt_id INTEGER,
                    employe_id INTEGER,
                    role_bt TEXT DEFAULT 'Opérateur',
                    date_assignation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    statut TEXT DEFAULT 'ASSIGNÉ',
                    notes_assignation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bt_id) REFERENCES formulaires(id),
                    FOREIGN KEY (employe_id) REFERENCES employees(id)
                )
            ''')
            
            # 22. RÉSERVATIONS POSTES DE TRAVAIL POUR BT
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bt_reservations_postes (
                    id INTEGER PRIMARY KEY,
                    bt_id INTEGER,
                    work_center_id INTEGER,
                    date_reservation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date_prevue DATE,
                    date_liberation TIMESTAMP,
                    statut TEXT DEFAULT 'RÉSERVÉ',
                    notes_reservation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bt_id) REFERENCES formulaires(id),
                    FOREIGN KEY (work_center_id) REFERENCES work_centers(id)
                )
            ''')
            
            # 23. AVANCEMENT BONS DE TRAVAIL (NOUVEAU - POUR INTÉGRATION TIMETRACKER)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bt_avancement (
                    id INTEGER PRIMARY KEY,
                    bt_id INTEGER NOT NULL,
                    operation_id INTEGER NOT NULL,
                    pourcentage_realise REAL DEFAULT 0.0,
                    temps_reel REAL DEFAULT 0.0,
                    notes_avancement TEXT,
                    updated_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bt_id) REFERENCES formulaires(id) ON DELETE CASCADE,
                    FOREIGN KEY (operation_id) REFERENCES operations(id) ON DELETE CASCADE,
                    FOREIGN KEY (updated_by) REFERENCES employees(id),
                    UNIQUE(bt_id, operation_id)
                )
            ''')
            
            # =========================================================================
            # INDEX POUR PERFORMANCE OPTIMALE
            # =========================================================================
            
            # Index tables existantes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_client ON projects(client_company_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_statut ON projects(statut)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_priorite ON projects(priorite)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_dates ON projects(date_soumis, date_prevu)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_operations_project ON operations(project_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_operations_work_center ON operations(work_center_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_project ON materials(project_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_entries_employee ON time_entries(employee_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_entries_project ON time_entries(project_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_competences_employee ON employee_competences(employee_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_companies_secteur ON companies(secteur)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_companies_type ON companies(type_company)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_statut ON inventory_items(statut)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_type ON inventory_items(type_produit)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_employees_statut ON employees(statut)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_employees_departement ON employees(departement)')
            
            # Index pour module formulaires
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_type ON formulaires(type_formulaire)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_statut ON formulaires(statut)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_project ON formulaires(project_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_company ON formulaires(company_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_employee ON formulaires(employee_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_numero ON formulaires(numero_document)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_date ON formulaires(date_creation)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_priorite ON formulaires(priorite)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaires_echeance ON formulaires(date_echeance)')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaire_lignes_formulaire ON formulaire_lignes(formulaire_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaire_lignes_sequence ON formulaire_lignes(formulaire_id, sequence_ligne)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaire_lignes_materiau ON formulaire_lignes(reference_materiau)')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaire_validations_formulaire ON formulaire_validations(formulaire_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaire_validations_employee ON formulaire_validations(employee_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaire_validations_date ON formulaire_validations(date_validation)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_formulaire_validations_type ON formulaire_validations(type_validation)')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_fournisseurs_company ON fournisseurs(company_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_fournisseurs_code ON fournisseurs(code_fournisseur)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_approvisionnements_formulaire ON approvisionnements(formulaire_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_approvisionnements_statut ON approvisionnements(statut_livraison)')
            
            # Index pour tables BT spécialisées
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bt_assignations_bt ON bt_assignations(bt_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bt_assignations_employe ON bt_assignations(employe_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bt_reservations_bt ON bt_reservations_postes(bt_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bt_reservations_work_center ON bt_reservations_postes(work_center_id)')
            
            # Index pour la nouvelle table bt_avancement
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bt_avancement_bt ON bt_avancement(bt_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bt_avancement_operation ON bt_avancement(operation_id)')
            
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
                    c.type_company as company_type,
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
            
            # Vue des fournisseurs avec statistiques
            cursor.execute('''
                CREATE VIEW IF NOT EXISTS view_fournisseurs_stats AS
                SELECT 
                    c.*,
                    f.code_fournisseur,
                    f.categorie_produits,
                    f.delai_livraison_moyen,
                    f.conditions_paiement,
                    f.evaluation_qualite,
                    f.est_actif as fournisseur_actif,
                    COUNT(form.id) as nombre_commandes,
                    COALESCE(SUM(form.montant_total), 0) as montant_total_commandes,
                    MAX(form.date_creation) as derniere_commande
                FROM companies c
                LEFT JOIN fournisseurs f ON c.id = f.company_id
                LEFT JOIN formulaires form ON c.id = form.company_id AND form.type_formulaire IN ('BON_ACHAT', 'BON_COMMANDE')
                WHERE c.type_company = 'FOURNISSEUR' OR f.id IS NOT NULL
                GROUP BY c.id
            ''')
            
            # Vue des stocks critiques
            cursor.execute('''
                CREATE VIEW IF NOT EXISTS view_stocks_critiques AS
                SELECT 
                    i.*,
                    CASE 
                        WHEN i.quantite_metric <= 0.001 THEN 'ÉPUISÉ'
                        WHEN i.quantite_metric <= i.limite_minimale_metric THEN 'CRITIQUE'
                        WHEN i.quantite_metric <= (i.limite_minimale_metric * 1.5) THEN 'FAIBLE'
                        ELSE 'DISPONIBLE'
                    END as statut_calcule,
                    (i.limite_minimale_metric * 2) as quantite_recommandee
                FROM inventory_items i
                WHERE i.limite_minimale_metric > 0
                ORDER BY 
                    CASE 
                        WHEN i.quantite_metric <= 0.001 THEN 1
                        WHEN i.quantite_metric <= i.limite_minimale_metric THEN 2
                        WHEN i.quantite_metric <= (i.limite_minimale_metric * 1.5) THEN 3
                        ELSE 4
                    END, i.nom
            ''')
            
            # Vue complète des projets avec toutes les informations
            cursor.execute('''
                CREATE VIEW IF NOT EXISTS view_projects_complets AS
                SELECT 
                    p.*,
                    c.nom as client_company_nom,
                    c.secteur as client_secteur,
                    c.type_company as client_type,
                    COUNT(DISTINCT o.id) as nombre_operations,
                    COUNT(DISTINCT m.id) as nombre_materiaux,
                    COUNT(DISTINCT pa.employee_id) as nombre_employes_assignes,
                    COALESCE(SUM(m.quantite * m.prix_unitaire), 0) as cout_materiaux_total,
                    COALESCE(SUM(o.temps_estime), 0) as temps_total_estime,
                    COUNT(DISTINCT f.id) as nombre_formulaires
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                LEFT JOIN operations o ON p.id = o.project_id
                LEFT JOIN materials m ON p.id = m.project_id
                LEFT JOIN project_assignments pa ON p.id = pa.project_id
                LEFT JOIN formulaires f ON p.id = f.project_id
                GROUP BY p.id
            ''')
            
            # Vue des bons de travail avec assignations
            cursor.execute('''
                CREATE VIEW IF NOT EXISTS view_bons_travail_complets AS
                SELECT 
                    f.*,
                    p.nom_projet,
                    c.nom as company_nom,
                    e.prenom || ' ' || e.nom as employee_nom,
                    COUNT(DISTINCT bta.employe_id) as nombre_employes_assignes,
                    COUNT(DISTINCT btr.work_center_id) as nombre_postes_reserves,
                    GROUP_CONCAT(DISTINCT emp.prenom || ' ' || emp.nom) as employes_assignes_noms,
                    GROUP_CONCAT(DISTINCT wc.nom) as postes_reserves_noms
                FROM formulaires f
                LEFT JOIN projects p ON f.project_id = p.id
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN employees e ON f.employee_id = e.id
                LEFT JOIN bt_assignations bta ON f.id = bta.bt_id
                LEFT JOIN bt_reservations_postes btr ON f.id = btr.bt_id
                LEFT JOIN employees emp ON bta.employe_id = emp.id
                LEFT JOIN work_centers wc ON btr.work_center_id = wc.id
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                GROUP BY f.id
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
            
            # Trigger pour mise à jour automatique du statut inventaire
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS trigger_update_inventory_status
                AFTER UPDATE OF quantite_metric ON inventory_items
                FOR EACH ROW
                BEGIN
                    UPDATE inventory_items 
                    SET statut = CASE
                        WHEN NEW.quantite_metric <= 0.001 THEN 'ÉPUISÉ'
                        WHEN NEW.quantite_metric <= NEW.limite_minimale_metric THEN 'CRITIQUE'
                        WHEN NEW.quantite_metric <= (NEW.limite_minimale_metric * 1.5) THEN 'FAIBLE'
                        ELSE 'DISPONIBLE'
                    END,
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = NEW.id AND NEW.limite_minimale_metric > 0;
                END;
            ''')
            
            # Trigger pour enregistrement automatique des modifications d'inventaire
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS trigger_inventory_history
                AFTER UPDATE OF quantite_metric ON inventory_items
                FOR EACH ROW
                WHEN OLD.quantite_metric != NEW.quantite_metric
                BEGIN
                    INSERT INTO inventory_history (inventory_item_id, action, quantite_avant, quantite_apres, notes)
                    VALUES (NEW.id, 'MODIFICATION', CAST(OLD.quantite_metric AS TEXT), CAST(NEW.quantite_metric AS TEXT), 'Modification automatique');
                END;
            ''')
            
            # Trigger pour mise à jour automatique des timestamps projects
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS trigger_projects_updated_at
                AFTER UPDATE ON projects
                FOR EACH ROW
                BEGIN
                    UPDATE projects 
                    SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = NEW.id;
                END;
            ''')
            
            # Trigger pour enregistrement automatique des validations de changement de statut
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS trigger_auto_log_status_change
                AFTER UPDATE OF statut ON formulaires
                FOR EACH ROW
                WHEN OLD.statut != NEW.statut
                BEGIN
                    INSERT INTO formulaire_validations (formulaire_id, type_validation, ancien_statut, nouveau_statut, commentaires)
                    VALUES (NEW.id, 'CHANGEMENT_STATUT', OLD.statut, NEW.statut, 'Changement automatique de statut');
                END;
            ''')
            
            conn.commit()
            
            # =========================================================================
            # CORRECTIONS AUTOMATIQUES POST-CRÉATION (Migration des anciennes colonnes)
            # =========================================================================
            
            # Vérifier et ajouter les colonnes manquantes si elles n'existent pas déjà
            self._apply_automatic_fixes(cursor)
            
            conn.commit()
            logger.info("Base de données ERP consolidée initialisée avec succès - Toutes corrections automatiques appliquées")
    
    def _apply_automatic_fixes(self, cursor):
        """Applique automatiquement toutes les corrections nécessaires"""
        try:
            # Vérifier les colonnes existantes dans projects
            cursor.execute("PRAGMA table_info(projects)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            
            # Ajouter les colonnes manquantes si nécessaire
            if 'date_debut_reel' not in existing_columns:
                cursor.execute("ALTER TABLE projects ADD COLUMN date_debut_reel DATE")
                logger.info("✅ Colonne date_debut_reel ajoutée automatiquement")
            
            if 'date_fin_reel' not in existing_columns:
                cursor.execute("ALTER TABLE projects ADD COLUMN date_fin_reel DATE")
                logger.info("✅ Colonne date_fin_reel ajoutée automatiquement")
            
            # Vérifier et corriger d'autres tables si nécessaire
            cursor.execute("PRAGMA table_info(bt_assignations)")
            assign_columns = [col[1] for col in cursor.fetchall()]
            if 'role_bt' not in assign_columns:
                cursor.execute("ALTER TABLE bt_assignations ADD COLUMN role_bt TEXT DEFAULT 'Opérateur'")
                logger.info("✅ Colonne role_bt ajoutée automatiquement à bt_assignations")

            logger.info("🔧 Corrections automatiques appliquées avec succès")
            
        except Exception as e:
            logger.warning(f"Avertissement lors des corrections automatiques: {e}")
    
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
            # Tables formulaires
            'formulaires', 'formulaire_lignes', 'formulaire_validations',
            'formulaire_pieces_jointes', 'formulaire_templates',
            'fournisseurs', 'approvisionnements',
            # Tables BT spécialisées
            'bt_assignations', 'bt_reservations_postes', 'bt_avancement'
        ]
        
        status = {}
        for table in tables:
            try:
                status[table] = self.get_table_count(table)
            except Exception as e:
                logger.warning(f"Erreur lecture table {table}: {e}")
                status[table] = 0
        
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
                
                # VÉRIFICATIONS MODULE FORMULAIRES
                
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
                
                # Fournisseurs → Companies
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM fournisseurs f
                    WHERE f.company_id NOT IN (SELECT id FROM companies)
                ''')
                checks['fournisseurs_companies_fk'] = cursor.fetchone()['orphans'] == 0
                
                # BT Assignations → Formulaires
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM bt_assignations bta
                    WHERE bta.bt_id NOT IN (SELECT id FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL')
                ''')
                checks['bt_assignations_formulaires_fk'] = cursor.fetchone()['orphans'] == 0
                
                # BT Réservations → Work Centers
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM bt_reservations_postes btr
                    WHERE btr.work_center_id NOT IN (SELECT id FROM work_centers)
                ''')
                checks['bt_reservations_work_centers_fk'] = cursor.fetchone()['orphans'] == 0

                # BT Avancement -> Formulaires
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM bt_avancement bta
                    WHERE bta.bt_id NOT IN (SELECT id FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL')
                ''')
                checks['bt_avancement_formulaires_fk'] = cursor.fetchone()['orphans'] == 0

                # BT Avancement -> Operations
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM bt_avancement bta
                    WHERE bta.operation_id NOT IN (SELECT id FROM operations)
                ''')
                checks['bt_avancement_operations_fk'] = cursor.fetchone()['orphans'] == 0

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
            'formulaires_info': {},
            'fournisseurs_info': {},
            'stocks_critiques': 0,
            'bt_info': {},
            'corrections_appliquees': True
        }
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Liste des tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row['name'] for row in cursor.fetchall()]
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    count = cursor.fetchone()['count']
                    info['tables'][table] = count
                    info['total_records'] += count
                except Exception as e:
                    logger.warning(f"Erreur lecture table {table}: {e}")
                    info['tables'][table] = 0
            
            # Informations spécifiques aux formulaires
            if 'formulaires' in tables:
                cursor.execute('''
                    SELECT type_formulaire, COUNT(*) as count 
                    FROM formulaires 
                    GROUP BY type_formulaire
                ''')
                for row in cursor.fetchall():
                    info['formulaires_info'][row['type_formulaire']] = row['count']
            
            # Informations sur les fournisseurs
            if 'fournisseurs' in tables:
                cursor.execute('SELECT COUNT(*) as count FROM fournisseurs WHERE est_actif = TRUE')
                result = cursor.fetchone()
                info['fournisseurs_info']['actifs'] = result['count'] if result else 0
            
            # Stocks critiques
            if 'inventory_items' in tables:
                cursor.execute("SELECT COUNT(*) as count FROM inventory_items WHERE statut IN ('CRITIQUE', 'FAIBLE', 'ÉPUISÉ')")
                result = cursor.fetchone()
                info['stocks_critiques'] = result['count'] if result else 0
            
            # Informations BT
            if 'bt_assignations' in tables and 'bt_reservations_postes' in tables:
                cursor.execute('SELECT COUNT(*) as count FROM bt_assignations')
                result = cursor.fetchone()
                info['bt_info']['assignations'] = result['count'] if result else 0
                
                cursor.execute('SELECT COUNT(*) as count FROM bt_reservations_postes')
                result = cursor.fetchone()
                info['bt_info']['reservations'] = result['count'] if result else 0
        
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
                'en_attente_validation': 0,
                'top_fournisseurs': [],
                'conversion_ba_bc': {'total_ba': 0, 'convertis_bc': 0, 'taux_conversion': 0.0},
                'bt_statistiques': {'total_bt': 0, 'assignations': 0, 'postes_reserves': 0}
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
            
            # Top fournisseurs
            query_fournisseurs = '''
                SELECT c.nom, COUNT(f.id) as nb_commandes, SUM(f.montant_total) as montant_total
                FROM formulaires f
                JOIN companies c ON f.company_id = c.id
                WHERE f.type_formulaire IN ('BON_ACHAT', 'BON_COMMANDE')
                GROUP BY c.id, c.nom
                ORDER BY montant_total DESC
                LIMIT 5
            '''
            rows_fournisseurs = self.execute_query(query_fournisseurs)
            stats['top_fournisseurs'] = [dict(row) for row in rows_fournisseurs]
            
            # Statistiques conversion BA → BC
            query_ba = "SELECT COUNT(*) as count FROM formulaires WHERE type_formulaire = 'BON_ACHAT'"
            result_ba = self.execute_query(query_ba)
            stats['conversion_ba_bc']['total_ba'] = result_ba[0]['count'] if result_ba else 0
            
            query_bc = '''
                SELECT COUNT(*) as count FROM formulaires 
                WHERE type_formulaire = 'BON_COMMANDE' 
                AND metadonnees_json LIKE '%ba_source_id%'
            '''
            result_bc = self.execute_query(query_bc)
            stats['conversion_ba_bc']['convertis_bc'] = result_bc[0]['count'] if result_bc else 0
            
            if stats['conversion_ba_bc']['total_ba'] > 0:
                stats['conversion_ba_bc']['taux_conversion'] = (
                    stats['conversion_ba_bc']['convertis_bc'] / stats['conversion_ba_bc']['total_ba'] * 100
                )
            
            # Statistiques BT spécialisées
            query_bt = "SELECT COUNT(*) as count FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL'"
            result_bt = self.execute_query(query_bt)
            stats['bt_statistiques']['total_bt'] = result_bt[0]['count'] if result_bt else 0
            
            query_bt_assignations = "SELECT COUNT(*) as count FROM bt_assignations"
            result_bt_assign = self.execute_query(query_bt_assignations)
            stats['bt_statistiques']['assignations'] = result_bt_assign[0]['count'] if result_bt_assign else 0
            
            query_bt_postes = "SELECT COUNT(*) as count FROM bt_reservations_postes"
            result_bt_postes = self.execute_query(query_bt_postes)
            stats['bt_statistiques']['postes_reserves'] = result_bt_postes[0]['count'] if result_bt_postes else 0
            
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
            
            # Si c'est un BT, ajouter les assignations et réservations
            if formulaire.get('type_formulaire') == 'BON_TRAVAIL':
                # Assignations employés
                query_assignations = '''
                    SELECT bta.*, e.prenom || ' ' || e.nom as employe_nom, e.poste as employe_poste
                    FROM bt_assignations bta
                    LEFT JOIN employees e ON bta.employe_id = e.id
                    WHERE bta.bt_id = ?
                    ORDER BY bta.date_assignation DESC
                '''
                assignations = self.execute_query(query_assignations, (formulaire_id,))
                formulaire['assignations'] = [dict(assign) for assign in assignations]
                
                # Réservations postes
                query_reservations = '''
                    SELECT btr.*, wc.nom as poste_nom, wc.departement as poste_departement
                    FROM bt_reservations_postes btr
                    LEFT JOIN work_centers wc ON btr.work_center_id = wc.id
                    WHERE btr.bt_id = ?
                    ORDER BY btr.date_reservation DESC
                '''
                reservations = self.execute_query(query_reservations, (formulaire_id,))
                formulaire['reservations_postes'] = [dict(res) for res in reservations]
            
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
            'EN COURS': '#2dd4bf',
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
            
            return f"{prefix}-{annee}-{sequence:04d}"
            
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
    
    # =========================================================================
    # MÉTHODES SPÉCIFIQUES AUX BONS DE TRAVAIL
    # =========================================================================
    
    def assign_employee_to_bt(self, bt_id: int, employe_id: int, notes: str = "") -> int:
        """Assigne un employé à un bon de travail"""
        try:
            query = '''
                INSERT INTO bt_assignations (bt_id, employe_id, notes_assignation)
                VALUES (?, ?, ?)
            '''
            assignation_id = self.execute_insert(query, (bt_id, employe_id, notes))
            
            # Enregistrer dans l'historique
            self._enregistrer_validation(bt_id, employe_id, 'ASSIGNATION', f"Employé assigné au BT - {notes}")
            
            return assignation_id
            
        except Exception as e:
            logger.error(f"Erreur assignation employé BT: {e}")
            return None
    
    def reserve_work_center_for_bt(self, bt_id: int, work_center_id: int, date_prevue: str, notes: str = "") -> int:
        """Réserve un poste de travail pour un bon de travail"""
        try:
            query = '''
                INSERT INTO bt_reservations_postes (bt_id, work_center_id, date_prevue, notes_reservation)
                VALUES (?, ?, ?, ?)
            '''
            reservation_id = self.execute_insert(query, (bt_id, work_center_id, date_prevue, notes))
            
            # Enregistrer dans l'historique
            self._enregistrer_validation(bt_id, None, 'RESERVATION_POSTE', f"Poste réservé pour le {date_prevue} - {notes}")
            
            return reservation_id
            
        except Exception as e:
            logger.error(f"Erreur réservation poste BT: {e}")
            return None
    
    def liberate_work_center_from_bt(self, reservation_id: int) -> bool:
        """Libère un poste de travail d'un bon de travail"""
        try:
            query = '''
                UPDATE bt_reservations_postes 
                SET statut = 'LIBÉRÉ', date_liberation = CURRENT_TIMESTAMP
                WHERE id = ?
            '''
            affected = self.execute_update(query, (reservation_id,))
            return affected > 0
            
        except Exception as e:
            logger.error(f"Erreur libération poste BT: {e}")
            return False
    
    def get_bt_with_assignments(self, bt_id: int) -> Dict:
        """Récupère un BT avec toutes ses assignations et réservations"""
        try:
            query = '''
                SELECT * FROM view_bons_travail_complets
                WHERE id = ?
            '''
            result = self.execute_query(query, (bt_id,))
            return dict(result[0]) if result else {}
            
        except Exception as e:
            logger.error(f"Erreur récupération BT avec assignations: {e}")
            return {}
    
    def get_work_center_reservations(self, work_center_id: int, date_debut: str = None, date_fin: str = None) -> List[Dict]:
        """Récupère les réservations d'un poste de travail"""
        try:
            query = '''
                SELECT btr.*, f.numero_document, f.statut as bt_statut, p.nom_projet
                FROM bt_reservations_postes btr
                LEFT JOIN formulaires f ON btr.bt_id = f.id
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE btr.work_center_id = ? AND btr.statut = 'RÉSERVÉ'
            '''
            params = [work_center_id]
            
            if date_debut:
                query += " AND btr.date_prevue >= ?"
                params.append(date_debut)
            
            if date_fin:
                query += " AND btr.date_prevue <= ?"
                params.append(date_fin)
            
            query += " ORDER BY btr.date_prevue"
            
            rows = self.execute_query(query, tuple(params))
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur récupération réservations poste: {e}")
            return []
    
    def get_employee_bt_assignments(self, employe_id: int) -> List[Dict]:
        """Récupère les assignations BT d'un employé"""
        try:
            query = '''
                SELECT bta.*, f.numero_document, f.statut as bt_statut, f.priorite, p.nom_projet
                FROM bt_assignations bta
                LEFT JOIN formulaires f ON bta.bt_id = f.id
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE bta.employe_id = ? AND bta.statut = 'ASSIGNÉ'
                ORDER BY f.priorite DESC, bta.date_assignation DESC
            '''
            rows = self.execute_query(query, (employe_id,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur récupération assignations employé: {e}")
            return []
    
    # =========================================================================
    # MÉTHODES SPÉCIFIQUES AUX BONS D'ACHATS
    # =========================================================================
    
    def get_companies_by_type(self, company_type: str = None) -> List[Dict]:
        """Récupère les entreprises par type (CLIENT, FOURNISSEUR, etc.)"""
        try:
            if company_type:
                # Recherche par secteur, type_company ou notes
                query = """
                    SELECT * FROM companies 
                    WHERE UPPER(secteur) LIKE UPPER(?) 
                       OR UPPER(type_company) LIKE UPPER(?)
                       OR UPPER(notes) LIKE UPPER(?)
                    ORDER BY nom
                """
                pattern = f"%{company_type}%"
                rows = self.execute_query(query, (pattern, pattern, pattern))
            else:
                rows = self.execute_query("SELECT * FROM companies ORDER BY nom")
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération companies: {e}")
            return []
    
    def get_fournisseurs_with_stats(self) -> List[Dict]:
        """Récupère les fournisseurs avec leurs statistiques"""
        try:
            query = "SELECT * FROM view_fournisseurs_stats ORDER BY nombre_commandes DESC, nom"
            rows = self.execute_query(query)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération fournisseurs: {e}")
            return []
    
    def add_fournisseur(self, company_id: int, fournisseur_data: Dict) -> int:
        """Ajoute un fournisseur basé sur une entreprise existante"""
        try:
            query = '''
                INSERT INTO fournisseurs 
                (company_id, code_fournisseur, categorie_produits, delai_livraison_moyen,
                 conditions_paiement, evaluation_qualite, contact_commercial, contact_technique,
                 certifications, notes_evaluation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            fournisseur_id = self.execute_insert(query, (
                company_id,
                fournisseur_data.get('code_fournisseur'),
                fournisseur_data.get('categorie_produits'),
                fournisseur_data.get('delai_livraison_moyen', 14),
                fournisseur_data.get('conditions_paiement', '30 jours net'),
                fournisseur_data.get('evaluation_qualite', 5),
                fournisseur_data.get('contact_commercial'),
                fournisseur_data.get('contact_technique'),
                fournisseur_data.get('certifications'),
                fournisseur_data.get('notes_evaluation')
            ))
            
            # Mettre à jour le type de l'entreprise
            self.execute_update(
                "UPDATE companies SET type_company = 'FOURNISSEUR' WHERE id = ?",
                (company_id,)
            )
            
            return fournisseur_id
            
        except Exception as e:
            logger.error(f"Erreur ajout fournisseur: {e}")
            return None
    
    def update_inventory_status_all(self):
        """Met à jour automatiquement le statut de tous les articles d'inventaire"""
        try:
            query = """
                UPDATE inventory_items 
                SET statut = CASE
                    WHEN quantite_metric <= 0.001 THEN 'ÉPUISÉ'
                    WHEN quantite_metric <= limite_minimale_metric THEN 'CRITIQUE'
                    WHEN quantite_metric <= (limite_minimale_metric * 1.5) THEN 'FAIBLE'
                    ELSE 'DISPONIBLE'
                END,
                updated_at = CURRENT_TIMESTAMP
                WHERE limite_minimale_metric > 0
            """
            
            affected = self.execute_update(query)
            logger.info(f"Statuts inventaire mis à jour: {affected} articles")
            return affected
            
        except Exception as e:
            logger.error(f"Erreur mise à jour statuts inventaire: {e}")
            return 0
    
    def get_stocks_critiques(self) -> List[Dict]:
        """Retourne les articles avec stock critique"""
        try:
            query = "SELECT * FROM view_stocks_critiques WHERE statut_calcule IN ('ÉPUISÉ', 'CRITIQUE', 'FAIBLE')"
            rows = self.execute_query(query)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération stocks critiques: {e}")
            return []
    
    def create_approvisionnement(self, formulaire_id: int, fournisseur_id: int, data: Dict) -> int:
        """Crée un enregistrement d'approvisionnement"""
        try:
            query = '''
                INSERT INTO approvisionnements
                (formulaire_id, fournisseur_id, statut_livraison, date_commande,
                 date_livraison_prevue, quantite_commandee, notes_livraison)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            '''
            
            appro_id = self.execute_insert(query, (
                formulaire_id,
                fournisseur_id,
                data.get('statut_livraison', 'EN_ATTENTE'),
                data.get('date_commande'),
                data.get('date_livraison_prevue'),
                data.get('quantite_commandee', 0),
                data.get('notes_livraison')
            ))
            
            return appro_id
            
        except Exception as e:
            logger.error(f"Erreur création approvisionnement: {e}")
            return None
    
    def update_approvisionnement_status(self, appro_id: int, nouveau_statut: str, notes: str = ""):
        """Met à jour le statut d'un approvisionnement"""
        try:
            query = '''
                UPDATE approvisionnements 
                SET statut_livraison = ?, notes_livraison = ?, 
                    date_livraison_reelle = CASE WHEN ? = 'LIVRÉ' THEN CURRENT_DATE ELSE date_livraison_reelle END
                WHERE id = ?
            '''
            
            affected = self.execute_update(query, (nouveau_statut, notes, nouveau_statut, appro_id))
            return affected > 0
            
        except Exception as e:
            logger.error(f"Erreur mise à jour approvisionnement: {e}")
            return False
    
    # =========================================================================
    # MÉTHODES D'ANALYSE ET REPORTING
    # =========================================================================
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques principales pour le dashboard"""
        try:
            metrics = {
                'projects': {'total': 0, 'actifs': 0, 'ca_total': 0.0},
                'formulaires': {'total': 0, 'en_attente': 0, 'montant_total': 0.0},
                'inventory': {'total_items': 0, 'stocks_critiques': 0},
                'fournisseurs': {'total': 0, 'actifs': 0},
                'employees': {'total': 0, 'actifs': 0},
                'bt_specialise': {'total': 0, 'assignations': 0, 'postes_reserves': 0}
            }
            
            # Métriques projets
            result = self.execute_query("SELECT COUNT(*) as total, SUM(prix_estime) as ca FROM projects")
            if result:
                metrics['projects']['total'] = result[0]['total']
                metrics['projects']['ca_total'] = result[0]['ca'] or 0.0
            
            result = self.execute_query("SELECT COUNT(*) as actifs FROM projects WHERE statut NOT IN ('TERMINÉ', 'ANNULÉ')")
            if result:
                metrics['projects']['actifs'] = result[0]['actifs']
            
            # Métriques formulaires
            result = self.execute_query("SELECT COUNT(*) as total, SUM(montant_total) as montant FROM formulaires")
            if result:
                metrics['formulaires']['total'] = result[0]['total']
                metrics['formulaires']['montant_total'] = result[0]['montant'] or 0.0
            
            result = self.execute_query("SELECT COUNT(*) as en_attente FROM formulaires WHERE statut IN ('BROUILLON', 'VALIDÉ')")
            if result:
                metrics['formulaires']['en_attente'] = result[0]['en_attente']
            
            # Métriques inventaire
            result = self.execute_query("SELECT COUNT(*) as total FROM inventory_items")
            if result:
                metrics['inventory']['total_items'] = result[0]['total']
            
            result = self.execute_query("SELECT COUNT(*) as critiques FROM inventory_items WHERE statut IN ('CRITIQUE', 'FAIBLE', 'ÉPUISÉ')")
            if result:
                metrics['inventory']['stocks_critiques'] = result[0]['critiques']
            
            # Métriques fournisseurs
            result = self.execute_query("SELECT COUNT(*) as total FROM companies WHERE type_company = 'FOURNISSEUR'")
            if result:
                metrics['fournisseurs']['total'] = result[0]['total']
            
            result = self.execute_query("SELECT COUNT(*) as actifs FROM fournisseurs WHERE est_actif = TRUE")
            if result:
                metrics['fournisseurs']['actifs'] = result[0]['actifs']
            
            # Métriques employés
            result = self.execute_query("SELECT COUNT(*) as total FROM employees")
            if result:
                metrics['employees']['total'] = result[0]['total']
            
            result = self.execute_query("SELECT COUNT(*) as actifs FROM employees WHERE statut = 'ACTIF'")
            if result:
                metrics['employees']['actifs'] = result[0]['actifs']
            
            # Métriques BT spécialisées
            result = self.execute_query("SELECT COUNT(*) as total FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL'")
            if result:
                metrics['bt_specialise']['total'] = result[0]['total']
            
            result = self.execute_query("SELECT COUNT(*) as assignations FROM bt_assignations")
            if result:
                metrics['bt_specialise']['assignations'] = result[0]['assignations']
            
            result = self.execute_query("SELECT COUNT(*) as reservations FROM bt_reservations_postes WHERE statut = 'RÉSERVÉ'")
            if result:
                metrics['bt_specialise']['postes_reserves'] = result[0]['reservations']
            
            return metrics
            
        except Exception as e:
            logger.error(f"Erreur métriques dashboard: {e}")
            return {}
    
    def generate_monthly_report(self, year: int, month: int) -> Dict[str, Any]:
        """Génère un rapport mensuel complet"""
        try:
            report = {
                'periode': f"{year}-{month:02d}",
                'formulaires_crees': 0,
                'montant_commandes': 0.0,
                'projets_livres': 0,
                'stocks_mouvements': 0,
                'performances_fournisseurs': [],
                'bt_performance': {'total_bt': 0, 'assignations_mois': 0, 'completion_rate': 0.0},
                'alertes': []
            }
            
            # Formulaires créés dans le mois
            query = '''
                SELECT COUNT(*) as count, SUM(montant_total) as montant
                FROM formulaires 
                WHERE strftime('%Y-%m', date_creation) = ?
            '''
            result = self.execute_query(query, (f"{year}-{month:02d}",))
            if result:
                report['formulaires_crees'] = result[0]['count']
                report['montant_commandes'] = result[0]['montant'] or 0.0
            
            # Projets livrés
            query = '''
                SELECT COUNT(*) as livres
                FROM projects 
                WHERE statut = 'TERMINÉ' 
                AND strftime('%Y-%m', updated_at) = ?
            '''
            result = self.execute_query(query, (f"{year}-{month:02d}",))
            if result:
                report['projets_livres'] = result[0]['livres']
            
            # Mouvements d'inventaire
            query = '''
                SELECT COUNT(*) as mouvements
                FROM inventory_history 
                WHERE strftime('%Y-%m', created_at) = ?
            '''
            result = self.execute_query(query, (f"{year}-{month:02d}",))
            if result:
                report['stocks_mouvements'] = result[0]['mouvements']
            
            # Performances fournisseurs (basique)
            query = '''
                SELECT c.nom, COUNT(f.id) as commandes, SUM(f.montant_total) as montant
                FROM formulaires f
                JOIN companies c ON f.company_id = c.id
                WHERE f.type_formulaire IN ('BON_ACHAT', 'BON_COMMANDE')
                AND strftime('%Y-%m', f.date_creation) = ?
                GROUP BY c.id, c.nom
                ORDER BY montant DESC
                LIMIT 10
            '''
            rows = self.execute_query(query, (f"{year}-{month:02d}",))
            report['performances_fournisseurs'] = [dict(row) for row in rows]
            
            # Performance BT mensuelle
            query = '''
                SELECT COUNT(*) as total_bt
                FROM formulaires 
                WHERE type_formulaire = 'BON_TRAVAIL'
                AND strftime('%Y-%m', date_creation) = ?
            '''
            result = self.execute_query(query, (f"{year}-{month:02d}",))
            if result:
                report['bt_performance']['total_bt'] = result[0]['total_bt']
            
            query = '''
                SELECT COUNT(*) as assignations
                FROM bt_assignations 
                WHERE strftime('%Y-%m', date_assignation) = ?
            '''
            result = self.execute_query(query, (f"{year}-{month:02d}",))
            if result:
                report['bt_performance']['assignations_mois'] = result[0]['assignations']
            
            # Calcul taux de completion BT
            if report['bt_performance']['total_bt'] > 0:
                query = '''
                    SELECT COUNT(*) as termines
                    FROM formulaires 
                    WHERE type_formulaire = 'BON_TRAVAIL'
                    AND statut = 'TERMINÉ'
                    AND strftime('%Y-%m', date_creation) = ?
                '''
                result = self.execute_query(query, (f"{year}-{month:02d}",))
                if result:
                    termines = result[0]['termines']
                    report['bt_performance']['completion_rate'] = (termines / report['bt_performance']['total_bt']) * 100
            
            return report
            
        except Exception as e:
            logger.error(f"Erreur génération rapport mensuel: {e}")
            return {}

    # =========================================================================
    # MÉTHODES D'INTÉGRATION BT ↔ TIMETRACKER (Extensions)
    # =========================================================================

    def get_bt_assignes_employe(self, employee_id: int) -> List[Dict]:
        """
        Récupère tous les BT assignés à un employé avec détails complets
        INTÉGRATION : TimeTracker → Bons de Travail
        
        Args:
            employee_id: ID de l'employé
            
        Returns:
            List[Dict]: Liste des BT assignés avec statuts et opérations
        """
        try:
            query = """
                SELECT 
                    f.id as bt_id,
                    f.numero_document,
                    f.statut as bt_statut,
                    f.priorite,
                    f.date_echeance,
                    p.nom_projet,
                    p.client_nom_cache as client_nom,
                    bta.role_bt,
                    bta.date_assignation,
                    bta.statut as assignation_statut,
                    
                    -- Avancement du BT
                    COALESCE(AVG(btav.pourcentage_realise), 0) as avancement_moyen,
                    COUNT(DISTINCT btav.operation_id) as operations_totales,
                    COUNT(CASE WHEN btav.pourcentage_realise >= 100 THEN 1 END) as operations_terminees,
                    
                    -- Temps TimeTracker sur ce BT
                    COALESCE(SUM(te.total_hours), 0) as temps_timetracker_total,
                    COALESCE(SUM(te.total_cost), 0) as cout_timetracker_total,
                    COUNT(te.id) as pointages_timetracker,
                    
                    -- Dernière activité
                    MAX(te.punch_in) as dernier_pointage
                    
                FROM bt_assignations bta
                JOIN formulaires f ON bta.bt_id = f.id
                LEFT JOIN projects p ON f.project_id = p.id
                LEFT JOIN bt_avancement btav ON f.id = btav.bt_id
                LEFT JOIN time_entries te ON f.project_id = te.project_id AND te.employee_id = bta.employe_id
                
                WHERE bta.employe_id = ? 
                AND bta.statut = 'ASSIGNÉ'
                AND f.statut NOT IN ('TERMINÉ', 'ANNULÉ')
                
                GROUP BY f.id, bta.id
                ORDER BY f.priorite DESC, f.date_echeance ASC
            """
            
            rows = self.execute_query(query, (employee_id,))
            
            bt_assignes = []
            for row in rows:
                bt = dict(row)
                
                # Enrichir avec opérations disponibles pour pointage
                bt['operations_pointage'] = self._get_operations_bt_pour_pointage(bt['bt_id'])
                
                # Calculer priorité numérique pour le tri
                bt['priorite_numeric'] = {'CRITIQUE': 3, 'URGENT': 2, 'NORMAL': 1}.get(bt['priorite'], 1)
                
                # Statut d'urgence basé sur échéance
                if bt['date_echeance']:
                    try:
                        echeance = datetime.strptime(bt['date_echeance'], '%Y-%m-%d')
                        jours_restants = (echeance.date() - datetime.now().date()).days
                        bt['jours_restants'] = jours_restants
                        bt['urgence_echeance'] = 'CRITIQUE' if jours_restants <= 1 else 'URGENT' if jours_restants <= 3 else 'NORMAL'
                    except:
                        bt['jours_restants'] = 999
                        bt['urgence_echeance'] = 'NORMAL'
                
                bt_assignes.append(bt)
            
            logging.info(f"✅ {len(bt_assignes)} BT assigné(s) trouvé(s) pour employé {employee_id}")
            return bt_assignes
            
        except Exception as e:
            logging.error(f"❌ Erreur récupération BT assignés employé {employee_id}: {e}")
            return []

    def _get_operations_bt_pour_pointage(self, bt_id: int) -> List[Dict]:
        """
        Récupère les opérations d'un BT formatées pour TimeTracker
        
        Args:
            bt_id: ID du BT
            
        Returns:
            List[Dict]: Opérations avec détails pour pointage
        """
        try:
            # Récupérer le projet du BT
            query_projet = """
                SELECT project_id FROM formulaires WHERE id = ?
            """
            result_projet = self.execute_query(query_projet, (bt_id,))
            
            if not result_projet or not result_projet[0]['project_id']:
                return []
            
            project_id = result_projet[0]['project_id']
            
            # Récupérer les opérations du projet avec état TimeTracker
            query = """
                SELECT 
                    o.id as operation_id,
                    o.sequence_number,
                    o.description,
                    o.temps_estime,
                    o.statut as operation_statut,
                    wc.nom as work_center_name,
                    wc.cout_horaire,
                    
                    -- État TimeTracker de cette opération
                    COALESCE(SUM(te.total_hours), 0) as temps_reel_timetracker,
                    COALESCE(SUM(te.total_cost), 0) as cout_reel_timetracker,
                    COUNT(te.id) as nb_pointages,
                    MAX(te.punch_out) as dernier_pointage,
                    
                    -- État avancement BT
                    btav.pourcentage_realise,
                    btav.temps_reel as temps_reel_bt,
                    btav.notes_avancement
                    
                FROM operations o
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                LEFT JOIN time_entries te ON o.id = te.operation_id
                LEFT JOIN bt_avancement btav ON o.id = btav.operation_id AND btav.bt_id = ?
                
                WHERE o.project_id = ?
                
                GROUP BY o.id
                ORDER BY o.sequence_number
            """
            
            rows = self.execute_query(query, (bt_id, project_id))
            
            operations = []
            for row in rows:
                op = dict(row)
                
                # Calculer progression
                if op['temps_estime'] and op['temps_estime'] > 0:
                    progression_temps = (op['temps_reel_timetracker'] / op['temps_estime']) * 100
                else:
                    progression_temps = 0
                
                op['progression_temps'] = min(100, progression_temps)
                op['peut_pointer'] = op['operation_statut'] not in ['TERMINÉ', 'ANNULÉ']
                op['description_pointage'] = f"OP{op['sequence_number']:02d} - {op['description']}"
                
                operations.append(op)
            
            return operations
            
        except Exception as e:
            logging.error(f"❌ Erreur opérations BT pour pointage {bt_id}: {e}")
            return []

    def synchroniser_avancement_bt_depuis_timetracker(self, bt_id: int) -> bool:
        """
        Synchronise l'avancement d'un BT basé sur les données TimeTracker
        INTÉGRATION : TimeTracker → Bons de Travail
        
        Args:
            bt_id: ID du BT à synchroniser
            
        Returns:
            bool: True si synchronisation réussie
        """
        try:
            # Récupérer le projet du BT
            query_projet = """
                SELECT project_id FROM formulaires WHERE id = ?
            """
            result_projet = self.execute_query(query_projet, (bt_id,))
            
            if not result_projet or not result_projet[0]['project_id']:
                return False
            
            project_id = result_projet[0]['project_id']
            
            # Synchroniser chaque opération
            query_operations = """
                SELECT 
                    o.id as operation_id,
                    o.temps_estime,
                    COALESCE(SUM(te.total_hours), 0) as temps_reel_timetracker,
                    COUNT(te.id) as nb_pointages
                FROM operations o
                LEFT JOIN time_entries te ON o.id = te.operation_id
                WHERE o.project_id = ?
                GROUP BY o.id
            """
            
            operations = self.execute_query(query_operations, (project_id,))
            operations_synchronisees = 0
            
            for op in operations:
                operation_id = op['operation_id']
                temps_reel = op['temps_reel_timetracker']
                temps_estime = op['temps_estime'] or 1  # Éviter division par zéro
                
                # Calculer pourcentage basé sur TimeTracker
                pourcentage = min(100, (temps_reel / temps_estime) * 100)
                
                # Mettre à jour ou créer l'avancement
                query_check = """
                    SELECT id FROM bt_avancement 
                    WHERE bt_id = ? AND operation_id = ?
                """
                existing = self.execute_query(query_check, (bt_id, operation_id))
                
                if existing:
                    # Mise à jour
                    query_update = """
                        UPDATE bt_avancement 
                        SET pourcentage_realise = ?, 
                            temps_reel = ?,
                            notes_avancement = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE bt_id = ? AND operation_id = ?
                    """
                    notes = f"Sync TimeTracker: {temps_reel:.2f}h sur {temps_estime:.2f}h estimé ({op['nb_pointages']} pointages)"
                    self.execute_update(query_update, (pourcentage, temps_reel, notes, bt_id, operation_id))
                else:
                    # Création
                    query_insert = """
                        INSERT INTO bt_avancement 
                        (bt_id, operation_id, pourcentage_realise, temps_reel, notes_avancement)
                        VALUES (?, ?, ?, ?, ?)
                    """
                    notes = f"Sync TimeTracker: {temps_reel:.2f}h ({op['nb_pointages']} pointages)"
                    self.execute_insert(query_insert, (bt_id, operation_id, pourcentage, temps_reel, notes))
                
                operations_synchronisees += 1
            
            logging.info(f"✅ Synchronisation BT {bt_id}: {operations_synchronisees} opération(s) mises à jour")
            return True
            
        except Exception as e:
            logging.error(f"❌ Erreur synchronisation BT {bt_id}: {e}")
            return False

    def demarrer_pointage_depuis_bt(self, employee_id: int, bt_id: int, operation_id: int, 
                                   notes: str = "") -> Optional[int]:
        """
        Démarre un pointage TimeTracker directement depuis un BT
        INTÉGRATION : Bons de Travail → TimeTracker
        
        Args:
            employee_id: ID de l'employé
            bt_id: ID du BT
            operation_id: ID de l'opération
            notes: Notes de démarrage
            
        Returns:
            Optional[int]: ID du time_entry créé ou None si erreur
        """
        try:
            # Vérifier que l'employé est assigné au BT
            query_check = """
                SELECT COUNT(*) as count FROM bt_assignations 
                WHERE bt_id = ? AND employe_id = ? AND statut = 'ASSIGNÉ'
            """
            result = self.execute_query(query_check, (bt_id, employee_id))
            
            if not result or result[0]['count'] == 0:
                raise ValueError("Employé non assigné à ce BT")
            
            # Vérifier qu'il n'y a pas déjà un pointage actif
            query_active = """
                SELECT COUNT(*) as count FROM time_entries 
                WHERE employee_id = ? AND punch_out IS NULL
            """
            result_active = self.execute_query(query_active, (employee_id,))
            
            if result_active and result_active[0]['count'] > 0:
                raise ValueError("Pointage déjà actif pour cet employé")
            
            # Récupérer les informations du BT et de l'opération
            query_info = """
                SELECT 
                    f.project_id,
                    f.numero_document as bt_numero,
                    o.description as operation_desc,
                    wc.cout_horaire
                FROM formulaires f
                JOIN operations o ON o.id = ?
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE f.id = ?
            """
            info_result = self.execute_query(query_info, (operation_id, bt_id))
            
            if not info_result:
                raise ValueError("BT ou opération non trouvé")
            
            info = info_result[0]
            project_id = info['project_id']
            hourly_rate = info['cout_horaire'] or 95.0  # Taux par défaut
            
            # Créer le pointage avec note enrichie
            notes_enrichies = f"BT {info['bt_numero']} - {info['operation_desc']} | {notes}".strip(' |')
            
            query_insert = """
                INSERT INTO time_entries 
                (employee_id, project_id, operation_id, punch_in, notes, hourly_rate)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            
            time_entry_id = self.execute_insert(query_insert, (
                employee_id, project_id, operation_id, 
                datetime.now().isoformat(), notes_enrichies, hourly_rate
            ))
            
            logging.info(f"✅ Pointage démarré depuis BT {bt_id}: time_entry {time_entry_id}")
            return time_entry_id
            
        except Exception as e:
            logging.error(f"❌ Erreur démarrage pointage depuis BT {bt_id}: {e}")
            return None

    def get_temps_reel_bt_operations(self, bt_id: int) -> Dict[str, Any]:
        """
        Récupère les temps réels TimeTracker pour toutes les opérations d'un BT
        INTÉGRATION : TimeTracker → Bons de Travail
        
        Args:
            bt_id: ID du BT
            
        Returns:
            Dict: Temps réels et statistiques par opération
        """
        try:
            # Récupérer le projet du BT
            query_projet = """
                SELECT project_id, numero_document FROM formulaires WHERE id = ?
            """
            result_projet = self.execute_query(query_projet, (bt_id,))
            
            if not result_projet or not result_projet[0]['project_id']:
                return {}
            
            project_id = result_projet[0]['project_id']
            bt_numero = result_projet[0]['numero_document']
            
            # Récupérer les temps par opération avec détails TimeTracker
            query = """
                SELECT 
                    o.id as operation_id,
                    o.sequence_number,
                    o.description,
                    o.temps_estime,
                    
                    -- Données TimeTracker
                    COALESCE(SUM(te.total_hours), 0) as temps_reel,
                    COALESCE(SUM(te.total_cost), 0) as cout_reel,
                    COALESCE(AVG(te.hourly_rate), 0) as taux_moyen,
                    COUNT(te.id) as nb_pointages,
                    COUNT(DISTINCT te.employee_id) as nb_employes,
                    
                    -- Dernière activité
                    MAX(te.punch_in) as dernier_debut,
                    MAX(te.punch_out) as derniere_fin,
                    
                    -- Pointage en cours
                    COUNT(CASE WHEN te.punch_out IS NULL THEN 1 END) as pointages_actifs
                    
                FROM operations o
                LEFT JOIN time_entries te ON o.id = te.operation_id
                WHERE o.project_id = ?
                GROUP BY o.id
                ORDER BY o.sequence_number
            """
            
            rows = self.execute_query(query, (project_id,))
            
            operations_temps = []
            temps_total_reel = 0
            temps_total_estime = 0
            cout_total = 0
            pointages_totaux = 0
            
            for row in rows:
                op = dict(row)
                
                # Calculs de progression
                if op['temps_estime'] and op['temps_estime'] > 0:
                    progression = (op['temps_reel'] / op['temps_estime']) * 100
                    variance = op['temps_reel'] - op['temps_estime']
                    variance_pct = (variance / op['temps_estime']) * 100
                else:
                    progression = 0 if op['temps_reel'] == 0 else 100
                    variance = op['temps_reel']
                    variance_pct = 0
                
                op['progression'] = min(100, progression)
                op['variance_heures'] = variance
                op['variance_pourcentage'] = variance_pct
                op['statut_progression'] = (
                    'DÉPASSÉ' if progression > 110 else
                    'EN RETARD' if progression > 100 else
                    'TERMINÉ' if progression >= 100 else
                    'EN COURS' if op['pointages_actifs'] > 0 else
                    'NON DÉMARRÉ'
                )
                
                # Efficacité
                if op['temps_estime'] and op['temps_reel'] > 0:
                    efficacite = (op['temps_estime'] / op['temps_reel']) * 100
                    op['efficacite'] = min(200, efficacite)  # Cap à 200%
                else:
                    op['efficacite'] = 0
                
                operations_temps.append(op)
                
                # Totaux
                temps_total_reel += op['temps_reel']
                temps_total_estime += op['temps_estime'] or 0
                cout_total += op['cout_reel']
                pointages_totaux += op['nb_pointages']
            
            # Synthèse globale
            progression_globale = (temps_total_reel / temps_total_estime * 100) if temps_total_estime > 0 else 0
            efficacite_globale = (temps_total_estime / temps_total_reel * 100) if temps_total_reel > 0 else 0
            
            synthese = {
                'bt_id': bt_id,
                'bt_numero': bt_numero,
                'operations': operations_temps,
                'synthese': {
                    'temps_total_estime': temps_total_estime,
                    'temps_total_reel': temps_total_reel,
                    'cout_total': cout_total,
                    'progression_globale': min(100, progression_globale),
                    'efficacite_globale': min(200, efficacite_globale),
                    'variance_globale': temps_total_reel - temps_total_estime,
                    'pointages_totaux': pointages_totaux,
                    'nb_operations': len(operations_temps),
                    'operations_terminees': len([op for op in operations_temps if op['progression'] >= 100]),
                    'operations_en_cours': len([op for op in operations_temps if op['pointages_actifs'] > 0])
                }
            }
            
            logging.info(f"✅ Temps réels récupérés pour BT {bt_id}: {len(operations_temps)} opérations")
            return synthese
            
        except Exception as e:
            logging.error(f"❌ Erreur temps réels BT {bt_id}: {e}")
            return {}

    def get_dashboard_integration_bt_timetracker(self) -> Dict[str, Any]:
        """
        Dashboard unifié BT/TimeTracker avec métriques croisées
        INTÉGRATION : Vue d'ensemble unifiée
        
        Returns:
            Dict: Métriques et données du dashboard intégré
        """
        try:
            dashboard = {
                'timestamp': datetime.now().isoformat(),
                'bt_metrics': {},
                'timetracker_metrics': {},
                'integration_metrics': {},
                'alertes': [],
                'top_performers': [],
                'projets_actifs': []
            }
            
            # === MÉTRIQUES BT ===
            query_bt = """
                SELECT 
                    COUNT(*) as total_bt,
                    COUNT(CASE WHEN statut = 'EN COURS' THEN 1 END) as bt_en_cours,
                    COUNT(CASE WHEN statut = 'TERMINÉ' THEN 1 END) as bt_termines,
                    COUNT(CASE WHEN priorite = 'CRITIQUE' THEN 1 END) as bt_critiques,
                    COUNT(CASE WHEN date_echeance < DATE('now') AND statut NOT IN ('TERMINÉ', 'ANNULÉ') THEN 1 END) as bt_retard,
                    COALESCE(SUM(montant_total), 0) as montant_total_bt
                FROM formulaires 
                WHERE type_formulaire = 'BON_TRAVAIL'
            """
            result_bt = self.execute_query(query_bt)
            dashboard['bt_metrics'] = dict(result_bt[0]) if result_bt else {}
            
            # === MÉTRIQUES TIMETRACKER ===
            today = datetime.now().strftime('%Y-%m-%d')
            query_tt = """
                SELECT 
                    COUNT(*) as total_pointages_jour,
                    COUNT(CASE WHEN punch_out IS NULL THEN 1 END) as pointages_actifs,
                    COALESCE(SUM(total_hours), 0) as heures_jour,
                    COALESCE(SUM(total_cost), 0) as revenus_jour,
                    COUNT(DISTINCT employee_id) as employes_actifs_jour
                FROM time_entries 
                WHERE DATE(punch_in) = ?
            """
            result_tt = self.execute_query(query_tt, (today,))
            dashboard['timetracker_metrics'] = dict(result_tt[0]) if result_tt else {}
            
            # === MÉTRIQUES D'INTÉGRATION ===
            query_integration = """
                SELECT 
                    COUNT(DISTINCT f.id) as bt_avec_pointages,
                    COUNT(DISTINCT te.employee_id) as employes_bt_timetracker,
                    COUNT(DISTINCT te.operation_id) as operations_pointees,
                    COALESCE(SUM(te.total_hours), 0) as heures_bt_total,
                    COALESCE(SUM(te.total_cost), 0) as revenus_bt_total
                FROM formulaires f
                JOIN time_entries te ON f.project_id = te.project_id
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                AND te.total_cost IS NOT NULL
            """
            result_integration = self.execute_query(query_integration)
            dashboard['integration_metrics'] = dict(result_integration[0]) if result_integration else {}
            
            # === ALERTES ===
            # BT en retard
            if dashboard['bt_metrics'].get('bt_retard', 0) > 0:
                dashboard['alertes'].append({
                    'type': 'RETARD',
                    'niveau': 'CRITIQUE',
                    'message': f"{dashboard['bt_metrics']['bt_retard']} BT en retard d'échéance",
                    'action': 'Vérifier les BT en retard et réassigner si nécessaire'
                })
            
            # Pointages oubliés (actifs depuis plus de 12h)
            query_pointages_longs = """
                SELECT COUNT(*) as count FROM time_entries 
                WHERE punch_out IS NULL 
                AND punch_in < datetime('now', '-12 hours')
            """
            result_longs = self.execute_query(query_pointages_longs)
            pointages_longs = result_longs[0]['count'] if result_longs else 0
            
            if pointages_longs > 0:
                dashboard['alertes'].append({
                    'type': 'POINTAGE_LONG',
                    'niveau': 'ATTENTION',
                    'message': f"{pointages_longs} pointage(s) actif(s) depuis plus de 12h",
                    'action': 'Vérifier les pointages oubliés avec les employés'
                })
            
            # === TOP PERFORMERS (Employés BT + TimeTracker) ===
            query_performers = """
                SELECT 
                    e.prenom || ' ' || e.nom as nom_employe,
                    e.poste,
                    COUNT(DISTINCT bta.bt_id) as bt_assignes,
                    COUNT(DISTINCT te.id) as pointages_mois,
                    COALESCE(SUM(te.total_hours), 0) as heures_mois,
                    COALESCE(SUM(te.total_cost), 0) as revenus_mois
                FROM employees e
                LEFT JOIN bt_assignations bta ON e.id = bta.employe_id AND bta.statut = 'ASSIGNÉ'
                LEFT JOIN time_entries te ON e.id = te.employee_id 
                    AND DATE(te.punch_in) >= DATE('now', '-30 days')
                    AND te.total_cost IS NOT NULL
                WHERE e.statut = 'ACTIF'
                GROUP BY e.id
                HAVING (bt_assignes > 0 OR pointages_mois > 0)
                ORDER BY revenus_mois DESC, heures_mois DESC
                LIMIT 5
            """
            rows_performers = self.execute_query(query_performers)
            dashboard['top_performers'] = [dict(row) for row in rows_performers]
            
            # === PROJETS ACTIFS AVEC INTÉGRATION ===
            query_projets = """
                SELECT 
                    p.id as project_id,
                    p.nom_projet,
                    p.statut as project_statut,
                    COUNT(DISTINCT f.id) as bt_count,
                    COUNT(DISTINCT te.employee_id) as employes_timetracker,
                    COALESCE(SUM(te.total_hours), 0) as heures_timetracker,
                    COALESCE(SUM(te.total_cost), 0) as revenus_timetracker,
                    COALESCE(AVG(btav.pourcentage_realise), 0) as avancement_moyen
                FROM projects p
                LEFT JOIN formulaires f ON p.id = f.project_id AND f.type_formulaire = 'BON_TRAVAIL'
                LEFT JOIN time_entries te ON p.id = te.project_id AND te.total_cost IS NOT NULL
                LEFT JOIN bt_avancement btav ON f.id = btav.bt_id
                WHERE p.statut IN ('À FAIRE', 'EN COURS', 'EN ATTENTE')
                GROUP BY p.id
                HAVING (bt_count > 0 OR employes_timetracker > 0)
                ORDER BY revenus_timetracker DESC
                LIMIT 10
            """
            rows_projets = self.execute_query(query_projets)
            dashboard['projets_actifs'] = [dict(row) for row in rows_projets]
            
            logging.info("✅ Dashboard intégration BT/TimeTracker généré")
            return dashboard
            
        except Exception as e:
            logging.error(f"❌ Erreur dashboard intégration: {e}")
            return {}

    def get_rapport_productivite_integre(self, periode_jours: int = 30) -> Dict[str, Any]:
        """
        Rapport de productivité intégré BT/TimeTracker
        INTÉGRATION : Analyse complète de performance
        
        Args:
            periode_jours: Période d'analyse en jours
            
        Returns:
            Dict: Rapport de productivité intégré
        """
        try:
            date_debut = (datetime.now() - timedelta(days=periode_jours)).strftime('%Y-%m-%d')
            
            rapport = {
                'periode': f"{periode_jours} derniers jours",
                'date_debut': date_debut,
                'date_generation': datetime.now().isoformat(),
                'employes': [],
                'projets': [],
                'operations': [],
                'synthese': {},
                'recommandations': []
            }
            
            # === ANALYSE PAR EMPLOYÉ ===
            query_employes = """
                SELECT 
                    e.id as employee_id,
                    e.prenom || ' ' || e.nom as nom_employe,
                    e.poste,
                    e.departement,
                    
                    -- Métriques BT
                    COUNT(DISTINCT bta.bt_id) as bt_assignes,
                    COUNT(CASE WHEN f.statut = 'TERMINÉ' THEN 1 END) as bt_termines,
                    
                    -- Métriques TimeTracker
                    COUNT(DISTINCT te.id) as pointages_periode,
                    COALESCE(SUM(te.total_hours), 0) as heures_periode,
                    COALESCE(SUM(te.total_cost), 0) as revenus_periode,
                    COALESCE(AVG(te.hourly_rate), 0) as taux_moyen,
                    
                    -- Efficacité
                    COUNT(DISTINCT te.project_id) as projets_touches,
                    COUNT(DISTINCT DATE(te.punch_in)) as jours_actifs
                    
                FROM employees e
                LEFT JOIN bt_assignations bta ON e.id = bta.employe_id
                LEFT JOIN formulaires f ON bta.bt_id = f.id AND f.type_formulaire = 'BON_TRAVAIL'
                LEFT JOIN time_entries te ON e.id = te.employee_id 
                    AND DATE(te.punch_in) >= ? AND te.total_cost IS NOT NULL
                
                WHERE e.statut = 'ACTIF'
                GROUP BY e.id
                HAVING (bt_assignes > 0 OR pointages_periode > 0)
                ORDER BY revenus_periode DESC
            """
            
            rows_employes = self.execute_query(query_employes, (date_debut,))
            
            for row in rows_employes:
                emp = dict(row)
                
                # Calculs d'efficacité
                if emp['bt_assignes'] > 0:
                    emp['taux_completion_bt'] = (emp['bt_termines'] / emp['bt_assignes']) * 100
                else:
                    emp['taux_completion_bt'] = 0
                
                if emp['jours_actifs'] > 0:
                    emp['heures_par_jour'] = emp['heures_periode'] / emp['jours_actifs']
                    emp['revenus_par_jour'] = emp['revenus_periode'] / emp['jours_actifs']
                else:
                    emp['heures_par_jour'] = 0
                    emp['revenus_par_jour'] = 0
                
                # Score de performance combiné
                score_bt = emp['taux_completion_bt'] * 0.3
                score_temps = min(40, emp['heures_par_jour']) * 2.5  # Max 100 points pour 40h/jour
                score_revenus = min(1000, emp['revenus_par_jour']) * 0.1  # Max 100 points pour 1000$/jour
                
                emp['score_performance'] = (score_bt + score_temps + score_revenus) / 3
                
                rapport['employes'].append(emp)
            
            # === ANALYSE PAR PROJET ===
            query_projets = """
                SELECT 
                    p.id as project_id,
                    p.nom_projet,
                    p.statut as project_statut,
                    p.prix_estime,
                    
                    -- Métriques BT
                    COUNT(DISTINCT f.id) as bt_total,
                    COUNT(CASE WHEN f.statut = 'TERMINÉ' THEN 1 END) as bt_termines,
                    COALESCE(AVG(btav.pourcentage_realise), 0) as avancement_moyen,
                    
                    -- Métriques TimeTracker
                    COALESCE(SUM(te.total_hours), 0) as heures_timetracker,
                    COALESCE(SUM(te.total_cost), 0) as revenus_timetracker,
                    COUNT(DISTINCT te.employee_id) as employes_timetracker,
                    
                    -- Dates
                    MIN(f.date_creation) as premier_bt,
                    MAX(te.punch_out) as derniere_activite
                    
                FROM projects p
                LEFT JOIN formulaires f ON p.id = f.project_id AND f.type_formulaire = 'BON_TRAVAIL'
                LEFT JOIN bt_avancement btav ON f.id = btav.bt_id
                LEFT JOIN time_entries te ON p.id = te.project_id 
                    AND DATE(te.punch_in) >= ? AND te.total_cost IS NOT NULL
                
                WHERE p.statut IN ('À FAIRE', 'EN COURS', 'EN ATTENTE', 'TERMINÉ')
                GROUP BY p.id
                HAVING (bt_total > 0 OR employes_timetracker > 0)
                ORDER BY revenus_timetracker DESC
            """
            
            rows_projets = self.execute_query(query_projets, (date_debut,))
            
            for row in rows_projets:
                proj = dict(row)
                
                # Calculs de performance projet
                if proj['bt_total'] > 0:
                    proj['taux_completion_bt'] = (proj['bt_termines'] / proj['bt_total']) * 100
                else:
                    proj['taux_completion_bt'] = 0
                
                if proj['prix_estime'] and proj['prix_estime'] > 0:
                    proj['ratio_revenus_estime'] = (proj['revenus_timetracker'] / proj['prix_estime']) * 100
                else:
                    proj['ratio_revenus_estime'] = 0
                
                rapport['projets'].append(proj)
            
            # === SYNTHÈSE GLOBALE ===
            total_employes = len(rapport['employes'])
            total_heures = sum(emp['heures_periode'] for emp in rapport['employes'])
            total_revenus = sum(emp['revenus_periode'] for emp in rapport['employes'])
            total_bt = sum(emp['bt_assignes'] for emp in rapport['employes'])
            total_bt_termines = sum(emp['bt_termines'] for emp in rapport['employes'])
            
            rapport['synthese'] = {
                'employes_actifs': total_employes,
                'heures_totales': total_heures,
                'revenus_totaux': total_revenus,
                'bt_totaux': total_bt,
                'bt_termines': total_bt_termines,
                'taux_completion_global': (total_bt_termines / total_bt * 100) if total_bt > 0 else 0,
                'heures_par_employe': total_heures / total_employes if total_employes > 0 else 0,
                'revenus_par_employe': total_revenus / total_employes if total_employes > 0 else 0,
                'revenus_par_heure': total_revenus / total_heures if total_heures > 0 else 0
            }
            
            # === RECOMMANDATIONS ===
            recommandations = []
            
            # Employés avec faible taux de completion BT
            employes_faible_completion = [emp for emp in rapport['employes'] if emp['taux_completion_bt'] < 50 and emp['bt_assignes'] > 0]
            if employes_faible_completion:
                recommandations.append(f"🎯 {len(employes_faible_completion)} employé(s) ont un faible taux de completion BT (<50%) - Formation ou rééquilibrage nécessaire")
            
            # Projets avec beaucoup d'heures mais peu de BT terminés
            projets_inefficaces = [proj for proj in rapport['projets'] if proj['heures_timetracker'] > 50 and proj['taux_completion_bt'] < 30]
            if projets_inefficaces:
                recommandations.append(f"📊 {len(projets_inefficaces)} projet(s) accumulent beaucoup d'heures mais peu de BT terminés - Révision nécessaire")
            
            # Performance globale
            if rapport['synthese']['taux_completion_global'] < 60:
                recommandations.append("⚠️ Taux de completion BT global faible (<60%) - Réviser la planification et l'assignation")
            
            if rapport['synthese']['revenus_par_heure'] < 50:
                recommandations.append("💰 Revenus par heure faibles (<50$/h) - Optimiser les taux horaires ou l'efficacité")
            
            if not recommandations:
                recommandations.append("✅ Performance globale satisfaisante - Maintenir les bonnes pratiques")
            
            rapport['recommandations'] = recommandations
            
            logging.info(f"✅ Rapport productivité intégré généré: {total_employes} employés, {len(rapport['projets'])} projets")
            return rapport
            
        except Exception as e:
            logging.error(f"❌ Erreur rapport productivité intégré: {e}")
            return {}

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
```
--- END OF UPDATED FILE erp_database.py ---
