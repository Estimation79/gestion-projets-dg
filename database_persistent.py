# database_persistent.py - Configuration Render Persistent Storage
# Version simplifiée pour migration rapide

import os
import shutil
import sqlite3
import logging
from datetime import datetime

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersistentERPDatabase:
    """
    Wrapper pour gérer le stockage persistant Render
    """
    
    def __init__(self):
        self.setup_persistent_paths()
        self.migrate_existing_data()
        
    def setup_persistent_paths(self):
        """Configure les chemins selon l'environnement"""
        
        # Détecter l'environnement
        self.is_render = os.path.exists('/opt/render/project')
        self.has_persistent_disk = os.path.exists('/opt/render/project/data')
        
        if self.is_render and self.has_persistent_disk:
            # Production Render avec persistent disk ✅
            self.data_dir = '/opt/render/project/data'
            self.db_path = os.path.join(self.data_dir, 'erp_production_dg.db')
            self.backup_dir = os.path.join(self.data_dir, 'backup_json')
            logger.info("🎯 Mode Render avec stockage persistant ACTIVÉ")
            
        elif self.is_render:
            # Render sans persistent disk ⚠️
            self.data_dir = '/tmp'
            self.db_path = '/tmp/erp_production_dg.db'
            self.backup_dir = '/tmp/backup_json'
            logger.warning("⚠️ Render détecté mais PAS de persistent disk")
            
        else:
            # Développement local 💻
            self.data_dir = '.'
            self.db_path = 'erp_production_dg.db'
            self.backup_dir = 'backup_json'
            logger.info("💻 Mode développement local")
        
        # Créer dossiers
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        logger.info(f"Base de données: {self.db_path}")
        logger.info(f"Stockage persistant: {'✅ OUI' if self.has_persistent_disk else '❌ NON'}")
    
    def migrate_existing_data(self):
        """Migre les données existantes vers le stockage persistant"""
        
        if not self.is_render or not self.has_persistent_disk:
            return
        
        # Chemins possibles des anciennes données
        old_paths = [
            '/opt/render/project/src/erp_production_dg.db',
            '/tmp/erp_production_dg.db',
            'erp_production_dg.db'
        ]
        
        for old_path in old_paths:
            if os.path.exists(old_path) and old_path != self.db_path:
                try:
                    # Copier vers stockage persistant
                    shutil.copy2(old_path, self.db_path)
                    logger.info(f"✅ Données migrées: {old_path} → {self.db_path}")
                    
                    # Vérifier intégrité
                    if self.verify_database():
                        logger.info("✅ Intégrité vérifiée")
                        break
                    
                except Exception as e:
                    logger.warning(f"⚠️ Erreur migration {old_path}: {e}")
    
    def verify_database(self):
        """Vérifie l'intégrité de la base"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()
            return result[0] == 'ok'
        except Exception as e:
            logger.error(f"Erreur vérification: {e}")
            return False
    
    def get_storage_info(self):
        """Retourne les infos de stockage pour le dashboard"""
        
        info = {
            'is_persistent': self.has_persistent_disk,
            'db_path': self.db_path,
            'db_exists': os.path.exists(self.db_path),
            'db_size_mb': 0,
            'storage_type': 'Persistant' if self.has_persistent_disk else 'Éphémère'
        }
        
        # Taille base
        if info['db_exists']:
            info['db_size_mb'] = round(os.path.getsize(self.db_path) / (1024*1024), 2)
        
        # Usage disque sur Render
        if self.is_render and self.has_persistent_disk:
            try:
                total, used, free = shutil.disk_usage(self.data_dir)
                info['disk_usage'] = {
                    'total_gb': round(total / (1024**3), 2),
                    'used_mb': round(used / (1024**2), 2),
                    'free_mb': round(free / (1024**2), 2),
                    'usage_percent': round((used / total) * 100, 1)
                }
            except Exception as e:
                logger.warning(f"Impossible de lire usage disque: {e}")
        
        return info
    
    def create_backup(self):
        """Crée une sauvegarde timestampée"""
        try:
            if not os.path.exists(self.db_path):
                return None
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"backup_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_file)
            
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"✅ Sauvegarde créée: {backup_path}")
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde: {e}")
            return None

# Fonction d'initialisation globale
def init_persistent_storage():
    """Initialise le gestionnaire de stockage persistant"""
    
    persistent_db = PersistentERPDatabase()
    return persistent_db

# Test de fonctionnement
if __name__ == "__main__":
    print("🧪 Test configuration stockage persistant...")
    
    db_manager = init_persistent_storage()
    info = db_manager.get_storage_info()
    
    print(f"Type stockage: {info['storage_type']}")
    print(f"Base existe: {info['db_exists']}")
    print(f"Taille: {info['db_size_mb']} MB")
    
    if info['is_persistent']:
        print("🎉 Configuration persistante RÉUSSIE !")
    else:
        print("⚠️ Configuration à finaliser")
