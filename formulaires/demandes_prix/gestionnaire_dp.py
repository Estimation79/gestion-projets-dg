# formulaires/demandes_prix/gestionnaire_dp.py

"""
Gestionnaire spécialisé pour les Demandes de Prix.
Contient la logique métier spécifique aux RFQ multi-fournisseurs.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import hashlib

from ..core.base_gestionnaire import GestionnaireFormulaires
from ..utils.validations import valider_demande_prix
from ..utils.helpers import (
    get_projets_actifs,
    get_employes_actifs,
    get_fournisseurs_actifs
)

class GestionnaireDemandesPrix:
    """
    Gestionnaire spécialisé pour les Demandes de Prix.
    
    Gère les opérations spécifiques aux demandes_prix :
    - Gestion multi-fournisseurs (3-5 fournisseurs par RFQ)
    - Comparaison automatique des offres
    - Critères d'évaluation pondérés
    - Sélection automatique + manuelle du gagnant
    - Conversion automatique DP → BC
    """
    
    def __init__(self, gestionnaire_base: GestionnaireFormulaires):
        self.base = gestionnaire_base
        self.db = gestionnaire_base.db
        
        # Types RFQ disponibles
        self.types_rfq = ['Ouvert', 'Restreint', 'Négocié', 'Urgente']
        
        # Critères d'évaluation standard
        self.criteres_standard = {
            'prix': {'nom': 'Prix', 'ponderation_defaut': 40},
            'delai': {'nom': 'Délai de Livraison', 'ponderation_defaut': 30},
            'qualite': {'nom': 'Qualité Fournisseur', 'ponderation_defaut': 30},
            'proximite': {'nom': 'Proximité Géographique', 'ponderation_defaut': 0},
            'experience': {'nom': 'Expérience Secteur', 'ponderation_defaut': 0}
        }
    
    def creer_demande_prix(self, data: Dict) -> Optional[int]:
        """Crée une nouvelle Demande de Prix avec validations spécifiques."""
        try:
            # Validation spécifique DP
            is_valid, erreurs = valider_demande_prix(data)
            if not is_valid:
                for erreur in erreurs:
                    st.error(f"❌ {erreur}")
                return None
            
            # Enrichissement des données
            data['type_formulaire'] = 'DEMANDE_PRIX'
            
            # Métadonnées spécifiques DP
            metadonnees = {
                'fournisseurs_invites': data.get('fournisseurs_invites', []),
                'type_rfq': data.get('type_rfq', 'Ouvert'),
                'criteres_evaluation': data.get('criteres_evaluation', {}),
                'delai_reponse': data.get('delai_reponse', 7),
                'mode_evaluation': data.get('mode_evaluation', 'Prix seul'),
                'validite_offre': data.get('validite_offre', 30),
                'conditions_participation': data.get('conditions_participation', ''),
                'langue_reponse': data.get('langue_reponse', 'Français'),
                'date_creation_dp': datetime.now().isoformat(),
                'offres_recues': {},  # Sera rempli quand les offres arrivent
                'fournisseur_gagnant': None,  # Sera défini lors de la sélection
                'conversion_bc_id': None  # ID du BC généré
            }
            
            data['metadonnees_json'] = json.dumps(metadonnees)
            
            # Création via gestionnaire base
            dp_id = self.base.creer_formulaire(data)
            
            if dp_id:
                self._post_creation_dp(dp_id, data)
            
            return dp_id
            
        except Exception as e:
            st.error(f"Erreur création DP: {e}")
            return None
    
    def _post_creation_dp(self, dp_id: int, data: Dict) -> None:
        """Actions post-création spécifiques aux DP."""
        try:
            # Générer des offres fictives pour la démo si demandé
            if data.get('generer_offres_demo'):
                self._generer_offres_demo(dp_id, data)
            
            # Notifier les fournisseurs invités (simulation)
            fournisseurs_invites = data.get('fournisseurs_invites', [])
            if fournisseurs_invites:
                st.info(f"📧 Notifications RFQ envoyées à {len(fournisseurs_invites)} fournisseur(s)")
                
        except Exception as e:
            st.warning(f"Actions post-création DP partiellement échouées: {e}")
    
    def get_demandes_prix(self, **filters) -> List[Dict]:
        """Récupère les Demandes de Prix avec filtres spécifiques."""
        try:
            # Filtres de base + spécifiques DP
            demandes = self.base.get_formulaires('DEMANDE_PRIX', **filters)
            
            # Enrichissement avec données spécifiques DP
            for item in demandes:
                item['infos_rfq'] = self._get_infos_rfq(item['id'])
                item['nb_fournisseurs_invites'] = self._get_nb_fournisseurs_invites(item['id'])
                item['statut_offres'] = self._get_statut_offres(item['id'])
                
            return demandes
            
        except Exception as e:
            st.error(f"Erreur récupération DP: {e}")
            return []
    
    def _get_infos_rfq(self, dp_id: int) -> Dict:
        """Récupère les informations RFQ d'une DP."""
        try:
            query = "SELECT metadonnees_json FROM formulaires WHERE id = ?"
            result = self.db.execute_query(query, (dp_id,))
            
            if result:
                meta = json.loads(result[0]['metadonnees_json'] or '{}')
                return {
                    'type_rfq': meta.get('type_rfq', 'N/A'),
                    'delai_reponse': meta.get('delai_reponse', 0),
                    'mode_evaluation': meta.get('mode_evaluation', 'N/A')
                }
            return {}
            
        except Exception as e:
            st.error(f"Erreur infos RFQ: {e}")
            return {}
    
    def _get_nb_fournisseurs_invites(self, dp_id: int) -> int:
        """Récupère le nombre de fournisseurs invités."""
        try:
            query = "SELECT metadonnees_json FROM formulaires WHERE id = ?"
            result = self.db.execute_query(query, (dp_id,))
            
            if result:
                meta = json.loads(result[0]['metadonnees_json'] or '{}')
                return len(meta.get('fournisseurs_invites', []))
            return 0
            
        except Exception as e:
            return 0
    
    def _get_statut_offres(self, dp_id: int) -> str:
        """Détermine le statut des offres pour une DP."""
        try:
            query = "SELECT metadonnees_json, statut FROM formulaires WHERE id = ?"
            result = self.db.execute_query(query, (dp_id,))
            
            if result:
                statut = result[0]['statut']
                meta = json.loads(result[0]['metadonnees_json'] or '{}')
                
                if statut == 'TERMINÉ':
                    return "Gagnant sélectionné"
                elif meta.get('offres_recues'):
                    nb_offres = len(meta.get('offres_recues', {}))
                    nb_invites = len(meta.get('fournisseurs_invites', []))
                    return f"{nb_offres}/{nb_invites} offres reçues"
                elif statut == 'ENVOYÉ':
                    return "En attente offres"
                else:
                    return "Brouillon"
            
            return "N/A"
            
        except Exception as e:
            return "Erreur"
    
    def get_statistiques_demande_prix(self) -> Dict:
        """Calcule les statistiques spécifiques aux DP."""
        try:
            stats_base = self.base.get_statistiques_formulaires().get('DEMANDE_PRIX', {})
            
            # Enrichissement spécifique DP
            query = """
                SELECT 
                    COUNT(CASE WHEN f.statut = 'TERMINÉ' THEN 1 END) as dp_terminees,
                    COUNT(CASE WHEN f.statut = 'ENVOYÉ' THEN 1 END) as dp_en_cours,
                    AVG(f.montant_total) as montant_moyen,
                    COUNT(DISTINCT f.company_id) as fournisseurs_uniques
                FROM formulaires f
                WHERE f.type_formulaire = 'DEMANDE_PRIX'
            """
            
            result = self.db.execute_query(query)
            if result:
                stats_enrichies = dict(result[0])
                
                # Calculs avancés DP
                stats_enrichies['taux_conversion_bc'] = self._calculer_taux_conversion_bc()
                stats_enrichies['delai_moyen_reponse'] = self._calculer_delai_moyen_reponse()
                stats_enrichies['fournisseurs_les_plus_performants'] = self._get_top_fournisseurs()
                
                stats_base.update(stats_enrichies)
            
            return stats_base
            
        except Exception as e:
            st.error(f"Erreur stats DP: {e}")
            return {}
    
    def _calculer_taux_conversion_bc(self) -> float:
        """Calcule le taux de conversion DP → BC."""
        try:
            query_total = "SELECT COUNT(*) as total FROM formulaires WHERE type_formulaire = 'DEMANDE_PRIX'"
            query_converties = """
                SELECT COUNT(*) as converties FROM formulaires 
                WHERE type_formulaire = 'BON_COMMANDE' 
                AND metadonnees_json LIKE '%dp_source_id%'
            """
            
            total_result = self.db.execute_query(query_total)
            converties_result = self.db.execute_query(query_converties)
            
            if total_result and converties_result:
                total = total_result[0]['total']
                converties = converties_result[0]['converties']
                return (converties / total * 100) if total > 0 else 0.0
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _calculer_delai_moyen_reponse(self) -> int:
        """Calcule le délai moyen de réponse des fournisseurs."""
        try:
            # Simulation basée sur les métadonnées
            query = """
                SELECT metadonnees_json FROM formulaires 
                WHERE type_formulaire = 'DEMANDE_PRIX' 
                AND statut IN ('APPROUVÉ', 'TERMINÉ')
            """
            
            result = self.db.execute_query(query)
            delais = []
            
            for row in result:
                try:
                    meta = json.loads(row['metadonnees_json'] or '{}')
                    delai_reponse = meta.get('delai_reponse', 7)
                    delais.append(delai_reponse)
                except:
                    continue
            
            return int(sum(delais) / len(delais)) if delais else 7
            
        except Exception:
            return 7
    
    def _get_top_fournisseurs(self) -> List[Dict]:
        """Récupère les fournisseurs les plus performants."""
        try:
            # Analyse basée sur les participations aux RFQ
            query = """
                SELECT c.nom, COUNT(f.id) as participations, AVG(f.montant_total) as montant_moyen
                FROM formulaires f
                JOIN companies c ON f.company_id = c.id
                WHERE f.type_formulaire = 'DEMANDE_PRIX'
                GROUP BY c.id, c.nom
                ORDER BY participations DESC, montant_moyen ASC
                LIMIT 5
            """
            
            rows = self.db.execute_query(query)
            return [dict(row) for row in rows]
            
        except Exception:
            return []
    
    def comparer_offres(self, dp_id: int, offres_data: List[Dict] = None) -> Dict:
        """Compare automatiquement les offres reçues selon les critères pondérés."""
        try:
            # Récupération de la DP et de ses critères
            dp_details = self.base.get_formulaire_details(dp_id)
            if not dp_details:
                return {"erreur": "DP introuvable"}
            
            meta = json.loads(dp_details.get('metadonnees_json', '{}'))
            criteres_eval = meta.get('criteres_evaluation', {})
            
            # Utiliser les offres fournies ou générer des offres fictives
            if offres_data:
                offres = offres_data
            else:
                offres = self._generer_offres_fictives_pour_comparaison(dp_details, meta)
            
            # Calcul des scores pondérés
            offres_avec_scores = self._calculer_scores_offres(offres, criteres_eval)
            
            # Recommandation automatique
            meilleure_offre = max(offres_avec_scores, key=lambda x: x.get('score_final', 0))
            
            return {
                'dp_id': dp_id,
                'offres_analysees': offres_avec_scores,
                'recommandation': meilleure_offre,
                'criteres_utilises': criteres_eval,
                'analyse_complete': True
            }
            
        except Exception as e:
            st.error(f"Erreur comparaison offres: {e}")
            return {"erreur": str(e)}
    
    def _calculer_scores_offres(self, offres: List[Dict], criteres_eval: Dict) -> List[Dict]:
        """Calcule les scores pondérés des offres."""
        if not offres:
            return []
        
        # Normalisation des critères (0-100)
        prix_list = [o.get('prix_total', 0) for o in offres if o.get('conforme', True)]
        delai_list = [o.get('delai_livraison', 0) for o in offres if o.get('conforme', True)]
        proximite_list = [o.get('proximite_km', 0) for o in offres if o.get('conforme', True)]
        
        # Calcul des min/max pour normalisation
        if prix_list:
            prix_min, prix_max = min(prix_list), max(prix_list)
        if delai_list:
            delai_min, delai_max = min(delai_list), max(delai_list)
        if proximite_list:
            proximite_min, proximite_max = min(proximite_list), max(proximite_list)
        
        offres_avec_scores = []
        
        for offre in offres:
            if not offre.get('conforme', True):
                offre['score_final'] = 0
                offres_avec_scores.append(offre)
                continue
            
            scores = {}
            
            # Score Prix (inversé : prix bas = score élevé)
            if criteres_eval.get('prix', {}).get('actif') and prix_list and prix_max > prix_min:
                score_prix = 100 * (prix_max - offre.get('prix_total', 0)) / (prix_max - prix_min)
                scores['prix'] = score_prix
            
            # Score Délai (inversé : délai court = score élevé)
            if criteres_eval.get('delai', {}).get('actif') and delai_list and delai_max > delai_min:
                score_delai = 100 * (delai_max - offre.get('delai_livraison', 0)) / (delai_max - delai_min)
                scores['delai'] = score_delai
            
            # Score Qualité (direct)
            if criteres_eval.get('qualite', {}).get('actif'):
                scores['qualite'] = offre.get('note_qualite', 5) * 10
            
            # Score Proximité (inversé : proche = score élevé)
            if criteres_eval.get('proximite', {}).get('actif') and proximite_list and proximite_max > proximite_min:
                score_proximite = 100 * (proximite_max - offre.get('proximite_km', 0)) / (proximite_max - proximite_min)
                scores['proximite'] = score_proximite
            
            # Score Expérience (direct)
            if criteres_eval.get('experience', {}).get('actif'):
                scores['experience'] = offre.get('experience_secteur', 5) * 10
            
            # Calcul score final pondéré
            score_final = 0
            total_ponderation = 0
            
            for critere, data in criteres_eval.items():
                if data.get('actif') and critere in scores:
                    score_final += scores[critere] * data.get('ponderation', 0) / 100
                    total_ponderation += data.get('ponderation', 0)
            
            if total_ponderation > 0:
                score_final = score_final * 100 / total_ponderation
            
            offre['scores_details'] = scores
            offre['score_final'] = score_final
            offres_avec_scores.append(offre)
        
        return offres_avec_scores
    
    def selectionner_gagnant(self, dp_id: int, fournisseur_gagnant_id: int, justification: str) -> Optional[int]:
        """Sélectionne le fournisseur gagnant et génère automatiquement le BC."""
        try:
            # Récupération des détails de la DP
            dp_details = self.base.get_formulaire_details(dp_id)
            if not dp_details:
                return None
            
            # Mise à jour des métadonnées avec le gagnant
            meta = json.loads(dp_details.get('metadonnees_json', '{}'))
            meta['fournisseur_gagnant'] = fournisseur_gagnant_id
            meta['date_selection'] = datetime.now().isoformat()
            meta['justification_selection'] = justification
            
            # Génération automatique du BC
            bc_id = self._convertir_dp_vers_bc(dp_id, fournisseur_gagnant_id, meta)
            
            if bc_id:
                meta['conversion_bc_id'] = bc_id
                
                # Mise à jour de la DP
                query = """
                    UPDATE formulaires 
                    SET statut = 'TERMINÉ', metadonnees_json = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """
                self.db.execute_update(query, (json.dumps(meta), dp_id))
                
                # Enregistrement de la sélection
                self.base.enregistrer_validation(
                    dp_id,
                    dp_details.get('employee_id'),
                    'SELECTION_GAGNANT',
                    f"Fournisseur {fournisseur_gagnant_id} sélectionné. BC {bc_id} généré. {justification}"
                )
                
                return bc_id
            
            return None
            
        except Exception as e:
            st.error(f"Erreur sélection gagnant: {e}")
            return None
    
    def _convertir_dp_vers_bc(self, dp_id: int, fournisseur_id: int, meta_dp: Dict) -> Optional[int]:
        """Convertit automatiquement une DP en BC pour le fournisseur gagnant."""
        try:
            dp_details = self.base.get_formulaire_details(dp_id)
            if not dp_details:
                return None
            
            # Génération du numéro BC
            numero_bc = self.base.generer_numero_document('BON_COMMANDE')
            
            # Métadonnées BC
            metadonnees_bc = {
                'dp_source_id': dp_id,
                'dp_source_numero': dp_details['numero_document'],
                'fournisseur_gagnant_selection': True,
                'conversion_automatique_dp': True,
                'conditions_rfq': meta_dp.get('conditions_commerciales', {}),
                'criteres_selection': meta_dp.get('criteres_evaluation', {}),
                'justification_selection': meta_dp.get('justification_selection', '')
            }
            
            # Notes BC
            notes_bc = f"""=== BON DE COMMANDE DEPUIS RFQ ===
Généré automatiquement depuis : {dp_details['numero_document']}
Date conversion : {datetime.now().strftime('%d/%m/%Y à %H:%M')}
Fournisseur sélectionné : {fournisseur_id}

=== JUSTIFICATION SÉLECTION ===
{meta_dp.get('justification_selection', 'Sélection automatique selon critères RFQ')}

=== CRITÈRES RFQ ===
Type RFQ : {meta_dp.get('type_rfq', 'N/A')}
Mode évaluation : {meta_dp.get('mode_evaluation', 'N/A')}
Délai réponse : {meta_dp.get('delai_reponse', 'N/A')} jours

=== NOTES DP SOURCE ===
{dp_details.get('notes', '')}"""
            
            # Données du BC
            data_bc = {
                'type_formulaire': 'BON_COMMANDE',
                'numero_document': numero_bc,
                'project_id': dp_details.get('project_id'),
                'company_id': fournisseur_id,  # Fournisseur gagnant
                'employee_id': dp_details.get('employee_id'),
                'statut': 'VALIDÉ',
                'priorite': dp_details.get('priorite'),
                'date_creation': datetime.now().date(),
                'date_echeance': datetime.now().date() + timedelta(days=14),
                'montant_total': dp_details.get('montant_total', 0),
                'notes': notes_bc,
                'metadonnees_json': json.dumps(metadonnees_bc),
                'lignes': dp_details.get('lignes', [])
            }
            
            # Création du BC
            return self.base.creer_formulaire(data_bc)
            
        except Exception as e:
            st.error(f"Erreur conversion DP→BC: {e}")
            return None
    
    def _generer_offres_fictives_pour_comparaison(self, dp_details: Dict, meta: Dict) -> List[Dict]:
        """Génère des offres fictives pour la démonstration."""
        try:
            fournisseurs_invites = meta.get('fournisseurs_invites', [])
            if not fournisseurs_invites:
                return []
            
            # Récupération des fournisseurs
            fournisseurs = get_fournisseurs_actifs()
            fournisseurs_filtres = [f for f in fournisseurs if f['id'] in fournisseurs_invites]
            
            offres = []
            base_price = dp_details.get('montant_total', 10000) or 10000
            
            for i, fournisseur in enumerate(fournisseurs_filtres):
                # Génération d'offre fictive avec variabilité
                note_qualite = self._get_note_fournisseur_fictive(fournisseur['id'])
                price_factor = 1.0 + (10 - note_qualite) * 0.05
                
                offre = {
                    'fournisseur': fournisseur,
                    'prix_total': round(base_price * price_factor * (0.9 + i * 0.1), 2),
                    'delai_livraison': 7 + (i * 5) + (10 - note_qualite),
                    'note_qualite': note_qualite,
                    'proximite_km': 50 + (i * 100),
                    'experience_secteur': max(5, note_qualite - 2),
                    'conforme': i < 3,  # Les 3 premiers sont conformes
                    'conditions_paiement': ['30j net', '45j net', '15j net'][i % 3],
                    'garantie': ['12 mois', '24 mois', '6 mois'][i % 3],
                    'notes': f"Offre standard de {fournisseur['nom']}"
                }
                offres.append(offre)
            
            return offres
            
        except Exception:
            return []
    
    def _get_note_fournisseur_fictive(self, fournisseur_id: int) -> int:
        """Génère une note de qualité fictive pour un fournisseur."""
        # Utilise un hash pour avoir une note constante par fournisseur
        hash_val = int(hashlib.md5(str(fournisseur_id).encode()).hexdigest()[:8], 16)
        return (hash_val % 5) + 6  # Note entre 6 et 10
    
    def _generer_offres_demo(self, dp_id: int, data: Dict) -> None:
        """Génère des offres fictives pour la démonstration."""
        try:
            # Cette fonction serait utilisée pour pré-remplir des offres en mode démo
            pass
        except Exception:
            pass
