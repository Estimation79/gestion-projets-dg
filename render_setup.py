#!/usr/bin/env python
"""
Script de configuration pour Render.com
Configure automatiquement les chemins et permissions pour l'environnement Render
"""

import os
import sys
import shutil

def setup_render_environment():
    """Configure l'environnement pour Render"""
    print("🚀 Configuration de l'environnement Render...")
    
    # Créer les répertoires nécessaires
    directories = [
        "/home/render/project/data",
        "/home/render/project/data/attachments",
        "/home/render/project/data/backups",
        "/home/render/project/data/backup_json"
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Répertoire créé: {directory}")
        else:
            print(f"ℹ️ Répertoire existant: {directory}")
    
    # Vérifier si la base de données existe dans le répertoire source
    source_db = "erp_production_dg.db"
    target_db = "/home/render/project/data/erp_production_dg.db"
    
    if os.path.exists(source_db) and not os.path.exists(target_db):
        print(f"📦 Copie de la base de données vers {target_db}")
        shutil.copy2(source_db, target_db)
        print("✅ Base de données copiée avec succès")
    elif os.path.exists(target_db):
        print(f"ℹ️ Base de données déjà présente: {target_db}")
    else:
        print("⚠️ Base de données source non trouvée, elle sera créée automatiquement")
    
    # Définir les permissions appropriées
    try:
        os.chmod("/home/render/project/data", 0o775)
        if os.path.exists(target_db):
            os.chmod(target_db, 0o664)
        print("✅ Permissions configurées")
    except Exception as e:
        print(f"⚠️ Impossible de définir les permissions: {e}")
    
    # Créer un fichier de test pour vérifier l'écriture
    test_file = "/home/render/project/data/test_write.txt"
    try:
        with open(test_file, "w") as f:
            f.write("Test d'écriture réussi")
        os.remove(test_file)
        print("✅ Test d'écriture réussi")
    except Exception as e:
        print(f"❌ Erreur lors du test d'écriture: {e}")
    
    print("\n✅ Configuration Render terminée!")
    print(f"📁 Répertoire de données: /home/render/project/data")
    print(f"🗄️ Base de données: {target_db}")

if __name__ == "__main__":
    # Vérifier si on est sur Render
    if os.environ.get('RENDER'):
        setup_render_environment()
    else:
        print("ℹ️ Ce script est conçu pour être exécuté sur Render.com")
        print("En environnement local, la configuration n'est pas nécessaire.")