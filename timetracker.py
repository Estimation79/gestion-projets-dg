# timetracker.py - TimeTracker Intégré ERP Production DG Inc.
# Version SQLite Unifiée Optimisée

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, time, date
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Any
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimeTrackerERP:
    """
    TimeTracker intégré à l'ERP Production DG Inc. - Version SQLite Optimisée
    Utilise directement la base SQLite unifiée sans duplication
    """
    
    def __init__(self, erp_db):
        self.db = erp_db
        logger.info("TimeTracker ERP initialisé avec base SQLite unifiée")
    
    def get_all_employees(self) -> List[Dict]:
        """Récupère tous les employés actifs depuis la base ERP avec informations étendues"""
        try:
            rows = self.db.execute_query('''
                SELECT e.id, e.prenom, e.nom, e.email, e.telephone, e.poste, 
                       e.departement, e.statut, e.salaire, e.charge_travail, e.date_embauche,
                       COUNT(pa.project_id) as projets_assignes
                FROM employees e
                LEFT JOIN project_assignments pa ON e.id = pa.employee_id
                WHERE e.statut = 'ACTIF' 
                GROUP BY e.id
                ORDER BY e.prenom, e.nom
            ''')
            
            employees = []
            for row in rows:
                emp = dict(row)
                emp['name'] = f"{emp['prenom']} {emp['nom']}"
                emp['employee_code'] = f"EMP{emp['id']:03d}"
                emp['full_name_with_role'] = f"{emp['name']} - {emp.get('poste', 'N/A')} ({emp.get('departement', 'N/A')})"
                employees.append(emp)
            
            return employees
        except Exception as e:
            logger.error(f"Erreur récupération employés: {e}")
            return []
    
    def get_employee_by_id(self, employee_id: int) -> Optional[Dict]:
        """Récupère un employé par son ID avec statistiques complètes"""
        try:
            # Données de base de l'employé
            emp_rows = self.db.execute_query('''
                SELECT e.*, COUNT(pa.project_id) as projets_assignes
                FROM employees e
                LEFT JOIN project_assignments pa ON e.id = pa.employee_id
                WHERE e.id = ? AND e.statut = 'ACTIF'
                GROUP BY e.id
            ''', (employee_id,))
            
            if not emp_rows:
                return None
            
            emp = dict(emp_rows[0])
            emp['name'] = f"{emp['prenom']} {emp['nom']}"
            emp['employee_code'] = f"EMP{emp['id']:03d}"
            
            # Statistiques TimeTracker de l'employé
            stats_rows = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total_entries,
                    COALESCE(SUM(total_hours), 0) as total_hours,
                    COALESCE(SUM(total_cost), 0) as total_revenue,
                    COALESCE(AVG(hourly_rate), 0) as avg_hourly_rate
                FROM time_entries 
                WHERE employee_id = ? AND total_cost IS NOT NULL
            ''', (employee_id,))
            
            if stats_rows:
                stats = dict(stats_rows[0])
                emp.update({
                    'timetracker_total_entries': stats['total_entries'],
                    'timetracker_total_hours': stats['total_hours'],
                    'timetracker_total_revenue': stats['total_revenue'],
                    'timetracker_avg_rate': stats['avg_hourly_rate']
                })
            
            return emp
        except Exception as e:
            logger.error(f"Erreur récupération employé {employee_id}: {e}")
            return None
    
    def get_active_projects(self) -> List[Dict]:
        """Récupère tous les projets actifs avec informations client"""
        try:
            rows = self.db.execute_query('''
                SELECT p.id, p.nom_projet, p.client_nom_cache, p.statut, p.prix_estime,
                       p.bd_ft_estime, p.date_prevu, p.description,
                       c.nom as company_name, c.secteur,
                       COUNT(o.id) as total_operations,
                       COALESCE(SUM(te.total_hours), 0) as timetracker_hours,
                       COALESCE(SUM(te.total_cost), 0) as timetracker_revenue
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                LEFT JOIN operations o ON p.id = o.project_id
                LEFT JOIN time_entries te ON p.id = te.project_id AND te.total_cost IS NOT NULL
                WHERE p.statut IN ('À FAIRE', 'EN COURS', 'EN ATTENTE') 
                GROUP BY p.id
                ORDER BY p.nom_projet
            ''')
            
            projects = []
            for row in rows:
                proj = dict(row)
                proj['project_name'] = proj['nom_projet']
                proj['client_name'] = proj['client_nom_cache'] or proj.get('company_name', 'Client Inconnu')
                proj['project_code'] = f"PROJ{proj['id']:04d}"
                proj['display_name'] = f"{proj['project_name']} - {proj['client_name']}"
                projects.append(proj)
            
            return projects
        except Exception as e:
            logger.error(f"Erreur récupération projets: {e}")
            return []
    
    def get_project_operations(self, project_id: int) -> List[Dict]:
        """Récupère les opérations d'un projet avec statistiques TimeTracker"""
        try:
            rows = self.db.execute_query('''
                SELECT o.id, o.description, o.temps_estime, o.poste_travail, o.sequence_number,
                       wc.nom as work_center_name, wc.cout_horaire, wc.departement,
                       COALESCE(SUM(te.total_hours), 0) as actual_hours,
                       COALESCE(SUM(te.total_cost), 0) as actual_cost,
                       COUNT(te.id) as timetracker_entries
                FROM operations o
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                LEFT JOIN time_entries te ON o.id = te.operation_id AND te.total_cost IS NOT NULL
                WHERE o.project_id = ? 
                GROUP BY o.id
                ORDER BY o.sequence_number, o.description
            ''', (project_id,))
            
            operations = []
            for row in rows:
                op = dict(row)
                op['task_name'] = op['description'] or f"Opération {op['sequence_number']}"
                op['task_code'] = f"OP{op['id']:03d}"
                op['hourly_rate'] = op['cout_horaire'] or 95.0  # Taux par défaut
                op['estimated_hours'] = op['temps_estime'] or 0
                
                # Calcul du pourcentage de progression
                if op['estimated_hours'] > 0:
                    op['completion_percentage'] = min(100, (op['actual_hours'] / op['estimated_hours']) * 100)
                else:
                    op['completion_percentage'] = 0
                
                operations.append(op)
            
            return operations
        except Exception as e:
            logger.error(f"Erreur récupération opérations projet {project_id}: {e}")
            return []
    
    def get_employee_current_entry(self, employee_id: int) -> Optional[Dict]:
        """Vérifie si l'employé a une entrée en cours avec détails complets"""
        try:
            rows = self.db.execute_query('''
                SELECT te.*, p.nom_projet as project_name, p.client_nom_cache as client_name,
                       o.description as task_name, o.sequence_number,
                       wc.nom as work_center_name, wc.departement as work_center_dept
                FROM time_entries te
                JOIN projects p ON te.project_id = p.id
                LEFT JOIN operations o ON te.operation_id = o.id
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE te.employee_id = ? AND te.punch_out IS NULL
                ORDER BY te.punch_in DESC
                LIMIT 1
            ''', (employee_id,))
            
            if rows:
                entry = dict(rows[0])
                entry['task_name'] = entry['task_name'] or 'Tâche générale'
                entry['client_name'] = entry['client_name'] or 'Client Inconnu'
                
                # Calcul du temps écoulé en temps réel
                punch_in_time = datetime.fromisoformat(entry['punch_in'])
                elapsed_seconds = (datetime.now() - punch_in_time).total_seconds()
                entry['elapsed_hours'] = elapsed_seconds / 3600
                entry['estimated_cost'] = entry['elapsed_hours'] * entry['hourly_rate']
                
                return entry
            return None
        except Exception as e:
            logger.error(f"Erreur récupération entrée courante employé {employee_id}: {e}")
            return None
    
    def punch_in(self, employee_id: int, project_id: int, operation_id: int = None, notes: str = "") -> int:
        """Enregistre un punch in avec validation renforcée"""
        try:
            # Vérifier s'il n'y a pas déjà un punch in actif
            current_entry = self.get_employee_current_entry(employee_id)
            if current_entry:
                raise ValueError(f"L'employé a déjà un pointage actif depuis {current_entry['punch_in']}")
            
            # Obtenir le taux horaire de l'opération ou du poste de travail
            hourly_rate = 95.0  # Taux par défaut
            if operation_id:
                rate_rows = self.db.execute_query('''
                    SELECT wc.cout_horaire 
                    FROM operations o
                    LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                    WHERE o.id = ?
                ''', (operation_id,))
                if rate_rows and rate_rows[0]['cout_horaire']:
                    hourly_rate = rate_rows[0]['cout_horaire']
            
            # Créer l'entrée de temps avec timestamp précis
            punch_in_time = datetime.now()
            entry_id = self.db.execute_insert('''
                INSERT INTO time_entries 
                (employee_id, project_id, operation_id, punch_in, notes, hourly_rate)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (employee_id, project_id, operation_id, punch_in_time.isoformat(), notes, hourly_rate))
            
            logger.info(f"Punch in créé - Employé: {employee_id}, Projet: {project_id}, Entry: {entry_id}, Taux: {hourly_rate}$/h")
            return entry_id
            
        except Exception as e:
            logger.error(f"Erreur punch in: {e}")
            raise
    
    def punch_out(self, employee_id: int, notes: str = "") -> Dict:
        """Enregistre un punch out avec calculs détaillés"""
        try:
            # Trouver l'entrée active
            current_entry = self.get_employee_current_entry(employee_id)
            if not current_entry:
                raise ValueError("Aucun pointage actif trouvé pour cet employé")
            
            # Calculer les heures et le coût avec précision
            punch_in_time = datetime.fromisoformat(current_entry['punch_in'])
            punch_out_time = datetime.now()
            total_seconds = (punch_out_time - punch_in_time).total_seconds()
            total_hours = total_seconds / 3600
            total_cost = total_hours * current_entry['hourly_rate']
            
            # Mettre à jour l'entrée avec toutes les informations
            updated_notes = f"{current_entry.get('notes', '')} | Fin: {notes}".strip(' |')
            
            self.db.execute_update('''
                UPDATE time_entries 
                SET punch_out = ?, total_hours = ?, total_cost = ?, notes = ?
                WHERE id = ?
            ''', (punch_out_time.isoformat(), total_hours, total_cost, updated_notes, current_entry['id']))
            
            # Retourner les détails de la session
            session_details = {
                'entry_id': current_entry['id'],
                'total_hours': total_hours,
                'total_cost': total_cost,
                'hourly_rate': current_entry['hourly_rate'],
                'project_name': current_entry['project_name'],
                'task_name': current_entry['task_name'],
                'punch_in': punch_in_time,
                'punch_out': punch_out_time
            }
            
            logger.info(f"Punch out complété - Entry: {current_entry['id']}, Heures: {total_hours:.2f}, Coût: {total_cost:.2f}$ CAD")
            return session_details
            
        except Exception as e:
            logger.error(f"Erreur punch out: {e}")
            raise
    
    def get_employee_time_entries(self, employee_id: int, limit: int = 50, date_filter: str = None) -> List[Dict]:
        """Récupère les entrées d'un employé avec filtres avancés"""
        try:
            base_query = '''
                SELECT te.*, p.nom_projet as project_name, p.client_nom_cache as client_name,
                       o.description as task_name, o.sequence_number,
                       wc.nom as work_center_name
                FROM time_entries te
                JOIN projects p ON te.project_id = p.id
                LEFT JOIN operations o ON te.operation_id = o.id
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE te.employee_id = ?
            '''
            
            params = [employee_id]
            
            if date_filter:
                base_query += ' AND DATE(te.punch_in) = ?'
                params.append(date_filter)
            
            base_query += ' ORDER BY te.punch_in DESC LIMIT ?'
            params.append(limit)
            
            rows = self.db.execute_query(base_query, tuple(params))
            
            entries = []
            for row in rows:
                entry = dict(row)
                entry['task_name'] = entry['task_name'] or 'Tâche générale'
                entry['client_name'] = entry['client_name'] or 'Client Inconnu'
                
                # Formater les dates pour l'affichage
                punch_in = datetime.fromisoformat(entry['punch_in'])
                entry['punch_in_formatted'] = punch_in.strftime('%Y-%m-%d %H:%M:%S')
                
                if entry['punch_out']:
                    punch_out = datetime.fromisoformat(entry['punch_out'])
                    entry['punch_out_formatted'] = punch_out.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    entry['punch_out_formatted'] = 'En cours...'
                    # Calculer le temps écoulé si en cours
                    elapsed = (datetime.now() - punch_in).total_seconds() / 3600
                    entry['elapsed_hours'] = elapsed
                
                entries.append(entry)
            
            return entries
        except Exception as e:
            logger.error(f"Erreur récupération historique employé {employee_id}: {e}")
            return []
    
    def get_daily_summary(self, date_str: str = None) -> List[Dict]:
        """Récupère le résumé quotidien avec détails enrichis"""
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        try:
            rows = self.db.execute_query('''
                SELECT 
                    e.id as employee_id,
                    e.prenom || ' ' || e.nom as employee_name,
                    e.poste, e.departement,
                    p.id as project_id,
                    p.nom_projet as project_name,
                    p.client_nom_cache as client_name,
                    COALESCE(o.description, 'Tâche générale') as task_name,
                    wc.nom as work_center_name,
                    COALESCE(SUM(te.total_hours), 0.0) as total_hours,
                    COALESCE(SUM(te.total_cost), 0.0) as total_cost,
                    COALESCE(AVG(te.hourly_rate), 0.0) as avg_hourly_rate,
                    COUNT(te.id) as entries_count,
                    MIN(te.punch_in) as first_punch_in,
                    MAX(te.punch_out) as last_punch_out
                FROM time_entries te
                JOIN employees e ON te.employee_id = e.id
                JOIN projects p ON te.project_id = p.id
                LEFT JOIN operations o ON te.operation_id = o.id
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE DATE(te.punch_in) = ? AND te.total_cost IS NOT NULL
                GROUP BY e.id, p.id, o.id
                ORDER BY e.prenom, e.nom, p.nom_projet
            ''', (date_str,))
            
            summary = []
            for row in rows:
                item = dict(row)
                item['client_name'] = item['client_name'] or 'Client Inconnu'
                summary.append(item)
            
            return summary
        except Exception as e:
            logger.error(f"Erreur résumé quotidien {date_str}: {e}")
            return []
    
    def get_project_revenue_summary(self, project_id: int = None, period_days: int = 30) -> List[Dict]:
        """Résumé des revenus par projet avec période configurable"""
        try:
            # Date de début pour la période
            start_date = (datetime.now() - timedelta(days=period_days)).strftime('%Y-%m-%d')
            
            if project_id:
                query = '''
                    SELECT 
                        p.id as project_id,
                        p.nom_projet as project_name,
                        p.client_nom_cache as client_name,
                        p.prix_estime as estimated_price,
                        COALESCE(SUM(te.total_hours), 0.0) as total_hours,
                        COALESCE(SUM(te.total_cost), 0.0) as total_revenue,
                        COALESCE(AVG(te.hourly_rate), 0.0) as avg_hourly_rate,
                        COUNT(DISTINCT te.employee_id) as employees_count,
                        COUNT(te.id) as entries_count,
                        MIN(te.punch_in) as first_entry,
                        MAX(te.punch_out) as last_entry
                    FROM time_entries te
                    JOIN projects p ON te.project_id = p.id
                    WHERE p.id = ? AND te.total_cost IS NOT NULL 
                    AND DATE(te.punch_in) >= ?
                    GROUP BY p.id
                '''
                params = (project_id, start_date)
            else:
                query = '''
                    SELECT 
                        p.id as project_id,
                        p.nom_projet as project_name,
                        p.client_nom_cache as client_name,
                        p.prix_estime as estimated_price,
                        COALESCE(SUM(te.total_hours), 0.0) as total_hours,
                        COALESCE(SUM(te.total_cost), 0.0) as total_revenue,
                        COALESCE(AVG(te.hourly_rate), 0.0) as avg_hourly_rate,
                        COUNT(DISTINCT te.employee_id) as employees_count,
                        COUNT(te.id) as entries_count,
                        MIN(te.punch_in) as first_entry,
                        MAX(te.punch_out) as last_entry
                    FROM time_entries te
                    JOIN projects p ON te.project_id = p.id
                    WHERE te.total_cost IS NOT NULL AND DATE(te.punch_in) >= ?
                    GROUP BY p.id
                    ORDER BY total_revenue DESC
                '''
                params = (start_date,)
            
            rows = self.db.execute_query(query, params)
            
            summary = []
            for row in rows:
                item = dict(row)
                item['client_name'] = item['client_name'] or 'Client Inconnu'
                
                # Calcul du ratio revenus/estimation
                if item['estimated_price'] and item['estimated_price'] > 0:
                    item['revenue_ratio'] = (item['total_revenue'] / item['estimated_price']) * 100
                else:
                    item['revenue_ratio'] = 0
                
                summary.append(item)
            
            return summary
            
        except Exception as e:
            logger.error(f"Erreur résumé revenus: {e}")
            return []
    
    def get_timetracker_statistics(self) -> Dict:
        """Statistiques globales TimeTracker enrichies"""
        try:
            stats = {}
            
            # Employés actifs dans l'ERP
            emp_result = self.db.execute_query("SELECT COUNT(*) as count FROM employees WHERE statut = 'ACTIF'")
            stats['total_employees'] = emp_result[0]['count'] if emp_result else 0
            
            # Pointages actifs (en cours)
            active_result = self.db.execute_query("SELECT COUNT(*) as count FROM time_entries WHERE punch_out IS NULL")
            stats['active_entries'] = active_result[0]['count'] if active_result else 0
            
            # Statistiques du jour
            today = datetime.now().strftime('%Y-%m-%d')
            daily_result = self.db.execute_query('''
                SELECT 
                    COALESCE(SUM(total_hours), 0.0) as hours,
                    COALESCE(SUM(total_cost), 0.0) as revenue,
                    COUNT(DISTINCT employee_id) as unique_employees,
                    COUNT(*) as total_entries
                FROM time_entries 
                WHERE DATE(punch_in) = ? AND total_cost IS NOT NULL
            ''', (today,))
            
            if daily_result:
                stats.update({
                    'total_hours_today': daily_result[0]['hours'],
                    'total_revenue_today': daily_result[0]['revenue'],
                    'active_employees_today': daily_result[0]['unique_employees'],
                    'total_entries_today': daily_result[0]['total_entries']
                })
            
            # Statistiques globales (dernier mois)
            month_start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            monthly_result = self.db.execute_query('''
                SELECT 
                    COALESCE(SUM(total_hours), 0.0) as monthly_hours,
                    COALESCE(SUM(total_cost), 0.0) as monthly_revenue,
                    COUNT(DISTINCT employee_id) as active_employees_month,
                    COUNT(DISTINCT project_id) as active_projects_month
                FROM time_entries 
                WHERE DATE(punch_in) >= ? AND total_cost IS NOT NULL
            ''', (month_start,))
            
            if monthly_result:
                stats.update({
                    'monthly_hours': monthly_result[0]['monthly_hours'],
                    'monthly_revenue': monthly_result[0]['monthly_revenue'],
                    'active_employees_month': monthly_result[0]['active_employees_month'],
                    'active_projects_month': monthly_result[0]['active_projects_month']
                })
            
            # Taux horaire moyen
            if stats.get('total_hours_today', 0) > 0:
                stats['avg_hourly_rate_today'] = stats['total_revenue_today'] / stats['total_hours_today']
            else:
                stats['avg_hourly_rate_today'] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur statistiques TimeTracker: {e}")
            return {}
    
    def get_work_center_productivity(self) -> List[Dict]:
        """Analyse de productivité par poste de travail"""
        try:
            rows = self.db.execute_query('''
                SELECT 
                    wc.id, wc.nom as work_center_name, wc.departement, wc.categorie,
                    wc.capacite_theorique, wc.cout_horaire,
                    COALESCE(SUM(te.total_hours), 0) as actual_hours,
                    COALESCE(SUM(te.total_cost), 0) as total_revenue,
                    COUNT(DISTINCT te.employee_id) as unique_employees,
                    COUNT(te.id) as total_entries
                FROM work_centers wc
                LEFT JOIN operations o ON wc.id = o.work_center_id
                LEFT JOIN time_entries te ON o.id = te.operation_id AND te.total_cost IS NOT NULL
                GROUP BY wc.id
                HAVING actual_hours > 0
                ORDER BY total_revenue DESC
            ''')
            
            productivity = []
            for row in rows:
                item = dict(row)
                
                # Calcul du taux d'utilisation (si capacité théorique disponible)
                if item['capacite_theorique'] and item['capacite_theorique'] > 0:
                    # Utilisation sur 30 jours (approximation)
                    theoretical_capacity_month = item['capacite_theorique'] * 30
                    item['utilization_rate'] = min(100, (item['actual_hours'] / theoretical_capacity_month) * 100)
                else:
                    item['utilization_rate'] = 0
                
                productivity.append(item)
            
            return productivity
            
        except Exception as e:
            logger.error(f"Erreur analyse productivité: {e}")
            return []

    # --- NOUVELLES MÉTHODES POUR INTÉGRATION BONS DE TRAVAIL (BT) ---
    
    def get_bt_assignes_employe_timetracker(self, employee_id: int) -> List[Dict]:
        """Récupère les Bons de Travail (BT) assignés à un employé."""
        # Le code complet pour cette méthode est attendu depuis timetracker_bt_integration.py
        logger.warning("La méthode 'get_bt_assignes_employe_timetracker' n'est pas encore implémentée.")
        return []

    def demarrer_pointage_bt(self, employee_id: int, bt_id: int, operation_id: int, notes: str = "") -> Optional[int]:
        """Démarre un pointage pour une opération d'un Bon de Travail (BT)."""
        # Le code complet pour cette méthode est attendu depuis timetracker_bt_integration.py
        logger.warning("La méthode 'demarrer_pointage_bt' n'est pas encore implémentée.")
        return None

    def terminer_pointage_avec_sync_bt(self, employee_id: int, notes: str = "") -> Dict:
        """Termine le pointage actuel et synchronise avec le Bon de Travail (BT)."""
        # Le code complet pour cette méthode est attendu depuis timetracker_bt_integration.py
        logger.warning("La méthode 'terminer_pointage_avec_sync_bt' n'est pas encore implémentée.")
        raise NotImplementedError("La synchronisation avec le Bon de Travail n'est pas implémentée.")

    def get_dashboard_bt_integration(self) -> Dict[str, Any]:
        """Récupère les données pour le dashboard d'intégration des BT."""
        # Le code complet pour cette méthode est attendu depuis timetracker_bt_integration.py
        logger.warning("La méthode 'get_dashboard_bt_integration' n'est pas encore implémentée.")
        return {}


