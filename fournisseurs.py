# fournisseurs.py - Module Fournisseurs pour ERP Production DG Inc.
# Gestion complète des fournisseurs, évaluations, performances et intégrations

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import json
from typing import Dict, List, Optional, Any

class GestionnaireFournisseurs:
    """
    Gestionnaire complet pour les fournisseurs de l'ERP Production DG Inc.
    Intégré avec la base de données SQLite unifiée
    """
    
    def __init__(self, db):
        self.db = db
    
    def get_all_fournisseurs(self) -> List[Dict]:
        """Récupère tous les fournisseurs avec leurs statistiques"""
        try:
            return self.db.get_fournisseurs_with_stats()
        except Exception as e:
            st.error(f"Erreur récupération fournisseurs: {e}")
            return []
    
    def get_fournisseur_by_id(self, fournisseur_id: int) -> Dict:
        """Récupère un fournisseur par ID avec détails complets"""
        try:
            query = '''
                SELECT f.*, c.nom, c.secteur, c.adresse, c.site_web, c.notes as company_notes
                FROM fournisseurs f
                JOIN companies c ON f.company_id = c.id
                WHERE f.id = ?
            '''
            result = self.db.execute_query(query, (fournisseur_id,))
            return dict(result[0]) if result else {}
        except Exception as e:
            st.error(f"Erreur récupération fournisseur: {e}")
            return {}
    
    def get_fournisseurs_by_category(self, category: str = None) -> List[Dict]:
        """Récupère les fournisseurs par catégorie"""
        try:
            if category:
                query = '''
                    SELECT f.*, c.nom, c.secteur
                    FROM fournisseurs f
                    JOIN companies c ON f.company_id = c.id
                    WHERE f.categorie_produits LIKE ? AND f.est_actif = TRUE
                    ORDER BY c.nom
                '''
                rows = self.db.execute_query(query, (f"%{category}%",))
            else:
                query = '''
                    SELECT f.*, c.nom, c.secteur
                    FROM fournisseurs f
                    JOIN companies c ON f.company_id = c.id
                    WHERE f.est_actif = TRUE
                    ORDER BY c.nom
                '''
                rows = self.db.execute_query(query)
            
            return [dict(row) for row in rows]
        except Exception as e:
            st.error(f"Erreur récupération par catégorie: {e}")
            return []
    
    def create_fournisseur(self, company_id: int, fournisseur_data: Dict) -> int:
        """Crée un nouveau fournisseur"""
        try:
            return self.db.add_fournisseur(company_id, fournisseur_data)
        except Exception as e:
            st.error(f"Erreur création fournisseur: {e}")
            return None
    
    def update_fournisseur(self, fournisseur_id: int, fournisseur_data: Dict) -> bool:
        """Met à jour un fournisseur existant"""
        try:
            # Construire la requête de mise à jour
            update_fields = []
            params = []
            
            for field in ['code_fournisseur', 'categorie_produits', 'delai_livraison_moyen', 
                         'conditions_paiement', 'evaluation_qualite', 'contact_commercial',
                         'contact_technique', 'certifications', 'notes_evaluation', 'est_actif']:
                if field in fournisseur_data:
                    update_fields.append(f"{field} = ?")
                    params.append(fournisseur_data[field])
            
            if update_fields:
                query = f"UPDATE fournisseurs SET {', '.join(update_fields)} WHERE id = ?"
                params.append(fournisseur_id)
                
                affected = self.db.execute_update(query, tuple(params))
                return affected > 0
            
            return False
            
        except Exception as e:
            st.error(f"Erreur mise à jour fournisseur: {e}")
            return False
    
    def delete_fournisseur(self, fournisseur_id: int) -> bool:
        """Désactive un fournisseur (soft delete)"""
        try:
            query = "UPDATE fournisseurs SET est_actif = FALSE WHERE id = ?"
            affected = self.db.execute_update(query, (fournisseur_id,))
            return affected > 0
        except Exception as e:
            st.error(f"Erreur suppression fournisseur: {e}")
            return False
    
    def get_fournisseur_performance(self, fournisseur_id: int, days: int = 365) -> Dict:
        """Calcule les performances d'un fournisseur"""
        try:
            # Statistiques commandes
            query_commandes = '''
                SELECT 
                    COUNT(*) as total_commandes,
                    SUM(f.montant_total) as montant_total,
                    AVG(f.montant_total) as montant_moyen,
                    MIN(f.date_creation) as premiere_commande,
                    MAX(f.date_creation) as derniere_commande
                FROM formulaires f
                JOIN companies c ON f.company_id = c.id
                JOIN fournisseurs fou ON c.id = fou.company_id
                WHERE fou.id = ? 
                AND f.type_formulaire IN ('BON_ACHAT', 'BON_COMMANDE')
                AND f.date_creation >= DATE('now', '-{} days')
            '''.format(days)
            
            result = self.db.execute_query(query_commandes, (fournisseur_id,))
            performance = dict(result[0]) if result else {}
            
            # Statistiques livraisons
            query_livraisons = '''
                SELECT 
                    COUNT(*) as total_livraisons,
                    COUNT(CASE WHEN a.date_livraison_reelle <= a.date_livraison_prevue THEN 1 END) as livraisons_temps,
                    AVG(JULIANDAY(a.date_livraison_reelle) - JULIANDAY(a.date_livraison_prevue)) as retard_moyen_jours
                FROM approvisionnements a
                JOIN formulaires f ON a.formulaire_id = f.id
                JOIN companies c ON f.company_id = c.id
                JOIN fournisseurs fou ON c.id = fou.company_id
                WHERE fou.id = ? 
                AND a.date_livraison_reelle IS NOT NULL
                AND a.date_commande >= DATE('now', '-{} days')
            '''.format(days)
            
            result_livr = self.db.execute_query(query_livraisons, (fournisseur_id,))
            if result_livr:
                livraisons_data = dict(result_livr[0])
                performance.update(livraisons_data)
                
                # Calcul taux de ponctualité
                if livraisons_data.get('total_livraisons', 0) > 0:
                    performance['taux_ponctualite'] = (
                        livraisons_data.get('livraisons_temps', 0) / 
                        livraisons_data['total_livraisons'] * 100
                    )
            
            return performance
            
        except Exception as e:
            st.error(f"Erreur calcul performance: {e}")
            return {}
    
    def get_categories_disponibles(self) -> List[str]:
        """Récupère toutes les catégories de produits disponibles"""
        try:
            query = '''
                SELECT DISTINCT categorie_produits 
                FROM fournisseurs 
                WHERE categorie_produits IS NOT NULL 
                AND categorie_produits != ''
                ORDER BY categorie_produits
            '''
            rows = self.db.execute_query(query)
            return [row['categorie_produits'] for row in rows]
        except Exception as e:
            st.error(f"Erreur récupération catégories: {e}")
            return []
    
    def get_fournisseurs_statistics(self) -> Dict:
        """Retourne des statistiques globales sur les fournisseurs"""
        try:
            stats = {
                'total_fournisseurs': 0,
                'fournisseurs_actifs': 0,
                'par_categorie': {},
                'evaluation_moyenne': 0.0,
                'delai_moyen': 0,
                'montant_total_commandes': 0.0,
                'top_performers': [],
                'certifications_count': {}
            }
            
            # Statistiques de base
            query_base = '''
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN est_actif = TRUE THEN 1 END) as actifs,
                    AVG(evaluation_qualite) as eval_moy,
                    AVG(delai_livraison_moyen) as delai_moy
                FROM fournisseurs
            '''
            result = self.db.execute_query(query_base)
            if result:
                row = result[0]
                stats['total_fournisseurs'] = row['total']
                stats['fournisseurs_actifs'] = row['actifs']
                stats['evaluation_moyenne'] = round(row['eval_moy'] or 0, 1)
                stats['delai_moyen'] = round(row['delai_moy'] or 0)
            
            # Par catégorie
            query_cat = '''
                SELECT categorie_produits, COUNT(*) as count
                FROM fournisseurs
                WHERE est_actif = TRUE AND categorie_produits IS NOT NULL
                GROUP BY categorie_produits
                ORDER BY count DESC
            '''
            rows_cat = self.db.execute_query(query_cat)
            for row in rows_cat:
                if row['categorie_produits']:
                    stats['par_categorie'][row['categorie_produits']] = row['count']
            
            # Montant total commandes
            query_montant = '''
                SELECT SUM(f.montant_total) as total_montant
                FROM formulaires f
                JOIN companies c ON f.company_id = c.id
                JOIN fournisseurs fou ON c.id = fou.company_id
                WHERE f.type_formulaire IN ('BON_ACHAT', 'BON_COMMANDE')
                AND fou.est_actif = TRUE
            '''
            result_montant = self.db.execute_query(query_montant)
            if result_montant:
                stats['montant_total_commandes'] = result_montant[0]['total_montant'] or 0.0
            
            # Top performers (par évaluation et volume)
            query_top = '''
                SELECT c.nom, f.evaluation_qualite, COUNT(form.id) as nb_commandes,
                       SUM(form.montant_total) as montant_total
                FROM fournisseurs f
                JOIN companies c ON f.company_id = c.id
                LEFT JOIN formulaires form ON c.id = form.company_id 
                    AND form.type_formulaire IN ('BON_ACHAT', 'BON_COMMANDE')
                WHERE f.est_actif = TRUE
                GROUP BY f.id, c.nom, f.evaluation_qualite
                ORDER BY f.evaluation_qualite DESC, montant_total DESC
                LIMIT 5
            '''
            rows_top = self.db.execute_query(query_top)
            stats['top_performers'] = [dict(row) for row in rows_top]
            
            return stats
            
        except Exception as e:
            st.error(f"Erreur statistiques fournisseurs: {e}")
            return {}

