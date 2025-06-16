# formulaires/utils/conversions.py
# Fonctions de conversion entre types de formulaires

"""
Fonctions de conversion entre différents types de formulaires.
Gère les transformations : BA→BC, DP→BC, EST→Projet, etc.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from ..core.types_formulaires import TYPES_FORMULAIRES


def convertir_ba_vers_bc(gestionnaire, ba_id: int, parametres: Dict = None) -> Optional[str]:
    """
    Conversion rapide BA → BC avec paramètres par défaut ou personnalisés.
    
    Args:
        gestionnaire: Instance du gestionnaire de formulaires
        ba_id: ID du Bon d'Achats à convertir
        parametres: Paramètres de conversion optionnels
        
    Returns:
        str: Numéro du BC créé ou None si erreur
    """
    try:
        ba_details = gestionnaire.get_formulaire_details(ba_id)
        if not ba_details:
            st.error("Bon d'Achats introuvable")
            return None
        
        if ba_details['statut'] not in ['VALIDÉ', 'APPROUVÉ']:
            st.error("Le BA doit être validé ou approuvé pour conversion")
            return None
        
        # Paramètres par défaut
        parametres = parametres or {}
        
        # Numéro BC automatique
        numero_bc = gestionnaire.generer_numero_document('BON_COMMANDE')
        
        # Métadonnées BC avec conditions par défaut
        metadonnees_bc = {
            'ba_source_id': ba_id,
            'ba_source_numero': ba_details['numero_document'],
            'conversion_automatique': True,
            'conditions_paiement': parametres.get('conditions_paiement', '30 jours net'),
            'adresse_livraison': parametres.get('adresse_livraison', 'DG Inc. - Adresse standard'),
            'contact_reception': parametres.get('contact_reception', 'À définir'),
            'horaires_livraison': parametres.get('horaires_livraison', 'Lundi-Vendredi 8h-16h'),
            'delai_livraison_max': parametres.get('delai_livraison_max', 14),
            'date_conversion': datetime.now().isoformat()
        }
        
        # Notes de conversion automatique
        notes_bc = f"""=== CONVERSION AUTOMATIQUE BA → BC ===
Bon de Commande généré automatiquement depuis {ba_details['numero_document']}
Date conversion : {datetime.now().strftime('%d/%m/%Y à %H:%M')}
Utilisateur : {parametres.get('user_name', 'Système')}

=== CONDITIONS COMMERCIALES ===
Paiement : {metadonnees_bc['conditions_paiement']}
Livraison : {metadonnees_bc['adresse_livraison']}
Contact : {metadonnees_bc['contact_reception']}
Horaires : {metadonnees_bc['horaires_livraison']}
Délai maximum : {metadonnees_bc['delai_livraison_max']} jours

=== NOTES BA SOURCE ===
{ba_details.get('notes', 'Aucune note spécifique')}"""
        
        # Données du BC
        data_bc = {
            'type_formulaire': 'BON_COMMANDE',
            'numero_document': numero_bc,
            'project_id': ba_details.get('project_id'),
            'company_id': ba_details.get('company_id'),
            'employee_id': ba_details.get('employee_id'),
            'statut': parametres.get('statut_initial', 'VALIDÉ'),
            'priorite': ba_details.get('priorite'),
            'date_creation': datetime.now().date(),
            'date_echeance': datetime.now().date() + timedelta(days=metadonnees_bc['delai_livraison_max']),
            'montant_total': ba_details.get('montant_total', 0),
            'notes': notes_bc,
            'metadonnees_json': json.dumps(metadonnees_bc),
            'lignes': ba_details.get('lignes', [])
        }
        
        # Création du BC
        bc_id = gestionnaire.creer_formulaire(data_bc)
        
        if bc_id:
            # Mise à jour du BA original
            gestionnaire.modifier_statut_formulaire(
                ba_id, 'TERMINÉ', 
                ba_details.get('employee_id'), 
                f"Converti automatiquement en BC {numero_bc}"
            )
            
            return numero_bc
        
        return None
        
    except Exception as e:
        st.error(f"Erreur conversion BA→BC: {e}")
        return None


def convertir_dp_vers_bc(gestionnaire, dp_id: int, fournisseur_gagnant: Dict, 
                        conditions_negociees: Dict) -> Optional[str]:
    """
    Conversion DP → BC après sélection du fournisseur gagnant.
    
    Args:
        gestionnaire: Instance du gestionnaire
        dp_id: ID de la Demande de Prix
        fournisseur_gagnant: Données du fournisseur sélectionné
        conditions_negociees: Conditions commerciales négociées
        
    Returns:
        str: Numéro du BC créé ou None
    """
    try:
        dp_details = gestionnaire.get_formulaire_details(dp_id)
        if not dp_details:
            return None
        
        # Numéro BC
        numero_bc = gestionnaire.generer_numero_document('BON_COMMANDE')
        
        # Métadonnées BC depuis RFQ
        metadonnees_bc = {
            'dp_source_id': dp_id,
            'dp_source_numero': dp_details['numero_document'],
            'fournisseur_gagnant': fournisseur_gagnant,
            'conditions_negociees': conditions_negociees,
            'conversion_rfq': True,
            'date_conversion': datetime.now().isoformat(),
            'score_fournisseur': fournisseur_gagnant.get('score_final'),
            'justification_selection': conditions_negociees.get('justification', '')
        }
        
        # Notes BC détaillées
        notes_bc = f"""=== BON DE COMMANDE DEPUIS RFQ ===
