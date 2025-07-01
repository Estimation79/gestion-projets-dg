# timetracker_unified.py - Système de Pointage sur Opérations pour ERP Production DG Inc.
# VERSION OPÉRATIONS UNIQUEMENT - Pointage granulaire sur opérations des Bons de Travail
# Utilise directement erp_database.py pour un punch spécialisé et efficace
# Support complet du pointage sur opérations et tâches BT depuis formulaire_lignes

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
    Système de pointage spécialisé sur opérations
    Pointage granulaire sur opérations spécifiques des Bons de Travail
    Interface optimisée pour le suivi opérationnel en production
    Support complet des tâches BT depuis formulaire_lignes
    Avec méthodes de diagnostic intégrées
    """
    
    def __init__(self, db):
        self.db = db
        logger.info("TimeTracker Opérations initialisé")
    
    # =========================================================================
    # MÉTHODES CORE DE POINTAGE - OPÉRATIONS UNIQUEMENT
    # =========================================================================
    
    def punch_in(self, employee_id: int, project_id: int, notes: str = "") -> Optional[int]:
        """Commence un pointage pour un employé sur un projet (fallback)"""
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
            active_punch = self.get_active_punch_with_operation(employee_id)
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
            
            # Si c'était une opération, mettre à jour le statut si nécessaire
            if active_punch.get('operation_id'):
                self.update_operation_progress(active_punch['operation_id'], total_hours)
            
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
    # MÉTHODES POUR OPÉRATIONS - COEUR DU SYSTÈME
    # =========================================================================
    
    def get_available_operations_hierarchical(self) -> Dict[str, List[Dict]]:
        """
        Récupère les opérations disponibles organisées par projet/BT
        Inclut les tâches des BT depuis formulaire_lignes
        """
        try:
            # Requête UNIFIÉE pour récupérer les opérations ET les tâches BT
            query = '''
            -- Vraies opérations depuis la table operations
            SELECT 
                'operation' as source_type,
                o.id,
                o.project_id,
                o.description,
                o.sequence_number,
                o.statut,
                o.temps_estime,
                o.work_center_id,
                p.nom_projet,
                wc.nom as work_center_name,
                f.numero_document as bt_numero,
                f.statut as bt_statut,
                NULL as formulaire_bt_id_from_ligne
            FROM operations o
            LEFT JOIN projects p ON o.project_id = p.id
            LEFT JOIN work_centers wc ON o.work_center_id = wc.id
            LEFT JOIN formulaires f ON o.formulaire_bt_id = f.id AND f.type_formulaire = 'BON_TRAVAIL'
            WHERE o.statut IN ('À FAIRE', 'EN COURS')
            
            UNION ALL
            
            -- Tâches BT depuis formulaire_lignes
            SELECT 
                'bt_task' as source_type,
                (fl.id + 100000) as id,  -- Décaler pour éviter conflits d'ID
                CAST(COALESCE(f.project_id, 0) as INTEGER) as project_id,
                fl.description,
                fl.sequence_ligne as sequence_number,
                CASE 
                    WHEN f.statut = 'TERMINÉ' THEN 'TERMINÉ'
                    WHEN f.statut IN ('VALIDÉ', 'EN COURS') THEN 'À FAIRE'
                    ELSE 'BROUILLON'
                END as statut,
                COALESCE(fl.prix_unitaire, 0.0) as temps_estime,
                NULL as work_center_id,
                COALESCE(
                    (SELECT nom_projet FROM projects WHERE id = f.project_id),
                    JSON_EXTRACT(f.metadonnees_json, '$.project_name'),
                    'Projet Inconnu'
                ) as nom_projet,
                COALESCE(
                    -- Extraire le poste depuis la description ou notes
                    CASE 
                        WHEN fl.notes_ligne LIKE '%operation%' 
                        THEN JSON_EXTRACT(fl.notes_ligne, '$.operation')
                        ELSE NULL
                    END,
                    'Poste Manuel'
                ) as work_center_name,
                f.numero_document as bt_numero,
                f.statut as bt_statut,
                f.id as formulaire_bt_id_from_ligne
            FROM formulaire_lignes fl
            INNER JOIN formulaires f ON fl.formulaire_id = f.id
            WHERE f.type_formulaire = 'BON_TRAVAIL'
            AND fl.sequence_ligne < 1000  -- Exclure les matériaux (>=1000)
            AND fl.description NOT LIKE 'MATERIAU:%'
            AND f.statut NOT IN ('ANNULÉ')
            AND (
                fl.description IS NOT NULL 
                AND fl.description != ''
                AND fl.description != 'None'
            )
            
            ORDER BY nom_projet, bt_numero, sequence_number
            '''
            
            rows = self.db.execute_query(query)
            
            # Organiser les opérations hiérarchiquement
            hierarchy = {}
            
            for row in rows:
                operation = dict(row)
                
                # Déterminer la clé de groupement
                if operation['bt_numero']:
                    # Opération/Tâche liée à un BT
                    group_key = f"📋 BT: {operation['bt_numero']} - {operation['nom_projet']}"
                else:
                    # Opération liée directement au projet
                    group_key = f"🎯 Projet: {operation['nom_projet']}"
                
                if group_key not in hierarchy:
                    hierarchy[group_key] = []
                
                # Extraire informations depuis les notes JSON si c'est une tâche BT
                operation_name = ""
                description_detail = ""
                
                if operation['source_type'] == 'bt_task':
                    # Parser les notes JSON pour récupérer operation/description
                    try:
                        if operation.get('description'):
                            desc = operation['description']
                            
                            # Format: "operation - description" ou juste description
                            if ' - ' in desc:
                                parts = desc.split(' - ', 1)
                                operation_name = parts[0]
                                description_detail = parts[1]
                            else:
                                # Essayer de parser depuis le début
                                if desc.startswith('TÂCHE - '):
                                    description_detail = desc.replace('TÂCHE - ', '')
                                else:
                                    operation_name = desc
                    except:
                        operation_name = operation.get('description', 'Tâche')
                else:
                    # Vraie opération
                    operation_name = operation.get('description', 'Opération')
                
                # Formater l'opération pour affichage
                display_name = f"{operation['sequence_number']:02d}. {operation_name}"
                if description_detail:
                    display_name += f" - {description_detail}"
                if operation['work_center_name']:
                    display_name += f" ({operation['work_center_name']})"
                
                operation_display = {
                    'id': operation['id'],
                    'display_name': display_name,
                    'work_center': operation['work_center_name'],
                    'temps_estime': operation['temps_estime'],
                    'statut': operation['statut'],
                    'project_id': operation['project_id'],
                    'bt_numero': operation['bt_numero'],
                    'source_type': operation['source_type'],  # NOUVEAU : pour différencier
                    'formulaire_bt_id': operation.get('formulaire_bt_id_from_ligne')  # NOUVEAU
                }
                
                hierarchy[group_key].append(operation_display)
            
            return hierarchy
            
        except Exception as e:
            logger.error(f"Erreur récupération opérations hiérarchiques: {e}")
            return {}
    
    def get_operation_info(self, operation_id: int) -> Optional[Dict]:
        """
        Récupère les informations d'une opération
        Support des tâches BT (ID > 100000)
        """
        try:
            if operation_id > 100000:
                # C'est une tâche BT - Convertir l'ID
                ligne_id = operation_id - 100000
                
                query = '''
                    SELECT 
                        fl.id,
                        fl.formulaire_id as formulaire_bt_id,
                        fl.description,
                        fl.sequence_ligne as sequence_number,
                        fl.prix_unitaire as temps_estime,
                        f.project_id,
                        COALESCE(
                            (SELECT nom_projet FROM projects WHERE id = f.project_id),
                            JSON_EXTRACT(f.metadonnees_json, '$.project_name'),
                            'Projet Inconnu'
                        ) as nom_projet,
                        f.numero_document as bt_numero,
                        'BT_TASK' as source_type,
                        COALESCE(
                            CASE 
                                WHEN fl.notes_ligne LIKE '%operation%' 
                                THEN JSON_EXTRACT(fl.notes_ligne, '$.operation')
                                ELSE NULL
                            END,
                            'Poste Manuel'
                        ) as work_center_name
                    FROM formulaire_lignes fl
                    INNER JOIN formulaires f ON fl.formulaire_id = f.id
                    WHERE fl.id = ? AND f.type_formulaire = 'BON_TRAVAIL'
                '''
                result = self.db.execute_query(query, (ligne_id,))
                
            else:
                # Vraie opération depuis la table operations
                query = '''
                    SELECT o.*, p.nom_projet, wc.nom as work_center_name,
                           f.numero_document as bt_numero, 'OPERATION' as source_type
                    FROM operations o
                    LEFT JOIN projects p ON o.project_id = p.id
                    LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                    LEFT JOIN formulaires f ON o.formulaire_bt_id = f.id AND f.type_formulaire = 'BON_TRAVAIL'
                    WHERE o.id = ?
                '''
                result = self.db.execute_query(query, (operation_id,))
            
            return dict(result[0]) if result else None
            
        except Exception as e:
            logger.error(f"Erreur récupération info opération: {e}")
            return None
    
    def punch_in_operation(self, employee_id: int, operation_id: int, notes: str = "") -> Optional[int]:
        """
        Commence un pointage pour un employé sur une opération spécifique
        Support des tâches BT
        """
        try:
            # Vérifier qu'il n'y a pas déjà un pointage actif
            active_punch = self.get_active_punch(employee_id)
            if active_punch:
                return None  # Déjà pointé
            
            # Récupérer les infos de l'opération/tâche
            operation_info = self.get_operation_info(operation_id)
            if not operation_info:
                logger.error(f"Opération {operation_id} non trouvée")
                return None
            
            # Déterminer les IDs selon le type
            if operation_id > 100000:
                # Tâche BT
                real_operation_id = None
                formulaire_bt_id = operation_info.get('formulaire_bt_id') or operation_info.get('formulaire_id')
            else:
                # Vraie opération
                real_operation_id = operation_id
                formulaire_bt_id = operation_info.get('formulaire_bt_id')
            
            # Créer l'entrée de pointage avec opération
            query = '''
                INSERT INTO time_entries 
                (employee_id, project_id, operation_id, formulaire_bt_id, punch_in, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            '''
            
            entry_id = self.db.execute_insert(query, (
                employee_id,
                operation_info['project_id'],
                real_operation_id,  # NULL pour les tâches BT
                formulaire_bt_id,
                datetime.now().isoformat(),
                notes
            ))
            
            logger.info(f"Punch IN opération créé: entry_id={entry_id}, employee={employee_id}, operation={operation_id} (type: {operation_info.get('source_type', 'UNKNOWN')})")
            return entry_id
            
        except Exception as e:
            logger.error(f"Erreur punch in opération: {e}")
            return None
    
    def get_active_punch_with_operation(self, employee_id: int) -> Optional[Dict]:
        """
        Récupère le pointage actif d'un employé avec infos opération
        Support des tâches BT
        """
        try:
            query = '''
                SELECT te.*, p.nom_projet, e.prenom || ' ' || e.nom as employee_name,
                       -- Opération classique
                       o.description as operation_description, 
                       o.sequence_number,
                       wc.nom as work_center_name, 
                       -- BT et ses tâches
                       f.numero_document as bt_numero,
                       fl.description as bt_task_description,
                       fl.sequence_ligne as bt_task_sequence,
                       -- Déterminer la source
                       CASE 
                           WHEN te.operation_id IS NOT NULL THEN 'OPERATION'
                           WHEN te.formulaire_bt_id IS NOT NULL THEN 'BT_TASK'
                           ELSE 'GENERAL'
                       END as pointage_type
                FROM time_entries te
                LEFT JOIN projects p ON te.project_id = p.id
                LEFT JOIN employees e ON te.employee_id = e.id
                LEFT JOIN operations o ON te.operation_id = o.id
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                LEFT JOIN formulaires f ON te.formulaire_bt_id = f.id AND f.type_formulaire = 'BON_TRAVAIL'
                LEFT JOIN formulaire_lignes fl ON f.id = fl.formulaire_id 
                    AND fl.sequence_ligne < 1000 
                    AND fl.description IS NOT NULL
                    AND fl.description != ''
                WHERE te.employee_id = ? AND te.punch_out IS NULL
                ORDER BY te.punch_in DESC
                LIMIT 1
            '''
            result = self.db.execute_query(query, (employee_id,))
            
            if result:
                punch_data = dict(result[0])
                
                # Unifier la description selon le type
                if punch_data['pointage_type'] == 'BT_TASK' and punch_data['bt_task_description']:
                    punch_data['operation_description'] = punch_data['bt_task_description']
                    punch_data['sequence_number'] = punch_data['bt_task_sequence']
                    
                    # Essayer d'extraire le poste de travail depuis les notes de la tâche
                    if not punch_data['work_center_name']:
                        try:
                            # Récupérer les notes de la ligne pour le poste
                            ligne_result = self.db.execute_query(
                                "SELECT notes_ligne FROM formulaire_lignes WHERE formulaire_id = ? AND sequence_ligne = ?",
                                (punch_data['formulaire_bt_id'], punch_data['bt_task_sequence'])
                            )
                            if ligne_result and ligne_result[0]['notes_ligne']:
                                notes_data = json.loads(ligne_result[0]['notes_ligne'])
                                punch_data['work_center_name'] = notes_data.get('operation', 'Poste Manuel')
                        except:
                            punch_data['work_center_name'] = 'Poste Manuel'
                
                return punch_data
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération punch actif avec opération: {e}")
            return None
    
    def get_operation_time_summary(self, operation_id: int) -> Dict:
        """
        Résumé des temps sur une opération
        Support des tâches BT
        """
        try:
            if operation_id > 100000:
                # Tâche BT - utiliser formulaire_bt_id
                ligne_id = operation_id - 100000
                
                # D'abord récupérer l'info de la tâche
                ligne_info = self.db.execute_query(
                    "SELECT formulaire_id, prix_unitaire, description FROM formulaire_lignes WHERE id = ?",
                    (ligne_id,)
                )
                
                if not ligne_info:
                    return {}
                
                formulaire_bt_id = ligne_info[0]['formulaire_id']
                temps_estime = ligne_info[0]['prix_unitaire'] or 0.0
                operation_description = ligne_info[0]['description']
                
                # Statistiques sur ce BT
                query = '''
                    SELECT 
                        COUNT(*) as total_sessions,
                        COUNT(DISTINCT employee_id) as unique_employees,
                        COALESCE(SUM(total_hours), 0) as total_hours_real,
                        COALESCE(SUM(total_cost), 0) as total_cost,
                        MIN(te.punch_in) as first_punch,
                        MAX(te.punch_out) as last_punch
                    FROM time_entries te
                    WHERE te.formulaire_bt_id = ? AND te.punch_out IS NOT NULL
                '''
                
                result = self.db.execute_query(query, (formulaire_bt_id,))
                
            else:
                # Vraie opération
                query = '''
                    SELECT 
                        COUNT(*) as total_sessions,
                        COUNT(DISTINCT employee_id) as unique_employees,
                        COALESCE(SUM(total_hours), 0) as total_hours_real,
                        COALESCE(SUM(total_cost), 0) as total_cost,
                        o.temps_estime,
                        o.description as operation_description,
                        MIN(te.punch_in) as first_punch,
                        MAX(te.punch_out) as last_punch
                    FROM time_entries te
                    LEFT JOIN operations o ON te.operation_id = o.id
                    WHERE te.operation_id = ? AND te.punch_out IS NOT NULL
                    GROUP BY o.id, o.temps_estime, o.description
                '''
                
                result = self.db.execute_query(query, (operation_id,))
                temps_estime = result[0]['temps_estime'] if result else 0.0
                operation_description = result[0]['operation_description'] if result else 'Opération'
            
            if result:
                summary = dict(result[0])
                
                # Ajouter les infos manquantes pour les tâches BT
                if operation_id > 100000:
                    summary['temps_estime'] = temps_estime
                    summary['operation_description'] = operation_description
                
                # Calculer l'écart temps estimé vs réel
                if summary.get('temps_estime', 0) > 0:
                    ecart_pct = ((summary['total_hours_real'] - summary['temps_estime']) / summary['temps_estime']) * 100
                    summary['ecart_temps_pct'] = ecart_pct
                    summary['performance'] = "En avance" if ecart_pct < -10 else "En retard" if ecart_pct > 10 else "Dans les temps"
                else:
                    summary['ecart_temps_pct'] = 0
                    summary['performance'] = "Estimation manquante"
                
                return summary
            
            return {}
            
        except Exception as e:
            logger.error(f"Erreur résumé opération: {e}")
            return {}
    
    def update_operation_progress(self, operation_id: int, hours_added: float):
        """Met à jour le progrès d'une opération après pointage"""
        try:
            # Récupérer le temps total pointé sur cette opération
            total_result = self.db.execute_query(
                "SELECT COALESCE(SUM(total_hours), 0) as total_hours FROM time_entries WHERE operation_id = ? AND total_cost IS NOT NULL",
                (operation_id,)
            )
            
            if total_result:
                total_hours = total_result[0]['total_hours']
                
                # Récupérer le temps estimé
                op_result = self.db.execute_query(
                    "SELECT temps_estime FROM operations WHERE id = ?",
                    (operation_id,)
                )
                
                if op_result and op_result[0]['temps_estime']:
                    temps_estime = op_result[0]['temps_estime']
                    
                    # Calculer le pourcentage d'avancement
                    if temps_estime > 0:
                        progress_pct = min(100, (total_hours / temps_estime) * 100)
                        
                        # Mettre à jour le statut si nécessaire
                        new_status = None
                        if progress_pct >= 100:
                            new_status = 'TERMINÉ'
                        elif progress_pct > 0:
                            new_status = 'EN COURS'
                        
                        if new_status:
                            self.db.execute_update(
                                "UPDATE operations SET statut = ? WHERE id = ?",
                                (new_status, operation_id)
                            )
                            
                            logger.info(f"Opération {operation_id} mise à jour: {progress_pct:.1f}% - {new_status}")
                
        except Exception as e:
            logger.error(f"Erreur mise à jour progression opération: {e}")
    
    # =========================================================================
    # MÉTHODES DE CONSULTATION
    # =========================================================================
    
    def get_punch_history(self, employee_id: int = None, days: int = 7) -> List[Dict]:
        """
        Récupère l'historique des pointages avec support opérations ET tâches BT
        """
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            query = '''
                SELECT te.*, 
                       p.nom_projet, 
                       e.prenom || ' ' || e.nom as employee_name,
                       e.poste as employee_poste,
                       DATE(te.punch_in) as date_travail,
                       
                       -- Opérations classiques
                       o.description as operation_description,
                       o.sequence_number,
                       wc.nom as work_center_name,
                       
                       -- Informations BT
                       f.numero_document as bt_numero,
                       f.statut as bt_statut,
                       
                       -- Tâches BT depuis formulaire_lignes
                       fl.description as bt_task_description,
                       fl.sequence_ligne as bt_task_sequence,
                       
                       -- Déterminer le type de pointage
                       CASE 
                           WHEN te.operation_id IS NOT NULL THEN 'OPERATION'
                           WHEN te.formulaire_bt_id IS NOT NULL THEN 'BT_TASK'
                           ELSE 'GENERAL'
                       END as pointage_type
                       
                FROM time_entries te
                LEFT JOIN projects p ON te.project_id = p.id
                LEFT JOIN employees e ON te.employee_id = e.id
                
                -- Jointures pour vraies opérations
                LEFT JOIN operations o ON te.operation_id = o.id
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                
                -- Jointures pour BT et ses tâches
                LEFT JOIN formulaires f ON te.formulaire_bt_id = f.id AND f.type_formulaire = 'BON_TRAVAIL'
                LEFT JOIN formulaire_lignes fl ON f.id = fl.formulaire_id 
                    AND fl.sequence_ligne < 1000 
                    AND fl.description IS NOT NULL
                    AND fl.description != ''
                    AND fl.description != 'None'
                
                WHERE DATE(te.punch_in) >= ?
            '''
            params = [start_date]
            
            if employee_id:
                query += " AND te.employee_id = ?"
                params.append(employee_id)
            
            query += " ORDER BY te.punch_in DESC"
            
            rows = self.db.execute_query(query, tuple(params))
            
            # Post-traitement pour unifier les descriptions
            history = []
            for row in rows:
                punch_data = dict(row)
                
                # Unifier la description selon le type
                if punch_data['pointage_type'] == 'BT_TASK' and punch_data['bt_task_description']:
                    # C'est une tâche BT - utiliser les infos de formulaire_lignes
                    punch_data['operation_description'] = punch_data['bt_task_description']
                    punch_data['sequence_number'] = punch_data['bt_task_sequence']
                    
                    # Essayer d'extraire le poste de travail depuis les notes de la tâche
                    if not punch_data['work_center_name']:
                        try:
                            # Récupérer les notes de la ligne pour le poste
                            ligne_result = self.db.execute_query(
                                "SELECT notes_ligne FROM formulaire_lignes WHERE formulaire_id = ? AND sequence_ligne = ? LIMIT 1",
                                (punch_data['formulaire_bt_id'], punch_data['bt_task_sequence'])
                            )
                            if ligne_result and ligne_result[0]['notes_ligne']:
                                notes_data = json.loads(ligne_result[0]['notes_ligne'])
                                punch_data['work_center_name'] = notes_data.get('operation', 'Poste Manuel')
                        except:
                            punch_data['work_center_name'] = 'Poste Manuel'
                
                elif punch_data['pointage_type'] == 'BT_TASK' and not punch_data['operation_description']:
                    # Tâche BT mais description vide - mettre une valeur par défaut
                    punch_data['operation_description'] = 'Tâche BT'
                    punch_data['work_center_name'] = punch_data['work_center_name'] or 'Poste Manuel'
                
                history.append(punch_data)
            
            return history
            
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
                    COUNT(DISTINCT operation_id) as unique_operations,
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
                    COUNT(DISTINCT operation_id) as unique_operations,
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
                    COUNT(DISTINCT operation_id) as unique_operations,
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
    # MÉTHODES DE GESTION DES DONNÉES
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
    
    def get_active_employees_with_operations(self) -> List[Dict]:
        """Récupère les employés avec pointage actif sur opérations"""
        try:
            query = '''
                SELECT DISTINCT e.id, e.prenom || ' ' || e.nom as name, 
                       e.poste, p.nom_projet, te.punch_in,
                       o.description as operation_description,
                       o.sequence_number, wc.nom as work_center_name,
                       f.numero_document as bt_numero,
                       ROUND((JULIANDAY('now') - JULIANDAY(te.punch_in)) * 24, 2) as hours_worked
                FROM time_entries te
                JOIN employees e ON te.employee_id = e.id
                LEFT JOIN projects p ON te.project_id = p.id
                LEFT JOIN operations o ON te.operation_id = o.id
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                LEFT JOIN formulaires f ON te.formulaire_bt_id = f.id AND f.type_formulaire = 'BON_TRAVAIL'
                WHERE te.punch_out IS NULL
                ORDER BY te.punch_in
            '''
            rows = self.db.execute_query(query)
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur employés actifs avec opérations: {e}")
            return []
    
    # =========================================================================
    # MÉTHODES STATISTIQUES
    # =========================================================================
    
    def get_timetracker_statistics_unified(self) -> Dict:
        """Statistiques générales pour compatibilité avec app.py"""
        try:
            # Stats générales
            general_stats = self.db.execute_query('''
                SELECT 
                    COUNT(DISTINCT employee_id) as total_employees,
                    COUNT(CASE WHEN punch_out IS NULL THEN 1 END) as active_entries,
                    COUNT(*) as total_entries,
                    COUNT(CASE WHEN operation_id IS NOT NULL THEN 1 END) as operation_entries,
                    COUNT(CASE WHEN formulaire_bt_id IS NOT NULL THEN 1 END) as bt_entries
                FROM time_entries
            ''')
            
            stats = dict(general_stats[0]) if general_stats else {}
            
            # Stats du jour
            today = date.today().strftime('%Y-%m-%d')
            daily_stats = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total_entries_today,
                    COUNT(CASE WHEN operation_id IS NOT NULL THEN 1 END) as operation_entries_today,
                    COUNT(CASE WHEN formulaire_bt_id IS NOT NULL THEN 1 END) as bt_entries_today,
                    COALESCE(SUM(total_hours), 0) as total_hours_today,
                    COALESCE(SUM(total_cost), 0) as total_revenue_today,
                    COALESCE(SUM(CASE WHEN operation_id IS NOT NULL THEN total_cost ELSE 0 END), 0) as operation_revenue_today,
                    COALESCE(SUM(CASE WHEN formulaire_bt_id IS NOT NULL THEN total_cost ELSE 0 END), 0) as bt_revenue_today
                FROM time_entries
                WHERE DATE(punch_in) = ? AND punch_out IS NOT NULL
            ''', (today,))
            
            if daily_stats:
                stats.update(dict(daily_stats[0]))
            
            # Compteurs pour compatibilité
            stats['active_entries_bt'] = stats.get('bt_entries', 0)
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur stats unifiées: {e}")
            return {}
    
    def get_work_centers_statistics(self) -> Dict:
        """Statistiques postes de travail"""
        try:
            result = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total_postes,
                    COUNT(CASE WHEN statut = 'ACTIF' THEN 1 END) as postes_actifs,
                    COUNT(CASE WHEN categorie = 'ROBOTIQUE' THEN 1 END) as postes_robotises,
                    COUNT(CASE WHEN categorie = 'CNC' THEN 1 END) as postes_cnc,
                    COALESCE(SUM(capacite_theorique), 0) as capacite_totale
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
            
            # Utilisation via opérations
            usage_result = self.db.execute_query('''
                SELECT 
                    COUNT(DISTINCT wc.id) as postes_utilises,
                    COUNT(DISTINCT te.id) as sessions_operations,
                    COALESCE(SUM(te.total_hours), 0) as heures_operations
                FROM work_centers wc
                LEFT JOIN operations o ON wc.id = o.work_center_id
                LEFT JOIN time_entries te ON o.id = te.operation_id AND te.total_cost IS NOT NULL
            ''')
            
            if usage_result:
                stats.update(dict(usage_result[0]))
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur stats postes: {e}")
            return {}
    
    # =========================================================================
    # MÉTHODES DE DIAGNOSTIC
    # =========================================================================
    
    def diagnostic_timetracker_data(self) -> Dict:
        """
        Diagnostic complet des données TimeTracker pour identifier les problèmes
        """
        try:
            diagnostic = {
                'time_entries': {},
                'operations': {},
                'formulaires_bt': {},
                'formulaire_lignes': {},
                'problemes_detectes': []
            }
            
            # 1. Analyser time_entries
            te_stats = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total_entries,
                    COUNT(CASE WHEN punch_out IS NULL THEN 1 END) as active_entries,
                    COUNT(CASE WHEN operation_id IS NOT NULL THEN 1 END) as operation_entries,
                    COUNT(CASE WHEN formulaire_bt_id IS NOT NULL THEN 1 END) as bt_entries,
                    COUNT(CASE WHEN operation_id IS NULL AND formulaire_bt_id IS NULL THEN 1 END) as general_entries,
                    MAX(punch_in) as last_punch_in
                FROM time_entries
            ''')
            
            if te_stats:
                diagnostic['time_entries'] = dict(te_stats[0])
            
            # 2. Analyser les pointages actifs par type
            active_details = self.db.execute_query('''
                SELECT 
                    te.id,
                    te.employee_id,
                    e.prenom || ' ' || e.nom as employee_name,
                    te.punch_in,
                    CASE 
                        WHEN te.operation_id IS NOT NULL THEN 'OPERATION'
                        WHEN te.formulaire_bt_id IS NOT NULL THEN 'BT_TASK'
                        ELSE 'GENERAL'
                    END as type_pointage,
                    te.operation_id,
                    te.formulaire_bt_id,
                    f.numero_document as bt_numero
                FROM time_entries te
                LEFT JOIN employees e ON te.employee_id = e.id
                LEFT JOIN formulaires f ON te.formulaire_bt_id = f.id
                WHERE te.punch_out IS NULL
                ORDER BY te.punch_in DESC
            ''')
            
            diagnostic['pointages_actifs'] = [dict(row) for row in active_details]
            
            # 3. Vérifier les BT avec des lignes
            bt_lignes = self.db.execute_query('''
                SELECT 
                    f.id as bt_id,
                    f.numero_document,
                    f.statut,
                    COUNT(fl.id) as nb_lignes,
                    COUNT(CASE WHEN fl.sequence_ligne < 1000 AND fl.description IS NOT NULL 
                               AND fl.description != '' AND fl.description != 'None' THEN 1 END) as nb_taches
                FROM formulaires f
                LEFT JOIN formulaire_lignes fl ON f.id = fl.formulaire_id
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                GROUP BY f.id, f.numero_document, f.statut
                ORDER BY f.id DESC
            ''')
            
            diagnostic['bts_avec_lignes'] = [dict(row) for row in bt_lignes]
            
            # 4. Vérifier les opérations classiques
            operations_stats = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total_operations,
                    COUNT(CASE WHEN formulaire_bt_id IS NOT NULL THEN 1 END) as operations_liees_bt,
                    COUNT(CASE WHEN statut = 'À FAIRE' THEN 1 END) as operations_a_faire,
                    COUNT(CASE WHEN statut = 'EN COURS' THEN 1 END) as operations_en_cours
                FROM operations
            ''')
            
            if operations_stats:
                diagnostic['operations'] = dict(operations_stats[0])
            
            # 5. Détecter les problèmes
            problemes = []
            
            # Pointages orphelins (BT supprimé)
            orphan_bt = self.db.execute_query('''
                SELECT COUNT(*) as count FROM time_entries te
                WHERE te.formulaire_bt_id IS NOT NULL
                AND te.formulaire_bt_id NOT IN (
                    SELECT id FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL'
                )
            ''')
            if orphan_bt and orphan_bt[0]['count'] > 0:
                problemes.append(f"❌ {orphan_bt[0]['count']} pointages orphelins (BT supprimés)")
            
            # Pointages sur opérations inexistantes
            orphan_ops = self.db.execute_query('''
                SELECT COUNT(*) as count FROM time_entries te
                WHERE te.operation_id IS NOT NULL
                AND te.operation_id NOT IN (SELECT id FROM operations)
            ''')
            if orphan_ops and orphan_ops[0]['count'] > 0:
                problemes.append(f"❌ {orphan_ops[0]['count']} pointages sur opérations inexistantes")
            
            # BT sans tâches
            bt_sans_taches = [bt for bt in diagnostic['bts_avec_lignes'] if bt['nb_taches'] == 0]
            if bt_sans_taches:
                problemes.append(f"⚠️ {len(bt_sans_taches)} BT sans tâches définies")
            
            # Pointages actifs sans description
            pointages_sans_desc = [p for p in diagnostic['pointages_actifs'] 
                                  if p['type_pointage'] == 'BT_TASK']
            if pointages_sans_desc:
                problemes.append(f"⚠️ {len(pointages_sans_desc)} pointages actifs sur tâches BT")
            
            diagnostic['problemes_detectes'] = problemes
            
            return diagnostic
            
        except Exception as e:
            logger.error(f"Erreur diagnostic TimeTracker: {e}")
            return {'erreur': str(e)}
    
    def corriger_pointages_bt_orphelins(self) -> Dict:
        """
        Corrige les pointages avec des formulaire_bt_id invalides
        """
        try:
            # Identifier les pointages orphelins
            orphelins = self.db.execute_query('''
                SELECT te.id, te.formulaire_bt_id, te.employee_id, te.punch_in
                FROM time_entries te
                WHERE te.formulaire_bt_id IS NOT NULL
                AND te.formulaire_bt_id NOT IN (
                    SELECT id FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL'
                )
            ''')
            
            corrections = {
                'orphelins_trouves': len(orphelins),
                'corrections_effectuees': 0,
                'erreurs': []
            }
            
            for orphelin in orphelins:
                try:
                    # Option 1: Supprimer le lien BT (garder comme pointage général)
                    affected = self.db.execute_update(
                        "UPDATE time_entries SET formulaire_bt_id = NULL WHERE id = ?",
                        (orphelin['id'],)
                    )
                    
                    if affected > 0:
                        corrections['corrections_effectuees'] += 1
                        
                except Exception as e:
                    corrections['erreurs'].append(f"Erreur ID {orphelin['id']}: {e}")
            
            return corrections
            
        except Exception as e:
            return {'erreur': str(e)}
    
    def debug_current_punches(self):
        """
        Debug les pointages actuels pour comprendre le problème
        """
        print("=== DIAGNOSTIC POINTAGES ACTIFS ===")
        
        # Pointages actifs bruts
        active_raw = self.db.execute_query('''
            SELECT te.*, e.prenom || ' ' || e.nom as emp_name
            FROM time_entries te
            LEFT JOIN employees e ON te.employee_id = e.id
            WHERE te.punch_out IS NULL
        ''')
        
        print(f"Pointages actifs trouvés: {len(active_raw)}")
        for punch in active_raw:
            print(f"  - {punch['emp_name']}: operation_id={punch['operation_id']}, bt_id={punch['formulaire_bt_id']}")
        
        # Test historique avec la nouvelle méthode
        print("\n=== TEST HISTORIQUE ===")
        history = self.get_punch_history(days=7)
        print(f"Historique trouvé: {len(history)} entrées")
        
        for h in history[:5]:  # Afficher les 5 premiers
            print(f"  - {h['employee_name']}: {h.get('operation_description', 'N/A')} (Type: {h.get('pointage_type', 'N/A')})")
    
    # =========================================================================
    # FONCTION UTILITAIRE BONUS
    # =========================================================================
    
    def sync_bt_tasks_to_operations(self):
        """
        Fonction optionnelle pour créer des entrées operations depuis les tâches BT
        À appeler manuellement si on veut unifier le système
        """
        try:
            # Récupérer toutes les tâches BT qui n'ont pas d'opération correspondante
            query = '''
                SELECT fl.*, f.project_id, f.numero_document
                FROM formulaire_lignes fl
                INNER JOIN formulaires f ON fl.formulaire_id = f.id
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                AND fl.sequence_ligne < 1000
                AND fl.description IS NOT NULL
                AND fl.description != ''
                AND NOT EXISTS (
                    SELECT 1 FROM operations o 
                    WHERE o.formulaire_bt_id = f.id 
                    AND o.sequence_number = fl.sequence_ligne
                )
            '''
            
            taches_bt = self.db.execute_query(query)
            
            operations_created = 0
            
            for tache in taches_bt:
                # Extraire le poste de travail depuis les notes
                work_center_id = None
                try:
                    if tache['notes_ligne']:
                        notes_data = json.loads(tache['notes_ligne'])
                        operation_name = notes_data.get('operation', '')
                        
                        # Chercher le work_center correspondant
                        if operation_name:
                            wc_result = self.db.execute_query(
                                "SELECT id FROM work_centers WHERE nom = ? LIMIT 1",
                                (operation_name,)
                            )
                            if wc_result:
                                work_center_id = wc_result[0]['id']
                except:
                    pass
                
                # Créer l'opération
                operation_data = {
                    'project_id': tache['project_id'],
                    'formulaire_bt_id': tache['formulaire_id'],
                    'description': tache['description'],
                    'sequence_number': tache['sequence_ligne'],
                    'temps_estime': tache['prix_unitaire'] or 0.0,
                    'work_center_id': work_center_id,
                    'statut': 'À FAIRE'
                }
                
                op_id = self.db.execute_insert('''
                    INSERT INTO operations 
                    (project_id, formulaire_bt_id, description, sequence_number, temps_estime, work_center_id, statut)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    operation_data['project_id'],
                    operation_data['formulaire_bt_id'],
                    operation_data['description'],
                    operation_data['sequence_number'],
                    operation_data['temps_estime'],
                    operation_data['work_center_id'],
                    operation_data['statut']
                ))
                
                if op_id:
                    operations_created += 1
            
            logger.info(f"Synchronisation BT → Operations: {operations_created} opérations créées")
            return operations_created
            
        except Exception as e:
            logger.error(f"Erreur synchronisation BT: {e}")
            return 0

