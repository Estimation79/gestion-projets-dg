# formulaires/core/types_formulaires.py
# Constantes et types de formulaires - Base de l'architecture modulaire

"""
Constantes et énumérations pour le module formulaires.
Ce fichier contient tous les types, statuts et priorités utilisés 
dans l'ensemble du système de gestion des formulaires.
"""

# Types de formulaires avec leurs configurations
TYPES_FORMULAIRES = {
    'BON_TRAVAIL': {
        'prefix': 'BT', 
        'nom': 'Bon de Travail', 
        'icon': '🔧',
        'description': 'Documents de travail interne - Production et maintenance'
    },
    'BON_ACHAT': {
        'prefix': 'BA', 
        'nom': "Bon d'Achats", 
        'icon': '🛒',
        'description': 'Demandes d\'achats - Approvisionnement matériaux'
    },
    'BON_COMMANDE': {
        'prefix': 'BC', 
        'nom': 'Bon de Commande', 
        'icon': '📦',
        'description': 'Commandes officielles fournisseurs - Contrats d\'achat'
    },
    'DEMANDE_PRIX': {
        'prefix': 'DP', 
        'nom': 'Demande de Prix', 
        'icon': '💰',
        'description': 'RFQ Multi-fournisseurs - Appels d\'offres'
    },
    'ESTIMATION': {
        'prefix': 'EST', 
        'nom': 'Estimation', 
        'icon': '📊',
        'description': 'Devis clients - Estimations projets'
    }
}

# Statuts possibles pour tous les formulaires
STATUTS_FORMULAIRES = [
    'BROUILLON',    # Document en cours de création
    'VALIDÉ',       # Document validé mais pas encore envoyé
    'ENVOYÉ',       # Document envoyé (fournisseur/client/équipe)
    'APPROUVÉ',     # Document approuvé par le destinataire
    'TERMINÉ',      # Document complètement traité
    'ANNULÉ'        # Document annulé
]

# Priorités applicables aux formulaires
PRIORITES_FORMULAIRES = [
    'NORMAL',       # Priorité standard
    'URGENT',       # Traitement prioritaire
    'CRITIQUE'      # Traitement immédiat requis
]

# Configuration des icônes par statut (pour l'affichage)
ICONES_STATUTS = {
    'BROUILLON': '📝',
    'VALIDÉ': '✅', 
    'ENVOYÉ': '📤',
    'APPROUVÉ': '👍',
    'TERMINÉ': '✔️',
    'ANNULÉ': '❌'
}

# Configuration des icônes par priorité
ICONES_PRIORITES = {
    'NORMAL': '🟢',
    'URGENT': '🟡', 
    'CRITIQUE': '🔴'
}

# Templates industrie pour les estimations
TEMPLATES_INDUSTRIE = {
    'AUTOMOBILE': {
        'marge_defaut': 15,
        'delai_standard': 21,
        'coefficient_complexite': 1.2,
        'cout_certification_pct': 5,
        'garantie': '12 mois pièces et main d\'œuvre',
        'conditions_paiement': '30 jours net'
    },
    'AERONAUTIQUE': {
        'marge_defaut': 25,
        'delai_standard': 45,
        'coefficient_complexite': 1.5,
        'cout_certification_pct': 15,
        'garantie': '24 mois certification aéro',
        'conditions_paiement': '50% avance + 50% livraison'
    },
    'CONSTRUCTION': {
        'marge_defaut': 12,
        'delai_standard': 14,
        'coefficient_complexite': 1.1,
        'cout_certification_pct': 2,
        'garantie': '12 mois installation',
        'conditions_paiement': '30 jours net'
    },
    'GENERAL': {
        'marge_defaut': 20,
        'delai_standard': 21,
        'coefficient_complexite': 1.0,
        'cout_certification_pct': 0,
        'garantie': '12 mois standard',
        'conditions_paiement': '30 jours net'
    }
}

# Unités de mesure communes
UNITES_MESURE = [
    'UN',      # Unité
    'KG',      # Kilogramme
    'M',       # Mètre
    'M²',      # Mètre carré
    'M³',      # Mètre cube
    'L',       # Litre
    'T',       # Tonne
    'H',       # Heure
    'J',       # Jour
    'BOÎTE',   # Boîte
    'SAC',     # Sac
    'SERVICE', # Service
    'FORFAIT'  # Forfait
]

# Types de validation possibles
TYPES_VALIDATION = [
    'CREATION',              # Création du document
    'CHANGEMENT_STATUT',     # Modification du statut
    'MODIFICATION',          # Modification du contenu
    'RECEPTION_MARCHANDISES', # Réception (BC)
    'SELECTION_GAGNANT',     # Sélection fournisseur (DP)
    'CONVERSION',            # Conversion d'un type vers un autre
    'APPROBATION',           # Approbation hiérarchique
    'REJET'                  # Rejet du document
]

# Devises supportées
DEVISES = ['CAD', 'USD', 'EUR']

# Conditions de paiement standards
CONDITIONS_PAIEMENT = [
    '15 jours net',
    '30 jours net', 
    '45 jours net',
    '60 jours net',
    'À réception',
    'Comptant',
    'Virement immédiat',
    '50% avance + 50% livraison'
]

def get_type_formulaire_config(type_formulaire: str) -> dict:
    """
    Récupère la configuration d'un type de formulaire.
    
    Args:
        type_formulaire: Type du formulaire (clé de TYPES_FORMULAIRES)
        
    Returns:
        dict: Configuration du type ou dict vide si non trouvé
    """
    return TYPES_FORMULAIRES.get(type_formulaire, {})

def get_icone_statut(statut: str) -> str:
    """
    Récupère l'icône correspondant à un statut.
    
    Args:
        statut: Statut du formulaire
        
    Returns:
        str: Icône correspondante ou '❓' si non trouvé
    """
    return ICONES_STATUTS.get(statut, '❓')

def get_icone_priorite(priorite: str) -> str:
    """
    Récupère l'icône correspondant à une priorité.
    
    Args:
        priorite: Priorité du formulaire
        
    Returns:
        str: Icône correspondante ou '⚪' si non trouvé
    """
    return ICONES_PRIORITES.get(priorite, '⚪')

def valider_type_formulaire(type_formulaire: str) -> bool:
    """
    Valide qu'un type de formulaire existe.
    
    Args:
        type_formulaire: Type à valider
        
    Returns:
        bool: True si le type existe, False sinon
    """
    return type_formulaire in TYPES_FORMULAIRES

def valider_statut(statut: str) -> bool:
    """
    Valide qu'un statut est autorisé.
    
    Args:
        statut: Statut à valider
        
    Returns:
        bool: True si le statut est valide, False sinon
    """
    return statut in STATUTS_FORMULAIRES

def valider_priorite(priorite: str) -> bool:
    """
    Valide qu'une priorité est autorisée.
    
    Args:
        priorite: Priorité à valider
        
    Returns:
        bool: True si la priorité est valide, False sinon
    """
    return priorite in PRIORITES_FORMULAIRES
