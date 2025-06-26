# --- START OF FILE kanban.py - VERSION UNIFIÉE PROJETS + BTs + OPÉRATIONS (COMPLET) ---

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

# KANBAN UNIFIÉ - Vue Projets par Statuts + Vue BTs par Postes + Vue Opérations par Postes
# Compatible avec app.py et erp_database.py pour une intégration complète
# NOUVEAU : Ajout de la vue "BTs par Postes de Travail"

# === CONFIGURATION POUR VUE PROJETS ===
STATUTS_KANBAN = ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON", "ANNULÉ"]
PRIORITES = ["BAS", "MOYEN", "ÉLEVÉ"]

# Configuration des couleurs pour les statuts de projets
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

# === CONFIGURATION POUR VUE OPÉRATIONS & BTs ===
# Couleurs pour statuts de BT
BT_COLORS = {
    'BROUILLON': '#FFB74D',
    'VALIDÉ': '#64B5F6',
    'EN_COURS': '#26A69A',
    'TERMINÉ': '#9C27B0',
    'ANNULÉ': '#795548',
    'DEFAULT': '#90A4AE'
}

# Couleurs pour statuts d'opérations
COULEURS_STATUTS_OPERATIONS = {
    'À FAIRE': '#f59e0b',
    'EN COURS': '#3b82f6',
    'EN ATTENTE': '#ef4444',
    'TERMINÉ': '#10b981',
    'SUSPENDU': '#8b5cf6',
    'ANNULÉ': '#6b7280'
}

# Couleurs et icônes pour priorités (utilisé pour BTs et Opérations)
COULEURS_PRIORITES_OPS = {
    'CRITIQUE': '#ef4444',
    'URGENT': '#f59e0b',
    'ÉLEVÉ': '#f59e0b',
    'NORMAL': '#10b981',
    'MOYEN': '#10b981',
    'BAS': '#6b7280'
}

ICONES_PRIORITES_OPS = {
    'CRITIQUE': '🔴',
    'URGENT': '🟡',
    'ÉLEVÉ': '🟡',
    'NORMAL': '🟢',
    'MOYEN': '🟢',
    'BAS': '⚪'
}

# Icônes pour les départements
ICONES_DEPARTEMENTS = {
    'USINAGE': '🔧',
    'SOUDAGE': '⚡',
    'ASSEMBLAGE': '🔩',
    'PEINTURE': '🎨',
    'CONTRÔLE': '🔍',
    'EXPÉDITION': '📦',
    'BUREAU': '📋',
    'PRODUCTION': '🏭',
    'QUALITE': '✅',
    'LOGISTIQUE': '🚚',
    'COMMERCIAL': '💼',
    'ADMINISTRATION': '📁',
    'DIRECTION': '⭐'
}

# === FONCTIONS HELPER ===

def get_bt_color(bt_statut):
    """Récupère la couleur pour un statut de Bon de Travail."""
    # S'assurer que le statut est une chaîne valide
    statut_valide = str(bt_statut).upper().replace(' ', '_') if bt_statut else 'DEFAULT'
    return BT_COLORS.get(statut_valide, BT_COLORS['DEFAULT'])


def format_currency(value) -> str:
    """Formate une valeur monétaire avec gestion d'erreurs robuste."""
    if value is None:
        return "$0.00"
    try:
        if isinstance(value, str):
            clean_value = value.replace(' ', '').replace('€', '').replace('$', '').replace(',', '')
        else:
            clean_value = str(value)
        num_value = float(clean_value) if clean_value else 0.0
        return f"${num_value:,.2f}"
    except (ValueError, TypeError):
        return "$0.00"


def format_temps_estime(temps: float) -> str:
    """Formate le temps estimé en heures."""
    if temps is None or temps == 0:
        return "0.0h"
    try:
        return f"{float(temps):.1f}h"
    except (ValueError, TypeError):
        return "0.0h"


def get_client_display_name(projet: Dict[str, Any], crm_manager) -> str:
    """Récupère le nom d'affichage du client avec fallback intelligent."""
    if projet.get('client_nom_cache') and projet.get('client_nom_cache') != 'N/A':
        return projet['client_nom_cache']
    if projet.get('client_company_id'):
        try:
            entreprise = crm_manager.get_entreprise_by_id(projet['client_company_id'])
            if entreprise and entreprise.get('nom'):
                return entreprise['nom']
        except Exception:
            pass
    if projet.get('client_legacy'):
        return projet['client_legacy']
    return "Client non spécifié"


def get_operation_priority_from_context(operation: Dict, erp_db) -> str:
    """Récupère la priorité d'une opération depuis son contexte (projet ou BT)."""
    try:
        if operation.get('formulaire_bt_id'):
            bt_info = erp_db.execute_query(
                "SELECT priorite FROM formulaires WHERE id = ? AND type_formulaire = 'BON_TRAVAIL'",
                (operation['formulaire_bt_id'],)
            )
            if bt_info and bt_info[0]['priorite']:
                return bt_info[0]['priorite']
        if operation.get('project_id'):
            project_info = erp_db.execute_query(
                "SELECT priorite FROM projects WHERE id = ?",
                (operation['project_id'],)
            )
            if project_info and project_info[0]['priorite']:
                return project_info[0]['priorite']
        return 'NORMAL'
    except Exception:
        return 'NORMAL'


