# nomenclature.py - Version SQLite adaptée pour ERP Production DG Inc.
# Compatible avec la nouvelle architecture unifiée

import streamlit as st
import pandas as pd
import plotly.express as px
import io
from datetime import datetime
from erp_database import ERPDatabase

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
    
    window.addEventListener('message', function(event) {
        if (event.data.type === 'streamlit:render') {
            setTimeout(function() {
                const buttons = document.querySelectorAll('button[data-baseweb="button"]');
                if (buttons.length > 0) {
                    buttons.forEach(function(button) {
                        button.setAttribute('data-is-mobile', checkIfMobile());
                    });
                }
            }, 500);
        }
    });
    </script>
    """, unsafe_allow_html=True)
    
    return st.session_state.is_mobile

def format_currency(value):
    """Formate une valeur numérique en devise CAD."""
    if value is None:
        return "$0.00"
    try:
        s_value = str(value).replace(' ','').replace('€','').replace('$','')
        if ',' in s_value and ('.' not in s_value or s_value.find(',') > s_value.find('.')):
             s_value = s_value.replace('.', '')
             s_value = s_value.replace(',', '.')
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
    .material-count { border-left-color: #bbdefb; }
    .total-cost { border-left-color: #c8e6c9; }
    .average-cost { border-left-color: #ffecb3; }
    </style>
    """, unsafe_allow_html=True)
    
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
        
    data = []
    for item in bom_items:
        qty = item.get('quantite', 0) or 0
        price = item.get('prix_unitaire', 0) or 0
        total_item_cost = qty * price
        
        data.append({
            'designation': item.get('designation', 'Sans nom'),
            'code': item.get('code_materiau', ''),
            'cout_total': total_item_cost,
            'unite': item.get('unite', ''),
            'quantite': qty
        })
    
    df = pd.DataFrame(data)
    if df.empty or df['cout_total'].sum() == 0:
        st.info("Pas assez de données pour générer un graphique.")
        return
        
    df = df.sort_values('cout_total', ascending=False)
    
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
    
    fig = px.bar(
        df_display, 
        x='designation', 
        y='cout_total',
        title="Distribution des coûts par matériau (SQLite)",
        labels={'designation': 'Matériau', 'cout_total': 'Coût total ($)'},
        color='cout_total',
        color_continuous_scale='blues',
        text=df_display['cout_total'].apply(lambda x: f"${x:,.2f}")
    )
    
    fig.update_traces(texttemplate='%{text}', textposition='outside')
    fig.update_layout(
        uniformtext_minsize=8, 
        uniformtext_mode='hide',
        plot_bgcolor='rgba(247, 249, 252, 0.8)',
        paper_bgcolor='rgba(247, 249, 252, 0)',
        font=dict(family="Arial, sans-serif", size=12, color="#444444"),
        margin=dict(l=20, r=20, t=50, b=30),
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial")
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    fig_pie = px.pie(
        df_display, 
        values='cout_total', 
        names='designation',
        title="Répartition des coûts (%) - SQLite",
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
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)

class BOMManagerSQLite:
    """Gestionnaire de nomenclature (BOM) utilisant SQLite"""
    
    def __init__(self, db: ERPDatabase):
        self.db = db
    
    def get_materials_by_project(self, project_id):
        """Récupère tous les matériaux d'un projet depuis SQLite"""
        try:
            query = '''
                SELECT m.*, p.nom_projet
                FROM materials m
                LEFT JOIN projects p ON m.project_id = p.id
                WHERE m.project_id = ?
                ORDER BY m.id
            '''
            rows = self.db.execute_query(query, (project_id,))
            return [dict(row) for row in rows]
        except Exception as e:
            st.error(f"Erreur récupération matériaux SQLite: {e}")
            return []
    
    def add_material(self, project_id, code, designation, quantite, unite, prix_unitaire, fournisseur=""):
        """Ajoute un matériau en SQLite"""
        try:
            query = '''
                INSERT INTO materials 
                (project_id, code_materiau, designation, quantite, unite, prix_unitaire, fournisseur)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            '''
            material_id = self.db.execute_insert(query, (
                project_id, code, designation, quantite, unite, prix_unitaire, fournisseur
            ))
            return material_id
        except Exception as e:
            st.error(f"Erreur ajout matériau SQLite: {e}")
            return None
    
    def update_material(self, material_id, code, designation, quantite, unite, prix_unitaire, fournisseur=""):
        """Modifie un matériau en SQLite"""
        try:
            query = '''
                UPDATE materials 
                SET code_materiau = ?, designation = ?, quantite = ?, 
                    unite = ?, prix_unitaire = ?, fournisseur = ?
                WHERE id = ?
            '''
            rows_affected = self.db.execute_update(query, (
                code, designation, quantite, unite, prix_unitaire, fournisseur, material_id
            ))
            return rows_affected > 0
        except Exception as e:
            st.error(f"Erreur modification matériau SQLite: {e}")
            return False
    
    def delete_material(self, material_id):
        """Supprime un matériau de SQLite"""
        try:
            rows_affected = self.db.execute_update("DELETE FROM materials WHERE id = ?", (material_id,))
            return rows_affected > 0
        except Exception as e:
            st.error(f"Erreur suppression matériau SQLite: {e}")
            return False

def app():
    """Application principale Nomenclature SQLite"""
    is_mobile = is_mobile_device()
    
    # Style global adapté pour SQLite
    st.markdown("""
    <style>
    .main-title {
        background: linear-gradient(135deg, #a5d8ff 0%, #ffd6e0 100%);
        padding: 20px;
        border-radius: 12px;
        color: #333;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
    }
    .main-title h1 { margin: 0; font-size: 28px; font-weight: 600; }
    
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
    div.stButton > button:has(span:contains("📥 Exporter")) {
        background: linear-gradient(90deg, #bbdefb 0%, #90caf9 100%) !important;
        color: #0d47a1 !important;
    }
    
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
    
    @media(max-width: 768px) {
        .main-title { padding: 15px; margin-bottom: 15px; }
        .main-title h1 { font-size: 24px; }
        .section-card { padding: 15px; }
        .section-header { font-size: 18px; }
        .form-card { padding: 15px; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Titre avec mention SQLite
    st.markdown('<div class="main-title"><h1>📋 Nomenclature des Matériaux (BOM) - SQLite</h1></div>', unsafe_allow_html=True)
    
    # Vérifier l'initialisation SQLite
    if 'erp_db' not in st.session_state:
        st.error("❌ Base de données SQLite non initialisée. Relancez l'application principale.")
        return
    
    # Initialiser le gestionnaire BOM SQLite
    if 'bom_manager_sqlite' not in st.session_state:
        st.session_state.bom_manager_sqlite = BOMManagerSQLite(st.session_state.erp_db)
    
    bom_manager = st.session_state.bom_manager_sqlite
    
    # Récupérer les projets depuis SQLite
    try:
        projects_rows = st.session_state.erp_db.execute_query('''
            SELECT id, nom_projet, client_nom_cache, statut, date_soumis 
            FROM projects 
            ORDER BY id DESC
        ''')
        projects = [dict(row) for row in projects_rows]
    except Exception as e:
        st.error(f"Erreur récupération projets SQLite: {e}")
        return
    
    # Sélection du projet
    st.markdown("""
    <div class="section-card" style="border-left-color: #c8e6c9;">
        <div class="section-header" style="color: #388e3c;">📁 Sélection du projet (SQLite)</div>
    """, unsafe_allow_html=True)
    
    if not projects:
        st.warning("Aucun projet disponible en SQLite. Créez d'abord un projet dans l'application principale.")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    projet_options = [(p['id'], f"#{p['id']} - {p['nom_projet']}") for p in projects]
    
    if is_mobile:
        selected_project_id = st.selectbox(
            "Sélectionner un projet:",
            options=[pid for pid, _ in projet_options],
            format_func=lambda pid: next((name for id, name in projet_options if id == pid), ""),
            key="bom_project_select_sqlite"
        )
        
        if st.button("➕ Ajouter un matériau", use_container_width=True, key="add_material_btn_sqlite"):
            st.session_state.show_add_material_sqlite = True
    else:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_project_id = st.selectbox(
                "Sélectionner un projet:",
                options=[pid for pid, _ in projet_options],
                format_func=lambda pid: next((name for id, name in projet_options if id == pid), ""),
                key="bom_project_select_sqlite"
            )
        
        with col2:
            if st.button("➕ Ajouter un matériau", use_container_width=True):
                st.session_state.show_add_material_sqlite = True
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Récupérer le projet sélectionné
    projet = next((p for p in projects if p['id'] == selected_project_id), None)
    if not projet:
        st.error(f"Projet #{selected_project_id} non trouvé en SQLite.")
        return
    
    # Information du projet
    st.markdown(f"""
    <div class="section-card" style="border-left-color: #bbdefb;">
        <div class="section-header" style="color: #1976d2;">📊 {projet['nom_projet']} (SQLite)</div>
        <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 10px;">
            <div style="background-color: #e3f2fd; padding: 5px 12px; border-radius: 20px; font-size: 14px;">
                <strong>Client:</strong> {projet.get('client_nom_cache', 'N/A')}
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
    
    # Récupérer les matériaux du projet depuis SQLite
    bom_items = bom_manager.get_materials_by_project(selected_project_id)
    
    # Onglets pour différentes vues
    tabs = st.tabs(["📋 Liste des matériaux", "📊 Analyse", "🔄 Import/Export"])
    
    with tabs[0]:  # Liste des matériaux
        if not bom_items:
            st.info("Aucun matériau défini pour ce projet en SQLite. Utilisez le bouton 'Ajouter un matériau' pour commencer.")
        else:
            # Préparer les données pour l'affichage
            display_data = []
            for item in bom_items:
                qty = item.get('quantite', 0) or 0
                price = item.get('prix_unitaire', 0) or 0
                total = qty * price
                
                display_data.append({
                    "ID": item.get('id', '?'),
                    "Code": item.get('code_materiau', ''),
                    "Désignation": item.get('designation', 'Sans nom'),
                    "Quantité": qty,
                    "Unité": item.get('unite', ''),
                    "Prix unitaire": format_currency(price),
                    "Total": format_currency(total),
                    "Fournisseur": item.get('fournisseur', '')
                })
            
            bom_df = pd.DataFrame(display_data)
            
            # Bouton pour exporter le tableau
            if not is_mobile:
                col_export, col_empty = st.columns([1, 3])
                with col_export:
                    if st.button("📥 Exporter en Excel", key="quick_export_sqlite"):
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            bom_df.to_excel(writer, sheet_name='BOM_SQLite', index=False)
                        
                        st.download_button(
                            label="⬇️ Télécharger Excel",
                            data=buffer.getvalue(),
                            file_name=f"bom_sqlite_projet_{selected_project_id}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
            
            # Afficher le tableau
            st.markdown("""
            <div style="background: linear-gradient(to right, #ffffff, #f7f9fc);
                        border-radius: 12px; padding: 15px; margin-bottom: 20px;
                        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);">
                <div style="font-weight: 600; margin-bottom: 10px; color: #333;">📋 Matériaux du projet (SQLite)</div>
            """, unsafe_allow_html=True)
            
            st.dataframe(bom_df, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Section actions sur les matériaux
            st.markdown("""
            <div style="background: linear-gradient(to right, #ffffff, #f7f9fc);
                        border-radius: 12px; padding: 15px; margin-bottom: 20px;
                        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);">
                <div style="font-weight: 600; margin-bottom: 10px; color: #333;">🔧 Actions SQLite</div>
            """, unsafe_allow_html=True)
            
            # Sélection d'un matériau pour modification/suppression
            selected_material_id = st.selectbox(
                "Sélectionner un matériau pour le modifier ou le supprimer:",
                options=[item.get('id') for item in bom_items],
                format_func=lambda id: next((f"{item.get('code_materiau', '')} - {item.get('designation', '')}" 
                                          for item in bom_items if item.get('id') == id), ""),
                key="material_select_sqlite"
            )
            
            # Boutons d'action
            if is_mobile:
                if st.button("✏️ Modifier", use_container_width=True, key="edit_material_sqlite"):
                    st.session_state.show_edit_material_sqlite = True
                    st.session_state.edit_material_id_sqlite = selected_material_id
                
                if st.button("🗑️ Supprimer", use_container_width=True, key="delete_material_sqlite"):
                    st.session_state.show_delete_material_sqlite = True
                    st.session_state.delete_material_id_sqlite = selected_material_id
            else:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Modifier", use_container_width=True, key="edit_material_sqlite"):
                        st.session_state.show_edit_material_sqlite = True
                        st.session_state.edit_material_id_sqlite = selected_material_id
                
                with col2:
                    if st.button("🗑️ Supprimer", use_container_width=True, key="delete_material_sqlite"):
                        st.session_state.show_delete_material_sqlite = True
                        st.session_state.delete_material_id_sqlite = selected_material_id
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    with tabs[1]:  # Analyse des coûts
        if not bom_items:
            st.info("Ajoutez des matériaux pour voir l'analyse des coûts SQLite.")
        else:
            # Statistiques améliorées
            st.markdown("""
            <div style="background: linear-gradient(to right, #ffffff, #f7f9fc);
                        border-radius: 12px; padding: 15px; margin-bottom: 20px;
                        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);">
                <div style="font-weight: 600; margin-bottom: 10px; color: #333;">📈 Statistiques SQLite</div>
            """, unsafe_allow_html=True)
            
            display_bom_stats(bom_items, is_mobile)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Graphiques améliorés
            st.markdown("""
            <div style="background: linear-gradient(to right, #ffffff, #f7f9fc);
                        border-radius: 12px; padding: 15px; margin-bottom: 20px;
                        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);">
                <div style="font-weight: 600; margin-bottom: 10px; color: #333;">📊 Visualisation des coûts SQLite</div>
            """, unsafe_allow_html=True)
            
            plot_bom_cost_distribution(bom_items)
            st.markdown("</div>", unsafe_allow_html=True)
    
    with tabs[2]:  # Import/Export
        # Section export SQLite
        st.markdown("""
        <div style="background: linear-gradient(to right, #ffffff, #f7f9fc);
                    border-radius: 12px; padding: 15px; margin-bottom: 20px;
                    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);">
            <div style="font-weight: 600; margin-bottom: 10px; color: #1976d2;">📤 Exporter la BOM (SQLite)</div>
        """, unsafe_allow_html=True)
        
        if is_mobile:
            export_format = st.radio("Format:", ["CSV", "Excel"], horizontal=True)
            
            if st.button("📥 Exporter SQLite", use_container_width=True):
                if bom_items:
                    export_data = []
                    for item in bom_items:
                        export_data.append({
                            "code": item.get('code_materiau', ''),
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
                            label="⬇️ Télécharger CSV SQLite",
                            data=csv,
                            file_name=f"bom_sqlite_projet_{selected_project_id}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    else:  # Excel
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            export_df.to_excel(writer, sheet_name='BOM_SQLite', index=False)
                        
                        st.download_button(
                            label="⬇️ Télécharger Excel SQLite",
                            data=buffer.getvalue(),
                            file_name=f"bom_sqlite_projet_{selected_project_id}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                else:
                    st.error("Aucune donnée à exporter.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                export_format = st.radio("Format:", ["CSV", "Excel"], horizontal=True)
                
                if st.button("📥 Exporter SQLite", use_container_width=True):
                    if bom_items:
                        export_data = []
                        for item in bom_items:
                            export_data.append({
                                "code": item.get('code_materiau', ''),
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
                                label="⬇️ Télécharger CSV SQLite",
                                data=csv,
                                file_name=f"bom_sqlite_projet_{selected_project_id}.csv",
                                mime="text/csv"
                            )
                        else:  # Excel
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                export_df.to_excel(writer, sheet_name='BOM_SQLite', index=False)
                            
                            st.download_button(
                                label="⬇️ Télécharger Excel SQLite",
                                data=buffer.getvalue(),
                                file_name=f"bom_sqlite_projet_{selected_project_id}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.error("Aucune donnée à exporter.")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Section import SQLite
        st.markdown("""
        <div style="background: linear-gradient(to right, #ffffff, #f7f9fc);
                    border-radius: 12px; padding: 15px; margin-bottom: 20px;
                    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);">
            <div style="font-weight: 600; margin-bottom: 10px; color: #388e3c;">📥 Importer des matériaux (SQLite)</div>
        """, unsafe_allow_html=True)
        
        import_file = st.file_uploader("Choisir un fichier CSV ou Excel", type=["csv", "xlsx"], key="import_sqlite")
        
        if import_file is not None:
            try:
                if import_file.name.endswith('.csv'):
                    import_df = pd.read_csv(import_file)
                else:  # Excel
                    import_df = pd.read_excel(import_file)
                
                required_cols = ['designation', 'quantite', 'unite', 'prix_unitaire']
                missing_cols = [col for col in required_cols if col not in import_df.columns]
                
                if missing_cols:
                    st.error(f"Colonnes manquantes dans le fichier: {', '.join(missing_cols)}")
                else:
                    st.dataframe(import_df, use_container_width=True)
                    
                    if st.button("✅ Importer ces matériaux en SQLite", use_container_width=True):
                        with st.spinner("Importation SQLite en cours..."):
                            counter = 0
                            for _, row in import_df.iterrows():
                                if bom_manager.add_material(
                                    selected_project_id,
                                    row.get('code', ''),
                                    row['designation'],
                                    row['quantite'],
                                    row['unite'],
                                    row['prix_unitaire'],
                                    row.get('fournisseur', '')
                                ):
                                    counter += 1
                            
                            st.success(f"✅ {counter} matériaux importés avec succès en SQLite!")
                            st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de l'importation SQLite: {str(e)}")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Section d'aide
        st.markdown("""
        <div style="background: linear-gradient(to right, #e6f3ff, #f0f7ff);
                    border-radius: 12px; padding: 15px; margin-bottom: 20px;
                    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.05);
                    border-left: 4px solid #4285f4;">
            <div style="font-weight: 600; margin-bottom: 10px; color: #4285f4;">ℹ️ Conseils SQLite</div>
            <p>
                Architecture SQLite unifiée. Les colonnes requises sont:
                <ul>
                    <li><strong>designation</strong> - Nom du matériau</li>
                    <li><strong>quantite</strong> - Quantité requise</li>
                    <li><strong>unite</strong> - Unité de mesure</li>
                    <li><strong>prix_unitaire</strong> - Prix unitaire</li>
                </ul>
                Colonnes optionnelles: <strong>code</strong> et <strong>fournisseur</strong>.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Modal pour ajouter un matériau (SQLite)
    if st.session_state.get('show_add_material_sqlite', False):
        st.markdown("""
        <div class="form-card">
            <div class="form-header">➕ Ajouter un matériau (SQLite)</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("add_material_form_sqlite"):
            col1, col2 = st.columns(2)
            with col1:
                code = st.text_input("Code:")
                designation = st.text_input("Désignation:")
                quantite = st.number_input("Quantité:", min_value=0.0, step=0.1)
            
            with col2:
                unite = st.selectbox("Unité:", ["pcs", "kg", "m", "m²", "m³", "L"])
                prix = st.number_input("Prix unitaire:", min_value=0.0, step=0.01)
                fournisseur = st.text_input("Fournisseur (optionnel):")
            
            total = quantite * prix
            st.markdown(f"""
            <div style="background-color: #e8f5e9; padding: 10px; border-radius: 8px; margin-top: 10px;">
                <strong>Total estimé (SQLite):</strong> {format_currency(total)}
            </div>
            """, unsafe_allow_html=True)
            
            submit = st.form_submit_button("Ajouter en SQLite", use_container_width=True)
            if submit:
                if not designation:
                    st.error("La désignation est requise.")
                else:
                    with st.spinner("Ajout SQLite en cours..."):
                        material_id = bom_manager.add_material(
                            selected_project_id, code, designation, quantite, unite, prix, fournisseur
                        )
                        if material_id:
                            st.success(f"✅ Matériau #{material_id} ajouté avec succès en SQLite!")
                            st.session_state.show_add_material_sqlite = False
                            st.rerun()
                        else:
                            st.error("❌ Erreur lors de l'ajout en SQLite.")
        
        col1, col2 = st.columns(2)
        with col2:
            if st.button("Annuler", key="cancel_add_material_sqlite", use_container_width=True):
                st.session_state.show_add_material_sqlite = False
                st.rerun()
    
    # Modal pour modifier un matériau (SQLite)
    if st.session_state.get('show_edit_material_sqlite', False):
        if hasattr(st.session_state, 'edit_material_id_sqlite'):
            material_id = st.session_state.edit_material_id_sqlite
            material = next((item for item in bom_items if item.get('id') == material_id), None)
            
            if material:
                st.markdown(f"""
                <div class="form-card">
                    <div class="form-header">✏️ Modifier le matériau #{material_id} (SQLite)</div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.form("edit_material_form_sqlite"):
                    col1, col2 = st.columns(2)
                    with col1:
                        code = st.text_input("Code:", value=material.get('code_materiau', ''))
                        designation = st.text_input("Désignation:", value=material.get('designation', ''))
                        quantite = st.number_input("Quantité:", min_value=0.0, step=0.1, value=float(material.get('quantite', 0)))
                    
                    with col2:
                        unites = ["pcs", "kg", "m", "m²", "m³", "L"]
                        unite_index = unites.index(material.get('unite')) if material.get('unite') in unites else 0
                        unite = st.selectbox("Unité:", unites, index=unite_index)
                        
                        prix = st.number_input("Prix unitaire:", min_value=0.0, step=0.01, value=float(material.get('prix_unitaire', 0)))
                        fournisseur = st.text_input("Fournisseur:", value=material.get('fournisseur', ''))
                    
                    total = quantite * prix
                    st.markdown(f"""
                    <div style="background-color: #e8f5e9; padding: 10px; border-radius: 8px; margin-top: 10px;">
                        <strong>Total estimé (SQLite):</strong> {format_currency(total)}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    submit = st.form_submit_button("Enregistrer les modifications SQLite", use_container_width=True)
                    if submit:
                        if not designation:
                            st.error("La désignation est requise.")
                        else:
                            with st.spinner("Modification SQLite en cours..."):
                                if bom_manager.update_material(
                                    material_id, code, designation, quantite, unite, prix, fournisseur
                                ):
                                    st.success("✅ Matériau modifié avec succès en SQLite!")
                                    st.session_state.show_edit_material_sqlite = False
                                    del st.session_state.edit_material_id_sqlite
                                    st.rerun()
                                else:
                                    st.error("❌ Erreur lors de la modification SQLite.")
                
                col1, col2 = st.columns(2)
                with col2:
                    if st.button("Annuler", key="cancel_edit_material_sqlite", use_container_width=True):
                        st.session_state.show_edit_material_sqlite = False
                        if hasattr(st.session_state, 'edit_material_id_sqlite'):
                            del st.session_state.edit_material_id_sqlite
                        st.rerun()
            else:
                st.error(f"Matériau #{material_id} non trouvé en SQLite.")
                st.session_state.show_edit_material_sqlite = False
                if hasattr(st.session_state, 'edit_material_id_sqlite'):
                    del st.session_state.edit_material_id_sqlite
                st.rerun()
    
    # Modal pour confirmer la suppression (SQLite)
    if st.session_state.get('show_delete_material_sqlite', False):
        if hasattr(st.session_state, 'delete_material_id_sqlite'):
            material_id = st.session_state.delete_material_id_sqlite
            material = next((item for item in bom_items if item.get('id') == material_id), None)
            
            if material:
                st.markdown(f"""
                <div style="background: linear-gradient(to right, #fff3e0, #ffecb3);
                            border-radius: 12px; padding: 20px; margin-bottom: 20px;
                            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
                            border-left: 5px solid #ff9800;">
                    <div style="font-weight: 600; margin-bottom: 15px; color: #e65100; font-size: 18px;">
                        ⚠️ Confirmation de suppression (SQLite)
                    </div>
                    <p>Êtes-vous sûr de vouloir supprimer le matériau suivant de SQLite?</p>
                    <ul>
                        <li><strong>Code:</strong> {material.get('code_materiau', '-')}</li>
                        <li><strong>Désignation:</strong> {material.get('designation', 'Sans nom')}</li>
                        <li><strong>Quantité:</strong> {material.get('quantite', 0)} {material.get('unite', '')}</li>
                        <li><strong>Prix unitaire:</strong> {format_currency(material.get('prix_unitaire', 0))}</li>
                    </ul>
                    <p>Cette action est irréversible.</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Oui, supprimer SQLite", use_container_width=True):
                        with st.spinner("Suppression SQLite en cours..."):
                            if bom_manager.delete_material(material_id):
                                st.success("✅ Matériau supprimé avec succès de SQLite!")
                                st.session_state.show_delete_material_sqlite = False
                                if hasattr(st.session_state, 'delete_material_id_sqlite'):
                                    del st.session_state.delete_material_id_sqlite
                                st.rerun()
                            else:
                                st.error("❌ Erreur lors de la suppression SQLite.")
                
                with col2:
                    if st.button("❌ Non, annuler", use_container_width=True):
                        st.session_state.show_delete_material_sqlite = False
                        if hasattr(st.session_state, 'delete_material_id_sqlite'):
                            del st.session_state.delete_material_id_sqlite
                        st.rerun()
            else:
                st.error(f"Matériau #{material_id} non trouvé en SQLite.")
                st.session_state.show_delete_material_sqlite = False
                if hasattr(st.session_state, 'delete_material_id_sqlite'):
                    del st.session_state.delete_material_id_sqlite
                st.rerun()

if __name__ == "__main__":
    app()
