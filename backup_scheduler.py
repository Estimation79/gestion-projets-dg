# backup_scheduler.py - Backup vers GitHub Releases - VERSION CORRIGÉE
import os
import sqlite3
import schedule
import time
import logging
import json
import zipfile
import threading
import requests
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GitHubBackupManager:
    """Gestionnaire de sauvegardes automatiques vers GitHub Releases - VERSION CORRIGÉE"""
    
    def __init__(self):
        self.config = {
            'db_path': os.environ.get('DB_PATH', '/opt/render/project/data/erp_production_dg.db'),
            'backup_local_dir': os.environ.get('BACKUP_LOCAL_DIR', '/opt/render/project/data/backups'),
            
            # Configuration GitHub
            'github_enabled': os.environ.get('GITHUB_BACKUP_ENABLED', 'true').lower() == 'true',
            'github_token': os.environ.get('GITHUB_TOKEN'),
            'github_repo': os.environ.get('GITHUB_REPO', 'Estimation79/gestion-projets-dg'),
            'github_api_url': 'https://api.github.com',
            
            'keep_local_backups': int(os.environ.get('KEEP_LOCAL_BACKUPS', '5')),
            'keep_github_releases': int(os.environ.get('KEEP_GITHUB_RELEASES', '10')),
            'max_backup_size_mb': int(os.environ.get('MAX_BACKUP_SIZE_MB', '100')),
            
            # NOUVELLES VARIABLES DEBUG CORRIGÉES
            'backup_schedule_minutes': int(os.environ.get('BACKUP_SCHEDULE_MINUTES', '120')),
            'immediate_backup_test': os.environ.get('IMMEDIATE_BACKUP_TEST', 'false').lower() == 'true',
            'force_backup_on_start': os.environ.get('FORCE_BACKUP_ON_START', 'false').lower() == 'true',
            'debug_github_backup': os.environ.get('DEBUG_GITHUB_BACKUP', 'false').lower() == 'true'
        }
        
        Path(self.config['backup_local_dir']).mkdir(parents=True, exist_ok=True)
        self._validate_github_config()
        
        # NOUVEAU : Logging debug activé
        if self.config['debug_github_backup']:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("🔍 Mode DEBUG backup activé")
    
    def _validate_github_config(self):
        """Valide la configuration GitHub - VERSION AMÉLIORÉE"""
        if not self.config['github_enabled']:
            logger.info("📊 Backup GitHub désactivé")
            return
        
        if not self.config['github_token']:
            logger.error("❌ GITHUB_TOKEN manquant")
            self.config['github_enabled'] = False
            return
        
        # AMÉLIORATION : Test de connexion plus robuste
        try:
            headers = {'Authorization': f'token {self.config["github_token"]}'}
            
            # Test 1 : Vérifier l'accès au repo
            repo_response = requests.get(
                f"{self.config['github_api_url']}/repos/{self.config['github_repo']}", 
                headers=headers, timeout=10
            )
            
            if repo_response.status_code == 200:
                repo_info = repo_response.json()
                logger.info(f"✅ Repo GitHub accessible: {repo_info['full_name']}")
                
                # Test 2 : Vérifier les permissions releases
                releases_response = requests.get(
                    f"{self.config['github_api_url']}/repos/{self.config['github_repo']}/releases",
                    headers=headers, timeout=10
                )
                
                if releases_response.status_code == 200:
                    logger.info("✅ Permissions releases OK")
                    return True
                else:
                    logger.error(f"❌ Pas d'accès aux releases: {releases_response.status_code}")
                    
            else:
                logger.error(f"❌ Erreur accès repo: {repo_response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Erreur connexion GitHub: {e}")
        
        self.config['github_enabled'] = False
        return False
    
    def create_backup(self):
        """Crée une sauvegarde de la base de données - AVEC DEBUG"""
        try:
            logger.info("🚀 DÉBUT création backup")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"erp_dg_backup_{timestamp}"
            
            if not os.path.exists(self.config['db_path']):
                logger.error(f"❌ Base de données non trouvée: {self.config['db_path']}")
                return None
            
            # AMÉLIORATION : Vérification taille DB
            db_size_mb = os.path.getsize(self.config['db_path']) / (1024*1024)
            logger.info(f"📊 Taille DB à sauvegarder: {db_size_mb:.2f} MB")
            
            # Sauvegarde SQLite
            backup_db_path = os.path.join(self.config['backup_local_dir'], f"{backup_name}.db")
            logger.debug(f"📁 Chemin backup DB: {backup_db_path}")
            
            source_conn = sqlite3.connect(self.config['db_path'])
            backup_conn = sqlite3.connect(backup_db_path)
            
            with backup_conn:
                source_conn.backup(backup_conn)
            
            source_conn.close()
            backup_conn.close()
            logger.info("✅ Backup SQLite terminé")
            
            # Métadonnées détaillées
            stats = self._get_database_stats(backup_db_path)
            metadata = {
                'backup_time': datetime.now().isoformat(),
                'backup_time_readable': datetime.now().strftime('%d/%m/%Y à %H:%M:%S'),
                'backup_size_mb': round(os.path.getsize(backup_db_path) / (1024*1024), 2),
                'company': 'Desmarais & Gagné Inc.',
                'database_stats': stats,
                'github_repo': self.config['github_repo'],
                'render_info': {
                    'service_id': os.environ.get('RENDER_SERVICE_ID', 'unknown'),
                    'git_commit': os.environ.get('RENDER_GIT_COMMIT', 'unknown')[:8],
                    'deploy_id': os.environ.get('RENDER_DEPLOY_ID', 'unknown')
                }
            }
            
            metadata_path = os.path.join(self.config['backup_local_dir'], f"{backup_name}.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Compression optimisée
            zip_path = os.path.join(self.config['backup_local_dir'], f"{backup_name}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                zipf.write(backup_db_path, f"{backup_name}.db")
                zipf.write(metadata_path, f"{backup_name}_info.json")
                
                # Ajouter un README dans le ZIP
                readme_content = self._create_backup_readme(metadata)
                zipf.writestr("README_BACKUP.md", readme_content)
            
            # Nettoyage fichiers temporaires
            os.remove(backup_db_path)
            os.remove(metadata_path)
            
            final_size_mb = round(os.path.getsize(zip_path) / (1024*1024), 2)
            logger.info(f"✅ Backup ZIP créé: {final_size_mb} MB")
            logger.info(f"📁 Chemin final: {zip_path}")
            
            return zip_path
            
        except Exception as e:
            logger.error(f"❌ Erreur création sauvegarde: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return None
    
    def _get_database_stats(self, db_path):
        """Récupère les statistiques complètes de la base"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            stats = {}
            tables = ['projects', 'companies', 'employees', 'formulaires', 'work_centers', 
                     'operations', 'materials', 'time_entries', 'contacts', 'interactions']
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[table] = cursor.fetchone()[0]
                except:
                    stats[table] = 0
            
            # Statistiques additionnelles
            try:
                cursor.execute("SELECT COUNT(*) FROM projects WHERE statut = 'EN COURS'")
                stats['projects_active'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM projects WHERE statut = 'TERMINÉ'")
                stats['projects_completed'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM time_entries WHERE DATE(start_time) = DATE('now')")
                stats['timetracker_today'] = cursor.fetchone()[0]
                
            except:
                pass
            
            stats['total_records'] = sum(v for k, v in stats.items() if not k.startswith('projects_') and k != 'timetracker_today')
            conn.close()
            
            logger.debug(f"📊 Stats DB: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Erreur stats DB: {e}")
            return {}
    
    def _create_backup_readme(self, metadata):
        """Crée un README pour le backup"""
        stats = metadata.get('database_stats', {})
        return f"""# 🏭 ERP Production DG Inc. - Sauvegarde

## 📋 Informations Générales
- **Entreprise:** {metadata['company']}
- **Date de sauvegarde:** {metadata['backup_time_readable']}
- **Taille:** {metadata['backup_size_mb']} MB
- **Repository:** {metadata['github_repo']}

## 📊 Contenu de la Base de Données
- **Projets:** {stats.get('projects', 0)} (dont {stats.get('projects_active', 0)} actifs)
- **Entreprises/Clients:** {stats.get('companies', 0)}
- **Employés:** {stats.get('employees', 0)}
- **Formulaires:** {stats.get('formulaires', 0)}
- **Postes de Travail:** {stats.get('work_centers', 0)}
- **Opérations:** {stats.get('operations', 0)}
- **Matériaux:** {stats.get('materials', 0)}
- **Pointages:** {stats.get('time_entries', 0)}
- **Contacts:** {stats.get('contacts', 0)}

**Total des enregistrements:** {stats.get('total_records', 0):,}

## 🔧 Informations Techniques
- **Service Render:** {metadata.get('render_info', {}).get('service_id', 'N/A')}
- **Commit Git:** {metadata.get('render_info', {}).get('git_commit', 'N/A')}
- **Deploy ID:** {metadata.get('render_info', {}).get('deploy_id', 'N/A')}

## 📁 Fichiers inclus
- `erp_dg_backup_YYYYMMDD_HHMMSS.db` - Base de données SQLite complète
- `erp_dg_backup_YYYYMMDD_HHMMSS_info.json` - Métadonnées détaillées
- `README_BACKUP.md` - Cette documentation

## 🔄 Restauration
Pour restaurer cette sauvegarde :
1. Extraire le fichier ZIP
2. Remplacer le fichier `erp_production_dg.db` par le fichier de backup
3. Redémarrer l'application ERP

---
🤖 Sauvegarde automatique générée par le système ERP DG Inc.
"""
    
    def upload_to_github(self, backup_path):
        """Upload la sauvegarde vers GitHub Releases - VERSION CORRIGÉE"""
        if not self.config['github_enabled']:
            logger.warning("📊 Upload GitHub désactivé")
            return False
        
        try:
            logger.info("🚀 DÉBUT upload GitHub")
            
            file_size_mb = os.path.getsize(backup_path) / (1024 * 1024)
            logger.info(f"📊 Taille fichier à uploader: {file_size_mb:.2f} MB")
            
            if file_size_mb > self.config['max_backup_size_mb']:
                logger.error(f"📁 Fichier trop volumineux ({file_size_mb:.1f}MB > {self.config['max_backup_size_mb']}MB)")
                return False
            
            backup_filename = os.path.basename(backup_path)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 1. Créer une release
            release_data = {
                'tag_name': f'backup-{timestamp}',
                'name': f'🏭 ERP Backup - {datetime.now().strftime("%d/%m/%Y %H:%M")}',
                'body': self._create_release_description(backup_path),
                'draft': False,
                'prerelease': True
            }
            
            headers = {
                'Authorization': f'token {self.config["github_token"]}',
                'Content-Type': 'application/json'
            }
            
            logger.info("📦 Création de la release GitHub...")
            logger.debug(f"🔧 URL: {self.config['github_api_url']}/repos/{self.config['github_repo']}/releases")
            logger.debug(f"🔧 Headers: {headers}")
            logger.debug(f"🔧 Data: {release_data}")
            
            release_response = requests.post(
                f"{self.config['github_api_url']}/repos/{self.config['github_repo']}/releases",
                headers=headers,
                json=release_data,
                timeout=30
            )
            
            logger.info(f"📋 Response status: {release_response.status_code}")
            
            if release_response.status_code != 201:
                logger.error(f"❌ Erreur création release: {release_response.status_code}")
                logger.error(f"📋 Response body: {release_response.text}")
                return False
            
            release_info = release_response.json()
            upload_url = release_info['upload_url'].replace('{?name,label}', '')
            logger.info(f"✅ Release créée: {release_info['html_url']}")
            
            # 2. Upload du fichier
            logger.info("📤 Upload du fichier backup...")
            
            with open(backup_path, 'rb') as f:
                upload_headers = {
                    'Authorization': f'token {self.config["github_token"]}',
                    'Content-Type': 'application/zip'
                }
                
                logger.debug(f"🔧 Upload URL: {upload_url}?name={backup_filename}")
                
                upload_response = requests.post(
                    f"{upload_url}?name={backup_filename}&label=ERP Database Backup",
                    headers=upload_headers,
                    data=f,
                    timeout=120
                )
            
            logger.info(f"📋 Upload status: {upload_response.status_code}")
            
            if upload_response.status_code == 201:
                download_url = upload_response.json()['browser_download_url']
                logger.info(f"✅ Backup uploadé vers GitHub: {download_url}")
                
                # Nettoyage des anciennes releases
                self._cleanup_old_github_releases()
                
                return True
            else:
                logger.error(f"❌ Erreur upload: {upload_response.status_code}")
                logger.error(f"📋 Response body: {upload_response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur upload GitHub: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return False
    
    def _create_release_description(self, backup_path):
        """Crée la description de la release"""
        try:
            # Charger les métadonnées
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                for file in zipf.namelist():
                    if file.endswith('_info.json'):
                        with zipf.open(file) as json_file:
                            metadata = json.load(json_file)
                            break
                else:
                    metadata = {}
            
            stats = metadata.get('database_stats', {})
            file_size_mb = round(os.path.getsize(backup_path) / (1024*1024), 2)
            
            return f"""# 🏭 Sauvegarde Automatique ERP DG Inc.

## 📋 Informations
- **📅 Date:** {metadata.get('backup_time_readable', 'N/A')}
- **📁 Taille:** {file_size_mb} MB
- **🏢 Entreprise:** Desmarais & Gagné Inc.

## 📊 Contenu de la Base
| Module | Enregistrements |
|--------|-----------------|
| Projets | {stats.get('projects', 0):,} |
| Entreprises | {stats.get('companies', 0):,} |
| Employés | {stats.get('employees', 0):,} |
| Formulaires | {stats.get('formulaires', 0):,} |
| Postes Travail | {stats.get('work_centers', 0):,} |
| Pointages | {stats.get('time_entries', 0):,} |
| **TOTAL** | **{stats.get('total_records', 0):,}** |

## 📦 Utilisation
1. Télécharger le fichier ZIP
2. Extraire le contenu
3. Utiliser le fichier `.db` pour restaurer l'ERP

---
🤖 Sauvegarde automatique générée par le système corrigé
"""
            
        except Exception as e:
            logger.error(f"Erreur création description: {e}")
            return f"""# 🏭 Sauvegarde ERP DG Inc.

**Date:** {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}

Sauvegarde automatique de la base de données ERP Production.
"""
    
    def _cleanup_old_github_releases(self):
        """Supprime les anciennes releases de backup"""
        try:
            headers = {'Authorization': f'token {self.config["github_token"]}'}
            
            response = requests.get(
                f"{self.config['github_api_url']}/repos/{self.config['github_repo']}/releases",
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                return
            
            releases = response.json()
            backup_releases = [r for r in releases if r['tag_name'].startswith('backup-')]
            backup_releases.sort(key=lambda x: x['created_at'], reverse=True)
            
            releases_to_delete = backup_releases[self.config['keep_github_releases']:]
            
            for release in releases_to_delete:
                delete_response = requests.delete(
                    f"{self.config['github_api_url']}/repos/{self.config['github_repo']}/releases/{release['id']}",
                    headers=headers,
                    timeout=30
                )
                
                if delete_response.status_code == 204:
                    logger.info(f"🗑️ Ancienne release supprimée: {release['tag_name']}")
                    
            if releases_to_delete:
                logger.info(f"🧹 {len(releases_to_delete)} ancienne(s) release(s) supprimée(s)")
                
        except Exception as e:
            logger.error(f"Erreur nettoyage GitHub: {e}")
    
    def cleanup_old_backups(self):
        """Nettoie les anciennes sauvegardes locales"""
        try:
            backup_files = []
            for file in Path(self.config['backup_local_dir']).iterdir():
                if file.is_file() and file.suffix == '.zip':
                    backup_files.append((file, file.stat().st_mtime))
            
            backup_files.sort(key=lambda x: x[1], reverse=True)
            files_to_delete = backup_files[self.config['keep_local_backups']:]
            
            for file_path, _ in files_to_delete:
                file_path.unlink()
                logger.debug(f"🗑️ Fichier local supprimé: {file_path}")
            
            if files_to_delete:
                logger.info(f"🧹 {len(files_to_delete)} sauvegarde(s) locale(s) supprimée(s)")
                
        except Exception as e:
            logger.error(f"Erreur nettoyage local: {e}")
    
    def run_backup_cycle(self):
        """Cycle complet de sauvegarde - VERSION CORRIGÉE"""
        logger.info("🚀 ===== DÉBUT CYCLE SAUVEGARDE GITHUB =====")
        
        try:
            # AMÉLIORATION : Test de validité avant backup
            if not self.config['github_enabled']:
                logger.warning("⚠️ GitHub backup désactivé - cycle annulé")
                return False
            
            # Créer backup
            backup_path = self.create_backup()
            
            if backup_path:
                logger.info(f"✅ Backup créé: {backup_path}")
                
                # Upload vers GitHub
                github_success = self.upload_to_github(backup_path)
                
                # Nettoyage
                self.cleanup_old_backups()
                
                if github_success:
                    logger.info("✅ ===== CYCLE TERMINÉ AVEC SUCCÈS =====")
                    return True
                else:
                    logger.warning("⚠️ ===== CYCLE TERMINÉ AVEC AVERTISSEMENT =====")
                    logger.warning("   Backup local OK, GitHub KO")
                    return False
            else:
                logger.error("❌ ===== CYCLE ÉCHOUÉ =====")
                logger.error("   Impossible de créer la sauvegarde")
                return False
                
        except Exception as e:
            logger.error(f"❌ ===== ERREUR CYCLE =====")
            logger.error(f"   Exception: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return False

# Scheduler CORRIGÉ
def start_backup_scheduler():
    """Lance le scheduler GitHub backup - VERSION CORRIGÉE"""
    try:
        backup_manager = GitHubBackupManager()
        
        # CORRECTION 1 : Utiliser les variables d'environnement
        schedule_minutes = backup_manager.config['backup_schedule_minutes']
        
        logger.info(f"⏰ Configuration scheduler:")
        logger.info(f"   🔄 Fréquence: {schedule_minutes} minutes")
        logger.info(f"   📦 GitHub enabled: {backup_manager.config['github_enabled']}")
        logger.info(f"   🧪 Test immédiat: {backup_manager.config['immediate_backup_test']}")
        logger.info(f"   🚀 Force startup: {backup_manager.config['force_backup_on_start']}")
        
        # CORRECTION 2 : Programmer selon la variable d'environnement
        if schedule_minutes < 60:
            schedule.every(schedule_minutes).minutes.do(backup_manager.run_backup_cycle)
            logger.info(f"   📅 Programmé: Toutes les {schedule_minutes} minutes")
        else:
            schedule.every(schedule_minutes // 60).hours.do(backup_manager.run_backup_cycle)
            logger.info(f"   📅 Programmé: Toutes les {schedule_minutes // 60} heures")
        
        # CORRECTION 3 : Test immédiat si demandé
        if backup_manager.config['immediate_backup_test'] or backup_manager.config['force_backup_on_start']:
            logger.info("🧪 Exécution test immédiat...")
            backup_manager.run_backup_cycle()
        
        # CORRECTION 4 : Boucle scheduler améliorée
        logger.info("🎯 Scheduler GitHub backup démarré !")
        
        while True:
            schedule.run_pending()
            time.sleep(30)  # Vérifier toutes les 30 secondes
            
    except Exception as e:
        logger.error(f"❌ Erreur scheduler GitHub: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

# CORRECTION 5 : Configuration de démarrage améliorée
def setup_github_backup_info():
    """Affiche les informations de configuration au démarrage - VERSION CORRIGÉE"""
    logger.info("🚀 GITHUB RELEASES BACKUP SYSTEM - VERSION CORRIGÉE")
    logger.info("=" * 60)
    
    # Variables de configuration
    config_vars = {
        'GITHUB_BACKUP_ENABLED': os.environ.get('GITHUB_BACKUP_ENABLED', 'NON DÉFINI'),
        'GITHUB_TOKEN': '✅ Configuré' if os.environ.get('GITHUB_TOKEN') else '❌ MANQUANT',
        'GITHUB_REPO': os.environ.get('GITHUB_REPO', 'NON DÉFINI'),
        'KEEP_GITHUB_RELEASES': os.environ.get('KEEP_GITHUB_RELEASES', '10'),
        'BACKUP_SCHEDULE_MINUTES': os.environ.get('BACKUP_SCHEDULE_MINUTES', '120'),
        'IMMEDIATE_BACKUP_TEST': os.environ.get('IMMEDIATE_BACKUP_TEST', 'false'),
        'FORCE_BACKUP_ON_START': os.environ.get('FORCE_BACKUP_ON_START', 'false'),
        'DEBUG_GITHUB_BACKUP': os.environ.get('DEBUG_GITHUB_BACKUP', 'false')
    }
    
    logger.info("📋 Configuration complète:")
    for var, value in config_vars.items():
        logger.info(f"   {var}: {value}")
    
    if not os.environ.get('GITHUB_TOKEN'):
        logger.error("🚨 CONFIGURATION REQUISE:")
        logger.error("   1. Créer Personal Access Token sur GitHub")
        logger.error("   2. Ajouter GITHUB_TOKEN sur Render")
        logger.error("   3. Redémarrer le service")

# CORRECTION 6 : Auto-start amélioré
if __name__ != "__main__":  # Quand importé par app.py
    # Afficher les infos de configuration
    setup_github_backup_info()
    
    # CORRECTION MAJEURE : Thread NON daemon pour persistence
    backup_thread = threading.Thread(target=start_backup_scheduler, daemon=False)
    backup_thread.start()
    
    logger.info("🎯 GitHub Backup System CORRIGÉ démarré !")

# NOUVEAU : Fonction de test direct
def test_backup_immediate():
    """Fonction de test pour backup immédiat"""
    logger.info("🧪 TEST BACKUP IMMÉDIAT")
    backup_manager = GitHubBackupManager()
    result = backup_manager.run_backup_cycle()
    logger.info(f"🏁 Résultat test: {'✅ SUCCÈS' if result else '❌ ÉCHEC'}")
    return result

if __name__ == "__main__":
    # Test direct
    logger.info("🧪 Mode test GitHub backup")
    setup_github_backup_info()
    test_backup_immediate()
