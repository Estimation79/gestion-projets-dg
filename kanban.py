# --- START OF FILE kanban.py - VERSION SQLITE OPTIMISÉE ---

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

# ARCHITECTURE SQLITE UNIFIÉE : Compatible avec app.py et erp_database.py
# Utilise GestionnaireProjetSQL et ERPDatabase pour une intégration complète

# Constantes pour le Kanban
STATUTS_KANBAN = ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON", "ANNULÉ"]
PRIORITES = ["BAS", "MOYEN", "ÉLEVÉ"]

# Configuration des couleurs pour les statuts
COULEURS_STATUTS = {
    'À FAIRE': '#f59e0b',      # Orange
    'EN COURS': '#3b82f6',     # Bleu
    'EN ATTENTE': '#ef4444',   # Rouge
    'TERMINÉ': '#10b981',      # Vert
    'LIVRAISON': '#8b5cf6',    # Violet
    'ANNULÉ': '#6b7280'        # Gris
}

# Configuration des couleurs pour les priorités
COULEURS_PRIORITES = {
    'ÉLEVÉ': '#ef4444',    # Rouge
    'MOYEN': '#f59e0b',    # Orange
    'BAS': '#10b981'       # Vert
}

ICONES_PRIORITES = {
    'ÉLEVÉ': '🔴',
    'MOYEN': '🟡', 
    'BAS': '🟢'
}


def format_currency(value) -> str:
    """Formate une valeur monétaire avec gestion d'erreurs robuste"""
    if value is None:
        return "$0.00"
    
    try:
        # Nettoyage de la chaîne
        if isinstance(value, str):
            clean_value = value.replace(' ', '').replace('€', '').replace('$', '').replace(',', '')
        else:
            clean_value = str(value)
        
        num_value = float(clean_value) if clean_value else 0.0
        return f"${num_value:,.2f}"
        
    except (ValueError, TypeError):
        return "$0.00"


def get_client_display_name(projet: Dict[str, Any], crm_manager) -> str:
    """
    Récupère le nom d'affichage du client avec fallback intelligent
    Compatible avec la structure SQLite
    """
    # 1. Essayer client_nom_cache d'abord
    if projet.get('client_nom_cache') and projet.get('client_nom_cache') != 'N/A':
        return projet['client_nom_cache']
    
    # 2. Essayer de récupérer depuis l'entreprise liée
    if projet.get('client_company_id'):
        try:
            entreprise = crm_manager.get_entreprise_by_id(projet['client_company_id'])
            if entreprise and entreprise.get('nom'):
                return entreprise['nom']
        except Exception:
            pass  # Continue vers le fallback
    
    # 3. Fallback sur client_legacy
    if projet.get('client_legacy'):
        return projet['client_legacy']
    
    # 4. Dernier fallback
    return "Client non spécifié"


def filtrer_projets_kanban(projets: List[Dict], recherche: str, crm_manager) -> List[Dict]:
    """
    Filtre les projets selon le terme de recherche
    Recherche dans nom, client, description
    """
    if not recherche:
        return projets
    
    terme = recherche.lower().strip()
    if not terme:
        return projets
    
    projets_filtres = []
    
    for projet in projets:
        # Champs de recherche
        nom_projet = str(projet.get('nom_projet', '')).lower()
        description = str(projet.get('description', '')).lower()
        client_nom = get_client_display_name(projet, crm_manager).lower()
        
        # Vérification correspondance
        if (terme in nom_projet or 
            terme in description or 
            terme in client_nom or
            terme in str(projet.get('id', ''))):
            projets_filtres.append(projet)
    
    return projets_filtres


def organiser_projets_par_statut(projets: List[Dict]) -> Dict[str, List[Dict]]:
    """Organise les projets par statut avec gestion des statuts inconnus"""
    projets_par_statut = {statut: [] for statut in STATUTS_KANBAN}
    
    for projet in projets:
        statut = projet.get('statut', 'À FAIRE')
        if statut in projets_par_statut:
            projets_par_statut[statut].append(projet)
        else:
            # Statut inconnu -> À FAIRE par défaut
            projets_par_statut['À FAIRE'].append(projet)
    
    return projets_par_statut


