# gantt.py - Vue Gantt Bons de Travail avec Postes de Travail
# Compatible avec l'architecture SQLite unifiée - ERP Production DG Inc.

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date

# --- Configuration des Couleurs pour Bons de Travail ---
BT_COLORS = {
    'BROUILLON': '#FFB74D',
    'VALIDÉ': '#64B5F6', 
    'ENVOYÉ': '#81C784',
    'APPROUVÉ': '#FFA726',
    'EN_COURS': '#26A69A',
    'TERMINÉ': '#9C27B0',
    'ANNULÉ': '#795548',
    'DEFAULT': '#90A4AE'
}

POSTE_COLORS = {
    'À FAIRE': '#FFAB91',
    'EN_COURS': '#80CBC4',
    'TERMINÉ': '#A5D6A7',
    'SUSPENDU': '#B39DDB',
    'ANNULÉ': '#FFCC02',
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

def get_bt_color(bt_statut):
    """Récupère la couleur pour un statut de Bon de Travail"""
    return BT_COLORS.get(bt_statut, BT_COLORS['DEFAULT'])

def get_poste_color(operation_statut):
    """Récupère la couleur pour un statut d'opération/poste"""
    return POSTE_COLORS.get(operation_statut, POSTE_COLORS['DEFAULT'])

def get_company_display_name(bt_data, erp_db):
    """Récupère le nom d'affichage de l'entreprise depuis la base SQLite"""
    try:
        company_id = bt_data.get('company_id')
        if company_id:
            company_result = erp_db.execute_query(
                "SELECT nom FROM companies WHERE id = ?", 
                (company_id,)
            )
            if company_result:
                return company_result[0]['nom']
    except Exception:
        pass
    return bt_data.get('company_nom', 'N/A')

def get_project_display_name(bt_data, erp_db):
    """Récupère le nom d'affichage du projet depuis la base SQLite"""
    try:
        project_id = bt_data.get('project_id')
        if project_id:
            project_result = erp_db.execute_query(
                "SELECT nom_projet FROM projects WHERE id = ?", 
                (project_id,)
            )
            if project_result:
                return project_result[0]['nom_projet']
    except Exception:
        pass
    return bt_data.get('nom_projet', 'N/A')

def get_bt_dates(bt_dict):
    """Retourne (date_debut, date_fin) pour un Bon de Travail depuis SQLite."""
    start_date_obj, end_date_obj = None, None
    
    try:
        # Priorité aux dates de création et échéance
        start_date_str = bt_dict.get('date_creation')
        if start_date_str: 
            # Gérer les formats datetime et date
            if 'T' in start_date_str:
                start_date_obj = datetime.strptime(start_date_str.split('T')[0], "%Y-%m-%d").date()
            else:
                start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError): 
        start_date_obj = None
        
    try:
        end_date_str = bt_dict.get('date_echeance')
        if end_date_str: 
            end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError): 
        end_date_obj = None

    # Si pas de date d'échéance, estimer basé sur les opérations
    if start_date_obj and end_date_obj is None:
        operations = bt_dict.get('operations', [])
        if operations:
            # Calculer durée totale basée sur temps estimé des opérations
            total_hours = sum(op.get('temps_estime', 0) or 0 for op in operations)
            duration_days = max(1, int(total_hours / 8))  # 8h par jour
        else:
            duration_days = 5  # Default 5 jours
        end_date_obj = start_date_obj + timedelta(days=duration_days - 1)

    # Si toujours pas de dates, utiliser aujourd'hui
    if start_date_obj is None:
        start_date_obj = date.today()
    if end_date_obj is None:
        end_date_obj = start_date_obj + timedelta(days=5)

    if start_date_obj and end_date_obj and end_date_obj < start_date_obj:
        end_date_obj = start_date_obj
        
    return start_date_obj, end_date_obj

