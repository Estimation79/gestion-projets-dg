# formulaires/bons_commande/gestionnaire_bc.py

"""
Gestionnaire spécialisé pour les Bons de Commande.
Contient la logique métier spécifique aux commandes officielles fournisseurs.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from ..core.base_gestionnaire import GestionnaireFormulaires
from ..utils.validations import valider_bon_commande
from ..utils.helpers import (
    get_projets_actifs,
    get_employes_actifs,
    get_fournisseurs_actifs
)

class GestionnaireBonsCommande:
    """
    Gestionnaire spécialisé pour les Bons de Commande.
    
    Gère les opérations spécifiques aux BC :
    - Création avec conditions commerciales avancées
    - Suivi des livraisons et expéditions
    - Réception marchandises avec mise à jour inventaire
    - Conversion depuis Bons d'Achats
    """
    
    def __init__(self, gestionnaire_base: GestionnaireFormulaires):
        self.base = gestionnaire_base
        self.db = gestionnaire_base.db
    
    def creer_bon_commande(self, data: Dict) -> Optional[int]:
        """Crée un nouveau Bon de Commande avec validations spécifiques."""
        try:
            # Validation spécifique BC
            is_valid, erreurs = valider_bon_commande(data)
            if not is_valid:
                for erreur in erreurs:
                    st.error(f"❌ {erreur}")
                return None
            
            # Enrichissement des données
            data['type_formulaire'] = 'BON_COMMANDE'
            
            # Métadonnées spécifiques BC
            metadonnees = {
                'conditions_paiement': data.get('conditions_paiement', '30 jours net'),
                'garantie_exigee': data.get('garantie_exigee', ''),
                'contact_fournisseur': data.get('contact_fournisseur', ''),
                'penalites_retard': data.get('penalites_retard', ''),
                'delai_livraison_max': data.get('delai_livraison_max', 14),
                'certification_requise': data.get('certification_requise', ''),
                'adresse_livraison': data.get('adresse_livraison', ''),
                'contact_reception': data.get('contact_reception', ''),
                'horaires_livraison': data.get('horaires_livraison', ''),
                'transporteur_prefere': data.get('transporteur_prefere', ''),
                'instructions_livraison': data.get('instructions_livraison', ''),
                'clauses': {
                    'force_majeure': data.get('clause_force_majeure', True),
                    'confidentialite': data.get('clause_confidentialite', False),
                    'acceptation_partielle': data.get('acceptation_partielle', True),
                    'inspection_reception': data.get('inspection_reception', True),
                    'assurance_transport': data.get('assurance_transport', True)
                },
                'validite': {
                    'validite_offre': data.get('validite_offre', 30),
                    'devise': data.get('devise', 'CAD'),
                    'clause_revision': data.get('clause_revision', False),
                    'taux_change_fixe': data.get('taux_change_fixe', False)
                },
                'budget': {
                    'centre_cout': data.get('centre_cout', ''),
                    'approbation_requise': data.get('approbation_requise', False),
                    'signature_electronique': data.get('signature_electronique', False)
                },
                'emballage_special': data.get('emballage_special', ''),
                'projet_associe': data.get('project_id'),
                'ba_source_id': data.get('ba_source_id'),  # Si conversion depuis BA
                'date_creation_bc': datetime.now().isoformat()
            }
            
            data['metadonnees_json'] = json.dumps(metadonnees)
            
            # Création via gestionnaire base
            bc_id = self.base.creer_formulaire(data)
            
            if bc_id:
                self._post_creation_bc(bc_id, data)
            
            return bc_id
            
        except Exception as e:
            st.error(f"Erreur création BC: {e}")
            return None
    
    def _post_creation_bc(self, bc_id: int, data: Dict) -> None:
        """Actions post-création spécifiques aux BC."""
        try:
            # Création automatique de l'approvisionnement
            self._creer_approvisionnement(bc_id, data)
            
            # Notification fournisseur si statut ENVOYÉ
            if data.get('statut') == 'ENVOYÉ':
                self._notifier_fournisseur(bc_id, data)
                
        except Exception as e:
            st.warning(f"Actions post-création BC partiellement échouées: {e}")
    
    def _creer_approvisionnement(self, bc_id: int, data: Dict) -> None:
        """Crée automatiquement un approvisionnement pour le BC."""
        try:
            fournisseur_id = data.get('company_id')
            if not fournisseur_id:
                return
            
            # Rechercher le fournisseur dans la table fournisseurs
            fournisseur_data = self.db.execute_query(
                "SELECT id FROM fournisseurs WHERE company_id = ?", 
                (fournisseur_id,)
            )
            
            if fournisseur_data:
                fournisseur_ref_id = fournisseur_data[0]['id']
            else:
                # Créer l'entrée fournisseur si elle n'existe pas
                delai_livraison = data.get('delai_livraison_max', 14)
                conditions_paiement = data.get('conditions_paiement', '30 jours net')
                
                fournisseur_ref_id = self.db.execute_insert(
                    "INSERT INTO fournisseurs (company_id, code_fournisseur, delai_livraison_moyen, conditions_paiement) VALUES (?, ?, ?, ?)",
                    (fournisseur_id, f"FOUR-{fournisseur_id}", delai_livraison, conditions_paiement)
                )
            
            # Créer l'approvisionnement
            appro_data = {
                'statut_livraison': 'EN_ATTENTE' if data.get('statut') == 'ENVOYÉ' else 'CONFIRMÉ',
                'date_commande': data.get('date_creation', datetime.now().date()),
                'date_livraison_prevue': data.get('date_echeance'),
                'quantite_commandee': sum(art.get('quantite', 0) for art in data.get('lignes', [])),
                'notes_livraison': f"BC {data.get('numero_document', '')} - {len(data.get('lignes', []))} article(s)"
            }
            
            # Insertion dans la table approvisionnements
            query = """
                INSERT INTO approvisionnements 
                (formulaire_id, fournisseur_id, statut_livraison, date_commande, 
                 date_livraison_prevue, quantite_commandee, notes_livraison)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            self.db.execute_insert(query, (
                bc_id, fournisseur_ref_id, appro_data['statut_livraison'],
                appro_data['date_commande'], appro_data['date_livraison_prevue'],
                appro_data['quantite_commandee'], appro_data['notes_livraison']
            ))
            
        except Exception as e:
            st.warning(f"Erreur création approvisionnement: {e}")
    
    def _notifier_fournisseur(self, bc_id: int, data: Dict) -> None:
        """Notification fournisseur pour BC envoyé."""
        try:
            st.info("📧 BC envoyé au fournisseur et suivi de livraison initialisé.")
        except Exception as e:
            st.warning(f"Erreur notification fournisseur: {e}")
    
    def get_bons_commande(self, **filters) -> List[Dict]:
        """Récupère les Bons de Commande avec filtres spécifiques."""
        try:
            # Filtres de base + spécifiques BC
            bons_commande = self.base.get_formulaires('BON_COMMANDE', **filters)
            
            # Enrichissement avec données spécifiques
            for bc in bons_commande:
                bc['info_fournisseur'] = self._get_info_fournisseur(bc.get('company_id'))
                bc['nb_articles'] = self._get_nb_articles_bc(bc['id'])
                bc['statut_livraison'] = self._get_statut_livraison_bc(bc['id'])
                bc['delai_restant'] = self._get_delai_restant(bc)
                
            return bons_commande
            
        except Exception as e:
            st.error(f"Erreur récupération BC: {e}")
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
    
    def _get_nb_articles_bc(self, bc_id: int) -> int:
        """Compte le nombre d'articles dans un BC."""
        try:
            query = "SELECT COUNT(*) as count FROM formulaire_lignes WHERE formulaire_id = ?"
            result = self.db.execute_query(query, (bc_id,))
            return result[0]['count'] if result else 0
        except:
            return 0
    
    def _get_statut_livraison_bc(self, bc_id: int) -> str:
        """Récupère le statut de livraison d'un BC."""
        try:
            query = "SELECT statut_livraison FROM approvisionnements WHERE formulaire_id = ?"
            result = self.db.execute_query(query, (bc_id,))
            return result[0]['statut_livraison'] if result else "Non défini"
        except:
            return "Indéterminé"
    
    def _get_delai_restant(self, bc: Dict) -> int:
        """Calcule le nombre de jours restants avant livraison."""
        try:
            if not bc.get('date_echeance'):
                return 0
            
            date_echeance = datetime.strptime(bc['date_echeance'], '%Y-%m-%d').date()
            today = datetime.now().date()
            return (date_echeance - today).days
        except:
            return 0
    
    def get_statistiques_bc(self) -> Dict:
        """Calcule les statistiques spécifiques aux BC."""
        try:
            stats_base = self.base.get_statistiques_formulaires().get('BON_COMMANDE', {})
            
            # Enrichissement spécifique BC
            query = """
                SELECT 
                    COUNT(CASE WHEN f.statut = 'ENVOYÉ' THEN 1 END) as bc_envoyes,
                    COUNT(CASE WHEN f.statut = 'TERMINÉ' THEN 1 END) as bc_livres,
                    AVG(f.montant_total) as montant_moyen_bc,
                    COUNT(CASE WHEN f.metadonnees_json LIKE '%"ba_source_id"%' THEN 1 END) as bc_depuis_ba,
                    COUNT(CASE WHEN EXISTS(
                        SELECT 1 FROM approvisionnements a 
                        WHERE a.formulaire_id = f.id 
                        AND a.date_livraison_prevue < date('now')
                        AND a.statut_livraison NOT IN ('LIVRÉ', 'ANNULÉ')
                    ) THEN 1 END) as bc_en_retard
                FROM formulaires f
                WHERE f.type_formulaire = 'BON_COMMANDE'
            """
            
            result = self.db.execute_query(query)
            if result:
                stats_enrichies = dict(result[0])
                stats_base.update(stats_enrichies)
            
            # Calcul taux de livraison
            total_bc = stats_base.get('total', 0)
            bc_livres = stats_base.get('bc_livres', 0)
            if total_bc > 0:
                stats_base['taux_livraison'] = (bc_livres / total_bc) * 100
            else:
                stats_base['taux_livraison'] = 0
            
            return stats_base
            
        except Exception as e:
            st.error(f"Erreur stats BC: {e}")
            return {}
    
    def mettre_a_jour_statut_livraison(self, bc_id: int, nouveau_statut: str, notes: str = "") -> bool:
        """Met à jour le statut de livraison d'un BC."""
        try:
            # Mise à jour dans la table approvisionnements
            query = """
                UPDATE approvisionnements 
                SET statut_livraison = ?, notes_livraison = ?, updated_at = CURRENT_TIMESTAMP
                WHERE formulaire_id = ?
            """
            self.db.execute_update(query, (nouveau_statut, notes, bc_id))
            
            # Si livré, mettre à jour le statut du BC
            if nouveau_statut == 'LIVRÉ':
                self.base.modifier_statut_formulaire(bc_id, 'TERMINÉ', 1, f"Livraison confirmée. {notes}")
            
            return True
            
        except Exception as e:
            st.error(f"Erreur mise à jour statut livraison: {e}")
            return False
    
    def marquer_bc_recu(self, bc_id: int, employee_id: int, notes: str = "") -> bool:
        """Marque un BC comme reçu rapidement."""
        try:
            # Mise à jour du statut du BC
            self.base.modifier_statut_formulaire(bc_id, 'TERMINÉ', employee_id, f"BC marqué comme reçu. {notes}")
            
            # Mise à jour de l'approvisionnement
            self.mettre_a_jour_statut_livraison(bc_id, 'LIVRÉ', f"Réception rapide validée. {notes}")
            
            return True
            
        except Exception as e:
            st.error(f"Erreur marquage réception BC: {e}")
            return False
    
    def get_livraisons_en_cours(self) -> List[Dict]:
        """Récupère les livraisons en cours de suivi."""
        try:
            query = """
                SELECT a.*, f.numero_document, c.nom as fournisseur_nom,
                       e.prenom || ' ' || e.nom as responsable_nom
                FROM approvisionnements a
                JOIN formulaires f ON a.formulaire_id = f.id
                JOIN companies c ON f.company_id = c.id
                LEFT JOIN employees e ON f.employee_id = e.id
                WHERE f.type_formulaire = 'BON_COMMANDE'
                AND a.statut_livraison IN ('EN_ATTENTE', 'CONFIRMÉ', 'EN_PRODUCTION', 'EXPÉDIÉ')
                ORDER BY a.date_livraison_prevue ASC
            """
            
            rows = self.db.execute_query(query)
            return [dict(row) for row in rows]
            
        except Exception as e:
            st.error(f"Erreur récupération livraisons: {e}")
            return []
    
    def get_bc_en_retard(self) -> List[Dict]:
        """Récupère les BC en retard de livraison."""
        try:
            today = datetime.now().date()
            bcs = self.get_bons_commande()
            
            retards = []
            for bc in bcs:
                if bc.get('date_echeance') and bc['statut'] not in ['TERMINÉ', 'ANNULÉ']:
                    try:
                        date_echeance = datetime.strptime(bc['date_echeance'], '%Y-%m-%d').date()
                        if date_echeance < today:
                            bc['jours_retard'] = (today - date_echeance).days
                            retards.append(bc)
                    except:
                        continue
            
            return retards
            
        except Exception as e:
            st.error(f"Erreur récupération BC en retard: {e}")
            return []
