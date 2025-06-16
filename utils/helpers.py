# formulaires/utils/helpers.py
# Fonctions utilitaires communes pour les formulaires

"""
Fonctions utilitaires communes utilisées dans tous les modules de formulaires.
Inclut les fonctions de récupération de données depuis la base ERP.
"""

import streamlit as st
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
import hashlib


# =============================================================================
# FONCTIONS DE RÉCUPÉRATION DE DONNÉES ERP
# =============================================================================

def get_projets_actifs() -> List[Dict]:
    """
    Récupère la liste des projets actifs.
    
    Returns:
        List[Dict]: Liste des projets avec leurs informations
    """
    try:
        query = """
            SELECT id, nom_projet, statut, prix_estime, client_company_id,
                   date_soumis, date_prevu
            FROM projects 
            WHERE statut NOT IN ('TERMINÉ', 'ANNULÉ') 
            ORDER BY nom_projet
        """
        rows = st.session_state.erp_db.execute_query(query)
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération projets: {e}")
        return []


def get_employes_actifs() -> List[Dict]:
    """
    Récupère la liste des employés actifs.
    
    Returns:
        List[Dict]: Liste des employés avec leurs informations
    """
    try:
        query = """
            SELECT id, prenom, nom, poste, departement, email, telephone
            FROM employees 
            WHERE statut = 'ACTIF' 
            ORDER BY prenom, nom
        """
        rows = st.session_state.erp_db.execute_query(query)
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération employés: {e}")
        return []


def get_fournisseurs_actifs() -> List[Dict]:
    """
    Récupère la liste des fournisseurs actifs depuis le CRM.
    
    Returns:
        List[Dict]: Liste des fournisseurs avec leurs informations
    """
    try:
        query = """
            SELECT id, nom, secteur, adresse, email, telephone, pays
            FROM companies 
            WHERE secteur LIKE '%FOURNISSEUR%' 
               OR secteur LIKE '%DISTRIBUTION%' 
               OR secteur LIKE '%COMMERCE%'
               OR id IN (
                   SELECT DISTINCT company_id 
                   FROM formulaires 
                   WHERE type_formulaire IN ('BON_ACHAT', 'BON_COMMANDE')
               )
            ORDER BY nom
        """
        rows = st.session_state.erp_db.execute_query(query)
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération fournisseurs: {e}")
        return []


def get_clients_actifs() -> List[Dict]:
    """
    Récupère la liste des clients depuis le CRM.
    
    Returns:
        List[Dict]: Liste des clients avec leurs informations
    """
    try:
        query = """
            SELECT id, nom, secteur, adresse, email, telephone, pays
            FROM companies 
            WHERE secteur NOT LIKE '%FOURNISSEUR%' 
               OR id IN (
                   SELECT DISTINCT company_id 
                   FROM formulaires 
                   WHERE type_formulaire = 'ESTIMATION'
               )
            ORDER BY nom
        """
        rows = st.session_state.erp_db.execute_query(query)
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération clients: {e}")
        return []


def get_operations_projet(projet_id: int) -> List[Dict]:
    """
    Récupère les opérations d'un projet spécifique.
    
    Args:
        projet_id: ID du projet
        
    Returns:
        List[Dict]: Liste des opérations du projet
    """
    try:
        query = """
            SELECT id, sequence_number as sequence, description, temps_estime,
                   work_center_id, statut
            FROM operations 
            WHERE project_id = ? 
            ORDER BY sequence_number
        """
        rows = st.session_state.erp_db.execute_query(query, (projet_id,))
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération opérations: {e}")
        return []


def get_materiaux_projet(projet_id: int) -> List[Dict]:
    """
    Récupère les matériaux d'un projet spécifique.
    
    Args:
        projet_id: ID du projet
        
    Returns:
        List[Dict]: Liste des matériaux du projet
    """
    try:
        query = """
            SELECT id, designation as description, quantite, prix_unitaire, 
                   unite, statut
            FROM materials 
            WHERE project_id = ?
            ORDER BY designation
        """
        rows = st.session_state.erp_db.execute_query(query, (projet_id,))
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération matériaux: {e}")
        return []


