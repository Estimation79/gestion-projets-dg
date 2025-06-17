# fix_database.py
# Script de correction des colonnes manquantes

import sqlite3
import os

def fix_erp_database():
    """Corrige les colonnes manquantes dans la base ERP"""
    
    db_path = "erp_production_dg.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Base de données {db_path} non trouvée!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔧 Correction de la base de données ERP...")
        
        # 1. Vérifier les colonnes existantes dans projects
        cursor.execute("PRAGMA table_info(projects)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"📋 Colonnes projects existantes: {len(columns)}")
        
        # 2. Ajouter colonnes manquantes
        if 'date_debut_reel' not in columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN date_debut_reel DATE")
            print("✅ Colonne date_debut_reel ajoutée")
        else:
            print("ℹ️ Colonne date_debut_reel déjà présente")
        
        if 'date_fin_reel' not in columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN date_fin_reel DATE")
            print("✅ Colonne date_fin_reel ajoutée")
        else:
            print("ℹ️ Colonne date_fin_reel déjà présente")
        
        # 3. Créer tables BT supplémentaires
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bt_assignations (
                id INTEGER PRIMARY KEY,
                bt_id INTEGER,
                employe_id INTEGER,
                date_assignation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                statut TEXT DEFAULT 'ASSIGNÉ',
                FOREIGN KEY (bt_id) REFERENCES formulaires(id),
                FOREIGN KEY (employe_id) REFERENCES employees(id)
            )
        """)
        print("✅ Table bt_assignations créée/vérifiée")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bt_reservations_postes (
                id INTEGER PRIMARY KEY,
                bt_id INTEGER,
                work_center_id INTEGER,
                date_reservation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_prevue DATE,
                date_liberation TIMESTAMP,
                statut TEXT DEFAULT 'RÉSERVÉ',
                FOREIGN KEY (bt_id) REFERENCES formulaires(id),
                FOREIGN KEY (work_center_id) REFERENCES work_centers(id)
            )
        """)
        print("✅ Table bt_reservations_postes créée/vérifiée")
        
        # 4. Commit et fermeture
        conn.commit()
        conn.close()
        
        print("🎉 Base de données corrigée avec succès!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur correction base: {e}")
        return False

if __name__ == "__main__":
    print("🏭 === CORRECTION ERP PRODUCTION DG INC. ===")
    success = fix_erp_database()
    
    if success:
        print("\n✅ CORRECTION TERMINÉE")
        print("👉 Vous pouvez maintenant redémarrer l'application")
    else:
        print("\n❌ CORRECTION ÉCHOUÉE")
        print("👉 Vérifiez les erreurs ci-dessus")
