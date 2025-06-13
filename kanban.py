# --- START OF FILE kanban.py - VERSION SQLITE UNIFIÉE ---

import streamlit as st
import pandas as pd
from datetime import datetime

# NOUVELLE ARCHITECTURE : Compatible avec app.py SQLite
# Le module utilise maintenant GestionnaireProjetSQL au lieu de GestionnaireProjetIA

# Constantes préservées
STATUTS = ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON", "ANNULÉ"]

def format_currency(value):
    """Fonction utilitaire pour formater les valeurs monétaires - INCHANGÉE"""
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
    NOUVELLE VERSION SQLite : Affiche la vue Kanban style Planner avec données SQLite
    Compatible avec l'architecture unifiée erp_production_dg.db
    """
    # CSS inchangé - Style Kanban horizontal préservé
    st.markdown("""
    <style>
    /* Kanban - Style "Planner" horizontal */
    .kanban-container {
        display: flex;
        flex-direction: row;
        gap: 15px;
        padding: 15px;
        background-color: var(--secondary-background-color);
        border-radius: 12px;
        overflow-x: auto;
        overflow-y: hidden;
        min-height: 600px;
        margin-bottom: 20px;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
    }
    .kanban-column {
        flex: 0 0 320px;
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
        flex-grow: 1;
        overflow-y: auto;
        padding-right: 5px;
    }
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
    .sqlite-indicator {
        background: linear-gradient(135deg, #10b981, #3b82f6);
        color: white;
        padding: 8px 12px;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: 500;
        margin-bottom: 1rem;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("## 🔄 Vue Kanban (SQLite Unifié)")
    
    # NOUVELLE ARCHITECTURE : Vérification gestionnaires SQLite
    if 'gestionnaire' not in st.session_state or 'gestionnaire_crm' not in st.session_state:
        st.error("⚠️ Gestionnaires SQLite non initialisés. Veuillez recharger depuis la page principale.")
        st.info("💡 Assurez-vous que l'architecture SQLite est correctement configurée dans app.py")
        return
    
    # NOUVELLE ARCHITECTURE : Récupération gestionnaires SQLite
    gestionnaire = st.session_state.gestionnaire  # Maintenant GestionnaireProjetSQL
    crm_manager = st.session_state.gestionnaire_crm  # Compatible SQLite
    
    # Vérification type gestionnaire (debug)
    gestionnaire_type = type(gestionnaire).__name__
    if gestionnaire_type == "GestionnaireProjetSQL":
        st.markdown('<div class="sqlite-indicator">🗄️ Données depuis SQLite : erp_production_dg.db</div>', unsafe_allow_html=True)
    
    # Initialisation état drag & drop (inchangé)
    if 'dragged_project_id' not in st.session_state:
        st.session_state.dragged_project_id = None
    if 'dragged_from_status' not in st.session_state:
        st.session_state.dragged_from_status = None

    # NOUVELLE ARCHITECTURE : Récupération projets depuis SQLite
    try:
        projets_sqlite = gestionnaire.projets  # Propriété qui appelle get_all_projects() en SQLite
        if not projets_sqlite:
            st.info("📋 Aucun projet en base SQLite pour affichage Kanban.")
            st.markdown("💡 Créez des projets depuis la page 'Liste des Projets' pour les voir ici.")
            return
    except Exception as e:
        st.error(f"❌ Erreur récupération projets SQLite : {e}")
        return

    # Interface de filtrage (logique identique)
    with st.expander("🔍 Filtres", expanded=False):
        recherche = st.text_input("Rechercher par nom, client...", key="kanban_sqlite_search")

    # MODIFICATION CRITIQUE : Adaptation filtrage pour champs SQLite
    projets_filtres = projets_sqlite
    if recherche:
        terme = recherche.lower()
        projets_filtres = []
        
        for p in projets_sqlite:
            # NOUVEAU : Recherche adaptée aux champs SQLite
            nom_projet = str(p.get('nom_projet', '')).lower()
            client_cache = str(p.get('client_nom_cache', '')).lower()
            client_legacy = str(p.get('client_legacy', '')).lower()
            
            # CORRECTION : client_company_id au lieu de client_entreprise_id
            client_company_nom = ""
            if p.get('client_company_id'):
                entreprise = crm_manager.get_entreprise_by_id(p.get('client_company_id'))
                if entreprise:
                    client_company_nom = entreprise.get('nom', '').lower()
            
            # Logique de recherche étendue
            if (terme in nom_projet or 
                terme in client_cache or 
                terme in client_legacy or 
                terme in client_company_nom):
                projets_filtres.append(p)

    # Préparation des données par statut (logique identique)
    projs_by_statut = {s: [] for s in STATUTS}
    for p in projets_filtres:
        stat = p.get('statut', 'À FAIRE')
        if stat in projs_by_statut:
            projs_by_statut[stat].append(p)
        else:
            projs_by_statut['À FAIRE'].append(p)
    
    # Couleurs colonnes (inchangées)
    col_borders_k = {
        'À FAIRE': '#f59e0b', 
        'EN COURS': '#3b82f6', 
        'EN ATTENTE': '#ef4444', 
        'TERMINÉ': '#10b981', 
        'LIVRAISON': '#8b5cf6',
        'ANNULÉ': '#6b7280'
    }

    # Indicateur visuel drag & drop (logique identique)
    if st.session_state.dragged_project_id:
        proj_dragged = next((p for p in projets_sqlite if p['id'] == st.session_state.dragged_project_id), None)
        if proj_dragged:
            st.markdown(f"""
            <div class="kanban-drag-indicator">
                🔄 Déplacement SQLite: <strong>#{proj_dragged['id']} - {proj_dragged['nom_projet']}</strong>
            </div>
            """, unsafe_allow_html=True)
            if st.sidebar.button("❌ Annuler le déplacement", use_container_width=True):
                st.session_state.dragged_project_id = None
                st.session_state.dragged_from_status = None
                st.rerun()

    # STRUCTURE HORIZONTALE (inchangée)
    st.markdown('<div class="kanban-container">', unsafe_allow_html=True)

    for sk in STATUTS:
        # Colonne Kanban
        st.markdown(f'<div class="kanban-column" style="border-top: 4px solid {col_borders_k.get(sk, "#ccc")};">', unsafe_allow_html=True)

        # En-tête colonne avec compteur
        st.markdown(f'<div class="kanban-header">{sk} ({len(projs_by_statut[sk])})</div>', unsafe_allow_html=True)

        # Zone de dépôt pour drag & drop
        if st.session_state.dragged_project_id and sk != st.session_state.dragged_from_status:
            if st.button(f"⤵️ Déposer ici", key=f"drop_sqlite_{sk}", use_container_width=True, help=f"Déplacer vers {sk}"):
                proj_id_to_move = st.session_state.dragged_project_id
                
                # NOUVELLE ARCHITECTURE : Modification via SQLite
                try:
                    if gestionnaire.modifier_projet(proj_id_to_move, {'statut': sk}):
                        st.success(f"✅ Projet #{proj_id_to_move} déplacé vers '{sk}' en SQLite !")
                    else:
                        st.error("❌ Erreur lors du déplacement SQLite.")
                except Exception as e:
                    st.error(f"❌ Erreur SQLite : {e}")

                st.session_state.dragged_project_id = None
                st.session_state.dragged_from_status = None
                st.rerun()

        # Zone cartes avec scroll vertical
        st.markdown('<div class="kanban-cards-zone">', unsafe_allow_html=True)

        if not projs_by_statut[sk]:
            st.markdown("<div style='text-align:center; color:var(--text-color-muted); margin-top:2rem;'><i>🗄️ Aucun projet SQLite dans ce statut</i></div>", unsafe_allow_html=True)

        for pk in projs_by_statut[sk]:
            # Gestion priorité (inchangée)
            prio_k = pk.get('priorite', 'MOYEN')
            card_borders_k = {'ÉLEVÉ': '#ef4444', 'MOYEN': '#f59e0b', 'BAS': '#10b981'}
            prio_icons_k = {'ÉLEVÉ': '🔴', 'MOYEN': '🟡', 'BAS': '🟢'}
            
            # MODIFICATION CRITIQUE : Logique nom client pour SQLite
            client_display_name_kanban = pk.get('client_nom_cache', 'N/A')
            
            # CORRECTION : client_company_id au lieu de client_entreprise_id  
            if client_display_name_kanban == 'N/A' and pk.get('client_company_id'):
                try:
                    entreprise = crm_manager.get_entreprise_by_id(pk.get('client_company_id'))
                    if entreprise:
                        client_display_name_kanban = entreprise.get('nom', 'N/A')
                except Exception:
                    pass  # Garde N/A si erreur
            
            # Fallback sur client_legacy si disponible
            if client_display_name_kanban == 'N/A' and pk.get('client_legacy'):
                client_display_name_kanban = pk.get('client_legacy')
            
            # Affichage carte (structure identique)
            st.markdown(f"""
            <div class='kanban-card' style='border-left-color:{card_borders_k.get(prio_k, 'var(--border-color)')};'>
                <div class='kanban-card-title'>#{pk.get('id')} - {pk.get('nom_projet', 'N/A')}</div>
                <div class='kanban-card-info'>👤 {client_display_name_kanban}</div>
                <div class='kanban-card-info'>{prio_icons_k.get(prio_k, '⚪')} {prio_k}</div>
                <div class='kanban-card-info'>💰 {format_currency(pk.get('prix_estime', 0))}</div>
                <div class='kanban-card-info'>📅 {pk.get('date_prevu', 'N/A')}</div>
            </div>
            """, unsafe_allow_html=True)

            # Boutons action (inchangés)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👁️ Voir", key=f"view_kanban_sqlite_{pk['id']}", help="Voir détails", use_container_width=True):
                    st.session_state.selected_project = pk
                    st.session_state.show_project_modal = True
                    st.rerun()
            with col2:
                if st.button("➡️ Déplacer", key=f"move_kanban_sqlite_{pk['id']}", help="Déplacer projet", use_container_width=True):
                    st.session_state.dragged_project_id = pk['id']
                    st.session_state.dragged_from_status = sk
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)  # Fin kanban-cards-zone
        st.markdown('</div>', unsafe_allow_html=True)  # Fin kanban-column

    st.markdown('</div>', unsafe_allow_html=True)  # Fin kanban-container
    
    # Statistiques SQLite en bas
    if projets_filtres:
        st.markdown("---")
        stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
        
        with stats_col1:
            st.metric("🗄️ Total SQLite", len(projets_filtres))
        with stats_col2:
            projets_actifs = len([p for p in projets_filtres if p.get('statut') not in ['TERMINÉ', 'ANNULÉ']])
            st.metric("🚀 Actifs", projets_actifs)
        with stats_col3:
            ca_total = sum(float(str(p.get('prix_estime', 0)).replace('$', '').replace(',', '')) for p in projets_filtres if p.get('prix_estime'))
            st.metric("💰 CA Total", f"{ca_total:,.0f}$")
        with stats_col4:
            if gestionnaire_type == "GestionnaireProjetSQL":
                # Statistiques base SQLite
                try:
                    total_db_projects = st.session_state.erp_db.get_table_count('projects')
                    st.metric("📊 Base SQLite", total_db_projects)
                except:
                    st.metric("📊 Base SQLite", "N/A")


def show_kanban():
    """Fonction wrapper pour compatibilité avec app.py"""
    app()


if __name__ == "__main__":
    # Test autonome du module
    st.title("🔄 Test Module Kanban SQLite")
    st.info("Module adapté pour architecture SQLite unifiée")
    
    # Simulation initialisation pour test
    if 'gestionnaire' not in st.session_state:
        st.warning("⚠️ Gestionnaire SQLite non initialisé - Lancez depuis app.py")
        st.stop()
    
    app()

# --- END OF FILE kanban.py - VERSION SQLITE UNIFIÉE ---
