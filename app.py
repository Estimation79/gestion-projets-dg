# app.py - ERP Production DG Inc. avec Portail d'Entrée Intégré
# VERSION COMPLÈTE : Portail d'authentification + ERP complet original + CSS externe
# Architecture : Portail → Authentification → ERP Production DG Inc. COMPLET
# ARCHITECTURE UNIFIÉE : TimeTracker + Postes de Travail fusionnés
# SANS ASSISTANT IA

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
import hashlib
from math import gcd
from fractions import Fraction

# ========================
# CHARGEMENT DU CSS EXTERNE (NOUVEAU)
# ========================

def load_external_css():
    """Charge le fichier CSS externe pour un design uniforme"""
    try:
        st.dataframe(pd.DataFrame(data_iti), use_container_width=True)

        st.markdown("---")
        st.markdown("##### 📈 Analyse Opérations")
        ac1, ac2 = st.columns(2)

        TEXT_COLOR_CHARTS = 'var(--text-color)'

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

def show_nomenclature():
    st.markdown("### 📊 Nomenclature (BOM)")
    gestionnaire = st.session_state.gestionnaire

    if not gestionnaire.projets:
        st.warning("Aucun projet disponible.")
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
        st.info("Aucun matériau défini.")
    else:
        total_cost = 0
        data_bom = []
        for item in materiaux:
            qty, price = item.get('quantite', 0) or 0, item.get('prix_unitaire', 0) or 0
            total = qty * price
            total_cost += total
            data_bom.append({
                '🆔': item.get('id', '?'),
                '📝 Code': item.get('code', ''),
                '📋 Désignation': item.get('designation', 'N/A'),
                '📊 Qté': f"{qty} {item.get('unite', '')}",
                '💳 PU': format_currency(price),
                '💰 Total': format_currency(total),
                '🏪 Fourn.': item.get('fournisseur', 'N/A')
            })

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

            TEXT_COLOR_CHARTS = 'var(--text-color)'
            fig = px.pie(values=costs, names=labels, title="Répartition coûts par matériau")
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT_COLOR_CHARTS), legend_title_text='', title_x=0.5)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

