# kanban_simple.py - Kanban Simple pour Bons de Travail
# Version simplifiée et fonctionnelle

import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration des statuts BT pour le kanban
STATUTS_BT_KANBAN = ["BROUILLON", "VALIDÉ", "EN COURS", "TERMINÉ", "ANNULÉ"]

# Couleurs par statut
COULEURS_STATUTS_BT = {
    'BROUILLON': '#f59e0b',      # Orange
    'VALIDÉ': '#3b82f6',         # Bleu
    'EN COURS': '#10b981',       # Vert
    'TERMINÉ': '#059669',        # Vert foncé
    'ANNULÉ': '#ef4444'          # Rouge
}

# Couleurs par priorité
COULEURS_PRIORITES_BT = {
    'CRITIQUE': '#ef4444',       # Rouge
    'URGENT': '#f59e0b',         # Orange
    'NORMAL': '#10b981'          # Vert
}

# Icônes par priorité
ICONES_PRIORITES_BT = {
    'CRITIQUE': '🔴',
    'URGENT': '🟡',
    'NORMAL': '🟢'
}

def afficher_css_kanban_simple():
    """CSS simple et efficace pour le kanban"""
    st.markdown("""
    <style>
    .kanban-container {
        display: flex;
        gap: 20px;
        padding: 20px;
        background: #f8fafc;
        border-radius: 12px;
        min-height: 600px;
        overflow-x: auto;
    }
    
    .kanban-column {
        flex: 0 0 280px;
        background: white;
        border-radius: 8px;
        padding: 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border: 1px solid #e5e7eb;
    }
    
    .kanban-header {
        padding: 15px;
        font-weight: 600;
        text-align: center;
        color: white;
        border-radius: 8px 8px 0 0;
        font-size: 0.9em;
    }
    
    .kanban-cards {
        padding: 15px;
        max-height: 500px;
        overflow-y: auto;
    }
    
    .kanban-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        transition: all 0.2s ease;
    }
    
    .kanban-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .card-title {
        font-weight: 600;
        font-size: 0.9em;
        margin-bottom: 8px;
        color: #374151;
    }
    
    .card-info {
        font-size: 0.8em;
        color: #6b7280;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .drop-zone {
        background: #f0f9ff;
        border: 2px dashed #3b82f6;
        border-radius: 6px;
        padding: 10px;
        margin-bottom: 10px;
        text-align: center;
        color: #1d4ed8;
        font-weight: 500;
        cursor: pointer;
    }
    
    .drop-zone:hover {
        background: #dbeafe;
    }
    
    .drag-indicator {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: #3b82f6;
        color: white;
        padding: 12px 24px;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        z-index: 1000;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: translateX(-50%) scale(1); }
        50% { transform: translateX(-50%) scale(1.05); }
        100% { transform: translateX(-50%) scale(1); }
    }
    
    .empty-column {
        text-align: center;
        color: #9ca3af;
        font-style: italic;
        margin-top: 40px;
    }
    </style>
    """, unsafe_allow_html=True)

def get_bons_travail_for_kanban(erp_db) -> List[Dict]:
    """Récupère tous les Bons de Travail pour le kanban"""
    try:
        query = '''
            SELECT f.*, 
                   p.nom_projet,
                   c.nom as company_nom,
                   e.prenom || ' ' || e.nom as employee_nom,
                   COUNT(DISTINCT bta.employe_id) as nb_employes_assignes
            FROM formulaires f
            LEFT JOIN projects p ON f.project_id = p.id
            LEFT JOIN companies c ON f.company_id = c.id
            LEFT JOIN employees e ON f.employee_id = e.id
            LEFT JOIN bt_assignations bta ON f.id = bta.bt_id AND bta.statut = 'ASSIGNÉ'
            WHERE f.type_formulaire = 'BON_TRAVAIL'
            GROUP BY f.id
            ORDER BY 
                CASE f.priorite 
                    WHEN 'CRITIQUE' THEN 1
                    WHEN 'URGENT' THEN 2
                    WHEN 'NORMAL' THEN 3
                    ELSE 4
                END,
                f.date_echeance ASC NULLS LAST,
                f.date_creation DESC
        '''
        
        result = erp_db.execute_query(query)
        return [dict(row) for row in result] if result else []
        
    except Exception as e:
        logger.error(f"Erreur récupération BTs pour kanban: {e}")
        return []

def organiser_bts_par_statut(bts: List[Dict]) -> Dict[str, List[Dict]]:
    """Organise les BTs par statut"""
    bts_par_statut = {statut: [] for statut in STATUTS_BT_KANBAN}
    
    for bt in bts:
        statut = bt.get('statut', 'BROUILLON')
        # Mapper certains statuts pour le kanban
        if statut == 'APPROUVÉ':
            statut = 'EN COURS'
        elif statut == 'ENVOYÉ':
            statut = 'VALIDÉ'
            
        if statut in bts_par_statut:
            bts_par_statut[statut].append(bt)
        else:
            bts_par_statut['BROUILLON'].append(bt)
    
    return bts_par_statut

