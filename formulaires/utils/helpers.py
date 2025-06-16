# formulaires/utils/helpers.py
# Fonctions utilitaires communes pour les formulaires - VERSION COMPLÈTE SÉCURISÉE

"""
Fonctions utilitaires communes utilisées dans tous les modules de formulaires.
Version complète et sécurisée avec gestion d'erreurs robuste.

Inclut :
- Fonctions de récupération de données depuis la base ERP
- Fonctions de formatage et affichage  
- Fonctions de validation métier
- Fonctions de calcul et génération
"""

import streamlit as st
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import random


# =============================================================================
# FONCTION UTILITAIRE DE BASE - ACCÈS BASE DE DONNÉES SÉCURISÉ
# =============================================================================

def _get_db():
    """
    Récupère la base de données de manière sécurisée.
    
    Returns:
        ERPDatabase: Instance de la base ou None si non disponible
    """
    try:
        if hasattr(st.session_state, 'erp_db') and st.session_state.erp_db:
            return st.session_state.erp_db
        return None
    except Exception:
        return None


# =============================================================================
# FONCTIONS DE RÉCUPÉRATION DE DONNÉES ERP - VERSION SÉCURISÉE
# =============================================================================

def get_projets_actifs() -> List[Dict]:
    """
    Récupère la liste des projets actifs depuis la base ERP.
    
    Returns:
        List[Dict]: Liste des projets avec leurs informations principales
    """
    try:
        db = _get_db()
        if not db:
            return []
        
        query = """
            SELECT id, nom_projet, statut, prix_estime, client_company_id,
                   date_soumis, date_prevu, description
            FROM projects 
            WHERE statut NOT IN ('TERMINÉ', 'ANNULÉ', 'FERMÉ') 
            ORDER BY priorite DESC, date_soumis DESC
        """
        rows = db.execute_query(query)
        return [dict(row) for row in rows]
        
    except Exception as e:
        # Log silencieux - pas d'affichage d'erreur dans les utils
        return []


def get_employes_actifs() -> List[Dict]:
    """
    Récupère la liste des employés actifs depuis la base RH.
    
    Returns:
        List[Dict]: Liste des employés avec leurs informations
    """
    try:
        db = _get_db()
        if not db:
            return []
        
        query = """
            SELECT id, prenom, nom, poste, departement, email, telephone,
                   salaire, manager_id, charge_travail
            FROM employees 
            WHERE statut = 'ACTIF' 
            ORDER BY departement, prenom, nom
        """
        rows = db.execute_query(query)
        return [dict(row) for row in rows]
        
    except Exception:
        return []


def get_fournisseurs_actifs() -> List[Dict]:
    """
    Récupère la liste des fournisseurs actifs depuis le CRM.
    
    Returns:
        List[Dict]: Liste des fournisseurs avec leurs informations
    """
    try:
        db = _get_db()
        if not db:
            return []
        
        query = """
            SELECT c.id, c.nom, c.secteur, c.adresse, c.email, c.telephone, c.pays,
                   f.code_fournisseur, f.categorie_produits, f.delai_livraison_moyen,
                   f.evaluation_qualite, f.conditions_paiement
            FROM companies c
            LEFT JOIN fournisseurs f ON c.id = f.company_id
            WHERE c.secteur LIKE '%FOURNISSEUR%' 
               OR c.secteur LIKE '%DISTRIBUTION%' 
               OR c.secteur LIKE '%COMMERCE%'
               OR c.type_company = 'FOURNISSEUR'
               OR f.id IS NOT NULL
            ORDER BY c.nom
        """
        rows = db.execute_query(query)
        return [dict(row) for row in rows]
        
    except Exception:
        return []


