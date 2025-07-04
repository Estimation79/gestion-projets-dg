# gantt_bons_travail.py - Programme Complet Gantt des Bons de Travail
# Compatible avec l'architecture SQLite unifiée - ERP Production DG Inc.
# Version Finale Complète - Aucune omission

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import json
import random
import logging

# Configuration de la page
st.set_page_config(
    page_title="Gantt - Bons de Travail",
    page_icon="📋",
    layout="wide"
)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================================
# CONFIGURATION DES COULEURS ET CONSTANTES
# =========================================================================

BT_COLORS = {
    'BROUILLON': '#FFB74D',     # Orange clair
    'VALIDÉ': '#64B5F6',        # Bleu clair
    'ENVOYÉ': '#81C784',        # Vert clair
    'APPROUVÉ': '#FFA726',      # Orange
    'EN_COURS': '#26A69A',      # Teal
    'TERMINÉ': '#9C27B0',       # Violet
    'ANNULÉ': '#795548',        # Marron
    'DEFAULT': '#90A4AE'        # Gris
}

POSTE_COLORS = {
    'À FAIRE': '#FFAB91',       # Orange saumon
    'EN_COURS': '#80CBC4',      # Teal clair
    'TERMINÉ': '#A5D6A7',       # Vert clair
    'SUSPENDU': '#B39DDB',      # Violet clair
    'ANNULÉ': '#FFCC02',        # Jaune
    'DEFAULT': '#CFD8DC'        # Gris clair
}

# =========================================================================
# STYLES CSS PERSONNALISÉS
# =========================================================================

def load_custom_css():
    """Charge les styles CSS personnalisés"""
    st.markdown("""
    <style>
    .main-title-gantt {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #06b6d4 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
    }
    
    .main-title-gantt h1 {
        margin: 0;
        font-size: 32px;
        font-weight: 700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-title-gantt p {
        margin: 10px 0 0 0;
        font-size: 16px;
        opacity: 0.9;
    }
    
    .filter-container-gantt {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
        margin-bottom: 25px;
        border: 1px solid #e2e8f0;
    }
    
    .metrics-container-gantt {
        background: #f8fafc;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #3b82f6;
        margin: 15px 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
    
    .bt-card {
        background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border: 1px solid #e5e7eb;
        transition: all 0.3s ease;
    }
    
    .bt-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
    }
    
    .status-badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 25px;
        font-size: 13px;
        font-weight: 600;
        color: white;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
    }
    
    .progress-bar-custom {
        background: #e5e7eb;
        border-radius: 10px;
        height: 10px;
        overflow: hidden;
        margin: 10px 0;
    }
    
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #10b981, #34d399);
        border-radius: 10px;
        transition: width 0.3s ease;
    }
    
    .legend-item {
        display: flex;
        align-items: center;
        margin: 5px 0;
        font-size: 14px;
    }
    
    .legend-color {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        margin-right: 10px;
        border: 2px solid rgba(0, 0, 0, 0.1);
    }
    
    .demo-warning {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border: 2px solid #f59e0b;
        border-radius: 10px;
        padding: 15px;
        margin: 20px 0;
        color: #92400e;
        font-weight: 500;
    }
    
    .success-message {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        border: 2px solid #10b981;
        border-radius: 10px;
        padding: 15px;
        margin: 15px 0;
        color: #065f46;
        font-weight: 500;
    }
    
    .error-message {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        border: 2px solid #ef4444;
        border-radius: 10px;
        padding: 15px;
        margin: 15px 0;
        color: #991b1b;
        font-weight: 500;
    }
    
    .info-card {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border: 1px solid #60a5fa;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        color: #1e40af;
    }
    </style>
    """, unsafe_allow_html=True)

# =========================================================================
# FONCTIONS DE CRÉATION DE DONNÉES DE DÉMONSTRATION
# =========================================================================

def create_sample_work_centers(erp_db):
    """Crée des postes de travail de démonstration si la base est vide"""
    try:
        # Vérifier si des postes existent déjà
        existing = erp_db.execute_query("SELECT COUNT(*) as count FROM work_centers")
        if existing and existing[0]['count'] > 0:
            logger.info("Postes de travail existants trouvés")
            return  # Des postes existent déjà
        
        postes_demo = [
            {
                "nom": "Programmation Bureau", 
                "departement": "BUREAU", 
                "categorie": "CONCEPTION", 
                "type_machine": "CAD/CAM", 
                "capacite_theorique": 8.0, 
                "operateurs_requis": 1, 
                "cout_horaire": 65.0, 
                "competences_requises": '["CAD", "Programmation CNC"]', 
                "statut": "ACTIF", 
                "localisation": "Bureau Technique"
            },
            {
                "nom": "Laser CNC", 
                "departement": "DECOUPE", 
                "categorie": "CNC", 
                "type_machine": "Laser Fiber", 
                "capacite_theorique": 16.0, 
                "operateurs_requis": 1, 
                "cout_horaire": 85.0, 
                "competences_requises": '["CNC", "Laser"]', 
                "statut": "ACTIF", 
                "localisation": "Atelier A"
            },
            {
                "nom": "Plieuse CNC 1", 
                "departement": "FORMAGE", 
                "categorie": "CNC", 
                "type_machine": "Plieuse Hydraulique", 
                "capacite_theorique": 8.0, 
                "operateurs_requis": 1, 
                "cout_horaire": 75.0, 
                "competences_requises": '["CNC", "Pliage"]', 
                "statut": "ACTIF", 
                "localisation": "Atelier A"
            },
            {
                "nom": "Perçage 1", 
                "departement": "USINAGE", 
                "categorie": "CONVENTIONNEL", 
                "type_machine": "Perceuse Radiale", 
                "capacite_theorique": 8.0, 
                "operateurs_requis": 1, 
                "cout_horaire": 45.0, 
                "competences_requises": '["Usinage", "Perçage"]', 
                "statut": "ACTIF", 
                "localisation": "Atelier B"
            },
            {
                "nom": "Soudage GMAW 1", 
                "departement": "SOUDAGE", 
                "categorie": "MANUEL", 
                "type_machine": "Poste GMAW", 
                "capacite_theorique": 8.0, 
                "operateurs_requis": 1, 
                "cout_horaire": 55.0, 
                "competences_requises": '["Soudage GMAW", "Lecture Plans"]', 
                "statut": "ACTIF", 
                "localisation": "Atelier Soudure"
            },
            {
                "nom": "Robot ABB GMAW", 
                "departement": "SOUDAGE", 
                "categorie": "ROBOTIQUE", 
                "type_machine": "Robot ABB IRB 2600", 
                "capacite_theorique": 16.0, 
                "operateurs_requis": 1, 
                "cout_horaire": 95.0, 
                "competences_requises": '["Robotique", "Programmation Robot", "Soudage"]', 
                "statut": "ACTIF", 
                "localisation": "Cellule Robot 1"
            },
            {
                "nom": "Assemblage Léger 1", 
                "departement": "ASSEMBLAGE", 
                "categorie": "MANUEL", 
                "type_machine": "Table Assemblage", 
                "capacite_theorique": 8.0, 
                "operateurs_requis": 2, 
                "cout_horaire": 45.0, 
                "competences_requises": '["Assemblage", "Lecture Plans", "Outillage"]', 
                "statut": "ACTIF", 
                "localisation": "Zone Assemblage"
            },
            {
                "nom": "Assemblage Lourd", 
                "departement": "ASSEMBLAGE", 
                "categorie": "MANUTENTION", 
                "type_machine": "Pont Roulant", 
                "capacite_theorique": 8.0, 
                "operateurs_requis": 3, 
                "cout_horaire": 60.0, 
                "competences_requises": '["Assemblage Lourd", "Pont Roulant", "Sécurité"]', 
                "statut": "ACTIF", 
                "localisation": "Zone Lourde"
            },
            {
                "nom": "Meulage 1", 
                "departement": "FINITION", 
                "categorie": "MANUEL", 
                "type_machine": "Meuleuse d'angle", 
                "capacite_theorique": 8.0, 
                "operateurs_requis": 1, 
                "cout_horaire": 40.0, 
                "competences_requises": '["Meulage", "Finition", "EPI"]', 
                "statut": "ACTIF", 
                "localisation": "Zone Finition"
            },
            {
                "nom": "Contrôle dimensionnel", 
                "departement": "QUALITE", 
                "categorie": "MESURE", 
                "type_machine": "MMT + Instruments", 
                "capacite_theorique": 8.0, 
                "operateurs_requis": 1, 
                "cout_horaire": 70.0, 
                "competences_requises": '["Métrologie", "MMT", "Lecture Plans"]', 
                "statut": "ACTIF", 
                "localisation": "Labo Qualité"
            },
            {
                "nom": "Peinture poudre", 
                "departement": "FINITION", 
                "categorie": "TRAITEMENT", 
                "type_machine": "Cabine Poudrage", 
                "capacite_theorique": 8.0, 
                "operateurs_requis": 1, 
                "cout_horaire": 50.0, 
                "competences_requises": '["Peinture", "Traitement Surface"]', 
                "statut": "ACTIF", 
                "localisation": "Cabine Peinture"
            },
            {
                "nom": "Plasma CNC", 
                "departement": "DECOUPE", 
                "categorie": "CNC", 
                "type_machine": "Plasma Hypertherm", 
                "capacite_theorique": 12.0, 
                "operateurs_requis": 1, 
                "cout_horaire": 70.0, 
                "competences_requises": '["CNC", "Plasma", "Tôlerie"]', 
                "statut": "ACTIF", 
                "localisation": "Atelier Découpe"
            }
        ]
        
        created_count = 0
        for poste in postes_demo:
            try:
                poste_id = erp_db.add_work_center(poste)
                if poste_id:
                    created_count += 1
                    logger.info(f"Poste créé: {poste['nom']} (ID: {poste_id})")
            except Exception as e:
                logger.error(f"Erreur création poste {poste['nom']}: {e}")
        
        if created_count > 0:
            st.success(f"✅ {created_count} postes de travail créés avec succès!")
        else:
            st.warning("⚠️ Aucun poste de travail n'a pu être créé")
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la création des postes de travail: {e}")
        logger.error(f"Erreur create_sample_work_centers: {e}")

