# kanban.py - Vue Kanban Complète pour Projets
# Programme complet pour remplacer le module manquant
# Compatible avec erp_database.py et app.py

import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import json

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================================
# CONFIGURATION DES STATUTS ET COULEURS
# =========================================================================

# Statuts des projets pour le kanban (selon votre interface)
STATUTS_PROJETS_KANBAN = ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON"]

# Couleurs par statut (identiques à votre interface)
COULEURS_STATUTS_PROJETS = {
    'À FAIRE': '#f59e0b',        # Orange
    'EN COURS': '#3b82f6',       # Bleu  
    'EN ATTENTE': '#ef4444',     # Rouge
    'TERMINÉ': '#10b981',        # Vert
    'LIVRAISON': '#8b5cf6',      # Violet
    'ANNULÉ': '#6b7280'          # Gris (fallback)
}

# Couleurs par priorité
COULEURS_PRIORITES_PROJETS = {
    'ÉLEVÉ': '#ef4444',          # Rouge
    'MOYEN': '#f59e0b',          # Orange
    'BAS': '#10b981',            # Vert
    'NORMAL': '#10b981'          # Vert (alias)
}

# Icônes par priorité
ICONES_PRIORITES_PROJETS = {
    'ÉLEVÉ': '🔴',
    'MOYEN': '🟡',
    'BAS': '🟢',
    'NORMAL': '🟢'
}

# =========================================================================
# CSS COMPLET POUR LE KANBAN
# =========================================================================

def afficher_css_kanban_complet():
    """CSS complet et moderne pour le kanban projets"""
    st.markdown("""
    <style>
    /* === KANBAN PROJETS - CSS COMPLET === */
    :root {
        --primary-color: #00A971; 
        --primary-color-darker: #00673D;
        --background-color: #F9FAFB;
        --card-background: #FFFFFF;
        --text-color: #374151;
        --text-color-light: #6B7280;
        --text-color-muted: #9CA3AF;
        --border-color: #E5E7EB;
        --border-color-light: #F3F4F6;
        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    
    .kanban-container {
        display: flex;
        flex-direction: row;
        gap: 20px;
        padding: 20px;
        background: linear-gradient(135deg, var(--card-background), var(--background-color));
        border-radius: 15px;
        overflow-x: auto;
        overflow-y: hidden;
        min-height: 700px;
        margin-bottom: 25px;
        box-shadow: var(--shadow-lg);
        border: 1px solid var(--border-color-light);
    }
    
    .kanban-column {
        flex: 0 0 300px;
        width: 300px;
        background: var(--background-color);
        border-radius: 12px;
        padding: 0;
        display: flex;
        flex-direction: column;
        box-shadow: var(--shadow-md);
        border: 1px solid var(--border-color-light);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .kanban-column:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg);
    }
    
    .kanban-header {
        font-weight: 700;
        text-align: center;
        padding: 16px 20px;
        margin: 0;
        color: white;
        border-radius: 12px 12px 0 0;
        position: sticky;
        top: 0;
        z-index: 10;
        font-size: 1.0em;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .kanban-cards-zone { 
        flex-grow: 1; 
        overflow-y: auto; 
        padding: 16px; 
        max-height: 600px;
        background: var(--card-background);
        border-radius: 0 0 12px 12px;
    }
    
    .kanban-cards-zone::-webkit-scrollbar { 
        width: 6px; 
    }
    
    .kanban-cards-zone::-webkit-scrollbar-track { 
        background: var(--background-color); 
        border-radius: 3px; 
    }
    
    .kanban-cards-zone::-webkit-scrollbar-thumb { 
        background: var(--primary-color); 
        border-radius: 3px; 
    }
    
    .kanban-cards-zone::-webkit-scrollbar-thumb:hover { 
        background: var(--primary-color-darker); 
    }
    
    .kanban-card { 
        background: var(--card-background); 
        border-radius: 12px; 
        padding: 16px; 
        margin-bottom: 16px; 
        box-shadow: var(--shadow-sm); 
        transition: all 0.3s ease; 
        color: var(--text-color); 
        position: relative; 
        overflow: hidden;
        border: 1px solid var(--border-color);
        border-left: 4px solid var(--border-color);
    }
    
    .kanban-card:hover { 
        transform: translateY(-3px); 
        box-shadow: var(--shadow-lg);
        border-color: var(--primary-color);
    }
    
    .kanban-card-title { 
        font-weight: 600; 
        font-size: 0.95em; 
        margin-bottom: 10px; 
        color: var(--primary-color-darker); 
        line-height: 1.4;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .kanban-card-info { 
        font-size: 0.85em; 
        color: var(--text-color-muted); 
        margin-bottom: 6px; 
        display: flex; 
        align-items: center; 
        gap: 8px;
        line-height: 1.3;
    }
    
    .kanban-card-info strong {
        color: var(--text-color);
        font-weight: 500;
    }
    
    .priority-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    .currency-amount {
        font-weight: 600;
        color: var(--primary-color-darker);
    }
    
    .date-info {
        font-size: 0.8em;
    }
    
    .date-overdue {
        color: #ef4444;
        font-weight: 600;
    }
    
    .drop-zone {
        background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
        border: 2px dashed var(--primary-color);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 16px;
        text-align: center;
        color: var(--primary-color-darker);
        font-weight: 600;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .drop-zone:hover {
        background: linear-gradient(135deg, #e0f2fe, #b3e5fc);
        transform: scale(1.02);
        box-shadow: var(--shadow-md);
    }
    
    .drag-indicator {
        position: fixed;
        bottom: 30px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, var(--primary-color), var(--primary-color-darker));
        color: white;
        padding: 16px 28px;
        border-radius: 25px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.3);
        z-index: 1000;
        animation: pulse 2s infinite;
        font-weight: 600;
        font-size: 0.9em;
        backdrop-filter: blur(10px);
    }
    
    @keyframes pulse {
        0% { transform: translateX(-50%) scale(1); }
        50% { transform: translateX(-50%) scale(1.05); }
        100% { transform: translateX(-50%) scale(1); }
    }
    
    .empty-column {
        text-align: center;
        color: var(--text-color-muted);
        margin-top: 60px;
        font-style: italic;
        opacity: 0.7;
        padding: 20px;
    }
    
    .empty-column::before {
        content: "📋";
        display: block;
        font-size: 2em;
        margin-bottom: 10px;
        opacity: 0.5;
    }
    
    .kanban-stats {
        background: var(--card-background);
        border-radius: 12px;
        padding: 20px;
        margin-top: 25px;
        box-shadow: var(--shadow-md);
        border: 1px solid var(--border-color-light);
    }
    
    .kanban-stats h3 {
        color: var(--primary-color-darker);
        margin-bottom: 15px;
        font-size: 1.1em;
    }
    
    .search-container {
        background: var(--card-background);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border-color-light);
    }
    
    .action-buttons {
        display: flex;
        gap: 8px;
        margin-top: 12px;
    }
    
    .action-button {
        flex: 1;
        padding: 6px 12px;
        border: none;
        border-radius: 6px;
        font-size: 0.8em;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .action-button:hover {
        transform: translateY(-1px);
        box-shadow: var(--shadow-sm);
    }
    
    .btn-view {
        background: var(--primary-color);
        color: white;
    }
    
    .btn-view:hover {
        background: var(--primary-color-darker);
    }
    
    .btn-move {
        background: #f59e0b;
        color: white;
    }
    
    .btn-move:hover {
        background: #d97706;
    }
    
    /* Responsive pour mobile */
    @media (max-width: 768px) {
        .kanban-container {
            flex-direction: column;
            padding: 10px;
        }
        
        .kanban-column {
            flex: none;
            width: 100%;
            margin-bottom: 20px;
        }
        
        .drag-indicator {
            bottom: 10px;
            padding: 12px 20px;
            font-size: 0.8em;
        }
    }
    
    /* Animations d'entrée */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .kanban-card {
        animation: fadeInUp 0.3s ease-out;
    }
    
    /* États de charge */
    .loading-indicator {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 40px;
        color: var(--text-color-muted);
    }
    
    .loading-indicator::before {
        content: "⏳";
        margin-right: 10px;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    </style>
    """, unsafe_allow_html=True)

