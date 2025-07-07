import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
import logging
import json
import io

logger = logging.getLogger(__name__)

class TimeTrackerUnified:
    """
    Système de pointage spécialisé sur opérations
    Pointage granulaire sur opérations spécifiques des Bons de Travail
    Interface optimisée pour le suivi opérationnel en production
    Support complet des tâches BT depuis formulaire_lignes
    Avec méthodes de diagnostic intégrées
    NOUVEAU: Gestion administrative avec suppression d'historique
    NOUVEAU: Interface double - Mode Superviseur et Mode Employé
    NOUVEAU: Réinitialisation automatique après pointage
    MODIFIÉ: Interface employé directe sans sélecteur de mode
    v2.1: Réinitialisation automatique du sélecteur d'employé après chaque pointage
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
    # MÉTHODES ADMINISTRATIVES - GESTION HISTORIQUE
    # =========================================================================
    
    def create_history_backup(self) -> str:
        """Crée une sauvegarde de l'historique avant suppression"""
        try:
            backup_data = {
                'timestamp': datetime.now().isoformat(),
                'time_entries': []
            }
            
            # Récupérer tous les pointages avec détails
            query = '''
                SELECT te.*, 
                       p.nom_projet, 
                       e.prenom || ' ' || e.nom as employee_name,
                       o.description as operation_description,
                       f.numero_document as bt_numero
                FROM time_entries te
                LEFT JOIN projects p ON te.project_id = p.id
                LEFT JOIN employees e ON te.employee_id = e.id
                LEFT JOIN operations o ON te.operation_id = o.id
                LEFT JOIN formulaires f ON te.formulaire_bt_id = f.id
                ORDER BY te.punch_in DESC
            '''
            
            rows = self.db.execute_query(query)
            for row in rows:
                backup_data['time_entries'].append(dict(row))
            
            # Créer le fichier de sauvegarde
            backup_json = json.dumps(backup_data, indent=2, default=str)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"timetracker_backup_{timestamp}.json"
            
            logger.info(f"Sauvegarde créée: {len(backup_data['time_entries'])} entrées")
            return backup_json, filename
            
        except Exception as e:
            logger.error(f"Erreur création sauvegarde: {e}")
            return None, None
    
    def get_history_statistics(self) -> Dict:
        """Statistiques de l'historique pour l'interface admin"""
        try:
            stats = {}
            
            # Statistiques générales
            general_stats = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total_entries,
                    COUNT(CASE WHEN punch_out IS NOT NULL THEN 1 END) as completed_entries,
                    COUNT(CASE WHEN punch_out IS NULL THEN 1 END) as active_entries,
                    COUNT(DISTINCT employee_id) as unique_employees,
                    MIN(DATE(punch_in)) as first_date,
                    MAX(DATE(punch_in)) as last_date,
                    COALESCE(SUM(total_hours), 0) as total_hours,
                    COALESCE(SUM(total_cost), 0) as total_cost
                FROM time_entries
            ''')
            
            if general_stats:
                stats.update(dict(general_stats[0]))
            
            # Répartition par type
            type_stats = self.db.execute_query('''
                SELECT 
                    COUNT(CASE WHEN operation_id IS NOT NULL THEN 1 END) as operation_entries,
                    COUNT(CASE WHEN formulaire_bt_id IS NOT NULL THEN 1 END) as bt_entries,
                    COUNT(CASE WHEN operation_id IS NULL AND formulaire_bt_id IS NULL THEN 1 END) as general_entries
                FROM time_entries
            ''')
            
            if type_stats:
                stats.update(dict(type_stats[0]))
            
            # Statistiques par période
            period_stats = self.db.execute_query('''
                SELECT 
                    COUNT(CASE WHEN DATE(punch_in) >= DATE('now', '-7 days') THEN 1 END) as last_7_days,
                    COUNT(CASE WHEN DATE(punch_in) >= DATE('now', '-30 days') THEN 1 END) as last_30_days,
                    COUNT(CASE WHEN DATE(punch_in) >= DATE('now', '-90 days') THEN 1 END) as last_90_days,
                    COUNT(CASE WHEN DATE(punch_in) < DATE('now', '-365 days') THEN 1 END) as older_than_year
                FROM time_entries
            ''')
            
            if period_stats:
                stats.update(dict(period_stats[0]))
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur statistiques historique: {e}")
            return {}
    
    def clear_all_time_entries(self, create_backup: bool = True) -> Dict:
        """Efface TOUT l'historique des pointages"""
        try:
            result = {
                'success': False,
                'entries_deleted': 0,
                'backup_created': False,
                'backup_data': None,
                'backup_filename': None,
                'message': ''
            }
            
            # Créer une sauvegarde si demandé
            if create_backup:
                backup_data, backup_filename = self.create_history_backup()
                if backup_data:
                    result['backup_created'] = True
                    result['backup_data'] = backup_data
                    result['backup_filename'] = backup_filename
            
            # Compter les entrées avant suppression
            count_result = self.db.execute_query("SELECT COUNT(*) as count FROM time_entries")
            entries_count = count_result[0]['count'] if count_result else 0
            
            # Supprimer toutes les entrées
            deleted = self.db.execute_update("DELETE FROM time_entries")
            
            result['entries_deleted'] = entries_count
            result['success'] = True
            result['message'] = f"✅ {entries_count} entrées supprimées avec succès"
            
            logger.warning(f"SUPPRESSION TOTALE: {entries_count} entrées de time_entries supprimées")
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur suppression totale: {e}")
            return {
                'success': False,
                'entries_deleted': 0,
                'message': f"❌ Erreur: {str(e)}"
            }
    
    def clear_time_entries_by_date_range(self, start_date: str, end_date: str, create_backup: bool = True) -> Dict:
        """Efface les pointages dans une plage de dates"""
        try:
            result = {
                'success': False,
                'entries_deleted': 0,
                'backup_created': False,
                'backup_data': None,
                'backup_filename': None,
                'message': ''
            }
            
            # Créer une sauvegarde si demandé
            if create_backup:
                backup_data, backup_filename = self.create_history_backup()
                if backup_data:
                    result['backup_created'] = True
                    result['backup_data'] = backup_data
                    result['backup_filename'] = backup_filename
            
            # Compter les entrées dans la plage
            count_query = '''
                SELECT COUNT(*) as count FROM time_entries 
                WHERE DATE(punch_in) BETWEEN ? AND ?
            '''
            count_result = self.db.execute_query(count_query, (start_date, end_date))
            entries_count = count_result[0]['count'] if count_result else 0
            
            if entries_count == 0:
                result['message'] = "Aucune entrée trouvée dans cette période"
                return result
            
            # Supprimer les entrées dans la plage
            delete_query = '''
                DELETE FROM time_entries 
                WHERE DATE(punch_in) BETWEEN ? AND ?
            '''
            deleted = self.db.execute_update(delete_query, (start_date, end_date))
            
            result['entries_deleted'] = entries_count
            result['success'] = True
            result['message'] = f"✅ {entries_count} entrées supprimées pour la période {start_date} à {end_date}"
            
            logger.warning(f"SUPPRESSION PAR PÉRIODE: {entries_count} entrées supprimées ({start_date} à {end_date})")
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur suppression par période: {e}")
            return {
                'success': False,
                'entries_deleted': 0,
                'message': f"❌ Erreur: {str(e)}"
            }
    
    def clear_time_entries_by_employee(self, employee_id: int, create_backup: bool = True) -> Dict:
        """Efface tous les pointages d'un employé spécifique"""
        try:
            result = {
                'success': False,
                'entries_deleted': 0,
                'backup_created': False,
                'backup_data': None,
                'backup_filename': None,
                'employee_name': '',
                'message': ''
            }
            
            # Récupérer le nom de l'employé
            emp_result = self.db.execute_query(
                "SELECT prenom || ' ' || nom as name FROM employees WHERE id = ?",
                (employee_id,)
            )
            employee_name = emp_result[0]['name'] if emp_result else f"ID {employee_id}"
            result['employee_name'] = employee_name
            
            # Créer une sauvegarde si demandé
            if create_backup:
                backup_data, backup_filename = self.create_history_backup()
                if backup_data:
                    result['backup_created'] = True
                    result['backup_data'] = backup_data
                    result['backup_filename'] = backup_filename
            
            # Compter les entrées de l'employé
            count_result = self.db.execute_query(
                "SELECT COUNT(*) as count FROM time_entries WHERE employee_id = ?",
                (employee_id,)
            )
            entries_count = count_result[0]['count'] if count_result else 0
            
            if entries_count == 0:
                result['message'] = f"Aucune entrée trouvée pour {employee_name}"
                return result
            
            # Supprimer les entrées de l'employé
            deleted = self.db.execute_update(
                "DELETE FROM time_entries WHERE employee_id = ?",
                (employee_id,)
            )
            
            result['entries_deleted'] = entries_count
            result['success'] = True
            result['message'] = f"✅ {entries_count} entrées supprimées pour {employee_name}"
            
            logger.warning(f"SUPPRESSION PAR EMPLOYÉ: {entries_count} entrées supprimées pour {employee_name} (ID: {employee_id})")
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur suppression par employé: {e}")
            return {
                'success': False,
                'entries_deleted': 0,
                'message': f"❌ Erreur: {str(e)}"
            }
    
    def clear_completed_entries_only(self, older_than_days: int = 30, create_backup: bool = True) -> Dict:
        """Efface seulement les pointages terminés plus vieux que X jours"""
        try:
            result = {
                'success': False,
                'entries_deleted': 0,
                'backup_created': False,
                'backup_data': None,
                'backup_filename': None,
                'message': ''
            }
            
            # Créer une sauvegarde si demandé
            if create_backup:
                backup_data, backup_filename = self.create_history_backup()
                if backup_data:
                    result['backup_created'] = True
                    result['backup_data'] = backup_data
                    result['backup_filename'] = backup_filename
            
            cutoff_date = (datetime.now() - timedelta(days=older_than_days)).strftime('%Y-%m-%d')
            
            # Compter les entrées terminées anciennes
            count_query = '''
                SELECT COUNT(*) as count FROM time_entries 
                WHERE punch_out IS NOT NULL 
                AND DATE(punch_in) < ?
            '''
            count_result = self.db.execute_query(count_query, (cutoff_date,))
            entries_count = count_result[0]['count'] if count_result else 0
            
            if entries_count == 0:
                result['message'] = f"Aucune entrée terminée trouvée avant {cutoff_date}"
                return result
            
            # Supprimer les entrées terminées anciennes
            delete_query = '''
                DELETE FROM time_entries 
                WHERE punch_out IS NOT NULL 
                AND DATE(punch_in) < ?
            '''
            deleted = self.db.execute_update(delete_query, (cutoff_date,))
            
            result['entries_deleted'] = entries_count
            result['success'] = True
            result['message'] = f"✅ {entries_count} entrées terminées supprimées (antérieures au {cutoff_date})"
            
            logger.warning(f"SUPPRESSION ENTRÉES TERMINÉES: {entries_count} entrées supprimées (avant {cutoff_date})")
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur suppression entrées terminées: {e}")
            return {
                'success': False,
                'entries_deleted': 0,
                'message': f"❌ Erreur: {str(e)}"
            }
    
    def clear_orphaned_entries(self, create_backup: bool = True) -> Dict:
        """Efface les pointages orphelins (projets/employés/opérations supprimés)"""
        try:
            result = {
                'success': False,
                'entries_deleted': 0,
                'backup_created': False,
                'backup_data': None,
                'backup_filename': None,
                'orphan_details': {},
                'message': ''
            }
            
            # Créer une sauvegarde si demandé
            if create_backup:
                backup_data, backup_filename = self.create_history_backup()
                if backup_data:
                    result['backup_created'] = True
                    result['backup_data'] = backup_data
                    result['backup_filename'] = backup_filename
            
            orphan_count = 0
            orphan_details = {}
            
            # 1. Pointages avec employés supprimés
            emp_orphans = self.db.execute_query('''
                SELECT COUNT(*) as count FROM time_entries te
                WHERE te.employee_id NOT IN (SELECT id FROM employees)
            ''')
            emp_count = emp_orphans[0]['count'] if emp_orphans else 0
            if emp_count > 0:
                self.db.execute_update('''
                    DELETE FROM time_entries 
                    WHERE employee_id NOT IN (SELECT id FROM employees)
                ''')
                orphan_count += emp_count
                orphan_details['employees'] = emp_count
            
            # 2. Pointages avec projets supprimés
            proj_orphans = self.db.execute_query('''
                SELECT COUNT(*) as count FROM time_entries te
                WHERE te.project_id IS NOT NULL 
                AND te.project_id NOT IN (SELECT id FROM projects)
            ''')
            proj_count = proj_orphans[0]['count'] if proj_orphans else 0
            if proj_count > 0:
                self.db.execute_update('''
                    DELETE FROM time_entries 
                    WHERE project_id IS NOT NULL 
                    AND project_id NOT IN (SELECT id FROM projects)
                ''')
                orphan_count += proj_count
                orphan_details['projects'] = proj_count
            
            # 3. Pointages avec opérations supprimées
            op_orphans = self.db.execute_query('''
                SELECT COUNT(*) as count FROM time_entries te
                WHERE te.operation_id IS NOT NULL 
                AND te.operation_id NOT IN (SELECT id FROM operations)
            ''')
            op_count = op_orphans[0]['count'] if op_orphans else 0
            if op_count > 0:
                self.db.execute_update('''
                    DELETE FROM time_entries 
                    WHERE operation_id IS NOT NULL 
                    AND operation_id NOT IN (SELECT id FROM operations)
                ''')
                orphan_count += op_count
                orphan_details['operations'] = op_count
            
            # 4. Pointages avec BT supprimés
            bt_orphans = self.db.execute_query('''
                SELECT COUNT(*) as count FROM time_entries te
                WHERE te.formulaire_bt_id IS NOT NULL 
                AND te.formulaire_bt_id NOT IN (
                    SELECT id FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL'
                )
            ''')
            bt_count = bt_orphans[0]['count'] if bt_orphans else 0
            if bt_count > 0:
                self.db.execute_update('''
                    DELETE FROM time_entries 
                    WHERE formulaire_bt_id IS NOT NULL 
                    AND formulaire_bt_id NOT IN (
                        SELECT id FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL'
                    )
                ''')
                orphan_count += bt_count
                orphan_details['bt_formulaires'] = bt_count
            
            result['entries_deleted'] = orphan_count
            result['orphan_details'] = orphan_details
            result['success'] = True
            
            if orphan_count > 0:
                result['message'] = f"✅ {orphan_count} entrées orphelines supprimées"
                logger.warning(f"SUPPRESSION ORPHELINS: {orphan_count} entrées supprimées - {orphan_details}")
            else:
                result['message'] = "Aucune entrée orpheline trouvée"
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur suppression orphelins: {e}")
            return {
                'success': False,
                'entries_deleted': 0,
                'message': f"❌ Erreur: {str(e)}"
            }
    
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
# UTILITAIRES DE RÉINITIALISATION INTERFACE
# =========================================================================

def reset_employee_selectors():
    """
    Fonction utilitaire pour réinitialiser tous les sélecteurs d'employés
    À utiliser après chaque pointage réussi pour forcer le retour à "-- Sélectionner un employé --"
    """
    # Marquer tous les sélecteurs pour réinitialisation
    st.session_state.reset_employee_selector = True
    st.session_state.reset_employee_hist_selector = True
    
    # Optionnel : nettoyer aussi les anciennes clés directement
    keys_to_reset = [
        "employee_punch_op_employee_select",
        "employee_hist_select",
        "employee_punch_op_project_bt_select",
        "employee_punch_op_operation_select"
    ]
    
    for key in keys_to_reset:
        if key in st.session_state:
            if key.endswith("_employee_select"):
                # Pour les sélecteurs d'employés, forcer None
                st.session_state[key] = None
            else:
                # Pour les autres, on peut les laisser ou les supprimer
                pass

def trigger_interface_reset(success_message: str = "✅ Opération terminée !"):
    """
    Déclenche la réinitialisation de l'interface après un pointage réussi
    """
    st.success(success_message)
    reset_employee_selectors()
    st.rerun()

# =========================================================================
# INTERFACES MODE SUPERVISEUR - INTERFACE COMPLÈTE ORIGINALE
# =========================================================================

def show_operation_punch_interface(tt):
    """Interface de pointage avancée avec sélection d'opérations - Version Superviseur/Admin"""
    
    st.markdown("#### 🔧 Pointage sur Opérations")
    
    # Section employés actifs avec opérations (TOUS les employés - Version Superviseur)
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

# =========================================================================
# INTERFACES MODE EMPLOYÉ - INTERFACE FILTRÉE NOUVELLE
# =========================================================================

def show_employee_punch_interface(tt):
    """Interface de pointage spécifique aux EMPLOYÉS - Vue filtrée par employé sélectionné"""
    
    st.markdown("#### 👤 Interface Employé - Pointage sur Opérations")
    st.info("🔧 **Interface simplifiée pour les employés** - Pointage granulaire sur opérations")
    
    # Section sélection employé d'abord
    st.markdown("##### 👤 Sélection Employé")
    
    employees = tt.get_all_employees()
    if not employees:
        st.warning("Aucun employé trouvé")
        return
    
    # Gestion de la réinitialisation automatique
    if 'reset_employee_selector' not in st.session_state:
        st.session_state.reset_employee_selector = False
    
    # Si réinitialisation demandée, forcer la valeur None
    if st.session_state.reset_employee_selector:
        st.session_state.employee_punch_op_employee_select = None
        st.session_state.reset_employee_selector = False
    
    employee_options = {None: "-- Sélectionner un employé --"}
    employee_options.update({emp['id']: f"{emp['display_name']} ({emp['poste']})" for emp in employees})
    
    selected_employee_id = st.selectbox(
        "👤 Sélectionner Employé:",
        options=list(employee_options.keys()),
        format_func=lambda x: employee_options[x],
        key="employee_punch_op_employee_select"
    )
    
    # Si aucun employé sélectionné, arrêter ici
    if selected_employee_id is None:
        st.info("👆 Veuillez sélectionner un employé pour continuer")
        return
    
    # Section employé pointé (seulement celui sélectionné)
    active_employees = tt.get_active_employees_with_operations()
    selected_active_employee = [emp for emp in active_employees if emp['id'] == selected_employee_id]
    
    if selected_active_employee:
        st.markdown("##### 🟢 Votre Pointage Actuel")
        
        emp = selected_active_employee[0]
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
            if st.button("🔴 Pointer Sortie", key=f"employee_out_op_{emp['id']}", use_container_width=True, type="primary"):
                notes = st.text_input(f"Notes sortie:", key=f"employee_notes_out_op_{emp['id']}")
                if tt.punch_out(emp['id'], notes):
                    trigger_interface_reset("✅ Pointage terminé !")
                else:
                    st.error("❌ Erreur pointage sortie")
        
        st.markdown("---")
    
    # Section nouveau pointage sur opération
    st.markdown("##### ➕ Nouveau Pointage sur Opération")
    
    # Affichage employé sélectionné (disposition verticale)
    st.info(f"👤 **Employé sélectionné:** {employee_options[selected_employee_id]}")
    
    # Sélection hiérarchique : Projet/BT puis Opération (disposition verticale)
    operations_hierarchy = tt.get_available_operations_hierarchical()
    
    if not operations_hierarchy:
        st.warning("Aucune opération disponible")
        return
    
    # Premier niveau : Projet/BT (disposition verticale)
    project_bt_options = list(operations_hierarchy.keys())
    selected_project_bt = st.selectbox(
        "📋 Sélectionner Projet/BT:",
        options=project_bt_options,
        key="employee_punch_op_project_bt_select"
    )
    
    # Deuxième niveau : Opération (disposition verticale)
    if selected_project_bt and selected_project_bt in operations_hierarchy:
        available_operations = operations_hierarchy[selected_project_bt]
        
        if available_operations:
            operation_options = {op['id']: op['display_name'] for op in available_operations}
            selected_operation_id = st.selectbox(
                "🔧 Sélectionner Opération:",
                options=list(operation_options.keys()),
                format_func=lambda x: operation_options[x],
                key="employee_punch_op_operation_select"
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
    notes = st.text_input("📝 Notes (optionnel):", key="employee_punch_op_notes")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("🟢 Pointer sur Opération", use_container_width=True, type="primary"):
            # Vérifier si l'employé est déjà pointé
            active_punch = tt.get_active_punch(selected_employee_id)
            if active_punch:
                current_op = active_punch.get('operation_description', 'Tâche générale')
                st.error(f"❌ {employee_options[selected_employee_id].split(' (')[0]} est déjà pointé sur: {current_op}")
            else:
                entry_id = tt.punch_in_operation(selected_employee_id, selected_operation_id, notes)
                if entry_id:
                    trigger_interface_reset(f"✅ Pointage sur opération démarré ! ID: {entry_id}")
                else:
                    st.error("❌ Erreur lors du pointage sur opération")
    
    with col_btn2:
        if st.button("🔴 Pointer Sortie", use_container_width=True):
            active_punch = tt.get_active_punch(selected_employee_id)
            if not active_punch:
                st.error(f"❌ {employee_options[selected_employee_id].split(' (')[0]} n'est pas pointé")
            else:
                if tt.punch_out(selected_employee_id, notes):
                    trigger_interface_reset("✅ Pointage terminé !")
                else:
                    st.error("❌ Erreur pointage sortie")

def show_employee_history_interface(tt):
    """Interface d'historique simplifiée pour les employés"""
    
    st.markdown("#### 📊 Mon Historique de Pointages")
    
    # Sélection employé
    employees = tt.get_all_employees()
    if not employees:
        st.warning("Aucun employé trouvé")
        return
    
    # Gestion de la réinitialisation automatique pour l'historique aussi
    if 'reset_employee_hist_selector' not in st.session_state:
        st.session_state.reset_employee_hist_selector = False
    
    # Si réinitialisation demandée, forcer la valeur None
    if st.session_state.reset_employee_hist_selector:
        st.session_state.employee_hist_select = None
        st.session_state.reset_employee_hist_selector = False
    
    employee_options = {None: "-- Sélectionner un employé --"}
    employee_options.update({emp['id']: f"{emp['display_name']} ({emp['poste']})" for emp in employees})
    
    selected_employee_id = st.selectbox(
        "👤 Sélectionner Employé:",
        options=list(employee_options.keys()),
        format_func=lambda x: employee_options[x],
        key="employee_hist_select"
    )
    
    # Si aucun employé sélectionné, arrêter ici
    if selected_employee_id is None:
        st.info("👆 Veuillez sélectionner un employé pour voir son historique")
        return
    
    # Filtres simples
    col1, col2 = st.columns(2)
    
    with col1:
        days_filter = st.selectbox("📅 Période:", [7, 14, 30], index=1, key="employee_hist_days")
    
    with col2:
        show_operations_only = st.checkbox("🔧 Opérations seulement", value=True, key="employee_hist_ops_only")
    
    # Récupérer l'historique pour cet employé uniquement
    history = tt.get_punch_history(selected_employee_id, days_filter)
    
    # Filtrer pour opérations seulement si demandé
    if show_operations_only:
        history = [h for h in history if h.get('operation_description')]
    
    if not history:
        st.info(f"Aucun pointage trouvé pour {employee_options[selected_employee_id].split(' (')[0]}")
        return
    
    # Résumé personnel
    total_sessions = len(history)
    completed_sessions = len([h for h in history if h['punch_out'] is not None])
    total_hours = sum(h['total_hours'] or 0 for h in history)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Mes Sessions", total_sessions)
    col2.metric("Terminées", completed_sessions)
    col3.metric("Mes Heures", f"{total_hours:.1f}h")
    
    # Tableau simplifié
    st.markdown("##### 📋 Mes Pointages")
    
    df_data = []
    for h in history:
        # Formatage pour employé
        if h['operation_description']:
            task_display = f"Op.{h['sequence_number']:02d}: {h['operation_description']}"
            if h['work_center_name']:
                task_display += f" ({h['work_center_name']})"
        else:
            task_display = "Tâche générale"
        
        project_display = f"{h['nom_projet']}"
        if h['bt_numero']:
            project_display += f" - BT {h['bt_numero']}"
        
        # Statut et durée
        if h['punch_out'] is None and h['punch_in']:
            try:
                start_time = datetime.fromisoformat(h['punch_in'])
                current_duration = (datetime.now() - start_time).total_seconds() / 3600
                status = f"🟢 En cours"
                hours_display = f"{current_duration:.1f}h"
            except:
                status = "🟢 En cours"
                hours_display = "En cours"
        else:
            status = "✅ Terminé"
            hours_display = f"{h['total_hours']:.1f}h" if h['total_hours'] else "0h"
        
        df_data.append({
            'Date': h['date_travail'],
            'Statut': status,
            'Projet': project_display,
            'Opération': task_display,
            'Début': h['punch_in'][-8:-3] if h['punch_in'] else 'N/A',
            'Fin': h['punch_out'][-8:-3] if h['punch_out'] else 'En cours',
            'Durée': hours_display,
            'Notes': h['notes'] or ''
        })
    
    if df_data:
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Bouton export personnel
        if st.button("📥 Exporter Mon Historique", use_container_width=True):
            csv = df.to_csv(index=False)
            employee_name = employee_options[selected_employee_id].split(' (')[0].replace(' ', '_')
            st.download_button(
                label="💾 Télécharger CSV",
                data=csv,
                file_name=f"historique_{employee_name}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

# =========================================================================
# INTERFACES COMMUNES - SUPERVISEUR ET EMPLOYÉ
# =========================================================================

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
# INTERFACE ADMINISTRATEUR - SECTION SUPERVISEUR SEULEMENT
# =========================================================================

def show_admin_interface(tt):
    """Interface d'administration avec gestion de l'historique"""
    
    st.markdown("#### ⚙️ Administration - Gestion de l'Historique")
    st.warning("🔒 **ZONE ADMINISTRATEUR** - Utilisez ces fonctions avec précaution")
    
    # Vérification de sécurité simple
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        st.markdown("##### 🔐 Authentification Administrateur")
        password = st.text_input("Mot de passe administrateur:", type="password", key="admin_password")
        
        if st.button("🔓 Se connecter"):
            # Mot de passe simple pour la démo - À changer en production !
            if password == "admin123":
                st.session_state.admin_authenticated = True
                st.success("✅ Authentification réussie")
                st.rerun()
            else:
                st.error("❌ Mot de passe incorrect")
        
        st.info("💡 **Mot de passe de démo:** admin123")
        return
    
    # Interface admin authentifiée
    st.success("🔓 **Connecté en tant qu'administrateur**")
    
    if st.button("🔒 Se déconnecter", key="admin_logout"):
        st.session_state.admin_authenticated = False
        st.rerun()
    
    # Statistiques de l'historique
    st.markdown("##### 📊 Statistiques de l'Historique")
    
    history_stats = tt.get_history_statistics()
    
    if history_stats:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Entrées", history_stats.get('total_entries', 0))
        col2.metric("Terminées", history_stats.get('completed_entries', 0))
        col3.metric("Actives", history_stats.get('active_entries', 0))
        col4.metric("Employés", history_stats.get('unique_employees', 0))
        
        col5, col6, col7, col8 = st.columns(4)
        col5.metric("Heures Total", f"{history_stats.get('total_hours', 0):.1f}h")
        col6.metric("Coût Total", f"{history_stats.get('total_cost', 0):,.0f}$")
        col7.metric("Première Entrée", history_stats.get('first_date', 'N/A'))
        col8.metric("Dernière Entrée", history_stats.get('last_date', 'N/A'))
        
        # Répartition par type
        st.markdown("**Répartition par Type:**")
        col_type1, col_type2, col_type3 = st.columns(3)
        col_type1.metric("Opérations", history_stats.get('operation_entries', 0))
        col_type2.metric("Tâches BT", history_stats.get('bt_entries', 0))
        col_type3.metric("Général", history_stats.get('general_entries', 0))
        
        # Répartition par période
        st.markdown("**Répartition par Période:**")
        col_per1, col_per2, col_per3, col_per4 = st.columns(4)
        col_per1.metric("7 derniers jours", history_stats.get('last_7_days', 0))
        col_per2.metric("30 derniers jours", history_stats.get('last_30_days', 0))
        col_per3.metric("90 derniers jours", history_stats.get('last_90_days', 0))
        col_per4.metric("Plus d'un an", history_stats.get('older_than_year', 0))
    
    st.markdown("---")
    
    # Options de suppression
    st.markdown("##### 🗑️ Options de Suppression d'Historique")
    
    # Créer les onglets pour différents types de suppression
    tab_all, tab_date, tab_employee, tab_completed, tab_orphans = st.tabs([
        "🔥 Tout Effacer", "📅 Par Période", "👤 Par Employé", "✅ Terminés Anciens", "🗑️ Orphelins"
    ])
    
    with tab_all:
        st.markdown("#### 🔥 Effacer TOUT l'Historique")
        st.error("⚠️ **DANGER** - Cette action supprimera TOUTES les entrées de pointage de manière permanente !")
        
        create_backup_all = st.checkbox("📦 Créer une sauvegarde avant suppression", value=True, key="backup_all")
        
        confirm_all = st.text_input(
            "Tapez 'SUPPRIMER TOUT' pour confirmer:",
            key="confirm_delete_all"
        )
        
        if st.button("🔥 EFFACER TOUT L'HISTORIQUE", type="primary", key="delete_all_btn"):
            if confirm_all == "SUPPRIMER TOUT":
                with st.spinner("Suppression en cours..."):
                    result = tt.clear_all_time_entries(create_backup_all)
                
                if result['success']:
                    st.success(result['message'])
                    
                    if result['backup_created'] and result['backup_data']:
                        st.download_button(
                            label="💾 Télécharger la Sauvegarde",
                            data=result['backup_data'],
                            file_name=result['backup_filename'],
                            mime="application/json"
                        )
                    
                    # Forcer le rechargement des stats
                    st.rerun()
                else:
                    st.error(result['message'])
            else:
                st.error("❌ Confirmation incorrecte. Tapez exactement 'SUPPRIMER TOUT'")
    
    with tab_date:
        st.markdown("#### 📅 Effacer par Période")
        
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input("Date de début:", key="delete_start_date")
        with col_date2:
            end_date = st.date_input("Date de fin:", key="delete_end_date")
        
        if start_date <= end_date:
            create_backup_date = st.checkbox("📦 Créer une sauvegarde avant suppression", value=True, key="backup_date")
            
            if st.button("🗑️ Effacer la Période", key="delete_date_btn"):
                with st.spinner("Suppression en cours..."):
                    result = tt.clear_time_entries_by_date_range(
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d'),
                        create_backup_date
                    )
                
                if result['success']:
                    st.success(result['message'])
                    
                    if result['backup_created'] and result['backup_data']:
                        st.download_button(
                            label="💾 Télécharger la Sauvegarde",
                            data=result['backup_data'],
                            file_name=result['backup_filename'],
                            mime="application/json"
                        )
                    
                    st.rerun()
                else:
                    st.error(result['message'])
        else:
            st.error("❌ La date de fin doit être postérieure à la date de début")
    
    with tab_employee:
        st.markdown("#### 👤 Effacer par Employé")
        
        employees = tt.get_all_employees()
        if employees:
            employee_options = {emp['id']: f"{emp['display_name']} ({emp['poste']})" for emp in employees}
            
            selected_emp_id = st.selectbox(
                "Sélectionner l'employé:",
                options=list(employee_options.keys()),
                format_func=lambda x: employee_options[x],
                key="delete_employee_select"
            )
            
            if selected_emp_id:
                # Afficher un aperçu des données de l'employé
                emp_stats = tt.get_employee_statistics(selected_emp_id, days=365)
                if emp_stats:
                    st.info(f"📊 Données trouvées: {emp_stats.get('total_sessions', 0)} sessions, {emp_stats.get('total_hours', 0):.1f}h")
                
                create_backup_emp = st.checkbox("📦 Créer une sauvegarde avant suppression", value=True, key="backup_emp")
                
                if st.button("🗑️ Effacer cet Employé", key="delete_emp_btn"):
                    with st.spinner("Suppression en cours..."):
                        result = tt.clear_time_entries_by_employee(selected_emp_id, create_backup_emp)
                    
                    if result['success']:
                        st.success(result['message'])
                        
                        if result['backup_created'] and result['backup_data']:
                            st.download_button(
                                label="💾 Télécharger la Sauvegarde",
                                data=result['backup_data'],
                                file_name=result['backup_filename'],
                                mime="application/json"
                            )
                        
                        st.rerun()
                    else:
                        st.error(result['message'])
        else:
            st.warning("Aucun employé trouvé")
    
    with tab_completed:
        st.markdown("#### ✅ Effacer les Pointages Terminés Anciens")
        st.info("💡 Cette option ne supprime que les pointages terminés, gardant les pointages actifs")
        
        older_than_days = st.number_input(
            "Supprimer les pointages terminés plus vieux que (jours):",
            min_value=1,
            max_value=365,
            value=30,
            key="older_than_days"
        )
        
        # Aperçu des données qui seraient supprimées
        cutoff_date = (datetime.now() - timedelta(days=older_than_days)).strftime('%Y-%m-%d')
        st.caption(f"Supprimera les pointages terminés avant le {cutoff_date}")
        
        create_backup_completed = st.checkbox("📦 Créer une sauvegarde avant suppression", value=True, key="backup_completed")
        
        if st.button("🗑️ Effacer les Pointages Terminés Anciens", key="delete_completed_btn"):
            with st.spinner("Suppression en cours..."):
                result = tt.clear_completed_entries_only(older_than_days, create_backup_completed)
            
            if result['success']:
                st.success(result['message'])
                
                if result['backup_created'] and result['backup_data']:
                    st.download_button(
                        label="💾 Télécharger la Sauvegarde",
                        data=result['backup_data'],
                        file_name=result['backup_filename'],
                        mime="application/json"
                    )
                
                st.rerun()
            else:
                st.error(result['message'])
    
    with tab_orphans:
        st.markdown("#### 🗑️ Nettoyer les Données Orphelines")
        st.info("💡 Supprime les pointages liés à des employés, projets, opérations ou BT supprimés")
        
        # Diagnostic préalable
        if st.button("🔍 Analyser les Orphelins", key="analyze_orphans"):
            diagnostic = tt.diagnostic_timetracker_data()
            
            if diagnostic.get('problemes_detectes'):
                st.markdown("**🚨 Problèmes détectés:**")
                for probleme in diagnostic['problemes_detectes']:
                    st.warning(probleme)
            else:
                st.success("✅ Aucun problème détecté dans les données")
        
        create_backup_orphans = st.checkbox("📦 Créer une sauvegarde avant suppression", value=True, key="backup_orphans")
        
        if st.button("🗑️ Nettoyer les Orphelins", key="delete_orphans_btn"):
            with st.spinner("Nettoyage en cours..."):
                result = tt.clear_orphaned_entries(create_backup_orphans)
            
            if result['success']:
                st.success(result['message'])
                
                if result.get('orphan_details'):
                    st.markdown("**Détail des suppressions:**")
                    for category, count in result['orphan_details'].items():
                        st.write(f"- {category}: {count} entrées")
                
                if result['backup_created'] and result['backup_data']:
                    st.download_button(
                        label="💾 Télécharger la Sauvegarde",
                        data=result['backup_data'],
                        file_name=result['backup_filename'],
                        mime="application/json"
                    )
                
                st.rerun()
            else:
                st.error(result['message'])
    
    st.markdown("---")
    
    # Outils de diagnostic
    st.markdown("##### 🔧 Outils de Diagnostic")
    
    col_diag1, col_diag2 = st.columns(2)
    
    with col_diag1:
        if st.button("🩺 Diagnostic Complet", key="full_diagnostic"):
            diagnostic = tt.diagnostic_timetracker_data()
            
            st.markdown("**📊 Résultats du Diagnostic:**")
            
            # Afficher les statistiques principales
            if diagnostic.get('time_entries'):
                te_stats = diagnostic['time_entries']
                st.json(te_stats)
            
            # Afficher les problèmes
            if diagnostic.get('problemes_detectes'):
                st.markdown("**🚨 Problèmes détectés:**")
                for probleme in diagnostic['problemes_detectes']:
                    st.error(probleme)
            else:
                st.success("✅ Système en bon état")
    
    with col_diag2:
        if st.button("🔧 Corriger les Orphelins BT", key="fix_orphans"):
            result = tt.corriger_pointages_bt_orphelins()
            
            if result.get('erreur'):
                st.error(f"❌ Erreur: {result['erreur']}")
            else:
                st.success(f"✅ {result['corrections_effectuees']} corrections effectuées sur {result['orphelins_trouves']} orphelins trouvés")
                
                if result.get('erreurs'):
                    st.warning("⚠️ Erreurs lors de certaines corrections:")
                    for erreur in result['erreurs']:
                        st.write(f"- {erreur}")

# =========================================================================
# INTERFACE PRINCIPALE MODIFIÉE - MODE EMPLOYÉ DIRECT
# =========================================================================

def show_timetracker_unified_interface():
    """Interface principale du TimeTracker unifié - MODE EMPLOYÉ DIRECT"""
    
    if 'timetracker_unified' not in st.session_state:
        st.error("❌ TimeTracker non initialisé")
        return
    
    tt = st.session_state.timetracker_unified
    
    st.markdown("### ⏱️ TimeTracker Unifié - Interface Employé")
    st.info("👤 **Interface Employé** - Vue personnelle simplifiée pour le pointage sur opérations")
    
    # MODE EMPLOYÉ DIRECT - Interface simplifiée (pas d'authentification requise)
    tab_employee_punch, tab_employee_history = st.tabs([
        "👤 Mon Pointage", "📊 Mon Historique"
    ])
    
    with tab_employee_punch:
        show_employee_punch_interface(tt)
    
    with tab_employee_history:
        # Interface historique simplifiée pour employés
        show_employee_history_interface(tt)

# =========================================================================
# NOUVELLE INTERFACE POUR ADMINISTRATEUR (si nécessaire)
# =========================================================================

def show_timetracker_supervisor_interface():
    """Interface TimeTracker pour superviseurs/administrateurs"""
    
    if 'timetracker_unified' not in st.session_state:
        st.error("❌ TimeTracker non initialisé")
        return
    
    tt = st.session_state.timetracker_unified
    
    st.markdown("### ⏱️ TimeTracker Unifié - Interface Superviseur")
    
    # Initialiser l'authentification superviseur
    if 'supervisor_authenticated' not in st.session_state:
        st.session_state.supervisor_authenticated = False
    
    # Vérification de l'authentification superviseur
    if not st.session_state.supervisor_authenticated:
        st.markdown("#### 🔐 Authentification Superviseur")
        st.warning("🔒 **Accès Restreint** - Authentification requise pour le mode superviseur")
        
        col_auth1, col_auth2 = st.columns(2)
        
        with col_auth1:
            supervisor_password = st.text_input(
                "Mot de passe superviseur:", 
                type="password", 
                key="supervisor_password",
                placeholder="Entrez le mot de passe superviseur"
            )
        
        with col_auth2:
            st.markdown("")  # Espacement
            if st.button("🔓 Se connecter comme Superviseur", type="primary"):
                # Mot de passe superviseur - À changer en production !
                if supervisor_password == "supervisor123":
                    st.session_state.supervisor_authenticated = True
                    st.success("✅ Authentification superviseur réussie")
                    st.rerun()
                else:
                    st.error("❌ Mot de passe superviseur incorrect")
        
        # Afficher les infos d'authentification
        with st.expander("💡 Informations d'authentification"):
            st.info("**Mot de passe superviseur de démo:** supervisor123")
            st.caption("🔒 En production, utilisez un mot de passe sécurisé et implémentez un système d'authentification plus robuste.")
        
        return
    
    # Interface superviseur authentifiée
    col_status1, col_status2 = st.columns([3, 1])
    
    with col_status1:
        st.success("🔓 **Connecté en mode Superviseur** - Accès complet autorisé")
    
    with col_status2:
        if st.button("🔒 Se déconnecter", key="supervisor_logout"):
            st.session_state.supervisor_authenticated = False
            st.rerun()
    
    st.markdown("---")
    
    # Mode superviseur - Interface complète avec tous les employés
    tab_operations, tab_history_op, tab_stats_op, tab_admin = st.tabs([
        "🔧 Pointage Opérations", "📊 Historique", "📈 Statistiques", "⚙️ Administration"
    ])
    
    with tab_operations:
        show_operation_punch_interface(tt)
    
    with tab_history_op:
        show_history_interface_operations(tt)
    
    with tab_stats_op:
        show_operation_statistics_interface(tt)
    
    with tab_admin:
        show_admin_interface(tt)

# =========================================================================
# FONCTIONS PRINCIPALES D'AFFICHAGE - DOUBLE MODE
# =========================================================================

def show_timetracker_unified_interface_main():
    """
    Point d'entrée pour l'ACCÈS EMPLOYÉ depuis le portail
    
    ACCÈS EMPLOYÉ:
    - Va directement au mode employé
    - Interface simplifiée sans sélecteur de mode
    - Vue personnelle filtrée par employé
    """
    show_timetracker_unified_interface()

def show_timetracker_admin_complete_interface():
    """
    Point d'entrée pour l'ACCÈS ADMINISTRATEUR depuis le portail
    
    ACCÈS ADMINISTRATEUR:
    - Interface complète avec sélecteur de mode
    - Choix entre Superviseur et Employé
    - Toutes les fonctionnalités administratives
    """
    
    if 'timetracker_unified' not in st.session_state:
        st.error("❌ TimeTracker non initialisé")
        return
    
    tt = st.session_state.timetracker_unified
    
    st.markdown("### ⏱️ TimeTracker Unifié - Interface Administrateur")
    
    # Initialiser l'authentification superviseur
    if 'supervisor_authenticated' not in st.session_state:
        st.session_state.supervisor_authenticated = False
    
    # Sélecteur de mode utilisateur COMPLET pour admin
    col_mode1, col_mode2 = st.columns(2)
    
    with col_mode1:
        user_mode = st.radio(
            "👥 Choisir le mode d'interface:",
            options=["superviseur", "employee"],
            format_func=lambda x: "🔧 Superviseur/Admin (voir tous les employés)" if x == "superviseur" else "👤 Employé (vue personnelle)",
            key="timetracker_admin_user_mode",
            horizontal=True
        )
    
    with col_mode2:
        if user_mode == "superviseur":
            st.info("🔧 **Mode Superviseur** - Gestion complète avec vue sur tous les employés pointés")
        else:
            st.info("👤 **Mode Employé** - Interface simplifiée avec vue filtrée par employé sélectionné")
    
    # Afficher l'interface selon le mode sélectionné
    if user_mode == "superviseur":
        # Vérification de l'authentification superviseur
        if not st.session_state.supervisor_authenticated:
            st.markdown("---")
            st.markdown("#### 🔐 Authentification Superviseur")
            st.warning("🔒 **Accès Restreint** - Authentification requise pour le mode superviseur")
            
            col_auth1, col_auth2 = st.columns(2)
            
            with col_auth1:
                supervisor_password = st.text_input(
                    "Mot de passe superviseur:", 
                    type="password", 
                    key="admin_supervisor_password",
                    placeholder="Entrez le mot de passe superviseur"
                )
            
            with col_auth2:
                st.markdown("")  # Espacement
                if st.button("🔓 Se connecter comme Superviseur", type="primary", key="admin_supervisor_login"):
                    # Mot de passe superviseur - À changer en production !
                    if supervisor_password == "supervisor123":
                        st.session_state.supervisor_authenticated = True
                        st.success("✅ Authentification superviseur réussie")
                        st.rerun()
                    else:
                        st.error("❌ Mot de passe superviseur incorrect")
            
            # Afficher les infos d'authentification
            with st.expander("💡 Informations d'authentification"):
                st.info("**Mot de passe superviseur de démo:** supervisor123")
                st.caption("🔒 En production, utilisez un mot de passe sécurisé et implémentez un système d'authentification plus robuste.")
            
            return
        
        # Interface superviseur authentifiée
        col_status1, col_status2 = st.columns([3, 1])
        
        with col_status1:
            st.success("🔓 **Connecté en mode Superviseur** - Accès complet autorisé")
        
        with col_status2:
            if st.button("🔒 Se déconnecter", key="admin_supervisor_logout"):
                st.session_state.supervisor_authenticated = False
                st.rerun()
        
        st.markdown("---")
        
        # Mode superviseur - Interface complète avec tous les employés
        tab_operations, tab_history_op, tab_stats_op, tab_admin = st.tabs([
            "🔧 Pointage Opérations", "📊 Historique", "📈 Statistiques", "⚙️ Administration"
        ])
        
        with tab_operations:
            show_operation_punch_interface(tt)
        
        with tab_history_op:
            show_history_interface_operations(tt)
        
        with tab_stats_op:
            show_operation_statistics_interface(tt)
        
        with tab_admin:
            show_admin_interface(tt)
    
    else:
        # Mode employé - Interface simplifiée (dans le contexte admin)
        st.markdown("---")
        
        tab_employee_punch, tab_employee_history = st.tabs([
            "👤 Pointage Employé", "📊 Historique Employé"
        ])
        
        with tab_employee_punch:
            show_employee_punch_interface(tt)
        
        with tab_employee_history:
            # Interface historique simplifiée pour employés
            show_employee_history_interface(tt)

# =========================================================================
# UTILITAIRES DE MAINTENANCE
# =========================================================================

def cleanup_timetracker_data(tt) -> Dict:
    """Nettoyage automatique des données TimeTracker"""
    try:
        cleanup_result = {
            'orphans_cleaned': 0,
            'old_entries_archived': 0,
            'invalid_entries_fixed': 0,
            'success': True,
            'message': ''
        }
        
        # 1. Nettoyer les orphelins
        orphan_result = tt.clear_orphaned_entries(create_backup=False)
        cleanup_result['orphans_cleaned'] = orphan_result.get('entries_deleted', 0)
        
        # 2. Corriger les BT orphelins
        bt_result = tt.corriger_pointages_bt_orphelins()
        cleanup_result['invalid_entries_fixed'] = bt_result.get('corrections_effectuees', 0)
        
        cleanup_result['message'] = f"✅ Nettoyage terminé: {cleanup_result['orphans_cleaned']} orphelins supprimés, {cleanup_result['invalid_entries_fixed']} entrées corrigées"
        
        return cleanup_result
        
    except Exception as e:
        logger.error(f"Erreur nettoyage: {e}")
        return {
            'success': False,
            'message': f"❌ Erreur lors du nettoyage: {e}"
        }

def initialize_timetracker_unified(db) -> TimeTrackerUnified:
    """
    Initialise le TimeTracker unifié avec vérifications
    """
    try:
        # Créer l'instance
        tt = TimeTrackerUnified(db)
        
        # Vérifier les tables nécessaires
        required_tables = ['time_entries', 'employees', 'projects', 'operations', 'work_centers', 'formulaires', 'formulaire_lignes']
        
        for table in required_tables:
            try:
                result = db.execute_query(f"SELECT COUNT(*) as count FROM {table} LIMIT 1")
                logger.info(f"Table {table}: {result[0]['count'] if result else 0} entrées")
            except Exception as e:
                logger.warning(f"Table {table} manquante ou inaccessible: {e}")
        
        # Diagnostic rapide
        diagnostic = tt.diagnostic_timetracker_data()
        if diagnostic.get('problemes_detectes'):
            logger.warning(f"Problèmes détectés lors de l'initialisation: {len(diagnostic['problemes_detectes'])}")
        
        logger.info("TimeTracker Unifié initialisé avec succès")
        return tt
        
    except Exception as e:
        logger.error(f"Erreur initialisation TimeTracker: {e}")
        raise

# =========================================================================
# FONCTIONS D'EXPORT/IMPORT POUR COMPATIBILITÉ
# =========================================================================

def export_timetracker_data(tt) -> str:
    """Exporte toutes les données TimeTracker en JSON"""
    try:
        export_data = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'version': '2.1',
                'type': 'timetracker_unified_export'
            },
            'time_entries': [],
            'statistics': tt.get_timetracker_statistics_unified()
        }
        
        # Récupérer toutes les entrées avec détails
        query = '''
            SELECT te.*, 
                   p.nom_projet, 
                   e.prenom || ' ' || e.nom as employee_name,
                   o.description as operation_description,
                   f.numero_document as bt_numero
            FROM time_entries te
            LEFT JOIN projects p ON te.project_id = p.id
            LEFT JOIN employees e ON te.employee_id = e.id
            LEFT JOIN operations o ON te.operation_id = o.id
            LEFT JOIN formulaires f ON te.formulaire_bt_id = f.id
            ORDER BY te.punch_in DESC
        '''
        
        rows = tt.db.execute_query(query)
        for row in rows:
            export_data['time_entries'].append(dict(row))
        
        return json.dumps(export_data, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Erreur export données: {e}")
        return None

def get_timetracker_summary_stats(tt) -> Dict:
    """Statistiques résumées pour l'affichage dans app.py"""
    try:
        stats = tt.get_timetracker_statistics_unified()
        
        return {
            'total_employees': stats.get('total_employees', 0),
            'active_entries': stats.get('active_entries', 0),
            'total_entries_today': stats.get('total_entries_today', 0),
            'total_hours_today': stats.get('total_hours_today', 0),
            'total_revenue_today': stats.get('total_revenue_today', 0),
            'operation_entries': stats.get('operation_entries', 0),
            'bt_entries': stats.get('bt_entries', 0)
        }
        
    except Exception as e:
        logger.error(f"Erreur stats résumées: {e}")
        return {}

# =========================================================================
# CONFIGURATION ET CONSTANTES
# =========================================================================

# Configuration par défaut
TIMETRACKER_CONFIG = {
    'default_hourly_rate': 25.0,
    'working_hours_per_year': 2080,
    'max_daily_hours': 12,
    'auto_cleanup_days': 90,
    'backup_retention_days': 30,
    'operation_id_offset': 100000,  # Pour différencier les tâches BT
    'default_work_center': 'Poste Manuel'
}

# Messages d'interface
INTERFACE_MESSAGES = {
    'employee_select_prompt': "👆 Veuillez sélectionner un employé pour continuer",
    'no_operations_available': "Aucune opération disponible",
    'already_punched_in': "est déjà pointé sur",
    'punch_in_success': "✅ Pointage sur opération démarré !",
    'punch_out_success': "✅ Pointage terminé !",
    'no_active_punch': "n'est pas pointé",
    'operation_selection_required': "Sélectionnez un projet/BT",
    'authentication_required': "🔒 Authentification requise",
    'access_granted': "🔓 Accès autorisé"
}

# Styles CSS pour l'interface (optionnel)
TIMETRACKER_STYLES = """
<style>
.timetracker-card {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #28a745;
    margin: 0.5rem 0;
}

.timetracker-warning {
    background: #fff3cd;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #ffc107;
    margin: 0.5rem 0;
}

.timetracker-error {
    background: #f8d7da;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #dc3545;
    margin: 0.5rem 0;
}

.employee-punch-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1.5rem;
    border-radius: 1rem;
    margin: 1rem 0;
}

.operation-card {
    background: #e3f2fd;
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #2196f3;
    margin: 0.5rem 0;
}
</style>
"""

# =========================================================================
# POINT D'ENTRÉE PRINCIPAL ET DOCUMENTATION
# =========================================================================

"""
TimeTracker Unifié - Système de Pointage sur Opérations
Version 2.1 - Double Interface : Employé Direct + Admin Complet
NOUVEAU: Réinitialisation automatique du sélecteur d'employé après chaque pointage

PRINCIPALES FONCTIONNALITÉS:
============================

1. POINTAGE SUR OPÉRATIONS:
   - Support des opérations classiques depuis la table 'operations'
   - Support des tâches BT depuis 'formulaire_lignes'
   - Sélection hiérarchique : Projet/BT → Opération
   - Calcul automatique des heures et coûts

2. DOUBLE INTERFACE ADAPTÉE AU PORTAIL:
   
   A) ACCÈS EMPLOYÉ (Portail section EMPLOYÉ):
      - Interface employé directe SANS sélecteur de mode
      - Aller directement aux onglets "Mon Pointage" et "Mon Historique"
      - Sélection d'employé puis opérations (disposition verticale)
      - Réinitialisation automatique après pointage (retour à "-- Sélectionner un employé --")
      - Fonction: show_timetracker_unified_interface_main()
   
   B) ACCÈS ADMINISTRATEUR (Portail section ADMINISTRATEUR):
      - Interface complète AVEC sélecteur de mode
      - Choix entre "🔧 Superviseur/Admin" et "👤 Employé"
      - Toutes les fonctionnalités administratives conservées
      - Authentification superviseur pour mode avancé
      - Fonction: show_timetracker_admin_complete_interface()

NOUVELLES FONCTIONNALITÉS v2.1:
============================

🔄 **RÉINITIALISATION AUTOMATIQUE:**
   - Après chaque pointage (entrée/sortie) réussi
   - Le sélecteur d'employé revient automatiquement à "-- Sélectionner un employé --"
   - Évite les erreurs de pointage (employé qui oublie de changer le nom)
   - Interface plus sécurisée pour un usage partagé/terminal de pointage
   - Workflow optimisé : sélectionner → pointer → automatiquement réinitialisé

3. MODE SUPERVISEUR (dans l'accès admin):
   - Authentification requise (supervisor123)
   - Vue complète sur tous les employés pointés
   - Outils d'administration et gestion historique
   - Statistiques avancées et diagnostics

4. GESTION DE L'HISTORIQUE:
   - Sauvegarde automatique avant suppression
   - Suppression par période, employé, ou type
   - Nettoyage des données orphelines
   - Export/Import des données

5. COMPATIBILITÉ:
   - Support des tâches BT avec ID décalé (>100000)
   - Unification des descriptions d'opérations
   - Statistiques pour app.py
   - Méthodes de diagnostic intégrées

UTILISATION DANS APP.PY:
========================

1. Pour l'accès EMPLOYÉ (bouton dans section EMPLOYÉ du portail):
   ```python
   if st.button("⏱️ TimeTracker Pro & Postes Unifiés"):
       st.session_state.current_page = "timetracker_employee"
   
   # Dans le router:
   elif st.session_state.current_page == "timetracker_employee":
       show_timetracker_unified_interface_main()  # Interface employé directe
   ```

2. Pour l'accès ADMINISTRATEUR (bouton dans section ADMINISTRATEUR du portail):
   ```python
   if st.button("⏱️ TimeTracker Unifié Complet"):
       st.session_state.current_page = "timetracker_admin_complete"
   
   # Dans le router:
   elif st.session_state.current_page == "timetracker_admin_complete":
       show_timetracker_admin_complete_interface()  # Interface complète avec choix
   ```

3. Pour initialiser (une seule fois):
   ```python
   from timetracker_unified import initialize_timetracker_unified
   
   if 'timetracker_unified' not in st.session_state:
       st.session_state.timetracker_unified = initialize_timetracker_unified(db)
   ```

RÉSULTAT FINAL:
===============

📊 PORTAIL DG INC:
├── 👤 EMPLOYÉ
│   └── ⏱️ TimeTracker Pro & Postes Unifiés
│       └── 🔄 Interface directe employé (SANS sélecteur)
│           ├── 👤 Mon Pointage (avec réinitialisation auto)
│           └── 📊 Mon Historique
│
└── 👑 ADMINISTRATEUR  
    └── ⏱️ TimeTracker Unifié Complet
        └── 🎛️ Interface complète (AVEC sélecteur)
            ├── 🔧 Mode Superviseur (auth requise)
            │   ├── 🔧 Pointage Opérations (tous employés)
            │   ├── 📊 Historique complet
            │   ├── 📈 Statistiques avancées
            │   └── ⚙️ Administration
            └── 👤 Mode Employé (dans contexte admin)
                ├── 👤 Pointage Employé (avec réinitialisation auto)
                └── 📊 Historique Employé

WORKFLOW DE POINTAGE OPTIMISÉ:
=============================

🔄 **TERMINAL DE POINTAGE PARTAGÉ:**
1. 👤 Employé A sélectionne son nom
2. 🟢 Pointe entrée sur opération
3. ✅ Message de succès
4. 🔄 **AUTOMATIQUEMENT** → Retour à "-- Sélectionner un employé --"
5. 👤 Employé B peut directement sélectionner son nom (aucun risque d'erreur)

MOTS DE PASSE DE DÉMO:
=====================
- Superviseur: supervisor123
- Administrateur: admin123

SÉCURITÉ:
=========
En production, remplacez les mots de passe codés en dur par un système 
d'authentification sécurisé avec base de données utilisateurs et hashage.

TABLES REQUISES:
================
- time_entries (table principale des pointages)
- employees (employés)
- projects (projets)
- operations (opérations classiques)
- work_centers (postes de travail)
- formulaires (BT)
- formulaire_lignes (tâches des BT)

LOGS:
=====
Utilisez logging pour suivre les opérations:
- INFO: Initialisation, pointages normaux
- WARNING: Données manquantes, corrections
- ERROR: Erreurs de base de données, échecs de pointage

MAINTENANCE:
============
- Exécutez cleanup_timetracker_data() périodiquement
- Sauvegardez les données avec export_timetracker_data()
- Vérifiez les diagnostics avec diagnostic_timetracker_data()

FONCTIONS UTILITAIRES DE RÉINITIALISATION:
==========================================
- reset_employee_selectors() : Réinitialise tous les sélecteurs d'employés
- trigger_interface_reset() : Déclenche réinitialisation + message succès + rerun
"""

if __name__ == "__main__":
    # Test d'import - ne pas exécuter directement
    print("TimeTracker Unifié v2.1 - Double Interface avec Réinitialisation Auto")
    print("FONCTIONS PRINCIPALES:")
    print("- show_timetracker_unified_interface_main() : Accès EMPLOYÉ direct avec auto-reset")
    print("- show_timetracker_admin_complete_interface() : Accès ADMIN complet")
    print("- show_timetracker_supervisor_interface() : Superviseur standalone")
    print("- reset_employee_selectors() : Réinitialise les sélecteurs")
    print("- trigger_interface_reset() : Déclenche réinitialisation complète")
    print("\nCe module doit être importé dans app.py")
    print("Consultez la documentation ci-dessus pour l'utilisation.")
