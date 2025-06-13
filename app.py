# --- START OF FILE app.py - VERSION SQLITE UNIFIÉE CORRIGÉE COMPLÈTE ---

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

# NOUVELLE ARCHITECTURE : Import SQLite Database
from erp_database import ERPDatabase, convertir_pieds_pouces_fractions_en_valeur_decimale, convertir_imperial_vers_metrique

# Importations pour le CRM (avec toutes les fonctions décommentées) - CORRIGÉ
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

# Importations pour les Employés - CORRIGÉ COMPLET
from employees import (
    GestionnaireEmployes,
    render_employes_liste_tab,
    render_employes_dashboard_tab,
    render_employe_form,
    render_employe_details,
    show_employees_page as real_show_employees_page,
    DEPARTEMENTS,
    STATUTS_EMPLOYE,
    COMPETENCES_DISPONIBLES
)

# Importation du module postes de travail
from postes_travail import (
    GestionnairePostes,
    integrer_postes_dans_projets,
    generer_rapport_capacite_production,
    show_work_centers_page,
    show_manufacturing_routes_page,
    show_capacity_analysis_page,
    update_sidebar_with_work_centers
)

# INTÉGRATION TIMETRACKER : Importation des modules TimeTracker
try:
    from timetracker import show_timetracker_interface
    from database_sync import DatabaseSync, show_sync_interface
    TIMETRACKER_AVAILABLE = True
except ImportError as e:
    TIMETRACKER_AVAILABLE = False
    # Note: Le warning sera affiché dans l'interface si nécessaire