def show_timetracker_interface_with_bt_integration():
    """
    Interface principale TimeTracker intégrée dans l'ERP DG Inc.
    Version SQLite optimisée avec fonctionnalités avancées
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
        <p style='margin: 5px 0 0 0; text-align: center; opacity: 0.9;'>🗄️ Architecture SQLite Unifiée • Intégration Complète</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Statistiques en temps réel enrichies
    stats = tt.get_timetracker_statistics()
    
    # Première ligne de métriques
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Employés ERP", stats.get('total_employees', 0))
    with col2:
        st.metric("🟢 Pointages Actifs", stats.get('active_entries', 0))
    with col3:
        st.metric("⏱️ Heures Aujourd'hui", f"{stats.get('total_hours_today', 0):.1f}h")
    with col4:
        st.metric("💰 Revenus Aujourd'hui", f"{stats.get('total_revenue_today', 0):.0f}$ CAD")
    
    # Deuxième ligne de métriques (mensuel)
    if stats.get('monthly_revenue', 0) > 0:
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric("📅 Revenus Mensuel", f"{stats.get('monthly_revenue', 0):.0f}$ CAD")
        with col6:
            st.metric("⏰ Heures Mensuel", f"{stats.get('monthly_hours', 0):.0f}h")
        with col7:
            st.metric("👥 Employés Actifs/Mois", stats.get('active_employees_month', 0))
        with col8:
            avg_rate = stats.get('avg_hourly_rate_today', 0)
            st.metric("💵 Taux Moy. Jour", f"{avg_rate:.0f}$/h" if avg_rate > 0 else "N/A")
    
    # Navigation TimeTracker enrichie
    tab_pointage, tab_analytics, tab_productivity, tab_admin, tab_system = st.tabs([
        "🕐 Pointage Employés", "📊 Analytics & Rapports", "🏭 Productivité", "⚙️ Administration", "ℹ️ Système"
    ])
    
    with tab_pointage:
        show_employee_timetracking_interface(tt)
    
    with tab_analytics:
        show_analytics_interface(tt)
    
    with tab_productivity:
        show_productivity_interface(tt)
    
    with tab_admin:
        show_admin_interface(tt)
    
    with tab_system:
        show_system_interface()


def show_employee_timetracking_interface(tt: TimeTrackerERP):
    """Interface de pointage pour employés avec fonctionnalités avancées"""
    
    st.markdown("### 👤 Interface de Pointage Avancée")
    
    # Récupération des employés depuis l'ERP
    employees = tt.get_all_employees()
    
    if not employees:
        st.warning("⚠️ Aucun employé actif trouvé dans l'ERP.")
        st.info("Veuillez ajouter des employés dans le module RH de l'ERP.")
        return
    
    # Mode de sélection d'employé
    selection_mode = st.radio("Mode de sélection:", ["Par employé", "Vue rapide équipe"], horizontal=True)
    
    if selection_mode == "Vue rapide équipe":
        show_team_quick_view(tt, employees)
        return
    
    # Sélecteur d'employé enrichi
    employee_options = {emp['id']: emp['full_name_with_role'] for emp in employees}
    
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
    
    # Interface de pointage enrichie
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Informations employé enrichies
        st.markdown(f"""
        <div class='info-card'>
            <h4>👤 {employee['name']}</h4>
            <p><strong>💼 Poste:</strong> {employee.get('poste', 'N/A')}</p>
            <p><strong>🏢 Département:</strong> {employee.get('departement', 'N/A')}</p>
            <p><strong>📧 Email:</strong> {employee.get('email', 'N/A')}</p>
            <p><strong>🆔 Code ERP:</strong> {employee['employee_code']}</p>
            <p><strong>📋 Projets Assignés:</strong> {employee.get('projets_assignes', 0)}</p>
            <p><strong>📊 Charge Travail:</strong> {employee.get('charge_travail', 'N/A')}%</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Statistiques TimeTracker de l'employé
        if employee.get('timetracker_total_entries', 0) > 0:
            st.markdown(f"""
            <div class='info-card' style='background: linear-gradient(135deg, #e0f2fe 0%, #b3e5fc 100%);'>
                <h5>📊 Statistiques TimeTracker</h5>
                <p><strong>⏱️ Total Heures:</strong> {employee.get('timetracker_total_hours', 0):.1f}h</p>
                <p><strong>💰 Total Revenus:</strong> {employee.get('timetracker_total_revenue', 0):.0f}$ CAD</p>
                <p><strong>📈 Taux Moyen:</strong> {employee.get('timetracker_avg_rate', 0):.0f}$/h</p>
                <p><strong>📝 Pointages:</strong> {employee.get('timetracker_total_entries', 0)}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        if current_entry:
            # Employé pointé - afficher le status enrichi
            punch_in_time = datetime.fromisoformat(current_entry['punch_in'])
            elapsed_hours = current_entry['elapsed_hours']
            estimated_cost = current_entry['estimated_cost']
            
            # Couleur d'alerte si session très longue
            alert_style = ""
            if elapsed_hours > 12:
                alert_style = "border-left: 4px solid #ef4444; background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);"
            elif elapsed_hours > 8:
                alert_style = "border-left: 4px solid #f59e0b; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);"
            else:
                alert_style = "border-left: 4px solid #10b981; background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);"
            
            st.markdown(f"""
            <div class='info-card' style='{alert_style}'>
                <h4>🟢 POINTÉ ACTUELLEMENT</h4>
                <p><strong>📋 Projet:</strong> {current_entry['project_name']}</p>
                <p><strong>👤 Client:</strong> {current_entry['client_name']}</p>
                <p><strong>🔧 Tâche:</strong> {current_entry['task_name']}</p>
                <p><strong>🏭 Poste:</strong> {current_entry.get('work_center_name', 'N/A')}</p>
                <p><strong>🕐 Début:</strong> {punch_in_time.strftime('%H:%M:%S')}</p>
                <p><strong>⏱️ Durée:</strong> {elapsed_hours:.2f}h</p>
                <p><strong>💰 Coût estimé:</strong> {estimated_cost:.2f}$ CAD</p>
                <p><strong>💵 Taux:</strong> {current_entry['hourly_rate']:.2f}$/h</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Alerte si session très longue
            if elapsed_hours > 12:
                st.error("⚠️ Session de travail très longue (>12h). Vérifiez si l'employé a oublié de pointer.")
            elif elapsed_hours > 8:
                st.warning("⏰ Session de travail longue (>8h). Pensez à faire des pauses.")
            
            # Formulaire punch out enrichi
            st.markdown("#### 🔴 Terminer le pointage")
            with st.form("punch_out_form"):
                notes_out = st.text_area(
                    "📝 Notes de fin (optionnel):", 
                    placeholder="Travail accompli, difficultés rencontrées, prochaines étapes...",
                    height=100
                )
                
                punch_out_col1, punch_out_col2 = st.columns(2)
                with punch_out_col1:
                    if st.form_submit_button("🔴 PUNCH OUT", use_container_width=True):
                        try:
                            session_details = tt.punch_out(selected_employee_id, notes_out)
                            
                            st.success(f"""
                            ✅ **Punch out enregistré !**
                            
                            📊 **Résumé de session:**
                            - ⏱️ Durée: {session_details['total_hours']:.2f}h
                            - 💰 Coût: {session_details['total_cost']:.2f}$ CAD
                            - 💵 Taux: {session_details['hourly_rate']:.2f}$/h
                            - 📋 Projet: {session_details['project_name']}
                            - 🔧 Tâche: {session_details['task_name']}
                            """)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erreur punch out: {str(e)}")
                
                with punch_out_col2:
                    if st.form_submit_button("⏸️ Pause Déjeuner", use_container_width=True):
                        try:
                            session_details = tt.punch_out(selected_employee_id, f"Pause déjeuner. {notes_out}".strip())
                            st.info(f"⏸️ Pause déjeuner enregistrée. Durée avant pause: {session_details['total_hours']:.2f}h")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erreur pause: {str(e)}")
        
        else:
            # Employé non pointé - interface punch in enrichie
            st.markdown("""
            <div class='info-card' style='border-left: 4px solid #f59e0b; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);'>
                <h4>🟡 PRÊT À POINTER</h4>
                <p>Sélectionnez un projet et une tâche pour commencer le pointage</p>
                <p><small>💡 Le taux horaire sera automatiquement déterminé par l'opération sélectionnée</small></p>
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
            # Sélection du projet enrichie
            project_options = {p['id']: f"{p['project_name']} - {p['client_name']} (H:{p['timetracker_hours']:.1f} | Rev:{p['timetracker_revenue']:.0f}$ CAD)" for p in projects}
            selected_project_id = st.selectbox(
                "📋 Projet:",
                options=list(project_options.keys()),
                format_func=lambda x: project_options[x],
                help="Affichage: Nom - Client (Heures TimeTracker | Revenus)"
            )
            
            # Affichage des détails du projet sélectionné
            if selected_project_id:
                selected_project = next(p for p in projects if p['id'] == selected_project_id)
                
                proj_col1, proj_col2, proj_col3 = st.columns(3)
                with proj_col1:
                    st.metric("📊 BD-FT Estimé", f"{selected_project.get('bd_ft_estime', 0):.1f}h")
                with proj_col2:
                    st.metric("💰 Prix Estimé", f"{selected_project.get('prix_estime', 0):.0f}$ CAD")
                with proj_col3:
                    st.metric("🔧 Opérations", selected_project.get('total_operations', 0))
                
                # Sélection de l'opération/tâche enrichie
                operations = tt.get_project_operations(selected_project_id)
                selected_operation_id = None
                
                if operations:
                    operation_options = {
                        op['id']: f"OP{op['sequence_number']:02d} - {op['task_name']} ({op['hourly_rate']:.0f}$/h) [{op['completion_percentage']:.0f}% completé]" 
                        for op in operations
                    }
                    selected_operation_id = st.selectbox(
                        "🔧 Opération/Tâche:",
                        options=[None] + list(operation_options.keys()),
                        format_func=lambda x: "🔧 Tâche générale (95$/h)" if x is None else operation_options[x],
                        help="Sélectionnez une opération spécifique ou laissez vide pour tâche générale"
                    )
                    
                    # Affichage des détails de l'opération
                    if selected_operation_id:
                        selected_operation = next(op for op in operations if op['id'] == selected_operation_id)
                        
                        op_col1, op_col2, op_col3 = st.columns(3)
                        with op_col1:
                            st.metric("⏱️ Temps Estimé", f"{selected_operation['estimated_hours']:.1f}h")
                        with op_col2:
                            st.metric("📊 Temps Réel", f"{selected_operation['actual_hours']:.1f}h")
                        with op_col3:
                            completion = selected_operation['completion_percentage']
                            st.metric("✅ Progression", f"{completion:.0f}%")
                        
                        # Barre de progression
                        progress_color = "🔴" if completion > 100 else "🟡" if completion > 80 else "🟢"
                        st.progress(min(1.0, completion / 100), text=f"{progress_color} Progression: {completion:.1f}%")
                else:
                    st.info("Aucune opération définie pour ce projet. Pointage général disponible.")
            
            # Notes de début enrichies
            notes_in = st.text_area(
                "📝 Notes de début (optionnel):", 
                placeholder="Objectifs de la session, plan de travail, outils nécessaires...",
                height=80
            )
            
            # Boutons d'action
            punch_in_col1, punch_in_col2, punch_in_col3 = st.columns(3)
            with punch_in_col1:
                if st.form_submit_button("🟢 PUNCH IN", use_container_width=True):
                    if selected_project_id:
                        try:
                            entry_id = tt.punch_in(selected_employee_id, selected_project_id, selected_operation_id, notes_in)
                            
                            # Déterminer le taux horaire qui sera appliqué
                            if selected_operation_id:
                                selected_operation = next(op for op in operations if op['id'] == selected_operation_id)
                                rate = selected_operation['hourly_rate']
                                task_name = selected_operation['task_name']
                            else:
                                rate = 95.0
                                task_name = "Tâche générale"
                            
                            st.success(f"""
                            ✅ **Punch in enregistré !**
                            
                            📊 **Détails:**
                            - 🆔 Entry ID: {entry_id}
                            - 📋 Projet: {selected_project['project_name']}
                            - 🔧 Tâche: {task_name}
                            - 💵 Taux: {rate:.2f}$/h
                            - 🕐 Heure début: {datetime.now().strftime('%H:%M:%S')}
                            """)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erreur punch in: {str(e)}")
                    else:
                        st.error("Veuillez sélectionner un projet.")
            
            with punch_in_col2:
                if st.form_submit_button("📋 Voir Détails Projet", use_container_width=True):
                    if selected_project_id:
                        # Stockage pour affichage des détails
                        st.session_state.timetracker_project_details = selected_project_id
                        st.info("💡 Détails du projet affichés ci-dessous.")
            
            with punch_in_col3:
                if st.form_submit_button("🔄 Rafraîchir Projets", use_container_width=True):
                    st.cache_data.clear()
                    st.success("🔄 Liste des projets mise à jour.")
                    st.rerun()
    
    # Affichage des détails de projet si demandé
    if st.session_state.get('timetracker_project_details'):
        show_project_details_for_timetracker(tt, st.session_state.timetracker_project_details)
    
    # Historique récent enrichi
    st.markdown("---")
    st.markdown("#### 📊 Historique Récent")
    
    # Filtres pour l'historique
    hist_col1, hist_col2, hist_col3 = st.columns(3)
    with hist_col1:
        limit_entries = st.selectbox("Nombre d'entrées:", [10, 25, 50, 100], index=0)
    with hist_col2:
        date_filter = st.date_input("Filtrer par date (optionnel):", value=None)
    with hist_col3:
        if st.button("🔄 Actualiser Historique"):
            st.rerun()
    
    date_filter_str = date_filter.strftime('%Y-%m-%d') if date_filter else None
    recent_entries = tt.get_employee_time_entries(selected_employee_id, limit_entries, date_filter_str)
    
    if recent_entries:
        df_history = []
        total_hours_shown = 0
        total_cost_shown = 0
        
        for entry in recent_entries:
            punch_in = datetime.fromisoformat(entry['punch_in'])
            
            if entry['punch_out']:
                punch_out_str = datetime.fromisoformat(entry['punch_out']).strftime('%H:%M:%S')
                duration_str = f"{entry['total_hours']:.2f}h"
                cost_str = f"{entry['total_cost']:.2f}$ CAD"
                status = "✅ Terminé"
                total_hours_shown += entry['total_hours']
                total_cost_shown += entry['total_cost']
            else:
                punch_out_str = "En cours..."
                elapsed = entry.get('elapsed_hours', 0)
                duration_str = f"{elapsed:.2f}h (en cours)"
                cost_str = f"{elapsed * entry['hourly_rate']:.2f}$ CAD (estimé)"
                status = "🟢 En cours"
            
            df_history.append({
                '📅 Date': punch_in.strftime('%Y-%m-%d'),
                '🕐 Début': punch_in.strftime('%H:%M:%S'),
                '🕑 Fin': punch_out_str,
                '📋 Projet': entry['project_name'],
                '👤 Client': entry['client_name'],
                '🔧 Tâche': entry['task_name'],
                '🏭 Poste': entry.get('work_center_name', 'N/A'),
                '⏱️ Durée': duration_str,
                '💰 Coût': cost_str,
                '🚦 Statut': status
            })
        
        # Résumé de l'historique affiché
        hist_summary_col1, hist_summary_col2, hist_summary_col3 = st.columns(3)
        with hist_summary_col1:
            st.metric("📊 Entrées Affichées", len(df_history))
        with hist_summary_col2:
            st.metric("⏱️ Total Heures", f"{total_hours_shown:.1f}h")
        with hist_summary_col3:
            st.metric("💰 Total Revenus", f"{total_cost_shown:.0f}$ CAD")
        
        # Tableau enrichi
        st.dataframe(pd.DataFrame(df_history), use_container_width=True)
        
        # Graphique de tendance si assez de données
        if len(recent_entries) >= 5:
            show_employee_trend_chart(recent_entries)
    else:
        message = "Aucun historique de pointage"
        if date_filter_str:
            message += f" pour le {date_filter_str}"
        st.info(message + ".")


def show_team_quick_view(tt: TimeTrackerERP, employees: List[Dict]):
    """Vue rapide de l'équipe - statuts de pointage"""
    
    st.markdown("#### 👥 Vue d'Équipe - Statuts de Pointage")
    
    # Répartition par département
    dept_employees = {}
    for emp in employees:
        dept = emp.get('departement', 'Non Assigné')
        if dept not in dept_employees:
            dept_employees[dept] = []
        dept_employees[dept].append(emp)
    
    for dept, dept_emps in dept_employees.items():
        with st.expander(f"🏢 {dept} ({len(dept_emps)} employés)", expanded=True):
            
            # Grille d'employés par département
            cols = st.columns(min(4, len(dept_emps)))
            
            for i, emp in enumerate(dept_emps):
                with cols[i % 4]:
                    current_entry = tt.get_employee_current_entry(emp['id'])
                    
                    if current_entry:
                        # Employé pointé
                        elapsed = current_entry['elapsed_hours']
                        color = "#10b981" if elapsed < 8 else "#f59e0b" if elapsed < 12 else "#ef4444"
                        
                        st.markdown(f"""
                        <div style='border: 2px solid {color}; border-radius: 8px; padding: 10px; margin-bottom: 10px; background: linear-gradient(135deg, {color}20, {color}10);'>
                            <h6 style='margin: 0; color: {color};'>🟢 {emp['name']}</h6>
                            <p style='margin: 2px 0; font-size: 0.8em;'><strong>Projet:</strong> {current_entry['project_name'][:20]}...</p>
                            <p style='margin: 2px 0; font-size: 0.8em;'><strong>Durée:</strong> {elapsed:.1f}h</p>
                            <p style='margin: 0; font-size: 0.8em;'><strong>Coût:</strong> {current_entry['estimated_cost']:.0f}$ CAD</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Employé libre
                        st.markdown(f"""
                        <div style='border: 2px solid #94a3b8; border-radius: 8px; padding: 10px; margin-bottom: 10px; background: #f8fafc;'>
                            <h6 style='margin: 0; color: #64748b;'>🟡 {emp['name']}</h6>
                            <p style='margin: 2px 0; font-size: 0.8em;'>Libre</p>
                            <p style='margin: 0; font-size: 0.8em;'>{emp.get('poste', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)


def show_project_details_for_timetracker(tt: TimeTrackerERP, project_id: int):
    """Affichage des détails d'un projet dans le contexte TimeTracker"""
    
    projects = tt.get_active_projects()
    project = next((p for p in projects if p['id'] == project_id), None)
    
    if not project:
        st.error("Projet non trouvé.")
        return
    
    with st.expander(f"📋 Détails: {project['project_name']}", expanded=True):
        # Informations générales
        det_col1, det_col2, det_col3 = st.columns(3)
        with det_col1:
            st.metric("💰 Prix Estimé", f"{project.get('prix_estime', 0):.0f}$ CAD")
        with det_col2:
            st.metric("⏱️ BD-FT Estimé", f"{project.get('bd_ft_estime', 0):.1f}h")
        with det_col3:
            st.metric("📅 Date Prévue", project.get('date_prevu', 'N/A'))
        
        # Progression TimeTracker
        tt_col1, tt_col2, tt_col3 = st.columns(3)
        with tt_col1:
            st.metric("⏱️ Heures TimeTracker", f"{project['timetracker_hours']:.1f}h")
        with tt_col2:
            st.metric("💰 Revenus TimeTracker", f"{project['timetracker_revenue']:.0f}$ CAD")
        with tt_col3:
            if project.get('bd_ft_estime', 0) > 0:
                progress_pct = (project['timetracker_hours'] / project['bd_ft_estime']) * 100
                st.metric("📊 Progression", f"{progress_pct:.1f}%")
        
        # Opérations du projet
        operations = tt.get_project_operations(project_id)
        if operations:
            st.markdown("##### 🔧 Opérations Disponibles")
            
            for op in operations:
                completion = op['completion_percentage']
                progress_color = "🔴" if completion > 100 else "🟡" if completion > 80 else "🟢"
                
                st.markdown(f"""
                **{op['task_name']}** ({op['hourly_rate']:.0f}$/h)
                - Estimé: {op['estimated_hours']:.1f}h | Réel: {op['actual_hours']:.1f}h | {progress_color} {completion:.0f}%
                """)
        
        if st.button("❌ Fermer Détails", key="close_project_details"):
            del st.session_state.timetracker_project_details
            st.rerun()


def show_employee_trend_chart(recent_entries: List[Dict]):
    """Graphique de tendance pour un employé"""
    
    st.markdown("##### 📈 Tendance des Heures")
    
    # Préparer les données pour le graphique
    completed_entries = [e for e in recent_entries if e.get('total_hours')]
    
    if len(completed_entries) >= 3:
        df_trend = pd.DataFrame([
            {
                'Date': datetime.fromisoformat(entry['punch_in']).date(),
                'Heures': entry['total_hours'],
                'Revenus': entry['total_cost'],
                'Projet': entry['project_name'][:15] + ('...' if len(entry['project_name']) > 15 else '')
            }
            for entry in completed_entries
        ])
        
        # Graphique des heures par jour
        fig = px.line(df_trend, x='Date', y='Heures', 
                     title="Évolution des Heures Travaillées",
                     hover_data=['Revenus', 'Projet'])
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='var(--text-color)'),
            title_x=0.5
        )
        st.plotly_chart(fig, use_container_width=True)


def show_analytics_interface(tt: TimeTrackerERP):
    """Interface d'analytics TimeTracker enrichie"""
    
    st.markdown("### 📊 Analytics & Rapports Avancés")
    
    # Période d'analyse configurable
    col_period1, col_period2, col_period3 = st.columns(3)
    with col_period1:
        period_preset = st.selectbox("Période prédéfinie:", 
                                   ["Personnalisée", "7 derniers jours", "30 derniers jours", "3 derniers mois"])
    
    if period_preset == "Personnalisée":
        with col_period2:
            start_date = st.date_input("📅 Date début:", datetime.now().date() - timedelta(days=30))
        with col_period3:
            end_date = st.date_input("📅 Date fin:", datetime.now().date())
    else:
        period_days = {"7 derniers jours": 7, "30 derniers jours": 30, "3 derniers mois": 90}[period_preset]
        start_date = datetime.now().date() - timedelta(days=period_days)
        end_date = datetime.now().date()
        
        with col_period2:
            st.metric("📅 Période", f"{period_days} jours")
        with col_period3:
            st.metric("📅 Du", f"{start_date} au {end_date}")
    
    # Revenus par projet enrichis
    st.markdown("#### 💰 Analyse des Revenus par Projet")
    
    period_days = (end_date - start_date).days
    project_revenues = tt.get_project_revenue_summary(period_days=period_days)
    
    if project_revenues:
        # Filtrage et validation des données
        valid_revenues = [rev for rev in project_revenues if rev.get('total_revenue', 0) > 0]
        
        if valid_revenues:
            # Métriques globales
            total_revenue_global = sum(rev['total_revenue'] for rev in valid_revenues)
            total_hours_global = sum(rev['total_hours'] for rev in valid_revenues)
            avg_hourly_rate = total_revenue_global / total_hours_global if total_hours_global > 0 else 0
            
            metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
            with metrics_col1:
                st.metric("💰 Revenus Total", f"{total_revenue_global:.0f}$ CAD")
            with metrics_col2:
                st.metric("⏱️ Heures Total", f"{total_hours_global:.1f}h")
            with metrics_col3:
                st.metric("💵 Taux Moyen", f"{avg_hourly_rate:.2f}$/h")
            with metrics_col4:
                st.metric("📋 Projets Actifs", len(valid_revenues))
            
            # Graphiques côte à côte
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                # Graphique en secteurs
                fig_pie = px.pie(
                    values=[rev['total_revenue'] for rev in valid_revenues],
                    names=[rev['project_name'][:20] + ('...' if len(rev['project_name']) > 20 else '') for rev in valid_revenues],
                    title="🥧 Répartition des Revenus"
                )
                fig_pie.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='var(--text-color)'),
                    title_x=0.5
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with chart_col2:
                # Graphique en barres horizontales
                fig_bar = px.bar(
                    y=[rev['project_name'][:25] + ('...' if len(rev['project_name']) > 25 else '') for rev in valid_revenues],
                    x=[rev['total_revenue'] for rev in valid_revenues],
                    orientation='h',
                    title="📊 Revenus par Projet",
                    labels={'x': 'Revenus (CAD)', 'y': 'Projets'}
                )
                fig_bar.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='var(--text-color)'),
                    title_x=0.5
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # Tableau détaillé enrichi
            st.markdown("##### 📋 Détail par Projet")
            df_revenues = []
            for rev in valid_revenues:
                revenue = rev['total_revenue']
                hours = rev['total_hours']
                estimated = rev.get('estimated_price', 0)
                
                # Calculs de performance
                efficiency = (hours / rev.get('employees_count', 1)) if rev.get('employees_count', 0) > 0 else hours
                revenue_per_employee = revenue / rev.get('employees_count', 1) if rev.get('employees_count', 0) > 0 else revenue
                
                df_revenues.append({
                    '📋 Projet': rev['project_name'],
                    '👤 Client': rev['client_name'],
                    '⏱️ Heures': f"{hours:.1f}h",
                    '💰 Revenus': f"{revenue:.0f}$ CAD",
                    '💵 Taux Moy.': f"{(revenue/hours):.2f}$/h" if hours > 0 else "N/A",
                    '👥 Employés': rev.get('employees_count', 0),
                    '📊 Efficacité': f"{efficiency:.1f}h/emp",
                    '💰 Rev./Emp.': f"{revenue_per_employee:.0f}$ CAD",
                    '📈 vs Estimé': f"{(revenue/estimated*100):.1f}%" if estimated > 0 else "N/A",
                    '📝 Pointages': rev.get('entries_count', 0)
                })
            
            st.dataframe(pd.DataFrame(df_revenues), use_container_width=True)
            
            # Analyse de performance
            st.markdown("##### 🎯 Analyse de Performance")
            
            # Top performers
            top_revenue = sorted(valid_revenues, key=lambda x: x['total_revenue'], reverse=True)[:3]
            top_efficiency = sorted(valid_revenues, key=lambda x: x['total_revenue']/x['total_hours'] if x['total_hours'] > 0 else 0, reverse=True)[:3]
            
            perf_col1, perf_col2 = st.columns(2)
            
            with perf_col1:
                st.markdown("**🏆 Top Revenus:**")
                for i, proj in enumerate(top_revenue, 1):
                    st.markdown(f"{i}. {proj['project_name'][:30]} - {proj['total_revenue']:.0f}$ CAD")
            
            with perf_col2:
                st.markdown("**⚡ Meilleure Efficacité ($/h):**")
                for i, proj in enumerate(top_efficiency, 1):
                    rate = proj['total_revenue']/proj['total_hours'] if proj['total_hours'] > 0 else 0
                    st.markdown(f"{i}. {proj['project_name'][:30]} - {rate:.2f}$/h")
    
    else:
        st.info(f"Aucune donnée de revenus TimeTracker pour la période du {start_date} au {end_date}.")
        st.markdown("💡 **Conseil**: Effectuez des pointages pour générer des données d'analyse.")


