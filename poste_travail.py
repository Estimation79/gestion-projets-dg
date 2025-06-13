# postes_travail.py - Module de gestion des postes de travail DG Inc.

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import json

# --- POSTES DE TRAVAIL DG INC. ---
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