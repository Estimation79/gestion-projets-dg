# --- START OF FILE kanban.py - VERSION UNIFIÉE PROJETS + OPÉRATIONS ---

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

# KANBAN UNIFIÉ - Vue Projets par Statuts + Vue Opérations par Postes de Travail
# Compatible avec app.py et erp_database.py pour une intégration complète

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

# === CONFIGURATION POUR VUE OPÉRATIONS ===
# Configuration des couleurs pour les statuts d'opérations
COULEURS_STATUTS_OPERATIONS = {
    'À FAIRE': '#f59e0b',      # Orange
    'EN COURS': '#3b82f6',     # Bleu
    'EN ATTENTE': '#ef4444',   # Rouge
    'TERMINÉ': '#10b981',      # Vert
    'SUSPENDU': '#8b5cf6',     # Violet
    'ANNULÉ': '#6b7280'        # Gris
}

# Configuration des couleurs pour les priorités d'opérations
COULEURS_PRIORITES_OPS = {
    'CRITIQUE': '#ef4444',    # Rouge
    'URGENT': '#f59e0b',      # Orange
    'ÉLEVÉ': '#f59e0b',       # Orange
    'NORMAL': '#10b981',      # Vert
    'MOYEN': '#10b981',       # Vert
    'BAS': '#6b7280'          # Gris
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
    'BUREAU': '📋'
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


def format_temps_estime(temps: float) -> str:
    """Formate le temps estimé en heures"""
    if temps is None or temps == 0:
        return "0.0h"
    
    try:
        return f"{float(temps):.1f}h"
    except (ValueError, TypeError):
        return "0.0h"


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


def get_operation_priority_from_context(operation: Dict, erp_db) -> str:
    """Récupère la priorité d'une opération depuis son contexte (projet ou BT)"""
    try:
        # 1. Priorité depuis le BT si lié
        if operation.get('formulaire_bt_id'):
            bt_info = erp_db.execute_query(
                "SELECT priorite FROM formulaires WHERE id = ? AND type_formulaire = 'BON_TRAVAIL'",
                (operation['formulaire_bt_id'],)
            )
            if bt_info and bt_info[0]['priorite']:
                return bt_info[0]['priorite']
        
        # 2. Priorité depuis le projet
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


# === FONCTIONS POUR VUE OPÉRATIONS ===

def filtrer_operations_kanban(operations: List[Dict], recherche: str, filtre_statut: str, filtre_projet: str) -> List[Dict]:
    """Filtre les opérations selon les critères"""
    if not operations:
        return []
    
    operations_filtrees = operations
    
    # Filtre par recherche
    if recherche:
        terme = recherche.lower().strip()
        operations_filtrees = [
            op for op in operations_filtrees
            if (terme in str(op.get('description', '')).lower() or
                terme in str(op.get('poste_travail', '')).lower() or
                terme in str(op.get('nom_projet', '')).lower() or
                terme in str(op.get('bt_numero', '')).lower() or
                terme in str(op.get('ressource', '')).lower() or
                terme in str(op.get('id', '')))
        ]
    
    # Filtre par statut
    if filtre_statut and filtre_statut != 'TOUS':
        operations_filtrees = [
            op for op in operations_filtrees
            if op.get('statut') == filtre_statut
        ]
    
    # Filtre par projet
    if filtre_projet and filtre_projet != 'TOUS':
        operations_filtrees = [
            op for op in operations_filtrees
            if str(op.get('project_id')) == filtre_projet
        ]
    
    return operations_filtrees


def organiser_operations_par_poste(operations: List[Dict], work_centers: List[Dict]) -> Dict[str, List[Dict]]:
    """Organise les opérations par poste de travail"""
    operations_par_poste = {}
    
    # Initialiser avec tous les postes de travail
    for wc in work_centers:
        poste_nom = wc['nom']
        operations_par_poste[poste_nom] = []
    
    # Ajouter une colonne pour les opérations non assignées
    operations_par_poste['🚫 Non assigné'] = []
    
    # Répartir les opérations
    for operation in operations:
        work_center_name = operation.get('work_center_name')
        poste_travail = operation.get('poste_travail')
        
        # Utiliser work_center_name en priorité, puis poste_travail
        poste_cible = work_center_name or poste_travail
        
        if poste_cible and poste_cible in operations_par_poste:
            operations_par_poste[poste_cible].append(operation)
        else:
            operations_par_poste['🚫 Non assigné'].append(operation)
    
    return operations_par_poste


def calculer_statistiques_poste(operations: List[Dict]) -> Dict[str, Any]:
    """Calcule les statistiques pour un poste de travail"""
    if not operations:
        return {
            'total_operations': 0,
            'temps_total_estime': 0.0,
            'operations_par_statut': {},
            'charge_critique': False
        }
    
    stats = {
        'total_operations': len(operations),
        'temps_total_estime': 0.0,
        'operations_par_statut': {},
        'charge_critique': False
    }
    
    # Calculer temps total et répartition par statut
    for op in operations:
        temps = op.get('temps_estime', 0) or 0
        try:
            stats['temps_total_estime'] += float(temps)
        except (ValueError, TypeError):
            pass
        
        statut = op.get('statut', 'À FAIRE')
        stats['operations_par_statut'][statut] = stats['operations_par_statut'].get(statut, 0) + 1
    
    # Déterminer si la charge est critique (plus de 40h ou plus de 10 opérations)
    stats['charge_critique'] = (stats['temps_total_estime'] > 40.0 or stats['total_operations'] > 10)
    
    return stats


def afficher_carte_operation(operation: Dict[str, Any], poste_nom: str, erp_db) -> None:
    """Affiche une carte opération dans le Kanban"""
    
    # Données de la carte
    operation_id = operation.get('id')
    sequence_number = operation.get('sequence_number', 0)
    description = operation.get('description', 'Description non spécifiée')
    statut = operation.get('statut', 'À FAIRE')
    temps_estime = operation.get('temps_estime', 0)
    nom_projet = operation.get('nom_projet', 'Projet inconnu')
    project_id = operation.get('project_id')
    bt_numero = operation.get('bt_numero', '')
    ressource = operation.get('ressource', '')
    
    # Récupérer la priorité depuis le contexte
    priorite = get_operation_priority_from_context(operation, erp_db)
    
    # Couleurs et icônes
    couleur_statut = COULEURS_STATUTS_OPERATIONS.get(statut, '#6b7280')
    couleur_priorite = COULEURS_PRIORITES_OPS.get(priorite, '#6b7280')
    icone_priorite = ICONES_PRIORITES_OPS.get(priorite, '⚪')
    
    # Icône du département
    departement = operation.get('work_center_departement', 'BUREAU')
    icone_dept = ICONES_DEPARTEMENTS.get(departement.upper(), '🏭')
    
    # Affichage de la carte
    st.markdown(f"""
    <div class='kanban-operation-card' style='border-left: 4px solid {couleur_statut}; border-top: 2px solid {couleur_priorite};'>
        <div class='operation-card-header'>
            <span class='operation-id'>#{operation_id}-{sequence_number:02d}</span>
            <span class='operation-status' style='background-color: {couleur_statut};'>{statut}</span>
        </div>
        <div class='operation-card-title'>{description[:60]}{'...' if len(description) > 60 else ''}</div>
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
    
    # Boutons d'action
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("👁️", 
                     key=f"view_op_{operation_id}_{poste_nom}", 
                     help="Voir les détails", 
                     use_container_width=True):
            st.session_state.selected_operation = operation
            st.session_state.show_operation_modal = True
            st.rerun()
    
    with col2:
        if st.button("📋", 
                     key=f"project_op_{operation_id}_{poste_nom}", 
                     help="Voir le projet", 
                     use_container_width=True):
            if project_id:
                st.session_state.selected_project_id = project_id
                st.session_state.show_project_details = True
                st.rerun()
    
    with col3:
        if st.button("➡️", 
                     key=f"move_op_{operation_id}_{poste_nom}", 
                     help="Réassigner ce poste", 
                     use_container_width=True):
            st.session_state.dragged_operation_id = operation_id
            st.session_state.dragged_from_poste = poste_nom
            st.rerun()


def gerer_reassignation_operation(erp_db, nouveau_poste_nom: str) -> bool:
    """Gère la réassignation d'une opération vers un nouveau poste"""
    operation_id = st.session_state.dragged_operation_id
    
    if not operation_id:
        return False
    
    try:
        # Trouver le work_center_id du nouveau poste
        wc_result = erp_db.execute_query(
            "SELECT id FROM work_centers WHERE nom = ?",
            (nouveau_poste_nom,)
        )
        
        if not wc_result:
            st.error(f"❌ Poste de travail '{nouveau_poste_nom}' non trouvé.")
            return False
        
        new_work_center_id = wc_result[0]['id']
        
        # Mettre à jour l'opération
        affected = erp_db.execute_update(
            "UPDATE operations SET work_center_id = ?, poste_travail = ? WHERE id = ?",
            (new_work_center_id, nouveau_poste_nom, operation_id)
        )
        
        if affected > 0:
            st.success(f"✅ Opération #{operation_id} réassignée au poste '{nouveau_poste_nom}' !")
            return True
        else:
            st.error("❌ Erreur lors de la réassignation.")
            return False
            
    except Exception as e:
        st.error(f"❌ Erreur lors de la réassignation : {e}")
        return False


# === FONCTIONS D'AFFICHAGE COMMUNES ===

def afficher_indicateur_drag() -> None:
    """Affiche l'indicateur de drag & drop actif"""
    if st.session_state.get('dragged_project_id'):
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


def afficher_indicateur_drag_operations() -> None:
    """Affiche l'indicateur de drag & drop actif pour les opérations"""
    if st.session_state.get('dragged_operation_id'):
        operation_id = st.session_state.dragged_operation_id
        from_poste = st.session_state.get('dragged_from_poste', 'Poste inconnu')
        
        st.markdown(f"""
        <div class="kanban-drag-indicator">
            🔄 Réassignation en cours: <strong>Opération #{operation_id}</strong> depuis <strong>{from_poste}</strong>
        </div>
        """, unsafe_allow_html=True)
        
        # Bouton d'annulation dans la sidebar
        if st.sidebar.button("❌ Annuler la réassignation", use_container_width=True):
            st.session_state.dragged_operation_id = None
            st.session_state.dragged_from_poste = None
            st.rerun()


def afficher_css_kanban() -> None:
    """Affiche le CSS personnalisé pour le Kanban unifié"""
    st.markdown("""
    <style>
    /* === KANBAN UNIFIÉ - STYLE MODERNE PROJETS + OPÉRATIONS === */
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
    
    .kanban-operations-container {
        display: flex;
        flex-direction: row;
        gap: 15px;
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
    
    .kanban-operations-column {
        flex: 0 0 320px;
        width: 320px;
        background: var(--background-color);
        border-radius: 12px;
        padding: 0;
        display: flex;
        flex-direction: column;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        border: 1px solid var(--border-color-light);
        transition: transform 0.2s ease;
    }
    
    .kanban-column:hover,
    .kanban-operations-column:hover {
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
    
    .kanban-operations-header {
        font-weight: 700;
        font-size: 0.95em;
        text-align: center;
        padding: 12px 15px;
        margin: 0;
        color: white;
        background: linear-gradient(135deg, #1f2937, #374151);
        border-radius: 12px 12px 0 0;
        border-bottom: 3px solid #1f2937;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    
    .kanban-operations-header.charge-critique {
        background: linear-gradient(135deg, #dc2626, #ef4444) !important;
        border-bottom-color: #dc2626 !important;
    }
    
    .kanban-cards-zone {
        flex-grow: 1;
        overflow-y: auto;
        padding: 15px;
        max-height: 600px;
    }
    
    .kanban-operations-cards-zone {
        flex-grow: 1;
        overflow-y: auto;
        padding: 10px;
        max-height: 600px;
    }
    
    .kanban-cards-zone::-webkit-scrollbar,
    .kanban-operations-cards-zone::-webkit-scrollbar {
        width: 6px;
    }
    
    .kanban-cards-zone::-webkit-scrollbar-track,
    .kanban-operations-cards-zone::-webkit-scrollbar-track {
        background: var(--secondary-background-color);
        border-radius: 3px;
    }
    
    .kanban-cards-zone::-webkit-scrollbar-thumb,
    .kanban-operations-cards-zone::-webkit-scrollbar-thumb {
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
    
    .kanban-operation-card {
        background: var(--card-background);
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid transparent;
        border-top: 2px solid transparent;
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
    
    .kanban-card:hover,
    .kanban-operation-card:hover {
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
    
    .sqlite-indicator-ops {
        background: linear-gradient(135deg, #059669, #10b981);
        color: white;
        padding: 10px 16px;
        border-radius: 25px;
        font-size: 0.85em;
        font-weight: 600;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(5, 150, 105, 0.3);
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
    
    .operations-summary {
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
    
    .empty-poste-column {
        text-align: center;
        color: var(--text-color-muted);
        margin-top: 40px;
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
        background: var(--card-background);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid var(--border-color-light);
    }
    </style>
    """, unsafe_allow_html=True)


# === VUE PROJETS PAR STATUTS ===

def show_kanban_projets():
    """Affiche la vue Kanban des projets par statuts"""
    
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


# === VUE OPÉRATIONS PAR POSTES ===

def show_kanban_operations():
    """Affiche la vue Kanban des opérations par postes de travail"""
    
    # === VÉRIFICATION DE L'ARCHITECTURE ===
    if 'erp_db' not in st.session_state:
        st.error("⚠️ Base de données ERP non initialisée.")
        st.info("💡 Veuillez démarrer l'application depuis app.py pour initialiser la base SQLite.")
        return
    
    erp_db = st.session_state.erp_db
    
    # === INITIALISATION DES VARIABLES DE SESSION ===
    if 'dragged_operation_id' not in st.session_state:
        st.session_state.dragged_operation_id = None
    if 'dragged_from_poste' not in st.session_state:
        st.session_state.dragged_from_poste = None
    
    # === RÉCUPÉRATION DES DONNÉES ===
    try:
        # Récupérer tous les postes de travail actifs
        work_centers = erp_db.execute_query(
            "SELECT * FROM work_centers WHERE statut = 'ACTIF' ORDER BY departement, nom"
        )
        work_centers = [dict(wc) for wc in work_centers]
        
        if not work_centers:
            st.warning("🏭 Aucun poste de travail actif trouvé.")
            st.info("💡 Créez des postes de travail depuis la gestion des ressources.")
            return
        
        # Récupérer toutes les opérations avec détails complets
        operations = erp_db.execute_query('''
            SELECT o.*, 
                   wc.nom as work_center_name, 
                   wc.departement as work_center_departement,
                   wc.capacite_theorique,
                   wc.cout_horaire as work_center_cout_horaire,
                   p.nom_projet,
                   f.numero_document as bt_numero,
                   f.statut as bt_statut,
                   f.priorite as bt_priorite
            FROM operations o
            LEFT JOIN work_centers wc ON o.work_center_id = wc.id
            LEFT JOIN projects p ON o.project_id = p.id
            LEFT JOIN formulaires f ON o.formulaire_bt_id = f.id AND f.type_formulaire = 'BON_TRAVAIL'
            ORDER BY o.sequence_number, o.id
        ''')
        operations = [dict(op) for op in operations]
        
        if not operations:
            st.info("⚙️ Aucune opération trouvée.")
            st.markdown("💡 **Créez des opérations** depuis la gestion des projets ou des bons de travail.")
            return
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la récupération des données : {e}")
        return
    
    # === INTERFACE DE FILTRAGE ===
    with st.expander("🔍 Filtres et Options", expanded=False):
        col_filtre1, col_filtre2, col_filtre3, col_filtre4 = st.columns(4)
        
        with col_filtre1:
            recherche = st.text_input(
                "Rechercher...", 
                key="kanban_ops_search",
                placeholder="Description, poste, projet..."
            )
        
        with col_filtre2:
            statuts_disponibles = ['TOUS'] + list(set(op.get('statut', 'À FAIRE') for op in operations))
            filtre_statut = st.selectbox("Statut", statuts_disponibles, key="filtre_statut_ops")
        
        with col_filtre3:
            projets_disponibles = ['TOUS'] + list(set(str(op.get('project_id', '')) for op in operations if op.get('project_id')))
            filtre_projet = st.selectbox("Projet", projets_disponibles, key="filtre_projet_ops")
        
        with col_filtre4:
            afficher_stats = st.toggle("📊 Statistiques détaillées", value=True)
    
    # === FILTRAGE DES OPÉRATIONS ===
    operations_filtrees = filtrer_operations_kanban(operations, recherche, filtre_statut, filtre_projet)
    
    if (recherche or filtre_statut != 'TOUS' or filtre_projet != 'TOUS') and not operations_filtrees:
        st.warning("🔍 Aucune opération ne correspond aux filtres appliqués")
        return
    
    # === ORGANISATION PAR POSTE ===
    operations_par_poste = organiser_operations_par_poste(operations_filtrees, work_centers)
    
    # === AFFICHAGE INDICATEUR DRAG & DROP ===
    afficher_indicateur_drag_operations()
    
    # === STATISTIQUES RAPIDES ===
    if afficher_stats:
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        
        total_ops = len(operations_filtrees)
        temps_total = sum(op.get('temps_estime', 0) or 0 for op in operations_filtrees)
        postes_utilises = len([poste for poste, ops in operations_par_poste.items() if ops and poste != '🚫 Non assigné'])
        
        with col_stat1:
            st.metric("⚙️ Total Opérations", total_ops)
        
        with col_stat2:
            st.metric("⏱️ Temps Total", f"{temps_total:.1f}h")
        
        with col_stat3:
            st.metric("🏭 Postes Utilisés", postes_utilises)
        
        with col_stat4:
            ops_non_assignees = len(operations_par_poste.get('🚫 Non assigné', []))
            st.metric("🚫 Non Assignées", ops_non_assignees)
    
    # === AFFICHAGE DU KANBAN ===
    st.markdown('<div class="kanban-operations-container">', unsafe_allow_html=True)
    
    # Calculer le nombre de colonnes à afficher
    postes_avec_operations = [poste for poste, ops in operations_par_poste.items() if ops]
    tous_postes = list(operations_par_poste.keys())
    
    # Afficher d'abord les postes avec opérations, puis les postes vides (limités)
    postes_a_afficher = postes_avec_operations + [p for p in tous_postes if p not in postes_avec_operations][:5]
    
    # Créer les colonnes
    for poste_nom in postes_a_afficher:
        operations_poste = operations_par_poste.get(poste_nom, [])
        stats_poste = calculer_statistiques_poste(operations_poste)
        
        # Classe CSS pour charge critique
        classe_header = "charge-critique" if stats_poste['charge_critique'] else ""
        
        st.markdown(f"""
        <div class="kanban-operations-column">
            <div class="kanban-operations-header {classe_header}">
                {poste_nom} ({stats_poste['total_operations']})
            </div>
        """, unsafe_allow_html=True)
        
        # Statistiques du poste
        if afficher_stats and operations_poste:
            st.markdown(f"""
            <div class="poste-stats">
                <div class="poste-stats-row">
                    <span>⏱️ Temps total:</span>
                    <span>{stats_poste['temps_total_estime']:.1f}h</span>
                </div>
                <div class="poste-stats-row">
                    <span>📊 En cours:</span>
                    <span>{stats_poste['operations_par_statut'].get('EN COURS', 0)}</span>
                </div>
                <div class="poste-stats-row">
                    <span>✅ Terminé:</span>
                    <span>{stats_poste['operations_par_statut'].get('TERMINÉ', 0)}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # === ZONE DE DÉPÔT POUR DRAG & DROP ===
        if (st.session_state.dragged_operation_id and 
            poste_nom != st.session_state.dragged_from_poste and
            poste_nom != '🚫 Non assigné'):
            
            st.markdown('<div class="drop-zone-operations">', unsafe_allow_html=True)
            if st.button(f"⤵️ Réassigner ici", 
                       key=f"drop_ops_{poste_nom}", 
                       use_container_width=True,
                       help=f"Réassigner l'opération au poste {poste_nom}"):
                
                if gerer_reassignation_operation(erp_db, poste_nom):
                    st.session_state.dragged_operation_id = None
                    st.session_state.dragged_from_poste = None
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # === ZONE DES CARTES OPÉRATIONS ===
        st.markdown('<div class="kanban-operations-cards-zone">', unsafe_allow_html=True)
        
        if not operations_poste:
            st.markdown('<div class="empty-poste-column">🔧 Aucune opération assignée</div>', 
                      unsafe_allow_html=True)
        else:
            # Trier par priorité et statut
            operations_triees = sorted(
                operations_poste,
                key=lambda op: (
                    0 if get_operation_priority_from_context(op, erp_db) in ['CRITIQUE', 'URGENT'] else 1,
                    0 if op.get('statut') == 'EN COURS' else 1 if op.get('statut') == 'À FAIRE' else 2,
                    op.get('sequence_number', 999)
                )
            )
            
            for operation in operations_triees:
                afficher_carte_operation(operation, poste_nom, erp_db)
        
        st.markdown('</div></div>', unsafe_allow_html=True)  # Fin cards-zone et column
    
    st.markdown('</div>', unsafe_allow_html=True)  # Fin kanban-container
    
    # === RÉSUMÉ GLOBAL ===
    if afficher_stats and operations_filtrees:
        st.markdown('<div class="operations-summary">', unsafe_allow_html=True)
        st.markdown("### 📊 Résumé Global des Opérations")
        
        # Statistiques par statut
        statuts_count = {}
        for op in operations_filtrees:
            statut = op.get('statut', 'À FAIRE')
            statuts_count[statut] = statuts_count.get(statut, 0) + 1
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**📈 Répartition par Statut:**")
            for statut, count in statuts_count.items():
                couleur = COULEURS_STATUTS_OPERATIONS.get(statut, '#6b7280')
                st.markdown(f"<span style='color: {couleur}'>●</span> {statut}: {count}", unsafe_allow_html=True)
        
        with col2:
            st.markdown("**🏭 Charge par Poste:**")
            postes_charges = sorted(
                [(poste, calculer_statistiques_poste(ops)['temps_total_estime']) 
                 for poste, ops in operations_par_poste.items() if ops and poste != '🚫 Non assigné'],
                key=lambda x: x[1], reverse=True
            )[:5]
            
            for poste, charge in postes_charges:
                st.markdown(f"🔧 {poste}: {charge:.1f}h")
        
        with col3:
            st.markdown("**⚠️ Alertes:**")
            alertes = []
            
            # Postes surchargés
            for poste, ops in operations_par_poste.items():
                if ops and poste != '🚫 Non assigné':
                    stats = calculer_statistiques_poste(ops)
                    if stats['charge_critique']:
                        alertes.append(f"🔴 {poste}: Charge critique")
            
            # Opérations non assignées
            if operations_par_poste.get('🚫 Non assigné'):
                alertes.append(f"🟡 {len(operations_par_poste['🚫 Non assigné'])} opération(s) non assignée(s)")
            
            if not alertes:
                alertes.append("✅ Aucune alerte")
            
            for alerte in alertes[:5]:
                st.markdown(alerte)
        
        st.markdown('</div>', unsafe_allow_html=True)


# === GESTION DES MODALES ===

def afficher_modal_operation():
    """Affiche la modale de détails d'une opération"""
    if st.session_state.get('show_operation_modal') and st.session_state.get('selected_operation'):
        operation = st.session_state.selected_operation
        
        with st.expander("🔍 Détails de l'Opération", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**ID:** {operation.get('id')}")
                st.markdown(f"**Séquence:** {operation.get('sequence_number')}")
                st.markdown(f"**Description:** {operation.get('description')}")
                st.markdown(f"**Statut:** {operation.get('statut')}")
                st.markdown(f"**Temps estimé:** {format_temps_estime(operation.get('temps_estime'))}")
            
            with col2:
                st.markdown(f"**Poste:** {operation.get('work_center_name') or operation.get('poste_travail')}")
                st.markdown(f"**Projet:** {operation.get('nom_projet')}")
                if operation.get('bt_numero'):
                    st.markdown(f"**Bon de Travail:** {operation.get('bt_numero')}")
                st.markdown(f"**Ressource:** {operation.get('ressource') or 'Non spécifiée'}")
            
            if st.button("❌ Fermer", key="close_operation_modal"):
                st.session_state.show_operation_modal = False
                st.session_state.selected_operation = None
                st.rerun()


# === FONCTION PRINCIPALE UNIFIÉE ===

def show_kanban_sqlite():
    """
    FONCTION PRINCIPALE - Vue Kanban Unifiée (Projets + Opérations)
    Compatible avec l'architecture ERP Production DG Inc.
    """
    
    # Application du CSS
    afficher_css_kanban()
    
    # === SÉLECTEUR DE MODE ===
    st.markdown("## 🔄 Vue Kanban Unifiée - ERP Production DG Inc.")
    st.markdown('<div class="sqlite-indicator">🗄️ Données en temps réel depuis SQLite : erp_production_dg.db</div>', 
                unsafe_allow_html=True)
    
    # Mode selector avec style unifié
    st.markdown('<div class="mode-selector">', unsafe_allow_html=True)
    mode_kanban = st.radio(
        "**Choisissez le mode d'affichage:**",
        ["📋 Projets par Statuts", "🏭 Opérations par Postes de Travail"],
        key="kanban_mode_selector",
        horizontal=True,
        help="Sélectionnez le type de vue Kanban souhaité"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # === AFFICHAGE DE LA VUE SÉLECTIONNÉE ===
    if mode_kanban == "📋 Projets par Statuts":
        st.markdown("### 📋 Vue Projets - Organisés par Statuts")
        show_kanban_projets()
    else:
        st.markdown("### 🏭 Vue Opérations - Organisées par Postes de Travail")
        show_kanban_operations()


# === FONCTIONS D'INTERFACE ===

def show_kanban():
    """Point d'entrée principal pour l'affichage du Kanban"""
    show_kanban_sqlite()


def app():
    """Fonction app() pour compatibilité avec les anciens appels"""
    show_kanban_sqlite()
    
    # Gestion des modales
    if st.session_state.get('show_operation_modal'):
        afficher_modal_operation()


# === POINT D'ENTRÉE POUR TEST AUTONOME ===
if __name__ == "__main__":
    st.title("🔄 Module Kanban Unifié - Test Autonome")
    st.info("Version unifiée pour projets et opérations avec l'architecture SQLite")
    
    # Vérification de l'environnement
    if 'gestionnaire' not in st.session_state or 'erp_db' not in st.session_state:
        st.error("⚠️ Ce module doit être lancé depuis app.py avec l'architecture SQLite initialisée.")
        st.markdown("### 📋 Instructions:")
        st.markdown("1. Lancez `streamlit run app.py`")
        st.markdown("2. Naviguez vers la page Kanban depuis le menu")
        st.stop()
    
    # Test du module
    show_kanban_sqlite()

# --- END OF FILE kanban.py - VERSION UNIFIÉE PROJETS + OPÉRATIONS ---