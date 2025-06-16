# formulaires/__init__.py
# Module Formulaires ERP Production DG Inc. - Exports principaux

"""
Module Formulaires ERP Production DG Inc.
Architecture modulaire pour la gestion de tous les documents métier :
- Bons de Travail (BT)
- Bons d'Achats (BA) 
- Bons de Commande (BC)
- Demandes de Prix (DP)
- Estimations (EST)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Import de la classe principale
from .core.base_gestionnaire import GestionnaireFormulaires

# Import des gestionnaires spécialisés disponibles
from .bons_travail import GestionnaireBonsTravail, render_bons_travail_tab

# TODO: Ajouter au fur et à mesure de la migration
# from .bons_achats import GestionnaireBonsAchats, render_bons_achats_tab
# from .bons_commande import GestionnaireBonsCommande, render_bons_commande_tab
# from .demandes_prix import GestionnaireDemandesPrix, render_demandes_prix_tab
# from .estimations import GestionnaireEstimations, render_estimations_tab

# Import des utilitaires
from .utils.helpers import formater_montant, formater_delai
from .core.types_formulaires import TYPES_FORMULAIRES


def show_formulaires_page():
    """
    Page principale du module Formulaires avec architecture modulaire.
    
    Cette fonction remplace l'ancienne fonction monolithique par une version
    modulaire qui utilise les gestionnaires spécialisés.
    """
    st.markdown("## 📑 Gestion des Formulaires - DG Inc.")
    st.caption("*Architecture modulaire v2.0*")
    
    # Initialisation du gestionnaire principal
    if 'gestionnaire_formulaires' not in st.session_state:
        st.session_state.gestionnaire_formulaires = GestionnaireFormulaires(st.session_state.erp_db)
    
    gestionnaire = st.session_state.gestionnaire_formulaires
    
    # Statistiques globales
    show_formulaires_dashboard(gestionnaire)
    
    # Tabs pour chaque type de formulaire
    # Note: Seuls les modules migrés sont activés
    tab_bt, tab_ba, tab_bc, tab_dp, tab_est = st.tabs([
        "🔧 Bons de Travail",
        "🛒 Bons d'Achats", 
        "📦 Bons de Commande",
        "💰 Demandes de Prix",
        "📊 Estimations"
    ])
    
    # ✅ Module BT migrée - Utilise la nouvelle architecture
    with tab_bt:
        render_bons_travail_tab(gestionnaire)
    
    # 🚧 Modules en cours de migration - Utilise temporairement l'ancien code
    with tab_ba:
        _render_legacy_tab("BON_ACHAT", gestionnaire, "🛒 Bons d'Achats")
    
    with tab_bc:
        _render_legacy_tab("BON_COMMANDE", gestionnaire, "📦 Bons de Commande")
    
    with tab_dp:
        _render_legacy_tab("DEMANDE_PRIX", gestionnaire, "💰 Demandes de Prix")
    
    with tab_est:
        _render_legacy_tab("ESTIMATION", gestionnaire, "📊 Estimations")


def show_formulaires_dashboard(gestionnaire):
    """
    Dashboard des formulaires avec métriques globales.
    Version modulaire optimisée.
    """
    st.markdown("### 📊 Dashboard Formulaires")
    
    stats = gestionnaire.get_statistiques_formulaires()
    
    if not any(stats.values()):
        st.info("Aucun formulaire créé. Commencez par créer votre premier document.")
        return
    
    # Métriques principales avec nouveau design
    col1, col2, col3, col4, col5 = st.columns(5)
    
    for i, (type_form, config) in enumerate(TYPES_FORMULAIRES.items()):
        with [col1, col2, col3, col4, col5][i]:
            type_stats = stats.get(type_form, {})
            total = type_stats.get('total', 0)
            montant = type_stats.get('montant_total', 0)
            
            # Indicateur de migration
            migre = type_form == 'BON_TRAVAIL'  # Seul BT est migré pour l'instant
            migration_icon = "✅" if migre else "🚧"
            
            st.metric(
                f"{migration_icon} {config['icon']} {config['nom']}",
                total,
                delta=formater_montant(montant) if montant else None,
                help=f"{'Module migré' if migre else 'Migration en cours'}"
            )
    
    # Graphiques optimisés
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Répartition par type avec statut migration
        types_data = []
        for type_form, config in TYPES_FORMULAIRES.items():
            total = stats.get(type_form, {}).get('total', 0)
            if total > 0:
                migre = type_form == 'BON_TRAVAIL'
                nom_affichage = f"{config['nom']} {'✅' if migre else '🚧'}"
                types_data.append({'Type': nom_affichage, 'Nombre': total})
        
        if types_data:
            df_types = pd.DataFrame(types_data)
            fig = px.pie(df_types, values='Nombre', names='Type', 
                        title="📊 Répartition par Type (✅=Migré, 🚧=Legacy)")
            fig.update_layout(showlegend=True, height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_g2:
        # Évolution avec indicateurs de performance
        evolution_data = []
        for type_form, type_stats in stats.items():
            for statut, count in type_stats.get('par_statut', {}).items():
                evolution_data.append({
                    'Statut': statut,
                    'Nombre': count,
                    'Type': TYPES_FORMULAIRES[type_form]['nom']
                })
        
        if evolution_data:
            df_statuts = pd.DataFrame(evolution_data)
            fig = px.bar(df_statuts, x='Statut', y='Nombre', color='Type',
                        title="📈 Documents par Statut")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)


def _render_legacy_tab(type_formulaire, gestionnaire, titre):
    """
    Interface temporaire pour les modules non encore migrés.
    Utilise l'ancien code en attendant la migration complète.
    
    Args:
        type_formulaire: Type de formulaire (BON_ACHAT, etc.)
        gestionnaire: Gestionnaire de base
        titre: Titre de l'onglet
    """
    st.markdown(f"### {titre}")
    
    # Message de statut de migration
    st.warning(f"""
    🚧 **Module en cours de migration**
    
    Ce module utilise encore l'ancienne architecture. La migration vers 
    l'architecture modulaire est prévue dans la prochaine version.
    
    **Fonctionnalités disponibles :**
    - Consultation des documents existants
    - Création de base (limitée)
    
    **Bientôt disponible :**
    - Interface optimisée
    - Gestionnaire spécialisé
    - Fonctionnalités avancées
    """)
    
    # Interface de base simplifiée
    documents = gestionnaire.get_formulaires(type_formulaire)
    
    if documents:
        st.markdown(f"##### 📋 {len(documents)} document(s) existant(s)")
        
        # Affichage simplifié
        for doc in documents[:5]:  # Limiter à 5 pour l'affichage
            with st.expander(f"{doc['numero_document']} - {doc.get('company_nom', 'N/A')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.text(f"Statut: {doc['statut']}")
                    st.text(f"Date: {doc['date_creation'][:10] if doc['date_creation'] else 'N/A'}")
                with col2:
                    st.text(f"Montant: {formater_montant(doc.get('montant_total', 0))}")
                    st.text(f"Responsable: {doc.get('employee_nom', 'N/A')}")
        
        if len(documents) > 5:
            st.info(f"... et {len(documents) - 5} autre(s) document(s)")
    else:
        st.info(f"Aucun {titre.lower()} créé.")
    
    # Actions de base
    col_action1, col_action2 = st.columns(2)
    with col_action1:
        if st.button(f"📋 Voir Tous les {titre}", key=f"view_all_{type_formulaire}"):
            st.info("Fonctionnalité disponible après migration du module")
    
    with col_action2:
        if st.button(f"➕ Créer {titre}", key=f"create_{type_formulaire}"):
            st.info("Utilisez temporairement l'ancien formulaire en attendant la migration")


# Métadonnées du module principal
__version__ = "2.0.0"
__author__ = "DG Inc. ERP Team"
__description__ = "Module Formulaires ERP - Architecture modulaire"

# Exports principaux
__all__ = [
    # Fonction principale
    'show_formulaires_page',
    
    # Gestionnaire principal
    'GestionnaireFormulaires',
    
    # Gestionnaires spécialisés migrés
    'GestionnaireBonsTravail',
    
    # Interfaces migrées
    'render_bons_travail_tab',
    
    # Utilitaires
    'formater_montant',
    'formater_delai',
    'TYPES_FORMULAIRES'
]

# TODO: Ajouter au fur et à mesure de la migration
# 'GestionnaireBonsAchats', 'render_bons_achats_tab',
# 'GestionnaireBonsCommande', 'render_bons_commande_tab',
# 'GestionnaireDemandesPrix', 'render_demandes_prix_tab',
# 'GestionnaireEstimations', 'render_estimations_tab'
