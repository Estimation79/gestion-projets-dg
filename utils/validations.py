# formulaires/utils/validations.py
# Fonctions de validation communes à tous les formulaires

"""
Fonctions de validation pour les formulaires.
Contient les validations de base et spécifiques à chaque type de formulaire.
"""

import streamlit as st
from datetime import datetime, date
from typing import Dict, List, Tuple, Any
import re

from ..core.types_formulaires import (
    valider_type_formulaire,
    valider_statut,
    valider_priorite,
    UNITES_MESURE,
    DEVISES
)


def valider_formulaire_base(data: dict) -> Tuple[bool, List[str]]:
    """
    Validation de base pour tous les formulaires.
    
    Args:
        data: Données du formulaire à valider
        
    Returns:
        Tuple[bool, List[str]]: (est_valide, liste_erreurs)
    """
    erreurs = []
    
    # Champs obligatoires de base
    if not data.get('employee_id'):
        erreurs.append("Responsable obligatoire")
    
    if not data.get('type_formulaire'):
        erreurs.append("Type de formulaire obligatoire")
    elif not valider_type_formulaire(data['type_formulaire']):
        erreurs.append("Type de formulaire invalide")
    
    # Validation des énumérations
    if data.get('statut') and not valider_statut(data['statut']):
        erreurs.append(f"Statut invalide: {data['statut']}")
    
    if data.get('priorite') and not valider_priorite(data['priorite']):
        erreurs.append(f"Priorité invalide: {data['priorite']}")
    
    # Validation des montants
    if data.get('montant_total') is not None:
        try:
            montant = float(data['montant_total'])
            if montant < 0:
                erreurs.append("Le montant ne peut pas être négatif")
        except (ValueError, TypeError):
            erreurs.append("Montant invalide")
    
    # Validation des dates
    if data.get('date_echeance'):
        if not valider_date(data['date_echeance']):
            erreurs.append("Date d'échéance invalide")
    
    return len(erreurs) == 0, erreurs


def valider_bon_travail(data: dict) -> Tuple[bool, List[str]]:
    """
    Validation spécifique aux Bons de Travail.
    
    Args:
        data: Données du bon de travail
        
    Returns:
        Tuple[bool, List[str]]: (est_valide, liste_erreurs)
    """
    is_valid, erreurs = valider_formulaire_base(data)
    
    # Projet obligatoire pour BT
    if not data.get('project_id'):
        erreurs.append("Projet obligatoire pour les Bons de Travail")
    
    # Description obligatoire
    if not data.get('description') and not data.get('notes'):
        erreurs.append("Description du travail obligatoire")
    
    # Validation des lignes (matériaux/opérations)
    if data.get('lignes'):
        lignes_valides, erreurs_lignes = valider_lignes_formulaire(data['lignes'])
        if not lignes_valides:
            erreurs.extend([f"Ligne {i+1}: {err}" for i, err in enumerate(erreurs_lignes)])
    
    return len(erreurs) == 0, erreurs


def valider_bon_achat(data: dict) -> Tuple[bool, List[str]]:
    """
    Validation spécifique aux Bons d'Achats.
    
    Args:
        data: Données du bon d'achat
        
    Returns:
        Tuple[bool, List[str]]: (est_valide, liste_erreurs)
    """
    is_valid, erreurs = valider_formulaire_base(data)
    
    # Fournisseur obligatoire pour BA
    if not data.get('company_id'):
        erreurs.append("Fournisseur obligatoire pour les Bons d'Achats")
    
    # Justification obligatoire
    if not data.get('justification') and 'justification' not in data.get('notes', '').lower():
        erreurs.append("Justification de l'achat obligatoire")
    
    # Au moins un article
    if not data.get('lignes') or len(data['lignes']) == 0:
        erreurs.append("Au moins un article doit être commandé")
    else:
        lignes_valides, erreurs_lignes = valider_lignes_formulaire(data['lignes'])
        if not lignes_valides:
            erreurs.extend([f"Article {i+1}: {err}" for i, err in enumerate(erreurs_lignes)])
    
    return len(erreurs) == 0, erreurs


