# backup_scheduler.py - Système de Sauvegarde Automatique ERP avec Email
# Sauvegarde automatique toutes les 2 heures + envoi par email

import os
import shutil
import sqlite3
import schedule
import time
import logging
import json
import smtplib
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict, Any

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ERPBackupManager:
    """Gestionnaire de sauvegardes automatiques pour ERP Production DG Inc. avec envoi email"""
    
    def __init__(self):
        self.setup_config()
        self.setup_paths()
        
    def setup_config(self):
        """Configuration depuis variables d'environnement"""
        self.config = {
            # Chemins de base
            'db_path': os.environ.get('DB_PATH', '/opt/render/project/data/erp_production_dg.db'),
            'backup_local_dir': os.environ.get('BACKUP_LOCAL_DIR', '/opt/render/project/data/backups'),
            
            # Configuration Email
            'email_enabled': os.environ.get('EMAIL_BACKUP_ENABLED', 'true').lower() == 'true',
            'email_recipient': os.environ.get('EMAIL_RECIPIENT', 'estimationls2023@gmail.com'),
            'email_sender': os.environ.get('EMAIL_SENDER', 'noreply@dg-inc.com'),
            'email_sender_name': os.environ.get('EMAIL_SENDER_NAME', 'ERP DG Inc. Backup System'),
            
            # Configuration SMTP
            'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.environ.get('SMTP_PORT', '587')),
            'smtp_username': os.environ.get('SMTP_USERNAME'),
            'smtp_password': os.environ.get('SMTP_PASSWORD'),
            'smtp_use_tls': os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true',
            
            # Rétention des sauvegardes
            'keep_local_backups': int(os.environ.get('KEEP_LOCAL_BACKUPS', '12')),  # 12 = 1 jour
            'max_email_size_mb': int(os.environ.get('MAX_EMAIL_SIZE_MB', '25')),  # Limite Gmail
            
            # Options
            'compress_backups': True,  # Toujours compresser pour email
            'verify_backups': os.environ.get('VERIFY_BACKUPS', 'true').lower() == 'true'
        }
        
    def setup_paths(self):
        """Création des dossiers nécessaires"""
        try:
            Path(self.config['backup_local_dir']).mkdir(parents=True, exist_ok=True)
            logger.info(f"Dossier backup configuré: {self.config['backup_local_dir']}")
        except Exception as e:
            logger.error(f"Erreur création dossier backup: {e}")
    
    def create_backup(self) -> Optional[str]:
        """Crée une sauvegarde complète de la base de données"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"erp_dg_backup_{timestamp}"
            
            # Vérifier que la DB existe
            if not os.path.exists(self.config['db_path']):
                logger.error(f"Base de données non trouvée: {self.config['db_path']}")
                return None
            
            # Créer la sauvegarde SQLite
            backup_db_path = os.path.join(self.config['backup_local_dir'], f"{backup_name}.db")
            
            # Utiliser la méthode SQLite backup pour consistance
            source_conn = sqlite3.connect(self.config['db_path'])
            backup_conn = sqlite3.connect(backup_db_path)
            
            with backup_conn:
                source_conn.backup(backup_conn)
            
            source_conn.close()
            backup_conn.close()
            
            # Vérifier l'intégrité de la sauvegarde
            if self.config['verify_backups']:
                if not self._verify_backup(backup_db_path):
                    logger.error("Vérification de sauvegarde échouée")
                    os.remove(backup_db_path)
                    return None
            
            # Obtenir les statistiques de la base
            stats = self._get_database_stats(backup_db_path)
            
            # Créer métadonnées enrichies
            metadata = {
                'backup_time': datetime.now().isoformat(),
                'backup_time_readable': datetime.now().strftime('%d/%m/%Y à %H:%M:%S'),
                'original_db_path': self.config['db_path'],
                'backup_size_mb': round(os.path.getsize(backup_db_path) / (1024*1024), 2),
                'backup_type': 'automatic_scheduled_email',
                'app_version': 'ERP_Production_DG_v1.0',
                'company': 'Desmarais & Gagné Inc.',
                'database_stats': stats
            }
            
            metadata_path = os.path.join(self.config['backup_local_dir'], f"{backup_name}.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Compression obligatoire pour email
            final_backup_path = self._compress_backup(backup_db_path, metadata_path, backup_name)
            
            # Supprimer les fichiers non compressés
            os.remove(backup_db_path)
            os.remove(metadata_path)
            
            logger.info(f"✅ Sauvegarde créée: {final_backup_path} ({metadata['backup_size_mb']} MB)")
            return final_backup_path
            
        except Exception as e:
            logger.error(f"❌ Erreur création sauvegarde: {e}")
            return None
    
    def _get_database_stats(self, db_path: str) -> Dict[str, Any]:
        """Récupère les statistiques de la base de données"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            stats = {}
            
            # Tables principales et leur nombre d'enregistrements
            tables_to_check = [
                'projects', 'companies', 'employees', 'formulaires', 
                'work_centers', 'operations', 'materials', 'inventory_items'
            ]
            
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    stats[table] = count
                except:
                    stats[table] = 0
            
            # Calculer le total d'enregistrements
            stats['total_records'] = sum(stats.values())
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"Erreur récupération stats DB: {e}")
            return {}
    
    def _verify_backup(self, backup_path: str) -> bool:
        """Vérifie l'intégrité d'une sauvegarde"""
        try:
            conn = sqlite3.connect(backup_path)
            cursor = conn.cursor()
            
            # Test d'intégrité SQLite
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()
            
            # Vérifier quelques tables principales
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            conn.close()
            
            is_valid = (
                integrity_result and 
                integrity_result[0] == 'ok' and 
                len(tables) > 5  # Au moins 5 tables attendues
            )
            
            logger.info(f"Vérification backup: {'✅ OK' if is_valid else '❌ ÉCHEC'} - {len(tables)} tables")
            return is_valid
            
        except Exception as e:
            logger.error(f"Erreur vérification backup: {e}")
            return False
    
    def _compress_backup(self, db_path: str, metadata_path: str, backup_name: str) -> str:
        """Compresse une sauvegarde en ZIP"""
        try:
            zip_path = os.path.join(self.config['backup_local_dir'], f"{backup_name}.zip")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                zipf.write(db_path, f"{backup_name}.db")
                zipf.write(metadata_path, f"{backup_name}_info.json")
            
            # Calculer compression ratio
            original_size = os.path.getsize(db_path) + os.path.getsize(metadata_path)
            compressed_size = os.path.getsize(zip_path)
            ratio = (1 - compressed_size / original_size) * 100
            
            logger.info(f"Compression: {ratio:.1f}% ({original_size/1024/1024:.1f}MB → {compressed_size/1024/1024:.1f}MB)")
            return zip_path
            
        except Exception as e:
            logger.error(f"Erreur compression: {e}")
            return db_path
    
    def send_backup_email(self, backup_path: str) -> bool:
        """Envoie la sauvegarde par email"""
        if not self.config['email_enabled']:
            logger.info("📧 Envoi email désactivé")
            return True
        
        try:
            # Vérifier la taille du fichier
            file_size_mb = os.path.getsize(backup_path) / (1024 * 1024)
            if file_size_mb > self.config['max_email_size_mb']:
                logger.warning(f"📧 Fichier trop volumineux ({file_size_mb:.1f}MB > {self.config['max_email_size_mb']}MB)")
                return self._send_large_file_notification(backup_path, file_size_mb)
            
            # Charger les métadonnées
            metadata = self._load_backup_metadata(backup_path)
            
            # Créer le message email
            msg = MIMEMultipart()
            msg['From'] = f"{self.config['email_sender_name']} <{self.config['email_sender']}>"
            msg['To'] = self.config['email_recipient']
            msg['Subject'] = f"🏭 Sauvegarde ERP DG Inc. - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            
            # Corps du message
            body = self._create_email_body(metadata, file_size_mb)
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            # Ajouter le fichier en pièce jointe
            with open(backup_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {os.path.basename(backup_path)}'
            )
            msg.attach(part)
            
            # Envoyer l'email
            self._send_email(msg)
            
            logger.info(f"📧 ✅ Email envoyé avec succès à {self.config['email_recipient']}")
            return True
            
        except Exception as e:
            logger.error(f"📧 ❌ Erreur envoi email: {e}")
            return False
    
    def _load_backup_metadata(self, backup_path: str) -> Dict[str, Any]:
        """Charge les métadonnées d'une sauvegarde"""
        try:
            # Extraire les métadonnées du ZIP
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                for file in zipf.namelist():
                    if file.endswith('_info.json'):
                        with zipf.open(file) as json_file:
                            return json.load(json_file)
            
            # Métadonnées par défaut si non trouvées
            return {
                'backup_time_readable': datetime.now().strftime('%d/%m/%Y à %H:%M:%S'),
                'backup_size_mb': round(os.path.getsize(backup_path) / (1024*1024), 2),
                'database_stats': {}
            }
            
        except Exception as e:
            logger.error(f"Erreur chargement métadonnées: {e}")
            return {}
    
    def _create_email_body(self, metadata: Dict[str, Any], file_size_mb: float) -> str:
        """Crée le corps de l'email en HTML"""
        stats = metadata.get('database_stats', {})
        
        # Construire le tableau des statistiques
        stats_rows = ""
        if stats:
            for table, count in stats.items():
                if table != 'total_records':
                    table_display = table.replace('_', ' ').title()
                    stats_rows += f"<tr><td>{table_display}</td><td style='text-align: right;'>{count:,}</td></tr>"
        
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: linear-gradient(135deg, #00A971 0%, #1F2937 100%); color: white; padding: 20px; border-radius: 8px; }}
                .content {{ background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .stats-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                .stats-table th, .stats-table td {{ border: 1px solid #ddd; padding: 8px; }}
                .stats-table th {{ background-color: #f2f2f2; }}
                .footer {{ color: #666; font-size: 12px; margin-top: 20px; }}
                .success {{ color: #10b981; font-weight: bold; }}
                .info {{ background: #e0f2fe; padding: 10px; border-radius: 4px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🏭 ERP Production DG Inc.</h2>
                <h3>Sauvegarde Automatique</h3>
            </div>
            
            <div class="content">
                <p>Bonjour,</p>
                
                <p class="success">✅ La sauvegarde automatique de l'ERP a été effectuée avec succès !</p>
                
                <div class="info">
                    <strong>📅 Date & Heure:</strong> {metadata.get('backup_time_readable', 'N/A')}<br>
                    <strong>📁 Taille du fichier:</strong> {file_size_mb:.2f} MB<br>
                    <strong>🏢 Entreprise:</strong> Desmarais & Gagné Inc.<br>
                    <strong>⚙️ Système:</strong> ERP Production (Version 1.0)
                </div>
                
                <h4>📊 Contenu de la sauvegarde:</h4>
                <table class="stats-table">
                    <thead>
                        <tr>
                            <th>Module</th>
                            <th>Nombre d'enregistrements</th>
                        </tr>
                    </thead>
                    <tbody>
                        {stats_rows}
                        <tr style="background-color: #f0f9ff; font-weight: bold;">
                            <td>TOTAL</td>
                            <td style="text-align: right;">{stats.get('total_records', 0):,}</td>
                        </tr>
                    </tbody>
                </table>
                
                <h4>📎 Fichier joint:</h4>
                <p>Le fichier de sauvegarde compressé est joint à cet email. Il contient :</p>
                <ul>
                    <li>🗄️ Base de données SQLite complète</li>
                    <li>📋 Métadonnées de sauvegarde</li>
                    <li>✅ Vérification d'intégrité effectuée</li>
                </ul>
                
                <div class="info">
                    <strong>💡 Important:</strong> Conservez ce fichier en lieu sûr. 
                    Il peut être utilisé pour restaurer complètement l'ERP en cas de besoin.
                </div>
                
                <p><strong>⏰ Prochaine sauvegarde:</strong> {(datetime.now() + timedelta(hours=2)).strftime('%d/%m/%Y à %H:%M')}</p>
            </div>
            
            <div class="footer">
                <p>
                    Ce message a été généré automatiquement par le système de sauvegarde ERP.<br>
                    <strong>Desmarais & Gagné Inc.</strong> - Fabrication métallique et industrielle<br>
                    📧 estimationls2023@gmail.com
                </p>
            </div>
        </body>
        </html>
        """
        
        return body
    
    def _send_large_file_notification(self, backup_path: str, file_size_mb: float) -> bool:
        """Envoie une notification pour un fichier trop volumineux"""
        try:
            msg = MIMEMultipart()
            msg['From'] = f"{self.config['email_sender_name']} <{self.config['email_sender']}>"
            msg['To'] = self.config['email_recipient']
            msg['Subject'] = f"⚠️ Sauvegarde ERP DG Inc. - Fichier volumineux - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h3>⚠️ Sauvegarde ERP - Fichier trop volumineux</h3>
                
                <p>La sauvegarde automatique a été créée avec succès, mais le fichier est trop volumineux pour être envoyé par email.</p>
                
                <p><strong>Taille du fichier:</strong> {file_size_mb:.1f} MB<br>
                <strong>Limite email:</strong> {self.config['max_email_size_mb']} MB</p>
                
                <p><strong>Localisation du fichier sur le serveur:</strong><br>
                <code>{backup_path}</code></p>
                
                <p>La sauvegarde est disponible sur le serveur et peut être récupérée manuellement si nécessaire.</p>
                
                <p><em>Système de sauvegarde ERP - Desmarais & Gagné Inc.</em></p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            self._send_email(msg)
            
            logger.info(f"📧 ✅ Notification fichier volumineux envoyée")
            return True
            
        except Exception as e:
            logger.error(f"📧 ❌ Erreur notification fichier volumineux: {e}")
            return False
    
    def _send_email(self, msg: MIMEMultipart):
        """Envoie l'email via SMTP"""
        try:
            # Connexion au serveur SMTP
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            
            if self.config['smtp_use_tls']:
                server.starttls()
            
            # Authentification
            if self.config['smtp_username'] and self.config['smtp_password']:
                server.login(self.config['smtp_username'], self.config['smtp_password'])
            
            # Envoi
            text = msg.as_string()
            server.sendmail(msg['From'], msg['To'], text)
            server.quit()
            
        except Exception as e:
            raise Exception(f"Erreur SMTP: {e}")
    
    def cleanup_old_backups(self):
        """Nettoie les anciennes sauvegardes locales"""
        try:
            backup_files = []
            for file in Path(self.config['backup_local_dir']).iterdir():
                if file.is_file() and file.suffix == '.zip':
                    backup_files.append((file, file.stat().st_mtime))
            
            # Trier par date (plus récent en premier)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Supprimer les anciens (garder les N plus récents)
            files_to_delete = backup_files[self.config['keep_local_backups']:]
            
            deleted_count = 0
            for file_path, _ in files_to_delete:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Impossible de supprimer {file_path}: {e}")
            
            if deleted_count > 0:
                logger.info(f"🧹 {deleted_count} ancienne(s) sauvegarde(s) supprimée(s)")
            
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")
    
    def run_backup_cycle(self):
        """Exécute un cycle complet de sauvegarde avec email"""
        logger.info("🚀 Début cycle sauvegarde automatique avec email")
        
        try:
            # Créer la sauvegarde
            backup_path = self.create_backup()
            
            if backup_path:
                # Envoyer par email
                email_success = self.send_backup_email(backup_path)
                
                # Nettoyage des anciennes sauvegardes
                self.cleanup_old_backups()
                
                if email_success:
                    logger.info(f"✅ Cycle sauvegarde terminé avec succès - Email envoyé")
                else:
                    logger.warning(f"⚠️ Sauvegarde créée mais email échoué")
                
            else:
                logger.error("❌ Cycle sauvegarde échoué")
                
        except Exception as e:
            error_msg = f"Erreur cycle sauvegarde: {str(e)}"
            logger.error(error_msg)

def main():
    """Fonction principale - Lance le scheduler de backup avec email"""
    logger.info("🏭 Démarrage ERP Backup Scheduler avec Email")
    logger.info("📅 Programmation: sauvegarde toutes les 2 heures + envoi email")
    
    backup_manager = ERPBackupManager()
    
    # Programmer la sauvegarde toutes les 2 heures
    schedule.every(2).hours.do(backup_manager.run_backup_cycle)
    
    # Sauvegarde immédiate au démarrage
    logger.info("🚀 Sauvegarde initiale...")
    backup_manager.run_backup_cycle()
    
    # Boucle principale
    logger.info("⏰ Scheduler actif - En attente des prochaines sauvegardes...")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Vérifier chaque minute
            
        except KeyboardInterrupt:
            logger.info("🛑 Arrêt du scheduler demandé")
            break
        except Exception as e:
            logger.error(f"Erreur dans boucle principale: {e}")
            time.sleep(300)  # Attendre 5 minutes avant de reprendre

if __name__ == "__main__":
    main()