Généré depuis RFQ : {dp_details['numero_document']}
Fournisseur sélectionné : {fournisseur_gagnant.get('nom', 'N/A')}
Score obtenu : {fournisseur_gagnant.get('score_final', 0)}/100

=== CONDITIONS NÉGOCIÉES ===
Prix final : {conditions_negociees.get('prix_final', 0):,.2f}$ CAD
Délai : {conditions_negociees.get('delai_final', 0)} jours
Paiement : {conditions_negociees.get('conditions_paiement', 'N/A')}
Garantie : {conditions_negociees.get('garantie', 'N/A')}

=== JUSTIFICATION SÉLECTION ===
{conditions_negociees.get('justification', 'Aucune justification fournie')}

=== CAHIER DES CHARGES ORIGINAL ===
{dp_details.get('notes', '')}"""
        
        # Données du BC
        data_bc = {
            'type_formulaire': 'BON_COMMANDE',
            'numero_document': numero_bc,
            'project_id': dp_details.get('project_id'),
            'company_id': fournisseur_gagnant.get('id'),
            'employee_id': dp_details.get('employee_id'),
            'statut': 'VALIDÉ',
            'priorite': dp_details.get('priorite'),
            'date_creation': datetime.now().date(),
            'date_echeance': datetime.now().date() + timedelta(days=conditions_negociees.get('delai_final', 30)),
            'montant_total': conditions_negociees.get('prix_final', 0),
            'notes': notes_bc,
            'metadonnees_json': json.dumps(metadonnees_bc),
            'lignes': adapter_lignes_dp_vers_bc(dp_details.get('lignes', []), conditions_negociees)
        }
        
        # Création du BC
        bc_id = gestionnaire.creer_formulaire(data_bc)
        
        if bc_id:
            # Finaliser la DP
            gestionnaire.modifier_statut_formulaire(
                dp_id, 'TERMINÉ',
                dp_details.get('employee_id'),
                f"Fournisseur sélectionné - BC {numero_bc} généré"
            )
            
            return numero_bc
        
        return None
        
    except Exception as e:
        st.error(f"Erreur conversion DP→BC: {e}")
        return None


def convertir_estimation_vers_projet(gestionnaire, estimation_id: int) -> Optional[int]:
    """
    Convertit une estimation acceptée en nouveau projet.
    
    Args:
        gestionnaire: Instance du gestionnaire
        estimation_id: ID de l'estimation à convertir
        
    Returns:
        int: ID du projet créé ou None
    """
    try:
        est_details = gestionnaire.get_formulaire_details(estimation_id)
        if not est_details:
            return None
        
        if est_details['statut'] != 'APPROUVÉ':
            st.error("L'estimation doit être approuvée pour conversion")
            return None
        
        # Récupération des métadonnées
        try:
            meta = json.loads(est_details.get('metadonnees_json', '{}'))
        except:
            meta = {}
        
        # Données du nouveau projet
        data_projet = {
            'nom_projet': f"Projet depuis EST {est_details['numero_document']}",
            'client_company_id': est_details.get('company_id'),
            'statut': 'À FAIRE',
            'priorite': est_details.get('priorite', 'NORMAL'),
            'prix_estime': est_details.get('montant_total', 0),
            'date_soumis': datetime.now().date(),
            'date_prevu': datetime.now().date() + timedelta(days=meta.get('delai_execution', 30)),
            'description': generer_description_projet_depuis_estimation(est_details, meta)
        }
        
        # Insertion du nouveau projet
        query = """
            INSERT INTO projects 
            (nom_projet, client_company_id, statut, priorite, prix_estime, 
             date_soumis, date_prevu, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        projet_id = gestionnaire.db.execute_insert(query, (
            data_projet['nom_projet'],
            data_projet['client_company_id'],
            data_projet['statut'],
            data_projet['priorite'],
            data_projet['prix_estime'],
            data_projet['date_soumis'],
            data_projet['date_prevu'],
            data_projet['description']
        ))
        
        if projet_id:
            # Copier les matériaux de l'estimation vers le projet
            copier_materiaux_estimation_vers_projet(gestionnaire, estimation_id, projet_id)
            
            # Mise à jour de l'estimation
            gestionnaire.modifier_statut_formulaire(
                estimation_id,
                'TERMINÉ',
                est_details.get('employee_id'),
                f"Convertie en projet #{projet_id}"
            )
            
            return projet_id
        
        return None
        
    except Exception as e:
        st.error(f"Erreur conversion EST→Projet: {e}")
        return None


def dupliquer_formulaire_nouvelle_version(gestionnaire, formulaire_id: int, 
                                        modifications: Dict) -> Optional[int]:
    """
    Duplique un formulaire pour créer une nouvelle version.
    
    Args:
        gestionnaire: Instance du gestionnaire
        formulaire_id: ID du formulaire à dupliquer
        modifications: Modifications à appliquer
        
    Returns:
        int: ID de la nouvelle version ou None
    """
    try:
        original = gestionnaire.get_formulaire_details(formulaire_id)
        if not original:
            return None
        
        # Calcul du nouveau numéro de version
        numero_version = calculer_nouveau_numero_version(original['numero_document'])
        
        # Métadonnées de la nouvelle version
        try:
            meta_originales = json.loads(original.get('metadonnees_json', '{}'))
        except:
            meta_originales = {}
        
        nouvelles_meta = meta_originales.copy()
        nouvelles_meta.update({
            'version_precedente_id': formulaire_id,
            'version_numero': extraire_numero_version(numero_version),
            'date_revision': datetime.now().isoformat(),
            'motif_revision': modifications.get('motif', 'Révision'),
            'modifications_apportees': modifications.get('details', [])
        })
        
        # Application des modifications
        nouveau_montant = original.get('montant_total', 0)
        if modifications.get('ajustement_prix'):
            ajustement = modifications['ajustement_prix']
            if ajustement.get('type') == 'pourcentage':
                nouveau_montant *= (1 + ajustement['valeur'] / 100)
            elif ajustement.get('type') == 'montant':
                nouveau_montant += ajustement['valeur']
        
        # Nouvelles lignes si spécifiées
        nouvelles_lignes = modifications.get('nouvelles_lignes', original.get('lignes', []))
        
        # Notes de révision
        notes_revision = f"""=== RÉVISION VERSION {numero_version} ===
Version précédente : {original['numero_document']}
Motif : {modifications.get('motif', 'Non spécifié')}
Date révision : {datetime.now().strftime('%d/%m/%Y à %H:%M')}

=== MODIFICATIONS APPORTÉES ===
{chr(10).join(modifications.get('details', ['Aucune modification détaillée']))}

=== NOTES VERSION PRÉCÉDENTE ===
{original.get('notes', '')}"""
        
        # Données de la nouvelle version
        data_nouvelle_version = {
            'type_formulaire': original['type_formulaire'],
            'numero_document': numero_version,
            'project_id': original.get('project_id'),
            'company_id': original.get('company_id'),
            'employee_id': original.get('employee_id'),
            'statut': 'BROUILLON',  # Nouvelle version en brouillon par défaut
            'priorite': modifications.get('nouvelle_priorite', original.get('priorite')),
            'date_creation': datetime.now().date(),
            'date_echeance': modifications.get('nouvelle_echeance', original.get('date_echeance')),
            'montant_total': nouveau_montant,
            'notes': notes_revision,
            'metadonnees_json': json.dumps(nouvelles_meta),
            'lignes': nouvelles_lignes
        }
        
        return gestionnaire.creer_formulaire(data_nouvelle_version)
        
    except Exception as e:
        st.error(f"Erreur création nouvelle version: {e}")
        return None


def adapter_lignes_dp_vers_bc(lignes_dp: List[Dict], conditions: Dict) -> List[Dict]:
    """
    Adapte les lignes d'une DP vers un BC avec les prix négociés.
    
    Args:
        lignes_dp: Lignes originales de la DP
        conditions: Conditions négociées avec prix
        
    Returns:
        List[Dict]: Lignes adaptées pour le BC
    """
    lignes_bc = []
    prix_total_negocie = conditions.get('prix_final', 0)
    
    if not lignes_dp:
        return lignes_bc
    
    # Répartition proportionnelle du prix négocié
    quantite_totale = sum(ligne.get('quantite', 0) for ligne in lignes_dp)
    
    for ligne in lignes_dp:
        if quantite_totale > 0:
            # Prix unitaire calculé proportionnellement
            proportion = ligne.get('quantite', 0) / quantite_totale
            prix_unitaire = (prix_total_negocie * proportion) / ligne.get('quantite', 1)
        else:
            prix_unitaire = 0
        
        ligne_bc = {
            'description': ligne.get('description', ''),
            'quantite': ligne.get('quantite', 0),
            'unite': ligne.get('unite', 'UN'),
            'prix_unitaire': prix_unitaire,
            'montant_ligne': ligne.get('quantite', 0) * prix_unitaire,
            'specifications': ligne.get('specifications', ''),
            'delai_livraison': conditions.get('delai_final', 30)
        }
        
        lignes_bc.append(ligne_bc)
    
    return lignes_bc


def generer_description_projet_depuis_estimation(est_details: Dict, meta: Dict) -> str:
    """
    Génère une description de projet depuis une estimation.
    
    Args:
        est_details: Détails de l'estimation
        meta: Métadonnées de l'estimation
        
    Returns:
        str: Description formatée du projet
    """
    description = f"""PROJET GÉNÉRÉ DEPUIS ESTIMATION {est_details['numero_document']}

CLIENT: {est_details.get('company_nom', 'N/A')}
COMMERCIAL: {est_details.get('employee_nom', 'N/A')}
MONTANT VALIDÉ: {est_details.get('montant_total', 0):,.2f}$ CAD

TEMPLATE INDUSTRIE: {meta.get('template_industrie', 'N/A')}
DÉLAI D'EXÉCUTION: {meta.get('delai_execution', 'N/A')} jours
GARANTIE: {meta.get('garantie_proposee', 'N/A')}

DESCRIPTION ORIGINALE:
{est_details.get('notes', 'Aucune description détaillée')[:500]}

DATE CONVERSION: {datetime.now().strftime('%d/%m/%Y à %H:%M')}
"""
    
    return description


def copier_materiaux_estimation_vers_projet(gestionnaire, estimation_id: int, projet_id: int) -> bool:
    """
    Copie les matériaux d'une estimation vers un nouveau projet.
    
    Args:
        gestionnaire: Instance du gestionnaire
        estimation_id: ID de l'estimation source
        projet_id: ID du projet destination
        
    Returns:
        bool: True si succès, False sinon
    """
    try:
        est_details = gestionnaire.get_formulaire_details(estimation_id)
        lignes = est_details.get('lignes', [])
        
        for ligne in lignes:
            query = """
                INSERT INTO materials 
                (project_id, designation, quantite, prix_unitaire, unite, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            
            gestionnaire.db.execute_insert(query, (
                projet_id,
                ligne.get('description', ''),
                ligne.get('quantite', 0),
                ligne.get('prix_unitaire', 0),
                ligne.get('unite', 'UN'),
                f"Importé depuis estimation {est_details['numero_document']}"
            ))
        
        return True
        
    except Exception as e:
        st.error(f"Erreur copie matériaux: {e}")
        return False


def calculer_nouveau_numero_version(numero_original: str) -> str:
    """
    Calcule le nouveau numéro de version.
    
    Args:
        numero_original: Numéro du document original
        
    Returns:
        str: Nouveau numéro avec version incrémentée
    """
    # Si déjà une version (ex: "EST-2024-001 v2")
    if ' v' in numero_original:
        base, version_str = numero_original.split(' v')
        try:
            version_actuelle = int(version_str)
            return f"{base} v{version_actuelle + 1}"
        except ValueError:
            return f"{numero_original} v2"
    else:
        # Première version
        return f"{numero_original} v2"


def extraire_numero_version(numero_avec_version: str) -> int:
    """
    Extrait le numéro de version d'un numéro de document.
    
    Args:
        numero_avec_version: Numéro avec version (ex: "EST-2024-001 v3")
        
    Returns:
        int: Numéro de version ou 1 si pas de version
    """
    if ' v' in numero_avec_version:
        try:
            version_str = numero_avec_version.split(' v')[-1]
            return int(version_str)
        except ValueError:
            return 1
    return 1
