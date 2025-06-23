# -*- coding: utf-8 -*-
"""
Production Management Module - DG Inc.
Système MRP/Production complet avec interface ERP
Intégration complète aux tables existantes de erp_database.py

Author: Assistant Claude
Date: 2025-06-23
Version: 2.0 - Complete Refactor
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import time
from typing import Dict, List, Optional, Tuple
import logging

# Import de la base de données ERP
try:
    from erp_database import ERPDatabase
except ImportError:
    st.error("❌ Module erp_database non trouvé. Vérifiez l'installation.")
    st.stop()

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTES ET CONFIGURATIONS
# =============================================================================

# Types de produits disponibles
PRODUCT_TYPES = {
    'PRODUIT_FINI': '🏆 Produit Fini',
    'SOUS_ASSEMBLAGE': '🔧 Sous-Assemblage',
    'COMPOSANT': '⚙️ Composant',
    'MATIERE_PREMIERE': '🧱 Matière Première'
}

# Statuts des bons de travail
WORK_ORDER_STATUSES = {
    'BROUILLON': '📝 Brouillon',
    'VALIDE': '✅ Validé',
    'EN_COURS': '🚀 En Cours',
    'SUSPEND': '⏸️ Suspendu',
    'TERMINE': '🎯 Terminé',
    'ANNULE': '❌ Annulé'
}

# Priorités des bons de travail
WORK_ORDER_PRIORITIES = {
    'FAIBLE': '🟢 Faible',
    'NORMALE': '🟡 Normale',
    'URGENTE': '🔴 Urgente'
}

# Types de BOM
BOM_TYPES = {
    'MANUFACTURE': 'Manufacture this product',
    'KIT': 'Kit',
    'SUBCONTRACTING': 'Subcontracting'
}

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def format_currency(amount: float) -> str:
    """Formate un montant en devise"""
    return f"{amount:,.2f} $"

def format_duration(minutes: float) -> str:
    """Formate une durée en minutes vers format lisible"""
    if minutes < 60:
        return f"{minutes:.0f} min"
    else:
        hours = minutes / 60
        return f"{hours:.1f} h"

def calculate_work_days_between(start_date: datetime, end_date: datetime) -> int:
    """Calcule le nombre de jours ouvrables entre deux dates"""
    from datetime import timedelta
    
    days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Exclure les weekends (samedi=5, dimanche=6)
        if current_date.weekday() < 5:
            days += 1
        current_date += timedelta(days=1)
    
    return days

def get_status_color(status: str) -> str:
    """Retourne la couleur associée à un statut"""
    colors = {
        'ACTIF': 'green',
        'BROUILLON': 'orange',
        'VALIDE': 'blue',
        'EN_COURS': 'green',
        'TERMINE': 'green',
        'SUSPEND': 'orange',
        'ANNULE': 'red',
        'SUPPRIME': 'gray'
    }
    return colors.get(status, 'gray')

def validate_bom_data(bom_data: Dict) -> Tuple[bool, str]:
    """Valide les données d'une BOM"""
    required_fields = ['component_code', 'designation', 'quantity', 'unit']
    
    for field in required_fields:
        if not bom_data.get(field):
            return False, f"Le champ '{field}' est obligatoire"
    
    if bom_data.get('quantity', 0) <= 0:
        return False, "La quantité doit être supérieure à 0"
    
    if bom_data.get('unit_price', 0) < 0:
        return False, "Le prix unitaire ne peut pas être négatif"
    
    return True, "OK"

def validate_operation_data(operation_data: Dict) -> Tuple[bool, str]:
    """Valide les données d'une opération"""
    required_fields = ['sequence_number', 'description', 'duration']
    
    for field in required_fields:
        if not operation_data.get(field):
            return False, f"Le champ '{field}' est obligatoire"
    
    if operation_data.get('sequence_number', 0) <= 0:
        return False, "Le numéro de séquence doit être supérieur à 0"
    
    if operation_data.get('duration', 0) <= 0:
        return False, "La durée doit être supérieure à 0"
    
    return True, "OK"

def create_backup_filename(original_filename: str) -> str:
    """Crée un nom de fichier de backup avec timestamp"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    name_parts = original_filename.split('.')
    if len(name_parts) > 1:
        return f"{'.'.join(name_parts[:-1])}_backup_{timestamp}.{name_parts[-1]}"
    else:
        return f"{original_filename}_backup_{timestamp}"

class ProductionMetrics:
    """Classe pour calculer les métriques de production"""
    
    @staticmethod
    def calculate_efficiency(planned_time: float, actual_time: float) -> float:
        """Calcule l'efficacité (temps planifié / temps réel)"""
        if actual_time <= 0:
            return 0.0
        return (planned_time / actual_time) * 100
    
    @staticmethod
    def calculate_utilization(used_time: float, available_time: float) -> float:
        """Calcule le taux d'utilisation"""
        if available_time <= 0:
            return 0.0
        return (used_time / available_time) * 100
    
    @staticmethod
    def calculate_productivity(units_produced: int, time_hours: float) -> float:
        """Calcule la productivité (unités/heure)"""
        if time_hours <= 0:
            return 0.0
        return units_produced / time_hours
    
    @staticmethod
    def calculate_cost_variance(budgeted_cost: float, actual_cost: float) -> Dict:
        """Calcule la variance de coût"""
        variance = actual_cost - budgeted_cost
        variance_percent = (variance / budgeted_cost * 100) if budgeted_cost > 0 else 0
        
        return {
            'variance_amount': variance,
            'variance_percent': variance_percent,
            'status': 'OVER' if variance > 0 else 'UNDER' if variance < 0 else 'ON_BUDGET'
        }

# =============================================================================
# TESTS ET VALIDATION DES CLASSES GESTIONNAIRES
# =============================================================================

def test_managers_functionality():
    """Teste la fonctionnalité de base de tous les gestionnaires"""
    try:
        # Test connexion base de données
        db = ERPDatabase()
        
        # Test ProductManager
        product_manager = ProductManager(db)
        products = product_manager.get_all_products()
        logger.info(f"✅ ProductManager: {len(products)} produits récupérés")
        
        # Test BOMManager
        bom_manager = BOMManager(db)
        if not products.empty:
            test_product_id = products.iloc[0]['id']
            bom = bom_manager.get_bom_for_product(test_product_id)
            logger.info(f"✅ BOMManager: BOM récupérée pour produit {test_product_id}")
        
        # Test RoutingManager
        routing_manager = RoutingManager(db)
        work_centers = routing_manager.get_available_work_centers()
        logger.info(f"✅ RoutingManager: {len(work_centers)} postes de travail disponibles")
        
        # Test WorkOrderManager
        work_order_manager = WorkOrderManager(db, bom_manager, routing_manager)
        all_work_orders = work_order_manager.get_all_work_orders()
        logger.info(f"✅ WorkOrderManager: {len(all_work_orders)} bons de travail en base")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur test gestionnaires: {e}")
        return False

def initialize_production_system():
    """Initialise le système de production et vérifie les prérequis"""
    try:
        # Vérification base de données
        db = ERPDatabase()
        
        # Vérifier les tables critiques
        required_tables = ['projects', 'materials', 'operations', 'work_centers', 'formulaires']
        missing_tables = []
        
        for table in required_tables:
            try:
                result = db.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                if result.empty:
                    missing_tables.append(f"{table} (vide)")
                else:
                    count = result.iloc[0]['count']
                    logger.info(f"📊 Table {table}: {count} enregistrements")
            except Exception as e:
                missing_tables.append(f"{table} (erreur: {e})")
        
        if missing_tables:
            logger.warning(f"⚠️ Tables manquantes/problématiques: {missing_tables}")
            return False, missing_tables
        
        # Test des gestionnaires
        managers_ok = test_managers_functionality()
        
        if managers_ok:
            logger.info("🎯 Système de production initialisé avec succès")
            return True, []
        else:
            return False, ["Erreur initialisation gestionnaires"]
            
    except Exception as e:
        logger.error(f"❌ Erreur initialisation système: {e}")
        return False, [str(e)]

def get_system_health_check() -> Dict:
    """Retourne un rapport de santé du système"""
    try:
        db = ERPDatabase()
        health = {
            'status': 'HEALTHY',
            'checks': {},
            'warnings': [],
            'errors': []
        }
        
        # Check 1: Base de données
        try:
            test_query = "SELECT COUNT(*) as count FROM projects"
            result = db.execute_query(test_query)
            health['checks']['database'] = 'OK'
        except Exception as e:
            health['checks']['database'] = f'ERROR: {e}'
            health['errors'].append(f"Base de données: {e}")
            health['status'] = 'UNHEALTHY'
        
        # Check 2: Tables critiques
        critical_tables = {
            'projects': 'Produits',
            'materials': 'BOM/Matériaux', 
            'operations': 'Gammes/Opérations',
            'work_centers': 'Postes de travail',
            'formulaires': 'Bons de travail'
        }
        
        for table, description in critical_tables.items():
            try:
                result = db.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                count = result.iloc[0]['count'] if not result.empty else 0
                
                if count == 0:
                    health['warnings'].append(f"Table {description} vide")
                    if health['status'] == 'HEALTHY':
                        health['status'] = 'WARNING'
                
                health['checks'][table] = f'OK ({count} enregistrements)'
                
            except Exception as e:
                health['checks'][table] = f'ERROR: {e}'
                health['errors'].append(f"Table {description}: {e}")
                health['status'] = 'UNHEALTHY'
        
        # Check 3: Gestionnaires
        try:
            managers_ok = test_managers_functionality()
            health['checks']['managers'] = 'OK' if managers_ok else 'ERROR'
            if not managers_ok:
                health['errors'].append("Erreur initialisation gestionnaires")
                health['status'] = 'UNHEALTHY'
        except Exception as e:
            health['checks']['managers'] = f'ERROR: {e}'
            health['errors'].append(f"Gestionnaires: {e}")
            health['status'] = 'UNHEALTHY'
        
        return health
        
    except Exception as e:
        return {
            'status': 'CRITICAL',
            'checks': {},
            'warnings': [],
            'errors': [f"Erreur critique health check: {e}"]
        }

# =============================================================================
# CLASSES GESTIONNAIRES MÉTIER
# =============================================================================

class ProductManager:
    """Gestionnaire des produits avec hiérarchie"""
    
    def __init__(self, db: ERPDatabase):
        self.db = db
        
    def get_all_products(self) -> pd.DataFrame:
        """Récupère tous les produits (utilise projects + logique étendue)"""
        try:
            query = """
            SELECT 
                id,
                nom_projet as product_name,
                description,
                statut as status,
                client_company_id,
                date_creation,
                date_fin_prevue,
                CASE 
                    WHEN EXISTS (SELECT 1 FROM materials WHERE project_id = projects.id) THEN 'PRODUIT_FINI'
                    ELSE 'COMPOSANT'
                END as product_type
            FROM projects 
            WHERE statut != 'SUPPRIME'
            ORDER BY nom_projet
            """
            result = self.db.execute_query(query)
            
            if not result.empty:
                # Enrichissement avec statistiques
                for idx, row in result.iterrows():
                    # Compter les composants BOM
                    bom_count = self.get_bom_component_count(row['id'])
                    result.at[idx, 'bom_components'] = bom_count
                    
                    # Compter les opérations
                    operations_count = self.get_operations_count(row['id'])
                    result.at[idx, 'operations_count'] = operations_count
                    
            return result
        except Exception as e:
            logger.error(f"Erreur récupération produits: {e}")
            return pd.DataFrame()
    
    def create_product(self, product_data: Dict) -> bool:
        """Crée un nouveau produit"""
        try:
            # Génération code produit automatique
            product_code = self.generate_product_code(product_data.get('type', 'PRODUIT_FINI'))
            
            query = """
            INSERT INTO projects (
                nom_projet, description, statut, date_creation, 
                date_debut, client_company_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (
                product_code if not product_data.get('name') else product_data.get('name'),
                product_data.get('description', ''),
                'ACTIF',
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                product_data.get('client_company_id', 1)  # Default client
            )
            
            result = self.db.execute_query(query, params)
            logger.info(f"Produit créé: {product_data.get('name', product_code)}")
            return True
        except Exception as e:
            logger.error(f"Erreur création produit: {e}")
            return False
    
    def update_product(self, product_id: int, product_data: Dict) -> bool:
        """Met à jour un produit existant"""
        try:
            query = """
            UPDATE projects 
            SET nom_projet = ?, description = ?, statut = ?
            WHERE id = ?
            """
            params = (
                product_data.get('name'),
                product_data.get('description'),
                product_data.get('status', 'ACTIF'),
                product_id
            )
            
            self.db.execute_query(query, params)
            logger.info(f"Produit {product_id} mis à jour")
            return True
        except Exception as e:
            logger.error(f"Erreur mise à jour produit: {e}")
            return False
    
    def delete_product(self, product_id: int) -> bool:
        """Supprime un produit (suppression logique)"""
        try:
            # Vérifier les dépendances
            dependencies = self.check_product_dependencies(product_id)
            if dependencies['has_dependencies']:
                logger.warning(f"Produit {product_id} a des dépendances: {dependencies}")
                return False
            
            query = "UPDATE projects SET statut = 'SUPPRIME' WHERE id = ?"
            self.db.execute_query(query, (product_id,))
            logger.info(f"Produit {product_id} supprimé (logique)")
            return True
        except Exception as e:
            logger.error(f"Erreur suppression produit: {e}")
            return False
    
    def generate_product_code(self, product_type: str) -> str:
        """Génère un code produit automatique"""
        try:
            prefix_map = {
                'PRODUIT_FINI': 'PF',
                'SOUS_ASSEMBLAGE': 'SA',
                'COMPOSANT': 'CP',
                'MATIERE_PREMIERE': 'MP'
            }
            
            prefix = prefix_map.get(product_type, 'PD')
            
            # Récupérer le dernier numéro pour ce type
            query = """
            SELECT COUNT(*) as count 
            FROM projects 
            WHERE nom_projet LIKE ?
            """
            result = self.db.execute_query(query, (f"{prefix}%",))
            
            if not result.empty:
                count = result.iloc[0]['count'] + 1
            else:
                count = 1
            
            return f"{prefix}-{count:04d}"
            
        except Exception as e:
            logger.error(f"Erreur génération code produit: {e}")
            return f"PD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def get_bom_component_count(self, product_id: int) -> int:
        """Compte les composants BOM d'un produit"""
        try:
            query = "SELECT COUNT(*) as count FROM materials WHERE project_id = ?"
            result = self.db.execute_query(query, (product_id,))
            return result.iloc[0]['count'] if not result.empty else 0
        except Exception as e:
            logger.error(f"Erreur comptage BOM: {e}")
            return 0
    
    def get_operations_count(self, product_id: int) -> int:
        """Compte les opérations d'un produit"""
        try:
            query = "SELECT COUNT(*) as count FROM operations WHERE project_id = ?"
            result = self.db.execute_query(query, (product_id,))
            return result.iloc[0]['count'] if not result.empty else 0
        except Exception as e:
            logger.error(f"Erreur comptage opérations: {e}")
            return 0
    
    def check_product_dependencies(self, product_id: int) -> Dict:
        """Vérifie les dépendances d'un produit avant suppression"""
        try:
            dependencies = {
                'has_dependencies': False,
                'bom_count': 0,
                'operations_count': 0,
                'work_orders_count': 0
            }
            
            # Vérifier BOM
            dependencies['bom_count'] = self.get_bom_component_count(product_id)
            
            # Vérifier opérations
            dependencies['operations_count'] = self.get_operations_count(product_id)
            
            # Vérifier bons de travail
            query = """
            SELECT COUNT(*) as count 
            FROM formulaires 
            WHERE project_id = ? AND type_formulaire = 'BON_TRAVAIL' AND statut != 'SUPPRIME'
            """
            result = self.db.execute_query(query, (product_id,))
            dependencies['work_orders_count'] = result.iloc[0]['count'] if not result.empty else 0
            
            dependencies['has_dependencies'] = (
                dependencies['bom_count'] > 0 or 
                dependencies['operations_count'] > 0 or 
                dependencies['work_orders_count'] > 0
            )
            
            return dependencies
        except Exception as e:
            logger.error(f"Erreur vérification dépendances: {e}")
            return {'has_dependencies': True}
    
    def get_product_hierarchy(self, product_id: int) -> Dict:
        """Récupère la hiérarchie d'un produit"""
        try:
            # Pour l'instant, hiérarchie basée sur les BOM
            hierarchy = {
                'product_id': product_id,
                'children': [],
                'level': 0
            }
            
            # Récupérer les composants directs
            query = """
            SELECT DISTINCT code_materiau, designation 
            FROM materials 
            WHERE project_id = ?
            """
            result = self.db.execute_query(query, (product_id,))
            
            for _, row in result.iterrows():
                child = {
                    'code': row['code_materiau'],
                    'name': row['designation'],
                    'level': 1
                }
                hierarchy['children'].append(child)
            
            return hierarchy
        except Exception as e:
            logger.error(f"Erreur hiérarchie produit: {e}")
            return {"product_id": product_id, "children": []}


