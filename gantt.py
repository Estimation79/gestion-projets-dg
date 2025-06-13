# gantt.py - Vue Gantt adaptée pour ERP Production DG Inc. SQLite
# Compatible avec l'architecture unifiée SQLite

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date

# --- Configuration des Couleurs Adaptées SQLite ---
TASK_COLORS = {
    'ESTIMATION': '#FFB74D',
    'CONCEPTION': '#64B5F6', 
    'DÉVELOPPEMENT': '#81C784',
    'TESTS': '#FFA726',
    'DÉPLOIEMENT': '#9C27B0',
    'MAINTENANCE': '#795548',
    'FORMATION': '#26A69A',
    'DEFAULT': '#90A4AE'
}

SOUS_TACHE_COLORS = {
    'PLANIFICATION': '#FFAB91',
    'RECHERCHE': '#80CBC4',
    'ANALYSE': '#A5D6A7',
    'DÉVELOPPEMENT': '#B39DDB',
    'VALIDATION': '#FFCC02',
    'DOCUMENTATION': '#BCAAA4',
    'DEFAULT': '#CFD8DC'
}

# --- Fonctions Utilitaires ---
def is_mobile_device():
    """Estimation si l'appareil est mobile basée sur la largeur de viewport."""
    if 'is_mobile' not in st.session_state:
        st.session_state.is_mobile = False
    
    st.markdown("""
    <script>
    const checkIfMobile = function() {
        const isMobile = window.innerWidth < 768;
        localStorage.setItem('streamlit_is_mobile', isMobile);
        return isMobile;
    };
    
    checkIfMobile();
    window.addEventListener('resize', checkIfMobile);
    </script>
    """, unsafe_allow_html=True)
    
    return st.session_state.is_mobile

def get_task_color_sqlite(task_type):
    """Récupère la couleur pour un type de tâche (compatible SQLite)"""
    return TASK_COLORS.get(task_type, TASK_COLORS['DEFAULT'])

def get_sous_tache_color_sqlite(sous_tache_name):
    """Récupère la couleur pour une sous-tâche (compatible SQLite)"""
    return SOUS_TACHE_COLORS.get(sous_tache_name, SOUS_TACHE_COLORS['DEFAULT'])

def get_client_display_name(projet, crm_manager):
    """Récupère le nom d'affichage du client depuis le système CRM SQLite"""
    # Prioriser le cache
    client_display = projet.get('client_nom_cache', 'N/A')
    
    # Si pas de cache et qu'il y a un ID d'entreprise
    if client_display == 'N/A' and projet.get('client_company_id'):
        entreprise = crm_manager.get_entreprise_by_id(projet.get('client_company_id'))
        if entreprise:
            client_display = entreprise.get('nom', 'N/A')
    
    # Fallback sur client legacy
    if client_display == 'N/A':
        client_display = projet.get('client_legacy', 'N/A')
    
    return client_display

def get_item_dates_sqlite(item_dict):
    """Retourne (date_debut, date_fin) pour un projet ou une sous-tâche depuis SQLite."""
    start_date_obj, end_date_obj = None, None
    start_key = 'date_debut' if 'date_debut' in item_dict else 'date_soumis'
    end_key = 'date_fin' if 'date_fin' in item_dict else 'date_prevu'

    try:
        start_date_str = item_dict.get(start_key)
        if start_date_str: 
            start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError): 
        start_date_obj = None
        
    try:
        end_date_str = item_dict.get(end_key)
        if end_date_str: 
            end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError): 
        end_date_obj = None

    # Auto-calculer la fin si seulement le début est défini
    is_project_like = 'operations' in item_dict or start_key == 'date_soumis'
    has_operations = isinstance(item_dict.get('operations'), list) and bool(item_dict['operations'])

    if is_project_like and not has_operations and start_date_obj and end_date_obj is None:
        duration_days = 1
        try:
            bd_ft_str = str(item_dict.get('bd_ft_estime', '')).strip()
            if bd_ft_str:
                cleaned_bd_ft = ''.join(filter(lambda x: x.isdigit() or x == '.', bd_ft_str))
                if cleaned_bd_ft: 
                    duration_days = max(1, int(float(cleaned_bd_ft)))
        except (ValueError, TypeError): 
            pass
        end_date_obj = start_date_obj + timedelta(days=duration_days - 1)

    if start_date_obj and end_date_obj and end_date_obj < start_date_obj:
        end_date_obj = start_date_obj
        
    return start_date_obj, end_date_obj