def calculer_statistiques_kanban(projets: List[Dict]) -> Dict[str, Any]:
    """Calcule les statistiques pour l'affichage en bas du Kanban"""
    if not projets:
        return {
            'total': 0,
            'actifs': 0,
            'ca_total': 0,
            'projet_plus_cher': None,
            'duree_moyenne': 0
        }
    
    # Compteurs
    total = len(projets)
    actifs = len([p for p in projets if p.get('statut') not in ['TERMINÉ', 'ANNULÉ']])
    
    # Calcul CA total
    ca_total = 0
    prix_max = 0
    projet_plus_cher = None
    
    durees = []
    
    for projet in projets:
        # CA
        try:
            prix = float(str(projet.get('prix_estime', 0)).replace('$', '').replace(',', ''))
            ca_total += prix
            if prix > prix_max:
                prix_max = prix
                projet_plus_cher = projet.get('nom_projet', 'N/A')
        except:
            pass
        
        # Durée
        try:
            date_debut = datetime.strptime(projet.get('date_soumis', ''), '%Y-%m-%d')
            date_fin = datetime.strptime(projet.get('date_prevu', ''), '%Y-%m-%d')
            duree = (date_fin - date_debut).days
            if duree > 0:
                durees.append(duree)
        except:
            pass
    
    duree_moyenne = sum(durees) / len(durees) if durees else 0
    
    return {
        'total': total,
        'actifs': actifs,
        'ca_total': ca_total,
        'projet_plus_cher': projet_plus_cher,
        'duree_moyenne': duree_moyenne
    }


