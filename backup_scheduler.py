# backup_scheduler.py - Backup vers GitHub Releases
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
    """Gestionnaire de sauvegardes automatiques vers GitHub Releases"""
    
    def __init__(self):
        self.config = {
            'db_path': os.environ.get('DB_PATH', '/opt/render/project/data/erp_production_dg.db'),
            'backup_local_dir': os.environ.get('BACKUP_LOCAL_DIR', '/opt/render/project/data/backups'),
            
            # Configuration GitHub
            'github_enabled': os.environ.get('GITHUB_BACKUP_ENABLED', 'true').lower() == 'true',
            'github_token': os.environ.get('GITHUB_TOKEN'),  # Personal Access Token
            'github_repo': os.environ.get('GITHUB_REPO', 'votre-username/votre-repo'),
            'github_api_url': 'https://api.github.com',
            
            'keep_local_backups': int(os.environ.get('KEEP_LOCAL_BACKUPS', '5')),
            'keep_github_releases': int(os.environ.get('KEEP_GITHUB_RELEASES', '10')),
            'max_backup_size_mb': int(os.environ.get('MAX_BACKUP_SIZE_MB', '100'))
        }
        
        Path(self.config['backup_local_dir']).mkdir(parents=True, exist_ok=True)
        self._validate_github_config()
    
    def _validate_github_config(self):
        """Valide la configuration GitHub"""
        if not self.config['github_enabled']:
            logger.info("📊 Backup GitHub désactivé")
            return
        
        if not self.config['github_token']:
            logger.error("❌ GITHUB_TOKEN manquant")
            logger.info("📝 Créez un Personal Access Token sur GitHub:")
            logger.info("   1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)")
            logger.info("   2. Generate new token → Cochez 'repo' scope")
            logger.info("   3. Ajoutez GITHUB_TOKEN=votre_token dans Render")
            self.config['github_enabled'] = False
            return
        
        # Test de connexion GitHub
        try:
            headers = {'Authorization': f'token {self.config["github_token"]}'}
            response = requests.get(f"{self.config['github_api_url']}/repos/{self.config['github_repo']}", 
                                  headers=headers, timeout=10)
            
            if response.status_code == 200:
                repo_info = response.json()
                logger.info(f"✅ GitHub connecté: {repo_info['full_name']} (⭐ {repo_info['stargazers_count']})")
            else:
                logger.error(f"❌ Erreur GitHub API: {response.status_code} - {response.text}")
                self.config['github_enabled'] = False
                
        except Exception as e:
            logger.error(f"❌ Erreur connexion GitHub: {e}")
            self.config['github_enabled'] = False
    
    def create_backup(self):
        """Crée une sauvegarde de la base de données"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"erp_dg_backup_{timestamp}"
            
            if not os.path.exists(self.config['db_path']):
                logger.error(f"Base de données non trouvée: {self.config['db_path']}")
                return None
            
            # Sauvegarde SQLite
            backup_db_path = os.path.join(self.config['backup_local_dir'], f"{backup_name}.db")
            
            source_conn = sqlite3.connect(self.config['db_path'])
            backup_conn = sqlite3.connect(backup_db_path)
            
            with backup_conn:
                source_conn.backup(backup_conn)
            
            source_conn.close()
            backup_conn.close()
            
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
            logger.info(f"✅ Sauvegarde créée: {zip_path} ({final_size_mb} MB)")
            
            return zip_path
            
        except Exception as e:
            logger.error(f"❌ Erreur création sauvegarde: {e}")
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
            return stats
            
        except Exception:
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
        """Upload la sauvegarde vers GitHub Releases"""
        if not self.config['github_enabled']:
            logger.info("📊 Upload GitHub désactivé")
            return True
        
        try:
            file_size_mb = os.path.getsize(backup_path) / (1024 * 1024)
            
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
                'prerelease': True  # Marquer comme pre-release pour les backups
            }
            
            headers = {
                'Authorization': f'token {self.config["github_token"]}',
                'Content-Type': 'application/json'
            }
            
            logger.info("📦 Création de la release GitHub...")
            release_response = requests.post(
                f"{self.config['github_api_url']}/repos/{self.config['github_repo']}/releases",
                headers=headers,
                json=release_data,
                timeout=30
            )
            
            if release_response.status_code != 201:
                logger.error(f"❌ Erreur création release: {release_response.status_code} - {release_response.text}")
                return False
            
            release_info = release_response.json()
            upload_url = release_info['upload_url'].replace('{?name,label}', '')
            
            # 2. Upload du fichier
            logger.info("📤 Upload du fichier backup...")
            
            with open(backup_path, 'rb') as f:
                upload_headers = {
                    'Authorization': f'token {self.config["github_token"]}',
                    'Content-Type': 'application/zip'
                }
                
                upload_response = requests.post(
                    f"{upload_url}?name={backup_filename}&label=ERP Database Backup",
                    headers=upload_headers,
                    data=f,
                    timeout=120  # Timeout plus long pour l'upload
                )
            
            if upload_response.status_code == 201:
                download_url = upload_response.json()['browser_download_url']
                logger.info(f"✅ Backup uploadé vers GitHub: {download_url}")
                
                # Nettoyage des anciennes releases
                self._cleanup_old_github_releases()
                
                return True
            else:
                logger.error(f"❌ Erreur upload: {upload_response.status_code} - {upload_response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur upload GitHub: {e}")
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
🤖 Sauvegarde automatique générée toutes les 2 heures
"""
            
        except Exception:
            return f"""# 🏭 Sauvegarde ERP DG Inc.

**Date:** {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}

Sauvegarde automatique de la base de données ERP Production.
"""
    
    def _cleanup_old_github_releases(self):
        """Supprime les anciennes releases de backup"""
        try:
            headers = {'Authorization': f'token {self.config["github_token"]}'}
            
            # Récupérer toutes les releases
            response = requests.get(
                f"{self.config['github_api_url']}/repos/{self.config['github_repo']}/releases",
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                return
            
            releases = response.json()
            
            # Filtrer les releases de backup et les trier par date
            backup_releases = [r for r in releases if r['tag_name'].startswith('backup-')]
            backup_releases.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Supprimer les anciennes releases
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
            
            if files_to_delete:
                logger.info(f"🧹 {len(files_to_delete)} sauvegarde(s) locale(s) supprimée(s)")
                
        except Exception as e:
            logger.error(f"Erreur nettoyage local: {e}")
    
    def run_backup_cycle(self):
        """Cycle complet de sauvegarde"""
        logger.info("🚀 Début cycle sauvegarde GitHub")
        
        try:
            backup_path = self.create_backup()
            
            if backup_path:
                github_success = self.upload_to_github(backup_path)
                self.cleanup_old_backups()
                
                if github_success:
                    logger.info("✅ Cycle terminé avec succès (backup + GitHub)")
                else:
                    logger.warning("⚠️ Cycle terminé avec avertissement (backup OK, GitHub KO)")
            else:
                logger.error("❌ Cycle échoué - Impossible de créer la sauvegarde")
                
        except Exception as e:
            logger.error(f"❌ Erreur cycle: {e}")

# Scheduler
def start_backup_scheduler():
    """Lance le scheduler GitHub backup"""
    try:
        backup_manager = GitHubBackupManager()
        
        # Programmer toutes les 2 heures
        schedule.every(2).hours.do(backup_manager.run_backup_cycle)
        
        # Première sauvegarde après 2 minutes (délai de démarrage)
        schedule.every(2).minutes.do(backup_manager.run_backup_cycle).tag('startup')
        
        logger.info("⏰ Scheduler GitHub backup actif:")
        logger.info(f"   🔄 Fréquence: Toutes les 2 heures")
        logger.info(f"   📦 GitHub: {backup_manager.config['github_repo']}")
        logger.info(f"   📁 Local: {backup_manager.config['backup_local_dir']}")
        logger.info(f"   🗃️ Conservation: {backup_manager.config['keep_github_releases']} releases GitHub")
        
        while True:
            schedule.run_pending()
            
            # Supprimer le job de démarrage après exécution
            if schedule.get_jobs('startup'):
                completed_jobs = [job for job in schedule.get_jobs('startup') if job.should_run]
                if not completed_jobs:
                    schedule.clear('startup')
                    logger.info("✅ Sauvegarde de démarrage GitHub terminée")
            
            time.sleep(60)
            
    except Exception as e:
        logger.error(f"❌ Erreur scheduler GitHub: {e}")

# Configuration de démarrage automatique
def setup_github_backup_info():
    """Affiche les informations de configuration au démarrage"""
    logger.info("🚀 GITHUB RELEASES BACKUP SYSTEM")
    logger.info("=" * 50)
    
    # Variables requises
    required_vars = {
        'GITHUB_BACKUP_ENABLED': os.environ.get('GITHUB_BACKUP_ENABLED', 'NON DÉFINI'),
        'GITHUB_TOKEN': '✅ Configuré' if os.environ.get('GITHUB_TOKEN') else '❌ MANQUANT',
        'GITHUB_REPO': os.environ.get('GITHUB_REPO', 'NON DÉFINI'),
        'KEEP_GITHUB_RELEASES': os.environ.get('KEEP_GITHUB_RELEASES', '10'),
    }
    
    logger.info("📋 Configuration actuelle:")
    for var, value in required_vars.items():
        logger.info(f"   {var}: {value}")
    
    if not os.environ.get('GITHUB_TOKEN'):
        logger.error("🚨 CONFIGURATION REQUISE:")
        logger.error("   1. Créer Personal Access Token sur GitHub")
        logger.error("   2. Ajouter GITHUB_TOKEN sur Render")
        logger.error("   3. Ajouter GITHUB_REPO sur Render")
        logger.error("   4. Redémarrer le service")

# Auto-start du scheduler
if __name__ != "__main__":  # Quand importé par app.py
    # Afficher les infos de configuration
    setup_github_backup_info()
    
    # Démarrer le thread de backup
    backup_thread = threading.Thread(target=start_backup_scheduler, daemon=True)
    backup_thread.start()
    
    logger.info("🎯 GitHub Backup System démarré !")

if __name__ == "__main__":
    # Test direct
    logger.info("🧪 Mode test GitHub backup")
    setup_github_backup_info()
    backup_manager = GitHubBackupManager()
    backup_manager.run_backup_cycle()
