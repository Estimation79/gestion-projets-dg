# formulaires/bons_travail/__init__.py
# Module Bons de Travail - Exports principaux

"""
Module Bons de Travail.
Contient le gestionnaire spécialisé et les interfaces pour les documents de travail interne.
"""

from .gestionnaire_bt import GestionnaireBonsTravail
from .interface_bt import render_bons_travail_tab

__all__ = [
    'GestionnaireBonsTravail',
    'render_bons_travail_tab'
]

# Métadonnées du module
__version__ = "1.0.0"
__author__ = "DG Inc. ERP Team"
__description__ = "Gestion des Bons de Travail - Documents de travail interne"
