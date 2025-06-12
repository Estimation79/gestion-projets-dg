# components/charts.py
"""
Composants graphiques réutilisables pour l'ERP Production DG Inc.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from config.constants import COLORS, CHART_CONFIG


def create_pie_chart(values, names, title, color_map=None):
    """Crée un graphique en secteurs (pie chart) standardisé"""
    fig = px.pie(
        values=values,
        names=names,
        title=title,
        color_discrete_map=color_map
    )
    
    fig.update_layout(**CHART_CONFIG)
    fig.update_layout(legend_title_text='')
    
    return fig


def create_bar_chart(x, y, title, color=None, color_map=None):
    """Crée un graphique en barres standardisé"""
    fig = px.bar(
        x=x,
        y=y,
        title=title,
        color=color,
        color_discrete_map=color_map
    )
    
    fig.update_layout(**CHART_CONFIG)
    fig.update_layout(showlegend=False if color is None else True)
    
    return fig


def create_timeline_chart(df, x_start, x_end, y, color, title, color_map=None, hover_data=None):
    """Crée un diagramme de Gantt/timeline standardisé"""
    fig = px.timeline(
        df,
        x_start=x_start,
        x_end=x_end,
        y=y,
        color=color,
        color_discrete_map=color_map,
        title=title,
        hover_data=hover_data or []
    )
    
    fig.update_layout(**CHART_CONFIG)
    fig.update_layout(
        xaxis=dict(title="📅 Calendrier", gridcolor='rgba(0,0,0,0.05)'),
        yaxis=dict(title="📋 Items", gridcolor='rgba(0,0,0,0.05)', categoryorder='total ascending'),
        legend_title_text=''
    )
    
    return fig


def create_line_chart(x, y, title, line_name="Données"):
    """Crée un graphique linéaire standardisé"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode='lines+markers',
        name=line_name,
        line=dict(color='var(--primary-color)', width=3),
        marker=dict(size=8, color='var(--primary-color)')
    ))
    
    fig.update_layout(**CHART_CONFIG)
    fig.update_layout(
        title=title,
        xaxis_title="Période",
        yaxis_title="Valeur"
    )
    
    return fig


def create_gauge_chart(value, title, min_val=0, max_val=100, color_ranges=None):
    """Crée un graphique de jauge standardisé"""
    if color_ranges is None:
        color_ranges = [
            {'range': [0, 50], 'color': "lightgray"},
            {'range': [50, 80], 'color': "yellow"},
            {'range': [80, 100], 'color': "green"}
        ]
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        gauge={
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': "var(--primary-color)"},
            'steps': color_ranges,
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(**CHART_CONFIG)
    fig.update_layout(height=300)
    
    return fig


def create_heatmap_chart(data_matrix, x_labels, y_labels, title):
    """Crée une heatmap standardisée"""
    fig = go.Figure(data=go.Heatmap(
        z=data_matrix,
        x=x_labels,
        y=y_labels,
        colorscale='Blues',
        showscale=True
    ))
    
    fig.update_layout(**CHART_CONFIG)
    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title=""
    )
    
    return fig


def create_scatter_chart(x, y, title, color=None, size=None, hover_name=None):
    """Crée un graphique de dispersion standardisé"""
    fig = px.scatter(
        x=x,
        y=y,
        title=title,
        color=color,
        size=size,
        hover_name=hover_name
    )
    
    fig.update_layout(**CHART_CONFIG)
    
    return fig


def create_histogram_chart(values, title, nbins=20):
    """Crée un histogramme standardisé"""
    fig = px.histogram(
        x=values,
        title=title,
        nbins=nbins,
        color_discrete_sequence=['var(--primary-color)']
    )
    
    fig.update_layout(**CHART_CONFIG)
    
    return fig


def create_box_plot(values, labels, title):
    """Crée un box plot standardisé"""
    fig = go.Figure()
    
    for i, (label, data) in enumerate(zip(labels, values)):
        fig.add_trace(go.Box(
            y=data,
            name=label,
            boxpoints='outliers'
        ))
    
    fig.update_layout(**CHART_CONFIG)
    fig.update_layout(title=title)
    
    return fig