def show_fournisseurs_page():
    """Page principale du module Fournisseurs"""
    st.markdown("## 🏪 Gestion des Fournisseurs DG Inc.")
    
    # Initialisation du gestionnaire
    if 'gestionnaire_fournisseurs' not in st.session_state:
        st.session_state.gestionnaire_fournisseurs = GestionnaireFournisseurs(st.session_state.erp_db)
    
    gestionnaire = st.session_state.gestionnaire_fournisseurs
    
    # Variables de session
    if 'fournisseur_action' not in st.session_state:
        st.session_state.fournisseur_action = None
    if 'selected_fournisseur_id' not in st.session_state:
        st.session_state.selected_fournisseur_id = None
    if 'fournisseur_filter_category' not in st.session_state:
        st.session_state.fournisseur_filter_category = 'TOUS'
    
    # Onglets principaux
    tab_dashboard, tab_liste, tab_performance, tab_categories = st.tabs([
        "📊 Dashboard Fournisseurs", "📋 Liste Fournisseurs", "📈 Performances", "🏷️ Catégories"
    ])
    
    with tab_dashboard:
        render_fournisseurs_dashboard(gestionnaire)
    
    with tab_liste:
        render_fournisseurs_liste(gestionnaire)
    
    with tab_performance:
        render_fournisseurs_performance(gestionnaire)
    
    with tab_categories:
        render_fournisseurs_categories(gestionnaire)
    
    # Formulaires modaux
    action = st.session_state.get('fournisseur_action')
    selected_id = st.session_state.get('selected_fournisseur_id')
    
    if action == "create_fournisseur":
        render_fournisseur_form(gestionnaire, fournisseur_data=None)
    elif action == "edit_fournisseur" and selected_id:
        fournisseur_data = gestionnaire.get_fournisseur_by_id(selected_id)
        render_fournisseur_form(gestionnaire, fournisseur_data=fournisseur_data)
    elif action == "view_fournisseur_details" and selected_id:
        fournisseur_data = gestionnaire.get_fournisseur_by_id(selected_id)
        render_fournisseur_details(gestionnaire, fournisseur_data)