def get_clients_actifs() -> List[Dict]:
    """
    Récupère la liste des clients depuis le CRM.
    
    Returns:
        List[Dict]: Liste des clients avec leurs informations
    """
    try:
        db = _get_db()
        if not db:
            return []
        
        query = """
            SELECT id, nom, secteur, adresse, email, telephone, pays,
                   site_web, contact_principal_id, type_company
            FROM companies 
            WHERE type_company IN ('CLIENT', 'PROSPECT') 
               OR secteur NOT LIKE '%FOURNISSEUR%'
               OR id IN (
                   SELECT DISTINCT client_company_id 
                   FROM projects 
                   WHERE client_company_id IS NOT NULL
               )
            ORDER BY nom
        """
        rows = db.execute_query(query)
        return [dict(row) for row in rows]
        
    except Exception:
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
        db = _get_db()
        if not db or not projet_id:
            return []
        
        query = """
            SELECT o.id, o.sequence_number as sequence, o.description, o.temps_estime,
                   o.work_center_id, o.statut, o.poste_travail, o.ressource,
                   wc.nom as work_center_nom, wc.cout_horaire
            FROM operations o
            LEFT JOIN work_centers wc ON o.work_center_id = wc.id
            WHERE o.project_id = ? 
            ORDER BY o.sequence_number
        """
        rows = db.execute_query(query, (projet_id,))
        return [dict(row) for row in rows]
        
    except Exception:
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
        db = _get_db()
        if not db or not projet_id:
            return []
        
        query = """
            SELECT id, code_materiau, designation as description, quantite, 
                   prix_unitaire, unite, fournisseur, statut
            FROM materials 
            WHERE project_id = ?
            ORDER BY designation
        """
        rows = db.execute_query(query, (projet_id,))
        return [dict(row) for row in rows]
        
    except Exception:
        return []


def get_work_centers_actifs() -> List[Dict]:
    """
    Récupère la liste des postes de travail actifs.
    
    Returns:
        List[Dict]: Liste des postes de travail
    """
    try:
        db = _get_db()
        if not db:
            return []
        
        query = """
            SELECT id, nom, departement, categorie, type_machine,
                   capacite_theorique, operateurs_requis, cout_horaire,
                   competences_requises, statut, localisation
            FROM work_centers 
            WHERE statut = 'ACTIF'
            ORDER BY departement, nom
        """
        rows = db.execute_query(query)
        return [dict(row) for row in rows]
        
    except Exception:
        return []


def get_articles_inventaire() -> List[Dict]:
    """
    Récupère tous les articles de l'inventaire.
    
    Returns:
        List[Dict]: Liste des articles avec stock
    """
    try:
        db = _get_db()
        if not db:
            return []
        
        query = """
            SELECT id, nom, type_produit, quantite_imperial, quantite_metric,
                   limite_minimale_imperial, limite_minimale_metric,
                   quantite_reservee_imperial, quantite_reservee_metric,
                   statut, description, fournisseur_principal, code_interne
            FROM inventory_items 
            ORDER BY nom
        """
        rows = db.execute_query(query)
        return [dict(row) for row in rows]
        
    except Exception:
        return []


