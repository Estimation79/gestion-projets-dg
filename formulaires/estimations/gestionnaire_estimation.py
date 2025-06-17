# formulaires/estimations/gestionnaire_estimation.py

"""
Gestionnaire spécialisé pour les Estimations.
Contient la logique métier spécifique aux Devis clients avec calculs automatiques.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from ..core.base_gestionnaire import GestionnaireFormulaires
from ..utils.validations import valider_estimation
from ..utils.helpers import (
    get_projets_actifs,
    get_employes_actifs,
    get_clients_actifs
    # 🔧 CORRECTION : Suppression des imports inexistants
)

class GestionnaireEstimations:
    """
    Gestionnaire spécialisé pour les Estimations.
    
    Gère les opérations spécifiques aux estimations :
    - Templates industrie avec coefficients automatiques
    - Calculs automatiques basés sur projets existants
    - Gestion des versions (v1, v2, v3...)
    - Conversion estimations acceptées → projets
    - Validité temporelle avec alertes d'expiration
    """
    
    # Templates industrie avec paramètres spécifiques
    TEMPLATES_INDUSTRIE = {
        "AUTOMOBILE": {
            "marge_defaut": 15,
            "coefficient_complexite": 1.2,
            "garantie": "12 mois pièces et main d'œuvre",
            "delai_standard": 21,
            "cout_certification_pct": 5,
            "conditions_paiement": "30 jours net",
            "clauses_techniques": [
                "Tolérances selon norme ISO 2768",
                "Matériaux certifiés automotive", 
                "Traçabilité complète exigée"
            ]
        },
        "AERONAUTIQUE": {
            "marge_defaut": 25,
            "coefficient_complexite": 1.5,
            "garantie": "24 mois certification aéro",
            "delai_standard": 45,
            "cout_certification_pct": 15,
            "conditions_paiement": "50% avance + 50% livraison",
            "clauses_techniques": [
                "Conformité AS9100",
                "Matériaux aéronautiques certifiés",
                "Documentation complète CAMO"
            ]
        },
        "CONSTRUCTION": {
            "marge_defaut": 12,
            "coefficient_complexite": 1.1,
            "garantie": "12 mois installation",
            "delai_standard": 14,
            "cout_certification_pct": 2,
            "conditions_paiement": "30 jours net",
            "clauses_techniques": [
                "Normes CNB en vigueur",
                "Résistance structurale certifiée",
                "Finition selon devis architectural"
            ]
        },
        "GENERAL": {
            "marge_defaut": 20,
            "coefficient_complexite": 1.0,
            "garantie": "12 mois standard",
            "delai_standard": 21,
            "cout_certification_pct": 0,
            "conditions_paiement": "30 jours net",
            "clauses_techniques": [
                "Qualité industrielle standard",
                "Conformité normes applicables"
            ]
        }
    }
    
    def __init__(self, gestionnaire_base: GestionnaireFormulaires):
        self.base = gestionnaire_base
        self.db = gestionnaire_base.db
    
    def creer_estimation(self, data: Dict) -> Optional[int]:
        """Crée une nouvelle Estimation avec validations spécifiques."""
        try:
            # Validation spécifique
            is_valid, erreurs = valider_estimation(data)
            if not is_valid:
                for erreur in erreurs:
                    st.error(f"❌ {erreur}")
                return None
            
            # Enrichissement des données
            data['type_formulaire'] = 'ESTIMATION'
            
            # Métadonnées spécifiques estimation
            template_info = self.TEMPLATES_INDUSTRIE.get(data.get('template_industrie', 'GENERAL'))
            
            metadonnees = {
                'template_industrie': data.get('template_industrie', 'GENERAL'),
                'marge_beneficiaire': data.get('marge_beneficiaire', template_info['marge_defaut']),
                'devise_devis': data.get('devise_devis', 'CAD'),
                'validite_devis': data.get('validite_devis', 30),
                'type_estimation': data.get('type_estimation', 'Devis Standard'),
                'conditions_paiement': data.get('conditions_paiement', template_info['conditions_paiement']),
                'garantie_proposee': data.get('garantie_proposee', template_info['garantie']),
                'delai_execution': data.get('delai_execution', template_info['delai_standard']),
                'version': data.get('version', 1),
                'calculs_automatiques': data.get('calculs_automatiques', False),
                'projet_base_id': data.get('projet_base_id'),
                'template_info': template_info,
                'date_creation_estimation': datetime.now().isoformat(),
                'date_validite': data.get('date_validite', (datetime.now().date() + timedelta(days=data.get('validite_devis', 30))).isoformat())
            }
            
            data['metadonnees_json'] = json.dumps(metadonnees)
            
            # Création via gestionnaire base
            estimation_id = self.base.creer_formulaire(data)
            
            if estimation_id:
                self._post_creation_estimation(estimation_id, data)
            
            return estimation_id
            
        except Exception as e:
            st.error(f"Erreur création estimation: {e}")
            return None
    
    def _post_creation_estimation(self, estimation_id: int, data: Dict) -> None:
        """Actions post-création spécifiques aux estimations."""
        try:
            # Enregistrer la création avec template utilisé
            template = data.get('template_industrie', 'GENERAL')
            self.base.enregistrer_validation(
                estimation_id, 
                data.get('employee_id'), 
                'CREATION',
                f"Estimation créée avec template {template}"
            )
            
            # Si basée sur un projet existant, créer le lien
            if data.get('projet_base_id'):
                self._lier_estimation_projet(estimation_id, data['projet_base_id'])
                
        except Exception as e:
            st.warning(f"Actions post-création estimation partiellement échouées: {e}")
    
    def _lier_estimation_projet(self, estimation_id: int, projet_id: int) -> None:
        """Crée le lien entre estimation et projet existant."""
        try:
            # Mise à jour du projet avec référence estimation
            query = "UPDATE projects SET estimation_id = ? WHERE id = ?"
            self.db.execute_update(query, (estimation_id, projet_id))
        except Exception as e:
            st.warning(f"Erreur liaison estimation-projet: {e}")
    
    def get_estimations(self, **filters) -> List[Dict]:
        """Récupère les Estimations avec filtres spécifiques."""
        try:
            # Filtres de base + spécifiques
            estimations = self.base.get_formulaires('ESTIMATION', **filters)
            
            # Enrichissement avec données spécifiques
            for est in estimations:
                est['template_industrie'] = self._get_template_from_metadata(est['id'])
                est['version'] = self._get_version_from_metadata(est['id'])
                est['statut_validite'] = self._get_statut_validite(est['id'])
                est['ca_potentiel'] = est.get('montant_total', 0)
                
            return estimations
            
        except Exception as e:
            st.error(f"Erreur récupération estimations: {e}")
            return []
    
    def get_statistiques_estimation(self) -> Dict:
        """Calcule les statistiques spécifiques aux estimations."""
        try:
            stats_base = self.base.get_statistiques_formulaires().get('ESTIMATION', {})
            
            # Enrichissement spécifique
            query = """
                SELECT 
                    COUNT(CASE WHEN f.statut = 'APPROUVÉ' THEN 1 END) as acceptees,
                    COUNT(CASE WHEN f.statut IN ('VALIDÉ', 'ENVOYÉ') THEN 1 END) as en_negociation,
                    COUNT(CASE WHEN f.date_echeance < DATE('now') AND f.statut NOT IN ('TERMINÉ', 'ANNULÉ') THEN 1 END) as expirees,
                    AVG(f.montant_total) as montant_moyen,
                    SUM(CASE WHEN f.statut = 'APPROUVÉ' THEN f.montant_total ELSE 0 END) as ca_realise
                FROM formulaires f
                WHERE f.type_formulaire = 'ESTIMATION'
            """
            
            result = self.db.execute_query(query)
            if result:
                stats_enrichies = dict(result[0])
                stats_base.update(stats_enrichies)
            
            # Statistiques par template
            stats_base['par_template'] = self._get_stats_par_template()
            
            # Taux de conversion
            total = stats_base.get('total', 0)
            acceptees = stats_base.get('acceptees', 0)
            stats_base['taux_acceptation'] = (acceptees / total * 100) if total > 0 else 0
            
            return stats_base
            
        except Exception as e:
            st.error(f"Erreur stats estimation: {e}")
            return {}
    
    def _get_stats_par_template(self) -> Dict:
        """Statistiques par template industrie."""
        try:
            query = """
                SELECT 
                    JSON_EXTRACT(f.metadonnees_json, '$.template_industrie') as template,
                    COUNT(*) as total,
                    COUNT(CASE WHEN f.statut = 'APPROUVÉ' THEN 1 END) as acceptees,
                    SUM(f.montant_total) as montant_total
                FROM formulaires f
                WHERE f.type_formulaire = 'ESTIMATION'
                AND JSON_EXTRACT(f.metadonnees_json, '$.template_industrie') IS NOT NULL
                GROUP BY template
            """
            
            rows = self.db.execute_query(query)
            stats_template = {}
            
            for row in rows:
                template = row['template'].strip('"') if row['template'] else 'GENERAL'
                stats_template[template] = {
                    'total': row['total'],
                    'acceptees': row['acceptees'],
                    'montant_total': row['montant_total'] or 0,
                    'taux_acceptation': (row['acceptees'] / row['total'] * 100) if row['total'] > 0 else 0
                }
            
            return stats_template
            
        except Exception as e:
            st.warning(f"Erreur stats par template: {e}")
            return {}
    
    def creer_nouvelle_version(self, estimation_base_id: int, motif_revision: str, modifications: Dict) -> Optional[int]:
        """Crée une nouvelle version d'une estimation existante."""
        try:
            # Récupérer l'estimation de base
            est_base = self.base.get_formulaire_details(estimation_base_id)
            if not est_base:
                return None
            
            # Calculer nouveau numéro de version
            nouvelle_version = self._get_prochaine_version(estimation_base_id)
            
            # Récupérer métadonnées actuelles
            meta_actuelles = json.loads(est_base.get('metadonnees_json', '{}'))
            
            # Mise à jour avec modifications
            nouvelles_meta = meta_actuelles.copy()
            nouvelles_meta.update({
                'version': nouvelle_version,
                'version_precedente_id': estimation_base_id,
                'motif_revision': motif_revision,
                'date_revision': datetime.now().isoformat(),
                **modifications
            })
            
            # Générer nouveau numéro
            numero_base = est_base['numero_document'].split(' v')[0]
            nouveau_numero = f"{numero_base} v{nouvelle_version}"
            
            # Construction notes de révision
            notes_revision = f"""=== RÉVISION VERSION {nouvelle_version} ===
Motif : {motif_revision}
Date révision : {datetime.now().strftime('%d/%m/%Y à %H:%M')}
Version précédente : {est_base['numero_document']}

=== MODIFICATIONS ===
{modifications.get('description_modifications', 'Voir métadonnées')}

=== NOTES VERSION PRÉCÉDENTE ===
{est_base.get('notes', '')}"""
            
            # Données nouvelle version
            data_nouvelle_version = {
                'type_formulaire': 'ESTIMATION',
                'numero_document': nouveau_numero,
                'project_id': est_base.get('project_id'),
                'company_id': est_base.get('company_id'),
                'employee_id': est_base.get('employee_id'),
                'statut': 'VALIDÉ',
                'priorite': est_base.get('priorite'),
                'date_creation': datetime.now().date(),
                'date_echeance': datetime.now().date() + timedelta(days=nouvelles_meta.get('validite_devis', 30)),
                'montant_total': modifications.get('nouveau_montant', est_base.get('montant_total', 0)),
                'notes': notes_revision,
                'metadonnees_json': json.dumps(nouvelles_meta),
                'lignes': est_base.get('lignes', [])
            }
            
            # Création nouvelle version
            nouvelle_version_id = self.base.creer_formulaire(data_nouvelle_version)
            
            if nouvelle_version_id:
                # Enregistrer l'action de révision
                self.base.enregistrer_validation(
                    nouvelle_version_id,
                    est_base.get('employee_id'),
                    'CREATION',
                    f"Version {nouvelle_version} créée - {motif_revision}"
                )
            
            return nouvelle_version_id
            
        except Exception as e:
            st.error(f"Erreur création nouvelle version: {e}")
            return None
    
    def convertir_vers_projet(self, estimation_id: int) -> Optional[int]:
        """Convertit une estimation acceptée en nouveau projet."""
        try:
            est_details = self.base.get_formulaire_details(estimation_id)
            if not est_details or est_details['statut'] != 'APPROUVÉ':
                return None
            
            # Récupération métadonnées
            meta = json.loads(est_details.get('metadonnees_json', '{}'))
            
            # Données du nouveau projet
            query = """
                INSERT INTO projects 
                (nom_projet, client_company_id, statut, priorite, prix_estime, 
                 date_soumis, date_prevu, description, estimation_source_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            projet_id = self.db.execute_insert(query, (
                f"Projet depuis {est_details['numero_document']}",
                est_details.get('company_id'),
                'À FAIRE',
                est_details.get('priorite', 'NORMAL'),
                est_details.get('montant_total', 0),
                datetime.now().date(),
                datetime.now().date() + timedelta(days=meta.get('delai_execution', 30)),
                f"Projet généré depuis estimation {est_details['numero_document']}",
                estimation_id
            ))
            
            if projet_id:
                # Mise à jour estimation
                self.base.modifier_statut_formulaire(
                    estimation_id,
                    'TERMINÉ',
                    est_details.get('employee_id'),
                    f"Convertie en projet #{projet_id}"
                )
            
            return projet_id
            
        except Exception as e:
            st.error(f"Erreur conversion projet: {e}")
            return None
    
    def get_estimations_expirees(self) -> List[Dict]:
        """Retourne les estimations expirées ou bientôt expirées."""
        try:
            query = """
                SELECT f.*, c.nom as company_nom, e.prenom || ' ' || e.nom as employee_nom
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN employees e ON f.employee_id = e.id
                WHERE f.type_formulaire = 'ESTIMATION'
                AND f.statut IN ('VALIDÉ', 'ENVOYÉ')
                AND (
                    f.date_echeance <= DATE('now', '+3 days')
                    OR JSON_EXTRACT(f.metadonnees_json, '$.date_validite') <= DATE('now', '+3 days')
                )
                ORDER BY f.date_echeance ASC
            """
            
            rows = self.db.execute_query(query)
            return [dict(row) for row in rows]
            
        except Exception as e:
            st.error(f"Erreur estimations expirées: {e}")
            return []
    
    def calculer_estimation_automatique(self, projet_id: int, template_industrie: str, marge: float) -> Dict:
        """Calcule automatiquement une estimation basée sur un projet existant."""
        try:
            template_info = self.TEMPLATES_INDUSTRIE.get(template_industrie, self.TEMPLATES_INDUSTRIE['GENERAL'])
            
            # Récupérer coûts matériaux depuis BOM projet
            materiaux_query = """
                SELECT SUM(quantite * prix_unitaire) as cout_materiaux
                FROM materials WHERE project_id = ?
            """
            result = self.db.execute_query(materiaux_query, (projet_id,))
            cout_materiaux = result[0]['cout_materiaux'] if result and result[0]['cout_materiaux'] else 0
            
            # Récupérer temps/coûts main d'œuvre
            operations_query = """
                SELECT SUM(o.temps_estime * COALESCE(wc.cout_horaire, 50)) as cout_main_oeuvre
                FROM operations o
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE o.project_id = ?
            """
            result = self.db.execute_query(operations_query, (projet_id,))
            cout_main_oeuvre = result[0]['cout_main_oeuvre'] if result and result[0]['cout_main_oeuvre'] else 0
            
            # Calculs selon template
            coefficient = template_info['coefficient_complexite']
            cout_certification = cout_materiaux * (template_info['cout_certification_pct'] / 100)
            
            cout_direct = (cout_materiaux + cout_main_oeuvre) * coefficient
            cout_indirect = cout_direct * 0.20  # 20% frais généraux
            marge_montant = (cout_direct + cout_indirect) * (marge / 100)
            
            prix_HT = cout_direct + cout_indirect + marge_montant + cout_certification
            taxes = prix_HT * 0.14975  # TVQ + TPS Québec
            prix_TTC = prix_HT + taxes
            
            return {
                'cout_materiaux': cout_materiaux,
                'cout_main_oeuvre': cout_main_oeuvre,
                'cout_certification': cout_certification,
                'cout_direct': cout_direct,
                'cout_indirect': cout_indirect,
                'marge': marge_montant,
                'prix_HT': prix_HT,
                'taxes': taxes,
                'prix_TTC': prix_TTC,
                'template_info': template_info,
                'details': f"Calcul automatique template {template_industrie}"
            }
            
        except Exception as e:
            st.error(f"Erreur calculs automatiques: {e}")
            return {}
    
    # Méthodes utilitaires privées
    def _get_template_from_metadata(self, estimation_id: int) -> str:
        """Extrait le template depuis les métadonnées."""
        try:
            query = "SELECT metadonnees_json FROM formulaires WHERE id = ?"
            result = self.db.execute_query(query, (estimation_id,))
            if result:
                meta = json.loads(result[0]['metadonnees_json'])
                return meta.get('template_industrie', 'GENERAL')
        except:
            pass
        return 'GENERAL'
    
    def _get_version_from_metadata(self, estimation_id: int) -> int:
        """Extrait le numéro de version depuis les métadonnées."""
        try:
            query = "SELECT metadonnees_json FROM formulaires WHERE id = ?"
            result = self.db.execute_query(query, (estimation_id,))
            if result:
                meta = json.loads(result[0]['metadonnees_json'])
                return meta.get('version', 1)
        except:
            pass
        return 1
    
    def _get_statut_validite(self, estimation_id: int) -> str:
        """Calcule le statut de validité d'une estimation."""
        try:
            query = "SELECT metadonnees_json, statut FROM formulaires WHERE id = ?"
            result = self.db.execute_query(query, (estimation_id,))
            if result:
                meta = json.loads(result[0]['metadonnees_json'])
                statut = result[0]['statut']
                
                if statut in ['TERMINÉ', 'ANNULÉ']:
                    return 'Terminée'
                
                date_validite_str = meta.get('date_validite')
                if date_validite_str:
                    date_validite = datetime.strptime(date_validite_str, '%Y-%m-%d').date()
                    today = datetime.now().date()
                    jours_restants = (date_validite - today).days
                    
                    if jours_restants < 0:
                        return f"Expirée ({abs(jours_restants)}j)"
                    elif jours_restants <= 3:
                        return f"Expire dans {jours_restants}j"
                    else:
                        return f"Valide ({jours_restants}j)"
        except:
            pass
        return 'Non définie'
    
    def _get_prochaine_version(self, estimation_base_id: int) -> int:
        """Calcule le prochain numéro de version."""
        try:
            # Récupérer le numéro de base
            query = "SELECT numero_document FROM formulaires WHERE id = ?"
            result = self.db.execute_query(query, (estimation_base_id,))
            if not result:
                return 2
            
            numero_base = result[0]['numero_document'].split(' v')[0]
            
            # Chercher toutes les versions
            query = """
                SELECT numero_document, metadonnees_json FROM formulaires 
                WHERE type_formulaire = 'ESTIMATION'
                AND (numero_document = ? OR numero_document LIKE ?)
            """
            rows = self.db.execute_query(query, (numero_base, f"{numero_base} v%"))
            
            max_version = 1
            for row in rows:
                try:
                    meta = json.loads(row['metadonnees_json'])
                    version = meta.get('version', 1)
                    max_version = max(max_version, version)
                except:
                    # Extraire depuis le numéro si métadonnées invalides
                    if ' v' in row['numero_document']:
                        try:
                            version = int(row['numero_document'].split(' v')[1])
                            max_version = max(max_version, version)
                        except:
                            pass
            
            return max_version + 1
            
        except Exception as e:
            st.warning(f"Erreur calcul prochaine version: {e}")
            return 2
