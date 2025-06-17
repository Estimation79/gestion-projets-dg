# formulaires/utils/helpers.py
# Fonctions utilitaires communes pour les formulaires - VERSION CORRIGÉE SQLite

"""
Fonctions utilitaires communes utilisées dans tous les modules de formulaires.
Inclut les fonctions de récupération de données depuis la base ERP.
VERSION CORRIGÉE : Utilise les bonnes colonnes SQLite selon le schéma erp_database.py
"""

import streamlit as st
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
import hashlib


# =============================================================================
# FONCTIONS DE RÉCUPÉRATION DE DONNÉES ERP - CORRIGÉES
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
                   date_soumis, date_prevu, client_nom_cache
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
            SELECT id, prenom, nom, poste, departement, email, telephone, statut
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
            SELECT id, nom, secteur, adresse, site_web, contact_principal_id
            FROM companies 
            WHERE type_company = 'FOURNISSEUR'
               OR secteur LIKE '%FOURNISSEUR%' 
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
            SELECT id, nom, secteur, adresse, site_web, contact_principal_id
            FROM companies 
            WHERE type_company != 'FOURNISSEUR'
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
                   work_center_id, statut, ressource, poste_travail
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
                   unite, code_materiau, fournisseur
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
    CORRIGÉ: Utilise les bonnes colonnes selon erp_database.py
    
    Returns:
        List[Dict]: Liste des postes de travail
    """
    try:
        query = """
            SELECT id, nom, departement, categorie, type_machine, 
                   capacite_theorique, operateurs_requis, cout_horaire, 
                   competences_requises, statut, localisation
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
    CORRIGÉ: Utilise les bonnes colonnes selon erp_database.py
    
    Returns:
        List[Dict]: Liste des articles avec stock
    """
    try:
        query = """
            SELECT id, nom, type_produit, quantite_imperial, quantite_metric,
                   limite_minimale_imperial, limite_minimale_metric,
                   quantite_reservee_imperial, quantite_reservee_metric,
                   statut, description, notes, fournisseur_principal, code_interne
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
    CORRIGÉ: Utilise les bonnes colonnes selon erp_database.py
    
    Returns:
        List[Dict]: Articles en stock critique
    """
    try:
        query = """
            SELECT id, nom, type_produit, quantite_imperial, quantite_metric,
                   limite_minimale_imperial, limite_minimale_metric, statut,
                   description, fournisseur_principal
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
    CORRIGÉ: Utilise les bonnes colonnes selon erp_database.py
    
    Args:
        search_term: Terme de recherche
        
    Returns:
        List[Dict]: Articles correspondant à la recherche
    """
    try:
        if not search_term or len(search_term) < 2:
            return []
        
        query = """
            SELECT id, nom, type_produit, quantite_imperial, quantite_metric,
                   statut, description, fournisseur_principal
            FROM inventory_items 
            WHERE LOWER(nom) LIKE LOWER(?) 
               OR LOWER(type_produit) LIKE LOWER(?)
               OR LOWER(description) LIKE LOWER(?)
            ORDER BY nom
            LIMIT 20
        """
        search_pattern = f"%{search_term}%"
        rows = st.session_state.erp_db.execute_query(query, (search_pattern, search_pattern, search_pattern))
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
            SELECT id, nom_projet, statut, prix_estime, date_soumis, date_prevu,
                   bd_ft_estime, description
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
    CORRIGÉ: Utilise les bonnes colonnes selon erp_database.py
    
    Args:
        work_center_id: ID du poste de travail
        
    Returns:
        Dict: Informations du poste ou None
    """
    try:
        if not work_center_id:
            return None
        
        query = """
            SELECT id, nom, cout_horaire, departement, capacite_theorique,
                   categorie, type_machine, operateurs_requis, competences_requises,
                   statut, localisation
            FROM work_centers 
            WHERE id = ?
        """
        rows = st.session_state.erp_db.execute_query(query, (work_center_id,))
        return dict(rows[0]) if rows else None
    except Exception as e:
        st.error(f"Erreur récupération poste travail: {e}")
        return None


