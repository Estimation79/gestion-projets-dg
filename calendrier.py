# calendrier.py - Version 100% Native Streamlit
# ERP Production DG Inc. - Calendrier entièrement basé sur les composants Streamlit
# ✅ AUCUN HTML PERSONNALISÉ - COMPOSANTS STREAMLIT UNIQUEMENT

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import calendar

# NOUVELLE ARCHITECTURE : Import SQLite Database et Gestionnaires
from erp_database import ERPDatabase
from app import GestionnaireProjetSQL  # Import depuis app.py

def load_external_css():
    """Charge le fichier CSS externe pour un design uniforme"""
    try:
        with open('style.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
        st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
        return True
    except FileNotFoundError:
        st.warning("⚠️ Fichier style.css non trouvé. Utilisation du style par défaut.")
        return False
    except Exception as e:
        st.warning(f"⚠️ Erreur chargement CSS: {e}")
        return False

def display_calendar_native_streamlit(year, month, month_events):
    """Calendrier 100% composants Streamlit natifs"""
    
    # Nom du mois en français
    month_names_fr = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                     "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    
    # Titre du calendrier
    st.subheader(f"📅 {month_names_fr[month]} {year}")
    
    # En-têtes des jours de la semaine
    days_fr = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    header_cols = st.columns(7)
    
    for i, day_name in enumerate(days_fr):
        with header_cols[i]:
            st.markdown(f"**{day_name}**")
    
    # Obtenir le calendrier du mois
    cal = calendar.monthcalendar(year, month)
    today = date.today()
    selected_date = st.session_state.selected_date
    
    # Afficher chaque semaine
    for week_index, week in enumerate(cal):
        week_cols = st.columns(7)
        
        for day_index, day in enumerate(week):
            with week_cols[day_index]:
                if day == 0:
                    # Jour vide
                    st.write("")
                else:
                    current_date = date(year, month, day)
                    
                    # Vérifier les événements pour ce jour
                    day_events = month_events.get(current_date, [])
                    num_events = len(day_events)
                    
                    # Déterminer le type de bouton selon l'état du jour
                    button_type = "secondary"
                    button_label = f"{day}"
                    
                    if current_date == today:
                        button_type = "primary"
                        button_label = f"🌟 {day}"
                    elif current_date == selected_date:
                        button_label = f"✅ {day}"
                    elif num_events > 0:
                        button_label = f"📅 {day}"
                    
                    # Ajouter indication du nombre d'événements
                    if num_events > 0:
                        button_label += f" ({num_events})"
                    
                    # Bouton pour sélectionner le jour
                    if st.button(
                        button_label, 
                        key=f"day_{year}_{month}_{day}_{week_index}_{day_index}",
                        help=f"Sélectionner le {day} {month_names_fr[month]} - {num_events} événement(s)",
                        type=button_type,
                        use_container_width=True
                    ):
                        st.session_state.selected_date = current_date
                        st.rerun()
                    
                    # Afficher les événements sous forme de puces
                    if num_events > 0:
                        for event in day_events[:2]:  # Max 2 événements affichés
                            event_type = event.get('type', 'N/A')
                            if event_type == 'Début':
                                st.caption(f"🚀 P#{event.get('id', '?')}")
                            elif event_type == 'Fin Prévue':
                                st.caption(f"🏁 P#{event.get('id', '?')}")
                            else:
                                st.caption(f"📋 P#{event.get('id', '?')}")
                        
                        if num_events > 2:
                            st.caption(f"... +{num_events - 2}")

def display_day_details_native_streamlit(selected_date, month_events, gestionnaire=None):
    """Affiche les détails du jour sélectionné avec composants Streamlit natifs"""
    
    # En-tête du jour sélectionné
    day_name_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    day_name = day_name_fr[selected_date.weekday()]
    month_name = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                 "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    
    with st.container():
        st.markdown(f"### 📅 {day_name} {selected_date.day} {month_name[selected_date.month]} {selected_date.year}")
        
        # Vérifier s'il y a des événements pour cette date
        day_events = month_events.get(selected_date, [])
        
        if not day_events:
            st.info("🌟 Aucun événement prévu pour cette journée")
            st.markdown("Cette journée est libre dans votre planning.")
        else:
            st.success(f"📋 {len(day_events)} événement(s) planifié(s)")
            
            # Affichage des événements avec des composants natifs
            for i, event in enumerate(day_events):
                with st.expander(f"📁 Projet #{event.get('id', '?')} - {event.get('nom_projet', 'N/A')}", expanded=i==0):
                    
                    # Informations de base
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("ID Projet", f"#{event.get('id', '?')}")
                        st.metric("Type d'événement", event.get('type', 'N/A'))
                    
                    with col2:
                        st.metric("Nom du projet", event.get('nom_projet', 'N/A'))
                        st.metric("Tâche", event.get('tache', 'N/A'))
                    
                    # Type d'événement avec icône
                    event_type = event.get('type', 'N/A')
                    if event_type == 'Début':
                        st.success("🚀 **Début de Projet** - Lancement des travaux")
                    elif event_type == 'Fin Prévue':
                        st.error("🏁 **Fin Prévue** - Livraison attendue")
                    else:
                        st.info(f"📋 **{event_type}**")
                    
                    # Bouton pour voir les détails complets
                    if st.button(
                        "🔍 Voir les Détails Complets", 
                        key=f"details_btn_{event.get('id', i)}",
                        type="primary",
                        use_container_width=True
                    ):
                        # Trouver le projet dans les données SQLite
                        projet = next((p for p in gestionnaire.projets if p.get('id') == event.get('id')), None)
                        if projet:
                            st.session_state.selected_project_id = event.get('id')
                            st.session_state.selected_project = projet
                            st.session_state.show_project_details = True
                            st.rerun()
                        else:
                            st.error(f"Projet #{event.get('id')} non trouvé dans la base de données")

def get_events_for_month(year, month, gestionnaire):
    """Récupère tous les événements pour le mois donné - VERSION SQLITE."""
    events = {}
    
    # Déterminer la plage de dates du mois
    _, last_day = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)
    
    # Parcourir les projets depuis SQLite
    for projet in gestionnaire.projets:
        proj_id = projet.get('id')
        proj_nom = projet.get('nom_projet', 'N/A')
        
        # Vérifier la date de début
        try:
            date_debut_str = projet.get('date_soumis')
            if date_debut_str:
                date_debut = datetime.strptime(date_debut_str, "%Y-%m-%d").date()
                if start_date <= date_debut <= end_date:
                    if date_debut not in events:
                        events[date_debut] = []
                    events[date_debut].append({
                        'id': proj_id,
                        'nom_projet': proj_nom,
                        'type': 'Début',
                        'tache': projet.get('tache', 'N/A')
                    })
        except (ValueError, TypeError):
            pass
        
        # Vérifier la date de fin
        try:
            date_fin_str = projet.get('date_prevu')
            if date_fin_str:
                date_fin = datetime.strptime(date_fin_str, "%Y-%m-%d").date()
                if start_date <= date_fin <= end_date:
                    if date_fin not in events:
                        events[date_fin] = []
                    events[date_fin].append({
                        'id': proj_id,
                        'nom_projet': proj_nom,
                        'type': 'Fin Prévue',
                        'tache': projet.get('tache', 'N/A')
                    })
        except (ValueError, TypeError):
            pass
    
    return events

