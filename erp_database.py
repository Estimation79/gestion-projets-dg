# erp_database.py - Gestionnaire Base de Données SQLite Unifié CONSOLIDÉ + INTERFACE UNIFIÉE + CORRECTION TABLE PROJECTS
# ERP Production DG Inc. - Migration JSON → SQLite + Module Formulaires Complet + Corrections Intégrées
# ÉTAPE 2 : Intégration TimeTracker ↔ Bons de Travail IMPLÉMENTÉE
# ÉTAPE 3 : Module Production Unifié COMPLET
# EXTENSION : Interface Unifiée TimeTracker + Postes de Travail COMPLÈTE
# NOUVEAU : Intégration Operations ↔ Bons de Travail INTÉGRÉE
# MISE À JOUR : Méthodes Communication TimeTracker Unifiées AJOUTÉES
# CORRECTION : Table Projects avec ID TEXT (compatible avec les anciens systèmes)

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

def force_recreate_projects_table_with_text_id(db_conn):
    """Solution de contournement robuste pour recréer la table projects avec ID TEXT."""
    try:
        cursor = db_conn.cursor()
        logger.info("🚨 SOLUTION FORCÉE : Vérification/Recréation de la table projects.")

        # Vérifier si la table 'projects' a le bon type de colonne 'id'
        try:
            cursor.execute("PRAGMA table_info(projects)")
            columns = cursor.fetchall()
            id_column = next((col for col in columns if col[1] == 'id'), None)
            if id_column and 'TEXT' in id_column[2].upper():
                logger.info("✅ La table 'projects' a déjà le bon format (ID TEXT). Aucune action requise.")
                return True
        except sqlite3.OperationalError:
            logger.warning("⚠️ La table 'projects' n'existe pas, elle va être créée.")
            # La table n'existe pas, on continue pour la créer.

        # 1. Sauvegarder les données existantes (depuis 'projects' ou 'projects_old')
        existing_projects = []
        source_table = None
        try:
            cursor.execute("SELECT * FROM projects")
            source_table = "projects"
            projects_data = cursor.fetchall()
            if projects_data:
                existing_projects = [dict(row) for row in projects_data]
        except sqlite3.OperationalError:
            try:
                cursor.execute("SELECT * FROM projects_old")
                source_table = "projects_old"
                projects_data = cursor.fetchall()
                if projects_data:
                    existing_projects = [dict(row) for row in projects_data]
            except sqlite3.OperationalError:
                logger.info("ℹ️ Aucune table 'projects' ou 'projects_old' trouvée pour la sauvegarde.")

        if existing_projects:
            logger.info(f"💾 Sauvegarde de {len(existing_projects)} projets depuis '{source_table}'.")

        # 2. Supprimer l'ancienne table 'projects' et la table de backup 'projects_old'
        cursor.execute("DROP TABLE IF EXISTS projects")
        cursor.execute("DROP TABLE IF EXISTS projects_old")
        logger.info("🗑️ Anciennes tables 'projects' et 'projects_old' supprimées.")

        # 3. Créer la nouvelle table avec la bonne structure (ID TEXT)
        logger.info("🏗️ Création de la nouvelle table 'projects'...")
        cursor.execute("""
            CREATE TABLE projects (
                id TEXT PRIMARY KEY,
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
        """)

        # 4. Restaurer les données sauvegardées
        if existing_projects:
            logger.info("📥 Restauration des données...")
            restored_count = 0
            for project in existing_projects:
                try:
                    # S'assurer que les clés nécessaires existent
                    project_id = str(project.get('id', ''))
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO projects 
                        (id, nom_projet, client_company_id, client_contact_id, client_nom_cache, client_legacy,
                         statut, priorite, tache, date_soumis, date_prevu, date_debut_reel, date_fin_reel,
                         bd_ft_estime, prix_estime, description, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        project_id,
                        project.get('nom_projet', ''),
                        project.get('client_company_id'),
                        project.get('client_contact_id'),
                        project.get('client_nom_cache', ''),
                        project.get('client_legacy', ''),
                        project.get('statut', 'À FAIRE'),
                        project.get('priorite', 'MOYEN'),
                        project.get('tache', ''),
                        project.get('date_soumis', ''),
                        project.get('date_prevu', ''),
                        project.get('date_debut_reel', ''),
                        project.get('date_fin_reel', ''),
                        project.get('bd_ft_estime', 0),
                        project.get('prix_estime', 0),
                        project.get('description', ''),
                        project.get('created_at', datetime.now().isoformat()),
                        project.get('updated_at', datetime.now().isoformat())
                    ))
                    restored_count += 1
                except Exception as restore_error:
                    logger.error(f"⚠️ Erreur restauration projet ID {project.get('id')}: {restore_error}")
            
            logger.info(f"✅ {restored_count}/{len(existing_projects)} projets restaurés.")
        
        db_conn.commit()
        logger.info("🎉 SUCCÈS : Table 'projects' réparée/créée avec succès.")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur critique dans la fonction de réparation de la table 'projects': {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

class ERPDatabase:
    """
    Gestionnaire de base de données SQLite unifié pour ERP Production DG Inc.
    VERSION CONSOLIDÉE + INTERFACE UNIFIÉE TIMETRACKER + POSTES + MODULE PRODUCTION + INTÉGRATION OPERATIONS ↔ BT
    VERSION COMMUNICANTE + MÉTHODES TIMETRACKER UNIFIÉES + CORRECTION TABLE PROJECTS
    
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
    
    INTÉGRATION TIMETRACKER ↔ BONS DE TRAVAIL :
    - time_entries.formulaire_bt_id → liaison directe avec formulaires BT
    - bt_assignations → assignations employés aux BT
    - bt_reservations_postes → réservations postes de travail
    - Traçabilité complète des pointages par BT
    
    NOUVELLE INTÉGRATION OPERATIONS ↔ BONS DE TRAVAIL :
    - operations.formulaire_bt_id → liaison opérations aux BT qui les ont créées
    - Traçabilité des gammes de fabrication par BT
    - Gestion unifiée des opérations de production
    
    INTERFACE UNIFIÉE TIMETRACKER + POSTES :
    - Méthodes complètes de gestion des postes de travail
    - Statistiques avancées pour l'interface fusionnée
    - Méthodes pour gammes de fabrication
    - Optimisations pour l'analyse de capacité
    - Vues spécialisées pour l'interface unifiée
    
    MODULE PRODUCTION UNIFIÉ (ÉTAPE 3) :
    - Gestion complète des nomenclatures (BOM)
    - Gammes de fabrication et itinéraires
    - Intégration inventaire ↔ production
    - Métriques et statistiques de production
    
    MÉTHODES COMMUNICATION TIMETRACKER UNIFIÉES :
    - get_employee_productivity_stats() → Statistiques employé avec BT
    - get_unified_analytics() → Analytics fusionnés BT + TimeTracker
    - marquer_bt_termine() → Finalisation BT avec traçabilité
    - recalculate_all_bt_progress() → Recalcul progression basé TimeTracker
    - sync_bt_timetracker_data() → Synchronisation données
    - cleanup_empty_bt_sessions() → Nettoyage sessions orphelines
    
    CORRECTIONS AUTOMATIQUES INTÉGRÉES :
    - Colonnes projects corrigées (date_debut_reel, date_fin_reel)
    - Tables BT spécialisées (bt_assignations, bt_reservations_postes)
    - Colonne formulaire_bt_id dans time_entries (ÉTAPE 2)
    - Colonne formulaire_bt_id dans operations (NOUVEAU)
    - Toutes les améliorations de fix_database.py
    - NOUVEAU : Table projects avec ID TEXT (correction majeure)
    """
    
    def __init__(self, db_path: str = "erp_production_dg.db"):
        self.db_path = db_path
        self.backup_dir = "backup_json"
        self.init_database()
        logger.info(f"ERPDatabase consolidé + Interface Unifiée + Production + Operations↔BT + Communication TT + Projects TEXT ID initialisé : {db_path}")
        
        # Vérification et mise à niveau du schéma
        logger.info("🔧 DEBUG: Avant appel check_and_upgrade_schema()")
        try:
            self.check_and_upgrade_schema()
            logger.info("🔧 DEBUG: Après appel check_and_upgrade_schema() - SUCCÈS")
        except Exception as e:
            logger.error(f"🔧 DEBUG: ERREUR dans check_and_upgrade_schema(): {e}")
            import traceback
            logger.error(f"🔧 DEBUG: Traceback: {traceback.format_exc()}")

    def get_schema_version(self):
        """Récupère la version actuelle du schéma de base de données"""
        try:
            result = self.execute_query("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1")
            if result:
                return result[0]['version']
            else:
                return 0  # Version initiale
        except Exception:
            # Table schema_version n'existe pas encore
            return 0

    def set_schema_version(self, version):
        """Définit la version du schéma"""
        try:
            # Créer la table si elle n'existe pas
            self.execute_update('''
                CREATE TABLE IF NOT EXISTS schema_version (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            ''')
            
            # Insérer la nouvelle version
            self.execute_update(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                (version, f"Schema upgraded to version {version}")
            )
        except Exception as e:
            print(f"Erreur set_schema_version: {e}")

    def check_and_upgrade_schema(self):
        """Vérifie et met à jour le schéma de base de données"""
        logger.info("🔧 DEBUG: check_and_upgrade_schema() appelé")
        
        LATEST_SCHEMA_VERSION = 6  # 🎯 Version 6 pour inclure la correction projects
        
        current_version = self.get_schema_version()
        logger.info(f"🔧 DEBUG: Version actuelle = {current_version}")
        
        if current_version < LATEST_SCHEMA_VERSION:
            logger.info(f"🔄 Migration nécessaire: v{current_version} → v{LATEST_SCHEMA_VERSION}")
            self.upgrade_schema(current_version, LATEST_SCHEMA_VERSION)
        else:
            logger.info(f"✅ Schéma à jour: v{current_version}")

    def upgrade_schema(self, from_version, to_version):
        """Applique les migrations de schéma"""
        try:
            logger.info(f"🔄 Migration schéma: v{from_version} → v{to_version}")
            
            if from_version < 1:
                logger.info("📝 Migration v1: Corrections colonnes projects...")
                try:
                    self.execute_update("ALTER TABLE projects ADD COLUMN date_debut_reel DATE")
                    self.execute_update("ALTER TABLE projects ADD COLUMN date_fin_reel DATE")
                except Exception:
                    pass  # Colonnes existent déjà
                    
            if from_version < 2:
                logger.info("📝 Migration v2: Tables BT spécialisées...")
                try:
                    self.execute_update('''
                        CREATE TABLE IF NOT EXISTS bt_assignations (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            bt_id INTEGER NOT NULL,
                            employee_id INTEGER NOT NULL,
                            assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            role_assignment TEXT DEFAULT 'Exécutant',
                            FOREIGN KEY (bt_id) REFERENCES formulaires(id),
                            FOREIGN KEY (employee_id) REFERENCES employees(id)
                        )
                    ''')
                    
                    self.execute_update('''
                        CREATE TABLE IF NOT EXISTS bt_reservations_postes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            bt_id INTEGER NOT NULL,
                            work_center_id INTEGER NOT NULL,
                            reserved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            duration_hours REAL DEFAULT 0,
                            FOREIGN KEY (bt_id) REFERENCES formulaires(id),
                            FOREIGN KEY (work_center_id) REFERENCES work_centers(id)
                        )
                    ''')
                    logger.info("✅ Tables BT spécialisées créées")
                except Exception as e:
                    logger.error(f"Erreur migration v2: {e}")
                    
            if from_version < 3:
                logger.info("📝 Migration v3: Colonnes formulaire_bt_id...")
                try:
                    self.execute_update("ALTER TABLE time_entries ADD COLUMN formulaire_bt_id INTEGER")
                    self.execute_update("ALTER TABLE operations ADD COLUMN formulaire_bt_id INTEGER")
                    logger.info("✅ Colonnes formulaire_bt_id ajoutées")
                except Exception as e:
                    logger.error(f"Erreur migration v3: {e}")
                    
            if from_version < 4:
                logger.info("📝 Migration v4: Améliorations finales et optimisations...")
                try:
                    # Index pour performance
                    self.execute_update("CREATE INDEX IF NOT EXISTS idx_time_entries_bt_id ON time_entries(formulaire_bt_id)")
                    self.execute_update("CREATE INDEX IF NOT EXISTS idx_operations_bt_id ON operations(formulaire_bt_id)")
                    self.execute_update("CREATE INDEX IF NOT EXISTS idx_bt_assignations_bt_id ON bt_assignations(bt_id)")
                    self.execute_update("CREATE INDEX IF NOT EXISTS idx_bt_reservations_bt_id ON bt_reservations_postes(bt_id)")
                    
                    # Mise à jour des données si nécessaire
                    self.execute_update("UPDATE projects SET statut = 'À FAIRE' WHERE statut IS NULL OR statut = ''")
                    self.execute_update("UPDATE projects SET priorite = 'MOYEN' WHERE priorite IS NULL OR priorite = ''")
                    
                    logger.info("✅ Optimisations et nettoyage appliqués")
                except Exception as e:
                    logger.error(f"Erreur migration v4: {e}")
                    
            if from_version < 5:
                logger.info("📝 Migration v5: FORCE - Application complète de toutes les améliorations DG Inc...")
                try:
                    # Application de toutes les améliorations précédentes
                    self._apply_full_improvements()
                    logger.info("✅ Migration v5 terminée")
                except Exception as e:
                    logger.error(f"❌ Erreur migration v5: {e}")
                    
            if from_version < 6:
                logger.info("📝 Migration v6: CORRECTION MAJEURE - Table projects avec ID TEXT...")
                try:
                    # Appliquer la correction pour la table projects
                    with self.get_connection() as conn:
                        success = force_recreate_projects_table_with_text_id(conn)
                        if success:
                            logger.info("✅ Migration v6 - Table projects corrigée avec ID TEXT")
                            self._update_related_tables_for_text_id(conn)
                        else:
                            logger.error("❌ Échec de la correction de la table projects")
                except Exception as e:
                    logger.error(f"❌ Erreur migration v6: {e}")
            
            # Marquer comme migré
            self.set_schema_version(to_version)
            logger.info(f"✅ Migration terminée: schéma v{to_version}")
            
        except Exception as e:
            logger.error(f"❌ Erreur migration schéma: {e}")
            import traceback
            logger.error(f"Traceback complet: {traceback.format_exc()}")

    def _apply_full_improvements(self):
        """Applique toutes les améliorations de la v5"""
        try:
            # Vérifier et créer colonnes manquantes
            try:
                self.execute_update("ALTER TABLE projects ADD COLUMN date_debut_reel DATE")
            except Exception:
                pass
            
            try:
                self.execute_update("ALTER TABLE projects ADD COLUMN date_fin_reel DATE")
            except Exception:
                pass
            
            # Créer tables BT spécialisées
            self.execute_update('''
                CREATE TABLE IF NOT EXISTS bt_assignations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bt_id INTEGER NOT NULL,
                    employee_id INTEGER NOT NULL,
                    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    role_assignment TEXT DEFAULT 'Exécutant'
                )
            ''')
            
            self.execute_update('''
                CREATE TABLE IF NOT EXISTS bt_reservations_postes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bt_id INTEGER NOT NULL,
                    work_center_id INTEGER NOT NULL,
                    reserved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    duration_hours REAL DEFAULT 0
                )
            ''')
            
            # Créer colonnes formulaire_bt_id
            try:
                self.execute_update("ALTER TABLE time_entries ADD COLUMN formulaire_bt_id INTEGER")
            except Exception:
                pass
                
            try:
                self.execute_update("ALTER TABLE operations ADD COLUMN formulaire_bt_id INTEGER")
            except Exception:
                pass
            
            # Créer index de performance
            performance_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_time_entries_bt_id ON time_entries(formulaire_bt_id)",
                "CREATE INDEX IF NOT EXISTS idx_operations_bt_id ON operations(formulaire_bt_id)",
                "CREATE INDEX IF NOT EXISTS idx_bt_assignations_bt_id ON bt_assignations(bt_id)",
                "CREATE INDEX IF NOT EXISTS idx_bt_reservations_bt_id ON bt_reservations_postes(bt_id)",
                "CREATE INDEX IF NOT EXISTS idx_projects_client_id ON projects(client_company_id)",
                "CREATE INDEX IF NOT EXISTS idx_time_entries_employee ON time_entries(employee_id)",
                "CREATE INDEX IF NOT EXISTS idx_operations_project ON operations(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_formulaires_type ON formulaires(type_formulaire)"
            ]
            
            for index_sql in performance_indexes:
                try:
                    self.execute_update(index_sql)
                except Exception:
                    pass
            
            # Nettoyage des données
            cleanup_queries = [
                "UPDATE projects SET statut = 'À FAIRE' WHERE statut IS NULL OR statut = ''",
                "UPDATE projects SET priorite = 'MOYEN' WHERE priorite IS NULL OR priorite = ''",
                "UPDATE employees SET statut = 'ACTIF' WHERE statut IS NULL OR statut = ''",
                "UPDATE work_centers SET statut = 'ACTIF' WHERE statut IS NULL OR statut = ''",
                "UPDATE formulaires SET statut = 'BROUILLON' WHERE statut IS NULL OR statut = ''"
            ]
            
            for cleanup_sql in cleanup_queries:
                try:
                    self.execute_update(cleanup_sql)
                except Exception:
                    pass
            
        except Exception as e:
            logger.error(f"Erreur application améliorations complètes: {e}")

    def _update_related_tables_for_text_id(self, conn):
        """Met à jour les tables liées pour utiliser project_id TEXT"""
        try:
            cursor = conn.cursor()
            logger.info("🔧 Mise à jour tables liées pour project_id TEXT...")
            
            # Recréer la table operations avec project_id TEXT
            try:
                cursor.execute("SELECT * FROM operations")
                operations_data = cursor.fetchall()
                operations_backup = [dict(row) for row in operations_data] if operations_data else []
                
                cursor.execute("DROP TABLE IF EXISTS operations")
                cursor.execute('''
                    CREATE TABLE operations (
                        id INTEGER PRIMARY KEY,
                        project_id TEXT,
                        work_center_id INTEGER,
                        formulaire_bt_id INTEGER,
                        sequence_number INTEGER,
                        description TEXT,
                        temps_estime REAL,
                        ressource TEXT,
                        statut TEXT DEFAULT 'À FAIRE',
                        poste_travail TEXT,
                        operation_legacy_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                        FOREIGN KEY (work_center_id) REFERENCES work_centers(id),
                        FOREIGN KEY (formulaire_bt_id) REFERENCES formulaires(id) ON DELETE SET NULL
                    )
                ''')
                
                # Restaurer les données operations
                for op in operations_backup:
                    cursor.execute('''
                        INSERT INTO operations 
                        (id, project_id, work_center_id, formulaire_bt_id, sequence_number, 
                         description, temps_estime, ressource, statut, poste_travail, 
                         operation_legacy_id, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        op.get('id'),
                        str(op.get('project_id', '')) if op.get('project_id') else None,
                        op.get('work_center_id'),
                        op.get('formulaire_bt_id'),
                        op.get('sequence_number', 0),
                        op.get('description', ''),
                        op.get('temps_estime', 0.0),
                        op.get('ressource', ''),
                        op.get('statut', 'À FAIRE'),
                        op.get('poste_travail', ''),
                        op.get('operation_legacy_id'),
                        op.get('created_at', datetime.now().isoformat())
                    ))
                
                logger.info(f"✅ Table operations mise à jour avec {len(operations_backup)} enregistrements")
                
            except Exception as e:
                logger.error(f"Erreur mise à jour operations: {e}")
            
            # Faire de même pour materials
            try:
                cursor.execute("SELECT * FROM materials")
                materials_data = cursor.fetchall()
                materials_backup = [dict(row) for row in materials_data] if materials_data else []
                
                cursor.execute("DROP TABLE IF EXISTS materials")
                cursor.execute('''
                    CREATE TABLE materials (
                        id INTEGER PRIMARY KEY,
                        project_id TEXT,
                        material_legacy_id INTEGER,
                        code_materiau TEXT,
                        designation TEXT,
                        quantite REAL,
                        unite TEXT,
                        prix_unitaire REAL,
                        fournisseur TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                    )
                ''')
                
                # Restaurer materials
                for mat in materials_backup:
                    cursor.execute('''
                        INSERT INTO materials 
                        (id, project_id, material_legacy_id, code_materiau, designation,
                         quantite, unite, prix_unitaire, fournisseur, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        mat.get('id'),
                        str(mat.get('project_id', '')) if mat.get('project_id') else None,
                        mat.get('material_legacy_id'),
                        mat.get('code_materiau', ''),
                        mat.get('designation', ''),
                        mat.get('quantite', 0.0),
                        mat.get('unite', ''),
                        mat.get('prix_unitaire', 0.0),
                        mat.get('fournisseur', ''),
                        mat.get('created_at', datetime.now().isoformat())
                    ))
                
                logger.info(f"✅ Table materials mise à jour avec {len(materials_backup)} enregistrements")
                
            except Exception as e:
                logger.error(f"Erreur mise à jour materials: {e}")
            
            # Mettre à jour time_entries si nécessaire
            try:
                cursor.execute("UPDATE time_entries SET project_id = CAST(project_id AS TEXT) WHERE project_id IS NOT NULL")
                logger.info("✅ time_entries project_id convertis en TEXT")
            except Exception as e:
                logger.error(f"Erreur conversion time_entries: {e}")
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Erreur mise à jour tables liées: {e}")
    
    def init_database(self):
        """Initialise toutes les tables de la base de données ERP avec corrections automatiques intégrées"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Activer les clés étrangères et optimisations SQLite
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.execute("PRAGMA temp_store = memory")
            cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB
            
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
            
            # 3. PROJETS - PLACEHOLDER (sera corrigé par force_recreate_projects_table_with_text_id)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects_placeholder (
                    id INTEGER PRIMARY KEY,
                    nom_projet TEXT,
                    description TEXT
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
                    nom TEXT NOT NULL UNIQUE,
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
            
            # 7-8. OPÉRATIONS ET MATÉRIAUX - PLACEHOLDER (seront corrigés avec project_id TEXT)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS operations_placeholder (
                    id INTEGER PRIMARY KEY,
                    project_id TEXT,
                    description TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS materials_placeholder (
                    id INTEGER PRIMARY KEY,
                    project_id TEXT,
                    description TEXT
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
                    project_id TEXT,
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
                    project_id TEXT,
                    operation_id INTEGER,
                    formulaire_bt_id INTEGER,
                    punch_in TIMESTAMP,
                    punch_out TIMESTAMP,
                    total_hours REAL,
                    hourly_rate REAL,
                    total_cost REAL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id),
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (operation_id) REFERENCES operations(id),
                    FOREIGN KEY (formulaire_bt_id) REFERENCES formulaires(id)
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
                    project_id TEXT,
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
                        ('CREATION', 'MODIFICATION', 'VALIDATION', 'APPROBATION', 'ENVOI', 'CHANGEMENT_STATUT', 'ANNULATION', 'TERMINAISON')),
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
            
            # 19. FOURNISSEURS
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
            
            # 20. APPROVISIONNEMENTS
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
            # TABLES SPÉCIALISÉES BONS DE TRAVAIL
            # =========================================================================
            
            # 21. ASSIGNATIONS BONS DE TRAVAIL
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bt_assignations (
                    id INTEGER PRIMARY KEY,
                    bt_id INTEGER,
                    employe_id INTEGER,
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
            
            # 23. AVANCEMENT BONS DE TRAVAIL
            cursor.execute('''
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
            ''')
            
            conn.commit()
            
            # =========================================================================
            # CORRECTION MAJEURE : Appliquer la correction projects après création des tables de base
            # =========================================================================
            
            logger.info("🔧 Application de la correction majeure table projects...")
            success = force_recreate_projects_table_with_text_id(conn)
            if success:
                logger.info("✅ Table projects corrigée avec ID TEXT")
                
                # Créer les vraies tables operations et materials maintenant que projects existe
                self._create_final_tables(conn)
                
                # Créer toutes les vues
                self._create_database_views(conn)
                
                # Créer tous les triggers
                self._create_database_triggers(conn)
                
            else:
                logger.error("❌ Échec correction table projects")
            
            # Optimisation finale de la base
            cursor.execute("PRAGMA optimize")
            conn.commit()
            logger.info("Base de données ERP consolidée + Correction Projects initialisée avec succès")

    def _create_final_tables(self, conn):
        """Crée les tables finales après correction de projects"""
        cursor = conn.cursor()
        
        try:
            # Supprimer les tables placeholder
            cursor.execute("DROP TABLE IF EXISTS operations_placeholder")
            cursor.execute("DROP TABLE IF EXISTS materials_placeholder")
            
            # 7. OPÉRATIONS (Gammes) - VERSION FINALE
            cursor.execute('''
                CREATE TABLE operations (
                    id INTEGER PRIMARY KEY,
                    project_id TEXT,
                    work_center_id INTEGER,
                    formulaire_bt_id INTEGER,
                    sequence_number INTEGER,
                    description TEXT,
                    temps_estime REAL,
                    ressource TEXT,
                    statut TEXT DEFAULT 'À FAIRE',
                    poste_travail TEXT,
                    operation_legacy_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (work_center_id) REFERENCES work_centers(id),
                    FOREIGN KEY (formulaire_bt_id) REFERENCES formulaires(id) ON DELETE SET NULL
                )
            ''')
            
            # 8. MATÉRIAUX/BOM - VERSION FINALE
            cursor.execute('''
                CREATE TABLE materials (
                    id INTEGER PRIMARY KEY,
                    project_id TEXT,
                    material_legacy_id INTEGER,
                    code_materiau TEXT,
                    designation TEXT,
                    quantite REAL,
                    unite TEXT,
                    prix_unitaire REAL,
                    fournisseur TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            ''')
            
            # Index pour performance optimale
            performance_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_projects_client ON projects(client_company_id)",
                "CREATE INDEX IF NOT EXISTS idx_projects_statut ON projects(statut)",
                "CREATE INDEX IF NOT EXISTS idx_projects_priorite ON projects(priorite)",
                "CREATE INDEX IF NOT EXISTS idx_operations_project ON operations(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_operations_work_center ON operations(work_center_id)",
                "CREATE INDEX IF NOT EXISTS idx_operations_bt ON operations(formulaire_bt_id)",
                "CREATE INDEX IF NOT EXISTS idx_materials_project ON materials(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_time_entries_employee ON time_entries(employee_id)",
                "CREATE INDEX IF NOT EXISTS idx_time_entries_project ON time_entries(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_time_entries_bt ON time_entries(formulaire_bt_id)",
                "CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company_id)",
                "CREATE INDEX IF NOT EXISTS idx_competences_employee ON employee_competences(employee_id)",
                "CREATE INDEX IF NOT EXISTS idx_companies_secteur ON companies(secteur)",
                "CREATE INDEX IF NOT EXISTS idx_companies_type ON companies(type_company)",
                "CREATE INDEX IF NOT EXISTS idx_inventory_statut ON inventory_items(statut)",
                "CREATE INDEX IF NOT EXISTS idx_inventory_type ON inventory_items(type_produit)",
                "CREATE INDEX IF NOT EXISTS idx_employees_statut ON employees(statut)",
                "CREATE INDEX IF NOT EXISTS idx_employees_departement ON employees(departement)",
                "CREATE INDEX IF NOT EXISTS idx_formulaires_type ON formulaires(type_formulaire)",
                "CREATE INDEX IF NOT EXISTS idx_formulaires_statut ON formulaires(statut)",
                "CREATE INDEX IF NOT EXISTS idx_formulaires_project ON formulaires(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_formulaires_company ON formulaires(company_id)",
                "CREATE INDEX IF NOT EXISTS idx_bt_assignations_bt ON bt_assignations(bt_id)",
                "CREATE INDEX IF NOT EXISTS idx_bt_reservations_bt ON bt_reservations_postes(bt_id)",
                "CREATE INDEX IF NOT EXISTS idx_work_centers_nom ON work_centers(nom)",
                "CREATE INDEX IF NOT EXISTS idx_work_centers_statut ON work_centers(statut)"
            ]
            
            for index_sql in performance_indexes:
                try:
                    cursor.execute(index_sql)
                except Exception:
                    pass  # Index existe peut-être déjà
            
            logger.info("✅ Tables finales créées avec index de performance")
            conn.commit()
            
        except Exception as e:
            logger.error(f"❌ Erreur création tables finales: {e}")

    def _create_database_views(self, conn):
        """Crée toutes les vues de la base de données"""
        cursor = conn.cursor()
        
        try:
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
            
            # Vue intégration TimeTracker ↔ Bons de Travail
            cursor.execute('''
                CREATE VIEW IF NOT EXISTS view_bt_timetracker_integration AS
                SELECT 
                    f.id as bt_id,
                    f.numero_document as bt_numero,
                    f.statut as bt_statut,
                    f.priorite as bt_priorite,
                    p.nom_projet,
                    COUNT(DISTINCT te.id) as nb_sessions_pointage,
                    COUNT(DISTINCT te.employee_id) as nb_employes_ayant_pointe,
                    COALESCE(SUM(te.total_hours), 0) as total_heures_pointees,
                    COALESCE(SUM(te.total_cost), 0) as total_cout_pointage,
                    MIN(te.punch_in) as premiere_session_pointage,
                    MAX(te.punch_out) as derniere_session_pointage,
                    COUNT(DISTINCT bta.employe_id) as nb_employes_assignes
                FROM formulaires f
                LEFT JOIN projects p ON f.project_id = p.id
                LEFT JOIN time_entries te ON f.id = te.formulaire_bt_id
                LEFT JOIN bt_assignations bta ON f.id = bta.bt_id
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                GROUP BY f.id
            ''')
            
            # Vue complète des postes avec statistiques TimeTracker
            cursor.execute('''
                CREATE VIEW IF NOT EXISTS view_work_centers_with_stats AS
                SELECT 
                    wc.*,
                    COUNT(DISTINCT o.id) as operations_count,
                    COUNT(DISTINCT te.id) as timetracker_entries,
                    COALESCE(SUM(te.total_hours), 0) as total_hours_tracked,
                    COALESCE(SUM(te.total_cost), 0) as total_revenue_generated,
                    COALESCE(AVG(te.hourly_rate), wc.cout_horaire) as avg_actual_rate,
                    COUNT(DISTINCT te.employee_id) as unique_employees_used,
                    COUNT(DISTINCT o.project_id) as projects_touched,
                    -- Calcul du taux d'utilisation (dernier mois)
                    CASE 
                        WHEN wc.capacite_theorique > 0 THEN
                            ROUND((COALESCE(SUM(CASE WHEN DATE(te.punch_in) >= DATE('now', '-30 days') 
                                             THEN te.total_hours ELSE 0 END), 0) / 
                                  (wc.capacite_theorique * 30)) * 100, 2)
                        ELSE 0
                    END as utilization_rate_30d,
                    -- Classification d'efficacité
                    CASE 
                        WHEN COALESCE(SUM(te.total_hours), 0) = 0 THEN 'NON_UTILISÉ'
                        WHEN wc.capacite_theorique > 0 AND 
                             (COALESCE(SUM(te.total_hours), 0) / (wc.capacite_theorique * 30)) >= 0.8 THEN 'TRÈS_EFFICACE'
                        WHEN wc.capacite_theorique > 0 AND 
                             (COALESCE(SUM(te.total_hours), 0) / (wc.capacite_theorique * 30)) >= 0.5 THEN 'EFFICACE'
                        WHEN wc.capacite_theorique > 0 AND 
                             (COALESCE(SUM(te.total_hours), 0) / (wc.capacite_theorique * 30)) >= 0.2 THEN 'SOUS_UTILISÉ'
                        ELSE 'PEU_UTILISÉ'
                    END as efficiency_classification
                FROM work_centers wc
                LEFT JOIN operations o ON wc.id = o.work_center_id
                LEFT JOIN time_entries te ON o.id = te.operation_id AND te.total_cost IS NOT NULL
                GROUP BY wc.id
                ORDER BY total_revenue_generated DESC
            ''')
            
            logger.info("✅ Vues de base de données créées")
            conn.commit()
            
        except Exception as e:
            logger.error(f"❌ Erreur création vues: {e}")

    def _create_database_triggers(self, conn):
        """Crée tous les triggers de la base de données"""
        cursor = conn.cursor()
        
        try:
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
            
            # Trigger pour validation automatique des pointages BT
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS trigger_validate_bt_timetracker
                BEFORE INSERT ON time_entries
                FOR EACH ROW
                WHEN NEW.formulaire_bt_id IS NOT NULL
                BEGIN
                    SELECT CASE 
                        WHEN (SELECT type_formulaire FROM formulaires WHERE id = NEW.formulaire_bt_id) != 'BON_TRAVAIL' THEN
                            RAISE(ABORT, 'formulaire_bt_id doit référencer un Bon de Travail')
                        WHEN NEW.employee_id IS NULL THEN
                            RAISE(ABORT, 'employee_id obligatoire pour pointage BT')
                    END;
                END;
            ''')
            
            logger.info("✅ Triggers de base de données créés")
            conn.commit()
            
        except Exception as e:
            logger.error(f"❌ Erreur création triggers: {e}")
    
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
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.fetchall()
            except sqlite3.OperationalError as e:
                logger.error(f"Erreur de requête: {e} | Query: {query} | Params: {params}")
                return []
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Exécute une requête INSERT/UPDATE/DELETE et retourne le nombre de lignes affectées"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.rowcount
            except sqlite3.OperationalError as e:
                logger.error(f"Erreur de mise à jour: {e} | Query: {query} | Params: {params}")
                return 0
    
    def execute_insert(self, query: str, params: tuple = None) -> int:
        """Exécute un INSERT et retourne l'ID de la nouvelle ligne"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.lastrowid
            except sqlite3.OperationalError as e:
                logger.error(f"Erreur d'insertion: {e} | Query: {query} | Params: {params}")
                return None
    
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
            'formulaires', 'formulaire_lignes', 'formulaire_validations',
            'formulaire_pieces_jointes', 'formulaire_templates',
            'fournisseurs', 'approvisionnements',
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
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Retourne des informations sur le schéma de la base"""
        info = {
            'database_file': self.db_path,
            'file_size_mb': round(os.path.getsize(self.db_path) / (1024*1024), 2) if os.path.exists(self.db_path) else 0,
            'tables': {},
            'total_records': 0,
            'projects_id_type': 'UNKNOWN',
            'corrections_appliquees': True,
            'etape_2_complete': True,
            'etape_3_complete': True,
            'interface_unifiee_complete': True,
            'operations_bt_integration_complete': True,
            'communication_tt_complete': True,
            'projects_text_id_correction': False
        }
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Vérifier le type d'ID de projects
            try:
                cursor.execute("PRAGMA table_info(projects)")
                columns = cursor.fetchall()
                id_column = next((col for col in columns if col[1] == 'id'), None)
                if id_column:
                    info['projects_id_type'] = id_column[2]
                    info['projects_text_id_correction'] = 'TEXT' in id_column[2].upper()
            except Exception as e:
                logger.warning(f"Erreur vérification type ID projects: {e}")
            
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
        
        return info
    
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

    # =========================================================================
    # MÉTHODES PRINCIPALES POUR COMPATIBILITÉ
    # =========================================================================
    
    def get_all_projects(self) -> List[Dict]:
        """Récupère tous les projets"""
        try:
            query = '''
                SELECT p.*, c.nom as client_company_nom
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                ORDER BY p.created_at DESC
            '''
            rows = self.execute_query(query)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération projets: {e}")
            return []
    
    def get_project_by_id(self, project_id: str) -> Optional[Dict]:
        """Récupère un projet par son ID"""
        try:
            query = '''
                SELECT p.*, c.nom as client_company_nom
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE p.id = ?
            '''
            result = self.execute_query(query, (str(project_id),))
            return dict(result[0]) if result else None
        except Exception as e:
            logger.error(f"Erreur récupération projet {project_id}: {e}")
            return None
    
    def add_project(self, project_data: Dict) -> Optional[str]:
        """Ajoute un nouveau projet"""
        try:
            project_id = project_data.get('id', str(datetime.now().timestamp()))
            
            query = '''
                INSERT INTO projects 
                (id, nom_projet, client_company_id, client_contact_id, client_nom_cache, client_legacy,
                 statut, priorite, tache, date_soumis, date_prevu, bd_ft_estime, prix_estime, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            self.execute_update(query, (
                str(project_id),
                project_data.get('nom_projet', ''),
                project_data.get('client_company_id'),
                project_data.get('client_contact_id'),
                project_data.get('client_nom_cache', ''),
                project_data.get('client_legacy', ''),
                project_data.get('statut', 'À FAIRE'),
                project_data.get('priorite', 'MOYEN'),
                project_data.get('tache', ''),
                project_data.get('date_soumis'),
                project_data.get('date_prevu'),
                project_data.get('bd_ft_estime', 0.0),
                project_data.get('prix_estime', 0.0),
                project_data.get('description', '')
            ))
            
            logger.info(f"Projet ajouté: {project_id}")
            return str(project_id)
            
        except Exception as e:
            logger.error(f"Erreur ajout projet: {e}")
            return None
    
    def update_project(self, project_id: str, project_data: Dict) -> bool:
        """Met à jour un projet existant"""
        try:
            query = '''
                UPDATE projects SET
                nom_projet = ?, client_company_id = ?, client_contact_id = ?, client_nom_cache = ?,
                statut = ?, priorite = ?, tache = ?, date_soumis = ?, date_prevu = ?,
                bd_ft_estime = ?, prix_estime = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            '''
            
            affected = self.execute_update(query, (
                project_data.get('nom_projet', ''),
                project_data.get('client_company_id'),
                project_data.get('client_contact_id'),
                project_data.get('client_nom_cache', ''),
                project_data.get('statut', 'À FAIRE'),
                project_data.get('priorite', 'MOYEN'),
                project_data.get('tache', ''),
                project_data.get('date_soumis'),
                project_data.get('date_prevu'),
                project_data.get('bd_ft_estime', 0.0),
                project_data.get('prix_estime', 0.0),
                project_data.get('description', ''),
                str(project_id)
            ))
            
            return affected > 0
            
        except Exception as e:
            logger.error(f"Erreur mise à jour projet {project_id}: {e}")
            return False
    
    def delete_project(self, project_id: str) -> bool:
        """Supprime un projet"""
        try:
            affected = self.execute_update("DELETE FROM projects WHERE id = ?", (str(project_id),))
            return affected > 0
        except Exception as e:
            logger.error(f"Erreur suppression projet {project_id}: {e}")
            return False

    # =========================================================================
    # MÉTHODES COMPLÉMENTAIRES POUR FULL COMPATIBILITY
    # =========================================================================
    
    def get_all_employees(self) -> List[Dict]:
        """Récupère tous les employés"""
        try:
            query = "SELECT * FROM employees ORDER BY nom, prenom"
            rows = self.execute_query(query)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération employés: {e}")
            return []
    
    def get_all_companies(self) -> List[Dict]:
        """Récupère toutes les entreprises"""
        try:
            query = "SELECT * FROM companies ORDER BY nom"
            rows = self.execute_query(query)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération entreprises: {e}")
            return []
    
    def get_all_work_centers(self) -> List[Dict]:
        """Récupère tous les postes de travail"""
        try:
            query = "SELECT * FROM work_centers ORDER BY departement, nom"
            rows = self.execute_query(query)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération postes de travail: {e}")
            return []
    
    def test_database_connection(self) -> bool:
        """Teste la connexion à la base de données"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Erreur connexion base de données: {e}")
            return False

    # =========================================================================
    # MÉTHODES SPÉCIFIQUES À L'INTÉGRATION TIMETRACKER ↔ BONS DE TRAVAIL
    # =========================================================================
    
    def get_bts_assignes_employe_avec_timetracker(self, employee_id: int) -> List[Dict]:
        """Récupère les BTs assignés à un employé avec ses statistiques TimeTracker"""
        try:
            query = '''
                SELECT 
                    f.id as bt_id,
                    f.numero_document,
                    f.statut as bt_statut,
                    f.priorite as bt_priorite,
                    f.date_creation,
                    f.date_echeance,
                    p.nom_projet,
                    c.nom as company_nom,
                    bta.date_assignation,
                    bta.statut as assignation_statut,
                    bta.notes_assignation,
                    -- Statistiques TimeTracker
                    COUNT(DISTINCT te.id) as nb_sessions_pointage,
                    COALESCE(SUM(te.total_hours), 0) as total_heures_pointees,
                    COALESCE(SUM(te.total_cost), 0) as total_cout_pointage,
                    MAX(te.punch_out) as derniere_session
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
                        WHEN 'NORMAL' THEN 3
                    END,
                    f.date_echeance ASC
            '''
            
            rows = self.execute_query(query, (employee_id, employee_id))
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur récupération BTs assignés avec TimeTracker: {e}")
            return []
    
    def get_bt_details_for_timetracker(self, bt_id: int) -> Optional[Dict]:
        """Récupère les détails d'un BT pour l'interface TimeTracker"""
        try:
            query = '''
                SELECT * FROM view_bt_timetracker_integration
                WHERE bt_id = ?
            '''
            result = self.execute_query(query, (bt_id,))
            return dict(result[0]) if result else {}
            
        except Exception as e:
            logger.error(f"Erreur récupération détails BT pour TimeTracker: {e}")
            return {}
    
    def create_time_entry_for_bt(self, employee_id: int, bt_id: int, notes: str = "") -> int:
        """Crée une entrée de pointage liée à un BT"""
        try:
            # Récupérer les infos du BT pour le project_id
            bt_info = self.execute_query(
                "SELECT project_id FROM formulaires WHERE id = ? AND type_formulaire = 'BON_TRAVAIL'", 
                (bt_id,)
            )
            
            if not bt_info:
                logger.error(f"BT {bt_id} non trouvé ou n'est pas un Bon de Travail")
                return None
            
            project_id = bt_info[0]['project_id']
            
            # Créer l'entrée de pointage
            query = '''
                INSERT INTO time_entries 
                (employee_id, project_id, formulaire_bt_id, punch_in, notes)
                VALUES (?, ?, ?, ?, ?)
            '''
            
            entry_id = self.execute_insert(query, (
                employee_id,
                project_id,
                bt_id,
                datetime.now().isoformat(),
                notes
            ))
            
            logger.info(f"✅ Pointage BT créé: entry_id={entry_id}, bt_id={bt_id}, employee_id={employee_id}")
            return entry_id
            
        except Exception as e:
            logger.error(f"Erreur création pointage BT: {e}")
            return None
    
    def close_time_entry_for_bt(self, entry_id: int, hourly_rate: float = None) -> bool:
        """Ferme une entrée de pointage BT et calcule les coûts"""
        try:
            # Récupérer l'entrée
            entry = self.execute_query(
                "SELECT * FROM time_entries WHERE id = ? AND punch_out IS NULL", 
                (entry_id,)
            )
            
            if not entry:
                logger.error(f"Time entry {entry_id} non trouvé ou déjà fermé")
                return False
            
            entry = entry[0]
            punch_in = datetime.fromisoformat(entry['punch_in'])
            punch_out = datetime.now()
            total_seconds = (punch_out - punch_in).total_seconds()
            total_hours = total_seconds / 3600
            
            # Utiliser le hourly_rate fourni ou récupérer celui de l'employé
            if hourly_rate is None:
                emp_result = self.execute_query(
                    "SELECT salaire FROM employees WHERE id = ?", 
                    (entry['employee_id'],)
                )
                hourly_rate = (emp_result[0]['salaire'] / 2080) if emp_result and emp_result[0]['salaire'] else 25.0
            
            total_cost = total_hours * hourly_rate
            
            # Mettre à jour l'entrée
            query = '''
                UPDATE time_entries 
                SET punch_out = ?, total_hours = ?, hourly_rate = ?, total_cost = ?
                WHERE id = ?
            '''
            
            affected = self.execute_update(query, (
                punch_out.isoformat(),
                total_hours,
                hourly_rate,
                total_cost,
                entry_id
            ))
            
            logger.info(f"✅ Pointage BT fermé: entry_id={entry_id}, heures={total_hours:.2f}, coût={total_cost:.2f}$")
            return affected > 0
            
        except Exception as e:
            logger.error(f"Erreur fermeture pointage BT: {e}")
            return False
    
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
                result = self.execute_query(query, (bt_id,))
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
                result = self.execute_query(query)
            
            return dict(result[0]) if result else {}
            
        except Exception as e:
            logger.error(f"Erreur stats BT TimeTracker: {e}")
            return {}

    # =========================================================================
    # MÉTHODES COMMUNICATION TIMETRACKER UNIFIÉES
    # =========================================================================
    
    def get_employee_productivity_stats(self, employee_id: int) -> Dict:
        """Statistiques de productivité d'un employé avec BTs"""
        try:
            query = '''
                SELECT 
                    COALESCE(SUM(te.total_hours), 0) as total_hours,
                    COALESCE(SUM(CASE WHEN te.formulaire_bt_id IS NOT NULL THEN te.total_hours ELSE 0 END), 0) as bt_hours,
                    COALESCE(SUM(te.total_cost), 0) as total_revenue,
                    COALESCE(SUM(CASE WHEN te.formulaire_bt_id IS NOT NULL THEN te.total_cost ELSE 0 END), 0) as bt_revenue,
                    COUNT(DISTINCT te.formulaire_bt_id) as bt_count,
                    COALESCE(AVG(te.total_hours), 0) as avg_hours_per_session,
                    COUNT(DISTINCT te.project_id) as projects_worked
                FROM time_entries te
                WHERE te.employee_id = ? AND te.total_cost IS NOT NULL
            '''
            result = self.execute_query(query, (employee_id,))
            
            if result:
                stats = dict(result[0])
                
                # Calculer l'efficacité (estimation basique)
                if stats['total_hours'] > 0:
                    stats['efficiency'] = min(100, (stats['bt_hours'] / stats['total_hours']) * 120)  # Bonus BT
                else:
                    stats['efficiency'] = 0
                    
                return stats
            return {
                'total_hours': 0, 'bt_hours': 0, 'total_revenue': 0, 
                'bt_revenue': 0, 'bt_count': 0, 'efficiency': 0
            }
        except Exception as e:
            logger.error(f"Erreur stats productivité employé {employee_id}: {e}")
            return {}

    def get_unified_analytics(self, start_date, end_date) -> Dict:
        """Analytics unifiés BT + TimeTracker pour période donnée"""
        try:
            # Données quotidiennes
            daily_query = '''
                SELECT 
                    DATE(te.punch_in) as date,
                    COALESCE(SUM(te.total_hours), 0) as total_hours,
                    COALESCE(SUM(CASE WHEN te.formulaire_bt_id IS NOT NULL THEN te.total_hours ELSE 0 END), 0) as bt_hours,
                    COALESCE(SUM(te.total_cost), 0) as total_revenue,
                    COUNT(DISTINCT te.employee_id) as unique_employees,
                    COUNT(DISTINCT te.formulaire_bt_id) as unique_bts
                FROM time_entries te
                WHERE DATE(te.punch_in) BETWEEN ? AND ?
                AND te.total_cost IS NOT NULL
                GROUP BY DATE(te.punch_in)
                ORDER BY DATE(te.punch_in)
            '''
            daily_data = self.execute_query(daily_query, (start_date, end_date))
            
            # Performance employés
            employee_query = '''
                SELECT 
                    e.prenom || ' ' || e.nom as name,
                    COALESCE(SUM(te.total_hours), 0) as total_hours,
                    COALESCE(SUM(CASE WHEN te.formulaire_bt_id IS NOT NULL THEN te.total_hours ELSE 0 END), 0) as bt_hours,
                    COALESCE(SUM(te.total_cost), 0) as total_revenue,
                    COUNT(DISTINCT te.formulaire_bt_id) as bt_count
                FROM employees e
                JOIN time_entries te ON e.id = te.employee_id
                WHERE DATE(te.punch_in) BETWEEN ? AND ?
                AND te.total_cost IS NOT NULL
                GROUP BY e.id
                ORDER BY total_revenue DESC
            '''
            employee_data = self.execute_query(employee_query, (start_date, end_date))
            
            # Calculs globaux
            total_hours = sum(row['total_hours'] for row in daily_data)
            bt_hours = sum(row['bt_hours'] for row in daily_data)
            total_revenue = sum(row['total_revenue'] for row in daily_data)
            
            # Efficacité moyenne
            avg_efficiency = 0
            if len(employee_data) > 0:
                efficiencies = []
                for emp in employee_data:
                    if emp['total_hours'] > 0:
                        eff = (emp['bt_hours'] / emp['total_hours']) * 100
                        efficiencies.append(eff)
                avg_efficiency = sum(efficiencies) / len(efficiencies) if efficiencies else 0
            
            return {
                'total_hours': total_hours,
                'bt_hours': bt_hours,
                'total_revenue': total_revenue,
                'avg_efficiency': avg_efficiency,
                'daily_breakdown': [dict(row) for row in daily_data],
                'employee_performance': [dict(row) for row in employee_data],
                'work_type_breakdown': {
                    'Bons de Travail': bt_hours,
                    'Projets Généraux': max(0, total_hours - bt_hours)
                },
                'profitability_analysis': {
                    'bt_revenue': sum(emp['total_revenue'] for emp in employee_data if emp['bt_count'] > 0),
                    'estimated_margin': 25.0,  # Placeholder
                    'roi_timetracker': 15.0    # Placeholder
                }
            }
        except Exception as e:
            logger.error(f"Erreur analytics unifiés: {e}")
            return {}

    def marquer_bt_termine(self, bt_id: int, employee_id: int, notes: str) -> bool:
        """Marque un BT comme terminé avec traçabilité"""
        try:
            # Vérifier que le BT existe et n'est pas déjà terminé
            bt_check = self.execute_query(
                "SELECT statut FROM formulaires WHERE id = ? AND type_formulaire = 'BON_TRAVAIL'",
                (bt_id,)
            )
            
            if not bt_check:
                logger.error(f"BT #{bt_id} non trouvé")
                return False
            
            if bt_check[0]['statut'] == 'TERMINÉ':
                logger.info(f"BT #{bt_id} déjà terminé")
                return True
            
            # Mettre à jour le statut
            affected = self.execute_update(
                "UPDATE formulaires SET statut = 'TERMINÉ', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (bt_id,)
            )
            
            if affected > 0:
                # Enregistrer dans l'historique des validations
                self.execute_insert(
                    """INSERT INTO formulaire_validations 
                       (formulaire_id, employee_id, type_validation, ancien_statut, nouveau_statut, commentaires)
                       VALUES (?, ?, 'TERMINAISON', ?, 'TERMINÉ', ?)""",
                    (bt_id, employee_id, bt_check[0]['statut'], notes)
                )
                
                # Mettre à jour tous les avancements à 100%
                self.execute_update(
                    "UPDATE bt_avancement SET pourcentage_realise = 100, updated_at = CURRENT_TIMESTAMP WHERE bt_id = ?",
                    (bt_id,)
                )
                
                # Libérer les postes de travail réservés
                self.execute_update(
                    "UPDATE bt_reservations_postes SET statut = 'LIBÉRÉ', date_liberation = CURRENT_TIMESTAMP WHERE bt_id = ? AND statut = 'RÉSERVÉ'",
                    (bt_id,)
                )
                
                logger.info(f"✅ BT #{bt_id} marqué terminé par employé #{employee_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur marquage BT terminé: {e}")
            return False

    def recalculate_all_bt_progress(self) -> int:
        """Recalcule la progression de tous les BTs basée sur TimeTracker"""
        try:
            count = 0
            # Récupérer tous les BTs non terminés
            bts = self.execute_query(
                "SELECT id, metadonnees_json FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL' AND statut != 'TERMINÉ'"
            )
            
            for bt in bts:
                bt_id = bt['id']
                
                # Récupérer temps total pointé sur ce BT
                time_result = self.execute_query(
                    "SELECT COALESCE(SUM(total_hours), 0) as total_worked FROM time_entries WHERE formulaire_bt_id = ? AND total_cost IS NOT NULL",
                    (bt_id,)
                )
                
                if time_result:
                    total_worked = time_result[0]['total_worked']
                    
                    # Récupérer temps estimé
                    temps_estime = 0
                    try:
                        metadonnees = json.loads(bt['metadonnees_json'] or '{}')
                        temps_estime = metadonnees.get('temps_estime_total', 0)
                    except:
                        pass
                    
                    # Calculer progression
                    if temps_estime > 0:
                        progression = min(100, (total_worked / temps_estime) * 100)
                    else:
                        # Si pas d'estimation, utiliser un calcul basique
                        progression = min(100, total_worked * 12.5)  # 8h = 100%
                    
                    # Mettre à jour ou créer l'avancement global
                    existing = self.execute_query(
                        "SELECT id FROM bt_avancement WHERE bt_id = ? AND operation_id IS NULL",
                        (bt_id,)
                    )
                    
                    if existing:
                        self.execute_update(
                            "UPDATE bt_avancement SET pourcentage_realise = ?, updated_at = CURRENT_TIMESTAMP WHERE bt_id = ? AND operation_id IS NULL",
                            (progression, bt_id)
                        )
                    else:
                        self.execute_insert(
                            "INSERT INTO bt_avancement (bt_id, pourcentage_realise) VALUES (?, ?)",
                            (bt_id, progression)
                        )
                    
                    count += 1
            
            logger.info(f"✅ {count} progressions BT recalculées")
            return count
        except Exception as e:
            logger.error(f"Erreur recalcul progressions: {e}")
            return 0

    def sync_bt_timetracker_data(self) -> None:
        """Synchronise les données BT ↔ TimeTracker"""
        try:
            # 1. Corriger les coûts manquants
            missing_costs = self.execute_update("""
                UPDATE time_entries 
                SET total_cost = total_hours * COALESCE(hourly_rate, 95.0)
                WHERE formulaire_bt_id IS NOT NULL 
                AND total_hours IS NOT NULL 
                AND total_cost IS NULL
            """)
            
            # 2. Corriger les taux horaires manquants
            missing_rates = self.execute_update("""
                UPDATE time_entries 
                SET hourly_rate = 95.0
                WHERE formulaire_bt_id IS NOT NULL 
                AND hourly_rate IS NULL
            """)
            
            # 3. Mettre à jour les progressions
            updated_progress = self.recalculate_all_bt_progress()
            
            # 4. Synchroniser les statuts de BT
            bt_status_updates = self.execute_update("""
                UPDATE formulaires 
                SET statut = 'EN COURS'
                WHERE type_formulaire = 'BON_TRAVAIL'
                AND statut = 'VALIDÉ'
                AND id IN (
                    SELECT DISTINCT formulaire_bt_id 
                    FROM time_entries 
                    WHERE formulaire_bt_id IS NOT NULL 
                    AND total_cost IS NOT NULL
                )
            """)
            
            logger.info(f"✅ Synchronisation terminée: {missing_costs} coûts, {missing_rates} taux, {updated_progress} progressions, {bt_status_updates} statuts")
        except Exception as e:
            logger.error(f"Erreur synchronisation: {e}")

    def cleanup_empty_bt_sessions(self) -> int:
        """Nettoie les sessions TimeTracker orphelines/vides sur BTs"""
        try:
            # 1. Sessions sans punch_out anciennes (>24h)
            cutoff_24h = datetime.now() - timedelta(hours=24)
            old_sessions = self.execute_update("""
                DELETE FROM time_entries 
                WHERE formulaire_bt_id IS NOT NULL 
                AND punch_out IS NULL 
                AND punch_in < ?
            """, (cutoff_24h.isoformat(),))
            
            # 2. Sessions avec 0 heures
            zero_hour_sessions = self.execute_update("""
                DELETE FROM time_entries 
                WHERE formulaire_bt_id IS NOT NULL 
                AND (total_hours IS NULL OR total_hours <= 0)
                AND punch_out IS NOT NULL
            """)
            
            # 3. Sessions liées à des BTs inexistants
            orphan_sessions = self.execute_update("""
                DELETE FROM time_entries 
                WHERE formulaire_bt_id IS NOT NULL 
                AND formulaire_bt_id NOT IN (
                    SELECT id FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL'
                )
            """)
            
            total_cleaned = old_sessions + zero_hour_sessions + orphan_sessions
            logger.info(f"✅ {total_cleaned} session(s) nettoyée(s) ({old_sessions} anciennes + {zero_hour_sessions} vides + {orphan_sessions} orphelines)")
            return total_cleaned
        except Exception as e:
            logger.error(f"Erreur nettoyage sessions: {e}")
            return 0

    # =========================================================================
    # MÉTHODES SPÉCIFIQUES AUX POSTES DE TRAVAIL - INTERFACE UNIFIÉE
    # =========================================================================

    def get_work_center_by_id(self, work_center_id: int) -> Optional[Dict]:
        """Récupère un poste de travail par son ID avec détails complets"""
        try:
            query = '''
                SELECT wc.*, 
                       COUNT(DISTINCT o.id) as operations_count,
                       COUNT(DISTINCT te.id) as timetracker_entries,
                       COALESCE(SUM(te.total_hours), 0) as total_hours_tracked,
                       COALESCE(SUM(te.total_cost), 0) as total_revenue_generated,
                       COALESCE(AVG(te.hourly_rate), wc.cout_horaire) as avg_actual_rate
                FROM work_centers wc
                LEFT JOIN operations o ON wc.id = o.work_center_id
                LEFT JOIN time_entries te ON o.id = te.operation_id AND te.total_cost IS NOT NULL
                WHERE wc.id = ?
                GROUP BY wc.id
            '''
            result = self.execute_query(query, (work_center_id,))
            return dict(result[0]) if result else None
        except Exception as e:
            logger.error(f"Erreur récupération poste {work_center_id}: {e}")
            return None

    def get_work_center_by_name(self, work_center_name: str) -> Optional[Dict]:
        """Récupère un poste de travail par son nom avec statistiques"""
        try:
            query = '''
                SELECT wc.*, 
                       COUNT(DISTINCT o.id) as operations_count,
                       COUNT(DISTINCT te.id) as timetracker_entries,
                       COALESCE(SUM(te.total_hours), 0) as total_hours_tracked,
                       COALESCE(SUM(te.total_cost), 0) as total_revenue_generated
                FROM work_centers wc
                LEFT JOIN operations o ON wc.id = o.work_center_id
                LEFT JOIN time_entries te ON o.id = te.operation_id AND te.total_cost IS NOT NULL
                WHERE wc.nom = ?
                GROUP BY wc.id
            '''
            result = self.execute_query(query, (work_center_name,))
            return dict(result[0]) if result else None
        except Exception as e:
            logger.error(f"Erreur récupération poste '{work_center_name}': {e}")
            return None

    def add_work_center(self, work_center_data: Dict) -> Optional[int]:
        """Ajoute un nouveau poste de travail avec validation"""
        try:
            # Validation des données requises
            required_fields = ['nom', 'departement', 'categorie']
            for field in required_fields:
                if field not in work_center_data or not work_center_data[field]:
                    raise ValueError(f"Champ requis manquant: {field}")
            
            # Vérifier l'unicité du nom
            existing = self.get_work_center_by_name(work_center_data['nom'])
            if existing:
                raise ValueError(f"Un poste avec le nom '{work_center_data['nom']}' existe déjà")
            
            query = '''
                INSERT INTO work_centers 
                (nom, departement, categorie, type_machine, capacite_theorique, 
                 operateurs_requis, cout_horaire, competences_requises, statut, localisation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            work_center_id = self.execute_insert(query, (
                work_center_data['nom'],
                work_center_data['departement'],
                work_center_data.get('categorie', ''),
                work_center_data.get('type_machine', ''),
                work_center_data.get('capacite_theorique', 8.0),
                work_center_data.get('operateurs_requis', 1),
                work_center_data.get('cout_horaire', 50.0),
                work_center_data.get('competences_requises', '[]'),
                work_center_data.get('statut', 'ACTIF'),
                work_center_data.get('localisation', '')
            ))
            
            logger.info(f"Poste de travail créé: ID={work_center_id}, nom={work_center_data['nom']}")
            return work_center_id
            
        except Exception as e:
            logger.error(f"Erreur ajout poste de travail: {e}")
            return None

    def get_work_centers_statistics(self) -> Dict[str, Any]:
        """Statistiques complètes des postes de travail pour interface unifiée"""
        try:
            stats = {
                'total_work_centers': 0,
                'by_department': {},
                'by_category': {},
                'by_status': {},
                'capacity_analysis': {},
                'timetracker_integration': {},
                'cost_analysis': {}
            }
            
            # Statistiques de base
            basic_stats = self.execute_query('''
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN statut = 'ACTIF' THEN 1 END) as actif,
                    COUNT(CASE WHEN statut = 'MAINTENANCE' THEN 1 END) as maintenance,
                    COUNT(CASE WHEN statut = 'INACTIF' THEN 1 END) as inactif,
                    SUM(capacite_theorique) as capacite_totale,
                    AVG(capacite_theorique) as capacite_moyenne,
                    SUM(cout_horaire * capacite_theorique) as cout_total_theorique,
                    AVG(cout_horaire) as cout_horaire_moyen
                FROM work_centers
            ''')
            
            if basic_stats:
                base = dict(basic_stats[0])
                stats['total_work_centers'] = base['total']
                stats['by_status'] = {
                    'ACTIF': base['actif'],
                    'MAINTENANCE': base['maintenance'], 
                    'INACTIF': base['inactif']
                }
                stats['capacity_analysis'] = {
                    'capacite_totale_heures_jour': base['capacite_totale'],
                    'capacite_moyenne_par_poste': base['capacite_moyenne'],
                    'cout_total_theorique_jour': base['cout_total_theorique'],
                    'cout_horaire_moyen': base['cout_horaire_moyen']
                }
            
            # Par département
            dept_stats = self.execute_query('''
                SELECT departement, COUNT(*) as count, 
                       SUM(capacite_theorique) as capacite,
                       AVG(cout_horaire) as cout_moyen
                FROM work_centers 
                GROUP BY departement
                ORDER BY count DESC
            ''')
            stats['by_department'] = {row['departement']: dict(row) for row in dept_stats}
            
            # Par catégorie
            cat_stats = self.execute_query('''
                SELECT categorie, COUNT(*) as count,
                       SUM(capacite_theorique) as capacite,
                       AVG(cout_horaire) as cout_moyen
                FROM work_centers 
                GROUP BY categorie
                ORDER BY count DESC
            ''')
            stats['by_category'] = {row['categorie']: dict(row) for row in cat_stats}
            
            # Intégration TimeTracker
            tt_stats = self.execute_query('''
                SELECT 
                    COUNT(DISTINCT wc.id) as postes_avec_pointages,
                    COUNT(DISTINCT te.id) as total_pointages,
                    COALESCE(SUM(te.total_hours), 0) as total_heures,
                    COALESCE(SUM(te.total_cost), 0) as total_revenus,
                    COUNT(DISTINCT te.employee_id) as employes_ayant_pointe
                FROM work_centers wc
                LEFT JOIN operations o ON wc.id = o.work_center_id
                LEFT JOIN time_entries te ON o.id = te.operation_id AND te.total_cost IS NOT NULL
            ''')
            
            if tt_stats:
                tt_data = dict(tt_stats[0])
                stats['timetracker_integration'] = tt_data
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur statistiques postes de travail: {e}")
            return {}

    # =========================================================================
    # MÉTHODES POUR GAMMES DE FABRICATION - INTERFACE UNIFIÉE
    # =========================================================================

    def create_operation_for_bt(self, bt_id: int, operation_data: Dict) -> Optional[int]:
        """Crée une opération spécifiquement liée à un Bon de Travail"""
        try:
            # Vérifier que le BT existe et récupérer le project_id
            bt_info = self.execute_query(
                "SELECT project_id FROM formulaires WHERE id = ? AND type_formulaire = 'BON_TRAVAIL'",
                (bt_id,)
            )
            
            if not bt_info:
                logger.error(f"BT {bt_id} non trouvé ou n'est pas un Bon de Travail")
                return None
            
            project_id = bt_info[0]['project_id']
            
            # Trouver le work_center_id par nom si fourni
            work_center_id = None
            if operation_data.get('poste_travail'):
                wc_result = self.execute_query(
                    "SELECT id FROM work_centers WHERE nom = ?",
                    (operation_data['poste_travail'],)
                )
                work_center_id = wc_result[0]['id'] if wc_result else None
            
            # Créer l'opération
            query = '''
                INSERT INTO operations 
                (project_id, work_center_id, formulaire_bt_id, sequence_number, description, 
                 temps_estime, ressource, statut, poste_travail)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            operation_id = self.execute_insert(query, (
                project_id,
                work_center_id,
                bt_id,
                operation_data.get('sequence_number', 1),
                operation_data.get('description', ''),
                operation_data.get('temps_estime', 0.0),
                operation_data.get('ressource', ''),
                operation_data.get('statut', 'À FAIRE'),
                operation_data.get('poste_travail', '')
            ))
            
            logger.info(f"✅ Opération créée pour BT #{bt_id}: operation_id={operation_id}")
            return operation_id
            
        except Exception as e:
            logger.error(f"Erreur création opération pour BT: {e}")
            return None

    def get_operations_by_bt(self, bt_id: int) -> List[Dict]:
        """Récupère toutes les opérations liées à un Bon de Travail"""
        try:
            query = '''
                SELECT o.*, 
                       wc.nom as work_center_name, 
                       wc.departement as work_center_departement,
                       wc.capacite_theorique,
                       wc.cout_horaire as work_center_cout_horaire,
                       p.nom_projet
                FROM operations o
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                LEFT JOIN projects p ON o.project_id = p.id
                WHERE o.formulaire_bt_id = ?
                ORDER BY o.sequence_number, o.id
            '''
            rows = self.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération opérations BT {bt_id}: {e}")
            return []

    def get_bts_with_operations(self) -> List[Dict]:
        """Récupère tous les BTs qui ont des opérations liées"""
        try:
            query = '''
                SELECT f.id as bt_id, f.numero_document, f.statut as bt_statut,
                       p.nom_projet, c.nom as company_nom,
                       COUNT(o.id) as nb_operations,
                       COALESCE(SUM(o.temps_estime), 0) as temps_total_estime,
                       GROUP_CONCAT(DISTINCT wc.nom) as postes_utilises
                FROM formulaires f
                LEFT JOIN projects p ON f.project_id = p.id
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN operations o ON f.id = o.formulaire_bt_id
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                AND o.id IS NOT NULL
                GROUP BY f.id
                ORDER BY f.numero_document
            '''
            rows = self.execute_query(query)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération BTs avec opérations: {e}")
            return []

    # =========================================================================
    # MÉTHODES SPÉCIFIQUES MODULE PRODUCTION UNIFIÉ - ÉTAPE 3
    # =========================================================================
    
    def get_materials_by_project(self, project_id: str) -> List[Dict]:
        """Récupère tous les matériaux d'un projet pour BOM"""
        try:
            query = '''
                SELECT m.*, p.nom_projet
                FROM materials m
                LEFT JOIN projects p ON m.project_id = p.id
                WHERE m.project_id = ?
                ORDER BY m.id
            '''
            rows = self.execute_query(query, (str(project_id),))
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération matériaux projet {project_id}: {e}")
            return []
    
    def get_project_operations_with_work_centers(self, project_id: str) -> List[Dict]:
        """Récupère les opérations d'un projet avec informations postes de travail"""
        try:
            query = '''
                SELECT o.*, 
                       wc.nom as work_center_name, 
                       wc.departement as work_center_departement,
                       wc.capacite_theorique,
                       wc.cout_horaire as work_center_cout_horaire,
                       wc.operateurs_requis,
                       wc.competences_requises,
                       wc.statut as work_center_statut,
                       f.numero_document as bt_numero,
                       f.statut as bt_statut
                FROM operations o
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                LEFT JOIN formulaires f ON o.formulaire_bt_id = f.id AND f.type_formulaire = 'BON_TRAVAIL'
                WHERE o.project_id = ?
                ORDER BY o.sequence_number, o.id
            '''
            rows = self.execute_query(query, (str(project_id),))
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération opérations projet avec postes: {e}")
            return []

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques principales pour le dashboard unifié"""
        try:
            metrics = {
                'projects': {'total': 0, 'actifs': 0, 'ca_total': 0.0},
                'formulaires': {'total': 0, 'en_attente': 0, 'montant_total': 0.0},
                'inventory': {'total_items': 0, 'stocks_critiques': 0},
                'fournisseurs': {'total': 0, 'actifs': 0},
                'employees': {'total': 0, 'actifs': 0},
                'bt_specialise': {'total': 0, 'assignations': 0, 'postes_reserves': 0},
                'timetracker_bt_integration': {'total_pointages_bt': 0, 'heures_bt': 0.0, 'cout_bt': 0.0},
                'work_centers_unified': {
                    'total_postes': 0,
                    'postes_actifs': 0,
                    'capacite_totale_jour': 0.0,
                    'utilisation_moyenne': 0.0,
                    'revenus_generes': 0.0,
                    'goulots_detectes': 0
                },
                'production_unified': {
                    'projets_avec_bom': 0,
                    'projets_avec_itineraires': 0,
                    'materiaux_total': 0,
                    'operations_total': 0,
                    'valeur_bom_total': 0.0,
                    'temps_planifie_total': 0.0
                },
                'operations_bt_integration': {
                    'operations_liees_bt': 0,
                    'bt_avec_operations': 0,
                    'temps_operations_bt': 0.0,
                    'postes_utilises_bt': 0
                },
                'communication_tt_integration': {
                    'methodes_disponibles': 6,
                    'integration_active': True,
                    'derniere_sync': datetime.now().isoformat()
                }
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
            
            # Métriques intégration TimeTracker ↔ BT
            result = self.execute_query('''
                SELECT 
                    COUNT(*) as total_pointages_bt,
                    COALESCE(SUM(total_hours), 0) as heures_bt,
                    COALESCE(SUM(total_cost), 0) as cout_bt
                FROM time_entries 
                WHERE formulaire_bt_id IS NOT NULL
            ''')
            if result:
                metrics['timetracker_bt_integration']['total_pointages_bt'] = result[0]['total_pointages_bt']
                metrics['timetracker_bt_integration']['heures_bt'] = round(result[0]['heures_bt'], 1)
                metrics['timetracker_bt_integration']['cout_bt'] = round(result[0]['cout_bt'], 2)
            
            # Métriques postes de travail unifiées
            wc_stats_result = self.execute_query('''
                SELECT 
                    COUNT(*) as total_postes,
                    COUNT(CASE WHEN statut = 'ACTIF' THEN 1 END) as postes_actifs,
                    COALESCE(SUM(capacite_theorique), 0) as capacite_totale,
                    COALESCE(AVG(CASE WHEN utilization_rate_30d > 0 THEN utilization_rate_30d END), 0) as utilisation_moyenne
                FROM view_work_centers_with_stats
            ''')
            
            if wc_stats_result:
                wc_data = dict(wc_stats_result[0])
                metrics['work_centers_unified'].update({
                    'total_postes': wc_data['total_postes'],
                    'postes_actifs': wc_data['postes_actifs'],
                    'capacite_totale_jour': wc_data['capacite_totale'],
                    'utilisation_moyenne': wc_data['utilisation_moyenne']
                })
            
            # Revenus générés par les postes
            revenue_result = self.execute_query('''
                SELECT COALESCE(SUM(total_revenue_generated), 0) as total_revenue
                FROM view_work_centers_with_stats
            ''')
            if revenue_result:
                metrics['work_centers_unified']['revenus_generes'] = revenue_result[0]['total_revenue']
            
            # Métriques production unifiées
            production_metrics = self.get_production_dashboard_metrics()
            if production_metrics:
                metrics['production_unified'] = {
                    'projets_avec_bom': production_metrics.get('nomenclatures', {}).get('projets_avec_bom', 0),
                    'projets_avec_itineraires': production_metrics.get('itineraires', {}).get('projets_avec_operations', 0),
                    'materiaux_total': production_metrics.get('nomenclatures', {}).get('materiaux_total', 0),
                    'operations_total': production_metrics.get('itineraires', {}).get('operations_total', 0),
                    'valeur_bom_total': production_metrics.get('nomenclatures', {}).get('valeur_moyenne_bom', 0.0),
                    'temps_planifie_total': production_metrics.get('itineraires', {}).get('temps_total_planifie', 0.0)
                }
            
            # Métriques Operations ↔ BT
            operations_bt_result = self.execute_query('''
                SELECT 
                    COUNT(*) as operations_liees_bt,
                    COUNT(DISTINCT formulaire_bt_id) as bt_avec_operations,
                    COALESCE(SUM(temps_estime), 0) as temps_operations_bt,
                    COUNT(DISTINCT work_center_id) as postes_utilises_bt
                FROM operations 
                WHERE formulaire_bt_id IS NOT NULL
            ''')
            if operations_bt_result:
                ops_bt_data = dict(operations_bt_result[0])
                metrics['operations_bt_integration'].update(ops_bt_data)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Erreur métriques dashboard unifié: {e}")
            return {}

    def get_production_dashboard_metrics(self) -> Dict[str, Any]:
        """Métriques spécifiques pour le dashboard du module production unifié"""
        try:
            metrics = {
                'inventaire': {
                    'total_articles': 0,
                    'articles_critiques': 0,
                    'valeur_totale_stock': 0.0,
                    'articles_sans_stock': 0
                },
                'nomenclatures': {
                    'projets_avec_bom': 0,
                    'materiaux_total': 0,
                    'valeur_moyenne_bom': 0.0,
                    'fournisseurs_utilises': 0
                },
                'itineraires': {
                    'projets_avec_operations': 0,
                    'operations_total': 0,
                    'temps_total_planifie': 0.0,
                    'postes_utilises': 0
                }
            }
            
            # Métriques inventaire
            inv_result = self.execute_query('''
                SELECT 
                    COUNT(*) as total_articles,
                    COUNT(CASE WHEN statut IN ('CRITIQUE', 'FAIBLE', 'ÉPUISÉ') THEN 1 END) as articles_critiques,
                    COUNT(CASE WHEN quantite_metric <= 0.001 THEN 1 END) as articles_sans_stock
                FROM inventory_items
            ''')
            if inv_result:
                metrics['inventaire'].update(dict(inv_result[0]))
            
            # Métriques nomenclatures
            bom_result = self.execute_query('''
                SELECT 
                    COUNT(DISTINCT project_id) as projets_avec_bom,
                    COUNT(*) as materiaux_total,
                    COALESCE(AVG(quantite * prix_unitaire), 0) as valeur_moyenne_bom,
                    COUNT(DISTINCT fournisseur) as fournisseurs_utilises
                FROM materials
                WHERE project_id IS NOT NULL
            ''')
            if bom_result:
                metrics['nomenclatures'].update(dict(bom_result[0]))
            
            # Métriques itinéraires
            routing_result = self.execute_query('''
                SELECT 
                    COUNT(DISTINCT project_id) as projets_avec_operations,
                    COUNT(*) as operations_total,
                    COALESCE(SUM(temps_estime), 0) as temps_total_planifie,
                    COUNT(DISTINCT work_center_id) as postes_utilises
                FROM operations
                WHERE project_id IS NOT NULL
            ''')
            if routing_result:
                metrics['itineraires'].update(dict(routing_result[0]))
            
            return metrics
            
        except Exception as e:
            logger.error(f"Erreur métriques dashboard production: {e}")
            return {}

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
                'bt_statistiques': {'total_bt': 0, 'assignations': 0, 'postes_reserves': 0},
                'bt_timetracker_stats': {}
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
            
            # Statistiques BT ↔ TimeTracker
            query_bt_tt = '''
                SELECT 
                    COUNT(DISTINCT te.formulaire_bt_id) as bt_avec_pointages,
                    COUNT(te.id) as total_sessions_bt,
                    COALESCE(SUM(te.total_hours), 0) as total_heures_bt,
                    COALESCE(SUM(te.total_cost), 0) as total_cout_bt,
                    COALESCE(AVG(te.total_hours), 0) as moyenne_heures_session
                FROM time_entries te
                WHERE te.formulaire_bt_id IS NOT NULL
            '''
            result_bt_tt = self.execute_query(query_bt_tt)
            if result_bt_tt:
                stats['bt_timetracker_stats'] = dict(result_bt_tt[0])
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur statistiques formulaires: {e}")
            return {}

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
                
                # Ajouter les statistiques TimeTracker
                formulaire['timetracker_stats'] = self.get_statistiques_bt_timetracker(formulaire_id)
                
                # Ajouter les opérations liées au BT
                formulaire['operations_bt'] = self.get_operations_by_bt(formulaire_id)
            
            return formulaire
            
        except Exception as e:
            logger.error(f"Erreur récupération formulaire détaillé: {e}")
            return {}

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
    # MÉTHODES COMPLÉMENTAIRES ET UTILITAIRES
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

    def get_inventory_items_for_bom(self, search_term: str = None) -> List[Dict]:
        """Récupère les articles d'inventaire pour sélection dans BOM"""
        try:
            query = '''
                SELECT id, nom, type_produit, quantite_imperial, quantite_metric,
                       statut, description, fournisseur_principal, code_interne
                FROM inventory_items
            '''
            params = []
            
            if search_term:
                query += " WHERE nom LIKE ? OR code_interne LIKE ? OR description LIKE ?"
                pattern = f"%{search_term}%"
                params = [pattern, pattern, pattern]
            
            query += " ORDER BY nom"
            
            rows = self.execute_query(query, tuple(params) if params else None)
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur récupération articles inventaire pour BOM: {e}")
            return []

    def get_projects_summary_for_production(self) -> List[Dict]:
        """Récupère un résumé des projets pour le module production"""
        try:
            query = '''
                SELECT p.id, p.nom_projet, p.client_nom_cache, p.statut, p.priorite,
                       p.date_soumis, p.date_prevu, p.prix_estime,
                       COUNT(DISTINCT m.id) as nb_materiaux,
                       COUNT(DISTINCT o.id) as nb_operations,
                       COALESCE(SUM(m.quantite * m.prix_unitaire), 0) as cout_materiaux,
                       COALESCE(SUM(o.temps_estime), 0) as temps_total_estime
                FROM projects p
                LEFT JOIN materials m ON p.id = m.project_id
                LEFT JOIN operations o ON p.id = o.project_id
                GROUP BY p.id
                ORDER BY p.id DESC
            '''
            
            rows = self.execute_query(query)
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur récupération résumé projets production: {e}")
            return []

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
                    WHERE o.project_id IS NOT NULL
                    AND o.project_id NOT IN (SELECT id FROM projects)
                ''')
                checks['operations_projects_fk'] = cursor.fetchone()['orphans'] == 0
                
                # Operations → Work Centers
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM operations o
                    WHERE o.work_center_id IS NOT NULL
                    AND o.work_center_id NOT IN (SELECT id FROM work_centers)
                ''')
                checks['operations_work_centers_fk'] = cursor.fetchone()['orphans'] == 0
                
                # Operations → Formulaires BT
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM operations o
                    WHERE o.formulaire_bt_id IS NOT NULL
                    AND o.formulaire_bt_id NOT IN (SELECT id FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL')
                ''')
                checks['operations_bt_fk'] = cursor.fetchone()['orphans'] == 0
                
                # Materials → Projects
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM materials m
                    WHERE m.project_id IS NOT NULL
                    AND m.project_id NOT IN (SELECT id FROM projects)
                ''')
                checks['materials_projects_fk'] = cursor.fetchone()['orphans'] == 0
                
                # Time entries avec BT → Formulaires BT
                cursor.execute('''
                    SELECT COUNT(*) as orphans FROM time_entries te
                    WHERE te.formulaire_bt_id IS NOT NULL 
                    AND te.formulaire_bt_id NOT IN (
                        SELECT id FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL'
                    )
                ''')
                checks['time_entries_bt_fk'] = cursor.fetchone()['orphans'] == 0
                
        except Exception as e:
            logger.error(f"Erreur validation intégrité: {e}")
            checks['error'] = str(e)
        
        return checks

    # =========================================================================
    # MÉTHODES MANQUANTES DU FICHIER ORIGINAL - AJOUTÉES
    # =========================================================================

    def update_work_center(self, work_center_id: int, work_center_data: Dict) -> bool:
        """Met à jour un poste de travail existant"""
        try:
            # Vérifier que le poste existe
            existing = self.get_work_center_by_id(work_center_id)
            if not existing:
                raise ValueError(f"Poste de travail {work_center_id} non trouvé")
            
            # Vérifier l'unicité du nom si changé
            if 'nom' in work_center_data and work_center_data['nom'] != existing['nom']:
                name_check = self.get_work_center_by_name(work_center_data['nom'])
                if name_check and name_check['id'] != work_center_id:
                    raise ValueError(f"Un autre poste avec le nom '{work_center_data['nom']}' existe déjà")
            
            query = '''
                UPDATE work_centers SET
                nom = ?, departement = ?, categorie = ?, type_machine = ?,
                capacite_theorique = ?, operateurs_requis = ?, cout_horaire = ?,
                competences_requises = ?, statut = ?, localisation = ?
                WHERE id = ?
            '''
            
            affected = self.execute_update(query, (
                work_center_data.get('nom', existing['nom']),
                work_center_data.get('departement', existing['departement']),
                work_center_data.get('categorie', existing['categorie']),
                work_center_data.get('type_machine', existing['type_machine']),
                work_center_data.get('capacite_theorique', existing['capacite_theorique']),
                work_center_data.get('operateurs_requis', existing['operateurs_requis']),
                work_center_data.get('cout_horaire', existing['cout_horaire']),
                work_center_data.get('competences_requises', existing['competences_requises']),
                work_center_data.get('statut', existing['statut']),
                work_center_data.get('localisation', existing['localisation']),
                work_center_id
            ))
            
            logger.info(f"Poste de travail mis à jour: ID={work_center_id}")
            return affected > 0
            
        except Exception as e:
            logger.error(f"Erreur mise à jour poste {work_center_id}: {e}")
            return False

    def delete_work_center(self, work_center_id: int) -> bool:
        """Supprime un poste de travail avec vérification des dépendances"""
        try:
            # Vérifier les dépendances - opérations
            operations_count = self.execute_query(
                "SELECT COUNT(*) as count FROM operations WHERE work_center_id = ?",
                (work_center_id,)
            )
            if operations_count and operations_count[0]['count'] > 0:
                raise ValueError(f"Impossible de supprimer: {operations_count[0]['count']} opération(s) liée(s)")
            
            # Vérifier les dépendances - réservations BT
            reservations_count = self.execute_query(
                "SELECT COUNT(*) as count FROM bt_reservations_postes WHERE work_center_id = ?",
                (work_center_id,)
            )
            if reservations_count and reservations_count[0]['count'] > 0:
                raise ValueError(f"Impossible de supprimer: {reservations_count[0]['count']} réservation(s) BT active(s)")
            
            affected = self.execute_update("DELETE FROM work_centers WHERE id = ?", (work_center_id,))
            
            logger.info(f"Poste de travail supprimé: ID={work_center_id}")
            return affected > 0
            
        except Exception as e:
            logger.error(f"Erreur suppression poste {work_center_id}: {e}")
            return False

    def get_work_center_utilization_analysis(self, period_days: int = 30) -> List[Dict]:
        """Analyse d'utilisation des postes de travail avec TimeTracker"""
        try:
            start_date = (datetime.now() - timedelta(days=period_days)).strftime('%Y-%m-%d')
            
            query = '''
                SELECT 
                    wc.id, wc.nom, wc.departement, wc.categorie, wc.type_machine,
                    wc.capacite_theorique, wc.cout_horaire, wc.operateurs_requis,
                    COALESCE(SUM(te.total_hours), 0) as heures_reelles,
                    COALESCE(SUM(te.total_cost), 0) as revenus_generes,
                    COALESCE(AVG(te.hourly_rate), wc.cout_horaire) as taux_horaire_reel,
                    COUNT(DISTINCT te.id) as nombre_pointages,
                    COUNT(DISTINCT te.employee_id) as employes_distincts,
                    COUNT(DISTINCT o.project_id) as projets_touches,
                    -- Calcul du taux d'utilisation
                    CASE 
                        WHEN wc.capacite_theorique > 0 THEN
                            ROUND((COALESCE(SUM(te.total_hours), 0) / (wc.capacite_theorique * ?)) * 100, 2)
                        ELSE 0
                    END as taux_utilisation_pct
                FROM work_centers wc
                LEFT JOIN operations o ON wc.id = o.work_center_id
                LEFT JOIN time_entries te ON o.id = te.operation_id 
                    AND te.total_cost IS NOT NULL 
                    AND DATE(te.punch_in) >= ?
                WHERE wc.statut = 'ACTIF'
                GROUP BY wc.id
                ORDER BY heures_reelles DESC
            '''
            
            rows = self.execute_query(query, (period_days, start_date))
            
            analysis = []
            for row in rows:
                data = dict(row)
                
                # Calculs additionnels
                if data['heures_reelles'] > 0:
                    data['efficacite_cout'] = data['revenus_generes'] / data['heures_reelles']
                    data['rentabilite_vs_theorique'] = (data['efficacite_cout'] / data['cout_horaire']) * 100 if data['cout_horaire'] > 0 else 0
                else:
                    data['efficacite_cout'] = 0
                    data['rentabilite_vs_theorique'] = 0
                
                # Classification d'utilisation
                utilisation = data['taux_utilisation_pct']
                if utilisation >= 80:
                    data['classification_utilisation'] = 'ÉLEVÉE'
                elif utilisation >= 50:
                    data['classification_utilisation'] = 'MOYENNE'
                elif utilisation >= 20:
                    data['classification_utilisation'] = 'FAIBLE'
                else:
                    data['classification_utilisation'] = 'TRÈS_FAIBLE'
                
                analysis.append(data)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erreur analyse utilisation postes: {e}")
            return []

    def get_work_center_capacity_bottlenecks(self) -> List[Dict]:
        """Identifie les goulots d'étranglement dans les postes de travail"""
        try:
            query = '''
                SELECT 
                    wc.id, wc.nom, wc.departement, wc.categorie,
                    wc.capacite_theorique, wc.operateurs_requis,
                    -- Charge planifiée (opérations en cours)
                    COALESCE(SUM(CASE WHEN o.statut IN ('À FAIRE', 'EN COURS') THEN o.temps_estime ELSE 0 END), 0) as charge_planifiee,
                    -- Charge réelle (TimeTracker)
                    COALESCE(SUM(CASE WHEN te.punch_out IS NULL THEN 
                        (JULIANDAY('now') - JULIANDAY(te.punch_in)) * 24 
                    ELSE 0 END), 0) as charge_en_cours,
                    COUNT(CASE WHEN o.statut IN ('À FAIRE', 'EN COURS') THEN 1 END) as operations_en_attente,
                    COUNT(CASE WHEN te.punch_out IS NULL THEN 1 END) as pointages_actifs,
                    -- Calcul du taux de charge
                    CASE 
                        WHEN wc.capacite_theorique > 0 THEN
                            ROUND(((COALESCE(SUM(CASE WHEN o.statut IN ('À FAIRE', 'EN COURS') THEN o.temps_estime ELSE 0 END), 0) / 
                                   (wc.capacite_theorique * 5)) * 100), 2) -- Sur 5 jours
                        ELSE 0
                    END as taux_charge_planifiee_pct
                FROM work_centers wc
                LEFT JOIN operations o ON wc.id = o.work_center_id
                LEFT JOIN time_entries te ON o.id = te.operation_id
                WHERE wc.statut = 'ACTIF'
                GROUP BY wc.id
                HAVING taux_charge_planifiee_pct > 70  -- Seuil de goulot d'étranglement
                ORDER BY taux_charge_planifiee_pct DESC
            '''
            
            rows = self.execute_query(query)
            
            bottlenecks = []
            for row in rows:
                data = dict(row)
                
                # Classification du niveau de goulot
                charge = data['taux_charge_planifiee_pct']
                if charge >= 100:
                    data['niveau_goulot'] = 'CRITIQUE'
                    data['priorite'] = 1
                elif charge >= 90:
                    data['niveau_goulot'] = 'ÉLEVÉ'
                    data['priorite'] = 2
                elif charge >= 80:
                    data['niveau_goulot'] = 'MODÉRÉ'
                    data['priorite'] = 3
                else:
                    data['niveau_goulot'] = 'FAIBLE'
                    data['priorite'] = 4
                
                # Recommandations automatiques
                recommendations = []
                if data['operations_en_attente'] > 5:
                    recommendations.append("Réorganiser la séquence des opérations")
                if data['pointages_actifs'] > data['operateurs_requis']:
                    recommendations.append("Surcharge d'opérateurs détectée")
                if charge >= 100:
                    recommendations.append("Considérer des heures supplémentaires")
                    recommendations.append("Évaluer la sous-traitance")
                
                data['recommandations'] = recommendations
                bottlenecks.append(data)
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"Erreur analyse goulots postes: {e}")
            return []

    def create_manufacturing_route(self, project_id: str, route_data: Dict) -> int:
        """Crée une gamme de fabrication complète pour un projet"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Créer les opérations de la gamme
                created_operations = []
                bt_id = route_data.get('formulaire_bt_id')  # Récupérer le BT lié si fourni
                
                for operation_data in route_data.get('operations', []):
                    # Trouver le work_center_id par nom
                    wc_result = self.execute_query(
                        "SELECT id FROM work_centers WHERE nom = ?",
                        (operation_data['poste_travail'],)
                    )
                    work_center_id = wc_result[0]['id'] if wc_result else None
                    
                    op_query = '''
                        INSERT INTO operations 
                        (project_id, work_center_id, formulaire_bt_id, sequence_number, description, 
                         temps_estime, ressource, statut, poste_travail)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    '''
                    
                    op_id = self.execute_insert(op_query, (
                        str(project_id),
                        work_center_id,
                        bt_id,
                        operation_data.get('sequence_number', 0),
                        operation_data.get('description', ''),
                        operation_data.get('temps_estime', 0.0),
                        operation_data.get('ressource', ''),
                        operation_data.get('statut', 'À FAIRE'),
                        operation_data['poste_travail']
                    ))
                    
                    created_operations.append(op_id)
                
                logger.info(f"Gamme créée pour projet {project_id}: {len(created_operations)} opérations{' (liées au BT #' + str(bt_id) + ')' if bt_id else ''}")
                return len(created_operations)
                
        except Exception as e:
            logger.error(f"Erreur création gamme projet {project_id}: {e}")
            return 0

    def get_manufacturing_route_templates(self) -> Dict[str, Any]:
        """Récupère les templates de gammes disponibles avec validation postes"""
        try:
            # Templates de base
            templates = {
                "CHASSIS_SOUDE": {
                    "nom": "Châssis Soudé",
                    "description": "Châssis métallique avec soudage",
                    "operations": [
                        {"sequence": "10", "poste": "Programmation Bureau", "description": "Programmation des pièces", "temps_base": 2.5},
                        {"sequence": "20", "poste": "Laser CNC", "description": "Découpe laser des tôles", "temps_base": 4.0},
                        {"sequence": "30", "poste": "Plieuse CNC 1", "description": "Pliage des éléments", "temps_base": 3.5},
                        {"sequence": "40", "poste": "Perçage 1", "description": "Perçage des fixations", "temps_base": 2.0},
                        {"sequence": "50", "poste": "Assemblage Léger 1", "description": "Pré-assemblage", "temps_base": 6.0},
                        {"sequence": "60", "poste": "Robot ABB GMAW", "description": "Soudage robotisé", "temps_base": 8.0},
                        {"sequence": "70", "poste": "Soudage GMAW 1", "description": "Finition soudure", "temps_base": 4.0},
                        {"sequence": "80", "poste": "Meulage 1", "description": "Meulage des cordons", "temps_base": 3.0},
                        {"sequence": "90", "poste": "Contrôle dimensionnel", "description": "Vérification dimensions", "temps_base": 1.5},
                        {"sequence": "100", "poste": "Peinture poudre", "description": "Finition peinture", "temps_base": 2.5}
                    ]
                },
                "STRUCTURE_LOURDE": {
                    "nom": "Structure Lourde", 
                    "description": "Charpente métallique industrielle",
                    "operations": [
                        {"sequence": "10", "poste": "Programmation Bureau", "description": "Étude et programmation", "temps_base": 4.0},
                        {"sequence": "20", "poste": "Plasma CNC", "description": "Découpe plasma gros éléments", "temps_base": 6.0},
                        {"sequence": "30", "poste": "Oxycoupage", "description": "Découpe éléments épais", "temps_base": 8.0},
                        {"sequence": "40", "poste": "Plieuse conventionnelle 1", "description": "Formage éléments", "temps_base": 5.0},
                        {"sequence": "50", "poste": "Perçage 2", "description": "Perçage assemblage", "temps_base": 4.0},
                        {"sequence": "60", "poste": "Assemblage Lourd", "description": "Assemblage structure", "temps_base": 12.0},
                        {"sequence": "70", "poste": "Soudage SAW", "description": "Soudage à l'arc submergé", "temps_base": 10.0},
                        {"sequence": "80", "poste": "Soudage SMAW 1", "description": "Soudage manuel finition", "temps_base": 6.0},
                        {"sequence": "90", "poste": "Meulage 2", "description": "Finition soudures", "temps_base": 4.0},
                        {"sequence": "100", "poste": "Tests non destructifs", "description": "Contrôle soudures", "temps_base": 2.0},
                        {"sequence": "110", "poste": "Galvanisation", "description": "Protection anticorrosion", "temps_base": 3.0}
                    ]
                },
                "PIECE_PRECISION": {
                    "nom": "Pièce de Précision",
                    "description": "Composant haute précision", 
                    "operations": [
                        {"sequence": "10", "poste": "Programmation Bureau", "description": "Programmation complexe", "temps_base": 3.0},
                        {"sequence": "20", "poste": "Sciage métal", "description": "Débit matière", "temps_base": 1.5},
                        {"sequence": "30", "poste": "Tour CNC 1", "description": "Tournage CNC", "temps_base": 5.0},
                        {"sequence": "40", "poste": "Fraiseuse CNC 1", "description": "Fraisage CNC", "temps_base": 6.0},
                        {"sequence": "50", "poste": "Centre d'usinage", "description": "Usinage complexe", "temps_base": 8.0},
                        {"sequence": "60", "poste": "Perçage 1", "description": "Perçage précision", "temps_base": 2.0},
                        {"sequence": "70", "poste": "Taraudage", "description": "Taraudage", "temps_base": 1.5},
                        {"sequence": "80", "poste": "Rectifieuse", "description": "Rectification", "temps_base": 4.0},
                        {"sequence": "90", "poste": "Ébavurage", "description": "Ébavurage", "temps_base": 2.0},
                        {"sequence": "100", "poste": "Polissage", "description": "Polissage", "temps_base": 3.0},
                        {"sequence": "110", "poste": "Contrôle métrologique", "description": "Contrôle dimensions", "temps_base": 2.5},
                        {"sequence": "120", "poste": "Anodisation", "description": "Traitement surface", "temps_base": 2.0}
                    ]
                }
            }
            
            # Valider que tous les postes existent
            for template_key, template in templates.items():
                postes_valides = []
                postes_manquants = []
                
                for operation in template['operations']:
                    poste_nom = operation['poste']
                    poste_exists = self.execute_query(
                        "SELECT id FROM work_centers WHERE nom = ?",
                        (poste_nom,)
                    )
                    
                    if poste_exists:
                        postes_valides.append(poste_nom)
                    else:
                        postes_manquants.append(poste_nom)
                
                template['validation'] = {
                    'postes_valides': postes_valides,
                    'postes_manquants': postes_manquants,
                    'taux_validite': len(postes_valides) / len(template['operations']) * 100 if template['operations'] else 0
                }
            
            return templates
            
        except Exception as e:
            logger.error(f"Erreur récupération templates gammes: {e}")
            return {}

    def optimize_manufacturing_route(self, project_id: str) -> Dict[str, Any]:
        """Optimise une gamme de fabrication existante"""
        try:
            # Récupérer les opérations actuelles
            current_operations = self.execute_query('''
                SELECT o.*, wc.nom as work_center_name, wc.capacite_theorique, 
                       wc.cout_horaire, wc.departement
                FROM operations o
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE o.project_id = ?
                ORDER BY o.sequence_number
            ''', (str(project_id),))
            
            if not current_operations:
                return {'error': 'Aucune opération trouvée pour ce projet'}
            
            optimization_results = {
                'project_id': project_id,
                'current_operations_count': len(current_operations),
                'analysis': {
                    'departements_utilises': set(),
                    'temps_total_estime': 0,
                    'cout_total_estime': 0,
                    'goulots_detectes': [],
                    'suggestions_amelioration': []
                },
                'optimizations': []
            }
            
            # Analyse des opérations actuelles
            for op in current_operations:
                op_dict = dict(op)
                optimization_results['analysis']['departements_utilises'].add(op_dict.get('departement', 'N/A'))
                optimization_results['analysis']['temps_total_estime'] += op_dict.get('temps_estime', 0)
                optimization_results['analysis']['cout_total_estime'] += (op_dict.get('temps_estime', 0) * op_dict.get('cout_horaire', 0))
            
            # Convertir set en list pour JSON
            optimization_results['analysis']['departements_utilises'] = list(optimization_results['analysis']['departements_utilises'])
            
            # Détecter les goulots d'étranglement
            bottlenecks = self.get_work_center_capacity_bottlenecks()
            current_work_centers = [op['work_center_id'] for op in current_operations if op['work_center_id']]
            
            for bottleneck in bottlenecks:
                if bottleneck['id'] in current_work_centers:
                    optimization_results['analysis']['goulots_detectes'].append({
                        'poste': bottleneck['nom'],
                        'charge': bottleneck['taux_charge_planifiee_pct'],
                        'niveau': bottleneck['niveau_goulot']
                    })
            
            # Suggestions d'amélioration
            suggestions = []
            if len(optimization_results['analysis']['goulots_detectes']) > 0:
                suggestions.append("Réorganiser les opérations pour éviter les goulots d'étranglement")
            
            if optimization_results['analysis']['temps_total_estime'] > 40:  # Plus de 40h
                suggestions.append("Considérer la parallélisation des opérations")
            
            if len(optimization_results['analysis']['departements_utilises']) > 3:
                suggestions.append("Réduire les déplacements inter-départements")
            
            optimization_results['analysis']['suggestions_amelioration'] = suggestions
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"Erreur optimisation gamme projet {project_id}: {e}")
            return {'error': str(e)}

    def get_bom_materials_with_suppliers(self, project_id: str) -> List[Dict]:
        """Récupère les matériaux BOM avec informations fournisseurs"""
        try:
            query = '''
                SELECT m.*, 
                       c.nom as supplier_name, 
                       f.delai_livraison_moyen as delai_livraison,
                       f.evaluation_qualite as supplier_rating
                FROM materials m
                LEFT JOIN companies c ON m.fournisseur = c.nom
                LEFT JOIN fournisseurs f ON c.id = f.company_id
                WHERE m.project_id = ?
                ORDER BY m.id
            '''
            rows = self.execute_query(query, (str(project_id),))
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération matériaux BOM avec fournisseurs: {e}")
            return []
    
    def get_work_centers_for_routing(self) -> List[Dict]:
        """Récupère tous les postes de travail disponibles pour l'itinéraire"""
        try:
            query = '''
                SELECT wc.*,
                       COUNT(DISTINCT o.id) as operations_assigned,
                       COALESCE(AVG(te.hourly_rate), wc.cout_horaire) as taux_reel_moyen
                FROM work_centers wc
                LEFT JOIN operations o ON wc.id = o.work_center_id
                LEFT JOIN time_entries te ON o.id = te.operation_id AND te.total_cost IS NOT NULL
                WHERE wc.statut = 'ACTIF'
                GROUP BY wc.id
                ORDER BY wc.departement, wc.nom
            '''
            rows = self.execute_query(query)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération postes pour itinéraire: {e}")
            return []
    
    def get_manufacturing_routes_for_project(self, project_id: str) -> Dict[str, Any]:
        """Récupère les gammes de fabrication complètes pour un projet"""
        try:
            # Récupérer les opérations avec détails postes
            operations = self.get_project_operations_with_work_centers(project_id)
            
            if not operations:
                return {
                    'project_id': project_id,
                    'operations': [],
                    'statistics': {
                        'total_operations': 0,
                        'total_time_estimated': 0,
                        'total_cost_estimated': 0,
                        'departments_involved': [],
                        'work_centers_used': []
                    }
                }
            
            # Calculer les statistiques
            total_time = sum(op.get('temps_estime', 0) or 0 for op in operations)
            total_cost = sum((op.get('temps_estime', 0) or 0) * (op.get('work_center_cout_horaire', 0) or 0) for op in operations)
            departments = list(set(op.get('work_center_departement') for op in operations if op.get('work_center_departement')))
            work_centers = list(set(op.get('work_center_name') for op in operations if op.get('work_center_name')))
            
            return {
                'project_id': project_id,
                'operations': operations,
                'statistics': {
                    'total_operations': len(operations),
                    'total_time_estimated': total_time,
                    'total_cost_estimated': total_cost,
                    'departments_involved': departments,
                    'work_centers_used': work_centers,
                    'complexity_score': self._calculate_route_complexity(operations)
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération gammes projet {project_id}: {e}")
            return {}
    
    def _calculate_route_complexity(self, operations: List[Dict]) -> str:
        """Calcule un score de complexité pour une gamme de fabrication"""
        try:
            if not operations:
                return "SIMPLE"
            
            num_operations = len(operations)
            num_departments = len(set(op.get('work_center_departement') for op in operations if op.get('work_center_departement')))
            total_time = sum(op.get('temps_estime', 0) or 0 for op in operations)
            
            # Score basé sur nombre d'opérations, départements et temps
            complexity_score = (num_operations * 0.3) + (num_departments * 0.4) + (total_time / 10 * 0.3)
            
            if complexity_score <= 3:
                return "SIMPLE"
            elif complexity_score <= 8:
                return "MODÉRÉE"
            elif complexity_score <= 15:
                return "COMPLEXE"
            else:
                return "TRÈS_COMPLEXE"
                
        except Exception:
            return "INDÉTERMINÉE"

    def update_inventory_from_bom_consumption(self, project_id: str, consumption_data: List[Dict]) -> bool:
        """Met à jour l'inventaire après consommation pour un projet (simulation)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for consumption in consumption_data:
                    material_code = consumption.get('material_code')
                    quantity_consumed = consumption.get('quantity_consumed', 0)
                    
                    # Trouver l'article d'inventaire correspondant
                    inventory_item = self.execute_query(
                        "SELECT * FROM inventory_items WHERE code_interne = ? OR nom LIKE ?",
                        (material_code, f"%{material_code}%")
                    )
                    
                    if inventory_item:
                        item = dict(inventory_item[0])
                        current_qty_metric = item['quantite_metric']
                        new_qty_metric = max(0, current_qty_metric - quantity_consumed)
                        
                        # Mettre à jour la quantité
                        cursor.execute(
                            "UPDATE inventory_items SET quantite_metric = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (new_qty_metric, item['id'])
                        )
                        
                        # Enregistrer dans l'historique
                        cursor.execute(
                            '''INSERT INTO inventory_history 
                               (inventory_item_id, action, quantite_avant, quantite_apres, notes)
                               VALUES (?, ?, ?, ?, ?)''',
                            (item['id'], 'CONSOMMATION_PROJET', str(current_qty_metric), 
                             str(new_qty_metric), f"Consommation projet #{project_id}")
                        )
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Erreur mise à jour inventaire consommation: {e}")
            return False

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
                'timetracker_bt_mensuel': {'sessions_bt': 0, 'heures_bt': 0.0, 'cout_bt': 0.0},
                'work_centers_performance': {'nouveaux_postes': 0, 'utilisation_moyenne': 0.0, 'revenus_generes': 0.0},
                'production_performance': {'nouveaux_bom': 0, 'nouvelles_operations': 0, 'projets_production': 0},
                'operations_bt_performance': {'operations_bt_creees': 0, 'bt_operations_mois': 0, 'temps_operations_bt': 0.0},
                'communication_tt_performance': {'syncs_effectuees': 0, 'progressions_recalculees': 0, 'sessions_nettoyees': 0},
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
            
            # Performances fournisseurs
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
            
            # Performance TimeTracker BT mensuelle
            query = '''
                SELECT 
                    COUNT(*) as sessions_bt,
                    COALESCE(SUM(total_hours), 0) as heures_bt,
                    COALESCE(SUM(total_cost), 0) as cout_bt
                FROM time_entries 
                WHERE formulaire_bt_id IS NOT NULL
                AND strftime('%Y-%m', punch_in) = ?
            '''
            result = self.execute_query(query, (f"{year}-{month:02d}",))
            if result:
                report['timetracker_bt_mensuel']['sessions_bt'] = result[0]['sessions_bt']
                report['timetracker_bt_mensuel']['heures_bt'] = round(result[0]['heures_bt'], 1)
                report['timetracker_bt_mensuel']['cout_bt'] = round(result[0]['cout_bt'], 2)
            
            # Performance postes de travail mensuelle
            query = '''
                SELECT COUNT(*) as nouveaux_postes
                FROM work_centers
                WHERE strftime('%Y-%m', created_at) = ?
            '''
            result = self.execute_query(query, (f"{year}-{month:02d}",))
            if result:
                report['work_centers_performance']['nouveaux_postes'] = result[0]['nouveaux_postes']
            
            # Utilisation moyenne des postes sur le mois
            query = '''
                SELECT 
                    COALESCE(AVG(wc.capacite_theorique), 0) as capacite_moyenne,
                    COALESCE(SUM(te.total_hours), 0) as heures_utilisees,
                    COALESCE(SUM(te.total_cost), 0) as revenus_generes
                FROM work_centers wc
                LEFT JOIN operations o ON wc.id = o.work_center_id
                LEFT JOIN time_entries te ON o.id = te.operation_id 
                    AND strftime('%Y-%m', te.punch_in) = ?
                WHERE wc.statut = 'ACTIF'
            '''
            result = self.execute_query(query, (f"{year}-{month:02d}",))
            if result:
                data = dict(result[0])
                if data['capacite_moyenne'] > 0:
                    # Calcul approximatif de l'utilisation moyenne du mois (30 jours)
                    days_in_month = 30
                    capacity_total_month = data['capacite_moyenne'] * days_in_month
                    utilization = (data['heures_utilisees'] / capacity_total_month * 100) if capacity_total_month > 0 else 0
                    report['work_centers_performance']['utilisation_moyenne'] = round(utilization, 2)
                
                report['work_centers_performance']['revenus_generes'] = round(data['revenus_generes'], 2)
            
            # Performance production mensuelle
            query = '''
                SELECT COUNT(*) as nouveaux_bom
                FROM materials
                WHERE strftime('%Y-%m', created_at) = ?
            '''
            result = self.execute_query(query, (f"{year}-{month:02d}",))
            if result:
                report['production_performance']['nouveaux_bom'] = result[0]['nouveaux_bom']
            
            query = '''
                SELECT COUNT(*) as nouvelles_operations
                FROM operations
                WHERE strftime('%Y-%m', created_at) = ?
            '''
            result = self.execute_query(query, (f"{year}-{month:02d}",))
            if result:
                report['production_performance']['nouvelles_operations'] = result[0]['nouvelles_operations']
            
            query = '''
                SELECT COUNT(DISTINCT project_id) as projets_production
                FROM materials
                WHERE strftime('%Y-%m', created_at) = ?
                AND project_id IS NOT NULL
            '''
            result = self.execute_query(query, (f"{year}-{month:02d}",))
            if result:
                report['production_performance']['projets_production'] = result[0]['projets_production']
            
            # Performance Operations ↔ BT mensuelle
            query = '''
                SELECT COUNT(*) as operations_bt_creees
                FROM operations
                WHERE formulaire_bt_id IS NOT NULL
                AND strftime('%Y-%m', created_at) = ?
            '''
            result = self.execute_query(query, (f"{year}-{month:02d}",))
            if result:
                report['operations_bt_performance']['operations_bt_creees'] = result[0]['operations_bt_creees']
            
            query = '''
                SELECT COUNT(DISTINCT formulaire_bt_id) as bt_operations_mois
                FROM operations
                WHERE formulaire_bt_id IS NOT NULL
                AND strftime('%Y-%m', created_at) = ?
            '''
            result = self.execute_query(query, (f"{year}-{month:02d}",))
            if result:
                report['operations_bt_performance']['bt_operations_mois'] = result[0]['bt_operations_mois']
            
            query = '''
                SELECT COALESCE(SUM(temps_estime), 0) as temps_operations_bt
                FROM operations
                WHERE formulaire_bt_id IS NOT NULL
                AND strftime('%Y-%m', created_at) = ?
            '''
            result = self.execute_query(query, (f"{year}-{month:02d}",))
            if result:
                report['operations_bt_performance']['temps_operations_bt'] = round(result[0]['temps_operations_bt'], 2)
            
            # Performance Communication TimeTracker mensuelle (simulée)
            report['communication_tt_performance'] = {
                'syncs_effectuees': 30,  # Une par jour approximativement
                'progressions_recalculees': report['bt_performance']['total_bt'] * 2,  # Estimation
                'sessions_nettoyees': 5  # Estimation du nettoyage
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Erreur génération rapport mensuel: {e}")
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
