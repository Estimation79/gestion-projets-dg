#!/usr/bin/env python3
# db_download.py - Script standalone pour télécharger la base de données ERP DG Inc.
"""
Script standalone Streamlit pour télécharger la base de données SQLite
Utilisation: streamlit run db_download.py
"""

import streamlit as st
import os
import datetime
import platform
import socket

# Configuration de la page
st.set_page_config(
    page_title="💾 DB Downloader - ERP DG Inc.",
    page_icon="💾",
    layout="wide",
    initial_sidebar_state="expanded"
)

def apply_styles():
    """Styles CSS pour une interface propre"""
    st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    
    .db-found {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        text-align: center;
    }
    
    .db-not-found {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        text-align: center;
    }
    
    .info-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .warning-box {
        background: #fef3c7;
        border: 1px solid #f59e0b;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        border-left: 4px solid #f59e0b;
    }
    
    .success-box {
        background: #dcfce7;
        border: 1px solid #10b981;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        border-left: 4px solid #10b981;
    }
    
    .code-block {
        background: #1f2937;
        color: #f9fafb;
        padding: 1rem;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

def get_system_info():
    """Récupère les informations système"""
    info = {
        'hostname': socket.gethostname(),
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'current_dir': os.getcwd(),
        'user': os.getenv('USER', os.getenv('USERNAME', 'inconnu')),
        'home': os.getenv('HOME', os.getenv('USERPROFILE', 'inconnu')),
    }
    
    # Variables d'environnement Render
    render_info = {
        'render': os.getenv('RENDER'),
        'render_service_id': os.getenv('RENDER_SERVICE_ID'),
        'render_service_name': os.getenv('RENDER_SERVICE_NAME'),
        'render_external_hostname': os.getenv('RENDER_EXTERNAL_HOSTNAME'),
        'render_internal_hostname': os.getenv('RENDER_INTERNAL_HOSTNAME'),
    }
    
    return info, render_info

def find_database():
    """Recherche la base de données dans différents emplacements"""
    possible_paths = [
        # Chemins relatifs
        "data/erp_production_dg.db",
        "../data/erp_production_dg.db", 
        "../../data/erp_production_dg.db",
        "./erp_production_dg.db",
        "erp_production_dg.db",
        
        # Chemins absolus Render
        "/opt/render/project/data/erp_production_dg.db",
        "/opt/render/project/src/data/erp_production_dg.db",
        "/app/data/erp_production_dg.db",
        
        # Autres chemins possibles
        "src/data/erp_production_dg.db",
        "app/data/erp_production_dg.db",
        "database/erp_production_dg.db",
    ]
    
    results = []
    for path in possible_paths:
        exists = os.path.exists(path)
        size = 0
        modified = None
        
        if exists:
            try:
                size = os.path.getsize(path)
                modified = datetime.datetime.fromtimestamp(os.path.getmtime(path))
            except Exception as e:
                size = f"Erreur: {e}"
                modified = "Erreur"
        
        results.append({
            'path': path,
            'exists': exists,
            'size': size,
            'modified': modified,
            'absolute_path': os.path.abspath(path) if exists else None
        })
    
    # Retourner le premier trouvé
    found = next((r for r in results if r['exists']), None)
    return found, results

def scan_directory(directory_path="."):
    """Scanne un répertoire pour trouver des fichiers .db"""
    db_files = []
    try:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.endswith('.db') or file.endswith('.sqlite') or file.endswith('.sqlite3'):
                    file_path = os.path.join(root, file)
                    try:
                        size = os.path.getsize(file_path)
                        modified = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                        db_files.append({
                            'path': file_path,
                            'name': file,
                            'size': size,
                            'modified': modified
                        })
                    except Exception:
                        pass
    except Exception as e:
        st.error(f"Erreur scan répertoire: {e}")
    
    return db_files

def main():
    """Interface principale du téléchargeur"""
    apply_styles()
    
    # Header principal
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h1>💾 Téléchargeur Base de Données</h1>
        <h3 style='color: #6b7280;'>ERP Production DG Inc.</h3>
        <p style='color: #9ca3af;'>Script standalone pour récupérer votre base de données SQLite</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Sidebar avec informations système
    with st.sidebar:
        st.markdown("### 🖥️ Informations Système")
        
        sys_info, render_info = get_system_info()
        
        # Informations de base
        st.markdown("#### 💻 Environnement")
        for key, value in sys_info.items():
            if value and value != 'inconnu':
                st.markdown(f"**{key.replace('_', ' ').title()}:** `{value}`")
        
        # Informations Render
        if any(render_info.values()):
            st.markdown("#### 🚀 Render")
            for key, value in render_info.items():
                if value:
                    st.markdown(f"**{key.replace('_', ' ').title()}:** `{value}`")
        
        st.markdown("---")
        
        # Heure actuelle
        current_time = datetime.datetime.now()
        st.markdown(f"**🕒 Heure:** {current_time.strftime('%H:%M:%S')}")
        st.markdown(f"**📅 Date:** {current_time.strftime('%d/%m/%Y')}")

    # Onglets principaux
    tab1, tab2, tab3 = st.tabs(["🎯 Téléchargement", "🔍 Recherche Avancée", "📋 Instructions"])
    
    with tab1:
        st.markdown("## 🎯 Téléchargement Principal")
        
        # Recherche automatique
        found_db, all_results = find_database()
        
        if found_db:
            st.markdown(f"""
            <div class="db-found">
                <h3>✅ Base de données trouvée !</h3>
                <p><strong>Chemin:</strong> {found_db['path']}</p>
                <p><strong>Chemin absolu:</strong> {found_db['absolute_path']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Informations sur le fichier
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if isinstance(found_db['size'], int):
                    size_mb = found_db['size'] / (1024 * 1024)
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4>📊 Taille</h4>
                        <p>{size_mb:.2f} MB</p>
                        <small>({found_db['size']:,} bytes)</small>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error(f"Erreur taille: {found_db['size']}")
            
            with col2:
                if found_db['modified']:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4>🕒 Modifié</h4>
                        <p>{found_db['modified'].strftime('%d/%m/%Y')}</p>
                        <small>{found_db['modified'].strftime('%H:%M:%S')}</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            with col3:
                # Calcul de l'âge du fichier
                if found_db['modified']:
                    age = datetime.datetime.now() - found_db['modified']
                    if age.days > 0:
                        age_str = f"{age.days} jour(s)"
                    elif age.seconds > 3600:
                        age_str = f"{age.seconds // 3600} heure(s)"
                    else:
                        age_str = f"{age.seconds // 60} minute(s)"
                    
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4>⏰ Âge</h4>
                        <p>{age_str}</p>
                        <small>depuis dernière modification</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Bouton de téléchargement principal
            try:
                with open(found_db['absolute_path'], 'rb') as file:
                    file_data = file.read()
                    
                    # Nom avec timestamp
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    download_filename = f"erp_production_dg_backup_{timestamp}.db"
                    
                    col_download1, col_download2 = st.columns([3, 1])
                    
                    with col_download1:
                        st.download_button(
                            label="📥 TÉLÉCHARGER LA BASE DE DONNÉES",
                            data=file_data,
                            file_name=download_filename,
                            mime="application/octet-stream",
                            help="Cliquer pour télécharger une sauvegarde complète",
                            use_container_width=True,
                            type="primary"
                        )
                    
                    with col_download2:
                        st.markdown(f"""
                        <div class="info-card" style="text-align: center;">
                            <strong>Nom du fichier:</strong><br>
                            <code>{download_filename}</code>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Vérification de l'intégrité
                    if len(file_data) > 0:
                        st.markdown(f"""
                        <div class="success-box">
                            ✅ <strong>Fichier prêt au téléchargement</strong><br>
                            Taille vérifiée: {len(file_data):,} bytes ({len(file_data) / (1024*1024):.2f} MB)
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("❌ Le fichier semble vide !")
                        
            except Exception as e:
                st.error(f"❌ Erreur lors de la lecture du fichier: {e}")
                
                # Essayer avec sudo ou permissions différentes
                st.markdown(f"""
                <div class="warning-box">
                    <strong>⚠️ Problème d'accès au fichier</strong><br>
                    Erreur: {e}<br><br>
                    <strong>Solutions possibles:</strong><br>
                    • Vérifier les permissions du fichier<br>
                    • Le fichier est peut-être verrouillé par l'application<br>
                    • Essayer via la console Render avec: <code>cp {found_db['path']} /tmp/backup.db</code>
                </div>
                """, unsafe_allow_html=True)
        
        else:
            st.markdown("""
            <div class="db-not-found">
                <h3>❌ Base de données non trouvée</h3>
                <p>Aucune base de données détectée dans les emplacements standards</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Afficher tous les chemins vérifiés
            st.markdown("### 🔍 Chemins vérifiés:")
            for result in all_results:
                status = "✅" if result['exists'] else "❌"
                st.markdown(f"{status} `{result['path']}`")
    
    with tab2:
        st.markdown("## 🔍 Recherche Avancée")
        
        # Scan automatique pour fichiers .db
        st.markdown("### 🔎 Scan automatique des fichiers de base de données")
        
        scan_path = st.text_input("Répertoire à scanner:", value=".", help="Répertoire de départ pour la recherche")
        
        if st.button("🚀 Lancer le scan", use_container_width=True):
            with st.spinner("Scan en cours..."):
                db_files = scan_directory(scan_path)
            
            if db_files:
                st.success(f"✅ {len(db_files)} fichier(s) de base de données trouvé(s)")
                
                for i, db_file in enumerate(db_files):
                    st.markdown(f"""
                    <div class="info-card">
                        <h5>📁 {db_file['name']}</h5>
                        <p><strong>Chemin:</strong> <code>{db_file['path']}</code></p>
                        <p><strong>Taille:</strong> {db_file['size'] / (1024*1024):.2f} MB ({db_file['size']:,} bytes)</p>
                        <p><strong>Modifié:</strong> {db_file['modified'].strftime('%d/%m/%Y %H:%M:%S')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Bouton de téléchargement pour chaque fichier
                    try:
                        with open(db_file['path'], 'rb') as f:
                            file_data = f.read()
                        
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        clean_name = db_file['name'].replace('.db', '').replace('.sqlite', '').replace('.sqlite3', '')
                        download_name = f"{clean_name}_backup_{timestamp}.db"
                        
                        st.download_button(
                            label=f"📥 Télécharger {db_file['name']}",
                            data=file_data,
                            file_name=download_name,
                            mime="application/octet-stream",
                            key=f"download_scan_{i}",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Erreur lecture {db_file['name']}: {e}")
            else:
                st.warning("Aucun fichier de base de données trouvé dans le répertoire spécifié")
        
        # Téléchargement manuel
        st.markdown("---")
        st.markdown("### ✏️ Téléchargement manuel")
        
        manual_path = st.text_input("Chemin complet vers le fichier:", placeholder="/chemin/vers/votre/fichier.db")
        
        if manual_path and st.button("📥 Télécharger fichier manuel", use_container_width=True):
            try:
                if os.path.exists(manual_path):
                    with open(manual_path, 'rb') as f:
                        manual_data = f.read()
                    
                    file_name = os.path.basename(manual_path)
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    download_name = f"manual_{timestamp}_{file_name}"
                    
                    st.download_button(
                        label=f"📥 Télécharger {file_name}",
                        data=manual_data,
                        file_name=download_name,
                        mime="application/octet-stream",
                        use_container_width=True
                    )
                else:
                    st.error(f"❌ Fichier non trouvé: {manual_path}")
            except Exception as e:
                st.error(f"❌ Erreur: {e}")
    
    with tab3:
        st.markdown("## 📋 Instructions d'utilisation")
        
        st.markdown("""
        ### 🚀 Pour utiliser ce script sur Render:
        
        #### **1. Créer le fichier**
        - Créez un fichier `db_download.py` dans votre projet GitHub
        - Copiez-y le code de ce script
        
        #### **2. Déployer sur Render**
        ```bash
        git add db_download.py
        git commit -m "Add database downloader"
        git push origin main
        ```
        
        #### **3. Accéder au script**
        - URL: `https://votre-app.onrender.com` (en remplaçant le script principal)
        - Ou configurez une route séparée
        
        #### **4. Alternative: Console Render**
        Si le script ne fonctionne pas, utilisez la console Render:
        ```bash
        # Copier la DB vers un dossier accessible
        cp data/erp_production_dg.db static/backup.db
        
        # Puis télécharger via:
        # https://votre-app.onrender.com/static/backup.db
        ```
        """)
        
        st.markdown("---")
        
        st.markdown("""
        ### ⚠️ Sécurité et Bonnes Pratiques
        
        - **🔒 Supprimez ce script** après usage (sécurité)
        - **💾 Sauvegardez régulièrement** votre base de données
        - **🔐 Ne laissez pas** les téléchargeurs en production
        - **✅ Vérifiez l'intégrité** des fichiers téléchargés
        """)
        
        # Informations de contact
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #6b7280; font-style: italic;'>
            💻 Script développé pour ERP Production DG Inc.<br>
            🛠️ Support technique disponible
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
