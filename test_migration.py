# test_migration.py - Tests et Validation Migration SQLite
# ERP Production DG Inc.

import os
import json
import pytest
import sqlite3
import logging
from datetime import datetime
from erp_database import ERPDatabase
from migration_scripts import MigrationManager, validate_migration_results

# Configuration logging pour tests
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestMigration:
    """Tests unitaires pour la migration JSON → SQLite"""
    
    @classmethod
    def setup_class(cls):
        """Setup avant tous les tests"""
        cls.test_db_path = "test_erp_production.db"
        cls.db = ERPDatabase(cls.test_db_path)
        cls.migration_manager = MigrationManager(cls.db)
    
    @classmethod
    def teardown_class(cls):
        """Cleanup après tous les tests"""
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)
    
    def test_database_creation(self):
        """Test création de la base de données"""
        assert os.path.exists(self.test_db_path)
        
        # Vérifier que toutes les tables sont créées
        expected_tables = [
            'companies', 'contacts', 'projects', 'employees', 
            'employee_competences', 'work_centers', 'operations',
            'materials', 'inventory_items', 'interactions',
            'project_assignments', 'time_entries', 'inventory_history'
        ]
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            actual_tables = [row['name'] for row in cursor.fetchall()]
        
        for table in expected_tables:
            assert table in actual_tables, f"Table {table} manquante"
        
        logger.info("✅ Toutes les tables créées correctement")
    
    def test_work_centers_migration(self):
        """Test migration des postes de travail"""
        from migration_scripts import migrate_work_centers
        
        result = migrate_work_centers(self.db)
        
        assert result['success'] == True
        assert result['migrated_count'] == 61
        
        # Vérifier données dans la base
        count = self.db.get_table_count('work_centers')
        assert count == 61
        
        # Vérifier un poste spécifique
        postes = self.db.execute_query("SELECT * FROM work_centers WHERE nom = 'Laser CNC'")
        assert len(postes) == 1
        assert postes[0]['departement'] == 'PRODUCTION'
        assert postes[0]['cout_horaire'] == 75
        
        logger.info("✅ Migration postes de travail validée")
    
    def test_sample_data_integrity(self):
        """Test intégrité des données d'exemple"""
        # Insérer des données d'exemple pour test
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Créer une entreprise test
            cursor.execute('''
                INSERT INTO companies (id, nom, secteur) 
                VALUES (999, 'Test Corp', 'Test')
            ''')
            
            # Créer un contact test
            cursor.execute('''
                INSERT INTO contacts (id, prenom, nom_famille, company_id) 
                VALUES (999, 'Test', 'User', 999)
            ''')
            
            # Créer un projet test
            cursor.execute('''
                INSERT INTO projects (id, nom_projet, client_company_id) 
                VALUES (99999, 'Projet Test', 999)
            ''')
            
            conn.commit()
        
        # Tester requête avec JOIN
        result = self.db.execute_query('''
            SELECT p.nom_projet, c.nom as nom_entreprise 
            FROM projects p 
            JOIN companies c ON p.client_company_id = c.id 
            WHERE p.id = 99999
        ''')
        
        assert len(result) == 1
        assert result[0]['nom_projet'] == 'Projet Test'
        assert result[0]['nom_entreprise'] == 'Test Corp'
        
        logger.info("✅ Intégrité des relations validée")
    
    def test_imperial_conversion(self):
        """Test conversion mesures impériales"""
        from erp_database import convertir_pieds_pouces_fractions_en_valeur_decimale, convertir_imperial_vers_metrique
        
        # Tests de conversion
        test_cases = [
            ("5' 6\"", 5.5),
            ("10' 0\"", 10.0),
            ("0' 8\"", 8/12),
            ("5' 6 3/4\"", 5.5625),
            ("0", 0.0)
        ]
        
        for input_str, expected_feet in test_cases:
            result = convertir_pieds_pouces_fractions_en_valeur_decimale(input_str)
            assert abs(result - expected_feet) < 0.0001, f"Conversion failed for {input_str}: got {result}, expected {expected_feet}"
        
        # Test conversion métrique
        meters = convertir_imperial_vers_metrique("5' 6\"")
        expected_meters = 5.5 * 0.3048
        assert abs(meters - expected_meters) < 0.0001
        
        logger.info("✅ Conversion mesures impériales validée")
    
    def test_foreign_key_constraints(self):
        """Test contraintes de clés étrangères"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Test insertion avec clé étrangère invalide (doit échouer)
            try:
                cursor.execute('''
                    INSERT INTO projects (id, nom_projet, client_company_id) 
                    VALUES (99998, 'Test Invalid FK', 999999)
                ''')
                conn.commit()
                assert False, "L'insertion avec FK invalide aurait dû échouer"
            except sqlite3.IntegrityError:
                pass  # Comportement attendu
        
        logger.info("✅ Contraintes de clés étrangères fonctionnelles")

def run_sample_migration_test():
    """Exécute un test de migration avec données d'exemple"""
    logger.info("🧪 Test de migration avec données d'exemple")
    
    # Créer des fichiers JSON d'exemple pour test
    create_sample_json_files()
    
    try:
        # Créer base de test
        test_db = ERPDatabase("test_migration.db")
        migration_manager = MigrationManager(test_db)
        
        # Exécuter migration
        results = migration_manager.run_full_migration()
        
        logger.info("📊 Résultats migration:")
        for module, result in results.get('modules', {}).items():
            if result.get('success'):
                logger.info(f"  ✅ {module}: {result.get('migrated_count', 'OK')}")
            else:
                logger.error(f"  ❌ {module}: {result.get('error', 'Erreur inconnue')}")
        
        # Validation
        validation_results = validate_migration_results(test_db)
        logger.info(f"📈 Base finale: {validation_results['table_counts']}")
        
        if validation_results['warnings']:
            for warning in validation_results['warnings']:
                logger.warning(f"⚠️ {warning}")
        
        return results
        
    finally:
        # Cleanup
        cleanup_sample_files()
        if os.path.exists("test_migration.db"):
            os.remove("test_migration.db")