def afficher_carte_bt(bt: Dict, statut: str):
    """Affiche une carte BT dans le kanban"""
    bt_id = bt.get('id')
    numero = bt.get('numero_document', 'N/A')
    projet = bt.get('nom_projet', 'Projet non lié')
    priorite = bt.get('priorite', 'NORMAL')
    echeance = bt.get('date_echeance', 'N/A')
    nb_employes = bt.get('nb_employes_assignes', 0)
    
    # Couleurs
    couleur_priorite = COULEURS_PRIORITES_BT.get(priorite, '#6b7280')
    icone_priorite = ICONES_PRIORITES_BT.get(priorite, '⚪')
    
    # Formatage de la date d'échéance
    echeance_formatee = echeance
    if echeance and echeance != 'N/A':
        try:
            date_obj = datetime.strptime(echeance, '%Y-%m-%d')
            echeance_formatee = date_obj.strftime('%d/%m/%Y')
            
            # Vérifier si en retard
            if date_obj < datetime.now():
                echeance_formatee = f"⚠️ {echeance_formatee}"
        except:
            pass
    
    # Affichage de la carte
    st.markdown(f"""
    <div class='kanban-card' style='border-left: 4px solid {couleur_priorite};'>
        <div class='card-title'>{numero}</div>
        <div class='card-info'>📋 {projet[:30]}{'...' if len(projet) > 30 else ''}</div>
        <div class='card-info'>{icone_priorite} {priorite}</div>
        <div class='card-info'>📅 {echeance_formatee}</div>
        {f"<div class='card-info'>👥 {nb_employes} assigné(s)</div>" if nb_employes > 0 else ""}
    </div>
    """, unsafe_allow_html=True)
    
    # Boutons d'action
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("👁️ Voir", key=f"view_bt_{bt_id}_{statut}", help="Voir les détails", use_container_width=True):
            st.session_state.selected_bt_id = bt_id
            st.session_state.show_bt_details = True
            st.rerun()
    
    with col2:
        if st.button("➡️ Déplacer", key=f"move_bt_{bt_id}_{statut}", help="Déplacer ce BT", use_container_width=True):
            st.session_state.dragged_bt_id = bt_id
            st.session_state.dragged_from_status = statut
            st.rerun()

def deplacer_bt_vers_statut(erp_db, bt_id: int, nouveau_statut: str) -> bool:
    """Déplace un BT vers un nouveau statut"""
    try:
        # Récupérer l'ancien statut
        result = erp_db.execute_query(
            "SELECT statut FROM formulaires WHERE id = ?", 
            (bt_id,)
        )
        
        if not result:
            st.error(f"BT #{bt_id} non trouvé")
            return False
        
        ancien_statut = result[0]['statut']
        
        # Mettre à jour le statut
        affected = erp_db.execute_update(
            "UPDATE formulaires SET statut = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (nouveau_statut, bt_id)
        )
        
        if affected > 0:
            # Enregistrer dans l'historique
            erp_db.execute_insert(
                """INSERT INTO formulaire_validations 
                   (formulaire_id, type_validation, ancien_statut, nouveau_statut, commentaires)
                   VALUES (?, 'CHANGEMENT_STATUT', ?, ?, ?)""",
                (bt_id, ancien_statut, nouveau_statut, f"Déplacé via Kanban: {ancien_statut} → {nouveau_statut}")
            )
            
            logger.info(f"✅ BT #{bt_id} déplacé: {ancien_statut} → {nouveau_statut}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Erreur déplacement BT: {e}")
        st.error(f"❌ Erreur lors du déplacement: {e}")
        return False