def calculate_overall_date_range_sqlite(projets_list_data):
    """Calcule la plage de dates minimale et maximale pour les projets SQLite."""
    min_overall_date, max_overall_date = None, None
    if not projets_list_data:
        today = date.today()
        return today - timedelta(days=30), today + timedelta(days=60)

    for projet_item_data in projets_list_data:
        dates_to_check = [get_item_dates_sqlite(projet_item_data)]
        
        # Vérifier les opérations (remplace sous_taches)
        for operation_data in projet_item_data.get('operations', []):
            # Les opérations n'ont pas de dates directes, utiliser les dates du projet
            dates_to_check.append(get_item_dates_sqlite(projet_item_data))
        
        for start_d, end_d in dates_to_check:
            if start_d:
                min_overall_date = min(min_overall_date, start_d) if min_overall_date else start_d
            if end_d:
                max_overall_date = max(max_overall_date, end_d) if max_overall_date else end_d
    
    if min_overall_date is None or max_overall_date is None:
        today = date.today()
        min_overall_date = today - timedelta(days=30)
        max_overall_date = today + timedelta(days=60)
    else:
        min_overall_date -= timedelta(days=10)
        max_overall_date += timedelta(days=20)
        if (max_overall_date - min_overall_date).days < 60:
            padding_needed = 60 - (max_overall_date - min_overall_date).days
            max_overall_date += timedelta(days=padding_needed // 2)
            min_overall_date -= timedelta(days=padding_needed - (padding_needed // 2))
    
    if min_overall_date:
         min_overall_date -= timedelta(days=min_overall_date.weekday())
         
    return min_overall_date, max_overall_date

def get_text_color_for_background(hex_bg_color):
    """Détermine si le texte doit être noir ou blanc pour un bon contraste."""
    try:
        if isinstance(hex_bg_color, str) and len(hex_bg_color) == 7 and hex_bg_color.startswith('#'):
            r = int(hex_bg_color[1:3], 16)
            g = int(hex_bg_color[3:5], 16)
            b = int(hex_bg_color[5:7], 16)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return 'black' if luminance > 0.5 else 'white'
    except: 
        pass
    return 'black'

def prepare_gantt_data_sqlite(projets_list, crm_manager, show_operations=True):
    """Prépare les données pour le diagramme Gantt avec architecture SQLite."""
    gantt_items_for_df = []
    y_axis_order = []
    
    min_gantt_date_obj, max_gantt_date_obj = calculate_overall_date_range_sqlite(projets_list)
    min_gantt_datetime, max_gantt_datetime = None, None
    if min_gantt_date_obj and max_gantt_date_obj:
        min_gantt_datetime = datetime.combine(min_gantt_date_obj, datetime.min.time())
        max_gantt_datetime = datetime.combine(max_gantt_date_obj, datetime.max.time())
    
    for projet_item in sorted(projets_list, key=lambda p: p.get('id', 0)):
        proj_id = projet_item.get('id')
        proj_nom_base = projet_item.get('nom_projet', 'Sans Nom')
        proj_nom_complet = f"P{proj_id}: {proj_nom_base}"
        y_axis_order.append(proj_nom_complet)

        proj_debut_orig, proj_fin_orig = get_item_dates_sqlite(projet_item)
        min_op_debut, max_op_fin = None, None
        
        operations_existantes = projet_item.get('operations', [])
        if operations_existantes:
            # Pour les opérations, utiliser les dates du projet parent
            valid_op_dates = [(proj_debut_orig, proj_fin_orig) for _ in operations_existantes if proj_debut_orig and proj_fin_orig]
            if valid_op_dates:
                min_op_debut = min(s for s, f in valid_op_dates)
                max_op_fin = max(f for s, f in valid_op_dates)
        
        barre_proj_debut = min_op_debut if min_op_debut else proj_debut_orig
        barre_proj_fin = max_op_fin if max_op_fin else proj_fin_orig
        
        client_name = get_client_display_name(projet_item, crm_manager)
        texte_barre_projet = f"{proj_nom_base} (Client: {client_name})"
        description_hover_projet = (
            f"Statut: {projet_item.get('statut', 'N/A')}\n"
            f"Tâche principale: {projet_item.get('tache', 'N/A')}\n"
            f"Début prévu: {proj_debut_orig.strftime('%d %b %Y') if proj_debut_orig else 'N/A'}\n"
            f"Fin prévue: {proj_fin_orig.strftime('%d %b %Y') if proj_fin_orig else 'N/A'}"
        )

        if barre_proj_debut and barre_proj_fin:
            gantt_items_for_df.append(dict(
                Task=proj_nom_complet,
                Start=datetime.combine(barre_proj_debut, datetime.min.time()),
                Finish=datetime.combine(barre_proj_fin + timedelta(days=1), datetime.min.time()),
                Type='Projet',
                Color=get_task_color_sqlite(projet_item.get('tache', 'DEFAULT')),
                TextOnBar=texte_barre_projet,
                Description=description_hover_projet,
                ID=f"P{proj_id}",
                OriginalData=projet_item
            ))

        # Afficher les opérations comme des sous-éléments
        if show_operations:
            for i, operation_item in enumerate(sorted(operations_existantes, key=lambda op: op.get('sequence', 0))):
                op_id = operation_item.get('id', i+1)
                op_nom_base = operation_item.get('description', 'Opération')[:50]
                op_nom_complet = f"    ↳ OP{op_id}: {op_nom_base}"
                y_axis_order.append(op_nom_complet)

                # Pour les opérations, calculer des dates basées sur la séquence
                if proj_debut_orig and proj_fin_orig:
                    total_ops = len(operations_existantes)
                    if total_ops > 0:
                        duration_total = (proj_fin_orig - proj_debut_orig).days
                        duration_per_op = max(1, duration_total // total_ops)
                        
                        op_debut = proj_debut_orig + timedelta(days=i * duration_per_op)
                        op_fin = op_debut + timedelta(days=duration_per_op - 1)
                        
                        # Ajuster la dernière opération
                        if i == total_ops - 1:
                            op_fin = proj_fin_orig
                    else:
                        op_debut = proj_debut_orig
                        op_fin = proj_fin_orig
                        
                    texte_barre_op = f"{op_nom_base} ({operation_item.get('statut', 'À FAIRE')})"
                    description_hover_op = (
                        f"Séquence: {operation_item.get('sequence', '?')}\n"
                        f"Poste: {operation_item.get('poste_travail', 'Non assigné')}\n"
                        f"Temps estimé: {operation_item.get('temps_estime', 0)}h\n"
                        f"Statut: {operation_item.get('statut', 'À FAIRE')}"
                    )

                    gantt_items_for_df.append(dict(
                        Task=op_nom_complet,
                        Start=datetime.combine(op_debut, datetime.min.time()),
                        Finish=datetime.combine(op_fin + timedelta(days=1), datetime.min.time()),
                        Type='Opération',
                        Color=get_sous_tache_color_sqlite(operation_item.get('statut', 'DEFAULT')),
                        TextOnBar=texte_barre_op,
                        Description=description_hover_op,
                        ID=f"OP{proj_id}-{op_id}",
                        OriginalData=operation_item
                    ))
    
    return gantt_items_for_df, y_axis_order, (min_gantt_datetime, max_gantt_datetime)

def add_status_indicators_sqlite(df):
    """Ajoute des indicateurs de statut pour les projets SQLite."""
    today = datetime.now().date()
    df['Status'] = 'Normal'
    
    for i, row in df.iterrows():
        finish_date = row['Finish'].date() - timedelta(days=1)
        start_date = row['Start'].date()
        
        if finish_date < today and row['Type'] == 'Projet':
            original_data = row['OriginalData']
            if original_data.get('statut') not in ['TERMINÉ', 'LIVRAISON', 'ANNULÉ']:
                df.at[i, 'Status'] = 'Retard'
        
        if start_date <= today <= finish_date:
            original_data = row['OriginalData']
            if original_data.get('statut') in ['EN COURS']:
                df.at[i, 'Status'] = 'EnCours'
    
    df['BorderColor'] = df['Status'].map({
        'Normal': 'rgba(0,0,0,0)',
        'Retard': 'rgba(255,0,0,0.8)',
        'EnCours': 'rgba(0,128,0,0.8)',
        'Alerte': 'rgba(255,165,0,0.8)'
    })
    
    return df

def create_gantt_chart_sqlite(df, y_axis_order, date_range, is_mobile=False):
    """Crée un diagramme Gantt Plotly adapté pour SQLite."""
    min_gantt_datetime, max_gantt_datetime = date_range
    
    df['Color'] = df['Color'].astype(str)
    unique_colors = df['Color'].unique()
    color_map = {color_val: color_val for color_val in unique_colors}

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="Color",
        color_discrete_map=color_map,
        text="TextOnBar",
        custom_data=['Description', 'Type', 'ID', 'Start', 'Finish', 'Status']
    )
    
    df_hover_data = df.copy()
    df_hover_data['Finish_Display_Hover'] = df_hover_data['Finish'] - timedelta(days=1)
    
    text_size = 8 if is_mobile else 9
    fig.update_traces(
        customdata=df_hover_data[['Description', 'Type', 'ID', 'Start', 'Finish_Display_Hover', 'Status']],
        hovertemplate=(
            "<b>%{y}</b><br>" +
            "Type: %{customdata[1]}<br>" +
            "ID: %{customdata[2]}<br>" +
            "Début: %{customdata[3]|%d %b %Y}<br>" +
            "Fin: %{customdata[4]|%d %b %Y}<br>" +
            "<i>%{customdata[0]}</i>" +
            "<extra></extra>"
        ),
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=text_size)
    )
    
    text_colors_on_bars = [get_text_color_for_background(bg_hex) for bg_hex in df['Color']]
    fig.update_traces(textfont_color=text_colors_on_bars)

    # Ajouter des formes pour améliorer la visualisation
    shapes = []
    if min_gantt_datetime and max_gantt_datetime:
        current_date_iter_obj = min_gantt_datetime.date()
        end_iter_date_obj = max_gantt_datetime.date() if max_gantt_datetime else current_date_iter_obj

        # Lignes horizontales
        for i in range(len(y_axis_order)):
            y_pos = len(y_axis_order) - 1 - i
            shapes.append(go.layout.Shape(
                type="line", x0=min_gantt_datetime, x1=max_gantt_datetime,
                y0=y_pos - 0.5, y1=y_pos - 0.5,
                line=dict(color="rgba(230,230,230,0.7)", width=0.5), layer="below"
            ))

        # Grille verticale et weekends
        while current_date_iter_obj <= end_iter_date_obj:
            dt_min_time_current = datetime.combine(current_date_iter_obj, datetime.min.time())
            line_color = "rgba(200,200,200,0.7)" if current_date_iter_obj.weekday() == 0 else "rgba(230,230,230,0.5)"
            line_width = 0.8 if current_date_iter_obj.weekday() == 0 else 0.5
            shapes.append(go.layout.Shape(
                type="line", x0=dt_min_time_current, x1=dt_min_time_current, 
                y0=0, y1=1, yref="paper",
                line=dict(color=line_color, width=line_width), layer="below"
            ))
            
            if current_date_iter_obj.weekday() >= 5:
                shapes.append(go.layout.Shape(
                    type="rect", 
                    x0=dt_min_time_current, 
                    x1=datetime.combine(current_date_iter_obj + timedelta(days=1), datetime.min.time()),
                    y0=0, y1=1, yref="paper",
                    fillcolor="rgba(235,235,235,0.6)", line=dict(width=0), layer="below"
                ))
            current_date_iter_obj += timedelta(days=1)
    
    # Ligne "Aujourd'hui"
    today_dt = datetime.now()
    shapes.append(go.layout.Shape(
        type="line", x0=today_dt, x1=today_dt,
        y0=0, y1=1, yref="paper",
        line=dict(color="rgba(255,0,0,0.7)", width=2, dash="dash")
    ))
    
    # Bordures pour statuts spéciaux
    for i, row in df.iterrows():
        if row['Status'] != 'Normal':
            task_idx = y_axis_order.index(row['Task'])
            y_pos = len(y_axis_order) - 1 - task_idx
            shapes.append(go.layout.Shape(
                type="rect",
                x0=row['Start'], x1=row['Finish'],
                y0=y_pos - 0.4, y1=y_pos + 0.4,
                line=dict(color=row['BorderColor'], width=2),
                fillcolor="rgba(0,0,0,0)",
                layer="above"
            ))
    
    fig.update_layout(shapes=shapes)

    # Configuration responsive
    if is_mobile:
        height = min(800, max(500, len(y_axis_order) * 20 + 150))
        margin_top = 60
        margin_bottom = 20
        range_selector_visible = False if len(y_axis_order) > 15 else True
        buttons = [
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=3, label="3m", step="month", stepmode="backward"),
            dict(step="all", label="Tout")
        ]
    else:
        height = max(600, len(y_axis_order) * 28 + 200)
        margin_top = 100
        margin_bottom = 50
        range_selector_visible = True
        buttons = [
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=3, label="3m", step="month", stepmode="backward"),
            dict(count=6, label="6m", step="month", stepmode="backward"),
            dict(count=1, label="1A", step="year", stepmode="backward"),
            dict(step="all", label="Tout")
        ]

    fig.update_layout(
        title=dict(
            text=f"📊 Diagramme Gantt - ERP Production DG Inc. (SQLite)",
            font=dict(size=20, color='#444444'),
            x=0.5,
            xanchor='center',
            y=0.95
        ),
        xaxis_title="📅 Calendrier", 
        yaxis_title="🏭 Projets et Opérations",
        height=height,
        yaxis=dict(
            categoryorder='array',
            categoryarray=y_axis_order,
            autorange="reversed",
            tickfont=dict(size=9 if is_mobile else 9.5)
        ),
        xaxis=dict(
            type='date',
            range=[min_gantt_datetime - timedelta(days=1), max_gantt_datetime + timedelta(days=1)] if min_gantt_datetime and max_gantt_datetime else None,
            showgrid=False,
            tickformat="%d %b\n%Y",
            dtick="M1",
            minor=dict(dtick="D7", showgrid=True, gridcolor='rgba(230,230,230,0.5)', gridwidth=0.5),
            rangeslider_visible=not is_mobile,
            rangeselector=dict(
                buttons=buttons,
                visible=range_selector_visible,
                activecolor="#90caf9"
            )
        ),
        showlegend=False,
        margin=dict(l=10 if is_mobile else 20, r=10 if is_mobile else 20, 
                    t=margin_top, b=margin_bottom),
        plot_bgcolor='rgba(252,252,252,1)',
        paper_bgcolor='rgba(247, 249, 252, 0.8)',
        clickmode="event+select"
    )
    
    return fig