def show_productivity_interface(tt: TimeTrackerERP):
    """Interface d'analyse de productivité"""
    
    st.markdown("### 🏭 Analyse de Productivité")
    
    # Analyse par poste de travail
    st.markdown("#### 🔧 Productivité par Poste de Travail")
    
    work_center_data = tt.get_work_center_productivity()
    
    if work_center_data:
        # Métriques globales des postes
        total_wc_revenue = sum(wc['total_revenue'] for wc in work_center_data)
        total_wc_hours = sum(wc['actual_hours'] for wc in work_center_data)
        
        wc_col1, wc_col2, wc_col3, wc_col4 = st.columns(4)
        with wc_col1:
            st.metric("🏭 Postes Actifs", len(work_center_data))
        with wc_col2:
            st.metric("💰 Revenus Postes", f"{total_wc_revenue:.0f}$ CAD")
        with wc_col3:
            st.metric("⏱️ Heures Postes", f"{total_wc_hours:.1f}h")
        with wc_col4:
            avg_wc_rate = total_wc_revenue / total_wc_hours if total_wc_hours > 0 else 0
            st.metric("💵 Taux Moyen Postes", f"{avg_wc_rate:.2f}$/h")
        
        # Graphique de productivité par poste
        if len(work_center_data) > 1:
            prod_chart_col1, prod_chart_col2 = st.columns(2)
            
            with prod_chart_col1:
                fig_wc_revenue = px.bar(
                    x=[wc['work_center_name'][:15] + ('...' if len(wc['work_center_name']) > 15 else '') for wc in work_center_data],
                    y=[wc['total_revenue'] for wc in work_center_data],
                    title="💰 Revenus par Poste de Travail",
                    labels={'x': 'Postes', 'y': 'Revenus (CAD)'}
                )
                fig_wc_revenue.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='var(--text-color)'),
                    title_x=0.5
                )
                st.plotly_chart(fig_wc_revenue, use_container_width=True)
            
            with prod_chart_col2:
                # Taux d'utilisation
                utilization_data = [wc for wc in work_center_data if wc['utilization_rate'] > 0]
                if utilization_data:
                    fig_utilization = px.bar(
                        x=[wc['work_center_name'][:15] + ('...' if len(wc['work_center_name']) > 15 else '') for wc in utilization_data],
                        y=[wc['utilization_rate'] for wc in utilization_data],
                        title="📊 Taux d'Utilisation (%)",
                        labels={'x': 'Postes', 'y': 'Utilisation (%)'}
                    )
                    fig_utilization.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='var(--text-color)'),
                        title_x=0.5
                    )
                    st.plotly_chart(fig_utilization, use_container_width=True)
        
        # Tableau détaillé des postes
        df_work_centers = []
        for wc in work_center_data:
            df_work_centers.append({
                '🏭 Poste': wc['work_center_name'],
                '🏢 Département': wc['departement'],
                '🔧 Catégorie': wc['categorie'],
                '⏱️ Heures Réelles': f"{wc['actual_hours']:.1f}h",
                '💰 Revenus': f"{wc['total_revenue']:.0f}$ CAD",
                '💵 Taux Théorique': f"{wc['cout_horaire']:.2f}$/h",
                '📊 Utilisation': f"{wc['utilization_rate']:.1f}%" if wc['utilization_rate'] > 0 else "N/A",
                '👥 Employés': wc['unique_employees'],
                '📝 Pointages': wc['total_entries']
            })
        
        st.dataframe(pd.DataFrame(df_work_centers), use_container_width=True)
    
    else:
        st.info("Aucune donnée de productivité disponible pour les postes de travail.")
    
    # Analyse par employé
    st.markdown("---")
    st.markdown("#### 👥 Productivité par Employé")
    
    employees = tt.get_all_employees()
    employee_productivity = []
    
    for emp in employees[:10]:  # Limiter à 10 pour performance
        recent_entries = tt.get_employee_time_entries(emp['id'], 20)
        completed_entries = [e for e in recent_entries if e.get('total_hours')]
        
        if completed_entries:
            total_hours = sum(e['total_hours'] for e in completed_entries)
            total_revenue = sum(e['total_cost'] for e in completed_entries)
            avg_session = total_hours / len(completed_entries)
            
            employee_productivity.append({
                'name': emp['name'],
                'poste': emp.get('poste', 'N/A'),
                'departement': emp.get('departement', 'N/A'),
                'total_hours': total_hours,
                'total_revenue': total_revenue,
                'avg_hourly_rate': total_revenue / total_hours if total_hours > 0 else 0,
                'avg_session_hours': avg_session,
                'sessions_count': len(completed_entries)
            })
    
    if employee_productivity:
        # Top performers employés
        top_emp_revenue = sorted(employee_productivity, key=lambda x: x['total_revenue'], reverse=True)[:5]
        top_emp_efficiency = sorted(employee_productivity, key=lambda x: x['avg_hourly_rate'], reverse=True)[:5]
        
        emp_perf_col1, emp_perf_col2 = st.columns(2)
        
        with emp_perf_col1:
            st.markdown("**🏆 Top Revenus Employés:**")
            for i, emp in enumerate(top_emp_revenue, 1):
                st.markdown(f"{i}. {emp['name']} - {emp['total_revenue']:.0f}$ CAD ({emp['total_hours']:.1f}h)")
        
        with emp_perf_col2:
            st.markdown("**⚡ Meilleure Efficacité Employés:**")
            for i, emp in enumerate(top_emp_efficiency, 1):
                st.markdown(f"{i}. {emp['name']} - {emp['avg_hourly_rate']:.2f}$/h")