# =========================================================================
# INTERFACE STREAMLIT PRINCIPALE - MODE OPÉRATIONS UNIQUEMENT
# =========================================================================

def show_timetracker_unified_interface():
    """Interface principale du TimeTracker unifié - MODE OPÉRATIONS UNIQUEMENT"""
    
    if 'timetracker_unified' not in st.session_state:
        st.error("❌ TimeTracker non initialisé")
        return
    
    tt = st.session_state.timetracker_unified
    
    st.markdown("### ⏱️ TimeTracker Unifié - Pointage sur Opérations")
    st.info("🔧 **Pointage granulaire sur les opérations spécifiques des Bons de Travail**")
    
    # Onglets pour le mode opérations
    tab_operations, tab_history_op, tab_stats_op = st.tabs([
        "🔧 Pointage Opérations", "📊 Historique", "📈 Statistiques"
    ])
    
    with tab_operations:
        show_operation_punch_interface(tt)
    
    with tab_history_op:
        show_history_interface_operations(tt)
    
    with tab_stats_op:
        show_operation_statistics_interface(tt)

# =========================================================================
# INTERFACES MODE OPÉRATIONS - POINTAGE GRANULAIRE
# =========================================================================

def show_operation_punch_interface(tt):
    """Interface de pointage avancée avec sélection d'opérations"""
    
    st.markdown("#### 🔧 Pointage sur Opérations")
    
    # Section employés actifs avec opérations
    active_employees = tt.get_active_employees_with_operations()
    if active_employees:
        st.markdown("##### 🟢 Employés Pointés sur Opérations")
        
        for emp in active_employees:
            col1, col2, col3, col4 = st.columns([3, 4, 2, 2])
            
            with col1:
                st.write(f"**{emp['name']}**")
                st.caption(emp['poste'])
            
            with col2:
                # Affichage hiérarchique de l'opération
                if emp['bt_numero']:
                    st.write(f"📋 **BT {emp['bt_numero']}**")
                    st.caption(f"Projet: {emp['nom_projet']}")
                else:
                    st.write(f"📋 **{emp['nom_projet']}**")
                
                if emp['operation_description']:
                    st.write(f"🔧 **Op.{emp['sequence_number']:02d}:** {emp['operation_description']}")
                    if emp['work_center_name']:
                        st.caption(f"🏭 {emp['work_center_name']}")
                else:
                    st.caption("Opération générale")
                
                st.caption(f"Depuis: {emp['punch_in'][:16]}")
            
            with col3:
                st.metric("Heures", f"{emp['hours_worked']:.1f}h")
            
            with col4:
                if st.button("🔴 Pointer Sortie", key=f"out_op_{emp['id']}", use_container_width=True):
                    notes = st.text_input(f"Notes sortie {emp['name']}:", key=f"notes_out_op_{emp['id']}")
                    if tt.punch_out(emp['id'], notes):
                        st.success(f"✅ {emp['name']} pointé sortie !")
                        st.rerun()
                    else:
                        st.error("❌ Erreur pointage sortie")
        
        st.markdown("---")
    
    # Section nouveau pointage sur opération
    st.markdown("##### ➕ Nouveau Pointage sur Opération")
    
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
            key="punch_op_employee_select"
        )
    
    with col2:
        # Sélection hiérarchique : Projet/BT puis Opération
        operations_hierarchy = tt.get_available_operations_hierarchical()
        
        if not operations_hierarchy:
            st.warning("Aucune opération disponible")
            return
        
        # Premier niveau : Projet/BT
        project_bt_options = list(operations_hierarchy.keys())
        selected_project_bt = st.selectbox(
            "📋 Sélectionner Projet/BT:",
            options=project_bt_options,
            key="punch_op_project_bt_select"
        )
    
    # Deuxième niveau : Opération
    if selected_project_bt and selected_project_bt in operations_hierarchy:
        available_operations = operations_hierarchy[selected_project_bt]
        
        if available_operations:
            operation_options = {op['id']: op['display_name'] for op in available_operations}
            selected_operation_id = st.selectbox(
                "🔧 Sélectionner Opération:",
                options=list(operation_options.keys()),
                format_func=lambda x: operation_options[x],
                key="punch_op_operation_select"
            )
            
            # Afficher les détails de l'opération sélectionnée
            selected_op_details = next((op for op in available_operations if op['id'] == selected_operation_id), None)
            if selected_op_details:
                col_det1, col_det2, col_det3 = st.columns(3)
                col_det1.metric("Temps Estimé", f"{selected_op_details['temps_estime']:.1f}h")
                col_det2.metric("Poste", selected_op_details['work_center'] or "N/A")
                col_det3.metric("Statut", selected_op_details['statut'])
        else:
            st.warning("Aucune opération disponible pour ce projet/BT")
            return
    else:
        st.warning("Sélectionnez un projet/BT")
        return
    
    # Notes et action
    notes = st.text_input("📝 Notes (optionnel):", key="punch_op_notes")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("🟢 Pointer sur Opération", use_container_width=True, type="primary"):
            # Vérifier si l'employé est déjà pointé
            active_punch = tt.get_active_punch(selected_employee_id)
            if active_punch:
                current_op = active_punch.get('operation_description', 'Tâche générale')
                st.error(f"❌ {employee_options[selected_employee_id]} est déjà pointé sur: {current_op}")
            else:
                entry_id = tt.punch_in_operation(selected_employee_id, selected_operation_id, notes)
                if entry_id:
                    st.success(f"✅ Pointage sur opération démarré ! ID: {entry_id}")
                    st.rerun()
                else:
                    st.error("❌ Erreur lors du pointage sur opération")
    
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