def get_companies_by_type(company_type: str = None) -> List[Dict]:
    """
    Récupère les entreprises par type (CLIENT, FOURNISSEUR, etc.)
    
    Args:
        company_type: Type d'entreprise recherché
        
    Returns:
        List[Dict]: Liste des entreprises
    """
    try:
        if company_type:
            # Recherche par secteur, type_company ou notes
            query = """
                SELECT id, nom, secteur, adresse, site_web, type_company,
                       contact_principal_id, notes
                FROM companies 
                WHERE UPPER(secteur) LIKE UPPER(?) 
                   OR UPPER(type_company) LIKE UPPER(?)
                   OR UPPER(notes) LIKE UPPER(?)
                ORDER BY nom
            """
            pattern = f"%{company_type}%"
            rows = st.session_state.erp_db.execute_query(query, (pattern, pattern, pattern))
        else:
            query = """
                SELECT id, nom, secteur, adresse, site_web, type_company,
                       contact_principal_id, notes
                FROM companies 
                ORDER BY nom
            """
            rows = st.session_state.erp_db.execute_query(query)
        
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération companies: {e}")
        return []


def get_contacts_company(company_id: int) -> List[Dict]:
    """
    Récupère les contacts d'une entreprise spécifique.
    
    Args:
        company_id: ID de l'entreprise
        
    Returns:
        List[Dict]: Liste des contacts de l'entreprise
    """
    try:
        query = """
            SELECT id, prenom, nom_famille, email, telephone, role_poste, notes
            FROM contacts 
            WHERE company_id = ?
            ORDER BY prenom, nom_famille
        """
        rows = st.session_state.erp_db.execute_query(query, (company_id,))
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération contacts: {e}")
        return []


def get_unites_mesure_disponibles() -> List[str]:
    """
    Récupère toutes les unités de mesure utilisées dans le système.
    
    Returns:
        List[str]: Liste des unités de mesure
    """
    try:
        # Unités de base
        unites_base = [
            "Pièces", "Kilogrammes", "Grammes", "Tonnes",
            "Mètres", "Centimètres", "Millimètres", "Kilomètres",
            "Mètres²", "Centimètres²", "Mètres³", "Centimètres³",
            "Litres", "Millilitres", "Heures", "Minutes",
            "Jours", "Semaines", "Mois"
        ]
        
        # Unités depuis la base de données
        try:
            query_materials = "SELECT DISTINCT unite FROM materials WHERE unite IS NOT NULL AND unite != ''"
            unites_materials = st.session_state.erp_db.execute_query(query_materials)
            unites_db = [u['unite'] for u in unites_materials if u['unite']]
            
            # Combiner et dédoublonner
            all_unites = sorted(list(set(unites_base + unites_db)))
            return all_unites
            
        except Exception:
            return sorted(unites_base)
            
    except Exception as e:
        st.error(f"Erreur récupération unités: {e}")
        return ["Pièces", "Kilogrammes", "Mètres", "Heures"]


def get_types_operations_disponibles() -> List[str]:
    """
    Récupère tous les types d'opération utilisés dans le système.
    
    Returns:
        List[str]: Liste des types d'opération
    """
    try:
        # Types de base pour DG Inc.
        types_base = [
            "Programmation CNC", "Découpe plasma", "Poinçonnage", "Soudage TIG",
            "Soudage MIG", "Assemblage", "Meulage", "Polissage", "Emballage",
            "Contrôle qualité", "Usinage conventionnel", "Perçage", "Taraudage",
            "Pliage", "Roulage", "Finition", "Peinture", "Galvanisation"
        ]
        
        # Types depuis la base de données
        try:
            query = """
                SELECT DISTINCT description 
                FROM operations 
                WHERE description IS NOT NULL AND description != ''
                ORDER BY description
            """
            types_db = st.session_state.erp_db.execute_query(query)
            types_operations = [t['description'] for t in types_db if t['description']]
            
            # Combiner et dédoublonner
            all_types = sorted(list(set(types_base + types_operations)))
            return all_types
            
        except Exception:
            return sorted(types_base)
            
    except Exception as e:
        st.error(f"Erreur récupération types opération: {e}")
        return sorted(types_base)