# =========================================================================
# FONCTIONS UTILITAIRES ET HELPERS
# =========================================================================

def format_currency(value) -> str:
    """Formate une valeur monétaire avec gestion d'erreurs robuste"""
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

def format_date(date_str: str) -> str:
    """Formate une date avec détection de retard"""
    if not date_str or date_str == 'N/A':
        return 'Non définie'
    
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        date_formatee = date_obj.strftime('%d/%m/%Y')
        
        # Vérifier si en retard
        if date_obj < datetime.now():
            return f"⚠️ {date_formatee}"
        elif date_obj < datetime.now() + timedelta(days=7):
            return f"⏰ {date_formatee}"
        else:
            return date_formatee
    except:
        return date_str

def get_client_display_name(projet: Dict) -> str:
    """Récupère le nom d'affichage du client avec fallbacks intelligents"""
    if projet.get('client_company_nom'):
        return projet['client_company_nom']
    elif projet.get('client_nom_cache'):
        return projet['client_nom_cache']
    elif projet.get('client_legacy'):
        return projet['client_legacy']
    else:
        return "Client non spécifié"

def get_priority_class(priorite: str) -> str:
    """Retourne la classe CSS pour une priorité"""
    return f"priority-{priorite.lower()}"

def safe_get(dict_obj: Dict, key: str, default: Any = None) -> Any:
    """Récupération sécurisée d'une valeur dans un dictionnaire"""
    try:
        return dict_obj.get(key, default)
    except (AttributeError, TypeError):
        return default

# =========================================================================
# FONCTIONS DE RÉCUPÉRATION DE DONNÉES
# =========================================================================