def create_sample_projects_and_companies(erp_db):
    """Crée des projets et entreprises de démonstration"""
    try:
        company_ids = []
        
        # Vérifier si des entreprises existent
        existing_companies = erp_db.execute_query("SELECT COUNT(*) as count FROM companies")
        if not existing_companies or existing_companies[0]['count'] == 0:
            # Créer des entreprises de démonstration
            companies_demo = [
                {
                    "nom": "Acier Drummond Inc.", 
                    "secteur": "METALLURGIE", 
                    "type_company": "CLIENT", 
                    "adresse": "123 Rue Industrielle, Drummondville, QC J2C 2S4",
                    "site_web": "www.acierdrummond.com",
                    "notes": "Client principal - Spécialisé en structures métalliques"
                },
                {
                    "nom": "Industries Mauricie", 
                    "secteur": "FABRICATION", 
                    "type_company": "CLIENT", 
                    "adresse": "456 Boul. Manufacturing, Trois-Rivières, QC G9A 5H7",
                    "site_web": "www.industriesmauricie.ca",
                    "notes": "Fabrication de machines industrielles"
                },
                {
                    "nom": "Precision Usinage Québec", 
                    "secteur": "USINAGE", 
                    "type_company": "CLIENT", 
                    "adresse": "789 Avenue CNC, Québec, QC G1L 3K5",
                    "site_web": "www.precisionusinage.qc.ca",
                    "notes": "Pièces de précision et prototypage"
                },
                {
                    "nom": "Charpentes Beauce", 
                    "secteur": "CONSTRUCTION", 
                    "type_company": "CLIENT", 
                    "adresse": "321 Route Structure, Saint-Georges, QC G5Y 2L8",
                    "site_web": "www.charpentesbeauce.com",
                    "notes": "Charpentes métalliques commerciales et industrielles"
                },
                {
                    "nom": "Métallurgie Laval", 
                    "secteur": "METALLURGIE", 
                    "type_company": "CLIENT", 
                    "adresse": "555 Rue du Métal, Laval, QC H7L 4B2",
                    "site_web": "www.metallurgielaval.ca",
                    "notes": "Transformation de métaux spécialisés"
                }
            ]
            
            for company in companies_demo:
                query = '''
                    INSERT INTO companies (nom, secteur, type_company, adresse, site_web, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                '''
                company_id = erp_db.execute_insert(query, (
                    company['nom'], company['secteur'], company['type_company'], 
                    company['adresse'], company['site_web'], company['notes']
                ))
                if company_id:
                    company_ids.append(company_id)
                    logger.info(f"Entreprise créée: {company['nom']} (ID: {company_id})")
            
            st.success(f"✅ {len(company_ids)} entreprises créées!")
        else:
            # Récupérer les entreprises existantes
            companies = erp_db.execute_query("SELECT id FROM companies LIMIT 5")
            company_ids = [c['id'] for c in companies]
            logger.info(f"Utilisation des entreprises existantes: {len(company_ids)}")
        
        # Vérifier si des projets existent
        project_ids = []
        existing_projects = erp_db.execute_query("SELECT COUNT(*) as count FROM projects")
        if not existing_projects or existing_projects[0]['count'] == 0:
            # Créer des projets de démonstration
            projects_demo = [
                {
                    "nom_projet": "Châssis Convoyeur CV-2024-001",
                    "client_company_id": company_ids[0] if company_ids else None,
                    "statut": "EN COURS",
                    "priorite": "ÉLEVÉ",
                    "tache": "Fabrication châssis métallique pour ligne de convoyage industrielle",
                    "date_soumis": (date.today() - timedelta(days=15)).isoformat(),
                    "date_prevu": (date.today() + timedelta(days=20)).isoformat(),
                    "bd_ft_estime": 45.0,
                    "prix_estime": 28500.0,
                    "description": "Châssis métallique robuste pour convoyeur industriel haute capacité. Inclut supports, guides et systèmes de fixation."
                },
                {
                    "nom_projet": "Support Machine SM-2024-002", 
                    "client_company_id": company_ids[1] if len(company_ids) > 1 else company_ids[0] if company_ids else None,
                    "statut": "À FAIRE",
                    "priorite": "MOYEN",
                    "tache": "Support métallique pour machine de production",
                    "date_soumis": (date.today() - timedelta(days=8)).isoformat(),
                    "date_prevu": (date.today() + timedelta(days=25)).isoformat(),
                    "bd_ft_estime": 32.0,
                    "prix_estime": 19800.0,
                    "description": "Support anti-vibration pour machine de production. Nécessite précision dimensionnelle élevée."
                },
                {
                    "nom_projet": "Pièces Précision PP-2024-003",
                    "client_company_id": company_ids[2] if len(company_ids) > 2 else company_ids[0] if company_ids else None,
                    "statut": "TERMINÉ",
                    "priorite": "MOYEN", 
                    "tache": "Lot de pièces usinées haute précision",
                    "date_soumis": (date.today() - timedelta(days=45)).isoformat(),
                    "date_prevu": (date.today() - timedelta(days=3)).isoformat(),
                    "bd_ft_estime": 18.0,
                    "prix_estime": 14200.0,
                    "description": "Série de 24 pièces usinées CNC avec tolérances ±0.05mm. Matériau: Acier inox 316L."
                },
                {
                    "nom_projet": "Structure Métallique ST-2024-004",
                    "client_company_id": company_ids[3] if len(company_ids) > 3 else company_ids[0] if company_ids else None,
                    "statut": "VALIDÉ",
                    "priorite": "ÉLEVÉ",
                    "tache": "Charpente métallique pour bâtiment industriel",
                    "date_soumis": (date.today() - timedelta(days=5)).isoformat(),
                    "date_prevu": (date.today() + timedelta(days=35)).isoformat(),
                    "bd_ft_estime": 85.0,
                    "prix_estime": 65000.0,
                    "description": "Charpente métallique complète pour extension d'usine. Portée 24m, hauteur 8m."
                },
                {
                    "nom_projet": "Réparation Équipement RE-2024-005",
                    "client_company_id": company_ids[4] if len(company_ids) > 4 else company_ids[0] if company_ids else None,
                    "statut": "EN COURS",
                    "priorite": "URGENT",
                    "tache": "Réparation d'urgence équipement de production",
                    "date_soumis": (date.today() - timedelta(days=2)).isoformat(),
                    "date_prevu": (date.today() + timedelta(days=7)).isoformat(),
                    "bd_ft_estime": 12.0,
                    "prix_estime": 8500.0,
                    "description": "Réparation critique d'un bâti de machine avec renforcement et modifications."
                }
            ]
            
            for project in projects_demo:
                query = '''
                    INSERT INTO projects (nom_projet, client_company_id, statut, priorite, tache,
                                         date_soumis, date_prevu, bd_ft_estime, prix_estime, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                project_id = erp_db.execute_insert(query, (
                    project['nom_projet'], project['client_company_id'], project['statut'],
                    project['priorite'], project['tache'], project['date_soumis'], 
                    project['date_prevu'], project['bd_ft_estime'], project['prix_estime'], 
                    project['description']
                ))
                if project_id:
                    project_ids.append(project_id)
                    logger.info(f"Projet créé: {project['nom_projet']} (ID: {project_id})")
            
            st.success(f"✅ {len(project_ids)} projets créés!")
        else:
            # Récupérer les projets existants
            projects = erp_db.execute_query("SELECT id FROM projects LIMIT 5")
            project_ids = [p['id'] for p in projects]
            logger.info(f"Utilisation des projets existants: {len(project_ids)}")
            
        return project_ids
            
    except Exception as e:
        st.error(f"❌ Erreur lors de la création des projets/entreprises: {e}")
        logger.error(f"Erreur create_sample_projects_and_companies: {e}")
        return []

def create_sample_employees(erp_db):
    """Crée des employés de démonstration"""
    try:
        # Vérifier si des employés existent
        existing = erp_db.execute_query("SELECT COUNT(*) as count FROM employees")
        if existing and existing[0]['count'] > 0:
            employees = erp_db.execute_query("SELECT id FROM employees LIMIT 5")
            employee_ids = [e['id'] for e in employees]
            logger.info(f"Utilisation des employés existants: {len(employee_ids)}")
            return employee_ids
        
        employees_demo = [
            {
                "prenom": "Marie", 
                "nom": "Tremblay", 
                "email": "marie.tremblay@dgprod.com",
                "telephone": "(819) 555-0101",
                "poste": "Superviseur Production", 
                "departement": "PRODUCTION", 
                "statut": "ACTIF",
                "type_contrat": "CDI",
                "date_embauche": "2020-03-15",
                "salaire": 68000.0,
                "charge_travail": 85,
                "notes": "Superviseur expérimenté, spécialisé en gestion d'équipes de production"
            },
            {
                "prenom": "Jean", 
                "nom": "Bouchard", 
                "email": "jean.bouchard@dgprod.com",
                "telephone": "(819) 555-0102",
                "poste": "Soudeur Certifié", 
                "departement": "SOUDAGE", 
                "statut": "ACTIF",
                "type_contrat": "CDI",
                "date_embauche": "2019-08-22",
                "salaire": 58000.0,
                "charge_travail": 90,
                "notes": "Certification GMAW, GTAW et SAW. Expert en soudage robotisé"
            },
            {
                "prenom": "Sophie", 
                "nom": "Gagnon", 
                "email": "sophie.gagnon@dgprod.com",
                "telephone": "(819) 555-0103",
                "poste": "Opérateur CNC", 
                "departement": "USINAGE", 
                "statut": "ACTIF",
                "type_contrat": "CDI",
                "date_embauche": "2021-01-10",
                "salaire": 54000.0,
                "charge_travail": 80,
                "notes": "Programmation et opération machines CNC, spécialiste laser et plasma"
            },
            {
                "prenom": "Daniel", 
                "nom": "Lavoie", 
                "email": "daniel.lavoie@dgprod.com",
                "telephone": "(819) 555-0104",
                "poste": "Contrôleur Qualité", 
                "departement": "QUALITE", 
                "statut": "ACTIF",
                "type_contrat": "CDI",
                "date_embauche": "2018-11-05",
                "salaire": 62000.0,
                "charge_travail": 75,
                "notes": "Métrologie avancée, certification ISO 9001. Expert MMT et instruments de mesure"
            },
            {
                "prenom": "Caroline", 
                "nom": "Dubois", 
                "email": "caroline.dubois@dgprod.com",
                "telephone": "(819) 555-0105",
                "poste": "Technicienne Méthodes", 
                "departement": "BUREAU", 
                "statut": "ACTIF",
                "type_contrat": "CDI",
                "date_embauche": "2022-06-01",
                "salaire": 59000.0,
                "charge_travail": 70,
                "notes": "Développement gammes de fabrication, optimisation processus, CAO/FAO"
            }
        ]
        
        employee_ids = []
        for emp in employees_demo:
            query = '''
                INSERT INTO employees (prenom, nom, email, telephone, poste, departement, 
                                     statut, type_contrat, date_embauche, salaire, charge_travail, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            emp_id = erp_db.execute_insert(query, (
                emp['prenom'], emp['nom'], emp['email'], emp['telephone'], emp['poste'], 
                emp['departement'], emp['statut'], emp['type_contrat'], emp['date_embauche'], 
                emp['salaire'], emp['charge_travail'], emp['notes']
            ))
            if emp_id:
                employee_ids.append(emp_id)
                logger.info(f"Employé créé: {emp['prenom']} {emp['nom']} (ID: {emp_id})")
        
        st.success(f"✅ {len(employee_ids)} employés créés!")
        return employee_ids
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la création des employés: {e}")
        logger.error(f"Erreur create_sample_employees: {e}")
        return []

def create_sample_bons_travail(erp_db, project_ids, employee_ids):
    """Crée des Bons de Travail de démonstration avec opérations complètes"""
    try:
        # Vérifier si des BT existent
        existing_bt = erp_db.execute_query("SELECT COUNT(*) as count FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL'")
        if existing_bt and existing_bt[0]['count'] > 0:
            logger.info("Bons de Travail existants trouvés")
            return  # Des BT existent déjà
        
        if not project_ids or not employee_ids:
            st.warning("⚠️ Impossible de créer des BT sans projets et employés")
            return
        
        # Récupérer des entreprises pour les BT
        companies = erp_db.execute_query("SELECT id FROM companies LIMIT 5")
        company_ids = [c['id'] for c in companies] if companies else [None] * 5
        
        # Définir les gammes d'opérations par type de projet
        gammes_operations = {
            "CHASSIS_SOUDE": [
                {"sequence": 10, "description": "Programmation découpe laser", "poste": "Programmation Bureau", "temps": 2.5, "statut": "TERMINÉ"},
                {"sequence": 20, "description": "Découpe tôles principales", "poste": "Laser CNC", "temps": 4.0, "statut": "TERMINÉ"},
                {"sequence": 30, "description": "Découpe éléments secondaires", "poste": "Plasma CNC", "temps": 2.0, "statut": "TERMINÉ"},
                {"sequence": 40, "description": "Pliage éléments", "poste": "Plieuse CNC 1", "temps": 3.5, "statut": "EN_COURS"},
                {"sequence": 50, "description": "Perçage fixations", "poste": "Perçage 1", "temps": 2.0, "statut": "À FAIRE"},
                {"sequence": 60, "description": "Pré-assemblage", "poste": "Assemblage Léger 1", "temps": 6.0, "statut": "À FAIRE"},
                {"sequence": 70, "description": "Soudage robotisé", "poste": "Robot ABB GMAW", "temps": 8.0, "statut": "À FAIRE"},
                {"sequence": 80, "description": "Finition soudure", "poste": "Soudage GMAW 1", "temps": 4.0, "statut": "À FAIRE"},
                {"sequence": 90, "description": "Meulage cordons", "poste": "Meulage 1", "temps": 3.0, "statut": "À FAIRE"},
                {"sequence": 100, "description": "Contrôle dimensionnel", "poste": "Contrôle dimensionnel", "temps": 1.5, "statut": "À FAIRE"},
                {"sequence": 110, "description": "Finition peinture", "poste": "Peinture poudre", "temps": 2.5, "statut": "À FAIRE"}
            ],
            "SUPPORT_MACHINE": [
                {"sequence": 10, "description": "Étude technique détaillée", "poste": "Programmation Bureau", "temps": 4.0, "statut": "À FAIRE"},
                {"sequence": 20, "description": "Découpe éléments principaux", "poste": "Laser CNC", "temps": 5.0, "statut": "À FAIRE"},
                {"sequence": 30, "description": "Formage précision", "poste": "Plieuse CNC 1", "temps": 3.5, "statut": "À FAIRE"},
                {"sequence": 40, "description": "Usinage surfaces contact", "poste": "Perçage 1", "temps": 4.0, "statut": "À FAIRE"},
                {"sequence": 50, "description": "Assemblage structure", "poste": "Assemblage Léger 1", "temps": 5.0, "statut": "À FAIRE"},
                {"sequence": 60, "description": "Soudage de précision", "poste": "Soudage GMAW 1", "temps": 6.0, "statut": "À FAIRE"},
                {"sequence": 70, "description": "Contrôle géométrie", "poste": "Contrôle dimensionnel", "temps": 2.0, "statut": "À FAIRE"},
                {"sequence": 80, "description": "Traitement surface", "poste": "Peinture poudre", "temps": 1.5, "statut": "À FAIRE"}
            ],
            "PIECES_PRECISION": [
                {"sequence": 10, "description": "Contrôle matière première", "poste": "Contrôle dimensionnel", "temps": 1.0, "statut": "TERMINÉ"},
                {"sequence": 20, "description": "Finition surface", "poste": "Meulage 1", "temps": 1.5, "statut": "TERMINÉ"},
                {"sequence": 30, "description": "Contrôle final dimensionnel", "poste": "Contrôle dimensionnel", "temps": 2.0, "statut": "TERMINÉ"},
                {"sequence": 40, "description": "Traitement protection", "poste": "Peinture poudre", "temps": 1.0, "statut": "TERMINÉ"}
            ],
            "STRUCTURE_LOURDE": [
                {"sequence": 10, "description": "Design et programmation", "poste": "Programmation Bureau", "temps": 8.0, "statut": "À FAIRE"},
                {"sequence": 20, "description": "Découpe gros éléments", "poste": "Plasma CNC", "temps": 12.0, "statut": "À FAIRE"},
                {"sequence": 30, "description": "Découpe précision", "poste": "Laser CNC", "temps": 6.0, "statut": "À FAIRE"},
                {"sequence": 40, "description": "Formage poutres", "poste": "Plieuse CNC 1", "temps": 8.0, "statut": "À FAIRE"},
                {"sequence": 50, "description": "Perçage assemblage", "poste": "Perçage 1", "temps": 6.0, "statut": "À FAIRE"},
                {"sequence": 60, "description": "Pré-assemblage au sol", "poste": "Assemblage Lourd", "temps": 16.0, "statut": "À FAIRE"},
                {"sequence": 70, "description": "Soudage principal", "poste": "Robot ABB GMAW", "temps": 20.0, "statut": "À FAIRE"},
                {"sequence": 80, "description": "Soudage finition", "poste": "Soudage GMAW 1", "temps": 12.0, "statut": "À FAIRE"},
                {"sequence": 90, "description": "Contrôle soudures", "poste": "Contrôle dimensionnel", "temps": 4.0, "statut": "À FAIRE"},
                {"sequence": 100, "description": "Finition meulage", "poste": "Meulage 1", "temps": 6.0, "statut": "À FAIRE"},
                {"sequence": 110, "description": "Traitement surface final", "poste": "Peinture poudre", "temps": 4.0, "statut": "À FAIRE"}
            ],
            "REPARATION": [
                {"sequence": 10, "description": "Diagnostic et analyse", "poste": "Programmation Bureau", "temps": 2.0, "statut": "TERMINÉ"},
                {"sequence": 20, "description": "Démontage partiel", "poste": "Assemblage Léger 1", "temps": 3.0, "statut": "EN_COURS"},
                {"sequence": 30, "description": "Réparation soudure", "poste": "Soudage GMAW 1", "temps": 4.0, "statut": "À FAIRE"},
                {"sequence": 40, "description": "Renforcement structure", "poste": "Soudage GMAW 1", "temps": 3.0, "statut": "À FAIRE"},
                {"sequence": 50, "description": "Finition réparation", "poste": "Meulage 1", "temps": 2.0, "statut": "À FAIRE"},
                {"sequence": 60, "description": "Contrôle réparation", "poste": "Contrôle dimensionnel", "temps": 1.0, "statut": "À FAIRE"},
                {"sequence": 70, "description": "Remontage", "poste": "Assemblage Léger 1", "temps": 2.0, "statut": "À FAIRE"}
            ]
        }
        
        bts_demo = [
            {
                "numero_document": "BT-2024-001",
                "project_id": project_ids[0],
                "company_id": company_ids[0],
                "employee_id": employee_ids[0],
                "statut": "EN_COURS",
                "priorite": "URGENT",
                "date_creation": (datetime.now() - timedelta(days=5)).isoformat(),
                "date_echeance": (date.today() + timedelta(days=15)).isoformat(),
                "montant_total": 12500.0,
                "notes": "Fabrication châssis convoyeur - Production prioritaire pour client principal",
                "metadonnees_json": '{"type_gamme": "CHASSIS_SOUDE", "temps_estime_total": 39.0, "criticite": "HAUTE"}',
                "gamme": "CHASSIS_SOUDE"
            },
            {
                "numero_document": "BT-2024-002",
                "project_id": project_ids[1] if len(project_ids) > 1 else project_ids[0],
                "company_id": company_ids[1] if len(company_ids) > 1 else company_ids[0],
                "employee_id": employee_ids[1] if len(employee_ids) > 1 else employee_ids[0],
                "statut": "VALIDÉ",
                "priorite": "NORMAL",
                "date_creation": (datetime.now() - timedelta(days=2)).isoformat(),
                "date_echeance": (date.today() + timedelta(days=22)).isoformat(),
                "montant_total": 8200.0,
                "notes": "Support machine industrielle - Précision requise pour surfaces d'appui",
                "metadonnees_json": '{"type_gamme": "SUPPORT_MACHINE", "temps_estime_total": 31.0, "criticite": "MOYENNE"}',
                "gamme": "SUPPORT_MACHINE"
            },
            {
                "numero_document": "BT-2024-003",
                "project_id": project_ids[2] if len(project_ids) > 2 else project_ids[0],
                "company_id": company_ids[2] if len(company_ids) > 2 else company_ids[0],
                "employee_id": employee_ids[2] if len(employee_ids) > 2 else employee_ids[0],
                "statut": "TERMINÉ",
                "priorite": "NORMAL",
                "date_creation": (datetime.now() - timedelta(days=30)).isoformat(),
                "date_echeance": (date.today() - timedelta(days=3)).isoformat(),
                "montant_total": 6800.0,
                "notes": "Lot pièces précision - Contrôle qualité renforcé. TERMINÉ avec succès.",
                "metadonnees_json": '{"type_gamme": "PIECES_PRECISION", "temps_estime_total": 5.5, "criticite": "FAIBLE"}',
                "gamme": "PIECES_PRECISION"
            },
            {
                "numero_document": "BT-2024-004",
                "project_id": project_ids[3] if len(project_ids) > 3 else project_ids[0],
                "company_id": company_ids[3] if len(company_ids) > 3 else company_ids[0],
                "employee_id": employee_ids[3] if len(employee_ids) > 3 else employee_ids[0],
                "statut": "APPROUVÉ",
                "priorite": "ÉLEVÉ",
                "date_creation": datetime.now().isoformat(),
                "date_echeance": (date.today() + timedelta(days=40)).isoformat(),
                "montant_total": 24500.0,
                "notes": "Charpente métallique complexe - Projet d'envergure nécessitant coordination équipes",
                "metadonnees_json": '{"type_gamme": "STRUCTURE_LOURDE", "temps_estime_total": 102.0, "criticite": "TRÈS_HAUTE"}',
                "gamme": "STRUCTURE_LOURDE"
            },
            {
                "numero_document": "BT-2024-005",
                "project_id": project_ids[4] if len(project_ids) > 4 else project_ids[0],
                "company_id": company_ids[4] if len(company_ids) > 4 else company_ids[0],
                "employee_id": employee_ids[4] if len(employee_ids) > 4 else employee_ids[0],
                "statut": "EN_COURS",
                "priorite": "CRITIQUE",
                "date_creation": (datetime.now() - timedelta(days=1)).isoformat(),
                "date_echeance": (date.today() + timedelta(days=6)).isoformat(),
                "montant_total": 4200.0,
                "notes": "URGENT - Réparation équipement critique. Production client arrêtée.",
                "metadonnees_json": '{"type_gamme": "REPARATION", "temps_estime_total": 17.0, "criticite": "CRITIQUE"}',
                "gamme": "REPARATION"
            }
        ]
        
        bt_ids_created = []
        
        for bt in bts_demo:
            try:
                # Créer le BT
                query_bt = '''
                    INSERT INTO formulaires 
                    (type_formulaire, numero_document, project_id, company_id, employee_id,
                     statut, priorite, date_creation, date_echeance, montant_total, notes, metadonnees_json)
                    VALUES ('BON_TRAVAIL', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                
                bt_id = erp_db.execute_insert(query_bt, (
                    bt['numero_document'], bt['project_id'], bt['company_id'], bt['employee_id'],
                    bt['statut'], bt['priorite'], bt['date_creation'], bt['date_echeance'],
                    bt['montant_total'], bt['notes'], bt['metadonnees_json']
                ))
                
                if bt_id:
                    bt_ids_created.append(bt_id)
                    logger.info(f"BT créé: {bt['numero_document']} (ID: {bt_id})")
                    
                    # Créer les opérations pour ce BT selon la gamme
                    gamme_type = bt['gamme']
                    operations = gammes_operations.get(gamme_type, [])
                    
                    for operation in operations:
                        # Trouver le work_center_id
                        wc_result = erp_db.execute_query(
                            "SELECT id FROM work_centers WHERE nom = ?",
                            (operation['poste'],)
                        )
                        work_center_id = wc_result[0]['id'] if wc_result else None
                        
                        query_op = '''
                            INSERT INTO operations 
                            (project_id, work_center_id, formulaire_bt_id, sequence_number, description, 
                             temps_estime, statut, poste_travail)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        '''
                        
                        op_id = erp_db.execute_insert(query_op, (
                            bt['project_id'], work_center_id, bt_id, operation['sequence'],
                            operation['description'], operation['temps'], operation['statut'],
                            operation['poste']
                        ))
                        
                        if op_id:
                            logger.info(f"  Opération créée: {operation['description']} (ID: {op_id})")
                    
                    # Assigner l'employé au BT
                    assignation_id = erp_db.assign_employee_to_bt(
                        bt_id, bt['employee_id'], 
                        f"Responsable principal du BT {bt['numero_document']}"
                    )
                    
                    if assignation_id:
                        logger.info(f"  Assignation créée: Employee {bt['employee_id']} → BT {bt_id}")
                
            except Exception as e:
                logger.error(f"Erreur création BT {bt['numero_document']}: {e}")
        
        if bt_ids_created:
            st.success(f"✅ {len(bt_ids_created)} Bons de Travail créés avec opérations complètes!")
        else:
            st.warning("⚠️ Aucun Bon de Travail n'a pu être créé")
        
        return bt_ids_created
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la création des Bons de Travail: {e}")
        logger.error(f"Erreur create_sample_bons_travail: {e}")
        return []

def initialize_demo_data_if_needed(erp_db):
    """Initialise toutes les données de démonstration si nécessaire"""
    try:
        with st.spinner("🔄 Vérification et initialisation des données de démonstration..."):
            # 1. Créer les postes de travail
            st.info("🏭 Création des postes de travail...")
            create_sample_work_centers(erp_db)
            
            # 2. Créer les projets et entreprises  
            st.info("🏢 Création des entreprises et projets...")
            project_ids = create_sample_projects_and_companies(erp_db)
            
            # 3. Créer les employés
            st.info("👥 Création des employés...")
            employee_ids = create_sample_employees(erp_db)
            
            # 4. Créer les Bons de Travail avec opérations
            if project_ids and employee_ids:
                st.info("📋 Création des Bons de Travail avec opérations...")
                create_sample_bons_travail(erp_db, project_ids, employee_ids)
            else:
                st.warning("⚠️ Impossible de créer les BT: projets ou employés manquants")
        
        st.success("✅ Initialisation des données terminée avec succès!")
        
    except Exception as e:
        st.error(f"❌ Erreur lors de l'initialisation: {e}")
        logger.error(f"Erreur initialize_demo_data_if_needed: {e}")

# =========================================================================
# FONCTIONS UTILITAIRES POUR LE GANTT
# =========================================================================

def get_company_display_name(bt_data, erp_db):
    """Récupère le nom d'affichage de l'entreprise depuis la base SQLite"""
    try:
        company_id = bt_data.get('company_id')
        if company_id:
            company_result = erp_db.execute_query(
                "SELECT nom FROM companies WHERE id = ?", 
                (company_id,)
            )
            if company_result:
                return company_result[0]['nom']
    except Exception:
        pass
    return bt_data.get('company_nom', 'N/A')

def get_project_display_name(bt_data, erp_db):
    """Récupère le nom d'affichage du projet depuis la base SQLite"""
    try:
        project_id = bt_data.get('project_id')
        if project_id:
            project_result = erp_db.execute_query(
                "SELECT nom_projet FROM projects WHERE id = ?", 
                (project_id,)
            )
            if project_result:
                return project_result[0]['nom_projet']
    except Exception:
        pass
    return bt_data.get('nom_projet', 'N/A')

def get_bt_dates(bt_dict):
    """Retourne (date_debut, date_fin) pour un Bon de Travail depuis SQLite."""
    start_date_obj, end_date_obj = None, None
    
    try:
        # Priorité aux dates de création et échéance
        start_date_str = bt_dict.get('date_creation')
        if start_date_str: 
            # Gérer les formats datetime et date
            if 'T' in start_date_str:
                start_date_obj = datetime.strptime(start_date_str.split('T')[0], "%Y-%m-%d").date()
            else:
                start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError): 
        start_date_obj = None
        
    try:
        end_date_str = bt_dict.get('date_echeance')
        if end_date_str: 
            end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError): 
        end_date_obj = None

    # Si pas de date d'échéance, estimer basé sur les opérations
    if start_date_obj and end_date_obj is None:
        operations = bt_dict.get('operations', [])
        if operations:
            # Calculer durée totale basée sur temps estimé des opérations
            total_hours = sum(op.get('temps_estime', 0) or 0 for op in operations)
            duration_days = max(1, int(total_hours / 8))  # 8h par jour
        else:
            duration_days = 7  # Default 7 jours
        end_date_obj = start_date_obj + timedelta(days=duration_days - 1)

    # Si toujours pas de dates, utiliser aujourd'hui
    if start_date_obj is None:
        start_date_obj = date.today()
    if end_date_obj is None:
        end_date_obj = start_date_obj + timedelta(days=7)

    if start_date_obj and end_date_obj and end_date_obj < start_date_obj:
        end_date_obj = start_date_obj
        
    return start_date_obj, end_date_obj

def get_operation_dates(operation_dict, bt_start_date, bt_end_date, operation_index, total_operations):
    """Calcule les dates d'une opération basée sur sa séquence dans le BT."""
    if not bt_start_date or not bt_end_date or total_operations == 0:
        return bt_start_date, bt_start_date
    
    # Calculer la durée totale du BT
    total_bt_days = (bt_end_date - bt_start_date).days + 1
    
    # Répartir les opérations sur la durée du BT
    if total_operations == 1:
        return bt_start_date, bt_end_date
    
    # Calculer la durée par opération
    days_per_operation = max(1, total_bt_days // total_operations)
    
    # Calculer les dates de cette opération
    op_start = bt_start_date + timedelta(days=operation_index * days_per_operation)
    op_end = op_start + timedelta(days=days_per_operation - 1)
    
    # Ajuster la dernière opération pour qu'elle se termine à la fin du BT
    if operation_index == total_operations - 1:
        op_end = bt_end_date
    
    return op_start, op_end

def calculate_overall_date_range_bt(bts_list_data):
    """Calcule la plage de dates minimale et maximale pour les Bons de Travail."""
    min_overall_date, max_overall_date = None, None
    if not bts_list_data:
        today = date.today()
        return today - timedelta(days=30), today + timedelta(days=60)

    for bt_item_data in bts_list_data:
        bt_start, bt_end = get_bt_dates(bt_item_data)
        
        if bt_start:
            min_overall_date = min(min_overall_date, bt_start) if min_overall_date else bt_start
        if bt_end:
            max_overall_date = max(max_overall_date, bt_end) if max_overall_date else bt_end
    
    if min_overall_date is None or max_overall_date is None:
        today = date.today()
        min_overall_date = today - timedelta(days=30)
        max_overall_date = today + timedelta(days=60)
    else:
        # Ajouter du padding
        min_overall_date -= timedelta(days=10)
        max_overall_date += timedelta(days=20)
        if (max_overall_date - min_overall_date).days < 60:
            padding_needed = 60 - (max_overall_date - min_overall_date).days
            max_overall_date += timedelta(days=padding_needed // 2)
            min_overall_date -= timedelta(days=padding_needed - (padding_needed // 2))
    
    # Aligner sur le début de la semaine
    if min_overall_date:
         min_overall_date -= timedelta(days=min_overall_date.weekday())
         
    return min_overall_date, max_overall_date

def get_text_color_for_background(hex_bg_color):
    """Détermine si le texte doit être noir ou blanc pour un bon contraste."""
    try:
        if isinstance(hex_bg_color, str) and len(hex_bg_color) == 7 and hex_bg_color.startswith('#'):
            r = int(hex_bg_color[1:3], 16)
            g = int(hex_bg_color[3:5], 16)
            b = int(hex_bg_color[5:7], 16)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return 'black' if luminance > 0.5 else 'white'
    except: 
        pass
    return 'black'

# =========================================================================
# FONCTIONS DE RÉCUPÉRATION DES DONNÉES
# =========================================================================

def get_bons_travail_with_operations(erp_db):
    """Récupère tous les Bons de Travail avec leurs opérations depuis la base SQLite."""
    try:
        # Récupérer tous les Bons de Travail avec détails complets
        bts_query = '''
            SELECT f.*, 
                   c.nom as company_nom,
                   p.nom_projet,
                   e.prenom || ' ' || e.nom as employee_nom
            FROM formulaires f
            LEFT JOIN companies c ON f.company_id = c.id
            LEFT JOIN projects p ON f.project_id = p.id
            LEFT JOIN employees e ON f.employee_id = e.id
            WHERE f.type_formulaire = 'BON_TRAVAIL'
            ORDER BY f.id DESC
        '''
        
        bts_rows = erp_db.execute_query(bts_query)
        bts_list = []
        
        for bt_row in bts_rows:
            bt_dict = dict(bt_row)
            
            # Récupérer les opérations avec détails des postes de travail
            operations_query = '''
                SELECT o.*, 
                       wc.nom as work_center_name,
                       wc.departement as work_center_departement,
                       wc.capacite_theorique as work_center_capacite,
                       wc.cout_horaire as work_center_cout_horaire,
                       wc.type_machine as work_center_type_machine,
                       wc.operateurs_requis as work_center_operateurs_requis
                FROM operations o
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE o.formulaire_bt_id = ?
                ORDER BY o.sequence_number, o.id
            '''
            
            operations_rows = erp_db.execute_query(operations_query, (bt_dict['id'],))
            bt_dict['operations'] = [dict(op_row) for op_row in operations_rows]
            
            # Récupérer les assignations d'employés
            assignations_query = '''
                SELECT bta.*, 
                       e.prenom || ' ' || e.nom as employe_nom,
                       e.poste as employe_poste,
                       e.departement as employe_departement
                FROM bt_assignations bta
                LEFT JOIN employees e ON bta.employe_id = e.id
                WHERE bta.bt_id = ?
                ORDER BY bta.date_assignation DESC
            '''
            
            assignations_rows = erp_db.execute_query(assignations_query, (bt_dict['id'],))
            bt_dict['assignations'] = [dict(assign_row) for assign_row in assignations_rows]
            
            # Récupérer les réservations de postes
            reservations_query = '''
                SELECT btr.*, 
                       wc.nom as poste_nom,
                       wc.departement as poste_departement,
                       wc.type_machine as poste_type_machine
                FROM bt_reservations_postes btr
                LEFT JOIN work_centers wc ON btr.work_center_id = wc.id
                WHERE btr.bt_id = ?
                ORDER BY btr.date_reservation DESC
            '''
            
            reservations_rows = erp_db.execute_query(reservations_query, (bt_dict['id'],))
            bt_dict['reservations_postes'] = [dict(res_row) for res_row in reservations_rows]
            
            # Récupérer les statistiques TimeTracker
            bt_dict['timetracker_stats'] = erp_db.get_statistiques_bt_timetracker(bt_dict['id'])
            
            bts_list.append(bt_dict)
        
        logger.info(f"Récupération de {len(bts_list)} Bons de Travail avec opérations")
        return bts_list
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la récupération des Bons de Travail: {e}")
        logger.error(f"Erreur get_bons_travail_with_operations: {e}")
        return []

# =========================================================================
# FONCTIONS DE PRÉPARATION DES DONNÉES GANTT
# =========================================================================

def prepare_gantt_data_bt(bts_list, erp_db, show_postes=True):
    """Prépare les données pour le diagramme Gantt avec Bons de Travail et Postes."""
    gantt_items_for_df = []
    y_axis_order = []
    
    min_gantt_date_obj, max_gantt_date_obj = calculate_overall_date_range_bt(bts_list)
    min_gantt_datetime, max_gantt_datetime = None, None
    if min_gantt_date_obj and max_gantt_date_obj:
        min_gantt_datetime = datetime.combine(min_gantt_date_obj, datetime.min.time())
        max_gantt_datetime = datetime.combine(max_gantt_date_obj, datetime.max.time())
    
    for bt_item in sorted(bts_list, key=lambda bt: bt.get('id', 0)):
        bt_id = bt_item.get('id')
        bt_numero = bt_item.get('numero_document', f'BT-{bt_id}')
        bt_nom_complet = f"📋 {bt_numero}"
        y_axis_order.append(bt_nom_complet)

        bt_debut, bt_fin = get_bt_dates(bt_item)
        
        company_name = get_company_display_name(bt_item, erp_db)
        project_name = get_project_display_name(bt_item, erp_db)
        
        texte_barre_bt = f"{bt_numero} - {company_name}"
        description_hover_bt = (
            f"Statut: {bt_item.get('statut', 'N/A')}\n"
            f"Priorité: {bt_item.get('priorite', 'N/A')}\n"
            f"Projet: {project_name}\n"
            f"Entreprise: {company_name}\n"
            f"Responsable: {bt_item.get('employee_nom', 'N/A')}\n"
            f"Créé: {bt_debut.strftime('%d %b %Y') if bt_debut else 'N/A'}\n"
            f"Échéance: {bt_fin.strftime('%d %b %Y') if bt_fin else 'N/A'}\n"
            f"Montant: {bt_item.get('montant_total', 0):,.2f}$"
        )

        if bt_debut and bt_fin:
            gantt_items_for_df.append(dict(
                Task=bt_nom_complet,
                Start=datetime.combine(bt_debut, datetime.min.time()),
                Finish=datetime.combine(bt_fin + timedelta(days=1), datetime.min.time()),
                Type='Bon de Travail',
                Color=BT_COLORS.get(bt_item.get('statut', 'DEFAULT'), BT_COLORS['DEFAULT']),
                TextOnBar=texte_barre_bt,
                Description=description_hover_bt,
                ID=f"BT{bt_id}",
                OriginalData=bt_item
            ))

        # Afficher les opérations/postes comme des sous-éléments
        if show_postes:
            operations_existantes = bt_item.get('operations', [])
            total_ops = len(operations_existantes)
            
            for i, operation_item in enumerate(sorted(operations_existantes, key=lambda op: op.get('sequence_number', 0))):
                op_id = operation_item.get('id', i+1)
                poste_nom = operation_item.get('work_center_name', 'Poste Non Assigné')
                op_description = operation_item.get('description', 'Opération')[:40]
                
                op_nom_complet = f"    🔧 {poste_nom}"
                y_axis_order.append(op_nom_complet)

                # Calculer les dates de l'opération
                op_debut, op_fin = get_operation_dates(operation_item, bt_debut, bt_fin, i, total_ops)
                        
                texte_barre_op = f"{poste_nom} - {op_description}"
                description_hover_op = (
                    f"Séquence: {operation_item.get('sequence_number', '?')}\n"
                    f"Description: {op_description}\n"
                    f"Poste: {poste_nom}\n"
                    f"Département: {operation_item.get('work_center_departement', 'N/A')}\n"
                    f"Type machine: {operation_item.get('work_center_type_machine', 'N/A')}\n"
                    f"Temps estimé: {operation_item.get('temps_estime', 0)}h\n"
                    f"Opérateurs requis: {operation_item.get('work_center_operateurs_requis', 1)}\n"
                    f"Statut: {operation_item.get('statut', 'À FAIRE')}"
                )

                gantt_items_for_df.append(dict(
                    Task=op_nom_complet,
                    Start=datetime.combine(op_debut, datetime.min.time()),
                    Finish=datetime.combine(op_fin + timedelta(days=1), datetime.min.time()),
                    Type='Poste de Travail',
                    Color=POSTE_COLORS.get(operation_item.get('statut', 'DEFAULT'), POSTE_COLORS['DEFAULT']),
                    TextOnBar=texte_barre_op,
                    Description=description_hover_op,
                    ID=f"OP{bt_id}-{op_id}",
                    OriginalData=operation_item
                ))
    
    logger.info(f"Préparation Gantt: {len(gantt_items_for_df)} éléments, plage {min_gantt_datetime} - {max_gantt_datetime}")
    return gantt_items_for_df, y_axis_order, (min_gantt_datetime, max_gantt_datetime)

def add_status_indicators_bt(df):
    """Ajoute des indicateurs de statut pour les Bons de Travail."""
    today = datetime.now().date()
    df['Status'] = 'Normal'
    
    for i, row in df.iterrows():
        finish_date = row['Finish'].date() - timedelta(days=1)
        start_date = row['Start'].date()
        
        if finish_date < today and row['Type'] == 'Bon de Travail':
            original_data = row['OriginalData']
            if original_data.get('statut') not in ['TERMINÉ', 'ANNULÉ']:
                df.at[i, 'Status'] = 'Retard'
        
        if start_date <= today <= finish_date:
            original_data = row['OriginalData']
            if original_data.get('statut') in ['EN_COURS', 'VALIDÉ']:
                df.at[i, 'Status'] = 'EnCours'
    
    df['BorderColor'] = df['Status'].map({
        'Normal': 'rgba(0,0,0,0)',
        'Retard': 'rgba(255,0,0,0.8)',
        'EnCours': 'rgba(0,128,0,0.8)',
        'Alerte': 'rgba(255,165,0,0.8)'
    })
    
    return df

# =========================================================================
# FONCTIONS DE CRÉATION DU GRAPHIQUE GANTT
# =========================================================================

def create_gantt_chart_bt(df, y_axis_order, date_range, is_mobile=False):
    """Crée un diagramme Gantt Plotly adapté pour les Bons de Travail."""
    min_gantt_datetime, max_gantt_datetime = date_range
    
    df['Color'] = df['Color'].astype(str)
    unique_colors = df['Color'].unique()
    color_map = {color_val: color_val for color_val in unique_colors}

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="Color",
        color_discrete_map=color_map,
        text="TextOnBar",
        custom_data=['Description', 'Type', 'ID', 'Start', 'Finish', 'Status']
    )
    
    df_hover_data = df.copy()
    df_hover_data['Finish_Display_Hover'] = df_hover_data['Finish'] - timedelta(days=1)
    
    text_size = 8 if is_mobile else 9
    fig.update_traces(
        customdata=df_hover_data[['Description', 'Type', 'ID', 'Start', 'Finish_Display_Hover', 'Status']],
        hovertemplate=(
            "<b>%{y}</b><br>" +
            "Type: %{customdata[1]}<br>" +
            "ID: %{customdata[2]}<br>" +
            "Début: %{customdata[3]|%d %b %Y}<br>" +
            "Fin: %{customdata[4]|%d %b %Y}<br>" +
            "Statut: %{customdata[5]}<br>" +
            "<i>%{customdata[0]}</i>" +
            "<extra></extra>"
        ),
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=text_size)
    )
    
    text_colors_on_bars = [get_text_color_for_background(bg_hex) for bg_hex in df['Color']]
    fig.update_traces(textfont_color=text_colors_on_bars)

    # Ajouter des formes pour améliorer la visualisation
    shapes = []
    if min_gantt_datetime and max_gantt_datetime:
        current_date_iter_obj = min_gantt_datetime.date()
        end_iter_date_obj = max_gantt_datetime.date() if max_gantt_datetime else current_date_iter_obj

        # Lignes horizontales de séparation
        for i in range(len(y_axis_order)):
            y_pos = len(y_axis_order) - 1 - i
            shapes.append(go.layout.Shape(
                type="line", x0=min_gantt_datetime, x1=max_gantt_datetime,
                y0=y_pos - 0.5, y1=y_pos - 0.5,
                line=dict(color="rgba(230,230,230,0.7)", width=0.5), layer="below"
            ))

        # Grille verticale et mise en évidence des weekends
        while current_date_iter_obj <= end_iter_date_obj:
            dt_min_time_current = datetime.combine(current_date_iter_obj, datetime.min.time())
            
            # Ligne de début de semaine plus épaisse
            line_color = "rgba(200,200,200,0.8)" if current_date_iter_obj.weekday() == 0 else "rgba(230,230,230,0.5)"
            line_width = 1.0 if current_date_iter_obj.weekday() == 0 else 0.5
            
            shapes.append(go.layout.Shape(
                type="line", x0=dt_min_time_current, x1=dt_min_time_current, 
                y0=0, y1=1, yref="paper",
                line=dict(color=line_color, width=line_width), layer="below"
            ))
            
            # Mise en évidence des weekends
            if current_date_iter_obj.weekday() >= 5:
                shapes.append(go.layout.Shape(
                    type="rect", 
                    x0=dt_min_time_current, 
                    x1=datetime.combine(current_date_iter_obj + timedelta(days=1), datetime.min.time()),
                    y0=0, y1=1, yref="paper",
                    fillcolor="rgba(235,235,235,0.6)", line=dict(width=0), layer="below"
                ))
                
            current_date_iter_obj += timedelta(days=1)
    
    # Ligne "Aujourd'hui" proéminente
    today_dt = datetime.now()
    shapes.append(go.layout.Shape(
        type="line", x0=today_dt, x1=today_dt,
        y0=0, y1=1, yref="paper",
        line=dict(color="rgba(255,0,0,0.8)", width=3, dash="dash")
    ))
    
    # Bordures pour statuts spéciaux (retard, en cours)
    for i, row in df.iterrows():
        if row['Status'] != 'Normal':
            task_idx = y_axis_order.index(row['Task'])
            y_pos = len(y_axis_order) - 1 - task_idx
            shapes.append(go.layout.Shape(
                type="rect",
                x0=row['Start'], x1=row['Finish'],
                y0=y_pos - 0.4, y1=y_pos + 0.4,
                line=dict(color=row['BorderColor'], width=3),
                fillcolor="rgba(0,0,0,0)",
                layer="above"
            ))
    
    fig.update_layout(shapes=shapes)

    # Configuration responsive
    if is_mobile:
        height = min(800, max(500, len(y_axis_order) * 20 + 150))
        margin_top = 80
        margin_bottom = 30
        range_selector_visible = False
        buttons = [
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=3, label="3m", step="month", stepmode="backward"),
            dict(step="all", label="Tout")
        ]
        title_font_size = 18
        tick_font_size = 8
    else:
        height = max(700, len(y_axis_order) * 32 + 250)
        margin_top = 120
        margin_bottom = 70
        range_selector_visible = True
        buttons = [
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=3, label="3m", step="month", stepmode="backward"),
            dict(count=6, label="6m", step="month", stepmode="backward"),
            dict(count=1, label="1A", step="year", stepmode="backward"),
            dict(step="all", label="Tout")
        ]
        title_font_size = 24
        tick_font_size = 10

    fig.update_layout(
        title=dict(
            text=f"📋 Planification Gantt - Bons de Travail & Postes de Travail",
            font=dict(size=title_font_size, color='#1f2937', weight='bold'),
            x=0.5,
            xanchor='center',
            y=0.96
        ),
        xaxis_title="📅 Calendrier", 
        yaxis_title="📋 Bons de Travail & 🔧 Postes",
        height=height,
        yaxis=dict(
            categoryorder='array',
            categoryarray=y_axis_order,
            autorange="reversed",
            tickfont=dict(size=tick_font_size),
            gridcolor='rgba(220,220,220,0.5)',
            gridwidth=0.5
        ),
        xaxis=dict(
            type='date',
            range=[min_gantt_datetime - timedelta(days=1), max_gantt_datetime + timedelta(days=1)] if min_gantt_datetime and max_gantt_datetime else None,
            showgrid=False,
            tickformat="%d %b\n%Y",
            dtick="M1",
            minor=dict(dtick="D7", showgrid=True, gridcolor='rgba(230,230,230,0.5)', gridwidth=0.5),
            rangeslider_visible=not is_mobile,
            rangeselector=dict(
                buttons=buttons,
                visible=range_selector_visible,
                activecolor="#3b82f6",
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="#d1d5db",
                borderwidth=1
            )
        ),
        showlegend=False,
        margin=dict(l=15 if is_mobile else 25, r=15 if is_mobile else 25, 
                    t=margin_top, b=margin_bottom),
        plot_bgcolor='rgba(252,252,252,1)',
        paper_bgcolor='rgba(249, 250, 251, 1)',
        clickmode="event+select",
        dragmode="zoom"
    )
    
    logger.info(f"Graphique Gantt créé: {len(y_axis_order)} tâches, hauteur {height}px")
    return fig

# =========================================================================
# FONCTIONS D'AFFICHAGE DES DÉTAILS
# =========================================================================

def display_selected_bt_details(bt_data, erp_db, is_mobile=False):
    """Affiche les détails complets du Bon de Travail sélectionné."""
    try:
        bt_id = bt_data.get('id')
        bt_numero = bt_data.get('numero_document', f'BT-{bt_id}')
        company_name = get_company_display_name(bt_data, erp_db)
        project_name = get_project_display_name(bt_data, erp_db)
        statut = bt_data.get('statut', 'N/A')
        
        # En-tête du BT avec badge de statut
        status_colors = {
            'BROUILLON': '#f59e0b', 'VALIDÉ': '#3b82f6', 'ENVOYÉ': '#8b5cf6',
            'APPROUVÉ': '#10b981', 'EN_COURS': '#059669', 'TERMINÉ': '#9333ea', 'ANNULÉ': '#dc2626'
        }
        status_color = status_colors.get(statut, '#6b7280')
        
        st.markdown(f"""
        <div class="bt-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 style="margin: 0; color: #1f2937;">📋 {bt_numero}</h2>
                <span class="status-badge" style="background-color: {status_color};">{statut}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Calcul de la progression
        operations = bt_data.get('operations', [])
        if operations:
            total_ops = len(operations)
            completed_ops = len([op for op in operations if op.get('statut') == 'TERMINÉ'])
            in_progress_ops = len([op for op in operations if op.get('statut') == 'EN_COURS'])
            progress_pct = int((completed_ops / total_ops) * 100) if total_ops > 0 else 0
        else:
            total_ops = 0
            completed_ops = 0
            in_progress_ops = 0
            progress_pct = 100 if statut == 'TERMINÉ' else 0
        
        # Informations de base
        if is_mobile:
            # Version mobile compacte
            st.markdown(f"""
            <div class="info-card">
                <div><strong>🏢 Entreprise:</strong> {company_name}</div>
                <div><strong>🏭 Projet:</strong> {project_name}</div>
                <div><strong>⭐ Priorité:</strong> {bt_data.get('priorite', 'N/A')}</div>
                <div><strong>📅 Créé:</strong> {bt_data.get('date_creation', 'N/A')}</div>
                <div><strong>📅 Échéance:</strong> {bt_data.get('date_echeance', 'N/A')}</div>
                <div><strong>💰 Montant:</strong> {bt_data.get('montant_total', 0):,.2f}$</div>
                <div><strong>👤 Responsable:</strong> {bt_data.get('employee_nom', 'N/A')}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Barre de progression
            st.markdown(f"""
            <div class="progress-bar-custom">
                <div class="progress-fill" style="width: {progress_pct}%;"></div>
            </div>
            <div style="text-align: center; margin: 10px 0; font-weight: 600; color: #374151;">
                Progression: {progress_pct}% ({completed_ops}/{total_ops} opérations terminées)
            </div>
            """, unsafe_allow_html=True)
            
            # Notes si présentes
            if bt_data.get('notes'):
                with st.expander("📝 Notes"):
                    st.text_area("", value=bt_data.get('notes', ''), height=100, disabled=True, label_visibility="collapsed")
                    
            # Tabs pour mobile
            tabs_mobile = st.tabs(["🔧 Opérations", "👥 Assignations", "📊 Statistiques"])
            
            with tabs_mobile[0]:
                display_operations_details(operations, is_mobile=True)
            
            with tabs_mobile[1]:
                display_assignations_details(bt_data, is_mobile=True)
            
            with tabs_mobile[2]:
                display_statistics_details(bt_data, is_mobile=True)
        
        else:  # Version desktop
            # Informations principales en colonnes
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                <div class="info-card">
                    <div><strong>🏢 Entreprise:</strong> {company_name}</div>
                </div>
                <div class="info-card">
                    <div><strong>🏭 Projet:</strong> {project_name}</div>
                </div>
                <div class="info-card">
                    <div><strong>⭐ Priorité:</strong> {bt_data.get('priorite', 'N/A')}</div>
                </div>
                <div class="info-card">
                    <div><strong>🚦 Statut:</strong> {statut}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="info-card">
                    <div><strong>📅 Date création:</strong> {bt_data.get('date_creation', 'N/A')}</div>
                </div>
                <div class="info-card">
                    <div><strong>📅 Date échéance:</strong> {bt_data.get('date_echeance', 'N/A')}</div>
                </div>
                <div class="info-card">
                    <div><strong>💰 Montant total:</strong> {bt_data.get('montant_total', 0):,.2f}$</div>
                </div>
                <div class="info-card">
                    <div><strong>👤 Responsable:</strong> {bt_data.get('employee_nom', 'N/A')}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Barre de progression desktop
            st.markdown(f"""
            <div style="margin: 20px 0;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-weight: 600; color: #374151;">Progression des opérations</span>
                    <span style="font-weight: 600; color: #059669;">{progress_pct}%</span>
                </div>
                <div class="progress-bar-custom">
                    <div class="progress-fill" style="width: {progress_pct}%;"></div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 14px; color: #6b7280;">
                    <span>✅ {completed_ops} terminées</span>
                    <span>🔄 {in_progress_ops} en cours</span>
                    <span>⏸️ {total_ops - completed_ops - in_progress_ops} à faire</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Notes si présentes
            if bt_data.get('notes'):
                st.markdown("**📝 Notes:**")
                st.text_area("", value=bt_data.get('notes', ''), height=80, disabled=True, label_visibility="collapsed")
            
            # Tabs pour desktop
            tabs_desktop = st.tabs(["🔧 Opérations/Postes", "👥 Assignations", "📊 Statistiques", "📋 Métadonnées"])
            
            with tabs_desktop[0]:
                display_operations_details(operations, is_mobile=False)
            
            with tabs_desktop[1]:
                display_assignations_details(bt_data, is_mobile=False)
            
            with tabs_desktop[2]:
                display_statistics_details(bt_data, is_mobile=False)
            
            with tabs_desktop[3]:
                display_metadata_details(bt_data)
        
        # Bouton fermer
        if st.button("✖️ Fermer les détails", use_container_width=is_mobile, key="gantt_close_bt_details"):
            st.session_state.pop('selected_bt_id', None)
            st.rerun()
    
    except Exception as e:
        st.error(f"❌ Erreur affichage détails BT: {e}")
        logger.error(f"Erreur display_selected_bt_details: {e}")

def display_operations_details(operations, is_mobile=False):
    """Affiche les détails des opérations"""
    if not operations:
        st.info("🔧 Aucune opération définie pour ce BT.")
        return
    
    if is_mobile:
        # Version mobile avec cartes
        for op in operations:
            op_status_colors = {
                'À FAIRE': '#f59e0b', 'EN_COURS': '#059669', 'TERMINÉ': '#9333ea', 'SUSPENDU': '#8b5cf6'
            }
            op_color = op_status_colors.get(op.get('statut', 'À FAIRE'), '#6b7280')
            
            st.markdown(f"""
            <div style="
                background: white;
                border-left: 4px solid {op_color};
                padding: 15px;
                margin: 10px 0;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            ">
                <div style="font-weight: 600; color: #1f2937; margin-bottom: 8px;">
                    🔧 {op.get('work_center_name', 'Poste Non Assigné')}
                </div>
                <div style="color: #6b7280; margin-bottom: 5px;">
                    📝 {op.get('description', 'N/A')}
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 14px;">
                    <span>🏭 {op.get('work_center_departement', 'N/A')}</span>
                    <span>⏱️ {op.get('temps_estime', 0)}h</span>
                </div>
                <div style="margin-top: 8px;">
                    <span style="
                        background: {op_color};
                        color: white;
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: 600;
                    ">{op.get('statut', 'À FAIRE')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        # Version desktop avec tableau
        operations_data = []
        for op in operations:
            operations_data.append({
                "Séq.": op.get('sequence_number', '?'),
                "Description": op.get('description', 'N/A'),
                "Poste de Travail": op.get('work_center_name', 'Non assigné'),
                "Département": op.get('work_center_departement', 'N/A'),
                "Type Machine": op.get('work_center_type_machine', 'N/A'),
                "Temps (h)": op.get('temps_estime', 0),
                "Opérateurs": op.get('work_center_operateurs_requis', 1),
                "Statut": op.get('statut', 'À FAIRE')
            })
        
        if operations_data:
            operations_df = pd.DataFrame(operations_data)
            st.dataframe(operations_df, use_container_width=True, height=300)

def display_assignations_details(bt_data, is_mobile=False):
    """Affiche les détails des assignations"""
    assignations = bt_data.get('assignations', [])
    reservations = bt_data.get('reservations_postes', [])
    
    if not assignations and not reservations:
        st.info("👥 Aucune assignation d'employé ou réservation de poste.")
        return
    
    # Assignations employés
    if assignations:
        st.markdown("**👥 Employés Assignés:**")
        
        if is_mobile:
            for assign in assignations:
                st.markdown(f"""
                <div class="info-card">
                    <div><strong>👤 {assign.get('employe_nom', 'N/A')}</strong></div>
                    <div>💼 {assign.get('employe_poste', 'N/A')}</div>
                    <div>🏭 {assign.get('employe_departement', 'N/A')}</div>
                    <div>📅 Assigné le: {assign.get('date_assignation', 'N/A')}</div>
                    <div>🚦 Statut: {assign.get('statut', 'N/A')}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            assignations_data = []
            for assign in assignations:
                assignations_data.append({
                    "Employé": assign.get('employe_nom', 'N/A'),
                    "Poste": assign.get('employe_poste', 'N/A'),
                    "Département": assign.get('employe_departement', 'N/A'),
                    "Date Assignation": assign.get('date_assignation', 'N/A'),
                    "Statut": assign.get('statut', 'N/A'),
                    "Notes": assign.get('notes_assignation', 'N/A')
                })
            
            if assignations_data:
                assignations_df = pd.DataFrame(assignations_data)
                st.dataframe(assignations_df, use_container_width=True)
    
    # Réservations postes
    if reservations:
        st.markdown("**🏭 Réservations de Postes:**")
        
        if is_mobile:
            for res in reservations:
                st.markdown(f"""
                <div class="info-card">
                    <div><strong>🏭 {res.get('poste_nom', 'N/A')}</strong></div>
                    <div>🏢 {res.get('poste_departement', 'N/A')}</div>
                    <div>🔧 {res.get('poste_type_machine', 'N/A')}</div>
                    <div>📅 Réservé le: {res.get('date_reservation', 'N/A')}</div>
                    <div>🚦 Statut: {res.get('statut', 'N/A')}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            reservations_data = []
            for res in reservations:
                reservations_data.append({
                    "Poste": res.get('poste_nom', 'N/A'),
                    "Département": res.get('poste_departement', 'N/A'),
                    "Type Machine": res.get('poste_type_machine', 'N/A'),
                    "Date Réservation": res.get('date_reservation', 'N/A'),
                    "Date Prévue": res.get('date_prevue', 'N/A'),
                    "Statut": res.get('statut', 'N/A')
                })
            
            if reservations_data:
                reservations_df = pd.DataFrame(reservations_data)
                st.dataframe(reservations_df, use_container_width=True)

def display_statistics_details(bt_data, is_mobile=False):
    """Affiche les statistiques détaillées"""
    tt_stats = bt_data.get('timetracker_stats', {})
    
    col_stats1, col_stats2 = st.columns(2)
    
    with col_stats1:
        st.markdown("**⏱️ Statistiques TimeTracker:**")
        st.markdown(f"""
        <div class="info-card">
            <div><strong>Sessions pointage:</strong> {tt_stats.get('nb_pointages', 0)}</div>
            <div><strong>Employés distincts:</strong> {tt_stats.get('nb_employes_distinct', 0)}</div>
            <div><strong>Total heures:</strong> {tt_stats.get('total_heures', 0):.1f}h</div>
            <div><strong>Coût total:</strong> {tt_stats.get('total_cout', 0):.2f}$</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_stats2:
        st.markdown("**📊 Métriques BT:**")
        operations_count = len(bt_data.get('operations', []))
        assignations_count = len(bt_data.get('assignations', []))
        total_temps_estime = sum(op.get('temps_estime', 0) for op in bt_data.get('operations', []))
        
        st.markdown(f"""
        <div class="info-card">
            <div><strong>Opérations:</strong> {operations_count}</div>
            <div><strong>Employés assignés:</strong> {assignations_count}</div>
            <div><strong>Temps estimé total:</strong> {total_temps_estime:.1f}h</div>
            <div><strong>Montant:</strong> {bt_data.get('montant_total', 0):,.2f}$</div>
        </div>
        """, unsafe_allow_html=True)

def display_metadata_details(bt_data):
    """Affiche les métadonnées du BT"""
    metadonnees_str = bt_data.get('metadonnees_json', '{}')
    try:
        metadonnees = json.loads(metadonnees_str) if metadonnees_str else {}
    except:
        metadonnees = {}
    
    if metadonnees:
        st.markdown("**🔧 Métadonnées Techniques:**")
        for key, value in metadonnees.items():
            st.markdown(f"- **{key}:** {value}")
    else:
        st.info("Aucune métadonnée disponible pour ce BT.")

def display_bt_summary_card(bt, show_operations=True, is_mobile=False):
    """Affiche une carte résumé compacte d'un Bon de Travail"""
    try:
        bt_id = bt.get('id')
        bt_numero = bt.get('numero_document', f'BT-{bt_id}')
        company_name = bt.get('company_nom', 'N/A')
        project_name = bt.get('nom_projet', 'N/A')
        statut = bt.get('statut', 'N/A')
        priorite = bt.get('priorite', 'N/A')
        montant = bt.get('montant_total', 0)
        
        # Couleurs selon statut
        status_colors = {
            'BROUILLON': '#f59e0b', 'VALIDÉ': '#3b82f6', 'ENVOYÉ': '#8b5cf6',
            'APPROUVÉ': '#10b981', 'EN_COURS': '#059669', 'TERMINÉ': '#9333ea', 'ANNULÉ': '#dc2626'
        }
        status_color = status_colors.get(statut, '#6b7280')
        
        # Calculer progression basée sur opérations
        operations = bt.get('operations', [])
        if operations:
            total_ops = len(operations)
            completed_ops = len([op for op in operations if op.get('statut') == 'TERMINÉ'])
            progress = int((completed_ops / total_ops) * 100) if total_ops > 0 else 0
        else:
            progress = 100 if statut == 'TERMINÉ' else 0
        
        with st.expander(f"📋 {bt_numero} - {statut}", expanded=False):
            col1, col2 = st.columns([3, 1] if not is_mobile else [1])
            
            with col1:
                st.markdown(f"""
                **🏭 Projet:** {project_name}  
                **🏢 Client:** {company_name}  
                **⭐ Priorité:** {priorite}  
                **💰 Montant:** {montant:,.2f}$ CAD  
                **👤 Responsable:** {bt.get('employee_nom', 'N/A')}
                """)
                
                # Barre de progression
                st.markdown(f"""
                <div class="progress-bar-custom" style="margin: 10px 0;">
                    <div class="progress-fill" style="width: {progress}%;"></div>
                </div>
                <div style="font-size: 14px; color: #6b7280;">Progression: {progress}%</div>
                """, unsafe_allow_html=True)
                
            if not is_mobile:
                with col2:
                    st.markdown(f"""
                    <div style='
                        background-color: {status_color};
                        color: white;
                        padding: 12px;
                        border-radius: 8px;
                        text-align: center;
                        font-weight: bold;
                        margin-bottom: 15px;
                    '>
                        {statut}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if operations:
                        st.metric("Opérations", f"{len(operations)}")
                        st.metric("Terminées", f"{sum(1 for op in operations if op.get('statut') == 'TERMINÉ')}")
            
            if show_operations and operations:
                st.markdown("**🔧 Opérations:**")
                for i, op in enumerate(operations[:5], 1):  # Limiter à 5 pour l'affichage
                    op_statut = op.get('statut', 'À FAIRE')
                    icon = "✅" if op_statut == "TERMINÉ" else "🔄" if op_statut == "EN_COURS" else "⏸️"
                    st.write(f"{i}. {icon} {op.get('description', 'N/A')} - {op.get('work_center_name', 'N/A')} ({op.get('temps_estime', 0)}h)")
                
                if len(operations) > 5:
                    st.caption(f"... et {len(operations) - 5} autre(s) opération(s)")
                    
    except Exception as e:
        st.error(f"❌ Erreur affichage carte BT: {e}")
        logger.error(f"Erreur display_bt_summary_card: {e}")

def is_mobile_device():
    """Estimation si l'appareil est mobile basée sur la largeur de viewport."""
    # Pour cette version, on utilise une détection simple basée sur la session
    if 'is_mobile' not in st.session_state:
        st.session_state.is_mobile = False
    
    return st.session_state.is_mobile

# =========================================================================
# APPLICATION PRINCIPALE
# =========================================================================

def app():
    """Application principale Gantt pour Bons de Travail - Version Complète Finale"""
    
    # Charger les styles CSS
    load_custom_css()
    
    # Titre principal avec design amélioré
    st.markdown("""
    <div class="main-title-gantt">
        <h1>📋 Vue Gantt - Bons de Travail & Postes de Travail</h1>
        <p>Planification et suivi en temps réel des Bons de Travail avec opérations sur postes</p>
    </div>
    """, unsafe_allow_html=True)

    # Vérifier la disponibilité de l'ERP Database
    if 'erp_db' not in st.session_state:
        st.markdown("""
        <div class="error-message">
            <h3>❌ Base de données ERP non initialisée</h3>
            <p><strong>Solution:</strong> Assurez-vous que <code>st.session_state.erp_db</code> est configuré dans votre application principale.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Bouton pour tenter une initialisation de base
        if st.button("🔧 Tenter l'initialisation ERP", type="primary"):
            try:
                # Tentative d'import et d'initialisation
                try:
                    from erp_database import ERPDatabase
                    st.session_state.erp_db = ERPDatabase()
                    st.markdown('<div class="success-message">✅ Base ERP initialisée avec succès!</div>', unsafe_allow_html=True)
                    st.rerun()
                except ImportError:
                    st.error("❌ Module 'erp_database' non trouvé. Assurez-vous que le fichier erp_database.py est présent.")
                except Exception as e:
                    st.error(f"❌ Erreur d'initialisation: {e}")
            except Exception as e:
                st.error(f"❌ Échec initialisation: {e}")
        return

    erp_db = st.session_state.erp_db
    is_mobile = is_mobile_device()

    # Section d'initialisation des données de démonstration
    with st.expander("🚀 Initialisation et gestion des données", expanded=False):
        st.markdown("""
        ### 🎯 Données de démonstration
        
        Si c'est votre première utilisation ou si vous souhaitez des données de test, 
        cliquez ci-dessous pour créer un environnement complet :
        
        - **🏭 Postes de travail** (12 postes: Laser CNC, Soudage, Assemblage, etc.)
        - **🏢 Entreprises et projets** (5 entreprises clientes avec projets variés)
        - **👥 Employés** (5 employés avec différents rôles)
        - **📋 Bons de Travail** (5 BT avec gammes d'opérations complètes)
        """)
        
        col_init1, col_init2 = st.columns(2)
        
        with col_init1:
            if st.button("🎯 Créer données de démonstration", type="primary", use_container_width=True):
                initialize_demo_data_if_needed(erp_db)
                st.rerun()
        
        with col_init2:
            # Bouton pour forcer détection mobile
            if st.button("📱 Mode Mobile", use_container_width=True):
                st.session_state.is_mobile = not st.session_state.get('is_mobile', False)
                st.rerun()

    # Récupérer les Bons de Travail
    with st.spinner("📋 Chargement des Bons de Travail..."):
        bts_list = get_bons_travail_with_operations(erp_db)
    
    if not bts_list:
        st.markdown("""
        <div class="demo-warning">
            <h3>📋 Aucun Bon de Travail trouvé</h3>
            <p><strong>💡 Suggestions:</strong></p>
            <ul>
                <li>Utilisez le bouton d'initialisation ci-dessus pour créer des données de démonstration</li>
                <li>Créez des Bons de Travail depuis votre module de gestion</li>
                <li>Vérifiez que votre base de données contient des formulaires de type 'BON_TRAVAIL'</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        return

    # Section Filtres et options avec design amélioré
    with st.container():
        st.markdown('<div class="filter-container-gantt">', unsafe_allow_html=True)
        st.markdown("### 🔍 Filtres et Options de Vue")
        
        filter_cols = st.columns(4 if not is_mobile else 2)
        
        with filter_cols[0]:
            available_statuts = ["Tous"] + sorted(list(set([bt.get('statut', 'N/A') for bt in bts_list if bt.get('statut')])))
            selected_statut = st.selectbox("📊 Statut BT:", available_statuts, key="filter_statut")
        
        with filter_cols[1]:
            available_priorities = ["Toutes"] + sorted(list(set([bt.get('priorite', 'N/A') for bt in bts_list if bt.get('priorite')])))
            selected_priority = st.selectbox("⭐ Priorité:", available_priorities, key="filter_priorite")
        
        if not is_mobile and len(filter_cols) > 2:
            with filter_cols[2]:
                show_postes = st.checkbox("🔧 Afficher postes de travail", value=True, key="show_postes")
            with filter_cols[3]:
                auto_refresh = st.checkbox("🔄 Actualisation auto", value=False, key="auto_refresh")
        else:
            # Version mobile avec options simplifiées
            show_postes = st.checkbox("🔧 Afficher postes de travail", value=True, key="show_postes_mobile")
            auto_refresh = False
        
        # Barre de recherche
        search_term = st.text_input(
            "🔍 Rechercher un BT:", 
            placeholder="Numéro, projet, entreprise, responsable...",
            key="search_bt"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Bouton retour si un BT est sélectionné
    if st.session_state.get('selected_bt_id'):
        if st.button(
            "⬅️ Retour à la vue d'ensemble", 
            key="back_button_bt", 
            on_click=lambda: st.session_state.pop('selected_bt_id', None),
            use_container_width=is_mobile
        ):
            st.rerun()
    
    # Appliquer les filtres
    filtered_bts = bts_list
    
    if selected_statut != "Tous":
        filtered_bts = [bt for bt in filtered_bts if bt.get('statut') == selected_statut]
    
    if selected_priority != "Toutes":
        filtered_bts = [bt for bt in filtered_bts if bt.get('priorite') == selected_priority]
    
    if search_term:
        term_lower = search_term.lower()
        filtered_bts = [bt for bt in filtered_bts if 
                       term_lower in str(bt.get('numero_document', '')).lower() or
                       term_lower in str(bt.get('company_nom', '')).lower() or
                       term_lower in str(bt.get('nom_projet', '')).lower() or
                       term_lower in str(bt.get('employee_nom', '')).lower() or
                       term_lower in str(bt.get('notes', '')).lower()]
    
    # Métriques rapides avec design amélioré
    st.markdown('<div class="metrics-container-gantt">', unsafe_allow_html=True)
    col_metrics = st.columns(4)
    
    with col_metrics[0]:
        st.metric("📋 Bons de Travail", len(filtered_bts), delta=f"sur {len(bts_list)} total")
    with col_metrics[1]:
        en_cours = len([bt for bt in filtered_bts if bt.get('statut') == 'EN_COURS'])
        st.metric("🚀 En cours", en_cours)
    with col_metrics[2]:
        termines = len([bt for bt in filtered_bts if bt.get('statut') == 'TERMINÉ'])
        completion_rate = int((termines / len(filtered_bts)) * 100) if filtered_bts else 0
        st.metric("✅ Terminés", termines, delta=f"{completion_rate}%")
    with col_metrics[3]:
        total_operations = sum(len(bt.get('operations', [])) for bt in filtered_bts)
        st.metric("🔧 Opérations", total_operations)
    
    st.markdown('</div>', unsafe_allow_html=True)

    # Préparer et afficher le diagramme Gantt
    if filtered_bts:
        try:
            with st.spinner("📊 Génération du diagramme Gantt..."):
                gantt_data, y_axis_order, date_range = prepare_gantt_data_bt(filtered_bts, erp_db, show_postes)
            
            if gantt_data:
                df = pd.DataFrame(gantt_data)
                df = add_status_indicators_bt(df)
                fig = create_gantt_chart_bt(df, y_axis_order, date_range, is_mobile)
                
                # Afficher le graphique avec événements de clic
                chart_event = st.plotly_chart(fig, use_container_width=True, key="gantt_chart")
                
                # Gestion des clics sur le graphique (si supporté)
                if hasattr(chart_event, 'selection') and chart_event.selection:
                    # Logique de sélection d'éléments (à implémenter selon besoin)
                    pass
                
                # Légende des couleurs avec design amélioré
                with st.expander("🎨 Légende des couleurs et statuts", expanded=False):
                    col_leg1, col_leg2 = st.columns(2)
                    
                    with col_leg1:
                        st.markdown("**📋 Statuts Bons de Travail:**")
                        for statut, color in BT_COLORS.items():
                            if statut != 'DEFAULT':
                                st.markdown(f'''
                                <div class="legend-item">
                                    <div class="legend-color" style="background-color:{color};"></div>
                                    <span>{statut}</span>
                                </div>
                                ''', unsafe_allow_html=True)
                    
                    with col_leg2:
                        st.markdown("**🔧 Statuts Opérations/Postes:**")
                        for statut, color in POSTE_COLORS.items():
                            if statut != 'DEFAULT':
                                st.markdown(f'''
                                <div class="legend-item">
                                    <div class="legend-color" style="background-color:{color};"></div>
                                    <span>{statut}</span>
                                </div>
                                ''', unsafe_allow_html=True)
                
                # Indicateurs visuels additionnels
                with st.expander("📊 Indicateurs visuels", expanded=False):
                    st.markdown("""
                    - **Ligne rouge pointillée**: Date d'aujourd'hui
                    - **Zones grises**: Weekends
                    - **Bordures colorées**: Alertes (retard, en cours urgent)
                    - **Largeur des barres**: Durée des tâches
                    - **Position verticale**: Hiérarchie BT → Opérations
                    """)
                
            else:
                st.warning("⚠️ Aucune donnée Gantt générée pour les BT sélectionnés.")
        
        except Exception as e:
            st.error(f"❌ Erreur génération Gantt: {e}")
            logger.error(f"Erreur create gantt: {e}")
            with st.expander("🐛 Détails de l'erreur", expanded=False):
                st.code(str(e))
    
    else:
        st.info("📋 Aucun Bon de Travail ne correspond aux critères de filtrage.")

    # Affichage des détails si un BT est sélectionné
    if st.session_state.get('selected_bt_id'):
        bt_id = st.session_state.selected_bt_id
        bt_data = next((bt for bt in bts_list if bt.get('id') == bt_id), None)
        
        if bt_data:
            st.markdown("---")
            st.markdown("### 📋 Détails du Bon de Travail Sélectionné")
            display_selected_bt_details(bt_data, erp_db, is_mobile)
        else:
            st.warning(f"⚠️ Bon de Travail #{bt_id} non trouvé.")
            st.session_state.pop('selected_bt_id', None)
    
    else:
        # Section détails des BT (vue d'ensemble)
        st.markdown("---")
        st.markdown("### 📋 Aperçu des Bons de Travail")
        
        # Sélecteur de nombre d'éléments à afficher
        display_count = st.slider(
            "Nombre de BT à afficher:", 
            min_value=5, 
            max_value=min(20, len(filtered_bts)), 
            value=min(10, len(filtered_bts)),
            key="display_count"
        )
        
        # Afficher les cartes résumé
        for bt in filtered_bts[:display_count]:
            display_bt_summary_card(bt, show_operations=True, is_mobile=is_mobile)
        
        if len(filtered_bts) > display_count:
            st.info(f"ℹ️ Affichage des {display_count} premiers BT. Total: {len(filtered_bts)} BT correspondent aux filtres.")
        
        # Instructions d'utilisation pour mobile
        if is_mobile:
            st.markdown("""
            <div class="info-card">
                <h4>📱 Instructions Mobile</h4>
                <p>• Touchez les barres du Gantt pour voir les détails</p>
                <p>• Utilisez les filtres pour affiner la vue</p>
                <p>• Faites défiler horizontalement pour naviguer dans le temps</p>
                <p>• Pincez pour zoomer sur le graphique</p>
            </div>
            """, unsafe_allow_html=True)

    # Instructions d'utilisation complètes
    with st.expander("💡 Guide d'utilisation complet", expanded=False):
        st.markdown("""
        ## 🎯 Comment utiliser cette vue Gantt
        
        ### 📋 Éléments Principaux
        - **Bons de Travail (barres principales)**: Chaque BT apparaît comme une barre principale avec son numéro et statut
        - **Opérations/Postes (sous-barres)**: Si activé, les opérations de chaque BT sont affichées avec leurs postes assignés
        
        ### 🔍 Navigation et Filtres
        - **Filtres de statut**: Concentrez-vous sur certains états (EN_COURS, TERMINÉ, etc.)
        - **Filtres de priorité**: Affichez seulement les BT URGENT, CRITIQUE, etc.
        - **Recherche textuelle**: Trouvez rapidement un BT par numéro, projet ou entreprise
        - **Affichage postes**: Activez/désactivez la vue détaillée des opérations
        
        ### 📅 Navigation Temporelle
        - **Boutons de période**: Utilisez 1m, 3m, 6m, 1A, Tout pour naviguer
        - **Zoom manuel**: Faites glisser pour sélectionner une période
        - **Ligne rouge**: Indique la date d'aujourd'hui
        - **Weekends**: Mis en évidence en gris
        
        ### 🎨 Code Couleur
        - **Statuts BT**: Chaque statut a sa couleur (voir légende)
        - **Statuts Opérations**: Différenciation des états d'avancement
        - **Bordures spéciales**: Alertes pour retards ou urgences
        
        ### 📊 Métriques et Analyse
        - **Compteurs en temps réel**: Total BT, en cours, terminés, opérations
        - **Taux de completion**: Pourcentage de BT terminés
        - **Progression individuelle**: Barre de progression par BT
        
        ### 🖱️ Interactions
        - **Survol**: Affichez les détails en survolant les barres
        - **Clic**: Sélectionnez un BT pour voir tous ses détails
        - **Cartes détails**: Explorez les opérations, assignations, statistiques
        
        ### 🔄 Actualisation
        - **Données en temps réel**: Les données sont mises à jour à chaque interaction
        - **Auto-refresh**: Option d'actualisation automatique (si activée)
        
        ### 💡 Conseils d'Utilisation
        - Commencez par filtrer par statut pour vous concentrer sur vos priorités
        - Utilisez la recherche pour trouver rapidement un BT spécifique
        - Activez l'affichage des postes pour voir la charge de travail détaillée
        - Consultez la légende pour interpréter les couleurs
        - Explorez les détails des BT pour voir assignations et statistiques TimeTracker
        - Surveillez les bordures colorées qui indiquent les retards ou urgences
        
        ### 🚀 Fonctionnalités Avancées
        - **Intégration TimeTracker**: Voir les heures pointées et coûts réels
        - **Gestion des assignations**: Employés assignés aux BT
        - **Réservations postes**: Planification des ressources
        - **Métadonnées techniques**: Informations détaillées sur les gammes
        - **Export possible**: Données prêtes pour rapports et analyses
        """)

    # Section informations système et performance
    with st.expander("🔧 Informations Système", expanded=False):
        col_sys1, col_sys2 = st.columns(2)
        
        with col_sys1:
            st.markdown("**📊 Statistiques de Performance:**")
            st.info(f"""
            - BT chargés: {len(bts_list)}
            - BT filtrés: {len(filtered_bts)}
            - Opérations totales: {sum(len(bt.get('operations', [])) for bt in bts_list)}
            - Mode d'affichage: {'Mobile' if is_mobile else 'Desktop'}
            """)
        
        with col_sys2:
            st.markdown("**🗄️ Base de Données:**")
            try:
                # Statistiques de la base de données
                companies_count = erp_db.execute_query("SELECT COUNT(*) as count FROM companies")[0]['count']
                projects_count = erp_db.execute_query("SELECT COUNT(*) as count FROM projects")[0]['count']
                employees_count = erp_db.execute_query("SELECT COUNT(*) as count FROM employees")[0]['count']
                work_centers_count = erp_db.execute_query("SELECT COUNT(*) as count FROM work_centers")[0]['count']
                
                st.info(f"""
                - Entreprises: {companies_count}
                - Projets: {projects_count}
                - Employés: {employees_count}
                - Postes de travail: {work_centers_count}
                """)
            except Exception as e:
                st.warning(f"Erreur lecture statistiques: {e}")

    # Auto-refresh si activé
    if auto_refresh:
        import time
        time.sleep(30)  # Refresh toutes les 30 secondes
        st.rerun()

    # Footer avec informations sur la version
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #6b7280; font-size: 14px; padding: 20px;">
        📋 <strong>Gantt Bons de Travail</strong> - Version Complète Finale<br>
        Compatible avec ERP Production DG Inc. - Intégration TimeTracker & Postes de Travail<br>
        <em>Dernière mise à jour: Interface unifiée avec fonctionnalités avancées</em>
    </div>
    """, unsafe_allow_html=True)

# =========================================================================
# FONCTIONS UTILITAIRES ADDITIONNELLES
# =========================================================================

def extract_bt_id_from_gantt_id(gantt_id):
    """Extrait l'ID du Bon de Travail à partir de l'ID d'un élément Gantt."""
    if not gantt_id:
        return None
        
    if gantt_id.startswith("BT"):
        try:
            return int(gantt_id[2:])
        except ValueError:
            return None
    elif gantt_id.startswith("OP"):
        parts = gantt_id.replace("OP", "").split('-')
        if len(parts) >= 1:
            try:
                return int(parts[0])
            except ValueError:
                return None
    return None

def calculate_bt_health_score(bt_data):
    """Calcule un score de santé pour un BT basé sur plusieurs critères"""
    try:
        score = 100
        
        # Critère 1: Respect des délais
        date_echeance = bt_data.get('date_echeance')
        if date_echeance:
            try:
                echeance = datetime.strptime(date_echeance, "%Y-%m-%d").date()
                today = date.today()
                if echeance < today and bt_data.get('statut') not in ['TERMINÉ', 'ANNULÉ']:
                    score -= 30  # Retard significatif
                elif (echeance - today).days < 3 and bt_data.get('statut') not in ['TERMINÉ', 'ANNULÉ']:
                    score -= 15  # Échéance proche
            except:
                pass
        
        # Critère 2: Progression des opérations
        operations = bt_data.get('operations', [])
        if operations:
            total_ops = len(operations)
            completed_ops = len([op for op in operations if op.get('statut') == 'TERMINÉ'])
            if total_ops > 0:
                progress_ratio = completed_ops / total_ops
                if progress_ratio < 0.2:
                    score -= 10  # Peu de progression
                elif progress_ratio > 0.8:
                    score += 5   # Bonne progression
        
        # Critère 3: Assignations
        assignations = bt_data.get('assignations', [])
        if not assignations:
            score -= 20  # Pas d'assignation
        
        # Critère 4: Priorité vs statut
        priorite = bt_data.get('priorite', 'NORMAL')
        statut = bt_data.get('statut', 'BROUILLON')
        
        if priorite in ['CRITIQUE', 'URGENT'] and statut in ['BROUILLON', 'VALIDÉ']:
            score -= 25  # Haute priorité pas encore démarrée
        
        return max(0, min(100, score))
        
    except Exception as e:
        logger.error(f"Erreur calcul health score: {e}")
        return 50  # Score neutre en cas d'erreur

def generate_bt_analytics(bts_list):
    """Génère des analytics avancées pour les BTs"""
    try:
        analytics = {
            'distribution_statuts': {},
            'distribution_priorites': {},
            'performance_temporelle': {},
            'charge_postes': {},
            'tendances': {}
        }
        
        # Distribution des statuts
        for bt in bts_list:
            statut = bt.get('statut', 'N/A')
            analytics['distribution_statuts'][statut] = analytics['distribution_statuts'].get(statut, 0) + 1
        
        # Distribution des priorités
        for bt in bts_list:
            priorite = bt.get('priorite', 'N/A')
            analytics['distribution_priorites'][priorite] = analytics['distribution_priorites'].get(priorite, 0) + 1
        
        # Charge par poste de travail
        poste_charges = {}
        for bt in bts_list:
            for op in bt.get('operations', []):
                poste = op.get('work_center_name', 'N/A')
                temps = op.get('temps_estime', 0)
                if poste not in poste_charges:
                    poste_charges[poste] = {'operations': 0, 'temps_total': 0}
                poste_charges[poste]['operations'] += 1
                poste_charges[poste]['temps_total'] += temps
        
        analytics['charge_postes'] = poste_charges
        
        # Performance temporelle
        retards = len([bt for bt in bts_list 
                      if bt.get('date_echeance') and 
                      datetime.strptime(bt['date_echeance'], "%Y-%m-%d").date() < date.today() and
                      bt.get('statut') not in ['TERMINÉ', 'ANNULÉ']])
        
        analytics['performance_temporelle'] = {
            'total_bt': len(bts_list),
            'bt_en_retard': retards,
            'taux_respect_delais': ((len(bts_list) - retards) / len(bts_list) * 100) if bts_list else 0
        }
        
        return analytics
        
    except Exception as e:
        logger.error(f"Erreur génération analytics: {e}")
        return {}

def export_gantt_data_to_csv(bts_list):
    """Exporte les données du Gantt vers un format CSV"""
    try:
        import io
        
        # Préparer les données d'export
        export_data = []
        for bt in bts_list:
            bt_base = {
                'bt_numero': bt.get('numero_document', ''),
                'bt_statut': bt.get('statut', ''),
                'bt_priorite': bt.get('priorite', ''),
                'project_nom': bt.get('nom_projet', ''),
                'company_nom': bt.get('company_nom', ''),
                'employee_nom': bt.get('employee_nom', ''),
                'date_creation': bt.get('date_creation', ''),
                'date_echeance': bt.get('date_echeance', ''),
                'montant_total': bt.get('montant_total', 0),
                'nb_operations': len(bt.get('operations', [])),
                'nb_assignations': len(bt.get('assignations', []))
            }
            export_data.append(bt_base)
        
        # Créer le DataFrame et CSV
        df_export = pd.DataFrame(export_data)
        csv_buffer = io.StringIO()
        df_export.to_csv(csv_buffer, index=False, encoding='utf-8')
        
        return csv_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Erreur export CSV: {e}")
        return None

# =========================================================================
# FONCTION DE TEST ET VALIDATION
# =========================================================================

def validate_gantt_data(bts_list):
    """Valide la cohérence des données avant affichage Gantt"""
    validation_results = {
        'is_valid': True,
        'warnings': [],
        'errors': []
    }
    
    try:
        for bt in bts_list:
            bt_numero = bt.get('numero_document', 'N/A')
            
            # Validation des dates
            date_creation = bt.get('date_creation')
            date_echeance = bt.get('date_echeance')
            
            if date_creation and date_echeance:
                try:
                    creation = datetime.strptime(date_creation.split('T')[0], "%Y-%m-%d").date()
                    echeance = datetime.strptime(date_echeance, "%Y-%m-%d").date()
                    
                    if echeance < creation:
                        validation_results['warnings'].append(
                            f"BT {bt_numero}: Date d'échéance antérieure à la création"
                        )
                except ValueError as e:
                    validation_results['errors'].append(
                        f"BT {bt_numero}: Format de date invalide - {e}"
                    )
            
            # Validation des opérations
            operations = bt.get('operations', [])
            sequences = [op.get('sequence_number') for op in operations if op.get('sequence_number')]
            if len(sequences) != len(set(sequences)) and sequences:
                validation_results['warnings'].append(
                    f"BT {bt_numero}: Numéros de séquence dupliqués dans les opérations"
                )
            
            # Validation des assignations
            if not bt.get('assignations') and bt.get('statut') in ['EN_COURS', 'TERMINÉ']:
                validation_results['warnings'].append(
                    f"BT {bt_numero}: Aucune assignation pour un BT {bt.get('statut')}"
                )
        
        if validation_results['errors']:
            validation_results['is_valid'] = False
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Erreur validation données Gantt: {e}")
        validation_results['is_valid'] = False
        validation_results['errors'].append(f"Erreur de validation: {e}")
        return validation_results

# =========================================================================
# POINT D'ENTRÉE PRINCIPAL
# =========================================================================

if __name__ == "__main__":
    # Lancement de l'application
    try:
        app()
    except Exception as e:
        st.error(f"❌ Erreur critique dans l'application Gantt: {e}")
        logger.error(f"Erreur critique app: {e}")
        
        # Affichage d'informations de debugging
        with st.expander("🐛 Informations de débogage", expanded=True):
            st.code(f"""
Erreur: {e}
Type: {type(e).__name__}

Session State Keys: {list(st.session_state.keys())}

ERP DB disponible: {'erp_db' in st.session_state}
            """)
            
            if st.button("🔄 Relancer l'application"):
                st.rerun()
