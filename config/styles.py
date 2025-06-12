# config/styles.py
"""
Styles CSS pour l'ERP Production DG Inc.
"""

import streamlit as st
import os


def load_css_file(css_file_path):
    """Charge un fichier CSS externe"""
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


def get_integrated_css():
    """Retourne le CSS intégré de l'application"""
    return """
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
    
    .stApp { 
        font-family: var(--font-family) !important; 
        background: var(--background-color) !important; 
        color: var(--text-color) !important; 
        min-height: 100vh; 
    }
    
    body { 
        font-family: var(--font-family) !important; 
        color: var(--text-color); 
        background-color: var(--background-color); 
        line-height: 1.6; 
        font-size: 16px; 
    }
    
    .main .block-container h1, .main .block-container h2, .main .block-container h3, 
    .main .block-container h4, .main .block-container h5, .main .block-container h6 {
        font-family: var(--font-family) !important; 
        font-weight: 700 !important; 
        color: var(--text-color) !important; 
        margin-bottom: 0.8em; 
        line-height: 1.3;
    }
    
    @keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
    @keyframes header-shine { 0% {left:-100%;} 50% {left:-100%;} 100% {left:100%;} }
    
    .main-title { 
        background: var(--primary-gradient) !important; 
        padding:25px 30px !important; 
        border-radius:16px !important; 
        color:white !important; 
        text-align:center !important;
        margin-bottom:30px !important; 
        box-shadow:var(--box-shadow-black) !important; 
        animation:fadeIn 0.8s ease-out !important;
        border:1px solid rgba(255,255,255,0.2) !important; 
        position:relative !important; 
        overflow:hidden !important;
    }
    
    .main-title::before { 
        content:""; 
        position:absolute; 
        top:0; 
        left:-100%; 
        width:100%; 
        height:100%;
        background:linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%);
        animation:header-shine 4s infinite; 
        z-index:1;
    }
    
    .main-title h1 { 
        margin:0 !important; 
        font-size:2.2rem !important; 
        font-weight:700 !important; 
        color:white !important;
        text-shadow:0 2px 4px rgba(0,0,0,0.6), 0 1px 2px rgba(0,0,0,0.4), 0 0 10px rgba(0,0,0,0.3) !important;
        position:relative !important; 
        z-index:2 !important;
    }
    
    .project-header { 
        background: linear-gradient(145deg, rgba(255,255,255,0.8) 0%, #DBEAFE 25%, #93C5FD 75%, rgba(59,130,246,0.3) 100%) !important;
        padding:22px 25px !important; 
        border-radius:14px !important; 
        margin-bottom:25px !important;
        box-shadow:0 6px 20px rgba(59,130,246,0.2), inset 0 2px 0 rgba(255,255,255,0.6), inset 0 -1px 0 rgba(0,0,0,0.1), 0 0 20px rgba(59,130,246,0.1) !important;
        border:1px solid rgba(59,130,246,0.3) !important; 
        position:relative !important; 
        overflow:hidden !important;
    }
    
    .project-header h2 { 
        margin:0 !important; 
        color:#1E40AF !important; 
        font-size:1.6rem !important; 
        display:flex !important;
        align-items:center !important; 
        font-weight:700 !important; 
        text-shadow:0 1px 2px rgba(255,255,255,0.8) !important;
        position:relative !important; 
        z-index:2 !important;
    }
    
    .stButton > button { 
        background:var(--button-gradient) !important; 
        color:white !important; 
        border:none !important;
        border-radius:var(--border-radius-md) !important; 
        padding:0.6rem 1.2rem !important; 
        font-weight:600 !important;
        transition:all var(--animation-speed) ease !important; 
        box-shadow:0 4px 8px rgba(59,130,246,0.25), inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -1px 0 rgba(0,0,0,0.1) !important; 
        width:100% !important;
        text-align:center !important; 
        display:inline-flex !important; 
        align-items:center !important;
        justify-content:center !important; 
        position:relative !important; 
        overflow:hidden !important;
    }
    
    .stButton > button:hover { 
        background:var(--button-gradient-hover) !important; 
        transform:translateY(-3px) !important;
        box-shadow:0 8px 16px rgba(59,130,246,0.35), inset 0 2px 0 rgba(255,255,255,0.4), inset 0 -2px 0 rgba(0,0,0,0.15), 0 0 20px rgba(59,130,246,0.2) !important;
    }
    
    .info-card, .nav-container, .section-card { 
        background:var(--card-background) !important; 
        padding:1.5rem !important; 
        border-radius:var(--border-radius-lg) !important;
        margin-bottom:1.5rem !important; 
        box-shadow:var(--box-shadow-md) !important; 
        border:1px solid var(--border-color-light) !important; 
        transition:all 0.3s ease !important;
    }
    
    .info-card:hover, .section-card:hover { 
        transform:translateY(-4px) !important; 
        box-shadow:var(--box-shadow-blue) !important; 
    }
    
    div[data-testid="stMetric"] { 
        background:var(--card-background) !important; 
        padding:1.5rem !important;
        border-radius:var(--border-radius-lg) !important; 
        box-shadow:var(--box-shadow-md) !important;
        border:1px solid var(--border-color-light) !important; 
        transition:all 0.3s ease !important;
    }
    
    div[data-testid="stMetric"]:hover { 
        transform:translateY(-4px) !important; 
        box-shadow:var(--box-shadow-blue) !important; 
    }
    
    .dataframe { 
        background:var(--card-background) !important; 
        border-radius:var(--border-radius-lg) !important;
        overflow:hidden !important; 
        box-shadow:var(--box-shadow-md) !important; 
        border:1px solid var(--border-color) !important;
    }
    
    .dataframe th { 
        background:linear-gradient(135deg, var(--primary-color-lighter), var(--primary-color-light)) !important;
        color:var(--primary-color-darkest) !important; 
        font-weight:600 !important; 
        padding:1rem !important; 
        border:none !important;
        border-bottom: 2px solid var(--primary-color) !important;
    }
    
    .dataframe td { 
        padding:0.75rem 1rem !important; 
        border-bottom:1px solid var(--border-color-light) !important;
        background:var(--card-background) !important; 
        color:var(--text-color) !important;
    }
    
    .dataframe tr:hover td { 
        background:var(--primary-color-lighter) !important; 
    }
    
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
    
    /* Responsive */
    @media (max-width:768px) {
        .main-title { padding:15px !important; margin-bottom:15px !important; }
        .main-title h1 { font-size:1.8rem !important; }
        .info-card, .nav-container, .section-card { padding:1rem !important; margin-bottom:1rem !important; }
        .stButton > button { min-height:44px !important; font-size:16px !important; padding:0.8rem 1rem !important; }
    }
    
    .stApp > div { animation:fadeIn 0.5s ease-out; }
    
    ::-webkit-scrollbar { width:8px; }
    ::-webkit-scrollbar-track { background:var(--border-color-light); border-radius:4px; }
    ::-webkit-scrollbar-thumb { background:var(--primary-color-light); border-radius:4px; }
    ::-webkit-scrollbar-thumb:hover { background:var(--primary-color); }
    """


def apply_global_styles():
    """Applique les styles CSS globaux"""
    css_loaded = load_css_file('style.css')
    if not css_loaded:
        st.markdown(f'<style>{get_integrated_css()}</style>', unsafe_allow_html=True)