def create_sample_json_files():
    """Crée des fichiers JSON d'exemple pour test"""
    
    # CRM data
    crm_data = {
        "entreprises": [
            {
                "id": 101,
                "nom": "Test Corp",
                "secteur": "Technologie",
                "adresse": "123 Test St",
                "site_web": "test.com",
                "contact_principal_id": 1,
                "notes": "Entreprise test",
                "date_creation": datetime.now().isoformat(),
                "date_modification": datetime.now().isoformat()
            }
        ],
        "contacts": [
            {
                "id": 1,
                "prenom": "John",
                "nom_famille": "Doe",
                "email": "john@test.com",
                "telephone": "555-1234",
                "entreprise_id": 101,
                "role": "Manager",
                "notes": "Contact test",
                "date_creation": datetime.now().isoformat(),
                "date_modification": datetime.now().isoformat()
            }
        ],
        "interactions": []
    }
    
    # Employees data
    employees_data = {
        "employes": [
            {
                "id": 1,
                "prenom": "Test",
                "nom": "Employee",
                "email": "test@dg-inc.qc.ca",
                "telephone": "450-372-9630",
                "poste": "Soudeur",
                "departement": "PRODUCTION",
                "statut": "ACTIF",
                "type_contrat": "CDI",
                "date_embauche": "2020-01-01",
                "salaire": 55000,
                "manager_id": None,
                "charge_travail": 85,
                "notes": "Employé test",
                "competences": [
                    {"nom": "Soudage GMAW", "niveau": "AVANCÉ", "certifie": True}
                ],
                "date_creation": datetime.now().isoformat(),
                "date_modification": datetime.now().isoformat()
            }
        ]
    }
    
    # Projects data
    projects_data = {
        "projets": [
            {
                "id": 10000,
                "nom_projet": "Test Project",
                "client_entreprise_id": 101,
                "client_nom_cache": "Test Corp",
                "statut": "EN COURS",
                "priorite": "MOYEN",
                "tache": "PRODUCTION",
                "date_soumis": "2024-01-01",
                "date_prevu": "2024-03-01",
                "bd_ft_estime": "50",
                "prix_estime": "25000",
                "description": "Projet test",
                "operations": [
                    {
                        "id": 1,
                        "sequence": "10",
                        "description": "Test operation",
                        "temps_estime": 5.0,
                        "ressource": "Test Employee",
                        "statut": "À FAIRE",
                        "poste_travail": "Laser CNC"
                    }
                ],
                "materiaux": [
                    {
                        "id": 1,
                        "code": "TEST-001",
                        "designation": "Matériau test",
                        "quantite": 10,
                        "unite": "kg",
                        "prix_unitaire": 5.0,
                        "fournisseur": "Test Supplier"
                    }
                ],
                "employes_assignes": [1]
            }
        ]
    }
    
    # Inventory data
    inventory_data = {
        "1": {
            "id": 1,
            "nom": "Test Material",
            "type": "TEST",
            "quantite": "5' 6\"",
            "limite_minimale": "2' 0\"",
            "quantite_reservee": "0' 0\"",
            "statut": "DISPONIBLE",
            "description": "Matériau test",
            "note": "Test note",
            "historique": [
                {
                    "date": datetime.now().isoformat(),
                    "action": "CRÉATION",
                    "quantite": "5' 6\"",
                    "note": "Création test"
                }
            ],
            "date_creation": datetime.now().isoformat()
        }
    }
    
    # Sauvegarder les fichiers
    with open('crm_data.json', 'w', encoding='utf-8') as f:
        json.dump(crm_data, f, indent=2, ensure_ascii=False)
    
    with open('employees_data.json', 'w', encoding='utf-8') as f:
        json.dump(employees_data, f, indent=2, ensure_ascii=False)
    
    with open('projets_data.json', 'w', encoding='utf-8') as f:
        json.dump(projects_data, f, indent=2, ensure_ascii=False)
    
    with open('inventaire_v2.json', 'w', encoding='utf-8') as f:
        json.dump(inventory_data, f, indent=2, ensure_ascii=False)
    
    logger.info("📄 Fichiers JSON d'exemple créés")

