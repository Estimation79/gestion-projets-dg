# models/work_centers.py
"""
Gestionnaire des postes de travail pour l'ERP Production DG Inc.
"""

import random
from config.work_centers import WORK_CENTERS_DG_INC, CATEGORIES_POSTES_TRAVAIL


class GestionnairePostes:
    """Gestionnaire pour les 61 postes de travail DG Inc."""
    
    def __init__(self):
        self.postes = WORK_CENTERS_DG_INC
        self.gammes_types = self.initialiser_gammes_types()
    
    def initialiser_gammes_types(self):
        """Initialise les gammes de fabrication types"""
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
        """Récupère un poste par son nom"""
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
        "date_generation": f"{random.randint(2024, 2025)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
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
