# formulaires/bons_travail/interface_bt.py
# Interface utilisateur pour les Bons de Travail - VERSION COMPLÈTE FINALE

"""
Interface utilisateur pour les Bons de Travail - Style DG Inc.
VERSION COMPLÈTE FINALE : Utilise les vraies données de la base SQLite
Contient tous les composants d'affichage et d'interaction pour les BT.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from .gestionnaire_bt import GestionnaireBonsTravail
from ..utils.helpers import (
    get_projets_actifs,
    get_employes_actifs,
    get_operations_projet,
    get_materiaux_projet,
    get_work_centers_actifs,
    formater_montant,
    formater_delai,
    generer_couleur_statut,
    generer_couleur_priorite
)
from ..core.types_formulaires import UNITES_MESURE


def apply_dg_style():
    """
    Applique le style DG Inc. professionnel fidèle au HTML
    """
    st.markdown("""
    <style>
    /* Variables de couleur DG Inc. - Fidèles au HTML */
    :root {
        --primary-color: #00A971;
        --primary-color-darker: #00673D;
        --primary-color-darkest: #004C2E;
        --background-color: #F9FAFB;
        --secondary-background-color: #FFFFFF;
        --text-color: #374151;
        --text-color-light: #6B7280;
        --border-color: #E5E7EB;
        --border-color-light: #F3F4F6;
        --border-radius-sm: 0.375rem;
        --border-radius-md: 0.5rem;
        --box-shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
        --box-shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        --animation-speed: 0.3s;
        --success-color: #10b981;
        --warning-color: #f59e0b;
        --error-color: #ef4444;
    }

    /* Header DG Inc. - Identique au HTML */
    .dg-header {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-color-darker) 100%);
        color: white;
        padding: 25px 30px;
        border-radius: 12px 12px 0 0;
        margin-bottom: 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 3px solid var(--primary-color-darkest);
        box-shadow: var(--box-shadow-md);
    }

    .dg-logo-container {
        display: flex;
        align-items: center;
        gap: 15px;
    }

    .dg-logo-box {
        background-color: white;
        width: 60px;
        height: 40px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .dg-logo-text {
        font-weight: 800;
        font-size: 20px;
        color: var(--primary-color);
        letter-spacing: 1px;
        margin: 0;
    }

    .dg-company-name {
        font-weight: 600;
        font-size: 24px;
        color: white;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        margin: 0;
    }

    .dg-contact {
        text-align: right;
        color: rgba(255, 255, 255, 0.95);
        font-size: 14px;
        line-height: 1.4;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }

    .dg-contact p {
        margin: 0;
        line-height: 1.3;
    }

    /* Section cards - Style DG */
    .dg-section-card {
        background: var(--secondary-background-color);
        border-radius: var(--border-radius-md);
        box-shadow: var(--box-shadow-md);
        margin: 20px 0;
        overflow: hidden;
        border: 1px solid var(--border-color);
        animation: fadeIn 0.6s ease-out;
    }

    .dg-info-section {
        background: linear-gradient(to right, #e6f7f1, #ffffff);
        padding: 20px;
        border-left: 5px solid var(--primary-color);
        margin: 20px 0;
        border-radius: var(--border-radius-md);
        box-shadow: var(--box-shadow-sm);
    }

    .dg-info-title {
        color: var(--primary-color-darker);
        margin: 0 0 15px 0;
        font-size: 20px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Tableaux DG style - Fidèles au HTML */
    .dg-table-container {
        background: white;
        border-radius: var(--border-radius-md);
        overflow: hidden;
        box-shadow: var(--box-shadow-sm);
        border: 1px solid var(--border-color);
        margin: 15px 0;
    }

    .dg-table-header {
        background: linear-gradient(135deg, #e6f7f1 0%, #d0f0e6 100%);
        color: var(--primary-color-darker);
        font-weight: 600;
        padding: 12px;
        border-bottom: 2px solid var(--primary-color);
    }

    .dg-table-row {
        padding: 12px;
        border-bottom: 1px solid var(--border-color-light);
        transition: background-color var(--animation-speed);
    }

    .dg-table-row:hover {
        background-color: #e6f7f1;
    }

    .dg-table-row:nth-child(even) {
        background-color: #f8f9fa;
    }

    /* Grille de formulaire */
    .dg-form-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 15px;
        margin: 15px 0;
    }

    .dg-form-field {
        display: flex;
        flex-direction: column;
        gap: 5px;
    }

    .dg-form-field label {
        font-weight: 500;
        color: var(--text-color);
        font-size: 14px;
    }

    /* Boutons DG style - Identiques au HTML */
    .dg-btn-primary {
        background: linear-gradient(90deg, var(--primary-color) 0%, var(--primary-color-darker) 100%);
        color: white !important;
        border: none;
        padding: 12px 24px;
        border-radius: var(--border-radius-md);
        font-weight: 600;
        cursor: pointer;
        transition: all var(--animation-speed);
        box-shadow: var(--box-shadow-sm);
        text-decoration: none;
    }

    .dg-btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: var(--box-shadow-md);
    }

    .dg-btn-secondary {
        background: linear-gradient(90deg, #60a5fa 0%, #3b82f6 100%);
        color: white !important;
        border: none;
        padding: 12px 24px;
        border-radius: var(--border-radius-md);
        font-weight: 600;
        cursor: pointer;
        transition: all var(--animation-speed);
        box-shadow: var(--box-shadow-sm);
    }

    .dg-btn-success {
        background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%);
        color: white !important;
        border: none;
        padding: 12px 24px;
        border-radius: var(--border-radius-md);
        font-weight: 600;
        cursor: pointer;
        transition: all var(--animation-speed);
        box-shadow: var(--box-shadow-sm);
    }

    .dg-btn-danger {
        background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);
        color: white !important;
        border: none;
        padding: 12px 24px;
        border-radius: var(--border-radius-md);
        font-weight: 600;
        cursor: pointer;
        transition: all var(--animation-speed);
        box-shadow: var(--box-shadow-sm);
    }

    /* Status badges - Identiques au HTML */
    .dg-status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-block;
    }

    .status-draft { background: #fef3c7; color: #92400e; }
    .status-pending { background: #dbeafe; color: #1e40af; }
    .status-approved { background: #d1fae5; color: #065f46; }
    .status-in-progress { background: #e0e7ff; color: #3730a3; }
    .status-completed { background: #d1fae5; color: #065f46; }
    .status-cancelled { background: #fee2e2; color: #991b1b; }

    /* Footer DG - Identique au HTML */
    .dg-footer {
        background: linear-gradient(135deg, #f3f4f6 0%, #ffffff 100%);
        padding: 20px;
        border-top: 1px solid var(--border-color);
        border-radius: 0 0 12px 12px;
        margin-top: 20px;
    }

    .dg-footer p {
        margin: 8px 0;
        color: var(--text-color);
        font-size: 14px;
    }

    /* Métriques DG style */
    .dg-metric {
        background: white;
        padding: 20px;
        border-radius: var(--border-radius-md);
        box-shadow: var(--box-shadow-sm);
        border: 1px solid var(--border-color);
        text-align: center;
        transition: all var(--animation-speed);
    }

    .dg-metric:hover {
        transform: translateY(-2px);
        box-shadow: var(--box-shadow-md);
    }

    .dg-metric-value {
        font-size: 24px;
        font-weight: 700;
        color: var(--primary-color-darker);
        margin: 0;
    }

    .dg-metric-label {
        font-size: 14px;
        color: var(--text-color-light);
        margin: 5px 0 0 0;
    }

    /* Couleurs priorité - Identiques au HTML */
    .priority-high { border-left: 4px solid #ef4444; }
    .priority-medium { border-left: 4px solid #f59e0b; }
    .priority-low { border-left: 4px solid #10b981; }
    .priority-critical { border-left: 4px solid #dc2626; }

    /* Conteneur principal DG */
    .dg-main-container {
        border: 1px solid #bbb;
        margin-bottom: 40px;
        padding: 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        border-radius: 12px;
        overflow: hidden;
        background: white;
    }

    /* Titre de section */
    .dg-section-title {
        background-color: var(--primary-color-darkest);
        color: white;
        padding: 15px 20px;
        margin: 0;
        text-align: center;
        font-size: 1.5em;
        border-bottom: 1px solid var(--primary-color-darkest);
    }

    /* Contenu principal */
    .dg-main-content {
        padding: 30px;
    }

    /* Contrôles de formulaire */
    .dg-form-controls {
        padding: 20px 30px;
        text-align: center;
        background: linear-gradient(135deg, #f3f4f6 0%, #ffffff 100%);
        border-top: 1px solid var(--border-color);
    }

    /* Progress bar style DG */
    .dg-progress {
        background-color: #e5e7eb;
        border-radius: 10px;
        overflow: hidden;
        height: 20px;
        margin: 5px 0;
    }

    .dg-progress-bar {
        background: linear-gradient(90deg, var(--primary-color) 0%, var(--success-color) 100%);
        height: 100%;
        transition: width var(--animation-speed);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 12px;
        font-weight: 600;
    }

    /* Tableau style DG */
    .dg-table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        background: white;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .dg-table th {
        background: linear-gradient(135deg, #e6f7f1 0%, #d0f0e6 100%);
        color: var(--primary-color-darker);
        font-weight: 600;
        padding: 12px 8px;
        text-align: left;
        border-bottom: 2px solid var(--primary-color);
    }

    .dg-table td {
        padding: 10px 8px;
        border-bottom: 1px solid #e5e7eb;
        vertical-align: top;
    }

    .dg-table tbody tr:nth-child(even) {
        background-color: #f8f9fa;
    }

    .dg-table tbody tr:hover {
        background-color: #e6f7f1;
    }

    /* Status badges */
    .status-badge {
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        display: inline-block;
    }

    .status-a-faire { background: #fef3c7; color: #92400e; }
    .status-en-cours { background: #dbeafe; color: #1e40af; }
    .status-termine { background: #d1fae5; color: #065f46; }
    .status-pause { background: #fee2e2; color: #991b1b; }

    /* Métriques dashboard style DG */
    .dg-dashboard-metric {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        box-shadow: var(--box-shadow-sm);
        transition: all var(--animation-speed);
    }

    .dg-dashboard-metric:hover {
        transform: translateY(-2px);
        box-shadow: var(--box-shadow-md);
    }

    .dg-dashboard-metric.success {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    }

    .dg-dashboard-metric.warning {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    }

    .dg-dashboard-metric.danger {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    }

    .dg-dashboard-value {
        font-size: 24px;
        font-weight: 700;
        margin: 0;
    }

    .dg-dashboard-label {
        font-size: 14px;
        opacity: 0.9;
        margin: 0;
    }

    /* Animations - Identiques au HTML */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .dg-section-card {
        animation: fadeIn 0.6s ease-out;
    }

    /* Responsive - Identique au HTML */
    @media (max-width: 768px) {
        .dg-header {
            flex-direction: column;
            text-align: center;
            gap: 15px;
            padding: 20px;
        }
        
        .dg-logo-container {
            flex-direction: column;
            gap: 10px;
        }
        
        .dg-company-name {
            font-size: 20px;
        }
        
        .dg-contact {
            text-align: center;
        }
        
        .dg-form-grid {
            grid-template-columns: 1fr;
        }

        .dg-metric {
            margin-bottom: 10px;
        }
    }
    </style>
    """, unsafe_allow_html=True)


def render_dg_header():
    """
    Affiche l'en-tête DG Inc. professionnel identique au HTML
    """
    st.markdown("""
    <div class="dg-header">
        <div class="dg-logo-container">
            <div class="dg-logo-box">
                <div class="dg-logo-text">DG</div>
            </div>
            <h2 class="dg-company-name">Desmarais & Gagné inc.</h2>
        </div>
        <div class="dg-contact">
            <p>565 rue Maisonneuve<br>
            Granby, QC J2G 3H5<br>
            Tél.: (450) 372-9630<br>
            Téléc.: (450) 372-8122</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_bons_travail_tab(gestionnaire):
    """
    Interface principale pour les Bons de Travail - Style DG Inc.
    
    Args:
        gestionnaire: Instance du gestionnaire de formulaires de base
    """
    # Appliquer le style DG
    apply_dg_style()
    
    st.markdown("### 🔧 Bons de Travail - DG Inc.")
    
    # Initialiser le gestionnaire spécialisé
    if 'gestionnaire_bt' not in st.session_state:
        st.session_state.gestionnaire_bt = GestionnaireBonsTravail(gestionnaire)
    
    gestionnaire_bt = st.session_state.gestionnaire_bt
    
    # Navigation style DG
    _render_navigation_dg(gestionnaire_bt)
    
    # Affichage selon l'action sélectionnée
    action = st.session_state.get('form_action', 'list_bon_travail')
    
    if action == "create_bon_travail":
        render_bon_travail_form_db(gestionnaire_bt)
    elif action == "list_bon_travail":
        render_bon_travail_list_dg(gestionnaire_bt)
    elif action == "stats_bon_travail":
        render_bon_travail_stats_dg(gestionnaire_bt)
    elif action == "productivite_bt":
        render_rapport_productivite_dg(gestionnaire_bt)


def _render_navigation_dg(gestionnaire_bt):
    """
    Navigation style DG Inc. avec métriques identiques au HTML
    
    Args:
        gestionnaire_bt: Instance du gestionnaire BT
    """
    # Métriques rapides style DG - Identiques au HTML
    stats = gestionnaire_bt.get_statistiques_bt()
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        total_bt = stats.get('total', 0)
        st.markdown(f"""
        <div class="dg-dashboard-metric">
            <div class="dg-dashboard-value">🔧 {total_bt}</div>
            <div class="dg-dashboard-label">Total BT</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_m2:
        en_cours = stats.get('en_cours', 0)
        st.markdown(f"""
        <div class="dg-dashboard-metric success">
            <div class="dg-dashboard-value">⚡ {en_cours}</div>
            <div class="dg-dashboard-label">En Cours</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_m3:
        termines = stats.get('par_statut', {}).get('TERMINÉ', 0)
        st.markdown(f"""
        <div class="dg-dashboard-metric warning">
            <div class="dg-dashboard-value">✅ {termines}</div>
            <div class="dg-dashboard-label">Terminés</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_m4:
        montant_total = stats.get('montant_total', 0)
        st.markdown(f"""
        <div class="dg-dashboard-metric danger">
            <div class="dg-dashboard-value">💰 {formater_montant(montant_total)}</div>
            <div class="dg-dashboard-label">Montant Total</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Navigation principale - Style DG
    col_nav1, col_nav2, col_nav3, col_nav4 = st.columns(4)
    
    with col_nav1:
        if st.button("➕ Nouveau BT", use_container_width=True, key="bt_nouveau"):
            st.session_state.form_action = "create_bon_travail"
            st.rerun()
    
    with col_nav2:
        if st.button("📋 Liste Complète", use_container_width=True, key="bt_liste"):
            st.session_state.form_action = "list_bon_travail"
            st.rerun()
    
    with col_nav3:
        if st.button("📊 Statistiques", use_container_width=True, key="bt_stats"):
            st.session_state.form_action = "stats_bon_travail"
            st.rerun()
    
    with col_nav4:
        if st.button("📈 Productivité", use_container_width=True, key="bt_productivite"):
            st.session_state.form_action = "productivite_bt"
            st.rerun()


def render_bon_travail_form_db(gestionnaire_bt):
    """
    Formulaire de création de Bon de Travail - VERSION COMPLÈTE UTILISANT LA BASE DE DONNÉES
    
    Args:
        gestionnaire_bt: Instance du gestionnaire BT spécialisé
    """
    # Gestion du succès AVANT le formulaire
    if st.session_state.get('bt_creation_success'):
        success_info = st.session_state.bt_creation_success
        
        st.success(f"✅ Bon de Travail {success_info['numero']} créé avec succès!")
        
        if success_info.get('urgent'):
            st.warning("🚨 **BT URGENT** - Équipe notifiée pour démarrage immédiat")
        
        col_next1, col_next2, col_next3 = st.columns(3)
        
        with col_next1:
            if st.button("📋 Voir la Liste", use_container_width=True, key="bt_voir_liste_success"):
                st.session_state.bt_creation_success = None
                st.session_state.form_action = "list_bon_travail"
                st.rerun()
        
        with col_next2:
            if st.button("👁️ Voir Détails", use_container_width=True, key="bt_voir_details_success"):
                st.session_state.selected_formulaire_id = success_info['bt_id']
                st.session_state.show_formulaire_modal = True
                st.session_state.bt_creation_success = None
                st.rerun()
        
        with col_next3:
            if st.button("➕ Créer un Autre", use_container_width=True, key="bt_creer_autre_success"):
                st.session_state.bt_creation_success = None
                st.rerun()
        
        return
    
    # Configuration et aide
    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
    st.markdown('<h3 class="dg-info-title">⚙️ Configuration du Bon de Travail</h3>', unsafe_allow_html=True)
    
    col_config1, col_config2 = st.columns(2)
    
    with col_config1:
        if st.button("🔄 Réinitialiser Formulaire", use_container_width=True, key="bt_reset_form"):
            # Supprimer toutes les clés de session liées au formulaire BT
            keys_to_remove = [key for key in st.session_state.keys() if key.startswith('bt_') and 'gestionnaire' not in key]
            for key in keys_to_remove:
                del st.session_state[key]
            st.success("✅ Formulaire réinitialisé!")
            st.rerun()
    
    with col_config2:
        if st.button("📋 Aide Formulaire", use_container_width=True, key="bt_help"):
            st.info("""
            💡 **Conseils de remplissage:**
            - Sélectionnez un projet actif pour lier le BT
            - Choisissez les opérations du projet à inclure
            - Sélectionnez les matériaux nécessaires
            - Assignez l'équipe appropriée
            - Complétez les instructions détaillées
            """)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Container principal style DG
    st.markdown('<div class="dg-main-container">', unsafe_allow_html=True)
    
    # En-tête DG
    render_dg_header()
    
    # Titre de section
    st.markdown('<h2 class="dg-section-title">Bon de Travail</h2>', unsafe_allow_html=True)
    
    # Contenu principal
    st.markdown('<div class="dg-main-content">', unsafe_allow_html=True)
    
    # Récupération des données de base depuis la BD
    projets = get_projets_actifs()
    employes = get_employes_actifs()
    work_centers = get_work_centers_actifs()
    
    if not projets:
        st.error("❌ Aucun projet actif. Créez d'abord un projet dans le module Projets.")
        st.markdown('</div></div>', unsafe_allow_html=True)
        return
    
    if not employes:
        st.error("❌ Aucun employé actif trouvé.")
        st.markdown('</div></div>', unsafe_allow_html=True)
        return
    
    # Formulaire principal avec style DG
    with st.form("bon_travail_form_db", clear_on_submit=True):
        # Section informations de base - Style DG
        st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
        st.markdown('<h3 class="dg-info-title">🔧 INFORMATIONS GÉNÉRALES</h3>', unsafe_allow_html=True)
        
        # Informations de base
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            numero_bt = gestionnaire_bt.base.generer_numero_document('BON_TRAVAIL')
            st.markdown(f"**Date de création:** {datetime.now().strftime('%Y-%m-%d')}")
            st.markdown(f"**N° Bon de Travail:** {numero_bt}")
            
            # Grille de formulaire DG
            st.markdown('<div class="dg-form-grid">', unsafe_allow_html=True)
            
            # Projet (OBLIGATOIRE pour BT)
            projet_options = [("", "Sélectionner un projet")] + [(p['id'], f"#{p['id']} - {p['nom_projet']}") for p in projets]
            projet_id = st.selectbox(
                "Projet *",
                options=[p[0] for p in projet_options],
                format_func=lambda x: next((p[1] for p in projet_options if p[0] == x), ""),
                help="Projet obligatoire pour les Bons de Travail"
            )
            
            # Informations du projet sélectionné
            if projet_id:
                projet_selectionne = next((p for p in projets if p['id'] == projet_id), None)
                if projet_selectionne:
                    st.text_input("Client", value=projet_selectionne.get('client_nom_cache', 'N/A'), disabled=True)
                    st.text_input("Statut Projet", value=projet_selectionne.get('statut', 'N/A'), disabled=True)
                    st.text_input("Prix Estimé", value=f"{projet_selectionne.get('prix_estime', 0):,.2f}$", disabled=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_info2:
            # Responsable du BT
            employe_options = [("", "Sélectionner...")] + [(e['id'], f"{e['prenom']} {e['nom']} - {e['poste']}") for e in employes]
            employe_id = st.selectbox(
                "Responsable BT *",
                options=[e[0] for e in employe_options],
                format_func=lambda x: next((e[1] for e in employe_options if e[0] == x), "")
            )
            
            priorite = st.selectbox("Priorité", ["NORMAL", "URGENT", "CRITIQUE"], index=0)
            
            col_dates = st.columns(2)
            with col_dates[0]:
                date_debut = st.date_input("Date début prévue", datetime.now().date())
            with col_dates[1]:
                date_fin = st.date_input("Date fin prévue", datetime.now().date() + timedelta(days=7))
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Section Opérations du Projet - DEPUIS LA BASE DE DONNÉES
        operations_selectionnees = []
        work_centers_utilises = []
        
        if projet_id:
            operations_projet = get_operations_projet(projet_id)
            
            st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
            st.markdown('<h3 class="dg-info-title">⚙️ OPÉRATIONS DU PROJET</h3>', unsafe_allow_html=True)
            
            if operations_projet:
                st.markdown("**Sélectionner les opérations à inclure dans ce BT :**")
                
                # Tableau des opérations disponibles avec sélection
                for i, operation in enumerate(operations_projet):
                    with st.container():
                        col_sel, col_seq, col_desc, col_temps, col_poste, col_statut = st.columns([1, 1, 4, 1, 3, 1])
                        
                        with col_sel:
                            selected = st.checkbox(
                                f"Op {operation['sequence']}", 
                                key=f"op_select_{operation['id']}",
                                label_visibility="collapsed"
                            )
                            
                            if selected:
                                operations_selectionnees.append(operation['id'])
                                if operation.get('work_center_id') and operation['work_center_id'] not in work_centers_utilises:
                                    work_centers_utilises.append(operation['work_center_id'])
                        
                        with col_seq:
                            st.write(f"**{operation['sequence']}**")
                        
                        with col_desc:
                            st.write(operation['description'][:60] + "..." if len(operation['description']) > 60 else operation['description'])
                        
                        with col_temps:
                            st.write(f"{operation.get('temps_estime', 0):.1f}h")
                        
                        with col_poste:
                            # Informations du poste de travail
                            poste_info = "N/A"
                            if operation.get('work_center_id'):
                                wc = next((w for w in work_centers if w['id'] == operation['work_center_id']), None)
                                if wc:
                                    poste_info = f"{wc['nom']} ({wc['departement']})"
                            st.write(poste_info)
                        
                        with col_statut:
                            # Statut avec badge
                            statut = operation.get('statut', 'À FAIRE')
                            statut_class = f"status-{statut.lower().replace(' ', '-').replace('à', 'a')}"
                            st.markdown(f'<span class="status-badge {statut_class}">{statut}</span>', unsafe_allow_html=True)
                
                # Résumé des sélections
                if operations_selectionnees:
                    temps_total = sum(op.get('temps_estime', 0) for op in operations_projet if op['id'] in operations_selectionnees)
                    st.success(f"✅ {len(operations_selectionnees)} opération(s) sélectionnée(s) - Temps total estimé: {temps_total:.1f}h")
                else:
                    st.info("ℹ️ Aucune opération sélectionnée. Le BT sera créé sans opérations spécifiques.")
            else:
                st.warning("⚠️ Aucune opération définie pour ce projet. Vous pouvez créer le BT et ajouter les opérations plus tard.")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Section Matériaux du Projet - DEPUIS LA BASE DE DONNÉES
        materiaux_selectionnes = []
        
        if projet_id:
            materiaux_projet = get_materiaux_projet(projet_id)
            
            st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
            st.markdown('<h3 class="dg-info-title">📦 MATÉRIAUX DU PROJET</h3>', unsafe_allow_html=True)
            
            if materiaux_projet:
                st.markdown("**Matériaux disponibles pour ce projet :**")
                
                # Tableau des matériaux avec sélection
                for i, materiau in enumerate(materiaux_projet):
                    with st.container():
                        col_sel, col_desc, col_qty, col_unit, col_prix, col_total = st.columns([1, 4, 1, 1, 1, 1])
                        
                        with col_sel:
                            selected_mat = st.checkbox(f"Mat {i+1}", key=f"mat_select_{materiau['id']}", label_visibility="collapsed")
                            
                            if selected_mat:
                                materiaux_selectionnes.append(materiau['id'])
                        
                        with col_desc:
                            st.write(materiau['designation'][:50] + "..." if len(materiau['designation']) > 50 else materiau['designation'])
                        
                        with col_qty:
                            st.write(f"{materiau.get('quantite', 0):.1f}")
                        
                        with col_unit:
                            st.write(materiau.get('unite', 'UN'))
                        
                        with col_prix:
                            st.write(f"{materiau.get('prix_unitaire', 0):.2f}$")
                        
                        with col_total:
                            total_materiau = materiau.get('quantite', 0) * materiau.get('prix_unitaire', 0)
                            st.write(f"{total_materiau:.2f}$")
                
                # Résumé matériaux
                if materiaux_selectionnes:
                    cout_total = sum(m.get('quantite', 0) * m.get('prix_unitaire', 0) 
                                   for m in materiaux_projet if m['id'] in materiaux_selectionnes)
                    st.success(f"✅ {len(materiaux_selectionnes)} matériau(x) sélectionné(s) - Coût estimé: {cout_total:.2f}$")
                else:
                    st.info("ℹ️ Aucun matériau sélectionné.")
            else:
                st.info("ℹ️ Aucun matériau défini pour ce projet.")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Section Assignations d'Employés - DEPUIS LA BASE DE DONNÉES
        st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
        st.markdown('<h3 class="dg-info-title">👥 ASSIGNATION D\'ÉQUIPE</h3>', unsafe_allow_html=True)
        
        st.markdown("**Sélectionner les employés à assigner à ce BT :**")
        
        employes_assignes = []
        
        # Grouper par département pour une meilleure organisation
        departements = {}
        for employe in employes:
            dept = employe.get('departement', 'Non défini')
            if dept not in departements:
                departements[dept] = []
            departements[dept].append(employe)
        
        for dept, employes_dept in departements.items():
            with st.expander(f"📁 {dept} ({len(employes_dept)} employés)", expanded=(dept == "Production")):
                cols = st.columns(min(3, len(employes_dept)))
                for i, employe in enumerate(employes_dept):
                    with cols[i % min(3, len(employes_dept))]:
                        assigned = st.checkbox(
                            f"{employe['prenom']} {employe['nom']}\n{employe['poste']}", 
                            key=f"emp_assign_{employe['id']}"
                        )
                        if assigned:
                            employes_assignes.append(employe['id'])
        
        if employes_assignes:
            st.success(f"✅ {len(employes_assignes)} employé(s) assigné(s) à ce BT")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Section Instructions et Notes
        st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
        st.markdown('<h3 class="dg-info-title">📝 INSTRUCTIONS ET NOTES</h3>', unsafe_allow_html=True)
        
        instructions = st.text_area("Instructions de travail *", height=100,
                                   placeholder="Instructions détaillées pour l'exécution du travail...")
        
        notes_securite = st.text_area("Notes de sécurité", height=80,
                                     placeholder="Consignes de sécurité particulières...")
        
        qualite = st.text_area("Exigences qualité", height=80,
                              placeholder="Standards et contrôles qualité requis...")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Boutons de soumission - Style DG
        st.markdown('<div class="dg-form-controls">', unsafe_allow_html=True)
        col_submit1, col_submit2, col_submit3 = st.columns(3)
        
        with col_submit1:
            submit_brouillon = st.form_submit_button("💾 Sauvegarder Brouillon", use_container_width=True)
        with col_submit2:
            submit_valider = st.form_submit_button("✅ Valider et Créer BT", use_container_width=True)
        with col_submit3:
            submit_annuler = st.form_submit_button("❌ Annuler", use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Traitement de la soumission
        if submit_brouillon or submit_valider:
            if not projet_id or not employe_id or not instructions:
                st.error("❌ Veuillez remplir tous les champs obligatoires (*)")
                return
            
            # Construction des données avec les VRAIES données de la base
            notes_completes = f"""=== BON DE TRAVAIL DG INC. ===
Instructions : {instructions}

=== OPÉRATIONS SÉLECTIONNÉES ===
{len(operations_selectionnees)} opération(s) du projet #{projet_id}
IDs Opérations : {operations_selectionnees}

=== MATÉRIAUX REQUIS ===
{len(materiaux_selectionnes)} matériau(x) du projet #{projet_id}
IDs Matériaux : {materiaux_selectionnes}

=== ÉQUIPE ASSIGNÉE ===
{len(employes_assignes)} employé(s) assigné(s)
IDs Employés : {employes_assignes}

=== POSTES DE TRAVAIL ===
{len(work_centers_utilises)} poste(s) requis
IDs Postes : {work_centers_utilises}

=== NOTES DE SÉCURITÉ ===
{notes_securite or 'Consignes standards DG Inc.'}

=== EXIGENCES QUALITÉ ===
{qualite or 'Standards DG Inc.'}

=== INFORMATIONS TECHNIQUES ===
Date création: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Créé par: Employé #{employe_id}
Projet source: #{projet_id}
Version: 2.1_database"""
            
            # Calcul des coûts estimés
            cout_materiaux_estime = 0
            if materiaux_selectionnes and projet_id:
                materiaux_projet = get_materiaux_projet(projet_id)
                cout_materiaux_estime = sum(
                    m.get('quantite', 0) * m.get('prix_unitaire', 0) 
                    for m in materiaux_projet if m['id'] in materiaux_selectionnes
                )
            
            temps_estime_total = 0
            if operations_selectionnees and projet_id:
                operations_projet = get_operations_projet(projet_id)
                temps_estime_total = sum(
                    op.get('temps_estime', 0) 
                    for op in operations_projet if op['id'] in operations_selectionnees
                )
            
            # Métadonnées enrichies avec les vraies données
            metadonnees_bt = {
                'operations_selectionnees': operations_selectionnees,
                'materiaux_selectionnes': materiaux_selectionnes,
                'employes_assignes': employes_assignes,
                'work_centers_utilises': work_centers_utilises,
                'projet_source': projet_id,
                'temps_estime_total': temps_estime_total,
                'cout_materiaux_estime': cout_materiaux_estime,
                'date_creation_bt': datetime.now().isoformat(),
                'version_bt': '2.1_database'
            }
            
            data = {
                'type_formulaire': 'BON_TRAVAIL',
                'numero_document': numero_bt,
                'project_id': projet_id,
                'employee_id': employe_id,
                'statut': 'VALIDÉ' if submit_valider else 'BROUILLON',
                'priorite': priorite,
                'date_creation': date_debut,
                'date_echeance': date_fin,
                'montant_total': cout_materiaux_estime,
                'notes': notes_completes,
                'metadonnees_json': json.dumps(metadonnees_bt),
                'operations_selectionnees': operations_selectionnees,
                'materiaux_selectionnes': materiaux_selectionnes,
                'employes_assignes': employes_assignes,
                'work_centers_utilises': work_centers_utilises,
                'description': instructions,
                'temps_estime_total': temps_estime_total,
                'cout_materiaux_estime': cout_materiaux_estime
            }
            
            bt_id = gestionnaire_bt.creer_bon_travail(data)
            
            if bt_id:
                st.session_state.bt_creation_success = {
                    'bt_id': bt_id,
                    'numero': numero_bt,
                    'urgent': priorite == 'CRITIQUE'
                }
                st.rerun()
        
        elif submit_annuler:
            st.session_state.form_action = "list_bon_travail"
            st.rerun()
    
    # Footer DG
    st.markdown("""
    <div class="dg-footer">
        <p><strong>📋 Système:</strong> Intégré avec base de données SQLite DG Inc.</p>
        <p><strong>🔄 Version:</strong> 2.1 - Données temps réel depuis tables projects, operations, materials, employees</p>
        <p><strong>📞 Support:</strong> (450) 372-9630</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Fin main-content
    st.markdown('</div>', unsafe_allow_html=True)  # Fin main-container


def render_bon_travail_list_dg(gestionnaire_bt):
    """
    Liste des Bons de Travail avec style DG Inc. et données réelles
    
    Args:
        gestionnaire_bt: Instance du gestionnaire BT spécialisé
    """
    st.markdown("#### 📋 Gestion des Bons de Travail - DG Inc.")
    
    bons_travail = gestionnaire_bt.get_bons_travail()
    
    if not bons_travail:
        st.markdown("""
        <div class="dg-info-section" style="text-align:center;">
            <h3>🏭 Bienvenue dans le système de Bons de Travail DG Inc.</h3>
            <p>Aucun Bon de Travail créé. Cliquez sur 'Nouveau BT' pour commencer.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("➕ Créer le Premier BT", use_container_width=True, key="bt_premier"):
            st.session_state.form_action = "create_bon_travail"
            st.rerun()
        return
    
    # Tableau de bord rapide - Style DG avec vraies données
    col_dash1, col_dash2, col_dash3, col_dash4 = st.columns(4)
    
    with col_dash1:
        total_bt = len(bons_travail)
        st.markdown(f"""
        <div class="dg-dashboard-metric">
            <div class="dg-dashboard-value">{total_bt}</div>
            <div class="dg-dashboard-label">Bons de Travail</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_dash2:
        en_cours = len([bt for bt in bons_travail if bt['statut'] in ['VALIDÉ', 'EN COURS']])
        st.markdown(f"""
        <div class="dg-dashboard-metric success">
            <div class="dg-dashboard-value">{en_cours}</div>
            <div class="dg-dashboard-label">En Cours</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_dash3:
        termines = len([bt for bt in bons_travail if bt['statut'] == 'TERMINÉ'])
        st.markdown(f"""
        <div class="dg-dashboard-metric warning">
            <div class="dg-dashboard-value">{termines}</div>
            <div class="dg-dashboard-label">Terminés</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_dash4:
        urgents = len([bt for bt in bons_travail if bt.get('priorite') in ['CRITIQUE', 'URGENT']])
        st.markdown(f"""
        <div class="dg-dashboard-metric danger">
            <div class="dg-dashboard-value">{urgents}</div>
            <div class="dg-dashboard-label">Urgents</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Liste des BT récents style DG avec vraies données
    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
    st.markdown('<h3 class="dg-info-title">🔧 Bons de Travail Récents</h3>', unsafe_allow_html=True)
    
    # Afficher les BT avec style HTML et vraies données
    bts_recents = sorted(bons_travail, key=lambda x: x.get('date_creation', ''), reverse=True)[:10]
    
    for bt in bts_recents:
        priorite_class = "priority-critical" if bt.get('priorite') == 'CRITIQUE' else "priority-high" if bt.get('priorite') == 'URGENT' else "priority-medium"
        priorite_color = "#ef4444" if bt.get('priorite') == 'CRITIQUE' else "#f59e0b" if bt.get('priorite') == 'URGENT' else "#10b981"
        statut_color = "#059669" if bt['statut'] == 'TERMINÉ' else "#3b82f6" if bt['statut'] == 'EN COURS' else "#f59e0b"
        
        avancement = bt.get('avancement', {}).get('pourcentage', 0)
        assignations = bt.get('assignations', [])
        reservations = bt.get('reservations_postes', [])
        
        st.markdown(f"""
        <div class="dg-table-container {priorite_class}" style="margin:15px 0;">
            <div style="padding:20px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
                    <div>
                        <h4 style="margin:0;color:var(--primary-color-darker);">BT {bt['numero_document']}</h4>
                        <span style="color:{priorite_color};font-weight:600;">● {bt.get('priorite', 'NORMAL')}</span>
                        <span style="color:{statut_color};font-weight:600;margin-left:15px;">● {bt['statut']}</span>
                    </div>
                    <div style="text-align:right;">
                        <div class="dg-progress">
                            <div class="dg-progress-bar" style="width:{avancement}%">
                                {avancement}%
                            </div>
                        </div>
                        <small>{bt.get('avancement', {}).get('operations_terminees', 0)}/{bt.get('avancement', {}).get('operations_totales', 0)} ops</small>
                    </div>
                </div>
                
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin-bottom:15px;">
                    <div>
                        <strong>📋 Projet:</strong><br>
                        <span>{bt.get('nom_projet', bt.get('project_nom', 'N/A'))}</span>
                    </div>
                    <div>
                        <strong>👤 Responsable:</strong><br>
                        <span>{bt.get('employee_nom', 'N/A')}</span>
                    </div>
                    <div>
                        <strong>📅 Création:</strong><br>
                        <span>{bt.get('date_creation', 'N/A')[:10] if bt.get('date_creation') else 'N/A'}</span>
                    </div>
                    <div>
                        <strong>🏁 Échéance:</strong><br>
                        <span>{bt.get('date_echeance', 'N/A')[:10] if bt.get('date_echeance') else 'N/A'}</span>
                    </div>
                </div>
                
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:15px;background:#f8f9fa;padding:10px;border-radius:6px;">
                    <div>
                        <strong>👥 Équipe:</strong><br>
                        <span>{len(assignations)} assigné(s)</span>
                    </div>
                    <div>
                        <strong>🏭 Postes:</strong><br>
                        <span>{len(reservations)} réservé(s)</span>
                    </div>
                    <div>
                        <strong>💰 Montant:</strong><br>
                        <span>{formater_montant(bt.get('montant_total', 0))}</span>
                    </div>
                    <div>
                        <strong>📊 Source:</strong><br>
                        <span>Base SQLite</span>
                    </div>
                </div>
                
                <div style="display:flex;gap:10px;margin-top:15px;flex-wrap:wrap;">
                    <button style="background:var(--primary-color);color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:500;">👁️ Voir</button>
                    <button style="background:#3b82f6;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:500;">✏️ Modifier</button>
                    <button style="background:#8b5cf6;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:500;">📊 Avancement</button>
                    <button style="background:#059669;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:500;">✅ Terminer</button>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Actions rapides - Style DG
    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
    st.markdown('<h3 class="dg-info-title">🔧 Actions sur un BT</h3>', unsafe_allow_html=True)
    
    # Sélection d'un BT pour actions avec vraies données
    if bons_travail:
        bt_options = [(bt['id'], f"BT {bt['numero_document']} - {bt.get('nom_projet', bt.get('project_nom', 'N/A'))}") for bt in bons_travail]
        selected_bt_id = st.selectbox(
            "Sélectionner un BT:",
            options=[bt[0] for bt in bt_options],
            format_func=lambda x: next((bt[1] for bt in bt_options if bt[0] == x), ""),
            key="bt_selection_actions"
        )
        
        selected_bt = next((bt for bt in bons_travail if bt['id'] == selected_bt_id), None)
        
        if selected_bt:
            col_action1, col_action2, col_action3, col_action4, col_action5 = st.columns(5)
            
            with col_action1:
                if st.button("👁️ Voir Détails", use_container_width=True, key=f"bt_voir_{selected_bt_id}"):
                    st.session_state.selected_formulaire_id = selected_bt_id
                    st.session_state.show_formulaire_modal = True
            
            with col_action2:
                if st.button("✏️ Modifier", use_container_width=True, key=f"bt_modifier_{selected_bt_id}"):
                    st.info("Fonction de modification en développement")
            
            with col_action3:
                if st.button("🔧 Créer BT", use_container_width=True, key="bt_creer_nouveau"):
                    st.session_state.form_action = "create_bon_travail"
                    st.rerun()
            
            with col_action4:
                if selected_bt['statut'] in ['VALIDÉ', 'EN COURS']:
                    if st.button("✅ Terminer", use_container_width=True, key=f"bt_terminer_{selected_bt_id}"):
                        if gestionnaire_bt.marquer_bt_termine(selected_bt_id, 1, "Marqué terminé depuis la liste"):
                            st.success("✅ BT terminé!")
                            st.rerun()
                else:
                    st.button("✅ Terminer", disabled=True, use_container_width=True, help="BT déjà terminé ou annulé")
            
            with col_action5:
                if st.button("🗑️ Supprimer", use_container_width=True, key=f"bt_supprimer_{selected_bt_id}"):
                    if st.session_state.get(f'confirm_delete_bt_{selected_bt_id}'):
                        # Confirmation de suppression
                        if gestionnaire_bt.base.supprimer_formulaire(selected_bt_id):
                            st.success("BT supprimé!")
                            del st.session_state[f'confirm_delete_bt_{selected_bt_id}']
                            st.rerun()
                    else:
                        st.session_state[f'confirm_delete_bt_{selected_bt_id}'] = True
                        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_bon_travail_stats_dg(gestionnaire_bt):
    """
    Statistiques détaillées spécifiques aux BT avec style DG Inc. et vraies données
    
    Args:
        gestionnaire_bt: Instance du gestionnaire BT spécialisé
    """
    st.markdown("#### 📊 Statistiques Bons de Travail - DG Inc.")
    
    stats = gestionnaire_bt.get_statistiques_bt()
    bons_travail = gestionnaire_bt.get_bons_travail()
    
    if not bons_travail:
        st.markdown("""
        <div class="dg-info-section" style="text-align:center;">
            <h3>📊 Aucune donnée pour les statistiques</h3>
            <p>Créez des Bons de Travail pour voir les statistiques apparaître ici.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Métriques principales - Style DG avec vraies données
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="dg-metric">
            <div class="dg-metric-value">📋 {len(bons_travail)}</div>
            <div class="dg-metric-label">Total BT</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        en_cours = len([bt for bt in bons_travail if bt['statut'] in ['VALIDÉ', 'EN COURS']])
        st.markdown(f"""
        <div class="dg-metric">
            <div class="dg-metric-value">⚡ {en_cours}</div>
            <div class="dg-metric-label">En Cours</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        termines = len([bt for bt in bons_travail if bt['statut'] == 'TERMINÉ'])
        taux_completion = (termines / len(bons_travail) * 100) if bons_travail else 0
        st.markdown(f"""
        <div class="dg-metric">
            <div class="dg-metric-value">✅ {termines}</div>
            <div class="dg-metric-label">Terminés ({taux_completion:.1f}%)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        duree_moyenne = stats.get('duree_moyenne', 0)
        st.markdown(f"""
        <div class="dg-metric">
            <div class="dg-metric-value">⏱️ {int(duree_moyenne)}</div>
            <div class="dg-metric-label">Durée Moy. (jours)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        projets_concernes = len(set(bt.get('project_id') for bt in bons_travail if bt.get('project_id')))
        st.markdown(f"""
        <div class="dg-metric">
            <div class="dg-metric-value">🏗️ {projets_concernes}</div>
            <div class="dg-metric-label">Projets Concernés</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Graphiques spécifiques BT - Style DG avec vraies données
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown('<div class="dg-section-card">', unsafe_allow_html=True)
        
        # Répartition par statut avec couleurs DG
        statut_counts = {}
        for bt in bons_travail:
            statut = bt['statut']
            statut_counts[statut] = statut_counts.get(statut, 0) + 1
        
        if statut_counts:
            colors_statut = {
                'BROUILLON': '#f59e0b', 'VALIDÉ': '#3b82f6', 'EN COURS': '#8b5cf6',
                'TERMINÉ': '#059669', 'ANNULÉ': '#ef4444'
            }
            fig = px.pie(values=list(statut_counts.values()), names=list(statut_counts.keys()),
                        title="📊 Répartition par Statut (Données Réelles)", 
                        color_discrete_map=colors_statut)
            fig.update_layout(showlegend=True, height=350, 
                             plot_bgcolor='rgba(0,0,0,0)', 
                             paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_g2:
        st.markdown('<div class="dg-section-card">', unsafe_allow_html=True)
        
        # Analyse par projet avec vraies données
        projet_stats = {}
        for bt in bons_travail:
            projet = bt.get('nom_projet', bt.get('project_nom', 'Projet non défini'))
            if projet not in projet_stats:
                projet_stats[projet] = {'total': 0, 'termines': 0}
            projet_stats[projet]['total'] += 1
            if bt['statut'] == 'TERMINÉ':
                projet_stats[projet]['termines'] += 1
        
        if projet_stats:
            projets_data = []
            for projet, stats_p in projet_stats.items():
                taux = (stats_p['termines'] / stats_p['total'] * 100) if stats_p['total'] > 0 else 0
                projets_data.append({
                    'Projet': projet[:20] + "..." if len(projet) > 20 else projet,
                    'Total BT': stats_p['total'],
                    'Taux Completion': taux
                })
            
            df_projets = pd.DataFrame(projets_data)
            fig = px.bar(df_projets, x='Projet', y='Total BT', color='Taux Completion',
                        title="📈 BT par Projet (Données BD)", color_continuous_scale='RdYlGn')
            fig.update_layout(height=350,
                             plot_bgcolor='rgba(0,0,0,0)', 
                             paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Analyse de productivité - Style DG avec vraies données
    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
    st.markdown('<h3 class="dg-info-title">📈 Analyse de Productivité (Base SQLite)</h3>', unsafe_allow_html=True)
    
    col_prod1, col_prod2 = st.columns(2)
    
    with col_prod1:
        # BT par responsable avec vraies données
        responsable_stats = {}
        for bt in bons_travail:
            responsable = bt.get('employee_nom', 'Non assigné')
            if responsable not in responsable_stats:
                responsable_stats[responsable] = {'total': 0, 'termines': 0}
            responsable_stats[responsable]['total'] += 1
            if bt['statut'] == 'TERMINÉ':
                responsable_stats[responsable]['termines'] += 1
        
        st.markdown("**Top Responsables BT (Données Réelles) :**")
        top_responsables = sorted(responsable_stats.items(), 
                                key=lambda x: x[1]['total'], reverse=True)[:5]
        
        for i, (responsable, stats_r) in enumerate(top_responsables, 1):
            taux = (stats_r['termines'] / stats_r['total'] * 100) if stats_r['total'] > 0 else 0
            st.markdown(f"""
            <div class="dg-metric" style="margin:5px 0;padding:10px;">
                <div style="font-size:16px;font-weight:600;">{i}. {responsable[:25]}</div>
                <div style="font-size:14px;">{stats_r['total']} BT • {taux:.0f}% terminés</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col_prod2:
        # Évolution mensuelle avec vraies données
        evolution_mensuelle = {}
        for bt in bons_travail:
            try:
                date_creation = bt.get('date_creation', '')
                if date_creation:
                    mois = date_creation[:7]  # YYYY-MM
                    if mois not in evolution_mensuelle:
                        evolution_mensuelle[mois] = 0
                    evolution_mensuelle[mois] += 1
            except:
                continue
        
        if evolution_mensuelle:
            mois_sorted = sorted(evolution_mensuelle.items())[-6:]  # 6 derniers mois
            df_evolution = pd.DataFrame(mois_sorted, columns=['Mois', 'Nombre BT'])
            
            fig = px.line(df_evolution, x='Mois', y='Nombre BT',
                         title="Évolution Mensuelle des BT (BD)",
                         markers=True, color_discrete_sequence=['#00A971'])
            fig.update_layout(height=300,
                             plot_bgcolor='rgba(0,0,0,0)', 
                             paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_rapport_productivite_dg(gestionnaire_bt):
    """
    Rapport de productivité détaillé pour les BT avec style DG Inc. et vraies données
    
    Args:
        gestionnaire_bt: Instance du gestionnaire BT spécialisé
    """
    st.markdown("#### 📈 Rapport de Productivité BT - DG Inc.")
    
    # Sélection de la période - Style DG
    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
    st.markdown('<h3 class="dg-info-title">⚙️ Configuration du Rapport</h3>', unsafe_allow_html=True)
    
    col_periode1, col_periode2 = st.columns(2)
    
    with col_periode1:
        periode = st.selectbox("Période d'analyse", [7, 15, 30, 60, 90], index=2, 
                              format_func=lambda x: f"{x} derniers jours")
    
    with col_periode2:
        if st.button("🔄 Générer Rapport", use_container_width=True, key="bt_generer_rapport"):
            rapport = gestionnaire_bt.generer_rapport_productivite(periode)
            
            if rapport:
                st.success(f"✅ Rapport généré pour {rapport['periode']} (Base SQLite)")
                
                # Métriques du rapport - Style DG
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                
                with col_r1:
                    st.markdown(f"""
                    <div class="dg-metric">
                        <div class="dg-metric-value">{rapport['total_bt_termines']}</div>
                        <div class="dg-metric-label">BT Terminés</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_r2:
                    st.markdown(f"""
                    <div class="dg-metric">
                        <div class="dg-metric-value">{rapport['duree_moyenne_globale']:.1f}</div>
                        <div class="dg-metric-label">Durée Moy. (jours)</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_r3:
                    st.markdown(f"""
                    <div class="dg-metric">
                        <div class="dg-metric-value">{len(rapport['employes'])}</div>
                        <div class="dg-metric-label">Employés Actifs</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_r4:
                    source = rapport.get('source_donnees', 'inconnue')
                    st.markdown(f"""
                    <div class="dg-metric">
                        <div class="dg-metric-value">📊</div>
                        <div class="dg-metric-label">{source}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Détail par employé - Style DG avec vraies données
                if rapport['employes']:
                    st.markdown('<br>', unsafe_allow_html=True)
                    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
                    st.markdown('<h3 class="dg-info-title">👥 Détail par Employé (Données BD)</h3>', unsafe_allow_html=True)
                    
                    df_employes = pd.DataFrame(rapport['employes'])
                    if 'duree_moyenne' in df_employes.columns:
                        df_employes['duree_moyenne'] = df_employes['duree_moyenne'].round(1)
                    if 'montant_total_travaux' in df_employes.columns:
                        df_employes['montant_total_travaux'] = df_employes['montant_total_travaux'].apply(lambda x: f"{x:,.0f}$")
                    
                    # Affichage tableau avec style
                    st.markdown('<div class="dg-table-container">', unsafe_allow_html=True)
                    st.dataframe(df_employes, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Analyse et recommandations - Style DG avec vraies données
                if rapport.get('analyse'):
                    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
                    st.markdown('<h3 class="dg-info-title">📊 Analyse des Performances (BD)</h3>', unsafe_allow_html=True)
                    
                    if 'top_performer' in rapport['analyse']:
                        top_perf = rapport['analyse']['top_performer']
                        st.markdown(f"**🏆 Top Performer:** {top_perf['employe_nom']} ({top_perf['nb_bt_termines']} BT terminés)")
                    
                    if 'plus_efficace' in rapport['analyse']:
                        efficace = rapport['analyse']['plus_efficace']
                        st.markdown(f"**⚡ Plus Efficace:** {efficace['employe_nom']} ({efficace['duree_moyenne']:.1f} jours/BT)")
                    
                    if 'plus_rentable' in rapport['analyse']:
                        rentable = rapport['analyse']['plus_rentable']
                        st.markdown(f"**💰 Plus Rentable:** {rentable['employe_nom']} ({rentable['montant_total_travaux']:,.0f}$ de travaux)")
                    
                    if 'plus_polyvalent' in rapport['analyse']:
                        polyvalent = rapport['analyse']['plus_polyvalent']
                        st.markdown(f"**🎯 Plus Polyvalent:** {polyvalent['employe_nom']} ({polyvalent['projets_touches']} projets)")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Recommandations - Style DG
                if rapport.get('recommandations'):
                    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
                    st.markdown('<h3 class="dg-info-title">💡 Recommandations (Base Données)</h3>', unsafe_allow_html=True)
                    
                    for recommandation in rapport['recommandations']:
                        st.info(recommandation)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning("Aucune donnée disponible pour cette période")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Conseils d'optimisation généraux - Style DG
    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
    st.markdown('<h3 class="dg-info-title">💡 Conseils d\'Optimisation DG Inc.</h3>', unsafe_allow_html=True)
    
    conseils = [
        "📊 Suivez régulièrement l'avancement des BT en cours depuis la base SQLite",
        "👥 Équilibrez la charge de travail entre les employés actifs",
        "⏱️ Identifiez les BT qui prennent plus de temps que prévu",
        "🔧 Optimisez l'assignation des postes de travail disponibles",
        "📋 Assurez-vous que les opérations sont bien définies dans les projets",
        "🏭 Utilisez les vraies données pour améliorer les processus DG Inc.",
        "📈 Analysez les tendances mensuelles pour planifier les ressources",
        "🗄️ Exploitez pleinement les relations entre tables SQLite",
        "🔗 Maintenez la cohérence entre projets, opérations et matériaux"
    ]
    
    for conseil in conseils:
        st.markdown(f"""
        <div style="background:#f0f9ff;border-left:4px solid var(--primary-color);padding:10px;margin:5px 0;border-radius:6px;">
            {conseil}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
