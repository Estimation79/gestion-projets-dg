# --- START OF FILE timetracker.py ---

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, time
import hashlib
import json
from typing import Dict, List, Optional, Tuple
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimeTrackerDB:
    """
    Gestionnaire de base de données TimeTracker intégré à l'ERP DG Inc.
    Compatible avec la synchronisation ERP via database_sync.py
    """
    
    def __init__(self, db_path: str = "timetracker.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données TimeTracker (compatible avec database_sync.py)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tables créées par database_sync.py - on s'assure qu'elles existent
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    password_hash TEXT,
                    role TEXT DEFAULT 'employee',
                    is_active INTEGER DEFAULT 1,
                    email TEXT,
                    poste TEXT,
                    salaire REAL,
                    date_embauche TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    erp_sync_id INTEGER,
                    last_sync TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_code TEXT UNIQUE NOT NULL,
                    project_name TEXT NOT NULL,
                    client_name TEXT,
                    requires_task_selection INTEGER DEFAULT 1,
                    erp_project_id INTEGER,
                    status TEXT DEFAULT 'À FAIRE',
                    start_date TEXT,
                    end_date TEXT,
                    estimated_price REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_sync TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    task_code TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    task_category TEXT,
                    hourly_rate REAL DEFAULT 95.0,
                    estimated_hours REAL DEFAULT 0,
                    erp_poste_id TEXT,
                    sequence_number INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS time_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER,
                    project_id INTEGER,
                    task_id INTEGER,
                    punch_in TIMESTAMP,
                    punch_out TIMESTAMP,
                    notes TEXT,
                    total_hours REAL,
                    hourly_rate REAL,
                    total_cost REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees (id),
                    FOREIGN KEY (project_id) REFERENCES projects (id),
                    FOREIGN KEY (task_id) REFERENCES project_tasks (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employee_task_assignments (
                    employee_id INTEGER,
                    project_id INTEGER,
                    task_id INTEGER,
                    skill_level TEXT DEFAULT 'INTERMÉDIAIRE',
                    hourly_rate_override REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (employee_id, project_id, task_id),
                    FOREIGN KEY (employee_id) REFERENCES employees (id),
                    FOREIGN KEY (project_id) REFERENCES projects (id),
                    FOREIGN KEY (task_id) REFERENCES project_tasks (id)
                )
            ''')
            
            conn.commit()
    
    def get_all_employees(self) -> List[Dict]:
        """Récupère tous les employés actifs"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM employees 
                WHERE is_active = 1 
                ORDER BY name
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_employee_by_id(self, employee_id: int) -> Optional[Dict]:
        """Récupère un employé par son ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM employees WHERE id = ?', (employee_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_active_projects(self) -> List[Dict]:
        """Récupère tous les projets actifs"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM projects 
                WHERE status IN ('À FAIRE', 'EN COURS') 
                ORDER BY project_name
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_project_tasks(self, project_id: int) -> List[Dict]:
        """Récupère les tâches d'un projet"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM project_tasks 
                WHERE project_id = ? 
                ORDER BY sequence_number, task_name
            ''', (project_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_employee_current_entry(self, employee_id: int) -> Optional[Dict]:
        """Vérifie si l'employé a une entrée en cours (pas de punch_out)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT te.*, p.project_name, pt.task_name 
                FROM time_entries te
                JOIN projects p ON te.project_id = p.id
                JOIN project_tasks pt ON te.task_id = pt.id
                WHERE te.employee_id = ? AND te.punch_out IS NULL
                ORDER BY te.punch_in DESC
                LIMIT 1
            ''', (employee_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def punch_in(self, employee_id: int, project_id: int, task_id: int, notes: str = "") -> int:
        """Enregistre un punch in"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Vérifier s'il n'y a pas déjà un punch in actif
            current_entry = self.get_employee_current_entry(employee_id)
            if current_entry:
                raise ValueError("L'employé a déjà un pointage actif")
            
            # Obtenir le taux horaire de la tâche
            cursor.execute('SELECT hourly_rate FROM project_tasks WHERE id = ?', (task_id,))
            task_rate_result = cursor.fetchone()
            task_rate = task_rate_result[0] if task_rate_result else 95.0
            
            # Créer l'entrée
            cursor.execute('''
                INSERT INTO time_entries 
                (employee_id, project_id, task_id, punch_in, notes, hourly_rate)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (employee_id, project_id, task_id, datetime.now().isoformat(), notes, task_rate))
            
            entry_id = cursor.lastrowid
            conn.commit()
            return entry_id
    
    def punch_out(self, employee_id: int, notes: str = "") -> bool:
        """Enregistre un punch out"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
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
            cursor.execute('''
                UPDATE time_entries 
                SET punch_out = ?, total_hours = ?, total_cost = ?, notes = ?
                WHERE id = ?
            ''', (punch_out_time.isoformat(), total_hours, total_cost, notes, current_entry['id']))
            
            conn.commit()
            return True
    
    def get_employee_time_entries(self, employee_id: int, limit: int = 50) -> List[Dict]:
        """Récupère les dernières entrées d'un employé"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT te.*, p.project_name, pt.task_name
                FROM time_entries te
                JOIN projects p ON te.project_id = p.id
                JOIN project_tasks pt ON te.task_id = pt.id
                WHERE te.employee_id = ?
                ORDER BY te.punch_in DESC
                LIMIT ?
            ''', (employee_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_daily_summary(self, date_str: str = None) -> List[Dict]:
        """Récupère le résumé quotidien des pointages"""
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    e.name as employee_name,
                    p.project_name,
                    pt.task_name,
                    COALESCE(SUM(te.total_hours), 0.0) as total_hours,
                    COALESCE(SUM(te.total_cost), 0.0) as total_cost,
                    COUNT(te.id) as entries_count
                FROM time_entries te
                JOIN employees e ON te.employee_id = e.id
                JOIN projects p ON te.project_id = p.id
                JOIN project_tasks pt ON te.task_id = pt.id
                WHERE DATE(te.punch_in) = ? AND te.total_cost IS NOT NULL
                GROUP BY e.id, p.id, pt.id
                ORDER BY e.name, p.project_name
            ''', (date_str,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_project_revenue_summary(self, project_id: int = None) -> List[Dict]:
        """Résumé des revenus par projet"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if project_id:
                cursor.execute('''
                    SELECT 
                        p.project_name,
                        p.client_name,
                        COALESCE(SUM(te.total_hours), 0.0) as total_hours,
                        COALESCE(SUM(te.total_cost), 0.0) as total_revenue,
                        COUNT(DISTINCT te.employee_id) as employees_count,
                        COUNT(te.id) as entries_count
                    FROM time_entries te
                    JOIN projects p ON te.project_id = p.id
                    WHERE p.id = ? AND te.total_cost IS NOT NULL
                    GROUP BY p.id
                ''', (project_id,))
            else:
                cursor.execute('''
                    SELECT 
                        p.project_name,
                        p.client_name,
                        COALESCE(SUM(te.total_hours), 0.0) as total_hours,
                        COALESCE(SUM(te.total_cost), 0.0) as total_revenue,
                        COUNT(DISTINCT te.employee_id) as employees_count,
                        COUNT(te.id) as entries_count
                    FROM time_entries te
                    JOIN projects p ON te.project_id = p.id
                    WHERE te.total_cost IS NOT NULL
                    GROUP BY p.id
                    ORDER BY total_revenue DESC
                ''')
            
            return [dict(row) for row in cursor.fetchall()]


def show_timetracker_interface():
    """
    Interface principale TimeTracker intégrée dans l'ERP DG Inc.
    Utilise l'authentification ERP unifiée et le style harmonisé
    """
    
    # Vérifier l'authentification ERP (session unifiée)
    if not hasattr(st.session_state, 'gestionnaire'):
        st.error("❌ Accès TimeTracker nécessite une session ERP active")
        return
    
    # Initialiser le gestionnaire TimeTracker
    if 'timetracker_db' not in st.session_state:
        st.session_state.timetracker_db = TimeTrackerDB()
    
    db = st.session_state.timetracker_db
    
    # En-tête TimeTracker avec style ERP harmonisé
    st.markdown("""
    <div class='project-header'>
        <h2>⏱️ TimeTracker Pro Desmarais & Gagné</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation TimeTracker
    tab_pointage, tab_admin, tab_analytics, tab_sync = st.tabs([
        "🕐 Pointage", "⚙️ Administration", "📊 Analytics", "🔄 Synchronisation"
    ])
    
    with tab_pointage:
        show_employee_timetracking_interface(db)
    
    with tab_admin:
        show_admin_interface(db)
    
    with tab_analytics:
        show_analytics_interface(db)
    
    with tab_sync:
        show_sync_management_interface()


def show_employee_timetracking_interface(db: TimeTrackerDB):
    """Interface de pointage pour employés"""
    
    st.markdown("### 👤 Interface Employé - Pointage")
    
    # Sélection de l'employé (simplifié car authentification ERP)
    employees = db.get_all_employees()
    
    if not employees:
        st.warning("⚠️ Aucun employé synchronisé. Veuillez lancer une synchronisation ERP.")
        return
    
    # Sélecteur d'employé (en attendant l'auth complète)
    employee_options = {emp['id']: f"{emp['name']} ({emp['poste']})" for emp in employees}
    
    selected_employee_id = st.selectbox(
        "Sélectionner l'employé:",
        options=list(employee_options.keys()),
        format_func=lambda x: employee_options[x],
        key="timetracker_employee_selector"
    )
    
    if not selected_employee_id:
        return
    
    employee = db.get_employee_by_id(selected_employee_id)
    current_entry = db.get_employee_current_entry(selected_employee_id)
    
    # Interface de pointage
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class='info-card'>
            <h4>👤 {employee['name']}</h4>
            <p><strong>📧 Email:</strong> {employee.get('email', 'N/A')}</p>
            <p><strong>💼 Poste:</strong> {employee.get('poste', 'N/A')}</p>
            <p><strong>🆔 Code:</strong> {employee['employee_code']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if current_entry:
            # Employé pointé - afficher le status et bouton punch out
            punch_in_time = datetime.fromisoformat(current_entry['punch_in'])
            elapsed = datetime.now() - punch_in_time
            elapsed_hours = elapsed.total_seconds() / 3600
            
            st.markdown(f"""
            <div class='info-card' style='border-left: 4px solid #10b981;'>
                <h4>🟢 POINTÉ</h4>
                <p><strong>📋 Projet:</strong> {current_entry['project_name']}</p>
                <p><strong>🔧 Tâche:</strong> {current_entry['task_name']}</p>
                <p><strong>🕐 Début:</strong> {punch_in_time.strftime('%H:%M')}</p>
                <p><strong>⏱️ Durée:</strong> {elapsed_hours:.2f}h</p>
                <p><strong>💰 Coût estimé:</strong> {elapsed_hours * current_entry['hourly_rate']:.2f}$ CAD</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Formulaire punch out
            with st.form("punch_out_form"):
                notes_out = st.text_area("📝 Notes (optionnel):", placeholder="Travail effectué...")
                if st.form_submit_button("🔴 PUNCH OUT", use_container_width=True):
                    try:
                        db.punch_out(selected_employee_id, notes_out)
                        st.success(f"✅ Punch out enregistré ! Durée: {elapsed_hours:.2f}h")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur punch out: {str(e)}")
        
        else:
            # Employé non pointé - interface punch in
            st.markdown("""
            <div class='info-card' style='border-left: 4px solid #f59e0b;'>
                <h4>🟡 NON POINTÉ</h4>
                <p>Sélectionnez un projet et une tâche pour commencer</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Interface de sélection projet/tâche si pas pointé
    if not current_entry:
        st.markdown("---")
        st.markdown("#### 📋 Nouveau Pointage")
        
        projects = db.get_active_projects()
        if not projects:
            st.warning("Aucun projet actif disponible.")
            return
        
        with st.form("punch_in_form"):
            # Sélection du projet
            project_options = {p['id']: f"{p['project_name']} ({p['client_name']})" for p in projects}
            selected_project_id = st.selectbox(
                "Projet:",
                options=list(project_options.keys()),
                format_func=lambda x: project_options[x]
            )
            
            # Sélection de la tâche
            if selected_project_id:
                tasks = db.get_project_tasks(selected_project_id)
                if tasks:
                    task_options = {t['id']: f"{t['task_name']} ({t['hourly_rate']}$/h)" for t in tasks}
                    selected_task_id = st.selectbox(
                        "Tâche:",
                        options=list(task_options.keys()),
                        format_func=lambda x: task_options[x]
                    )
                else:
                    st.warning("Aucune tâche disponible pour ce projet.")
                    selected_task_id = None
            else:
                selected_task_id = None
            
            notes_in = st.text_area("📝 Notes (optionnel):", placeholder="Description du travail à effectuer...")
            
            if st.form_submit_button("🟢 PUNCH IN", use_container_width=True):
                if selected_project_id and selected_task_id:
                    try:
                        entry_id = db.punch_in(selected_employee_id, selected_project_id, selected_task_id, notes_in)
                        st.success(f"✅ Punch in enregistré ! ID: {entry_id}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur punch in: {str(e)}")
                else:
                    st.error("Veuillez sélectionner un projet et une tâche.")
    
    # Historique récent
    st.markdown("---")
    st.markdown("#### 📊 Historique Récent")
    
    recent_entries = db.get_employee_time_entries(selected_employee_id, 10)
    if recent_entries:
        df_history = []
        for entry in recent_entries:
            punch_in = datetime.fromisoformat(entry['punch_in'])
            punch_out_str = "En cours..."
            duration_str = "En cours..."
            cost_str = "En cours..."
            
            if entry['punch_out']:
                punch_out = datetime.fromisoformat(entry['punch_out'])
                punch_out_str = punch_out.strftime('%H:%M')
                duration_str = f"{entry['total_hours']:.2f}h"
                cost_str = f"{entry['total_cost']:.2f}$ CAD"
            
            df_history.append({
                '📅 Date': punch_in.strftime('%Y-%m-%d'),
                '🕐 Début': punch_in.strftime('%H:%M'),
                '🕑 Fin': punch_out_str,
                '📋 Projet': entry['project_name'],
                '🔧 Tâche': entry['task_name'],
                '⏱️ Durée': duration_str,
                '💰 Coût': cost_str
            })
        
        st.dataframe(pd.DataFrame(df_history), use_container_width=True)
    else:
        st.info("Aucun historique de pointage.")


def show_admin_interface(db: TimeTrackerDB):
    """Interface d'administration TimeTracker"""
    
    st.markdown("### ⚙️ Administration TimeTracker")
    
    # Vue d'ensemble
    employees = db.get_all_employees()
    projects = db.get_active_projects()
    
    # Métriques
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Employés", len(employees))
    with col2:
        st.metric("📋 Projets Actifs", len(projects))
    with col3:
        # Employés actuellement pointés
        currently_working = 0
        for emp in employees:
            if db.get_employee_current_entry(emp['id']):
                currently_working += 1
        st.metric("🟢 En Activité", currently_working)
    with col4:
        # 🔧 CORRECTION - Revenus du jour avec gestion robuste des valeurs None
        today_summary = db.get_daily_summary()
        today_revenue = 0.0
        for entry in today_summary:
            cost = entry.get('total_cost')
            if cost is not None and cost != '':
                try:
                    today_revenue += float(cost)
                except (ValueError, TypeError):
                    continue  # Ignorer les valeurs invalides
        
        st.metric("💰 Revenus Jour", f"{today_revenue:.0f}$ CAD")
    
    # Onglets d'administration
    admin_tab1, admin_tab2, admin_tab3 = st.tabs([
        "👥 Employés", "📋 Projets", "📊 Résumé Quotidien"
    ])
    
    with admin_tab1:
        st.markdown("#### 👥 Gestion des Employés")
        
        if employees:
            df_employees = []
            for emp in employees:
                current_entry = db.get_employee_current_entry(emp['id'])
                status = "🟢 Pointé" if current_entry else "🟡 Libre"
                current_task = ""
                if current_entry:
                    current_task = f"{current_entry['project_name']} - {current_entry['task_name']}"
                
                df_employees.append({
                    '🆔 ID': emp['id'],
                    '👤 Nom': emp['name'],
                    '💼 Poste': emp.get('poste', 'N/A'),
                    '📧 Email': emp.get('email', 'N/A'),
                    '🚦 Statut': status,
                    '🔧 Tâche Actuelle': current_task or 'Aucune'
                })
            
            st.dataframe(pd.DataFrame(df_employees), use_container_width=True)
        else:
            st.info("Aucun employé synchronisé.")
    
    with admin_tab2:
        st.markdown("#### 📋 Gestion des Projets")
        
        if projects:
            df_projects = []
            for proj in projects:
                tasks = db.get_project_tasks(proj['id'])
                revenue_summary = db.get_project_revenue_summary(proj['id'])
                total_revenue = revenue_summary[0]['total_revenue'] if revenue_summary else 0
                
                df_projects.append({
                    '🆔 ID': proj['id'],
                    '📋 Nom': proj['project_name'],
                    '👤 Client': proj.get('client_name', 'N/A'),
                    '🚦 Statut': proj['status'],
                    '🔧 Tâches': len(tasks),
                    '💰 Revenus': f"{total_revenue:.2f}$ CAD"
                })
            
            st.dataframe(pd.DataFrame(df_projects), use_container_width=True)
        else:
            st.info("Aucun projet actif.")
    
    with admin_tab3:
        st.markdown("#### 📊 Résumé Quotidien")
        
        # Sélecteur de date
        selected_date = st.date_input("📅 Date:", datetime.now().date())
        date_str = selected_date.strftime('%Y-%m-%d')
        
        daily_summary = db.get_daily_summary(date_str)
        
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
                    '📋 Projet': entry['project_name'],
                    '🔧 Tâche': entry['task_name'],
                    '⏱️ Heures': f"{hours:.2f}h",
                    '💰 Revenus': f"{cost:.2f}$ CAD",
                    '📊 Pointages': entry['entries_count']
                })
            
            # Métriques du jour
            day_col1, day_col2 = st.columns(2)
            with day_col1:
                st.metric("⏱️ Total Heures", f"{total_hours:.1f}h")
            with day_col2:
                st.metric("💰 Total Revenus", f"{total_revenue:.2f}$ CAD")
            
            st.dataframe(pd.DataFrame(df_daily), use_container_width=True)
        else:
            st.info(f"Aucune activité enregistrée pour le {date_str}")


def show_analytics_interface(db: TimeTrackerDB):
    """Interface d'analytics TimeTracker"""
    
    st.markdown("### 📊 Analytics & Rapports")
    
    # Période d'analyse
    col_period1, col_period2 = st.columns(2)
    with col_period1:
        start_date = st.date_input("📅 Date début:", datetime.now().date() - timedelta(days=30))
    with col_period2:
        end_date = st.date_input("📅 Date fin:", datetime.now().date())
    
    # Revenus par projet
    st.markdown("#### 💰 Revenus par Projet")
    project_revenues = db.get_project_revenue_summary()
    
    if project_revenues:
        # 🔧 CORRECTION - Validation des données pour graphiques
        valid_revenues = []
        for rev in project_revenues:
            total_revenue = rev.get('total_revenue', 0)
            if total_revenue is not None and total_revenue > 0:
                try:
                    valid_revenues.append({
                        'project_name': rev.get('project_name', 'Projet Inconnu'),
                        'total_revenue': float(total_revenue)
                    })
                except (ValueError, TypeError):
                    continue
        
        if valid_revenues:
            # Graphique en secteurs avec données validées
            fig_pie = px.pie(
                values=[rev['total_revenue'] for rev in valid_revenues],
                names=[rev['project_name'] for rev in valid_revenues],
                title="Répartition des Revenus par Projet"
            )
            fig_pie.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                title_x=0.5
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Aucune donnée de revenus valide pour le graphique.")
        
        # Tableau détaillé avec gestion d'erreurs
        df_revenues = []
        total_revenue_calc = 0
        total_hours_calc = 0
        
        for rev in project_revenues:
            try:
                revenue = float(rev.get('total_revenue', 0) or 0)
                hours = float(rev.get('total_hours', 0) or 0)
                
                total_revenue_calc += revenue
                total_hours_calc += hours
                
                df_revenues.append({
                    '📋 Projet': rev.get('project_name', 'N/A'),
                    '👤 Client': rev.get('client_name', 'N/A'),
                    '⏱️ Heures': f"{hours:.1f}h",
                    '💰 Revenus': f"{revenue:.2f}$ CAD",
                    '👥 Employés': rev.get('employees_count', 0),
                    '📊 Pointages': rev.get('entries_count', 0)
                })
            except (ValueError, TypeError) as e:
                st.warning(f"Données invalides ignorées pour le projet: {rev.get('project_name', 'Inconnu')}")
                continue
        
        if df_revenues:
            st.dataframe(pd.DataFrame(df_revenues), use_container_width=True)
            
            # Métriques globales avec protection d'erreur
            avg_hourly_rate = total_revenue_calc / total_hours_calc if total_hours_calc > 0 else 0
            
            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            with metrics_col1:
                st.metric("💰 Revenus Total", f"{total_revenue_calc:.2f}$ CAD")
            with metrics_col2:
                st.metric("⏱️ Heures Total", f"{total_hours_calc:.1f}h")
            with metrics_col3:
                st.metric("💵 Taux Moyen", f"{avg_hourly_rate:.2f}$/h")
        else:
            st.warning("Aucune donnée de revenus valide trouvée.")
    else:
        st.info("Aucune donnée de revenus disponible.")


def show_sync_management_interface():
    """Interface de gestion de la synchronisation"""
    
    st.markdown("### 🔄 Gestion de la Synchronisation")
    
    try:
        from database_sync import show_sync_interface
        show_sync_interface()
    except ImportError:
        st.error("❌ Module database_sync non disponible")
        st.info("Veuillez créer le fichier database_sync.py pour activer la synchronisation")


# Fonction utilitaire pour l'authentification (simplifiée pour l'intégration ERP)
def hash_password(password: str) -> str:
    """Hash un mot de passe avec SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Vérifie un mot de passe contre son hash"""
    return hash_password(password) == hashed


# --- END OF FILE timetracker.py ---