def cleanup_sample_files():
    """Supprime les fichiers d'exemple"""
    files_to_remove = [
        'crm_data.json', 'employees_data.json', 
        'projets_data.json', 'inventaire_v2.json'
    ]
    
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)
    
    logger.info("🧹 Fichiers d'exemple supprimés")

def run_performance_test(db: ERPDatabase):
    """Test de performance sur requêtes complexes"""
    logger.info("⚡ Test de performance...")
    
    import time
    
    # Test 1: Requête simple
    start_time = time.time()
    result = db.execute_query("SELECT COUNT(*) FROM work_centers")
    simple_time = time.time() - start_time
    
    # Test 2: Requête avec JOIN
    start_time = time.time()
    result = db.execute_query('''
        SELECT p.nom_projet, c.nom, COUNT(o.id) as nb_operations
        FROM projects p
        LEFT JOIN companies c ON p.client_company_id = c.id
        LEFT JOIN operations o ON p.id = o.project_id
        GROUP BY p.id
    ''')
    join_time = time.time() - start_time
    
    # Test 3: Requête complexe avec agrégations
    start_time = time.time()
    result = db.execute_query('''
        SELECT 
            e.departement,
            COUNT(DISTINCT e.id) as nb_employes,
            COUNT(DISTINCT pa.project_id) as nb_projets,
            AVG(e.salaire) as salaire_moyen
        FROM employees e
        LEFT JOIN project_assignments pa ON e.id = pa.employee_id
        GROUP BY e.departement
    ''')
    complex_time = time.time() - start_time
    
    logger.info(f"📊 Performance:")
    logger.info(f"  Simple query: {simple_time:.4f}s")
    logger.info(f"  JOIN query: {join_time:.4f}s") 
    logger.info(f"  Complex query: {complex_time:.4f}s")
    
    return {
        'simple_query_time': simple_time,
        'join_query_time': join_time,
        'complex_query_time': complex_time
    }

if __name__ == "__main__":
    logger.info("🚀 Lancement des tests de migration")
    
    # Test migration complète
    migration_results = run_sample_migration_test()
    
    if migration_results.get('success'):
        logger.info("✅ Tous les tests de migration réussis!")
    else:
        logger.error("❌ Échec des tests de migration")
        if migration_results.get('error'):
            logger.error(f"Erreur: {migration_results['error']}")
    
    logger.info("🏁 Tests terminés")
