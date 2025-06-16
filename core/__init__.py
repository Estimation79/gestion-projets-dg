# formulaires/core/__init__.py
# Point d'entrée du module core

"""
Module core pour la gestion des formulaires.
Contient la classe de base et les constantes communes.
"""

from .base_gestionnaire import GestionnaireFormulaires
from .types_formulaires import (
    TYPES_FORMULAIRES,
    STATUTS_FORMULAIRES, 
    PRIORITES_FORMULAIRES,
    ICONES_STATUTS,
    ICONES_PRIORITES,
    TEMPLATES_INDUSTRIE,
    UNITES_MESURE,
    TYPES_VALIDATION,
    DEVISES,
    CONDITIONS_PAIEMENT,
    get_type_formulaire_config,
    get_icone_statut,
    get_icone_priorite,
    valider_type_formulaire,
    valider_statut,
    valider_priorite
)

__all__ = [
    'GestionnaireFormulaires',
    'TYPES_FORMULAIRES',
    'STATUTS_FORMULAIRES', 
    'PRIORITES_FORMULAIRES',
    'ICONES_STATUTS',
    'ICONES_PRIORITES',
    'TEMPLATES_INDUSTRIE',
    'UNITES_MESURE',
    'TYPES_VALIDATION',
    'DEVISES',
    'CONDITIONS_PAIEMENT',
    'get_type_formulaire_config',
    'get_icone_statut',
    'get_icone_priorite',
    'valider_type_formulaire',
    'valider_statut',
    'valider_priorite'
]
