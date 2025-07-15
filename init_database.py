"""
Module d'initialisation de la base de données
Force la connexion à la base de données au démarrage
"""

import streamlit as st
from database_config import DATABASE_PATH
import os

def init_database_connection():
    """
    Initialise la connexion à la base de données dans session_state
    """
    if 'erp_db' not in st.session_state:
        print(f"[Init DB] Initialisation de la connexion à la base de données...")
        print(f"[Init DB] DATABASE_PATH: {DATABASE_PATH}")
        print(f"[Init DB] Fichier existe: {os.path.exists(DATABASE_PATH)}")
        
        try:
            from erp_database import ERPDatabase
            
            if os.path.exists(DATABASE_PATH):
                st.session_state.erp_db = ERPDatabase(DATABASE_PATH)
                print(f"[Init DB] ✓ Base de données initialisée dans session_state")
                
                # Test de connexion
                with st.session_state.erp_db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM projects")
                    count = cursor.fetchone()[0]
                    print(f"[Init DB] ✓ Test connexion réussi - {count} projets trouvés")
                    
                return True
            else:
                print(f"[Init DB] ❌ Fichier base de données non trouvé: {DATABASE_PATH}")
                return False
                
        except Exception as e:
            print(f"[Init DB] ❌ Erreur lors de l'initialisation: {e}")
            import traceback
            print(f"[Init DB] Traceback: {traceback.format_exc()}")
            return False
    else:
        print(f"[Init DB] Base de données déjà initialisée dans session_state")
        return True

# Initialiser automatiquement au chargement du module
if 'streamlit' in globals():
    init_database_connection()