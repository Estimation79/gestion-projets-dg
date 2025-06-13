# -*- coding: utf-8 -*-
# employees.py - Module RH SQLite Unifié
# ERP Production DG Inc. - Migration JSON → SQLite

import json
import os
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional, Any

# === CONSTANTES MÉTALLURGIE QUÉBEC ===

# Départements spécifiques métallurgie mécano-soudé
DEPARTEMENTS = [
    "PRODUCTION",           # Soudeurs, journaliers, assemblage
    "USINAGE",             # Sciage, pliage, poinçonnage, découpe
    "INGÉNIERIE",          # Conception, dessin, calculs
    "QUALITÉ",             # Contrôle, inspection, réception
    "ADMINISTRATION",      # Bureau, comptabilité, RH
    "COMMERCIAL",          # Ventes, estimation, développement
    "DIRECTION"            # Supervision, contremaîtrise
]

# Statuts adaptés contexte québécois
STATUTS_EMPLOYE = [
    "ACTIF",               # Employé en service
    "CONGÉ",               # Congé personnel/parental
    "FORMATION",           # En formation/perfectionnement
    "ARRÊT_TRAVAIL",       # Maladie/accident de travail
    "INACTIF"              # Temporairement inactif
]

# Niveaux de compétence selon standards québécois
NIVEAUX_COMPETENCE = ["DÉBUTANT", "INTERMÉDIAIRE", "AVANCÉ", "EXPERT"]

# Types de contrat québécois
TYPES_CONTRAT = [
    "CDI",                 # Contrat à durée indéterminée
    "CDD",                 # Contrat à durée déterminée  
    "TEMPORAIRE",          # Travail temporaire/saisonnier
    "STAGE",               # Stagiaire
    "APPRENTISSAGE"        # Programme d'apprentissage
]

# Compétences spécifiques métallurgie mécano-soudé québécoise
COMPETENCES_DISPONIBLES = [
    # === SOUDAGE ET ASSEMBLAGE ===
    "Soudage GMAW (MIG)", "Soudage GTAW (TIG)", "Soudage SMAW (Électrode)",
    "Soudage SAW", "Soudage Flux-Core", "Lecture de plans de soudage",
    "Certification CWB", "Soudage acier inoxydable", "Soudage aluminium",
    "Position verticale", "Position plafond", "Assemblage soudé",
    "Préparation joints", "Post-traitement soudure", "Réparation soudure",
    
    # === USINAGE ET FABRICATION ===
    "Découpe plasma", "Découpe laser", "Oxycoupage", "Scie à ruban métal",
    "Pliage tôle", "Poinçonnage", "Cisaillage", "Meulage",
    "Usinage CNC", "Tour métaux", "Fraiseuse", "Perceuse à colonne",
    "Lecture de plans mécaniques", "Mesure et vérification",
    "Outils pneumatiques", "Outils hydrauliques", "Pont roulant",
    "Manutention lourde", "Assemblage mécanique",
    
    # === QUALITÉ ET CONTRÔLE ===
    "Contrôle dimensionnel", "Inspection visuelle soudure",
    "Ressuage (PT)", "Magnétoscopie (MT)", "Radiographie (RT)",
    "Ultrasons (UT)", "Métrologie", "Calibrage instruments",
    "ISO 9001", "Contrôle réception", "Documentation qualité",
    "Traçabilité matériaux", "Rapport d'inspection",
    
    # === CONCEPTION ET INGÉNIERIE ===
    "AutoCAD", "SolidWorks", "Inventor", "Tekla Structures",
    "SketchUp", "Calcul de structure", "Dessin technique",
    "Cotation GD&T", "Normes CSA", "Code de soudage W59",
    "Plans d'atelier", "Plans d'assemblage", "Nomenclatures",
    "Estimation matériaux", "Analyse contraintes",
    
    # === GESTION ET COMMERCIAL ===
    "Estimation projets", "ERP/MRP", "Gestion production",
    "Planification atelier", "Ordonnancement", "Approvisionnement",
    "Service client", "Négociation", "Soumission commerciale",
    "Gestion équipe", "Formation employés", "Suivi budget",
    "Analyse coûts", "Amélioration continue",
    
    # === ÉQUIPEMENTS SPÉCIALISÉS ===
    "Presse plieuse CNC", "Poinçonneuse CNC", "Centre usinage",
    "Robot de soudage", "Table plasma CNC", "Laser CO2",
    "Machines conventionnelles", "Outillage spécialisé",
    
    # === MATÉRIAUX MÉTALLURGIE ===
    "Acier doux", "Acier haute résistance", "Acier inoxydable",
    "Aluminium", "Alliages spéciaux", "Fonte", "Tôlerie",
    "Profilés structuraux", "Tubes et barres",
    
    # === SÉCURITÉ ET RÉGLEMENTATION QUÉBEC ===
    "CNESST", "Cadenassage LOTO", "Espaces clos",
    "Travail en hauteur", "SIMDUT 2015", "Premiers soins",
    "Sécurité atelier", "Prévention accidents", "EPI",
    "Manipulation matières dangereuses", "Protection incendie",
    
    # === LANGUES ET COMMUNICATION ===
    "Français", "Anglais", "Espagnol", "Communication technique",
    "Rédaction rapports", "Présentation client"
]

