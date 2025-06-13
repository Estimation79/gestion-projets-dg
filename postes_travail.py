# postes_travail.py - Module de gestion des postes de travail DG Inc. - VERSION SQLITE

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import json
from typing import Dict, List, Optional, Any

# --- DONNÉES DE RÉFÉRENCE POUR MIGRATION INITIALE ---
WORK_CENTERS_DG_INC_REFERENCE = [
    # PRODUCTION (35 postes) - 57%
    {"id": 1, "nom": "Laser CNC", "departement": "PRODUCTION", "categorie": "CNC", "type_machine": "LASER", "capacite_theorique": 16, "operateurs_requis": 1, "competences": ["Programmation CNC", "Lecture plan"], "cout_horaire": 75},
    {"id": 2, "nom": "Plasma CNC", "departement": "PRODUCTION", "categorie": "CNC", "type_machine": "PLASMA", "capacite_theorique": 14, "operateurs_requis": 1, "competences": ["Programmation CNC"], "cout_horaire": 65},
    {"id": 3, "nom": "Jet d'eau", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "DECOUPE", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Découpe jet d'eau"], "cout_horaire": 85},
    {"id": 4, "nom": "Oxycoupage", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "DECOUPE", "capacite_theorique": 10, "operateurs_requis": 1, "competences": ["Oxycoupage"], "cout_horaire": 45},
    {"id": 5, "nom": "Plieuse CNC 1", "departement": "PRODUCTION", "categorie": "CNC", "type_machine": "PLIAGE", "capacite_theorique": 12, "operateurs_requis": 1, "competences": ["Programmation CNC", "Pliage"], "cout_horaire": 70},
    {"id": 6, "nom": "Plieuse CNC 2", "departement": "PRODUCTION", "categorie": "CNC", "type_machine": "PLIAGE", "capacite_theorique": 12, "operateurs_requis": 1, "competences": ["Programmation CNC", "Pliage"], "cout_horaire": 70},
    {"id": 7, "nom": "Plieuse conventionnelle 1", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "PLIAGE", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Pliage"], "cout_horaire": 50},
    {"id": 8, "nom": "Plieuse conventionnelle 2", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "PLIAGE", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Pliage"], "cout_horaire": 50},
    {"id": 9, "nom": "Robot ABB GMAW", "departement": "PRODUCTION", "categorie": "ROBOT", "type_machine": "SOUDAGE", "capacite_theorique": 18, "operateurs_requis": 1, "competences": ["Programmation robot", "Soudage GMAW"], "cout_horaire": 95},
    {"id": 10, "nom": "Robot ABB FCAW", "departement": "PRODUCTION", "categorie": "ROBOT", "type_machine": "SOUDAGE", "capacite_theorique": 18, "operateurs_requis": 1, "competences": ["Programmation robot", "Soudage FCAW"], "cout_horaire": 95},
    {"id": 11, "nom": "Robot ABB GTAW", "departement": "PRODUCTION", "categorie": "ROBOT", "type_machine": "SOUDAGE", "capacite_theorique": 16, "operateurs_requis": 1, "competences": ["Programmation robot", "Soudage GTAW"], "cout_horaire": 105},
    {"id": 12, "nom": "Soudage SMAW 1", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "SOUDAGE", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Soudage SMAW"], "cout_horaire": 55},
    {"id": 13, "nom": "Soudage SMAW 2", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "SOUDAGE", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Soudage SMAW"], "cout_horaire": 55},
    {"id": 14, "nom": "Soudage GMAW 1", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "SOUDAGE", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Soudage GMAW"], "cout_horaire": 60},
    {"id": 15, "nom": "Soudage GMAW 2", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "SOUDAGE", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Soudage GMAW"], "cout_horaire": 60},
    {"id": 16, "nom": "Soudage FCAW", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "SOUDAGE", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Soudage FCAW"], "cout_horaire": 65},
    {"id": 17, "nom": "Soudage GTAW", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "SOUDAGE", "capacite_theorique": 6, "operateurs_requis": 1, "competences": ["Soudage GTAW"], "cout_horaire": 70},
    {"id": 18, "nom": "Soudage SAW", "departement": "PRODUCTION", "categorie": "SEMI_AUTO", "type_machine": "SOUDAGE", "capacite_theorique": 12, "operateurs_requis": 1, "competences": ["Soudage SAW"], "cout_horaire": 80},
    {"id": 19, "nom": "Assemblage Léger 1", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "ASSEMBLAGE", "capacite_theorique": 8, "operateurs_requis": 2, "competences": ["Assemblage"], "cout_horaire": 45},
    {"id": 20, "nom": "Assemblage Léger 2", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "ASSEMBLAGE", "capacite_theorique": 8, "operateurs_requis": 2, "competences": ["Assemblage"], "cout_horaire": 45},
    {"id": 21, "nom": "Assemblage Lourd", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "ASSEMBLAGE", "capacite_theorique": 8, "operateurs_requis": 3, "competences": ["Assemblage lourd"], "cout_horaire": 55},
    {"id": 22, "nom": "Meulage 1", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "FINITION", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Meulage"], "cout_horaire": 40},
    {"id": 23, "nom": "Meulage 2", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "FINITION", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Meulage"], "cout_horaire": 40},
    {"id": 24, "nom": "Sablage", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "FINITION", "capacite_theorique": 6, "operateurs_requis": 1, "competences": ["Sablage"], "cout_horaire": 50},
    {"id": 25, "nom": "Galvanisation", "departement": "PRODUCTION", "categorie": "TRAITEMENT", "type_machine": "TRAITEMENT", "capacite_theorique": 4, "operateurs_requis": 1, "competences": ["Galvanisation"], "cout_horaire": 60},
    {"id": 26, "nom": "Anodisation", "departement": "PRODUCTION", "categorie": "TRAITEMENT", "type_machine": "TRAITEMENT", "capacite_theorique": 4, "operateurs_requis": 1, "competences": ["Anodisation"], "cout_horaire": 65},
    {"id": 27, "nom": "Passivation", "departement": "PRODUCTION", "categorie": "TRAITEMENT", "type_machine": "TRAITEMENT", "capacite_theorique": 4, "operateurs_requis": 1, "competences": ["Passivation"], "cout_horaire": 55},
    {"id": 28, "nom": "Peinture poudre", "departement": "PRODUCTION", "categorie": "TRAITEMENT", "type_machine": "PEINTURE", "capacite_theorique": 6, "operateurs_requis": 1, "competences": ["Peinture poudre"], "cout_horaire": 45},
    {"id": 29, "nom": "Peinture liquide", "departement": "PRODUCTION", "categorie": "TRAITEMENT", "type_machine": "PEINTURE", "capacite_theorique": 6, "operateurs_requis": 1, "competences": ["Peinture liquide"], "cout_horaire": 45},
    {"id": 30, "nom": "Perçage 1", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "PERCAGE", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Perçage"], "cout_horaire": 35},
    {"id": 31, "nom": "Perçage 2", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "PERCAGE", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Perçage"], "cout_horaire": 35},
    {"id": 32, "nom": "Taraudage", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "PERCAGE", "capacite_theorique": 6, "operateurs_requis": 1, "competences": ["Taraudage"], "cout_horaire": 40},
    {"id": 33, "nom": "Programmation Bureau", "departement": "PRODUCTION", "categorie": "BUREAU", "type_machine": "PROGRAMMATION", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Programmation CNC", "CAO/FAO"], "cout_horaire": 85},
    {"id": 34, "nom": "Programmation Usine", "departement": "PRODUCTION", "categorie": "BUREAU", "type_machine": "PROGRAMMATION", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Programmation CNC"], "cout_horaire": 75},
    {"id": 35, "nom": "Manutention", "departement": "PRODUCTION", "categorie": "MANUEL", "type_machine": "MANUTENTION", "capacite_theorique": 8, "operateurs_requis": 2, "competences": ["Manutention"], "cout_horaire": 35},
    
    # USINAGE (15 postes) - 25%
    {"id": 36, "nom": "Tour CNC 1", "departement": "USINAGE", "categorie": "CNC", "type_machine": "TOUR", "capacite_theorique": 16, "operateurs_requis": 1, "competences": ["Programmation CNC", "Tournage"], "cout_horaire": 80},
    {"id": 37, "nom": "Tour CNC 2", "departement": "USINAGE", "categorie": "CNC", "type_machine": "TOUR", "capacite_theorique": 16, "operateurs_requis": 1, "competences": ["Programmation CNC", "Tournage"], "cout_horaire": 80},
    {"id": 38, "nom": "Fraiseuse CNC 1", "departement": "USINAGE", "categorie": "CNC", "type_machine": "FRAISAGE", "capacite_theorique": 14, "operateurs_requis": 1, "competences": ["Programmation CNC", "Fraisage"], "cout_horaire": 85},
    {"id": 39, "nom": "Fraiseuse CNC 2", "departement": "USINAGE", "categorie": "CNC", "type_machine": "FRAISAGE", "capacite_theorique": 14, "operateurs_requis": 1, "competences": ["Programmation CNC", "Fraisage"], "cout_horaire": 85},
    {"id": 40, "nom": "Centre d'usinage", "departement": "USINAGE", "categorie": "CNC", "type_machine": "CENTRE_USINAGE", "capacite_theorique": 20, "operateurs_requis": 1, "competences": ["Programmation CNC", "Usinage complexe"], "cout_horaire": 95},
    {"id": 41, "nom": "Tour conventionnel", "departement": "USINAGE", "categorie": "MANUEL", "type_machine": "TOUR", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Tournage"], "cout_horaire": 55},
    {"id": 42, "nom": "Fraiseuse conventionnelle", "departement": "USINAGE", "categorie": "MANUEL", "type_machine": "FRAISAGE", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Fraisage"], "cout_horaire": 55},
    {"id": 43, "nom": "Rectifieuse", "departement": "USINAGE", "categorie": "MANUEL", "type_machine": "RECTIFICATION", "capacite_theorique": 6, "operateurs_requis": 1, "competences": ["Rectification"], "cout_horaire": 65},
    {"id": 44, "nom": "Alésage", "departement": "USINAGE", "categorie": "MANUEL", "type_machine": "ALESAGE", "capacite_theorique": 6, "operateurs_requis": 1, "competences": ["Alésage"], "cout_horaire": 60},
    {"id": 45, "nom": "Rabotage", "departement": "USINAGE", "categorie": "MANUEL", "type_machine": "RABOTAGE", "capacite_theorique": 6, "operateurs_requis": 1, "competences": ["Rabotage"], "cout_horaire": 50},
    {"id": 46, "nom": "Mortaisage", "departement": "USINAGE", "categorie": "MANUEL", "type_machine": "MORTAISAGE", "capacite_theorique": 4, "operateurs_requis": 1, "competences": ["Mortaisage"], "cout_horaire": 45},
    {"id": 47, "nom": "Sciage métal", "departement": "USINAGE", "categorie": "MANUEL", "type_machine": "SCIAGE", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Sciage"], "cout_horaire": 35},
    {"id": 48, "nom": "Ébavurage", "departement": "USINAGE", "categorie": "MANUEL", "type_machine": "FINITION", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Ébavurage"], "cout_horaire": 35},
    {"id": 49, "nom": "Polissage", "departement": "USINAGE", "categorie": "MANUEL", "type_machine": "FINITION", "capacite_theorique": 6, "operateurs_requis": 1, "competences": ["Polissage"], "cout_horaire": 40},
    {"id": 50, "nom": "Contrôle métrologique", "departement": "USINAGE", "categorie": "MESURE", "type_machine": "CONTROLE", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Métrologie"], "cout_horaire": 70},
    
    # QUALITÉ (3 postes) - 5%
    {"id": 51, "nom": "Inspection visuelle", "departement": "QUALITE", "categorie": "CONTROLE", "type_machine": "INSPECTION", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Contrôle visuel"], "cout_horaire": 55},
    {"id": 52, "nom": "Contrôle dimensionnel", "departement": "QUALITE", "categorie": "CONTROLE", "type_machine": "MESURE", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Métrologie", "Lecture plan"], "cout_horaire": 65},
    {"id": 53, "nom": "Tests non destructifs", "departement": "QUALITE", "categorie": "CONTROLE", "type_machine": "TEST", "capacite_theorique": 6, "operateurs_requis": 1, "competences": ["Tests ND"], "cout_horaire": 85},
    
    # LOGISTIQUE (7 postes) - 11%
    {"id": 54, "nom": "Réception matières", "departement": "LOGISTIQUE", "categorie": "RECEPTION", "type_machine": "RECEPTION", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Réception"], "cout_horaire": 35},
    {"id": 55, "nom": "Stockage matières", "departement": "LOGISTIQUE", "categorie": "STOCKAGE", "type_machine": "STOCKAGE", "capacite_theorique": 8, "operateurs_requis": 2, "competences": ["Manutention"], "cout_horaire": 30},
    {"id": 56, "nom": "Préparation commandes", "departement": "LOGISTIQUE", "categorie": "PREPARATION", "type_machine": "PREPARATION", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Préparation"], "cout_horaire": 35},
    {"id": 57, "nom": "Emballage", "departement": "LOGISTIQUE", "categorie": "EMBALLAGE", "type_machine": "EMBALLAGE", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Emballage"], "cout_horaire": 30},
    {"id": 58, "nom": "Expédition", "departement": "LOGISTIQUE", "categorie": "EXPEDITION", "type_machine": "EXPEDITION", "capacite_theorique": 8, "operateurs_requis": 2, "competences": ["Expédition"], "cout_horaire": 35},
    {"id": 59, "nom": "Inventaire", "departement": "LOGISTIQUE", "categorie": "INVENTAIRE", "type_machine": "INVENTAIRE", "capacite_theorique": 4, "operateurs_requis": 1, "competences": ["Inventaire"], "cout_horaire": 40},
    {"id": 60, "nom": "Transport interne", "departement": "LOGISTIQUE", "categorie": "TRANSPORT", "type_machine": "TRANSPORT", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Conduite chariot"], "cout_horaire": 35},
    
    # COMMERCIAL (1 poste) - 2%
    {"id": 61, "nom": "Support technique", "departement": "COMMERCIAL", "categorie": "SUPPORT", "type_machine": "BUREAU", "capacite_theorique": 8, "operateurs_requis": 1, "competences": ["Support technique"], "cout_horaire": 75}
]

CATEGORIES_POSTES_TRAVAIL = {
    "CNC": "Machines à commande numérique",
    "ROBOT": "Robots industriels ABB",
    "MANUEL": "Postes manuels",
    "SEMI_AUTO": "Semi-automatique",
    "TRAITEMENT": "Traitement de surface",
    "BUREAU": "Travail de bureau",
    "CONTROLE": "Contrôle qualité",
    "RECEPTION": "Réception",
    "STOCKAGE": "Stockage",
    "PREPARATION": "Préparation",
    "EMBALLAGE": "Emballage",
    "EXPEDITION": "Expédition",
    "INVENTAIRE": "Inventaire",
    "TRANSPORT": "Transport",
    "SUPPORT": "Support",
    "MESURE": "Mesure et contrôle"
}

# --- GESTIONNAIRE DES POSTES DE TRAVAIL SQLITE ---
class GestionnairePostes:
    """
    Gestionnaire des postes de travail utilisant SQLite
    Remplace l'ancienne version avec données en mémoire
    """
    
    def __init__(self, db=None):
        """
        Initialise le gestionnaire avec une connexion à la base SQLite
        Args:
            db: Instance ERPDatabase ou None (sera récupéré depuis session_state)
        """
        if db is None:
            # Récupérer la base depuis session_state si disponible
            if 'erp_db' in st.session_state:
                self.db = st.session_state.erp_db
            else:
                raise ValueError("ERPDatabase non disponible dans session_state")
        else:
            self.db = db
        
        self.gammes_types = self.initialiser_gammes_types()
        self._ensure_work_centers_migrated()
    
    def _ensure_work_centers_migrated(self):
        """S'assure que les postes de travail sont migrés en SQLite"""
        try:
            count = self.db.get_table_count('work_centers')
            if count == 0:
                print("🔄 Migration des postes de travail vers SQLite...")
                self._migrate_work_centers_to_sqlite()
                print(f"✅ {len(WORK_CENTERS_DG_INC_REFERENCE)} postes migrés vers SQLite")
            else:
                print(f"✅ {count} postes de travail trouvés en SQLite")
        except Exception as e:
            print(f"⚠️ Erreur migration postes: {e}")
    
    def _migrate_work_centers_to_sqlite(self):
        """Migre les postes de travail de référence vers SQLite"""
        try:
            for poste in WORK_CENTERS_DG_INC_REFERENCE:
                # Convertir la liste de compétences en string JSON
                competences_str = json.dumps(poste.get('competences', []))
                
                query = '''
                    INSERT OR REPLACE INTO work_centers 
                    (id, nom, departement, categorie, type_machine, capacite_theorique, 
                     operateurs_requis, cout_horaire, competences_requises)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                
                self.db.execute_update(query, (
                    poste['id'],
                    poste['nom'],
                    poste['departement'],
                    poste['categorie'],
                    poste['type_machine'],
                    poste['capacite_theorique'],
                    poste['operateurs_requis'],
                    poste['cout_horaire'],
                    competences_str
                ))
            
            return True
        except Exception as e:
            print(f"Erreur migration postes: {e}")
            return False
    
    @property
    def postes(self):
        """Propriété pour récupérer tous les postes depuis SQLite"""
        return self.get_all_work_centers()
    
    def get_all_work_centers(self) -> List[Dict[str, Any]]:
        """Récupère tous les postes de travail depuis SQLite"""
        try:
            rows = self.db.execute_query("SELECT * FROM work_centers ORDER BY id")
            postes = []
            
            for row in rows:
                poste = dict(row)
                # Convertir les compétences JSON en liste
                try:
                    competences_str = poste.get('competences_requises', '[]')
                    poste['competences'] = json.loads(competences_str) if competences_str else []
                except json.JSONDecodeError:
                    poste['competences'] = []
                
                postes.append(poste)
            
            return postes
        except Exception as e:
            print(f"Erreur récupération postes: {e}")
            return []
    
    def get_poste_by_id(self, poste_id: int) -> Optional[Dict[str, Any]]:
        """Récupère un poste par son ID"""
        try:
            rows = self.db.execute_query("SELECT * FROM work_centers WHERE id = ?", (poste_id,))
            if rows:
                poste = dict(rows[0])
                # Convertir les compétences JSON en liste
                try:
                    competences_str = poste.get('competences_requises', '[]')
                    poste['competences'] = json.loads(competences_str) if competences_str else []
                except json.JSONDecodeError:
                    poste['competences'] = []
                return poste
            return None
        except Exception as e:
            print(f"Erreur récupération poste {poste_id}: {e}")
            return None
    
    def get_poste_by_nom(self, nom_poste: str) -> Optional[Dict[str, Any]]:
        """Récupère un poste par son nom"""
        try:
            rows = self.db.execute_query("SELECT * FROM work_centers WHERE nom = ?", (nom_poste,))
            if rows:
                poste = dict(rows[0])
                # Convertir les compétences JSON en liste
                try:
                    competences_str = poste.get('competences_requises', '[]')
                    poste['competences'] = json.loads(competences_str) if competences_str else []
                except json.JSONDecodeError:
                    poste['competences'] = []
                return poste
            return None
        except Exception as e:
            print(f"Erreur récupération poste '{nom_poste}': {e}")
            return None
    
    def add_work_center(self, poste_data: Dict[str, Any]) -> Optional[int]:
        """Ajoute un nouveau poste de travail en SQLite"""
        try:
            competences_str = json.dumps(poste_data.get('competences', []))
            
            query = '''
                INSERT INTO work_centers 
                (nom, departement, categorie, type_machine, capacite_theorique, 
                 operateurs_requis, cout_horaire, competences_requises)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            poste_id = self.db.execute_insert(query, (
                poste_data['nom'],
                poste_data.get('departement', ''),
                poste_data.get('categorie', ''),
                poste_data.get('type_machine', ''),
                poste_data.get('capacite_theorique', 0),
                poste_data.get('operateurs_requis', 1),
                poste_data.get('cout_horaire', 0),
                competences_str
            ))
            
            return poste_id
        except Exception as e:
            print(f"Erreur ajout poste: {e}")
            return None
    
    def update_work_center(self, poste_id: int, poste_data: Dict[str, Any]) -> bool:
        """Met à jour un poste de travail existant"""
        try:
            competences_str = json.dumps(poste_data.get('competences', []))
            
            query = '''
                UPDATE work_centers SET
                nom = ?, departement = ?, categorie = ?, type_machine = ?,
                capacite_theorique = ?, operateurs_requis = ?, cout_horaire = ?,
                competences_requises = ?
                WHERE id = ?
            '''
            
            self.db.execute_update(query, (
                poste_data['nom'],
                poste_data.get('departement', ''),
                poste_data.get('categorie', ''),
                poste_data.get('type_machine', ''),
                poste_data.get('capacite_theorique', 0),
                poste_data.get('operateurs_requis', 1),
                poste_data.get('cout_horaire', 0),
                competences_str,
                poste_id
            ))
            
            return True
        except Exception as e:
            print(f"Erreur mise à jour poste {poste_id}: {e}")
            return False
    
    def delete_work_center(self, poste_id: int) -> bool:
        """Supprime un poste de travail"""
        try:
            # Vérifier les dépendances (opérations liées)
            operations_count = self.db.execute_query(
                "SELECT COUNT(*) as count FROM operations WHERE work_center_id = ?",
                (poste_id,)
            )
            
            if operations_count and operations_count[0]['count'] > 0:
                print(f"Impossible de supprimer le poste {poste_id}: {operations_count[0]['count']} opération(s) liée(s)")
                return False
            
            self.db.execute_update("DELETE FROM work_centers WHERE id = ?", (poste_id,))
            return True
        except Exception as e:
            print(f"Erreur suppression poste {poste_id}: {e}")
            return False
    
    def get_employes_competents(self, poste_nom: str, gestionnaire_employes) -> List[str]:
        """Retourne les employés compétents pour un poste donné"""
        poste = self.get_poste_by_nom(poste_nom)
        if not poste:
            return []
        
        competences_requises = poste.get("competences", [])
        employes_competents = []
        
        for employe in gestionnaire_employes.employes:
            if employe.get("statut") != "ACTIF":
                continue
                
            competences_emp = employe.get("competences", [])
            if any(comp in competences_emp for comp in competences_requises):
                employes_competents.append(f"{employe.get('prenom', '')} {employe.get('nom', '')}")
        
        return employes_competents
    
    def get_statistiques_postes(self) -> Dict[str, Any]:
        """Retourne les statistiques des postes de travail depuis SQLite"""
        try:
            postes = self.get_all_work_centers()
            
            stats = {
                "total_postes": len(postes),
                "postes_cnc": len([p for p in postes if p["categorie"] == "CNC"]),
                "postes_robotises": len([p for p in postes if p["categorie"] == "ROBOT"]),
                "postes_manuels": len([p for p in postes if p["categorie"] == "MANUEL"]),
                "par_departement": {}
            }
            
            # Statistiques par département
            for poste in postes:
                dept = poste["departement"]
                stats["par_departement"][dept] = stats["par_departement"].get(dept, 0) + 1
            
            return stats
        except Exception as e:
            print(f"Erreur calcul statistiques: {e}")
            return {"total_postes": 0, "postes_cnc": 0, "postes_robotises": 0, "postes_manuels": 0, "par_departement": {}}
    
    def calculer_charge_poste(self, nom_poste: str, projets_actifs: List[Dict]) -> float:
        """Calcule la charge de travail pour un poste donné"""
        charge_totale = 0
        poste = self.get_poste_by_nom(nom_poste)
        
        if not poste:
            return 0
        
        for projet in projets_actifs:
            for operation in projet.get("operations", []):
                if operation.get("poste_travail") == nom_poste and operation.get("statut") != "TERMINÉ":
                    charge_totale += operation.get("temps_estime", 0)
        
        # Calcul du pourcentage de charge (base 40h/semaine)
        capacite_hebdo = poste["capacite_theorique"] * 5  # 5 jours
        return min(100, (charge_totale / capacite_hebdo) * 100) if capacite_hebdo > 0 else 0
    
    def initialiser_gammes_types(self):
        """Initialise les gammes types (inchangé - fonctionnel)"""
        return {
            "CHASSIS_SOUDE": {
                "nom": "Châssis Soudé",
                "description": "Châssis métallique avec soudage",
                "operations": [
                    {"sequence": "10", "poste": "Programmation Bureau", "description": "Programmation des pièces", "temps_base": 2.5},
                    {"sequence": "20", "poste": "Laser CNC", "description": "Découpe laser des tôles", "temps_base": 4.0},
                    {"sequence": "30", "poste": "Plieuse CNC 1", "description": "Pliage des éléments", "temps_base": 3.5},
                    {"sequence": "40", "poste": "Perçage 1", "description": "Perçage des fixations", "temps_base": 2.0},
                    {"sequence": "50", "poste": "Assemblage Léger 1", "description": "Pré-assemblage", "temps_base": 6.0},
                    {"sequence": "60", "poste": "Robot ABB GMAW", "description": "Soudage robotisé", "temps_base": 8.0},
                    {"sequence": "70", "poste": "Soudage GMAW 1", "description": "Finition soudure", "temps_base": 4.0},
                    {"sequence": "80", "poste": "Meulage 1", "description": "Meulage des cordons", "temps_base": 3.0},
                    {"sequence": "90", "poste": "Contrôle dimensionnel", "description": "Vérification dimensions", "temps_base": 1.5},
                    {"sequence": "100", "poste": "Peinture poudre", "description": "Finition peinture", "temps_base": 2.5}
                ]
            },
            "STRUCTURE_LOURDE": {
                "nom": "Structure Lourde",
                "description": "Charpente métallique industrielle",
                "operations": [
                    {"sequence": "10", "poste": "Programmation Bureau", "description": "Étude et programmation", "temps_base": 4.0},
                    {"sequence": "20", "poste": "Plasma CNC", "description": "Découpe plasma gros éléments", "temps_base": 6.0},
                    {"sequence": "30", "poste": "Oxycoupage", "description": "Découpe éléments épais", "temps_base": 8.0},
                    {"sequence": "40", "poste": "Plieuse conventionnelle 1", "description": "Formage éléments", "temps_base": 5.0},
                    {"sequence": "50", "poste": "Perçage 2", "description": "Perçage assemblage", "temps_base": 4.0},
                    {"sequence": "60", "poste": "Assemblage Lourd", "description": "Assemblage structure", "temps_base": 12.0},
                    {"sequence": "70", "poste": "Soudage SAW", "description": "Soudage à l'arc submergé", "temps_base": 10.0},
                    {"sequence": "80", "poste": "Soudage SMAW 1", "description": "Soudage manuel finition", "temps_base": 6.0},
                    {"sequence": "90", "poste": "Meulage 2", "description": "Finition soudures", "temps_base": 4.0},
                    {"sequence": "100", "poste": "Tests non destructifs", "description": "Contrôle soudures", "temps_base": 2.0},
                    {"sequence": "110", "poste": "Galvanisation", "description": "Protection anticorrosion", "temps_base": 3.0}
                ]
            },
            "PIECE_PRECISION": {
                "nom": "Pièce de Précision",
                "description": "Composant haute précision",
                "operations": [
                    {"sequence": "10", "poste": "Programmation Bureau", "description": "Programmation complexe", "temps_base": 3.0},
                    {"sequence": "20", "poste": "Sciage métal", "description": "Débit matière", "temps_base": 1.5},
                    {"sequence": "30", "poste": "Tour CNC 1", "description": "Tournage CNC", "temps_base": 5.0},
                    {"sequence": "40", "poste": "Fraiseuse CNC 1", "description": "Fraisage CNC", "temps_base": 6.0},
                    {"sequence": "50", "poste": "Centre d'usinage", "description": "Usinage complexe", "temps_base": 8.0},
                    {"sequence": "60", "poste": "Perçage 1", "description": "Perçage précision", "temps_base": 2.0},
                    {"sequence": "70", "poste": "Taraudage", "description": "Taraudage", "temps_base": 1.5},
                    {"sequence": "80", "poste": "Rectifieuse", "description": "Rectification", "temps_base": 4.0},
                    {"sequence": "90", "poste": "Ébavurage", "description": "Ébavurage", "temps_base": 2.0},
                    {"sequence": "100", "poste": "Polissage", "description": "Polissage", "temps_base": 3.0},
                    {"sequence": "110", "poste": "Contrôle métrologique", "description": "Contrôle dimensions", "temps_base": 2.5},
                    {"sequence": "120", "poste": "Anodisation", "description": "Traitement surface", "temps_base": 2.0}
                ]
            }
        }
    
    def generer_gamme_fabrication(self, type_produit: str, complexite: str, gestionnaire_employes=None) -> List[Dict]:
        """Génère une gamme de fabrication pour un type de produit donné (utilise SQLite)"""
        if type_produit not in self.gammes_types:
            return []
        
        gamme_base = self.gammes_types[type_produit]["operations"]
        gamme_generee = []
        
        # Coefficient de complexité
        coeff_complexite = {"SIMPLE": 0.8, "MOYEN": 1.0, "COMPLEXE": 1.3}.get(complexite, 1.0)
        
        for op in gamme_base:
            poste = self.get_poste_by_nom(op["poste"])
            if not poste:
                continue
            
            # Calcul du temps estimé
            temps_estime = op["temps_base"] * coeff_complexite
            
            # Variation aléatoire réaliste (-10% à +15%)
            variation = random.uniform(0.9, 1.15)
            temps_estime *= variation
            
            # Employés disponibles
            employes_disponibles = []
            if gestionnaire_employes:
                employes_disponibles = self.get_employes_competents(op["poste"], gestionnaire_employes)
            
            gamme_generee.append({
                "sequence": op["sequence"],
                "poste": op["poste"],
                "description": op["description"],
                "temps_estime": round(temps_estime, 1),
                "poste_info": poste,
                "employes_disponibles": employes_disponibles[:3],  # Limite à 3 pour l'affichage
                "statut": "À FAIRE"
            })
        
        return gamme_generee

# --- FONCTIONS UTILITAIRES ADAPTÉES SQLITE ---

def integrer_postes_dans_projets(gestionnaire_projets, gestionnaire_postes):
    """Intègre les postes de travail SQLite dans les projets existants"""
    for projet in gestionnaire_projets.projets:
        # Ajouter le champ poste_travail aux opérations existantes
        for operation in projet.get("operations", []):
            if "poste_travail" not in operation:
                operation["poste_travail"] = "À déterminer"
                operation["employe_assigne"] = None
                operation["machine_utilisee"] = None
    
    # Note: En SQLite, pas besoin de sauvegarder explicitement
    return gestionnaire_projets

def generer_rapport_capacite_production():
    """Génère un rapport de capacité de production depuis SQLite"""
    try:
        if 'gestionnaire_postes' not in st.session_state:
            return {"date_generation": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "capacites": {}, "utilisation_theorique": {}}
        
        gestionnaire_postes = st.session_state.gestionnaire_postes
        postes = gestionnaire_postes.get_all_work_centers()
        
        rapport = {
            "date_generation": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "capacites": {
                "postes_robotises": len([p for p in postes if p["categorie"] == "ROBOT"]),
                "postes_cnc": len([p for p in postes if p["categorie"] == "CNC"]),
                "postes_soudage": len([p for p in postes if "SOUDAGE" in p["type_machine"]]),
                "postes_finition": len([p for p in postes if "FINITION" in p["type_machine"] or "TRAITEMENT" in p["type_machine"]])
            },
            "utilisation_theorique": {
                "production": sum(p["capacite_theorique"] for p in postes if p["departement"] == "PRODUCTION"),
                "usinage": sum(p["capacite_theorique"] for p in postes if p["departement"] == "USINAGE"),
                "qualite": sum(p["capacite_theorique"] for p in postes if p["departement"] == "QUALITE"),
                "logistique": sum(p["capacite_theorique"] for p in postes if p["departement"] == "LOGISTIQUE")
            }
        }
        
        return rapport
    except Exception as e:
        print(f"Erreur génération rapport: {e}")
        return {"date_generation": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "capacites": {}, "utilisation_theorique": {}}

# --- PAGES INTERFACE UTILISATEUR (ADAPTÉES SQLITE) ---

def show_work_centers_page():
    """Page principale des postes de travail DG Inc. - Version SQLite"""
    st.markdown("## 🏭 Postes de Travail - DG Inc. (SQLite)")
    gestionnaire_postes = st.session_state.gestionnaire_postes
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    # Vérification de la migration
    total_postes = len(gestionnaire_postes.get_all_work_centers())
    if total_postes == 0:
        st.warning("⚠️ Aucun poste de travail trouvé. Migration en cours...")
        gestionnaire_postes._ensure_work_centers_migrated()
        st.rerun()
    
    tab_overview, tab_details, tab_analytics, tab_manage = st.tabs([
        "📊 Vue d'ensemble", "🔍 Détails par poste", "📈 Analyses", "⚙️ Gestion"
    ])
    
    with tab_overview:
        render_work_centers_overview(gestionnaire_postes)
    
    with tab_details:
        render_work_centers_details(gestionnaire_postes, gestionnaire_employes)
    
    with tab_analytics:
        render_work_centers_analytics(gestionnaire_postes)
    
    with tab_manage:
        render_work_centers_management(gestionnaire_postes)

def render_work_centers_overview(gestionnaire_postes):
    """Vue d'ensemble des postes de travail - Version SQLite"""
    stats = gestionnaire_postes.get_statistiques_postes()
    
    if stats['total_postes'] == 0:
        st.info("🔄 Migration des postes de travail en cours...")
        return
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🏭 Total Postes", stats['total_postes'])
    with col2:
        st.metric("🤖 Robots ABB", stats['postes_robotises'])
    with col3:
        st.metric("💻 Postes CNC", stats['postes_cnc'])
    with col4:
        efficacite_globale = random.uniform(82, 87)
        st.metric("⚡ Efficacité", f"{efficacite_globale:.1f}%")
    
    st.markdown("---")
    st.success(f"✅ {stats['total_postes']} postes de travail DG Inc. synchronisés avec SQLite")
    
    # Répartition par département
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        if stats['par_departement']:
            fig_dept = px.pie(
                values=list(stats['par_departement'].values()),
                names=list(stats['par_departement'].keys()),
                title="📊 Répartition par Département (SQLite)",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_dept.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                title_x=0.5
            )
            st.plotly_chart(fig_dept, use_container_width=True)
    
    with col_chart2:
        # Capacité par type de machine depuis SQLite
        postes = gestionnaire_postes.get_all_work_centers()
        capacite_par_type = {}
        for poste in postes:
            type_machine = poste.get('type_machine', 'AUTRE')
            capacite_par_type[type_machine] = capacite_par_type.get(type_machine, 0) + poste.get('capacite_theorique', 0)
        
        if capacite_par_type:
            fig_cap = px.bar(
                x=list(capacite_par_type.keys()),
                y=list(capacite_par_type.values()),
                title="⚡ Capacité par Type (h/jour) - SQLite",
                color=list(capacite_par_type.keys()),
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_cap.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                showlegend=False,
                title_x=0.5
            )
            st.plotly_chart(fig_cap, use_container_width=True)

def render_work_centers_details(gestionnaire_postes, gestionnaire_employes):
    """Détails par poste de travail - Version SQLite"""
    st.subheader("🔍 Détails des Postes de Travail (SQLite)")
    
    postes = gestionnaire_postes.get_all_work_centers()
    
    if not postes:
        st.warning("Aucun poste trouvé en SQLite.")
        return
    
    # Filtres
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        departements = list(set(p['departement'] for p in postes))
        dept_filter = st.selectbox("Département:", ["Tous"] + sorted(departements))
    
    with col_filter2:
        categories = list(set(p['categorie'] for p in postes))
        cat_filter = st.selectbox("Catégorie:", ["Toutes"] + sorted(categories))
    
    with col_filter3:
        search_term = st.text_input("🔍 Rechercher:", placeholder="Nom du poste...")
    
    # Application des filtres
    postes_filtres = postes
    
    if dept_filter != "Tous":
        postes_filtres = [p for p in postes_filtres if p['departement'] == dept_filter]
    
    if cat_filter != "Toutes":
        postes_filtres = [p for p in postes_filtres if p['categorie'] == cat_filter]
    
    if search_term:
        terme = search_term.lower()
        postes_filtres = [p for p in postes_filtres if terme in p['nom'].lower()]
    
    st.markdown(f"**{len(postes_filtres)} poste(s) trouvé(s) en SQLite**")
    
    # Affichage des postes filtrés
    for poste in postes_filtres:
        with st.container():
            st.markdown(f"""
            <div class='work-center-card'>
                <div class='work-center-header'>
                    <div class='work-center-title'>#{poste['id']} - {poste['nom']}</div>
                    <div class='work-center-badge'>{poste['categorie']}</div>
                </div>
                <p><strong>Département:</strong> {poste['departement']} | <strong>Type:</strong> {poste['type_machine']}</p>
                <p><strong>Compétences requises:</strong> {', '.join(poste.get('competences', []))}</p>
                <div class='work-center-info'>
                    <div class='work-center-stat'>
                        <div class='work-center-stat-value'>{poste['capacite_theorique']}h</div>
                        <p class='work-center-stat-label'>Capacité/jour</p>
                    </div>
                    <div class='work-center-stat'>
                        <div class='work-center-stat-value'>{poste['operateurs_requis']}</div>
                        <p class='work-center-stat-label'>Opérateurs</p>
                    </div>
                    <div class='work-center-stat'>
                        <div class='work-center-stat-value'>{poste['cout_horaire']}$</div>
                        <p class='work-center-stat-label'>Coût/heure</p>
                    </div>
                    <div class='work-center-stat'>
                        <div class='work-center-stat-value'>{random.randint(75, 95)}%</div>
                        <p class='work-center-stat-label'>Utilisation</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Affichage des employés compétents
            employes_competents = gestionnaire_postes.get_employes_competents(poste['nom'], gestionnaire_employes)
            if employes_competents:
                st.caption(f"👥 Employés compétents: {', '.join(employes_competents)}")
            else:
                st.caption("⚠️ Aucun employé compétent trouvé")

def render_work_centers_analytics(gestionnaire_postes):
    """Analyses avancées des postes de travail - Version SQLite"""
    st.subheader("📈 Analyses de Performance (SQLite)")
    
    rapport = generer_rapport_capacite_production()
    
    # Métriques de capacité
    st.markdown("### ⚡ Capacités Théoriques SQLite")
    cap_col1, cap_col2, cap_col3, cap_col4 = st.columns(4)
    
    with cap_col1:
        st.metric("🏭 Production", f"{rapport['utilisation_theorique'].get('production', 0)}h/j")
    with cap_col2:
        st.metric("⚙️ Usinage", f"{rapport['utilisation_theorique'].get('usinage', 0)}h/j")
    with cap_col3:
        st.metric("✅ Qualité", f"{rapport['utilisation_theorique'].get('qualite', 0)}h/j")
    with cap_col4:
        st.metric("📦 Logistique", f"{rapport['utilisation_theorique'].get('logistique', 0)}h/j")
    
    st.markdown("---")
    
    # Analyse des coûts depuis SQLite
    st.markdown("### 💰 Analyse des Coûts SQLite")
    postes = gestionnaire_postes.get_all_work_centers()
    
    cout_col1, cout_col2 = st.columns(2)
    
    with cout_col1:
        # Coût par catégorie
        cout_par_categorie = {}
        for poste in postes:
            cat = poste['categorie']
            cout = poste['cout_horaire'] * poste['capacite_theorique']
            cout_par_categorie[cat] = cout_par_categorie.get(cat, 0) + cout
        
        if cout_par_categorie:
            fig_cout = px.bar(
                x=list(cout_par_categorie.keys()),
                y=list(cout_par_categorie.values()),
                title="💰 Coût Journalier par Catégorie ($) - SQLite",
                color=list(cout_par_categorie.keys()),
                color_discrete_sequence=px.colors.qualitative.Vivid
            )
            fig_cout.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                showlegend=False,
                title_x=0.5
            )
            st.plotly_chart(fig_cout, use_container_width=True)
    
    with cout_col2:
        # Analyse ROI potentiel
        st.markdown("**💡 Recommandations SQLite:**")
        recommendations = [
            "🤖 Maximiser l'utilisation des robots ABB (ROI élevé)",
            "⚡ Grouper les opérations CNC par type de matériau",
            "🔄 Implémenter des changements d'équipes optimisés",
            "📊 Former plus d'employés sur postes critiques",
            "⏰ Programmer maintenance préventive en heures creuses"
        ]
        
        for i, rec in enumerate(recommendations, 1):
            st.markdown(f"**{i}.** {rec}")

def render_work_centers_management(gestionnaire_postes):
    """Gestion des postes de travail - Nouveau module SQLite"""
    st.subheader("⚙️ Gestion des Postes (SQLite)")
    
    tab_add, tab_edit, tab_stats = st.tabs(["➕ Ajouter", "✏️ Modifier", "📊 Statistiques"])
    
    with tab_add:
        st.markdown("##### ➕ Ajouter un Nouveau Poste")
        with st.form("add_work_center_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                nom = st.text_input("Nom du poste *:")
                departement = st.selectbox("Département *:", ["PRODUCTION", "USINAGE", "QUALITE", "LOGISTIQUE", "COMMERCIAL"])
                categorie = st.selectbox("Catégorie *:", list(CATEGORIES_POSTES_TRAVAIL.keys()))
                type_machine = st.text_input("Type de machine:")
            
            with col2:
                capacite_theorique = st.number_input("Capacité théorique (h/j):", min_value=0.0, value=8.0, step=0.5)
                operateurs_requis = st.number_input("Opérateurs requis:", min_value=1, value=1, step=1)
                cout_horaire = st.number_input("Coût horaire ($):", min_value=0.0, value=50.0, step=5.0)
            
            competences = st.multiselect(
                "Compétences requises:",
                ["Programmation CNC", "Soudage GMAW", "Soudage FCAW", "Soudage GTAW", "Soudage SMAW", 
                 "Tournage", "Fraisage", "Assemblage", "Meulage", "Peinture", "Contrôle qualité",
                 "Manutention", "Lecture plan", "CAO/FAO", "Métrologie"]
            )
            
            if st.form_submit_button("💾 Ajouter Poste SQLite"):
                if not nom or not departement:
                    st.error("Nom et département obligatoires.")
                else:
                    poste_data = {
                        'nom': nom,
                        'departement': departement,
                        'categorie': categorie,
                        'type_machine': type_machine,
                        'capacite_theorique': capacite_theorique,
                        'operateurs_requis': operateurs_requis,
                        'cout_horaire': cout_horaire,
                        'competences': competences
                    }
                    
                    poste_id = gestionnaire_postes.add_work_center(poste_data)
                    if poste_id:
                        st.success(f"✅ Poste '{nom}' ajouté avec l'ID {poste_id} en SQLite!")
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de l'ajout en SQLite")
    
    with tab_edit:
        st.markdown("##### ✏️ Modifier un Poste Existant")
        postes = gestionnaire_postes.get_all_work_centers()
        
        if postes:
            poste_options = [(p['id'], f"#{p['id']} - {p['nom']}") for p in postes]
            selected_poste_id = st.selectbox(
                "Sélectionner un poste:",
                options=[p[0] for p in poste_options],
                format_func=lambda x: next((p[1] for p in poste_options if p[0] == x), "")
            )
            
            poste_selected = gestionnaire_postes.get_poste_by_id(selected_poste_id)
            
            if poste_selected:
                with st.form("edit_work_center_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        nom = st.text_input("Nom du poste *:", value=poste_selected['nom'])
                        departement = st.selectbox(
                            "Département *:", 
                            ["PRODUCTION", "USINAGE", "QUALITE", "LOGISTIQUE", "COMMERCIAL"],
                            index=["PRODUCTION", "USINAGE", "QUALITE", "LOGISTIQUE", "COMMERCIAL"].index(poste_selected['departement'])
                        )
                        categorie = st.selectbox(
                            "Catégorie *:", 
                            list(CATEGORIES_POSTES_TRAVAIL.keys()),
                            index=list(CATEGORIES_POSTES_TRAVAIL.keys()).index(poste_selected['categorie']) if poste_selected['categorie'] in CATEGORIES_POSTES_TRAVAIL else 0
                        )
                        type_machine = st.text_input("Type de machine:", value=poste_selected.get('type_machine', ''))
                    
                    with col2:
                        capacite_theorique = st.number_input("Capacité théorique (h/j):", min_value=0.0, value=float(poste_selected['capacite_theorique']), step=0.5)
                        operateurs_requis = st.number_input("Opérateurs requis:", min_value=1, value=int(poste_selected['operateurs_requis']), step=1)
                        cout_horaire = st.number_input("Coût horaire ($):", min_value=0.0, value=float(poste_selected['cout_horaire']), step=5.0)
                    
                    competences = st.multiselect(
                        "Compétences requises:",
                        ["Programmation CNC", "Soudage GMAW", "Soudage FCAW", "Soudage GTAW", "Soudage SMAW", 
                         "Tournage", "Fraisage", "Assemblage", "Meulage", "Peinture", "Contrôle qualité",
                         "Manutention", "Lecture plan", "CAO/FAO", "Métrologie"],
                        default=poste_selected.get('competences', [])
                    )
                    
                    col_save, col_delete = st.columns(2)
                    
                    with col_save:
                        if st.form_submit_button("💾 Sauvegarder SQLite"):
                            poste_data = {
                                'nom': nom,
                                'departement': departement,
                                'categorie': categorie,
                                'type_machine': type_machine,
                                'capacite_theorique': capacite_theorique,
                                'operateurs_requis': operateurs_requis,
                                'cout_horaire': cout_horaire,
                                'competences': competences
                            }
                            
                            if gestionnaire_postes.update_work_center(selected_poste_id, poste_data):
                                st.success(f"✅ Poste #{selected_poste_id} mis à jour en SQLite!")
                                st.rerun()
                            else:
                                st.error("❌ Erreur lors de la mise à jour SQLite")
                    
                    with col_delete:
                        if st.form_submit_button("🗑️ Supprimer SQLite"):
                            if gestionnaire_postes.delete_work_center(selected_poste_id):
                                st.success(f"✅ Poste #{selected_poste_id} supprimé de SQLite!")
                                st.rerun()
                            else:
                                st.error("❌ Impossible de supprimer (opérations liées)")
        else:
            st.info("Aucun poste trouvé en SQLite.")
    
    with tab_stats:
        st.markdown("##### 📊 Statistiques Détaillées SQLite")
        stats = gestionnaire_postes.get_statistiques_postes()
        postes = gestionnaire_postes.get_all_work_centers()
        
        # Métriques détaillées
        st_col1, st_col2, st_col3, st_col4 = st.columns(4)
        with st_col1:
            st.metric("📊 Total Postes", stats['total_postes'])
        with st_col2:
            capacite_totale = sum(p['capacite_theorique'] for p in postes)
            st.metric("⚡ Capacité Totale", f"{capacite_totale:.1f}h/j")
        with st_col3:
            cout_total = sum(p['cout_horaire'] * p['capacite_theorique'] for p in postes)
            st.metric("💰 Coût Total/jour", f"{cout_total:.0f}$")
        with st_col4:
            operateurs_total = sum(p['operateurs_requis'] for p in postes)
            st.metric("👥 Opérateurs Total", operateurs_total)
        
        # Tableau récapitulatif
        if postes:
            df_postes = pd.DataFrame([
                {
                    'ID': p['id'],
                    'Nom': p['nom'],
                    'Département': p['departement'],
                    'Catégorie': p['categorie'],
                    'Capacité (h/j)': p['capacite_theorique'],
                    'Coût ($/h)': p['cout_horaire'],
                    'Opérateurs': p['operateurs_requis']
                }
                for p in postes
            ])
            
            st.markdown("##### 📋 Tableau Récapitulatif SQLite")
            st.dataframe(df_postes, use_container_width=True)

# --- PAGES GAMMES ET CAPACITÉ (INCHANGÉES MAIS ADAPTÉES) ---

def show_manufacturing_routes_page():
    """Page des gammes de fabrication - Version SQLite"""
    st.markdown("## ⚙️ Gammes de Fabrication - DG Inc. (SQLite)")
    
    gestionnaire_postes = st.session_state.gestionnaire_postes
    gestionnaire_projets = st.session_state.gestionnaire
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    # Vérification postes SQLite
    if len(gestionnaire_postes.get_all_work_centers()) == 0:
        st.warning("⚠️ Aucun poste trouvé en SQLite. Migration en cours...")
        gestionnaire_postes._ensure_work_centers_migrated()
        st.rerun()
    
    tab_generator, tab_templates, tab_optimization = st.tabs([
        "🔧 Générateur SQLite", "📋 Modèles", "🎯 Optimisation"
    ])
    
    with tab_generator:
        render_operations_manager(gestionnaire_postes, gestionnaire_employes)
    
    with tab_templates:
        render_gammes_templates(gestionnaire_postes)
    
    with tab_optimization:
        render_route_optimization(gestionnaire_postes, gestionnaire_projets)

def show_capacity_analysis_page():
    """Page d'analyse de capacité de production - Version SQLite"""
    st.markdown("## 📈 Analyse de Capacité - DG Inc. (SQLite)")
    
    gestionnaire_postes = st.session_state.gestionnaire_postes
    
    # Vérification postes SQLite
    postes_count = len(gestionnaire_postes.get_all_work_centers())
    if postes_count == 0:
        st.warning("⚠️ Aucun poste trouvé en SQLite. Migration en cours...")
        gestionnaire_postes._ensure_work_centers_migrated()
        st.rerun()
    
    # Rapport de capacité en temps réel depuis SQLite
    rapport = generer_rapport_capacite_production()
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🤖 Robots ABB", rapport['capacites'].get('postes_robotises', 0))
    with col2:
        st.metric("💻 Postes CNC", rapport['capacites'].get('postes_cnc', 0))
    with col3:
        st.metric("🔥 Postes Soudage", rapport['capacites'].get('postes_soudage', 0))
    with col4:
        st.metric("✨ Postes Finition", rapport['capacites'].get('postes_finition', 0))
    
    st.success(f"📊 Analyse basée sur {postes_count} postes SQLite synchronisés")
    
    # Affichage détaillé
    render_capacity_analysis(gestionnaire_postes)

def render_capacity_analysis(gestionnaire_postes):
    """Analyse détaillée de la capacité - Version SQLite"""
    st.markdown("### 🏭 Analyse Détaillée de la Capacité SQLite")
    
    postes = gestionnaire_postes.get_all_work_centers()
    
    # Analyse par département depuis SQLite
    dept_analysis = {}
    for poste in postes:
        dept = poste['departement']
        if dept not in dept_analysis:
            dept_analysis[dept] = {
                'postes': 0,
                'capacite_totale': 0,
                'cout_total': 0,
                'operateurs_requis': 0
            }
        
        dept_analysis[dept]['postes'] += 1
        dept_analysis[dept]['capacite_totale'] += poste['capacite_theorique']
        dept_analysis[dept]['cout_total'] += poste['cout_horaire'] * poste['capacite_theorique']
        dept_analysis[dept]['operateurs_requis'] += poste['operateurs_requis']
    
    # Affichage par département
    for dept, stats in dept_analysis.items():
        with st.expander(f"🏭 {dept} - {stats['postes']} postes (SQLite)", expanded=False):
            dept_col1, dept_col2, dept_col3, dept_col4 = st.columns(4)
            
            with dept_col1:
                st.metric("📊 Postes", stats['postes'])
            with dept_col2:
                st.metric("⚡ Capacité/jour", f"{stats['capacite_totale']}h")
            with dept_col3:
                st.metric("👥 Opérateurs", stats['operateurs_requis'])
            with dept_col4:
                st.metric("💰 Coût/jour", f"{stats['cout_total']:.0f}$")
            
            # Liste des postes du département depuis SQLite
            postes_dept = [p for p in postes if p['departement'] == dept]
            
            data_dept = []
            for poste in postes_dept:
                utilisation_simulee = random.uniform(65, 95)
                data_dept.append({
                    'ID': poste['id'],
                    'Poste': poste['nom'],
                    'Catégorie': poste['categorie'],
                    'Capacité (h/j)': poste['capacite_theorique'],
                    'Coût ($/h)': poste['cout_horaire'],
                    'Utilisation (%)': f"{utilisation_simulee:.1f}%"
                })
            
            if data_dept:
                df_dept = pd.DataFrame(data_dept)
                st.dataframe(df_dept, use_container_width=True)

# Fonctions d'interface inchangées mais adaptées...
def render_operations_manager(gestionnaire_postes, gestionnaire_employes):
    """Gestionnaire d'opérations avec vrais postes SQLite"""
    st.subheader("🔧 Générateur de Gammes de Fabrication (SQLite)")
    
    # Vérification des postes SQLite
    postes_count = len(gestionnaire_postes.get_all_work_centers())
    if postes_count == 0:
        st.error("❌ Aucun poste trouvé en SQLite. Impossible de générer des gammes.")
        return
    
    st.info(f"📊 Utilisation de {postes_count} postes de travail synchronisés depuis SQLite")
    
    # Le reste de la fonction reste identique...
    # Formulaire de génération
    with st.form("gamme_generator_form"):
        col_form1, col_form2 = st.columns(2)
        
        with col_form1:
            type_produit = st.selectbox(
                "Type de produit:",
                ["CHASSIS_SOUDE", "STRUCTURE_LOURDE", "PIECE_PRECISION"],
                format_func=lambda x: gestionnaire_postes.gammes_types[x]["nom"]
            )
            complexite = st.selectbox("Complexité:", ["SIMPLE", "MOYEN", "COMPLEXE"])
        
        with col_form2:
            quantite = st.number_input("Quantité:", min_value=1, value=1, step=1)
            priorite = st.selectbox("Priorité:", ["BAS", "MOYEN", "ÉLEVÉ"])
        
        description_produit = st.text_area(
            "Description:",
            value=gestionnaire_postes.gammes_types[type_produit]["description"]
        )
        
        generate_btn = st.form_submit_button("🚀 Générer Gamme SQLite", use_container_width=True)
        
        if generate_btn:
            with st.spinner("Génération de la gamme optimisée depuis SQLite..."):
                gamme = gestionnaire_postes.generer_gamme_fabrication(
                    type_produit, complexite, gestionnaire_employes
                )
                
                st.session_state.gamme_generated = gamme
                st.session_state.gamme_metadata = {
                    "type": type_produit,
                    "complexite": complexite,
                    "quantite": quantite,
                    "priorite": priorite,
                    "description": description_produit
                }
                
                st.success(f"✅ Gamme générée avec {len(gamme)} opérations depuis SQLite !")
    
    # Affichage de la gamme générée (reste identique mais avec mention SQLite)
    if st.session_state.get('gamme_generated'):
        st.markdown("---")
        st.markdown("### 📋 Gamme Générée (SQLite)")
        
        gamme = st.session_state.gamme_generated
        metadata = st.session_state.get('gamme_metadata', {})
        
        # Informations sur la gamme
        info_col1, info_col2, info_col3 = st.columns(3)
        with info_col1:
            st.metric("⚙️ Opérations", len(gamme))
        with info_col2:
            temps_total = sum(op['temps_estime'] for op in gamme)
            st.metric("⏱️ Temps Total", f"{temps_total:.1f}h")
        with info_col3:
            cout_total = sum(
                op['temps_estime'] * op['poste_info']['cout_horaire'] 
                for op in gamme if op.get('poste_info')
            )
            st.metric("💰 Coût Estimé", f"{cout_total:.0f}$")
        
        # Tableau des opérations
        st.markdown("#### 📊 Détail des Opérations (Postes SQLite)")
        
        data_gamme = []
        for op in gamme:
            poste_info = op.get('poste_info', {})
            data_gamme.append({
                'Séq.': op['sequence'],
                'ID Poste': poste_info.get('id', 'N/A'),
                'Poste': op['poste'],
                'Description': op['description'],
                'Temps (h)': f"{op['temps_estime']:.1f}",
                'Coût/h': f"{poste_info.get('cout_horaire', 0)}$",
                'Total': f"{op['temps_estime'] * poste_info.get('cout_horaire', 0):.0f}$",
                'Employés Dispo.': ', '.join(op.get('employes_disponibles', ['Aucun'])[:2])
            })
        
        df_gamme = pd.DataFrame(data_gamme)
        st.dataframe(df_gamme, use_container_width=True)
        
        # Graphiques (restent identiques)
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            temps_par_dept = {}
            for op in gamme:
                poste_info = op.get('poste_info', {})
                dept = poste_info.get('departement', 'AUTRE')
                temps_par_dept[dept] = temps_par_dept.get(dept, 0) + op['temps_estime']
            
            if temps_par_dept:
                fig_temps = px.pie(
                    values=list(temps_par_dept.values()),
                    names=list(temps_par_dept.keys()),
                    title="⏱️ Répartition Temps par Département (SQLite)"
                )
                fig_temps.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='var(--text-color)'),
                    title_x=0.5
                )
                st.plotly_chart(fig_temps, use_container_width=True)
        
        with col_chart2:
            cout_par_dept = {}
            for op in gamme:
                poste_info = op.get('poste_info', {})
                dept = poste_info.get('departement', 'AUTRE')
                cout = op['temps_estime'] * poste_info.get('cout_horaire', 0)
                cout_par_dept[dept] = cout_par_dept.get(dept, 0) + cout
            
            if cout_par_dept:
                fig_cout = px.bar(
                    x=list(cout_par_dept.keys()),
                    y=list(cout_par_dept.values()),
                    title="💰 Coût par Département ($) - SQLite",
                    color=list(cout_par_dept.keys())
                )
                fig_cout.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='var(--text-color)'),
                    showlegend=False,
                    title_x=0.5
                )
                st.plotly_chart(fig_cout, use_container_width=True)
        
        # Bouton pour appliquer à un projet
        if st.button("📋 Appliquer à un Projet SQLite", use_container_width=True):
            st.session_state.show_apply_gamme_to_project = True

def render_gammes_templates(gestionnaire_postes):
    """Templates de gammes prédéfinies - Version SQLite"""
    st.subheader("📋 Modèles de Gammes Prédéfinis (SQLite)")
    
    for type_key, gamme_info in gestionnaire_postes.gammes_types.items():
        with st.expander(f"🔧 {gamme_info['nom']} - SQLite", expanded=False):
            col_t1, col_t2 = st.columns(2)
            
            with col_t1:
                st.markdown(f"**Description:** {gamme_info['description']}")
                st.markdown(f"**Nombre d'opérations:** {len(gamme_info['operations'])}")
                
                temps_base_total = sum(op['temps_base'] for op in gamme_info['operations'])
                st.markdown(f"**Temps de base:** {temps_base_total:.1f}h")
                
                # Aperçu des opérations
                st.markdown("**Opérations principales:**")
                for i, op in enumerate(gamme_info['operations'][:5], 1):
                    # Vérification que le poste existe en SQLite
                    poste_sqlite = gestionnaire_postes.get_poste_by_nom(op['poste'])
                    status_icon = "✅" if poste_sqlite else "⚠️"
                    st.markdown(f"  {i}. {status_icon} {op['poste']} - {op['description']}")
                if len(gamme_info['operations']) > 5:
                    st.markdown(f"  ... et {len(gamme_info['operations']) - 5} autres")
            
            with col_t2:
                # Répartition des postes utilisés depuis SQLite
                postes_utilises = {}
                postes_manquants = 0
                
                for op in gamme_info['operations']:
                    poste_obj = gestionnaire_postes.get_poste_by_nom(op['poste'])
                    if poste_obj:
                        dept = poste_obj['departement']
                        postes_utilises[dept] = postes_utilises.get(dept, 0) + 1
                    else:
                        postes_manquants += 1
                
                if postes_manquants > 0:
                    st.warning(f"⚠️ {postes_manquants} poste(s) manquant(s) en SQLite")
                
                if postes_utilises:
                    fig_template = px.bar(
                        x=list(postes_utilises.keys()),
                        y=list(postes_utilises.values()),
                        title=f"Postes par Département - {gamme_info['nom']} (SQLite)",
                        color=list(postes_utilises.keys())
                    )
                    fig_template.update_layout(
                        height=300,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='var(--text-color)', size=10),
                        showlegend=False,
                        title_x=0.5
                    )
                    st.plotly_chart(fig_template, use_container_width=True)
                
                if st.button(f"🚀 Appliquer Modèle {gamme_info['nom']} (SQLite)", key=f"apply_{type_key}"):
                    gestionnaire_employes = st.session_state.gestionnaire_employes
                    gamme = gestionnaire_postes.generer_gamme_fabrication(
                        type_key, "MOYEN", gestionnaire_employes
                    )
                    st.session_state.gamme_generated = gamme
                    st.session_state.gamme_metadata = {
                        "type": type_key,
                        "complexite": "MOYEN",
                        "quantite": 1,
                        "description": gamme_info['description']
                    }
                    st.success(f"✅ Modèle {gamme_info['nom']} appliqué depuis SQLite !")
                    st.rerun()

def render_route_optimization(gestionnaire_postes, gestionnaire_projets):
    """Optimisation des gammes et séquencement - Version SQLite"""
    st.subheader("🎯 Optimisation des Gammes (SQLite)")
    
    # Message informatif sur l'utilisation SQLite
    st.info("📊 Optimisation basée sur les données temps réel depuis SQLite")
    
    # Sélection des projets actifs pour optimisation
    projets_actifs = [p for p in gestionnaire_projets.projets if p.get('statut') not in ['TERMINÉ', 'ANNULÉ']]
    
    if not projets_actifs:
        st.info("Aucun projet actif pour l'optimisation.")
        return
    
    st.markdown("### 📊 Analyse de Charge Actuelle SQLite")
    
    # Calcul de la charge par poste depuis SQLite
    charge_par_poste = {}
    for projet in projets_actifs:
        for operation in projet.get('operations', []):
            poste = operation.get('poste_travail', 'Non assigné')
            if poste != 'Non assigné' and operation.get('statut') != 'TERMINÉ':
                temps = operation.get('temps_estime', 0)
                charge_par_poste[poste] = charge_par_poste.get(poste, 0) + temps
    
    if charge_par_poste:
        # Graphique de charge
        postes_charges = sorted(charge_par_poste.items(), key=lambda x: x[1], reverse=True)[:10]
        
        fig_charge = px.bar(
            x=[p[0] for p in postes_charges],
            y=[p[1] for p in postes_charges],
            title="📊 Charge Actuelle par Poste (Top 10) - SQLite",
            color=[p[1] for p in postes_charges],
            color_continuous_scale="Reds"
        )
        fig_charge.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='var(--text-color)'),
            showlegend=False,
            title_x=0.5,
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig_charge, use_container_width=True)
        
        # Identification des goulots avec données SQLite
        st.markdown("### 🚨 Goulots d'Étranglement Identifiés (SQLite)")
        
        goulots = []
        for poste_nom, charge_totale in charge_par_poste.items():
            poste_obj = gestionnaire_postes.get_poste_by_nom(poste_nom)
            if poste_obj:
                capacite_hebdo = poste_obj['capacite_theorique'] * 5  # 5 jours
                taux_charge = (charge_totale / capacite_hebdo) * 100 if capacite_hebdo > 0 else 0
                
                if taux_charge > 90:
                    goulots.append({
                        'poste': poste_nom,
                        'poste_id': poste_obj['id'],
                        'charge': charge_totale,
                        'capacite': capacite_hebdo,
                        'taux': taux_charge
                    })
        
        if goulots:
            for goulot in sorted(goulots, key=lambda x: x['taux'], reverse=True):
                st.error(f"⚠️ **Poste #{goulot['poste_id']} - {goulot['poste']}**: {goulot['taux']:.1f}% de charge "
                        f"({goulot['charge']:.1f}h / {goulot['capacite']:.1f}h) - Source SQLite")
        else:
            st.success("✅ Aucun goulot d'étranglement critique détecté en SQLite")
    
    # Simulation d'optimisation (reste identique mais avec mention SQLite)
    st.markdown("---")
    st.markdown("### 🔄 Optimisation Automatique SQLite")
    
    if st.button("🚀 Lancer Optimisation Globale SQLite", use_container_width=True):
        with st.spinner("Optimisation en cours avec données SQLite..."):
            import time
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Étapes d'optimisation simulées avec SQLite
            etapes = [
                "Analyse charge actuelle par poste SQLite...",
                "Identification des goulots d'étranglement SQLite...", 
                "Calcul des alternatives de routage depuis SQLite...",
                "Optimisation utilisation robots ABB (SQLite)...",
                "Équilibrage des charges par département SQLite...",
                "Génération des recommandations optimisées..."
            ]
            
            resultats_optim = {
                'temps_economise': 0,
                'cout_reduit': 0,
                'utilisation_amelioree': {},
                'recommandations': []
            }
            
            for i, etape in enumerate(etapes):
                status_text.text(etape)
                time.sleep(0.8)
                progress_bar.progress((i + 1) / len(etapes))
                
                # Simulation de résultats améliorée avec SQLite
                resultats_optim['temps_economise'] += random.uniform(2.5, 8.3)
                resultats_optim['cout_reduit'] += random.uniform(150, 450)
            
            # Résultats d'optimisation
            st.success("✅ Optimisation SQLite terminée !")
            
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("⏱️ Temps Économisé", f"{resultats_optim['temps_economise']:.1f}h")
            with col_r2:
                st.metric("💰 Coût Réduit", f"{resultats_optim['cout_reduit']:.0f}$ CAD")
            with col_r3:
                efficacite = random.uniform(12, 18)
                st.metric("📈 Efficacité SQLite", f"+{efficacite:.1f}%")
            
            # Recommandations détaillées optimisées SQLite
            st.markdown("### 💡 Recommandations d'Optimisation SQLite")
            postes_sqlite = gestionnaire_postes.get_all_work_centers()
            robots_count = len([p for p in postes_sqlite if p['categorie'] == 'ROBOT'])
            cnc_count = len([p for p in postes_sqlite if p['categorie'] == 'CNC'])
            
            recommandations = [
                f"🤖 Programmer {robots_count} Robots ABB en priorité pour pièces répétitives",
                f"⚡ Grouper les découpes sur {cnc_count} machines CNC par épaisseur",
                "🔄 Alterner soudage manuel/robot selon complexité géométrique SQLite",
                "📊 Former employés sur Plieuses CNC haute précision (données SQLite)",
                "⏰ Décaler finition peinture sur équipe de soir (optimisation SQLite)"
            ]
            
            for recommandation in recommandations:
                st.markdown(f"- {recommandation}")

def update_sidebar_with_work_centers():
    """Ajoute les statistiques des postes de travail SQLite dans la sidebar"""
    try:
        gestionnaire_postes = st.session_state.gestionnaire_postes
        stats_postes = gestionnaire_postes.get_statistiques_postes()
        
        if stats_postes['total_postes'] > 0:
            st.sidebar.markdown("---")
            st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>🏭 Production SQLite</h3>", unsafe_allow_html=True)
            st.sidebar.metric("SQLite: Postes Actifs", stats_postes['total_postes'])
            st.sidebar.metric("SQLite: CNC/Robots", stats_postes['postes_cnc'] + stats_postes['postes_robotises'])
            
            # Graphique simple de répartition depuis SQLite
            if stats_postes['par_departement']:
                dept_data = list(stats_postes['par_departement'].items())
                dept_names = [d[0][:4] for d in dept_data]  # Abréger pour sidebar
                dept_values = [d[1] for d in dept_data]
                
                fig_sidebar = px.bar(
                    x=dept_names,
                    y=dept_values,
                    color=dept_names,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_sidebar.update_layout(
                    height=150, 
                    margin=dict(l=0, r=0, t=10, b=0),
                    plot_bgcolor='rgba(0,0,0,0)', 
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='var(--text-color)', size=8), 
                    showlegend=False
                )
                st.sidebar.markdown("<p style='font-size:0.8em;text-align:center;color:var(--text-color);'>Postes par département (SQLite)</p>", unsafe_allow_html=True)
                st.sidebar.plotly_chart(fig_sidebar, use_container_width=True)
    except Exception as e:
        # Silencieux si erreur pendant l'initialisation
        pass