def render_fournisseurs_dashboard(gestionnaire):
    """Dashboard principal des fournisseurs"""
    st.markdown("### 📊 Vue d'Ensemble Fournisseurs")
    
    # Récupération des statistiques
    stats = gestionnaire.get_fournisseurs_statistics()
    
    if not stats:
        st.info("Aucune donnée fournisseur disponible.")
        if st.button("➕ Ajouter Premier Fournisseur", use_container_width=True):
            st.session_state.fournisseur_action = "create_fournisseur"
            st.rerun()
        return
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🏪 Total Fournisseurs", stats['total_fournisseurs'])
    with col2:
        st.metric("✅ Fournisseurs Actifs", stats['fournisseurs_actifs'])
    with col3:
        st.metric("⭐ Éval. Moyenne", f"{stats['evaluation_moyenne']}/10")
    with col4:
        st.metric("📦 Délai Moyen", f"{stats['delai_moyen']} jours")
    
    # Métriques financières
    col5, col6 = st.columns(2)
    with col5:
        montant_formate = f"{stats['montant_total_commandes']:,.0f} $ CAD"
        st.metric("💰 Volume Total Commandes", montant_formate)
    with col6:
        if stats['fournisseurs_actifs'] > 0:
            moyenne_par_fournisseur = stats['montant_total_commandes'] / stats['fournisseurs_actifs']
            st.metric("📊 Moy./Fournisseur", f"{moyenne_par_fournisseur:,.0f} $ CAD")
    
    st.markdown("---")
    
    # Graphiques
    if stats['par_categorie'] or stats['top_performers']:
        graph_col1, graph_col2 = st.columns(2)
        
        with graph_col1:
            # Répartition par catégorie
            if stats['par_categorie']:
                st.markdown("#### 🏷️ Fournisseurs par Catégorie")
                categories = list(stats['par_categorie'].keys())
                valeurs = list(stats['par_categorie'].values())
                
                fig_cat = px.pie(
                    values=valeurs, 
                    names=categories, 
                    title="Répartition par Catégorie"
                )
                fig_cat.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', 
                    paper_bgcolor='rgba(0,0,0,0)',
                    title_x=0.5
                )
                st.plotly_chart(fig_cat, use_container_width=True)
        
        with graph_col2:
            # Top performers
            if stats['top_performers']:
                st.markdown("#### 🏆 Top Fournisseurs")
                df_top = pd.DataFrame(stats['top_performers'])
                if not df_top.empty:
                    fig_top = px.bar(
                        df_top, 
                        x='nom', 
                        y='montant_total',
                        color='evaluation_qualite',
                        title="Top Fournisseurs (Volume & Qualité)",
                        color_continuous_scale='Viridis'
                    )
                    fig_top.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)', 
                        paper_bgcolor='rgba(0,0,0,0)',
                        title_x=0.5,
                        xaxis_title="Fournisseur",
                        yaxis_title="Montant Total ($)",
                        showlegend=False
                    )
                    st.plotly_chart(fig_top, use_container_width=True)
    
    # Actions rapides
    st.markdown("---")
    st.markdown("#### ⚡ Actions Rapides")
    
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    
    with action_col1:
        if st.button("➕ Nouveau Fournisseur", use_container_width=True):
            st.session_state.fournisseur_action = "create_fournisseur"
            st.rerun()
    
    with action_col2:
        if st.button("📊 Voir Performances", use_container_width=True):
            # Redirection vers l'onglet performances
            st.info("💡 Consultez l'onglet 'Performances' pour les analyses détaillées.")
    
    with action_col3:
        if st.button("🏷️ Gérer Catégories", use_container_width=True):
            st.info("💡 Consultez l'onglet 'Catégories' pour la gestion par catégories.")
    
    with action_col4:
        if st.button("🔄 Actualiser Stats", use_container_width=True):
            st.rerun()