def get_operation_dates(operation_dict, bt_start_date, bt_end_date, operation_index, total_operations):
    """Calcule les dates d'une opération basée sur sa séquence dans le BT."""
    if not bt_start_date or not bt_end_date or total_operations == 0:
        return bt_start_date, bt_start_date
    
    # Calculer la durée totale du BT
    total_bt_days = (bt_end_date - bt_start_date).days + 1
    
    # Répartir les opérations sur la durée du BT
    if total_operations == 1:
        return bt_start_date, bt_end_date
    
    # Calculer la durée par opération
    days_per_operation = max(1, total_bt_days // total_operations)
    
    # Calculer les dates de cette opération
    op_start = bt_start_date + timedelta(days=operation_index * days_per_operation)
    op_end = op_start + timedelta(days=days_per_operation - 1)
    
    # Ajuster la dernière opération pour qu'elle se termine à la fin du BT
    if operation_index == total_operations - 1:
        op_end = bt_end_date
    
    return op_start, op_end

def calculate_overall_date_range_bt(bts_list_data):
    """Calcule la plage de dates minimale et maximale pour les Bons de Travail."""
    min_overall_date, max_overall_date = None, None
    if not bts_list_data:
        today = date.today()
        return today - timedelta(days=30), today + timedelta(days=60)

    for bt_item_data in bts_list_data:
        bt_start, bt_end = get_bt_dates(bt_item_data)
        
        if bt_start:
            min_overall_date = min(min_overall_date, bt_start) if min_overall_date else bt_start
        if bt_end:
            max_overall_date = max(max_overall_date, bt_end) if max_overall_date else bt_end
    
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

def prepare_gantt_data_bt(bts_list, erp_db, show_postes=True):
    """Prépare les données pour le diagramme Gantt avec Bons de Travail et Postes."""
    gantt_items_for_df = []
    y_axis_order = []
    
    min_gantt_date_obj, max_gantt_date_obj = calculate_overall_date_range_bt(bts_list)
    min_gantt_datetime, max_gantt_datetime = None, None
    if min_gantt_date_obj and max_gantt_date_obj:
        min_gantt_datetime = datetime.combine(min_gantt_date_obj, datetime.min.time())
        max_gantt_datetime = datetime.combine(max_gantt_date_obj, datetime.max.time())
    
    for bt_item in sorted(bts_list, key=lambda bt: bt.get('id', 0)):
        bt_id = bt_item.get('id')
        bt_numero = bt_item.get('numero_document', f'BT-{bt_id}')
        bt_nom_complet = f"📋 {bt_numero}"
        y_axis_order.append(bt_nom_complet)

        bt_debut, bt_fin = get_bt_dates(bt_item)
        
        company_name = get_company_display_name(bt_item, erp_db)
        project_name = get_project_display_name(bt_item, erp_db)
        
        texte_barre_bt = f"{bt_numero} - {company_name}"
        description_hover_bt = (
            f"Statut: {bt_item.get('statut', 'N/A')}\n"
            f"Priorité: {bt_item.get('priorite', 'N/A')}\n"
            f"Projet: {project_name}\n"
            f"Entreprise: {company_name}\n"
            f"Créé: {bt_debut.strftime('%d %b %Y') if bt_debut else 'N/A'}\n"
            f"Échéance: {bt_fin.strftime('%d %b %Y') if bt_fin else 'N/A'}"
        )

        if bt_debut and bt_fin:
            gantt_items_for_df.append(dict(
                Task=bt_nom_complet,
                Start=datetime.combine(bt_debut, datetime.min.time()),
                Finish=datetime.combine(bt_fin + timedelta(days=1), datetime.min.time()),
                Type='Bon de Travail',
                Color=get_bt_color(bt_item.get('statut', 'DEFAULT')),
                TextOnBar=texte_barre_bt,
                Description=description_hover_bt,
                ID=f"BT{bt_id}",
                OriginalData=bt_item
            ))

        # Afficher les opérations/postes comme des sous-éléments
        if show_postes:
            operations_existantes = bt_item.get('operations', [])
            total_ops = len(operations_existantes)
            
            for i, operation_item in enumerate(sorted(operations_existantes, key=lambda op: op.get('sequence_number', 0))):
                op_id = operation_item.get('id', i+1)
                poste_nom = operation_item.get('work_center_name', 'Poste Non Assigné')
                op_description = operation_item.get('description', 'Opération')[:40]
                
                op_nom_complet = f"    🔧 {poste_nom}"
                y_axis_order.append(op_nom_complet)

                # Calculer les dates de l'opération
                op_debut, op_fin = get_operation_dates(operation_item, bt_debut, bt_fin, i, total_ops)
                        
                texte_barre_op = f"{poste_nom} - {op_description}"
                description_hover_op = (
                    f"Séquence: {operation_item.get('sequence_number', '?')}\n"
                    f"Description: {op_description}\n"
                    f"Poste: {poste_nom}\n"
                    f"Département: {operation_item.get('work_center_departement', 'N/A')}\n"
                    f"Temps estimé: {operation_item.get('temps_estime', 0)}h\n"
                    f"Statut: {operation_item.get('statut', 'À FAIRE')}"
                )

                gantt_items_for_df.append(dict(
                    Task=op_nom_complet,
                    Start=datetime.combine(op_debut, datetime.min.time()),
                    Finish=datetime.combine(op_fin + timedelta(days=1), datetime.min.time()),
                    Type='Poste de Travail',
                    Color=get_poste_color(operation_item.get('statut', 'DEFAULT')),
                    TextOnBar=texte_barre_op,
                    Description=description_hover_op,
                    ID=f"OP{bt_id}-{op_id}",
                    OriginalData=operation_item
                ))
    
    return gantt_items_for_df, y_axis_order, (min_gantt_datetime, max_gantt_datetime)

def add_status_indicators_bt(df):
    """Ajoute des indicateurs de statut pour les Bons de Travail."""
    today = datetime.now().date()
    df['Status'] = 'Normal'
    
    for i, row in df.iterrows():
        finish_date = row['Finish'].date() - timedelta(days=1)
        start_date = row['Start'].date()
        
        if finish_date < today and row['Type'] == 'Bon de Travail':
            original_data = row['OriginalData']
            if original_data.get('statut') not in ['TERMINÉ', 'ANNULÉ']:
                df.at[i, 'Status'] = 'Retard'
        
        if start_date <= today <= finish_date:
            original_data = row['OriginalData']
            if original_data.get('statut') in ['EN_COURS', 'VALIDÉ']:
                df.at[i, 'Status'] = 'EnCours'
    
    df['BorderColor'] = df['Status'].map({
        'Normal': 'rgba(0,0,0,0)',
        'Retard': 'rgba(255,0,0,0.8)',
        'EnCours': 'rgba(0,128,0,0.8)',
        'Alerte': 'rgba(255,165,0,0.8)'
    })
    
    return df

def create_gantt_chart_bt(df, y_axis_order, date_range, is_mobile=False):
    """Crée un diagramme Gantt Plotly adapté pour les Bons de Travail."""
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
            text=f"📋 Diagramme Gantt - Bons de Travail & Postes (ERP Production DG Inc.)",
            font=dict(size=20, color='#444444'),
            x=0.5,
            xanchor='center',
            y=0.95
        ),
        xaxis_title="📅 Calendrier", 
        yaxis_title="📋 Bons de Travail & 🔧 Postes",
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

