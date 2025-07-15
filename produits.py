import streamlit as st
import pandas as pd
from datetime import datetime
import json
from typing import Dict, List, Optional, Any

# Constantes pour les produits métallurgiques (migrées depuis crm.py)
CATEGORIES_PRODUITS = ["Acier", "Aluminium", "Inox", "Cuivre", "Laiton", "Autres métaux", "Fournitures", "Services"]
UNITES_VENTE = ["kg", "tonne", "m", "m²", "m³", "pièce", "lot", "heure"]
NUANCES_MATERIAUX = {
    "Acier": ["S235", "S355", "S460", "42CrMo4", "25CrMo4", "Autres"],
    "Aluminium": ["6061-T6", "6063-T5", "2024-T3", "7075-T6", "5083", "Autres"],
    "Inox": ["304L", "316L", "321", "410", "430", "Duplex", "Autres"],
    "Cuivre": ["Cu-ETP", "Cu-DHP", "CuZn37", "CuSn8", "Autres"],
    "Autres": ["Standard", "Spécial", "Sur mesure"]
}

class GestionnaireProduits:
    """
    Gestionnaire dédié au catalogue de produits, stock, et prix.
    """
    
    def __init__(self, db):
        self.db = db
        self.use_sqlite = db is not None
        
        if not self.use_sqlite:
            # Mode rétrocompatibilité JSON
            self.data_file = "produits_data.json"
            self._produits = []
            self.next_produit_id = 1
            self.charger_donnees_produits()
        else:
            # Mode SQLite unifié
            self._init_products_table()
    
    def _init_products_table(self):
        """Initialise la table des produits si elle n'existe pas"""
        if not self.use_sqlite:
            return
        
        try:
            # Vérifier si la table produits existe
            tables = self.db.execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name='produits'")
            
            if not tables:
                # Créer la table produits
                create_table_query = '''
                CREATE TABLE produits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code_produit TEXT UNIQUE NOT NULL,
                    nom TEXT NOT NULL,
                    description TEXT,
                    categorie TEXT NOT NULL,
                    materiau TEXT,
                    nuance TEXT,
                    dimensions TEXT,
                    unite_vente TEXT NOT NULL DEFAULT 'kg',
                    prix_unitaire REAL NOT NULL DEFAULT 0.0,
                    stock_disponible REAL DEFAULT 0.0,
                    stock_minimum REAL DEFAULT 0.0,
                    stock_reserve REAL DEFAULT 0.0,
                    stock_en_commande REAL DEFAULT 0.0,
                    point_commande REAL DEFAULT 0.0,
                    lot_commande REAL DEFAULT 0.0,
                    delai_approvisionnement INTEGER DEFAULT 0,
                    fournisseur_principal TEXT,
                    notes_techniques TEXT,
                    emplacement_stock TEXT,
                    date_dernier_inventaire DATE,
                    actif BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                '''
                self.db.execute_update(create_table_query)
                st.success("✅ Table 'produits' créée avec succès")
                
                # Ajouter des données de démonstration
                self._create_demo_products()
            else:
                # Vérifier et ajouter les colonnes manquantes si nécessaire
                self._check_and_add_inventory_columns()
                
                # Vérifier si des produits existent, sinon ajouter démo
                count_result = self.db.execute_query("SELECT COUNT(*) as count FROM produits")
                if count_result[0]['count'] == 0:
                    self._create_demo_products()
                    
        except Exception as e:
            st.error(f"Erreur lors de l'initialisation de la table produits: {e}")
    
    def _check_and_add_inventory_columns(self):
        """Vérifie et ajoute les colonnes d'inventaire si elles n'existent pas"""
        try:
            # Vérifier les colonnes existantes
            columns_info = self.db.execute_query("PRAGMA table_info(produits)")
            existing_columns = [col['name'] for col in columns_info]
            
            # Colonnes d'inventaire à ajouter
            inventory_columns = {
                'stock_reserve': 'REAL DEFAULT 0.0',
                'stock_en_commande': 'REAL DEFAULT 0.0',
                'point_commande': 'REAL DEFAULT 0.0',
                'lot_commande': 'REAL DEFAULT 0.0',
                'delai_approvisionnement': 'INTEGER DEFAULT 0',
                'emplacement_stock': 'TEXT',
                'date_dernier_inventaire': 'DATE'
            }
            
            # Ajouter les colonnes manquantes
            for column_name, column_type in inventory_columns.items():
                if column_name not in existing_columns:
                    self.db.execute_update(f"ALTER TABLE produits ADD COLUMN {column_name} {column_type}")
                    
        except Exception as e:
            # Ne pas bloquer si certaines colonnes existent déjà
            pass

    def _create_demo_products(self):
        """Crée des produits de démonstration pour la métallurgie"""
        if not self.use_sqlite:
            return
        
        try:
            produits_demo = [
                {
                    'code_produit': 'AC-PLT-001',
                    'nom': 'Plaque Acier S235',
                    'description': 'Plaque d\'acier de construction standard',
                    'categorie': 'Acier',
                    'materiau': 'Acier',
                    'nuance': 'S235',
                    'dimensions': '2000x1000x10mm',
                    'unite_vente': 'kg',
                    'prix_unitaire': 2.50,
                    'stock_disponible': 150.0,
                    'stock_minimum': 50.0,
                    'fournisseur_principal': 'ArcelorMittal',
                    'notes_techniques': 'Limite élastique: 235 MPa. Soudable.',
                    'actif': 1
                },
                {
                    'code_produit': 'AL-TUB-002',
                    'nom': 'Tube Aluminium 6061-T6',
                    'description': 'Tube rond en aluminium traité thermiquement',
                    'categorie': 'Aluminium',
                    'materiau': 'Aluminium',
                    'nuance': '6061-T6',
                    'dimensions': 'Ø50x3mm',
                    'unite_vente': 'm',
                    'prix_unitaire': 15.80,
                    'stock_disponible': 85.0,
                    'stock_minimum': 20.0,
                    'fournisseur_principal': 'Hydro Aluminium',
                    'notes_techniques': 'Excellente résistance à la corrosion. Usinable.',
                    'actif': 1
                },
                {
                    'code_produit': 'INX-BAR-003',
                    'nom': 'Barre Inox 316L',
                    'description': 'Barre ronde en acier inoxydable 316L',
                    'categorie': 'Inox',
                    'materiau': 'Inox',
                    'nuance': '316L',
                    'dimensions': 'Ø20mm',
                    'unite_vente': 'm',
                    'prix_unitaire': 28.50,
                    'stock_disponible': 45.0,
                    'stock_minimum': 10.0,
                    'fournisseur_principal': 'Aperam',
                    'notes_techniques': 'Résistant aux acides. Qualité alimentaire.',
                    'actif': 1
                },
                {
                    'code_produit': 'SRV-DEC-001',
                    'nom': 'Découpe Laser',
                    'description': 'Service de découpe laser précise',
                    'categorie': 'Services',
                    'materiau': 'Service',
                    'nuance': 'Standard',
                    'dimensions': 'Variable',
                    'unite_vente': 'heure',
                    'prix_unitaire': 125.00,
                    'stock_disponible': 0.0,
                    'stock_minimum': 0.0,
                    'fournisseur_principal': 'Interne',
                    'notes_techniques': 'Précision +/- 0.1mm. Épaisseur max: 25mm.',
                    'actif': 1
                },
                {
                    'code_produit': 'CU-FIL-004',
                    'nom': 'Fil Cuivre Cu-ETP',
                    'description': 'Fil de cuivre électrolytique pur',
                    'categorie': 'Cuivre',
                    'materiau': 'Cuivre',
                    'nuance': 'Cu-ETP',
                    'dimensions': 'Ø8mm',
                    'unite_vente': 'kg',
                    'prix_unitaire': 12.80,
                    'stock_disponible': 25.0,
                    'stock_minimum': 5.0,
                    'fournisseur_principal': 'Aurubis',
                    'notes_techniques': 'Conductivité électrique: 58 MS/m min.',
                    'actif': 1
                }
            ]
            
            for produit in produits_demo:
                query = '''
                INSERT INTO produits 
                (code_produit, nom, description, categorie, materiau, nuance, dimensions,
                 unite_vente, prix_unitaire, stock_disponible, stock_minimum, 
                 fournisseur_principal, notes_techniques, actif)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                
                self.db.execute_insert(query, (
                    produit['code_produit'],
                    produit['nom'],
                    produit['description'],
                    produit['categorie'],
                    produit['materiau'],
                    produit['nuance'],
                    produit['dimensions'],
                    produit['unite_vente'],
                    produit['prix_unitaire'],
                    produit['stock_disponible'],
                    produit['stock_minimum'],
                    produit['fournisseur_principal'],
                    produit['notes_techniques'],
                    produit['actif']
                ))
            
            st.info("✅ Produits de démonstration métallurgiques créés")
            
        except Exception as e:
            st.error(f"Erreur création produits démo: {e}")

    @property
    def produits(self):
        """Propriété pour maintenir compatibilité avec l'interface existante"""
        if self.use_sqlite:
            return self.get_all_products()
        else:
            return getattr(self, '_produits', [])
    
    @produits.setter
    def produits(self, value):
        if not self.use_sqlite:
            self._produits = value

    def get_all_products(self):
        """Récupère tous les produits depuis SQLite"""
        if not self.use_sqlite:
            return getattr(self, '_produits', [])
        
        try:
            rows = self.db.execute_query('''
                SELECT * FROM produits 
                WHERE actif = 1 
                ORDER BY categorie, nom
            ''')
            
            return [dict(row) for row in rows]
        except Exception as e:
            st.error(f"Erreur récupération produits: {e}")
            return []

    def ajouter_produit(self, data_produit):
        """Ajoute un nouveau produit en SQLite"""
        if not self.use_sqlite:
            return self._ajouter_produit_json(data_produit)
        
        try:
            query = '''
                INSERT INTO produits 
                (code_produit, nom, description, categorie, materiau, nuance, dimensions,
                 unite_vente, prix_unitaire, stock_disponible, stock_minimum, 
                 fournisseur_principal, notes_techniques, actif)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            produit_id = self.db.execute_insert(query, (
                data_produit.get('code_produit'),
                data_produit.get('nom'),
                data_produit.get('description'),
                data_produit.get('categorie'),
                data_produit.get('materiau'),
                data_produit.get('nuance'),
                data_produit.get('dimensions'),
                data_produit.get('unite_vente', 'kg'),
                data_produit.get('prix_unitaire', 0.0),
                data_produit.get('stock_disponible', 0.0),
                data_produit.get('stock_minimum', 0.0),
                data_produit.get('fournisseur_principal'),
                data_produit.get('notes_techniques'),
                1  # actif par défaut
            ))
            
            if produit_id:
                st.success(f"✅ Produit créé avec l'ID #{produit_id}")
            
            return produit_id
            
        except Exception as e:
            st.error(f"Erreur ajout produit: {e}")
            return None

    def modifier_produit(self, id_produit, data_produit):
        """Modifie un produit existant en SQLite"""
        if not self.use_sqlite:
            return self._modifier_produit_json(id_produit, data_produit)
        
        try:
            # Construire la requête dynamiquement
            update_fields = []
            params = []
            
            field_mapping = {
                'code_produit': 'code_produit',
                'nom': 'nom',
                'description': 'description',
                'categorie': 'categorie',
                'materiau': 'materiau',
                'nuance': 'nuance',
                'dimensions': 'dimensions',
                'unite_vente': 'unite_vente',
                'prix_unitaire': 'prix_unitaire',
                'stock_disponible': 'stock_disponible',
                'stock_minimum': 'stock_minimum',
                'fournisseur_principal': 'fournisseur_principal',
                'notes_techniques': 'notes_techniques',
                'actif': 'actif'
            }
            
            for field, db_field in field_mapping.items():
                if field in data_produit:
                    update_fields.append(f"{db_field} = ?")
                    params.append(data_produit[field])
            
            if update_fields:
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                params.append(id_produit)
                
                query = f"UPDATE produits SET {', '.join(update_fields)} WHERE id = ?"
                rows_affected = self.db.execute_update(query, tuple(params))
                
                if rows_affected > 0:
                    st.success(f"✅ Produit #{id_produit} mis à jour")
                
                return rows_affected > 0
            
            return False
            
        except Exception as e:
            st.error(f"Erreur modification produit: {e}")
            return False

    def supprimer_produit(self, id_produit, suppression_definitive=False):
        """Supprime un produit (logique par défaut, physique si spécifié)"""
        if not self.use_sqlite:
            return self._supprimer_produit_json(id_produit)
        
        try:
            if suppression_definitive:
                # Suppression physique
                rows_affected = self.db.execute_update("DELETE FROM produits WHERE id = ?", (id_produit,))
                st.success("✅ Produit supprimé définitivement")
            else:
                # Suppression logique (marquer comme inactif)
                rows_affected = self.db.execute_update(
                    "UPDATE produits SET actif = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                    (id_produit,)
                )
                st.success("✅ Produit désactivé")
            
            return rows_affected > 0
            
        except Exception as e:
            st.error(f"Erreur suppression produit: {e}")
            return False

    def get_produit_by_id(self, id_produit):
        """Récupère un produit par son ID"""
        if not self.use_sqlite:
            return next((p for p in getattr(self, '_produits', []) if p.get('id') == id_produit), None)
        
        try:
            rows = self.db.execute_query("SELECT * FROM produits WHERE id = ?", (id_produit,))
            if rows:
                return dict(rows[0])
            return None
        except Exception as e:
            st.error(f"Erreur récupération produit {id_produit}: {e}")
            return None

    def get_produits_by_categorie(self, categorie):
        """Récupère tous les produits d'une catégorie"""
        if not self.use_sqlite:
            return [p for p in getattr(self, '_produits', []) if p.get('categorie') == categorie]
        
        try:
            rows = self.db.execute_query(
                "SELECT * FROM produits WHERE categorie = ? AND actif = 1 ORDER BY nom", 
                (categorie,)
            )
            return [dict(row) for row in rows]
        except Exception as e:
            st.error(f"Erreur récupération produits catégorie {categorie}: {e}")
            return []

    def search_produits(self, terme_recherche):
        """Recherche de produits par terme"""
        if not self.use_sqlite:
            terme = terme_recherche.lower()
            return [p for p in getattr(self, '_produits', []) 
                   if terme in p.get('nom', '').lower() or 
                      terme in p.get('code_produit', '').lower() or
                      terme in p.get('description', '').lower()]
        
        try:
            query = '''
                SELECT * FROM produits 
                WHERE actif = 1 AND (
                    LOWER(nom) LIKE ? OR 
                    LOWER(code_produit) LIKE ? OR 
                    LOWER(description) LIKE ? OR
                    LOWER(materiau) LIKE ?
                )
                ORDER BY nom
            '''
            terme = f"%{terme_recherche.lower()}%"
            rows = self.db.execute_query(query, (terme, terme, terme, terme))
            return [dict(row) for row in rows]
        except Exception as e:
            st.error(f"Erreur recherche produits: {e}")
            return []

    def get_produits_stock_bas(self):
        """Récupère les produits avec un stock bas"""
        if not self.use_sqlite:
            return [p for p in getattr(self, '_produits', []) 
                   if p.get('stock_disponible', 0) <= p.get('stock_minimum', 0)]
        
        try:
            rows = self.db.execute_query('''
                SELECT * FROM produits 
                WHERE actif = 1 AND stock_disponible <= stock_minimum
                ORDER BY (stock_disponible - stock_minimum)
            ''')
            return [dict(row) for row in rows]
        except Exception as e:
            st.error(f"Erreur récupération stock bas: {e}")
            return []

    def ajuster_stock_produit(self, id_produit, nouvelle_quantite, motif="Ajustement manuel", employee_id=None):
        """Ajuste le stock d'un produit avec traçabilité"""
        if not self.use_sqlite:
            # En mode JSON, mise à jour directe
            for p in getattr(self, '_produits', []):
                if p.get('id') == id_produit:
                    p['stock_disponible'] = nouvelle_quantite
                    self.sauvegarder_donnees_produits()
                    return True
            return False
        
        try:
            # Utiliser la méthode de traçabilité de la base de données
            mouvement_id = self.db.enregistrer_mouvement_stock({
                'produit_id': id_produit,
                'type_mouvement': 'AJUSTEMENT',
                'quantite': nouvelle_quantite,
                'motif': motif,
                'employee_id': employee_id,
                'reference_type': 'AJUSTEMENT'
            })
            
            return mouvement_id is not None
            
        except Exception as e:
            st.error(f"Erreur ajustement stock: {e}")
            return False
    
    def get_stock_complet(self, produit_id):
        """Récupère toutes les informations de stock d'un produit"""
        if not self.use_sqlite:
            return None
        
        try:
            query = '''
                SELECT p.*,
                       (p.stock_disponible - COALESCE(
                           (SELECT SUM(quantite_reservee) 
                            FROM reservations_stock 
                            WHERE produit_id = p.id AND statut = 'ACTIVE'), 0)
                       ) as stock_libre,
                       COALESCE(
                           (SELECT SUM(quantite_reservee) 
                            FROM reservations_stock 
                            WHERE produit_id = p.id AND statut = 'ACTIVE'), 0
                       ) as total_reserve
                FROM produits p
                WHERE p.id = ?
            '''
            result = self.db.execute_query(query, (produit_id,))
            return result[0] if result else None
            
        except Exception as e:
            st.error(f"Erreur récupération stock complet: {e}")
            return None
    
    def entree_stock(self, produit_id, quantite, reference_document=None, cout_unitaire=None, employee_id=None):
        """Enregistre une entrée de stock (réception)"""
        if not self.use_sqlite:
            return False
        
        try:
            cout_total = (cout_unitaire * quantite) if cout_unitaire else None
            
            mouvement_id = self.db.enregistrer_mouvement_stock({
                'produit_id': produit_id,
                'type_mouvement': 'ENTREE',
                'quantite': quantite,
                'reference_document': reference_document,
                'reference_type': 'BON_RECEPTION',
                'cout_unitaire': cout_unitaire,
                'cout_total': cout_total,
                'employee_id': employee_id,
                'motif': 'Réception marchandise'
            })
            
            return mouvement_id is not None
            
        except Exception as e:
            st.error(f"Erreur entrée stock: {e}")
            return False
    
    def sortie_stock(self, produit_id, quantite, reference_document=None, motif=None, employee_id=None):
        """Enregistre une sortie de stock"""
        if not self.use_sqlite:
            return False
        
        try:
            # Vérifier la disponibilité
            stock = self.get_stock_complet(produit_id)
            if not stock or stock['stock_libre'] < quantite:
                st.error("Stock insuffisant pour cette sortie")
                return False
            
            mouvement_id = self.db.enregistrer_mouvement_stock({
                'produit_id': produit_id,
                'type_mouvement': 'SORTIE',
                'quantite': quantite,
                'reference_document': reference_document,
                'reference_type': 'BON_LIVRAISON',
                'employee_id': employee_id,
                'motif': motif or 'Sortie stock'
            })
            
            return mouvement_id is not None
            
        except Exception as e:
            st.error(f"Erreur sortie stock: {e}")
            return False
    
    def reserver_stock(self, produit_id, quantite, reference_document, reference_type='AUTRE', notes=None, employee_id=None):
        """Réserve du stock pour un document"""
        if not self.use_sqlite:
            return None
        
        try:
            reservation_id = self.db.reserver_stock({
                'produit_id': produit_id,
                'quantite_reservee': quantite,
                'reference_document': reference_document,
                'reference_type': reference_type,
                'notes': notes,
                'created_by': employee_id
            })
            
            return reservation_id
            
        except Exception as e:
            st.error(f"Erreur réservation stock: {e}")
            return None
    
    def get_historique_mouvements(self, produit_id):
        """Récupère l'historique des mouvements d'un produit"""
        if not self.use_sqlite:
            return []
        
        try:
            return self.db.get_mouvements_stock(produit_id=produit_id, limit=50)
        except Exception as e:
            st.error(f"Erreur récupération historique: {e}")
            return []
    
    def get_reservations_actives(self, produit_id=None):
        """Récupère les réservations actives"""
        if not self.use_sqlite:
            return []
        
        try:
            if produit_id:
                query = '''
                    SELECT r.*, p.code_produit, p.nom as produit_nom
                    FROM reservations_stock r
                    JOIN produits p ON r.produit_id = p.id
                    WHERE r.statut = 'ACTIVE' AND r.produit_id = ?
                    ORDER BY r.date_reservation DESC
                '''
                return self.db.execute_query(query, (produit_id,))
            else:
                query = '''
                    SELECT r.*, p.code_produit, p.nom as produit_nom
                    FROM reservations_stock r
                    JOIN produits p ON r.produit_id = p.id
                    WHERE r.statut = 'ACTIVE'
                    ORDER BY r.date_reservation DESC
                '''
                return self.db.execute_query(query)
                
        except Exception as e:
            st.error(f"Erreur récupération réservations: {e}")
            return []
    
    def get_analyse_inventaire(self):
        """Récupère l'analyse complète de l'inventaire"""
        if not self.use_sqlite:
            return {}
        
        try:
            return self.db.get_stock_analysis()
        except Exception as e:
            st.error(f"Erreur analyse inventaire: {e}")
            return {}

    def get_statistics_produits(self):
        """Statistiques des produits"""
        if not self.use_sqlite:
            produits = getattr(self, '_produits', [])
            total = len(produits)
            by_category = {}
            total_value = 0
            low_stock = 0
            
            for p in produits:
                cat = p.get('categorie', 'Autres')
                by_category[cat] = by_category.get(cat, 0) + 1
                total_value += p.get('stock_disponible', 0) * p.get('prix_unitaire', 0)
                if p.get('stock_disponible', 0) <= p.get('stock_minimum', 0):
                    low_stock += 1
            
            return {
                'total_produits': total,
                'par_categorie': by_category,
                'valeur_stock_total': total_value,
                'produits_stock_bas': low_stock
            }
        
        try:
            stats = {}
            
            # Total produits actifs
            total_result = self.db.execute_query("SELECT COUNT(*) as count FROM produits WHERE actif = 1")
            stats['total_produits'] = total_result[0]['count'] if total_result else 0
            
            # Par catégorie
            cat_result = self.db.execute_query('''
                SELECT categorie, COUNT(*) as count 
                FROM produits 
                WHERE actif = 1 
                GROUP BY categorie 
                ORDER BY count DESC
            ''')
            stats['par_categorie'] = {row['categorie']: row['count'] for row in cat_result}
            
            # Valeur totale du stock
            value_result = self.db.execute_query('''
                SELECT SUM(stock_disponible * prix_unitaire) as valeur_totale 
                FROM produits 
                WHERE actif = 1
            ''')
            stats['valeur_stock_total'] = value_result[0]['valeur_totale'] if value_result and value_result[0]['valeur_totale'] else 0
            
            # Produits en stock bas
            low_stock_result = self.db.execute_query('''
                SELECT COUNT(*) as count 
                FROM produits 
                WHERE actif = 1 AND stock_disponible <= stock_minimum
            ''')
            stats['produits_stock_bas'] = low_stock_result[0]['count'] if low_stock_result else 0
            
            return stats
            
        except Exception as e:
            st.error(f"Erreur statistiques produits: {e}")
            return {}

    # Méthodes JSON pour rétrocompatibilité
    def charger_donnees_produits(self):
        """Charge les données produits depuis JSON (rétrocompatibilité)"""
        if self.use_sqlite:
            return
        
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._produits = data.get('produits', [])
                    self.next_produit_id = self._get_next_id(self._produits)
            else:
                self._initialiser_donnees_demo_produits()
        except Exception as e:
            st.error(f"Erreur chargement données produits: {e}")
            self._initialiser_donnees_demo_produits()

    def _get_next_id(self, entity_list):
        """Utilitaire pour calculer le prochain ID"""
        if not entity_list:
            return 1
        return max(item.get('id', 0) for item in entity_list) + 1

    def _initialiser_donnees_demo_produits(self):
        """Initialise des données de démonstration produits JSON"""
        if self.use_sqlite:
            return
        
        now_iso = datetime.now().isoformat()
        self._produits = [
            {'id':1, 'code_produit':'AC-PLT-001', 'nom':'Plaque Acier S235', 'description':'Plaque d\'acier de construction standard', 'categorie':'Acier', 'materiau':'Acier', 'nuance':'S235', 'dimensions':'2000x1000x10mm', 'unite_vente':'kg', 'prix_unitaire':2.50, 'stock_disponible':150.0, 'stock_minimum':50.0, 'fournisseur_principal':'ArcelorMittal', 'notes_techniques':'Limite élastique: 235 MPa. Soudable.', 'actif':True, 'date_creation': now_iso, 'date_modification': now_iso},
            {'id':2, 'code_produit':'AL-TUB-002', 'nom':'Tube Aluminium 6061-T6', 'description':'Tube rond en aluminium traité thermiquement', 'categorie':'Aluminium', 'materiau':'Aluminium', 'nuance':'6061-T6', 'dimensions':'Ø50x3mm', 'unite_vente':'m', 'prix_unitaire':15.80, 'stock_disponible':85.0, 'stock_minimum':20.0, 'fournisseur_principal':'Hydro Aluminium', 'notes_techniques':'Excellente résistance à la corrosion. Usinable.', 'actif':True, 'date_creation': now_iso, 'date_modification': now_iso}
        ]
        
        self.next_produit_id = self._get_next_id(self._produits)
        self.sauvegarder_donnees_produits()

    def sauvegarder_donnees_produits(self):
        """Sauvegarde les données produits en JSON (rétrocompatibilité)"""
        if self.use_sqlite:
            return
        
        try:
            data = {
                'produits': self._produits,
                'next_produit_id': self.next_produit_id,
                'last_update': datetime.now().isoformat()
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            st.error(f"Erreur sauvegarde données produits: {e}")

    def _ajouter_produit_json(self, data_produit):
        data_produit['id'] = self.next_produit_id
        data_produit['date_creation'] = datetime.now().isoformat()
        data_produit['date_modification'] = datetime.now().isoformat()
        data_produit['actif'] = True
        self._produits.append(data_produit)
        self.next_produit_id += 1
        self.sauvegarder_donnees_produits()
        return data_produit['id']

    def _modifier_produit_json(self, id_produit, data_produit):
        for i, p in enumerate(self._produits):
            if p['id'] == id_produit:
                updated_produit = {**p, **data_produit, 'date_modification': datetime.now().isoformat()}
                self._produits[i] = updated_produit
                self.sauvegarder_donnees_produits()
                return True
        return False

    def _supprimer_produit_json(self, id_produit):
        # En mode JSON, suppression logique par défaut
        for p in self._produits:
            if p['id'] == id_produit:
                p['actif'] = False
                p['date_modification'] = datetime.now().isoformat()
                self.sauvegarder_donnees_produits()
                return True
        return False


# =========================================================================
# FONCTIONS D'AFFICHAGE STREAMLIT POUR PRODUITS (migrées et renommées)
# =========================================================================

def render_produits_tab(gestionnaire_produits: GestionnaireProduits):
    """Interface Streamlit pour la gestion des produits métallurgiques"""
    st.subheader("🔧 Catalogue des Produits")

    # Statistiques en haut
    stats = gestionnaire_produits.get_statistics_produits()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Produits", stats.get('total_produits', 0))
    with col2:
        st.metric("Stock Bas", stats.get('produits_stock_bas', 0))
    with col3:
        valeur_stock = stats.get('valeur_stock_total', 0.0)
        st.metric("Valeur Stock", f"{valeur_stock:,.0f} $")
    with col4:
        categories = len(stats.get('par_categorie', {}))
        st.metric("Catégories", categories)

    col_create_product, col_search_product = st.columns([1, 2])
    with col_create_product:
        if st.button("➕ Nouveau Produit", key="produit_create_btn", use_container_width=True):
            st.session_state.produit_action = "create_product"
            st.session_state.produit_selected_id = None

    with col_search_product:
        search_product_term = st.text_input("Rechercher un produit...", key="produit_search")

    # Filtres
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        filtre_categorie = st.selectbox("Filtrer par catégorie", 
                                      options=["Toutes"] + CATEGORIES_PRODUITS,
                                      key="filtre_categorie_produits")
    with col_filter2:
        filtre_stock_bas = st.checkbox("Afficher seulement stock bas", key="filtre_stock_bas")
    with col_filter3:
        st.write("")  # Espacement

    # Récupérer et filtrer les produits
    if search_product_term:
        filtered_products = gestionnaire_produits.search_produits(search_product_term)
    elif filtre_stock_bas:
        filtered_products = gestionnaire_produits.get_produits_stock_bas()
    elif filtre_categorie != "Toutes":
        filtered_products = gestionnaire_produits.get_produits_by_categorie(filtre_categorie)
    else:
        filtered_products = gestionnaire_produits.produits

    if filtered_products:
        products_data_display = []
        for produit in filtered_products:
            # Calcul de la valeur du stock
            valeur_stock = produit.get('stock_disponible', 0) * produit.get('prix_unitaire', 0)
            
            # Indicateur de stock
            stock_niveau = "🔴" if produit.get('stock_disponible', 0) <= produit.get('stock_minimum', 0) else "🟢"
            
            products_data_display.append({
                "ID": produit.get('id'),
                "Code": produit.get('code_produit'),
                "Nom": produit.get('nom'),
                "Catégorie": produit.get('categorie'),
                "Matériau/Nuance": f"{produit.get('materiau', '')}/{produit.get('nuance', '')}",
                "Dimensions": produit.get('dimensions'),
                "Prix Unit.": f"{produit.get('prix_unitaire', 0):.2f} $",
                "Stock": f"{stock_niveau} {produit.get('stock_disponible', 0)} {produit.get('unite_vente', '')}",
                "Valeur Stock": f"{valeur_stock:,.2f} $",
                "Fournisseur": produit.get('fournisseur_principal', 'N/A')
            })
        
        st.dataframe(pd.DataFrame(products_data_display), use_container_width=True)

        st.markdown("---")
        st.markdown("### 🔧 Actions sur un produit")
        selected_product_id_action = st.selectbox(
            "Produit:",
            options=[p['id'] for p in filtered_products],
            format_func=lambda pid: f"#{pid} - {next((p.get('code_produit', '') + ' - ' + p.get('nom', '') for p in filtered_products if p.get('id') == pid), '')}",
            key="produit_action_select"
        )

        if selected_product_id_action:
            col_act1, col_act2, col_act3, col_act4 = st.columns(4)
            with col_act1:
                if st.button("👁️ Voir Détails", key=f"view_product_{selected_product_id_action}", use_container_width=True):
                    st.session_state.produit_action = "view_product_details"
                    st.session_state.produit_selected_id = selected_product_id_action
            with col_act2:
                if st.button("✏️ Modifier", key=f"edit_product_{selected_product_id_action}", use_container_width=True):
                    st.session_state.produit_action = "edit_product"
                    st.session_state.produit_selected_id = selected_product_id_action
            with col_act3:
                if st.button("📦 Ajuster Stock", key=f"adjust_stock_{selected_product_id_action}", use_container_width=True):
                    st.session_state.produit_action = "adjust_stock"
                    st.session_state.produit_selected_id = selected_product_id_action
            with col_act4:
                if st.button("🗑️ Supprimer", key=f"delete_product_{selected_product_id_action}", use_container_width=True):
                    st.session_state.produit_confirm_delete_id = selected_product_id_action
    else:
        st.info("Aucun produit correspondant aux filtres." if search_product_term or filtre_stock_bas or filtre_categorie != "Toutes" else "Aucun produit enregistré.")

    # Gestion des confirmations de suppression
    if 'produit_confirm_delete_id' in st.session_state and st.session_state.produit_confirm_delete_id:
        product_to_delete = gestionnaire_produits.get_produit_by_id(st.session_state.produit_confirm_delete_id)
        if product_to_delete:
            st.warning(f"Êtes-vous sûr de vouloir supprimer le produit {product_to_delete.get('code_produit')} - {product_to_delete.get('nom')} ?")
            
            col_del_type = st.columns(1)[0]
            suppression_definitive = col_del_type.checkbox("Suppression définitive (ne peut pas être annulée)", key="suppression_definitive_product")
            
            col_del_confirm, col_del_cancel = st.columns(2)
            if col_del_confirm.button("Oui, supprimer ce produit", type="primary", key="confirm_delete_product_btn_final"):
                if gestionnaire_produits.supprimer_produit(st.session_state.produit_confirm_delete_id, suppression_definitive):
                    st.success("Produit supprimé avec succès.")
                else:
                    st.error("Erreur lors de la suppression.")
                del st.session_state.produit_confirm_delete_id
                st.rerun()
            if col_del_cancel.button("Annuler la suppression", key="cancel_delete_product_btn_final"):
                del st.session_state.produit_confirm_delete_id
                st.rerun()

def render_product_form(gestionnaire_produits: GestionnaireProduits, product_data=None):
    """Formulaire pour ajouter/modifier un produit"""
    form_title = "➕ Ajouter un Nouveau Produit" if product_data is None else f"✏️ Modifier le Produit #{product_data.get('id')}"
    
    with st.expander(form_title, expanded=True):
        with st.form(key="product_form_in_expander", clear_on_submit=False):
            # Ligne 1 : Informations de base
            col1, col2 = st.columns(2)
            with col1:
                code_produit = st.text_input("Code produit *", 
                                           value=product_data.get('code_produit', '') if product_data else "", 
                                           help="Code unique du produit")
                nom = st.text_input("Nom du produit *", 
                                  value=product_data.get('nom', '') if product_data else "")
                
                # Catégorie et matériau
                categorie = st.selectbox("Catégorie *", 
                                       options=CATEGORIES_PRODUITS,
                                       index=CATEGORIES_PRODUITS.index(product_data.get('categorie', CATEGORIES_PRODUITS[0])) if product_data and product_data.get('categorie') in CATEGORIES_PRODUITS else 0,
                                       key="product_form_categorie")
                
                # Matériau (basé sur la catégorie)
                materiau = st.text_input("Matériau", 
                                       value=product_data.get('materiau', '') if product_data else "",
                                       help="Type de matériau (ex: Acier, Aluminium)")

            with col2:
                description = st.text_area("Description", 
                                         value=product_data.get('description', '') if product_data else "",
                                         height=100)
                
                # Nuance (suggestions basées sur le matériau)
                materiau_selected = product_data.get('materiau', '') if product_data else ""
                nuances_disponibles = NUANCES_MATERIAUX.get(materiau_selected, NUANCES_MATERIAUX["Autres"])
                
                current_nuance = product_data.get('nuance', '') if product_data else ""
                if current_nuance and current_nuance not in nuances_disponibles:
                    nuances_disponibles = nuances_disponibles + [current_nuance]
                
                nuance = st.selectbox("Nuance", 
                                    options=nuances_disponibles,
                                    index=nuances_disponibles.index(current_nuance) if current_nuance in nuances_disponibles else 0,
                                    key="product_form_nuance")
                
                dimensions = st.text_input("Dimensions", 
                                         value=product_data.get('dimensions', '') if product_data else "",
                                         help="Ex: 2000x1000x10mm, Ø50x3mm")

            # Ligne 2 : Prix et stock
            col3, col4, col5 = st.columns(3)
            with col3:
                unite_vente = st.selectbox("Unité de vente *", 
                                         options=UNITES_VENTE,
                                         index=UNITES_VENTE.index(product_data.get('unite_vente', 'kg')) if product_data and product_data.get('unite_vente') in UNITES_VENTE else 0,
                                         key="product_form_unite")
                
                prix_unitaire = st.number_input("Prix unitaire * ($)", 
                                              min_value=0.0, 
                                              value=float(product_data.get('prix_unitaire', 0.0)) if product_data else 0.0,
                                              step=0.01, 
                                              format="%.2f")

            with col4:
                stock_disponible = st.number_input("Stock disponible", 
                                                 min_value=0.0, 
                                                 value=float(product_data.get('stock_disponible', 0.0)) if product_data else 0.0,
                                                 step=0.1, 
                                                 format="%.2f")
                
                stock_minimum = st.number_input("Stock minimum", 
                                              min_value=0.0, 
                                              value=float(product_data.get('stock_minimum', 0.0)) if product_data else 0.0,
                                              step=0.1, 
                                              format="%.2f")

            with col5:
                fournisseur_principal = st.text_input("Fournisseur principal", 
                                                    value=product_data.get('fournisseur_principal', '') if product_data else "")
                
                # Calculer la valeur du stock
                valeur_stock = stock_disponible * prix_unitaire
                st.metric("Valeur du stock", f"{valeur_stock:,.2f} $")

            # Ligne 3 : Notes techniques
            notes_techniques = st.text_area("Notes techniques", 
                                           value=product_data.get('notes_techniques', '') if product_data else "",
                                           height=80,
                                           help="Spécifications techniques, propriétés, conseils d'utilisation")

            st.caption("* Champs obligatoires")

            # Boutons
            col_submit, col_cancel_form = st.columns(2)
            with col_submit:
                submitted = st.form_submit_button("💾 Enregistrer le Produit", use_container_width=True)
            with col_cancel_form:
                if st.form_submit_button("❌ Annuler", use_container_width=True):
                    st.session_state.produit_action = None
                    st.session_state.produit_selected_id = None
                    st.rerun()

            if submitted:
                if not code_produit or not nom or not categorie or prix_unitaire <= 0:
                    st.error("Le code produit, nom, catégorie et prix unitaire sont obligatoires.")
                else:
                    new_product_data = {
                        'code_produit': code_produit,
                        'nom': nom,
                        'description': description,
                        'categorie': categorie,
                        'materiau': materiau,
                        'nuance': nuance,
                        'dimensions': dimensions,
                        'unite_vente': unite_vente,
                        'prix_unitaire': prix_unitaire,
                        'stock_disponible': stock_disponible,
                        'stock_minimum': stock_minimum,
                        'fournisseur_principal': fournisseur_principal,
                        'notes_techniques': notes_techniques
                    }
                    
                    if product_data:
                        # Mode modification
                        if gestionnaire_produits.modifier_produit(product_data['id'], new_product_data):
                            st.success(f"✅ Produit #{product_data['id']} mis à jour !")
                        else:
                            st.error("Erreur lors de la modification.")
                    else:
                        # Mode création
                        new_id = gestionnaire_produits.ajouter_produit(new_product_data)
                        if new_id:
                            st.success(f"✅ Nouveau produit #{new_id} ajouté !")
                        else:
                            st.error("Erreur lors de la création.")

                    st.session_state.produit_action = None
                    st.session_state.produit_selected_id = None
                    st.rerun()

def render_product_details(gestionnaire_produits: GestionnaireProduits, product_data):
    """Affiche les détails d'un produit"""
    if not product_data:
        st.error("Produit non trouvé.")
        return

    st.subheader(f"🔧 Détails du Produit: {product_data.get('code_produit')} - {product_data.get('nom')}")

    # Informations principales
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**ID:** {product_data.get('id')}")
        st.write(f"**Code:** {product_data.get('code_produit')}")
        st.write(f"**Catégorie:** {product_data.get('categorie')}")
        st.write(f"**Matériau:** {product_data.get('materiau')}")
        st.write(f"**Nuance:** {product_data.get('nuance')}")
        st.write(f"**Dimensions:** {product_data.get('dimensions', 'N/A')}")
    
    with col2:
        st.write(f"**Prix unitaire:** {product_data.get('prix_unitaire', 0):.2f} $ / {product_data.get('unite_vente')}")
        st.write(f"**Stock disponible:** {product_data.get('stock_disponible', 0)} {product_data.get('unite_vente')}")
        st.write(f"**Stock minimum:** {product_data.get('stock_minimum', 0)} {product_data.get('unite_vente')}")
        st.write(f"**Fournisseur:** {product_data.get('fournisseur_principal', 'N/A')}")
        
        # Calcul valeur stock
        valeur_stock = product_data.get('stock_disponible', 0) * product_data.get('prix_unitaire', 0)
        st.metric("Valeur du stock", f"{valeur_stock:,.2f} $")

    # Description
    st.markdown("### 📝 Description")
    st.write(product_data.get('description', 'Aucune description.'))

    # Notes techniques
    st.markdown("### 🔬 Notes Techniques")
    st.text_area("notes_tech_display", value=product_data.get('notes_techniques', 'Aucune note technique.'), 
                height=100, disabled=True, label_visibility="collapsed")

    # Indicateur de stock
    stock_disponible = product_data.get('stock_disponible', 0)
    stock_minimum = product_data.get('stock_minimum', 0)
    
    if stock_disponible <= stock_minimum:
        st.error(f"⚠️ Stock faible ! Niveau actuel: {stock_disponible}, Minimum: {stock_minimum}")
    elif stock_disponible <= stock_minimum * 1.5:
        st.warning(f"⚡ Stock bientôt bas. Niveau actuel: {stock_disponible}, Minimum: {stock_minimum}")
    else:
        st.success(f"✅ Stock correct. Niveau: {stock_disponible}")

    # Actions rapides
    st.markdown("### 🔧 Actions")
    col_act1, col_act2, col_act3 = st.columns(3)
    
    with col_act1:
        if st.button("✏️ Modifier ce produit", key="edit_product_from_details", use_container_width=True):
            st.session_state.produit_action = "edit_product"
            st.rerun()
    
    with col_act2:
        if st.button("📦 Ajuster le stock", key="adjust_stock_from_details", use_container_width=True):
            st.session_state.produit_action = "adjust_stock"
            st.rerun()
    
    with col_act3:
        st.info("💡 Les devis sont maintenant gérés dans un module séparé.")

    if st.button("Retour à la liste des produits", key="back_to_products_list_from_details"):
        st.session_state.produit_action = None
        st.rerun()

def render_stock_adjustment(gestionnaire_produits: GestionnaireProduits, product_data):
    """Interface pour ajuster le stock d'un produit"""
    if not product_data:
        st.error("Produit non trouvé.")
        return

    st.subheader(f"📦 Ajustement de Stock: {product_data.get('code_produit')} - {product_data.get('nom')}")
    
    # Informations actuelles
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.metric("Stock actuel", f"{product_data.get('stock_disponible', 0)} {product_data.get('unite_vente')}")
    with col_info2:
        st.metric("Stock minimum", f"{product_data.get('stock_minimum', 0)} {product_data.get('unite_vente')}")

    with st.form("ajustement_stock_form"):
        st.markdown("##### Nouvel ajustement")
        
        col_adj1, col_adj2 = st.columns(2)
        with col_adj1:
            nouveau_stock = st.number_input(
                f"Nouvelle quantité ({product_data.get('unite_vente')})",
                min_value=0.0,
                value=float(product_data.get('stock_disponible', 0)),
                step=0.1,
                format="%.2f"
            )
        
        with col_adj2:
            motif = st.text_input("Motif de l'ajustement", 
                                placeholder="Ex: Réception livraison, Correction inventaire, Consommation...")

        # Calcul de la différence
        difference = nouveau_stock - product_data.get('stock_disponible', 0)
        
        if difference > 0:
            st.success(f"➕ Augmentation: +{difference} {product_data.get('unite_vente')}")
        elif difference < 0:
            st.error(f"➖ Diminution: {difference} {product_data.get('unite_vente')}")
        else:
            st.info("↔️ Aucun changement")

        # Boutons
        col_save, col_cancel = st.columns(2)
        with col_save:
            submitted = st.form_submit_button("💾 Confirmer l'ajustement", type="primary", use_container_width=True)
        with col_cancel:
            if st.form_submit_button("❌ Annuler", use_container_width=True):
                st.session_state.produit_action = "view_product_details"
                st.rerun()

        if submitted:
            if gestionnaire_produits.ajuster_stock_produit(product_data['id'], nouveau_stock, motif):
                st.session_state.produit_action = "view_product_details"
                st.rerun()
            else:
                st.error("Erreur lors de l'ajustement du stock.")

# =========================================================================
# GESTION DES ACTIONS ET POINT D'ENTRÉE PRINCIPAL
# =========================================================================

def handle_produits_actions(gestionnaire_produits: GestionnaireProduits):
    """Gère l'affichage des formulaires et des détails pour les produits."""
    action = st.session_state.get('produit_action')
    selected_id = st.session_state.get('produit_selected_id')

    if action == "create_product":
        render_product_form(gestionnaire_produits)
    elif action == "edit_product" and selected_id:
        product_data = gestionnaire_produits.get_produit_by_id(selected_id)
        render_product_form(gestionnaire_produits, product_data=product_data)
    elif action == "view_product_details" and selected_id:
        product_data = gestionnaire_produits.get_produit_by_id(selected_id)
        render_product_details(gestionnaire_produits, product_data=product_data)
    elif action == "adjust_stock" and selected_id:
        product_data = gestionnaire_produits.get_produit_by_id(selected_id)
        render_stock_adjustment(gestionnaire_produits, product_data=product_data)


def show_produits_page():
    """Point d'entrée principal pour l'interface de gestion des produits."""
    st.title("🔧 Gestion des Produits et Inventaire")
    
    if 'gestionnaire_produits' not in st.session_state:
        st.error("Le gestionnaire de produits n'est pas initialisé.")
        return

    gestionnaire_produits = st.session_state.gestionnaire_produits
    
    # Créer les onglets pour Produits et Inventaire
    tab1, tab2, tab3, tab4 = st.tabs(["📦 Catalogue Produits", "📊 Inventaire", "📈 Mouvements Stock", "🔄 Inventaire Physique"])
    
    with tab1:
        # Onglet principal des produits
        render_produits_tab(gestionnaire_produits)
        handle_produits_actions(gestionnaire_produits)
    
    with tab2:
        # Onglet inventaire
        render_inventaire_tab(gestionnaire_produits)
    
    with tab3:
        # Onglet mouvements de stock
        render_mouvements_tab(gestionnaire_produits)
    
    with tab4:
        # Onglet inventaire physique
        render_inventaire_physique_tab(gestionnaire_produits)

# =========================================================================
# FONCTIONS D'INVENTAIRE
# =========================================================================

def render_inventaire_tab(gestionnaire_produits: GestionnaireProduits):
    """Affiche l'onglet de vue d'ensemble de l'inventaire"""
    
    # Analyse globale
    analyse = gestionnaire_produits.get_analyse_inventaire()
    
    # Métriques en haut
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Valeur Totale Stock", f"${analyse.get('valeur_totale_stock', 0):,.2f}")
    
    with col2:
        ruptures = analyse.get('produits_rupture', 0)
        st.metric("Ruptures de Stock", ruptures, 
                 delta=f"-{ruptures}" if ruptures > 0 else None,
                 delta_color="inverse")
    
    with col3:
        sous_min = analyse.get('produits_sous_minimum', 0)
        st.metric("Stock Bas", sous_min,
                 delta=f"-{sous_min}" if sous_min > 0 else None,
                 delta_color="inverse")
    
    with col4:
        reservations = analyse.get('reservations_actives', {})
        st.metric("Réservations Actives", reservations.get('count', 0))
    
    st.markdown("---")
    
    # Vue détaillée de l'inventaire
    st.subheader("📊 État des Stocks")
    
    # Filtres
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtre_statut = st.selectbox(
            "Filtrer par statut",
            ["Tous", "Stock OK", "Stock Bas", "Rupture", "Avec Réservations"]
        )
    
    with col2:
        filtre_categorie = st.selectbox(
            "Catégorie",
            ["Toutes"] + CATEGORIES_PRODUITS
        )
    
    with col3:
        recherche = st.text_input("Rechercher...", placeholder="Code ou nom produit")
    
    # Récupérer et filtrer les produits
    produits = gestionnaire_produits.produits
    
    # Appliquer les filtres
    produits_filtres = []
    for p in produits:
        # Filtre recherche
        if recherche and recherche.lower() not in p.get('code_produit', '').lower() and recherche.lower() not in p.get('nom', '').lower():
            continue
        
        # Filtre catégorie
        if filtre_categorie != "Toutes" and p.get('categorie') != filtre_categorie:
            continue
        
        # Calculer le statut
        stock_dispo = p.get('stock_disponible', 0)
        stock_min = p.get('stock_minimum', 0)
        
        if filtre_statut == "Stock OK" and (stock_dispo <= stock_min or stock_dispo <= 0):
            continue
        elif filtre_statut == "Stock Bas" and not (0 < stock_dispo <= stock_min):
            continue
        elif filtre_statut == "Rupture" and stock_dispo > 0:
            continue
        
        # Ajouter les infos de stock complet
        if gestionnaire_produits.use_sqlite:
            stock_info = gestionnaire_produits.get_stock_complet(p['id'])
            if stock_info:
                p['stock_libre'] = stock_info.get('stock_libre', stock_dispo)
                p['stock_reserve'] = stock_info.get('total_reserve', 0)
            else:
                p['stock_libre'] = stock_dispo
                p['stock_reserve'] = 0
        else:
            p['stock_libre'] = stock_dispo
            p['stock_reserve'] = 0
        
        produits_filtres.append(p)
    
    # Afficher les produits
    if produits_filtres:
        df_data = []
        for p in produits_filtres:
            stock_dispo = p.get('stock_disponible', 0)
            stock_min = p.get('stock_minimum', 0)
            stock_libre = p.get('stock_libre', stock_dispo)
            stock_reserve = p.get('stock_reserve', 0)
            
            # Statut avec emoji
            if stock_dispo <= 0:
                statut = "🔴 Rupture"
            elif stock_dispo <= stock_min:
                statut = "🟡 Stock Bas"
            else:
                statut = "🟢 OK"
            
            # Taux de stock
            taux = (stock_dispo / stock_min * 100) if stock_min > 0 else 100
            
            df_data.append({
                "Code": p.get('code_produit'),
                "Produit": p.get('nom'),
                "Catégorie": p.get('categorie'),
                "Stock Total": f"{stock_dispo:.2f} {p.get('unite_vente')}",
                "Stock Libre": f"{stock_libre:.2f} {p.get('unite_vente')}",
                "Réservé": f"{stock_reserve:.2f}" if stock_reserve > 0 else "-",
                "Stock Min": f"{stock_min:.2f}",
                "Taux": f"{taux:.0f}%",
                "Statut": statut,
                "Valeur": f"${stock_dispo * p.get('prix_unitaire', 0):,.2f}",
                "Emplacement": p.get('emplacement_stock', 'N/A')
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Actions rapides
        st.markdown("### 🔧 Actions Rapides")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            selected_product = st.selectbox(
                "Sélectionner un produit",
                options=[p['id'] for p in produits_filtres],
                format_func=lambda x: next((f"{p['code_produit']} - {p['nom']}" for p in produits_filtres if p['id'] == x), "")
            )
        
        with col2:
            if st.button("📥 Entrée Stock", use_container_width=True):
                st.session_state.inventory_action = "entree_stock"
                st.session_state.inventory_product_id = selected_product
        
        with col3:
            if st.button("📤 Sortie Stock", use_container_width=True):
                st.session_state.inventory_action = "sortie_stock"
                st.session_state.inventory_product_id = selected_product
    
    else:
        st.info("Aucun produit ne correspond aux critères")
    
    # Gérer les actions d'inventaire
    handle_inventory_actions(gestionnaire_produits)


def render_mouvements_tab(gestionnaire_produits: GestionnaireProduits):
    """Affiche l'historique des mouvements de stock"""
    
    st.subheader("📈 Historique des Mouvements de Stock")
    
    # Filtres
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Sélection du produit (optionnel)
        produits = gestionnaire_produits.produits
        produit_id = st.selectbox(
            "Filtrer par produit",
            options=[None] + [p['id'] for p in produits],
            format_func=lambda x: "Tous les produits" if x is None else next((f"{p['code_produit']} - {p['nom']}" for p in produits if p['id'] == x), "")
        )
    
    with col2:
        type_mouvement = st.selectbox(
            "Type de mouvement",
            ["Tous", "ENTREE", "SORTIE", "AJUSTEMENT", "RESERVATION", "LIBERATION", "INVENTAIRE"]
        )
    
    with col3:
        limite = st.number_input("Nombre de lignes", min_value=10, max_value=500, value=100)
    
    # Récupérer les mouvements
    if gestionnaire_produits.use_sqlite:
        mouvements = gestionnaire_produits.db.get_mouvements_stock(produit_id=produit_id, limit=limite)
        
        # Filtrer par type si nécessaire
        if type_mouvement != "Tous":
            mouvements = [m for m in mouvements if m['type_mouvement'] == type_mouvement]
        
        if mouvements:
            # Préparer les données pour l'affichage
            df_data = []
            for m in mouvements:
                # Couleur selon le type
                if m['type_mouvement'] in ['ENTREE', 'LIBERATION']:
                    type_icon = "➕"
                    quantite_str = f"+{m['quantite']}"
                elif m['type_mouvement'] in ['SORTIE', 'RESERVATION']:
                    type_icon = "➖"
                    quantite_str = f"-{m['quantite']}"
                else:
                    type_icon = "🔄"
                    quantite_str = f"{m['quantite']}"
                
                df_data.append({
                    "Date": datetime.fromisoformat(m['created_at']).strftime("%d/%m/%Y %H:%M"),
                    "Code Produit": m.get('code_produit', ''),
                    "Produit": m.get('produit_nom', ''),
                    "Type": f"{type_icon} {m['type_mouvement']}",
                    "Quantité": quantite_str,
                    "Stock Avant": f"{m.get('quantite_avant', 0):.2f}",
                    "Stock Après": f"{m.get('quantite_apres', 0):.2f}",
                    "Référence": m.get('reference_document', ''),
                    "Motif": m.get('motif', ''),
                    "Employé": m.get('employee_name', 'N/A')
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Export
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Télécharger CSV",
                data=csv,
                file_name=f"mouvements_stock_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Aucun mouvement de stock trouvé")
    else:
        st.warning("L'historique des mouvements n'est disponible qu'en mode SQLite")


def render_inventaire_physique_tab(gestionnaire_produits: GestionnaireProduits):
    """Gère les inventaires physiques"""
    
    st.subheader("🔄 Inventaire Physique")
    
    if not gestionnaire_produits.use_sqlite:
        st.warning("Les inventaires physiques ne sont disponibles qu'en mode SQLite")
        return
    
    # Actions principales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Nouvel Inventaire", use_container_width=True):
            st.session_state.inventory_action = "new_inventaire"
    
    with col2:
        # Récupérer les inventaires en cours
        inventaires_en_cours = gestionnaire_produits.db.execute_query(
            "SELECT * FROM inventaires_physiques WHERE statut = 'EN_COURS' ORDER BY created_at DESC"
        )
        
        if inventaires_en_cours:
            inventaire_id = st.selectbox(
                "Inventaire en cours",
                options=[inv['id'] for inv in inventaires_en_cours],
                format_func=lambda x: next((f"{inv['code_inventaire']} - {inv['date_inventaire']}" for inv in inventaires_en_cours if inv['id'] == x), "")
            )
            
            if st.button("📝 Saisir Comptage", use_container_width=True):
                st.session_state.inventory_action = "saisie_comptage"
                st.session_state.inventory_id = inventaire_id
    
    with col3:
        if inventaires_en_cours and st.button("✅ Valider Inventaire", use_container_width=True):
            st.session_state.inventory_action = "valider_inventaire"
            st.session_state.inventory_id = inventaire_id
    
    st.markdown("---")
    
    # Historique des inventaires
    st.markdown("### 📋 Historique des Inventaires")
    
    historique = gestionnaire_produits.db.execute_query('''
        SELECT ip.*, e.prenom || ' ' || e.nom as created_by_name,
               ev.prenom || ' ' || ev.nom as validated_by_name
        FROM inventaires_physiques ip
        LEFT JOIN employees e ON ip.created_by = e.id
        LEFT JOIN employees ev ON ip.validated_by = ev.id
        ORDER BY ip.created_at DESC
        LIMIT 20
    ''')
    
    if historique:
        df_data = []
        for inv in historique:
            # Calculer les écarts si validé
            if inv['statut'] == 'VALIDE':
                ecarts = gestionnaire_produits.db.execute_query('''
                    SELECT COUNT(*) as nb_ecarts, SUM(ABS(ecart_valeur)) as valeur_ecarts
                    FROM inventaire_lignes
                    WHERE inventaire_id = ? AND ecart != 0
                ''', (inv['id'],))[0]
                ecarts_str = f"{ecarts['nb_ecarts']} écarts (${ecarts.get('valeur_ecarts', 0):,.2f})"
            else:
                ecarts_str = "-"
            
            df_data.append({
                "Code": inv['code_inventaire'],
                "Date": inv['date_inventaire'],
                "Type": inv['type_inventaire'],
                "Statut": inv['statut'],
                "Créé par": inv.get('created_by_name', 'N/A'),
                "Validé par": inv.get('validated_by_name', '-'),
                "Écarts": ecarts_str,
                "Notes": inv.get('notes', '')
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun inventaire physique réalisé")
    
    # Gérer les actions d'inventaire physique
    handle_inventory_physical_actions(gestionnaire_produits)


def handle_inventory_actions(gestionnaire_produits: GestionnaireProduits):
    """Gère les actions d'inventaire"""
    
    action = st.session_state.get('inventory_action')
    product_id = st.session_state.get('inventory_product_id')
    
    if action == "entree_stock" and product_id:
        render_entree_stock_form(gestionnaire_produits, product_id)
    elif action == "sortie_stock" and product_id:
        render_sortie_stock_form(gestionnaire_produits, product_id)


def render_entree_stock_form(gestionnaire_produits: GestionnaireProduits, product_id):
    """Formulaire d'entrée de stock"""
    
    product = gestionnaire_produits.get_produit_by_id(product_id)
    if not product:
        st.error("Produit non trouvé")
        return
    
    st.subheader(f"📥 Entrée de Stock - {product['code_produit']} - {product['nom']}")
    
    with st.form("entree_stock_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            quantite = st.number_input(
                f"Quantité à entrer ({product['unite_vente']})",
                min_value=0.0,
                step=1.0
            )
            
            reference = st.text_input("Référence document", placeholder="N° bon de réception, facture...")
        
        with col2:
            cout_unitaire = st.number_input(
                "Coût unitaire ($)",
                min_value=0.0,
                value=float(product.get('prix_unitaire', 0)),
                step=0.01
            )
            
            cout_total = quantite * cout_unitaire
            st.metric("Coût total", f"${cout_total:,.2f}")
        
        notes = st.text_area("Notes", placeholder="Fournisseur, conditions...")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("✅ Confirmer l'entrée", type="primary", use_container_width=True):
                if quantite > 0:
                    # Récupérer l'employé actuel (simplification)
                    employee_id = 1  # À remplacer par l'employé connecté
                    
                    if gestionnaire_produits.entree_stock(
                        product_id, 
                        quantite, 
                        reference, 
                        cout_unitaire,
                        employee_id
                    ):
                        st.success(f"✅ Entrée de {quantite} {product['unite_vente']} enregistrée")
                        st.session_state.inventory_action = None
                        st.rerun()
                else:
                    st.error("La quantité doit être supérieure à 0")
        
        with col2:
            if st.form_submit_button("❌ Annuler", use_container_width=True):
                st.session_state.inventory_action = None
                st.rerun()


def render_sortie_stock_form(gestionnaire_produits: GestionnaireProduits, product_id):
    """Formulaire de sortie de stock"""
    
    product = gestionnaire_produits.get_produit_by_id(product_id)
    stock_info = gestionnaire_produits.get_stock_complet(product_id)
    
    if not product or not stock_info:
        st.error("Produit non trouvé")
        return
    
    st.subheader(f"📤 Sortie de Stock - {product['code_produit']} - {product['nom']}")
    
    # Afficher le stock disponible
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Stock Total", f"{stock_info['stock_disponible']:.2f} {product['unite_vente']}")
    with col2:
        st.metric("Stock Libre", f"{stock_info['stock_libre']:.2f} {product['unite_vente']}")
    with col3:
        st.metric("Réservé", f"{stock_info['total_reserve']:.2f} {product['unite_vente']}")
    
    with st.form("sortie_stock_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            quantite = st.number_input(
                f"Quantité à sortir ({product['unite_vente']})",
                min_value=0.0,
                max_value=float(stock_info['stock_libre']),
                step=1.0
            )
            
            reference = st.text_input("Référence document", placeholder="N° bon de livraison, BT...")
        
        with col2:
            motif = st.selectbox(
                "Motif de sortie",
                ["Consommation production", "Livraison client", "Échantillon", "Perte/Déchet", "Autre"]
            )
            
            if motif == "Autre":
                motif_autre = st.text_input("Préciser le motif")
                motif = motif_autre if motif_autre else motif
        
        notes = st.text_area("Notes", placeholder="Détails supplémentaires...")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("✅ Confirmer la sortie", type="primary", use_container_width=True):
                if quantite > 0:
                    # Récupérer l'employé actuel (simplification)
                    employee_id = 1  # À remplacer par l'employé connecté
                    
                    if gestionnaire_produits.sortie_stock(
                        product_id, 
                        quantite, 
                        reference, 
                        motif,
                        employee_id
                    ):
                        st.success(f"✅ Sortie de {quantite} {product['unite_vente']} enregistrée")
                        st.session_state.inventory_action = None
                        st.rerun()
                else:
                    st.error("La quantité doit être supérieure à 0")
        
        with col2:
            if st.form_submit_button("❌ Annuler", use_container_width=True):
                st.session_state.inventory_action = None
                st.rerun()


def handle_inventory_physical_actions(gestionnaire_produits: GestionnaireProduits):
    """Gère les actions d'inventaire physique"""
    
    action = st.session_state.get('inventory_action')
    
    if action == "new_inventaire":
        render_new_inventaire_form(gestionnaire_produits)
    elif action == "saisie_comptage":
        render_saisie_comptage_form(gestionnaire_produits)
    elif action == "valider_inventaire":
        render_validation_inventaire(gestionnaire_produits)


def render_new_inventaire_form(gestionnaire_produits: GestionnaireProduits):
    """Formulaire de création d'inventaire physique"""
    
    with st.expander("➕ Créer un nouvel inventaire", expanded=True):
        with st.form("new_inventaire_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                type_inventaire = st.selectbox(
                    "Type d'inventaire",
                    ["COMPLET", "PARTIEL", "CYCLIQUE", "ALEATOIRE"]
                )
                
                date_inventaire = st.date_input("Date de l'inventaire", value=datetime.now().date())
            
            with col2:
                if type_inventaire == "PARTIEL":
                    categories = st.multiselect(
                        "Catégories à inventorier",
                        CATEGORIES_PRODUITS
                    )
                
                notes = st.text_area("Notes", placeholder="Objectif, périmètre...")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.form_submit_button("✅ Créer l'inventaire", type="primary", use_container_width=True):
                    employee_id = 1  # À remplacer par l'employé connecté
                    
                    inventaire_id = gestionnaire_produits.db.creer_inventaire_physique({
                        'type_inventaire': type_inventaire,
                        'date_inventaire': date_inventaire,
                        'created_by': employee_id,
                        'notes': notes
                    })
                    
                    if inventaire_id:
                        st.success("✅ Inventaire créé avec succès")
                        st.session_state.inventory_action = None
                        st.rerun()
            
            with col2:
                if st.form_submit_button("❌ Annuler", use_container_width=True):
                    st.session_state.inventory_action = None
                    st.rerun()


def render_saisie_comptage_form(gestionnaire_produits: GestionnaireProduits):
    """Formulaire de saisie de comptage pour inventaire physique"""
    
    inventaire_id = st.session_state.get('inventory_id')
    if not inventaire_id:
        st.error("Aucun inventaire sélectionné")
        return
    
    st.subheader("📝 Saisie de Comptage Physique")
    
    # Récupérer les lignes à compter
    lignes = gestionnaire_produits.db.execute_query('''
        SELECT il.*, p.code_produit, p.nom as produit_nom, p.unite_vente, p.emplacement_stock
        FROM inventaire_lignes il
        JOIN produits p ON il.produit_id = p.id
        WHERE il.inventaire_id = ? AND il.statut_ligne = 'A_COMPTER'
        ORDER BY p.code_produit
        LIMIT 20
    ''', (inventaire_id,))
    
    if lignes:
        st.info(f"📋 {len(lignes)} produits à compter (max 20 affichés)")
        
        # Formulaire de comptage par lot
        with st.form("comptage_form"):
            comptages = {}
            
            for ligne in lignes:
                st.markdown(f"### {ligne['code_produit']} - {ligne['produit_nom']}")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Emplacement:** {ligne.get('emplacement_stock', 'N/A')}")
                    st.write(f"**Stock théorique:** {ligne['quantite_theorique']} {ligne['unite_vente']}")
                
                with col2:
                    quantite_physique = st.number_input(
                        f"Quantité comptée ({ligne['unite_vente']})",
                        min_value=0.0,
                        value=float(ligne['quantite_theorique']),
                        step=0.1,
                        key=f"comptage_{ligne['id']}"
                    )
                    comptages[ligne['id']] = quantite_physique
                
                with col3:
                    ecart = quantite_physique - ligne['quantite_theorique']
                    if ecart != 0:
                        st.metric("Écart", f"{ecart:+.2f}", delta_color="inverse" if ecart < 0 else "normal")
                    else:
                        st.metric("Écart", "0")
                
                st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.form_submit_button("✅ Valider les comptages", type="primary", use_container_width=True):
                    employee_id = 1  # À remplacer par l'employé connecté
                    
                    # Enregistrer tous les comptages
                    success_count = 0
                    for ligne_id, quantite in comptages.items():
                        if gestionnaire_produits.db.saisir_comptage_inventaire(ligne_id, quantite, employee_id):
                            success_count += 1
                    
                    st.success(f"✅ {success_count} comptages enregistrés")
                    st.session_state.inventory_action = None
                    st.rerun()
            
            with col2:
                if st.form_submit_button("❌ Annuler", use_container_width=True):
                    st.session_state.inventory_action = None
                    st.rerun()
    else:
        st.success("✅ Tous les produits ont été comptés pour cet inventaire")
        if st.button("Retour"):
            st.session_state.inventory_action = None
            st.rerun()


def render_validation_inventaire(gestionnaire_produits: GestionnaireProduits):
    """Interface de validation d'inventaire"""
    
    inventaire_id = st.session_state.get('inventory_id')
    if not inventaire_id:
        st.error("Aucun inventaire sélectionné")
        return
    
    st.subheader("✅ Validation d'Inventaire")
    
    # Récupérer les informations de l'inventaire
    inventaire = gestionnaire_produits.db.execute_query(
        "SELECT * FROM inventaires_physiques WHERE id = ?",
        (inventaire_id,)
    )[0]
    
    # Statistiques de l'inventaire
    stats = gestionnaire_produits.db.execute_query('''
        SELECT 
            COUNT(*) as total_lignes,
            COUNT(CASE WHEN statut_ligne = 'COMPTE' THEN 1 END) as lignes_comptees,
            COUNT(CASE WHEN ecart != 0 THEN 1 END) as lignes_avec_ecart,
            SUM(ABS(ecart_valeur)) as valeur_ecarts_total
        FROM inventaire_lignes
        WHERE inventaire_id = ?
    ''', (inventaire_id,))[0]
    
    # Afficher les statistiques
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Produits", stats['total_lignes'])
    
    with col2:
        st.metric("Produits Comptés", stats['lignes_comptees'])
    
    with col3:
        st.metric("Produits avec Écart", stats['lignes_avec_ecart'])
    
    with col4:
        st.metric("Valeur Totale Écarts", f"${stats['valeur_ecarts_total'] or 0:,.2f}")
    
    # Vérifier si tout est compté
    if stats['lignes_comptees'] < stats['total_lignes']:
        st.error(f"⚠️ {stats['total_lignes'] - stats['lignes_comptees']} produits n'ont pas été comptés")
        return
    
    # Afficher les écarts significatifs
    if stats['lignes_avec_ecart'] > 0:
        st.markdown("### 📊 Écarts Détectés")
        
        ecarts = gestionnaire_produits.db.execute_query('''
            SELECT il.*, p.code_produit, p.nom as produit_nom, p.unite_vente
            FROM inventaire_lignes il
            JOIN produits p ON il.produit_id = p.id
            WHERE il.inventaire_id = ? AND il.ecart != 0
            ORDER BY ABS(il.ecart_valeur) DESC
            LIMIT 20
        ''', (inventaire_id,))
        
        df_data = []
        for ecart in ecarts:
            df_data.append({
                "Code": ecart['code_produit'],
                "Produit": ecart['produit_nom'],
                "Stock Théorique": f"{ecart['quantite_theorique']} {ecart['unite_vente']}",
                "Stock Physique": f"{ecart['quantite_physique']} {ecart['unite_vente']}",
                "Écart": f"{ecart['ecart']:+.2f} {ecart['unite_vente']}",
                "Valeur Écart": f"${ecart['ecart_valeur']:+,.2f}"
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Boutons d'action
    st.markdown("---")
    st.warning("⚠️ La validation appliquera automatiquement tous les ajustements de stock")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Valider et Appliquer les Ajustements", type="primary", use_container_width=True):
            employee_id = 1  # À remplacer par l'employé connecté
            
            if gestionnaire_produits.db.valider_inventaire(inventaire_id, employee_id):
                st.success("✅ Inventaire validé et ajustements appliqués")
                st.session_state.inventory_action = None
                st.rerun()
            else:
                st.error("Erreur lors de la validation")
    
    with col2:
        if st.button("❌ Annuler", use_container_width=True):
            st.session_state.inventory_action = None
            st.rerun()

# =========================================================================
# FONCTIONS UTILITAIRES
# =========================================================================

def get_produits_statistics_summary(gestionnaire_produits: GestionnaireProduits):
    """Résumé des statistiques produits pour dashboard"""
    try:
        return gestionnaire_produits.get_statistics_produits()
    except Exception as e:
        st.error(f"Erreur calcul statistiques produits: {e}")
        return {}

def export_produits_to_excel(gestionnaire_produits: GestionnaireProduits):
    """Exporte les données produits vers Excel"""
    try:
        produits_df = pd.DataFrame(gestionnaire_produits.produits)
        return produits_df
    except Exception as e:
        st.error(f"Erreur export Excel produits: {e}")
        return None

# =========================================================================
# DÉMONSTRATION ET TESTS
# =========================================================================

def demo_produits_standalone():
    """Démonstration du module produits en mode standalone"""
    st.title("🎯 Démonstration Module Produits")
    
    # Initialisation du gestionnaire en mode JSON pour la démo
    gestionnaire_produits = GestionnaireProduits(db=None)
    
    st.info("💡 Cette démonstration utilise le mode JSON. Pour une version complète avec SQLite, il faut un environnement avec ERPDatabase.")
    
    # Stocker dans la session pour la démo
    st.session_state.gestionnaire_produits = gestionnaire_produits
    
    # Afficher l'interface
    show_produits_page()

if __name__ == "__main__":
    # Pour une exécution standalone du module
    demo_produits_standalone()