def render_fournisseurs_liste(gestionnaire):
    """Liste et gestion des fournisseurs"""
    st.markdown("### 📋 Liste des Fournisseurs")
    
    # Bouton d'ajout
    col_add, _ = st.columns([1, 3])
    with col_add:
        if st.button("➕ Nouveau Fournisseur", use_container_width=True, key="create_fournisseur_btn"):
            st.session_state.fournisseur_action = "create_fournisseur"
            st.rerun()
    
    # Filtres
    with st.expander("🔍 Filtres et Recherche", expanded=False):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            categories = ['TOUS'] + gestionnaire.get_categories_disponibles()
            category_filter = st.selectbox(
                "Catégorie:", 
                categories,
                index=categories.index(st.session_state.fournisseur_filter_category) if st.session_state.fournisseur_filter_category in categories else 0,
                key="fournisseur_category_filter"
            )
            st.session_state.fournisseur_filter_category = category_filter
        
        with filter_col2:
            statut_filter = st.selectbox("Statut:", ["TOUS", "ACTIF", "INACTIF"], key="fournisseur_statut_filter")
        
        with filter_col3:
            recherche = st.text_input("🔍 Rechercher:", placeholder="Nom, code, secteur...", key="fournisseur_search")
    
    # Récupération et filtrage des données
    fournisseurs = gestionnaire.get_all_fournisseurs()
    
    if category_filter != 'TOUS':
        fournisseurs = [f for f in fournisseurs if f.get('categorie_produits', '').upper() == category_filter.upper()]
    
    if statut_filter == 'ACTIF':
        fournisseurs = [f for f in fournisseurs if f.get('est_actif')]
    elif statut_filter == 'INACTIF':
        fournisseurs = [f for f in fournisseurs if not f.get('est_actif')]
    
    if recherche:
        terme = recherche.lower()
        fournisseurs = [f for f in fournisseurs if
            terme in str(f.get('nom', '')).lower() or
            terme in str(f.get('code_fournisseur', '')).lower() or
            terme in str(f.get('secteur', '')).lower() or
            terme in str(f.get('categorie_produits', '')).lower()
        ]
    
    if not fournisseurs:
        st.info("Aucun fournisseur ne correspond aux critères de recherche.")
        return
    
    st.markdown(f"**{len(fournisseurs)} fournisseur(s) trouvé(s)**")
    
    # Tableau des fournisseurs
    df_data = []
    for f in fournisseurs:
        statut_display = "✅ ACTIF" if f.get('est_actif') else "❌ INACTIF"
        evaluation_display = f"⭐ {f.get('evaluation_qualite', 0)}/10"
        
        df_data.append({
            '🆔': f.get('id', ''),
            '🏪 Nom': f.get('nom', 'N/A'),
            '📋 Code': f.get('code_fournisseur', 'N/A'),
            '🏷️ Catégorie': f.get('categorie_produits', 'N/A'),
            '⭐ Évaluation': evaluation_display,
            '📦 Délai (j)': f.get('delai_livraison_moyen', 0),
            '💰 Total Commandes': f"{f.get('montant_total_commandes', 0):,.0f} $",
            '📊 Nb Commandes': f.get('nombre_commandes', 0),
            '🚦 Statut': statut_display
        })
    
    st.dataframe(pd.DataFrame(df_data), use_container_width=True)
    
    # Actions sur un fournisseur
    if fournisseurs:
        st.markdown("---")
        st.markdown("#### 🔧 Actions sur un Fournisseur")
        
        selected_fournisseur_id = st.selectbox(
            "Sélectionner un fournisseur:",
            options=[f.get('id') for f in fournisseurs],
            format_func=lambda fid: next((f.get('nom', 'N/A') for f in fournisseurs if f.get('id') == fid), ''),
            key="fournisseur_action_select"
        )
        
        if selected_fournisseur_id:
            action_col1, action_col2, action_col3, action_col4 = st.columns(4)
            
            with action_col1:
                if st.button("👁️ Voir Détails", use_container_width=True, key=f"view_fournisseur_{selected_fournisseur_id}"):
                    st.session_state.selected_fournisseur_id = selected_fournisseur_id
                    st.session_state.fournisseur_action = "view_fournisseur_details"
                    st.rerun()
            
            with action_col2:
                if st.button("✏️ Modifier", use_container_width=True, key=f"edit_fournisseur_{selected_fournisseur_id}"):
                    st.session_state.selected_fournisseur_id = selected_fournisseur_id
                    st.session_state.fournisseur_action = "edit_fournisseur"
                    st.rerun()
            
            with action_col3:
                if st.button("📊 Performance", use_container_width=True, key=f"perf_fournisseur_{selected_fournisseur_id}"):
                    st.session_state.selected_fournisseur_id = selected_fournisseur_id
                    st.info("💡 Consultez l'onglet 'Performances' pour voir les détails de ce fournisseur.")
            
            with action_col4:
                if st.button("🗑️ Désactiver", use_container_width=True, key=f"delete_fournisseur_{selected_fournisseur_id}"):
                    if st.warning("Êtes-vous sûr de vouloir désactiver ce fournisseur ?"):
                        if gestionnaire.delete_fournisseur(selected_fournisseur_id):
                            st.success("Fournisseur désactivé avec succès !")
                            st.rerun()