def get_articles_inventaire_critique() -> List[Dict]:
    """
    Récupère les articles avec stock critique nécessitant réapprovisionnement.
    
    Returns:
        List[Dict]: Articles en stock critique
    """
    try:
        db = _get_db()
        if not db:
            return []
        
        query = """
            SELECT id, nom, type_produit, quantite_imperial, quantite_metric,
                   limite_minimale_imperial, limite_minimale_metric,
                   statut, fournisseur_principal
            FROM inventory_items 
            WHERE statut IN ('CRITIQUE', 'FAIBLE', 'ÉPUISÉ')
            ORDER BY 
                CASE statut 
                    WHEN 'ÉPUISÉ' THEN 1
                    WHEN 'CRITIQUE' THEN 2 
                    WHEN 'FAIBLE' THEN 3
                END, nom
        """
        rows = db.execute_query(query)
        return [dict(row) for row in rows]
        
    except Exception:
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
        db = _get_db()
        if not db or not search_term or len(search_term) < 2:
            return []
        
        query = """
            SELECT id, nom, type_produit, quantite_imperial, quantite_metric,
                   statut, fournisseur_principal, code_interne
            FROM inventory_items 
            WHERE LOWER(nom) LIKE LOWER(?) 
               OR LOWER(type_produit) LIKE LOWER(?)
               OR LOWER(code_interne) LIKE LOWER(?)
               OR LOWER(description) LIKE LOWER(?)
            ORDER BY nom
            LIMIT 20
        """
        search_pattern = f"%{search_term}%"
        rows = db.execute_query(query, (search_pattern, search_pattern, search_pattern, search_pattern))
        return [dict(row) for row in rows]
        
    except Exception:
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
        db = _get_db()
        if not db or not client_id:
            return []
        
        query = """
            SELECT id, nom_projet, statut, priorite, prix_estime, 
                   date_soumis, date_prevu, description
            FROM projects 
            WHERE client_company_id = ? 
            ORDER BY date_soumis DESC
        """
        rows = db.execute_query(query, (client_id,))
        return [dict(row) for row in rows]
        
    except Exception:
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
        db = _get_db()
        if not db or not work_center_id:
            return None
        
        query = """
            SELECT id, nom, departement, categorie, type_machine,
                   capacite_theorique, operateurs_requis, cout_horaire,
                   competences_requises, statut, localisation
            FROM work_centers 
            WHERE id = ?
        """
        rows = db.execute_query(query, (work_center_id,))
        return dict(rows[0]) if rows else None
        
    except Exception:
        return None


# =============================================================================
# FONCTIONS UTILITAIRES CALCULÉES - VERSION COMPLÈTE
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
        statut = article.get('statut', 'NORMAL').upper()
        type_produit = article.get('type_produit', '').upper()
        
        # Logique basée sur le statut et le type
        if 'ÉPUISÉ' in statut:
            base_qty = 50
        elif 'CRITIQUE' in statut:
            base_qty = 30
        elif 'FAIBLE' in statut:
            base_qty = 20
        else:
            base_qty = 10
        
        # Ajustement selon le type de produit
        if 'QUINCAILLERIE' in type_produit or 'ACCESSOIRES' in type_produit:
            base_qty *= 2  # Plus de petites pièces
        elif 'BOIS' in type_produit or 'MÉTAL' in type_produit:
            base_qty = max(base_qty, 15)  # Minimum pour matières premières
        
        return base_qty
        
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
        fournisseur_id = str(fournisseur.get('id', 1))
        hash_val = int(hashlib.md5(fournisseur_id.encode()).hexdigest()[:8], 16)
        
        # Note de base entre 6 et 10 (fournisseurs présélectionnés)
        note_base = (hash_val % 5) + 6
        
        # Ajustements selon l'évaluation qualité existante si disponible
        if 'evaluation_qualite' in fournisseur and fournisseur['evaluation_qualite']:
            note_base = max(note_base, int(fournisseur['evaluation_qualite']))
        
        return min(note_base, 10)
        
    except Exception:
        return 7


