# db_downloader.py - Module de téléchargement de base de données pour ERP DG Inc.
"""
Module temporaire pour télécharger la base de données SQLite depuis Render
À intégrer dans app.py ou à utiliser comme page séparée
"""

import streamlit as st
import os
from pathlib import Path
import datetime

def create_db_downloader_page():
    """
    Page de téléchargement de base de données à ajouter temporairement à votre app
    """
    st.markdown("### 💾 Téléchargement Base de Données")
    st.markdown("---")
    
    # Recherche automatique de la base de données
    db_paths_to_check = [
        "data/erp_production_dg.db",           # Chemin principal
        "../data/erp_production_dg.db",       # Chemin parent
        "./erp_production_dg.db",             # Répertoire courant
        "/opt/render/project/data/erp_production_dg.db",  # Chemin Render
        "erp_production_dg.db"                # Nom direct
    ]
    
    found_db = None
    for db_path in db_paths_to_check:
        if os.path.exists(db_path):
            found_db = db_path
            break
    
    if found_db:
        st.success(f"✅ Base de données trouvée: `{found_db}`")
        
        # Informations sur le fichier
        try:
            file_size = os.path.getsize(found_db)
            file_size_mb = file_size / (1024 * 1024)
            modification_time = datetime.datetime.fromtimestamp(os.path.getmtime(found_db))
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Taille", f"{file_size_mb:.2f} MB")
            with col2:
                st.metric("📁 Taille", f"{file_size:,} bytes")
            with col3:
                st.metric("🕒 Modifié", modification_time.strftime("%d/%m/%Y %H:%M"))
                
        except Exception as e:
            st.warning(f"Erreur lecture infos fichier: {e}")
        
        st.markdown("---")
        
        # Bouton de téléchargement
        try:
            with open(found_db, 'rb') as file:
                file_data = file.read()
                
                # Nom du fichier avec timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                download_filename = f"erp_production_dg_backup_{timestamp}.db"
                
                st.download_button(
                    label="📥 Télécharger la Base de Données",
                    data=file_data,
                    file_name=download_filename,
                    mime="application/octet-stream",
                    help="Cliquer pour télécharger une copie de la base de données",
                    use_container_width=True,
                    type="primary"
                )
                
                st.info(f"💡 Le fichier sera téléchargé sous le nom: `{download_filename}`")
                
        except Exception as e:
            st.error(f"❌ Erreur lors de la lecture du fichier: {e}")
    
    else:
        st.error("❌ Base de données non trouvée")
        st.markdown("**Chemins vérifiés:**")
        for path in db_paths_to_check:
            exists = "✅" if os.path.exists(path) else "❌"
            st.markdown(f"- {exists} `{path}`")
            
        # Debug: lister les fichiers du répertoire courant
        st.markdown("---")
        st.markdown("**📁 Contenu du répertoire courant:**")
        try:
            current_files = os.listdir(".")
            for file in sorted(current_files):
                if os.path.isfile(file):
                    size = os.path.getsize(file)
                    st.markdown(f"- 📄 `{file}` ({size:,} bytes)")
                else:
                    st.markdown(f"- 📁 `{file}/`")
        except Exception as e:
            st.error(f"Erreur listage fichiers: {e}")
    
    st.markdown("---")
    
    # Instructions d'utilisation
    with st.expander("📋 Instructions d'utilisation", expanded=False):
        st.markdown("""
        **Pour utiliser ce téléchargeur:**
        
        1. **Intégration temporaire** - Ajoutez ce code à votre `app.py`:
        ```python
        # Dans votre fonction show_erp_main(), ajoutez cette condition:
        if page_to_show_val == "database_download":
            create_db_downloader_page()
            
        # Et ajoutez cette option dans available_pages:
        available_pages["💾 Télécharger DB"] = "database_download"
        ```
        
        2. **Page séparée** - Ou créez un fichier `db_download.py` séparé
        
        3. **Suppression** - Supprimez ce code après le téléchargement pour la sécurité
        
        **⚠️ Sécurité:** Ne laissez pas ce téléchargeur actif en production !
        """)
    
    # Informations sur l'environnement
    with st.expander("🔧 Informations Système", expanded=False):
        st.markdown("**Environnement détecté:**")
        
        # Variables d'environnement Render
        render_vars = {
            "RENDER": os.getenv("RENDER"),
            "RENDER_SERVICE_ID": os.getenv("RENDER_SERVICE_ID"),
            "RENDER_SERVICE_NAME": os.getenv("RENDER_SERVICE_NAME"),
        }
        
        for var, value in render_vars.items():
            if value:
                st.markdown(f"- `{var}`: {value}")
        
        # Répertoire de travail
        st.markdown(f"- **Répertoire courant**: `{os.getcwd()}`")
        
        # Utilisateur
        st.markdown(f"- **Utilisateur**: `{os.getenv('USER', 'inconnu')}`")

def add_db_downloader_to_sidebar():
    """
    Version sidebar compacte - À ajouter dans la sidebar de votre app
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💾 Base de Données")
    
    # Recherche rapide
    db_exists = any(os.path.exists(path) for path in [
        "data/erp_production_dg.db",
        "../data/erp_production_dg.db", 
        "./erp_production_dg.db"
    ])
    
    if db_exists:
        st.sidebar.success("DB trouvée ✅")
        
        # Trouver le bon chemin
        for path in ["data/erp_production_dg.db", "../data/erp_production_dg.db", "./erp_production_dg.db"]:
            if os.path.exists(path):
                found_path = path
                break
        
        try:
            with open(found_path, 'rb') as f:
                db_data = f.read()
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            
            st.sidebar.download_button(
                "💾 Télécharger DB",
                data=db_data,
                file_name=f"erp_dg_backup_{timestamp}.db",
                mime="application/octet-stream",
                use_container_width=True
            )
            
            # Taille du fichier
            size_mb = len(db_data) / (1024 * 1024)
            st.sidebar.caption(f"Taille: {size_mb:.1f} MB")
            
        except Exception as e:
            st.sidebar.error(f"Erreur: {str(e)[:30]}...")
    else:
        st.sidebar.warning("DB non trouvée ❌")

# ====================
# INTÉGRATION RAPIDE DANS APP.PY
# ====================

def integrate_downloader_in_main_app():
    """
    Code à ajouter directement dans votre fonction show_erp_main()
    """
    code_to_add = '''
    # À ajouter dans available_pages de show_erp_main():
    if has_all_permissions:  # Seulement pour les admins complets
        available_pages["💾 Télécharger DB"] = "database_download"
    
    # À ajouter dans la section de routage des pages:
    elif page_to_show_val == "database_download":
        create_db_downloader_page()
    '''
    
    return code_to_add

# ====================
# UTILISATION STANDALONE
# ====================

if __name__ == "__main__":
    # Version standalone pour test
    st.set_page_config(
        page_title="💾 DB Downloader - ERP DG Inc.",
        page_icon="💾",
        layout="wide"
    )
    
    st.title("💾 Téléchargeur Base de Données ERP DG Inc.")
    create_db_downloader_page()