class GestionnaireEmployesSQL:
    """
    NOUVELLE ARCHITECTURE SQLite : Gestionnaire employés utilisant ERPDatabase
    Remplace GestionnaireEmployes (JSON) pour architecture unifiée
    """
    
    def __init__(self, db):
        self.db = db  # Instance ERPDatabase
        self.employes = []  # Cache des employés (pour compatibilité)
        self._load_employes_from_db()
        
        # Vérifier si données employés existent, sinon initialiser
        if not self.employes:
            self._initialiser_donnees_employes_dg_inc()
    
    def _load_employes_from_db(self):
        """Charge les employés depuis SQLite avec leurs compétences"""
        try:
            # Récupérer employés
            employes_rows = self.db.execute_query("""
                SELECT * FROM employees ORDER BY id
            """)
            
            self.employes = []
            for emp_row in employes_rows:
                employe = dict(emp_row)
                
                # Récupérer compétences de l'employé
                competences_rows = self.db.execute_query("""
                    SELECT nom_competence, niveau, certifie, date_obtention 
                    FROM employee_competences 
                    WHERE employee_id = ?
                """, (employe['id'],))
                
                employe['competences'] = [
                    {
                        'nom': row['nom_competence'],
                        'niveau': row['niveau'],
                        'certifie': bool(row['certifie']),
                        'date_obtention': row['date_obtention']
                    }
                    for row in competences_rows
                ]
                
                # Récupérer projets assignés
                projets_rows = self.db.execute_query("""
                    SELECT project_id FROM project_assignments WHERE employee_id = ?
                """, (employe['id'],))
                
                employe['projets_assignes'] = [row['project_id'] for row in projets_rows]
                
                self.employes.append(employe)
                
        except Exception as e:
            st.error(f"Erreur chargement employés SQLite: {e}")
            self.employes = []

    def _calculer_salaire_metallurgie(self, poste, experience_annees=5):
        """Calcule le salaire selon les standards québécois métallurgie"""
        salaires_base_qc = {
            "Soudeur": 55000,
            "Journalier": 45000, 
            "Scieur": 50000,
            "Plieur": 52000,
            "Poinçonneuse": 50000,
            "Dessinateur": 65000,
            "Qualité/Réception": 55000,
            "Contremaître/Superviseur": 75000,
            "Estimateur et intégration ERP": 70000,
            "Développement des affaires": 65000,
            "Adjointe administrative": 45000,
            "Marketing et web": 50000
        }
        base = salaires_base_qc.get(poste, 45000)
        # Ajustement selon expérience (1.5% par année)
        facteur_exp = 1 + (experience_annees * 0.015)
        return int(base * facteur_exp)

    def _get_competences_par_poste(self, poste):
        """Retourne les compétences typiques selon le poste"""
        competences_map = {
            "Soudeur": [
                {'nom': 'Soudage GMAW (MIG)', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Soudage GTAW (TIG)', 'niveau': 'INTERMÉDIAIRE', 'certifie': False},
                {'nom': 'Lecture de plans de soudage', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Assemblage soudé', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'CNESST', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Français', 'niveau': 'AVANCÉ', 'certifie': True}
            ],
            "Journalier": [
                {'nom': 'Assemblage mécanique', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Outils pneumatiques', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Pont roulant', 'niveau': 'INTERMÉDIAIRE', 'certifie': True},
                {'nom': 'Manutention lourde', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'CNESST', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Français', 'niveau': 'AVANCÉ', 'certifie': True}
            ],
            "Scieur": [
                {'nom': 'Scie à ruban métal', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'Découpe plasma', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Lecture de plans mécaniques', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Mesure et vérification', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'CNESST', 'niveau': 'AVANCÉ', 'certifie': True}
            ],
            "Plieur": [
                {'nom': 'Pliage tôle', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'Presse plieuse CNC', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Lecture de plans mécaniques', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'CNESST', 'niveau': 'AVANCÉ', 'certifie': True}
            ],
            "Poinçonneuse": [
                {'nom': 'Poinçonnage', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'Poinçonneuse CNC', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Lecture de plans mécaniques', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'CNESST', 'niveau': 'AVANCÉ', 'certifie': True}
            ],
            "Dessinateur": [
                {'nom': 'AutoCAD', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'SolidWorks', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Dessin technique', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'Code de soudage W59', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Plans d\'atelier', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'Français', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'Anglais', 'niveau': 'AVANCÉ', 'certifie': True}
            ],
            "Qualité/Réception": [
                {'nom': 'Contrôle dimensionnel', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'Inspection visuelle soudure', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Métrologie', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Documentation qualité', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'CNESST', 'niveau': 'AVANCÉ', 'certifie': True}
            ],
            "Contremaître/Superviseur": [
                {'nom': 'Gestion équipe', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'Planification atelier', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'Sécurité atelier', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'CNESST', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'Lecture de plans mécaniques', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Français', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'Anglais', 'niveau': 'AVANCÉ', 'certifie': True}
            ],
            "Estimateur et intégration ERP": [
                {'nom': 'Estimation projets', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'ERP/MRP', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'Analyse coûts', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Soumission commerciale', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Français', 'niveau': 'EXPERT', 'certifie': True}
            ],
            "Développement des affaires": [
                {'nom': 'Service client', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'Négociation', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Présentation client', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Français', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'Anglais', 'niveau': 'AVANCÉ', 'certifie': True}
            ],
            "Adjointe administrative": [
                {'nom': 'Gestion production', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Communication technique', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Rédaction rapports', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Français', 'niveau': 'EXPERT', 'certifie': True}
            ],
            "Marketing et web": [
                {'nom': 'Communication technique', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Présentation client', 'niveau': 'AVANCÉ', 'certifie': True},
                {'nom': 'Français', 'niveau': 'EXPERT', 'certifie': True},
                {'nom': 'Anglais', 'niveau': 'AVANCÉ', 'certifie': True}
            ]
        }
        return competences_map.get(poste, [
            {'nom': 'CNESST', 'niveau': 'AVANCÉ', 'certifie': True},
            {'nom': 'Français', 'niveau': 'AVANCÉ', 'certifie': True}
        ])

    def _initialiser_donnees_employes_dg_inc(self):
        """Initialise avec les vrais employés de DG Inc. en SQLite"""
        if self.db.get_table_count('employees') > 0:
            return  # Déjà initialisé
        
        # Données des 21 employés réels de DG Inc.
        employes_data = [
            # === PRODUCTION (11 employés) ===
            {
                'id': 1, 'prenom': 'Alex', 'nom': 'Boucher Cloutier',
                'email': 'alex.bouchercloutier@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Journalier', 'departement': 'PRODUCTION',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2020-03-15',
                'salaire': self._calculer_salaire_metallurgie('Journalier', 4),
                'manager_id': 11,  # Martin Beauregard
                'competences': self._get_competences_par_poste('Journalier'),
                'projets_assignes': [], 'charge_travail': 85,
                'notes': 'Employé polyvalent production - Badge ID: 566',
                'photo_url': ''
            },
            {
                'id': 2, 'prenom': 'François', 'nom': 'Lapointe',
                'email': 'francois.lapointe@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Soudeur', 'departement': 'PRODUCTION',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2018-06-01',
                'salaire': self._calculer_salaire_metallurgie('Soudeur', 6),
                'manager_id': 11,
                'competences': self._get_competences_par_poste('Soudeur'),
                'projets_assignes': [], 'charge_travail': 90,
                'notes': 'Soudeur certifié MIG/TIG - Badge ID: 492',
                'photo_url': ''
            },
            {
                'id': 3, 'prenom': 'Andrew', 'nom': 'Jones',
                'email': 'andrew.jones@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Scieur', 'departement': 'USINAGE',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2019-09-15',
                'salaire': self._calculer_salaire_metallurgie('Scieur', 5),
                'manager_id': 11,
                'competences': self._get_competences_par_poste('Scieur'),
                'projets_assignes': [], 'charge_travail': 88,
                'notes': 'Spécialiste découpe et préparation - Badge ID: 375',
                'photo_url': ''
            },
            {
                'id': 4, 'prenom': 'Denis', 'nom': 'Jetté',
                'email': 'ingenierie@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Dessinateur', 'departement': 'INGÉNIERIE',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2015-01-20',
                'salaire': self._calculer_salaire_metallurgie('Dessinateur', 9),
                'manager_id': None,
                'competences': self._get_competences_par_poste('Dessinateur'),
                'projets_assignes': [], 'charge_travail': 95,
                'notes': 'Dessinateur senior, expert AutoCAD - Badge ID: 434',
                'photo_url': ''
            },
            {
                'id': 5, 'prenom': 'Lucien', 'nom': 'Kock',
                'email': 'lucien.kock@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Soudeur', 'departement': 'PRODUCTION',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2017-11-01',
                'salaire': self._calculer_salaire_metallurgie('Soudeur', 7),
                'manager_id': 11,
                'competences': self._get_competences_par_poste('Soudeur'),
                'projets_assignes': [], 'charge_travail': 87,
                'notes': 'Soudeur expérimenté, spécialiste TIG',
                'photo_url': ''
            },
            {
                'id': 6, 'prenom': 'Daniel', 'nom': 'Paquette',
                'email': 'daniel.paquette@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Journalier', 'departement': 'PRODUCTION',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2021-04-12',
                'salaire': self._calculer_salaire_metallurgie('Journalier', 3),
                'manager_id': 11,
                'competences': self._get_competences_par_poste('Journalier'),
                'projets_assignes': [], 'charge_travail': 82,
                'notes': 'Journalier polyvalent assemblage',
                'photo_url': ''
            },
            {
                'id': 7, 'prenom': 'Denis', 'nom': 'Lacasse',
                'email': 'denis.lacasse@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Plieur', 'departement': 'USINAGE',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2016-08-15',
                'salaire': self._calculer_salaire_metallurgie('Plieur', 8),
                'manager_id': 11,
                'competences': self._get_competences_par_poste('Plieur'),
                'projets_assignes': [], 'charge_travail': 90,
                'notes': 'Expert pliage tôle, presse CNC',
                'photo_url': ''
            },
            {
                'id': 8, 'prenom': 'Maxime', 'nom': 'Gagné',
                'email': 'maxime.gagne@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Soudeur', 'departement': 'PRODUCTION',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2019-02-20',
                'salaire': self._calculer_salaire_metallurgie('Soudeur', 5),
                'manager_id': 11,
                'competences': self._get_competences_par_poste('Soudeur'),
                'projets_assignes': [], 'charge_travail': 89,
                'notes': 'Soudeur certifié, formation continue',
                'photo_url': ''
            },
            {
                'id': 9, 'prenom': 'Nicolas', 'nom': 'Martin',
                'email': 'nicolas.martin@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Poinçonneuse', 'departement': 'USINAGE',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2018-10-05',
                'salaire': self._calculer_salaire_metallurgie('Poinçonneuse', 6),
                'manager_id': 11,
                'competences': self._get_competences_par_poste('Poinçonneuse'),
                'projets_assignes': [], 'charge_travail': 86,
                'notes': 'Opérateur poinçonneuse CNC certifié',
                'photo_url': ''
            },
            {
                'id': 10, 'prenom': 'Luis Waldo', 'nom': 'Pavez Gonzalez',
                'email': 'luis.pavez@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Journalier', 'departement': 'PRODUCTION',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2020-07-10',
                'salaire': self._calculer_salaire_metallurgie('Journalier', 4),
                'manager_id': 11,
                'competences': self._get_competences_par_poste('Journalier') + [
                    {'nom': 'Espagnol', 'niveau': 'EXPERT', 'certifie': True}
                ],
                'projets_assignes': [], 'charge_travail': 84,
                'notes': 'Trilingue (français/anglais/espagnol)',
                'photo_url': ''
            },
            # === SUPERVISION ===
            {
                'id': 11, 'prenom': 'Martin', 'nom': 'Beauregard',
                'email': 'mbeauregard@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Contremaître/Superviseur', 'departement': 'DIRECTION',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2012-05-01',
                'salaire': self._calculer_salaire_metallurgie('Contremaître/Superviseur', 12),
                'manager_id': None,
                'competences': self._get_competences_par_poste('Contremaître/Superviseur'),
                'projets_assignes': [], 'charge_travail': 100,
                'notes': 'Contremaître principal, responsable production - Badge ID: 149',
                'photo_url': ''
            },
            # === SUITE DES EMPLOYÉS ===
            {
                'id': 12, 'prenom': 'Williams Cédrick', 'nom': 'Kengne Tzokeu',
                'email': 'williams.kengne@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Soudeur', 'departement': 'PRODUCTION',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2021-01-15',
                'salaire': self._calculer_salaire_metallurgie('Soudeur', 3),
                'manager_id': 11,
                'competences': self._get_competences_par_poste('Soudeur'),
                'projets_assignes': [], 'charge_travail': 86,
                'notes': 'Soudeur junior en formation avancée',
                'photo_url': ''
            },
            {
                'id': 13, 'prenom': 'Martin', 'nom': 'Leduc',
                'email': 'martin.leduc@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Journalier', 'departement': 'PRODUCTION',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2019-05-20',
                'salaire': self._calculer_salaire_metallurgie('Journalier', 5),
                'manager_id': 11,
                'competences': self._get_competences_par_poste('Journalier'),
                'projets_assignes': [], 'charge_travail': 88,
                'notes': 'Journalier expérimenté, polyvalent',
                'photo_url': ''
            },
            {
                'id': 14, 'prenom': 'Roxanne', 'nom': 'Lanctôt',
                'email': 'roxanne.lanctot@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Qualité/Réception', 'departement': 'QUALITÉ',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2017-09-01',
                'salaire': self._calculer_salaire_metallurgie('Qualité/Réception', 7),
                'manager_id': 11,
                'competences': self._get_competences_par_poste('Qualité/Réception'),
                'projets_assignes': [], 'charge_travail': 85,
                'notes': 'Responsable qualité et réception matériaux',
                'photo_url': ''
            },
            {
                'id': 15, 'prenom': 'Samuel', 'nom': 'Turcotte',
                'email': 'samuel.turcotte@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Journalier', 'departement': 'PRODUCTION',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2022-03-10',
                'salaire': self._calculer_salaire_metallurgie('Journalier', 2),
                'manager_id': 11,
                'competences': self._get_competences_par_poste('Journalier'),
                'projets_assignes': [], 'charge_travail': 80,
                'notes': 'Journalier récent, apprentissage rapide',
                'photo_url': ''
            },
            {
                'id': 16, 'prenom': 'Éric', 'nom': 'Brisebois',
                'email': 'eric.brisebois@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Soudeur', 'departement': 'PRODUCTION',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2016-04-15',
                'salaire': self._calculer_salaire_metallurgie('Soudeur', 8),
                'manager_id': 11,
                'competences': self._get_competences_par_poste('Soudeur'),
                'projets_assignes': [], 'charge_travail': 91,
                'notes': 'Soudeur senior, mentor pour juniors',
                'photo_url': ''
            },
            # === COMMERCIAL ET ESTIMATION ===
            {
                'id': 17, 'prenom': 'Jovick', 'nom': 'Desmarais',
                'email': 'jovick.desmarais@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Développement des affaires', 'departement': 'COMMERCIAL',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2014-06-01',
                'salaire': self._calculer_salaire_metallurgie('Développement des affaires', 10),
                'manager_id': None,
                'competences': self._get_competences_par_poste('Développement des affaires'),
                'projets_assignes': [], 'charge_travail': 95,
                'notes': 'Développement commercial et relations clients',
                'photo_url': ''
            },
            {
                'id': 18, 'prenom': 'Sylvain', 'nom': 'Leduc',
                'email': 'sylvain.leduc@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Estimateur et intégration ERP', 'departement': 'COMMERCIAL',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2013-09-15',
                'salaire': self._calculer_salaire_metallurgie('Estimateur et intégration ERP', 11),
                'manager_id': None,
                'competences': self._get_competences_par_poste('Estimateur et intégration ERP'),
                'projets_assignes': [], 'charge_travail': 98,
                'notes': 'Expert estimation et système ERP',
                'photo_url': ''
            },
            # === ADMINISTRATION ===
            {
                'id': 19, 'prenom': 'Myriam', 'nom': 'Girouard',
                'email': 'myriam.girouard@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Adjointe administrative', 'departement': 'ADMINISTRATION',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2018-02-01',
                'salaire': self._calculer_salaire_metallurgie('Adjointe administrative', 6),
                'manager_id': None,
                'competences': self._get_competences_par_poste('Adjointe administrative'),
                'projets_assignes': [], 'charge_travail': 85,
                'notes': 'Gestion administrative et coordination',
                'photo_url': ''
            },
            {
                'id': 20, 'prenom': 'Cindy', 'nom': 'Julien',
                'email': 'cindy.julien@dg-inc.qc.ca',
                'telephone': '450-372-9630',
                'poste': 'Marketing et web', 'departement': 'ADMINISTRATION',
                'statut': 'ACTIF', 'type_contrat': 'CDI',
                'date_embauche': '2020-11-10',
                'salaire': self._calculer_salaire_metallurgie('Marketing et web', 4),
                'manager_id': None,
                'competences': self._get_competences_par_poste('Marketing et web'),
                'projets_assignes': [], 'charge_travail': 80,
                'notes': 'Responsable marketing digital et web',
                'photo_url': ''
            }
        ]
        
        # Insérer chaque employé en SQLite
        for emp_data in employes_data:
            emp_id = self.ajouter_employe_sql(emp_data)
            if emp_id:
                st.info(f"Employé {emp_data['prenom']} {emp_data['nom']} initialisé en SQLite (ID: {emp_id})")
        
        # Recharger depuis SQLite
        self._load_employes_from_db()

    # --- Méthodes CRUD SQLite ---
    
    def ajouter_employe_sql(self, data_employe):
        """Ajoute un nouvel employé en SQLite avec ses compétences"""
        try:
            # Insérer employé principal
            query_emp = '''
                INSERT INTO employees 
                (id, prenom, nom, email, telephone, poste, departement, statut, 
                 type_contrat, date_embauche, salaire, manager_id, charge_travail, 
                 notes, photo_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            emp_id = self.db.execute_insert(query_emp, (
                data_employe.get('id'),
                data_employe['prenom'],
                data_employe['nom'],
                data_employe.get('email'),
                data_employe.get('telephone'),
                data_employe.get('poste'),
                data_employe.get('departement'),
                data_employe.get('statut', 'ACTIF'),
                data_employe.get('type_contrat', 'CDI'),
                data_employe.get('date_embauche'),
                data_employe.get('salaire'),
                data_employe.get('manager_id'),
                data_employe.get('charge_travail', 80),
                data_employe.get('notes'),
                data_employe.get('photo_url')
            ))
            
            # Insérer compétences
            competences = data_employe.get('competences', [])
            for comp in competences:
                self.db.execute_insert('''
                    INSERT INTO employee_competences 
                    (employee_id, nom_competence, niveau, certifie, date_obtention)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    emp_id,
                    comp.get('nom'),
                    comp.get('niveau'),
                    comp.get('certifie', False),
                    comp.get('date_obtention')
                ))
            
            # Insérer assignations projets
            projets_assignes = data_employe.get('projets_assignes', [])
            for proj_id in projets_assignes:
                self.db.execute_insert('''
                    INSERT OR IGNORE INTO project_assignments 
                    (project_id, employee_id, role_projet)
                    VALUES (?, ?, ?)
                ''', (proj_id, emp_id, 'Membre équipe'))
            
            return emp_id
            
        except Exception as e:
            st.error(f"Erreur ajout employé SQLite: {e}")
            return None

    def ajouter_employe(self, data_employe):
        """Interface de compatibilité pour ajouter employé"""
        emp_id = self.ajouter_employe_sql(data_employe)
        if emp_id:
            self._load_employes_from_db()  # Recharger cache
        return emp_id

    def modifier_employe(self, id_employe, data_employe):
        """Modifie un employé existant en SQLite"""
        try:
            # Mettre à jour employé principal
            update_fields = []
            params = []
            
            fields_map = {
                'prenom': 'prenom', 'nom': 'nom', 'email': 'email',
                'telephone': 'telephone', 'poste': 'poste', 'departement': 'departement',
                'statut': 'statut', 'type_contrat': 'type_contrat',
                'date_embauche': 'date_embauche', 'salaire': 'salaire',
                'manager_id': 'manager_id', 'charge_travail': 'charge_travail',
                'notes': 'notes', 'photo_url': 'photo_url'
            }
            
            for field, col in fields_map.items():
                if field in data_employe:
                    update_fields.append(f"{col} = ?")
                    params.append(data_employe[field])
            
            if update_fields:
                query = f"UPDATE employees SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
                params.append(id_employe)
                self.db.execute_update(query, tuple(params))
            
            # Mettre à jour compétences si fournies
            if 'competences' in data_employe:
                # Supprimer anciennes compétences
                self.db.execute_update("DELETE FROM employee_competences WHERE employee_id = ?", (id_employe,))
                
                # Ajouter nouvelles compétences
                for comp in data_employe['competences']:
                    self.db.execute_insert('''
                        INSERT INTO employee_competences 
                        (employee_id, nom_competence, niveau, certifie, date_obtention)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        id_employe,
                        comp.get('nom'),
                        comp.get('niveau'),
                        comp.get('certifie', False),
                        comp.get('date_obtention')
                    ))
            
            # Mettre à jour assignations projets si fournies
            if 'projets_assignes' in data_employe:
                # Supprimer anciennes assignations
                self.db.execute_update("DELETE FROM project_assignments WHERE employee_id = ?", (id_employe,))
                
                # Ajouter nouvelles assignations
                for proj_id in data_employe['projets_assignes']:
                    self.db.execute_insert('''
                        INSERT OR IGNORE INTO project_assignments 
                        (project_id, employee_id, role_projet)
                        VALUES (?, ?, ?)
                    ''', (proj_id, id_employe, 'Membre équipe'))
            
            self._load_employes_from_db()  # Recharger cache
            return True
            
        except Exception as e:
            st.error(f"Erreur modification employé SQLite: {e}")
            return False

    def supprimer_employe(self, id_employe):
        """Supprime un employé et ses données associées"""
        try:
            # Supprimer les données associées d'abord (contraintes FK)
            self.db.execute_update("DELETE FROM employee_competences WHERE employee_id = ?", (id_employe,))
            self.db.execute_update("DELETE FROM project_assignments WHERE employee_id = ?", (id_employe,))
            self.db.execute_update("DELETE FROM time_entries WHERE employee_id = ?", (id_employe,))
            
            # Mettre à jour les références manager_id
            self.db.execute_update("UPDATE employees SET manager_id = NULL WHERE manager_id = ?", (id_employe,))
            
            # Supprimer l'employé
            self.db.execute_update("DELETE FROM employees WHERE id = ?", (id_employe,))
            
            self._load_employes_from_db()  # Recharger cache
            return True
            
        except Exception as e:
            st.error(f"Erreur suppression employé SQLite: {e}")
            return False

    def get_employe_by_id(self, id_employe):
        """Récupère un employé par ID (depuis cache)"""
        return next((emp for emp in self.employes if emp.get('id') == id_employe), None)

    def get_employes_by_departement(self, departement):
        """Récupère employés par département"""
        return [emp for emp in self.employes if emp.get('departement') == departement]

    def get_employes_by_projet(self, projet_id):
        """Récupère employés assignés à un projet"""
        return [emp for emp in self.employes if projet_id in emp.get('projets_assignes', [])]

    def get_managers(self):
        """Récupère les managers (employés sans manager)"""
        return [emp for emp in self.employes if not emp.get('manager_id')]

    def get_subordinates(self, manager_id):
        """Récupère les subordonnés d'un manager"""
        return [emp for emp in self.employes if emp.get('manager_id') == manager_id]

    # --- Méthodes d'analyse adaptées Québec (compatibilité) ---
    
    def get_statistiques_employes(self):
        """Version adaptée des statistiques pour métallurgie québécoise"""
        if not self.employes:
            return {}
        
        stats = {
            'total': len(self.employes),
            'par_departement': {},
            'par_statut': {},
            'par_type_contrat': {},
            'salaire_moyen': 0,
            'charge_moyenne': 0,
            'competences_populaires': {},
            'certifications_cnesst': 0,
            'langues_parlees': {},
            'anciennete_moyenne': 0,
            'soudeurs_certifies': 0,
            'bilingues': 0
        }
        
        total_salaire = 0
        total_charge = 0
        total_anciennete = 0
        toutes_competences = {}
        langues = {}
        
        for emp in self.employes:
            # Départements
            dept = emp.get('departement', 'N/A')
            stats['par_departement'][dept] = stats['par_departement'].get(dept, 0) + 1
            
            # Statuts
            statut = emp.get('statut', 'N/A')
            stats['par_statut'][statut] = stats['par_statut'].get(statut, 0) + 1
            
            # Types de contrat
            contrat = emp.get('type_contrat', 'N/A')
            stats['par_type_contrat'][contrat] = stats['par_type_contrat'].get(contrat, 0) + 1
            
            # Salaires en CAD
            if emp.get('salaire'):
                total_salaire += emp['salaire']
            
            # Charge de travail
            if emp.get('charge_travail'):
                total_charge += emp['charge_travail']
            
            # Ancienneté
            if emp.get('date_embauche'):
                try:
                    date_emb = datetime.strptime(emp['date_embauche'], '%Y-%m-%d')
                    anciennete = (datetime.now() - date_emb).days / 365.25
                    total_anciennete += anciennete
                except:
                    pass
            
            # Analyse des compétences
            competences_emp = emp.get('competences', [])
            has_francais = False
            has_anglais = False
            has_soudage = False
            has_cnesst = False
            
            for comp in competences_emp:
                nom_comp = comp.get('nom')
                if nom_comp:
                    toutes_competences[nom_comp] = toutes_competences.get(nom_comp, 0) + 1
                    
                    # Vérifications spécifiques
                    if 'CNESST' in nom_comp and comp.get('certifie'):
                        has_cnesst = True
                    if 'Soudage' in nom_comp:
                        has_soudage = True
                    if nom_comp == 'Français':
                        has_francais = True
                    if nom_comp == 'Anglais':
                        has_anglais = True
                    if nom_comp in ['Français', 'Anglais', 'Espagnol']:
                        langues[nom_comp] = langues.get(nom_comp, 0) + 1
            
            # Compteurs spéciaux
            if has_cnesst:
                stats['certifications_cnesst'] += 1
            if has_soudage:
                stats['soudeurs_certifies'] += 1
            if has_francais and has_anglais:
                stats['bilingues'] += 1
        
        # Calculs des moyennes
        if self.employes:
            stats['salaire_moyen'] = total_salaire / len(self.employes)
            stats['charge_moyenne'] = total_charge / len(self.employes)
            stats['anciennete_moyenne'] = total_anciennete / len(self.employes)
        
        # Top 10 compétences
        stats['competences_populaires'] = dict(
            sorted(toutes_competences.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        
        # Langues
        stats['langues_parlees'] = langues
        
        return stats

    def generer_rapport_rh_metallurgie(self):
        """Génère un rapport RH spécifique métallurgie"""
        stats = self.get_statistiques_employes()
        
        rapport = {
            'date_rapport': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'entreprise': 'DG Inc. - Métallurgie Mécano-Soudé',
            'localisation': 'Québec, Canada',
            'effectif_total': stats['total'],
            'repartition_departements': stats['par_departement'],
            'salaire_moyen_cad': f"{stats['salaire_moyen']:,.0f}$ CAD",
            'anciennete_moyenne': f"{stats['anciennete_moyenne']:.1f} années",
            'taux_certification_cnesst': f"{(stats['certifications_cnesst']/stats['total']*100):.1f}%",
            'soudeurs_certifies': stats['soudeurs_certifies'],
            'employes_bilingues': stats['bilingues'],
            'competences_critiques': {
                'soudage': len([e for e in self.employes if any('Soudage' in c.get('nom', '') for c in e.get('competences', []))]),
                'lecture_plans': len([e for e in self.employes if any('plans' in c.get('nom', '').lower() for c in e.get('competences', []))]),
                'cnesst': stats['certifications_cnesst'],
                'pont_roulant': len([e for e in self.employes if any('Pont roulant' in c.get('nom', '') for c in e.get('competences', []))])
            }
        }
        
        return rapport

    # Méthodes de compatibilité (JSON legacy)
    def charger_donnees_employes(self):
        """Méthode de compatibilité - charge depuis SQLite maintenant"""
        self._load_employes_from_db()
    
    def sauvegarder_donnees_employes(self):
        """Méthode de compatibilité - sauvegarde automatique SQLite"""
        pass  # Sauvegarde automatique en SQLite

# --- Fonctions d'affichage Streamlit adaptées SQLite ---

def render_employes_liste_tab(emp_manager, projet_manager):
    """Interface liste employés - Compatible SQLite"""
    st.subheader("👥 Employés DG Inc. - Métallurgie (SQLite)")
    
    col_create, col_search = st.columns([1, 2])
    with col_create:
        if st.button("➕ Nouvel Employé", key="emp_create_btn", use_container_width=True):
            st.session_state.emp_action = "create_employe"
            st.session_state.emp_selected_id = None
    
    with col_search:
        search_term = st.text_input("Rechercher un employé...", key="emp_search")
    
    # Filtres adaptés métallurgie
    with st.expander("🔍 Filtres avancés", expanded=False):
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            filtre_dept = st.multiselect(
                "Département:", 
                ['Tous'] + DEPARTEMENTS, 
                default=['Tous']
            )
        with fcol2:
            filtre_statut = st.multiselect("Statut:", ['Tous'] + STATUTS_EMPLOYE, default=['Tous'])
        with fcol3:
            filtre_contrat = st.multiselect("Type contrat:", ['Tous'] + TYPES_CONTRAT, default=['Tous'])
    
    # Filtrage des employés
    employes_filtres = emp_manager.employes
    
    if search_term:
        term = search_term.lower()
        employes_filtres = [
            emp for emp in employes_filtres if
            term in emp.get('prenom', '').lower() or
            term in emp.get('nom', '').lower() or
            term in emp.get('email', '').lower() or
            term in emp.get('poste', '').lower()
        ]
    
    if 'Tous' not in filtre_dept and filtre_dept:
        employes_filtres = [emp for emp in employes_filtres if emp.get('departement') in filtre_dept]
    
    if 'Tous' not in filtre_statut and filtre_statut:
        employes_filtres = [emp for emp in employes_filtres if emp.get('statut') in filtre_statut]
    
    if 'Tous' not in filtre_contrat and filtre_contrat:
        employes_filtres = [emp for emp in employes_filtres if emp.get('type_contrat') in filtre_contrat]
    
    if employes_filtres:
        st.success(f"📊 {len(employes_filtres)} employé(s) trouvé(s) en base SQLite")
        
        # Affichage tableau adapté
        employes_data_display = []
        for emp in employes_filtres:
            manager = emp_manager.get_employe_by_id(emp.get('manager_id')) if emp.get('manager_id') else None
            manager_nom = f"{manager.get('prenom', '')} {manager.get('nom', '')}" if manager else "Autonome"
            
            # Projets assignés
            projets_noms = []
            if projet_manager and hasattr(projet_manager, 'projets'):
                for proj_id in emp.get('projets_assignes', []):
                    projet = next((p for p in projet_manager.projets if p.get('id') == proj_id), None)
                    if projet:
                        projets_noms.append(projet.get('nom_projet', f'Projet #{proj_id}'))
            
            employes_data_display.append({
                "ID": emp.get('id'),
                "Nom": f"{emp.get('prenom', '')} {emp.get('nom', '')}",
                "Poste": emp.get('poste', ''),
                "Département": emp.get('departement', ''),
                "Statut": emp.get('statut', ''),
                "Salaire CAD": f"{emp.get('salaire', 0):,}$",
                "Manager": manager_nom,
                "Charge": f"{emp.get('charge_travail', 0)}%",
                "Email": emp.get('email', '')
            })
        
        st.dataframe(pd.DataFrame(employes_data_display), use_container_width=True)
        
        # Actions sur employé sélectionné
        st.markdown("---")
        st.markdown("### 🔧 Actions sur un employé")
        selected_emp_id = st.selectbox(
            "Sélectionner un employé:",
            options=[emp['id'] for emp in employes_filtres],
            format_func=lambda eid: next((f"#{eid} - {emp.get('prenom', '')} {emp.get('nom', '')}" for emp in employes_filtres if emp.get('id') == eid), ''),
            key="emp_action_select"
        )
        
        if selected_emp_id:
            col_act1, col_act2, col_act3 = st.columns(3)
            with col_act1:
                if st.button("👁️ Voir Profil", key=f"emp_view_{selected_emp_id}", use_container_width=True):
                    st.session_state.emp_action = "view_employe_details"
                    st.session_state.emp_selected_id = selected_emp_id
            with col_act2:
                if st.button("✏️ Modifier", key=f"emp_edit_{selected_emp_id}", use_container_width=True):
                    st.session_state.emp_action = "edit_employe"
                    st.session_state.emp_selected_id = selected_emp_id
            with col_act3:
                if st.button("🗑️ Supprimer", key=f"emp_delete_{selected_emp_id}", use_container_width=True):
                    st.session_state.emp_confirm_delete_id = selected_emp_id
    else:
        st.info("Aucun employé correspondant aux filtres.")
    
    # Confirmation de suppression
    if 'emp_confirm_delete_id' in st.session_state and st.session_state.emp_confirm_delete_id:
        emp_to_delete = emp_manager.get_employe_by_id(st.session_state.emp_confirm_delete_id)
        if emp_to_delete:
            st.warning(f"⚠️ Supprimer {emp_to_delete.get('prenom')} {emp_to_delete.get('nom')} de la base SQLite ? Action irréversible.")
            col_del1, col_del2 = st.columns(2)
            if col_del1.button("Oui, supprimer SQLite", type="primary", key="emp_confirm_delete_final"):
                if emp_manager.supprimer_employe(st.session_state.emp_confirm_delete_id):
                    st.success("✅ Employé supprimé de SQLite.")
                    del st.session_state.emp_confirm_delete_id
                    st.rerun()
                else:
                    st.error("❌ Erreur suppression SQLite.")
            if col_del2.button("Annuler", key="emp_cancel_delete_final"):
                del st.session_state.emp_confirm_delete_id
                st.rerun()

def render_employes_dashboard_tab(emp_manager, projet_manager):
    """Dashboard RH - Compatible SQLite"""
    st.subheader("📊 Dashboard RH - DG Inc. Métallurgie (SQLite)")
    
    stats = emp_manager.get_statistiques_employes()
    if not stats:
        st.info("Aucune donnée d'employé disponible en SQLite.")
        return
    
    # Métriques principales adaptées Québec
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Total Employés", stats['total'])
    with col2:
        st.metric("💰 Salaire Moyen", f"{stats['salaire_moyen']:,.0f}$ CAD")
    with col3:
        st.metric("🏗️ Certifiés CNESST", stats.get('certifications_cnesst', 0))
    with col4:
        st.metric("🔧 Soudeurs", stats.get('soudeurs_certifies', 0))
    
    # Métriques secondaires
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("📊 Charge Moyenne", f"{stats['charge_moyenne']:.1f}%")
    with col6:
        st.metric("📅 Ancienneté Moy.", f"{stats.get('anciennete_moyenne', 0):.1f} ans")
    with col7:
        st.metric("🌍 Bilingues", stats.get('bilingues', 0))
    with col8:
        employes_surcharges = len([emp for emp in emp_manager.employes if emp.get('charge_travail', 0) > 90])
        st.metric("⚠️ Surchargés", employes_surcharges)
    
    # Graphiques adaptés métallurgie
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        if stats['par_departement']:
            # Couleurs spécifiques métallurgie
            colors_dept = {
                'PRODUCTION': '#ff6b35',
                'USINAGE': '#004e89',
                'INGÉNIERIE': '#9b59b6',
                'QUALITÉ': '#2ecc71',
                'COMMERCIAL': '#f39c12',
                'ADMINISTRATION': '#95a5a6',
                'DIRECTION': '#e74c3c'
            }
            
            fig_dept = px.pie(
                values=list(stats['par_departement'].values()),
                names=list(stats['par_departement'].keys()),
                title="🏭 Répartition par Département (SQLite)",
                color=list(stats['par_departement'].keys()),
                color_discrete_map=colors_dept
            )
            fig_dept.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                title_x=0.5
            )
            st.plotly_chart(fig_dept, use_container_width=True)
    
    with col_g2:
        if stats['par_statut']:
            colors_statut = {
                'ACTIF': '#2ecc71',
                'CONGÉ': '#f39c12', 
                'FORMATION': '#3498db',
                'ARRÊT_TRAVAIL': '#e74c3c',
                'INACTIF': '#95a5a6'
            }
            fig_statut = px.bar(
                x=list(stats['par_statut'].keys()),
                y=list(stats['par_statut'].values()),
                title="📈 Statut des Employés (SQLite)",
                color=list(stats['par_statut'].keys()),
                color_discrete_map=colors_statut
            )
            fig_statut.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                showlegend=False,
                title_x=0.5
            )
            st.plotly_chart(fig_statut, use_container_width=True)
    
    # Compétences et langues
    if stats['competences_populaires']:
        st.markdown("---")
        col_comp1, col_comp2 = st.columns(2)
        
        with col_comp1:
            st.markdown("##### 🎯 Top Compétences Métallurgie")
            fig_comp = px.bar(
                x=list(stats['competences_populaires'].values()),
                y=list(stats['competences_populaires'].keys()),
                orientation='h',
                title="🔧 Compétences les plus présentes"
            )
            fig_comp.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                title_x=0.5
            )
            st.plotly_chart(fig_comp, use_container_width=True)
        
        with col_comp2:
            st.markdown("##### 🌍 Langues Parlées")
            if stats['langues_parlees']:
                fig_langues = px.bar(
                    x=list(stats['langues_parlees'].keys()),
                    y=list(stats['langues_parlees'].values()),
                    title="🗣️ Répartition des Langues",
                    color=list(stats['langues_parlees'].keys()),
                    color_discrete_map={'Français': '#0066cc', 'Anglais': '#cc0000', 'Espagnol': '#ffcc00'}
                )
                fig_langues.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='var(--text-color)'),
                    showlegend=False,
                    title_x=0.5
                )
                st.plotly_chart(fig_langues, use_container_width=True)
            else:
                st.info("Aucune donnée de langue disponible")
    
    # Rapport métallurgie
    st.markdown("---")
    if st.button("📋 Générer Rapport RH Métallurgie (SQLite)", use_container_width=True):
        rapport = emp_manager.generer_rapport_rh_metallurgie()
        
        st.markdown("### 📊 Rapport RH - DG Inc. Métallurgie (SQLite)")
        st.markdown(f"**Date:** {rapport['date_rapport']}")
        st.markdown(f"**Entreprise:** {rapport['entreprise']}")
        st.markdown(f"**Localisation:** {rapport['localisation']}")
        
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.markdown(f"**Effectif Total:** {rapport['effectif_total']}")
            st.markdown(f"**Salaire Moyen:** {rapport['salaire_moyen_cad']}")
        with col_r2:
            st.markdown(f"**Ancienneté Moyenne:** {rapport['anciennete_moyenne']}")
            st.markdown(f"**Taux CNESST:** {rapport['taux_certification_cnesst']}")
        with col_r3:
            st.markdown(f"**Soudeurs Certifiés:** {rapport['soudeurs_certifies']}")
            st.markdown(f"**Employés Bilingues:** {rapport['employes_bilingues']}")

def render_employe_form(emp_manager, employe_data=None):
    """Formulaire employé - Compatible SQLite"""
    form_title = "➕ Ajouter un Nouvel Employé (SQLite)" if employe_data is None else f"✏️ Modifier {employe_data.get('prenom')} {employe_data.get('nom')} (SQLite)"
    
    with st.expander(form_title, expanded=True):
        # GESTION DES COMPÉTENCES AVANT LE FORMULAIRE
        st.markdown("##### 🎯 Gestion des Compétences Métallurgie")
        
        # Initialiser les compétences en session
        if 'competences_form' not in st.session_state:
            st.session_state.competences_form = employe_data.get('competences', []) if employe_data else []
        
        # Interface d'ajout de compétences
        col_comp1, col_comp2, col_comp3, col_comp4 = st.columns([3, 2, 1, 1])
        with col_comp1:
            nouvelle_comp = st.selectbox("Ajouter compétence:", [""] + COMPETENCES_DISPONIBLES, key="new_comp_select")
        with col_comp2:
            niveau_comp = st.selectbox("Niveau:", NIVEAUX_COMPETENCE, key="new_comp_level")
        with col_comp3:
            certifie_comp = st.checkbox("Certifié", key="new_comp_certified")
        with col_comp4:
            if st.button("➕ Ajouter", key="add_comp_btn"):
                if nouvelle_comp:
                    existing = next((comp for comp in st.session_state.competences_form if comp['nom'] == nouvelle_comp), None)
                    if not existing:
                        st.session_state.competences_form.append({
                            'nom': nouvelle_comp,
                            'niveau': niveau_comp,
                            'certifie': certifie_comp
                        })
                        st.rerun()
                    else:
                        st.warning(f"La compétence '{nouvelle_comp}' existe déjà.")
        
        # Afficher les compétences actuelles
        if st.session_state.competences_form:
            st.markdown("**Compétences actuelles:**")
            for i, comp in enumerate(st.session_state.competences_form):
                col_c1, col_c2, col_c3, col_c4 = st.columns([3, 2, 1, 1])
                with col_c1:
                    st.text(comp['nom'])
                with col_c2:
                    st.text(comp['niveau'])
                with col_c3:
                    st.text("✅" if comp['certifie'] else "❌")
                with col_c4:
                    if st.button("🗑️", key=f"del_comp_{i}"):
                        st.session_state.competences_form.pop(i)
                        st.rerun()
        
        st.markdown("---")
        
        # FORMULAIRE PRINCIPAL
        with st.form("emp_form", clear_on_submit=False):
            # Informations personnelles
            st.markdown("##### 👤 Informations Personnelles")
            col1, col2 = st.columns(2)
            
            with col1:
                prenom = st.text_input("Prénom *", value=employe_data.get('prenom', '') if employe_data else "")
                email = st.text_input("Email *", value=employe_data.get('email', '') if employe_data else "", 
                                    help="Format: prenom.nom@dg-inc.qc.ca")
                telephone = st.text_input("Téléphone", value=employe_data.get('telephone', '450-372-9630') if employe_data else "450-372-9630")
            
            with col2:
                nom = st.text_input("Nom *", value=employe_data.get('nom', '') if employe_data else "")
                photo_url = st.text_input("Photo URL", value=employe_data.get('photo_url', '') if employe_data else "")
            
            # Informations professionnelles
            st.markdown("##### 💼 Informations Professionnelles")
            col3, col4 = st.columns(2)
            
            with col3:
                poste = st.text_input("Poste *", value=employe_data.get('poste', '') if employe_data else "")
                departement = st.selectbox(
                    "Département *",
                    DEPARTEMENTS,
                    index=DEPARTEMENTS.index(employe_data.get('departement')) if employe_data and employe_data.get('departement') in DEPARTEMENTS else 0
                )
                statut = st.selectbox(
                    "Statut *",
                    STATUTS_EMPLOYE,
                    index=STATUTS_EMPLOYE.index(employe_data.get('statut')) if employe_data and employe_data.get('statut') in STATUTS_EMPLOYE else 0
                )
                type_contrat = st.selectbox(
                    "Type de contrat *",
                    TYPES_CONTRAT,
                    index=TYPES_CONTRAT.index(employe_data.get('type_contrat')) if employe_data and employe_data.get('type_contrat') in TYPES_CONTRAT else 0
                )
            
            with col4:
                date_embauche = st.date_input(
                    "Date d'embauche *",
                    value=datetime.strptime(employe_data.get('date_embauche'), '%Y-%m-%d').date() if employe_data and employe_data.get('date_embauche') else datetime.now().date()
                )
                salaire = st.number_input(
                    "Salaire annuel (CAD) *",
                    min_value=30000,
                    max_value=150000,
                    value=employe_data.get('salaire', 45000) if employe_data else 45000,
                    step=1000,
                    help="Salaire en dollars canadiens"
                )
                
                # Manager - Martin Beauregard par défaut pour production
                managers_options = [("", "Autonome")] + [(emp['id'], f"{emp.get('prenom', '')} {emp.get('nom', '')}") for emp in emp_manager.get_managers()]
                current_manager_id = employe_data.get('manager_id') if employe_data else (11 if departement in ['PRODUCTION', 'USINAGE', 'QUALITÉ'] else "")
                manager_id = st.selectbox(
                    "Manager",
                    options=[mid for mid, _ in managers_options],
                    format_func=lambda mid: next((name for id_m, name in managers_options if id_m == mid), "Autonome"),
                    index=next((i for i, (mid, _) in enumerate(managers_options) if mid == current_manager_id), 0)
                )
                
                charge_travail = st.slider(
                    "Charge de travail (%)",
                    0, 100,
                    value=employe_data.get('charge_travail', 85) if employe_data else 85
                )
            
            # Compétences dans le formulaire (lecture seule)
            st.markdown("##### 📋 Compétences sélectionnées")
            if st.session_state.competences_form:
                comp_text = ", ".join([f"{comp['nom']} ({comp['niveau']})" for comp in st.session_state.competences_form])
                st.text_area("Compétences:", value=comp_text, disabled=True)
            else:
                st.info("Aucune compétence ajoutée. Utilisez la section ci-dessus.")
            
            # Notes
            notes = st.text_area("Notes", value=employe_data.get('notes', '') if employe_data else "")
            
            st.caption("* Champs obligatoires - Sauvegarde en SQLite")
            
            # Boutons du formulaire
            col_submit, col_cancel = st.columns(2)
            with col_submit:
                submitted = st.form_submit_button("💾 Enregistrer SQLite", use_container_width=True)
            with col_cancel:
                cancelled = st.form_submit_button("❌ Annuler", use_container_width=True)
            
            # TRAITEMENT DU FORMULAIRE
            if submitted:
                if not prenom or not nom or not email or not poste:
                    st.error("Les champs marqués * sont obligatoires.")
                elif '@' not in email:
                    st.error("Format d'email invalide.")
                else:
                    new_employe_data = {
                        'prenom': prenom,
                        'nom': nom,
                        'email': email,
                        'telephone': telephone,
                        'poste': poste,
                        'departement': departement,
                        'statut': statut,
                        'type_contrat': type_contrat,
                        'date_embauche': date_embauche.strftime('%Y-%m-%d'),
                        'salaire': salaire,
                        'manager_id': manager_id if manager_id else None,
                        'charge_travail': charge_travail,
                        'competences': st.session_state.competences_form,
                        'projets_assignes': employe_data.get('projets_assignes', []) if employe_data else [],
                        'notes': notes,
                        'photo_url': photo_url
                    }
                    
                    try:
                        if employe_data:  # Modification
                            success = emp_manager.modifier_employe(employe_data['id'], new_employe_data)
                            if success:
                                st.success(f"✅ Employé {prenom} {nom} mis à jour en SQLite !")
                            else:
                                st.error("❌ Erreur modification SQLite.")
                        else:  # Création
                            new_id = emp_manager.ajouter_employe(new_employe_data)
                            if new_id:
                                st.success(f"✅ Nouvel employé {prenom} {nom} ajouté en SQLite (ID: {new_id}) !")
                            else:
                                st.error("❌ Erreur création SQLite.")
                        
                        # Nettoyage
                        if 'competences_form' in st.session_state:
                            del st.session_state.competences_form
                        st.session_state.emp_action = None
                        st.session_state.emp_selected_id = None
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Erreur lors de la sauvegarde SQLite : {str(e)}")
            
            if cancelled:
                # Nettoyage lors de l'annulation
                if 'competences_form' in st.session_state:
                    del st.session_state.competences_form
                st.session_state.emp_action = None
                st.session_state.emp_selected_id = None
                st.rerun()

def render_employe_details(emp_manager, projet_manager, employe_data):
    """Détails employé - Compatible SQLite"""
    if not employe_data:
        st.error("Employé non trouvé en SQLite.")
        return
    
    st.subheader(f"👤 Profil: {employe_data.get('prenom')} {employe_data.get('nom')} (SQLite)")
    
    # Informations principales
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"""
        <div class='info-card'>
            <h4>📋 Informations Personnelles</h4>
            <p><strong>Email:</strong> {employe_data.get('email', 'N/A')}</p>
            <p><strong>Téléphone:</strong> {employe_data.get('telephone', 'N/A')}</p>
            <p><strong>Poste:</strong> {employe_data.get('poste', 'N/A')}</p>
            <p><strong>Département:</strong> {employe_data.get('departement', 'N/A')}</p>
            <p><strong>Statut:</strong> {employe_data.get('statut', 'N/A')}</p>
            <p><strong>Type contrat:</strong> {employe_data.get('type_contrat', 'N/A')}</p>
            <p><strong>Date embauche:</strong> {employe_data.get('date_embauche', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='info-card'>
            <h4>💰 Informations Financières</h4>
            <p><strong>Salaire:</strong> {employe_data.get('salaire', 0):,}$ CAD/an</p>
            <p><strong>Charge travail:</strong> {employe_data.get('charge_travail', 0)}%</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Manager et hiérarchie
        manager = emp_manager.get_employe_by_id(employe_data.get('manager_id')) if employe_data.get('manager_id') else None
        manager_nom = f"{manager.get('prenom', '')} {manager.get('nom', '')}" if manager else "Autonome"
        
        subordinates = emp_manager.get_subordinates(employe_data['id'])
        
        st.markdown(f"""
        <div class='info-card'>
            <h4>👥 Hiérarchie</h4>
            <p><strong>Manager:</strong> {manager_nom}</p>
            <p><strong>Subordonnés:</strong> {len(subordinates)}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Compétences métallurgie
    st.markdown("---")
    st.markdown("##### 🎯 Compétences Métallurgie (SQLite)")
    competences = employe_data.get('competences', [])
    if competences:
        # Grouper par catégorie
        comp_soudage = [c for c in competences if 'soudage' in c.get('nom', '').lower() or 'mig' in c.get('nom', '').lower() or 'tig' in c.get('nom', '').lower()]
        comp_usinage = [c for c in competences if any(mot in c.get('nom', '').lower() for mot in ['découpe', 'pliage', 'scie', 'plasma', 'cnc'])]
        comp_securite = [c for c in competences if any(mot in c.get('nom', '').lower() for mot in ['cnesst', 'sécurité', 'loto'])]
        comp_langues = [c for c in competences if c.get('nom') in ['Français', 'Anglais', 'Espagnol']]
        comp_autres = [c for c in competences if c not in comp_soudage + comp_usinage + comp_securite + comp_langues]
        
        categories = [
            ("🔥 Soudage", comp_soudage),
            ("⚙️ Usinage", comp_usinage),
            ("🦺 Sécurité", comp_securite),
            ("🗣️ Langues", comp_langues),
            ("🔧 Autres", comp_autres)
        ]
        
        for cat_nom, cat_comps in categories:
            if cat_comps:
                st.markdown(f"**{cat_nom}**")
                comp_cols = st.columns(min(3, len(cat_comps)))
                for i, comp in enumerate(cat_comps):
                    col_idx = i % 3
                    with comp_cols[col_idx]:
                        certif_icon = "🏆" if comp.get('certifie') else "📚"
                        niveau_color = {
                            'DÉBUTANT': '#f39c12',
                            'INTERMÉDIAIRE': '#3498db', 
                            'AVANCÉ': '#2ecc71',
                            'EXPERT': '#9b59b6'
                        }.get(comp.get('niveau'), '#95a5a6')
                        
                        st.markdown(f"""
                        <div class='info-card' style='border-left: 4px solid {niveau_color}; margin-bottom: 0.5rem;'>
                            <h6 style='margin: 0 0 0.2rem 0;'>{certif_icon} {comp.get('nom', 'N/A')}</h6>
                            <p style='margin: 0; font-size: 0.9em;'>{comp.get('niveau', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.info("Aucune compétence renseignée.")
    
    # Projets assignés
    st.markdown("---")
    st.markdown("##### 🚀 Projets Assignés (SQLite)")
    projets_assignes = employe_data.get('projets_assignes', [])
    if projets_assignes and projet_manager and hasattr(projet_manager, 'projets'):
        for proj_id in projets_assignes:
            projet = next((p for p in projet_manager.projets if p.get('id') == proj_id), None)
            if projet:
                statut_color = {
                    'À FAIRE': '#f39c12',
                    'EN COURS': '#3498db',
                    'EN ATTENTE': '#e74c3c', 
                    'TERMINÉ': '#2ecc71',
                    'LIVRAISON': '#9b59b6'
                }.get(projet.get('statut'), '#95a5a6')
                
                st.markdown(f"""
                <div class='info-card' style='border-left: 4px solid {statut_color}; margin-bottom: 0.5rem;'>
                    <h6 style='margin: 0 0 0.2rem 0;'>#{projet.get('id')} - {projet.get('nom_projet', 'N/A')}</h6>
                    <p style='margin: 0; font-size: 0.9em;'>📊 {projet.get('statut', 'N/A')} • 💰 {projet.get('prix_estime', 0):,}$ CAD</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Aucun projet assigné.")
    
    # Notes
    if employe_data.get('notes'):
        st.markdown("---")
        st.markdown("##### 📝 Notes")
        st.markdown(f"<div class='info-card'><p>{employe_data.get('notes', '')}</p></div>", unsafe_allow_html=True)
    
    # Bouton retour
    if st.button("⬅️ Retour à la liste", key="back_to_emp_list"):
        st.session_state.emp_action = None
        st.rerun()

# Interface principale pour la page employés
def show_employees_page():
    """Page principale employés - Compatible SQLite"""
    st.markdown("## 👥 Gestion des Employés - DG Inc. (SQLite)")
    
    # Vérifier si le gestionnaire employés SQLite existe
    if 'gestionnaire_employes' not in st.session_state:
        st.error("❌ Gestionnaire employés non initialisé.")
        return
    
    emp_manager = st.session_state.gestionnaire_employes
    projet_manager = st.session_state.get('gestionnaire', None)
    
    # Onglets
    tab1, tab2 = st.tabs(["📋 Liste des Employés", "📊 Dashboard RH"])
    
    with tab1:
        render_employes_liste_tab(emp_manager, projet_manager)
    
    with tab2:
        render_employes_dashboard_tab(emp_manager, projet_manager)
    
    # Gestion des actions
    if st.session_state.get('emp_action') == "create_employe":
        render_employe_form(emp_manager)
    elif st.session_state.get('emp_action') == "edit_employe" and st.session_state.get('emp_selected_id'):
        employe_data = emp_manager.get_employe_by_id(st.session_state.emp_selected_id)
        render_employe_form(emp_manager, employe_data)
    elif st.session_state.get('emp_action') == "view_employe_details" and st.session_state.get('emp_selected_id'):
        employe_data = emp_manager.get_employe_by_id(st.session_state.emp_selected_id)
        render_employe_details(emp_manager, projet_manager, employe_data)
