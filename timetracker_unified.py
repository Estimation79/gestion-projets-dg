# timetracker_unified.py - Système de Punch Simple pour ERP Production DG Inc.
# VERSION SIMPLIFIÉE - Remplace l'ancien système complexe
# Utilise directement erp_database.py pour un punch simple et efficace

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
import logging
import json

logger = logging.getLogger(__name__)

class TimeTrackerUnified:
    """
    Système de punch simple et efficace
    Remplace l'ancien TimeTrackerUnified complexe
    Interface unifiée pour pointage employés sur projets
    """
    
    def __init__(self, db):
        self.db = db
        logger.info("TimeTracker Unifié Simple initialisé")
    
    # =========================================================================
    # MÉTHODES CORE DE POINTAGE
    # =========================================================================
    
    def punch_in(self, employee_id: int, project_id: int, notes: str = "") -> Optional[int]:
        """Commence un pointage pour un employé sur un projet"""
        try:
            # Vérifier qu'il n'y a pas déjà un pointage actif
            active_punch = self.get_active_punch(employee_id)
            if active_punch:
                return None  # Déjà pointé
            
            # Créer l'entrée de pointage
            query = '''
                INSERT INTO time_entries 
                (employee_id, project_id, punch_in, notes)
                VALUES (?, ?, ?, ?)
            '''
            
            entry_id = self.db.execute_insert(query, (
                employee_id,
                project_id,
                datetime.now().isoformat(),
                notes
            ))
            
            logger.info(f"Punch IN créé: entry_id={entry_id}, employee={employee_id}, project={project_id}")
            return entry_id
            
        except Exception as e:
            logger.error(f"Erreur punch in: {e}")
            return None
    
    def punch_out(self, employee_id: int, notes: str = "") -> bool:
        """Termine le pointage actif d'un employé"""
        try:
            # Récupérer le pointage actif
            active_punch = self.get_active_punch(employee_id)
            if not active_punch:
                return False  # Pas de pointage actif
            
            entry_id = active_punch['id']
            punch_in_time = datetime.fromisoformat(active_punch['punch_in'])
            punch_out_time = datetime.now()
            
            # Calculer les heures et coûts
            total_seconds = (punch_out_time - punch_in_time).total_seconds()
            total_hours = total_seconds / 3600
            
            # Récupérer le taux horaire de l'employé
            hourly_rate = self.get_employee_hourly_rate(employee_id)
            total_cost = total_hours * hourly_rate
            
            # Mettre à jour l'entrée
            query = '''
                UPDATE time_entries 
                SET punch_out = ?, total_hours = ?, hourly_rate = ?, total_cost = ?, notes = ?
                WHERE id = ?
            '''
            
            affected = self.db.execute_update(query, (
                punch_out_time.isoformat(),
                total_hours,
                hourly_rate,
                total_cost,
                notes or active_punch.get('notes', ''),
                entry_id
            ))
            
            logger.info(f"Punch OUT terminé: entry_id={entry_id}, heures={total_hours:.2f}, coût={total_cost:.2f}$")
            return affected > 0
            
        except Exception as e:
            logger.error(f"Erreur punch out: {e}")
            return False
    
    def get_active_punch(self, employee_id: int) -> Optional[Dict]:
        """Récupère le pointage actif d'un employé"""
        try:
            query = '''
                SELECT te.*, p.nom_projet, e.prenom || ' ' || e.nom as employee_name
                FROM time_entries te
                LEFT JOIN projects p ON te.project_id = p.id
                LEFT JOIN employees e ON te.employee_id = e.id
                WHERE te.employee_id = ? AND te.punch_out IS NULL
                ORDER BY te.punch_in DESC
                LIMIT 1
            '''
            result = self.db.execute_query(query, (employee_id,))
            return dict(result[0]) if result else None
            
        except Exception as e:
            logger.error(f"Erreur récupération punch actif: {e}")
            return None
    
    def get_employee_hourly_rate(self, employee_id: int) -> float:
        """Récupère le taux horaire d'un employé"""
        try:
            result = self.db.execute_query(
                "SELECT salaire FROM employees WHERE id = ?", 
                (employee_id,)
            )
            if result and result[0]['salaire']:
                # Convertir salaire annuel en taux horaire (2080h/an)
                return result[0]['salaire'] / 2080
            return 25.0  # Taux par défaut
            
        except Exception:
            return 25.0
    
    # =========================================================================
    # MÉTHODES DE CONSULTATION
    # =========================================================================
    
    def get_punch_history(self, employee_id: int = None, days: int = 7) -> List[Dict]:
        """Récupère l'historique des pointages"""
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            query = '''
                SELECT te.*, 
                       p.nom_projet, 
                       e.prenom || ' ' || e.nom as employee_name,
                       e.poste as employee_poste,
                       DATE(te.punch_in) as date_travail
                FROM time_entries te
                LEFT JOIN projects p ON te.project_id = p.id
                LEFT JOIN employees e ON te.employee_id = e.id
                WHERE DATE(te.punch_in) >= ?
            '''
            params = [start_date]
            
            if employee_id:
                query += " AND te.employee_id = ?"
                params.append(employee_id)
            
            query += " ORDER BY te.punch_in DESC"
            
            rows = self.db.execute_query(query, tuple(params))
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur historique punch: {e}")
            return []
    
    def get_daily_summary(self, target_date: date = None) -> Dict:
        """Résumé des pointages pour une journée"""
        try:
            if not target_date:
                target_date = date.today()
            
            date_str = target_date.strftime('%Y-%m-%d')
            
            query = '''
                SELECT 
                    COUNT(*) as total_punches,
                    COUNT(CASE WHEN punch_out IS NOT NULL THEN 1 END) as completed_punches,
                    COUNT(CASE WHEN punch_out IS NULL THEN 1 END) as active_punches,
                    COUNT(DISTINCT employee_id) as unique_employees,
                    COUNT(DISTINCT project_id) as unique_projects,
                    COALESCE(SUM(total_hours), 0) as total_hours,
                    COALESCE(SUM(total_cost), 0) as total_revenue
                FROM time_entries
                WHERE DATE(punch_in) = ?
            '''
            
            result = self.db.execute_query(query, (date_str,))
            return dict(result[0]) if result else {}
            
        except Exception as e:
            logger.error(f"Erreur résumé quotidien: {e}")
            return {}
    
    def get_employee_statistics(self, employee_id: int, days: int = 30) -> Dict:
        """Statistiques d'un employé"""
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            query = '''
                SELECT 
                    COUNT(*) as total_sessions,
                    COUNT(DISTINCT project_id) as unique_projects,
                    COALESCE(SUM(total_hours), 0) as total_hours,
                    COALESCE(SUM(total_cost), 0) as total_revenue,
                    COALESCE(AVG(total_hours), 0) as avg_session_hours,
                    COALESCE(AVG(hourly_rate), 0) as avg_hourly_rate
                FROM time_entries
                WHERE employee_id = ? 
                AND DATE(punch_in) >= ?
                AND punch_out IS NOT NULL
            '''
            
            result = self.db.execute_query(query, (employee_id, start_date))
            stats = dict(result[0]) if result else {}
            
            # Ajouter le nom de l'employé
            emp_result = self.db.execute_query(
                "SELECT prenom || ' ' || nom as name, poste FROM employees WHERE id = ?",
                (employee_id,)
            )
            if emp_result:
                stats['employee_name'] = emp_result[0]['name']
                stats['employee_poste'] = emp_result[0]['poste']
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur stats employé: {e}")
            return {}
    
    def get_project_time_summary(self, project_id: int) -> Dict:
        """Résumé des heures sur un projet"""
        try:
            query = '''
                SELECT 
                    COUNT(*) as total_sessions,
                    COUNT(DISTINCT employee_id) as unique_employees,
                    COALESCE(SUM(total_hours), 0) as total_hours,
                    COALESCE(SUM(total_cost), 0) as total_cost,
                    MIN(punch_in) as first_punch,
                    MAX(punch_out) as last_punch
                FROM time_entries
                WHERE project_id = ? AND punch_out IS NOT NULL
            '''
            
            result = self.db.execute_query(query, (project_id,))
            return dict(result[0]) if result else {}
            
        except Exception as e:
            logger.error(f"Erreur résumé projet: {e}")
            return {}
    
    # =========================================================================
    # MÉTHODES DE GESTION DES EMPLOYÉS
    # =========================================================================
    
    def get_all_employees(self) -> List[Dict]:
        """Récupère tous les employés actifs"""
        try:
            query = '''
                SELECT id, prenom, nom, poste, departement, statut,
                       prenom || ' ' || nom as display_name
                FROM employees
                WHERE statut = 'ACTIF'
                ORDER BY prenom, nom
            '''
            rows = self.db.execute_query(query)
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur récupération employés: {e}")
            return []
    
    def get_all_projects(self) -> List[Dict]:
        """Récupère tous les projets actifs"""
        try:
            query = '''
                SELECT id, nom_projet, client_nom_cache, statut, priorite
                FROM projects
                WHERE statut NOT IN ('TERMINÉ', 'ANNULÉ')
                ORDER BY priorite DESC, nom_projet
            '''
            rows = self.db.execute_query(query)
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur récupération projets: {e}")
            return []
    
    def get_active_employees(self) -> List[Dict]:
        """Récupère les employés avec pointage actif"""
        try:
            query = '''
                SELECT DISTINCT e.id, e.prenom || ' ' || e.nom as name, 
                       e.poste, p.nom_projet, te.punch_in,
                       ROUND((JULIANDAY('now') - JULIANDAY(te.punch_in)) * 24, 2) as hours_worked
                FROM time_entries te
                JOIN employees e ON te.employee_id = e.id
                LEFT JOIN projects p ON te.project_id = p.id
                WHERE te.punch_out IS NULL
                ORDER BY te.punch_in
            '''
            rows = self.db.execute_query(query)
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur employés actifs: {e}")
            return []
    
    # =========================================================================
    # MÉTHODES STATISTIQUES COMPATIBLES
    # =========================================================================
    
    def get_timetracker_statistics_unified(self) -> Dict:
        """Statistiques générales pour compatibilité avec app.py"""
        try:
            # Stats générales
            general_stats = self.db.execute_query('''
                SELECT 
                    COUNT(DISTINCT employee_id) as total_employees,
                    COUNT(CASE WHEN punch_out IS NULL THEN 1 END) as active_entries,
                    COUNT(*) as total_entries
                FROM time_entries
            ''')
            
            stats = dict(general_stats[0]) if general_stats else {}
            
            # Stats du jour
            today = date.today().strftime('%Y-%m-%d')
            daily_stats = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total_entries_today,
                    COALESCE(SUM(total_hours), 0) as total_hours_today,
                    COALESCE(SUM(total_cost), 0) as total_revenue_today
                FROM time_entries
                WHERE DATE(punch_in) = ? AND punch_out IS NOT NULL
            ''', (today,))
            
            if daily_stats:
                stats.update(dict(daily_stats[0]))
            
            # Compteurs BT (compatibilité - pas utilisé dans version simple)
            stats['active_entries_bt'] = 0
            stats['bt_entries_today'] = 0
            stats['bt_revenue_today'] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur stats unifiées: {e}")
            return {}
    
    def get_work_centers_statistics(self) -> Dict:
        """Statistiques postes de travail (basique pour compatibilité)"""
        try:
            result = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total_postes,
                    COUNT(CASE WHEN statut = 'ACTIF' THEN 1 END) as postes_actifs,
                    COUNT(CASE WHEN categorie = 'ROBOTIQUE' THEN 1 END) as postes_robotises,
                    COUNT(CASE WHEN categorie = 'CNC' THEN 1 END) as postes_cnc
                FROM work_centers
            ''')
            
            stats = dict(result[0]) if result else {}
            
            # Par département
            dept_result = self.db.execute_query('''
                SELECT departement, COUNT(*) as count
                FROM work_centers
                WHERE statut = 'ACTIF'
                GROUP BY departement
            ''')
            
            stats['par_departement'] = {row['departement']: row['count'] for row in dept_result}
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur stats postes: {e}")
            return {}

