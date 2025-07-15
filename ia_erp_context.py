"""
Module de contexte ERP pour l'intégration IA
Permet à l'IA d'accéder aux données de l'ERP de manière sécurisée
"""

import streamlit as st
import json
from datetime import datetime, timedelta
import pandas as pd

class ERPContextProvider:
    """
    Fournit un accès contextuel aux données de l'ERP pour l'IA
    """
    
    def __init__(self, erp_db=None, permissions=None):
        """
        Initialise le fournisseur de contexte
        
        Args:
            erp_db: Instance de ERPDatabase
            permissions: Liste des permissions de l'utilisateur
        """
        self.erp_db = erp_db or st.session_state.get('erp_db')
        
        # Si pas de DB dans session_state, essayer de se connecter directement
        if self.erp_db is None:
            print("[IA Context] Pas de DB dans session_state, tentative de connexion directe...")
            try:
                from erp_database import ERPDatabase
                from database_config import DATABASE_PATH
                import os
                
                print(f"[IA Context] DATABASE_PATH depuis config: {DATABASE_PATH}")
                print(f"[IA Context] Fichier existe: {os.path.exists(DATABASE_PATH)}")
                
                # Utiliser le chemin de la configuration
                if os.path.exists(DATABASE_PATH):
                    print("[IA Context] Création de l'instance ERPDatabase...")
                    self.erp_db = ERPDatabase(DATABASE_PATH)
                    # Stocker dans session_state pour les prochaines utilisations
                    st.session_state['erp_db'] = self.erp_db
                    print(f"[IA Context] ✓ Connexion établie avec la DB: {DATABASE_PATH}")
                else:
                    print(f"[IA Context] ❌ Base de données non trouvée: {DATABASE_PATH}")
            except Exception as e:
                print(f"[IA Context] ❌ Erreur lors de la connexion directe à la DB: {e}")
                import traceback
                print(f"[IA Context] Traceback: {traceback.format_exc()}")
        
        self.permissions = permissions or st.session_state.get('admin_permissions', ["ALL"])
        self.has_all_permissions = "ALL" in self.permissions or len(self.permissions) == 0
        
        # Mode dégradé si pas de DB
        self.demo_mode = self.erp_db is None
    
    def get_context_summary(self):
        """
        Retourne un résumé général du contexte ERP
        """
        summary = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'company': 'DG Inc.',
            'industry': 'Fabrication métallurgique',
            'modules_available': self._get_available_modules(),
            'database_connected': not self.demo_mode
        }
        
        # Ajouter des statistiques générales
        if self.erp_db and not self.demo_mode:
            try:
                summary['statistics'] = {
                    'total_projects': self._safe_query("SELECT COUNT(*) as count FROM projects", {'count': 0})['count'],
                    'total_clients': self._safe_query("SELECT COUNT(*) as count FROM companies", {'count': 0})['count'],
                    'total_employees': self._safe_query("SELECT COUNT(*) as count FROM employees", {'count': 0})['count'],
                    'total_formulaires': self._safe_query("SELECT COUNT(*) as count FROM formulaires WHERE type_formulaire = 'DEVIS'", {'count': 0})['count']
                }
                summary['database_status'] = 'Connecté avec succès'
            except Exception as e:
                summary['database_status'] = f'Erreur de connexion: {str(e)}'
        else:
            summary['database_status'] = 'Non connecté'
        
        return summary
    
    def search_projects(self, query=None, status=None, client=None, limit=10):
        """
        Recherche des projets selon les critères
        """
        if not self._can_access('projects'):
            return {'error': 'Accès non autorisé aux projets'}
        
        try:
            sql = "SELECT * FROM projects WHERE 1=1"
            params = []
            
            if query:
                sql += " AND (nom_projet LIKE ? OR description LIKE ? OR numero_projet LIKE ?)"
                params.extend([f"%{query}%"] * 3)
            
            if status:
                sql += " AND statut = ?"
                params.append(status)
            
            if client:
                sql += " AND (client_company_id = ? OR client_legacy LIKE ?)"
                params.extend([client, f"%{client}%"])
            
            sql += " ORDER BY date_soumis DESC LIMIT ?"
            params.append(limit)
            
            with self.erp_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                
                projects = []
                for row in rows:
                    project = dict(zip(columns, row))
                    # Ajouter le nom du client
                    if project.get('client_company_id'):
                        client_info = self._get_company_name(project['client_company_id'])
                        project['client_name'] = client_info
                    projects.append(project)
                
                return {
                    'success': True,
                    'count': len(projects),
                    'projects': projects
                }
                
        except Exception as e:
            return {'error': f'Erreur lors de la recherche: {str(e)}'}
    
    def search_devis(self, query=None, status=None, client=None, limit=10):
        """
        Recherche des devis selon les critères
        """
        if not self._can_access('crm'):
            return {'error': 'Accès non autorisé aux devis'}
        
        try:
            sql = """
                SELECT f.*, c.nom as client_nom
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                WHERE f.type_formulaire = 'DEVIS'
            """
            params = []
            
            if query:
                sql += " AND (f.numero_document LIKE ? OR f.notes LIKE ?)"
                params.extend([f"%{query}%"] * 2)
            
            if status:
                sql += " AND f.statut = ?"
                params.append(status)
            
            if client:
                sql += " AND (c.nom LIKE ? OR f.company_id = ?)"
                params.extend([f"%{client}%", client])
            
            sql += " ORDER BY f.date_creation DESC LIMIT ?"
            params.append(limit)
            
            with self.erp_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                
                devis = [dict(zip(columns, row)) for row in rows]
                
                return {
                    'success': True,
                    'count': len(devis),
                    'devis': devis
                }
                
        except Exception as e:
            return {'error': f'Erreur lors de la recherche: {str(e)}'}
    
    def get_client_info(self, client_id=None, client_name=None):
        """
        Obtient les informations détaillées d'un client
        """
        if not self._can_access('crm'):
            return {'error': 'Accès non autorisé aux données clients'}
        
        try:
            if client_id:
                sql = "SELECT * FROM companies WHERE id = ?"
                params = [client_id]
            elif client_name:
                sql = "SELECT * FROM companies WHERE nom LIKE ?"
                params = [f"%{client_name}%"]
            else:
                return {'error': 'ID ou nom du client requis'}
            
            with self.erp_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                columns = [col[0] for col in cursor.description]
                row = cursor.fetchone()
                
                if row:
                    company = dict(zip(columns, row))
                    
                    # Ajouter les contacts
                    cursor.execute("SELECT * FROM contacts WHERE company_id = ?", [company['id']])
                    contact_cols = [col[0] for col in cursor.description]
                    contacts = [dict(zip(contact_cols, row)) for row in cursor.fetchall()]
                    company['contacts'] = contacts
                    
                    # Ajouter l'historique des projets
                    cursor.execute("""
                        SELECT id, nom_projet, statut, prix_estime, date_creation 
                        FROM projects 
                        WHERE client_company_id = ? 
                        ORDER BY date_creation DESC 
                        LIMIT 10
                    """, [company['id']])
                    project_cols = [col[0] for col in cursor.description]
                    projects = [dict(zip(project_cols, row)) for row in cursor.fetchall()]
                    company['recent_projects'] = projects
                    
                    return {
                        'success': True,
                        'company': company
                    }
                else:
                    return {'error': 'Client non trouvé'}
                    
        except Exception as e:
            return {'error': f'Erreur: {str(e)}'}
    
    def get_inventory_status(self, item_name=None, category=None):
        """
        Obtient le statut de l'inventaire
        """
        if not self._can_access('inventory'):
            return {'error': 'Accès non autorisé à l\'inventaire'}
        
        try:
            sql = "SELECT * FROM inventory_items WHERE 1=1"
            params = []
            
            if item_name:
                sql += " AND (nom LIKE ? OR description LIKE ?)"
                params.extend([f"%{item_name}%"] * 2)
            
            if category:
                sql += " AND categorie = ?"
                params.append(category)
            
            sql += " ORDER BY nom"
            
            with self.erp_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                
                items = []
                for row in rows:
                    item = dict(zip(columns, row))
                    # Déterminer le statut du stock
                    if item['quantite_stock'] <= 0:
                        item['stock_status'] = 'ÉPUISÉ'
                    elif item['quantite_stock'] <= item.get('stock_minimum', 10):
                        item['stock_status'] = 'CRITIQUE'
                    elif item['quantite_stock'] <= item.get('stock_minimum', 10) * 2:
                        item['stock_status'] = 'FAIBLE'
                    else:
                        item['stock_status'] = 'DISPONIBLE'
                    
                    items.append(item)
                
                return {
                    'success': True,
                    'count': len(items),
                    'items': items
                }
                
        except Exception as e:
            return {'error': f'Erreur: {str(e)}'}
    
    def get_production_status(self, project_id=None):
        """
        Obtient le statut de production pour un projet
        """
        if not self._can_access('production'):
            return {'error': 'Accès non autorisé à la production'}
        
        try:
            if project_id:
                # Obtenir les opérations du projet
                sql = """
                    SELECT o.*, wc.nom as poste_nom, wc.taux_horaire
                    FROM operations o
                    LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                    WHERE o.project_id = ?
                    ORDER BY o.ordre
                """
                
                with self.erp_db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(sql, [project_id])
                    columns = [col[0] for col in cursor.description]
                    operations = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    
                    # Calculer les statistiques
                    total_operations = len(operations)
                    completed = sum(1 for op in operations if op.get('statut') == 'TERMINÉ')
                    in_progress = sum(1 for op in operations if op.get('statut') == 'EN_COURS')
                    
                    return {
                        'success': True,
                        'project_id': project_id,
                        'operations': operations,
                        'statistics': {
                            'total': total_operations,
                            'completed': completed,
                            'in_progress': in_progress,
                            'completion_rate': round((completed / total_operations * 100) if total_operations > 0 else 0, 1)
                        }
                    }
            else:
                # Vue d'ensemble de la production
                return self._get_production_overview()
                
        except Exception as e:
            return {'error': f'Erreur: {str(e)}'}
    
    def get_employee_info(self, employee_id=None, employee_name=None):
        """
        Obtient les informations d'un employé
        """
        if not self._can_access('employees'):
            return {'error': 'Accès non autorisé aux données employés'}
        
        try:
            if employee_id:
                sql = "SELECT * FROM employees WHERE id = ?"
                params = [employee_id]
            elif employee_name:
                sql = "SELECT * FROM employees WHERE nom LIKE ? OR prenom LIKE ?"
                params = [f"%{employee_name}%", f"%{employee_name}%"]
            else:
                return {'error': 'ID ou nom de l\'employé requis'}
            
            with self.erp_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                columns = [col[0] for col in cursor.description]
                row = cursor.fetchone()
                
                if row:
                    employee = dict(zip(columns, row))
                    
                    # Ajouter les compétences
                    cursor.execute("""
                        SELECT competence FROM employee_competences 
                        WHERE employee_id = ?
                    """, [employee['id']])
                    employee['competences'] = [row[0] for row in cursor.fetchall()]
                    
                    return {
                        'success': True,
                        'employee': employee
                    }
                else:
                    return {'error': 'Employé non trouvé'}
                    
        except Exception as e:
            return {'error': f'Erreur: {str(e)}'}
    
    def format_for_ai(self, data):
        """
        Formate les données pour une utilisation optimale par l'IA
        """
        if isinstance(data, dict) and 'error' in data:
            return f"Erreur: {data['error']}"
        
        if isinstance(data, dict) and 'success' in data:
            # Retirer les champs techniques
            formatted = {}
            for key, value in data.items():
                if key not in ['success', 'created_at', 'updated_at', 'deleted_at']:
                    if isinstance(value, list) and len(value) > 0:
                        # Limiter les listes longues
                        if len(value) > 5:
                            formatted[key] = value[:5] + [f"... et {len(value) - 5} autres éléments"]
                        else:
                            formatted[key] = value
                    elif value is not None:
                        formatted[key] = value
            
            return json.dumps(formatted, ensure_ascii=False, indent=2)
        
        return str(data)
    
    # Méthodes privées
    
    def _can_access(self, module):
        """Vérifie si l'utilisateur peut accéder à un module"""
        if self.has_all_permissions:
            return True
        
        module_permissions = {
            'projects': ['projects'],
            'crm': ['crm'],
            'inventory': ['inventory', 'production'],
            'production': ['production', 'work_centers'],
            'employees': ['employees'],
            'devis': ['crm']
        }
        
        required = module_permissions.get(module, [])
        return any(perm in self.permissions for perm in required)
    
    def _get_available_modules(self):
        """Retourne la liste des modules accessibles"""
        all_modules = ['projects', 'crm', 'devis', 'inventory', 'production', 'employees']
        return [m for m in all_modules if self._can_access(m)]
    
    def _safe_query(self, sql, default=None):
        """Exécute une requête de manière sécurisée"""
        if self.demo_mode or not self.erp_db:
            return default or {}
            
        try:
            with self.erp_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                row = cursor.fetchone()
                if row:
                    columns = [col[0] for col in cursor.description]
                    return dict(zip(columns, row))
        except Exception as e:
            print(f"Erreur requête SQL dans _safe_query: {e}")
            print(f"SQL: {sql}")
        return default or {}
    
    def _get_company_name(self, company_id):
        """Obtient le nom d'une entreprise par son ID"""
        try:
            result = self._safe_query(
                "SELECT nom FROM companies WHERE id = ?",
                {'nom': 'N/A'}
            )
            return result.get('nom', 'N/A')
        except:
            return 'N/A'
    
    def _get_production_overview(self):
        """Obtient une vue d'ensemble de la production"""
        try:
            with self.erp_db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Statistiques des postes de travail
                cursor.execute("""
                    SELECT COUNT(*) as total_postes,
                           SUM(CASE WHEN type_poste LIKE '%ROBOT%' THEN 1 ELSE 0 END) as robots,
                           SUM(CASE WHEN type_poste LIKE '%CNC%' THEN 1 ELSE 0 END) as cnc
                    FROM work_centers
                """)
                poste_stats = cursor.fetchone()
                
                # Opérations en cours
                cursor.execute("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN statut = 'EN_COURS' THEN 1 ELSE 0 END) as en_cours,
                           SUM(CASE WHEN statut = 'TERMINÉ' THEN 1 ELSE 0 END) as termines
                    FROM operations
                    WHERE date_creation > date('now', '-30 days')
                """)
                ops_stats = cursor.fetchone()
                
                return {
                    'success': True,
                    'work_centers': {
                        'total': poste_stats[0],
                        'robots': poste_stats[1],
                        'cnc': poste_stats[2]
                    },
                    'operations_30_days': {
                        'total': ops_stats[0],
                        'in_progress': ops_stats[1],
                        'completed': ops_stats[2]
                    }
                }
                
        except Exception as e:
            return {'error': f'Erreur: {str(e)}'}


# Fonctions utilitaires pour l'intégration IA

def create_erp_context_for_ai():
    """
    Crée un contexte ERP enrichi pour l'IA
    """
    # Créer le provider qui tentera de se connecter à la DB
    provider = ERPContextProvider()
    
    # Vérifier si la connexion a réussi
    if provider.demo_mode:
        return "Contexte ERP non disponible - Base de données non trouvée"
    
    context_summary = provider.get_context_summary()
    
    context_text = f"""
Contexte ERP - {context_summary['company']}
Date: {context_summary['timestamp']}
Industrie: {context_summary['industry']}

Statistiques générales:
- Projets actifs: {context_summary.get('statistics', {}).get('total_projects', 0)}
- Clients: {context_summary.get('statistics', {}).get('total_clients', 0)}
- Employés: {context_summary.get('statistics', {}).get('total_employees', 0)}
- Devis: {context_summary.get('statistics', {}).get('total_devis', 0)}

Modules disponibles: {', '.join(context_summary.get('modules_available', []))}

Vous avez accès aux données de l'ERP et pouvez rechercher:
- Projets (par nom, statut, client)
- Devis (par numéro, titre, client)
- Clients (informations détaillées)
- Inventaire (stock, disponibilité)
- Production (statut, opérations)
- Employés (compétences, informations)
"""
    
    return context_text


def enhance_ai_prompt_with_erp(original_prompt, user_query):
    """
    Enrichit le prompt de l'IA avec des données ERP pertinentes
    """
    provider = ERPContextProvider()
    enhanced_prompt = original_prompt
    
    # Analyser la requête pour détecter les intentions
    query_lower = user_query.lower()
    
    # Détection des entités et recherches automatiques
    erp_data = []
    
    # Recherche de projets
    if any(word in query_lower for word in ['projet', 'project', 'chantier', 'commande']):
        result = provider.search_projects(limit=5)
        if result.get('success') and result.get('projects'):
            erp_data.append(f"\nProjets récents:\n{provider.format_for_ai(result)}")
    
    # Recherche de devis
    if any(word in query_lower for word in ['devis', 'estimation', 'quote', 'soumission']):
        result = provider.search_devis(limit=5)
        if result.get('success') and result.get('devis'):
            erp_data.append(f"\nDevis récents:\n{provider.format_for_ai(result)}")
    
    # Recherche de clients
    if any(word in query_lower for word in ['client', 'customer', 'entreprise']):
        # Extraire le nom du client si mentionné
        for word in query_lower.split():
            if len(word) > 3:  # Nom potentiel
                result = provider.get_client_info(client_name=word)
                if result.get('success'):
                    erp_data.append(f"\nInformations client:\n{provider.format_for_ai(result)}")
                    break
    
    # Vérification inventaire
    if any(word in query_lower for word in ['stock', 'inventaire', 'inventory', 'matériel', 'pièce']):
        result = provider.get_inventory_status()
        if result.get('success'):
            erp_data.append(f"\nStatut inventaire:\n{provider.format_for_ai(result)}")
    
    # Statut production
    if any(word in query_lower for word in ['production', 'fabrication', 'usinage', 'opération']):
        result = provider.get_production_status()
        if result.get('success'):
            erp_data.append(f"\nStatut production:\n{provider.format_for_ai(result)}")
    
    # Ajouter les données ERP au prompt
    if erp_data:
        enhanced_prompt += f"\n\n=== DONNÉES ERP DISPONIBLES ===\n"
        enhanced_prompt += create_erp_context_for_ai()
        enhanced_prompt += "\n".join(erp_data)
        enhanced_prompt += "\n\nUtilisez ces données pour fournir une réponse précise et contextuelle."
    
    return enhanced_prompt