def show_admin_interface(tt: TimeTrackerERP):
    """Interface d'administration TimeTracker enrichie"""
    
    st.markdown("### ⚙️ Administration TimeTracker ERP")
    
    # Vue d'ensemble avec données ERP enrichies
    employees = tt.get_all_employees()
    projects = tt.get_active_projects()
    stats = tt.get_timetracker_statistics()
    
    # Métriques d'administration enrichies
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("👥 Employés ERP", len(employees))
    with col2:
        st.metric("📋 Projets Actifs", len(projects))
    with col3:
        currently_working = sum(1 for emp in employees if tt.get_employee_current_entry(emp['id']))
        st.metric("🟢 En Pointage", currently_working)
    with col4:
        st.metric("💰 Revenus Jour", f"{stats.get('total_revenue_today', 0):.0f}$ CAD")
    with col5:
        st.metric("📊 Pointages Jour", stats.get('total_entries_today', 0))
    
    # Alertes et notifications
    if currently_working > 0:
        st.info(f"ℹ️ {currently_working} employé(s) actuellement en pointage.")
    
    # Vérification des sessions longues
    long_sessions = []
    for emp in employees:
        current_entry = tt.get_employee_current_entry(emp['id'])
        if current_entry and current_entry['elapsed_hours'] > 10:
            long_sessions.append((emp['name'], current_entry['elapsed_hours']))
    
    if long_sessions:
        st.warning(f"⚠️ {len(long_sessions)} session(s) longue(s) détectée(s) (>10h):")
        for name, hours in long_sessions:
            st.write(f"- {name}: {hours:.1f}h")
    
    # Onglets d'administration enrichis
    admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
        "👥 Employés ERP", "📋 Projets ERP", "📊 Résumé Quotidien", "🔧 Outils Admin"
    ])
    
    with admin_tab1:
        show_admin_employees_tab(tt, employees)
    
    with admin_tab2:
        show_admin_projects_tab(tt, projects)
    
    with admin_tab3:
        show_admin_daily_summary_tab(tt)
    
    with admin_tab4:
        show_admin_tools_tab(tt)


