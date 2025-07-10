import json
import os
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from typing import Dict, List, Optional, Any

# --- Constantes ---
TYPES_INTERACTION = ["Email", "Appel", "Réunion", "Note", "Autre"]
STATUTS_OPPORTUNITE = ["Prospection", "Qualification", "Proposition", "Négociation", "Gagné", "Perdu"]

# Constantes pour les produits métallurgiques
CATEGORIES_PRODUITS = ["Acier", "Aluminium", "Inox", "Cuivre", "Laiton", "Autres métaux", "Fournitures", "Services"]
UNITES_VENTE = ["kg", "tonne", "m", "m²", "m³", "pièce", "lot", "heure"]
NUANCES_MATERIAUX = {
    "Acier": ["S235", "S355", "S460", "42CrMo4", "25CrMo4", "Autres"],
    "Aluminium": ["6061-T6", "6063-T5", "2024-T3", "7075-T6", "5083", "Autres"],
    "Inox": ["304L", "316L", "321", "410", "430", "Duplex", "Autres"],
    "Cuivre": ["Cu-ETP", "Cu-DHP", "CuZn37", "CuSn8", "Autres"],
    "Autres": ["Standard", "Spécial", "Sur mesure"]
}

class GestionnaireCRM:
    """
    Gestionnaire CRM utilisant SQLite au lieu de JSON
    Compatible avec ERPDatabase pour une architecture unifiée
    + GESTION COMPLÈTE DES PRODUITS MÉTALLURGIQUES
    + ADRESSES STRUCTURÉES (adresse, ville, province, code_postal, pays)
    """
    
    def __init__(self, db=None):
        """
        Initialise le gestionnaire CRM avec base SQLite.
        Le project_manager n'est plus nécessaire ici car les devis sont gérés séparément.
        """
        self.db = db
        self.use_sqlite = db is not None
        
        if not self.use_sqlite:
            # Mode rétrocompatibilité JSON (conservé temporairement)
            self.data_file = "crm_data.json"
            self._contacts = []
            self._entreprises = []
            self._interactions = []
            self._produits = []
            self.next_contact_id = 1
            self.next_entreprise_id = 1
            self.next_interaction_id = 1
            self.next_produit_id = 1
            self.charger_donnees_crm()
        else:
            # Mode SQLite unifié
            self._init_demo_data_if_empty()
            self._init_products_table()
    
    def _init_demo_data_if_empty(self):
        """Initialise des données démo si les tables SQLite sont vides"""
        if not self.use_sqlite:
            return
            
        try:
            # D'abord, vérifier et mettre à jour la structure de la table companies
            self._ensure_companies_table_structure()
            
            # Vérifier si des données existent déjà
            companies = self.db.execute_query("SELECT COUNT(*) as count FROM companies")
            contacts = self.db.execute_query("SELECT COUNT(*) as count FROM contacts")
            
            if companies[0]['count'] == 0 and contacts[0]['count'] == 0:
                self._create_demo_data_sqlite()
        except Exception as e:
            st.error(f"Erreur initialisation données démo CRM: {e}")
    
    def _ensure_companies_table_structure(self):
        """Vérifie et ajoute les colonnes d'adresse structurées si nécessaire"""
        if not self.use_sqlite:
            return
        
        try:
            # Vérifier la structure actuelle de la table companies
            columns_info = self.db.execute_query("PRAGMA table_info(companies)")
            existing_columns = [col['name'] for col in columns_info]
            
            # Colonnes d'adresse à ajouter si elles n'existent pas
            required_address_columns = {
                'ville': 'TEXT',
                'province': 'TEXT', 
                'code_postal': 'TEXT',
                'pays': 'TEXT'
            }
            
            # Ajouter les colonnes manquantes
            for column_name, column_type in required_address_columns.items():
                if column_name not in existing_columns:
                    alter_query = f"ALTER TABLE companies ADD COLUMN {column_name} {column_type}"
                    self.db.execute_update(alter_query)
                    st.info(f"✅ Colonne '{column_name}' ajoutée à la table companies")
            
            # Vérifier si le champ 'adresse' existe, sinon le renommer/traiter
            if 'adresse' not in existing_columns:
                # Si pas de colonne adresse du tout, l'ajouter
                self.db.execute_update("ALTER TABLE companies ADD COLUMN adresse TEXT")
                st.info("✅ Colonne 'adresse' ajoutée à la table companies")
        
        except Exception as e:
            st.warning(f"Attention lors de la mise à jour de la structure: {e}")
            # En cas d'erreur, continuer quand même

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
                    fournisseur_principal TEXT,
                    notes_techniques TEXT,
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
                # Vérifier si des produits existent, sinon ajouter démo
                count_result = self.db.execute_query("SELECT COUNT(*) as count FROM produits")
                if count_result[0]['count'] == 0:
                    self._create_demo_products()
                    
        except Exception as e:
            st.error(f"Erreur lors de l'initialisation de la table produits: {e}")

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
    
    def debug_database_structure(self):
        """Fonction de diagnostic pour vérifier la structure de la base de données"""
        if not self.use_sqlite:
            return "Mode JSON - pas de structure SQLite à vérifier"
        
        try:
            # Informations sur la table companies
            columns_info = self.db.execute_query("PRAGMA table_info(companies)")
            
            # Informations sur la table produits
            produits_columns = []
            try:
                produits_columns = self.db.execute_query("PRAGMA table_info(produits)")
            except:
                produits_columns = []
            
            debug_info = {
                'colonnes_companies': [{'nom': col['name'], 'type': col['type']} for col in columns_info],
                'colonnes_produits': [{'nom': col['name'], 'type': col['type']} for col in produits_columns],
                'nombre_entreprises': len(self.get_all_companies()),
                'nombre_produits': len(self.get_all_products()) if self.use_sqlite else 0,
            }
            
            return debug_info
        except Exception as e:
            return f"Erreur lors du diagnostic: {e}"
    
    def _create_demo_data_sqlite(self):
        """Crée des données de démonstration en SQLite avec adresses structurées"""
        if not self.use_sqlite:
            return
            
        try:
            now_iso = datetime.now().isoformat()
            
            # Créer entreprises de démonstration avec adresses structurées
            entreprises_demo = [
                {
                    'id': 101,
                    'nom': 'TechCorp Inc.',
                    'secteur': 'Technologie',
                    'adresse': '123 Rue de la Paix',
                    'ville': 'Paris',
                    'province': 'Île-de-France',
                    'code_postal': '75001',
                    'pays': 'France',
                    'site_web': 'techcorp.com',
                    'notes': 'Client pour le projet E-commerce. Actif.'
                },
                {
                    'id': 102,
                    'nom': 'StartupXYZ',
                    'secteur': 'Logiciel',
                    'adresse': '456 Innovation Drive',
                    'ville': 'San Francisco',
                    'province': 'California',
                    'code_postal': '94102',
                    'pays': 'États-Unis',
                    'site_web': 'startup.xyz',
                    'notes': 'Client pour l\'app mobile. En phase de développement.'
                },
                {
                    'id': 103,
                    'nom': 'MegaCorp Ltd',
                    'secteur': 'Finance',
                    'adresse': '789 Boulevard des Affaires',
                    'ville': 'Montréal',
                    'province': 'Québec',
                    'code_postal': 'H3B 1A1',
                    'pays': 'Canada',
                    'site_web': 'megacorp.com',
                    'notes': 'Projet CRM terminé. Potentiel pour maintenance.'
                }
            ]
            
            for entreprise in entreprises_demo:
                self.db.execute_update('''
                    INSERT OR REPLACE INTO companies 
                    (id, nom, secteur, adresse, ville, province, code_postal, pays, site_web, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entreprise['id'],
                    entreprise['nom'],
                    entreprise['secteur'],
                    entreprise['adresse'],
                    entreprise['ville'],
                    entreprise['province'],
                    entreprise['code_postal'],
                    entreprise['pays'],
                    entreprise['site_web'],
                    entreprise['notes'],
                    now_iso,
                    now_iso
                ))
            
            # Créer contacts de démonstration
            contacts_demo = [
                {
                    'id': 1,
                    'prenom': 'Alice',
                    'nom_famille': 'Martin',
                    'email': 'alice@techcorp.com',
                    'telephone': '0102030405',
                    'company_id': 101,
                    'role_poste': 'Responsable Marketing',
                    'notes': 'Contact principal pour le projet E-commerce.'
                },
                {
                    'id': 2,
                    'prenom': 'Bob',
                    'nom_famille': 'Durand',
                    'email': 'bob@startupxyz.com',
                    'telephone': '0607080910',
                    'company_id': 102,
                    'role_poste': 'CTO',
                    'notes': 'Décideur technique pour l\'application mobile.'
                },
                {
                    'id': 3,
                    'prenom': 'Claire',
                    'nom_famille': 'Leroy',
                    'email': 'claire.leroy@megacorp.com',
                    'telephone': '0708091011',
                    'company_id': 103,
                    'role_poste': 'Chef de projet CRM',
                    'notes': 'Très organisée, demande des rapports réguliers.'
                }
            ]
            
            for contact in contacts_demo:
                self.db.execute_update('''
                    INSERT OR REPLACE INTO contacts 
                    (id, prenom, nom_famille, email, telephone, company_id, role_poste, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    contact['id'],
                    contact['prenom'],
                    contact['nom_famille'],
                    contact['email'],
                    contact['telephone'],
                    contact['company_id'],
                    contact['role_poste'],
                    contact['notes'],
                    now_iso,
                    now_iso
                ))
            
            # Mettre à jour les contact_principal_id des entreprises
            self.db.execute_update("UPDATE companies SET contact_principal_id = 1 WHERE id = 101")
            self.db.execute_update("UPDATE companies SET contact_principal_id = 2 WHERE id = 102")
            self.db.execute_update("UPDATE companies SET contact_principal_id = 3 WHERE id = 103")
            
            # Créer interactions de démonstration
            interactions_demo = [
                {
                    'id': 1001,
                    'contact_id': 1,
                    'company_id': 101,
                    'type_interaction': 'Réunion',
                    'date_interaction': (datetime.now() - timedelta(days=10)).isoformat(),
                    'resume': 'Kick-off projet E-commerce',
                    'details': 'Discussion des objectifs et du calendrier.',
                    'resultat': 'Positif',
                    'suivi_prevu': (datetime.now() - timedelta(days=3)).date().isoformat()
                },
                {
                    'id': 1002,
                    'contact_id': 2,
                    'company_id': 102,
                    'type_interaction': 'Appel',
                    'date_interaction': (datetime.now() - timedelta(days=5)).isoformat(),
                    'resume': 'Point technique app mobile',
                    'details': 'Questions sur l\'API backend.',
                    'resultat': 'En cours',
                    'suivi_prevu': datetime.now().date().isoformat()
                }
            ]
            
            for interaction in interactions_demo:
                self.db.execute_update('''
                    INSERT OR REPLACE INTO interactions 
                    (id, contact_id, company_id, type_interaction, date_interaction, resume, details, resultat, suivi_prevu, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    interaction['id'],
                    interaction['contact_id'],
                    interaction['company_id'],
                    interaction['type_interaction'],
                    interaction['date_interaction'],
                    interaction['resume'],
                    interaction['details'],
                    interaction['resultat'],
                    interaction['suivi_prevu'],
                    now_iso
                ))
            
            st.info("✅ Données de démonstration CRM créées en SQLite avec adresses structurées")
            
        except Exception as e:
            st.error(f"Erreur création données démo CRM: {e}")

    # --- Propriétés de compatibilité (pour l'interface existante) ---
    @property
    def contacts(self):
        """Propriété pour maintenir compatibilité avec l'interface existante"""
        if self.use_sqlite:
            return self.get_all_contacts()
        else:
            return getattr(self, '_contacts', [])
    
    @contacts.setter
    def contacts(self, value):
        if not self.use_sqlite:
            self._contacts = value
    
    @property
    def entreprises(self):
        """Propriété pour maintenir compatibilité avec l'interface existante"""
        if self.use_sqlite:
            return self.get_all_companies()
        else:
            return getattr(self, '_entreprises', [])
    
    @entreprises.setter
    def entreprises(self, value):
        if not self.use_sqlite:
            self._entreprises = value
    
    @property
    def interactions(self):
        """Propriété pour maintenir compatibilité avec l'interface existante"""
        if self.use_sqlite:
            return self.get_all_interactions()
        else:
            return getattr(self, '_interactions', [])
    
    @interactions.setter
    def interactions(self, value):
        if not self.use_sqlite:
            self._interactions = value

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

    # --- Fonctions utilitaires pour adresses ---
    def format_adresse_complete(self, entreprise_data):
        """Formate une adresse complète à partir des champs séparés"""
        if not entreprise_data:
            return "N/A"
        
        parts = []
        
        # Adresse de rue
        if entreprise_data.get('adresse'):
            parts.append(entreprise_data['adresse'])
        
        # Ville, Province Code_postal
        ville_province_postal = []
        if entreprise_data.get('ville'):
            ville_province_postal.append(entreprise_data['ville'])
        if entreprise_data.get('province'):
            ville_province_postal.append(entreprise_data['province'])
        if entreprise_data.get('code_postal'):
            ville_province_postal.append(entreprise_data['code_postal'])
        
        if ville_province_postal:
            parts.append(', '.join(ville_province_postal))
        
        # Pays
        if entreprise_data.get('pays'):
            parts.append(entreprise_data['pays'])
        
        return '\n'.join(parts) if parts else "N/A"

    # =========================================================================
    # MÉTHODES SQLITE POUR PRODUITS MÉTALLURGIQUES
    # =========================================================================

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

    def ajuster_stock_produit(self, id_produit, nouvelle_quantite, motif="Ajustement manuel"):
        """Ajuste le stock d'un produit"""
        if not self.use_sqlite:
            # En mode JSON, mise à jour directe
            for p in getattr(self, '_produits', []):
                if p.get('id') == id_produit:
                    p['stock_disponible'] = nouvelle_quantite
                    self.sauvegarder_donnees_crm()
                    return True
            return False
        
        try:
            rows_affected = self.db.execute_update(
                "UPDATE produits SET stock_disponible = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (nouvelle_quantite, id_produit)
            )
            
            if rows_affected > 0:
                st.success(f"✅ Stock ajusté: {nouvelle_quantite}")
                # Ici on pourrait enregistrer un historique des mouvements de stock
            
            return rows_affected > 0
            
        except Exception as e:
            st.error(f"Erreur ajustement stock: {e}")
            return False

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

    # --- Méthodes SQLite pour Companies (Entreprises) avec adresses structurées ---
    def get_all_companies(self):
        """Récupère toutes les entreprises depuis SQLite"""
        if not self.use_sqlite:
            return getattr(self, '_entreprises', [])
        
        try:
            rows = self.db.execute_query('''
                SELECT c.*, co.prenom as contact_prenom, co.nom_famille as contact_nom
                FROM companies c
                LEFT JOIN contacts co ON c.contact_principal_id = co.id
                ORDER BY c.nom
            ''')
            
            companies = []
            for row in rows:
                company = dict(row)
                # Mapping pour compatibilité interface
                company['id'] = company['id']
                # Ajouter l'adresse formatée pour l'affichage
                company['adresse_complete'] = self.format_adresse_complete(company)
                companies.append(company)
            
            return companies
        except Exception as e:
            st.error(f"Erreur récupération entreprises: {e}")
            return []
    
    def ajouter_entreprise(self, data_entreprise):
        """Ajoute une nouvelle entreprise en SQLite avec adresses structurées"""
        if not self.use_sqlite:
            return self._ajouter_entreprise_json(data_entreprise)
        
        try:
            now_iso = datetime.now().isoformat()
            
            # Vérifier quelles colonnes existent dans la table
            columns_info = self.db.execute_query("PRAGMA table_info(companies)")
            existing_columns = [col['name'] for col in columns_info]
            
            # Construire la requête dynamiquement selon les colonnes disponibles
            base_columns = ['nom', 'secteur', 'site_web', 'contact_principal_id', 'notes', 'created_at', 'updated_at']
            address_columns = ['adresse', 'ville', 'province', 'code_postal', 'pays']
            
            # Colonnes à insérer
            columns_to_insert = []
            values_to_insert = []
            placeholders = []
            
            # Ajouter les colonnes de base
            for col in base_columns:
                if col in existing_columns:
                    columns_to_insert.append(col)
                    if col == 'created_at' or col == 'updated_at':
                        values_to_insert.append(now_iso)
                    else:
                        values_to_insert.append(data_entreprise.get(col))
                    placeholders.append('?')
            
            # Ajouter les colonnes d'adresse si elles existent
            for col in address_columns:
                if col in existing_columns:
                    columns_to_insert.append(col)
                    values_to_insert.append(data_entreprise.get(col))
                    placeholders.append('?')
            
            # Construire et exécuter la requête
            query = f'''
                INSERT INTO companies 
                ({', '.join(columns_to_insert)})
                VALUES ({', '.join(placeholders)})
            '''
            
            company_id = self.db.execute_insert(query, tuple(values_to_insert))
            
            if company_id:
                st.success(f"✅ Entreprise créée avec l'ID #{company_id}")
            
            return company_id
            
        except Exception as e:
            st.error(f"Erreur ajout entreprise: {e}")
            st.error(f"Détails: Colonnes disponibles: {existing_columns if 'existing_columns' in locals() else 'Inconnues'}")
            return None
    
    def modifier_entreprise(self, id_entreprise, data_entreprise):
        """Modifie une entreprise existante en SQLite avec adresses structurées"""
        if not self.use_sqlite:
            return self._modifier_entreprise_json(id_entreprise, data_entreprise)
        
        try:
            now_iso = datetime.now().isoformat()
            
            # Vérifier quelles colonnes existent dans la table
            columns_info = self.db.execute_query("PRAGMA table_info(companies)")
            existing_columns = [col['name'] for col in columns_info]
            
            # Construire la requête dynamiquement selon les champs fournis ET les colonnes disponibles
            update_fields = []
            params = []
            
            field_mapping = {
                'nom': 'nom',
                'secteur': 'secteur', 
                'adresse': 'adresse',
                'ville': 'ville',
                'province': 'province',
                'code_postal': 'code_postal',
                'pays': 'pays',
                'site_web': 'site_web',
                'contact_principal_id': 'contact_principal_id',
                'notes': 'notes'
            }
            
            for field, db_field in field_mapping.items():
                # Vérifier que le champ est dans les données ET que la colonne existe
                if field in data_entreprise and db_field in existing_columns:
                    update_fields.append(f"{db_field} = ?")
                    params.append(data_entreprise[field])
            
            if update_fields:
                # Ajouter updated_at si la colonne existe
                if 'updated_at' in existing_columns:
                    update_fields.append("updated_at = ?")
                    params.append(now_iso)
                
                params.append(id_entreprise)
                
                query = f"UPDATE companies SET {', '.join(update_fields)} WHERE id = ?"
                rows_affected = self.db.execute_update(query, tuple(params))
                
                if rows_affected > 0:
                    st.success(f"✅ Entreprise #{id_entreprise} mise à jour")
                
                return rows_affected > 0
            
            st.warning("Aucun champ valide à mettre à jour")
            return False
            
        except Exception as e:
            st.error(f"Erreur modification entreprise: {e}")
            return False
    
    def supprimer_entreprise(self, id_entreprise):
        """Supprime une entreprise et ses données associées"""
        if not self.use_sqlite:
            return self._supprimer_entreprise_json(id_entreprise)
        
        try:
            # Supprimer en cascade
            self.db.execute_update("UPDATE contacts SET company_id = NULL WHERE company_id = ?", (id_entreprise,))
            self.db.execute_update("DELETE FROM interactions WHERE company_id = ?", (id_entreprise,))
            rows_affected = self.db.execute_update("DELETE FROM companies WHERE id = ?", (id_entreprise,))
            return rows_affected > 0
            
        except Exception as e:
            st.error(f"Erreur suppression entreprise: {e}")
            return False
    
    def get_entreprise_by_id(self, id_entreprise):
        """Récupère une entreprise par son ID"""
        if not self.use_sqlite:
            return next((e for e in getattr(self, '_entreprises', []) if e.get('id') == id_entreprise), None)
        
        try:
            rows = self.db.execute_query("SELECT * FROM companies WHERE id = ?", (id_entreprise,))
            if rows:
                company = dict(rows[0])
                company['adresse_complete'] = self.format_adresse_complete(company)
                return company
            return None
        except Exception as e:
            st.error(f"Erreur récupération entreprise {id_entreprise}: {e}")
            return None

    # --- Méthodes SQLite pour Contacts ---
    def get_all_contacts(self):
        """Récupère tous les contacts depuis SQLite"""
        if not self.use_sqlite:
            return getattr(self, '_contacts', [])
        
        try:
            rows = self.db.execute_query('''
                SELECT c.*, co.nom as company_nom
                FROM contacts c
                LEFT JOIN companies co ON c.company_id = co.id
                ORDER BY c.nom_famille, c.prenom
            ''')
            
            contacts = []
            for row in rows:
                contact = dict(row)
                # Mapping pour compatibilité interface existante
                contact['entreprise_id'] = contact['company_id']  # Compatibilité
                contact['role'] = contact['role_poste']  # Compatibilité
                contacts.append(contact)
            
            return contacts
        except Exception as e:
            st.error(f"Erreur récupération contacts: {e}")
            return []
    
    def ajouter_contact(self, data_contact):
        """Ajoute un nouveau contact en SQLite"""
        if not self.use_sqlite:
            return self._ajouter_contact_json(data_contact)
        
        try:
            now_iso = datetime.now().isoformat()
            
            query = '''
                INSERT INTO contacts 
                (prenom, nom_famille, email, telephone, company_id, role_poste, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            # Mapping des champs pour compatibilité
            company_id = data_contact.get('entreprise_id') or data_contact.get('company_id')
            role_poste = data_contact.get('role') or data_contact.get('role_poste')
            
            contact_id = self.db.execute_insert(query, (
                data_contact.get('prenom'),
                data_contact.get('nom_famille'),
                data_contact.get('email'),
                data_contact.get('telephone'),
                company_id,
                role_poste,
                data_contact.get('notes'),
                now_iso,
                now_iso
            ))
            
            return contact_id
            
        except Exception as e:
            st.error(f"Erreur ajout contact: {e}")
            return None
    
    def modifier_contact(self, id_contact, data_contact):
        """Modifie un contact existant en SQLite"""
        if not self.use_sqlite:
            return self._modifier_contact_json(id_contact, data_contact)
        
        try:
            now_iso = datetime.now().isoformat()
            
            # Construire la requête dynamiquement
            update_fields = []
            params = []
            
            field_mapping = {
                'prenom': 'prenom',
                'nom_famille': 'nom_famille',
                'email': 'email',
                'telephone': 'telephone',
                'entreprise_id': 'company_id',
                'company_id': 'company_id',
                'role': 'role_poste',
                'role_poste': 'role_poste',
                'notes': 'notes'
            }
            
            # Utiliser un set pour éviter les champs en double (ex: entreprise_id et company_id)
            processed_db_fields = set()
            for field, db_field in field_mapping.items():
                if field in data_contact and db_field not in processed_db_fields:
                    update_fields.append(f"{db_field} = ?")
                    params.append(data_contact[field])
                    processed_db_fields.add(db_field)

            if update_fields:
                update_fields.append("updated_at = ?")
                params.append(now_iso)
                params.append(id_contact)
                
                query = f"UPDATE contacts SET {', '.join(update_fields)} WHERE id = ?"
                rows_affected = self.db.execute_update(query, tuple(params))
                return rows_affected > 0
            
            return False
            
        except Exception as e:
            st.error(f"Erreur modification contact: {e}")
            return False
    
    def supprimer_contact(self, id_contact):
        """Supprime un contact et ses données associées"""
        if not self.use_sqlite:
            return self._supprimer_contact_json(id_contact)
        
        try:
            # Supprimer en cascade
            self.db.execute_update("DELETE FROM interactions WHERE contact_id = ?", (id_contact,))
            self.db.execute_update("UPDATE companies SET contact_principal_id = NULL WHERE contact_principal_id = ?", (id_contact,))
            rows_affected = self.db.execute_update("DELETE FROM contacts WHERE id = ?", (id_contact,))
            return rows_affected > 0
            
        except Exception as e:
            st.error(f"Erreur suppression contact: {e}")
            return False
    
    def get_contact_by_id(self, id_contact):
        """Récupère un contact par son ID"""
        if not self.use_sqlite:
            return next((c for c in getattr(self, '_contacts', []) if c.get('id') == id_contact), None)
        
        try:
            rows = self.db.execute_query("SELECT * FROM contacts WHERE id = ?", (id_contact,))
            if rows:
                contact = dict(rows[0])
                # Mapping pour compatibilité
                contact['entreprise_id'] = contact['company_id']
                contact['role'] = contact['role_poste']
                return contact
            return None
        except Exception as e:
            st.error(f"Erreur récupération contact {id_contact}: {e}")
            return None
    
    def get_contacts_by_entreprise_id(self, id_entreprise):
        """Récupère tous les contacts d'une entreprise"""
        if not self.use_sqlite:
            return [c for c in getattr(self, '_contacts', []) if c.get('entreprise_id') == id_entreprise]
        
        try:
            rows = self.db.execute_query("SELECT * FROM contacts WHERE company_id = ?", (id_entreprise,))
            contacts = []
            for row in rows:
                contact = dict(row)
                contact['entreprise_id'] = contact['company_id']
                contact['role'] = contact['role_poste']
                contacts.append(contact)
            return contacts
        except Exception as e:
            st.error(f"Erreur récupération contacts entreprise {id_entreprise}: {e}")
            return []

    # --- Méthodes SQLite pour Interactions ---
    def get_all_interactions(self):
        """Récupère toutes les interactions depuis SQLite"""
        if not self.use_sqlite:
            return getattr(self, '_interactions', [])
        
        try:
            rows = self.db.execute_query('''
                SELECT i.*, 
                       c.prenom || ' ' || c.nom_famille as contact_nom,
                       co.nom as company_nom
                FROM interactions i
                LEFT JOIN contacts c ON i.contact_id = c.id
                LEFT JOIN companies co ON i.company_id = co.id
                ORDER BY i.date_interaction DESC
            ''')
            
            interactions = []
            for row in rows:
                interaction = dict(row)
                # Mapping pour compatibilité
                interaction['entreprise_id'] = interaction['company_id']
                interaction['type'] = interaction['type_interaction']
                interactions.append(interaction)
            
            return interactions
        except Exception as e:
            st.error(f"Erreur récupération interactions: {e}")
            return []
    
    def ajouter_interaction(self, data_interaction):
        """Ajoute une nouvelle interaction en SQLite"""
        if not self.use_sqlite:
            return self._ajouter_interaction_json(data_interaction)
        
        try:
            now_iso = datetime.now().isoformat()
            
            query = '''
                INSERT INTO interactions 
                (contact_id, company_id, type_interaction, date_interaction, resume, details, resultat, suivi_prevu, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            # Mapping des champs pour compatibilité
            company_id = data_interaction.get('entreprise_id') or data_interaction.get('company_id')
            type_interaction = data_interaction.get('type') or data_interaction.get('type_interaction')
            
            interaction_id = self.db.execute_insert(query, (
                data_interaction.get('contact_id'),
                company_id,
                type_interaction,
                data_interaction.get('date_interaction'),
                data_interaction.get('resume'),
                data_interaction.get('details'),
                data_interaction.get('resultat'),
                data_interaction.get('suivi_prevu'),
                now_iso
            ))
            
            return interaction_id
            
        except Exception as e:
            st.error(f"Erreur ajout interaction: {e}")
            return None
    
    def modifier_interaction(self, id_interaction, data_interaction):
        """Modifie une interaction existante en SQLite"""
        if not self.use_sqlite:
            return self._modifier_interaction_json(id_interaction, data_interaction)
        
        try:
            # Construire la requête dynamiquement
            update_fields = []
            params = []
            
            field_mapping = {
                'contact_id': 'contact_id',
                'entreprise_id': 'company_id',
                'company_id': 'company_id',
                'type': 'type_interaction',
                'type_interaction': 'type_interaction',
                'date_interaction': 'date_interaction',
                'resume': 'resume',
                'details': 'details',
                'resultat': 'resultat',
                'suivi_prevu': 'suivi_prevu'
            }
            
            processed_db_fields = set()
            for field, db_field in field_mapping.items():
                if field in data_interaction and db_field not in processed_db_fields:
                    update_fields.append(f"{db_field} = ?")
                    params.append(data_interaction[field])
                    processed_db_fields.add(db_field)

            if update_fields:
                params.append(id_interaction)
                query = f"UPDATE interactions SET {', '.join(update_fields)} WHERE id = ?"
                rows_affected = self.db.execute_update(query, tuple(params))
                return rows_affected > 0
            
            return False
            
        except Exception as e:
            st.error(f"Erreur modification interaction: {e}")
            return False
    
    def supprimer_interaction(self, id_interaction):
        """Supprime une interaction"""
        if not self.use_sqlite:
            return self._supprimer_interaction_json(id_interaction)
        
        try:
            rows_affected = self.db.execute_update("DELETE FROM interactions WHERE id = ?", (id_interaction,))
            return rows_affected > 0
        except Exception as e:
            st.error(f"Erreur suppression interaction: {e}")
            return False
    
    def get_interaction_by_id(self, id_interaction):
        """Récupère une interaction par son ID"""
        if not self.use_sqlite:
            return next((i for i in getattr(self, '_interactions', []) if i.get('id') == id_interaction), None)
        
        try:
            rows = self.db.execute_query("SELECT * FROM interactions WHERE id = ?", (id_interaction,))
            if rows:
                interaction = dict(rows[0])
                # Mapping pour compatibilité
                interaction['entreprise_id'] = interaction['company_id']
                interaction['type'] = interaction['type_interaction']
                return interaction
            return None
        except Exception as e:
            st.error(f"Erreur récupération interaction {id_interaction}: {e}")
            return None
    
    def get_interactions_for_contact(self, id_contact):
        """Récupère toutes les interactions d'un contact"""
        if not self.use_sqlite:
            return sorted([i for i in getattr(self, '_interactions', []) if i.get('contact_id') == id_contact], 
                         key=lambda x: x.get('date_interaction'), reverse=True)
        
        try:
            rows = self.db.execute_query(
                "SELECT * FROM interactions WHERE contact_id = ? ORDER BY date_interaction DESC", 
                (id_contact,)
            )
            interactions = []
            for row in rows:
                interaction = dict(row)
                interaction['entreprise_id'] = interaction['company_id']
                interaction['type'] = interaction['type_interaction']
                interactions.append(interaction)
            return interactions
        except Exception as e:
            st.error(f"Erreur récupération interactions contact {id_contact}: {e}")
            return []
    
    def get_interactions_for_entreprise(self, id_entreprise):
        """Récupère toutes les interactions d'une entreprise"""
        if not self.use_sqlite:
            return sorted([i for i in getattr(self, '_interactions', []) if i.get('entreprise_id') == id_entreprise], 
                         key=lambda x: x.get('date_interaction'), reverse=True)
        
        try:
            rows = self.db.execute_query(
                "SELECT * FROM interactions WHERE company_id = ? ORDER BY date_interaction DESC", 
                (id_entreprise,)
            )
            interactions = []
            for row in rows:
                interaction = dict(row)
                interaction['entreprise_id'] = interaction['company_id']
                interaction['type'] = interaction['type_interaction']
                interactions.append(interaction)
            return interactions
        except Exception as e:
            st.error(f"Erreur récupération interactions entreprise {id_entreprise}: {e}")
            return []

    # --- Méthodes JSON (Rétrocompatibilité) ---
    def charger_donnees_crm(self):
        """Charge les données CRM depuis JSON (rétrocompatibilité)"""
        if self.use_sqlite:
            return
        
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._contacts = data.get('contacts', [])
                    self._entreprises = data.get('entreprises', [])
                    self._interactions = data.get('interactions', [])
                    self._produits = data.get('produits', [])  # Ajout pour les produits
                    
                    self.next_contact_id = self._get_next_id(self._contacts)
                    self.next_entreprise_id = self._get_next_id(self._entreprises)
                    self.next_interaction_id = self._get_next_id(self._interactions)
                    self.next_produit_id = self._get_next_id(self._produits)  # Ajout pour les produits
            else:
                self._initialiser_donnees_demo_crm()
        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur critique lors du chargement des données CRM: {e}. Initialisation avec données de démo.")
            self._initialiser_donnees_demo_crm()

    def _get_next_id(self, entity_list):
        """Utilitaire pour calculer le prochain ID"""
        if not entity_list:
            return 1
        return max(item.get('id', 0) for item in entity_list) + 1

    def _initialiser_donnees_demo_crm(self):
        """Initialise des données de démonstration JSON avec adresses structurées et produits"""
        if self.use_sqlite:
            return
        
        now_iso = datetime.now().isoformat()
        self._contacts = [
            {'id':1, 'prenom':'Alice', 'nom_famille':'Martin', 'email':'alice@techcorp.com', 'telephone':'0102030405', 'entreprise_id':101, 'role':'Responsable Marketing', 'notes':'Contact principal pour le projet E-commerce.', 'date_creation': now_iso, 'date_modification': now_iso},
            {'id':2, 'prenom':'Bob', 'nom_famille':'Durand', 'email':'bob@startupxyz.com', 'telephone':'0607080910', 'entreprise_id':102, 'role':'CTO', 'notes':'Décideur technique pour l\'application mobile.', 'date_creation': now_iso, 'date_modification': now_iso},
            {'id':3, 'prenom':'Claire', 'nom_famille':'Leroy', 'email':'claire.leroy@megacorp.com', 'telephone':'0708091011', 'entreprise_id':103, 'role':'Chef de projet CRM', 'notes':'Très organisée, demande des rapports réguliers.', 'date_creation': now_iso, 'date_modification': now_iso}
        ]
        self._entreprises = [
            {'id':101, 'nom':'TechCorp Inc.', 'secteur':'Technologie', 'adresse':'123 Rue de la Paix', 'ville':'Paris', 'province':'Île-de-France', 'code_postal':'75001', 'pays':'France', 'site_web':'techcorp.com', 'contact_principal_id':1, 'notes':'Client pour le projet E-commerce. Actif.', 'date_creation': now_iso, 'date_modification': now_iso},
            {'id':102, 'nom':'StartupXYZ', 'secteur':'Logiciel', 'adresse':'456 Innovation Drive', 'ville':'San Francisco', 'province':'California', 'code_postal':'94102', 'pays':'États-Unis', 'site_web':'startup.xyz', 'contact_principal_id':2, 'notes':'Client pour l\'app mobile. En phase de développement.', 'date_creation': now_iso, 'date_modification': now_iso},
            {'id':103, 'nom':'MegaCorp Ltd', 'secteur':'Finance', 'adresse':'789 Boulevard des Affaires', 'ville':'Montréal', 'province':'Québec', 'code_postal':'H3B 1A1', 'pays':'Canada', 'site_web':'megacorp.com', 'contact_principal_id':3, 'notes':'Projet CRM terminé. Potentiel pour maintenance.', 'date_creation': now_iso, 'date_modification': now_iso}
        ]
        self._interactions = [
            {'id':1001, 'contact_id':1, 'entreprise_id':101, 'type':'Réunion', 'date_interaction': (datetime.now() - timedelta(days=10)).isoformat(), 'resume':'Kick-off projet E-commerce', 'details': 'Discussion des objectifs et du calendrier.', 'resultat':'Positif', 'suivi_prevu': (datetime.now() - timedelta(days=3)).isoformat()},
            {'id':1002, 'contact_id':2, 'entreprise_id':102, 'type':'Appel', 'date_interaction': (datetime.now() - timedelta(days=5)).isoformat(), 'resume':'Point technique app mobile', 'details': 'Questions sur l\'API backend.', 'resultat':'En cours', 'suivi_prevu': datetime.now().isoformat()}
        ]
        
        # Ajout des produits de démonstration en mode JSON
        self._produits = [
            {'id':1, 'code_produit':'AC-PLT-001', 'nom':'Plaque Acier S235', 'description':'Plaque d\'acier de construction standard', 'categorie':'Acier', 'materiau':'Acier', 'nuance':'S235', 'dimensions':'2000x1000x10mm', 'unite_vente':'kg', 'prix_unitaire':2.50, 'stock_disponible':150.0, 'stock_minimum':50.0, 'fournisseur_principal':'ArcelorMittal', 'notes_techniques':'Limite élastique: 235 MPa. Soudable.', 'actif':True, 'date_creation': now_iso, 'date_modification': now_iso},
            {'id':2, 'code_produit':'AL-TUB-002', 'nom':'Tube Aluminium 6061-T6', 'description':'Tube rond en aluminium traité thermiquement', 'categorie':'Aluminium', 'materiau':'Aluminium', 'nuance':'6061-T6', 'dimensions':'Ø50x3mm', 'unite_vente':'m', 'prix_unitaire':15.80, 'stock_disponible':85.0, 'stock_minimum':20.0, 'fournisseur_principal':'Hydro Aluminium', 'notes_techniques':'Excellente résistance à la corrosion. Usinable.', 'actif':True, 'date_creation': now_iso, 'date_modification': now_iso}
        ]
        
        self.next_contact_id = self._get_next_id(self._contacts)
        self.next_entreprise_id = self._get_next_id(self._entreprises)
        self.next_interaction_id = self._get_next_id(self._interactions)
        self.next_produit_id = self._get_next_id(self._produits)
        self.sauvegarder_donnees_crm()

    def sauvegarder_donnees_crm(self):
        """Sauvegarde les données CRM en JSON (rétrocompatibilité)"""
        if self.use_sqlite:
            return
        
        try:
            data = {
                'contacts': self._contacts,
                'entreprises': self._entreprises,
                'interactions': self._interactions,
                'produits': self._produits,  # Ajout pour les produits
                'next_contact_id': self.next_contact_id,
                'next_entreprise_id': self.next_entreprise_id,
                'next_interaction_id': self.next_interaction_id,
                'next_produit_id': self.next_produit_id,  # Ajout pour les produits
                'last_update': datetime.now().isoformat()
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur critique lors de la sauvegarde des données CRM: {e}")

    # Méthodes JSON pour les produits (rétrocompatibilité)
    def _ajouter_produit_json(self, data_produit):
        data_produit['id'] = self.next_produit_id
        data_produit['date_creation'] = datetime.now().isoformat()
        data_produit['date_modification'] = datetime.now().isoformat()
        data_produit['actif'] = True
        self._produits.append(data_produit)
        self.next_produit_id += 1
        self.sauvegarder_donnees_crm()
        return data_produit['id']

    def _modifier_produit_json(self, id_produit, data_produit):
        for i, p in enumerate(self._produits):
            if p['id'] == id_produit:
                updated_produit = {**p, **data_produit, 'date_modification': datetime.now().isoformat()}
                self._produits[i] = updated_produit
                self.sauvegarder_donnees_crm()
                return True
        return False

    def _supprimer_produit_json(self, id_produit):
        # En mode JSON, suppression logique par défaut
        for p in self._produits:
            if p['id'] == id_produit:
                p['actif'] = False
                p['date_modification'] = datetime.now().isoformat()
                self.sauvegarder_donnees_crm()
                return True
        return False

    # Méthodes JSON (implémentation simplifiée pour rétrocompatibilité)
    def _ajouter_contact_json(self, data_contact):
        data_contact['id'] = self.next_contact_id
        data_contact['date_creation'] = datetime.now().isoformat()
        data_contact['date_modification'] = datetime.now().isoformat()
        self._contacts.append(data_contact)
        self.next_contact_id += 1
        self.sauvegarder_donnees_crm()
        return data_contact['id']

    def _modifier_contact_json(self, id_contact, data_contact):
        for i, c in enumerate(self._contacts):
            if c['id'] == id_contact:
                updated_contact = {**c, **data_contact, 'date_modification': datetime.now().isoformat()}
                self._contacts[i] = updated_contact
                self.sauvegarder_donnees_crm()
                return True
        return False

    def _supprimer_contact_json(self, id_contact):
        self._contacts = [c for c in self._contacts if c['id'] != id_contact]
        self._interactions = [i for i in self._interactions if i.get('contact_id') != id_contact]
        for entreprise in self._entreprises:
            if entreprise.get('contact_principal_id') == id_contact:
                entreprise['contact_principal_id'] = None
        self.sauvegarder_donnees_crm()
        return True

    def _ajouter_entreprise_json(self, data_entreprise):
        data_entreprise['id'] = self.next_entreprise_id
        data_entreprise['date_creation'] = datetime.now().isoformat()
        data_entreprise['date_modification'] = datetime.now().isoformat()
        self._entreprises.append(data_entreprise)
        self.next_entreprise_id += 1
        self.sauvegarder_donnees_crm()
        return data_entreprise['id']

    def _modifier_entreprise_json(self, id_entreprise, data_entreprise):
        for i, e in enumerate(self._entreprises):
            if e['id'] == id_entreprise:
                updated_entreprise = {**e, **data_entreprise, 'date_modification': datetime.now().isoformat()}
                self._entreprises[i] = updated_entreprise
                self.sauvegarder_donnees_crm()
                return True
        return False

    def _supprimer_entreprise_json(self, id_entreprise):
        self._entreprises = [e for e in self._entreprises if e['id'] != id_entreprise]
        for contact in self._contacts:
            if contact.get('entreprise_id') == id_entreprise:
                contact['entreprise_id'] = None
        self._interactions = [i for i in self._interactions if not (i.get('entreprise_id') == id_entreprise and i.get('contact_id') is None)]
        self.sauvegarder_donnees_crm()
        return True

    def _ajouter_interaction_json(self, data_interaction):
        data_interaction['id'] = self.next_interaction_id
        if 'date_interaction' not in data_interaction:
            data_interaction['date_interaction'] = datetime.now().isoformat()
        self._interactions.append(data_interaction)
        self.next_interaction_id += 1
        self.sauvegarder_donnees_crm()
        return data_interaction['id']

    def _modifier_interaction_json(self, id_interaction, data_interaction):
        for i, inter in enumerate(self._interactions):
            if inter['id'] == id_interaction:
                updated_interaction = {**inter, **data_interaction}
                self._interactions[i] = updated_interaction
                self.sauvegarder_donnees_crm()
                return True
        return False

    def _supprimer_interaction_json(self, id_interaction):
        self._interactions = [i for i in self._interactions if i.get('id') != id_interaction]
        self.sauvegarder_donnees_crm()
        return True

# =========================================================================
# FONCTIONS D'AFFICHAGE STREAMLIT POUR PRODUITS
# =========================================================================

def render_crm_produits_tab(crm_manager: GestionnaireCRM):
    """Interface Streamlit pour la gestion des produits métallurgiques"""
    st.subheader("🔧 Catalogue des Produits")

    # Statistiques en haut
    stats = crm_manager.get_statistics_produits()
    
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
        if st.button("➕ Nouveau Produit", key="crm_create_product_btn", use_container_width=True):
            st.session_state.crm_action = "create_product"
            st.session_state.crm_selected_id = None

    with col_search_product:
        search_product_term = st.text_input("Rechercher un produit...", key="crm_product_search")

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
        filtered_products = crm_manager.search_produits(search_product_term)
    elif filtre_stock_bas:
        filtered_products = crm_manager.get_produits_stock_bas()
    elif filtre_categorie != "Toutes":
        filtered_products = crm_manager.get_produits_by_categorie(filtre_categorie)
    else:
        filtered_products = crm_manager.produits

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
            key="crm_product_action_select"
        )

        if selected_product_id_action:
            col_act1, col_act2, col_act3, col_act4 = st.columns(4)
            with col_act1:
                if st.button("👁️ Voir Détails", key=f"crm_view_product_{selected_product_id_action}", use_container_width=True):
                    st.session_state.crm_action = "view_product_details"
                    st.session_state.crm_selected_id = selected_product_id_action
            with col_act2:
                if st.button("✏️ Modifier", key=f"crm_edit_product_{selected_product_id_action}", use_container_width=True):
                    st.session_state.crm_action = "edit_product"
                    st.session_state.crm_selected_id = selected_product_id_action
            with col_act3:
                if st.button("📦 Ajuster Stock", key=f"crm_adjust_stock_{selected_product_id_action}", use_container_width=True):
                    st.session_state.crm_action = "adjust_stock"
                    st.session_state.crm_selected_id = selected_product_id_action
            with col_act4:
                if st.button("🗑️ Supprimer", key=f"crm_delete_product_{selected_product_id_action}", use_container_width=True):
                    st.session_state.crm_confirm_delete_product_id = selected_product_id_action
    else:
        st.info("Aucun produit correspondant aux filtres." if search_product_term or filtre_stock_bas or filtre_categorie != "Toutes" else "Aucun produit enregistré.")

    # Gestion des confirmations de suppression
    if 'crm_confirm_delete_product_id' in st.session_state and st.session_state.crm_confirm_delete_product_id:
        product_to_delete = crm_manager.get_produit_by_id(st.session_state.crm_confirm_delete_product_id)
        if product_to_delete:
            st.warning(f"Êtes-vous sûr de vouloir supprimer le produit {product_to_delete.get('code_produit')} - {product_to_delete.get('nom')} ?")
            
            col_del_type = st.columns(1)[0]
            suppression_definitive = col_del_type.checkbox("Suppression définitive (ne peut pas être annulée)", key="suppression_definitive_product")
            
            col_del_confirm, col_del_cancel = st.columns(2)
            if col_del_confirm.button("Oui, supprimer ce produit", type="primary", key="crm_confirm_delete_product_btn_final"):
                if crm_manager.supprimer_produit(st.session_state.crm_confirm_delete_product_id, suppression_definitive):
                    st.success("Produit supprimé avec succès.")
                else:
                    st.error("Erreur lors de la suppression.")
                del st.session_state.crm_confirm_delete_product_id
                st.rerun()
            if col_del_cancel.button("Annuler la suppression", key="crm_cancel_delete_product_btn_final"):
                del st.session_state.crm_confirm_delete_product_id
                st.rerun()

def render_crm_product_form(crm_manager: GestionnaireCRM, product_data=None):
    """Formulaire pour ajouter/modifier un produit"""
    form_title = "➕ Ajouter un Nouveau Produit" if product_data is None else f"✏️ Modifier le Produit #{product_data.get('id')}"
    
    with st.expander(form_title, expanded=True):
        with st.form(key="crm_product_form_in_expander", clear_on_submit=False):
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
                    st.session_state.crm_action = None
                    st.session_state.crm_selected_id = None
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
                        if crm_manager.modifier_produit(product_data['id'], new_product_data):
                            st.success(f"✅ Produit #{product_data['id']} mis à jour !")
                        else:
                            st.error("Erreur lors de la modification.")
                    else:
                        # Mode création
                        new_id = crm_manager.ajouter_produit(new_product_data)
                        if new_id:
                            st.success(f"✅ Nouveau produit #{new_id} ajouté !")
                        else:
                            st.error("Erreur lors de la création.")

                    st.session_state.crm_action = None
                    st.session_state.crm_selected_id = None
                    st.rerun()

def render_crm_product_details(crm_manager: GestionnaireCRM, product_data):
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
            st.session_state.crm_action = "edit_product"
            st.rerun()
    
    with col_act2:
        if st.button("📦 Ajuster le stock", key="adjust_stock_from_details", use_container_width=True):
            st.session_state.crm_action = "adjust_stock"
            st.rerun()
    
    with col_act3:
        st.info("💡 Les devis sont maintenant gérés dans un module séparé.")

    if st.button("Retour à la liste des produits", key="back_to_products_list_from_details"):
        st.session_state.crm_action = None
        st.rerun()

def render_crm_stock_adjustment(crm_manager: GestionnaireCRM, product_data):
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
                st.session_state.crm_action = "view_product_details"
                st.rerun()

        if submitted:
            if crm_manager.ajuster_stock_produit(product_data['id'], nouveau_stock, motif):
                st.session_state.crm_action = "view_product_details"
                st.rerun()
            else:
                st.error("Erreur lors de l'ajustement du stock.")

# --- Fonctions d'affichage Streamlit avec adresses structurées ---

def render_crm_contacts_tab(crm_manager: GestionnaireCRM, projet_manager):
    st.subheader("👤 Liste des Contacts")

    col_create_contact, col_search_contact = st.columns([1, 2])
    with col_create_contact:
        if st.button("➕ Nouveau Contact", key="crm_create_contact_btn", use_container_width=True):
            st.session_state.crm_action = "create_contact"
            st.session_state.crm_selected_id = None

    with col_search_contact:
        search_contact_term = st.text_input("Rechercher un contact...", key="crm_contact_search")

    filtered_contacts = crm_manager.contacts
    if search_contact_term:
        term = search_contact_term.lower()
        filtered_contacts = [
            c for c in filtered_contacts if
            term in c.get('prenom', '').lower() or
            term in c.get('nom_famille', '').lower() or
            term in c.get('email', '').lower() or
            (crm_manager.get_entreprise_by_id(c.get('entreprise_id') or c.get('company_id')) and 
             term in crm_manager.get_entreprise_by_id(c.get('entreprise_id') or c.get('company_id')).get('nom','').lower())
        ]

    if filtered_contacts:
        contacts_data_display = []
        for contact in filtered_contacts:
            entreprise_id = contact.get('entreprise_id') or contact.get('company_id')
            entreprise = crm_manager.get_entreprise_by_id(entreprise_id)
            nom_entreprise = entreprise['nom'] if entreprise else "N/A"
            
            # Recherche des projets liés - adaptation pour SQLite
            projets_lies = []
            if hasattr(projet_manager, 'projets'):
                projets_lies = [p['nom_projet'] for p in projet_manager.projets 
                              if p.get('client_contact_id') == contact.get('id') or 
                              (p.get('client_entreprise_id') == entreprise_id and entreprise_id is not None) or
                              (p.get('client_company_id') == entreprise_id and entreprise_id is not None)]
            
            contacts_data_display.append({
                "ID": contact.get('id'),
                "Prénom": contact.get('prenom'),
                "Nom": contact.get('nom_famille'),
                "Email": contact.get('email'),
                "Téléphone": contact.get('telephone'),
                "Entreprise": nom_entreprise,
                "Rôle": contact.get('role') or contact.get('role_poste'),
                "Projets Liés": ", ".join(projets_lies) if projets_lies else "-"
            })
        st.dataframe(pd.DataFrame(contacts_data_display), use_container_width=True)

        st.markdown("---")
        st.markdown("### 🔧 Actions sur un contact")
        selected_contact_id_action = st.selectbox(
            "Contact:",
            options=[c['id'] for c in filtered_contacts],
            format_func=lambda cid: f"#{cid} - {next((c.get('prenom', '') + ' ' + c.get('nom_famille', '') for c in filtered_contacts if c.get('id') == cid), '')}",
            key="crm_contact_action_select"
        )

        if selected_contact_id_action:
            col_act1, col_act2, col_act3 = st.columns(3)
            with col_act1:
                if st.button("👁️ Voir Détails", key=f"crm_view_contact_{selected_contact_id_action}", use_container_width=True):
                    st.session_state.crm_action = "view_contact_details"
                    st.session_state.crm_selected_id = selected_contact_id_action
            with col_act2:
                if st.button("✏️ Modifier", key=f"crm_edit_contact_{selected_contact_id_action}", use_container_width=True):
                    st.session_state.crm_action = "edit_contact"
                    st.session_state.crm_selected_id = selected_contact_id_action
            with col_act3:
                if st.button("🗑️ Supprimer", key=f"crm_delete_contact_{selected_contact_id_action}", use_container_width=True):
                    st.session_state.crm_confirm_delete_contact_id = selected_contact_id_action
    else:
        st.info("Aucun contact correspondant aux filtres." if search_contact_term else "Aucun contact enregistré.")

    # Gestion des confirmations de suppression
    if 'crm_confirm_delete_contact_id' in st.session_state and st.session_state.crm_confirm_delete_contact_id:
        contact_to_delete = crm_manager.get_contact_by_id(st.session_state.crm_confirm_delete_contact_id)
        if contact_to_delete:
            st.warning(f"Êtes-vous sûr de vouloir supprimer le contact {contact_to_delete.get('prenom')} {contact_to_delete.get('nom_famille')} ? Cette action est irréversible.")
            col_del_confirm, col_del_cancel = st.columns(2)
            if col_del_confirm.button("Oui, supprimer ce contact", type="primary", key="crm_confirm_delete_contact_btn_final"):
                crm_manager.supprimer_contact(st.session_state.crm_confirm_delete_contact_id)
                st.success("Contact supprimé de SQLite.")
                del st.session_state.crm_confirm_delete_contact_id
                st.rerun()
            if col_del_cancel.button("Annuler la suppression", key="crm_cancel_delete_contact_btn_final"):
                del st.session_state.crm_confirm_delete_contact_id
                st.rerun()

def render_crm_contact_form(crm_manager: GestionnaireCRM, contact_data=None):
    form_title = "➕ Ajouter un Nouveau Contact (SQLite)" if contact_data is None else f"✏️ Modifier le Contact #{contact_data.get('id')} (SQLite)"
    
    with st.expander(form_title, expanded=True):
        with st.form(key="crm_contact_form_in_expander", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                prenom = st.text_input("Prénom *", value=contact_data.get('prenom', '') if contact_data else "")
                email = st.text_input("Email", value=contact_data.get('email', '') if contact_data else "")
                
                # Sélection d'entreprise - compatible SQLite
                entreprise_id_options = [("", "Aucune")] + [(e['id'], e['nom']) for e in crm_manager.entreprises]
                current_entreprise_id = contact_data.get('entreprise_id') or contact_data.get('company_id') if contact_data else ""
                entreprise_id = st.selectbox(
                    "Entreprise",
                    options=[opt_id for opt_id, _ in entreprise_id_options],
                    format_func=lambda opt_id: next((name for id_e, name in entreprise_id_options if id_e == opt_id), "Aucune"),
                    index=next((i for i, (opt_id, _) in enumerate(entreprise_id_options) if opt_id == current_entreprise_id), 0),
                    key="contact_form_entreprise_select"
                )

            with c2:
                nom_famille = st.text_input("Nom de famille *", value=contact_data.get('nom_famille', '') if contact_data else "")
                telephone = st.text_input("Téléphone", value=contact_data.get('telephone', '') if contact_data else "")
                role = st.text_input("Rôle/Fonction", value=(contact_data.get('role') or contact_data.get('role_poste', '')) if contact_data else "")

            notes = st.text_area("Notes", value=contact_data.get('notes', '') if contact_data else "", key="contact_form_notes")
            st.caption("* Champs obligatoires")

            col_submit, col_cancel_form = st.columns(2)
            with col_submit:
                submitted = st.form_submit_button("💾 Enregistrer SQLite", use_container_width=True)
            with col_cancel_form:
                if st.form_submit_button("❌ Annuler", use_container_width=True):
                    st.session_state.crm_action = None
                    st.session_state.crm_selected_id = None
                    st.rerun()

            if submitted:
                if not prenom or not nom_famille:
                    st.error("Le prénom et le nom de famille sont obligatoires.")
                else:
                    new_contact_data = {
                        'prenom': prenom,
                        'nom_famille': nom_famille,
                        'email': email,
                        'telephone': telephone,
                        'entreprise_id': entreprise_id if entreprise_id else None,
                        'company_id': entreprise_id if entreprise_id else None,
                        'role': role,
                        'role_poste': role,
                        'notes': notes
                    }
                    if contact_data:
                        if crm_manager.modifier_contact(contact_data['id'], new_contact_data):
                            st.success(f"Contact #{contact_data['id']} mis à jour en SQLite !")
                        else:
                            st.error("Erreur lors de la modification SQLite.")
                    else:
                        new_id = crm_manager.ajouter_contact(new_contact_data)
                        if new_id:
                            st.success(f"Nouveau contact #{new_id} ajouté en SQLite !")
                        else:
                            st.error("Erreur lors de la création SQLite.")

                    st.session_state.crm_action = None
                    st.session_state.crm_selected_id = None
                    st.rerun()

def render_crm_contact_details(crm_manager: GestionnaireCRM, projet_manager, contact_data):
    if not contact_data:
        st.error("Contact non trouvé.")
        return

    st.subheader(f"👤 Détails du Contact: {contact_data.get('prenom')} {contact_data.get('nom_famille')} (SQLite)")

    entreprise_id = contact_data.get('entreprise_id') or contact_data.get('company_id')
    entreprise = crm_manager.get_entreprise_by_id(entreprise_id)
    nom_entreprise_detail = entreprise['nom'] if entreprise else "N/A"

    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**ID:** {contact_data.get('id')}")
        st.write(f"**Email:** {contact_data.get('email', 'N/A')}")
        st.write(f"**Entreprise:** {nom_entreprise_detail}")
    with c2:
        st.write(f"**Téléphone:** {contact_data.get('telephone', 'N/A')}")
        st.write(f"**Rôle:** {contact_data.get('role') or contact_data.get('role_poste', 'N/A')}")

    st.markdown("**Notes:**")
    st.text_area("contact_detail_notes_display", value=contact_data.get('notes', 'Aucune note.'), height=100, disabled=True, label_visibility="collapsed")

    st.markdown("---")
    st.markdown("#### 💬 Interactions Récentes (SQLite)")
    interactions_contact = crm_manager.get_interactions_for_contact(contact_data['id'])
    if interactions_contact:
        for inter in interactions_contact[:5]:
            type_display = inter.get('type') or inter.get('type_interaction', 'N/A')
            st.markdown(f"<div class='info-card' style='border-left: 3px solid var(--primary-color-light);'><b>{type_display}</b> - {datetime.fromisoformat(inter.get('date_interaction')).strftime('%d/%m/%Y %H:%M')}<br>{inter.get('resume', '')}</div>", unsafe_allow_html=True)
    else:
        st.caption("Aucune interaction enregistrée pour ce contact.")

    st.markdown("---")
    st.markdown("#### 🚀 Projets Liés (SQLite)")
    if hasattr(projet_manager, 'projets'):
        projets_lies_contact = [p for p in projet_manager.projets 
                              if p.get('client_contact_id') == contact_data.get('id') or 
                              (p.get('client_entreprise_id') == entreprise_id and entreprise_id is not None) or
                              (p.get('client_company_id') == entreprise_id and entreprise_id is not None)]
        if projets_lies_contact:
            for proj in projets_lies_contact:
                link_text = f"Projet #{proj.get('id')}: {proj.get('nom_projet')} ({proj.get('statut')})"
                if st.button(link_text, key=f"goto_project_from_crm_{proj.get('id')}"):
                    st.session_state.page_to_show_val = "liste"
                    st.session_state.view_project_id_from_crm = proj.get('id')
                    st.rerun()
                st.markdown("---", unsafe_allow_html=True)
        else:
            st.caption("Aucun projet directement lié à ce contact.")
    else:
        st.caption("Gestionnaire de projets non disponible.")

    if st.button("Retour à la liste des contacts", key="back_to_contacts_list_from_details_crm"):
        st.session_state.crm_action = None
        st.rerun()

def render_crm_entreprises_tab(crm_manager: GestionnaireCRM, projet_manager):
    st.subheader("🏢 Liste des Entreprises (SQLite)")

    col_create_entreprise, col_search_entreprise = st.columns([1, 2])
    with col_create_entreprise:
        if st.button("➕ Nouvelle Entreprise", key="crm_create_entreprise_btn", use_container_width=True):
            st.session_state.crm_action = "create_entreprise"
            st.session_state.crm_selected_id = None

    with col_search_entreprise:
        search_entreprise_term = st.text_input("Rechercher une entreprise...", key="crm_entreprise_search")

    filtered_entreprises = crm_manager.entreprises
    if search_entreprise_term:
        term_e = search_entreprise_term.lower()
        filtered_entreprises = [
            e for e in filtered_entreprises if
            term_e in e.get('nom', '').lower() or
            term_e in e.get('secteur', '').lower() or
            term_e in e.get('ville', '').lower() or
            term_e in e.get('pays', '').lower()
        ]

    if filtered_entreprises:
        entreprises_data_display = []
        for entreprise_item in filtered_entreprises:
            contact_principal = crm_manager.get_contact_by_id(entreprise_item.get('contact_principal_id'))
            nom_contact_principal = f"{contact_principal.get('prenom','')} {contact_principal.get('nom_famille','')}" if contact_principal else "N/A"
            
            # Recherche des projets liés - adaptation pour SQLite
            projets_lies_entreprise = []
            if hasattr(projet_manager, 'projets'):
                projets_lies_entreprise = [p['nom_projet'] for p in projet_manager.projets 
                                         if p.get('client_entreprise_id') == entreprise_item.get('id') or
                                         p.get('client_company_id') == entreprise_item.get('id')]

            # Formater l'adresse pour l'affichage dans le tableau
            ville_pays = []
            if entreprise_item.get('ville'):
                ville_pays.append(entreprise_item['ville'])
            if entreprise_item.get('pays'):
                ville_pays.append(entreprise_item['pays'])
            ville_pays_str = ', '.join(ville_pays) if ville_pays else "N/A"

            entreprises_data_display.append({
                "ID": entreprise_item.get('id'),
                "Nom": entreprise_item.get('nom'),
                "Secteur": entreprise_item.get('secteur'),
                "Ville/Pays": ville_pays_str,
                "Site Web": entreprise_item.get('site_web'),
                "Contact Principal": nom_contact_principal,
                "Projets Liés": ", ".join(projets_lies_entreprise) if projets_lies_entreprise else "-"
            })
        st.dataframe(pd.DataFrame(entreprises_data_display), use_container_width=True)

        st.markdown("---")
        st.markdown("### 🔧 Actions sur une entreprise")
        selected_entreprise_id_action = st.selectbox(
            "Entreprise:",
            options=[e['id'] for e in filtered_entreprises],
            format_func=lambda eid: f"#{eid} - {next((e.get('nom', '') for e in filtered_entreprises if e.get('id') == eid), '')}",
            key="crm_entreprise_action_select"
        )
        if selected_entreprise_id_action:
            col_act_e1, col_act_e2, col_act_e3 = st.columns(3)
            with col_act_e1:
                if st.button("👁️ Voir Détails Entreprise", key=f"crm_view_entreprise_{selected_entreprise_id_action}", use_container_width=True):
                    st.session_state.crm_action = "view_entreprise_details"
                    st.session_state.crm_selected_id = selected_entreprise_id_action
            with col_act_e2:
                if st.button("✏️ Modifier Entreprise", key=f"crm_edit_entreprise_{selected_entreprise_id_action}", use_container_width=True):
                    st.session_state.crm_action = "edit_entreprise"
                    st.session_state.crm_selected_id = selected_entreprise_id_action
            with col_act_e3:
                if st.button("🗑️ Supprimer Entreprise", key=f"crm_delete_entreprise_{selected_entreprise_id_action}", use_container_width=True):
                    st.session_state.crm_confirm_delete_entreprise_id = selected_entreprise_id_action
    else:
        st.info("Aucune entreprise correspondante." if search_entreprise_term else "Aucune entreprise enregistrée.")

    # Gérer la confirmation de suppression pour entreprise
    if 'crm_confirm_delete_entreprise_id' in st.session_state and st.session_state.crm_confirm_delete_entreprise_id:
        entreprise_to_delete = crm_manager.get_entreprise_by_id(st.session_state.crm_confirm_delete_entreprise_id)
        if entreprise_to_delete:
            st.warning(f"Êtes-vous sûr de vouloir supprimer l'entreprise {entreprise_to_delete.get('nom')} ? Cette action est irréversible.")
            col_del_confirm, col_del_cancel = st.columns(2)
            if col_del_confirm.button("Oui, supprimer cette entreprise", type="primary", key="crm_confirm_delete_entreprise_btn_final"):
                if crm_manager.supprimer_entreprise(st.session_state.crm_confirm_delete_entreprise_id):
                    st.success("Entreprise supprimée de SQLite.")
                else:
                    st.error("Erreur lors de la suppression SQLite.")
                del st.session_state.crm_confirm_delete_entreprise_id
                st.rerun()
            if col_del_cancel.button("Annuler la suppression", key="crm_cancel_delete_entreprise_btn_final"):
                del st.session_state.crm_confirm_delete_entreprise_id
                st.rerun()

def render_crm_entreprise_form(crm_manager: GestionnaireCRM, entreprise_data=None):
    form_title_e = "➕ Ajouter une Nouvelle Entreprise (SQLite)" if entreprise_data is None else f"✏️ Modifier l'Entreprise #{entreprise_data.get('id')} (SQLite)"
    with st.expander(form_title_e, expanded=True):
        with st.form(key="crm_entreprise_form_in_expander", clear_on_submit=False):
            nom_e = st.text_input("Nom de l'entreprise *", value=entreprise_data.get('nom', '') if entreprise_data else "")
            secteur_e = st.text_input("Secteur d'activité", value=entreprise_data.get('secteur', '') if entreprise_data else "")
            
            # Champs d'adresse structurés
            st.markdown("**Adresse**")
            col_addr1, col_addr2 = st.columns(2)
            with col_addr1:
                adresse_e = st.text_input("Adresse (rue, numéro)", value=entreprise_data.get('adresse', '') if entreprise_data else "")
                province_e = st.text_input("Province/État", value=entreprise_data.get('province', '') if entreprise_data else "")
                pays_e = st.text_input("Pays", value=entreprise_data.get('pays', '') if entreprise_data else "")
            with col_addr2:
                ville_e = st.text_input("Ville", value=entreprise_data.get('ville', '') if entreprise_data else "")
                code_postal_e = st.text_input("Code postal", value=entreprise_data.get('code_postal', '') if entreprise_data else "")
            
            site_web_e = st.text_input("Site Web", value=entreprise_data.get('site_web', '') if entreprise_data else "")

            contact_options_e = [("", "Aucun")] + [(c['id'], f"{c.get('prenom','')} {c.get('nom_famille','')}") for c in crm_manager.contacts]
            current_contact_id_e = entreprise_data.get('contact_principal_id') if entreprise_data else ""
            contact_principal_id_e = st.selectbox(
                "Contact Principal",
                options=[opt_id for opt_id, _ in contact_options_e],
                format_func=lambda opt_id: next((name for id_c, name in contact_options_e if id_c == opt_id), "Aucun"),
                index=next((i for i, (opt_id, _) in enumerate(contact_options_e) if opt_id == current_contact_id_e),0),
                key="entreprise_form_contact_select"
            )
            notes_e = st.text_area("Notes sur l'entreprise", value=entreprise_data.get('notes', '') if entreprise_data else "", key="entreprise_form_notes")
            st.caption("* Champs obligatoires")

            col_submit_e, col_cancel_e_form = st.columns(2)
            with col_submit_e:
                submitted_e = st.form_submit_button("💾 Enregistrer Entreprise SQLite", use_container_width=True)
            with col_cancel_e_form:
                if st.form_submit_button("❌ Annuler", use_container_width=True):
                    st.session_state.crm_action = None
                    st.session_state.crm_selected_id = None
                    st.rerun()

            if submitted_e:
                if not nom_e:
                    st.error("Le nom de l'entreprise est obligatoire.")
                else:
                    new_entreprise_data = {
                        'nom': nom_e, 
                        'secteur': secteur_e, 
                        'adresse': adresse_e,
                        'ville': ville_e,
                        'province': province_e,
                        'code_postal': code_postal_e,
                        'pays': pays_e,
                        'site_web': site_web_e,
                        'contact_principal_id': contact_principal_id_e if contact_principal_id_e else None,
                        'notes': notes_e
                    }
                    
                    # Affichage de débogage
                    with st.expander("🔍 Debug - Données à enregistrer", expanded=False):
                        st.json(new_entreprise_data)
                    
                    if entreprise_data:
                        # Mode modification
                        success = crm_manager.modifier_entreprise(entreprise_data['id'], new_entreprise_data)
                        if success:
                            st.success(f"Entreprise #{entreprise_data['id']} mise à jour en SQLite !")
                            st.session_state.crm_action = None
                            st.session_state.crm_selected_id = None
                            st.rerun()
                        else:
                            st.error("Erreur lors de la modification SQLite.")
                    else:
                        # Mode création
                        st.info("Tentative de création de l'entreprise...")
                        new_id_e = crm_manager.ajouter_entreprise(new_entreprise_data)
                        if new_id_e:
                            st.success(f"Nouvelle entreprise #{new_id_e} ajoutée en SQLite !")
                            st.balloons()
                            st.session_state.crm_action = None
                            st.session_state.crm_selected_id = None
                            st.rerun()
                        else:
                            st.error("Erreur lors de la création SQLite.")
                            st.error("Vérifiez les logs ci-dessus pour plus de détails.")

def render_crm_entreprise_details(crm_manager: GestionnaireCRM, projet_manager, entreprise_data):
    if not entreprise_data:
        st.error("Entreprise non trouvée.")
        return

    st.subheader(f"🏢 Détails de l'Entreprise: {entreprise_data.get('nom')} (SQLite)")

    contact_principal = crm_manager.get_contact_by_id(entreprise_data.get('contact_principal_id'))
    nom_contact_principal = f"{contact_principal.get('prenom','')} {contact_principal.get('nom_famille','')}" if contact_principal else "N/A"

    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**ID:** {entreprise_data.get('id')}")
        st.write(f"**Secteur:** {entreprise_data.get('secteur', 'N/A')}")
        st.write(f"**Contact Principal:** {nom_contact_principal}")
        st.write(f"**Site Web:** {entreprise_data.get('site_web', 'N/A')}")
    with c2:
        st.markdown("**Adresse complète:**")
        adresse_complete = crm_manager.format_adresse_complete(entreprise_data)
        st.text_area("adresse_display", value=adresse_complete, height=120, disabled=True, label_visibility="collapsed")

    st.markdown("**Notes:**")
    st.text_area("entreprise_detail_notes_display", value=entreprise_data.get('notes', 'Aucune note.'), height=100, disabled=True, label_visibility="collapsed")

    st.markdown("---")
    st.markdown("#### 👥 Contacts de cette entreprise (SQLite)")
    contacts_entreprise = crm_manager.get_contacts_by_entreprise_id(entreprise_data['id'])
    if contacts_entreprise:
        for contact in contacts_entreprise:
            role_display = contact.get('role') or contact.get('role_poste', 'N/A')
            st.markdown(f"<div class='info-card' style='border-left: 3px solid var(--primary-color-light);'><b>{contact.get('prenom')} {contact.get('nom_famille')}</b> - {role_display}<br>{contact.get('email', '')}</div>", unsafe_allow_html=True)
    else:
        st.caption("Aucun contact enregistré pour cette entreprise.")

    st.markdown("---")
    st.markdown("#### 🚀 Projets Liés (SQLite)")
    if hasattr(projet_manager, 'projets'):
        projets_lies_entreprise = [p for p in projet_manager.projets 
                                 if p.get('client_entreprise_id') == entreprise_data.get('id') or
                                 p.get('client_company_id') == entreprise_data.get('id')]
        if projets_lies_entreprise:
            for proj in projets_lies_entreprise:
                link_text = f"Projet #{proj.get('id')}: {proj.get('nom_projet')} ({proj.get('statut')})"
                if st.button(link_text, key=f"goto_project_from_crm_entreprise_{proj.get('id')}"):
                    st.session_state.page_to_show_val = "liste"
                    st.session_state.view_project_id_from_crm = proj.get('id')
                    st.rerun()
                st.markdown("---", unsafe_allow_html=True)
        else:
            st.caption("Aucun projet directement lié à cette entreprise.")
    else:
        st.caption("Gestionnaire de projets non disponible.")

    if st.button("Retour à la liste des entreprises", key="back_to_entreprises_list_from_details_crm"):
        st.session_state.crm_action = None
        st.rerun()

def render_crm_interactions_tab(crm_manager: GestionnaireCRM):
    st.subheader("💬 Journal des Interactions (SQLite)")
    
    col_create_interaction, col_search_interaction = st.columns([1, 2])
    with col_create_interaction:
        if st.button("➕ Nouvelle Interaction", key="crm_create_interaction_btn", use_container_width=True):
            st.session_state.crm_action = "create_interaction"
            st.session_state.crm_selected_id = None

    with col_search_interaction:
        search_interaction_term = st.text_input("Rechercher une interaction...", key="crm_interaction_search")

    filtered_interactions = crm_manager.interactions
    if search_interaction_term:
        term_i = search_interaction_term.lower()
        filtered_interactions = [
            i for i in filtered_interactions if
            term_i in i.get('resume', '').lower() or
            term_i in (i.get('type') or i.get('type_interaction', '')).lower() or
            term_i in i.get('details', '').lower()
        ]

    if filtered_interactions:
        interactions_data_display = []
        for interaction in filtered_interactions:
            contact = crm_manager.get_contact_by_id(interaction.get('contact_id'))
            entreprise_id = interaction.get('entreprise_id') or interaction.get('company_id')
            entreprise = crm_manager.get_entreprise_by_id(entreprise_id)
            nom_contact = f"{contact.get('prenom','')} {contact.get('nom_famille','')}" if contact else "N/A"
            nom_entreprise = entreprise.get('nom', 'N/A') if entreprise else "N/A"
            
            try:
                date_formatted = datetime.fromisoformat(interaction.get('date_interaction', '')).strftime('%d/%m/%Y %H:%M')
            except:
                date_formatted = interaction.get('date_interaction', 'N/A')

            type_display = interaction.get('type') or interaction.get('type_interaction', 'N/A')

            interactions_data_display.append({
                "ID": interaction.get('id'),
                "Type": type_display,
                "Date": date_formatted,
                "Contact": nom_contact,
                "Entreprise": nom_entreprise,
                "Résumé": interaction.get('resume', 'N/A'),
                "Résultat": interaction.get('resultat', 'N/A')
            })
        
        st.dataframe(pd.DataFrame(interactions_data_display), use_container_width=True)

        st.markdown("---")
        st.markdown("### 🔧 Actions sur une interaction")
        selected_interaction_id_action = st.selectbox(
            "Interaction:",
            options=[i['id'] for i in filtered_interactions],
            format_func=lambda iid: f"#{iid} - {next(((i.get('type') or i.get('type_interaction', '')) + ': ' + i.get('resume', '') for i in filtered_interactions if i.get('id') == iid), '')}",
            key="crm_interaction_action_select"
        )

        if selected_interaction_id_action:
            col_act_i1, col_act_i2, col_act_i3 = st.columns(3)
            with col_act_i1:
                if st.button("👁️ Voir Détails", key=f"crm_view_interaction_{selected_interaction_id_action}", use_container_width=True):
                    st.session_state.crm_action = "view_interaction_details"
                    st.session_state.crm_selected_id = selected_interaction_id_action
            with col_act_i2:
                if st.button("✏️ Modifier", key=f"crm_edit_interaction_{selected_interaction_id_action}", use_container_width=True):
                    st.session_state.crm_action = "edit_interaction"
                    st.session_state.crm_selected_id = selected_interaction_id_action
            with col_act_i3:
                if st.button("🗑️ Supprimer", key=f"crm_delete_interaction_{selected_interaction_id_action}", use_container_width=True):
                    st.session_state.crm_confirm_delete_interaction_id = selected_interaction_id_action
    else:
        st.info("Aucune interaction correspondante." if search_interaction_term else "Aucune interaction enregistrée.")

    # Gérer la confirmation de suppression pour interaction
    if 'crm_confirm_delete_interaction_id' in st.session_state and st.session_state.crm_confirm_delete_interaction_id:
        interaction_to_delete = crm_manager.get_interaction_by_id(st.session_state.crm_confirm_delete_interaction_id)
        if interaction_to_delete:
            type_display = interaction_to_delete.get('type') or interaction_to_delete.get('type_interaction', 'N/A')
            st.warning(f"Êtes-vous sûr de vouloir supprimer l'interaction #{interaction_to_delete.get('id')} ({type_display}: {interaction_to_delete.get('resume')}) ? Cette action est irréversible.")
            col_del_confirm, col_del_cancel = st.columns(2)
            if col_del_confirm.button("Oui, supprimer cette interaction", type="primary", key="crm_confirm_delete_interaction_btn_final"):
                if crm_manager.supprimer_interaction(st.session_state.crm_confirm_delete_interaction_id):
                    st.success("Interaction supprimée de SQLite.")
                else:
                    st.error("Erreur lors de la suppression SQLite.")
                del st.session_state.crm_confirm_delete_interaction_id
                st.rerun()
            if col_del_cancel.button("Annuler la suppression", key="crm_cancel_delete_interaction_btn_final"):
                del st.session_state.crm_confirm_delete_interaction_id
                st.rerun()

def render_crm_interaction_form(crm_manager: GestionnaireCRM, interaction_data=None):
    form_title_i = "➕ Ajouter une Nouvelle Interaction (SQLite)" if interaction_data is None else f"✏️ Modifier l'Interaction #{interaction_data.get('id')} (SQLite)"
    with st.expander(form_title_i, expanded=True):
        with st.form(key="crm_interaction_form_in_expander", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            with col1:
                type_value = interaction_data.get('type') or interaction_data.get('type_interaction') if interaction_data else None
                type_interaction = st.selectbox(
                    "Type d'interaction *",
                    TYPES_INTERACTION,
                    index=TYPES_INTERACTION.index(type_value) if type_value and type_value in TYPES_INTERACTION else 0
                )
                
                # Sélection du contact
                contact_options = [("", "Aucun")] + [(c['id'], f"{c.get('prenom','')} {c.get('nom_famille','')}") for c in crm_manager.contacts]
                current_contact_id = interaction_data.get('contact_id') if interaction_data else ""
                contact_id = st.selectbox(
                    "Contact",
                    options=[opt_id for opt_id, _ in contact_options],
                    format_func=lambda opt_id: next((name for id_c, name in contact_options if id_c == opt_id), "Aucun"),
                    index=next((i for i, (opt_id, _) in enumerate(contact_options) if opt_id == current_contact_id), 0),
                    key="interaction_form_contact_select"
                )
                
                # Sélection de l'entreprise
                entreprise_options = [("", "Aucune")] + [(e['id'], e['nom']) for e in crm_manager.entreprises]
                current_entreprise_id = interaction_data.get('entreprise_id') or interaction_data.get('company_id') if interaction_data else ""
                entreprise_id = st.selectbox(
                    "Entreprise",
                    options=[opt_id for opt_id, _ in entreprise_options],
                    format_func=lambda opt_id: next((name for id_e, name in entreprise_options if id_e == opt_id), "Aucune"),
                    index=next((i for i, (opt_id, _) in enumerate(entreprise_options) if opt_id == current_entreprise_id), 0),
                    key="interaction_form_entreprise_select"
                )

            with col2:
                # Date de l'interaction
                try:
                    default_date = datetime.fromisoformat(interaction_data.get('date_interaction')).date() if interaction_data and interaction_data.get('date_interaction') else datetime.now().date()
                except:
                    default_date = datetime.now().date()
                    
                date_interaction = st.date_input("Date de l'interaction *", value=default_date)
                
                try:
                    default_time = datetime.fromisoformat(interaction_data.get('date_interaction')).time() if interaction_data and interaction_data.get('date_interaction') else datetime.now().time()
                except:
                    default_time = datetime.now().time()
                    
                time_interaction = st.time_input("Heure de l'interaction", value=default_time)
                
                resultat = st.selectbox(
                    "Résultat",
                    ["Positif", "Neutre", "Négatif", "En cours", "À suivre"],
                    index=["Positif", "Neutre", "Négatif", "En cours", "À suivre"].index(interaction_data.get('resultat')) if interaction_data and interaction_data.get('resultat') in ["Positif", "Neutre", "Négatif", "En cours", "À suivre"] else 0
                )

            resume = st.text_input("Résumé de l'interaction *", value=interaction_data.get('resume', '') if interaction_data else "", max_chars=100)
            details = st.text_area("Détails", value=interaction_data.get('details', '') if interaction_data else "", height=100)
            
            # Date de suivi prévue
            try:
                default_suivi = datetime.fromisoformat(interaction_data.get('suivi_prevu')).date() if interaction_data and interaction_data.get('suivi_prevu') else date_interaction + timedelta(days=7)
            except:
                default_suivi = date_interaction + timedelta(days=7)
                
            suivi_prevu = st.date_input("Suivi prévu", value=default_suivi)
            
            st.caption("* Champs obligatoires")

            col_submit_i, col_cancel_i_form = st.columns(2)
            with col_submit_i:
                submitted_i = st.form_submit_button("💾 Enregistrer Interaction SQLite", use_container_width=True)
            with col_cancel_i_form:
                if st.form_submit_button("❌ Annuler", use_container_width=True):
                    st.session_state.crm_action = None
                    st.session_state.crm_selected_id = None
                    st.rerun()

            if submitted_i:
                if not type_interaction or not resume:
                    st.error("Le type et le résumé sont obligatoires.")
                elif not contact_id and not entreprise_id:
                    st.error("Vous devez sélectionner au moins un contact ou une entreprise.")
                else:
                    # Combiner date et heure
                    datetime_interaction = datetime.combine(date_interaction, time_interaction)
                    
                    new_interaction_data = {
                        'type': type_interaction,
                        'type_interaction': type_interaction,
                        'contact_id': contact_id if contact_id else None,
                        'entreprise_id': entreprise_id if entreprise_id else None,
                        'company_id': entreprise_id if entreprise_id else None,
                        'date_interaction': datetime_interaction.isoformat(),
                        'resume': resume,
                        'details': details,
                        'resultat': resultat,
                        'suivi_prevu': suivi_prevu.isoformat()
                    }
                    
                    if interaction_data:
                        if crm_manager.modifier_interaction(interaction_data['id'], new_interaction_data):
                            st.success(f"Interaction #{interaction_data['id']} mise à jour en SQLite !")
                        else:
                            st.error("Erreur lors de la modification SQLite.")
                    else:
                        new_id_i = crm_manager.ajouter_interaction(new_interaction_data)
                        if new_id_i:
                            st.success(f"Nouvelle interaction #{new_id_i} ajoutée en SQLite !")
                        else:
                            st.error("Erreur lors de la création SQLite.")
                    
                    st.session_state.crm_action = None
                    st.session_state.crm_selected_id = None
                    st.rerun()

def render_crm_interaction_details(crm_manager: GestionnaireCRM, projet_manager, interaction_data):
    if not interaction_data:
        st.error("Interaction non trouvée.")
        return

    st.subheader(f"💬 Détails de l'Interaction #{interaction_data.get('id')} (SQLite)")

    contact = crm_manager.get_contact_by_id(interaction_data.get('contact_id'))
    entreprise_id = interaction_data.get('entreprise_id') or interaction_data.get('company_id')
    entreprise = crm_manager.get_entreprise_by_id(entreprise_id)
    nom_contact = f"{contact.get('prenom','')} {contact.get('nom_famille','')}" if contact else "N/A"
    nom_entreprise = entreprise.get('nom', 'N/A') if entreprise else "N/A"

    try:
        date_formatted = datetime.fromisoformat(interaction_data.get('date_interaction', '')).strftime('%d/%m/%Y à %H:%M')
    except:
        date_formatted = interaction_data.get('date_interaction', 'N/A')

    try:
        suivi_formatted = datetime.fromisoformat(interaction_data.get('suivi_prevu', '')).strftime('%d/%m/%Y')
    except:
        suivi_formatted = interaction_data.get('suivi_prevu', 'N/A')

    type_display = interaction_data.get('type') or interaction_data.get('type_interaction', 'N/A')

    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**ID:** {interaction_data.get('id')}")
        st.write(f"**Type:** {type_display}")
        st.write(f"**Date:** {date_formatted}")
        st.write(f"**Contact:** {nom_contact}")
    with c2:
        st.write(f"**Entreprise:** {nom_entreprise}")
        st.write(f"**Résultat:** {interaction_data.get('resultat', 'N/A')}")
        st.write(f"**Suivi prévu:** {suivi_formatted}")

    st.markdown("**Résumé:**")
    st.write(interaction_data.get('resume', 'Aucun résumé.'))

    st.markdown("**Détails:**")
    st.text_area("interaction_detail_details_display", value=interaction_data.get('details', 'Aucun détail.'), height=100, disabled=True, label_visibility="collapsed")

    if st.button("Retour à la liste des interactions", key="back_to_interactions_list_from_details_crm"):
        st.session_state.crm_action = None
        st.rerun()

# =========================================================================
# FONCTIONS DE GESTION DES ACTIONS CRM (SANS DEVIS)
# =========================================================================

def handle_crm_actions(crm_manager: GestionnaireCRM, projet_manager=None):
    """Gestionnaire centralisé des actions CRM (sans devis)."""
    action = st.session_state.get('crm_action')
    selected_id = st.session_state.get('crm_selected_id')
    
    # Actions pour les contacts
    if action == "create_contact": 
        render_crm_contact_form(crm_manager)
    elif action == "edit_contact" and selected_id: 
        render_crm_contact_form(crm_manager, crm_manager.get_contact_by_id(selected_id))
    elif action == "view_contact_details" and selected_id: 
        render_crm_contact_details(crm_manager, projet_manager, crm_manager.get_contact_by_id(selected_id))
    # Actions pour les entreprises
    elif action == "create_entreprise": 
        render_crm_entreprise_form(crm_manager)
    elif action == "edit_entreprise" and selected_id: 
        render_crm_entreprise_form(crm_manager, crm_manager.get_entreprise_by_id(selected_id))
    elif action == "view_entreprise_details" and selected_id: 
        render_crm_entreprise_details(crm_manager, projet_manager, crm_manager.get_entreprise_by_id(selected_id))
    # Actions pour les interactions
    elif action == "create_interaction": 
        render_crm_interaction_form(crm_manager)
    elif action == "edit_interaction" and selected_id: 
        render_crm_interaction_form(crm_manager, crm_manager.get_interaction_by_id(selected_id))
    elif action == "view_interaction_details" and selected_id: 
        render_crm_interaction_details(crm_manager, projet_manager, crm_manager.get_interaction_by_id(selected_id))
    # Actions pour les produits
    elif action == "create_product": 
        render_crm_product_form(crm_manager)
    elif action == "edit_product" and selected_id: 
        render_crm_product_form(crm_manager, crm_manager.get_produit_by_id(selected_id))
    elif action == "view_product_details" and selected_id: 
        render_crm_product_details(crm_manager, crm_manager.get_produit_by_id(selected_id))
    elif action == "adjust_stock" and selected_id: 
        render_crm_stock_adjustment(crm_manager, crm_manager.get_produit_by_id(selected_id))

def render_crm_main_interface(crm_manager: GestionnaireCRM, projet_manager=None):
    """Interface principale CRM (sans devis)."""
    st.title("📋 Gestion des Ventes")
    
    if crm_manager.use_sqlite:
        st.success("✅ Mode SQLite actif - Données centralisées.")
    else:
        st.warning("⚠️ Mode JSON (rétrocompatibilité).")
    
    # Le menu principal n'a plus que 4 onglets
    tab1, tab2, tab3, tab4 = st.tabs(["👤 Contacts", "🏢 Entreprises", "💬 Interactions", "🔧 Produits"])
    
    with tab1:
        render_crm_contacts_tab(crm_manager, projet_manager)
    with tab2:
        render_crm_entreprises_tab(crm_manager, projet_manager)
    with tab3:
        render_crm_interactions_tab(crm_manager)
    with tab4:
        render_crm_produits_tab(crm_manager)
    
    # Le gestionnaire d'actions est conservé pour les autres entités CRM
    handle_crm_actions(crm_manager, projet_manager)

# =========================================================================
# POINTS D'ENTRÉE PRINCIPAUX
# =========================================================================

def main_crm_interface(db_instance=None, project_manager_instance=None):
    """Point d'entrée principal pour l'interface CRM complète."""
    
    # Le project_manager n'est plus passé au constructeur CRM, mais reste nécessaire pour l'affichage des projets liés.
    crm_manager = GestionnaireCRM(db=db_instance)
    
    # Afficher l'interface principale
    render_crm_main_interface(crm_manager, project_manager_instance)
    
    return crm_manager

def demo_crm_with_products():
    """Démonstration du système CRM avec produits (sans devis)"""
    
    st.title("🎯 Démonstration CRM + Produits")
    
    # Pour la démo, utilisation du mode JSON
    crm_manager = GestionnaireCRM()
    
    st.info("💡 Cette démonstration utilise le mode JSON. Pour une version complète avec SQLite, il faut un environnement avec ERPDatabase.")
    
    # Afficher les statistiques
    stats = get_crm_statistics_summary(crm_manager)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Contacts", stats['total_contacts'])
    with col2:
        st.metric("Entreprises", stats['total_entreprises'])  
    with col3:
        st.metric("Interactions", stats['total_interactions'])
    with col4:
        st.metric("Produits", stats['total_produits'])
    
    # Interface simplifiée (sans project_manager)
    render_crm_main_interface(crm_manager, None)

# =========================================================================
# FONCTIONS UTILITAIRES ET HELPERS
# =========================================================================

def get_crm_statistics_summary(crm_manager: GestionnaireCRM):
    """Résumé des statistiques CRM pour dashboard"""
    try:
        stats = {
            'total_contacts': len(crm_manager.contacts),
            'total_entreprises': len(crm_manager.entreprises),
            'total_interactions': len(crm_manager.interactions),
            'total_produits': len(crm_manager.produits),
            'valeur_stock': 0.0,
            'produits_stock_bas': 0
        }
        
        # Statistiques produits
        stats_produits = crm_manager.get_statistics_produits()
        stats['valeur_stock'] = stats_produits.get('valeur_stock_total', 0.0)
        stats['produits_stock_bas'] = stats_produits.get('produits_stock_bas', 0)
        
        return stats
    except Exception as e:
        st.error(f"Erreur calcul statistiques CRM: {e}")
        return {}

def export_crm_data_to_excel(crm_manager: GestionnaireCRM):
    """Exporte les données CRM vers Excel (placeholder)"""
    try:
        # Créer un DataFrame avec toutes les données
        contacts_df = pd.DataFrame(crm_manager.contacts)
        entreprises_df = pd.DataFrame(crm_manager.entreprises)
        interactions_df = pd.DataFrame(crm_manager.interactions)
        produits_df = pd.DataFrame(crm_manager.produits)
        
        return {
            'contacts': contacts_df,
            'entreprises': entreprises_df, 
            'interactions': interactions_df,
            'produits': produits_df
        }
    except Exception as e:
        st.error(f"Erreur export Excel: {e}")
        return None

def format_currency(amount, currency="CAD"):
    """Formate un montant en devise"""
    try:
        if currency == "CAD":
            return f"{amount:,.2f} $ CAD"
        else:
            return f"{amount:,.2f} {currency}"
    except:
        return "0,00 $"

# =========================================================================
# TESTS ET VALIDATION
# =========================================================================

def test_crm_functionality():
    """Tests unitaires basiques pour le CRM"""
    
    # Test mode JSON
    crm_json = GestionnaireCRM()
    
    # Test ajout contact
    contact_data = {
        'prenom': 'Test',
        'nom_famille': 'User',
        'email': 'test@example.com',
        'telephone': '123456789',
        'entreprise_id': 101,
        'role': 'Testeur'
    }
    
    contact_id = crm_json.ajouter_contact(contact_data)
    assert contact_id is not None, "Échec ajout contact"
    
    # Test récupération contact
    contact = crm_json.get_contact_by_id(contact_id)
    assert contact is not None, "Échec récupération contact"
    assert contact['prenom'] == 'Test', "Données contact incorrectes"
    
    # Test modification contact
    success = crm_json.modifier_contact(contact_id, {'telephone': '987654321'})
    assert success, "Échec modification contact"
    
    # Test suppression contact
    success = crm_json.supprimer_contact(contact_id)
    assert success, "Échec suppression contact"
    
    # Test ajout produit
    produit_data = {
        'code_produit': 'TEST-001',
        'nom': 'Produit Test',
        'description': 'Produit de test',
        'categorie': 'Acier',
        'materiau': 'Acier',
        'nuance': 'S235',
        'unite_vente': 'kg',
        'prix_unitaire': 10.50
    }
    
    produit_id = crm_json.ajouter_produit(produit_data)
    assert produit_id is not None, "Échec ajout produit"
    
    print("✅ Tous les tests CRM (mode JSON) passent!")

if __name__ == "__main__":
    st.set_page_config(layout="wide")
    
    # Pour une exécution standalone, on peut simuler la DB
    # Ceci est juste pour la démonstration du fichier seul.
    try:
        from erp_database import ERPDatabase
        from projects import GestionnaireProjetSQL

        # Simuler une base de données en mémoire pour le test
        # En production, utiliser le chemin du fichier DB: 'erp_prod.db'
        db = ERPDatabase(db_name=":memory:") 
        db.create_tables()

        # Initialiser les managers
        project_manager = GestionnaireProjetSQL(db=db)
        crm_manager = GestionnaireCRM(db=db)

        # Afficher l'interface complète
        render_crm_main_interface(crm_manager, project_manager)
        
    except ImportError:
        # Si les autres modules ne sont pas trouvés, lancer la démo en mode JSON
        st.warning("Modules 'erp_database' ou 'projects' non trouvés. Lancement en mode démo JSON.")
        demo_crm_with_products()
    except Exception as e:
        st.error(f"Une erreur est survenue lors de l'initialisation: {e}")
        st.info("Lancement en mode démo JSON de secours.")
        demo_crm_with_products()