def valider_bon_commande(data: dict) -> Tuple[bool, List[str]]:
    """
    Validation spécifique aux Bons de Commande.
    
    Args:
        data: Données du bon de commande
        
    Returns:
        Tuple[bool, List[str]]: (est_valide, liste_erreurs)
    """
    is_valid, erreurs = valider_formulaire_base(data)
    
    # Fournisseur obligatoire
    if not data.get('company_id'):
        erreurs.append("Fournisseur obligatoire pour les Bons de Commande")
    
    # Conditions commerciales obligatoires
    try:
        metadonnees = data.get('metadonnees_json', '{}')
        if isinstance(metadonnees, str):
            import json
            metadonnees = json.loads(metadonnees)
        
        if not metadonnees.get('conditions_paiement'):
            erreurs.append("Conditions de paiement obligatoires")
        
        if not metadonnees.get('adresse_livraison'):
            erreurs.append("Adresse de livraison obligatoire")
            
    except (json.JSONDecodeError, AttributeError):
        erreurs.append("Métadonnées du BC malformées")
    
    # Articles avec prix définis
    if not data.get('lignes'):
        erreurs.append("Articles obligatoires pour BC")
    else:
        for i, ligne in enumerate(data['lignes']):
            if not ligne.get('prix_unitaire') or ligne['prix_unitaire'] <= 0:
                erreurs.append(f"Article {i+1}: Prix unitaire obligatoire et > 0")
    
    return len(erreurs) == 0, erreurs


def valider_demande_prix(data: dict) -> Tuple[bool, List[str]]:
    """
    Validation spécifique aux Demandes de Prix (RFQ).
    
    Args:
        data: Données de la demande de prix
        
    Returns:
        Tuple[bool, List[str]]: (est_valide, liste_erreurs)
    """
    is_valid, erreurs = valider_formulaire_base(data)
    
    # Validation des métadonnées RFQ
    try:
        metadonnees = data.get('metadonnees_json', '{}')
        if isinstance(metadonnees, str):
            import json
            metadonnees = json.loads(metadonnees)
        
        # Fournisseurs invités obligatoires
        fournisseurs_invites = metadonnees.get('fournisseurs_invites', [])
        if not fournisseurs_invites or len(fournisseurs_invites) < 2:
            erreurs.append("Au moins 2 fournisseurs doivent être invités")
        
        # Critères d'évaluation obligatoires
        criteres = metadonnees.get('criteres_evaluation', {})
        if not criteres:
            erreurs.append("Critères d'évaluation obligatoires")
        else:
            # Vérifier que les pondérations totalisent 100%
            total_ponderation = sum(
                critere.get('ponderation', 0) 
                for critere in criteres.values() 
                if critere.get('actif', False)
            )
            if abs(total_ponderation - 100) > 0.1:  # Tolérance pour les arrondis
                erreurs.append(f"Pondérations doivent totaliser 100% (actuellement: {total_ponderation}%)")
        
        # Délai de réponse raisonnable
        delai_reponse = metadonnees.get('delai_reponse', 0)
        if delai_reponse < 3 or delai_reponse > 90:
            erreurs.append("Délai de réponse doit être entre 3 et 90 jours")
            
    except (json.JSONDecodeError, AttributeError):
        erreurs.append("Métadonnées RFQ malformées")
    
    # Objet et description obligatoires
    if not data.get('notes') or len(data['notes']) < 50:
        erreurs.append("Description détaillée obligatoire (minimum 50 caractères)")
    
    return len(erreurs) == 0, erreurs


def valider_estimation(data: dict) -> Tuple[bool, List[str]]:
    """
    Validation spécifique aux Estimations.
    
    Args:
        data: Données de l'estimation
        
    Returns:
        Tuple[bool, List[str]]: (est_valide, liste_erreurs)
    """
    is_valid, erreurs = valider_formulaire_base(data)
    
    # Client obligatoire
    if not data.get('company_id'):
        erreurs.append("Client obligatoire pour les Estimations")
    
    # Montant obligatoire et positif
    if not data.get('montant_total') or data['montant_total'] <= 0:
        erreurs.append("Montant de l'estimation doit être > 0")
    
    # Validation des métadonnées estimation
    try:
        metadonnees = data.get('metadonnees_json', '{}')
        if isinstance(metadonnees, str):
            import json
            metadonnees = json.loads(metadonnees)
        
        # Template industrie obligatoire
        if not metadonnees.get('template_industrie'):
            erreurs.append("Template industrie obligatoire")
        
        # Marge bénéficiaire raisonnable
        marge = metadonnees.get('marge_beneficiaire', 0)
        if marge < 5 or marge > 100:
            erreurs.append("Marge bénéficiaire doit être entre 5% et 100%")
        
        # Validité de l'offre
        validite = metadonnees.get('validite_devis', 0)
        if validite < 15 or validite > 365:
            erreurs.append("Validité devis doit être entre 15 et 365 jours")
            
    except (json.JSONDecodeError, AttributeError):
        erreurs.append("Métadonnées estimation malformées")
    
    # Articles ou base projet obligatoire
    if not data.get('lignes') and not data.get('project_id'):
        erreurs.append("Articles détaillés ou projet de base obligatoire")
    
    return len(erreurs) == 0, erreurs


