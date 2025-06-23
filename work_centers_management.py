# work_centers_management.py - Gestion des Postes de Travail - DG Inc.
# Interface complète pour la gestion des postes de travail
# Utilise erp_database.py pour toutes les opérations

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class GestionnairePostes:
    """Gestionnaire pour l'interface des postes de travail"""
    
    def __init__(self, db):
        self.db = db
        self.init_session_state()
    
    def init_session_state(self):
        """Initialise les variables de session"""
        if 'wc_action' not in st.session_state:
            st.session_state.wc_action = 'list'  # 'list', 'create', 'edit', 'view'
        if 'wc_selected_id' not in st.session_state:
            st.session_state.wc_selected_id = None
        if 'wc_confirm_delete' not in st.session_state:
            st.session_state.wc_confirm_delete = None
        if 'wc_filter_dept' not in st.session_state:
            st.session_state.wc_filter_dept = 'TOUS'
        if 'wc_filter_cat' not in st.session_state:
            st.session_state.wc_filter_cat = 'TOUS'
        if 'wc_search' not in st.session_state:
            st.session_state.wc_search = ''

def apply_work_centers_styles():
    """Applique les styles pour la gestion des postes"""
    st.markdown("""
    <style>
    /* Variables DG Inc. */
    :root {
        --primary-color: #00A971;
        --primary-color-darker: #00673D;
        --primary-color-darkest: #004C2E;
        --primary-color-lighter: #DCFCE7;
        --background-color: #F9FAFB;
        --card-background: #F0FDF4;
        --text-color: #374151;
        --border-radius-lg: 0.75rem;
        --box-shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    
    .wc-header {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-color-darker) 100%);
        color: white;
        padding: 25px 30px;
        border-radius: 12px;
        margin-bottom: 25px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: var(--box-shadow-md);
    }
    
    .wc-card {
        background: var(--card-background);
        border-radius: var(--border-radius-lg);
        padding: 20px;
        margin: 10px 0;
        box-shadow: var(--box-shadow-md);
        border-left: 4px solid var(--primary-color);
    }
    
    .wc-stats-card {
        background: white;
        border-radius: var(--border-radius-lg);
        padding: 15px;
        text-align: center;
        box-shadow: var(--box-shadow-md);
        border: 1px solid var(--primary-color-lighter);
    }
    
    .wc-status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-block;
    }
    
    .wc-status-actif { background: #d1fae5; color: #065f46; }
    .wc-status-maintenance { background: #fef3c7; color: #92400e; }
    .wc-status-inactif { background: #fee2e2; color: #991b1b; }
    
    .wc-category-badge {
        padding: 3px 8px;
        border-radius: 15px;
        font-size: 11px;
        font-weight: 500;
        display: inline-block;
        margin-right: 5px;
    }
    
    .wc-cat-robotique { background: #e0e7ff; color: #3730a3; }
    .wc-cat-cnc { background: #dbeafe; color: #1e40af; }
    .wc-cat-manuel { background: #d1fae5; color: #065f46; }
    .wc-cat-inspection { background: #fef3c7; color: #92400e; }
    
    .wc-metric-big {
        font-size: 2.5rem;
        font-weight: 800;
        color: var(--primary-color-darker);
        line-height: 1;
    }
    
    .wc-metric-label {
        font-size: 0.875rem;
        color: var(--text-color);
        margin-top: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

def show_work_centers_header():
    """Affiche l'en-tête de la page"""
    st.markdown("""
    <div class="wc-header">
        <div>
            <h2 style="margin: 0; font-size: 1.875rem;">🏭 Gestion des Postes de Travail</h2>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">Interface de gestion complète - DG Inc.</p>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 1.125rem; font-weight: 600;">DG Inc.</div>
            <div style="font-size: 0.875rem; opacity: 0.8;">Production & Métallurgie</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def show_work_centers_navigation():
    """Navigation principale des postes"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📋 Liste des Postes", use_container_width=True, 
                     type="primary" if st.session_state.wc_action == 'list' else "secondary"):
            st.session_state.wc_action = 'list'
            st.session_state.wc_selected_id = None
            st.rerun()
    
    with col2:
        if st.button("➕ Nouveau Poste", use_container_width=True,
                     type="primary" if st.session_state.wc_action == 'create' else "secondary"):
            st.session_state.wc_action = 'create'
            st.session_state.wc_selected_id = None
            st.rerun()
    
    with col3:
        if st.button("📊 Statistiques", use_container_width=True,
                     type="primary" if st.session_state.wc_action == 'stats' else "secondary"):
            st.session_state.wc_action = 'stats'
            st.rerun()
    
    with col4:
        if st.button("📈 Analyses", use_container_width=True,
                     type="primary" if st.session_state.wc_action == 'analysis' else "secondary"):
            st.session_state.wc_action = 'analysis'
            st.rerun()

def show_work_centers_list():
    """Affiche la liste des postes de travail"""
    st.markdown("### 📋 Liste des Postes de Travail")
    
    # Récupérer tous les postes
    try:
        postes = st.session_state.erp_db.execute_query('''
            SELECT wc.*, 
                   COUNT(DISTINCT o.id) as nb_operations,
                   COALESCE(SUM(te.total_hours), 0) as total_heures,
                   COALESCE(SUM(te.total_cost), 0) as total_revenus
            FROM work_centers wc
            LEFT JOIN operations o ON wc.id = o.work_center_id
            LEFT JOIN time_entries te ON o.id = te.operation_id AND te.total_cost IS NOT NULL
            GROUP BY wc.id
            ORDER BY wc.nom
        ''')
        postes = [dict(p) for p in postes]
    except Exception as e:
        st.error(f"Erreur chargement postes: {e}")
        return
    
    if not postes:
        st.info("🏭 Aucun poste de travail configuré. Commencez par créer votre premier poste !")
        if st.button("➕ Créer le premier poste", type="primary"):
            st.session_state.wc_action = 'create'
            st.rerun()
        return
    
    # Filtres
    st.markdown("#### 🔍 Filtres")
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        departements = ['TOUS'] + sorted(list(set(p['departement'] for p in postes if p['departement'])))
        st.session_state.wc_filter_dept = st.selectbox(
            "Département:", departements, 
            index=departements.index(st.session_state.wc_filter_dept) if st.session_state.wc_filter_dept in departements else 0
        )
    
    with filter_col2:
        categories = ['TOUS'] + sorted(list(set(p['categorie'] for p in postes if p['categorie'])))
        st.session_state.wc_filter_cat = st.selectbox(
            "Catégorie:", categories,
            index=categories.index(st.session_state.wc_filter_cat) if st.session_state.wc_filter_cat in categories else 0
        )
    
    with filter_col3:
        st.session_state.wc_search = st.text_input("🔍 Rechercher:", value=st.session_state.wc_search)
    
    # Appliquer filtres
    postes_filtres = postes
    if st.session_state.wc_filter_dept != 'TOUS':
        postes_filtres = [p for p in postes_filtres if p['departement'] == st.session_state.wc_filter_dept]
    if st.session_state.wc_filter_cat != 'TOUS':
        postes_filtres = [p for p in postes_filtres if p['categorie'] == st.session_state.wc_filter_cat]
    if st.session_state.wc_search:
        search_term = st.session_state.wc_search.lower()
        postes_filtres = [p for p in postes_filtres if 
                         search_term in p['nom'].lower() or 
                         search_term in (p['type_machine'] or '').lower()]
    
    st.markdown(f"**{len(postes_filtres)} poste(s) trouvé(s)**")
    
    # Affichage des postes
    for poste in postes_filtres:
        with st.container():
            st.markdown('<div class="wc-card">', unsafe_allow_html=True)
            
            # En-tête du poste
            header_col1, header_col2, header_col3 = st.columns([3, 2, 1])
            
            with header_col1:
                # Nom et type
                st.markdown(f"### 🏭 {poste['nom']}")
                st.markdown(f"**Type:** {poste['type_machine'] or 'N/A'}")
                
                # Badges département et catégorie
                dept_class = f"wc-cat-{poste['categorie'].lower()}" if poste['categorie'] else "wc-cat-manuel"
                st.markdown(f"""
                <span class="wc-category-badge {dept_class}">{poste['departement']}</span>
                <span class="wc-category-badge wc-cat-{poste['categorie'].lower() if poste['categorie'] else 'manuel'}">{poste['categorie']}</span>
                """, unsafe_allow_html=True)
            
            with header_col2:
                # Statut
                statut_class = f"wc-status-{poste['statut'].lower()}" if poste['statut'] else "wc-status-actif"
                st.markdown(f'<span class="wc-status-badge {statut_class}">{poste["statut"]}</span>', unsafe_allow_html=True)
                
                # Capacité et opérateurs
                st.markdown(f"**Capacité:** {poste['capacite_theorique']}h/jour")
                st.markdown(f"**Opérateurs:** {poste['operateurs_requis']}")
                st.markdown(f"**Coût:** {poste['cout_horaire']:.0f}$/h")
            
            with header_col3:
                # Métriques d'utilisation
                st.metric("Opérations", poste['nb_operations'])
                st.metric("Heures", f"{poste['total_heures']:.0f}h")
                st.metric("Revenus", f"{poste['total_revenus']:,.0f}$")
            
            # Compétences requises
            if poste['competences_requises']:
                st.markdown(f"**🎯 Compétences:** {poste['competences_requises']}")
            
            # Localisation
            if poste['localisation']:
                st.markdown(f"**📍 Localisation:** {poste['localisation']}")
            
            # Actions
            action_col1, action_col2, action_col3, action_col4 = st.columns(4)
            
            with action_col1:
                if st.button("👁️ Voir", key=f"view_{poste['id']}", use_container_width=True):
                    st.session_state.wc_action = 'view'
                    st.session_state.wc_selected_id = poste['id']
                    st.rerun()
            
            with action_col2:
                if st.button("✏️ Modifier", key=f"edit_{poste['id']}", use_container_width=True):
                    st.session_state.wc_action = 'edit'
                    st.session_state.wc_selected_id = poste['id']
                    st.rerun()
            
            with action_col3:
                if st.button("📊 Analytics", key=f"analytics_{poste['id']}", use_container_width=True):
                    st.session_state.wc_action = 'view_analytics'
                    st.session_state.wc_selected_id = poste['id']
                    st.rerun()
            
            with action_col4:
                if st.button("🗑️ Supprimer", key=f"delete_{poste['id']}", type="secondary", use_container_width=True):
                    st.session_state.wc_confirm_delete = poste['id']
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Confirmation de suppression
    if st.session_state.wc_confirm_delete:
        show_delete_confirmation(st.session_state.wc_confirm_delete)

def show_work_center_form(poste_data=None):
    """Formulaire d'ajout/modification de poste"""
    is_edit = poste_data is not None
    title = "✏️ Modifier Poste" if is_edit else "➕ Nouveau Poste"
    
    st.markdown(f"### {title}")
    
    with st.form("work_center_form"):
        # Informations de base
        st.markdown("#### 📋 Informations Générales")
        
        col1, col2 = st.columns(2)
        
        with col1:
            nom = st.text_input(
                "Nom du poste *:", 
                value=poste_data.get('nom', '') if is_edit else '',
                placeholder="Ex: Robot ABB GMAW Station 1"
            )
            
            departements = ['PRODUCTION', 'USINAGE', 'QUALITE', 'LOGISTIQUE', 'MAINTENANCE', 'COMMERCIAL']
            dept_index = departements.index(poste_data['departement']) if is_edit and poste_data.get('departement') in departements else 0
            departement = st.selectbox("Département *:", departements, index=dept_index)
            
            categories = ['ROBOTIQUE', 'CNC', 'MANUEL', 'INSPECTION', 'ASSEMBLAGE', 'FINITION', 'TRANSPORT']
            cat_index = categories.index(poste_data['categorie']) if is_edit and poste_data.get('categorie') in categories else 0
            categorie = st.selectbox("Catégorie *:", categories, index=cat_index)
        
        with col2:
            type_machine = st.text_input(
                "Type de machine:", 
                value=poste_data.get('type_machine', '') if is_edit else '',
                placeholder="Ex: Robot de soudage 6 axes"
            )
            
            capacite_theorique = st.number_input(
                "Capacité théorique (h/jour):", 
                value=float(poste_data.get('capacite_theorique', 8.0)) if is_edit else 8.0,
                min_value=0.1, max_value=24.0, step=0.5
            )
            
            operateurs_requis = st.number_input(
                "Opérateurs requis:", 
                value=int(poste_data.get('operateurs_requis', 1)) if is_edit else 1,
                min_value=1, max_value=10, step=1
            )
        
        # Coûts et statut
        st.markdown("#### 💰 Coûts et Statut")
        
        col3, col4 = st.columns(2)
        
        with col3:
            cout_horaire = st.number_input(
                "Coût horaire ($):", 
                value=float(poste_data.get('cout_horaire', 50.0)) if is_edit else 50.0,
                min_value=0.0, step=5.0
            )
            
            statuts = ['ACTIF', 'MAINTENANCE', 'INACTIF']
            statut_index = statuts.index(poste_data['statut']) if is_edit and poste_data.get('statut') in statuts else 0
            statut = st.selectbox("Statut:", statuts, index=statut_index)
        
        with col4:
            localisation = st.text_input(
                "Localisation:", 
                value=poste_data.get('localisation', '') if is_edit else '',
                placeholder="Ex: Atelier A - Zone 2"
            )
        
        # Compétences
        st.markdown("#### 🎯 Compétences Requises")
        competences_requises = st.text_area(
            "Compétences requises:", 
            value=poste_data.get('competences_requises', '') if is_edit else '',
            placeholder="Ex: Soudage GMAW, Programmation Robot ABB, Lecture de plans",
            height=100
        )
        
        # Boutons
        col_submit, col_cancel = st.columns(2)
        
        with col_submit:
            submitted = st.form_submit_button(
                "💾 Sauvegarder" if is_edit else "➕ Créer Poste", 
                use_container_width=True, type="primary"
            )
        
        with col_cancel:
            cancelled = st.form_submit_button("❌ Annuler", use_container_width=True)
        
        if submitted:
            # Validation
            if not nom:
                st.error("❌ Le nom du poste est obligatoire")
                return
            
            if not departement:
                st.error("❌ Le département est obligatoire")
                return
            
            # Données du poste
            work_center_data = {
                'nom': nom,
                'departement': departement,
                'categorie': categorie,
                'type_machine': type_machine,
                'capacite_theorique': capacite_theorique,
                'operateurs_requis': operateurs_requis,
                'cout_horaire': cout_horaire,
                'competences_requises': competences_requises,
                'statut': statut,
                'localisation': localisation
            }
            
            try:
                if is_edit:
                    # Modification
                    success = st.session_state.erp_db.update_work_center(
                        st.session_state.wc_selected_id, 
                        work_center_data
                    )
                    if success:
                        st.success(f"✅ Poste {nom} modifié avec succès !")
                        st.session_state.wc_action = 'list'
                        st.session_state.wc_selected_id = None
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la modification")
                else:
                    # Création
                    poste_id = st.session_state.erp_db.add_work_center(work_center_data)
                    if poste_id:
                        st.success(f"✅ Poste {nom} créé avec succès ! ID: {poste_id}")
                        st.session_state.wc_action = 'list'
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la création")
                        
            except Exception as e:
                st.error(f"❌ Erreur: {e}")
        
        if cancelled:
            st.session_state.wc_action = 'list'
            st.session_state.wc_selected_id = None
            st.rerun()

def show_work_center_details(poste_id):
    """Affiche les détails d'un poste"""
    try:
        poste = st.session_state.erp_db.get_work_center_by_id(poste_id)
        if not poste:
            st.error("❌ Poste non trouvé")
            return
        
        st.markdown(f"### 👁️ Détails - {poste['nom']}")
        
        # Informations générales
        st.markdown('<div class="wc-card">', unsafe_allow_html=True)
        
        detail_col1, detail_col2, detail_col3 = st.columns(3)
        
        with detail_col1:
            st.markdown("#### 📋 Informations")
            st.markdown(f"**Nom:** {poste['nom']}")
            st.markdown(f"**Département:** {poste['departement']}")
            st.markdown(f"**Catégorie:** {poste['categorie']}")
            st.markdown(f"**Type:** {poste.get('type_machine', 'N/A')}")
            st.markdown(f"**Localisation:** {poste.get('localisation', 'N/A')}")
        
        with detail_col2:
            st.markdown("#### ⚙️ Capacités")
            st.markdown(f"**Capacité:** {poste['capacite_theorique']}h/jour")
            st.markdown(f"**Opérateurs:** {poste['operateurs_requis']}")
            st.markdown(f"**Coût horaire:** {poste['cout_horaire']:.0f}$/h")
            
            statut_class = f"wc-status-{poste['statut'].lower()}"
            st.markdown(f"**Statut:** <span class='wc-status-badge {statut_class}'>{poste['statut']}</span>", unsafe_allow_html=True)
        
        with detail_col3:
            st.markdown("#### 📊 Utilisation")
            st.markdown(f"**Opérations:** {poste.get('operations_count', 0)}")
            st.markdown(f"**Heures totales:** {poste.get('total_hours_tracked', 0):.0f}h")
            st.markdown(f"**Revenus générés:** {poste.get('total_revenue_generated', 0):,.0f}$")
            st.markdown(f"**Employés uniques:** {poste.get('unique_employees_used', 0)}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Compétences
        if poste.get('competences_requises'):
            st.markdown("#### 🎯 Compétences Requises")
            st.info(poste['competences_requises'])
        
        # Actions
        action_col1, action_col2 = st.columns(2)
        
        with action_col1:
            if st.button("✏️ Modifier ce poste", use_container_width=True, type="primary"):
                st.session_state.wc_action = 'edit'
                st.rerun()
        
        with action_col2:
            if st.button("📋 Retour à la liste", use_container_width=True):
                st.session_state.wc_action = 'list'
                st.session_state.wc_selected_id = None
                st.rerun()
        
    except Exception as e:
        st.error(f"❌ Erreur chargement détails: {e}")

def show_work_centers_statistics():
    """Affiche les statistiques des postes de travail"""
    st.markdown("### 📊 Statistiques des Postes de Travail")
    
    try:
        stats = st.session_state.erp_db.get_work_centers_statistics()
        
        if not stats or stats.get('total_work_centers', 0) == 0:
            st.info("📊 Aucune donnée statistique disponible")
            return
        
        # Métriques principales
        st.markdown("#### 🎯 Vue d'Ensemble")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="wc-stats-card">', unsafe_allow_html=True)
            st.markdown('<div class="wc-metric-big">🏭</div>', unsafe_allow_html=True)
            st.metric("Total Postes", stats.get('total_work_centers', 0))
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="wc-stats-card">', unsafe_allow_html=True)
            st.markdown('<div class="wc-metric-big">⚡</div>', unsafe_allow_html=True)
            actifs = stats.get('by_status', {}).get('ACTIF', 0)
            st.metric("Postes Actifs", actifs)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="wc-stats-card">', unsafe_allow_html=True)
            st.markdown('<div class="wc-metric-big">🕐</div>', unsafe_allow_html=True)
            capacite = stats.get('capacity_analysis', {}).get('capacite_totale_heures_jour', 0)
            st.metric("Capacité Totale", f"{capacite:.0f}h/j")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="wc-stats-card">', unsafe_allow_html=True)
            st.markdown('<div class="wc-metric-big">💰</div>', unsafe_allow_html=True)
            cout_total = stats.get('capacity_analysis', {}).get('cout_total_theorique_jour', 0)
            st.metric("Coût Théorique", f"{cout_total:,.0f}$/j")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Graphiques
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Répartition par département
            dept_data = stats.get('by_department', {})
            if dept_data:
                dept_names = list(dept_data.keys())
                dept_counts = [dept_data[dept]['count'] for dept in dept_names]
                
                fig_dept = px.pie(
                    values=dept_counts,
                    names=dept_names,
                    title="📊 Répartition par Département",
                    color_discrete_sequence=['#00A971', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']
                )
                fig_dept.update_layout(height=400)
                st.plotly_chart(fig_dept, use_container_width=True)
        
        with chart_col2:
            # Répartition par catégorie
            cat_data = stats.get('by_category', {})
            if cat_data:
                cat_names = list(cat_data.keys())
                cat_counts = [cat_data[cat]['count'] for cat in cat_names]
                
                fig_cat = px.bar(
                    x=cat_names,
                    y=cat_counts,
                    title="📈 Répartition par Catégorie",
                    color=cat_names,
                    color_discrete_sequence=['#00A971', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']
                )
                fig_cat.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_cat, use_container_width=True)
        
        # Intégration TimeTracker
        tt_stats = stats.get('timetracker_integration', {})
        if tt_stats and tt_stats.get('total_pointages', 0) > 0:
            st.markdown("#### ⏱️ Intégration TimeTracker")
            
            tt_col1, tt_col2, tt_col3, tt_col4 = st.columns(4)
            
            with tt_col1:
                st.metric("Postes avec pointages", tt_stats.get('postes_avec_pointages', 0))
            with tt_col2:
                st.metric("Total pointages", tt_stats.get('total_pointages', 0))
            with tt_col3:
                st.metric("Heures totales", f"{tt_stats.get('total_heures', 0):.0f}h")
            with tt_col4:
                st.metric("Employés distincts", tt_stats.get('employes_ayant_pointe', 0))
        
    except Exception as e:
        st.error(f"❌ Erreur statistiques: {e}")

def show_work_centers_analysis():
    """Analyse avancée des postes de travail"""
    st.markdown("### 📈 Analyses Avancées")
    
    analysis_tab1, analysis_tab2 = st.tabs(["🔍 Analyse d'Utilisation", "⚠️ Goulots d'Étranglement"])
    
    with analysis_tab1:
        show_utilization_analysis()
    
    with analysis_tab2:
        show_bottleneck_analysis()

def show_utilization_analysis():
    """Analyse d'utilisation des postes"""
    st.markdown("#### 🔍 Analyse d'Utilisation")
    
    # Sélection de période
    period_days = st.selectbox("📅 Période d'analyse:", [7, 14, 30, 90], index=2)
    
    try:
        analysis = st.session_state.erp_db.get_work_center_utilization_analysis(period_days)
        
        if not analysis:
            st.info("📊 Aucune donnée d'utilisation disponible")
            return
        
        # Tableau d'analyse
        df_data = []
        for wc in analysis:
            df_data.append({
                'Poste': wc['nom'],
                'Département': wc['departement'],
                'Catégorie': wc['categorie'],
                'Capacité (h/j)': wc['capacite_theorique'],
                'Heures Réelles': f"{wc['heures_reelles']:.1f}h",
                'Utilisation %': f"{wc['taux_utilisation_pct']:.1f}%",
                'Classification': wc['classification_utilisation'],
                'Revenus': f"{wc['revenus_generes']:,.0f}$",
                'Employés': wc['employes_distincts'],
                'Projets': wc['projets_touches']
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Graphique d'utilisation
            fig_util = px.bar(
                df, 
                x='Poste', 
                y='Utilisation %',
                color='Classification',
                title=f"Taux d'Utilisation des Postes ({period_days} derniers jours)",
                color_discrete_map={
                    'TRÈS_FAIBLE': '#ef4444',
                    'FAIBLE': '#f59e0b', 
                    'MOYENNE': '#3b82f6',
                    'ÉLEVÉE': '#10b981'
                }
            )
            fig_util.update_layout(height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig_util, use_container_width=True)
    
    except Exception as e:
        st.error(f"❌ Erreur analyse utilisation: {e}")

def show_bottleneck_analysis():
    """Analyse des goulots d'étranglement"""
    st.markdown("#### ⚠️ Goulots d'Étranglement")
    
    try:
        bottlenecks = st.session_state.erp_db.get_work_center_capacity_bottlenecks()
        
        if not bottlenecks:
            st.success("✅ Aucun goulot d'étranglement détecté ! Votre production est bien équilibrée.")
            return
        
        # Affichage des goulots
        for bottleneck in bottlenecks:
            level = bottleneck['niveau_goulot']
            
            # Couleur selon le niveau
            if level == 'CRITIQUE':
                alert_type = 'error'
                icon = '🚨'
            elif level == 'ÉLEVÉ':
                alert_type = 'warning'
                icon = '⚠️'
            else:
                alert_type = 'info'
                icon = '📊'
            
            with st.container():
                if alert_type == 'error':
                    st.error(f"""
                    {icon} **GOULOT CRITIQUE** - {bottleneck['nom']}
                    
                    - **Charge:** {bottleneck['taux_charge_planifiee_pct']:.1f}% 
                    - **Opérations en attente:** {bottleneck['operations_en_attente']}
                    - **Pointages actifs:** {bottleneck['pointages_actifs']}
                    - **Département:** {bottleneck['departement']}
                    """)
                elif alert_type == 'warning':
                    st.warning(f"""
                    {icon} **GOULOT ÉLEVÉ** - {bottleneck['nom']}
                    
                    - **Charge:** {bottleneck['taux_charge_planifiee_pct']:.1f}%
                    - **Opérations en attente:** {bottleneck['operations_en_attente']}
                    - **Département:** {bottleneck['departement']}
                    """)
                else:
                    st.info(f"""
                    {icon} **Charge Modérée** - {bottleneck['nom']}
                    
                    - **Charge:** {bottleneck['taux_charge_planifiee_pct']:.1f}%
                    - **Département:** {bottleneck['departement']}
                    """)
                
                # Recommandations
                if bottleneck.get('recommandations'):
                    st.markdown("**🎯 Recommandations:**")
                    for rec in bottleneck['recommandations']:
                        st.markdown(f"- {rec}")
        
        # Graphique des charges
        if bottlenecks:
            bottleneck_names = [b['nom'] for b in bottlenecks]
            bottleneck_charges = [b['taux_charge_planifiee_pct'] for b in bottlenecks]
            bottleneck_levels = [b['niveau_goulot'] for b in bottlenecks]
            
            fig_bottleneck = px.bar(
                x=bottleneck_names,
                y=bottleneck_charges,
                color=bottleneck_levels,
                title="📊 Analyse des Goulots d'Étranglement",
                labels={'x': 'Postes', 'y': 'Charge (%)'},
                color_discrete_map={
                    'CRITIQUE': '#ef4444',
                    'ÉLEVÉ': '#f59e0b',
                    'MODÉRÉ': '#3b82f6',
                    'FAIBLE': '#10b981'
                }
            )
            fig_bottleneck.add_hline(y=100, line_dash="dash", line_color="red", 
                                   annotation_text="Capacité Maximum")
            fig_bottleneck.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_bottleneck, use_container_width=True)
    
    except Exception as e:
        st.error(f"❌ Erreur analyse goulots: {e}")

def show_delete_confirmation(poste_id):
    """Confirmation de suppression"""
    try:
        poste = st.session_state.erp_db.get_work_center_by_id(poste_id)
        if not poste:
            st.session_state.wc_confirm_delete = None
            return
        
        st.error(f"""
        ⚠️ **CONFIRMATION DE SUPPRESSION**
        
        Êtes-vous sûr de vouloir supprimer le poste **{poste['nom']}** ?
        
        Cette action est **irréversible** et supprimera :
        - Le poste de travail
        - Toutes les opérations associées
        - Toutes les réservations
        
        **⚠️ ATTENTION :** Cette action peut affecter vos projets en cours !
        """)
        
        col_confirm, col_cancel = st.columns(2)
        
        with col_confirm:
            if st.button("🗑️ CONFIRMER LA SUPPRESSION", type="primary", use_container_width=True):
                try:
                    if st.session_state.erp_db.delete_work_center(poste_id):
                        st.success(f"✅ Poste {poste['nom']} supprimé avec succès !")
                        st.session_state.wc_confirm_delete = None
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la suppression")
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
        
        with col_cancel:
            if st.button("❌ Annuler", use_container_width=True):
                st.session_state.wc_confirm_delete = None
                st.rerun()
    
    except Exception as e:
        st.error(f"❌ Erreur: {e}")

def show_work_centers_page():
    """Page principale de gestion des postes de travail"""
    
    # Vérifier la disponibilité de la base
    if 'erp_db' not in st.session_state:
        st.error("❌ Base de données ERP non disponible")
        return
    
    # Initialiser le gestionnaire
    if 'gestionnaire_postes' not in st.session_state:
        st.session_state.gestionnaire_postes = GestionnairePostes(st.session_state.erp_db)
    
    # Appliquer les styles
    apply_work_centers_styles()
    
    # En-tête
    show_work_centers_header()
    
    # Navigation
    show_work_centers_navigation()
    
    # Contenu selon l'action
    action = st.session_state.get('wc_action', 'list')
    
    if action == 'list':
        show_work_centers_list()
    
    elif action == 'create':
        show_work_center_form()
    
    elif action == 'edit':
        if st.session_state.wc_selected_id:
            try:
                poste_data = st.session_state.erp_db.get_work_center_by_id(st.session_state.wc_selected_id)
                if poste_data:
                    show_work_center_form(poste_data)
                else:
                    st.error("❌ Poste non trouvé")
                    st.session_state.wc_action = 'list'
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Erreur: {e}")
                st.session_state.wc_action = 'list'
        else:
            st.session_state.wc_action = 'list'
            st.rerun()
    
    elif action == 'view':
        if st.session_state.wc_selected_id:
            show_work_center_details(st.session_state.wc_selected_id)
        else:
            st.session_state.wc_action = 'list'
            st.rerun()
    
    elif action == 'stats':
        show_work_centers_statistics()
    
    elif action == 'analysis':
        show_work_centers_analysis()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align:center;color:var(--text-color);padding:20px 0;'>
        <p><strong>🏭 Gestion des Postes de Travail</strong> - DG Inc. Production</p>
        <p>Interface complète pour la gestion de votre parc machine</p>
    </div>
    """, unsafe_allow_html=True)

# Point d'entrée principal
if __name__ == "__main__":
    show_work_centers_page()