def afficher_carte_projet(projet: Dict[str, Any], crm_manager, statut: str) -> None:
    """Affiche une carte projet dans le Kanban"""
    
    # Données de la carte
    project_id = projet.get('id')
    nom_projet = projet.get('nom_projet', 'N/A')
    priorite = projet.get('priorite', 'MOYEN')
    prix_estime = projet.get('prix_estime', 0)
    date_prevu = projet.get('date_prevu', 'N/A')
    client_nom = get_client_display_name(projet, crm_manager)
    
    # Couleurs et icônes
    couleur_priorite = COULEURS_PRIORITES.get(priorite, '#6b7280')
    icone_priorite = ICONES_PRIORITES.get(priorite, '⚪')
    
    # Affichage de la carte
    st.markdown(f"""
    <div class='kanban-card' style='border-left-color: {couleur_priorite};'>
        <div class='kanban-card-title'>#{project_id} - {nom_projet}</div>
        <div class='kanban-card-info'>👤 {client_nom}</div>
        <div class='kanban-card-info'>{icone_priorite} {priorite}</div>
        <div class='kanban-card-info'>💰 {format_currency(prix_estime)}</div>
        <div class='kanban-card-info'>📅 {date_prevu}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Boutons d'action
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👁️ Voir", 
                     key=f"view_kanban_{project_id}_{statut}", 
                     help="Voir les détails", 
                     use_container_width=True):
            st.session_state.selected_project = projet
            st.session_state.show_project_modal = True
            st.rerun()
    
    with col2:
        if st.button("➡️ Déplacer", 
                     key=f"move_kanban_{project_id}_{statut}", 
                     help="Déplacer ce projet", 
                     use_container_width=True):
            st.session_state.dragged_project_id = project_id
            st.session_state.dragged_from_status = statut
            st.rerun()


def gerer_deplacement_projet(gestionnaire_sqlite, nouveau_statut: str) -> bool:
    """Gère le déplacement d'un projet vers un nouveau statut"""
    projet_id = st.session_state.dragged_project_id
    
    if not projet_id:
        return False
    
    try:
        # Mise à jour via SQLite
        success = gestionnaire_sqlite.modifier_projet(projet_id, {'statut': nouveau_statut})
        
        if success:
            st.success(f"✅ Projet #{projet_id} déplacé vers '{nouveau_statut}' en SQLite !")
            return True
        else:
            st.error("❌ Erreur lors de la mise à jour SQLite.")
            return False
            
    except Exception as e:
        st.error(f"❌ Erreur SQLite : {e}")
        return False


def afficher_indicateur_drag() -> None:
    """Affiche l'indicateur de drag & drop actif"""
    if not st.session_state.get('dragged_project_id'):
        return
    
    # Récupérer le projet en cours de déplacement
    gestionnaire = st.session_state.gestionnaire
    projet_dragged = None
    
    try:
        for p in gestionnaire.projets:
            if p.get('id') == st.session_state.dragged_project_id:
                projet_dragged = p
                break
    except:
        pass
    
    if projet_dragged:
        st.markdown(f"""
        <div class="kanban-drag-indicator">
            🔄 Déplacement en cours: <strong>#{projet_dragged.get('id')} - {projet_dragged.get('nom_projet', 'N/A')}</strong>
        </div>
        """, unsafe_allow_html=True)
        
        # Bouton d'annulation dans la sidebar
        if st.sidebar.button("❌ Annuler le déplacement", use_container_width=True):
            st.session_state.dragged_project_id = None
            st.session_state.dragged_from_status = None
            st.rerun()


def afficher_css_kanban() -> None:
    """Affiche le CSS personnalisé pour le Kanban"""
    st.markdown("""
    <style>
    /* === KANBAN SQLITE - STYLE MODERNE === */
    .kanban-container {
        display: flex;
        flex-direction: row;
        gap: 20px;
        padding: 20px;
        background: linear-gradient(135deg, var(--secondary-background-color), var(--background-color));
        border-radius: 15px;
        overflow-x: auto;
        overflow-y: hidden;
        min-height: 700px;
        margin-bottom: 25px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid var(--border-color-light);
    }
    
    .kanban-column {
        flex: 0 0 340px;
        width: 340px;
        background: var(--background-color);
        border-radius: 12px;
        padding: 0;
        display: flex;
        flex-direction: column;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        border: 1px solid var(--border-color-light);
        transition: transform 0.2s ease;
    }
    
    .kanban-column:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.12);
    }
    
    .kanban-header {
        font-weight: 700;
        font-size: 1.1em;
        text-align: center;
        padding: 15px 20px;
        margin: 0;
        color: white;
        background: linear-gradient(135deg, var(--primary-color), var(--primary-color-darker));
        border-radius: 12px 12px 0 0;
        border-bottom: 3px solid var(--primary-color-darker);
        position: sticky;
        top: 0;
        z-index: 10;
    }
    
    .kanban-cards-zone {
        flex-grow: 1;
        overflow-y: auto;
        padding: 15px;
        max-height: 600px;
    }
    
    .kanban-cards-zone::-webkit-scrollbar {
        width: 6px;
    }
    
    .kanban-cards-zone::-webkit-scrollbar-track {
        background: var(--secondary-background-color);
        border-radius: 3px;
    }
    
    .kanban-cards-zone::-webkit-scrollbar-thumb {
        background: var(--primary-color-light);
        border-radius: 3px;
    }
    
    .kanban-card {
        background: var(--card-background);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid transparent;
        transition: all 0.3s ease;
        color: var(--text-color);
        position: relative;
        overflow: hidden;
    }
    
    .kanban-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--primary-color), transparent);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    
    .kanban-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    
    .kanban-card:hover::before {
        opacity: 1;
    }
    
    .kanban-card-title {
        font-weight: 600;
        font-size: 0.95em;
        margin-bottom: 8px;
        color: var(--primary-color-darker);
        line-height: 1.3;
    }
    
    .kanban-card-info {
        font-size: 0.85em;
        color: var(--text-color-muted);
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .kanban-drag-indicator {
        position: fixed;
        bottom: 30px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, var(--primary-color), var(--primary-color-darker));
        color: white;
        padding: 15px 25px;
        border-radius: 25px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.3);
        z-index: 1000;
        animation: pulse 2s infinite;
        font-weight: 600;
        font-size: 0.9em;
    }
    
    @keyframes pulse {
        0% { transform: translateX(-50%) scale(1); }
        50% { transform: translateX(-50%) scale(1.05); }
        100% { transform: translateX(-50%) scale(1); }
    }
    
    .sqlite-indicator {
        background: linear-gradient(135deg, #10b981, #3b82f6);
        color: white;
        padding: 10px 16px;
        border-radius: 25px;
        font-size: 0.85em;
        font-weight: 600;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
        animation: fadeIn 0.5s ease-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .kanban-stats {
        background: var(--card-background);
        border-radius: 12px;
        padding: 20px;
        margin-top: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border: 1px solid var(--border-color-light);
    }
    
    .empty-column {
        text-align: center;
        color: var(--text-color-muted);
        margin-top: 60px;
        font-style: italic;
        opacity: 0.7;
    }
    
    .drop-zone {
        background: linear-gradient(135deg, var(--primary-color-lighter), var(--primary-color-light));
        border: 2px dashed var(--primary-color);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 15px;
        text-align: center;
        color: var(--primary-color-darker);
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .drop-zone:hover {
        background: var(--primary-color-light);
        transform: scale(1.02);
    }
    </style>
    """, unsafe_allow_html=True)


def show_kanban_sqlite():
    """
    FONCTION PRINCIPALE - Vue Kanban optimisée pour SQLite
    Compatible avec l'architecture ERP Production DG Inc.
    """
    
    # Application du CSS
    afficher_css_kanban()
    
    # En-tête avec indicateur SQLite
    st.markdown("## 🔄 Vue Kanban - ERP Production DG Inc.")
    st.markdown('<div class="sqlite-indicator">🗄️ Données en temps réel depuis SQLite : erp_production_dg.db</div>', 
                unsafe_allow_html=True)
    
    # === VÉRIFICATION DE L'ARCHITECTURE ===
    if 'gestionnaire' not in st.session_state:
        st.error("⚠️ Gestionnaire de projets SQLite non initialisé.")
        st.info("💡 Veuillez démarrer l'application depuis app.py pour initialiser l'architecture SQLite.")
        return
    
    if 'gestionnaire_crm' not in st.session_state:
        st.error("⚠️ Gestionnaire CRM non initialisé.")
        return
    
    # === RÉCUPÉRATION DES GESTIONNAIRES ===
    gestionnaire = st.session_state.gestionnaire
    crm_manager = st.session_state.gestionnaire_crm
    
    # Vérification du type de gestionnaire
    if hasattr(gestionnaire, '__class__'):
        gestionnaire_type = gestionnaire.__class__.__name__
        if gestionnaire_type != "GestionnaireProjetSQL":
            st.warning(f"⚠️ Type de gestionnaire inattendu: {gestionnaire_type}")
    
    # === INITIALISATION DES VARIABLES DE SESSION ===
    if 'dragged_project_id' not in st.session_state:
        st.session_state.dragged_project_id = None
    if 'dragged_from_status' not in st.session_state:
        st.session_state.dragged_from_status = None
    
    # === RÉCUPÉRATION DES PROJETS ===
    try:
        projets = gestionnaire.projets  # Utilise la propriété qui appelle get_all_projects()
        
        if not projets:
            st.info("📋 Aucun projet trouvé en base SQLite.")
            st.markdown("💡 **Créez votre premier projet** depuis la page 'Liste des Projets' pour l'afficher ici.")
            
            # Afficher quelques statistiques de la base
            try:
                total_projects = st.session_state.erp_db.get_table_count('projects')
                total_companies = st.session_state.erp_db.get_table_count('companies')
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("📊 Projets en base", total_projects)
                with col2:
                    st.metric("🏢 Entreprises en base", total_companies)
            except:
                pass
            
            return
            
    except Exception as e:
        st.error(f"❌ Erreur lors de la récupération des projets SQLite : {e}")
        st.info("🔧 Vérifiez que la base de données SQLite est correctement initialisée.")
        return
    
    # === INTERFACE DE FILTRAGE ===
    with st.expander("🔍 Filtres et Options", expanded=False):
        col_filtre1, col_filtre2 = st.columns(2)
        
        with col_filtre1:
            recherche = st.text_input(
                "Rechercher par nom, client, ID...", 
                key="kanban_search",
                placeholder="Ex: Chassis, DG Corp, 10001..."
            )
        
        with col_filtre2:
            afficher_stats = st.toggle("📊 Afficher statistiques détaillées", value=True)
    
    # === FILTRAGE DES PROJETS ===
    projets_filtres = filtrer_projets_kanban(projets, recherche, crm_manager)
    
    if recherche and not projets_filtres:
        st.warning(f"🔍 Aucun projet ne correspond à '{recherche}'")
        return
    
    # === ORGANISATION PAR STATUT ===
    projets_par_statut = organiser_projets_par_statut(projets_filtres)
    
    # === AFFICHAGE INDICATEUR DRAG & DROP ===
    afficher_indicateur_drag()
    
    # === AFFICHAGE DU KANBAN ===
    st.markdown('<div class="kanban-container">', unsafe_allow_html=True)
    
    # Créer une colonne pour chaque statut
    colonnes = st.columns(len(STATUTS_KANBAN))
    
    for idx, statut in enumerate(STATUTS_KANBAN):
        with colonnes[idx]:
            # === EN-TÊTE DE COLONNE ===
            couleur_statut = COULEURS_STATUTS.get(statut, '#6b7280')
            nombre_projets = len(projets_par_statut[statut])
            
            st.markdown(f"""
            <div class="kanban-column" style="border-top: 4px solid {couleur_statut};">
                <div class="kanban-header" style="background: linear-gradient(135deg, {couleur_statut}, {couleur_statut}dd);">
                    {statut} ({nombre_projets})
                </div>
            """, unsafe_allow_html=True)
            
            # === ZONE DE DÉPÔT POUR DRAG & DROP ===
            if (st.session_state.dragged_project_id and 
                statut != st.session_state.dragged_from_status):
                
                st.markdown('<div class="drop-zone">', unsafe_allow_html=True)
                if st.button(f"⤵️ Déposer ici", 
                           key=f"drop_{statut}", 
                           use_container_width=True,
                           help=f"Déplacer le projet vers {statut}"):
                    
                    if gerer_deplacement_projet(gestionnaire, statut):
                        st.session_state.dragged_project_id = None
                        st.session_state.dragged_from_status = None
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # === ZONE DES CARTES ===
            st.markdown('<div class="kanban-cards-zone">', unsafe_allow_html=True)
            
            if not projets_par_statut[statut]:
                st.markdown('<div class="empty-column">📝 Aucun projet dans ce statut</div>', 
                          unsafe_allow_html=True)
            else:
                # Trier par priorité et date
                projets_tries = sorted(
                    projets_par_statut[statut],
                    key=lambda p: (
                        0 if p.get('priorite') == 'ÉLEVÉ' else 1 if p.get('priorite') == 'MOYEN' else 2,
                        p.get('date_prevu', '9999-12-31')
                    )
                )
                
                for projet in projets_tries:
                    afficher_carte_projet(projet, crm_manager, statut)
            
            st.markdown('</div></div>', unsafe_allow_html=True)  # Fin cards-zone et column
    
    st.markdown('</div>', unsafe_allow_html=True)  # Fin kanban-container
    
    # === STATISTIQUES DÉTAILLÉES ===
    if afficher_stats and projets_filtres:
        stats = calculer_statistiques_kanban(projets_filtres)
        
        st.markdown('<div class="kanban-stats">', unsafe_allow_html=True)
        st.markdown("### 📊 Statistiques Kanban SQLite")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🗄️ Total Projets", stats['total'])
        
        with col2:
            st.metric("🚀 Projets Actifs", stats['actifs'])
            taux_actifs = (stats['actifs'] / stats['total'] * 100) if stats['total'] > 0 else 0
            st.caption(f"Taux: {taux_actifs:.1f}%")
        
        with col3:
            st.metric("💰 CA Total", f"{stats['ca_total']:,.0f}$")
            if stats['projet_plus_cher']:
                st.caption(f"Plus gros: {stats['projet_plus_cher']}")
        
        with col4:
            st.metric("📅 Durée Moyenne", f"{stats['duree_moyenne']:.0f} jours")
        
        # Graphique de répartition par statut
        if len(projets_filtres) > 1:
            st.markdown("---")
            import plotly.express as px
            
            # Données pour le graphique
            repartition = []
            for statut in STATUTS_KANBAN:
                count = len(projets_par_statut[statut])
                if count > 0:
                    repartition.append({'Statut': statut, 'Nombre': count})
            
            if repartition:
                df_stats = pd.DataFrame(repartition)
                fig = px.pie(
                    df_stats, 
                    values='Nombre', 
                    names='Statut',
                    title="Répartition des projets par statut",
                    color='Statut',
                    color_discrete_map=COULEURS_STATUTS
                )
                
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='var(--text-color)'),
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)


# === FONCTIONS D'INTERFACE ===

def show_kanban():
    """Point d'entrée principal pour l'affichage du Kanban"""
    show_kanban_sqlite()


def app():
    """Fonction app() pour compatibilité avec les anciens appels"""
    show_kanban_sqlite()


# === POINT D'ENTRÉE POUR TEST AUTONOME ===
if __name__ == "__main__":
    st.title("🔄 Module Kanban SQLite - Test Autonome")
    st.info("Version optimisée pour l'architecture SQLite unifiée")
    
    # Vérification de l'environnement
    if 'gestionnaire' not in st.session_state:
        st.error("⚠️ Ce module doit être lancé depuis app.py avec l'architecture SQLite initialisée.")
        st.markdown("### 📋 Instructions:")
        st.markdown("1. Lancez `streamlit run app.py`")
        st.markdown("2. Naviguez vers la page Kanban depuis le menu")
        st.stop()
    
    # Test du module
    show_kanban_sqlite()

# --- END OF FILE kanban.py - VERSION SQLITE OPTIMISÉE ---