def extract_bt_id_from_gantt_id(gantt_id):
    """Extrait l'ID du Bon de Travail à partir de l'ID d'un élément Gantt."""
    if not gantt_id:
        return None
        
    if gantt_id.startswith("BT"):
        try:
            return int(gantt_id[2:])
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

def display_selected_bt_details(bt_data, erp_db, is_mobile=False):
    """Affiche les détails du Bon de Travail sélectionné."""
    # Style CSS amélioré
    st.markdown("""
    <style>
    .bt-header {
        background: linear-gradient(135deg, #e3f2fd 0%, #f1f8e9 100%);
        padding: 18px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
    }
    .bt-header h2 {
        margin: 0;
        color: #333;
        font-size: 22px;
        display: flex;
        align-items: center;
    }
    .bt-header h2::before {
        content: "📋 ";
        margin-right: 10px;
    }
    .info-card-bt {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: all 0.3s;
    }
    .info-card-bt:hover {
        background-color: #f0f7ff;
        box-shadow: 0 3px 8px rgba(0,0,0,0.08);
    }
    .operation-card-bt {
        background: linear-gradient(to right, #ffffff, #f7f9fc);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
        border-left: 5px solid #2196F3;
        transition: transform 0.2s;
    }
    .operation-card-bt:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.12);
    }
    .status-badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        color: white;
        margin-left: 10px;
    }
    .status-brouillon { background-color: #FF9800; }
    .status-valide { background-color: #2196F3; }
    .status-envoye { background-color: #4CAF50; }
    .status-approuve { background-color: #8BC34A; }
    .status-en-cours { background-color: #00BCD4; }
    .status-termine { background-color: #9C27B0; }
    .status-annule { background-color: #795548; }
    </style>
    """, unsafe_allow_html=True)
    
    bt_id = bt_data.get('id')
    bt_numero = bt_data.get('numero_document', f'BT-{bt_id}')
    company_name = get_company_display_name(bt_data, erp_db)
    project_name = get_project_display_name(bt_data, erp_db)
    statut = bt_data.get('statut', 'N/A')
    
    # En-tête du BT
    status_class = f"status-{statut.lower().replace('_', '-')}"
    st.markdown(f"""
    <div class="bt-header">
        <h2>{bt_numero}
            <span class="status-badge {status_class}">{statut}</span>
        </h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Informations de base
    if is_mobile:
        st.markdown(f"""
        <div class="info-card-bt">
            <div><strong>🏢 Entreprise:</strong> {company_name}</div>
            <div><strong>🏭 Projet:</strong> {project_name}</div>
            <div><strong>⭐ Priorité:</strong> {bt_data.get('priorite', 'N/A')}</div>
            <div><strong>📅 Créé le:</strong> {bt_data.get('date_creation', 'N/A')}</div>
            <div><strong>📅 Échéance:</strong> {bt_data.get('date_echeance', 'N/A')}</div>
            <div><strong>💰 Montant:</strong> {bt_data.get('montant_total', 0)}$</div>
        </div>
        """, unsafe_allow_html=True)
        
        if bt_data.get('notes'):
            with st.expander("📝 Notes"):
                st.text_area("", value=bt_data.get('notes', ''), height=100, disabled=True, label_visibility="collapsed")
                
        tabs_mobile = st.tabs(["🔧 Opérations/Postes", "👥 Assignations", "📊 Statistiques"])
        
        with tabs_mobile[0]:
            operations = bt_data.get('operations', [])
            if not operations:
                st.info("Aucune opération/poste défini pour ce BT.")
            else:
                for op in operations:
                    st.markdown(f"""
                    <div class="operation-card-bt">
                        <div><strong>🔧 {op.get('work_center_name', 'Poste Non Assigné')}</strong></div>
                        <div>📝 {op.get('description', 'N/A')}</div>
                        <div>🏭 Département: {op.get('work_center_departement', 'N/A')}</div>
                        <div>⏱️ Temps: {op.get('temps_estime', 0)}h</div>
                        <div>🚦 Statut: {op.get('statut', 'À FAIRE')}</div>
                        <div>📊 Séquence: {op.get('sequence_number', '?')}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        with tabs_mobile[1]:
            # Afficher les assignations d'employés
            assignations = bt_data.get('assignations', [])
            if not assignations:
                st.info("Aucun employé assigné à ce BT.")
            else:
                for assign in assignations:
                    st.markdown(f"""
                    <div class="info-card-bt">
                        <div><strong>👤 {assign.get('employe_nom', 'N/A')}</strong></div>
                        <div>💼 Poste: {assign.get('employe_poste', 'N/A')}</div>
                        <div>📅 Assigné le: {assign.get('date_assignation', 'N/A')}</div>
                        <div>🚦 Statut: {assign.get('statut', 'N/A')}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        with tabs_mobile[2]:
            # Statistiques TimeTracker
            tt_stats = bt_data.get('timetracker_stats', {})
            st.markdown(f"""
            <div class="info-card-bt">
                <div><strong>⏱️ Sessions pointage:</strong> {tt_stats.get('nb_pointages', 0)}</div>
                <div><strong>👥 Employés distincts:</strong> {tt_stats.get('nb_employes_distinct', 0)}</div>
                <div><strong>🕐 Total heures:</strong> {tt_stats.get('total_heures', 0):.1f}h</div>
                <div><strong>💰 Coût total:</strong> {tt_stats.get('total_cout', 0):.2f}$</div>
            </div>
            """, unsafe_allow_html=True)
    
    else:  # Desktop
        tabs_desktop = st.tabs(["ℹ️ Informations", "🔧 Opérations/Postes", "👥 Assignations", "📊 Statistiques"])
        
        with tabs_desktop[0]:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                <div class="info-card-bt">
                    <div><strong>🏢 Entreprise:</strong> {company_name}</div>
                </div>
                <div class="info-card-bt">
                    <div><strong>🏭 Projet:</strong> {project_name}</div>
                </div>
                <div class="info-card-bt">
                    <div><strong>⭐ Priorité:</strong> {bt_data.get('priorite', 'N/A')}</div>
                </div>
                <div class="info-card-bt">
                    <div><strong>🚦 Statut:</strong> {statut}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="info-card-bt">
                    <div><strong>📅 Date création:</strong> {bt_data.get('date_creation', 'N/A')}</div>
                </div>
                <div class="info-card-bt">
                    <div><strong>📅 Date échéance:</strong> {bt_data.get('date_echeance', 'N/A')}</div>
                </div>
                <div class="info-card-bt">
                    <div><strong>💰 Montant total:</strong> {bt_data.get('montant_total', 0)}$</div>
                </div>
                <div class="info-card-bt">
                    <div><strong>📝 Employé responsable:</strong> {bt_data.get('employee_nom', 'N/A')}</div>
                </div>
                """, unsafe_allow_html=True)
            
            if bt_data.get('notes'):
                st.markdown("**📝 Notes:**")
                st.text_area("", value=bt_data.get('notes', ''), height=100, disabled=True, label_visibility="collapsed")
        
        with tabs_desktop[1]:  # Opérations/Postes
            operations = bt_data.get('operations', [])
            if not operations:
                st.info("Aucune opération/poste défini pour ce BT.")
            else:
                operations_data = []
                for op in operations:
                    operations_data.append({
                        "ID": op.get('id', '?'),
                        "Séquence": op.get('sequence_number', '?'),
                        "Description": op.get('description', 'N/A'),
                        "Poste de Travail": op.get('work_center_name', 'Non assigné'),
                        "Département": op.get('work_center_departement', 'N/A'),
                        "Temps (h)": op.get('temps_estime', 0),
                        "Statut": op.get('statut', 'À FAIRE')
                    })
                
                operations_df = pd.DataFrame(operations_data)
                st.dataframe(operations_df, use_container_width=True)
        
        with tabs_desktop[2]:  # Assignations
            assignations = bt_data.get('assignations', [])
            if not assignations:
                st.info("Aucun employé assigné à ce BT.")
            else:
                assignations_data = []
                for assign in assignations:
                    assignations_data.append({
                        "Employé": assign.get('employe_nom', 'N/A'),
                        "Poste": assign.get('employe_poste', 'N/A'),
                        "Date Assignation": assign.get('date_assignation', 'N/A'),
                        "Statut": assign.get('statut', 'N/A'),
                        "Notes": assign.get('notes_assignation', 'N/A')
                    })
                
                assignations_df = pd.DataFrame(assignations_data)
                st.dataframe(assignations_df, use_container_width=True)
            
            # Réservations de postes
            reservations = bt_data.get('reservations_postes', [])
            if reservations:
                st.markdown("**🏭 Réservations de Postes:**")
                reservations_data = []
                for res in reservations:
                    reservations_data.append({
                        "Poste": res.get('poste_nom', 'N/A'),
                        "Département": res.get('poste_departement', 'N/A'),
                        "Date Prévue": res.get('date_prevue', 'N/A'),
                        "Statut": res.get('statut', 'N/A'),
                        "Notes": res.get('notes_reservation', 'N/A')
                    })
                
                reservations_df = pd.DataFrame(reservations_data)
                st.dataframe(reservations_df, use_container_width=True)
        
        with tabs_desktop[3]:  # Statistiques
            tt_stats = bt_data.get('timetracker_stats', {})
            
            col_stats1, col_stats2 = st.columns(2)
            
            with col_stats1:
                st.markdown("**⏱️ Statistiques TimeTracker:**")
                st.markdown(f"""
                <div class="info-card-bt">
                    <div><strong>Sessions de pointage:</strong> {tt_stats.get('nb_pointages', 0)}</div>
                    <div><strong>Employés distincts:</strong> {tt_stats.get('nb_employes_distinct', 0)}</div>
                    <div><strong>Total heures pointées:</strong> {tt_stats.get('total_heures', 0):.1f}h</div>
                    <div><strong>Coût total:</strong> {tt_stats.get('total_cout', 0):.2f}$</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_stats2:
                st.markdown("**📊 Métriques BT:**")
                operations_count = len(bt_data.get('operations', []))
                assignations_count = len(bt_data.get('assignations', []))
                st.markdown(f"""
                <div class="info-card-bt">
                    <div><strong>Nombre d'opérations:</strong> {operations_count}</div>
                    <div><strong>Employés assignés:</strong> {assignations_count}</div>
                    <div><strong>Progression estimée:</strong> ?%</div>
                    <div><strong>Temps restant estimé:</strong> ? jours</div>
                </div>
                """, unsafe_allow_html=True)
    
    # Bouton fermer
    if st.button("✖️ Fermer", use_container_width=is_mobile, key="gantt_close_bt_details"):
        st.session_state.pop('selected_bt_id', None)
        st.rerun()

def get_bons_travail_with_operations(erp_db):
    """Récupère tous les Bons de Travail avec leurs opérations depuis la base SQLite."""
    try:
        # Récupérer tous les Bons de Travail avec détails complets
        bts_query = '''
            SELECT f.*, 
                   c.nom as company_nom,
                   p.nom_projet,
                   e.prenom || ' ' || e.nom as employee_nom
            FROM formulaires f
            LEFT JOIN companies c ON f.company_id = c.id
            LEFT JOIN projects p ON f.project_id = p.id
            LEFT JOIN employees e ON f.employee_id = e.id
            WHERE f.type_formulaire = 'BON_TRAVAIL'
            ORDER BY f.id DESC
        '''
        
        bts_rows = erp_db.execute_query(bts_query)
        bts_list = []
        
        for bt_row in bts_rows:
            bt_dict = dict(bt_row)
            
            # Récupérer les opérations avec détails des postes de travail
            operations_query = '''
                SELECT o.*, 
                       wc.nom as work_center_name,
                       wc.departement as work_center_departement,
                       wc.capacite_theorique as work_center_capacite,
                       wc.cout_horaire as work_center_cout_horaire
                FROM operations o
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE o.formulaire_bt_id = ?
                ORDER BY o.sequence_number, o.id
            '''
            
            operations_rows = erp_db.execute_query(operations_query, (bt_dict['id'],))
            bt_dict['operations'] = [dict(op_row) for op_row in operations_rows]
            
            # Récupérer les assignations d'employés
            assignations_query = '''
                SELECT bta.*, 
                       e.prenom || ' ' || e.nom as employe_nom,
                       e.poste as employe_poste
                FROM bt_assignations bta
                LEFT JOIN employees e ON bta.employe_id = e.id
                WHERE bta.bt_id = ?
                ORDER BY bta.date_assignation DESC
            '''
            
            assignations_rows = erp_db.execute_query(assignations_query, (bt_dict['id'],))
            bt_dict['assignations'] = [dict(assign_row) for assign_row in assignations_rows]
            
            # Récupérer les réservations de postes
            reservations_query = '''
                SELECT btr.*, 
                       wc.nom as poste_nom,
                       wc.departement as poste_departement
                FROM bt_reservations_postes btr
                LEFT JOIN work_centers wc ON btr.work_center_id = wc.id
                WHERE btr.bt_id = ?
                ORDER BY btr.date_reservation DESC
            '''
            
            reservations_rows = erp_db.execute_query(reservations_query, (bt_dict['id'],))
            bt_dict['reservations_postes'] = [dict(res_row) for res_row in reservations_rows]
            
            # Récupérer les statistiques TimeTracker
            bt_dict['timetracker_stats'] = erp_db.get_statistiques_bt_timetracker(bt_dict['id'])
            
            bts_list.append(bt_dict)
        
        return bts_list
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération des Bons de Travail: {e}")
        return []

def app():
    """Application principale Gantt pour Bons de Travail avec Postes"""
    # Style global
    st.markdown("""
    <style>
    .main-title-gantt-bt {
        background: linear-gradient(135deg, #e1f5fe 0%, #f3e5f5 100%);
        padding: 20px;
        border-radius: 12px;
        color: #333;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
    }
    .main-title-gantt-bt h1 {
        margin: 0;
        font-size: 28px;
        font-weight: 600;
    }
    .filter-container-gantt-bt {
        background-color: #f7f9fc;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.08);
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Titre
    st.markdown('<div class="main-title-gantt-bt"><h1>📋 Vue Gantt - Bons de Travail & Postes</h1></div>', unsafe_allow_html=True)

    # Vérifier la disponibilité de l'ERP Database
    if 'erp_db' not in st.session_state:
        st.error("❌ Base de données ERP non initialisée.")
        st.info("Veuillez d'abord initialiser la base de données depuis la page principale.")
        return

    erp_db = st.session_state.erp_db
    is_mobile = is_mobile_device()

    # Récupérer les Bons de Travail avec opérations
    bts_list = get_bons_travail_with_operations(erp_db)
    
    if not bts_list:
        st.info("Aucun Bon de Travail à afficher dans le Gantt.")
        st.markdown("**💡 Suggestion:** Créez des Bons de Travail avec des opérations assignées à des postes de travail.")
        return

    # Section Filtres
    with st.expander("🔍 Filtres et Options", expanded=not is_mobile):
        filter_cols = st.columns([1, 1] if is_mobile else [1, 1, 1])
        
        with filter_cols[0]:
            available_statuts = ["Tous"] + sorted(list(set([bt.get('statut', 'N/A') for bt in bts_list if bt.get('statut')])))
            selected_statut = st.selectbox("Statut BT:", available_statuts)
        
        with filter_cols[1]:
            available_priorities = ["Toutes"] + sorted(list(set([bt.get('priorite', 'N/A') for bt in bts_list if bt.get('priorite')])))
            selected_priority = st.selectbox("Priorité:", available_priorities)
        
        if not is_mobile and len(filter_cols) > 2:
            with filter_cols[2]:
                show_postes = st.checkbox("Afficher postes de travail", value=True)
        else:
            show_postes = st.checkbox("Afficher postes de travail", value=True)
        
        search_term = st.text_input("🔍 Rechercher un BT:", "")
    
    # Bouton retour si un BT est sélectionné
    if st.session_state.get('selected_bt_id'):
        if st.button("⬅️ Retour à la vue d'ensemble", 
                     key="back_button_bt", 
                     on_click=lambda: st.session_state.pop('selected_bt_id', None),
                     use_container_width=is_mobile):
            st.rerun()
    
    # Appliquer les filtres
    filtered_bts = bts_list
    
    if selected_statut != "Tous":
        filtered_bts = [bt for bt in filtered_bts if bt.get('statut') == selected_statut]
    
    if selected_priority != "Toutes":
        filtered_bts = [bt for bt in filtered_bts if bt.get('priorite') == selected_priority]
    
    if search_term:
        term_lower = search_term.lower()
        filtered_bts = [bt for bt in filtered_bts if 
                       term_lower in str(bt.get('numero_document', '')).lower() or
                       term_lower in get_company_display_name(bt, erp_db).lower() or
                       term_lower in get_project_display_name(bt, erp_db).lower() or
                       term_lower in str(bt.get('notes', '')).lower()]
    
    # Préparer les données Gantt
    gantt_data, y_axis_order, date_range = prepare_gantt_data_bt(
        filtered_bts, 
        erp_db, 
        show_postes=show_postes
    )
    
    if not gantt_data:
        st.info("Aucun Bon de Travail ne correspond aux critères de filtrage.")
        return
    
    # Création du DataFrame et graphique
    df = pd.DataFrame(gantt_data)
    df = add_status_indicators_bt(df)
    fig = create_gantt_chart_bt(df, y_axis_order, date_range, is_mobile)
    
    # Affichage du graphique
    st.plotly_chart(fig, use_container_width=True)
    
    # Statistiques rapides
    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
    with col_stats1:
        st.metric("📋 Bons de Travail", len(filtered_bts))
    with col_stats2:
        en_cours = len([bt for bt in filtered_bts if bt.get('statut') == 'EN_COURS'])
        st.metric("🚀 En cours", en_cours)
    with col_stats3:
        termines = len([bt for bt in filtered_bts if bt.get('statut') == 'TERMINÉ'])
        st.metric("✅ Terminés", termines)
    with col_stats4:
        total_operations = sum(len(bt.get('operations', [])) for bt in filtered_bts)
        st.metric("🔧 Opérations/Postes", total_operations)
    
    # Légende des couleurs
    with st.expander("🎨 Légende des couleurs"):
        col_leg1, col_leg2 = st.columns(2)
        
        with col_leg1:
            st.markdown("**📋 Statuts Bons de Travail:**")
            for statut, color in BT_COLORS.items():
                if statut != 'DEFAULT':
                    st.markdown(f'<span style="color:{color};">●</span> {statut}', unsafe_allow_html=True)
        
        with col_leg2:
            st.markdown("**🔧 Statuts Opérations/Postes:**")
            for statut, color in POSTE_COLORS.items():
                if statut != 'DEFAULT':
                    st.markdown(f'<span style="color:{color};">●</span> {statut}', unsafe_allow_html=True)
    
    # Affichage des détails si un BT est sélectionné
    if st.session_state.get('selected_bt_id'):
        bt_id = st.session_state.selected_bt_id
        bt_data = next((bt for bt in bts_list if bt.get('id') == bt_id), None)
        
        if bt_data:
            display_selected_bt_details(bt_data, erp_db, is_mobile)
        else:
            st.warning(f"Bon de Travail #{bt_id} non trouvé.")
            st.session_state.pop('selected_bt_id', None)
    
    elif is_mobile:
        st.info("📱 Touchez une barre du diagramme pour voir les détails du Bon de Travail.")

if __name__ == "__main__":
    app()