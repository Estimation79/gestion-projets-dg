# production_management.py - Gestion des Bons de Travail & Postes - Desmarais & Gagné Inc.
# Interface inspirée du fichier Bons_travail R00.html
# Intégration complète avec erp_database.py
# NOUVEAU MODULE FOCALISÉ SUR LES BONS DE TRAVAIL + GESTION POSTES DE TRAVAIL

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import json
import uuid
from typing import Dict, List, Optional, Any
import logging

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GestionnaireBonsTravail:
    """
    Gestionnaire principal pour les Bons de Travail
    Reproduit les fonctionnalités du fichier HTML en version Streamlit
    """
    
    def __init__(self, db):
        self.db = db
        self.init_session_state()
    
    def init_session_state(self):
        """Initialise les variables de session pour les BT"""
        if 'bt_current_form_data' not in st.session_state:
            st.session_state.bt_current_form_data = self.get_empty_bt_form()
        
        if 'bt_task_counter' not in st.session_state:
            st.session_state.bt_task_counter = 1
            
        if 'bt_material_counter' not in st.session_state:
            st.session_state.bt_material_counter = 1
            
        if 'bt_mode' not in st.session_state:
            st.session_state.bt_mode = 'create'  # 'create', 'edit', 'view'
            
        if 'bt_selected_id' not in st.session_state:
            st.session_state.bt_selected_id = None
            
        if 'bt_show_success' not in st.session_state:
            st.session_state.bt_show_success = False

    def get_empty_bt_form(self) -> Dict:
        """Retourne un formulaire BT vide"""
        today = datetime.now().strftime('%Y-%m-%d')
        return {
            'numero_document': self.generate_bt_number(),
            'project_name': '',
            'client_name': '',
            'project_manager': '',
            'priority': 'NORMAL',
            'start_date': today,
            'end_date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
            'work_instructions': '',
            'safety_notes': '',
            'quality_requirements': '',
            'tasks': [self.get_empty_task()],
            'materials': [self.get_empty_material()],
            'created_by': 'Utilisateur'
        }
    
    def get_empty_task(self) -> Dict:
        """Retourne une tâche vide"""
        return {
            'operation': '',
            'description': '',
            'quantity': 1,
            'planned_hours': 0.0,
            'actual_hours': 0.0,
            'assigned_to': '',
            'status': 'pending',
            'start_date': '',
            'end_date': ''
        }
    
    def get_empty_material(self) -> Dict:
        """Retourne un matériau vide"""
        return {
            'name': '',
            'description': '',
            'quantity': 1.0,
            'unit': 'pcs',
            'available': 'yes',
            'notes': ''
        }
    
    def generate_bt_number(self) -> str:
        """Génère un numéro de BT automatique"""
        try:
            year = datetime.now().year
            
            # Compter les BT existants pour cette année
            count_result = self.db.execute_query(
                "SELECT COUNT(*) as count FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL' AND numero_document LIKE ?",
                (f"BT-{year}-%",)
            )
            
            if count_result:
                count = count_result[0]['count'] + 1
            else:
                count = 1
            
            return f"BT-{year}-{count:03d}"
            
        except Exception as e:
            logger.error(f"Erreur génération numéro BT: {e}")
            return f"BT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def save_bon_travail(self, form_data: Dict) -> Optional[int]:
        """Sauvegarde un bon de travail dans la base"""
        try:
            # Créer le formulaire principal
            formulaire_data = {
                'type_formulaire': 'BON_TRAVAIL',
                'numero_document': form_data['numero_document'],
                'statut': 'BROUILLON',
                'priorite': form_data['priority'],
                'date_echeance': form_data['end_date'],
                'notes': form_data.get('work_instructions', ''),
                'metadonnees_json': json.dumps({
                    'project_name': form_data['project_name'],
                    'client_name': form_data['client_name'],
                    'project_manager': form_data['project_manager'],
                    'start_date': form_data['start_date'],
                    'safety_notes': form_data.get('safety_notes', ''),
                    'quality_requirements': form_data.get('quality_requirements', ''),
                    'created_by': form_data.get('created_by', 'Utilisateur')
                })
            }
            
            # Insérer le formulaire
            bt_id = self.db.execute_insert('''
                INSERT INTO formulaires 
                (type_formulaire, numero_document, statut, priorite, date_echeance, notes, metadonnees_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                formulaire_data['type_formulaire'],
                formulaire_data['numero_document'], 
                formulaire_data['statut'],
                formulaire_data['priorite'],
                formulaire_data['date_echeance'],
                formulaire_data['notes'],
                formulaire_data['metadonnees_json']
            ))
            
            if not bt_id:
                return None
            
            # Sauvegarder les tâches comme lignes de formulaire
            for i, task in enumerate(form_data.get('tasks', []), 1):
                if task['description']:  # Seulement si la tâche a une description
                    self.db.execute_insert('''
                        INSERT INTO formulaire_lignes 
                        (formulaire_id, sequence_ligne, description, quantite, prix_unitaire, notes_ligne)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        bt_id, i, 
                        f"{task['operation']} - {task['description']}", 
                        task['quantity'], 
                        task['planned_hours'],  # Utiliser planned_hours comme "prix"
                        json.dumps({
                            'operation': task['operation'],
                            'actual_hours': task['actual_hours'],
                            'assigned_to': task['assigned_to'],
                            'status': task['status'],
                            'start_date': task.get('start_date', ''),
                            'end_date': task.get('end_date', '')
                        })
                    ))
            
            # Sauvegarder les matériaux comme lignes spéciales
            for i, material in enumerate(form_data.get('materials', []), 1000):  # Commencer à 1000 pour différencier
                if material['name']:  # Seulement si le matériau a un nom
                    self.db.execute_insert('''
                        INSERT INTO formulaire_lignes 
                        (formulaire_id, sequence_ligne, description, quantite, unite, notes_ligne)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        bt_id, i, 
                        f"MATERIAU: {material['name']} - {material['description']}", 
                        material['quantity'], 
                        material['unit'],
                        json.dumps({
                            'type': 'material',
                            'available': material['available'],
                            'notes': material.get('notes', '')
                        })
                    ))
            
            # Enregistrer l'action dans l'historique
            self.db.execute_insert('''
                INSERT INTO formulaire_validations
                (formulaire_id, type_validation, commentaires)
                VALUES (?, 'CREATION', ?)
            ''', (bt_id, f"Bon de Travail créé par {form_data.get('created_by', 'Utilisateur')}"))
            
            logger.info(f"Bon de Travail {formulaire_data['numero_document']} sauvegardé avec ID {bt_id}")
            return bt_id
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde BT: {e}")
            return None
    
    def load_bon_travail(self, bt_id: int) -> Optional[Dict]:
        """Charge un bon de travail depuis la base"""
        try:
            # Récupérer le formulaire principal
            bt_result = self.db.execute_query('''
                SELECT * FROM formulaires 
                WHERE id = ? AND type_formulaire = 'BON_TRAVAIL'
            ''', (bt_id,))
            
            if not bt_result:
                return None
            
            bt_data = dict(bt_result[0])
            
            # Parser les métadonnées
            metadonnees = {}
            try:
                metadonnees = json.loads(bt_data.get('metadonnees_json', '{}'))
            except:
                pass
            
            # Récupérer les lignes (tâches et matériaux)
            lignes_result = self.db.execute_query('''
                SELECT * FROM formulaire_lignes 
                WHERE formulaire_id = ? 
                ORDER BY sequence_ligne
            ''', (bt_id,))
            
            tasks = []
            materials = []
            
            for ligne in lignes_result:
                ligne_data = dict(ligne)
                notes_data = {}
                try:
                    notes_data = json.loads(ligne_data.get('notes_ligne', '{}'))
                except:
                    pass
                
                if ligne_data['sequence_ligne'] >= 1000:  # Matériaux
                    # Extraire le nom du matériau de la description
                    desc = ligne_data['description']
                    if desc.startswith('MATERIAU: '):
                        desc = desc[10:]  # Enlever "MATERIAU: "
                    
                    name_desc = desc.split(' - ', 1)
                    material = {
                        'name': name_desc[0] if name_desc else desc,
                        'description': name_desc[1] if len(name_desc) > 1 else '',
                        'quantity': ligne_data.get('quantite', 1.0),
                        'unit': ligne_data.get('unite', 'pcs'),
                        'available': notes_data.get('available', 'yes'),
                        'notes': notes_data.get('notes', '')
                    }
                    materials.append(material)
                    
                else:  # Tâches
                    # Extraire l'opération de la description
                    desc = ligne_data['description']
                    op_desc = desc.split(' - ', 1)
                    
                    task = {
                        'operation': op_desc[0] if op_desc else '',
                        'description': op_desc[1] if len(op_desc) > 1 else desc,
                        'quantity': ligne_data.get('quantite', 1),
                        'planned_hours': ligne_data.get('prix_unitaire', 0.0),
                        'actual_hours': notes_data.get('actual_hours', 0.0),
                        'assigned_to': notes_data.get('assigned_to', ''),
                        'status': notes_data.get('status', 'pending'),
                        'start_date': notes_data.get('start_date', ''),
                        'end_date': notes_data.get('end_date', '')
                    }
                    tasks.append(task)
            
            # Construire le formulaire complet
            form_data = {
                'id': bt_data['id'],
                'numero_document': bt_data['numero_document'],
                'project_name': metadonnees.get('project_name', ''),
                'client_name': metadonnees.get('client_name', ''),
                'project_manager': metadonnees.get('project_manager', ''),
                'priority': bt_data.get('priorite', 'NORMAL'),
                'start_date': metadonnees.get('start_date', ''),
                'end_date': bt_data.get('date_echeance', ''),
                'work_instructions': bt_data.get('notes', ''),
                'safety_notes': metadonnees.get('safety_notes', ''),
                'quality_requirements': metadonnees.get('quality_requirements', ''),
                'tasks': tasks if tasks else [self.get_empty_task()],
                'materials': materials if materials else [self.get_empty_material()],
                'created_by': metadonnees.get('created_by', 'Utilisateur'),
                'statut': bt_data.get('statut', 'BROUILLON'),
                'date_creation': bt_data.get('created_at', ''),
                'date_modification': bt_data.get('updated_at', '')
            }
            
            return form_data
            
        except Exception as e:
            logger.error(f"Erreur chargement BT {bt_id}: {e}")
            return None
    
    def get_all_bons_travail(self) -> List[Dict]:
        """Récupère tous les bons de travail"""
        try:
            results = self.db.execute_query('''
                SELECT f.*, 
                       COUNT(fl.id) as nb_lignes,
                       COALESCE(SUM(CASE WHEN fl.sequence_ligne < 1000 THEN fl.prix_unitaire ELSE 0 END), 0) as total_heures_prevues
                FROM formulaires f
                LEFT JOIN formulaire_lignes fl ON f.id = fl.formulaire_id
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                GROUP BY f.id
                ORDER BY f.created_at DESC
            ''')
            
            bons = []
            for row in results:
                row_data = dict(row)
                
                # Parser les métadonnées
                metadonnees = {}
                try:
                    metadonnees = json.loads(row_data.get('metadonnees_json', '{}'))
                except:
                    pass
                
                bon = {
                    'id': row_data['id'],
                    'numero_document': row_data['numero_document'],
                    'project_name': metadonnees.get('project_name', 'N/A'),
                    'client_name': metadonnees.get('client_name', 'N/A'),
                    'project_manager': metadonnees.get('project_manager', 'Non assigné'),
                    'priorite': row_data.get('priorite', 'NORMAL'),
                    'statut': row_data.get('statut', 'BROUILLON'),
                    'date_creation': row_data.get('created_at', ''),
                    'date_echeance': row_data.get('date_echeance', ''),
                    'nb_lignes': row_data.get('nb_lignes', 0),
                    'total_heures_prevues': row_data.get('total_heures_prevues', 0.0)
                }
                bons.append(bon)
            
            return bons
            
        except Exception as e:
            logger.error(f"Erreur récupération BTs: {e}")
            return []
    
    def get_bt_statistics(self) -> Dict:
        """Récupère les statistiques des BT"""
        try:
            # Statistiques de base
            stats_result = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total_bt,
                    COUNT(CASE WHEN statut = 'BROUILLON' THEN 1 END) as brouillons,
                    COUNT(CASE WHEN statut = 'VALIDÉ' THEN 1 END) as valides,
                    COUNT(CASE WHEN statut = 'EN COURS' THEN 1 END) as en_cours,
                    COUNT(CASE WHEN statut = 'TERMINÉ' THEN 1 END) as termines,
                    COUNT(CASE WHEN priorite = 'CRITIQUE' THEN 1 END) as critiques,
                    COUNT(CASE WHEN priorite = 'URGENT' THEN 1 END) as urgents
                FROM formulaires 
                WHERE type_formulaire = 'BON_TRAVAIL'
            ''')
            
            if stats_result:
                stats = dict(stats_result[0])
            else:
                stats = {
                    'total_bt': 0, 'brouillons': 0, 'valides': 0, 
                    'en_cours': 0, 'termines': 0, 'critiques': 0, 'urgents': 0
                }
            
            # Statistiques TimeTracker
            tt_stats_result = self.db.execute_query('''
                SELECT 
                    COUNT(DISTINCT te.formulaire_bt_id) as bt_avec_pointages,
                    COUNT(te.id) as total_sessions,
                    COALESCE(SUM(te.total_hours), 0) as total_heures,
                    COALESCE(SUM(te.total_cost), 0) as total_cout
                FROM time_entries te
                WHERE te.formulaire_bt_id IS NOT NULL
            ''')
            
            if tt_stats_result:
                tt_stats = dict(tt_stats_result[0])
                stats.update(tt_stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur statistiques BT: {e}")
            return {}

class GestionnairePostes:
    """Gestionnaire pour les postes de travail intégré"""
    
    def __init__(self, db):
        self.db = db
        self.init_session_state()
    
    def init_session_state(self):
        """Initialise les variables de session pour les postes"""
        if 'wc_action' not in st.session_state:
            st.session_state.wc_action = 'list'  # 'list', 'create', 'edit', 'view'
        if 'wc_selected_id' not in st.session_state:
            st.session_state.wc_selected_id = None
        if 'wc_confirm_delete' not in st.session_state:
            st.session_state.wc_confirm_delete = None

def apply_dg_styles():
    """Applique les styles DG Inc. cohérents avec le HTML"""
    st.markdown("""
    <style>
    /* Variables DG Inc. */
    :root {
        --primary-color: #00A971;
        --primary-color-darker: #00673D;
        --primary-color-darkest: #004C2E;
        --primary-color-lighter: #DCFCE7;
        --background-color: #F9FAFB;
        --secondary-background-color: #FFFFFF;
        --text-color: #374151;
        --text-color-light: #6B7280;
        --border-color: #E5E7EB;
        --border-radius-md: 0.5rem;
        --box-shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    
    /* Header DG style */
    .dg-header {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-color-darker) 100%);
        color: white;
        padding: 25px 30px;
        border-radius: 12px 12px 0 0;
        margin: -1rem -1rem 1rem -1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .dg-logo-container {
        display: flex;
        align-items: center;
        gap: 15px;
    }
    
    .dg-logo-box {
        background-color: white;
        width: 60px;
        height: 40px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .dg-logo-text {
        font-family: 'Segoe UI', sans-serif;
        font-weight: 800;
        font-size: 20px;
        color: var(--primary-color);
        letter-spacing: 1px;
    }
    
    .dg-company-name {
        font-weight: 600;
        font-size: 24px;
        color: white;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    .dg-contact {
        text-align: right;
        color: rgba(255, 255, 255, 0.95);
        font-size: 14px;
        line-height: 1.4;
    }
    
    /* Section d'information */
    .dg-info-section {
        background: linear-gradient(to right, #e6f7f1, #ffffff);
        padding: 20px;
        border-radius: var(--border-radius-md);
        margin-bottom: 25px;
        border-left: 5px solid var(--primary-color);
        box-shadow: var(--box-shadow-md);
    }
    
    .dg-info-title {
        color: var(--primary-color-darker);
        margin: 0 0 15px 0;
        font-size: 24px;
        font-weight: 600;
        display: flex;
        align-items: center;
    }
    
    /* Styles pour les formulaires */
    .dg-form-container {
        background-color: var(--secondary-background-color);
        border-radius: 12px;
        box-shadow: var(--box-shadow-md);
        padding: 20px;
        margin: 10px 0;
    }
    
    /* Badges de statut */
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-block;
    }
    
    .status-brouillon { background: #fef3c7; color: #92400e; }
    .status-valide { background: #dbeafe; color: #1e40af; }
    .status-en-cours { background: #e0e7ff; color: #3730a3; }
    .status-termine { background: #d1fae5; color: #065f46; }
    .status-annule { background: #fee2e2; color: #991b1b; }
    
    .priority-critique { background: #fee2e2; color: #991b1b; }
    .priority-urgent { background: #fef3c7; color: #92400e; }
    .priority-normal { background: #d1fae5; color: #065f46; }
    
    /* Styles postes de travail */
    .wc-card {
        background: var(--primary-color-lighter);
        border-radius: var(--border-radius-md);
        padding: 20px;
        margin: 10px 0;
        box-shadow: var(--box-shadow-md);
        border-left: 4px solid var(--primary-color);
    }
    
    .wc-status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-block;
    }
    
    .wc-status-actif { background: #d1fae5; color: #065f46; }
    .wc-status-maintenance { background: #fef3c7; color: #92400e; }
    .wc-status-inactif { background: #fee2e2; color: #991b1b; }
    
    /* Tables */
    .dg-table {
        border: 1px solid var(--border-color);
        border-radius: var(--border-radius-md);
        overflow: hidden;
    }
    
    /* Boutons DG */
    .dg-btn-primary {
        background: linear-gradient(90deg, var(--primary-color) 0%, var(--primary-color-darker) 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: var(--border-radius-md);
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s;
    }
    
    .dg-btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: var(--box-shadow-md);
    }
    
    /* Navigation */
    .dg-nav-container {
        background: white;
        padding: 15px 0;
        border-bottom: 2px solid var(--border-color);
        margin-bottom: 20px;
        border-radius: var(--border-radius-md);
        box-shadow: var(--box-shadow-md);
    }
    
    /* Masquer les éléments Streamlit */
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .stApp > header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

def show_dg_header():
    """Affiche l'en-tête DG Inc. comme dans le HTML"""
    st.markdown("""
    <div class="dg-header">
        <div class="dg-logo-container">
            <div class="dg-logo-box">
                <div class="dg-logo-text">DG</div>
            </div>
            <div class="dg-company-name">Desmarais & Gagné inc.</div>
        </div>
        <div class="dg-contact">
            565 rue Maisonneuve<br>
            Granby, QC J2G 3H5<br>
            Tél.: (450) 372-9630<br>
            Téléc.: (450) 372-8122
        </div>
    </div>
    """, unsafe_allow_html=True)

def show_main_navigation():
    """Navigation principale entre BT et Postes"""
    st.markdown('<div class="dg-nav-container">', unsafe_allow_html=True)
    
    # Mode principal : BT ou Postes
    if 'main_mode' not in st.session_state:
        st.session_state.main_mode = 'bt'  # 'bt' ou 'postes'
    
    nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns(5)
    
    with nav_col1:
        if st.button("🔧 Bons de Travail", use_container_width=True, 
                     type="primary" if st.session_state.main_mode == 'bt' else "secondary"):
            st.session_state.main_mode = 'bt'
            st.session_state.bt_mode = 'create'
            st.rerun()
    
    with nav_col2:
        if st.button("🏭 Postes de Travail", use_container_width=True,
                     type="primary" if st.session_state.main_mode == 'postes' else "secondary"):
            st.session_state.main_mode = 'postes'
            st.session_state.wc_action = 'list'
            st.rerun()
    
    with nav_col3:
        if st.button("📋 Gestion", use_container_width=True):
            if st.session_state.main_mode == 'bt':
                st.session_state.bt_mode = 'manage'
            else:
                st.session_state.wc_action = 'list'
            st.rerun()
    
    with nav_col4:
        if st.button("📊 Statistiques", use_container_width=True):
            if st.session_state.main_mode == 'bt':
                st.session_state.bt_mode = 'stats'
            else:
                st.session_state.wc_action = 'stats'
            st.rerun()
    
    with nav_col5:
        if st.button("⏱️ TimeTracker Pro", use_container_width=True):
            st.session_state.page_redirect = "timetracker_pro_page"
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# ================== FONCTIONS BONS DE TRAVAIL (existantes) ==================

def show_bt_navigation():
    """Navigation secondaire pour les BT"""
    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
    
    with nav_col1:
        if st.button("🔧 Nouveau Bon", use_container_width=True, 
                     type="primary" if st.session_state.bt_mode == 'create' else "secondary"):
            st.session_state.bt_mode = 'create'
            st.session_state.bt_current_form_data = st.session_state.gestionnaire_bt.get_empty_bt_form()
            st.session_state.bt_selected_id = None
            st.rerun()
    
    with nav_col2:
        if st.button("📋 Gestion", use_container_width=True,
                     type="primary" if st.session_state.bt_mode == 'manage' else "secondary"):
            st.session_state.bt_mode = 'manage'
            st.rerun()
    
    with nav_col3:
        if st.button("📊 Stats BT", use_container_width=True,
                     type="primary" if st.session_state.bt_mode == 'stats' else "secondary"):
            st.session_state.bt_mode = 'stats'
            st.rerun()
    
    with nav_col4:
        if st.button("🔗 Opérations", use_container_width=True):
            st.info("🔗 Lien vers module opérations en développement")

def show_bt_form_section():
    """Section principale du formulaire BT"""
    gestionnaire = st.session_state.gestionnaire_bt
    form_data = st.session_state.bt_current_form_data
    
    # Titre de section
    mode_text = "Modifier" if st.session_state.bt_mode == 'edit' else "Créer"
    st.markdown(f"""
    <div class="dg-info-section">
        <h2 class="dg-info-title">🔧 {mode_text} Bon de Travail</h2>
        <p><strong>Date de création:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
        <p><strong>N° Bon de Travail:</strong> {form_data['numero_document']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Informations générales
    with st.container():
        st.markdown("### 📋 Informations Générales")
        
        col1, col2 = st.columns(2)
        
        with col1:
            form_data['project_name'] = st.text_input(
                "Nom du projet *:", 
                value=form_data.get('project_name', ''),
                placeholder="Nom du projet"
            )
            
            form_data['client_name'] = st.text_input(
                "Client *:", 
                value=form_data.get('client_name', ''),
                placeholder="Nom du client"
            )
            
            # Récupérer la liste des employés
            try:
                employees = st.session_state.gestionnaire_employes.employes if hasattr(st.session_state, 'gestionnaire_employes') else []
                employee_options = [''] + [f"{emp.get('prenom', '')} {emp.get('nom', '')}" for emp in employees if emp.get('statut') == 'ACTIF']
            except:
                employee_options = ['', 'Jean Martin', 'Marie Dubois', 'Pierre Gagnon', 'Louise Tremblay']
            
            current_manager = form_data.get('project_manager', '')
            manager_index = employee_options.index(current_manager) if current_manager in employee_options else 0
            
            form_data['project_manager'] = st.selectbox(
                "Chargé de projet:",
                options=employee_options,
                index=manager_index
            )
        
        with col2:
            priority_options = ['NORMAL', 'URGENT', 'CRITIQUE']
            priority_labels = {
                'NORMAL': '🟢 Normal',
                'URGENT': '🟡 Urgent', 
                'CRITIQUE': '🔴 Critique'
            }
            
            current_priority = form_data.get('priority', 'NORMAL')
            priority_index = priority_options.index(current_priority) if current_priority in priority_options else 0
            
            form_data['priority'] = st.selectbox(
                "Priorité:",
                options=priority_options,
                index=priority_index,
                format_func=lambda x: priority_labels.get(x, x)
            )
            
            form_data['start_date'] = st.date_input(
                "Date de début prévue:",
                value=datetime.strptime(form_data.get('start_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date()
            ).strftime('%Y-%m-%d')
            
            form_data['end_date'] = st.date_input(
                "Date de fin prévue:",
                value=datetime.strptime(form_data.get('end_date', (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')), '%Y-%m-%d').date()
            ).strftime('%Y-%m-%d')

def show_tasks_section():
    """Section des tâches et opérations"""
    form_data = st.session_state.bt_current_form_data
    
    st.markdown("### 📋 Tâches et Opérations")
    
    # Operations disponibles (en fonction des postes de travail)
    try:
        # Récupérer les postes de travail disponibles
        postes = st.session_state.erp_db.execute_query(
            "SELECT nom FROM work_centers WHERE statut = 'ACTIF' ORDER BY nom"
        )
        operation_options = [''] + [poste['nom'] for poste in postes]
    except:
        operation_options = [
            '', 'Programmation CNC', 'Découpe plasma', 'Poinçonnage', 
            'Soudage TIG', 'Assemblage', 'Meulage', 'Polissage', 'Emballage'
        ]
    
    # Employés disponibles
    try:
        employees = st.session_state.gestionnaire_employes.employes if hasattr(st.session_state, 'gestionnaire_employes') else []
        employee_options = [''] + [f"{emp.get('prenom', '')} {emp.get('nom', '')}" for emp in employees if emp.get('statut') == 'ACTIF']
    except:
        employee_options = ['', 'Technicien 1', 'Technicien 2', 'Soudeur 1', 'Soudeur 2', 'Programmeur CNC']
    
    status_options = ['pending', 'in-progress', 'completed', 'on-hold']
    status_labels = {
        'pending': 'En attente',
        'in-progress': 'En cours', 
        'completed': 'Terminé',
        'on-hold': 'En pause'
    }
    
    if 'tasks' not in form_data or not form_data['tasks']:
        form_data['tasks'] = [st.session_state.gestionnaire_bt.get_empty_task()]
    
    # Affichage des tâches
    tasks_to_remove = []
    
    for i, task in enumerate(form_data['tasks']):
        with st.expander(f"Tâche {i+1}" + (f" - {task['operation']}" if task['operation'] else ""), expanded=True):
            task_col1, task_col2, task_col3 = st.columns([2, 1, 1])
            
            with task_col1:
                # Opération
                op_index = operation_options.index(task.get('operation', '')) if task.get('operation', '') in operation_options else 0
                task['operation'] = st.selectbox(
                    "Poste/Opération:", 
                    options=operation_options,
                    index=op_index,
                    key=f"task_op_{i}"
                )
                
                # Description
                task['description'] = st.text_input(
                    "Description:", 
                    value=task.get('description', ''),
                    placeholder="Description détaillée de la tâche",
                    key=f"task_desc_{i}"
                )
            
            with task_col2:
                # Quantité
                task['quantity'] = st.number_input(
                    "Quantité:", 
                    value=task.get('quantity', 1),
                    min_value=1,
                    key=f"task_qty_{i}"
                )
                
                # Heures prévues
                task['planned_hours'] = st.number_input(
                    "Heures prévues:", 
                    value=task.get('planned_hours', 0.0),
                    min_value=0.0,
                    step=0.25,
                    key=f"task_planned_{i}"
                )
                
                # Heures réelles
                task['actual_hours'] = st.number_input(
                    "Heures réelles:", 
                    value=task.get('actual_hours', 0.0),
                    min_value=0.0,
                    step=0.25,
                    key=f"task_actual_{i}"
                )
            
            with task_col3:
                # Assigné à
                assigned_index = employee_options.index(task.get('assigned_to', '')) if task.get('assigned_to', '') in employee_options else 0
                task['assigned_to'] = st.selectbox(
                    "Assigné à:", 
                    options=employee_options,
                    index=assigned_index,
                    key=f"task_assigned_{i}"
                )
                
                # Statut
                status_index = status_options.index(task.get('status', 'pending')) if task.get('status', 'pending') in status_options else 0
                task['status'] = st.selectbox(
                    "Statut:", 
                    options=status_options,
                    index=status_index,
                    format_func=lambda x: status_labels.get(x, x),
                    key=f"task_status_{i}"
                )
                
                # Dates
                if task.get('start_date'):
                    try:
                        start_date = datetime.strptime(task['start_date'], '%Y-%m-%d').date()
                    except:
                        start_date = None
                else:
                    start_date = None
                
                task['start_date'] = st.date_input(
                    "Date début:", 
                    value=start_date,
                    key=f"task_start_{i}"
                )
                if task['start_date']:
                    task['start_date'] = task['start_date'].strftime('%Y-%m-%d')
                
                if task.get('end_date'):
                    try:
                        end_date = datetime.strptime(task['end_date'], '%Y-%m-%d').date()
                    except:
                        end_date = None
                else:
                    end_date = None
                
                task['end_date'] = st.date_input(
                    "Date fin:", 
                    value=end_date,
                    key=f"task_end_{i}"
                )
                if task['end_date']:
                    task['end_date'] = task['end_date'].strftime('%Y-%m-%d')
                
                # Bouton supprimer
                if len(form_data['tasks']) > 1:
                    if st.button("🗑️ Supprimer", key=f"del_task_{i}", type="secondary"):
                        tasks_to_remove.append(i)
    
    # Supprimer les tâches marquées
    for i in reversed(tasks_to_remove):
        form_data['tasks'].pop(i)
        st.rerun()
    
    # Bouton ajouter tâche
    col_add, col_total = st.columns([1, 2])
    with col_add:
        if st.button("➕ Ajouter une tâche", type="secondary"):
            form_data['tasks'].append(st.session_state.gestionnaire_bt.get_empty_task())
            st.rerun()
    
    with col_total:
        # Totaux
        total_planned = sum(task.get('planned_hours', 0) for task in form_data['tasks'])
        total_actual = sum(task.get('actual_hours', 0) for task in form_data['tasks'])
        
        st.markdown(f"""
        **Totaux:** 
        - Heures prévues: **{total_planned:.2f}h**
        - Heures réelles: **{total_actual:.2f}h**
        """)

def show_materials_section():
    """Section des matériaux et outils"""
    form_data = st.session_state.bt_current_form_data
    
    st.markdown("### 📝 Matériaux et Outils Requis")
    
    unit_options = ['pcs', 'kg', 'm', 'm2', 'l', 'h']
    unit_labels = {
        'pcs': 'Pièces', 'kg': 'Kilogrammes', 'm': 'Mètres', 
        'm2': 'Mètres²', 'l': 'Litres', 'h': 'Heures'
    }
    
    available_options = ['yes', 'no', 'partial', 'ordered']
    available_labels = {
        'yes': '✅ Disponible',
        'no': '❌ Non disponible', 
        'partial': '⚠️ Partiellement',
        'ordered': '📦 Commandé'
    }
    
    if 'materials' not in form_data or not form_data['materials']:
        form_data['materials'] = [st.session_state.gestionnaire_bt.get_empty_material()]
    
    # Affichage des matériaux
    materials_to_remove = []
    
    for i, material in enumerate(form_data['materials']):
        with st.expander(f"Matériau/Outil {i+1}" + (f" - {material['name']}" if material['name'] else ""), expanded=True):
            mat_col1, mat_col2, mat_col3 = st.columns([2, 1, 1])
            
            with mat_col1:
                material['name'] = st.text_input(
                    "Nom du matériau/outil:", 
                    value=material.get('name', ''),
                    placeholder="Nom du matériau/outil",
                    key=f"mat_name_{i}"
                )
                
                material['description'] = st.text_input(
                    "Description:", 
                    value=material.get('description', ''),
                    placeholder="Description détaillée",
                    key=f"mat_desc_{i}"
                )
            
            with mat_col2:
                material['quantity'] = st.number_input(
                    "Quantité:", 
                    value=material.get('quantity', 1.0),
                    min_value=0.1,
                    step=0.1,
                    key=f"mat_qty_{i}"
                )
                
                unit_index = unit_options.index(material.get('unit', 'pcs')) if material.get('unit', 'pcs') in unit_options else 0
                material['unit'] = st.selectbox(
                    "Unité:", 
                    options=unit_options,
                    index=unit_index,
                    format_func=lambda x: unit_labels.get(x, x),
                    key=f"mat_unit_{i}"
                )
            
            with mat_col3:
                available_index = available_options.index(material.get('available', 'yes')) if material.get('available', 'yes') in available_options else 0
                material['available'] = st.selectbox(
                    "Disponibilité:", 
                    options=available_options,
                    index=available_index,
                    format_func=lambda x: available_labels.get(x, x),
                    key=f"mat_avail_{i}"
                )
                
                material['notes'] = st.text_area(
                    "Notes:", 
                    value=material.get('notes', ''),
                    placeholder="Notes spéciales",
                    height=100,
                    key=f"mat_notes_{i}"
                )
                
                # Bouton supprimer
                if len(form_data['materials']) > 1:
                    if st.button("🗑️ Supprimer", key=f"del_mat_{i}", type="secondary"):
                        materials_to_remove.append(i)
    
    # Supprimer les matériaux marqués
    for i in reversed(materials_to_remove):
        form_data['materials'].pop(i)
        st.rerun()
    
    # Bouton ajouter matériau
    if st.button("➕ Ajouter un matériau/outil", type="secondary"):
        form_data['materials'].append(st.session_state.gestionnaire_bt.get_empty_material())
        st.rerun()

def show_instructions_section():
    """Section des instructions et notes"""
    form_data = st.session_state.bt_current_form_data
    
    st.markdown("### 📄 Instructions et Notes")
    
    form_data['work_instructions'] = st.text_area(
        "Instructions de travail:",
        value=form_data.get('work_instructions', ''),
        placeholder="Instructions détaillées pour l'exécution du travail...",
        height=100
    )
    
    form_data['safety_notes'] = st.text_area(
        "Notes de sécurité:",
        value=form_data.get('safety_notes', ''),
        placeholder="Consignes de sécurité particulières...",
        height=80
    )
    
    form_data['quality_requirements'] = st.text_area(
        "Exigences qualité:",
        value=form_data.get('quality_requirements', ''),
        placeholder="Standards et contrôles qualité requis...",
        height=80
    )

def show_bt_actions():
    """Boutons d'action pour le BT"""
    st.markdown("---")
    
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    
    form_data = st.session_state.bt_current_form_data
    gestionnaire = st.session_state.gestionnaire_bt
    
    with action_col1:
        if st.button("💾 Sauvegarder Bon de Travail", type="primary", use_container_width=True):
            # Validation
            if not form_data.get('project_name'):
                st.error("❌ Le nom du projet est obligatoire")
                return
            
            if not form_data.get('client_name'):
                st.error("❌ Le nom du client est obligatoire")
                return
            
            # Sauvegarder
            if st.session_state.bt_mode == 'edit' and form_data.get('id'):
                # TODO: Implémenter la modification
                st.success("✅ Modification en cours de développement")
            else:
                bt_id = gestionnaire.save_bon_travail(form_data)
                if bt_id:
                    st.success(f"✅ Bon de Travail {form_data['numero_document']} sauvegardé avec succès!")
                    st.session_state.bt_show_success = True
                    
                    # Réinitialiser le formulaire
                    st.session_state.bt_current_form_data = gestionnaire.get_empty_bt_form()
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la sauvegarde")
    
    with action_col2:
        if st.button("🖨️ Imprimer", use_container_width=True):
            st.info("📋 Fonction d'impression en développement")
    
    with action_col3:
        if st.button("📄 Exporter PDF", use_container_width=True):
            st.info("📄 Fonction PDF en développement")
    
    with action_col4:
        if st.button("🗑️ Nouveau Bon", use_container_width=True):
            if st.session_state.get('bt_form_has_changes', False):
                if st.button("⚠️ Confirmer - Perdre les modifications", type="secondary"):
                    st.session_state.bt_current_form_data = gestionnaire.get_empty_bt_form()
                    st.session_state.bt_form_has_changes = False
                    st.rerun()
            else:
                st.session_state.bt_current_form_data = gestionnaire.get_empty_bt_form()
                st.rerun()

def show_bt_management():
    """Interface de gestion des bons de travail"""
    gestionnaire = st.session_state.gestionnaire_bt
    
    st.markdown("### 📋 Gestion des Bons de Travail")
    
    # Récupérer tous les BT
    bons = gestionnaire.get_all_bons_travail()
    
    if not bons:
        st.info("📋 Aucun bon de travail trouvé. Créez votre premier bon !")
        return
    
    # Filtres
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        statuts = ['TOUS'] + list(set(bon['statut'] for bon in bons))
        statut_filter = st.selectbox("Filtrer par statut:", statuts)
    
    with filter_col2:
        priorities = ['TOUTES'] + list(set(bon['priorite'] for bon in bons))
        priority_filter = st.selectbox("Filtrer par priorité:", priorities)
    
    with filter_col3:
        search_term = st.text_input("🔍 Rechercher:", placeholder="Projet, client, numéro...")
    
    # Appliquer les filtres
    filtered_bons = bons
    
    if statut_filter != 'TOUS':
        filtered_bons = [b for b in filtered_bons if b['statut'] == statut_filter]
    
    if priority_filter != 'TOUTES':
        filtered_bons = [b for b in filtered_bons if b['priorite'] == priority_filter]
    
    if search_term:
        search_lower = search_term.lower()
        filtered_bons = [
            b for b in filtered_bons 
            if search_lower in b['numero_document'].lower() 
            or search_lower in b['project_name'].lower()
            or search_lower in b['client_name'].lower()
        ]
    
    st.markdown(f"**{len(filtered_bons)} bon(s) trouvé(s)**")
    
    # Affichage en tableau
    if filtered_bons:
        for bon in filtered_bons:
            with st.expander(f"🔧 {bon['numero_document']} - {bon['project_name']}", expanded=False):
                detail_col1, detail_col2, detail_col3 = st.columns(3)
                
                with detail_col1:
                    st.markdown(f"""
                    **Client:** {bon['client_name']}  
                    **Chargé de projet:** {bon['project_manager']}  
                    **Nb. lignes:** {bon['nb_lignes']}
                    """)
                
                with detail_col2:
                    statut_class = f"status-{bon['statut'].lower().replace(' ', '-').replace('é', 'e')}"
                    priority_class = f"priority-{bon['priorite'].lower()}"
                    
                    st.markdown(f"""
                    **Statut:** <span class="status-badge {statut_class}">{bon['statut']}</span>  
                    **Priorité:** <span class="status-badge {priority_class}">{bon['priorite']}</span>  
                    **Heures prévues:** {bon['total_heures_prevues']:.1f}h
                    """, unsafe_allow_html=True)
                
                with detail_col3:
                    st.markdown(f"""
                    **Créé le:** {bon['date_creation'][:10] if bon['date_creation'] else 'N/A'}  
                    **Échéance:** {bon['date_echeance'] if bon['date_echeance'] else 'N/A'}
                    """)
                
                # Actions
                action_detail_col1, action_detail_col2, action_detail_col3, action_detail_col4 = st.columns(4)
                
                with action_detail_col1:
                    if st.button("👁️ Voir", key=f"view_{bon['id']}"):
                        form_data = gestionnaire.load_bon_travail(bon['id'])
                        if form_data:
                            st.session_state.bt_current_form_data = form_data
                            st.session_state.bt_mode = 'view'
                            st.session_state.bt_selected_id = bon['id']
                            st.rerun()
                
                with action_detail_col2:
                    if st.button("✏️ Modifier", key=f"edit_{bon['id']}"):
                        form_data = gestionnaire.load_bon_travail(bon['id'])
                        if form_data:
                            st.session_state.bt_current_form_data = form_data
                            st.session_state.bt_mode = 'edit'
                            st.session_state.bt_selected_id = bon['id']
                            st.rerun()
                
                with action_detail_col3:
                    if st.button("⏱️ TimeTracker", key=f"tt_{bon['id']}"):
                        st.session_state.timetracker_redirect_to_bt = True
                        st.session_state.formulaire_project_preselect = bon['id']
                        st.session_state.page_redirect = "timetracker_pro_page"
                        st.rerun()
                
                with action_detail_col4:
                    if st.button("🗑️ Supprimer", key=f"del_{bon['id']}", type="secondary"):
                        st.error("🗑️ Fonction de suppression en développement")

def show_bt_statistics():
    """Affichage des statistiques des BT"""
    gestionnaire = st.session_state.gestionnaire_bt
    
    st.markdown("### 📊 Statistiques des Bons de Travail")
    
    stats = gestionnaire.get_bt_statistics()
    
    if not stats or stats.get('total_bt', 0) == 0:
        st.info("📊 Aucune donnée statistique disponible")
        return
    
    # Métriques principales
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    
    with metric_col1:
        st.metric("📋 Total BT", stats.get('total_bt', 0))
    
    with metric_col2:
        st.metric("🟢 En cours", stats.get('en_cours', 0))
    
    with metric_col3:
        st.metric("✅ Terminés", stats.get('termines', 0))
    
    with metric_col4:
        st.metric("🔴 Urgents", stats.get('urgents', 0) + stats.get('critiques', 0))
    
    # Graphiques
    if stats.get('total_bt', 0) > 0:
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Graphique par statut
            statut_data = {
                'Statut': ['Brouillons', 'Validés', 'En cours', 'Terminés'],
                'Nombre': [
                    stats.get('brouillons', 0),
                    stats.get('valides', 0), 
                    stats.get('en_cours', 0),
                    stats.get('termines', 0)
                ]
            }
            
            fig_statut = px.pie(
                values=statut_data['Nombre'],
                names=statut_data['Statut'],
                title="📈 Répartition par Statut",
                color_discrete_sequence=['#fef3c7', '#dbeafe', '#e0e7ff', '#d1fae5']
            )
            fig_statut.update_layout(height=400)
            st.plotly_chart(fig_statut, use_container_width=True)
        
        with chart_col2:
            # Graphique par priorité
            priority_data = {
                'Priorité': ['Normal', 'Urgent', 'Critique'],
                'Nombre': [
                    stats.get('total_bt', 0) - stats.get('urgents', 0) - stats.get('critiques', 0),
                    stats.get('urgents', 0),
                    stats.get('critiques', 0)
                ]
            }
            
            fig_priority = px.bar(
                x=priority_data['Priorité'],
                y=priority_data['Nombre'],
                title="📊 Répartition par Priorité",
                color=priority_data['Priorité'],
                color_discrete_map={
                    'Normal': '#10b981',
                    'Urgent': '#f59e0b', 
                    'Critique': '#ef4444'
                }
            )
            fig_priority.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_priority, use_container_width=True)
    
    # Statistiques TimeTracker
    if stats.get('bt_avec_pointages', 0) > 0:
        st.markdown("---")
        st.markdown("### ⏱️ Intégration TimeTracker")
        
        tt_col1, tt_col2, tt_col3, tt_col4 = st.columns(4)
        
        with tt_col1:
            st.metric("🔧 BT avec pointages", stats.get('bt_avec_pointages', 0))
        
        with tt_col2:
            st.metric("📊 Sessions total", stats.get('total_sessions', 0))
        
        with tt_col3:
            st.metric("⏱️ Heures total", f"{stats.get('total_heures', 0):.1f}h")
        
        with tt_col4:
            st.metric("💰 Coût total", f"{stats.get('total_cout', 0):,.0f}$")

# ================== FONCTIONS POSTES DE TRAVAIL (nouvelles) ==================

def show_work_centers_navigation():
    """Navigation secondaire pour les postes"""
    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
    
    with nav_col1:
        if st.button("📋 Liste Postes", use_container_width=True,
                     type="primary" if st.session_state.wc_action == 'list' else "secondary"):
            st.session_state.wc_action = 'list'
            st.session_state.wc_selected_id = None
            st.rerun()
    
    with nav_col2:
        if st.button("➕ Nouveau Poste", use_container_width=True,
                     type="primary" if st.session_state.wc_action == 'create' else "secondary"):
            st.session_state.wc_action = 'create'
            st.session_state.wc_selected_id = None
            st.rerun()
    
    with nav_col3:
        if st.button("📊 Stats Postes", use_container_width=True,
                     type="primary" if st.session_state.wc_action == 'stats' else "secondary"):
            st.session_state.wc_action = 'stats'
            st.rerun()
    
    with nav_col4:
        if st.button("📈 Analyses", use_container_width=True,
                     type="primary" if st.session_state.wc_action == 'analysis' else "secondary"):
            st.session_state.wc_action = 'analysis'
            st.rerun()

def show_work_centers_list():
    """Affiche la liste des postes de travail"""
    st.markdown("### 🏭 Liste des Postes de Travail")
    
    # Récupérer tous les postes
    try:
        postes = st.session_state.erp_db.execute_query('''
            SELECT wc.*, 
                   COUNT(DISTINCT o.id) as nb_operations,
                   COALESCE(SUM(te.total_hours), 0) as total_heures,
                   COALESCE(SUM(te.total_cost), 0) as total_revenus
            FROM work_centers wc
            LEFT JOIN operations o ON wc.id = o.work_center_id
            LEFT JOIN time_entries te ON o.id = te.operation_id AND te.total_cost IS NOT NULL
            GROUP BY wc.id
            ORDER BY wc.nom
        ''')
        postes = [dict(p) for p in postes]
    except Exception as e:
        st.error(f"Erreur chargement postes: {e}")
        return
    
    if not postes:
        st.info("🏭 Aucun poste de travail configuré. Commencez par créer votre premier poste !")
        if st.button("➕ Créer le premier poste", type="primary"):
            st.session_state.wc_action = 'create'
            st.rerun()
        return
    
    # Filtres
    st.markdown("#### 🔍 Filtres")
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        departements = ['TOUS'] + sorted(list(set(p['departement'] for p in postes if p['departement'])))
        dept_filter = st.selectbox("Département:", departements)
    
    with filter_col2:
        categories = ['TOUS'] + sorted(list(set(p['categorie'] for p in postes if p['categorie'])))
        cat_filter = st.selectbox("Catégorie:", categories)
    
    with filter_col3:
        search_term = st.text_input("🔍 Rechercher:", placeholder="Nom, type machine...")
    
    # Appliquer filtres
    postes_filtres = postes
    if dept_filter != 'TOUS':
        postes_filtres = [p for p in postes_filtres if p['departement'] == dept_filter]
    if cat_filter != 'TOUS':
        postes_filtres = [p for p in postes_filtres if p['categorie'] == cat_filter]
    if search_term:
        search_lower = search_term.lower()
        postes_filtres = [p for p in postes_filtres if 
                         search_lower in p['nom'].lower() or 
                         search_lower in (p['type_machine'] or '').lower()]
    
    st.markdown(f"**{len(postes_filtres)} poste(s) trouvé(s)**")
    
    # Affichage des postes
    for poste in postes_filtres:
        with st.container():
            st.markdown('<div class="wc-card">', unsafe_allow_html=True)
            
            # En-tête du poste
            header_col1, header_col2, header_col3 = st.columns([3, 2, 1])
            
            with header_col1:
                # Nom et type
                st.markdown(f"### 🏭 {poste['nom']}")
                st.markdown(f"**Type:** {poste['type_machine'] or 'N/A'}")
                st.markdown(f"**Département:** {poste['departement']} | **Catégorie:** {poste['categorie']}")
            
            with header_col2:
                # Statut
                statut_class = f"wc-status-{poste['statut'].lower()}" if poste['statut'] else "wc-status-actif"
                st.markdown(f'<span class="wc-status-badge {statut_class}">{poste["statut"]}</span>', unsafe_allow_html=True)
                
                # Capacité et opérateurs
                st.markdown(f"**Capacité:** {poste['capacite_theorique']}h/jour")
                st.markdown(f"**Opérateurs:** {poste['operateurs_requis']}")
                st.markdown(f"**Coût:** {poste['cout_horaire']:.0f}$/h")
            
            with header_col3:
                # Métriques d'utilisation
                st.metric("Opérations", poste['nb_operations'])
                st.metric("Heures", f"{poste['total_heures']:.0f}h")
                st.metric("Revenus", f"{poste['total_revenus']:,.0f}$")
            
            # Compétences requises
            if poste['competences_requises']:
                st.markdown(f"**🎯 Compétences:** {poste['competences_requises']}")
            
            # Localisation
            if poste['localisation']:
                st.markdown(f"**📍 Localisation:** {poste['localisation']}")
            
            # Actions
            action_col1, action_col2, action_col3, action_col4 = st.columns(4)
            
            with action_col1:
                if st.button("👁️ Voir", key=f"view_wc_{poste['id']}", use_container_width=True):
                    st.session_state.wc_action = 'view'
                    st.session_state.wc_selected_id = poste['id']
                    st.rerun()
            
            with action_col2:
                if st.button("✏️ Modifier", key=f"edit_wc_{poste['id']}", use_container_width=True):
                    st.session_state.wc_action = 'edit'
                    st.session_state.wc_selected_id = poste['id']
                    st.rerun()
            
            with action_col3:
                if st.button("📊 Analytics", key=f"analytics_wc_{poste['id']}", use_container_width=True):
                    st.session_state.wc_action = 'view_analytics'
                    st.session_state.wc_selected_id = poste['id']
                    st.rerun()
            
            with action_col4:
                if st.button("🗑️ Supprimer", key=f"delete_wc_{poste['id']}", type="secondary", use_container_width=True):
                    st.session_state.wc_confirm_delete = poste['id']
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Confirmation de suppression
    if st.session_state.wc_confirm_delete:
        show_delete_confirmation(st.session_state.wc_confirm_delete)

def show_work_center_form(poste_data=None):
    """Formulaire d'ajout/modification de poste"""
    is_edit = poste_data is not None
    title = "✏️ Modifier Poste" if is_edit else "➕ Nouveau Poste"
    
    st.markdown(f"### {title}")
    
    with st.form("work_center_form"):
        # Informations de base
        st.markdown("#### 📋 Informations Générales")
        
        col1, col2 = st.columns(2)
        
        with col1:
            nom = st.text_input(
                "Nom du poste *:", 
                value=poste_data.get('nom', '') if is_edit else '',
                placeholder="Ex: Robot ABB GMAW Station 1"
            )
            
            departements = ['PRODUCTION', 'USINAGE', 'QUALITE', 'LOGISTIQUE', 'MAINTENANCE', 'COMMERCIAL']
            dept_index = departements.index(poste_data['departement']) if is_edit and poste_data.get('departement') in departements else 0
            departement = st.selectbox("Département *:", departements, index=dept_index)
            
            categories = ['ROBOTIQUE', 'CNC', 'MANUEL', 'INSPECTION', 'ASSEMBLAGE', 'FINITION', 'TRANSPORT']
            cat_index = categories.index(poste_data['categorie']) if is_edit and poste_data.get('categorie') in categories else 0
            categorie = st.selectbox("Catégorie *:", categories, index=cat_index)
        
        with col2:
            type_machine = st.text_input(
                "Type de machine:", 
                value=poste_data.get('type_machine', '') if is_edit else '',
                placeholder="Ex: Robot de soudage 6 axes"
            )
            
            capacite_theorique = st.number_input(
                "Capacité théorique (h/jour):", 
                value=float(poste_data.get('capacite_theorique', 8.0)) if is_edit else 8.0,
                min_value=0.1, max_value=24.0, step=0.5
            )
            
            operateurs_requis = st.number_input(
                "Opérateurs requis:", 
                value=int(poste_data.get('operateurs_requis', 1)) if is_edit else 1,
                min_value=1, max_value=10, step=1
            )
        
        # Coûts et statut
        st.markdown("#### 💰 Coûts et Statut")
        
        col3, col4 = st.columns(2)
        
        with col3:
            cout_horaire = st.number_input(
                "Coût horaire ($):", 
                value=float(poste_data.get('cout_horaire', 50.0)) if is_edit else 50.0,
                min_value=0.0, step=5.0
            )
            
            statuts = ['ACTIF', 'MAINTENANCE', 'INACTIF']
            statut_index = statuts.index(poste_data['statut']) if is_edit and poste_data.get('statut') in statuts else 0
            statut = st.selectbox("Statut:", statuts, index=statut_index)
        
        with col4:
            localisation = st.text_input(
                "Localisation:", 
                value=poste_data.get('localisation', '') if is_edit else '',
                placeholder="Ex: Atelier A - Zone 2"
            )
        
        # Compétences
        st.markdown("#### 🎯 Compétences Requises")
        competences_requises = st.text_area(
            "Compétences requises:", 
            value=poste_data.get('competences_requises', '') if is_edit else '',
            placeholder="Ex: Soudage GMAW, Programmation Robot ABB, Lecture de plans",
            height=100
        )
        
        # Boutons
        col_submit, col_cancel = st.columns(2)
        
        with col_submit:
            submitted = st.form_submit_button(
                "💾 Sauvegarder" if is_edit else "➕ Créer Poste", 
                use_container_width=True, type="primary"
            )
        
        with col_cancel:
            cancelled = st.form_submit_button("❌ Annuler", use_container_width=True)
        
        if submitted:
            # Validation
            if not nom:
                st.error("❌ Le nom du poste est obligatoire")
                return
            
            if not departement:
                st.error("❌ Le département est obligatoire")
                return
            
            # Données du poste
            work_center_data = {
                'nom': nom,
                'departement': departement,
                'categorie': categorie,
                'type_machine': type_machine,
                'capacite_theorique': capacite_theorique,
                'operateurs_requis': operateurs_requis,
                'cout_horaire': cout_horaire,
                'competences_requises': competences_requises,
                'statut': statut,
                'localisation': localisation
            }
            
            try:
                if is_edit:
                    # Modification
                    success = st.session_state.erp_db.update_work_center(
                        st.session_state.wc_selected_id, 
                        work_center_data
                    )
                    if success:
                        st.success(f"✅ Poste {nom} modifié avec succès !")
                        st.session_state.wc_action = 'list'
                        st.session_state.wc_selected_id = None
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la modification")
                else:
                    # Création
                    poste_id = st.session_state.erp_db.add_work_center(work_center_data)
                    if poste_id:
                        st.success(f"✅ Poste {nom} créé avec succès ! ID: {poste_id}")
                        st.session_state.wc_action = 'list'
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la création")
                        
            except Exception as e:
                st.error(f"❌ Erreur: {e}")
        
        if cancelled:
            st.session_state.wc_action = 'list'
            st.session_state.wc_selected_id = None
            st.rerun()

def show_work_center_details(poste_id):
    """Affiche les détails d'un poste"""
    try:
        poste = st.session_state.erp_db.get_work_center_by_id(poste_id)
        if not poste:
            st.error("❌ Poste non trouvé")
            return
        
        st.markdown(f"### 👁️ Détails - {poste['nom']}")
        
        # Informations générales
        st.markdown('<div class="wc-card">', unsafe_allow_html=True)
        
        detail_col1, detail_col2, detail_col3 = st.columns(3)
        
        with detail_col1:
            st.markdown("#### 📋 Informations")
            st.markdown(f"**Nom:** {poste['nom']}")
            st.markdown(f"**Département:** {poste['departement']}")
            st.markdown(f"**Catégorie:** {poste['categorie']}")
            st.markdown(f"**Type:** {poste.get('type_machine', 'N/A')}")
            st.markdown(f"**Localisation:** {poste.get('localisation', 'N/A')}")
        
        with detail_col2:
            st.markdown("#### ⚙️ Capacités")
            st.markdown(f"**Capacité:** {poste['capacite_theorique']}h/jour")
            st.markdown(f"**Opérateurs:** {poste['operateurs_requis']}")
            st.markdown(f"**Coût horaire:** {poste['cout_horaire']:.0f}$/h")
            
            statut_class = f"wc-status-{poste['statut'].lower()}"
            st.markdown(f"**Statut:** <span class='wc-status-badge {statut_class}'>{poste['statut']}</span>", unsafe_allow_html=True)
        
        with detail_col3:
            st.markdown("#### 📊 Utilisation")
            st.markdown(f"**Opérations:** {poste.get('operations_count', 0)}")
            st.markdown(f"**Heures totales:** {poste.get('total_hours_tracked', 0):.0f}h")
            st.markdown(f"**Revenus générés:** {poste.get('total_revenue_generated', 0):,.0f}$")
            st.markdown(f"**Employés uniques:** {poste.get('unique_employees_used', 0)}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Compétences
        if poste.get('competences_requises'):
            st.markdown("#### 🎯 Compétences Requises")
            st.info(poste['competences_requises'])
        
        # Actions
        action_col1, action_col2 = st.columns(2)
        
        with action_col1:
            if st.button("✏️ Modifier ce poste", use_container_width=True, type="primary"):
                st.session_state.wc_action = 'edit'
                st.rerun()
        
        with action_col2:
            if st.button("📋 Retour à la liste", use_container_width=True):
                st.session_state.wc_action = 'list'
                st.session_state.wc_selected_id = None
                st.rerun()
        
    except Exception as e:
        st.error(f"❌ Erreur chargement détails: {e}")

def show_work_centers_statistics():
    """Affiche les statistiques des postes de travail"""
    st.markdown("### 📊 Statistiques des Postes de Travail")
    
    try:
        stats = st.session_state.erp_db.get_work_centers_statistics()
        
        if not stats or stats.get('total_work_centers', 0) == 0:
            st.info("📊 Aucune donnée statistique disponible")
            return
        
        # Métriques principales
        st.markdown("#### 🎯 Vue d'Ensemble")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🏭 Total Postes", stats.get('total_work_centers', 0))
        
        with col2:
            actifs = stats.get('by_status', {}).get('ACTIF', 0)
            st.metric("⚡ Postes Actifs", actifs)
        
        with col3:
            capacite = stats.get('capacity_analysis', {}).get('capacite_totale_heures_jour', 0)
            st.metric("🕐 Capacité Totale", f"{capacite:.0f}h/j")
        
        with col4:
            cout_total = stats.get('capacity_analysis', {}).get('cout_total_theorique_jour', 0)
            st.metric("💰 Coût Théorique", f"{cout_total:,.0f}$/j")
        
        # Graphiques
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Répartition par département
            dept_data = stats.get('by_department', {})
            if dept_data:
                dept_names = list(dept_data.keys())
                dept_counts = [dept_data[dept]['count'] for dept in dept_names]
                
                fig_dept = px.pie(
                    values=dept_counts,
                    names=dept_names,
                    title="📊 Répartition par Département",
                    color_discrete_sequence=['#00A971', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']
                )
                fig_dept.update_layout(height=400)
                st.plotly_chart(fig_dept, use_container_width=True)
        
        with chart_col2:
            # Répartition par catégorie
            cat_data = stats.get('by_category', {})
            if cat_data:
                cat_names = list(cat_data.keys())
                cat_counts = [cat_data[cat]['count'] for cat in cat_names]
                
                fig_cat = px.bar(
                    x=cat_names,
                    y=cat_counts,
                    title="📈 Répartition par Catégorie",
                    color=cat_names,
                    color_discrete_sequence=['#00A971', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']
                )
                fig_cat.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_cat, use_container_width=True)
        
        # Intégration TimeTracker
        tt_stats = stats.get('timetracker_integration', {})
        if tt_stats and tt_stats.get('total_pointages', 0) > 0:
            st.markdown("#### ⏱️ Intégration TimeTracker")
            
            tt_col1, tt_col2, tt_col3, tt_col4 = st.columns(4)
            
            with tt_col1:
                st.metric("Postes avec pointages", tt_stats.get('postes_avec_pointages', 0))
            with tt_col2:
                st.metric("Total pointages", tt_stats.get('total_pointages', 0))
            with tt_col3:
                st.metric("Heures totales", f"{tt_stats.get('total_heures', 0):.0f}h")
            with tt_col4:
                st.metric("Employés distincts", tt_stats.get('employes_ayant_pointe', 0))
        
    except Exception as e:
        st.error(f"❌ Erreur statistiques: {e}")

def show_work_centers_analysis():
    """Analyse avancée des postes de travail"""
    st.markdown("### 📈 Analyses Avancées")
    
    analysis_tab1, analysis_tab2 = st.tabs(["🔍 Analyse d'Utilisation", "⚠️ Goulots d'Étranglement"])
    
    with analysis_tab1:
        show_utilization_analysis()
    
    with analysis_tab2:
        show_bottleneck_analysis()

def show_utilization_analysis():
    """Analyse d'utilisation des postes"""
    st.markdown("#### 🔍 Analyse d'Utilisation")
    
    # Sélection de période
    period_days = st.selectbox("📅 Période d'analyse:", [7, 14, 30, 90], index=2)
    
    try:
        analysis = st.session_state.erp_db.get_work_center_utilization_analysis(period_days)
        
        if not analysis:
            st.info("📊 Aucune donnée d'utilisation disponible")
            return
        
        # Tableau d'analyse
        df_data = []
        for wc in analysis:
            df_data.append({
                'Poste': wc['nom'],
                'Département': wc['departement'],
                'Catégorie': wc['categorie'],
                'Capacité (h/j)': wc['capacite_theorique'],
                'Heures Réelles': f"{wc['heures_reelles']:.1f}h",
                'Utilisation %': f"{wc['taux_utilisation_pct']:.1f}%",
                'Classification': wc['classification_utilisation'],
                'Revenus': f"{wc['revenus_generes']:,.0f}$",
                'Employés': wc['employes_distincts'],
                'Projets': wc['projets_touches']
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Graphique d'utilisation
            fig_util = px.bar(
                df, 
                x='Poste', 
                y='Utilisation %',
                color='Classification',
                title=f"Taux d'Utilisation des Postes ({period_days} derniers jours)",
                color_discrete_map={
                    'TRÈS_FAIBLE': '#ef4444',
                    'FAIBLE': '#f59e0b', 
                    'MOYENNE': '#3b82f6',
                    'ÉLEVÉE': '#10b981'
                }
            )
            fig_util.update_layout(height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig_util, use_container_width=True)
    
    except Exception as e:
        st.error(f"❌ Erreur analyse utilisation: {e}")

def show_bottleneck_analysis():
    """Analyse des goulots d'étranglement"""
    st.markdown("#### ⚠️ Goulots d'Étranglement")
    
    try:
        bottlenecks = st.session_state.erp_db.get_work_center_capacity_bottlenecks()
        
        if not bottlenecks:
            st.success("✅ Aucun goulot d'étranglement détecté ! Votre production est bien équilibrée.")
            return
        
        # Affichage des goulots
        for bottleneck in bottlenecks:
            level = bottleneck['niveau_goulot']
            
            # Couleur selon le niveau
            if level == 'CRITIQUE':
                alert_type = 'error'
                icon = '🚨'
            elif level == 'ÉLEVÉ':
                alert_type = 'warning'
                icon = '⚠️'
            else:
                alert_type = 'info'
                icon = '📊'
            
            with st.container():
                if alert_type == 'error':
                    st.error(f"""
                    {icon} **GOULOT CRITIQUE** - {bottleneck['nom']}
                    
                    - **Charge:** {bottleneck['taux_charge_planifiee_pct']:.1f}% 
                    - **Opérations en attente:** {bottleneck['operations_en_attente']}
                    - **Pointages actifs:** {bottleneck['pointages_actifs']}
                    - **Département:** {bottleneck['departement']}
                    """)
                elif alert_type == 'warning':
                    st.warning(f"""
                    {icon} **GOULOT ÉLEVÉ** - {bottleneck['nom']}
                    
                    - **Charge:** {bottleneck['taux_charge_planifiee_pct']:.1f}%
                    - **Opérations en attente:** {bottleneck['operations_en_attente']}
                    - **Département:** {bottleneck['departement']}
                    """)
                else:
                    st.info(f"""
                    {icon} **Charge Modérée** - {bottleneck['nom']}
                    
                    - **Charge:** {bottleneck['taux_charge_planifiee_pct']:.1f}%
                    - **Département:** {bottleneck['departement']}
                    """)
                
                # Recommandations
                if bottleneck.get('recommandations'):
                    st.markdown("**🎯 Recommandations:**")
                    for rec in bottleneck['recommandations']:
                        st.markdown(f"- {rec}")
        
        # Graphique des charges
        if bottlenecks:
            bottleneck_names = [b['nom'] for b in bottlenecks]
            bottleneck_charges = [b['taux_charge_planifiee_pct'] for b in bottlenecks]
            bottleneck_levels = [b['niveau_goulot'] for b in bottlenecks]
            
            fig_bottleneck = px.bar(
                x=bottleneck_names,
                y=bottleneck_charges,
                color=bottleneck_levels,
                title="📊 Analyse des Goulots d'Étranglement",
                labels={'x': 'Postes', 'y': 'Charge (%)'},
                color_discrete_map={
                    'CRITIQUE': '#ef4444',
                    'ÉLEVÉ': '#f59e0b',
                    'MODÉRÉ': '#3b82f6',
                    'FAIBLE': '#10b981'
                }
            )
            fig_bottleneck.add_hline(y=100, line_dash="dash", line_color="red", 
                                   annotation_text="Capacité Maximum")
            fig_bottleneck.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_bottleneck, use_container_width=True)
    
    except Exception as e:
        st.error(f"❌ Erreur analyse goulots: {e}")

def show_delete_confirmation(poste_id):
    """Confirmation de suppression"""
    try:
        poste = st.session_state.erp_db.get_work_center_by_id(poste_id)
        if not poste:
            st.session_state.wc_confirm_delete = None
            return
        
        st.error(f"""
        ⚠️ **CONFIRMATION DE SUPPRESSION**
        
        Êtes-vous sûr de vouloir supprimer le poste **{poste['nom']}** ?
        
        Cette action est **irréversible** et supprimera :
        - Le poste de travail
        - Toutes les opérations associées
        - Toutes les réservations
        
        **⚠️ ATTENTION :** Cette action peut affecter vos projets en cours !
        """)
        
        col_confirm, col_cancel = st.columns(2)
        
        with col_confirm:
            if st.button("🗑️ CONFIRMER LA SUPPRESSION", type="primary", use_container_width=True):
                try:
                    if st.session_state.erp_db.delete_work_center(poste_id):
                        st.success(f"✅ Poste {poste['nom']} supprimé avec succès !")
                        st.session_state.wc_confirm_delete = None
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la suppression")
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
        
        with col_cancel:
            if st.button("❌ Annuler", use_container_width=True):
                st.session_state.wc_confirm_delete = None
                st.rerun()
    
    except Exception as e:
        st.error(f"❌ Erreur: {e}")

# ================== FONCTION PRINCIPALE ==================

def show_production_management_page():
    """
    Page principale du module de gestion des bons de travail et postes de travail
    Reproduit l'interface du fichier HTML en version Streamlit avec extension postes
    """
    
    # Appliquer les styles DG
    apply_dg_styles()
    
    # Initialiser les gestionnaires si nécessaires
    if 'gestionnaire_bt' not in st.session_state:
        if 'erp_db' in st.session_state:
            st.session_state.gestionnaire_bt = GestionnaireBonsTravail(st.session_state.erp_db)
        else:
            st.error("❌ Base de données ERP non disponible")
            return
    
    if 'gestionnaire_postes' not in st.session_state:
        if 'erp_db' in st.session_state:
            st.session_state.gestionnaire_postes = GestionnairePostes(st.session_state.erp_db)
        else:
            st.error("❌ Base de données ERP non disponible")
            return
    
    # Afficher l'en-tête DG
    show_dg_header()
    
    # Navigation principale
    show_main_navigation()
    
    # Gestion des messages de succès
    if st.session_state.get('bt_show_success'):
        st.success("✅ Bon de Travail sauvegardé avec succès!")
        st.session_state.bt_show_success = False
    
    # Affichage selon le mode principal
    main_mode = st.session_state.get('main_mode', 'bt')
    
    if main_mode == 'bt':
        # Mode Bons de Travail
        show_bt_navigation()
        
        bt_mode = st.session_state.get('bt_mode', 'create')
        
        if bt_mode in ['create', 'edit', 'view']:
            # Mode formulaire
            if bt_mode == 'view':
                st.info("👁️ Mode visualisation - Formulaire en lecture seule")
            
            with st.container():
                show_bt_form_section()
                show_tasks_section()
                show_materials_section() 
                show_instructions_section()
                
                if bt_mode != 'view':
                    show_bt_actions()
        
        elif bt_mode == 'manage':
            # Mode gestion BT
            show_bt_management()
        
        elif bt_mode == 'stats':
            # Mode statistiques BT
            show_bt_statistics()
    
    elif main_mode == 'postes':
        # Mode Postes de Travail
        show_work_centers_navigation()
        
        wc_action = st.session_state.get('wc_action', 'list')
        
        if wc_action == 'list':
            show_work_centers_list()
        
        elif wc_action == 'create':
            show_work_center_form()
        
        elif wc_action == 'edit':
            if st.session_state.wc_selected_id:
                try:
                    poste_data = st.session_state.erp_db.get_work_center_by_id(st.session_state.wc_selected_id)
                    if poste_data:
                        show_work_center_form(poste_data)
                    else:
                        st.error("❌ Poste non trouvé")
                        st.session_state.wc_action = 'list'
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
                    st.session_state.wc_action = 'list'
            else:
                st.session_state.wc_action = 'list'
                st.rerun()
        
        elif wc_action == 'view':
            if st.session_state.wc_selected_id:
                show_work_center_details(st.session_state.wc_selected_id)
            else:
                st.session_state.wc_action = 'list'
                st.rerun()
        
        elif wc_action == 'stats':
            show_work_centers_statistics()
        
        elif wc_action == 'analysis':
            show_work_centers_analysis()
    
    # Footer DG
    st.markdown("---")
    st.markdown(f"""
    <div style='text-align:center;color:var(--text-color-light);padding:20px 0;'>
        <p><strong>🏭 Desmarais & Gagné Inc.</strong> - Système de Gestion Production</p>
        <p>📞 (450) 372-9630 | 📧 info@dg-inc.com | 🌐 Interface intégrée ERP Production</p>
        <p><em>Mode actuel: {'📋 Bons de Travail' if main_mode == 'bt' else '🏭 Postes de Travail'}</em></p>
    </div>
    """, unsafe_allow_html=True)

# Point d'entrée principal
if __name__ == "__main__":
    show_production_management_page()
