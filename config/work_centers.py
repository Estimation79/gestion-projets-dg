# config/work_centers.py
"""
Configuration des 61 postes de travail DG Inc.
"""

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