def valider_lignes_formulaire(lignes: List[Dict]) -> Tuple[bool, List[str]]:
    """
    Valide les lignes de détail d'un formulaire.
    
    Args:
        lignes: Liste des lignes à valider
        
    Returns:
        Tuple[bool, List[str]]: (sont_valides, liste_erreurs)
    """
    erreurs = []
    
    for i, ligne in enumerate(lignes):
        # Description obligatoire
        if not ligne.get('description') or ligne['description'].strip() == '':
            erreurs.append(f"Ligne {i+1}: Description obligatoire")
        
        # Quantité positive
        try:
            quantite = float(ligne.get('quantite', 0))
            if quantite <= 0:
                erreurs.append(f"Ligne {i+1}: Quantité doit être > 0")
        except (ValueError, TypeError):
            erreurs.append(f"Ligne {i+1}: Quantité invalide")
        
        # Unité valide
        unite = ligne.get('unite')
        if unite and unite not in UNITES_MESURE:
            erreurs.append(f"Ligne {i+1}: Unité '{unite}' non reconnue")
        
        # Prix unitaire si spécifié
        if ligne.get('prix_unitaire') is not None:
            try:
                prix = float(ligne['prix_unitaire'])
                if prix < 0:
                    erreurs.append(f"Ligne {i+1}: Prix unitaire ne peut pas être négatif")
            except (ValueError, TypeError):
                erreurs.append(f"Ligne {i+1}: Prix unitaire invalide")
    
    return len(erreurs) == 0, erreurs


def valider_date(date_value: Any) -> bool:
    """
    Valide qu'une valeur est une date valide.
    
    Args:
        date_value: Valeur à valider
        
    Returns:
        bool: True si valide, False sinon
    """
    if date_value is None:
        return True  # Date optionnelle
    
    # Si c'est déjà un objet date/datetime
    if isinstance(date_value, (date, datetime)):
        return True
    
    # Si c'est une chaîne, essayer de la parser
    if isinstance(date_value, str):
        try:
            datetime.strptime(date_value, '%Y-%m-%d')
            return True
        except ValueError:
            try:
                datetime.strptime(date_value, '%d/%m/%Y')
                return True
            except ValueError:
                return False
    
    return False


def valider_email(email: str) -> bool:
    """
    Valide un format d'email.
    
    Args:
        email: Email à valider
        
    Returns:
        bool: True si valide, False sinon
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def valider_telephone(telephone: str) -> bool:
    """
    Valide un numéro de téléphone canadien.
    
    Args:
        telephone: Numéro à valider
        
    Returns:
        bool: True si valide, False sinon
    """
    if not telephone:
        return False
    
    # Nettoyer le numéro
    numero_nettoye = re.sub(r'[^\d]', '', telephone)
    
    # Format canadien: 10 chiffres
    return len(numero_nettoye) == 10


def valider_code_postal_canadien(code_postal: str) -> bool:
    """
    Valide un code postal canadien.
    
    Args:
        code_postal: Code postal à valider
        
    Returns:
        bool: True si valide, False sinon
    """
    if not code_postal:
        return False
    
    # Format canadien: A1A 1A1
    pattern = r'^[A-Za-z]\d[A-Za-z] ?\d[A-Za-z]\d$'
    return re.match(pattern, code_postal.strip()) is not None


def valider_montant_devise(montant: float, devise: str) -> Tuple[bool, str]:
    """
    Valide un montant dans une devise donnée.
    
    Args:
        montant: Montant à valider
        devise: Devise (CAD, USD, EUR)
        
    Returns:
        Tuple[bool, str]: (est_valide, message_erreur)
    """
    if montant < 0:
        return False, "Le montant ne peut pas être négatif"
    
    if devise not in DEVISES:
        return False, f"Devise '{devise}' non supportée"
    
    # Limites raisonnables par devise
    limites = {
        'CAD': 10_000_000,  # 10M CAD
        'USD': 8_000_000,   # 8M USD  
        'EUR': 7_000_000    # 7M EUR
    }
    
    if montant > limites.get(devise, 1_000_000):
        return False, f"Montant trop élevé pour {devise}"
    
    return True, ""


def valider_coherence_dates(date_debut: date, date_fin: date) -> Tuple[bool, str]:
    """
    Valide la cohérence entre deux dates.
    
    Args:
        date_debut: Date de début
        date_fin: Date de fin
        
    Returns:
        Tuple[bool, str]: (coherentes, message_erreur)
    """
    if date_debut and date_fin:
        if date_fin < date_debut:
            return False, "La date de fin ne peut pas être antérieure à la date de début"
        
        # Vérifier que l'écart n'est pas déraisonnable (ex: > 5 ans)
        ecart = (date_fin - date_debut).days
        if ecart > 1825:  # 5 ans
            return False, "L'écart entre les dates semble déraisonnable (> 5 ans)"
    
    return True, ""
