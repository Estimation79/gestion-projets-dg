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
    # Chemins possibles de la base de données
    possible_paths = [
        # Chemin local (dans le même dossier que l'app)
        "erp_production_dg.db",
        
        # Chemin Render (dans /project/data/)
        "/home/render/project/data/erp_production_dg.db",
        "../data/erp_production_dg.db",
        "data/erp_production_dg.db",
        
        # Autres chemins possibles
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "erp_production_dg.db"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "erp_production_dg.db"),
    ]
    
    # Vérifier si on est sur Render
    if os.environ.get('RENDER'):
        # Sur Render, prioriser le chemin /project/data/
        render_path = "/home/render/project/data/erp_production_dg.db"
        if os.path.exists(render_path):
            print(f"[Database Config] Base de données trouvée sur Render: {render_path}")
            return render_path
    
    # Chercher dans tous les chemins possibles
    for path in possible_paths:
        if os.path.exists(path):
            abs_path = os.path.abspath(path)
            print(f"[Database Config] Base de données trouvée: {abs_path}")
            return abs_path
    
    # Si aucun fichier n'est trouvé, créer dans le bon répertoire
    if os.environ.get('RENDER'):
        # Sur Render, créer dans /project/data/
        data_dir = "/home/render/project/data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
        default_path = os.path.join(data_dir, "erp_production_dg.db")
    else:
        # En local, créer dans le répertoire courant
        default_path = "erp_production_dg.db"
    
    print(f"[Database Config] Base de données non trouvée, utilisation du chemin par défaut: {default_path}")
    return default_path

def get_attachments_path():
    """
    Retourne le chemin correct pour les pièces jointes
    """
    if os.environ.get('RENDER'):
        attachments_dir = "/home/render/project/data/attachments"
    else:
        attachments_dir = "attachments"
    
    # Créer le dossier s'il n'existe pas
    os.makedirs(attachments_dir, exist_ok=True)
    return attachments_dir

def get_backup_path():
    """
    Retourne le chemin correct pour les sauvegardes
    """
    if os.environ.get('RENDER'):
        backup_dir = "/home/render/project/data/backups"
    else:
        backup_dir = "backups"
    
    # Créer le dossier s'il n'existe pas
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

# Variable globale pour le chemin de la base de données
DATABASE_PATH = get_database_path()

# Test au chargement du module
if __name__ == "__main__":
    print(f"Environnement: {'Render' if os.environ.get('RENDER') else 'Local'}")
    print(f"Chemin base de données: {DATABASE_PATH}")
    print(f"Fichier existe: {os.path.exists(DATABASE_PATH)}")
    print(f"Chemin pièces jointes: {get_attachments_path()}")
    print(f"Chemin sauvegardes: {get_backup_path()}")