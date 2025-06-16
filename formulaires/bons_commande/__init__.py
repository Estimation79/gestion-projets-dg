# formulaires/bons_commande/__init__.py

"""
Module Bons de Commande.
Contient le gestionnaire spécialisé et les interfaces pour les commandes officielles fournisseurs.
"""

from .gestionnaire_bc import GestionnaireBonsCommande
from .interface_bc import render_bons_commande_tab

__all__ = [
    'GestionnaireBonsCommande',
    'render_bons_commande_tab'
]

__version__ = "1.0.0"
__author__ = "DG Inc. ERP Team"
__description__ = "Commandes officielles fournisseurs avec suivi livraisons et réception marchandises"
