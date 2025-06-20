# formulaires/bons_travail/gestionnaire_bt.py
# Gestionnaire spécialisé pour les Bons de Travail - VERSION CORRIGÉE AVEC INSERTION OPÉRATIONS

"""
Gestionnaire spécialisé pour les Bons de Travail (BT).
Contient la logique métier spécifique aux documents de travail interne.
VERSION CORRIGÉE : Gère l'insertion des opérations dans la table 'operations'
ÉTAPE 3 : Intégration complète TimeTracker ↔ Bons de Travail
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
    Gestionnaire spécialisé pour les Bons de Travail - VERSION ÉTAPE 3 COMPLÈTE
    
    Gère les opérations spécifiques aux BT :
    - Création avec validation projet obligatoire
    - Gestion des équipes assignées
    - Suivi des opérations et matériaux
    - Interface avec les postes de travail
    - Gestion robuste des erreurs de base de données
    - ÉTAPE 3 : Intégration complète avec TimeTracker
    - CORRECTION : Insertion réelle des opérations en base
    """
    
    def __init__(self, gestionnaire_base: GestionnaireFormulaires):
        """
        Initialise le gestionnaire spécialisé - VERSION CORRIGÉE
        
        Args:
            gestionnaire_base: Instance du gestionnaire de base
        """
        self.base = gestionnaire_base
        self.db = gestionnaire_base.db
        
        # NOUVEAU : Vérifier et créer l'infrastructure BT complète
        self._ensure_bt_infrastructure()
    
    def _ensure_bt_infrastructure(self):
        """
        S'assurer que toute l'infrastructure BT est en place
        """
        try:
            # 1. Vérifier et corriger les colonnes projects
            self._check_and_fix_projects_columns()
            
            # 2. Créer les tables BT spécialisées si manquantes
            self._create_bt_tables()
            
            # 3. Vérifier l'intégrité des données
            self._verify_bt_data_integrity()
            
        except Exception as e:
            st.warning(f"Avertissement infrastructure BT: {e}")
    
    def _check_and_fix_projects_columns(self):
        """
        Vérifier et ajouter les colonnes manquantes dans la table projects
        """
        try:
            # Vérifier les colonnes existantes
            schema_query = "PRAGMA table_info(projects)"
            columns = self.db.execute_query(schema_query)
            existing_columns = [col['name'] for col in columns]
            
            columns_added = False
            
            # Ajouter date_debut_reel si manquante
            if 'date_debut_reel' not in existing_columns:
                self.db.execute_update("ALTER TABLE projects ADD COLUMN date_debut_reel DATE")
                print("✅ Colonne date_debut_reel ajoutée à projects")
                columns_added = True
            
            # Ajouter date_fin_reel si manquante
            if 'date_fin_reel' not in existing_columns:
                self.db.execute_update("ALTER TABLE projects ADD COLUMN date_fin_reel DATE")
                print("✅ Colonne date_fin_reel ajoutée à projects")
                columns_added = True
            
            if columns_added:
                st.info("🔧 Colonnes de dates réelles ajoutées à la table projects")
                
        except Exception as e:
            print(f"Erreur vérification colonnes projects: {e}")
            # Continuer sans bloquer
    
    def _create_bt_tables(self):
        """
        Créer les tables spécifiques aux BT si elles n'existent pas
        """
        try:
            # Table des assignations d'employés aux BT
            self.db.execute_update("""
                CREATE TABLE IF NOT EXISTS bt_assignations (
                    id INTEGER PRIMARY KEY,
                    bt_id INTEGER NOT NULL,
                    employe_id INTEGER NOT NULL,
                    date_assignation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    statut TEXT DEFAULT 'ASSIGNÉ',
                    role_bt TEXT DEFAULT 'MEMBRE_ÉQUIPE',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bt_id) REFERENCES formulaires(id) ON DELETE CASCADE,
                    FOREIGN KEY (employe_id) REFERENCES employees(id)
                )
            """)
            
            # Table des réservations de postes de travail
            self.db.execute_update("""
                CREATE TABLE IF NOT EXISTS bt_reservations_postes (
                    id INTEGER PRIMARY KEY,
                    bt_id INTEGER NOT NULL,
                    work_center_id INTEGER NOT NULL,
                    date_reservation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date_prevue DATE,
                    date_liberation TIMESTAMP,
                    statut TEXT DEFAULT 'RÉSERVÉ',
                    priorite TEXT DEFAULT 'NORMAL',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bt_id) REFERENCES formulaires(id) ON DELETE CASCADE,
                    FOREIGN KEY (work_center_id) REFERENCES work_centers(id)
                )
            """)
            
            # Table de suivi de l'avancement des BT
            self.db.execute_update("""
                CREATE TABLE IF NOT EXISTS bt_avancement (
                    id INTEGER PRIMARY KEY,
                    bt_id INTEGER NOT NULL,
                    operation_id INTEGER,
                    pourcentage_realise REAL DEFAULT 0.0,
                    temps_reel REAL DEFAULT 0.0,
                    date_debut_reel TIMESTAMP,
                    date_fin_reel TIMESTAMP,
                    notes_avancement TEXT,
                    updated_by INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bt_id) REFERENCES formulaires(id) ON DELETE CASCADE,
                    FOREIGN KEY (operation_id) REFERENCES operations(id),
                    FOREIGN KEY (updated_by) REFERENCES employees(id)
                )
            """)
            
            # Index pour optimisation des requêtes BT
            self.db.execute_update("CREATE INDEX IF NOT EXISTS idx_bt_assignations_bt ON bt_assignations(bt_id)")
            self.db.execute_update("CREATE INDEX IF NOT EXISTS idx_bt_assignations_employe ON bt_assignations(employe_id)")
            self.db.execute_update("CREATE INDEX IF NOT EXISTS idx_bt_reservations_bt ON bt_reservations_postes(bt_id)")
            self.db.execute_update("CREATE INDEX IF NOT EXISTS idx_bt_reservations_poste ON bt_reservations_postes(work_center_id)")
            self.db.execute_update("CREATE INDEX IF NOT EXISTS idx_bt_avancement_bt ON bt_avancement(bt_id)")
            
            print("✅ Tables BT créées/vérifiées avec succès")
            
        except Exception as e:
            print(f"Erreur création tables BT: {e}")
            # Continuer sans bloquer
    
    def _verify_bt_data_integrity(self):
        """
        Vérifier l'intégrité des données BT
        """
        try:
            # Vérifier que les formulaires BT existent
            bt_count = self.db.execute_query(
                "SELECT COUNT(*) as count FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL'"
            )
            
            if bt_count and bt_count[0]['count'] > 0:
                print(f"✅ {bt_count[0]['count']} Bon(s) de Travail trouvé(s) en base")
            
        except Exception as e:
            print(f"Erreur vérification intégrité BT: {e}")
    
    def creer_bon_travail(self, data: Dict) -> Optional[int]:
        """
        Crée un nouveau Bon de Travail avec validation et insertion des opérations.
        VERSION CORRIGÉE : Insère réellement les opérations dans la table 'operations'
        
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
            
            # Métadonnées BT sans les opérations détaillées qui seront en base
            metadonnees_bt = {
                'temps_estime_total': data.get('temps_estime_total', 0),
                'cout_main_oeuvre_estime': data.get('cout_main_oeuvre_estime', 0),
                'date_creation_bt': datetime.now().isoformat(),
                'version_bt': '2.1'  # Version corrigée
            }
            
            data['metadonnees_json'] = json.dumps(metadonnees_bt)
            
            # Création du formulaire de base pour obtenir un ID
            bt_id = self.base.creer_formulaire(data)
            
            if bt_id:
                # CORRECTION MAJEURE : Insérer les opérations dans la table 'operations'
                operations_creees_ids = self._inserer_operations_bt(bt_id, data)

                # Actions post-création avec les IDs des opérations réelles
                self._post_creation_bt(bt_id, data, operations_creees_ids)
                
                # Log de création
                print(f"✅ BT #{bt_id} créé avec succès - {data.get('numero_document', 'N/A')}")
            
            return bt_id
            
        except Exception as e:
            st.error(f"Erreur création BT: {e}")
            print(f"❌ Erreur détaillée création BT: {e}")
            return None

    def _inserer_operations_bt(self, bt_id: int, data: Dict) -> List[int]:
        """
        Insère les opérations définies dans le BT dans la table 'operations'.
        VERSION CORRIGÉE ET ROBUSTE
        
        Args:
            bt_id (int): ID du formulaire BT parent.
            data (Dict): Données complètes du BT contenant 'operations_detaillees'.

        Returns:
            List[int]: Liste des IDs des opérations créées.
        """
        operations_creees_ids = []
        operations_data = data.get('operations_detaillees', [])
        project_id = data.get('project_id')
        
        if not operations_data:
            print(f"ℹ️ Aucune opération détaillée à insérer pour BT #{bt_id}")
            return []
        
        for i, op_data in enumerate(operations_data):
            work_center_id = None
            poste_nom = op_data.get('poste_travail')
            
            if not op_data.get('description'):  # Ignorer les opérations vides
                continue
            
            if poste_nom:
                # Logique de recherche d'ID plus robuste
                poste_clean = poste_nom.split(' (')[0].strip()
                wc_result = self.db.execute_query(
                    "SELECT id FROM work_centers WHERE nom = ?", (poste_clean,)
                )
                if wc_result:
                    work_center_id = wc_result[0]['id']
                else:
                    st.warning(f"Opération {i+1} : Poste de travail '{poste_clean}' non trouvé. L'opération sera créée sans poste lié.")
            
            try:
                query = """
                    INSERT INTO operations 
                    (project_id, formulaire_bt_id, work_center_id, description, 
                     temps_estime, ressource, statut, poste_travail, sequence_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    project_id,
                    bt_id,
                    work_center_id,
                    op_data.get('description'),
                    op_data.get('temps_prevu', 0.0),
                    op_data.get('assigne'),
                    op_data.get('statut', 'À FAIRE'),
                    op_data.get('poste_travail'),
                    (i + 1) * 10  # Générer un numéro de séquence automatique
                )
                
                op_id = self.db.execute_insert(query, params)
                if op_id:
                    operations_creees_ids.append(op_id)
                    print(f"✅ Opération '{op_data.get('description')}' insérée avec ID #{op_id}")
            
            except Exception as e:
                st.error(f"Impossible d'insérer l'opération '{op_data.get('description')}': {e}")
                print(f"❌ Erreur insertion opération: {e}")
                continue
        
        print(f"✅ {len(operations_creees_ids)} opération(s) insérée(s) pour le BT #{bt_id}")
        return operations_creees_ids

    def _post_creation_bt(self, bt_id: int, data: Dict, operations_creees_ids: List[int] = None) -> None:
        """
        Actions post-création spécifiques aux BT.
        VERSION CORRIGÉE : Prend en compte les IDs des opérations réellement créées.
        
        Args:
            bt_id: ID du BT créé
            data: Données originales du BT
            operations_creees_ids: IDs des opérations insérées dans la DB
        """
        try:
            # 1. Assignation automatique aux employés
            employes_assignes = data.get('employes_assignes', [])
            if employes_assignes:
                self._assigner_employes_bt(bt_id, employes_assignes)
            
            # 2. Réservation des postes de travail si spécifiés
            work_centers = data.get('work_centers_utilises', [])
            if work_centers:
                # Convertir les noms de postes en IDs
                wc_ids_to_reserve = []
                for wc_name in work_centers:
                    wc_clean = wc_name.split(' (')[0]  # Nettoyer le nom
                    wc_result = self.db.execute_query(
                        "SELECT id FROM work_centers WHERE nom = ?", (wc_clean,)
                    )
                    if wc_result:
                        wc_ids_to_reserve.append(wc_result[0]['id'])
                
                self._reserver_postes_travail(bt_id, wc_ids_to_reserve, data.get('date_echeance'))
            
            # 3. Initialisation du suivi d'avancement avec les vrais IDs d'opérations
            if operations_creees_ids:
                self._initialiser_avancement_bt(bt_id, operations_creees_ids)
            
            # 4. Mise à jour du statut du projet si applicable
            if data.get('project_id'):
                self._mettre_a_jour_statut_projet(data['project_id'], bt_id)
            
            print(f"✅ Actions post-création BT #{bt_id} terminées")
                
        except Exception as e:
            st.warning(f"Actions post-création BT partiellement échouées: {e}")
            print(f"⚠️ Erreur post-création BT: {e}")
    
    def _assigner_employes_bt(self, bt_id: int, employes_ids: List[int]) -> None:
        """
        Assigne des employés au BT avec traçabilité complète.
        
        Args:
            bt_id: ID du BT
            employes_ids: Liste des IDs employés à assigner
        """
        try:
            assignations_creees = 0
            
            for employe_id in employes_ids:
                # Vérifier si l'employé existe
                employe_exists = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM employees WHERE id = ?",
                    (employe_id,)
                )
                
                if employe_exists and employe_exists[0]['count'] > 0:
                    query = """
                        INSERT INTO bt_assignations (bt_id, employe_id, date_assignation, statut, role_bt)
                        VALUES (?, ?, CURRENT_TIMESTAMP, 'ASSIGNÉ', 'MEMBRE_ÉQUIPE')
                    """
                    self.db.execute_insert(query, (bt_id, employe_id))
                    assignations_creees += 1
                else:
                    st.warning(f"Employé ID {employe_id} non trouvé - assignation ignorée")
            
            if assignations_creees > 0:
                print(f"✅ {assignations_creees} employé(s) assigné(s) au BT #{bt_id}")
                
        except Exception as e:
            st.warning(f"Erreur assignation employés: {e}")
            print(f"❌ Erreur assignation employés BT: {e}")
    
    def _reserver_postes_travail(self, bt_id: int, work_centers: List[int], 
                                date_prevue: Optional[str]) -> None:
        """
        Réserve des postes de travail pour le BT avec validation.
        
        Args:
            bt_id: ID du BT
            work_centers: Liste des IDs postes de travail
            date_prevue: Date prévue d'utilisation
        """
        try:
            reservations_creees = 0
            
            for wc_id in work_centers:
                # Vérifier si le poste existe
                poste_exists = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM work_centers WHERE id = ?",
                    (wc_id,)
                )
                
                if poste_exists and poste_exists[0]['count'] > 0:
                    query = """
                        INSERT INTO bt_reservations_postes 
                        (bt_id, work_center_id, date_reservation, date_prevue, statut)
                        VALUES (?, ?, CURRENT_TIMESTAMP, ?, 'RÉSERVÉ')
                    """
                    self.db.execute_insert(query, (bt_id, wc_id, date_prevue))
                    reservations_creees += 1
                else:
                    st.warning(f"Poste de travail ID {wc_id} non trouvé - réservation ignorée")
            
            if reservations_creees > 0:
                print(f"✅ {reservations_creees} poste(s) réservé(s) pour BT #{bt_id}")
                
        except Exception as e:
            st.warning(f"Erreur réservation postes: {e}")
            print(f"❌ Erreur réservation postes BT: {e}")
    
    def _initialiser_avancement_bt(self, bt_id: int, operations_ids: List[int]) -> None:
        """
        Initialise le suivi d'avancement pour les opérations du BT.
        
        Args:
            bt_id: ID du BT
            operations_ids: Liste des IDs opérations
        """
        try:
            avancements_crees = 0
            
            for operation_id in operations_ids:
                # Vérifier si l'opération existe
                operation_exists = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM operations WHERE id = ?",
                    (operation_id,)
                )
                
                if operation_exists and operation_exists[0]['count'] > 0:
                    query = """
                        INSERT INTO bt_avancement 
                        (bt_id, operation_id, pourcentage_realise, temps_reel)
                        VALUES (?, ?, 0.0, 0.0)
                    """
                    self.db.execute_insert(query, (bt_id, operation_id))
                    avancements_crees += 1
            
            if avancements_crees > 0:
                print(f"✅ Suivi avancement initialisé pour {avancements_crees} opération(s)")
                
        except Exception as e:
            print(f"❌ Erreur initialisation avancement: {e}")
    
    def _mettre_a_jour_statut_projet(self, project_id: int, bt_id: int) -> None:
        """
        Met à jour le statut du projet associé - VERSION CORRIGÉE ROBUSTE
        
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
                # CORRECTION ROBUSTE : Gestion sécurisée des colonnes
                try:
                    # Tenter mise à jour avec colonnes complètes
                    query_update = """
                        UPDATE projects 
                        SET statut = 'EN COURS', 
                            date_debut_reel = CURRENT_DATE,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND statut = 'À FAIRE'
                    """
                    affected = self.db.execute_update(query_update, (project_id,))
                    
                    if affected > 0:
                        st.info(f"✅ Projet #{project_id} automatiquement démarré (EN COURS)")
                        print(f"✅ Projet #{project_id} mis à jour: À FAIRE → EN COURS")
                    else:
                        print(f"ℹ️ Projet #{project_id} déjà en cours ou statut différent")
                        
                except Exception as e_col:
                    # Si erreur avec les nouvelles colonnes, essayer mise à jour basique
                    if "no such column" in str(e_col).lower():
                        print("⚠️ Colonnes date_debut_reel manquantes - mise à jour basique")
                        
                        query_update_basic = """
                            UPDATE projects 
                            SET statut = 'EN COURS', updated_at = CURRENT_TIMESTAMP
                            WHERE id = ? AND statut = 'À FAIRE'
                        """
                        affected = self.db.execute_update(query_update_basic, (project_id,))
                        
                        if affected > 0:
                            st.info(f"✅ Projet #{project_id} marqué EN COURS (mise à jour basique)")
                            print(f"✅ Projet #{project_id} mis à jour (basique): À FAIRE → EN COURS")
                    else:
                        # Autre erreur, la propager
                        raise e_col
            else:
                print(f"ℹ️ BT #{bt_id} n'est pas le premier du projet #{project_id}")
                        
        except Exception as e:
            st.warning(f"Erreur mise à jour projet: {e}")
            print(f"❌ Erreur mise à jour projet #{project_id}: {e}")
            # Continuer sans bloquer la création du BT
    
    def get_bons_travail(self, **filters) -> List[Dict]:
        """
        Récupère les Bons de Travail avec filtres spécifiques et enrichissement complet.
        
        Args:
            **filters: Filtres optionnels (project_id, employe_id, statut, etc.)
            
        Returns:
            List[Dict]: Liste des BT avec informations enrichies
        """
        try:
            # Récupération des BT de base
            bts = self.base.get_formulaires('BON_TRAVAIL', **filters)
            
            # Enrichissement avec données spécifiques BT (sécurisé)
            for bt in bts:
                try:
                    # Informations d'assignation
                    bt['assignations'] = self._get_assignations_bt(bt['id'])
                    
                    # Informations de réservation postes
                    bt['reservations_postes'] = self._get_reservations_postes_bt(bt['id'])
                    
                    # Calcul de l'avancement
                    bt['avancement'] = self._calculer_avancement_bt(bt['id'])
                    
                    # Informations complémentaires
                    bt['metadata_parsed'] = self._parse_metadata_bt(bt.get('metadonnees_json', '{}'))
                    
                    # NOUVEAU : Opérations réelles de la base
                    bt['operations_reelles'] = self._get_operations_bt(bt['id'])
                    
                except Exception as e_enrich:
                    # Continuer avec données partielles si erreur d'enrichissement
                    print(f"⚠️ Erreur enrichissement BT #{bt['id']}: {e_enrich}")
                    bt['assignations'] = []
                    bt['reservations_postes'] = []
                    bt['avancement'] = {'pourcentage': 0, 'operations_terminees': 0, 'operations_totales': 0}
                    bt['metadata_parsed'] = {}
                    bt['operations_reelles'] = []
            
            print(f"✅ {len(bts)} BT récupéré(s) avec enrichissement")
            return bts
            
        except Exception as e:
            st.error(f"Erreur récupération BT: {e}")
            print(f"❌ Erreur récupération BT: {e}")
            return []

    def _get_operations_bt(self, bt_id: int) -> List[Dict]:
        """
        Récupère les opérations réelles d'un BT depuis la table operations.
        
        Args:
            bt_id: ID du BT
            
        Returns:
            List[Dict]: Liste des opérations avec détails
        """
        try:
            query = """
                SELECT 
                    o.*,
                    wc.nom as work_center_nom,
                    wc.departement as work_center_dept
                FROM operations o
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE o.formulaire_bt_id = ?
                ORDER BY o.id
            """
            rows = self.db.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"❌ Erreur récupération opérations BT #{bt_id}: {e}")
            return []
    
    def _parse_metadata_bt(self, metadonnees_json: str) -> Dict:
        """
        Parse les métadonnées JSON du BT de manière sécurisée.
        
        Args:
            metadonnees_json: Métadonnées JSON du BT
            
        Returns:
            Dict: Métadonnées parsées
        """
        try:
            if not metadonnees_json:
                return {}
            return json.loads(metadonnees_json)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def _get_assignations_bt(self, bt_id: int) -> List[Dict]:
        """
        Récupère les assignations d'employés pour un BT avec informations complètes.
        
        Args:
            bt_id: ID du BT
            
        Returns:
            List[Dict]: Liste des assignations enrichies
        """
        try:
            query = """
                SELECT 
                    a.*,
                    e.prenom || ' ' || e.nom as employe_nom,
                    e.poste,
                    e.departement,
                    e.email
                FROM bt_assignations a
                JOIN employees e ON a.employe_id = e.id
                WHERE a.bt_id = ?
                ORDER BY a.date_assignation
            """
            rows = self.db.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"❌ Erreur récupération assignations BT #{bt_id}: {e}")
            return []
    
    def _get_reservations_postes_bt(self, bt_id: int) -> List[Dict]:
        """
        Récupère les réservations de postes pour un BT avec informations complètes.
        
        Args:
            bt_id: ID du BT
            
        Returns:
            List[Dict]: Liste des réservations enrichies
        """
        try:
            query = """
                SELECT 
                    r.*,
                    w.nom as poste_nom,
                    w.departement,
                    w.categorie,
                    w.type_machine,
                    w.capacite_theorique
                FROM bt_reservations_postes r
                JOIN work_centers w ON r.work_center_id = w.id
                WHERE r.bt_id = ?
                ORDER BY r.date_prevue
            """
            rows = self.db.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"❌ Erreur récupération réservations BT #{bt_id}: {e}")
            return []
    
    def _calculer_avancement_bt(self, bt_id: int) -> Dict:
        """
        Calcule l'avancement d'un BT basé sur les opérations et le suivi réel.
        
        Args:
            bt_id: ID du BT
            
        Returns:
            Dict: Informations d'avancement détaillées
        """
        try:
            # Vérifier l'avancement via la table bt_avancement
            avancement_reel = self._get_avancement_reel_bt(bt_id)
            if avancement_reel:
                return avancement_reel
            
            # Fallback : calculer basé sur les opérations réelles de la table operations
            operations = self._get_operations_bt(bt_id)
            if not operations:
                return {'pourcentage': 0, 'operations_terminees': 0, 'operations_totales': 0}
            
            operations_terminees = 0
            for operation in operations:
                if operation.get('statut') == 'TERMINÉ':
                    operations_terminees += 1
            
            operations_totales = len(operations)
            pourcentage = (operations_terminees / operations_totales * 100) if operations_totales > 0 else 0
            
            return {
                'pourcentage': round(pourcentage, 1),
                'operations_terminees': operations_terminees,
                'operations_totales': operations_totales,
                'mode_calcul': 'statut_operations_reelles'
            }
            
        except Exception as e:
            print(f"❌ Erreur calcul avancement BT #{bt_id}: {e}")
            return {'pourcentage': 0, 'operations_terminees': 0, 'operations_totales': 0, 'erreur': str(e)}
    
    def _get_avancement_reel_bt(self, bt_id: int) -> Optional[Dict]:
        """
        Récupère l'avancement réel depuis la table de suivi.
        
        Args:
            bt_id: ID du BT
            
        Returns:
            Optional[Dict]: Avancement réel ou None
        """
        try:
            query = """
                SELECT 
                    COUNT(*) as operations_totales,
                    COUNT(CASE WHEN pourcentage_realise >= 100 THEN 1 END) as operations_terminees,
                    AVG(pourcentage_realise) as pourcentage_moyen,
                    SUM(temps_reel) as temps_total_reel
                FROM bt_avancement
                WHERE bt_id = ?
            """
            result = self.db.execute_query(query, (bt_id,))
            
            if result and result[0]['operations_totales'] > 0:
                row = result[0]
                return {
                    'pourcentage': round(row['pourcentage_moyen'] or 0, 1),
                    'operations_terminees': row['operations_terminees'],
                    'operations_totales': row['operations_totales'],
                    'temps_total_reel': row['temps_total_reel'] or 0,
                    'mode_calcul': 'suivi_reel'
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Erreur avancement réel BT #{bt_id}: {e}")
            return None
    
    def _operation_terminee(self, operation_id: int) -> bool:
        """
        Vérifie si une opération est terminée.
        
        Args:
            operation_id: ID de l'opération
            
        Returns:
            bool: True si terminée
        """
        try:
            query = "SELECT statut FROM operations WHERE id = ?"
            result = self.db.execute_query(query, (operation_id,))
            return result and result[0]['statut'] == 'TERMINÉ'
        except Exception as e:
            print(f"❌ Erreur vérification opération #{operation_id}: {e}")
            return False
    
    def marquer_bt_termine(self, bt_id: int, employe_id: int, 
                          commentaires: str = "") -> bool:
        """
        Marque un BT comme terminé avec validations et traçabilité complète.
        
        Args:
            bt_id: ID du BT
            employe_id: ID de l'employé qui termine
            commentaires: Commentaires de fin
            
        Returns:
            bool: True si succès
        """
        try:
            # Validation : vérifier que l'employé est autorisé
            if not self._employe_peut_terminer_bt(bt_id, employe_id):
                st.error("Seuls les employés assignés ou responsables peuvent terminer ce BT")
                return False
            
            # Marquer le BT comme terminé
            success = self.base.modifier_statut_formulaire(
                bt_id, 'TERMINÉ', employe_id,
                f"BT terminé par employé #{employe_id}. {commentaires}"
            )
            
            if success:
                # Actions de finalisation
                self._finaliser_bt_termine(bt_id)
                
                # Vérifier si tous les BT du projet sont terminés
                self._verifier_completion_projet(bt_id)
                
                print(f"✅ BT #{bt_id} marqué terminé par employé #{employe_id}")
            
            return success
            
        except Exception as e:
            st.error(f"Erreur fin BT: {e}")
            print(f"❌ Erreur fin BT #{bt_id}: {e}")
            return False
    
    def _finaliser_bt_termine(self, bt_id: int) -> None:
        """
        Actions de finalisation quand un BT est terminé.
        
        Args:
            bt_id: ID du BT terminé
        """
        try:
            # 1. Libérer les réservations de postes
            self._liberer_reservations_postes(bt_id)
            
            # 2. Mettre à jour les assignations
            self._finaliser_assignations_bt(bt_id)
            
            # 3. Compléter l'avancement à 100%
            self._completer_avancement_bt(bt_id)
            
            print(f"✅ Finalisation BT #{bt_id} terminée")
            
        except Exception as e:
            print(f"⚠️ Erreur finalisation BT #{bt_id}: {e}")
    
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
            # 1. Vérifier si c'est le responsable du BT
            bt_details = self.base.get_formulaire_details(bt_id)
            if bt_details and bt_details.get('employee_id') == employe_id:
                return True
            
            # 2. Vérifier si c'est un employé assigné
            assignations = self._get_assignations_bt(bt_id)
            employes_assignes = [a['employe_id'] for a in assignations if a.get('statut') == 'ASSIGNÉ']
            
            if employe_id in employes_assignes:
                return True
            
            # 3. Vérifier les permissions spéciales (ex: superviseur)
            # TODO: Implémenter système de permissions plus avancé
            
            return False
            
        except Exception as e:
            print(f"❌ Erreur vérification permissions BT #{bt_id}: {e}")
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
                SET statut = 'LIBÉRÉ', 
                    date_liberation = CURRENT_TIMESTAMP,
                    notes = COALESCE(notes, '') || ' - Libéré automatiquement (BT terminé)'
                WHERE bt_id = ? AND statut = 'RÉSERVÉ'
            """
            affected = self.db.execute_update(query, (bt_id,))
            
            if affected > 0:
                print(f"✅ {affected} réservation(s) de postes libérée(s) pour BT #{bt_id}")
                
        except Exception as e:
            st.warning(f"Erreur libération postes: {e}")
            print(f"❌ Erreur libération postes BT #{bt_id}: {e}")
    
    def _finaliser_assignations_bt(self, bt_id: int) -> None:
        """
        Finalise les assignations d'employés d'un BT terminé.
        
        Args:
            bt_id: ID du BT terminé
        """
        try:
            query = """
                UPDATE bt_assignations 
                SET statut = 'TERMINÉ',
                    notes = COALESCE(notes, '') || ' - BT terminé'
                WHERE bt_id = ? AND statut = 'ASSIGNÉ'
            """
            affected = self.db.execute_update(query, (bt_id,))
            
            if affected > 0:
                print(f"✅ {affected} assignation(s) finalisée(s) pour BT #{bt_id}")
                
        except Exception as e:
            print(f"❌ Erreur finalisation assignations BT #{bt_id}: {e}")
    
    def _completer_avancement_bt(self, bt_id: int) -> None:
        """
        Marque toutes les opérations du BT comme terminées à 100%.
        
        Args:
            bt_id: ID du BT terminé
        """
        try:
            query = """
                UPDATE bt_avancement 
                SET pourcentage_realise = 100.0,
                    date_fin_reel = CURRENT_TIMESTAMP,
                    notes_avancement = COALESCE(notes_avancement, '') || ' - Complété automatiquement (BT terminé)'
                WHERE bt_id = ? AND pourcentage_realise < 100.0
            """
            affected = self.db.execute_update(query, (bt_id,))
            
            if affected > 0:
                print(f"✅ {affected} opération(s) marquée(s) terminée(s) pour BT #{bt_id}")
                
        except Exception as e:
            print(f"❌ Erreur completion avancement BT #{bt_id}: {e}")
    
    def _verifier_completion_projet(self, bt_id: int) -> None:
        """
        Vérifie si le projet est complètement terminé - VERSION CORRIGÉE ROBUSTE
        
        Args:
            bt_id: ID du BT qui vient d'être terminé
        """
        try:
            bt_details = self.base.get_formulaire_details(bt_id)
            project_id = bt_details.get('project_id')
            
            if not project_id:
                print(f"ℹ️ BT #{bt_id} n'est pas lié à un projet")
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
                try:
                    # Tenter avec toutes les colonnes
                    query_update = """
                        UPDATE projects 
                        SET statut = 'TERMINÉ', 
                            date_fin_reel = CURRENT_DATE,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """
                    affected = self.db.execute_update(query_update, (project_id,))
                    
                    if affected > 0:
                        st.success(f"🎉 Projet #{project_id} automatiquement marqué comme terminé!")
                        print(f"🎉 Projet #{project_id} complété automatiquement")
                    
                except Exception as e_col:
                    # Si erreur colonne, mise à jour basique
                    if "no such column" in str(e_col).lower():
                        print("⚠️ Colonnes date_fin_reel manquantes - mise à jour basique")
                        
                        query_update_basic = """
                            UPDATE projects 
                            SET statut = 'TERMINÉ', updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """
                        affected = self.db.execute_update(query_update_basic, (project_id,))
                        
                        if affected > 0:
                            st.success(f"🎉 Projet #{project_id} marqué terminé!")
                            print(f"🎉 Projet #{project_id} complété (mise à jour basique)")
                    else:
                        raise e_col
            else:
                bt_restants = result[0]['count']
                print(f"ℹ️ Projet #{project_id} a encore {bt_restants} BT en cours")
                
        except Exception as e:
            st.warning(f"Erreur vérification projet: {e}")
            print(f"❌ Erreur vérification completion projet: {e}")
    
    def get_statistiques_bt(self) -> Dict:
        """
        Calcule les statistiques complètes et enrichies des BT.
        
        Returns:
            Dict: Statistiques BT enrichies
        """
        try:
            # Statistiques de base du gestionnaire principal
            stats_base = self.base.get_statistiques_formulaires().get('BON_TRAVAIL', {})
            
            # Enrichissement avec données BT spécifiques (sécurisé)
            try:
                query = """
                    SELECT 
                        COUNT(CASE WHEN f.statut = 'EN COURS' THEN 1 END) as en_cours,
                        COUNT(CASE WHEN f.statut = 'VALIDÉ' THEN 1 END) as valides,
                        COUNT(CASE WHEN f.statut = 'TERMINÉ' THEN 1 END) as termines,
                        COUNT(CASE WHEN f.statut = 'BROUILLON' THEN 1 END) as brouillons,
                        AVG(julianday('now') - julianday(f.date_creation)) as duree_moyenne,
                        COUNT(DISTINCT f.project_id) as projets_concernes,
                        COUNT(DISTINCT f.employee_id) as employes_impliques,
                        SUM(f.montant_total) as montant_total_bt,
                        MIN(f.date_creation) as premier_bt_date,
                        MAX(f.date_creation) as dernier_bt_date
                    FROM formulaires f
                    WHERE f.type_formulaire = 'BON_TRAVAIL'
                """
                
                result = self.db.execute_query(query)
                if result:
                    stats_enrichies = dict(result[0])
                    
                    # Calculer le taux de completion
                    total_bt = stats_enrichies.get('termines', 0) + stats_enrichies.get('en_cours', 0) + stats_enrichies.get('valides', 0) + stats_enrichies.get('brouillons', 0)
                    if total_bt > 0:
                        stats_enrichies['taux_completion'] = (stats_enrichies.get('termines', 0) / total_bt) * 100
                    else:
                        stats_enrichies['taux_completion'] = 0
                    
                    # Ajouter aux stats de base
                    stats_base.update(stats_enrichies)
                    
                    print(f"✅ Statistiques BT calculées: {total_bt} BT total")
                    
            except Exception as e:
                st.warning(f"Erreur enrichissement stats BT: {e}")
                print(f"⚠️ Erreur stats enrichies BT: {e}")
            
            # Ajouter des statistiques sur les assignations et réservations
            try:
                stats_assignations = self._get_statistiques_assignations()
                stats_reservations = self._get_statistiques_reservations()
                
                stats_base.update(stats_assignations)
                stats_base.update(stats_reservations)
                
            except Exception as e:
                print(f"⚠️ Erreur stats assignations/réservations: {e}")
            
            return stats_base
            
        except Exception as e:
            st.error(f"Erreur stats BT: {e}")
            print(f"❌ Erreur statistiques BT: {e}")
            return {}
    
    def _get_statistiques_assignations(self) -> Dict:
        """
        Calcule les statistiques des assignations BT.
        
        Returns:
            Dict: Statistiques assignations
        """
        try:
            query = """
                SELECT 
                    COUNT(*) as total_assignations,
                    COUNT(DISTINCT employe_id) as employes_assignes_uniques,
                    COUNT(DISTINCT bt_id) as bt_avec_assignations
                FROM bt_assignations
                WHERE statut = 'ASSIGNÉ'
            """
            
            result = self.db.execute_query(query)
            if result:
                row = result[0]
                return {
                    'assignations_actives': row['total_assignations'],
                    'employes_assignes_bt': row['employes_assignes_uniques'],
                    'bt_avec_equipe': row['bt_avec_assignations']
                }
            
            return {}
            
        except Exception as e:
            print(f"❌ Erreur stats assignations: {e}")
            return {}
    
    def _get_statistiques_reservations(self) -> Dict:
        """
        Calcule les statistiques des réservations de postes.
        
        Returns:
            Dict: Statistiques réservations
        """
        try:
            query = """
                SELECT 
                    COUNT(*) as total_reservations,
                    COUNT(DISTINCT work_center_id) as postes_reserves_uniques,
                    COUNT(CASE WHEN statut = 'RÉSERVÉ' THEN 1 END) as reservations_actives
                FROM bt_reservations_postes
            """
            
            result = self.db.execute_query(query)
            if result:
                row = result[0]
                return {
                    'reservations_postes_total': row['total_reservations'],
                    'postes_utilises_bt': row['postes_reserves_uniques'],
                    'reservations_actives': row['reservations_actives']
                }
            
            return {}
            
        except Exception as e:
            print(f"❌ Erreur stats réservations: {e}")
            return {}
    
    def generer_rapport_productivite(self, periode_jours: int = 30) -> Dict:
        """
        Génère un rapport de productivité complet des BT.
        
        Args:
            periode_jours: Période d'analyse en jours
            
        Returns:
            Dict: Rapport de productivité détaillé
        """
        try:
            date_debut = datetime.now() - timedelta(days=periode_jours)
            
            # Requête principale pour la productivité par employé
            query = """
                SELECT 
                    e.prenom || ' ' || e.nom as employe_nom,
                    e.poste,
                    e.departement,
                    COUNT(f.id) as nb_bt_termines,
                    AVG(julianday(f.updated_at) - julianday(f.date_creation)) as duree_moyenne,
                    SUM(f.montant_total) as montant_total_travaux,
                    MIN(f.date_creation) as premier_bt_periode,
                    MAX(f.updated_at) as dernier_bt_termine
                FROM formulaires f
                JOIN employees e ON f.employee_id = e.id
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                AND f.statut = 'TERMINÉ'
                AND f.updated_at >= ?
                GROUP BY f.employee_id, e.prenom, e.nom, e.poste, e.departement
                ORDER BY nb_bt_termines DESC
            """
            
            rows = self.db.execute_query(query, (date_debut.isoformat(),))
            
            # Statistiques globales de la période
            query_global = """
                SELECT 
                    COUNT(*) as total_bt_crees,
                    COUNT(CASE WHEN statut = 'TERMINÉ' THEN 1 END) as total_bt_termines,
                    AVG(montant_total) as montant_moyen,
                    SUM(montant_total) as montant_total_periode
                FROM formulaires
                WHERE type_formulaire = 'BON_TRAVAIL'
                AND date_creation >= ?
            """
            
            result_global = self.db.execute_query(query_global, (date_debut.isoformat(),))
            
            # Construction du rapport
            rapport = {
                'periode': f"{periode_jours} derniers jours",
                'date_generation': datetime.now().isoformat(),
                'date_debut_analyse': date_debut.isoformat(),
                'employes': [dict(row) for row in rows],
                'statistiques_globales': dict(result_global[0]) if result_global else {},
                'analyse': {}
            }
            
            # Calculs d'analyse
            if rapport['employes']:
                rapport['total_bt_termines'] = sum(emp['nb_bt_termines'] for emp in rapport['employes'])
                rapport['duree_moyenne_globale'] = sum(emp['duree_moyenne'] or 0 for emp in rapport['employes']) / len(rapport['employes'])
                
                # Top performers
                rapport['analyse']['top_performer'] = max(rapport['employes'], key=lambda x: x['nb_bt_termines'])
                rapport['analyse']['plus_efficace'] = min(rapport['employes'], key=lambda x: x['duree_moyenne'] or float('inf'))
                rapport['analyse']['plus_rentable'] = max(rapport['employes'], key=lambda x: x['montant_total_travaux'] or 0)
            else:
                rapport['total_bt_termines'] = 0
                rapport['duree_moyenne_globale'] = 0
                rapport['analyse'] = {'message': 'Aucune donnée disponible pour la période'}
            
            # Ajouter recommandations
            rapport['recommandations'] = self._generer_recommandations_productivite(rapport)
            
            print(f"✅ Rapport productivité généré pour {periode_jours} jours")
            return rapport
            
        except Exception as e:
            st.error(f"Erreur rapport productivité: {e}")
            print(f"❌ Erreur rapport productivité: {e}")
            return {}
    
    def _generer_recommandations_productivite(self, rapport: Dict) -> List[str]:
        """
        Génère des recommandations basées sur l'analyse de productivité.
        
        Args:
            rapport: Données du rapport de productivité
            
        Returns:
            List[str]: Liste des recommandations
        """
        recommandations = []
        
        try:
            employes = rapport.get('employes', [])
            if not employes:
                return ["Aucune donnée suffisante pour générer des recommandations"]
            
            # Analyse de la charge de travail
            nb_bt_max = max(emp['nb_bt_termines'] for emp in employes)
            nb_bt_min = min(emp['nb_bt_termines'] for emp in employes)
            
            if nb_bt_max - nb_bt_min > 5:
                recommandations.append("📊 Équilibrer la charge de travail entre les employés")
            
            # Analyse des durées
            durees = [emp['duree_moyenne'] for emp in employes if emp['duree_moyenne']]
            if durees:
                duree_max = max(durees)
                duree_moyenne = sum(durees) / len(durees)
                
                if duree_max > duree_moyenne * 1.5:
                    recommandations.append("⏱️ Identifier les causes des retards sur certains BT")
            
            # Analyse par département
            depts = {}
            for emp in employes:
                dept = emp.get('departement', 'N/A')
                if dept not in depts:
                    depts[dept] = []
                depts[dept].append(emp['nb_bt_termines'])
            
            if len(depts) > 1:
                recommandations.append("🏢 Analyser les différences de performance entre départements")
            
            # Recommandations générales
            if len(employes) < 3:
                recommandations.append("👥 Considérer l'augmentation de l'équipe pour les BT")
            
            if not recommandations:
                recommandations.append("✅ Performance globale satisfaisante")
            
        except Exception as e:
            print(f"❌ Erreur génération recommandations: {e}")
            recommandations.append("⚠️ Erreur dans l'analyse des recommandations")
        
        return recommandations
    
    def get_bt_details_complets(self, bt_id: int) -> Optional[Dict]:
        """
        Récupère tous les détails complets d'un BT spécifique.
        
        Args:
            bt_id: ID du BT
            
        Returns:
            Optional[Dict]: Détails complets du BT
        """
        try:
            # Détails de base
            bt_details = self.base.get_formulaire_details(bt_id)
            if not bt_details:
                return None
            
            # Enrichissement complet
            bt_details['assignations'] = self._get_assignations_bt(bt_id)
            bt_details['reservations_postes'] = self._get_reservations_postes_bt(bt_id)
            bt_details['avancement_detaille'] = self._get_avancement_detaille_bt(bt_id)
            bt_details['historique_modifications'] = self._get_historique_bt(bt_id)
            bt_details['metadata_parsed'] = self._parse_metadata_bt(bt_details.get('metadonnees_json', '{}'))
            bt_details['operations_reelles'] = self._get_operations_bt(bt_id)
            
            print(f"✅ Détails complets récupérés pour BT #{bt_id}")
            return bt_details
            
        except Exception as e:
            st.error(f"Erreur récupération détails BT: {e}")
            print(f"❌ Erreur détails BT #{bt_id}: {e}")
            return None
    
    def _get_avancement_detaille_bt(self, bt_id: int) -> List[Dict]:
        """
        Récupère l'avancement détaillé de toutes les opérations du BT.
        
        Args:
            bt_id: ID du BT
            
        Returns:
            List[Dict]: Avancement détaillé par opération
        """
        try:
            query = """
                SELECT 
                    a.*,
                    o.sequence_number,
                    o.description as operation_description,
                    o.temps_estime,
                    e.prenom || ' ' || e.nom as updated_by_nom
                FROM bt_avancement a
                LEFT JOIN operations o ON a.operation_id = o.id
                LEFT JOIN employees e ON a.updated_by = e.id
                WHERE a.bt_id = ?
                ORDER BY o.sequence_number
            """
            
            rows = self.db.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"❌ Erreur avancement détaillé BT #{bt_id}: {e}")
            return []
    
    def _get_historique_bt(self, bt_id: int) -> List[Dict]:
        """
        Récupère l'historique des modifications du BT.
        
        Args:
            bt_id: ID du BT
            
        Returns:
            List[Dict]: Historique des modifications
        """
        try:
            # Récupérer depuis l'historique des validations du gestionnaire de base
            query = """
                SELECT 
                    fv.*,
                    e.prenom || ' ' || e.nom as employee_nom
                FROM formulaire_validations fv
                LEFT JOIN employees e ON fv.employee_id = e.id
                WHERE fv.formulaire_id = ?
                ORDER BY fv.date_validation DESC
            """
            
            rows = self.db.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"❌ Erreur historique BT #{bt_id}: {e}")
            return []
    
    def mettre_a_jour_avancement_operation(self, bt_id: int, operation_id: int, 
                                         pourcentage: float, temps_reel: float = 0, 
                                         notes: str = "", employe_id: int = None) -> bool:
        """
        Met à jour l'avancement d'une opération spécifique du BT.
        
        Args:
            bt_id: ID du BT
            operation_id: ID de l'opération
            pourcentage: Pourcentage de réalisation (0-100)
            temps_reel: Temps réel passé
            notes: Notes sur l'avancement
            employe_id: ID de l'employé qui fait la mise à jour
            
        Returns:
            bool: True si succès
        """
        try:
            # Validation
            if not (0 <= pourcentage <= 100):
                st.error("Le pourcentage doit être entre 0 et 100")
                return False
            
            # Vérifier si l'enregistrement existe
            existing = self.db.execute_query(
                "SELECT id FROM bt_avancement WHERE bt_id = ? AND operation_id = ?",
                (bt_id, operation_id)
            )
            
            if existing:
                # Mise à jour
                query = """
                    UPDATE bt_avancement 
                    SET pourcentage_realise = ?, 
                        temps_reel = ?, 
                        notes_avancement = ?,
                        updated_by = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE bt_id = ? AND operation_id = ?
                """
                params = (pourcentage, temps_reel, notes, employe_id, bt_id, operation_id)
            else:
                # Création
                query = """
                    INSERT INTO bt_avancement 
                    (bt_id, operation_id, pourcentage_realise, temps_reel, notes_avancement, updated_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                params = (bt_id, operation_id, pourcentage, temps_reel, notes, employe_id)
            
            affected = self.db.execute_update(query, params)
            
            if affected > 0:
                print(f"✅ Avancement opération #{operation_id} mis à jour: {pourcentage}%")
                
                # Marquer l'opération comme terminée si 100%
                if pourcentage >= 100:
                    self._marquer_operation_terminee(operation_id)
                
                return True
            
            return False
            
        except Exception as e:
            st.error(f"Erreur mise à jour avancement: {e}")
            print(f"❌ Erreur avancement opération #{operation_id}: {e}")
            return False
    
    def _marquer_operation_terminee(self, operation_id: int) -> None:
        """
        Marque une opération comme terminée dans la table operations.
        
        Args:
            operation_id: ID de l'opération
        """
        try:
            query = """
                UPDATE operations 
                SET statut = 'TERMINÉ', updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND statut != 'TERMINÉ'
            """
            affected = self.db.execute_update(query, (operation_id,))
            
            if affected > 0:
                print(f"✅ Opération #{operation_id} marquée terminée")
                
        except Exception as e:
            print(f"❌ Erreur marquage opération terminée #{operation_id}: {e}")
    
    # ======================================================================
    # ÉTAPE 3 : MÉTHODES D'INTÉGRATION TIMETRACKER ↔ BONS DE TRAVAIL
    # ======================================================================
    
    def get_heures_timetracker_bt(self, bt_id: int) -> Dict:
        """
        Récupère les heures TimeTracker pour un BT.
        
        Args:
            bt_id: ID du Bon de Travail
            
        Returns:
            Dict: Statistiques des heures pointées sur ce BT
        """
        try:
            query = '''
                SELECT 
                    COUNT(*) as nb_sessions,
                    COUNT(DISTINCT employee_id) as nb_employes,
                    COALESCE(SUM(total_hours), 0) as total_heures,
                    COALESCE(SUM(total_cost), 0) as total_cout,
                    MIN(punch_in) as premiere_session,
                    MAX(punch_out) as derniere_session
                FROM time_entries 
                WHERE formulaire_bt_id = ? AND total_cost IS NOT NULL
            '''
            result = self.db.execute_query(query, (bt_id,))
            
            if result and result[0]:
                stats = dict(result[0])
                print(f"✅ Stats TimeTracker BT #{bt_id}: {stats['nb_sessions']} sessions, {stats['total_heures']:.1f}h")
                return stats
            else:
                return {
                    'nb_sessions': 0,
                    'nb_employes': 0, 
                    'total_heures': 0,
                    'total_cout': 0,
                    'premiere_session': None,
                    'derniere_session': None
                }
        except Exception as e:
            print(f"❌ Erreur récupération heures TimeTracker BT #{bt_id}: {e}")
            return {}

    def get_sessions_timetracker_bt(self, bt_id: int) -> List[Dict]:
        """
        Récupère toutes les sessions TimeTracker d'un BT.
        
        Args:
            bt_id: ID du Bon de Travail
            
        Returns:
            List[Dict]: Liste des sessions de pointage avec détails employés
        """
        try:
            query = '''
                SELECT 
                    te.*,
                    e.prenom || ' ' || e.nom as employee_name,
                    e.poste as employee_poste,
                    e.departement as employee_dept
                FROM time_entries te
                JOIN employees e ON te.employee_id = e.id
                WHERE te.formulaire_bt_id = ?
                ORDER BY te.punch_in DESC
            '''
            rows = self.db.execute_query(query, (bt_id,))
            sessions = [dict(row) for row in rows]
            
            print(f"✅ {len(sessions)} session(s) TimeTracker récupérée(s) pour BT #{bt_id}")
            return sessions
            
        except Exception as e:
            print(f"❌ Erreur récupération sessions TimeTracker BT #{bt_id}: {e}")
            return []

    def demarrer_pointage_bt(self, bt_id: int, employee_id: int) -> bool:
        """
        Démarre un pointage TimeTracker depuis un BT.
        
        Args:
            bt_id: ID du Bon de Travail
            employee_id: ID de l'employé
            
        Returns:
            bool: True si le pointage a été démarré avec succès
        """
        try:
            # Vérifier que TimeTracker est disponible
            if 'timetracker_erp' not in st.session_state:
                print("❌ TimeTracker non disponible dans la session")
                return False
            
            # Vérifier que l'employé est assigné à ce BT
            employes_assignes = self.get_employes_assignes_bt(bt_id)
            employes_ids = [emp['id'] for emp in employes_assignes]
            
            if employee_id not in employes_ids:
                print(f"❌ L'employé #{employee_id} n'est pas assigné au BT #{bt_id}")
                return False
            
            # Démarrer le pointage via TimeTracker
            tt = st.session_state.timetracker_erp
            entry_id = tt.punch_in_sur_bt(employee_id, bt_id, f"Pointage démarré depuis BT #{bt_id}")
            
            if entry_id:
                print(f"✅ Pointage TimeTracker démarré: entry #{entry_id} pour employé #{employee_id} sur BT #{bt_id}")
                return True
            else:
                print(f"❌ Échec démarrage pointage TimeTracker pour BT #{bt_id}")
                return False
                
        except Exception as e:
            print(f"❌ Erreur démarrage pointage BT #{bt_id}: {e}")
            return False

    def get_employes_assignes_bt(self, bt_id: int) -> List[Dict]:
        """
        Récupère les employés assignés à un BT avec leurs informations complètes.
        
        Args:
            bt_id: ID du Bon de Travail
            
        Returns:
            List[Dict]: Liste des employés assignés avec détails
        """
        try:
            query = '''
                SELECT 
                    bta.*,
                    e.id,
                    e.prenom || ' ' || e.nom as nom,
                    e.poste,
                    e.departement,
                    e.email,
                    e.salaire_horaire
                FROM bt_assignations bta
                JOIN employees e ON bta.employe_id = e.id
                WHERE bta.bt_id = ? AND bta.statut = 'ASSIGNÉ'
                ORDER BY bta.date_assignation DESC
            '''
            rows = self.db.execute_query(query, (bt_id,))
            employes = [dict(row) for row in rows]
            
            print(f"✅ {len(employes)} employé(s) assigné(s) récupéré(s) pour BT #{bt_id}")
            return employes
            
        except Exception as e:
            print(f"❌ Erreur récupération employés assignés BT #{bt_id}: {e}")
            return []