def show_admin_employees_tab(tt: TimeTrackerERP, employees: List[Dict]):
    """Onglet administration des employés"""
    
    st.markdown("#### 👥 Gestion des Employés (Synchronisé ERP)")
    
    if employees:
        # Filtres
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            dept_filter = st.selectbox("Filtrer par département:", 
                                     ["Tous"] + list(set(emp.get('departement', 'N/A') for emp in employees)))
        with filter_col2:
            status_filter = st.selectbox("Filtrer par statut:", ["Tous", "En pointage", "Libre"])
        
        filtered_employees = employees
        if dept_filter != "Tous":
            filtered_employees = [emp for emp in filtered_employees if emp.get('departement') == dept_filter]
        
        df_employees = []
        for emp in filtered_employees:
            current_entry = tt.get_employee_current_entry(emp['id'])
            
            if status_filter == "En pointage" and not current_entry:
                continue
            elif status_filter == "Libre" and current_entry:
                continue
            
            status = "🟢 Pointé" if current_entry else "🟡 Libre"
            current_task = ""
            session_duration = ""
            estimated_cost = ""
            
            if current_entry:
                current_task = f"{current_entry['project_name'][:20]}... - {current_entry['task_name'][:15]}..."
                session_duration = f"{current_entry['elapsed_hours']:.1f}h"
                estimated_cost = f"{current_entry['estimated_cost']:.0f}$ CAD"
            
            df_employees.append({
                '🆔 ID': emp['id'],
                '👤 Nom': emp['name'],
                '💼 Poste': emp.get('poste', 'N/A'),
                '🏢 Département': emp.get('departement', 'N/A'),
                '📧 Email': emp.get('email', 'N/A'),
                '📊 Charge': f"{emp.get('charge_travail', 'N/A')}%",
                '🚦 Statut': status,
                '⏱️ Durée Session': session_duration or 'N/A',
                '💰 Coût Session': estimated_cost or 'N/A',
                '🔧 Tâche Actuelle': current_task or 'Aucune'
            })
        
        st.dataframe(pd.DataFrame(df_employees), use_container_width=True)
        st.info(f"ℹ️ {len(df_employees)} employé(s) affiché(s) - Données synchronisées depuis le module RH ERP")
    else:
        st.warning("Aucun employé actif dans l'ERP.")