def show_gantt():
    st.markdown("### 📈 Diagramme de Gantt")
    gestionnaire = st.session_state.gestionnaire
    crm_manager = st.session_state.gestionnaire_crm

    if not gestionnaire.projets:
        st.info("Aucun projet disponible pour le Gantt.")
        return

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    gantt_data = []
    for p in gestionnaire.projets:
        try:
            s_date = datetime.strptime(p.get('date_soumis', ''), "%Y-%m-%d") if p.get('date_soumis') else None
            e_date = datetime.strptime(p.get('date_prevu', ''), "%Y-%m-%d") if p.get('date_prevu') else None

            if s_date and e_date:
                client_display_name_gantt = p.get('client_nom_cache', 'N/A')
                if client_display_name_gantt == 'N/A' and p.get('client_company_id'):
                    entreprise = crm_manager.get_entreprise_by_id(p.get('client_company_id'))
                    if entreprise:
                        client_display_name_gantt = entreprise.get('nom', 'N/A')
                elif client_display_name_gantt == 'N/A':
                    client_display_name_gantt = p.get('client_legacy', 'N/A')

                gantt_data.append({
                    'Projet': f"#{p.get('id')} - {p.get('nom_projet', 'N/A')}",
                    'Début': s_date,
                    'Fin': e_date,
                    'Client': client_display_name_gantt,
                    'Statut': p.get('statut', 'N/A'),
                    'Priorité': p.get('priorite', 'N/A')
                })
        except:
            continue

    if not gantt_data:
        st.warning("Données de dates invalides pour le Gantt.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    df_gantt = pd.DataFrame(gantt_data)
    colors_gantt = {'À FAIRE': '#f59e0b', 'EN COURS': '#3b82f6', 'EN ATTENTE': '#ef4444', 'TERMINÉ': '#10b981', 'ANNULÉ': '#6b7280', 'LIVRAISON': '#8b5cf6'}

    TEXT_COLOR_CHARTS = 'var(--text-color)'

    fig = px.timeline(
        df_gantt,
        x_start="Début",
        x_end="Fin",
        y="Projet",
        color="Statut",
        color_discrete_map=colors_gantt,
        title="📊 Planning Projets",
        hover_data=['Client', 'Priorité']
    )

    fig.update_layout(
        height=max(400, len(gantt_data) * 40),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color=TEXT_COLOR_CHARTS),
        xaxis=dict(title="📅 Calendrier", gridcolor='rgba(0,0,0,0.05)'),
        yaxis=dict(title="📋 Projets", gridcolor='rgba(0,0,0,0.05)', categoryorder='total ascending'),
        title_x=0.5,
        legend_title_text=''
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("##### 📊 Statistiques Planning")
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
    st.markdown("### 📅 Vue Calendrier")
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

    # Préparation des données depuis SQLite
    events_by_date = {}
    for p in gestionnaire.projets:
        try:
            s_date_obj = datetime.strptime(p.get('date_soumis', ''), "%Y-%m-%d").date() if p.get('date_soumis') else None
            e_date_obj = datetime.strptime(p.get('date_prevu', ''), "%Y-%m-%d").date() if p.get('date_prevu') else None

            client_display_name_cal = p.get('client_nom_cache', 'N/A')
            if client_display_name_cal == 'N/A':
                 client_display_name_cal = p.get('client_legacy', 'N/A')

            if s_date_obj:
                if s_date_obj not in events_by_date:
                    events_by_date[s_date_obj] = []
                events_by_date[s_date_obj].append({
                    'type': '🚀 Début',
                    'projet': p.get('nom_projet', 'N/A'),
                    'id': p.get('id'),
                    'client': client_display_name_cal,
                    'color_class': 'event-type-debut'
                })
            if e_date_obj:
                if e_date_obj not in events_by_date:
                    events_by_date[e_date_obj] = []
                events_by_date[e_date_obj].append({
                    'type': '🏁 Fin',
                    'projet': p.get('nom_projet', 'N/A'),
                    'id': p.get('id'),
                    'client': client_display_name_cal,
                    'color_class': 'event-type-fin'
                })
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
    st.markdown("### 🔄 Vue Kanban (Style Planner)")
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
            (p.get('client_company_id') and crm_manager.get_entreprise_by_id(p.get('client_company_id')) and terme in crm_manager.get_entreprise_by_id(p.get('client_company_id')).get('nom', '').lower()) or
            terme in str(p.get('client_legacy', '')).lower()
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

    # Créer colonnes pour chaque statut
    cols = st.columns(len(statuts_k))

    for idx, sk in enumerate(statuts_k):
        with cols[idx]:
            # En-tête de la colonne
            st.markdown(f"""
            <div class="kanban-column" style="border-top: 4px solid {col_borders_k.get(sk, '#ccc')};">
                <div class="kanban-header">{sk} ({len(projs_by_statut[sk])})</div>
            </div>
            """, unsafe_allow_html=True)

            # Si un projet est "soulevé", afficher une zone de dépôt
            if st.session_state.dragged_project_id and sk != st.session_state.dragged_from_status:
                if st.button(f"⤵️ Déposer ici", key=f"drop_in_{sk}", use_container_width=True, help=f"Déplacer vers {sk}"):
                    proj_id_to_move = st.session_state.dragged_project_id
                    if gestionnaire.modifier_projet(proj_id_to_move, {'statut': sk}):
                        st.success(f"Projet #{proj_id_to_move} déplacé vers '{sk}' !")
                    else:
                        st.error("Erreur lors du déplacement.")

                    st.session_state.dragged_project_id = None
                    st.session_state.dragged_from_status = None
                    st.rerun()

            # Zone pour les cartes
            if not projs_by_statut[sk]:
                st.markdown("<div style='text-align:center; color:var(--text-color-muted); margin-top:2rem;'><i>Vide</i></div>", unsafe_allow_html=True)

            for pk in projs_by_statut[sk]:
                prio_k = pk.get('priorite', 'MOYEN')
                card_borders_k = {'ÉLEVÉ': '#ef4444', 'MOYEN': '#f59e0b', 'BAS': '#10b981'}
                prio_icons_k = {'ÉLEVÉ': '🔴', 'MOYEN': '🟡', 'BAS': '🟢'}

                client_display_name_kanban = pk.get('client_nom_cache', 'N/A')
                if client_display_name_kanban == 'N/A' and pk.get('client_company_id'):
                    entreprise = crm_manager.get_entreprise_by_id(pk.get('client_company_id'))
                    client_display_name_kanban = entreprise.get('nom', 'N/A') if entreprise else 'N/A'
                elif client_display_name_kanban == 'N/A':
                    client_display_name_kanban = pk.get('client_legacy', 'N/A')

                # Affichage de la carte
                st.markdown(f"""
                <div class='kanban-card' style='border-left-color:{card_borders_k.get(prio_k, 'var(--border-color)')};'>
                    <div class='kanban-card-title'>#{pk.get('id')} - {pk.get('nom_projet', 'N/A')}</div>
                    <div class='kanban-card-info'>👤 {client_display_name_kanban}</div>
                    <div class='kanban-card-info'>{prio_icons_k.get(prio_k, '⚪')} {prio_k}</div>
                    <div class='kanban-card-info'>💰 {format_currency(pk.get('prix_estime', 0))}</div>
                </div>
                """, unsafe_allow_html=True)

                # Boutons d'action pour la carte - MODIFIÉ avec BT et BA
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("👁️", key=f"view_kanban_{pk['id']}", help="Voir les détails", use_container_width=True):
                        st.session_state.selected_project = pk
                        st.session_state.show_project_modal = True
                        st.rerun()
                with col2:
                    # NOUVEAU : Bouton création BT dans Kanban
                    if st.button("🔧", key=f"bt_kanban_{pk['id']}", help="Créer Bon de Travail", use_container_width=True):
                        st.session_state.form_action = "create_bon_travail"
                        st.session_state.formulaire_project_preselect = pk['id']
                        st.session_state.page_redirect = "formulaires_page"
                        st.rerun()
                with col3:
                    # NOUVEAU : Bouton création BA dans Kanban
                    if st.button("🛒", key=f"ba_kanban_{pk['id']}", help="Créer Bon d'Achat", use_container_width=True):
                        st.session_state.form_action = "create_bon_achat"
                        st.session_state.formulaire_project_preselect = pk['id']
                        st.session_state.page_redirect = "formulaires_page"
                        st.rerun()
                with col4:
                    if st.button("➡️", key=f"move_kanban_{pk['id']}", help="Déplacer ce projet", use_container_width=True):
                        st.session_state.dragged_project_id = pk['id']
                        st.session_state.dragged_from_status = sk
                        st.rerun()

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
                <p><strong>👤 Client:</strong> {proj_mod.get('client_nom_cache', 'N/A')}</p>
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
                st.info("Aucune sous-tâche définie.")
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
                st.info("Aucun matériau défini.")
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
                st.info("Aucune opération définie.")
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

def show_footer():
    st.markdown("---")
    footer_text = "🏭 ERP Production DG Inc. - Architecture Unifiée • ⏱️🏭 TimeTracker & Postes Intégrés • CRM • Inventaire • 📑 Formulaires • 🏪 Fournisseurs"
    if TIMETRACKER_AVAILABLE:
        footer_text += " • ✅ Module Unifié Actif"

    # NOUVEAU : Ajouter info stockage persistant dans footer principal
    if 'storage_manager' in st.session_state and st.session_state.storage_manager:
        storage_info = st.session_state.storage_manager.get_storage_info()
        if storage_info['environment_type'] == 'RENDER_PERSISTENT':
            footer_text += " • 💾 Stockage Persistant Render"
        elif storage_info['environment_type'] == 'RENDER_EPHEMERAL':
            footer_text += " • ⚠️ Mode Temporaire"

    st.markdown(f"<div style='text-align:center;color:var(--text-color-muted);padding:20px 0;font-size:0.9em;'><p>{footer_text}</p><p>🗄️ Architecture Unifiée TimeTracker ↔ Postes • Module Formulaires Intégré • Gestion Fournisseurs Complète • Stockage Persistant Render • 🔄 Navigation Fluide</p></div>", unsafe_allow_html=True)

# ========================
# ERP PRINCIPAL AVEC PORTAIL (INTÉGRATION COMPLÈTE)
# ========================

def show_erp_main():
    """ERP principal avec authentification et permissions"""
    # Initialiser l'ERP
    init_erp_system()

    # Header admin
    show_admin_header()

    # Permissions utilisateur
    permissions = st.session_state.get('admin_permissions', [])
    has_all_permissions = "ALL" in permissions

    # NAVIGATION PRINCIPALE avec permissions
    available_pages = {}

    # Pages toujours disponibles
    available_pages["🏠 Tableau de Bord"] = "dashboard"

    # Pages selon permissions
    if has_all_permissions or "projects" in permissions:
        available_pages["📋 Liste des Projets"] = "liste"
        available_pages["🛠️ Itinéraire"] = "routing"
        available_pages["📊 Nomenclature (BOM)"] = "bom"
        available_pages["📈 Vue Gantt"] = "gantt"
        available_pages["📅 Calendrier"] = "calendrier"
        available_pages["🔄 Kanban"] = "kanban"

    if has_all_permissions or "crm" in permissions:
        available_pages["🤝 CRM"] = "crm_page"

    if has_all_permissions or "employees" in permissions:
        available_pages["👥 Employés"] = "employees_page"

    if has_all_permissions or "fournisseurs" in permissions:
        available_pages["🏪 Fournisseurs"] = "fournisseurs_page"

    if has_all_permissions or "formulaires" in permissions:
        available_pages["📑 Formulaires"] = "formulaires_page"

    if has_all_permissions or "timetracker" in permissions or "work_centers" in permissions:
        available_pages["⏱️🏭 TimeTracker & Postes"] = "timetracker_unified_page"

    if has_all_permissions or "inventory" in permissions:
        available_pages["📦 Gestion Inventaire"] = "inventory_management"

    # Navigation dans la sidebar
    st.sidebar.markdown("### 🧭 Navigation ERP")

    # Bouton déconnexion
    if st.sidebar.button("🚪 Se Déconnecter", use_container_width=True):
        st.session_state.admin_authenticated = False
        st.session_state.admin_username = None
        st.session_state.admin_login_time = None
        st.session_state.admin_permissions = []
        st.session_state.app_mode = "portal"
        st.rerun()

    st.sidebar.markdown("---")

    # Menu de navigation
    sel_page_key = st.sidebar.radio("Menu Principal:", list(available_pages.keys()), key="main_nav_radio")
    page_to_show_val = available_pages[sel_page_key]

    # GESTION SIDEBAR SELON CONTEXTE
    if page_to_show_val == "inventory_management":
        st.sidebar.markdown("---")
        st.sidebar.markdown("<h4 style='color:var(--primary-color-darker);'>Actions Inventaire</h4>", unsafe_allow_html=True)
        st.session_state.inv_action_mode = st.sidebar.radio(
            "Mode:",
            ["Voir Liste", "Ajouter Article", "Modifier Article"],
            key="inv_action_mode_selector",
            index=["Voir Liste", "Ajouter Article", "Modifier Article"].index(st.session_state.get('inv_action_mode', "Voir Liste"))
        )

    st.sidebar.markdown("---")

    # NOUVEAU : Affichage du statut de stockage persistant dans la sidebar
    show_storage_status_sidebar()

    # Statistiques dans la sidebar
    try:
        total_projects_sql = st.session_state.erp_db.get_table_count('projects')
        total_companies = st.session_state.erp_db.get_table_count('companies')
        total_employees = st.session_state.erp_db.get_table_count('employees')
        total_work_centers = st.session_state.erp_db.get_table_count('work_centers')

        st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>📊 Base de Données</h3>", unsafe_allow_html=True)
        st.sidebar.metric("Base: Projets", total_projects_sql)
        st.sidebar.metric("Base: Entreprises", total_companies)
        st.sidebar.metric("Base: Employés", total_employees)
        st.sidebar.metric("Base: Postes", total_work_centers)

        # Informations sur la base
        schema_info = st.session_state.erp_db.get_schema_info()
        if schema_info['file_size_mb'] > 0:
            st.sidebar.metric("Base: Taille", f"{schema_info['file_size_mb']} MB")
            st.sidebar.metric("Base: Total", f"{schema_info['total_records']}")

    except Exception:
        pass

    # NOUVEAU : Statistiques Formulaires dans la sidebar
    try:
        if 'gestionnaire_formulaires' in st.session_state:
            form_stats = st.session_state.gestionnaire_formulaires.get_statistiques_formulaires()
            total_formulaires = sum(
                type_stats.get('total', 0)
                for type_stats in form_stats.values()
                if isinstance(type_stats, dict)
            )

            if total_formulaires > 0:
                st.sidebar.markdown("---")
                st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>📑 Formulaires</h3>", unsafe_allow_html=True)
                st.sidebar.metric("Total Documents", total_formulaires)

                # Formulaires en attente
                en_attente = form_stats.get('en_attente_validation', 0)
                if en_attente > 0:
                    st.sidebar.metric("⏳ En Attente", en_attente)

                # Formulaires en retard
                en_retard = form_stats.get('en_retard', 0)
                if en_retard > 0:
                    st.sidebar.metric("🚨 En Retard", en_retard)

                # ÉTAPE 4 : Navigation vers TimeTracker depuis Formulaires
                if TIMETRACKER_AVAILABLE and st.sidebar.button("⏱️ Aller au TimeTracker", key="nav_to_tt", use_container_width=True):
                    st.session_state.page_redirect = "timetracker_page"
                    st.session_state.navigation_message = "⏱️ Redirection vers TimeTracker..."
                    st.rerun()

    except Exception:
        pass  # Silencieux si erreur

    # NOUVEAU : Statistiques Fournisseurs dans la sidebar
    try:
        if 'gestionnaire_fournisseurs' not in st.session_state:
            st.session_state.gestionnaire_fournisseurs = GestionnaireFournisseurs(st.session_state.erp_db)

        fournisseurs_stats = st.session_state.gestionnaire_fournisseurs.get_fournisseurs_statistics()

        if fournisseurs_stats and fournisseurs_stats.get('total_fournisseurs', 0) > 0:
            st.sidebar.markdown("---")
            st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>🏪 Fournisseurs</h3>", unsafe_allow_html=True)
            st.sidebar.metric("Total Fournisseurs", fournisseurs_stats.get('total_fournisseurs', 0))
            st.sidebar.metric("Fournisseurs Actifs", fournisseurs_stats.get('fournisseurs_actifs', 0))

            # Évaluation moyenne
            eval_moyenne = fournisseurs_stats.get('evaluation_moyenne', 0)
            if eval_moyenne > 0:
                st.sidebar.metric("⭐ Éval. Moyenne", f"{eval_moyenne}/10")

            # Montant total commandes si significatif
            montant_total = fournisseurs_stats.get('montant_total_commandes', 0)
            if montant_total > 0:
                st.sidebar.metric("💰 Total Commandes", f"{montant_total:,.0f}$")
    except Exception:
        pass  # Silencieux si erreur

    # ARCHITECTURE UNIFIÉE : Statistiques postes depuis TimeTracker
    if TIMETRACKER_AVAILABLE and 'timetracker_erp' in st.session_state:
        try:
            postes_stats = st.session_state.timetracker_erp.get_work_centers_statistics()
            if postes_stats.get('total_postes', 0) > 0:
                st.sidebar.markdown("---")
                st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>🏭 Postes Travail</h3>", unsafe_allow_html=True)
                st.sidebar.metric("Postes Actifs", postes_stats.get('total_postes', 0))
                st.sidebar.metric("🤖 Robots", postes_stats.get('postes_robotises', 0))
                st.sidebar.metric("💻 CNC", postes_stats.get('postes_cnc', 0))
        except Exception:
            pass  # Silencieux si erreur

    # INTÉGRATION TIMETRACKER : Statistiques dans la sidebar
    if TIMETRACKER_AVAILABLE and 'timetracker_erp' in st.session_state:
        try:
            tt_stats = st.session_state.timetracker_erp.get_timetracker_statistics()
            if tt_stats.get('total_employees', 0) > 0 or tt_stats.get('active_entries', 0) > 0:
                st.sidebar.markdown("---")
                st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>⏱️ TimeTracker ERP</h3>", unsafe_allow_html=True)
                st.sidebar.metric("👥 Employés", tt_stats.get('total_employees', 0))
                st.sidebar.metric("🟢 Pointages Actifs", tt_stats.get('active_entries', 0))
                if tt_stats.get('total_hours_today', 0) > 0:
                    st.sidebar.metric("⏱️ Heures Jour", f"{tt_stats.get('total_hours_today', 0):.1f}h")
                if tt_stats.get('total_revenue_today', 0) > 0:
                    st.sidebar.metric("💰 Revenus Jour", f"{tt_stats.get('total_revenue_today', 0):,.0f}$")

                # ÉTAPE 4 : Navigation vers Bons de Travail depuis TimeTracker
                if st.sidebar.button("🔧 Voir Mes Bons de Travail", key="nav_to_bt", use_container_width=True):
                    st.session_state.page_redirect = "formulaires_page"
                    st.session_state.form_action = "list_bon_travail"
                    st.session_state.navigation_message = "🔧 Redirection vers les Bons de Travail..."
                    st.rerun()
        except Exception:
            pass  # Silencieux si erreur

    st.sidebar.markdown("---")
    footer_text = "🏭 ERP Production DG Inc.<br/>🗄️ Architecture Unifiée<br/>📑 Module Formulaires Actif<br/>🏪 Module Fournisseurs Intégré<br/>⏱️🏭 TimeTracker & Postes Unifiés"

    # NOUVEAU : Ajouter info stockage persistant dans footer sidebar
    if st.session_state.get('storage_manager'):
        storage_info = st.session_state.storage_manager.get_storage_info()
        if storage_info['environment_type'] == 'RENDER_PERSISTENT':
            footer_text += "<br/>💾 Stockage Persistant Render"
        elif storage_info['environment_type'] == 'RENDER_EPHEMERAL':
            footer_text += "<br/>⚠️ Mode Temporaire"

    st.sidebar.markdown(f"<div style='background:var(--primary-color-lighter);padding:10px;border-radius:8px;text-align:center;'><p style='color:var(--primary-color-darkest);font-size:12px;margin:0;'>{footer_text}</p></div>", unsafe_allow_html=True)

    # PAGES (MODIFIÉES avec module Formulaires et Fournisseurs, SANS Assistant IA)
    if page_to_show_val == "dashboard":
        show_dashboard()
    elif page_to_show_val == "liste":
        show_liste_projets()
    elif page_to_show_val == "crm_page":
        show_crm_page()
    elif page_to_show_val == "employees_page":
        show_employees_page()
    elif page_to_show_val == "fournisseurs_page":
        if FOURNISSEURS_AVAILABLE:
            show_fournisseurs_page()
        else:
            st.error("❌ Module Fournisseurs non disponible")
    elif page_to_show_val == "formulaires_page":
        if FORMULAIRES_AVAILABLE:
            show_formulaires_page()
        else:
            st.error("❌ Module Formulaires non disponible")
    elif page_to_show_val == "timetracker_unified_page":
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

    # Affichage des modales et formulaires
    if st.session_state.get('show_project_modal'):
        show_project_modal()
    if st.session_state.get('show_create_project'):
        render_create_project_form(st.session_state.gestionnaire, st.session_state.gestionnaire_crm)
    if st.session_state.get('show_edit_project'):
        render_edit_project_form(st.session_state.gestionnaire, st.session_state.gestionnaire_crm, st.session_state.edit_project_data)
    if st.session_state.get('show_delete_confirmation'):
        render_delete_confirmation(st.session_state.gestionnaire)

# ========================
# FONCTION PRINCIPALE AVEC PORTAIL
# ========================

def main():
    """Fonction principale avec routage des modes - PORTAIL + ERP COMPLET SANS Assistant IA"""

    # NOUVEAU : Charger le CSS externe en priorité
    css_loaded = load_external_css()
    
    # Fallback si CSS externe indisponible
    if not css_loaded:
        apply_fallback_styles()

    # Initialisation des variables de session - COMPLÈTE
    if 'app_mode' not in st.session_state:
        st.session_state.app_mode = "portal"
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None

    # Initialisation des variables de session (MISES À JOUR SANS Assistant IA)
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
        'timetracker_employee_id': None, 'timetracker_project_id': None,
        'timetracker_task_id': None, 'timetracker_is_clocked_in': False,
        'timetracker_current_entry_id': None, 'timetracker_view_mode': 'employee',
        'form_action': None,
        'selected_formulaire_id': None,
        'formulaire_filter_type': 'TOUS',
        'formulaire_filter_statut': 'TOUS',
        'show_formulaire_modal': False,
        'formulaire_project_preselect': None,
        'page_redirect': None,
        'fournisseur_action': None,
        'selected_fournisseur_id': None,
        'fournisseur_filter_category': 'TOUS',
        'fournisseur_confirm_delete_id': None,
        'fournisseur_performance_period': 365,
        'navigation_message': None,
        'current_page': None,
        'admin_permissions': [],
        'pointages_temp': []
    }
    for k, v_def in session_defs.items():
        if k not in st.session_state:
            st.session_state[k] = v_def

    # Gestion des redirections automatiques depuis les modules intégrés
    if st.session_state.get('page_redirect'):
        target_page = st.session_state.page_redirect
        del st.session_state.page_redirect

        if target_page == "timetracker_page":
            st.session_state.current_page = "timetracker"
        elif target_page == "formulaires_page":
            st.session_state.current_page = "formulaires"

        st.rerun()

    # Affichage de notifications de navigation
    if st.session_state.get('navigation_message'):
        st.info(st.session_state.navigation_message)
        del st.session_state.navigation_message

    # Routage selon le mode
    if st.session_state.app_mode == "portal":
        show_portal_home()

    elif st.session_state.app_mode == "employee":
        init_erp_system()  # Initialiser le système pour avoir accès aux modules
        show_employee_interface()

    elif st.session_state.app_mode == "admin_auth":
        show_admin_auth()

    elif st.session_state.app_mode == "erp":
        if check_admin_session():
            show_erp_main()
        else:
            st.error("Session expirée. Veuillez vous reconnecter.")
            st.session_state.app_mode = "admin_auth"
            st.rerun()

    else:
        # Mode par défaut - retour au portail
        st.session_state.app_mode = "portal"
        st.rerun()

    # Sauvegarde périodique automatique
    if st.session_state.get('storage_manager'):
        if hasattr(st.session_state, 'action_counter'):
            st.session_state.action_counter += 1
        else:
            st.session_state.action_counter = 1

        # Sauvegarde automatique toutes les 100 actions
        if st.session_state.action_counter % 100 == 0:
            try:
                backup_path = st.session_state.storage_manager.create_backup("auto")
                if backup_path:
                    st.toast("💾 Sauvegarde automatique effectuée", icon="✅")
            except Exception as e:
                print(f"Erreur sauvegarde automatique: {e}")

