# formulaires/utils/__init__.py
# Point d'entrée du module utils

"""
Module utils pour les formulaires.
Contient toutes les fonctions utilitaires communes.
"""

# Import des validations
from .validations import (
    valider_formulaire_base,
    valider_bon_travail,
    valider_bon_achat,
    valider_bon_commande,
    valider_demande_prix,
    valider_estimation,
    valider_lignes_formulaire,
    valider_date,
    valider_email,
    valider_telephone,
    valider_code_postal_canadien,
    valider_montant_devise,
    valider_coherence_dates
)

# Import des conversions
from .conversions import (
    convertir_ba_vers_bc,
    convertir_dp_vers_bc,
    convertir_estimation_vers_projet,
    dupliquer_formulaire_nouvelle_version,
    adapter_lignes_dp_vers_bc,
    generer_description_projet_depuis_estimation,
    copier_materiaux_estimation_vers_projet,
    calculer_nouveau_numero_version,
    extraire_numero_version
)

# Import des helpers
from .helpers import (
    get_projets_actifs,
    get_employes_actifs,
    get_fournisseurs_actifs,
    get_clients_actifs,
    get_operations_projet,
    get_materiaux_projet,
    get_work_centers_actifs,
    get_articles_inventaire,
    get_articles_inventaire_critique,
    search_articles_inventaire,
    get_projets_client,
    get_poste_travail,
    calculer_quantite_recommandee,
    get_note_fournisseur_fictive,
    generer_offres_fictives_rfq,
    formater_montant,
    formater_delai,
    calculer_statut_validite,
    generer_couleur_statut,
    generer_couleur_priorite,
    verifier_coherence_dates_projet,
    valider_budget_projet_vs_estimation,
    calculer_taux_marge_realiste
)

__all__ = [
    # Validations
    'valider_formulaire_base',
    'valider_bon_travail',
    'valider_bon_achat',
    'valider_bon_commande',
    'valider_demande_prix',
    'valider_estimation',
    'valider_lignes_formulaire',
    'valider_date',
    'valider_email',
    'valider_telephone',
    'valider_code_postal_canadien',
    'valider_montant_devise',
    'valider_coherence_dates',
    
    # Conversions
    'convertir_ba_vers_bc',
    'convertir_dp_vers_bc',
    'convertir_estimation_vers_projet',
    'dupliquer_formulaire_nouvelle_version',
    'adapter_lignes_dp_vers_bc',
    'generer_description_projet_depuis_estimation',
    'copier_materiaux_estimation_vers_projet',
    'calculer_nouveau_numero_version',
    'extraire_numero_version',
    
    # Helpers - Récupération données
    'get_projets_actifs',
    'get_employes_actifs',
    'get_fournisseurs_actifs',
    'get_clients_actifs',
    'get_operations_projet',
    'get_materiaux_projet',
    'get_work_centers_actifs',
    'get_articles_inventaire',
    'get_articles_inventaire_critique',
    'search_articles_inventaire',
    'get_projets_client',
    'get_poste_travail',
    
    # Helpers - Calculs et formatage
    'calculer_quantite_recommandee',
    'get_note_fournisseur_fictive',
    'generer_offres_fictives_rfq',
    'formater_montant',
    'formater_delai',
    'calculer_statut_validite',
    'generer_couleur_statut',
    'generer_couleur_priorite',
    'verifier_coherence_dates_projet',
    'valider_budget_projet_vs_estimation',
    'calculer_taux_marge_realiste'
]
