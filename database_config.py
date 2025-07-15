"""
Configuration de la base de données pour différents environnements
Gère automatiquement les chemins pour local et Render
"""

import os
import sys

def get_database_path():
    """
    Retourne le chemin correct de la base de données selon l'environnement
    """
    db_filename = "erp_production_dg.db"
    
    # Détecter l'environnement et définir les chemins à vérifier
    if os.environ.get('RENDER'):
        # Sur Render, vérifier plusieurs emplacements possibles
        possible_paths = [
            os.path.join(os.path.expanduser("~"), "project", "data", db_filename),
            os.path.join("/opt/render/project/src/data", db_filename),
            os.path.join("../data", db_filename),
            os.path.join("data", db_filename),
            db_filename  # Répertoire courant
        ]
        default_dir = os.path.join(os.path.expanduser("~"), "project", "data")
    else:
        # En local, chercher dans le répertoire courant
        possible_paths = [
            db_filename,
            os.path.join("data", db_filename)
        ]
        default_dir = "."
    
    # Chercher le fichier existant
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            print(f"[Database Config] Base de données trouvée: {abs_path}")
            return abs_path
    
    # Si non trouvé, retourner le chemin par défaut
    if not os.path.exists(default_dir):
        try:
            os.makedirs(default_dir, exist_ok=True)
            print(f"[Database Config] Répertoire créé: {default_dir}")
        except Exception as e:
            print(f"[Database Config] Impossible de créer le répertoire: {e}")
    
    default_path = os.path.join(default_dir, db_filename)
    print(f"[Database Config] Base de données non trouvée, chemin par défaut: {default_path}")
    return default_path

def get_attachments_path():
    """
    Retourne le chemin correct pour les pièces jointes
    """
    if os.environ.get('RENDER'):
        base_dir = os.path.join(os.path.expanduser("~"), "project", "data")
    else:
        base_dir = "."
    
    attachments_dir = os.path.join(base_dir, "attachments")
    os.makedirs(attachments_dir, exist_ok=True)
    return attachments_dir

def get_backup_path():
    """
    Retourne le chemin correct pour les sauvegardes
    """
    if os.environ.get('RENDER'):
        base_dir = os.path.join(os.path.expanduser("~"), "project", "data")
    else:
        base_dir = "."
    
    backup_dir = os.path.join(base_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

# Variable globale pour le chemin de la base de données
DATABASE_PATH = get_database_path()

# Test au chargement du module
if __name__ == "__main__":
    print("=== Configuration Base de Données ===")
    print(f"Environnement: {'Render' if os.environ.get('RENDER') else 'Local'}")
    print(f"Répertoire de travail: {os.getcwd()}")
    print(f"Chemin base de données: {DATABASE_PATH}")
    print(f"Base de données existe: {os.path.exists(DATABASE_PATH)}")
    print(f"Chemin pièces jointes: {get_attachments_path()}")
    print(f"Chemin sauvegardes: {get_backup_path()}")
    
    # Test de lecture si le fichier existe
    if os.path.exists(DATABASE_PATH):
        try:
            import sqlite3
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            conn.close()
            print(f"Base de données valide avec {table_count} tables")
        except Exception as e:
            print(f"Erreur lors de la lecture de la DB: {e}")