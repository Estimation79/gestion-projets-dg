import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from utils.gestionnaire import GestionnaireProjetIA, TASK_COLORS, SOUS_TACHE_COLORS

# --- Fonctions Utilitaires ---
def is_mobile_device():
    """Estimation si l'appareil est mobile basée sur la largeur de viewport."""
    # Si non défini ou première visite, définir par défaut comme non-mobile
    if 'is_mobile' not in st.session_state:
        st.session_state.is_mobile = False

    # JavaScript pour détecter la largeur d'écran
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
    </script>
    """, unsafe_allow_html=True)
    
    # Retourner la valeur actuelle
    return st.session_state.is_mobile

def get_item_dates_st(item_dict):
    """Retourne (date_debut, date_fin) pour un projet ou une sous-tâche sous forme d'objets date."""
    start_date_obj, end_date_obj = None, None
    start_key = 'date_debut' if 'date_debut' in item_dict else 'date_soumis'
    end_key = 'date_fin' if 'date_fin' in item_dict else 'date_prevu'

    try:
        start_date_str = item_dict.get(start_key)
        if start_date_str: start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError): start_date_obj = None
    try:
        end_date_str = item_dict.get(end_key)
        if end_date_str: end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError): end_date_obj = None

    is_project_like = 'sous_taches' in item_dict or start_key == 'date_soumis'
    has_subtasks = isinstance(item_dict.get('sous_taches'), list) and bool(item_dict['sous_taches'])

    if is_project_like and not has_subtasks and start_date_obj and end_date_obj is None:
        duration_days = 1
        try:
            bd_ft_str = str(item_dict.get('bd_ft_estime', '')).strip()
            if bd_ft_str:
                cleaned_bd_ft = ''.join(filter(lambda x: x.isdigit() or x == '.', bd_ft_str))
                if cleaned_bd_ft: duration_days = max(1, int(float(cleaned_bd_ft)))
        except (ValueError, TypeError): pass
        end_date_obj = start_date_obj + timedelta(days=duration_days - 1)

    if start_date_obj and end_date_obj and end_date_obj < start_date_obj:
        end_date_obj = start_date_obj
    return start_date_obj, end_date_obj