def get_work_centers_actifs() -> List[Dict]:
    """
    Récupère la liste des postes de travail actifs.
    
    Returns:
        List[Dict]: Liste des postes de travail
    """
    try:
        query = """
            SELECT id, nom, departement, cout_horaire, capacite_max
            FROM work_centers 
            WHERE statut = 'ACTIF'
            ORDER BY departement, nom
        """
        rows = st.session_state.erp_db.execute_query(query)
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération postes travail: {e}")
        return []


def get_articles_inventaire() -> List[Dict]:
    """
    Récupère tous les articles de l'inventaire.
    
    Returns:
        List[Dict]: Liste des articles avec stock
    """
    try:
        query = """
            SELECT id, nom, type_produit, quantite_imperial, 
                   limite_minimale_imperial, statut, prix_unitaire_moyen
            FROM inventory_items 
            ORDER BY nom
        """
        rows = st.session_state.erp_db.execute_query(query)
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération inventaire: {e}")
        return []


def get_articles_inventaire_critique() -> List[Dict]:
    """
    Récupère les articles avec stock critique nécessitant réapprovisionnement.
    
    Returns:
        List[Dict]: Articles en stock critique
    """
    try:
        query = """
            SELECT id, nom, type_produit, quantite_imperial, 
                   limite_minimale_imperial, statut
            FROM inventory_items 
            WHERE statut IN ('CRITIQUE', 'FAIBLE', 'ÉPUISÉ')
            ORDER BY 
                CASE statut 
                    WHEN 'ÉPUISÉ' THEN 1
                    WHEN 'CRITIQUE' THEN 2 
                    WHEN 'FAIBLE' THEN 3
                END, nom
        """
        rows = st.session_state.erp_db.execute_query(query)
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération stocks critiques: {e}")
        return []


def search_articles_inventaire(search_term: str) -> List[Dict]:
    """
    Recherche dans l'inventaire par nom ou type.
    
    Args:
        search_term: Terme de recherche
        
    Returns:
        List[Dict]: Articles correspondant à la recherche
    """
    try:
        if not search_term or len(search_term) < 2:
            return []
        
        query = """
            SELECT id, nom, type_produit, quantite_imperial, statut, prix_unitaire_moyen
            FROM inventory_items 
            WHERE LOWER(nom) LIKE LOWER(?) 
               OR LOWER(type_produit) LIKE LOWER(?)
            ORDER BY nom
            LIMIT 20
        """
        search_pattern = f"%{search_term}%"
        rows = st.session_state.erp_db.execute_query(query, (search_pattern, search_pattern))
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur recherche inventaire: {e}")
        return []


def get_projets_client(client_id: int) -> List[Dict]:
    """
    Récupère les projets d'un client spécifique.
    
    Args:
        client_id: ID du client
        
    Returns:
        List[Dict]: Projets du client
    """
    try:
        query = """
            SELECT id, nom_projet, statut, prix_estime, date_soumis, date_prevu
            FROM projects 
            WHERE client_company_id = ? 
            ORDER BY date_soumis DESC
        """
        rows = st.session_state.erp_db.execute_query(query, (client_id,))
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération projets client: {e}")
        return []


def get_poste_travail(work_center_id: int) -> Optional[Dict]:
    """
    Récupère les informations d'un poste de travail spécifique.
    
    Args:
        work_center_id: ID du poste de travail
        
    Returns:
        Dict: Informations du poste ou None
    """
    try:
        if not work_center_id:
            return None
        
        query = """
            SELECT id, nom, cout_horaire, departement, capacite_max
            FROM work_centers 
            WHERE id = ?
        """
        rows = st.session_state.erp_db.execute_query(query, (work_center_id,))
        return dict(rows[0]) if rows else None
    except Exception as e:
        st.error(f"Erreur récupération poste travail: {e}")
        return None


# =============================================================================
# FONCTIONS UTILITAIRES CALCULÉES
# =============================================================================

def calculer_quantite_recommandee(article: Dict) -> int:
    """
    Calcule la quantité recommandée pour un réapprovisionnement.
    
    Args:
        article: Informations de l'article
        
    Returns:
        int: Quantité recommandée
    """
    try:
        # Logique simple basée sur le statut
        statut = article.get('statut', 'NORMAL').upper()
        
        if 'ÉPUISÉ' in statut:
            return 50  # Stock de sécurité important
        elif 'CRITIQUE' in statut:
            return 30  # Réapprovisionnement critique
        elif 'FAIBLE' in statut:
            return 20  # Réapprovisionnement préventif
        else:
            return 10  # Minimum standard
            
    except Exception:
        return 10