def get_statuts_disponibles() -> Dict[str, List[str]]:
    """
    Récupère tous les statuts disponibles pour les différents éléments.
    
    Returns:
        Dict[str, List[str]]: Statuts par type d'élément
    """
    return {
        'formulaires': ['BROUILLON', 'VALIDÉ', 'ENVOYÉ', 'APPROUVÉ', 'TERMINÉ', 'ANNULÉ'],
        'projets': ['À FAIRE', 'EN COURS', 'EN PAUSE', 'TERMINÉ', 'ANNULÉ'],
        'operations': ['À FAIRE', 'EN COURS', 'EN PAUSE', 'TERMINÉ', 'ANNULÉ'],
        'employees': ['ACTIF', 'INACTIF', 'CONGÉ', 'DÉMISSIONNÉ'],
        'work_centers': ['ACTIF', 'INACTIF', 'MAINTENANCE', 'HORS_SERVICE'],
        'inventory': ['DISPONIBLE', 'FAIBLE', 'CRITIQUE', 'ÉPUISÉ', 'COMMANDÉ'],
        'priorites': ['NORMAL', 'URGENT', 'CRITIQUE']
    }


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


def calculer_prix_estime_article(article: Dict, quantite: float) -> float:
    """
    Calcule un prix estimé pour un article basé sur les données disponibles.
    
    Args:
        article: Informations de l'article
        quantite: Quantité demandée
        
    Returns:
        float: Prix estimé total
    """
    try:
        # Prix de base fictif basé sur le type de produit
        prix_base_par_type = {
            'ACIER': 2.5,
            'ALUMINIUM': 4.0,
            'INOX': 6.0,
            'CUIVRE': 8.0,
            'PLASTIQUE': 1.5,
            'ÉLECTRONIQUE': 15.0,
            'OUTIL': 25.0,
            'CONSOMMABLE': 1.0
        }
        
        type_produit = article.get('type_produit', '').upper()
        prix_unitaire_base = 5.0  # Prix par défaut
        
        for type_key, prix in prix_base_par_type.items():
            if type_key in type_produit:
                prix_unitaire_base = prix
                break
        
        # Variation selon la disponibilité
        facteur_disponibilite = 1.0
        statut = article.get('statut', '').upper()
        if 'CRITIQUE' in statut or 'ÉPUISÉ' in statut:
            facteur_disponibilite = 1.3  # Prix plus élevé si rare
        elif 'FAIBLE' in statut:
            facteur_disponibilite = 1.1
        
        prix_total = quantite * prix_unitaire_base * facteur_disponibilite
        return round(prix_total, 2)
        
    except Exception:
        return quantite * 5.0  # Prix de secours


def convertir_quantite_metric(quantite_imperial: str, type_produit: str = "") -> float:
    """
    Convertit une quantité impériale en métrique (approximatif).
    
    Args:
        quantite_imperial: Quantité en format impérial
        type_produit: Type de produit pour contexte
        
    Returns:
        float: Quantité en métrique
    """
    try:
        if not quantite_imperial:
            return 0.0
        
        # Extraction numérique simple
        import re
        numbers = re.findall(r'\d+\.?\d*', str(quantite_imperial))
        if not numbers:
            return 0.0
        
        value = float(numbers[0])
        
        # Conversions approximatives selon le contenu
        quantite_str = str(quantite_imperial).lower()
        
        if 'lb' in quantite_str or 'livre' in quantite_str:
            return value * 0.453592  # livres vers kg
        elif 'oz' in quantite_str or 'once' in quantite_str:
            return value * 0.0283495  # onces vers kg
        elif 'ft' in quantite_str or 'pied' in quantite_str:
            return value * 0.3048  # pieds vers mètres
        elif 'in' in quantite_str or 'pouce' in quantite_str:
            return value * 0.0254  # pouces vers mètres
        elif 'gal' in quantite_str or 'gallon' in quantite_str:
            return value * 3.78541  # gallons vers litres
        else:
            return value  # Déjà métrique ou unité inconnue
            
    except Exception:
        return 0.0


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


