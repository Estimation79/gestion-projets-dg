# --- START OF FILE timetracker.py - VERSION FINALE ERP UNIFIÉE ---

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, time
import hashlib
import json
from typing import Dict, List, Optional, Tuple
import logging
from erp_database import ERPDatabase

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimeTrackerERP:
    """
    TimeTracker intégré à l'ERP Production DG Inc.
    Utilise la base SQLite unifiée via ERPDatabase
    """
    
    def __init__(self, erp_db: ERPDatabase):
        self.db = erp_db
        logger.info("TimeTracker ERP initialisé avec base SQLite unifiée")
    
    def get_all_employees(self) -> List[Dict]:
        """Récupère tous les employés actifs depuis la base ERP"""
        try:
            rows = self.db.execute_query('''
                SELECT id, prenom, nom, email, telephone, poste, departement, statut, salaire
                FROM employees 
                WHERE statut = 'ACTIF' 
                ORDER BY prenom, nom
            ''')
            
            employees = []
            for row in rows:
                emp = dict(row)
                emp['name'] = f"{emp['prenom']} {emp['nom']}"
                emp['employee_code'] = f"EMP{emp['id']:03d}"
                employees.append(emp)
            
            return employees
        except Exception as e:
            logger.error(f"Erreur récupération employés: {e}")
            return []
    
    def get_employee_by_id(self, employee_id: int) -> Optional[Dict]:
        """Récupère un employé par son ID depuis la base ERP"""
        try:
            rows = self.db.execute_query('''
                SELECT id, prenom, nom, email, telephone, poste, departement, statut, salaire
                FROM employees 
                WHERE id = ? AND statut = 'ACTIF'
            ''', (employee_id,))
            
            if rows:
                emp = dict(rows[0])
                emp['name'] = f"{emp['prenom']} {emp['nom']}"
                emp['employee_code'] = f"EMP{emp['id']:03d}"
                return emp
            return None
        except Exception as e:
            logger.error(f"Erreur récupération employé {employee_id}: {e}")
            return None
    
    def get_active_projects(self) -> List[Dict]:
        """Récupère tous les projets actifs depuis la base ERP"""
        try:
            rows = self.db.execute_query('''
                SELECT p.id, p.nom_projet, p.client_nom_cache, p.statut, p.prix_estime,
                       c.nom as company_name
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE p.statut IN ('À FAIRE', 'EN COURS') 
                ORDER BY p.nom_projet
            ''')
            
            projects = []
            for row in rows:
                proj = dict(row)
                proj['project_name'] = proj['nom_projet']
                proj['client_name'] = proj['client_nom_cache'] or proj.get('company_name', 'Client Inconnu')
                proj['project_code'] = f"PROJ{proj['id']:04d}"
                projects.append(proj)
            
            return projects
        except Exception as e:
            logger.error(f"Erreur récupération projets: {e}")
            return []
    
    def get_project_operations(self, project_id: int) -> List[Dict]:
        """Récupère les opérations d'un projet (utilisées comme tâches)"""
        try:
            rows = self.db.execute_query('''
                SELECT o.id, o.description, o.temps_estime, o.poste_travail,
                       wc.nom as work_center_name, wc.cout_horaire
                FROM operations o
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE o.project_id = ? 
                ORDER BY o.sequence_number, o.description
            ''', (project_id,))
            
            operations = []
            for row in rows:
                op = dict(row)
                op['task_name'] = op['description'] or f"Opération {op['id']}"
                op['task_code'] = f"OP{op['id']:03d}"
                op['hourly_rate'] = op['cout_horaire'] or 95.0  # Taux par défaut
                op['estimated_hours'] = op['temps_estime'] or 0
                operations.append(op)
            
            return operations
        except Exception as e:
            logger.error(f"Erreur récupération opérations projet {project_id}: {e}")
            return []
    
    def get_employee_current_entry(self, employee_id: int) -> Optional[Dict]:
        """Vérifie si l'employé a une entrée en cours (pas de punch_out)"""
        try:
            rows = self.db.execute_query('''
                SELECT te.*, p.nom_projet as project_name, o.description as task_name
                FROM time_entries te
                JOIN projects p ON te.project_id = p.id
                LEFT JOIN operations o ON te.operation_id = o.id
                WHERE te.employee_id = ? AND te.punch_out IS NULL
                ORDER BY te.punch_in DESC
                LIMIT 1
            ''', (employee_id,))
            
            if rows:
                entry = dict(rows[0])
                entry['task_name'] = entry['task_name'] or 'Tâche générale'
                return entry
            return None
        except Exception as e:
            logger.error(f"Erreur récupération entrée courante employé {employee_id}: {e}")
            return None
    
    def punch_in(self, employee_id: int, project_id: int, operation_id: int = None, notes: str = "") -> int:
        """Enregistre un punch in dans la base ERP unifiée"""
        try:
            # Vérifier s'il n'y a pas déjà un punch in actif
            current_entry = self.get_employee_current_entry(employee_id)
            if current_entry:
                raise ValueError("L'employé a déjà un pointage actif")
            
            # Obtenir le taux horaire de l'opération ou utiliser le taux par défaut
            hourly_rate = 95.0  # Taux par défaut
            if operation_id:
                rate_rows = self.db.execute_query('''
                    SELECT wc.cout_horaire 
                    FROM operations o
                    JOIN work_centers wc ON o.work_center_id = wc.id
                    WHERE o.id = ?
                ''', (operation_id,))
                if rate_rows:
                    hourly_rate = rate_rows[0]['cout_horaire']
            
            # Créer l'entrée de temps
            entry_id = self.db.execute_insert('''
                INSERT INTO time_entries 
                (employee_id, project_id, operation_id, punch_in, notes, hourly_rate)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (employee_id, project_id, operation_id, datetime.now().isoformat(), notes, hourly_rate))
            
            logger.info(f"Punch in créé - Employé: {employee_id}, Projet: {project_id}, Entry: {entry_id}")
            return entry_id
            
        except Exception as e:
            logger.error(f"Erreur punch in: {e}")
            raise
    
    def punch_out(self, employee_id: int, notes: str = "") -> bool:
        """Enregistre un punch out dans la base ERP unifiée"""
        try:
            # Trouver l'entrée active
            current_entry = self.get_employee_current_entry(employee_id)
            if not current_entry:
                raise ValueError("Aucun pointage actif trouvé")
            
            # Calculer les heures et le coût
            punch_in_time = datetime.fromisoformat(current_entry['punch_in'])
            punch_out_time = datetime.now()
            total_hours = (punch_out_time - punch_in_time).total_seconds() / 3600
            total_cost = total_hours * current_entry['hourly_rate']
            
            # Mettre à jour l'entrée
            self.db.execute_update('''
                UPDATE time_entries 
                SET punch_out = ?, total_hours = ?, total_cost = ?, notes = ?
                WHERE id = ?
            ''', (punch_out_time.isoformat(), total_hours, total_cost, notes, current_entry['id']))
            
            logger.info(f"Punch out complété - Entry: {current_entry['id']}, Heures: {total_hours:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur punch out: {e}")
            raise
    
    def get_employee_time_entries(self, employee_id: int, limit: int = 50) -> List[Dict]:
        """Récupère les dernières entrées d'un employé"""
        try:
            rows = self.db.execute_query('''
                SELECT te.*, p.nom_projet as project_name, o.description as task_name
                FROM time_entries te
                JOIN projects p ON te.project_id = p.id
                LEFT JOIN operations o ON te.operation_id = o.id
                WHERE te.employee_id = ?
                ORDER BY te.punch_in DESC
                LIMIT ?
            ''', (employee_id, limit))
            
            entries = []
            for row in rows:
                entry = dict(row)
                entry['task_name'] = entry['task_name'] or 'Tâche générale'
                entries.append(entry)
            
            return entries
        except Exception as e:
            logger.error(f"Erreur récupération historique employé {employee_id}: {e}")
            return []
    
    def get_daily_summary(self, date_str: str = None) -> List[Dict]:
        """Récupère le résumé quotidien des pointages"""
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        try:
            rows = self.db.execute_query('''
                SELECT 
                    e.prenom || ' ' || e.nom as employee_name,
                    p.nom_projet as project_name,
                    COALESCE(o.description, 'Tâche générale') as task_name,
                    COALESCE(SUM(te.total_hours), 0.0) as total_hours,
                    COALESCE(SUM(te.total_cost), 0.0) as total_cost,
                    COUNT(te.id) as entries_count
                FROM time_entries te
                JOIN employees e ON te.employee_id = e.id
                JOIN projects p ON te.project_id = p.id
                LEFT JOIN operations o ON te.operation_id = o.id
                WHERE DATE(te.punch_in) = ? AND te.total_cost IS NOT NULL
                GROUP BY e.id, p.id, o.id
                ORDER BY e.prenom, e.nom, p.nom_projet
            ''', (date_str,))
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur résumé quotidien {date_str}: {e}")
            return []
    
    def get_project_revenue_summary(self, project_id: int = None) -> List[Dict]:
        """Résumé des revenus par projet"""
        try:
            if project_id:
                query = '''
                    SELECT 
                        p.nom_projet as project_name,
                        p.client_nom_cache as client_name,
                        COALESCE(SUM(te.total_hours), 0.0) as total_hours,
                        COALESCE(SUM(te.total_cost), 0.0) as total_revenue,
                        COUNT(DISTINCT te.employee_id) as employees_count,
                        COUNT(te.id) as entries_count
                    FROM time_entries te
                    JOIN projects p ON te.project_id = p.id
                    WHERE p.id = ? AND te.total_cost IS NOT NULL
                    GROUP BY p.id
                '''
                params = (project_id,)
            else:
                query = '''
                    SELECT 
                        p.nom_projet as project_name,
                        p.client_nom_cache as client_name,
                        COALESCE(SUM(te.total_hours), 0.0) as total_hours,
                        COALESCE(SUM(te.total_cost), 0.0) as total_revenue,
                        COUNT(DISTINCT te.employee_id) as employees_count,
                        COUNT(te.id) as entries_count
                    FROM time_entries te
                    JOIN projects p ON te.project_id = p.id
                    WHERE te.total_cost IS NOT NULL
                    GROUP BY p.id
                    ORDER BY total_revenue DESC
                '''
                params = None
            
            rows = self.db.execute_query(query, params)
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur résumé revenus: {e}")
            return []
    
    def get_timetracker_statistics(self) -> Dict:
        """Statistiques globales TimeTracker"""
        try:
            stats = {
                'total_employees': 0,
                'active_entries': 0,
                'total_revenue_today': 0.0,
                'total_hours_today': 0.0
            }
            
            # Employés actifs
            emp_result = self.db.execute_query("SELECT COUNT(*) as count FROM employees WHERE statut = 'ACTIF'")
            if emp_result:
                stats['total_employees'] = emp_result[0]['count']
            
            # Pointages actifs
            active_result = self.db.execute_query("SELECT COUNT(*) as count FROM time_entries WHERE punch_out IS NULL")
            if active_result:
                stats['active_entries'] = active_result[0]['count']
            
            # Revenus et heures du jour
            today = datetime.now().strftime('%Y-%m-%d')
            daily_result = self.db.execute_query('''
                SELECT 
                    COALESCE(SUM(total_hours), 0.0) as hours,
                    COALESCE(SUM(total_cost), 0.0) as revenue
                FROM time_entries 
                WHERE DATE(punch_in) = ? AND total_cost IS NOT NULL
            ''', (today,))
            
            if daily_result:
                stats['total_hours_today'] = daily_result[0]['hours']
                stats['total_revenue_today'] = daily_result[0]['revenue']
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur statistiques TimeTracker: {e}")
            return {}


def show_timetracker_interface():
    """
    Interface principale TimeTracker intégrée dans l'ERP DG Inc.
    Utilise la base SQLite unifiée
    """
    
    # Vérifier l'accès à la base ERP
    if 'erp_db' not in st.session_state:
        st.error("❌ Accès TimeTracker nécessite une session ERP active")
        st.info("Veuillez redémarrer l'application ERP.")
        return
    
    # Initialiser le TimeTracker ERP unifié
    if 'timetracker_erp' not in st.session_state:
        st.session_state.timetracker_erp = TimeTrackerERP(st.session_state.erp_db)
    
    tt = st.session_state.timetracker_erp
    
    # En-tête TimeTracker avec style ERP harmonisé
    st.markdown("""
    <div class='project-header' style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h2 style='margin: 0; text-align: center;'>⏱️ TimeTracker Pro - ERP Production DG Inc.</h2>
        <p style='margin: 5px 0 0 0; text-align: center; opacity: 0.9;'>🗄️ Architecture SQLite Unifiée</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Statistiques en temps réel
    stats = tt.get_timetracker_statistics()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Employés ERP", stats.get('total_employees', 0))
    with col2:
        st.metric("🟢 Pointages Actifs", stats.get('active_entries', 0))
    with col3:
        st.metric("⏱️ Heures Aujourd'hui", f"{stats.get('total_hours_today', 0):.1f}h")
    with col4:
        st.metric("💰 Revenus Aujourd'hui", f"{stats.get('total_revenue_today', 0):.0f}$ CAD")
    
    # Navigation TimeTracker
    tab_pointage, tab_analytics, tab_admin, tab_system = st.tabs([
        "🕐 Pointage Employés", "📊 Analytics & Rapports", "⚙️ Administration", "ℹ️ Système"
    ])
    
    with tab_pointage:
        show_employee_timetracking_interface(tt)
    
    with tab_analytics:
        show_analytics_interface(tt)
    
    with tab_admin:
        show_admin_interface(tt)
    
    with tab_system:
        show_system_interface()


def show_employee_timetracking_interface(tt: TimeTrackerERP):
    """Interface de pointage pour employés"""
    
    st.markdown("### 👤 Interface de Pointage")
    
    # Récupération des employés depuis l'ERP
    employees = tt.get_all_employees()
    
    if not employees:
        st.warning("⚠️ Aucun employé actif trouvé dans l'ERP.")
        st.info("Veuillez ajouter des employés dans le module RH de l'ERP.")
        return
    
    # Sélecteur d'employé
    employee_options = {emp['id']: f"{emp['name']} - {emp['poste']}" for emp in employees}
    
    selected_employee_id = st.selectbox(
        "👤 Sélectionner l'employé:",
        options=list(employee_options.keys()),
        format_func=lambda x: employee_options[x],
        key="timetracker_employee_selector"
    )
    
    if not selected_employee_id:
        return
    
    employee = tt.get_employee_by_id(selected_employee_id)
    current_entry = tt.get_employee_current_entry(selected_employee_id)
    
    # Interface de pointage
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class='info-card'>
            <h4>👤 {employee['name']}</h4>
            <p><strong>💼 Poste:</strong> {employee.get('poste', 'N/A')}</p>
            <p><strong>🏢 Département:</strong> {employee.get('departement', 'N/A')}</p>
            <p><strong>📧 Email:</strong> {employee.get('email', 'N/A')}</p>
            <p><strong>🆔 Code ERP:</strong> {employee['employee_code']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if current_entry:
            # Employé pointé - afficher le status et bouton punch out
            punch_in_time = datetime.fromisoformat(current_entry['punch_in'])
            elapsed = datetime.now() - punch_in_time
            elapsed_hours = elapsed.total_seconds() / 3600
            estimated_cost = elapsed_hours * current_entry['hourly_rate']
            
            st.markdown(f"""
            <div class='info-card' style='border-left: 4px solid #10b981; background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);'>
                <h4>🟢 POINTÉ ACTUELLEMENT</h4>
                <p><strong>📋 Projet:</strong> {current_entry['project_name']}</p>
                <p><strong>🔧 Tâche:</strong> {current_entry['task_name']}</p>
                <p><strong>🕐 Début:</strong> {punch_in_time.strftime('%H:%M:%S')}</p>
                <p><strong>⏱️ Durée:</strong> {elapsed_hours:.2f}h</p>
                <p><strong>💰 Coût estimé:</strong> {estimated_cost:.2f}$ CAD</p>
                <p><strong>💵 Taux:</strong> {current_entry['hourly_rate']:.2f}$/h</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Formulaire punch out
            st.markdown("#### 🔴 Terminer le pointage")
            with st.form("punch_out_form"):
                notes_out = st.text_area("📝 Notes de fin (optionnel):", 
                                       placeholder="Travail accompli, difficultés rencontrées...")
                
                punch_out_col1, punch_out_col2 = st.columns(2)
                with punch_out_col1:
                    if st.form_submit_button("🔴 PUNCH OUT", use_container_width=True):
                        try:
                            tt.punch_out(selected_employee_id, notes_out)
                            st.success(f"✅ Punch out enregistré ! Durée totale: {elapsed_hours:.2f}h - Coût: {estimated_cost:.2f}$ CAD")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erreur punch out: {str(e)}")
                with punch_out_col2:
                    if st.form_submit_button("⏸️ Pause", use_container_width=True):
                        st.info("Fonctionnalité pause en développement")
        
        else:
            # Employé non pointé - interface punch in
            st.markdown("""
            <div class='info-card' style='border-left: 4px solid #f59e0b; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);'>
                <h4>🟡 PRÊT À POINTER</h4>
                <p>Sélectionnez un projet et une tâche pour commencer le pointage</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Interface de sélection projet/tâche si pas pointé
    if not current_entry:
        st.markdown("---")
        st.markdown("#### 📋 Nouveau Pointage")
        
        projects = tt.get_active_projects()
        if not projects:
            st.warning("❌ Aucun projet actif disponible dans l'ERP.")
            st.info("Veuillez créer des projets dans le module Projets de l'ERP.")
            return
        
        with st.form("punch_in_form"):
            # Sélection du projet
            project_options = {p['id']: f"{p['project_name']} ({p['client_name']})" for p in projects}
            selected_project_id = st.selectbox(
                "📋 Projet:",
                options=list(project_options.keys()),
                format_func=lambda x: project_options[x]
            )
            
            # Sélection de l'opération/tâche
            selected_operation_id = None
            if selected_project_id:
                operations = tt.get_project_operations(selected_project_id)
                if operations:
                    operation_options = {op['id']: f"{op['task_name']} ({op['hourly_rate']:.0f}$/h)" for op in operations}
                    selected_operation_id = st.selectbox(
                        "🔧 Opération/Tâche:",
                        options=[None] + list(operation_options.keys()),
                        format_func=lambda x: "Tâche générale (95$/h)" if x is None else operation_options[x]
                    )
                else:
                    st.info("Aucune opération définie pour ce projet. Pointage général disponible.")
            
            notes_in = st.text_area("📝 Notes de début (optionnel):", 
                                  placeholder="Objectifs, plan de travail...")
            
            punch_in_col1, punch_in_col2 = st.columns(2)
            with punch_in_col1:
                if st.form_submit_button("🟢 PUNCH IN", use_container_width=True):
                    if selected_project_id:
                        try:
                            entry_id = tt.punch_in(selected_employee_id, selected_project_id, selected_operation_id, notes_in)
                            st.success(f"✅ Punch in enregistré ! ID: {entry_id}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erreur punch in: {str(e)}")
                    else:
                        st.error("Veuillez sélectionner un projet.")
            
            with punch_in_col2:
                if st.form_submit_button("📋 Voir Projets", use_container_width=True):
                    st.info("Redirection vers module Projets ERP...")
    
    # Historique récent
    st.markdown("---")
    st.markdown("#### 📊 Historique Récent")
    
    recent_entries = tt.get_employee_time_entries(selected_employee_id, 10)
    if recent_entries:
        df_history = []
        for entry in recent_entries:
            punch_in = datetime.fromisoformat(entry['punch_in'])
            punch_out_str = "En cours..."
            duration_str = "En cours..."
            cost_str = "En cours..."
            
            if entry['punch_out']:
                punch_out = datetime.fromisoformat(entry['punch_out'])
                punch_out_str = punch_out.strftime('%H:%M:%S')
                duration_str = f"{entry['total_hours']:.2f}h"
                cost_str = f"{entry['total_cost']:.2f}$ CAD"
            
            df_history.append({
                '📅 Date': punch_in.strftime('%Y-%m-%d'),
                '🕐 Début': punch_in.strftime('%H:%M:%S'),
                '🕑 Fin': punch_out_str,
                '📋 Projet': entry['project_name'],
                '🔧 Tâche': entry['task_name'],
                '⏱️ Durée': duration_str,
                '💰 Coût': cost_str
            })
        
        st.dataframe(pd.DataFrame(df_history), use_container_width=True)
    else:
        st.info("Aucun historique de pointage.")


def show_analytics_interface(tt: TimeTrackerERP):
    """Interface d'analytics TimeTracker"""
    
    st.markdown("### 📊 Analytics & Rapports")
    
    # Période d'analyse
    col_period1, col_period2 = st.columns(2)
    with col_period1:
        start_date = st.date_input("📅 Date début:", datetime.now().date() - timedelta(days=30))
    with col_period2:
        end_date = st.date_input("📅 Date fin:", datetime.now().date())
    
    # Revenus par projet
    st.markdown("#### 💰 Revenus par Projet (Base ERP)")
    project_revenues = tt.get_project_revenue_summary()
    
    if project_revenues:
        # Validation et nettoyage des données
        valid_revenues = []
        total_revenue_global = 0
        total_hours_global = 0
        
        for rev in project_revenues:
            try:
                revenue = float(rev.get('total_revenue', 0) or 0)
                hours = float(rev.get('total_hours', 0) or 0)
                
                if revenue > 0:
                    valid_revenues.append({
                        'project_name': rev.get('project_name', 'Projet Inconnu'),
                        'total_revenue': revenue,
                        'total_hours': hours
                    })
                    total_revenue_global += revenue
                    total_hours_global += hours
            except (ValueError, TypeError):
                continue
        
        if valid_revenues:
            # Graphique en secteurs
            fig_pie = px.pie(
                values=[rev['total_revenue'] for rev in valid_revenues],
                names=[rev['project_name'] for rev in valid_revenues],
                title="🥧 Répartition des Revenus TimeTracker par Projet ERP"
            )
            fig_pie.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                title_x=0.5
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Graphique en barres
            fig_bar = px.bar(
                x=[rev['project_name'] for rev in valid_revenues],
                y=[rev['total_revenue'] for rev in valid_revenues],
                title="📊 Revenus TimeTracker par Projet",
                labels={'x': 'Projets ERP', 'y': 'Revenus (CAD)'}
            )
            fig_bar.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                title_x=0.5
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Tableau détaillé
        df_revenues = []
        for rev in project_revenues:
            try:
                revenue = float(rev.get('total_revenue', 0) or 0)
                hours = float(rev.get('total_hours', 0) or 0)
                
                df_revenues.append({
                    '📋 Projet ERP': rev.get('project_name', 'N/A'),
                    '👤 Client': rev.get('client_name', 'N/A'),
                    '⏱️ Heures': f"{hours:.1f}h",
                    '💰 Revenus': f"{revenue:.2f}$ CAD",
                    '👥 Employés': rev.get('employees_count', 0),
                    '📊 Pointages': rev.get('entries_count', 0),
                    '💵 Taux Moy.': f"{(revenue/hours):.2f}$/h" if hours > 0 else "N/A"
                })
            except (ValueError, TypeError):
                continue
        
        if df_revenues:
            st.dataframe(pd.DataFrame(df_revenues), use_container_width=True)
            
            # Métriques globales
            avg_hourly_rate = total_revenue_global / total_hours_global if total_hours_global > 0 else 0
            
            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            with metrics_col1:
                st.metric("💰 Revenus Total TimeTracker", f"{total_revenue_global:.2f}$ CAD")
            with metrics_col2:
                st.metric("⏱️ Heures Total", f"{total_hours_global:.1f}h")
            with metrics_col3:
                st.metric("💵 Taux Horaire Moyen", f"{avg_hourly_rate:.2f}$/h")
        
    else:
        st.info("Aucune donnée de revenus TimeTracker disponible.")
        st.markdown("💡 **Conseil**: Effectuez des pointages pour générer des données d'analyse.")


def show_admin_interface(tt: TimeTrackerERP):
    """Interface d'administration TimeTracker"""
    
    st.markdown("### ⚙️ Administration TimeTracker ERP")
    
    # Vue d'ensemble avec données ERP
    employees = tt.get_all_employees()
    projects = tt.get_active_projects()
    
    # Métriques d'administration
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Employés ERP", len(employees))
    with col2:
        st.metric("📋 Projets Actifs", len(projects))
    with col3:
        # Employés actuellement pointés
        currently_working = 0
        for emp in employees:
            if tt.get_employee_current_entry(emp['id']):
                currently_working += 1
        st.metric("🟢 En Pointage", currently_working)
    with col4:
        # Revenus du jour
        today_summary = tt.get_daily_summary()
        today_revenue = sum(float(entry.get('total_cost', 0) or 0) for entry in today_summary)
        st.metric("💰 Revenus Jour", f"{today_revenue:.0f}$ CAD")
    
    # Onglets d'administration
    admin_tab1, admin_tab2, admin_tab3 = st.tabs([
        "👥 Employés ERP", "📋 Projets ERP", "📊 Résumé Quotidien"
    ])
    
    with admin_tab1:
        st.markdown("#### 👥 Gestion des Employés (Synchronisé ERP)")
        
        if employees:
            df_employees = []
            for emp in employees:
                current_entry = tt.get_employee_current_entry(emp['id'])
                status = "🟢 Pointé" if current_entry else "🟡 Libre"
                current_task = ""
                if current_entry:
                    current_task = f"{current_entry['project_name']} - {current_entry['task_name']}"
                
                df_employees.append({
                    '🆔 ID ERP': emp['id'],
                    '👤 Nom': emp['name'],
                    '💼 Poste': emp.get('poste', 'N/A'),
                    '🏢 Département': emp.get('departement', 'N/A'),
                    '📧 Email': emp.get('email', 'N/A'),
                    '🚦 Statut': status,
                    '🔧 Tâche Actuelle': current_task or 'Aucune'
                })
            
            st.dataframe(pd.DataFrame(df_employees), use_container_width=True)
            st.info("ℹ️ Données synchronisées automatiquement depuis le module RH ERP")
        else:
            st.warning("Aucun employé actif dans l'ERP.")
    
    with admin_tab2:
        st.markdown("#### 📋 Gestion des Projets (Synchronisé ERP)")
        
        if projects:
            df_projects = []
            for proj in projects:
                operations = tt.get_project_operations(proj['id'])
                revenue_summary = tt.get_project_revenue_summary(proj['id'])
                total_revenue = revenue_summary[0]['total_revenue'] if revenue_summary else 0
                
                df_projects.append({
                    '🆔 ID ERP': proj['id'],
                    '📋 Nom': proj['project_name'],
                    '👤 Client': proj.get('client_name', 'N/A'),
                    '🚦 Statut': proj['statut'],
                    '🔧 Opérations': len(operations),
                    '💰 Revenus TimeTracker': f"{total_revenue:.2f}$ CAD"
                })
            
            st.dataframe(pd.DataFrame(df_projects), use_container_width=True)
            st.info("ℹ️ Données synchronisées automatiquement depuis le module Projets ERP")
        else:
            st.warning("Aucun projet actif dans l'ERP.")
    
    with admin_tab3:
        st.markdown("#### 📊 Résumé Quotidien TimeTracker")
        
        # Sélecteur de date
        selected_date = st.date_input("📅 Date:", datetime.now().date())
        date_str = selected_date.strftime('%Y-%m-%d')
        
        daily_summary = tt.get_daily_summary(date_str)
        
        if daily_summary:
            df_daily = []
            total_hours = 0
            total_revenue = 0
            
            for entry in daily_summary:
                hours = entry.get('total_hours', 0) or 0
                cost = entry.get('total_cost', 0) or 0
                total_hours += hours
                total_revenue += cost
                
                df_daily.append({
                    '👤 Employé': entry['employee_name'],
                    '📋 Projet ERP': entry['project_name'],
                    '🔧 Tâche': entry['task_name'],
                    '⏱️ Heures': f"{hours:.2f}h",
                    '💰 Revenus': f"{cost:.2f}$ CAD",
                    '📊 Pointages': entry['entries_count']
                })
            
            # Métriques du jour
            day_col1, day_col2, day_col3 = st.columns(3)
            with day_col1:
                st.metric("⏱️ Total Heures", f"{total_hours:.1f}h")
            with day_col2:
                st.metric("💰 Total Revenus", f"{total_revenue:.2f}$ CAD")
            with day_col3:
                avg_rate = total_revenue / total_hours if total_hours > 0 else 0
                st.metric("💵 Taux Moyen", f"{avg_rate:.2f}$/h")
            
            st.dataframe(pd.DataFrame(df_daily), use_container_width=True)
        else:
            st.info(f"Aucune activité TimeTracker enregistrée pour le {date_str}")
            st.markdown("💡 **Conseil**: Les employés doivent effectuer des pointages pour générer des données.")


def show_system_interface():
    """Interface d'information système (remplace la synchronisation)"""
    
    st.markdown("### ℹ️ Informations Système ERP")
    
    st.success("""
    🎉 **Architecture SQLite Unifiée Active !**
    
    Plus besoin de synchronisation - toutes les données TimeTracker sont directement 
    intégrées dans la base ERP unifiée `erp_production_dg.db`.
    """)
    
    # Informations sur la base unifiée
    if 'erp_db' in st.session_state:
        db_info = st.session_state.erp_db.get_schema_info()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📊 Base ERP", f"{db_info['file_size_mb']} MB")
            st.metric("👥 Employés", db_info['tables'].get('employees', 0))
            st.metric("📋 Projets", db_info['tables'].get('projects', 0))
        with col2:
            st.metric("⏱️ Pointages", db_info['tables'].get('time_entries', 0))
            st.metric("🔧 Opérations", db_info['tables'].get('operations', 0))
            st.metric("🏢 Entreprises", db_info['tables'].get('companies', 0))
        
        # Validation de l'intégrité
        st.markdown("#### 🔍 Validation de l'Intégrité")
        
        if st.button("🔍 Vérifier Intégrité Base", use_container_width=True):
            with st.spinner("Validation en cours..."):
                integrity = st.session_state.erp_db.validate_integrity()
                
                if 'error' not in integrity:
                    st.markdown("**Résultats de validation:**")
                    for check, status in integrity.items():
                        icon = "✅" if status else "❌"
                        check_name = check.replace('_', ' ').title()
                        st.markdown(f"{icon} {check_name}")
                    
                    if all(integrity.values()):
                        st.success("🎉 Intégrité parfaite ! Architecture unifiée fonctionnelle.")
                    else:
                        st.warning("⚠️ Certaines vérifications ont échoué.")
                else:
                    st.error(f"Erreur validation: {integrity['error']}")
        
        # Informations détaillées
        st.markdown("#### 📋 Détails de la Base")
        
        with st.expander("📊 Informations Techniques", expanded=False):
            st.json(db_info)
    
    else:
        st.error("❌ Base ERP non disponible")


# Fonctions utilitaires (conservées pour compatibilité)
def hash_password(password: str) -> str:
    """Hash un mot de passe avec SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Vérifie un mot de passe contre son hash"""
    return hash_password(password) == hashed


# --- END OF FILE timetracker.py - VERSION FINALE ERP UNIFIÉE ---