def create_waterfall_chart(categories, values, title):
    """Crée un graphique en cascade (waterfall) standardisé"""
    fig = go.Figure(go.Waterfall(
        name="Données",
        orientation="v",
        measure=["relative"] * (len(categories) - 1) + ["total"],
        x=categories,
        textposition="outside",
        text=[f"{val:+.1f}" if val != 0 else "0" for val in values],
        y=values,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
    ))
    
    fig.update_layout(**CHART_CONFIG)
    fig.update_layout(title=title)
    
    return fig


def create_funnel_chart(stages, values, title):
    """Crée un graphique en entonnoir standardisé"""
    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textinfo="value+percent initial"
    ))
    
    fig.update_layout(**CHART_CONFIG)
    fig.update_layout(title=title)
    
    return fig


def create_radar_chart(categories, values, title, names=None):
    """Crée un graphique radar standardisé"""
    fig = go.Figure()
    
    if names is None:
        names = ['Données']
        values = [values]
    
    for name, vals in zip(names, values):
        fig.add_trace(go.Scatterpolar(
            r=vals,
            theta=categories,
            fill='toself',
            name=name
        ))
    
    fig.update_layout(**CHART_CONFIG)
    fig.update_layout(
        title=title,
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(max(vals) for vals in values)]
            )
        )
    )
    
    return fig


def create_treemap_chart(labels, parents, values, title):
    """Crée un treemap standardisé"""
    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        textinfo="label+value+percent parent"
    ))
    
    fig.update_layout(**CHART_CONFIG)
    fig.update_layout(title=title)
    
    return fig


def render_chart_with_container(fig, key=None):
    """Affiche un graphique dans un conteneur stylisé"""
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, key=key)
    st.markdown("</div>", unsafe_allow_html=True)


def create_project_status_pie(projects_data):
    """Crée un graphique spécifique pour les statuts de projets"""
    statuts = {}
    for project in projects_data:
        statut = project.get('statut', 'N/A')
        statuts[statut] = statuts.get(statut, 0) + 1
    
    return create_pie_chart(
        values=list(statuts.values()),
        names=list(statuts.keys()),
        title="📈 Projets par Statut",
        color_map=COLORS['statut']
    )


def create_department_capacity_bar(postes_data):
    """Crée un graphique spécifique pour la capacité par département"""
    capacite_par_dept = {}
    for poste in postes_data:
        dept = poste.get('departement', 'AUTRE')
        capacite = poste.get('capacite_theorique', 0)
        capacite_par_dept[dept] = capacite_par_dept.get(dept, 0) + capacite
    
    return create_bar_chart(
        x=list(capacite_par_dept.keys()),
        y=list(capacite_par_dept.values()),
        title="🏭 Capacité par Département (h/jour)",
        color=list(capacite_par_dept.keys()),
        color_map=COLORS['departement']
    )


def create_employee_workload_gauge(workload_percentage, employee_name):
    """Crée une jauge spécifique pour la charge de travail d'un employé"""
    return create_gauge_chart(
        value=workload_percentage,
        title=f"Charge de {employee_name}",
        color_ranges=[
            {'range': [0, 60], 'color': "lightgreen"},
            {'range': [60, 85], 'color': "yellow"},
            {'range': [85, 100], 'color': "red"}
        ]
    )


def create_monthly_revenue_line(revenue_data, months):
    """Crée un graphique linéaire spécifique pour le CA mensuel"""
    return create_line_chart(
        x=months,
        y=revenue_data,
        title="💰 Évolution du Chiffre d'Affaires",
        line_name="CA Mensuel"
    )


def create_project_timeline_gantt(projects_data):
    """Crée un Gantt spécifique pour les projets"""
    gantt_data = []
    
    for project in projects_data:
        try:
            start_date = pd.to_datetime(project.get('date_soumis'))
            end_date = pd.to_datetime(project.get('date_prevu'))
            
            gantt_data.append({
                'Projet': f"#{project.get('id')} - {project.get('nom_projet', 'N/A')}",
                'Début': start_date,
                'Fin': end_date,
                'Statut': project.get('statut', 'N/A'),
                'Client': project.get('client', 'N/A')
            })
        except:
            continue
    
    if not gantt_data:
        return None
    
    df_gantt = pd.DataFrame(gantt_data)
    
    return create_timeline_chart(
        df=df_gantt,
        x_start='Début',
        x_end='Fin',
        y='Projet',
        color='Statut',
        title="📊 Planning des Projets",
        color_map=COLORS['statut'],
        hover_data=['Client']
    )