def get_note_fournisseur_fictive(fournisseur: Dict) -> int:
    """
    Calcule une note fictive pour un fournisseur (pour la démo).
    Dans un vrai système, cette note viendrait de l'historique des évaluations.
    
    Args:
        fournisseur: Informations du fournisseur
        
    Returns:
        int: Note entre 1 et 10
    """
    try:
        # Utilisation d'un hash pour avoir une note cohérente mais "aléatoire"
        hash_val = int(hashlib.md5(str(fournisseur['id']).encode()).hexdigest()[:8], 16)
        return (hash_val % 5) + 6  # Note entre 6 et 10
    except:
        return 7  # Note par défaut


def generer_offres_fictives_rfq(dp_details: Dict, fournisseurs: List[Dict]) -> List[Dict]:
    """
    Génère des offres fictives pour une RFQ (pour la démo).
    
    Args:
        dp_details: Détails de la demande de prix
        fournisseurs: Liste des fournisseurs invités
        
    Returns:
        List[Dict]: Offres fictives générées
    """
    import random
    
    offres = []
    # Prix de base estimé
    base_price = random.uniform(10000, 50000)
    
    for i, fournisseur in enumerate(fournisseurs):
        note_qualite = get_note_fournisseur_fictive(fournisseur)
        
        # Variation de prix selon la "qualité" du fournisseur
        price_factor = 1.0 + (10 - note_qualite) * 0.05  # Meilleure qualité = prix plus élevé
        
        offre = {
            'fournisseur': fournisseur,
            'prix_total': round(base_price * price_factor * random.uniform(0.9, 1.1), 2),
            'delai_livraison': random.randint(7, 28),
            'note_qualite': note_qualite,
            'proximite_km': random.randint(10, 500),
            'experience_secteur': random.randint(5, 10),
            'conforme': random.choice([True, True, True, False]),  # 75% conformes
            'conditions_paiement': random.choice(['30j net', '45j net', '15j net']),
            'garantie': random.choice(['12 mois', '24 mois', '6 mois']),
            'notes': f"Offre standard de {fournisseur['nom']}"
        }
        offres.append(offre)
    
    return offres


# =============================================================================
# FONCTIONS DE FORMATAGE ET AFFICHAGE
# =============================================================================

def formater_montant(montant: float, devise: str = "CAD") -> str:
    """
    Formate un montant pour l'affichage.
    
    Args:
        montant: Montant à formater
        devise: Devise (CAD, USD, EUR)
        
    Returns:
        str: Montant formaté
    """
    try:
        if montant == 0:
            return f"0,00$ {devise}"
        elif montant >= 1000000:
            return f"{montant/1000000:.1f}M$ {devise}"
        elif montant >= 1000:
            return f"{montant/1000:.0f}k$ {devise}"
        else:
            return f"{montant:,.2f}$ {devise}"
    except:
        return f"0,00$ {devise}"


def formater_delai(jours: int) -> str:
    """
    Formate un délai en jours pour l'affichage.
    
    Args:
        jours: Nombre de jours
        
    Returns:
        str: Délai formaté
    """
    if jours == 0:
        return "Immédiat"
    elif jours == 1:
        return "1 jour"
    elif jours < 7:
        return f"{jours} jours"
    elif jours < 30:
        semaines = jours // 7
        jours_restants = jours % 7
        if jours_restants == 0:
            return f"{semaines} sem."
        else:
            return f"{semaines}sem. {jours_restants}j"
    else:
        mois = jours // 30
        jours_restants = jours % 30
        if jours_restants == 0:
            return f"{mois} mois"
        else:
            return f"{mois}m {jours_restants}j"


def calculer_statut_validite(date_validite: str) -> Tuple[str, str]:
    """
    Calcule le statut de validité d'un document.
    
    Args:
        date_validite: Date de validité (format ISO)
        
    Returns:
        Tuple[str, str]: (statut, description)
    """
    try:
        if not date_validite:
            return "unknown", "Non définie"
        
        date_val = datetime.strptime(date_validite, '%Y-%m-%d').date()
        today = datetime.now().date()
        jours_restants = (date_val - today).days
        
        if jours_restants < 0:
            return "expired", f"Expirée ({abs(jours_restants)}j)"
        elif jours_restants == 0:
            return "expires_today", "Expire aujourd'hui"
        elif jours_restants <= 3:
            return "expires_soon", f"Expire dans {jours_restants}j"
        elif jours_restants <= 7:
            return "valid_short", f"{jours_restants}j restants"
        else:
            return "valid", f"{jours_restants}j restants"
            
    except Exception:
        return "error", "Erreur date"