def get_projets_for_kanban(erp_db) -> List[Dict]:
    """Récupère tous les projets pour le kanban avec jointures complètes"""
    try:
        query = '''
            SELECT p.*, 
                   c.nom as client_company_nom,
                   c.secteur as client_secteur,
                   c.type_company as client_type,
                   COUNT(DISTINCT o.id) as nb_operations,
                   COUNT(DISTINCT m.id) as nb_materiaux,
                   COALESCE(SUM(m.quantite * m.prix_unitaire), 0) as cout_materiaux_estime,
                   COUNT(DISTINCT pa.employee_id) as nb_employes_assignes
            FROM projects p
            LEFT JOIN companies c ON p.client_company_id = c.id
            LEFT JOIN operations o ON p.id = o.project_id
            LEFT JOIN materials m ON p.id = m.project_id
            LEFT JOIN project_assignments pa ON p.id = pa.project_id
            GROUP BY p.id
            ORDER BY 
                CASE p.priorite 
                    WHEN 'ÉLEVÉ' THEN 1
                    WHEN 'MOYEN' THEN 2
                    WHEN 'BAS' THEN 3
                    WHEN 'NORMAL' THEN 3
                    ELSE 4
                END,
                p.date_prevu ASC NULLS LAST,
                p.id DESC
        '''
        
        result = erp_db.execute_query(query)
        projets = [dict(row) for row in result] if result else []
        
        logger.info(f"Récupération kanban: {len(projets)} projets trouvés")
        return projets
        
    except Exception as e:
        logger.error(f"Erreur récupération projets pour kanban: {e}")
        st.error(f"❌ Erreur de récupération des données: {e}")
        return []

def organiser_projets_par_statut(projets: List[Dict]) -> Dict[str, List[Dict]]:
    """Organise les projets par statut avec mapping intelligent"""
    projets_par_statut = {statut: [] for statut in STATUTS_PROJETS_KANBAN}
    
    for projet in projets:
        statut = safe_get(projet, 'statut', 'À FAIRE')
        
        # Mapping des statuts alternatifs
        if statut == 'ANNULÉ':
            statut = 'EN ATTENTE'  # ou créer une colonne séparée
        elif statut == 'SUSPENDED':
            statut = 'EN ATTENTE'
        elif statut == 'COMPLETED':
            statut = 'TERMINÉ'
        elif statut == 'SHIPPED':
            statut = 'LIVRAISON'
            
        if statut in projets_par_statut:
            projets_par_statut[statut].append(projet)
        else:
            # Fallback vers À FAIRE
            projets_par_statut['À FAIRE'].append(projet)
    
    return projets_par_statut

def filtrer_projets_kanban(projets: List[Dict], recherche: str) -> List[Dict]:
    """Filtre les projets selon le terme de recherche"""
    if not recherche:
        return projets
    
    terme = recherche.lower().strip()
    if not terme:
        return projets
    
    projets_filtres = []
    for projet in projets:
        # Recherche dans plusieurs champs
        champs_recherche = [
            safe_get(projet, 'nom_projet', ''),
            safe_get(projet, 'description', ''),
            get_client_display_name(projet),
            str(safe_get(projet, 'id', '')),
            safe_get(projet, 'client_secteur', '')
        ]
        
        if any(terme in str(champ).lower() for champ in champs_recherche):
            projets_filtres.append(projet)
    
    return projets_filtres

# =========================================================================
# FONCTIONS D'AFFICHAGE DES CARTES
# =========================================================================

def afficher_carte_projet(projet: Dict, statut: str):
    """Affiche une carte projet optimisée dans le kanban"""
    project_id = safe_get(projet, 'id')
    nom_projet = safe_get(projet, 'nom_projet', 'Projet sans nom')
    client_nom = get_client_display_name(projet)
    priorite = safe_get(projet, 'priorite', 'MOYEN')
    prix_estime = safe_get(projet, 'prix_estime', 0)
    date_prevu = safe_get(projet, 'date_prevu')
    nb_operations = safe_get(projet, 'nb_operations', 0)
    nb_materiaux = safe_get(projet, 'nb_materiaux', 0)
    
    # Couleurs et icônes
    couleur_priorite = COULEURS_PRIORITES_PROJETS.get(priorite, '#6b7280')
    icone_priorite = ICONES_PRIORITES_PROJETS.get(priorite, '⚪')
    
    # Formatage des données
    prix_formate = format_currency(prix_estime)
    date_formatee = format_date(date_prevu)
    
    # Titre tronqué intelligent
    nom_affiche = nom_projet[:28] + '...' if len(nom_projet) > 28 else nom_projet
    client_affiche = client_nom[:25] + '...' if len(client_nom) > 25 else client_nom
    
    # Affichage de la carte avec structure améliorée
    st.markdown(f"""
    <div class='kanban-card' style='border-left-color: {couleur_priorite};'>
        <div class='kanban-card-title'>
            <span>#{project_id}</span>
            <span>{nom_affiche}</span>
        </div>
        
        <div class='kanban-card-info'>
            <span>👤</span>
            <strong>Client:</strong> {client_affiche}
        </div>
        
        <div class='kanban-card-info'>
            <span>{icone_priorite}</span>
            <strong>Priorité:</strong> 
            <span class='priority-badge' style='background-color: {couleur_priorite}20; color: {couleur_priorite};'>
                {priorite}
            </span>
        </div>
        
        <div class='kanban-card-info'>
            <span>💰</span>
            <strong>Prix:</strong> 
            <span class='currency-amount'>{prix_formate}</span>
        </div>
        
        <div class='kanban-card-info date-info'>
            <span>📅</span>
            <strong>Échéance:</strong> {date_formatee}
        </div>
        
        {f'''<div class='kanban-card-info'>
            <span>⚙️</span>
            <strong>Opérations:</strong> {nb_operations} | 
            <strong>Matériaux:</strong> {nb_materiaux}
        </div>''' if nb_operations > 0 or nb_materiaux > 0 else ''}
    </div>
    """, unsafe_allow_html=True)
    
    # Boutons d'action avec style amélioré
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("👁️ Voir", 
                    key=f"view_proj_{project_id}_{statut}", 
                    help="Voir les détails du projet", 
                    use_container_width=True):
            st.session_state.selected_project_id = project_id
            st.session_state.show_project_details = True
            st.rerun()
    
    with col2:
        if st.button("➡️ Déplacer", 
                    key=f"move_proj_{project_id}_{statut}", 
                    help="Déplacer ce projet vers un autre statut", 
                    use_container_width=True):
            st.session_state.dragged_project_id = project_id
            st.session_state.dragged_from_status = statut
            st.rerun()

