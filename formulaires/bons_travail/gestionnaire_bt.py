# formulaires/bons_travail/gestionnaire_bt.py
# Gestionnaire spécialisé pour les Bons de Travail

"""
Gestionnaire spécialisé pour les Bons de Travail (BT).
Contient la logique métier spécifique aux documents de travail interne.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from ..core.base_gestionnaire import GestionnaireFormulaires
from ..utils.validations import valider_bon_travail
from ..utils.helpers import (
    get_projets_actifs,
    get_employes_actifs,
    get_operations_projet,
    get_materiaux_projet,
    get_work_centers_actifs
)


class GestionnaireBonsTravail:
    """
    Gestionnaire spécialisé pour les Bons de Travail.
    
    Gère les opérations spécifiques aux BT :
    - Création avec validation projet obligatoire
    - Gestion des équipes assignées
    - Suivi des opérations et matériaux
    - Interface avec les postes de travail
    """
    
    def __init__(self, gestionnaire_base: GestionnaireFormulaires):
        """
        Initialise le gestionnaire spécialisé.
        
        Args:
            gestionnaire_base: Instance du gestionnaire de base
        """
        self.base = gestionnaire_base
        self.db = gestionnaire_base.db
    
    def creer_bon_travail(self, data: Dict) -> Optional[int]:
        """
        Crée un nouveau Bon de Travail avec validations spécifiques.
        
        Args:
            data: Données du bon de travail
            
        Returns:
            int: ID du BT créé ou None si erreur
        """
        try:
            # Validation spécifique BT
            is_valid, erreurs = valider_bon_travail(data)
            if not is_valid:
                for erreur in erreurs:
                    st.error(f"❌ {erreur}")
                return None
            
            # Enrichissement des données BT
            data['type_formulaire'] = 'BON_TRAVAIL'
            
            # Métadonnées spécifiques BT
            metadonnees_bt = {
                'operations_selectionnees': data.get('operations_selectionnees', []),
                'employes_assignes': data.get('employes_assignes', []),
                'work_centers_utilises': data.get('work_centers_utilises', []),
                'temps_estime_total': data.get('temps_estime_total', 0),
                'cout_main_oeuvre_estime': data.get('cout_main_oeuvre_estime', 0),
                'date_creation_bt': datetime.now().isoformat()
            }
            
            data['metadonnees_json'] = json.dumps(metadonnees_bt)
            
            # Création via le gestionnaire de base
            bt_id = self.base.creer_formulaire(data)
            
            if bt_id:
                # Actions post-création spécifiques BT
                self._post_creation_bt(bt_id, data)
            
            return bt_id
            
        except Exception as e:
            st.error(f"Erreur création BT: {e}")
            return None
    
    def _post_creation_bt(self, bt_id: int, data: Dict) -> None:
        """
        Actions post-création spécifiques aux BT.
        
        Args:
            bt_id: ID du BT créé
            data: Données originales du BT
        """
        try:
            # Assignation automatique aux employés
            employes_assignes = data.get('employes_assignes', [])
            if employes_assignes:
                self._assigner_employes_bt(bt_id, employes_assignes)
            
            # Réservation des postes de travail si spécifiés
            work_centers = data.get('work_centers_utilises', [])
            if work_centers:
                self._reserver_postes_travail(bt_id, work_centers, data.get('date_echeance'))
            
            # Mise à jour du statut du projet si applicable
            if data.get('project_id'):
                self._mettre_a_jour_statut_projet(data['project_id'], bt_id)
                
        except Exception as e:
            st.warning(f"Actions post-création BT partiellement échouées: {e}")
    
    def _assigner_employes_bt(self, bt_id: int, employes_ids: List[int]) -> None:
        """
        Assigne des employés au BT.
        
        Args:
            bt_id: ID du BT
            employes_ids: Liste des IDs employés à assigner
        """
        try:
            for employe_id in employes_ids:
                query = """
                    INSERT INTO bt_assignations (bt_id, employe_id, date_assignation, statut)
                    VALUES (?, ?, CURRENT_TIMESTAMP, 'ASSIGNÉ')
                """
                self.db.execute_insert(query, (bt_id, employe_id))
                
        except Exception as e:
            st.warning(f"Erreur assignation employés: {e}")
    
    def _reserver_postes_travail(self, bt_id: int, work_centers: List[int], 
                                date_prevue: Optional[str]) -> None:
        """
        Réserve des postes de travail pour le BT.
        
        Args:
            bt_id: ID du BT
            work_centers: Liste des IDs postes de travail
            date_prevue: Date prévue d'utilisation
        """
        try:
            for wc_id in work_centers:
                query = """
                    INSERT INTO bt_reservations_postes 
                    (bt_id, work_center_id, date_reservation, date_prevue, statut)
                    VALUES (?, ?, CURRENT_TIMESTAMP, ?, 'RÉSERVÉ')
                """
                self.db.execute_insert(query, (bt_id, wc_id, date_prevue))
                
        except Exception as e:
            st.warning(f"Erreur réservation postes: {e}")
    
    def _mettre_a_jour_statut_projet(self, project_id: int, bt_id: int) -> None:
        """
        Met à jour le statut du projet associé.
        
        Args:
            project_id: ID du projet
            bt_id: ID du BT créé
        """
        try:
            # Vérifier si c'est le premier BT du projet
            query = """
                SELECT COUNT(*) as count FROM formulaires 
                WHERE project_id = ? AND type_formulaire = 'BON_TRAVAIL'
            """
            result = self.db.execute_query(query, (project_id,))
            
            if result and result[0]['count'] == 1:  # Premier BT
                # Mettre le projet en cours
                query_update = """
                    UPDATE projects SET statut = 'EN COURS', date_debut_reel = CURRENT_DATE 
                    WHERE id = ? AND statut = 'À FAIRE'
                """
                self.db.execute_update(query_update, (project_id,))
                
        except Exception as e:
            st.warning(f"Erreur mise à jour projet: {e}")
    
    def get_bons_travail(self, **filters) -> List[Dict]:
        """
        Récupère les Bons de Travail avec filtres spécifiques.
        
        Args:
            **filters: Filtres optionnels (project_id, employe_id, statut, etc.)
            
        Returns:
            List[Dict]: Liste des BT avec informations enrichies
        """
        try:
            # Filtres de base + spécifiques BT
            bts = self.base.get_formulaires('BON_TRAVAIL', **filters)
            
            # Enrichissement avec données spécifiques BT
            for bt in bts:
                bt['assignations'] = self._get_assignations_bt(bt['id'])
                bt['reservations_postes'] = self._get_reservations_postes_bt(bt['id'])
                bt['avancement'] = self._calculer_avancement_bt(bt['id'])
                
            return bts
            
        except Exception as e:
            st.error(f"Erreur récupération BT: {e}")
            return []
    
    def _get_assignations_bt(self, bt_id: int) -> List[Dict]:
        """
        Récupère les assignations d'employés pour un BT.
        
        Args:
            bt_id: ID du BT
            
        Returns:
            List[Dict]: Liste des assignations
        """
        try:
            query = """
                SELECT a.*, e.prenom || ' ' || e.nom as employe_nom, e.poste
                FROM bt_assignations a
                JOIN employees e ON a.employe_id = e.id
                WHERE a.bt_id = ?
                ORDER BY a.date_assignation
            """
            rows = self.db.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
        except:
            return []
    
    def _get_reservations_postes_bt(self, bt_id: int) -> List[Dict]:
        """
        Récupère les réservations de postes pour un BT.
        
        Args:
            bt_id: ID du BT
            
        Returns:
            List[Dict]: Liste des réservations
        """
        try:
            query = """
                SELECT r.*, w.nom as poste_nom, w.departement
                FROM bt_reservations_postes r
                JOIN work_centers w ON r.work_center_id = w.id
                WHERE r.bt_id = ?
                ORDER BY r.date_prevue
            """
            rows = self.db.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
        except:
            return []
    
    def _calculer_avancement_bt(self, bt_id: int) -> Dict:
        """
        Calcule l'avancement d'un BT.
        
        Args:
            bt_id: ID du BT
            
        Returns:
            Dict: Informations d'avancement
        """
        try:
            # Récupérer les opérations associées
            bt_details = self.base.get_formulaire_details(bt_id)
            if not bt_details:
                return {'pourcentage': 0, 'operations_terminees': 0, 'operations_totales': 0}
            
            try:
                metadonnees = json.loads(bt_details.get('metadonnees_json', '{}'))
                operations_ids = metadonnees.get('operations_selectionnees', [])
            except:
                operations_ids = []
            
            if not operations_ids:
                return {'pourcentage': 0, 'operations_terminees': 0, 'operations_totales': 0}
            
            # Compter les opérations terminées (logique simplifiée)
            operations_terminees = len([op for op in operations_ids if self._operation_terminee(op)])
            operations_totales = len(operations_ids)
            
            pourcentage = (operations_terminees / operations_totales * 100) if operations_totales > 0 else 0
            
            return {
                'pourcentage': round(pourcentage, 1),
                'operations_terminees': operations_terminees,
                'operations_totales': operations_totales
            }
            
        except Exception:
            return {'pourcentage': 0, 'operations_terminees': 0, 'operations_totales': 0}
    
    def _operation_terminee(self, operation_id: int) -> bool:
        """
        Vérifie si une opération est terminée (logique simplifiée).
        
        Args:
            operation_id: ID de l'opération
            
        Returns:
            bool: True si terminée
        """
        try:
            query = "SELECT statut FROM operations WHERE id = ?"
            result = self.db.execute_query(query, (operation_id,))
            return result and result[0]['statut'] == 'TERMINÉ'
        except:
            return False
    
    def marquer_bt_termine(self, bt_id: int, employe_id: int, 
                          commentaires: str = "") -> bool:
        """
        Marque un BT comme terminé avec validations.
        
        Args:
            bt_id: ID du BT
            employe_id: ID de l'employé qui termine
            commentaires: Commentaires de fin
            
        Returns:
            bool: True si succès
        """
        try:
            # Validation : vérifier que l'employé est assigné ou responsable
            if not self._employe_peut_terminer_bt(bt_id, employe_id):
                st.error("Seuls les employés assignés peuvent terminer ce BT")
                return False
            
            # Marquer terminé
            success = self.base.modifier_statut_formulaire(
                bt_id, 'TERMINÉ', employe_id,
                f"BT terminé. {commentaires}"
            )
            
            if success:
                # Libérer les réservations de postes
                self._liberer_reservations_postes(bt_id)
                
                # Vérifier si tous les BT du projet sont terminés
                self._verifier_completion_projet(bt_id)
            
            return success
            
        except Exception as e:
            st.error(f"Erreur fin BT: {e}")
            return False
    
    def _employe_peut_terminer_bt(self, bt_id: int, employe_id: int) -> bool:
        """
        Vérifie si un employé peut terminer le BT.
        
        Args:
            bt_id: ID du BT
            employe_id: ID de l'employé
            
        Returns:
            bool: True si autorisé
        """
        try:
            # Responsable du BT
            bt_details = self.base.get_formulaire_details(bt_id)
            if bt_details and bt_details.get('employee_id') == employe_id:
                return True
            
            # Employé assigné
            assignations = self._get_assignations_bt(bt_id)
            employes_assignes = [a['employe_id'] for a in assignations]
            
            return employe_id in employes_assignes
            
        except:
            return False
    
    def _liberer_reservations_postes(self, bt_id: int) -> None:
        """
        Libère les réservations de postes d'un BT terminé.
        
        Args:
            bt_id: ID du BT terminé
        """
        try:
            query = """
                UPDATE bt_reservations_postes 
                SET statut = 'LIBÉRÉ', date_liberation = CURRENT_TIMESTAMP
                WHERE bt_id = ? AND statut = 'RÉSERVÉ'
            """
            self.db.execute_update(query, (bt_id,))
        except Exception as e:
            st.warning(f"Erreur libération postes: {e}")
    
    def _verifier_completion_projet(self, bt_id: int) -> None:
        """
        Vérifie si le projet est complètement terminé.
        
        Args:
            bt_id: ID du BT qui vient d'être terminé
        """
        try:
            bt_details = self.base.get_formulaire_details(bt_id)
            project_id = bt_details.get('project_id')
            
            if not project_id:
                return
            
            # Compter les BT non terminés du projet
            query = """
                SELECT COUNT(*) as count FROM formulaires 
                WHERE project_id = ? AND type_formulaire = 'BON_TRAVAIL' 
                AND statut NOT IN ('TERMINÉ', 'ANNULÉ')
            """
            result = self.db.execute_query(query, (project_id,))
            
            if result and result[0]['count'] == 0:
                # Tous les BT sont terminés, marquer le projet comme terminé
                query_update = """
                    UPDATE projects SET statut = 'TERMINÉ', date_fin_reel = CURRENT_DATE
                    WHERE id = ?
                """
                self.db.execute_update(query_update, (project_id,))
                
                st.success(f"🎉 Projet #{project_id} automatiquement marqué comme terminé!")
                
        except Exception as e:
            st.warning(f"Erreur vérification projet: {e}")
    
    def get_statistiques_bt(self) -> Dict:
        """
        Calcule les statistiques spécifiques aux BT.
        
        Returns:
            Dict: Statistiques BT enrichies
        """
        try:
            # Statistiques de base
            stats_base = self.base.get_statistiques_formulaires().get('BON_TRAVAIL', {})
            
            # Enrichissement avec données BT spécifiques
            query = """
                SELECT 
                    COUNT(CASE WHEN f.statut = 'EN COURS' THEN 1 END) as en_cours,
                    AVG(julianday('now') - julianday(f.date_creation)) as duree_moyenne,
                    COUNT(DISTINCT f.project_id) as projets_concernes,
                    COUNT(DISTINCT f.employee_id) as employes_impliques
                FROM formulaires f
                WHERE f.type_formulaire = 'BON_TRAVAIL'
            """
            
            result = self.db.execute_query(query)
            if result:
                stats_enrichies = dict(result[0])
                stats_base.update(stats_enrichies)
            
            return stats_base
            
        except Exception as e:
            st.error(f"Erreur stats BT: {e}")
            return {}
    
    def generer_rapport_productivite(self, periode_jours: int = 30) -> Dict:
        """
        Génère un rapport de productivité des BT.
        
        Args:
            periode_jours: Période d'analyse en jours
            
        Returns:
            Dict: Rapport de productivité
        """
        try:
            date_debut = datetime.now() - timedelta(days=periode_jours)
            
            query = """
                SELECT 
                    e.prenom || ' ' || e.nom as employe_nom,
                    COUNT(f.id) as nb_bt_termines,
                    AVG(julianday(f.updated_at) - julianday(f.date_creation)) as duree_moyenne,
                    SUM(f.montant_total) as montant_total_travaux
                FROM formulaires f
                JOIN employees e ON f.employee_id = e.id
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                AND f.statut = 'TERMINÉ'
                AND f.updated_at >= ?
                GROUP BY f.employee_id, e.prenom, e.nom
                ORDER BY nb_bt_termines DESC
            """
            
            rows = self.db.execute_query(query, (date_debut.isoformat(),))
            
            rapport = {
                'periode': f"{periode_jours} derniers jours",
                'date_generation': datetime.now().isoformat(),
                'employes': [dict(row) for row in rows],
                'total_bt_termines': sum(row['nb_bt_termines'] for row in rows),
                'duree_moyenne_globale': sum(row['duree_moyenne'] or 0 for row in rows) / len(rows) if rows else 0
            }
            
            return rapport
            
        except Exception as e:
            st.error(f"Erreur rapport productivité: {e}")
            return {}
