# login_portal.py - Portail d'Entrée Principal
# ERP Production DG Inc. - Page d'accueil avec authentification
# Redirection vers Interface Employé ou ERP Admin

import streamlit as st
import subprocess
import sys
import os
from datetime import datetime
import hashlib
from auth_config import ADMIN_PASSWORDS, hash_password, verify_password

# Configuration page Streamlit
st.set_page_config(
    page_title="🏭 Portail DG Inc.",
    page_icon="🏭",
    layout="centered",
    initial_sidebar_state="collapsed"
)

def apply_portal_styles():
    """Styles CSS pour le portail d'entrée"""
    st.markdown("""
    <style>
    /* Import de la police moderne */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Variables CSS globales */
    :root {
        --primary-color: #1E40AF;
        --primary-color-light: #3B82F6;
        --primary-color-dark: #1E3A8A;
        --accent-color: #F59E0B;
        --success-color: #10B981;
        --danger-color: #EF4444;
        --background-main: #FAFBFC;
        --text-primary: #1F2937;
        --text-secondary: #6B7280;
        --border-color: #E5E7EB;
        --shadow-light: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        --shadow-medium: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --gradient-secondary: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    
    /* Reset et base */
    .main {
        padding: 0 !important;
        background: var(--background-main);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .block-container {
        padding: 2rem 1rem !important;
        max-width: 800px !important;
    }
    
    /* Header principal */
    .portal-header {
        background: var(--gradient-primary);
        color: white;
        padding: 3rem 2rem;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 3rem;
        box-shadow: var(--shadow-medium);
        position: relative;
        overflow: hidden;
    }
    
    .portal-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: url("data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M20 20c0 11.046-8.954 20-20 20v20h40V20H20z'/%3E%3C/g%3E%3C/svg%3E") repeat;
        animation: move 20s linear infinite;
        z-index: 0;
    }
    
    @keyframes move {
        0% { transform: translate(0, 0); }
        100% { transform: translate(40px, 40px); }
    }
    
    .portal-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0 0 0.5rem 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        position: relative;
        z-index: 1;
    }
    
    .portal-header .subtitle {
        font-size: 1.2rem;
        font-weight: 300;
        opacity: 0.9;
        position: relative;
        z-index: 1;
    }
    
    /* Container des boutons d'accès */
    .access-container {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2rem;
        margin: 2rem 0;
    }
    
    @media (max-width: 768px) {
        .access-container {
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }
    }
    
    /* Cartes d'accès */
    .access-card {
        background: white;
        border-radius: 16px;
        padding: 2.5rem 2rem;
        text-align: center;
        box-shadow: var(--shadow-light);
        border: 2px solid transparent;
        transition: all 0.3s ease;
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }
    
    .access-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: var(--gradient-primary);
        transform: scaleX(0);
        transition: transform 0.3s ease;
    }
    
    .access-card:hover {
        transform: translateY(-5px);
        box-shadow: var(--shadow-medium);
        border-color: var(--primary-color-light);
    }
    
    .access-card:hover::before {
        transform: scaleX(1);
    }
    
    .access-card.employee {
        border-left: 4px solid var(--success-color);
    }
    
    .access-card.admin {
        border-left: 4px solid var(--primary-color);
    }
    
    .access-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
        display: block;
    }
    
    .access-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
    }
    
    .access-description {
        color: var(--text-secondary);
        font-size: 0.95rem;
        line-height: 1.6;
        margin-bottom: 1.5rem;
    }
    
    .access-features {
        list-style: none;
        padding: 0;
        margin: 1rem 0;
    }
    
    .access-features li {
        padding: 0.3rem 0;
        color: var(--text-secondary);
        font-size: 0.9rem;
    }
    
    /* Modal d'authentification admin */
    .auth-modal {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: var(--shadow-medium);
        border: 1px solid var(--border-color);
    }
    
    .auth-modal h3 {
        color: var(--primary-color);
        margin-bottom: 1.5rem;
        text-align: center;
    }
    
    /* Footer */
    .portal-footer {
        text-align: center;
        margin-top: 3rem;
        padding: 2rem;
        color: var(--text-secondary);
        font-size: 0.9rem;
        border-top: 1px solid var(--border-color);
        background: white;
        border-radius: 12px;
    }
    
    .status-info {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 2rem 0;
    }
    
    .status-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: var(--shadow-light);
        border-left: 4px solid var(--accent-color);
    }
    
    .status-number {
        font-size: 2rem;
        font-weight: 700;
        color: var(--primary-color);
        margin-bottom: 0.5rem;
    }
    
    .status-label {
        color: var(--text-secondary);
        font-size: 0.9rem;
    }
    
    /* Animations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .access-card {
        animation: fadeInUp 0.6s ease-out;
    }
    
    .access-card:nth-child(2) {
        animation-delay: 0.1s;
    }
    
    /* Boutons personnalisés */
    .stButton > button {
        width: 100%;
        background: var(--gradient-primary);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: var(--shadow-light);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-medium);
    }
    
    /* Messages d'alerte */
    .alert-success {
        background: #D1FAE5;
        border: 1px solid #10B981;
        color: #065F46;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .alert-error {
        background: #FEE2E2;
        border: 1px solid #EF4444;
        color: #991B1B;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    /* Masquer la sidebar et autres éléments Streamlit */
    .css-1d391kg {display: none;}
    .css-1rs6os {display: none;}
    .css-17ziqus {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

def get_system_stats():
    """Récupère quelques statistiques système pour l'affichage"""
    try:
        # Essayer de récupérer des stats de base si possible
        from erp_database import ERPDatabase
        db = ERPDatabase("erp_production_dg.db")
        
        stats = {
            'projets': db.get_table_count('projects'),
            'employes': db.get_table_count('employees'), 
            'entreprises': db.get_table_count('companies'),
            'postes': db.get_table_count('work_centers')
        }
        return stats
    except Exception:
        # Stats par défaut si erreur
        return {
            'projets': '150+',
            'employes': '45',
            'entreprises': '80+', 
            'postes': '61'
        }

def launch_employee_interface():
    """Lance l'interface employé dans un nouvel onglet/fenêtre"""
    try:
        # Créer un lien vers l'interface employé
        st.markdown("""
        <div class="alert-success">
            ✅ <strong>Interface Employé activée !</strong><br>
            L'interface de pointage va s'ouvrir...
        </div>
        """, unsafe_allow_html=True)
        
        # Script JavaScript pour ouvrir dans un nouvel onglet
        st.markdown("""
        <script>
        setTimeout(function() {
            window.open('employee_timetracker.py', '_blank');
        }, 1000);
        </script>
        """, unsafe_allow_html=True)
        
        # Alternative : bouton de redirection manuelle
        st.markdown("### 👥 Accès Interface Employé")
        st.info("🔗 Si l'interface ne s'ouvre pas automatiquement, lancez : `streamlit run employee_timetracker.py --server.port 8502`")
        
        if st.button("🔄 Retour au Portail", key="back_to_portal"):
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ Erreur lancement interface employé: {e}")

def authenticate_admin():
    """Interface d'authentification admin"""
    st.markdown("""
    <div class="auth-modal">
        <h3>🔐 Authentification Administrateur</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Formulaire d'authentification
    with st.form("admin_auth_form", clear_on_submit=False):
        username = st.text_input("👤 Nom d'utilisateur:", placeholder="admin")
        password = st.text_input("🔒 Mot de passe:", type="password", placeholder="Entrez votre mot de passe")
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("🚀 Accéder à l'ERP", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("❌ Annuler", use_container_width=True)
        
        if submitted:
            if verify_password(username, password):
                st.session_state.admin_authenticated = True
                st.session_state.admin_username = username
                st.markdown("""
                <div class="alert-success">
                    ✅ <strong>Authentification réussie !</strong><br>
                    Accès à l'ERP autorisé. Redirection en cours...
                </div>
                """, unsafe_allow_html=True)
                
                # Redirection vers l'ERP principal
                st.info("🚀 Lancez l'ERP principal avec : `streamlit run app.py --server.port 8501`")
                
                # Alternative : instruction pour lancer l'ERP
                st.markdown("### 🏭 Accès ERP Complet")
                st.success(f"👋 Bienvenue **{username}** ! Vous avez accès à toutes les fonctionnalités ERP.")
                
            else:
                st.markdown("""
                <div class="alert-error">
                    ❌ <strong>Authentification échouée !</strong><br>
                    Nom d'utilisateur ou mot de passe incorrect.
                </div>
                """, unsafe_allow_html=True)
        
        if cancel:
            st.session_state.show_admin_auth = False
            st.rerun()

def main():
    """Fonction principale du portail"""
    
    # Initialisation des variables de session
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    if 'show_admin_auth' not in st.session_state:
        st.session_state.show_admin_auth = False
    if 'show_employee_interface' not in st.session_state:
        st.session_state.show_employee_interface = False
    
    # Appliquer les styles
    apply_portal_styles()
    
    # Header principal
    current_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%d/%m/%Y")
    
    st.markdown(f"""
    <div class="portal-header">
        <h1>🏭 PORTAIL DG INC.</h1>
        <div class="subtitle">
            Système de Gestion Intégré • Production & Métallurgie<br>
            📅 {current_date} • 🕒 {current_time}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Affichage selon l'état
    if st.session_state.show_employee_interface:
        launch_employee_interface()
        return
    
    if st.session_state.show_admin_auth:
        authenticate_admin()
        return
    
    # Interface principale avec les deux options d'accès
    st.markdown("## 🚪 Choisissez votre mode d'accès")
    
    # Container des cartes d'accès
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="access-card employee">
            <span class="access-icon">👥</span>
            <div class="access-title">EMPLOYÉ</div>
            <div class="access-description">
                Interface de pointage simplifiée pour les employés de production
            </div>
            <ul class="access-features">
                <li>⏰ Pointage entrée/sortie</li>
                <li>🔧 Bons de Travail assignés</li>
                <li>📊 Suivi temps en temps réel</li>
                <li>📱 Interface simple et rapide</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("👥 ACCÈS EMPLOYÉ", key="employee_access", use_container_width=True, type="primary"):
            st.session_state.show_employee_interface = True
            st.rerun()
    
    with col2:
        st.markdown("""
        <div class="access-card admin">
            <span class="access-icon">👨‍💼</span>
            <div class="access-title">ADMINISTRATEUR</div>
            <div class="access-description">
                ERP complet avec toutes les fonctionnalités de gestion
            </div>
            <ul class="access-features">
                <li>📋 Gestion projets complète</li>
                <li>🤝 CRM et fournisseurs</li>
                <li>📑 Formulaires et documents</li>
                <li>🤖 Assistant IA métallurgie</li>
                <li>📊 Analyse et reporting</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("👨‍💼 ACCÈS ADMIN", key="admin_access", use_container_width=True, type="secondary"):
            st.session_state.show_admin_auth = True
            st.rerun()
    
    # Statistiques système
    stats = get_system_stats()
    
    st.markdown("---")
    st.markdown("### 📊 État du Système")
    
    st.markdown("""
    <div class="status-info">
        <div class="status-card">
            <div class="status-number">{}</div>
            <div class="status-label">Projets Actifs</div>
        </div>
        <div class="status-card">
            <div class="status-number">{}</div>
            <div class="status-label">Employés ERP</div>
        </div>
        <div class="status-card">
            <div class="status-number">{}</div>
            <div class="status-label">Entreprises Clientes</div>
        </div>
        <div class="status-card">
            <div class="status-number">{}</div>
            <div class="status-label">Postes de Travail</div>
        </div>
    </div>
    """.format(stats['projets'], stats['employes'], stats['entreprises'], stats['postes']), 
    unsafe_allow_html=True)
    
    # Footer avec informations
    st.markdown("""
    <div class="portal-footer">
        <h4>🏭 ERP Production DG Inc.</h4>
        <p>
            <strong>Desmarais & Gagné Inc.</strong> • Fabrication métallique et industrielle<br>
            🗄️ Architecture unifiée • 📑 Formulaires intégrés • 🤖 Assistant IA • ⏱️ TimeTracker synchronisé<br>
            💾 Stockage persistant • 🔄 Navigation fluide • 🏪 Gestion fournisseurs
        </p>
        <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color);">
            <small>
                👥 <strong>Employés:</strong> Accès direct au pointage<br>
                👨‍💼 <strong>Admins:</strong> Authentification requise pour ERP complet<br>
                🔒 Système sécurisé • ✅ Données en temps réel
            </small>
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