# =========================================================================
# FONCTIONS DE GESTION DES DÉPLACEMENTS
# =========================================================================

def deplacer_projet_vers_statut(erp_db, project_id: int, nouveau_statut: str) -> bool:
    """Déplace un projet vers un nouveau statut avec traçabilité complète"""
    try:
        # Récupérer l'ancien statut et les infos du projet
        result = erp_db.execute_query(
            "SELECT statut, nom_projet FROM projects WHERE id = ?", 
            (project_id,)
        )
        
        if not result:
            st.error(f"❌ Projet #{project_id} non trouvé")
            return False
        
        ancien_statut = result[0]['statut']
        nom_projet = result[0]['nom_projet']
        
        if ancien_statut == nouveau_statut:
            st.info(f"ℹ️ Projet déjà dans le statut '{nouveau_statut}'")
            return True
        
        # Mettre à jour le statut avec timestamp
        affected = erp_db.execute_update(
            "UPDATE projects SET statut = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (nouveau_statut, project_id)
        )
        
        if affected > 0:
            # Enregistrer dans un log si la table existe
            try:
                erp_db.execute_insert(
                    """INSERT INTO project_status_log 
                       (project_id, ancien_statut, nouveau_statut, changed_at, changed_via)
                       VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'KANBAN')""",
                    (project_id, ancien_statut, nouveau_statut)
                )
            except:
                # Table de log n'existe pas, continuer sans erreur
                pass
            
            logger.info(f"✅ Projet #{project_id} déplacé: {ancien_statut} → {nouveau_statut}")
            return True
        else:
            st.error("❌ Erreur lors de la mise à jour du statut")
            return False
        
    except Exception as e:
        logger.error(f"Erreur déplacement projet {project_id}: {e}")
        st.error(f"❌ Erreur lors du déplacement: {e}")
        return False

# =========================================================================
# FONCTIONS DE CRÉATION DE DONNÉES DE TEST
# =========================================================================

def creer_projets_de_test(erp_db) -> bool:
    """Crée des projets de test réalistes pour démonstration"""
    try:
        # Vérifier/créer des entreprises de test
        companies_test = [
            ("EMB Laser Inc.", "USINAGE", "CLIENT"),
            ("Doucet Machineries", "MÉCANIQUE", "CLIENT"), 
            ("AeroTech Solutions", "AÉRONAUTIQUE", "CLIENT"),
            ("ProMetal Industries", "MÉTALLURGIE", "CLIENT")
        ]
        
        company_ids = []
        for nom, secteur, type_comp in companies_test:
            existing = erp_db.execute_query(
                "SELECT id FROM companies WHERE nom = ?", (nom,)
            )
            
            if existing:
                company_ids.append(existing[0]['id'])
            else:
                company_id = erp_db.execute_insert(
                    "INSERT INTO companies (nom, secteur, type_company) VALUES (?, ?, ?)",
                    (nom, secteur, type_comp)
                )
                if company_id:
                    company_ids.append(company_id)
        
        # Projets de test réalistes
        projets_test = [
            {
                'nom': 'Fabrication Châssis Principal',
                'statut': 'À FAIRE',
                'priorite': 'ÉLEVÉ',
                'prix': 25000.00,
                'description': 'Châssis métallique pour équipement industriel',
                'bd_ft': 120.5
            },
            {
                'nom': 'Attache de Serre 10" (Lot de 50)', 
                'statut': 'EN COURS',
                'priorite': 'MOYEN',
                'prix': 12500.00,
                'description': 'Production série d\'attaches pour serres agricoles',
                'bd_ft': 85.0
            },
            {
                'nom': 'Support Moteur Aéronautique',
                'statut': 'EN ATTENTE',
                'priorite': 'ÉLEVÉ',
                'prix': 45000.00,
                'description': 'Support moteur certifié pour aviation civile',
                'bd_ft': 200.0
            },
            {
                'nom': 'Pièces de Rechange Convoyeur',
                'statut': 'TERMINÉ', 
                'priorite': 'BAS',
                'prix': 8000.00,
                'description': 'Lot de pièces de rechange pour maintenance',
                'bd_ft': 45.0
            },
            {
                'nom': 'Prototype Nouvelle Gamme',
                'statut': 'LIVRAISON',
                'priorite': 'MOYEN',
                'prix': 15000.00,
                'description': 'Prototype pour validation client',
                'bd_ft': 75.5
            }
        ]
        
        created_count = 0
        for i, projet_data in enumerate(projets_test):
            # Vérifier si le projet existe déjà
            existing = erp_db.execute_query(
                "SELECT id FROM projects WHERE nom_projet = ?",
                (projet_data['nom'],)
            )
            
            if not existing:
                # Utiliser une entreprise cliente
                company_id = company_ids[i % len(company_ids)] if company_ids else None
                
                project_id = erp_db.execute_insert(
                    """INSERT INTO projects 
                       (nom_projet, client_company_id, statut, priorite, prix_estime, 
                        bd_ft_estime, description, date_prevu, date_soumis)
                       VALUES (?, ?, ?, ?, ?, ?, ?, DATE('now', '+' || ? || ' days'), DATE('now'))""",
                    (projet_data['nom'], company_id, projet_data['statut'], 
                     projet_data['priorite'], projet_data['prix'], projet_data['bd_ft'],
                     projet_data['description'], (i + 1) * 15)  # Échelonnement des dates
                )
                
                if project_id:
                    created_count += 1
                    logger.info(f"Projet test créé: {projet_data['nom']} (ID: {project_id})")
        
        if created_count > 0:
            st.success(f"✅ {created_count} projets de test créés avec succès !")
            return True
        else:
            st.info("ℹ️ Des projets de test existent déjà dans le système.")
            return True
            
    except Exception as e:
        logger.error(f"Erreur création projets test: {e}")
        st.error(f"❌ Erreur lors de la création des projets de test: {e}")
        return False

