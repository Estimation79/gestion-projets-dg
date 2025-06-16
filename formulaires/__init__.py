# formulaires/__init__.py
# Module Formulaires ERP Production DG Inc. - Version 2.0 FINALE COMPLÈTE

"""
Module Formulaires ERP Production DG Inc.
Architecture modulaire complète avec TOUS les gestionnaires opérationnels.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Import de la classe principale
from .core.base_gestionnaire import GestionnaireFormulaires

# ✅ TOUS LES 5 GESTIONNAIRES SPÉCIALISÉS OPÉRATIONNELS - VERSION FINALE
from .bons_travail import GestionnaireBonsTravail, render_bons_travail_tab
from .bons_achats import GestionnaireBonsAchats, render_bons_achats_tab
from .bons_commande import GestionnaireBonsCommande, render_bons_commande_tab
from .demandes_prix import GestionnaireDemandesPrix, render_demandes_prix_tab
from .estimations import GestionnaireEstimations, render_estimations_tab  # 🎉 AJOUTÉ

# Import des utilitaires (déjà complets)
from .utils.helpers import formater_montant, formater_delai
from .core.types_formulaires import TYPES_FORMULAIRES


def show_formulaires_page():
    """
    Page principale du module Formulaires - VERSION FINALE COMPLÈTE.
    
    🎉 TOUS LES 5 MODULES MAINTENANT OPÉRATIONNELS !
    """
    st.markdown("## 📑 Gestion des Formulaires - DG Inc.")
    st.caption("*Architecture modulaire v2.0 - 5/5 MODULES OPÉRATIONNELS*")
    
    # Initialisation du gestionnaire principal
    if 'gestionnaire_formulaires' not in st.session_state:
        st.session_state.gestionnaire_formulaires = GestionnaireFormulaires(st.session_state.erp_db)
    
    gestionnaire = st.session_state.gestionnaire_formulaires
    
    # Statistiques globales
    show_formulaires_dashboard(gestionnaire)
    
    # ✅ TOUS LES 5 MODULES MAINTENANT OPÉRATIONNELS
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
    
    # ✅ Module BC - OPÉRATIONNEL
    with tab_bc:
        render_bons_commande_tab(gestionnaire)
    
    # ✅ Module DP - OPÉRATIONNEL
    with tab_dp:
        render_demandes_prix_tab(gestionnaire)
    
    # 🎉 Module EST - MAINTENANT OPÉRATIONNEL !
    with tab_est:
        render_estimations_tab(gestionnaire)


def show_formulaires_dashboard(gestionnaire):
    """Dashboard des formulaires avec métriques globales - VERSION FINALE."""
    st.markdown("### 📊 Dashboard Formulaires")
    
    stats = gestionnaire.get_statistiques_formulaires()
    
    if not any(stats.values()):
        st.info("Aucun formulaire créé. Commencez par créer votre premier document.")
        return
    
    # Métriques principales avec TOUS les modules - VERSION FINALE
    col1, col2, col3, col4, col5 = st.columns(5)
    
    modules_status = {
        'BON_TRAVAIL': {'icon': '🔧', 'status': '✅', 'nom': 'Bons Travail'},
        'BON_ACHAT': {'icon': '🛒', 'status': '✅', 'nom': 'Bons Achats'},
        'BON_COMMANDE': {'icon': '📦', 'status': '✅', 'nom': 'Bons Commande'},
        'DEMANDE_PRIX': {'icon': '💰', 'status': '✅', 'nom': 'Demandes Prix'},
        'ESTIMATION': {'icon': '📊', 'status': '✅', 'nom': 'Estimations'}  # 🎉 MAINTENANT OPÉRATIONNEL
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
                help="Module opérationnel complet"
            )
    
    # Message de statut - VERSION FINALE
    st.success("🎉 **TOUS LES MODULES OPÉRATIONNELS !** BT ✅ + BA ✅ + BC ✅ + DP ✅ + EST ✅")
    st.info("🚀 **Architecture modulaire complète** : Gestion intégrale des documents DG Inc.")
    
    # Graphiques optimisés
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Répartition par type avec statut complet
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
                        title="📊 Répartition par Type (✅=Opérationnel)")
            fig.update_layout(showlegend=True, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Créez vos premiers documents pour voir les statistiques.")
    
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
        else:
            st.info("Données des statuts disponibles après création de documents.")
    
    # NOUVEAU : Métriques avancées avec tous les modules
    if any(stats.values()):
        st.markdown("---")
        st.markdown("### 💼 Métriques Avancées")
        
        col_av1, col_av2, col_av3, col_av4 = st.columns(4)
        
        with col_av1:
            # Total CA tous types
            ca_total = sum(
                type_stats.get('montant_total', 0) 
                for type_stats in stats.values() 
                if isinstance(type_stats, dict)
            )
            st.metric("💰 CA Total Documents", f"{ca_total:,.0f}$ CAD")
        
        with col_av2:
            # Documents en cours
            docs_actifs = sum(
                len(type_stats.get('par_statut', {}).get('VALIDÉ', [])) + 
                len(type_stats.get('par_statut', {}).get('ENVOYÉ', []))
                for type_stats in stats.values() 
                if isinstance(type_stats, dict)
            )
            st.metric("📄 Documents Actifs", docs_actifs)
        
        with col_av3:
            # Taux de completion globale
            total_docs = sum(
                type_stats.get('total', 0) 
                for type_stats in stats.values() 
                if isinstance(type_stats, dict)
            )
            docs_termines = sum(
                len(type_stats.get('par_statut', {}).get('TERMINÉ', []))
                for type_stats in stats.values() 
                if isinstance(type_stats, dict)
            )
            taux_completion = (docs_termines / total_docs * 100) if total_docs > 0 else 0
            st.metric("📈 Taux Completion", f"{taux_completion:.1f}%")
        
        with col_av4:
            # Efficacité module (documents par module actif)
            modules_actifs = sum(1 for config in modules_status.values() if config['status'] == '✅')
            efficacite = total_docs / modules_actifs if modules_actifs > 0 else 0
            st.metric("⚡ Efficacité Modules", f"{efficacite:.1f} docs/module")


# Exports principaux - VERSION FINALE COMPLÈTE
__all__ = [
    # Fonction principale
    'show_formulaires_page',
    
    # Gestionnaire principal
    'GestionnaireFormulaires',
    
    # ✅ TOUS LES 5 GESTIONNAIRES SPÉCIALISÉS OPÉRATIONNELS
    'GestionnaireBonsTravail',
    'GestionnaireBonsAchats',
    'GestionnaireBonsCommande',
    'GestionnaireDemandesPrix',
    'GestionnaireEstimations',      # 🎉 AJOUTÉ
    
    # ✅ TOUTES LES 5 INTERFACES OPÉRATIONNELLES
    'render_bons_travail_tab',
    'render_bons_achats_tab',
    'render_bons_commande_tab',
    'render_demandes_prix_tab',
    'render_estimations_tab',       # 🎉 AJOUTÉ
    
    # Utilitaires
    'formater_montant',
    'formater_delai',
    'TYPES_FORMULAIRES'
]

# Métadonnées du module principal - VERSION FINALE
__version__ = "2.0.0"
__author__ = "DG Inc. ERP Team"
__description__ = "Module Formulaires ERP - 5/5 modules opérationnels - ARCHITECTURE COMPLÈTE"
