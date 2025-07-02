# migration_handler.py - Gestionnaire de migration pour Render
import sqlite3
import os
import streamlit as st
import shutil
from datetime import datetime

def check_if_migration_needed(db_path="erp_production_dg.db"):
    """Vérifie si la migration est nécessaire"""
    try:
        if not os.path.exists(db_path):
            return False
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(projects)")
        columns_info = cursor.fetchall()
        
        id_column = next((col for col in columns_info if col[1] == 'id'), None)
        if id_column:
            conn.close()
            return id_column[2].upper() == 'INTEGER'  # True si migration nécessaire
        
        conn.close()
        return False
    except Exception as e:
        st.error(f"Erreur vérification migration: {e}")
        return False

def drop_problematic_views(conn):
    """Supprime temporairement les vues qui pourraient poser problème"""
    problematic_views = [
        'view_manufacturing_routes_progress',
        'view_projects_complets', 
        'view_formulaires_complets',
        'view_bt_timetracker_integration'
    ]
    
    cursor = conn.cursor()
    dropped_views = []
    
    for view_name in problematic_views:
        try:
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name=?", (view_name,))
            view_sql = cursor.fetchone()
            
            if view_sql:
                dropped_views.append((view_name, view_sql[0]))
                cursor.execute(f"DROP VIEW IF EXISTS {view_name}")
                st.info(f"🗑️ Vue supprimée temporairement: {view_name}")
        except Exception as e:
            st.warning(f"⚠️ Erreur suppression vue {view_name}: {e}")
    
    return dropped_views

def recreate_views(conn, dropped_views):
    """Recrée les vues après migration"""
    cursor = conn.cursor()
    
    for view_name, view_sql in dropped_views:
        try:
            # Corriger la vue manufacturing_routes_progress
            if view_name == 'view_manufacturing_routes_progress':
                corrected_sql = view_sql.replace('o.updated_at', 'o.created_at')
                cursor.execute(corrected_sql)
                st.success(f"✅ Vue corrigée et recréée: {view_name}")
            else:
                cursor.execute(view_sql)
                st.success(f"✅ Vue recréée: {view_name}")
        except Exception as e:
            st.warning(f"⚠️ Erreur recréation vue {view_name}: {e}")

def run_database_migration(db_path="erp_production_dg.db"):
    """Exécute la migration de la base de données"""
    try:
        # Création d'une sauvegarde
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.backup_{timestamp}"
        
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            st.info(f"💾 Sauvegarde créée: {backup_path}")
        
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = OFF")
        
        cursor = conn.cursor()
        
        # Supprimer les vues problématiques
        dropped_views = drop_problematic_views(conn)
        
        # Sauvegarder les données existantes
        cursor.execute("SELECT * FROM projects")
        existing_projects = cursor.fetchall()
        st.info(f"📊 {len(existing_projects)} projets à migrer")
        
        # Renommer la table actuelle
        cursor.execute("ALTER TABLE projects RENAME TO projects_old")
        st.info("📝 Table renommée: projects → projects_old")
        
        # Créer la nouvelle table avec ID TEXT
        cursor.execute('''
            CREATE TABLE projects (
                id TEXT PRIMARY KEY,
                nom_projet TEXT NOT NULL,
                client_company_id INTEGER,
                client_contact_id INTEGER,
                client_nom_cache TEXT,
                client_legacy TEXT,
                statut TEXT DEFAULT 'À FAIRE',
                priorite TEXT DEFAULT 'MOYEN',
                tache TEXT,
                date_soumis DATE,
                date_prevu DATE,
                date_debut_reel DATE,
                date_fin_reel DATE,
                bd_ft_estime REAL,
                prix_estime REAL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_company_id) REFERENCES companies(id),
                FOREIGN KEY (client_contact_id) REFERENCES contacts(id)
            )
        ''')
        st.success("✅ Nouvelle table créée avec ID TEXT")
        
        # Copier les données
        if existing_projects:
            cursor.execute('''
                INSERT INTO projects 
                SELECT CAST(id AS TEXT), nom_projet, client_company_id, client_contact_id,
                       client_nom_cache, client_legacy, statut, priorite, tache,
                       date_soumis, date_prevu, date_debut_reel, date_fin_reel,
                       bd_ft_estime, prix_estime, description,
                       COALESCE(created_at, CURRENT_TIMESTAMP),
                       COALESCE(updated_at, CURRENT_TIMESTAMP)
                FROM projects_old
            ''')
            st.success(f"✅ {len(existing_projects)} projets migrés")
        
        # Mettre à jour les tables liées
        tables_to_update = [
            'project_assignments', 'operations', 'materials', 
            'time_entries', 'formulaires', 'project_attachments'
        ]
        
        for table in tables_to_update:
            try:
                cursor.execute(f'''
                    UPDATE {table} 
                    SET project_id = CAST(project_id AS TEXT)
                    WHERE project_id IS NOT NULL
                ''')
                st.success(f"✅ {table} mise à jour")
            except Exception as e:
                st.warning(f"⚠️ Erreur {table}: {e}")
        
        # Supprimer l'ancienne table
        cursor.execute("DROP TABLE projects_old")
        st.success("🗑️ Ancienne table supprimée")
        
        # Recréer les index
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_projects_client ON projects(client_company_id)',
            'CREATE INDEX IF NOT EXISTS idx_projects_statut ON projects(statut)',
            'CREATE INDEX IF NOT EXISTS idx_projects_priorite ON projects(priorite)',
            'CREATE INDEX IF NOT EXISTS idx_projects_dates ON projects(date_soumis, date_prevu)',
            'CREATE INDEX IF NOT EXISTS idx_projects_client_id ON projects(client_company_id)'
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        st.success("📇 Index recréés")
        
        # Recréer les vues
        recreate_views(conn, dropped_views)
        
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()
        
        st.success("✅ Migration terminée avec succès!")
        return True
        
    except Exception as e:
        st.error(f"❌ Erreur migration: {e}")
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        return False