# === FONCTIONS POUR VUE PROJETS ===

def filtrer_projets_kanban(projets: List[Dict], recherche: str, crm_manager) -> List[Dict]:
    """Filtre les projets selon le terme de recherche."""
    if not recherche:
        return projets
    terme = recherche.lower().strip()
    if not terme:
        return projets
    projets_filtres = []
    for projet in projets:
        nom_projet = str(projet.get('nom_projet', '')).lower()
        description = str(projet.get('description', '')).lower()
        client_nom = get_client_display_name(projet, crm_manager).lower()
        if (terme in nom_projet or 
            terme in description or 
            terme in client_nom or
            terme in str(projet.get('id', ''))):
            projets_filtres.append(projet)
    return projets_filtres


def organiser_projets_par_statut(projets: List[Dict]) -> Dict[str, List[Dict]]:
    """Organise les projets par statut."""
    projets_par_statut = {statut: [] for statut in STATUTS_KANBAN}
    for projet in projets:
        statut = projet.get('statut', 'À FAIRE')
        if statut in projets_par_statut:
            projets_par_statut[statut].append(projet)
        else:
            projets_par_statut['À FAIRE'].append(projet)
    return projets_par_statut


def calculer_statistiques_kanban(projets: List[Dict]) -> Dict[str, Any]:
    """Calcule les statistiques pour l'affichage en bas du Kanban."""
    if not projets:
        return {'total': 0, 'actifs': 0, 'ca_total': 0, 'projet_plus_cher': None, 'duree_moyenne': 0}
    
    total = len(projets)
    actifs = len([p for p in projets if p.get('statut') not in ['TERMINÉ', 'ANNULÉ']])
    ca_total, prix_max, projet_plus_cher, durees = 0, 0, None, []
    
    for projet in projets:
        try:
            prix = float(str(projet.get('prix_estime', 0)).replace('$', '').replace(',', ''))
            ca_total += prix
            if prix > prix_max:
                prix_max, projet_plus_cher = prix, projet.get('nom_projet', 'N/A')
        except: 
            pass
        
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
    """Affiche une carte projet dans le Kanban."""
    project_id, nom_projet = projet.get('id'), projet.get('nom_projet', 'N/A')
    priorite, prix_estime = projet.get('priorite', 'MOYEN'), projet.get('prix_estime', 0)
    date_prevu, client_nom = projet.get('date_prevu', 'N/A'), get_client_display_name(projet, crm_manager)
    
    couleur_priorite, icone_priorite = COULEURS_PRIORITES.get(priorite, '#6b7280'), ICONES_PRIORITES.get(priorite, '⚪')
    
    st.markdown(f"""
    <div class='kanban-card' style='border-left-color: {couleur_priorite};'>
        <div class='kanban-card-title'>#{project_id} - {nom_projet}</div>
        <div class='kanban-card-info'>👤 {client_nom}</div>
        <div class='kanban-card-info'>{icone_priorite} {priorite}</div>
        <div class='kanban-card-info'>💰 {format_currency(prix_estime)}</div>
        <div class='kanban-card-info'>📅 {date_prevu}</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👁️ Voir", key=f"view_kanban_{project_id}_{statut}", help="Voir les détails", use_container_width=True):
            st.session_state.selected_project = projet
            st.session_state.show_project_modal = True
            st.rerun()
    with col2:
        if st.button("➡️ Déplacer", key=f"move_kanban_{project_id}_{statut}", help="Déplacer ce projet", use_container_width=True):
            st.session_state.dragged_project_id = project_id
            st.session_state.dragged_from_status = statut
            st.rerun()


def gerer_deplacement_projet(gestionnaire_sqlite, nouveau_statut: str) -> bool:
    """Gère le déplacement d'un projet vers un nouveau statut."""
    projet_id = st.session_state.get('dragged_project_id')
    if not projet_id: 
        return False
    try:
        success = gestionnaire_sqlite.modifier_projet(projet_id, {'statut': nouveau_statut})
        if success:
            st.success(f"✅ Projet #{projet_id} déplacé vers '{nouveau_statut}' !")
            return True
        else:
            st.error("❌ Erreur lors de la mise à jour.")
            return False
    except Exception as e:
        st.error(f"❌ Erreur SQLite : {e}")
        return False


# === FONCTIONS POUR VUE OPÉRATIONS PAR POSTES ===

def filtrer_operations_kanban(operations: List[Dict], recherche: str, filtre_statut: str, filtre_projet: str) -> List[Dict]:
    """Filtre les opérations selon les critères."""
    if not operations: 
        return []
    ops_filtrees = operations
    if recherche:
        terme = recherche.lower().strip()
        ops_filtrees = [op for op in ops_filtrees if any(terme in str(op.get(field, '')).lower() for field in ['description', 'poste_travail', 'nom_projet', 'bt_numero', 'ressource', 'id'])]
    if filtre_statut and filtre_statut != 'TOUS':
        ops_filtrees = [op for op in ops_filtrees if op.get('statut') == filtre_statut]
    if filtre_projet and filtre_projet != 'TOUS':
        ops_filtrees = [op for op in ops_filtrees if str(op.get('project_id')) == filtre_projet]
    return ops_filtrees


def organiser_operations_par_poste(operations: List[Dict], work_centers: List[Dict]) -> Dict[str, List[Dict]]:
    """Organise les opérations par poste de travail."""
    ops_par_poste = {wc['nom']: [] for wc in work_centers}
    ops_par_poste['🚫 Non assigné'] = []
    for op in operations:
        poste_cible = op.get('work_center_name') or op.get('poste_travail')
        if poste_cible and poste_cible in ops_par_poste:
            ops_par_poste[poste_cible].append(op)
        else:
            ops_par_poste['🚫 Non assigné'].append(op)
    return ops_par_poste


def calculer_statistiques_poste(operations: List[Dict]) -> Dict[str, Any]:
    """Calcule les statistiques pour un poste de travail."""
    if not operations: 
        return {'total_operations': 0, 'temps_total_estime': 0.0, 'operations_par_statut': {}, 'charge_critique': False}
    stats = {'total_operations': len(operations), 'temps_total_estime': 0.0, 'operations_par_statut': {}, 'charge_critique': False}
    for op in operations:
        try: 
            stats['temps_total_estime'] += float(op.get('temps_estime', 0) or 0)
        except (ValueError, TypeError): 
            pass
        statut = op.get('statut', 'À FAIRE')
        stats['operations_par_statut'][statut] = stats['operations_par_statut'].get(statut, 0) + 1
    stats['charge_critique'] = (stats['temps_total_estime'] > 40.0 or stats['total_operations'] > 10)
    return stats


def afficher_carte_operation(operation: Dict[str, Any], poste_nom: str, erp_db) -> None:
    """Affiche une carte opération dans le Kanban."""
    op_id, seq = operation.get('id'), operation.get('sequence_number', 0)
    desc, statut = operation.get('description', 'N/A'), operation.get('statut', 'À FAIRE')
    temps_estime = operation.get('temps_estime', 0)
    nom_projet, project_id = operation.get('nom_projet', 'N/A'), operation.get('project_id')
    bt_numero, ressource = operation.get('bt_numero', ''), operation.get('ressource', '')
    priorite = get_operation_priority_from_context(operation, erp_db)
    
    couleur_statut, couleur_priorite = COULEURS_STATUTS_OPERATIONS.get(statut, '#6b7280'), COULEURS_PRIORITES_OPS.get(priorite, '#6b7280')
    icone_priorite = ICONES_PRIORITES_OPS.get(priorite, '⚪')
    icone_dept = ICONES_DEPARTEMENTS.get(operation.get('work_center_departement', 'BUREAU').upper(), '🏭')
    
    st.markdown(f"""
    <div class='kanban-operation-card' style='border-left: 4px solid {couleur_statut}; border-top: 2px solid {couleur_priorite};'>
        <div class='operation-card-header'>
            <span class='operation-id'>#{op_id}-{seq:02d}</span>
            <span class='operation-status' style='background-color: {couleur_statut};'>{statut}</span>
        </div>
        <div class='operation-card-title'>{desc[:60]}{'...' if len(desc) > 60 else ''}</div>
        <div class='operation-card-info'>
            <div class='info-line'>{icone_dept} <strong>Poste:</strong> {poste_nom}</div>
            <div class='info-line'>📋 <strong>Projet:</strong> {nom_projet}</div>
            {f"<div class='info-line'>📄 <strong>BT:</strong> {bt_numero}</div>" if bt_numero else ""}
            <div class='info-line'>⏱️ <strong>Temps:</strong> {format_temps_estime(temps_estime)}</div>
            <div class='info-line'>{icone_priorite} <strong>Priorité:</strong> {priorite}</div>
            {f"<div class='info-line'>🔧 <strong>Ressource:</strong> {ressource}</div>" if ressource else ""}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("👁️", key=f"view_op_{op_id}_{poste_nom}", help="Voir les détails", use_container_width=True):
            st.session_state.selected_operation, st.session_state.show_operation_modal = operation, True
            st.rerun()
    with col2:
        if st.button("📋", key=f"project_op_{op_id}_{poste_nom}", help="Voir le projet", use_container_width=True) and project_id:
            st.session_state.selected_project_id, st.session_state.show_project_details = project_id, True
            st.rerun()
    with col3:
        if st.button("➡️", key=f"move_op_{op_id}_{poste_nom}", help="Réassigner ce poste", use_container_width=True):
            st.session_state.dragged_operation_id, st.session_state.dragged_from_poste = op_id, poste_nom
            st.rerun()


def gerer_reassignation_operation(erp_db, nouveau_poste_nom: str) -> bool:
    """Gère la réassignation d'une opération vers un nouveau poste."""
    op_id = st.session_state.get('dragged_operation_id')
    if not op_id: 
        return False
    try:
        wc_result = erp_db.execute_query("SELECT id FROM work_centers WHERE nom = ?", (nouveau_poste_nom,))
        if not wc_result:
            st.error(f"❌ Poste '{nouveau_poste_nom}' non trouvé.")
            return False
        new_wc_id = wc_result[0]['id']
        affected = erp_db.execute_update("UPDATE operations SET work_center_id = ?, poste_travail = ? WHERE id = ?", (new_wc_id, nouveau_poste_nom, op_id))
        if affected > 0:
            st.success(f"✅ Opération #{op_id} réassignée à '{nouveau_poste_nom}' !")
            return True
        else:
            st.error("❌ Erreur lors de la réassignation.")
            return False
    except Exception as e:
        st.error(f"❌ Erreur réassignation : {e}")
        return False


# === FONCTIONS POUR LA NOUVELLE VUE : BTs PAR POSTES ===

def get_bt_to_workcenter_associations(erp_db):
    """Récupère toutes les associations BT -> Poste via les opérations."""
    try:
        query = """
            SELECT
                f.id as bt_id, f.numero_document as bt_numero, f.statut as bt_statut,
                f.priorite as bt_priorite, f.date_echeance, p.nom_projet, c.nom as client_nom,
                wc.nom as poste_travail_nom
            FROM formulaires f
            JOIN operations o ON f.id = o.formulaire_bt_id
            JOIN work_centers wc ON o.work_center_id = wc.id
            LEFT JOIN projects p ON f.project_id = p.id
            LEFT JOIN companies c ON f.company_id = c.id
            WHERE f.type_formulaire = 'BON_TRAVAIL' AND f.statut NOT IN ('TERMINÉ', 'ANNULÉ')
        """
        return [dict(row) for row in erp_db.execute_query(query)]
    except Exception as e:
        st.error(f"Erreur lors de la récupération des associations BT-Postes : {e}")
        return []


def organiser_bts_par_poste(associations: List[Dict], work_centers: List[Dict]) -> Dict[str, List[Dict]]:
    """Organise les Bons de Travail par poste de travail, en dédupliquant."""
    bts_par_poste_dedup = {wc['nom']: {} for wc in work_centers}
    for row in associations:
        poste_nom = row['poste_travail_nom']
        bt_id = row['bt_id']
        if poste_nom in bts_par_poste_dedup:
            if bt_id not in bts_par_poste_dedup[poste_nom]:
                bts_par_poste_dedup[poste_nom][bt_id] = {
                    'id': bt_id, 
                    'numero_document': row['bt_numero'], 
                    'statut': row['bt_statut'],
                    'priorite': row['bt_priorite'], 
                    'nom_projet': row['nom_projet'],
                    'client_nom': row['client_nom'], 
                    'date_echeance': row['date_echeance']
                }
    return {poste: list(bts.values()) for poste, bts in bts_par_poste_dedup.items()}


def afficher_carte_bt_pour_poste(bt: Dict[str, Any], poste_nom: str) -> None:
    """Affiche une carte Bon de Travail dans le Kanban des postes."""
    bt_id, bt_numero = bt.get('id'), bt.get('numero_document', 'N/A')
    priorite, nom_projet = bt.get('priorite', 'NORMAL'), bt.get('nom_projet', 'Projet non lié')
    
    couleur_priorite = COULEURS_PRIORITES_OPS.get(priorite, '#6b7280')
    icone_priorite = ICONES_PRIORITES_OPS.get(priorite, '⚪')
    
    st.markdown(f"""
    <div class='kanban-operation-card' style='border-left: 4px solid {couleur_priorite};'>
        <div class='operation-card-header'>
            <span class='operation-id'>{bt_numero}</span>
            <span class='operation-status' style='background-color: {get_bt_color(bt.get("statut"))};'>{bt.get("statut")}</span>
        </div>
        <div class='operation-card-title'>Projet: {nom_projet}</div>
        <div class='operation-card-info'>
            <div class='info-line'>{icone_priorite} <strong>Priorité:</strong> {priorite}</div>
            <div class='info-line'>📅 <strong>Échéance:</strong> {bt.get('date_echeance', 'N/A')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("👁️ Voir BT", key=f"view_bt_kanban_{bt_id}_{poste_nom}", use_container_width=True):
        st.session_state.main_mode = 'bt'
        st.session_state.bt_mode = 'view'
        st.session_state.bt_selected_id = bt_id
        if 'page_redirect' in st.session_state:
            st.session_state.page_redirect = 'production_management'
        else:
            st.session_state['current_page'] = 'production_management'
        
        st.info(f"Redirection vers les détails du BT #{bt_id}...")
        st.rerun()


# === FONCTIONS D'AFFICHAGE COMMUNES ===

def afficher_indicateur_drag():
    """Affiche l'indicateur de drag & drop actif pour les projets."""
    if st.session_state.get('dragged_project_id'):
        gestionnaire = st.session_state.gestionnaire
        try:
            projet_dragged = next((p for p in gestionnaire.projets if p.get('id') == st.session_state.dragged_project_id), None)
            if projet_dragged:
                st.markdown(f"""
                <div class="kanban-drag-indicator">
                    🔄 Déplacement: <strong>#{projet_dragged.get('id')} - {projet_dragged.get('nom_projet', 'N/A')}</strong>
                </div>
                """, unsafe_allow_html=True)
                if st.sidebar.button("❌ Annuler déplacement", use_container_width=True):
                    st.session_state.dragged_project_id, st.session_state.dragged_from_status = None, None
                    st.rerun()
        except:
            pass


def afficher_indicateur_drag_operations():
    """Affiche l'indicateur de drag & drop actif pour les opérations."""
    if st.session_state.get('dragged_operation_id'):
        op_id, from_poste = st.session_state.get('dragged_operation_id'), st.session_state.get('dragged_from_poste', 'N/A')
        st.markdown(f"""
        <div class="kanban-drag-indicator">
            🔄 Réassignation: <strong>Opération #{op_id}</strong> depuis <strong>{from_poste}</strong>
        </div>
        """, unsafe_allow_html=True)
        if st.sidebar.button("❌ Annuler réassignation", use_container_width=True):
            st.session_state.dragged_operation_id, st.session_state.dragged_from_poste = None, None
            st.rerun()


def afficher_css_kanban() -> None:
    """Affiche le CSS personnalisé pour le Kanban unifié."""
    st.markdown("""
    <style>
    /* === KANBAN UNIFIÉ - STYLE MODERNE PROJETS + OPÉRATIONS === */
    :root {
        --primary-color: #00A971; 
        --primary-color-darker: #00673D;
        --primary-color-light: #66d9af;
        --primary-color-lighter: #e6f7f1;
        --background-color: #F9FAFB;
        --secondary-background-color: #FFFFFF;
        --text-color: #374151;
        --text-color-light: #6B7280;
        --text-color-muted: #9CA3AF;
        --border-color: #E5E7EB;
        --border-color-light: #F3F4F6;
    }
    
    .kanban-container, .kanban-operations-container {
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
    
    .kanban-column, .kanban-operations-column {
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
    
    .kanban-column:hover, .kanban-operations-column:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.12);
    }
    
    .kanban-header, .kanban-operations-header {
        font-weight: 700;
        text-align: center;
        padding: 15px 20px;
        margin: 0;
        color: white;
        border-radius: 12px 12px 0 0;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    
    .kanban-header { 
        font-size: 1.1em; 
        border-bottom: 3px solid var(--primary-color-darker); 
    }
    
    .kanban-operations-header { 
        font-size: 0.95em; 
        background: linear-gradient(135deg, #1f2937, #374151); 
        border-bottom: 3px solid #1f2937; 
    }
    
    .kanban-operations-header.charge-critique { 
        background: linear-gradient(135deg, #dc2626, #ef4444) !important; 
        border-bottom-color: #dc2626 !important; 
    }
    
    .kanban-cards-zone, .kanban-operations-cards-zone { 
        flex-grow: 1; 
        overflow-y: auto; 
        padding: 15px; 
        max-height: 600px; 
    }
    
    .kanban-cards-zone::-webkit-scrollbar, .kanban-operations-cards-zone::-webkit-scrollbar { 
        width: 6px; 
    }
    
    .kanban-cards-zone::-webkit-scrollbar-track, .kanban-operations-cards-zone::-webkit-scrollbar-track { 
        background: var(--secondary-background-color); 
        border-radius: 3px; 
    }
    
    .kanban-cards-zone::-webkit-scrollbar-thumb, .kanban-operations-cards-zone::-webkit-scrollbar-thumb { 
        background: var(--primary-color-light); 
        border-radius: 3px; 
    }
    
    .kanban-card, .kanban-operation-card { 
        background: var(--secondary-background-color); 
        border-radius: 12px; 
        padding: 16px; 
        margin-bottom: 16px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); 
        transition: all 0.3s ease; 
        color: var(--text-color); 
        position: relative; 
        overflow: hidden; 
    }
    
    .kanban-operation-card { 
        padding: 12px; 
        margin-bottom: 12px; 
    }
    
    .kanban-card:hover, .kanban-operation-card:hover { 
        transform: translateY(-4px); 
        box-shadow: 0 8px 25px rgba(0,0,0,0.15); 
    }
    
    .kanban-card-title { 
        font-weight: 600; 
        font-size: 0.95em; 
        margin-bottom: 8px; 
        color: var(--primary-color-darker); 
        line-height: 1.3; 
    }
    
    .operation-card-header { 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        margin-bottom: 8px; 
    }
    
    .operation-id { 
        font-weight: 600; 
        font-size: 0.8em; 
        color: var(--primary-color-darker); 
        font-family: monospace; 
    }
    
    .operation-status { 
        font-size: 0.7em; 
        color: white; 
        padding: 2px 6px; 
        border-radius: 10px; 
        font-weight: 600; 
        text-transform: uppercase; 
    }
    
    .operation-card-title { 
        font-weight: 600; 
        font-size: 0.9em; 
        margin-bottom: 10px; 
        color: var(--text-color); 
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
    
    .operation-card-info { 
        font-size: 0.8em; 
        color: var(--text-color-muted); 
    }
    
    .info-line { 
        margin-bottom: 3px; 
        display: flex; 
        align-items: center; 
        gap: 4px; 
    }
    
    .info-line strong { 
        color: var(--text-color); 
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
    
    .kanban-stats, .operations-summary { 
        background: var(--secondary-background-color); 
        border-radius: 12px; 
        padding: 20px; 
        margin-top: 25px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.08); 
        border: 1px solid var(--border-color-light); 
    }
    
    .empty-column, .empty-poste-column { 
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
    
    .drop-zone-operations { 
        background: linear-gradient(135deg, #3b82f6, #60a5fa); 
        border: 2px dashed #1d4ed8; 
        border-radius: 8px; 
        padding: 10px; 
        margin-bottom: 12px; 
        text-align: center; 
        color: white; 
        font-weight: 500; 
        transition: all 0.3s ease; 
        font-size: 0.85em; 
    }
    
    .drop-zone-operations:hover { 
        background: linear-gradient(135deg, #1d4ed8, #3b82f6); 
        transform: scale(1.02); 
    }
    
    .poste-stats { 
        background: var(--secondary-background-color); 
        padding: 8px; 
        border-radius: 6px; 
        margin-bottom: 10px; 
        font-size: 0.75em; 
        color: var(--text-color-muted); 
    }
    
    .poste-stats-row { 
        display: flex; 
        justify-content: space-between; 
        margin-bottom: 2px; 
    }
    
    .mode-selector { 
        background: var(--secondary-background-color); 
        border-radius: 12px; 
        padding: 15px; 
        margin-bottom: 20px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); 
        border: 1px solid var(--border-color-light); 
    }
    </style>
    """, unsafe_allow_html=True)


# === VUES PRINCIPALES DU KANBAN ===

def show_kanban_projets():
    """Affiche la vue Kanban des projets par statuts."""
    if 'gestionnaire' not in st.session_state or 'gestionnaire_crm' not in st.session_state:
        st.error("⚠️ Gestionnaires non initialisés.")
        return
    
    gestionnaire, crm_manager = st.session_state.gestionnaire, st.session_state.gestionnaire_crm
    
    # Initialisation des variables de session pour drag & drop
    if 'dragged_project_id' not in st.session_state:
        st.session_state.dragged_project_id = None
    if 'dragged_from_status' not in st.session_state:
        st.session_state.dragged_from_status = None
    
    try:
        projets = gestionnaire.projets
        if not projets:
            st.info("📋 Aucun projet trouvé en base SQLite.")
            return
    except Exception as e:
        st.error(f"❌ Erreur récupération projets : {e}")
        return

    with st.expander("🔍 Filtres", expanded=False):
        recherche = st.text_input("Rechercher...", key="kanban_search_projets")
    
    projets_filtres = filtrer_projets_kanban(projets, recherche, crm_manager)
    projets_par_statut = organiser_projets_par_statut(projets_filtres)
    
    afficher_indicateur_drag()
    
    st.markdown('<div class="kanban-container">', unsafe_allow_html=True)
    colonnes = st.columns(len(STATUTS_KANBAN))
    
    for idx, statut in enumerate(STATUTS_KANBAN):
        with colonnes[idx]:
            nombre_projets = len(projets_par_statut[statut])
            couleur_statut = COULEURS_STATUTS.get(statut, '#6b7280')
            
            st.markdown(f"""
            <div class="kanban-column" style="border-top: 4px solid {couleur_statut};">
                <div class="kanban-header" style="background: linear-gradient(135deg, {couleur_statut}, {couleur_statut}dd);">
                    {statut} ({nombre_projets})
                </div>
            """, unsafe_allow_html=True)
            
            # Zone de dépôt pour drag & drop
            if st.session_state.get('dragged_project_id') and statut != st.session_state.get('dragged_from_status'):
                st.markdown('<div class="drop-zone">', unsafe_allow_html=True)
                if st.button(f"⤵️ Déposer ici", key=f"drop_{statut}", use_container_width=True):
                    if gerer_deplacement_projet(gestionnaire, statut):
                        st.session_state.dragged_project_id, st.session_state.dragged_from_status = None, None
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="kanban-cards-zone">', unsafe_allow_html=True)
            
            if not projets_par_statut[statut]:
                st.markdown('<div class="empty-column">📝 Aucun projet</div>', unsafe_allow_html=True)
            else:
                projets_tries = sorted(projets_par_statut[statut], 
                                     key=lambda p: (PRIORITES.index(p.get('priorite', 'BAS')) if p.get('priorite') in PRIORITES else 99, 
                                                   p.get('date_prevu', '9999-12-31')))
                for projet in projets_tries:
                    afficher_carte_projet(projet, crm_manager, statut)
            
            st.markdown('</div></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    # Statistiques détaillées
    if projets_filtres:
        stats = calculer_statistiques_kanban(projets_filtres)
        st.markdown('<div class="kanban-stats"><h3>📊 Statistiques</h3>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🗄️ Total", stats['total'])
        c2.metric("🚀 Actifs", stats['actifs'])
        c3.metric("💰 CA Total", f"{stats['ca_total']:,.0f}$")
        c4.metric("📅 Durée Moy.", f"{stats['duree_moyenne']:.0f}j")
        st.markdown('</div>', unsafe_allow_html=True)


def show_kanban_bts_par_poste():
    """NOUVELLE VUE : Affiche les Bons de Travail regroupés par Poste de Travail."""
    if 'erp_db' not in st.session_state:
        st.error("⚠️ Base de données ERP non initialisée.")
        return

    erp_db = st.session_state.erp_db
    
    try:
        work_centers = erp_db.execute_query("SELECT * FROM work_centers WHERE statut = 'ACTIF' ORDER BY departement, nom")
        work_centers = [dict(wc) for wc in work_centers]
        
        if not work_centers:
            st.warning("🏭 Aucun poste de travail actif trouvé.")
            return

        associations_bt_poste = get_bt_to_workcenter_associations(erp_db)
        bts_par_poste = organiser_bts_par_poste(associations_bt_poste, work_centers)
        
        st.markdown('<div class="kanban-operations-container">', unsafe_allow_html=True)
        postes_a_afficher = [wc['nom'] for wc in work_centers]

        for poste_nom in postes_a_afficher:
            bts_poste = bts_par_poste.get(poste_nom, [])
            stats_poste = {'total_bts': len(bts_poste)}

            st.markdown(f'''
            <div class="kanban-operations-column">
                <div class="kanban-operations-header">
                    🔧 {poste_nom} ({stats_poste["total_bts"]})
                </div>
            ''', unsafe_allow_html=True)
            
            st.markdown('<div class="kanban-operations-cards-zone">', unsafe_allow_html=True)
            
            if not bts_poste:
                st.markdown('<div class="empty-poste-column">📋 Aucun BT</div>', unsafe_allow_html=True)
            else:
                bts_tries = sorted(bts_poste, 
                                 key=lambda bt: (PRIORITES.index(bt.get('priorite', 'BAS')) if bt.get('priorite') in PRIORITES else 99, 
                                               bt.get('date_echeance', '9999-12-31')))
                for bt in bts_tries:
                    afficher_carte_bt_pour_poste(bt, poste_nom)

            st.markdown('</div></div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"❌ Erreur lors de l'affichage du Kanban des BTs : {e}")


def show_kanban_operations():
    """Affiche la vue Kanban des opérations par postes de travail."""
    if 'erp_db' not in st.session_state:
        st.error("⚠️ Base de données ERP non initialisée.")
        return
    
    erp_db = st.session_state.erp_db
    
    # Initialisation des variables de session pour drag & drop
    if 'dragged_operation_id' not in st.session_state:
        st.session_state.dragged_operation_id = None
    if 'dragged_from_poste' not in st.session_state:
        st.session_state.dragged_from_poste = None
    
    try:
        work_centers = [dict(wc) for wc in erp_db.execute_query("SELECT * FROM work_centers WHERE statut = 'ACTIF' ORDER BY departement, nom")]
        operations = [dict(op) for op in erp_db.execute_query('''
            SELECT o.*, wc.nom as work_center_name, wc.departement as work_center_departement, 
                   p.nom_projet, f.numero_document as bt_numero
            FROM operations o
            LEFT JOIN work_centers wc ON o.work_center_id = wc.id
            LEFT JOIN projects p ON o.project_id = p.id
            LEFT JOIN formulaires f ON o.formulaire_bt_id = f.id AND f.type_formulaire = 'BON_TRAVAIL'
            ORDER BY o.sequence_number, o.id
        ''')]
        
        if not work_centers:
            st.warning("🏭 Aucun poste de travail actif trouvé.")
            return
        
        if not operations:
            st.info("⚙️ Aucune opération trouvée.")
            return
            
    except Exception as e:
        st.error(f"❌ Erreur de récupération des données : {e}")
        return
    
    # Interface de filtrage
    with st.expander("🔍 Filtres", expanded=False):
        c1, c2, c3 = st.columns(3)
        recherche = c1.text_input("Rechercher...", key="kanban_ops_search")
        filtre_statut = c2.selectbox("Statut", ['TOUS'] + sorted(list(set(op.get('statut', 'À FAIRE') for op in operations))), key="filtre_statut_ops")
        filtre_projet = c3.selectbox("Projet", ['TOUS'] + sorted(list(set(str(op.get('project_id', '')) for op in operations if op.get('project_id')))), key="filtre_projet_ops")
    
    operations_filtrees = filtrer_operations_kanban(operations, recherche, filtre_statut, filtre_projet)
    operations_par_poste = organiser_operations_par_poste(operations_filtrees, work_centers)
    
    afficher_indicateur_drag_operations()
    
    st.markdown('<div class="kanban-operations-container">', unsafe_allow_html=True)
    postes_a_afficher = sorted(list(operations_par_poste.keys()), key=lambda p: (len(operations_par_poste[p]) == 0, p))
    
    for poste_nom in postes_a_afficher:
        operations_poste = operations_par_poste.get(poste_nom, [])
        stats_poste = calculer_statistiques_poste(operations_poste)
        classe_header = "charge-critique" if stats_poste['charge_critique'] else ""
        
        st.markdown(f'''
        <div class="kanban-operations-column">
            <div class="kanban-operations-header {classe_header}">
                ⚙️ {poste_nom} ({stats_poste["total_operations"]})
            </div>
        ''', unsafe_allow_html=True)
        
        # Zone de dépôt pour drag & drop
        if (st.session_state.get('dragged_operation_id') and 
            poste_nom != st.session_state.get('dragged_from_poste') and 
            poste_nom != '🚫 Non assigné'):
            st.markdown('<div class="drop-zone-operations">', unsafe_allow_html=True)
            if st.button(f"⤵️ Réassigner ici", key=f"drop_ops_{poste_nom}", use_container_width=True):
                if gerer_reassignation_operation(erp_db, poste_nom):
                    st.session_state.dragged_operation_id, st.session_state.dragged_from_poste = None, None
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="kanban-operations-cards-zone">', unsafe_allow_html=True)
        
        if not operations_poste:
            st.markdown('<div class="empty-poste-column">🔧 Aucune opération</div>', unsafe_allow_html=True)
        else:
            ops_tries = sorted(operations_poste, 
                             key=lambda op: (0 if get_operation_priority_from_context(op, erp_db) in ['CRITIQUE', 'URGENT'] else 1, 
                                           0 if op.get('statut') == 'EN COURS' else 1, 
                                           op.get('sequence_number', 999)))
            for op in ops_tries:
                afficher_carte_operation(op, poste_nom, erp_db)
        
        st.markdown('</div></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def afficher_modal_operation():
    """Affiche la modale de détails d'une opération."""
    if st.session_state.get('show_operation_modal') and st.session_state.get('selected_operation'):
        operation = st.session_state.selected_operation
        
        with st.expander("🔍 Détails de l'Opération", expanded=True):
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown(f"""
                **ID:** {operation.get('id')}<br>
                **Séquence:** {operation.get('sequence_number')}<br>
                **Description:** {operation.get('description')}
                """, unsafe_allow_html=True)
            
            with c2:
                st.markdown(f"""
                **Statut:** {operation.get('statut')}<br>
                **Temps estimé:** {format_temps_estime(operation.get('temps_estime'))}<br>
                **Poste:** {operation.get('work_center_name') or operation.get('poste_travail')}
                """, unsafe_allow_html=True)
            
            if st.button("❌ Fermer", key="close_op_modal"):
                st.session_state.show_operation_modal = False
                st.session_state.selected_operation = None
                st.rerun()


# === FONCTION PRINCIPALE UNIFIÉE ===

def show_kanban_sqlite():
    """Fonction principale - Vue Kanban Unifiée."""
    afficher_css_kanban()
    
    st.markdown("## 🔄 Vue Kanban Unifiée - ERP Production DG Inc.")
    st.markdown('<div class="sqlite-indicator">🗄️ Données en temps réel depuis SQLite</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="mode-selector">', unsafe_allow_html=True)
    mode_kanban = st.radio(
        "**Choisissez le mode d'affichage:**",
        [
            "📋 Projets par Statuts", 
            "🏭 BTs par Postes de Travail",
            "⚙️ Opérations par Postes"
        ],
        key="kanban_mode_selector", 
        horizontal=True
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    if mode_kanban == "📋 Projets par Statuts":
        st.markdown("### 📋 Vue Projets - Organisés par Statuts")
        show_kanban_projets()
    elif mode_kanban == "🏭 BTs par Postes de Travail":
        st.markdown("### 🏭 Vue Bons de Travail - Organisés par Postes")
        show_kanban_bts_par_poste()
    else:
        st.markdown("### ⚙️ Vue Opérations - Organisées par Postes")
        show_kanban_operations()


# === POINTS D'ENTRÉE POUR APP.PY ===

def show_kanban():
    """Point d'entrée principal pour l'affichage du Kanban."""
    show_kanban_sqlite()


def app():
    """Fonction app() pour compatibilité avec les anciens appels."""
    show_kanban_sqlite()
    if st.session_state.get('show_operation_modal'):
        afficher_modal_operation()


# === TEST AUTONOME ===
if __name__ == "__main__":
    st.title("🔄 Module Kanban Unifié - Test Autonome")
    st.info("Version unifiée pour projets et opérations avec l'architecture SQLite")
    
    if 'gestionnaire' not in st.session_state or 'erp_db' not in st.session_state:
        st.error("⚠️ Ce module doit être lancé depuis app.py.")
        st.stop()
    
    show_kanban_sqlite()

# --- END OF FILE kanban.py - VERSION UNIFIÉE PROJETS + BTs + OPÉRATIONS (COMPLET) ---
