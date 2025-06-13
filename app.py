# app.py - TimeTracker Pro Desmarais & Gagné - VERSION COMPLÈTE AVEC 34 POSTES RÉELS
# Système de pointage avec gestion granulaire des tâches, interfaces CRUD complètes et assignations
# Intégration des vrais postes de travail D&G avec taux 85-140$ CAD

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import io
import base64
import json
import os
from datetime import datetime, date, timedelta
from PIL import Image
import time

# Configuration de la page
st.set_page_config(
    page_title="TimeTracker Pro - Desmarais & Gagné",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================
# CSS PERSONNALISÉ COMPLET
# ================================

def load_css():
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* --- Variables CSS identiques au programme d'estimation --- */
    :root {
        --primary-color: #00A971; 
        --primary-color-darker: #00673D;
        --primary-color-darkest: #004C2E;
        --background-color: #F9FAFB;
        --secondary-background-color: #FFFFFF;
        --text-color: #374151;
        --text-color-light: #6B7280;
        --border-color: #E5E7EB;
        --border-color-light: #F3F4F6;
        --border-radius-sm: 0.375rem;
        --border-radius-md: 0.5rem;
        --font-family: 'Inter', sans-serif;
        --box-shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
        --box-shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        --animation-speed: 0.3s;
        --success-color: #22c55e;
        --warning-color: #f59e0b;
        --error-color: #ef4444;
        --task-color: #8b5cf6;
        --edit-color: #3b82f6;
        --delete-color: #ef4444;
        --assignment-color: #06b6d4;
        --premium-color: #e74c3c;
        --high-value-color: #f39c12;
        
        /* Nouveaux gradients D&G */
        --primary-gradient: linear-gradient(135deg, #e6f7f1 0%, #ffffff 100%);
        --secondary-gradient: linear-gradient(135deg, #e8f5e9 0%, #ffffff 100%);
        --green-gradient: linear-gradient(90deg, #00A971 0%, #00673D 100%);
    }

    /* --- Reset et Styles Globaux identiques --- */
    body {
        font-family: var(--font-family) !important;
        color: var(--text-color);
        background-color: var(--background-color);
        line-height: 1.6;
        font-size: 16px;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: var(--font-family) !important;
        font-weight: 700 !important;
        color: var(--text-color);
        margin-bottom: 0.8em;
        line-height: 1.3;
    }

    /* --- Animations identiques au programme d'estimation --- */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes slideIn {
        from { transform: translateX(-20px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }

    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(0, 169, 113, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(0, 169, 113, 0); }
        100% { box-shadow: 0 0 0 0 rgba(0, 169, 113, 0); }
    }

    @keyframes pulse-lustrous {
        0% { 
            box-shadow: 
                0 4px 8px rgba(51, 105, 30, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.6),
                inset 0 -1px 0 rgba(0, 0, 0, 0.1),
                0 0 0 0 rgba(174, 213, 129, 0.4);
        }
        70% { 
            box-shadow: 
                0 4px 8px rgba(51, 105, 30, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.6),
                inset 0 -1px 0 rgba(0, 0, 0, 0.1),
                0 0 0 12px rgba(174, 213, 129, 0);
        }
        100% { 
            box-shadow: 
                0 4px 8px rgba(51, 105, 30, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.6),
                inset 0 -1px 0 rgba(0, 0, 0, 0.1),
                0 0 0 0 rgba(174, 213, 129, 0);
        }
    }

    @keyframes subtle-pulse {
        0% { 
            box-shadow: 
                0 4px 8px rgba(0, 169, 113, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.3),
                inset 0 -1px 0 rgba(0, 0, 0, 0.1),
                0 0 0 0 rgba(0, 169, 113, 0.3);
        }
        50% { 
            box-shadow: 
                0 4px 8px rgba(0, 169, 113, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.3),
                inset 0 -1px 0 rgba(0, 0, 0, 0.1),
                0 0 0 4px rgba(0, 169, 113, 0.1);
        }
        100% { 
            box-shadow: 
                0 4px 8px rgba(0, 169, 113, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.3),
                inset 0 -1px 0 rgba(0, 0, 0, 0.1),
                0 0 0 0 rgba(0, 169, 113, 0);
        }
    }

    /* ================================
       SIDEBAR BLANC IDENTIQUE À L'ESTIMATION
       ================================ */
    
    /* Sidebar principal - exactement comme l'estimation */
    .css-1d391kg,
    .css-1lcbmhc,
    .css-17eq0hr,
    .css-1cypcdb,
    .css-1lcbmhc .css-1cypcdb,
    .css-1d391kg .css-1cypcdb,
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div,
    .css-1outpf7,
    .css-1e5imcs,
    .css-1e5imcs .css-1cypcdb {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    
    section[data-testid="stSidebar"] {
        background-color: var(--secondary-background-color) !important;
        border-right: 1px solid var(--border-color) !important;
        padding: 1.5rem !important;
    }

    /* Titre de la sidebar */
    section[data-testid="stSidebar"] .stHeadingContainer h1 {
        font-size: 1.5rem;
        color: var(--primary-color);
        margin-bottom: 1.5rem;
    }

    /* Sous-titres dans la sidebar */
    section[data-testid="stSidebar"] h3 {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-color-light);
        margin-top: 2rem;
        margin-bottom: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: flex;
        align-items: center;
    }

    /* Container du sidebar */
    .css-1d391kg {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E5E7EB !important;
    }
    
    /* Texte du sidebar */
    .css-1d391kg,
    .css-1d391kg .stMarkdown,
    .css-1d391kg p,
    .css-1d391kg h1,
    .css-1d391kg h2,
    .css-1d391kg h3,
    .css-1d391kg h4,
    .css-1d391kg h5,
    .css-1d391kg span {
        color: var(--text-color) !important;
    }
    
    /* Titre du sidebar */
    .css-1d391kg h3 {
        color: var(--primary-color) !important;
        font-weight: 600 !important;
        border-bottom: 2px solid var(--primary-color) !important;
        padding-bottom: 8px !important;
        margin-bottom: 16px !important;
    }

    /* === BOUTONS LUSTRÉS IDENTIQUES À L'ESTIMATION === */
    
    /* Boutons principaux avec effet lustré exactement comme l'estimation */
    .stButton > button {
        background: linear-gradient(145deg, 
            rgba(255,255,255,0.4) 0%, 
            var(--primary-color) 20%, 
            var(--primary-color-darker) 80%, 
            rgba(0,0,0,0.2) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--border-radius-md) !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 600 !important;
        transition: all var(--animation-speed) ease !important;
        box-shadow: 
            0 4px 8px rgba(0, 169, 113, 0.25),
            inset 0 1px 0 rgba(255, 255, 255, 0.3),
            inset 0 -1px 0 rgba(0, 0, 0, 0.1) !important;
        width: 100% !important;
        text-align: center !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        position: relative !important;
        overflow: hidden !important;
        font-size: 16px !important;
        margin: 10px 0 !important;
    }

    /* Effet de brillance animé */
    .stButton > button::before {
        content: "";
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, 
            transparent 0%, 
            rgba(255, 255, 255, 0.4) 50%, 
            transparent 100%);
        transition: left 0.6s ease;
        z-index: 1;
    }

    .stButton > button:hover::before {
        left: 100%;
    }

    .stButton > button:hover {
        background: linear-gradient(145deg, 
            rgba(255,255,255,0.5) 0%, 
            #00C89A 20%, 
            var(--primary-color-darker) 80%, 
            rgba(0,0,0,0.3) 100%) !important;
        transform: translateY(-3px) !important;
        box-shadow: 
            0 8px 16px rgba(0, 169, 113, 0.35),
            inset 0 2px 0 rgba(255, 255, 255, 0.4),
            inset 0 -2px 0 rgba(0, 0, 0, 0.15),
            0 0 20px rgba(0, 169, 113, 0.2) !important;
    }

    .stButton > button:active {
        background: linear-gradient(145deg, 
            rgba(0,0,0,0.1) 0%, 
            var(--primary-color-darker) 20%, 
            var(--primary-color-darkest) 80%, 
            rgba(0,0,0,0.4) 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 
            0 2px 4px rgba(0, 169, 113, 0.3),
            inset 0 -1px 0 rgba(255, 255, 255, 0.2),
            inset 0 1px 2px rgba(0, 0, 0, 0.2) !important;
    }

    /* Boutons spécialisés TimeTracker */
    .stButton > button:has(span:contains("SORTIE")) {
        background: linear-gradient(145deg, 
            rgba(255,255,255,0.4) 0%, 
            var(--error-color) 20%, 
            #dc2626 80%, 
            rgba(0,0,0,0.2) 100%) !important;
    }

    .stButton > button:has(span:contains("PAUSE")) {
        background: linear-gradient(145deg, 
            rgba(255,255,255,0.4) 0%, 
            var(--warning-color) 20%, 
            #d97706 80%, 
            rgba(0,0,0,0.2) 100%) !important;
    }

    .stButton > button:has(span:contains("CHANGER")) {
        background: linear-gradient(145deg, 
            rgba(255,255,255,0.4) 0%, 
            var(--task-color) 20%, 
            #7c3aed 80%, 
            rgba(0,0,0,0.2) 100%) !important;
    }

    .stButton > button:has(span:contains("✏️")) {
        background: linear-gradient(145deg, 
            rgba(255,255,255,0.4) 0%, 
            var(--edit-color) 20%, 
            #2563eb 80%, 
            rgba(0,0,0,0.2) 100%) !important;
    }

    .stButton > button:has(span:contains("🗑️")) {
        background: linear-gradient(145deg, 
            rgba(255,255,255,0.4) 0%, 
            var(--delete-color) 20%, 
            #dc2626 80%, 
            rgba(0,0,0,0.2) 100%) !important;
    }

    .stButton > button:has(span:contains("👥")) {
        background: linear-gradient(145deg, 
            rgba(255,255,255,0.4) 0%, 
            var(--assignment-color) 20%, 
            #0891b2 80%, 
            rgba(0,0,0,0.2) 100%) !important;
    }

    /* Boutons sidebar - style différencié */
    .css-1d391kg .stButton > button {
        background: linear-gradient(145deg, 
            rgba(255,255,255,0.8) 0%, 
            #f8f9fa 50%, 
            #e9ecef 100%) !important;
        color: var(--text-color) !important;
        border: 1px solid var(--border-color) !important;
    }
    
    .css-1d391kg .stButton > button:hover {
        background: linear-gradient(145deg, 
            rgba(255,255,255,0.9) 0%, 
            #e6f3ff 50%, 
            #dbeafe 100%) !important;
        color: var(--primary-color) !important;
        border-color: var(--primary-color) !important;
    }

    /* === HEADER PRINCIPAL IDENTIQUE === */
    .main-header {
        background: var(--primary-gradient);
        padding: 20px;
        border-radius: var(--border-radius-md);
        color: var(--text-color);
        text-align: center;
        margin-bottom: 25px;
        box-shadow: var(--box-shadow-md);
        animation: fadeIn 0.6s ease-out;
    }

    .main-header h1 {
        margin: 0;
        font-size: 28px;
        font-weight: 600;
        color: var(--primary-color-darker);
    }

    .main-header p {
        margin-top: 10px;
        margin-bottom: 0;
        font-size: 16px;
        opacity: 0.9;
    }

    /* === STATUS CARDS TIMETRACKER === */
    .status-card {
        background: linear-gradient(to right, var(--secondary-background-color), #f7f9fc);
        padding: 20px;
        border-radius: var(--border-radius-md);
        margin-bottom: 15px;
        box-shadow: var(--box-shadow-sm);
        transition: all var(--animation-speed);
        border-left: 4px solid var(--primary-color);
        animation: slideIn 0.4s ease-out;
    }

    .status-card.punched-in {
        border-left-color: var(--success-color);
        background: linear-gradient(to right, #f0fdf4, #e6f7ec);
    }

    .status-card.break {
        border-left-color: var(--warning-color);
        background: linear-gradient(to right, #fffbeb, #fef3c7);
    }

    .status-card.task-active {
        border-left-color: var(--task-color);
        background: linear-gradient(to right, #f3f4f6, #e5e7eb);
    }

    .status-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--box-shadow-md);
    }

    /* === CARTES DE TÂCHES D&G === */
    .task-card-dg {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid var(--border-color);
        border-radius: var(--border-radius-md);
        padding: 15px;
        margin: 8px 0;
        transition: all var(--animation-speed);
        cursor: pointer;
    }

    .task-card-dg:hover {
        border-color: var(--primary-color);
        box-shadow: var(--box-shadow-md);
        transform: translateY(-1px);
    }

    .task-card-dg.premium {
        border-left: 4px solid var(--premium-color);
        background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%);
    }

    .task-card-dg.high-value {
        border-left: 4px solid var(--high-value-color);
        background: linear-gradient(135deg, #fffbeb 0%, #ffffff 100%);
    }

    /* === HORLOGE DIGITALE === */
    .digital-clock {
        background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
        color: #00ff41;
        font-family: 'Courier New', monospace;
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        padding: 20px;
        border-radius: var(--border-radius-md);
        margin-bottom: 20px;
        box-shadow: 
            0 8px 16px rgba(0, 0, 0, 0.3),
            inset 0 2px 4px rgba(255, 255, 255, 0.1);
        text-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
        border: 2px solid #4a5568;
    }

    /* === INDICATEURS ET BADGES === */
    .task-indicator {
        background: var(--task-color);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        margin: 5px 0;
    }

    .assignment-indicator {
        background: var(--assignment-color);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        margin: 5px 0;
    }

    .premium-indicator {
        background: var(--premium-color);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        margin: 5px 0;
    }

    .high-value-indicator {
        background: var(--high-value-color);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        margin: 5px 0;
    }

    /* === CARTES MÉTRIQUES === */
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        padding: 20px;
        border-radius: var(--border-radius-md);
        box-shadow: var(--box-shadow-sm);
        border-left: 4px solid var(--primary-color);
        margin: 10px 0;
        transition: all var(--animation-speed);
    }

    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--box-shadow-md);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--primary-color);
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: var(--text-color-light);
        margin: 5px 0 0 0;
    }

    /* === FORMULAIRES === */
    .edit-form {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border: 2px solid var(--edit-color);
        border-radius: var(--border-radius-md);
        padding: 20px;
        margin: 15px 0;
    }

    .delete-form {
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        border: 2px solid var(--delete-color);
        border-radius: var(--border-radius-md);
        padding: 20px;
        margin: 15px 0;
    }

    .assignment-card {
        background: linear-gradient(135deg, #e0f7ff 0%, #ffffff 100%);
        border: 2px solid var(--assignment-color);
        border-radius: var(--border-radius-md);
        padding: 15px;
        margin: 10px 0;
        box-shadow: var(--box-shadow-sm);
    }

    /* === FILTRES === */
    .filter-container {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border: 1px solid var(--border-color);
        border-radius: var(--border-radius-md);
        padding: 15px;
        margin: 15px 0;
    }

    /* === ALERTES D&G === */
    .alert-dg {
        padding: 15px;
        border-radius: var(--border-radius-md);
        margin: 10px 0;
        border-left: 4px solid;
    }

    .alert-dg.warning {
        background: #fffbeb;
        border-left-color: var(--warning-color);
        color: #92400e;
    }

    .alert-dg.success {
        background: #f0fdf4;
        border-left-color: var(--success-color);
        color: #065f46;
    }

    .alert-dg.error {
        background: #fef2f2;
        border-left-color: var(--error-color);
        color: #991b1b;
    }

    .alert-dg.info {
        background: #f0f9ff;
        border-left-color: var(--assignment-color);
        color: #0c4a6e;
    }

    /* === INPUTS ET SELECTBOX === */
    .stSelectbox > div {
        border-radius: var(--border-radius-md);
        border: 1px solid var(--border-color);
        background-color: var(--secondary-background-color);
        color: var(--text-color);
        box-shadow: var(--box-shadow-sm);
        transition: all var(--animation-speed);
    }

    .stSelectbox > div:hover {
        border-color: var(--primary-color);
        box-shadow: 0 2px 6px rgba(0, 169, 113, 0.15);
    }

    .stTextInput > div > div > input {
        border-radius: var(--border-radius-md) !important;
        border: 1px solid var(--border-color) !important;
        background-color: var(--secondary-background-color) !important;
        padding: 0.7rem 1rem !important;
        transition: all var(--animation-speed) !important;
        box-shadow: 
            0 1px 3px rgba(0, 0, 0, 0.05),
            inset 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 
            0 0 0 2px rgba(0, 169, 113, 0.2),
            inset 0 1px 3px rgba(0, 0, 0, 0.1),
            0 2px 4px rgba(0, 169, 113, 0.1) !important;
        transform: translateY(-1px) !important;
    }

    /* === TABLEAUX === */
    .styled-dataframe {
        background: white;
        border-radius: var(--border-radius-md);
        overflow: hidden;
        box-shadow: var(--box-shadow-md);
        margin: 20px 0;
    }

    /* === GRILLES D'ASSIGNATION === */
    .assignment-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 15px;
        margin: 20px 0;
    }

    .employee-card {
        background: white;
        border: 1px solid var(--border-color);
        border-radius: var(--border-radius-md);
        padding: 15px;
        box-shadow: var(--box-shadow-sm);
        transition: all var(--animation-speed);
    }

    .employee-card:hover {
        box-shadow: var(--box-shadow-md);
        transform: translateY(-2px);
    }

    /* === BADGES DE COMPÉTENCES === */
    .skill-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        margin-left: 5px;
    }

    .skill-debutant { background: #fef3c7; color: #92400e; }
    .skill-intermediaire { background: #dbeafe; color: #1e40af; }
    .skill-avance { background: #d1fae5; color: #065f46; }
    .skill-expert { background: #fce7f3; color: #be185d; }

    /* === STATUS BADGES === */
    .status-active {
        background: var(--success-color);
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }

    .status-inactive {
        background: var(--error-color);
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }

    .status-assigned {
        background: var(--assignment-color);
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }

    /* === INDICATEURS DE TAUX === */
    .rate-premium {
        color: var(--premium-color);
        font-weight: 700;
        font-size: 1.1em;
    }

    .rate-high {
        color: var(--high-value-color);
        font-weight: 600;
    }

    .rate-standard {
        color: var(--primary-color);
        font-weight: 500;
    }

    .rate-admin {
        color: var(--text-color-light);
    }

    /* === PULSE ANIMATION POUR TÂCHE ACTIVE === */
    .task-active-indicator {
        animation: pulse 2s infinite;
    }

    /* === RESPONSIVE MOBILE === */
    @media (max-width: 768px) {
        .digital-clock {
            font-size: 1.8rem;
            padding: 15px;
        }
        
        .stButton > button {
            padding: 12px 20px !important;
            font-size: 16px !important;
        }
        
        .main-header h1 {
            font-size: 24px;
        }
        
        .task-card-dg {
            padding: 10px;
        }

        .metric-card {
            padding: 15px;
        }

        .assignment-grid {
            grid-template-columns: 1fr;
        }

        body {
            padding: 10px;
        }
        
        .main-header {
            padding: 15px;
            margin-bottom: 15px;
        }
        
        .status-card {
            padding: 12px;
        }
        
        .stButton > button {
            min-height: 44px !important;
            font-size: 16px !important;
            padding: 0.8rem 1rem !important;
        }
    }

    /* === MASQUER BRANDING STREAMLIT === */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* === SCROLLBAR SIDEBAR === */
    .css-1d391kg::-webkit-scrollbar {
        width: 6px;
    }
    
    .css-1d391kg::-webkit-scrollbar-track {
        background: #F1F5F9;
    }
    
    .css-1d391kg::-webkit-scrollbar-thumb {
        background: #CBD5E1;
        border-radius: 3px;
    }
    
    .css-1d391kg::-webkit-scrollbar-thumb:hover {
        background: var(--primary-color);
    }

    /* === SÉPARATEURS SIDEBAR === */
    .css-1d391kg hr {
        border-color: #E5E7EB !important;
        margin: 16px 0 !important;
    }

    /* Hide Streamlit sidebar default styles */
    section[data-testid="stSidebar"] hr {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)

# ================================
# GESTIONNAIRE BASE DE DONNÉES ENRICHI AVEC POSTES D&G RÉELS
# ================================

class DatabaseManager:
    def __init__(self, db_path="timetracking.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données avec toutes les tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table des employés
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'employee',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table des projets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_code TEXT UNIQUE NOT NULL,
                project_name TEXT NOT NULL,
                client_name TEXT,
                requires_task_selection BOOLEAN DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table des tâches de projet
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                task_code TEXT NOT NULL,
                task_name TEXT NOT NULL,
                task_category TEXT,
                hourly_rate DECIMAL(10,2) DEFAULT 0,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id),
                UNIQUE(project_id, task_code)
            )
        """)
        
        # Table des assignations Projet-Tâches
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_task_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                is_enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (task_id) REFERENCES project_tasks (id),
                UNIQUE(project_id, task_id)
            )
        """)
        
        # Table des assignations Employé-Tâches
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_task_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                is_authorized BOOLEAN DEFAULT 1,
                skill_level TEXT DEFAULT 'intermédiaire',
                hourly_rate_override DECIMAL(10,2),
                assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees (id),
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (task_id) REFERENCES project_tasks (id),
                UNIQUE(employee_id, project_id, task_id)
            )
        """)
        
        # Table des entrées de temps
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                project_id INTEGER,
                task_id INTEGER,
                punch_in TIMESTAMP NOT NULL,
                punch_out TIMESTAMP,
                break_start TIMESTAMP,
                break_end TIMESTAMP,
                total_break_minutes INTEGER DEFAULT 0,
                location_lat REAL,
                location_lng REAL,
                notes TEXT,
                photo_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees (id),
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (task_id) REFERENCES project_tasks (id)
            )
        """)
        
        # Table des changements de tâches
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_entry_id INTEGER NOT NULL,
                previous_task_id INTEGER,
                new_task_id INTEGER NOT NULL,
                change_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (time_entry_id) REFERENCES time_entries (id),
                FOREIGN KEY (previous_task_id) REFERENCES project_tasks (id),
                FOREIGN KEY (new_task_id) REFERENCES project_tasks (id)
            )
        """)
        
        # Créer admin par défaut
        admin_password = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute("""
            INSERT OR IGNORE INTO employees (employee_code, name, password_hash, role) 
            VALUES ('ADMIN', 'Administrateur', ?, 'admin')
        """, (admin_password,))
        
        # Projets par défaut avec focus D&G
        default_projects = [
            ('DG-GENERAL', 'Opérations Générales D&G', 'Desmarais & Gagné Inc.', 1),
            ('MAINTENANCE', 'Maintenance', 'Interne', 0),
            ('FORMATION', 'Formation', 'Interne', 0)
        ]
        
        cursor.executemany("""
            INSERT OR IGNORE INTO projects (project_code, project_name, client_name, requires_task_selection) 
            VALUES (?, ?, ?, ?)
        """, default_projects)
        
        # Créer les 34 postes réels D&G
        self._create_dg_real_tasks(cursor)
        
        conn.commit()
        conn.close()
    
    def _create_dg_real_tasks(self, cursor):
        """Crée les 34 postes de travail réels Desmarais & Gagné"""
        
        # Récupérer l'ID du projet DG-GENERAL
        cursor.execute("SELECT id FROM projects WHERE project_code = 'DG-GENERAL'")
        dg_project = cursor.fetchone()
        
        if dg_project:
            project_id = dg_project[0]
            
            # LES 34 POSTES RÉELS DESMARAIS & GAGNÉ avec vrais taux 2025
            dg_tasks = [
                # PRÉPARATION ET PROGRAMMATION
                ('PROGR_POINCO', 'Programmation CNC', 'Préparation et Programmation', 95.00, 'Programmation des machines CNC et poinçonneuses'),
                ('DESSIN', 'Conception technique', 'Préparation et Programmation', 105.00, 'Conception et dessin technique des pièces'),
                ('TEMPS_BUREAU', 'Temps administratif', 'Préparation et Programmation', 85.00, 'Tâches administratives et bureau'),
                
                # DÉCOUPE ET PERÇAGE (taux élevés 120-135$)
                ('PLASMA', 'Découpe plasma', 'Découpe et Perçage', 135.00, 'Découpe plasma automatisée'),
                ('OXYCOUPAGE', 'Opération de coupe au feu', 'Découpe et Perçage', 135.00, 'Découpe à l\'oxygène et acétylène'),
                ('SCIE', 'Découpe avec scie', 'Découpe et Perçage', 95.00, 'Découpe mécanique avec scie'),
                ('POINCONNAGE', 'Poinçonnage', 'Découpe et Perçage', 135.00, 'Poinçonnage automatisé'),
                ('PUNCH_PRESS', 'Presse à poinçonner', 'Découpe et Perçage', 135.00, 'Opération presse à poinçonner'),
                ('DRILL_MAGNET', 'Perçage magnétique', 'Découpe et Perçage', 95.00, 'Perçage avec perceuse magnétique'),
                ('PRESS_DRILL', 'Perceuse à colonne', 'Découpe et Perçage', 95.00, 'Perçage avec perceuse à colonne'),
                ('FRAISAGE', 'Fraiser des trous', 'Découpe et Perçage', 120.00, 'Fraisage de précision'),
                
                # FORMAGE ET ASSEMBLAGE (taux 95-120$)
                ('PLIEUSE', 'Opération de pliage', 'Formage et Assemblage', 120.00, 'Pliage de tôles avec plieuse'),
                ('ROULAGE', 'Opération de rouleau', 'Formage et Assemblage', 120.00, 'Roulage et formage cylindrique'),
                ('CINTRUSE', 'Cintrage des pièces', 'Formage et Assemblage', 120.00, 'Cintrage de profilés et tubes'),
                ('ASSEMBLAGE', 'Préparation pour soudage', 'Formage et Assemblage', 95.00, 'Assemblage et préparation des pièces'),
                ('POINTAGE', 'Pointage des pièces', 'Formage et Assemblage', 95.00, 'Pointage de soudure et fixation'),
                
                # SOUDAGE (95$ standard, 140$ robot)
                ('SOUDURE_TIG', 'Soudage TIG', 'Soudage', 95.00, 'Soudage TIG manuel de précision'),
                ('SOUDURE_MIG', 'Soudure MIG', 'Soudage', 95.00, 'Soudage MIG semi-automatique'),
                ('SOUDURE_SPOT', 'Soudure par points', 'Soudage', 95.00, 'Soudage par résistance par points'),
                ('ROBOT', 'Robot soudeur', 'Soudage', 140.00, 'Soudage robotisé automatisé (taux premium)'),
                
                # FINITION (95$ standard)
                ('ÉBAVURAGE', 'Préparation et ébavurage', 'Finition', 95.00, 'Ébavurage et préparation des surfaces'),
                ('MEULAGE', 'Meuler les surfaces', 'Finition', 95.00, 'Meulage et finition des soudures'),
                ('POLISSAGE', 'Polir', 'Finition', 95.00, 'Polissage et finition miroir'),
                ('SABLAGE', 'Sabler', 'Finition', 95.00, 'Sablage et préparation de surface'),
                ('FILETAGE', 'Fileter des trous', 'Finition', 95.00, 'Filetage manuel et mécanique'),
                ('SERTISSAGE', 'Sertissage', 'Finition', 95.00, 'Sertissage d\'éléments et fixations'),
                
                # MANUTENTION ET CISAILLAGE (85-110$)
                ('SHEAR', 'Cisaillage', 'Manutention et Cisaillage', 110.00, 'Cisaillage de tôles'),
                ('MANUTENTION', 'Nettoyage et manutention', 'Manutention et Cisaillage', 95.00, 'Manutention générale et nettoyage'),
                ('RECEPTION', 'Réception matériel', 'Manutention et Cisaillage', 85.00, 'Réception et contrôle matières premières'),
                ('INVENTAIRE', 'Gestion d\'inventaire', 'Manutention et Cisaillage', 85.00, 'Gestion stocks et inventaires'),
                
                # CONTRÔLE QUALITÉ (85$ administratif)
                ('XINSP_PARTIE', 'Inspection partielle', 'Contrôle Qualité', 85.00, 'Inspection en cours de fabrication'),
                ('X_INSPEC_FIN', 'Inspection finale', 'Contrôle Qualité', 85.00, 'Contrôle qualité final'),
                ('X_FERMETURE', 'Fermeture d\'un item', 'Contrôle Qualité', 85.00, 'Finalisation et fermeture dossier'),
                
                # EXPÉDITION (85-95$)
                ('EMBALLAGE', 'Emballer', 'Expédition', 85.00, 'Emballage des produits finis'),
                ('EXPEDITION', 'Expédition', 'Expédition', 85.00, 'Préparation et expédition commandes'),
                ('TRANSPORT', 'Transport externe', 'Expédition', 95.00, 'Transport et livraison externe'),
            ]
            
            for task_code, task_name, category, rate, description in dg_tasks:
                cursor.execute("""
                    INSERT OR IGNORE INTO project_tasks 
                    (project_id, task_code, task_name, task_category, hourly_rate, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (project_id, task_code, task_name, category, rate, description))
            
            # Assigner toutes les tâches D&G au projet automatiquement
            cursor.execute("""
                INSERT OR IGNORE INTO project_task_assignments (project_id, task_id, is_enabled)
                SELECT ?, id, 1 FROM project_tasks WHERE project_id = ?
            """, (project_id, project_id))
    
    def authenticate_user(self, employee_code, password):
        """Authentifie un utilisateur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("""
            SELECT id, name, role FROM employees 
            WHERE employee_code = ? AND password_hash = ? AND is_active = 1
        """, (employee_code, password_hash))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'name': result[1], 
                'role': result[2],
                'employee_code': employee_code
            }
        return None
    
    def get_active_punch(self, employee_id):
        """Récupère le pointage actif d'un employé avec tâche"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                te.id, te.punch_in, te.break_start, te.break_end, 
                te.project_id, te.task_id,
                p.project_name, p.requires_task_selection,
                pt.task_name, pt.task_category, 
                COALESCE(eta.hourly_rate_override, pt.hourly_rate) as effective_rate
            FROM time_entries te
            LEFT JOIN projects p ON te.project_id = p.id
            LEFT JOIN project_tasks pt ON te.task_id = pt.id
            LEFT JOIN employee_task_assignments eta ON te.employee_id = eta.employee_id 
                AND te.project_id = eta.project_id AND te.task_id = eta.task_id
            WHERE te.employee_id = ? AND te.punch_out IS NULL 
            ORDER BY te.punch_in DESC LIMIT 1
        """, (employee_id,))
        
        result = cursor.fetchone()
        conn.close()
        return result
    
    def get_projects(self):
        """Récupère tous les projets actifs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, project_code, project_name, client_name, requires_task_selection 
            FROM projects WHERE is_active = 1
            ORDER BY project_name
        """)
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_all_projects(self):
        """Récupère TOUS les projets (actifs et inactifs)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, project_code, project_name, client_name, requires_task_selection, is_active, created_at
            FROM projects
            ORDER BY project_name
        """)
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_project_by_id(self, project_id):
        """Récupère un projet par son ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, project_code, project_name, client_name, requires_task_selection, is_active
            FROM projects WHERE id = ?
        """, (project_id,))
        
        result = cursor.fetchone()
        conn.close()
        return result
    
    def get_project_tasks(self, project_id):
        """Récupère les tâches d'un projet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, task_code, task_name, task_category, hourly_rate, description
            FROM project_tasks 
            WHERE project_id = ? AND is_active = 1
            ORDER BY task_category, task_name
        """, (project_id,))
        
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_all_project_tasks(self, project_id):
        """Récupère TOUTES les tâches d'un projet (actives et inactives)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, task_code, task_name, task_category, hourly_rate, description, is_active
            FROM project_tasks 
            WHERE project_id = ?
            ORDER BY task_category, task_name
        """, (project_id,))
        
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_task_by_id(self, task_id):
        """Récupère une tâche par son ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, project_id, task_code, task_name, task_category, hourly_rate, description, is_active
            FROM project_tasks WHERE id = ?
        """, (task_id,))
        
        result = cursor.fetchone()
        conn.close()
        return result
    
    # ================================
    # MÉTHODES POUR ASSIGNATIONS
    # ================================
    
    def get_project_assigned_tasks(self, project_id):
        """Récupère les tâches assignées à un projet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pt.id, pt.task_name, pt.task_category, pt.hourly_rate, pta.is_enabled
            FROM project_tasks pt
            INNER JOIN project_task_assignments pta ON pt.id = pta.task_id
            WHERE pta.project_id = ? AND pta.is_enabled = 1
            ORDER BY pt.task_category, pt.task_name
        """, (project_id,))
        
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_available_tasks_for_project(self, project_id):
        """Récupère toutes les tâches disponibles (non spécifiques au projet)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, task_code, task_name, task_category, hourly_rate, description
            FROM project_tasks 
            WHERE is_active = 1
            ORDER BY task_category, task_name
        """)
        
        result = cursor.fetchall()
        conn.close()
        return result
    
    def assign_task_to_project(self, project_id, task_id):
        """Assigne une tâche à un projet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO project_task_assignments (project_id, task_id, is_enabled)
                VALUES (?, ?, 1)
            """, (project_id, task_id))
            conn.commit()
            conn.close()
            return True, "Tâche assignée au projet"
        except Exception as e:
            conn.close()
            return False, f"Erreur lors de l'assignation: {str(e)}"
    
    def unassign_task_from_project(self, project_id, task_id):
        """Désassigne une tâche d'un projet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE project_task_assignments 
                SET is_enabled = 0 
                WHERE project_id = ? AND task_id = ?
            """, (project_id, task_id))
            conn.commit()
            conn.close()
            return True, "Tâche désassignée du projet"
        except Exception as e:
            conn.close()
            return False, f"Erreur lors de la désassignation: {str(e)}"
    
    def is_task_assigned_to_project(self, project_id, task_id):
        """Vérifie si une tâche est assignée à un projet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT is_enabled FROM project_task_assignments 
            WHERE project_id = ? AND task_id = ?
        """, (project_id, task_id))
        
        result = cursor.fetchone()
        conn.close()
        return result is not None and result[0] == 1
    
    def get_employee_authorized_tasks(self, employee_id, project_id):
        """Récupère les tâches autorisées pour un employé sur un projet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                pt.id, pt.task_name, pt.task_category, 
                eta.skill_level, 
                COALESCE(eta.hourly_rate_override, pt.hourly_rate) as effective_rate,
                pt.description
            FROM project_tasks pt
            INNER JOIN project_task_assignments pta ON pt.id = pta.task_id
            INNER JOIN employee_task_assignments eta ON pt.id = eta.task_id 
                AND eta.project_id = pta.project_id
            WHERE eta.employee_id = ? AND eta.project_id = ? 
                AND pta.is_enabled = 1 AND eta.is_authorized = 1 AND pt.is_active = 1
            ORDER BY pt.task_category, pt.task_name
        """, (employee_id, project_id))
        
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_task_assigned_employees(self, project_id, task_id):
        """Récupère les employés assignés à une tâche spécifique"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                e.id, e.name, e.employee_code,
                eta.skill_level, eta.hourly_rate_override, eta.is_authorized
            FROM employees e
            INNER JOIN employee_task_assignments eta ON e.id = eta.employee_id
            WHERE eta.project_id = ? AND eta.task_id = ? AND eta.is_authorized = 1
            ORDER BY e.name
        """, (project_id, task_id))
        
        result = cursor.fetchall()
        conn.close()
        return result
    
    def assign_employee_to_task(self, employee_id, project_id, task_id, skill_level='intermédiaire', hourly_rate_override=None):
        """Assigne un employé à une tâche"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO employee_task_assignments 
                (employee_id, project_id, task_id, skill_level, hourly_rate_override, is_authorized)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (employee_id, project_id, task_id, skill_level, hourly_rate_override))
            conn.commit()
            conn.close()
            return True, "Employé assigné à la tâche"
        except Exception as e:
            conn.close()
            return False, f"Erreur lors de l'assignation: {str(e)}"
    
    def unassign_employee_from_task(self, employee_id, project_id, task_id):
        """Désassigne un employé d'une tâche"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE employee_task_assignments 
                SET is_authorized = 0 
                WHERE employee_id = ? AND project_id = ? AND task_id = ?
            """, (employee_id, project_id, task_id))
            conn.commit()
            conn.close()
            return True, "Employé désassigné de la tâche"
        except Exception as e:
            conn.close()
            return False, f"Erreur lors de la désassignation: {str(e)}"
    
    def is_employee_authorized_for_task(self, employee_id, project_id, task_id):
        """Vérifie si un employé est autorisé pour une tâche"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT is_authorized FROM employee_task_assignments 
            WHERE employee_id = ? AND project_id = ? AND task_id = ?
        """, (employee_id, project_id, task_id))
        
        result = cursor.fetchone()
        conn.close()
        return result is not None and result[0] == 1
    
    def get_all_global_tasks(self):
        """Récupère toutes les tâches globales (pour assignation)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT task_name, task_category, id, project_id
            FROM project_tasks 
            WHERE is_active = 1
            ORDER BY task_category, task_name
        """)
        
        result = cursor.fetchall()
        conn.close()
        return result
    
    # ================================
    # MÉTHODES MÉTIER AVEC VALIDATION D&G
    # ================================
    
    def punch_in(self, employee_id, project_id, task_id=None, location=None, notes=None):
        """Enregistre un pointage d'arrivée avec vérification des assignations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Vérifier qu'il n'y a pas déjà un punch actif
        active = self.get_active_punch(employee_id)
        if active:
            conn.close()
            return False, "Vous êtes déjà pointé. Veuillez d'abord pointer la sortie."
        
        # Vérifier si le projet nécessite une tâche
        cursor.execute("SELECT requires_task_selection FROM projects WHERE id = ?", (project_id,))
        project_info = cursor.fetchone()
        
        if project_info and project_info[0] and not task_id:
            conn.close()
            return False, "Ce projet nécessite la sélection d'un poste de travail spécifique."
        
        # Vérifier l'autorisation de l'employé pour cette tâche
        if task_id:
            if not self.is_employee_authorized_for_task(employee_id, project_id, task_id):
                conn.close()
                return False, "Vous n'êtes pas autorisé à travailler sur ce poste pour ce projet."
        
        lat, lng = location if location else (None, None)
        cursor.execute("""
            INSERT INTO time_entries (employee_id, project_id, task_id, punch_in, location_lat, location_lng, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (employee_id, project_id, task_id, datetime.now(), lat, lng, notes))
        
        conn.commit()
        entry_id = cursor.lastrowid
        conn.close()
        return True, entry_id
    
    def change_task(self, employee_id, new_task_id, notes=None):
        """Change la tâche active avec vérification des assignations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Récupérer le pointage actif
        active = self.get_active_punch(employee_id)
        if not active:
            conn.close()
            return False, "Aucun pointage actif trouvé."
        
        time_entry_id = active[0]
        current_task_id = active[5]
        project_id = active[4]
        
        # Vérifier que la nouvelle tâche appartient au même projet et est autorisée
        if not self.is_employee_authorized_for_task(employee_id, project_id, new_task_id):
            conn.close()
            return False, "Vous n'êtes pas autorisé à travailler sur ce poste."
        
        # Enregistrer le changement de tâche
        cursor.execute("""
            INSERT INTO task_changes (time_entry_id, previous_task_id, new_task_id, notes)
            VALUES (?, ?, ?, ?)
        """, (time_entry_id, current_task_id, new_task_id, notes))
        
        # Mettre à jour l'entrée de temps
        cursor.execute("""
            UPDATE time_entries SET task_id = ? WHERE id = ?
        """, (new_task_id, time_entry_id))
        
        conn.commit()
        conn.close()
        return True, "Poste de travail changé avec succès."
    
    def punch_out(self, employee_id, notes=None):
        """Enregistre un pointage de sortie"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        active = self.get_active_punch(employee_id)
        if not active:
            conn.close()
            return False, "Aucun pointage actif trouvé."
        
        # Si en pause, terminer la pause
        if active[2] and not active[3]:  # break_start exists but break_end doesn't
            cursor.execute("""
                UPDATE time_entries 
                SET break_end = ?, total_break_minutes = total_break_minutes + ?
                WHERE id = ?
            """, (datetime.now(), 
                  int((datetime.now() - datetime.fromisoformat(active[2])).total_seconds() / 60),
                  active[0]))
        
        cursor.execute("""
            UPDATE time_entries 
            SET punch_out = ?, notes = COALESCE(notes, '') || COALESCE(?, '')
            WHERE id = ?
        """, (datetime.now(), f"\nNotes sortie: {notes}" if notes else "", active[0]))
        
        conn.commit()
        conn.close()
        return True, "Pointage de sortie enregistré."
    
    def start_break(self, employee_id):
        """Démarre une pause"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        active = self.get_active_punch(employee_id)
        if not active:
            conn.close()
            return False, "Aucun pointage actif trouvé."
        
        if active[2] and not active[3]:  # Already on break
            conn.close()
            return False, "Vous êtes déjà en pause."
        
        cursor.execute("""
            UPDATE time_entries 
            SET break_start = ?
            WHERE id = ?
        """, (datetime.now(), active[0]))
        
        conn.commit()
        conn.close()
        return True, "Pause démarrée."
    
    def end_break(self, employee_id):
        """Termine une pause"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        active = self.get_active_punch(employee_id)
        if not active or not active[2] or active[3]:
            conn.close()
            return False, "Aucune pause active trouvée."
        
        break_duration = int((datetime.now() - datetime.fromisoformat(active[2])).total_seconds() / 60)
        
        cursor.execute("""
            UPDATE time_entries 
            SET break_end = ?, total_break_minutes = total_break_minutes + ?
            WHERE id = ?
        """, (datetime.now(), break_duration, active[0]))
        
        conn.commit()
        conn.close()
        return True, f"Pause terminée ({break_duration} minutes)."
    
    def get_employee_timesheet(self, employee_id, start_date, end_date):
        """Récupère la feuille de temps d'un employé avec détails des tâches et assignations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                te.id,
                te.punch_in,
                te.punch_out,
                te.total_break_minutes,
                p.project_name,
                pt.task_name,
                COALESCE(eta.hourly_rate_override, pt.hourly_rate) as effective_rate,
                eta.skill_level,
                te.notes,
                CASE 
                    WHEN te.punch_out IS NOT NULL THEN
                        ROUND((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes, 2)
                    ELSE NULL
                END as total_minutes
            FROM time_entries te
            LEFT JOIN projects p ON te.project_id = p.id
            LEFT JOIN project_tasks pt ON te.task_id = pt.id
            LEFT JOIN employee_task_assignments eta ON te.employee_id = eta.employee_id 
                AND te.project_id = eta.project_id AND te.task_id = eta.task_id
            WHERE te.employee_id = ? 
            AND DATE(te.punch_in) BETWEEN ? AND ?
            ORDER BY te.punch_in DESC
        """, (employee_id, start_date, end_date))
        
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_task_changes_for_entry(self, time_entry_id):
        """Récupère l'historique des changements de tâches pour une entrée"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                tc.change_time,
                pt_prev.task_name as previous_task,
                pt_new.task_name as new_task,
                tc.notes
            FROM task_changes tc
            LEFT JOIN project_tasks pt_prev ON tc.previous_task_id = pt_prev.id
            LEFT JOIN project_tasks pt_new ON tc.new_task_id = pt_new.id
            WHERE tc.time_entry_id = ?
            ORDER BY tc.change_time
        """, (time_entry_id,))
        
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_all_employees(self):
        """Récupère tous les employés"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, employee_code, name, role, is_active, created_at
            FROM employees 
            WHERE role != 'admin'
            ORDER BY name
        """)
        
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_employee_by_id(self, employee_id):
        """Récupère un employé par son ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, employee_code, name, role, is_active
            FROM employees WHERE id = ?
        """, (employee_id,))
        
        result = cursor.fetchone()
        conn.close()
        return result
    
    def add_employee(self, employee_code, name, password, role='employee'):
        """Ajoute un nouvel employé"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Vérifier unicité
        cursor.execute("SELECT id FROM employees WHERE employee_code = ?", (employee_code,))
        if cursor.fetchone():
            conn.close()
            return False, f"Code employé '{employee_code}' déjà utilisé"
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("""
            INSERT INTO employees (employee_code, name, password_hash, role)
            VALUES (?, ?, ?, ?)
        """, (employee_code, name, password_hash, role))
        
        conn.commit()
        employee_id = cursor.lastrowid
        
        # Auto-assigner à tous les postes D&G avec niveau intermédiaire
        self._auto_assign_employee_to_dg_tasks(cursor, employee_id)
        
        conn.commit()
        conn.close()
        return True, "Employé créé avec succès et assigné aux postes D&G"
    
    def _auto_assign_employee_to_dg_tasks(self, cursor, employee_id):
        """Assigne automatiquement un nouvel employé à tous les postes D&G"""
        # Récupérer le projet D&G
        cursor.execute("SELECT id FROM projects WHERE project_code = 'DG-GENERAL'")
        dg_project = cursor.fetchone()
        
        if dg_project:
            project_id = dg_project[0]
            
            # Assigner à toutes les tâches D&G avec niveau intermédiaire
            cursor.execute("""
                INSERT OR IGNORE INTO employee_task_assignments 
                (employee_id, project_id, task_id, skill_level, hourly_rate_override, is_authorized)
                SELECT ?, ?, pt.id, 'intermédiaire', pt.hourly_rate, 1 
                FROM project_tasks pt WHERE pt.project_id = ?
            """, (employee_id, project_id, project_id))
    
    def update_employee(self, employee_id, **kwargs):
        """Met à jour un employé"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Construire la requête dynamiquement
        set_clauses = []
        values = []
        
        if 'employee_code' in kwargs:
            # Vérifier unicité du code
            cursor.execute("SELECT id FROM employees WHERE employee_code = ? AND id != ?", 
                          (kwargs['employee_code'], employee_id))
            if cursor.fetchone():
                conn.close()
                return False, f"Code employé '{kwargs['employee_code']}' déjà utilisé"
            set_clauses.append("employee_code = ?")
            values.append(kwargs['employee_code'])
        
        if 'name' in kwargs:
            set_clauses.append("name = ?")
            values.append(kwargs['name'])
        
        if 'password' in kwargs:
            password_hash = hashlib.sha256(kwargs['password'].encode()).hexdigest()
            set_clauses.append("password_hash = ?")
            values.append(password_hash)
        
        if 'role' in kwargs:
            set_clauses.append("role = ?")
            values.append(kwargs['role'])
        
        if 'is_active' in kwargs:
            set_clauses.append("is_active = ?")
            values.append(kwargs['is_active'])
        
        if not set_clauses:
            conn.close()
            return False, "Aucune modification spécifiée"
        
        values.append(employee_id)
        query = f"UPDATE employees SET {', '.join(set_clauses)} WHERE id = ?"
        
        try:
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            return True, "Employé mis à jour avec succès"
        except Exception as e:
            conn.close()
            return False, f"Erreur lors de la mise à jour: {str(e)}"
    
    def delete_employee(self, employee_id):
        """Supprime un employé (ou le désactive)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Vérifier si l'employé a des pointages
        cursor.execute("SELECT COUNT(*) FROM time_entries WHERE employee_id = ?", (employee_id,))
        time_entries_count = cursor.fetchone()[0]
        
        if time_entries_count > 0:
            # Désactiver au lieu de supprimer
            cursor.execute("UPDATE employees SET is_active = 0 WHERE id = ?", (employee_id,))
            conn.commit()
            conn.close()
            return True, f"Employé désactivé (avait {time_entries_count} pointages)"
        else:
            # Supprimer complètement
            cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
            conn.commit()
            conn.close()
            return True, "Employé supprimé définitivement"
    
    def add_project(self, project_code, project_name, client_name=None, requires_task_selection=True):
        """Ajoute un nouveau projet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Vérifier unicité
        cursor.execute("SELECT id FROM projects WHERE project_code = ?", (project_code,))
        if cursor.fetchone():
            conn.close()
            return False, f"Code projet '{project_code}' déjà utilisé"
        
        try:
            cursor.execute("""
                INSERT INTO projects (project_code, project_name, client_name, requires_task_selection)
                VALUES (?, ?, ?, ?)
            """, (project_code, project_name, client_name, requires_task_selection))
            conn.commit()
            project_id = cursor.lastrowid
            conn.close()
            return True, f"Projet créé avec succès (ID: {project_id})"
        except Exception as e:
            conn.close()
            return False, f"Erreur lors de la création: {str(e)}"
    
    def update_project(self, project_id, **kwargs):
        """Met à jour un projet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Construire la requête dynamiquement
        set_clauses = []
        values = []
        
        if 'project_code' in kwargs:
            # Vérifier unicité du code
            cursor.execute("SELECT id FROM projects WHERE project_code = ? AND id != ?", 
                          (kwargs['project_code'], project_id))
            if cursor.fetchone():
                conn.close()
                return False, f"Code projet '{kwargs['project_code']}' déjà utilisé"
            set_clauses.append("project_code = ?")
            values.append(kwargs['project_code'])
        
        if 'project_name' in kwargs:
            set_clauses.append("project_name = ?")
            values.append(kwargs['project_name'])
        
        if 'client_name' in kwargs:
            set_clauses.append("client_name = ?")
            values.append(kwargs['client_name'])
        
        if 'requires_task_selection' in kwargs:
            set_clauses.append("requires_task_selection = ?")
            values.append(kwargs['requires_task_selection'])
        
        if 'is_active' in kwargs:
            set_clauses.append("is_active = ?")
            values.append(kwargs['is_active'])
        
        if not set_clauses:
            conn.close()
            return False, "Aucune modification spécifiée"
        
        values.append(project_id)
        query = f"UPDATE projects SET {', '.join(set_clauses)} WHERE id = ?"
        
        try:
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            return True, "Projet mis à jour avec succès"
        except Exception as e:
            conn.close()
            return False, f"Erreur lors de la mise à jour: {str(e)}"
    
    def delete_project(self, project_id):
        """Supprime un projet (ou le désactive)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Vérifier si le projet a des pointages
        cursor.execute("SELECT COUNT(*) FROM time_entries WHERE project_id = ?", (project_id,))
        time_entries_count = cursor.fetchone()[0]
        
        # Vérifier si le projet a des tâches
        cursor.execute("SELECT COUNT(*) FROM project_tasks WHERE project_id = ?", (project_id,))
        tasks_count = cursor.fetchone()[0]
        
        if time_entries_count > 0 or tasks_count > 0:
            # Désactiver au lieu de supprimer
            cursor.execute("UPDATE projects SET is_active = 0 WHERE id = ?", (project_id,))
            # Désactiver aussi les tâches associées
            cursor.execute("UPDATE project_tasks SET is_active = 0 WHERE project_id = ?", (project_id,))
            conn.commit()
            conn.close()
            return True, f"Projet désactivé (avait {time_entries_count} pointages et {tasks_count} tâches)"
        else:
            # Supprimer complètement
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            conn.close()
            return True, "Projet supprimé définitivement"
    
    def add_task(self, project_id, task_code, task_name, task_category=None, hourly_rate=0.0, description=None):
        """Ajoute une nouvelle tâche"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Vérifier unicité du code dans le projet
        cursor.execute("SELECT id FROM project_tasks WHERE project_id = ? AND task_code = ?", 
                      (project_id, task_code))
        if cursor.fetchone():
            conn.close()
            return False, f"Code tâche '{task_code}' déjà utilisé dans ce projet"
        
        try:
            cursor.execute("""
                INSERT INTO project_tasks (project_id, task_code, task_name, task_category, hourly_rate, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (project_id, task_code, task_name, task_category, hourly_rate, description))
            conn.commit()
            task_id = cursor.lastrowid
            conn.close()
            return True, f"Tâche créée avec succès (ID: {task_id})"
        except Exception as e:
            conn.close()
            return False, f"Erreur lors de la création: {str(e)}"
    
    def update_task(self, task_id, **kwargs):
        """Met à jour une tâche"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Récupérer le project_id de la tâche
        cursor.execute("SELECT project_id FROM project_tasks WHERE id = ?", (task_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Tâche introuvable"
        
        project_id = result[0]
        
        # Construire la requête dynamiquement
        set_clauses = []
        values = []
        
        if 'task_code' in kwargs:
            # Vérifier unicité du code dans le projet
            cursor.execute("SELECT id FROM project_tasks WHERE project_id = ? AND task_code = ? AND id != ?", 
                          (project_id, kwargs['task_code'], task_id))
            if cursor.fetchone():
                conn.close()
                return False, f"Code tâche '{kwargs['task_code']}' déjà utilisé dans ce projet"
            set_clauses.append("task_code = ?")
            values.append(kwargs['task_code'])
        
        if 'task_name' in kwargs:
            set_clauses.append("task_name = ?")
            values.append(kwargs['task_name'])
        
        if 'task_category' in kwargs:
            set_clauses.append("task_category = ?")
            values.append(kwargs['task_category'])
        
        if 'hourly_rate' in kwargs:
            set_clauses.append("hourly_rate = ?")
            values.append(kwargs['hourly_rate'])
        
        if 'description' in kwargs:
            set_clauses.append("description = ?")
            values.append(kwargs['description'])
        
        if 'is_active' in kwargs:
            set_clauses.append("is_active = ?")
            values.append(kwargs['is_active'])
        
        if not set_clauses:
            conn.close()
            return False, "Aucune modification spécifiée"
        
        values.append(task_id)
        query = f"UPDATE project_tasks SET {', '.join(set_clauses)} WHERE id = ?"
        
        try:
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            return True, "Tâche mise à jour avec succès"
        except Exception as e:
            conn.close()
            return False, f"Erreur lors de la mise à jour: {str(e)}"
    
    def delete_task(self, task_id):
        """Supprime une tâche (ou la désactive)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Vérifier si la tâche est utilisée
        cursor.execute("SELECT COUNT(*) FROM time_entries WHERE task_id = ?", (task_id,))
        usage_count = cursor.fetchone()[0]
        
        if usage_count > 0:
            # Désactiver au lieu de supprimer
            cursor.execute("UPDATE project_tasks SET is_active = 0 WHERE id = ?", (task_id,))
            conn.commit()
            conn.close()
            return True, f"Tâche désactivée (était utilisée {usage_count} fois)"
        else:
            # Supprimer complètement
            cursor.execute("DELETE FROM project_tasks WHERE id = ?", (task_id,))
            conn.commit()
            conn.close()
            return True, "Tâche supprimée définitivement"
    
    def get_dashboard_stats(self):
        """Récupère les statistiques pour le tableau de bord"""
        conn = sqlite3.connect(self.db_path)
        today = date.today()
        
        # Employés pointés aujourd'hui
        pointés_aujourd_hui = pd.read_sql_query("""
            SELECT COUNT(DISTINCT employee_id) as count
            FROM time_entries 
            WHERE DATE(punch_in) = ?
        """, conn, params=(today,))
        
        # Employés au travail
        au_travail = pd.read_sql_query("""
            SELECT COUNT(*) as count 
            FROM time_entries 
            WHERE punch_out IS NULL AND DATE(punch_in) = ?
        """, conn, params=(today,))
        
        # Heures travaillées aujourd'hui
        heures_total = pd.read_sql_query("""
            SELECT COALESCE(SUM(CASE 
                WHEN punch_out IS NOT NULL THEN
                    ROUND(((JULIANDAY(punch_out) - JULIANDAY(punch_in)) * 24 * 60 - total_break_minutes) / 60, 2)
                ELSE 0
            END), 0) as total_hours
            FROM time_entries 
            WHERE DATE(punch_in) = ?
        """, conn, params=(today,))
        
        # Retards
        retards = pd.read_sql_query("""
            SELECT COUNT(*) as count
            FROM time_entries 
            WHERE DATE(punch_in) = ? AND TIME(punch_in) > '08:30:00'
        """, conn, params=(today,))
        
        conn.close()
        
        return {
            'pointés_aujourd_hui': pointés_aujourd_hui.iloc[0]['count'],
            'au_travail': au_travail.iloc[0]['count'],
            'heures_total': heures_total.iloc[0]['total_hours'],
            'retards': retards.iloc[0]['count']
        }
    
    def get_dg_enhanced_stats(self):
        """Statistiques spécialisées pour Desmarais & Gagné"""
        conn = sqlite3.connect(self.db_path)
        today = date.today()
        
        # Revenus temps réel avec taux D&G
        revenus_query = """
            SELECT COALESCE(SUM(CASE 
                WHEN te.punch_out IS NOT NULL THEN
                    (((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60) 
                    * COALESCE(eta.hourly_rate_override, pt.hourly_rate)
                ELSE 0
            END), 0) as revenus_journee
            FROM time_entries te
            LEFT JOIN project_tasks pt ON te.task_id = pt.id
            LEFT JOIN employee_task_assignments eta ON te.employee_id = eta.employee_id 
                AND te.project_id = eta.project_id AND te.task_id = eta.task_id
            WHERE DATE(te.punch_in) = ?
        """
        
        revenus_df = pd.read_sql_query(revenus_query, conn, params=(today,))
        revenus_today = revenus_df.iloc[0]['revenus_journee']
        
        # Postes premium actifs (≥130$/h)
        premium_query = """
            SELECT COUNT(DISTINCT te.id) as sessions_premium
            FROM time_entries te
            INNER JOIN project_tasks pt ON te.task_id = pt.id
            WHERE DATE(te.punch_in) = ? AND pt.hourly_rate >= 130
            AND te.punch_out IS NULL
        """
        
        premium_df = pd.read_sql_query(premium_query, conn, params=(today,))
        premium_active = premium_df.iloc[0]['sessions_premium']
        
        # Efficacité moyenne
        efficiency_query = """
            SELECT 
                COALESCE(SUM(((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60), 0) as total_hours,
                COALESCE(SUM((((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60) 
                    * COALESCE(eta.hourly_rate_override, pt.hourly_rate)), 0) as total_revenue
            FROM time_entries te
            LEFT JOIN project_tasks pt ON te.task_id = pt.id
            LEFT JOIN employee_task_assignments eta ON te.employee_id = eta.employee_id 
                AND te.project_id = eta.project_id AND te.task_id = eta.task_id
            WHERE DATE(te.punch_in) = ? AND te.punch_out IS NOT NULL
        """
        
        efficiency_df = pd.read_sql_query(efficiency_query, conn, params=(today,))
        total_hours = efficiency_df.iloc[0]['total_hours']
        total_revenue = efficiency_df.iloc[0]['total_revenue']
        avg_efficiency = total_revenue / total_hours if total_hours > 0 else 0
        
        # Utilisation postes haute valeur
        high_value_query = """
            SELECT 
                ROUND(
                    (COUNT(CASE WHEN pt.hourly_rate >= 120 THEN 1 END) * 100.0 / COUNT(*)), 1
                ) as pct_high_value
            FROM time_entries te
            INNER JOIN project_tasks pt ON te.task_id = pt.id
            WHERE DATE(te.punch_in) = ?
        """
        
        high_value_df = pd.read_sql_query(high_value_query, conn, params=(today,))
        pct_high_value = high_value_df.iloc[0]['pct_high_value'] or 0
        
        conn.close()
        
        return {
            'revenus_today': revenus_today,
            'premium_active': premium_active,
            'avg_efficiency': avg_efficiency,
            'pct_high_value': pct_high_value,
            'total_hours': total_hours,
            'total_revenue': total_revenue
        }

