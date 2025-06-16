# formulaires/estimations/__init__.py

"""
Module Estimations.
Contient le gestionnaire spécialisé et les interfaces pour Devis clients avec calculs automatiques.
"""

from .gestionnaire_estimation import GestionnaireEstimations
from .interface_estimation import render_estimations_tab

__all__ = [
    'GestionnaireEstimations',
    'render_estimations_tab'
]

__version__ = "1.0.0"
__author__ = "DG Inc. ERP Team"
__description__ = "Devis clients avec calculs automatiques"
