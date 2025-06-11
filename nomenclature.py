import streamlit as st
import pandas as pd
import plotly.express as px
import io
from datetime import datetime
from utils.gestionnaire import GestionnaireProjetIA

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

def format_currency(value):
    """Formate une valeur numérique en devise CAD."""
    if value is None:
        return "$0.00" # Changé
    try:
        # Tentative de nettoyage des formats courants (euro ou string)
        s_value = str(value).replace(' ','').replace('€','').replace('$','')
        if ',' in s_value and ('.' not in s_value or s_value.find(',') > s_value.find('.')):
             s_value = s_value.replace('.', '') # Supprime les séparateurs de milliers européens
             s_value = s_value.replace(',', '.') # Remplace la virgule décimale par un point
        elif ',' in s_value and '.' in s_value and s_value.find('.') > s_value.find(','): # Format 1,234.56
            s_value = s_value.replace(',', '') # Supprime le séparateur de milliers

        num_value = float(s_value)
        if num_value == 0:
            return "$0.00" # Changé
        return f"${num_value:,.2f}" # Format standard nord-américain
    except (ValueError, TypeError):
        if isinstance(value, (int, float)):
            return f"${value:,.2f}"
        return str(value) + " $ (Err)" # Changé

def calculate_totals(bom_items):
    """Calcule les totaux pour la BOM."""
    total_cost = 0
    item_count = len(bom_items)
    
    for item in bom_items:
        qty = item.get('quantite', 0) or 0
        price = item.get('prix_unitaire', 0) or 0
        total_cost += qty * price
        
    return {
        'total_cost': total_cost,
        'item_count': item_count
    }