# ================================
# UTILITAIRES
# ================================

def format_duration(minutes):
    """Formate une durée en minutes vers HH:MM"""
    if pd.isna(minutes) or minutes is None or minutes == 0:
        return "00:00"
    
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"

def get_time_display():
    """Retourne l'heure actuelle formatée"""
    return datetime.now().strftime('%H:%M:%S')

def generate_excel_report(data, filename="rapport_temps.xlsx"):
    """Génère un rapport Excel"""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        data.to_excel(writer, sheet_name='Rapport_Temps', index=False)
    
    return output.getvalue()

def get_skill_badge_class(skill_level):
    """Retourne la classe CSS pour le badge de niveau"""
    skill_classes = {
        'débutant': 'skill-debutant',
        'intermédiaire': 'skill-intermediaire', 
        'avancé': 'skill-avance',
        'expert': 'skill-expert'
    }
    return skill_classes.get(skill_level, 'skill-intermediaire')

def get_rate_class(rate):
    """Retourne la classe CSS selon le taux horaire D&G"""
    if rate >= 130:
        return 'rate-premium'
    elif rate >= 100:
        return 'rate-high'
    elif rate >= 90:
        return 'rate-standard'
    else:
        return 'rate-admin'

def get_rate_indicator(rate):
    """Retourne l'indicateur visuel pour le taux"""
    if rate >= 130:
        return "🔥"  # Premium
    elif rate >= 100:
        return "⚡"  # Élevé
    elif rate >= 90:
        return "💼"  # Standard
    else:
        return "📋"  # Administratif

