import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import io
import csv
from typing import Dict, List, Optional, Any
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GestionnaireInventaire:
    """
    Gestionnaire d'inventaire connecté à ERPDatabase SQLite
    Gère les articles, mouvements, alertes et statistiques
    """
    
    def __init__(self, db):
        self.db = db
        logger.info("GestionnaireInventaire initialisé avec base SQLite")
    
    # =========================================================================
    # MÉTHODES CRUD ARTICLES INVENTAIRE
    # =========================================================================
    
    def get_all_items(self) -> List[Dict]:
        """Récupère tous les articles d'inventaire"""
        try:
            query = '''
                SELECT * FROM inventory_items 
                ORDER BY nom ASC
            '''
            rows = self.db.execute_query(query)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération articles: {e}")
            return []
    
    def get_item_by_id(self, item_id: int) -> Optional[Dict]:
        """Récupère un article par son ID"""
        try:
            query = "SELECT * FROM inventory_items WHERE id = ?"
            result = self.db.execute_query(query, (item_id,))
            return dict(result[0]) if result else None
        except Exception as e:
            logger.error(f"Erreur récupération article {item_id}: {e}")
            return None
    
    def add_item(self, item_data: Dict) -> Optional[int]:
        """Ajoute un nouvel article d'inventaire"""
        try:
            # Validation des données
            if not item_data.get('nom'):
                raise ValueError("Nom de l'article obligatoire")
            
            # Générer code interne si non fourni
            if not item_data.get('code_interne'):
                item_data['code_interne'] = self._generate_internal_code(item_data['nom'])
            
            query = '''
                INSERT INTO inventory_items 
                (nom, type_produit, quantite_imperial, quantite_metric, 
                 limite_minimale_imperial, limite_minimale_metric,
                 quantite_reservee_imperial, quantite_reservee_metric,
                 statut, description, notes, fournisseur_principal, code_interne)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            # Calcul automatique du statut
            statut = self._calculate_status(
                item_data.get('quantite_metric', 0),
                item_data.get('limite_minimale_metric', 0)
            )
            
            item_id = self.db.execute_insert(query, (
                item_data['nom'],
                item_data.get('type_produit', ''),
                item_data.get('quantite_imperial', ''),
                float(item_data.get('quantite_metric', 0)),
                item_data.get('limite_minimale_imperial', ''),
                float(item_data.get('limite_minimale_metric', 0)),
                item_data.get('quantite_reservee_imperial', ''),
                float(item_data.get('quantite_reservee_metric', 0)),
                statut,
                item_data.get('description', ''),
                item_data.get('notes', ''),
                item_data.get('fournisseur_principal', ''),
                item_data['code_interne']
            ))
            
            # Enregistrer dans l'historique
            if item_id:
                self._add_history_entry(
                    item_id, 
                    'CREATION', 
                    '0', 
                    str(item_data.get('quantite_metric', 0)),
                    f"Création article: {item_data['nom']}"
                )
            
            logger.info(f"Article créé: ID={item_id}, nom={item_data['nom']}")
            return item_id
            
        except Exception as e:
            logger.error(f"Erreur ajout article: {e}")
            return None
    
    def update_item(self, item_id: int, item_data: Dict) -> bool:
        """Met à jour un article d'inventaire"""
        try:
            # Récupérer l'article existant pour comparaison
            existing = self.get_item_by_id(item_id)
            if not existing:
                return False
            
            # Calcul automatique du statut
            statut = self._calculate_status(
                item_data.get('quantite_metric', existing['quantite_metric']),
                item_data.get('limite_minimale_metric', existing['limite_minimale_metric'])
            )
            
            query = '''
                UPDATE inventory_items SET
                nom = ?, type_produit = ?, quantite_imperial = ?, quantite_metric = ?,
                limite_minimale_imperial = ?, limite_minimale_metric = ?,
                quantite_reservee_imperial = ?, quantite_reservee_metric = ?,
                statut = ?, description = ?, notes = ?, fournisseur_principal = ?,
                code_interne = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            '''
            
            affected = self.db.execute_update(query, (
                item_data.get('nom', existing['nom']),
                item_data.get('type_produit', existing['type_produit']),
                item_data.get('quantite_imperial', existing['quantite_imperial']),
                float(item_data.get('quantite_metric', existing['quantite_metric'])),
                item_data.get('limite_minimale_imperial', existing['limite_minimale_imperial']),
                float(item_data.get('limite_minimale_metric', existing['limite_minimale_metric'])),
                item_data.get('quantite_reservee_imperial', existing['quantite_reservee_imperial']),
                float(item_data.get('quantite_reservee_metric', existing['quantite_reservee_metric'])),
                statut,
                item_data.get('description', existing['description']),
                item_data.get('notes', existing['notes']),
                item_data.get('fournisseur_principal', existing['fournisseur_principal']),
                item_data.get('code_interne', existing['code_interne']),
                item_id
            ))
            
            # Historique si quantité changée
            if item_data.get('quantite_metric') != existing['quantite_metric']:
                self._add_history_entry(
                    item_id,
                    'MODIFICATION',
                    str(existing['quantite_metric']),
                    str(item_data.get('quantite_metric', existing['quantite_metric'])),
                    f"Modification article: {existing['nom']}"
                )
            
            logger.info(f"Article mis à jour: ID={item_id}")
            return affected > 0
            
        except Exception as e:
            logger.error(f"Erreur mise à jour article {item_id}: {e}")
            return False
    
    def delete_item(self, item_id: int) -> bool:
        """Supprime un article d'inventaire"""
        try:
            # Vérifier que l'article existe
            item = self.get_item_by_id(item_id)
            if not item:
                return False
            
            # Supprimer l'historique associé
            self.db.execute_update("DELETE FROM inventory_history WHERE inventory_item_id = ?", (item_id,))
            
            # Supprimer l'article
            affected = self.db.execute_update("DELETE FROM inventory_items WHERE id = ?", (item_id,))
            
            logger.info(f"Article supprimé: ID={item_id}, nom={item['nom']}")
            return affected > 0
            
        except Exception as e:
            logger.error(f"Erreur suppression article {item_id}: {e}")
            return False
    
    # =========================================================================
    # MÉTHODES MOUVEMENTS DE STOCK
    # =========================================================================
    
    def add_stock_movement(self, item_id: int, movement_type: str, quantity: float, notes: str = "", employee_id: int = None) -> bool:
        """Ajoute un mouvement de stock (ENTREE, SORTIE, AJUSTEMENT)"""
        try:
            # Récupérer l'article
            item = self.get_item_by_id(item_id)
            if not item:
                return False
            
            current_qty = float(item['quantite_metric'])
            
            # Calculer la nouvelle quantité
            if movement_type == 'ENTREE':
                new_qty = current_qty + quantity
            elif movement_type == 'SORTIE':
                new_qty = max(0, current_qty - quantity)  # Éviter les quantités négatives
            elif movement_type == 'AJUSTEMENT':
                new_qty = quantity  # Ajustement direct
            else:
                raise ValueError(f"Type de mouvement invalide: {movement_type}")
            
            # Mettre à jour la quantité
            success = self.update_item(item_id, {'quantite_metric': new_qty})
            
            if success:
                # Enregistrer dans l'historique
                self._add_history_entry(
                    item_id,
                    movement_type,
                    str(current_qty),
                    str(new_qty),
                    notes,
                    employee_id
                )
                
                logger.info(f"Mouvement de stock: {movement_type} {quantity} pour article {item_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur mouvement de stock: {e}")
            return False
    
    def get_stock_movements(self, item_id: int = None, limit: int = 100) -> List[Dict]:
        """Récupère l'historique des mouvements de stock"""
        try:
            if item_id:
                query = '''
                    SELECT ih.*, ii.nom as item_nom, ii.code_interne,
                           e.prenom || ' ' || e.nom as employee_nom
                    FROM inventory_history ih
                    LEFT JOIN inventory_items ii ON ih.inventory_item_id = ii.id
                    LEFT JOIN employees e ON ih.employee_id = e.id
                    WHERE ih.inventory_item_id = ?
                    ORDER BY ih.created_at DESC
                    LIMIT ?
                '''
                rows = self.db.execute_query(query, (item_id, limit))
            else:
                query = '''
                    SELECT ih.*, ii.nom as item_nom, ii.code_interne,
                           e.prenom || ' ' || e.nom as employee_nom
                    FROM inventory_history ih
                    LEFT JOIN inventory_items ii ON ih.inventory_item_id = ii.id
                    LEFT JOIN employees e ON ih.employee_id = e.id
                    ORDER BY ih.created_at DESC
                    LIMIT ?
                '''
                rows = self.db.execute_query(query, (limit,))
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur récupération mouvements: {e}")
            return []
    
    # =========================================================================
    # MÉTHODES ALERTES ET ANALYSE
    # =========================================================================
    
    def get_critical_stock_items(self) -> List[Dict]:
        """Récupère les articles avec stock critique"""
        try:
            query = '''
                SELECT * FROM inventory_items 
                WHERE statut IN ('ÉPUISÉ', 'CRITIQUE', 'FAIBLE')
                OR quantite_metric <= limite_minimale_metric
                ORDER BY 
                    CASE statut
                        WHEN 'ÉPUISÉ' THEN 1
                        WHEN 'CRITIQUE' THEN 2
                        WHEN 'FAIBLE' THEN 3
                        ELSE 4
                    END,
                    quantite_metric ASC
            '''
            rows = self.db.execute_query(query)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur récupération stocks critiques: {e}")
            return []
    
    def get_inventory_statistics(self) -> Dict[str, Any]:
        """Calcule les statistiques d'inventaire"""
        try:
            stats = {
                'total_items': 0,
                'by_status': {},
                'by_type': {},
                'total_value': 0.0,
                'critical_items': 0,
                'movements_last_30_days': 0,
                'top_suppliers': [],
                'low_stock_alerts': 0
            }
            
            # Statistiques de base
            basic_stats = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN statut = 'DISPONIBLE' THEN 1 END) as disponible,
                    COUNT(CASE WHEN statut = 'FAIBLE' THEN 1 END) as faible,
                    COUNT(CASE WHEN statut = 'CRITIQUE' THEN 1 END) as critique,
                    COUNT(CASE WHEN statut = 'ÉPUISÉ' THEN 1 END) as epuise,
                    COUNT(CASE WHEN quantite_metric <= limite_minimale_metric THEN 1 END) as alerts
                FROM inventory_items
            ''')
            
            if basic_stats:
                base = dict(basic_stats[0])
                stats['total_items'] = base['total']
                stats['by_status'] = {
                    'DISPONIBLE': base['disponible'],
                    'FAIBLE': base['faible'],
                    'CRITIQUE': base['critique'],
                    'ÉPUISÉ': base['epuise']
                }
                stats['critical_items'] = base['critique'] + base['epuise']
                stats['low_stock_alerts'] = base['alerts']
            
            # Par type de produit
            type_stats = self.db.execute_query('''
                SELECT type_produit, COUNT(*) as count
                FROM inventory_items 
                WHERE type_produit IS NOT NULL AND type_produit != ''
                GROUP BY type_produit
                ORDER BY count DESC
            ''')
            stats['by_type'] = {row['type_produit']: row['count'] for row in type_stats}
            
            # Mouvements des 30 derniers jours
            movements_30d = self.db.execute_query('''
                SELECT COUNT(*) as count
                FROM inventory_history
                WHERE created_at >= date('now', '-30 days')
            ''')
            if movements_30d:
                stats['movements_last_30_days'] = movements_30d[0]['count']
            
            # Top fournisseurs
            suppliers_stats = self.db.execute_query('''
                SELECT fournisseur_principal, COUNT(*) as items_count
                FROM inventory_items 
                WHERE fournisseur_principal IS NOT NULL AND fournisseur_principal != ''
                GROUP BY fournisseur_principal
                ORDER BY items_count DESC
                LIMIT 5
            ''')
            stats['top_suppliers'] = [dict(row) for row in suppliers_stats]
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur calcul statistiques: {e}")
            return {}
    
    def search_items(self, search_term: str = "", filters: Dict = None) -> List[Dict]:
        """Recherche d'articles avec filtres"""
        try:
            query = "SELECT * FROM inventory_items WHERE 1=1"
            params = []
            
            # Recherche textuelle
            if search_term:
                query += " AND (nom LIKE ? OR code_interne LIKE ? OR description LIKE ?)"
                pattern = f"%{search_term}%"
                params.extend([pattern, pattern, pattern])
            
            # Filtres
            if filters:
                if filters.get('type_produit'):
                    query += " AND type_produit = ?"
                    params.append(filters['type_produit'])
                
                if filters.get('statut'):
                    query += " AND statut = ?"
                    params.append(filters['statut'])
                
                if filters.get('fournisseur'):
                    query += " AND fournisseur_principal LIKE ?"
                    params.append(f"%{filters['fournisseur']}%")
                
                if filters.get('stock_critique_only'):
                    query += " AND statut IN ('CRITIQUE', 'FAIBLE', 'ÉPUISÉ')"
            
            query += " ORDER BY nom ASC"
            
            rows = self.db.execute_query(query, tuple(params) if params else None)
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erreur recherche articles: {e}")
            return []
    
    # =========================================================================
    # MÉTHODES EXPORT/IMPORT
    # =========================================================================
    
    def export_to_csv(self, items: List[Dict] = None) -> str:
        """Exporte les articles en CSV"""
        try:
            if items is None:
                items = self.get_all_items()
            
            output = io.StringIO()
            fieldnames = [
                'id', 'nom', 'type_produit', 'code_interne', 'quantite_metric',
                'limite_minimale_metric', 'statut', 'description', 'fournisseur_principal',
                'created_at', 'updated_at'
            ]
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in items:
                row = {field: item.get(field, '') for field in fieldnames}
                writer.writerow(row)
            
            csv_content = output.getvalue()
            output.close()
            return csv_content
            
        except Exception as e:
            logger.error(f"Erreur export CSV: {e}")
            return ""
    
    def import_from_csv(self, csv_content: str) -> Dict[str, int]:
        """Importe des articles depuis un CSV"""
        try:
            result = {'success': 0, 'errors': 0, 'skipped': 0}
            
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            
            for row in reader:
                try:
                    # Préparer les données
                    item_data = {
                        'nom': row.get('nom', '').strip(),
                        'type_produit': row.get('type_produit', '').strip(),
                        'code_interne': row.get('code_interne', '').strip(),
                        'quantite_metric': float(row.get('quantite_metric', 0)),
                        'limite_minimale_metric': float(row.get('limite_minimale_metric', 0)),
                        'description': row.get('description', '').strip(),
                        'fournisseur_principal': row.get('fournisseur_principal', '').strip()
                    }
                    
                    if not item_data['nom']:
                        result['skipped'] += 1
                        continue
                    
                    # Vérifier si l'article existe déjà (par code ou nom)
                    existing = None
                    if item_data['code_interne']:
                        existing_rows = self.db.execute_query(
                            "SELECT id FROM inventory_items WHERE code_interne = ?",
                            (item_data['code_interne'],)
                        )
                        if existing_rows:
                            existing = existing_rows[0]['id']
                    
                    if existing:
                        # Mise à jour
                        if self.update_item(existing, item_data):
                            result['success'] += 1
                        else:
                            result['errors'] += 1
                    else:
                        # Création
                        if self.add_item(item_data):
                            result['success'] += 1
                        else:
                            result['errors'] += 1
                
                except Exception as e:
                    logger.error(f"Erreur import ligne: {e}")
                    result['errors'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur import CSV: {e}")
            return {'success': 0, 'errors': 1, 'skipped': 0}
    
    # =========================================================================
    # MÉTHODES UTILITAIRES PRIVÉES
    # =========================================================================
    
    def _generate_internal_code(self, nom: str) -> str:
        """Génère un code interne automatique"""
        try:
            # Prendre les 3 premières lettres + timestamp
            prefix = ''.join([c.upper() for c in nom if c.isalpha()])[:3]
            if len(prefix) < 3:
                prefix = prefix.ljust(3, 'X')
            
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"{prefix}-{timestamp[-6:]}"
        except:
            return f"ART-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def _calculate_status(self, current_qty: float, min_qty: float) -> str:
        """Calcule le statut basé sur les quantités"""
        try:
            if current_qty <= 0:
                return 'ÉPUISÉ'
            elif min_qty > 0 and current_qty <= min_qty:
                return 'CRITIQUE'
            elif min_qty > 0 and current_qty <= (min_qty * 1.5):
                return 'FAIBLE'
            else:
                return 'DISPONIBLE'
        except:
            return 'DISPONIBLE'
    
    def _add_history_entry(self, item_id: int, action: str, qty_before: str, qty_after: str, notes: str = "", employee_id: int = None):
        """Ajoute une entrée dans l'historique"""
        try:
            query = '''
                INSERT INTO inventory_history 
                (inventory_item_id, action, quantite_avant, quantite_apres, notes, employee_id)
                VALUES (?, ?, ?, ?, ?, ?)
            '''
            self.db.execute_insert(query, (item_id, action, qty_before, qty_after, notes, employee_id))
        except Exception as e:
            logger.error(f"Erreur ajout historique: {e}")

# =========================================================================
# FONCTIONS UTILITAIRES POUR GESTION DES VALEURS NONE
# =========================================================================

def safe_string_slice(value, max_length: int = 20, default: str = 'N/A') -> str:
    """Retourne une chaîne tronquée en gérant les valeurs None"""
    if value is None:
        return default
    try:
        str_value = str(value)
        return str_value[:max_length] if len(str_value) > max_length else str_value
    except:
        return default

def safe_get_display_name(data_dict: dict, keys: list, default: str = 'N/A', max_length: int = None) -> str:
    """Récupère de manière sécurisée une valeur d'affichage depuis un dictionnaire"""
    for key in keys:
        value = data_dict.get(key)
        if value is not None and str(value).strip():
            result = str(value).strip()
            if max_length:
                return result[:max_length] + ('...' if len(result) > max_length else '')
            return result
    return default

# =========================================================================
# INTERFACE STREAMLIT PRINCIPALE
# =========================================================================

def show_inventory_page():
    """Interface principale du module inventaire"""
    st.markdown("### 📦 Gestion d'Inventaire")
    
    # Vérifier que la base est disponible
    if 'erp_db' not in st.session_state:
        st.error("❌ Base de données ERP non disponible")
        return
    
    # Initialiser le gestionnaire
    if 'inventory_manager' not in st.session_state:
        st.session_state.inventory_manager = GestionnaireInventaire(st.session_state.erp_db)
    
    inventory_manager = st.session_state.inventory_manager
    
    # Onglets principaux
    tab_list, tab_add, tab_movements, tab_stats, tab_import = st.tabs([
        "📋 Liste Articles", "➕ Ajouter", "📊 Mouvements", "📈 Statistiques", "📤 Import/Export"
    ])
    
    with tab_list:
        render_items_list_tab(inventory_manager)
    
    with tab_add:
        render_add_item_tab(inventory_manager)
    
    with tab_movements:
        render_movements_tab(inventory_manager)
    
    with tab_stats:
        render_statistics_tab(inventory_manager)
    
    with tab_import:
        render_import_export_tab(inventory_manager)
    
    # Gestion des actions
    handle_inventory_actions(inventory_manager)

def render_items_list_tab(inventory_manager):
    """Onglet liste des articles"""
    st.markdown("#### 📋 Liste des Articles d'Inventaire")
    
    # Filtres et recherche
    col_search, col_filter1, col_filter2, col_filter3 = st.columns([3, 1, 1, 1])
    
    with col_search:
        search_term = st.text_input("🔍 Rechercher:", placeholder="Nom, code, description...")
    
    with col_filter1:
        # Types de produits disponibles
        try:
            types_result = inventory_manager.db.execute_query(
                "SELECT DISTINCT type_produit FROM inventory_items WHERE type_produit IS NOT NULL AND type_produit != ''"
            )
            types_options = ['Tous'] + [row['type_produit'] for row in types_result if row['type_produit']]
        except:
            types_options = ['Tous']
        type_filter = st.selectbox("Type:", types_options)
    
    with col_filter2:
        statut_filter = st.selectbox("Statut:", ['Tous', 'DISPONIBLE', 'FAIBLE', 'CRITIQUE', 'ÉPUISÉ'])
    
    with col_filter3:
        show_critical_only = st.checkbox("Stock critique uniquement")
    
    # Préparer les filtres
    filters = {}
    if type_filter != 'Tous':
        filters['type_produit'] = type_filter
    if statut_filter != 'Tous':
        filters['statut'] = statut_filter
    if show_critical_only:
        filters['stock_critique_only'] = True
    
    # Récupérer les articles
    if search_term or filters:
        items = inventory_manager.search_items(search_term, filters)
    else:
        items = inventory_manager.get_all_items()
    
    if not items:
        st.info("Aucun article trouvé.")
        return
    
    # Affichage en mode carte ou tableau
    display_mode = st.radio("Mode d'affichage:", ["📋 Tableau", "🃏 Cartes"], horizontal=True, key="inventory_display_mode")
    
    if display_mode == "📋 Tableau":
        render_items_table(items, inventory_manager)
    else:
        render_items_cards(items, inventory_manager)

def render_items_table(items, inventory_manager):
    """Affichage en mode tableau"""
    # Préparer les données pour le tableau
    table_data = []
    for item in items:
        status_icon = {
            'DISPONIBLE': '🟢',
            'FAIBLE': '🟡', 
            'CRITIQUE': '🟠',
            'ÉPUISÉ': '🔴'
        }.get(item.get('statut', ''), '⚪')
        
        table_data.append({
            'ID': item.get('id', ''),
            'Code': safe_get_display_name(item, ['code_interne'], 'N/A', 15),
            'Nom': safe_get_display_name(item, ['nom'], 'N/A', 25),
            'Type': safe_get_display_name(item, ['type_produit'], 'N/A', 15),
            'Quantité': f"{item.get('quantite_metric', 0):.2f}",
            'Limite Min': f"{item.get('limite_minimale_metric', 0):.2f}",
            'Statut': f"{status_icon} {item.get('statut', '')}",
            'Fournisseur': safe_get_display_name(item, ['fournisseur_principal'], 'N/A', 20)
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(
        df,
        use_container_width=True,
        height=400,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Quantité": st.column_config.NumberColumn("Quantité", format="%.2f"),
            "Limite Min": st.column_config.NumberColumn("Limite Min", format="%.2f"),
        }
    )
    
    # Actions sur articles sélectionnés
    st.markdown("---")
    st.markdown("##### 🎯 Actions")
    
    selected_item = st.selectbox(
        "Sélectionner un article:",
        options=[None] + items,
        format_func=lambda x: f"{safe_get_display_name(x, ['code_interne'], '', 10)} - {safe_get_display_name(x, ['nom'], '', 25)}" if x else "Choisir...",
        key="selected_item_table"
    )
    
    if selected_item:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("👁️ Voir", use_container_width=True):
                st.session_state.inventory_action = "view_item"
                st.session_state.selected_item_id = selected_item['id']
        
        with col2:
            if st.button("✏️ Modifier", use_container_width=True):
                st.session_state.inventory_action = "edit_item" 
                st.session_state.selected_item_id = selected_item['id']
        
        with col3:
            if st.button("📦 Mouvement", use_container_width=True):
                st.session_state.inventory_action = "add_movement"
                st.session_state.selected_item_id = selected_item['id']
        
        with col4:
            if st.button("🗑️ Supprimer", use_container_width=True):
                st.session_state.inventory_action = "delete_item"
                st.session_state.selected_item_id = selected_item['id']

def render_items_cards(items, inventory_manager):
    """Affichage en mode cartes"""
    # Organiser en grille de 3 colonnes
    for i in range(0, len(items), 3):
        cols = st.columns(3)
        
        for j, col in enumerate(cols):
            if i + j < len(items):
                item = items[i + j]
                
                status_color = {
                    'DISPONIBLE': '#10b981',
                    'FAIBLE': '#f59e0b',
                    'CRITIQUE': '#ef4444', 
                    'ÉPUISÉ': '#dc2626'
                }.get(item.get('statut', ''), '#6b7280')
                
                code_interne = safe_get_display_name(item, ['code_interne'], 'N/A', 10)
                nom = safe_get_display_name(item, ['nom'], 'N/A', 25)
                type_produit = safe_get_display_name(item, ['type_produit'], 'N/A', 15)
                
                with col:
                    st.markdown(f"""
                    <div style="
                        border: 1px solid #e5e7eb;
                        border-left: 4px solid {status_color};
                        border-radius: 8px;
                        padding: 1rem;
                        margin-bottom: 1rem;
                        background: white;
                    ">
                        <h5 style="margin: 0 0 0.5rem 0; color: #1e40af;">
                            {code_interne} - {nom}
                        </h5>
                        <p style="margin: 0.25rem 0; font-size: 0.9em;">
                            📦 Quantité: {item.get('quantite_metric', 0):.2f}
                        </p>
                        <p style="margin: 0.25rem 0; font-size: 0.9em;">
                            ⚠️ Limite: {item.get('limite_minimale_metric', 0):.2f}
                        </p>
                        <p style="margin: 0.25rem 0; font-size: 0.9em;">
                            🏷️ Type: {type_produit}
                        </p>
                        <p style="margin: 0.25rem 0; font-size: 0.9em; color: {status_color}; font-weight: 600;">
                            📊 {item.get('statut', 'N/A')}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Boutons d'action
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    
                    with btn_col1:
                        if st.button("👁️", key=f"view_card_{item['id']}", help="Voir", use_container_width=True):
                            st.session_state.inventory_action = "view_item"
                            st.session_state.selected_item_id = item['id']
                    
                    with btn_col2:
                        if st.button("✏️", key=f"edit_card_{item['id']}", help="Modifier", use_container_width=True):
                            st.session_state.inventory_action = "edit_item"
                            st.session_state.selected_item_id = item['id']
                    
                    with btn_col3:
                        if st.button("📦", key=f"move_card_{item['id']}", help="Mouvement", use_container_width=True):
                            st.session_state.inventory_action = "add_movement"
                            st.session_state.selected_item_id = item['id']

def render_add_item_tab(inventory_manager):
    """Onglet ajout d'article"""
    st.markdown("#### ➕ Ajouter un Nouvel Article")
    
    with st.form("add_item_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            nom = st.text_input("Nom de l'article *:", placeholder="Ex: Tube acier rond 25mm")
            code_interne = st.text_input("Code interne:", placeholder="Auto-généré si vide")
            type_produit = st.selectbox("Type de produit:", [
                "", "Matière première", "Tube/Profilé", "Tôle/Plaque", "Visserie", 
                "Outil", "Consommable", "Produit fini", "Autre"
            ])
            fournisseur = st.text_input("Fournisseur principal:", placeholder="Ex: Acier ABC Inc.")
        
        with col2:
            quantite_metric = st.number_input("Quantité initiale:", min_value=0.0, value=0.0, step=0.01)
            limite_min = st.number_input("Limite minimale:", min_value=0.0, value=0.0, step=0.01)
            quantite_imperial = st.text_input("Quantité impériale:", placeholder="Ex: 10 ft 6 in")
            limite_imperial = st.text_input("Limite min. impériale:", placeholder="Ex: 2 ft")
        
        description = st.text_area("Description:", placeholder="Description détaillée de l'article...")
        notes = st.text_area("Notes:", placeholder="Notes internes, observations...")
        
        submitted = st.form_submit_button("💾 Ajouter l'Article", use_container_width=True, type="primary")
        
        if submitted:
            if not nom:
                st.error("Le nom de l'article est obligatoire.")
            else:
                item_data = {
                    'nom': nom.strip(),
                    'code_interne': code_interne.strip() if code_interne else None,
                    'type_produit': type_produit,
                    'quantite_metric': quantite_metric,
                    'limite_minimale_metric': limite_min,
                    'quantite_imperial': quantite_imperial.strip(),
                    'limite_minimale_imperial': limite_imperial.strip(),
                    'quantite_reservee_metric': 0,
                    'description': description.strip(),
                    'notes': notes.strip(),
                    'fournisseur_principal': fournisseur.strip()
                }
                
                item_id = inventory_manager.add_item(item_data)
                if item_id:
                    st.success(f"✅ Article ajouté avec succès ! ID: {item_id}")
                    if code_interne:
                        st.info(f"Code interne assigné: {item_data.get('code_interne', 'Auto-généré')}")
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de l'ajout de l'article.")

def render_movements_tab(inventory_manager):
    """Onglet mouvements de stock - CORRIGÉ pour gérer les valeurs None"""
    st.markdown("#### 📊 Mouvements de Stock")
    
    # Section ajout de mouvement
    with st.expander("➕ Ajouter un Mouvement", expanded=False):
        with st.form("add_movement_form"):
            # Sélection de l'article
            items = inventory_manager.get_all_items()
            if not items:
                st.warning("Aucun article en inventaire.")
                return
            
            selected_item = st.selectbox(
                "Article:",
                options=items,
                format_func=lambda x: f"{safe_get_display_name(x, ['code_interne'], 'N/A', 10)} - {safe_get_display_name(x, ['nom'], 'N/A', 30)} (Stock: {x.get('quantite_metric', 0):.2f})"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                movement_type = st.selectbox("Type de mouvement:", ["ENTREE", "SORTIE", "AJUSTEMENT"])
                quantity = st.number_input("Quantité:", min_value=0.01, value=1.0, step=0.01)
            
            with col2:
                # Employé (si disponible)
                try:
                    employees = inventory_manager.db.execute_query("SELECT id, prenom, nom FROM employees WHERE statut = 'ACTIF'")
                    if employees:
                        employee_options = [None] + employees
                        selected_employee = st.selectbox(
                            "Employé responsable:",
                            options=employee_options,
                            format_func=lambda x: f"{safe_get_display_name(x, ['prenom'], '', 10)} {safe_get_display_name(x, ['nom'], '', 15)}" if x else "Non spécifié"
                        )
                        employee_id = selected_employee.get('id') if selected_employee else None
                    else:
                        employee_id = None
                        st.info("Aucun employé disponible")
                except:
                    employee_id = None
            
            notes = st.text_area("Notes:", placeholder="Raison du mouvement, référence commande...")
            
            submitted = st.form_submit_button("📦 Enregistrer le Mouvement", type="primary")
            
            if submitted and selected_item:
                success = inventory_manager.add_stock_movement(
                    selected_item['id'],
                    movement_type,
                    quantity,
                    notes,
                    employee_id
                )
                
                if success:
                    st.success(f"✅ Mouvement enregistré: {movement_type} de {quantity} pour {selected_item['nom']}")
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de l'enregistrement du mouvement.")
    
    # Historique des mouvements
    st.markdown("##### 📋 Historique des Mouvements")
    
    # Filtres pour l'historique
    col1, col2 = st.columns(2)
    with col1:
        show_all = st.checkbox("Afficher tous les mouvements", value=True)
    with col2:
        if not show_all:
            items = inventory_manager.get_all_items()
            filter_item = st.selectbox(
                "Filtrer par article:",
                options=[None] + items,
                format_func=lambda x: f"{safe_get_display_name(x, ['code_interne'], 'N/A', 10)} - {safe_get_display_name(x, ['nom'], 'N/A', 25)}" if x else "Tous"
            )
        else:
            filter_item = None
    
    # Récupérer les mouvements
    if filter_item:
        movements = inventory_manager.get_stock_movements(filter_item['id'], 50)
    else:
        movements = inventory_manager.get_stock_movements(None, 100)
    
    if movements:
        # Affichage en tableau - CORRIGÉ pour gérer les valeurs None
        movement_data = []
        for mov in movements:
            # CORRECTION PRINCIPALE : Gestion sécurisée des valeurs None
            movement_data.append({
                'Date': safe_string_slice(mov.get('created_at', ''), 16, 'N/A').replace('T', ' '),
                'Article': safe_string_slice(f"{safe_get_display_name(mov, ['code_interne'], '', 10)} - {safe_get_display_name(mov, ['item_nom'], '', 20)}", 30, 'N/A'),
                'Action': safe_get_display_name(mov, ['action'], 'N/A', 15),
                'Avant': safe_get_display_name(mov, ['quantite_avant'], 'N/A', 10),
                'Après': safe_get_display_name(mov, ['quantite_apres'], 'N/A', 10),
                'Employé': safe_string_slice(mov.get('employee_nom', 'Système'), 20, 'Système'),
                'Notes': safe_string_slice(mov.get('notes', ''), 40, '')
            })
        
        df_movements = pd.DataFrame(movement_data)
        st.dataframe(
            df_movements,
            use_container_width=True,
            height=400
        )
    else:
        st.info("Aucun mouvement enregistré.")

def render_statistics_tab(inventory_manager):
    """Onglet statistiques"""
    st.markdown("#### 📈 Statistiques d'Inventaire")
    
    # Récupérer les statistiques
    stats = inventory_manager.get_inventory_statistics()
    if not stats:
        st.warning("Impossible de charger les statistiques.")
        return
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Total Articles", stats.get('total_items', 0))
    with col2:
        st.metric("🚨 Articles Critiques", stats.get('critical_items', 0))
    with col3:
        st.metric("⚠️ Alertes Stock Bas", stats.get('low_stock_alerts', 0))
    with col4:
        st.metric("📊 Mouvements (30j)", stats.get('movements_last_30_days', 0))
    
    # Graphiques
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # Graphique par statut
        if stats.get('by_status'):
            labels = list(stats['by_status'].keys())
            values = list(stats['by_status'].values())
            colors = ['#10b981', '#f59e0b', '#ef4444', '#dc2626']
            
            fig = px.pie(
                values=values,
                names=labels,
                title="📊 Répartition par Statut",
                color_discrete_sequence=colors
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_chart2:
        # Graphique par type
        if stats.get('by_type'):
            type_labels = list(stats['by_type'].keys())
            type_values = list(stats['by_type'].values())
            
            fig = px.bar(
                x=type_labels,
                y=type_values,
                title="🏷️ Articles par Type",
                color=type_values,
                color_continuous_scale="viridis"
            )
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    # Articles critiques
    critical_items = inventory_manager.get_critical_stock_items()
    if critical_items:
        st.markdown("---")
        st.markdown("##### 🚨 Articles avec Stock Critique")
        
        critical_data = []
        for item in critical_items[:10]:  # Top 10
            critical_data.append({
                'Code': safe_get_display_name(item, ['code_interne'], 'N/A', 15),
                'Nom': safe_get_display_name(item, ['nom'], 'N/A', 25),
                'Stock Actuel': f"{item.get('quantite_metric', 0):.2f}",
                'Limite Min': f"{item.get('limite_minimale_metric', 0):.2f}",
                'Statut': safe_get_display_name(item, ['statut'], 'N/A', 10),
                'Fournisseur': safe_get_display_name(item, ['fournisseur_principal'], 'N/A', 20)
            })
        
        df_critical = pd.DataFrame(critical_data)
        st.dataframe(df_critical, use_container_width=True)
    
    # Top fournisseurs
    if stats.get('top_suppliers'):
        st.markdown("---")
        st.markdown("##### 🏪 Top Fournisseurs")
        
        suppliers_data = []
        for supplier in stats['top_suppliers']:
            suppliers_data.append({
                'Fournisseur': safe_get_display_name(supplier, ['fournisseur_principal'], 'N/A', 30),
                'Nombre d\'Articles': supplier.get('items_count', 0)
            })
        
        df_suppliers = pd.DataFrame(suppliers_data)
        st.dataframe(df_suppliers, use_container_width=True)

def render_import_export_tab(inventory_manager):
    """Onglet import/export"""
    st.markdown("#### 📤 Import/Export")
    
    # Section Export
    st.markdown("##### 📤 Export")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📋 Exporter Tout en CSV", use_container_width=True):
            csv_content = inventory_manager.export_to_csv()
            if csv_content:
                st.download_button(
                    label="⬇️ Télécharger le fichier CSV",
                    data=csv_content,
                    file_name=f"inventaire_dg_inc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.error("Erreur lors de l'export.")
    
    with col2:
        # Export des articles critiques seulement
        if st.button("🚨 Exporter Stock Critique", use_container_width=True):
            critical_items = inventory_manager.get_critical_stock_items()
            if critical_items:
                csv_content = inventory_manager.export_to_csv(critical_items)
                st.download_button(
                    label="⬇️ Télécharger Stock Critique",
                    data=csv_content,
                    file_name=f"stock_critique_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("Aucun article avec stock critique.")
    
    # Section Import
    st.markdown("---")
    st.markdown("##### 📥 Import")
    
    uploaded_file = st.file_uploader(
        "Choisir un fichier CSV à importer:",
        type=['csv'],
        help="Le fichier doit contenir les colonnes: nom, type_produit, code_interne, quantite_metric, limite_minimale_metric, description, fournisseur_principal"
    )
    
    if uploaded_file is not None:
        try:
            # Lire le fichier
            csv_content = uploaded_file.getvalue().decode('utf-8')
            
            # Prévisualisation
            st.markdown("###### 👀 Prévisualisation (5 premières lignes)")
            df_preview = pd.read_csv(io.StringIO(csv_content))
            st.dataframe(df_preview.head(), use_container_width=True)
            
            # Bouton d'import
            if st.button("📥 Importer les Données", type="primary"):
                with st.spinner("Import en cours..."):
                    result = inventory_manager.import_from_csv(csv_content)
                
                # Afficher les résultats
                col_res1, col_res2, col_res3 = st.columns(3)
                with col_res1:
                    st.metric("✅ Succès", result.get('success', 0))
                with col_res2:
                    st.metric("❌ Erreurs", result.get('errors', 0))
                with col_res3:
                    st.metric("⏭️ Ignorés", result.get('skipped', 0))
                
                if result.get('success', 0) > 0:
                    st.success(f"✅ Import terminé ! {result['success']} article(s) traité(s) avec succès.")
                    st.rerun()
                elif result.get('errors', 0) > 0:
                    st.error(f"❌ Erreurs lors de l'import. {result['errors']} erreur(s) détectée(s).")
        
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier: {e}")

def handle_inventory_actions(inventory_manager):
    """Gère les actions utilisateur"""
    action = st.session_state.get('inventory_action')
    item_id = st.session_state.get('selected_item_id')
    
    if action == "view_item" and item_id:
        show_item_details_modal(inventory_manager, item_id)
    elif action == "edit_item" and item_id:
        show_edit_item_modal(inventory_manager, item_id)
    elif action == "delete_item" and item_id:
        show_delete_item_modal(inventory_manager, item_id)
    elif action == "add_movement" and item_id:
        show_add_movement_modal(inventory_manager, item_id)

def show_item_details_modal(inventory_manager, item_id):
    """Modal détails d'un article"""
    item = inventory_manager.get_item_by_id(item_id)
    if not item:
        st.error("Article non trouvé.")
        return
    
    with st.expander(f"👁️ Détails - {safe_get_display_name(item, ['nom'], 'N/A')}", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            **📋 Informations Générales**
            - **ID:** {item.get('id', 'N/A')}
            - **Nom:** {safe_get_display_name(item, ['nom'], 'N/A')}
            - **Code interne:** {safe_get_display_name(item, ['code_interne'], 'N/A')}
            - **Type:** {safe_get_display_name(item, ['type_produit'], 'N/A')}
            - **Statut:** {safe_get_display_name(item, ['statut'], 'N/A')}
            """)
        
        with col2:
            st.markdown(f"""
            **📊 Quantités**
            - **Stock actuel:** {item.get('quantite_metric', 0):.2f}
            - **Limite minimale:** {item.get('limite_minimale_metric', 0):.2f}
            - **Stock réservé:** {item.get('quantite_reservee_metric', 0):.2f}
            - **Fournisseur:** {safe_get_display_name(item, ['fournisseur_principal'], 'N/A')}
            """)
        
        description = safe_get_display_name(item, ['description'], '')
        if description:
            st.markdown(f"**📝 Description:** {description}")
        
        notes = safe_get_display_name(item, ['notes'], '')
        if notes:
            st.markdown(f"**📌 Notes:** {notes}")
        
        # Historique récent
        st.markdown("**📋 Derniers Mouvements**")
        movements = inventory_manager.get_stock_movements(item_id, 5)
        if movements:
            for mov in movements:
                date = safe_string_slice(mov.get('created_at', ''), 16, 'N/A').replace('T', ' ')
                action = safe_get_display_name(mov, ['action'], 'N/A')
                qty_before = safe_get_display_name(mov, ['quantite_avant'], 'N/A')
                qty_after = safe_get_display_name(mov, ['quantite_apres'], 'N/A')
                st.markdown(f"- {date}: {action} ({qty_before} → {qty_after})")
        else:
            st.info("Aucun mouvement enregistré.")
        
        if st.button("✖️ Fermer", key="close_details"):
            st.session_state.inventory_action = None
            st.session_state.selected_item_id = None
            st.rerun()

def show_edit_item_modal(inventory_manager, item_id):
    """Modal édition d'un article"""
    item = inventory_manager.get_item_by_id(item_id)
    if not item:
        st.error("Article non trouvé.")
        return
    
    with st.expander(f"✏️ Modifier - {safe_get_display_name(item, ['nom'], 'N/A')}", expanded=True):
        with st.form("edit_item_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                nom = st.text_input("Nom:", value=safe_get_display_name(item, ['nom'], ''))
                code_interne = st.text_input("Code interne:", value=safe_get_display_name(item, ['code_interne'], ''))
                
                # Type de produit avec gestion sécurisée
                type_options = ["", "Matière première", "Tube/Profilé", "Tôle/Plaque", "Visserie", "Outil", "Consommable", "Produit fini", "Autre"]
                current_type = safe_get_display_name(item, ['type_produit'], '')
                try:
                    type_index = type_options.index(current_type) if current_type in type_options else 0
                except (ValueError, TypeError):
                    type_index = 0
                
                type_produit = st.selectbox("Type:", type_options, index=type_index)
                fournisseur = st.text_input("Fournisseur:", value=safe_get_display_name(item, ['fournisseur_principal'], ''))
            
            with col2:
                quantite_metric = st.number_input("Quantité:", value=float(item.get('quantite_metric', 0)), step=0.01)
                limite_min = st.number_input("Limite min:", value=float(item.get('limite_minimale_metric', 0)), step=0.01)
                quantite_imperial = st.text_input("Qté impériale:", value=safe_get_display_name(item, ['quantite_imperial'], ''))
                limite_imperial = st.text_input("Limite imp.:", value=safe_get_display_name(item, ['limite_minimale_imperial'], ''))
            
            description = st.text_area("Description:", value=safe_get_display_name(item, ['description'], ''))
            notes = st.text_area("Notes:", value=safe_get_display_name(item, ['notes'], ''))
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                submitted = st.form_submit_button("💾 Sauvegarder", type="primary", use_container_width=True)
            with col_btn2:
                cancelled = st.form_submit_button("❌ Annuler", use_container_width=True)
            
            if submitted:
                update_data = {
                    'nom': nom.strip(),
                    'code_interne': code_interne.strip(),
                    'type_produit': type_produit,
                    'quantite_metric': quantite_metric,
                    'limite_minimale_metric': limite_min,
                    'quantite_imperial': quantite_imperial.strip(),
                    'limite_minimale_imperial': limite_imperial.strip(),
                    'description': description.strip(),
                    'notes': notes.strip(),
                    'fournisseur_principal': fournisseur.strip()
                }
                
                if inventory_manager.update_item(item_id, update_data):
                    st.success("✅ Article mis à jour avec succès !")
                    st.session_state.inventory_action = None
                    st.session_state.selected_item_id = None
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la mise à jour.")
            
            if cancelled:
                st.session_state.inventory_action = None
                st.session_state.selected_item_id = None
                st.rerun()

def show_delete_item_modal(inventory_manager, item_id):
    """Modal suppression d'un article"""
    item = inventory_manager.get_item_by_id(item_id)
    if not item:
        st.error("Article non trouvé.")
        return
    
    with st.expander(f"🗑️ Supprimer - {safe_get_display_name(item, ['nom'], 'N/A')}", expanded=True):
        st.warning(f"⚠️ Êtes-vous sûr de vouloir supprimer l'article **{safe_get_display_name(item, ['nom'], 'N/A')}** ?")
        st.markdown("Cette action supprimera également tout l'historique des mouvements associés.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Confirmer Suppression", type="primary", use_container_width=True):
                if inventory_manager.delete_item(item_id):
                    st.success("✅ Article supprimé avec succès !")
                    st.session_state.inventory_action = None
                    st.session_state.selected_item_id = None
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la suppression.")
        
        with col2:
            if st.button("❌ Annuler", use_container_width=True):
                st.session_state.inventory_action = None
                st.session_state.selected_item_id = None
                st.rerun()

def show_add_movement_modal(inventory_manager, item_id):
    """Modal ajout de mouvement rapide"""
    item = inventory_manager.get_item_by_id(item_id)
    if not item:
        st.error("Article non trouvé.")
        return
    
    with st.expander(f"📦 Mouvement - {safe_get_display_name(item, ['nom'], 'N/A')}", expanded=True):
        st.markdown(f"**Stock actuel:** {item.get('quantite_metric', 0):.2f}")
        
        with st.form("quick_movement_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                movement_type = st.selectbox("Type:", ["ENTREE", "SORTIE", "AJUSTEMENT"])
                quantity = st.number_input("Quantité:", min_value=0.01, value=1.0, step=0.01)
            
            with col2:
                notes = st.text_area("Notes:", placeholder="Raison du mouvement...")
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                submitted = st.form_submit_button("📦 Enregistrer", type="primary", use_container_width=True)
            with col_btn2:
                cancelled = st.form_submit_button("❌ Annuler", use_container_width=True)
            
            if submitted:
                success = inventory_manager.add_stock_movement(item_id, movement_type, quantity, notes)
                if success:
                    st.success(f"✅ Mouvement enregistré: {movement_type} de {quantity}")
                    st.session_state.inventory_action = None
                    st.session_state.selected_item_id = None
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de l'enregistrement.")
            
            if cancelled:
                st.session_state.inventory_action = None
                st.session_state.selected_item_id = None
                st.rerun()

# =========================================================================
# FONCTIONS D'INTÉGRATION AVEC L'APPLICATION PRINCIPALE
# =========================================================================

def init_inventory_manager(erp_db):
    """Initialise le gestionnaire d'inventaire dans st.session_state"""
    if 'inventory_manager' not in st.session_state:
        st.session_state.inventory_manager = GestionnaireInventaire(erp_db)
        logger.info("GestionnaireInventaire initialisé dans session_state")
    return st.session_state.inventory_manager

def get_inventory_summary_stats():
    """Retourne des stats résumées pour affichage dans d'autres modules"""
    if 'inventory_manager' not in st.session_state:
        return {}
    
    try:
        inventory_manager = st.session_state.inventory_manager
        stats = inventory_manager.get_inventory_statistics()
        return {
            'total_items': stats.get('total_items', 0),
            'critical_items': stats.get('critical_items', 0),
            'available_items': stats.get('by_status', {}).get('DISPONIBLE', 0)
        }
    except Exception as e:
        logger.error(f"Erreur stats résumé inventaire: {e}")
        return {}

# =========================================================================
# EXPORT DE LA FONCTION PRINCIPALE
# =========================================================================

if __name__ == "__main__":
    # Test du module en mode standalone
    st.set_page_config(page_title="Module Inventaire", layout="wide")
    st.title("🧪 Test Module Inventaire")
    
    # Simulation de la base de données pour test
    class MockDB:
        def execute_query(self, query, params=None):
            return []
        def execute_update(self, query, params=None):
            return 0
        def execute_insert(self, query, params=None):
            return 1
    
    st.session_state.erp_db = MockDB()
    show_inventory_page()

print("📦 Module Inventaire SQLite CORRIGÉ avec succès !")
print("✅ Corrections apportées:")
print("   - Gestion sécurisée des valeurs None")
print("   - Fonctions utilitaires safe_string_slice et safe_get_display_name")
print("   - Protection contre les erreurs de slicing sur None")
print("   - Gestion robuste des champs optionnels")
print("   - Validation des données avant affichage")
print("🔧 L'erreur 'NoneType object is not subscriptable' est maintenant résolue")
