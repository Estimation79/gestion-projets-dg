import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.gestionnaire import GestionnaireProjetIA

# Import networkx avec gestion d'erreur
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

# Variable globale pour stocker le message d'avertissement
NETWORKX_WARNING_MESSAGE = "Le module 'networkx' n'est pas installé. Certaines fonctionnalités avancées comme le calcul du chemin critique seront désactivées. Pour l'installer, exécutez 'pip install networkx'."

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

def format_duration(hours):
    """Formate un nombre d'heures en jours, heures."""
    if hours is None:
        return "0h"
    
    days = int(hours // 8)  # Considère 8h par jour de travail
    remaining_hours = hours % 8
    
    if days > 0:
        return f"{days}j {remaining_hours:.1f}h"
    else:
        return f"{hours:.1f}h"

def create_gantt_chart(routing_items):
    """Crée un diagramme de Gantt pour visualiser les opérations."""
    if not routing_items:
        return None
    
    # Créer un graphe pour calculer les dates de début les plus tôt possibles
    early_starts = {}
    
    # Version adaptée pour fonctionner avec ou sans networkx
    if NETWORKX_AVAILABLE:
        G = nx.DiGraph()
        
        # Ajouter les nœuds et les arêtes (dépendances)
        for op in routing_items:
            op_id = op.get('id')
            G.add_node(op_id, duration=op.get('temps_estime', 0) or 0)
            
            # Ajouter les dépendances
            pred_id = op.get('predecesseur_id')
            if pred_id is not None and pred_id != op_id:
                G.add_edge(pred_id, op_id)
        
        # Trouver les nœuds sans prédécesseurs (départs)
        start_nodes = [n for n in G.nodes() if G.in_degree(n) == 0]
        
        # Initialiser les dates de départ
        for node in start_nodes:
            early_starts[node] = 0
        
        # Parcourir le graphe topologiquement pour calculer les dates de début
        try:
            for node in nx.topological_sort(G):
                if node not in early_starts:
                    # Trouver la date la plus tardive parmi tous les prédécesseurs
                    predecessors = list(G.predecessors(node))
                    if predecessors:
                        max_end_time = max(early_starts[p] + G.nodes[p]['duration'] for p in predecessors)
                        early_starts[node] = max_end_time
                    else:
                        early_starts[node] = 0
        except nx.NetworkXUnfeasible:
            # En cas de cycle dans le graphe
            st.warning("Impossible de calculer les dates de début en raison de dépendances cycliques.")
            # Fallback simple
            for op in routing_items:
                early_starts[op.get('id')] = 0
    else:
        # Méthode simplifiée sans networkx
        # Cette méthode ne prend pas en compte les dépendances complexes
        current_time = 0
        op_ids_with_pred = set()
        
        # D'abord les opérations sans prédécesseur
        for op in routing_items:
            if op.get('predecesseur_id') is None:
                early_starts[op.get('id')] = 0
            else:
                op_ids_with_pred.add(op.get('id'))
        
        # Puis on essaie de résoudre les autres de manière très simplifiée
        remaining_attempts = 3  # Limite pour éviter les boucles infinies
        while op_ids_with_pred and remaining_attempts > 0:
            remaining_attempts -= 1
            for op in routing_items:
                if op.get('id') in op_ids_with_pred:
                    pred_id = op.get('predecesseur_id')
                    if pred_id in early_starts:
                        pred_op = next((p for p in routing_items if p.get('id') == pred_id), None)
                        if pred_op:
                            early_starts[op.get('id')] = early_starts[pred_id] + (pred_op.get('temps_estime', 0) or 0)
                            op_ids_with_pred.remove(op.get('id'))
        
        # Pour les opérations dont les dépendances n'ont pas été résolues
        for op_id in op_ids_with_pred:
            early_starts[op_id] = 0
    
    # Préparer les données pour Plotly
    df_data = []
    for op in routing_items:
        op_id = op.get('id')
        start_time = early_starts.get(op_id, 0)
        duration = op.get('temps_estime', 0) or 0
        end_time = start_time + duration
        
        df_data.append({
            'Task': f"{op.get('sequence', '?')} - {op.get('description', 'Sans nom')}",
            'Resource': op.get('ressource', 'N/A'),
            'Start': start_time,
            'Finish': end_time,
            'ID': op_id,
            'Status': op.get('statut', 'À FAIRE'),
            'Duration': duration
        })
    
    df = pd.DataFrame(df_data)
    
    # Déterminer les couleurs selon le statut - Palette pastel améliorée
    color_map = {
        'À FAIRE': '#9ebdd8',     # Bleu clair pastel
        'EN COURS': '#8fd1cd',    # Turquoise pastel
        'TERMINÉ': '#a5d8a7',     # Vert pastel
        'EN ATTENTE': '#f8d0a9',  # Orange pastel
        'ANNULÉ': '#f4a6a6'       # Rouge pastel
    }
    
    df['Color'] = df['Status'].map(lambda s: color_map.get(s, '#9ebdd8'))
    
    # Créer le diagramme avec style amélioré
    fig = px.timeline(
        df, 
        x_start='Start', 
        x_end='Finish', 
        y='Task',
        color='Status',
        color_discrete_map=color_map,
        labels={
            'Task': 'Opération',
            'Start': 'Début (heures)',
            'Finish': 'Fin (heures)'
        }
    )
    
    # Ajouter les arcs de dépendance avec style amélioré
    shapes = []
    annotations = []
    
    for op in routing_items:
        op_id = op.get('id')
        pred_id = op.get('predecesseur_id')
        
        if pred_id is not None and pred_id != op_id:
            # Trouver les points de départ/arrivée pour la flèche
            successor_row = df[df['ID'] == op_id]
            predecessor_row = df[df['ID'] == pred_id]
            
            if not successor_row.empty and not predecessor_row.empty:
                start_x = predecessor_row.iloc[0]['Finish']
                start_y = predecessor_row.index[0]
                end_x = successor_row.iloc[0]['Start']
                end_y = successor_row.index[0]
                
                # Inverser y car les indices de DataFrame sont différents des indices d'affichage
                start_y = len(df) - 1 - start_y
                end_y = len(df) - 1 - end_y
                
                annotations.append(
                    dict(
                        x=end_x,
                        y=end_y,
                        ax=start_x,
                        ay=start_y,
                        xref='x',
                        yref='y',
                        axref='x',
                        ayref='y',
                        showarrow=True,
                        arrowhead=2,
                        arrowsize=1.2,
                        arrowwidth=1.5,
                        arrowcolor='rgba(120, 160, 190, 0.6)'
                    )
                )
    
    fig.update_layout(annotations=annotations)
    
    # Ajuster la mise en page avec style amélioré
    fig.update_layout(
        autosize=True,
        height=max(400, 100 + 40 * len(df)),
        xaxis=dict(
            title="Temps (heures)",
            title_font=dict(family="Arial", size=14, color="#5c7cfa")
        ),
        yaxis=dict(
            autorange="reversed",
            title_font=dict(family="Arial", size=14, color="#5c7cfa")
        ),
        margin=dict(l=10, r=10, t=60, b=20),
        legend=dict(
            title="Statut", 
            orientation="h", 
            y=1.1, 
            x=0,
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor='rgba(180, 180, 180, 0.2)',
            borderwidth=1
        ),
        plot_bgcolor='rgba(248, 249, 250, 1)',
        paper_bgcolor='rgba(248, 249, 250, 0)',
        font=dict(family="Arial, sans-serif", size=12, color="#444444"),
        title=dict(
            text="Planification des opérations",
            font=dict(family="Arial", size=18, color="#5c7cfa"),
            x=0.5,
            y=0.95
        )
    )
    
    # Afficher les durées sur les barres avec style
    fig.update_traces(
        text=df['Duration'].apply(lambda x: format_duration(x)),
        textposition='inside',
        textfont=dict(color="white", size=10, family="Arial"),
        marker=dict(line=dict(width=0)),
        hovertemplate='<b>%{y}</b><br>Durée: %{text}<br>Début: %{x}<br>Ressource: %{customdata}<extra></extra>',
        customdata=df['Resource']
    )
    
    return fig

def visualize_network(routing_items):
    """Visualise le réseau de dépendances des opérations."""
    if not routing_items:
        return None
    
    if not NETWORKX_AVAILABLE:
        return None
    
    # Créer un graphe dirigé
    G = nx.DiGraph()
    
    # Ajouter les nœuds avec attributs (statut, description)
    for op in routing_items:
        op_id = op.get('id')
        G.add_node(
            op_id, 
            label=f"{op.get('sequence', '?')}: {op.get('description', '')}",
            status=op.get('statut', 'À FAIRE'),
            duration=op.get('temps_estime', 0) or 0,
            resource=op.get('ressource', '')
        )
        
        # Ajouter les dépendances
        pred_id = op.get('predecesseur_id')
        if pred_id is not None and pred_id != op_id:
            G.add_edge(pred_id, op_id)
    
    # Déterminer la mise en page pour le graphe
    pos = nx.spring_layout(G, k=0.5, iterations=100)  # Augmentation des itérations pour meilleure disposition
    
    # Créer les traces pour les arêtes avec style amélioré
    edge_trace = go.Scatter(
        x=[],
        y=[],
        line=dict(width=1.5, color='rgba(180, 200, 220, 0.7)'),
        hoverinfo='none',
        mode='lines'
    )
    
    # Ajouter les arêtes au graphique
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace['x'] += (x0, x1, None)
        edge_trace['y'] += (y0, y1, None)
    
    # Créer les traces pour les nœuds avec couleurs pastels selon le statut
    node_colors = {
        'À FAIRE': '#9ebdd8',     # Bleu clair pastel
        'EN COURS': '#8fd1cd',    # Turquoise pastel
        'TERMINÉ': '#a5d8a7',     # Vert pastel
        'EN ATTENTE': '#f8d0a9',  # Orange pastel
        'ANNULÉ': '#f4a6a6'       # Rouge pastel
    }
    
    node_trace = go.Scatter(
        x=[pos[node][0] for node in G.nodes()],
        y=[pos[node][1] for node in G.nodes()],
        mode='markers+text',
        text=[G.nodes[node]['label'] for node in G.nodes()],
        textposition="bottom center",
        textfont=dict(family="Arial", size=10, color="#444"),
        hovertext=[f"<b>{G.nodes[node]['label']}</b><br>Durée: {format_duration(G.nodes[node]['duration'])}<br>Ressource: {G.nodes[node]['resource']}<br>Statut: {G.nodes[node]['status']}" for node in G.nodes()],
        hoverinfo='text',
        marker=dict(
            size=22,
            color=[node_colors.get(G.nodes[node]['status'], '#9ebdd8') for node in G.nodes()],
            line=dict(width=2, color='white'),
            symbol='circle',
            opacity=0.9
        )
    )
    
    # Créer la figure avec style amélioré
    fig = go.Figure(data=[edge_trace, node_trace],
                  layout=go.Layout(
                      title=dict(
                          text="Réseau de dépendances des opérations",
                          font=dict(family="Arial", size=18, color="#5c7cfa"),
                          x=0.5,
                          y=0.95
                      ),
                      showlegend=False,
                      hovermode='closest',
                      margin=dict(b=20, l=5, r=5, t=60),
                      xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                      yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                      plot_bgcolor='rgba(248,249,250,1)',
                      paper_bgcolor='rgba(248,249,250,0)'
                  ))
    
    return fig

def calculate_critical_path(routing_items):
    """Calcule et renvoie le chemin critique du projet."""
    if not routing_items:
        return []
    
    if not NETWORKX_AVAILABLE:
        # Version simplifiée sans networkx - on retourne juste les opérations sans successeurs
        result = []
        op_ids_with_successors = set()
        
        for op in routing_items:
            pred_id = op.get('predecesseur_id')
            if pred_id is not None:
                op_ids_with_successors.add(pred_id)
        
        for op in routing_items:
            if op.get('id') not in op_ids_with_successors:
                result.append(op)
        
        return result
    
    # Créer un graphe dirigé
    G = nx.DiGraph()
    
    # Ajouter les nœuds et les arêtes avec durées
    for op in routing_items:
        op_id = op.get('id')
        G.add_node(op_id, duration=op.get('temps_estime', 0) or 0, description=op.get('description', ''))
        
        # Ajouter les dépendances
        pred_id = op.get('predecesseur_id')
        if pred_id is not None and pred_id != op_id:
            # Le poids est la durée de l'opération source
            pred_op = next((item for item in routing_items if item.get('id') == pred_id), None)
            if pred_op:
                weight = pred_op.get('temps_estime', 0) or 0
                G.add_edge(pred_id, op_id, weight=weight)
    
    # Trouver les nœuds de départ et d'arrivée
    start_nodes = [n for n in G.nodes() if G.in_degree(n) == 0]
    end_nodes = [n for n in G.nodes() if G.out_degree(n) == 0]
    
    # S'il y a plusieurs départs/fins, on crée des nœuds virtuels
    if len(start_nodes) == 0:
        return []  # Graphe cyclique, pas de chemin critique
    
    # Trouver le chemin critique (le plus long)
    critical_path = None
    max_path_length = -1
    
    # Pour chaque paire départ-fin possible
    for start_node in start_nodes:
        for end_node in end_nodes:
            try:
                # Trouver tous les chemins simples de start à end
                for path in nx.all_simple_paths(G, start_node, end_node):
                    # Calculer la longueur du chemin
                    path_length = sum(G.nodes[node]['duration'] for node in path)
                    
                    if path_length > max_path_length:
                        max_path_length = path_length
                        critical_path = path
            except nx.NetworkXNoPath:
                continue
    
    # Convertir les IDs du chemin critique en données complètes
    if critical_path:
        critical_ops = []
        for op_id in critical_path:
            op = next((item for item in routing_items if item.get('id') == op_id), None)
            if op:
                critical_ops.append(op)
        return critical_ops
    else:
        return []

def app():
    # Styles CSS globaux améliorés
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
    
    /* Cartes d'information */
    .info-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: all 0.3s;
        border-left: 4px solid #a5d8ff;
    }
    .info-card:hover {
        background-color: #f0f7ff;
        box-shadow: 0 3px 8px rgba(0,0,0,0.08);
        transform: translateY(-2px);
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
    
    /* Onglets personnalisés */
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
    
    /* Navigation améliorée */
    .nav-container {
        background-color: #f7f9fc;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    /* Boutons améliorés */
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
    
    /* Bouton d'ajout */
    div.stButton > button:has(span:contains("➕")) {
        background: linear-gradient(90deg, #c5e1a5 0%, #aed581 100%) !important;
        color: #33691e !important;
    }
    
    /* Bouton de modification */
    div.stButton > button:has(span:contains("✏️")) {
        background: linear-gradient(90deg, #bbdefb 0%, #90caf9 100%) !important;
        color: #1565c0 !important;
    }
    
    /* Bouton de suppression */
    div.stButton > button:has(span:contains("🗑️")) {
        background: linear-gradient(90deg, #ffccbc 0%, #ffab91 100%) !important;
        color: #bf360c !important;
    }
    
    /* Bouton de mise à jour */
    div.stButton > button:has(span:contains("🔄")) {
        background: linear-gradient(90deg, #b3e5fc 0%, #81d4fa 100%) !important;
        color: #0277bd !important;
    }
    
    /* Bouton d'analyse */
    div.stButton > button:has(span:contains("📊")) {
        background: linear-gradient(90deg, #e1bee7 0%, #ce93d8 100%) !important;
        color: #6a1b9a !important;
    }
    
    /* Style pour les tableaux */
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
    
    /* Style pour les métriques */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);
        border-radius: 10px;
        padding: 10px 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: all 0.3s;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.08);
    }
    div[data-testid="stMetric"] > div:first-child {
        font-weight: 600;
        color: #5c7cfa;
    }
    
    /* Style pour les sous-titres */
    h3 {
        color: #5c7cfa !important;
        padding-bottom: 8px;
        border-bottom: 2px solid #edf2ff;
        margin-top: 20px !important;
    }
    
    /* Style pour les forms */
    div[data-testid="stForm"] {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        border-left: 5px solid #a5d8ff;
    }
    
    /* Style pour les selects et inputs */
    div[data-baseweb="select"] {
        border-radius: 8px !important;
    }
    div[data-baseweb="input"] input {
        border-radius: 8px !important;
    }
    
    /* Style pour les warnings et errors */
    div.stAlert {
        border-radius: 8px !important;
        padding: 12px 15px !important;
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
        .info-card {
            padding: 12px;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Vérifier si on est sur mobile
    is_mobile = is_mobile_device()
    
    # Titre avec style amélioré
    st.markdown('<div class="main-title"><h1>🛠️ Itinéraire de Fabrication</h1></div>', unsafe_allow_html=True)
    
    # Afficher l'avertissement à propos de networkx si nécessaire
    if not NETWORKX_AVAILABLE:
        st.warning(NETWORKX_WARNING_MESSAGE)
    
    # Récupérer le gestionnaire de la session
    if 'gestionnaire' not in st.session_state:
        st.session_state.gestionnaire = GestionnaireProjetIA()
    
    gestionnaire = st.session_state.gestionnaire
    
    # Vérifier si le gestionnaire Routing existe
    if not hasattr(gestionnaire, 'gestionnaire_routing'):
        st.error("Module de gestion Routing non initialisé. Veuillez contacter l'administrateur.")
        return
    
    # Sélection du projet
    projet_options = [(p.get('id'), f"#{p.get('id')} - {p.get('nom_projet', 'Sans Nom')}") 
                     for p in gestionnaire.projets]
    
    if not projet_options:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #ffe0e0 0%, #ffcdd2 100%);
                    padding: 20px; border-radius: 10px; margin: 20px 0;
                    border-left: 5px solid #ef9a9a; box-shadow: 0 3px 8px rgba(0,0,0,0.1);">
            <h3 style="color: #c62828; margin-top: 0;">⚠️ Aucun projet disponible</h3>
            <p style="margin-bottom: 0;">Veuillez d'abord créer un projet dans la vue Liste.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Interface principale avec conteneur amélioré
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected_project_id = st.selectbox(
            "Sélectionner un projet:",
            options=[pid for pid, _ in projet_options],
            format_func=lambda pid: next((name for id, name in projet_options if id == pid), ""),
            key="routing_project_select"
        )
    
    with col2:
        if st.button("➕ Ajouter une opération", use_container_width=True):
            st.session_state.show_add_operation = True
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Récupérer le projet sélectionné
    projet = next((p for p in gestionnaire.projets if p.get('id') == selected_project_id), None)
    if not projet:
        st.error(f"Projet #{selected_project_id} non trouvé.")
        return
    
    # Entête de projet améliorée
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #e0f7fa 0%, #e8f5e9 100%);
               padding: 15px; border-radius: 12px; margin-bottom: 20px;
               box-shadow: 0 3px 8px rgba(0,0,0,0.08); border-left: 5px solid #a5d8ff;">
        <h2 style="margin: 0; font-size: 20px; color: #333;">📋 {projet.get('nom_projet')}</h2>
        <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">
            <span style="display: inline-block; margin-right: 15px;"><b>👤 Client:</b> {projet.get('client', 'N/A')}</span>
            <span style="display: inline-block; margin-right: 15px;"><b>🚦 Statut:</b> {projet.get('statut', 'N/A')}</span>
            <span style="display: inline-block;"><b>📅 Date:</b> {projet.get('date_soumis', 'N/A')}</span>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Récupérer les opérations du projet
    routing_items = gestionnaire.gestionnaire_routing.obtenir_routing_projet(selected_project_id)
    
    # Onglets pour différentes vues
    tabs = st.tabs(["📋 Liste des opérations", "📊 Diagramme de Gantt", "🔄 Réseau", "📈 Analyse"])
    
    with tabs[0]:  # Liste des opérations
        if not routing_items:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%);
                       padding: 15px; border-radius: 10px; margin: 15px 0;
                       border-left: 5px solid #aed581; box-shadow: 0 2px 6px rgba(0,0,0,0.08);">
                <h3 style="color: #689f38; margin-top: 0; border-bottom: none;">🔍 Aucune opération</h3>
                <p style="margin-bottom: 0;">Aucune opération définie pour ce projet. Utilisez le bouton 'Ajouter une opération' pour commencer.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Préparer les données pour l'affichage
            display_data = []
            for op in routing_items:
                temps = op.get('temps_estime', 0) or 0
                
                # Trouver le prédécesseur
                pred_id = op.get('predecesseur_id')
                pred_desc = "Aucun"
                if pred_id:
                    pred_op = next((item for item in routing_items if item.get('id') == pred_id), None)
                    if pred_op:
                        pred_desc = f"#{pred_id}: {pred_op.get('description', '')}"
                
                # Détermine couleur selon statut
                status_colors = {
                    'À FAIRE': '#9ebdd8',
                    'EN COURS': '#8fd1cd',
                    'TERMINÉ': '#a5d8a7',
                    'EN ATTENTE': '#f8d0a9',
                    'ANNULÉ': '#f4a6a6'
                }
                
                display_data.append({
                    "ID": op.get('id', '?'),
                    "Séquence": op.get('sequence', ''),
                    "Description": op.get('description', ''),
                    "Temps estimé": format_duration(temps),
                    "Ressource": op.get('ressource', ''),
                    "Statut": op.get('statut', 'À FAIRE'),
                    "Prédécesseur": pred_desc
                })
            
            # Créer DataFrame pour affichage
            routing_df = pd.DataFrame(display_data)
            
            # Afficher le tableau avec actions
            st.dataframe(routing_df, use_container_width=True)
            
            # Actions sous le tableau dans un conteneur stylisé
            st.markdown("""
            <div style="background-color: #f7f9fc; padding: 15px; border-radius: 10px; 
                      margin: 15px 0; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
                <h3 style="color: #5c7cfa; margin-top: 0; font-size: 16px; border-bottom: none;">
                    🔧 Actions sur les opérations
                </h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Sélection d'une opération pour modification/suppression
            selected_operation_id = st.selectbox(
                "Sélectionner une opération:",
                options=[op.get('id') for op in routing_items],
                format_func=lambda id_op: next((f"{op.get('sequence', '')}: {op.get('description', '')}" 
                                           for op in routing_items if op.get('id') == id_op), ""),
                key="operation_select"
            )
            
            # Boutons d'action
            action_col1, action_col2, action_col3 = st.columns(3)
            with action_col1:
                if st.button("✏️ Modifier", use_container_width=True):
                    st.session_state.show_edit_operation = True
                    st.session_state.edit_operation_id = selected_operation_id
            
            with action_col2:
                if st.button("🗑️ Supprimer", use_container_width=True):
                    st.session_state.show_delete_operation = True
                    st.session_state.delete_operation_id = selected_operation_id
                    
            with action_col3:
                if st.button("🔄 Mettre à jour le statut", use_container_width=True):
                    st.session_state.show_update_status = True
                    st.session_state.update_status_id = selected_operation_id
    
    with tabs[1]:  # Diagramme de Gantt
        if not routing_items:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%);
                       padding: 15px; border-radius: 10px; margin: 15px 0;
                       border-left: 5px solid #aed581; box-shadow: 0 2px 6px rgba(0,0,0,0.08);">
                <p style="margin: 0;"><i>Aucune opération à afficher dans le diagramme de Gantt.</i></p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Créer le diagramme de Gantt
            st.markdown("<h3 style='color: #5c7cfa; margin-top: 0;'>📊 Planification des opérations</h3>", unsafe_allow_html=True)
            fig = create_gantt_chart(routing_items)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("""
                <div style="background-color: #f0f7ff; padding: 12px; border-radius: 8px; 
                          margin-top: 10px; border-left: 4px solid #a5d8ff;">
                    <p style="margin: 0; color: #333;"><i>Ce diagramme montre la planification temporelle des opérations avec leurs durées et dépendances.</i></p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("Impossible de générer le diagramme de Gantt. Vérifiez les données des opérations.")
    
    with tabs[2]:  # Réseau de dépendances
        if not routing_items:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%);
                       padding: 15px; border-radius: 10px; margin: 15px 0;
                       border-left: 5px solid #aed581; box-shadow: 0 2px 6px rgba(0,0,0,0.08);">
                <p style="margin: 0;"><i>Aucune opération à afficher dans le réseau.</i></p>
            </div>
            """, unsafe_allow_html=True)
        elif not NETWORKX_AVAILABLE:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
                       padding: 15px; border-radius: 10px; margin: 15px 0;
                       border-left: 5px solid #ffd54f; box-shadow: 0 2px 6px rgba(0,0,0,0.08);">
                <h3 style="color: #ff8f00; margin-top: 0; border-bottom: none;">⚠️ Module manquant</h3>
                <p style="margin-bottom: 0;">La visualisation du réseau de dépendances nécessite le module 'networkx'. Pour l'installer, exécutez 'pip install networkx'.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Générer le graphe de dépendances
            st.markdown("<h3 style='color: #5c7cfa; margin-top: 0;'>🔄 Réseau de dépendances</h3>", unsafe_allow_html=True)
            fig = visualize_network(routing_items)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("""
                <div style="background-color: #f0f7ff; padding: 12px; border-radius: 8px; 
                          margin-top: 10px; border-left: 4px solid #a5d8ff;">
                    <p style="margin: 0; color: #333;"><i>Ce diagramme montre les relations de dépendance entre les opérations. Les couleurs indiquent le statut de chaque opération.</i></p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("Impossible de générer le réseau. Vérifiez les données des opérations.")
    
    with tabs[3]:  # Analyse
        if not routing_items:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%);
                       padding: 15px; border-radius: 10px; margin: 15px 0;
                       border-left: 5px solid #aed581; box-shadow: 0 2px 6px rgba(0,0,0,0.08);">
                <p style="margin: 0;"><i>Aucune opération à analyser.</i></p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Calcul de statistiques
            total_time = sum(op.get('temps_estime', 0) or 0 for op in routing_items)
            finished_ops = sum(1 for op in routing_items if op.get('statut') == 'TERMINÉ')
            progress = finished_ops / len(routing_items) * 100 if routing_items else 0
            
            # Carte des statistiques améliorée
            st.markdown("""
            <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
                       padding: 15px; border-radius: 12px; margin-bottom: 20px;
                       box-shadow: 0 3px 8px rgba(0,0,0,0.08);">
                <h3 style="color: #1976d2; margin-top: 0; border-bottom: none;">📊 Statistiques générales</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Statistiques générales
            stats_col1, stats_col2, stats_col3 = st.columns(3)
            with stats_col1:
                st.metric("Nombre d'opérations", len(routing_items))
            with stats_col2:
                st.metric("Durée totale estimée", format_duration(total_time))
            with stats_col3:
                st.metric("Progression", f"{progress:.1f}%")
            
            # Carte du chemin critique
            st.markdown("""
            <div style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
                       padding: 15px; border-radius: 12px; margin: 20px 0;
                       box-shadow: 0 3px 8px rgba(0,0,0,0.08);">
                <h3 style="color: #388e3c; margin-top: 0; border-bottom: none;">⏱️ Chemin critique</h3>
            </div>
            """, unsafe_allow_html=True)
            
            if not NETWORKX_AVAILABLE:
                st.markdown("""
                <div style="background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
                           padding: 12px; border-radius: 8px; margin-bottom: 15px;
                           border-left: 4px solid #ffd54f;">
                    <p style="margin: 0; color: #ff8f00;"><b>⚠️ Note:</b> Le calcul précis du chemin critique nécessite le module 'networkx'. Une approximation simplifiée est affichée ci-dessous.</p>
                </div>
                """, unsafe_allow_html=True)
                
            critical_path = calculate_critical_path(routing_items)
            
            if critical_path:
                critical_time = sum(op.get('temps_estime', 0) or 0 for op in critical_path)
                
                st.markdown(f"""
                <div style="background-color: #f0f7ff; padding: 12px; border-radius: 8px; 
                          margin-bottom: 15px; border-left: 4px solid #a5d8ff;">
                    <p style="margin: 0; color: #333; font-weight: bold;">⏱️ Durée du chemin critique: {format_duration(critical_time)}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Afficher les opérations du chemin critique
                cp_data = []
                for op in critical_path:
                    cp_data.append({
                        "Séquence": op.get('sequence', ''),
                        "Opération": op.get('description', ''),
                        "Durée": format_duration(op.get('temps_estime', 0) or 0),
                        "Statut": op.get('statut', 'À FAIRE')
                    })
                
                st.markdown("<b>Opérations du chemin critique:</b>", unsafe_allow_html=True)
                cp_df = pd.DataFrame(cp_data)
                st.dataframe(cp_df, use_container_width=True)
            else:
                st.warning("Impossible de déterminer le chemin critique. Vérifiez les dépendances entre opérations.")
            
            # Section pour l'analyse IA si disponible
            if hasattr(gestionnaire, 'ai_assistant') and gestionnaire.ai_assistant:
                st.markdown("""
                <div style="background: linear-gradient(135deg, #e1bee7 0%, #ce93d8 100%);
                           padding: 15px; border-radius: 12px; margin: 20px 0;
                           box-shadow: 0 3px 8px rgba(0,0,0,0.08);">
                    <h3 style="color: #6a1b9a; margin-top: 0; border-bottom: none;">🧠 Analyse intelligente</h3>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("🧠 Analyser la gamme avec IA", use_container_width=False):
                    with st.spinner("Analyse en cours..."):
                        analysis = gestionnaire.ai_assistant.analyze_project_routing(projet, routing_items)
                        st.markdown("""
                        <div style="background: linear-gradient(to right, #f0f7ff, #e6f3ff); 
                                    padding: 15px; border-radius: 10px; 
                                    border-left: 4px solid #9c27b0;
                                    box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                        """, unsafe_allow_html=True)
                        st.markdown(analysis)
                        st.markdown("</div>", unsafe_allow_html=True)
            
            # Carte de répartition des ressources
            st.markdown("""
            <div style="background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
                       padding: 15px; border-radius: 12px; margin: 20px 0;
                       box-shadow: 0 3px 8px rgba(0,0,0,0.08);">
                <h3 style="color: #ff8f00; margin-top: 0; border-bottom: none;">📊 Répartition des ressources</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Agréger les données par ressource
            resource_data = {}
            for op in routing_items:
                resource = op.get('ressource', 'Non défini')
                time = op.get('temps_estime', 0) or 0
                
                if resource not in resource_data:
                    resource_data[resource] = 0
                resource_data[resource] += time
            
            # Créer le graphique pie
            if resource_data:
                # Palette de couleurs pastels pour le graphique
                pastel_colors = ['#9ebdd8', '#8fd1cd', '#a5d8a7', '#f8d0a9', '#f4a6a6', 
                                '#d6c5e8', '#b2dfdb', '#c8e6c9', '#fff59d', '#ffcc80']
                
                fig_pie_res = px.pie(
                    values=list(resource_data.values()),
                    names=list(resource_data.keys()),
                    hole=0.4,
                    color_discrete_sequence=pastel_colors
                )
                
                fig_pie_res.update_layout(
                    title=dict(
                        text="Répartition du temps par ressource",
                        font=dict(family="Arial", size=18, color="#ff8f00"),
                        x=0.5,
                        y=0.95
                    ),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.1,
                        xanchor="center",
                        x=0.5,
                        bgcolor='rgba(255, 255, 255, 0.8)',
                        bordercolor='rgba(180, 180, 180, 0.2)',
                        borderwidth=1
                    ),
                    plot_bgcolor='rgba(248,249,250,0)',
                    paper_bgcolor='rgba(248,249,250,0)'
                )
                
                st.plotly_chart(fig_pie_res, use_container_width=True)
            else:
                st.info("Aucune donnée de ressource disponible.")
            
            # Carte des statuts des opérations
            st.markdown("""
            <div style="background: linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 100%);
                       padding: 15px; border-radius: 12px; margin: 20px 0;
                       box-shadow: 0 3px 8px rgba(0,0,0,0.08);">
                <h3 style="color: #0097a7; margin-top: 0; border-bottom: none;">🔍 Statut des opérations</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Agréger par statut
            status_data = {}
            for op in routing_items:
                status = op.get('statut', 'À FAIRE')
                
                if status not in status_data:
                    status_data[status] = 0
                status_data[status] += 1
            
            # Créer le graphique bar
            if status_data:
                # Couleurs pastels correspondant aux statuts
                color_map = {
                    'À FAIRE': '#9ebdd8',
                    'EN COURS': '#8fd1cd',
                    'TERMINÉ': '#a5d8a7',
                    'EN ATTENTE': '#f8d0a9',
                    'ANNULÉ': '#f4a6a6'
                }
                
                status_colors = [color_map.get(status, '#9ebdd8') for status in status_data.keys()]
                
                fig_bar_status = px.bar(
                    x=list(status_data.keys()),
                    y=list(status_data.values()),
                    labels={'x': 'Statut', 'y': 'Nombre d\'opérations'},
                    color=list(status_data.keys()),
                    color_discrete_map=color_map,
                    text=list(status_data.values())
                )
                
                fig_bar_status.update_layout(
                    title=dict(
                        text="Nombre d'opérations par statut",
                        font=dict(family="Arial", size=18, color="#0097a7"),
                        x=0.5,
                        y=0.95
                    ),
                    xaxis=dict(title=dict(text="Statut", font=dict(family="Arial", size=14, color="#0097a7"))),
                    yaxis=dict(title=dict(text="Nombre d'opérations", font=dict(family="Arial", size=14, color="#0097a7"))),
                    plot_bgcolor='rgba(248,249,250,0.5)',
                    paper_bgcolor='rgba(248,249,250,0)'
                )
                
                fig_bar_status.update_traces(
                    textposition='outside',
                    textfont=dict(family="Arial", size=12, color="#333")
                )
                
                st.plotly_chart(fig_bar_status, use_container_width=True)
            else:
                st.info("Aucune donnée de statut disponible.")
            
            # Section pour les sous-tâches associées
            sous_taches = []
            if 'sous_taches' in projet:
                sous_taches = projet.get('sous_taches', [])
            
            if sous_taches:
                st.markdown("""
                <div style="background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
                           padding: 15px; border-radius: 12px; margin: 20px 0;
                           box-shadow: 0 3px 8px rgba(0,0,0,0.08);">
                    <h3 style="color: #8e24aa; margin-top: 0; border-bottom: none;">📝 Sous-tâches associées</h3>
                </div>
                """, unsafe_allow_html=True)
                
                st_data_display = []
                for st_item in sous_taches:
                    st_data_display.append({
                        "ID": st_item.get('id', '?'),
                        "Nom": st_item.get('nom', ''),
                        "Statut": st_item.get('statut', ''),
                        "Date Début": st_item.get('date_debut', ''),
                        "Date Fin": st_item.get('date_fin', '')
                    })
                
                st_df_display = pd.DataFrame(st_data_display)
                st.dataframe(st_df_display, use_container_width=True)
                
                if st.button("🔄 Créer des opérations à partir des sous-tâches", use_container_width=False):
                    existing_descriptions = [op.get('description', '').lower() for op in routing_items]
                    
                    new_ops_count = 0
                    for st_item_create in sous_taches:
                        st_name = st_item_create.get('nom', '')
                        
                        if st_name.lower() not in existing_descriptions:
                            temps_estime = 8
                            try:
                                date_debut_str = st_item_create.get('date_debut', '')
                                date_fin_str = st_item_create.get('date_fin', '')
                                if date_debut_str and date_fin_str:
                                    date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d')
                                    date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d')
                                    delta = date_fin - date_debut
                                    temps_estime = delta.days * 8
                            except (ValueError, TypeError):
                                pass
                            
                            gestionnaire.gestionnaire_routing.ajouter_operation(
                                projet_id=selected_project_id,
                                sequence=str(st_item_create.get('id', '')),
                                description=st_name,
                                temps_estime=temps_estime,
                                ressource="Personnel",
                                statut="À FAIRE"
                            )
                            new_ops_count += 1
                    
                    if new_ops_count > 0:
                        gestionnaire.sauvegarder_projets()
                        st.success(f"{new_ops_count} opérations créées à partir des sous-tâches!")
                        st.experimental_rerun()
                    else:
                        st.info("Aucune nouvelle opération à créer, toutes les sous-tâches ont déjà des opérations correspondantes.")
    
    # Modal pour ajouter une opération
    if 'show_add_operation' in st.session_state and st.session_state.show_add_operation:
        with st.form("add_operation_form"):
            st.markdown("""
            <h3 style="color: #43a047; margin-top: 0;">➕ Ajouter une opération</h3>
            <hr style="margin: 0 0 15px 0; border: none; height: 1px; background-color: #e0e0e0;">
            """, unsafe_allow_html=True)
            
            sequence = st.text_input("Séquence (ordre):")
            description = st.text_input("Description de l'opération:")
            temps_estime_input = st.number_input("Temps estimé (heures):", min_value=0.0, step=0.5)
            ressource_input = st.text_input("Ressource (personnel, machine, etc.):")
            statut_input = st.selectbox("Statut:", ["À FAIRE", "EN COURS", "TERMINÉ", "EN ATTENTE", "ANNULÉ"])
            
            if routing_items:
                predecesseurs = [("", "Aucun")] + [(op.get('id'), f"{op.get('sequence', '')}: {op.get('description', '')}") for op in routing_items]
                pred_id_input = st.selectbox(
                    "Opération prédécesseur:",
                    options=[id_val for id_val, _ in predecesseurs],
                    format_func=lambda id_val: next((name for pid, name in predecesseurs if pid == id_val), ""),
                )
                if pred_id_input == "": pred_id_input = None
            else:
                pred_id_input = None
                st.info("Pas de prédécesseur possible (première opération).")
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit_col, cancel_col = st.columns([1, 1])
            
            with submit_col:
                submit = st.form_submit_button("💾 Ajouter", use_container_width=True)
            with cancel_col:
                cancel = st.form_submit_button("❌ Annuler", use_container_width=True)
            
            if submit:
                if not description:
                    st.error("La description est requise.")
                else:
                    gestionnaire.gestionnaire_routing.ajouter_operation(
                        projet_id=selected_project_id,
                        sequence=sequence,
                        description=description,
                        temps_estime=temps_estime_input,
                        ressource=ressource_input,
                        statut=statut_input,
                        predecesseur_id=pred_id_input
                    )
                    gestionnaire.sauvegarder_projets()
                    st.success("Opération ajoutée avec succès!")
                    st.session_state.show_add_operation = False
                    st.experimental_rerun()
            
            if cancel:
                st.session_state.show_add_operation = False
                st.experimental_rerun()
    
    # Modal pour modifier une opération
    if 'show_edit_operation' in st.session_state and st.session_state.show_edit_operation:
        if hasattr(st.session_state, 'edit_operation_id'):
            operation_id_edit = st.session_state.edit_operation_id
            operation_to_edit = next((op for op in routing_items if op.get('id') == operation_id_edit), None)
            
            if operation_to_edit:
                with st.form("edit_operation_form"):
                    st.markdown(f"""
                    <h3 style="color: #1976d2; margin-top: 0;">✏️ Modifier l'opération #{operation_id_edit}</h3>
                    <hr style="margin: 0 0 15px 0; border: none; height: 1px; background-color: #e0e0e0;">
                    """, unsafe_allow_html=True)
                    
                    sequence_edit = st.text_input("Séquence (ordre):", value=operation_to_edit.get('sequence', ''))
                    description_edit = st.text_input("Description:", value=operation_to_edit.get('description', ''))
                    temps_estime_edit = st.number_input("Temps estimé (heures):", min_value=0.0, step=0.5, value=float(operation_to_edit.get('temps_estime', 0) or 0))
                    ressource_edit = st.text_input("Ressource:", value=operation_to_edit.get('ressource', ''))
                    
                    statut_options_edit = ["À FAIRE", "EN COURS", "TERMINÉ", "EN ATTENTE", "ANNULÉ"]
                    statut_index_edit = statut_options_edit.index(operation_to_edit.get('statut')) if operation_to_edit.get('statut') in statut_options_edit else 0
                    statut_edit = st.selectbox("Statut:", statut_options_edit, index=statut_index_edit)
                    
                    current_pred_id_edit = operation_to_edit.get('predecesseur_id')
                    pred_options_edit = [("", "Aucun")] + [(op.get('id'), f"{op.get('sequence', '')}: {op.get('description', '')}") 
                                                    for op in routing_items if op.get('id') != operation_id_edit]
                    
                    pred_id_edit = st.selectbox(
                        "Opération prédécesseur:",
                        options=[id_val for id_val, _ in pred_options_edit],
                        format_func=lambda id_val: next((name for pid, name in pred_options_edit if pid == id_val), ""),
                        index=next((i for i, (pid, _) in enumerate(pred_options_edit) if pid == current_pred_id_edit), 0)
                    )
                    if pred_id_edit == "": pred_id_edit = None
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    submit_col, cancel_col = st.columns([1, 1])
                    
                    with submit_col:
                        submit_edit = st.form_submit_button("💾 Enregistrer", use_container_width=True)
                    with cancel_col:
                        cancel_edit = st.form_submit_button("❌ Annuler", use_container_width=True)
                    
                    if submit_edit:
                        if not description_edit:
                            st.error("La description est requise.")
                        else:
                            if pred_id_edit == operation_id_edit:
                                st.error("Une opération ne peut pas dépendre d'elle-même.")
                            else:
                                gestionnaire.gestionnaire_routing.modifier_operation(
                                    operation_id=operation_id_edit,
                                    sequence=sequence_edit,
                                    description=description_edit,
                                    temps_estime=temps_estime_edit,
                                    ressource=ressource_edit,
                                    statut=statut_edit,
                                    predecesseur_id=pred_id_edit
                                )
                                gestionnaire.sauvegarder_projets()
                                st.success("Opération modifiée avec succès!")
                                st.session_state.show_edit_operation = False
                                del st.session_state.edit_operation_id
                                st.experimental_rerun()
                    
                    if cancel_edit:
                        st.session_state.show_edit_operation = False
                        if hasattr(st.session_state, 'edit_operation_id'):
                            del st.session_state.edit_operation_id
                        st.experimental_rerun()
            else:
                st.error(f"Opération #{operation_id_edit} non trouvée.")
                st.session_state.show_edit_operation = False
                if hasattr(st.session_state, 'edit_operation_id'):
                    del st.session_state.edit_operation_id
                st.experimental_rerun()
    
    # Modal pour confirmer la suppression
    if 'show_delete_operation' in st.session_state and st.session_state.show_delete_operation:
        if hasattr(st.session_state, 'delete_operation_id'):
            operation_id_delete = st.session_state.delete_operation_id
            operation_to_delete = next((op for op in routing_items if op.get('id') == operation_id_delete), None)
            
            if operation_to_delete:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
                           padding: 15px; border-radius: 12px; margin: 20px 0;
                           box-shadow: 0 3px 8px rgba(0,0,0,0.08); border-left: 5px solid #ef9a9a;">
                    <h3 style="color: #c62828; margin-top: 0; border-bottom: none;">🗑️ Confirmer la suppression</h3>
                    <p>Êtes-vous sûr de vouloir supprimer l'opération <b>#{operation_id_delete}: {operation_to_delete.get('description')}</b> ?</p>
                """, unsafe_allow_html=True)
                
                dependent_ops = [op for op in routing_items if op.get('predecesseur_id') == operation_id_delete]
                if dependent_ops:
                    st.markdown(f"""
                    <div style="background-color: #fff3e0; padding: 12px; border-radius: 8px; 
                              margin: 10px 0; border-left: 4px solid #ffb74d;">
                        <p style="margin: 0; color: #e65100;"><b>⚠️ Attention:</b> {len(dependent_ops)} opérations dépendent de celle-ci. Leur suppression rompra les dépendances.</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                del_col1, del_col2 = st.columns(2)
                with del_col1:
                    if st.button("✅ Oui, supprimer", use_container_width=True):
                        gestionnaire.gestionnaire_routing.supprimer_operation(operation_id_delete)
                        gestionnaire.sauvegarder_projets()
                        st.success("Opération supprimée avec succès!")
                        st.session_state.show_delete_operation = False
                        if hasattr(st.session_state, 'delete_operation_id'):
                            del st.session_state.delete_operation_id
                        st.experimental_rerun()
                
                with del_col2:
                    if st.button("❌ Non, annuler", use_container_width=True):
                        st.session_state.show_delete_operation = False
                        if hasattr(st.session_state, 'delete_operation_id'):
                            del st.session_state.delete_operation_id
                        st.experimental_rerun()
            else:
                st.error(f"Opération #{operation_id_delete} non trouvée.")
                st.session_state.show_delete_operation = False
                if hasattr(st.session_state, 'delete_operation_id'):
                    del st.session_state.delete_operation_id
                st.experimental_rerun()
    
    # Modal pour mettre à jour le statut
    if 'show_update_status' in st.session_state and st.session_state.show_update_status:
        if hasattr(st.session_state, 'update_status_id'):
            operation_id_status = st.session_state.update_status_id
            operation_for_status = next((op for op in routing_items if op.get('id') == operation_id_status), None)
            
            if operation_for_status:
                with st.form("update_status_form"):
                    st.markdown(f"""
                    <h3 style="color: #0288d1; margin-top: 0;">🔄 Mettre à jour le statut</h3>
                    <p style="color: #555;">Opération: <b>#{operation_id_status}: {operation_for_status.get('description')}</b></p>
                    <hr style="margin: 0 0 15px 0; border: none; height: 1px; background-color: #e0e0e0;">
                    """, unsafe_allow_html=True)
                    
                    # Afficher un indicateur visuel du statut actuel
                    status_colors = {
                        'À FAIRE': '#9ebdd8',
                        'EN COURS': '#8fd1cd',
                        'TERMINÉ': '#a5d8a7',
                        'EN ATTENTE': '#f8d0a9',
                        'ANNULÉ': '#f4a6a6'
                    }
                    
                    current_status = operation_for_status.get('statut')
                    current_color = status_colors.get(current_status, '#9ebdd8')
                    
                    st.markdown(f"""
                    <div style="background-color: {current_color}; padding: 10px; border-radius: 8px; 
                              margin-bottom: 15px; text-align: center;">
                        <p style="margin: 0; color: #333; font-weight: bold;">Statut actuel: {current_status}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    statut_options_update = ["À FAIRE", "EN COURS", "TERMINÉ", "EN ATTENTE", "ANNULÉ"]
                    statut_index_update = statut_options_update.index(operation_for_status.get('statut')) if operation_for_status.get('statut') in statut_options_update else 0
                    nouveau_statut_update = st.selectbox("Nouveau statut:", statut_options_update, index=statut_index_update)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    submit_col, cancel_col = st.columns([1, 1])
                    
                    with submit_col:
                        submit_status = st.form_submit_button("💾 Mettre à jour", use_container_width=True)
                    with cancel_col:
                        cancel_status = st.form_submit_button("❌ Annuler", use_container_width=True)
                    
                    if submit_status:
                        gestionnaire.gestionnaire_routing.modifier_statut_operation(
                            operation_id=operation_id_status,
                            statut=nouveau_statut_update
                        )
                        gestionnaire.sauvegarder_projets()
                        
                        # Afficher un message de confirmation stylé
                        new_color = status_colors.get(nouveau_statut_update, '#9ebdd8')
                        st.markdown(f"""
                        <div style="background-color: #e8f5e9; padding: 10px; border-radius: 8px; 
                                  margin-top: 15px; text-align: center; border-left: 4px solid #66bb6a;">
                            <p style="margin: 0; color: #2e7d32; font-weight: bold;">
                                ✅ Statut mis à jour: <span style="background-color: {new_color}; padding: 3px 8px; border-radius: 4px; color: #333;">{nouveau_statut_update}</span>
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.session_state.show_update_status = False
                        if hasattr(st.session_state, 'update_status_id'):
                            del st.session_state.update_status_id
                        st.experimental_rerun()
                    
                    if cancel_status:
                        st.session_state.show_update_status = False
                        if hasattr(st.session_state, 'update_status_id'):
                            del st.session_state.update_status_id
                        st.experimental_rerun()
            else:
                st.error(f"Opération #{operation_id_status} non trouvée.")
                st.session_state.show_update_status = False
                if hasattr(st.session_state, 'update_status_id'):
                    del st.session_state.update_status_id
                st.experimental_rerun()

if __name__ == "__main__":
    app()