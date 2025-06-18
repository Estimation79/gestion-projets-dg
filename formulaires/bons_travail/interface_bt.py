# formulaires/bons_travail/interface_bt.py
# Interface utilisateur pour les Bons de Travail - VERSION COMPLÈTE ÉTAPE 3 INTÉGRATION TIMETRACKER

"""
Interface utilisateur pour les Bons de Travail - Style DG Inc.
Contient tous les composants d'affichage et d'interaction pour les BT.
VERSION ÉTAPE 3 : Design professionnel DG Inc. fidèle au HTML avec données dynamiques SQLite + Intégration TimeTracker
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .gestionnaire_bt import GestionnaireBonsTravail
from ..utils.helpers import (
    get_projets_actifs,
    get_employes_actifs,
    get_operations_projet,
    get_materiaux_projet,
    get_work_centers_actifs,
    get_articles_inventaire,
    search_articles_inventaire,
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

    .dg-btn-add {
        background: var(--primary-color);
        color: white;
        border: none;
        border-radius: var(--border-radius-sm);
        padding: 8px 16px;
        cursor: pointer;
        font-size: 14px;
        margin: 10px 0;
        transition: all var(--animation-speed);
    }

    .dg-btn-delete {
        background: #ef4444;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 4px 8px;
        cursor: pointer;
        font-size: 12px;
        margin-left: 5px;
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

    /* Input styles DG */
    .stTextInput input, .stTextArea textarea, .stSelectbox select, .stNumberInput input {
        border: 1px solid var(--border-color) !important;
        border-radius: var(--border-radius-sm) !important;
        transition: all var(--animation-speed) !important;
        padding: 6px 8px !important;
        font-family: 'Inter', sans-serif !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus, .stNumberInput input:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 2px rgba(0, 169, 113, 0.2) !important;
        outline: none !important;
    }

    /* Navigation principale DG */
    .dg-nav {
        background: white;
        padding: 15px 0;
        border-bottom: 2px solid var(--border-color);
        margin-bottom: 20px;
        box-shadow: var(--box-shadow-sm);
    }

    .dg-nav-btn {
        padding: 10px 20px;
        background: #f8f9fa;
        border: 1px solid var(--border-color);
        border-radius: var(--border-radius-md);
        cursor: pointer;
        font-weight: 500;
        transition: all var(--animation-speed);
        text-decoration: none;
        color: var(--text-color);
        display: inline-flex;
        align-items: center;
        gap: 8px;
        margin: 0 5px;
    }

    .dg-nav-btn.active {
        background: var(--primary-color);
        color: white;
        border-color: var(--primary-color);
    }

    .dg-nav-btn:hover:not(.active) {
        background: #e9ecef;
        border-color: var(--primary-color);
        transform: translateY(-1px);
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

    /* Animations - Identiques au HTML */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .dg-section-card {
        animation: fadeIn 0.6s ease-out;
    }

    /* Styles spécifiques tableaux */
    .dg-operations-table {
        margin-bottom: 25px;
    }

    .dg-operations-table th {
        background: linear-gradient(135deg, #e6f7f1 0%, #d0f0e6 100%);
        color: var(--primary-color-darker);
        font-weight: 600;
        font-size: 13px;
        border-bottom: 2px solid var(--primary-color);
        padding: 8px 6px;
        text-align: left;
    }

    .dg-operations-table td {
        border: 1px solid var(--border-color);
        padding: 8px 6px;
        text-align: left;
    }

    .dg-operations-table tbody tr:nth-child(even) {
        background-color: #f8f9fa;
    }

    .dg-operations-table tbody tr:hover {
        background-color: #e6f7f1;
        transition: background-color var(--animation-speed);
    }

    .total-row {
        background: linear-gradient(135deg, #e6f7f1 0%, #d0f0e6 100%);
        font-weight: 600;
        color: var(--primary-color-darker);
    }

    /* Colonnes spécifiques */
    .qty-col { width: 80px; text-align: center; }
    .price-col { width: 100px; text-align: right; }
    .time-col { width: 100px; text-align: center; }
    .date-col { width: 120px; text-align: center; }
    .status-col { width: 120px; text-align: center; }

    /* Styles pour les sélecteurs spécialisés */
    .priority-select { 
        background-color: #fff7ed; 
        border: 2px solid #fb923c; 
        font-weight: 500; 
    }
    
    .status-select { 
        background-color: #f0f9ff; 
        border: 2px solid #3b82f6; 
        font-weight: 500; 
    }

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

    /* Notification style DG */
    .dg-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-color-darker) 100%);
        color: white;
        padding: 15px 20px;
        border-radius: var(--border-radius-md);
        box-shadow: var(--box-shadow-md);
        z-index: 1000;
        transform: translateX(400px);
        transition: transform 0.3s ease;
    }

    .dg-notification.show {
        transform: translateX(0);
    }

    /* Style Streamlit overrides pour cohérence DG */
    .stButton > button {
        border-radius: var(--border-radius-md) !important;
        border: 1px solid var(--border-color) !important;
        transition: all var(--animation-speed) !important;
    }

    .stButton > button:hover {
        border-color: var(--primary-color) !important;
        transform: translateY(-1px) !important;
    }

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


def get_types_operations_dynamiques() -> List[str]:
    """
    Récupère les types d'opérations depuis la base de données.
    Combine les opérations existantes et les types prédéfinis.
    
    Returns:
        List[str]: Liste des types d'opération disponibles
    """
    try:
        # Types d'opération de base pour DG Inc.
        types_base = [
            "Programmation CNC",
            "Découpe plasma", 
            "Poinçonnage",
            "Soudage TIG",
            "Soudage MIG",
            "Assemblage",
            "Meulage",
            "Polissage",
            "Emballage",
            "Contrôle qualité",
            "Usinage conventionnel",
            "Perçage",
            "Taraudage",
            "Pliage",
            "Roulage"
        ]
        
        # Récupérer les types d'opération depuis la base (si disponible)
        try:
            query = """
                SELECT DISTINCT description 
                FROM operations 
                WHERE description IS NOT NULL 
                AND description != ''
                ORDER BY description
            """
            rows = st.session_state.erp_db.execute_query(query)
            types_db = [row['description'] for row in rows if row['description']]
            
            # Combiner et dédoublonner
            all_types = list(set(types_base + types_db))
            all_types.sort()
            
            return all_types
            
        except Exception as e:
            print(f"Info: Utilisation des types d'opération par défaut - {e}")
            return sorted(types_base)
            
    except Exception as e:
        print(f"Erreur récupération types opération: {e}")
        return ["Programmation CNC", "Découpe plasma", "Soudage", "Assemblage"]


def get_statuts_operations() -> List[str]:
    """
    Retourne les statuts possibles pour les opérations.
    
    Returns:
        List[str]: Liste des statuts d'opération
    """
    return ["En attente", "En cours", "Terminé", "En pause", "Annulé"]


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
    
    # Gestion de l'affichage modal des détails BT avec intégration TimeTracker
    if st.session_state.get('show_formulaire_modal') and st.session_state.get('selected_formulaire_id'):
        render_bon_travail_details_modal(gestionnaire_bt, st.session_state.selected_formulaire_id)
        return
    
    # Affichage selon l'action sélectionnée
    action = st.session_state.get('form_action', 'list_bon_travail')
    
    if action == "create_bon_travail":
        render_bon_travail_form_dg(gestionnaire_bt)
    elif action == "list_bon_travail":
        render_bon_travail_list_dg(gestionnaire_bt)
    elif action == "stats_bon_travail":
        render_bon_travail_stats_dg(gestionnaire_bt)
    elif action == "productivite_bt":
        render_rapport_productivite_dg(gestionnaire_bt)


def render_bon_travail_details_modal(gestionnaire_bt, bt_id):
    """
    Affiche les détails complets d'un BT avec intégration TimeTracker - ÉTAPE 3
    
    Args:
        gestionnaire_bt: Instance du gestionnaire BT
        bt_id: ID du Bon de Travail
    """
    bt_details = gestionnaire_bt.get_bt_details_complets(bt_id)
    
    if not bt_details:
        st.error("Bon de Travail non trouvé")
        if st.button("← Retour"):
            st.session_state.show_formulaire_modal = False
            st.session_state.selected_formulaire_id = None
            st.rerun()
        return
    
    # En-tête modal style DG
    st.markdown('<div class="dg-main-container">', unsafe_allow_html=True)
    render_dg_header()
    
    col_header1, col_header2, col_header3 = st.columns([2, 1, 1])
    
    with col_header1:
        priorite_color = "#ef4444" if bt_details.get('priorite') == 'CRITIQUE' else "#f59e0b" if bt_details.get('priorite') == 'URGENT' else "#10b981"
        statut_color = "#059669" if bt_details['statut'] == 'TERMINÉ' else "#3b82f6" if bt_details['statut'] == 'EN COURS' else "#f59e0b"
        
        st.markdown(f"""
        <h2 class="dg-section-title">🔧 BT {bt_details['numero_document']}</h2>
        <div style="padding: 15px 20px; background: #f8f9fa;">
            <span style="color:{priorite_color};font-weight:600;">● {bt_details.get('priorite', 'NORMAL')}</span>
            <span style="color:{statut_color};font-weight:600;margin-left:20px;">● {bt_details['statut']}</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col_header2:
        if st.button("✏️ Modifier", use_container_width=True):
            st.info("Fonction de modification en développement")
    
    with col_header3:
        if st.button("← Fermer", use_container_width=True):
            st.session_state.show_formulaire_modal = False
            st.session_state.selected_formulaire_id = None
            st.rerun()
    
    st.markdown('<div class="dg-main-content">', unsafe_allow_html=True)
    
    # Informations générales du BT
    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
    st.markdown('<h3 class="dg-info-title">📋 Informations Générales</h3>', unsafe_allow_html=True)
    
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.markdown(f"**🏗️ Projet:** {bt_details.get('project_nom', 'N/A')}")
        st.markdown(f"**👤 Responsable:** {bt_details.get('employee_nom', 'N/A')}")
        st.markdown(f"**📅 Création:** {bt_details.get('date_creation', 'N/A')}")
        st.markdown(f"**🏁 Échéance:** {bt_details.get('date_echeance', 'N/A')}")
    
    with col_info2:
        avancement = bt_details.get('avancement_detaille', [])
        nb_operations = len(avancement) if avancement else bt_details.get('avancement', {}).get('operations_totales', 0)
        ops_terminees = bt_details.get('avancement', {}).get('operations_terminees', 0)
        pourcentage = bt_details.get('avancement', {}).get('pourcentage', 0)
        
        st.markdown(f"**📊 Avancement:** {pourcentage}%")
        st.markdown(f"**⚙️ Opérations:** {ops_terminees}/{nb_operations}")
        st.markdown(f"**💰 Montant:** {formater_montant(bt_details.get('montant_total', 0))}")
        
        # Barre de progression
        st.markdown(f"""
        <div class="dg-progress">
            <div class="dg-progress-bar" style="width:{pourcentage}%">
                {pourcentage}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ======================================================================
    # ÉTAPE 3 : SECTION INTÉGRATION TIMETRACKER
    # ======================================================================
    
    st.markdown("---")
    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
    st.markdown('<h3 class="dg-info-title">⏱️ Intégration TimeTracker</h3>', unsafe_allow_html=True)
    
    # Récupérer les statistiques TimeTracker pour ce BT
    stats_tt = gestionnaire_bt.get_heures_timetracker_bt(bt_id)
    
    if stats_tt.get('nb_sessions', 0) > 0:
        # Métriques TimeTracker
        col_tt1, col_tt2, col_tt3, col_tt4 = st.columns(4)
        
        with col_tt1:
            st.markdown(f"""
            <div class="dg-metric">
                <div class="dg-metric-value">🕐 {stats_tt['nb_sessions']}</div>
                <div class="dg-metric-label">Sessions</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_tt2:
            st.markdown(f"""
            <div class="dg-metric">
                <div class="dg-metric-value">👥 {stats_tt['nb_employes']}</div>
                <div class="dg-metric-label">Employés</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_tt3:
            st.markdown(f"""
            <div class="dg-metric">
                <div class="dg-metric-value">⏱️ {stats_tt['total_heures']:.1f}h</div>
                <div class="dg-metric-label">Total Heures</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_tt4:
            st.markdown(f"""
            <div class="dg-metric">
                <div class="dg-metric-value">💰 {stats_tt['total_cout']:.0f}$</div>
                <div class="dg-metric-label">Coût Total</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Afficher les sessions récentes
        sessions = gestionnaire_bt.get_sessions_timetracker_bt(bt_id)
        if sessions:
            with st.expander("🕐 Sessions de Pointage Détaillées", expanded=True):
                st.markdown('<div class="dg-table-container">', unsafe_allow_html=True)
                
                for i, session in enumerate(sessions[:10], 1):  # Limiter à 10 sessions récentes
                    punch_out_display = session.get('punch_out', 'En cours')[:16] if session.get('punch_out') else "⏱️ En cours"
                    total_hours = session.get('total_hours', 0)
                    total_cost = session.get('total_cost', 0)
                    
                    # Status de la session
                    if session.get('punch_out'):
                        session_status = "✅ Terminée"
                        session_color = "#059669"
                    else:
                        session_status = "⏱️ En cours"
                        session_color = "#f59e0b"
                    
                    st.markdown(f"""
                    <div class="dg-table-row" style="border-left: 4px solid {session_color};">
                        <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 15px; align-items: center;">
                            <div>
                                <strong>👤 {session['employee_name']}</strong><br>
                                <small>{session.get('employee_poste', 'N/A')} - {session.get('employee_dept', 'N/A')}</small><br>
                                <small>📅 Du {session['punch_in'][:16]}</small><br>
                                <small>🏁 Au {punch_out_display}</small>
                            </div>
                            <div style="text-align: center;">
                                <span style="color: {session_color}; font-weight: 600;">{session_status}</span>
                            </div>
                            <div style="text-align: center;">
                                {"<strong>⏱️ " + f"{total_hours:.2f}h" + "</strong>" if total_hours > 0 else "➖"}
                            </div>
                            <div style="text-align: center;">
                                {"<strong>💰 " + f"{total_cost:.0f}$" + "</strong>" if total_cost > 0 else "➖"}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: #f0f9ff; border: 2px dashed #3b82f6; border-radius: 8px; padding: 20px; text-align: center;">
            <h4 style="color: #1e40af; margin: 0;">⏱️ Aucun pointage TimeTracker</h4>
            <p style="color: #3b82f6; margin: 10px 0;">Aucune session de pointage n'a encore été enregistrée sur ce Bon de Travail.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Section pour démarrer un pointage depuis le BT
    if st.session_state.get('timetracker_erp'):
        st.markdown("---")
        st.markdown("**🚀 Démarrer un nouveau pointage :**")
        
        # Récupérer les employés assignés à ce BT
        employes_assignes = gestionnaire_bt.get_employes_assignes_bt(bt_id)
        
        if employes_assignes:
            col_emp, col_btn = st.columns([3, 1])
            
            with col_emp:
                emp_options = [(e['id'], f"👤 {e['nom']} - {e['poste']} ({e['departement']})") for e in employes_assignes]
                selected_emp = st.selectbox(
                    "Employé à pointer",
                    options=[e[0] for e in emp_options],
                    format_func=lambda x: next((e[1] for e in emp_options if e[0] == x), ""),
                    key=f"select_emp_bt_{bt_id}"
                )
            
            with col_btn:
                if st.button("▶️ Démarrer Pointage", use_container_width=True, type="primary", key=f"start_pointage_bt_{bt_id}"):
                    if gestionnaire_bt.demarrer_pointage_bt(bt_id, selected_emp):
                        st.success("✅ Pointage démarré avec succès!")
                        st.info("🔄 Redirection vers TimeTracker...")
                        
                        # Redirection vers TimeTracker
                        st.session_state.page_redirect = "timetracker_page" 
                        st.session_state.show_formulaire_modal = False
                        st.session_state.selected_formulaire_id = None
                        
                        # Petit délai pour que l'utilisateur voie le message
                        import time
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors du démarrage du pointage")
                        st.error("Vérifiez que TimeTracker est actif et que l'employé n'a pas déjà un pointage en cours")
        else:
            st.warning("⚠️ Aucun employé assigné à ce Bon de Travail")
            st.info("💡 Assignez des employés dans la section équipe pour permettre le pointage")
    else:
        st.info("⚠️ TimeTracker non disponible - Impossible de démarrer un pointage")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ======================================================================
    # FIN SECTION INTÉGRATION TIMETRACKER
    # ======================================================================
    
    # Équipe assignée
    assignations = bt_details.get('assignations', [])
    if assignations:
        st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
        st.markdown('<h3 class="dg-info-title">👥 Équipe Assignée</h3>', unsafe_allow_html=True)
        
        for assignation in assignations:
            st.markdown(f"""
            <div class="dg-table-row">
                <strong>👤 {assignation['employe_nom']}</strong> - {assignation['poste']}<br>
                <small>📧 {assignation.get('email', 'N/A')} | 🏢 {assignation.get('departement', 'N/A')}</small><br>
                <small>📅 Assigné le {assignation['date_assignation'][:10]}</small>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Réservations de postes
    reservations = bt_details.get('reservations_postes', [])
    if reservations:
        st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
        st.markdown('<h3 class="dg-info-title">🏭 Postes de Travail Réservés</h3>', unsafe_allow_html=True)
        
        for reservation in reservations:
            statut_color = "#059669" if reservation['statut'] == 'LIBÉRÉ' else "#3b82f6"
            st.markdown(f"""
            <div class="dg-table-row">
                <strong>🏭 {reservation['poste_nom']}</strong><br>
                <small>🏢 {reservation.get('departement', 'N/A')} | 🔧 {reservation.get('type_machine', 'N/A')}</small><br>
                <small>📅 Réservé le {reservation['date_reservation'][:10]} | 
                <span style="color:{statut_color};font-weight:600;">● {reservation['statut']}</span></small>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Notes et instructions
    if bt_details.get('notes'):
        st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
        st.markdown('<h3 class="dg-info-title">📝 Instructions et Notes</h3>', unsafe_allow_html=True)
        
        notes_lines = bt_details['notes'].split('\n')
        for line in notes_lines:
            if line.strip():
                st.markdown(f"<p style='margin:5px 0;'>{line}</p>", unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Actions du BT
    st.markdown('<div class="dg-form-controls">', unsafe_allow_html=True)
    
    col_act1, col_act2, col_act3, col_act4 = st.columns(4)
    
    with col_act1:
        if bt_details['statut'] not in ['TERMINÉ', 'ANNULÉ']:
            if st.button("✅ Marquer Terminé", use_container_width=True, type="primary"):
                if gestionnaire_bt.marquer_bt_termine(bt_id, 1, "Marqué terminé depuis les détails"):
                    st.success("✅ BT marqué terminé!")
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la finalisation")
    
    with col_act2:
        if st.button("📊 TimeTracker", use_container_width=True):
            st.session_state.page_redirect = "timetracker_page"
            st.session_state.show_formulaire_modal = False
            st.rerun()
    
    with col_act3: 
        if st.button("🖨️ Imprimer", use_container_width=True):
            st.info("📄 Fonction d'impression en développement")
    
    with col_act4:
        if st.button("📄 Export PDF", use_container_width=True):
            st.info("📄 Fonction PDF en développement")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # main-content
    st.markdown('</div>', unsafe_allow_html=True)  # main-container


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


def render_bon_travail_form_dg(gestionnaire_bt):
    """
    Formulaire de création de Bon de Travail - Style DG Inc. fidèle au HTML avec données SQLite dynamiques
    
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
    
    # Récupération des données dynamiques depuis SQLite
    projets = get_projets_actifs()
    employes = get_employes_actifs()
    work_centers = get_work_centers_actifs()
    types_operations = get_types_operations_dynamiques()
    statuts_operations = get_statuts_operations()
    articles_inventaire = get_articles_inventaire()
    
    # Gestion des opérations/matériaux AVANT le formulaire (pour éviter les erreurs Streamlit)
    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
    st.markdown('<h3 class="dg-info-title">⚙️ Configuration du Bon de Travail</h3>', unsafe_allow_html=True)
    
    col_config1, col_config2 = st.columns(2)
    
    with col_config1:
        if st.button("🔄 Réinitialiser Formulaire", use_container_width=True, key="bt_reset_form"):
            # Supprimer toutes les clés de session liées au formulaire BT
            keys_to_remove = [key for key in st.session_state.keys() if key.startswith('bt_op_') or key.startswith('bt_mat_')]
            for key in keys_to_remove:
                del st.session_state[key]
            st.success("✅ Formulaire réinitialisé!")
            st.rerun()
    
    with col_config2:
        if st.button("📋 Aide Formulaire", use_container_width=True, key="bt_help"):
            st.info("""
            💡 **Conseils de remplissage:**
            - Sélectionnez un projet actif pour lier le BT
            - Définissez jusqu'à 5 opérations avec temps estimés
            - Ajoutez les matériaux nécessaires avec disponibilité
            - Complétez les instructions pour l'équipe
            """)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Vérifications préalables avec données dynamiques
    if not projets:
        st.error("❌ Aucun projet actif trouvé. Créez d'abord un projet dans le module Projets.")
        if st.button("🏗️ Aller aux Projets", use_container_width=True):
            st.session_state.form_action = "projects"  # À adapter selon votre navigation
        return
    
    if not employes:
        st.error("❌ Aucun employé actif trouvé. Vérifiez la base de données des employés.")
        return
    
    # Container principal style DG
    st.markdown('<div class="dg-main-container">', unsafe_allow_html=True)
    
    # En-tête DG
    render_dg_header()
    
    # Titre de section
    st.markdown('<h2 class="dg-section-title">Bon de Travail</h2>', unsafe_allow_html=True)
    
    # Contenu principal
    st.markdown('<div class="dg-main-content">', unsafe_allow_html=True)
    
    # Formulaire principal avec style DG et données dynamiques
    with st.form("bon_travail_form_dg", clear_on_submit=True):
        # Section informations de base - Style DG avec données SQLite
        st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
        st.markdown('<h3 class="dg-info-title">🔧 BON DE TRAVAIL</h3>', unsafe_allow_html=True)
        
        # Informations de base
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            numero_bt = gestionnaire_bt.base.generer_numero_document('BON_TRAVAIL')
            st.markdown(f"**Date de création:** {datetime.now().strftime('%Y-%m-%d')}")
            st.markdown(f"**N° Bon de Travail:** {numero_bt}")
            
            # Grille de formulaire DG
            st.markdown('<div class="dg-form-grid">', unsafe_allow_html=True)
            
            # Nom du projet (OBLIGATOIRE pour BT) - DONNÉES DYNAMIQUES
            projet_options = [("", "Sélectionner un projet")] + [(p['id'], f"#{p['id']} - {p['nom_projet']}") for p in projets]
            projet_id = st.selectbox(
                "Nom du projet *",
                options=[p[0] for p in projet_options],
                format_func=lambda x: next((p[1] for p in projet_options if p[0] == x), ""),
                help="Projet obligatoire pour les Bons de Travail"
            )
            
            # Client du projet - DONNÉES DYNAMIQUES
            if projet_id:
                projet_selectionne = next((p for p in projets if p['id'] == projet_id), None)
                if projet_selectionne:
                    # Récupérer le nom du client depuis la base
                    client_id = projet_selectionne.get('client_company_id')
                    if client_id:
                        try:
                            query_client = "SELECT nom FROM companies WHERE id = ?"
                            result_client = st.session_state.erp_db.execute_query(query_client, (client_id,))
                            client_nom = result_client[0]['nom'] if result_client else 'Client non trouvé'
                        except:
                            client_nom = projet_selectionne.get('client_nom_cache', 'N/A')
                    else:
                        client_nom = projet_selectionne.get('client_nom_cache', 'N/A')
                    
                    st.text_input("Client", value=client_nom, disabled=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_info2:
            # Chargé de projet (responsable) - DONNÉES DYNAMIQUES
            employe_options = [("", "Sélectionner...")] + [(e['id'], f"{e['prenom']} {e['nom']} - {e['poste']}") for e in employes]
            employe_id = st.selectbox(
                "Chargé de projet *",
                options=[e[0] for e in employe_options],
                format_func=lambda x: next((e[1] for e in employe_options if e[0] == x), "")
            )
            
            priorite = st.selectbox("Priorité", ["🟢 NORMAL", "🟡 URGENT", "🔴 CRITIQUE"], index=0)
            
            col_dates = st.columns(2)
            with col_dates[0]:
                date_debut = st.date_input("Date de début prévue", datetime.now().date())
            with col_dates[1]:
                date_fin = st.date_input("Date de fin prévue", datetime.now().date() + timedelta(days=7))
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Section Tâches et Opérations - Style DG avec données dynamiques
        st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
        st.markdown('<h3 class="dg-info-title">📋 Tâches et Opérations</h3>', unsafe_allow_html=True)
        
        # Affichage des opérations du projet sélectionné (si disponible)
        operations_projet = []
        if projet_id:
            try:
                operations_projet = get_operations_projet(projet_id)
                if operations_projet:
                    st.info(f"📋 {len(operations_projet)} opération(s) trouvée(s) dans le projet sélectionné")
                    
                    # Afficher les opérations du projet pour référence
                    with st.expander("🔍 Voir les opérations du projet", expanded=False):
                        for i, op in enumerate(operations_projet[:5], 1):  # Max 5 pour éviter l'encombrement
                            st.markdown(f"**{i}.** {op.get('description', 'N/A')} - Temps estimé: {op.get('temps_estime', 0)}h")
                            
            except Exception as e:
                st.warning(f"Impossible de récupérer les opérations du projet: {e}")
        
        # Interface pour opérations avec données dynamiques
        operations_data = []
        total_temps_prevu = 0
        total_temps_reel = 0
        
        st.markdown("**Opérations à réaliser :**")
        st.info("📋 Jusqu'à 5 opérations peuvent être définies pour ce Bon de Travail")
        
        # Nombre fixe d'opérations (5 lignes maximum) avec données dynamiques
        for i in range(5):
            with st.expander(f"Opération {i+1}", expanded=(i == 0)):
                cols = st.columns([2, 3, 1, 1, 1, 2])
                
                with cols[0]:
                    # Types d'opération dynamiques depuis la base
                    operation_options = [""] + types_operations
                    operation_type = st.selectbox(
                        "Type d'opération", 
                        operation_options,
                        key=f"bt_op_type_{i}"
                    )
                
                with cols[1]:
                    description = st.text_input("Description", key=f"bt_op_desc_{i}", 
                                               placeholder="Description détaillée de la tâche")
                
                with cols[2]:
                    quantite = st.number_input("Quantité", min_value=0, value=1 if i == 0 else 0, key=f"bt_op_qty_{i}")
                
                with cols[3]:
                    temps_prevu = st.number_input("Temps prévu (h)", min_value=0.0, step=0.25, 
                                                 key=f"bt_op_temps_{i}", format="%.2f")
                    if temps_prevu > 0:
                        total_temps_prevu += temps_prevu
                
                with cols[4]:
                    temps_reel = st.number_input("Temps réel (h)", min_value=0.0, step=0.25, 
                                               key=f"bt_op_reel_{i}", format="%.2f")
                    if temps_reel > 0:
                        total_temps_reel += temps_reel
                
                with cols[5]:
                    # Employés assignés - DONNÉES DYNAMIQUES
                    employe_assign_options = [""] + [f"{e['prenom']} {e['nom']}" for e in employes]
                    assigne = st.selectbox(
                        "Assigné à",
                        employe_assign_options,
                        key=f"bt_op_assign_{i}"
                    )
                
                # Dates, statut et poste de travail en ligne séparée avec données dynamiques
                cols2 = st.columns([1, 1, 1, 1])
                with cols2[0]:
                    statut_op = st.selectbox("Statut", statuts_operations, 
                                           key=f"bt_op_status_{i}")
                with cols2[1]:
                    date_debut_op = st.date_input("Date début", key=f"bt_op_start_{i}")
                with cols2[2]:
                    date_fin_op = st.date_input("Date fin", key=f"bt_op_end_{i}")
                with cols2[3]:
                    # Poste de travail - DONNÉES DYNAMIQUES
                    wc_options = [""] + [f"{wc['nom']} ({wc['departement']})" for wc in work_centers] if work_centers else [""]
                    poste_travail = st.selectbox("Poste de travail", wc_options, key=f"bt_op_wc_{i}")
                
                # Ajouter à la liste si rempli
                if operation_type and description and quantite > 0:
                    operations_data.append({
                        'operation': operation_type,
                        'description': description,
                        'quantite': quantite,
                        'temps_prevu': temps_prevu,
                        'temps_reel': temps_reel,
                        'assigne': assigne,
                        'statut': statut_op,
                        'date_debut': date_debut_op,
                        'date_fin': date_fin_op,
                        'poste_travail': poste_travail
                    })
        
        # Affichage des totaux
        if total_temps_prevu > 0 or total_temps_reel > 0:
            st.markdown(f"""
            <div class="total-row" style="padding: 15px; border-radius: 6px; margin-top: 15px; background: linear-gradient(135deg, #e6f7f1 0%, #d0f0e6 100%);">
                <strong>📊 TOTAUX OPÉRATIONS:</strong><br>
                ⏱️ Temps prévu total: <strong>{total_temps_prevu:.2f}h</strong><br>
                ⏱️ Temps réel total: <strong>{total_temps_reel:.2f}h</strong><br>
                📋 Opérations définies: <strong>{len(operations_data)}</strong><br>
                👥 Employés assignés: <strong>{len(set([op['assigne'] for op in operations_data if op['assigne']]))}</strong>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Section Matériaux et Outils - Style DG avec données dynamiques
        st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
        st.markdown('<h3 class="dg-info-title">📝 Matériaux et Outils Requis</h3>', unsafe_allow_html=True)
        
        # Affichage des matériaux du projet sélectionné (si disponible)
        materiaux_projet = []
        if projet_id:
            try:
                materiaux_projet = get_materiaux_projet(projet_id)
                if materiaux_projet:
                    st.info(f"📦 {len(materiaux_projet)} matériau(x) trouvé(s) dans le projet sélectionné")
                    
                    # Afficher les matériaux du projet pour référence
                    with st.expander("🔍 Voir les matériaux du projet", expanded=False):
                        for i, mat in enumerate(materiaux_projet[:5], 1):  # Max 5 pour éviter l'encombrement
                            st.markdown(f"**{i}.** {mat.get('description', 'N/A')} - Qté: {mat.get('quantite', 0)} {mat.get('unite', '')}")
                            
            except Exception as e:
                st.warning(f"Impossible de récupérer les matériaux du projet: {e}")
        
        # Interface pour matériaux avec données dynamiques
        materiaux_data = []
        
        st.markdown("**Matériaux et outils requis :**")
        st.info("📦 Jusqu'à 5 matériaux/outils peuvent être définis pour ce Bon de Travail")
        
        # Recherche dans l'inventaire pour aide
        col_search1, col_search2 = st.columns(2)
        with col_search1:
            search_term = st.text_input("🔍 Rechercher dans l'inventaire", 
                                       placeholder="Tapez pour rechercher...",
                                       key="bt_search_inventory")
        
        with col_search2:
            if search_term and len(search_term) >= 2:
                resultats = search_articles_inventaire(search_term)
                if resultats:
                    st.success(f"✅ {len(resultats)} article(s) trouvé(s)")
                else:
                    st.warning("❌ Aucun article trouvé")
        
        # Nombre fixe de matériaux (5 lignes maximum) avec données dynamiques
        for i in range(5):
            with st.expander(f"Matériau/Outil {i+1}", expanded=(i == 0)):
                cols = st.columns([3, 3, 1, 1, 2])
                
                with cols[0]:
                    # Suggestions depuis l'inventaire pour le nom
                    suggestions_noms = []
                    if articles_inventaire:
                        suggestions_noms = [art['nom'] for art in articles_inventaire[:10]]  # Top 10
                    
                    nom_materiau = st.text_input("Nom du matériau/outil", key=f"bt_mat_nom_{i}", 
                                               placeholder="Ex: Tôle acier, Électrodes...")
                    
                    # Afficher suggestions si disponibles
                    if i == 0 and suggestions_noms:  # Seulement pour le premier pour éviter l'encombrement
                        with st.expander("💡 Suggestions depuis l'inventaire", expanded=False):
                            for sugg in suggestions_noms[:5]:
                                if st.button(f"📦 {sugg}", key=f"suggestion_{i}_{sugg}"):
                                    st.session_state[f"bt_mat_nom_{i}"] = sugg
                                    st.rerun()
                
                with cols[1]:
                    desc_materiau = st.text_input("Description", key=f"bt_mat_desc_{i}", 
                                                 placeholder="Description détaillée")
                
                with cols[2]:
                    qty_materiau = st.number_input("Quantité", min_value=0.0, step=0.1, 
                                                  value=1.0 if i == 0 else 0.0, key=f"bt_mat_qty_{i}", format="%.1f")
                
                with cols[3]:
                    # Unités depuis les types définis + unités dynamiques de l'inventaire
                    unites_base = list(UNITES_MESURE.keys()) if hasattr(st.session_state, 'UNITES_MESURE') else [
                        "Pièces", "Kilogrammes", "Mètres", "Mètres²", "Litres", "Heures"
                    ]
                    
                    # Ajouter unités depuis l'inventaire
                    try:
                        query_unites = "SELECT DISTINCT unite FROM materials WHERE unite IS NOT NULL AND unite != ''"
                        unites_db = st.session_state.erp_db.execute_query(query_unites)
                        unites_inventaire = [u['unite'] for u in unites_db if u['unite']]
                        unites_disponibles = sorted(list(set(unites_base + unites_inventaire)))
                    except:
                        unites_disponibles = unites_base
                    
                    unite_materiau = st.selectbox(
                        "Unité",
                        unites_disponibles,
                        key=f"bt_mat_unit_{i}"
                    )
                
                with cols[4]:
                    # Vérification de disponibilité avec données réelles si possible
                    disponible = st.selectbox(
                        "Disponibilité",
                        ["✅ Disponible", "❌ Non disponible", "⚠️ Partiellement", "📦 À commander", "🔍 À vérifier"],
                        key=f"bt_mat_dispo_{i}"
                    )
                
                # Notes et informations complémentaires
                cols3 = st.columns([2, 1])
                with cols3[0]:
                    notes_materiau = st.text_input("Notes spéciales", key=f"bt_mat_notes_{i}", 
                                                 placeholder="Instructions particulières, contraintes...")
                
                with cols3[1]:
                    # Vérification stock réel si article trouvé dans l'inventaire
                    if nom_materiau and articles_inventaire:
                        article_trouve = next((art for art in articles_inventaire if art['nom'].lower() == nom_materiau.lower()), None)
                        if article_trouve:
                            statut_stock = article_trouve.get('statut', 'INCONNU')
                            couleur_statut = "#10b981" if statut_stock == "DISPONIBLE" else "#ef4444" if statut_stock in ["ÉPUISÉ", "CRITIQUE"] else "#f59e0b"
                            st.markdown(f'<span style="color:{couleur_statut};font-weight:600;">● {statut_stock}</span>', unsafe_allow_html=True)
                
                # Ajouter à la liste si rempli
                if nom_materiau and qty_materiau > 0:
                    materiaux_data.append({
                        'nom': nom_materiau,
                        'description': desc_materiau,
                        'quantite': qty_materiau,
                        'unite': unite_materiau,
                        'disponible': disponible,
                        'notes': notes_materiau
                    })
        
        # Résumé des matériaux avec statuts réels
        if materiaux_data:
            disponibles = len([m for m in materiaux_data if '✅' in m['disponible']])
            non_disponibles = len([m for m in materiaux_data if '❌' in m['disponible']])
            a_commander = len([m for m in materiaux_data if '📦' in m['disponible']])
            
            st.markdown(f"""
            <div class="total-row" style="padding: 15px; border-radius: 6px; margin-top: 15px; background: linear-gradient(135deg, #fef3e7 0%, #fefaf3 100%);">
                <strong>📦 RÉSUMÉ MATÉRIAUX:</strong><br>
                📋 Éléments définis: <strong>{len(materiaux_data)}</strong><br>
                ✅ Disponibles: <strong>{disponibles}</strong><br>
                ❌ Non disponibles: <strong>{non_disponibles}</strong><br>
                📦 À commander: <strong>{a_commander}</strong>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Section Instructions et Notes - Style DG
        st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
        st.markdown('<h3 class="dg-info-title">📄 Instructions et Notes</h3>', unsafe_allow_html=True)
        
        instructions = st.text_area("Instructions de travail", height=100,
                                   placeholder="Instructions détaillées pour l'exécution du travail...")
        
        notes_securite = st.text_area("Notes de sécurité", height=80,
                                     placeholder="Consignes de sécurité particulières...")
        
        qualite = st.text_area("Exigences qualité", height=80,
                              placeholder="Standards et contrôles qualité requis...")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Boutons de soumission - Style DG identique au HTML
        st.markdown('<div class="dg-form-controls">', unsafe_allow_html=True)
        col_submit1, col_submit2, col_submit3, col_submit4 = st.columns(4)
        
        with col_submit1:
            submit_sauvegarder = st.form_submit_button("💾 Sauvegarder Bon de Travail", use_container_width=True)
        with col_submit2:
            submit_imprimer = st.form_submit_button("🖨️ Imprimer", use_container_width=True)
        with col_submit3:
            submit_pdf = st.form_submit_button("📄 Exporter PDF", use_container_width=True)
        with col_submit4:
            submit_nouveau = st.form_submit_button("🗑️ Nouveau Bon", use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Traitement de la soumission avec données dynamiques
        if submit_sauvegarder:
            if not projet_id or not employe_id or not instructions:
                st.error("❌ Veuillez remplir tous les champs obligatoires (*)")
                return
            
            # Construction des données avec informations enrichies
            notes_completes = f"""=== BON DE TRAVAIL DG INC. ===
Numéro: {numero_bt}
Projet: {next((p['nom_projet'] for p in projets if p['id'] == projet_id), 'N/A')}
Responsable: {next((f"{e['prenom']} {e['nom']}" for e in employes if e['id'] == employe_id), 'N/A')}

Instructions : {instructions}

=== OPÉRATIONS ({len(operations_data)}) ===
{chr(10).join([f"- {op['operation']}: {op['description']} ({op['temps_prevu']}h)" for op in operations_data])}

=== MATÉRIAUX ET OUTILS ({len(materiaux_data)}) ===
{chr(10).join([f"- {mat['nom']}: {mat['quantite']} {mat['unite']} ({mat['disponible']})" for mat in materiaux_data])}

=== NOTES DE SÉCURITÉ ===
{notes_securite or 'Standards DG Inc. - Aucune consigne particulière'}

=== EXIGENCES QUALITÉ ===
{qualite or 'Standards DG Inc. applicables'}

=== ASSIGNATIONS ===
Employés assignés: {', '.join(set([op['assigne'] for op in operations_data if op['assigne']]))}
Postes de travail: {', '.join(set([op['poste_travail'] for op in operations_data if op['poste_travail']]))}
"""
            
            # Extraction de la priorité (enlever l'emoji)
            priorite_clean = priorite.split(' ')[1] if ' ' in priorite else priorite.replace('🟢', '').replace('🟡', '').replace('🔴', '').strip()
            
            data = {
                'type_formulaire': 'BON_TRAVAIL',
                'numero_document': numero_bt,
                'project_id': projet_id,
                'employee_id': employe_id,
                'statut': 'BROUILLON',
                'priorite': priorite_clean,
                'date_creation': date_debut,
                'date_echeance': date_fin,
                'montant_total': 0,  # Calculé plus tard si nécessaire
                'notes': notes_completes,
                'operations_selectionnees': [op['operation'] for op in operations_data],
                'employes_assignes': list(set([op['assigne'] for op in operations_data if op['assigne']])),
                'work_centers_utilises': list(set([op['poste_travail'] for op in operations_data if op['poste_travail']])),
                'description': instructions,
                'temps_estime_total': sum(op['temps_prevu'] for op in operations_data),
                'materiaux_requis': materiaux_data,
                'operations_detaillees': operations_data
            }
            
            bt_id = gestionnaire_bt.creer_bon_travail(data)
            
            if bt_id:
                st.session_state.bt_creation_success = {
                    'bt_id': bt_id,
                    'numero': numero_bt,
                    'urgent': priorite_clean in ['URGENT', 'CRITIQUE']
                }
                st.rerun()
        
        elif submit_nouveau:
            # Réinitialiser le formulaire (les champs seront vides au prochain chargement)
            st.info("🗑️ Formulaire réinitialisé. Rechargez la page pour un nouveau BT.")
            st.rerun()
        
        elif submit_imprimer:
            st.info("🖨️ Fonction d'impression en développement. Utilisez l'export PDF pour l'instant.")
        
        elif submit_pdf:
            st.info("📄 Fonction PDF en développement. Utilisez l'impression pour l'instant.")
    
    # Footer DG - Identique au HTML
    st.markdown("""
    <div class="dg-footer">
        <p><strong>📋 Statut:</strong> <span class="dg-status-badge status-draft">Brouillon</span></p>
        <p><strong>👤 Créé par:</strong> Utilisateur</p>
        <p><strong>📞 Contact urgence:</strong> (450) 372-9630</p>
        <p><strong>📊 Données:</strong> Base SQLite dynamique</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Fin main-content
    st.markdown('</div>', unsafe_allow_html=True)  # Fin main-container


def render_bon_travail_list_dg(gestionnaire_bt):
    """
    Liste des Bons de Travail avec style DG Inc. fidèle au HTML
    
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
    
    # Tableau de bord rapide - Style DG identique au HTML
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
    
    # Liste des BT récents style DG - Identique au HTML
    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
    st.markdown('<h3 class="dg-info-title">🔧 Bons de Travail Récents</h3>', unsafe_allow_html=True)
    
    # Afficher les BT avec style HTML
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
                        <span>{bt.get('project_nom', 'N/A')}</span>
                    </div>
                    <div>
                        <strong>👤 Responsable:</strong><br>
                        <span>{bt.get('employee_nom', 'N/A')}</span>
                    </div>
                    <div>
                        <strong>📅 Création:</strong><br>
                        <span>{bt.get('date_creation', 'N/A')}</span>
                    </div>
                    <div>
                        <strong>🏁 Échéance:</strong><br>
                        <span>{bt.get('date_echeance', 'N/A')}</span>
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
                </div>
                
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Boutons fonctionnels avec Streamlit (CORRECTION INDENTATION)
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        
        with col_btn1:
            if st.button("👁️ Voir", key=f"voir_bt_{bt['id']}", use_container_width=True):
                st.session_state.selected_formulaire_id = bt['id']
                st.session_state.show_formulaire_modal = True
                st.rerun()
        
        with col_btn2:
            if st.button("✏️ Modifier", key=f"modifier_bt_{bt['id']}", use_container_width=True):
                st.info("Fonction de modification en développement")
        
        with col_btn3:
            if st.button("📊 Avancement", key=f"avancement_bt_{bt['id']}", use_container_width=True):
                st.info("Fonction de suivi d'avancement en développement")
        
        with col_btn4:
            if bt['statut'] in ['VALIDÉ', 'EN COURS'] and avancement >= 90:
                if st.button("✅ Terminer", key=f"terminer_bt_{bt['id']}", use_container_width=True):
                    if gestionnaire_bt.marquer_bt_termine(bt['id'], 1, "Marqué terminé depuis la liste"):
                        st.success("✅ BT terminé!")
                        st.rerun()
            else:
                st.button("✅ Terminer", key=f"terminer_bt_{bt['id']}", disabled=True, use_container_width=True, help="BT pas prêt à être terminé")
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Actions rapides - Style DG
    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
    st.markdown('<h3 class="dg-info-title">🔧 Actions sur un BT</h3>', unsafe_allow_html=True)
    
    # Sélection d'un BT pour actions
    if bons_travail:
        bt_options = [(bt['id'], f"BT {bt['numero_document']} - {bt.get('project_nom', 'N/A')}") for bt in bons_travail]
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
                if selected_bt['statut'] in ['VALIDÉ', 'EN COURS'] and selected_bt.get('avancement', {}).get('pourcentage', 0) == 100:
                    if st.button("✅ Terminer", use_container_width=True, key=f"bt_terminer_{selected_bt_id}"):
                        if gestionnaire_bt.marquer_bt_termine(selected_bt_id, 1, "Marqué terminé depuis la liste"):
                            st.success("✅ BT terminé!")
                            st.rerun()
                else:
                    st.button("✅ Terminer", disabled=True, use_container_width=True, help="BT pas prêt à être terminé")
            
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
    Statistiques détaillées spécifiques aux BT avec style DG Inc.
    
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
    
    # Métriques principales - Style DG
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="dg-metric">
            <div class="dg-metric-value">📋 {len(bons_travail)}</div>
            <div class="dg-metric-label">Total BT</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        en_cours = stats.get('en_cours', 0)
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
        projets_concernes = stats.get('projets_concernes', 0)
        st.markdown(f"""
        <div class="dg-metric">
            <div class="dg-metric-value">🏗️ {projets_concernes}</div>
            <div class="dg-metric-label">Projets Concernés</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Graphiques spécifiques BT - Style DG
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
                        title="📊 Répartition par Statut", 
                        color_discrete_map=colors_statut)
            fig.update_layout(showlegend=True, height=350, 
                             plot_bgcolor='rgba(0,0,0,0)', 
                             paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_g2:
        st.markdown('<div class="dg-section-card">', unsafe_allow_html=True)
        
        # Analyse par projet
        projet_stats = {}
        for bt in bons_travail:
            projet = bt.get('project_nom', 'Projet non défini')
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
                        title="📈 BT par Projet", color_continuous_scale='RdYlGn')
            fig.update_layout(height=350,
                             plot_bgcolor='rgba(0,0,0,0)', 
                             paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Analyse de productivité - Style DG
    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
    st.markdown('<h3 class="dg-info-title">📈 Analyse de Productivité</h3>', unsafe_allow_html=True)
    
    col_prod1, col_prod2 = st.columns(2)
    
    with col_prod1:
        # BT par responsable
        responsable_stats = {}
        for bt in bons_travail:
            responsable = bt.get('employee_nom', 'Non assigné')
            if responsable not in responsable_stats:
                responsable_stats[responsable] = {'total': 0, 'termines': 0}
            responsable_stats[responsable]['total'] += 1
            if bt['statut'] == 'TERMINÉ':
                responsable_stats[responsable]['termines'] += 1
        
        st.markdown("**Top Responsables BT :**")
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
        # Évolution mensuelle
        evolution_mensuelle = {}
        for bt in bons_travail:
            try:
                mois = bt['date_creation'][:7]  # YYYY-MM
                if mois not in evolution_mensuelle:
                    evolution_mensuelle[mois] = 0
                evolution_mensuelle[mois] += 1
            except:
                continue
        
        if evolution_mensuelle:
            mois_sorted = sorted(evolution_mensuelle.items())[-6:]  # 6 derniers mois
            df_evolution = pd.DataFrame(mois_sorted, columns=['Mois', 'Nombre BT'])
            
            fig = px.line(df_evolution, x='Mois', y='Nombre BT',
                         title="Évolution Mensuelle des BT",
                         markers=True, color_discrete_sequence=['#00A971'])
            fig.update_layout(height=300,
                             plot_bgcolor='rgba(0,0,0,0)', 
                             paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_rapport_productivite_dg(gestionnaire_bt):
    """
    Rapport de productivité détaillé pour les BT avec style DG Inc.
    
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
                st.success(f"✅ Rapport généré pour {rapport['periode']}")
                
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
                    st.markdown(f"""
                    <div class="dg-metric">
                        <div class="dg-metric-value">{rapport['date_generation'][:10]}</div>
                        <div class="dg-metric-label">Date Génération</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Détail par employé - Style DG
                if rapport['employes']:
                    st.markdown('<br>', unsafe_allow_html=True)
                    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
                    st.markdown('<h3 class="dg-info-title">👥 Détail par Employé</h3>', unsafe_allow_html=True)
                    
                    df_employes = pd.DataFrame(rapport['employes'])
                    df_employes['duree_moyenne'] = df_employes['duree_moyenne'].round(1)
                    df_employes['montant_total_travaux'] = df_employes['montant_total_travaux'].apply(lambda x: f"{x:,.0f}$")
                    
                    # Affichage tableau avec style
                    st.markdown('<div class="dg-table-container">', unsafe_allow_html=True)
                    st.dataframe(df_employes, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Analyse et recommandations - Style DG
                if rapport.get('analyse'):
                    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
                    st.markdown('<h3 class="dg-info-title">📊 Analyse des Performances</h3>', unsafe_allow_html=True)
                    
                    if 'top_performer' in rapport['analyse']:
                        top_perf = rapport['analyse']['top_performer']
                        st.markdown(f"**🏆 Top Performer:** {top_perf['employe_nom']} ({top_perf['nb_bt_termines']} BT terminés)")
                    
                    if 'plus_efficace' in rapport['analyse']:
                        efficace = rapport['analyse']['plus_efficace']
                        st.markdown(f"**⚡ Plus Efficace:** {efficace['employe_nom']} ({efficace['duree_moyenne']:.1f} jours/BT)")
                    
                    if 'plus_rentable' in rapport['analyse']:
                        rentable = rapport['analyse']['plus_rentable']
                        st.markdown(f"**💰 Plus Rentable:** {rentable['employe_nom']} ({rentable['montant_total_travaux']:,.0f}$ de travaux)")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Recommandations - Style DG
                if rapport.get('recommandations'):
                    st.markdown('<div class="dg-info-section">', unsafe_allow_html=True)
                    st.markdown('<h3 class="dg-info-title">💡 Recommandations</h3>', unsafe_allow_html=True)
                    
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
        "📊 Suivez régulièrement l'avancement des BT en cours",
        "👥 Équilibrez la charge de travail entre les employés",
        "⏱️ Identifiez les BT qui prennent plus de temps que prévu",
        "🔧 Optimisez l'assignation des postes de travail",
        "📋 Assurez-vous que les opérations sont bien définies dans les projets",
        "🏭 Utilisez les données pour améliorer les processus DG Inc.",
        "📈 Analysez les tendances mensuelles pour planifier les ressources",
        "🎯 Concentrez-vous sur les BT prioritaires et urgents",
        "🔍 Utilisez les données d'inventaire pour optimiser les matériaux",
        "📞 Maintenez une communication efficace avec l'équipe"
    ]
    
    for conseil in conseils:
        st.markdown(f"""
        <div style="background:#f0f9ff;border-left:4px solid var(--primary-color);padding:10px;margin:5px 0;border-radius:6px;">
            {conseil}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
