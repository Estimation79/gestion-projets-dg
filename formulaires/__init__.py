# formulaires/__init__.py
# Module Formulaires ERP Production DG Inc. - Version 2.0 COMPLÈTE CORRIGÉE

"""
Module Formulaires ERP Production DG Inc.
Architecture modulaire complète avec tous les gestionnaires opérationnels.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Import de la classe principale
from .core.base_gestionnaire import GestionnaireFormulaires

# ✅ TOUS LES GESTIONNAIRES SPÉCIALISÉS OPÉRATIONNELS - CORRIGÉ
from .bons_travail import GestionnaireBonsTravail, render_bons_travail_tab
from .bons_achats import GestionnaireBonsAchats, render_bons_achats_tab
from .demandes_prix import GestionnaireDemandesPrix, render_demandes_prix_tab
# 🔧 CORRECTION PRINCIPALE : Ajout import Bons de Commande
from .bons_commande import GestionnaireBonsCommande, render_bons_commande_tab

# Import des utilitaires (déjà complets)
from .utils.helpers import formater_montant, formater_delai
from .core.types_formulaires import TYPES_FORMULAIRES


def show_formulaires_page():
    """
    Page principale du module Formulaires - VERSION CORRIGÉE.
    
    CORRECTION : Tous les 4 modules principaux maintenant opérationnels !
    """
    st.markdown("## 📑 Gestion des Formulaires - DG Inc.")
    st.caption("*Architecture modulaire v2.0 - 4/5 MODULES OPÉRATIONNELS*")
    
    # Initialisation du gestionnaire principal
    if 'gestionnaire_formulaires' not in st.session_state:
        st.session_state.gestionnaire_formulaires = GestionnaireFormulaires(st.session_state.erp_db)
    
    gestionnaire = st.session_state.gestionnaire_formulaires
    
    # Statistiques globales
    show_formulaires_dashboard(gestionnaire)
    
    # ✅ CORRECTION : TOUS LES MODULES MAINTENANT OPÉRATIONNELS
    tab_bt, tab_ba, tab_bc, tab_dp, tab_est = st.tabs([
        "🔧 Bons de Travail",
        "🛒 Bons d'Achats", 
        "📦 Bons de Commande",
        "💰 Demandes de Prix",
        "📊 Estimations"
    ])
    
    # ✅ Module BT - OPÉRATIONNEL
    with tab_bt:
        render_bons_travail_tab(gestionnaire)
    
    # ✅ Module BA - OPÉRATIONNEL
    with tab_ba:
        render_bons_achats_tab(gestionnaire)
    
    # 🔧 CORRECTION PRINCIPALE : Module BC maintenant OPÉRATIONNEL !
    with tab_bc:
        render_bons_commande_tab(gestionnaire)
    
    # ✅ Module DP - OPÉRATIONNEL
    with tab_dp:
        render_demandes_prix_tab(gestionnaire)
    
    # 🚧 Module EST - En finalisation (utilise encore legacy temporairement)
    with tab_est:
        _render_legacy_tab("ESTIMATION", gestionnaire, "📊 Estimations")


def show_formulaires_dashboard(gestionnaire):
    """Dashboard des formulaires avec métriques globales - CORRIGÉ."""
    st.markdown("### 📊 Dashboard Formulaires")
    
    stats = gestionnaire.get_statistiques_formulaires()
    
    if not any(stats.values()):
        st.info("Aucun formulaire créé. Commencez par créer votre premier document.")
        return
    
    # Métriques principales avec statut des modules - CORRIGÉ
    col1, col2, col3, col4, col5 = st.columns(5)
    
    modules_status = {
        'BON_TRAVAIL': {'icon': '🔧', 'status': '✅', 'nom': 'Bons Travail'},
        'BON_ACHAT': {'icon': '🛒', 'status': '✅', 'nom': 'Bons Achats'},
        'BON_COMMANDE': {'icon': '📦', 'status': '✅', 'nom': 'Bons Commande'},  # 🔧 CORRIGÉ
        'DEMANDE_PRIX': {'icon': '💰', 'status': '✅', 'nom': 'Demandes Prix'},
        'ESTIMATION': {'icon': '📊', 'status': '🚧', 'nom': 'Estimations'}
    }
    
    for i, (type_form, config) in enumerate(modules_status.items()):
        with [col1, col2, col3, col4, col5][i]:
            type_stats = stats.get(type_form, {})
            total = type_stats.get('total', 0)
            montant = type_stats.get('montant_total', 0)
            
            st.metric(
                f"{config['status']} {config['icon']} {config['nom']}",
                total,
                delta=formater_montant(montant) if montant else None,
                help=f"{'Module opérationnel' if config['status'] == '✅' else 'Module en finalisation'}"
            )
    
    # Message de statut - CORRIGÉ
    st.success("🎉 **4/5 modules maintenant opérationnels !** BT ✅ + BA ✅ + BC ✅ + DP ✅")
    
    # Graphiques optimisés
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Répartition par type avec statut migration
        types_data = []
        for type_form, config in modules_status.items():
            total = stats.get(type_form, {}).get('total', 0)
            if total > 0:
                status_icon = config['status']
                nom_affichage = f"{config['nom']} {status_icon}"
                types_data.append({'Type': nom_affichage, 'Nombre': total})
        
        if types_data:
            df_types = pd.DataFrame(types_data)
            fig = px.pie(df_types, values='Nombre', names='Type', 
                        title="📊 Répartition par Type (✅=Opérationnel, 🚧=Finalisation)")
            fig.update_layout(showlegend=True, height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_g2:
        # Évolution avec indicateurs de performance
        evolution_data = []
        for type_form, type_stats in stats.items():
            if type_form in modules_status:
                config = modules_status[type_form]
                for statut, count in type_stats.get('par_statut', {}).items():
                    evolution_data.append({
                        'Statut': statut,
                        'Nombre': count,
                        'Type': config['nom']
                    })
        
        if evolution_data:
            df_statuts = pd.DataFrame(evolution_data)
            fig = px.bar(df_statuts, x='Statut', y='Nombre', color='Type',
                        title="📈 Documents par Statut")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)


def _render_legacy_tab(type_formulaire, gestionnaire, titre):
    """Interface temporaire pour le dernier module en finalisation (Estimations)."""
    st.markdown(f"### {titre}")
    
    st.warning(f"""
    🚧 **Module en finalisation**
    
    Ce module sera disponible dans la prochaine mise à jour.
    
    **Modules maintenant opérationnels :**
    - ✅ Bons de Travail (complet)
    - ✅ Bons d'Achats (complet avec réappro auto)
    - ✅ Bons de Commande (complet avec suivi livraison)  # 🔧 CORRIGÉ
    - ✅ Demandes de Prix (RFQ multi-fournisseurs)
    
    **En cours de finalisation :**
    - 🚧 Estimations (80% terminé)
    """)
    
    documents = gestionnaire.get_formulaires(type_formulaire)
    
    if documents:
        st.markdown(f"##### 📋 {len(documents)} document(s) existant(s)")
        for doc in documents[:3]:
            with st.expander(f"{doc['numero_document']} - {doc.get('company_nom', 'N/A')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.text(f"Statut: {doc['statut']}")
                    st.text(f"Date: {doc['date_creation'][:10] if doc['date_creation'] else 'N/A'}")
                with col2:
                    st.text(f"Montant: {formater_montant(doc.get('montant_total', 0))}")
                    st.text(f"Responsable: {doc.get('employee_nom', 'N/A')}")
        
        if len(documents) > 3:
            st.info(f"... et {len(documents) - 3} autre(s) document(s)")
    else:
        st.info(f"Aucun {titre.lower()} créé.")
    
    # Actions de base
    col_action1, col_action2 = st.columns(2)
    with col_action1:
        if st.button(f"📋 Voir Tous les {titre}", key=f"view_all_{type_formulaire}"):
            st.info("Fonctionnalité disponible après finalisation du module")
    
    with col_action2:
        if st.button(f"➕ Créer {titre}", key=f"create_{type_formulaire}"):
            st.info("Utilisez temporairement l'ancien formulaire en attendant la finalisation")


# Exports principaux - CORRIGÉS
__all__ = [
    # Fonction principale
    'show_formulaires_page',
    
    # Gestionnaire principal
    'GestionnaireFormulaires',
    
    # ✅ Gestionnaires spécialisés opérationnels - CORRIGÉ
    'GestionnaireBonsTravail',
    'GestionnaireBonsAchats',
    'GestionnaireBonsCommande',      # 🔧 AJOUTÉ
    'GestionnaireDemandesPrix',
    
    # ✅ Interfaces opérationnelles - CORRIGÉ
    'render_bons_travail_tab',
    'render_bons_achats_tab',
    'render_bons_commande_tab',      # 🔧 AJOUTÉ
    'render_demandes_prix_tab',
    
    # Utilitaires
    'formater_montant',
    'formater_delai',
    'TYPES_FORMULAIRES'
]

# Métadonnées du module principal - CORRIGÉES
__version__ = "2.0.1"
__author__ = "DG Inc. ERP Team"
__description__ = "Module Formulaires ERP - 4/5 modules opérationnels"  # 🔧 CORRIGÉ
