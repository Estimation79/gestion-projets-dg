#!/usr/bin/env python
"""
Script de diagnostic pour tester la connexion DB sur Render
"""
import os
import sys

print("=== Test de connexion DB sur Render ===\n")

# 1. Vérifier l'environnement
print("1. ENVIRONNEMENT:")
print(f"   - RENDER env var: {os.environ.get('RENDER', 'Non défini')}")
print(f"   - Working directory: {os.getcwd()}")
print(f"   - Python path: {sys.executable}")

# 2. Lister les fichiers dans différents répertoires
print("\n2. RECHERCHE DE LA BASE DE DONNÉES:")
paths_to_check = [
    ".",
    "..",
    "../data",
    "/home/render/project/data",
    "/opt/render/project/src",
    "/opt/render/project/src/data",
    os.path.expanduser("~/project/data"),
]

db_found = False
for path in paths_to_check:
    try:
        if os.path.exists(path):
            files = os.listdir(path)
            db_files = [f for f in files if f.endswith('.db')]
            if db_files:
                print(f"   ✓ {path}: {db_files}")
                for db in db_files:
                    full_path = os.path.join(path, db)
                    size = os.path.getsize(full_path) / 1024 / 1024
                    print(f"      - {db}: {size:.2f} MB")
                    if db == "erp_production_dg.db":
                        db_found = True
                        print(f"      🎯 BASE DE DONNÉES TROUVÉE: {full_path}")
            else:
                print(f"   - {path}: Aucun fichier .db")
        else:
            print(f"   - {path}: N'existe pas")
    except Exception as e:
        print(f"   - {path}: Erreur - {e}")

# 3. Tester database_config.py
print("\n3. TEST DE database_config.py:")
try:
    from database_config import DATABASE_PATH, get_database_path
    print(f"   - DATABASE_PATH: {DATABASE_PATH}")
    print(f"   - Existe: {os.path.exists(DATABASE_PATH)}")
    
    # Forcer la détection
    detected_path = get_database_path()
    print(f"   - Chemin détecté: {detected_path}")
    print(f"   - Existe: {os.path.exists(detected_path)}")
except Exception as e:
    print(f"   ❌ Erreur import database_config: {e}")

# 4. Tester la connexion ERPDatabase
print("\n4. TEST DE CONNEXION ERPDatabase:")
try:
    from erp_database import ERPDatabase
    
    # Essayer différents chemins
    test_paths = [
        "erp_production_dg.db",
        "../data/erp_production_dg.db",
        "/home/render/project/data/erp_production_dg.db",
    ]
    
    for test_path in test_paths:
        if os.path.exists(test_path):
            print(f"\n   Test avec: {test_path}")
            try:
                db = ERPDatabase(test_path)
                # Tester une requête simple
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM projects")
                    count = cursor.fetchone()[0]
                    print(f"   ✅ Connexion réussie! Nombre de projets: {count}")
                    break
            except Exception as e:
                print(f"   ❌ Erreur connexion: {e}")
except Exception as e:
    print(f"   ❌ Erreur import ERPDatabase: {e}")

# 5. Variables d'environnement
print("\n5. VARIABLES D'ENVIRONNEMENT RENDER:")
render_vars = [
    "RENDER",
    "RENDER_SERVICE_NAME", 
    "RENDER_SERVICE_TYPE",
    "RENDER_GIT_COMMIT",
    "HOME",
    "PWD",
]
for var in render_vars:
    print(f"   - {var}: {os.environ.get(var, 'Non défini')}")

print("\n=== Fin du diagnostic ===")