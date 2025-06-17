# formulaires/bons_travail/gestionnaire_bt.py
# Gestionnaire spécialisé pour les Bons de Travail - VERSION CORRIGÉE BASE DE DONNÉES

"""
Gestionnaire spécialisé pour les Bons de Travail (BT).
VERSION CORRIGÉE : Utilise pleinement la base de données SQLite avec vraies données
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
    Gestionnaire spécialisé pour les Bons de Travail - VERSION CORRIGÉE BASE DE DONNÉES
    
    Utilise complètement les tables SQLite avec vraies données :
    - formulaires (table principale)
    - formulaire_lignes (détails des matériaux)
    - bt_assignations (équipe assignée)
    - bt_reservations_postes (postes réservés)
    - bt_avancement (suivi des opérations)
    - operations (opérations du projet)
    - materials (matériaux du projet)
    - work_centers (postes de travail)
    - employees (employés réels)
    - projects (projets réels)
    """
    
    def __init__(self, gestionnaire_base: GestionnaireFormulaires):
        """
        Initialise le gestionnaire spécialisé avec infrastructure complète
        
        Args:
            gestionnaire_base: Instance du gestionnaire de base
        """
        self.base = gestionnaire_base
        self.db = gestionnaire_base.db
        
        # Vérifier et créer l'infrastructure BT complète
        self._ensure_bt_infrastructure()
    
    def _ensure_bt_infrastructure(self):
        """
        S'assurer que toute l'infrastructure BT est en place avec robustesse
        """
        try:
            print("🔧 Vérification infrastructure BT...")
            
            # 1. Vérifier et corriger les colonnes projects
            self._check_and_fix_projects_columns()
            
            # 2. Créer les tables BT spécialisées si manquantes
            self._create_bt_tables()
            
            # 3. Vérifier l'intégrité des données
            self._verify_bt_data_integrity()
            
            print("✅ Infrastructure BT vérifiée et configurée")
            
        except Exception as e:
            st.warning(f"Avertissement infrastructure BT: {e}")
            print(f"⚠️ Erreur infrastructure BT: {e}")
    
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
            print(f"❌ Erreur vérification colonnes projects: {e}")
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
            print(f"❌ Erreur création tables BT: {e}")
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
            else:
                print("ℹ️ Aucun BT existant - base prête pour nouveaux BT")
            
        except Exception as e:
            print(f"❌ Erreur vérification intégrité BT: {e}")
    
    def creer_bon_travail(self, data: Dict) -> Optional[int]:
        """
        Crée un nouveau Bon de Travail en utilisant pleinement la base de données
        
        Args:
            data: Données du bon de travail avec vrais IDs de la base
            
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
            
            # Enrichissement des données BT avec vraies données de la base
            data['type_formulaire'] = 'BON_TRAVAIL'
            
            # Métadonnées avec vraies références BD
            metadonnees_bt = {
                'operations_selectionnees': data.get('operations_selectionnees', []),
                'materiaux_selectionnes': data.get('materiaux_selectionnes', []), 
                'employes_assignes': data.get('employes_assignes', []),
                'work_centers_utilises': data.get('work_centers_utilises', []),
                'projet_source': data.get('project_id'),
                'temps_estime_total': data.get('temps_estime_total', 0),
                'cout_materiaux_estime': data.get('cout_materiaux_estime', 0),
                'cout_main_oeuvre_estime': data.get('cout_main_oeuvre_estime', 0),
                'date_creation_bt': datetime.now().isoformat(),
                'version_bt': '2.1_database'
            }
            
            data['metadonnees_json'] = json.dumps(metadonnees_bt)
            
            # Création via le gestionnaire de base
            bt_id = self.base.creer_formulaire(data)
            
            if bt_id:
                # Actions post-création spécifiques BT avec vraies données BD
                self._post_creation_bt_database(bt_id, data)
                
                st.success(f"✅ Bon de Travail #{bt_id} créé avec succès!")
                print(f"✅ BT #{bt_id} créé avec succès - {data.get('numero_document', 'N/A')}")
            
            return bt_id
            
        except Exception as e:
            st.error(f"Erreur création BT: {e}")
            print(f"❌ Erreur détaillée création BT: {e}")
            return None
    
    def _post_creation_bt_database(self, bt_id: int, data: Dict) -> None:
        """
        Actions post-création utilisant les vraies données de la base
        
        Args:
            bt_id: ID du BT créé
            data: Données originales avec vrais IDs
        """
        try:
            # 1. Assignation des employés réels depuis la base
            employes_assignes = data.get('employes_assignes', [])
            if employes_assignes:
                self._assigner_employes_reels(bt_id, employes_assignes)
            
            # 2. Réservation des postes de travail réels
            work_centers = data.get('work_centers_utilises', [])
            if work_centers:
                self._reserver_postes_reels(bt_id, work_centers, data.get('date_echeance'))
            
            # 3. Initialisation du suivi pour les vraies opérations
            operations_selectionnees = data.get('operations_selectionnees', [])
            if operations_selectionnees:
                self._initialiser_avancement_operations_reelles(bt_id, operations_selectionnees)
            
            # 4. Création des lignes de formulaire pour les vrais matériaux
            materiaux_selectionnes = data.get('materiaux_selectionnes', [])
            if materiaux_selectionnes:
                self._creer_lignes_materiaux_reels(bt_id, materiaux_selectionnes)
            
            # 5. Mise à jour du statut du projet
            if data.get('project_id'):
                self._mettre_a_jour_statut_projet(data['project_id'], bt_id)
            
            print(f"✅ Actions post-création BT #{bt_id} avec vraies données BD terminées")
                
        except Exception as e:
            st.warning(f"Actions post-création BT partiellement échouées: {e}")
            print(f"⚠️ Erreur post-création BT: {e}")
    
    def _assigner_employes_reels(self, bt_id: int, employes_ids: List[int]) -> None:
        """
        Assigne des employés réels de la base au BT
        
        Args:
            bt_id: ID du BT
            employes_ids: Liste des vrais IDs employés depuis la table employees
        """
        try:
            assignations_creees = 0
            
            for employe_id in employes_ids:
                # Vérifier que l'employé existe vraiment dans la base
                employe_exists = self.db.execute_query(
                    "SELECT prenom, nom, poste FROM employees WHERE id = ? AND statut = 'ACTIF'",
                    (employe_id,)
                )
                
                if employe_exists:
                    employe_info = employe_exists[0]
                    query = """
                        INSERT INTO bt_assignations (bt_id, employe_id, date_assignation, statut, role_bt)
                        VALUES (?, ?, CURRENT_TIMESTAMP, 'ASSIGNÉ', 'MEMBRE_ÉQUIPE')
                    """
                    self.db.execute_insert(query, (bt_id, employe_id))
                    assignations_creees += 1
                    print(f"✅ Employé {employe_info['prenom']} {employe_info['nom']} assigné au BT #{bt_id}")
                else:
                    st.warning(f"Employé ID {employe_id} non trouvé ou inactif")
            
            if assignations_creees > 0:
                print(f"✅ {assignations_creees} employé(s) réel(s) assigné(s) au BT #{bt_id}")
                
        except Exception as e:
            st.warning(f"Erreur assignation employés réels: {e}")
            print(f"❌ Erreur assignation employés BT: {e}")
    
    def _reserver_postes_reels(self, bt_id: int, work_centers_ids: List[int], 
                              date_prevue: Optional[str]) -> None:
        """
        Réserve des postes de travail réels pour le BT
        
        Args:
            bt_id: ID du BT
            work_centers_ids: Liste des vrais IDs postes depuis work_centers
            date_prevue: Date prévue d'utilisation
        """
        try:
            reservations_creees = 0
            
            for wc_id in work_centers_ids:
                # Vérifier que le poste existe vraiment
                poste_exists = self.db.execute_query(
                    "SELECT nom, departement FROM work_centers WHERE id = ? AND statut = 'ACTIF'",
                    (wc_id,)
                )
                
                if poste_exists:
                    poste_info = poste_exists[0]
                    query = """
                        INSERT INTO bt_reservations_postes 
                        (bt_id, work_center_id, date_reservation, date_prevue, statut)
                        VALUES (?, ?, CURRENT_TIMESTAMP, ?, 'RÉSERVÉ')
                    """
                    self.db.execute_insert(query, (bt_id, wc_id, date_prevue))
                    reservations_creees += 1
                    print(f"✅ Poste {poste_info['nom']} ({poste_info['departement']}) réservé pour BT #{bt_id}")
                else:
                    st.warning(f"Poste de travail ID {wc_id} non trouvé ou inactif")
            
            if reservations_creees > 0:
                print(f"✅ {reservations_creees} poste(s) réel(s) réservé(s) pour BT #{bt_id}")
                
        except Exception as e:
            st.warning(f"Erreur réservation postes réels: {e}")
            print(f"❌ Erreur réservation postes BT: {e}")
    
    def _initialiser_avancement_operations_reelles(self, bt_id: int, operations_ids: List[int]) -> None:
        """
        Initialise le suivi d'avancement pour les vraies opérations du projet
        
        Args:
            bt_id: ID du BT
            operations_ids: Liste des vrais IDs opérations depuis operations
        """
        try:
            avancements_crees = 0
            
            for operation_id in operations_ids:
                # Vérifier que l'opération existe vraiment
                operation_exists = self.db.execute_query(
                    "SELECT description, temps_estime, sequence_number FROM operations WHERE id = ?",
                    (operation_id,)
                )
                
                if operation_exists:
                    operation_info = operation_exists[0]
                    query = """
                        INSERT INTO bt_avancement 
                        (bt_id, operation_id, pourcentage_realise, temps_reel)
                        VALUES (?, ?, 0.0, 0.0)
                    """
                    self.db.execute_insert(query, (bt_id, operation_id))
                    avancements_crees += 1
                    print(f"✅ Suivi initialisé pour opération: {operation_info['description'][:50]}")
            
            if avancements_crees > 0:
                print(f"✅ Suivi avancement initialisé pour {avancements_crees} opération(s) réelle(s)")
                
        except Exception as e:
            print(f"❌ Erreur initialisation avancement opérations réelles: {e}")
    
    def _creer_lignes_materiaux_reels(self, bt_id: int, materiaux_ids: List[int]) -> None:
        """
        Crée les lignes de formulaire pour les vrais matériaux sélectionnés
        
        Args:
            bt_id: ID du BT
            materiaux_ids: Liste des vrais IDs matériaux depuis materials
        """
        try:
            lignes_creees = 0
            
            for materiau_id in materiaux_ids:
                # Récupérer les vraies données du matériau
                materiau_data = self.db.execute_query(
                    "SELECT designation, quantite, unite, prix_unitaire FROM materials WHERE id = ?",
                    (materiau_id,)
                )
                
                if materiau_data:
                    mat = materiau_data[0]
                    
                    # Créer la ligne de formulaire avec référence au vrai matériau
                    sequence = lignes_creees + 1
                    montant_ligne = (mat['quantite'] or 0) * (mat['prix_unitaire'] or 0)
                    
                    # Vérifier si la colonne reference_materiau existe
                    try:
                        query = """
                            INSERT INTO formulaire_lignes 
                            (formulaire_id, sequence_ligne, description, quantite, unite, 
                             prix_unitaire, montant_ligne, reference_materiau)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        
                        self.db.execute_insert(query, (
                            bt_id,
                            sequence,
                            mat['designation'],
                            mat['quantite'],
                            mat['unite'],
                            mat['prix_unitaire'],
                            montant_ligne,
                            materiau_id
                        ))
                    except Exception as e_col:
                        if "no such column" in str(e_col).lower():
                            # Fallback sans reference_materiau
                            query_fallback = """
                                INSERT INTO formulaire_lignes 
                                (formulaire_id, sequence_ligne, description, quantite, unite, 
                                 prix_unitaire, montant_ligne)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """
                            
                            self.db.execute_insert(query_fallback, (
                                bt_id,
                                sequence,
                                f"{mat['designation']} (Réf: {materiau_id})",
                                mat['quantite'],
                                mat['unite'],
                                mat['prix_unitaire'],
                                montant_ligne
                            ))
                        else:
                            raise e_col
                    
                    lignes_creees += 1
                    print(f"✅ Ligne créée pour matériau: {mat['designation'][:50]}")
            
            if lignes_creees > 0:
                print(f"✅ {lignes_creees} ligne(s) de matériaux réels créée(s)")
                
        except Exception as e:
            print(f"❌ Erreur création lignes matériaux réels: {e}")
    
    def _mettre_a_jour_statut_projet(self, project_id: int, bt_id: int) -> None:
        """
        Met à jour le statut du projet associé de manière robuste
        
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
                            st.info(f"✅ Projet #{project_id} marqué EN COURS")
                            print(f"✅ Projet #{project_id} mis à jour (basique): À FAIRE → EN COURS")
                    else:
                        raise e_col
            else:
                print(f"ℹ️ BT #{bt_id} n'est pas le premier du projet #{project_id}")
                        
        except Exception as e:
            st.warning(f"Erreur mise à jour projet: {e}")
            print(f"❌ Erreur mise à jour projet #{project_id}: {e}")
            # Continuer sans bloquer la création du BT
    
    def get_bons_travail(self, **filters) -> List[Dict]:
        """
        Récupère les Bons de Travail avec enrichissement depuis la vraie base
        
        Args:
            **filters: Filtres optionnels (project_id, employe_id, statut, etc.)
            
        Returns:
            List[Dict]: Liste des BT enrichis avec vraies données BD
        """
        try:
            # Récupération des BT de base
            bts = self.base.get_formulaires('BON_TRAVAIL', **filters)
            
            # Enrichissement avec vraies données de la base
            for bt in bts:
                try:
                    # Enrichir avec vraies données projet
                    if bt.get('project_id'):
                        bt.update(self._get_vraies_donnees_projet(bt['project_id']))
                    
                    # Enrichir avec vraies assignations
                    bt['assignations'] = self._get_vraies_assignations_bt(bt['id'])
                    
                    # Enrichir avec vraies réservations postes
                    bt['reservations_postes'] = self._get_vraies_reservations_postes_bt(bt['id'])
                    
                    # Calcul avancement basé sur vraies opérations
                    bt['avancement'] = self._calculer_avancement_reel_bt(bt['id'])
                    
                    # Parse métadonnées
                    bt['metadata_parsed'] = self._parse_metadata_bt(bt.get('metadonnees_json', '{}'))
                    
                except Exception as e_enrich:
                    print(f"⚠️ Erreur enrichissement BT #{bt['id']}: {e_enrich}")
                    bt['assignations'] = []
                    bt['reservations_postes'] = []
                    bt['avancement'] = {'pourcentage': 0, 'operations_terminees': 0, 'operations_totales': 0}
                    bt['metadata_parsed'] = {}
            
            print(f"✅ {len(bts)} BT récupéré(s) avec enrichissement depuis vraie base")
            return bts
            
        except Exception as e:
            st.error(f"Erreur récupération BT: {e}")
            print(f"❌ Erreur récupération BT: {e}")
            return []
    
    def _get_vraies_donnees_projet(self, project_id: int) -> Dict:
        """
        Récupère les vraies données du projet depuis la base
        
        Args:
            project_id: ID du projet
            
        Returns:
            Dict: Vraies données du projet
        """
        try:
            query = """
                SELECT p.nom_projet, p.statut as project_statut, p.priorite as project_priorite,
                       p.prix_estime, p.date_soumis, p.date_prevu, p.date_debut_reel, p.date_fin_reel,
                       c.nom as client_nom
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE p.id = ?
            """
            
            result = self.db.execute_query(query, (project_id,))
            return dict(result[0]) if result else {}
            
        except Exception as e:
            print(f"❌ Erreur données projet #{project_id}: {e}")
            return {}
    
    def _get_vraies_assignations_bt(self, bt_id: int) -> List[Dict]:
        """
        Récupère les vraies assignations depuis bt_assignations
        
        Args:
            bt_id: ID du BT
            
        Returns:
            List[Dict]: Vraies assignations avec infos employés
        """
        try:
            query = """
                SELECT 
                    a.*,
                    e.prenom || ' ' || e.nom as employe_nom,
                    e.poste,
                    e.departement,
                    e.email,
                    e.statut as employe_statut
                FROM bt_assignations a
                JOIN employees e ON a.employe_id = e.id
                WHERE a.bt_id = ?
                ORDER BY a.date_assignation
            """
            rows = self.db.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"❌ Erreur assignations BT #{bt_id}: {e}")
            return []
    
    def _get_vraies_reservations_postes_bt(self, bt_id: int) -> List[Dict]:
        """
        Récupère les vraies réservations depuis bt_reservations_postes
        
        Args:
            bt_id: ID du BT
            
        Returns:
            List[Dict]: Vraies réservations avec infos postes
        """
        try:
            query = """
                SELECT 
                    r.*,
                    w.nom as poste_nom,
                    w.departement,
                    w.categorie,
                    w.type_machine,
                    w.capacite_theorique,
                    w.statut as poste_statut
                FROM bt_reservations_postes r
                JOIN work_centers w ON r.work_center_id = w.id
                WHERE r.bt_id = ?
                ORDER BY r.date_prevue
            """
            rows = self.db.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"❌ Erreur réservations BT #{bt_id}: {e}")
            return []
    
    def _calculer_avancement_reel_bt(self, bt_id: int) -> Dict:
        """
        Calcule l'avancement basé sur les vraies opérations et bt_avancement
        
        Args:
            bt_id: ID du BT
            
        Returns:
            Dict: Avancement calculé depuis vraies données
        """
        try:
            # Récupérer l'avancement réel depuis bt_avancement
            query = """
                SELECT 
                    COUNT(*) as operations_totales,
                    COUNT(CASE WHEN pourcentage_realise >= 100 THEN 1 END) as operations_terminees,
                    AVG(pourcentage_realise) as pourcentage_moyen,
                    SUM(temps_reel) as temps_total_reel,
                    MIN(date_debut_reel) as debut_reel,
                    MAX(date_fin_reel) as fin_reel
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
                    'date_debut_reel': row['debut_reel'],
                    'date_fin_reel': row['fin_reel'],
                    'mode_calcul': 'vraies_donnees_bt_avancement'
                }
            
            # Fallback : calculer depuis les métadonnées si pas de suivi détaillé
            bt_details = self.base.get_formulaire_details(bt_id)
            if bt_details:
                try:
                    metadonnees = json.loads(bt_details.get('metadonnees_json', '{}'))
                    operations_ids = metadonnees.get('operations_selectionnees', [])
                    
                    if operations_ids:
                        # Vérifier statut des vraies opérations
                        operations_terminees = 0
                        for op_id in operations_ids:
                            query_op = "SELECT statut FROM operations WHERE id = ?"
                            result_op = self.db.execute_query(query_op, (op_id,))
                            if result_op and result_op[0]['statut'] == 'TERMINÉ':
                                operations_terminees += 1
                        
                        pourcentage = (operations_terminees / len(operations_ids) * 100) if operations_ids else 0
                        
                        return {
                            'pourcentage': round(pourcentage, 1),
                            'operations_terminees': operations_terminees,
                            'operations_totales': len(operations_ids),
                            'mode_calcul': 'statut_vraies_operations'
                        }
                except:
                    pass
            
            return {'pourcentage': 0, 'operations_terminees': 0, 'operations_totales': 0, 'mode_calcul': 'aucune_donnee'}
            
        except Exception as e:
            print(f"❌ Erreur calcul avancement BT #{bt_id}: {e}")
            return {'pourcentage': 0, 'operations_terminees': 0, 'operations_totales': 0, 'erreur': str(e)}
    
    def _parse_metadata_bt(self, metadonnees_json: str) -> Dict:
        """
        Parse les métadonnées JSON du BT de manière sécurisée
        
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
    
    def mettre_a_jour_avancement_operation_reelle(self, bt_id: int, operation_id: int, 
                                                 pourcentage: float, temps_reel: float = 0, 
                                                 notes: str = "", employe_id: int = None) -> bool:
        """
        Met à jour l'avancement d'une vraie opération du BT dans bt_avancement
        
        Args:
            bt_id: ID du BT
            operation_id: ID de la vraie opération depuis operations
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
            
            # Vérifier que l'opération existe vraiment
            operation_exists = self.db.execute_query(
                "SELECT description FROM operations WHERE id = ?",
                (operation_id,)
            )
            
            if not operation_exists:
                st.error(f"Opération #{operation_id} non trouvée")
                return False
            
            # Vérifier si l'enregistrement existe déjà
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
                        updated_at = CURRENT_TIMESTAMP,
                        date_fin_reel = CASE WHEN ? >= 100 THEN CURRENT_TIMESTAMP ELSE date_fin_reel END
                    WHERE bt_id = ? AND operation_id = ?
                """
                params = (pourcentage, temps_reel, notes, employe_id, pourcentage, bt_id, operation_id)
            else:
                # Création
                query = """
                    INSERT INTO bt_avancement 
                    (bt_id, operation_id, pourcentage_realise, temps_reel, notes_avancement, 
                     updated_by, date_debut_reel, date_fin_reel)
                    VALUES (?, ?, ?, ?, ?, ?, 
                            CASE WHEN ? > 0 THEN CURRENT_TIMESTAMP ELSE NULL END,
                            CASE WHEN ? >= 100 THEN CURRENT_TIMESTAMP ELSE NULL END)
                """
                params = (bt_id, operation_id, pourcentage, temps_reel, notes, employe_id, pourcentage, pourcentage)
            
            affected = self.db.execute_update(query, params)
            
            if affected > 0:
                st.success(f"✅ Avancement opération mis à jour: {pourcentage}%")
                print(f"✅ Avancement opération #{operation_id} mis à jour: {pourcentage}%")
                
                # Marquer l'opération comme terminée si 100%
                if pourcentage >= 100:
                    self._marquer_vraie_operation_terminee(operation_id)
                
                return True
            
            return False
            
        except Exception as e:
            st.error(f"Erreur mise à jour avancement: {e}")
            print(f"❌ Erreur avancement opération #{operation_id}: {e}")
            return False
    
    def _marquer_vraie_operation_terminee(self, operation_id: int) -> None:
        """
        Marque une vraie opération comme terminée dans la table operations
        
        Args:
            operation_id: ID de la vraie opération
        """
        try:
            query = """
                UPDATE operations 
                SET statut = 'TERMINÉ'
                WHERE id = ? AND statut != 'TERMINÉ'
            """
            affected = self.db.execute_update(query, (operation_id,))
            
            if affected > 0:
                print(f"✅ Vraie opération #{operation_id} marquée terminée")
                
        except Exception as e:
            print(f"❌ Erreur marquage vraie opération terminée #{operation_id}: {e}")
    
    def marquer_bt_termine(self, bt_id: int, employe_id: int, 
                          commentaires: str = "") -> bool:
        """
        Marque un BT comme terminé avec validations et traçabilité complète
        
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
                
                st.success(f"✅ Bon de Travail #{bt_id} marqué comme terminé!")
                print(f"✅ BT #{bt_id} marqué terminé par employé #{employe_id}")
            
            return success
            
        except Exception as e:
            st.error(f"Erreur fin BT: {e}")
            print(f"❌ Erreur fin BT #{bt_id}: {e}")
            return False
    
    def _employe_peut_terminer_bt(self, bt_id: int, employe_id: int) -> bool:
        """
        Vérifie si un employé peut terminer le BT
        
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
            assignations = self._get_vraies_assignations_bt(bt_id)
            employes_assignes = [a['employe_id'] for a in assignations if a.get('statut') == 'ASSIGNÉ']
            
            if employe_id in employes_assignes:
                return True
            
            # 3. Vérifier les permissions spéciales (ex: superviseur)
            # TODO: Implémenter système de permissions plus avancé
            
            return False
            
        except Exception as e:
            print(f"❌ Erreur vérification permissions BT #{bt_id}: {e}")
            return False
    
    def _finaliser_bt_termine(self, bt_id: int) -> None:
        """
        Actions de finalisation quand un BT est terminé
        
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
    
    def _liberer_reservations_postes(self, bt_id: int) -> None:
        """
        Libère les réservations de postes d'un BT terminé
        
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
        Finalise les assignations d'employés d'un BT terminé
        
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
        Marque toutes les opérations du BT comme terminées à 100%
        
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
        Vérifie si le projet est complètement terminé et met à jour son statut
        
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
        Calcule les statistiques des BT depuis la vraie base
        
        Returns:
            Dict: Statistiques enrichies depuis vraies données
        """
        try:
            # Statistiques de base
            stats_base = self.base.get_statistiques_formulaires().get('BON_TRAVAIL', {})
            
            # Enrichissement avec vraies données BT
            try:
                query = """
                    SELECT 
                        f.statut,
                        COUNT(*) as count,
                        AVG(julianday('now') - julianday(f.date_creation)) as duree_moyenne,
                        SUM(f.montant_total) as montant_total,
                        COUNT(DISTINCT f.project_id) as projets_concernes,
                        COUNT(DISTINCT f.employee_id) as employes_impliques
                    FROM formulaires f
                    WHERE f.type_formulaire = 'BON_TRAVAIL'
                    GROUP BY f.statut
                """
                
                rows = self.db.execute_query(query)
                
                stats_enrichies = {}
                total_bt = 0
                
                for row in rows:
                    statut = row['statut']
                    count = row['count']
                    total_bt += count
                    
                    stats_enrichies[f'{statut.lower()}'] = count
                    stats_enrichies['duree_moyenne'] = row['duree_moyenne'] or 0
                    stats_enrichies['montant_total'] = row['montant_total'] or 0
                    stats_enrichies['projets_concernes'] = row['projets_concernes'] or 0
                    stats_enrichies['employes_impliques'] = row['employes_impliques'] or 0
                
                # Calculer taux de completion
                termines = stats_enrichies.get('terminé', 0)
                if total_bt > 0:
                    stats_enrichies['taux_completion'] = (termines / total_bt) * 100
                else:
                    stats_enrichies['taux_completion'] = 0
                
                # Ajouter aux stats de base
                stats_base.update(stats_enrichies)
                
                print(f"✅ Statistiques BT calculées depuis vraie base: {total_bt} BT")
                
            except Exception as e:
                st.warning(f"Erreur statistiques enrichies BT: {e}")
                print(f"⚠️ Erreur stats enrichies BT: {e}")
            
            # Ajouter statistiques assignations/réservations réelles
            try:
                stats_assignations = self._get_vraies_statistiques_assignations()
                stats_reservations = self._get_vraies_statistiques_reservations()
                
                stats_base.update(stats_assignations)
                stats_base.update(stats_reservations)
                
            except Exception as e:
                print(f"⚠️ Erreur stats assignations/réservations: {e}")
            
            return stats_base
            
        except Exception as e:
            st.error(f"Erreur stats BT: {e}")
            print(f"❌ Erreur statistiques BT: {e}")
            return {}
    
    def _get_vraies_statistiques_assignations(self) -> Dict:
        """
        Calcule les vraies statistiques des assignations depuis bt_assignations
        
        Returns:
            Dict: Statistiques assignations réelles
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
                    'assignations_actives_reelles': row['total_assignations'],
                    'employes_assignes_bt_reels': row['employes_assignes_uniques'],
                    'bt_avec_equipe_reelle': row['bt_avec_assignations']
                }
            
            return {}
            
        except Exception as e:
            print(f"❌ Erreur stats assignations réelles: {e}")
            return {}
    
    def _get_vraies_statistiques_reservations(self) -> Dict:
        """
        Calcule les vraies statistiques des réservations depuis bt_reservations_postes
        
        Returns:
            Dict: Statistiques réservations réelles
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
                    'reservations_postes_total_reelles': row['total_reservations'],
                    'postes_utilises_bt_reels': row['postes_reserves_uniques'],
                    'reservations_actives_reelles': row['reservations_actives']
                }
            
            return {}
            
        except Exception as e:
            print(f"❌ Erreur stats réservations réelles: {e}")
            return {}
    
    def generer_rapport_productivite(self, periode_jours: int = 30) -> Dict:
        """
        Génère un rapport de productivité basé sur les vraies données
        
        Args:
            periode_jours: Période d'analyse en jours
            
        Returns:
            Dict: Rapport basé sur vraies données BD
        """
        try:
            date_debut = datetime.now() - timedelta(days=periode_jours)
            
            # Requête avec vraies données employés et projets
            query = """
                SELECT 
                    e.prenom || ' ' || e.nom as employe_nom,
                    e.poste,
                    e.departement,
                    COUNT(f.id) as nb_bt_termines,
                    AVG(julianday(f.updated_at) - julianday(f.date_creation)) as duree_moyenne,
                    SUM(f.montant_total) as montant_total_travaux,
                    MIN(f.date_creation) as premier_bt_periode,
                    MAX(f.updated_at) as dernier_bt_termine,
                    COUNT(DISTINCT f.project_id) as projets_touches
                FROM formulaires f
                JOIN employees e ON f.employee_id = e.id
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                AND f.statut = 'TERMINÉ'
                AND f.updated_at >= ?
                GROUP BY f.employee_id, e.prenom, e.nom, e.poste, e.departement
                ORDER BY nb_bt_termines DESC
            """
            
            rows = self.db.execute_query(query, (date_debut.isoformat(),))
            
            # Statistiques globales vraies
            query_global = """
                SELECT 
                    COUNT(*) as total_bt_crees,
                    COUNT(CASE WHEN statut = 'TERMINÉ' THEN 1 END) as total_bt_termines,
                    AVG(montant_total) as montant_moyen,
                    SUM(montant_total) as montant_total_periode,
                    COUNT(DISTINCT project_id) as projets_impactes
                FROM formulaires
                WHERE type_formulaire = 'BON_TRAVAIL'
                AND date_creation >= ?
            """
            
            result_global = self.db.execute_query(query_global, (date_debut.isoformat(),))
            
            # Construction du rapport avec vraies données
            rapport = {
                'periode': f"{periode_jours} derniers jours",
                'date_generation': datetime.now().isoformat(),
                'date_debut_analyse': date_debut.isoformat(),
                'employes': [dict(row) for row in rows],
                'statistiques_globales': dict(result_global[0]) if result_global else {},
                'analyse': {},
                'source_donnees': 'vraie_base_sqlite'
            }
            
            # Calculs d'analyse enrichis
            if rapport['employes']:
                rapport['total_bt_termines'] = sum(emp['nb_bt_termines'] for emp in rapport['employes'])
                rapport['duree_moyenne_globale'] = sum(emp['duree_moyenne'] or 0 for emp in rapport['employes']) / len(rapport['employes'])
                
                # Analyses enrichies
                rapport['analyse']['top_performer'] = max(rapport['employes'], key=lambda x: x['nb_bt_termines'])
                rapport['analyse']['plus_efficace'] = min(rapport['employes'], key=lambda x: x['duree_moyenne'] or float('inf'))
                rapport['analyse']['plus_rentable'] = max(rapport['employes'], key=lambda x: x['montant_total_travaux'] or 0)
                rapport['analyse']['plus_polyvalent'] = max(rapport['employes'], key=lambda x: x['projets_touches'] or 0)
            else:
                rapport['total_bt_termines'] = 0
                rapport['duree_moyenne_globale'] = 0
                rapport['analyse'] = {'message': 'Aucune donnée disponible pour la période depuis la vraie base'}
            
            # Recommandations basées sur vraies données
            rapport['recommandations'] = self._generer_recommandations_productivite_reelles(rapport)
            
            print(f"✅ Rapport productivité généré depuis vraie base pour {periode_jours} jours")
            return rapport
            
        except Exception as e:
            st.error(f"Erreur rapport productivité: {e}")
            print(f"❌ Erreur rapport productivité: {e}")
            return {}
    
    def _generer_recommandations_productivite_reelles(self, rapport: Dict) -> List[str]:
        """
        Génère des recommandations basées sur l'analyse des vraies données
        
        Args:
            rapport: Données du rapport depuis vraie base
            
        Returns:
            List[str]: Recommandations basées sur vraies données
        """
        recommandations = []
        
        try:
            employes = rapport.get('employes', [])
            if not employes:
                return ["Aucune donnée suffisante depuis la vraie base pour générer des recommandations"]
            
            # Analyses basées sur vraies données
            nb_bt_values = [emp['nb_bt_termines'] for emp in employes]
            durees = [emp['duree_moyenne'] for emp in employes if emp['duree_moyenne']]
            projets_values = [emp['projets_touches'] for emp in employes]
            
            if nb_bt_values:
                nb_bt_max = max(nb_bt_values)
                nb_bt_min = min(nb_bt_values)
                
                if nb_bt_max - nb_bt_min > 3:
                    recommandations.append("📊 Équilibrer la charge de travail BT entre les employés")
            
            if durees:
                duree_max = max(durees)
                duree_moyenne = sum(durees) / len(durees)
                
                if duree_max > duree_moyenne * 1.5:
                    recommandations.append("⏱️ Identifier les causes des retards sur certains BT")
            
            if projets_values:
                projets_max = max(projets_values)
                if projets_max > 5:
                    recommandations.append("🎯 Considérer la spécialisation par type de projet")
            
            # Analyse par département (vraies données)
            depts = {}
            for emp in employes:
                dept = emp.get('departement', 'N/A')
                if dept not in depts:
                    depts[dept] = []
                depts[dept].append(emp['nb_bt_termines'])
            
            if len(depts) > 1:
                recommandations.append("🏢 Analyser les différences de performance entre départements réels")
            
            # Recommandations spécifiques
            if len(employes) < 3:
                recommandations.append("👥 Considérer l'augmentation de l'équipe pour les BT")
            
            # Recommandations spécifiques DG Inc.
            recommandations.append("🔧 Optimiser l'utilisation des postes de travail DG Inc.")
            recommandations.append("📋 Améliorer la définition des opérations dans les projets")
            
            if not recommandations:
                recommandations.append("✅ Performance globale satisfaisante selon les vraies données")
            
        except Exception as e:
            print(f"❌ Erreur génération recommandations réelles: {e}")
            recommandations.append("⚠️ Erreur dans l'analyse des vraies données")
        
        return recommandations
    
    def get_bt_details_complets(self, bt_id: int) -> Optional[Dict]:
        """
        Récupère tous les détails complets d'un BT spécifique avec vraies données
        
        Args:
            bt_id: ID du BT
            
        Returns:
            Optional[Dict]: Détails complets du BT enrichis
        """
        try:
            # Détails de base
            bt_details = self.base.get_formulaire_details(bt_id)
            if not bt_details:
                return None
            
            # Enrichissement complet avec vraies données
            bt_details['assignations'] = self._get_vraies_assignations_bt(bt_id)
            bt_details['reservations_postes'] = self._get_vraies_reservations_postes_bt(bt_id)
            bt_details['avancement_detaille'] = self._get_avancement_detaille_bt(bt_id)
            bt_details['lignes_materiaux'] = self._get_lignes_materiaux_bt(bt_id)
            bt_details['historique_modifications'] = self._get_historique_bt(bt_id)
            bt_details['metadata_parsed'] = self._parse_metadata_bt(bt_details.get('metadonnees_json', '{}'))
            
            # Enrichir avec données projet si disponible
            if bt_details.get('project_id'):
                bt_details.update(self._get_vraies_donnees_projet(bt_details['project_id']))
            
            print(f"✅ Détails complets récupérés pour BT #{bt_id}")
            return bt_details
            
        except Exception as e:
            st.error(f"Erreur récupération détails BT: {e}")
            print(f"❌ Erreur détails BT #{bt_id}: {e}")
            return None
    
    def _get_avancement_detaille_bt(self, bt_id: int) -> List[Dict]:
        """
        Récupère l'avancement détaillé de toutes les opérations du BT
        
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
                    o.statut as operation_statut,
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
    
    def _get_lignes_materiaux_bt(self, bt_id: int) -> List[Dict]:
        """
        Récupère les lignes de matériaux du BT
        
        Args:
            bt_id: ID du BT
            
        Returns:
            List[Dict]: Lignes de matériaux
        """
        try:
            query = """
                SELECT 
                    fl.*,
                    m.designation as materiau_designation,
                    m.stock_actuel
                FROM formulaire_lignes fl
                LEFT JOIN materials m ON fl.reference_materiau = m.id
                WHERE fl.formulaire_id = ?
                ORDER BY fl.sequence_ligne
            """
            
            rows = self.db.execute_query(query, (bt_id,))
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"❌ Erreur lignes matériaux BT #{bt_id}: {e}")
            return []
    
    def _get_historique_bt(self, bt_id: int) -> List[Dict]:
        """
        Récupère l'historique des modifications du BT
        
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
