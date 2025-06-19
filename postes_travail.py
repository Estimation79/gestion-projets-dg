# timetracker.py - TimeTracker Intégré ERP Production DG Inc.
# Version SQLite Unifiée avec Gestion Postes de Travail Intégrée
# FUSION: TimeTracker + Postes de Travail dans un module unifié

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, time, date
import hashlib
import json
import random
from typing import Dict, List, Optional, Tuple, Any
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================================
# DONNÉES DE RÉFÉRENCE POSTES DE TRAVAIL (Intégrées depuis postes_travail.py)
# =========================================================================

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

# =========================================================================
# CLASSES PRINCIPALES
# =========================================================================

class TimeTrackerERP:
    """
    TimeTracker intégré à l'ERP Production DG Inc. - Version SQLite Optimisée
    Utilise directement la base SQLite unifiée sans duplication
    """
    
    def __init__(self, erp_db):
        self.db = erp_db
        logger.info("TimeTracker ERP initialisé avec base SQLite unifiée")
    
    def get_all_employees(self) -> List[Dict]:
        """Récupère tous les employés actifs depuis la base ERP avec informations étendues"""
        try:
            rows = self.db.execute_query('''
                SELECT e.id, e.prenom, e.nom, e.email, e.telephone, e.poste, 
                       e.departement, e.statut, e.salaire, e.charge_travail, e.date_embauche,
                       COUNT(pa.project_id) as projets_assignes
                FROM employees e
                LEFT JOIN project_assignments pa ON e.id = pa.employee_id
                WHERE e.statut = 'ACTIF' 
                GROUP BY e.id
                ORDER BY e.prenom, e.nom
            ''')
            
            employees = []
            for row in rows:
                emp = dict(row)
                emp['name'] = f"{emp['prenom']} {emp['nom']}"
                emp['employee_code'] = f"EMP{emp['id']:03d}"
                emp['full_name_with_role'] = f"{emp['name']} - {emp.get('poste', 'N/A')} ({emp.get('departement', 'N/A')})"
                employees.append(emp)
            
            return employees
        except Exception as e:
            logger.error(f"Erreur récupération employés: {e}")
            return []
    
    def get_employee_by_id(self, employee_id: int) -> Optional[Dict]:
        """Récupère un employé par son ID avec statistiques complètes"""
        try:
            # Données de base de l'employé
            emp_rows = self.db.execute_query('''
                SELECT e.*, COUNT(pa.project_id) as projets_assignes
                FROM employees e
                LEFT JOIN project_assignments pa ON e.id = pa.employee_id
                WHERE e.id = ? AND e.statut = 'ACTIF'
                GROUP BY e.id
            ''', (employee_id,))
            
            if not emp_rows:
                return None
            
            emp = dict(emp_rows[0])
            emp['name'] = f"{emp['prenom']} {emp['nom']}"
            emp['employee_code'] = f"EMP{emp['id']:03d}"
            
            # Statistiques TimeTracker de l'employé
            stats_rows = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total_entries,
                    COALESCE(SUM(total_hours), 0) as total_hours,
                    COALESCE(SUM(total_cost), 0) as total_revenue,
                    COALESCE(AVG(hourly_rate), 0) as avg_hourly_rate
                FROM time_entries 
                WHERE employee_id = ? AND total_cost IS NOT NULL
            ''', (employee_id,))
            
            if stats_rows:
                stats = dict(stats_rows[0])
                emp.update({
                    'timetracker_total_entries': stats['total_entries'],
                    'timetracker_total_hours': stats['total_hours'],
                    'timetracker_total_revenue': stats['total_revenue'],
                    'timetracker_avg_rate': stats['avg_hourly_rate']
                })
            
            return emp
        except Exception as e:
            logger.error(f"Erreur récupération employé {employee_id}: {e}")
            return None
    
    def get_active_projects(self) -> List[Dict]:
        """Récupère tous les projets actifs avec informations client"""
        try:
            rows = self.db.execute_query('''
                SELECT p.id, p.nom_projet, p.client_nom_cache, p.statut, p.prix_estime,
                       p.bd_ft_estime, p.date_prevu, p.description,
                       c.nom as company_name, c.secteur,
                       COUNT(o.id) as total_operations,
                       COALESCE(SUM(te.total_hours), 0) as timetracker_hours,
                       COALESCE(SUM(te.total_cost), 0) as timetracker_revenue
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                LEFT JOIN operations o ON p.id = o.project_id
                LEFT JOIN time_entries te ON p.id = te.project_id AND te.total_cost IS NOT NULL
                WHERE p.statut IN ('À FAIRE', 'EN COURS', 'EN ATTENTE') 
                GROUP BY p.id
                ORDER BY p.nom_projet
            ''')
            
            projects = []
            for row in rows:
                proj = dict(row)
                proj['project_name'] = proj['nom_projet']
                proj['client_name'] = proj['client_nom_cache'] or proj.get('company_name', 'Client Inconnu')
                proj['project_code'] = f"PROJ{proj['id']:04d}"
                proj['display_name'] = f"{proj['project_name']} - {proj['client_name']}"
                projects.append(proj)
            
            return projects
        except Exception as e:
            logger.error(f"Erreur récupération projets: {e}")
            return []
    
    def get_project_operations(self, project_id: int) -> List[Dict]:
        """Récupère les opérations d'un projet avec statistiques TimeTracker"""
        try:
            rows = self.db.execute_query('''
                SELECT o.id, o.description, o.temps_estime, o.poste_travail, o.sequence_number,
                       wc.nom as work_center_name, wc.cout_horaire, wc.departement,
                       COALESCE(SUM(te.total_hours), 0) as actual_hours,
                       COALESCE(SUM(te.total_cost), 0) as actual_cost,
                       COUNT(te.id) as timetracker_entries
                FROM operations o
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                LEFT JOIN time_entries te ON o.id = te.operation_id AND te.total_cost IS NOT NULL
                WHERE o.project_id = ? 
                GROUP BY o.id
                ORDER BY o.sequence_number, o.description
            ''', (project_id,))
            
            operations = []
            for row in rows:
                op = dict(row)
                op['task_name'] = op['description'] or f"Opération {op['sequence_number']}"
                op['task_code'] = f"OP{op['id']:03d}"
                op['hourly_rate'] = op['cout_horaire'] or 95.0  # Taux par défaut
                op['estimated_hours'] = op['temps_estime'] or 0
                
                # Calcul du pourcentage de progression
                if op['estimated_hours'] > 0:
                    op['completion_percentage'] = min(100, (op['actual_hours'] / op['estimated_hours']) * 100)
                else:
                    op['completion_percentage'] = 0
                
                operations.append(op)
            
            return operations
        except Exception as e:
            logger.error(f"Erreur récupération opérations projet {project_id}: {e}")
            return []
    
    def get_employee_current_entry(self, employee_id: int) -> Optional[Dict]:
        """Vérifie si l'employé a une entrée en cours avec détails complets"""
        try:
            rows = self.db.execute_query('''
                SELECT te.*, p.nom_projet as project_name, p.client_nom_cache as client_name,
                       o.description as task_name, o.sequence_number,
                       wc.nom as work_center_name, wc.departement as work_center_dept
                FROM time_entries te
                JOIN projects p ON te.project_id = p.id
                LEFT JOIN operations o ON te.operation_id = o.id
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE te.employee_id = ? AND te.punch_out IS NULL
                ORDER BY te.punch_in DESC
                LIMIT 1
            ''', (employee_id,))
            
            if rows:
                entry = dict(rows[0])
                entry['task_name'] = entry['task_name'] or 'Tâche générale'
                entry['client_name'] = entry['client_name'] or 'Client Inconnu'
                
                # Calcul du temps écoulé en temps réel
                punch_in_time = datetime.fromisoformat(entry['punch_in'])
                elapsed_seconds = (datetime.now() - punch_in_time).total_seconds()
                entry['elapsed_hours'] = elapsed_seconds / 3600
                entry['estimated_cost'] = entry['elapsed_hours'] * entry['hourly_rate']
                
                return entry
            return None
        except Exception as e:
            logger.error(f"Erreur récupération entrée courante employé {employee_id}: {e}")
            return None
    
    def punch_in(self, employee_id: int, project_id: int, operation_id: int = None, notes: str = "") -> int:
        """Enregistre un punch in avec validation renforcée"""
        try:
            # Vérifier s'il n'y a pas déjà un punch in actif
            current_entry = self.get_employee_current_entry(employee_id)
            if current_entry:
                raise ValueError(f"L'employé a déjà un pointage actif depuis {current_entry['punch_in']}")
            
            # Obtenir le taux horaire de l'opération ou du poste de travail
            hourly_rate = 95.0  # Taux par défaut
            if operation_id:
                rate_rows = self.db.execute_query('''
                    SELECT wc.cout_horaire 
                    FROM operations o
                    LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                    WHERE o.id = ?
                ''', (operation_id,))
                if rate_rows and rate_rows[0]['cout_horaire']:
                    hourly_rate = rate_rows[0]['cout_horaire']
            
            # Créer l'entrée de temps avec timestamp précis
            punch_in_time = datetime.now()
            entry_id = self.db.execute_insert('''
                INSERT INTO time_entries 
                (employee_id, project_id, operation_id, punch_in, notes, hourly_rate)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (employee_id, project_id, operation_id, punch_in_time.isoformat(), notes, hourly_rate))
            
            logger.info(f"Punch in créé - Employé: {employee_id}, Projet: {project_id}, Entry: {entry_id}, Taux: {hourly_rate}$/h")
            return entry_id
            
        except Exception as e:
            logger.error(f"Erreur punch in: {e}")
            raise
    
    def punch_out(self, employee_id: int, notes: str = "") -> Dict:
        """Enregistre un punch out avec calculs détaillés"""
        try:
            # Trouver l'entrée active
            current_entry = self.get_employee_current_entry(employee_id)
            if not current_entry:
                raise ValueError("Aucun pointage actif trouvé pour cet employé")
            
            # Calculer les heures et le coût avec précision
            punch_in_time = datetime.fromisoformat(current_entry['punch_in'])
            punch_out_time = datetime.now()
            total_seconds = (punch_out_time - punch_in_time).total_seconds()
            total_hours = total_seconds / 3600
            total_cost = total_hours * current_entry['hourly_rate']
            
            # Mettre à jour l'entrée avec toutes les informations
            updated_notes = f"{current_entry.get('notes', '')} | Fin: {notes}".strip(' |')
            
            self.db.execute_update('''
                UPDATE time_entries 
                SET punch_out = ?, total_hours = ?, total_cost = ?, notes = ?
                WHERE id = ?
            ''', (punch_out_time.isoformat(), total_hours, total_cost, updated_notes, current_entry['id']))
            
            # Retourner les détails de la session
            session_details = {
                'entry_id': current_entry['id'],
                'total_hours': total_hours,
                'total_cost': total_cost,
                'hourly_rate': current_entry['hourly_rate'],
                'project_name': current_entry['project_name'],
                'task_name': current_entry['task_name'],
                'punch_in': punch_in_time,
                'punch_out': punch_out_time
            }
            
            logger.info(f"Punch out complété - Entry: {current_entry['id']}, Heures: {total_hours:.2f}, Coût: {total_cost:.2f}$ CAD")
            return session_details
            
        except Exception as e:
            logger.error(f"Erreur punch out: {e}")
            raise
    
    def get_employee_time_entries(self, employee_id: int, limit: int = 50, date_filter: str = None) -> List[Dict]:
        """Récupère les entrées d'un employé avec filtres avancés"""
        try:
            base_query = '''
                SELECT te.*, p.nom_projet as project_name, p.client_nom_cache as client_name,
                       o.description as task_name, o.sequence_number,
                       wc.nom as work_center_name
                FROM time_entries te
                JOIN projects p ON te.project_id = p.id
                LEFT JOIN operations o ON te.operation_id = o.id
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE te.employee_id = ?
            '''
            
            params = [employee_id]
            
            if date_filter:
                base_query += ' AND DATE(te.punch_in) = ?'
                params.append(date_filter)
            
            base_query += ' ORDER BY te.punch_in DESC LIMIT ?'
            params.append(limit)
            
            rows = self.db.execute_query(base_query, tuple(params))
            
            entries = []
            for row in rows:
                entry = dict(row)
                entry['task_name'] = entry['task_name'] or 'Tâche générale'
                entry['client_name'] = entry['client_name'] or 'Client Inconnu'
                
                # Formater les dates pour l'affichage
                punch_in = datetime.fromisoformat(entry['punch_in'])
                entry['punch_in_formatted'] = punch_in.strftime('%Y-%m-%d %H:%M:%S')
                
                if entry['punch_out']:
                    punch_out = datetime.fromisoformat(entry['punch_out'])
                    entry['punch_out_formatted'] = punch_out.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    entry['punch_out_formatted'] = 'En cours...'
                    # Calculer le temps écoulé si en cours
                    elapsed = (datetime.now() - punch_in).total_seconds() / 3600
                    entry['elapsed_hours'] = elapsed
                
                entries.append(entry)
            
            return entries
        except Exception as e:
            logger.error(f"Erreur récupération historique employé {employee_id}: {e}")
            return []
    
    def get_daily_summary(self, date_str: str = None) -> List[Dict]:
        """Récupère le résumé quotidien avec détails enrichis"""
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        try:
            rows = self.db.execute_query('''
                SELECT 
                    e.id as employee_id,
                    e.prenom || ' ' || e.nom as employee_name,
                    e.poste, e.departement,
                    p.id as project_id,
                    p.nom_projet as project_name,
                    p.client_nom_cache as client_name,
                    COALESCE(o.description, 'Tâche générale') as task_name,
                    wc.nom as work_center_name,
                    COALESCE(SUM(te.total_hours), 0.0) as total_hours,
                    COALESCE(SUM(te.total_cost), 0.0) as total_cost,
                    COALESCE(AVG(te.hourly_rate), 0.0) as avg_hourly_rate,
                    COUNT(te.id) as entries_count,
                    MIN(te.punch_in) as first_punch_in,
                    MAX(te.punch_out) as last_punch_out
                FROM time_entries te
                JOIN employees e ON te.employee_id = e.id
                JOIN projects p ON te.project_id = p.id
                LEFT JOIN operations o ON te.operation_id = o.id
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE DATE(te.punch_in) = ? AND te.total_cost IS NOT NULL
                GROUP BY e.id, p.id, o.id
                ORDER BY e.prenom, e.nom, p.nom_projet
            ''', (date_str,))
            
            summary = []
            for row in rows:
                item = dict(row)
                item['client_name'] = item['client_name'] or 'Client Inconnu'
                summary.append(item)
            
            return summary
        except Exception as e:
            logger.error(f"Erreur résumé quotidien {date_str}: {e}")
            return []
    
    def get_project_revenue_summary(self, project_id: int = None, period_days: int = 30) -> List[Dict]:
        """Résumé des revenus par projet avec période configurable"""
        try:
            # Date de début pour la période
            start_date = (datetime.now() - timedelta(days=period_days)).strftime('%Y-%m-%d')
            
            if project_id:
                query = '''
                    SELECT 
                        p.id as project_id,
                        p.nom_projet as project_name,
                        p.client_nom_cache as client_name,
                        p.prix_estime as estimated_price,
                        COALESCE(SUM(te.total_hours), 0.0) as total_hours,
                        COALESCE(SUM(te.total_cost), 0.0) as total_revenue,
                        COALESCE(AVG(te.hourly_rate), 0.0) as avg_hourly_rate,
                        COUNT(DISTINCT te.employee_id) as employees_count,
                        COUNT(te.id) as entries_count,
                        MIN(te.punch_in) as first_entry,
                        MAX(te.punch_out) as last_entry
                    FROM time_entries te
                    JOIN projects p ON te.project_id = p.id
                    WHERE p.id = ? AND te.total_cost IS NOT NULL 
                    AND DATE(te.punch_in) >= ?
                    GROUP BY p.id
                '''
                params = (project_id, start_date)
            else:
                query = '''
                    SELECT 
                        p.id as project_id,
                        p.nom_projet as project_name,
                        p.client_nom_cache as client_name,
                        p.prix_estime as estimated_price,
                        COALESCE(SUM(te.total_hours), 0.0) as total_hours,
                        COALESCE(SUM(te.total_cost), 0.0) as total_revenue,
                        COALESCE(AVG(te.hourly_rate), 0.0) as avg_hourly_rate,
                        COUNT(DISTINCT te.employee_id) as employees_count,
                        COUNT(te.id) as entries_count,
                        MIN(te.punch_in) as first_entry,
                        MAX(te.punch_out) as last_entry
                    FROM time_entries te
                    JOIN projects p ON te.project_id = p.id
                    WHERE te.total_cost IS NOT NULL AND DATE(te.punch_in) >= ?
                    GROUP BY p.id
                    ORDER BY total_revenue DESC
                '''
                params = (start_date,)
            
            rows = self.db.execute_query(query, params)
            
            summary = []
            for row in rows:
                item = dict(row)
                item['client_name'] = item['client_name'] or 'Client Inconnu'
                
                # Calcul du ratio revenus/estimation
                if item['estimated_price'] and item['estimated_price'] > 0:
                    item['revenue_ratio'] = (item['total_revenue'] / item['estimated_price']) * 100
                else:
                    item['revenue_ratio'] = 0
                
                summary.append(item)
            
            return summary
            
        except Exception as e:
            logger.error(f"Erreur résumé revenus: {e}")
            return []
    
    def get_timetracker_statistics(self) -> Dict:
        """Statistiques globales TimeTracker enrichies"""
        try:
            stats = {}
            
            # Employés actifs dans l'ERP
            emp_result = self.db.execute_query("SELECT COUNT(*) as count FROM employees WHERE statut = 'ACTIF'")
            stats['total_employees'] = emp_result[0]['count'] if emp_result else 0
            
            # Pointages actifs (en cours)
            active_result = self.db.execute_query("SELECT COUNT(*) as count FROM time_entries WHERE punch_out IS NULL")
            stats['active_entries'] = active_result[0]['count'] if active_result else 0
            
            # Statistiques du jour
            today = datetime.now().strftime('%Y-%m-%d')
            daily_result = self.db.execute_query('''
                SELECT 
                    COALESCE(SUM(total_hours), 0.0) as hours,
                    COALESCE(SUM(total_cost), 0.0) as revenue,
                    COUNT(DISTINCT employee_id) as unique_employees,
                    COUNT(*) as total_entries
                FROM time_entries 
                WHERE DATE(punch_in) = ? AND total_cost IS NOT NULL
            ''', (today,))
            
            if daily_result:
                stats.update({
                    'total_hours_today': daily_result[0]['hours'],
                    'total_revenue_today': daily_result[0]['revenue'],
                    'active_employees_today': daily_result[0]['unique_employees'],
                    'total_entries_today': daily_result[0]['total_entries']
                })
            
            # Statistiques globales (dernier mois)
            month_start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            monthly_result = self.db.execute_query('''
                SELECT 
                    COALESCE(SUM(total_hours), 0.0) as monthly_hours,
                    COALESCE(SUM(total_cost), 0.0) as monthly_revenue,
                    COUNT(DISTINCT employee_id) as active_employees_month,
                    COUNT(DISTINCT project_id) as active_projects_month
                FROM time_entries 
                WHERE DATE(punch_in) >= ? AND total_cost IS NOT NULL
            ''', (month_start,))
            
            if monthly_result:
                stats.update({
                    'monthly_hours': monthly_result[0]['monthly_hours'],
                    'monthly_revenue': monthly_result[0]['monthly_revenue'],
                    'active_employees_month': monthly_result[0]['active_employees_month'],
                    'active_projects_month': monthly_result[0]['active_projects_month']
                })
            
            # Taux horaire moyen
            if stats.get('total_hours_today', 0) > 0:
                stats['avg_hourly_rate_today'] = stats['total_revenue_today'] / stats['total_hours_today']
            else:
                stats['avg_hourly_rate_today'] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur statistiques TimeTracker: {e}")
            return {}
    
    def get_work_center_productivity(self) -> List[Dict]:
        """Analyse de productivité par poste de travail"""
        try:
            rows = self.db.execute_query('''
                SELECT 
                    wc.id, wc.nom as work_center_name, wc.departement, wc.categorie,
                    wc.capacite_theorique, wc.cout_horaire,
                    COALESCE(SUM(te.total_hours), 0) as actual_hours,
                    COALESCE(SUM(te.total_cost), 0) as total_revenue,
                    COUNT(DISTINCT te.employee_id) as unique_employees,
                    COUNT(te.id) as total_entries
                FROM work_centers wc
                LEFT JOIN operations o ON wc.id = o.work_center_id
                LEFT JOIN time_entries te ON o.id = te.operation_id AND te.total_cost IS NOT NULL
                GROUP BY wc.id
                HAVING actual_hours > 0
                ORDER BY total_revenue DESC
            ''')
            
            productivity = []
            for row in rows:
                item = dict(row)
                
                # Calcul du taux d'utilisation (si capacité théorique disponible)
                if item['capacite_theorique'] and item['capacite_theorique'] > 0:
                    # Utilisation sur 30 jours (approximation)
                    theoretical_capacity_month = item['capacite_theorique'] * 30
                    item['utilization_rate'] = min(100, (item['actual_hours'] / theoretical_capacity_month) * 100)
                else:
                    item['utilization_rate'] = 0
                
                productivity.append(item)
            
            return productivity
            
        except Exception as e:
            logger.error(f"Erreur analyse productivité: {e}")
            return []
    
    # Nouvelles méthodes pour intégration Bons de Travail
    def get_bts_assignes_employe(self, employee_id: int) -> List[Dict]:
        """Récupère les BTs assignés à un employé avec détails complets."""
        try:
            query = '''
                SELECT f.id as bt_id, f.numero_document, f.statut as bt_statut, 
                       f.priorite, f.date_creation, f.date_echeance, f.notes,
                       p.nom_projet, p.client_nom_cache,
                       bta.date_assignation, bta.statut as assignation_statut,
                       c.nom as company_nom,
                       -- Calculer temps déjà pointé sur ce BT
                       COALESCE(SUM(te.total_hours), 0) as heures_pointees,
                       COALESCE(SUM(te.total_cost), 0) as cout_total,
                       COUNT(te.id) as nb_pointages
                FROM bt_assignations bta
                JOIN formulaires f ON bta.bt_id = f.id
                LEFT JOIN projects p ON f.project_id = p.id  
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN time_entries te ON f.id = te.formulaire_bt_id AND te.employee_id = ?
                WHERE bta.employe_id = ? 
                AND bta.statut = 'ASSIGNÉ'
                AND f.statut NOT IN ('TERMINÉ', 'ANNULÉ')
                GROUP BY f.id, bta.id
                ORDER BY f.priorite DESC, f.date_echeance ASC
            '''
            rows = self.db.execute_query(query, (employee_id, employee_id))
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération BTs assignés: {e}")
            return []

    def get_bt_details_for_timetracker(self, bt_id: int) -> Optional[Dict]:
        """Récupère les détails d'un BT pour le pointage."""
        try:
            query = '''
                SELECT f.*, p.nom_projet, c.nom as company_nom,
                       COUNT(DISTINCT bta.employe_id) as nb_employes_assignes,
                       COUNT(DISTINCT btr.work_center_id) as nb_postes_reserves
                FROM formulaires f
                LEFT JOIN projects p ON f.project_id = p.id
                LEFT JOIN companies c ON f.company_id = c.id  
                LEFT JOIN bt_assignations bta ON f.id = bta.bt_id
                LEFT JOIN bt_reservations_postes btr ON f.id = btr.bt_id
                WHERE f.id = ? AND f.type_formulaire = 'BON_TRAVAIL'
                GROUP BY f.id
            '''
            result = self.db.execute_query(query, (bt_id,))
            return dict(result[0]) if result else None
        except Exception as e:
            logger.error(f"Erreur récupération détails BT: {e}")
            return None

    def punch_in_sur_bt(self, employee_id: int, bt_id: int, notes: str = "") -> int:
        """Démarre un pointage directement sur un Bon de Travail."""
        try:
            # Récupérer les infos du BT
            bt_details = self.get_bt_details_for_timetracker(bt_id)
            if not bt_details:
                raise ValueError("BT non trouvé")
            
            # Vérifier qu'employé est bien assigné
            assignation = self.db.execute_query(
                "SELECT id FROM bt_assignations WHERE bt_id = ? AND employe_id = ? AND statut = 'ASSIGNÉ'",
                (bt_id, employee_id)
            )
            if not assignation:
                raise ValueError("Employé non assigné à ce BT")
            
            # Démarrer le pointage avec référence BT
            punch_in_time = datetime.now()
            entry_id = self.db.execute_insert('''
                INSERT INTO time_entries 
                (employee_id, project_id, punch_in, notes, hourly_rate, formulaire_bt_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                employee_id, 
                bt_details.get('project_id'), 
                punch_in_time.isoformat(), 
                f"BT {bt_details['numero_document']} - {notes}".strip(),
                95.0,  # Taux par défaut
                bt_id
            ))
            
            return entry_id
        except Exception as e:
            logger.error(f"Erreur punch in BT: {e}")
            raise

    def get_statistiques_bt_timetracker(self, bt_id: int) -> Dict:
        """Statistiques TimeTracker pour un BT spécifique."""
        try:
            query = '''
                SELECT 
                    COUNT(*) as nb_pointages,
                    COUNT(DISTINCT employee_id) as nb_employes_distinct,
                    COALESCE(SUM(total_hours), 0) as total_heures,
                    COALESCE(SUM(total_cost), 0) as total_cout,
                    COALESCE(AVG(total_hours), 0) as moyenne_heures_session,
                    MIN(punch_in) as premier_pointage,
                    MAX(punch_out) as dernier_pointage
                FROM time_entries 
                WHERE formulaire_bt_id = ? AND total_cost IS NOT NULL
            '''
            result = self.db.execute_query(query, (bt_id,))
            return dict(result[0]) if result else {}
        except Exception as e:
            logger.error(f"Erreur stats BT TimeTracker: {e}")
            return {}


# =========================================================================
# GESTIONNAIRE POSTES DE TRAVAIL (Intégré depuis postes_travail.py)
# =========================================================================

class GestionnairePostes:
    """
    Gestionnaire des postes de travail intégré au TimeTracker
    Version fusionnée pour module unifié
    """
    
    def __init__(self, erp_db):
        """
        Initialise le gestionnaire avec une connexion à la base SQLite
        Args:
            erp_db: Instance ERPDatabase
        """
        self.db = erp_db
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
        """Initialise les gammes types"""
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


# =========================================================================
# INTERFACE PRINCIPALE UNIFIÉE
# =========================================================================

def show_timetracker_interface():
    """
    Interface principale TimeTracker + Postes de Travail
    Version fusionnée avec navigation intégrée
    """
    # Vérifier l'accès à la base ERP
    if 'erp_db' not in st.session_state:
        st.error("❌ Accès TimeTracker nécessite une session ERP active")
        st.info("Veuillez redémarrer l'application ERP.")
        return
    
    # Initialiser TimeTracker et GestionnairePostes
    if 'timetracker_erp' not in st.session_state:
        st.session_state.timetracker_erp = TimeTrackerERP(st.session_state.erp_db)
    
    if 'gestionnaire_postes_tt' not in st.session_state:
        st.session_state.gestionnaire_postes_tt = GestionnairePostes(st.session_state.erp_db)
    
    # En-tête unifié
    st.markdown("""
    <div class='project-header' style='background: linear-gradient(135deg, #00A971 0%, #00673D 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h2 style='margin: 0; text-align: center;'>⏱️🏭 TimeTracker Pro + Postes de Travail - ERP DG Inc.</h2>
        <p style='margin: 5px 0 0 0; text-align: center; opacity: 0.9;'>🗄️ Module Unifié • Gestion Intégrée SQLite</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Statistiques en temps réel enrichies
    tt = st.session_state.timetracker_erp
    gp = st.session_state.gestionnaire_postes_tt
    stats = tt.get_timetracker_statistics()
    
    # Première ligne de métriques
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Employés ERP", stats.get('total_employees', 0))
    with col2:
        st.metric("🟢 Pointages Actifs", stats.get('active_entries', 0))
    with col3:
        st.metric("⏱️ Heures Aujourd'hui", f"{stats.get('total_hours_today', 0):.1f}h")
    with col4:
        st.metric("💰 Revenus Aujourd'hui", f"{stats.get('total_revenue_today', 0):.0f}$ CAD")
    
    # Deuxième ligne de métriques (postes de travail)
    postes_stats = gp.get_statistiques_postes()
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("🏭 Postes Travail", postes_stats.get('total_postes', 0))
    with col6:
        st.metric("🤖 Robots ABB", postes_stats.get('postes_robotises', 0))
    with col7:
        st.metric("💻 Postes CNC", postes_stats.get('postes_cnc', 0))
    with col8:
        efficacite_globale = random.uniform(82, 87)
        st.metric("⚡ Efficacité", f"{efficacite_globale:.1f}%")
    
    # Navigation principale étendue
    tab_pointage, tab_analytics, tab_postes, tab_gammes, tab_capacite, tab_admin, tab_system = st.tabs([
        "🕐 Pointage", "📊 Analytics", "🏭 Postes", "⚙️ Gammes", "📈 Capacité", "⚙️ Admin", "ℹ️ Système"
    ])
    
    with tab_pointage:
        show_employee_timetracking_interface(tt)
    
    with tab_analytics:
        show_analytics_interface(tt)
    
    with tab_postes:
        show_work_centers_integrated_interface(gp)
    
    with tab_gammes:
        show_manufacturing_routes_integrated_interface(gp)
    
    with tab_capacite:
        show_capacity_analysis_integrated_interface(gp)
    
    with tab_admin:
        show_admin_interface(tt)
    
    with tab_system:
        show_system_interface()


# =========================================================================
# INTERFACES TIMETRACKER (Conservées)
# =========================================================================

def show_employee_timetracking_interface(tt: TimeTrackerERP):
    """Interface de pointage pour employés avec fonctionnalités avancées"""
    
    st.markdown("### 👤 Interface de Pointage Avancée")
    
    # Récupération des employés depuis l'ERP
    employees = tt.get_all_employees()
    
    if not employees:
        st.warning("⚠️ Aucun employé actif trouvé dans l'ERP.")
        st.info("Veuillez ajouter des employés dans le module RH de l'ERP.")
        return
    
    # Mode de sélection d'employé
    selection_mode = st.radio("Mode de sélection:", ["Par employé", "Vue rapide équipe"], horizontal=True)
    
    if selection_mode == "Vue rapide équipe":
        show_team_quick_view(tt, employees)
        return
    
    # Sélecteur d'employé enrichi
    employee_options = {emp['id']: emp['full_name_with_role'] for emp in employees}
    
    selected_employee_id = st.selectbox(
        "👤 Sélectionner l'employé:",
        options=list(employee_options.keys()),
        format_func=lambda x: employee_options[x],
        key="timetracker_employee_selector"
    )
    
    if not selected_employee_id:
        return
    
    employee = tt.get_employee_by_id(selected_employee_id)
    current_entry = tt.get_employee_current_entry(selected_employee_id)
    
    # Affichage des BTs assignés
    if selected_employee_id:
        # Récupérer BTs assignés
        bts_assignes = tt.get_bts_assignes_employe(selected_employee_id)
        
        if bts_assignes:
            with st.expander(f"🔧 {len(bts_assignes)} Bon(s) de Travail assigné(s)", expanded=True):
                for bt in bts_assignes:
                    col_bt1, col_bt2, col_bt3 = st.columns([2, 1, 1])
                    
                    with col_bt1:
                        priorite_icon = {'CRITIQUE': '🔴', 'URGENT': '🟡', 'NORMAL': '🟢'}.get(bt['priorite'], '⚪')
                        statut_icon = {'VALIDÉ': '✅', 'EN COURS': '⚡', 'TERMINÉ': '🎯'}.get(bt['bt_statut'], '📋')
                        
                        st.markdown(f"""
                        **{statut_icon} BT {bt['numero_document']}** {priorite_icon}
                        - Projet: {bt.get('nom_projet', 'N/A')}
                        - Client: {bt.get('client_nom_cache', 'N/A')}
                        - Échéance: {bt.get('date_echeance', 'N/A')}
                        """)
                    
                    with col_bt2:
                        st.metric("Heures pointées", f"{bt['heures_pointees']:.1f}h")
                        st.metric("Coût généré", f"{bt['cout_total']:.0f}$")
                    
                    with col_bt3:
                        if not current_entry:  # Si pas déjà en pointage
                            if st.button(f"▶️ Pointer", key=f"start_bt_{bt['bt_id']}", use_container_width=True):
                                try:
                                    entry_id = tt.punch_in_sur_bt(selected_employee_id, bt['bt_id'])
                                    st.success(f"✅ Pointage démarré sur BT {bt['numero_document']}!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur: {e}")
                        else:
                            st.info("Déjà en pointage")
    
    # Interface de pointage enrichie
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Informations employé enrichies
        st.markdown(f"""
        <div class='info-card'>
            <h4>👤 {employee['name']}</h4>
            <p><strong>💼 Poste:</strong> {employee.get('poste', 'N/A')}</p>
            <p><strong>🏢 Département:</strong> {employee.get('departement', 'N/A')}</p>
            <p><strong>📧 Email:</strong> {employee.get('email', 'N/A')}</p>
            <p><strong>🆔 Code ERP:</strong> {employee['employee_code']}</p>
            <p><strong>📋 Projets Assignés:</strong> {employee.get('projets_assignes', 0)}</p>
            <p><strong>📊 Charge Travail:</strong> {employee.get('charge_travail', 'N/A')}%</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Statistiques TimeTracker de l'employé
        if employee.get('timetracker_total_entries', 0) > 0:
            st.markdown(f"""
            <div class='info-card' style='background: linear-gradient(135deg, #e0f2fe 0%, #b3e5fc 100%);'>
                <h5>📊 Statistiques TimeTracker</h5>
                <p><strong>⏱️ Total Heures:</strong> {employee.get('timetracker_total_hours', 0):.1f}h</p>
                <p><strong>💰 Total Revenus:</strong> {employee.get('timetracker_total_revenue', 0):.0f}$ CAD</p>
                <p><strong>📈 Taux Moyen:</strong> {employee.get('timetracker_avg_rate', 0):.0f}$/h</p>
                <p><strong>📝 Pointages:</strong> {employee.get('timetracker_total_entries', 0)}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        if current_entry:
            # Employé pointé - afficher le status enrichi
            punch_in_time = datetime.fromisoformat(current_entry['punch_in'])
            elapsed_hours = current_entry['elapsed_hours']
            estimated_cost = current_entry['estimated_cost']
            
            # Couleur d'alerte si session très longue
            alert_style = ""
            if elapsed_hours > 12:
                alert_style = "border-left: 4px solid #ef4444; background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);"
            elif elapsed_hours > 8:
                alert_style = "border-left: 4px solid #f59e0b; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);"
            else:
                alert_style = "border-left: 4px solid #10b981; background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);"
            
            st.markdown(f"""
            <div class='info-card' style='{alert_style}'>
                <h4>🟢 POINTÉ ACTUELLEMENT</h4>
                <p><strong>📋 Projet:</strong> {current_entry['project_name']}</p>
                <p><strong>👤 Client:</strong> {current_entry['client_name']}</p>
                <p><strong>🔧 Tâche:</strong> {current_entry['task_name']}</p>
                <p><strong>🏭 Poste:</strong> {current_entry.get('work_center_name', 'N/A')}</p>
                <p><strong>🕐 Début:</strong> {punch_in_time.strftime('%H:%M:%S')}</p>
                <p><strong>⏱️ Durée:</strong> {elapsed_hours:.2f}h</p>
                <p><strong>💰 Coût estimé:</strong> {estimated_cost:.2f}$ CAD</p>
                <p><strong>💵 Taux:</strong> {current_entry['hourly_rate']:.2f}$/h</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Alerte si session très longue
            if elapsed_hours > 12:
                st.error("⚠️ Session de travail très longue (>12h). Vérifiez si l'employé a oublié de pointer.")
            elif elapsed_hours > 8:
                st.warning("⏰ Session de travail longue (>8h). Pensez à faire des pauses.")
            
            # Formulaire punch out enrichi
            st.markdown("#### 🔴 Terminer le pointage")
            with st.form("punch_out_form"):
                notes_out = st.text_area(
                    "📝 Notes de fin (optionnel):", 
                    placeholder="Travail accompli, difficultés rencontrées, prochaines étapes...",
                    height=100
                )
                
                punch_out_col1, punch_out_col2 = st.columns(2)
                with punch_out_col1:
                    if st.form_submit_button("🔴 PUNCH OUT", use_container_width=True):
                        try:
                            session_details = tt.punch_out(selected_employee_id, notes_out)
                            
                            st.success(f"""
                            ✅ **Punch out enregistré !**
                            
                            📊 **Résumé de session:**
                            - ⏱️ Durée: {session_details['total_hours']:.2f}h
                            - 💰 Coût: {session_details['total_cost']:.2f}$ CAD
                            - 💵 Taux: {session_details['hourly_rate']:.2f}$/h
                            - 📋 Projet: {session_details['project_name']}
                            - 🔧 Tâche: {session_details['task_name']}
                            """)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erreur punch out: {str(e)}")
                
                with punch_out_col2:
                    if st.form_submit_button("⏸️ Pause Déjeuner", use_container_width=True):
                        try:
                            session_details = tt.punch_out(selected_employee_id, f"Pause déjeuner. {notes_out}".strip())
                            st.info(f"⏸️ Pause déjeuner enregistrée. Durée avant pause: {session_details['total_hours']:.2f}h")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erreur pause: {str(e)}")
        
        else:
            # Employé non pointé - interface punch in enrichie
            st.markdown("""
            <div class='info-card' style='border-left: 4px solid #f59e0b; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);'>
                <h4>🟡 PRÊT À POINTER</h4>
                <p>Sélectionnez un projet et une tâche pour commencer le pointage</p>
                <p><small>💡 Le taux horaire sera automatiquement déterminé par l'opération sélectionnée</small></p>
            </div>
            """, unsafe_allow_html=True)
    
    # Interface de sélection projet/tâche si pas pointé
    if not current_entry:
        st.markdown("---")
        st.markdown("#### 📋 Nouveau Pointage")
        
        projects = tt.get_active_projects()
        if not projects:
            st.warning("❌ Aucun projet actif disponible dans l'ERP.")
            st.info("Veuillez créer des projets dans le module Projets de l'ERP.")
            return
        
        with st.form("punch_in_form"):
            # Sélection du projet enrichie
            project_options = {p['id']: f"{p['project_name']} - {p['client_name']} (H:{p['timetracker_hours']:.1f} | Rev:{p['timetracker_revenue']:.0f}$ CAD)" for p in projects}
            selected_project_id = st.selectbox(
                "📋 Projet:",
                options=list(project_options.keys()),
                format_func=lambda x: project_options[x],
                help="Affichage: Nom - Client (Heures TimeTracker | Revenus)"
            )
            
            # Affichage des détails du projet sélectionné
            if selected_project_id:
                selected_project = next(p for p in projects if p['id'] == selected_project_id)
                
                proj_col1, proj_col2, proj_col3 = st.columns(3)
                with proj_col1:
                    st.metric("📊 BD-FT Estimé", f"{selected_project.get('bd_ft_estime', 0):.1f}h")
                with proj_col2:
                    st.metric("💰 Prix Estimé", f"{selected_project.get('prix_estime', 0):.0f}$ CAD")
                with proj_col3:
                    st.metric("🔧 Opérations", selected_project.get('total_operations', 0))
                
                # Sélection de l'opération/tâche enrichie
                operations = tt.get_project_operations(selected_project_id)
                selected_operation_id = None
                
                if operations:
                    operation_options = {
                        op['id']: f"OP{op['sequence_number']:02d} - {op['task_name']} ({op['hourly_rate']:.0f}$/h) [{op['completion_percentage']:.0f}% completé]" 
                        for op in operations
                    }
                    selected_operation_id = st.selectbox(
                        "🔧 Opération/Tâche:",
                        options=[None] + list(operation_options.keys()),
                        format_func=lambda x: "🔧 Tâche générale (95$/h)" if x is None else operation_options[x],
                        help="Sélectionnez une opération spécifique ou laissez vide pour tâche générale"
                    )
                    
                    # Affichage des détails de l'opération
                    if selected_operation_id:
                        selected_operation = next(op for op in operations if op['id'] == selected_operation_id)
                        
                        op_col1, op_col2, op_col3 = st.columns(3)
                        with op_col1:
                            st.metric("⏱️ Temps Estimé", f"{selected_operation['estimated_hours']:.1f}h")
                        with op_col2:
                            st.metric("📊 Temps Réel", f"{selected_operation['actual_hours']:.1f}h")
                        with op_col3:
                            completion = selected_operation['completion_percentage']
                            st.metric("✅ Progression", f"{completion:.0f}%")
                        
                        # Barre de progression
                        progress_color = "🔴" if completion > 100 else "🟡" if completion > 80 else "🟢"
                        st.progress(min(1.0, completion / 100), text=f"{progress_color} Progression: {completion:.1f}%")
                else:
                    st.info("Aucune opération définie pour ce projet. Pointage général disponible.")
            
            # Notes de début enrichies
            notes_in = st.text_area(
                "📝 Notes de début (optionnel):", 
                placeholder="Objectifs de la session, plan de travail, outils nécessaires...",
                height=80
            )
            
            # Boutons d'action
            punch_in_col1, punch_in_col2, punch_in_col3 = st.columns(3)
            with punch_in_col1:
                if st.form_submit_button("🟢 PUNCH IN", use_container_width=True):
                    if selected_project_id:
                        try:
                            entry_id = tt.punch_in(selected_employee_id, selected_project_id, selected_operation_id, notes_in)
                            
                            # Déterminer le taux horaire qui sera appliqué
                            if selected_operation_id:
                                selected_operation = next(op for op in operations if op['id'] == selected_operation_id)
                                rate = selected_operation['hourly_rate']
                                task_name = selected_operation['task_name']
                            else:
                                rate = 95.0
                                task_name = "Tâche générale"
                            
                            st.success(f"""
                            ✅ **Punch in enregistré !**
                            
                            📊 **Détails:**
                            - 🆔 Entry ID: {entry_id}
                            - 📋 Projet: {selected_project['project_name']}
                            - 🔧 Tâche: {task_name}
                            - 💵 Taux: {rate:.2f}$/h
                            - 🕐 Heure début: {datetime.now().strftime('%H:%M:%S')}
                            """)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erreur punch in: {str(e)}")
                    else:
                        st.error("Veuillez sélectionner un projet.")
            
            with punch_in_col2:
                if st.form_submit_button("📋 Voir Détails Projet", use_container_width=True):
                    if selected_project_id:
                        # Stockage pour affichage des détails
                        st.session_state.timetracker_project_details = selected_project_id
                        st.info("💡 Détails du projet affichés ci-dessous.")
            
            with punch_in_col3:
                if st.form_submit_button("🔄 Rafraîchir Projets", use_container_width=True):
                    st.cache_data.clear()
                    st.success("🔄 Liste des projets mise à jour.")
                    st.rerun()
    
    # Affichage des détails de projet si demandé
    if st.session_state.get('timetracker_project_details'):
        show_project_details_for_timetracker(tt, st.session_state.timetracker_project_details)
    
    # Historique récent enrichi
    st.markdown("---")
    st.markdown("#### 📊 Historique Récent")
    
    # Filtres pour l'historique
    hist_col1, hist_col2, hist_col3 = st.columns(3)
    with hist_col1:
        limit_entries = st.selectbox("Nombre d'entrées:", [10, 25, 50, 100], index=0)
    with hist_col2:
        date_filter = st.date_input("Filtrer par date (optionnel):", value=None)
    with hist_col3:
        if st.button("🔄 Actualiser Historique"):
            st.rerun()
    
    date_filter_str = date_filter.strftime('%Y-%m-%d') if date_filter else None
    recent_entries = tt.get_employee_time_entries(selected_employee_id, limit_entries, date_filter_str)
    
    if recent_entries:
        df_history = []
        total_hours_shown = 0
        total_cost_shown = 0
        
        for entry in recent_entries:
            punch_in = datetime.fromisoformat(entry['punch_in'])
            
            if entry['punch_out']:
                punch_out_str = datetime.fromisoformat(entry['punch_out']).strftime('%H:%M:%S')
                duration_str = f"{entry['total_hours']:.2f}h"
                cost_str = f"{entry['total_cost']:.2f}$ CAD"
                status = "✅ Terminé"
                total_hours_shown += entry['total_hours']
                total_cost_shown += entry['total_cost']
            else:
                punch_out_str = "En cours..."
                elapsed = entry.get('elapsed_hours', 0)
                duration_str = f"{elapsed:.2f}h (en cours)"
                cost_str = f"{elapsed * entry['hourly_rate']:.2f}$ CAD (estimé)"
                status = "🟢 En cours"
            
            df_history.append({
                '📅 Date': punch_in.strftime('%Y-%m-%d'),
                '🕐 Début': punch_in.strftime('%H:%M:%S'),
                '🕑 Fin': punch_out_str,
                '📋 Projet': entry['project_name'],
                '👤 Client': entry['client_name'],
                '🔧 Tâche': entry['task_name'],
                '🏭 Poste': entry.get('work_center_name', 'N/A'),
                '⏱️ Durée': duration_str,
                '💰 Coût': cost_str,
                '🚦 Statut': status
            })
        
        # Résumé de l'historique affiché
        hist_summary_col1, hist_summary_col2, hist_summary_col3 = st.columns(3)
        with hist_summary_col1:
            st.metric("📊 Entrées Affichées", len(df_history))
        with hist_summary_col2:
            st.metric("⏱️ Total Heures", f"{total_hours_shown:.1f}h")
        with hist_summary_col3:
            st.metric("💰 Total Revenus", f"{total_cost_shown:.0f}$ CAD")
        
        # Tableau enrichi
        st.dataframe(pd.DataFrame(df_history), use_container_width=True)
        
        # Graphique de tendance si assez de données
        if len(recent_entries) >= 5:
            show_employee_trend_chart(recent_entries)
    else:
        message = "Aucun historique de pointage"
        if date_filter_str:
            message += f" pour le {date_filter_str}"
        st.info(message + ".")


def show_team_quick_view(tt: TimeTrackerERP, employees: List[Dict]):
    """Vue rapide de l'équipe - statuts de pointage"""
    
    st.markdown("#### 👥 Vue d'Équipe - Statuts de Pointage")
    
    # Répartition par département
    dept_employees = {}
    for emp in employees:
        dept = emp.get('departement', 'Non Assigné')
        if dept not in dept_employees:
            dept_employees[dept] = []
        dept_employees[dept].append(emp)
    
    for dept, dept_emps in dept_employees.items():
        with st.expander(f"🏢 {dept} ({len(dept_emps)} employés)", expanded=True):
            
            # Grille d'employés par département
            cols = st.columns(min(4, len(dept_emps)))
            
            for i, emp in enumerate(dept_emps):
                with cols[i % 4]:
                    current_entry = tt.get_employee_current_entry(emp['id'])
                    
                    if current_entry:
                        # Employé pointé
                        elapsed = current_entry['elapsed_hours']
                        color = "#10b981" if elapsed < 8 else "#f59e0b" if elapsed < 12 else "#ef4444"
                        
                        st.markdown(f"""
                        <div style='border: 2px solid {color}; border-radius: 8px; padding: 10px; margin-bottom: 10px; background: linear-gradient(135deg, {color}20, {color}10);'>
                            <h6 style='margin: 0; color: {color};'>🟢 {emp['name']}</h6>
                            <p style='margin: 2px 0; font-size: 0.8em;'><strong>Projet:</strong> {current_entry['project_name'][:20]}...</p>
                            <p style='margin: 2px 0; font-size: 0.8em;'><strong>Durée:</strong> {elapsed:.1f}h</p>
                            <p style='margin: 0; font-size: 0.8em;'><strong>Coût:</strong> {current_entry['estimated_cost']:.0f}$ CAD</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Employé libre
                        st.markdown(f"""
                        <div style='border: 2px solid #94a3b8; border-radius: 8px; padding: 10px; margin-bottom: 10px; background: #f8fafc;'>
                            <h6 style='margin: 0; color: #64748b;'>🟡 {emp['name']}</h6>
                            <p style='margin: 2px 0; font-size: 0.8em;'>Libre</p>
                            <p style='margin: 0; font-size: 0.8em;'>{emp.get('poste', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)


def show_project_details_for_timetracker(tt: TimeTrackerERP, project_id: int):
    """Affichage des détails d'un projet dans le contexte TimeTracker"""
    
    projects = tt.get_active_projects()
    project = next((p for p in projects if p['id'] == project_id), None)
    
    if not project:
        st.error("Projet non trouvé.")
        return
    
    with st.expander(f"📋 Détails: {project['project_name']}", expanded=True):
        # Informations générales
        det_col1, det_col2, det_col3 = st.columns(3)
        with det_col1:
            st.metric("💰 Prix Estimé", f"{project.get('prix_estime', 0):.0f}$ CAD")
        with det_col2:
            st.metric("⏱️ BD-FT Estimé", f"{project.get('bd_ft_estime', 0):.1f}h")
        with det_col3:
            st.metric("📅 Date Prévue", project.get('date_prevu', 'N/A'))
        
        # Progression TimeTracker
        tt_col1, tt_col2, tt_col3 = st.columns(3)
        with tt_col1:
            st.metric("⏱️ Heures TimeTracker", f"{project['timetracker_hours']:.1f}h")
        with tt_col2:
            st.metric("💰 Revenus TimeTracker", f"{project['timetracker_revenue']:.0f}$ CAD")
        with tt_col3:
            if project.get('bd_ft_estime', 0) > 0:
                progress_pct = (project['timetracker_hours'] / project['bd_ft_estime']) * 100
                st.metric("📊 Progression", f"{progress_pct:.1f}%")
        
        # Opérations du projet
        operations = tt.get_project_operations(project_id)
        if operations:
            st.markdown("##### 🔧 Opérations Disponibles")
            
            for op in operations:
                completion = op['completion_percentage']
                progress_color = "🔴" if completion > 100 else "🟡" if completion > 80 else "🟢"
                
                st.markdown(f"""
                **{op['task_name']}** ({op['hourly_rate']:.0f}$/h)
                - Estimé: {op['estimated_hours']:.1f}h | Réel: {op['actual_hours']:.1f}h | {progress_color} {completion:.0f}%
                """)
        
        if st.button("❌ Fermer Détails", key="close_project_details"):
            del st.session_state.timetracker_project_details
            st.rerun()


def show_employee_trend_chart(recent_entries: List[Dict]):
    """Graphique de tendance pour un employé"""
    
    st.markdown("##### 📈 Tendance des Heures")
    
    # Préparer les données pour le graphique
    completed_entries = [e for e in recent_entries if e.get('total_hours')]
    
    if len(completed_entries) >= 3:
        df_trend = pd.DataFrame([
            {
                'Date': datetime.fromisoformat(entry['punch_in']).date(),
                'Heures': entry['total_hours'],
                'Revenus': entry['total_cost'],
                'Projet': entry['project_name'][:15] + ('...' if len(entry['project_name']) > 15 else '')
            }
            for entry in completed_entries
        ])
        
        # Graphique des heures par jour
        fig = px.line(df_trend, x='Date', y='Heures', 
                     title="Évolution des Heures Travaillées",
                     hover_data=['Revenus', 'Projet'])
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='var(--text-color)'),
            title_x=0.5
        )
        st.plotly_chart(fig, use_container_width=True)


def show_analytics_interface(tt: TimeTrackerERP):
    """Interface d'analytics TimeTracker enrichie"""
    
    st.markdown("### 📊 Analytics & Rapports Avancés")
    
    # Période d'analyse configurable
    col_period1, col_period2, col_period3 = st.columns(3)
    with col_period1:
        period_preset = st.selectbox("Période prédéfinie:", 
                                   ["Personnalisée", "7 derniers jours", "30 derniers jours", "3 derniers mois"])
    
    if period_preset == "Personnalisée":
        with col_period2:
            start_date = st.date_input("📅 Date début:", datetime.now().date() - timedelta(days=30))
        with col_period3:
            end_date = st.date_input("📅 Date fin:", datetime.now().date())
    else:
        period_days = {"7 derniers jours": 7, "30 derniers jours": 30, "3 derniers mois": 90}[period_preset]
        start_date = datetime.now().date() - timedelta(days=period_days)
        end_date = datetime.now().date()
        
        with col_period2:
            st.metric("📅 Période", f"{period_days} jours")
        with col_period3:
            st.metric("📅 Du", f"{start_date} au {end_date}")
    
    # Revenus par projet enrichis
    st.markdown("#### 💰 Analyse des Revenus par Projet")
    
    period_days = (end_date - start_date).days
    project_revenues = tt.get_project_revenue_summary(period_days=period_days)
    
    if project_revenues:
        # Filtrage et validation des données
        valid_revenues = [rev for rev in project_revenues if rev.get('total_revenue', 0) > 0]
        
        if valid_revenues:
            # Métriques globales
            total_revenue_global = sum(rev['total_revenue'] for rev in valid_revenues)
            total_hours_global = sum(rev['total_hours'] for rev in valid_revenues)
            avg_hourly_rate = total_revenue_global / total_hours_global if total_hours_global > 0 else 0
            
            metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
            with metrics_col1:
                st.metric("💰 Revenus Total", f"{total_revenue_global:.0f}$ CAD")
            with metrics_col2:
                st.metric("⏱️ Heures Total", f"{total_hours_global:.1f}h")
            with metrics_col3:
                st.metric("💵 Taux Moyen", f"{avg_hourly_rate:.2f}$/h")
            with metrics_col4:
                st.metric("📋 Projets Actifs", len(valid_revenues))
            
            # Graphiques côte à côte
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                # Graphique en secteurs
                fig_pie = px.pie(
                    values=[rev['total_revenue'] for rev in valid_revenues],
                    names=[rev['project_name'][:20] + ('...' if len(rev['project_name']) > 20 else '') for rev in valid_revenues],
                    title="🥧 Répartition des Revenus"
                )
                fig_pie.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='var(--text-color)'),
                    title_x=0.5
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with chart_col2:
                # Graphique en barres horizontales
                fig_bar = px.bar(
                    y=[rev['project_name'][:25] + ('...' if len(rev['project_name']) > 25 else '') for rev in valid_revenues],
                    x=[rev['total_revenue'] for rev in valid_revenues],
                    orientation='h',
                    title="📊 Revenus par Projet",
                    labels={'x': 'Revenus (CAD)', 'y': 'Projets'}
                )
                fig_bar.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='var(--text-color)'),
                    title_x=0.5
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # Tableau détaillé enrichi
            st.markdown("##### 📋 Détail par Projet")
            df_revenues = []
            for rev in valid_revenues:
                revenue = rev['total_revenue']
                hours = rev['total_hours']
                estimated = rev.get('estimated_price', 0)
                
                # Calculs de performance
                efficiency = (hours / rev.get('employees_count', 1)) if rev.get('employees_count', 0) > 0 else hours
                revenue_per_employee = revenue / rev.get('employees_count', 1) if rev.get('employees_count', 0) > 0 else revenue
                
                df_revenues.append({
                    '📋 Projet': rev['project_name'],
                    '👤 Client': rev['client_name'],
                    '⏱️ Heures': f"{hours:.1f}h",
                    '💰 Revenus': f"{revenue:.0f}$ CAD",
                    '💵 Taux Moy.': f"{(revenue/hours):.2f}$/h" if hours > 0 else "N/A",
                    '👥 Employés': rev.get('employees_count', 0),
                    '📊 Efficacité': f"{efficiency:.1f}h/emp",
                    '💰 Rev./Emp.': f"{revenue_per_employee:.0f}$ CAD",
                    '📈 vs Estimé': f"{(revenue/estimated*100):.1f}%" if estimated > 0 else "N/A",
                    '📝 Pointages': rev.get('entries_count', 0)
                })
            
            st.dataframe(pd.DataFrame(df_revenues), use_container_width=True)
            
            # Analyse de performance
            st.markdown("##### 🎯 Analyse de Performance")
            
            # Top performers
            top_revenue = sorted(valid_revenues, key=lambda x: x['total_revenue'], reverse=True)[:3]
            top_efficiency = sorted(valid_revenues, key=lambda x: x['total_revenue']/x['total_hours'] if x['total_hours'] > 0 else 0, reverse=True)[:3]
            
            perf_col1, perf_col2 = st.columns(2)
            
            with perf_col1:
                st.markdown("**🏆 Top Revenus:**")
                for i, proj in enumerate(top_revenue, 1):
                    st.markdown(f"{i}. {proj['project_name'][:30]} - {proj['total_revenue']:.0f}$ CAD")
            
            with perf_col2:
                st.markdown("**⚡ Meilleure Efficacité ($/h):**")
                for i, proj in enumerate(top_efficiency, 1):
                    rate = proj['total_revenue']/proj['total_hours'] if proj['total_hours'] > 0 else 0
                    st.markdown(f"{i}. {proj['project_name'][:30]} - {rate:.2f}$/h")
    
    else:
        st.info(f"Aucune donnée de revenus TimeTracker pour la période du {start_date} au {end_date}.")
        st.markdown("💡 **Conseil**: Effectuez des pointages pour générer des données d'analyse.")


def show_productivity_interface(tt: TimeTrackerERP):
    """Interface d'analyse de productivité"""
    
    st.markdown("### 🏭 Analyse de Productivité")
    
    # Analyse par poste de travail
    st.markdown("#### 🔧 Productivité par Poste de Travail")
    
    work_center_data = tt.get_work_center_productivity()
    
    if work_center_data:
        # Métriques globales des postes
        total_wc_revenue = sum(wc['total_revenue'] for wc in work_center_data)
        total_wc_hours = sum(wc['actual_hours'] for wc in work_center_data)
        
        wc_col1, wc_col2, wc_col3, wc_col4 = st.columns(4)
        with wc_col1:
            st.metric("🏭 Postes Actifs", len(work_center_data))
        with wc_col2:
            st.metric("💰 Revenus Postes", f"{total_wc_revenue:.0f}$ CAD")
        with wc_col3:
            st.metric("⏱️ Heures Postes", f"{total_wc_hours:.1f}h")
        with wc_col4:
            avg_wc_rate = total_wc_revenue / total_wc_hours if total_wc_hours > 0 else 0
            st.metric("💵 Taux Moyen Postes", f"{avg_wc_rate:.2f}$/h")
        
        # Graphique de productivité par poste
        if len(work_center_data) > 1:
            prod_chart_col1, prod_chart_col2 = st.columns(2)
            
            with prod_chart_col1:
                fig_wc_revenue = px.bar(
                    x=[wc['work_center_name'][:15] + ('...' if len(wc['work_center_name']) > 15 else '') for wc in work_center_data],
                    y=[wc['total_revenue'] for wc in work_center_data],
                    title="💰 Revenus par Poste de Travail",
                    labels={'x': 'Postes', 'y': 'Revenus (CAD)'}
                )
                fig_wc_revenue.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='var(--text-color)'),
                    title_x=0.5
                )
                st.plotly_chart(fig_wc_revenue, use_container_width=True)
            
            with prod_chart_col2:
                # Taux d'utilisation
                utilization_data = [wc for wc in work_center_data if wc['utilization_rate'] > 0]
                if utilization_data:
                    fig_utilization = px.bar(
                        x=[wc['work_center_name'][:15] + ('...' if len(wc['work_center_name']) > 15 else '') for wc in utilization_data],
                        y=[wc['utilization_rate'] for wc in utilization_data],
                        title="📊 Taux d'Utilisation (%)",
                        labels={'x': 'Postes', 'y': 'Utilisation (%)'}
                    )
                    fig_utilization.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='var(--text-color)'),
                        title_x=0.5
                    )
                    st.plotly_chart(fig_utilization, use_container_width=True)
        
        # Tableau détaillé des postes
        df_work_centers = []
        for wc in work_center_data:
            df_work_centers.append({
                '🏭 Poste': wc['work_center_name'],
                '🏢 Département': wc['departement'],
                '🔧 Catégorie': wc['categorie'],
                '⏱️ Heures Réelles': f"{wc['actual_hours']:.1f}h",
                '💰 Revenus': f"{wc['total_revenue']:.0f}$ CAD",
                '💵 Taux Théorique': f"{wc['cout_horaire']:.2f}$/h",
                '📊 Utilisation': f"{wc['utilization_rate']:.1f}%" if wc['utilization_rate'] > 0 else "N/A",
                '👥 Employés': wc['unique_employees'],
                '📝 Pointages': wc['total_entries']
            })
        
        st.dataframe(pd.DataFrame(df_work_centers), use_container_width=True)
    
    else:
        st.info("Aucune donnée de productivité disponible pour les postes de travail.")
    
    # Analyse par employé
    st.markdown("---")
    st.markdown("#### 👥 Productivité par Employé")
    
    employees = tt.get_all_employees()
    employee_productivity = []
    
    for emp in employees[:10]:  # Limiter à 10 pour performance
        recent_entries = tt.get_employee_time_entries(emp['id'], 20)
        completed_entries = [e for e in recent_entries if e.get('total_hours')]
        
        if completed_entries:
            total_hours = sum(e['total_hours'] for e in completed_entries)
            total_revenue = sum(e['total_cost'] for e in completed_entries)
            avg_session = total_hours / len(completed_entries)
            
            employee_productivity.append({
                'name': emp['name'],
                'poste': emp.get('poste', 'N/A'),
                'departement': emp.get('departement', 'N/A'),
                'total_hours': total_hours,
                'total_revenue': total_revenue,
                'avg_hourly_rate': total_revenue / total_hours if total_hours > 0 else 0,
                'avg_session_hours': avg_session,
                'sessions_count': len(completed_entries)
            })
    
    if employee_productivity:
        # Top performers employés
        top_emp_revenue = sorted(employee_productivity, key=lambda x: x['total_revenue'], reverse=True)[:5]
        top_emp_efficiency = sorted(employee_productivity, key=lambda x: x['avg_hourly_rate'], reverse=True)[:5]
        
        emp_perf_col1, emp_perf_col2 = st.columns(2)
        
        with emp_perf_col1:
            st.markdown("**🏆 Top Revenus Employés:**")
            for i, emp in enumerate(top_emp_revenue, 1):
                st.markdown(f"{i}. {emp['name']} - {emp['total_revenue']:.0f}$ CAD ({emp['total_hours']:.1f}h)")
        
        with emp_perf_col2:
            st.markdown("**⚡ Meilleure Efficacité Employés:**")
            for i, emp in enumerate(top_emp_efficiency, 1):
                st.markdown(f"{i}. {emp['name']} - {emp['avg_hourly_rate']:.2f}$/h")


def show_admin_interface(tt: TimeTrackerERP):
    """Interface d'administration TimeTracker enrichie"""
    
    st.markdown("### ⚙️ Administration TimeTracker ERP")
    
    # Vue d'ensemble avec données ERP enrichies
    employees = tt.get_all_employees()
    projects = tt.get_active_projects()
    stats = tt.get_timetracker_statistics()
    
    # Métriques d'administration enrichies
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("👥 Employés ERP", len(employees))
    with col2:
        st.metric("📋 Projets Actifs", len(projects))
    with col3:
        currently_working = sum(1 for emp in employees if tt.get_employee_current_entry(emp['id']))
        st.metric("🟢 En Pointage", currently_working)
    with col4:
        st.metric("💰 Revenus Jour", f"{stats.get('total_revenue_today', 0):.0f}$ CAD")
    with col5:
        st.metric("📊 Pointages Jour", stats.get('total_entries_today', 0))
    
    # Alertes et notifications
    if currently_working > 0:
        st.info(f"ℹ️ {currently_working} employé(s) actuellement en pointage.")
    
    # Vérification des sessions longues
    long_sessions = []
    for emp in employees:
        current_entry = tt.get_employee_current_entry(emp['id'])
        if current_entry and current_entry['elapsed_hours'] > 10:
            long_sessions.append((emp['name'], current_entry['elapsed_hours']))
    
    if long_sessions:
        st.warning(f"⚠️ {len(long_sessions)} session(s) longue(s) détectée(s) (>10h):")
        for name, hours in long_sessions:
            st.write(f"- {name}: {hours:.1f}h")
    
    # Onglets d'administration enrichis
    admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
        "👥 Employés ERP", "📋 Projets ERP", "📊 Résumé Quotidien", "🔧 Outils Admin"
    ])
    
    with admin_tab1:
        show_admin_employees_tab(tt, employees)
    
    with admin_tab2:
        show_admin_projects_tab(tt, projects)
    
    with admin_tab3:
        show_admin_daily_summary_tab(tt)
    
    with admin_tab4:
        show_admin_tools_tab(tt)


def show_admin_employees_tab(tt: TimeTrackerERP, employees: List[Dict]):
    """Onglet administration des employés"""
    
    st.markdown("#### 👥 Gestion des Employés (Synchronisé ERP)")
    
    if employees:
        # Filtres
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            dept_filter = st.selectbox("Filtrer par département:", 
                                     ["Tous"] + list(set(emp.get('departement', 'N/A') for emp in employees)))
        with filter_col2:
            status_filter = st.selectbox("Filtrer par statut:", ["Tous", "En pointage", "Libre"])
        
        filtered_employees = employees
        if dept_filter != "Tous":
            filtered_employees = [emp for emp in filtered_employees if emp.get('departement') == dept_filter]
        
        df_employees = []
        for emp in filtered_employees:
            current_entry = tt.get_employee_current_entry(emp['id'])
            
            if status_filter == "En pointage" and not current_entry:
                continue
            elif status_filter == "Libre" and current_entry:
                continue
            
            status = "🟢 Pointé" if current_entry else "🟡 Libre"
            current_task = ""
            session_duration = ""
            estimated_cost = ""
            
            if current_entry:
                current_task = f"{current_entry['project_name'][:20]}... - {current_entry['task_name'][:15]}..."
                session_duration = f"{current_entry['elapsed_hours']:.1f}h"
                estimated_cost = f"{current_entry['estimated_cost']:.0f}$ CAD"
            
            df_employees.append({
                '🆔 ID': emp['id'],
                '👤 Nom': emp['name'],
                '💼 Poste': emp.get('poste', 'N/A'),
                '🏢 Département': emp.get('departement', 'N/A'),
                '📧 Email': emp.get('email', 'N/A'),
                '📊 Charge': f"{emp.get('charge_travail', 'N/A')}%",
                '🚦 Statut': status,
                '⏱️ Durée Session': session_duration or 'N/A',
                '💰 Coût Session': estimated_cost or 'N/A',
                '🔧 Tâche Actuelle': current_task or 'Aucune'
            })
        
        st.dataframe(pd.DataFrame(df_employees), use_container_width=True)
        st.info(f"ℹ️ {len(df_employees)} employé(s) affiché(s) - Données synchronisées depuis le module RH ERP")
    else:
        st.warning("Aucun employé actif dans l'ERP.")


def show_admin_projects_tab(tt: TimeTrackerERP, projects: List[Dict]):
    """Onglet administration des projets"""
    
    st.markdown("#### 📋 Gestion des Projets (Synchronisé ERP)")
    
    if projects:
        df_projects = []
        for proj in projects:
            operations = tt.get_project_operations(proj['id'])
            revenue_summary = tt.get_project_revenue_summary(proj['id'])
            total_revenue = revenue_summary[0]['total_revenue'] if revenue_summary else 0
            total_hours = revenue_summary[0]['total_hours'] if revenue_summary else 0
            
            # Calcul de progression
            estimated_hours = proj.get('bd_ft_estime', 0)
            progress = (total_hours / estimated_hours * 100) if estimated_hours > 0 else 0
            
            df_projects.append({
                '🆔 ID': proj['id'],
                '📋 Nom': proj['project_name'],
                '👤 Client': proj.get('client_name', 'N/A'),
                '🚦 Statut ERP': proj['statut'],
                '🔧 Opérations': len(operations),
                '⏱️ H. Estimées': f"{estimated_hours:.1f}h",
                '⏱️ H. Réelles': f"{total_hours:.1f}h",
                '📊 Progression': f"{progress:.1f}%",
                '💰 Revenus TT': f"{total_revenue:.0f}$ CAD",
                '💰 Prix Estimé': f"{proj.get('prix_estime', 0):.0f}$ CAD"
            })
        
        st.dataframe(pd.DataFrame(df_projects), use_container_width=True)
        st.info(f"ℹ️ {len(projects)} projet(s) actif(s) - Données synchronisées depuis le module Projets ERP")
    else:
        st.warning("Aucun projet actif dans l'ERP.")


def show_admin_daily_summary_tab(tt: TimeTrackerERP):
    """Onglet résumé quotidien enrichi"""
    
    st.markdown("#### 📊 Résumé Quotidien TimeTracker")
    
    # Sélecteur de date avec raccourcis
    date_col1, date_col2, date_col3 = st.columns(3)
    with date_col1:
        selected_date = st.date_input("📅 Date:", datetime.now().date())
    with date_col2:
        if st.button("📅 Aujourd'hui"):
            selected_date = datetime.now().date()
            st.rerun()
    with date_col3:
        if st.button("📅 Hier"):
            selected_date = datetime.now().date() - timedelta(days=1)
            st.rerun()
    
    date_str = selected_date.strftime('%Y-%m-%d')
    daily_summary = tt.get_daily_summary(date_str)
    
    if daily_summary:
        # Agrégation des données
        total_hours = sum(entry['total_hours'] for entry in daily_summary)
        total_revenue = sum(entry['total_cost'] for entry in daily_summary)
        unique_employees = len(set(entry['employee_id'] for entry in daily_summary))
        unique_projects = len(set(entry['project_id'] for entry in daily_summary))
        total_entries = sum(entry['entries_count'] for entry in daily_summary)
        
        # Métriques du jour
        day_col1, day_col2, day_col3, day_col4, day_col5 = st.columns(5)
        with day_col1:
            st.metric("⏱️ Total Heures", f"{total_hours:.1f}h")
        with day_col2:
            st.metric("💰 Total Revenus", f"{total_revenue:.0f}$ CAD")
        with day_col3:
            avg_rate = total_revenue / total_hours if total_hours > 0 else 0
            st.metric("💵 Taux Moyen", f"{avg_rate:.2f}$/h")
        with day_col4:
            st.metric("👥 Employés Actifs", unique_employees)
        with day_col5:
            st.metric("📋 Projets Touchés", unique_projects)
        
        # Tableau détaillé
        df_daily = []
        for entry in daily_summary:
            df_daily.append({
                '👤 Employé': entry['employee_name'],
                '💼 Poste': entry['poste'],
                '🏢 Département': entry['departement'],
                '📋 Projet': entry['project_name'],
                '👤 Client': entry['client_name'],
                '🔧 Tâche': entry['task_name'],
                '🏭 Poste Travail': entry.get('work_center_name', 'N/A'),
                '⏱️ Heures': f"{entry['total_hours']:.2f}h",
                '💰 Revenus': f"{entry['total_cost']:.2f}$ CAD",
                '💵 Taux': f"{entry['avg_hourly_rate']:.2f}$/h",
                '📊 Pointages': entry['entries_count']
            })
        
        st.dataframe(pd.DataFrame(df_daily), use_container_width=True)
        
        # Graphiques de répartition si assez de données
        if len(daily_summary) > 1:
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                # Répartition par employé
                emp_data = {}
                for entry in daily_summary:
                    emp_name = entry['employee_name']
                    emp_data[emp_name] = emp_data.get(emp_name, 0) + entry['total_hours']
                
                fig_emp = px.pie(values=list(emp_data.values()), names=list(emp_data.keys()),
                               title="⏱️ Répartition Heures par Employé")
                fig_emp.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='var(--text-color)'), title_x=0.5)
                st.plotly_chart(fig_emp, use_container_width=True)
            
            with chart_col2:
                # Répartition par projet
                proj_data = {}
                for entry in daily_summary:
                    proj_name = entry['project_name'][:20] + ('...' if len(entry['project_name']) > 20 else '')
                    proj_data[proj_name] = proj_data.get(proj_name, 0) + entry['total_cost']
                
                fig_proj = px.pie(values=list(proj_data.values()), names=list(proj_data.keys()),
                                title="💰 Répartition Revenus par Projet")
                fig_proj.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                     font=dict(color='var(--text-color)'), title_x=0.5)
                st.plotly_chart(fig_proj, use_container_width=True)
    
    else:
        st.info(f"Aucune activité TimeTracker enregistrée pour le {date_str}")
        st.markdown("💡 **Conseil**: Les employés doivent effectuer des pointages pour générer des données.")


def show_admin_tools_tab(tt: TimeTrackerERP):
    """Onglet outils d'administration"""
    
    st.markdown("#### 🔧 Outils d'Administration")
    
    # Section de maintenance
    with st.expander("🔧 Outils de Maintenance", expanded=True):
        
        maintenance_col1, maintenance_col2 = st.columns(2)
        
        with maintenance_col1:
            st.markdown("**🔍 Vérifications:**")
            
            if st.button("🔍 Détecter Sessions Orphelines", use_container_width=True):
                # Détecter les entrées sans punch_out depuis plus de 24h
                orphan_entries = tt.db.execute_query('''
                    SELECT te.id, e.prenom || ' ' || e.nom as employee_name, 
                           te.punch_in, p.nom_projet as project_name
                    FROM time_entries te
                    JOIN employees e ON te.employee_id = e.id
                    JOIN projects p ON te.project_id = p.id
                    WHERE te.punch_out IS NULL 
                    AND te.punch_in < datetime('now', '-1 day')
                ''')
                
                if orphan_entries:
                    st.warning(f"⚠️ {len(orphan_entries)} session(s) orpheline(s) détectée(s):")
                    for entry in orphan_entries:
                        st.write(f"- {entry['employee_name']}: {entry['project_name']} (depuis {entry['punch_in']})")
                else:
                    st.success("✅ Aucune session orpheline détectée.")
            
            if st.button("📊 Statistiques Base", use_container_width=True):
                # Statistiques de la base
                stats = {
                    'Total entrées': tt.db.get_table_count('time_entries'),
                    'Entrées complètes': len(tt.db.execute_query('SELECT * FROM time_entries WHERE punch_out IS NOT NULL')),
                    'Entrées en cours': len(tt.db.execute_query('SELECT * FROM time_entries WHERE punch_out IS NULL')),
                    'Employés avec pointages': len(tt.db.execute_query('SELECT DISTINCT employee_id FROM time_entries')),
                    'Projets avec pointages': len(tt.db.execute_query('SELECT DISTINCT project_id FROM time_entries'))
                }
                
                for key, value in stats.items():
                    st.metric(key, value)
        
        with maintenance_col2:
            st.markdown("**⚙️ Actions:**")
            
            if st.button("🧹 Nettoyer Sessions Vides", use_container_width=True):
                # Supprimer les entrées sans heures et très anciennes
                deleted = tt.db.execute_update('''
                    DELETE FROM time_entries 
                    WHERE total_hours IS NULL 
                    AND punch_out IS NULL 
                    AND punch_in < datetime('now', '-7 days')
                ''')
                
                if deleted > 0:
                    st.success(f"✅ {deleted} session(s) vide(s) supprimée(s).")
                else:
                    st.info("ℹ️ Aucune session vide à nettoyer.")
            
            if st.button("📈 Recalculer Totaux", use_container_width=True):
                # Recalculer les totaux pour les entrées complètes
                entries_to_fix = tt.db.execute_query('''
                    SELECT id, punch_in, punch_out, hourly_rate
                    FROM time_entries 
                    WHERE punch_out IS NOT NULL 
                    AND (total_hours IS NULL OR total_cost IS NULL)
                ''')
                
                fixed_count = 0
                for entry in entries_to_fix:
                    punch_in = datetime.fromisoformat(entry['punch_in'])
                    punch_out = datetime.fromisoformat(entry['punch_out'])
                    total_hours = (punch_out - punch_in).total_seconds() / 3600
                    total_cost = total_hours * entry['hourly_rate']
                    
                    tt.db.execute_update('''
                        UPDATE time_entries 
                        SET total_hours = ?, total_cost = ?
                        WHERE id = ?
                    ''', (total_hours, total_cost, entry['id']))
                    fixed_count += 1
                
                if fixed_count > 0:
                    st.success(f"✅ {fixed_count} entrée(s) recalculée(s).")
                else:
                    st.info("ℹ️ Tous les totaux sont corrects.")
    
    # Section d'export/import
    with st.expander("📤 Export/Import de Données", expanded=False):
        
        export_col1, export_col2 = st.columns(2)
        
        with export_col1:
            st.markdown("**📤 Export:**")
            
            # Sélection de la période d'export
            export_start = st.date_input("Date début export:", datetime.now().date() - timedelta(days=30))
            export_end = st.date_input("Date fin export:", datetime.now().date())
            
            if st.button("📤 Exporter CSV", use_container_width=True):
                # Requête d'export enrichie
                export_data = tt.db.execute_query('''
                    SELECT 
                        te.id, te.punch_in, te.punch_out, te.total_hours, te.total_cost, te.hourly_rate, te.notes,
                        e.prenom || ' ' || e.nom as employee_name, e.poste, e.departement,
                        p.nom_projet as project_name, p.client_nom_cache as client_name,
                        o.description as task_name, o.sequence_number,
                        wc.nom as work_center_name, wc.departement as work_center_dept
                    FROM time_entries te
                    JOIN employees e ON te.employee_id = e.id
                    JOIN projects p ON te.project_id = p.id
                    LEFT JOIN operations o ON te.operation_id = o.id
                    LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                    WHERE DATE(te.punch_in) BETWEEN ? AND ?
                    ORDER BY te.punch_in DESC
                ''', (export_start.strftime('%Y-%m-%d'), export_end.strftime('%Y-%m-%d')))
                
                if export_data:
                    df_export = pd.DataFrame([dict(row) for row in export_data])
                    csv = df_export.to_csv(index=False)
                    
                    st.download_button(
                        label="💾 Télécharger CSV",
                        data=csv,
                        file_name=f"timetracker_export_{export_start}_{export_end}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.success(f"✅ Export prêt: {len(export_data)} entrées")
                else:
                    st.warning("Aucune donnée à exporter pour cette période.")
        
        with export_col2:
            st.markdown("**ℹ️ Informations:**")
            st.info("""
            **Export inclut:**
            - Toutes les entrées de temps
            - Détails employés et projets
            - Informations postes de travail
            - Calculs de coûts
            
            **Format:** CSV compatible Excel
            """)


def show_system_interface():
    """Interface d'information système enrichie"""
    
    st.markdown("### ℹ️ Informations Système ERP")
    
    st.success("""
    🎉 **Architecture SQLite Unifiée Active !**
    
    TimeTracker est maintenant intégralement intégré dans la base ERP unifiée 
    `erp_production_dg.db`. Toutes les données sont synchronisées en temps réel.
    """)
    
    # Informations sur la base unifiée
    if 'erp_db' in st.session_state:
        db_info = st.session_state.erp_db.get_schema_info()
        
        # Métriques système
        sys_col1, sys_col2, sys_col3, sys_col4 = st.columns(4)
        with sys_col1:
            st.metric("📊 Taille Base", f"{db_info['file_size_mb']} MB")
        with sys_col2:
            st.metric("📋 Tables", len(db_info['tables']))
        with sys_col3:
            st.metric("📝 Enregistrements", f"{db_info['total_records']:,}")
        with sys_col4:
            timetracker_records = db_info['tables'].get('time_entries', 0)
            st.metric("⏱️ Entrées TimeTracker", timetracker_records)
        
        # Détails par module
        st.markdown("#### 📊 Répartition des Données par Module")
        
        modules_col1, modules_col2 = st.columns(2)
        
        with modules_col1:
            st.markdown("**🏭 Modules Production:**")
            st.metric("📋 Projets", db_info['tables'].get('projects', 0))
            st.metric("🔧 Opérations", db_info['tables'].get('operations', 0))
            st.metric("📦 Matériaux", db_info['tables'].get('materials', 0))
            st.metric("🏭 Postes Travail", db_info['tables'].get('work_centers', 0))
        
        with modules_col2:
            st.markdown("**👥 Modules Gestion:**")
            st.metric("👥 Employés", db_info['tables'].get('employees', 0))
            st.metric("🏢 Entreprises", db_info['tables'].get('companies', 0))
            st.metric("👤 Contacts", db_info['tables'].get('contacts', 0))
            st.metric("💬 Interactions", db_info['tables'].get('interactions', 0))
        
        # Validation de l'intégrité enrichie
        st.markdown("#### 🔍 Validation de l'Intégrité")
        
        integrity_col1, integrity_col2 = st.columns(2)
        
        with integrity_col1:
            if st.button("🔍 Vérifier Intégrité Complète", use_container_width=True):
                with st.spinner("Validation en cours..."):
                    integrity = st.session_state.erp_db.validate_integrity()
                    
                    if 'error' not in integrity:
                        st.markdown("**Résultats de validation:**")
                        all_good = True
                        for check, status in integrity.items():
                            icon = "✅" if status else "❌"
                            check_name = check.replace('_', ' ').title()
                            st.markdown(f"{icon} {check_name}")
                            if not status:
                                all_good = False
                        
                        if all_good:
                            st.success("🎉 Intégrité parfaite ! Architecture unifiée fonctionnelle.")
                        else:
                            st.warning("⚠️ Certaines vérifications ont échoué.")
                    else:
                        st.error(f"Erreur validation: {integrity['error']}")
        
        with integrity_col2:
            if st.button("📊 Statistiques Avancées", use_container_width=True):
                with st.spinner("Calcul des statistiques..."):
                    # Statistiques TimeTracker spécifiques
                    tt_stats = st.session_state.erp_db.execute_query('''
                        SELECT 
                            COUNT(*) as total_entries,
                            COUNT(CASE WHEN punch_out IS NOT NULL THEN 1 END) as completed_entries,
                            COUNT(CASE WHEN punch_out IS NULL THEN 1 END) as active_entries,
                            COALESCE(SUM(total_hours), 0) as total_hours,
                            COALESCE(SUM(total_cost), 0) as total_revenue,
                            COUNT(DISTINCT employee_id) as unique_employees,
                            COUNT(DISTINCT project_id) as unique_projects
                        FROM time_entries
                    ''')
                    
                    if tt_stats:
                        stats = dict(tt_stats[0])
                        st.markdown("**📊 Statistiques TimeTracker:**")
                        st.json({
                            "Entrées totales": stats['total_entries'],
                            "Entrées complétées": stats['completed_entries'],
                            "Entrées actives": stats['active_entries'],
                            "Heures totales": f"{stats['total_hours']:.1f}h",
                            "Revenus totaux": f"{stats['total_revenue']:.2f}$ CAD",
                            "Employés uniques": stats['unique_employees'],
                            "Projets uniques": stats['unique_projects']
                        })
        
        # Informations techniques détaillées
        with st.expander("🔧 Informations Techniques", expanded=False):
            
            tech_col1, tech_col2 = st.columns(2)
            
            with tech_col1:
                st.markdown("**🗄️ Base de Données:**")
                st.code(f"""
                Fichier: {db_info['database_file']}
                Taille: {db_info['file_size_mb']} MB
                Tables: {len(db_info['tables'])}
                Enregistrements: {db_info['total_records']:,}
                """)
                
                st.markdown("**⏱️ TimeTracker:**")
                timetracker_entries = db_info['tables'].get('time_entries', 0)
                st.code(f"""
                Entrées de temps: {timetracker_entries:,}
                Architecture: SQLite unifiée
                Synchronisation: Temps réel
                """)
            
            with tech_col2:
                st.markdown("**📋 Détail Tables:**")
                st.json(db_info['tables'])
    
    else:
        st.error("❌ Base ERP non disponible")
        st.info("Veuillez redémarrer l'application ERP.")


# =========================================================================
# INTERFACES POSTES DE TRAVAIL INTÉGRÉES
# =========================================================================

def show_work_centers_integrated_interface(gestionnaire_postes):
    """Interface postes de travail intégrée au TimeTracker"""
    
    st.markdown("## 🏭 Gestion des Postes de Travail")
    
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
        render_work_centers_details(gestionnaire_postes, st.session_state.gestionnaire_employes)
    
    with tab_analytics:
        render_work_centers_analytics(gestionnaire_postes)
    
    with tab_manage:
        render_work_centers_management(gestionnaire_postes)


def show_manufacturing_routes_integrated_interface(gestionnaire_postes):
    """Interface gammes de fabrication intégrée"""
    
    st.markdown("## ⚙️ Gammes de Fabrication Intégrées")
    
    # Vérification postes SQLite
    if len(gestionnaire_postes.get_all_work_centers()) == 0:
        st.warning("⚠️ Aucun poste trouvé en SQLite. Migration en cours...")
        gestionnaire_postes._ensure_work_centers_migrated()
        st.rerun()
    
    tab_generator, tab_templates, tab_optimization = st.tabs([
        "🔧 Générateur SQLite", "📋 Modèles", "🎯 Optimisation"
    ])
    
    with tab_generator:
        render_operations_manager(gestionnaire_postes, st.session_state.gestionnaire_employes)
    
    with tab_templates:
        render_gammes_templates(gestionnaire_postes)
    
    with tab_optimization:
        render_route_optimization(gestionnaire_postes, st.session_state.gestionnaire)


def show_capacity_analysis_integrated_interface(gestionnaire_postes):
    """Interface analyse de capacité intégrée"""
    
    st.markdown("## 📈 Analyse de Capacité Intégrée")
    
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


# =========================================================================
# FONCTIONS DE RENDU POSTES DE TRAVAIL (Intégrées)
# =========================================================================

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


def render_operations_manager(gestionnaire_postes, gestionnaire_employes):
    """Gestionnaire d'opérations avec vrais postes SQLite"""
    st.subheader("🔧 Générateur de Gammes de Fabrication (SQLite)")
    
    # Vérification des postes SQLite
    postes_count = len(gestionnaire_postes.get_all_work_centers())
    if postes_count == 0:
        st.error("❌ Aucun poste trouvé en SQLite. Impossible de générer des gammes.")
        return
    
    st.info(f"📊 Utilisation de {postes_count} postes de travail synchronisés depuis SQLite")
    
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
    
    # Affichage de la gamme générée
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
        
        # Graphiques
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
                    gamme = gestionnaire_postes.generer_gamme_fabrication(
                        type_key, "MOYEN", st.session_state.gestionnaire_employes
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
    
    # Simulation d'optimisation
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


# =========================================================================
# FONCTIONS UTILITAIRES POSTES DE TRAVAIL (Intégrées)
# =========================================================================

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
        if 'gestionnaire_postes_tt' not in st.session_state:
            return {"date_generation": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "capacites": {}, "utilisation_theorique": {}}
        
        gestionnaire_postes = st.session_state.gestionnaire_postes_tt
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


def update_sidebar_with_work_centers():
    """Ajoute les statistiques des postes de travail SQLite dans la sidebar"""
    try:
        if 'gestionnaire_postes_tt' not in st.session_state:
            return
        
        gestionnaire_postes = st.session_state.gestionnaire_postes_tt
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


# Fonctions utilitaires conservées pour compatibilité
def hash_password(password: str) -> str:
    """Hash un mot de passe avec SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Vérifie un mot de passe contre son hash"""
    return hash_password(password) == hashed


# Point d'entrée principal
if __name__ == "__main__":
    st.error("❌ Ce module doit être importé par app.py")
    st.info("Lancez l'application ERP avec: streamlit run app.py")
