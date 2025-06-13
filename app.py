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

# ----- FONCTIONS D'AFFICHAGE MODIFIÉES -----

TEXT_COLOR_CHARTS = 'var(--text-color)'

def show_dashboard():
    st.markdown("## 📊 Tableau de Bord ERP Production")
    gestionnaire = st.session_state.gestionnaire
    gestionnaire_employes = st.session_state.gestionnaire_employes
    gestionnaire_postes = st.session_state.gestionnaire_postes
    
    stats = get_project_statistics(gestionnaire)
    emp_stats = gestionnaire_employes.get_statistiques_employes()
    postes_stats = gestionnaire_postes.get_statistiques_postes()
    
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
    gestionnaire_postes = st.session_state.gestionnaire_postes
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

    # Bouton de régénération de gamme
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
        
        # Tableau enrichi avec postes de travail
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
            
            # Gestion de la liste des entreprises CRM
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
            submit = st.form_submit_button("💾 Sauvegarder", use_container_width=True)
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
                    'client_entreprise_id': selected_entreprise_id_form if selected_entreprise_id_form else None,
                    'client_nom_cache': client_nom_cache_val,
                    'client': client_nom_direct_form if not selected_entreprise_id_form and client_nom_direct_form else "",
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
                    
                    st.success(f"✅ Projet #{project_data['id']} modifié !")
                    st.session_state.show_edit_project = False
                    st.session_state.edit_project_data = None
                    st.rerun()
                else:
                    st.error("Erreur lors de la modification.")
        
        # Traitement de l'annulation
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

# ----- Fonction Principale MODIFIÉE POUR TIMETRACKER -----
def main():
    # Initialisation des gestionnaires
    if 'gestionnaire' not in st.session_state:
        st.session_state.gestionnaire = GestionnaireProjetIA()
    if 'gestionnaire_crm' not in st.session_state:
        st.session_state.gestionnaire_crm = GestionnaireCRM()
    if 'gestionnaire_employes' not in st.session_state:
        st.session_state.gestionnaire_employes = GestionnaireEmployes()
    
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

    # Migration des IDs de projet au premier lancement
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
        'gamme_generated': None, 'gamme_metadata': None,  # NOUVEAU pour les gammes
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

    st.markdown('<div class="main-title"><h1>🏭 ERP Production DG Inc.</h1></div>', unsafe_allow_html=True)

    if not st.session_state.welcome_seen:
        welcome_msg = "🎉 Bienvenue dans l'ERP Production DG Inc. ! Explorez les 61 postes de travail et les gammes de fabrication."
        if TIMETRACKER_AVAILABLE:
            welcome_msg += " ⏱️ TimeTracker intégré pour le suivi temps réel !"
        st.success(welcome_msg)
        st.session_state.welcome_seen = True

    st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>🧭 Navigation</h3>", unsafe_allow_html=True)

    # MENU INTÉGRÉ avec TimeTracker
    pages = {
        "🏠 Tableau de Bord": "dashboard",
        "📋 Liste des Projets": "liste",
        "🤝 CRM": "crm_page",
        "👥 Employés": "employees_page",
        "🏭 Postes de Travail": "work_centers_page",        # NOUVEAU
        "⚙️ Gammes Fabrication": "manufacturing_routes",    # NOUVEAU
        "📊 Capacité Production": "capacity_analysis",      # NOUVEAU
        "⏱️ TimeTracker": "timetracker_page",              # INTÉGRATION TIMETRACKER
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

    # Statistiques des postes de travail dans la sidebar
    update_sidebar_with_work_centers()

    # INTÉGRATION TIMETRACKER : Statistiques dans la sidebar
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

    # NOUVELLES PAGES dans le switch avec TimeTracker
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
    elif page_to_show_val == "timetracker_page":           # INTÉGRATION TIMETRACKER
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
    footer_text = "🏭 ERP Production DG Inc. - 61 Postes de Travail • CRM • Inventaire"
    if TIMETRACKER_AVAILABLE:
        footer_text += " • ⏱️ TimeTracker"
    
    st.markdown(f"<div style='text-align:center;color:var(--text-color-muted);padding:20px 0;font-size:0.9em;'><p>{footer_text}</p><p>Transformé en véritable industrie 4.0</p></div>", unsafe_allow_html=True)

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