def show_history_interface_operations(tt):
    """Interface d'historique adaptée pour les opérations"""
    
    st.markdown("#### 📊 Historique des Pointages sur Opérations")
    
    # Filtres
    col1, col2, col3 = st.columns(3)
    
    with col1:
        days_filter = st.selectbox("📅 Période:", [7, 14, 30, 90], index=1, key="hist_op_days")
    
    with col2:
        employees = tt.get_all_employees()
        employee_filter = st.selectbox(
            "👤 Employé:",
            options=[None] + [emp['id'] for emp in employees],
            format_func=lambda x: "Tous" if x is None else next((emp['display_name'] for emp in employees if emp['id'] == x), str(x)),
            key="hist_op_employee"
        )
    
    with col3:
        show_operations_only = st.checkbox("🔧 Opérations seulement", value=True)
    
    # Récupérer l'historique avec opérations
    history = tt.get_punch_history(employee_filter, days_filter)
    
    # Filtrer pour opérations seulement si demandé
    if show_operations_only:
        history = [h for h in history if h.get('operation_description')]
    
    if not history:
        st.info("Aucun pointage trouvé")
        return
    
    # Résumé
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
    st.markdown("##### 📋 Détail des Pointages sur Opérations")
    
    df_data = []
    for h in history:
        # Formatage spécial pour opérations
        if h['operation_description']:
            task_display = f"Op.{h['sequence_number']:02d}: {h['operation_description']}"
            if h['work_center_name']:
                task_display += f" ({h['work_center_name']})"
        else:
            task_display = "Tâche générale"
        
        # Extraire numéros pour colonnes séparées
        numero_projet = h.get('project_id', 'N/A')
        numero_bt = h.get('bt_numero', '')
        
        # Formatage projet/BT pour colonne nom
        if h['bt_numero']:
            project_display = f"{h['nom_projet']}"
        else:
            project_display = h['nom_projet'] or 'N/A'
        
        # Statut et durée
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
            'Statut': status,
            'No. Projet': numero_projet,
            'Nom Projet': project_display,
            'No. BT': numero_bt,
            'Opération': task_display,
            'Date': h['date_travail'],
            'Employé': h['employee_name'],
            'Début': h['punch_in'][-8:-3] if h['punch_in'] else 'N/A',
            'Fin': h['punch_out'][-8:-3] if h['punch_out'] else 'En cours',
            'Durée': hours_display,
            'Coût': cost_display,
            'Notes': h['notes'] or ''
        })
    
    if df_data:
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Bouton export
        if st.button("📥 Exporter CSV Opérations", use_container_width=True):
            csv = df.to_csv(index=False)
            st.download_button(
                label="💾 Télécharger CSV",
                data=csv,
                file_name=f"pointages_operations_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

def show_operation_statistics_interface(tt):
    """Interface statistiques améliorée avec opérations"""
    
    st.markdown("#### 📈 Statistiques par Opérations")
    
    # Résumé du jour avec opérations
    daily_summary = tt.get_daily_summary()
    
    st.markdown("##### 📅 Aujourd'hui")
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Pointages", daily_summary.get('total_punches', 0))
    col2.metric("Employés", daily_summary.get('unique_employees', 0))
    col3.metric("Opérations", daily_summary.get('unique_operations', 0))
    col4.metric("Revenus", f"{daily_summary.get('total_revenue', 0):,.0f}$")
    
    # Sélecteur d'opération pour statistiques détaillées
    operations_hierarchy = tt.get_available_operations_hierarchical()
    
    if operations_hierarchy:
        st.markdown("##### 🔧 Analyse d'Opération Spécifique")
        
        # Créer une liste plate de toutes les opérations
        all_operations = []
        for project_bt, operations in operations_hierarchy.items():
            for op in operations:
                all_operations.append({
                    'id': op['id'],
                    'display_name': f"{project_bt} → {op['display_name']}",
                    'project_bt': project_bt
                })
        
        if all_operations:
            operation_options = {op['id']: op['display_name'] for op in all_operations}
            selected_op_id = st.selectbox(
                "Sélectionner une opération:",
                options=list(operation_options.keys()),
                format_func=lambda x: operation_options[x]
            )
            
            if selected_op_id:
                # Afficher les statistiques de l'opération
                op_stats = tt.get_operation_time_summary(selected_op_id)
                
                if op_stats and op_stats.get('total_sessions', 0) > 0:
                    st.markdown("**📊 Statistiques de l'Opération**")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Sessions", op_stats['total_sessions'])
                    col2.metric("Employés", op_stats['unique_employees'])
                    col3.metric("Temps Réel", f"{op_stats['total_hours_real']:.1f}h")
                    col4.metric("Temps Estimé", f"{op_stats.get('temps_estime', 0):.1f}h")
                    
                    col5, col6, col7 = st.columns(3)
                    col5.metric("Coût Total", f"{op_stats['total_cost']:,.0f}$")
                    
                    if op_stats.get('ecart_temps_pct') is not None:
                        ecart = op_stats['ecart_temps_pct']
                        col6.metric("Écart Temps", f"{ecart:+.1f}%", 
                                   delta=f"{ecart:.1f}%" if ecart != 0 else None)
                    
                    col7.metric("Performance", op_stats.get('performance', 'N/A'))
                    
                    # Barre de progression
                    if op_stats.get('temps_estime', 0) > 0:
                        progress = min(1.0, op_stats['total_hours_real'] / op_stats['temps_estime'])
                        st.progress(progress)
                        st.caption(f"Progression: {progress * 100:.1f}% du temps estimé")
                else:
                    st.info("Aucune donnée de pointage pour cette opération")
    
    # Graphiques par opérations
    st.markdown("##### 📊 Analyses par Opérations")
    
    # Historique 30 derniers jours avec opérations
    history_30d = tt.get_punch_history(days=30)
    
    # Filtrer les entrées avec opérations
    history_ops = [h for h in history_30d if h.get('operation_description')]
    
    if history_ops:
        df_ops = pd.DataFrame(history_ops)
        
        # Top opérations par temps
        if not df_ops.empty and 'total_hours' in df_ops.columns:
            op_hours = df_ops.groupby('operation_description')['total_hours'].sum().reset_index()
            op_hours = op_hours[op_hours['total_hours'].notna()].sort_values('total_hours', ascending=False).head(10)
            
            if not op_hours.empty:
                fig_ops = px.bar(
                    op_hours,
                    x='total_hours',
                    y='operation_description',
                    orientation='h',
                    title="Top 10 Opérations par Heures (30j)",
                    labels={'total_hours': 'Heures', 'operation_description': 'Opération'}
                )
                fig_ops.update_layout(height=500)
                st.plotly_chart(fig_ops, use_container_width=True)
        
        # Répartition par postes de travail
        if 'work_center_name' in df_ops.columns:
            wc_hours = df_ops.groupby('work_center_name')['total_hours'].sum().reset_index()
            wc_hours = wc_hours[wc_hours['total_hours'].notna()]
            
            if not wc_hours.empty:
                fig_wc = px.pie(
                    wc_hours,
                    values='total_hours',
                    names='work_center_name',
                    title="Répartition Heures par Poste de Travail (30j)"
                )
                st.plotly_chart(fig_wc, use_container_width=True)
    
    else:
        st.info("Aucune opération disponible pour les statistiques")

# =========================================================================
# FONCTION PRINCIPALE D'AFFICHAGE
# =========================================================================

def show_timetracker_unified_interface_main():
    """Point d'entrée principal pour l'interface (appelé depuis app.py)"""
    show_timetracker_unified_interface()
