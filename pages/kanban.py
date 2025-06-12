# --- START OF FILE kanban.py ---

import streamlit as st
import pandas as pd
from datetime import datetime

# NOTE: Pour que ce module fonctionne de manière autonome, il doit avoir accès
# aux gestionnaires via st.session_state, qui sont initialisés dans app.py.
# from app import GestionnaireProjetIA, GestionnaireCRM, format_currency

# Pour rendre ce module plus autonome, nous redéfinissons les fonctions et constantes nécessaires ici.
# Dans une application plus grande, ceux-ci seraient dans un fichier utils.py.

STATUTS = ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON"]

def format_currency(value):
    """Fonction utilitaire pour formater les valeurs monétaires."""
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


def app():
    """
    Affiche la vue Kanban de style Planner.
    Cette fonction est une version modulaire de la logique contenue dans show_kanban() de app.py.
    """
    # Injection du CSS spécifique au Kanban horizontal
    st.markdown("""
    <style>
    /* Kanban - Style "Planner" horizontal */
    .kanban-container {
        display: flex; /* La clé pour un affichage horizontal */
        flex-direction: row;
        gap: 15px;
        padding: 15px;
        background-color: var(--secondary-background-color); /* Fond léger pour la zone de défilement */
        border-radius: 12px;
        overflow-x: auto; /* Active le défilement horizontal */
        overflow-y: hidden; /* Empêche le défilement vertical parasite */
        min-height: 600px; /* Donne de la hauteur à la zone */
        margin-bottom: 20px;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
    }
    .kanban-column {
        flex: 0 0 320px; /* Chaque colonne a une largeur fixe, ne grandit pas, ne rétrécit pas */
        width: 320px;
        padding: 1rem;
        border-radius: var(--border-radius-md);
        background: var(--background-color);
        height: 100%;
        display: flex;
        flex-direction: column;
        border: 1px solid var(--border-color-light);
    }
    .kanban-header {
        font-weight: 600;
        font-size: 1.1em;
        text-align: left;
        padding: 0.75rem;
        border-radius: var(--border-radius-sm);
        margin-bottom: 1rem;
        color: var(--primary-color-darker);
        background: var(--primary-color-lighter);
        border-bottom: 2px solid var(--primary-color);
        cursor: default;
    }
    .kanban-cards-zone {
        flex-grow: 1; /* Permet à la zone des cartes de prendre l'espace restant */
        overflow-y: auto; /* Scroll vertical pour les cartes DANS la colonne */
        padding-right: 5px; /* Espace pour la scrollbar */
    }

    /* Style des cartes individuelles */
    .kanban-card {
        background: var(--card-background);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: var(--box-shadow-sm);
        border-left: 5px solid transparent;
        transition: all 0.3s ease;
        color: var(--text-color);
    }
    .kanban-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--box-shadow-blue);
    }
    .kanban-card-title {
        font-weight: 600;
        margin-bottom: 5px;
    }
    .kanban-card-info {
        font-size: 0.8em;
        color: var(--text-color-muted);
        margin-bottom: 3px;
    }

    /* Logique de Drag & Drop Visuel */
    /* État lorsqu'un projet est "soulevé" */
    .kanban-drag-indicator {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background-color: var(--button-color);
        color: white;
        padding: 12px 20px;
        border-radius: var(--border-radius-lg);
        box-shadow: var(--box-shadow-black);
        z-index: 1000;
        animation: fadeIn 0.3s ease-out;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("## 🔄 Vue Kanban (Style Planner)")

    # Récupération des gestionnaires depuis l'état de la session
    if 'gestionnaire' not in st.session_state or 'gestionnaire_crm' not in st.session_state:
        st.error("Les gestionnaires de données n'ont pas été initialisés. Veuillez recharger l'application depuis la page principale.")
        return
        
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
        recherche = st.text_input("Rechercher par nom, client...", key="kanban_module_search")

    projets_filtres = gestionnaire.projets
    if recherche:
        terme = recherche.lower()
        projets_filtres = [
            p for p in projets_filtres if
            terme in str(p.get('nom_projet', '')).lower() or
            terme in str(p.get('client_nom_cache', '')).lower() or
            (p.get('client_entreprise_id') and crm_manager.get_entreprise_by_id(p.get('client_entreprise_id')) and terme in crm_manager.get_entreprise_by_id(p.get('client_entreprise_id')).get('nom', '').lower()) or
            terme in str(p.get('client', '')).lower()
        ]

    # Préparation des données pour les colonnes
    projs_by_statut = {s: [] for s in STATUTS}
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
                Déplacement de: <strong>#{proj_dragged['id']} - {proj_dragged['nom_projet']}</strong>
            </div>
            """, unsafe_allow_html=True)
            if st.sidebar.button("❌ Annuler le déplacement", use_container_width=True):
                st.session_state.dragged_project_id = None
                st.session_state.dragged_from_status = None
                st.rerun()

    # --- STRUCTURE HORIZONTALE ---
    st.markdown('<div class="kanban-container">', unsafe_allow_html=True)

    for sk in STATUTS:
        # Chaque colonne est un conteneur div
        st.markdown(f'<div class="kanban-column" style="border-top: 4px solid {col_borders_k.get(sk, "#ccc")};">', unsafe_allow_html=True)

        # En-tête de la colonne
        st.markdown(f'<div class="kanban-header">{sk} ({len(projs_by_statut[sk])})</div>', unsafe_allow_html=True)

        # Si un projet est "soulevé", afficher une zone de dépôt
        if st.session_state.dragged_project_id and sk != st.session_state.dragged_from_status:
            if st.button(f"⤵️ Déposer ici", key=f"drop_in_module_{sk}", use_container_width=True, help=f"Déplacer vers {sk}"):
                proj_id_to_move = st.session_state.dragged_project_id
                if gestionnaire.modifier_projet(proj_id_to_move, {'statut': sk}):
                    st.success(f"Projet #{proj_id_to_move} déplacé vers '{sk}'!")
                else:
                    st.error("Une erreur est survenue lors du déplacement.")

                st.session_state.dragged_project_id = None
                st.session_state.dragged_from_status = None
                st.rerun()

        # Zone pour les cartes avec défilement vertical interne
        st.markdown('<div class="kanban-cards-zone">', unsafe_allow_html=True)

        if not projs_by_statut[sk]:
            st.markdown("<div style='text-align:center; color:var(--text-color-muted); margin-top:2rem;'><i>Vide</i></div>", unsafe_allow_html=True)

        for pk in projs_by_statut[sk]:
            prio_k = pk.get('priorite', 'MOYEN')
            card_borders_k = {'ÉLEVÉ': '#ef4444', 'MOYEN': '#f59e0b', 'BAS': '#10b981'}
            prio_icons_k = {'ÉLEVÉ': '🔴', 'MOYEN': '🟡', 'BAS': '🟢'}
            
            client_display_name_kanban = pk.get('client_nom_cache', 'N/A')
            if client_display_name_kanban == 'N/A' and pk.get('client_entreprise_id'):
                entreprise = crm_manager.get_entreprise_by_id(pk.get('client_entreprise_id'))
                client_display_name_kanban = entreprise.get('nom', 'N/A') if entreprise else 'N/A'
            elif client_display_name_kanban == 'N/A':
                client_display_name_kanban = pk.get('client', 'N/A')
            
            # Affichage de la carte
            st.markdown(f"""
            <div class='kanban-card' style='border-left-color:{card_borders_k.get(prio_k, 'var(--border-color)')};'>
                <div class='kanban-card-title'>#{pk.get('id')} - {pk.get('nom_projet', 'N/A')}</div>
                <div class='kanban-card-info'>👤 {client_display_name_kanban}</div>
                <div class='kanban-card-info'>{prio_icons_k.get(prio_k, '⚪')} {prio_k}</div>
                <div class='kanban-card-info'>💰 {format_currency(pk.get('prix_estime', 0))}</div>
            </div>
            """, unsafe_allow_html=True)

            # Boutons d'action pour la carte
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👁️ Voir", key=f"view_kanban_module_{pk['id']}", help="Voir les détails", use_container_width=True):
                    # Cette action définit l'état. Le rendu de la modale est géré par app.py
                    st.session_state.selected_project = pk
                    st.session_state.show_project_modal = True
                    st.rerun()
            with col2:
                # Le bouton "Déplacer" initie l'état de drag & drop
                if st.button("➡️ Déplacer", key=f"move_kanban_module_{pk['id']}", help="Déplacer ce projet", use_container_width=True):
                    st.session_state.dragged_project_id = pk['id']
                    st.session_state.dragged_from_status = sk
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True) # Fin de .kanban-cards-zone
        st.markdown('</div>', unsafe_allow_html=True) # Fin de .kanban-column

    st.markdown('</div>', unsafe_allow_html=True) # Fin de .kanban-container

if __name__ == "__main__":
    # Ce bloc est pour le test direct du module.
    # Il nécessite que l'environnement Streamlit soit en cours d'exécution.
    # Pour un test complet, il faut lancer l'application principale (app.py)
    # et naviguer vers la page Kanban.
    st.title("Test du Module Kanban")
    st.info("Ce module est conçu pour être appelé depuis l'application principale. "
            "Assurez-vous que `st.session_state.gestionnaire` est initialisé.")
    
    # Simulation de l'initialisation pour le test
    # Dans un vrai scénario, ces données viendraient de app.py
    if 'gestionnaire' not in st.session_state:
        from app import GestionnaireProjetIA
        st.session_state.gestionnaire = GestionnaireProjetIA()
    if 'gestionnaire_crm' not in st.session_state:
        from crm import GestionnaireCRM
        st.session_state.gestionnaire_crm = GestionnaireCRM()

    app()