def display_bom_stats(bom_items, is_mobile=False):
    """Affiche des statistiques sur la BOM avec style amélioré."""
    if not bom_items:
        st.info("Aucun matériau à analyser.")
        return
        
    totals = calculate_totals(bom_items)
    
    # Style pour les cartes de métriques
    st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(to right, #ffffff, #f7f9fc);
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
        margin-bottom: 15px;
        transition: transform 0.3s;
        border-left: 5px solid;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.12);
    }
    .metric-label {
        font-size: 14px;
        font-weight: 600;
        color: #555;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #333;
    }
    .material-count {
        border-left-color: #bbdefb;
    }
    .total-cost {
        border-left-color: #c8e6c9;
    }
    .average-cost {
        border-left-color: #ffecb3;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Disposition adaptative
    if is_mobile:
        st.markdown(f"""
        <div class="metric-card material-count">
            <div class="metric-label">📦 Nombre de matériaux</div>
            <div class="metric-value">{totals['item_count']}</div>
        </div>
        <div class="metric-card total-cost">
            <div class="metric-label">💰 Coût total</div>
            <div class="metric-value">{format_currency(totals['total_cost'])}</div>
        </div>
        <div class="metric-card average-cost">
            <div class="metric-label">📊 Coût moyen par matériau</div>
            <div class="metric-value">{format_currency(totals['total_cost'] / totals['item_count'] if totals['item_count'] > 0 else 0)}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card material-count">
                <div class="metric-label">📦 Nombre de matériaux</div>
                <div class="metric-value">{totals['item_count']}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card total-cost">
                <div class="metric-label">💰 Coût total</div>
                <div class="metric-value">{format_currency(totals['total_cost'])}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            avg_cost = totals['total_cost'] / totals['item_count'] if totals['item_count'] > 0 else 0
            st.markdown(f"""
            <div class="metric-card average-cost">
                <div class="metric-label">📊 Coût moyen par matériau</div>
                <div class="metric-value">{format_currency(avg_cost)}</div>
            </div>
            """, unsafe_allow_html=True)

def plot_bom_cost_distribution(bom_items):
    """Crée un graphique de distribution des coûts avec style amélioré."""
    if not bom_items:
        return
        
    # Préparer les données
    data = []
    for item in bom_items:
        qty = item.get('quantite', 0) or 0
        price = item.get('prix_unitaire', 0) or 0
        total_item_cost = qty * price
        
        data.append({
            'designation': item.get('designation', 'Sans nom'),
            'code': item.get('code', ''),
            'cout_total': total_item_cost,
            'unite': item.get('unite', ''),
            'quantite': qty
        })
    
    df = pd.DataFrame(data)
    if df.empty or df['cout_total'].sum() == 0:
        st.info("Pas assez de données pour générer un graphique.")
        return
        
    # Trier par coût
    df = df.sort_values('cout_total', ascending=False)
    
    # Limiter aux 10 premiers pour lisibilité
    if len(df) > 10:
        df_display = df.iloc[:10].copy()
        df_display.loc[len(df_display)] = {
            'designation': 'Autres', 
            'cout_total': df.iloc[10:]['cout_total'].sum(),
            'code': '-',
            'unite': '-',
            'quantite': '-'
        }
    else:
        df_display = df
    
    # Créer le graphique avec un style amélioré
    fig = px.bar(
        df_display, 
        x='designation', 
        y='cout_total',
        title="Distribution des coûts par matériau",
        labels={'designation': 'Matériau', 'cout_total': 'Coût total ($)'},
        color='cout_total',
        color_continuous_scale='blues',
        text=df_display['cout_total'].apply(lambda x: f"${x:,.2f}") # Changé pour format CAD
    )
    
    fig.update_traces(texttemplate='%{text}', textposition='outside')
    fig.update_layout(
        uniformtext_minsize=8, 
        uniformtext_mode='hide',
        plot_bgcolor='rgba(247, 249, 252, 0.8)',
        paper_bgcolor='rgba(247, 249, 252, 0)',
        font=dict(family="Arial, sans-serif", size=12, color="#444444"),
        margin=dict(l=20, r=20, t=50, b=30),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial"
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Afficher aussi un graphique en camembert pour la proportion, avec style amélioré
    fig_pie = px.pie(
        df_display, 
        values='cout_total', 
        names='designation',
        title="Répartition des coûts (%)",
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.Blues_r
    )
    
    fig_pie.update_traces(
        textposition='inside', 
        textinfo='percent+label',
        hoverinfo='label+percent+value',
        marker=dict(line=dict(color='#FFFFFF', width=2))
    )
    
    fig_pie.update_layout(
        plot_bgcolor='rgba(247, 249, 252, 0.8)',
        paper_bgcolor='rgba(247, 249, 252, 0)',
        font=dict(family="Arial, sans-serif", size=12, color="#444444"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)

def app():
    # Vérifier si l'appareil est mobile
    is_mobile = is_mobile_device()
    
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
    
    /* Section styles */
    .section-card {
        background: linear-gradient(to right, #ffffff, #f7f9fc);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
        border-left: 5px solid #a5d8ff;
    }
    .section-header {
        color: #333;
        font-size: 20px;
        font-weight: 600;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
    }
    .section-header::before {
        margin-right: 10px;
    }
    
    /* Boutons stylisés */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.3s !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
    }
    
    /* Boutons spéciaux */
    div.stButton > button:has(span:contains("➕ Ajouter")) {
        background: linear-gradient(90deg, #c5e1a5 0%, #aed581 100%) !important;
        color: #33691e !important;
    }
    div.stButton > button:has(span:contains("✏️ Modifier")) {
        background: linear-gradient(90deg, #e3f2fd 0%, #bbdefb 100%) !important;
        color: #1976d2 !important;
    }
    div.stButton > button:has(span:contains("🗑️ Supprimer")) {
        background: linear-gradient(90deg, #ffcdd2 0%, #ef9a9a 100%) !important;
        color: #b71c1c !important;
    }
    div.stButton > button:has(span:contains("📊 Analyser")) {
        background: linear-gradient(90deg, #d1c4e9 0%, #b39ddb 100%) !important;
        color: #4527a0 !important;
    }
    div.stButton > button:has(span:contains("📥 Exporter")) {
        background: linear-gradient(90deg, #bbdefb 0%, #90caf9 100%) !important;
        color: #0d47a1 !important;
    }
    
    /* DataFrames améliorés */
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
    
    /* Tabs améliorés */
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
    
    /* Formulaires améliorés */
    .form-card {
        background: linear-gradient(to right, #ffffff, #f7f9fc);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
    }
    .form-header {
        color: #333;
        font-size: 20px;
        font-weight: 600;
        margin-bottom: 15px;
        text-align: center;
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
        .section-card {
            padding: 15px;
        }
        .section-header {
            font-size: 18px;
        }
        .form-card {
            padding: 15px;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Titre avec style amélioré
    st.markdown('<div class="main-title"><h1>📋 Nomenclature des Matériaux (BOM)</h1></div>', unsafe_allow_html=True)
    
    # Récupérer le gestionnaire de la session
    if 'gestionnaire' not in st.session_state:
        st.session_state.gestionnaire = GestionnaireProjetIA()
    
    gestionnaire = st.session_state.gestionnaire
    
    # Vérifier si le gestionnaire BOM existe
    if not hasattr(gestionnaire, 'gestionnaire_bom'):
        st.error("Module de gestion BOM non initialisé. Veuillez contacter l'administrateur.")
        return
    
    # Sélection du projet avec style amélioré
    st.markdown("""
    <div class="section-card" style="border-left-color: #c8e6c9;">
        <div class="section-header" style="color: #388e3c;">📁 Sélection du projet</div>
    """, unsafe_allow_html=True)
    
    projet_options = [(p.get('id'), f"#{p.get('id')} - {p.get('nom_projet', 'Sans Nom')}") 
                     for p in gestionnaire.projets]
    
    if not projet_options:
        st.warning("Aucun projet disponible. Veuillez d'abord créer un projet dans la vue Liste.")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    # Interface principale adaptée selon mobile ou desktop
    if is_mobile:
        selected_project_id = st.selectbox(
            "Sélectionner un projet:",
            options=[pid for pid, _ in projet_options],
            format_func=lambda pid: next((name for id, name in projet_options if id == pid), ""),
            key="bom_project_select"
        )
        
        st.button("➕ Ajouter un matériau", use_container_width=True, key="add_material_btn")
        if st.session_state.get("add_material_btn", False):
            st.session_state.show_add_material = True
    else:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_project_id = st.selectbox(
                "Sélectionner un projet:",
                options=[pid for pid, _ in projet_options],
                format_func=lambda pid: next((name for id, name in projet_options if id == pid), ""),
                key="bom_project_select"
            )
        
        with col2:
            if st.button("➕ Ajouter un matériau", use_container_width=True):
                st.session_state.show_add_material = True
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Récupérer le projet sélectionné
    projet = next((p for p in gestionnaire.projets if p.get('id') == selected_project_id), None)
    if not projet:
        st.error(f"Projet #{selected_project_id} non trouvé.")
        return
    
    # Information du projet avec style
    st.markdown(f"""
    <div class="section-card" style="border-left-color: #bbdefb;">
        <div class="section-header" style="color: #1976d2;">📊 {projet.get('nom_projet')}</div>
        <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 10px;">
            <div style="background-color: #e3f2fd; padding: 5px 12px; border-radius: 20px; font-size: 14px;">
                <strong>Client:</strong> {projet.get('client', 'N/A')}
            </div>
            <div style="background-color: #e8f5e9; padding: 5px 12px; border-radius: 20px; font-size: 14px;">
                <strong>Statut:</strong> {projet.get('statut', 'N/A')}
            </div>
            <div style="background-color: #fff8e1; padding: 5px 12px; border-radius: 20px; font-size: 14px;">
                <strong>Date:</strong> {projet.get('date_soumis', 'N/A')}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Récupérer les matériaux du projet
    bom_items = gestionnaire.gestionnaire_bom.obtenir_bom_projet(selected_project_id)
    
    # Onglets pour différentes vues avec style amélioré
    tabs = st.tabs(["📋 Liste des matériaux", "📊 Analyse", "🔄 Import/Export"])
    
    with tabs[0]:  # Liste des matériaux
        if not bom_items:
            st.info("Aucun matériau défini pour ce projet. Utilisez le bouton 'Ajouter un matériau' pour commencer.")
        else:
            # Préparer les données pour l'affichage
            display_data = []
            for item in bom_items:
                qty = item.get('quantite', 0) or 0
                price = item.get('prix_unitaire', 0) or 0
                total = qty * price
                
                display_data.append({
                    "ID": item.get('id', '?'),
                    "Code": item.get('code', ''),
                    "Désignation": item.get('designation', 'Sans nom'),
                    "Quantité": qty,
                    "Unité": item.get('unite', ''),
                    "Prix unitaire": format_currency(price),
                    "Total": format_currency(total),
                    "Fournisseur": item.get('fournisseur', '')
                })
            
            # Créer DataFrame pour affichage avec style amélioré
            bom_df = pd.DataFrame(display_data)
            
            # Bouton pour exporter le tableau
            if not is_mobile:
                col_export, col_empty = st.columns([1, 3])
                with col_export:
                    if st.button("📥 Exporter en Excel", key="quick_export"):
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            bom_df.to_excel(writer, sheet_name='BOM', index=False)
                        
                        st.download_button(
                            label="⬇️ Télécharger Excel",
                            data=buffer.getvalue(),
                            file_name=f"bom_projet_{selected_project_id}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
            
            # Afficher le tableau avec style
            st.markdown("""
            <div style="background: linear-gradient(to right, #ffffff, #f7f9fc);
                        border-radius: 12px; padding: 15px; margin-bottom: 20px;
                        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);">
                <div style="font-weight: 600; margin-bottom: 10px; color: #333;">📋 Matériaux du projet</div>
            """, unsafe_allow_html=True)
            
            st.dataframe(bom_df, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Section actions sur les matériaux
            st.markdown("""
            <div style="background: linear-gradient(to right, #ffffff, #f7f9fc);
                        border-radius: 12px; padding: 15px; margin-bottom: 20px;
                        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);">
                <div style="font-weight: 600; margin-bottom: 10px; color: #333;">🔧 Actions</div>
            """, unsafe_allow_html=True)
            
            # Sélection d'un matériau pour modification/suppression
            selected_material_id = st.selectbox(
                "Sélectionner un matériau pour le modifier ou le supprimer:",
                options=[item.get('id') for item in bom_items],
                format_func=lambda id: next((f"{item.get('code', '')} - {item.get('designation', '')}" 
                                          for item in bom_items if item.get('id') == id), ""),
                key="material_select"
            )
            
            # Boutons d'action
            if is_mobile:
                if st.button("✏️ Modifier", use_container_width=True):
                    st.session_state.show_edit_material = True
                    st.session_state.edit_material_id = selected_material_id
                
                if st.button("🗑️ Supprimer", use_container_width=True):
                    st.session_state.show_delete_material = True
                    st.session_state.delete_material_id = selected_material_id
            else:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Modifier", use_container_width=True):
                        st.session_state.show_edit_material = True
                        st.session_state.edit_material_id = selected_material_id
                
                with col2:
                    if st.button("🗑️ Supprimer", use_container_width=True):
                        st.session_state.show_delete_material = True
                        st.session_state.delete_material_id = selected_material_id
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    with tabs[1]:  # Analyse des coûts
        if not bom_items:
            st.info("Ajoutez des matériaux pour voir l'analyse des coûts.")
        else:
            # Statistiques améliorées
            st.markdown("""
            <div style="background: linear-gradient(to right, #ffffff, #f7f9fc);
                        border-radius: 12px; padding: 15px; margin-bottom: 20px;
                        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);">
                <div style="font-weight: 600; margin-bottom: 10px; color: #333;">📈 Statistiques</div>
            """, unsafe_allow_html=True)
            
            display_bom_stats(bom_items, is_mobile)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Graphiques améliorés
            st.markdown("""
            <div style="background: linear-gradient(to right, #ffffff, #f7f9fc);
                        border-radius: 12px; padding: 15px; margin-bottom: 20px;
                        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);">
                <div style="font-weight: 600; margin-bottom: 10px; color: #333;">📊 Visualisation des coûts</div>
            """, unsafe_allow_html=True)
            
            plot_bom_cost_distribution(bom_items)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Section pour l'analyse IA si disponible
            if hasattr(gestionnaire, 'ai_assistant') and gestionnaire.ai_assistant:
                st.markdown("""
                <div style="background: linear-gradient(to right, #ffffff, #f7f9fc);
                            border-radius: 12px; padding: 15px; margin-bottom: 20px;
                            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);">
                    <div style="font-weight: 600; margin-bottom: 10px; color: #333;">🧠 Assistant IA</div>
                """, unsafe_allow_html=True)
                
                if st.button("📊 Analyser la BOM avec IA", use_container_width=is_mobile):
                    with st.spinner("Analyse en cours..."):
                        analysis = gestionnaire.ai_assistant.analyze_project_bom(projet, bom_items)
                        st.markdown("""
                        <div style="background: linear-gradient(to right, #f0f7ff, #e6f3ff); 
                                    padding: 15px; border-radius: 10px; 
                                    border-left: 4px solid #4285f4;
                                    box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                        <h3 style="color: #4285f4; display: flex; align-items: center;"><span style="margin-right: 8px;">🧠</span> Analyse IA</h3>
                        """, unsafe_allow_html=True)
                        st.markdown(analysis)
                        st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)
    
    with tabs[2]:  # Import/Export
        # Section export avec style
        st.markdown("""
        <div style="background: linear-gradient(to right, #ffffff, #f7f9fc);
                    border-radius: 12px; padding: 15px; margin-bottom: 20px;
                    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);">
            <div style="font-weight: 600; margin-bottom: 10px; color: #1976d2;">📤 Exporter la BOM</div>
        """, unsafe_allow_html=True)
        
        if is_mobile:
            export_format = st.radio("Format:", ["CSV", "Excel"], horizontal=True)
            
            if st.button("📥 Exporter", use_container_width=True):
                if bom_items:
                    # Préparer les données pour l'export
                    export_data = []
                    for item in bom_items:
                        export_data.append({
                            "code": item.get('code', ''),
                            "designation": item.get('designation', ''),
                            "quantite": item.get('quantite', 0),
                            "unite": item.get('unite', ''),
                            "prix_unitaire": item.get('prix_unitaire', 0),
                            "fournisseur": item.get('fournisseur', '')
                        })
                    
                    export_df = pd.DataFrame(export_data)
                    
                    if export_format == "CSV":
                        csv = export_df.to_csv(index=False)
                        st.download_button(
                            label="⬇️ Télécharger CSV",
                            data=csv,
                            file_name=f"bom_projet_{selected_project_id}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    else:  # Excel
                        # Pour Excel, utiliser un buffer temporaire
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            export_df.to_excel(writer, sheet_name='BOM', index=False)
                        
                        st.download_button(
                            label="⬇️ Télécharger Excel",
                            data=buffer.getvalue(),
                            file_name=f"bom_projet_{selected_project_id}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                else:
                    st.error("Aucune donnée à exporter.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                export_format = st.radio("Format:", ["CSV", "Excel"], horizontal=True)
                
                if st.button("📥 Exporter", use_container_width=True):
                    if bom_items:
                        # Préparer les données pour l'export
                        export_data = []
                        for item in bom_items:
                            export_data.append({
                                "code": item.get('code', ''),
                                "designation": item.get('designation', ''),
                                "quantite": item.get('quantite', 0),
                                "unite": item.get('unite', ''),
                                "prix_unitaire": item.get('prix_unitaire', 0),
                                "fournisseur": item.get('fournisseur', '')
                            })
                        
                        export_df = pd.DataFrame(export_data)
                        
                        if export_format == "CSV":
                            csv = export_df.to_csv(index=False)
                            st.download_button(
                                label="⬇️ Télécharger CSV",
                                data=csv,
                                file_name=f"bom_projet_{selected_project_id}.csv",
                                mime="text/csv"
                            )
                        else:  # Excel
                            # Pour Excel, utiliser un buffer temporaire
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                export_df.to_excel(writer, sheet_name='BOM', index=False)
                            
                            st.download_button(
                                label="⬇️ Télécharger Excel",
                                data=buffer.getvalue(),
                                file_name=f"bom_projet_{selected_project_id}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.error("Aucune donnée à exporter.")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Section import avec style
        st.markdown("""
        <div style="background: linear-gradient(to right, #ffffff, #f7f9fc);
                    border-radius: 12px; padding: 15px; margin-bottom: 20px;
                    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);">
            <div style="font-weight: 600; margin-bottom: 10px; color: #388e3c;">📥 Importer des matériaux</div>
        """, unsafe_allow_html=True)
        
        if is_mobile:
            import_file = st.file_uploader("Choisir un fichier CSV ou Excel", type=["csv", "xlsx"])
            
            if import_file is not None:
                try:
                    # Déterminer le type de fichier et le charger
                    if import_file.name.endswith('.csv'):
                        import_df = pd.read_csv(import_file)
                    else:  # Excel
                        import_df = pd.read_excel(import_file)
                    
                    # Vérifier que le fichier a les colonnes requises
                    required_cols = ['designation', 'quantite', 'unite', 'prix_unitaire']
                    missing_cols = [col for col in required_cols if col not in import_df.columns]
                    
                    if missing_cols:
                        st.error(f"Colonnes manquantes dans le fichier: {', '.join(missing_cols)}")
                    else:
                        st.dataframe(import_df, use_container_width=True)
                        
                        if st.button("✅ Importer ces matériaux", use_container_width=True):
                            with st.spinner("Importation en cours..."):
                                counter = 0
                                for _, row in import_df.iterrows():
                                    # Ajouter le matériau
                                    gestionnaire.gestionnaire_bom.ajouter_materiau(
                                        selected_project_id,
                                        row.get('code', ''),
                                        row['designation'],
                                        row['quantite'],
                                        row['unite'],
                                        row['prix_unitaire'],
                                        row.get('fournisseur', '')
                                    )
                                    counter += 1
                                
                                gestionnaire.sauvegarder_projets()
                                st.success(f"{counter} matériaux importés avec succès!")
                                st.experimental_rerun()
                except Exception as e:
                    st.error(f"Erreur lors de l'importation: {str(e)}")
        else:
            col1, col2 = st.columns(2)
            with col2:
                import_file = st.file_uploader("Choisir un fichier CSV ou Excel", type=["csv", "xlsx"])
                
                if import_file is not None:
                    try:
                        # Déterminer le type de fichier et le charger
                        if import_file.name.endswith('.csv'):
                            import_df = pd.read_csv(import_file)
                        else:  # Excel
                            import_df = pd.read_excel(import_file)
                        
                        # Vérifier que le fichier a les colonnes requises
                        required_cols = ['designation', 'quantite', 'unite', 'prix_unitaire']
                        missing_cols = [col for col in required_cols if col not in import_df.columns]
                        
                        if missing_cols:
                            st.error(f"Colonnes manquantes dans le fichier: {', '.join(missing_cols)}")
                        else:
                            st.dataframe(import_df, use_container_width=True)
                            
                            if st.button("✅ Importer ces matériaux", use_container_width=True):
                                with st.spinner("Importation en cours..."):
                                    counter = 0
                                    for _, row in import_df.iterrows():
                                        # Ajouter le matériau
                                        gestionnaire.gestionnaire_bom.ajouter_materiau(
                                            selected_project_id,
                                            row.get('code', ''),
                                            row['designation'],
                                            row['quantite'],
                                            row['unite'],
                                            row['prix_unitaire'],
                                            row.get('fournisseur', '')
                                        )
                                        counter += 1
                                    
                                    gestionnaire.sauvegarder_projets()
                                    st.success(f"{counter} matériaux importés avec succès!")
                                    st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de l'importation: {str(e)}")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Section d'aide et modèle
        st.markdown("""
        <div style="background: linear-gradient(to right, #e6f3ff, #f0f7ff);
                    border-radius: 12px; padding: 15px; margin-bottom: 20px;
                    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.05);
                    border-left: 4px solid #4285f4;">
            <div style="font-weight: 600; margin-bottom: 10px; color: #4285f4;">ℹ️ Conseils pour l'import/export</div>
            <p>
                Pour importer des matériaux, assurez-vous que votre fichier CSV ou Excel contient au minimum les colonnes suivantes:
                <ul>
                    <li><strong>designation</strong> - Nom du matériau</li>
                    <li><strong>quantite</strong> - Quantité requise</li>
                    <li><strong>unite</strong> - Unité de mesure (pcs, kg, m, etc.)</li>
                    <li><strong>prix_unitaire</strong> - Prix unitaire</li>
                </ul>
                Vous pouvez également ajouter les colonnes optionnelles <strong>code</strong> et <strong>fournisseur</strong>.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Modal pour ajouter un matériau
    if 'show_add_material' in st.session_state and st.session_state.show_add_material:
        st.markdown("""
        <div class="form-card">
            <div class="form-header">➕ Ajouter un matériau</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("add_material_form"):
            col1, col2 = st.columns(2)
            with col1:
                code = st.text_input("Code:")
                designation = st.text_input("Désignation:")
                quantite = st.number_input("Quantité:", min_value=0.0, step=0.1)
            
            with col2:
                unite = st.selectbox("Unité:", ["pcs", "kg", "m", "m²", "m³", "L"])
                prix = st.number_input("Prix unitaire:", min_value=0.0, step=0.01)
                fournisseur = st.text_input("Fournisseur (optionnel):")
            
            # Calcul du total
            total = quantite * prix
            st.markdown(f"""
            <div style="background-color: #e8f5e9; padding: 10px; border-radius: 8px; margin-top: 10px;">
                <strong>Total estimé:</strong> {format_currency(total)}
            </div>
            """, unsafe_allow_html=True)
            
            submit = st.form_submit_button("Ajouter", use_container_width=True)
            if submit:
                if not designation:
                    st.error("La désignation est requise.")
                else:
                    with st.spinner("Ajout en cours..."):
                        gestionnaire.gestionnaire_bom.ajouter_materiau(
                            selected_project_id, code, designation, quantite, unite, prix, fournisseur
                        )
                        gestionnaire.sauvegarder_projets()
                        st.success("Matériau ajouté avec succès!")
                        st.session_state.show_add_material = False
                        st.experimental_rerun()
        
        col1, col2 = st.columns(2)
        with col2:
            if st.button("Annuler", key="cancel_add_material", use_container_width=True):
                st.session_state.show_add_material = False
                st.experimental_rerun()
    
    # Modal pour modifier un matériau
    if 'show_edit_material' in st.session_state and st.session_state.show_edit_material:
        if hasattr(st.session_state, 'edit_material_id'):
            material_id = st.session_state.edit_material_id
            material = next((item for item in bom_items if item.get('id') == material_id), None)
            
            if material:
                st.markdown(f"""
                <div class="form-card">
                    <div class="form-header">✏️ Modifier le matériau #{material_id}</div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.form("edit_material_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        code = st.text_input("Code:", value=material.get('code', ''))
                        designation = st.text_input("Désignation:", value=material.get('designation', ''))
                        quantite = st.number_input("Quantité:", min_value=0.0, step=0.1, value=float(material.get('quantite', 0)))
                    
                    with col2:
                        unites = ["pcs", "kg", "m", "m²", "m³", "L"]
                        unite_index = unites.index(material.get('unite')) if material.get('unite') in unites else 0
                        unite = st.selectbox("Unité:", unites, index=unite_index)
                        
                        prix = st.number_input("Prix unitaire:", min_value=0.0, step=0.01, value=float(material.get('prix_unitaire', 0)))
                        fournisseur = st.text_input("Fournisseur:", value=material.get('fournisseur', ''))
                    
                    # Calcul du total
                    total = quantite * prix
                    st.markdown(f"""
                    <div style="background-color: #e8f5e9; padding: 10px; border-radius: 8px; margin-top: 10px;">
                        <strong>Total estimé:</strong> {format_currency(total)}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    submit = st.form_submit_button("Enregistrer les modifications", use_container_width=True)
                    if submit:
                        if not designation:
                            st.error("La désignation est requise.")
                        else:
                            with st.spinner("Modification en cours..."):
                                # Mettre à jour le matériau
                                gestionnaire.gestionnaire_bom.modifier_materiau(
                                    material_id, code=code, designation=designation, 
                                    quantite=quantite, unite=unite, prix_unitaire=prix, 
                                    fournisseur=fournisseur
                                )
                                gestionnaire.sauvegarder_projets()
                                st.success("Matériau modifié avec succès!")
                                st.session_state.show_edit_material = False
                                del st.session_state.edit_material_id
                                st.experimental_rerun()
                
                col1, col2 = st.columns(2)
                with col2:
                    if st.button("Annuler", key="cancel_edit_material", use_container_width=True):
                        st.session_state.show_edit_material = False
                        if hasattr(st.session_state, 'edit_material_id'):
                            del st.session_state.edit_material_id
                        st.experimental_rerun()
            else:
                st.error(f"Matériau #{material_id} non trouvé.")
                st.session_state.show_edit_material = False
                if hasattr(st.session_state, 'edit_material_id'):
                    del st.session_state.edit_material_id
                st.experimental_rerun()
    
    # Modal pour confirmer la suppression
    if 'show_delete_material' in st.session_state and st.session_state.show_delete_material:
        if hasattr(st.session_state, 'delete_material_id'):
            material_id = st.session_state.delete_material_id
            material = next((item for item in bom_items if item.get('id') == material_id), None)
            
            if material:
                st.markdown(f"""
                <div style="background: linear-gradient(to right, #fff3e0, #ffecb3);
                            border-radius: 12px; padding: 20px; margin-bottom: 20px;
                            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
                            border-left: 5px solid #ff9800;">
                    <div style="font-weight: 600; margin-bottom: 15px; color: #e65100; font-size: 18px;">
                        ⚠️ Confirmation de suppression
                    </div>
                    <p>Êtes-vous sûr de vouloir supprimer le matériau suivant?</p>
                    <ul>
                        <li><strong>Code:</strong> {material.get('code', '-')}</li>
                        <li><strong>Désignation:</strong> {material.get('designation', 'Sans nom')}</li>
                        <li><strong>Quantité:</strong> {material.get('quantite', 0)} {material.get('unite', '')}</li>
                        <li><strong>Prix unitaire:</strong> {format_currency(material.get('prix_unitaire', 0))}</li>
                    </ul>
                    <p>Cette action est irréversible.</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Oui, supprimer", use_container_width=True):
                        with st.spinner("Suppression en cours..."):
                            # Supprimer le matériau
                            gestionnaire.gestionnaire_bom.supprimer_materiau(material_id)
                            gestionnaire.sauvegarder_projets()
                            st.success("Matériau supprimé avec succès!")
                            st.session_state.show_delete_material = False
                            if hasattr(st.session_state, 'delete_material_id'):
                                del st.session_state.delete_material_id
                            st.experimental_rerun()
                
                with col2:
                    if st.button("❌ Non, annuler", use_container_width=True):
                        st.session_state.show_delete_material = False
                        if hasattr(st.session_state, 'delete_material_id'):
                            del st.session_state.delete_material_id
                        st.experimental_rerun()
            else:
                st.error(f"Matériau #{material_id} non trouvé.")
                st.session_state.show_delete_material = False
                if hasattr(st.session_state, 'delete_material_id'):
                    del st.session_state.delete_material_id
                st.experimental_rerun()

if __name__ == "__main__":
    import io  # Pour l'export Excel
    app()