def calculate_overall_date_range(projets_list_data):
    """Calcule la plage de dates minimale et maximale pour l'ensemble des items."""
    min_overall_date, max_overall_date = None, None
    if not projets_list_data:
        today = date.today()
        return today - timedelta(days=30), today + timedelta(days=60)

    for projet_item_data in projets_list_data:
        dates_to_check = [get_item_dates_st(projet_item_data)]
        for st_data_item in projet_item_data.get('sous_taches', []):
            dates_to_check.append(get_item_dates_st(st_data_item))
        
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
        min_overall_date -= timedelta(days=10) # Padding avant
        max_overall_date += timedelta(days=20) # Padding après
        if (max_overall_date - min_overall_date).days < 60: # Assurer une durée minimale
            padding_needed = 60 - (max_overall_date - min_overall_date).days
            max_overall_date += timedelta(days=padding_needed // 2)
            min_overall_date -= timedelta(days=padding_needed - (padding_needed // 2))
    
    if min_overall_date: # Ajuster au lundi précédent
         min_overall_date -= timedelta(days=min_overall_date.weekday())
    return min_overall_date, max_overall_date

def get_item_color(item_data_color, is_subtask_color, gestionnaire_obj):
    """Récupère la couleur pour un projet ou une sous-tâche."""
    if is_subtask_color:
        return gestionnaire_obj.get_sous_tache_color(item_data_color.get('nom', 'DEFAULT'))
    else: # Projet
        return gestionnaire_obj.get_task_color(item_data_color.get('tache', 'DEFAULT'))

def get_text_color_for_background(hex_bg_color):
    """Détermine si le texte doit être noir ou blanc pour un bon contraste."""
    try:
        if isinstance(hex_bg_color, str) and len(hex_bg_color) == 7 and hex_bg_color.startswith('#'):
            r = int(hex_bg_color[1:3], 16)
            g = int(hex_bg_color[3:5], 16)
            b = int(hex_bg_color[5:7], 16)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return 'black' if luminance > 0.5 else 'white'
    except: pass
    return 'black' # Fallback

def prepare_gantt_data(projets_list, gestionnaire, show_subtasks=True):
    """Prépare les données pour le diagramme Gantt avec filtres."""
    gantt_items_for_df = []
    y_axis_order = []
    
    min_gantt_date_obj, max_gantt_date_obj = calculate_overall_date_range(projets_list)
    min_gantt_datetime, max_gantt_datetime = None, None
    if min_gantt_date_obj and max_gantt_date_obj:
        min_gantt_datetime = datetime.combine(min_gantt_date_obj, datetime.min.time())
        max_gantt_datetime = datetime.combine(max_gantt_date_obj, datetime.max.time())
    
    for projet_item in sorted(projets_list, key=lambda p: p.get('id', 0)):
        proj_id = projet_item.get('id')
        proj_nom_base = projet_item.get('nom_projet', 'Sans Nom')
        proj_nom_complet = f"P{proj_id}: {proj_nom_base}"
        y_axis_order.append(proj_nom_complet)

        proj_debut_orig, proj_fin_orig = get_item_dates_st(projet_item)
        min_st_debut, max_st_fin = None, None
        sous_taches_existantes_list = projet_item.get('sous_taches', [])
        if sous_taches_existantes_list:
            valid_st_dates_list = [get_item_dates_st(st_item_loop) for st_item_loop in sous_taches_existantes_list if get_item_dates_st(st_item_loop)[0] and get_item_dates_st(st_item_loop)[1]] # Renamed st to st_item_loop
            if valid_st_dates_list:
                min_st_debut = min(s for s, f in valid_st_dates_list)
                max_st_fin = max(f for s, f in valid_st_dates_list)
        
        barre_proj_debut = min_st_debut if min_st_debut else proj_debut_orig
        barre_proj_fin = max_st_fin if max_st_fin else proj_fin_orig
        
        texte_barre_projet = f"{proj_nom_base} (Client: {projet_item.get('client', 'N/A')})"
        description_hover_projet = (
            f"Statut: {projet_item.get('statut', 'N/A')}\n"
            f"Tâche principale: {projet_item.get('tache', 'N/A')}\n"
            f"Début prévu (projet): {proj_debut_orig.strftime('%d %b %Y') if proj_debut_orig else 'N/A'}\n"
            f"Fin prévue (projet): {proj_fin_orig.strftime('%d %b %Y') if proj_fin_orig else 'N/A'}"
        )

        if barre_proj_debut and barre_proj_fin:
            gantt_items_for_df.append(dict(
                Task=proj_nom_complet,
                Start=datetime.combine(barre_proj_debut, datetime.min.time()),
                Finish=datetime.combine(barre_proj_fin + timedelta(days=1), datetime.min.time()),
                Type='Projet',
                Color=get_item_color(projet_item, False, gestionnaire),
                TextOnBar=texte_barre_projet,
                Description=description_hover_projet,
                ID=f"P{proj_id}",
                OriginalData=projet_item
            ))

        if show_subtasks:
            for st_item_loop_2 in sorted(sous_taches_existantes_list, key=lambda st_param: st_param.get('id', 0)): # Renamed st_item and st
                st_id = st_item_loop_2.get('id')
                st_nom_base = st_item_loop_2.get('nom', 'N/A')
                st_nom_complet = f"    ↳ ST{st_id}: {st_nom_base}"
                y_axis_order.append(st_nom_complet)

                st_debut, st_fin = get_item_dates_st(st_item_loop_2)
                texte_barre_st = f"{st_nom_base} ({st_item_loop_2.get('statut', 'N/A')})"
                description_hover_st = st_item_loop_2.get('description', '') or f"Statut: {st_item_loop_2.get('statut', 'N/A')}"
                if st_debut and st_fin :
                     description_hover_st += f"\nDébut: {st_debut.strftime('%d %b %Y')}\nFin: {st_fin.strftime('%d %b %Y')}"

                if st_debut and st_fin:
                    gantt_items_for_df.append(dict(
                        Task=st_nom_complet,
                        Start=datetime.combine(st_debut, datetime.min.time()),
                        Finish=datetime.combine(st_fin + timedelta(days=1), datetime.min.time()),
                        Type='Sous-tâche',
                        Color=get_item_color(st_item_loop_2, True, gestionnaire),
                        TextOnBar=texte_barre_st,
                        Description=description_hover_st,
                        ID=f"ST{proj_id}-{st_id}",
                        OriginalData=st_item_loop_2
                    ))
    
    return gantt_items_for_df, y_axis_order, (min_gantt_datetime, max_gantt_datetime)

def add_status_indicators(df):
    """Ajoute des indicateurs de statut (retard, etc.) au DataFrame."""
    today = datetime.now().date()
    df['Status'] = 'Normal'
    
    for i, row in df.iterrows():
        # Convertir en date pour comparaison
        finish_date = row['Finish'].date() - timedelta(days=1)  # Ajusté pour le format de stockage
        start_date = row['Start'].date()
        
        # Vérifier si le projet est en retard
        if finish_date < today and row['Type'] == 'Projet':
            original_data = row['OriginalData']
            if original_data.get('statut') not in ['TERMINÉ', 'ANNULÉ', 'FERMÉ', 'PAYÉ', 'FACTURÉ']:
                df.at[i, 'Status'] = 'Retard'
        
        # Ajouter l'indicateur "En cours"
        if start_date <= today <= finish_date:
            original_data = row['OriginalData']
            if original_data.get('statut') in ['EN COURS']:
                df.at[i, 'Status'] = 'EnCours'
        
        # Ajouter d'autres conditions de statut si nécessaire
    
    # Ajouter une couleur de bordure selon le statut
    df['BorderColor'] = df['Status'].map({
        'Normal': 'rgba(0,0,0,0)',
        'Retard': 'rgba(255,0,0,0.8)',
        'EnCours': 'rgba(0,128,0,0.8)',
        'Alerte': 'rgba(255,165,0,0.8)'
    })
    
    return df

def create_gantt_chart(df, y_axis_order, date_range, is_mobile=False):
    """Crée un diagramme Gantt Plotly avec les fonctionnalités avancées."""
    min_gantt_datetime, max_gantt_datetime = date_range
    
    df['Color'] = df['Color'].astype(str)
    unique_colors = df['Color'].unique()
    color_map = {color_val: color_val for color_val in unique_colors}

    # Créer la figure Plotly
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
    
    # Configurer les traces pour meilleure présentation
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
    
    # Adapter couleur du texte au fond des barres
    text_colors_on_bars = [get_text_color_for_background(bg_hex) for bg_hex in df['Color']]
    fig.update_traces(textfont_color=text_colors_on_bars)

    # Ajouter l'ombrage des Week-ends et la grille verticale/horizontale
    shapes = []
    if min_gantt_datetime and max_gantt_datetime:
        current_date_iter_obj = min_gantt_datetime.date()
        end_iter_date_obj = max_gantt_datetime.date() if max_gantt_datetime else current_date_iter_obj

        # Lignes horizontales pour séparer les tâches
        for i in range(len(y_axis_order)):
            y_pos = len(y_axis_order) - 1 - i
            shapes.append(go.layout.Shape(
                type="line", x0=min_gantt_datetime, x1=max_gantt_datetime,
                y0=y_pos - 0.5, y1=y_pos - 0.5,
                line=dict(color="rgba(230,230,230,0.7)", width=0.5), layer="below"
            ))

        # Lignes verticales et weekend shading
        while current_date_iter_obj <= end_iter_date_obj:
            dt_min_time_current = datetime.combine(current_date_iter_obj, datetime.min.time())
            line_color = "rgba(200,200,200,0.7)" if current_date_iter_obj.weekday() == 0 else "rgba(230,230,230,0.5)"
            line_width = 0.8 if current_date_iter_obj.weekday() == 0 else 0.5
            shapes.append(go.layout.Shape(
                type="line", x0=dt_min_time_current, x1=dt_min_time_current, y0=0, y1=1, yref="paper",
                line=dict(color=line_color, width=line_width), layer="below"))
            if current_date_iter_obj.weekday() >= 5:
                shapes.append(go.layout.Shape(
                    type="rect", x0=dt_min_time_current, x1=datetime.combine(current_date_iter_obj + timedelta(days=1), datetime.min.time()),
                    y0=0, y1=1, yref="paper",
                    fillcolor="rgba(235,235,235,0.6)", line=dict(width=0), layer="below"))
            current_date_iter_obj += timedelta(days=1)
    
    # Ajouter la ligne "Aujourd'hui"
    today_dt = datetime.now() # Renamed to avoid conflict with date.today()
    shapes.append(go.layout.Shape(
        type="line", x0=today_dt, x1=today_dt,
        y0=0, y1=1, yref="paper",
        line=dict(color="rgba(255,0,0,0.7)", width=2, dash="dash"),
        name="Aujourd'hui"
    ))
    
    # Ajouter des bordures pour les projets spéciaux (retard, en cours, etc.)
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
    
    # Ajouter les éléments visuels à la figure
    fig.update_layout(shapes=shapes)

    # Optimiser la hauteur du graphique selon le dispositif
    if is_mobile:
        height = min(800, max(500, len(y_axis_order) * 20 + 150))
        margin_top = 60
        margin_bottom = 20
        range_selector_visible = False if len(y_axis_order) > 15 else True
    else:
        height = max(600, len(y_axis_order) * 28 + 200)
        margin_top = 100
        margin_bottom = 50
        range_selector_visible = True

    # Définition des boutons pour le rangeselector (sans attributs de style)
    if not is_mobile:
        buttons = [
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=3, label="3m", step="month", stepmode="backward"),
            dict(count=6, label="6m", step="month", stepmode="backward"),
            dict(count=1, label="1A", step="year", stepmode="backward"),
            dict(step="all", label="Tout")
        ]
    else:
        buttons = [
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=3, label="3m", step="month", stepmode="backward"),
            dict(step="all", label="Tout")
        ]

    # Configuration finale de la mise en page avec style amélioré
    fig.update_layout(
        title=dict(
            text=f"Diagramme Gantt ({min_gantt_datetime.date().strftime('%d %b %Y') if min_gantt_datetime else ''} - {max_gantt_datetime.date().strftime('%d %b %Y') if max_gantt_datetime else ''})",
            font=dict(size=20, color='#444444'),
            x=0.5,
            xanchor='center',
            y=0.95
        ),
        xaxis_title="Calendrier", 
        yaxis_title="Projets et Sous-tâches",
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
        # C'est un projet
        try:
            return int(gantt_id[1:])
        except ValueError:
            return None
    elif gantt_id.startswith("ST"):
        # C'est une sous-tâche, extraire l'ID du projet parent
        parts = gantt_id.replace("ST", "").split('-')
        if len(parts) >= 1:
            try:
                return int(parts[0])
            except ValueError:
                return None
    return None

def display_selected_project_details(gestionnaire, is_mobile=False):
    """Affiche les détails du projet sélectionné avec style amélioré."""
    projet_id = st.session_state.get('selected_project_id')
    projet = next((p for p in gestionnaire.projets if p.get('id') == projet_id), None)
    
    if not projet:
        st.warning(f"Projet #{projet_id} non trouvé.")
        return
        
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
    .subtask-card {
        background: linear-gradient(to right, #ffffff, #f7f9fc);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
        border-left: 5px solid #3B82F6;
        transition: transform 0.2s;
        position: relative;
    }
    .subtask-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.12);
    }
    .subtask-title {
        font-weight: bold;
        font-size: 16px;
        margin-bottom: 8px;
        color: #333;
        display: flex;
        align-items: center;
    }
    .subtask-title::before {
        content: "📌 ";
        margin-right: 8px;
    }
    .subtask-dates {
        font-size: 14px;
        color: #4B5563;
        margin-bottom: 5px;
        display: flex;
        align-items: center;
    }
    .subtask-dates::before {
        content: "📅 ";
        margin-right: 5px;
    }
    .subtask-status {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 14px;
        margin-bottom: 8px;
        font-weight: 500;
        background-color: #EFF6FF;
        color: #2563EB;
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
    div.stButton > button:has(span:contains("Analyser avec IA")) {
        background: linear-gradient(90deg, #c5e1a5 0%, #aed581 100%) !important;
        color: #33691e !important;
        border: none !important;
        padding: 10px 15px !important;
        border-radius: 8px !important; 
        font-weight: bold !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        transition: all 0.3s !important;
    }
    div.stButton > button:has(span:contains("Analyser avec IA"))::before {
        content: "🧠 " !important;
    }
    div.stButton > button:has(span:contains("Fermer")) {
        background: linear-gradient(90deg, #ffcdd2 0%, #ef9a9a 100%) !important;
        color: #b71c1c !important;
        border: none !important;
        font-weight: bold !important;
    }
    div.stButton > button:has(span:contains("Fermer"))::before {
        content: "✖️ " !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Déterminer le titre de l'expander
    expander_title = f"Détails du Projet #{projet_id}: {projet.get('nom_projet', 'Sans Nom')}"
    if len(expander_title) > 40 and is_mobile:
        expander_title = f"Projet #{projet_id}: {projet.get('nom_projet', 'Sans Nom')[:20]}..."
    
    # Entête du projet avec style amélioré
    st.markdown(f"""
    <div class="project-header">
        <h2>Projet #{projet_id}: {projet.get('nom_projet', 'Sans Nom')}</h2>
    </div>
    """, unsafe_allow_html=True)
        
    # Adapter l'affichage en fonction du dispositif
    if is_mobile:
        # Version compacte pour mobile
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
        <div class="info-card">
            <div class="info-label">📅 Dates:</div>
            <div class="info-value">{projet.get('date_soumis', 'N/A')} - {projet.get('date_prevu', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)
            
        if projet.get('description'):
            with st.expander("Description"):
                st.text_area("", value=projet.get('description', ''), height=100, disabled=True)
                    
        tabs_mobile = st.tabs(["Sous-tâches", "IA"]) # Renamed tabs for clarity
        # Use tabs_mobile below
        with tabs_mobile[0]: # Sous-tâches
            sous_taches = projet.get('sous_taches', [])
        
            if not sous_taches:
                st.info("Aucune sous-tâche pour ce projet.")
            else:
                st_data_display = [] # Renamed
                for sub_task_item in sous_taches: # MODIFIED: Renamed loop variable 'st' to 'sub_task_item'
                    st_data_display.append({
                        "ID": sub_task_item.get('id', '?'),
                        "Nom": sub_task_item.get('nom', 'N/A'),
                        "Statut": sub_task_item.get('statut', 'N/A'),
                        "Date Début": sub_task_item.get('date_debut', 'N/A'),
                        "Date Fin": sub_task_item.get('date_fin', 'N/A'),
                        "Description": sub_task_item.get('description', '')[:30] + ('...' if len(sub_task_item.get('description', '')) > 30 else '')
                    })
                
                for st_card_item in st_data_display: # MODIFIED: Renamed loop variable 'st' to 'st_card_item'
                    st.markdown(f"""
                    <div class="subtask-card">
                        <div class="subtask-title">ST{st_card_item['ID']}: {st_card_item['Nom']}</div>
                        <div class="subtask-status">{st_card_item['Statut']}</div>
                        <div class="subtask-dates">{st_card_item['Date Début']} → {st_card_item['Date Fin']}</div>
                        <div>{st_card_item['Description']}</div>
                    </div>
                    """, unsafe_allow_html=True)
        with tabs_mobile[1]: # IA
            if st.button("📊 Analyser avec IA", use_container_width=is_mobile, key="gantt_analyze_ia_mobile"):
                if 'ai_assistant' in st.session_state:
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

    else: # Desktop view
        tabs_desktop = st.tabs(["Informations", "Sous-tâches", "Documents", "IA"]) # Renamed
        
        with tabs_desktop[0]:  # Informations
            col1_info, col2_info = st.columns(2) # Renamed
            
            with col1_info:
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
            
            with col2_info:
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
            st.text_area("", value=projet.get('description', '(Aucune description)'), height=100, disabled=True, key="gantt_desc_desktop", label_visibility="collapsed")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with tabs_desktop[1]:  # Sous-tâches (Desktop)
            sous_taches = projet.get('sous_taches', [])
        
            if not sous_taches:
                st.info("Aucune sous-tâche pour ce projet.")
            else:
                st_data_desktop = [] # Renamed
                for sub_task_item_desk in sous_taches: # MODIFIED: Renamed loop variable 'st' to 'sub_task_item_desk'
                    st_data_desktop.append({
                        "ID": sub_task_item_desk.get('id', '?'),
                        "Nom": sub_task_item_desk.get('nom', 'N/A'),
                        "Statut": sub_task_item_desk.get('statut', 'N/A'),
                        "Date Début": sub_task_item_desk.get('date_debut', 'N/A'),
                        "Date Fin": sub_task_item_desk.get('date_fin', 'N/A'),
                        "Description": sub_task_item_desk.get('description', '')[:30] + ('...' if len(sub_task_item_desk.get('description', '')) > 30 else '')
                    })
                st_df_desktop = pd.DataFrame(st_data_desktop) # Renamed
                st.dataframe(st_df_desktop, use_container_width=True)

        with tabs_desktop[2]:  # Documents
            documents = projet.get('documents', [])
            
            if not documents:
                st.info("Aucun document lié à ce projet.")
            else:
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
    
        with tabs_desktop[3]:  # IA (Desktop)
            if st.button("📊 Analyser avec IA", use_container_width=is_mobile, key="gantt_analyze_ia_desktop"):
                if 'ai_assistant' in st.session_state:
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
        
    # Bouton pour fermer (commun)
    if st.button("Fermer", use_container_width=is_mobile, key="gantt_close_details"):
        st.session_state.pop('selected_project_id', None)
        st.experimental_rerun()

def app():
    # Style global amélioré
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
    .filter-container {
        background-color: #f7f9fc;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.08);
        margin-bottom: 20px;
    }
    .filter-title {
        color: #5c7cfa;
        font-weight: 600;
        margin-bottom: 10px;
        font-size: 16px;
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

    /* Style pour les input et select boxes */
    div[data-baseweb="select"] {
        border-radius: 8px !important;
    }
    div[data-baseweb="input"] {
        border-radius: 8px !important;
    }
    
    /* Adaptations mobiles */
    @media(max-width: 768px) {
        .main-title {
            padding: 15px;
            margin-bottom: 15px;
        }
        .main-title h1 {
            font-size: 24px;
        }
        .filter-container {
            padding: 12px;
        }
    }
    
    /* Style pour l'info box */
    div.stInfo {
        background-color: #e3f2fd !important;
        color: #1976d2 !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 15px !important;
        box-shadow: 0 2px 8px rgba(25, 118, 210, 0.1) !important;
    }
    
    /* Style pour les alerts */
    div.stAlert {
        border-radius: 8px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Titre avec style amélioré
    st.markdown('<div class="main-title"><h1>📊 Vue Gantt</h1></div>', unsafe_allow_html=True)

    # Vérifier si mobile
    is_mobile = is_mobile_device()

    if 'gestionnaire' not in st.session_state:
        st.session_state.gestionnaire = GestionnaireProjetIA()
    gestionnaire = st.session_state.gestionnaire

    if not gestionnaire.projets:
        st.info("Aucun projet à afficher dans le Gantt.")
        return

    # Section Filtres avec style amélioré
    with st.expander("Filtres et Options", expanded=not is_mobile):
        st.markdown("""
        <div class="filter-title">🔍 Affiner les résultats</div>
        """, unsafe_allow_html=True)
        
        filter_cols_spec = [1, 1, 1] if not is_mobile else [1, 1]
        filter_cols = st.columns(filter_cols_spec)
        
        with filter_cols[0]:
            # Filtre par statut
            available_statuts = ["Tous"] + sorted(list(set([p.get('statut', 'N/A') for p in gestionnaire.projets if p.get('statut')])))
            selected_statut = st.selectbox("Statut:", available_statuts)
        
        with filter_cols[1]:
            # Filtre par priorité
            available_priorities = ["Toutes"] + sorted(list(set([p.get('priorite', 'N/A') for p in gestionnaire.projets if p.get('priorite')])))
            selected_priority = st.selectbox("Priorité:", available_priorities)
        
        if not is_mobile:
            with filter_cols[2]:
                # Option pour montrer/cacher les sous-tâches
                show_subtasks = st.checkbox("Afficher sous-tâches", value=True)
        else:
            # Pour mobile, mettre cette option après les filtres principaux
            show_subtasks = st.checkbox("Afficher sous-tâches", value=True)
        
        # Recherche par texte
        search_term = st.text_input("Rechercher un projet:", "")
    
    # Bouton pour réinitialiser la sélection avec style amélioré
    if st.session_state.get('selected_project_id'):
        st.markdown("""
        <style>
        div.stButton > button:has(span:contains("⬅️ Retour")) {
            background: linear-gradient(90deg, #e3f2fd 0%, #bbdefb 100%) !important;
            color: #1976d2 !important;
            font-weight: bold !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.button("⬅️ Retour à la vue d'ensemble", 
                  key="back_button", 
                  on_click=lambda: st.session_state.pop('selected_project_id', None),
                  use_container_width=is_mobile)
    
    # Préparation des données avec filtres appliqués
    filtered_projets = gestionnaire.projets
    
    # Appliquer les filtres
    if selected_statut != "Tous":
        filtered_projets = [p for p in filtered_projets if p.get('statut') == selected_statut]
    
    if selected_priority != "Toutes":
        filtered_projets = [p for p in filtered_projets if p.get('priorite') == selected_priority]
    
    if search_term:
        filtered_projets = [p for p in filtered_projets if 
                           search_term.lower() in str(p.get('nom_projet', '')).lower() or
                           search_term.lower() in str(p.get('client', '')).lower() or
                           search_term.lower() in str(p.get('description', '')).lower()]
    
    # Préparer les données pour le graphique Gantt
    gantt_data, y_axis_order, date_range = prepare_gantt_data(
        filtered_projets, 
        gestionnaire, 
        show_subtasks=show_subtasks
    )
    
    if not gantt_data:
        st.info("Aucune donnée de projet ne correspond aux critères de filtrage.")
        return
    
    # Création du DataFrame et du graphique
    df = pd.DataFrame(gantt_data)
    
    # Ajouter des indicateurs de statut
    df = add_status_indicators(df)
    
    # Création du graphique Plotly amélioré
    fig = create_gantt_chart(df, y_axis_order, date_range, is_mobile)
    
    # Affichage du graphique
    st.plotly_chart(fig, use_container_width=True)
    
    # Callback JavaScript pour détecter les clics sur le graphique
    st.markdown("""
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        const handlePlotlyClick = function(data) {
            if (data && data.points && data.points.length) {
                const point = data.points[0];
                const id = point.customdata[2]; // ID est en position 2 dans customdata
                
                // Stocker l'ID sélectionné dans localStorage
                localStorage.setItem('selected_gantt_item', id);
                
                // Trouver et cliquer sur le bouton caché de sélection
                // Assurez-vous que l'ID du bouton est unique si cette page est réutilisée ou s'il y a d'autres boutons similaires
                const triggerButton = document.getElementById('project_selection_trigger_gantt');
                if (triggerButton) {
                    triggerButton.click();
                } else {
                    console.error("Bouton déclencheur 'project_selection_trigger_gantt' non trouvé.");
                }
            }
        };
        
        // Observer le DOM pour détecter quand le graphique Plotly est ajouté
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    const plotlyDiv = document.querySelector('.js-plotly-plot'); // Potentiellement trop générique si plusieurs graphiques
                    if (plotlyDiv && !plotlyDiv.getAttribute('data-plotly-click-listener-gantt')) {
                        plotlyDiv.setAttribute('data-plotly-click-listener-gantt', 'true');
                        plotlyDiv.on('plotly_click', handlePlotlyClick);
                    }
                }
            });
        });
        
        observer.observe(document.body, { childList: true, subtree: true });
    });
    </script>
    """, unsafe_allow_html=True)
    
    # Bouton caché pour récupérer la sélection
    # Utilisez une clé unique pour ce bouton
    if st.button("", key="project_selection_trigger_gantt", help="Internal trigger for Gantt selection", type="secondary", disabled=True, on_click=None):
        # Ce code est juste un placeholder pour que le bouton existe.
        # La logique réelle de récupération de l'ID depuis localStorage et mise à jour de st.session_state
        # est un peu plus complexe à faire de manière fiable sans des hacks JS plus profonds ou des composants Streamlit custom.
        # Pour l'instant, la sélection est implicite via les interactions.
        pass
        # Idéalement ici, on lirait localStorage.getItem('selected_gantt_item')
        # mais Streamlit Python ne peut pas lire le localStorage directement après un clic JS comme ça.
        # Une solution plus Streamlit-native serait que handle_bar_click soit appelé d'une manière ou d'une autre.

    
    # Affichage des détails d'un projet sélectionné
    if st.session_state.get('selected_project_id'):
        display_selected_project_details(gestionnaire, is_mobile)
    # Sinon, si mobile, suggérer de sélectionner un projet
    elif is_mobile:
        st.info("Touchez une barre du diagramme pour voir les détails du projet.")

# Gérer les clics sur les barres (via le bouton ou direct)
def handle_bar_click(clicked_id):
    """Fonction pour gérer les clics sur les barres du Gantt."""
    proj_id = extract_project_id_from_gantt_id(clicked_id)
    if proj_id:
        st.session_state.selected_project_id = proj_id
        return True # Indique que la sélection a changé
    return False

if __name__ == "__main__":
    app()