def creer_bts_de_test(erp_db) -> bool:
    """Crée quelques BTs de test pour démonstration"""
    try:
        # Vérifier s'il y a un projet existant
        projects = erp_db.execute_query("SELECT id FROM projects LIMIT 1")
        if projects:
            project_id = projects[0]['id']
        else:
            # Créer un projet de test
            project_id = erp_db.execute_insert(
                "INSERT INTO projects (nom_projet, statut, priorite) VALUES (?, ?, ?)",
                ("Projet Test Kanban", "EN COURS", "NORMAL")
            )
        
        # Créer des BTs de test avec différents statuts
        bts_test = [
            {
                'numero': 'BT-TEST-001',
                'statut': 'BROUILLON',
                'priorite': 'URGENT',
                'notes': 'Fabrication châssis principal'
            },
            {
                'numero': 'BT-TEST-002', 
                'statut': 'VALIDÉ',
                'priorite': 'NORMAL',
                'notes': 'Usinage pièces précision'
            },
            {
                'numero': 'BT-TEST-003',
                'statut': 'EN COURS', 
                'priorite': 'CRITIQUE',
                'notes': 'Assemblage final'
            },
            {
                'numero': 'BT-TEST-004',
                'statut': 'TERMINÉ',
                'priorite': 'NORMAL', 
                'notes': 'Contrôle qualité'
            }
        ]
        
        created_count = 0
        for bt_data in bts_test:
            # Vérifier si le BT existe déjà
            existing = erp_db.execute_query(
                "SELECT id FROM formulaires WHERE numero_document = ?",
                (bt_data['numero'],)
            )
            
            if not existing:
                bt_id = erp_db.execute_insert(
                    """INSERT INTO formulaires 
                       (type_formulaire, numero_document, project_id, statut, priorite, 
                        date_echeance, notes)
                       VALUES ('BON_TRAVAIL', ?, ?, ?, ?, DATE('now', '+7 days'), ?)""",
                    (bt_data['numero'], project_id, bt_data['statut'], 
                     bt_data['priorite'], bt_data['notes'])
                )
                
                if bt_id:
                    created_count += 1
        
        if created_count > 0:
            st.success(f"✅ {created_count} Bons de Travail de test créés !")
            return True
        else:
            st.info("ℹ️ Des BTs de test existent déjà.")
            return True
            
    except Exception as e:
        logger.error(f"Erreur création BTs test: {e}")
        st.error(f"❌ Erreur création BTs test: {e}")
        return False

def afficher_statistiques_kanban(bts_par_statut: Dict):
    """Affiche des statistiques simples du kanban"""
    total_bts = sum(len(bts) for bts in bts_par_statut.values())
    
    if total_bts == 0:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Total BTs", total_bts)
    
    with col2:
        en_cours = len(bts_par_statut['EN COURS'])
        st.metric("🔄 En Cours", en_cours)
    
    with col3:
        termines = len(bts_par_statut['TERMINÉ'])
        pourcentage = round((termines / total_bts) * 100, 1) if total_bts > 0 else 0
        st.metric("✅ Terminés", f"{termines} ({pourcentage}%)")
    
    with col4:
        critiques = sum(1 for bts in bts_par_statut.values() 
                       for bt in bts if bt.get('priorite') == 'CRITIQUE')
        st.metric("🔴 Critiques", critiques)