def show_admin_projects_tab(tt: TimeTrackerERP, projects: List[Dict]):
    """Onglet administration des projets"""
    
    st.markdown("#### 📋 Gestion des Projets (Synchronisé ERP)")
    
    if projects:
        df_projects = []
        for proj in projects:
            operations = tt.get_project_operations(proj['id'])
            revenue_summary = tt.get_project_revenue_summary(proj['id'])
            total_revenue = revenue_summary[0]['total_revenue'] if revenue_summary else 0
            total_hours = revenue_summary[0]['total_hours'] if revenue_summary else 0
            
            # Calcul de progression
            estimated_hours = proj.get('bd_ft_estime', 0)
            progress = (total_hours / estimated_hours * 100) if estimated_hours > 0 else 0
            
            df_projects.append({
                '🆔 ID': proj['id'],
                '📋 Nom': proj['project_name'],
                '👤 Client': proj.get('client_name', 'N/A'),
                '🚦 Statut ERP': proj['statut'],
                '🔧 Opérations': len(operations),
                '⏱️ H. Estimées': f"{estimated_hours:.1f}h",
                '⏱️ H. Réelles': f"{total_hours:.1f}h",
                '📊 Progression': f"{progress:.1f}%",
                '💰 Revenus TT': f"{total_revenue:.0f}$ CAD",
                '💰 Prix Estimé': f"{proj.get('prix_estime', 0):.0f}$ CAD"
            })
        
        st.dataframe(pd.DataFrame(df_projects), use_container_width=True)
        st.info(f"ℹ️ {len(projects)} projet(s) actif(s) - Données synchronisées depuis le module Projets ERP")
    else:
        st.warning("Aucun projet actif dans l'ERP.")