# ================================
# SÉLECTEUR DE TÂCHE AVANCÉ POUR D&G
# ================================

def show_advanced_task_selector_dg(db, user_info, project_id):
    """Sélecteur de poste de travail avancé pour les 34 postes D&G"""
    
    st.markdown("#### 🔧 Sélection de Poste de Travail D&G")
    
    # Récupérer les tâches autorisées
    authorized_tasks = db.get_employee_authorized_tasks(user_info['id'], project_id)
    
    if not authorized_tasks:
        st.error("❌ Aucun poste autorisé pour ce projet")
        st.info("💡 Contactez votre superviseur pour obtenir les autorisations nécessaires")
        return None
    
    # Filtres avancés
    with st.container():
        st.markdown('<div class="filter-container">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Filtre par catégorie
            categories = list(set([task[2] for task in authorized_tasks]))
            selected_category = st.selectbox(
                "📋 Filtrer par catégorie", 
                ["Toutes"] + sorted(categories),
                help="Filtrer les postes par type d'opération"
            )
        
        with col2:
            # Filtre par taux horaire
            rates = [task[4] for task in authorized_tasks]
            min_rate, max_rate = min(rates), max(rates)
            rate_range = st.slider(
                "💰 Plage de taux ($/h)",
                min_value=float(min_rate),
                max_value=float(max_rate),
                value=(float(min_rate), float(max_rate)),
                step=5.0,
                help="Filtrer par gamme de taux horaire"
            )
        
        with col3:
            # Recherche textuelle
            search_term = st.text_input(
                "🔍 Rechercher un poste",
                placeholder="Ex: soudage, robot, plasma...",
                help="Rechercher par nom ou type de poste"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Filtrer les tâches selon les critères
    filtered_tasks = []
    for task in authorized_tasks:
        task_id, task_name, task_category, skill_level, effective_rate, description = task
        
        # Filtre catégorie
        if selected_category != "Toutes" and task_category != selected_category:
            continue
        
        # Filtre taux
        if not (rate_range[0] <= effective_rate <= rate_range[1]):
            continue
        
        # Filtre recherche
        if search_term and search_term.lower() not in task_name.lower() and search_term.lower() not in (task_category or "").lower():
            continue
        
        filtered_tasks.append(task)
    
    if not filtered_tasks:
        st.warning("⚠️ Aucun poste ne correspond aux critères de recherche")
        return None
    
    # Affichage des postes filtrés avec design D&G
    st.markdown(f"**{len(filtered_tasks)} poste(s) disponible(s):**")
    
    # Grouper par catégorie pour affichage organisé
    tasks_by_category = {}
    for task in filtered_tasks:
        category = task[2] or "Général"
        if category not in tasks_by_category:
            tasks_by_category[category] = []
        tasks_by_category[category].append(task)
    
    selected_task = None
    
    # Couleurs par catégorie D&G
    category_colors = {
        'Soudage': '#e74c3c',
        'Découpe et Perçage': '#3498db', 
        'Formage et Assemblage': '#9b59b6',
        'Finition': '#2ecc71',
        'Préparation et Programmation': '#f39c12',
        'Manutention et Cisaillage': '#95a5a6',
        'Contrôle Qualité': '#1abc9c',
        'Expédition': '#e67e22'
    }
    
    # Afficher par catégorie avec style D&G
    for category, category_tasks in tasks_by_category.items():
        color = category_colors.get(category, '#34495e')
        
        # Trier par taux décroissant dans chaque catégorie
        category_tasks.sort(key=lambda x: x[4], reverse=True)
        
        with st.expander(f"🔧 {category} ({len(category_tasks)} postes)", expanded=True):
            
            for task in category_tasks:
                task_id, task_name, task_category, skill_level, effective_rate, description = task
                
                # Déterminer le style selon le taux
                if effective_rate >= 130:
                    card_class = "task-card-dg premium"
                    indicator_class = "premium-indicator"
                elif effective_rate >= 100:
                    card_class = "task-card-dg high-value"
                    indicator_class = "high-value-indicator"
                else:
                    card_class = "task-card-dg"
                    indicator_class = "task-indicator"
                
                rate_class = get_rate_class(effective_rate)
                rate_icon = get_rate_indicator(effective_rate)
                
                # Carte de poste avec style D&G
                task_key = f"select_task_dg_{task_id}_{category.replace(' ', '_')}"
                
                st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
                
                col_task, col_rate, col_skill, col_btn = st.columns([3, 1, 1, 1])
                
                with col_task:
                    st.markdown(f"**{task_name}**")
                    if description:
                        st.caption(description)
                    st.markdown(f'<div class="{indicator_class}">{task_category}</div>', unsafe_allow_html=True)
                
                with col_rate:
                    st.markdown(f'<div class="{rate_class}">{rate_icon} {effective_rate:.0f}$ CAD</div>', unsafe_allow_html=True)
                
                with col_skill:
                    skill_colors = {
                        'expert': '🟣',
                        'avancé': '🟢', 
                        'intermédiaire': '🟡',
                        'débutant': '🟠'
                    }
                    skill_icon = skill_colors.get(skill_level, '⚪')
                    st.markdown(f"**{skill_icon} {skill_level.capitalize()}**")
                
                with col_btn:
                    if st.button("✅ Sélectionner", key=task_key):
                        selected_task = task
                        st.session_state.selected_task_dg = selected_task
                        st.success(f"✅ **{task_name}** sélectionné")
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    # Afficher le poste sélectionné
    if 'selected_task_dg' in st.session_state:
        task = st.session_state.selected_task_dg
        
        st.markdown("---")
        st.markdown("### ✅ Poste de Travail Sélectionné")
        
        # Card de confirmation stylée
        rate_class = get_rate_class(task[4])
        rate_icon = get_rate_indicator(task[4])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{task[1]}</div>
                <div class="metric-label">📋 {task[2]}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value {rate_class}">{rate_icon} {task[4]:.0f}$ CAD</div>
                <div class="metric-label">💰 Taux Effectif / Heure</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            skill_class = get_skill_badge_class(task[3])
            if st.button("🔄 Changer de poste", key="change_selected_task"):
                del st.session_state.selected_task_dg
                st.rerun()
        
        return task[0]  # Return task_id
    
    return None

# ================================
# INTERFACE DE CONNEXION
# ================================

def show_login_page():
    """Affiche la page de connexion"""
    
    # Logo et header
    st.markdown("""
    <div class="main-header">
        <h1>⏱️ TimeTracker Pro</h1>
        <p>Système de Pointage Avancé - Desmarais & Gagné</p>
        <small>🔧 Version avec 34 Postes de Travail Réels et Taux D&G</small>
    </div>
    """, unsafe_allow_html=True)
    
    # Interface de connexion centrée
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Connexion Employé")
        
        with st.form("login_form"):
            employee_code = st.text_input(
                "Code Employé", 
                placeholder="Ex: EMP001 ou ADMIN",
                help="Entrez votre code employé"
            )
            password = st.text_input(
                "Mot de passe", 
                type="password",
                help="Mot de passe fourni par l'administrateur"
            )
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submit = st.form_submit_button("🔑 Se connecter", use_container_width=True)
            with col_btn2:
                demo = st.form_submit_button("👀 Démo", use_container_width=True, help="Connexion démo avec ADMIN/admin123")
            
            if demo:
                employee_code = "ADMIN"
                password = "admin123"
                submit = True
            
            if submit:
                if employee_code and password:
                    db = get_database()
                    user = db.authenticate_user(employee_code.upper(), password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user_info = user
                        st.success(f"✅ Connexion réussie ! Bienvenue {user['name']}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("🚫 Code employé ou mot de passe incorrect")
                else:
                    st.warning("⚠️ Veuillez remplir tous les champs")
        
        # Informations de connexion par défaut
        with st.expander("ℹ️ Informations de connexion", expanded=False):
            st.info("""
            **Connexion administrateur par défaut :**
            - Code : `ADMIN`
            - Mot de passe : `admin123`
            
            **🆕 Nouveautés Version D&G :**
            - ✅ 34 postes de travail réels Desmarais & Gagné
            - ✅ Taux horaires réels (85-140$ CAD)
            - ✅ Catégorisation avancée (8 catégories)
            - ✅ Sélecteur de poste avec filtres intelligents
            - ✅ Dashboard revenus temps réel
            - ✅ Analytics par niveau de taux
            - ✅ Assignations automatiques nouveaux employés
            - ✅ Rapports spécialisés rentabilité
            """)

# ================================
# INTERFACE EMPLOYÉ ENRICHIE POUR D&G
# ================================

def show_employee_interface():
    """Interface principale pour les employés avec postes D&G"""
    
    user_info = st.session_state.user_info
    db = get_database()
    
    # Header avec horloge temps réel
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"""
        <div class="main-header">
            <h1>👋 Bonjour {user_info['name']}</h1>
            <p>Interface de pointage D&G - Code: {user_info['employee_code']}</p>
            <small>🏭 34 postes de travail disponibles</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Horloge temps réel
        clock_placeholder = st.empty()
        clock_placeholder.markdown(f"""
        <div class="digital-clock" id="digital-clock">
            {get_time_display()}
        </div>
        """, unsafe_allow_html=True)
    
    # Récupérer statut actuel
    active_punch = db.get_active_punch(user_info['id'])
    
    # Interface de pointage
    col1, col2 = st.columns(2)
    
    with col1:
        # Affichage du statut enrichi avec détails D&G
        if active_punch:
            punch_time = datetime.fromisoformat(active_punch[1])
            worked_time = datetime.now() - punch_time
            hours, remainder = divmod(worked_time.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            
            project_name = active_punch[6] or "Projet non spécifié"
            task_name = active_punch[8] or "Aucun poste"
            task_category = active_punch[9] or ""
            effective_rate = active_punch[10] or 0
            
            # Calculer revenus estimés
            total_hours = hours + minutes/60
            estimated_earnings = total_hours * effective_rate
            
            # Indicateurs visuels D&G
            rate_icon = get_rate_indicator(effective_rate)
            rate_class = get_rate_class(effective_rate)
            
            if active_punch[2] and not active_punch[3]:  # En pause
                break_start = datetime.fromisoformat(active_punch[2])
                break_duration = datetime.now() - break_start
                break_minutes = int(break_duration.total_seconds() / 60)
                
                st.markdown(f"""
                <div class="status-card break">
                    <h3>☕ EN PAUSE</h3>
                    <p><strong>Projet:</strong> {project_name}</p>
                    <div class="task-indicator">{task_category}: {task_name}</div>
                    <p><strong>Arrivée:</strong> {punch_time.strftime('%H:%M')}</p>
                    <p><strong>Temps travaillé:</strong> {int(hours)}h {int(minutes)}m</p>
                    <p><strong>En pause depuis:</strong> {break_minutes} minutes</p>
                    <p class="{rate_class}"><strong>Taux:</strong> {rate_icon} {effective_rate:.0f}$ CAD/h</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="status-card punched-in task-active">
                    <h3>✅ AU TRAVAIL</h3>
                    <p><strong>Projet:</strong> {project_name}</p>
                    <div class="task-indicator task-active-indicator">{task_category}: {task_name}</div>
                    <p><strong>Arrivée:</strong> {punch_time.strftime('%H:%M')}</p>
                    <p><strong>Temps travaillé:</strong> {int(hours)}h {int(minutes)}m</p>
                    <p class="{rate_class}"><strong>Taux:</strong> {rate_icon} {effective_rate:.0f}$ CAD/h</p>
                    <p><strong>Revenus estimés:</strong> {estimated_earnings:.2f}$ CAD</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-card">
                <h3>⭕ NON POINTÉ</h3>
                <p>Vous n'êtes pas actuellement pointé au travail</p>
                <p><strong>Prêt à commencer votre journée ?</strong></p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # Boutons d'action avec sélection de poste D&G
        if not active_punch:
            # Interface de pointage d'arrivée avec sélecteur D&G avancé
            st.markdown("#### 🔴 Pointer l'arrivée")
            
            projects = db.get_projects()
            if projects:
                project_options = {f"{p[1]} - {p[3] or 'N/A'}": p for p in projects}
                selected_project_display = st.selectbox(
                    "📋 Sélectionner le projet", 
                    options=list(project_options.keys()),
                    help="Choisissez le projet sur lequel vous allez travailler"
                )
                
                selected_project = project_options[selected_project_display]
                project_id = selected_project[0]
                requires_task = selected_project[4]
                
                # Sélection de poste de travail D&G
                task_id = None
                if requires_task:
                    task_id = show_advanced_task_selector_dg(db, user_info, project_id)
                
                notes_arrivee = st.text_area(
                    "📝 Notes (optionnel)", 
                    placeholder="Ex: Travail sur fabrication porte ARQ-2025...",
                    help="Décrivez brièvement ce que vous allez faire"
                )
                
                # Bouton de pointage
                punch_enabled = not requires_task or task_id is not None
                if st.button("🔴 POINTER L'ARRIVÉE", key="punch_in", disabled=not punch_enabled):
                    success, result = db.punch_in(user_info['id'], project_id, task_id, notes=notes_arrivee)
                    if success:
                        st.success("✅ Pointage d'arrivée enregistré!")
                        if 'selected_task_dg' in st.session_state:
                            del st.session_state.selected_task_dg
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ {result}")
                
                if requires_task and not task_id:
                    st.warning("⚠️ Vous devez sélectionner un poste de travail autorisé pour ce projet")
                
            else:
                st.warning("⚠️ Aucun projet disponible. Contactez l'administrateur.")
        
        else:
            # Interface pour employé pointé avec changement de poste D&G
            st.markdown("#### ⚡ Actions rapides")
            
            # Changement de poste basé sur les assignations D&G
            current_project_id = active_punch[4]
            current_task_id = active_punch[5]
            
            if current_project_id:
                authorized_tasks = db.get_employee_authorized_tasks(user_info['id'], current_project_id)
                available_tasks = [t for t in authorized_tasks if t[0] != current_task_id]
                
                if available_tasks:
                    st.markdown("##### 🔄 Changer de poste de travail")
                    
                    # Grouper par catégorie pour changement
                    tasks_by_category = {}
                    for t in available_tasks:
                        category = t[2] or "Général"
                        if category not in tasks_by_category:
                            tasks_by_category[category] = []
                        tasks_by_category[category].append(t)
                    
                    selected_category_change = st.selectbox(
                        "Catégorie de poste",
                        options=list(tasks_by_category.keys()),
                        help="Sélectionnez d'abord la catégorie"
                    )
                    
                    if selected_category_change:
                        category_tasks = tasks_by_category[selected_category_change]
                        task_options = {}
                        
                        for t in category_tasks:
                            rate_icon = get_rate_indicator(t[4])
                            task_display = f"{t[1]} ({rate_icon} {t[4]:.0f}$/h) - {t[3]}"
                            task_options[task_display] = t[0]
                        
                        if task_options:
                            new_task_display = st.selectbox(
                                "Nouveau poste autorisé", 
                                options=list(task_options.keys()),
                                help="Changez de poste sans pointer sortie/entrée"
                            )
                            
                            change_notes = st.text_input(
                                "Raison du changement", 
                                placeholder="Ex: Changement de priorité production..."
                            )
                            
                            if st.button("🔄 CHANGER DE POSTE", key="change_task"):
                                new_task_id = task_options[new_task_display]
                                success, message = db.change_task(user_info['id'], new_task_id, change_notes)
                                if success:
                                    st.success(f"✅ {message}")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ {message}")
                else:
                    st.info("ℹ️ Aucun autre poste autorisé disponible pour ce projet")
            
            st.markdown("---")
            
            # Gestion des pauses
            if active_punch[2] and not active_punch[3]:  # En pause
                if st.button("🔵 REPRENDRE LE TRAVAIL", key="end_break"):
                    success, message = db.end_break(user_info['id'])
                    if success:
                        st.success(f"✅ {message}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
            else:
                if st.button("🟡 COMMENCER UNE PAUSE", key="start_break"):
                    success, message = db.start_break(user_info['id'])
                    if success:
                        st.success(f"✅ {message}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
            
            st.markdown("---")
            st.markdown("#### 📝 Fin de journée")
            notes_sortie = st.text_area(
                "Notes de fin de journée", 
                placeholder="Résumé du travail effectué aujourd'hui...",
                help="Décrivez votre travail d'aujourd'hui (optionnel mais recommandé)"
            )
            
            if st.button("🔴 POINTER LA SORTIE", key="punch_out"):
                success, message = db.punch_out(user_info['id'], notes_sortie)
                if success:
                    st.success(f"✅ {message}")
                    st.success("🎉 Bonne fin de journée !")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
    
    # Feuille de temps récente avec détails des assignations et taux D&G
    st.markdown("---")
    st.markdown("### 📊 Mes heures récentes (avec taux D&G)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("📅 Date de début", value=date.today() - timedelta(days=7))
    with col2:
        end_date = st.date_input("📅 Date de fin", value=date.today())
    with col3:
        refresh_data = st.button("🔄 Actualiser", help="Recharger les données")
    
    # Récupérer et afficher les données
    timesheet = db.get_employee_timesheet(user_info['id'], start_date, end_date)
    
    if timesheet:
        df_data = []
        total_hours = 0
        total_earnings = 0
        total_days = 0
        
        for entry in timesheet:
            punch_in = datetime.fromisoformat(entry[1])
            punch_out = datetime.fromisoformat(entry[2]) if entry[2] else None
            
            if punch_out and entry[9]:  # Si pointage complet
                hours = entry[9] / 60
                total_hours += hours
                total_days += 1
                status = "✅ Complet"
                hours_display = f"{hours:.2f}h"
                
                # Calcul des revenus avec taux effectif D&G
                effective_rate = entry[6] or 0
                skill_level = entry[7] or "N/A"
                earnings = hours * effective_rate
                total_earnings += earnings
                
                # Formatage avec icônes selon taux
                rate_icon = get_rate_indicator(effective_rate)
                earnings_display = f"{earnings:.2f}$"
                rate_display = f"{rate_icon} {effective_rate:.0f}$"
            else:
                hours = 0
                earnings = 0
                effective_rate = entry[6] or 0
                skill_level = entry[7] or "N/A"
                status = "🔄 En cours" if not punch_out else "⚠️ Incomplet"
                hours_display = "-"
                earnings_display = "-"
                rate_display = f"{get_rate_indicator(effective_rate)} {effective_rate:.0f}$" if effective_rate else "0$"
            
            df_data.append({
                "Date": punch_in.strftime('%Y-%m-%d'),
                "Jour": punch_in.strftime('%A'),
                "Arrivée": punch_in.strftime('%H:%M'),
                "Sortie": punch_out.strftime('%H:%M') if punch_out else "-",
                "Pause": format_duration(entry[3]) if entry[3] else "00:00",
                "Projet": entry[4] or "Non spécifié",
                "Poste": entry[5] or "Générale",
                "Niveau": skill_level,
                "Taux": rate_display,
                "Heures": hours_display,
                "Revenus": earnings_display,
                "Statut": status
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            # Résumé enrichi avec métriques D&G
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{total_hours:.1f}h</div>
                    <div class="metric-label">Total heures</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                avg_hours = total_hours / total_days if total_days > 0 else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{avg_hours:.1f}h</div>
                    <div class="metric-label">Moyenne/jour</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{total_days}</div>
                    <div class="metric-label">Jours travaillés</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                overtime = max(0, total_hours - (total_days * 8))
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{overtime:.1f}h</div>
                    <div class="metric-label">Heures supp.</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col5:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{total_earnings:.0f}$</div>
                    <div class="metric-label">Revenus période</div>
                </div>
                """, unsafe_allow_html=True)
        
    else:
        st.info("📭 Aucune entrée de temps pour cette période")

# ================================
# DASHBOARD ADMIN ENRICHI POUR D&G
# ================================

def show_dg_enhanced_dashboard(db):
    """Dashboard admin spécifique aux réalités D&G"""
    
    st.markdown("### 📊 Dashboard Desmarais & Gagné - Analytics Temps Réel")
    
    # Métriques temps réel avec focus D&G
    stats = db.get_dashboard_stats()
    dg_stats = db.get_dg_enhanced_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{dg_stats['revenus_today']:,.0f}$</div>
            <div class="metric-label">💰 Revenus Aujourd'hui</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{dg_stats['premium_active']}</div>
            <div class="metric-label">🔥 Postes Premium Actifs (≥130$)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{dg_stats['avg_efficiency']:.0f}$/h</div>
            <div class="metric-label">⚡ Efficacité Moyenne</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{dg_stats['pct_high_value']:.1f}%</div>
            <div class="metric-label">🎯 % Postes Haute Valeur (≥120$)</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Graphiques spécialisés D&G
    col1, col2 = st.columns(2)
    
    with col1:
        # Répartition revenus par catégorie D&G
        conn = sqlite3.connect(db.db_path)
        today = date.today()
        
        revenue_by_category_query = """
            SELECT 
                pt.task_category,
                SUM((((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60) 
                    * COALESCE(eta.hourly_rate_override, pt.hourly_rate)) as revenue
            FROM time_entries te
            INNER JOIN project_tasks pt ON te.task_id = pt.id
            LEFT JOIN employee_task_assignments eta ON te.employee_id = eta.employee_id 
                AND te.project_id = eta.project_id AND te.task_id = eta.task_id
            WHERE DATE(te.punch_in) = ? AND te.punch_out IS NOT NULL
            GROUP BY pt.task_category
            HAVING revenue > 0
            ORDER BY revenue DESC
        """
        
        revenue_cat_df = pd.read_sql_query(revenue_by_category_query, conn, params=(today,))
        
        if not revenue_cat_df.empty:
            fig_revenue = px.pie(
                revenue_cat_df,
                values='revenue',
                names='task_category',
                title="💰 Revenus par Catégorie D&G (Aujourd'hui)",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_revenue.update_traces(textinfo='label+percent', textfont_size=12)
            fig_revenue.update_layout(height=400)
            st.plotly_chart(fig_revenue, use_container_width=True)
        else:
            st.info("Aucun revenu catégorisé aujourd'hui")
    
    with col2:
        # Utilisation des postes par niveau de taux D&G
        premium_usage_query = """
            SELECT 
                CASE 
                    WHEN pt.hourly_rate >= 130 THEN 'Premium (≥130$)'
                    WHEN pt.hourly_rate >= 100 THEN 'Élevé (100-129$)'
                    WHEN pt.hourly_rate >= 90 THEN 'Standard (90-99$)'
                    ELSE 'Administratif (<90$)'
                END as tier,
                COUNT(*) as sessions,
                SUM(((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60) as hours
            FROM time_entries te
            INNER JOIN project_tasks pt ON te.task_id = pt.id
            WHERE DATE(te.punch_in) >= ? AND te.punch_out IS NOT NULL
            GROUP BY tier
            ORDER BY 
                CASE tier
                    WHEN 'Premium (≥130$)' THEN 1
                    WHEN 'Élevé (100-129$)' THEN 2
                    WHEN 'Standard (90-99$)' THEN 3
                    ELSE 4
                END
        """
        
        start_week = today - timedelta(days=7)
        tier_df = pd.read_sql_query(premium_usage_query, conn, params=(start_week,))
        
        if not tier_df.empty:
            fig_tiers = px.bar(
                tier_df,
                x='tier',
                y='hours',
                title="⚡ Utilisation par Niveau de Taux (7 jours)",
                color='tier',
                color_discrete_map={
                    'Premium (≥130$)': '#e74c3c',
                    'Élevé (100-129$)': '#f39c12',
                    'Standard (90-99$)': '#3498db',
                    'Administratif (<90$)': '#95a5a6'
                }
            )
            fig_tiers.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_tiers, use_container_width=True)
        
        conn.close()
    
    # Alertes intelligentes pour D&G
    st.markdown("### 🚨 Alertes Opérationnelles D&G")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if dg_stats['pct_high_value'] < 40:
            st.markdown(f"""
            <div class="alert-dg warning">
                <strong>⚠️ Sous-utilisation postes haute valeur</strong><br>
                Seulement {dg_stats['pct_high_value']:.1f}% des sessions sont sur des postes ≥120$/h<br>
                <strong>Objectif D&G:</strong> >50%
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="alert-dg success">
                <strong>✅ Bonne utilisation postes haute valeur</strong><br>
                {dg_stats['pct_high_value']:.1f}% des sessions sur postes premium<br>
                <strong>Continue ainsi!</strong>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        if dg_stats['avg_efficiency'] < 100:
            st.markdown(f"""
            <div class="alert-dg error">
                <strong>🔴 Efficacité sous la moyenne D&G</strong><br>
                Efficacité actuelle: {dg_stats['avg_efficiency']:.0f}$/h<br>
                <strong>Objectif D&G:</strong> >100$/h
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="alert-dg success">
                <strong>✅ Excellente efficacité</strong><br>
                {dg_stats['avg_efficiency']:.0f}$/h dépasse l'objectif D&G<br>
                <strong>Performance optimale!</strong>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        if dg_stats['revenus_today'] < 5000:
            st.markdown(f"""
            <div class="alert-dg info">
                <strong>📊 Revenus journée normale</strong><br>
                {dg_stats['revenus_today']:,.0f}$ aujourd'hui<br>
                <strong>Objectif D&G:</strong> 8000$/jour
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="alert-dg success">
                <strong>🎉 Excellente journée revenus!</strong><br>
                {dg_stats['revenus_today']:,.0f}$ aujourd'hui<br>
                <strong>Dépasse l'objectif D&G!</strong>
            </div>
            """, unsafe_allow_html=True)
    
    # Analytics en temps réel des postes premium
    st.markdown("### 🔥 Suivi Postes Premium D&G (≥130$/h)")
    
    premium_details_query = """
        SELECT 
            pt.task_name,
            pt.hourly_rate,
            COUNT(CASE WHEN te.punch_out IS NULL THEN 1 END) as actifs_maintenant,
            COUNT(*) as sessions_total,
            SUM(CASE 
                WHEN te.punch_out IS NOT NULL THEN
                    ((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60
                ELSE 0
            END) as heures_terminees,
            SUM(CASE 
                WHEN te.punch_out IS NOT NULL THEN
                    (((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60) * pt.hourly_rate
                ELSE 0
            END) as revenus_generes
        FROM project_tasks pt
        LEFT JOIN time_entries te ON pt.id = te.task_id AND DATE(te.punch_in) = ?
        WHERE pt.hourly_rate >= 130 AND pt.is_active = 1
        GROUP BY pt.id
        ORDER BY pt.hourly_rate DESC, revenus_generes DESC
    """
    
    conn = sqlite3.connect(db.db_path)
    premium_df = pd.read_sql_query(premium_details_query, conn, params=(today,))
    conn.close()
    
    if not premium_df.empty:
        # Formater pour affichage
        premium_display = premium_df.copy()
        premium_display['Poste'] = premium_display['task_name']
        premium_display['Taux'] = premium_display['hourly_rate'].apply(lambda x: f"🔥 {x:.0f}$")
        premium_display['Actifs'] = premium_display['actifs_maintenant']
        premium_display['Sessions'] = premium_display['sessions_total']
        premium_display['Heures'] = premium_display['heures_terminees'].apply(lambda x: f"{x:.1f}h")
        premium_display['Revenus'] = premium_display['revenus_generes'].apply(lambda x: f"{x:,.0f}$")
        
        # Afficher le tableau des postes premium
        st.dataframe(
            premium_display[['Poste', 'Taux', 'Actifs', 'Sessions', 'Heures', 'Revenus']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Aucune utilisation des postes premium aujourd'hui")

# ================================
# INTERFACE ADMINISTRATEUR ENRICHIE AVEC D&G
# ================================

def show_admin_interface():
    """Interface administrateur complète avec gestion D&G"""
    
    user_info = st.session_state.user_info
    db = get_database()
    
    st.markdown(f"""
    <div class="main-header">
        <h1>👨‍💼 Tableau de Bord Administrateur</h1>
        <p>Bienvenue {user_info['name']} - Gestion complète D&G avec 34 postes de travail</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs pour organiser l'interface admin
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Dashboard D&G", "👥 Employés", "📋 Projets", "🔧 Tâches", "🎯 Assignations", "📈 Rapports"])
    
    with tab1:
        show_dg_enhanced_dashboard(db)
    
    with tab2:
        show_employee_management_crud(db)
    
    with tab3:
        show_project_management_crud(db)
    
    with tab4:
        show_task_management_crud(db)
    
    with tab5:
        show_assignment_management(db)
    
    with tab6:
        show_reports_management_enhanced(db)

def show_assignment_management(db):
    """Interface de gestion des assignations"""
    
    st.markdown("### 🎯 Gestion des Assignations")
    
    assignment_type = st.radio(
        "Type d'assignation", 
        ["📋 Tâches → Projets", "👥 Employés → Tâches"],
        horizontal=True
    )
    
    if assignment_type == "📋 Tâches → Projets":
        show_project_task_assignments(db)
    else:
        show_employee_task_assignments(db)

def show_project_task_assignments(db):
    """Interface pour assigner tâches aux projets"""
    
    st.markdown("#### 📋 Assignation Tâches → Projets")
    
    # Sélection du projet
    projects = db.get_all_projects()
    active_projects = [p for p in projects if p[5]]  # is_active = True
    
    if not active_projects:
        st.warning("Aucun projet actif disponible")
        return
    
    project_options = {f"{p[2]} ({p[1]})": p[0] for p in active_projects}
    selected_project_display = st.selectbox(
        "📋 Sélectionner un projet", 
        options=list(project_options.keys())
    )
    
    project_id = project_options[selected_project_display]
    project_name = next(p[2] for p in active_projects if p[0] == project_id)
    
    st.markdown(f"##### Gestion des tâches pour: **{project_name}**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔧 Toutes les tâches disponibles**")
        
        # Récupérer toutes les tâches
        all_tasks = db.get_all_global_tasks()
        
        # Grouper par catégorie
        task_categories = {}
        for task in all_tasks:
            category = task[1] or "Général"
            if category not in task_categories:
                task_categories[category] = []
            task_categories[category].append(task)
        
        # Interface par catégorie
        for category, category_tasks in task_categories.items():
            with st.expander(f"🔧 {category} ({len(category_tasks)} tâches)"):
                for task in category_tasks:
                    task_name, task_category, task_id, task_project_id = task
                    
                    # Vérifier si déjà assignée
                    is_assigned = db.is_task_assigned_to_project(project_id, task_id)
                    
                    col_check, col_action = st.columns([3, 1])
                    
                    with col_check:
                        assign_checked = st.checkbox(
                            f"{task_name}",
                            value=is_assigned,
                            key=f"assign_task_{task_id}_{project_id}"
                        )
                    
                    with col_action:
                        if assign_checked and not is_assigned:
                            if st.button("✅", key=f"add_{task_id}_{project_id}", help="Assigner"):
                                success, message = db.assign_task_to_project(project_id, task_id)
                                if success:
                                    st.success("✅ Assignée")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {message}")
                        
                        elif not assign_checked and is_assigned:
                            if st.button("❌", key=f"remove_{task_id}_{project_id}", help="Désassigner"):
                                success, message = db.unassign_task_from_project(project_id, task_id)
                                if success:
                                    st.success("✅ Désassignée")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {message}")
    
    with col2:
        st.markdown("**✅ Tâches assignées à ce projet**")
        
        assigned_tasks = db.get_project_assigned_tasks(project_id)
        
        if assigned_tasks:
            st.info(f"📊 **{len(assigned_tasks)}** tâches assignées")
            
            for task in assigned_tasks:
                task_id, task_name, task_category, hourly_rate, is_enabled = task
                
                rate_icon = get_rate_indicator(hourly_rate)
                
                st.markdown(f"""
                <div class="assignment-card">
                    <strong>{task_name}</strong><br>
                    <small>Catégorie: {task_category} | Taux: {rate_icon} {hourly_rate:.0f}$ CAD</small>
                    <div class="assignment-indicator">Assignée</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune tâche assignée à ce projet")

def show_employee_task_assignments(db):
    """Interface pour assigner employés aux tâches"""
    
    st.markdown("#### 👥 Assignation Employés → Tâches")
    
    # Sélection du projet et de la tâche
    col1, col2 = st.columns(2)
    
    with col1:
        projects = db.get_all_projects()
        active_projects = [p for p in projects if p[5]]
        
        if not active_projects:
            st.warning("Aucun projet actif disponible")
            return
        
        project_options = {f"{p[2]} ({p[1]})": p[0] for p in active_projects}
        selected_project_display = st.selectbox(
            "📋 Sélectionner un projet", 
            options=list(project_options.keys()),
            key="emp_assign_project"
        )
        
        project_id = project_options[selected_project_display]
    
    with col2:
        # Récupérer les tâches assignées à ce projet
        assigned_tasks = db.get_project_assigned_tasks(project_id)
        
        if not assigned_tasks:
            st.warning("Aucune tâche assignée à ce projet")
            return
        
        task_options = {f"{t[1]} ({get_rate_indicator(t[3])} {t[3]:.0f}$)": t[0] for t in assigned_tasks}
        selected_task_display = st.selectbox(
            "🔧 Sélectionner une tâche", 
            options=list(task_options.keys()),
            key="emp_assign_task"
        )
        
        task_id = task_options[selected_task_display]
    
    # Interface d'assignation des employés
    st.markdown(f"##### Assignation des employés à la tâche sélectionnée")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**👥 Tous les employés**")
        
        all_employees = db.get_all_employees()
        active_employees = [e for e in all_employees if e[4]]  # is_active = True
        
        for emp in active_employees:
            emp_id, emp_code, emp_name, emp_role, is_active, created_at = emp
            
            # Vérifier si déjà assigné
            is_authorized = db.is_employee_authorized_for_task(emp_id, project_id, task_id)
            
            with st.expander(f"👤 {emp_name} ({emp_code})", expanded=is_authorized):
                col_check, col_skill, col_rate = st.columns([2, 2, 2])
                
                with col_check:
                    authorize_checked = st.checkbox(
                        "Autoriser",
                        value=is_authorized,
                        key=f"auth_emp_{emp_id}_{task_id}"
                    )
                
                if authorize_checked:
                    with col_skill:
                        skill_level = st.selectbox(
                            "Niveau de compétence",
                            ["débutant", "intermédiaire", "avancé", "expert"],
                            index=1,
                            key=f"skill_emp_{emp_id}_{task_id}"
                        )
                    
                    with col_rate:
                        # Récupérer le taux de base de la tâche
                        task_info = next((t for t in assigned_tasks if t[0] == task_id), None)
                        base_rate = task_info[3] if task_info else 95.0
                        
                        rate_override = st.number_input(
                            "Taux spécial (CAD)",
                            min_value=0.0,
                            value=float(base_rate),
                            step=5.0,
                            key=f"rate_emp_{emp_id}_{task_id}"
                        )
                    
                    if st.button("💾 Sauvegarder", key=f"save_emp_{emp_id}_{task_id}"):
                        if authorize_checked and not is_authorized:
                            success, message = db.assign_employee_to_task(
                                emp_id, project_id, task_id, skill_level, rate_override
                            )
                        elif authorize_checked and is_authorized:
                            success, message = db.assign_employee_to_task(
                                emp_id, project_id, task_id, skill_level, rate_override
                            )
                        else:
                            success, message = db.unassign_employee_from_task(emp_id, project_id, task_id)
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                
                elif is_authorized:
                    if st.button("❌ Désautoriser", key=f"unauth_emp_{emp_id}_{task_id}"):
                        success, message = db.unassign_employee_from_task(emp_id, project_id, task_id)
                        if success:
                            st.success(f"✅ {message}")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
    
    with col2:
        st.markdown("**✅ Employés autorisés pour cette tâche**")
        
        assigned_employees = db.get_task_assigned_employees(project_id, task_id)
        
        if assigned_employees:
            st.info(f"📊 **{len(assigned_employees)}** employés autorisés")
            
            for emp in assigned_employees:
                emp_id, emp_name, emp_code, skill_level, rate_override, is_authorized = emp
                
                if is_authorized:
                    skill_class = get_skill_badge_class(skill_level)
                    rate_icon = get_rate_indicator(rate_override)
                    
                    st.markdown(f"""
                    <div class="assignment-card">
                        <strong>{emp_name}</strong> ({emp_code})<br>
                        <small>Taux: {rate_icon} {rate_override:.0f}$ CAD</small><br>
                        <span class="skill-badge {skill_class}">{skill_level}</span>
                        <div class="assignment-indicator">Autorisé</div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Aucun employé autorisé pour cette tâche")
            st.warning("⚠️ Les employés ne pourront pas sélectionner cette tâche lors du pointage")

def show_employee_management_crud(db):
    """Gestion CRUD complète des employés"""
    
    st.markdown("### 👥 Gestion des Employés")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### ➕ Ajouter un employé")
        
        with st.form("add_employee_form"):
            emp_code = st.text_input("Code Employé *", placeholder="EMP001")
            emp_name = st.text_input("Nom Complet *", placeholder="Jean Dupont")
            emp_password = st.text_input("Mot de passe *", type="password", value="", placeholder="Mot de passe initial")
            emp_role = st.selectbox("Rôle", ["employee", "admin"])
            
            if st.form_submit_button("👤 Créer l'employé"):
                if emp_code and emp_name and emp_password:
                    success, message = db.add_employee(emp_code.upper(), emp_name, emp_password, emp_role)
                    if success:
                        st.success(f"✅ {message}")
                        st.info(f"🔑 Code de connexion: **{emp_code.upper()}**")
                        st.info("🎯 Employé automatiquement assigné à tous les postes D&G")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.warning("⚠️ Tous les champs sont obligatoires")
    
    with col2:
        st.markdown("#### 📋 Liste des employés")
        
        try:
            employees = db.get_all_employees()
            if employees and len(employees) > 0:
                for emp in employees:
                    if len(emp) >= 6:  # Vérifier que nous avons tous les champs
                        emp_id, emp_code, emp_name, emp_role, is_active, created_at = emp
                        
                        with st.container():
                            col_info, col_status, col_assign_btn, col_edit_btn, col_delete_btn = st.columns([3, 1, 1, 1, 1])
                            
                            with col_info:
                                st.write(f"**{emp_name}** ({emp_code})")
                                st.caption(f"Rôle: {emp_role} | Créé: {created_at[:10]}")
                            
                            with col_status:
                                if is_active:
                                    st.markdown('<span class="status-active">✅ Actif</span>', unsafe_allow_html=True)
                                else:
                                    st.markdown('<span class="status-inactive">❌ Inactif</span>', unsafe_allow_html=True)
                            
                            with col_assign_btn:
                                if st.button("👥", key=f"assign_emp_{emp_id}", help="Assignations"):
                                    st.session_state.view_employee_assignments = emp_id
                                    st.rerun()
                            
                            with col_edit_btn:
                                if st.button("✏️", key=f"edit_emp_{emp_id}", help="Modifier"):
                                    st.session_state.edit_employee_id = emp_id
                                    st.rerun()
                            
                            with col_delete_btn:
                                if st.button("🗑️", key=f"delete_emp_{emp_id}", help="Supprimer"):
                                    st.session_state.delete_employee_id = emp_id
                                    st.rerun()
                            
                            st.markdown("---")
            else:
                st.info("Aucun employé trouvé")
        except Exception as e:
            st.error(f"Erreur lors du chargement des employés: {str(e)}")
            st.info("Essayez de rafraîchir la page.")
    
    # Gestion des modals d'édition, suppression et assignations
    if 'edit_employee_id' in st.session_state:
        show_edit_employee_form(db, st.session_state.edit_employee_id)
    
    if 'delete_employee_id' in st.session_state:
        show_delete_employee_form(db, st.session_state.delete_employee_id)
    
    if 'view_employee_assignments' in st.session_state:
        show_employee_assignments_summary(db, st.session_state.view_employee_assignments)

def show_employee_assignments_summary(db, employee_id):
    """Affiche un résumé des assignations d'un employé"""
    
    employee = db.get_employee_by_id(employee_id)
    if not employee:
        st.error("Employé introuvable")
        if st.button("❌ Fermer"):
            del st.session_state.view_employee_assignments
            st.rerun()
        return
    
    emp_id, emp_code, emp_name, emp_role, is_active = employee
    
    st.markdown(f"""
    <div class="assignment-card">
        <h4>👥 Assignations de: {emp_name} ({emp_code})</h4>
    </div>
    """, unsafe_allow_html=True)
    
    # Récupérer toutes les assignations de l'employé
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            p.project_name, p.project_code,
            pt.task_name, pt.task_category,
            eta.skill_level, eta.hourly_rate_override,
            eta.is_authorized
        FROM employee_task_assignments eta
        INNER JOIN projects p ON eta.project_id = p.id
        INNER JOIN project_tasks pt ON eta.task_id = pt.id
        WHERE eta.employee_id = ? AND eta.is_authorized = 1
        ORDER BY p.project_name, pt.task_category, pt.task_name
    """, (employee_id,))
    
    assignments = cursor.fetchall()
    conn.close()
    
    if assignments:
        st.info(f"📊 **{len(assignments)}** assignations actives")
        
        # Grouper par projet
        projects_assignments = {}
        for assignment in assignments:
            project_name = assignment[0]
            if project_name not in projects_assignments:
                projects_assignments[project_name] = []
            projects_assignments[project_name].append(assignment)
        
        for project_name, project_assignments in projects_assignments.items():
            with st.expander(f"📋 {project_name} ({len(project_assignments)} tâches)"):
                for assignment in project_assignments:
                    project_name, project_code, task_name, task_category, skill_level, hourly_rate, is_authorized = assignment
                    
                    skill_class = get_skill_badge_class(skill_level)
                    rate_icon = get_rate_indicator(hourly_rate)
                    
                    st.markdown(f"""
                    <div class="employee-card">
                        <strong>{task_name}</strong> ({task_category})<br>
                        <small>Taux: {rate_icon} {hourly_rate:.0f}$ CAD</small><br>
                        <span class="skill-badge {skill_class}">{skill_level}</span>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.warning("Aucune assignation active pour cet employé")
        st.info("💡 Utilisez l'onglet 'Assignations' pour autoriser cet employé sur des tâches")
    
    if st.button("❌ Fermer", key="close_assignments"):
        del st.session_state.view_employee_assignments
        st.rerun()

def show_edit_employee_form(db, employee_id):
    """Formulaire de modification d'un employé"""
    
    employee = db.get_employee_by_id(employee_id)
    if not employee:
        st.error("Employé introuvable")
        if st.button("❌ Fermer"):
            del st.session_state.edit_employee_id
            st.rerun()
        return
    
    emp_id, emp_code, emp_name, emp_role, is_active = employee
    
    st.markdown(f"""
    <div class="edit-form">
        <h4>✏️ Modifier l'employé: {emp_name}</h4>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form(f"edit_employee_form_{employee_id}"):
        new_code = st.text_input("Code Employé", value=emp_code)
        new_name = st.text_input("Nom Complet", value=emp_name)
        new_password = st.text_input("Nouveau mot de passe", type="password", placeholder="Laisser vide pour conserver actuel")
        new_role = st.selectbox("Rôle", ["employee", "admin"], index=0 if emp_role == "employee" else 1)
        new_status = st.selectbox("Statut", [True, False], index=0 if is_active else 1, 
                                 format_func=lambda x: "✅ Actif" if x else "❌ Inactif")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Sauvegarder"):
                updates = {
                    'employee_code': new_code,
                    'name': new_name,
                    'role': new_role,
                    'is_active': new_status
                }
                
                if new_password:
                    updates['password'] = new_password
                
                success, message = db.update_employee(employee_id, **updates)
                if success:
                    st.success(f"✅ {message}")
                    del st.session_state.edit_employee_id
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
        
        with col2:
            if st.form_submit_button("❌ Annuler"):
                del st.session_state.edit_employee_id
                st.rerun()

def show_delete_employee_form(db, employee_id):
    """Formulaire de suppression d'un employé"""
    
    employee = db.get_employee_by_id(employee_id)
    if not employee:
        st.error("Employé introuvable")
        if st.button("❌ Fermer"):
            del st.session_state.delete_employee_id
            st.rerun()
        return
    
    emp_id, emp_code, emp_name, emp_role, is_active = employee
    
    st.markdown(f"""
    <div class="delete-form">
        <h4>🗑️ Supprimer l'employé: {emp_name}</h4>
        <p>⚠️ <strong>Attention:</strong> Cette action peut être irréversible selon l'utilisation de l'employé.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Vérifier l'utilisation
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM time_entries WHERE employee_id = ?", (employee_id,))
    usage_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM employee_task_assignments WHERE employee_id = ?", (employee_id,))
    assignments_count = cursor.fetchone()[0]
    conn.close()
    
    if usage_count > 0:
        st.warning(f"⚠️ Cet employé a {usage_count} pointage(s) enregistré(s). Il sera désactivé au lieu d'être supprimé.")
    
    if assignments_count > 0:
        st.info(f"ℹ️ Cet employé a {assignments_count} assignation(s) de tâches.")
    
    if usage_count == 0 and assignments_count == 0:
        st.info("ℹ️ Cet employé n'a aucun pointage ni assignation et peut être supprimé définitivement.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"🗑️ Confirmer la suppression", key=f"confirm_delete_emp_{employee_id}"):
            success, message = db.delete_employee(employee_id)
            if success:
                st.success(f"✅ {message}")
                del st.session_state.delete_employee_id
                time.sleep(2)
                st.rerun()
            else:
                st.error(f"❌ {message}")
    
    with col2:
        if st.button("❌ Annuler", key=f"cancel_delete_emp_{employee_id}"):
            del st.session_state.delete_employee_id
            st.rerun()

def show_project_management_crud(db):
    """Gestion CRUD complète des projets"""
    
    st.markdown("### 📋 Gestion des Projets")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### ➕ Ajouter un projet")
        
        with st.form("add_project_form"):
            proj_code = st.text_input("Code Projet *", placeholder="PROJ001")
            proj_name = st.text_input("Nom Projet *", placeholder="Fabrication portes")
            client_name = st.text_input("Client", placeholder="Nom du client")
            requires_task = st.checkbox("Sélection de poste obligatoire", value=True, 
                                      help="Cochez si ce projet nécessite obligatoirement la sélection d'un poste de travail")
            
            if st.form_submit_button("📋 Créer le projet"):
                if proj_code and proj_name:
                    success, message = db.add_project(proj_code.upper(), proj_name, client_name, requires_task)
                    if success:
                        st.success(f"✅ {message}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.warning("⚠️ Code et nom du projet sont obligatoires")
    
    with col2:
        st.markdown("#### 📋 Liste des projets")
        
        try:
            projects = db.get_all_projects()
            if projects and len(projects) > 0:
                for proj in projects:
                    if len(proj) >= 7:  # Vérifier que nous avons tous les champs
                        proj_id, proj_code, proj_name, client_name, requires_task, is_active, created_at = proj
                        
                        with st.container():
                            col_info, col_status, col_assign_btn, col_edit_btn, col_delete_btn = st.columns([3, 1, 1, 1, 1])
                            
                            with col_info:
                                st.write(f"**{proj_name}** ({proj_code})")
                                if client_name:
                                    st.caption(f"Client: {client_name}")
                                st.caption(f"Poste obligatoire: {'✅ Oui' if requires_task else '❌ Non'}")
                            
                            with col_status:
                                if is_active:
                                    st.markdown('<span class="status-active">✅ Actif</span>', unsafe_allow_html=True)
                                else:
                                    st.markdown('<span class="status-inactive">❌ Inactif</span>', unsafe_allow_html=True)
                            
                            with col_assign_btn:
                                if st.button("🎯", key=f"assign_proj_{proj_id}", help="Assignations"):
                                    st.session_state.view_project_assignments = proj_id
                                    st.rerun()
                            
                            with col_edit_btn:
                                if st.button("✏️", key=f"edit_proj_{proj_id}", help="Modifier"):
                                    st.session_state.edit_project_id = proj_id
                                    st.rerun()
                            
                            with col_delete_btn:
                                if st.button("🗑️", key=f"delete_proj_{proj_id}", help="Supprimer"):
                                    st.session_state.delete_project_id = proj_id
                                    st.rerun()
                            
                            st.markdown("---")
            else:
                st.info("Aucun projet trouvé")
        except Exception as e:
            st.error(f"Erreur lors du chargement des projets: {str(e)}")
            st.info("Essayez de rafraîchir la page.")
    
    # Gestion des modals d'édition, suppression et assignations
    if 'edit_project_id' in st.session_state:
        show_edit_project_form(db, st.session_state.edit_project_id)
    
    if 'delete_project_id' in st.session_state:
        show_delete_project_form(db, st.session_state.delete_project_id)
    
    if 'view_project_assignments' in st.session_state:
        show_project_assignments_summary(db, st.session_state.view_project_assignments)

def show_project_assignments_summary(db, project_id):
    """Affiche un résumé des assignations d'un projet"""
    
    project = db.get_project_by_id(project_id)
    if not project:
        st.error("Projet introuvable")
        if st.button("❌ Fermer"):
            del st.session_state.view_project_assignments
            st.rerun()
        return
    
    proj_id, proj_code, proj_name, client_name, requires_task, is_active = project
    
    st.markdown(f"""
    <div class="assignment-card">
        <h4>🎯 Assignations du projet: {proj_name} ({proj_code})</h4>
        <p>Client: {client_name or 'N/A'}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Récupérer les tâches assignées au projet
    assigned_tasks = db.get_project_assigned_tasks(project_id)
    
    if assigned_tasks:
        st.info(f"📊 **{len(assigned_tasks)}** tâches assignées à ce projet")
        
        # Pour chaque tâche, afficher les employés autorisés
        for task in assigned_tasks:
            task_id, task_name, task_category, hourly_rate, is_enabled = task
            
            rate_icon = get_rate_indicator(hourly_rate)
            
            with st.expander(f"🔧 {task_name} ({task_category}) - {rate_icon} {hourly_rate:.0f}$"):
                # Récupérer les employés autorisés pour cette tâche
                assigned_employees = db.get_task_assigned_employees(project_id, task_id)
                
                if assigned_employees:
                    st.success(f"👥 {len(assigned_employees)} employé(s) autorisé(s)")
                    
                    cols = st.columns(min(len(assigned_employees), 3))
                    for i, emp in enumerate(assigned_employees):
                        emp_id, emp_name, emp_code, skill_level, rate_override, is_authorized = emp
                        
                        if is_authorized:
                            skill_class = get_skill_badge_class(skill_level)
                            emp_rate_icon = get_rate_indicator(rate_override)
                            
                            with cols[i % 3]:
                                st.markdown(f"""
                                <div class="employee-card">
                                    <strong>{emp_name}</strong><br>
                                    <small>({emp_code})</small><br>
                                    <span class="skill-badge {skill_class}">{skill_level}</span><br>
                                    <small>{emp_rate_icon} {rate_override:.0f}$ CAD/h</small>
                                </div>
                                """, unsafe_allow_html=True)
                else:
                    st.warning("❌ Aucun employé autorisé pour cette tâche")
                    st.info("💡 Utilisez l'onglet 'Assignations' pour autoriser des employés")
    else:
        st.warning("Aucune tâche assignée à ce projet")
        st.info("💡 Utilisez l'onglet 'Assignations' pour assigner des tâches")
    
    if st.button("❌ Fermer", key="close_project_assignments"):
        del st.session_state.view_project_assignments
        st.rerun()

def show_edit_project_form(db, project_id):
    """Formulaire de modification d'un projet"""
    
    project = db.get_project_by_id(project_id)
    if not project:
        st.error("Projet introuvable")
        if st.button("❌ Fermer"):
            del st.session_state.edit_project_id
            st.rerun()
        return
    
    proj_id, proj_code, proj_name, client_name, requires_task, is_active = project
    
    st.markdown(f"""
    <div class="edit-form">
        <h4>✏️ Modifier le projet: {proj_name}</h4>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form(f"edit_project_form_{project_id}"):
        new_code = st.text_input("Code Projet", value=proj_code)
        new_name = st.text_input("Nom Projet", value=proj_name)
        new_client = st.text_input("Client", value=client_name or "")
        new_requires_task = st.checkbox("Sélection de poste obligatoire", value=requires_task)
        new_status = st.selectbox("Statut", [True, False], index=0 if is_active else 1,
                                 format_func=lambda x: "✅ Actif" if x else "❌ Inactif")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Sauvegarder"):
                updates = {
                    'project_code': new_code,
                    'project_name': new_name,
                    'client_name': new_client,
                    'requires_task_selection': new_requires_task,
                    'is_active': new_status
                }
                
                success, message = db.update_project(project_id, **updates)
                if success:
                    st.success(f"✅ {message}")
                    del st.session_state.edit_project_id
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
        
        with col2:
            if st.form_submit_button("❌ Annuler"):
                del st.session_state.edit_project_id
                st.rerun()

def show_delete_project_form(db, project_id):
    """Formulaire de suppression d'un projet"""
    
    project = db.get_project_by_id(project_id)
    if not project:
        st.error("Projet introuvable")
        if st.button("❌ Fermer"):
            del st.session_state.delete_project_id
            st.rerun()
        return
    
    proj_id, proj_code, proj_name, client_name, requires_task, is_active = project
    
    st.markdown(f"""
    <div class="delete-form">
        <h4>🗑️ Supprimer le projet: {proj_name}</h4>
        <p>⚠️ <strong>Attention:</strong> Cette action peut être irréversible selon l'utilisation du projet.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Vérifier l'utilisation
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM time_entries WHERE project_id = ?", (project_id,))
    time_entries_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM project_tasks WHERE project_id = ?", (project_id,))
    tasks_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM project_task_assignments WHERE project_id = ?", (project_id,))
    assignments_count = cursor.fetchone()[0]
    conn.close()
    
    if time_entries_count > 0 or tasks_count > 0:
        st.warning(f"⚠️ Ce projet a {time_entries_count} pointage(s) et {tasks_count} tâche(s). Il sera désactivé au lieu d'être supprimé.")
    
    if assignments_count > 0:
        st.info(f"ℹ️ Ce projet a {assignments_count} assignation(s) de tâches.")
    
    if time_entries_count == 0 and tasks_count == 0 and assignments_count == 0:
        st.info("ℹ️ Ce projet n'a aucun pointage, tâche ni assignation et peut être supprimé définitivement.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"🗑️ Confirmer la suppression", key=f"confirm_delete_proj_{project_id}"):
            success, message = db.delete_project(project_id)
            if success:
                st.success(f"✅ {message}")
                del st.session_state.delete_project_id
                time.sleep(2)
                st.rerun()
            else:
                st.error(f"❌ {message}")
    
    with col2:
        if st.button("❌ Annuler", key=f"cancel_delete_proj_{project_id}"):
            del st.session_state.delete_project_id
            st.rerun()

def show_task_management_crud(db):
    """Gestion CRUD complète des tâches"""
    
    st.markdown("### 🔧 Gestion des Postes de Travail")
    
    # Sélection du projet
    projects = db.get_all_projects()
    if not projects:
        st.warning("Aucun projet disponible. Créez d'abord un projet.")
        return
    
    active_projects = [p for p in projects if p[5]]  # is_active = True
    project_options = {f"{p[2]} ({p[3] or 'Pas de client'})": p for p in active_projects}
    
    if not project_options:
        st.warning("Aucun projet actif. Activez d'abord un projet.")
        return
    
    selected_project_display = st.selectbox(
        "📋 Sélectionner un projet", 
        options=list(project_options.keys())
    )
    
    selected_project = project_options[selected_project_display]
    project_id = selected_project[0]
    project_name = selected_project[2]
    
    st.markdown(f"#### Postes de travail pour: **{project_name}**")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("##### ➕ Ajouter un poste")
        
        with st.form(f"add_task_form_{project_id}"):
            task_code = st.text_input("Code Poste *", placeholder="ROBOT")
            task_name = st.text_input("Nom Poste *", placeholder="Robot soudeur")
            task_category = st.selectbox("Catégorie", [
                "Soudage", "Découpe et Perçage", "Formage et Assemblage", "Finition", 
                "Préparation et Programmation", "Manutention et Cisaillage", "Contrôle Qualité", "Expédition"
            ])
            hourly_rate = st.number_input("Taux Horaire (CAD)", min_value=0.0, value=95.0, step=5.0)
            description = st.text_area("Description", placeholder="Description détaillée du poste de travail...")
            
            if st.form_submit_button("🔧 Créer le Poste"):
                if task_code and task_name:
                    success, message = db.add_task(project_id, task_code.upper(), task_name, task_category, hourly_rate, description)
                    if success:
                        st.success(f"✅ {message}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.warning("⚠️ Code et nom du poste sont obligatoires")
    
    with col2:
        st.markdown("##### 📋 Postes existants")
        
        tasks = db.get_all_project_tasks(project_id)
        if tasks:
            # Grouper par catégorie
            task_categories = {}
            for task in tasks:
                category = task[3] or "Général"
                if category not in task_categories:
                    task_categories[category] = []
                task_categories[category].append(task)
            
            for category, category_tasks in task_categories.items():
                with st.expander(f"🔧 {category} ({len(category_tasks)} postes)"):
                    for task in category_tasks:
                        task_id, task_code, task_name, task_category, hourly_rate, description, is_active = task
                        
                        rate_icon = get_rate_indicator(hourly_rate)
                        rate_class = get_rate_class(hourly_rate)
                        
                        col_task1, col_task2, col_assign_task, col_edit_task, col_delete_task = st.columns([2, 1, 1, 1, 1])
                        
                        with col_task1:
                            st.write(f"**{task_name}** ({task_code})")
                            if description:
                                st.caption(description)
                            if not is_active:
                                st.markdown('<span class="status-inactive">❌ Inactif</span>', unsafe_allow_html=True)
                        
                        with col_task2:
                            st.markdown(f'<div class="{rate_class}">{rate_icon} {hourly_rate:.0f}$ CAD</div>', unsafe_allow_html=True)
                        
                        with col_assign_task:
                            if st.button("👥", key=f"assign_task_{task_id}", help="Assignations"):
                                st.session_state.view_task_assignments = task_id
                                st.rerun()
                        
                        with col_edit_task:
                            if st.button("✏️", key=f"edit_task_{task_id}", help="Modifier"):
                                st.session_state.edit_task_id = task_id
                                st.rerun()
                        
                        with col_delete_task:
                            if st.button("🗑️", key=f"delete_task_{task_id}", help="Supprimer"):
                                st.session_state.delete_task_id = task_id
                                st.rerun()
        else:
            st.info("Aucun poste défini pour ce projet")
    
    # Gestion des modals d'édition, suppression et assignations des tâches
    if 'edit_task_id' in st.session_state:
        show_edit_task_form(db, st.session_state.edit_task_id)
    
    if 'delete_task_id' in st.session_state:
        show_delete_task_form(db, st.session_state.delete_task_id)
    
    if 'view_task_assignments' in st.session_state:
        show_task_assignments_summary(db, st.session_state.view_task_assignments)

def show_task_assignments_summary(db, task_id):
    """Affiche un résumé des assignations d'une tâche"""
    
    task = db.get_task_by_id(task_id)
    if not task:
        st.error("Tâche introuvable")
        if st.button("❌ Fermer"):
            del st.session_state.view_task_assignments
            st.rerun()
        return
    
    task_id_val, project_id, task_code, task_name, task_category, hourly_rate, description, is_active = task
    
    # Récupérer le nom du projet
    project = db.get_project_by_id(project_id)
    project_name = project[2] if project else "Projet inconnu"
    
    rate_icon = get_rate_indicator(hourly_rate)
    
    st.markdown(f"""
    <div class="assignment-card">
        <h4>🎯 Assignations du poste: {task_name} ({task_code})</h4>
        <p>Projet: {project_name} | Catégorie: {task_category} | Taux: {rate_icon} {hourly_rate:.0f}$ CAD</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Vérifier si la tâche est assignée au projet
    is_assigned_to_project = db.is_task_assigned_to_project(project_id, task_id)
    
    if not is_assigned_to_project:
        st.warning("⚠️ Ce poste n'est pas assigné au projet")
        st.info("💡 Utilisez l'onglet 'Assignations' → 'Tâches → Projets' pour l'assigner d'abord")
        
        if st.button("❌ Fermer", key="close_task_assignments_not_assigned"):
            del st.session_state.view_task_assignments
            st.rerun()
        return
    
    # Récupérer les employés autorisés pour cette tâche
    assigned_employees = db.get_task_assigned_employees(project_id, task_id)
    
    if assigned_employees:
        st.info(f"📊 **{len(assigned_employees)}** employé(s) autorisé(s) pour ce poste")
        
        # Afficher les employés par niveau de compétence
        skill_groups = {}
        for emp in assigned_employees:
            emp_id, emp_name, emp_code, skill_level, rate_override, is_authorized = emp
            if is_authorized:
                if skill_level not in skill_groups:
                    skill_groups[skill_level] = []
                skill_groups[skill_level].append(emp)
        
        # Ordre des niveaux
        skill_order = ['expert', 'avancé', 'intermédiaire', 'débutant']
        
        for skill in skill_order:
            if skill in skill_groups:
                employees = skill_groups[skill]
                skill_class = get_skill_badge_class(skill)
                
                with st.expander(f"{skill.capitalize()} ({len(employees)} employé(s))", expanded=True):
                    cols = st.columns(min(len(employees), 3))
                    
                    for i, emp in enumerate(employees):
                        emp_id, emp_name, emp_code, skill_level, rate_override, is_authorized = emp
                        
                        emp_rate_icon = get_rate_indicator(rate_override)
                        
                        with cols[i % 3]:
                            st.markdown(f"""
                            <div class="employee-card">
                                <strong>{emp_name}</strong><br>
                                <small>({emp_code})</small><br>
                                <span class="skill-badge {skill_class}">{skill_level}</span><br>
                                <small>{emp_rate_icon} {rate_override:.0f}$ CAD/h</small>
                            </div>
                            """, unsafe_allow_html=True)
    else:
        st.warning("❌ Aucun employé autorisé pour ce poste")
        st.info("💡 Utilisez l'onglet 'Assignations' → 'Employés → Tâches' pour autoriser des employés")
    
    if st.button("❌ Fermer", key="close_task_assignments"):
        del st.session_state.view_task_assignments
        st.rerun()

def show_edit_task_form(db, task_id):
    """Formulaire de modification d'une tâche"""
    
    task = db.get_task_by_id(task_id)
    if not task:
        st.error("Tâche introuvable")
        if st.button("❌ Fermer"):
            del st.session_state.edit_task_id
            st.rerun()
        return
    
    task_id_val, project_id, task_code, task_name, task_category, hourly_rate, description, is_active = task
    
    st.markdown(f"""
    <div class="edit-form">
        <h4>✏️ Modifier le poste: {task_name}</h4>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form(f"edit_task_form_{task_id}"):
        new_code = st.text_input("Code Poste", value=task_code)
        new_name = st.text_input("Nom Poste", value=task_name)
        new_category = st.selectbox("Catégorie", [
            "Soudage", "Découpe et Perçage", "Formage et Assemblage", "Finition", 
            "Préparation et Programmation", "Manutention et Cisaillage", "Contrôle Qualité", "Expédition"
        ], index=[
            "Soudage", "Découpe et Perçage", "Formage et Assemblage", "Finition", 
            "Préparation et Programmation", "Manutention et Cisaillage", "Contrôle Qualité", "Expédition"
        ].index(task_category) if task_category in [
            "Soudage", "Découpe et Perçage", "Formage et Assemblage", "Finition", 
            "Préparation et Programmation", "Manutention et Cisaillage", "Contrôle Qualité", "Expédition"] else 0)
        new_rate = st.number_input("Taux Horaire (CAD)", min_value=0.0, value=float(hourly_rate), step=5.0)
        new_description = st.text_area("Description", value=description or "")
        new_status = st.selectbox("Statut", [True, False], index=0 if is_active else 1,
                                 format_func=lambda x: "✅ Actif" if x else "❌ Inactif")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Sauvegarder"):
                updates = {
                    'task_code': new_code,
                    'task_name': new_name,
                    'task_category': new_category,
                    'hourly_rate': new_rate,
                    'description': new_description,
                    'is_active': new_status
                }
                
                success, message = db.update_task(task_id, **updates)
                if success:
                    st.success(f"✅ {message}")
                    del st.session_state.edit_task_id
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
        
        with col2:
            if st.form_submit_button("❌ Annuler"):
                del st.session_state.edit_task_id
                st.rerun()

def show_delete_task_form(db, task_id):
    """Formulaire de suppression d'une tâche"""
    
    task = db.get_task_by_id(task_id)
    if not task:
        st.error("Tâche introuvable")
        if st.button("❌ Fermer"):
            del st.session_state.delete_task_id
            st.rerun()
        return
    
    task_id_val, project_id, task_code, task_name, task_category, hourly_rate, description, is_active = task
    
    st.markdown(f"""
    <div class="delete-form">
        <h4>🗑️ Supprimer le poste: {task_name}</h4>
        <p>⚠️ <strong>Attention:</strong> Cette action peut être irréversible selon l'utilisation du poste.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Vérifier l'utilisation
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM time_entries WHERE task_id = ?", (task_id,))
    usage_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM employee_task_assignments WHERE task_id = ?", (task_id,))
    assignments_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM project_task_assignments WHERE task_id = ?", (task_id,))
    project_assignments_count = cursor.fetchone()[0]
    conn.close()
    
    if usage_count > 0:
        st.warning(f"⚠️ Ce poste a été utilisé {usage_count} fois. Il sera désactivé au lieu d'être supprimé.")
    
    if assignments_count > 0:
        st.info(f"ℹ️ Ce poste a {assignments_count} assignation(s) d'employés.")
    
    if project_assignments_count > 0:
        st.info(f"ℹ️ Ce poste a {project_assignments_count} assignation(s) de projets.")
    
    if usage_count == 0 and assignments_count == 0 and project_assignments_count == 0:
        st.info("ℹ️ Ce poste n'a jamais été utilisé et peut être supprimé définitivement.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"🗑️ Confirmer la suppression", key=f"confirm_delete_task_{task_id}"):
            success, message = db.delete_task(task_id)
            if success:
                st.success(f"✅ {message}")
                del st.session_state.delete_task_id
                time.sleep(2)
                st.rerun()
            else:
                st.error(f"❌ {message}")
    
    with col2:
        if st.button("❌ Annuler", key=f"cancel_delete_task_{task_id}"):
            del st.session_state.delete_task_id
            st.rerun()

def show_reports_management_enhanced(db):
    """Gestion des rapports avec détails D&G spécialisés"""
    
    st.markdown("### 📈 Rapports et Analytics D&G")
    
    # Sélecteur de période
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("📅 Date début", value=date.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("📅 Date fin", value=date.today())
    with col3:
        report_type = st.selectbox("📊 Type de rapport", [
            "Analyse Rentabilité D&G",
            "Résumé global avec postes D&G",
            "Détail par employé avec taux effectifs", 
            "Analyse par poste/catégorie avec niveaux",
            "Rapport de paie avec taux D&G",
            "Efficacité par niveau de compétence",
            "Statut des assignations par projet",
            "Performance postes premium (≥130$)"
        ])
    
    if st.button("📊 Générer le rapport"):
        conn = sqlite3.connect(db.db_path)
        
        if report_type == "Analyse Rentabilité D&G":
            # Rapport spécialisé pour les réalités business de D&G
            query = """
                SELECT 
                    pt.task_code as 'Code',
                    pt.task_name as 'Poste de Travail',
                    pt.task_category as 'Catégorie',
                    pt.hourly_rate as 'Taux Base ($/h)',
                    COUNT(te.id) as 'Nb Sessions',
                    ROUND(SUM(CASE 
                        WHEN te.punch_out IS NOT NULL THEN
                            ((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60
                        ELSE 0
                    END), 2) as 'Heures Totales',
                    ROUND(SUM(CASE 
                        WHEN te.punch_out IS NOT NULL THEN
                            (((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60) 
                            * COALESCE(eta.hourly_rate_override, pt.hourly_rate)
                        ELSE 0
                    END), 2) as 'Revenus Générés ($)',
                    ROUND(AVG(COALESCE(eta.hourly_rate_override, pt.hourly_rate)), 2) as 'Taux Moyen Effectif ($/h)',
                    CASE 
                        WHEN pt.hourly_rate >= 130 THEN 'Premium'
                        WHEN pt.hourly_rate >= 100 THEN 'Élevé'
                        WHEN pt.hourly_rate >= 90 THEN 'Standard'
                        ELSE 'Administratif'
                    END as 'Niveau Taux'
                FROM project_tasks pt
                LEFT JOIN time_entries te ON pt.id = te.task_id
                    AND DATE(te.punch_in) BETWEEN ? AND ?
                LEFT JOIN employee_task_assignments eta ON te.employee_id = eta.employee_id 
                    AND te.project_id = eta.project_id AND te.task_id = eta.task_id
                WHERE pt.project_id = (SELECT id FROM projects WHERE project_code = 'DG-GENERAL')
                GROUP BY pt.id
                ORDER BY 'Revenus Générés ($)' DESC
            """
            
            df_report = pd.read_sql_query(query, conn, params=(start_date, end_date))
            
        elif report_type == "Performance postes premium (≥130$)":
            # Analyse des postes premium D&G
            query = """
                SELECT 
                    pt.task_name as 'Poste Premium',
                    pt.hourly_rate as 'Taux ($/h)',
                    COUNT(te.id) as 'Sessions Période',
                    COUNT(DISTINCT te.employee_id) as 'Employés Différents',
                    ROUND(SUM(CASE 
                        WHEN te.punch_out IS NOT NULL THEN
                            ((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60
                        ELSE 0
                    END), 2) as 'Heures Premium',
                    ROUND(SUM(CASE 
                        WHEN te.punch_out IS NOT NULL THEN
                            (((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60) 
                            * pt.hourly_rate
                        ELSE 0
                    END), 2) as 'Revenus Premium ($)',
                    ROUND(AVG(CASE 
                        WHEN te.punch_out IS NOT NULL THEN
                            ((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60
                        ELSE NULL
                    END), 2) as 'Durée Moy Session (h)',
                    GROUP_CONCAT(DISTINCT eta.skill_level) as 'Niveaux Utilisés'
                FROM project_tasks pt
                LEFT JOIN time_entries te ON pt.id = te.task_id
                    AND DATE(te.punch_in) BETWEEN ? AND ?
                LEFT JOIN employee_task_assignments eta ON te.employee_id = eta.employee_id 
                    AND te.project_id = eta.project_id AND te.task_id = eta.task_id
                WHERE pt.hourly_rate >= 130 AND pt.is_active = 1
                GROUP BY pt.id
                HAVING COUNT(te.id) > 0
                ORDER BY 'Revenus Premium ($)' DESC
            """
            
            df_report = pd.read_sql_query(query, conn, params=(start_date, end_date))
            
        elif report_type == "Résumé global avec postes D&G":
            # Rapport global avec répartition des postes D&G
            query = """
                SELECT 
                    e.name as 'Employé',
                    e.employee_code as 'Code',
                    COUNT(DISTINCT DATE(te.punch_in)) as 'Jours travaillés',
                    ROUND(SUM(CASE 
                        WHEN te.punch_out IS NOT NULL THEN
                            ((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60
                        ELSE 0
                    END), 2) as 'Total heures',
                    ROUND(SUM(CASE 
                        WHEN te.punch_out IS NOT NULL AND COALESCE(eta.hourly_rate_override, pt.hourly_rate) IS NOT NULL THEN
                            (((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60) * COALESCE(eta.hourly_rate_override, pt.hourly_rate)
                        ELSE 0
                    END), 2) as 'Revenus totaux (CAD)',
                    ROUND(AVG(COALESCE(eta.hourly_rate_override, pt.hourly_rate)), 2) as 'Taux moyen ($/h)',
                    COUNT(DISTINCT pt.task_category) as 'Catégories utilisées',
                    COUNT(CASE WHEN pt.hourly_rate >= 130 THEN 1 END) as 'Sessions Premium'
                FROM employees e
                LEFT JOIN time_entries te ON e.id = te.employee_id 
                    AND DATE(te.punch_in) BETWEEN ? AND ?
                LEFT JOIN project_tasks pt ON te.task_id = pt.id
                LEFT JOIN employee_task_assignments eta ON te.employee_id = eta.employee_id 
                    AND te.project_id = eta.project_id AND te.task_id = eta.task_id
                WHERE e.role != 'admin'
                GROUP BY e.id
                ORDER BY 'Revenus totaux (CAD)' DESC
            """
            
            df_report = pd.read_sql_query(query, conn, params=(start_date, end_date))
            
        elif report_type == "Rapport de paie avec taux D&G":
            # Rapport pour la paie avec taux D&G réels
            query = """
                SELECT 
                    e.name as 'Employé',
                    e.employee_code as 'Code',
                    COUNT(DISTINCT DATE(te.punch_in)) as 'Jours',
                    ROUND(SUM(CASE 
                        WHEN te.punch_out IS NOT NULL THEN
                            MIN(((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60, 8)
                        ELSE 0
                    END), 2) as 'Heures régulières',
                    ROUND(SUM(CASE 
                        WHEN te.punch_out IS NOT NULL THEN
                            MAX(((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60 - 8, 0)
                        ELSE 0
                    END), 2) as 'Heures supplémentaires',
                    ROUND(SUM(CASE 
                        WHEN te.punch_out IS NOT NULL AND COALESCE(eta.hourly_rate_override, pt.hourly_rate) IS NOT NULL THEN
                            (((JULIANDAY(te.punch_out) - JULIANDAY(te.punch_in)) * 24 * 60 - te.total_break_minutes) / 60) * COALESCE(eta.hourly_rate_override, pt.hourly_rate)
                        ELSE 0
                    END), 2) as 'Revenus bruts (CAD)',
                    ROUND(AVG(COALESCE(eta.hourly_rate_override, pt.hourly_rate)), 2) as 'Taux moyen ($/h)',
                    COUNT(CASE WHEN pt.hourly_rate >= 130 THEN 1 END) as 'Heures Premium',
                    GROUP_CONCAT(DISTINCT eta.skill_level) as 'Niveaux utilisés'
                FROM employees e
                LEFT JOIN time_entries te ON e.id = te.employee_id 
                    AND DATE(te.punch_in) BETWEEN ? AND ?
                LEFT JOIN project_tasks pt ON te.task_id = pt.id
                LEFT JOIN employee_task_assignments eta ON te.employee_id = eta.employee_id 
                    AND te.project_id = eta.project_id AND te.task_id = eta.task_id
                WHERE e.role != 'admin'
                GROUP BY e.id
                ORDER BY 'Revenus bruts (CAD)' DESC
            """
            
            df_report = pd.read_sql_query(query, conn, params=(start_date, end_date))
        
        conn.close()
        
        if not df_report.empty:
            st.markdown(f"#### 📊 {report_type}")
            st.dataframe(df_report, use_container_width=True, hide_index=True)
            
            # Statistiques spécialisées D&G
            if 'Revenus' in df_report.columns.str.cat():
                revenue_cols = [col for col in df_report.columns if 'Revenus' in col or 'revenus' in col]
                if revenue_cols:
                    total_revenue = df_report[revenue_cols[0]].sum()
                    st.markdown(f"**💰 Total Revenus: {total_revenue:,.2f}$ CAD**")
            
            if 'Total heures' in df_report.columns:
                total_hours = df_report['Total heures'].sum()
                st.markdown(f"**⏱️ Total Heures: {total_hours:.1f}h**")
            
            if 'Sessions Premium' in df_report.columns:
                premium_sessions = df_report['Sessions Premium'].sum()
                st.markdown(f"**🔥 Sessions Premium (≥130$): {premium_sessions}**")
            
            # Bouton d'export Excel
            excel_data = generate_excel_report(df_report)
            filename = f"rapport_dg_{report_type.lower().replace(' ', '_')}_{start_date}_{end_date}.xlsx"
            
            st.download_button(
                label="📥 Télécharger Excel",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Aucune donnée trouvée pour cette période")

# ================================
# FONCTIONS PRINCIPALES
# ================================

@st.cache_resource
def get_database():
    """Initialise et retourne l'instance de base de données"""
    return DatabaseManager()

def main():
    """Fonction principale de l'application avec gestion d'erreurs robuste"""
    
    try:
        # Charger le CSS
        load_css()
        
        # Initialiser l'état de session
        if 'logged_in' not in st.session_state:
            st.session_state.logged_in = False
        if 'user_info' not in st.session_state:
            st.session_state.user_info = None
        
        # Sidebar avec bouton de déconnexion si connecté
        if st.session_state.logged_in:
            with st.sidebar:
                st.markdown("### ⚙️ Menu")
                
                user_info = st.session_state.user_info
                st.info(f"👤 **{user_info['name']}**\n\nCode: {user_info['employee_code']}\nRôle: {user_info['role']}")
                
                st.markdown("---")
                
                # Informations système D&G
                try:
                    db = get_database()
                    stats = db.get_dashboard_stats()
                    dg_stats = db.get_dg_enhanced_stats()
                    
                    st.markdown("### 📊 Stats D&G")
                    st.metric("👥 Employés pointés", stats['pointés_aujourd_hui'])
                    st.metric("🟢 Au travail", stats['au_travail']) 
                    st.metric("💰 Revenus aujourd'hui", f"{dg_stats['revenus_today']:,.0f}$")
                    st.metric("⚡ Efficacité moyenne", f"{dg_stats['avg_efficiency']:.0f}$/h")
                except Exception as e:
                    st.warning("⚠️ Erreur chargement stats")
                    st.caption(f"Détail: {str(e)}")
                
                # Nouveautés version D&G
                st.markdown("---")
                st.markdown("### 🏭 Version D&G Complète")
                st.success("✅ 34 postes de travail réels")
                st.success("✅ Taux 85-140$ CAD")
                st.success("✅ 8 catégories métier")
                st.success("✅ Sélecteur avancé avec filtres")
                st.success("✅ Dashboard revenus temps réel")
                st.success("✅ Analytics par niveau taux")
                st.success("✅ Auto-assignations nouveaux employés")
                st.success("✅ Rapports spécialisés D&G")
                
                st.markdown("---")
                
                # Bouton de déconnexion
                if st.button("🚪 Se déconnecter", use_container_width=True):
                    st.session_state.logged_in = False
                    st.session_state.user_info = None
                    # Nettoyer les états de session
                    for key in list(st.session_state.keys()):
                        if any(x in key for x in ['edit_', 'delete_', 'selected_task', 'view_', 'assign_']):
                            del st.session_state[key]
                    st.success("👋 Déconnexion réussie")
                    time.sleep(1)
                    st.rerun()
        
        # Affichage de l'interface selon l'état de connexion
        if not st.session_state.logged_in:
            show_login_page()
        else:
            user_info = st.session_state.user_info
            if user_info and user_info.get('role') == 'admin':
                show_admin_interface()
            else:
                show_employee_interface()
                
    except Exception as e:
        st.error("🚨 Une erreur inattendue s'est produite")
        st.markdown("### 🔧 Informations de débogage")
        
        col1, col2 = st.columns(2)
        with col1:
            st.error(f"**Type d'erreur:** {type(e).__name__}")
            st.error(f"**Message:** {str(e)}")
        
        with col2:
            st.info("### 🔄 Solutions suggérées")
            st.markdown("""
            1. **Rafraîchir la page** (F5)
            2. **Se déconnecter et reconnecter**
            3. **Vider le cache du navigateur**
            4. **Contacter l'administrateur**
            """)
        
        # Bouton de reset d'urgence
        if st.button("🆘 Reset Application", help="Remet à zéro la session"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("✅ Session réinitialisée")
            st.info("🔄 Veuillez rafraîchir la page")
        
        # Option pour afficher le traceback complet en développement
        if st.checkbox("🔍 Afficher détails techniques"):
            import traceback
            st.code(traceback.format_exc())

# ================================
# POINT D'ENTRÉE
# ================================

if __name__ == "__main__":
    main()