def test_migration_success(db_path="erp_production_dg.db"):
    """Teste si la migration a réussi"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Test d'insertion ID alphanumériques
        test_id = "TEST-RENDER-001"
        cursor.execute('''
            INSERT INTO projects (id, nom_projet, statut, priorite, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (test_id, "Test Migration Render", "À FAIRE", "MOYEN", "Test de migration sur Render"))
        
        # Vérifier l'insertion
        cursor.execute("SELECT id, nom_projet FROM projects WHERE id = ?", (test_id,))
        result = cursor.fetchone()
        
        if result:
            # Nettoyer le test
            cursor.execute("DELETE FROM projects WHERE id = ?", (test_id,))
            conn.commit()
            conn.close()
            st.success("✅ Test IDs alphanumériques: RÉUSSI")
            return True
        else:
            conn.close()
            st.error("❌ Test IDs alphanumériques: ÉCHOUÉ")
            return False
            
    except Exception as e:
        st.error(f"❌ Erreur test: {e}")
        return False

def handle_database_migration():
    """Fonction principale pour gérer la migration sur Render"""
    
    # Vérifier la variable d'environnement
    migration_needed = os.getenv('DB_MIGRATION_NEEDED', 'false').lower() == 'true'
    
    if migration_needed:
        st.warning("🔧 Migration de base de données détectée")
        
        # Vérifier si la migration est vraiment nécessaire
        if check_if_migration_needed():
            st.info("🔄 Migration en cours...")
            
            with st.spinner("Migration de la base de données..."):
                if run_database_migration():
                    if test_migration_success():
                        st.balloons()
                        st.success("🎉 Migration terminée avec succès!")
                        st.info("ℹ️ Vous pouvez maintenant supprimer la variable DB_MIGRATION_NEEDED des paramètres Render")
                        return True
                    else:
                        st.error("❌ Migration réussie mais test échoué")
                        return False
                else:
                    st.error("❌ Échec de la migration")
                    return False
        else:
            st.info("✅ Migration déjà appliquée ou non nécessaire")
            st.info("ℹ️ Vous pouvez supprimer la variable DB_MIGRATION_NEEDED des paramètres Render")
            return True
    
    return True

# Pour tester en local
if __name__ == "__main__":
    # Simuler la variable d'environnement
    os.environ['DB_MIGRATION_NEEDED'] = 'true'
    
    st.title("Test Migration Handler")
    handle_database_migration()
