# production_management.py - Module Production Unifié
# ERP Production DG Inc. - Inventaire + Nomenclature + Itinéraire
# Architecture unifiée avec interface à onglets

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from math import gcd
from fractions import Fraction

# Import conditionnel pour les dépendances
try:
    from erp_database import ERPDatabase, convertir_pieds_pouces_fractions_en_valeur_decimale, convertir_imperial_vers_metrique
    ERP_DATABASE_AVAILABLE = True
except ImportError:
    ERP_DATABASE_AVAILABLE = False

# Import networkx avec gestion d'erreur pour itinéraire
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

# =========================================================================
# CONSTANTES ET UTILITAIRES (extraits de app.py)
# =========================================================================

UNITES_MESURE = ["IMPÉRIAL", "MÉTRIQUE"]
TYPES_PRODUITS_INVENTAIRE = ["BOIS", "MÉTAL", "QUINCAILLERIE", "OUTILLAGE", "MATÉRIAUX", "ACCESSOIRES", "AUTRE"]
STATUTS_STOCK_INVENTAIRE = ["DISPONIBLE", "FAIBLE", "CRITIQUE", "EN COMMANDE", "ÉPUISÉ", "INDÉTERMINÉ"]

# Fonctions utilitaires extraites de app.py
def convertir_en_pieds_pouces_fractions(valeur_decimale_pieds_input):
    """Convertit une valeur décimale en pieds vers format pieds' pouces fractions\""""
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
    """Valide une mesure saisie et retourne le format standardisé"""
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
    """Met à jour le statut de stock selon les quantités"""
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
    """Formate une valeur numérique en devise CAD (extrait de nomenclature.py)"""
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

# =========================================================================
# GESTIONNAIRE INVENTAIRE (extrait de app.py)
# =========================================================================

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

# =========================================================================
# GESTIONNAIRE NOMENCLATURE (extrait de nomenclature.py)
# =========================================================================

def calculate_totals(bom_items):
    """Calcule les totaux pour la BOM"""
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
    """Affiche des statistiques sur la BOM avec style amélioré"""
    if not bom_items:
        st.info("Aucun matériau à analyser.")
        return
        
    totals = calculate_totals(bom_items)
    
    if is_mobile:
        st.metric("📦 Matériaux", totals['item_count'])
        st.metric("💰 Coût Total", format_currency(totals['total_cost']))
        st.metric("📊 Coût Moyen", format_currency(totals['total_cost'] / totals['item_count'] if totals['item_count'] > 0 else 0))
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📦 Matériaux", totals['item_count'])
        with col2:
            st.metric("💰 Coût Total", format_currency(totals['total_cost']))
        with col3:
            avg_cost = totals['total_cost'] / totals['item_count'] if totals['item_count'] > 0 else 0
            st.metric("📊 Coût Moyen", format_currency(avg_cost))

def plot_bom_cost_distribution(bom_items):
    """Crée un graphique de distribution des coûts avec style amélioré"""
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
            'cout_total': total_item_cost
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
            'code': '-'
        }
    else:
        df_display = df
    
    fig = px.pie(
        df_display, 
        values='cout_total', 
        names='designation',
        title="Répartition des coûts par matériau",
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.Blues_r
    )
    
    fig.update_layout(
        plot_bgcolor='rgba(247, 249, 252, 0.8)',
        paper_bgcolor='rgba(247, 249, 252, 0)',
        font=dict(family="Arial, sans-serif", size=12, color="#444444")
    )
    
    st.plotly_chart(fig, use_container_width=True)

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
            st.error(f"Erreur récupération matériaux: {e}")
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
            st.error(f"Erreur ajout matériau: {e}")
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
            st.error(f"Erreur modification matériau: {e}")
            return False
    
    def delete_material(self, material_id):
        """Supprime un matériau de SQLite"""
        try:
            rows_affected = self.db.execute_update("DELETE FROM materials WHERE id = ?", (material_id,))
            return rows_affected > 0
        except Exception as e:
            st.error(f"Erreur suppression matériau: {e}")
            return False

