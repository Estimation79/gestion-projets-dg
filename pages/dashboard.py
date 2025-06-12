# pages/dashboard.py
"""
Page tableau de bord pour l'ERP Production DG Inc.
"""

import streamlit as st
import plotly.express as px
from datetime import datetime
from models.projects import get_project_statistics
from utils.formatting import format_currency
from config.constants import COLORS
import random


def show_dashboard():
    """Affiche le tableau de bord principal"""
    st.markdown("## 📊 Tableau de Bord ERP Production")
    
    # Récupération des gestionnaires
    gestionnaire = st.session_state.gestionnaire
    gestionnaire_employes = st.session_state.gestionnaire_employes
    gestionnaire_postes = st.session_state.gestionnaire_postes
    
    # Calcul des statistiques
    stats = get_project_statistics(gestionnaire)
    emp_stats = gestionnaire_employes.get_statistiques_employes()
    postes_stats = gestionnaire_postes.get_statistiques_postes()
    
    # Message de bienvenue si aucune donnée
    if stats['total'] == 0 and emp_stats.get('total', 0) == 0:
        _render_welcome_message()
        return

    # Métriques principales
    _render_project_metrics(stats)
    _render_production_metrics(postes_stats)
    _render_hr_metrics(emp_stats, gestionnaire_employes)
    
    # Graphiques
    _render_charts(stats, postes_stats)
    
    # Projets récents
    _render_recent_projects(gestionnaire)


def _render_welcome_message():
    """Affiche le message de bienvenue"""
    st.markdown("""
    <div class='info-card' style='text-align:center;padding:3rem;'>
        <h3>🏭 Bienvenue dans l'ERP Production DG Inc. !</h3>
        <p>Créez votre premier projet, explorez les postes de travail ou consultez les gammes de fabrication.</p>
    </div>
    """, unsafe_allow_html=True)


def _render_project_metrics(stats):
    """Affiche les métriques des projets"""
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


def _render_production_metrics(postes_stats):
    """Affiche les métriques de production"""
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


def _render_hr_metrics(emp_stats, gestionnaire_employes):
    """Affiche les métriques RH"""
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


def _render_charts(stats, postes_stats):
    """Affiche les graphiques du tableau de bord"""
    st.markdown("<br>", unsafe_allow_html=True)
    
    if stats['total'] > 0 or postes_stats['total_postes'] > 0:
        gc1, gc2 = st.columns(2)
        
        with gc1:
            _render_projects_status_chart(stats)
        
        with gc2:
            _render_work_centers_chart(postes_stats)


def _render_projects_status_chart(stats):
    """Graphique des projets par statut"""
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    if stats['par_statut']:
        fig = px.pie(
            values=list(stats['par_statut'].values()), 
            names=list(stats['par_statut'].keys()), 
            title="📈 Projets par Statut", 
            color_discrete_map=COLORS['statut']
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)', 
            font=dict(color='var(--text-color)'), 
            legend_title_text='', 
            title_x=0.5
        )
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_work_centers_chart(postes_stats):
    """Graphique des postes par département"""
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    if postes_stats.get('par_departement'):
        fig = px.bar(
            x=list(postes_stats['par_departement'].keys()), 
            y=list(postes_stats['par_departement'].values()), 
            title="🏭 Postes par Département", 
            color=list(postes_stats['par_departement'].keys()), 
            color_discrete_map=COLORS['departement']
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)', 
            font=dict(color='var(--text-color)'), 
            showlegend=False, 
            title_x=0.5
        )
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_recent_projects(gestionnaire):
    """Affiche les projets récents"""
    st.markdown("---")
    st.markdown("### 🕒 Projets Récents")
    
    crm_manager = st.session_state.gestionnaire_crm
    projets_recents = sorted(gestionnaire.projets, key=lambda x: x.get('id', 0), reverse=True)[:5]
    
    if not projets_recents:
        st.info("Aucun projet récent.")
        return
    
    for p in projets_recents:
        _render_project_card(p, crm_manager)


def _render_project_card(projet, crm_manager):
    """Affiche une carte de projet"""
    st.markdown("<div class='info-card'>", unsafe_allow_html=True)
    
    rc1, rc2, rc3, rc4 = st.columns([3, 2, 2, 1])
    
    with rc1:
        st.markdown(f"**#{projet.get('id')} - {projet.get('nom_projet', 'Sans nom')}**")
        st.caption(f"📝 {projet.get('description', 'N/A')[:100]}...")
    
    with rc2:
        client_display_name = _get_client_display_name(projet, crm_manager)
        st.markdown(f"👤 **{client_display_name}**")
        st.caption(f"💰 {format_currency(projet.get('prix_estime', 0))}")
    
    with rc3:
        _render_project_status_priority(projet)
    
    with rc4:
        if st.button("👁️", key=f"view_rec_{projet.get('id')}", help="Voir détails"):
            st.session_state.selected_project = projet
            st.session_state.show_project_modal = True
    
    st.markdown("</div>", unsafe_allow_html=True)


def _get_client_display_name(projet, crm_manager):
    """Récupère le nom d'affichage du client"""
    client_display_name = projet.get('client_nom_cache', 'N/A')
    
    if client_display_name == 'N/A' and projet.get('client_entreprise_id'):
        entreprise = crm_manager.get_entreprise_by_id(projet.get('client_entreprise_id'))
        if entreprise:
            client_display_name = entreprise.get('nom', 'N/A')
    elif client_display_name == 'N/A':
        client_display_name = projet.get('client', 'N/A')
    
    return client_display_name


def _render_project_status_priority(projet):
    """Affiche le statut et la priorité d'un projet"""
    statut, priorite = projet.get('statut', 'N/A'), projet.get('priorite', 'N/A')
    
    statut_map = {
        'À FAIRE': '🟡', 
        'EN COURS': '🔵', 
        'EN ATTENTE': '🔴', 
        'TERMINÉ': '🟢', 
        'ANNULÉ': '⚫', 
        'LIVRAISON': '🟣'
    }
    priorite_map = {
        'ÉLEVÉ': '🔴', 
        'MOYEN': '🟡', 
        'BAS': '🟢'
    }
    
    st.markdown(f"{statut_map.get(statut, '⚪')} {statut}")
    st.caption(f"{priorite_map.get(priorite, '⚪')} {priorite}")