def render_fournisseurs_performance(gestionnaire):
    """Analyse des performances des fournisseurs"""
    st.markdown("### 📈 Analyse des Performances")
    
    fournisseurs = gestionnaire.get_all_fournisseurs()
    
    if not fournisseurs:
        st.info("Aucun fournisseur disponible pour l'analyse.")
        return
    
    # Sélection du fournisseur et période
    perf_col1, perf_col2 = st.columns(2)
    
    with perf_col1:
        selected_fournisseur_id = st.selectbox(
            "Fournisseur à analyser:",
            options=[f.get('id') for f in fournisseurs],
            format_func=lambda fid: next((f.get('nom', 'N/A') for f in fournisseurs if f.get('id') == fid), ''),
            key="performance_fournisseur_select"
        )
    
    with perf_col2:
        periode_jours = st.selectbox(
            "Période d'analyse:",
            options=[30, 90, 180, 365, 730],
            format_func=lambda d: f"{d} jours" if d < 365 else f"{d//365} an(s)",
            index=3,  # 365 jours par défaut
            key="performance_periode_select"
        )
    
    if selected_fournisseur_id:
        # Récupération des données de performance
        performance = gestionnaire.get_fournisseur_performance(selected_fournisseur_id, periode_jours)
        fournisseur_info = gestionnaire.get_fournisseur_by_id(selected_fournisseur_id)
        
        if not performance:
            st.warning("Aucune donnée de performance disponible pour cette période.")
            return
        
        # Affichage du nom du fournisseur
        st.markdown(f"#### 🏪 {fournisseur_info.get('nom', 'N/A')} - {periode_jours} derniers jours")
        
        # Métriques de performance
        perf_met_col1, perf_met_col2, perf_met_col3, perf_met_col4 = st.columns(4)
        
        with perf_met_col1:
            st.metric("📦 Total Commandes", performance.get('total_commandes', 0))
        with perf_met_col2:
            montant_total = performance.get('montant_total', 0) or 0
            st.metric("💰 Montant Total", f"{montant_total:,.0f} $")
        with perf_met_col3:
            montant_moyen = performance.get('montant_moyen', 0) or 0
            st.metric("📊 Commande Moyenne", f"{montant_moyen:,.0f} $")
        with perf_met_col4:
            taux_ponctualite = performance.get('taux_ponctualite', 0) or 0
            couleur_ponctualite = "normal" if taux_ponctualite >= 90 else "inverse" if taux_ponctualite >= 70 else "off"
            st.metric("⏰ Ponctualité", f"{taux_ponctualite:.1f}%", delta_color=couleur_ponctualite)
        
        # Détails supplémentaires
        if performance.get('total_livraisons', 0) > 0:
            st.markdown("---")
            st.markdown("#### 📊 Détails Livraisons")
            
            detail_col1, detail_col2, detail_col3 = st.columns(3)
            
            with detail_col1:
                st.metric("🚚 Total Livraisons", performance.get('total_livraisons', 0))
            with detail_col2:
                livraisons_temps = performance.get('livraisons_temps', 0)
                st.metric("✅ Livrées à Temps", livraisons_temps)
            with detail_col3:
                retard_moyen = performance.get('retard_moyen_jours', 0) or 0
                if retard_moyen > 0:
                    st.metric("⏱️ Retard Moyen", f"{retard_moyen:.1f} jours", delta_color="inverse")
                else:
                    st.metric("⏱️ Retard Moyen", "0 jour", delta_color="normal")
        
        # Évaluation et notes
        st.markdown("---")
        st.markdown("#### ⭐ Évaluation Qualité")
        
        eval_col1, eval_col2 = st.columns(2)
        
        with eval_col1:
            evaluation_actuelle = fournisseur_info.get('evaluation_qualite', 5)
            st.metric("Note Actuelle", f"{evaluation_actuelle}/10")
            
            # Barre de progression pour l'évaluation
            progress_value = evaluation_actuelle / 10
            st.progress(progress_value)
            
            if evaluation_actuelle >= 8:
                st.success("🏆 Excellent fournisseur")
            elif evaluation_actuelle >= 6:
                st.info("👍 Bon fournisseur")
            else:
                st.warning("⚠️ Fournisseur à surveiller")
        
        with eval_col2:
            if fournisseur_info.get('notes_evaluation'):
                st.markdown("**📝 Notes d'évaluation:**")
                st.markdown(f"_{fournisseur_info['notes_evaluation']}_")
            
            if fournisseur_info.get('certifications'):
                st.markdown("**🏅 Certifications:**")
                st.markdown(f"_{fournisseur_info['certifications']}_")
        
        # Recommandations automatiques
        st.markdown("---")
        st.markdown("#### 💡 Recommandations")
        
        recommendations = []
        
        if taux_ponctualite < 70:
            recommendations.append("🚨 Ponctualité faible - Renégocier les délais de livraison")
        elif taux_ponctualite < 90:
            recommendations.append("⚠️ Ponctualité moyenne - Suivre de près les prochaines livraisons")
        
        if evaluation_actuelle < 6:
            recommendations.append("📉 Note qualité faible - Prévoir une évaluation approfondie")
        
        if performance.get('total_commandes', 0) == 0:
            recommendations.append("📦 Aucune commande récente - Évaluer la pertinence du partenariat")
        
        if not recommendations:
            recommendations.append("✅ Performance satisfaisante - Continuer le partenariat")
        
        for rec in recommendations:
            st.markdown(f"• {rec}")

