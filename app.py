# app.py - Version Simplifiée
"""
ERP Production DG Inc. - Application principale
Version modulaire et optimisée
"""

import streamlit as st
from datetime import datetime, date

# Configuration de la page
from config.constants import APP_CONFIG
st.set_page_config(
    page_title=APP_CONFIG["title"],
    page_icon=APP_CONFIG["icon"],
    layout=APP_CONFIG["layout"],
    initial_sidebar_state=APP_CONFIG["sidebar_state"]
)

# Imports des modules
from config.styles import apply_global_styles
from models.projects import GestionnaireProjetIA, migrer_ids_projets, get_project_statistics
from models.work_centers import GestionnairePostes, integrer_postes_dans_projets
from crm import GestionnaireCRM
from employees import GestionnaireEmployes
from utils.formatting import format_currency

# Import des pages
from pages.dashboard import show_dashboard
from pages.projects import show_liste_projets, show_project_modal
from pages.production import (
    show_work_centers_page, 
    show_manufacturing_routes_page, 
    show_capacity_analysis_page
)
from pages.analytics import (
    show_nomenclature, 
    show_itineraire, 
    show_gantt, 
    show_calendrier, 
    show_kanban
)
from pages.inventory import show_inventory_management_page
from pages.crm import show_crm_page
from pages.employees import show_employees_page


def initialize_session_state():
    """Initialise les états de session et gestionnaires"""
    
    # Gestionnaires principaux
    if 'gestionnaire' not in st.session_state:
        st.session_state.gestionnaire = GestionnaireProjetIA()
    
    if 'gestionnaire_crm' not in st.session_state:
        st.session_state.gestionnaire_crm = GestionnaireCRM()
    
    if 'gestionnaire_employes' not in st.session_state:
        st.session_state.gestionnaire_employes = GestionnaireEmployes()
    
    if 'gestionnaire_postes' not in st.session_state:
        st.session_state.gestionnaire_postes = GestionnairePostes()
        # Intégrer les postes dans les projets existants
        if not hasattr(st.session_state, 'postes_integres'):
            st.session_state.gestionnaire = integrer_postes_dans_projets(
                st.session_state.gestionnaire, 
                st.session_state.gestionnaire_postes
            )
            st.session_state.postes_integres = True

    # Migration des IDs de projet si nécessaire
    if 'ids_migres' not in st.session_state:
        gestionnaire = st.session_state.gestionnaire
        if gestionnaire.projets and any(p.get('id', 0) < 10000 for p in gestionnaire.projets):
            nb_migres = migrer_ids_projets(gestionnaire)
            st.success(f"✅ {nb_migres} projet(s) migré(s) vers les nouveaux IDs (10000+)")
            st.session_state.ids_migres = True

    # États de session par défaut
    session_defaults = {
        'show_project_modal': False,
        'selected_project': None,
        'show_create_project': False,
        'show_edit_project': False,
        'edit_project_data': None,
        'show_delete_confirmation': False,
        'delete_project_id': None,
        'selected_date': datetime.now().date(),
        'welcome_seen': False,
        'crm_action': None,
        'crm_selected_id': None,
        'emp_action': None,
        'emp_selected_id': None,
        'gamme_generated': None,
        'gamme_metadata': None
    }
    
    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def render_sidebar():
    """Affiche la barre latérale avec navigation et statistiques"""
    st.sidebar.markdown(
        "<h3 style='text-align:center;color:var(--primary-color-darkest);'>🧭 Navigation</h3>", 
        unsafe_allow_html=True
    )

    # Menu principal
    pages = {
        "🏠 Tableau de Bord": "dashboard",
        "📋 Liste des Projets": "liste",
        "🤝 CRM": "crm_page",
        "👥 Employés": "employees_page",
        "🏭 Postes de Travail": "work_centers_page",
        "⚙️ Gammes Fabrication": "manufacturing_routes",
        "📊 Capacité Production": "capacity_analysis",
        "📦 Gestion Inventaire": "inventory_management",
        "📊 Nomenclature (BOM)": "bom",
        "🛠️ Itinéraire": "routing",
        "📈 Vue Gantt": "gantt",
        "📅 Calendrier": "calendrier",
        "🔄 Kanban": "kanban",
    }
    
    selected_page_key = st.sidebar.radio(
        "Menu Principal:", 
        list(pages.keys()), 
        key="main_nav_radio"
    )
    
    # Statistiques dans la sidebar
    _render_sidebar_stats()
    
    # Footer sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style='background:var(--primary-color-lighter);padding:10px;border-radius:8px;text-align:center;'>
        <p style='color:var(--primary-color-darkest);font-size:12px;margin:0;'>
            🏭 ERP Production DG Inc.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    return pages[selected_page_key]