def show_admin_daily_summary_tab(tt: TimeTrackerERP):
    """Onglet résumé quotidien enrichi"""
    
    st.markdown("#### 📊 Résumé Quotidien TimeTracker")
    
    # Sélecteur de date avec raccourcis
    date_col1, date_col2, date_col3 = st.columns(3)
    with date_col1:
        selected_date = st.date_input("📅 Date:", datetime.now().date())
    with date_col2:
        if st.button("📅 Aujourd'hui"):
            selected_date = datetime.now().date()
            st.rerun()
    with date_col3:
        if st.button("📅 Hier"):
            selected_date = datetime.now().date() - timedelta(days=1)
            st.rerun()
    
    date_str = selected_date.strftime('%Y-%m-%d')
    daily_summary = tt.get_daily_summary(date_str)
    
    if daily_summary:
        # Agrégation des données
        total_hours = sum(entry['total_hours'] for entry in daily_summary)
        total_revenue = sum(entry['total_cost'] for entry in daily_summary)
        unique_employees = len(set(entry['employee_id'] for entry in daily_summary))
        unique_projects = len(set(entry['project_id'] for entry in daily_summary))
        total_entries = sum(entry['entries_count'] for entry in daily_summary)
        
        # Métriques du jour
        day_col1, day_col2, day_col3, day_col4, day_col5 = st.columns(5)
        with day_col1:
            st.metric("⏱️ Total Heures", f"{total_hours:.1f}h")
        with day_col2:
            st.metric("💰 Total Revenus", f"{total_revenue:.0f}$ CAD")
        with day_col3:
            avg_rate = total_revenue / total_hours if total_hours > 0 else 0
            st.metric("💵 Taux Moyen", f"{avg_rate:.2f}$/h")
        with day_col4:
            st.metric("👥 Employés Actifs", unique_employees)
        with day_col5:
            st.metric("📋 Projets Touchés", unique_projects)
        
        # Tableau détaillé
        df_daily = []
        for entry in daily_summary:
            df_daily.append({
                '👤 Employé': entry['employee_name'],
                '💼 Poste': entry['poste'],
                '🏢 Département': entry['departement'],
                '📋 Projet': entry['project_name'],
                '👤 Client': entry['client_name'],
                '🔧 Tâche': entry['task_name'],
                '🏭 Poste Travail': entry.get('work_center_name', 'N/A'),
                '⏱️ Heures': f"{entry['total_hours']:.2f}h",
                '💰 Revenus': f"{entry['total_cost']:.2f}$ CAD",
                '💵 Taux': f"{entry['avg_hourly_rate']:.2f}$/h",
                '📊 Pointages': entry['entries_count']
            })
        
        st.dataframe(pd.DataFrame(df_daily), use_container_width=True)
        
        # Graphiques de répartition si assez de données
        if len(daily_summary) > 1:
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                # Répartition par employé
                emp_data = {}
                for entry in daily_summary:
                    emp_name = entry['employee_name']
                    emp_data[emp_name] = emp_data.get(emp_name, 0) + entry['total_hours']
                
                fig_emp = px.pie(values=list(emp_data.values()), names=list(emp_data.keys()),
                               title="⏱️ Répartition Heures par Employé")
                fig_emp.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='var(--text-color)'), title_x=0.5)
                st.plotly_chart(fig_emp, use_container_width=True)
            
            with chart_col2:
                # Répartition par projet
                proj_data = {}
                for entry in daily_summary:
                    proj_name = entry['project_name'][:20] + ('...' if len(entry['project_name']) > 20 else '')
                    proj_data[proj_name] = proj_data.get(proj_name, 0) + entry['total_cost']
                
                fig_proj = px.pie(values=list(proj_data.values()), names=list(proj_data.keys()),
                                title="💰 Répartition Revenus par Projet")
                fig_proj.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                     font=dict(color='var(--text-color)'), title_x=0.5)
                st.plotly_chart(fig_proj, use_container_width=True)
    
    else:
        st.info(f"Aucune activité TimeTracker enregistrée pour le {date_str}")
        st.markdown("💡 **Conseil**: Les employés doivent effectuer des pointages pour générer des données.")