class BOMManager:
    """Gestionnaire des nomenclatures multiniveaux"""
    
    def __init__(self, db: ERPDatabase):
        self.db = db
    
    def get_bom_for_product(self, product_id: int) -> pd.DataFrame:
        """Récupère la BOM d'un produit (utilise materials)"""
        try:
            query = """
            SELECT 
                m.id,
                m.code_materiau as component_code,
                m.designation as component_name,
                m.quantite as quantity,
                m.unite as unit,
                COALESCE(m.prix_unitaire, 0) as unit_price,
                m.fournisseur as supplier,
                COALESCE(m.quantite * m.prix_unitaire, 0) as total_cost,
                m.notes,
                m.date_creation,
                CASE 
                    WHEN m.code_materiau LIKE 'PF-%' THEN 'PRODUIT_FINI'
                    WHEN m.code_materiau LIKE 'SA-%' THEN 'SOUS_ASSEMBLAGE'
                    WHEN m.code_materiau LIKE 'CP-%' THEN 'COMPOSANT'
                    ELSE 'MATIERE_PREMIERE'
                END as component_type
            FROM materials m
            WHERE m.project_id = ?
            ORDER BY m.code_materiau
            """
            result = self.db.execute_query(query, (product_id,))
            
            if not result.empty:
                # Enrichissement avec données inventaire si disponible
                result = self.enrich_bom_with_inventory(result)
                
            return result
        except Exception as e:
            logger.error(f"Erreur récupération BOM: {e}")
            return pd.DataFrame()
    
    def enrich_bom_with_inventory(self, bom_df: pd.DataFrame) -> pd.DataFrame:
        """Enrichit la BOM avec les données d'inventaire"""
        try:
            for idx, row in bom_df.iterrows():
                # Rechercher dans l'inventaire
                query = """
                SELECT quantite_metric, statut 
                FROM inventory_items 
                WHERE nom LIKE ? OR nom LIKE ?
                LIMIT 1
                """
                inv_result = self.db.execute_query(
                    query, 
                    (f"%{row['component_code']}%", f"%{row['component_name']}%")
                )
                
                if not inv_result.empty:
                    bom_df.at[idx, 'stock_available'] = inv_result.iloc[0]['quantite_metric']
                    bom_df.at[idx, 'stock_status'] = inv_result.iloc[0]['statut']
                else:
                    bom_df.at[idx, 'stock_available'] = 0
                    bom_df.at[idx, 'stock_status'] = 'NON_STOCKE'
                    
            return bom_df
        except Exception as e:
            logger.error(f"Erreur enrichissement inventaire: {e}")
            return bom_df
    
    def add_component_to_bom(self, product_id: int, component_data: Dict) -> bool:
        """Ajoute un composant à une BOM"""
        try:
            query = """
            INSERT INTO materials (
                project_id, code_materiau, designation, quantite, 
                unite, prix_unitaire, fournisseur, notes, date_creation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                product_id,
                component_data.get('code'),
                component_data.get('designation'),
                component_data.get('quantity', 1),
                component_data.get('unit', 'PC'),
                component_data.get('unit_price', 0),
                component_data.get('supplier', ''),
                component_data.get('notes', ''),
                datetime.now().isoformat()
            )
            
            self.db.execute_query(query, params)
            logger.info(f"Composant ajouté à BOM produit {product_id}")
            return True
        except Exception as e:
            logger.error(f"Erreur ajout composant BOM: {e}")
            return False
    
    def update_component_in_bom(self, component_id: int, component_data: Dict) -> bool:
        """Met à jour un composant de BOM"""
        try:
            query = """
            UPDATE materials 
            SET designation = ?, quantite = ?, unite = ?, 
                prix_unitaire = ?, fournisseur = ?, notes = ?
            WHERE id = ?
            """
            params = (
                component_data.get('designation'),
                component_data.get('quantity'),
                component_data.get('unit'),
                component_data.get('unit_price'),
                component_data.get('supplier'),
                component_data.get('notes'),
                component_id
            )
            
            self.db.execute_query(query, params)
            logger.info(f"Composant BOM {component_id} mis à jour")
            return True
        except Exception as e:
            logger.error(f"Erreur mise à jour composant BOM: {e}")
            return False
    
    def remove_component_from_bom(self, component_id: int) -> bool:
        """Supprime un composant d'une BOM"""
        try:
            query = "DELETE FROM materials WHERE id = ?"
            self.db.execute_query(query, (component_id,))
            logger.info(f"Composant BOM {component_id} supprimé")
            return True
        except Exception as e:
            logger.error(f"Erreur suppression composant BOM: {e}")
            return False
    
    def explode_bom(self, product_id: int, level: int = 0, parent_quantity: float = 1.0) -> List[Dict]:
        """Explosion BOM multiniveaux récursive"""
        if level > 10:  # Limite récursion
            logger.warning(f"Limite de récursion atteinte pour produit {product_id}")
            return []
        
        try:
            bom_df = self.get_bom_for_product(product_id)
            explosion = []
            
            for _, row in bom_df.iterrows():
                # Quantité calculée avec le niveau parent
                calculated_quantity = row['quantity'] * parent_quantity
                
                item = {
                    'level': level,
                    'product_id': product_id,
                    'component_id': row['id'],
                    'component_code': row['component_code'],
                    'component_name': row['component_name'],
                    'quantity_per_unit': row['quantity'],
                    'quantity_total': calculated_quantity,
                    'unit': row['unit'],
                    'unit_price': row['unit_price'],
                    'total_cost': calculated_quantity * row['unit_price'],
                    'supplier': row['supplier'],
                    'component_type': row['component_type'],
                    'stock_available': row.get('stock_available', 0),
                    'stock_status': row.get('stock_status', 'UNKNOWN')
                }
                explosion.append(item)
                
                # Récursion pour sous-assemblages
                if row['component_type'] in ['PRODUIT_FINI', 'SOUS_ASSEMBLAGE']:
                    # Chercher si ce composant a lui-même une BOM
                    sub_product = self.find_product_by_code(row['component_code'])
                    if sub_product:
                        sub_explosion = self.explode_bom(
                            sub_product['id'], 
                            level + 1, 
                            calculated_quantity
                        )
                        explosion.extend(sub_explosion)
                
            return explosion
        except Exception as e:
            logger.error(f"Erreur explosion BOM: {e}")
            return []
    
    def find_product_by_code(self, product_code: str) -> Optional[Dict]:
        """Trouve un produit par son code"""
        try:
            query = """
            SELECT id, nom_projet as name 
            FROM projects 
            WHERE nom_projet = ? AND statut = 'ACTIF'
            LIMIT 1
            """
            result = self.db.execute_query(query, (product_code,))
            
            if not result.empty:
                return {
                    'id': result.iloc[0]['id'],
                    'name': result.iloc[0]['name']
                }
            return None
        except Exception as e:
            logger.error(f"Erreur recherche produit par code: {e}")
            return None
    
    def calculate_bom_cost(self, product_id: int, quantity: float = 1.0) -> Dict:
        """Calcule le coût total d'une BOM avec détails"""
        try:
            explosion = self.explode_bom(product_id, parent_quantity=quantity)
            
            costs = {
                'materials_cost': 0.0,
                'components_cost': 0.0,
                'sub_assemblies_cost': 0.0,
                'total_cost': 0.0,
                'cost_breakdown': []
            }
            
            for item in explosion:
                item_cost = item['total_cost']
                
                if item['component_type'] == 'MATIERE_PREMIERE':
                    costs['materials_cost'] += item_cost
                elif item['component_type'] == 'COMPOSANT':
                    costs['components_cost'] += item_cost
                elif item['component_type'] in ['SOUS_ASSEMBLAGE', 'PRODUIT_FINI']:
                    costs['sub_assemblies_cost'] += item_cost
                
                costs['cost_breakdown'].append({
                    'level': item['level'],
                    'component': item['component_name'],
                    'quantity': item['quantity_total'],
                    'unit_price': item['unit_price'],
                    'total_cost': item_cost
                })
            
            costs['total_cost'] = costs['materials_cost'] + costs['components_cost'] + costs['sub_assemblies_cost']
            
            return costs
        except Exception as e:
            logger.error(f"Erreur calcul coût BOM: {e}")
            return {'total_cost': 0.0, 'error': str(e)}
    
    def generate_bom_report(self, product_id: int) -> Dict:
        """Génère un rapport complet de BOM"""
        try:
            # Informations produit
            product_query = "SELECT nom_projet, description FROM projects WHERE id = ?"
            product_result = self.db.execute_query(product_query, (product_id,))
            
            if product_result.empty:
                return {'error': 'Produit non trouvé'}
            
            product_info = product_result.iloc[0]
            
            # Explosion BOM
            explosion = self.explode_bom(product_id)
            
            # Calculs coûts
            costs = self.calculate_bom_cost(product_id)
            
            # Statistiques
            stats = {
                'total_components': len(explosion),
                'max_level': max([item['level'] for item in explosion]) if explosion else 0,
                'unique_suppliers': len(set([item['supplier'] for item in explosion if item['supplier']])),
                'components_by_type': {}
            }
            
            # Comptage par type
            for item in explosion:
                comp_type = item['component_type']
                stats['components_by_type'][comp_type] = stats['components_by_type'].get(comp_type, 0) + 1
            
            return {
                'product_name': product_info['nom_projet'],
                'product_description': product_info['description'],
                'explosion': explosion,
                'costs': costs,
                'statistics': stats,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur génération rapport BOM: {e}")
            return {'error': str(e)}


class RoutingManager:
    """Gestionnaire des gammes de fabrication"""
    
    def __init__(self, db: ERPDatabase):
        self.db = db
    
    def get_routing_for_product(self, product_id: int) -> pd.DataFrame:
        """Récupère la gamme d'un produit (utilise operations)"""
        try:
            query = """
            SELECT 
                o.id,
                o.sequence_number as operation_seq,
                o.description as operation_name,
                COALESCE(w.nom, o.poste_travail) as work_center_name,
                o.temps_estime as duration_minutes,
                o.statut as status,
                o.poste_travail,
                COALESCE(w.cout_horaire, 50.0) as hourly_rate,
                w.departement,
                w.categorie,
                w.capacite_theorique,
                o.formulaire_bt_id,
                o.notes,
                CASE 
                    WHEN o.temps_estime > 0 AND w.cout_horaire > 0 
                    THEN (o.temps_estime / 60.0) * w.cout_horaire 
                    ELSE 0 
                END as operation_cost
            FROM operations o
            LEFT JOIN work_centers w ON o.work_center_id = w.id
            WHERE o.project_id = ?
            ORDER BY o.sequence_number
            """
            result = self.db.execute_query(query, (product_id,))
            
            if not result.empty:
                # Enrichissement avec informations de charge
                result = self.enrich_routing_with_workload(result)
                
            return result
        except Exception as e:
            logger.error(f"Erreur récupération gamme: {e}")
            return pd.DataFrame()
    
    def enrich_routing_with_workload(self, routing_df: pd.DataFrame) -> pd.DataFrame:
        """Enrichit la gamme avec les informations de charge des postes"""
        try:
            for idx, row in routing_df.iterrows():
                if pd.notna(row.get('work_center_name')):
                    # Calculer la charge actuelle du poste
                    workload = self.get_work_center_current_load(row.get('work_center_name'))
                    routing_df.at[idx, 'current_load_percent'] = workload
                    
                    # Statut de disponibilité
                    if workload < 80:
                        routing_df.at[idx, 'availability_status'] = 'DISPONIBLE'
                    elif workload < 95:
                        routing_df.at[idx, 'availability_status'] = 'CHARGE'
                    else:
                        routing_df.at[idx, 'availability_status'] = 'SATURE'
                else:
                    routing_df.at[idx, 'current_load_percent'] = 0
                    routing_df.at[idx, 'availability_status'] = 'INCONNU'
                    
            return routing_df
        except Exception as e:
            logger.error(f"Erreur enrichissement charge: {e}")
            return routing_df
    
    def get_work_center_current_load(self, work_center_name: str) -> float:
        """Calcule la charge actuelle d'un poste de travail (simulé)"""
        try:
            # Simulation basée sur le nombre d'opérations en cours
            query = """
            SELECT COUNT(*) as active_operations
            FROM operations o
            LEFT JOIN work_centers w ON o.work_center_id = w.id
            WHERE (w.nom = ? OR o.poste_travail = ?) 
            AND o.statut IN ('EN_COURS', 'PLANIFIE')
            """
            result = self.db.execute_query(query, (work_center_name, work_center_name))
            
            if not result.empty:
                active_ops = result.iloc[0]['active_operations']
                # Simulation: chaque opération active = 20% de charge
                return min(active_ops * 20, 100)
            
            return 0
        except Exception as e:
            logger.error(f"Erreur calcul charge poste: {e}")
            return 0
    
    def create_operation(self, operation_data: Dict) -> bool:
        """Crée une nouvelle opération"""
        try:
            # Vérifier si le numéro de séquence existe déjà
            if self.sequence_exists(operation_data.get('product_id'), operation_data.get('sequence_number')):
                logger.warning(f"Séquence {operation_data.get('sequence_number')} existe déjà")
                return False
            
            query = """
            INSERT INTO operations 
            (project_id, work_center_id, sequence_number, description, 
             temps_estime, statut, poste_travail, notes, date_creation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                operation_data.get('product_id'),
                operation_data.get('work_center_id'),
                operation_data.get('sequence_number'),
                operation_data.get('description'),
                operation_data.get('duration', 60),
                'ACTIF',
                operation_data.get('work_center_name', ''),
                operation_data.get('notes', ''),
                datetime.now().isoformat()
            )
            
            self.db.execute_query(query, params)
            logger.info(f"Opération {operation_data.get('sequence_number')} créée")
            return True
        except Exception as e:
            logger.error(f"Erreur création opération: {e}")
            return False
    
    def update_operation(self, operation_id: int, operation_data: Dict) -> bool:
        """Met à jour une opération existante"""
        try:
            query = """
            UPDATE operations 
            SET description = ?, temps_estime = ?, work_center_id = ?, 
                poste_travail = ?, notes = ?, statut = ?
            WHERE id = ?
            """
            params = (
                operation_data.get('description'),
                operation_data.get('duration'),
                operation_data.get('work_center_id'),
                operation_data.get('work_center_name'),
                operation_data.get('notes'),
                operation_data.get('status', 'ACTIF'),
                operation_id
            )
            
            self.db.execute_query(query, params)
            logger.info(f"Opération {operation_id} mise à jour")
            return True
        except Exception as e:
            logger.error(f"Erreur mise à jour opération: {e}")
            return False
    
    def delete_operation(self, operation_id: int) -> bool:
        """Supprime une opération"""
        try:
            # Vérifier si l'opération est utilisée dans des BT
            query = """
            SELECT COUNT(*) as count 
            FROM formulaires 
            WHERE metadonnees_json LIKE '%"operation_id": ' || ? || '%'
            AND type_formulaire = 'BON_TRAVAIL'
            """
            result = self.db.execute_query(query, (operation_id,))
            
            if not result.empty and result.iloc[0]['count'] > 0:
                logger.warning(f"Opération {operation_id} utilisée dans des BT")
                return False
            
            # Suppression
            query = "DELETE FROM operations WHERE id = ?"
            self.db.execute_query(query, (operation_id,))
            logger.info(f"Opération {operation_id} supprimée")
            return True
        except Exception as e:
            logger.error(f"Erreur suppression opération: {e}")
            return False
    
    def sequence_exists(self, product_id: int, sequence_number: int) -> bool:
        """Vérifie si un numéro de séquence existe déjà pour un produit"""
        try:
            query = """
            SELECT COUNT(*) as count 
            FROM operations 
            WHERE project_id = ? AND sequence_number = ?
            """
            result = self.db.execute_query(query, (product_id, sequence_number))
            return not result.empty and result.iloc[0]['count'] > 0
        except Exception as e:
            logger.error(f"Erreur vérification séquence: {e}")
            return True  # En cas d'erreur, on assume que ça existe
    
    def get_next_sequence_number(self, product_id: int) -> int:
        """Récupère le prochain numéro de séquence disponible"""
        try:
            query = """
            SELECT COALESCE(MAX(sequence_number), 1000) + 1 as next_seq
            FROM operations 
            WHERE project_id = ?
            """
            result = self.db.execute_query(query, (product_id,))
            
            if not result.empty:
                return result.iloc[0]['next_seq']
            return 1001
        except Exception as e:
            logger.error(f"Erreur calcul prochaine séquence: {e}")
            return 1001
    
    def get_available_work_centers(self) -> pd.DataFrame:
        """Récupère les 61 postes de travail disponibles"""
        try:
            query = """
            SELECT 
                id,
                nom as name,
                departement,
                categorie,
                capacite_theorique as capacity,
                cout_horaire as hourly_rate,
                statut as status,
                CASE 
                    WHEN statut = 'ACTIF' THEN 'DISPONIBLE'
                    WHEN statut = 'MAINTENANCE' THEN 'MAINTENANCE'
                    ELSE 'INDISPONIBLE'
                END as availability
            FROM work_centers
            WHERE statut IN ('ACTIF', 'MAINTENANCE')
            ORDER BY departement, nom
            """
            result = self.db.execute_query(query)
            
            if not result.empty:
                # Ajouter la charge actuelle pour chaque poste
                for idx, row in result.iterrows():
                    current_load = self.get_work_center_current_load(row['name'])
                    result.at[idx, 'current_load'] = current_load
                    
            return result
        except Exception as e:
            logger.error(f"Erreur récupération postes de travail: {e}")
            return pd.DataFrame()
    
    def copy_routing_from_product(self, source_product_id: int, target_product_id: int) -> bool:
        """Copie la gamme d'un produit vers un autre"""
        try:
            # Récupérer la gamme source
            source_routing = self.get_routing_for_product(source_product_id)
            
            if source_routing.empty:
                logger.warning(f"Aucune gamme à copier pour le produit {source_product_id}")
                return False
            
            # Copier chaque opération
            success_count = 0
            for _, operation in source_routing.iterrows():
                operation_data = {
                    'product_id': target_product_id,
                    'work_center_id': operation.get('work_center_id'),
                    'sequence_number': operation['operation_seq'],
                    'description': operation['operation_name'],
                    'duration': operation['duration_minutes'],
                    'work_center_name': operation['work_center_name'],
                    'notes': f"Copié du produit {source_product_id}"
                }
                
                if self.create_operation(operation_data):
                    success_count += 1
            
            logger.info(f"{success_count} opérations copiées vers produit {target_product_id}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Erreur copie gamme: {e}")
            return False
    
    def calculate_routing_cost(self, product_id: int, quantity: float = 1.0) -> Dict:
        """Calcule le coût total d'une gamme de fabrication"""
        try:
            routing_df = self.get_routing_for_product(product_id)
            
            if routing_df.empty:
                return {'total_cost': 0.0, 'total_time': 0.0}
            
            # Calculs
            total_time = routing_df['duration_minutes'].sum() * quantity
            total_cost = routing_df['operation_cost'].sum() * quantity
            
            # Détails par opération
            operations_detail = []
            for _, op in routing_df.iterrows():
                op_total_time = op['duration_minutes'] * quantity
                op_total_cost = op['operation_cost'] * quantity
                
                operations_detail.append({
                    'sequence': op['operation_seq'],
                    'operation': op['operation_name'],
                    'work_center': op['work_center_name'],
                    'unit_time': op['duration_minutes'],
                    'total_time': op_total_time,
                    'hourly_rate': op['hourly_rate'],
                    'total_cost': op_total_cost
                })
            
            return {
                'total_time_minutes': total_time,
                'total_time_hours': total_time / 60,
                'total_cost': total_cost,
                'average_hourly_rate': routing_df['hourly_rate'].mean(),
                'operations_count': len(routing_df),
                'operations_detail': operations_detail
            }
            
        except Exception as e:
            logger.error(f"Erreur calcul coût gamme: {e}")
            return {'total_cost': 0.0, 'error': str(e)}


class WorkOrderManager:
    """Gestionnaire des bons de travail avec explosion"""
    
    def __init__(self, db: ERPDatabase, bom_manager: BOMManager, routing_manager: RoutingManager):
        self.db = db
        self.bom_manager = bom_manager
        self.routing_manager = routing_manager
    
    def create_work_order(self, product_id: int, quantity: float, work_order_data: Dict = None) -> Optional[int]:
        """Crée un BT avec explosion BOM + génération gamme"""
        try:
            # Explosion BOM
            bom_explosion = self.bom_manager.explode_bom(product_id, parent_quantity=quantity)
            
            # Récupération gamme
            routing_df = self.routing_manager.get_routing_for_product(product_id)
            
            # Calculs des coûts
            bom_costs = self.bom_manager.calculate_bom_cost(product_id, quantity)
            routing_costs = self.routing_manager.calculate_routing_cost(product_id, quantity)
            
            # Génération numéro BT unique
            bt_number = self.generate_work_order_number(product_id)
            
            # Métadonnées complètes du BT
            metadonnees = {
                'product_id': product_id,
                'quantity_to_produce': quantity,
                'bom_explosion': bom_explosion,
                'routing_operations': routing_df.to_dict('records') if not routing_df.empty else [],
                'cost_breakdown': {
                    'materials_cost': bom_costs.get('total_cost', 0),
                    'labor_cost': routing_costs.get('total_cost', 0),
                    'total_cost': bom_costs.get('total_cost', 0) + routing_costs.get('total_cost', 0)
                },
                'time_estimates': {
                    'total_production_time': routing_costs.get('total_time_minutes', 0),
                    'estimated_hours': routing_costs.get('total_time_hours', 0)
                },
                'created_by': work_order_data.get('created_by', 'System') if work_order_data else 'System',
                'priority': work_order_data.get('priority', 'NORMALE') if work_order_data else 'NORMALE',
                'due_date': work_order_data.get('due_date') if work_order_data else None,
                'work_centers_required': [op['work_center_name'] for op in routing_df.to_dict('records')] if not routing_df.empty else []
            }
            
            # Création BT dans formulaires
            query = """
            INSERT INTO formulaires 
            (type_formulaire, numero_document, project_id, statut, date_creation, metadonnees_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            
            params = (
                'BON_TRAVAIL',
                bt_number,
                product_id,
                'BROUILLON',
                datetime.now().isoformat(),
                json.dumps(metadonnees, ensure_ascii=False, indent=2)
            )
            
            # Exécution et récupération de l'ID
            result = self.db.execute_query(query, params)
            
            # Récupérer l'ID du BT créé
            id_query = "SELECT id FROM formulaires WHERE numero_document = ? ORDER BY date_creation DESC LIMIT 1"
            id_result = self.db.execute_query(id_query, (bt_number,))
            
            if not id_result.empty:
                work_order_id = id_result.iloc[0]['id']
                logger.info(f"Bon de travail créé: {bt_number} (ID: {work_order_id})")
                
                # Réserver automatiquement les postes de travail
                if not routing_df.empty:
                    self.reserve_work_centers(work_order_id, routing_df)
                
                return work_order_id
            else:
                logger.error("Impossible de récupérer l'ID du BT créé")
                return None
            
        except Exception as e:
            logger.error(f"Erreur création BT: {e}")
            return None
    
    def generate_work_order_number(self, product_id: int) -> str:
        """Génère un numéro de BT unique"""
        try:
            # Format: BT-YYYYMMDD-PRODUCTID-XXX
            date_str = datetime.now().strftime('%Y%m%d')
            
            # Compter les BT du jour pour ce produit
            query = """
            SELECT COUNT(*) as count 
            FROM formulaires 
            WHERE type_formulaire = 'BON_TRAVAIL' 
            AND project_id = ? 
            AND DATE(date_creation) = DATE('now')
            """
            result = self.db.execute_query(query, (product_id,))
            
            if not result.empty:
                daily_count = result.iloc[0]['count'] + 1
            else:
                daily_count = 1
            
            return f"BT-{date_str}-{product_id:04d}-{daily_count:03d}"
            
        except Exception as e:
            logger.error(f"Erreur génération numéro BT: {e}")
            return f"BT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def get_work_order_by_id(self, work_order_id: int) -> Optional[Dict]:
        """Récupère un BT par son ID avec tous les détails"""
        try:
            query = """
            SELECT 
                f.id,
                f.numero_document as work_order_number,
                f.project_id,
                p.nom_projet as product_name,
                p.description as product_description,
                f.statut as status,
                f.date_creation,
                f.metadonnees_json,
                f.date_modification
            FROM formulaires f
            LEFT JOIN projects p ON f.project_id = p.id
            WHERE f.id = ? AND f.type_formulaire = 'BON_TRAVAIL'
            """
            result = self.db.execute_query(query, (work_order_id,))
            
            if not result.empty:
                work_order = result.iloc[0].to_dict()
                
                # Parser les métadonnées JSON
                if work_order['metadonnees_json']:
                    try:
                        work_order['metadata'] = json.loads(work_order['metadonnees_json'])
                    except json.JSONDecodeError:
                        work_order['metadata'] = {}
                else:
                    work_order['metadata'] = {}
                
                return work_order
            
            return None
        except Exception as e:
            logger.error(f"Erreur récupération BT {work_order_id}: {e}")
            return None
    
    def get_all_work_orders(self, filters: Dict = None) -> pd.DataFrame:
        """Récupère tous les BT avec filtres optionnels"""
        try:
            base_query = """
            SELECT 
                f.id,
                f.numero_document as work_order_number,
                p.nom_projet as product_name,
                f.statut as status,
                f.date_creation,
                f.metadonnees_json
            FROM formulaires f
            LEFT JOIN projects p ON f.project_id = p.id
            WHERE f.type_formulaire = 'BON_TRAVAIL'
            """
            
            params = []
            
            # Application des filtres
            if filters:
                if filters.get('status'):
                    base_query += " AND f.statut = ?"
                    params.append(filters['status'])
                
                if filters.get('product_id'):
                    base_query += " AND f.project_id = ?"
                    params.append(filters['product_id'])
                
                if filters.get('date_from'):
                    base_query += " AND DATE(f.date_creation) >= ?"
                    params.append(filters['date_from'])
                
                if filters.get('date_to'):
                    base_query += " AND DATE(f.date_creation) <= ?"
                    params.append(filters['date_to'])
            
            base_query += " ORDER BY f.date_creation DESC"
            
            result = self.db.execute_query(base_query, params)
            
            if not result.empty:
                # Enrichir avec informations des métadonnées
                for idx, row in result.iterrows():
                    try:
                        if row['metadonnees_json']:
                            metadata = json.loads(row['metadonnees_json'])
                            result.at[idx, 'quantity'] = metadata.get('quantity_to_produce', 0)
                            result.at[idx, 'total_cost'] = metadata.get('cost_breakdown', {}).get('total_cost', 0)
                            result.at[idx, 'priority'] = metadata.get('priority', 'NORMALE')
                        else:
                            result.at[idx, 'quantity'] = 0
                            result.at[idx, 'total_cost'] = 0
                            result.at[idx, 'priority'] = 'NORMALE'
                    except json.JSONDecodeError:
                        result.at[idx, 'quantity'] = 0
                        result.at[idx, 'total_cost'] = 0
                        result.at[idx, 'priority'] = 'NORMALE'
            
            return result
        except Exception as e:
            logger.error(f"Erreur récupération BT: {e}")
            return pd.DataFrame()
    
    def update_work_order_status(self, work_order_id: int, new_status: str, notes: str = None) -> bool:
        """Met à jour le statut d'un BT"""
        try:
            # Statuts valides
            valid_statuses = ['BROUILLON', 'VALIDE', 'EN_COURS', 'SUSPEND', 'TERMINE', 'ANNULE']
            
            if new_status not in valid_statuses:
                logger.error(f"Statut invalide: {new_status}")
                return False
            
            # Récupérer les métadonnées actuelles
            work_order = self.get_work_order_by_id(work_order_id)
            if not work_order:
                logger.error(f"BT {work_order_id} non trouvé")
                return False
            
            # Mettre à jour les métadonnées
            metadata = work_order.get('metadata', {})
            
            if 'status_history' not in metadata:
                metadata['status_history'] = []
            
            metadata['status_history'].append({
                'old_status': work_order['status'],
                'new_status': new_status,
                'changed_at': datetime.now().isoformat(),
                'notes': notes
            })
            
            # Mise à jour en base
            query = """
            UPDATE formulaires 
            SET statut = ?, metadonnees_json = ?, date_modification = ?
            WHERE id = ?
            """
            params = (
                new_status,
                json.dumps(metadata, ensure_ascii=False, indent=2),
                datetime.now().isoformat(),
                work_order_id
            )
            
            self.db.execute_query(query, params)
            logger.info(f"BT {work_order_id} statut mis à jour: {new_status}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur mise à jour statut BT: {e}")
            return False
    
    def reserve_work_centers(self, work_order_id: int, routing_df: pd.DataFrame) -> bool:
        """Réserve les postes de travail pour un BT"""
        try:
            reservations_made = 0
            
            for _, operation in routing_df.iterrows():
                if pd.notna(operation.get('work_center_name')):
                    # Créer une réservation dans bt_reservations_postes si la table existe
                    try:
                        reservation_query = """
                        INSERT INTO bt_reservations_postes 
                        (formulaire_bt_id, work_center_id, operation_id, date_debut_prevue, duree_prevue, statut)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """
                        
                        # Date de début estimée (peut être améliorée avec un vrai planificateur)
                        start_date = datetime.now() + timedelta(days=1)
                        
                        params = (
                            work_order_id,
                            operation.get('work_center_id'),
                            operation.get('id'),
                            start_date.isoformat(),
                            operation.get('duration_minutes', 60),
                            'RESERVE'
                        )
                        
                        self.db.execute_query(reservation_query, params)
                        reservations_made += 1
                        
                    except Exception as e:
                        # Si la table n'existe pas, on continue sans réservation
                        logger.warning(f"Réservation poste impossible: {e}")
                        continue
            
            logger.info(f"{reservations_made} réservations créées pour BT {work_order_id}")
            return reservations_made > 0
            
        except Exception as e:
            logger.error(f"Erreur réservation postes: {e}")
            return False
    
    def get_work_order_materials_requirements(self, work_order_id: int) -> List[Dict]:
        """Récupère les besoins matières d'un BT"""
        try:
            work_order = self.get_work_order_by_id(work_order_id)
            if not work_order:
                return []
            
            metadata = work_order.get('metadata', {})
            bom_explosion = metadata.get('bom_explosion', [])
            
            # Enrichir avec informations stock
            requirements = []
            for item in bom_explosion:
                # Vérifier le stock disponible
                stock_query = """
                SELECT quantite_metric, statut 
                FROM inventory_items 
                WHERE nom LIKE ? OR nom LIKE ?
                LIMIT 1
                """
                stock_result = self.db.execute_query(
                    stock_query, 
                    (f"%{item.get('component_code', '')}%", f"%{item.get('component_name', '')}%")
                )
                
                stock_available = 0
                stock_status = 'NON_STOCKE'
                
                if not stock_result.empty:
                    stock_available = stock_result.iloc[0]['quantite_metric']
                    stock_status = stock_result.iloc[0]['statut']
                
                # Calculer le besoin vs disponible
                required_qty = item.get('quantity_total', 0)
                shortage = max(0, required_qty - stock_available)
                
                requirement = {
                    'component_code': item.get('component_code'),
                    'component_name': item.get('component_name'),
                    'required_quantity': required_qty,
                    'available_stock': stock_available,
                    'shortage': shortage,
                    'unit': item.get('unit'),
                    'unit_cost': item.get('unit_price', 0),
                    'total_cost': item.get('total_cost', 0),
                    'stock_status': stock_status,
                    'procurement_needed': shortage > 0
                }
                
                requirements.append(requirement)
            
            return requirements
            
        except Exception as e:
            logger.error(f"Erreur besoins matières BT: {e}")
            return []
    
    def calculate_work_order_kpis(self, work_order_id: int) -> Dict:
        """Calcule les KPI d'un bon de travail"""
        try:
            work_order = self.get_work_order_by_id(work_order_id)
            if not work_order:
                return {}
            
            metadata = work_order.get('metadata', {})
            
            # KPIs de base
            kpis = {
                'total_cost': metadata.get('cost_breakdown', {}).get('total_cost', 0),
                'materials_cost': metadata.get('cost_breakdown', {}).get('materials_cost', 0),
                'labor_cost': metadata.get('cost_breakdown', {}).get('labor_cost', 0),
                'estimated_hours': metadata.get('time_estimates', {}).get('estimated_hours', 0),
                'quantity_to_produce': metadata.get('quantity_to_produce', 0)
            }
            
            # Calculs dérivés
            if kpis['quantity_to_produce'] > 0:
                kpis['cost_per_unit'] = kpis['total_cost'] / kpis['quantity_to_produce']
                kpis['time_per_unit'] = kpis['estimated_hours'] / kpis['quantity_to_produce']
            else:
                kpis['cost_per_unit'] = 0
                kpis['time_per_unit'] = 0
            
            # Analyse des matières
            materials_requirements = self.get_work_order_materials_requirements(work_order_id)
            kpis['materials_count'] = len(materials_requirements)
            kpis['materials_with_shortage'] = sum(1 for req in materials_requirements if req['procurement_needed'])
            kpis['procurement_ready'] = kpis['materials_with_shortage'] == 0
            
            # Analyse des postes
            routing_operations = metadata.get('routing_operations', [])
            kpis['operations_count'] = len(routing_operations)
            kpis['work_centers_required'] = len(set(op.get('work_center_name', '') for op in routing_operations))
            
            return kpis
            
        except Exception as e:
            logger.error(f"Erreur calcul KPIs BT: {e}")
            return {}


# =============================================================================
# INTERFACES UTILISATEUR - 4 ONGLETS PRINCIPAUX
# =============================================================================

def show_products_tab():
    """Onglet 1: Gestion des Produits - Interface complète"""
    st.markdown("### 📦 Gestion des Produits")
    
    # Initialisation gestionnaire
    db = ERPDatabase()
    product_manager = ProductManager(db)
    
    # Métriques rapides en en-tête
    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        
        try:
            products_df = product_manager.get_all_products()
            
            with col1:
                total_products = len(products_df)
                st.metric("Total Produits", total_products)
            
            with col2:
                active_products = len(products_df[products_df['status'] == 'ACTIF']) if not products_df.empty else 0
                st.metric("Produits Actifs", active_products)
            
            with col3:
                with_bom = len(products_df[products_df['bom_components'] > 0]) if not products_df.empty else 0
                st.metric("Avec BOM", with_bom)
            
            with col4:
                with_routing = len(products_df[products_df['operations_count'] > 0]) if not products_df.empty else 0
                st.metric("Avec Gamme", with_routing)
                
        except Exception as e:
            st.error(f"Erreur calcul métriques: {e}")
    
    st.markdown("---")
    
    # Sous-onglets pour organisation
    sub_tabs = st.tabs([
        "📋 Liste & Recherche", 
        "➕ Nouveau Produit", 
        "🔧 Modification", 
        "📊 Analyses"
    ])
    
    with sub_tabs[0]:
        show_products_list_tab(product_manager)
    
    with sub_tabs[1]:
        show_new_product_tab(product_manager)
    
    with sub_tabs[2]:
        show_edit_product_tab(product_manager)
    
    with sub_tabs[3]:
        show_products_analytics_tab(product_manager)


def show_products_list_tab(product_manager: ProductManager):
    """Sous-onglet: Liste et recherche de produits"""
    st.markdown("#### 📋 Liste des Produits")
    
    # Récupération des produits
    products_df = product_manager.get_all_products()
    
    if not products_df.empty:
        # Barre de recherche et filtres avancés
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_term = st.text_input(
                "🔍 Rechercher un produit:",
                placeholder="Nom, description, ou code produit...",
                help="Recherche dans le nom et la description"
            )
        
        with col2:
            status_filter = st.selectbox(
                "Filtrer par statut:",
                options=["Tous"] + sorted(products_df['status'].unique().tolist()),
                help="Filtrer par statut du produit"
            )
        
        with col3:
            type_filter = st.selectbox(
                "Filtrer par type:",
                options=["Tous"] + list(PRODUCT_TYPES.keys()),
                format_func=lambda x: PRODUCT_TYPES.get(x, x) if x != "Tous" else x,
                help="Filtrer par type de produit"
            )
        
        # Options d'affichage
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            show_bom_info = st.checkbox("📋 Afficher info BOM", value=True)
        with col2:
            show_routing_info = st.checkbox("⚙️ Afficher info Gamme", value=True)
        with col3:
            show_dates = st.checkbox("📅 Afficher dates", value=False)
        with col4:
            items_per_page = st.selectbox("Items par page:", [10, 25, 50, 100], index=1)
        
        # Application des filtres
        filtered_df = products_df.copy()
        
        # Filtre de recherche
        if search_term:
            search_mask = (
                filtered_df['product_name'].str.contains(search_term, case=False, na=False) |
                filtered_df['description'].str.contains(search_term, case=False, na=False)
            )
            filtered_df = filtered_df[search_mask]
        
        # Filtre statut
        if status_filter != "Tous":
            filtered_df = filtered_df[filtered_df['status'] == status_filter]
        
        # Filtre type
        if type_filter != "Tous":
            filtered_df = filtered_df[filtered_df['product_type'] == type_filter]
        
        # Pagination
        total_items = len(filtered_df)
        total_pages = (total_items - 1) // items_per_page + 1 if total_items > 0 else 1
        
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                current_page = st.number_input(
                    f"Page (1-{total_pages}):",
                    min_value=1,
                    max_value=total_pages,
                    value=1,
                    help=f"Total: {total_items} produits"
                )
        else:
            current_page = 1
        
        # Calcul des indices de pagination
        start_idx = (current_page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        page_df = filtered_df.iloc[start_idx:end_idx]
        
        if not page_df.empty:
            # Configuration colonnes pour affichage
            column_config = {
                "id": st.column_config.NumberColumn("ID", width="small"),
                "product_name": st.column_config.TextColumn("Nom du Produit", width="large"),
                "description": st.column_config.TextColumn("Description", width="medium"),
                "status": st.column_config.TextColumn("Statut", width="small"),
                "product_type": st.column_config.SelectboxColumn(
                    "Type",
                    options=list(PRODUCT_TYPES.keys()),
                    width="medium"
                )
            }
            
            # Colonnes conditionnelles
            if show_bom_info:
                column_config["bom_components"] = st.column_config.NumberColumn(
                    "Composants BOM", width="small", format="%d"
                )
            
            if show_routing_info:
                column_config["operations_count"] = st.column_config.NumberColumn(
                    "Opérations", width="small", format="%d"
                )
            
            if show_dates:
                column_config["date_creation"] = st.column_config.DatetimeColumn(
                    "Date Création", width="medium"
                )
            
            # Sélection des colonnes à afficher
            display_columns = ["id", "product_name", "description", "status", "product_type"]
            
            if show_bom_info:
                display_columns.append("bom_components")
            if show_routing_info:
                display_columns.append("operations_count")
            if show_dates:
                display_columns.append("date_creation")
            
            # Affichage du tableau avec sélection
            st.markdown(f"**Affichage:** {start_idx + 1}-{end_idx} sur {total_items} produits")
            
            edited_df = st.data_editor(
                page_df[display_columns],
                use_container_width=True,
                hide_index=True,
                column_config=column_config,
                num_rows="fixed",
                disabled=["id", "bom_components", "operations_count", "date_creation"]
            )
            
            # Actions sur les produits sélectionnés
            st.markdown("#### 🛠️ Actions")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("🗑️ Supprimer Sélectionnés"):
                    st.warning("⚠️ Fonctionnalité de suppression en développement")
                    # TODO: Implémenter suppression multiple avec confirmation
            
            with col2:
                if st.button("📋 Créer BOM"):
                    st.info("💡 Utilisez l'onglet 'Nomenclatures (BOM)' pour créer des BOM")
            
            with col3:
                if st.button("⚙️ Créer Gamme"):
                    st.info("💡 Utilisez l'onglet 'Gammes Fabrication' pour créer des gammes")
            
            with col4:
                if st.button("📊 Export Excel"):
                    # Préparation export
                    export_df = filtered_df.copy()
                    export_df['product_type_label'] = export_df['product_type'].map(PRODUCT_TYPES)
                    
                    # Conversion en CSV (simulé)
                    csv_data = export_df.to_csv(index=False)
                    st.download_button(
                        label="💾 Télécharger CSV",
                        data=csv_data,
                        file_name=f"produits_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            # Statistiques de la page
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                avg_bom_components = page_df['bom_components'].mean() if show_bom_info else 0
                st.metric("Moy. Composants BOM", f"{avg_bom_components:.1f}")
            
            with col2:
                avg_operations = page_df['operations_count'].mean() if show_routing_info else 0
                st.metric("Moy. Opérations", f"{avg_operations:.1f}")
            
            with col3:
                complexity_score = (avg_bom_components + avg_operations) / 2
                st.metric("Score Complexité", f"{complexity_score:.1f}")
        
        else:
            st.warning("🔍 Aucun produit trouvé avec les filtres appliqués.")
            
            if st.button("🔄 Réinitialiser les filtres"):
                st.rerun()
    
    else:
        st.warning("📦 Aucun produit trouvé dans la base de données.")
        st.info("💡 Créez votre premier produit dans l'onglet '➕ Nouveau Produit'")


def show_new_product_tab(product_manager: ProductManager):
    """Sous-onglet: Création de nouveau produit"""
    st.markdown("#### ➕ Créer un Nouveau Produit")
    
    # Formulaire de création avec validation en temps réel
    with st.form("new_product_form", clear_on_submit=True):
        
        # Section informations de base
        st.markdown("##### 📝 Informations de Base")
        
        col1, col2 = st.columns(2)
        
        with col1:
            product_name = st.text_input(
                "Nom du produit *",
                placeholder="Ex: Product_Test_Ass_01",
                help="Nom unique du produit. Sera utilisé comme référence principale."
            )
            
            product_type = st.selectbox(
                "Type de produit *:",
                options=list(PRODUCT_TYPES.keys()),
                format_func=lambda x: PRODUCT_TYPES[x],
                help="Type détermine la logique de gestion (BOM, gamme, etc.)"
            )
            
            auto_code = st.checkbox(
                "🔄 Générer code automatiquement",
                value=True,
                help="Génère un code basé sur le type (PF-0001, SA-0002, etc.)"
            )
        
        with col2:
            description = st.text_area(
                "Description",
                placeholder="Description détaillée du produit, caractéristiques techniques...",
                height=100,
                help="Description qui apparaîtra dans les rapports et BOM"
            )
            
            client_company_id = st.number_input(
                "Client/Projet ID",
                min_value=1,
                value=1,
                help="ID du client associé (optionnel)"
            )
        
        # Section paramètres avancés
        with st.expander("⚙️ Paramètres Avancés"):
            col1, col2 = st.columns(2)
            
            with col1:
                due_date = st.date_input(
                    "Date d'échéance",
                    value=datetime.now().date() + timedelta(days=30),
                    help="Date d'échéance prévue pour le projet"
                )
                
                create_bom = st.checkbox(
                    "📋 Créer BOM vide",
                    value=False,
                    help="Crée automatiquement une structure BOM de base"
                )
            
            with col2:
                create_routing = st.checkbox(
                    "⚙️ Créer gamme vide",
                    value=False,
                    help="Crée automatiquement une gamme de fabrication de base"
                )
                
                copy_from_product = st.selectbox(
                    "Copier depuis produit existant:",
                    options=["Aucun"] + product_manager.get_all_products()['product_name'].tolist(),
                    help="Copie BOM et gamme d'un produit existant"
                )
        
        # Aperçu du code qui sera généré
        if auto_code and product_type:
            preview_code = product_manager.generate_product_code(product_type)
            st.info(f"🏷️ **Code généré:** {preview_code}")
        
        # Validation en temps réel
        validation_messages = []
        
        if product_name:
            if len(product_name) < 3:
                validation_messages.append("⚠️ Le nom doit contenir au moins 3 caractères")
            
            # Vérifier unicité (simulation)
            existing_products = product_manager.get_all_products()
            if not existing_products.empty:
                if product_name.lower() in existing_products['product_name'].str.lower().values:
                    validation_messages.append("❌ Un produit avec ce nom existe déjà")
        
        if validation_messages:
            for msg in validation_messages:
                st.warning(msg)
        
        # Boutons de soumission
        col1, col2, col3 = st.columns(3)
        
        with col1:
            submitted = st.form_submit_button(
                "🎯 Créer le Produit",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            draft_saved = st.form_submit_button(
                "💾 Sauver Brouillon",
                use_container_width=True
            )
        
        with col3:
            preview_clicked = st.form_submit_button(
                "👁️ Aperçu",
                use_container_width=True
            )
        
        # Traitement de la soumission
        if submitted and product_name and not validation_messages:
            
            # Préparation des données
            final_name = product_name
            if auto_code:
                final_name = product_manager.generate_product_code(product_type)
            
            product_data = {
                'name': final_name,
                'description': description,
                'type': product_type,
                'client_company_id': client_company_id,
                'due_date': due_date.isoformat() if due_date else None
            }
            
            # Création du produit
            with st.spinner("🔄 Création du produit en cours..."):
                success = product_manager.create_product(product_data)
            
            if success:
                st.success(f"✅ Produit '{final_name}' créé avec succès!")
                
                # Actions post-création
                if create_bom or create_routing or copy_from_product != "Aucun":
                    st.info("🚧 Fonctionnalités post-création en développement...")
                    # TODO: Implémenter création BOM/gamme automatique
                
                # Auto-refresh pour voir le nouveau produit
                time.sleep(1)
                st.rerun()
                
            else:
                st.error("❌ Erreur lors de la création du produit.")
        
        elif submitted and validation_messages:
            st.error("❌ Veuillez corriger les erreurs avant de continuer.")
        
        elif submitted and not product_name:
            st.error("❌ Le nom du produit est obligatoire.")
        
        # Traitement brouillon
        if draft_saved:
            st.session_state.product_draft = {
                'name': product_name,
                'description': description,
                'type': product_type,
                'client_company_id': client_company_id
            }
            st.success("💾 Brouillon sauvegardé!")
        
        # Traitement aperçu
        if preview_clicked:
            if product_name:
                st.markdown("#### 👁️ Aperçu du Produit")
                
                preview_df = pd.DataFrame([{
                    'Nom': final_name if auto_code else product_name,
                    'Type': PRODUCT_TYPES[product_type],
                    'Description': description[:50] + "..." if len(description) > 50 else description,
                    'Client ID': client_company_id,
                    'Date Échéance': due_date.strftime('%Y-%m-%d') if due_date else "Non définie"
                }])
                
                st.dataframe(preview_df, use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ Saisissez au moins le nom pour l'aperçu")
    
    # Aide et conseils
    with st.expander("💡 Conseils pour la Création de Produits"):
        st.markdown("""
        **🎯 Bonnes pratiques:**
        - Utilisez des noms descriptifs et uniques
        - Choisissez le bon type de produit dès le départ
        - Rédigez des descriptions détaillées pour faciliter la recherche
        - Profitez de la copie depuis un produit existant pour gagner du temps
        
        **📋 Types de produits:**
        - **🏆 Produit Fini:** Produits vendables aux clients
        - **🔧 Sous-Assemblage:** Composants intermédiaires complexes
        - **⚙️ Composant:** Pièces élémentaires simples
        - **🧱 Matière Première:** Matières brutes de base
        
        **🔄 Codes automatiques:**
        - PF-0001, PF-0002... pour les Produits Finis
        - SA-0001, SA-0002... pour les Sous-Assemblages
        - CP-0001, CP-0002... pour les Composants
        - MP-0001, MP-0002... pour les Matières Premières
        """)
    
    # Restaurer brouillon s'il existe
    if 'product_draft' in st.session_state:
        st.markdown("---")
        st.markdown("#### 📄 Brouillon Sauvegardé")
        
        draft = st.session_state.product_draft
        st.json(draft)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Restaurer Brouillon"):
                # TODO: Implémenter restauration brouillon
                st.info("🚧 Restauration en développement...")
        
        with col2:
            if st.button("🗑️ Supprimer Brouillon"):
                del st.session_state.product_draft
                st.rerun()


def show_edit_product_tab(product_manager: ProductManager):
    """Sous-onglet: Modification de produits"""
    st.markdown("#### 🔧 Modification de Produits")
    
    # Sélection du produit à modifier
    products_df = product_manager.get_all_products()
    
    if not products_df.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            product_options = {
                f"{row['product_name']} (ID: {row['id']}) - {PRODUCT_TYPES.get(row['product_type'], row['product_type'])}": row['id']
                for _, row in products_df.iterrows()
            }
            
            selected_product = st.selectbox(
                "Sélectionner le produit à modifier:",
                options=list(product_options.keys()),
                help="Choisissez le produit que vous souhaitez modifier"
            )
        
        with col2:
            if st.button("🔄 Actualiser Liste"):
                st.rerun()
        
        if selected_product:
            product_id = product_options[selected_product]
            
            # Récupérer les détails du produit
            current_product = products_df[products_df['id'] == product_id].iloc[0]
            
            # Affichage des informations actuelles
            st.markdown("##### 📋 Informations Actuelles")
            
            info_col1, info_col2, info_col3 = st.columns(3)
            
            with info_col1:
                st.metric("Nom", current_product['product_name'])
                st.metric("Type", PRODUCT_TYPES.get(current_product['product_type'], current_product['product_type']))
            
            with info_col2:
                st.metric("Composants BOM", current_product['bom_components'])
                st.metric("Opérations", current_product['operations_count'])
            
            with info_col3:
                st.metric("Statut", current_product['status'])
                creation_date = pd.to_datetime(current_product['date_creation']).strftime('%Y-%m-%d')
                st.metric("Créé le", creation_date)
            
            # Vérifier les dépendances
            dependencies = product_manager.check_product_dependencies(product_id)
            
            if dependencies['has_dependencies']:
                st.warning("⚠️ **Attention:** Ce produit a des dépendances actives")
                
                dep_col1, dep_col2, dep_col3 = st.columns(3)
                with dep_col1:
                    st.metric("BOM Composants", dependencies['bom_count'])
                with dep_col2:
                    st.metric("Opérations", dependencies['operations_count'])
                with dep_col3:
                    st.metric("Bons de Travail", dependencies['work_orders_count'])
            
            st.markdown("---")
            
            # Formulaire de modification
            with st.form("edit_product_form"):
                st.markdown("##### ✏️ Modifier les Informations")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    new_name = st.text_input(
                        "Nom du produit:",
                        value=current_product['product_name'],
                        help="Modifier le nom du produit"
                    )
                    
                    new_status = st.selectbox(
                        "Statut:",
                        options=['ACTIF', 'INACTIF', 'ARCHIVE'],
                        index=['ACTIF', 'INACTIF', 'ARCHIVE'].index(current_product['status']) if current_product['status'] in ['ACTIF', 'INACTIF', 'ARCHIVE'] else 0,
                        help="Modifier le statut du produit"
                    )
                
                with col2:
                    new_description = st.text_area(
                        "Description:",
                        value=current_product['description'] if pd.notna(current_product['description']) else "",
                        height=100,
                        help="Modifier la description du produit"
                    )
                
                # Options avancées
                with st.expander("⚙️ Options Avancées"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        force_update = st.checkbox(
                            "🔄 Forcer mise à jour malgré dépendances",
                            value=False,
                            help="Permet la modification même si le produit a des dépendances"
                        )
                    
                    with col2:
                        update_linked = st.checkbox(
                            "🔗 Mettre à jour les éléments liés",
                            value=True,
                            help="Met à jour automatiquement les BOM et gammes liées"
                        )
                
                # Détection des changements
                changes_detected = (
                    new_name != current_product['product_name'] or
                    new_description != (current_product['description'] if pd.notna(current_product['description']) else "") or
                    new_status != current_product['status']
                )
                
                if changes_detected:
                    st.info("🔄 Modifications détectées")
                    
                    # Aperçu des changements
                    changes = []
                    if new_name != current_product['product_name']:
                        changes.append(f"Nom: '{current_product['product_name']}' → '{new_name}'")
                    if new_description != (current_product['description'] if pd.notna(current_product['description']) else ""):
                        changes.append("Description modifiée")
                    if new_status != current_product['status']:
                        changes.append(f"Statut: '{current_product['status']}' → '{new_status}'")
                    
                    for change in changes:
                        st.markdown(f"• {change}")
                
                # Boutons d'action
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    update_submitted = st.form_submit_button(
                        "💾 Sauvegarder",
                        type="primary",
                        disabled=not changes_detected,
                        use_container_width=True
                    )
                
                with col2:
                    preview_changes = st.form_submit_button(
                        "👁️ Aperçu",
                        use_container_width=True
                    )
                
                with col3:
                    reset_form = st.form_submit_button(
                        "🔄 Réinitialiser",
                        use_container_width=True
                    )
                
                # Traitement de la soumission
                if update_submitted and changes_detected:
                    
                    # Vérification des contraintes
                    can_update = True
                    
                    if dependencies['has_dependencies'] and not force_update:
                        st.error("❌ Impossible de modifier: Le produit a des dépendances actives. Cochez 'Forcer mise à jour' pour continuer.")
                        can_update = False
                    
                    if can_update:
                        # Préparation des données
                        update_data = {
                            'name': new_name,
                            'description': new_description,
                            'status': new_status
                        }
                        
                        # Mise à jour
                        with st.spinner("🔄 Mise à jour en cours..."):
                            success = product_manager.update_product(product_id, update_data)
                        
                        if success:
                            st.success(f"✅ Produit '{new_name}' mis à jour avec succès!")
                            
                            if update_linked and dependencies['has_dependencies']:
                                st.info("🔗 Mise à jour des éléments liés en cours...")
                                # TODO: Implémenter mise à jour des BOM/gammes liées
                            
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Erreur lors de la mise à jour du produit.")
                
                elif preview_changes:
                    st.markdown("#### 👁️ Aperçu des Modifications")
                    
                    comparison_data = {
                        'Champ': ['Nom', 'Description', 'Statut'],
                        'Valeur Actuelle': [
                            current_product['product_name'],
                            current_product['description'] if pd.notna(current_product['description']) else "Vide",
                            current_product['status']
                        ],
                        'Nouvelle Valeur': [
                            new_name,
                            new_description if new_description else "Vide",
                            new_status
                        ]
                    }
                    
                    comparison_df = pd.DataFrame(comparison_data)
                    st.dataframe(comparison_df, use_container_width=True, hide_index=True)
                
                elif reset_form:
                    st.rerun()
            
            # Section suppression
            st.markdown("---")
            st.markdown("##### 🗑️ Zone de Danger")
            
            with st.expander("⚠️ Supprimer le Produit", expanded=False):
                st.warning("**Attention:** Cette action est irréversible!")
                
                if dependencies['has_dependencies']:
                    st.error("❌ Impossible de supprimer: Le produit a des dépendances actives.")
                    st.markdown("**Dépendances détectées:**")
                    st.markdown(f"• {dependencies['bom_count']} composants BOM")
                    st.markdown(f"• {dependencies['operations_count']} opérations")
                    st.markdown(f"• {dependencies['work_orders_count']} bons de travail")
                else:
                    confirm_text = st.text_input(
                        f"Tapez '{current_product['product_name']}' pour confirmer la suppression:",
                        help="Confirmation requise pour éviter les suppressions accidentelles"
                    )
                    
                    if confirm_text == current_product['product_name']:
                        if st.button("🗑️ SUPPRIMER DÉFINITIVEMENT", type="primary"):
                            with st.spinner("🗑️ Suppression en cours..."):
                                success = product_manager.delete_product(product_id)
                            
                            if success:
                                st.success(f"✅ Produit '{current_product['product_name']}' supprimé avec succès!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Erreur lors de la suppression du produit.")
    
    else:
        st.warning("📦 Aucun produit disponible pour modification.")
        st.info("💡 Créez d'abord des produits dans l'onglet '➕ Nouveau Produit'")


def show_products_analytics_tab(product_manager: ProductManager):
    """Sous-onglet: Analyses et statistiques des produits"""
    st.markdown("#### 📊 Analyses et Statistiques")
    
    products_df = product_manager.get_all_products()
    
    if not products_df.empty:
        
        # Métriques générales
        st.markdown("##### 📈 Vue d'Ensemble")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_products = len(products_df)
            st.metric("Total Produits", total_products)
        
        with col2:
            active_ratio = len(products_df[products_df['status'] == 'ACTIF']) / total_products * 100
            st.metric("% Actifs", f"{active_ratio:.1f}%")
        
        with col3:
            avg_bom_complexity = products_df['bom_components'].mean()
            st.metric("Complexité BOM Moy.", f"{avg_bom_complexity:.1f}")
        
        with col4:
            avg_routing_complexity = products_df['operations_count'].mean()
            st.metric("Complexité Gamme Moy.", f"{avg_routing_complexity:.1f}")
        
        st.markdown("---")
        
        # Analyses par type
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 🏷️ Répartition par Type")
            
            type_counts = products_df['product_type'].value_counts()
            type_data = []
            
            for product_type, count in type_counts.items():
                percentage = count / total_products * 100
                type_data.append({
                    'Type': PRODUCT_TYPES.get(product_type, product_type),
                    'Nombre': count,
                    'Pourcentage': f"{percentage:.1f}%"
                })
            
            type_df = pd.DataFrame(type_data)
            st.dataframe(type_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("##### 📊 Répartition par Statut")
            
            status_counts = products_df['status'].value_counts()
            status_data = []
            
            for status, count in status_counts.items():
                percentage = count / total_products * 100
                status_data.append({
                    'Statut': status,
                    'Nombre': count,
                    'Pourcentage': f"{percentage:.1f}%"
                })
            
            status_df = pd.DataFrame(status_data)
            st.dataframe(status_df, use_container_width=True, hide_index=True)
        
        # Analyse de complexité
        st.markdown("##### 🎯 Analyse de Complexité")
        
        # Calculer score de complexité
        products_df['complexity_score'] = (
            products_df['bom_components'] * 0.6 + 
            products_df['operations_count'] * 0.4
        )
        
        # Catégoriser la complexité
        def categorize_complexity(score):
            if score == 0:
                return "🟢 Aucune"
            elif score < 5:
                return "🟡 Faible" 
            elif score < 15:
                return "🟠 Moyenne"
            else:
                return "🔴 Élevée"
        
        products_df['complexity_category'] = products_df['complexity_score'].apply(categorize_complexity)
        
        col1, col2 = st.columns(2)
        
        with col1:
            complexity_counts = products_df['complexity_category'].value_counts()
            complexity_data = []
            
            for category, count in complexity_counts.items():
                percentage = count / total_products * 100
                complexity_data.append({
                    'Complexité': category,
                    'Nombre': count,
                    'Pourcentage': f"{percentage:.1f}%"
                })
            
            complexity_df = pd.DataFrame(complexity_data)
            st.dataframe(complexity_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("**Top 5 Produits Plus Complexes:**")
            
            top_complex = products_df.nlargest(5, 'complexity_score')[
                ['product_name', 'bom_components', 'operations_count', 'complexity_score']
            ].round(1)
            
            st.dataframe(
                top_complex,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'product_name': 'Produit',
                    'bom_components': 'BOM',
                    'operations_count': 'Ops',
                    'complexity_score': 'Score'
                }
            )
        
        # Tendances temporelles
        st.markdown("##### 📅 Tendances de Création")
        
        if 'date_creation' in products_df.columns:
            products_df['creation_date'] = pd.to_datetime(products_df['date_creation'])
            products_df['creation_month'] = products_df['creation_date'].dt.to_period('M')
            
            monthly_creation = products_df.groupby('creation_month').size().reset_index(name='count')
            monthly_creation['month_str'] = monthly_creation['creation_month'].astype(str)
            
            if len(monthly_creation) > 1:
                st.line_chart(
                    monthly_creation.set_index('month_str')['count'],
                    use_container_width=True
                )
            else:
                st.info("📊 Pas assez de données pour afficher la tendance temporelle")
        
        # Recommandations
        st.markdown("##### 💡 Recommandations")
        
        recommendations = []
        
        # Analyse des produits sans BOM/Gamme
        no_bom_count = len(products_df[products_df['bom_components'] == 0])
        no_routing_count = len(products_df[products_df['operations_count'] == 0])
        
        if no_bom_count > 0:
            recommendations.append(f"📋 {no_bom_count} produit(s) sans BOM - Complétez les nomenclatures")
        
        if no_routing_count > 0:
            recommendations.append(f"⚙️ {no_routing_count} produit(s) sans gamme - Définissez les opérations")
        
        # Analyse de déséquilibre
        type_distribution = products_df['product_type'].value_counts()
        if len(type_distribution) > 1:
            max_type_ratio = type_distribution.max() / total_products
            if max_type_ratio > 0.8:
                dominant_type = type_distribution.index[0]
                recommendations.append(f"⚖️ Déséquilibre détecté - 80%+ sont des {PRODUCT_TYPES.get(dominant_type, dominant_type)}")
        
        # Analyse de complexité
        high_complexity_count = len(products_df[products_df['complexity_score'] > 20])
        if high_complexity_count > total_products * 0.2:
            recommendations.append(f"🎯 {high_complexity_count} produit(s) très complexes - Considérez la simplification")
        
        if recommendations:
            for rec in recommendations:
                st.info(rec)
        else:
            st.success("✅ Aucune recommandation - Portfolio produits bien équilibré!")
        
        # Export des analyses
        st.markdown("---")
        
        if st.button("📊 Exporter Rapport d'Analyse"):
            # Préparation rapport complet
            report_data = {
                'summary': {
                    'total_products': total_products,
                    'active_ratio': active_ratio,
                    'avg_bom_complexity': avg_bom_complexity,
                    'avg_routing_complexity': avg_routing_complexity
                },
                'type_distribution': type_counts.to_dict(),
                'status_distribution': status_counts.to_dict(),
                'complexity_distribution': complexity_counts.to_dict(),
                'recommendations': recommendations,
                'generated_at': datetime.now().isoformat()
            }
            
            # Conversion en JSON pour download
            import json
            report_json = json.dumps(report_data, ensure_ascii=False, indent=2)
            
            st.download_button(
                label="💾 Télécharger Rapport JSON",
                data=report_json,
                file_name=f"analyse_produits_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    else:
        st.warning("📊 Aucune donnée disponible pour l'analyse.")
        st.info("💡 Créez des produits pour voir apparaître les analyses")
        
        # Graphique de démonstration
        st.markdown("##### 📈 Exemple d'Analyse (Données de Démonstration)")
        
        demo_data = {
            'Type': ['Produits Finis', 'Sous-Assemblages', 'Composants', 'Matières Premières'],
            'Nombre': [12, 8, 25, 15]
        }
        demo_df = pd.DataFrame(demo_data)
        
        st.bar_chart(demo_df.set_index('Type')['Nombre'], use_container_width=True)


def show_bom_tab():
    """Onglet 2: Nomenclatures (BOM) - Interface identique à l'image 1"""
    st.markdown("### 📋 Nomenclatures (BOM)")
    
    # Initialisation gestionnaires
    db = ERPDatabase()
    product_manager = ProductManager(db)
    bom_manager = BOMManager(db)
    
    # Récupération produits
    products_df = product_manager.get_all_products()
    
    if not products_df.empty:
        # Section sélection produit principal
        st.markdown("#### 🎯 Sélection du Produit Principal")
        
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            product_options = {f"{row['product_name']} (ID: {row['id']})": row['id'] 
                              for _, row in products_df.iterrows()}
            
            selected_product = st.selectbox(
                "Produit à analyser:",
                options=list(product_options.keys()),
                help="Sélectionnez le produit pour afficher/modifier sa nomenclature",
                key="bom_product_selector"
            )
        
        with col2:
            if st.button("🔄 Actualiser", key="bom_refresh"):
                st.rerun()
        
        with col3:
            bom_view_mode = st.selectbox(
                "Mode d'affichage:",
                ["Standard", "Explosion", "Coûts"],
                help="Choisissez le mode d'affichage de la BOM"
            )
        
        if selected_product:
            product_id = product_options[selected_product]
            selected_product_info = products_df[products_df['id'] == product_id].iloc[0]
            
            # En-tête avec informations produit
            st.markdown("---")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"**📦 Produit:** {selected_product_info['product_name']}")
                st.markdown(f"**🏷️ Type:** {PRODUCT_TYPES.get(selected_product_info['product_type'], selected_product_info['product_type'])}")
            
            with col2:
                bom_df = bom_manager.get_bom_for_product(product_id)
                components_count = len(bom_df)
                st.metric("Composants", components_count)
            
            with col3:
                total_cost = bom_manager.calculate_bom_cost(product_id)
                if isinstance(total_cost, dict):
                    total_cost_value = total_cost.get('total_cost', 0)
                else:
                    total_cost_value = total_cost
                st.metric("Coût Total", format_currency(total_cost_value))
            
            with col4:
                if not bom_df.empty:
                    total_cost = bom_manager.calculate_bom_cost(product_id)
                    if isinstance(total_cost, dict):
                        total_cost_value = total_cost.get('total_cost', 0)
                    else:
                        total_cost_value = total_cost
                    avg_cost_per_component = total_cost_value / components_count
                    st.metric("Coût Moy./Comp.", format_currency(avg_cost_per_component))
                else:
                    st.metric("Coût Moy./Comp.", "N/A")
            
            # Type de BOM (comme dans l'image de référence)
            st.markdown("#### ⚙️ Type de BOM")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                bom_type = st.radio(
                    "Sélectionnez le type de BOM:",
                    options=list(BOM_TYPES.keys()),
                    format_func=lambda x: BOM_TYPES[x],
                    horizontal=True,
                    help="Type de nomenclature pour ce produit"
                )
            
            # Interface principale BOM - Identique à l'image 1
            st.markdown("#### 📋 Nomenclature - Liste des Composants")
            
            if bom_view_mode == "Explosion":
                show_bom_explosion_view(bom_manager, product_id, selected_product_info['product_name'])
            elif bom_view_mode == "Coûts":
                show_bom_cost_analysis_view(bom_manager, product_id)
            else:
                show_bom_standard_view(bom_manager, product_id, selected_product_info['product_name'])
    
    else:
        st.warning("📦 Aucun produit disponible pour créer des nomenclatures.")
        st.info("💡 Créez d'abord des produits dans l'onglet **📦 Produits**")


def show_bom_standard_view(bom_manager: BOMManager, product_id: int, product_name: str):
    """Affichage standard de la BOM - Interface comme image 1"""
    
    # Récupération BOM
    bom_df = bom_manager.get_bom_for_product(product_id)
    
    # Session state pour gestion des modifications
    if 'bom_editing_mode' not in st.session_state:
        st.session_state.bom_editing_mode = False
    if 'bom_selected_rows' not in st.session_state:
        st.session_state.bom_selected_rows = []
    
    # Barre d'outils - Identique à l'image de référence
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("➕ Add a line", key="bom_add_line", use_container_width=True):
            st.session_state.bom_show_add_form = True
    
    with col2:
        if st.button("📖 Catalog", key="bom_catalog", use_container_width=True):
            st.session_state.bom_show_catalog = True
    
    with col3:
        edit_mode = st.checkbox("✏️ Mode Édition", value=st.session_state.bom_editing_mode)
        st.session_state.bom_editing_mode = edit_mode
    
    with col4:
        if st.button("💾 Sauvegarder", key="bom_save", use_container_width=True):
            st.success("✅ BOM sauvegardée!")
    
    with col5:
        if st.button("📊 Exporter", key="bom_export", use_container_width=True):
            show_bom_export_options(bom_df, product_name)
    
    # Affichage de la BOM principale
    if not bom_df.empty:
        
        # Configuration des colonnes - Identique à l'image 1
        column_config = {
            "component_code": st.column_config.TextColumn(
                "Component",
                width="medium",
                help="Code du composant"
            ),
            "component_name": st.column_config.TextColumn(
                "Designation", 
                width="large",
                help="Désignation complète du composant"
            ),
            "quantity": st.column_config.NumberColumn(
                "Quantity",
                width="small",
                format="%.3f",
                min_value=0,
                help="Quantité nécessaire"
            ),
            "unit": st.column_config.SelectboxColumn(
                "Unit",
                width="small",
                options=["PC", "KG", "M", "L", "M2", "M3", "H"],
                help="Unité de mesure"
            ),
            "unit_price": st.column_config.NumberColumn(
                "Prix Unit.",
                width="small",
                format="%.2f $",
                min_value=0,
                help="Prix unitaire"
            ),
            "total_cost": st.column_config.NumberColumn(
                "Total",
                width="small", 
                format="%.2f $",
                help="Coût total = Quantité × Prix unitaire"
            ),
            "supplier": st.column_config.TextColumn(
                "Fournisseur",
                width="medium",
                help="Fournisseur principal"
            ),
            "stock_available": st.column_config.NumberColumn(
                "Stock",
                width="small",
                format="%.1f",
                help="Stock disponible"
            ),
            "stock_status": st.column_config.SelectboxColumn(
                "Statut Stock",
                width="small",
                options=["EN_STOCK", "RUPTURE", "COMMANDE", "NON_STOCKE"],
                help="Statut du stock"
            )
        }
        
        # Colonnes à afficher selon le mode
        if st.session_state.bom_editing_mode:
            display_columns = [
                "component_code", "component_name", "quantity", "unit", 
                "unit_price", "total_cost", "supplier"
            ]
        else:
            display_columns = [
                "component_code", "component_name", "quantity", "unit", 
                "total_cost", "stock_available", "stock_status"
            ]
        
        # Affichage tableau principal avec édition
        st.markdown(f"**📋 Composants pour: {product_name}**")
        
        if st.session_state.bom_editing_mode:
            # Mode édition avec data_editor
            edited_bom = st.data_editor(
                bom_df[display_columns],
                use_container_width=True,
                hide_index=True,
                column_config=column_config,
                num_rows="dynamic",
                key="bom_editor"
            )
            
            # Boutons de validation des modifications
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("✅ Valider Modifications", type="primary"):
                    # TODO: Implémenter sauvegarde des modifications
                    with st.spinner("💾 Sauvegarde en cours..."):
                        # Logic to save changes
                        pass
                    st.success("✅ Modifications sauvegardées!")
            
            with col2:
                if st.button("❌ Annuler"):
                    st.session_state.bom_editing_mode = False
                    st.rerun()
            
            with col3:
                if st.button("🗑️ Supprimer Sélectionnés"):
                    show_bom_delete_confirmation()
        
        else:
            # Mode consultation
            st.dataframe(
                bom_df[display_columns],
                use_container_width=True,
                hide_index=True,
                column_config=column_config
            )
        
        # Statistiques BOM détaillées
        show_bom_statistics(bom_df)
        
        # Alertes et recommandations
        show_bom_alerts(bom_df)
    
    else:
        # BOM vide - Interface de création
        show_empty_bom_interface(bom_manager, product_id, product_name)
    
    # Formulaires modaux
    if st.session_state.get('bom_show_add_form', False):
        show_add_component_form(bom_manager, product_id)
    
    if st.session_state.get('bom_show_catalog', False):
        show_component_catalog()


def show_bom_explosion_view(bom_manager: BOMManager, product_id: int, product_name: str):
    """Vue explosion multiniveaux de la BOM"""
    st.markdown("#### 🌳 Explosion Multiniveaux")
    
    # Options d'explosion
    col1, col2, col3 = st.columns(3)
    
    with col1:
        explosion_depth = st.slider("Profondeur max:", 1, 10, 5)
    
    with col2:
        show_costs = st.checkbox("💰 Afficher coûts", value=True)
    
    with col3:
        show_stock = st.checkbox("📦 Afficher stock", value=True)
    
    # Récupération explosion
    with st.spinner("🔄 Explosion BOM en cours..."):
        explosion = bom_manager.explode_bom(product_id, parent_quantity=1.0)
    
    if explosion:
        # Affichage en arbre hiérarchique
        st.markdown(f"**🌳 Structure hiérarchique pour: {product_name}**")
        
        # Grouper par niveau
        levels = {}
        for item in explosion:
            level = item['level']
            if level not in levels:
                levels[level] = []
            levels[level].append(item)
        
        # Affichage par niveau
        for level in sorted(levels.keys()):
            level_items = levels[level]
            
            # En-tête de niveau
            indent = "　" * level  # Espaces d'indentation
            if level == 0:
                st.markdown(f"**📦 {indent}PRODUIT PRINCIPAL**")
            else:
                st.markdown(f"**🔧 {indent}NIVEAU {level}**")
            
            # Tableau des items de ce niveau
            level_data = []
            for item in level_items:
                row_data = {
                    'Composant': f"{indent}├─ {item['component_name']}",
                    'Code': item['component_code'],
                    'Qté': f"{item['quantity_total']:.3f}",
                    'Unité': item['unit']
                }
                
                if show_costs:
                    row_data['Prix Unit.'] = f"{item['unit_price']:.2f} $"
                    row_data['Coût Total'] = f"{item['total_cost']:.2f} $"
                
                if show_stock:
                    row_data['Stock Dispo'] = f"{item.get('stock_available', 0):.1f}"
                    row_data['Statut'] = item.get('stock_status', 'INCONNU')
                
                level_data.append(row_data)
            
            if level_data:
                level_df = pd.DataFrame(level_data)
                st.dataframe(level_df, use_container_width=True, hide_index=True)
        
        # Résumé explosion
        st.markdown("#### 📊 Résumé de l'Explosion")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_components = len(explosion)
            st.metric("Composants Total", total_components)
        
        with col2:
            if len(explosion) > 0:
                max_level = max(item.get('level', 0) for item in explosion)
                st.metric("Profondeur Max", max_level + 1)
            else:
                st.metric("Profondeur Max", 0)
        
        with col3:
            if len(explosion) > 0:
                total_cost = sum(item.get('total_cost', 0) for item in explosion)
                st.metric("Coût Total", format_currency(total_cost))
            else:
                st.metric("Coût Total", format_currency(0))
        
        with col4:
            if len(explosion) > 0:
                unique_suppliers = len(set(item.get('supplier', '') for item in explosion if item.get('supplier')))
                st.metric("Fournisseurs", unique_suppliers)
            else:
                st.metric("Fournisseurs", 0)
        
        # Analyse des besoins
        show_explosion_analysis(explosion)
    
    else:
        st.warning("🔍 Aucun composant trouvé pour l'explosion.")


def show_bom_cost_analysis_view(bom_manager: BOMManager, product_id: int):
    """Vue analyse des coûts détaillée"""
    st.markdown("#### 💰 Analyse des Coûts")
    
    # Calculs coûts détaillés
    cost_details = bom_manager.calculate_bom_cost(product_id)
    
    # S'assurer que cost_details est un dictionnaire
    if not isinstance(cost_details, dict):
        cost_details = {'total_cost': cost_details, 'materials_cost': 0, 'components_cost': 0, 'sub_assemblies_cost': 0}
    
    if cost_details.get('total_cost', 0) > 0:
        
        # Métriques principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Matières Premières", format_currency(cost_details.get('materials_cost', 0)))
        
        with col2:
            st.metric("Composants", format_currency(cost_details.get('components_cost', 0)))
        
        with col3:
            st.metric("Sous-Assemblages", format_currency(cost_details.get('sub_assemblies_cost', 0)))
        
        with col4:
            st.metric("TOTAL BOM", format_currency(cost_details.get('total_cost', 0)))
        
        # Répartition des coûts
        cost_breakdown = cost_details.get('cost_breakdown', [])
        
        if cost_breakdown:
            # Graphique de répartition
            st.markdown("##### 📊 Répartition des Coûts par Composant")
            
            # Préparer données pour graphique
            chart_data = []
            for item in cost_breakdown[:10]:  # Top 10
                chart_data.append({
                    'Composant': item['component'][:20] + "..." if len(item['component']) > 20 else item['component'],
                    'Coût': item['total_cost']
                })
            
            if chart_data:
                chart_df = pd.DataFrame(chart_data)
                st.bar_chart(chart_df.set_index('Composant')['Coût'], use_container_width=True)
            
            # Tableau détaillé des coûts
            st.markdown("##### 📋 Détail des Coûts par Composant")
            
            cost_detail_df = pd.DataFrame(cost_breakdown)
            
            # Configuration colonnes
            cost_column_config = {
                "level": st.column_config.NumberColumn("Niveau", width="small"),
                "component": st.column_config.TextColumn("Composant", width="large"),
                "quantity": st.column_config.NumberColumn("Quantité", format="%.3f", width="small"),
                "unit_price": st.column_config.NumberColumn("Prix Unit.", format="%.2f $", width="small"),
                "total_cost": st.column_config.NumberColumn("Coût Total", format="%.2f $", width="small")
            }
            
            st.dataframe(
                cost_detail_df[['level', 'component', 'quantity', 'unit_price', 'total_cost']],
                use_container_width=True,
                hide_index=True,
                column_config=cost_column_config
            )
            
            # Analyse des coûts
            st.markdown("##### 🎯 Analyse des Coûts")
            
            # Top 5 composants les plus chers
            sorted_costs = sorted(cost_breakdown, key=lambda x: x['total_cost'], reverse=True)
            top_expensive = sorted_costs[:5]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🔴 Top 5 Plus Chers:**")
                for i, item in enumerate(top_expensive, 1):
                    percentage = (item['total_cost'] / cost_details['total_cost']) * 100
                    st.markdown(f"{i}. {item['component'][:30]}... - {format_currency(item['total_cost'])} ({percentage:.1f}%)")
            
            with col2:
                st.markdown("**📊 Recommandations:**")
                
                # Analyse automatique
                total_cost = cost_details['total_cost']
                
                if total_cost > 1000:
                    st.info("💡 Coût élevé détecté - Vérifiez les fournisseurs")
                
                if len([item for item in cost_breakdown if item['total_cost'] > total_cost * 0.2]) > 0:
                    st.warning("⚠️ Composants à forte valeur - Négociation recommandée")
                
                if cost_details.get('materials_cost', 0) > total_cost * 0.7:
                    st.info("🧱 Coût matières élevé - Optimisation possible")
        
        # Export analyse coûts
        if st.button("📊 Exporter Analyse Coûts"):
            # Préparer rapport
            cost_report = {
                'product_id': product_id,
                'total_cost': cost_details['total_cost'],
                'breakdown_by_type': {
                    'materials': cost_details.get('materials_cost', 0),
                    'components': cost_details.get('components_cost', 0),
                    'sub_assemblies': cost_details.get('sub_assemblies_cost', 0)
                },
                'detailed_breakdown': cost_breakdown,
                'analysis_date': datetime.now().isoformat()
            }
            
            import json
            report_json = json.dumps(cost_report, ensure_ascii=False, indent=2)
            
            st.download_button(
                label="💾 Télécharger Rapport Coûts",
                data=report_json,
                file_name=f"analyse_couts_bom_{product_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    else:
        st.warning("💰 Aucune donnée de coût disponible pour ce produit.")


def show_bom_statistics(bom_df: pd.DataFrame):
    """Affiche les statistiques détaillées de la BOM"""
    st.markdown("#### 📊 Statistiques BOM")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_components = len(bom_df)
        st.metric("Total Composants", total_components)
    
    with col2:
        total_quantity = bom_df['quantity'].sum()
        st.metric("Quantité Totale", f"{total_quantity:.2f}")
    
    with col3:
        total_cost = bom_df['total_cost'].sum()
        st.metric("Coût Total", format_currency(total_cost))
    
    with col4:
        unique_suppliers = bom_df['supplier'].nunique()
        st.metric("Fournisseurs", unique_suppliers)
    
    # Analyse des unités
    if not bom_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📏 Répartition par Unité:**")
            unit_counts = bom_df['unit'].value_counts()
            for unit, count in unit_counts.items():
                percentage = (count / total_components) * 100
                st.markdown(f"• {unit}: {count} ({percentage:.1f}%)")
        
        with col2:
            st.markdown("**💰 Analyse des Prix:**")
            avg_price = bom_df['unit_price'].mean()
            max_price = bom_df['unit_price'].max()
            min_price = bom_df['unit_price'].min()
            
            st.markdown(f"• Prix moyen: {format_currency(avg_price)}")
            st.markdown(f"• Prix max: {format_currency(max_price)}")
            st.markdown(f"• Prix min: {format_currency(min_price)}")


def show_bom_alerts(bom_df: pd.DataFrame):
    """Affiche les alertes et recommandations BOM"""
    if bom_df.empty:
        return
    
    alerts = []
    
    # Vérification stock
    if 'stock_available' in bom_df.columns:
        out_of_stock = bom_df[bom_df['stock_available'] <= 0]
        if not out_of_stock.empty:
            alerts.append(f"🔴 {len(out_of_stock)} composant(s) en rupture de stock")
    
    # Vérification prix manquants
    no_price = bom_df[bom_df['unit_price'] <= 0]
    if not no_price.empty:
        alerts.append(f"⚠️ {len(no_price)} composant(s) sans prix défini")
    
    # Vérification fournisseurs manquants
    no_supplier = bom_df[bom_df['supplier'].isna() | (bom_df['supplier'] == '')]
    if not no_supplier.empty:
        alerts.append(f"📋 {len(no_supplier)} composant(s) sans fournisseur")
    
    # Affichage des alertes
    if alerts:
        st.markdown("#### ⚠️ Alertes BOM")
        for alert in alerts:
            st.warning(alert)
    else:
        st.success("✅ Aucune alerte détectée - BOM complète")


def show_empty_bom_interface(bom_manager: BOMManager, product_id: int, product_name: str):
    """Interface pour BOM vide"""
    st.markdown("#### 📋 BOM Vide - Commencez la Configuration")
    
    # Message d'aide
    st.info(f"🎯 **Produit sélectionné:** {product_name}")
    st.markdown("""
    **📋 Cette nomenclature est vide. Vous pouvez:**
    - ➕ Ajouter des composants manuellement
    - 📖 Importer depuis le catalogue
    - 📂 Copier depuis un autre produit
    - 📄 Importer depuis un fichier Excel/CSV
    """)
    
    # Options de création rapide
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Ajouter Premier Composant", use_container_width=True):
            st.session_state.bom_show_add_form = True
    
    with col2:
        if st.button("📂 Copier BOM Existante", use_container_width=True):
            show_copy_bom_interface(bom_manager, product_id)
    
    with col3:
        if st.button("📄 Import Excel/CSV", use_container_width=True):
            show_import_bom_interface()
    
    # Template de BOM suggéré
    with st.expander("💡 Template de BOM Suggéré"):
        st.markdown("""
        **🏗️ Structure de BOM typique:**
        
        **Pour un Produit Fini:**
        - 🔧 Sous-assemblages principaux
        - ⚙️ Composants mécaniques
        - 🔩 Visserie et fixations
        - 🧱 Matières premières
        
        **Exemples de composants:**
        - `SA-001`: Sous-assemblage principal
        - `CP-001`: Pièce usinée
        - `MP-001`: Matière première (acier, plastique...)
        - `VIS-M6x20`: Visserie standard
        """)


def show_add_component_form(bom_manager: BOMManager, product_id: int):
    """Formulaire d'ajout de composant"""
    st.markdown("#### ➕ Ajouter un Composant")
    
    with st.form("add_component_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            component_code = st.text_input(
                "Code composant *",
                placeholder="Ex: CP-001",
                help="Code unique du composant"
            )
            
            designation = st.text_input(
                "Désignation *",
                placeholder="Ex: Pièce usinée principale",
                help="Description détaillée du composant"
            )
            
            quantity = st.number_input(
                "Quantité *",
                min_value=0.001,
                value=1.0,
                step=0.001,
                format="%.3f",
                help="Quantité nécessaire par unité de produit fini"
            )
        
        with col2:
            unit = st.selectbox(
                "Unité *",
                options=["PC", "KG", "M", "L", "M2", "M3", "H"],
                help="Unité de mesure"
            )
            
            unit_price = st.number_input(
                "Prix unitaire",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f",
                help="Prix unitaire en devise locale"
            )
            
            supplier = st.text_input(
                "Fournisseur",
                placeholder="Ex: Fournisseur ABC",
                help="Fournisseur principal"
            )
        
        # Options avancées
        with st.expander("⚙️ Options Avancées"):
            notes = st.text_area(
                "Notes",
                placeholder="Notes techniques, spécifications...",
                help="Informations complémentaires"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                is_critical = st.checkbox("🔴 Composant critique")
            with col2:
                auto_order = st.checkbox("🔄 Commande automatique")
        
        # Aperçu du composant
        if component_code and designation:
            total_cost = quantity * unit_price
            st.markdown("**👁️ Aperçu:**")
            st.markdown(f"• {quantity:.3f} {unit} de '{designation}' = {format_currency(total_cost)}")
        
        # Boutons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            submitted = st.form_submit_button("✅ Ajouter", type="primary")
        
        with col2:
            if st.form_submit_button("👁️ Aperçu"):
                if component_code and designation:
                    st.info(f"Composant: {component_code} - {designation} ({quantity} {unit})")
        
        with col3:
            if st.form_submit_button("❌ Annuler"):
                st.session_state.bom_show_add_form = False
                st.rerun()
        
        # Traitement soumission
        if submitted:
            if component_code and designation and quantity > 0:
                component_data = {
                    'code': component_code,
                    'designation': designation,
                    'quantity': quantity,
                    'unit': unit,
                    'unit_price': unit_price,
                    'supplier': supplier,
                    'notes': notes
                }
                
                with st.spinner("➕ Ajout du composant..."):
                    success = bom_manager.add_component_to_bom(product_id, component_data)
                
                if success:
                    st.success(f"✅ Composant '{component_code}' ajouté avec succès!")
                    st.session_state.bom_show_add_form = False
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de l'ajout du composant.")
            else:
                st.error("❌ Veuillez remplir tous les champs obligatoires.")


def show_component_catalog():
    """Catalogue de composants"""
    st.markdown("#### 📖 Catalogue de Composants")
    
    # Simulation d'un catalogue
    catalog_components = [
        {"code": "CP-001", "name": "Pièce usinée standard", "unit": "PC", "price": 25.50},
        {"code": "VIS-M6", "name": "Vis M6x20 inox", "unit": "PC", "price": 0.15},
        {"code": "MP-ACIER", "name": "Acier S235 - Plaque 10mm", "unit": "KG", "price": 2.80},
        {"code": "SA-BASE", "name": "Sous-assemblage de base", "unit": "PC", "price": 156.00},
        {"code": "ROULEMENT", "name": "Roulement à billes 6204", "unit": "PC", "price": 12.30}
    ]
    
    catalog_df = pd.DataFrame(catalog_components)
    
    # Recherche dans le catalogue
    search_term = st.text_input("🔍 Rechercher dans le catalogue:", placeholder="Code ou nom du composant...")
    
    if search_term:
        mask = (
            catalog_df['code'].str.contains(search_term, case=False) |
            catalog_df['name'].str.contains(search_term, case=False)
        )
        catalog_df = catalog_df[mask]
    
    # Affichage catalogue
    if not catalog_df.empty:
        selected_components = st.dataframe(
            catalog_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row"
        )
        
        if st.button("✅ Ajouter Sélectionnés à la BOM"):
            st.info("🚧 Ajout depuis catalogue en développement...")
    
    if st.button("❌ Fermer Catalogue"):
        st.session_state.bom_show_catalog = False
        st.rerun()


def show_bom_export_options(bom_df: pd.DataFrame, product_name: str):
    """Options d'export de la BOM"""
    st.markdown("#### 📊 Options d'Export")
    
    export_formats = ["CSV", "Excel", "PDF", "JSON"]
    selected_format = st.selectbox("Format d'export:", export_formats)
    
    if selected_format == "CSV":
        csv_data = bom_df.to_csv(index=False)
        st.download_button(
            label="💾 Télécharger CSV",
            data=csv_data,
            file_name=f"BOM_{product_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    elif selected_format == "JSON":
        json_data = bom_df.to_json(orient='records', indent=2)
        st.download_button(
            label="💾 Télécharger JSON", 
            data=json_data,
            file_name=f"BOM_{product_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    else:
        st.info(f"🚧 Export {selected_format} en développement...")


def show_explosion_analysis(explosion: List[Dict]):
    """Analyse détaillée de l'explosion BOM"""
    st.markdown("#### 🔍 Analyse de l'Explosion")
    
    # Analyse par niveau
    level_analysis = {}
    for item in explosion:
        level = item.get('level', 0)
        if level not in level_analysis:
            level_analysis[level] = {'count': 0, 'total_cost': 0}
        level_analysis[level]['count'] += 1
        level_analysis[level]['total_cost'] += item.get('total_cost', 0)
    
    # Affichage analyse par niveau
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📊 Analyse par Niveau:**")
        for level in sorted(level_analysis.keys()):
            data = level_analysis[level]
            st.markdown(f"• Niveau {level}: {data['count']} composants - {format_currency(data['total_cost'])}")
    
    with col2:
        st.markdown("**🎯 Points d'Attention:**")
        
        # Détection anomalies
        total_cost = sum(item.get('total_cost', 0) for item in explosion)
        
        # Composants chers
        expensive_items = [item for item in explosion if item.get('total_cost', 0) > total_cost * 0.1]
        if expensive_items and total_cost > 0:
            st.warning(f"⚠️ {len(expensive_items)} composant(s) représentent >10% du coût")
        
        # Ruptures de stock
        out_of_stock = [item for item in explosion if item.get('stock_available', 0) <= 0]
        if out_of_stock:
            st.error(f"🔴 {len(out_of_stock)} composant(s) en rupture")
        
        # Fournisseurs manquants
        no_supplier = [item for item in explosion if not item.get('supplier')]
        if no_supplier:
            st.info(f"📋 {len(no_supplier)} composant(s) sans fournisseur")


def show_copy_bom_interface(bom_manager: BOMManager, target_product_id: int):
    """Interface de copie de BOM"""
    st.markdown("#### 📂 Copier BOM Existante")
    st.info("🚧 Fonctionnalité de copie BOM en développement...")


def show_import_bom_interface():
    """Interface d'import BOM"""
    st.markdown("#### 📄 Import BOM depuis Excel/CSV")
    st.info("🚧 Fonctionnalité d'import BOM en développement...")


def show_bom_delete_confirmation():
    """Confirmation de suppression BOM"""
    st.markdown("#### 🗑️ Suppression de Composants")
    st.info("🚧 Fonctionnalité de suppression en développement...")


def show_routing_tab():
    """Onglet 3: Gammes de Fabrication - Interface identique à l'image 2"""
    st.markdown("### ⚙️ Gammes de Fabrication")
    
    # Initialisation gestionnaires
    db = ERPDatabase()
    product_manager = ProductManager(db)
    routing_manager = RoutingManager(db)
    
    # Récupération produits
    products_df = product_manager.get_all_products()
    
    if not products_df.empty:
        # Section sélection produit principal - Identique à l'image 2
        st.markdown("#### 🎯 Sélection du Produit à Fabriquer")
        
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            product_options = {f"{row['product_name']} (ID: {row['id']})": row['id'] 
                              for _, row in products_df.iterrows()}
            
            selected_product = st.selectbox(
                "Produit à fabriquer:",
                options=list(product_options.keys()),
                help="Sélectionnez le produit pour afficher/modifier sa gamme de fabrication",
                key="routing_product_selector"
            )
        
        with col2:
            if st.button("🔄 Actualiser", key="routing_refresh"):
                st.rerun()
        
        with col3:
            routing_view_mode = st.selectbox(
                "Mode d'affichage:",
                ["Standard", "Planification", "Coûts"],
                help="Choisissez le mode d'affichage de la gamme"
            )
        
        if selected_product:
            product_id = product_options[selected_product]
            selected_product_info = products_df[products_df['id'] == product_id].iloc[0]
            
            # Type de BOM - Exactement comme dans l'image 2
            st.markdown("#### ⚙️ Type de Fabrication")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                manufacturing_type = st.radio(
                    "Type de fabrication:",
                    options=["Manufacture this product", "Kit", "Subcontracting"],
                    index=0,
                    help="Type de production pour ce produit"
                )
            
            with col2:
                routing_df = routing_manager.get_routing_for_product(product_id)
                operations_count = len(routing_df)
                st.metric("Opérations", operations_count)
            
            with col3:
                if not routing_df.empty:
                    total_duration = routing_df['duration_minutes'].sum()
                    st.metric("Temps Total", format_duration(total_duration))
                else:
                    st.metric("Temps Total", "0 min")
            
            with col4:
                if not routing_df.empty:
                    routing_costs = routing_manager.calculate_routing_cost(product_id)
                    total_cost = routing_costs.get('total_cost', 0)
                    st.metric("Coût Total", format_currency(total_cost))
                else:
                    st.metric("Coût Total", format_currency(0))
            
            # Interface principale Gammes - Identique à l'image 2
            st.markdown("#### ⚙️ Gamme de Fabrication - Séquence d'Opérations")
            
            if routing_view_mode == "Planification":
                show_routing_planning_view(routing_manager, product_id, selected_product_info['product_name'])
            elif routing_view_mode == "Coûts":
                show_routing_cost_analysis_view(routing_manager, product_id)
            else:
                show_routing_standard_view(routing_manager, product_id, selected_product_info['product_name'])
    
    else:
        st.warning("📦 Aucun produit disponible pour créer des gammes de fabrication.")
        st.info("💡 Créez d'abord des produits dans l'onglet **📦 Produits**")


def show_routing_standard_view(routing_manager: RoutingManager, product_id: int, product_name: str):
    """Affichage standard de la gamme - Interface comme image 2"""
    
    # Récupération gamme
    routing_df = routing_manager.get_routing_for_product(product_id)
    
    # Session state pour gestion des modifications
    if 'routing_editing_mode' not in st.session_state:
        st.session_state.routing_editing_mode = False
    if 'routing_show_add_form' not in st.session_state:
        st.session_state.routing_show_add_form = False
    
    # Barre d'outils - Identique à l'image de référence
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("➕ Add a line", key="routing_add_line", use_container_width=True):
            st.session_state.routing_show_add_form = True
    
    with col2:
        if st.button("📋 Copy Existing Operations", key="routing_copy", use_container_width=True):
            st.session_state.routing_show_copy = True
    
    with col3:
        edit_mode = st.checkbox("✏️ Mode Édition", value=st.session_state.routing_editing_mode)
        st.session_state.routing_editing_mode = edit_mode
    
    with col4:
        if st.button("💾 Sauvegarder", key="routing_save", use_container_width=True):
            st.success("✅ Gamme sauvegardée!")
    
    with col5:
        if st.button("📊 Exporter", key="routing_export", use_container_width=True):
            show_routing_export_options(routing_df, product_name)
    
    # Affichage de la gamme principale
    if not routing_df.empty:
        
        # Calcul temps total comme dans l'image 2
        total_duration = routing_df['duration_minutes'].sum()
        st.markdown(f"**⏱️ Temps total de fabrication: {total_duration:.0f} minutes ({total_duration/60:.1f} heures)**")
        
        # Configuration des colonnes - Identique à l'image 2
        column_config = {
            "operation_seq": st.column_config.NumberColumn(
                "Operation",
                width="small",
                format="%d",
                help="Numéro de séquence de l'opération"
            ),
            "operation_name": st.column_config.TextColumn(
                "Description", 
                width="large",
                help="Description détaillée de l'opération"
            ),
            "work_center_name": st.column_config.SelectboxColumn(
                "Work Center",
                width="medium",
                help="Poste de travail assigné"
            ),
            "duration_minutes": st.column_config.NumberColumn(
                "Duration (min)",
                width="small",
                format="%.0f",
                min_value=1,
                help="Durée de l'opération en minutes"
            ),
            "operation_cost": st.column_config.NumberColumn(
                "Cost",
                width="small", 
                format="%.2f $",
                help="Coût de l'opération (temps × taux horaire)"
            ),
            "hourly_rate": st.column_config.NumberColumn(
                "Rate ($/h)",
                width="small",
                format="%.2f",
                help="Taux horaire du poste"
            ),
            "current_load_percent": st.column_config.ProgressColumn(
                "Load %",
                width="small",
                min_value=0,
                max_value=100,
                help="Charge actuelle du poste"
            ),
            "availability_status": st.column_config.SelectboxColumn(
                "Status",
                width="small",
                options=["DISPONIBLE", "CHARGE", "SATURE", "MAINTENANCE"],
                help="Statut de disponibilité"
            )
        }
        
        # Colonnes à afficher selon le mode
        if st.session_state.routing_editing_mode:
            display_columns = [
                "operation_seq", "operation_name", "work_center_name", 
                "duration_minutes", "hourly_rate", "operation_cost"
            ]
        else:
            display_columns = [
                "operation_seq", "operation_name", "work_center_name", 
                "duration_minutes", "current_load_percent", "availability_status"
            ]
        
        # Affichage tableau principal avec édition
        st.markdown(f"**⚙️ Opérations pour: {product_name}**")
        
        if st.session_state.routing_editing_mode:
            # Mode édition avec data_editor
            
            # Récupérer les postes de travail disponibles pour la sélection
            work_centers_df = routing_manager.get_available_work_centers()
            work_centers_options = work_centers_df['name'].tolist() if not work_centers_df.empty else []
            
            # Mise à jour de la configuration des colonnes pour l'édition
            column_config["work_center_name"] = st.column_config.SelectboxColumn(
                "Work Center",
                width="medium",
                options=work_centers_options,
                help="Sélectionnez le poste de travail"
            )
            
            edited_routing = st.data_editor(
                routing_df[display_columns],
                use_container_width=True,
                hide_index=True,
                column_config=column_config,
                num_rows="dynamic",
                key="routing_editor"
            )
            
            # Boutons de validation des modifications
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("✅ Valider Modifications", type="primary"):
                    # TODO: Implémenter sauvegarde des modifications
                    with st.spinner("💾 Sauvegarde en cours..."):
                        # Logic to save changes
                        pass
                    st.success("✅ Modifications sauvegardées!")
            
            with col2:
                if st.button("❌ Annuler"):
                    st.session_state.routing_editing_mode = False
                    st.rerun()
            
            with col3:
                if st.button("🗑️ Supprimer Sélectionnés"):
                    show_routing_delete_confirmation()
        
        else:
            # Mode consultation
            st.dataframe(
                routing_df[display_columns],
                use_container_width=True,
                hide_index=True,
                column_config=column_config
            )
        
        # Statistiques gamme détaillées
        show_routing_statistics(routing_df)
        
        # Analyse de charge des postes
        show_work_centers_load_analysis(routing_manager, routing_df)
        
        # Alertes et recommandations
        show_routing_alerts(routing_df)
    
    else:
        # Gamme vide - Interface de création
        show_empty_routing_interface(routing_manager, product_id, product_name)
    
    # Formulaires modaux
    if st.session_state.get('routing_show_add_form', False):
        show_add_operation_form(routing_manager, product_id)
    
    if st.session_state.get('routing_show_copy', False):
        show_copy_routing_interface(routing_manager, product_id)


def show_routing_planning_view(routing_manager: RoutingManager, product_id: int, product_name: str):
    """Vue planification de la gamme avec analyse des charges"""
    st.markdown("#### 📅 Planification de Production")
    
    # Récupération gamme
    routing_df = routing_manager.get_routing_for_product(product_id)
    
    if not routing_df.empty:
        
        # Paramètres de planification
        col1, col2, col3 = st.columns(3)
        
        with col1:
            production_quantity = st.number_input(
                "Quantité à produire:",
                min_value=1,
                value=1,
                help="Nombre d'unités à fabriquer"
            )
        
        with col2:
            start_date = st.date_input(
                "Date de début:",
                value=datetime.now().date(),
                help="Date de début de production"
            )
        
        with col3:
            working_hours_per_day = st.slider(
                "Heures/jour:",
                min_value=1,
                max_value=24,
                value=8,
                help="Heures de travail par jour"
            )
        
        # Calculs de planification
        total_time_per_unit = routing_df['duration_minutes'].sum()
        total_time_all_units = total_time_per_unit * production_quantity
        estimated_days = (total_time_all_units / 60) / working_hours_per_day
        
        # Métriques de planification
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Temps/Unité", format_duration(total_time_per_unit))
        
        with col2:
            st.metric("Temps Total", format_duration(total_time_all_units))
        
        with col3:
            st.metric("Durée Estimée", f"{estimated_days:.1f} jours")
        
        with col4:
            end_date = start_date + timedelta(days=int(estimated_days) + 1)
            st.metric("Date Fin Prévue", end_date.strftime('%Y-%m-%d'))
        
        # Planning détaillé par opération
        st.markdown("##### 📋 Planning Détaillé par Opération")
        
        planning_data = []
        current_date = datetime.combine(start_date, datetime.min.time())
        
        for _, operation in routing_df.iterrows():
            op_duration_total = operation['duration_minutes'] * production_quantity
            op_duration_hours = op_duration_total / 60
            op_duration_days = op_duration_hours / working_hours_per_day
            
            op_end_date = current_date + timedelta(days=op_duration_days)
            
            planning_item = {
                'Séquence': operation['operation_seq'],
                'Opération': operation['operation_name'],
                'Poste': operation['work_center_name'],
                'Début': current_date.strftime('%Y-%m-%d %H:%M'),
                'Fin': op_end_date.strftime('%Y-%m-%d %H:%M'),
                'Durée (h)': f"{op_duration_hours:.1f}",
                'Charge Poste': f"{operation.get('current_load_percent', 0):.0f}%"
            }
            
            planning_data.append(planning_item)
            current_date = op_end_date
        
        planning_df = pd.DataFrame(planning_data)
        st.dataframe(planning_df, use_container_width=True, hide_index=True)
        
        # Graphique de Gantt simplifié
        show_simplified_gantt_chart(planning_data)
        
        # Analyse des conflits de ressources
        show_resource_conflicts_analysis(routing_manager, routing_df, production_quantity)
    
    else:
        st.warning("🔧 Aucune gamme définie pour ce produit.")


def show_routing_cost_analysis_view(routing_manager: RoutingManager, product_id: int):
    """Vue analyse des coûts de main d'œuvre"""
    st.markdown("#### 💰 Analyse des Coûts de Main d'Œuvre")
    
    # Calculs coûts détaillés
    routing_costs = routing_manager.calculate_routing_cost(product_id)
    
    if routing_costs.get('total_cost', 0) > 0:
        
        # Métriques principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Coût Total", format_currency(routing_costs['total_cost']))
        
        with col2:
            st.metric("Temps Total", f"{routing_costs['total_time_hours']:.1f} h")
        
        with col3:
            st.metric("Taux Moyen", format_currency(routing_costs['average_hourly_rate']) + "/h")
        
        with col4:
            st.metric("Opérations", routing_costs['operations_count'])
        
        # Détail des coûts par opération
        operations_detail = routing_costs.get('operations_detail', [])
        
        if operations_detail:
            # Graphique de répartition
            st.markdown("##### 📊 Répartition des Coûts par Opération")
            
            # Préparer données pour graphique
            chart_data = []
            for op in operations_detail[:10]:  # Top 10
                chart_data.append({
                    'Opération': f"Op {op['sequence']}",
                    'Coût': op['total_cost']
                })
            
            if chart_data:
                chart_df = pd.DataFrame(chart_data)
                st.bar_chart(chart_df.set_index('Opération')['Coût'], use_container_width=True)
            
            # Tableau détaillé des coûts
            st.markdown("##### 📋 Détail des Coûts par Opération")
            
            cost_detail_df = pd.DataFrame(operations_detail)
            
            # Configuration colonnes
            cost_column_config = {
                "sequence": st.column_config.NumberColumn("Séq.", width="small"),
                "operation": st.column_config.TextColumn("Opération", width="large"),
                "work_center": st.column_config.TextColumn("Poste", width="medium"),
                "unit_time": st.column_config.NumberColumn("Temps (min)", format="%.0f", width="small"),
                "hourly_rate": st.column_config.NumberColumn("Taux ($/h)", format="%.2f", width="small"),
                "total_cost": st.column_config.NumberColumn("Coût Total", format="%.2f $", width="small")
            }
            
            st.dataframe(
                cost_detail_df[['sequence', 'operation', 'work_center', 'unit_time', 'hourly_rate', 'total_cost']],
                use_container_width=True,
                hide_index=True,
                column_config=cost_column_config
            )
            
            # Analyse des coûts
            show_routing_cost_analysis(operations_detail, routing_costs['total_cost'])
        
        # Export analyse coûts
        if st.button("📊 Exporter Analyse Coûts Main d'Œuvre"):
            export_routing_cost_analysis(product_id, routing_costs)
    
    else:
        st.warning("💰 Aucune donnée de coût disponible pour cette gamme.")


def show_routing_statistics(routing_df: pd.DataFrame):
    """Affiche les statistiques détaillées de la gamme"""
    st.markdown("#### 📊 Statistiques Gamme")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_operations = len(routing_df)
        st.metric("Total Opérations", total_operations)
    
    with col2:
        total_duration = routing_df['duration_minutes'].sum()
        st.metric("Temps Total", format_duration(total_duration))
    
    with col3:
        avg_duration = routing_df['duration_minutes'].mean()
        st.metric("Temps Moy./Op", format_duration(avg_duration))
    
    with col4:
        unique_work_centers = routing_df['work_center_name'].nunique()
        st.metric("Postes Utilisés", unique_work_centers)
    
    # Analyse des postes de travail
    if not routing_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🏭 Répartition par Poste:**")
            wc_counts = routing_df['work_center_name'].value_counts()
            for wc, count in wc_counts.items():
                percentage = (count / total_operations) * 100
                st.markdown(f"• {wc}: {count} op. ({percentage:.1f}%)")
        
        with col2:
            st.markdown("**⏱️ Analyse des Temps:**")
            max_duration = routing_df['duration_minutes'].max()
            min_duration = routing_df['duration_minutes'].min()
            std_duration = routing_df['duration_minutes'].std()
            
            st.markdown(f"• Durée max: {format_duration(max_duration)}")
            st.markdown(f"• Durée min: {format_duration(min_duration)}")
            st.markdown(f"• Écart-type: {format_duration(std_duration)}")


def show_work_centers_load_analysis(routing_manager: RoutingManager, routing_df: pd.DataFrame):
    """Analyse de charge des postes de travail"""
    st.markdown("#### 🏭 Analyse de Charge des Postes")
    
    if not routing_df.empty:
        # Récupérer tous les postes disponibles
        all_work_centers = routing_manager.get_available_work_centers()
        
        # Analyser les postes utilisés dans cette gamme
        used_work_centers = routing_df['work_center_name'].unique()
        
        load_analysis = []
        for wc_name in used_work_centers:
            if pd.notna(wc_name):
                # Filtrer les opérations pour ce poste
                wc_operations = routing_df[routing_df['work_center_name'] == wc_name]
                
                total_time_wc = wc_operations['duration_minutes'].sum()
                operations_count = len(wc_operations)
                current_load = wc_operations['current_load_percent'].mean() if 'current_load_percent' in wc_operations.columns else 0
                
                # Déterminer le statut de charge
                if current_load < 50:
                    load_status = "🟢 Disponible"
                elif current_load < 80:
                    load_status = "🟡 Modéré"
                elif current_load < 95:
                    load_status = "🟠 Chargé"
                else:
                    load_status = "🔴 Saturé"
                
                load_analysis.append({
                    'Poste': wc_name,
                    'Opérations': operations_count,
                    'Temps Total': format_duration(total_time_wc),
                    'Charge Actuelle': f"{current_load:.0f}%",
                    'Statut': load_status
                })
        
        if load_analysis:
            load_df = pd.DataFrame(load_analysis)
            st.dataframe(load_df, use_container_width=True, hide_index=True)
            
            # Recommandations de charge
            high_load_count = len([item for item in load_analysis if "🔴" in item['Statut'] or "🟠" in item['Statut']])
            
            if high_load_count > 0:
                st.warning(f"⚠️ {high_load_count} poste(s) en forte charge - Planification recommandée")
            else:
                st.success("✅ Tous les postes sont disponibles")


def show_routing_alerts(routing_df: pd.DataFrame):
    """Affiche les alertes et recommandations gamme"""
    if routing_df.empty:
        return
    
    alerts = []
    
    # Vérification séquencement
    sequences = routing_df['operation_seq'].sort_values()
    gaps = []
    for i in range(len(sequences) - 1):
        if sequences.iloc[i+1] - sequences.iloc[i] > 1:
            gaps.append(f"{sequences.iloc[i]}-{sequences.iloc[i+1]}")
    
    if gaps:
        alerts.append(f"📋 Trous dans la séquence détectés: {', '.join(gaps)}")
    
    # Vérification durées
    long_operations = routing_df[routing_df['duration_minutes'] > 480]  # > 8h
    if not long_operations.empty:
        alerts.append(f"⏱️ {len(long_operations)} opération(s) très longue(s) (>8h)")
    
    # Vérification postes surchargés
    if 'current_load_percent' in routing_df.columns:
        overloaded = routing_df[routing_df['current_load_percent'] > 90]
        if not overloaded.empty:
            alerts.append(f"🔴 {len(overloaded)} poste(s) surchargé(s) (>90%)")
    
    # Vérification coûts manquants
    if 'hourly_rate' in routing_df.columns:
        no_rate = routing_df[routing_df['hourly_rate'] <= 0]
        if not no_rate.empty:
            alerts.append(f"💰 {len(no_rate)} opération(s) sans taux horaire défini")
    
    # Affichage des alertes
    if alerts:
        st.markdown("#### ⚠️ Alertes Gamme")
        for alert in alerts:
            st.warning(alert)
    else:
        st.success("✅ Aucune alerte détectée - Gamme optimale")


def show_empty_routing_interface(routing_manager: RoutingManager, product_id: int, product_name: str):
    """Interface pour gamme vide"""
    st.markdown("#### ⚙️ Gamme Vide - Configuration Initiale")
    
    # Message d'aide
    st.info(f"🎯 **Produit sélectionné:** {product_name}")
    st.markdown("""
    **⚙️ Cette gamme de fabrication est vide. Vous pouvez:**
    - ➕ Ajouter des opérations manuellement
    - 📋 Copier depuis un autre produit
    - 🏭 Utiliser un template standard
    - 📄 Importer depuis un fichier Excel/CSV
    """)
    
    # Options de création rapide
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Ajouter Première Opération", use_container_width=True):
            st.session_state.routing_show_add_form = True
    
    with col2:
        if st.button("📋 Copier Gamme Existante", use_container_width=True):
            st.session_state.routing_show_copy = True
    
    with col3:
        if st.button("🏭 Template Standard", use_container_width=True):
            show_routing_template_interface(routing_manager, product_id)
    
    # Templates de gamme suggérés
    with st.expander("💡 Templates de Gammes Suggérés"):
        st.markdown("""
        **🏗️ Gammes de fabrication typiques:**
        
        **Pour Pièce Mécanique:**
        - 1001: Découpe matière première
        - 1002: Usinage première face
        - 1003: Retournement pièce
        - 1004: Usinage deuxième face
        - 1005: Contrôle qualité
        
        **Pour Assemblage Soudé:**
        - 1001: Préparation composants
        - 1002: Assemblage à blanc
        - 1003: Pointage soudure
        - 1004: Soudage final
        - 1005: Meulage finition
        - 1006: Contrôle soudure
        
        **Numérotation recommandée:**
        - 1001-1999: Opérations principales
        - 2001-2999: Opérations secondaires  
        - 3001-3999: Contrôles qualité
        - 4001-4999: Finitions/traitements
        """)


def show_add_operation_form(routing_manager: RoutingManager, product_id: int):
    """Formulaire d'ajout d'opération"""
    st.markdown("#### ➕ Ajouter une Opération")
    
    with st.form("add_operation_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Suggestion automatique du prochain numéro de séquence
            next_sequence = routing_manager.get_next_sequence_number(product_id)
            
            sequence_number = st.number_input(
                "Numéro de séquence *",
                min_value=1,
                max_value=9999,
                value=next_sequence,
                step=1,
                help=f"Numéro de séquence suggéré: {next_sequence}"
            )
            
            operation_description = st.text_input(
                "Description opération *",
                placeholder="Ex: Montage-soudé, Soudage manuel SMAW...",
                help="Description détaillée de l'opération"
            )
            
            duration_minutes = st.number_input(
                "Durée (minutes) *",
                min_value=1,
                value=60,
                step=1,
                help="Durée estimée de l'opération en minutes"
            )
        
        with col2:
            # Récupération des postes de travail disponibles
            work_centers_df = routing_manager.get_available_work_centers()
            
            if not work_centers_df.empty:
                wc_options = {}
                for _, wc in work_centers_df.iterrows():
                    display_name = f"{wc['name']} ({wc['departement']}) - {format_currency(wc['hourly_rate'])}/h"
                    wc_options[display_name] = {
                        'id': wc['id'],
                        'name': wc['name'],
                        'rate': wc['hourly_rate'],
                        'load': wc.get('current_load', 0)
                    }
                
                selected_wc = st.selectbox(
                    "Poste de travail *:",
                    options=list(wc_options.keys()),
                    help="Choisissez le poste de travail pour cette opération"
                )
                
                # Affichage des informations du poste sélectionné
                if selected_wc:
                    wc_info = wc_options[selected_wc]
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Taux Horaire", format_currency(wc_info['rate']) + "/h")
                    with col_b:
                        load_color = "🟢" if wc_info['load'] < 50 else "🟡" if wc_info['load'] < 80 else "🔴"
                        st.metric("Charge Actuelle", f"{load_color} {wc_info['load']:.0f}%")
            else:
                st.error("❌ Aucun poste de travail disponible")
                selected_wc = None
            
            notes = st.text_area(
                "Instructions/Notes",
                placeholder="Instructions spécifiques, consignes de sécurité...",
                help="Informations complémentaires pour l'opérateur"
            )
        
        # Options avancées
        with st.expander("⚙️ Options Avancées"):
            col1, col2 = st.columns(2)
            
            with col1:
                is_critical_path = st.checkbox(
                    "🎯 Opération critique",
                    help="Opération sur le chemin critique"
                )
                
                requires_qualification = st.checkbox(
                    "🏆 Qualification requise",
                    help="Opérateur qualifié nécessaire"
                )
            
            with col2:
                setup_time = st.number_input(
                    "Temps préparation (min)",
                    min_value=0,
                    value=0,
                    help="Temps de préparation/réglage"
                )
                
                parallel_operations = st.text_input(
                    "Opérations parallèles",
                    placeholder="Ex: 1002, 1003",
                    help="Numéros des opérations pouvant être faites en parallèle"
                )
        
        # Aperçu de l'opération
        if operation_description and selected_wc and duration_minutes > 0:
            wc_info = wc_options[selected_wc]
            estimated_cost = (duration_minutes / 60) * wc_info['rate']
            
            st.markdown("**👁️ Aperçu de l'Opération:**")
            st.markdown(f"• **{sequence_number}**: {operation_description}")
            st.markdown(f"• **Poste**: {wc_info['name']} ({format_duration(duration_minutes)})")
            st.markdown(f"• **Coût estimé**: {format_currency(estimated_cost)}")
        
        # Boutons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            submitted = st.form_submit_button("✅ Ajouter Opération", type="primary")
        
        with col2:
            if st.form_submit_button("👁️ Aperçu"):
                if all([sequence_number, operation_description, selected_wc, duration_minutes]):
                    st.info(f"Opération {sequence_number}: {operation_description} ({duration_minutes} min)")
        
        with col3:
            if st.form_submit_button("❌ Annuler"):
                st.session_state.routing_show_add_form = False
                st.rerun()
        
        # Traitement soumission
        if submitted:
            if all([sequence_number, operation_description, selected_wc, duration_minutes > 0]):
                
                # Vérifier que la séquence n'existe pas déjà
                if routing_manager.sequence_exists(product_id, sequence_number):
                    st.error(f"❌ La séquence {sequence_number} existe déjà. Choisissez un autre numéro.")
                else:
                    wc_info = wc_options[selected_wc]
                    
                    operation_data = {
                        'product_id': product_id,
                        'work_center_id': wc_info['id'],
                        'sequence_number': sequence_number,
                        'description': operation_description,
                        'duration': duration_minutes,
                        'work_center_name': wc_info['name'],
                        'notes': notes
                    }
                    
                    with st.spinner("➕ Ajout de l'opération..."):
                        success = routing_manager.create_operation(operation_data)
                    
                    if success:
                        st.success(f"✅ Opération {sequence_number} '{operation_description}' ajoutée avec succès!")
                        st.session_state.routing_show_add_form = False
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de l'ajout de l'opération.")
            else:
                st.error("❌ Veuillez remplir tous les champs obligatoires.")


def show_copy_routing_interface(routing_manager: RoutingManager, target_product_id: int):
    """Interface de copie de gamme"""
    st.markdown("#### 📋 Copier Gamme Existante")
    
    # Récupérer tous les produits ayant une gamme
    db = ERPDatabase()
    product_manager = ProductManager(db)
    all_products = product_manager.get_all_products()
    
    if not all_products.empty:
        # Filtrer les produits ayant des opérations
        products_with_routing = []
        for _, product in all_products.iterrows():
            if product['id'] != target_product_id:  # Exclure le produit cible
                routing_df = routing_manager.get_routing_for_product(product['id'])
                if not routing_df.empty:
                    products_with_routing.append({
                        'id': product['id'],
                        'name': product['product_name'],
                        'operations_count': len(routing_df),
                        'total_time': routing_df['duration_minutes'].sum()
                    })
        
        if products_with_routing:
            st.markdown("**Sélectionnez le produit source:**")
            
            for product_info in products_with_routing:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**{product_info['name']}**")
                
                with col2:
                    st.metric("Opérations", product_info['operations_count'])
                
                with col3:
                    st.metric("Temps Total", format_duration(product_info['total_time']))
                
                with col4:
                    if st.button(f"📋 Copier", key=f"copy_{product_info['id']}"):
                        with st.spinner("📋 Copie en cours..."):
                            success = routing_manager.copy_routing_from_product(
                                product_info['id'], 
                                target_product_id
                            )
                        
                        if success:
                            st.success(f"✅ Gamme copiée depuis '{product_info['name']}'!")
                            st.session_state.routing_show_copy = False
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Erreur lors de la copie de la gamme.")
                
                st.markdown("---")
        
        else:
            st.warning("📋 Aucun autre produit avec gamme définie trouvé.")
    
    if st.button("❌ Fermer"):
        st.session_state.routing_show_copy = False
        st.rerun()


def show_routing_template_interface(routing_manager: RoutingManager, product_id: int):
    """Interface de templates de gamme"""
    st.markdown("#### 🏭 Templates de Gamme Standard")
    
    templates = {
        "Pièce Mécanique": [
            {"seq": 1001, "desc": "Découpe matière première", "duration": 30, "wc": "Découpe Plasma"},
            {"seq": 1002, "desc": "Usinage première face", "duration": 120, "wc": "Centre Usinage"},
            {"seq": 1003, "desc": "Retournement pièce", "duration": 15, "wc": "Poste Manuel"},
            {"seq": 1004, "desc": "Usinage deuxième face", "duration": 90, "wc": "Centre Usinage"},
            {"seq": 1005, "desc": "Contrôle dimensionnel", "duration": 30, "wc": "Métrologie"}
        ],
        "Assemblage Soudé": [
            {"seq": 1001, "desc": "Préparation composants", "duration": 45, "wc": "Préparation"},
            {"seq": 1002, "desc": "Assemblage à blanc", "duration": 60, "wc": "Assemblage"},
            {"seq": 1003, "desc": "Pointage soudure", "duration": 30, "wc": "Soudage MIG"},
            {"seq": 1004, "desc": "Soudage final", "duration": 120, "wc": "Soudage MIG"},
            {"seq": 1005, "desc": "Meulage finition", "duration": 45, "wc": "Finition"},
            {"seq": 1006, "desc": "Contrôle soudure", "duration": 30, "wc": "Contrôle"}
        ],
        "Kit d'Assemblage": [
            {"seq": 1001, "desc": "Préparation composants", "duration": 20, "wc": "Préparation"},
            {"seq": 1002, "desc": "Conditionnement", "duration": 15, "wc": "Conditionnement"},
            {"seq": 1003, "desc": "Étiquetage", "duration": 10, "wc": "Étiquetage"},
            {"seq": 1004, "desc": "Contrôle qualité", "duration": 15, "wc": "Contrôle"}
        ]
    }
    
    selected_template = st.selectbox(
        "Choisissez un template:",
        options=list(templates.keys()),
        help="Sélectionnez le type de gamme à appliquer"
    )
    
    if selected_template:
        template_ops = templates[selected_template]
        
        st.markdown(f"**📋 Aperçu Template: {selected_template}**")
        
        template_df = pd.DataFrame(template_ops)
        template_df.columns = ['Séquence', 'Description', 'Durée (min)', 'Poste Suggéré']
        
        st.dataframe(template_df, use_container_width=True, hide_index=True)
        
        total_time = sum(op['duration'] for op in template_ops)
        st.info(f"⏱️ Temps total template: {format_duration(total_time)}")
        
        if st.button("🏭 Appliquer ce Template", type="primary"):
            st.info("🚧 Application de template en développement...")


def show_routing_export_options(routing_df: pd.DataFrame, product_name: str):
    """Options d'export de la gamme"""
    st.markdown("#### 📊 Options d'Export Gamme")
    
    export_formats = ["CSV", "Excel", "PDF", "JSON"]
    selected_format = st.selectbox("Format d'export:", export_formats)
    
    if selected_format == "CSV":
        csv_data = routing_df.to_csv(index=False)
        st.download_button(
            label="💾 Télécharger CSV",
            data=csv_data,
            file_name=f"Gamme_{product_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    elif selected_format == "JSON":
        json_data = routing_df.to_json(orient='records', indent=2)
        st.download_button(
            label="💾 Télécharger JSON", 
            data=json_data,
            file_name=f"Gamme_{product_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    else:
        st.info(f"🚧 Export {selected_format} en développement...")


def show_simplified_gantt_chart(planning_data: List[Dict]):
    """Affichage d'un diagramme de Gantt simplifié"""
    st.markdown("##### 📊 Diagramme de Gantt Simplifié")
    
    # Créer un graphique simple avec les données de planning
    gantt_data = []
    for item in planning_data:
        gantt_data.append({
            'Opération': f"Op {item['Séquence']}",
            'Début': datetime.strptime(item['Début'], '%Y-%m-%d %H:%M'),
            'Fin': datetime.strptime(item['Fin'], '%Y-%m-%d %H:%M')
        })
    
    # Affichage sous forme de tableau pour simulation
    st.dataframe(
        pd.DataFrame(planning_data)[['Séquence', 'Opération', 'Début', 'Fin', 'Durée (h)']],
        use_container_width=True,
        hide_index=True
    )


def show_resource_conflicts_analysis(routing_manager: RoutingManager, routing_df: pd.DataFrame, quantity: int):
    """Analyse des conflits de ressources"""
    st.markdown("##### ⚠️ Analyse des Conflits de Ressources")
    
    # Analyser les postes utilisés multiple fois
    wc_usage = routing_df['work_center_name'].value_counts()
    conflicts = wc_usage[wc_usage > 1]
    
    if not conflicts.empty:
        st.warning(f"⚠️ {len(conflicts)} poste(s) utilisé(s) plusieurs fois:")
        for wc, count in conflicts.items():
            st.markdown(f"• **{wc}**: {count} opérations")
    else:
        st.success("✅ Aucun conflit de ressources détecté")


def show_routing_cost_analysis(operations_detail: List[Dict], total_cost: float):
    """Analyse détaillée des coûts de gamme"""
    st.markdown("##### 🎯 Analyse des Coûts")
    
    # Top 5 opérations les plus chères
    sorted_ops = sorted(operations_detail, key=lambda x: x['total_cost'], reverse=True)
    top_expensive = sorted_ops[:5]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔴 Top 5 Opérations Plus Chères:**")
        for i, op in enumerate(top_expensive, 1):
            percentage = (op['total_cost'] / total_cost) * 100
            st.markdown(f"{i}. Op {op['sequence']} - {format_currency(op['total_cost'])} ({percentage:.1f}%)")
    
    with col2:
        st.markdown("**📊 Recommandations:**")
        
        # Analyse automatique
        if total_cost > 500:
            st.info("💡 Coût main d'œuvre élevé - Optimisation recommandée")
        
        high_cost_ops = [op for op in operations_detail if op['total_cost'] > total_cost * 0.3]
        if high_cost_ops:
            st.warning("⚠️ Opération(s) à coût élevé - Vérifiez la durée")
        
        high_rate_ops = [op for op in operations_detail if op['hourly_rate'] > 100]
        if high_rate_ops:
            st.info("🏆 Poste(s) à taux élevé - Qualification spécialisée")


def export_routing_cost_analysis(product_id: int, routing_costs: Dict):
    """Export de l'analyse des coûts de gamme"""
    cost_report = {
        'product_id': product_id,
        'total_cost': routing_costs['total_cost'],
        'total_time_hours': routing_costs['total_time_hours'],
        'average_hourly_rate': routing_costs['average_hourly_rate'],
        'operations_count': routing_costs['operations_count'],
        'operations_detail': routing_costs.get('operations_detail', []),
        'analysis_date': datetime.now().isoformat()
    }
    
    import json
    report_json = json.dumps(cost_report, ensure_ascii=False, indent=2)
    
    st.download_button(
        label="💾 Télécharger Rapport Coûts Main d'Œuvre",
        data=report_json,
        file_name=f"analyse_couts_gamme_{product_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )


def show_routing_delete_confirmation():
    """Confirmation de suppression d'opérations"""
    st.markdown("#### 🗑️ Suppression d'Opérations")
    st.info("🚧 Fonctionnalité de suppression en développement...")


def show_work_orders_tab():
    """Onglet 4: Bons de Travail - Workflow complet avec explosion BOM"""
    st.markdown("### 🧾 Bons de Travail")
    
    # Initialisation gestionnaires
    db = ERPDatabase()
    product_manager = ProductManager(db)
    bom_manager = BOMManager(db)
    routing_manager = RoutingManager(db)
    work_order_manager = WorkOrderManager(db, bom_manager, routing_manager)
    
    # Métriques rapides en en-tête
    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        
        try:
            all_work_orders = work_order_manager.get_all_work_orders()
            
            with col1:
                total_work_orders = len(all_work_orders)
                st.metric("Total BT", total_work_orders)
            
            with col2:
                if not all_work_orders.empty:
                    active_bt = len(all_work_orders[all_work_orders['status'].isin(['VALIDE', 'EN_COURS'])])
                else:
                    active_bt = 0
                st.metric("BT Actifs", active_bt)
            
            with col3:
                if not all_work_orders.empty:
                    completed_bt = len(all_work_orders[all_work_orders['status'] == 'TERMINE'])
                else:
                    completed_bt = 0
                st.metric("BT Terminés", completed_bt)
            
            with col4:
                if not all_work_orders.empty and 'total_cost' in all_work_orders.columns:
                    total_value = all_work_orders['total_cost'].sum()
                else:
                    total_value = 0
                st.metric("Valeur Total", format_currency(total_value))
                
        except Exception as e:
            st.error(f"Erreur calcul métriques BT: {e}")
    
    st.markdown("---")
    
    # Sous-onglets pour organisation
    sub_tabs = st.tabs([
        "🎯 Nouveau BT", 
        "📋 BT Existants", 
        "📊 Suivi Production",
        "🔍 Analyse Avancement"
    ])
    
    with sub_tabs[0]:
        show_new_work_order_tab(work_order_manager, product_manager, bom_manager, routing_manager)
    
    with sub_tabs[1]:
        show_existing_work_orders_tab(work_order_manager)
    
    with sub_tabs[2]:
        show_production_tracking_tab(work_order_manager)
    
    with sub_tabs[3]:
        show_progress_analysis_tab(work_order_manager)


def show_new_work_order_tab(work_order_manager: WorkOrderManager, product_manager: ProductManager, 
                           bom_manager: BOMManager, routing_manager: RoutingManager):
    """Sous-onglet: Créer un nouveau bon de travail - Workflow complet"""
    st.markdown("#### 🎯 Créer un Nouveau Bon de Travail")
    
    # Workflow: Produit → BOM → Gamme → BT
    products_df = product_manager.get_all_products()
    
    if not products_df.empty:
        
        # Section 1: Sélection et paramètres du produit
        st.markdown("##### 📦 1. Sélection du Produit")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            product_options = {f"{row['product_name']} (ID: {row['id']})": row['id'] 
                              for _, row in products_df.iterrows()}
            
            selected_product = st.selectbox(
                "Produit à fabriquer:",
                options=list(product_options.keys()),
                help="Sélectionnez le produit pour lequel créer un bon de travail",
                key="work_order_product_selector"
            )
        
        with col2:
            if st.button("🔄 Actualiser Produits"):
                st.rerun()
        
        if selected_product:
            product_id = product_options[selected_product]
            selected_product_info = products_df[products_df['id'] == product_id].iloc[0]
            
            # Paramètres de production
            col1, col2, col3 = st.columns(3)
            
            with col1:
                quantity = st.number_input(
                    "Quantité à produire:",
                    min_value=1,
                    value=1,
                    help="Nombre d'unités à fabriquer"
                )
            
            with col2:
                priority = st.selectbox(
                    "Priorité:",
                    options=list(WORK_ORDER_PRIORITIES.keys()),
                    format_func=lambda x: WORK_ORDER_PRIORITIES[x],
                    help="Niveau de priorité du bon de travail"
                )
            
            with col3:
                due_date = st.date_input(
                    "Date d'échéance:",
                    value=datetime.now().date() + timedelta(days=7),
                    help="Date d'échéance souhaitée"
                )
            
            st.markdown("---")
            
            # Section 2: Prévisualisation BOM et Gamme
            st.markdown("##### 🔍 2. Analyse Produit Sélectionné")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📋 Nomenclature (BOM):**")
                bom_df = bom_manager.get_bom_for_product(product_id)
                
                if not bom_df.empty:
                    # Affichage BOM avec explosion pour quantité
                    explosion = bom_manager.explode_bom(product_id, parent_quantity=quantity)
                    
                    if explosion:
                        # Résumé BOM
                        bom_summary = []
                        for item in explosion[:5]:  # Top 5 pour aperçu
                            bom_summary.append({
                                'Composant': item['component_name'][:30] + "..." if len(item['component_name']) > 30 else item['component_name'],
                                'Qté': f"{item['quantity_total']:.2f}",
                                'Unité': item['unit'],
                                'Coût': format_currency(item['total_cost'])
                            })
                        
                        bom_summary_df = pd.DataFrame(bom_summary)
                        st.dataframe(bom_summary_df, use_container_width=True, hide_index=True)
                        
                        if len(explosion) > 5:
                            st.info(f"... et {len(explosion) - 5} autre(s) composant(s)")
                        
                        # Calculs BOM
                        total_bom_cost = sum(item['total_cost'] for item in explosion)
                        st.metric("Coût Matières Total", format_currency(total_bom_cost))
                    else:
                        st.warning("Explosion BOM impossible")
                else:
                    st.warning("⚠️ Aucune BOM définie")
                    st.info("Créez d'abord une nomenclature dans l'onglet 'Nomenclatures (BOM)'")
            
            with col2:
                st.markdown("**⚙️ Gamme de Fabrication:**")
                routing_df = routing_manager.get_routing_for_product(product_id)
                
                if not routing_df.empty:
                    # Affichage gamme avec calculs pour quantité
                    routing_summary = []
                    for _, operation in routing_df.iterrows():
                        total_time = operation['duration_minutes'] * quantity
                        operation_cost = (total_time / 60) * operation.get('hourly_rate', 0)
                        
                        routing_summary.append({
                            'Opération': f"{operation['operation_seq']}: {operation['operation_name'][:25]}...",
                            'Poste': operation['work_center_name'][:20] if pd.notna(operation['work_center_name']) else "N/A",
                            'Temps': format_duration(total_time),
                            'Coût': format_currency(operation_cost)
                        })
                    
                    routing_summary_df = pd.DataFrame(routing_summary)
                    st.dataframe(routing_summary_df, use_container_width=True, hide_index=True)
                    
                    # Calculs gamme
                    total_routing_time = routing_df['duration_minutes'].sum() * quantity
                    routing_costs = routing_manager.calculate_routing_cost(product_id, quantity)
                    total_routing_cost = routing_costs.get('total_cost', 0)
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Temps Total", format_duration(total_routing_time))
                    with col_b:
                        st.metric("Coût M.O. Total", format_currency(total_routing_cost))
                else:
                    st.warning("⚠️ Aucune gamme définie")
                    st.info("Créez d'abord une gamme dans l'onglet 'Gammes Fabrication'")
            
            # Section 3: Validation et création
            st.markdown("---")
            st.markdown("##### ✅ 3. Validation et Création du BT")
            
            # Vérifications préalables
            has_bom = not bom_df.empty
            has_routing = not routing_df.empty
            
            if has_bom and has_routing:
                validation_status = "🟢 Prêt pour création"
                can_create = True
            elif has_bom or has_routing:
                validation_status = "🟡 Création possible (partielle)"
                can_create = True
            else:
                validation_status = "🔴 Impossible - BOM et Gamme manquantes"
                can_create = False
            
            st.info(f"**Statut de validation:** {validation_status}")
            
            if can_create:
                # Résumé final avant création
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if has_bom:
                        total_bom_cost = sum(item['total_cost'] for item in explosion) if 'explosion' in locals() else 0
                    else:
                        total_bom_cost = 0
                    st.metric("Coût Matières", format_currency(total_bom_cost))
                
                with col2:
                    if has_routing:
                        total_routing_cost = routing_costs.get('total_cost', 0) if 'routing_costs' in locals() else 0
                    else:
                        total_routing_cost = 0
                    st.metric("Coût Main d'Œuvre", format_currency(total_routing_cost))
                
                with col3:
                    total_cost = total_bom_cost + total_routing_cost
                    st.metric("Coût Total Estimé", format_currency(total_cost))
                
                # Options avancées
                with st.expander("⚙️ Options Avancées"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        auto_reserve_resources = st.checkbox(
                            "🔒 Réserver automatiquement les ressources",
                            value=True,
                            help="Réserve automatiquement les postes de travail"
                        )
                        
                        generate_material_requisition = st.checkbox(
                            "📋 Générer demande matières",
                            value=True,
                            help="Crée automatiquement les demandes de matières"
                        )
                    
                    with col2:
                        assign_employees = st.checkbox(
                            "👥 Assigner employés automatiquement",
                            value=False,
                            help="Assigne automatiquement les employés qualifiés"
                        )
                        
                        send_notifications = st.checkbox(
                            "📧 Envoyer notifications",
                            value=True,
                            help="Notifie les responsables de la création du BT"
                        )
                
                # Notes et commentaires
                notes = st.text_area(
                    "Notes du bon de travail:",
                    placeholder="Instructions spéciales, commentaires, contraintes particulières...",
                    help="Informations complémentaires pour l'équipe de production"
                )
                
                # Bouton de création
                st.markdown("---")
                
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col2:
                    if st.button(
                        f"🎯 CRÉER BON DE TRAVAIL - {quantity} × {selected_product_info['product_name']}",
                        type="primary",
                        use_container_width=True
                    ):
                        # Création du bon de travail
                        work_order_data = {
                            'priority': priority,
                            'due_date': due_date.isoformat(),
                            'created_by': 'Production Manager',  # TODO: Récupérer utilisateur actuel
                            'notes': notes,
                            'auto_reserve_resources': auto_reserve_resources,
                            'generate_material_requisition': generate_material_requisition,
                            'assign_employees': assign_employees,
                            'send_notifications': send_notifications
                        }
                        
                        with st.spinner("🔄 Création du bon de travail en cours..."):
                            work_order_id = work_order_manager.create_work_order(
                                product_id, 
                                quantity, 
                                work_order_data
                            )
                        
                        if work_order_id:
                            st.success(f"✅ Bon de travail créé avec succès!")
                            st.balloons()
                            
                            # Affichage du BT créé
                            created_bt = work_order_manager.get_work_order_by_id(work_order_id)
                            if created_bt:
                                st.info(f"📋 **Numéro BT:** {created_bt['work_order_number']}")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("👁️ Voir le BT créé"):
                                        show_work_order_details(created_bt, work_order_manager)
                                
                                with col2:
                                    if st.button("🔄 Créer un autre BT"):
                                        st.rerun()
                            
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("❌ Erreur lors de la création du bon de travail.")
            
            else:
                st.error("❌ Impossible de créer un bon de travail sans BOM ni gamme.")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📋 Créer BOM"):
                        st.info("💡 Utilisez l'onglet 'Nomenclatures (BOM)' pour créer une BOM")
                
                with col2:
                    if st.button("⚙️ Créer Gamme"):
                        st.info("💡 Utilisez l'onglet 'Gammes Fabrication' pour créer une gamme")
    
    else:
        st.warning("📦 Aucun produit disponible pour créer des bons de travail.")
        st.info("💡 Créez d'abord des produits dans l'onglet **📦 Produits**")


def show_existing_work_orders_tab(work_order_manager: WorkOrderManager):
    """Sous-onglet: Bons de travail existants avec gestion avancée"""
    st.markdown("#### 📋 Bons de Travail Existants")
    
    # Filtres et recherche
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox(
            "Filtrer par statut:",
            options=["Tous"] + list(WORK_ORDER_STATUSES.keys()),
            format_func=lambda x: WORK_ORDER_STATUSES.get(x, x) if x != "Tous" else x
        )
    
    with col2:
        priority_filter = st.selectbox(
            "Filtrer par priorité:",
            options=["Toutes"] + list(WORK_ORDER_PRIORITIES.keys()),
            format_func=lambda x: WORK_ORDER_PRIORITIES.get(x, x) if x != "Toutes" else x
        )
    
    with col3:
        date_filter = st.selectbox(
            "Période:",
            options=["Toutes", "Aujourd'hui", "Cette semaine", "Ce mois", "Personnalisée"]
        )
    
    with col4:
        search_term = st.text_input(
            "🔍 Rechercher:",
            placeholder="N° BT, produit...",
            help="Recherche dans numéro BT et nom produit"
        )
    
    # Récupération des BT avec filtres
    filters = {}
    
    if status_filter != "Tous":
        filters['status'] = status_filter
    
    if date_filter == "Aujourd'hui":
        filters['date_from'] = datetime.now().date()
        filters['date_to'] = datetime.now().date()
    elif date_filter == "Cette semaine":
        filters['date_from'] = datetime.now().date() - timedelta(days=7)
    elif date_filter == "Ce mois":
        filters['date_from'] = datetime.now().date() - timedelta(days=30)
    elif date_filter == "Personnalisée":
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input("Date début:", value=datetime.now().date() - timedelta(days=30))
        with col2:
            date_to = st.date_input("Date fin:", value=datetime.now().date())
        
        filters['date_from'] = date_from
        filters['date_to'] = date_to
    
    try:
        work_orders_df = work_order_manager.get_all_work_orders(filters)
        
        # Application filtres supplémentaires
        if not work_orders_df.empty:
            # Filtre priorité
            if priority_filter != "Toutes":
                work_orders_df = work_orders_df[work_orders_df['priority'] == priority_filter]
            
            # Filtre recherche
            if search_term:
                search_mask = (
                    work_orders_df['work_order_number'].str.contains(search_term, case=False, na=False) |
                    work_orders_df['product_name'].str.contains(search_term, case=False, na=False)
                )
                work_orders_df = work_orders_df[search_mask]
        
        if not work_orders_df.empty:
            st.markdown(f"**📊 {len(work_orders_df)} bon(s) de travail trouvé(s)**")
            
            # Configuration colonnes d'affichage
            column_config = {
                "work_order_number": st.column_config.TextColumn("N° BT", width="medium"),
                "product_name": st.column_config.TextColumn("Produit", width="large"),
                "status": st.column_config.SelectboxColumn(
                    "Statut",
                    options=list(WORK_ORDER_STATUSES.keys()),
                    width="small"
                ),
                "priority": st.column_config.SelectboxColumn(
                    "Priorité",
                    options=list(WORK_ORDER_PRIORITIES.keys()),
                    width="small"
                ),
                "quantity": st.column_config.NumberColumn("Quantité", format="%.0f", width="small"),
                "total_cost": st.column_config.NumberColumn("Coût Total", format="%.2f $", width="small"),
                "date_creation": st.column_config.DatetimeColumn("Date Création", width="medium")
            }
            
            # Affichage tableau avec sélection
            selected_rows = st.dataframe(
                work_orders_df,
                use_container_width=True,
                hide_index=True,
                column_config=column_config,
                on_select="rerun",
                selection_mode="multi-row"
            )
            
            # Actions sur les BT sélectionnés
            if selected_rows.selection.rows:
                st.markdown("#### 🛠️ Actions sur BT Sélectionnés")
                
                selected_bt_ids = [work_orders_df.iloc[i]['id'] for i in selected_rows.selection.rows]
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    new_status = st.selectbox(
                        "Changer statut vers:",
                        options=list(WORK_ORDER_STATUSES.keys()),
                        format_func=lambda x: WORK_ORDER_STATUSES[x]
                    )
                    
                    if st.button("🔄 Changer Statut"):
                        update_multiple_work_orders_status(work_order_manager, selected_bt_ids, new_status)
                
                with col2:
                    if st.button("👁️ Voir Détails"):
                        if len(selected_bt_ids) == 1:
                            bt_details = work_order_manager.get_work_order_by_id(selected_bt_ids[0])
                            if bt_details:
                                show_work_order_details(bt_details, work_order_manager)
                        else:
                            st.warning("Sélectionnez un seul BT pour voir les détails")
                
                with col3:
                    if st.button("📊 Analyser"):
                        show_multiple_work_orders_analysis(work_order_manager, selected_bt_ids)
                
                with col4:
                    if st.button("📄 Export"):
                        export_work_orders_data(work_orders_df.iloc[selected_rows.selection.rows])
            
            # Statistiques rapides
            show_work_orders_statistics(work_orders_df)
        
        else:
            st.warning("🔍 Aucun bon de travail trouvé avec les filtres appliqués.")
            
            if st.button("🔄 Réinitialiser les filtres"):
                st.rerun()
    
    except Exception as e:
        st.error(f"Erreur lors de la récupération des BT: {e}")


def show_production_tracking_tab(work_order_manager: WorkOrderManager):
    """Sous-onglet: Suivi de production en temps réel"""
    st.markdown("#### 📊 Suivi de Production")
    
    # Sélection du BT à suivre
    active_work_orders = work_order_manager.get_all_work_orders({'status': 'EN_COURS'})
    
    if not active_work_orders.empty:
        
        # Sélection BT
        bt_options = {
            f"{row['work_order_number']} - {row['product_name']}": row['id']
            for _, row in active_work_orders.iterrows()
        }
        
        selected_bt = st.selectbox(
            "Sélectionner un BT en cours:",
            options=list(bt_options.keys()),
            help="Choisissez le bon de travail à suivre"
        )
        
        if selected_bt:
            bt_id = bt_options[selected_bt]
            bt_details = work_order_manager.get_work_order_by_id(bt_id)
            
            if bt_details:
                show_real_time_production_tracking(bt_details, work_order_manager)
    
    else:
        st.info("📋 Aucun bon de travail en cours de production.")
        
        # Affichage des BT récents pour suivi
        recent_bt = work_order_manager.get_all_work_orders()
        
        if not recent_bt.empty:
            st.markdown("#### 📈 Bons de Travail Récents")
            
            # Graphique de statuts
            status_counts = recent_bt['status'].value_counts()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📊 Répartition par Statut:**")
                for status, count in status_counts.items():
                    percentage = (count / len(recent_bt)) * 100
                    status_label = WORK_ORDER_STATUSES.get(status, status)
                    st.markdown(f"• {status_label}: {count} ({percentage:.1f}%)")
            
            with col2:
                st.bar_chart(status_counts, use_container_width=True)


def show_progress_analysis_tab(work_order_manager: WorkOrderManager):
    """Sous-onglet: Analyse d'avancement et KPIs"""
    st.markdown("#### 🔍 Analyse d'Avancement")
    
    # KPIs globaux de production
    all_bt = work_order_manager.get_all_work_orders()
    
    if not all_bt.empty:
        
        # Métriques principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_bt = len(all_bt)
            st.metric("Total BT", total_bt)
        
        with col2:
            if 'status' in all_bt.columns:
                completed_bt = len(all_bt[all_bt['status'] == 'TERMINE'])
                completion_rate = (completed_bt / total_bt) * 100 if total_bt > 0 else 0
                st.metric("Taux Réalisation", f"{completion_rate:.1f}%")
            else:
                st.metric("Taux Réalisation", "N/A")
        
        with col3:
            if 'total_cost' in all_bt.columns:
                total_value = all_bt['total_cost'].sum()
                st.metric("Valeur Totale", format_currency(total_value))
            else:
                st.metric("Valeur Totale", "N/A")
        
        with col4:
            if 'total_cost' in all_bt.columns and total_bt > 0:
                avg_value = all_bt['total_cost'].mean()
                st.metric("Valeur Moyenne", format_currency(avg_value))
            else:
                st.metric("Valeur Moyenne", "N/A")
        
        # Analyse des tendances
        show_production_trends_analysis(all_bt)
        
        # Analyse des retards
        show_delays_analysis(work_order_manager, all_bt)
        
        # Top produits
        show_top_products_analysis(all_bt)
    
    else:
        st.info("📊 Aucune donnée disponible pour l'analyse.")


def show_work_order_details(bt_details: Dict, work_order_manager: WorkOrderManager):
    """Affichage détaillé d'un bon de travail"""
    st.markdown("#### 📋 Détails du Bon de Travail")
    
    # En-tête avec informations principales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"**📋 N° BT:** {bt_details['work_order_number']}")
        st.markdown(f"**📦 Produit:** {bt_details['product_name']}")
        st.markdown(f"**📊 Statut:** {WORK_ORDER_STATUSES.get(bt_details['status'], bt_details['status'])}")
    
    with col2:
        metadata = bt_details.get('metadata', {})
        quantity = metadata.get('quantity_to_produce', 0)
        priority = metadata.get('priority', 'NORMALE')
        
        st.markdown(f"**🔢 Quantité:** {quantity}")
        st.markdown(f"**🎯 Priorité:** {WORK_ORDER_PRIORITIES.get(priority, priority)}")
        st.markdown(f"**📅 Créé le:** {bt_details['date_creation'][:10]}")
    
    with col3:
        cost_breakdown = metadata.get('cost_breakdown', {})
        total_cost = cost_breakdown.get('total_cost', 0)
        
        st.metric("Coût Total", format_currency(total_cost))
    
    # Onglets détaillés
    detail_tabs = st.tabs(["📋 BOM Explosée", "⚙️ Gamme", "📊 Avancement", "💰 Coûts"])
    
    with detail_tabs[0]:
        show_bt_bom_explosion(metadata)
    
    with detail_tabs[1]:
        show_bt_routing_operations(metadata)
    
    with detail_tabs[2]:
        show_bt_progress_tracking(bt_details, work_order_manager)
    
    with detail_tabs[3]:
        show_bt_cost_analysis(metadata)


def show_bt_bom_explosion(metadata: Dict):
    """Affichage de l'explosion BOM du BT"""
    st.markdown("##### 📋 Explosion BOM")
    
    bom_explosion = metadata.get('bom_explosion', [])
    
    if bom_explosion:
        # Conversion en DataFrame pour affichage
        explosion_data = []
        for item in bom_explosion:
            explosion_data.append({
                'Niveau': item.get('level', 0),
                'Code': item.get('component_code', ''),
                'Composant': item.get('component_name', ''),
                'Qté Unitaire': f"{item.get('quantity_per_unit', 0):.3f}",
                'Qté Totale': f"{item.get('quantity_total', 0):.3f}",
                'Unité': item.get('unit', ''),
                'Prix Unit.': format_currency(item.get('unit_price', 0)),
                'Coût Total': format_currency(item.get('total_cost', 0)),
                'Stock Dispo': f"{item.get('stock_available', 0):.1f}",
                'Statut Stock': item.get('stock_status', 'INCONNU')
            })
        
        explosion_df = pd.DataFrame(explosion_data)
        
        # Affichage avec mise en forme par niveau
        st.dataframe(
            explosion_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Analyse des besoins matières
        st.markdown("##### 📦 Analyse des Besoins Matières")
        
        materials_requirements = []
        for item in bom_explosion:
            shortage = max(0, item.get('quantity_total', 0) - item.get('stock_available', 0))
            if shortage > 0:
                materials_requirements.append({
                    'Composant': item.get('component_name', ''),
                    'Besoin': item.get('quantity_total', 0),
                    'Stock': item.get('stock_available', 0),
                    'Manque': shortage,
                    'Action': '🔴 Approvisionner'
                })
        
        if materials_requirements:
            st.warning(f"⚠️ {len(materials_requirements)} composant(s) en rupture:")
            
            req_df = pd.DataFrame(materials_requirements)
            st.dataframe(req_df, use_container_width=True, hide_index=True)
        else:
            st.success("✅ Tous les composants sont disponibles en stock")
    
    else:
        st.warning("📋 Aucune explosion BOM disponible pour ce BT")


def show_bt_routing_operations(metadata: Dict):
    """Affichage des opérations de la gamme du BT"""
    st.markdown("##### ⚙️ Opérations de Fabrication")
    
    routing_operations = metadata.get('routing_operations', [])
    
    if routing_operations:
        # Conversion en DataFrame
        operations_data = []
        for op in routing_operations:
            operations_data.append({
                'Séquence': op.get('operation_seq', 0),
                'Opération': op.get('operation_name', ''),
                'Poste de Travail': op.get('work_center_name', ''),
                'Durée (min)': op.get('duration_minutes', 0),
                'Taux ($/h)': format_currency(op.get('hourly_rate', 0)),
                'Coût': format_currency(op.get('operation_cost', 0)),
                'Statut': op.get('status', 'PLANIFIE')
            })
        
        operations_df = pd.DataFrame(operations_data)
        
        st.dataframe(
            operations_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Résumé gamme
        time_estimates = metadata.get('time_estimates', {})
        total_time = time_estimates.get('total_production_time', 0)
        estimated_hours = time_estimates.get('estimated_hours', 0)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Temps Total Production", format_duration(total_time))
        with col2:
            st.metric("Heures Estimées", f"{estimated_hours:.1f} h")
    
    else:
        st.warning("⚙️ Aucune gamme de fabrication disponible pour ce BT")


def show_bt_progress_tracking(bt_details: Dict, work_order_manager: WorkOrderManager):
    """Suivi d'avancement du BT"""
    st.markdown("##### 📊 Suivi d'Avancement")
    
    # Simulation d'avancement (en réalité, cela viendrait du TimeTracker)
    metadata = bt_details.get('metadata', {})
    routing_operations = metadata.get('routing_operations', [])
    
    if routing_operations:
        # Simulation d'états d'avancement
        progress_data = []
        for i, op in enumerate(routing_operations):
            # Simulation d'avancement basée sur le statut du BT
            if bt_details['status'] == 'TERMINE':
                progress = 100
                op_status = "TERMINE"
            elif bt_details['status'] == 'EN_COURS':
                # Simulation: les premières opérations sont terminées
                if i < len(routing_operations) // 2:
                    progress = 100
                    op_status = "TERMINE"
                elif i == len(routing_operations) // 2:
                    progress = 50
                    op_status = "EN_COURS"
                else:
                    progress = 0
                    op_status = "PLANIFIE"
            else:
                progress = 0
                op_status = "PLANIFIE"
            
            progress_data.append({
                'Opération': f"{op.get('operation_seq', 0)}: {op.get('operation_name', '')}",
                'Poste': op.get('work_center_name', ''),
                'Avancement': progress,
                'Statut': op_status,
                'Temps Prévu': format_duration(op.get('duration_minutes', 0)),
                'Temps Réel': format_duration(op.get('duration_minutes', 0) * (progress / 100)) if progress > 0 else "0 min"
            })
        
        progress_df = pd.DataFrame(progress_data)
        
        # Configuration colonnes avec barre de progression
        column_config = {
            "Opération": st.column_config.TextColumn("Opération", width="large"),
            "Poste": st.column_config.TextColumn("Poste", width="medium"),
            "Avancement": st.column_config.ProgressColumn(
                "Avancement",
                width="medium",
                min_value=0,
                max_value=100,
                format="%.0f%%"
            ),
            "Statut": st.column_config.SelectboxColumn(
                "Statut",
                options=["PLANIFIE", "EN_COURS", "TERMINE", "SUSPEND"],
                width="small"
            ),
            "Temps Prévu": st.column_config.TextColumn("Temps Prévu", width="small"),
            "Temps Réel": st.column_config.TextColumn("Temps Réel", width="small")
        }
        
        st.dataframe(
            progress_df,
            use_container_width=True,
            hide_index=True,
            column_config=column_config
        )
        
        # Avancement global
        total_progress = progress_df['Avancement'].mean()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Avancement Global", f"{total_progress:.0f}%")
        
        with col2:
            completed_ops = len(progress_df[progress_df['Avancement'] == 100])
            st.metric("Opérations Terminées", f"{completed_ops}/{len(progress_df)}")
        
        with col3:
            if total_progress > 0:
                estimated_completion = datetime.now() + timedelta(
                    days=(100 - total_progress) / 20  # Estimation simple
                )
                st.metric("Fin Estimée", estimated_completion.strftime('%Y-%m-%d'))
            else:
                st.metric("Fin Estimée", "À déterminer")
    
    else:
        st.warning("📊 Aucune donnée d'avancement disponible")


def show_bt_cost_analysis(metadata: Dict):
    """Analyse des coûts du BT"""
    st.markdown("##### 💰 Analyse des Coûts")
    
    cost_breakdown = metadata.get('cost_breakdown', {})
    
    if cost_breakdown:
        # Métriques principales
        col1, col2, col3 = st.columns(3)
        
        with col1:
            materials_cost = cost_breakdown.get('materials_cost', 0)
            st.metric("Coût Matières", format_currency(materials_cost))
        
        with col2:
            labor_cost = cost_breakdown.get('labor_cost', 0)
            st.metric("Coût Main d'Œuvre", format_currency(labor_cost))
        
        with col3:
            total_cost = cost_breakdown.get('total_cost', 0)
            st.metric("Coût Total", format_currency(total_cost))
        
        # Graphique de répartition
        if total_cost > 0:
            cost_data = {
                'Matières': materials_cost,
                'Main d\'Œuvre': labor_cost
            }
            
            st.markdown("**📊 Répartition des Coûts:**")
            
            for category, cost in cost_data.items():
                percentage = (cost / total_cost) * 100
                st.markdown(f"• {category}: {format_currency(cost)} ({percentage:.1f}%)")
            
            # Graphique simple
            cost_df = pd.DataFrame(list(cost_data.items()), columns=['Catégorie', 'Coût'])
            st.bar_chart(cost_df.set_index('Catégorie')['Coût'], use_container_width=True)
    
    else:
        st.warning("💰 Aucune analyse de coût disponible")


def show_real_time_production_tracking(bt_details: Dict, work_order_manager: WorkOrderManager):
    """Suivi de production en temps réel"""
    st.markdown(f"#### 🎯 Suivi Temps Réel - {bt_details['work_order_number']}")
    
    # Informations principales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"**📦 Produit:** {bt_details['product_name']}")
        metadata = bt_details.get('metadata', {})
        quantity = metadata.get('quantity_to_produce', 0)
        st.markdown(f"**🔢 Quantité:** {quantity}")
    
    with col2:
        priority = metadata.get('priority', 'NORMALE')
        st.markdown(f"**🎯 Priorité:** {WORK_ORDER_PRIORITIES.get(priority, priority)}")
        st.markdown(f"**📊 Statut:** {WORK_ORDER_STATUSES.get(bt_details['status'], bt_details['status'])}")
    
    with col3:
        # Boutons d'action rapide
        if st.button("▶️ Démarrer", key="start_bt"):
            work_order_manager.update_work_order_status(bt_details['id'], 'EN_COURS', 'Démarré depuis interface')
            st.success("✅ BT démarré!")
            st.rerun()
        
        if st.button("⏸️ Suspendre", key="pause_bt"):
            work_order_manager.update_work_order_status(bt_details['id'], 'SUSPEND', 'Suspendu depuis interface')
            st.warning("⏸️ BT suspendu!")
            st.rerun()
    
    # Suivi des opérations en temps réel
    st.markdown("---")
    show_bt_progress_tracking(bt_details, work_order_manager)
    
    # Intégration TimeTracker (simulation)
    st.markdown("##### ⏱️ Intégration TimeTracker")
    
    st.info("🔗 **Intégration TimeTracker:** Les pointages des employés sur ce BT apparaîtront ici automatiquement.")
    
    # Simulation de pointages
    tracking_data = [
        {"Employé": "Jean Dupont", "Opération": "1001: Montage-soudé", "Début": "08:00", "Fin": "10:30", "Durée": "2h30"},
        {"Employé": "Marie Martin", "Opération": "1002: Soudage manuel", "Début": "10:45", "Fin": "En cours", "Durée": "1h15+"},
    ]
    
    tracking_df = pd.DataFrame(tracking_data)
    st.dataframe(tracking_df, use_container_width=True, hide_index=True)


def show_work_orders_statistics(work_orders_df: pd.DataFrame):
    """Statistiques des bons de travail"""
    st.markdown("#### 📊 Statistiques")
    
    if not work_orders_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_quantity = work_orders_df['quantity'].sum() if 'quantity' in work_orders_df.columns else 0
            st.metric("Quantité Totale", f"{total_quantity:.0f}")
        
        with col2:
            avg_cost = work_orders_df['total_cost'].mean() if 'total_cost' in work_orders_df.columns else 0
            st.metric("Coût Moyen", format_currency(avg_cost))
        
        with col3:
            if 'status' in work_orders_df.columns:
                completion_rate = len(work_orders_df[work_orders_df['status'] == 'TERMINE']) / len(work_orders_df) * 100
                st.metric("Taux Réalisation", f"{completion_rate:.1f}%")
            else:
                st.metric("Taux Réalisation", "N/A")
        
        with col4:
            unique_products = work_orders_df['product_name'].nunique() if 'product_name' in work_orders_df.columns else 0
            st.metric("Produits Différents", unique_products)


def update_multiple_work_orders_status(work_order_manager: WorkOrderManager, bt_ids: List[int], new_status: str):
    """Met à jour le statut de plusieurs BT"""
    success_count = 0
    
    for bt_id in bt_ids:
        if work_order_manager.update_work_order_status(bt_id, new_status, f'Changement groupé vers {new_status}'):
            success_count += 1
    
    if success_count == len(bt_ids):
        st.success(f"✅ {success_count} BT mis à jour vers '{WORK_ORDER_STATUSES.get(new_status, new_status)}'")
    else:
        st.warning(f"⚠️ {success_count}/{len(bt_ids)} BT mis à jour")
    
    time.sleep(1)
    st.rerun()


def show_multiple_work_orders_analysis(work_order_manager: WorkOrderManager, bt_ids: List[int]):
    """Analyse de plusieurs BT sélectionnés"""
    st.markdown("#### 📊 Analyse des BT Sélectionnés")
    
    analysis_data = []
    total_cost = 0
    total_quantity = 0
    
    for bt_id in bt_ids:
        bt_details = work_order_manager.get_work_order_by_id(bt_id)
        if bt_details:
            metadata = bt_details.get('metadata', {})
            cost = metadata.get('cost_breakdown', {}).get('total_cost', 0)
            quantity = metadata.get('quantity_to_produce', 0)
            
            analysis_data.append({
                'BT': bt_details['work_order_number'],
                'Produit': bt_details['product_name'],
                'Quantité': quantity,
                'Coût': cost,
                'Statut': bt_details['status']
            })
            
            total_cost += cost
            total_quantity += quantity
    
    if analysis_data:
        analysis_df = pd.DataFrame(analysis_data)
        st.dataframe(analysis_df, use_container_width=True, hide_index=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Coût Total Sélection", format_currency(total_cost))
        with col2:
            st.metric("Quantité Totale", f"{total_quantity:.0f}")


def export_work_orders_data(work_orders_df: pd.DataFrame):
    """Export des données de BT"""
    csv_data = work_orders_df.to_csv(index=False)
    
    st.download_button(
        label="💾 Télécharger CSV",
        data=csv_data,
        file_name=f"bons_travail_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )


def show_production_trends_analysis(all_bt: pd.DataFrame):
    """Analyse des tendances de production"""
    st.markdown("##### 📈 Tendances de Production")
    
    if 'date_creation' in all_bt.columns and len(all_bt) > 1:
        # Analyse temporelle
        all_bt['creation_date'] = pd.to_datetime(all_bt['date_creation'])
        all_bt['creation_month'] = all_bt['creation_date'].dt.to_period('M')
        
        monthly_bt = all_bt.groupby('creation_month').size().reset_index(name='count')
        monthly_bt['month_str'] = monthly_bt['creation_month'].astype(str)
        
        if len(monthly_bt) > 1:
            st.line_chart(
                monthly_bt.set_index('month_str')['count'],
                use_container_width=True
            )
        else:
            st.info("📊 Pas assez de données pour la tendance temporelle")
    
    else:
        st.info("📊 Données insuffisantes pour l'analyse des tendances")


def show_delays_analysis(work_order_manager: WorkOrderManager, all_bt: pd.DataFrame):
    """Analyse des retards"""
    st.markdown("##### ⏰ Analyse des Retards")
    
    # Simulation d'analyse de retards
    if not all_bt.empty:
        delayed_bt = 0  # Simulation - en réalité calculé depuis dates d'échéance
        
        if delayed_bt > 0:
            st.warning(f"⚠️ {delayed_bt} BT en retard")
        else:
            st.success("✅ Aucun retard détecté")
    
    else:
        st.info("📊 Aucune donnée pour l'analyse des retards")


def show_top_products_analysis(all_bt: pd.DataFrame):
    """Analyse des top produits"""
    st.markdown("##### 🏆 Top Produits")
    
    if 'product_name' in all_bt.columns and not all_bt.empty:
        top_products = all_bt['product_name'].value_counts().head(5)
        
        if not top_products.empty:
            st.markdown("**🥇 Top 5 Produits les Plus Fabriqués:**")
            
            for i, (product, count) in enumerate(top_products.items(), 1):
                percentage = (count / len(all_bt)) * 100
                st.markdown(f"{i}. {product}: {count} BT ({percentage:.1f}%)")
        else:
            st.info("📊 Aucune donnée produit disponible")
    
    else:
        st.info("📊 Aucune donnée produit disponible")


# =============================================================================
# FONCTION PRINCIPALE - INTERFACE UNIFIÉE
# =============================================================================

def show_production_management_page():
    """Interface principale Production Management DG Inc. avec 4 onglets unifiés"""
    
    # Initialisation des variables de session
    if 'bom_editing_mode' not in st.session_state:
        st.session_state.bom_editing_mode = False
    if 'bom_selected_rows' not in st.session_state:
        st.session_state.bom_selected_rows = []
    if 'bom_show_add_form' not in st.session_state:
        st.session_state.bom_show_add_form = False
    if 'bom_show_catalog' not in st.session_state:
        st.session_state.bom_show_catalog = False
    
    # En-tête avec style
    st.markdown("""
    <div style="background: linear-gradient(90deg, #1f4e79, #2e5984); 
                padding: 1rem; border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0; text-align: center;">
            🏭 Production Management DG Inc.
        </h1>
        <p style="color: #e8f4fd; margin: 0.5rem 0 0 0; text-align: center;">
            Système MRP/Production - BOM • Gammes • Bons de Travail
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Health Check du système au démarrage
    with st.spinner("🔍 Vérification du système..."):
        health_check = get_system_health_check()
    
    # Affichage du statut système
    if health_check['status'] == 'HEALTHY':
        st.success("✅ Système de production opérationnel")
    elif health_check['status'] == 'WARNING':
        st.warning("⚠️ Système fonctionnel avec avertissements")
        with st.expander("Voir les avertissements"):
            for warning in health_check['warnings']:
                st.warning(f"⚠️ {warning}")
    else:
        st.error("❌ Problèmes détectés dans le système")
        with st.expander("Voir les erreurs", expanded=True):
            for error in health_check['errors']:
                st.error(f"❌ {error}")
        
        if health_check['status'] == 'CRITICAL':
            st.stop()
    
    # Vérification de la connexion à la base de données
    try:
        db = ERPDatabase()
        # Test de connexion étendu
        system_initialized, init_errors = initialize_production_system()
        
        if not system_initialized:
            st.error("❌ Échec de l'initialisation du système de production")
            with st.expander("Détails des erreurs"):
                for error in init_errors:
                    st.error(f"• {error}")
            st.info("💡 Vérifiez la configuration de la base de données dans le module ERP")
            
    except Exception as e:
        st.error(f"❌ Erreur de connexion à la base de données: {e}")
        st.info("💡 Vérifiez que le module `erp_database.py` est correctement configuré")
        st.stop()
    
    # Navigation principale avec 4 onglets
    tabs = st.tabs([
        "📦 Produits", 
        "📋 Nomenclatures (BOM)", 
        "⚙️ Gammes Fabrication",
        "🧾 Bons de Travail"
    ])
    
    # Affichage des onglets avec gestion d'erreurs robuste
    try:
        with tabs[0]:
            show_products_tab()
        
        with tabs[1]:
            show_bom_tab()
        
        with tabs[2]:
            show_routing_tab()
        
        with tabs[3]:
            show_work_orders_tab()
            
    except Exception as e:
        st.error(f"❌ Erreur dans l'interface utilisateur: {e}")
        logger.error(f"Erreur interface: {e}")
        
        # Bouton de récupération
        if st.button("🔄 Recharger l'interface"):
            st.rerun()
    
    # Footer informatif avec statistiques système
    st.markdown("---")
    
    # Statistiques rapides du système
    try:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            products_count = len(ProductManager(db).get_all_products())
            st.metric("Produits", products_count)
        
        with col2:
            work_centers_count = len(RoutingManager(db).get_available_work_centers())
            st.metric("Postes Travail", work_centers_count)
        
        with col3:
            work_orders_count = len(WorkOrderManager(db, BOMManager(db), RoutingManager(db)).get_all_work_orders())
            st.metric("Bons Travail", work_orders_count)
        
        with col4:
            # Health status badge
            status_colors = {
                'HEALTHY': 'green',
                'WARNING': 'orange', 
                'UNHEALTHY': 'red',
                'CRITICAL': 'red'
            }
            status_color = status_colors.get(health_check['status'], 'gray')
            st.markdown(f"""
            <div style="text-align: center;">
                <span style="background-color: {status_color}; color: white; 
                           padding: 0.3rem 0.8rem; border-radius: 15px; font-size: 0.8rem;">
                    {health_check['status']}
                </span>
            </div>
            """, unsafe_allow_html=True)
            
    except Exception as e:
        logger.warning(f"Erreur calcul statistiques: {e}")
    
    # Footer avec version et timestamp
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.8rem; margin-top: 1rem;">
        Production Management v2.0 - DG Inc. | Intégration complète ERP Database<br>
        <small>Dernière mise à jour: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</small>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# POINT D'ENTRÉE PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    # Test en mode standalone
    st.set_page_config(
        page_title="Production Management - DG Inc.",
        page_icon="🏭",
        layout="wide"
    )
    
    show_production_management_page()