def afficher_details_bt_modal():
    """Affiche les détails d'un BT dans une modale"""
    if not st.session_state.get('show_bt_details') or not st.session_state.get('selected_bt_id'):
        return
    
    erp_db = st.session_state.erp_db
    bt_id = st.session_state.selected_bt_id
    
    try:
        # Récupérer les détails du BT
        query = '''
            SELECT f.*, 
                   p.nom_projet,
                   c.nom as company_nom,
                   e.prenom || ' ' || e.nom as employee_nom
            FROM formulaires f
            LEFT JOIN projects p ON f.project_id = p.id
            LEFT JOIN companies c ON f.company_id = c.id
            LEFT JOIN employees e ON f.employee_id = e.id
            WHERE f.id = ?
        '''
        
        result = erp_db.execute_query(query, (bt_id,))
        if not result:
            st.error("BT non trouvé")
            return
        
        bt = dict(result[0])
        
        with st.expander(f"🔍 Détails du BT {bt.get('numero_document', '')}", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**ID:** {bt.get('id')}")
                st.write(f"**Numéro:** {bt.get('numero_document', 'N/A')}")
                st.write(f"**Statut:** {bt.get('statut', 'N/A')}")
                st.write(f"**Priorité:** {bt.get('priorite', 'N/A')}")
                st.write(f"**Date création:** {bt.get('date_creation', 'N/A')}")
            
            with col2:
                st.write(f"**Projet:** {bt.get('nom_projet', 'Non lié')}")
                st.write(f"**Client:** {bt.get('company_nom', 'Non spécifié')}")
                st.write(f"**Responsable:** {bt.get('employee_nom', 'Non assigné')}")
                st.write(f"**Échéance:** {bt.get('date_echeance', 'Non définie')}")
            
            if bt.get('notes'):
                st.write("**Notes:**")
                st.write(bt['notes'])
            
            if st.button("❌ Fermer", key="close_bt_modal"):
                st.session_state.show_bt_details = False
                st.session_state.selected_bt_id = None
                st.rerun()
                
    except Exception as e:
        st.error(f"Erreur affichage détails BT: {e}")

def show_kanban_bons_travail():
    """Fonction principale pour afficher le kanban des Bons de Travail"""
    
    # CSS
    afficher_css_kanban_simple()
    
    # Vérification de la base de données
    if 'erp_db' not in st.session_state:
        st.error("⚠️ Base de données ERP non initialisée.")
        return
    
    erp_db = st.session_state.erp_db
    
    # Titre
    st.markdown("## 🏭 Kanban - Bons de Travail")
    st.markdown("Visualisez et gérez vos Bons de Travail par statut")
    
    # Initialisation des variables de session
    if 'dragged_bt_id' not in st.session_state:
        st.session_state.dragged_bt_id = None
    if 'dragged_from_status' not in st.session_state:
        st.session_state.dragged_from_status = None
    
    # Récupération des BTs
    bts = get_bons_travail_for_kanban(erp_db)
    
    # Si aucun BT, proposer d'en créer
    if not bts:
        st.warning("⚠️ Aucun Bon de Travail trouvé.")
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("💡 Créez des Bons de Travail de test pour voir le kanban en action.")
        
        with col2:
            if st.button("🔧 Créer des BTs de test", use_container_width=True):
                if creer_bts_de_test(erp_db):
                    st.rerun()
        return
    
    # Organiser les BTs par statut
    bts_par_statut = organiser_bts_par_statut(bts)
    
    # Affichage de l'indicateur de drag & drop
    if st.session_state.dragged_bt_id:
        bt_numero = next((bt['numero_document'] for statut_bts in bts_par_statut.values() 
                         for bt in statut_bts if bt['id'] == st.session_state.dragged_bt_id), 'N/A')
        
        st.markdown(f"""
        <div class='drag-indicator'>
            🔄 Déplacement en cours: <strong>{bt_numero}</strong>
        </div>
        """, unsafe_allow_html=True)
        
        # Bouton d'annulation dans la sidebar
        if st.sidebar.button("❌ Annuler déplacement", use_container_width=True):
            st.session_state.dragged_bt_id = None
            st.session_state.dragged_from_status = None
            st.rerun()
    
    # Affichage du kanban
    st.markdown('<div class="kanban-container">', unsafe_allow_html=True)
    
    colonnes = st.columns(len(STATUTS_BT_KANBAN))
    
    for idx, statut in enumerate(STATUTS_BT_KANBAN):
        with colonnes[idx]:
            nb_bts = len(bts_par_statut[statut])
            couleur_statut = COULEURS_STATUTS_BT.get(statut, '#6b7280')
            
            # En-tête de colonne
            st.markdown(f"""
            <div class="kanban-column">
                <div class="kanban-header" style="background: {couleur_statut};">
                    {statut} ({nb_bts})
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="kanban-cards">', unsafe_allow_html=True)
            
            # Zone de dépôt pour drag & drop
            if (st.session_state.dragged_bt_id and 
                statut != st.session_state.dragged_from_status):
                
                st.markdown('<div class="drop-zone">', unsafe_allow_html=True)
                if st.button(f"⬇️ Déposer ici", key=f"drop_{statut}", use_container_width=True):
                    if deplacer_bt_vers_statut(erp_db, st.session_state.dragged_bt_id, statut):
                        st.success(f"✅ BT déplacé vers {statut}")
                        st.session_state.dragged_bt_id = None
                        st.session_state.dragged_from_status = None
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Affichage des BTs
            if not bts_par_statut[statut]:
                st.markdown('<div class="empty-column">Aucun BT</div>', unsafe_allow_html=True)
            else:
                for bt in bts_par_statut[statut]:
                    afficher_carte_bt(bt, statut)
            
            st.markdown('</div></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Statistiques
    st.markdown("---")
    afficher_statistiques_kanban(bts_par_statut)
    
    # Modale des détails
    afficher_details_bt_modal()
    
    # Actions rapides
    with st.expander("⚡ Actions rapides", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔧 Créer BTs de test", help="Ajouter des BTs de démonstration"):
                creer_bts_de_test(erp_db)
                st.rerun()
        
        with col2:
            if st.button("🔄 Actualiser", help="Recharger les données"):
                st.rerun()
        
        with col3:
            total_bts = sum(len(bts) for bts in bts_par_statut.values())
            st.metric("📊 Total BTs", total_bts)

# Point d'entrée principal
def app():
    """Point d'entrée pour l'application"""
    show_kanban_bons_travail()

if __name__ == "__main__":
    st.title("🏭 Kanban Simple - Bons de Travail")
    st.info("Module Kanban simplifié pour la gestion des Bons de Travail")
    
    if 'erp_db' not in st.session_state:
        st.error("⚠️ Ce module doit être lancé depuis app.py avec erp_database initialisé.")
        st.stop()
    
    show_kanban_bons_travail()