def display_navigation_native(current_year, current_month):
    """Navigation avec composants Streamlit natifs"""
    month_names_fr = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                     "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    
    # Navigation principale
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("◀️ Mois Précédent", key="nav_prev", use_container_width=True):
            if current_month == 1:
                st.session_state.view_month = 12
                st.session_state.view_year = current_year - 1
            else:
                st.session_state.view_month = current_month - 1
            st.rerun()
    
    with col2:
        st.markdown(f"<h3 style='text-align: center; color: #1e40af;'>{month_names_fr[current_month]} {current_year}</h3>", unsafe_allow_html=True)
    
    with col3:
        if st.button("Mois Suivant ▶️", key="nav_next", use_container_width=True):
            if current_month == 12:
                st.session_state.view_month = 1
                st.session_state.view_year = current_year + 1
            else:
                st.session_state.view_month = current_month + 1
            st.rerun()
    
    # Bouton "Aujourd'hui" centré
    col_today = st.columns([2, 1, 2])[1]
    with col_today:
        if st.button("📅 Aujourd'hui", key="nav_today", type="primary", use_container_width=True):
            today = datetime.now().date()
            st.session_state.view_month = today.month
            st.session_state.view_year = today.year
            st.session_state.selected_date = today
            st.rerun()

def show_project_details_native():
    """Affichage des détails d'un projet avec composants natifs"""
    projet_id = st.session_state.selected_project_id
    projet = st.session_state.selected_project
    
    with st.container():
        st.markdown("---")
        st.header(f"📁 Détails du Projet #{projet_id}")
        
        # Informations principales
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Nom du Projet", projet.get('nom_projet', 'Sans Nom'))
            st.metric("Client", projet.get('client_nom_cache', 'N/A'))
        
        with col2:
            st.metric("Statut", projet.get('statut', 'N/A'))
            st.metric("Priorité", projet.get('priorite', 'N/A'))
        
        with col3:
            st.metric("Prix Estimé", f"{projet.get('prix_estime', 'N/A')}")
            st.metric("BD-FT Estimé", f"{projet.get('bd_ft_estime', 'N/A')}h")
        
        # Dates
        st.subheader("📅 Planification")
        date_col1, date_col2 = st.columns(2)
        
        with date_col1:
            st.metric("Date de Début", projet.get('date_soumis', 'N/A'))
        
        with date_col2:
            st.metric("Date de Fin Prévue", projet.get('date_prevu', 'N/A'))
        
        # Description
        if projet.get('description'):
            st.subheader("📝 Description")
            st.write(projet.get('description'))
        
        # Bouton fermer
        if st.button("✖️ Fermer les Détails", type="secondary", use_container_width=True):
            st.session_state.show_project_details = False
            st.rerun()