def formater_quantite(quantite: float, unite: str = "") -> str:
    """
    Formate une quantité pour l'affichage.
    
    Args:
        quantite: Quantité numérique
        unite: Unité de mesure
        
    Returns:
        str: Quantité formatée
    """
    try:
        if quantite == int(quantite):
            return f"{int(quantite)} {unite}".strip()
        else:
            return f"{quantite:.2f} {unite}".strip()
    except:
        return f"{quantite} {unite}".strip()


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
        'ANNULÉ': '#ef4444',       # Rouge
        'À FAIRE': '#6b7280',      # Gris
        'EN COURS': '#3b82f6',     # Bleu
        'EN PAUSE': '#f59e0b',     # Orange
        'ACTIF': '#10b981',        # Vert
        'INACTIF': '#6b7280',      # Gris
        'DISPONIBLE': '#10b981',   # Vert
        'CRITIQUE': '#ef4444',     # Rouge
        'ÉPUISÉ': '#dc2626',       # Rouge foncé
        'FAIBLE': '#f59e0b'        # Orange
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


def generer_icone_statut(statut: str) -> str:
    """
    Génère une icône selon le statut.
    
    Args:
        statut: Statut du document
        
    Returns:
        str: Icône emoji
    """
    icones = {
        'BROUILLON': '📝', 'VALIDÉ': '✅', 'ENVOYÉ': '📤', 'APPROUVÉ': '👍',
        'TERMINÉ': '🎯', 'ANNULÉ': '❌', 'À FAIRE': '📋', 'EN COURS': '⚡',
        'EN PAUSE': '⏸️', 'ACTIF': '🟢', 'INACTIF': '🔴', 'DISPONIBLE': '✅',
        'CRITIQUE': '🚨', 'ÉPUISÉ': '❌', 'FAIBLE': '⚠️', 'NORMAL': '🟢',
        'URGENT': '🟡', 'CRITIQUE': '🔴'
    }
    
    return icones.get(statut, '⚪')


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


def valider_disponibilite_stock(article_id: int, quantite_demandee: float) -> Tuple[bool, str, float]:
    """
    Valide la disponibilité d'un article en stock.
    
    Args:
        article_id: ID de l'article
        quantite_demandee: Quantité demandée
        
    Returns:
        Tuple[bool, str, float]: (disponible, message, quantite_disponible)
    """
    try:
        query = """
            SELECT quantite_metric, quantite_reservee_metric, statut
            FROM inventory_items 
            WHERE id = ?
        """
        result = st.session_state.erp_db.execute_query(query, (article_id,))
        
        if not result:
            return False, "Article non trouvé", 0.0
        
        article = result[0]
        quantite_stock = article['quantite_metric'] or 0.0
        quantite_reservee = article['quantite_reservee_metric'] or 0.0
        quantite_disponible = quantite_stock - quantite_reservee
        
        if quantite_disponible <= 0:
            return False, f"Stock épuisé (réservé: {quantite_reservee})", quantite_disponible
        elif quantite_disponible < quantite_demandee:
            return False, f"Stock insuffisant (disponible: {quantite_disponible})", quantite_disponible
        else:
            return True, "Stock suffisant", quantite_disponible
            
    except Exception as e:
        return False, f"Erreur vérification stock: {e}", 0.0
