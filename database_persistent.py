# database_persistent.py - Gestionnaire Stockage Persistant Render
# ERP Production DG Inc. - VERSION COMPLÈTE FINALE
# Configuration automatique du stockage persistant pour Render

import os
import shutil
import sqlite3
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PersistentERPDatabase:
    """
    Gestionnaire de stockage persistant pour ERP Production DG Inc.
    
    Détecte automatiquement l'environnement et configure les chemins appropriés :
    - Render avec Persistent Disk : /opt/render/project/data/ (✅ PERSISTANT)
    - Render sans Persistent Disk : /tmp/ (⚠️ ÉPHÉMÈRE) 
    - Développement local : ./ (💻 LOCAL)
    """
    
    def __init__(self):
        """Initialise le gestionnaire de stockage persistant"""
        self.setup_environment_detection()
        self.setup_persistent_paths()
        self.migrate_existing_data()
        self.log_configuration_status()
    
    def setup_environment_detection(self):
        """Détecte l'environnement d'exécution"""
        # Détecter Render
        self.is_render = os.path.exists('/opt/render/project')
        
        # Détecter le disque persistant
        self.has_persistent_disk = os.path.exists('/opt/render/project/data')
        
        # Détecter les variables d'environnement
        self.use_persistent_storage = os.environ.get('USE_PERSISTENT_STORAGE', '').lower() == 'true'
        self.custom_data_path = os.environ.get('DATA_PATH')
        
        logger.info(f"Environnement détecté:")
        logger.info(f"  - Render: {'✅' if self.is_render else '❌'}")
        logger.info(f"  - Persistent Disk: {'✅' if self.has_persistent_disk else '❌'}")
        logger.info(f"  - Variables env: USE_PERSISTENT_STORAGE={self.use_persistent_storage}")
    
    def setup_persistent_paths(self):
        """Configure les chemins selon l'environnement détecté"""
        
        if self.is_render and self.has_persistent_disk:
            # Production Render avec persistent disk ✅ OPTIMAL
            self.environment_type = "RENDER_PERSISTENT"
            self.data_dir = '/opt/render/project/data'
            self.db_path = os.path.join(self.data_dir, 'erp_production_dg.db')
            self.backup_dir = os.path.join(self.data_dir, 'backup_json')
            self.storage_status = "PERSISTANT"
            logger.info("🎯 Mode Render avec stockage persistant ACTIVÉ")
            
        elif self.is_render:
            # Render sans persistent disk ⚠️ PROBLÉMATIQUE
            self.environment_type = "RENDER_EPHEMERAL"
            self.data_dir = '/tmp'
            self.db_path = '/tmp/erp_production_dg.db'
            self.backup_dir = '/tmp/backup_json'
            self.storage_status = "ÉPHÉMÈRE"
            logger.warning("⚠️ Render détecté mais PAS de persistent disk configuré")
            logger.warning("🚨 LES DONNÉES SERONT PERDUES À CHAQUE REDÉPLOIEMENT")
            
        elif self.custom_data_path and os.path.exists(self.custom_data_path):
            # Chemin personnalisé via variable d'environnement
            self.environment_type = "CUSTOM_PATH"
            self.data_dir = self.custom_data_path
            self.db_path = os.path.join(self.data_dir, 'erp_production_dg.db')
            self.backup_dir = os.path.join(self.data_dir, 'backup_json')
            self.storage_status = "PERSONNALISÉ"
            logger.info(f"📁 Chemin personnalisé utilisé: {self.data_dir}")
            
        else:
            # Développement local 💻
            self.environment_type = "LOCAL_DEVELOPMENT"
            self.data_dir = '.'
            self.db_path = 'erp_production_dg.db'
            self.backup_dir = 'backup_json'
            self.storage_status = "LOCAL"
            logger.info("💻 Mode développement local")
        
        # Créer les dossiers nécessaires
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            os.makedirs(self.backup_dir, exist_ok=True)
            logger.info(f"📁 Dossiers créés: {self.data_dir}")
        except Exception as e:
            logger.error(f"❌ Erreur création dossiers: {e}")
            raise
        
        # Log des chemins configurés
        logger.info(f"Configuration chemins:")
        logger.info(f"  - Base de données: {self.db_path}")
        logger.info(f"  - Sauvegardes: {self.backup_dir}")
        logger.info(f"  - Statut stockage: {self.storage_status}")
    
    def migrate_existing_data(self):
        """Migre les données existantes vers le stockage persistant"""
        
        if not self.is_render or not self.has_persistent_disk:
            # Pas de migration nécessaire en local ou si pas de disque persistant
            return
        
        logger.info("🔄 Recherche données existantes à migrer...")
        
        # Chemins possibles des anciennes données (ordre de priorité)
        potential_old_paths = [
            '/opt/render/project/src/erp_production_dg.db',  # Build directory
            '/tmp/erp_production_dg.db',                     # Ancien stockage temporaire
            '/opt/render/project/erp_production_dg.db',      # Racine projet
            'erp_production_dg.db'                           # Relatif
        ]
        
        migration_completed = False
        
        for old_path in potential_old_paths:
            if os.path.exists(old_path) and old_path != self.db_path:
                try:
                    # Vérifier que l'ancien fichier est valide
                    if self._verify_database_file(old_path):
                        # Copier vers le stockage persistant
                        shutil.copy2(old_path, self.db_path)
                        logger.info(f"✅ Données migrées avec succès:")
                        logger.info(f"   Source: {old_path}")
                        logger.info(f"   Destination: {self.db_path}")
                        
                        # Vérifier l'intégrité après migration
                        if self.verify_database():
                            logger.info("✅ Intégrité vérifiée après migration")
                            migration_completed = True
                            
                            # Créer une sauvegarde de sécurité immédiate
                            backup_path = self.create_backup("migration_backup")
                            if backup_path:
                                logger.info(f"✅ Sauvegarde de migration créée: {backup_path}")
                            
                            break
                        else:
                            logger.warning(f"⚠️ Problème d'intégrité après migration depuis {old_path}")
                    else:
                        logger.warning(f"⚠️ Fichier invalide ignoré: {old_path}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Erreur migration depuis {old_path}: {e}")
                    continue
        
        if not migration_completed:
            logger.info("ℹ️ Aucune donnée existante trouvée ou migration non nécessaire")
        
        # Log final du statut de la base
        if os.path.exists(self.db_path):
            size_mb = round(os.path.getsize(self.db_path) / (1024*1024), 2)
            logger.info(f"📊 Base de données finale: {size_mb} MB")
        else:
            logger.info("📊 Nouvelle base de données sera créée")
    
    def _verify_database_file(self, db_path: str) -> bool:
        """Vérifie qu'un fichier de base de données est valide"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Test basique : essayer de lire les tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            conn.close()
            
            # Considérer valide s'il y a au moins quelques tables attendues
            table_names = [table[0] for table in tables]
            expected_tables = ['projects', 'companies', 'employees']
            has_expected_tables = any(table in table_names for table in expected_tables)
            
            return len(tables) > 0 and has_expected_tables
            
        except Exception as e:
            logger.warning(f"Vérification fichier DB échouée pour {db_path}: {e}")
            return False
    
    def verify_database(self) -> bool:
        """Vérifie l'intégrité de la base de données actuelle"""
        try:
            if not os.path.exists(self.db_path):
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Vérification d'intégrité SQLite
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()
            
            # Vérification de la structure de base
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            conn.close()
            
            # Vérifications
            integrity_ok = integrity_result and integrity_result[0] == 'ok'
            has_tables = len(tables) > 0
            
            if integrity_ok and has_tables:
                logger.info(f"✅ Base de données intègre - {len(tables)} tables")
                return True
            else:
                logger.warning(f"⚠️ Problème intégrité - Integrity: {integrity_ok}, Tables: {len(tables)}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur vérification intégrité: {e}")
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Retourne les informations complètes de stockage pour le dashboard"""
        
        info = {
            # Informations de base
            'environment_type': self.environment_type,
            'storage_status': self.storage_status,
            'is_persistent': self.has_persistent_disk if self.is_render else True,
            'is_render': self.is_render,
            
            # Chemins
            'data_dir': self.data_dir,
            'db_path': self.db_path,
            'backup_dir': self.backup_dir,
            
            # État des fichiers
            'db_exists': os.path.exists(self.db_path),
            'db_size_mb': 0,
            'backup_count': 0,
            
            # Métadonnées
            'last_check': datetime.now().isoformat(),
            'configuration_valid': True
        }
        
        try:
            # Taille de la base de données
            if info['db_exists']:
                info['db_size_mb'] = round(os.path.getsize(self.db_path) / (1024*1024), 2)
            
            # Nombre de sauvegardes
            if os.path.exists(self.backup_dir):
                backup_files = [f for f in os.listdir(self.backup_dir) if f.endswith('.db')]
                info['backup_count'] = len(backup_files)
            
            # Usage du disque (Render uniquement)
            if self.is_render and self.has_persistent_disk:
                total, used, free = shutil.disk_usage(self.data_dir)
                info['disk_usage'] = {
                    'total_gb': round(total / (1024**3), 2),
                    'used_mb': round(used / (1024**2), 2),
                    'free_mb': round(free / (1024**2), 2),
                    'usage_percent': round((used / total) * 100, 1)
                }
            
            # Statistiques des tables (si base existe)
            if info['db_exists']:
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    # Compter les principales tables
                    table_counts = {}
                    main_tables = ['projects', 'companies', 'employees', 'formulaires', 'inventory_items']
                    
                    for table in main_tables:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table}")
                            table_counts[table] = cursor.fetchone()[0]
                        except sqlite3.OperationalError:
                            # Table n'existe pas encore
                            table_counts[table] = 0
                    
                    info['table_counts'] = table_counts
                    conn.close()
                    
                except Exception as e:
                    logger.warning(f"Impossible de lire les stats des tables: {e}")
            
        except Exception as e:
            logger.warning(f"Erreur calcul des informations de stockage: {e}")
            info['configuration_valid'] = False
            info['error'] = str(e)
        
        return info
    
    def create_backup(self, backup_suffix: str = None) -> Optional[str]:
        """
        Crée une sauvegarde timestampée de la base de données
        
        Args:
            backup_suffix: Suffixe optionnel pour le nom de fichier
            
        Returns:
            Chemin du fichier de sauvegarde créé, ou None si erreur
        """
        try:
            if not os.path.exists(self.db_path):
                logger.warning("Impossible de créer une sauvegarde - base de données introuvable")
                return None
            
            # Génération du nom de fichier
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if backup_suffix:
                backup_filename = f"backup_{backup_suffix}_{timestamp}.db"
            else:
                backup_filename = f"backup_{timestamp}.db"
            
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Copie de la base de données
            shutil.copy2(self.db_path, backup_path)
            
            # Vérification de la sauvegarde
            if os.path.exists(backup_path) and self._verify_database_file(backup_path):
                backup_size = round(os.path.getsize(backup_path) / (1024*1024), 2)
                logger.info(f"✅ Sauvegarde créée: {backup_filename} ({backup_size} MB)")
                
                # Nettoyage des anciennes sauvegardes
                self._cleanup_old_backups()
                
                return backup_path
            else:
                logger.error("❌ Sauvegarde créée mais vérification échouée")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erreur création sauvegarde: {e}")
            return None
    
    def _cleanup_old_backups(self, max_backups: int = 10):
        """
        Nettoie les anciennes sauvegardes pour éviter l'accumulation
        
        Args:
            max_backups: Nombre maximum de sauvegardes à conserver
        """
        try:
            if not os.path.exists(self.backup_dir):
                return
            
            # Lister tous les fichiers de sauvegarde
            backup_files = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith('backup_') and filename.endswith('.db'):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_mtime = os.path.getmtime(file_path)
                    backup_files.append((file_path, file_mtime, filename))
            
            # Trier par date de modification (plus récent en premier)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Supprimer les anciens au-delà de la limite
            files_to_delete = backup_files[max_backups:]
            
            for file_path, _, filename in files_to_delete:
                try:
                    os.remove(file_path)
                    logger.info(f"🗑️ Ancienne sauvegarde supprimée: {filename}")
                except Exception as e:
                    logger.warning(f"Impossible de supprimer {filename}: {e}")
            
            if len(files_to_delete) > 0:
                logger.info(f"📁 Nettoyage terminé - {len(files_to_delete)} ancienne(s) sauvegarde(s) supprimée(s)")
                
        except Exception as e:
            logger.warning(f"Erreur nettoyage sauvegardes: {e}")
    
    def log_configuration_status(self):
        """Affiche un résumé de la configuration dans les logs"""
        
        logger.info("=" * 60)
        logger.info("📊 RÉSUMÉ CONFIGURATION STOCKAGE PERSISTANT")
        logger.info("=" * 60)
        
        logger.info(f"🖥️  Environnement: {self.environment_type}")
        logger.info(f"💾 Statut stockage: {self.storage_status}")
        logger.info(f"📁 Répertoire données: {self.data_dir}")
        logger.info(f"🗄️  Base de données: {self.db_path}")
        
        if os.path.exists(self.db_path):
            size_mb = round(os.path.getsize(self.db_path) / (1024*1024), 2)
            logger.info(f"📊 Taille base: {size_mb} MB")
        else:
            logger.info("📊 Base: Nouvelle installation")
        
        # Recommandations selon la configuration
        if self.environment_type == "RENDER_PERSISTENT":
            logger.info("✅ CONFIGURATION OPTIMALE - Données protégées")
        elif self.environment_type == "RENDER_EPHEMERAL":
            logger.info("🚨 ATTENTION - Configurez le Persistent Disk sur Render")
            logger.info("   Dashboard Render → Settings → Disks → Add Disk")
            logger.info("   Mount Path: /opt/render/project/data")
        elif self.environment_type == "LOCAL_DEVELOPMENT":
            logger.info("💻 Mode développement - Sauvegardez régulièrement")
        
        logger.info("=" * 60)
    
    def test_storage_functionality(self) -> Dict[str, Any]:
        """
        Teste les fonctionnalités de stockage
        
        Returns:
            Dictionnaire avec les résultats des tests
        """
        
        test_results = {
            'timestamp': datetime.now().isoformat(),
            'environment': self.environment_type,
            'tests': {},
            'overall_success': False
        }
        
        logger.info("🧪 Début des tests de stockage...")
        
        # Test 1: Écriture/lecture fichier simple
        try:
            test_file = os.path.join(self.data_dir, 'storage_test.txt')
            test_content = f"Test stockage persistant - {datetime.now().isoformat()}"
            
            with open(test_file, 'w') as f:
                f.write(test_content)
            
            with open(test_file, 'r') as f:
                read_content = f.read()
            
            os.remove(test_file)  # Nettoyage
            
            test_results['tests']['file_operations'] = {
                'success': read_content == test_content,
                'message': "Écriture/lecture fichier réussie"
            }
            
        except Exception as e:
            test_results['tests']['file_operations'] = {
                'success': False,
                'message': f"Erreur opérations fichier: {e}"
            }
        
        # Test 2: Base de données SQLite
        try:
            test_db_path = os.path.join(self.data_dir, 'test_storage.db')
            
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            
            # Créer table test
            cursor.execute('''
                CREATE TABLE test_storage (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    test_data TEXT
                )
            ''')
            
            # Insérer données test
            cursor.execute(
                "INSERT INTO test_storage (timestamp, test_data) VALUES (?, ?)",
                (datetime.now().isoformat(), "Test données SQLite")
            )
            
            # Lire données
            cursor.execute("SELECT COUNT(*) FROM test_storage")
            count = cursor.fetchone()[0]
            
            conn.commit()
            conn.close()
            
            # Nettoyage
            os.remove(test_db_path)
            
            test_results['tests']['sqlite_operations'] = {
                'success': count == 1,
                'message': f"SQLite fonctionnel - {count} enregistrement"
            }
            
        except Exception as e:
            test_results['tests']['sqlite_operations'] = {
                'success': False,
                'message': f"Erreur SQLite: {e}"
            }
        
        # Test 3: Création sauvegarde
        if os.path.exists(self.db_path):
            try:
                backup_path = self.create_backup("test")
                
                test_results['tests']['backup_creation'] = {
                    'success': backup_path is not None,
                    'message': f"Sauvegarde créée: {backup_path}" if backup_path else "Erreur création sauvegarde"
                }
                
            except Exception as e:
                test_results['tests']['backup_creation'] = {
                    'success': False,
                    'message': f"Erreur sauvegarde: {e}"
                }
        else:
            test_results['tests']['backup_creation'] = {
                'success': False,
                'message': "Base de données inexistante - impossible de tester sauvegarde"
            }
        
        # Résultat global
        all_tests_passed = all(test['success'] for test in test_results['tests'].values())
        test_results['overall_success'] = all_tests_passed
        
        # Log des résultats
        logger.info("📋 Résultats des tests:")
        for test_name, result in test_results['tests'].items():
            status = "✅" if result['success'] else "❌"
            logger.info(f"   {status} {test_name}: {result['message']}")
        
        if all_tests_passed:
            logger.info("🎉 Tous les tests de stockage réussis !")
        else:
            logger.warning("⚠️ Certains tests ont échoué")
        
        return test_results


def init_persistent_storage() -> PersistentERPDatabase:
    """
    Fonction d'initialisation principale du gestionnaire de stockage persistant
    
    Returns:
        Instance configurée de PersistentERPDatabase
    """
    
    logger.info("🚀 Initialisation du gestionnaire de stockage persistant...")
    
    try:
        # Créer et configurer le gestionnaire
        storage_manager = PersistentERPDatabase()
        
        # Afficher les informations de configuration
        storage_info = storage_manager.get_storage_info()
        
        logger.info("✅ Gestionnaire de stockage persistant initialisé avec succès")
        logger.info(f"   Type: {storage_info['environment_type']}")
        logger.info(f"   Statut: {storage_info['storage_status']}")
        logger.info(f"   Base: {storage_info['db_size_mb']} MB")
        
        return storage_manager
        
    except Exception as e:
        logger.error(f"❌ Erreur initialisation gestionnaire stockage: {e}")
        raise


def test_storage_configuration():
    """
    Fonction de test standalone pour valider la configuration
    Peut être appelée indépendamment pour diagnostiquer des problèmes
    """
    
    print("🧪 Test de Configuration Stockage Persistant")
    print("=" * 50)
    
    try:
        # Initialiser le gestionnaire
        storage_manager = init_persistent_storage()
        
        # Récupérer les informations
        storage_info = storage_manager.get_storage_info()
        
        # Afficher les informations
        print(f"🖥️  Environnement: {storage_info['environment_type']}")
        print(f"💾 Type stockage: {storage_info['storage_status']}")
        print(f"📁 Répertoire: {storage_info['data_dir']}")
        print(f"🗄️  Base données: {storage_info['db_path']}")
        print(f"📊 Taille base: {storage_info['db_size_mb']} MB")
        print(f"💾 Persistant: {'✅ OUI' if storage_info['is_persistent'] else '❌ NON'}")
        
        if storage_info.get('disk_usage'):
            disk = storage_info['disk_usage']
            print(f"💽 Usage disque: {disk['usage_percent']}% ({disk['used_mb']}/{disk['used_mb'] + disk['free_mb']} MB)")
        
        # Exécuter les tests
        print("\n🧪 Exécution des tests...")
        test_results = storage_manager.test_storage_functionality()
        
        print(f"\n📋 Résultats: {'✅ SUCCÈS' if test_results['overall_success'] else '❌ ÉCHEC'}")
        
        # Recommandations
        print("\n💡 Recommandations:")
        if storage_info['environment_type'] == "RENDER_PERSISTENT":
            print("   ✅ Configuration optimale - Aucune action requise")
        elif storage_info['environment_type'] == "RENDER_EPHEMERAL":
            print("   🚨 URGENT: Configurez le Persistent Disk sur Render")
            print("   📋 Render Dashboard → Settings → Disks → Add Disk")
            print("   📁 Mount Path: /opt/render/project/data")
        elif storage_info['environment_type'] == "LOCAL_DEVELOPMENT":
            print("   💻 Mode développement - Sauvegardez régulièrement")
        
        return test_results['overall_success']
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False


# Point d'entrée pour tests manuels
if __name__ == "__main__":
    print("🏭 ERP Production DG Inc. - Test Stockage Persistant")
    print("=" * 60)
    
    success = test_storage_configuration()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 CONFIGURATION RÉUSSIE - Stockage persistant opérationnel !")
    else:
        print("🔧 CONFIGURATION À FINALISER - Voir recommandations ci-dessus")
    
    print("🏁 Test terminé.")