# =========================================================================
# FONCTIONS DE STATISTIQUES
# =========================================================================

def calculer_statistiques_kanban(projets_par_statut: Dict) -> Dict[str, Any]:
    """Calcule des statistiques complètes pour le kanban"""
    try:
        total_projets = sum(len(projets) for projets in projets_par_statut.values())
        
        if total_projets == 0:
            return {
                'total': 0, 'actifs': 0, 'ca_total': 0.0, 'ca_moyen': 0.0,
                'duree_moyenne': 0, 'projet_plus_cher': None, 'repartition': {}
            }
        
        # Calculs détaillés
        ca_total = 0.0
        durees = []
        prix_max = 0.0
        projet_plus_cher = None
        actifs = 0
        repartition = {}
        
        for statut, projets in projets_par_statut.items():
            repartition[statut] = len(projets)
            
            if statut not in ['TERMINÉ', 'ANNULÉ']:
                actifs += len(projets)
            
            for projet in projets:
                # CA total
                try:
                    prix = float(safe_get(projet, 'prix_estime', 0) or 0)
                    ca_total += prix
                    
                    if prix > prix_max:
                        prix_max = prix
                        projet_plus_cher = safe_get(projet, 'nom_projet', 'N/A')
                except (ValueError, TypeError):
                    pass
                
                # Durées de projet
                try:
                    date_soumis = safe_get(projet, 'date_soumis')
                    date_prevu = safe_get(projet, 'date_prevu')
                    
                    if date_soumis and date_prevu:
                        debut = datetime.strptime(date_soumis, '%Y-%m-%d')
                        fin = datetime.strptime(date_prevu, '%Y-%m-%d')
                        duree = (fin - debut).days
                        if duree > 0:
                            durees.append(duree)
                except:
                    pass
        
        # Calculs finaux
        ca_moyen = ca_total / total_projets if total_projets > 0 else 0.0
        duree_moyenne = sum(durees) / len(durees) if durees else 0
        
        return {
            'total': total_projets,
            'actifs': actifs,
            'ca_total': ca_total,
            'ca_moyen': ca_moyen,
            'duree_moyenne': duree_moyenne,
            'projet_plus_cher': projet_plus_cher,
            'repartition': repartition
        }
        
    except Exception as e:
        logger.error(f"Erreur calcul statistiques: {e}")
        return {}

