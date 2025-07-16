#!/usr/bin/env python3
# test_db_connection.py - Script de diagnostic pour vérifier la connexion DB

import sqlite3
import os
import sys

def test_database_connection():
    """Test la connexion à la base de données et affiche des informations"""
    
    print("=== TEST DE CONNEXION BASE DE DONNÉES ===")
    print(f"Répertoire actuel: {os.getcwd()}")
    print(f"OS: {os.name}")
    print(f"Sur Render: {'OUI' if os.path.exists('/opt/render/project') else 'NON'}")
    
    # Chemins possibles
    possible_paths = [
        "/opt/render/project/data/erp_production_dg.db",  # Render avec persistent disk
        "erp_production_dg.db",  # Local
        "../data/erp_production_dg.db",  # Relatif depuis src
        "/tmp/erp_production_dg.db"  # Temporaire
    ]
    
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            print(f"\n✅ Base de données trouvée: {path}")
            print(f"   Taille: {os.path.getsize(path) / 1024 / 1024:.2f} MB")
            break
    
    if not db_path:
        print("\n❌ ERREUR: Aucune base de données trouvée!")
        print("Chemins testés:")
        for path in possible_paths:
            print(f"  - {path}")
        return
    
    # Test de connexion
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Vérifier les tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\n📊 Tables trouvées ({len(tables)}):")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Vérifier les projets
        try:
            cursor.execute("SELECT COUNT(*) FROM projects")
            count = cursor.fetchone()[0]
            print(f"\n📁 Nombre de projets: {count}")
            
            # Projets en cours
            cursor.execute("SELECT COUNT(*) FROM projects WHERE statut = 'EN COURS'")
            en_cours = cursor.fetchone()[0]
            print(f"   - En cours: {en_cours}")
            
            # Afficher quelques projets
            cursor.execute("""
                SELECT nom_projet, statut, prix_estime 
                FROM projects 
                WHERE statut = 'EN COURS' 
                LIMIT 3
            """)
            projets = cursor.fetchall()
            if projets:
                print("\n🔍 Exemples de projets en cours:")
                for p in projets:
                    print(f"   - {p[0]} ({p[1]}) - {p[2]:,.0f}$ CAD" if p[2] else f"   - {p[0]} ({p[1]})")
            
        except Exception as e:
            print(f"\n⚠️ Erreur lecture projets: {e}")
        
        # Vérifier l'inventaire
        try:
            cursor.execute("SELECT COUNT(*) FROM inventory_items")
            count = cursor.fetchone()[0]
            print(f"\n📦 Articles inventaire: {count}")
        except:
            print("\n⚠️ Table inventory_items non trouvée")
        
        # Vérifier les employés
        try:
            cursor.execute("SELECT COUNT(*) FROM employees")
            count = cursor.fetchone()[0]
            print(f"\n👥 Employés: {count}")
        except:
            print("\n⚠️ Table employees non trouvée")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ ERREUR connexion SQLite: {e}")
    
    # Test du module database_persistent
    print("\n=== TEST MODULE PERSISTENT STORAGE ===")
    try:
        from database_persistent import PersistentERPDatabase
        storage = PersistentERPDatabase()
        info = storage.get_storage_info()
        
        print(f"Environment: {info['environment_type']}")
        print(f"Storage: {info['storage_status']}")
        print(f"DB Path: {info['db_path']}")
        print(f"DB Exists: {info['db_exists']}")
        print(f"DB Size: {info['db_size_mb']} MB")
        
    except Exception as e:
        print(f"❌ Erreur test storage: {e}")

if __name__ == "__main__":
    test_database_connection()