# =========================================================================
# GESTIONNAIRE ITINÉRAIRE (extrait de itineraire.py)
# =========================================================================

def is_mobile_device():
    """Estimation si l'appareil est mobile basée sur la largeur de viewport"""
    if 'is_mobile' not in st.session_state:
        st.session_state.is_mobile = False
    return st.session_state.is_mobile

def format_duration(hours):
    """Formate un nombre d'heures en jours, heures"""
    if hours is None:
        return "0h"
    
    days = int(hours // 8)  # Considère 8h par jour de travail
    remaining_hours = hours % 8
    
    if days > 0:
        return f"{days}j {remaining_hours:.1f}h"
    else:
        return f"{hours:.1f}h"

def create_gantt_chart(routing_items):
    """Crée un diagramme de Gantt pour visualiser les opérations"""
    if not routing_items:
        return None
    
    # Calcul des dates de début optimisées
    early_starts = {}
    
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
        for op in routing_items:
            early_starts[op.get('id')] = 0
    
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
    
    # Couleurs selon le statut
    color_map = {
        'À FAIRE': '#9ebdd8',
        'EN COURS': '#8fd1cd', 
        'TERMINÉ': '#a5d8a7',
        'EN ATTENTE': '#f8d0a9',
        'ANNULÉ': '#f4a6a6'
    }
    
    # Créer le diagramme
    fig = px.timeline(
        df, 
        x_start='Start', 
        x_end='Finish', 
        y='Task',
        color='Status',
        color_discrete_map=color_map,
        title="Planification des opérations"
    )
    
    fig.update_layout(
        autosize=True,
        height=max(400, 100 + 40 * len(df)),
        plot_bgcolor='rgba(248, 249, 250, 1)',
        paper_bgcolor='rgba(248, 249, 250, 0)',
        font=dict(family="Arial, sans-serif", size=12, color="#444444")
    )
    
    return fig

def visualize_network(routing_items):
    """Visualise le réseau de dépendances des opérations"""
    if not routing_items or not NETWORKX_AVAILABLE:
        return None
    
    # Créer un graphe dirigé
    G = nx.DiGraph()
    
    # Ajouter les nœuds avec attributs
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
    
    # Mise en page du graphe
    pos = nx.spring_layout(G, k=0.5, iterations=100)
    
    # Créer le graphique avec Plotly
    edge_trace = go.Scatter(
        x=[], y=[],
        line=dict(width=1.5, color='rgba(180, 200, 220, 0.7)'),
        hoverinfo='none',
        mode='lines'
    )
    
    # Ajouter les arêtes
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace['x'] += (x0, x1, None)
        edge_trace['y'] += (y0, y1, None)
    
    # Couleurs des nœuds selon le statut
    node_colors = {
        'À FAIRE': '#9ebdd8',
        'EN COURS': '#8fd1cd',
        'TERMINÉ': '#a5d8a7',
        'EN ATTENTE': '#f8d0a9',
        'ANNULÉ': '#f4a6a6'
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
    
    # Créer la figure
    fig = go.Figure(data=[edge_trace, node_trace],
                  layout=go.Layout(
                      title="Réseau de dépendances des opérations",
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
    """Calcule et renvoie le chemin critique du projet"""
    if not routing_items:
        return []
    
    if not NETWORKX_AVAILABLE:
        # Version simplifiée sans networkx
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
    
    # Méthode complète avec networkx
    G = nx.DiGraph()
    
    # Ajouter les nœuds et les arêtes avec durées
    for op in routing_items:
        op_id = op.get('id')
        G.add_node(op_id, duration=op.get('temps_estime', 0) or 0, description=op.get('description', ''))
        
        # Ajouter les dépendances
        pred_id = op.get('predecesseur_id')
        if pred_id is not None and pred_id != op_id:
            pred_op = next((item for item in routing_items if item.get('id') == pred_id), None)
            if pred_op:
                weight = pred_op.get('temps_estime', 0) or 0
                G.add_edge(pred_id, op_id, weight=weight)
    
    # Trouver les nœuds de départ et d'arrivée
    start_nodes = [n for n in G.nodes() if G.in_degree(n) == 0]
    end_nodes = [n for n in G.nodes() if G.out_degree(n) == 0]
    
    if len(start_nodes) == 0:
        return []  # Graphe cyclique, pas de chemin critique
    
    # Trouver le chemin critique (le plus long)
    critical_path = None
    max_path_length = -1
    
    for start_node in start_nodes:
        for end_node in end_nodes:
            try:
                for path in nx.all_simple_paths(G, start_node, end_node):
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

# =========================================================================
# FONCTIONS D'INITIALISATION
# =========================================================================

def init_production_session_state():
    """Initialise les variables de session pour production"""
    session_vars = {
        'inv_action_mode': "Voir Liste",
        'show_add_material_sqlite': False,
        'show_edit_material_sqlite': False,
        'show_delete_material_sqlite': False,
        'edit_material_id_sqlite': None,
        'delete_material_id_sqlite': None,
        'show_add_operation': False,
        'show_edit_operation': False,
        'show_delete_operation': False,
        'edit_operation_id': None,
        'delete_operation_id': None,
        'show_update_status': False,
        'update_status_id': None
    }
    
    for key, default_value in session_vars.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def apply_production_styles():
    """Applique les styles CSS pour le module production"""
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
    .production-tab-content {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin-top: 10px;
    }
    /* Styles pour inventaire */
    .inventory-metrics {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    /* Styles pour nomenclature */
    .bom-stats {
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    /* Styles pour itinéraire */
    .routing-operations {
        background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# =========================================================================
# INTERFACE PRINCIPALE UNIFIÉE
# =========================================================================

def show_production_management_page():
    """Interface principale avec onglets unifiés"""
    # Appliquer les styles
    apply_production_styles()
    
    # Initialiser les variables de session
    init_production_session_state()
    
    # Vérifier les gestionnaires
    if 'erp_db' not in st.session_state:
        st.error("❌ Base de données non initialisée")
        return
    
    # Header unifié
    st.markdown("""
    <div class="main-title">
        <h1>🏭 Gestion de Production - DG Inc.</h1>
        <p>Interface unifiée : Inventaire • Nomenclature • Itinéraire</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Onglets principaux
    tabs = st.tabs([
        "📦 Inventaire", 
        "📋 Nomenclature (BOM)", 
        "🛠️ Itinéraire de Fabrication"
    ])
    
    with tabs[0]:
        show_inventory_tab()
    
    with tabs[1]:
        show_nomenclature_tab()
    
    with tabs[2]:
        show_itineraire_tab()

def show_inventory_tab():
    """Onglet gestion inventaire (extrait de show_inventory_management_page)"""
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

def show_nomenclature_tab():
    """Onglet nomenclature BOM (extrait de nomenclature.py)"""
    is_mobile = is_mobile_device()
    
    st.markdown("### 📋 Nomenclature des Matériaux (BOM)")
    
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
        st.error(f"Erreur récupération projets: {e}")
        return
    
    # Sélection du projet
    if not projects:
        st.warning("Aucun projet disponible. Créez d'abord un projet dans l'application principale.")
        return
    
    projet_options = [(p['id'], f"#{p['id']} - {p['nom_projet']}") for p in projects]
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected_project_id = st.selectbox(
            "Sélectionner un projet:",
            options=[pid for pid, _ in projet_options],
            format_func=lambda pid: next((name for id, name in projet_options if id == pid), ""),
            key="bom_project_select_unified"
        )
    
    with col2:
        if st.button("➕ Ajouter un matériau", use_container_width=True):
            st.session_state.show_add_material_sqlite = True
    
    # Récupérer le projet sélectionné
    projet = next((p for p in projects if p['id'] == selected_project_id), None)
    if not projet:
        st.error(f"Projet #{selected_project_id} non trouvé.")
        return
    
    # Information du projet
    st.markdown(f"""
    <div class="bom-stats">
        <h4>📊 {projet['nom_projet']}</h4>
        <p><strong>Client:</strong> {projet.get('client_nom_cache', 'N/A')} | 
           <strong>Statut:</strong> {projet.get('statut', 'N/A')} | 
           <strong>Date:</strong> {projet.get('date_soumis', 'N/A')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Récupérer les matériaux du projet
    bom_items = bom_manager.get_materials_by_project(selected_project_id)
    
    # Onglets secondaires pour BOM
    bom_tabs = st.tabs(["📋 Liste des matériaux", "📊 Analyse", "🔄 Import/Export"])
    
    with bom_tabs[0]:  # Liste des matériaux
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
                    "Code": item.get('code_materiau', ''),
                    "Désignation": item.get('designation', 'Sans nom'),
                    "Quantité": qty,
                    "Unité": item.get('unite', ''),
                    "Prix unitaire": format_currency(price),
                    "Total": format_currency(total),
                    "Fournisseur": item.get('fournisseur', '')
                })
            
            bom_df = pd.DataFrame(display_data)
            st.dataframe(bom_df, use_container_width=True)
            
            # Actions sur les matériaux
            selected_material_id = st.selectbox(
                "Sélectionner un matériau pour le modifier ou le supprimer:",
                options=[item.get('id') for item in bom_items],
                format_func=lambda id: next((f"{item.get('code_materiau', '')} - {item.get('designation', '')}" 
                                          for item in bom_items if item.get('id') == id), ""),
                key="material_select_unified"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✏️ Modifier", use_container_width=True, key="edit_material_unified"):
                    st.session_state.show_edit_material_sqlite = True
                    st.session_state.edit_material_id_sqlite = selected_material_id
            
            with col2:
                if st.button("🗑️ Supprimer", use_container_width=True, key="delete_material_unified"):
                    st.session_state.show_delete_material_sqlite = True
                    st.session_state.delete_material_id_sqlite = selected_material_id
    
    with bom_tabs[1]:  # Analyse des coûts
        if not bom_items:
            st.info("Ajoutez des matériaux pour voir l'analyse des coûts.")
        else:
            display_bom_stats(bom_items, is_mobile)
            plot_bom_cost_distribution(bom_items)
    
    with bom_tabs[2]:  # Import/Export
        st.info("Fonctionnalités d'import/export à implémenter")

def show_itineraire_tab():
    """Onglet itinéraire fabrication (extrait de itineraire.py)"""
    st.markdown("### 🛠️ Itinéraire de Fabrication")
    
    # Vérifier le gestionnaire de projets
    if 'gestionnaire' not in st.session_state:
        st.error("Gestionnaire de projets non initialisé.")
        return
    
    gestionnaire = st.session_state.gestionnaire
    
    # Sélection du projet
    projet_options = [(p.get('id'), f"#{p.get('id')} - {p.get('nom_projet', 'Sans Nom')}") 
                     for p in gestionnaire.projets]
    
    if not projet_options:
        st.warning("Aucun projet disponible. Veuillez d'abord créer un projet.")
        return
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected_project_id = st.selectbox(
            "Sélectionner un projet:",
            options=[pid for pid, _ in projet_options],
            format_func=lambda pid: next((name for id, name in projet_options if id == pid), ""),
            key="routing_project_select_unified"
        )
    
    with col2:
        if st.button("➕ Ajouter une opération", use_container_width=True):
            st.session_state.show_add_operation = True
    
    # Récupérer le projet sélectionné
    projet = next((p for p in gestionnaire.projets if p.get('id') == selected_project_id), None)
    if not projet:
        st.error(f"Projet #{selected_project_id} non trouvé.")
        return
    
    # Information du projet
    st.markdown(f"""
    <div class="routing-operations">
        <h4>📋 {projet.get('nom_projet')}</h4>
        <p><strong>Client:</strong> {projet.get('client_nom_cache', 'N/A')} | 
           <strong>Statut:</strong> {projet.get('statut', 'N/A')} | 
           <strong>Date:</strong> {projet.get('date_soumis', 'N/A')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Récupérer les opérations du projet
    operations = projet.get('operations', [])
    
    # Onglets secondaires pour itinéraire
    routing_tabs = st.tabs(["📋 Liste des opérations", "📊 Diagramme de Gantt", "🔄 Réseau", "📈 Analyse"])
    
    with routing_tabs[0]:  # Liste des opérations
        if not operations:
            st.info("Aucune opération définie pour ce projet.")
        else:
            total_time = sum(op.get('temps_estime', 0) for op in operations)
            finished_ops = sum(1 for op in operations if op.get('statut') == 'TERMINÉ')
            progress = (finished_ops / len(operations) * 100) if operations else 0

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🔧 Opérations", len(operations))
            with col2:
                st.metric("⏱️ Durée Totale", f"{total_time:.1f}h")
            with col3:
                st.metric("📊 Progression", f"{progress:.1f}%")

            # Tableau des opérations
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
    
    with routing_tabs[1]:  # Diagramme de Gantt
        if not operations:
            st.info("Aucune opération à afficher dans le diagramme de Gantt.")
        else:
            fig = create_gantt_chart(operations)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Impossible de générer le diagramme de Gantt.")
    
    with routing_tabs[2]:  # Réseau de dépendances
        if not operations:
            st.info("Aucune opération à afficher dans le réseau.")
        elif not NETWORKX_AVAILABLE:
            st.warning("La visualisation du réseau de dépendances nécessite le module 'networkx'.")
        else:
            fig = visualize_network(operations)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Impossible de générer le réseau.")
    
    with routing_tabs[3]:  # Analyse
        if not operations:
            st.info("Aucune opération à analyser.")
        else:
            # Calcul de statistiques
            total_time = sum(op.get('temps_estime', 0) or 0 for op in operations)
            finished_ops = sum(1 for op in operations if op.get('statut') == 'TERMINÉ')
            progress = finished_ops / len(operations) * 100 if operations else 0
            
            # Statistiques générales
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Nombre d'opérations", len(operations))
            with col2:
                st.metric("Durée totale estimée", format_duration(total_time))
            with col3:
                st.metric("Progression", f"{progress:.1f}%")
            
            # Chemin critique
            st.markdown("#### ⏱️ Chemin critique")
            
            if not NETWORKX_AVAILABLE:
                st.info("Le calcul précis du chemin critique nécessite le module 'networkx'.")
                
            critical_path = calculate_critical_path(operations)
            
            if critical_path:
                critical_time = sum(op.get('temps_estime', 0) or 0 for op in critical_path)
                st.metric("Durée du chemin critique", format_duration(critical_time))
                
                # Afficher les opérations du chemin critique
                cp_data = []
                for op in critical_path:
                    cp_data.append({
                        "Séquence": op.get('sequence', ''),
                        "Opération": op.get('description', ''),
                        "Durée": format_duration(op.get('temps_estime', 0) or 0),
                        "Statut": op.get('statut', 'À FAIRE')
                    })
                
                st.markdown("**Opérations du chemin critique:**")
                cp_df = pd.DataFrame(cp_data)
                st.dataframe(cp_df, use_container_width=True)
            else:
                st.warning("Impossible de déterminer le chemin critique.")

# Point d'entrée du module
if __name__ == "__main__":
    show_production_management_page()
