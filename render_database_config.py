"""
Configuration de base de données pour déploiement sur Render
Supporte SQLite local et PostgreSQL pour production
"""

import os
import streamlit as st
from urllib.parse import urlparse

def get_database_url():
    """
    Retourne l'URL de base de données appropriée selon l'environnement
    """
    # Vérifier si on est sur Render (DATABASE_URL est défini)
    if os.getenv('DATABASE_URL'):
        return os.getenv('DATABASE_URL')
    
    # Sinon, utiliser SQLite local
    return 'sqlite:///erp_production_dg.db'

def init_render_database():
    """
    Initialise la connexion à la base de données pour Render
    """
    db_url = get_database_url()
    
    if db_url.startswith('postgres://'):
        # PostgreSQL sur Render
        try:
            import psycopg2
            from sqlalchemy import create_engine
            
            # Render utilise postgres:// mais SQLAlchemy veut postgresql://
            if db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql://', 1)
            
            # Créer engine SQLAlchemy
            engine = create_engine(db_url)
            
            st.success("✅ Connecté à PostgreSQL sur Render")
            return engine
            
        except ImportError:
            st.error("❌ psycopg2 et sqlalchemy requis pour PostgreSQL")
            st.info("Ajoutez à requirements.txt : psycopg2-binary sqlalchemy")
            return None
    else:
        # SQLite local (développement)
        from erp_database import ERPDatabase
        return ERPDatabase()

def check_database_access():
    """
    Vérifie l'accès à la base de données et retourne un statut
    """
    try:
        if 'erp_db' not in st.session_state:
            st.session_state.erp_db = init_render_database()
        
        if st.session_state.erp_db is None:
            return {
                'status': 'error',
                'message': 'Base de données non disponible',
                'can_use_ai': False
            }
        
        # Test simple de connexion
        if hasattr(st.session_state.erp_db, 'execute_query'):
            # SQLite
            result = st.session_state.erp_db.execute_query("SELECT 1")
            if result:
                return {
                    'status': 'ok',
                    'message': 'Base SQLite connectée',
                    'can_use_ai': True
                }
        else:
            # PostgreSQL via SQLAlchemy
            with st.session_state.erp_db.connect() as conn:
                result = conn.execute("SELECT 1")
                if result:
                    return {
                        'status': 'ok',
                        'message': 'Base PostgreSQL connectée',
                        'can_use_ai': True
                    }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Erreur connexion: {str(e)}',
            'can_use_ai': False
        }
    
    return {
        'status': 'warning',
        'message': 'Base de données non configurée',
        'can_use_ai': False
    }

def get_ai_fallback_context():
    """
    Retourne un contexte IA de secours quand la DB n'est pas accessible
    """
    return {
        'mode': 'demo',
        'message': 'Mode démonstration - Données ERP non disponibles',
        'sample_data': {
            'projects': [
                {
                    'id': 10001,
                    'nom_projet': 'Châssis Automobile',
                    'client': 'AutoTech Corp',
                    'statut': 'EN_COURS',
                    'budget': 35000
                },
                {
                    'id': 10002,
                    'nom_projet': 'Structure Industrielle',
                    'client': 'BâtiTech Inc',
                    'statut': 'PLANIFIE',
                    'budget': 58000
                }
            ],
            'inventory': {
                'total_items': 156,
                'low_stock_alerts': 12,
                'categories': ['Acier', 'Aluminium', 'Inox', 'Consommables']
            },
            'employees': {
                'total': 45,
                'departments': ['Production', 'Usinage', 'Ingénierie', 'Qualité']
            }
        }
    }