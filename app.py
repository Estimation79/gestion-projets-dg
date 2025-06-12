# --- START OF FILE app.py ---

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import calendar
import io
import json
import os
import re
import random
from math import gcd
from fractions import Fraction

# Importations pour le CRM (avec toutes les fonctions décommentées)
from crm import (
    GestionnaireCRM,
    render_crm_contacts_tab,
    render_crm_entreprises_tab,
    render_crm_interactions_tab,
    render_crm_contact_form,
    render_crm_entreprise_form,
    render_crm_contact_details,
    render_crm_entreprise_details,
    render_crm_interaction_form,
    render_crm_interaction_details
)

# Importations pour les Employés
from employees import (
    GestionnaireEmployes,
    render_employes_liste_tab,
    render_employes_dashboard_tab,
    render_employe_form,
    render_employe_details
)

# Configuration de la page
st.set_page_config(
    page_title="🚀 ERP Production DG Inc.",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- NOUVEAUX POSTES DE TRAVAIL DG INC. ---
WORK_CENTERS_DG_INC = [
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

# --- GESTIONNAIRE DES POSTES DE TRAVAIL ---
class GestionnairePostes:
    def __init__(self):
        self.postes = WORK_CENTERS_DG_INC
        self.gammes_types = self.initialiser_gammes_types()
    
    def initialiser_gammes_types(self):
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
    
    def get_poste_by_nom(self, nom_poste):
        return next((p for p in self.postes if p["nom"] == nom_poste), None)
    
    def get_employes_competents(self, poste_nom, gestionnaire_employes):
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
    
    def generer_gamme_fabrication(self, type_produit, complexite, gestionnaire_employes=None):
        """Génère une gamme de fabrication pour un type de produit donné"""
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
    
    def get_statistiques_postes(self):
        """Retourne les statistiques des postes de travail"""
        stats = {
            "total_postes": len(self.postes),
            "postes_cnc": len([p for p in self.postes if p["categorie"] == "CNC"]),
            "postes_robotises": len([p for p in self.postes if p["categorie"] == "ROBOT"]),
            "postes_manuels": len([p for p in self.postes if p["categorie"] == "MANUEL"]),
            "par_departement": {}
        }
        
        # Statistiques par département
        for poste in self.postes:
            dept = poste["departement"]
            stats["par_departement"][dept] = stats["par_departement"].get(dept, 0) + 1
        
        return stats
    
    def calculer_charge_poste(self, nom_poste, projets_actifs):
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

def integrer_postes_dans_projets(gestionnaire_projets, gestionnaire_postes):
    """Intègre les postes de travail dans les projets existants"""
    for projet in gestionnaire_projets.projets:
        # Ajouter le champ poste_travail aux opérations existantes
        for operation in projet.get("operations", []):
            if "poste_travail" not in operation:
                operation["poste_travail"] = "À déterminer"
                operation["employe_assigne"] = None
                operation["machine_utilisee"] = None
    
    gestionnaire_projets.sauvegarder_projets()
    return gestionnaire_projets

def generer_rapport_capacite_production():
    """Génère un rapport de capacité de production"""
    postes = WORK_CENTERS_DG_INC
    
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

# --- Fonctions Utilitaires de Mesure (intégrées depuis inventory_app.py) ---
UNITES_MESURE = ["IMPÉRIAL", "MÉTRIQUE"]
TYPES_PRODUITS_INVENTAIRE = ["BOIS", "MÉTAL", "QUINCAILLERIE", "OUTILLAGE", "MATÉRIAUX", "ACCESSOIRES", "AUTRE"]
STATUTS_STOCK_INVENTAIRE = ["DISPONIBLE", "FAIBLE", "CRITIQUE", "EN COMMANDE", "ÉPUISÉ", "INDÉTERMINÉ"]

def convertir_pieds_pouces_fractions_en_valeur_decimale(mesure_imperiale_str_input):
    try:
        mesure_str_cleaned = str(mesure_imperiale_str_input).strip().lower()
        mesure_str_cleaned = mesure_str_cleaned.replace('"', '"').replace("''", "'")
        mesure_str_cleaned = mesure_str_cleaned.replace('ft', "'").replace('pieds', "'").replace('pied', "'")
        mesure_str_cleaned = mesure_str_cleaned.replace('in', '"').replace('pouces', '"').replace('pouce', '"')
        if mesure_str_cleaned == "0":
            return 0.0
        total_pieds_dec = 0.0
        pattern_general = re.compile(
            r"^\s*(?:(?P<feet>\d+(?:\.\d+)?)\s*(?:'|\sft|\spieds?)?)?"
            r"\s*(?:(?P<inches>\d+(?:\.\d+)?)\s*(?:\"|\sin|\spouces?)?)?"
            r"\s*(?:(?P<frac_num>\d+)\s*\/\s*(?P<frac_den>\d+)\s*(?:\"|\sin|\spouces?)?)?\s*$"
        )
        pattern_nombres_seulement = re.compile(
            r"^\s*(?P<num1>\d+(?:\.\d+)?)"
            r"(?:\s+(?P<num2>\d+(?:\.\d+)?)"
            r"(?:\s+(?P<frac_num2>\d+)\s*\/\s*(?P<frac_den2>\d+))?"
            r")?"
            r"(?:\s+(?P<frac_num1>\d+)\s*\/\s*(?P<frac_den1>\d+))?"
            r"\s*$"
        )
        match = pattern_general.match(mesure_str_cleaned)
        pieds_val, pouces_val, fraction_dec = 0.0, 0.0, 0.0
        if match and (match.group('feet') or match.group('inches') or match.group('frac_num')):
            if match.group('feet'):
                pieds_val = float(match.group('feet'))
            if match.group('inches'):
                pouces_val = float(match.group('inches'))
            if match.group('frac_num') and match.group('frac_den'):
                num, den = int(match.group('frac_num')), int(match.group('frac_den'))
                if den == 0:
                    return 0.0
                fraction_dec = num / den
        else:
            match_alt = pattern_nombres_seulement.match(mesure_str_cleaned)
            if match_alt:
                pieds_val = float(match_alt.group('num1'))
                if match_alt.group('num2'):
                    pouces_val = float(match_alt.group('num2'))
                    if match_alt.group('frac_num2') and match_alt.group('frac_den2'):
                        num, den = int(match_alt.group('frac_num2')), int(match_alt.group('frac_den2'))
                        if den == 0:
                            return 0.0
                        fraction_dec = num / den
                elif match_alt.group('frac_num1') and match_alt.group('frac_den1'):
                    num, den = int(match_alt.group('frac_num1')), int(match_alt.group('frac_den1'))
                    if den == 0:
                        return 0.0
                    pouces_val = num / den
            elif "/" in mesure_str_cleaned:
                try:
                    pouces_val = float(Fraction(mesure_str_cleaned))
                except ValueError:
                    return 0.0
            elif mesure_str_cleaned.replace('.', '', 1).isdigit():
                try:
                    pouces_val = float(mesure_str_cleaned)
                except ValueError:
                    return 0.0
            else:
                return 0.0
        total_pieds_dec = pieds_val + (pouces_val / 12.0) + (fraction_dec / 12.0)
        return total_pieds_dec
    except Exception:
        return 0.0

def convertir_en_pieds_pouces_fractions(valeur_decimale_pieds_input):
    try:
        valeur_pieds_dec = float(valeur_decimale_pieds_input)
        if valeur_pieds_dec < 0:
            valeur_pieds_dec = 0
        pieds_entiers = int(valeur_pieds_dec)
        pouces_decimaux_restants_total = (valeur_pieds_dec - pieds_entiers) * 12.0
        pouces_entiers = int(pouces_decimaux_restants_total)
        fraction_decimale_de_pouce = pouces_decimaux_restants_total - pouces_entiers
        fraction_denominateur = 8
        fraction_numerateur_arrondi = round(fraction_decimale_de_pouce * fraction_denominateur)
        fraction_display_str = ""
        if fraction_numerateur_arrondi > 0:
            if fraction_numerateur_arrondi == fraction_denominateur:
                pouces_entiers += 1
            else:
                common_divisor = gcd(fraction_numerateur_arrondi, fraction_denominateur)
                num_simplifie, den_simplifie = fraction_numerateur_arrondi // common_divisor, fraction_denominateur // common_divisor
                fraction_display_str = f" {num_simplifie}/{den_simplifie}"
        if pouces_entiers >= 12:
            pieds_entiers += pouces_entiers // 12
            pouces_entiers %= 12
        if pieds_entiers == 0 and pouces_entiers == 0 and not fraction_display_str:
            return "0' 0\""
        return f"{pieds_entiers}' {pouces_entiers}{fraction_display_str}\""
    except Exception:
        return "0' 0\""

def valider_mesure_saisie(mesure_saisie_str):
    mesure_nettoyee = str(mesure_saisie_str).strip()
    if not mesure_nettoyee:
        return True, "0' 0\""
    try:
        valeur_pieds_dec = convertir_pieds_pouces_fractions_en_valeur_decimale(mesure_nettoyee)
        entree_est_zero_explicite = mesure_nettoyee in ["0", "0'", "0\"", "0.0", "0.0'"]
        if valeur_pieds_dec > 0.000001 or entree_est_zero_explicite:
            format_standardise = convertir_en_pieds_pouces_fractions(valeur_pieds_dec)
            return True, format_standardise
        else:
            return False, f"Format non reconnu ou invalide: '{mesure_nettoyee}'"
    except Exception as e_valid:
        return False, f"Erreur de validation: {e_valid}"

def convertir_imperial_vers_metrique(mesure_imperiale_str_conv):
    try:
        valeur_pieds_decimaux_conv = convertir_pieds_pouces_fractions_en_valeur_decimale(mesure_imperiale_str_conv)
        metres_val = valeur_pieds_decimaux_conv * 0.3048
        return {"valeur": round(metres_val, 3), "unite": "m"}
    except Exception:
        return {"valeur": 0.0, "unite": "m"}

def mettre_a_jour_statut_stock(produit_dict_stat):
    if not isinstance(produit_dict_stat, dict):
        return
    try:
        qty_act_dec_stat = convertir_pieds_pouces_fractions_en_valeur_decimale(produit_dict_stat.get('quantite', "0' 0\""))
        lim_min_dec_stat = convertir_pieds_pouces_fractions_en_valeur_decimale(produit_dict_stat.get('limite_minimale', "0' 0\""))
        qty_res_dec_stat = convertir_pieds_pouces_fractions_en_valeur_decimale(produit_dict_stat.get('quantite_reservee', "0' 0\""))
        stock_disp_dec_stat = qty_act_dec_stat - qty_res_dec_stat
        epsilon_stat = 0.0001
        if stock_disp_dec_stat <= epsilon_stat:
            produit_dict_stat['statut'] = "ÉPUISÉ"
        elif lim_min_dec_stat > epsilon_stat and stock_disp_dec_stat <= lim_min_dec_stat + epsilon_stat:
            produit_dict_stat['statut'] = "CRITIQUE"
        elif lim_min_dec_stat > epsilon_stat and stock_disp_dec_stat <= (lim_min_dec_stat * 1.5) + epsilon_stat:
            produit_dict_stat['statut'] = "FAIBLE"
        else:
            produit_dict_stat['statut'] = "DISPONIBLE"
    except Exception:
        produit_dict_stat['statut'] = "INDÉTERMINÉ"

def get_next_inventory_id(inventory_data):
    max_numeric_id = 0
    if inventory_data:
        for prod_id_str in inventory_data.keys():
            try:
                prod_id_int = int(prod_id_str)
                if prod_id_int > max_numeric_id:
                    max_numeric_id = prod_id_int
            except ValueError:
                continue
    return max_numeric_id + 1

# --- CSS et Interface ---
def load_css_file(css_file_path):
    try:
        with open(css_file_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
        return True
    except FileNotFoundError:
        st.warning(f"Fichier CSS '{css_file_path}' non trouvé. Utilisation du CSS intégré.")
        return False
    except Exception as e:
        st.error(f"Erreur CSS : {e}")
        return False

def apply_integrated_css():
    css_content = """
    /* Style CSS harmonisé pour ERP Production DG Inc. */
    :root {
        --primary-color: #3B82F6; --primary-color-light: #93C5FD; --primary-color-lighter: #DBEAFE;
        --primary-color-darker: #2563EB; --primary-color-darkest: #1D4ED8;
        --button-color: #1F2937; --button-color-light: #374151; --button-color-lighter: #4B5563;
        --button-color-dark: #111827; --button-color-darkest: #030712;
        --background-color: #FAFBFF; --secondary-background-color: #F0F8FF; --card-background: #FFFFFF;
        --content-background: #FFFFFF; --text-color: #1F2937; --text-color-light: #6B7280; --text-color-muted: #9CA3AF;
        --border-color: #E5E7EB; --border-color-light: #F3F4F6; --border-color-blue: #DBEAFE;
        --border-radius-sm: 0.375rem; --border-radius-md: 0.5rem; --border-radius-lg: 0.75rem;
        --font-family: 'Inter', sans-serif; --box-shadow-sm: 0 1px 3px 0 rgb(0 0 0 / 0.05);
        --box-shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        --box-shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -2px rgb(0 0 0 / 0.1);
        --box-shadow-blue: 0 4px 12px rgba(59, 130, 246, 0.15); --box-shadow-black: 0 4px 12px rgba(31, 41, 55, 0.25);
        --animation-speed: 0.3s; --primary-gradient: linear-gradient(135deg, #3B82F6 0%, #1F2937 100%);
        --secondary-gradient: linear-gradient(135deg, #DBEAFE 0%, #FFFFFF 100%);
        --card-gradient: linear-gradient(135deg, #F5F8FF 0%, #FFFFFF 100%);
        --button-gradient: linear-gradient(145deg, rgba(255,255,255,0.4) 0%, #3B82F6 20%, #1F2937 80%, rgba(0,0,0,0.2) 100%);
        --button-gradient-hover: linear-gradient(145deg, rgba(255,255,255,0.5) 0%, #60A5FA 20%, #2563EB 80%, rgba(0,0,0,0.3) 100%);
        --button-gradient-active: linear-gradient(145deg, rgba(0,0,0,0.1) 0%, #2563EB 20%, #1D4ED8 80%, rgba(0,0,0,0.4) 100%);
    }
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    .stApp { font-family: var(--font-family) !important; background: var(--background-color) !important; color: var(--text-color) !important; min-height: 100vh; }
    body { font-family: var(--font-family) !important; color: var(--text-color); background-color: var(--background-color); line-height: 1.6; font-size: 16px; }
    .main .block-container h1, .main .block-container h2, .main .block-container h3, .main .block-container h4, .main .block-container h5, .main .block-container h6 {
        font-family: var(--font-family) !important; font-weight: 700 !important; color: var(--text-color) !important; margin-bottom: 0.8em; line-height: 1.3;
    }
    @keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
    @keyframes header-shine { 0% {left:-100%;} 50% {left:-100%;} 100% {left:100%;} }
    .main-title { background: var(--primary-gradient) !important; padding:25px 30px !important; border-radius:16px !important; color:white !important; text-align:center !important;
        margin-bottom:30px !important; box-shadow:var(--box-shadow-black) !important; animation:fadeIn 0.8s ease-out !important;
        border:1px solid rgba(255,255,255,0.2) !important; position:relative !important; overflow:hidden !important;
    }
    .main-title::before { content:""; position:absolute; top:0; left:-100%; width:100%; height:100%;
        background:linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%);
        animation:header-shine 4s infinite; z-index:1;
    }
    .main-title h1 { margin:0 !important; font-size:2.2rem !important; font-weight:700 !important; color:white !important;
        text-shadow:0 2px 4px rgba(0,0,0,0.6), 0 1px 2px rgba(0,0,0,0.4), 0 0 10px rgba(0,0,0,0.3) !important;
        position:relative !important; z-index:2 !important;
    }
    .project-header { background: linear-gradient(145deg, rgba(255,255,255,0.8) 0%, #DBEAFE 25%, #93C5FD 75%, rgba(59,130,246,0.3) 100%) !important;
        padding:22px 25px !important; border-radius:14px !important; margin-bottom:25px !important;
        box-shadow:0 6px 20px rgba(59,130,246,0.2), inset 0 2px 0 rgba(255,255,255,0.6), inset 0 -1px 0 rgba(0,0,0,0.1), 0 0 20px rgba(59,130,246,0.1) !important;
        border:1px solid rgba(59,130,246,0.3) !important; position:relative !important; overflow:hidden !important;
    }
    .project-header::before { content:""; position:absolute; top:0; left:-100%; width:100%; height:100%;
        background:linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.4) 50%, transparent 100%);
        animation:header-shine 6s infinite; z-index:1;
    }
    .project-header h2 { margin:0 !important; color:#1E40AF !important; font-size:1.6rem !important; display:flex !important;
        align-items:center !important; font-weight:700 !important; text-shadow:0 1px 2px rgba(255,255,255,0.8) !important;
        position:relative !important; z-index:2 !important;
    }
    .project-header h2::before { content:"🏭 " !important; margin-right:12px !important; font-size:1.4rem !important;
        filter:drop-shadow(0 1px 2px rgba(0,0,0,0.1)) !important;
    }
    .stButton > button { background:var(--button-gradient) !important; color:white !important; border:none !important;
        border-radius:var(--border-radius-md) !important; padding:0.6rem 1.2rem !important; font-weight:600 !important;
        transition:all var(--animation-speed) ease !important; box-shadow:0 4px 8px rgba(59,130,246,0.25),
        inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -1px 0 rgba(0,0,0,0.1) !important; width:100% !important;
        text-align:center !important; display:inline-flex !important; align-items:center !important;
        justify-content:center !important; position:relative !important; overflow:hidden !important;
    }
    .stButton > button::before { content:""; position:absolute; top:0; left:-100%; width:100%; height:100%;
        background:linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.4) 50%, transparent 100%);
        transition:left 0.6s ease; z-index:1;
    }
    .stButton > button:hover::before { left:100%; }
    .stButton > button:hover { background:var(--button-gradient-hover) !important; transform:translateY(-3px) !important;
        box-shadow:0 8px 16px rgba(59,130,246,0.35), inset 0 2px 0 rgba(255,255,255,0.4),
        inset 0 -2px 0 rgba(0,0,0,0.15), 0 0 20px rgba(59,130,246,0.2) !important;
    }
    .stButton > button:active { background:var(--button-gradient-active) !important; transform:translateY(-1px) !important;
        box-shadow:0 2px 4px rgba(59,130,246,0.3), inset 0 -1px 0 rgba(255,255,255,0.2),
        inset 0 1px 2px rgba(0,0,0,0.2) !important;
    }
    .stButton > button:has(span:contains("🤖")) { background: linear-gradient(145deg, rgba(255,255,255,0.4) 0%, #8b5cf6 20%, #7c3aed 80%, rgba(0,0,0,0.2) 100%) !important; }
    .stButton > button:has(span:contains("⚙️")) { background: linear-gradient(145deg, rgba(255,255,255,0.4) 0%, #f59e0b 20%, #d97706 80%, rgba(0,0,0,0.2) 100%) !important; }
    .stButton > button:has(span:contains("🏭")) { background: linear-gradient(145deg, rgba(255,255,255,0.4) 0%, #10b981 20%, #059669 80%, rgba(0,0,0,0.2) 100%) !important; }
    section[data-testid="stSidebar"] { background: var(--card-gradient) !important; border-right:1px solid var(--border-color-blue) !important; padding:1.5rem !important;
        box-shadow:2px 0 10px rgba(59,130,246,0.08) !important;
    }
    section[data-testid="stSidebar"] * { color:var(--text-color) !important; }
    section[data-testid="stSidebar"] h3 { color:var(--primary-color-darker) !important; }
    section[data-testid="stSidebar"] .stMetric > div > div { color:var(--text-color-light) !important; }
    section[data-testid="stSidebar"] .stMetric > div:nth-child(2) > div { color:var(--primary-color-darker) !important; font-size: 1.5rem !important; }
    section[data-testid="stSidebar"] .stRadio > label p { color: var(--text-color) !important; }
    .info-card, .nav-container, .section-card { background:var(--card-background) !important; padding:1.5rem !important; border-radius:var(--border-radius-lg) !important;
        margin-bottom:1.5rem !important; box-shadow:var(--box-shadow-md) !important; border:1px solid var(--border-color-light) !important; transition:all 0.3s ease !important;
    }
    .info-card:hover, .section-card:hover { transform:translateY(-4px) !important; box-shadow:var(--box-shadow-blue) !important; }
    .info-card h4, .section-card h4, .info-card h5, .section-card h5 { color:var(--primary-color-darker) !important; }
    .info-card p, .section-card p { color:var(--text-color) !important; }
    .info-card small, .section-card small { color:var(--text-color-light) !important; }
    div[data-testid="stMetric"] { background:var(--card-background) !important; padding:1.5rem !important;
        border-radius:var(--border-radius-lg) !important; box-shadow:var(--box-shadow-md) !important;
        border:1px solid var(--border-color-light) !important; transition:all 0.3s ease !important;
    }
    div[data-testid="stMetric"]:hover { transform:translateY(-4px) !important; box-shadow:var(--box-shadow-blue) !important; }
    div[data-testid="stMetric"] > div:first-child > div { font-weight:600 !important; color:var(--primary-color) !important; }
    div[data-testid="stMetric"] > div:nth-child(2) > div { color:var(--text-color) !important; font-size: 1.75rem; }
    .dataframe { background:var(--card-background) !important; border-radius:var(--border-radius-lg) !important;
        overflow:hidden !important; box-shadow:var(--box-shadow-md) !important; border:1px solid var(--border-color) !important;
    }
    .dataframe th { background:linear-gradient(135deg, var(--primary-color-lighter), var(--primary-color-light)) !important;
        color:var(--primary-color-darkest) !important; font-weight:600 !important; padding:1rem !important; border:none !important;
        border-bottom: 2px solid var(--primary-color) !important;
    }
    .dataframe td { padding:0.75rem 1rem !important; border-bottom:1px solid var(--border-color-light) !important;
        background:var(--card-background) !important; color:var(--text-color) !important;
    }
    .dataframe tr:hover td { background:var(--primary-color-lighter) !important; }
    div[data-testid="stTabs"] > div[data-baseweb="tab-list"] { gap:0.25rem !important; background:var(--secondary-background-color) !important;
        padding:0.5rem !important; border-radius:var(--border-radius-lg) !important; border-bottom: 1px solid var(--border-color-blue) !important; margin-bottom: -1px;
    }
    div[data-testid="stTabs"] > div[data-baseweb="tab-list"] > button[data-baseweb="tab"] { background:transparent !important; border-radius:var(--border-radius-md) var(--border-radius-md) 0 0 !important;
        border:1px solid transparent !important; border-bottom:none !important; padding:0.75rem 1.5rem !important; font-weight:500 !important; color:var(--text-color-light) !important;
        transition:all 0.3s ease !important; margin-bottom: -1px;
    }
    div[data-testid="stTabs"] > div[data-baseweb="tab-list"] > button[data-baseweb="tab"]:hover { color:var(--primary-color) !important; background:var(--primary-color-lighter) !important; }
    div[data-testid="stTabs"] > div[data-baseweb="tab-list"] > button[data-baseweb="tab"][aria-selected="true"] { background:var(--content-background) !important;
        color:var(--primary-color-darker) !important; border: 1px solid var(--border-color-blue) !important;
        border-bottom: 1px solid var(--content-background) !important; box-shadow:none !important;
    }
    div[data-testid="stTabs"] > div:not([data-baseweb="tab-list"]) { background:var(--content-background) !important; padding:1.5rem !important;
        border-radius:0 0 var(--border-radius-lg) var(--border-radius-lg) !important; border: 1px solid var(--border-color-blue) !important; color:var(--text-color) !important;
    }
    div[data-testid="stTabs"] > div:not([data-baseweb="tab-list"]) * { color:var(--text-color) !important; }
    div[data-testid="stTabs"] > div:not([data-baseweb="tab-list"]) h5 { color:var(--primary-color-darker) !important; }
    .kanban-container { display: flex; flex-direction: row; gap: 15px; padding: 15px; background-color: var(--secondary-background-color);
        border-radius: 12px; overflow-x: auto; overflow-y: hidden; min-height: 600px; margin-bottom: 20px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
    }
    .kanban-column { flex: 0 0 320px; width: 320px; padding: 1rem; border-radius: var(--border-radius-md); background: var(--background-color);
        height: 100%; display: flex; flex-direction: column; border: 1px solid var(--border-color-light);
    }
    .kanban-header { font-weight: 600; font-size: 1.1em; text-align: left; padding: 0.75rem; border-radius: var(--border-radius-sm);
        margin-bottom: 1rem; color: var(--primary-color-darker); background: var(--primary-color-lighter);
        border-bottom: 2px solid var(--primary-color); cursor: default;
    }
    .kanban-cards-zone { flex-grow: 1; overflow-y: auto; padding-right: 5px; }
    .kanban-card { background: var(--card-background); border-radius: 10px; padding: 15px; margin-bottom: 15px;
        box-shadow: var(--box-shadow-sm); border-left: 5px solid transparent; transition: all 0.3s ease; color: var(--text-color);
    }
    .kanban-card:hover { transform: translateY(-3px); box-shadow: var(--box-shadow-blue); }
    .kanban-card-title { font-weight: 600; margin-bottom: 5px; }
    .kanban-card-info { font-size: 0.8em; color: var(--text-color-muted); margin-bottom: 3px; }
    .kanban-drag-indicator { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background-color: var(--button-color);
        color: white; padding: 12px 20px; border-radius: var(--border-radius-lg); box-shadow: var(--box-shadow-black); z-index: 1000;
        animation: fadeIn 0.3s ease-out; font-weight: 500;
    }
    .stButton > button.drop-target-button { background: #D4EDDA !important; color: #155724 !important; border: 2px dashed #155724 !important;
        width: 100%; margin-bottom: 1rem; font-weight: 600 !important;
    }
    .stButton > button.drop-target-button:hover { background: #C3E6CB !important; transform: scale(1.02); }
    .calendar-grid-container { border: 1px solid var(--border-color-blue); border-radius: var(--border-radius-lg); overflow: hidden;
        background: var(--card-background); box-shadow: var(--box-shadow-md);
    }
    .calendar-week-header { display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; padding: 0.5rem 0;
        background: var(--primary-color-lighter); border-bottom: 1px solid var(--border-color-blue);
    }
    .calendar-week-header .day-name { font-weight: 600; color: var(--primary-color-darker); font-size: 0.9em; }
    .calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); grid-auto-rows: minmax(120px, auto); }
    .calendar-day-cell { border-right: 1px solid var(--border-color-light); border-bottom: 1px solid var(--border-color-light);
        padding: 0.3rem; position: relative; transition: background-color 0.2s ease; display: flex; flex-direction: column;
    }
    .calendar-day-cell:nth-child(7n) { border-right: none; }
    .calendar-day-cell.other-month { background-color: var(--secondary-background-color); }
    .calendar-day-cell.other-month .day-number { color: var(--text-color-muted); }
    .day-number { font-weight: 500; text-align: right; font-size: 0.85em; padding: 0.2rem 0.4rem; align-self: flex-end; }
    .calendar-day-cell.today .day-number { background-color: var(--primary-color); color: white !important; border-radius: 50%;
        width: 24px; height: 24px; line-height: 24px; text-align: center; font-weight: 700; margin-left: auto;
    }
    .calendar-events-container { flex-grow: 1; overflow-y: auto; max-height: 85px; scrollbar-width: thin;
        scrollbar-color: var(--primary-color-light) var(--border-color-light);
    }
    .calendar-events-container::-webkit-scrollbar { width: 5px; }
    .calendar-events-container::-webkit-scrollbar-track { background: transparent; }
    .calendar-events-container::-webkit-scrollbar-thumb { background-color: var(--primary-color-light); border-radius: 10px; }
    .calendar-event-item { font-size: 0.75em; padding: 3px 6px; border-radius: 4px; margin: 2px 0; color: white;
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; transition: opacity 0.2s;
    }
    .calendar-event-item:hover { opacity: 0.8; }
    .event-type-debut { background-color: #3b82f6; }
    .event-type-fin { background-color: #10b981; }
    .stAlert { background:var(--card-background) !important; backdrop-filter:blur(10px) !important;
        border-radius:var(--border-radius-lg) !important; border:1px solid var(--border-color) !important;
        box-shadow:var(--box-shadow-sm) !important; color:var(--text-color) !important;
    }
    .stAlert p { color:var(--text-color) !important; }
    .stAlert[data-testid="stNotificationSuccess"] { background-color: #E6FFFA !important; border-left: 5px solid #38A169 !important; }
    .stAlert[data-testid="stNotificationSuccess"] p { color: #2F855A !important; }
    @media (max-width:768px) {
        .main-title { padding:15px !important; margin-bottom:15px !important; }
        .main-title h1 { font-size:1.8rem !important; }
        .info-card, .nav-container, .section-card { padding:1rem !important; margin-bottom:1rem !important; }
        .project-header { padding:18px 20px !important; border-radius:10px !important; }
        .project-header h2 { font-size:1.4rem !important; }
        .main-title::before, .project-header::before { animation-duration:10s !important; }
        .main-title:hover, .project-header:hover { transform:translateY(-1px) !important; }
        .stButton > button { min-height:44px !important; font-size:16px !important; padding:0.8rem 1rem !important; }
        .stButton > button::before { display:none; }
        .stButton > button:hover { transform:translateY(-2px) !important; }
        .kanban-container { flex-direction: column; }
        .calendar-grid { grid-auto-rows: minmax(100px, auto); }
        .calendar-event-item { font-size: 0.7em; }
    }
    .stApp > div { animation:fadeIn 0.5s ease-out; }
    ::-webkit-scrollbar { width:8px; }
    ::-webkit-scrollbar-track { background:var(--border-color-light); border-radius:4px; }
    ::-webkit-scrollbar-thumb { background:var(--primary-color-light); border-radius:4px; }
    ::-webkit-scrollbar-thumb:hover { background:var(--primary-color); }
    /* Styles spécifiques pour les postes de travail */
    .work-center-card { 
        background: var(--card-background); 
        border-radius: var(--border-radius-lg); 
        padding: 1.2rem; 
        margin-bottom: 1rem; 
        box-shadow: var(--box-shadow-md); 
        border-left: 4px solid var(--primary-color); 
        transition: all 0.3s ease; 
    }
    .work-center-card:hover { 
        transform: translateY(-2px); 
        box-shadow: var(--box-shadow-blue); 
        border-left-color: var(--primary-color-darker); 
    }
    .work-center-header { 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        margin-bottom: 0.8rem; 
    }
    .work-center-title { 
        font-weight: 700; 
        font-size: 1.1rem; 
        color: var(--primary-color-darker); 
        margin: 0; 
    }
    .work-center-badge { 
        background: var(--primary-color-lighter); 
        color: var(--primary-color-darker); 
        padding: 0.2rem 0.6rem; 
        border-radius: var(--border-radius-sm); 
        font-size: 0.8rem; 
        font-weight: 600; 
    }
    .work-center-info { 
        display: grid; 
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); 
        gap: 0.8rem; 
        margin-top: 0.8rem; 
    }
    .work-center-stat { 
        text-align: center; 
        padding: 0.5rem; 
        background: var(--secondary-background-color); 
        border-radius: var(--border-radius-sm); 
    }
    .work-center-stat-value { 
        font-weight: 700; 
        font-size: 1.2rem; 
        color: var(--primary-color-darker); 
        margin-bottom: 0.2rem; 
    }
    .work-center-stat-label { 
        font-size: 0.8rem; 
        color: var(--text-color-muted); 
        margin: 0; 
    }
    """
    st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)

def apply_global_styles():
    css_loaded = load_css_file('style.css')
    if not css_loaded:
        apply_integrated_css()

# NOUVELLE FONCTION pour obtenir le chemin des données de l'app inventaire
def get_inventory_data_app_data_path():
    app_name = "GestionnaireInventaireAI"
    if os.name == 'nt':
        base_app_data = os.environ.get('APPDATA', os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming'))
        app_data = os.path.join(base_app_data, app_name)
    else:
        app_data = os.path.join(os.path.expanduser('~'), f'.{app_name.lower()}')

    if not os.path.exists(app_data):
        try:
            os.makedirs(app_data, exist_ok=True)
        except Exception as e:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            app_data = os.path.join(script_dir, f".{app_name.lower()}_data_streamlit_fallback")
            if not os.path.exists(app_data):
                os.makedirs(app_data, exist_ok=True)
            st.warning(f"Impossible de créer/accéder au dossier de données standard. Utilisation du dossier local: {app_data}. Erreur: {e}")
    return app_data

def load_inventory_data():
    app_data_dir_inventory = get_inventory_data_app_data_path()
    inventory_file = os.path.join(app_data_dir_inventory, 'inventaire_v2.json')

    if os.path.exists(inventory_file):
        try:
            with open(inventory_file, 'r', encoding='utf-8') as f:
                inventaire_content = json.load(f)
            return {str(k): v for k, v in inventaire_content.items()}
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier d'inventaire '{inventory_file}': {e}")
            return {}
    return {}

def save_inventory_data(inventory_data_to_save):
    app_data_dir_inventory = get_inventory_data_app_data_path()
    inventory_file = os.path.join(app_data_dir_inventory, 'inventaire_v2.json')
    try:
        with open(inventory_file, 'w', encoding='utf-8') as f:
            json.dump(inventory_data_to_save, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde du fichier d'inventaire '{inventory_file}': {e}")
        return False

# ----- Gestionnaire de Données (Projets) MODIFIÉ POUR IDS 10000+ -----
class GestionnaireProjetIA:
    def __init__(self):
        self.data_file = "projets_data.json"
        self.projets = []
        self.next_id = 10000  # MODIFIÉ : Commencer à 10000
        self.charger_projets()

    def charger_projets(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.projets = data.get('projets', [])
                    # MODIFIÉ : Calculer le prochain ID en tenant compte du minimum 10000
                    if self.projets:
                        max_id = max(p.get('id', 10000) for p in self.projets)
                        self.next_id = max(max_id + 1, 10000)
                    else:
                        self.next_id = 10000
            else:
                self.projets = self.get_demo_data()
                self.next_id = 10003  # Après les 3 projets de démo (10000, 10001, 10002)
        except Exception as e:
            st.error(f"Erreur chargement projets: {e}")
            self.projets = self.get_demo_data()
            self.next_id = 10003

    def sauvegarder_projets(self):
        try:
            data = {'projets': self.projets, 'next_id': self.next_id, 'last_update': datetime.now().isoformat()}
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            st.error(f"Erreur sauvegarde projets: {e}")

    def get_demo_data(self):
        """MODIFIÉ : Données de démonstration avec IDs à partir de 10000"""
        now_iso = datetime.now().isoformat()
        return [
            {
                'id': 10000,  # MODIFIÉ : ID commence à 10000
                'nom_projet': 'Châssis Automobile', 
                'client_entreprise_id': 101, 
                'client_nom_cache': 'AutoTech Corp.', 
                'statut': 'EN COURS', 
                'priorite': 'ÉLEVÉ', 
                'tache': 'PRODUCTION', 
                'date_soumis': '2024-01-15', 
                'date_prevu': '2024-03-15', 
                'bd_ft_estime': '120', 
                'prix_estime': '35000', 
                'description': 'Châssis soudé pour véhicule électrique', 
                'sous_taches': [
                    {'id': 1, 'nom': 'Programmation CNC', 'statut': 'TERMINÉ', 'date_debut': '2024-01-15', 'date_fin': '2024-01-20'}, 
                    {'id': 2, 'nom': 'Découpe laser', 'statut': 'EN COURS', 'date_debut': '2024-01-21', 'date_fin': '2024-02-05'}, 
                    {'id': 3, 'nom': 'Soudage robotisé', 'statut': 'À FAIRE', 'date_debut': '2024-02-06', 'date_fin': '2024-02-20'}
                ], 
                'materiaux': [
                    {'id': 1, 'code': 'ACR-001', 'designation': 'Acier haute résistance', 'quantite': 250, 'unite': 'kg', 'prix_unitaire': 8.5, 'fournisseur': 'Aciers DG'}, 
                    {'id': 2, 'code': 'SOD-001', 'designation': 'Fil de soudage GMAW', 'quantite': 15, 'unite': 'bobines', 'prix_unitaire': 125, 'fournisseur': 'Soudage Pro'}
                ], 
                'operations': [
                    {'id': 1, 'sequence': '10', 'description': 'Programmation Bureau', 'temps_estime': 2.5, 'ressource': 'Programmeur CNC', 'statut': 'TERMINÉ', 'poste_travail': 'Programmation Bureau'}, 
                    {'id': 2, 'sequence': '20', 'description': 'Découpe laser des tôles', 'temps_estime': 4.2, 'ressource': 'Opérateur laser', 'statut': 'EN COURS', 'poste_travail': 'Laser CNC'}, 
                    {'id': 3, 'sequence': '30', 'description': 'Soudage robotisé GMAW', 'temps_estime': 8.5, 'ressource': 'Programmeur robot', 'statut': 'À FAIRE', 'poste_travail': 'Robot ABB GMAW'}
                ], 
                'employes_assignes': [1, 2]
            },
            {
                'id': 10001,  # MODIFIÉ : ID 10001
                'nom_projet': 'Structure Industrielle', 
                'client_entreprise_id': 102, 
                'client_nom_cache': 'BâtiTech Inc.', 
                'statut': 'À FAIRE', 
                'priorite': 'MOYEN', 
                'tache': 'ESTIMATION', 
                'date_soumis': '2024-02-01', 
                'date_prevu': '2024-05-01', 
                'bd_ft_estime': '180', 
                'prix_estime': '58000', 
                'description': 'Charpente métallique pour entrepôt industriel', 
                'sous_taches': [
                    {'id': 1, 'nom': 'Étude structure', 'statut': 'À FAIRE', 'date_debut': '2024-02-15', 'date_fin': '2024-03-01'}, 
                    {'id': 2, 'nom': 'Découpe plasma', 'statut': 'À FAIRE', 'date_debut': '2024-03-02', 'date_fin': '2024-03-20'}, 
                    {'id': 3, 'nom': 'Assemblage lourd', 'statut': 'À FAIRE', 'date_debut': '2024-03-21', 'date_fin': '2024-04-15'}
                ], 
                'materiaux': [
                    {'id': 1, 'code': 'IPE-200', 'designation': 'Poutre IPE 200', 'quantite': 50, 'unite': 'ml', 'prix_unitaire': 45, 'fournisseur': 'Métal Québec'}, 
                    {'id': 2, 'code': 'HEA-160', 'designation': 'Poutre HEA 160', 'quantite': 30, 'unite': 'ml', 'prix_unitaire': 52, 'fournisseur': 'Métal Québec'}
                ], 
                'operations': [
                    {'id': 1, 'sequence': '10', 'description': 'Étude et programmation', 'temps_estime': 4.0, 'ressource': 'Ingénieur', 'statut': 'À FAIRE', 'poste_travail': 'Programmation Bureau'}, 
                    {'id': 2, 'sequence': '20', 'description': 'Découpe plasma CNC', 'temps_estime': 6.8, 'ressource': 'Opérateur plasma', 'statut': 'À FAIRE', 'poste_travail': 'Plasma CNC'}, 
                    {'id': 3, 'sequence': '30', 'description': 'Assemblage structure', 'temps_estime': 12.5, 'ressource': 'Équipe assemblage', 'statut': 'À FAIRE', 'poste_travail': 'Assemblage Lourd'}
                ], 
                'employes_assignes': [2, 3]
            },
            {
                'id': 10002,  # MODIFIÉ : ID 10002
                'nom_projet': 'Pièce Aéronautique', 
                'client_entreprise_id': 103, 
                'client_nom_cache': 'AeroSpace Ltd', 
                'statut': 'TERMINÉ', 
                'priorite': 'ÉLEVÉ', 
                'tache': 'LIVRAISON', 
                'date_soumis': '2023-10-01', 
                'date_prevu': '2024-01-31', 
                'bd_ft_estime': '95', 
                'prix_estime': '75000', 
                'description': 'Composant haute précision pour train d\'atterrissage', 
                'sous_taches': [
                    {'id': 1, 'nom': 'Usinage CNC', 'statut': 'TERMINÉ', 'date_debut': '2023-10-15', 'date_fin': '2023-11-15'}, 
                    {'id': 2, 'nom': 'Contrôle qualité', 'statut': 'TERMINÉ', 'date_debut': '2023-11-16', 'date_fin': '2023-11-30'}, 
                    {'id': 3, 'nom': 'Traitement surface', 'statut': 'TERMINÉ', 'date_debut': '2023-12-01', 'date_fin': '2023-12-15'}
                ], 
                'materiaux': [
                    {'id': 1, 'code': 'ALU-7075', 'designation': 'Aluminium 7075 T6', 'quantite': 25, 'unite': 'kg', 'prix_unitaire': 18.5, 'fournisseur': 'Alu Tech'}, 
                    {'id': 2, 'code': 'ANO-001', 'designation': 'Anodisation Type II', 'quantite': 1, 'unite': 'lot', 'prix_unitaire': 850, 'fournisseur': 'Surface Pro'}
                ], 
                'operations': [
                    {'id': 1, 'sequence': '10', 'description': 'Usinage centre CNC', 'temps_estime': 8.2, 'ressource': 'Usineur CNC', 'statut': 'TERMINÉ', 'poste_travail': 'Centre d\'usinage'}, 
                    {'id': 2, 'sequence': '20', 'description': 'Contrôle métrologique', 'temps_estime': 2.5, 'ressource': 'Contrôleur', 'statut': 'TERMINÉ', 'poste_travail': 'Contrôle métrologique'}, 
                    {'id': 3, 'sequence': '30', 'description': 'Anodisation', 'temps_estime': 2.0, 'ressource': 'Technicien surface', 'statut': 'TERMINÉ', 'poste_travail': 'Anodisation'}
                ], 
                'employes_assignes': [3, 4]
            }
        ]

    def ajouter_projet(self, projet_data):
        projet_data['id'] = self.next_id
        self.projets.append(projet_data)
        self.next_id += 1
        self.sauvegarder_projets()
        return projet_data['id']

    def modifier_projet(self, projet_id, projet_data_update):
        for i, p in enumerate(self.projets):
            if p['id'] == projet_id:
                self.projets[i].update(projet_data_update)
                self.sauvegarder_projets()
                return True
        return False

    def supprimer_projet(self, projet_id):
        self.projets = [p for p in self.projets if p['id'] != projet_id]
        self.sauvegarder_projets()

# NOUVELLE FONCTION : Migration des IDs des projets existants
def migrer_ids_projets():
    """Migre tous les projets vers des IDs commençant à 10000"""
    gestionnaire = st.session_state.gestionnaire
    
    # Trier les projets par ID pour maintenir l'ordre
    projets_tries = sorted(gestionnaire.projets, key=lambda x: x.get('id', 0))
    
    # Réassigner les IDs
    for i, projet in enumerate(projets_tries):
        nouveau_id = 10000 + i
        projet['id'] = nouveau_id
    
    # Mettre à jour le prochain ID
    gestionnaire.next_id = 10000 + len(gestionnaire.projets)
    gestionnaire.sauvegarder_projets()
    
    return len(projets_tries)

# --- Fonctions Utilitaires (Projets)-----
def format_currency(value):
    if value is None:
        return "$0.00"
    try:
        s_value = str(value).replace(' ', '').replace('€', '').replace('$', '')
        if ',' in s_value and ('.' not in s_value or s_value.find(',') > s_value.find('.')):
            s_value = s_value.replace('.', '').replace(',', '.')
        elif ',' in s_value and '.' in s_value and s_value.find('.') > s_value.find(','):
            s_value = s_value.replace(',', '')

        num_value = float(s_value)
        if num_value == 0:
            return "$0.00"
        return f"${num_value:,.2f}"
    except (ValueError, TypeError):
        if isinstance(value, (int, float)):
            return f"${value:,.2f}"
        return str(value) + " $ (Err)"

def get_project_statistics(gestionnaire):
    if not gestionnaire.projets:
        return {'total': 0, 'par_statut': {}, 'par_priorite': {}, 'ca_total': 0, 'projets_actifs': 0, 'taux_completion': 0}
    stats = {'total': len(gestionnaire.projets), 'par_statut': {}, 'par_priorite': {}, 'ca_total': 0, 'projets_actifs': 0}
    for p in gestionnaire.projets:
        statut = p.get('statut', 'N/A')
        stats['par_statut'][statut] = stats['par_statut'].get(statut, 0) + 1
        priorite = p.get('priorite', 'N/A')
        stats['par_priorite'][priorite] = stats['par_priorite'].get(priorite, 0) + 1
        try:
            prix = p.get('prix_estime', '0')
            s_prix = str(prix).replace(' ', '').replace('€', '').replace('$', '')
            if ',' in s_prix and ('.' not in s_prix or s_prix.find(',') > s_prix.find('.')):
                s_prix = s_prix.replace('.', '').replace(',', '.')
            elif ',' in s_prix and '.' in s_prix and s_prix.find('.') > s_prix.find(','):
                s_prix = s_prix.replace(',', '')
            prix_num = float(s_prix)
            stats['ca_total'] += prix_num
        except (ValueError, TypeError):
            pass
        if statut not in ['TERMINÉ', 'ANNULÉ', 'FERMÉ']:
            stats['projets_actifs'] += 1
    termines = stats['par_statut'].get('TERMINÉ', 0)
    stats['taux_completion'] = (termines / stats['total'] * 100) if stats['total'] > 0 else 0
    return stats

# ----- NOUVELLES PAGES POSTES DE TRAVAIL -----

def show_work_centers_page():
    """Page principale des postes de travail DG Inc."""
    st.markdown("## 🏭 Postes de Travail - DG Inc.")
    gestionnaire_postes = st.session_state.gestionnaire_postes
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    tab_overview, tab_details, tab_analytics = st.tabs([
        "📊 Vue d'ensemble", "🔍 Détails par poste", "📈 Analyses"
    ])
    
    with tab_overview:
        render_work_centers_overview(gestionnaire_postes)
    
    with tab_details:
        render_work_centers_details(gestionnaire_postes, gestionnaire_employes)
    
    with tab_analytics:
        render_work_centers_analytics(gestionnaire_postes)

def render_work_centers_overview(gestionnaire_postes):
    """Vue d'ensemble des postes de travail"""
    stats = gestionnaire_postes.get_statistiques_postes()
    
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
    
    # Répartition par département
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        if stats['par_departement']:
            fig_dept = px.pie(
                values=list(stats['par_departement'].values()),
                names=list(stats['par_departement'].keys()),
                title="📊 Répartition par Département",
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
        # Capacité par type de machine
        capacite_par_type = {}
        for poste in gestionnaire_postes.postes:
            type_machine = poste.get('type_machine', 'AUTRE')
            capacite_par_type[type_machine] = capacite_par_type.get(type_machine, 0) + poste.get('capacite_theorique', 0)
        
        if capacite_par_type:
            fig_cap = px.bar(
                x=list(capacite_par_type.keys()),
                y=list(capacite_par_type.values()),
                title="⚡ Capacité par Type de Machine (h/jour)",
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
    """Détails par poste de travail"""
    st.subheader("🔍 Détails des Postes de Travail")
    
    # Filtres
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        departements = list(set(p['departement'] for p in gestionnaire_postes.postes))
        dept_filter = st.selectbox("Département:", ["Tous"] + sorted(departements))
    
    with col_filter2:
        categories = list(set(p['categorie'] for p in gestionnaire_postes.postes))
        cat_filter = st.selectbox("Catégorie:", ["Toutes"] + sorted(categories))
    
    with col_filter3:
        search_term = st.text_input("🔍 Rechercher:", placeholder="Nom du poste...")
    
    # Application des filtres
    postes_filtres = gestionnaire_postes.postes
    
    if dept_filter != "Tous":
        postes_filtres = [p for p in postes_filtres if p['departement'] == dept_filter]
    
    if cat_filter != "Toutes":
        postes_filtres = [p for p in postes_filtres if p['categorie'] == cat_filter]
    
    if search_term:
        terme = search_term.lower()
        postes_filtres = [p for p in postes_filtres if terme in p['nom'].lower()]
    
    st.markdown(f"**{len(postes_filtres)} poste(s) trouvé(s)**")
    
    # Affichage des postes filtrés
    for poste in postes_filtres:
        with st.container():
            st.markdown(f"""
            <div class='work-center-card'>
                <div class='work-center-header'>
                    <div class='work-center-title'>{poste['nom']}</div>
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
    """Analyses avancées des postes de travail"""
    st.subheader("📈 Analyses de Performance")
    
    rapport = generer_rapport_capacite_production()
    
    # Métriques de capacité
    st.markdown("### ⚡ Capacités Théoriques")
    cap_col1, cap_col2, cap_col3, cap_col4 = st.columns(4)
    
    with cap_col1:
        st.metric("🏭 Production", f"{rapport['utilisation_theorique']['production']}h/j")
    with cap_col2:
        st.metric("⚙️ Usinage", f"{rapport['utilisation_theorique']['usinage']}h/j")
    with cap_col3:
        st.metric("✅ Qualité", f"{rapport['utilisation_theorique']['qualite']}h/j")
    with cap_col4:
        st.metric("📦 Logistique", f"{rapport['utilisation_theorique']['logistique']}h/j")
    
    st.markdown("---")
    
    # Analyse des coûts
    st.markdown("### 💰 Analyse des Coûts")
    cout_col1, cout_col2 = st.columns(2)
    
    with cout_col1:
        # Coût par catégorie
        cout_par_categorie = {}
        for poste in gestionnaire_postes.postes:
            cat = poste['categorie']
            cout = poste['cout_horaire'] * poste['capacite_theorique']
            cout_par_categorie[cat] = cout_par_categorie.get(cat, 0) + cout
        
        if cout_par_categorie:
            fig_cout = px.bar(
                x=list(cout_par_categorie.keys()),
                y=list(cout_par_categorie.values()),
                title="💰 Coût Journalier par Catégorie ($)",
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
        st.markdown("**💡 Recommandations d'Optimisation:**")
        recommendations = [
            "🤖 Maximiser l'utilisation des robots ABB (ROI élevé)",
            "⚡ Grouper les opérations CNC par type de matériau",
            "🔄 Implémenter des changements d'équipes optimisés",
            "📊 Former plus d'employés sur postes critiques",
            "⏰ Programmer maintenance préventive en heures creuses"
        ]
        
        for i, rec in enumerate(recommendations, 1):
            st.markdown(f"**{i}.** {rec}")
    
    # Simulation de charge
    st.markdown("---")
    st.markdown("### 📊 Simulation de Charge Hebdomadaire")
    
    if st.button("🚀 Lancer Simulation", use_container_width=True):
        with st.spinner("Calcul de la charge optimale..."):
            # Simulation de données de charge
            jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
            postes_critiques = ['Laser CNC', 'Robot ABB GMAW', 'Centre d\'usinage']
            
            data_simulation = []
            for jour in jours:
                for poste in postes_critiques:
                    charge = random.uniform(70, 95)
                    data_simulation.append({
                        'Jour': jour,
                        'Poste': poste,
                        'Charge (%)': charge
                    })
            
            df_sim = pd.DataFrame(data_simulation)
            
            fig_sim = px.bar(
                df_sim, x='Jour', y='Charge (%)', color='Poste',
                title="📊 Charge Hebdomadaire des Postes Critiques",
                barmode='group'
            )
            fig_sim.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                title_x=0.5
            )
            fig_sim.add_hline(y=90, line_dash="dash", line_color="red", 
                            annotation_text="Seuil critique (90%)")
            
            st.plotly_chart(fig_sim, use_container_width=True)
            
            # Résultats de simulation
            charge_moyenne = df_sim['Charge (%)'].mean()
            postes_surcharges = len(df_sim[df_sim['Charge (%)'] > 90])
            
            sim_col1, sim_col2, sim_col3 = st.columns(3)
            with sim_col1:
                st.metric("📊 Charge Moyenne", f"{charge_moyenne:.1f}%")
            with sim_col2:
                st.metric("⚠️ Instances Surchargées", postes_surcharges)
            with sim_col3:
                efficacite_sem = random.uniform(85, 92)
                st.metric("✅ Efficacité Semaine", f"{efficacite_sem:.1f}%")

def show_manufacturing_routes_page():
    """Page des gammes de fabrication"""
    st.markdown("## ⚙️ Gammes de Fabrication - DG Inc.")
    
    gestionnaire_postes = st.session_state.gestionnaire_postes
    gestionnaire_projets = st.session_state.gestionnaire
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    tab_generator, tab_templates, tab_optimization = st.tabs([
        "🔧 Générateur", "📋 Modèles", "🎯 Optimisation"
    ])
    
    with tab_generator:
        render_operations_manager(gestionnaire_postes, gestionnaire_employes)
    
    with tab_templates:
        render_gammes_templates(gestionnaire_postes)
    
    with tab_optimization:
        render_route_optimization(gestionnaire_postes, gestionnaire_projets)

def render_operations_manager(gestionnaire_postes, gestionnaire_employes):
    """Gestionnaire d'opérations avec vrais postes"""
    st.subheader("🔧 Générateur de Gammes de Fabrication")
    
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
        
        generate_btn = st.form_submit_button("🚀 Générer Gamme", use_container_width=True)
        
        if generate_btn:
            with st.spinner("Génération de la gamme optimisée..."):
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
                
                st.success(f"✅ Gamme générée avec {len(gamme)} opérations !")
    
    # Affichage de la gamme générée
    if st.session_state.get('gamme_generated'):
        st.markdown("---")
        st.markdown("### 📋 Gamme Générée")
        
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
        st.markdown("#### 📊 Détail des Opérations")
        
        data_gamme = []
        for op in gamme:
            poste_info = op.get('poste_info', {})
            data_gamme.append({
                'Séq.': op['sequence'],
                'Poste': op['poste'],
                'Description': op['description'],
                'Temps (h)': f"{op['temps_estime']:.1f}",
                'Coût/h': f"{poste_info.get('cout_horaire', 0)}$",
                'Total': f"{op['temps_estime'] * poste_info.get('cout_horaire', 0):.0f}$",
                'Employés Dispo.': ', '.join(op.get('employes_disponibles', ['Aucun'])[:2])
            })
        
        df_gamme = pd.DataFrame(data_gamme)
        st.dataframe(df_gamme, use_container_width=True)
        
        # Graphique de répartition du temps
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
                    title="⏱️ Répartition Temps par Département"
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
                    title="💰 Coût par Département ($)",
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
        if st.button("📋 Appliquer à un Projet", use_container_width=True):
            st.session_state.show_apply_gamme_to_project = True

def render_gammes_templates(gestionnaire_postes):
    """Templates de gammes prédéfinies"""
    st.subheader("📋 Modèles de Gammes Prédéfinis")
    
    for type_key, gamme_info in gestionnaire_postes.gammes_types.items():
        with st.expander(f"🔧 {gamme_info['nom']}", expanded=False):
            col_t1, col_t2 = st.columns(2)
            
            with col_t1:
                st.markdown(f"**Description:** {gamme_info['description']}")
                st.markdown(f"**Nombre d'opérations:** {len(gamme_info['operations'])}")
                
                temps_base_total = sum(op['temps_base'] for op in gamme_info['operations'])
                st.markdown(f"**Temps de base:** {temps_base_total:.1f}h")
                
                # Aperçu des opérations
                st.markdown("**Opérations principales:**")
                for i, op in enumerate(gamme_info['operations'][:5], 1):
                    st.markdown(f"  {i}. {op['poste']} - {op['description']}")
                if len(gamme_info['operations']) > 5:
                    st.markdown(f"  ... et {len(gamme_info['operations']) - 5} autres")
            
            with col_t2:
                # Répartition des postes utilisés
                postes_utilises = {}
                for op in gamme_info['operations']:
                    poste_obj = gestionnaire_postes.get_poste_by_nom(op['poste'])
                    if poste_obj:
                        dept = poste_obj['departement']
                        postes_utilises[dept] = postes_utilises.get(dept, 0) + 1
                
                if postes_utilises:
                    fig_template = px.bar(
                        x=list(postes_utilises.keys()),
                        y=list(postes_utilises.values()),
                        title=f"Postes par Département - {gamme_info['nom']}",
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
                
                if st.button(f"🚀 Appliquer Modèle {gamme_info['nom']}", key=f"apply_{type_key}"):
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
                    st.success(f"✅ Modèle {gamme_info['nom']} appliqué !")
                    st.rerun()

def render_route_optimization(gestionnaire_postes, gestionnaire_projets):
    """Optimisation des gammes et séquencement"""
    st.subheader("🎯 Optimisation des Gammes")
    
    # Sélection des projets actifs pour optimisation
    projets_actifs = [p for p in gestionnaire_projets.projets if p.get('statut') not in ['TERMINÉ', 'ANNULÉ']]
    
    if not projets_actifs:
        st.info("Aucun projet actif pour l'optimisation.")
        return
    
    st.markdown("### 📊 Analyse de Charge Actuelle")
    
    # Calcul de la charge par poste
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
            title="📊 Charge Actuelle par Poste (Top 10)",
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
        
        # Identification des goulots
        st.markdown("### 🚨 Goulots d'Étranglement Identifiés")
        
        goulots = []
        for poste_nom, charge_totale in charge_par_poste.items():
            poste_obj = gestionnaire_postes.get_poste_by_nom(poste_nom)
            if poste_obj:
                capacite_hebdo = poste_obj['capacite_theorique'] * 5  # 5 jours
                taux_charge = (charge_totale / capacite_hebdo) * 100 if capacite_hebdo > 0 else 0
                
                if taux_charge > 90:
                    goulots.append({
                        'poste': poste_nom,
                        'charge': charge_totale,
                        'capacite': capacite_hebdo,
                        'taux': taux_charge
                    })
        
        if goulots:
            for goulot in sorted(goulots, key=lambda x: x['taux'], reverse=True):
                st.error(f"⚠️ **{goulot['poste']}**: {goulot['taux']:.1f}% de charge "
                        f"({goulot['charge']:.1f}h / {goulot['capacite']:.1f}h)")
        else:
            st.success("✅ Aucun goulot d'étranglement critique détecté")
    
    # Simulation d'optimisation
    st.markdown("---")
    st.markdown("### 🔄 Optimisation Automatique")
    
    if st.button("🚀 Lancer Optimisation Globale", use_container_width=True):
        with st.spinner("Optimisation en cours..."):
            # Simulation d'optimisation
            import time
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Étapes d'optimisation simulées
            etapes = [
                "Analyse charge actuelle par poste...",
                "Identification des goulots d'étranglement...", 
                "Calcul des alternatives de routage...",
                "Optimisation utilisation robots ABB...",
                "Équilibrage des charges par département...",
                "Génération des recommandations..."
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
                
                # Simulation de résultats
                resultats_optim['temps_economise'] += random.uniform(2.5, 8.3)
                resultats_optim['cout_reduit'] += random.uniform(150, 450)
            
            # Résultats d'optimisation
            st.success("✅ Optimisation terminée !")
            
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("⏱️ Temps Économisé", f"{resultats_optim['temps_economise']:.1f}h")
            with col_r2:
                st.metric("💰 Coût Réduit", f"{resultats_optim['cout_reduit']:.0f}$ CAD")
            with col_r3:
                efficacite = random.uniform(12, 18)
                st.metric("📈 Efficacité", f"+{efficacite:.1f}%")
            
            # Recommandations détaillées
            st.markdown("### 💡 Recommandations d'Optimisation")
            recommandations = [
                "🤖 Programmer Robot ABB GMAW en priorité pour pièces répétitives",
                "⚡ Grouper les découpes laser par épaisseur de matériau",
                "🔄 Alterner soudage manuel/robot selon complexité géométrique",
                "📊 Former employés sur Plieuse CNC haute précision",
                "⏰ Décaler finition peinture sur équipe de soir"
            ]
            
            for recommandation in recommandations:
                st.markdown(f"- {recommandation}")

def show_capacity_analysis_page():
    """Page d'analyse de capacité de production"""
    st.markdown("## 📈 Analyse de Capacité - DG Inc.")
    
    gestionnaire_postes = st.session_state.gestionnaire_postes
    
    # Rapport de capacité en temps réel
    rapport = generer_rapport_capacite_production()
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🤖 Robots ABB", rapport['capacites']['postes_robotises'])
    with col2:
        st.metric("💻 Postes CNC", rapport['capacites']['postes_cnc'])
    with col3:
        st.metric("🔥 Postes Soudage", rapport['capacites']['postes_soudage'])
    with col4:
        st.metric("✨ Postes Finition", rapport['capacites']['postes_finition'])
    
    # Affichage détaillé
    render_capacity_analysis(gestionnaire_postes)

def render_capacity_analysis(gestionnaire_postes):
    """Analyse détaillée de la capacité"""
    st.markdown("### 🏭 Analyse Détaillée de la Capacité")
    
    # Analyse par département
    dept_analysis = {}
    for poste in gestionnaire_postes.postes:
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
        with st.expander(f"🏭 {dept} - {stats['postes']} postes", expanded=False):
            dept_col1, dept_col2, dept_col3, dept_col4 = st.columns(4)
            
            with dept_col1:
                st.metric("📊 Postes", stats['postes'])
            with dept_col2:
                st.metric("⚡ Capacité/jour", f"{stats['capacite_totale']}h")
            with dept_col3:
                st.metric("👥 Opérateurs", stats['operateurs_requis'])
            with dept_col4:
                st.metric("💰 Coût/jour", f"{stats['cout_total']:.0f}$")
            
            # Liste des postes du département
            postes_dept = [p for p in gestionnaire_postes.postes if p['departement'] == dept]
            
            data_dept = []
            for poste in postes_dept:
                utilisation_simulee = random.uniform(65, 95)
                data_dept.append({
                    'Poste': poste['nom'],
                    'Catégorie': poste['categorie'],
                    'Capacité (h/j)': poste['capacite_theorique'],
                    'Coût ($/h)': poste['cout_horaire'],
                    'Utilisation (%)': f"{utilisation_simulee:.1f}%"
                })
            
            if data_dept:
                df_dept = pd.DataFrame(data_dept)
                st.dataframe(df_dept, use_container_width=True)

# ----- FONCTIONS D'AFFICHAGE MODIFIÉES -----

TEXT_COLOR_CHARTS = 'var(--text-color)'

def show_dashboard():
    st.markdown("## 📊 Tableau de Bord ERP Production")
    gestionnaire = st.session_state.gestionnaire
    gestionnaire_employes = st.session_state.gestionnaire_employes
    gestionnaire_postes = st.session_state.gestionnaire_postes  # NOUVEAU
    
    stats = get_project_statistics(gestionnaire)
    emp_stats = gestionnaire_employes.get_statistiques_employes()
    postes_stats = gestionnaire_postes.get_statistiques_postes()  # NOUVEAU
    
    if stats['total'] == 0 and emp_stats.get('total', 0) == 0:
        st.markdown("<div class='info-card' style='text-align:center;padding:3rem;'><h3>🏭 Bienvenue dans l'ERP Production DG Inc. !</h3><p>Créez votre premier projet, explorez les postes de travail ou consultez les gammes de fabrication.</p></div>", unsafe_allow_html=True)
        return

    # Métriques Projets
    if stats['total'] > 0:
        st.markdown("### 🚀 Aperçu Projets")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("📊 Total Projets", stats['total'])
        with c2:
            st.metric("🚀 Projets Actifs", stats['projets_actifs'])
        with c3:
            st.metric("✅ Taux Completion", f"{stats['taux_completion']:.1f}%")
        with c4:
            st.metric("💰 CA Total", format_currency(stats['ca_total']))

    # NOUVEAU : Métriques postes de travail
    if postes_stats['total_postes'] > 0:
        st.markdown("### 🏭 Aperçu Production DG Inc.")
        prod_c1, prod_c2, prod_c3, prod_c4 = st.columns(4)
        with prod_c1:
            st.metric("🏭 Total Postes", postes_stats['total_postes'])
        with prod_c2:
            st.metric("🤖 Robots ABB", postes_stats['postes_robotises'])
        with prod_c3:
            st.metric("💻 Postes CNC", postes_stats['postes_cnc'])
        with prod_c4:
            efficacite_globale = random.uniform(82, 87)  # Simulation temps réel
            st.metric("⚡ Efficacité", f"{efficacite_globale:.1f}%")

    # Métriques RH
    if emp_stats.get('total', 0) > 0:
        st.markdown("### 👥 Aperçu Ressources Humaines")
        emp_c1, emp_c2, emp_c3, emp_c4 = st.columns(4)
        with emp_c1:
            st.metric("👥 Total Employés", emp_stats['total'])
        with emp_c2:
            employes_actifs = len([emp for emp in gestionnaire_employes.employes if emp.get('statut') == 'ACTIF'])
            st.metric("✅ Employés Actifs", employes_actifs)
        with emp_c3:
            st.metric("💰 Salaire Moyen", f"{emp_stats.get('salaire_moyen', 0):,.0f}€")
        with emp_c4:
            employes_surcharges = len([emp for emp in gestionnaire_employes.employes if emp.get('charge_travail', 0) > 90])
            st.metric("⚠️ Surchargés", employes_surcharges)

    st.markdown("<br>", unsafe_allow_html=True)

    # Graphiques combinés
    if stats['total'] > 0 or postes_stats['total_postes'] > 0:
        gc1, gc2 = st.columns(2)
        
        with gc1:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            if stats['par_statut']:
                colors_statut = {'À FAIRE': '#f59e0b', 'EN COURS': '#3b82f6', 'EN ATTENTE': '#ef4444', 'TERMINÉ': '#10b981', 'ANNULÉ': '#6b7280', 'LIVRAISON': '#8b5cf6'}
                fig = px.pie(values=list(stats['par_statut'].values()), names=list(stats['par_statut'].keys()), title="📈 Projets par Statut", color_discrete_map=colors_statut)
                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT_COLOR_CHARTS), legend_title_text='', title_x=0.5)
                st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with gc2:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            if postes_stats.get('par_departement'):
                colors_dept = {'PRODUCTION': '#10b981', 'USINAGE': '#3b82f6', 'QUALITE': '#f59e0b', 'LOGISTIQUE': '#8b5cf6', 'COMMERCIAL': '#ef4444'}
                fig = px.bar(x=list(postes_stats['par_departement'].keys()), y=list(postes_stats['par_departement'].values()), 
                           title="🏭 Postes par Département", color=list(postes_stats['par_departement'].keys()), 
                           color_discrete_map=colors_dept)
                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT_COLOR_CHARTS), showlegend=False, title_x=0.5)
                st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🕒 Projets Récents")
        projets_recents = sorted(gestionnaire.projets, key=lambda x: x.get('id', 0), reverse=True)[:5]
        if not projets_recents:
            st.info("Aucun projet récent.")
        for p in projets_recents:
            st.markdown("<div class='info-card'>", unsafe_allow_html=True)
            rc1, rc2, rc3, rc4 = st.columns([3, 2, 2, 1])
            with rc1:
                st.markdown(f"**#{p.get('id')} - {p.get('nom_projet', 'Sans nom')}**")
                st.caption(f"📝 {p.get('description', 'N/A')[:100]}...")
            with rc2:
                client_display_name = p.get('client_nom_cache', 'N/A')
                if client_display_name == 'N/A' and p.get('client_entreprise_id'):
                    crm_manager = st.session_state.gestionnaire_crm
                    entreprise = crm_manager.get_entreprise_by_id(p.get('client_entreprise_id'))
                    if entreprise:
                        client_display_name = entreprise.get('nom', 'N/A')
                elif client_display_name == 'N/A':
                    client_display_name = p.get('client', 'N/A')

                st.markdown(f"👤 **{client_display_name}**")
                st.caption(f"💰 {format_currency(p.get('prix_estime', 0))}")
            with rc3:
                statut, priorite = p.get('statut', 'N/A'), p.get('priorite', 'N/A')
                statut_map = {'À FAIRE': '🟡', 'EN COURS': '🔵', 'EN ATTENTE': '🔴', 'TERMINÉ': '🟢', 'ANNULÉ': '⚫', 'LIVRAISON': '🟣'}
                priorite_map = {'ÉLEVÉ': '🔴', 'MOYEN': '🟡', 'BAS': '🟢'}
                st.markdown(f"{statut_map.get(statut, '⚪')} {statut}")
                st.caption(f"{priorite_map.get(priorite, '⚪')} {priorite}")
            with rc4:
                if st.button("👁️", key=f"view_rec_{p.get('id')}", help="Voir détails"):
                    st.session_state.selected_project = p
                    st.session_state.show_project_modal = True
            st.markdown("</div>", unsafe_allow_html=True)

def show_itineraire():
    """Version améliorée avec vrais postes de travail"""
    st.markdown("## 🛠️ Itinéraire Fabrication - DG Inc.")
    gestionnaire = st.session_state.gestionnaire
    gestionnaire_postes = st.session_state.gestionnaire_postes  # NOUVEAU
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    if not gestionnaire.projets:
        st.warning("Aucun projet.")
        return
    
    opts = [(p.get('id'), f"#{p.get('id')} - {p.get('nom_projet', 'N/A')}") for p in gestionnaire.projets]
    sel_id = st.selectbox("Projet:", options=[pid for pid, _ in opts], format_func=lambda pid: next((name for id, name in opts if id == pid), ""), key="iti_sel")
    proj = next((p for p in gestionnaire.projets if p.get('id') == sel_id), None)
    
    if not proj:
        st.error("Projet non trouvé.")
        return
    
    st.markdown(f"<div class='project-header'><h2>{proj.get('nom_projet', 'N/A')}</h2></div>", unsafe_allow_html=True)

    # NOUVEAU : Bouton de régénération de gamme
    col_regen1, col_regen2 = st.columns([3, 1])
    with col_regen2:
        if st.button("🔄 Régénérer Gamme", help="Régénérer avec les vrais postes DG Inc."):
            # Déterminer le type de produit
            nom_projet = proj.get('nom_projet', '').lower()
            if any(mot in nom_projet for mot in ['chassis', 'structure', 'assemblage']):
                type_produit = "CHASSIS_SOUDE"
            elif any(mot in nom_projet for mot in ['batiment', 'pont', 'charpente']):
                type_produit = "STRUCTURE_LOURDE"
            else:
                type_produit = "PIECE_PRECISION"
            
            # Générer nouvelle gamme
            gamme = gestionnaire_postes.generer_gamme_fabrication(type_produit, "MOYEN", gestionnaire_employes)
            
            # Mettre à jour les opérations
            nouvelles_operations = []
            for i, op in enumerate(gamme, 1):
                nouvelles_operations.append({
                    'id': i,
                    'sequence': str(op['sequence']),
                    'description': f"{op['poste']} - {proj.get('nom_projet', '')}",
                    'temps_estime': op['temps_estime'],
                    'ressource': op['employes_disponibles'][0] if op['employes_disponibles'] else 'À assigner',
                    'statut': 'À FAIRE',
                    'poste_travail': op['poste']
                })
            
            proj['operations'] = nouvelles_operations
            gestionnaire.sauvegarder_projets()
            st.success("✅ Gamme régénérée avec les postes DG Inc. !")
            st.rerun()

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    operations = proj.get('operations', [])
    if not operations:
        st.info("Aucune opération.")
    else:
        total_time = sum(op.get('temps_estime', 0) for op in operations)
        finished_ops = sum(1 for op in operations if op.get('statut') == 'TERMINÉ')
        progress = (finished_ops / len(operations) * 100) if operations else 0
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.metric("🔧 Opérations", len(operations))
        with mc2:
            st.metric("⏱️ Durée Totale", f"{total_time:.1f}h")
        with mc3:
            st.metric("📊 Progression", f"{progress:.1f}%")
        
        # NOUVEAU : Tableau enrichi avec postes de travail
        data_iti = []
        for op in operations:
            poste_travail = op.get('poste_travail', 'Non assigné')
            data_iti.append({
                '🆔': op.get('id', '?'), 
                '📊 Séq.': op.get('sequence', ''), 
                '🏭 Poste': poste_travail,
                '📋 Desc.': op.get('description', ''), 
                '⏱️ Tps (h)': f"{(op.get('temps_estime', 0) or 0):.1f}", 
                '👨‍🔧 Ress.': op.get('ressource', ''), 
                '🚦 Statut': op.get('statut', 'À FAIRE')
            })
        
        st.dataframe(pd.DataFrame(data_iti), use_container_width=True)
        st.markdown("---")
        st.markdown("##### 📈 Analyse Opérations")
        ac1, ac2 = st.columns(2)
        with ac1:
            counts = {}
            colors_op_statut = {'À FAIRE': '#f59e0b', 'EN COURS': '#3b82f6', 'TERMINÉ': '#10b981', 'EN ATTENTE': '#ef4444'}
            for op in operations:
                status = op.get('statut', 'À FAIRE')
                counts[status] = counts.get(status, 0) + 1
            if counts:
                fig = px.bar(x=list(counts.keys()), y=list(counts.values()), title="Répartition par statut", color=list(counts.keys()), color_discrete_map=colors_op_statut)
                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT_COLOR_CHARTS), showlegend=False, title_x=0.5)
                st.plotly_chart(fig, use_container_width=True)
        with ac2:
            res_time = {}
            for op in operations:
                res = op.get('poste_travail', 'Non assigné')
                time = op.get('temps_estime', 0)
                res_time[res] = res_time.get(res, 0) + time
            if res_time:
                fig = px.pie(values=list(res_time.values()), names=list(res_time.keys()), title="Temps par poste")
                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT_COLOR_CHARTS), legend_title_text='', title_x=0.5)
                st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

def show_liste_projets():
    st.markdown("## 📋 Liste des Projets")
    gestionnaire = st.session_state.gestionnaire
    crm_manager = st.session_state.gestionnaire_crm

    col_create, _ = st.columns([1, 3])
    with col_create:
        if st.button("➕ Nouveau Projet", use_container_width=True, key="create_btn_liste"):
            st.session_state.show_create_project = True
    st.markdown("---")
    if not gestionnaire.projets and not st.session_state.get('show_create_project'):
        st.info("Aucun projet. Cliquez sur 'Nouveau Projet' pour commencer.")

    if gestionnaire.projets:
        with st.expander("🔍 Filtres", expanded=False):
            fcol1, fcol2, fcol3 = st.columns(3)
            statuts_dispo = sorted(list(set([p.get('statut', 'N/A') for p in gestionnaire.projets])))
            priorites_dispo = sorted(list(set([p.get('priorite', 'N/A') for p in gestionnaire.projets])))
            with fcol1:
                filtre_statut = st.multiselect("Statut:", ['Tous'] + statuts_dispo, default=['Tous'])
            with fcol2:
                filtre_priorite = st.multiselect("Priorité:", ['Toutes'] + priorites_dispo, default=['Toutes'])
            with fcol3:
                recherche = st.text_input("🔍 Rechercher:", placeholder="Nom, client...")

        projets_filtres = gestionnaire.projets
        if 'Tous' not in filtre_statut and filtre_statut:
            projets_filtres = [p for p in projets_filtres if p.get('statut') in filtre_statut]
        if 'Toutes' not in filtre_priorite and filtre_priorite:
            projets_filtres = [p for p in projets_filtres if p.get('priorite') in filtre_priorite]
        if recherche:
            terme = recherche.lower()
            projets_filtres = [p for p in projets_filtres if
                               terme in str(p.get('nom_projet', '')).lower() or
                               terme in str(p.get('client_nom_cache', '')).lower() or
                               (p.get('client_entreprise_id') and crm_manager.get_entreprise_by_id(p.get('client_entreprise_id')) and terme in crm_manager.get_entreprise_by_id(p.get('client_entreprise_id')).get('nom', '').lower()) or
                               terme in str(p.get('client', '')).lower()
                              ]

        st.markdown(f"**{len(projets_filtres)} projet(s) trouvé(s)**")
        if projets_filtres:
            df_data = []
            for p in projets_filtres:
                client_display_name_df = p.get('client_nom_cache', 'N/A')
                if client_display_name_df == 'N/A' and p.get('client_entreprise_id'):
                    entreprise = crm_manager.get_entreprise_by_id(p.get('client_entreprise_id'))
                    if entreprise:
                        client_display_name_df = entreprise.get('nom', 'N/A')
                elif client_display_name_df == 'N/A':
                    client_display_name_df = p.get('client', 'N/A')

                df_data.append({'🆔': p.get('id', '?'), '📋 Projet': p.get('nom_projet', 'N/A'), '👤 Client': client_display_name_df, '🚦 Statut': p.get('statut', 'N/A'), '⭐ Priorité': p.get('priorite', 'N/A'), '📅 Début': p.get('date_soumis', 'N/A'), '🏁 Fin': p.get('date_prevu', 'N/A'), '💰 Prix': format_currency(p.get('prix_estime', 0))})
            st.dataframe(pd.DataFrame(df_data), use_container_width=True)
            st.markdown("---")
            st.markdown("### 🔧 Actions sur un projet")
            selected_id_actions = st.selectbox("Projet:", options=[p.get('id') for p in projets_filtres], format_func=lambda pid: f"#{pid} - {next((p.get('nom_projet', '') for p in projets_filtres if p.get('id') == pid), '')}", key="proj_actions_sel")
            sel_proj_action = next((p for p in gestionnaire.projets if p.get('id') == selected_id_actions), None)
            if sel_proj_action:
                acol1, acol2, acol3 = st.columns(3)
                with acol1:
                    if st.button("👁️ Voir Détails", use_container_width=True, key=f"view_act_{selected_id_actions}"):
                        st.session_state.selected_project = sel_proj_action
                        st.session_state.show_project_modal = True
                with acol2:
                    if st.button("✏️ Modifier", use_container_width=True, key=f"edit_act_{selected_id_actions}"):
                        st.session_state.edit_project_data = sel_proj_action
                        st.session_state.show_edit_project = True
                with acol3:
                    if st.button("🗑️ Supprimer", use_container_width=True, key=f"del_act_{selected_id_actions}"):
                        st.session_state.delete_project_id = selected_id_actions
                        st.session_state.show_delete_confirmation = True

    if st.session_state.get('show_create_project'):
        render_create_project_form(gestionnaire, crm_manager)
    if st.session_state.get('show_edit_project') and st.session_state.get('edit_project_data'):
        render_edit_project_form(gestionnaire, crm_manager, st.session_state.edit_project_data)
    if st.session_state.get('show_delete_confirmation'):
        render_delete_confirmation(gestionnaire)

def render_create_project_form(gestionnaire, crm_manager):
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### ➕ Créer Projet")
    with st.form("create_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        with fc1:
            nom = st.text_input("Nom *:")
            liste_entreprises_crm_form = [("", "Sélectionner ou laisser vide")] + [(e['id'], e['nom']) for e in crm_manager.entreprises]
            selected_entreprise_id_form = st.selectbox(
                "Client (Entreprise) *:",
                options=[e_id for e_id, _ in liste_entreprises_crm_form],
                format_func=lambda e_id: next((nom for id_e, nom in liste_entreprises_crm_form if id_e == e_id), "Sélectionner..."),
                key="project_create_client_select"
            )
            client_nom_direct_form = st.text_input("Ou nom client direct (si non listé):")

            statut = st.selectbox("Statut:", ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON"])
            priorite = st.selectbox("Priorité:", ["BAS", "MOYEN", "ÉLEVÉ"])
        with fc2:
            tache = st.selectbox("Type:", ["ESTIMATION", "CONCEPTION", "DÉVELOPPEMENT", "TESTS", "DÉPLOIEMENT", "MAINTENANCE", "FORMATION"])
            d_debut = st.date_input("Début:", datetime.now().date())
            d_fin = st.date_input("Fin Prévue:", datetime.now().date() + timedelta(days=30))
            bd_ft = st.number_input("BD-FT (h):", 0, value=40, step=1)
            prix = st.number_input("Prix ($):", 0.0, value=10000.0, step=100.0, format="%.2f")
        desc = st.text_area("Description:")
        
        # Assignation d'employés
        if gestionnaire_employes.employes:
            st.markdown("##### 👥 Assignation d'Employés")
            employes_disponibles = [(emp['id'], f"{emp.get('prenom', '')} {emp.get('nom', '')} ({emp.get('poste', '')})") for emp in gestionnaire_employes.employes if emp.get('statut') == 'ACTIF']
            employes_assignes = st.multiselect(
                "Employés assignés:",
                options=[emp_id for emp_id, _ in employes_disponibles],
                format_func=lambda emp_id: next((nom for id_e, nom in employes_disponibles if id_e == emp_id), ""),
                key="project_create_employes_assign"
            )
        
        st.markdown("<small>* Obligatoire</small>", unsafe_allow_html=True)
        s_btn, c_btn = st.columns(2)
        with s_btn:
            submit = st.form_submit_button("💾 Créer", use_container_width=True)
        with c_btn:
            cancel = st.form_submit_button("❌ Annuler", use_container_width=True)
        if submit:
            if not nom or (not selected_entreprise_id_form and not client_nom_direct_form):
                st.error("Nom du projet et Client (sélection ou nom direct) obligatoires.")
            elif d_fin < d_debut:
                st.error("Date fin < date début.")
            else:
                client_nom_cache_val = ""
                if selected_entreprise_id_form:
                    entreprise_obj = crm_manager.get_entreprise_by_id(selected_entreprise_id_form)
                    if entreprise_obj:
                        client_nom_cache_val = entreprise_obj.get('nom', '')
                elif client_nom_direct_form:
                    client_nom_cache_val = client_nom_direct_form

                data = {'nom_projet': nom,
                        'client_entreprise_id': selected_entreprise_id_form if selected_entreprise_id_form else None,
                        'client_nom_cache': client_nom_cache_val,
                        'client': client_nom_direct_form if not selected_entreprise_id_form and client_nom_direct_form else "",
                        'statut': statut, 'priorite': priorite, 'tache': tache, 'date_soumis': d_debut.strftime('%Y-%m-%d'), 'date_prevu': d_fin.strftime('%Y-%m-%d'), 'bd_ft_estime': str(bd_ft), 'prix_estime': str(prix), 'description': desc or f"Projet {tache.lower()} pour {client_nom_cache_val}", 'sous_taches': [], 'materiaux': [], 'operations': [], 'employes_assignes': employes_assignes if 'employes_assignes' in locals() else []}
                pid = gestionnaire.ajouter_projet(data)
                
                # Mettre à jour les assignations des employés
                if 'employes_assignes' in locals() and employes_assignes:
                    for emp_id in employes_assignes:
                        employe = gestionnaire_employes.get_employe_by_id(emp_id)
                        if employe:
                            projets_existants = employe.get('projets_assignes', [])
                            if pid not in projets_existants:
                                projets_existants.append(pid)
                                gestionnaire_employes.modifier_employe(emp_id, {'projets_assignes': projets_existants})
                
                st.success(f"✅ Projet #{pid} créé !")
                st.session_state.show_create_project = False
                st.rerun()
        if cancel:
            st.session_state.show_create_project = False
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def render_edit_project_form(gestionnaire, crm_manager, project_data):
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(f"### ✏️ Modifier Projet #{project_data.get('id')}")
    with st.form("edit_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        with fc1:
            nom = st.text_input("Nom *:", value=project_data.get('nom_projet', ''))
            liste_entreprises_crm_form = [("", "Sélectionner ou laisser vide")] + [(e['id'], e['nom']) for e in crm_manager.entreprises]
            current_entreprise_id = project_data.get('client_entreprise_id', "")
            selected_entreprise_id_form = st.selectbox(
                "Client (Entreprise) *:",
                options=[e_id for e_id, _ in liste_entreprises_crm_form],
                index=next((i for i, (e_id, _) in enumerate(liste_entreprises_crm_form) if e_id == current_entreprise_id), 0),
                format_func=lambda e_id: next((nom for id_e, nom in liste_entreprises_crm_form if id_e == e_id), "Sélectionner..."),
                key="project_edit_client_select"
            )
            client_nom_direct_form = st.text_input("Ou nom client direct:", value=project_data.get('client', ''))

            statuts = ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON"]
            current_statut = project_data.get('statut', 'À FAIRE')
            statut = st.selectbox("Statut:", statuts, index=statuts.index(current_statut) if current_statut in statuts else 0)
            
            priorites = ["BAS", "MOYEN", "ÉLEVÉ"]
            current_priorite = project_data.get('priorite', 'MOYEN')
            priorite = st.selectbox("Priorité:", priorites, index=priorites.index(current_priorite) if current_priorite in priorites else 1)
        with fc2:
            taches = ["ESTIMATION", "CONCEPTION", "DÉVELOPPEMENT", "TESTS", "DÉPLOIEMENT", "MAINTENANCE", "FORMATION"]
            current_tache = project_data.get('tache', 'ESTIMATION')
            tache = st.selectbox("Type:", taches, index=taches.index(current_tache) if current_tache in taches else 0)
            
            try:
                d_debut = st.date_input("Début:", datetime.strptime(project_data.get('date_soumis', ''), '%Y-%m-%d').date())
            except:
                d_debut = st.date_input("Début:", datetime.now().date())
            try:
                d_fin = st.date_input("Fin Prévue:", datetime.strptime(project_data.get('date_prevu', ''), '%Y-%m-%d').date())
            except:
                d_fin = st.date_input("Fin Prévue:", datetime.now().date() + timedelta(days=30))
            
            bd_ft = st.number_input("BD-FT (h):", 0, value=int(project_data.get('bd_ft_estime', 0)), step=1)
            try:
                prix_val = float(str(project_data.get('prix_estime', '0')).replace(', '').replace(',', ''))
            except:
                prix_val = 0.0
            prix = st.number_input("Prix ($):", 0.0, value=prix_val, step=100.0, format="%.2f")
        desc = st.text_area("Description:", value=project_data.get('description', ''))
        
        # Assignation d'employés
        if gestionnaire_employes.employes:
            st.markdown("##### 👥 Assignation d'Employés")
            employes_disponibles = [(emp['id'], f"{emp.get('prenom', '')} {emp.get('nom', '')} ({emp.get('poste', '')})") for emp in gestionnaire_employes.employes if emp.get('statut') == 'ACTIF']
            current_employes = project_data.get('employes_assignes', [])
            employes_assignes = st.multiselect(
                "Employés assignés:",
                options=[emp_id for emp_id, _ in employes_disponibles],
                default=[emp_id for emp_id in current_employes if emp_id in [e[0] for e in employes_disponibles]],
                format_func=lambda emp_id: next((nom for id_e, nom in employes_disponibles if id_e == emp_id), ""),
                key="project_edit_employes_assign"
            )
        
        st.markdown("<small>* Obligatoire</small>", unsafe_allow_html=True)
        s_btn, c_btn = st.columns(2)
        with s_btn:
            submit = st.form_submit_button("💾 Sauvegarder", use_container_width=True)
        with c_btn:
            cancel = st.form_submit_button("❌ Annuler", use_container_width=True)
        if submit:
            if not nom or (not selected_entreprise_id_form and not client_nom_direct_form):
                st.error("Nom du projet et Client obligatoires.")
            elif d_fin < d_debut:
                st.error("Date fin < date début.")
            else:
                client_nom_cache_val = ""
                if selected_entreprise_id_form:
                    entreprise_obj = crm_manager.get_entreprise_by_id(selected_entreprise_id_form)
                    if entreprise_obj:
                        client_nom_cache_val = entreprise_obj.get('nom', '')
                elif client_nom_direct_form:
                    client_nom_cache_val = client_nom_direct_form

                update_data = {
                    'nom_projet': nom,
                    'client_entreprise_id': selected_entreprise_id_form if selected_entreprise_id_form else None,
                    'client_nom_cache': client_nom_cache_val,
                    'client': client_nom_direct_form if not selected_entreprise_id_form and client_nom_direct_form else "",
                    'statut': statut, 'priorite': priorite, 'tache': tache, 'date_soumis': d_debut.strftime('%Y-%m-%d'), 'date_prevu': d_fin.strftime('%Y-%m-%d'), 'bd_ft_estime': str(bd_ft), 'prix_estime': str(prix), 'description': desc,
                    'employes_assignes': employes_assignes if 'employes_assignes' in locals() else []
                }
                
                if gestionnaire.modifier_projet(project_data['id'], update_data):
                    # Mettre à jour les assignations des employés
                    if 'employes_assignes' in locals():
                        # Supprimer l'ancien projet des anciens employés
                        for emp_id in project_data.get('employes_assignes', []):
                            if emp_id not in employes_assignes:
                                employe = gestionnaire_employes.get_employe_by_id(emp_id)
                                if employe:
                                    projets_existants = employe.get('projets_assignes', [])
                                    if project_data['id'] in projets_existants:
                                        projets_existants.remove(project_data['id'])
                                        gestionnaire_employes.modifier_employe(emp_id, {'projets_assignes': projets_existants})
                        
                        # Ajouter le projet aux nouveaux employés
                        for emp_id in employes_assignes:
                            if emp_id not in project_data.get('employes_assignes', []):
                                employe = gestionnaire_employes.get_employe_by_id(emp_id)
                                if employe:
                                    projets_existants = employe.get('projets_assignes', [])
                                    if project_data['id'] not in projets_existants:
                                        projets_existants.append(project_data['id'])
                                        gestionnaire_employes.modifier_employe(emp_id, {'projets_assignes': projets_existants})
                    
                    st.success(f"✅ Projet #{project_data['id']} modifié !")
                    st.session_state.show_edit_project = False
                    st.session_state.edit_project_data = None
                    st.rerun()
                else:
                    st.error("Erreur lors de la modification.")
        if cancel:
            st.session_state.show_edit_project = False
            st.session_state.edit_project_data = None
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def render_delete_confirmation(gestionnaire):
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### 🗑️ Confirmation de Suppression")
    project_id = st.session_state.delete_project_id
    project = next((p for p in gestionnaire.projets if p.get('id') == project_id), None)
    
    if project:
        st.warning(f"⚠️ Êtes-vous sûr de vouloir supprimer le projet **#{project.get('id')} - {project.get('nom_projet', 'N/A')}** ?")
        st.markdown("Cette action est **irréversible**.")
        
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            if st.button("🗑️ Confirmer Suppression", use_container_width=True):
                gestionnaire.supprimer_projet(project_id)
                st.success(f"✅ Projet #{project_id} supprimé !")
                st.session_state.show_delete_confirmation = False
                st.session_state.delete_project_id = None
                st.rerun()
        with dcol2:
            if st.button("❌ Annuler", use_container_width=True):
                st.session_state.show_delete_confirmation = False
                st.session_state.delete_project_id = None
                st.rerun()
    else:
        st.error("Projet non trouvé.")
        st.session_state.show_delete_confirmation = False
        st.session_state.delete_project_id = None
    st.markdown("</div>", unsafe_allow_html=True)

def show_nomenclature():
    st.markdown("## 📊 Nomenclature (BOM)")
    gestionnaire = st.session_state.gestionnaire
    if not gestionnaire.projets:
        st.warning("Aucun projet.")
        return
    opts = [(p.get('id'), f"#{p.get('id')} - {p.get('nom_projet', 'N/A')}") for p in gestionnaire.projets]
    sel_id = st.selectbox("Projet:", options=[pid for pid, _ in opts], format_func=lambda pid: next((name for id, name in opts if id == pid), ""), key="bom_sel")
    proj = next((p for p in gestionnaire.projets if p.get('id') == sel_id), None)
    if not proj:
        st.error("Projet non trouvé.")
        return
    st.markdown(f"<div class='project-header'><h2>{proj.get('nom_projet', 'N/A')}</h2></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    materiaux = proj.get('materiaux', [])
    if not materiaux:
        st.info("Aucun matériau.")
    else:
        total_cost = 0
        data_bom = []
        for item in materiaux:
            qty, price = item.get('quantite', 0) or 0, item.get('prix_unitaire', 0) or 0
            total = qty * price
            total_cost += total
            data_bom.append({'🆔': item.get('id', '?'), '📝 Code': item.get('code', ''), '📋 Désignation': item.get('designation', 'N/A'), '📊 Qté': f"{qty} {item.get('unite', '')}", '💳 PU': format_currency(price), '💰 Total': format_currency(total), '🏪 Fourn.': item.get('fournisseur', 'N/A')})
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.metric("📦 Items", len(materiaux))
        with mc2:
            st.metric("💰 Coût Total", format_currency(total_cost))
        with mc3:
            st.metric("📊 Coût Moyen/Item", format_currency(total_cost / len(materiaux) if materiaux else 0))
        st.dataframe(pd.DataFrame(data_bom), use_container_width=True)
        if len(materiaux) > 1:
            st.markdown("---")
            st.markdown("##### 📈 Analyse Coûts Matériaux")
            costs = [(item.get('quantite', 0) or 0) * (item.get('prix_unitaire', 0) or 0) for item in materiaux]
            labels = [item.get('designation', 'N/A') for item in materiaux]
            fig = px.pie(values=costs, names=labels, title="Répartition coûts par matériau")
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT_COLOR_CHARTS), legend_title_text='', title_x=0.5)
            st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

def show_gantt():
    st.markdown("## 📈 Diagramme de Gantt")
    gestionnaire = st.session_state.gestionnaire
    crm_manager = st.session_state.gestionnaire_crm
    if not gestionnaire.projets:
        st.info("Aucun projet pour Gantt.")
        return
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    gantt_data = []
    for p in gestionnaire.projets:
        try:
            s_date = datetime.strptime(p.get('date_soumis', ''), "%Y-%m-%d") if p.get('date_soumis') else None
            e_date = datetime.strptime(p.get('date_prevu', ''), "%Y-%m-%d") if p.get('date_prevu') else None
            if s_date and e_date:
                client_display_name_gantt = p.get('client_nom_cache', 'N/A')
                if client_display_name_gantt == 'N/A' and p.get('client_entreprise_id'):
                    entreprise = crm_manager.get_entreprise_by_id(p.get('client_entreprise_id'))
                    if entreprise:
                        client_display_name_gantt = entreprise.get('nom', 'N/A')
                elif client_display_name_gantt == 'N/A':
                    client_display_name_gantt = p.get('client', 'N/A')

                gantt_data.append({'Projet': f"#{p.get('id')} - {p.get('nom_projet', 'N/A')}", 'Début': s_date, 'Fin': e_date, 'Client': client_display_name_gantt, 'Statut': p.get('statut', 'N/A'), 'Priorité': p.get('priorite', 'N/A')})
        except:
            continue
    if not gantt_data:
        st.warning("Données de dates invalides pour Gantt.")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    df_gantt = pd.DataFrame(gantt_data)
    colors_gantt = {'À FAIRE': '#f59e0b', 'EN COURS': '#3b82f6', 'EN ATTENTE': '#ef4444', 'TERMINÉ': '#10b981', 'ANNULÉ': '#6b7280', 'LIVRAISON': '#8b5cf6'}
    fig = px.timeline(df_gantt, x_start="Début", x_end="Fin", y="Projet", color="Statut", color_discrete_map=colors_gantt, title="📊 Planning Projets", hover_data=['Client', 'Priorité'])
    fig.update_layout(height=max(400, len(gantt_data) * 40), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT_COLOR_CHARTS), xaxis=dict(title="📅 Calendrier", gridcolor='rgba(0,0,0,0.05)'), yaxis=dict(title="📋 Projets", gridcolor='rgba(0,0,0,0.05)', categoryorder='total ascending'), title_x=0.5, legend_title_text='')
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("---")
    st.markdown("##### 📊 Stats Planning")
    durees = [(item['Fin'] - item['Début']).days for item in gantt_data if item['Fin'] and item['Début']]
    if durees:
        gsc1, gsc2, gsc3 = st.columns(3)
        with gsc1:
            st.metric("📅 Durée Moy.", f"{sum(durees) / len(durees):.1f} j")
        with gsc2:
            st.metric("⏱️ Min Durée", f"{min(durees)} j")
        with gsc3:
            st.metric("🕐 Max Durée", f"{max(durees)} j")
    st.markdown("</div>", unsafe_allow_html=True)

def show_calendrier():
    st.markdown("## 📅 Vue Calendrier")
    gestionnaire = st.session_state.gestionnaire
    crm_manager = st.session_state.gestionnaire_crm
    curr_date = st.session_state.selected_date

    # Navigation
    cn1, cn2, cn3 = st.columns([1, 2, 1])
    with cn1:
        if st.button("◀️ Mois Préc.", key="cal_prev", use_container_width=True):
            prev_m = curr_date.replace(day=1) - timedelta(days=1)
            st.session_state.selected_date = prev_m.replace(day=min(curr_date.day, calendar.monthrange(prev_m.year, prev_m.month)[1]))
            st.rerun()
    with cn2:
        m_names = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        st.markdown(f"<div class='project-header' style='margin-bottom:1rem; text-align:center;'><h4 style='margin:0; color:#1E40AF;'>{m_names[curr_date.month]} {curr_date.year}</h4></div>", unsafe_allow_html=True)
    with cn3:
        if st.button("Mois Suiv. ▶️", key="cal_next", use_container_width=True):
            next_m = (curr_date.replace(day=calendar.monthrange(curr_date.year, curr_date.month)[1])) + timedelta(days=1)
            st.session_state.selected_date = next_m.replace(day=min(curr_date.day, calendar.monthrange(next_m.year, next_m.month)[1]))
            st.rerun()
    if st.button("📅 Aujourd'hui", key="cal_today", use_container_width=True):
        st.session_state.selected_date = date.today()
        st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)

    # Préparation des données
    events_by_date = {}
    for p in gestionnaire.projets:
        try:
            s_date_obj = datetime.strptime(p.get('date_soumis', ''), "%Y-%m-%d").date() if p.get('date_soumis') else None
            e_date_obj = datetime.strptime(p.get('date_prevu', ''), "%Y-%m-%d").date() if p.get('date_prevu') else None
            
            client_display_name_cal = p.get('client_nom_cache', 'N/A')
            if client_display_name_cal == 'N/A':
                 client_display_name_cal = p.get('client', 'N/A')

            if s_date_obj:
                if s_date_obj not in events_by_date: events_by_date[s_date_obj] = []
                events_by_date[s_date_obj].append({'type': '🚀 Début', 'projet': p.get('nom_projet', 'N/A'), 'id': p.get('id'), 'client': client_display_name_cal, 'color_class': 'event-type-debut'})
            if e_date_obj:
                if e_date_obj not in events_by_date: events_by_date[e_date_obj] = []
                events_by_date[e_date_obj].append({'type': '🏁 Fin', 'projet': p.get('nom_projet', 'N/A'), 'id': p.get('id'), 'client': client_display_name_cal, 'color_class': 'event-type-fin'})
        except:
            continue
    
    # Affichage de la grille du calendrier
    cal = calendar.Calendar(firstweekday=6)
    month_dates = cal.monthdatescalendar(curr_date.year, curr_date.month)
    day_names = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"]

    st.markdown('<div class="calendar-grid-container">', unsafe_allow_html=True)
    # En-têtes des jours
    header_cols = st.columns(7)
    for i, name in enumerate(day_names):
        with header_cols[i]:
            st.markdown(f"<div class='calendar-week-header'><div class='day-name'>{name}</div></div>", unsafe_allow_html=True)
    
    # Grille des jours
    for week in month_dates:
        cols = st.columns(7)
        for i, day_date_obj in enumerate(week):
            with cols[i]:
                day_classes = ["calendar-day-cell"]
                if day_date_obj.month != curr_date.month:
                    day_classes.append("other-month")
                if day_date_obj == date.today():
                    day_classes.append("today")

                events_html = ""
                if day_date_obj in events_by_date:
                    for event in events_by_date[day_date_obj]:
                        events_html += f"<div class='calendar-event-item {event['color_class']}' title='{event['projet']}'>{event['type']} P#{event['id']}</div>"

                cell_html = f"""
                <div class='{' '.join(day_classes)}'>
                    <div class='day-number'>{day_date_obj.day}</div>
                    <div class='calendar-events-container'>{events_html}</div>
                </div>
                """
                st.markdown(cell_html, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

def show_kanban():
    st.markdown("## 🔄 Vue Kanban (Style Planner)")
    gestionnaire = st.session_state.gestionnaire
    crm_manager = st.session_state.gestionnaire_crm

    # Initialisation de l'état de drag & drop
    if 'dragged_project_id' not in st.session_state:
        st.session_state.dragged_project_id = None
    if 'dragged_from_status' not in st.session_state:
        st.session_state.dragged_from_status = None

    if not gestionnaire.projets:
        st.info("Aucun projet à afficher dans le Kanban.")
        return

    # Logique de filtrage
    with st.expander("🔍 Filtres", expanded=False):
        recherche = st.text_input("Rechercher par nom, client...", key="kanban_search")

    projets_filtres = gestionnaire.projets
    if recherche:
        terme = recherche.lower()
        projets_filtres = [
            p for p in projets_filtres if
            terme in str(p.get('nom_projet', '')).lower() or
            terme in str(p.get('client_nom_cache', '')).lower() or
            (p.get('client_entreprise_id') and crm_manager.get_entreprise_by_id(p.get('client_entreprise_id')) and terme in crm_manager.get_entreprise_by_id(p.get('client_entreprise_id')).get('nom', '').lower()) or
            terme in str(p.get('client', '')).lower()
        ]

    # Préparation des données pour les colonnes
    statuts_k = ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON"]
    projs_by_statut = {s: [] for s in statuts_k}
    for p in projets_filtres:
        stat = p.get('statut', 'À FAIRE')
        if stat in projs_by_statut:
            projs_by_statut[stat].append(p)
        else:
            projs_by_statut['À FAIRE'].append(p)
    
    # Définition des couleurs pour les colonnes
    col_borders_k = {'À FAIRE': '#f59e0b', 'EN COURS': '#3b82f6', 'EN ATTENTE': '#ef4444', 'TERMINÉ': '#10b981', 'LIVRAISON': '#8b5cf6'}

    # Indicateur visuel si un projet est en cours de déplacement
    if st.session_state.dragged_project_id:
        proj_dragged = next((p for p in gestionnaire.projets if p['id'] == st.session_state.dragged_project_id), None)
        if proj_dragged:
            st.markdown(f"""
            <div class="kanban-drag-indicator">
                Déplacement de: <strong>#{proj_dragged['id']} - {proj_dragged['nom_projet']}</strong>
            </div>
            """, unsafe_allow_html=True)
            if st.sidebar.button("❌ Annuler le déplacement", use_container_width=True):
                st.session_state.dragged_project_id = None
                st.session_state.dragged_from_status = None
                st.rerun()

    # STRUCTURE HORIZONTALE
    st.markdown('<div class="kanban-container">', unsafe_allow_html=True)

    for sk in statuts_k:
        # Chaque colonne est un conteneur div
        st.markdown(f'<div class="kanban-column" style="border-top: 4px solid {col_borders_k.get(sk, "#ccc")};">', unsafe_allow_html=True)

        # En-tête de la colonne
        st.markdown(f'<div class="kanban-header">{sk} ({len(projs_by_statut[sk])})</div>', unsafe_allow_html=True)

        # Si un projet est "soulevé", afficher une zone de dépôt
        if st.session_state.dragged_project_id and sk != st.session_state.dragged_from_status:
            if st.button(f"⤵️ Déposer ici", key=f"drop_in_{sk}", use_container_width=True, help=f"Déplacer vers {sk}"):
                proj_id_to_move = st.session_state.dragged_project_id
                if gestionnaire.modifier_projet(proj_id_to_move, {'statut': sk}):
                    st.success(f"Projet #{proj_id_to_move} déplacé vers '{sk}'!")
                else:
                    st.error("Une erreur est survenue lors du déplacement.")

                st.session_state.dragged_project_id = None
                st.session_state.dragged_from_status = None
                st.rerun()

        # Zone pour les cartes avec défilement vertical interne
        st.markdown('<div class="kanban-cards-zone">', unsafe_allow_html=True)

        if not projs_by_statut[sk]:
            st.markdown("<div style='text-align:center; color:var(--text-color-muted); margin-top:2rem;'><i>Vide</i></div>", unsafe_allow_html=True)

        for pk in projs_by_statut[sk]:
            prio_k = pk.get('priorite', 'MOYEN')
            card_borders_k = {'ÉLEVÉ': '#ef4444', 'MOYEN': '#f59e0b', 'BAS': '#10b981'}
            prio_icons_k = {'ÉLEVÉ': '🔴', 'MOYEN': '🟡', 'BAS': '🟢'}
            
            client_display_name_kanban = pk.get('client_nom_cache', 'N/A')
            if client_display_name_kanban == 'N/A' and pk.get('client_entreprise_id'):
                entreprise = crm_manager.get_entreprise_by_id(pk.get('client_entreprise_id'))
                client_display_name_kanban = entreprise.get('nom', 'N/A') if entreprise else 'N/A'
            elif client_display_name_kanban == 'N/A':
                client_display_name_kanban = pk.get('client', 'N/A')
            
            # Affichage de la carte
            st.markdown(f"""
            <div class='kanban-card' style='border-left-color:{card_borders_k.get(prio_k, 'var(--border-color)')};'>
                <div class='kanban-card-title'>#{pk.get('id')} - {pk.get('nom_projet', 'N/A')}</div>
                <div class='kanban-card-info'>👤 {client_display_name_kanban}</div>
                <div class='kanban-card-info'>{prio_icons_k.get(prio_k, '⚪')} {prio_k}</div>
                <div class='kanban-card-info'>💰 {format_currency(pk.get('prix_estime', 0))}</div>
            </div>
            """, unsafe_allow_html=True)

            # Boutons d'action pour la carte
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👁️ Voir", key=f"view_kanban_{pk['id']}", help="Voir les détails", use_container_width=True):
                    st.session_state.selected_project = pk
                    st.session_state.show_project_modal = True
                    st.rerun()
            with col2:
                if st.button("➡️ Déplacer", key=f"move_kanban_{pk['id']}", help="Déplacer ce projet", use_container_width=True):
                    st.session_state.dragged_project_id = pk['id']
                    st.session_state.dragged_from_status = sk
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

def show_project_modal():
    """Affichage des détails d'un projet dans un expander"""
    if 'selected_project' not in st.session_state or not st.session_state.get('show_project_modal') or not st.session_state.selected_project:
        return
    
    proj_mod = st.session_state.selected_project
    
    with st.expander(f"📁 Détails Projet #{proj_mod.get('id')} - {proj_mod.get('nom_projet', 'N/A')}", expanded=True):
        if st.button("✖️ Fermer", key="close_modal_details_btn_top"):
            st.session_state.show_project_modal = False
            st.rerun()
        
        st.markdown("---")
        
        mc1, mc2 = st.columns(2)
        with mc1:
            st.markdown(f"""
            <div class='info-card'>
                <h4>📋 {proj_mod.get('nom_projet', 'N/A')}</h4>
                <p><strong>👤 Client:</strong> {proj_mod.get('client', 'N/A')}</p>
                <p><strong>🚦 Statut:</strong> {proj_mod.get('statut', 'N/A')}</p>
                <p><strong>⭐ Priorité:</strong> {proj_mod.get('priorite', 'N/A')}</p>
                <p><strong>✅ Tâche:</strong> {proj_mod.get('tache', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with mc2:
            st.markdown(f"""
            <div class='info-card'>
                <h4>📊 Finances</h4>
                <p><strong>💰 Prix:</strong> {format_currency(proj_mod.get('prix_estime', 0))}</p>
                <p><strong>⏱️ BD-FT:</strong> {proj_mod.get('bd_ft_estime', 'N/A')}h</p>
                <p><strong>📅 Début:</strong> {proj_mod.get('date_soumis', 'N/A')}</p>
                <p><strong>🏁 Fin:</strong> {proj_mod.get('date_prevu', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        if proj_mod.get('description'):
            st.markdown("##### 📝 Description")
            st.markdown(f"<div class='info-card'><p>{proj_mod.get('description', 'Aucune.')}</p></div>", unsafe_allow_html=True)

        tabs_mod = st.tabs(["📝 Sous-tâches", "📦 Matériaux", "🔧 Opérations"])
        
        with tabs_mod[0]:
            sts_mod = proj_mod.get('sous_taches', [])
            if not sts_mod:
                st.info("Aucune sous-tâche.")
            else:
                for st_item in sts_mod:
                    st_color = {
                        'À FAIRE': 'orange', 
                        'EN COURS': 'var(--primary-color)', 
                        'TERMINÉ': 'var(--success-color)'
                    }.get(st_item.get('statut', 'À FAIRE'), 'var(--text-color-muted)')
                    
                    st.markdown(f"""
                    <div class='info-card' style='border-left:4px solid {st_color};margin-top:0.5rem;'>
                        <h5 style='margin:0 0 0.3rem 0;'>ST{st_item.get('id')} - {st_item.get('nom', 'N/A')}</h5>
                        <p style='margin:0 0 0.3rem 0;'>🚦 {st_item.get('statut', 'N/A')}</p>
                        <p style='margin:0;'>📅 {st_item.get('date_debut', 'N/A')} → {st_item.get('date_fin', 'N/A')}</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        with tabs_mod[1]:
            mats_mod = proj_mod.get('materiaux', [])
            if not mats_mod:
                st.info("Aucun matériau.")
            else:
                total_c_mod = 0
                for mat in mats_mod:
                    q, p_u = mat.get('quantite', 0), mat.get('prix_unitaire', 0)
                    tot = q * p_u
                    total_c_mod += tot
                    fournisseur_html = ""
                    if mat.get("fournisseur"):
                        fournisseur_html = f"<p style='margin:0.3rem 0 0 0;font-size:0.9em;'>🏪 {mat.get('fournisseur', 'N/A')}</p>"
                    
                    st.markdown(f"""
                    <div class='info-card' style='margin-top:0.5rem;'>
                        <h5 style='margin:0 0 0.3rem 0;'>{mat.get('code', 'N/A')} - {mat.get('designation', 'N/A')}</h5>
                        <div style='display:flex;justify-content:space-between;font-size:0.9em;'>
                            <span>📊 {q} {mat.get('unite', '')}</span>
                            <span>💳 {format_currency(p_u)}</span>
                            <span>💰 {format_currency(tot)}</span>
                        </div>
                        {fournisseur_html}
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class='info-card' style='background:var(--primary-color-lighter);text-align:center;margin-top:1rem;'>
                    <h5 style='color:var(--primary-color-darker);margin:0;'>💰 Coût Total Mat.: {format_currency(total_c_mod)}</h5>
                </div>
                """, unsafe_allow_html=True)
        
        with tabs_mod[2]:
            ops_mod = proj_mod.get('operations', [])
            if not ops_mod:
                st.info("Aucune opération.")
            else:
                total_t_mod = 0
                for op_item in ops_mod:
                    tps = op_item.get('temps_estime', 0)
                    total_t_mod += tps
                    op_color = {
                        'À FAIRE': 'orange', 
                        'EN COURS': 'var(--primary-color)', 
                        'TERMINÉ': 'var(--success-color)'
                    }.get(op_item.get('statut', 'À FAIRE'), 'var(--text-color-muted)')
                    
                    poste_travail = op_item.get('poste_travail', 'Non assigné')
                    st.markdown(f"""
                    <div class='info-card' style='border-left:4px solid {op_color};margin-top:0.5rem;'>
                        <h5 style='margin:0 0 0.3rem 0;'>{op_item.get('sequence', '?')} - {op_item.get('description', 'N/A')}</h5>
                        <div style='display:flex;justify-content:space-between;font-size:0.9em;'>
                            <span>🏭 {poste_travail}</span>
                            <span>⏱️ {tps}h</span>
                            <span>👨‍🔧 {op_item.get('ressource', 'N/A')}</span>
                            <span>🚦 {op_item.get('statut', 'N/A')}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class='info-card' style='background:var(--primary-color-lighter);text-align:center;margin-top:1rem;'>
                    <h5 style='color:var(--primary-color-darker);margin:0;'>⏱️ Temps Total Est.: {total_t_mod}h</h5>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("✖️ Fermer", use_container_width=True, key="close_modal_details_btn_bottom"):
            st.session_state.show_project_modal = False
            st.rerun()

def show_inventory_management_page():
    st.markdown("## 📦 Gestion de l'Inventaire")

    if 'inventory_data' not in st.session_state:
        st.session_state.inventory_data = load_inventory_data()
    inventory_data = st.session_state.inventory_data

    action_mode = st.session_state.get('inv_action_mode', "Voir Liste")

    if action_mode == "Ajouter Article":
        st.subheader("➕ Ajouter un Nouvel Article")
        with st.form("add_inventory_item_form", clear_on_submit=True):
            new_id = get_next_inventory_id(inventory_data)
            st.text_input("ID Article (auto)", value=str(new_id), disabled=True)
            nom = st.text_input("Nom de l'article *:")
            type_art = st.selectbox("Type *:", TYPES_PRODUITS_INVENTAIRE)
            quantite_imp = st.text_input("Quantité Stock (Impérial) *:", "0' 0\"")
            limite_min_imp = st.text_input("Limite Minimale (Impérial):", "0' 0\"")
            description = st.text_area("Description:")
            notes = st.text_area("Notes Internes:")

            submitted_add = st.form_submit_button("💾 Ajouter Article")
            if submitted_add:
                if not nom or not quantite_imp:
                    st.error("Le nom et la quantité sont obligatoires.")
                else:
                    is_valid_q, quantite_std = valider_mesure_saisie(quantite_imp)
                    is_valid_l, limite_std = valider_mesure_saisie(limite_min_imp)
                    if not is_valid_q:
                        st.error(f"Format de quantité invalide: {quantite_std}")
                    elif not is_valid_l:
                        st.error(f"Format de limite minimale invalide: {limite_std}")
                    else:
                        new_item = {
                            "id": new_id,
                            "nom": nom,
                            "type": type_art,
                            "quantite": quantite_std,
                            "conversion_metrique": convertir_imperial_vers_metrique(quantite_std),
                            "limite_minimale": limite_std,
                            "quantite_reservee": "0' 0\"",
                            "statut": "",
                            "description": description,
                            "note": notes,
                            "reservations": {},
                            "historique": [{"date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "action": "CRÉATION", "quantite": quantite_std, "note": "Création initiale"}],
                            "date_creation": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        mettre_a_jour_statut_stock(new_item)
                        inventory_data[str(new_id)] = new_item
                        if save_inventory_data(inventory_data):
                            st.success(f"Article '{nom}' (ID: {new_id}) ajouté avec succès!")
                            st.session_state.inventory_data = inventory_data
                            st.rerun()
                        else:
                            st.error("Erreur lors de la sauvegarde de l'article.")

    elif action_mode == "Voir Liste" or not inventory_data:
        st.subheader("📋 Liste des Articles en Inventaire")
        if not inventory_data:
            st.info("L'inventaire est vide. Cliquez sur 'Ajouter Article' dans les actions d'inventaire de la barre latérale pour commencer.")
        else:
            search_term_inv = st.text_input("Rechercher dans l'inventaire (nom, ID):", key="inv_search").lower()

            items_display_list = []
            for item_id, data in inventory_data.items():
                if search_term_inv:
                    if search_term_inv not in str(data.get("id", "")).lower() and \
                       search_term_inv not in data.get("nom", "").lower():
                        continue

                items_display_list.append({
                    "ID": data.get("id", item_id),
                    "Nom": data.get("nom", "N/A"),
                    "Type": data.get("type", "N/A"),
                    "Stock (Imp.)": data.get("quantite", "N/A"),
                    "Stock (Métr.)": f"{data.get('conversion_metrique', {}).get('valeur', 0):.3f} {data.get('conversion_metrique', {}).get('unite', 'm')}",
                    "Limite Min.": data.get("limite_minimale", "N/A"),
                    "Réservé": data.get("quantite_reservee", "N/A"),
                    "Statut": data.get("statut", "N/A")
                })

            if items_display_list:
                df_inventory = pd.DataFrame(items_display_list)
                st.dataframe(df_inventory, use_container_width=True)
            else:
                st.info("Aucun article ne correspond à votre recherche." if search_term_inv else "L'inventaire est vide.")

def show_crm_page():
    st.markdown("## 🤝 Gestion de la Relation Client (CRM)")
    gestionnaire_crm = st.session_state.gestionnaire_crm
    gestionnaire_projets = st.session_state.gestionnaire

    if 'crm_action' not in st.session_state:
        st.session_state.crm_action = None
    if 'crm_selected_id' not in st.session_state:
        st.session_state.crm_selected_id = None
    if 'crm_confirm_delete_contact_id' not in st.session_state:
        st.session_state.crm_confirm_delete_contact_id = None
    if 'crm_confirm_delete_entreprise_id' not in st.session_state:
        st.session_state.crm_confirm_delete_entreprise_id = None
    if 'crm_confirm_delete_interaction_id' not in st.session_state:
        st.session_state.crm_confirm_delete_interaction_id = None

    tab_contacts, tab_entreprises, tab_interactions = st.tabs([
        "👤 Contacts", "🏢 Entreprises", "💬 Interactions"
    ])

    with tab_contacts:
        render_crm_contacts_tab(gestionnaire_crm, gestionnaire_projets)

    with tab_entreprises:
        render_crm_entreprises_tab(gestionnaire_crm, gestionnaire_projets)

    with tab_interactions:
        render_crm_interactions_tab(gestionnaire_crm)

    action = st.session_state.get('crm_action')
    selected_id = st.session_state.get('crm_selected_id')

    if action == "create_contact":
        render_crm_contact_form(gestionnaire_crm, contact_data=None)
    elif action == "edit_contact" and selected_id:
        contact_data = gestionnaire_crm.get_contact_by_id(selected_id)
        render_crm_contact_form(gestionnaire_crm, contact_data=contact_data)
    elif action == "view_contact_details" and selected_id:
        contact_data = gestionnaire_crm.get_contact_by_id(selected_id)
        render_crm_contact_details(gestionnaire_crm, gestionnaire_projets, contact_data)
    elif action == "create_entreprise":
        render_crm_entreprise_form(gestionnaire_crm, entreprise_data=None)
    elif action == "edit_entreprise" and selected_id:
        entreprise_data = gestionnaire_crm.get_entreprise_by_id(selected_id)
        render_crm_entreprise_form(gestionnaire_crm, entreprise_data=entreprise_data)
    elif action == "view_entreprise_details" and selected_id:
        entreprise_data = gestionnaire_crm.get_entreprise_by_id(selected_id)
        render_crm_entreprise_details(gestionnaire_crm, gestionnaire_projets, entreprise_data)
    elif action == "create_interaction":
        render_crm_interaction_form(gestionnaire_crm, interaction_data=None)
    elif action == "edit_interaction" and selected_id:
        interaction_data = gestionnaire_crm.get_interaction_by_id(selected_id)
        render_crm_interaction_form(gestionnaire_crm, interaction_data=interaction_data)
    elif action == "view_interaction_details" and selected_id:
        interaction_data = gestionnaire_crm.get_interaction_by_id(selected_id)
        render_crm_interaction_details(gestionnaire_crm, gestionnaire_projets, interaction_data)

def show_employees_page():
    st.markdown("## 👥 Gestion des Employés")
    gestionnaire_employes = st.session_state.gestionnaire_employes
    gestionnaire_projets = st.session_state.gestionnaire
    
    if 'emp_action' not in st.session_state:
        st.session_state.emp_action = None
    if 'emp_selected_id' not in st.session_state:
        st.session_state.emp_selected_id = None
    if 'emp_confirm_delete_id' not in st.session_state:
        st.session_state.emp_confirm_delete_id = None
    
    tab_dashboard, tab_liste = st.tabs([
        "📊 Dashboard RH", "👥 Liste Employés"
    ])
    
    with tab_dashboard:
        render_employes_dashboard_tab(gestionnaire_employes, gestionnaire_projets)
    
    with tab_liste:
        render_employes_liste_tab(gestionnaire_employes, gestionnaire_projets)
    
    action = st.session_state.get('emp_action')
    selected_id = st.session_state.get('emp_selected_id')
    
    if action == "create_employe":
        render_employe_form(gestionnaire_employes, employe_data=None)
    elif action == "edit_employe" and selected_id:
        employe_data = gestionnaire_employes.get_employe_by_id(selected_id)
        render_employe_form(gestionnaire_employes, employe_data=employe_data)
    elif action == "view_employe_details" and selected_id:
        employe_data = gestionnaire_employes.get_employe_by_id(selected_id)
        render_employe_details(gestionnaire_employes, gestionnaire_projets, employe_data)

# Nouvelles fonctions manquantes pour la sidebar DG Inc.
def update_sidebar_with_work_centers():
    """Ajoute les statistiques des postes de travail dans la sidebar"""
    gestionnaire_postes = st.session_state.gestionnaire_postes
    stats_postes = gestionnaire_postes.get_statistiques_postes()
    
    if stats_postes['total_postes'] > 0:
        st.sidebar.markdown("---")
        st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>🏭 Aperçu Production</h3>", unsafe_allow_html=True)
        st.sidebar.metric("Production: Postes Actifs", stats_postes['total_postes'])
        st.sidebar.metric("Production: CNC/Robots", stats_postes['postes_cnc'] + stats_postes['postes_robotises'])
        
        # Graphique simple de répartition
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
            st.sidebar.markdown("<p style='font-size:0.8em;text-align:center;color:var(--text-color);'>Postes par département</p>", unsafe_allow_html=True)
            st.sidebar.plotly_chart(fig_sidebar, use_container_width=True)

# ----- Fonction Principale MODIFIÉE POUR MIGRATION IDS -----
def main():
    # Initialisation des gestionnaires
    if 'gestionnaire' not in st.session_state:
        st.session_state.gestionnaire = GestionnaireProjetIA()
    if 'gestionnaire_crm' not in st.session_state:
        st.session_state.gestionnaire_crm = GestionnaireCRM()
    if 'gestionnaire_employes' not in st.session_state:
        st.session_state.gestionnaire_employes = GestionnaireEmployes()
    
    # NOUVEAU : Gestionnaire des postes de travail
    if 'gestionnaire_postes' not in st.session_state:
        st.session_state.gestionnaire_postes = GestionnairePostes()
        # Intégrer les postes dans les projets existants au premier lancement
        if not hasattr(st.session_state, 'postes_integres'):
            st.session_state.gestionnaire = integrer_postes_dans_projets(
                st.session_state.gestionnaire, 
                st.session_state.gestionnaire_postes
            )
            st.session_state.postes_integres = True

    # NOUVEAU : Migration des IDs de projet au premier lancement
    if 'ids_migres' not in st.session_state:
        gestionnaire = st.session_state.gestionnaire
        if gestionnaire.projets and any(p.get('id', 0) < 10000 for p in gestionnaire.projets):
            nb_migres = migrer_ids_projets()
            st.success(f"✅ {nb_migres} projet(s) migré(s) vers les nouveaux IDs (10000+)")
            st.session_state.ids_migres = True

    session_defs = {
        'show_project_modal': False, 'selected_project': None,
        'show_create_project': False, 'show_edit_project': False,
        'edit_project_data': None, 'show_delete_confirmation': False,
        'delete_project_id': None, 'selected_date': datetime.now().date(),
        'welcome_seen': False,
        'inventory_data': load_inventory_data(),
        'inv_action_mode': "Voir Liste",
        'crm_action': None, 'crm_selected_id': None, 'crm_confirm_delete_contact_id': None,
        'crm_confirm_delete_entreprise_id': None, 'crm_confirm_delete_interaction_id': None,
        'emp_action': None, 'emp_selected_id': None, 'emp_confirm_delete_id': None,
        'competences_form': [],
        'gamme_generated': None, 'gamme_metadata': None  # NOUVEAU pour les gammes
    }
    for k, v_def in session_defs.items():
        if k not in st.session_state:
            st.session_state[k] = v_def

    apply_global_styles()

    st.markdown('<div class="main-title"><h1>🏭 ERP Production DG Inc.</h1></div>', unsafe_allow_html=True)

    if not st.session_state.welcome_seen:
        st.success("🎉 Bienvenue dans l'ERP Production DG Inc. ! Explorez les 61 postes de travail et les gammes de fabrication.")
        st.session_state.welcome_seen = True

    st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>🧭 Navigation</h3>", unsafe_allow_html=True)

    # NOUVEAU MENU avec postes de travail
    pages = {
        "🏠 Tableau de Bord": "dashboard",
        "📋 Liste des Projets": "liste",
        "🤝 CRM": "crm_page",
        "👥 Employés": "employees_page",
        "🏭 Postes de Travail": "work_centers_page",        # NOUVEAU
        "⚙️ Gammes Fabrication": "manufacturing_routes",    # NOUVEAU
        "📊 Capacité Production": "capacity_analysis",      # NOUVEAU
        "📦 Gestion Inventaire": "inventory_management",
        "📊 Nomenclature (BOM)": "bom",
        "🛠️ Itinéraire": "routing",
        "📈 Vue Gantt": "gantt",
        "📅 Calendrier": "calendrier",
        "🔄 Kanban": "kanban",
    }
    
    sel_page_key = st.sidebar.radio("Menu Principal:", list(pages.keys()), key="main_nav_radio")
    page_to_show_val = pages[sel_page_key]

    if page_to_show_val == "inventory_management":
        st.sidebar.markdown("---")
        st.sidebar.markdown("<h4 style='color:var(--primary-color-darker);'>Actions Inventaire</h4>", unsafe_allow_html=True)
        st.session_state.inv_action_mode = st.sidebar.radio(
            "Mode:",
            ["Voir Liste", "Ajouter Article", "Modifier Article"],
            key="inv_action_mode_selector",
            index=["Voir Liste", "Ajouter Article", "Modifier Article"].index(st.session_state.inv_action_mode)
        )

    st.sidebar.markdown("---")

    # Statistiques d'inventaire
    current_inventory_data = st.session_state.inventory_data
    if current_inventory_data:
        st.sidebar.metric("Inventaire: Total Articles", len(current_inventory_data))
        items_low_stock_count = sum(1 for item_id, item_data in current_inventory_data.items() if isinstance(item_data, dict) and item_data.get("statut") in ["FAIBLE", "CRITIQUE", "ÉPUISÉ"])
        st.sidebar.metric("Inventaire: Stock Bas/Critique", items_low_stock_count)

    # NOUVEAU : Statistiques des postes de travail dans la sidebar
    update_sidebar_with_work_centers()

    # Statistiques projets
    stats_sb_projects = get_project_statistics(st.session_state.gestionnaire)
    if stats_sb_projects['total'] > 0:
        st.sidebar.markdown("---")
        st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>📊 Aperçu Projets</h3>", unsafe_allow_html=True)
        st.sidebar.metric("Projets: Total", stats_sb_projects['total'])
        st.sidebar.metric("Projets: Actifs", stats_sb_projects['projets_actifs'])
        if stats_sb_projects['ca_total'] > 0:
            st.sidebar.metric("Projets: CA Estimé", format_currency(stats_sb_projects['ca_total']))

    # Statistiques CRM
    crm_manager_sb = st.session_state.gestionnaire_crm
    if crm_manager_sb.contacts or crm_manager_sb.entreprises:
        st.sidebar.markdown("---")
        st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>📊 Aperçu CRM</h3>", unsafe_allow_html=True)
        st.sidebar.metric("CRM: Total Contacts", len(crm_manager_sb.contacts))
        st.sidebar.metric("CRM: Total Entreprises", len(crm_manager_sb.entreprises))

    # Statistiques RH
    emp_manager_sb = st.session_state.gestionnaire_employes
    if emp_manager_sb.employes:
        st.sidebar.markdown("---")
        st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>📊 Aperçu RH</h3>", unsafe_allow_html=True)
        st.sidebar.metric("RH: Total Employés", len(emp_manager_sb.employes))
        employes_actifs = len([emp for emp in emp_manager_sb.employes if emp.get('statut') == 'ACTIF'])
        st.sidebar.metric("RH: Employés Actifs", employes_actifs)

    st.sidebar.markdown("---")
    st.sidebar.markdown("<div style='background:var(--primary-color-lighter);padding:10px;border-radius:8px;text-align:center;'><p style='color:var(--primary-color-darkest);font-size:12px;margin:0;'>🏭 ERP Production DG Inc.</p></div>", unsafe_allow_html=True)

    # NOUVELLES PAGES dans le switch
    if page_to_show_val == "dashboard":
        show_dashboard()
    elif page_to_show_val == "liste":
        show_liste_projets()
    elif page_to_show_val == "crm_page":
        show_crm_page()
    elif page_to_show_val == "employees_page":
        show_employees_page()
    elif page_to_show_val == "work_centers_page":          # NOUVEAU
        show_work_centers_page()
    elif page_to_show_val == "manufacturing_routes":       # NOUVEAU
        show_manufacturing_routes_page()
    elif page_to_show_val == "capacity_analysis":          # NOUVEAU
        show_capacity_analysis_page()
    elif page_to_show_val == "inventory_management":
        show_inventory_management_page()
    elif page_to_show_val == "bom":
        show_nomenclature()
    elif page_to_show_val == "routing":
        show_itineraire()
    elif page_to_show_val == "gantt":
        show_gantt()
    elif page_to_show_val == "calendrier":
        show_calendrier()
    elif page_to_show_val == "kanban":
        show_kanban()

    if st.session_state.get('show_project_modal'):
        show_project_modal()

def show_footer():
    st.markdown("---")
    st.markdown("<div style='text-align:center;color:var(--text-color-muted);padding:20px 0;font-size:0.9em;'><p>🏭 ERP Production DG Inc. - 61 Postes de Travail • CRM • Inventaire</p><p>Transformé en véritable industrie 4.0</p></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main()
        show_footer()
    except Exception as e_main:
        st.error(f"Une erreur majeure est survenue dans l'application: {str(e_main)}")
        st.info("Veuillez essayer de rafraîchir la page ou de redémarrer l'application.")
        import traceback
        st.code(traceback.format_exc())

# --- END OF FILE app.py ---
