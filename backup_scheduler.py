# backup_scheduler.py - Version finale pour Render
import os
import sqlite3
import schedule
import time
import logging
import json
import smtplib
import zipfile
import threading
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ERPBackupManager:
    """Gestionnaire de sauvegardes automatiques ERP avec envoi email"""
    
    def __init__(self):
        self.config = {
            'db_path': os.environ.get('DB_PATH', '/opt/render/project/data/erp_production_dg.db'),
            'backup_local_dir': os.environ.get('BACKUP_LOCAL_DIR', '/opt/render/project/data/backups'),
            
            'email_enabled': os.environ.get('EMAIL_BACKUP_ENABLED', 'true').lower() == 'true',
            'email_recipient': os.environ.get('EMAIL_RECIPIENT', 'estimationls2023@gmail.com'),
            'email_sender': os.environ.get('EMAIL_SENDER'),
            'email_sender_name': os.environ.get('EMAIL_SENDER_NAME', 'ERP DG Inc. Backup System'),
            
            'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.environ.get('SMTP_PORT', '587')),
            'smtp_username': os.environ.get('SMTP_USERNAME'),
            'smtp_password': os.environ.get('SMTP_PASSWORD'),
            'smtp_use_tls': os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true',
            
            'keep_local_backups': int(os.environ.get('KEEP_LOCAL_BACKUPS', '12')),
            'max_email_size_mb': int(os.environ.get('MAX_EMAIL_SIZE_MB', '25'))
        }
        
        # Créer le dossier de backup
        Path(self.config['backup_local_dir']).mkdir(parents=True, exist_ok=True)
    
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
            
            # Métadonnées
            stats = self._get_database_stats(backup_db_path)
            metadata = {
                'backup_time': datetime.now().isoformat(),
                'backup_time_readable': datetime.now().strftime('%d/%m/%Y à %H:%M:%S'),
                'backup_size_mb': round(os.path.getsize(backup_db_path) / (1024*1024), 2),
                'company': 'Desmarais & Gagné Inc.',
                'database_stats': stats
            }
            
            metadata_path = os.path.join(self.config['backup_local_dir'], f"{backup_name}.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Compression
            zip_path = os.path.join(self.config['backup_local_dir'], f"{backup_name}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                zipf.write(backup_db_path, f"{backup_name}.db")
                zipf.write(metadata_path, f"{backup_name}_info.json")
            
            # Nettoyage
            os.remove(backup_db_path)
            os.remove(metadata_path)
            
            logger.info(f"✅ Sauvegarde créée: {zip_path} ({metadata['backup_size_mb']} MB)")
            return zip_path
            
        except Exception as e:
            logger.error(f"❌ Erreur création sauvegarde: {e}")
            return None
    
    def _get_database_stats(self, db_path):
        """Récupère les statistiques de la base"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            stats = {}
            tables = ['projects', 'companies', 'employees', 'formulaires', 'work_centers', 'operations']
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[table] = cursor.fetchone()[0]
                except:
                    stats[table] = 0
            
            stats['total_records'] = sum(stats.values())
            conn.close()
            return stats
            
        except Exception:
            return {}
    
    def send_backup_email(self, backup_path):
        """Envoie la sauvegarde par email"""
        if not self.config['email_enabled']:
            logger.info("📧 Envoi email désactivé")
            return True
        
        try:
            file_size_mb = os.path.getsize(backup_path) / (1024 * 1024)
            
            if file_size_mb > self.config['max_email_size_mb']:
                logger.warning(f"📧 Fichier trop volumineux ({file_size_mb:.1f}MB)")
                return False
            
            # Charger métadonnées
            metadata = self._load_backup_metadata(backup_path)
            
            # Créer email
            msg = MIMEMultipart()
            msg['From'] = f"{self.config['email_sender_name']} <{self.config['email_sender']}>"
            msg['To'] = self.config['email_recipient']
            msg['Subject'] = f"🏭 Sauvegarde ERP DG Inc. - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            
            # Corps HTML
            body = self._create_email_body(metadata, file_size_mb)
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            # Pièce jointe
            with open(backup_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {os.path.basename(backup_path)}'
            )
            msg.attach(part)
            
            # Envoi
            self._send_email(msg)
            
            logger.info(f"📧 ✅ Email envoyé avec succès à {self.config['email_recipient']}")
            return True
            
        except Exception as e:
            logger.error(f"📧 ❌ Erreur envoi email: {e}")
            return False
    
    def _load_backup_metadata(self, backup_path):
        """Charge les métadonnées du ZIP"""
        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                for file in zipf.namelist():
                    if file.endswith('_info.json'):
                        with zipf.open(file) as json_file:
                            return json.load(json_file)
            return {}
        except Exception:
            return {}
    
    def _create_email_body(self, metadata, file_size_mb):
        """Crée le corps de l'email en HTML"""
        stats = metadata.get('database_stats', {})
        
        stats_rows = ""
        for table, count in stats.items():
            if table != 'total_records':
                table_display = table.replace('_', ' ').title()
                stats_rows += f"<tr><td>{table_display}</td><td style='text-align: right;'>{count:,}</td></tr>"
        
        return f"""
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <div style="background: linear-gradient(135deg, #00A971 0%, #1F2937 100%); color: white; padding: 20px; border-radius: 8px;">
                <h2>🏭 ERP Production DG Inc.</h2>
                <h3>Sauvegarde Automatique</h3>
            </div>
            
            <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p>Bonjour,</p>
                <p style="color: #10b981; font-weight: bold;">✅ La sauvegarde automatique de l'ERP a été effectuée avec succès !</p>
                
                <div style="background: #e0f2fe; padding: 10px; border-radius: 4px; margin: 10px 0;">
                    <strong>📅 Date & Heure:</strong> {metadata.get('backup_time_readable', 'N/A')}<br>
                    <strong>📁 Taille:</strong> {file_size_mb:.2f} MB<br>
                    <strong>🏢 Entreprise:</strong> Desmarais & Gagné Inc.
                </div>
                
                <h4>📊 Contenu de la sauvegarde:</h4>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background-color: #f2f2f2;">
                            <th style="border: 1px solid #ddd; padding: 8px;">Module</th>
                            <th style="border: 1px solid #ddd; padding: 8px;">Enregistrements</th>
                        </tr>
                    </thead>
                    <tbody>
                        {stats_rows}
                        <tr style="background-color: #f0f9ff; font-weight: bold;">
                            <td style="border: 1px solid #ddd; padding: 8px;">TOTAL</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{stats.get('total_records', 0):,}</td>
                        </tr>
                    </tbody>
                </table>
                
                <p><strong>⏰ Prochaine sauvegarde:</strong> {(datetime.now() + timedelta(hours=2)).strftime('%d/%m/%Y à %H:%M')}</p>
            </div>
            
            <div style="color: #666; font-size: 12px;">
                <p>Message automatique - ERP Production DG Inc.<br>
                📧 estimationls2023@gmail.com</p>
            </div>
        </body>
        </html>
        """
    
    def _send_email(self, msg):
        """Envoie l'email via SMTP"""
        server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
        
        if self.config['smtp_use_tls']:
            server.starttls()
        
        if self.config['smtp_username'] and self.config['smtp_password']:
            server.login(self.config['smtp_username'], self.config['smtp_password'])
        
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.quit()
    
    def cleanup_old_backups(self):
        """Nettoie les anciennes sauvegardes"""
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
                logger.info(f"🧹 {len(files_to_delete)} ancienne(s) sauvegarde(s) supprimée(s)")
                
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")
    
    def run_backup_cycle(self):
        """Cycle complet de sauvegarde"""
        logger.info("🚀 Début cycle sauvegarde automatique")
        
        try:
            backup_path = self.create_backup()
            
            if backup_path:
                self.send_backup_email(backup_path)
                self.cleanup_old_backups()
                logger.info("✅ Cycle terminé avec succès")
            else:
                logger.error("❌ Cycle échoué")
                
        except Exception as e:
            logger.error(f"Erreur cycle: {e}")

# Scheduler en arrière-plan
def start_backup_scheduler():
    """Lance le scheduler en arrière-plan"""
    try:
        backup_manager = ERPBackupManager()
        
        # Programmer toutes les 2 heures
        schedule.every(2).hours.do(backup_manager.run_backup_cycle)
        
        # Première sauvegarde immédiate
        logger.info("🚀 Sauvegarde de démarrage...")
        backup_manager.run_backup_cycle()
        
        # Boucle scheduler
        logger.info("⏰ Scheduler backup actif - sauvegarde toutes les 2h")
        while True:
            schedule.run_pending()
            time.sleep(60)
            
    except Exception as e:
        logger.error(f"Erreur scheduler backup: {e}")

# Auto-start du scheduler
if __name__ != "__main__":  # Quand importé par app.py
    backup_thread = threading.Thread(target=start_backup_scheduler, daemon=True)
    backup_thread.start()