# =========================================================================
# INTERFACE STREAMLIT PRINCIPALE - EMPLOYÉS SEULEMENT
# =========================================================================

def show_timetracker_unified_interface():
    """Interface principale du TimeTracker unifié simplifié - VERSION EMPLOYÉS"""
    
    if 'timetracker_unified' not in st.session_state:
        st.error("❌ TimeTracker non initialisé")
        return
    
    tt = st.session_state.timetracker_unified
    
    st.markdown("### ⏱️ TimeTracker Simple - Pointage Employés")
    
    # Onglets principaux - SUPPRIMÉ ADMINISTRATION
    tab_punch, tab_history, tab_stats = st.tabs([
        "🕐 Pointage", "📊 Historique", "📈 Statistiques"
    ])
    
    with tab_punch:
        show_punch_interface(tt)
    
    with tab_history:
        show_history_interface(tt)
    
    with tab_stats:
        show_statistics_interface(tt)

def show_punch_interface(tt):
    """Interface de pointage simple"""
    
    st.markdown("#### 🕐 Pointage Employés")
    
    # Section employés actifs
    active_employees = tt.get_active_employees()
    if active_employees:
        st.markdown("##### 🟢 Employés Pointés Actuellement")
        
        for emp in active_employees:
            col1, col2, col3, col4 = st.columns([3, 3, 2, 2])
            
            with col1:
                st.write(f"**{emp['name']}**")
                st.caption(emp['poste'])
            
            with col2:
                st.write(f"📋 {emp['nom_projet'] or 'N/A'}")
                st.caption(f"Depuis: {emp['punch_in'][:16]}")
            
            with col3:
                st.metric("Heures", f"{emp['hours_worked']:.1f}h")
            
            with col4:
                if st.button("🔴 Pointer Sortie", key=f"out_{emp['id']}", use_container_width=True):
                    notes = st.text_input(f"Notes sortie {emp['name']}:", key=f"notes_out_{emp['id']}")
                    if tt.punch_out(emp['id'], notes):
                        st.success(f"✅ {emp['name']} pointé sortie !")
                        st.rerun()
                    else:
                        st.error("❌ Erreur pointage sortie")
        
        st.markdown("---")
    
    # Section nouveau pointage
    st.markdown("##### ➕ Nouveau Pointage")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Sélection employé
        employees = tt.get_all_employees()
        if not employees:
            st.warning("Aucun employé trouvé")
            return
        
        employee_options = {emp['id']: f"{emp['display_name']} ({emp['poste']})" for emp in employees}
        selected_employee_id = st.selectbox(
            "👤 Sélectionner Employé:",
            options=list(employee_options.keys()),
            format_func=lambda x: employee_options[x],
            key="punch_employee_select"
        )
    
    with col2:
        # Sélection projet
        projects = tt.get_all_projects()
        if not projects:
            st.warning("Aucun projet actif trouvé")
            return
        
        project_options = {proj['id']: f"#{proj['id']} - {proj['nom_projet']} ({proj['statut']})" for proj in projects}
        selected_project_id = st.selectbox(
            "📋 Sélectionner Projet:",
            options=list(project_options.keys()),
            format_func=lambda x: project_options[x],
            key="punch_project_select"
        )
    
    # Notes et action
    notes = st.text_input("📝 Notes (optionnel):", key="punch_notes")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("🟢 Pointer Entrée", use_container_width=True, type="primary"):
            # Vérifier si l'employé est déjà pointé
            active_punch = tt.get_active_punch(selected_employee_id)
            if active_punch:
                st.error(f"❌ {employee_options[selected_employee_id]} est déjà pointé sur: {active_punch.get('nom_projet', 'Projet inconnu')}")
            else:
                entry_id = tt.punch_in(selected_employee_id, selected_project_id, notes)
                if entry_id:
                    st.success(f"✅ Pointage démarré ! ID: {entry_id}")
                    st.rerun()
                else:
                    st.error("❌ Erreur lors du pointage")
    
    with col_btn2:
        if st.button("🔴 Pointer Sortie Employé", use_container_width=True):
            active_punch = tt.get_active_punch(selected_employee_id)
            if not active_punch:
                st.error(f"❌ {employee_options[selected_employee_id]} n'est pas pointé")
            else:
                if tt.punch_out(selected_employee_id, notes):
                    st.success("✅ Pointage terminé !")
                    st.rerun()
                else:
                    st.error("❌ Erreur pointage sortie")

