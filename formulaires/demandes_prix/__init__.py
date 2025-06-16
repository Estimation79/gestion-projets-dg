# formulaires/demandes_prix/__init__.py

"""
Module Demandes de Prix.
Contient le gestionnaire spécialisé et les interfaces pour RFQ multi-fournisseurs.
"""

from .gestionnaire_dp import GestionnaireDemandesPrix
from .interface_dp import render_demandes_prix_tab

__all__ = [
    'GestionnaireDemandesPrix',
    'render_demandes_prix_tab'
]

__version__ = "1.0.0"
__author__ = "DG Inc. ERP Team"
__description__ = "RFQ multi-fournisseurs avec comparaison d'offres et sélection automatique du gagnant"