def render_fournisseurs_categories(gestionnaire):
    """Gestion par catégories de fournisseurs"""
    st.markdown("### 🏷️ Gestion par Catégories")
    
    categories = gestionnaire.get_categories_disponibles()
    
    if not categories:
        st.info("Aucune catégorie de fournisseurs définie.")
        st.markdown("💡 Les catégories sont créées automatiquement lors de l'ajout de fournisseurs.")
        return
    
    # Statistiques par catégorie
    cat_col1, cat_col2 = st.columns(2)
    
    with cat_col1:
        st.markdown("#### 📊 Répartition par Catégorie")
        
        cat_stats = {}
        for category in categories:
            fournisseurs_cat = gestionnaire.get_fournisseurs_by_category(category)
            cat_stats[category] = len(fournisseurs_cat)
        
        # Graphique en barres
        if cat_stats:
            fig_cat_bar = px.bar(
                x=list(cat_stats.keys()),
                y=list(cat_stats.values()),
                title="Nombre de Fournisseurs par Catégorie",
                labels={'x': 'Catégorie', 'y': 'Nombre de Fournisseurs'}
            )
            fig_cat_bar.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                title_x=0.5
            )
            st.plotly_chart(fig_cat_bar, use_container_width=True)
    
    with cat_col2:
        st.markdown("#### 🔍 Explorer par Catégorie")
        
        selected_category = st.selectbox(
            "Sélectionner une catégorie:",
            categories,
            key="category_explorer_select"
        )
        
        if selected_category:
            fournisseurs_cat = gestionnaire.get_fournisseurs_by_category(selected_category)
            
            st.markdown(f"**{len(fournisseurs_cat)} fournisseur(s) dans '{selected_category}'**")
            
            for fournisseur in fournisseurs_cat:
                with st.container():
                    st.markdown(f"""
                    <div style='border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin: 0.5rem 0; background-color: #f9f9f9;'>
                        <h5 style='margin: 0 0 0.5rem 0;'>🏪 {fournisseur.get('nom', 'N/A')}</h5>
                        <p style='margin: 0; color: #666;'>
                            <strong>Secteur:</strong> {fournisseur.get('secteur', 'N/A')} | 
                            <strong>Évaluation:</strong> ⭐ {fournisseur.get('evaluation_qualite', 0)}/10
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Liste détaillée des catégories
    st.markdown("---")
    st.markdown("#### 📋 Vue d'Ensemble des Catégories")
    
    categories_data = []
    for category in categories:
        fournisseurs_cat = gestionnaire.get_fournisseurs_by_category(category)
        
        if fournisseurs_cat:
            evaluations = [f.get('evaluation_qualite', 0) for f in fournisseurs_cat if f.get('evaluation_qualite')]
            eval_moyenne = sum(evaluations) / len(evaluations) if evaluations else 0
            
            delais = [f.get('delai_livraison_moyen', 0) for f in fournisseurs_cat if f.get('delai_livraison_moyen')]
            delai_moyen = sum(delais) / len(delais) if delais else 0
            
            categories_data.append({
                '🏷️ Catégorie': category,
                '🏪 Nb Fournisseurs': len(fournisseurs_cat),
                '⭐ Éval. Moyenne': f"{eval_moyenne:.1f}/10",
                '📦 Délai Moyen': f"{delai_moyen:.0f} jours",
                '✅ Actifs': len([f for f in fournisseurs_cat if f.get('est_actif')])
            })
    
    if categories_data:
        st.dataframe(pd.DataFrame(categories_data), use_container_width=True)

def render_fournisseur_form(gestionnaire, fournisseur_data=None):
    """Formulaire de création/modification d'un fournisseur"""
    is_edit = fournisseur_data is not None
    title = "✏️ Modifier Fournisseur" if is_edit else "➕ Nouveau Fournisseur"
    
    st.markdown(f"<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(f"### {title}")
    
    with st.form("fournisseur_form", clear_on_submit=not is_edit):
        # Sélection de l'entreprise (obligatoire)
        companies = st.session_state.erp_db.get_companies_by_type()
        
        if is_edit:
            current_company_id = fournisseur_data.get('company_id')
            company_options = [(c['id'], c['nom']) for c in companies]
            default_index = next((i for i, (cid, _) in enumerate(company_options) if cid == current_company_id), 0)
        else:
            company_options = [(c['id'], c['nom']) for c in companies]
            default_index = 0
        
        if not company_options:
            st.error("Aucune entreprise disponible. Créez d'abord une entreprise dans le module CRM.")
            st.stop()
        
        selected_company_id = st.selectbox(
            "Entreprise *:",
            options=[cid for cid, _ in company_options],
            format_func=lambda cid: next((nom for id_c, nom in company_options if id_c == cid), ""),
            index=default_index,
            help="Sélectionnez l'entreprise à associer comme fournisseur"
        )
        
        # Informations fournisseur
        col1, col2 = st.columns(2)
        
        with col1:
            code_fournisseur = st.text_input(
                "Code Fournisseur *:",
                value=fournisseur_data.get('code_fournisseur', '') if is_edit else '',
                help="Code unique pour identifier le fournisseur"
            )
            
            categorie_produits = st.text_input(
                "Catégorie de Produits *:",
                value=fournisseur_data.get('categorie_produits', '') if is_edit else '',
                help="Ex: Métallurgie, Électronique, Consommables..."
            )
            
            delai_livraison = st.number_input(
                "Délai de Livraison (jours):",
                min_value=1,
                max_value=365,
                value=fournisseur_data.get('delai_livraison_moyen', 14) if is_edit else 14,
                help="Délai moyen de livraison en jours"
            )
            
            evaluation_qualite = st.slider(
                "Évaluation Qualité:",
                min_value=1,
                max_value=10,
                value=fournisseur_data.get('evaluation_qualite', 5) if is_edit else 5,
                help="Note sur 10 pour la qualité du fournisseur"
            )
        
        with col2:
            conditions_paiement = st.text_input(
                "Conditions de Paiement:",
                value=fournisseur_data.get('conditions_paiement', '30 jours net') if is_edit else '30 jours net',
                help="Ex: 30 jours net, Comptant, 60 jours fin de mois..."
            )
            
            contact_commercial = st.text_input(
                "Contact Commercial:",
                value=fournisseur_data.get('contact_commercial', '') if is_edit else '',
                help="Nom du contact commercial principal"
            )
            
            contact_technique = st.text_input(
                "Contact Technique:",
                value=fournisseur_data.get('contact_technique', '') if is_edit else '',
                help="Nom du contact technique principal"
            )
            
            if is_edit:
                est_actif = st.checkbox(
                    "Fournisseur Actif",
                    value=fournisseur_data.get('est_actif', True),
                    help="Décochez pour désactiver le fournisseur"
                )
            else:
                est_actif = True
        
        # Champs texte longs
        certifications = st.text_area(
            "Certifications:",
            value=fournisseur_data.get('certifications', '') if is_edit else '',
            help="Liste des certifications du fournisseur (ISO, etc.)"
        )
        
        notes_evaluation = st.text_area(
            "Notes d'Évaluation:",
            value=fournisseur_data.get('notes_evaluation', '') if is_edit else '',
            help="Notes et commentaires sur le fournisseur"
        )
        
        # Boutons
        st.markdown("---")
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            submit_label = "💾 Sauvegarder" if is_edit else "➕ Créer Fournisseur"
            submitted = st.form_submit_button(submit_label, use_container_width=True)
        
        with btn_col2:
            cancelled = st.form_submit_button("❌ Annuler", use_container_width=True)
        
        # Traitement du formulaire
        if submitted:
            # Validation
            if not code_fournisseur or not categorie_produits:
                st.error("Le code fournisseur et la catégorie sont obligatoires.")
            else:
                # Préparation des données
                fournisseur_form_data = {
                    'code_fournisseur': code_fournisseur,
                    'categorie_produits': categorie_produits,
                    'delai_livraison_moyen': delai_livraison,
                    'conditions_paiement': conditions_paiement,
                    'evaluation_qualite': evaluation_qualite,
                    'contact_commercial': contact_commercial,
                    'contact_technique': contact_technique,
                    'certifications': certifications,
                    'notes_evaluation': notes_evaluation,
                    'est_actif': est_actif
                }
                
                # Création ou modification
                if is_edit:
                    success = gestionnaire.update_fournisseur(fournisseur_data['id'], fournisseur_form_data)
                    if success:
                        st.success("✅ Fournisseur modifié avec succès !")
                        st.session_state.fournisseur_action = None
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la modification.")
                else:
                    new_id = gestionnaire.create_fournisseur(selected_company_id, fournisseur_form_data)
                    if new_id:
                        st.success(f"✅ Fournisseur créé avec succès ! (ID: {new_id})")
                        st.session_state.fournisseur_action = None
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la création.")
        
        if cancelled:
            st.session_state.fournisseur_action = None
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

def render_fournisseur_details(gestionnaire, fournisseur_data):
    """Affichage détaillé d'un fournisseur"""
    if not fournisseur_data:
        st.error("Fournisseur non trouvé.")
        return
    
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(f"### 🏪 {fournisseur_data.get('nom', 'N/A')}")
    
    # Bouton fermer
    if st.button("✖️ Fermer", key="close_fournisseur_details"):
        st.session_state.fournisseur_action = None
        st.rerun()
    
    # Informations générales
    st.markdown("#### 📋 Informations Générales")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.markdown(f"""
        **🆔 ID Fournisseur:** {fournisseur_data.get('id', 'N/A')}
        
        **📋 Code:** {fournisseur_data.get('code_fournisseur', 'N/A')}
        
        **🏷️ Catégorie:** {fournisseur_data.get('categorie_produits', 'N/A')}
        
        **🏢 Secteur:** {fournisseur_data.get('secteur', 'N/A')}
        
        **🚦 Statut:** {'✅ ACTIF' if fournisseur_data.get('est_actif') else '❌ INACTIF'}
        """)
    
    with info_col2:
        st.markdown(f"""
        **⭐ Évaluation:** {fournisseur_data.get('evaluation_qualite', 0)}/10
        
        **📦 Délai Livraison:** {fournisseur_data.get('delai_livraison_moyen', 0)} jours
        
        **💳 Conditions Paiement:** {fournisseur_data.get('conditions_paiement', 'N/A')}
        
        **👨‍💼 Contact Commercial:** {fournisseur_data.get('contact_commercial', 'N/A')}
        
        **🔧 Contact Technique:** {fournisseur_data.get('contact_technique', 'N/A')}
        """)
    
    # Informations entreprise
    st.markdown("---")
    st.markdown("#### 🏢 Informations Entreprise")
    
    entreprise_col1, entreprise_col2 = st.columns(2)
    
    with entreprise_col1:
        st.markdown(f"""
        **🏢 Nom:** {fournisseur_data.get('nom', 'N/A')}
        
        **📍 Adresse:** {fournisseur_data.get('adresse', 'N/A')}
        """)
    
    with entreprise_col2:
        st.markdown(f"""
        **🌐 Site Web:** {fournisseur_data.get('site_web', 'N/A')}
        
        **📝 Notes Entreprise:** {fournisseur_data.get('company_notes', 'N/A')}
        """)
    
    # Certifications et évaluations
    if fournisseur_data.get('certifications') or fournisseur_data.get('notes_evaluation'):
        st.markdown("---")
        st.markdown("#### 🏅 Certifications et Évaluations")
        
        if fournisseur_data.get('certifications'):
            st.markdown("**🏅 Certifications:**")
            st.markdown(f"_{fournisseur_data['certifications']}_")
        
        if fournisseur_data.get('notes_evaluation'):
            st.markdown("**📝 Notes d'Évaluation:**")
            st.markdown(f"_{fournisseur_data['notes_evaluation']}_")
    
    # Performance rapide
    st.markdown("---")
    st.markdown("#### 📊 Performance (365 derniers jours)")
    
    performance = gestionnaire.get_fournisseur_performance(fournisseur_data['id'], 365)
    
    if performance:
        perf_col1, perf_col2, perf_col3 = st.columns(3)
        
        with perf_col1:
            st.metric("📦 Commandes", performance.get('total_commandes', 0))
        with perf_col2:
            montant = performance.get('montant_total', 0) or 0
            st.metric("💰 Montant Total", f"{montant:,.0f} $")
        with perf_col3:
            ponctualite = performance.get('taux_ponctualite', 0) or 0
            st.metric("⏰ Ponctualité", f"{ponctualite:.1f}%")
    else:
        st.info("Aucune donnée de performance disponible.")
    
    # Actions rapides
    st.markdown("---")
    st.markdown("#### ⚡ Actions Rapides")
    
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("✏️ Modifier", use_container_width=True, key="edit_from_details"):
            st.session_state.fournisseur_action = "edit_fournisseur"
            st.rerun()
    
    with action_col2:
        if st.button("📊 Voir Performance", use_container_width=True, key="perf_from_details"):
            st.info("💡 Consultez l'onglet 'Performances' pour l'analyse complète.")
    
    with action_col3:
        if st.button("🛒 Créer Bon d'Achat", use_container_width=True, key="create_ba_from_details"):
            # Redirection vers le module formulaires avec pré-sélection
            st.session_state.form_action = "create_bon_achat"
            st.session_state.formulaire_company_preselect = fournisseur_data.get('company_id')
            st.session_state.page_redirect = "formulaires_page"
            st.info("🔄 Redirection vers le module Formulaires...")
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)
