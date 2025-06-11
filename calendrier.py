import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import calendar
import os
import json

# --- Classe GestionnaireProjetIA (intégrée pour rendre le fichier autonome) ---
# NOTE: Cette classe est une copie de celle dans app.py pour la cohérence.
class GestionnaireProjetIA:
    def __init__(self):
        self.data_file = "projets_data.json"
        self.projets = []
        self.next_id = 1
        self.charger_projets()

    def charger_projets(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.projets = data.get('projets', [])
                    self.next_id = data.get('next_id', len(self.projets) + 1 if self.projets else 1)
            else:
                self.projets = self.get_demo_data()
                self.next_id = len(self.projets) + 1
        except Exception as e:
            st.error(f"Erreur chargement projets: {e}")
            self.projets = self.get_demo_data()
            self.next_id = len(self.projets) + 1

    def sauvegarder_projets(self):
        try:
            data = {'projets': self.projets, 'next_id': self.next_id, 'last_update': datetime.now().isoformat()}
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            st.error(f"Erreur sauvegarde projets: {e}")

    def get_demo_data(self):
        now_iso = datetime.now().isoformat()
        return [
            {'id': 1, 'nom_projet': 'Site Web E-commerce', 'client_entreprise_id': 101, 'client_nom_cache': 'TechCorp Inc.', 'statut': 'EN COURS', 'priorite': 'ÉLEVÉ', 'tache': 'DÉVELOPPEMENT', 'date_soumis': '2024-01-15', 'date_prevu': '2024-03-15', 'bd_ft_estime': '120', 'prix_estime': '25000', 'description': 'Développement d\'une plateforme e-commerce complète avec paiement en ligne', 'sous_taches': [{'id': 1, 'nom': 'Design UI/UX', 'statut': 'TERMINÉ', 'date_debut': '2024-01-15', 'date_fin': '2024-01-30'}, {'id': 2, 'nom': 'Développement Frontend', 'statut': 'EN COURS', 'date_debut': '2024-02-01', 'date_fin': '2024-02-28'}, {'id': 3, 'nom': 'Intégration paiement', 'statut': 'À FAIRE', 'date_debut': '2024-03-01', 'date_fin': '2024-03-15'}], 'materiaux': [{'id': 1, 'code': 'LIC-001', 'designation': 'Licence SSL', 'quantite': 1, 'unite': 'pcs', 'prix_unitaire': 150, 'fournisseur': 'SecureTech'}, {'id': 2, 'code': 'SRV-001', 'designation': 'Serveur Cloud', 'quantite': 12, 'unite': 'mois', 'prix_unitaire': 200, 'fournisseur': 'CloudProvider'}], 'operations': [{'id': 1, 'sequence': '10', 'description': 'Analyse des besoins', 'temps_estime': 16, 'ressource': 'Analyste', 'statut': 'TERMINÉ'}, {'id': 2, 'sequence': '20', 'description': 'Conception architecture', 'temps_estime': 24, 'ressource': 'Architecte', 'statut': 'TERMINÉ'}, {'id': 3, 'sequence': '30', 'description': 'Développement', 'temps_estime': 80, 'ressource': 'Développeurs', 'statut': 'EN COURS'}]},
            {'id': 2, 'nom_projet': 'Application Mobile', 'client_entreprise_id': 102, 'client_nom_cache': 'StartupXYZ', 'statut': 'À FAIRE', 'priorite': 'MOYEN', 'tache': 'ESTIMATION', 'date_soumis': '2024-02-01', 'date_prevu': '2024-05-01', 'bd_ft_estime': '80', 'prix_estime': '18000', 'description': 'Application mobile native iOS et Android pour gestion de tâches', 'sous_taches': [{'id': 1, 'nom': 'Wireframes', 'statut': 'À FAIRE', 'date_debut': '2024-02-15', 'date_fin': '2024-02-28'}, {'id': 2, 'nom': 'Développement iOS', 'statut': 'À FAIRE', 'date_debut': '2024-03-01', 'date_fin': '2024-04-15'}, {'id': 3, 'nom': 'Développement Android', 'statut': 'À FAIRE', 'date_debut': '2024-03-01', 'date_fin': '2024-04-15'}], 'materiaux': [{'id': 1, 'code': 'DEV-IOS', 'designation': 'Licence développeur iOS', 'quantite': 1, 'unite': 'pcs', 'prix_unitaire': 99, 'fournisseur': 'Apple'}, {'id': 2, 'code': 'DEV-AND', 'designation': 'Licence développeur Android', 'quantite': 1, 'unite': 'pcs', 'prix_unitaire': 25, 'fournisseur': 'Google'}], 'operations': [{'id': 1, 'sequence': '10', 'description': 'Spécifications techniques', 'temps_estime': 12, 'ressource': 'Analyste', 'statut': 'À FAIRE'}, {'id': 2, 'sequence': '20', 'description': 'Développement cross-platform', 'temps_estime': 60, 'ressource': 'Développeurs', 'statut': 'À FAIRE'}, {'id': 3, 'sequence': '30', 'description': 'Tests et déploiement', 'temps_estime': 8, 'ressource': 'Testeur', 'statut': 'À FAIRE'}]},
            {'id': 3, 'nom_projet': 'Système CRM', 'client_entreprise_id': 103, 'client_nom_cache': 'MegaCorp Ltd', 'statut': 'TERMINÉ', 'priorite': 'ÉLEVÉ', 'tache': 'LIVRAISON', 'date_soumis': '2023-10-01', 'date_prevu': '2024-01-31', 'bd_ft_estime': '200', 'prix_estime': '45000', 'description': 'Système de gestion de relation client personnalisé avec intégrations', 'sous_taches': [{'id': 1, 'nom': 'Module contacts', 'statut': 'TERMINÉ', 'date_debut': '2023-10-15', 'date_fin': '2023-11-15'}, {'id': 2, 'nom': 'Module ventes', 'statut': 'TERMINÉ', 'date_debut': '2023-11-16', 'date_fin': '2023-12-15'}, {'id': 3, 'nom': 'Rapports et analytics', 'statut': 'TERMINÉ', 'date_debut': '2023-12-16', 'date_fin': '2024-01-31'}], 'materiaux': [{'id': 1, 'code': 'DB-001', 'designation': 'Base de données Enterprise', 'quantite': 1, 'unite': 'licence', 'prix_unitaire': 5000, 'fournisseur': 'DatabaseCorp'}, {'id': 2, 'code': 'INT-001', 'designation': 'API Intégrations', 'quantite': 5, 'unite': 'pcs', 'prix_unitaire': 200, 'fournisseur': 'IntegrationHub'}], 'operations': [{'id': 1, 'sequence': '10', 'description': 'Analyse détaillée', 'temps_estime': 40, 'ressource': 'Analyste Senior', 'statut': 'TERMINÉ'}, {'id': 2, 'sequence': '20', 'description': 'Développement modules', 'temps_estime': 120, 'ressource': 'Équipe Dev', 'statut': 'TERMINÉ'}, {'id': 3, 'sequence': '30', 'description': 'Tests et formation', 'temps_estime': 40, 'ressource': 'Consultant', 'statut': 'TERMINÉ'}]}
        ]

# --- Fin de la classe GestionnaireProjetIA ---


def is_mobile_device():
    """Estimation si l'appareil est mobile basée sur la largeur de viewport."""
    # Si non défini ou première visite, définir par défaut comme non-mobile
    if 'is_mobile' not in st.session_state:
        st.session_state.is_mobile = False

    # JavaScript pour détecter la largeur d'écran et mettre à jour via le localStorage
    st.markdown("""
    <script>
    // Vérifier si l'appareil a une petite largeur d'écran
    const checkIfMobile = function() {
        const isMobile = window.innerWidth < 768;
        localStorage.setItem('streamlit_is_mobile', isMobile);
        return isMobile;
    };
    
    // Exécuter au chargement et à chaque redimensionnement
    checkIfMobile();
    window.addEventListener('resize', checkIfMobile);
    
    // Essayer de communiquer avec Streamlit
    window.addEventListener('message', function(event) {
        if (event.data.type === 'streamlit:render') {
            setTimeout(function() {
                const buttons = document.querySelectorAll('button[data-baseweb="button"]');
                if (buttons.length > 0) {
                    // Ajouter un attribut data-mobile pour utilisation future
                    buttons.forEach(function(button) {
                        button.setAttribute('data-is-mobile', checkIfMobile());
                    });
                }
            }, 500);
        }
    });
    </script>
    """, unsafe_allow_html=True)
    
    # Retourner la valeur actuelle
    return st.session_state.is_mobile

def display_mini_calendar(year, month, calendar_func, month_events, is_mobile=False):
    """Affiche le mini calendrier avec adaptation mobile."""
    month_calendar, days_names = calendar_func(year, month)
    
    # Style CSS amélioré pour plus de lisibilité et ajout d'icônes
    st.markdown("""
    <style>
    .calendar-container {
        background-color: #f7f9fc;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.08);
    }
    .calendar-day {
        text-align: center;
        padding: 12px 0;
        margin: 3px;
        border-radius: 12px;
        min-height: 45px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        font-weight: 500;
        cursor: pointer;
        background-color: #ffffff;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        color: #333;
    }
    .calendar-day:hover {
        background-color: #e6f0ff;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    .calendar-day.selected {
        background: linear-gradient(135deg, #a5d8ff 0%, #c8e6ff 100%);
        color: #0056b3;
        font-weight: bold;
        box-shadow: 0 4px 8px rgba(26, 115, 232, 0.2);
        transform: scale(1.05);
    }
    .calendar-day.today {
        border: 2px solid #b2d8d8;
        background-color: #e8f5f5;
        position: relative;
    }
    .calendar-day.today::after {
        content: "📅";
        position: absolute;
        top: -8px;
        right: -8px;
        font-size: 12px;
    }
    .calendar-day.has-events {
        font-weight: bold;
        position: relative;
    }
    .calendar-day.has-events::after {
        content: "🔔";
        position: absolute;
        bottom: -5px;
        right: -3px;
        font-size: 12px;
    }
    .calendar-header {
        font-weight: bold;
        text-align: center;
        padding: 12px 0;
        margin-bottom: 8px;
        color: #5c7cfa;
        background-color: #edf2ff;
        border-radius: 8px;
        font-size: 16px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    /* Adaptations spécifiques pour mobile */
    @media(max-width: 768px) {
        .calendar-day {
            font-size: 16px;
            padding: 10px 0;
            min-height: 40px;
        }
        .calendar-header {
            font-size: 14px;
            padding: 10px 0;
        }
    }
    /* Ajout de styles pour le bouton du jour sélectionné */
    button.selected-day {
        background: linear-gradient(135deg, #a5d8ff 0%, #c8e6ff 100%) !important;
        color: #0056b3 !important;
        font-weight: bold !important;
        box-shadow: 0 4px 8px rgba(26, 115, 232, 0.2) !important;
        transform: scale(1.05) !important;
    }
    /* Styles pour les icônes de jour */
    .day-icon {
        position: absolute;
        right: -3px;
        bottom: -3px;
        font-size: 11px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Conteneur calendrier
    st.markdown('<div class="calendar-container">', unsafe_allow_html=True)
    
    # Ligne des jours de la semaine
    cols_days = st.columns(7)
    for i, day_name in enumerate(days_names):
        with cols_days[i]:
            st.markdown(f"<div class='calendar-header'>{day_name}</div>", unsafe_allow_html=True)
    
    # Jours du mois
    today = date.today()
    for week in month_calendar:
        cols_week = st.columns(7)
        for i, day in enumerate(week):
            with cols_week[i]:
                if day != 0:
                    # Déterminer si c'est le jour sélectionné
                    current_date = date(year, month, day)
                    is_selected = (current_date == st.session_state.selected_date)
                    is_today = (current_date == today)
                    has_events = current_date in month_events and month_events[current_date]
                    
                    # Préparer les icônes et styles
                    icons = ""
                    if is_today:
                        icons += "📆 "
                    if has_events:
                        icons += "🔔 "
                    
                    # Classe CSS pour le style
                    button_style = """
                    style="
                        width: 100%;
                        height: 100%;
                        font-size: {font_size};
                        font-weight: {font_weight};
                        border-radius: 10px;
                        border: {border};
                        background: {bg_color};
                        color: {text_color};
                        box-shadow: {shadow};
                        padding: 10px 5px;
                        position: relative;
                        transition: all 0.3s;
                    "
                    """.format(
                        font_size="18px" if not is_mobile else "16px",
                        font_weight="bold" if is_selected or has_events else "500",
                        border="2px solid #b2d8d8" if is_today else "1px solid #e0e0e0",
                        bg_color="linear-gradient(135deg, #a5d8ff 0%, #c8e6ff 100%)" if is_selected else "#ffffff",
                        text_color="#0056b3" if is_selected else "#333333",
                        shadow="0 4px 8px rgba(26, 115, 232, 0.2)" if is_selected else "0 2px 4px rgba(0, 0, 0, 0.05)"
                    )
                    
                    # Affichage du jour avec un style amélioré
                    day_display = f"{day}"
                    if has_events:
                        day_display += " 🔔"
                    if is_today:
                        day_display += " 📆"
                    if is_selected:
                        day_display += " ✓"
                    
                    if st.button(day_display, key=f"day_{year}_{month}_{day}", use_container_width=True):
                        st.session_state.selected_date = current_date
                        st.experimental_rerun()
                    
                    # Superposer les icônes si nécessaire
                    if has_events or is_today or is_selected:
                        icons_html = ""
                        if has_events:
                            icons_html += '<span style="position: absolute; bottom: -5px; right: 0; font-size: 12px;">🔔</span>'
                        if is_today:
                            icons_html += '<span style="position: absolute; top: -5px; left: 0; font-size: 12px;">📆</span>'
                        if is_selected:
                            icons_html += '<span style="position: absolute; top: -5px; right: 0; font-size: 12px;">✓</span>'
                        
                        # Injecter les icônes via JavaScript
                        st.markdown(f"""
                        <script>
                            (function() {{
                                const buttons = document.querySelectorAll('button[kind="secondary"][data-testid="baseButton-secondary"]');
                                const targetButton = Array.from(buttons).find(btn => btn.innerText.includes("{day}"));
                                if (targetButton) {{
                                    targetButton.innerHTML += '{icons_html}';
                                    targetButton.style.position = 'relative';
                                }}
                            }})();
                        </script>
                        """, unsafe_allow_html=True)
                else:
                    # Jour vide (hors du mois)
                    st.markdown("<div style='height: 45px;'></div>", unsafe_allow_html=True)
    
    # Fermer le conteneur calendrier
    st.markdown('</div>', unsafe_allow_html=True)

def display_day_details(selected_date, month_events, is_mobile=False, gestionnaire=None):
    """Affiche les détails du jour sélectionné avec adaptation mobile."""
    day_name_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    day_name = day_name_fr[selected_date.weekday()]
    month_name = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                 "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    
    # Style amélioré avec couleurs pastels et meilleure lisibilité
    st.markdown("""
    <style>
    .selected-date-header {
        background: linear-gradient(135deg, #a5d8ff 0%, #ffd6e0 100%);
        padding: 18px;
        border-radius: 12px;
        color: #333;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.08);
    }
    .selected-date-header h2 {
        font-size: 24px;
        margin: 0;
        font-weight: 600;
    }
    .event-card {
        background: linear-gradient(to right, #ffffff, #f7f9fc);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
        border-left: 5px solid;
        transition: transform 0.2s;
        position: relative;
    }
    .event-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.12);
    }
    .event-title {
        font-weight: bold;
        margin-bottom: 8px;
        font-size: 17px;
        color: #333;
        display: flex;
        align-items: center;
    }
    .event-title i {
        margin-right: 8px;
        font-size: 18px;
    }
    .event-type {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 14px;
        margin-bottom: 8px;
        font-weight: 500;
    }
    .event-details {
        font-size: 15px;
        color: #555;
        margin-top: 8px;
    }
    .type-debut {
        background-color: #e3f2fd;
        color: #1976d2;
        border-left-color: #bbdefb;
    }
    .type-debut .event-title::before {
        content: "🚀 ";
    }
    .type-fin {
        background-color: #e8f5e9;
        color: #388e3c;
        border-left-color: #c8e6c9;
    }
    .type-fin .event-title::before {
        content: "🏁 ";
    }
    .type-debut-st {
        background-color: #fff8e1;
        color: #ffa000;
        border-left-color: #ffecb3;
    }
    .type-debut-st .event-title::before {
        content: "▶️ ";
    }
    .type-fin-st {
        background-color: #fce4ec;
        color: #c2185b;
        border-left-color: #f8bbd0;
    }
    .type-fin-st .event-title::before {
        content: "✅ ";
    }
    .actions-container {
        background-color: #f8f9fa;
        border-radius: 12px;
        padding: 18px;
        margin-top: 20px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .actions-container h3 {
        color: #5c7cfa;
        margin-bottom: 15px;
        font-size: 20px;
        display: flex;
        align-items: center;
    }
    .actions-container h3::before {
        content: "🔍 ";
        margin-right: 8px;
    }
    /* Adaptations mobiles */
    @media(max-width: 768px) {
        .selected-date-header {
            padding: 12px;
        }
        .selected-date-header h2 {
            font-size: 20px;
        }
        .event-card {
            padding: 12px;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Afficher la date sélectionnée avec un style amélioré
    st.markdown(f"""
    <div class="selected-date-header">
        <h2>📅 {day_name} {selected_date.day} {month_name[selected_date.month]} {selected_date.year}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Vérifier s'il y a des événements pour cette date
    day_events = month_events.get(selected_date, [])
    
    if not day_events:
        st.info("Aucun événement prévu pour cette date.")
    else:
        # Trier les événements par type et ID de projet
        day_events.sort(key=lambda x: (x.get('type', ''), x.get('id', 0)))
        
        # Affichage des événements avec un style adapté au type d'événement
        for event in day_events:
            event_type = event.get('type', 'N/A')
            
            # Déterminer la classe CSS et l'icône selon le type d'événement
            type_class = ""
            type_icon = ""
            type_bg_color = ""
            
            if event_type == 'Début':
                type_class = "type-debut"
                type_icon = "🚀"
                type_bg_color = "#e3f2fd"
            elif event_type == 'Fin Prévue':
                type_class = "type-fin"
                type_icon = "🏁"
                type_bg_color = "#e8f5e9"
            elif event_type == 'Début ST':
                type_class = "type-debut-st"
                type_icon = "▶️"
                type_bg_color = "#fff8e1"
            elif event_type == 'Fin ST':
                type_class = "type-fin-st"
                type_icon = "✅"
                type_bg_color = "#fce4ec"
            
            st.markdown(f"""
            <div class="event-card {type_class}">
                <div class="event-title">{type_icon} #{event.get('id', '?')} - {event.get('nom_projet', 'N/A')}</div>
                <div class="event-type" style="background-color: {type_bg_color};">{event_type}</div>
                <div class="event-details">📝 Tâche: {event.get('tache', 'N/A')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Option pour voir les détails du projet dans un conteneur stylisé
        st.markdown('<div class="actions-container">', unsafe_allow_html=True)
        st.markdown("<h3>Actions</h3>", unsafe_allow_html=True)
        
        # Sélectionner un projet à afficher
        if len(day_events) > 0:
            projects_ids = [event.get('id', '?') for event in day_events]
            projects_names = [f"#{event.get('id', '?')} - {event.get('nom_projet', 'N/A')}" for event in day_events]
            
            selected_proj_index = st.selectbox(
                "Sélectionnez un projet pour voir les détails:",
                range(len(projects_names)),
                format_func=lambda i: projects_names[i]
            )
            
            # Style de bouton amélioré
            button_style = """
            <style>
            div.stButton > button {
                background: linear-gradient(90deg, #a5d8ff 0%, #b2d8d8 100%);
                color: #1a1a1a;
                border: none;
                font-weight: bold;
                transition: all 0.3s;
                font-size: 16px;
                padding: 10px 20px;
                border-radius: 8px;
            }
            div.stButton > button:hover {
                background: linear-gradient(90deg, #88ccff 0%, #99cccc 100%);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
                transform: translateY(-2px);
            }
            div.stButton > button::before {
                content: "🔍 ";
            }
            </style>
            """
            st.markdown(button_style, unsafe_allow_html=True)
            
            if st.button("Voir les détails", use_container_width=is_mobile):
                selected_proj_id = projects_ids[selected_proj_index]
                # Trouver le projet dans les données
                projet = next((p for p in gestionnaire.projets if p.get('id') == selected_proj_id), None)
                if projet:
                    st.session_state.selected_project_id = selected_proj_id
                    st.session_state.selected_project = projet
                    st.session_state.show_project_details = True
        
        st.markdown('</div>', unsafe_allow_html=True)

def display_week_overview(selected_date, month_events, is_mobile=False):
    """Affiche l'aperçu de la semaine avec adaptation mobile."""
    # Calculer le début et la fin de la semaine
    weekday = selected_date.weekday()
    start_of_week = selected_date - timedelta(days=weekday)
    end_of_week = start_of_week + timedelta(days=6)
    
    month_name = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                 "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    
    # Styles améliorés pour l'aperçu de la semaine
    st.markdown("""
    <style>
    .week-header {
        background: linear-gradient(135deg, #e0f7fa 0%, #e8f5e9 100%);
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
        font-weight: bold;
        color: #333;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .week-header h3 {
        margin: 0;
        font-size: 18px;
    }
    .week-event-card {
        padding: 15px;
        margin-bottom: 12px;
        border-radius: 10px;
        background: linear-gradient(to right, #ffffff, #fafafa);
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        border-left: 4px solid #a5d8ff;
        transition: all 0.2s;
        position: relative;
    }
    .week-event-card:hover {
        transform: translateX(3px);
        box-shadow: 0 3px 10px rgba(0,0,0,0.12);
    }
    .week-event-date {
        font-size: 13px;
        color: #666;
        margin-bottom: 5px;
    }
    .week-event-title {
        font-weight: 600;
        margin-bottom: 5px;
        color: #333;
        font-size: 16px;
        display: flex;
        align-items: center;
    }
    .week-event-type {
        font-size: 13px;
        display: inline-block;
        padding: 4px 10px;
        border-radius: 15px;
        background-color: #e3f2fd;
        color: #1976d2;
        margin-top: 5px;
    }
    .week-day-header {
        background-color: #f1f8e9;
        padding: 10px;
        border-radius: 8px;
        margin-top: 15px;
        margin-bottom: 10px;
        font-weight: bold;
        color: #558b2f;
        display: flex;
        align-items: center;
    }
    .week-day-header::before {
        content: "📆 ";
        margin-right: 8px;
    }
    /* Types d'événements avec icônes */
    .type-debut-week {
        border-left-color: #bbdefb;
    }
    .type-debut-week .week-event-title::before {
        content: "🚀 ";
        margin-right: 5px;
    }
    .type-fin-week {
        border-left-color: #c8e6c9;
    }
    .type-fin-week .week-event-title::before {
        content: "🏁 ";
        margin-right: 5px;
    }
    .type-debut-st-week {
        border-left-color: #ffecb3;
    }
    .type-debut-st-week .week-event-title::before {
        content: "▶️ ";
        margin-right: 5px;
    }
    .type-fin-st-week {
        border-left-color: #f8bbd0;
    }
    .type-fin-st-week .week-event-title::before {
        content: "✅ ";
        margin-right: 5px;
    }
    /* Adaptations mobiles */
    @media(max-width: 768px) {
        .week-header {
            padding: 12px;
        }
        .week-header h3 {
            font-size: 16px;
        }
        .week-event-card {
            padding: 12px;
        }
        .week-event-title {
            font-size: 15px;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Afficher l'intervalle de dates avec style amélioré
    st.markdown(f"""
    <div class="week-header">
        <h3>📅 Semaine du {start_of_week.day} {month_name[start_of_week.month]} 
        au {end_of_week.day} {month_name[end_of_week.month]} {end_of_week.year}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Créer un tableau des événements de la semaine
    week_events = []
    current_day = start_of_week
    day_name_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    
    while current_day <= end_of_week:
        day_evts = month_events.get(current_day, [])
        
        for event in day_evts:
            week_events.append({
                "Date": current_day.strftime("%d/%m/%Y"),
                "Jour": day_name_fr[current_day.weekday()],
                "ID": event.get('id', '?'),
                "Projet": event.get('nom_projet', 'N/A'),
                "Type": event.get('type', 'N/A')
            })
        
        current_day += timedelta(days=1)
    
    if not week_events:
        st.info("Aucun événement prévu pour cette semaine.")
        return
    
    # Regrouper par jour pour l'affichage
    days_with_events = {}
    for event in week_events:
        day_key = f"{event['Jour']} {event['Date']}"
        if day_key not in days_with_events:
            days_with_events[day_key] = []
        days_with_events[day_key].append(event)
    
    # Afficher par jour avec style amélioré
    for day_key, day_events in days_with_events.items():
        st.markdown(f'<div class="week-day-header">{day_key}</div>', unsafe_allow_html=True)
        
        for event in day_events:
            event_type = event['Type']
            
            # Couleurs et classes en fonction du type d'événement
            type_class = ""
            type_color = "#e3f2fd"
            text_color = "#1976d2"
            border_color = "#a5d8ff"
            
            if event_type == 'Début':
                type_class = "type-debut-week"
                type_color = "#e3f2fd"
                text_color = "#1976d2"
                border_color = "#bbdefb"
            elif event_type == 'Fin Prévue':
                type_class = "type-fin-week"
                type_color = "#e8f5e9"
                text_color = "#388e3c"
                border_color = "#c8e6c9"
            elif event_type == 'Début ST':
                type_class = "type-debut-st-week"
                type_color = "#fff8e1"
                text_color = "#ffa000"
                border_color = "#ffecb3"
            elif event_type == 'Fin ST':
                type_class = "type-fin-st-week"
                type_color = "#fce4ec"
                text_color = "#c2185b"
                border_color = "#f8bbd0"
            
            st.markdown(f"""
            <div class="week-event-card {type_class}" style="border-left-color: {border_color};">
                <div class="week-event-title">#{event['ID']} - {event['Projet']}</div>
                <div class="week-event-type" style="background-color: {type_color}; color: {text_color};">
                    {event_type}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Graphique pour visualiser la semaine avec couleurs pastels
    if week_events:
        # Regrouper les événements par jour pour voir la charge
        events_by_day = {}
        for event in week_events:
            day_name = event["Jour"]
            if day_name not in events_by_day:
                events_by_day[day_name] = 0
            events_by_day[day_name] += 1
        
        # Créer un graphique en barres pour montrer la charge de travail par jour
        days = day_name_fr  # Pour garantir l'ordre correct
        counts = [events_by_day.get(day, 0) for day in days]
        
        # Couleurs pastels pour le graphique
        pastel_colors = [
            '#a5d8ff' if day != day_name_fr[selected_date.weekday()] else '#b2f2bb' 
            for day in days
        ]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=days if not is_mobile else counts,
            y=counts if not is_mobile else days,
            text=counts,
            textposition='auto',
            name='Nombre d\'événements',
            orientation='v' if not is_mobile else 'h',
            marker_color=pastel_colors,
            marker=dict(
                line=dict(width=1, color='#ffffff')
            )
        ))
        fig.update_layout(
            title={
                'text': "Charge d'événements de la semaine",
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=20, color='#444444')
            },
            xaxis_title="Jour de la semaine" if not is_mobile else "Nombre d'événements",
            yaxis_title="Nombre d'événements" if not is_mobile else "Jour de la semaine",
            height=350 if is_mobile else 400,
            margin=dict(l=10, r=10, t=50, b=20) if is_mobile else dict(l=20, r=20, t=80, b=50),
            bargap=0.2,
            plot_bgcolor='rgba(247, 249, 252, 0.8)',
            paper_bgcolor='rgba(247, 249, 252, 0)',
            font=dict(family="Arial, sans-serif", size=12, color="#444444")
        )
        
        st.plotly_chart(fig, use_container_width=True)

def get_month_calendar(year, month):
    """Retourne une matrice représentant le calendrier du mois."""
    cal = calendar.monthcalendar(year, month)
    
    # Ajouter les noms des jours de la semaine
    days_of_week = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    
    return cal, days_of_week

def get_events_for_month(year, month, gestionnaire):
    """Récupère tous les événements pour le mois donné."""
    events = {}
    
    # Déterminer la plage de dates du mois
    _, last_day = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)
    
    # Étendre légèrement pour voir les jours adjacents des mois voisins
    start_date_extended = start_date - timedelta(days=7)
    end_date_extended = end_date + timedelta(days=7)
    
    # Parcourir les projets pour trouver les dates
    for projet in gestionnaire.projets:
        proj_id = projet.get('id')
        proj_nom = projet.get('nom_projet', 'N/A')
        
        # Vérifier la date de début
        try:
            date_debut_str = projet.get('date_soumis')
            if date_debut_str:
                date_debut = datetime.strptime(date_debut_str, "%Y-%m-%d").date()
                if start_date_extended <= date_debut <= end_date_extended:
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
                if start_date_extended <= date_fin <= end_date_extended:
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
        
        # Vérifier les sous-tâches
        for st in projet.get('sous_taches', []):
            # Date début sous-tâche
            try:
                st_debut_str = st.get('date_debut')
                if st_debut_str:
                    st_debut = datetime.strptime(st_debut_str, "%Y-%m-%d").date()
                    if start_date_extended <= st_debut <= end_date_extended:
                        if st_debut not in events:
                            events[st_debut] = []
                        events[st_debut].append({
                            'id': proj_id,
                            'nom_projet': f"{proj_nom} - ST{st.get('id')}: {st.get('nom', 'N/A')}",
                            'type': 'Début ST',
                            'tache': st.get('nom', 'N/A')
                        })
            except (ValueError, TypeError):
                pass
            
            # Date fin sous-tâche
            try:
                st_fin_str = st.get('date_fin')
                if st_fin_str:
                    st_fin = datetime.strptime(st_fin_str, "%Y-%m-%d").date()
                    if start_date_extended <= st_fin <= end_date_extended:
                        if st_fin not in events:
                            events[st_fin] = []
                        events[st_fin].append({
                            'id': proj_id,
                            'nom_projet': f"{proj_nom} - ST{st.get('id')}: {st.get('nom', 'N/A')}",
                            'type': 'Fin ST',
                            'tache': st.get('nom', 'N/A')
                        })
            except (ValueError, TypeError):
                pass
    
    return events

def show_project_details():
    # Style amélioré pour les détails du projet
    st.markdown("""
    <style>
    .project-header {
        background: linear-gradient(135deg, #bbdefb 0%, #c8e6c9 100%);
        padding: 18px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
    }
    .project-header h2 {
        margin: 0;
        color: #333;
        font-size: 22px;
        display: flex;
        align-items: center;
    }
    .project-header h2::before {
        content: "📁 ";
        margin-right: 10px;
    }
    .info-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: all 0.3s;
    }
    .info-card:hover {
        background-color: #f0f7ff;
        box-shadow: 0 3px 8px rgba(0,0,0,0.08);
    }
    .info-label {
        font-weight: bold;
        color: #555;
        margin-bottom: 5px;
        font-size: 14px;
    }
    .info-value {
        color: #333;
        font-size: 16px;
    }
    .tab-custom {
        border-radius: 8px 8px 0 0;
        padding: 10px;
    }
    .tab-content {
        background-color: #ffffff;
        border-radius: 0 0 8px 8px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-top: -5px;
    }
    div[data-testid="stTabs"] > div[data-baseweb="tab-list"] {
        gap: 8px;
    }
    div[data-testid="stTabs"] > div[data-baseweb="tab-list"] > button[data-baseweb="tab"] {
        background-color: #f0f7ff;
        border-radius: 8px 8px 0 0;
        border-bottom: none;
        padding: 8px 16px;
        font-weight: 600;
    }
    div[data-testid="stTabs"] > div[data-baseweb="tab-list"] > button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #a5d8ff;
        color: #0056b3;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Récupérer le projet sélectionné
    projet_id = st.session_state.selected_project_id
    projet = st.session_state.selected_project
    gestionnaire = st.session_state.gestionnaire
    
    # Entête du projet
    st.markdown(f"""
    <div class="project-header">
        <h2>Projet #{projet_id}: {projet.get('nom_projet', 'Sans Nom')}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    tabs = st.tabs(["📊 Informations", "📝 Sous-tâches", "📎 Documents"])
    
    with tabs[0]:  # Informations
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div class="info-card">
                <div class="info-label">👤 Client:</div>
                <div class="info-value">{projet.get('client', 'N/A')}</div>
            </div>
            <div class="info-card">
                <div class="info-label">🚦 Statut:</div>
                <div class="info-value">{projet.get('statut', 'N/A')}</div>
            </div>
            <div class="info-card">
                <div class="info-label">⭐ Priorité:</div>
                <div class="info-value">{projet.get('priorite', 'N/A')}</div>
            </div>
            <div class="info-card">
                <div class="info-label">✅ Tâche:</div>
                <div class="info-value">{projet.get('tache', 'N/A')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="info-card">
                <div class="info-label">🚀 Date Début:</div>
                <div class="info-value">{projet.get('date_soumis', 'N/A')}</div>
            </div>
            <div class="info-card">
                <div class="info-label">🏁 Date Fin Prévue:</div>
                <div class="info-value">{projet.get('date_prevu', 'N/A')}</div>
            </div>
            <div class="info-card">
                <div class="info-label">📊 BD-FT Estimé:</div>
                <div class="info-value">{projet.get('bd_ft_estime', 'N/A')}</div>
            </div>
            <div class="info-card">
                <div class="info-label">💰 Prix Estimé:</div>
                <div class="info-value">{projet.get('prix_estime', 'N/A')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<div class='info-card'>", unsafe_allow_html=True)
        st.markdown("<div class='info-label'>📝 Description:</div>", unsafe_allow_html=True)
        st.text_area("", value=projet.get('description', '(Aucune description)'), height=100, disabled=True, label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Bouton pour analyser le projet avec l'IA
        st.markdown("""
        <style>
        .ai-button {
            background: linear-gradient(90deg, #c5e1a5 0%, #aed581 100%);
            border: none;
            padding: 10px 15px;
            border-radius: 8px;
            color: #33691e;
            font-weight: bold;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.3s;
        }
        .ai-button:hover {
            background: linear-gradient(90deg, #aed581 0%, #9ccc65 100%);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            transform: translateY(-2px);
        }
        div.stButton > button:has(span:contains("Analyser")) {
            background: linear-gradient(90deg, #c5e1a5 0%, #aed581 100%) !important;
            color: #33691e !important;
        }
        div.stButton > button:has(span:contains("Analyser"))::before {
            content: "🧠 " !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        ai_button_container = st.container()
        with ai_button_container:
            if st.button("Analyser avec IA", use_container_width=True):
                if 'ai_assistant' in st.session_state and st.session_state.ai_assistant:
                    with st.spinner("Analyse en cours..."):
                        analyse = st.session_state.ai_assistant.analyze_project_data(projet)
                        st.markdown("""
                        <div style="background: linear-gradient(to right, #f0f7ff, #e6f3ff); 
                                    padding: 15px; border-radius: 10px; 
                                    border-left: 4px solid #4285f4;
                                    box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                        <h3 style="color: #4285f4; display: flex; align-items: center;"><span style="margin-right: 8px;">🧠</span> Analyse IA</h3>
                        """, unsafe_allow_html=True)
                        st.markdown(analyse)
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.warning("Assistant IA non disponible. Vérifiez la clé API.")
    
    with tabs[1]:  # Sous-tâches
        sous_taches = projet.get('sous_taches', [])
        
        if not sous_taches:
            st.info("Aucune sous-tâche pour ce projet.")
        else:
            # Style pour le tableau des sous-tâches
            st.markdown("""
            <style>
            .dataframe {
                border-collapse: separate !important;
                border-spacing: 0 !important;
                border-radius: 10px !important;
                overflow: hidden !important;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
            }
            .dataframe th {
                background-color: #edf2ff !important;
                color: #5c7cfa !important;
                font-weight: bold !important;
                text-align: left !important;
                padding: 12px 15px !important;
            }
            .dataframe td {
                padding: 10px 15px !important;
                border-bottom: 1px solid #f0f0f0 !important;
            }
            .dataframe tr:nth-child(even) {
                background-color: #f8f9fa !important;
            }
            .dataframe tr:hover {
                background-color: #e6f0ff !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Tableau des sous-tâches
            st_data = []
            for st in sous_taches:
                st_data.append({
                    "ID": f"ST{st.get('id', '?')}",
                    "Nom": st.get('nom', 'N/A'),
                    "Statut": st.get('statut', 'N/A'),
                    "Date Début": st.get('date_debut', 'N/A'),
                    "Date Fin": st.get('date_fin', 'N/A'),
                    "Description": st.get('description', '')
                })
            
            st_df = pd.DataFrame(st_data)
            st.dataframe(st_df, use_container_width=True)
    
    with tabs[2]:  # Documents
        documents = projet.get('documents', [])
        
        if not documents:
            st.info("Aucun document lié à ce projet.")
        else:
            # Tableau des documents
            doc_data = []
            for doc in documents:
                doc_data.append({
                    "Type": doc.get('type', 'N/A'),
                    "Nom": doc.get('nom', 'N/A'),
                    "Date": doc.get('date', 'N/A'),
                    "Taille": doc.get('taille', 'N/A')
                })
            
            doc_df = pd.DataFrame(doc_data)
            st.dataframe(doc_df, use_container_width=True)
    
    # Bouton pour fermer
    st.markdown("""
    <style>
    .close-button {
        margin-top: 20px;
    }
    div.stButton > button:has(span:contains("Fermer")) {
        background: linear-gradient(90deg, #ffcdd2 0%, #ef9a9a 100%) !important;
        color: #b71c1c !important;
    }
    div.stButton > button:has(span:contains("Fermer"))::before {
        content: "✖️ " !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        if st.button("Fermer", use_container_width=True, key="btn_close_details"):
            st.session_state.show_project_details = False
            st.experimental_rerun()

def app():
    # Style global de l'application
    st.markdown("""
    <style>
    /* Styles globaux */
    .main-title {
        background: linear-gradient(135deg, #a5d8ff 0%, #ffd6e0 100%);
        padding: 20px;
        border-radius: 12px;
        color: #333;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
    }
    .main-title h1 {
        margin: 0;
        font-size: 28px;
        font-weight: 600;
    }
    
    /* Navigation améliorée */
    .nav-button {
        border-radius: 8px;
        border: none;
        padding: 10px 15px;
        font-weight: 600;
        background: linear-gradient(135deg, #e0f7fa 0%, #e8f5e9 100%);
        color: #333;
        transition: all 0.3s;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .nav-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* Améliorations mobiles */
    @media(max-width: 768px) {
        .main-title {
            padding: 15px;
            margin-bottom: 15px;
        }
        .main-title h1 {
            font-size: 24px;
        }
    }
    
    /* Style général pour les boutons Streamlit */
    div.stButton > button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.3s !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
    }
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
    }
    
    /* Style pour les expanders */
    div.streamlit-expanderHeader {
        background-color: #f7f9fc !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        color: #5c7cfa !important;
    }
    div.streamlit-expanderContent {
        background-color: #ffffff !important;
        border-radius: 0 0 8px 8px !important;
        padding: 15px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important;
    }
    
    /* Style pour les selecboxes */
    div[data-baseweb="select"] {
        border-radius: 8px !important;
    }
    
    /* Style pour les info boxes */
    div.stAlert {
        border-radius: 8px !important;
        padding: 12px 15px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Titre avec style amélioré
    st.markdown('<div class="main-title"><h1>📅 Vue Calendrier</h1></div>', unsafe_allow_html=True)
    
    # Récupérer le gestionnaire des données de session
    if 'gestionnaire' not in st.session_state:
        st.session_state.gestionnaire = GestionnaireProjetIA()
    
    gestionnaire = st.session_state.gestionnaire
    
    # Initialiser la date sélectionnée si nécessaire
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = datetime.now().date()
    
    if 'view_month' not in st.session_state:
        st.session_state.view_month = datetime.now().month
        
    if 'view_year' not in st.session_state:
        st.session_state.view_year = datetime.now().year
    
    # Détection d'appareil mobile (via CSS et JavaScript)
    st.markdown("""
    <style>
    .mobile-indicator {display: none;}
    @media(max-width: 768px) {
        .mobile-indicator {display: block;}
        .desktop-only {display: none !important;}
        .mobile-only {display: block !important;}
        /* Améliorer la taille des boutons sur mobile */
        button {min-height: 44px !important; font-size: 16px !important;}
        /* Réduire les marges sur mobile */
        .block-container {padding-left: 1rem !important; padding-right: 1rem !important;}
    }
    .mobile-only {display: none;}
    </style>
    <div class="mobile-indicator"></div>
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        const isMobile = window.innerWidth <= 768;
        const mobileIndicator = document.querySelector('.mobile-indicator');
        if (mobileIndicator) {
            mobileIndicator.setAttribute('data-is-mobile', isMobile);
        }
    });
    </script>
    """, unsafe_allow_html=True)
    
    # Vérifier si on est sur mobile
    is_mobile = is_mobile_device()
    
    # Options dans la sidebar
    st.sidebar.markdown("""
    <div style="background: linear-gradient(135deg, #e0f7fa 0%, #e8f5e9 100%); 
                padding: 15px; border-radius: 10px; margin-bottom: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
        <h3 style="color: #333; text-align: center; margin: 0;">📌 Navigation</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Mois et année actuellement visibles
    current_month = st.session_state.view_month
    current_year = st.session_state.view_year
    
    # Navigation par mois - version améliorée pour mobile
    month_name_fr = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    
    # Style pour les boutons de navigation
    nav_button_style = """
    <style>
    .month-nav-button {
        background: linear-gradient(90deg, #e3f2fd 0%, #bbdefb 100%);
        color: #1976d2;
        border: none;
        border-radius: 8px;
        padding: 10px 15px;
        margin: 5px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: all 0.3s;
        font-weight: bold;
    }
    .month-nav-button:hover {
        background: linear-gradient(90deg, #bbdefb 0%, #90caf9 100%);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        transform: translateY(-2px);
    }
    .today-button {
        background: linear-gradient(90deg, #e8f5e9 0%, #c8e6c9 100%);
        color: #388e3c;
    }
    .today-button:hover {
        background: linear-gradient(90deg, #c8e6c9 0%, #a5d6a7 100%);
    }
    
    /* Style pour les boutons de navigation standard */
    div.stButton > button:has(span:contains("◀️")), 
    div.stButton > button:has(span:contains("▶️")) {
        background: linear-gradient(90deg, #e3f2fd 0%, #bbdefb 100%) !important;
        color: #1976d2 !important;
        font-weight: bold !important;
        padding: 8px 12px !important;
        min-width: 50px !important;
    }
    div.stButton > button:has(span:contains("Aujourd'hui")) {
        background: linear-gradient(90deg, #e8f5e9 0%, #c8e6c9 100%) !important;
        color: #388e3c !important;
        font-weight: bold !important;
    }
    </style>
    """
    st.markdown(nav_button_style, unsafe_allow_html=True)
    
    # Navigation principale - affichage adaptatif
    if is_mobile:
        # Version mobile: navigation verticale
        st.markdown(f"""
        <div style="text-align: center; background: linear-gradient(135deg, #e0f7fa 0%, #e8f5e9 100%);
                     padding: 12px; border-radius: 10px; margin-bottom: 15px; 
                     box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <h3 style="margin: 0; color: #333; font-weight: 600;">{month_name_fr[current_month]} {current_year}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        nav_cols = st.columns([1, 1, 1])
        
        with nav_cols[0]:
            if st.button("◀️", key="prev_month_mobile", help="Mois précédent"):
                if current_month == 1:
                    st.session_state.view_month = 12
                    st.session_state.view_year = current_year - 1
                else:
                    st.session_state.view_month = current_month - 1
                st.experimental_rerun()
                
        with nav_cols[1]:
            if st.button("📅 Aujourd'hui", key="today_mobile"):
                today = datetime.now().date()
                st.session_state.view_month = today.month
                st.session_state.view_year = today.year
                st.session_state.selected_date = today
                st.experimental_rerun()
                
        with nav_cols[2]:
            if st.button("▶️", key="next_month_mobile", help="Mois suivant"):
                if current_month == 12:
                    st.session_state.view_month = 1
                    st.session_state.view_year = current_year + 1
                else:
                    st.session_state.view_month = current_month + 1
                st.experimental_rerun()
    else:
        # Version desktop: navigation horizontale
        col1, col2, col3 = st.sidebar.columns([1, 2, 1])
        
        with col1:
            if st.button("◀️", key="prev_month_desktop"):
                if current_month == 1:
                    st.session_state.view_month = 12
                    st.session_state.view_year = current_year - 1
                else:
                    st.session_state.view_month = current_month - 1
                st.experimental_rerun()
        
        with col2:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #e0f7fa 0%, #e8f5e9 100%);
                        padding: 10px; border-radius: 8px; text-align: center;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.08);">
                <h3 style="margin: 0;">{month_name_fr[current_month]} {current_year}</h3>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            if st.button("▶️", key="next_month_desktop"):
                if current_month == 12:
                    st.session_state.view_month = 1
                    st.session_state.view_year = current_year + 1
                else:
                    st.session_state.view_month = current_month + 1
                st.experimental_rerun()
        
        # Bouton Aujourd'hui dans la sidebar pour version desktop
        if st.sidebar.button("📅 Aujourd'hui", key="today_desktop"):
            today = datetime.now().date()
            st.session_state.view_month = today.month
            st.session_state.view_year = today.year
            st.session_state.selected_date = today
            st.experimental_rerun()
    
    # Récupérer les événements pour le mois en cours
    month_events = get_events_for_month(current_year, current_month, gestionnaire)
    
    # Layout principal - adaptation mobile/desktop
    if is_mobile:
        # Sur mobile, calendrier et détails s'affichent en sections verticales
        with st.expander("📅 Calendrier du mois", expanded=True):
            display_mini_calendar(current_year, current_month, get_month_calendar, month_events, is_mobile=True)
            
        # Détails du jour sélectionné
        display_day_details(st.session_state.selected_date, month_events, is_mobile=True, gestionnaire=gestionnaire)
        
        # Section semaine compacte
        with st.expander("📊 Aperçu de la semaine", expanded=False):
            display_week_overview(st.session_state.selected_date, month_events, is_mobile=True)
    else:
        # Sur desktop, disposition en colonnes horizontales
        col_miniCal, col_events = st.columns([1, 3])
        
        with col_miniCal:
            st.markdown("""
            <div style="background-color: #f7f9fc; padding: 12px; border-radius: 10px; margin-bottom: 20px; 
                       box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                <h3 style="text-align: center; color: #5c7cfa; margin: 0;">📅 Navigation</h3>
            </div>
            """, unsafe_allow_html=True)
            display_mini_calendar(current_year, current_month, get_month_calendar, month_events)
        
        with col_events:
            display_day_details(st.session_state.selected_date, month_events, gestionnaire=gestionnaire)
            st.markdown("<hr style='margin: 25px 0; border: none; height: 1px; background-color: #e0e0e0;'>", unsafe_allow_html=True)
            st.subheader("📊 Aperçu de la semaine")
            display_week_overview(st.session_state.selected_date, month_events)

# Modal pour les détails du projet
if 'show_project_details' in st.session_state and st.session_state.show_project_details:
    show_project_details()

if __name__ == "__main__":
    app()