# formulaires/bons_achats/gestionnaire_ba.py

"""
Gestionnaire spécialisé pour les Bons d'Achats.
Contient la logique métier spécifique aux documents d'achat fournisseurs.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from ..core.base_gestionnaire import GestionnaireFormulaires
from ..utils.validations import valider_bon_achat
from ..utils.helpers import (
    get_projets_actifs,
    get_employes_actifs,
    get_fournisseurs_actifs,
    search_articles_inventaire,
    get_articles_inventaire_critique,
    calculer_quantite_recommandee,
    convertir_ba_vers_bc
)

class GestionnaireBonsAchats:
    """
    Gestionnaire spécialisé pour les Bons d'Achats.
    
    Gère les opérations spécifiques aux BA :
    - Création avec validation fournisseur
    - Gestion des stocks critiques
    - Réapprovisionnement automatique  
    - Conversion vers Bons de Commande
    """
    
    def __init__(self, gestionnaire_base: GestionnaireFormulaires):
        self.base = gestionnaire_base
        self.db = gestionnaire_base.db
    
    def creer_bon_achat(self, data: Dict) -> Optional[int]:
        """Crée un nouveau Bon d'Achats avec validations spécifiques."""
        try:
            # Validation spécifique BA
            is_valid, erreurs = valider_bon_achat(data)
            if not is_valid:
                for erreur in erreurs:
                    st.error(f"❌ {erreur}")
                return None
            
            # Enrichissement des données
            data['type_formulaire'] = 'BON_ACHAT'
            
            # Métadonnées spécifiques BA
            metadonnees = {
                'fournisseur_id': data.get('company_id'),
                'livraison_lieu': data.get('livraison_lieu', ''),
                'livraison_contact': data.get('livraison_contact', ''),
                'mode_paiement': data.get('mode_paiement', '30 jours net'),
                'centre_cout': data.get('centre_cout', ''),
                'approbation_requise': data.get('approbation_requise', False),
                'manager_approbateur': data.get('manager_approbateur'),
                'urgence_motif': data.get('urgence_motif', ''),
                'projet_associe': data.get('project_id'),
                'auto_generated': data.get('auto_generated', False),
                'articles_critiques': data.get('articles_critiques', []),
                'date_creation_ba': datetime.now().isoformat()
            }
            
            data['metadonnees_json'] = json.dumps(metadonnees)
            
            # Création via gestionnaire base
            ba_id = self.base.creer_formulaire(data)
            
            if ba_id:
                self._post_creation_ba(ba_id, data)
            
            return ba_id
            
        except Exception as e:
            st.error(f"Erreur création BA: {e}")
            return None
    
    def _post_creation_ba(self, ba_id: int, data: Dict) -> None:
        """Actions post-création spécifiques aux BA."""
        try:
            # Notification automatique si urgent
            if data.get('priorite') == 'CRITIQUE':
                self._notifier_ba_urgent(ba_id, data)
            
            # Mise à jour des stocks si réapprovisionnement
            if data.get('auto_generated'):
                self._marquer_articles_en_commande(data.get('articles_critiques', []))
                
        except Exception as e:
            st.warning(f"Actions post-création BA partiellement échouées: {e}")
    
    def _notifier_ba_urgent(self, ba_id: int, data: Dict) -> None:
        """Notification pour les BA urgents."""
        try:
            # Simulation notification service achats
            st.info("📧 Notification envoyée au service achats pour traitement prioritaire")
        except Exception as e:
            st.warning(f"Erreur notification BA urgent: {e}")
    
    def _marquer_articles_en_commande(self, articles_critiques: List[int]) -> None:
        """Marque les articles critiques comme en commande."""
        try:
            for article_id in articles_critiques:
                # Mise à jour statut inventaire
                query = "UPDATE inventory_items SET statut = 'EN COMMANDE' WHERE id = ?"
                self.db.execute_update(query, (article_id,))
        except Exception as e:
            st.warning(f"Erreur mise à jour statuts inventaire: {e}")
    
    def get_bons_achats(self, **filters) -> List[Dict]:
        """Récupère les Bons d'Achats avec filtres spécifiques."""
        try:
            # Filtres de base + spécifiques BA
            bons_achats = self.base.get_formulaires('BON_ACHAT', **filters)
            
            # Enrichissement avec données spécifiques
            for ba in bons_achats:
                ba['info_fournisseur'] = self._get_info_fournisseur(ba.get('company_id'))
                ba['nb_articles'] = self._get_nb_articles_ba(ba['id'])
                ba['statut_livraison'] = self._get_statut_livraison_ba(ba['id'])
                
            return bons_achats
            
        except Exception as e:
            st.error(f"Erreur récupération BA: {e}")
            return []
    
    def _get_info_fournisseur(self, company_id: int) -> Dict:
        """Récupère les informations détaillées du fournisseur."""
        try:
            if not company_id:
                return {}
            
            query = "SELECT nom, secteur, adresse FROM companies WHERE id = ?"
            result = self.db.execute_query(query, (company_id,))
            return dict(result[0]) if result else {}
        except:
            return {}
    
    def _get_nb_articles_ba(self, ba_id: int) -> int:
        """Compte le nombre d'articles dans un BA."""
        try:
            query = "SELECT COUNT(*) as count FROM formulaire_lignes WHERE formulaire_id = ?"
            result = self.db.execute_query(query, (ba_id,))
            return result[0]['count'] if result else 0
        except:
            return 0
    
    def _get_statut_livraison_ba(self, ba_id: int) -> str:
        """Récupère le statut de livraison d'un BA."""
        try:
            # Vérifier si converti en BC
            query = """
                SELECT COUNT(*) as count FROM formulaires 
                WHERE type_formulaire = 'BON_COMMANDE' 
                AND metadonnees_json LIKE ?
            """
            result = self.db.execute_query(query, (f'%"ba_source_id": {ba_id}%',))
            
            if result and result[0]['count'] > 0:
                return "Converti en BC"
            else:
                return "En attente"
        except:
            return "Indéterminé"
    
    def get_statistiques_ba(self) -> Dict:
        """Calcule les statistiques spécifiques aux BA."""
        try:
            stats_base = self.base.get_statistiques_formulaires().get('BON_ACHAT', {})
            
            # Enrichissement spécifique BA
            query = """
                SELECT 
                    COUNT(CASE WHEN f.priorite = 'CRITIQUE' THEN 1 END) as ba_urgents,
                    COUNT(CASE WHEN f.metadonnees_json LIKE '%"auto_generated": true%' THEN 1 END) as ba_automatiques,
                    AVG(f.montant_total) as montant_moyen_ba,
                    COUNT(CASE WHEN EXISTS(
                        SELECT 1 FROM formulaires f2 
                        WHERE f2.type_formulaire = 'BON_COMMANDE' 
                        AND f2.metadonnees_json LIKE '%"ba_source_id": ' || f.id || '%'
                    ) THEN 1 END) as ba_convertis
                FROM formulaires f
                WHERE f.type_formulaire = 'BON_ACHAT'
            """
            
            result = self.db.execute_query(query)
            if result:
                stats_enrichies = dict(result[0])
                stats_base.update(stats_enrichies)
            
            # Calcul taux de conversion
            total_ba = stats_base.get('total', 0)
            ba_convertis = stats_base.get('ba_convertis', 0)
            if total_ba > 0:
                stats_base['taux_conversion_bc'] = (ba_convertis / total_ba) * 100
            else:
                stats_base['taux_conversion_bc'] = 0
            
            return stats_base
            
        except Exception as e:
            st.error(f"Erreur stats BA: {e}")
            return {}
    
    def creer_ba_automatique_stocks_critiques(self, 
                                            fournisseur_id: int, 
                                            employe_id: int, 
                                            articles_critiques: List[Dict],
                                            notes: str = "") -> Optional[int]:
        """Crée automatiquement un BA pour réapprovisionnement stocks critiques."""
        try:
            # Préparation des lignes articles
            articles_commande = []
            montant_total = 0
            
            for article in articles_critiques:
                qty_recommandee = calculer_quantite_recommandee(article)
                prix_estime = 50.0  # Prix par défaut, à ajuster
                
                articles_commande.append({
                    'description': f"{article['nom']} - Réapprovisionnement stock critique",
                    'quantite': qty_recommandee,
                    'unite': 'UN',
                    'prix_unitaire': prix_estime,
                    'code_article': f"INV-{article['id']}",
                    'reference_materiau': article['id']
                })
                
                montant_total += qty_recommandee * prix_estime
            
            # Données du BA automatique
            data = {
                'company_id': fournisseur_id,
                'employee_id': employe_id,
                'statut': 'VALIDÉ',
                'priorite': 'URGENT',
                'date_creation': datetime.now().date(),
                'date_echeance': datetime.now().date() + timedelta(days=7),
                'montant_total': montant_total,
                'notes': f"=== RÉAPPROVISIONNEMENT AUTOMATIQUE ===\n{notes or f'Réapprovisionnement automatique de {len(articles_critiques)} article(s) en stock critique détecté le {datetime.now().strftime(\"%d/%m/%Y à %H:%M\")}'}",
                'auto_generated': True,
                'articles_critiques': [a['id'] for a in articles_critiques],
                'lignes': articles_commande
            }
            
            return self.creer_bon_achat(data)
            
        except Exception as e:
            st.error(f"Erreur création BA automatique: {e}")
            return None
    
    def convertir_vers_bc(self, ba_id: int, conditions_finales: Dict = None) -> Optional[str]:
        """Convertit un BA en Bon de Commande."""
        try:
            return convertir_ba_vers_bc(self.base, ba_id, conditions_finales)
        except Exception as e:
            st.error(f"Erreur conversion BA→BC: {e}")
            return None
    
    def get_ba_convertibles(self) -> List[Dict]:
        """Récupère les BA prêts à être convertis en BC."""
        try:
            return [ba for ba in self.get_bons_achats() 
                   if ba['statut'] in ['VALIDÉ', 'APPROUVÉ'] and 
                   self._get_statut_livraison_ba(ba['id']) != "Converti en BC"]
        except Exception as e:
            st.error(f"Erreur récupération BA convertibles: {e}")
            return []
    
    def marquer_ba_recu(self, ba_id: int, employee_id: int, notes: str = "") -> bool:
        """Marque un BA comme reçu rapidement."""
        try:
            # Mise à jour du statut
            self.base.modifier_statut_formulaire(
                ba_id, 
                'TERMINÉ', 
                employee_id, 
                f"BA marqué comme reçu. {notes}"
            )
            
            # Enregistrement de la réception
            self.base.enregistrer_validation(
                ba_id,
                employee_id,
                'RECEPTION',
                f"Réception rapide validée. {notes}"
            )
            
            return True
            
        except Exception as e:
            st.error(f"Erreur marquage réception BA: {e}")
            return False