# Configuration de la page
st.set_page_config(
    page_title="🚀 ERP Production DG Inc.",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Fonctions Utilitaires de Mesure (préservées) ---
UNITES_MESURE = ["IMPÉRIAL", "MÉTRIQUE"]
TYPES_PRODUITS_INVENTAIRE = ["BOIS", "MÉTAL", "QUINCAILLERIE", "OUTILLAGE", "MATÉRIAUX", "ACCESSOIRES", "AUTRE"]
STATUTS_STOCK_INVENTAIRE = ["DISPONIBLE", "FAIBLE", "CRITIQUE", "EN COMMANDE", "ÉPUISÉ", "INDÉTERMINÉ"]

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

def mettre_a_jour_statut_stock(produit_dict_stat):
    if not isinstance(produit_dict_stat, dict):
        return
    try:
        qty_act_dec_stat = convertir_pieds_pouces_fractions_en_valeur_decimale(produit_dict_stat.get('quantite_imperial', "0' 0\""))
        lim_min_dec_stat = convertir_pieds_pouces_fractions_en_valeur_decimale(produit_dict_stat.get('limite_minimale_imperial', "0' 0\""))
        qty_res_dec_stat = convertir_pieds_pouces_fractions_en_valeur_decimale(produit_dict_stat.get('quantite_reservee_imperial', "0' 0\""))
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

# --- CSS et Interface ---
def load_css_file(css_file_path):
    try:
        with open(css_file_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
        return True
    except FileNotFoundError:
        st.warning(f"Fichier CSS '{css_file_path}' non trouvé. Utilisation du CSS par défaut.")
        return False
    except Exception as e:
        st.error(f"Erreur CSS : {e}")
        return False

def apply_global_styles():
    """Version allégée - tout le CSS est externalisé dans style.css"""
    load_css_file('style.css')

# ----- NOUVELLE FONCTION : Initialisation Données de Base (CORRECTION CRITIQUE) -----
def _init_base_data_if_empty():
    """Initialise les données de base si les tables sont vides - RÉSOUT ERREURS FK"""
    db = st.session_state.erp_db
    
    try:
        # Vérifier et créer entreprises par défaut
        companies_count = db.get_table_count('companies')
        if companies_count == 0:
            # Créer quelques entreprises par défaut
            default_companies = [
                {
                    'id': 1,
                    'nom': 'AutoTech Corp.',
                    'secteur': 'Automobile',
                    'adresse': '123 Rue Industrielle, Montréal, QC',
                    'site_web': 'www.autotech.com',
                    'notes': 'Client métallurgie automobile'
                },
                {
                    'id': 2,
                    'nom': 'BâtiTech Inc.',
                    'secteur': 'Construction',
                    'adresse': '456 Boul. Construction, Québec, QC',
                    'site_web': 'www.batitech.ca',
                    'notes': 'Structures industrielles'
                },
                {
                    'id': 3,
                    'nom': 'AeroSpace Ltd',
                    'secteur': 'Aéronautique',
                    'adresse': '789 Ave. Aviation, Mirabel, QC',
                    'site_web': 'www.aerospace.com',
                    'notes': 'Pièces aéronautiques'
                }
            ]
            
            for company in default_companies:
                db.execute_insert('''
                    INSERT OR IGNORE INTO companies (id, nom, secteur, adresse, site_web, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    company['id'], company['nom'], company['secteur'],
                    company['adresse'], company['site_web'], company['notes']
                ))
            
            print(f"✅ {len(default_companies)} entreprises par défaut créées")
        
        # Vérifier et créer contacts par défaut
        contacts_count = db.get_table_count('contacts')
        if contacts_count == 0:
            default_contacts = [
                {
                    'id': 1,
                    'prenom': 'Jean',
                    'nom_famille': 'Dubois',
                    'email': 'j.dubois@autotech.com',
                    'telephone': '514-555-0101',
                    'company_id': 1,
                    'role_poste': 'Directeur Technique'
                },
                {
                    'id': 2,
                    'prenom': 'Marie',
                    'nom_famille': 'Tremblay',
                    'email': 'm.tremblay@batitech.ca',
                    'telephone': '418-555-0202',
                    'company_id': 2,
                    'role_poste': 'Ingénieure Projet'
                },
                {
                    'id': 3,
                    'prenom': 'David',
                    'nom_famille': 'Johnson',
                    'email': 'd.johnson@aerospace.com',
                    'telephone': '450-555-0303',
                    'company_id': 3,
                    'role_poste': 'Responsable Achats'
                }
            ]
            
            for contact in default_contacts:
                db.execute_insert('''
                    INSERT OR IGNORE INTO contacts (id, prenom, nom_famille, email, telephone, company_id, role_poste)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    contact['id'], contact['prenom'], contact['nom_famille'],
                    contact['email'], contact['telephone'], contact['company_id'], contact['role_poste']
                ))
            
            print(f"✅ {len(default_contacts)} contacts par défaut créés")
        
        # Initialiser postes de travail si vides
        work_centers_count = db.get_table_count('work_centers')
        if work_centers_count == 0:
            # Créer quelques postes essentiels
            default_work_centers = [
                {
                    'id': 1,
                    'nom': 'Robot ABB GMAW Station 1',
                    'departement': 'PRODUCTION',
                    'categorie': 'ROBOTIQUE',
                    'type_machine': 'Robot de soudage',
                    'capacite_theorique': 8.0,
                    'operateurs_requis': 1,
                    'cout_horaire': 140.0,
                    'competences_requises': 'Soudage GMAW, Programmation Robot'
                },
                {
                    'id': 2,
                    'nom': 'Découpe Plasma CNC',
                    'departement': 'USINAGE',
                    'categorie': 'CNC',
                    'type_machine': 'Table plasma',
                    'capacite_theorique': 7.5,
                    'operateurs_requis': 1,
                    'cout_horaire': 125.0,
                    'competences_requises': 'Découpe plasma, Programmation CNC'
                },
                {
                    'id': 3,
                    'nom': 'Assemblage Manuel Station A',
                    'departement': 'PRODUCTION',
                    'categorie': 'MANUEL',
                    'type_machine': 'Poste assemblage',
                    'capacite_theorique': 8.0,
                    'operateurs_requis': 2,
                    'cout_horaire': 65.0,
                    'competences_requises': 'Assemblage mécanique, Lecture plans'
                }
            ]
            
            for wc in default_work_centers:
                db.execute_insert('''
                    INSERT OR IGNORE INTO work_centers 
                    (id, nom, departement, categorie, type_machine, capacite_theorique, 
                     operateurs_requis, cout_horaire, competences_requises)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    wc['id'], wc['nom'], wc['departement'], wc['categorie'],
                    wc['type_machine'], wc['capacite_theorique'], wc['operateurs_requis'],
                    wc['cout_horaire'], wc['competences_requises']
                ))
            
            print(f"✅ {len(default_work_centers)} postes de travail créés")
            
    except Exception as e:
        print(f"Erreur initialisation données de base: {e}")

# ----- NOUVELLE CLASSE : Gestionnaire de Projets SQLite CORRIGÉE -----
class GestionnaireProjetSQL:
    """
    NOUVELLE ARCHITECTURE : Gestionnaire de projets utilisant SQLite au lieu de JSON
    Remplace GestionnaireProjetIA pour une architecture unifiée - VERSION CORRIGÉE
    """
    
    def __init__(self, db: ERPDatabase):
        self.db = db
        self.next_id = 10000  # Commence à 10000 pour professionnalisme
        self._init_next_id()
    
    def _init_next_id(self):
        """Initialise le prochain ID basé sur les projets existants"""
        try:
            result = self.db.execute_query("SELECT MAX(id) as max_id FROM projects")
            if result and result[0]['max_id']:
                self.next_id = max(result[0]['max_id'] + 1, 10000)
            else:
                self.next_id = 10000
        except Exception as e:
            st.error(f"Erreur initialisation next_id: {e}")
            self.next_id = 10000
    
    @property
    def projets(self):
        """Propriété pour maintenir compatibilité avec l'ancien code"""
        return self.get_all_projects()
    
    def get_all_projects(self):
        """Récupère tous les projets depuis SQLite"""
        try:
            query = '''
                SELECT p.*, c.nom as client_nom_company
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                ORDER BY p.id DESC
            '''
            rows = self.db.execute_query(query)
            
            projets = []
            for row in rows:
                projet = dict(row)
                
                # Récupérer opérations
                operations = self.db.execute_query(
                    "SELECT * FROM operations WHERE project_id = ? ORDER BY sequence_number",
                    (projet['id'],)
                )
                projet['operations'] = [dict(op) for op in operations]
                
                # Récupérer matériaux
                materiaux = self.db.execute_query(
                    "SELECT * FROM materials WHERE project_id = ?",
                    (projet['id'],)
                )
                projet['materiaux'] = [dict(mat) for mat in materiaux]
                
                # Récupérer employés assignés
                employes_assignes = self.db.execute_query(
                    "SELECT employee_id FROM project_assignments WHERE project_id = ?",
                    (projet['id'],)
                )
                projet['employes_assignes'] = [row['employee_id'] for row in employes_assignes]
                
                # Compatibilité avec ancien format
                if not projet.get('client_nom_cache') and projet.get('client_nom_company'):
                    projet['client_nom_cache'] = projet['client_nom_company']
                
                projets.append(projet)
            
            return projets
            
        except Exception as e:
            st.error(f"Erreur récupération projets: {e}")
            return []
    
    def ajouter_projet(self, projet_data):
        """Ajoute un nouveau projet en SQLite - VERSION CORRIGÉE avec validation FK"""
        try:
            project_id = self.next_id
            
            # VALIDATION PRÉALABLE des clés étrangères
            if projet_data.get('client_company_id'):
                company_exists = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM companies WHERE id = ?",
                    (projet_data['client_company_id'],)
                )
                if not company_exists or company_exists[0]['count'] == 0:
                    raise ValueError(f"Entreprise ID {projet_data['client_company_id']} n'existe pas")
            
            # Validation employés assignés
            employes_assignes = projet_data.get('employes_assignes', [])
            for emp_id in employes_assignes:
                emp_exists = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM employees WHERE id = ?",
                    (emp_id,)
                )
                if not emp_exists or emp_exists[0]['count'] == 0:
                    raise ValueError(f"Employé ID {emp_id} n'existe pas")
            
            # Insérer projet principal avec gestion NULL
            query = '''
                INSERT INTO projects 
                (id, nom_projet, client_company_id, client_nom_cache, client_legacy,
                 statut, priorite, tache, date_soumis, date_prevu, bd_ft_estime, 
                 prix_estime, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            prix_estime = float(str(projet_data.get('prix_estime', 0)).replace('$', '').replace(',', '')) if projet_data.get('prix_estime') else 0
            bd_ft_estime = float(projet_data.get('bd_ft_estime', 0)) if projet_data.get('bd_ft_estime') else 0
            
            self.db.execute_update(query, (
                project_id,
                projet_data['nom_projet'],
                projet_data.get('client_company_id'),  # Peut être NULL
                projet_data.get('client_nom_cache'),
                projet_data.get('client_legacy', ''),  # Legacy field
                projet_data.get('statut', 'À FAIRE'),
                projet_data.get('priorite', 'MOYEN'),
                projet_data.get('tache'),
                projet_data.get('date_soumis'),
                projet_data.get('date_prevu'),
                bd_ft_estime,
                prix_estime,
                projet_data.get('description')
            ))
            
            # Insérer assignations employés (validation déjà faite)
            for emp_id in employes_assignes:
                self.db.execute_update(
                    "INSERT OR IGNORE INTO project_assignments (project_id, employee_id, role_projet) VALUES (?, ?, ?)",
                    (project_id, emp_id, 'Membre équipe')
                )
            
            self.next_id += 1
            return project_id
            
        except ValueError as ve:
            st.error(f"Erreur validation: {ve}")
            return None
        except Exception as e:
            st.error(f"Erreur technique ajout projet: {e}")
            return None
    
    def modifier_projet(self, projet_id, projet_data_update):
        """Modifie un projet existant"""
        try:
            # Préparer les champs à mettre à jour
            update_fields = []
            params = []
            
            for field, value in projet_data_update.items():
                if field in ['nom_projet', 'client_company_id', 'client_nom_cache', 'client_legacy',
                           'statut', 'priorite', 'tache', 'date_soumis', 'date_prevu', 
                           'bd_ft_estime', 'prix_estime', 'description']:
                    update_fields.append(f"{field} = ?")
                    
                    # Traitement spécial pour les prix
                    if field == 'prix_estime':
                        value = float(str(value).replace('$', '').replace(',', '')) if value else 0
                    elif field == 'bd_ft_estime':
                        value = float(value) if value else 0
                    
                    params.append(value)
            
            if update_fields:
                query = f"UPDATE projects SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
                params.append(projet_id)
                self.db.execute_update(query, tuple(params))
            
            # Mettre à jour assignations employés si fourni
            if 'employes_assignes' in projet_data_update:
                # Supprimer anciennes assignations
                self.db.execute_update("DELETE FROM project_assignments WHERE project_id = ?", (projet_id,))
                
                # Ajouter nouvelles assignations
                for emp_id in projet_data_update['employes_assignes']:
                    self.db.execute_update(
                        "INSERT INTO project_assignments (project_id, employee_id, role_projet) VALUES (?, ?, ?)",
                        (projet_id, emp_id, 'Membre équipe')
                    )
            
            return True
            
        except Exception as e:
            st.error(f"Erreur modification projet: {e}")
            return False
    
    def supprimer_projet(self, projet_id):
        """Supprime un projet et ses données associées"""
        try:
            # Supprimer en cascade (relations d'abord)
            self.db.execute_update("DELETE FROM project_assignments WHERE project_id = ?", (projet_id,))
            self.db.execute_update("DELETE FROM operations WHERE project_id = ?", (projet_id,))
            self.db.execute_update("DELETE FROM materials WHERE project_id = ?", (projet_id,))
            self.db.execute_update("DELETE FROM time_entries WHERE project_id = ?", (projet_id,))
            
            # Supprimer le projet
            self.db.execute_update("DELETE FROM projects WHERE id = ?", (projet_id,))
            
            return True
            
        except Exception as e:
            st.error(f"Erreur suppression projet: {e}")
            return False
    
    def get_demo_data(self):
        """Retourne des données de démonstration (pour compatibilité)"""
        return []  # Les données de démo sont maintenant en SQLite
    
    def charger_projets(self):
        """Méthode de compatibilité"""
        pass  # Plus besoin de charger depuis JSON
    
    def sauvegarder_projets(self):
        """Méthode de compatibilité"""
        pass  # Auto-sauvegardé en SQLite

# ----- NOUVELLE CLASSE : Gestionnaire Inventaire SQLite -----
class GestionnaireInventaireSQL:
    """Gestionnaire inventaire utilisant SQLite au lieu de JSON"""
    
    def __init__(self, db: ERPDatabase):
        self.db = db
    
    def get_all_inventory(self):
        """Récupère tout l'inventaire depuis SQLite"""
        try:
            rows = self.db.execute_query("SELECT * FROM inventory_items ORDER BY id")
            return {str(row['id']): dict(row) for row in rows}
        except Exception as e:
            st.error(f"Erreur récupération inventaire: {e}")
            return {}
    
    def add_inventory_item(self, item_data):
        """Ajoute un article d'inventaire"""
        try:
            query = '''
                INSERT INTO inventory_items 
                (nom, type_produit, quantite_imperial, quantite_metric,
                 limite_minimale_imperial, limite_minimale_metric,
                 quantite_reservee_imperial, quantite_reservee_metric,
                 statut, description, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            # Conversions métriques
            quantite_metric = convertir_imperial_vers_metrique(item_data.get('quantite_imperial', '0\' 0"'))
            limite_metric = convertir_imperial_vers_metrique(item_data.get('limite_minimale_imperial', '0\' 0"'))
            reservee_metric = convertir_imperial_vers_metrique(item_data.get('quantite_reservee_imperial', '0\' 0"'))
            
            item_id = self.db.execute_insert(query, (
                item_data['nom'],
                item_data.get('type_produit'),
                item_data.get('quantite_imperial'),
                quantite_metric,
                item_data.get('limite_minimale_imperial'),
                limite_metric,
                item_data.get('quantite_reservee_imperial', '0\' 0"'),
                reservee_metric,
                item_data.get('statut'),
                item_data.get('description'),
                item_data.get('notes')
            ))
            
            # Ajouter entrée historique
            self.db.execute_update(
                "INSERT INTO inventory_history (inventory_item_id, action, quantite_apres, notes) VALUES (?, ?, ?, ?)",
                (item_id, 'CRÉATION', item_data.get('quantite_imperial'), 'Création initiale')
            )
            
            return item_id
            
        except Exception as e:
            st.error(f"Erreur ajout inventaire: {e}")
            return None

# --- Fonctions Utilitaires (Projets) - INCHANGÉES -----
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

# ----- FONCTIONS D'AFFICHAGE MODIFIÉES POUR SQLITE -----

TEXT_COLOR_CHARTS = 'var(--text-color)'

def show_dashboard():
    st.markdown("## 📊 Tableau de Bord ERP Production")
    gestionnaire = st.session_state.gestionnaire
    gestionnaire_employes = st.session_state.gestionnaire_employes
    gestionnaire_postes = st.session_state.gestionnaire_postes
    
    # Affichage notification migration
    if st.session_state.get('migration_completed'):
        st.success("🎉 Migration SQLite complétée ! ERP Production DG Inc. utilise maintenant une architecture unifiée.")
    
    stats = get_project_statistics(gestionnaire)
    emp_stats = gestionnaire_employes.get_statistiques_employes()
    postes_stats = gestionnaire_postes.get_statistiques_postes()
    
    if stats['total'] == 0 and emp_stats.get('total', 0) == 0:
        st.markdown("<div class='info-card' style='text-align:center;padding:3rem;'><h3>🏭 Bienvenue dans l'ERP Production DG Inc. SQLite !</h3><p>Architecture unifiée avec base de données relationnelle. Créez votre premier projet ou explorez les données migrées.</p></div>", unsafe_allow_html=True)
        return

    # Métriques Projets
    if stats['total'] > 0:
        st.markdown("### 🚀 Aperçu Projets (SQLite)")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("📊 Total Projets", stats['total'])
        with c2:
            st.metric("🚀 Projets Actifs", stats['projets_actifs'])
        with c3:
            st.metric("✅ Taux Completion", f"{stats['taux_completion']:.1f}%")
        with c4:
            st.metric("💰 CA Total", format_currency(stats['ca_total']))

    # Métriques postes de travail
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

    # INTÉGRATION TIMETRACKER : Métriques temps et revenus
    if TIMETRACKER_AVAILABLE:
        try:
            # Initialiser le gestionnaire de sync s'il n'existe pas
            if 'database_sync' not in st.session_state:
                st.session_state.database_sync = DatabaseSync()
            
            timetracker_stats = st.session_state.database_sync.get_sync_statistics()
            if timetracker_stats['employees'] > 0 or timetracker_stats['time_entries'] > 0:
                st.markdown("### ⏱️ Aperçu TimeTracker DG")
                tt_c1, tt_c2, tt_c3, tt_c4 = st.columns(4)
                with tt_c1:
                    st.metric("👥 Employés Sync", timetracker_stats['employees'])
                with tt_c2:
                    st.metric("⏱️ Entrées Temps", timetracker_stats['time_entries'])
                with tt_c3:
                    st.metric("🔧 Tâches Actives", timetracker_stats['tasks'])
                with tt_c4:
                    revenue_display = f"{timetracker_stats['total_revenue']:,.0f}$ CAD" if timetracker_stats['total_revenue'] > 0 else "0$ CAD"
                    st.metric("💰 Revenus Temps", revenue_display)
        except Exception as e:
            st.warning(f"TimeTracker stats non disponibles: {str(e)}")
    
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

    # Graphiques combinés (inchangés)
    if stats['total'] > 0 or postes_stats['total_postes'] > 0:
        gc1, gc2 = st.columns(2)
        
        with gc1:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            if stats['par_statut']:
                colors_statut = {'À FAIRE': '#f59e0b', 'EN COURS': '#3b82f6', 'EN ATTENTE': '#ef4444', 'TERMINÉ': '#10b981', 'ANNULÉ': '#6b7280', 'LIVRAISON': '#8b5cf6'}
                fig = px.pie(values=list(stats['par_statut'].values()), names=list(stats['par_statut'].keys()), title="📈 Projets par Statut (SQLite)", color_discrete_map=colors_statut)
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

        # Projets récents depuis SQLite
        st.markdown("---")
        st.markdown("### 🕒 Projets Récents (SQLite)")
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
                if client_display_name == 'N/A' and p.get('client_company_id'):
                    crm_manager = st.session_state.gestionnaire_crm
                    entreprise = crm_manager.get_entreprise_by_id(p.get('client_company_id'))
                    if entreprise:
                        client_display_name = entreprise.get('nom', 'N/A')
                elif client_display_name == 'N/A':
                    client_display_name = p.get('client_legacy', 'N/A')

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

def show_liste_projets():
    st.markdown("## 📋 Liste des Projets (SQLite)")
    gestionnaire = st.session_state.gestionnaire
    crm_manager = st.session_state.gestionnaire_crm

    col_create, _ = st.columns([1, 3])
    with col_create:
        if st.button("➕ Nouveau Projet", use_container_width=True, key="create_btn_liste"):
            st.session_state.show_create_project = True
    st.markdown("---")
    
    if not gestionnaire.projets and not st.session_state.get('show_create_project'):
        st.info("Aucun projet en base SQLite. Cliquez sur 'Nouveau Projet' pour commencer.")

    if gestionnaire.projets:
        # Interface de filtrage identique
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

        # Logique de filtrage identique
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
                               (p.get('client_company_id') and crm_manager.get_entreprise_by_id(p.get('client_company_id')) and terme in crm_manager.get_entreprise_by_id(p.get('client_company_id')).get('nom', '').lower()) or
                               terme in str(p.get('client_legacy', '')).lower()
                              ]

        st.markdown(f"**{len(projets_filtres)} projet(s) trouvé(s) en SQLite**")
        if projets_filtres:
            # Tableau des projets (logique identique)
            df_data = []
            for p in projets_filtres:
                client_display_name_df = p.get('client_nom_cache', 'N/A')
                if client_display_name_df == 'N/A' and p.get('client_company_id'):
                    entreprise = crm_manager.get_entreprise_by_id(p.get('client_company_id'))
                    if entreprise:
                        client_display_name_df = entreprise.get('nom', 'N/A')
                elif client_display_name_df == 'N/A':
                    client_display_name_df = p.get('client_legacy', 'N/A')

                df_data.append({'🆔': p.get('id', '?'), '📋 Projet': p.get('nom_projet', 'N/A'), '👤 Client': client_display_name_df, '🚦 Statut': p.get('statut', 'N/A'), '⭐ Priorité': p.get('priorite', 'N/A'), '📅 Début': p.get('date_soumis', 'N/A'), '🏁 Fin': p.get('date_prevu', 'N/A'), '💰 Prix': format_currency(p.get('prix_estime', 0))})
            st.dataframe(pd.DataFrame(df_data), use_container_width=True)
            
            # Actions sur projets (interface identique)
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

    # Affichage des formulaires (inchangés)
    if st.session_state.get('show_create_project'):
        render_create_project_form(gestionnaire, crm_manager)
    if st.session_state.get('show_edit_project') and st.session_state.get('edit_project_data'):
        render_edit_project_form(gestionnaire, crm_manager, st.session_state.edit_project_data)
    if st.session_state.get('show_delete_confirmation'):
        render_delete_confirmation(gestionnaire)

def render_create_project_form(gestionnaire, crm_manager):
    """FORMULAIRE CRÉATION PROJET - VERSION CORRIGÉE avec validation FK"""
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### ➕ Créer Projet DG Inc. (SQLite)")
    
    # VALIDATION PRÉALABLE des données de base
    companies_count = st.session_state.erp_db.get_table_count('companies')
    if companies_count == 0:
        st.warning("⚠️ Aucune entreprise en base. Initialisation...")
        _init_base_data_if_empty()
        st.rerun()
    
    with st.form("create_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        with fc1:
            nom = st.text_input("Nom *:")
            
            # CORRECTION CRITIQUE : Récupérer entreprises depuis SQLite
            try:
                entreprises_db = st.session_state.erp_db.execute_query("SELECT id, nom FROM companies ORDER BY nom")
                liste_entreprises_crm_form = [("", "Sélectionner ou laisser vide")] + [(e['id'], e['nom']) for e in entreprises_db]
            except Exception as e:
                st.error(f"Erreur récupération entreprises: {e}")
                liste_entreprises_crm_form = [("", "Aucune entreprise disponible")]
            
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
        
        # Assignation d'employés avec validation
        employes_assignes = []
        if gestionnaire_employes.employes:
            st.markdown("##### 👥 Assignation d'Employés")
            employes_disponibles = [(emp['id'], f"{emp.get('prenom', '')} {emp.get('nom', '')} ({emp.get('poste', '')})") for emp in gestionnaire_employes.employes if emp.get('statut') == 'ACTIF']
            if employes_disponibles:
                employes_assignes = st.multiselect(
                    "Employés assignés:",
                    options=[emp_id for emp_id, _ in employes_disponibles],
                    format_func=lambda emp_id: next((nom for id_e, nom in employes_disponibles if id_e == emp_id), ""),
                    key="project_create_employes_assign"
                )
        
        st.markdown("<small>* Obligatoire</small>", unsafe_allow_html=True)
        s_btn, c_btn = st.columns(2)
        with s_btn:
            submit = st.form_submit_button("💾 Créer en SQLite", use_container_width=True)
        with c_btn:
            cancel = st.form_submit_button("❌ Annuler", use_container_width=True)
        
        if submit:
            # VALIDATION RENFORCÉE
            if not nom:
                st.error("Nom du projet obligatoire.")
            elif not selected_entreprise_id_form and not client_nom_direct_form:
                st.error("Client (entreprise ou nom direct) obligatoire.")
            elif d_fin < d_debut:
                st.error("Date fin < date début.")
            else:
                # VALIDATION CLÉS ÉTRANGÈRES
                client_company_id = None
                client_nom_cache_val = ""
                
                if selected_entreprise_id_form:
                    # Vérifier que l'entreprise existe
                    company_check = st.session_state.erp_db.execute_query(
                        "SELECT nom FROM companies WHERE id = ?", 
                        (selected_entreprise_id_form,)
                    )
                    if company_check:
                        client_company_id = selected_entreprise_id_form
                        client_nom_cache_val = company_check[0]['nom']
                    else:
                        st.error(f"Entreprise ID {selected_entreprise_id_form} non trouvée en base.")
                        return
                elif client_nom_direct_form:
                    client_nom_cache_val = client_nom_direct_form

                # Validation employés assignés
                employes_valides = []
                if employes_assignes:
                    for emp_id in employes_assignes:
                        emp_check = st.session_state.erp_db.execute_query(
                            "SELECT id FROM employees WHERE id = ?", 
                            (emp_id,)
                        )
                        if emp_check:
                            employes_valides.append(emp_id)
                        else:
                            st.warning(f"Employé ID {emp_id} non trouvé - ignoré")

                # DONNÉES PROJET VALIDÉES
                data = {
                    'nom_projet': nom,
                    'client_company_id': client_company_id,  # NULL si client direct
                    'client_nom_cache': client_nom_cache_val,
                    'client_legacy': client_nom_direct_form if not selected_entreprise_id_form else "",
                    'statut': statut,
                    'priorite': priorite,
                    'tache': tache,
                    'date_soumis': d_debut.strftime('%Y-%m-%d'),
                    'date_prevu': d_fin.strftime('%Y-%m-%d'),
                    'bd_ft_estime': float(bd_ft),
                    'prix_estime': float(prix),
                    'description': desc or f"Projet {tache.lower()} pour {client_nom_cache_val}",
                    'employes_assignes': employes_valides
                }
                
                try:
                    pid = gestionnaire.ajouter_projet(data)
                    
                    if pid:
                        # Mettre à jour les assignations des employés
                        if employes_valides:
                            for emp_id in employes_valides:
                                employe = gestionnaire_employes.get_employe_by_id(emp_id)
                                if employe:
                                    projets_existants = employe.get('projets_assignes', [])
                                    if pid not in projets_existants:
                                        projets_existants.append(pid)
                                        gestionnaire_employes.modifier_employe(emp_id, {'projets_assignes': projets_existants})
                        
                        st.success(f"✅ Projet #{pid} créé en SQLite avec {len(employes_valides)} employé(s) assigné(s) !")
                        st.session_state.show_create_project = False
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la création en SQLite")
                        
                except Exception as e:
                    st.error(f"❌ Erreur création projet: {str(e)}")
                    st.info("💡 Vérifiez que les données de base sont initialisées (entreprises, employés)")
        
        if cancel:
            st.session_state.show_create_project = False
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

def render_edit_project_form(gestionnaire, crm_manager, project_data):
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(f"### ✏️ Modifier Projet #{project_data.get('id')} (SQLite)")
    
    with st.form("edit_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        
        with fc1:
            nom = st.text_input("Nom *:", value=project_data.get('nom_projet', ''))
            
            # Gestion de la liste des entreprises CRM
            liste_entreprises_crm_form = [("", "Sélectionner ou laisser vide")] + [(e['id'], e['nom']) for e in crm_manager.entreprises]
            current_entreprise_id = project_data.get('client_company_id', "")
            selected_entreprise_id_form = st.selectbox(
                "Client (Entreprise) *:",
                options=[e_id for e_id, _ in liste_entreprises_crm_form],
                index=next((i for i, (e_id, _) in enumerate(liste_entreprises_crm_form) if e_id == current_entreprise_id), 0),
                format_func=lambda e_id: next((nom for id_e, nom in liste_entreprises_crm_form if id_e == e_id), "Sélectionner..."),
                key="project_edit_client_select"
            )
            client_nom_direct_form = st.text_input("Ou nom client direct:", value=project_data.get('client_legacy', ''))

            # Gestion du statut
            statuts = ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON"]
            current_statut = project_data.get('statut', 'À FAIRE')
            statut = st.selectbox("Statut:", statuts, index=statuts.index(current_statut) if current_statut in statuts else 0)
            
            # Gestion de la priorité
            priorites = ["BAS", "MOYEN", "ÉLEVÉ"]
            current_priorite = project_data.get('priorite', 'MOYEN')
            priorite = st.selectbox("Priorité:", priorites, index=priorites.index(current_priorite) if current_priorite in priorites else 1)
        
        with fc2:
            # Gestion du type de tâche
            taches = ["ESTIMATION", "CONCEPTION", "DÉVELOPPEMENT", "TESTS", "DÉPLOIEMENT", "MAINTENANCE", "FORMATION"]
            current_tache = project_data.get('tache', 'ESTIMATION')
            tache = st.selectbox("Type:", taches, index=taches.index(current_tache) if current_tache in taches else 0)
            
            # Gestion des dates
            try:
                d_debut = st.date_input("Début:", datetime.strptime(project_data.get('date_soumis', ''), '%Y-%m-%d').date())
            except (ValueError, TypeError):
                d_debut = st.date_input("Début:", datetime.now().date())
            
            try:
                d_fin = st.date_input("Fin Prévue:", datetime.strptime(project_data.get('date_prevu', ''), '%Y-%m-%d').date())
            except (ValueError, TypeError):
                d_fin = st.date_input("Fin Prévue:", datetime.now().date() + timedelta(days=30))
            
            # Gestion BD-FT
            try:
                bd_ft_val = int(project_data.get('bd_ft_estime', 0))
            except (ValueError, TypeError):
                bd_ft_val = 0
            bd_ft = st.number_input("BD-FT (h):", 0, value=bd_ft_val, step=1)
            
            # Gestion du prix
            try:
                prix_str = str(project_data.get('prix_estime', '0'))
                # Nettoyer la chaîne de tous les caractères non numériques sauf le point décimal
                prix_str = prix_str.replace(' ', '').replace(',', '').replace('€', '').replace('$', '')
                prix_val = float(prix_str) if prix_str else 0.0
            except (ValueError, TypeError):
                prix_val = 0.0
            
            prix = st.number_input("Prix ($):", 0.0, value=prix_val, step=100.0, format="%.2f")
        
        # Description
        desc = st.text_area("Description:", value=project_data.get('description', ''))
        
        # Assignation d'employés
        if gestionnaire_employes.employes:
            st.markdown("##### 👥 Assignation d'Employés")
            employes_disponibles = [
                (emp['id'], f"{emp.get('prenom', '')} {emp.get('nom', '')} ({emp.get('poste', '')})")
                for emp in gestionnaire_employes.employes 
                if emp.get('statut') == 'ACTIF'
            ]
            current_employes = project_data.get('employes_assignes', [])
            employes_assignes = st.multiselect(
                "Employés assignés:",
                options=[emp_id for emp_id, _ in employes_disponibles],
                default=[emp_id for emp_id in current_employes if emp_id in [e[0] for e in employes_disponibles]],
                format_func=lambda emp_id: next((nom for id_e, nom in employes_disponibles if id_e == emp_id), ""),
                key="project_edit_employes_assign"
            )
        
        st.markdown("<small>* Obligatoire</small>", unsafe_allow_html=True)
        
        # Boutons d'action
        s_btn, c_btn = st.columns(2)
        with s_btn:
            submit = st.form_submit_button("💾 Sauvegarder SQLite", use_container_width=True)
        with c_btn:
            cancel = st.form_submit_button("❌ Annuler", use_container_width=True)
        
        # Traitement de la soumission
        if submit:
            if not nom or (not selected_entreprise_id_form and not client_nom_direct_form):
                st.error("Nom du projet et Client obligatoires.")
            elif d_fin < d_debut:
                st.error("Date fin < date début.")
            else:
                # Détermination du nom du client pour cache
                client_nom_cache_val = ""
                if selected_entreprise_id_form:
                    entreprise_obj = crm_manager.get_entreprise_by_id(selected_entreprise_id_form)
                    if entreprise_obj:
                        client_nom_cache_val = entreprise_obj.get('nom', '')
                elif client_nom_direct_form:
                    client_nom_cache_val = client_nom_direct_form

                # Préparation des données de mise à jour
                update_data = {
                    'nom_projet': nom,
                    'client_company_id': selected_entreprise_id_form if selected_entreprise_id_form else None,
                    'client_nom_cache': client_nom_cache_val,
                    'client_legacy': client_nom_direct_form if not selected_entreprise_id_form and client_nom_direct_form else "",
                    'statut': statut,
                    'priorite': priorite,
                    'tache': tache,
                    'date_soumis': d_debut.strftime('%Y-%m-%d'),
                    'date_prevu': d_fin.strftime('%Y-%m-%d'),
                    'bd_ft_estime': str(bd_ft),
                    'prix_estime': str(prix),
                    'description': desc,
                    'employes_assignes': employes_assignes if 'employes_assignes' in locals() else []
                }
                
                # Mise à jour du projet
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
                    
                    st.success(f"✅ Projet #{project_data['id']} modifié en SQLite !")
                    st.session_state.show_edit_project = False
                    st.session_state.edit_project_data = None
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la modification SQLite.")
        
        # Traitement de l'annulation
        if cancel:
            st.session_state.show_edit_project = False
            st.session_state.edit_project_data = None
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

def render_delete_confirmation(gestionnaire):
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### 🗑️ Confirmation de Suppression (SQLite)")
    project_id = st.session_state.delete_project_id
    project = next((p for p in gestionnaire.projets if p.get('id') == project_id), None)
    
    if project:
        st.warning(f"⚠️ Êtes-vous sûr de vouloir supprimer le projet **#{project.get('id')} - {project.get('nom_projet', 'N/A')}** de la base SQLite ?")
        st.markdown("Cette action est **irréversible** et supprimera toutes les données associées (opérations, matériaux, assignations).")
        
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            if st.button("🗑️ Confirmer Suppression SQLite", use_container_width=True):
                if gestionnaire.supprimer_projet(project_id):
                    st.success(f"✅ Projet #{project_id} supprimé de SQLite !")
                    st.session_state.show_delete_confirmation = False
                    st.session_state.delete_project_id = None
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la suppression SQLite")
        with dcol2:
            if st.button("❌ Annuler", use_container_width=True):
                st.session_state.show_delete_confirmation = False
                st.session_state.delete_project_id = None
                st.rerun()
    else:
        st.error("Projet non trouvé en SQLite.")
        st.session_state.show_delete_confirmation = False
        st.session_state.delete_project_id = None
    st.markdown("</div>", unsafe_allow_html=True)

def show_itineraire():
    """Version améliorée avec vrais postes de travail"""
    st.markdown("## 🛠️ Itinéraire Fabrication - DG Inc. (SQLite)")
    gestionnaire = st.session_state.gestionnaire
    gestionnaire_postes = st.session_state.gestionnaire_postes
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    if not gestionnaire.projets:
        st.warning("Aucun projet en SQLite.")
        return
    
    opts = [(p.get('id'), f"#{p.get('id')} - {p.get('nom_projet', 'N/A')}") for p in gestionnaire.projets]
    sel_id = st.selectbox("Projet:", options=[pid for pid, _ in opts], format_func=lambda pid: next((name for id, name in opts if id == pid), ""), key="iti_sel")
    proj = next((p for p in gestionnaire.projets if p.get('id') == sel_id), None)
    
    if not proj:
        st.error("Projet non trouvé en SQLite.")
        return
    
    st.markdown(f"<div class='project-header'><h2>{proj.get('nom_projet', 'N/A')}</h2></div>", unsafe_allow_html=True)

def show_nomenclature():
    st.markdown("## 📊 Nomenclature (BOM) - SQLite")
    gestionnaire = st.session_state.gestionnaire
    if not gestionnaire.projets:
        st.warning("Aucun projet en SQLite.")
        return

def show_gantt():
    st.markdown("## 📈 Diagramme de Gantt - SQLite")
    gestionnaire = st.session_state.gestionnaire
    crm_manager = st.session_state.gestionnaire_crm
    if not gestionnaire.projets:
        st.info("Aucun projet SQLite pour Gantt.")
        return

def show_calendrier():
    st.markdown("## 📅 Vue Calendrier - SQLite")

def show_kanban():
    st.markdown("## 🔄 Vue Kanban - SQLite")

def show_project_modal():
    """Affichage des détails d'un projet dans un expander"""
    if 'selected_project' not in st.session_state or not st.session_state.get('show_project_modal') or not st.session_state.selected_project:
        return
    
    proj_mod = st.session_state.selected_project
    
    with st.expander(f"📁 Détails Projet #{proj_mod.get('id')} - {proj_mod.get('nom_projet', 'N/A')} (SQLite)", expanded=True):
        if st.button("✖️ Fermer", key="close_modal_details_btn_top"):
            st.session_state.show_project_modal = False
            st.rerun()

def show_inventory_management_page():
    st.markdown("## 📦 Gestion de l'Inventaire (SQLite)")

    # Adaptation pour utiliser SQLite
    if 'inventory_manager_sql' not in st.session_state:
        st.session_state.inventory_manager_sql = GestionnaireInventaireSQL(st.session_state.erp_db)
    
    inventory_manager = st.session_state.inventory_manager_sql
    inventory_data = inventory_manager.get_all_inventory()

    action_mode = st.session_state.get('inv_action_mode', "Voir Liste")

    if action_mode == "Ajouter Article":
        st.subheader("➕ Ajouter un Nouvel Article (SQLite)")
        with st.form("add_inventory_item_form", clear_on_submit=True):
            st.info("Les données seront sauvegardées directement en SQLite")
            nom = st.text_input("Nom de l'article *:")
            type_art = st.selectbox("Type *:", TYPES_PRODUITS_INVENTAIRE)
            quantite_imp = st.text_input("Quantité Stock (Impérial) *:", "0' 0\"")
            limite_min_imp = st.text_input("Limite Minimale (Impérial):", "0' 0\"")
            description = st.text_area("Description:")
            notes = st.text_area("Notes Internes:")

            submitted_add = st.form_submit_button("💾 Ajouter Article SQLite")
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
                            "nom": nom,
                            "type_produit": type_art,
                            "quantite_imperial": quantite_std,
                            "limite_minimale_imperial": limite_std,
                            "quantite_reservee_imperial": "0' 0\"",
                            "statut": "DISPONIBLE",
                            "description": description,
                            "notes": notes
                        }
                        
                        item_id = inventory_manager.add_inventory_item(new_item)
                        if item_id:
                            st.success(f"Article '{nom}' (ID: {item_id}) ajouté avec succès en SQLite!")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la sauvegarde en SQLite.")

    elif action_mode == "Voir Liste" or not inventory_data:
        st.subheader("📋 Liste des Articles en Inventaire (SQLite)")
        if not inventory_data:
            st.info("L'inventaire SQLite est vide. Cliquez sur 'Ajouter Article' pour commencer.")
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
                    "Type": data.get("type_produit", "N/A"),
                    "Stock (Imp.)": data.get("quantite_imperial", "N/A"),
                    "Stock (Métr.)": f"{data.get('quantite_metric', 0):.3f} m",
                    "Limite Min.": data.get("limite_minimale_imperial", "N/A"),
                    "Réservé": data.get("quantite_reservee_imperial", "N/A"),
                    "Statut": data.get("statut", "N/A")
                })

            if items_display_list:
                df_inventory = pd.DataFrame(items_display_list)
                st.dataframe(df_inventory, use_container_width=True)
                st.info(f"📊 {len(items_display_list)} articles en base SQLite")
            else:
                st.info("Aucun article ne correspond à votre recherche." if search_term_inv else "L'inventaire SQLite est vide.")

def show_crm_page():
    """Page CRM complète avec onglets et fonctionnalités - CORRIGÉE"""
    st.markdown("## 🤝 Gestion de la Relation Client (CRM) - SQLite")
    
    # Récupérer les gestionnaires
    crm_manager = st.session_state.gestionnaire_crm
    projet_manager = st.session_state.gestionnaire
    
    # Initialiser le CRM avec la base SQLite si pas déjà fait
    if not crm_manager.use_sqlite:
        crm_manager.db = st.session_state.erp_db
        crm_manager.use_sqlite = True
        crm_manager._init_demo_data_if_empty()
    
    # Vérifier données en base
    total_companies = st.session_state.erp_db.get_table_count('companies')
    total_contacts = st.session_state.erp_db.get_table_count('contacts')
    st.info(f"🗄️ Base SQLite CRM : {total_companies} entreprises • {total_contacts} contacts")
    
    # Interface avec onglets
    tab1, tab2, tab3 = st.tabs(["👤 Contacts", "🏢 Entreprises", "💬 Interactions"])
    
    with tab1:
        render_crm_contacts_tab(crm_manager, projet_manager)
    
    with tab2:
        render_crm_entreprises_tab(crm_manager, projet_manager)
    
    with tab3:
        render_crm_interactions_tab(crm_manager)
    
    # Gestion des actions CRM (formulaires, détails, etc.)
    action = st.session_state.get('crm_action')
    selected_id = st.session_state.get('crm_selected_id')
    
    if action == "create_contact":
        render_crm_contact_form(crm_manager)
    
    elif action == "edit_contact" and selected_id:
        contact_data = crm_manager.get_contact_by_id(selected_id)
        render_crm_contact_form(crm_manager, contact_data)
    
    elif action == "view_contact_details" and selected_id:
        contact_data = crm_manager.get_contact_by_id(selected_id)
        render_crm_contact_details(crm_manager, projet_manager, contact_data)
    
    elif action == "create_entreprise":
        render_crm_entreprise_form(crm_manager)
    
    elif action == "edit_entreprise" and selected_id:
        entreprise_data = crm_manager.get_entreprise_by_id(selected_id)
        render_crm_entreprise_form(crm_manager, entreprise_data)
    
    elif action == "view_entreprise_details" and selected_id:
        entreprise_data = crm_manager.get_entreprise_by_id(selected_id)
        render_crm_entreprise_details(crm_manager, projet_manager, entreprise_data)
    
    elif action == "create_interaction":
        render_crm_interaction_form(crm_manager)
    
    elif action == "edit_interaction" and selected_id:
        interaction_data = crm_manager.get_interaction_by_id(selected_id)
        render_crm_interaction_form(crm_manager, interaction_data)
    
    elif action == "view_interaction_details" and selected_id:
        interaction_data = crm_manager.get_interaction_by_id(selected_id)
        render_crm_interaction_details(crm_manager, projet_manager, interaction_data)

def show_employees_page():
    """Redirection vers la vraie page employés - CORRIGÉE"""
    # Vérifier que le gestionnaire utilise SQLite
    if hasattr(st.session_state, 'gestionnaire_employes'):
        emp_manager = st.session_state.gestionnaire_employes
        if hasattr(emp_manager, 'db') and emp_manager.db is None:
            # Connecter à SQLite si pas déjà fait
            emp_manager.db = st.session_state.erp_db
            emp_manager._load_employes_from_db()
    
    # Appeler la vraie fonction depuis employees.py
    real_show_employees_page()

# ----- Fonction Principale MODIFIÉE POUR SQLITE CORRIGÉE -----
def main():
    # NOUVELLE ARCHITECTURE : Initialisation ERPDatabase avec correction FK
    if 'erp_db' not in st.session_state:
        st.session_state.erp_db = ERPDatabase("erp_production_dg.db")
        st.session_state.migration_completed = True
        
        # AJOUT CRITIQUE : Initialiser données de base si vides - RÉSOUT ERREURS FK
        _init_base_data_if_empty()
    
    # NOUVELLE ARCHITECTURE : Gestionnaire projets SQLite
    if 'gestionnaire' not in st.session_state:
        st.session_state.gestionnaire = GestionnaireProjetSQL(st.session_state.erp_db)
    
    # Gestionnaire CRM - CORRECTION SQLite  
    if 'gestionnaire_crm' not in st.session_state:
        st.session_state.gestionnaire_crm = GestionnaireCRM(st.session_state.erp_db)
    
    # Gestionnaire employés - CORRECTION SQLite
    if 'gestionnaire_employes' not in st.session_state:
        st.session_state.gestionnaire_employes = GestionnaireEmployes(st.session_state.erp_db)
        
        # Vérifier si les employés sont initialisés
        emp_count = st.session_state.erp_db.get_table_count('employees')
        if emp_count == 0:
            st.info("🏭 Initialisation des 21 employés DG Inc...")
    
    # Gestionnaire des postes de travail
    if 'gestionnaire_postes' not in st.session_state:
        st.session_state.gestionnaire_postes = GestionnairePostes()
        # Intégrer les postes dans les projets existants au premier lancement
        if not hasattr(st.session_state, 'postes_integres'):
            st.session_state.gestionnaire = integrer_postes_dans_projets(
                st.session_state.gestionnaire, 
                st.session_state.gestionnaire_postes
            )
            st.session_state.postes_integres = True

    # INTÉGRATION TIMETRACKER : Gestionnaire de synchronisation
    if TIMETRACKER_AVAILABLE and 'database_sync' not in st.session_state:
        try:
            st.session_state.database_sync = DatabaseSync()
            # Vérifier si une synchronisation initiale est nécessaire
            if not hasattr(st.session_state, 'timetracker_init_sync_done'):
                stats = st.session_state.database_sync.get_sync_statistics()
                if stats['projects'] == 0 and len(st.session_state.gestionnaire.projets) > 0:
                    # Synchronisation silencieuse au premier lancement
                    try:
                        st.session_state.database_sync.full_sync(
                            st.session_state.gestionnaire,
                            st.session_state.gestionnaire_employes,
                            st.session_state.gestionnaire_postes
                        )
                    except Exception:
                        pass  # Silencieux si erreur
                st.session_state.timetracker_init_sync_done = True
        except Exception:
            pass  # Silencieux si erreur d'initialisation TimeTracker

    # DEBUG - Forcer initialisation si nécessaire
    if st.session_state.erp_db.get_table_count('companies') == 0:
        st.session_state.gestionnaire_crm._create_demo_data_sqlite()
        
    if st.session_state.erp_db.get_table_count('employees') == 0:
        st.session_state.gestionnaire_employes._initialiser_donnees_employes_dg_inc()

    # Initialisation des variables de session (inchangées)
    session_defs = {
        'show_project_modal': False, 'selected_project': None,
        'show_create_project': False, 'show_edit_project': False,
        'edit_project_data': None, 'show_delete_confirmation': False,
        'delete_project_id': None, 'selected_date': datetime.now().date(),
        'welcome_seen': False,
        'inv_action_mode': "Voir Liste",
        'crm_action': None, 'crm_selected_id': None, 'crm_confirm_delete_contact_id': None,
        'crm_confirm_delete_entreprise_id': None, 'crm_confirm_delete_interaction_id': None,
        'emp_action': None, 'emp_selected_id': None, 'emp_confirm_delete_id': None,
        'competences_form': [],
        'gamme_generated': None, 'gamme_metadata': None,
        # INTÉGRATION TIMETRACKER : Variables de session
        'timetracker_employee_id': None, 'timetracker_project_id': None,
        'timetracker_task_id': None, 'timetracker_is_clocked_in': False,
        'timetracker_current_entry_id': None, 'timetracker_view_mode': 'employee',
        'timetracker_show_sync': False, 'timetracker_selected_employee': None
    }
    for k, v_def in session_defs.items():
        if k not in st.session_state:
            st.session_state[k] = v_def

    apply_global_styles()

    st.markdown('<div class="main-title"><h1>🏭 ERP Production DG Inc. - SQLite Unifié</h1></div>', unsafe_allow_html=True)

    if not st.session_state.welcome_seen:
        welcome_msg = "🎉 Architecture SQLite unifiée ! ERP Production DG Inc. utilise maintenant une base relationnelle. 61 postes de travail intégrés."
        if TIMETRACKER_AVAILABLE:
            welcome_msg += " ⏱️ TimeTracker synchronisé avec SQLite !"
        st.success(welcome_msg)
        st.session_state.welcome_seen = True

    st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>🧭 Navigation SQLite</h3>", unsafe_allow_html=True)

    # MENU INTÉGRÉ avec TimeTracker (inchangé)
    pages = {
        "🏠 Tableau de Bord": "dashboard",
        "📋 Liste des Projets": "liste",
        "🤝 CRM": "crm_page",
        "👥 Employés": "employees_page",
        "🏭 Postes de Travail": "work_centers_page",
        "⚙️ Gammes Fabrication": "manufacturing_routes",
        "📊 Capacité Production": "capacity_analysis",
        "⏱️ TimeTracker": "timetracker_page",
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
        st.sidebar.markdown("<h4 style='color:var(--primary-color-darker);'>Actions Inventaire SQLite</h4>", unsafe_allow_html=True)
        st.session_state.inv_action_mode = st.sidebar.radio(
            "Mode:",
            ["Voir Liste", "Ajouter Article", "Modifier Article"],
            key="inv_action_mode_selector",
            index=["Voir Liste", "Ajouter Article", "Modifier Article"].index(st.session_state.inv_action_mode)
        )

    st.sidebar.markdown("---")

    # Statistiques SQLite dans la sidebar
    try:
        total_projects_sql = st.session_state.erp_db.get_table_count('projects')
        total_companies = st.session_state.erp_db.get_table_count('companies')
        total_employees = st.session_state.erp_db.get_table_count('employees')
        total_work_centers = st.session_state.erp_db.get_table_count('work_centers')
        
        st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>📊 Base SQLite</h3>", unsafe_allow_html=True)
        st.sidebar.metric("Base: Projets", total_projects_sql)
        st.sidebar.metric("Base: Entreprises", total_companies)
        st.sidebar.metric("Base: Employés", total_employees)
        st.sidebar.metric("Base: Postes", total_work_centers)
        
        # Informations sur la base
        schema_info = st.session_state.erp_db.get_schema_info()
        if schema_info['file_size_mb'] > 0:
            st.sidebar.metric("Base: Taille", f"{schema_info['file_size_mb']} MB")
            st.sidebar.metric("Base: Total", f"{schema_info['total_records']}")
        
    except Exception as e:
        st.sidebar.error(f"Erreur stats SQLite: {e}")

    # Statistiques des postes de travail dans la sidebar
    update_sidebar_with_work_centers()

    # INTÉGRATION TIMETRACKER : Statistiques dans la sidebar (inchangé)
    if TIMETRACKER_AVAILABLE:
        try:
            if 'database_sync' not in st.session_state:
                st.session_state.database_sync = DatabaseSync()
            
            tt_stats = st.session_state.database_sync.get_sync_statistics()
            if tt_stats['employees'] > 0 or tt_stats['projects'] > 0:
                st.sidebar.markdown("---")
                st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>⏱️ Aperçu TimeTracker</h3>", unsafe_allow_html=True)
                st.sidebar.metric("TimeTracker: Employés", tt_stats['employees'])
                st.sidebar.metric("TimeTracker: Projets Sync", tt_stats['projects'])
                if tt_stats['time_entries'] > 0:
                    st.sidebar.metric("TimeTracker: Pointages", tt_stats['time_entries'])
                if tt_stats['total_revenue'] > 0:
                    st.sidebar.metric("TimeTracker: Revenus", f"{tt_stats['total_revenue']:,.0f}$")
                
                # Afficher le statut de la dernière synchronisation
                if tt_stats['last_sync']:
                    last_sync_date = tt_stats['last_sync'][:10]  # Juste la date
                    st.sidebar.info(f"🔄 Dernière sync: {last_sync_date}")
        except Exception:
            pass  # Silencieux si TimeTracker pas encore configuré

    st.sidebar.markdown("---")
    st.sidebar.markdown("<div style='background:var(--primary-color-lighter);padding:10px;border-radius:8px;text-align:center;'><p style='color:var(--primary-color-darkest);font-size:12px;margin:0;'>🏭 ERP Production DG Inc.<br/>🗄️ Architecture SQLite Unifiée</p></div>", unsafe_allow_html=True)

    # PAGES (inchangées)
    if page_to_show_val == "dashboard":
        show_dashboard()
    elif page_to_show_val == "liste":
        show_liste_projets()
    elif page_to_show_val == "crm_page":
        show_crm_page()
    elif page_to_show_val == "employees_page":
        show_employees_page()
    elif page_to_show_val == "work_centers_page":
        show_work_centers_page()
    elif page_to_show_val == "manufacturing_routes":
        show_manufacturing_routes_page()
    elif page_to_show_val == "capacity_analysis":
        show_capacity_analysis_page()
    elif page_to_show_val == "timetracker_page":
        if TIMETRACKER_AVAILABLE:
            show_timetracker_interface()
        else:
            st.error("❌ TimeTracker non disponible. Veuillez créer les fichiers timetracker.py et database_sync.py")
            st.info("📋 Consultez le plan d'intégration pour créer les modules manquants.")
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
    footer_text = "🏭 ERP Production DG Inc. - Architecture SQLite Unifiée • 61 Postes • CRM • Inventaire"
    if TIMETRACKER_AVAILABLE:
        footer_text += " • ⏱️ TimeTracker"
    
    st.markdown(f"<div style='text-align:center;color:var(--text-color-muted);padding:20px 0;font-size:0.9em;'><p>{footer_text}</p><p>🗄️ Migration JSON → SQLite complétée • Architecture Relationnelle</p></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main()
        show_footer()
    except Exception as e_main:
        st.error(f"Une erreur majeure est survenue dans l'application SQLite: {str(e_main)}")
        st.info("Veuillez essayer de rafraîchir la page ou de redémarrer l'application.")
        import traceback
        st.code(traceback.format_exc())

# --- END OF FILE app.py - VERSION SQLITE UNIFIÉE CORRIGÉE COMPLÈTE ---