def generer_couleur_statut(statut: str) -> str:
    """
    Génère une couleur CSS selon le statut.
    
    Args:
        statut: Statut du document
        
    Returns:
        str: Code couleur CSS
    """
    couleurs = {
        'BROUILLON': '#f59e0b',    # Orange
        'VALIDÉ': '#3b82f6',       # Bleu
        'ENVOYÉ': '#8b5cf6',       # Violet
        'APPROUVÉ': '#10b981',     # Vert
        'TERMINÉ': '#059669',      # Vert foncé
        'ANNULÉ': '#ef4444'        # Rouge
    }
    
    return couleurs.get(statut, '#6b7280')  # Gris par défaut


def generer_couleur_priorite(priorite: str) -> str:
    """
    Génère une couleur CSS selon la priorité.
    
    Args:
        priorite: Priorité du document
        
    Returns:
        str: Code couleur CSS
    """
    couleurs = {
        'NORMAL': '#10b981',   # Vert
        'URGENT': '#f59e0b',   # Orange
        'CRITIQUE': '#ef4444'  # Rouge
    }
    
    return couleurs.get(priorite, '#6b7280')


# =============================================================================
# FONCTIONS DE VALIDATION MÉTIER
# =============================================================================

def verifier_coherence_dates_projet(date_debut: date, date_fin: date, 
                                   delai_estimation: int) -> Tuple[bool, str]:
    """
    Vérifie la cohérence entre les dates d'un projet et son délai estimé.
    
    Args:
        date_debut: Date de début du projet
        date_fin: Date de fin prévue
        delai_estimation: Délai estimé en jours
        
    Returns:
        Tuple[bool, str]: (coherent, message)
    """
    if not date_debut or not date_fin:
        return True, ""  # OK si dates manquantes
    
    ecart_reel = (date_fin - date_debut).days
    
    # Tolérance de ±20%
    tolerance = delai_estimation * 0.2
    
    if abs(ecart_reel - delai_estimation) > tolerance:
        return False, f"Incohérence: écart réel {ecart_reel}j vs estimé {delai_estimation}j"
    
    return True, ""


def valider_budget_projet_vs_estimation(budget_projet: float, 
                                       montant_estimation: float) -> Tuple[bool, str]:
    """
    Valide la cohérence entre le budget projet et l'estimation.
    
    Args:
        budget_projet: Budget alloué au projet
        montant_estimation: Montant de l'estimation
        
    Returns:
        Tuple[bool, str]: (coherent, message)
    """
    if budget_projet <= 0 or montant_estimation <= 0:
        return True, ""  # OK si montants non définis
    
    ecart_pct = abs(budget_projet - montant_estimation) / montant_estimation * 100
    
    # Alerte si écart > 15%
    if ecart_pct > 15:
        return False, f"Écart important: {ecart_pct:.1f}% entre budget et estimation"
    
    return True, ""


def calculer_taux_marge_realiste(cout_materiau: float, cout_main_oeuvre: float, 
                                prix_vente: float) -> Tuple[float, str]:
    """
    Calcule le taux de marge et vérifie s'il est réaliste.
    
    Args:
        cout_materiau: Coût des matériaux
        cout_main_oeuvre: Coût de la main d'œuvre
        prix_vente: Prix de vente proposé
        
    Returns:
        Tuple[float, str]: (taux_marge, evaluation)
    """
    cout_total = cout_materiau + cout_main_oeuvre
    
    if cout_total <= 0:
        return 0.0, "Coûts non définis"
    
    marge = prix_vente - cout_total
    taux_marge = (marge / cout_total) * 100
    
    if taux_marge < 5:
        evaluation = "Marge très faible - Risqué"
    elif taux_marge < 15:
        evaluation = "Marge acceptable"
    elif taux_marge < 30:
        evaluation = "Marge correcte"
    elif taux_marge < 50:
        evaluation = "Bonne marge"
    else:
        evaluation = "Marge élevée - Vérifier compétitivité"
    
    return taux_marge, evaluation
