# app.py - ERP Production DG Inc. avec Portail d'Entrée Intégré et Numérotation Manuelle

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import calendar
import io
import json
import os
import re
import random
import hashlib
from math import gcd
from fractions import Fraction
import csv
import backup_scheduler  # Ceci démarre automatiquement le scheduler

# ========================
# CHARGEMENT DU CSS EXTERNE (CORRIGÉ)
# ========================

def safe_price_conversion(price_value, default=0.0):
    """Convertit de manière sécurisée une valeur de prix en float"""
    if price_value is None:
        return default
    
    try:
        price_str = str(price_value)
        price_str = price_str.replace(' ', '').replace('€', '').replace('$', '').replace(',', '.')
        return float(price_str) if price_str and price_str != '.' else default
    except (ValueError, TypeError):
        return default

def clean_price_for_sum(price_value):
    """Nettoie et convertit un prix pour sommation"""
    try:
        if not price_value:
            return 0.0
        price_str = str(price_value).replace(' ', '').replace('€', '').replace('$', '').replace(',', '.')
        return float(price_str) if price_str else 0.0
    except (ValueError, TypeError):
        return 0.0

def load_external_css():
    """Charge le fichier CSS externe pour un design uniforme"""
    try:
        with open('style.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
        st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
        return True
    except FileNotFoundError:
        st.warning("⚠️ Fichier style.css non trouvé. Utilisation du style par défaut.")
        return False
    except Exception as e:
        st.warning(f"⚠️ Erreur chargement CSS: {e}")
        return False

def apply_fallback_styles():
    """Styles CSS de secours si le fichier externe n'est pas disponible"""
    st.markdown("""
    <style>
    /* Styles de secours minimaux */
    :root {
        --primary-color: #00A971;
        --primary-color-light: #33BF85;
        --primary-color-lighter: #DCFCE7;
        --text-color: #374151;
        --background-color: #F9FAFB;
        --card-background: #F0FDF4;
        --border-radius-lg: 0.75rem;
        --box-shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    
    .main {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: var(--background-color);
    }
    
    .stButton > button {
        background: linear-gradient(145deg, #00A971 0%, #1F2937 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--border-radius-lg) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--box-shadow-md) !important;
    }
    
    /* Masquer éléments Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .css-1d391kg {display: none;}
    </style>
    """, unsafe_allow_html=True)

def apply_additional_project_styles():
    """Styles CSS supplémentaires pour la gestion des projets"""
    st.markdown("""
    <style>
    .project-card {
        border-left: 5px solid var(--primary-color);
        margin-bottom: 1rem;
        padding: 1rem;
        border-radius: 8px;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .project-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    .project-card h4 {
        margin: 0;
        color: #1e40af;
        font-size: 1.1rem;
    }
    
    .project-card p {
        margin: 0.5rem 0;
        color: #6b7280;
    }
    
    .status-badge {
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 500;
        color: white;
        display: inline-block;
    }
    
    .priority-badge {
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 500;
        color: white;
        display: inline-block;
        margin-left: 0.5rem;
    }
    
    .batch-actions-container {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .batch-actions-container h5 {
        margin: 0 0 1rem 0;
        color: #374151;
    }
    
    .action-buttons {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
    }
    
    .action-buttons .stButton > button {
        font-size: 0.8rem;
        padding: 0.25rem 0.5rem;
        height: auto;
        min-height: 2rem;
    }
    
    .filter-container {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    .project-stats {
        background: linear-gradient(135deg, var(--primary-color-lighter) 0%, var(--primary-color-light) 100%);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        color: var(--primary-color-darker);
    }
    
    .project-stats h5 {
        margin: 0;
        font-weight: 600;
    }
    
    @media (max-width: 768px) {
        .action-buttons {
            flex-direction: column;
        }
        
        .action-buttons .stButton {
            width: 100%;
        }
        
        .project-card {
            padding: 0.75rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def apply_additional_attachments_styles():
    """Styles CSS pour les pièces jointes"""
    st.markdown("""
    <style>
    /* Styles pour pièces jointes */
    .attachment-upload-zone {
        border: 2px dashed var(--primary-color);
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        background: linear-gradient(135deg, var(--primary-color-lighter) 0%, #f0fdf4 100%);
        margin: 1rem 0;
        transition: all 0.3s ease;
        position: relative;
        cursor: pointer;
    }
    
    .attachment-upload-zone:hover {
        border-color: var(--primary-color-dark);
        background: linear-gradient(135deg, var(--primary-color-light) 0%, #dcfce7 100%);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 169, 113, 0.2);
    }
    
    .attachment-card {
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: white;
        transition: all 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    
    .attachment-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: var(--primary-color);
        opacity: 0;
        transition: opacity 0.2s ease;
    }
    
    .attachment-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        transform: translateY(-1px);
        border-color: var(--primary-color-light);
    }
    
    .attachment-card:hover::before {
        opacity: 1;
    }
    
    .attachment-category-header {
        background: linear-gradient(135deg, var(--primary-color-lighter) 0%, #e6f3ff 100%);
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin: 1.5rem 0 1rem 0;
        font-weight: 600;
        color: var(--primary-color-darkest);
        border-left: 4px solid var(--primary-color);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .attachment-file-info {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem;
        background: #f8fafc;
        border-radius: 6px;
        margin: 0.5rem 0;
        border: 1px solid #e2e8f0;
        transition: background 0.2s ease;
    }
    
    .attachment-file-info:hover {
        background: #f1f5f9;
    }
    
    .attachment-stats {
        background: linear-gradient(135deg, #e6f3ff 0%, #cce7ff 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        text-align: center;
        border: 1px solid #bfdbfe;
    }
    
    .category-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 16px;
        font-size: 0.8rem;
        font-weight: 500;
        color: white;
        margin-right: 0.5rem;
        gap: 0.25rem;
    }
    
    .category-badge.DOCUMENT { 
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
    }
    
    .category-badge.IMAGE { 
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    }
    
    .category-badge.TECHNIQUE { 
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    }
    
    .category-badge.ARCHIVE { 
        background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
    }
    
    .category-badge.MEDIA { 
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    }
    
    .category-badge.AUTRE { 
        background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
    }
    
    @media (max-width: 768px) {
        .attachment-upload-zone {
            padding: 1.5rem 1rem;
        }
        
        .attachment-file-info {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
        }
        
        .attachment-category-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# ========================
# CONFIGURATION AUTHENTIFICATION
# ========================

def get_admin_credentials():
    """Configuration des identifiants admin pour déploiement"""
    return {
        "admin": os.environ.get("ADMIN_PASSWORD", "admin123"),
        "dg_admin": os.environ.get("DG_ADMIN_PASSWORD", "dg2024!"),
        "superviseur": os.environ.get("SUPERVISEUR_PASSWORD", "super2024"),
        "direction": os.environ.get("DIRECTION_PASSWORD", "direction!123"),
        "production": os.environ.get("PRODUCTION_PASSWORD", "prod2024"),
    }

def verify_admin_password(username, password):
    """Vérifie les identifiants administrateur"""
    admin_creds = get_admin_credentials()
    return username in admin_creds and admin_creds[username] == password

def get_user_display_name(username):
    """Retourne le nom d'affichage selon le rôle"""
    names = {
        "admin": "Administrateur Principal",
        "dg_admin": "Admin DG Inc.",
        "superviseur": "Superviseur Production",
        "direction": "Direction Générale",
        "production": "Responsable Production"
    }
    return names.get(username, username.title())

def get_user_permissions(username):
    """Définit les permissions selon le rôle"""
    permissions = {
        "admin": ["ALL"],
        "dg_admin": ["ALL"],
        "direction": ["projects", "crm", "employees", "reports", "formulaires", "fournisseurs"],
        "superviseur": ["projects", "timetracker", "work_centers", "employees", "formulaires"],
        "production": ["timetracker", "work_centers", "formulaires", "inventory"]
    }
    return permissions.get(username, [])

def check_admin_session():
    """Vérifie la validité de la session admin"""
    if not st.session_state.get('admin_authenticated'):
        return False

    if 'admin_login_time' not in st.session_state:
        return False

    # Session expire après 4 heures
    session_age = datetime.now() - st.session_state.admin_login_time
    if session_age > timedelta(hours=4):
        st.session_state.admin_authenticated = False
        st.warning("Session expirée. Veuillez vous reconnecter.")
        return False

    return True

def show_admin_header():
    """Affiche l'en-tête admin avec info session"""
    username = st.session_state.get('admin_username', 'Admin')
    display_name = get_user_display_name(username)
    login_time = st.session_state.get('admin_login_time')

    if login_time:
        session_duration = datetime.now() - login_time
        hours = int(session_duration.total_seconds() // 3600)
        minutes = int((session_duration.total_seconds() % 3600) // 60)
        session_info = f"Session: {hours}h{minutes}m"
    else:
        session_info = "Session active"

    st.markdown(f"""
    <div class="admin-welcome">
        <h3>🏭 ERP Production DG Inc. - Mode Administrateur</h3>
        <p>Bienvenue <strong>{display_name}</strong> ! {session_info}</p>
    </div>
    """, unsafe_allow_html=True)

# ========================
# IMPORTS MODULES ERP (MODIFIÉS POUR TIMETRACKER PRO + PIÈCES JOINTES)
# ========================

# PERSISTENT STORAGE : Import du gestionnaire de stockage persistant
try:
    from database_persistent import init_persistent_storage
    PERSISTENT_STORAGE_AVAILABLE = True
except ImportError:
    PERSISTENT_STORAGE_AVAILABLE = False

# NOUVELLE ARCHITECTURE : Import SQLite Database
try:
    from erp_database import ERPDatabase, convertir_pieds_pouces_fractions_en_valeur_decimale, convertir_imperial_vers_metrique
    ERP_DATABASE_AVAILABLE = True
except ImportError:
    ERP_DATABASE_AVAILABLE = False

# ========================
# NOUVEAU : Import du module unifié
# ========================
try:
    from production_management import show_production_management_page
    PRODUCTION_MANAGEMENT_AVAILABLE = True
except ImportError:
    PRODUCTION_MANAGEMENT_AVAILABLE = False

# --- REMPLACEZ PAR CECI DANS app.py ---

# Importations pour le CRM (avec toutes les fonctions décommentées)
try:
    # On importe uniquement le constructeur et l'interface principale du CRM.
    from crm import GestionnaireCRM, render_crm_main_interface
    CRM_AVAILABLE = True
except ImportError:
    CRM_AVAILABLE = False

# Importations pour les Employés
try:
    from employees import (
        GestionnaireEmployes,
        render_employes_liste_tab,
        render_employes_dashboard_tab,
        render_employe_form,
        render_employe_details
    )
    EMPLOYEES_AVAILABLE = True
except ImportError:
    EMPLOYEES_AVAILABLE = False

# ARCHITECTURE UNIFIÉE : Postes de travail intégrés dans TimeTracker
# Les fonctions postes sont maintenant dans timetracker_unified.py
POSTES_AVAILABLE = False  # Désactivé - maintenant unifié dans TimeTracker Pro

# NOUVEAU : Importation du module Formulaires
try:
    from formulaires import (
        GestionnaireFormulaires,
        show_formulaires_page
    )
    FORMULAIRES_AVAILABLE = True
except ImportError:
    FORMULAIRES_AVAILABLE = False

# NOUVEAU : Importation du module Fournisseurs
try:
    from fournisseurs import (
        GestionnaireFournisseurs,
        show_fournisseurs_page
    )
    FOURNISSEURS_AVAILABLE = True
except ImportError:
    FOURNISSEURS_AVAILABLE = False

# CHECKPOINT 6 : INTÉGRATION TIMETRACKER PRO UNIFIÉ
try:
    from timetracker_unified import show_timetracker_unified_interface, TimeTrackerUnified
    TIMETRACKER_AVAILABLE = True
except ImportError as e:
    TIMETRACKER_AVAILABLE = False
    print(f"Erreur import TimeTracker Pro: {e}")

# NOUVEAU : Importation du module Kanban unifié
try:
    from kanban import show_kanban_sqlite, show_kanban
    KANBAN_AVAILABLE = True
except ImportError:
    KANBAN_AVAILABLE = False

# NOUVEAU : Import du gestionnaire de pièces jointes
try:
    from attachments_manager import (
        AttachmentsManager,
        show_project_attachments_interface,
        init_attachments_manager,
        show_attachments_tab_in_project_modal
    )
    ATTACHMENTS_AVAILABLE = True
except ImportError:
    ATTACHMENTS_AVAILABLE = False

# Configuration de la page
st.set_page_config(
    page_title="🚀 ERP Production DG Inc.",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================
# FONCTIONS UTILITAIRES ERP (RÉDUITES - MODULE UNIFIÉ)
# ========================

# Les constantes et fonctions utilitaires ont été déplacées vers production_management.py
# Seules les fonctions encore utilisées dans app.py sont conservées ici

def format_currency(value):
    if value is None:
        return "$0.00"
    try:
        s_value = str(value).replace(' ', '').replace('€', '').replace('$', '')
        if ',' in s_value and ('.' not in s_value or s_value.find(',') > s_value.find('.')):
            s_value = s_value.replace('.', '').replace(',', '.')
        elif ',' in s_value and '.' in s_value and s_value.find('.') > s_value.find(','):
            s_value = s_value.replace(',', '')

        num_value = float(s_value)
        if num_value == 0:
            return "$0.00"
        return f"${num_value:,.2f}"
    except (ValueError, TypeError):
        if isinstance(value, (int, float)):
            return f"${value:,.2f}"
        return str(value) + " $ (Err)"

def get_project_statistics(gestionnaire):
    if not gestionnaire.projets:
        return {'total': 0, 'par_statut': {}, 'par_priorite': {}, 'ca_total': 0, 'projets_actifs': 0, 'taux_completion': 0}
    stats = {'total': len(gestionnaire.projets), 'par_statut': {}, 'par_priorite': {}, 'ca_total': 0, 'projets_actifs': 0}
    for p in gestionnaire.projets:
        statut = p.get('statut', 'N/A')
        stats['par_statut'][statut] = stats['par_statut'].get(statut, 0) + 1
        priorite = p.get('priorite', 'N/A')
        stats['par_priorite'][priorite] = stats['par_priorite'].get(priorite, 0) + 1
        try:
            prix = p.get('prix_estime', '0')
            s_prix = str(prix).replace(' ', '').replace('€', '').replace('$', '')
            if ',' in s_prix and ('.' not in s_prix or s_prix.find(',') > s_prix.find('.')):
                s_prix = s_prix.replace('.', '').replace(',', '.')
            elif ',' in s_prix and '.' in s_prix and s_prix.find('.') > s_prix.find(','):
                s_prix = s_prix.replace(',', '')
            prix_num = float(s_prix)
            stats['ca_total'] += prix_num
        except (ValueError, TypeError):
            pass
        if statut not in ['TERMINÉ', 'ANNULÉ', 'FERMÉ']:
            stats['projets_actifs'] += 1
    termines = stats['par_statut'].get('TERMINÉ', 0)
    stats['taux_completion'] = (termines / stats['total'] * 100) if stats['total'] > 0 else 0
    return stats

# ========================
# NOUVELLES FONCTIONS UTILITAIRES POUR GESTION PROJETS
# ========================

def get_client_display_name(project, crm_manager):
    """Récupère le nom d'affichage du client"""
    client_display_name = project.get('client_nom_cache', 'N/A')
    if client_display_name == 'N/A' and project.get('client_company_id'):
        entreprise = crm_manager.get_entreprise_by_id(project.get('client_company_id'))
        if entreprise:
            client_display_name = entreprise.get('nom', 'N/A')
    elif client_display_name == 'N/A':
        client_display_name = project.get('client_legacy', 'N/A')
    return client_display_name

def get_status_color(status):
    """Retourne la couleur associée au statut"""
    colors = {
        'À FAIRE': '#f59e0b',
        'EN COURS': '#3b82f6',
        'EN ATTENTE': '#ef4444',
        'TERMINÉ': '#10b981',
        'ANNULÉ': '#6b7280',
        'LIVRAISON': '#8b5cf6'
    }
    return colors.get(status, '#6b7280')

def get_priority_color(priority):
    """Retourne la couleur associée à la priorité"""
    colors = {
        'ÉLEVÉ': '#ef4444',
        'MOYEN': '#f59e0b',
        'BAS': '#10b981'
    }
    return colors.get(priority, '#6b7280')

def duplicate_project(gestionnaire, original_project):
    """Duplique un projet existant"""
    try:
        # Créer une copie du projet avec un nouveau nom
        new_project_data = original_project.copy()
        new_project_data['nom_projet'] = f"COPIE - {original_project.get('nom_projet', 'N/A')}"
        new_project_data['statut'] = 'À FAIRE'
        
        # Supprimer l'ID pour forcer une nouvelle création
        if 'id' in new_project_data:
            del new_project_data['id']
        
        # Ajuster les dates
        today = datetime.now().date()
        new_project_data['date_soumis'] = today.strftime('%Y-%m-%d')
        new_project_data['date_prevu'] = (today + timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Créer le nouveau projet
        new_id = gestionnaire.ajouter_projet(new_project_data)
        if new_id:
            st.success(f"✅ Projet #{new_id} créé par duplication !")
        else:
            st.error("❌ Erreur lors de la duplication")
    except Exception as e:
        st.error(f"❌ Erreur lors de la duplication: {str(e)}")

def export_projects_to_csv(projects, crm_manager):
    """Exporte les projets au format CSV"""
    try:
        # Préparer les données pour l'export
        export_data = []
        for p in projects:
            client_name = get_client_display_name(p, crm_manager)
            
            export_data.append({
                'ID': p.get('id', ''),
                'Nom du Projet': p.get('nom_projet', ''),
                'Client': client_name,
                'Statut': p.get('statut', ''),
                'Priorité': p.get('priorite', ''),
                'Type de Tâche': p.get('tache', ''),
                'Date de Soumission': p.get('date_soumis', ''),
                'Date Prévue': p.get('date_prevu', ''),
                'BD-FT Estimé (h)': p.get('bd_ft_estime', ''),
                'Prix Estimé': p.get('prix_estime', ''),
                'Description': p.get('description', '')
            })
        
        # Créer le fichier CSV en mémoire
        output = io.StringIO()
        fieldnames = ['ID', 'Nom du Projet', 'Client', 'Statut', 'Priorité', 'Type de Tâche', 
                     'Date de Soumission', 'Date Prévue', 'BD-FT Estimé (h)', 'Prix Estimé', 'Description']
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(export_data)
        
        # Retourner le contenu CSV
        csv_content = output.getvalue()
        output.close()
        
        return csv_content
        
    except Exception as e:
        st.error(f"Erreur lors de l'export: {str(e)}")
        return None

def show_project_statistics(projects, crm_manager):
    """Affiche des statistiques avancées sur les projets"""
    if not projects:
        return
    
    st.markdown("### 📊 Statistiques Détaillées")
    
    # Calculs statistiques
    total_projets = len(projects)
    projets_termines = len([p for p in projects if p.get('statut') == 'TERMINÉ'])
    projets_en_cours = len([p for p in projects if p.get('statut') == 'EN COURS'])
    projets_en_attente = len([p for p in projects if p.get('statut') == 'EN ATTENTE'])
    
    # Calcul du CA total et moyen
    ca_total = 0
    ca_values = []
    for p in projects:
        try:
            prix_str = str(p.get('prix_estime', '0')).replace('$', '').replace(',', '')
            prix_num = float(prix_str) if prix_str else 0
            ca_total += prix_num
            if prix_num > 0:
                ca_values.append(prix_num)
        except:
            pass
    
    ca_moyen = sum(ca_values) / len(ca_values) if ca_values else 0
    
    # Temps total estimé
    temps_total = 0
    for p in projects:
        try:
            temps = float(p.get('bd_ft_estime', 0))
            temps_total += temps
        except:
            pass
    
    # Affichage des métriques
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📈 Total Projets", total_projets)
    with col2:
        taux_completion = (projets_termines / total_projets * 100) if total_projets > 0 else 0
        st.metric("✅ Taux Completion", f"{taux_completion:.1f}%")
    with col3:
        st.metric("🚀 En Cours", projets_en_cours)
    with col4:
        st.metric("⏳ En Attente", projets_en_attente)
    with col5:
        st.metric("⏱️ Temps Total", f"{temps_total:.1f}h")
    
    # Métriques financières
    col6, col7, col8 = st.columns(3)
    with col6:
        st.metric("💰 CA Total", format_currency(ca_total))
    with col7:
        st.metric("💳 CA Moyen", format_currency(ca_moyen))
    with col8:
        ca_par_heure = ca_total / temps_total if temps_total > 0 else 0
        st.metric("💎 CA/Heure", format_currency(ca_par_heure))

def advanced_project_search(projects, search_term, crm_manager):
    """Recherche avancée dans les projets"""
    if not search_term:
        return projects
    
    search_term = search_term.lower()
    results = []
    
    for p in projects:
        # Recherche dans tous les champs texte
        searchable_fields = [
            str(p.get('nom_projet', '')),
            str(p.get('description', '')),
            str(p.get('tache', '')),
            str(p.get('statut', '')),
            str(p.get('priorite', '')),
            get_client_display_name(p, crm_manager),
            str(p.get('id', ''))
        ]
        
        # Recherche dans les opérations et matériaux
        for operation in p.get('operations', []):
            searchable_fields.extend([
                str(operation.get('description', '')),
                str(operation.get('poste_travail', '')),
                str(operation.get('ressource', ''))
            ])
        
        for materiau in p.get('materiaux', []):
            searchable_fields.extend([
                str(materiau.get('designation', '')),
                str(materiau.get('code', '')),
                str(materiau.get('fournisseur', ''))
            ])
        
        # Vérifier si le terme de recherche est trouvé
        if any(search_term in field.lower() for field in searchable_fields):
            results.append(p)
    
    return results

def sort_projects(projects, sort_by, crm_manager):
    """Trie les projets selon le critère sélectionné"""
    try:
        if sort_by == "ID (Desc)":
            return sorted(projects, key=lambda x: x.get('id', 0), reverse=True)
        elif sort_by == "ID (Asc)":
            return sorted(projects, key=lambda x: x.get('id', 0))
        elif sort_by == "Nom":
            return sorted(projects, key=lambda x: x.get('nom_projet', '').lower())
        elif sort_by == "Client":
            return sorted(projects, key=lambda x: get_client_display_name(x, crm_manager).lower())
        elif sort_by == "Date Début":
            return sorted(projects, key=lambda x: x.get('date_soumis', ''), reverse=True)
        elif sort_by == "Prix":
            return sorted(projects, key=lambda x: float(str(x.get('prix_estime', 0)).replace('$', '').replace(',', '') or 0), reverse=True)
        elif sort_by == "Statut":
            return sorted(projects, key=lambda x: x.get('statut', ''))
        else:
            return projects
    except Exception as e:
        st.error(f"Erreur de tri: {str(e)}")
        return projects

def show_projects_detailed_view(projects, crm_manager):
    """Vue liste détaillée avec toutes les actions"""
    
    # Sélection pour actions en lot
    st.markdown("##### 🎯 Actions en Lot")
    selected_ids = st.multiselect(
        "Sélectionner des projets:",
        options=[p.get('id') for p in projects],
        format_func=lambda x: f"#{x} - {next((p.get('nom_projet', 'N/A') for p in projects if p.get('id') == x), 'N/A')}",
        key="batch_select_detailed"
    )
    
    if selected_ids:
        batch_col1, batch_col2, batch_col3, batch_col4 = st.columns(4)
        with batch_col1:
            if st.button("🔄 Changer Statut", use_container_width=True, key="batch_status"):
                st.session_state.batch_action = "change_status"
                st.session_state.batch_selected_ids = selected_ids
                st.rerun()
        with batch_col2:
            if st.button("⭐ Changer Priorité", use_container_width=True, key="batch_priority"):
                st.session_state.batch_action = "change_priority"
                st.session_state.batch_selected_ids = selected_ids
                st.rerun()
        with batch_col3:
            if st.button("📋 Export Sélection", use_container_width=True, key="batch_export"):
                selected_projects = [p for p in projects if p.get('id') in selected_ids]
                csv_content = export_projects_to_csv(selected_projects, crm_manager)
                if csv_content:
                    st.download_button(
                        label="⬇️ Télécharger",
                        data=csv_content,
                        file_name=f"projets_selection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
        with batch_col4:
            if st.button("🗑️ Supprimer", use_container_width=True, key="batch_delete"):
                st.session_state.batch_action = "delete_multiple"
                st.session_state.batch_selected_ids = selected_ids
                st.rerun()

    st.markdown("---")
    
    # Affichage des projets
    for i, p in enumerate(projects):
        client_display_name = get_client_display_name(p, crm_manager)
        
        # Carte projet
        statut_color = get_status_color(p.get('statut', 'N/A'))
        priority_color = get_priority_color(p.get('priorite', 'N/A'))
        
        # Indicateur si sélectionné
        selected_indicator = "✅ " if p.get('id') in selected_ids else ""
        
        st.markdown(f"""
        <div class="project-card" style="border-left-color: {statut_color};">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="flex: 1;">
                    <h4>{selected_indicator}#{p.get('id')} - {p.get('nom_projet', 'N/A')}</h4>
                    <p><strong>👤 Client:</strong> {client_display_name}</p>
                    <p><strong>📝 Description:</strong> {(p.get('description', 'Aucune description'))[:100]}{'...' if len(p.get('description', '')) > 100 else ''}</p>
                </div>
                <div style="text-align: right; min-width: 200px;">
                    <span class="status-badge" style="background-color: {statut_color};">{p.get('statut', 'N/A')}</span>
                    <span class="priority-badge" style="background-color: {priority_color};">{p.get('priorite', 'N/A')}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Informations détaillées
        info_col1, info_col2, info_col3, info_col4 = st.columns(4)
        with info_col1:
            st.markdown(f"**📅 Début:** {p.get('date_soumis', 'N/A')}")
        with info_col2:
            st.markdown(f"**🏁 Fin:** {p.get('date_prevu', 'N/A')}")
        with info_col3:
            st.markdown(f"**💰 Prix:** {format_currency(p.get('prix_estime', 0))}")
        with info_col4:
            st.markdown(f"**⏱️ BD-FT:** {p.get('bd_ft_estime', 'N/A')}h")
        
        # Boutons d'action
        action_col1, action_col2, action_col3, action_col4, action_col5, action_col6 = st.columns(6)
        
        with action_col1:
            if st.button("👁️", key=f"view_{p.get('id')}", help="Voir détails", use_container_width=True):
                st.session_state.selected_project = p
                st.session_state.show_project_modal = True
                st.rerun()
        
        with action_col2:
            if st.button("✏️", key=f"edit_{p.get('id')}", help="Modifier", use_container_width=True):
                st.session_state.show_edit_project = True
                st.session_state.edit_project_data = p
                st.rerun()
        
        with action_col3:
            if st.button("🗑️", key=f"delete_{p.get('id')}", help="Supprimer", use_container_width=True):
                st.session_state.show_delete_confirmation = True
                st.session_state.delete_project_id = p.get('id')
                st.rerun()
        
        with action_col4:
            if st.button("🔧", key=f"bt_{p.get('id')}", help="Bon de Travail", use_container_width=True):
                st.session_state.timetracker_redirect_to_bt = True
                st.session_state.formulaire_project_preselect = p.get('id')
                st.session_state.page_redirect = "timetracker_pro_page"
                st.rerun()
        
        with action_col5:
            if st.button("🛒", key=f"ba_{p.get('id')}", help="Bon d'Achat", use_container_width=True):
                st.session_state.form_action = "create_bon_achat"
                st.session_state.formulaire_project_preselect = p.get('id')
                st.session_state.page_redirect = "formulaires_page"
                st.rerun()
        
        with action_col6:
            if st.button("📋", key=f"duplicate_{p.get('id')}", help="Dupliquer", use_container_width=True):
                duplicate_project(st.session_state.gestionnaire, p)
                st.rerun()
        
        st.markdown("---")

def show_projects_table_view(projects, crm_manager):
    """Vue tableau compacte avec ordre personnalisé : ID, Statut, Priorité, Tâche, No.Projet, Nom, Client, Description, Prix, Début, Durée, Fin, Adresse"""
    df_data = []
    for p in projects:
        client_display_name = get_client_display_name(p, crm_manager)
        
        # Calcul de la durée en jours
        duree_jours = "N/A"
        try:
            if p.get('date_soumis') and p.get('date_prevu'):
                date_debut = datetime.strptime(p.get('date_soumis'), '%Y-%m-%d')
                date_fin = datetime.strptime(p.get('date_prevu'), '%Y-%m-%d')
                duree = (date_fin - date_debut).days
                duree_jours = f"{duree}j"
        except:
            duree_jours = "N/A"
        
        # Récupération de l'adresse du client depuis le CRM
        adresse_client = "N/A"
        if p.get('client_company_id'):
            try:
                entreprise = crm_manager.get_entreprise_by_id(p.get('client_company_id'))
                if entreprise:
                    adresse_client = entreprise.get('adresse', 'N/A')[:25] + ('...' if len(entreprise.get('adresse', '')) > 25 else '')
            except:
                pass
        
        df_data.append({
            '🆔 ID': p.get('id', '?'),
            '🚦 Statut': p.get('statut', 'N/A'),
            '⭐ Priorité': p.get('priorite', 'N/A'),
            '🏷️ Tâche': p.get('tache', 'N/A'),
            '📋 No. Projet': f"PRJ-{p.get('id', '?')}",
            '📝 Nom Projet': p.get('nom_projet', 'N/A')[:35] + ('...' if len(p.get('nom_projet', '')) > 35 else ''),
            '👤 Client': client_display_name[:25] + ('...' if len(client_display_name) > 25 else ''),
            '📄 Description': (p.get('description', 'N/A')[:40] + ('...' if len(p.get('description', '')) > 40 else '')) if p.get('description') else 'N/A',
            '💰 Prix Estimé': format_currency(p.get('prix_estime', 0)),
            '📅 Début': p.get('date_soumis', 'N/A'),
            '⏱️ Durée': duree_jours,
            '🏁 Fin': p.get('date_prevu', 'N/A'),
            '🏢 Adresse': adresse_client
        })
    
    df_projets = pd.DataFrame(df_data)
    
    # Affichage du tableau avec défilement horizontal pour toutes les colonnes
    st.dataframe(
        df_projets, 
        use_container_width=True, 
        height=400,
        column_config={
            "🆔 ID": st.column_config.NumberColumn(
                "🆔 ID",
                help="Identifiant unique du projet",
                width="small",
            ),
            "🚦 Statut": st.column_config.TextColumn(
                "🚦 Statut",
                help="Statut actuel du projet",
                width="medium",
            ),
            "🏷️ Tâche": st.column_config.TextColumn(
                "🏷️ Tâche",
                help="Type de tâche du projet",
                width="medium",
            ),
            "📝 Nom Projet": st.column_config.TextColumn(
                "📝 Nom Projet",
                help="Nom complet du projet",
                width="large",
            ),
            "💰 Prix Estimé": st.column_config.TextColumn(
                "💰 Prix Estimé",
                help="Prix estimé du projet",
                width="medium",
            ),
            "📄 Description": st.column_config.TextColumn(
                "📄 Description",
                help="Description détaillée du projet",
                width="large",
            ),
            "🏢 Adresse": st.column_config.TextColumn(
                "🏢 Adresse",
                help="Adresse du client",
                width="large",
            )
        }
    )

def show_projects_card_view(projects, crm_manager):
    """Vue cartes compactes en grille"""
    # Organiser en grille de 2 colonnes
    for i in range(0, len(projects), 2):
        cols = st.columns(2)
        
        for j, col in enumerate(cols):
            if i + j < len(projects):
                p = projects[i + j]
                client_name = get_client_display_name(p, crm_manager)
                statut_color = get_status_color(p.get('statut', 'N/A'))
                
                with col:
                    st.markdown(f"""
                    <div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; border-left: 4px solid {statut_color};">
                        <h5 style="margin: 0 0 0.5rem 0; color: #1e40af;">#{p.get('id')} - {p.get('nom_projet', 'N/A')[:25]}{'...' if len(p.get('nom_projet', '')) > 25 else ''}</h5>
                        <p style="margin: 0.25rem 0; font-size: 0.9em;">👤 {client_name[:20]}{'...' if len(client_name) > 20 else ''}</p>
                        <p style="margin: 0.25rem 0; font-size: 0.9em;">🚦 {p.get('statut', 'N/A')} | ⭐ {p.get('priorite', 'N/A')}</p>
                        <p style="margin: 0.25rem 0; font-size: 0.9em;">💰 {format_currency(p.get('prix_estime', 0))}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Boutons compacts
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    with btn_col1:
                        if st.button("👁️", key=f"card_view_{p.get('id')}", help="Voir", use_container_width=True):
                            st.session_state.selected_project = p
                            st.session_state.show_project_modal = True
                            st.rerun()
                    with btn_col2:
                        if st.button("✏️", key=f"card_edit_{p.get('id')}", help="Modifier", use_container_width=True):
                            st.session_state.show_edit_project = True
                            st.session_state.edit_project_data = p
                            st.rerun()
                    with btn_col3:
                        if st.button("🔧", key=f"card_bt_{p.get('id')}", help="BT", use_container_width=True):
                            st.session_state.timetracker_redirect_to_bt = True
                            st.session_state.formulaire_project_preselect = p.get('id')
                            st.session_state.page_redirect = "timetracker_pro_page"
                            st.rerun()

def handle_batch_actions():
    """Gère les actions en lot sur les projets"""
    if st.session_state.get('batch_action') and st.session_state.get('batch_selected_ids'):
        batch_action = st.session_state.batch_action
        selected_ids = st.session_state.batch_selected_ids
        gestionnaire = st.session_state.gestionnaire
        
        st.markdown("---")
        st.markdown("### 🎯 Action en Lot")
        
        if batch_action == "change_status":
            st.markdown("#### 🔄 Changement de Statut en Lot")
            st.info(f"Modification du statut pour {len(selected_ids)} projet(s) sélectionné(s)")
            
            new_status = st.selectbox("Nouveau statut:", ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON"])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Appliquer", use_container_width=True, type="primary"):
                    success_count = 0
                    for project_id in selected_ids:
                        if gestionnaire.modifier_projet(project_id, {'statut': new_status}):
                            success_count += 1
                    
                    st.success(f"✅ Statut modifié pour {success_count}/{len(selected_ids)} projets")
                    st.session_state.batch_action = None
                    st.session_state.batch_selected_ids = None
                    st.rerun()
            with col2:
                if st.button("❌ Annuler", use_container_width=True):
                    st.session_state.batch_action = None
                    st.session_state.batch_selected_ids = None
                    st.rerun()
        
        elif batch_action == "change_priority":
            st.markdown("#### ⭐ Changement de Priorité en Lot")
            st.info(f"Modification de la priorité pour {len(selected_ids)} projet(s) sélectionné(s)")
            
            new_priority = st.selectbox("Nouvelle priorité:", ["BAS", "MOYEN", "ÉLEVÉ"])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Appliquer", use_container_width=True, type="primary"):
                    success_count = 0
                    for project_id in selected_ids:
                        if gestionnaire.modifier_projet(project_id, {'priorite': new_priority}):
                            success_count += 1
                    
                    st.success(f"✅ Priorité modifiée pour {success_count}/{len(selected_ids)} projets")
                    st.session_state.batch_action = None
                    st.session_state.batch_selected_ids = None
                    st.rerun()
            with col2:
                if st.button("❌ Annuler", use_container_width=True):
                    st.session_state.batch_action = None
                    st.session_state.batch_selected_ids = None
                    st.rerun()
        
        elif batch_action == "delete_multiple":
            st.markdown("#### 🗑️ Suppression en Lot")
            st.error(f"⚠️ Vous êtes sur le point de supprimer {len(selected_ids)} projet(s). Cette action est irréversible.")
            
            # Afficher la liste des projets à supprimer
            projects_to_delete = [p for p in gestionnaire.projets if p.get('id') in selected_ids]
            for p in projects_to_delete:
                st.markdown(f"- **#{p.get('id')}** - {p.get('nom_projet', 'N/A')}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Confirmer Suppression", type="primary", use_container_width=True):
                    success_count = 0
                    for project_id in selected_ids:
                        if gestionnaire.supprimer_projet(project_id):
                            success_count += 1
                    
                    st.success(f"✅ {success_count}/{len(selected_ids)} projets supprimés")
                    st.session_state.batch_action = None
                    st.session_state.batch_selected_ids = None
                    st.rerun()
            
            with col2:
                if st.button("❌ Annuler", use_container_width=True):
                    st.session_state.batch_action = None
                    st.session_state.batch_selected_ids = None
                    st.rerun()

# ========================
# GESTIONNAIRE PROJETS SQLite (MODIFIÉ AVEC NUMÉROTATION MANUELLE)
# ========================

class GestionnaireProjetSQL:
    """
    NOUVELLE ARCHITECTURE : Gestionnaire de projets utilisant SQLite au lieu de JSON
    Remplace GestionnaireProjetIA pour une architecture unifiée - VERSION CORRIGÉE AVEC NUMÉROTATION MANUELLE
    """

    def __init__(self, db: ERPDatabase):
        self.db = db
        self.next_id = 10000  # Commence à 10000 pour professionnalisme
        self._init_next_id()

    def _init_next_id(self):
        """Initialise le prochain ID basé sur les projets existants"""
        try:
            result = self.db.execute_query("SELECT MAX(id) as max_id FROM projects")
            if result and result[0]['max_id']:
                self.next_id = max(result[0]['max_id'] + 1, 10000)
            else:
                self.next_id = 10000
        except Exception as e:
            st.error(f"Erreur initialisation next_id: {e}")
            self.next_id = 10000

    def _is_project_id_exists(self, project_id):
        """Vérifie si un numéro de projet existe déjà"""
        try:
            result = self.db.execute_query("SELECT COUNT(*) as count FROM projects WHERE id = ?", (project_id,))
            return result and result[0]['count'] > 0
        except Exception:
            return False

    def _validate_custom_project_id(self, custom_id):
        """Valide un numéro de projet personnalisé"""
        if not custom_id:
            return None, None
        
        # Nettoyer l'ID personnalisé
        custom_id = str(custom_id).strip()
        
        # Vérifier si c'est un numéro
        try:
            numeric_id = int(custom_id)
            if numeric_id <= 0:
                return None, "Le numéro de projet doit être positif"
        except ValueError:
            return None, "Le numéro de projet doit être un nombre entier"
        
        # Vérifier si le numéro existe déjà
        if self._is_project_id_exists(numeric_id):
            return None, f"Le numéro de projet #{numeric_id} est déjà utilisé"
        
        return numeric_id, None

    @property
    def projets(self):
        """Propriété pour maintenir compatibilité avec l'ancien code"""
        return self.get_all_projects()

    def get_all_projects(self):
        """Récupère tous les projets depuis SQLite"""
        try:
            query = '''
                SELECT p.*, c.nom as client_nom_company
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                ORDER BY p.id DESC
            '''
            rows = self.db.execute_query(query)

            projets = []
            for row in rows:
                projet = dict(row)

                # Récupérer opérations
                operations = self.db.execute_query(
                    "SELECT * FROM operations WHERE project_id = ? ORDER BY sequence_number",
                    (projet['id'],)
                )
                projet['operations'] = [dict(op) for op in operations]

                # Récupérer matériaux
                materiaux = self.db.execute_query(
                    "SELECT * FROM materials WHERE project_id = ?",
                    (projet['id'],)
                )
                projet['materiaux'] = [dict(mat) for mat in materiaux]

                # Récupérer employés assignés
                employes_assignes = self.db.execute_query(
                    "SELECT employee_id FROM project_assignments WHERE project_id = ?",
                    (projet['id'],)
                )
                projet['employes_assignes'] = [row['employee_id'] for row in employes_assignes]

                # Compatibilité avec ancien format
                if not projet.get('client_nom_cache') and projet.get('client_nom_company'):
                    projet['client_nom_cache'] = projet['client_nom_company']

                projets.append(projet)

            return projets

        except Exception as e:
            st.error(f"Erreur récupération projets: {e}")
            return []

    def ajouter_projet(self, projet_data):
        """Ajoute un nouveau projet en SQLite - VERSION CORRIGÉE avec validation FK et numérotation manuelle"""
        try:
            # NOUVEAU : Gestion de la numérotation manuelle
            custom_project_id = projet_data.get('custom_project_id')
            
            if custom_project_id:
                # Utiliser le numéro personnalisé après validation
                validated_id, error_msg = self._validate_custom_project_id(custom_project_id)
                if error_msg:
                    st.error(f"❌ Erreur numérotation: {error_msg}")
                    return None
                project_id = validated_id
            else:
                # Utiliser la numérotation automatique
                project_id = self.next_id

            # VALIDATION PRÉALABLE des clés étrangères
            if projet_data.get('client_company_id'):
                company_exists = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM companies WHERE id = ?",
                    (projet_data['client_company_id'],)
                )
                if not company_exists or company_exists[0]['count'] == 0:
                    raise ValueError(f"Entreprise ID {projet_data['client_company_id']} n'existe pas")

            # Validation employés assignés
            employes_assignes = projet_data.get('employes_assignes', [])
            for emp_id in employes_assignes:
                emp_exists = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM employees WHERE id = ?",
                    (emp_id,)
                )
                if not emp_exists or emp_exists[0]['count'] == 0:
                    raise ValueError(f"Employé ID {emp_id} n'existe pas")

            # Insérer projet principal avec gestion NULL
            query = '''
                INSERT INTO projects
                (id, nom_projet, client_company_id, client_nom_cache, client_legacy,
                 statut, priorite, tache, date_soumis, date_prevu, bd_ft_estime,
                 prix_estime, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''

            prix_estime = float(str(projet_data.get('prix_estime', 0)).replace('$', '').replace(',', '')) if projet_data.get('prix_estime') else 0
            bd_ft_estime = float(projet_data.get('bd_ft_estime', 0)) if projet_data.get('bd_ft_estime') else 0

            self.db.execute_update(query, (
                project_id,
                projet_data['nom_projet'],
                projet_data.get('client_company_id'),
                projet_data.get('client_nom_cache'),
                projet_data.get('client_legacy', ''),
                projet_data.get('statut', 'À FAIRE'),
                projet_data.get('priorite', 'MOYEN'),
                projet_data['tache'],
                projet_data.get('date_soumis'),
                projet_data.get('date_prevu'),
                bd_ft_estime,
                prix_estime,
                projet_data.get('description')
            ))

            # Insérer assignations employés (validation déjà faite)
            for emp_id in employes_assignes:
                self.db.execute_update(
                    "INSERT OR IGNORE INTO project_assignments (project_id, employee_id, role_projet) VALUES (?, ?, ?)",
                    (project_id, emp_id, 'Membre équipe')
                )

            # NOUVEAU : Ne mettre à jour next_id que si on a utilisé la numérotation automatique
            if not custom_project_id:
                self.next_id += 1

            return project_id

        except ValueError as ve:
            st.error(f"Erreur validation: {ve}")
            return None
        except Exception as e:
            st.error(f"Erreur technique ajout projet: {e}")
            return None

    def modifier_projet(self, projet_id, projet_data_update):
        """Modifie un projet existant"""
        try:
            # Préparer les champs à mettre à jour
            update_fields = []
            params = []

            for field, value in projet_data_update.items():
                if field in ['nom_projet', 'client_company_id', 'client_nom_cache', 'client_legacy',
                           'statut', 'priorite', 'tache', 'date_soumis', 'date_prevu',
                           'bd_ft_estime', 'prix_estime', 'description']:
                    update_fields.append(f"{field} = ?")

                    # Traitement spécial pour les prix
                    if field == 'prix_estime':
                        value = float(str(value).replace('$', '').replace(',', '')) if value else 0
                    elif field == 'bd_ft_estime':
                        value = float(value) if value else 0

                    params.append(value)

            if update_fields:
                query = f"UPDATE projects SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
                params.append(projet_id)
                self.db.execute_update(query, tuple(params))

            # Mettre à jour assignations employés si fourni
            if 'employes_assignes' in projet_data_update:
                # Supprimer anciennes assignations
                self.db.execute_update("DELETE FROM project_assignments WHERE project_id = ?", (projet_id,))

                # Ajouter nouvelles assignations
                for emp_id in projet_data_update['employes_assignes']:
                    self.db.execute_update(
                        "INSERT INTO project_assignments (project_id, employee_id, role_projet) VALUES (?, ?, ?)",
                        (projet_id, emp_id, 'Membre équipe')
                    )

            return True

        except Exception as e:
            st.error(f"Erreur modification projet: {e}")
            return False

    def supprimer_projet(self, projet_id):
        """Supprime un projet et ses données associées"""
        try:
            # Supprimer en cascade (relations d'abord)
            self.db.execute_update("DELETE FROM project_assignments WHERE project_id = ?", (projet_id,))
            self.db.execute_update("DELETE FROM operations WHERE project_id = ?", (projet_id,))
            self.db.execute_update("DELETE FROM materials WHERE project_id = ?", (projet_id,))
            self.db.execute_update("DELETE FROM time_entries WHERE project_id = ?", (projet_id,))

            # Supprimer le projet
            self.db.execute_update("DELETE FROM projects WHERE id = ?", (projet_id,))

            return True

        except Exception as e:
            st.error(f"Erreur suppression projet: {e}")
            return False

# ========================
# INITIALISATION ERP SYSTÈME (MODIFIÉ AVEC PIÈCES JOINTES)
# ========================

def _init_base_data_if_empty():
    """Initialise les données de base si les tables sont vides - RÉSOUT ERREURS FK"""
    if not ERP_DATABASE_AVAILABLE:
        return

    db = st.session_state.erp_db

    try:
        # Vérifier et créer entreprises par défaut
        companies_count = db.get_table_count('companies')
        if companies_count == 0:
            # Créer quelques entreprises par défaut
            default_companies = [
                {
                    'id': 1,
                    'nom': 'AutoTech Corp.',
                    'secteur': 'Automobile',
                    'adresse': '123 Rue Industrielle, Montréal, QC',
                    'site_web': 'www.autotech.com',
                    'notes': 'Client métallurgie automobile'
                },
                {
                    'id': 2,
                    'nom': 'BâtiTech Inc.',
                    'secteur': 'Construction',
                    'adresse': '456 Boul. Construction, Québec, QC',
                    'site_web': 'www.batitech.ca',
                    'notes': 'Structures industrielles'
                },
                {
                    'id': 3,
                    'nom': 'AeroSpace Ltd',
                    'secteur': 'Aéronautique',
                    'adresse': '789 Ave. Aviation, Mirabel, QC',
                    'site_web': 'www.aerospace.com',
                    'notes': 'Pièces aéronautiques'
                }
            ]

            for company in default_companies:
                db.execute_insert('''
                    INSERT OR IGNORE INTO companies (id, nom, secteur, adresse, site_web, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    company['id'], company['nom'], company['secteur'],
                    company['adresse'], company['site_web'], company['notes']
                ))

            print(f"✅ {len(default_companies)} entreprises par défaut créées")

        # Vérifier et créer contacts par défaut
        contacts_count = db.get_table_count('contacts')
        if contacts_count == 0:
            default_contacts = [
                {
                    'id': 1,
                    'prenom': 'Jean',
                    'nom_famille': 'Dubois',
                    'email': 'j.dubois@autotech.com',
                    'telephone': '514-555-0101',
                    'company_id': 1,
                    'role_poste': 'Directeur Technique'
                },
                {
                    'id': 2,
                    'prenom': 'Marie',
                    'nom_famille': 'Tremblay',
                    'email': 'm.tremblay@batitech.ca',
                    'telephone': '418-555-0202',
                    'company_id': 2,
                    'role_poste': 'Ingénieure Projet'
                },
                {
                    'id': 3,
                    'prenom': 'David',
                    'nom_famille': 'Johnson',
                    'email': 'd.johnson@aerospace.com',
                    'telephone': '450-555-0303',
                    'company_id': 3,
                    'role_poste': 'Responsable Achats'
                }
            ]

            for contact in default_contacts:
                db.execute_insert('''
                    INSERT OR IGNORE INTO contacts (id, prenom, nom_famille, email, telephone, company_id, role_poste)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    contact['id'], contact['prenom'], contact['nom_famille'],
                    contact['email'], contact['telephone'], contact['company_id'], contact['role_poste']
                ))

            print(f"✅ {len(default_contacts)} contacts par défaut créés")

        # Initialiser postes de travail si vides
        work_centers_count = db.get_table_count('work_centers')
        if work_centers_count == 0:
            # Créer quelques postes essentiels
            default_work_centers = [
                {
                    'id': 1,
                    'nom': 'Robot ABB GMAW Station 1',
                    'departement': 'PRODUCTION',
                    'categorie': 'ROBOTIQUE',
                    'type_machine': 'Robot de soudage',
                    'capacite_theorique': 8.0,
                    'operateurs_requis': 1,
                    'cout_horaire': 140.0,
                    'competences_requises': 'Soudage GMAW, Programmation Robot'
                },
                {
                    'id': 2,
                    'nom': 'Découpe Plasma CNC',
                    'departement': 'USINAGE',
                    'categorie': 'CNC',
                    'type_machine': 'Table plasma',
                    'capacite_theorique': 7.5,
                    'operateurs_requis': 1,
                    'cout_horaire': 125.0,
                    'competences_requises': 'Découpe plasma, Programmation CNC'
                },
                {
                    'id': 3,
                    'nom': 'Assemblage Manuel Station A',
                    'departement': 'PRODUCTION',
                    'categorie': 'MANUEL',
                    'type_machine': 'Poste assemblage',
                    'capacite_theorique': 8.0,
                    'operateurs_requis': 2,
                    'cout_horaire': 65.0,
                    'competences_requises': 'Assemblage mécanique, Lecture plans'
                }
            ]

            for wc in default_work_centers:
                db.execute_insert('''
                    INSERT OR IGNORE INTO work_centers
                    (id, nom, departement, categorie, type_machine, capacite_theorique,
                     operateurs_requis, cout_horaire, competences_requises)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    wc['id'], wc['nom'], wc['departement'], wc['categorie'],
                    wc['type_machine'], wc['capacite_theorique'], wc['operateurs_requis'],
                    wc['cout_horaire'], wc['competences_requises']
                ))

            print(f"✅ {len(default_work_centers)} postes de travail créés")

    except Exception as e:
        print(f"Erreur initialisation données de base: {e}")

def init_erp_system():
    """Initialise le système ERP complet - MODIFIÉ avec Pièces Jointes"""

    # NOUVEAU : Initialisation du gestionnaire de stockage persistant AVANT tout
    if PERSISTENT_STORAGE_AVAILABLE and 'storage_manager' not in st.session_state:
        try:
            st.session_state.storage_manager = init_persistent_storage()

            # Utiliser le chemin de base de données configuré par le gestionnaire de stockage
            db_path = st.session_state.storage_manager.db_path

            # Notification selon le type de stockage
            storage_info = st.session_state.storage_manager.get_storage_info()
            if storage_info['environment_type'] == 'RENDER_PERSISTENT':
                st.toast("💾 Stockage persistant Render activé !", icon="✅")
            elif storage_info['environment_type'] == 'RENDER_EPHEMERAL':
                st.toast("⚠️ Mode temporaire - Configurez le persistent disk", icon="⚠️")

        except Exception as e:
            st.error(f"❌ Erreur initialisation stockage persistant: {e}")
            # Fallback vers stockage local
            db_path = "erp_production_dg.db"
            st.session_state.storage_manager = None
    else:
        db_path = st.session_state.storage_manager.db_path if st.session_state.get('storage_manager') else "erp_production_dg.db"

    # NOUVELLE ARCHITECTURE : Initialisation ERPDatabase avec chemin configuré
    if ERP_DATABASE_AVAILABLE and 'erp_db' not in st.session_state:
        st.session_state.erp_db = ERPDatabase(db_path)
        st.session_state.migration_completed = True

        # AJOUT CRITIQUE : Initialiser données de base si vides - RÉSOUT ERREURS FK
        _init_base_data_if_empty()

        # Créer une sauvegarde initiale si gestionnaire disponible
        if st.session_state.get('storage_manager'):
            try:
                backup_path = st.session_state.storage_manager.create_backup("initial_startup")
                if backup_path:
                    print(f"✅ Sauvegarde de démarrage créée: {backup_path}")
            except Exception as e:
                print(f"⚠️ Erreur sauvegarde de démarrage: {e}")

    # NOUVELLE ARCHITECTURE : Gestionnaire projets SQLite
    if ERP_DATABASE_AVAILABLE and 'gestionnaire' not in st.session_state:
        st.session_state.gestionnaire = GestionnaireProjetSQL(st.session_state.erp_db)

    # NOUVEAU : Gestionnaire formulaires
    if FORMULAIRES_AVAILABLE and ERP_DATABASE_AVAILABLE and 'gestionnaire_formulaires' not in st.session_state:
        st.session_state.gestionnaire_formulaires = GestionnaireFormulaires(st.session_state.erp_db)

    # NOUVEAU : Gestionnaire fournisseurs
    if FOURNISSEURS_AVAILABLE and ERP_DATABASE_AVAILABLE and 'gestionnaire_fournisseurs' not in st.session_state:
        st.session_state.gestionnaire_fournisseurs = GestionnaireFournisseurs(st.session_state.erp_db)

    # NOUVEAU : Gestionnaire pièces jointes
    if ATTACHMENTS_AVAILABLE and ERP_DATABASE_AVAILABLE and 'attachments_manager' not in st.session_state:
        st.session_state.attachments_manager = init_attachments_manager(
            st.session_state.erp_db,
            st.session_state.get('storage_manager')
        )
        print("✅ Gestionnaire de pièces jointes initialisé")

    # CORRECTION CRITIQUE : CRM avec base SQLite unifiée
    # SECTION MODIFIÉE SELON LA DEMANDE
    if CRM_AVAILABLE and ERP_DATABASE_AVAILABLE and 'gestionnaire_crm' not in st.session_state:
        # On s'assure que le gestionnaire de projets est déjà initialisé
        if 'gestionnaire' in st.session_state:
            st.session_state.gestionnaire_crm = GestionnaireCRM(
                db=st.session_state.erp_db, 
                project_manager=st.session_state.gestionnaire  # Injection de la dépendance ici
            )
            print("✅ Gestionnaire CRM initialisé avec accès au gestionnaire de projets.")
        else:
            # Fallback si le gestionnaire de projet n'est pas prêt (ne devrait pas arriver)
            st.session_state.gestionnaire_crm = GestionnaireCRM(db=st.session_state.erp_db)
            print("⚠️ Gestionnaire CRM initialisé SANS accès au gestionnaire de projets.")

    # Gestionnaire employés (reste identique pour l'instant)
    if EMPLOYEES_AVAILABLE and 'gestionnaire_employes' not in st.session_state:
        st.session_state.gestionnaire_employes = GestionnaireEmployes()

    # ARCHITECTURE UNIFIÉE : Gestionnaire postes intégré dans TimeTracker
    # Plus besoin d'initialiser gestionnaire_postes séparément
    # Il sera initialisé automatiquement dans show_timetracker_unified_interface()

    # CHECKPOINT 6 : INTÉGRATION TIMETRACKER PRO UNIFIÉ
    if TIMETRACKER_AVAILABLE and ERP_DATABASE_AVAILABLE and 'timetracker_unified' not in st.session_state:
        try:
            st.session_state.timetracker_unified = TimeTrackerUnified(st.session_state.erp_db)
            print("✅ TimeTracker Pro Unifié initialisé avec intégration BT complète")
        except Exception as e:
            print(f"Erreur initialisation TimeTracker Pro: {e}")
            st.session_state.timetracker_unified = None

def get_system_stats():
    """Récupère les statistiques système"""
    try:
        if ERP_DATABASE_AVAILABLE and 'erp_db' in st.session_state:
            db = st.session_state.erp_db
            return {
                'projets': db.get_table_count('projects'),
                'employes': db.get_table_count('employees'),
                'entreprises': db.get_table_count('companies'),
                'postes': db.get_table_count('work_centers'),
                'formulaires': db.get_table_count('formulaires') if hasattr(db, 'get_table_count') else 0
            }
    except Exception:
        pass

    # Stats par défaut
    return {
        'projets': 150,
        'employes': 45,
        'entreprises': 80,
        'postes': 61,
        'formulaires': 120
    }

# ========================
# INTERFACE PORTAIL (AVEC CLASSES CSS)
# ========================

def show_portal_home():
    """Affiche la page d'accueil du portail avec classes CSS - SIMPLIFIÉ sans statistiques"""
    # Header principal
    current_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%d/%m/%Y")

    st.markdown(f"""
    <div class="portal-header">
        <h1>🏭 PORTAIL DG INC.</h1>
        <div class="portal-subtitle">
            Système de Gestion Intégré • Production & Métallurgie<br>
            📅 {current_date} • 🕒 {current_time} • Desmarais & Gagné Inc.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("## 🚪 Choisissez votre mode d'accès")

    # Cartes d'accès
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="access-card employee">
            <div class="access-icon">👥</div>
            <div class="access-title">EMPLOYÉ</div>
            <div class="access-description">
                Interface unifiée TimeTracker Pro & Postes de travail
            </div>
            <ul class="access-features">
                <li>⏱️🔧 TimeTracker Pro & Postes Unifiés</li>
                <li>🔧 Bons de Travail Intégrés</li>
                <li>📊 Suivi temps réel</li>
                <li>📱 Interface simplifiée</li>
                <li>🎯 Gestion centralisée</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        if st.button("👥 ACCÈS EMPLOYÉ", key="employee_btn", use_container_width=True, type="primary"):
            st.session_state.app_mode = "employee"
            st.session_state.user_role = "employee"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="access-card admin">
            <div class="access-icon">👨‍💼</div>
            <div class="access-title">ADMINISTRATEUR</div>
            <div class="access-description">
                ERP complet avec authentification sécurisée
            </div>
            <ul class="access-features">
                <li>📋 Gestion projets</li>
                <li>🤝 CRM complet</li>
                <li>📑 Formulaires DG</li>
                <li>🏪 Fournisseurs</li>
                <li>📊 Reporting avancé</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        if st.button("👨‍💼 ACCÈS ADMIN", key="admin_btn", use_container_width=True, type="secondary"):
            st.session_state.app_mode = "admin_auth"
            st.rerun()

    # Footer
    st.markdown("---")
    st.markdown("""
    <div class="portal-footer">
        <h4>🏭 ERP Production DG Inc.</h4>
        <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--border-color); text-align: center;">
            <small style="color: var(--text-color-muted); font-style: italic;">
                💻 Développé par <strong>Sylvain Leduc</strong> • 2025
            </small>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ========================
# GESTION REDIRECTION TIMETRACKER PRO (NOUVEAU)
# ========================

def handle_timetracker_redirect():
    """Gère la redirection vers TimeTracker Pro avec focus BT"""
    if st.session_state.get('timetracker_redirect_to_bt'):
        del st.session_state.timetracker_redirect_to_bt
        
        # Forcer l'affichage de TimeTracker Pro avec onglet BT
        if 'timetracker_unified' in st.session_state:
            st.session_state.timetracker_focus_tab = "bt_management"
            st.success("🔧 Redirection vers TimeTracker Pro - Onglet Gestion BTs")
            show_timetracker_unified_interface()
            return True
    return False

def show_employee_interface():
    """Interface simplifiée pour les employés - TimeTracker uniquement"""
    st.markdown("""
    <div class="employee-header">
        <h2>👥 Interface Employé - DG Inc.</h2>
        <p>TimeTracker Pro & Postes Unifiés et Suivi Production</p>
    </div>
    """, unsafe_allow_html=True)

    # Interface TimeTracker Pro directe (sans onglets)
    if TIMETRACKER_AVAILABLE and 'timetracker_unified' in st.session_state:
        try:
            # Interface TimeTracker Pro complète
            show_timetracker_unified_interface()
        except Exception as e:
            st.error(f"Erreur TimeTracker Pro: {e}")
            show_fallback_timetracker()
    else:
        show_fallback_timetracker()

    # Bouton retour
    st.markdown("---")
    if st.button("🏠 Retour au Portail", use_container_width=True):
        st.session_state.app_mode = "portal"
        st.rerun()

def show_fallback_timetracker():
    """Interface de pointage de substitution"""
    st.markdown("### ⏰ Pointage Simplifié")
    st.info("Interface de pointage temporaire en attendant le déploiement complet du TimeTracker Pro")

    # Interface basique de pointage
    with st.container():
        st.markdown("#### 👤 Informations Employé")

        col1, col2 = st.columns(2)
        with col1:
            employee_name = st.text_input("Nom de l'employé:", placeholder="Ex: Jean Dupont")
            employee_id = st.text_input("ID Employé:", placeholder="Ex: EMP001")

        with col2:
            project_id = st.text_input("Projet:", placeholder="Ex: #10001")
            task_description = st.text_input("Tâche:", placeholder="Ex: Soudage chassis")

        st.markdown("#### 🔧 Actions de Pointage")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🟢 DÉBUTER", use_container_width=True, type="primary"):
                if employee_name and project_id:
                    current_time = datetime.now().strftime("%H:%M:%S")
                    st.success(f"✅ Pointage débuté à {current_time}")
                    st.balloons()

                    # Sauvegarder dans session state
                    if 'pointages_temp' not in st.session_state:
                        st.session_state.pointages_temp = []

                    st.session_state.pointages_temp.append({
                        'employee': employee_name,
                        'project': project_id,
                        'task': task_description,
                        'start_time': current_time,
                        'date': datetime.now().strftime("%Y-%m-%d")
                    })
                else:
                    st.error("Veuillez remplir au minimum le nom et le projet")

        with col2:
            if st.button("⏸️ PAUSE", use_container_width=True):
                st.warning("⏸️ Pause activée")

        with col3:
            if st.button("🔴 TERMINER", use_container_width=True):
                current_time = datetime.now().strftime("%H:%M:%S")
                st.success(f"✅ Pointage terminé à {current_time}")

        # Affichage des pointages temporaires
        if st.session_state.get('pointages_temp'):
            st.markdown("---")
            st.markdown("#### 📊 Pointages de la session")

            df_pointages = pd.DataFrame(st.session_state.pointages_temp)
            st.dataframe(df_pointages, use_container_width=True)

def show_admin_auth():
    """Interface d'authentification administrateur"""
    st.markdown("""
    <div class="admin-auth">
        <h3>🔐 Authentification Administrateur</h3>
        <p style="text-align: center; color: #6B7280;">ERP Production DG Inc. - Accès Restreint</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("admin_login"):
        st.markdown("#### 👤 Identifiants")
        username = st.text_input("Nom d'utilisateur:", placeholder="admin, dg_admin, superviseur, direction, production")
        password = st.text_input("🔒 Mot de passe:", type="password")

        st.markdown("#### 🔒 Connexion")
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("🚀 Se Connecter", use_container_width=True, type="primary")
        with col2:
            cancel = st.form_submit_button("❌ Annuler", use_container_width=True)

        if submitted:
            if verify_admin_password(username, password):
                st.session_state.admin_authenticated = True
                st.session_state.admin_username = username
                st.session_state.admin_login_time = datetime.now()
                st.session_state.admin_permissions = get_user_permissions(username)
                st.session_state.app_mode = "erp"
                st.session_state.user_role = "admin"

                st.markdown(f"""
                <div class="alert-success">
                    ✅ <strong>Connexion réussie !</strong><br>
                    Bienvenue {get_user_display_name(username)}
                </div>
                """, unsafe_allow_html=True)

                st.rerun()
            else:
                st.markdown("""
                <div class="alert-error">
                    ❌ <strong>Échec de connexion</strong><br>
                    Nom d'utilisateur ou mot de passe incorrect.
                </div>
                """, unsafe_allow_html=True)

        if cancel:
            st.session_state.app_mode = "portal"
            st.rerun()

    # Informations de connexion pour demo
    with st.expander("🔒 Comptes de Démonstration", expanded=False):
        st.markdown("""
        **Comptes administrateurs disponibles:**

        - **admin** / admin123 *(Accès complet)*
        - **dg_admin** / dg2024! *(Admin DG Inc.)*
        - **superviseur** / super2024 *(Supervision Production)*
        - **direction** / direction!123 *(Direction Générale)*
        - **production** / prod2024 *(Responsable Production)*

        *En production, ces mots de passe sont configurés via les variables d'environnement*
        """)

# ========================
# ERP PRINCIPAL AVEC PORTAIL (INTÉGRATION COMPLÈTE)
# ========================

def show_erp_main():
    """ERP principal avec authentification et permissions - MENU CHRONOLOGIQUE FABRICATION"""
    # Initialiser l'ERP
    init_erp_system()

    # Header admin
    show_admin_header()

    # Permissions utilisateur
    permissions = st.session_state.get('admin_permissions', [])
    has_all_permissions = "ALL" in permissions

    # NAVIGATION PRINCIPALE - ORDRE CHRONOLOGIQUE DE FABRICATION
    available_pages = {}

    # 1. VUE D'ENSEMBLE
    available_pages["🏠 Tableau de Bord"] = "dashboard"

    # 2. CONTACT CLIENT, OPPORTUNITÉ
    if has_all_permissions or "crm" in permissions:
        available_pages["🤝 CRM"] = "crm_page"

    # 3. CONSULTER PRIX MATÉRIAUX/SERVICES
    if has_all_permissions or "fournisseurs" in permissions:
        available_pages["🏪 Fournisseurs"] = "fournisseurs_page"

    # 4. DEVIS ACCEPTÉ → PROJET CONFIRMÉ
    if has_all_permissions or "projects" in permissions:
        available_pages["📋 Projets"] = "liste"

    # 5. PLANIFICATION FABRICATION
    if has_all_permissions or "projects" in permissions or "inventory" in permissions:
        available_pages["🏭 Production"] = "production_management"    

    # 6. SUIVI TEMPS RÉEL - CHECKPOINT 6: TIMETRACKER PRO
    if has_all_permissions or "timetracker" in permissions or "work_centers" in permissions:
        available_pages["⏱️ TimeTracker"] = "timetracker_pro_page"

    # 7. GESTION ÉQUIPES
    if has_all_permissions or "employees" in permissions:
        available_pages["👥 Employés"] = "employees_page"

    # 8. VUES DE SUIVI (regroupées en fin) - MISE À JOUR AVEC MODULE KANBAN
    if has_all_permissions or "projects" in permissions:
        available_pages["📈 Vue Gantt"] = "gantt"
        available_pages["📅 Calendrier"] = "calendrier"
        # NOUVEAU : Utilisation du module Kanban unifié
        if KANBAN_AVAILABLE:
            available_pages["🔄 Kanban Unifié"] = "kanban"
        else:
            available_pages["🔄 Kanban"] = "kanban"

    # Navigation dans la sidebar
    st.sidebar.markdown("### 🧭 Navigation ERP")
    st.sidebar.markdown("<small>📋 <strong>Chronologie Fabrication:</strong><br/>Contact → Prix → Devis → Projet → Suivi → Production</small>", unsafe_allow_html=True)
    
    # Bouton déconnexion
    if st.sidebar.button("🚪 Se Déconnecter", use_container_width=True):
        st.session_state.admin_authenticated = False
        st.session_state.admin_username = None
        st.session_state.admin_login_time = None
        st.session_state.admin_permissions = []
        st.session_state.app_mode = "portal"
        st.rerun()

    st.sidebar.markdown("---")

    # Menu de navigation chronologique
    sel_page_key = st.sidebar.radio("🏭 Workflow DG Inc.:", list(available_pages.keys()), key="main_nav_radio")
    page_to_show_val = available_pages[sel_page_key]

    # Indication visuelle de l'étape actuelle
    etapes_workflow = {
        "dashboard": "📊 Vue d'ensemble",
        "crm_page": "🤝 Contact client",
        "fournisseurs_page": "🏪 Prix matériaux",
        "formulaires_page": "📑 Création devis",
        "liste": "📋 Gestion projet",
        "timetracker_pro_page": "⏱️🔧 Suivi temps",
        "production_management": "🏭 Fabrication",
        "employees_page": "👥 Équipes",
        "gantt": "📈 Planning",
        "calendrier": "📅 Calendrier",
        "kanban": "🔄 Kanban"
    }
    
    etape_actuelle = etapes_workflow.get(page_to_show_val, "")
    if etape_actuelle:
        st.sidebar.markdown(f"<div style='background:var(--primary-color-lighter);padding:8px;border-radius:5px;text-align:center;margin-bottom:1rem;'><small><strong>Étape:</strong> {etape_actuelle}</small></div>", unsafe_allow_html=True)

    # GESTION SIDEBAR SELON CONTEXTE - MISE À JOUR pour module unifié
    if page_to_show_val == "production_management":
        st.sidebar.markdown("---")
        st.sidebar.markdown("<h4 style='color:var(--primary-color-darker);'>Production Unifié</h4>", unsafe_allow_html=True)
        st.session_state.inv_action_mode = st.sidebar.radio(
            "Mode Inventaire:",
            ["Voir Liste", "Ajouter Article", "Modifier Article"],
            key="inv_action_mode_selector",
            index=["Voir Liste", "Ajouter Article", "Modifier Article"].index(st.session_state.get('inv_action_mode', "Voir Liste"))
        )

    st.sidebar.markdown("---")

    # NOUVEAU : Affichage du statut de stockage persistant dans la sidebar
    show_storage_status_sidebar()

    # Statistiques dans la sidebar - MISE À JOUR avec module unifié
    try:
        total_projects_sql = st.session_state.erp_db.get_table_count('projects')
        total_companies = st.session_state.erp_db.get_table_count('companies')
        total_employees = st.session_state.erp_db.get_table_count('employees')
        total_work_centers = st.session_state.erp_db.get_table_count('work_centers')

        st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>📊 Base de Données</h3>", unsafe_allow_html=True)
        st.sidebar.metric("Base: Projets", total_projects_sql)
        st.sidebar.metric("Base: Entreprises", total_companies)
        st.sidebar.metric("Base: Employés", total_employees)
        st.sidebar.metric("Base: Postes", total_work_centers)

        # Informations sur la base
        schema_info = st.session_state.erp_db.get_schema_info()
        if schema_info['file_size_mb'] > 0:
            st.sidebar.metric("Base: Taille", f"{schema_info['file_size_mb']} MB")
            st.sidebar.metric("Base: Total", f"{schema_info['total_records']}")

        # NOUVEAU : Statistiques inventaire depuis module unifié
        try:
            if 'inventory_manager_sql' not in st.session_state:
                from production_management import GestionnaireInventaireSQL
                st.session_state.inventory_manager_sql = GestionnaireInventaireSQL(st.session_state.erp_db)
            
            inventory_count = len(st.session_state.inventory_manager_sql.get_all_inventory())
            if inventory_count > 0:
                st.sidebar.metric("📦 Articles Stock", inventory_count)
        except Exception:
            pass

    except Exception:
        pass

    # NOUVEAU : Statistiques Formulaires dans la sidebar
    try:
        if 'gestionnaire_formulaires' in st.session_state:
            form_stats = st.session_state.gestionnaire_formulaires.get_statistiques_formulaires()
            total_formulaires = sum(
                type_stats.get('total', 0)
                for type_stats in form_stats.values()
                if isinstance(type_stats, dict)
            )

            if total_formulaires > 0:
                st.sidebar.markdown("---")
                st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>📑 Formulaires</h3>", unsafe_allow_html=True)
                st.sidebar.metric("Total Documents", total_formulaires)

                # Formulaires en attente
                en_attente = form_stats.get('en_attente_validation', 0)
                if en_attente > 0:
                    st.sidebar.metric("⏳ En Attente", en_attente)

                # Formulaires en retard
                en_retard = form_stats.get('en_retard', 0)
                if en_retard > 0:
                    st.sidebar.metric("🚨 En Retard", en_retard)

                # ÉTAPE 4 : Navigation vers TimeTracker depuis Formulaires
                if TIMETRACKER_AVAILABLE and st.sidebar.button("⏱️ Aller au TimeTracker Pro", key="nav_to_tt", use_container_width=True):
                    st.session_state.page_redirect = "timetracker_pro_page"
                    st.session_state.navigation_message = "⏱️ Redirection vers TimeTracker Pro..."
                    st.rerun()

    except Exception:
        pass  # Silencieux si erreur

    # NOUVEAU : Statistiques Fournisseurs dans la sidebar
    try:
        if 'gestionnaire_fournisseurs' not in st.session_state:
            st.session_state.gestionnaire_fournisseurs = GestionnaireFournisseurs(st.session_state.erp_db)

        fournisseurs_stats = st.session_state.gestionnaire_fournisseurs.get_fournisseurs_statistics()

        if fournisseurs_stats and fournisseurs_stats.get('total_fournisseurs', 0) > 0:
            st.sidebar.markdown("---")
            st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>🏪 Fournisseurs</h3>", unsafe_allow_html=True)
            st.sidebar.metric("Total Fournisseurs", fournisseurs_stats.get('total_fournisseurs', 0))
            st.sidebar.metric("Fournisseurs Actifs", fournisseurs_stats.get('fournisseurs_actifs', 0))

            # Évaluation moyenne
            eval_moyenne = fournisseurs_stats.get('evaluation_moyenne', 0)
            if eval_moyenne > 0:
                st.sidebar.metric("⭐ Éval. Moyenne", f"{eval_moyenne}/10")

            # Montant total commandes si significatif
            montant_total = fournisseurs_stats.get('montant_total_commandes', 0)
            if montant_total > 0:
                st.sidebar.metric("💰 Total Commandes", f"{montant_total:,.0f}$")
    except Exception:
        pass  # Silencieux si erreur

    # NOUVEAU : Statistiques Pièces Jointes dans la sidebar
    if ATTACHMENTS_AVAILABLE and 'attachments_manager' in st.session_state:
        try:
            attachments_stats = st.session_state.attachments_manager.get_attachments_statistics()
            
            if attachments_stats.get('total_attachments', 0) > 0:
                st.sidebar.markdown("---")
                st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>📎 Pièces Jointes</h3>", unsafe_allow_html=True)
                st.sidebar.metric("📁 Total Fichiers", attachments_stats.get('total_attachments', 0))
                st.sidebar.metric("💾 Espace Utilisé", f"{attachments_stats.get('total_size_mb', 0)} MB")
                
                # Nombre de catégories utilisées
                categories_count = len(attachments_stats.get('by_category', {}))
                if categories_count > 0:
                    st.sidebar.metric("📂 Catégories", categories_count)
        except Exception:
            pass  # Silencieux si erreur

    # CHECKPOINT 6 : ARCHITECTURE UNIFIÉE : Statistiques postes depuis TimeTracker Pro
    if TIMETRACKER_AVAILABLE and 'timetracker_unified' in st.session_state:
        try:
            postes_stats = st.session_state.timetracker_unified.get_work_centers_statistics()
            if postes_stats.get('total_postes', 0) > 0:
                st.sidebar.markdown("---")
                st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>🏭 Postes Travail</h3>", unsafe_allow_html=True)
                st.sidebar.metric("Postes Actifs", postes_stats.get('total_postes', 0))
                st.sidebar.metric("🤖 Robots", postes_stats.get('postes_robotises', 0))
                st.sidebar.metric("💻 CNC", postes_stats.get('postes_cnc', 0))
        except Exception:
            pass  # Silencieux si erreur

    # CHECKPOINT 6 : INTÉGRATION TIMETRACKER PRO : Statistiques dans la sidebar
    if TIMETRACKER_AVAILABLE and 'timetracker_unified' in st.session_state:
        try:
            tt_stats = st.session_state.timetracker_unified.get_timetracker_statistics_unified()
            if tt_stats.get('total_employees', 0) > 0 or tt_stats.get('active_entries', 0) > 0:
                st.sidebar.markdown("---")
                st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>⏱️🔧 TimeTracker Pro</h3>", unsafe_allow_html=True)
                st.sidebar.metric("👥 Employés", tt_stats.get('total_employees', 0))
                
                # NOUVEAU : Distinction BT
                active_total = tt_stats.get('active_entries', 0)
                active_bt = tt_stats.get('active_entries_bt', 0)
                st.sidebar.metric("🟢 Pointages Actifs", f"{active_total} ({active_bt} BT)")
                
                if tt_stats.get('total_hours_today', 0) > 0:
                    st.sidebar.metric("⏱️ Heures Jour", f"{tt_stats.get('total_hours_today', 0):.1f}h")
                if tt_stats.get('total_revenue_today', 0) > 0:
                    st.sidebar.metric("💰 Revenus Jour", f"{tt_stats.get('total_revenue_today', 0):,.0f}$")
                
                # NOUVEAU : Métriques BT spécifiques
                bt_entries_today = tt_stats.get('bt_entries_today', 0)
                if bt_entries_today > 0:
                    st.sidebar.metric("🔧 Pointages BT", bt_entries_today)
                    bt_revenue_today = tt_stats.get('bt_revenue_today', 0)
                    if bt_revenue_today > 0:
                        st.sidebar.metric("💰 Revenus BT", f"{bt_revenue_today:,.0f}$")

                # ÉTAPE 4 : Navigation vers Bons de Travail depuis TimeTracker
                if st.sidebar.button("🔧 Voir Mes Bons de Travail", key="nav_to_bt", use_container_width=True):
                    st.session_state.page_redirect = "formulaires_page"
                    st.session_state.form_action = "list_bon_travail"
                    st.session_state.navigation_message = "🔧 Redirection vers les Bons de Travail..."
                    st.rerun()
        except Exception:
            pass  # Silencieux si erreur

    # NOUVEAU : Indication module Kanban dans la sidebar
    if KANBAN_AVAILABLE:
        st.sidebar.markdown("---")
        st.sidebar.success("🔄 Module Kanban Unifié Actif")
        st.sidebar.markdown("<small>Vue Projets + Opérations par Postes</small>", unsafe_allow_html=True)
    else:
        st.sidebar.warning("⚠️ Module Kanban - Version interne")

    st.sidebar.markdown("---")
    footer_text = "🏭 ERP Production DG Inc.<br/>🗄️ Architecture Unifiée<br/>📑 Module Formulaires Actif<br/>🏪 Module Fournisseurs Intégré<br/>⏱️🔧 TimeTracker Pro & Postes Unifiés<br/>🏭 Module Production Unifié"

    # NOUVEAU : Indication module Kanban dans footer sidebar
    if KANBAN_AVAILABLE:
        footer_text += "<br/>🔄 Kanban Unifié (Projets + Opérations)"
    else:
        footer_text += "<br/>🔄 Kanban Interne"

    # NOUVEAU : Indication module pièces jointes dans footer sidebar
    if ATTACHMENTS_AVAILABLE:
        footer_text += "<br/>📎 Pièces Jointes Actives"

    # NOUVEAU : Ajouter info stockage persistant dans footer sidebar
    if st.session_state.get('storage_manager'):
        storage_info = st.session_state.storage_manager.get_storage_info()
        if storage_info['environment_type'] == 'RENDER_PERSISTENT':
            footer_text += "<br/>💾 Stockage Persistant Render"
        elif storage_info['environment_type'] == 'RENDER_EPHEMERAL':
            footer_text += "<br/>⚠️ Mode Temporaire"

    st.sidebar.markdown(f"<div style='background:var(--primary-color-lighter);padding:10px;border-radius:8px;text-align:center;'><p style='color:var(--primary-color-darkest);font-size:12px;margin:0;'>{footer_text}</p></div>", unsafe_allow_html=True)

    # PAGES (MODIFIÉES avec module kanban)
    if page_to_show_val == "dashboard":
        show_dashboard()
    elif page_to_show_val == "liste":
        show_liste_projets()
    elif page_to_show_val == "crm_page":
        show_crm_page()
    elif page_to_show_val == "employees_page":
        show_employees_page()
    elif page_to_show_val == "fournisseurs_page":
        if FOURNISSEURS_AVAILABLE:
            show_fournisseurs_page()
        else:
            st.error("❌ Module Fournisseurs non disponible")
    elif page_to_show_val == "formulaires_page":
        if FORMULAIRES_AVAILABLE:
            # CHECKPOINT 6: REDIRECTION BT vers TimeTracker Pro
            st.info("""
            📋 **Formulaires DG Inc. - Évolution du Système**
            
            🔧 **Bons de Travail** → Désormais intégrés dans **⏱️🔧 TimeTracker Pro**
            
            Cette section est réservée aux autres types de formulaires :
            • 🛒 Bons d'Achat • 📦 Bons de Commande • 💰 Demandes de Prix • 📊 Estimations
            """)
            
            col_redirect1, col_redirect2 = st.columns(2)
            with col_redirect1:
                if st.button("🚀 Aller à TimeTracker Pro (pour BTs)", use_container_width=True, type="primary"):
                    # Redirection vers TimeTracker Pro avec onglet BT
                    st.session_state.timetracker_redirect_to_bt = True
                    st.rerun()
            
            with col_redirect2:
                if st.button("📋 Continuer vers Autres Formulaires", use_container_width=True):
                    pass  # Continue vers formulaires non-BT
            
            st.markdown("---")
            show_formulaires_page()
        else:
            st.error("❌ Module Formulaires non disponible")
    elif page_to_show_val == "timetracker_pro_page":
        if TIMETRACKER_AVAILABLE:
            show_timetracker_unified_interface()
        else:
            st.error("❌ TimeTracker Pro non disponible")
            st.info("Le module timetracker_unified.py est requis pour cette fonctionnalité.")
    elif page_to_show_val == "production_management":
        # NOUVEAU : Routage vers module unifié
        if PRODUCTION_MANAGEMENT_AVAILABLE:
            show_production_management_page()
        else:
            st.error("❌ Module Production non disponible")
            st.info("Le module production_management.py est requis pour cette fonctionnalité.")
    elif page_to_show_val == "gantt":
        show_gantt()
    elif page_to_show_val == "calendrier":
        show_calendrier()
    elif page_to_show_val == "kanban":
        # NOUVEAU : Utilisation du module Kanban unifié
        if KANBAN_AVAILABLE:
            show_kanban_sqlite()  # Utilise la fonction du module kanban.py
        else:
            # Fallback sur la fonction interne si le module n'est pas disponible
            show_kanban_legacy()
            st.warning("⚠️ Module kanban.py non disponible - utilisation de la version interne")

    # Affichage des modales et formulaires
    if st.session_state.get('show_project_modal'):
        show_project_modal()
    if st.session_state.get('show_create_project'):
        render_create_project_form(st.session_state.gestionnaire, st.session_state.gestionnaire_crm)
    if st.session_state.get('show_edit_project'):
        render_edit_project_form(st.session_state.gestionnaire, st.session_state.gestionnaire_crm, st.session_state.edit_project_data)
    if st.session_state.get('show_delete_confirmation'):
        render_delete_confirmation(st.session_state.gestionnaire)
    
    # NOUVEAU : Gestion des actions en lot
    if st.session_state.get('batch_action'):
        handle_batch_actions()

# ========================
# AFFICHAGE DU STATUT DE STOCKAGE DANS LA SIDEBAR (ORIGINAL)
# ========================

def show_storage_status_sidebar():
    """Affiche le statut du stockage persistant dans la sidebar"""
    if 'storage_manager' not in st.session_state:
        return

    try:
        storage_info = st.session_state.storage_manager.get_storage_info()

        st.sidebar.markdown("---")
        st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>💾 Stockage</h3>", unsafe_allow_html=True)

        # Statut principal
        if storage_info['is_persistent']:
            st.sidebar.success("💾 Stockage Persistant")
        else:
            st.sidebar.warning("⚠️ Stockage Éphémère")

        # Informations de base
        if storage_info['db_exists']:
            st.sidebar.metric("Base ERP", f"{storage_info['db_size_mb']} MB")

        if storage_info.get('backup_count', 0) > 0:
            st.sidebar.metric("Sauvegardes", storage_info['backup_count'])

        # Usage disque (Render uniquement)
        if storage_info.get('disk_usage'):
            disk = storage_info['disk_usage']
            st.sidebar.metric("Usage Disque", f"{disk['usage_percent']}%")
            if disk['usage_percent'] > 80:
                st.sidebar.warning("⚠️ Espace disque faible")

        # Type d'environnement (en petit)
        env_display = {
            'RENDER_PERSISTENT': '🚀 Render Persistent',
            'RENDER_EPHEMERAL': '⚠️ Render Temporaire',
            'LOCAL_DEVELOPMENT': '💻 Développement',
            'CUSTOM_PATH': '📁 Personnalisé'
        }

        st.sidebar.caption(f"Type: {env_display.get(storage_info['environment_type'], 'Inconnu')}")

    except Exception as e:
        st.sidebar.error(f"Erreur statut stockage: {str(e)[:50]}...")

# ========================
# FONCTIONS DE VUE ET DE RENDU ERP (MODIFIÉES AVEC GESTION PROJETS COMPLÈTE + PIÈCES JOINTES)
# ========================

def show_dashboard():
    """Dashboard principal utilisant les classes CSS - MODIFIÉ avec Pièces Jointes"""
    st.markdown("""
    <div class="main-title">
        <h1>📊 Tableau de Bord ERP Production</h1>
    </div>
    """, unsafe_allow_html=True)
    
    gestionnaire = st.session_state.gestionnaire
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    # ARCHITECTURE UNIFIÉE : Postes via TimeTracker
    postes_stats = {'total_postes': 0, 'postes_robotises': 0, 'postes_cnc': 0, 'par_departement': {}}
    if TIMETRACKER_AVAILABLE and 'timetracker_unified' in st.session_state:
        try:
            # Récupérer les stats postes depuis TimeTracker unifié
            postes_stats = st.session_state.timetracker_unified.get_work_centers_statistics()
        except Exception:
            pass  # Utiliser les stats par défaut si erreur

    # NOUVEAU : Gestionnaire fournisseurs pour métriques
    if 'gestionnaire_fournisseurs' not in st.session_state:
        st.session_state.gestionnaire_fournisseurs = GestionnaireFournisseurs(st.session_state.erp_db)
    gestionnaire_fournisseurs = st.session_state.gestionnaire_fournisseurs

    # NOUVEAU : Gestionnaire formulaires pour métriques
    if FORMULAIRES_AVAILABLE and 'gestionnaire_formulaires' not in st.session_state:
        st.session_state.gestionnaire_formulaires = GestionnaireFormulaires(st.session_state.erp_db)

    gestionnaire_formulaires = st.session_state.get('gestionnaire_formulaires')

    # Messages de notification supprimés pour une interface plus épurée

    stats = get_project_statistics(gestionnaire)
    emp_stats = gestionnaire_employes.get_statistiques_employes()
    
    # ARCHITECTURE UNIFIÉE : Stats postes depuis TimeTracker
    # postes_stats déjà initialisé plus haut

    # NOUVEAU : Statistiques formulaires
    form_stats = gestionnaire_formulaires.get_statistiques_formulaires() if gestionnaire_formulaires else {}

    # NOUVEAU : Statistiques fournisseurs
    fournisseurs_stats = gestionnaire_fournisseurs.get_fournisseurs_statistics()

    if stats['total'] == 0 and emp_stats.get('total', 0) == 0:
        st.markdown("""
        <div class='welcome-card'>
            <h3>🏭 Bienvenue dans l'ERP Production DG Inc. !</h3>
            <p>Architecture unifiée avec TimeTracker Pro, Kanban Unifié et Pièces Jointes intégrés. Créez votre premier projet ou explorez les données migrées.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Métriques Projets
    if stats['total'] > 0:
        st.markdown("### 🚀 Aperçu Projets")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("📊 Total Projets", stats['total'])
        with c2:
            st.metric("🚀 Projets Actifs", stats['projets_actifs'])
        with c3:
            st.metric("✅ Taux Completion", f"{stats['taux_completion']:.1f}%")
        with c4:
            st.metric("💰 CA Total", format_currency(stats['ca_total']))

    # NOUVEAU : Métriques Production Unifiée
    if PRODUCTION_MANAGEMENT_AVAILABLE:
        st.markdown("### 🏭 Aperçu Production Unifiée")
        prod_c1, prod_c2, prod_c3, prod_c4 = st.columns(4)

        with prod_c1:
            # Stats inventaire depuis module unifié
            try:
                if 'inventory_manager_sql' not in st.session_state:
                    from production_management import GestionnaireInventaireSQL
                    st.session_state.inventory_manager_sql = GestionnaireInventaireSQL(st.session_state.erp_db)
                
                inventory_count = len(st.session_state.inventory_manager_sql.get_all_inventory())
                st.metric("📦 Articles Stock", inventory_count)
            except Exception:
                st.metric("📦 Articles Stock", 0)

        with prod_c2:
            # Stats BOM depuis projets
            total_materials = 0
            try:
                for project in gestionnaire.projets:
                    total_materials += len(project.get('materiaux', []))
                st.metric("📋 Matériaux BOM", total_materials)
            except Exception:
                st.metric("📋 Matériaux BOM", 0)

        with prod_c3:
            # Stats opérations itinéraire
            total_operations = 0
            try:
                for project in gestionnaire.projets:
                    total_operations += len(project.get('operations', []))
                st.metric("🛠️ Opérations", total_operations)
            except Exception:
                st.metric("🛠️ Opérations", 0)

        with prod_c4:
            st.metric("✅ Module Unifié", "ACTIF" if PRODUCTION_MANAGEMENT_AVAILABLE else "INACTIF")

    # NOUVEAU : Métriques Formulaires
    if gestionnaire_formulaires and any(form_stats.values()):
        st.markdown("### 📑 Aperçu Formulaires DG Inc.")
        form_c1, form_c2, form_c3, form_c4, form_c5 = st.columns(5)

        with form_c1:
            total_bt = form_stats.get('BON_TRAVAIL', {}).get('total', 0) if isinstance(form_stats.get('BON_TRAVAIL'), dict) else 0
            st.metric("🔧 Bons Travail", total_bt)
        with form_c2:
            total_ba = form_stats.get('BON_ACHAT', {}).get('total', 0) if isinstance(form_stats.get('BON_ACHAT'), dict) else 0
            st.metric("🛒 Bons Achats", total_ba)
        with form_c3:
            total_bc = form_stats.get('BON_COMMANDE', {}).get('total', 0) if isinstance(form_stats.get('BON_COMMANDE'), dict) else 0
            st.metric("📦 Bons Commande", total_bc)
        with form_c4:
            total_dp = form_stats.get('DEMANDE_PRIX', {}).get('total', 0) if isinstance(form_stats.get('DEMANDE_PRIX'), dict) else 0
            st.metric("💰 Demandes Prix", total_dp)
        with form_c5:
            total_est = form_stats.get('ESTIMATION', {}).get('total', 0) if isinstance(form_stats.get('ESTIMATION'), dict) else 0
            st.metric("📊 Estimations", total_est)

        # Montant total des formulaires
        montant_total_forms = sum(
            type_stats.get('montant_total', 0)
            for type_stats in form_stats.values()
            if isinstance(type_stats, dict)
        )
        if montant_total_forms > 0:
            st.markdown(f"**💼 Valeur Documents: {montant_total_forms:,.0f}$ CAD**")

    # NOUVEAU : Métriques Fournisseurs DG Inc.
    if fournisseurs_stats and fournisseurs_stats.get('total_fournisseurs', 0) > 0:
        st.markdown("### 🏪 Aperçu Fournisseurs DG Inc.")
        fournisseur_c1, fournisseur_c2, fournisseur_c3, fournisseur_c4 = st.columns(4)

        with fournisseur_c1:
            st.metric("🏪 Total Fournisseurs", fournisseurs_stats.get('total_fournisseurs', 0))
        with fournisseur_c2:
            st.metric("✅ Fournisseurs Actifs", fournisseurs_stats.get('fournisseurs_actifs', 0))
        with fournisseur_c3:
            eval_moyenne = fournisseurs_stats.get('evaluation_moyenne', 0)
            st.metric("⭐ Évaluation Moy.", f"{eval_moyenne}/10")
        with fournisseur_c4:
            delai_moyen = fournisseurs_stats.get('delai_moyen', 0)
            st.metric("📦 Délai Moyen", f"{delai_moyen}j")

        # Montant total fournisseurs
        montant_total_fournisseurs = fournisseurs_stats.get('montant_total_commandes', 0)
        if montant_total_fournisseurs > 0:
            st.markdown(f"**💰 Volume Total Commandes: {montant_total_fournisseurs:,.0f}$ CAD**")

    # NOUVEAU : Métriques Pièces Jointes
    if ATTACHMENTS_AVAILABLE and 'attachments_manager' in st.session_state:
        try:
            attachments_stats = st.session_state.attachments_manager.get_attachments_statistics()
            
            if attachments_stats.get('total_attachments', 0) > 0:
                st.markdown("### 📎 Aperçu Pièces Jointes")
                att_c1, att_c2, att_c3, att_c4 = st.columns(4)
                
                with att_c1:
                    st.metric("📁 Total Fichiers", attachments_stats.get('total_attachments', 0))
                with att_c2:
                    st.metric("💾 Taille Totale", f"{attachments_stats.get('total_size_mb', 0)} MB")
                with att_c3:
                    categories_count = len(attachments_stats.get('by_category', {}))
                    st.metric("📂 Catégories", categories_count)
                with att_c4:
                    # Calcul de la taille moyenne par fichier
                    avg_size = attachments_stats.get('total_size_mb', 0) / max(attachments_stats.get('total_attachments', 1), 1)
                    st.metric("📊 Taille Moy.", f"{avg_size:.1f} MB")
                
                # Répartition par catégorie
                if attachments_stats.get('by_category'):
                    st.markdown("**📂 Répartition par Catégorie:**")
                    for category, count in attachments_stats['by_category'].items():
                        category_info = st.session_state.attachments_manager.categories.get(category, {'icon': '📎', 'label': category})
                        st.markdown(f"- {category_info['icon']} {category_info['label']}: {count} fichier(s)")
        except Exception as e:
            st.warning(f"Erreur statistiques pièces jointes: {e}")

    # Métriques postes de travail
    if postes_stats['total_postes'] > 0:
        st.markdown("### 🏭 Aperçu Production DG Inc.")
        prod_c1, prod_c2, prod_c3, prod_c4 = st.columns(4)
        with prod_c1:
            st.metric("🏭 Total Postes", postes_stats['total_postes'])
        with prod_c2:
            st.metric("🤖 Robots ABB", postes_stats['postes_robotises'])
        with prod_c3:
            st.metric("💻 Postes CNC", postes_stats['postes_cnc'])
        with prod_c4:
            efficacite_globale = random.uniform(82, 87)  # Simulation temps réel
            st.metric("⚡ Efficacité", f"{efficacite_globale:.1f}%")

    # CHECKPOINT 6 : INTÉGRATION TIMETRACKER PRO : Métriques temps et revenus
    if TIMETRACKER_AVAILABLE and 'timetracker_unified' in st.session_state:
        try:
            timetracker_stats = st.session_state.timetracker_unified.get_timetracker_statistics_unified()
            if timetracker_stats.get('total_employees', 0) > 0 or timetracker_stats.get('total_entries_today', 0) > 0:
                st.markdown("### ⏱️🔧 Aperçu TimeTracker Pro")
                tt_c1, tt_c2, tt_c3, tt_c4 = st.columns(4)
                with tt_c1:
                    st.metric("👥 Employés ERP", timetracker_stats.get('total_employees', 0))
                with tt_c2:
                    active_total = timetracker_stats.get('active_entries', 0)
                    active_bt = timetracker_stats.get('active_entries_bt', 0)
                    st.metric("🟢 Pointages Actifs", f"{active_total} ({active_bt} BT)")
                with tt_c3:
                    st.metric("📊 Heures Jour", f"{timetracker_stats.get('total_hours_today', 0):.1f}h")
                with tt_c4:
                    revenue_display = f"{timetracker_stats.get('total_revenue_today', 0):,.0f}$ CAD"
                    st.metric("💰 Revenus Jour", revenue_display)
        except Exception as e:
            st.warning(f"TimeTracker Pro stats non disponibles: {str(e)}")

    # Métriques RH
    if emp_stats.get('total', 0) > 0:
        st.markdown("### 👥 Aperçu Ressources Humaines")
        emp_c1, emp_c2, emp_c3, emp_c4 = st.columns(4)
        with emp_c1:
            st.metric("👥 Total Employés", emp_stats['total'])
        with emp_c2:
            employes_actifs = len([emp for emp in gestionnaire_employes.employes if emp.get('statut') == 'ACTIF'])
            st.metric("✅ Employés Actifs", employes_actifs)
        with emp_c3:
            st.metric("💰 Salaire Moyen", f"{emp_stats.get('salaire_moyen', 0):,.0f}€")
        with emp_c4:
            employes_surcharges = len([emp for emp in gestionnaire_employes.employes if emp.get('charge_travail', 0) > 90])
            st.metric("⚠️ Surchargés", employes_surcharges)

    st.markdown("<br>", unsafe_allow_html=True)

    # Graphiques combinés
    if stats['total'] > 0 or postes_stats['total_postes'] > 0:
        gc1, gc2 = st.columns(2)

        TEXT_COLOR_CHARTS = 'var(--text-color)'

        with gc1:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            if stats['par_statut']:
                colors_statut = {'À FAIRE': '#f59e0b', 'EN COURS': '#3b82f6', 'EN ATTENTE': '#ef4444', 'TERMINÉ': '#10b981', 'ANNULÉ': '#6b7280', 'LIVRAISON': '#8b5cf6'}
                fig = px.pie(values=list(stats['par_statut'].values()), names=list(stats['par_statut'].keys()), title="📈 Projets par Statut", color_discrete_map=colors_statut)
                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT_COLOR_CHARTS), legend_title_text='', title_x=0.5)
                st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with gc2:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            if postes_stats.get('par_departement'):
                colors_dept = {'PRODUCTION': '#10b981', 'USINAGE': '#3b82f6', 'QUALITE': '#f59e0b', 'LOGISTIQUE': '#8b5cf6', 'COMMERCIAL': '#ef4444'}
                fig = px.bar(x=list(postes_stats['par_departement'].keys()), y=list(postes_stats['par_departement'].values()),
                           title="🏭 Postes par Département", color=list(postes_stats['par_departement'].keys()),
                           color_discrete_map=colors_dept)
                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT_COLOR_CHARTS), showlegend=False, title_x=0.5)
                st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # Projets récents depuis SQLite
        st.markdown("---")
        st.markdown("### 🕒 Projets Récents")
        projets_recents = sorted(gestionnaire.projets, key=lambda x: x.get('id', 0), reverse=True)[:5]
        if not projets_recents:
            st.info("Aucun projet récent.")
        for p in projets_recents:
            st.markdown("<div class='info-card'>", unsafe_allow_html=True)
            rc1, rc2, rc3, rc4 = st.columns([3, 2, 2, 1])
            with rc1:
                st.markdown(f"**#{p.get('id')} - {p.get('nom_projet', 'Sans nom')}**")
                st.caption(f"📝 {p.get('description', 'N/A')[:100]}...")
            with rc2:
                client_display_name = p.get('client_nom_cache', 'N/A')
                if client_display_name == 'N/A' and p.get('client_company_id'):
                    crm_manager = st.session_state.gestionnaire_crm
                    entreprise = crm_manager.get_entreprise_by_id(p.get('client_company_id'))
                    if entreprise:
                        client_display_name = entreprise.get('nom', 'N/A')
                elif client_display_name == 'N/A':
                    client_display_name = p.get('client_legacy', 'N/A')

                st.markdown(f"👤 **{client_display_name}**")
                st.caption(f"💰 {format_currency(p.get('prix_estime', 0))}")
            with rc3:
                statut, priorite = p.get('statut', 'N/A'), p.get('priorite', 'N/A')
                statut_map = {'À FAIRE': '🟡', 'EN COURS': '🔵', 'EN ATTENTE': '🔴', 'TERMINÉ': '🟢', 'ANNULÉ': '⚫', 'LIVRAISON': '🟣'}
                priorite_map = {'ÉLEVÉ': '🔴', 'MOYEN': '🟡', 'BAS': '🟢'}
                st.markdown(f"{statut_map.get(statut, '⚪')} {statut}")
                st.caption(f"{priorite_map.get(priorite, '⚪')} {priorite}")
            with rc4:
                if st.button("👁️", key=f"view_rec_{p.get('id')}", help="Voir détails"):
                    st.session_state.selected_project = p
                    st.session_state.show_project_modal = True
                # NOUVEAU : Bouton création BT depuis projet récent
                if st.button("🔧", key=f"bt_rec_{p.get('id')}", help="Créer Bon de Travail"):
                    st.session_state.form_action = "create_bon_travail"
                    st.session_state.formulaire_project_preselect = p.get('id')
                    st.session_state.page_redirect = "formulaires_page"
                    st.rerun()
                # NOUVEAU : Bouton création BA depuis projet récent
                if st.button("🛒", key=f"ba_rec_{p.get('id')}", help="Créer Bon d'Achat"):
                    st.session_state.form_action = "create_bon_achat"
                    st.session_state.formulaire_project_preselect = p.get('id')
                    st.session_state.page_redirect = "formulaires_page"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

def show_liste_projets():
    """Liste des projets avec fonctionnalités CRUD complètes - VERSION FINALE"""
    
    # Appliquer les styles CSS supplémentaires
    apply_additional_project_styles()
    
    st.markdown("### 📋 Gestion des Projets DG Inc.")
    gestionnaire = st.session_state.gestionnaire
    crm_manager = st.session_state.gestionnaire_crm

    # Gestion des actions en lot en priorité
    if st.session_state.get('batch_action'):
        handle_batch_actions()
        return

    # Boutons d'actions principales
    col_create, col_refresh, col_export, col_stats = st.columns([2, 1, 1, 1])
    with col_create:
        if st.button("➕ Nouveau Projet", use_container_width=True, key="create_btn_liste", type="primary"):
            st.session_state.show_create_project = True
            st.rerun()
    with col_refresh:
        if st.button("🔄 Actualiser", use_container_width=True, key="refresh_btn_liste"):
            st.rerun()
    with col_export:
        if st.button("📊 Export CSV", use_container_width=True, key="export_btn_liste"):
            if gestionnaire.projets:
                csv_content = export_projects_to_csv(gestionnaire.projets, crm_manager)
                if csv_content:
                    st.download_button(
                        label="⬇️ Télécharger CSV",
                        data=csv_content,
                        file_name=f"projets_dg_inc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            else:
                st.info("Aucun projet à exporter")
    with col_stats:
        if st.button("📈 Statistiques", use_container_width=True, key="stats_btn_liste"):
            st.session_state.show_project_stats = not st.session_state.get('show_project_stats', False)

    # Affichage des statistiques si activé
    if st.session_state.get('show_project_stats', False) and gestionnaire.projets:
        with st.expander("📊 Statistiques Détaillées", expanded=True):
            show_project_statistics(gestionnaire.projets, crm_manager)

    st.markdown("---")

    if not gestionnaire.projets and not st.session_state.get('show_create_project'):
        st.markdown("""
        <div class="project-stats">
            <h5>🚀 Commencez votre premier projet !</h5>
            <p>Aucun projet en base. Cliquez sur 'Nouveau Projet' pour commencer.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    if gestionnaire.projets:
        # Interface de filtrage et recherche avancée
        with st.expander("🔍 Filtres et Recherche Avancée", expanded=False):
            search_col, filter_col1, filter_col2, sort_col = st.columns(4)
            
            # Récupération des valeurs uniques pour les filtres
            statuts_dispo = sorted(list(set([p.get('statut', 'N/A') for p in gestionnaire.projets])))
            priorites_dispo = sorted(list(set([p.get('priorite', 'N/A') for p in gestionnaire.projets])))
            
            with search_col:
                recherche = st.text_input(
                    "🔍 Recherche globale:", 
                    placeholder="Nom, client, description, ID...",
                    value=st.session_state.get('project_search_term', ''),
                    key="project_search_input"
                )
                st.session_state.project_search_term = recherche
            
            with filter_col1:
                filtre_statut = st.multiselect(
                    "Statut:", 
                    ['Tous'] + statuts_dispo, 
                    default=st.session_state.get('project_filter_statut', ['Tous']),
                    key="project_filter_statut_input"
                )
                st.session_state.project_filter_statut = filtre_statut
            
            with filter_col2:
                filtre_priorite = st.multiselect(
                    "Priorité:", 
                    ['Toutes'] + priorites_dispo, 
                    default=st.session_state.get('project_filter_priorite', ['Toutes']),
                    key="project_filter_priorite_input"
                )
                st.session_state.project_filter_priorite = filtre_priorite
            
            with sort_col:
                tri_par = st.selectbox(
                    "Trier par:", 
                    ["ID (Desc)", "ID (Asc)", "Nom", "Client", "Date Début", "Prix", "Statut"],
                    index=["ID (Desc)", "ID (Asc)", "Nom", "Client", "Date Début", "Prix", "Statut"].index(
                        st.session_state.get('project_sort_by', "ID (Desc)")
                    ),
                    key="project_sort_input"
                )
                st.session_state.project_sort_by = tri_par

            # Bouton de réinitialisation des filtres
            if st.button("🔄 Réinitialiser Filtres", key="reset_filters"):
                st.session_state.project_search_term = ''
                st.session_state.project_filter_statut = ['Tous']
                st.session_state.project_filter_priorite = ['Toutes']
                st.session_state.project_sort_by = "ID (Desc)"
                st.rerun()

        # Application des filtres et recherche
        projets_filtres = gestionnaire.projets
        
        # Recherche avancée
        if recherche:
            projets_filtres = advanced_project_search(projets_filtres, recherche, crm_manager)
        
        # Filtres par statut
        if 'Tous' not in filtre_statut and filtre_statut:
            projets_filtres = [p for p in projets_filtres if p.get('statut') in filtre_statut]
        
        # Filtres par priorité
        if 'Toutes' not in filtre_priorite and filtre_priorite:
            projets_filtres = [p for p in projets_filtres if p.get('priorite') in filtre_priorite]

        # Application du tri
        projets_filtres = sort_projects(projets_filtres, tri_par, crm_manager)

        # Résultats de la recherche
        total_projets = len(gestionnaire.projets)
        projets_affiches = len(projets_filtres)
        
        # Barre de résultats avec métriques rapides
        result_col1, result_col2, result_col3 = st.columns(3)
        with result_col1:
            st.markdown(f"**🔍 {projets_affiches} projet(s) sur {total_projets} total**")
        with result_col2:
            if projets_filtres:
                ca_filtre = sum(float(str(p.get('prix_estime', 0)).replace(' ', '').replace(',', '') or 0) for p in projets_filtres)
                st.markdown(f"**💰 CA filtré: {format_currency(ca_filtre)}**")
        with result_col3:
            if projets_filtres:
                temps_filtre = sum(float(p.get('bd_ft_estime', 0) or 0) for p in projets_filtres)
                st.markdown(f"**⏱️ Temps filtré: {temps_filtre:.1f}h**")
        
        if projets_filtres:
            # Mode d'affichage
            view_mode = st.radio(
                "Mode d'affichage:", 
                ["📋 Liste Détaillée", "📊 Tableau Compact", "🃏 Cartes Compactes"], 
                horizontal=True,
                index=["📋 Liste Détaillée", "📊 Tableau Compact", "🃏 Cartes Compactes"].index(
                    st.session_state.get('project_view_mode', "📋 Liste Détaillée")
                ),
                key="project_view_mode_input"
            )
            st.session_state.project_view_mode = view_mode
            
            if view_mode == "📊 Tableau Compact":
                show_projects_table_view(projets_filtres, crm_manager)
            elif view_mode == "🃏 Cartes Compactes":
                show_projects_card_view(projets_filtres, crm_manager)
            else:
                show_projects_detailed_view(projets_filtres, crm_manager)
        
        else:
            st.markdown("""
            <div class="project-stats">
                <h5>🔍 Aucun résultat trouvé</h5>
                <p>Essayez d'ajuster vos critères de recherche ou de filtrage.</p>
            </div>
            """, unsafe_allow_html=True)

def render_create_project_form(gestionnaire, crm_manager):
    """FORMULAIRE CRÉATION PROJET - VERSION CORRIGÉE avec validation FK et numérotation manuelle"""
    gestionnaire_employes = st.session_state.gestionnaire_employes

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### ➕ Créer Projet DG Inc.")

    # VALIDATION PRÉALABLE des données de base
    companies_count = st.session_state.erp_db.get_table_count('companies')
    if companies_count == 0:
        st.warning("⚠️ Aucune entreprise en base. Initialisation...")
        _init_base_data_if_empty()
        st.rerun()

    with st.form("create_form", clear_on_submit=True):
        # NOUVEAU : Champ pour numéro personnalisé
        st.markdown("#### 🔢 Numérotation")
        custom_number_col, auto_number_col = st.columns(2)
        
        with custom_number_col:
            custom_project_id = st.text_input(
                "Numéro personnalisé (optionnel):",
                placeholder="Ex: 20250001, DG-2025-001",
                help="Laissez vide pour génération automatique"
            )
        
        with auto_number_col:
            if custom_project_id:
                st.info(f"🎯 Utilisation du numéro: **{custom_project_id}**")
            else:
                next_auto_id = gestionnaire.next_id
                st.info(f"🔄 Numéro automatique: **#{next_auto_id}**")

        st.markdown("---")
        
        fc1, fc2 = st.columns(2)
        with fc1:
            nom = st.text_input("Nom *:")

            # CORRECTION CRITIQUE : Récupérer entreprises depuis SQLite
            try:
                entreprises_db = st.session_state.erp_db.execute_query("SELECT id, nom FROM companies ORDER BY nom")
                liste_entreprises_crm_form = [("", "Sélectionner ou laisser vide")] + [(e['id'], e['nom']) for e in entreprises_db]
            except Exception as e:
                st.error(f"Erreur récupération entreprises: {e}")
                liste_entreprises_crm_form = [("", "Aucune entreprise disponible")]

            selected_entreprise_id_form = st.selectbox(
                "Client (Entreprise) *:",
                options=[e_id for e_id, _ in liste_entreprises_crm_form],
                format_func=lambda e_id: next((nom for id_e, nom in liste_entreprises_crm_form if id_e == e_id), "Sélectionner..."),
                key="project_create_client_select"
            )
            client_nom_direct_form = st.text_input("Ou nom client direct (si non listé):")

            statut = st.selectbox("Statut:", ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON"])
            priorite = st.selectbox("Priorité:", ["BAS", "MOYEN", "ÉLEVÉ"])

        with fc2:
            tache = st.selectbox("Type:", ["ESTIMATION", "CONCEPTION", "DÉVELOPPEMENT", "TESTS", "DÉPLOIEMENT", "MAINTENANCE", "FORMATION"])
            d_debut = st.date_input("Début:", datetime.now().date())
            d_fin = st.date_input("Fin Prévue:", datetime.now().date() + timedelta(days=30))
            bd_ft = st.number_input("BD-FT (h):", 0, value=40, step=1)
            prix = st.number_input("Prix ($):", 0.0, value=10000.0, step=100.0, format="%.2f")

        desc = st.text_area("Description:")

        # Assignation d'employés avec validation
        employes_assignes = []
        if gestionnaire_employes.employes:
            st.markdown("##### 👥 Assignation d'Employés")
            employes_disponibles = [(emp['id'], f"{emp.get('prenom', '')} {emp.get('nom', '')} ({emp.get('poste', '')})") for emp in gestionnaire_employes.employes if emp.get('statut') == 'ACTIF']
            if employes_disponibles:
                employes_assignes = st.multiselect(
                    "Employés assignés:",
                    options=[emp_id for emp_id, _ in employes_disponibles],
                    format_func=lambda emp_id: next((nom for id_e, nom in employes_disponibles if id_e == emp_id), ""),
                    key="project_create_employes_assign"
                )

        st.markdown("<small>* Obligatoire</small>", unsafe_allow_html=True)
        s_btn, c_btn = st.columns(2)
        with s_btn:
            submit = st.form_submit_button("💾 Créer le Projet", use_container_width=True)
        with c_btn:
            cancel = st.form_submit_button("❌ Annuler", use_container_width=True)

        if submit:
            # VALIDATION RENFORCÉE
            if not nom:
                st.error("Nom du projet obligatoire.")
            elif not selected_entreprise_id_form and not client_nom_direct_form:
                st.error("Client (entreprise ou nom direct) obligatoire.")
            elif d_fin < d_debut:
                st.error("Date fin < date début.")
            else:
                # VALIDATION CLÉS ÉTRANGÈRES
                client_company_id = None
                client_nom_cache_val = ""

                if selected_entreprise_id_form:
                    # Vérifier que l'entreprise existe
                    company_check = st.session_state.erp_db.execute_query(
                        "SELECT nom FROM companies WHERE id = ?",
                        (selected_entreprise_id_form,)
                    )
                    if company_check:
                        client_company_id = selected_entreprise_id_form
                        client_nom_cache_val = company_check[0]['nom']
                    else:
                        st.error(f"Entreprise ID {selected_entreprise_id_form} non trouvée en base.")
                        return
                elif client_nom_direct_form:
                    client_nom_cache_val = client_nom_direct_form

                # Validation employés assignés
                employes_valides = []
                if employes_assignes:
                    for emp_id in employes_assignes:
                        emp_check = st.session_state.erp_db.execute_query(
                            "SELECT id FROM employees WHERE id = ?",
                            (emp_id,)
                        )
                        if emp_check:
                            employes_valides.append(emp_id)
                        else:
                            st.warning(f"Employé ID {emp_id} non trouvé - ignoré")

                # NOUVEAU : Ajouter le numéro personnalisé aux données
                data = {
                    'nom_projet': nom,
                    'custom_project_id': custom_project_id if custom_project_id.strip() else None,
                    'client_company_id': client_company_id,  # NULL si client direct
                    'client_nom_cache': client_nom_cache_val,
                    'client_legacy': client_nom_direct_form if not selected_entreprise_id_form else "",
                    'statut': statut,
                    'priorite': priorite,
                    'tache': tache,
                    'date_soumis': d_debut.strftime('%Y-%m-%d'),
                    'date_prevu': d_fin.strftime('%Y-%m-%d'),
                    'bd_ft_estime': float(bd_ft),
                    'prix_estime': float(prix),
                    'description': desc or f"Projet {tache.lower()} pour {client_nom_cache_val}",
                    'employes_assignes': employes_valides
                }

                try:
                    pid = gestionnaire.ajouter_projet(data)

                    if pid:
                        # Mettre à jour les assignations des employés
                        if employes_valides:
                            for emp_id in employes_valides:
                                employe = gestionnaire_employes.get_employe_by_id(emp_id)
                                if employe:
                                    projets_existants = employe.get('projets_assignes', [])
                                    if pid not in projets_existants:
                                        projets_existants.append(pid)
                                        gestionnaire_employes.modifier_employe(emp_id, {'projets_assignes': projets_existants})

                        # Message de succès avec indication du type de numérotation
                        if custom_project_id:
                            st.success(f"✅ Projet #{pid} créé avec numéro personnalisé et {len(employes_valides)} employé(s) assigné(s) !")
                        else:
                            st.success(f"✅ Projet #{pid} créé avec numérotation automatique et {len(employes_valides)} employé(s) assigné(s) !")
                        
                        st.session_state.show_create_project = False
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la création du projet")

                except Exception as e:
                    st.error(f"❌ Erreur création projet: {str(e)}")
                    st.info("💡 Vérifiez que les données de base sont initialisées (entreprises, employés)")

        if cancel:
            st.session_state.show_create_project = False
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

def render_edit_project_form(gestionnaire, crm_manager, project_data):
    """Formulaire d'édition de projet - VERSION COMPLÈTE CORRIGÉE"""
    gestionnaire_employes = st.session_state.gestionnaire_employes

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(f"### ✏️ Modifier Projet #{project_data.get('id')}")

    with st.form("edit_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)

        with fc1:
            nom = st.text_input("Nom *:", value=project_data.get('nom_projet', ''))

            # Gestion de la liste des entreprises CRM
            try:
                entreprises_db = st.session_state.erp_db.execute_query("SELECT id, nom FROM companies ORDER BY nom")
                liste_entreprises_crm_form = [("", "Sélectionner ou laisser vide")] + [(e['id'], e['nom']) for e in entreprises_db]
            except Exception as e:
                st.error(f"Erreur récupération entreprises: {e}")
                liste_entreprises_crm_form = [("", "Aucune entreprise disponible")]

            current_entreprise_id = project_data.get('client_company_id', "")
            selected_entreprise_id_form = st.selectbox(
                "Client (Entreprise) *:",
                options=[e_id for e_id, _ in liste_entreprises_crm_form],
                index=next((i for i, (e_id, _) in enumerate(liste_entreprises_crm_form) if e_id == current_entreprise_id), 0),
                format_func=lambda e_id: next((nom for id_e, nom in liste_entreprises_crm_form if id_e == e_id), "Sélectionner..."),
                key="project_edit_client_select"
            )
            client_nom_direct_form = st.text_input("Ou nom client direct:", value=project_data.get('client_legacy', ''))

            # Gestion du statut
            statuts = ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON"]
            current_statut = project_data.get('statut', 'À FAIRE')
            statut = st.selectbox("Statut:", statuts, index=statuts.index(current_statut) if current_statut in statuts else 0)

            # Gestion de la priorité
            priorites = ["BAS", "MOYEN", "ÉLEVÉ"]
            current_priorite = project_data.get('priorite', 'MOYEN')
            priorite = st.selectbox("Priorité:", priorites, index=priorites.index(current_priorite) if current_priorite in priorites else 1)

        with fc2:
            # Gestion du type de tâche
            taches = ["ESTIMATION", "CONCEPTION", "DÉVELOPPEMENT", "TESTS", "DÉPLOIEMENT", "MAINTENANCE", "FORMATION"]
            current_tache = project_data.get('tache', 'ESTIMATION')
            tache = st.selectbox("Type:", taches, index=taches.index(current_tache) if current_tache in taches else 0)

            # Gestion des dates
            try:
                d_debut = st.date_input("Début:", datetime.strptime(project_data.get('date_soumis', ''), '%Y-%m-%d').date())
            except (ValueError, TypeError):
                d_debut = st.date_input("Début:", datetime.now().date())

            try:
                d_fin = st.date_input("Fin Prévue:", datetime.strptime(project_data.get('date_prevu', ''), '%Y-%m-%d').date())
            except (ValueError, TypeError):
                d_fin = st.date_input("Fin Prévue:", datetime.now().date() + timedelta(days=30))

            # Gestion BD-FT
            try:
                bd_ft_val = int(project_data.get('bd_ft_estime', 0))
            except (ValueError, TypeError):
                bd_ft_val = 0
            bd_ft = st.number_input("BD-FT (h):", 0, value=bd_ft_val, step=1)

            # Gestion du prix
            try:
                prix_str = str(project_data.get('prix_estime', '0'))
                # Nettoyer la chaîne de tous les caractères non numériques sauf le point décimal
                prix_str = prix_str.replace(' ', '').replace(',', '.').replace('€', '').replace(', '')
                # Traitement des formats de prix différents
                if ',' in prix_str and ('.' not in prix_str or prix_str.find(',') > prix_str.find('.')):
                    prix_str = prix_str.replace('.', '').replace(',', '.')
                elif ',' in prix_str and '.' in prix_str and prix_str.find('.') > prix_str.find(','):
                    prix_str = prix_str.replace(',', '')

                prix_val = float(prix_str) if prix_str else 0.0
            except (ValueError, TypeError):
                prix_val = 0.0

            prix = st.number_input("Prix ($):", 0.0, value=prix_val, step=100.0, format="%.2f")

        # Description
        desc = st.text_area("Description:", value=project_data.get('description', ''))

        # Assignation d'employés
        employes_assignes = []
        if gestionnaire_employes.employes:
            st.markdown("##### 👥 Assignation d'Employés")
            employes_disponibles = [
                (emp['id'], f"{emp.get('prenom', '')} {emp.get('nom', '')} ({emp.get('poste', '')})")
                for emp in gestionnaire_employes.employes
                if emp.get('statut') == 'ACTIF'
            ]
            current_employes = project_data.get('employes_assignes', [])
            employes_assignes = st.multiselect(
                "Employés assignés:",
                options=[emp_id for emp_id, _ in employes_disponibles],
                default=[emp_id for emp_id in current_employes if emp_id in [e[0] for e in employes_disponibles]],
                format_func=lambda emp_id: next((nom for id_e, nom in employes_disponibles if id_e == emp_id), ""),
                key="project_edit_employes_assign"
            )

        st.markdown("<small>* Obligatoire</small>", unsafe_allow_html=True)

        # Boutons d'action
        s_btn, c_btn = st.columns(2)
        with s_btn:
            submit = st.form_submit_button("💾 Sauvegarder", use_container_width=True)
        with c_btn:
            cancel = st.form_submit_button("❌ Annuler", use_container_width=True)

        # Traitement de la soumission
        if submit:
            if not nom or (not selected_entreprise_id_form and not client_nom_direct_form):
                st.error("Nom du projet et Client obligatoires.")
            elif d_fin < d_debut:
                st.error("Date fin < date début.")
            else:
                # Détermination du nom du client pour cache
                client_nom_cache_val = ""
                if selected_entreprise_id_form:
                    entreprise_obj = crm_manager.get_entreprise_by_id(selected_entreprise_id_form)
                    if entreprise_obj:
                        client_nom_cache_val = entreprise_obj.get('nom', '')
                elif client_nom_direct_form:
                    client_nom_cache_val = client_nom_direct_form

                # Préparation des données de mise à jour
                update_data = {
                    'nom_projet': nom,
                    'client_company_id': selected_entreprise_id_form if selected_entreprise_id_form else None,
                    'client_nom_cache': client_nom_cache_val,
                    'client_legacy': client_nom_direct_form if not selected_entreprise_id_form and client_nom_direct_form else "",
                    'statut': statut,
                    'priorite': priorite,
                    'tache': tache,
                    'date_soumis': d_debut.strftime('%Y-%m-%d'),
                    'date_prevu': d_fin.strftime('%Y-%m-%d'),
                    'bd_ft_estime': str(bd_ft),
                    'prix_estime': str(prix),
                    'description': desc,
                    'employes_assignes': employes_assignes
                }

                # Mise à jour du projet
                if gestionnaire.modifier_projet(project_data['id'], update_data):
                    # Mettre à jour les assignations des employés
                    if employes_assignes:
                        # Supprimer l'ancien projet des anciens employés
                        for emp_id in project_data.get('employes_assignes', []):
                            if emp_id not in employes_assignes:
                                employe = gestionnaire_employes.get_employe_by_id(emp_id)
                                if employe:
                                    projets_existants = employe.get('projets_assignes', [])
                                    if project_data['id'] in projets_existants:
                                        projets_existants.remove(project_data['id'])
                                        gestionnaire_employes.modifier_employe(emp_id, {'projets_assignes': projets_existants})

                        # Ajouter le projet aux nouveaux employés
                        for emp_id in employes_assignes:
                            if emp_id not in project_data.get('employes_assignes', []):
                                employe = gestionnaire_employes.get_employe_by_id(emp_id)
                                if employe:
                                    projets_existants = employe.get('projets_assignes', [])
                                    if project_data['id'] not in projets_existants:
                                        projets_existants.append(project_data['id'])
                                        gestionnaire_employes.modifier_employe(emp_id, {'projets_assignes': projets_existants})

                    st.success(f"✅ Projet #{project_data['id']} modifié avec succès !")
                    st.session_state.show_edit_project = False
                    st.session_state.edit_project_data = None
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la modification.")

        # Traitement de l'annulation
        if cancel:
            st.session_state.show_edit_project = False
            st.session_state.edit_project_data = None
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

def render_delete_confirmation(gestionnaire):
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### 🗑️ Confirmation de Suppression")
    project_id = st.session_state.delete_project_id
    project = next((p for p in gestionnaire.projets if p.get('id') == project_id), None)

    if project:
        st.warning(f"⚠️ Êtes-vous sûr de vouloir supprimer le projet **#{project.get('id')} - {project.get('nom_projet', 'N/A')}** ?")
        st.markdown("Cette action est **irréversible** et supprimera toutes les données associées (opérations, matériaux, assignations).")

        dcol1, dcol2 = st.columns(2)
        with dcol1:
            if st.button("🗑️ Confirmer Suppression", use_container_width=True):
                if gestionnaire.supprimer_projet(project_id):
                    st.success(f"✅ Projet #{project_id} supprimé avec succès !")
                    st.session_state.show_delete_confirmation = False
                    st.session_state.delete_project_id = None
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la suppression")
        with dcol2:
            if st.button("❌ Annuler", use_container_width=True):
                st.session_state.show_delete_confirmation = False
                st.session_state.delete_project_id = None
                st.rerun()
    else:
        st.error("Projet non trouvé.")
        st.session_state.show_delete_confirmation = False
        st.session_state.delete_project_id = None
    st.markdown("</div>", unsafe_allow_html=True)

def show_crm_page():
    """
    Affiche l'interface CRM complète en utilisant le module CRM dédié.
    Cette fonction appelle directement l'interface principale du module CRM,
    qui gère ses propres onglets (y compris les Devis) et actions.
    """
    gestionnaire_crm = st.session_state.gestionnaire_crm
    gestionnaire_projets = st.session_state.gestionnaire

    # Appel de la nouvelle interface unifiée qui inclut les devis
    render_crm_main_interface(gestionnaire_crm, gestionnaire_projets)

def show_employees_page():
    st.markdown("### 👥 Gestion des Employés")
    gestionnaire_employes = st.session_state.gestionnaire_employes
    gestionnaire_projets = st.session_state.gestionnaire

    if 'emp_action' not in st.session_state:
        st.session_state.emp_action = None
    if 'emp_selected_id' not in st.session_state:
        st.session_state.emp_selected_id = None
    if 'emp_confirm_delete_id' not in st.session_state:
        st.session_state.emp_confirm_delete_id = None

    tab_dashboard, tab_liste = st.tabs([
        "📊 Dashboard RH", "👥 Liste Employés"
    ])

    with tab_dashboard:
        render_employes_dashboard_tab(gestionnaire_employes, gestionnaire_projets)

    with tab_liste:
        render_employes_liste_tab(gestionnaire_employes, gestionnaire_projets)

    action = st.session_state.get('emp_action')
    selected_id = st.session_state.get('emp_selected_id')

    if action == "create_employe":
        render_employe_form(gestionnaire_employes, employe_data=None)
    elif action == "edit_employe" and selected_id:
        employe_data = gestionnaire_employes.get_employe_by_id(selected_id)
        render_employe_form(gestionnaire_employes, employe_data=employe_data)
    elif action == "view_employe_details" and selected_id:
        employe_data = gestionnaire_employes.get_employe_by_id(selected_id)
        render_employe_details(gestionnaire_employes, gestionnaire_projets, employe_data)

def show_gantt():
    st.markdown("### 📈 Diagramme de Gantt")
    gestionnaire = st.session_state.gestionnaire
    crm_manager = st.session_state.gestionnaire_crm

    if not gestionnaire.projets:
        st.info("Aucun projet disponible pour le Gantt.")
        return

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    gantt_data = []
    for p in gestionnaire.projets:
        try:
            s_date = datetime.strptime(p.get('date_soumis', ''), "%Y-%m-%d") if p.get('date_soumis') else None
            e_date = datetime.strptime(p.get('date_prevu', ''), "%Y-%m-%d") if p.get('date_prevu') else None

            if s_date and e_date:
                client_display_name_gantt = p.get('client_nom_cache', 'N/A')
                if client_display_name_gantt == 'N/A' and p.get('client_company_id'):
                    entreprise = crm_manager.get_entreprise_by_id(p.get('client_company_id'))
                    if entreprise:
                        client_display_name_gantt = entreprise.get('nom', 'N/A')
                elif client_display_name_gantt == 'N/A':
                    client_display_name_gantt = p.get('client_legacy', 'N/A')

                gantt_data.append({
                    'Projet': f"#{p.get('id')} - {p.get('nom_projet', 'N/A')}",
                    'Début': s_date,
                    'Fin': e_date,
                    'Client': client_display_name_gantt,
                    'Statut': p.get('statut', 'N/A'),
                    'Priorité': p.get('priorite', 'N/A')
                })
        except:
            continue

    if not gantt_data:
        st.warning("Données de dates invalides pour le Gantt.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    df_gantt = pd.DataFrame(gantt_data)
    colors_gantt = {'À FAIRE': '#f59e0b', 'EN COURS': '#3b82f6', 'EN ATTENTE': '#ef4444', 'TERMINÉ': '#10b981', 'ANNULÉ': '#6b7280', 'LIVRAISON': '#8b5cf6'}

    TEXT_COLOR_CHARTS = 'var(--text-color)'

    fig = px.timeline(
        df_gantt,
        x_start="Début",
        x_end="Fin",
        y="Projet",
        color="Statut",
        color_discrete_map=colors_gantt,
        title="📊 Planning Projets",
        hover_data=['Client', 'Priorité']
    )

    fig.update_layout(
        height=max(400, len(gantt_data) * 40),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color=TEXT_COLOR_CHARTS),
        xaxis=dict(title="📅 Calendrier", gridcolor='rgba(0,0,0,0.05)'),
        yaxis=dict(title="📋 Projets", gridcolor='rgba(0,0,0,0.05)', categoryorder='total ascending'),
        title_x=0.5,
        legend_title_text=''
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("##### 📊 Statistiques Planning")
    durees = [(item['Fin'] - item['Début']).days for item in gantt_data if item['Fin'] and item['Début']]
    if durees:
        gsc1, gsc2, gsc3 = st.columns(3)
        with gsc1:
            st.metric("📅 Durée Moy.", f"{sum(durees) / len(durees):.1f} j")
        with gsc2:
            st.metric("⏱️ Min Durée", f"{min(durees)} j")
        with gsc3:
            st.metric("🕐 Max Durée", f"{max(durees)} j")

    st.markdown("</div>", unsafe_allow_html=True)

def show_calendrier():
    st.markdown("### 📅 Vue Calendrier")
    gestionnaire = st.session_state.gestionnaire
    crm_manager = st.session_state.gestionnaire_crm
    curr_date = st.session_state.selected_date

    # Navigation
    cn1, cn2, cn3 = st.columns([1, 2, 1])
    with cn1:
        if st.button("◀️ Mois Préc.", key="cal_prev", use_container_width=True):
            prev_m = curr_date.replace(day=1) - timedelta(days=1)
            st.session_state.selected_date = prev_m.replace(day=min(curr_date.day, calendar.monthrange(prev_m.year, prev_m.month)[1]))
            st.rerun()
    with cn2:
        m_names = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        st.markdown(f"<div class='project-header' style='margin-bottom:1rem; text-align:center;'><h4 style='margin:0; color:#1E40AF;'>{m_names[curr_date.month]} {curr_date.year}</h4></div>", unsafe_allow_html=True)
    with cn3:
        if st.button("Mois Suiv. ▶️", key="cal_next", use_container_width=True):
            next_m = (curr_date.replace(day=calendar.monthrange(curr_date.year, curr_date.month)[1])) + timedelta(days=1)
            st.session_state.selected_date = next_m.replace(day=min(curr_date.day, calendar.monthrange(next_m.year, next_m.month)[1]))
            st.rerun()

    if st.button("📅 Aujourd'hui", key="cal_today", use_container_width=True):
        st.session_state.selected_date = date.today()
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Préparation des données depuis SQLite
    events_by_date = {}
    for p in gestionnaire.projets:
        try:
            s_date_obj = datetime.strptime(p.get('date_soumis', ''), "%Y-%m-%d").date() if p.get('date_soumis') else None
            e_date_obj = datetime.strptime(p.get('date_prevu', ''), "%Y-%m-%d").date() if p.get('date_prevu') else None

            client_display_name_cal = p.get('client_nom_cache', 'N/A')
            if client_display_name_cal == 'N/A':
                 client_display_name_cal = p.get('client_legacy', 'N/A')

            if s_date_obj:
                if s_date_obj not in events_by_date:
                    events_by_date[s_date_obj] = []
                events_by_date[s_date_obj].append({
                    'type': '🚀 Début',
                    'projet': p.get('nom_projet', 'N/A'),
                    'id': p.get('id'),
                    'client': client_display_name_cal,
                    'color_class': 'event-type-debut'
                })
            if e_date_obj:
                if e_date_obj not in events_by_date:
                    events_by_date[e_date_obj] = []
                events_by_date[e_date_obj].append({
                    'type': '🏁 Fin',
                    'projet': p.get('nom_projet', 'N/A'),
                    'id': p.get('id'),
                    'client': client_display_name_cal,
                    'color_class': 'event-type-fin'
                })
        except:
            continue

    # Affichage de la grille du calendrier
    cal = calendar.Calendar(firstweekday=6)
    month_dates = cal.monthdatescalendar(curr_date.year, curr_date.month)
    day_names = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"]

    st.markdown('<div class="calendar-grid-container">', unsafe_allow_html=True)
    # En-têtes des jours
    header_cols = st.columns(7)
    for i, name in enumerate(day_names):
        with header_cols[i]:
            st.markdown(f"<div class='calendar-week-header'><div class='day-name'>{name}</div></div>", unsafe_allow_html=True)

    # Grille des jours
    for week in month_dates:
        cols = st.columns(7)
        for i, day_date_obj in enumerate(week):
            with cols[i]:
                day_classes = ["calendar-day-cell"]
                if day_date_obj.month != curr_date.month:
                    day_classes.append("other-month")
                if day_date_obj == date.today():
                    day_classes.append("today")

                events_html = ""
                if day_date_obj in events_by_date:
                    for event in events_by_date[day_date_obj]:
                        events_html += f"<div class='calendar-event-item {event['color_class']}' title='{event['projet']}'>{event['type']} P#{event['id']}</div>"

                cell_html = f"""
                <div class='{' '.join(day_classes)}'>
                    <div class='day-number'>{day_date_obj.day}</div>
                    <div class='calendar-events-container'>{events_html}</div>
                </div>
                """
                st.markdown(cell_html, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

def show_kanban_legacy():
    """
    ANCIENNE FONCTION KANBAN (renommée pour éviter conflit avec le module)
    Gardée comme fallback si le module kanban.py n'est pas disponible
    """
    st.markdown("### 🔄 Vue Kanban (Style Planner)")
    gestionnaire = st.session_state.gestionnaire
    crm_manager = st.session_state.gestionnaire_crm

    # Initialisation de l'état de drag & drop
    if 'dragged_project_id' not in st.session_state:
        st.session_state.dragged_project_id = None
    if 'dragged_from_status' not in st.session_state:
        st.session_state.dragged_from_status = None

    if not gestionnaire.projets:
        st.info("Aucun projet à afficher dans le Kanban.")
        return

    # Logique de filtrage
    with st.expander("🔍 Filtres", expanded=False):
        recherche = st.text_input("Rechercher par nom, client...", key="kanban_search")

    projets_filtres = gestionnaire.projets
    if recherche:
        terme = recherche.lower()
        projets_filtres = [
            p for p in projets_filtres if
            terme in str(p.get('nom_projet', '')).lower() or
            terme in str(p.get('client_nom_cache', '')).lower() or
            (p.get('client_company_id') and crm_manager.get_entreprise_by_id(p.get('client_company_id')) and terme in crm_manager.get_entreprise_by_id(p.get('client_company_id')).get('nom', '').lower()) or
            terme in str(p.get('client_legacy', '')).lower()
        ]

    # Préparation des données pour les colonnes
    statuts_k = ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON"]
    projs_by_statut = {s: [] for s in statuts_k}
    for p in projets_filtres:
        stat = p.get('statut', 'À FAIRE')
        if stat in projs_by_statut:
            projs_by_statut[stat].append(p)
        else:
            projs_by_statut['À FAIRE'].append(p)

    # Définition des couleurs pour les colonnes
    col_borders_k = {'À FAIRE': '#f59e0b', 'EN COURS': '#3b82f6', 'EN ATTENTE': '#ef4444', 'TERMINÉ': '#10b981', 'LIVRAISON': '#8b5cf6'}

    # Indicateur visuel si un projet est en cours de déplacement
    if st.session_state.dragged_project_id:
        proj_dragged = next((p for p in gestionnaire.projets if p['id'] == st.session_state.dragged_project_id), None)
        if proj_dragged:
            st.markdown(f"""
            <div class="kanban-drag-indicator">
                🔄 Déplacement en cours: <strong>#{proj_dragged['id']} - {proj_dragged['nom_projet']}</strong>
            </div>
            """, unsafe_allow_html=True)
            if st.sidebar.button("❌ Annuler le déplacement", use_container_width=True):
                st.session_state.dragged_project_id = None
                st.session_state.dragged_from_status = None
                st.rerun()

    # STRUCTURE HORIZONTALE
    st.markdown('<div class="kanban-container">', unsafe_allow_html=True)

    # Créer colonnes pour chaque statut
    cols = st.columns(len(statuts_k))

    for idx, sk in enumerate(statuts_k):
        with cols[idx]:
            # En-tête de la colonne
            st.markdown(f"""
            <div class="kanban-column" style="border-top: 4px solid {col_borders_k.get(sk, '#ccc')};">
                <div class="kanban-header">{sk} ({len(projs_by_statut[sk])})</div>
            </div>
            """, unsafe_allow_html=True)

            # Si un projet est "soulevé", afficher une zone de dépôt
            if st.session_state.dragged_project_id and sk != st.session_state.dragged_from_status:
                if st.button(f"⤵️ Déposer ici", key=f"drop_in_{sk}", use_container_width=True, help=f"Déplacer vers {sk}"):
                    proj_id_to_move = st.session_state.dragged_project_id
                    if gestionnaire.modifier_projet(proj_id_to_move, {'statut': sk}):
                        st.success(f"Projet #{proj_id_to_move} déplacé vers '{sk}' !")
                    else:
                        st.error("Erreur lors du déplacement.")

                    st.session_state.dragged_project_id = None
                    st.session_state.dragged_from_status = None
                    st.rerun()

            # Zone pour les cartes
            if not projs_by_statut[sk]:
                st.markdown("<div style='text-align:center; color:var(--text-color-muted); margin-top:2rem;'><i>Vide</i></div>", unsafe_allow_html=True)

            for pk in projs_by_statut[sk]:
                prio_k = pk.get('priorite', 'MOYEN')
                card_borders_k = {'ÉLEVÉ': '#ef4444', 'MOYEN': '#f59e0b', 'BAS': '#10b981'}
                prio_icons_k = {'ÉLEVÉ': '🔴', 'MOYEN': '🟡', 'BAS': '🟢'}

                client_display_name_kanban = pk.get('client_nom_cache', 'N/A')
                if client_display_name_kanban == 'N/A' and pk.get('client_company_id'):
                    entreprise = crm_manager.get_entreprise_by_id(pk.get('client_company_id'))
                    client_display_name_kanban = entreprise.get('nom', 'N/A') if entreprise else 'N/A'
                elif client_display_name_kanban == 'N/A':
                    client_display_name_kanban = pk.get('client_legacy', 'N/A')

                # Affichage de la carte
                st.markdown(f"""
                <div class='kanban-card' style='border-left-color:{card_borders_k.get(prio_k, 'var(--border-color)')};'>
                    <div class='kanban-card-title'>#{pk.get('id')} - {pk.get('nom_projet', 'N/A')}</div>
                    <div class='kanban-card-info'>👤 {client_display_name_kanban}</div>
                    <div class='kanban-card-info'>{prio_icons_k.get(prio_k, '⚪')} {prio_k}</div>
                    <div class='kanban-card-info'>💰 {format_currency(pk.get('prix_estime', 0))}</div>
                </div>
                """, unsafe_allow_html=True)

                # Boutons d'action pour la carte - MODIFIÉ avec BT et BA
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("👁️", key=f"view_kanban_{pk['id']}", help="Voir les détails", use_container_width=True):
                        st.session_state.selected_project = pk
                        st.session_state.show_project_modal = True
                        st.rerun()
                with col2:
                    # NOUVEAU : Bouton création BT dans Kanban - REDIRECTION vers TimeTracker Pro
                    if st.button("🔧", key=f"bt_kanban_{pk['id']}", help="Créer Bon de Travail", use_container_width=True):
                        st.session_state.timetracker_redirect_to_bt = True
                        st.session_state.formulaire_project_preselect = pk['id']
                        st.session_state.page_redirect = "timetracker_pro_page"
                        st.rerun()
                with col3:
                    # NOUVEAU : Bouton création BA dans Kanban
                    if st.button("🛒", key=f"ba_kanban_{pk['id']}", help="Créer Bon d'Achat", use_container_width=True):
                        st.session_state.form_action = "create_bon_achat"
                        st.session_state.formulaire_project_preselect = pk['id']
                        st.session_state.page_redirect = "formulaires_page"
                        st.rerun()
                with col4:
                    if st.button("➡️", key=f"move_kanban_{pk['id']}", help="Déplacer ce projet", use_container_width=True):
                        st.session_state.dragged_project_id = pk['id']
                        st.session_state.dragged_from_status = sk
                        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

def show_project_modal():
    """Affichage des détails d'un projet dans un expander - MODIFIÉ avec opérations complètes BT incluses"""
    if 'selected_project' not in st.session_state or not st.session_state.get('show_project_modal') or not st.session_state.selected_project:
        return

    proj_mod = st.session_state.selected_project

    with st.expander(f"📁 Détails Projet #{proj_mod.get('id')} - {proj_mod.get('nom_projet', 'N/A')}", expanded=True):
        if st.button("✖️ Fermer", key="close_modal_details_btn_top"):
            st.session_state.show_project_modal = False
            st.rerun()

        st.markdown("---")

        # Informations principales (inchangé)
        mc1, mc2 = st.columns(2)
        with mc1:
            st.markdown(f"""
            <div class='info-card'>
                <h4>📋 {proj_mod.get('nom_projet', 'N/A')}</h4>
                <p><strong>👤 Client:</strong> {proj_mod.get('client_nom_cache', 'N/A')}</p>
                <p><strong>🚦 Statut:</strong> {proj_mod.get('statut', 'N/A')}</p>
                <p><strong>⭐ Priorité:</strong> {proj_mod.get('priorite', 'N/A')}</p>
                <p><strong>✅ Tâche:</strong> {proj_mod.get('tache', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)

        with mc2:
            st.markdown(f"""
            <div class='info-card'>
                <h4>📊 Finances</h4>
                <p><strong>💰 Prix:</strong> {format_currency(proj_mod.get('prix_estime', 0))}</p>
                <p><strong>⏱️ BD-FT:</strong> {proj_mod.get('bd_ft_estime', 'N/A')}h</p>
                <p><strong>📅 Début:</strong> {proj_mod.get('date_soumis', 'N/A')}</p>
                <p><strong>🏁 Fin:</strong> {proj_mod.get('date_prevu', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)

        if proj_mod.get('description'):
            st.markdown("##### 📝 Description")
            st.markdown(f"<div class='info-card'><p>{proj_mod.get('description', 'Aucune.')}</p></div>", unsafe_allow_html=True)

        # Onglets avec opérations complètes et pièces jointes
        if ATTACHMENTS_AVAILABLE:
            tabs_mod = st.tabs(["🔧 Opérations Complètes", "📎 Pièces Jointes"])
        else:
            tabs_mod = st.tabs(["🔧 Opérations Complètes"])

        # Onglet Opérations MODIFIÉ - Récupération complète via base de données
        with tabs_mod[0]:
            try:
                # NOUVEAU : Récupérer TOUTES les opérations du projet via la base de données
                # Cela inclut les opérations directes ET celles créées via les Bons de Travail
                project_id = proj_mod.get('id')
                if project_id and hasattr(st.session_state, 'erp_db'):
                    all_operations = st.session_state.erp_db.get_project_operations_with_work_centers(project_id)
                else:
                    # Fallback sur l'ancienne méthode si la base n'est pas disponible
                    all_operations = proj_mod.get('operations', [])
                
                if not all_operations:
                    st.info("Aucune opération définie pour ce projet.")
                else:
                    # Regrouper les opérations par source
                    operations_directes = []
                    operations_bt = []
                    
                    for op in all_operations:
                        if op.get('formulaire_bt_id'):
                            # Opération créée via un Bon de Travail
                            operations_bt.append(op)
                        else:
                            # Opération directe du projet
                            operations_directes.append(op)
                    
                    # Afficher les statistiques globales
                    total_temps = sum(float(op.get('temps_estime', 0) or 0) for op in all_operations)
                    total_operations = len(all_operations)
                    
                    st.markdown(f"""
                    <div class='info-card' style='background:var(--primary-color-lighter);text-align:center;margin-bottom:1rem;'>
                        <h5 style='color:var(--primary-color-darker);margin:0;'>
                            📊 Total: {total_operations} opération(s) | ⏱️ Temps Total: {total_temps:.1f}h
                        </h5>
                        <p style='margin:0.5rem 0 0 0;font-size:0.9em;'>
                            🔧 Directes: {len(operations_directes)} | 📋 Via Bons de Travail: {len(operations_bt)}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Section 1 : Opérations directes du projet
                    if operations_directes:
                        st.markdown("#### 🔧 Opérations Directes du Projet")
                        for op in operations_directes:
                            _afficher_operation_dans_modal(op, "var(--primary-color)")
                    
                    # Section 2 : Opérations via Bons de Travail
                    if operations_bt:
                        st.markdown("#### 📋 Opérations via Bons de Travail")
                        
                        # Regrouper par BT
                        bt_groups = {}
                        for op in operations_bt:
                            bt_id = op.get('formulaire_bt_id')
                            bt_numero = op.get('bt_numero', f'BT #{bt_id}')
                            if bt_numero not in bt_groups:
                                bt_groups[bt_numero] = {
                                    'bt_id': bt_id,
                                    'bt_statut': op.get('bt_statut', 'N/A'),
                                    'operations': []
                                }
                            bt_groups[bt_numero]['operations'].append(op)
                        
                        # Afficher par BT
                        for bt_numero, bt_data in bt_groups.items():
                            bt_statut = bt_data['bt_statut']
                            bt_color = {
                                'BROUILLON': '#f59e0b',
                                'VALIDÉ': '#3b82f6', 
                                'EN COURS': '#10b981',
                                'TERMINÉ': '#059669',
                                'ANNULÉ': '#ef4444'
                            }.get(bt_statut, '#6b7280')
                            
                            st.markdown(f"""
                            <div style='background:#f8fafc;border:1px solid {bt_color};border-radius:6px;padding:0.5rem;margin:0.5rem 0;'>
                                <h6 style='margin:0;color:{bt_color};'>📋 {bt_numero} - Statut: {bt_statut}</h6>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            for op in bt_data['operations']:
                                _afficher_operation_dans_modal(op, bt_color)
                    
            except Exception as e:
                st.error(f"Erreur lors de la récupération des opérations: {e}")
                # Fallback sur l'ancienne méthode
                ops_mod = proj_mod.get('operations', [])
                if not ops_mod:
                    st.info("Aucune opération définie.")
                else:
                    total_t_mod = 0
                    for op_item in ops_mod:
                        tps = op_item.get('temps_estime', 0)
                        total_t_mod += tps
                        _afficher_operation_dans_modal(op_item, "orange")

                    st.markdown(f"""
                    <div class='info-card' style='background:var(--primary-color-lighter);text-align:center;margin-top:1rem;'>
                        <h5 style='color:var(--primary-color-darker);margin:0;'>⏱️ Temps Total Est.: {total_t_mod}h</h5>
                    </div>
                    """, unsafe_allow_html=True)

        # Onglet Pièces Jointes (maintenant à l'indice 1)
        if ATTACHMENTS_AVAILABLE:
            with tabs_mod[1]:
                show_attachments_tab_in_project_modal(proj_mod)

        st.markdown("---")
        if st.button("✖️ Fermer", use_container_width=True, key="close_modal_details_btn_bottom"):
            st.session_state.show_project_modal = False
            st.rerun()


def _afficher_operation_dans_modal(operation, border_color):
    """Fonction helper pour afficher une opération dans la modal avec informations complètes"""
    temps = operation.get('temps_estime', 0)
    statut = operation.get('statut', 'À FAIRE')
    
    # Couleur selon le statut
    statut_color = {
        'À FAIRE': '#f59e0b',
        'EN COURS': '#3b82f6',
        'TERMINÉ': '#10b981'
    }.get(statut, '#6b7280')
    
    # Informations sur le poste de travail
    poste_travail = operation.get('work_center_name') or operation.get('poste_travail', 'Non assigné')
    departement = operation.get('work_center_departement', '')
    cout_horaire = operation.get('work_center_cout_horaire', 0)
    
    # Calcul du coût estimé
    try:
        cout_estime = float(temps or 0) * float(cout_horaire or 0)
    except (ValueError, TypeError):
        cout_estime = 0.0
    
    # Numéro de séquence
    sequence = operation.get('sequence_number') or operation.get('sequence', '?')
    
    # Description de l'opération
    description = operation.get('description', 'N/A')
    
    # Ressource assignée
    ressource = operation.get('ressource', 'N/A')
    
    st.markdown(f"""
    <div class='info-card' style='border-left:4px solid {border_color};margin-top:0.5rem;'>
        <div style='display:flex;justify-content:space-between;align-items:center;'>
            <h5 style='margin:0 0 0.3rem 0;'>
                {sequence} - {description}
            </h5>
            <span style='background:{statut_color};color:white;padding:2px 8px;border-radius:4px;font-size:0.8em;'>
                {statut}
            </span>
        </div>
        <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;font-size:0.9em;margin-top:0.5rem;'>
            <div>
                <strong>🏭 Poste:</strong> {poste_travail}<br>
                <small style='color:#6b7280;'>{departement}</small>
            </div>
            <div>
                <strong>⏱️ Temps:</strong> {temps}h<br>
                <strong>👨‍🔧 Ressource:</strong> {ressource}
            </div>
            <div>
                <strong>💰 Coût Estimé:</strong> {cout_estime:.2f}$<br>
                <small style='color:#6b7280;'>({cout_horaire}$/h)</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
def show_footer():
    st.markdown("---")
    st.markdown("""
    <div style='text-align:center;color:var(--text-color-muted);padding:20px 0;font-size:0.9em;'>
        <p>🏭 ERP Production DG Inc.</p>
        <p style='font-style: italic;'>💻 Développé par <strong>Sylvain Leduc</strong> • 2025</p>
    </div>
    """, unsafe_allow_html=True)

# ========================
# FONCTION PRINCIPALE AVEC PORTAIL
# ========================

def main():
    """Fonction principale avec routage des modes - PORTAIL + ERP COMPLET REFACTORISÉ"""

    # NOUVEAU : Charger le CSS externe en priorité
    css_loaded = load_external_css()
    
    # Fallback si CSS externe indisponible
    if not css_loaded:
        apply_fallback_styles()

    # NOUVEAU : Appliquer les styles supplémentaires pour les pièces jointes
    if ATTACHMENTS_AVAILABLE:
        apply_additional_attachments_styles()

    # Initialisation des variables de session - COMPLÈTE
    if 'app_mode' not in st.session_state:
        st.session_state.app_mode = "portal"
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None

    # Initialisation des variables de session (MISES À JOUR)
    session_defs = {
        'show_project_modal': False, 'selected_project': None,
        'show_create_project': False, 'show_edit_project': False,
        'edit_project_data': None, 'show_delete_confirmation': False,
        'delete_project_id': None, 'selected_date': datetime.now().date(),
        'welcome_seen': False,
        'inv_action_mode': "Voir Liste",
        'crm_action': None, 'crm_selected_id': None, 'crm_confirm_delete_contact_id': None,
        'crm_confirm_delete_entreprise_id': None, 'crm_confirm_delete_interaction_id': None,
        'emp_action': None, 'emp_selected_id': None, 'emp_confirm_delete_id': None,
        'competences_form': [],
        'gamme_generated': None, 'gamme_metadata': None,
        'timetracker_employee_id': None, 'timetracker_project_id': None,
        'timetracker_task_id': None, 'timetracker_is_clocked_in': False,
        'timetracker_current_entry_id': None, 'timetracker_view_mode': 'employee',
        'form_action': None,
        'selected_formulaire_id': None,
        'formulaire_filter_type': 'TOUS',
        'formulaire_filter_statut': 'TOUS',
        'show_formulaire_modal': False,
        'formulaire_project_preselect': None,
        'page_redirect': None,
        'fournisseur_action': None,
        'selected_fournisseur_id': None,
        'fournisseur_filter_category': 'TOUS',
        'fournisseur_confirm_delete_id': None,
        'fournisseur_performance_period': 365,
        'navigation_message': None,
        'current_page': None,
        'admin_permissions': [],
        'pointages_temp': [],
        # CHECKPOINT 6 : NOUVELLES VARIABLES TIMETRACKER PRO
        'timetracker_focus_tab': None,
        'timetracker_redirect_to_bt': False,
        # NOUVELLES VARIABLES POUR GESTION PROJETS AMÉLIORÉE
        'batch_action': None,
        'batch_selected_ids': None,
        'show_project_stats': False,
        'project_search_term': '',
        'project_filter_statut': ['Tous'],
        'project_filter_priorite': ['Toutes'],
        'project_sort_by': "ID (Desc)",
        'project_view_mode': "📋 Liste Détaillée"
    }
    for k, v_def in session_defs.items():
        if k not in st.session_state:
            st.session_state[k] = v_def

    # CHECKPOINT 6 : GESTION REDIRECTION TIMETRACKER PRO
    if handle_timetracker_redirect():
        return

    # Gestion des redirections automatiques depuis les modules intégrés
    if st.session_state.get('page_redirect'):
        target_page = st.session_state.page_redirect
        del st.session_state.page_redirect

        if target_page == "timetracker_pro_page":
            st.session_state.current_page = "timetracker_pro"
        elif target_page == "formulaires_page":
            st.session_state.current_page = "formulaires"

        st.rerun()

    # Affichage de notifications de navigation
    if st.session_state.get('navigation_message'):
        st.info(st.session_state.navigation_message)
        del st.session_state.navigation_message

    # Routage selon le mode
    if st.session_state.app_mode == "portal":
        show_portal_home()

    elif st.session_state.app_mode == "employee":
        init_erp_system()  # Initialiser le système pour avoir accès aux modules
        show_employee_interface()

    elif st.session_state.app_mode == "admin_auth":
        show_admin_auth()

    elif st.session_state.app_mode == "erp":
        if check_admin_session():
            show_erp_main()
        else:
            st.error("Session expirée. Veuillez vous reconnecter.")
            st.session_state.app_mode = "admin_auth"
            st.rerun()

    else:
        # Mode par défaut - retour au portail
        st.session_state.app_mode = "portal"
        st.rerun()

    # Sauvegarde périodique automatique
    if st.session_state.get('storage_manager'):
        if hasattr(st.session_state, 'action_counter'):
            st.session_state.action_counter += 1
        else:
            st.session_state.action_counter = 1

        # Sauvegarde automatique toutes les 100 actions
        if st.session_state.action_counter % 100 == 0:
            try:
                backup_path = st.session_state.storage_manager.create_backup("auto")
                if backup_path:
                    st.toast("💾 Sauvegarde automatique effectuée", icon="✅")
            except Exception as e:
                print(f"Erreur sauvegarde automatique: {e}")

if __name__ == "__main__":
    try:
        main()
        if st.session_state.get('admin_authenticated'):
            show_footer()
    except Exception as e_main:
        st.error(f"Une erreur majeure est survenue dans l'application: {str(e_main)}")
        st.info("Veuillez essayer de rafraîchir la page ou de redémarrer l'application.")
        import traceback
        st.code(traceback.format_exc())

        # En cas d'erreur, essayer de créer une sauvegarde d'urgence
        if 'storage_manager' in st.session_state and st.session_state.storage_manager:
            try:
                emergency_backup = st.session_state.storage_manager.create_backup("emergency_error")
                if emergency_backup:
                    st.info(f"💾 Sauvegarde d'urgence créée: {emergency_backup}")
            except Exception:
                pass

print("🎯 CHECKPOINT FINAL - MIGRATION APP.PY TERMINÉE avec NUMÉROTATION MANUELLE")
print("✅ Toutes les modifications appliquées pour TimeTracker Pro Unifié")
print("✅ Gestion des projets complète intégrée avec CRUD + Actions en lot + Recherche avancée")
print("✅ Module Kanban unifié intégré avec fallback")
print("✅ Injection de dépendance CRM avec gestionnaire de projets corrigée")
print("✅ NOUVEAU: Numérotation manuelle pour projets et devis implémentée")
print("🚀 Prêt pour tests et validation complète")