def generer_offres_fictives_rfq(dp_details: Dict, fournisseurs: List[Dict]) -> List[Dict]:
    """
    Génère des offres fictives pour une RFQ (pour la démo).
    
    Args:
        dp_details: Détails de la demande de prix
        fournisseurs: Liste des fournisseurs invités
        
    Returns:
        List[Dict]: Offres fictives générées
    """
    try:
        if not fournisseurs:
            return []
        
        offres = []
        
        # Prix de base estimé selon le type de demande
        montant_estime = dp_details.get('montant_total', 0)
        if montant_estime > 0:
            base_price = montant_estime
        else:
            # Estimation basée sur le nombre de lignes
            nb_lignes = len(dp_details.get('lignes', []))
            base_price = random.uniform(5000, 50000) * max(nb_lignes, 1)
        
        for i, fournisseur in enumerate(fournisseurs):
            note_qualite = get_note_fournisseur_fictive(fournisseur)
            
            # Variation de prix selon la "qualité" du fournisseur
            # Meilleure qualité = prix plus élevé mais plus fiable
            price_factor = 0.9 + (note_qualite / 10) * 0.3
            
            # Variation aléatoire ±15%
            random_factor = random.uniform(0.85, 1.15)
            prix_final = base_price * price_factor * random_factor
            
            # Délai basé sur la complexité et la capacité du fournisseur
            delai_base = random.randint(7, 30)
            if note_qualite >= 8:
                delai_base = int(delai_base * 0.8)  # Fournisseurs premium plus rapides
            
            # Conformité basée sur la qualité
            conforme = note_qualite >= 7 or random.random() > 0.3
            
            offre = {
                'fournisseur': fournisseur,
                'prix_total': round(prix_final, 2),
                'delai_livraison': delai_base,
                'note_qualite': note_qualite,
                'proximite_km': random.randint(10, 500),
                'experience_secteur': min(note_qualite + random.randint(-2, 2), 10),
                'conforme': conforme,
                'conditions_paiement': random.choice(['30j net', '45j net', '15j net', 'À réception']),
                'garantie': random.choice(['12 mois', '24 mois', '6 mois', '18 mois']),
                'certifications': random.choice(['ISO 9001', 'ISO 14001', 'AS9100', 'Standard']),
                'notes': f"Offre {['économique', 'standard', 'premium'][min(int(note_qualite/3), 2)]} de {fournisseur.get('nom', 'Fournisseur')}",
                'score_final': 0  # Sera calculé selon les critères de la DP
            }
            
            offres.append(offre)
        
        return offres
        
    except Exception:
        return []


# =============================================================================
# FONCTIONS DE FORMATAGE ET AFFICHAGE - VERSION COMPLÈTE
# =============================================================================

