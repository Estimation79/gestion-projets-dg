# pages/analytics.py
"""
Pages d'analyses et vues pour l'ERP Production DG Inc.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import calendar
from utils.formatting import format_currency
from config.constants import COLORS


def show_nomenclature():
    """Affiche la nomenclature (BOM) d'un projet"""
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
            fig = px.pie(values=costs, names=labels, title="Répartition coûts par matériau")
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)', 
                font=dict(color='var(--text-color)'), 
                legend_title_text='', 
                title_x=0.5
            )
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


def show_itineraire():
    """Affiche l'itinéraire de fabrication avec vrais postes de travail"""
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
            for op in operations:
                status = op.get('statut', 'À FAIRE')
                counts[status] = counts.get(status, 0) + 1
            
            if counts:
                fig = px.bar(
                    x=list(counts.keys()), 
                    y=list(counts.values()), 
                    title="Répartition par statut", 
                    color=list(counts.keys()), 
                    color_discrete_map=COLORS['statut']
                )
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', 
                    paper_bgcolor='rgba(0,0,0,0)', 
                    font=dict(color='var(--text-color)'), 
                    showlegend=False, 
                    title_x=0.5
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with ac2:
            res_time = {}
            for op in operations:
                res = op.get('poste_travail', 'Non assigné')
                time = op.get('temps_estime', 0)
                res_time[res] = res_time.get(res, 0) + time
            
            if res_time:
                fig = px.pie(values=list(res_time.values()), names=list(res_time.keys()), title="Temps par poste")
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', 
                    paper_bgcolor='rgba(0,0,0,0)', 
                    font=dict(color='var(--text-color)'), 
                    legend_title_text='', 
                    title_x=0.5
                )
                st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


def show_gantt():
    """Affiche le diagramme de Gantt"""
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
        st.warning("Données de dates invalides pour Gantt.")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    df_gantt = pd.DataFrame(gantt_data)
    fig = px.timeline(
        df_gantt, 
        x_start="Début", 
        x_end="Fin", 
        y="Projet", 
        color="Statut", 
        color_discrete_map=COLORS['statut'], 
        title="📊 Planning Projets", 
        hover_data=['Client', 'Priorité']
    )
    fig.update_layout(
        height=max(400, len(gantt_data) * 40), 
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)', 
        font=dict(color='var(--text-color)'), 
        xaxis=dict(title="📅 Calendrier", gridcolor='rgba(0,0,0,0.05)'), 
        yaxis=dict(title="📋 Projets", gridcolor='rgba(0,0,0,0.05)', categoryorder='total ascending'), 
        title_x=0.5, 
        legend_title_text=''
    )
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
    """Affiche la vue calendrier"""
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
    """Affiche la vue Kanban (Style Planner)"""
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
    col_borders_k = COLORS['statut']

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
            card_borders_k = COLORS['priorite']
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