def show_history_interface(tt):
    """Interface d'historique des pointages"""
    
    st.markdown("#### 📊 Historique des Pointages")
    
    # Filtres
    col1, col2, col3 = st.columns(3)
    
    with col1:
        days_filter = st.selectbox("📅 Période:", [7, 14, 30, 90], index=1)
    
    with col2:
        employees = tt.get_all_employees()
        employee_filter = st.selectbox(
            "👤 Employé:",
            options=[None] + [emp['id'] for emp in employees],
            format_func=lambda x: "Tous" if x is None else next((emp['display_name'] for emp in employees if emp['id'] == x), str(x))
        )
    
    with col3:
        show_active_only = st.checkbox("🟢 Pointages actifs seulement")
    
    # Récupérer historique
    history = tt.get_punch_history(employee_filter, days_filter)
    
    if show_active_only:
        history = [h for h in history if h['punch_out'] is None]
    
    if not history:
        st.info("Aucun pointage trouvé pour les critères sélectionnés")
        return
    
    # Résumé
    st.markdown("##### 📈 Résumé")
    
    total_sessions = len(history)
    completed_sessions = len([h for h in history if h['punch_out'] is not None])
    total_hours = sum(h['total_hours'] or 0 for h in history)
    total_revenue = sum(h['total_cost'] or 0 for h in history)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sessions", total_sessions)
    col2.metric("Terminées", completed_sessions)
    col3.metric("Heures Total", f"{total_hours:.1f}h")
    col4.metric("Revenus", f"{total_revenue:,.0f}$")
    
    # Tableau détaillé
    st.markdown("##### 📋 Détail des Pointages")
    
    df_data = []
    for h in history:
        # Calcul durée en cours pour pointages actifs
        if h['punch_out'] is None and h['punch_in']:
            try:
                start_time = datetime.fromisoformat(h['punch_in'])
                current_duration = (datetime.now() - start_time).total_seconds() / 3600
                status = f"🟢 En cours ({current_duration:.1f}h)"
                hours_display = f"{current_duration:.1f}h"
                cost_display = "En cours"
            except:
                status = "🟢 En cours"
                hours_display = "En cours"
                cost_display = "En cours"
        else:
            status = "✅ Terminé"
            hours_display = f"{h['total_hours']:.1f}h" if h['total_hours'] else "0h"
            cost_display = f"{h['total_cost']:,.0f}$" if h['total_cost'] else "0$"
        
        df_data.append({
            'ID': h['id'],
            'Date': h['date_travail'],
            'Employé': h['employee_name'],
            'Poste': h['employee_poste'],
            'Projet': h['nom_projet'] or 'N/A',
            'Début': h['punch_in'][-8:-3] if h['punch_in'] else 'N/A',  # HH:MM
            'Fin': h['punch_out'][-8:-3] if h['punch_out'] else 'En cours',
            'Durée': hours_display,
            'Coût': cost_display,
            'Statut': status,
            'Notes': h['notes'] or ''
        })
    
    if df_data:
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Bouton export
        if st.button("📥 Exporter CSV", use_container_width=True):
            csv = df.to_csv(index=False)
            st.download_button(
                label="💾 Télécharger CSV",
                data=csv,
                file_name=f"pointages_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

def show_statistics_interface(tt):
    """Interface de statistiques"""
    
    st.markdown("#### 📈 Statistiques TimeTracker")
    
    # Résumé du jour
    daily_summary = tt.get_daily_summary()
    
    st.markdown("##### 📅 Aujourd'hui")
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Pointages", daily_summary.get('total_punches', 0))
    col2.metric("Employés", daily_summary.get('unique_employees', 0))
    col3.metric("Heures", f"{daily_summary.get('total_hours', 0):.1f}h")
    col4.metric("Revenus", f"{daily_summary.get('total_revenue', 0):,.0f}$")
    
    # Graphiques
    st.markdown("##### 📊 Analyses")
    
    # Historique 30 derniers jours
    history_30d = tt.get_punch_history(days=30)
    
    if history_30d:
        # Préparation données pour graphiques
        df_history = pd.DataFrame(history_30d)
        df_history['date'] = pd.to_datetime(df_history['date_travail'])
        
        # Graphique heures par jour
        daily_hours = df_history.groupby('date_travail')['total_hours'].sum().reset_index()
        daily_hours = daily_hours[daily_hours['total_hours'].notna()]
        
        if not daily_hours.empty:
            fig_daily = px.bar(
                daily_hours, 
                x='date_travail', 
                y='total_hours',
                title="Heures par Jour (30 derniers jours)",
                labels={'total_hours': 'Heures', 'date_travail': 'Date'}
            )
            fig_daily.update_layout(height=400)
            st.plotly_chart(fig_daily, use_container_width=True)
        
        # Top employés
        emp_hours = df_history.groupby('employee_name')['total_hours'].sum().reset_index()
        emp_hours = emp_hours[emp_hours['total_hours'].notna()].sort_values('total_hours', ascending=False).head(10)
        
        if not emp_hours.empty:
            fig_emp = px.bar(
                emp_hours,
                x='total_hours',
                y='employee_name',
                orientation='h',
                title="Top 10 Employés par Heures (30j)",
                labels={'total_hours': 'Heures', 'employee_name': 'Employé'}
            )
            fig_emp.update_layout(height=400)
            st.plotly_chart(fig_emp, use_container_width=True)
        
        # Projets populaires
        proj_hours = df_history.groupby('nom_projet')['total_hours'].sum().reset_index()
        proj_hours = proj_hours[proj_hours['total_hours'].notna()].sort_values('total_hours', ascending=False).head(10)
        
        if not proj_hours.empty:
            fig_proj = px.pie(
                proj_hours,
                values='total_hours',
                names='nom_projet',
                title="Répartition Heures par Projet (30j)"
            )
            st.plotly_chart(fig_proj, use_container_width=True)
    
    # Stats employé individuel
    st.markdown("##### 👤 Statistiques Employé")
    
    employees = tt.get_all_employees()
    if employees:
        employee_options = {emp['id']: emp['display_name'] for emp in employees}
        selected_emp = st.selectbox(
            "Sélectionner employé:",
            options=list(employee_options.keys()),
            format_func=lambda x: employee_options[x]
        )
        
        if selected_emp:
            emp_stats = tt.get_employee_statistics(selected_emp, 30)
            
            if emp_stats:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Sessions", emp_stats.get('total_sessions', 0))
                col2.metric("Projets", emp_stats.get('unique_projects', 0))
                col3.metric("Heures Total", f"{emp_stats.get('total_hours', 0):.1f}h")
                col4.metric("Revenus", f"{emp_stats.get('total_revenue', 0):,.0f}$")
                
                if emp_stats.get('total_sessions', 0) > 0:
                    st.metric("Moyenne/Session", f"{emp_stats.get('avg_session_hours', 0):.1f}h")
                    st.metric("Taux Horaire Moyen", f"{emp_stats.get('avg_hourly_rate', 0):.0f}$/h")

# =========================================================================
# FONCTION PRINCIPALE D'AFFICHAGE (Compatibilité app.py)
# =========================================================================

def show_timetracker_unified_interface_main():
    """Point d'entrée principal pour l'interface (appelé depuis app.py)"""
    show_timetracker_unified_interface()

# =========================================================================
# FONCTIONS DE COMPATIBILITÉ AVEC L'ANCIEN SYSTÈME
# =========================================================================

def get_timetracker_redirect_to_bt():
    """Fonction de compatibilité - pas utilisée dans version simple"""
    return False

def handle_timetracker_redirect():
    """Fonction de compatibilité - pas utilisée dans version simple"""
    return False