def formater_montant(montant: float, devise: str = "CAD") -> str:
    """
    Formate un montant pour l'affichage avec gestion des devises.
    
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
    except Exception:
        return f"0,00$ {devise}"


def formater_delai(jours: int) -> str:
    """
    Formate un délai en jours pour l'affichage lisible.
    
    Args:
        jours: Nombre de jours
        
    Returns:
        str: Délai formaté
    """
    try:
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
        elif jours < 365:
            mois = jours // 30
            jours_restants = jours % 30
            if jours_restants == 0:
                return f"{mois} mois"
            else:
                return f"{mois}m {jours_restants}j"
        else:
            annees = jours // 365
            return f"{annees} an{'s' if annees > 1 else ''}"
    except Exception:
        return "N/A"


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
        
        # Gestion des différents formats de date
        try:
            if 'T' in date_validite:
                date_val = datetime.fromisoformat(date_validite.replace('T', ' ').split('.')[0]).date()
            else:
                date_val = datetime.strptime(date_validite, '%Y-%m-%d').date()
        except ValueError:
            try:
                date_val = datetime.strptime(date_validite, '%d/%m/%Y').date()
            except ValueError:
                return "error", "Format date invalide"
        
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
        'BROUILLON': '#f59e0b',    # Orange - En cours
        'VALIDÉ': '#3b82f6',       # Bleu - Prêt
        'ENVOYÉ': '#8b5cf6',       # Violet - En transit
        'APPROUVÉ': '#10b981',     # Vert - Accepté
        'TERMINÉ': '#059669',      # Vert foncé - Complété
        'ANNULÉ': '#ef4444',       # Rouge - Annulé
        'EN_ATTENTE': '#f59e0b',   # Orange - En attente
        'REJETÉ': '#dc2626'        # Rouge foncé - Rejeté
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
        'NORMAL': '#10b981',   # Vert - Normal
        'URGENT': '#f59e0b',   # Orange - Urgent
        'CRITIQUE': '#ef4444', # Rouge - Critique
        'BAS': '#6b7280',      # Gris - Basse priorité
        'ÉLEVÉ': '#dc2626'     # Rouge foncé - Très élevé
    }
    
    return couleurs.get(priorite, '#6b7280')


# =============================================================================
# FONCTIONS DE VALIDATION MÉTIER - VERSION COMPLÈTE
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
    try:
        if not date_debut or not date_fin:
            return True, ""  # OK si dates manquantes
        
        ecart_reel = (date_fin - date_debut).days
        
        # Tolérance de ±20%
        tolerance = max(delai_estimation * 0.2, 2)  # Minimum 2 jours de tolérance
        
        if abs(ecart_reel - delai_estimation) > tolerance:
            return False, f"Incohérence: écart réel {ecart_reel}j vs estimé {delai_estimation}j (±{tolerance:.0f}j tolérance)"
        
        return True, ""
        
    except Exception:
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
    try:
        if budget_projet <= 0 or montant_estimation <= 0:
            return True, ""  # OK si montants non définis
        
        ecart_pct = abs(budget_projet - montant_estimation) / montant_estimation * 100
        
        # Alerte si écart > 15%
        if ecart_pct > 15:
            sens = "supérieur" if budget_projet > montant_estimation else "inférieur"
            return False, f"Budget {sens} à l'estimation de {ecart_pct:.1f}% (seuil: 15%)"
        elif ecart_pct > 10:
            return True, f"Écart acceptable: {ecart_pct:.1f}% entre budget et estimation"
        
        return True, ""
        
    except Exception:
        return True, ""


def calculer_taux_marge_realiste(cout_materiau: float, cout_main_oeuvre: float, 
                                prix_vente: float) -> Tuple[float, str]:
    """
    Calcule le taux de marge et vérifie s'il est réaliste pour l'industrie.
    
    Args:
        cout_materiau: Coût des matériaux
        cout_main_oeuvre: Coût de la main d'œuvre
        prix_vente: Prix de vente proposé
        
    Returns:
        Tuple[float, str]: (taux_marge, evaluation)
    """
    try:
        cout_total = cout_materiau + cout_main_oeuvre
        
        if cout_total <= 0:
            return 0.0, "Coûts non définis"
        
        if prix_vente <= 0:
            return 0.0, "Prix de vente non défini"
        
        marge = prix_vente - cout_total
        taux_marge = (marge / cout_total) * 100
        
        # Évaluation selon les standards de l'industrie métallurgique
        if taux_marge < 0:
            evaluation = "⚠️ PERTE - Prix inférieur aux coûts"
        elif taux_marge < 5:
            evaluation = "🔴 Marge très faible - Risqué"
        elif taux_marge < 10:
            evaluation = "🟡 Marge faible - Surveiller"
        elif taux_marge < 20:
            evaluation = "🟢 Marge acceptable - Standard industrie"
        elif taux_marge < 35:
            evaluation = "✅ Bonne marge - Rentable"
        elif taux_marge < 50:
            evaluation = "💰 Excellente marge - Très rentable"
        else:
            evaluation = "⚠️ Marge très élevée - Vérifier compétitivité"
        
        return taux_marge, evaluation
        
    except Exception:
        return 0.0, "Erreur calcul marge"


def calculer_score_fournisseur_rfq(offre: Dict, criteres: Dict) -> float:
    """
    Calcule le score d'une offre selon les critères de la RFQ.
    
    Args:
        offre: Données de l'offre fournisseur
        criteres: Critères d'évaluation avec pondérations
        
    Returns:
        float: Score final sur 100
    """
    try:
        score_total = 0.0
        ponderation_totale = 0.0
        
        for critere, config in criteres.items():
            if not config.get('actif', False):
                continue
                
            ponderation = config.get('ponderation', 0) / 100.0
            ponderation_totale += ponderation
            
            # Calcul du score selon le type de critère
            if critere == 'prix':
                # Score inversé pour le prix (moins cher = meilleur score)
                prix_offre = offre.get('prix_total', float('inf'))
                if prix_offre > 0:
                    # Normalisation relative (à implémenter selon les autres offres)
                    score_critere = min(100, 10000 / prix_offre)  # Formule simplifiée
                else:
                    score_critere = 0
                    
            elif critere == 'delai':
                # Score inversé pour le délai (plus rapide = meilleur score)
                delai = offre.get('delai_livraison', 999)
                score_critere = max(0, 100 - (delai - 7) * 2)  # 7j = 100pts, chaque jour = -2pts
                
            elif critere == 'qualite':
                # Score direct sur la note qualité
                note_qualite = offre.get('note_qualite', 5)
                score_critere = (note_qualite / 10) * 100
                
            elif critere == 'proximite':
                # Score inversé pour la distance
                distance = offre.get('proximite_km', 1000)
                score_critere = max(0, 100 - (distance / 10))  # 0km = 100pts, chaque 10km = -1pt
                
            elif critere == 'experience':
                # Score direct sur l'expérience
                experience = offre.get('experience_secteur', 5)
                score_critere = (experience / 10) * 100
                
            elif critere == 'conformite':
                # Score binaire sur la conformité
                conforme = offre.get('conforme', False)
                score_critere = 100 if conforme else 0
                
            else:
                score_critere = 50  # Score neutre pour critères non reconnus
            
            score_total += score_critere * ponderation
        
        # Normalisation finale
        if ponderation_totale > 0:
            score_final = score_total / ponderation_totale
        else:
            score_final = 0
        
        return round(min(100, max(0, score_final)), 1)
        
    except Exception:
        return 0.0


def generer_recommendations_approvisionnement(articles_critiques: List[Dict]) -> Dict[str, Any]:
    """
    Génère des recommandations d'approvisionnement basées sur les stocks critiques.
    
    Args:
        articles_critiques: Liste des articles en stock critique
        
    Returns:
        Dict: Recommandations structurées
    """
    try:
        if not articles_critiques:
            return {
                'priorite': 'NORMALE',
                'message': 'Tous les stocks sont à niveau acceptable',
                'actions': [],
                'budget_estime': 0
            }
        
        # Analyse par priorité
        epuises = [a for a in articles_critiques if a.get('statut') == 'ÉPUISÉ']
        critiques = [a for a in articles_critiques if a.get('statut') == 'CRITIQUE']
        faibles = [a for a in articles_critiques if a.get('statut') == 'FAIBLE']
        
        # Détermination de la priorité globale
        if epuises:
            priorite = 'CRITIQUE'
            message = f"{len(epuises)} article(s) épuisé(s) - Action immédiate requise"
        elif critiques:
            priorite = 'URGENT'
            message = f"{len(critiques)} article(s) en stock critique - Réapprovisionner rapidement"
        else:
            priorite = 'NORMAL'
            message = f"{len(faibles)} article(s) en stock faible - Planifier réapprovisionnement"
        
        # Génération des actions recommandées
        actions = []
        budget_total = 0
        
        for article in articles_critiques:
            qty_recommandee = calculer_quantite_recommandee(article)
            # Prix estimé (simulation)
            prix_estime = random.uniform(10, 500) * qty_recommandee
            budget_total += prix_estime
            
            action = {
                'article': article.get('nom'),
                'statut_actuel': article.get('statut'),
                'quantite_recommandee': qty_recommandee,
                'fournisseur_suggere': article.get('fournisseur_principal', 'À déterminer'),
                'budget_estime': prix_estime,
                'urgence': 'IMMÉDIATE' if article.get('statut') == 'ÉPUISÉ' else 'NORMALE'
            }
            actions.append(action)
        
        return {
            'priorite': priorite,
            'message': message,
            'actions': sorted(actions, key=lambda x: x['urgence'] == 'IMMÉDIATE', reverse=True),
            'budget_estime': budget_total,
            'nb_articles_concernes': len(articles_critiques),
            'delai_recommande': 7 if priorite == 'CRITIQUE' else 14
        }
        
    except Exception:
        return {
            'priorite': 'ERREUR',
            'message': 'Erreur lors de l\'analyse des stocks',
            'actions': [],
            'budget_estime': 0
        }


# =============================================================================
# FONCTIONS UTILITAIRES SPÉCIALISÉES - EXTENSION
# =============================================================================

def detecter_anomalies_prix(prix_propose: float, prix_references: List[float]) -> Tuple[bool, str]:
    """
    Détecte les anomalies de prix par rapport à des références.
    
    Args:
        prix_propose: Prix proposé à vérifier
        prix_references: Liste des prix de référence
        
    Returns:
        Tuple[bool, str]: (anomalie_detectee, message)
    """
    try:
        if not prix_references or prix_propose <= 0:
            return False, ""
        
        prix_ref_moyens = [p for p in prix_references if p > 0]
        if not prix_ref_moyens:
            return False, ""
        
        prix_moyen = sum(prix_ref_moyens) / len(prix_ref_moyens)
        ecart_pct = abs(prix_propose - prix_moyen) / prix_moyen * 100
        
        if ecart_pct > 50:
            sens = "supérieur" if prix_propose > prix_moyen else "inférieur"
            return True, f"Prix {sens} de {ecart_pct:.0f}% à la moyenne du marché"
        elif ecart_pct > 25:
            sens = "supérieur" if prix_propose > prix_moyen else "inférieur"
            return True, f"Prix {sens} de {ecart_pct:.0f}% à la moyenne (attention)"
        
        return False, ""
        
    except Exception:
        return False, ""


def calculer_impact_delai_projet(delai_fournisseur: int, date_besoin_projet: str) -> Dict[str, Any]:
    """
    Calcule l'impact d'un délai fournisseur sur un projet.
    
    Args:
        delai_fournisseur: Délai annoncé par le fournisseur (jours)
        date_besoin_projet: Date de besoin pour le projet
        
    Returns:
        Dict: Analyse de l'impact sur le planning
    """
    try:
        if not date_besoin_projet:
            return {'impact': 'INCONNU', 'message': 'Date de besoin non définie'}
        
        # Conversion de la date
        try:
            date_besoin = datetime.strptime(date_besoin_projet, '%Y-%m-%d').date()
        except ValueError:
            try:
                date_besoin = datetime.strptime(date_besoin_projet, '%d/%m/%Y').date()
            except ValueError:
                return {'impact': 'ERREUR', 'message': 'Format de date invalide'}
        
        date_livraison_prevue = datetime.now().date() + timedelta(days=delai_fournisseur)
        ecart_jours = (date_livraison_prevue - date_besoin).days
        
        if ecart_jours <= 0:
            impact = 'POSITIF'
            message = f"Livraison {abs(ecart_jours)} jour(s) avant le besoin"
        elif ecart_jours <= 3:
            impact = 'NEUTRE'
            message = f"Livraison {ecart_jours} jour(s) après le besoin (acceptable)"
        elif ecart_jours <= 7:
            impact = 'ATTENTION'
            message = f"Retard de {ecart_jours} jours - Impact mineur sur le projet"
        else:
            impact = 'CRITIQUE'
            message = f"Retard de {ecart_jours} jours - Impact majeur sur le planning"
        
        return {
            'impact': impact,
            'message': message,
            'ecart_jours': ecart_jours,
            'date_livraison_prevue': date_livraison_prevue.strftime('%d/%m/%Y'),
            'recommandation': _generer_recommandation_delai(impact, ecart_jours)
        }
        
    except Exception:
        return {'impact': 'ERREUR', 'message': 'Erreur de calcul'}


def _generer_recommandation_delai(impact: str, ecart_jours: int) -> str:
    """Génère une recommandation basée sur l'impact délai."""
    recommendations = {
        'POSITIF': "Délai acceptable - Valider la commande",
        'NEUTRE': "Délai acceptable avec marge réduite",
        'ATTENTION': "Négocier une livraison express ou chercher un fournisseur plus rapide",
        'CRITIQUE': "Chercher un fournisseur alternatif ou revoir le planning projet"
    }
    return recommendations.get(impact, "Analyser l'impact sur le projet")