def afficher_statistiques_kanban(projets_par_statut: Dict):
    """Affiche des statistiques complètes et visuelles"""
    stats = calculer_statistiques_kanban(projets_par_statut)
    
    if not stats or stats['total'] == 0:
        return
    
    st.markdown('<div class="kanban-stats">', unsafe_allow_html=True)
    st.markdown("### 📊 Tableau de Bord - Projets")
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Total Projets", stats['total'])
    
    with col2:
        st.metric("🔄 Projets Actifs", stats['actifs'])
    
    with col3:
        pourcentage_termine = round((stats['repartition'].get('TERMINÉ', 0) / stats['total']) * 100, 1) if stats['total'] > 0 else 0
        st.metric("✅ Taux Completion", f"{pourcentage_termine}%")
    
    with col4:
        st.metric("💰 CA Total", format_currency(stats['ca_total']))
    
    # Métriques secondaires
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric("💵 CA Moyen", format_currency(stats['ca_moyen']))
    
    with col6:
        st.metric("📅 Durée Moyenne", f"{stats['duree_moyenne']:.0f} jours")
    
    with col7:
        en_retard = stats['repartition'].get('EN ATTENTE', 0)
        st.metric("⚠️ En Attente", en_retard)
    
    with col8:
        livraisons = stats['repartition'].get('LIVRAISON', 0)
        st.metric("🚚 Livraisons", livraisons)
    
    # Projet le plus important
    if stats['projet_plus_cher']:
        st.info(f"💎 **Projet le plus important:** {stats['projet_plus_cher']}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================================
# FONCTIONS D'AFFICHAGE DES MODALES
# =========================================================================

def afficher_details_projet_modal():
    """Affiche les détails complets d'un projet dans une modale"""
    if not st.session_state.get('show_project_details') or not st.session_state.get('selected_project_id'):
        return
    
    erp_db = st.session_state.erp_db
    project_id = st.session_state.selected_project_id
    
    try:
        # Récupérer les détails complets du projet
        query = '''
            SELECT p.*, 
                   c.nom as company_nom,
                   c.secteur as company_secteur,
                   c.adresse as company_adresse,
                   COUNT(DISTINCT o.id) as nb_operations_total,
                   COUNT(DISTINCT m.id) as nb_materiaux_total,
                   COUNT(DISTINCT pa.employee_id) as nb_employes_total,
                   COALESCE(SUM(m.quantite * m.prix_unitaire), 0) as cout_materiaux_total
            FROM projects p
            LEFT JOIN companies c ON p.client_company_id = c.id
            LEFT JOIN operations o ON p.id = o.project_id
            LEFT JOIN materials m ON p.id = m.project_id
            LEFT JOIN project_assignments pa ON p.id = pa.project_id
            WHERE p.id = ?
            GROUP BY p.id
        '''
        
        result = erp_db.execute_query(query, (project_id,))
        if not result:
            st.error("❌ Projet non trouvé")
            return
        
        projet = dict(result[0])
        
        with st.expander(f"🔍 Détails Complets - Projet #{projet.get('id', '')}", expanded=True):
            
            # En-tête avec informations principales
            st.markdown(f"### 📋 {projet.get('nom_projet', 'Projet sans nom')}")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**📊 Informations Générales**")
                st.write(f"**ID:** #{projet.get('id')}")
                st.write(f"**Statut:** {projet.get('statut', 'N/A')}")
                st.write(f"**Priorité:** {projet.get('priorite', 'N/A')}")
                st.write(f"**Date création:** {projet.get('date_soumis', 'N/A')}")
                st.write(f"**Date prévue:** {projet.get('date_prevu', 'N/A')}")
            
            with col2:
                st.markdown("**👤 Informations Client**")
                st.write(f"**Client:** {get_client_display_name(projet)}")
                st.write(f"**Secteur:** {projet.get('company_secteur', 'Non spécifié')}")
                st.write(f"**Adresse:** {projet.get('company_adresse', 'Non spécifiée')}")
                st.write(f"**Type:** {projet.get('company_type', 'N/A')}")
            
            with col3:
                st.markdown("**💰 Informations Financières**")
                st.write(f"**Prix estimé:** {format_currency(projet.get('prix_estime'))}")
                st.write(f"**BD/FT estimé:** {projet.get('bd_ft_estime', 'N/A')}")
                st.write(f"**Coût matériaux:** {format_currency(projet.get('cout_materiaux_total'))}")
            
            # Section ressources et progression
            st.markdown("---")
            col4, col5, col6 = st.columns(3)
            
            with col4:
                st.metric("⚙️ Opérations", projet.get('nb_operations_total', 0))
            
            with col5:
                st.metric("📦 Matériaux", projet.get('nb_materiaux_total', 0))
            
            with col6:
                st.metric("👥 Employés Assignés", projet.get('nb_employes_total', 0))
            
            # Description si disponible
            if projet.get('description'):
                st.markdown("**📝 Description:**")
                st.write(projet['description'])
            
            # Tâches si disponibles
            if projet.get('tache'):
                st.markdown("**✅ Tâches:**")
                st.write(projet['tache'])
            
            # Dates de réalisation
            if projet.get('date_debut_reel') or projet.get('date_fin_reel'):
                st.markdown("**📅 Dates de Réalisation:**")
                col_dates1, col_dates2 = st.columns(2)
                with col_dates1:
                    st.write(f"**Début réel:** {projet.get('date_debut_reel', 'Non commencé')}")
                with col_dates2:
                    st.write(f"**Fin réelle:** {projet.get('date_fin_reel', 'Non terminé')}")
            
            # Boutons d'action
            st.markdown("---")
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                if st.button("✏️ Modifier Projet", key="edit_project_btn"):
                    st.info("🚧 Fonctionnalité de modification à implémenter")
            
            with col_btn2:
                if st.button("📊 Voir Opérations", key="view_operations_btn"):
                    st.info("🚧 Vue des opérations à implémenter")
            
            with col_btn3:
                if st.button("❌ Fermer", key="close_project_modal"):
                    st.session_state.show_project_details = False
                    st.session_state.selected_project_id = None
                    st.rerun()
                
    except Exception as e:
        logger.error(f"Erreur affichage détails projet {project_id}: {e}")
        st.error(f"❌ Erreur lors de l'affichage des détails: {e}")

# =========================================================================
# FONCTION PRINCIPALE DU KANBAN
# =========================================================================

def show_kanban_projets():
    """Fonction principale pour afficher le kanban des projets"""
    
    # CSS complet
    afficher_css_kanban_complet()
    
    # Vérification de la base de données
    if 'erp_db' not in st.session_state:
        st.error("⚠️ Base de données ERP non initialisée.")
        st.info("💡 Assurez-vous que erp_database.py est correctement chargé dans votre application.")
        return
    
    erp_db = st.session_state.erp_db
    
    # Titre principal
    st.markdown("## 📋 Vue Kanban - Gestion des Projets")
    st.markdown("*Visualisez et gérez vos projets par statut avec glisser-déposer*")
    
    # Initialisation des variables de session pour drag & drop
    if 'dragged_project_id' not in st.session_state:
        st.session_state.dragged_project_id = None
    if 'dragged_from_status' not in st.session_state:
        st.session_state.dragged_from_status = None
    if 'show_project_details' not in st.session_state:
        st.session_state.show_project_details = False
    if 'selected_project_id' not in st.session_state:
        st.session_state.selected_project_id = None
    
    # Interface de recherche et filtres
    with st.expander("🔍 Recherche et Filtres", expanded=False):
        col_search1, col_search2 = st.columns([3, 1])
        
        with col_search1:
            recherche = st.text_input(
                "Rechercher un projet...", 
                key="kanban_search",
                placeholder="Nom du projet, client, ID..."
            )
        
        with col_search2:
            if st.button("🔄 Actualiser", help="Recharger les données"):
                st.rerun()
    
    # Récupération et traitement des données
    try:
        with st.spinner("⏳ Chargement des projets..."):
            projets = get_projets_for_kanban(erp_db)
        
        # Appliquer la recherche si nécessaire
        if recherche:
            projets = filtrer_projets_kanban(projets, recherche)
            st.info(f"🔍 {len(projets)} projet(s) trouvé(s) pour '{recherche}'")
        
        # Vérification des données
        if not projets:
            st.warning("⚠️ Aucun projet trouvé dans le système.")
            
            col_empty1, col_empty2 = st.columns(2)
            
            with col_empty1:
                st.info("💡 **Options disponibles:**")
                st.write("• Créez des projets de test pour découvrir le kanban")
                st.write("• Ajoutez de vrais projets via l'interface de gestion")
                st.write("• Vérifiez que la base de données contient des projets")
            
            with col_empty2:
                if st.button("🔧 Créer des Projets de Test", 
                           help="Génère 5 projets d'exemple réalistes",
                           use_container_width=True):
                    if creer_projets_de_test(erp_db):
                        st.rerun()
            return
        
        # Organisation des projets par statut
        projets_par_statut = organiser_projets_par_statut(projets)
        
        # Affichage de l'indicateur de drag & drop
        if st.session_state.dragged_project_id:
            projet_nom = "Projet inconnu"
            for statut_projets in projets_par_statut.values():
                for p in statut_projets:
                    if p['id'] == st.session_state.dragged_project_id:
                        projet_nom = p.get('nom_projet', 'Projet sans nom')
                        break
            
            st.markdown(f"""
            <div class='drag-indicator'>
                🔄 Déplacement en cours: <strong>#{st.session_state.dragged_project_id} - {projet_nom[:30]}{'...' if len(projet_nom) > 30 else ''}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            # Bouton d'annulation dans la sidebar
            with st.sidebar:
                st.markdown("### 🔄 Déplacement en Cours")
                st.write(f"**Projet:** #{st.session_state.dragged_project_id}")
                st.write(f"**De:** {st.session_state.dragged_from_status}")
                
                if st.button("❌ Annuler Déplacement", use_container_width=True):
                    st.session_state.dragged_project_id = None
                    st.session_state.dragged_from_status = None
                    st.rerun()
        
        # Affichage principal du kanban
        st.markdown('<div class="kanban-container">', unsafe_allow_html=True)
        
        colonnes = st.columns(len(STATUTS_PROJETS_KANBAN))
        
        for idx, statut in enumerate(STATUTS_PROJETS_KANBAN):
            with colonnes[idx]:
                nb_projets = len(projets_par_statut[statut])
                couleur_statut = COULEURS_STATUTS_PROJETS.get(statut, '#6b7280')
                
                # En-tête de colonne avec style
                st.markdown(f"""
                <div class="kanban-column">
                    <div class="kanban-header" style="background: linear-gradient(135deg, {couleur_statut}, {couleur_statut}dd);">
                        {statut} ({nb_projets})
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown('<div class="kanban-cards-zone">', unsafe_allow_html=True)
                
                # Zone de dépôt pour drag & drop
                if (st.session_state.dragged_project_id and 
                    statut != st.session_state.dragged_from_status):
                    
                    st.markdown('<div class="drop-zone">', unsafe_allow_html=True)
                    if st.button(f"⬇️ Déposer dans {statut}", 
                               key=f"drop_{statut}", 
                               use_container_width=True,
                               help=f"Déplacer le projet vers {statut}"):
                        
                        if deplacer_projet_vers_statut(erp_db, st.session_state.dragged_project_id, statut):
                            st.success(f"✅ Projet déplacé vers {statut} avec succès !")
                            st.session_state.dragged_project_id = None
                            st.session_state.dragged_from_status = None
                            time.sleep(1)  # Pause pour voir le message
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Affichage des projets dans la colonne
                if not projets_par_statut[statut]:
                    st.markdown('<div class="empty-column">Aucun projet dans ce statut</div>', unsafe_allow_html=True)
                else:
                    # Tri intelligent des projets
                    projets_tries = sorted(
                        projets_par_statut[statut], 
                        key=lambda p: (
                            # Priorité (ÉLEVÉ en premier)
                            0 if p.get('priorite') == 'ÉLEVÉ' else 1 if p.get('priorite') == 'MOYEN' else 2,
                            # Date d'échéance (plus proche en premier)
                            p.get('date_prevu', '9999-12-31'),
                            # ID (plus récent en premier)
                            -p.get('id', 0)
                        )
                    )
                    
                    for projet in projets_tries:
                        afficher_carte_projet(projet, statut)
                
                st.markdown('</div></div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Statistiques complètes
        st.markdown("---")
        afficher_statistiques_kanban(projets_par_statut)
        
        # Modale des détails de projet
        afficher_details_projet_modal()
        
        # Actions rapides en bas de page
        with st.expander("⚡ Actions Rapides et Outils", expanded=False):
            col_actions1, col_actions2, col_actions3, col_actions4 = st.columns(4)
            
            with col_actions1:
                if st.button("🔧 Créer Projets Test", 
                           help="Ajouter des projets de démonstration réalistes"):
                    creer_projets_de_test(erp_db)
                    st.rerun()
            
            with col_actions2:
                if st.button("📊 Export Données", 
                           help="Exporter les données du kanban"):
                    st.info("🚧 Fonctionnalité d'export à implémenter")
            
            with col_actions3:
                if st.button("⚙️ Configuration", 
                           help="Configurer les statuts et couleurs"):
                    st.info("🚧 Interface de configuration à implémenter")
            
            with col_actions4:
                total_projets = sum(len(projets) for projets in projets_par_statut.values())
                st.metric("📈 Total Affiché", total_projets)
        
    except Exception as e:
        logger.error(f"Erreur critique dans show_kanban_projets: {e}")
        st.error(f"❌ Erreur critique lors de l'affichage du kanban: {e}")
        st.info("💡 Essayez de recharger la page ou contactez l'administrateur.")

# =========================================================================
# POINTS D'ENTRÉE POUR COMPATIBILITÉ
# =========================================================================

def show_kanban_sqlite():
    """Point d'entrée principal pour remplacer l'ancien kanban"""
    show_kanban_projets()

def show_kanban():
    """Point d'entrée alternatif pour compatibilité"""
    show_kanban_projets()

def app():
    """Point d'entrée pour l'application standalone"""
    show_kanban_projets()

# =========================================================================
# FONCTIONS D'UTILITAIRES POUR L'INTÉGRATION
# =========================================================================

def get_kanban_status():
    """Retourne le statut du module kanban pour diagnostic"""
    return {
        'module_name': 'kanban.py',
        'version': '2.0.0',
        'status': 'operational',
        'functions_available': [
            'show_kanban_projets', 'show_kanban_sqlite', 'show_kanban', 'app'
        ],
        'dependencies': ['streamlit', 'erp_database'],
        'last_updated': '2025-01-04'
    }

def validate_database_connection():
    """Valide la connexion à la base de données"""
    if 'erp_db' not in st.session_state:
        return False, "erp_db non trouvé dans session_state"
    
    try:
        erp_db = st.session_state.erp_db
        test_query = "SELECT COUNT(*) as count FROM projects LIMIT 1"
        result = erp_db.execute_query(test_query)
        return True, f"Connexion OK - {result[0]['count'] if result else 0} projets"
    except Exception as e:
        return False, f"Erreur connexion: {e}"

# =========================================================================
# SCRIPT DE TEST ET DEBUG
# =========================================================================

if __name__ == "__main__":
    st.set_page_config(
        page_title="Kanban Projets - Test",
        page_icon="📋",
        layout="wide"
    )
    
    st.title("📋 Module Kanban - Test Autonome")
    st.markdown("---")
    
    # Diagnostic du module
    status = get_kanban_status()
    st.json(status)
    
    # Test de la base de données
    db_ok, db_message = validate_database_connection()
    if db_ok:
        st.success(f"✅ Base de données: {db_message}")
        
        # Lancer le kanban
        st.markdown("---")
        show_kanban_projets()
        
    else:
        st.error(f"❌ Base de données: {db_message}")
        st.info("💡 Ce module doit être lancé depuis app.py avec erp_database initialisé.")