def extract_project_id_from_gantt_id(gantt_id):
    """Extrait l'ID du projet à partir de l'ID d'un élément Gantt."""
    if not gantt_id:
        return None
        
    if gantt_id.startswith("P"):
        try:
            return int(gantt_id[1:])
        except ValueError:
            return None
    elif gantt_id.startswith("OP"):
        parts = gantt_id.replace("OP", "").split('-')
        if len(parts) >= 1:
            try:
                return int(parts[0])
            except ValueError:
                return None
    return None

def display_selected_project_details_sqlite(projet, crm_manager, is_mobile=False):
    """Affiche les détails du projet sélectionné avec style SQLite."""
    # Style CSS amélioré
    st.markdown("""
    <style>
    .project-header-sqlite {
        background: linear-gradient(135deg, #bbdefb 0%, #c8e6c9 100%);
        padding: 18px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
    }
    .project-header-sqlite h2 {
        margin: 0;
        color: #333;
        font-size: 22px;
        display: flex;
        align-items: center;
    }
    .project-header-sqlite h2::before {
        content: "🏭 ";
        margin-right: 10px;
    }
    .info-card-sqlite {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: all 0.3s;
    }
    .info-card-sqlite:hover {
        background-color: #f0f7ff;
        box-shadow: 0 3px 8px rgba(0,0,0,0.08);
    }
    .operation-card {
        background: linear-gradient(to right, #ffffff, #f7f9fc);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
        border-left: 5px solid #3B82F6;
        transition: transform 0.2s;
    }
    .operation-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.12);
    }
    </style>
    """, unsafe_allow_html=True)
    
    projet_id = projet.get('id')
    client_name = get_client_display_name(projet, crm_manager)
    
    # En-tête du projet
    st.markdown(f"""
    <div class="project-header-sqlite">
        <h2>Projet #{projet_id}: {projet.get('nom_projet', 'Sans Nom')}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Informations de base
    if is_mobile:
        st.markdown(f"""
        <div class="info-card-sqlite">
            <div><strong>👤 Client:</strong> {client_name}</div>
            <div><strong>🚦 Statut:</strong> {projet.get('statut', 'N/A')}</div>
            <div><strong>⭐ Priorité:</strong> {projet.get('priorite', 'N/A')}</div>
            <div><strong>✅ Tâche:</strong> {projet.get('tache', 'N/A')}</div>
            <div><strong>📅 Dates:</strong> {projet.get('date_soumis', 'N/A')} → {projet.get('date_prevu', 'N/A')}</div>
            <div><strong>💰 Prix:</strong> {projet.get('prix_estime', 'N/A')}$</div>
        </div>
        """, unsafe_allow_html=True)
        
        if projet.get('description'):
            with st.expander("📝 Description"):
                st.text_area("", value=projet.get('description', ''), height=100, disabled=True, label_visibility="collapsed")
                
        tabs_mobile = st.tabs(["🔧 Opérations", "📦 Matériaux"])
        
        with tabs_mobile[0]:
            operations = projet.get('operations', [])
            if not operations:
                st.info("Aucune opération définie.")
            else:
                for op in operations:
                    st.markdown(f"""
                    <div class="operation-card">
                        <div><strong>OP{op.get('id', '?')}</strong>: {op.get('description', 'N/A')}</div>
                        <div>🏭 Poste: {op.get('poste_travail', 'Non assigné')}</div>
                        <div>⏱️ Temps: {op.get('temps_estime', 0)}h</div>
                        <div>🚦 Statut: {op.get('statut', 'À FAIRE')}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        with tabs_mobile[1]:
            materiaux = projet.get('materiaux', [])
            if not materiaux:
                st.info("Aucun matériau défini.")
            else:
                total_cost = 0
                for mat in materiaux:
                    qty = mat.get('quantite', 0) or 0
                    price = mat.get('prix_unitaire', 0) or 0
                    total = qty * price
                    total_cost += total
                    
                    st.markdown(f"""
                    <div class="info-card-sqlite">
                        <div><strong>{mat.get('code_materiau', 'N/A')}</strong>: {mat.get('designation', 'N/A')}</div>
                        <div>📊 Quantité: {qty} {mat.get('unite', '')}</div>
                        <div>💳 Prix unitaire: {price}$</div>
                        <div>💰 Total: {total}$</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div style="background:#e8f5e8;padding:15px;border-radius:10px;text-align:center;">
                    <strong>💰 Coût total matériaux: {total_cost}$</strong>
                </div>
                """, unsafe_allow_html=True)
    
    else:  # Desktop
        tabs_desktop = st.tabs(["ℹ️ Informations", "🔧 Opérations", "📦 Matériaux"])
        
        with tabs_desktop[0]:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                <div class="info-card-sqlite">
                    <div><strong>👤 Client:</strong> {client_name}</div>
                </div>
                <div class="info-card-sqlite">
                    <div><strong>🚦 Statut:</strong> {projet.get('statut', 'N/A')}</div>
                </div>
                <div class="info-card-sqlite">
                    <div><strong>⭐ Priorité:</strong> {projet.get('priorite', 'N/A')}</div>
                </div>
                <div class="info-card-sqlite">
                    <div><strong>✅ Tâche:</strong> {projet.get('tache', 'N/A')}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="info-card-sqlite">
                    <div><strong>🚀 Date Début:</strong> {projet.get('date_soumis', 'N/A')}</div>
                </div>
                <div class="info-card-sqlite">
                    <div><strong>🏁 Date Fin:</strong> {projet.get('date_prevu', 'N/A')}</div>
                </div>
                <div class="info-card-sqlite">
                    <div><strong>📊 BD-FT:</strong> {projet.get('bd_ft_estime', 'N/A')}h</div>
                </div>
                <div class="info-card-sqlite">
                    <div><strong>💰 Prix:</strong> {projet.get('prix_estime', 'N/A')}$</div>
                </div>
                """, unsafe_allow_html=True)
            
            if projet.get('description'):
                st.markdown("**📝 Description:**")
                st.text_area("", value=projet.get('description', ''), height=100, disabled=True, label_visibility="collapsed")
        
        with tabs_desktop[1]:  # Opérations
            operations = projet.get('operations', [])
            if not operations:
                st.info("Aucune opération définie en SQLite.")
            else:
                operations_data = []
                for op in operations:
                    operations_data.append({
                        "ID": op.get('id', '?'),
                        "Séquence": op.get('sequence', '?'),
                        "Description": op.get('description', 'N/A'),
                        "Poste": op.get('poste_travail', 'Non assigné'),
                        "Temps (h)": op.get('temps_estime', 0),
                        "Ressource": op.get('ressource', 'N/A'),
                        "Statut": op.get('statut', 'À FAIRE')
                    })
                
                operations_df = pd.DataFrame(operations_data)
                st.dataframe(operations_df, use_container_width=True)
        
        with tabs_desktop[2]:  # Matériaux
            materiaux = projet.get('materiaux', [])
            if not materiaux:
                st.info("Aucun matériau défini en SQLite.")
            else:
                materiaux_data = []
                total_cost = 0
                for mat in materiaux:
                    qty = mat.get('quantite', 0) or 0
                    price = mat.get('prix_unitaire', 0) or 0
                    total = qty * price
                    total_cost += total
                    
                    materiaux_data.append({
                        "Code": mat.get('code_materiau', 'N/A'),
                        "Désignation": mat.get('designation', 'N/A'),
                        "Quantité": f"{qty} {mat.get('unite', '')}",
                        "Prix Unit.": f"{price}$",
                        "Total": f"{total}$",
                        "Fournisseur": mat.get('fournisseur', 'N/A')
                    })
                
                materiaux_df = pd.DataFrame(materiaux_data)
                st.dataframe(materiaux_df, use_container_width=True)
                
                st.markdown(f"""
                <div style="background:#e8f5e8;padding:15px;border-radius:10px;text-align:center;margin-top:15px;">
                    <strong>💰 Coût total matériaux: {total_cost}$</strong>
                </div>
                """, unsafe_allow_html=True)
    
    # Bouton fermer
    if st.button("✖️ Fermer", use_container_width=is_mobile, key="gantt_close_details_sqlite"):
        st.session_state.pop('selected_project_id', None)
        st.rerun()

def app():
    """Application principale Gantt adaptée pour SQLite"""
    # Style global
    st.markdown("""
    <style>
    .main-title-gantt {
        background: linear-gradient(135deg, #a5d8ff 0%, #ffd6e0 100%);
        padding: 20px;
        border-radius: 12px;
        color: #333;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
    }
    .main-title-gantt h1 {
        margin: 0;
        font-size: 28px;
        font-weight: 600;
    }
    .filter-container-gantt {
        background-color: #f7f9fc;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.08);
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Titre
    st.markdown('<div class="main-title-gantt"><h1>📊 Vue Gantt - ERP Production DG Inc.</h1></div>', unsafe_allow_html=True)

    # Vérifier la disponibilité des gestionnaires SQLite
    if 'gestionnaire' not in st.session_state:
        st.error("❌ Gestionnaire de projets SQLite non initialisé.")
        return
        
    if 'gestionnaire_crm' not in st.session_state:
        st.error("❌ Gestionnaire CRM non initialisé.")
        return

    gestionnaire = st.session_state.gestionnaire
    crm_manager = st.session_state.gestionnaire_crm
    is_mobile = is_mobile_device()

    if not gestionnaire.projets:
        st.info("Aucun projet à afficher dans le Gantt SQLite.")
        return

    # Section Filtres
    with st.expander("🔍 Filtres et Options", expanded=not is_mobile):
        filter_cols = st.columns([1, 1] if is_mobile else [1, 1, 1])
        
        with filter_cols[0]:
            available_statuts = ["Tous"] + sorted(list(set([p.get('statut', 'N/A') for p in gestionnaire.projets if p.get('statut')])))
            selected_statut = st.selectbox("Statut:", available_statuts)
        
        with filter_cols[1]:
            available_priorities = ["Toutes"] + sorted(list(set([p.get('priorite', 'N/A') for p in gestionnaire.projets if p.get('priorite')])))
            selected_priority = st.selectbox("Priorité:", available_priorities)
        
        if not is_mobile and len(filter_cols) > 2:
            with filter_cols[2]:
                show_operations = st.checkbox("Afficher opérations", value=True)
        else:
            show_operations = st.checkbox("Afficher opérations", value=True)
        
        search_term = st.text_input("🔍 Rechercher un projet:", "")
    
    # Bouton retour si un projet est sélectionné
    if st.session_state.get('selected_project_id'):
        if st.button("⬅️ Retour à la vue d'ensemble", 
                     key="back_button_sqlite", 
                     on_click=lambda: st.session_state.pop('selected_project_id', None),
                     use_container_width=is_mobile):
            st.rerun()
    
    # Appliquer les filtres
    filtered_projets = gestionnaire.projets
    
    if selected_statut != "Tous":
        filtered_projets = [p for p in filtered_projets if p.get('statut') == selected_statut]
    
    if selected_priority != "Toutes":
        filtered_projets = [p for p in filtered_projets if p.get('priorite') == selected_priority]
    
    if search_term:
        term_lower = search_term.lower()
        filtered_projets = [p for p in filtered_projets if 
                           term_lower in str(p.get('nom_projet', '')).lower() or
                           term_lower in get_client_display_name(p, crm_manager).lower() or
                           term_lower in str(p.get('description', '')).lower()]
    
    # Préparer les données Gantt
    gantt_data, y_axis_order, date_range = prepare_gantt_data_sqlite(
        filtered_projets, 
        crm_manager, 
        show_operations=show_operations
    )
    
    if not gantt_data:
        st.info("Aucune donnée de projet ne correspond aux critères de filtrage SQLite.")
        return
    
    # Création du DataFrame et graphique
    df = pd.DataFrame(gantt_data)
    df = add_status_indicators_sqlite(df)
    fig = create_gantt_chart_sqlite(df, y_axis_order, date_range, is_mobile)
    
    # Affichage du graphique
    st.plotly_chart(fig, use_container_width=True)
    
    # Statistiques rapides
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("📊 Projets affichés", len(filtered_projets))
    with col_stats2:
        en_cours = len([p for p in filtered_projets if p.get('statut') == 'EN COURS'])
        st.metric("🚀 En cours", en_cours)
    with col_stats3:
        termines = len([p for p in filtered_projets if p.get('statut') == 'TERMINÉ'])
        st.metric("✅ Terminés", termines)
    
    # Affichage des détails si un projet est sélectionné
    if st.session_state.get('selected_project_id'):
        projet_id = st.session_state.selected_project_id
        projet = next((p for p in gestionnaire.projets if p.get('id') == projet_id), None)
        
        if projet:
            display_selected_project_details_sqlite(projet, crm_manager, is_mobile)
        else:
            st.warning(f"Projet #{projet_id} non trouvé en SQLite.")
            st.session_state.pop('selected_project_id', None)
    
    elif is_mobile:
        st.info("📱 Touchez une barre du diagramme pour voir les détails du projet.")

if __name__ == "__main__":
    app()