def app():
    """Application calendrier principale - VERSION 100% NATIVE STREAMLIT"""
    
    # Charger le CSS si disponible
    css_loaded = load_external_css()
    
    # Titre principal avec émojis
    st.title("📅 Calendrier ERP")
    st.markdown("Interface 100% Native Streamlit - Base SQLite Unifiée")
    
    # INITIALISATION SQLITE
    if 'erp_db' not in st.session_state:
        st.session_state.erp_db = ERPDatabase("erp_production_dg.db")
    
    if 'gestionnaire' not in st.session_state:
        st.session_state.gestionnaire = GestionnaireProjetSQL(st.session_state.erp_db)
    
    gestionnaire = st.session_state.gestionnaire
    
    # Message de statut
    status_css = "✅ CSS externe chargé" if css_loaded else "⚠️ CSS par défaut utilisé"
    st.success(f"🎯 Calendrier entièrement natif activé ! - {status_css}")
    
    # Initialisation des variables de session
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = datetime.now().date()
    if 'view_month' not in st.session_state:
        st.session_state.view_month = datetime.now().month
    if 'view_year' not in st.session_state:
        st.session_state.view_year = datetime.now().year
    if 'show_project_details' not in st.session_state:
        st.session_state.show_project_details = False
    
    # Sidebar avec statistiques natives
    with st.sidebar:
        st.header("📊 Statistiques")
        
        try:
            total_projects_sql = st.session_state.erp_db.get_table_count('projects')
            total_companies = st.session_state.erp_db.get_table_count('companies')
            
            st.metric("📋 Projets Total", total_projects_sql)
            st.metric("🏢 Entreprises", total_companies)
            
            if total_projects_sql == 0:
                st.warning("⚠️ Aucun projet en base")
                st.info("Créez des projets dans le module Projets pour voir les événements dans le calendrier.")
            else:
                st.success(f"✅ {total_projects_sql} projets en base")
            
        except Exception as e:
            st.error(f"Erreur base de données: {e}")
        
        # Informations sur la date sélectionnée
        st.markdown("---")
        st.markdown("### 📍 Date Sélectionnée")
        st.info(f"📅 {st.session_state.selected_date.strftime('%d/%m/%Y')}")
        
        # Raccourcis rapides
        st.markdown("---")
        st.markdown("### 🚀 Raccourcis")
        
        if st.button("🏠 Retour ERP", use_container_width=True):
            # Retour vers la navigation principale de l'ERP
            st.switch_page("app.py")
    
    # Variables pour le mois/année actuels
    current_month = st.session_state.view_month
    current_year = st.session_state.view_year
    
    # Navigation
    display_navigation_native(current_year, current_month)
    
    st.markdown("---")
    
    # Récupérer les événements pour le mois
    month_events = get_events_for_month(current_year, current_month, gestionnaire)
    
    # Afficher le nombre total d'événements du mois
    total_events = sum(len(events) for events in month_events.values())
    if total_events > 0:
        st.info(f"📅 {total_events} événement(s) planifié(s) ce mois-ci")
    else:
        st.warning("📅 Aucun événement planifié ce mois-ci")
    
    # Layout principal avec colonnes natives
    col_cal, col_details = st.columns([3, 2])
    
    with col_cal:
        st.markdown("#### 🗓️ Vue Calendrier")
        display_calendar_native_streamlit(current_year, current_month, month_events)
    
    with col_details:
        st.markdown("#### 📋 Détails du Jour")
        display_day_details_native_streamlit(st.session_state.selected_date, month_events, gestionnaire)
    
    # Modal pour les détails du projet (uniquement si activée)
    if st.session_state.get('show_project_details'):
        show_project_details_native()

if __name__ == "__main__":
    app()