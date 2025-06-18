# app_with_auth.py - ERP avec Authentification Intégrée
# ERP Production DG Inc. - Wrapper d'authentification pour l'ERP principal
# Vérifie l'authentification avant d'autoriser l'accès à l'ERP complet

import streamlit as st
import sys
import os
from datetime import datetime, timedelta
from auth_config import verify_password, get_user_permissions, get_user_display_name, log_login_attempt

# Configuration page
st.set_page_config(
    page_title="🏭 ERP Production DG Inc. - Admin",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

def apply_auth_styles():
    """Styles pour la page d'authentification"""
    st.markdown("""
    <style>
    .auth-container {
        max-width: 400px;
        margin: 2rem auto;
        padding: 2rem;
        background: white;
        border-radius: 16px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        border: 1px solid #e5e7eb;
    }
    
    .auth-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .auth-header h2 {
        color: #1E40AF;
        margin-bottom: 0.5rem;
    }
    
    .auth-header p {
        color: #6B7280;
        font-size: 0.9rem;
    }
    
    .auth-form {
        margin-bottom: 1.5rem;
    }
    
    .security-info {
        background: #F3F4F6;
        padding: 1rem;
        border-radius: 8px;
        margin-top: 1rem;
        font-size: 0.85rem;
        color: #374151;
    }
    
    .welcome-banner {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .session-info {
        background: #F0F9FF;
        border: 1px solid #0EA5E9;
        padding: 0.75rem;
        border-radius: 6px;
        margin-bottom: 1rem;
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)

def check_session_validity():
    """Vérifie si la session est encore valide"""
    if 'admin_login_time' not in st.session_state:
        return False
    
    login_time = st.session_state.admin_login_time
    session_duration = datetime.now() - login_time
    
    # Session expire après 2 heures
    if session_duration > timedelta(hours=2):
        # Session expirée
        st.session_state.admin_authenticated = False
        st.session_state.admin_username = None
        st.session_state.admin_login_time = None
        return False
    
    return True

def show_admin_login():
    """Interface de connexion administrateur"""
    apply_auth_styles()
    
    st.markdown("""
    <div class="auth-container">
        <div class="auth-header">
            <h2>🔐 Authentification Administrateur</h2>
            <p>ERP Production DG Inc. - Accès Restreint</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Formulaire de connexion
    with st.form("admin_login_form", clear_on_submit=False):
        st.markdown("### 👤 Identifiants")
        
        username = st.text_input(
            "Nom d'utilisateur:",
            placeholder="admin / dg_admin / superviseur / direction",
            help="Utilisez un des comptes administrateur configurés"
        )
        
        password = st.text_input(
            "Mot de passe:",
            type="password",
            placeholder="Entrez votre mot de passe"
        )
        
        # Options de connexion
        remember_me = st.checkbox("Se souvenir de moi (2h)", value=True)
        
        # Boutons
        col1, col2 = st.columns(2)
        with col1:
            login_btn = st.form_submit_button("🚀 Se Connecter", use_container_width=True, type="primary")
        with col2:
            portal_btn = st.form_submit_button("🏠 Retour Portail", use_container_width=True)
        
        # Traitement du formulaire
        if login_btn:
            if not username or not password:
                st.error("❌ Veuillez remplir tous les champs")
            else:
                # Tentative d'authentification
                if verify_password(username, password):
                    # Connexion réussie
                    st.session_state.admin_authenticated = True
                    st.session_state.admin_username = username
                    st.session_state.admin_login_time = datetime.now()
                    st.session_state.admin_permissions = get_user_permissions(username)
                    
                    # Log de connexion
                    log_login_attempt(username, True)
                    
                    st.success(f"✅ Connexion réussie ! Bienvenue {get_user_display_name(username)}")
                    st.rerun()
                    
                else:
                    # Connexion échouée
                    log_login_attempt(username, False)
                    st.error("❌ Nom d'utilisateur ou mot de passe incorrect")
                    
                    # Incrémenter compteur d'échecs
                    if 'login_attempts' not in st.session_state:
                        st.session_state.login_attempts = 0
                    st.session_state.login_attempts += 1
                    
                    if st.session_state.login_attempts >= 3:
                        st.warning("⚠️ Trop de tentatives échouées. Veuillez patienter.")
        
        if portal_btn:
            # Redirection vers le portail
            st.info("🏠 Retour au portail principal...")
            st.markdown("**Instruction:** Lancez `streamlit run login_portal.py` pour revenir au portail")
    
    # Informations de sécurité
    st.markdown("""
    <div class="security-info">
        <strong>🔒 Informations de Sécurité</strong><br>
        • Comptes disponibles: admin, dg_admin, superviseur, direction<br>
        • Sessions expirent après 2 heures d'inactivité<br>
        • Toutes les connexions sont auditées<br>
        • En cas d'oubli de mot de passe, contactez l'administrateur système
    </div>
    """, unsafe_allow_html=True)

def show_session_info():
    """Affiche les informations de session dans la sidebar"""
    if st.session_state.get('admin_authenticated'):
        username = st.session_state.get('admin_username', 'Inconnu')
        display_name = get_user_display_name(username)
        login_time = st.session_state.get('admin_login_time', datetime.now())
        
        # Calcul du temps de session
        session_duration = datetime.now() - login_time
        hours, remainder = divmod(int(session_duration.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        
        st.sidebar.markdown(f"""
        <div class="session-info">
            <strong>👤 {display_name}</strong><br>
            🕒 Connecté depuis {hours}h{minutes:02d}m<br>
            🔐 Session sécurisée
        </div>
        """, unsafe_allow_html=True)
        
        # Bouton de déconnexion
        if st.sidebar.button("🚪 Se Déconnecter", use_container_width=True):
            log_login_attempt(username, True, "LOGOUT")
            st.session_state.admin_authenticated = False
            st.session_state.admin_username = None
            st.session_state.admin_login_time = None
            st.session_state.admin_permissions = None
            st.rerun()

def load_main_erp():
    """Charge l'ERP principal après authentification"""
    try:
        # Afficher banner de bienvenue
        username = st.session_state.get('admin_username', 'Admin')
        display_name = get_user_display_name(username)
        
        st.markdown(f"""
        <div class="welcome-banner">
            <h3>🏭 ERP Production DG Inc. - Mode Administrateur</h3>
            <p>Bienvenue <strong>{display_name}</strong> ! Accès complet autorisé.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Importer et exécuter l'ERP principal
        # Note: En production, vous pourriez vouloir importer dynamiquement
        import importlib.util
        
        # Charger le module app.py
        spec = importlib.util.spec_from_file_location("main_erp", "app.py")
        if spec and spec.loader:
            main_erp = importlib.util.module_from_spec(spec)
            
            # Injecter les informations d'authentification dans le module
            main_erp.st.session_state.admin_authenticated = True
            main_erp.st.session_state.admin_username = username
            main_erp.st.session_state.admin_permissions = st.session_state.admin_permissions
            
            # Exécuter l'ERP principal
            spec.loader.exec_module(main_erp)
            
        else:
            st.error("❌ Impossible de charger l'ERP principal (app.py)")
            st.info("🔧 Vérifiez que le fichier app.py existe dans le répertoire courant")
            
    except ImportError as e:
        st.error(f"❌ Erreur d'importation de l'ERP principal: {e}")
        st.info("🔧 Assurez-vous que tous les modules requis sont installés")
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement de l'ERP: {e}")
        st.code(str(e))

def main():
    """Fonction principale avec authentification"""
    
    # Initialisation des variables de session
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    if 'admin_username' not in st.session_state:
        st.session_state.admin_username = None
    if 'admin_login_time' not in st.session_state:
        st.session_state.admin_login_time = None
    if 'admin_permissions' not in st.session_state:
        st.session_state.admin_permissions = None
    
    # Vérifier l'authentification
    if not st.session_state.admin_authenticated or not check_session_validity():
        # Pas authentifié ou session expirée
        show_admin_login()
    else:
        # Authentifié et session valide
        show_session_info()
        load_main_erp()

if __name__ == "__main__":
    main()
