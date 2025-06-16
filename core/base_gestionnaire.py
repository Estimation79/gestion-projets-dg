# formulaires/core/base_gestionnaire.py
# Classe de base pour la gestion des formulaires

"""
Gestionnaire unifié pour tous les formulaires métier DG Inc.
Classe de base contenant la logique commune à tous les types de formulaires.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import json

from .types_formulaires import (
    TYPES_FORMULAIRES,
    STATUTS_FORMULAIRES,
    PRIORITES_FORMULAIRES,
    valider_type_formulaire,
    valider_statut,
    valider_priorite
)


class GestionnaireFormulaires:
    """
    Gestionnaire unifié pour tous les formulaires métier DG Inc.
    
    Gère les opérations communes à tous les types de formulaires :
    - Bons de Travail (BT)
    - Bons d'Achats (BA) 
    - Bons de Commande (BC)
    - Demandes de Prix (DP)
    - Estimations (EST)
    """
    
    def __init__(self, db):
        """
        Initialise le gestionnaire avec une connexion à la base de données.
        
        Args:
            db: Instance de connexion à la base de données
        """
        self.db = db
        self.types_formulaires = TYPES_FORMULAIRES
        self.statuts = STATUTS_FORMULAIRES
        self.priorites = PRIORITES_FORMULAIRES
    
    def generer_numero_document(self, type_formulaire: str) -> str:
        """
        Génère un numéro unique pour le document selon le type.
        
        Args:
            type_formulaire: Type du formulaire (clé de TYPES_FORMULAIRES)
            
        Returns:
            str: Numéro généré au format PREFIX-ANNEE-SEQUENCE
        """
        try:
            if not valider_type_formulaire(type_formulaire):
                return "ERREUR-001"
            
            config = self.types_formulaires.get(type_formulaire)
            prefix = config['prefix']
            annee = datetime.now().year
            
            # Récupérer le dernier numéro pour ce type et cette année
            query = '''
                SELECT numero_document FROM formulaires 
                WHERE type_formulaire = ? AND numero_document LIKE ?
                ORDER BY id DESC LIMIT 1
            '''
            pattern = f"{prefix}-{annee}-%"
            result = self.db.execute_query(query, (type_formulaire, pattern))
            
            if result:
                last_num = result[0]['numero_document']
                # Extraire la séquence du dernier numéro
                try:
                    sequence = int(last_num.split('-')[-1].split(' ')[0]) + 1  # Gérer les versions " v2"
                except (ValueError, IndexError):
                    sequence = 1
            else:
                sequence = 1
            
            return f"{prefix}-{annee}-{sequence:03d}"
            
        except Exception as e:
            st.error(f"Erreur génération numéro: {e}")
            return f"ERR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def creer_formulaire(self, data: Dict) -> Optional[int]:
        """
        Crée un nouveau formulaire dans la base de données.
        
        Args:
            data: Dictionnaire contenant les données du formulaire
            
        Returns:
            int: ID du formulaire créé, None en cas d'erreur
        """
        try:
            # Validation des données
            if not self._valider_donnees_formulaire(data):
                return None
            
            # Générer numéro si pas fourni
            if not data.get('numero_document'):
                data['numero_document'] = self.generer_numero_document(data['type_formulaire'])
            
            # Requête d'insertion
            query = '''
                INSERT INTO formulaires 
                (type_formulaire, numero_document, project_id, company_id, employee_id,
                 statut, date_creation, montant_total, notes, priorite, date_echeance, metadonnees_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            formulaire_id = self.db.execute_insert(query, (
                data['type_formulaire'],
                data['numero_document'],
                data.get('project_id'),
                data.get('company_id'),
                data.get('employee_id'),
                data.get('statut', 'BROUILLON'),
                data.get('date_creation', datetime.now()),
                data.get('montant_total', 0.0),
                data.get('notes', ''),
                data.get('priorite', 'NORMAL'),
                data.get('date_echeance'),
                data.get('metadonnees_json', '{}')
            ))
            
            # Ajouter les lignes de détail si fournies
            if data.get('lignes') and formulaire_id:
                self.ajouter_lignes_formulaire(formulaire_id, data['lignes'])
            
            # Enregistrer la création dans l'historique
            self.enregistrer_validation(formulaire_id, data.get('employee_id'), 'CREATION', 'Document créé')
            
            return formulaire_id
            
        except Exception as e:
            st.error(f"Erreur création formulaire: {e}")
            return None
    
    def _valider_donnees_formulaire(self, data: Dict) -> bool:
        """
        Valide les données de base d'un formulaire.
        
        Args:
            data: Données du formulaire à valider
            
        Returns:
            bool: True si valide, False sinon
        """
        # Type de formulaire obligatoire et valide
        if not data.get('type_formulaire') or not valider_type_formulaire(data['type_formulaire']):
            st.error("Type de formulaire manquant ou invalide")
            return False
        
        # Statut valide si fourni
        if data.get('statut') and not valider_statut(data['statut']):
            st.error("Statut invalide")
            return False
        
        # Priorité valide si fournie
        if data.get('priorite') and not valider_priorite(data['priorite']):
            st.error("Priorité invalide")
            return False
        
        return True
    
    def ajouter_lignes_formulaire(self, formulaire_id: int, lignes: List[Dict]) -> bool:
        """
        Ajoute les lignes de détail à un formulaire.
        
        Args:
            formulaire_id: ID du formulaire
            lignes: Liste des lignes à ajouter
            
        Returns:
            bool: True si succès, False sinon
        """
        try:
            for i, ligne in enumerate(lignes, 1):
                query = '''
                    INSERT INTO formulaire_lignes
                    (formulaire_id, sequence_ligne, description, quantite, unite,
                     prix_unitaire, montant_ligne, reference_materiau, code_article)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                
                montant_ligne = float(ligne.get('quantite', 0)) * float(ligne.get('prix_unitaire', 0))
                
                self.db.execute_insert(query, (
                    formulaire_id,
                    i,
                    ligne.get('description', ''),
                    ligne.get('quantite', 0),
                    ligne.get('unite', 'UN'),
                    ligne.get('prix_unitaire', 0),
                    montant_ligne,
                    ligne.get('reference_materiau'),
                    ligne.get('code_article', '')
                ))
            
            return True
                
        except Exception as e:
            st.error(f"Erreur ajout lignes: {e}")
            return False
    
    def get_formulaires(self, type_formulaire: str = None, statut: str = None, **filters) -> List[Dict]:
        """
        Récupère les formulaires avec filtres optionnels.
        
        Args:
            type_formulaire: Type de formulaire à filtrer
            statut: Statut à filtrer
            **filters: Autres filtres optionnels
            
        Returns:
            List[Dict]: Liste des formulaires
        """
        try:
            query = '''
                SELECT f.*, c.nom as company_nom, e.prenom || ' ' || e.nom as employee_nom,
                       p.nom_projet as project_nom
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN employees e ON f.employee_id = e.id  
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE 1=1
            '''
            params = []
            
            if type_formulaire:
                query += " AND f.type_formulaire = ?"
                params.append(type_formulaire)
            
            if statut:
                query += " AND f.statut = ?"
                params.append(statut)
            
            # Autres filtres dynamiques
            for key, value in filters.items():
                if value is not None:
                    query += f" AND f.{key} = ?"
                    params.append(value)
            
            query += " ORDER BY f.id DESC"
            
            rows = self.db.execute_query(query, tuple(params))
            return [dict(row) for row in rows]
            
        except Exception as e:
            st.error(f"Erreur récupération formulaires: {e}")
            return []
    
    def get_formulaire_details(self, formulaire_id: int) -> Optional[Dict]:
        """
        Récupère les détails complets d'un formulaire.
        
        Args:
            formulaire_id: ID du formulaire
            
        Returns:
            Dict: Détails complets du formulaire ou None
        """
        try:
            # Formulaire principal
            query = '''
                SELECT f.*, c.nom as company_nom, e.prenom || ' ' || e.nom as employee_nom,
                       p.nom_projet as project_nom
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN employees e ON f.employee_id = e.id
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE f.id = ?
            '''
            result = self.db.execute_query(query, (formulaire_id,))
            if not result:
                return None
            
            formulaire = dict(result[0])
            
            # Lignes de détail
            query_lignes = '''
                SELECT * FROM formulaire_lignes 
                WHERE formulaire_id = ? 
                ORDER BY sequence_ligne
            '''
            lignes = self.db.execute_query(query_lignes, (formulaire_id,))
            formulaire['lignes'] = [dict(ligne) for ligne in lignes]
            
            # Historique validations
            query_validations = '''
                SELECT fv.*, e.prenom || ' ' || e.nom as validator_nom
                FROM formulaire_validations fv
                LEFT JOIN employees e ON fv.employee_id = e.id
                WHERE fv.formulaire_id = ?
                ORDER BY fv.date_validation DESC
            '''
            validations = self.db.execute_query(query_validations, (formulaire_id,))
            formulaire['validations'] = [dict(val) for val in validations]
            
            return formulaire
            
        except Exception as e:
            st.error(f"Erreur récupération détails: {e}")
            return None
    
    def modifier_statut_formulaire(self, formulaire_id: int, nouveau_statut: str, 
                                  employee_id: int, commentaires: str = "") -> bool:
        """
        Modifie le statut d'un formulaire avec traçabilité.
        
        Args:
            formulaire_id: ID du formulaire
            nouveau_statut: Nouveau statut à appliquer
            employee_id: ID de l'employé effectuant le changement
            commentaires: Commentaires sur le changement
            
        Returns:
            bool: True si succès, False sinon
        """
        try:
            if not valider_statut(nouveau_statut):
                st.error(f"Statut invalide: {nouveau_statut}")
                return False
            
            # Mettre à jour le statut
            query = "UPDATE formulaires SET statut = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            self.db.execute_update(query, (nouveau_statut, formulaire_id))
            
            # Enregistrer la validation
            self.enregistrer_validation(formulaire_id, employee_id, 'CHANGEMENT_STATUT', 
                                      f"Statut modifié vers {nouveau_statut}. {commentaires}")
            
            return True
            
        except Exception as e:
            st.error(f"Erreur modification statut: {e}")
            return False
    
    def enregistrer_validation(self, formulaire_id: int, employee_id: int, 
                              type_validation: str, commentaires: str) -> bool:
        """
        Enregistre une validation/action sur un formulaire.
        
        Args:
            formulaire_id: ID du formulaire
            employee_id: ID de l'employé
            type_validation: Type de validation
            commentaires: Commentaires détaillés
            
        Returns:
            bool: True si succès, False sinon
        """
        try:
            query = '''
                INSERT INTO formulaire_validations
                (formulaire_id, employee_id, type_validation, commentaires, date_validation)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            '''
            self.db.execute_insert(query, (formulaire_id, employee_id, type_validation, commentaires))
            return True
            
        except Exception as e:
            st.error(f"Erreur enregistrement validation: {e}")
            return False
    
    def get_statistiques_formulaires(self) -> Dict:
        """
        Calcule les statistiques globales des formulaires.
        
        Returns:
            Dict: Statistiques par type de formulaire
        """
        try:
            stats = {}
            
            for type_form, config in self.types_formulaires.items():
                query = '''
                    SELECT statut, COUNT(*) as count, SUM(montant_total) as total_montant
                    FROM formulaires 
                    WHERE type_formulaire = ?
                    GROUP BY statut
                '''
                result = self.db.execute_query(query, (type_form,))
                
                stats[type_form] = {
                    'total': 0,
                    'par_statut': {},
                    'montant_total': 0.0,
                    'config': config
                }
                
                for row in result:
                    stats[type_form]['total'] += row['count']
                    stats[type_form]['par_statut'][row['statut']] = row['count']
                    stats[type_form]['montant_total'] += row['total_montant'] or 0
            
            return stats
            
        except Exception as e:
            st.error(f"Erreur calcul statistiques: {e}")
            return {}
    
    def dupliquer_formulaire(self, formulaire_id: int, nouveau_type: str = None) -> Optional[int]:
        """
        Duplique un formulaire existant.
        
        Args:
            formulaire_id: ID du formulaire à dupliquer
            nouveau_type: Nouveau type si conversion, sinon garde le même
            
        Returns:
            int: ID du nouveau formulaire ou None
        """
        try:
            # Récupérer le formulaire original
            original = self.get_formulaire_details(formulaire_id)
            if not original:
                return None
            
            # Préparer les nouvelles données
            nouveau_data = {
                'type_formulaire': nouveau_type or original['type_formulaire'],
                'project_id': original.get('project_id'),
                'company_id': original.get('company_id'),
                'employee_id': original.get('employee_id'),
                'statut': 'BROUILLON',  # Nouveau formulaire en brouillon
                'priorite': original.get('priorite'),
                'montant_total': original.get('montant_total', 0),
                'notes': f"Dupliqué depuis {original['numero_document']}\n\n{original.get('notes', '')}",
                'lignes': original.get('lignes', [])
            }
            
            return self.creer_formulaire(nouveau_data)
            
        except Exception as e:
            st.error(f"Erreur duplication formulaire: {e}")
            return None