if __name__ == "__main__":
    try:
        main()
        if st.session_state.get('admin_authenticated'):
            show_footer()
    except Exception as e_main:
        st.error(f"Une erreur majeure est survenue dans l'application: {str(e_main)}")
        st.info("Veuillez essayer de rafraîchir la page ou de redémarrer l'application.")
        import traceback
        st.code(traceback.format_exc())

        # En cas d'erreur, essayer de créer une sauvegarde d'urgence
        if 'storage_manager' in st.session_state and st.session_state.storage_manager:
            try:
                emergency_backup = st.session_state.storage_manager.create_backup("emergency_error")
                if emergency_backup:
                    st.info(f"💾 Sauvegarde d'urgence créée: {emergency_backup}")
            except Exception:
                passwith open('style.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
        st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
        return True
    except FileNotFoundError:
        st.warning("⚠️ Fichier style.css non trouvé. Utilisation du style par défaut.")
        return False
    except Exception as e:
        st.warning(f"⚠️ Erreur chargement CSS: {e}")
        return False

def apply_fallback_styles():
    """Styles CSS de secours si le fichier externe n'est pas disponible"""
    st.markdown("""
    <style>
    /* Styles de secours minimaux */
    :root {
        --primary-color: #00A971;
        --primary-color-light: #33BF85;
        --primary-color-lighter: #DCFCE7;
        --text-color: #374151;
        --background-color: #F9FAFB;
        --card-background: #F0FDF4;
        --border-radius-lg: 0.75rem;
        --box-shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    
    .main {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: var(--background-color);
    }
    
    .stButton > button {
        background: linear-gradient(145deg, #00A971 0%, #1F2937 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--border-radius-lg) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--box-shadow-md) !important;
    }
    
    /* Masquer éléments Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .css-1d391kg {display: none;}
    </style>
    """, unsafe_allow_html=True)

# ========================
# CONFIGURATION AUTHENTIFICATION
# ========================

def get_admin_credentials():
    """Configuration des identifiants admin pour déploiement"""
    return {
        "admin": os.environ.get("ADMIN_PASSWORD", "admin123"),
        "dg_admin": os.environ.get("DG_ADMIN_PASSWORD", "dg2024!"),
        "superviseur": os.environ.get("SUPERVISEUR_PASSWORD", "super2024"),
        "direction": os.environ.get("DIRECTION_PASSWORD", "direction!123"),
        "production": os.environ.get("PRODUCTION_PASSWORD", "prod2024"),
    }

def verify_admin_password(username, password):
    """Vérifie les identifiants administrateur"""
    admin_creds = get_admin_credentials()
    return username in admin_creds and admin_creds[username] == password

def get_user_display_name(username):
    """Retourne le nom d'affichage selon le rôle"""
    names = {
        "admin": "Administrateur Principal",
        "dg_admin": "Admin DG Inc.",
        "superviseur": "Superviseur Production",
        "direction": "Direction Générale",
        "production": "Responsable Production"
    }
    return names.get(username, username.title())

def get_user_permissions(username):
    """Définit les permissions selon le rôle"""
    permissions = {
        "admin": ["ALL"],
        "dg_admin": ["ALL"],
        "direction": ["projects", "crm", "employees", "reports", "formulaires", "fournisseurs"],
        "superviseur": ["projects", "timetracker", "work_centers", "employees", "formulaires"],
        "production": ["timetracker", "work_centers", "formulaires", "inventory"]
    }
    return permissions.get(username, [])

def check_admin_session():
    """Vérifie la validité de la session admin"""
    if not st.session_state.get('admin_authenticated'):
        return False

    if 'admin_login_time' not in st.session_state:
        return False

    # Session expire après 4 heures
    session_age = datetime.now() - st.session_state.admin_login_time
    if session_age > timedelta(hours=4):
        st.session_state.admin_authenticated = False
        st.warning("Session expirée. Veuillez vous reconnecter.")
        return False

    return True

def show_admin_header():
    """Affiche l'en-tête admin avec info session"""
    username = st.session_state.get('admin_username', 'Admin')
    display_name = get_user_display_name(username)
    login_time = st.session_state.get('admin_login_time')

    if login_time:
        session_duration = datetime.now() - login_time
        hours = int(session_duration.total_seconds() // 3600)
        minutes = int((session_duration.total_seconds() % 3600) // 60)
        session_info = f"Session: {hours}h{minutes}m"
    else:
        session_info = "Session active"

    st.markdown(f"""
    <div class="admin-welcome">
        <h3>🏭 ERP Production DG Inc. - Mode Administrateur</h3>
        <p>Bienvenue <strong>{display_name}</strong> ! {session_info}</p>
    </div>
    """, unsafe_allow_html=True)

# ========================
# IMPORTS MODULES ERP (ORIGINAL)
# ========================

# PERSISTENT STORAGE : Import du gestionnaire de stockage persistant
try:
    from database_persistent import init_persistent_storage
    PERSISTENT_STORAGE_AVAILABLE = True
except ImportError:
    PERSISTENT_STORAGE_AVAILABLE = False

# NOUVELLE ARCHITECTURE : Import SQLite Database
try:
    from erp_database import ERPDatabase, convertir_pieds_pouces_fractions_en_valeur_decimale, convertir_imperial_vers_metrique
    ERP_DATABASE_AVAILABLE = True
except ImportError:
    ERP_DATABASE_AVAILABLE = False

# Importations pour le CRM (avec toutes les fonctions décommentées)
try:
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
    CRM_AVAILABLE = True
except ImportError:
    CRM_AVAILABLE = False

# Importations pour les Employés
try:
    from employees import (
        GestionnaireEmployes,
        render_employes_liste_tab,
        render_employes_dashboard_tab,
        render_employe_form,
        render_employe_details
    )
    EMPLOYEES_AVAILABLE = True
except ImportError:
    EMPLOYEES_AVAILABLE = False

# ARCHITECTURE UNIFIÉE : Postes de travail intégrés dans TimeTracker
# Les fonctions postes sont maintenant dans timetracker.py
POSTES_AVAILABLE = False  # Désactivé - maintenant unifié dans TimeTracker

# NOUVEAU : Importation du module Formulaires
try:
    from formulaires import (
        GestionnaireFormulaires,
        show_formulaires_page
    )
    FORMULAIRES_AVAILABLE = True
except ImportError:
    FORMULAIRES_AVAILABLE = False

# NOUVEAU : Importation du module Fournisseurs
try:
    from fournisseurs import (
        GestionnaireFournisseurs,
        show_fournisseurs_page
    )
    FOURNISSEURS_AVAILABLE = True
except ImportError:
    FOURNISSEURS_AVAILABLE = False

# INTÉGRATION TIMETRACKER : Importation du module TimeTracker unifié
try:
    from timetracker import show_timetracker_interface, TimeTrackerERP
    TIMETRACKER_AVAILABLE = True
except ImportError as e:
    TIMETRACKER_AVAILABLE = False

# Configuration de la page
st.set_page_config(
    page_title="🚀 ERP Production DG Inc.",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================
# FONCTIONS UTILITAIRES ERP (ORIGINALES COMPLÈTES)
# ========================

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
    except Exception as e:
        print(f"Erreur de conversion en pieds/pouces : {e}")
        return "0' 0\""

def valider_mesure_saisie(mesure_saisie_str):
    mesure_nettoyee = str(mesure_saisie_str).strip()
    if not mesure_nettoyee:
        return True, "0' 0\""
    try:
        valeur_pieds_dec = convertir_pieds_pouces_fractions_en_valeur_decimale(mesure_saisie_str)
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

# ========================
# GESTIONNAIRE PROJETS SQLite (ORIGINAL)
# ========================

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

# ========================
# GESTIONNAIRE INVENTAIRE SQLite (ORIGINAL)
# ========================

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

# ========================
# INITIALISATION ERP SYSTÈME (ORIGINAL)
# ========================

def _init_base_data_if_empty():
    """Initialise les données de base si les tables sont vides - RÉSOUT ERREURS FK"""
    if not ERP_DATABASE_AVAILABLE:
        return

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

def init_erp_system():
    """Initialise le système ERP complet"""

    # NOUVEAU : Initialisation du gestionnaire de stockage persistant AVANT tout
    if PERSISTENT_STORAGE_AVAILABLE and 'storage_manager' not in st.session_state:
        try:
            st.session_state.storage_manager = init_persistent_storage()

            # Utiliser le chemin de base de données configuré par le gestionnaire de stockage
            db_path = st.session_state.storage_manager.db_path

            # Notification selon le type de stockage
            storage_info = st.session_state.storage_manager.get_storage_info()
            if storage_info['environment_type'] == 'RENDER_PERSISTENT':
                st.toast("💾 Stockage persistant Render activé !", icon="✅")
            elif storage_info['environment_type'] == 'RENDER_EPHEMERAL':
                st.toast("⚠️ Mode temporaire - Configurez le persistent disk", icon="⚠️")

        except Exception as e:
            st.error(f"❌ Erreur initialisation stockage persistant: {e}")
            # Fallback vers stockage local
            db_path = "erp_production_dg.db"
            st.session_state.storage_manager = None
    else:
        db_path = st.session_state.storage_manager.db_path if st.session_state.get('storage_manager') else "erp_production_dg.db"

    # NOUVELLE ARCHITECTURE : Initialisation ERPDatabase avec chemin configuré
    if ERP_DATABASE_AVAILABLE and 'erp_db' not in st.session_state:
        st.session_state.erp_db = ERPDatabase(db_path)
        st.session_state.migration_completed = True

        # AJOUT CRITIQUE : Initialiser données de base si vides - RÉSOUT ERREURS FK
        _init_base_data_if_empty()

        # Créer une sauvegarde initiale si gestionnaire disponible
        if st.session_state.get('storage_manager'):
            try:
                backup_path = st.session_state.storage_manager.create_backup("initial_startup")
                if backup_path:
                    print(f"✅ Sauvegarde de démarrage créée: {backup_path}")
            except Exception as e:
                print(f"⚠️ Erreur sauvegarde de démarrage: {e}")

    # NOUVELLE ARCHITECTURE : Gestionnaire projets SQLite
    if ERP_DATABASE_AVAILABLE and 'gestionnaire' not in st.session_state:
        st.session_state.gestionnaire = GestionnaireProjetSQL(st.session_state.erp_db)

    # NOUVEAU : Gestionnaire formulaires
    if FORMULAIRES_AVAILABLE and ERP_DATABASE_AVAILABLE and 'gestionnaire_formulaires' not in st.session_state:
        st.session_state.gestionnaire_formulaires = GestionnaireFormulaires(st.session_state.erp_db)

    # NOUVEAU : Gestionnaire fournisseurs
    if FOURNISSEURS_AVAILABLE and ERP_DATABASE_AVAILABLE and 'gestionnaire_fournisseurs' not in st.session_state:
        st.session_state.gestionnaire_fournisseurs = GestionnaireFournisseurs(st.session_state.erp_db)

    # CORRECTION CRITIQUE : CRM avec base SQLite unifiée
    if CRM_AVAILABLE and ERP_DATABASE_AVAILABLE and 'gestionnaire_crm' not in st.session_state:
        st.session_state.gestionnaire_crm = GestionnaireCRM(st.session_state.erp_db)

    # Gestionnaire employés (reste identique pour l'instant)
    if EMPLOYEES_AVAILABLE and 'gestionnaire_employes' not in st.session_state:
        st.session_state.gestionnaire_employes = GestionnaireEmployes()

    # ARCHITECTURE UNIFIÉE : Gestionnaire postes intégré dans TimeTracker
    # Plus besoin d'initialiser gestionnaire_postes séparément
    # Il sera initialisé automatiquement dans show_timetracker_interface()

    # INTÉGRATION TIMETRACKER : Gestionnaire unifié
    if TIMETRACKER_AVAILABLE and ERP_DATABASE_AVAILABLE and 'timetracker_erp' not in st.session_state:
        try:
            st.session_state.timetracker_erp = TimeTrackerERP(st.session_state.erp_db)
        except Exception as e:
            print(f"Erreur initialisation TimeTracker: {e}")

def get_system_stats():
    """Récupère les statistiques système"""
    try:
        if ERP_DATABASE_AVAILABLE and 'erp_db' in st.session_state:
            db = st.session_state.erp_db
            return {
                'projets': db.get_table_count('projects'),
                'employes': db.get_table_count('employees'),
                'entreprises': db.get_table_count('companies'),
                'postes': db.get_table_count('work_centers'),
                'formulaires': db.get_table_count('formulaires') if hasattr(db, 'get_table_count') else 0
            }
    except Exception:
        pass

    # Stats par défaut
    return {
        'projets': 150,
        'employes': 45,
        'entreprises': 80,
        'postes': 61,
        'formulaires': 120
    }

# ========================
# INTERFACE PORTAIL (AVEC CLASSES CSS)
# ========================

def show_portal_home():
    """Affiche la page d'accueil du portail avec classes CSS"""
    # Header principal
    current_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%d/%m/%Y")

    st.markdown(f"""
    <div class="portal-header">
        <h1>🏭 PORTAIL DG INC.</h1>
        <div class="portal-subtitle">
            Système de Gestion Intégré • Production & Métallurgie<br>
            📅 {current_date} • 🕒 {current_time} • Desmarais & Gagné Inc.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("## 🚪 Choisissez votre mode d'accès")

    # Cartes d'accès
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="access-card employee">
            <div class="access-icon">👥</div>
            <div class="access-title">EMPLOYÉ</div>
            <div class="access-description">
                Interface unifiée TimeTracker & Postes de travail
            </div>
            <ul class="access-features">
                <li>⏰🏭 TimeTracker & Postes Unifiés</li>
                <li>🔧 Bons de Travail</li>
                <li>📊 Suivi temps réel</li>
                <li>📱 Interface simplifiée</li>
                <li>🎯 Gestion centralisée</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        if st.button("👥 ACCÈS EMPLOYÉ", key="employee_btn", use_container_width=True, type="primary"):
            st.session_state.app_mode = "employee"
            st.session_state.user_role = "employee"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="access-card admin">
            <div class="access-icon">👨‍💼</div>
            <div class="access-title">ADMINISTRATEUR</div>
            <div class="access-description">
                ERP complet avec authentification sécurisée
            </div>
            <ul class="access-features">
                <li>📋 Gestion projets</li>
                <li>🤝 CRM complet</li>
                <li>📑 Formulaires DG</li>
                <li>🏪 Fournisseurs</li>
                <li>📊 Reporting avancé</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        if st.button("👨‍💼 ACCÈS ADMIN", key="admin_btn", use_container_width=True, type="secondary"):
            st.session_state.app_mode = "admin_auth"
            st.rerun()

    # Statistiques système
    stats = get_system_stats()

    st.markdown("---")
    st.markdown("### 📊 État du Système DG Inc.")

    st.markdown(f"""
    <div class="status-grid">
        <div class="status-card">
            <div class="status-number">{stats['projets']}</div>
            <div class="status-label">Projets Actifs</div>
        </div>
        <div class="status-card">
            <div class="status-number">{stats['employes']}</div>
            <div class="status-label">Employés ERP</div>
        </div>
        <div class="status-card">
            <div class="status-number">{stats['entreprises']}</div>
            <div class="status-label">Entreprises</div>
        </div>
        <div class="status-card">
            <div class="status-number">{stats['postes']}</div>
            <div class="status-label">Postes Travail</div>
        </div>
        <div class="status-card">
            <div class="status-number">{stats.get('formulaires', 120)}</div>
            <div class="status-label">Formulaires</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Modules disponibles
    st.markdown("---")
    st.markdown("### 🔧 Modules Actifs")

    modules_status = [
        ("📊 Base de Données ERP", ERP_DATABASE_AVAILABLE),
        ("🤝 CRM", CRM_AVAILABLE),
        ("👥 Employés", EMPLOYEES_AVAILABLE),
        ("⏱️🏭 TimeTracker & Postes", TIMETRACKER_AVAILABLE),
        ("📑 Formulaires", FORMULAIRES_AVAILABLE),
        ("🏪 Fournisseurs", FOURNISSEURS_AVAILABLE),
        ("💾 Stockage Persistant", PERSISTENT_STORAGE_AVAILABLE)
    ]

    modules_col1, modules_col2, modules_col3 = st.columns(3)

    for i, (module_name, is_available) in enumerate(modules_status):
        target_col = [modules_col1, modules_col2, modules_col3][i % 3]
        with target_col:
            if is_available:
                st.success(f"✅ {module_name}")
            else:
                st.error(f"❌ {module_name}")

    # Footer
    st.markdown("""
    <div class="portal-footer">
        <h4>🏭 ERP Production DG Inc.</h4>
        <p>
            <strong>Desmarais & Gagné Inc.</strong> • Fabrication métallique et industrielle<br>
            🗄️ Architecture unifiée • 📑 Formulaires • ⏱️🏭 TimeTracker & Postes<br>
            💾 Stockage persistant • 🔄 Navigation fluide • 🔒 Sécurisé
        </p>
        <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color);">
            <small>
                👥 <strong>Employés:</strong> Interface unifiée TimeTracker & Postes<br>
                👨‍💼 <strong>Admins:</strong> ERP complet avec architecture moderne<br>
                🏗️ Version intégrée • ✅ Production Ready • 🎯 Module Unifié
            </small>
        </div>
    </div>
    """, unsafe_allow_html=True)

def show_employee_interface():
    """Interface simplifiée pour les employés"""
    st.markdown("""
    <div class="employee-header">
        <h2>👥 Interface Employé - DG Inc.</h2>
        <p>TimeTracker & Postes Unifiés, Bons de Travail et Suivi Production</p>
    </div>
    """, unsafe_allow_html=True)

    # Onglets pour organiser l'interface employé
    tab_timetracker, tab_bons_travail, tab_production = st.tabs([
        "⏱️🏭 TimeTracker & Postes", "🔧 Bons de Travail", "📊 Production"
    ])

    with tab_timetracker:
        if TIMETRACKER_AVAILABLE and 'timetracker_erp' in st.session_state:
            try:
                # Interface TimeTracker complète avec postes intégrés
                show_timetracker_interface()
            except Exception as e:
                st.error(f"Erreur TimeTracker: {e}")
                show_fallback_timetracker()
        else:
            show_fallback_timetracker()

    with tab_bons_travail:
        if FORMULAIRES_AVAILABLE:
            st.markdown("### 🔧 Mes Bons de Travail")
            try:
                # Interface simplifiée pour les formulaires
                if 'gestionnaire_formulaires' in st.session_state:
                    formulaires = st.session_state.gestionnaire_formulaires.get_all_formulaires()
                    bons_travail = [f for f in formulaires if f.get('type_formulaire') == 'BON_TRAVAIL']

                    if bons_travail:
                        st.success(f"📊 {len(bons_travail)} Bons de Travail disponibles")

                        # Affichage simplifié des BT
                        for bt in bons_travail[:10]:  # Limiter à 10
                            with st.expander(f"🔧 BT-{bt.get('numero', 'N/A')} - {bt.get('titre', 'Sans titre')}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**Statut:** {bt.get('statut', 'N/A')}")
                                    st.write(f"**Priorité:** {bt.get('priorite', 'N/A')}")
                                with col2:
                                    st.write(f"**Date:** {bt.get('date_creation', 'N/A')}")
                                    st.write(f"**Projet:** #{bt.get('project_id', 'N/A')}")

                                if bt.get('description'):
                                    st.write(f"**Description:** {bt.get('description')}")
                    else:
                        st.info("Aucun Bon de Travail assigné")
                else:
                    st.warning("Gestionnaire formulaires non initialisé")
            except Exception as e:
                st.error(f"Erreur chargement Bons de Travail: {e}")
        else:
            st.warning("❌ Module Formulaires non disponible")
            st.info("Les Bons de Travail ne peuvent pas être affichés")

    with tab_production:
        st.markdown("### 🏭 État de la Production")

        # Statistiques de production - ARCHITECTURE UNIFIÉE
        stats = get_system_stats()

        col1, col2, col3 = st.columns(3)
        with col1:
            # Stats depuis TimeTracker unifié si disponible
            postes_count = stats['postes']
            if TIMETRACKER_AVAILABLE and 'timetracker_erp' in st.session_state:
                try:
                    postes_stats = st.session_state.timetracker_erp.get_work_centers_statistics()
                    postes_count = postes_stats.get('total_postes', stats['postes'])
                except Exception:
                    pass
            st.metric("🏭 Postes Actifs", postes_count)
        with col2:
            st.metric("📊 Projets", stats['projets'])
        with col3:
            # Simulation efficacité
            efficacite = random.uniform(82, 87)
            st.metric("⚡ Efficacité", f"{efficacite:.1f}%")

        # État des postes (simulation avec architecture unifiée)
        st.markdown("#### 🔧 État des Postes de Travail (Architecture Unifiée)")

        postes_demo = [
            {"nom": "Robot ABB GMAW Station 1", "statut": "🟢 En Production", "operateur": "Jean D."},
            {"nom": "Découpe Plasma CNC", "statut": "🟡 En Attente", "operateur": "Marie T."},
            {"nom": "Assemblage Manuel Station A", "statut": "🟢 En Production", "operateur": "Paul L."},
            {"nom": "Robot KUKA Station 2", "statut": "🔴 Maintenance", "operateur": "-"},
            {"nom": "Presse Hydraulique", "statut": "🟢 En Production", "operateur": "Sophie R."}
        ]

        for poste in postes_demo:
            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                st.write(f"**{poste['nom']}**")
            with col2:
                st.write(poste['statut'])
            with col3:
                st.write(f"👤 {poste['operateur']}")

        st.info("💡 Interface unifiée TimeTracker & Postes - Gestion centralisée")

    # Bouton retour
    st.markdown("---")
    if st.button("🏠 Retour au Portail", use_container_width=True):
        st.session_state.app_mode = "portal"
        st.rerun()

def show_fallback_timetracker():
    """Interface de pointage de substitution"""
    st.markdown("### ⏰ Pointage Simplifié")
    st.info("Interface de pointage temporaire en attendant le déploiement complet du TimeTracker")

    # Interface basique de pointage
    with st.container():
        st.markdown("#### 👤 Informations Employé")

        col1, col2 = st.columns(2)
        with col1:
            employee_name = st.text_input("Nom de l'employé:", placeholder="Ex: Jean Dupont")
            employee_id = st.text_input("ID Employé:", placeholder="Ex: EMP001")

        with col2:
            project_id = st.text_input("Projet:", placeholder="Ex: #10001")
            task_description = st.text_input("Tâche:", placeholder="Ex: Soudage chassis")

        st.markdown("#### 🔧 Actions de Pointage")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🟢 DÉBUTER", use_container_width=True, type="primary"):
                if employee_name and project_id:
                    current_time = datetime.now().strftime("%H:%M:%S")
                    st.success(f"✅ Pointage débuté à {current_time}")
                    st.balloons()

                    # Sauvegarder dans session state
                    if 'pointages_temp' not in st.session_state:
                        st.session_state.pointages_temp = []

                    st.session_state.pointages_temp.append({
                        'employee': employee_name,
                        'project': project_id,
                        'task': task_description,
                        'start_time': current_time,
                        'date': datetime.now().strftime("%Y-%m-%d")
                    })
                else:
                    st.error("Veuillez remplir au minimum le nom et le projet")

        with col2:
            if st.button("⏸️ PAUSE", use_container_width=True):
                st.warning("⏸️ Pause activée")

        with col3:
            if st.button("🔴 TERMINER", use_container_width=True):
                current_time = datetime.now().strftime("%H:%M:%S")
                st.success(f"✅ Pointage terminé à {current_time}")

        # Affichage des pointages temporaires
        if st.session_state.get('pointages_temp'):
            st.markdown("---")
            st.markdown("#### 📊 Pointages de la session")

            df_pointages = pd.DataFrame(st.session_state.pointages_temp)
            st.dataframe(df_pointages, use_container_width=True)

def show_admin_auth():
    """Interface d'authentification administrateur"""
    st.markdown("""
    <div class="admin-auth">
        <h3>🔐 Authentification Administrateur</h3>
        <p style="text-align: center; color: #6B7280;">ERP Production DG Inc. - Accès Restreint</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("admin_login"):
        st.markdown("#### 👤 Identifiants")
        username = st.text_input("Nom d'utilisateur:", placeholder="admin, dg_admin, superviseur, direction, production")
        password = st.text_input("🔒 Mot de passe:", type="password")

        st.markdown("#### 🔒 Connexion")
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("🚀 Se Connecter", use_container_width=True, type="primary")
        with col2:
            cancel = st.form_submit_button("❌ Annuler", use_container_width=True)

        if submitted:
            if verify_admin_password(username, password):
                st.session_state.admin_authenticated = True
                st.session_state.admin_username = username
                st.session_state.admin_login_time = datetime.now()
                st.session_state.admin_permissions = get_user_permissions(username)
                st.session_state.app_mode = "erp"
                st.session_state.user_role = "admin"

                st.markdown(f"""
                <div class="alert-success">
                    ✅ <strong>Connexion réussie !</strong><br>
                    Bienvenue {get_user_display_name(username)}
                </div>
                """, unsafe_allow_html=True)

                st.rerun()
            else:
                st.markdown("""
                <div class="alert-error">
                    ❌ <strong>Échec de connexion</strong><br>
                    Nom d'utilisateur ou mot de passe incorrect.
                </div>
                """, unsafe_allow_html=True)

        if cancel:
            st.session_state.app_mode = "portal"
            st.rerun()

    # Informations de connexion pour demo
    with st.expander("🔒 Comptes de Démonstration", expanded=False):
        st.markdown("""
        **Comptes administrateurs disponibles:**

        - **admin** / admin123 *(Accès complet)*
        - **dg_admin** / dg2024! *(Admin DG Inc.)*
        - **superviseur** / super2024 *(Supervision Production)*
        - **direction** / direction!123 *(Direction Générale)*
        - **production** / prod2024 *(Responsable Production)*

        *En production, ces mots de passe sont configurés via les variables d'environnement*
        """)

# ========================
# AFFICHAGE DU STATUT DE STOCKAGE DANS LA SIDEBAR (ORIGINAL)
# ========================

def show_storage_status_sidebar():
    """Affiche le statut du stockage persistant dans la sidebar"""
    if 'storage_manager' not in st.session_state:
        return

    try:
        storage_info = st.session_state.storage_manager.get_storage_info()

        st.sidebar.markdown("---")
        st.sidebar.markdown("<h3 style='text-align:center;color:var(--primary-color-darkest);'>💾 Stockage</h3>", unsafe_allow_html=True)

        # Statut principal
        if storage_info['is_persistent']:
            st.sidebar.success("💾 Stockage Persistant")
        else:
            st.sidebar.warning("⚠️ Stockage Éphémère")

        # Informations de base
        if storage_info['db_exists']:
            st.sidebar.metric("Base ERP", f"{storage_info['db_size_mb']} MB")

        if storage_info.get('backup_count', 0) > 0:
            st.sidebar.metric("Sauvegardes", storage_info['backup_count'])

        # Usage disque (Render uniquement)
        if storage_info.get('disk_usage'):
            disk = storage_info['disk_usage']
            st.sidebar.metric("Usage Disque", f"{disk['usage_percent']}%")
            if disk['usage_percent'] > 80:
                st.sidebar.warning("⚠️ Espace disque faible")

        # Type d'environnement (en petit)
        env_display = {
            'RENDER_PERSISTENT': '🚀 Render Persistent',
            'RENDER_EPHEMERAL': '⚠️ Render Temporaire',
            'LOCAL_DEVELOPMENT': '💻 Développement',
            'CUSTOM_PATH': '📁 Personnalisé'
        }

        st.sidebar.caption(f"Type: {env_display.get(storage_info['environment_type'], 'Inconnu')}")

    except Exception as e:
        st.sidebar.error(f"Erreur statut stockage: {str(e)[:50]}...")

# ========================
# FONCTIONS DE VUE ET DE RENDU ERP
# ========================

def show_dashboard():
    """Dashboard principal utilisant les classes CSS"""
    st.markdown("""
    <div class="main-title">
        <h1>📊 Tableau de Bord ERP Production</h1>
    </div>
    """, unsafe_allow_html=True)
    
    gestionnaire = st.session_state.gestionnaire
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    # ARCHITECTURE UNIFIÉE : Postes via TimeTracker
    postes_stats = {'total_postes': 0, 'postes_robotises': 0, 'postes_cnc': 0, 'par_departement': {}}
    if TIMETRACKER_AVAILABLE and 'timetracker_erp' in st.session_state:
        try:
            # Récupérer les stats postes depuis TimeTracker unifié
            postes_stats = st.session_state.timetracker_erp.get_work_centers_statistics()
        except Exception:
            pass  # Utiliser les stats par défaut si erreur

    # NOUVEAU : Gestionnaire fournisseurs pour métriques
    if 'gestionnaire_fournisseurs' not in st.session_state:
        st.session_state.gestionnaire_fournisseurs = GestionnaireFournisseurs(st.session_state.erp_db)
    gestionnaire_fournisseurs = st.session_state.gestionnaire_fournisseurs

    # NOUVEAU : Gestionnaire formulaires pour métriques
    if 'gestionnaire_formulaires' not in st.session_state:
        st.session_state.gestionnaire_formulaires = GestionnaireFormulaires(st.session_state.erp_db)
    gestionnaire_formulaires = st.session_state.gestionnaire_formulaires

    # Affichage notification migration
    if st.session_state.get('migration_completed'):
        st.success("🎉 Migration complétée ! ERP Production DG Inc. utilise maintenant une architecture unifiée.")

    stats = get_project_statistics(gestionnaire)
    emp_stats = gestionnaire_employes.get_statistiques_employes()
    
    # ARCHITECTURE UNIFIÉE : Stats postes depuis TimeTracker
    # postes_stats déjà initialisé plus haut

    # NOUVEAU : Statistiques formulaires
    form_stats = gestionnaire_formulaires.get_statistiques_formulaires()

    # NOUVEAU : Statistiques fournisseurs
    fournisseurs_stats = gestionnaire_fournisseurs.get_fournisseurs_statistics()

    if stats['total'] == 0 and emp_stats.get('total', 0) == 0:
        st.markdown("""
        <div class='welcome-card'>
            <h3>🏭 Bienvenue dans l'ERP Production DG Inc. !</h3>
            <p>Architecture unifiée avec base de données relationnelle. Créez votre premier projet ou explorez les données migrées.</p>
        </div>
        """, unsafe_allow_html=True)
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

    # NOUVEAU : Métriques Formulaires
    if any(form_stats.values()):
        st.markdown("### 📑 Aperçu Formulaires DG Inc.")
        form_c1, form_c2, form_c3, form_c4, form_c5 = st.columns(5)

        with form_c1:
            total_bt = form_stats.get('BON_TRAVAIL', {}).get('total', 0) if isinstance(form_stats.get('BON_TRAVAIL'), dict) else 0
            st.metric("🔧 Bons Travail", total_bt)
        with form_c2:
            total_ba = form_stats.get('BON_ACHAT', {}).get('total', 0) if isinstance(form_stats.get('BON_ACHAT'), dict) else 0
            st.metric("🛒 Bons Achats", total_ba)
        with form_c3:
            total_bc = form_stats.get('BON_COMMANDE', {}).get('total', 0) if isinstance(form_stats.get('BON_COMMANDE'), dict) else 0
            st.metric("📦 Bons Commande", total_bc)
        with form_c4:
            total_dp = form_stats.get('DEMANDE_PRIX', {}).get('total', 0) if isinstance(form_stats.get('DEMANDE_PRIX'), dict) else 0
            st.metric("💰 Demandes Prix", total_dp)
        with form_c5:
            total_est = form_stats.get('ESTIMATION', {}).get('total', 0) if isinstance(form_stats.get('ESTIMATION'), dict) else 0
            st.metric("📊 Estimations", total_est)

        # Montant total des formulaires
        montant_total_forms = sum(
            type_stats.get('montant_total', 0)
            for type_stats in form_stats.values()
            if isinstance(type_stats, dict)
        )
        if montant_total_forms > 0:
            st.markdown(f"**💼 Valeur Documents: {montant_total_forms:,.0f}$ CAD**")

    # NOUVEAU : Métriques Fournisseurs DG Inc.
    if fournisseurs_stats and fournisseurs_stats.get('total_fournisseurs', 0) > 0:
        st.markdown("### 🏪 Aperçu Fournisseurs DG Inc.")
        fournisseur_c1, fournisseur_c2, fournisseur_c3, fournisseur_c4 = st.columns(4)

        with fournisseur_c1:
            st.metric("🏪 Total Fournisseurs", fournisseurs_stats.get('total_fournisseurs', 0))
        with fournisseur_c2:
            st.metric("✅ Fournisseurs Actifs", fournisseurs_stats.get('fournisseurs_actifs', 0))
        with fournisseur_c3:
            eval_moyenne = fournisseurs_stats.get('evaluation_moyenne', 0)
            st.metric("⭐ Évaluation Moy.", f"{eval_moyenne}/10")
        with fournisseur_c4:
            delai_moyen = fournisseurs_stats.get('delai_moyen', 0)
            st.metric("📦 Délai Moyen", f"{delai_moyen}j")

        # Montant total fournisseurs
        montant_total_fournisseurs = fournisseurs_stats.get('montant_total_commandes', 0)
        if montant_total_fournisseurs > 0:
            st.markdown(f"**💰 Volume Total Commandes: {montant_total_fournisseurs:,.0f}$ CAD**")

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
    if TIMETRACKER_AVAILABLE and 'timetracker_erp' in st.session_state:
        try:
            timetracker_stats = st.session_state.timetracker_erp.get_timetracker_statistics()
            if timetracker_stats.get('total_employees', 0) > 0 or timetracker_stats.get('total_entries_today', 0) > 0:
                st.markdown("### ⏱️ Aperçu TimeTracker DG")
                tt_c1, tt_c2, tt_c3, tt_c4 = st.columns(4)
                with tt_c1:
                    st.metric("👥 Employés ERP", timetracker_stats.get('total_employees', 0))
                with tt_c2:
                    st.metric("🟢 Pointages Actifs", timetracker_stats.get('active_entries', 0))
                with tt_c3:
                    st.metric("📊 Heures Jour", f"{timetracker_stats.get('total_hours_today', 0):.1f}h")
                with tt_c4:
                    revenue_display = f"{timetracker_stats.get('total_revenue_today', 0):,.0f}$ CAD"
                    st.metric("💰 Revenus Jour", revenue_display)
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

        TEXT_COLOR_CHARTS = 'var(--text-color)'

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

        # Projets récents depuis SQLite
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
                # NOUVEAU : Bouton création BT depuis projet récent
                if st.button("🔧", key=f"bt_rec_{p.get('id')}", help="Créer Bon de Travail"):
                    st.session_state.form_action = "create_bon_travail"
                    st.session_state.formulaire_project_preselect = p.get('id')
                    st.session_state.page_redirect = "formulaires_page"
                    st.rerun()
                # NOUVEAU : Bouton création BA depuis projet récent
                if st.button("🛒", key=f"ba_rec_{p.get('id')}", help="Créer Bon d'Achat"):
                    st.session_state.form_action = "create_bon_achat"
                    st.session_state.formulaire_project_preselect = p.get('id')
                    st.session_state.page_redirect = "formulaires_page"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

def show_liste_projets():
    st.markdown("### 📋 Liste des Projets")
    gestionnaire = st.session_state.gestionnaire
    crm_manager = st.session_state.gestionnaire_crm

    col_create, _ = st.columns([1, 3])
    with col_create:
        if st.button("➕ Nouveau Projet", use_container_width=True, key="create_btn_liste"):
            st.session_state.show_create_project = True
    st.markdown("---")

    if not gestionnaire.projets and not st.session_state.get('show_create_project'):
        st.info("Aucun projet en base. Cliquez sur 'Nouveau Projet' pour commencer.")

    if gestionnaire.projets:
        # Interface de filtrage
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

        # Logique de filtrage
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

        st.markdown(f"**{len(projets_filtres)} projet(s) trouvé(s)**")
        if projets_filtres:
            # Tableau des projets
            df_data = []
            for p in projets_filtres:
                client_display_name_df = p.get('client_nom_cache', 'N/A')
                if client_display_name_df == 'N/A' and p.get('client_company_id'):
                    entreprise = crm_manager.get_entreprise_by_id(p.get('client_company_id'))
                    if entreprise:
                        client_display_name_df = entreprise.get('nom', 'N/A')
                elif client_display_name_df == 'N/A':
                    client_display_name_df = p.get('client_legacy', 'N/A')

                df_data.append({
                    '🆔': p.get('id', '?'),
                    '📋 Projet': p.get('nom_projet', 'N/A'),
                    '👤 Client': client_display_name_df,
                    '🚦 Statut': p.get('statut', 'N/A'),
                    '⭐ Priorité': p.get('priorite', 'N/A'),
                    '📅 Début': p.get('date_soumis', 'N/A'),
                    '🏁 Fin': p.get('date_prevu', 'N/A'),
                    '💰 Prix': format_currency(p.get('prix_estime', 0))
                })
            st.dataframe(pd.DataFrame(df_data), use_container_width=True)

def render_create_project_form(gestionnaire, crm_manager):
    """FORMULAIRE CRÉATION PROJET - VERSION CORRIGÉE avec validation FK"""
    gestionnaire_employes = st.session_state.gestionnaire_employes

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### ➕ Créer Projet DG Inc.")

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
            submit = st.form_submit_button("💾 Créer le Projet", use_container_width=True)
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

                        st.success(f"✅ Projet #{pid} créé avec {len(employes_valides)} employé(s) assigné(s) !")
                        st.session_state.show_create_project = False
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la création du projet")

                except Exception as e:
                    st.error(f"❌ Erreur création projet: {str(e)}")
                    st.info("💡 Vérifiez que les données de base sont initialisées (entreprises, employés)")

        if cancel:
            st.session_state.show_create_project = False
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

def render_edit_project_form(gestionnaire, crm_manager, project_data):
    """Formulaire d'édition de projet - VERSION COMPLÈTE CORRIGÉE"""
    gestionnaire_employes = st.session_state.gestionnaire_employes

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(f"### ✏️ Modifier Projet #{project_data.get('id')}")

    with st.form("edit_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)

        with fc1:
            nom = st.text_input("Nom *:", value=project_data.get('nom_projet', ''))

            # Gestion de la liste des entreprises CRM
            try:
                entreprises_db = st.session_state.erp_db.execute_query("SELECT id, nom FROM companies ORDER BY nom")
                liste_entreprises_crm_form = [("", "Sélectionner ou laisser vide")] + [(e['id'], e['nom']) for e in entreprises_db]
            except Exception as e:
                st.error(f"Erreur récupération entreprises: {e}")
                liste_entreprises_crm_form = [("", "Aucune entreprise disponible")]

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
                # Traitement des formats de prix différents
                if ',' in prix_str and ('.' not in prix_str or prix_str.find(',') > prix_str.find('.')):
                    prix_str = prix_str.replace('.', '').replace(',', '.')
                elif ',' in prix_str and '.' in prix_str and prix_str.find('.') > prix_str.find(','):
                    prix_str = prix_str.replace(',', '')
                prix_val = float(prix_str) if prix_str else 0.0
            except (ValueError, TypeError):
                prix_val = 0.0

            prix = st.number_input("Prix ($):", 0.0, value=prix_val, step=100.0, format="%.2f")

        # Description
        desc = st.text_area("Description:", value=project_data.get('description', ''))

        # Assignation d'employés
        employes_assignes = []
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
                    'employes_assignes': employes_assignes
                }

                # Mise à jour du projet
                if gestionnaire.modifier_projet(project_data['id'], update_data):
                    # Mettre à jour les assignations des employés
                    if employes_assignes:
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

                    st.success(f"✅ Projet #{project_data['id']} modifié avec succès !")
                    st.session_state.show_edit_project = False
                    st.session_state.edit_project_data = None
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la modification.")

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
        st.markdown("Cette action est **irréversible** et supprimera toutes les données associées (opérations, matériaux, assignations).")

        dcol1, dcol2 = st.columns(2)
        with dcol1:
            if st.button("🗑️ Confirmer Suppression", use_container_width=True):
                if gestionnaire.supprimer_projet(project_id):
                    st.success(f"✅ Projet #{project_id} supprimé avec succès !")
                    st.session_state.show_delete_confirmation = False
                    st.session_state.delete_project_id = None
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la suppression")
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

def show_crm_page():
    st.markdown("### 🤝 Gestion de la Relation Client (CRM)")
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
    st.markdown("### 👥 Gestion des Employés")
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

def show_inventory_management_page():
    st.markdown("### 📦 Gestion de l'Inventaire")

    # Adaptation pour utiliser SQLite
    if 'inventory_manager_sql' not in st.session_state:
        st.session_state.inventory_manager_sql = GestionnaireInventaireSQL(st.session_state.erp_db)

    inventory_manager = st.session_state.inventory_manager_sql
    inventory_data = inventory_manager.get_all_inventory()

    action_mode = st.session_state.get('inv_action_mode', "Voir Liste")

    if action_mode == "Ajouter Article":
        st.subheader("➕ Ajouter un Nouvel Article")
        with st.form("add_inventory_item_form", clear_on_submit=True):
            st.info("Les données seront sauvegardées automatiquement")
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
                            st.success(f"Article '{nom}' (ID: {item_id}) ajouté avec succès !")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la sauvegarde.")

    elif action_mode == "Voir Liste" or not inventory_data:
        st.subheader("📋 Liste des Articles en Inventaire")
        if not inventory_data:
            st.info("L'inventaire est vide. Cliquez sur 'Ajouter Article' pour commencer.")
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
                st.info(f"📊 {len(items_display_list)} articles en inventaire")
            else:
                st.info("Aucun article ne correspond à votre recherche." if search_term_inv else "L'inventaire est vide.")

def show_itineraire():
    """Version améliorée avec vrais postes de travail - Architecture Unifiée"""
    st.markdown("### 🛠️ Itinéraire Fabrication - DG Inc.")
    gestionnaire = st.session_state.gestionnaire
    gestionnaire_employes = st.session_state.gestionnaire_employes

    if not gestionnaire.projets:
        st.warning("Aucun projet disponible.")
        return

    opts = [(p.get('id'), f"#{p.get('id')} - {p.get('nom_projet', 'N/A')}") for p in gestionnaire.projets]
    sel_id = st.selectbox("Projet:", options=[pid for pid, _ in opts], format_func=lambda pid: next((name for id, name in opts if id == pid), ""), key="iti_sel")
    proj = next((p for p in gestionnaire.projets if p.get('id') == sel_id), None)

    if not proj:
        st.error("Projet non trouvé.")
        return

    st.markdown(f"<div class='project-header'><h2>{proj.get('nom_projet', 'N/A')}</h2></div>", unsafe_allow_html=True)

    # Bouton de régénération de gamme - ARCHITECTURE UNIFIÉE
    col_regen1, col_regen2 = st.columns([3, 1])
    with col_regen2:
        if st.button("🔄 Régénérer Gamme", help="Régénérer avec les postes TimeTracker"):
            if TIMETRACKER_AVAILABLE and 'timetracker_erp' in st.session_state:
                try:
                    # Utiliser la génération de gamme depuis TimeTracker unifié
                    nom_projet = proj.get('nom_projet', '').lower()
                    if any(mot in nom_projet for mot in ['chassis', 'structure', 'assemblage']):
                        type_produit = "CHASSIS_SOUDE"
                    elif any(mot in nom_projet for mot in ['batiment', 'pont', 'charpente']):
                        type_produit = "STRUCTURE_LOURDE"
                    else:
                        type_produit = "PIECE_PRECISION"

                    # Générer nouvelle gamme via TimeTracker
                    gamme = st.session_state.timetracker_erp.generer_gamme_fabrication(type_produit, "MOYEN")

                    # Mettre à jour les opérations en SQLite
                    nouvelles_operations = []
                    for i, op in enumerate(gamme, 1):
                        nouvelles_operations.append({
                            'id': i,
                            'sequence': str(op['sequence']),
                            'description': f"{op['poste']} - {proj.get('nom_projet', '')}",
                            'temps_estime': op['temps_estime'],
                            'ressource': op.get('employes_disponibles', ['À assigner'])[0] if op.get('employes_disponibles') else 'À assigner',
                            'statut': 'À FAIRE',
                            'poste_travail': op['poste']
                        })

                    # Mise à jour via SQLite
                    proj['operations'] = nouvelles_operations
                    gestionnaire.modifier_projet(proj['id'], {'operations': nouvelles_operations})
                    st.success("✅ Gamme régénérée avec l'architecture unifiée !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur génération gamme: {e}")
                    st.info("💡 Utilisez l'interface TimeTracker & Postes pour gérer les gammes")
            else:
                st.warning("⚠️ TimeTracker non disponible - Gamme non régénérée")

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    operations = proj.get('operations', [])
    if not operations:
        st.info("Aucune opération définie.")
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