def _render_sidebar_stats():
    """Affiche les statistiques dans la sidebar"""
    st.sidebar.markdown("---")
    
    # Statistiques des postes de travail
    gestionnaire_postes = st.session_state.gestionnaire_postes
    stats_postes = gestionnaire_postes.get_statistiques_postes()
    
    if stats_postes['total_postes'] > 0:
        st.sidebar.markdown(
            "<h3 style='text-align:center;color:var(--primary-color-darkest);'>🏭 Aperçu Production</h3>", 
            unsafe_allow_html=True
        )
        st.sidebar.metric("Production: Postes Actifs", stats_postes['total_postes'])
        st.sidebar.metric("Production: CNC/Robots", 
                         stats_postes['postes_cnc'] + stats_postes['postes_robotises'])

    # Statistiques projets
    stats_projects = get_project_statistics(st.session_state.gestionnaire)
    if stats_projects['total'] > 0:
        st.sidebar.markdown("---")
        st.sidebar.markdown(
            "<h3 style='text-align:center;color:var(--primary-color-darkest);'>📊 Aperçu Projets</h3>", 
            unsafe_allow_html=True
        )
        st.sidebar.metric("Projets: Total", stats_projects['total'])
        st.sidebar.metric("Projets: Actifs", stats_projects['projets_actifs'])
        if stats_projects['ca_total'] > 0:
            st.sidebar.metric("Projets: CA Estimé", format_currency(stats_projects['ca_total']))

    # Statistiques CRM
    crm_manager = st.session_state.gestionnaire_crm
    if crm_manager.contacts or crm_manager.entreprises:
        st.sidebar.markdown("---")
        st.sidebar.markdown(
            "<h3 style='text-align:center;color:var(--primary-color-darkest);'>📊 Aperçu CRM</h3>", 
            unsafe_allow_html=True
        )
        st.sidebar.metric("CRM: Total Contacts", len(crm_manager.contacts))
        st.sidebar.metric("CRM: Total Entreprises", len(crm_manager.entreprises))

    # Statistiques RH
    emp_manager = st.session_state.gestionnaire_employes
    if emp_manager.employes:
        st.sidebar.markdown("---")
        st.sidebar.markdown(
            "<h3 style='text-align:center;color:var(--primary-color-darkest);'>📊 Aperçu RH</h3>", 
            unsafe_allow_html=True
        )
        st.sidebar.metric("RH: Total Employés", len(emp_manager.employes))
        employes_actifs = len([emp for emp in emp_manager.employes if emp.get('statut') == 'ACTIF'])
        st.sidebar.metric("RH: Employés Actifs", employes_actifs)


def route_to_page(page_name):
    """Route vers la page appropriée"""
    if page_name == "dashboard":
        show_dashboard()
    elif page_name == "liste":
        show_liste_projets()
    elif page_name == "crm_page":
        show_crm_page()
    elif page_name == "employees_page":
        show_employees_page()
    elif page_name == "work_centers_page":
        show_work_centers_page()
    elif page_name == "manufacturing_routes":
        show_manufacturing_routes_page()
    elif page_name == "capacity_analysis":
        show_capacity_analysis_page()
    elif page_name == "inventory_management":
        show_inventory_management_page()
    elif page_name == "bom":
        show_nomenclature()
    elif page_name == "routing":
        show_itineraire()
    elif page_name == "gantt":
        show_gantt()
    elif page_name == "calendrier":
        show_calendrier()
    elif page_name == "kanban":
        show_kanban()


def show_header():
    """Affiche l'en-tête principal"""
    st.markdown("""
    <div class="main-title">
        <h1>🏭 ERP Production DG Inc.</h1>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.welcome_seen:
        st.success("🎉 Bienvenue dans l'ERP Production DG Inc. ! Explorez les 61 postes de travail et les gammes de fabrication.")
        st.session_state.welcome_seen = True


def show_footer():
    """Affiche le pied de page"""
    st.markdown("---")
    st.markdown("""
    <div style='text-align:center;color:var(--text-color-muted);padding:20px 0;font-size:0.9em;'>
        <p>🏭 ERP Production DG Inc. - 61 Postes de Travail • CRM • Inventaire</p>
        <p>Transformé en véritable industrie 4.0</p>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Fonction principale de l'application"""
    try:
        # Initialisation
        initialize_session_state()
        apply_global_styles()
        
        # Interface
        show_header()
        selected_page = render_sidebar()
        route_to_page(selected_page)
        
        # Modals
        if st.session_state.get('show_project_modal'):
            show_project_modal()
        
        # Footer
        show_footer()
        
    except Exception as e:
        st.error(f"Une erreur majeure est survenue dans l'application: {str(e)}")
        st.info("Veuillez essayer de rafraîchir la page ou de redémarrer l'application.")
        
        # Debug en mode développement
        import traceback
        with st.expander("Détails de l'erreur (Debug)", expanded=False):
            st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