def show_admin_tools_tab(tt: TimeTrackerERP):
    """Onglet outils d'administration"""
    
    st.markdown("#### 🔧 Outils d'Administration")
    
    # Section de maintenance
    with st.expander("🔧 Outils de Maintenance", expanded=True):
        
        maintenance_col1, maintenance_col2 = st.columns(2)
        
        with maintenance_col1:
            st.markdown("**🔍 Vérifications:**")
            
            if st.button("🔍 Détecter Sessions Orphelines", use_container_width=True):
                # Détecter les entrées sans punch_out depuis plus de 24h
                orphan_entries = tt.db.execute_query('''
                    SELECT te.id, e.prenom || ' ' || e.nom as employee_name, 
                           te.punch_in, p.nom_projet as project_name
                    FROM time_entries te
                    JOIN employees e ON te.employee_id = e.id
                    JOIN projects p ON te.project_id = p.id
                    WHERE te.punch_out IS NULL 
                    AND te.punch_in < datetime('now', '-1 day')
                ''')
                
                if orphan_entries:
                    st.warning(f"⚠️ {len(orphan_entries)} session(s) orpheline(s) détectée(s):")
                    for entry in orphan_entries:
                        st.write(f"- {entry['employee_name']}: {entry['project_name']} (depuis {entry['punch_in']})")
                else:
                    st.success("✅ Aucune session orpheline détectée.")
            
            if st.button("📊 Statistiques Base", use_container_width=True):
                # Statistiques de la base
                stats = {
                    'Total entrées': tt.db.get_table_count('time_entries'),
                    'Entrées complètes': len(tt.db.execute_query('SELECT * FROM time_entries WHERE punch_out IS NOT NULL')),
                    'Entrées en cours': len(tt.db.execute_query('SELECT * FROM time_entries WHERE punch_out IS NULL')),
                    'Employés avec pointages': len(tt.db.execute_query('SELECT DISTINCT employee_id FROM time_entries')),
                    'Projets avec pointages': len(tt.db.execute_query('SELECT DISTINCT project_id FROM time_entries'))
                }
                
                for key, value in stats.items():
                    st.metric(key, value)
        
        with maintenance_col2:
            st.markdown("**⚙️ Actions:**")
            
            if st.button("🧹 Nettoyer Sessions Vides", use_container_width=True):
                # Supprimer les entrées sans heures et très anciennes
                deleted = tt.db.execute_update('''
                    DELETE FROM time_entries 
                    WHERE total_hours IS NULL 
                    AND punch_out IS NULL 
                    AND punch_in < datetime('now', '-7 days')
                ''')
                
                if deleted > 0:
                    st.success(f"✅ {deleted} session(s) vide(s) supprimée(s).")
                else:
                    st.info("ℹ️ Aucune session vide à nettoyer.")
            
            if st.button("📈 Recalculer Totaux", use_container_width=True):
                # Recalculer les totaux pour les entrées complètes
                entries_to_fix = tt.db.execute_query('''
                    SELECT id, punch_in, punch_out, hourly_rate
                    FROM time_entries 
                    WHERE punch_out IS NOT NULL 
                    AND (total_hours IS NULL OR total_cost IS NULL)
                ''')
                
                fixed_count = 0
                for entry in entries_to_fix:
                    punch_in = datetime.fromisoformat(entry['punch_in'])
                    punch_out = datetime.fromisoformat(entry['punch_out'])
                    total_hours = (punch_out - punch_in).total_seconds() / 3600
                    total_cost = total_hours * entry['hourly_rate']
                    
                    tt.db.execute_update('''
                        UPDATE time_entries 
                        SET total_hours = ?, total_cost = ?
                        WHERE id = ?
                    ''', (total_hours, total_cost, entry['id']))
                    fixed_count += 1
                
                if fixed_count > 0:
                    st.success(f"✅ {fixed_count} entrée(s) recalculée(s).")
                else:
                    st.info("ℹ️ Tous les totaux sont corrects.")
    
    # Section d'export/import
    with st.expander("📤 Export/Import de Données", expanded=False):
        
        export_col1, export_col2 = st.columns(2)
        
        with export_col1:
            st.markdown("**📤 Export:**")
            
            # Sélection de la période d'export
            export_start = st.date_input("Date début export:", datetime.now().date() - timedelta(days=30))
            export_end = st.date_input("Date fin export:", datetime.now().date())
            
            if st.button("📤 Exporter CSV", use_container_width=True):
                # Requête d'export enrichie
                export_data = tt.db.execute_query('''
                    SELECT 
                        te.id, te.punch_in, te.punch_out, te.total_hours, te.total_cost, te.hourly_rate, te.notes,
                        e.prenom || ' ' || e.nom as employee_name, e.poste, e.departement,
                        p.nom_projet as project_name, p.client_nom_cache as client_name,
                        o.description as task_name, o.sequence_number,
                        wc.nom as work_center_name, wc.departement as work_center_dept
                    FROM time_entries te
                    JOIN employees e ON te.employee_id = e.id
                    JOIN projects p ON te.project_id = p.id
                    LEFT JOIN operations o ON te.operation_id = o.id
                    LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                    WHERE DATE(te.punch_in) BETWEEN ? AND ?
                    ORDER BY te.punch_in DESC
                ''', (export_start.strftime('%Y-%m-%d'), export_end.strftime('%Y-%m-%d')))
                
                if export_data:
                    df_export = pd.DataFrame([dict(row) for row in export_data])
                    csv = df_export.to_csv(index=False)
                    
                    st.download_button(
                        label="💾 Télécharger CSV",
                        data=csv,
                        file_name=f"timetracker_export_{export_start}_{export_end}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.success(f"✅ Export prêt: {len(export_data)} entrées")
                else:
                    st.warning("Aucune donnée à exporter pour cette période.")
        
        with export_col2:
            st.markdown("**ℹ️ Informations:**")
            st.info("""
            **Export inclut:**
            - Toutes les entrées de temps
            - Détails employés et projets
            - Informations postes de travail
            - Calculs de coûts
            
            **Format:** CSV compatible Excel
            """)


def show_system_interface():
    """Interface d'information système enrichie"""
    
    st.markdown("### ℹ️ Informations Système ERP")
    
    st.success("""
    🎉 **Architecture SQLite Unifiée Active !**
    
    TimeTracker est maintenant intégralement intégré dans la base ERP unifiée 
    `erp_production_dg.db`. Toutes les données sont synchronisées en temps réel.
    """)
    
    # Informations sur la base unifiée
    if 'erp_db' in st.session_state:
        db_info = st.session_state.erp_db.get_schema_info()
        
        # Métriques système
        sys_col1, sys_col2, sys_col3, sys_col4 = st.columns(4)
        with sys_col1:
            st.metric("📊 Taille Base", f"{db_info['file_size_mb']} MB")
        with sys_col2:
            st.metric("📋 Tables", len(db_info['tables']))
        with sys_col3:
            st.metric("📝 Enregistrements", f"{db_info['total_records']:,}")
        with sys_col4:
            timetracker_records = db_info['tables'].get('time_entries', 0)
            st.metric("⏱️ Entrées TimeTracker", timetracker_records)
        
        # Détails par module
        st.markdown("#### 📊 Répartition des Données par Module")
        
        modules_col1, modules_col2 = st.columns(2)
        
        with modules_col1:
            st.markdown("**🏭 Modules Production:**")
            st.metric("📋 Projets", db_info['tables'].get('projects', 0))
            st.metric("🔧 Opérations", db_info['tables'].get('operations', 0))
            st.metric("📦 Matériaux", db_info['tables'].get('materials', 0))
            st.metric("🏭 Postes Travail", db_info['tables'].get('work_centers', 0))
        
        with modules_col2:
            st.markdown("**👥 Modules Gestion:**")
            st.metric("👥 Employés", db_info['tables'].get('employees', 0))
            st.metric("🏢 Entreprises", db_info['tables'].get('companies', 0))
            st.metric("👤 Contacts", db_info['tables'].get('contacts', 0))
            st.metric("💬 Interactions", db_info['tables'].get('interactions', 0))
        
        # Validation de l'intégrité enrichie
        st.markdown("#### 🔍 Validation de l'Intégrité")
        
        integrity_col1, integrity_col2 = st.columns(2)
        
        with integrity_col1:
            if st.button("🔍 Vérifier Intégrité Complète", use_container_width=True):
                with st.spinner("Validation en cours..."):
                    integrity = st.session_state.erp_db.validate_integrity()
                    
                    if 'error' not in integrity:
                        st.markdown("**Résultats de validation:**")
                        all_good = True
                        for check, status in integrity.items():
                            icon = "✅" if status else "❌"
                            check_name = check.replace('_', ' ').title()
                            st.markdown(f"{icon} {check_name}")
                            if not status:
                                all_good = False
                        
                        if all_good:
                            st.success("🎉 Intégrité parfaite ! Architecture unifiée fonctionnelle.")
                        else:
                            st.warning("⚠️ Certaines vérifications ont échoué.")
                    else:
                        st.error(f"Erreur validation: {integrity['error']}")
        
        with integrity_col2:
            if st.button("📊 Statistiques Avancées", use_container_width=True):
                with st.spinner("Calcul des statistiques..."):
                    # Statistiques TimeTracker spécifiques
                    tt_stats = st.session_state.erp_db.execute_query('''
                        SELECT 
                            COUNT(*) as total_entries,
                            COUNT(CASE WHEN punch_out IS NOT NULL THEN 1 END) as completed_entries,
                            COUNT(CASE WHEN punch_out IS NULL THEN 1 END) as active_entries,
                            COALESCE(SUM(total_hours), 0) as total_hours,
                            COALESCE(SUM(total_cost), 0) as total_revenue,
                            COUNT(DISTINCT employee_id) as unique_employees,
                            COUNT(DISTINCT project_id) as unique_projects
                        FROM time_entries
                    ''')
                    
                    if tt_stats:
                        stats = dict(tt_stats[0])
                        st.markdown("**📊 Statistiques TimeTracker:**")
                        st.json({
                            "Entrées totales": stats['total_entries'],
                            "Entrées complétées": stats['completed_entries'],
                            "Entrées actives": stats['active_entries'],
                            "Heures totales": f"{stats['total_hours']:.1f}h",
                            "Revenus totaux": f"{stats['total_revenue']:.2f}$ CAD",
                            "Employés uniques": stats['unique_employees'],
                            "Projets uniques": stats['unique_projects']
                        })
        
        # Informations techniques détaillées
        with st.expander("🔧 Informations Techniques", expanded=False):
            
            tech_col1, tech_col2 = st.columns(2)
            
            with tech_col1:
                st.markdown("**🗄️ Base de Données:**")
                st.code(f"""
                Fichier: {db_info['database_file']}
                Taille: {db_info['file_size_mb']} MB
                Tables: {len(db_info['tables'])}
                Enregistrements: {db_info['total_records']:,}
                """)
                
                st.markdown("**⏱️ TimeTracker:**")
                timetracker_entries = db_info['tables'].get('time_entries', 0)
                st.code(f"""
                Entrées de temps: {timetracker_entries:,}
                Architecture: SQLite unifiée
                Synchronisation: Temps réel
                """)
            
            with tech_col2:
                st.markdown("**📋 Détail Tables:**")
                st.json(db_info['tables'])
    
    else:
        st.error("❌ Base ERP non disponible")
        st.info("Veuillez redémarrer l'application ERP.")


# Fonctions utilitaires conservées pour compatibilité
def hash_password(password: str) -> str:
    """Hash un mot de passe avec SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Vérifie un mot de passe contre son hash"""
    return hash_password(password) == hashed


# Point d'entrée principal
if __name__ == "__main__":
    st.error("❌ Ce module doit être importé par app.py")
    st.info("Lancez l'application ERP avec: streamlit run app.py")
