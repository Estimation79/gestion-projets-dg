# formulaires/bons_achats/__init__.py

"""
Module Bons d'Achats.
Contient le gestionnaire spécialisé et les interfaces pour les documents d'achat fournisseurs.
"""

from .gestionnaire_ba import GestionnaireBonsAchats
from .interface_ba import render_bons_achats_tab

__all__ = [
    'GestionnaireBonsAchats',
    'render_bons_achats_tab'
]

__version__ = "1.0.0"
__author__ = "DG Inc. ERP Team"
__description__ = "Documents d'achat fournisseurs avec gestion stocks critiques et conversion BC"
