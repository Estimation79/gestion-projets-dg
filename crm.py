import json
import os
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from typing import Dict, List, Optional, Any

# --- Constantes ---
TYPES_INTERACTION = ["Email", "Appel", "Réunion", "Note", "Autre"]
STATUTS_OPPORTUNITE = ["Prospection", "Qualification", "Proposition", "Négociation", "Gagné", "Perdu"]
STATUTS_DEVIS = ["BROUILLON", "VALIDÉ", "ENVOYÉ", "APPROUVÉ", "TERMINÉ", "ANNULÉ"]

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
    NOUVELLE ARCHITECTURE : Gestionnaire CRM utilisant SQLite au lieu de JSON
    Compatible avec ERPDatabase pour une architecture unifiée
    + SYSTÈME DEVIS INTÉGRÉ utilisant l'infrastructure formulaires existante
    + SUPPRESSION DE DEVIS avec sécurité et traçabilité
    + ADRESSES STRUCTURÉES (adresse, ville, province, code_postal, pays)
    + GESTION COMPLÈTE DES PRODUITS MÉTALLURGIQUES
    + EXPORT DEVIS HTML PROFESSIONNEL
    """
    
    def __init__(self, db=None, project_manager=None):
        """
        Initialise le gestionnaire CRM avec base SQLite
        
        Args:
            db: Instance de ERPDatabase, si None utilise l'ancienne méthode JSON (rétrocompatibilité)
            project_manager: Instance de GestionnaireProjetSQL pour la création de projets.
        """
        self.db = db
        self.project_manager = project_manager # Ajout pour pouvoir créer des projets
        self.use_sqlite = db is not None
        
        if not self.use_sqlite:
            # Mode rétrocompatibilité JSON (conservé temporairement)
            self.data_file = "crm_data.json"
            self._contacts = []
            self._entreprises = []
            self._interactions = []
            self._produits = []  # Ajout pour les produits en mode JSON
            self.next_contact_id = 1
            self.next_entreprise_id = 1
            self.next_interaction_id = 1
            self.next_produit_id = 1  # Ajout pour les produits
            self.charger_donnees_crm()
        else:
            # Mode SQLite unifié + initialisation devis + produits
            self._init_demo_data_if_empty()
            self._init_devis_support()
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
    
    def _init_devis_support(self):
        """Initialise le support des devis dans le système de formulaires avec mode compatibilité"""
        if not self.use_sqlite:
            return
        
        # Par défaut, mode DEVIS natif
        self._devis_compatibility_mode = False
        self._devis_type_db = 'DEVIS'
        
        try:
            # Test si le type DEVIS peut être inséré (test de compatibilité)
            test_query = """
                INSERT INTO formulaires (type_formulaire, numero_document, statut) 
                VALUES ('DEVIS', 'TEST-DEVIS-COMPATIBILITY', 'BROUILLON')
            """
            
            try:
                test_id = self.db.execute_insert(test_query)
                # Si ça marche, supprimer le test
                if test_id:
                    self.db.execute_update("DELETE FROM formulaires WHERE id = ?", (test_id,))
                st.success("✅ Support DEVIS natif activé dans le système de formulaires")
                
            except Exception as e:
                if "CHECK constraint failed" in str(e):
                    # Activer le mode compatibilité
                    self._devis_compatibility_mode = True
                    self._devis_type_db = 'ESTIMATION'
                    st.warning("⚠️ Mode compatibilité DEVIS activé - Utilisation d'ESTIMATION avec métadonnées")
                    st.info("💡 Pour le support natif, exécutez le script de migration de la base de données")
                else:
                    st.error(f"⚠️ Support devis limité: {e}")
                
        except Exception as e:
            st.error(f"Erreur initialisation support devis: {e}")
            # En cas d'erreur, activer le mode compatibilité par sécurité
            self._devis_compatibility_mode = True
            self._devis_type_db = 'ESTIMATION'
    
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

    # =========================================================================
    # SYSTÈME DE DEVIS INTÉGRÉ - UTILISE L'INFRASTRUCTURE FORMULAIRES
    # =========================================================================
    
    def generer_numero_devis(self):
        """
        Génère un numéro de devis/estimation automatique.
        S'adapte au mode de compatibilité (DEVIS-YYYY-XXX ou EST-YYYY-XXX).
        """
        if not self.use_sqlite:
            return f"DEVIS-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            annee = datetime.now().year
            
            # Déterminer le préfixe en fonction du mode de compatibilité
            prefix = "EST" if getattr(self, '_devis_compatibility_mode', False) else "DEVIS"
            
            # La requête doit chercher le dernier numéro pour le préfixe et l'année en cours
            query = '''
                SELECT numero_document FROM formulaires 
                WHERE numero_document LIKE ?
                ORDER BY id DESC LIMIT 1
            '''
            
            pattern = f"{prefix}-{annee}-%"
            result = self.db.execute_query(query, (pattern,))
            
            sequence = 1
            if result:
                last_num = result[0]['numero_document']
                try:
                    # Extrait le dernier numéro de séquence et l'incrémente
                    sequence = int(last_num.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    # En cas de format inattendu, on repart de 1 par sécurité
                    sequence = 1
            
            return f"{prefix}-{annee}-{sequence:03d}"
            
        except Exception as e:
            st.error(f"Erreur génération numéro devis: {e}")
            # Le fallback doit aussi respecter le mode de compatibilité
            prefix_fallback = "EST" if getattr(self, '_devis_compatibility_mode', False) else "DEVIS"
            return f"{prefix_fallback}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def create_devis(self, devis_data: Dict[str, Any]) -> Optional[int]:
        """
        Crée un nouveau devis en utilisant la table formulaires existante
        Supporte le mode compatibilité ESTIMATION si DEVIS n'est pas disponible
        
        Args:
            devis_data: {
                'client_company_id': int,
                'client_contact_id': int (optionnel),
                'project_id': int (optionnel),
                'employee_id': int (responsable),
                'date_echeance': str (format YYYY-MM-DD),
                'notes': str,
                'lignes': [
                    {
                        'description': str,
                        'quantite': float,
                        'prix_unitaire': float,
                        'unite': str
                    }
                ]
            }
        """
        if not self.use_sqlite:
            st.error("Fonction devis disponible uniquement en mode SQLite")
            return None
        
        try:
            # Générer le numéro de devis automatiquement
            numero_devis = self.generer_numero_devis()
            
            # Déterminer le type à utiliser selon le mode
            type_formulaire_db = self._devis_type_db
            mode_info = " (mode compatibilité)" if self._devis_compatibility_mode else ""
            
            # Créer le devis principal
            query = '''
                INSERT INTO formulaires 
                (type_formulaire, numero_document, project_id, company_id, employee_id,
                 statut, priorite, date_echeance, notes, metadonnees_json)
                VALUES (?, ?, ?, ?, ?, 'BROUILLON', 'NORMAL', ?, ?, ?)
            '''
            
            # Métadonnées spécifiques aux devis
            metadonnees = {
                'type_reel': 'DEVIS',  # TOUJOURS identifier comme devis réel
                'type_devis': 'STANDARD',
                'tva_applicable': True,
                'taux_tva': 14.975,  # QC + GST
                'devise': 'CAD',
                'validite_jours': 30,
                'created_by_module': 'CRM_DEVIS',
                'compatibility_mode': self._devis_compatibility_mode
            }
            
            devis_id = self.db.execute_insert(query, (
                type_formulaire_db,  # Utilise le type adapté
                numero_devis,
                devis_data.get('project_id'),
                devis_data['client_company_id'],
                devis_data['employee_id'],
                devis_data['date_echeance'],
                devis_data.get('notes', ''),
                json.dumps(metadonnees)
            ))
            
            if devis_id:
                # Ajouter les lignes du devis
                if devis_data.get('lignes'):
                    for i, ligne in enumerate(devis_data['lignes'], 1):
                        self.ajouter_ligne_devis(devis_id, i, ligne)
                
                # Enregistrer la création dans l'historique
                self.enregistrer_validation_devis(
                    devis_id, 
                    devis_data['employee_id'], 
                    'CREATION',
                    f"Devis créé: {numero_devis}{mode_info}"
                )
                
                return devis_id
            
            return None
            
        except Exception as e:
            st.error(f"Erreur création devis: {e}")
            return None
    
    def modifier_devis(self, devis_id: int, devis_data: Dict[str, Any]) -> bool:
        """
        Modifie un devis existant
        
        Args:
            devis_id: ID du devis à modifier
            devis_data: Nouvelles données du devis (même structure que create_devis)
        """
        if not self.use_sqlite:
            st.error("Modification devis disponible uniquement en mode SQLite")
            return False
        
        try:
            # Vérifier que le devis existe et n'est pas dans un état non modifiable
            devis_existant = self.get_devis_complet(devis_id)
            if not devis_existant:
                st.error(f"Devis #{devis_id} non trouvé.")
                return False
            
            # Vérifier le statut - empêcher modification des devis approuvés/terminés
            statuts_non_modifiables = ['APPROUVÉ', 'TERMINÉ', 'ANNULÉ']
            if devis_existant.get('statut') in statuts_non_modifiables:
                st.error(f"Impossible de modifier un devis au statut '{devis_existant.get('statut')}'")
                return False
            
            # Mettre à jour les informations principales du formulaire
            query = '''
                UPDATE formulaires 
                SET company_id = ?, employee_id = ?, project_id = ?, 
                    date_echeance = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            '''
            
            rows_affected = self.db.execute_update(query, (
                devis_data['client_company_id'],
                devis_data['employee_id'],
                devis_data.get('project_id'),
                devis_data['date_echeance'],
                devis_data.get('notes', ''),
                devis_id
            ))
            
            if rows_affected > 0:
                # Supprimer les anciennes lignes et ajouter les nouvelles
                self.db.execute_update("DELETE FROM formulaire_lignes WHERE formulaire_id = ?", (devis_id,))
                
                # Ajouter les nouvelles lignes
                if devis_data.get('lignes'):
                    for i, ligne in enumerate(devis_data['lignes'], 1):
                        self.ajouter_ligne_devis(devis_id, i, ligne)
                
                # Enregistrer la modification dans l'historique
                self.enregistrer_validation_devis(
                    devis_id,
                    devis_data['employee_id'],
                    'MODIFICATION',
                    f"Devis modifié via interface"
                )
                
                return True
            
            return False
            
        except Exception as e:
            st.error(f"Erreur modification devis: {e}")
            return False
    
    def supprimer_devis(self, devis_id: int, employee_id: int, motif: str = "") -> bool:
        """
        Supprime un devis et toutes ses données associées
        
        Args:
            devis_id: ID du devis à supprimer
            employee_id: ID de l'employé qui effectue la suppression
            motif: Motif de suppression (optionnel)
        
        Returns:
            bool: True si suppression réussie, False sinon
        """
        if not self.use_sqlite:
            st.error("Suppression de devis disponible uniquement en mode SQLite")
            return False
        
        try:
            # Vérifier que le devis existe
            devis_existant = self.get_devis_complet(devis_id)
            if not devis_existant:
                st.error(f"Devis #{devis_id} non trouvé.")
                return False
            
            # Vérifier les permissions de suppression selon le statut
            statuts_non_supprimables = ['APPROUVÉ', 'TERMINÉ']
            if devis_existant.get('statut') in statuts_non_supprimables:
                st.error(f"Impossible de supprimer un devis au statut '{devis_existant.get('statut')}'")
                st.info("💡 Conseil: Vous pouvez annuler le devis au lieu de le supprimer.")
                return False
            
            # Enregistrer l'action avant suppression (pour audit)
            self.enregistrer_validation_devis(
                devis_id,
                employee_id,
                'SUPPRESSION',
                f"Devis supprimé. Motif: {motif if motif else 'Non spécifié'}"
            )
            
            # Supprimer en cascade dans l'ordre correct
            # 1. Supprimer les validations
            self.db.execute_update(
                "DELETE FROM formulaire_validations WHERE formulaire_id = ?", 
                (devis_id,)
            )
            
            # 2. Supprimer les lignes
            self.db.execute_update(
                "DELETE FROM formulaire_lignes WHERE formulaire_id = ?", 
                (devis_id,)
            )
            
            # 3. Supprimer le devis principal
            rows_affected = self.db.execute_update(
                "DELETE FROM formulaires WHERE id = ?", 
                (devis_id,)
            )
            
            if rows_affected > 0:
                st.success(f"✅ Devis #{devis_id} ({devis_existant.get('numero_document')}) supprimé avec succès!")
                return True
            else:
                st.error("Aucune ligne affectée lors de la suppression.")
                return False
            
        except Exception as e:
            st.error(f"Erreur lors de la suppression du devis: {e}")
            return False
    
    def ajouter_ligne_devis(self, devis_id: int, sequence: int, ligne_data: Dict[str, Any]) -> Optional[int]:
        """Ajoute une ligne à un devis"""
        if not self.use_sqlite:
            return None
        
        try:
            query = '''
                INSERT INTO formulaire_lignes
                (formulaire_id, sequence_ligne, description, code_article,
                 quantite, unite, prix_unitaire, notes_ligne)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            ligne_id = self.db.execute_insert(query, (
                devis_id,
                sequence,
                ligne_data['description'],
                ligne_data.get('code_article', ''),
                ligne_data['quantite'],
                ligne_data.get('unite', 'UN'),
                ligne_data['prix_unitaire'],
                ligne_data.get('notes', '')
            ))
            
            return ligne_id
            
        except Exception as e:
            st.error(f"Erreur ajout ligne devis: {e}")
            return None
    
    def get_devis_complet(self, devis_id: int) -> Dict[str, Any]:
        """Récupère un devis avec tous ses détails"""
        if not self.use_sqlite:
            return {}
        
        try:
            # Récupérer le devis principal
            query = '''
                SELECT f.*, 
                       c.nom as client_nom, 
                       c.adresse, c.ville, c.province, c.code_postal, c.pays,
                       co.prenom || ' ' || co.nom_famille as contact_nom, 
                       co.email as contact_email, co.telephone as contact_telephone,
                       e.prenom || ' ' || e.nom as responsable_nom,
                       p.nom_projet
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN contacts co ON c.contact_principal_id = co.id
                LEFT JOIN employees e ON f.employee_id = e.id
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE f.id = ? AND (f.type_formulaire = 'DEVIS' OR (f.type_formulaire = 'ESTIMATION' AND f.metadonnees_json LIKE '%"type_reel": "DEVIS"%'))
            '''
            
            result = self.db.execute_query(query, (devis_id,))
            if not result:
                st.error(f"Aucun devis trouvé avec l'ID {devis_id} dans la base de données.")
                return {}
            
            devis = dict(result[0])
            
            # Ajouter l'adresse complète formatée
            if devis.get('client_nom'):
                devis['client_adresse_complete'] = self.format_adresse_complete(devis)
            
            # Récupérer les lignes
            query_lignes = '''
                SELECT * FROM formulaire_lignes 
                WHERE formulaire_id = ? 
                ORDER BY sequence_ligne
            '''
            lignes = self.db.execute_query(query_lignes, (devis_id,))
            devis['lignes'] = [dict(ligne) for ligne in lignes]
            
            # Calculer les totaux
            devis['totaux'] = self.calculer_totaux_devis(devis_id)
            
            # Récupérer l'historique
            query_historique = '''
                SELECT fv.*, e.prenom || ' ' || e.nom as employee_nom
                FROM formulaire_validations fv
                LEFT JOIN employees e ON fv.employee_id = e.id
                WHERE fv.formulaire_id = ?
                ORDER BY fv.date_validation DESC
            '''
            historique = self.db.execute_query(query_historique, (devis_id,))
            devis['historique'] = [dict(h) for h in historique]
            
            # Parser les métadonnées
            try:
                devis['metadonnees'] = json.loads(devis.get('metadonnees_json', '{}'))
            except:
                devis['metadonnees'] = {}
            
            return devis
            
        except Exception as e:
            st.error(f"Erreur récupération devis complet: {e}")
            return {}
    
    def calculer_totaux_devis(self, devis_id: int) -> Dict[str, float]:
        """Calcule les totaux d'un devis (HT, TVA, TTC)"""
        if not self.use_sqlite:
            return {'total_ht': 0, 'taux_tva': 0, 'montant_tva': 0, 'total_ttc': 0}
        
        try:
            # Récupérer les lignes pour calcul
            query = '''
                SELECT quantite, prix_unitaire
                FROM formulaire_lignes 
                WHERE formulaire_id = ?
            '''
            lignes = self.db.execute_query(query, (devis_id,))
            
            total_ht = sum((ligne['quantite'] * ligne['prix_unitaire']) for ligne in lignes)
            
            # Récupérer le taux TVA des métadonnées
            devis_info = self.db.execute_query(
                "SELECT metadonnees_json FROM formulaires WHERE id = ?", 
                (devis_id,)
            )
            
            taux_tva = 14.975  # Défaut QC
            if devis_info:
                try:
                    metadonnees = json.loads(devis_info[0]['metadonnees_json'] or '{}')
                    taux_tva = metadonnees.get('taux_tva', 14.975)
                except:
                    pass
            
            tva = total_ht * (taux_tva / 100)
            total_ttc = total_ht + tva
            
            return {
                'total_ht': round(total_ht, 2),
                'taux_tva': taux_tva,
                'montant_tva': round(tva, 2),
                'total_ttc': round(total_ttc, 2)
            }
            
        except Exception as e:
            st.error(f"Erreur calcul totaux devis: {e}")
            return {'total_ht': 0, 'taux_tva': 0, 'montant_tva': 0, 'total_ttc': 0}
    
    def changer_statut_devis(self, devis_id: int, nouveau_statut: str, employee_id: int, commentaires: str = "") -> bool:
        """Change le statut d'un devis avec traçabilité"""
        if not self.use_sqlite:
            return False
        
        try:
            # Récupérer l'ancien statut
            result = self.db.execute_query(
                "SELECT statut FROM formulaires WHERE id = ?",
                (devis_id,)
            )
            
            if not result:
                st.error(f"Devis #{devis_id} non trouvé.")
                return False
            
            ancien_statut = result[0]['statut']
            
            # Mettre à jour le statut
            affected = self.db.execute_update(
                "UPDATE formulaires SET statut = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (nouveau_statut, devis_id)
            )
            
            if affected > 0:
                # Enregistrer le changement
                self.enregistrer_validation_devis(
                    devis_id,
                    employee_id,
                    'CHANGEMENT_STATUT',
                    f"Statut changé de {ancien_statut} vers {nouveau_statut}. {commentaires}"
                )
                
                # Actions spéciales selon le nouveau statut
                if nouveau_statut == 'APPROUVÉ':
                    self.on_devis_accepte(devis_id)
                elif nouveau_statut == 'EXPIRÉ':
                    self.on_devis_expire(devis_id)
                
                return True
            
            return False
            
        except Exception as e:
            st.error(f"Erreur changement statut devis: {e}")
            return False
    
    def on_devis_accepte(self, devis_id: int):
        """
        Actions à effectuer quand un devis est accepté.
        TRANSFORME LE DEVIS EN PROJET.
        """
        # Vérification 1: S'assurer que le gestionnaire de projets est disponible
        if not self.project_manager:
            st.error("❌ Le gestionnaire de projets n'est pas disponible. Transformation impossible.")
            return

        try:
            devis = self.get_devis_complet(devis_id)
            
            # Vérification 2: S'assurer que le devis existe
            if not devis:
                st.error(f"❌ Devis #{devis_id} non trouvé. Transformation annulée.")
                return
            
            # Vérification 3: S'assurer qu'un projet n'est pas déjà lié
            if devis.get('project_id'):
                st.warning(f"ℹ️ Un projet (#{devis['project_id']}) est déjà lié à ce devis. Aucune action effectuée.")
                return

            # Préparation des données pour le nouveau projet
            project_data = {
                'nom_projet': f"Projet - Devis {devis.get('numero_document', devis_id)}",
                'client_company_id': devis.get('company_id'),
                'client_nom_cache': devis.get('client_nom'),
                'statut': 'À FAIRE',
                'priorite': devis.get('priorite', 'MOYEN'),
                'description': f"Projet créé automatiquement suite à l'acceptation du devis {devis.get('numero_document')}.\n\nNotes du devis:\n{devis.get('notes', '')}",
                'prix_estime': devis.get('totaux', {}).get('total_ht', 0.0),
                'date_soumis': datetime.now().strftime('%Y-%m-%d'),
                'date_prevu': (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d'),
                'employes_assignes': [devis.get('employee_id')] if devis.get('employee_id') else [],
                'tache': 'PROJET_CLIENT',
                'bd_ft_estime': 0.0,
                'client_legacy': '',
                'operations': [],
                'materiaux': []
            }
            
            # Création du projet via le gestionnaire de projets
            st.info(f"⏳ Transformation du devis #{devis_id} en projet...")
            project_id = self.project_manager.ajouter_projet(project_data)
            
            if project_id:
                # Lier le nouveau projet au devis
                self.db.execute_update(
                    "UPDATE formulaires SET project_id = ? WHERE id = ?",
                    (project_id, devis_id)
                )
                
                # Enregistrer l'action dans l'historique du devis
                self.enregistrer_validation_devis(
                    devis_id,
                    devis.get('employee_id', 1),
                    'TERMINAISON',
                    f"Devis transformé en Projet #{project_id}."
                )
                st.success(f"✅ Devis transformé avec succès en Projet #{project_id} !")
                st.balloons()
            else:
                st.error("❌ Échec de la création du projet. La transformation a été annulée.")

        except Exception as e:
            st.error(f"Erreur lors de la transformation du devis en projet: {e}")
    
    def on_devis_expire(self, devis_id: int):
        """Actions à effectuer quand un devis expire"""
        try:
            st.info(f"Le devis #{devis_id} est maintenant marqué comme expiré.")
            pass
        except Exception as e:
            st.error(f"Erreur expiration devis: {e}")
    
    def enregistrer_validation_devis(self, devis_id: int, employee_id: int, type_validation: str, commentaires: str):
        """Enregistre une validation dans l'historique du devis"""
        if not self.use_sqlite:
            return
        
        try:
            query = '''
                INSERT INTO formulaire_validations
                (formulaire_id, employee_id, type_validation, commentaires)
                VALUES (?, ?, ?, ?)
            '''
            self.db.execute_insert(query, (devis_id, employee_id, type_validation, commentaires))
        except Exception as e:
            st.error(f"Erreur enregistrement validation devis: {e}")
    
    def get_all_devis(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Récupère tous les devis avec filtres optionnels"""
        if not self.use_sqlite:
            return []
        
        try:
            query = f'''
                SELECT f.id, f.numero_document, f.statut, f.priorite, f.date_creation, 
                       f.date_echeance,
                       c.nom as client_nom,
                       e.prenom || ' ' || e.nom as responsable_nom,
                       p.nom_projet
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN employees e ON f.employee_id = e.id
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE (f.type_formulaire = 'DEVIS' OR (f.type_formulaire = 'ESTIMATION' AND f.metadonnees_json LIKE '%"type_reel": "DEVIS"%'))
            '''
            
            params = []
            
            if filters:
                if filters.get('statut'):
                    query += " AND f.statut = ?"
                    params.append(filters['statut'])
                
                if filters.get('client_id'):
                    query += " AND f.company_id = ?"
                    params.append(filters['client_id'])
                
                if filters.get('responsable_id'):
                    query += " AND f.employee_id = ?"
                    params.append(filters['responsable_id'])
                
                if filters.get('date_debut'):
                    query += " AND DATE(f.date_creation) >= ?"
                    params.append(filters['date_debut'])
                
                if filters.get('date_fin'):
                    query += " AND DATE(f.date_creation) <= ?"
                    params.append(filters['date_fin'])
            
            query += " ORDER BY f.date_creation DESC"
            
            rows = self.db.execute_query(query, tuple(params) if params else None)
            
            # Enrichir avec les totaux
            devis_list = []
            for row in rows:
                devis = dict(row)
                devis['totaux'] = self.calculer_totaux_devis(devis['id'])
                devis_list.append(devis)
            
            return devis_list
            
        except Exception as e:
            st.error(f"Erreur récupération liste devis: {e}")
            return []
    
    def get_devis_statistics(self) -> Dict[str, Any]:
        """Statistiques des devis"""
        if not self.use_sqlite:
            return {}
        
        try:
            stats = {
                'total_devis': 0,
                'par_statut': {},
                'montant_total': 0.0,
                'taux_acceptation': 0.0,
                'devis_expires': 0,
                'en_attente': 0
            }
            
            all_devis = self.get_all_devis()
            
            stats['total_devis'] = len(all_devis)
            
            for devis in all_devis:
                statut = devis['statut']
                if statut not in stats['par_statut']:
                    stats['par_statut'][statut] = {'count': 0, 'montant': 0.0}
                
                stats['par_statut'][statut]['count'] += 1
                stats['par_statut'][statut]['montant'] += devis.get('totaux', {}).get('total_ht', 0.0)
                stats['montant_total'] += devis.get('totaux', {}).get('total_ht', 0.0)
            
            # Taux d'acceptation
            accepted_count = stats['par_statut'].get('ACCEPTÉ', {}).get('count', 0)
            refused_count = stats['par_statut'].get('REFUSÉ', {}).get('count', 0)
            expired_count = stats['par_statut'].get('EXPIRÉ', {}).get('count', 0)
            
            total_decides = accepted_count + refused_count + expired_count
            
            if total_decides > 0:
                stats['taux_acceptation'] = (accepted_count / total_decides) * 100
            
            # Devis expirés (potentiellement, non encore marqués)
            query_expires = '''
                SELECT COUNT(*) as count FROM formulaires 
                WHERE (type_formulaire = 'DEVIS' OR (type_formulaire = 'ESTIMATION' AND metadonnees_json LIKE '%"type_reel": "DEVIS"%'))
                AND date_echeance < DATE('now') 
                AND statut NOT IN ('ACCEPTÉ', 'REFUSÉ', 'EXPIRÉ', 'ANNULÉ')
            '''
            result = self.db.execute_query(query_expires)
            stats['devis_expires'] = result[0]['count'] if result else 0
            
            # En attente
            stats['en_attente'] = stats['par_statut'].get('ENVOYÉ', {}).get('count', 0) + \
                                 stats['par_statut'].get('BROUILLON', {}).get('count', 0)
            
            return stats
            
        except Exception as e:
            st.error(f"Erreur statistiques devis: {e}")
            return {}
    
    def dupliquer_devis(self, devis_id: int, employee_id: int) -> Optional[int]:
        """Duplique un devis existant"""
        if not self.use_sqlite:
            return None
        
        try:
            devis_original = self.get_devis_complet(devis_id)
            if not devis_original:
                st.error("Devis original non trouvé pour duplication.")
                return None
            
            # Créer nouveau devis basé sur l'original
            nouveau_devis_data = {
                'client_company_id': devis_original['company_id'],
                'client_contact_id': devis_original.get('client_contact_id'),
                'project_id': devis_original.get('project_id'),
                'employee_id': employee_id,
                'date_echeance': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                'notes': f"Copie de {devis_original['numero_document']} - {devis_original.get('notes', '')}",
                'lignes': devis_original['lignes']
            }
            
            nouveau_id = self.create_devis(nouveau_devis_data)
            
            if nouveau_id:
                self.enregistrer_validation_devis(
                    nouveau_id,
                    employee_id,
                    'CREATION',
                    f"Devis dupliqué depuis #{devis_id} ({devis_original['numero_document']})"
                )
            
            return nouveau_id
            
        except Exception as e:
            st.error(f"Erreur duplication devis: {e}")
            return None

    # =========================================================================
    # EXPORT DEVIS HTML PROFESSIONNEL
    # =========================================================================
    
    def export_devis_html(self, devis_id: int) -> Optional[str]:
        """
        Exporte un devis au format HTML professionnel pour les clients
        
        Args:
            devis_id: ID du devis à exporter
            
        Returns:
            str: Contenu HTML du devis ou None si erreur
        """
        if not self.use_sqlite:
            st.error("Export HTML disponible uniquement en mode SQLite")
            return None
        
        try:
            # Récupérer toutes les données du devis
            devis_data = self.get_devis_complet(devis_id)
            if not devis_data:
                st.error(f"Devis #{devis_id} non trouvé pour export")
                return None
            
            # Générer le HTML
            html_content = self.generate_devis_html_template(devis_data)
            
            return html_content
            
        except Exception as e:
            st.error(f"Erreur export HTML devis: {e}")
            return None
    
    def generate_devis_html_template(self, devis_data: Dict[str, Any]) -> str:
        """
        Génère le template HTML pour un devis en utilisant le même style que le bon de travail
        
        Args:
            devis_data: Données complètes du devis
            
        Returns:
            str: Contenu HTML formaté
        """
        try:
            # Formatage des dates
            date_creation = devis_data.get('date_creation', '')
            if date_creation:
                try:
                    date_creation_formatted = datetime.fromisoformat(date_creation).strftime('%d/%m/%Y')
                except:
                    date_creation_formatted = date_creation[:10] if len(date_creation) >= 10 else date_creation
            else:
                date_creation_formatted = 'N/A'
            
            date_echeance = devis_data.get('date_echeance', '')
            try:
                date_echeance_formatted = datetime.fromisoformat(date_echeance).strftime('%d/%m/%Y') if date_echeance else 'N/A'
            except:
                date_echeance_formatted = date_echeance
            
            # Calcul du nombre de jours de validité restants
            jours_validite = 0
            if date_echeance:
                try:
                    echeance = datetime.fromisoformat(date_echeance).date() if isinstance(date_echeance, str) else date_echeance
                    today = datetime.now().date()
                    jours_validite = (echeance - today).days
                except:
                    jours_validite = 0
            
            # Badge de validité
            if jours_validite > 7:
                validite_badge = f'<span class="badge badge-in-progress">✅ Valide ({jours_validite} jours)</span>'
            elif jours_validite > 0:
                validite_badge = f'<span class="badge badge-pending">⚡ Expire bientôt ({jours_validite} jours)</span>'
            else:
                validite_badge = '<span class="badge badge-on-hold">⚠️ Expiré</span>'
            
            # Récupération des totaux
            totaux = devis_data.get('totaux', {})
            total_ht = totaux.get('total_ht', 0)
            taux_tva = totaux.get('taux_tva', 14.975)
            montant_tva = totaux.get('montant_tva', 0)
            total_ttc = totaux.get('total_ttc', 0)
            
            # Génération des lignes du tableau
            lignes_html = ""
            if devis_data.get('lignes'):
                for ligne in devis_data['lignes']:
                    montant_ligne = ligne.get('quantite', 0) * ligne.get('prix_unitaire', 0)
                    lignes_html += f"""
                    <tr>
                        <td><strong>{ligne.get('description', '')}</strong></td>
                        <td style="text-align: center;">{ligne.get('quantite', 0):,.2f}</td>
                        <td style="text-align: center;">{ligne.get('unite', '')}</td>
                        <td style="text-align: right;">{ligne.get('prix_unitaire', 0):,.2f} $</td>
                        <td style="text-align: right;"><strong>{montant_ligne:,.2f} $</strong></td>
                    </tr>
                    """
            else:
                lignes_html = """
                <tr>
                    <td colspan="5" style="text-align: center; color: #6B7280;">Aucune ligne dans ce devis</td>
                </tr>
                """
            
            # Badge de statut
            statut = devis_data.get('statut', 'BROUILLON')
            statut_badges = {
                'BROUILLON': 'badge-pending',
                'VALIDÉ': 'badge-in-progress', 
                'ENVOYÉ': 'badge-in-progress',
                'APPROUVÉ': 'badge-completed',
                'TERMINÉ': 'badge-completed',
                'ANNULÉ': 'badge-on-hold'
            }
            statut_badge_class = statut_badges.get(statut, 'badge-pending')
            
            # Conditions de paiement et validité
            conditions_paiement = """
            <div class="instructions-box">
                <h4 style="color: var(--primary-color-darker); margin-bottom: 10px;">💰 Conditions de Paiement</h4>
                <p><strong>• Acompte :</strong> 50% à la commande</p>
                <p><strong>• Solde :</strong> À la livraison</p>
                <p><strong>• Délai de paiement :</strong> Net 30 jours</p>
                <p><strong>• Validité du devis :</strong> 30 jours à compter de la date d'émission</p>
                <p><strong>• Prix :</strong> Les prix sont exprimés en dollars canadiens (CAD) et incluent les taxes applicables</p>
            </div>
            """
            
            # Template HTML complet
            html_template = f"""
            <!DOCTYPE html>
            <html lang="fr">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Devis - {devis_data.get('numero_document', 'N/A')}</title>
                <style>
                    :root {{
                        --primary-color: #00A971;
                        --primary-color-darker: #00673D;
                        --primary-color-darkest: #004C2E;
                        --primary-color-lighter: #DCFCE7;
                        --background-color: #F9FAFB;
                        --secondary-background-color: #FFFFFF;
                        --text-color: #374151;
                        --text-color-light: #6B7280;
                        --border-color: #E5E7EB;
                        --border-radius-md: 0.5rem;
                        --box-shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
                    }}
                    
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: var(--text-color);
                        background-color: var(--background-color);
                        margin: 0;
                        padding: 15px;
                    }}
                    
                    .container {{
                        max-width: 8.5in;
                        margin: 0 auto;
                        background-color: white;
                        border-radius: 12px;
                        box-shadow: var(--box-shadow-md);
                        overflow: hidden;
                        width: 100%;
                    }}
                    
                    .header {{
                        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-color-darker) 100%);
                        color: white;
                        padding: 30px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }}
                    
                    .logo-container {{
                        display: flex;
                        align-items: center;
                        gap: 20px;
                    }}
                    
                    .logo-box {{
                        background-color: white;
                        width: 70px;
                        height: 45px;
                        border-radius: 8px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
                    }}
                    
                    .logo-text {{
                        font-family: 'Segoe UI', sans-serif;
                        font-weight: 800;
                        font-size: 24px;
                        color: var(--primary-color);
                        letter-spacing: 1px;
                    }}
                    
                    .company-info {{
                        text-align: left;
                    }}
                    
                    .company-name {{
                        font-weight: 700;
                        font-size: 28px;
                        margin-bottom: 5px;
                        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                    }}
                    
                    .company-subtitle {{
                        font-size: 16px;
                        opacity: 0.9;
                    }}
                    
                    .contact-info {{
                        text-align: right;
                        font-size: 14px;
                        line-height: 1.4;
                        opacity: 0.95;
                    }}
                    
                    .document-title {{
                        background: var(--primary-color-lighter);
                        padding: 20px 30px;
                        border-left: 5px solid var(--primary-color);
                    }}
                    
                    .document-title h1 {{
                        color: var(--primary-color-darker);
                        font-size: 24px;
                        margin-bottom: 10px;
                    }}
                    
                    .document-meta {{
                        display: flex;
                        justify-content: space-between;
                        color: var(--text-color-light);
                        font-size: 14px;
                    }}
                    
                    .content {{
                        padding: 25px;
                    }}
                    
                    .section {{
                        margin-bottom: 30px;
                    }}
                    
                    .section-title {{
                        color: var(--primary-color-darker);
                        font-size: 18px;
                        font-weight: 600;
                        margin-bottom: 15px;
                        padding-bottom: 8px;
                        border-bottom: 2px solid var(--primary-color-lighter);
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }}
                    
                    .info-grid {{
                        display: grid;
                        grid-template-columns: 1fr 1fr 1fr;
                        gap: 15px;
                        margin-bottom: 20px;
                    }}
                    
                    .info-item {{
                        background: var(--background-color);
                        padding: 15px;
                        border-radius: var(--border-radius-md);
                        border-left: 3px solid var(--primary-color);
                    }}
                    
                    .info-label {{
                        font-weight: 600;
                        color: var(--text-color-light);
                        font-size: 12px;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        margin-bottom: 5px;
                    }}
                    
                    .info-value {{
                        font-size: 16px;
                        color: var(--text-color);
                        font-weight: 500;
                    }}
                    
                    .table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 15px 0;
                        border-radius: var(--border-radius-md);
                        overflow: hidden;
                        box-shadow: var(--box-shadow-md);
                    }}
                    
                    .table th {{
                        background: var(--primary-color);
                        color: white;
                        padding: 12px;
                        text-align: left;
                        font-weight: 600;
                        font-size: 14px;
                    }}
                    
                    .table td {{
                        padding: 12px;
                        border-bottom: 1px solid var(--border-color);
                        vertical-align: top;
                    }}
                    
                    .table tr:nth-child(even) {{
                        background-color: var(--background-color);
                    }}
                    
                    .table tr:hover {{
                        background-color: var(--primary-color-lighter);
                    }}
                    
                    .badge {{
                        padding: 4px 12px;
                        border-radius: 20px;
                        font-size: 11px;
                        font-weight: 600;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        display: inline-block;
                    }}
                    
                    .badge-pending {{ background: #fef3c7; color: #92400e; }}
                    .badge-in-progress {{ background: #dbeafe; color: #1e40af; }}
                    .badge-completed {{ background: #d1fae5; color: #065f46; }}
                    .badge-on-hold {{ background: #fee2e2; color: #991b1b; }}
                    
                    .summary-box {{
                        background: linear-gradient(45deg, var(--primary-color-lighter), white);
                        border: 2px solid var(--primary-color);
                        border-radius: var(--border-radius-md);
                        padding: 20px;
                        margin: 20px 0;
                    }}
                    
                    .summary-grid {{
                        display: grid;
                        grid-template-columns: repeat(4, 1fr);
                        gap: 15px;
                    }}
                    
                    .summary-item {{
                        text-align: center;
                        background: white;
                        padding: 15px;
                        border-radius: var(--border-radius-md);
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    
                    .summary-number {{
                        font-size: 24px;
                        font-weight: 700;
                        color: var(--primary-color-darker);
                        display: block;
                    }}
                    
                    .summary-label {{
                        font-size: 12px;
                        color: var(--text-color-light);
                        text-transform: uppercase;
                        font-weight: 600;
                        letter-spacing: 0.5px;
                    }}
                    
                    .instructions-box {{
                        background: var(--background-color);
                        border-left: 4px solid var(--primary-color);
                        padding: 20px;
                        border-radius: 0 var(--border-radius-md) var(--border-radius-md) 0;
                        margin: 15px 0;
                    }}
                    
                    .footer {{
                        background: var(--primary-color-darkest);
                        color: white;
                        padding: 20px 30px;
                        text-align: center;
                        font-size: 12px;
                        line-height: 1.4;
                    }}
                    
                    .client-address {{
                        background: var(--background-color);
                        border: 2px solid var(--primary-color-lighter);
                        border-radius: var(--border-radius-md);
                        padding: 15px;
                        margin: 15px 0;
                        font-size: 14px;
                        line-height: 1.4;
                    }}
                    
                    @media print {{
                        body {{ 
                            margin: 0; 
                            padding: 0; 
                        }}
                        .container {{ 
                            box-shadow: none; 
                            max-width: 100%;
                            width: 8.5in;
                        }}
                        .table {{ 
                            break-inside: avoid; 
                            font-size: 12px;
                        }}
                        .section {{ 
                            break-inside: avoid-page; 
                        }}
                        .header {{
                            padding: 20px 25px;
                        }}
                        .content {{
                            padding: 20px;
                        }}
                        @page {{
                            size: letter;
                            margin: 0.5in;
                        }}
                    }}
                    
                    @media screen and (max-width: 768px) {{
                        .container {{
                            max-width: 100%;
                            margin: 0 10px;
                        }}
                        .info-grid {{
                            grid-template-columns: 1fr;
                            gap: 10px;
                        }}
                        .summary-grid {{
                            grid-template-columns: repeat(2, 1fr);
                        }}
                        .header {{
                            flex-direction: column;
                            text-align: center;
                            gap: 15px;
                        }}
                        .contact-info {{
                            text-align: center;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <!-- En-tête -->
                    <div class="header">
                        <div class="logo-container">
                            <div class="logo-box">
                                <div class="logo-text">DG</div>
                            </div>
                            <div class="company-info">
                                <div class="company-name">Desmarais & Gagné inc.</div>
                                <div class="company-subtitle">Fabrication et Assemblage Métallurgique</div>
                            </div>
                        </div>
                        <div class="contact-info">
                            565 rue Maisonneuve<br>
                            Granby, QC J2G 3H5<br>
                            Tél.: (450) 372-9630<br>
                            Téléc.: (450) 372-8122
                        </div>
                    </div>
                    
                    <!-- Titre du document -->
                    <div class="document-title">
                        <h1>💰 DEVIS</h1>
                        <div class="document-meta">
                            <span><strong>N° Devis:</strong> {devis_data.get('numero_document', 'N/A')}</span>
                            <span><strong>Généré le:</strong> {datetime.now().strftime('%d/%m/%Y à %H:%M')}</span>
                        </div>
                    </div>
                    
                    <!-- Contenu principal -->
                    <div class="content">
                        <!-- Informations générales -->
                        <div class="section">
                            <h2 class="section-title">📋 Informations du Devis</h2>
                            <div class="info-grid">
                                <div class="info-item">
                                    <div class="info-label">Client</div>
                                    <div class="info-value">{devis_data.get('client_nom', 'N/A')}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Responsable</div>
                                    <div class="info-value">{devis_data.get('responsable_nom', 'N/A')}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Statut</div>
                                    <div class="info-value">
                                        <span class="badge {statut_badge_class}">
                                            {statut}
                                        </span>
                                    </div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Date Création</div>
                                    <div class="info-value">{date_creation_formatted}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Date Échéance</div>
                                    <div class="info-value">{date_echeance_formatted}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Validité</div>
                                    <div class="info-value">{validite_badge}</div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Adresse du client -->
                        <div class="section">
                            <h2 class="section-title">📍 Adresse de Facturation</h2>
                            <div class="client-address">
                                <strong>{devis_data.get('client_nom', 'N/A')}</strong><br>
                                {devis_data.get('client_adresse_complete', 'Adresse non disponible').replace(chr(10), '<br>')}
                            </div>
                        </div>
                        
                        <!-- Résumé financier -->
                        <div class="summary-box">
                            <h3 style="color: var(--primary-color-darker); margin-bottom: 15px; text-align: center;">💰 Résumé Financier</h3>
                            <div class="summary-grid">
                                <div class="summary-item">
                                    <span class="summary-number">{len(devis_data.get('lignes', []))}</span>
                                    <span class="summary-label">Articles</span>
                                </div>
                                <div class="summary-item">
                                    <span class="summary-number">{total_ht:,.2f} $</span>
                                    <span class="summary-label">Total HT</span>
                                </div>
                                <div class="summary-item">
                                    <span class="summary-number">{montant_tva:,.2f} $</span>
                                    <span class="summary-label">TVA ({taux_tva:.3f}%)</span>
                                </div>
                                <div class="summary-item">
                                    <span class="summary-number">{total_ttc:,.2f} $</span>
                                    <span class="summary-label">Total TTC</span>
                                </div>
                            </div>
                        </div>
                
                        <!-- Détail des articles -->
                        <div class="section">
                            <h2 class="section-title">📝 Détail des Articles et Services</h2>
                            <table class="table">
                                <thead>
                                    <tr>
                                        <th>Description</th>
                                        <th style="text-align: center;">Quantité</th>
                                        <th style="text-align: center;">Unité</th>
                                        <th style="text-align: right;">Prix Unit.</th>
                                        <th style="text-align: right;">Montant</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {lignes_html}
                                    <!-- Ligne de total -->
                                    <tr style="background: var(--primary-color-lighter); font-weight: bold;">
                                        <td colspan="4" style="text-align: right; padding: 15px;"><strong>SOUS-TOTAL (HT)</strong></td>
                                        <td style="text-align: right; padding: 15px;"><strong>{total_ht:,.2f} $ CAD</strong></td>
                                    </tr>
                                    <tr style="background: var(--background-color);">
                                        <td colspan="4" style="text-align: right; padding: 10px;">TVA ({taux_tva:.3f}%)</td>
                                        <td style="text-align: right; padding: 10px;">{montant_tva:,.2f} $ CAD</td>
                                    </tr>
                                    <tr style="background: var(--primary-color); color: white; font-weight: bold; font-size: 16px;">
                                        <td colspan="4" style="text-align: right; padding: 15px;"><strong>TOTAL TTC</strong></td>
                                        <td style="text-align: right; padding: 15px;"><strong>{total_ttc:,.2f} $ CAD</strong></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                
                        <!-- Notes du devis -->
                        {f'''
                        <div class="section">
                            <h2 class="section-title">📝 Notes et Commentaires</h2>
                            <div class="instructions-box">
                                {devis_data.get('notes', 'Aucune note particulière.')}
                            </div>
                        </div>
                        ''' if devis_data.get('notes') else ''}
                        
                        <!-- Conditions -->
                        {conditions_paiement}
                        
                    </div>
                    
                    <!-- Pied de page -->
                    <div class="footer">
                        <div><strong>🏭 Desmarais & Gagné inc.</strong> - Système de Gestion CRM</div>
                        <div>Devis généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</div>
                        <div>📞 (450) 372-9630 | 📧 info@dg-inc.com | 🌐 www.dg-inc.com</div>
                        <div style="margin-top: 10px; font-size: 11px; opacity: 0.8;">
                            Ce devis est valable {devis_data.get('metadonnees', {}).get('validite_jours', 30)} jours à compter de la date d'émission.
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html_template
            
        except Exception as e:
            st.error(f"Erreur génération template HTML: {e}")
            return ""
    
    def save_devis_html_file(self, devis_id: int, filename: Optional[str] = None) -> Optional[str]:
        """
        Sauvegarde le devis en fichier HTML
        
        Args:
            devis_id: ID du devis
            filename: Nom du fichier (optionnel, généré automatiquement si None)
            
        Returns:
            str: Chemin du fichier créé ou None si erreur
        """
        try:
            html_content = self.export_devis_html(devis_id)
            if not html_content:
                return None
            
            # Générer le nom de fichier si non fourni
            if not filename:
                devis_data = self.get_devis_complet(devis_id)
                numero_devis = devis_data.get('numero_document', f'DEVIS-{devis_id}')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{numero_devis}_{timestamp}.html"
            
            # Assurer que le fichier a une extension .html
            if not filename.endswith('.html'):
                filename += '.html'
            
            # Écrire le fichier
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return filename
            
        except Exception as e:
            st.error(f"Erreur sauvegarde fichier HTML: {e}")
            return None

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
        if st.button("📋 Utiliser dans un devis", key="use_in_quote_from_details", use_container_width=True):
            st.info("💡 Vous pouvez utiliser ce produit lors de la création d'un devis dans l'onglet Devis.")

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
# FONCTIONS D'AFFICHAGE STREAMLIT POUR DEVIS AVEC SUPPRESSION + EXPORT HTML
# =========================================================================

def render_crm_devis_tab(crm_manager: GestionnaireCRM):
    """Interface Streamlit pour la gestion des devis avec suppression et export HTML"""
    if not crm_manager.use_sqlite:
        st.warning("⚠️ Le système de devis n'est disponible qu'en mode SQLite.")
        return
    
    st.title("🧾 Gestion des Devis")
    
    # Statistiques en haut
    stats = crm_manager.get_devis_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Devis", stats.get('total_devis', 0))
    with col2:
        st.metric("Taux d'acceptation", f"{stats.get('taux_acceptation', 0):.1f}%")
    with col3:
        montant_total = stats.get('montant_total', 0.0)
        st.metric("Montant Total (HT)", f"{montant_total:,.0f} $")
    with col4:
        st.metric("En Attente", stats.get('en_attente', 0))
    
    # Onglets principal
    tab1, tab2, tab3 = st.tabs(["📋 Liste des Devis", "➕ Nouveau Devis", "📊 Statistiques"])
    
    with tab1:
        st.subheader("Liste des Devis")
        
        # Filtres
        col_filtre1, col_filtre2, col_filtre3 = st.columns(3)
        
        with col_filtre1:
            filtre_statut = st.selectbox("Statut", 
                options=["Tous"] + STATUTS_DEVIS,
                key="filtre_statut_devis"
            )
        
        with col_filtre2:
            # Liste des clients
            clients = crm_manager.entreprises
            client_options = [("", "Tous les clients")] + [(c['id'], c['nom']) for c in clients]
            filtre_client = st.selectbox("Client",
                options=[opt[0] for opt in client_options],
                format_func=lambda x: next((opt[1] for opt in client_options if opt[0] == x), "Tous les clients"),
                key="filtre_client_devis"
            )
        
        with col_filtre3:
            # Période
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                date_debut = st.date_input("Du", value=None, key="date_debut_devis")
            with col_date2:
                date_fin = st.date_input("Au", value=None, key="date_fin_devis")
        
        # Construire les filtres
        filters = {}
        if filtre_statut != "Tous":
            filters['statut'] = filtre_statut
        if filtre_client:
            filters['client_id'] = filtre_client
        if date_debut:
            filters['date_debut'] = date_debut.strftime('%Y-%m-%d')
        if date_fin:
            filters['date_fin'] = date_fin.strftime('%Y-%m-%d')
        
        # Récupérer et afficher les devis
        devis_list = crm_manager.get_all_devis(filters)
        
        if devis_list:
            # Préparer les données pour l'affichage
            display_data = []
            for devis in devis_list:
                display_data.append({
                    "ID": devis['id'],
                    "Numéro": devis['numero_document'],
                    "Client": devis['client_nom'],
                    "Statut": devis['statut'],
                    "Date Création": devis['date_creation'][:10] if devis.get('date_creation') else 'N/A',
                    "Échéance": devis['date_echeance'],
                    "Total TTC": f"{devis['totaux']['total_ttc']:,.2f} $",
                    "Responsable": devis.get('responsable_nom', 'N/A')
                })
            
            df = pd.DataFrame(display_data)
            st.dataframe(df, use_container_width=True)
            
            # Actions sur devis sélectionné MODIFIÉES AVEC SUPPRESSION + EXPORT HTML
            st.markdown("---")
            selected_devis_id = st.selectbox(
                "Sélectionner un devis pour actions:",
                options=[d['id'] for d in devis_list],
                format_func=lambda x: f"#{x} - {next((d['numero_document'] for d in devis_list if d['id'] == x), '')}",
                key="selected_devis_action"
            )
            
            if selected_devis_id:
                # Vérifier si le devis peut être supprimé
                selected_devis = next((d for d in devis_list if d['id'] == selected_devis_id), None)
                peut_supprimer = selected_devis and selected_devis.get('statut') not in ['APPROUVÉ', 'TERMINÉ']
                
                if peut_supprimer:
                    col_action1, col_action2, col_action3, col_action4, col_action5, col_action6 = st.columns(6)
                else:
                    col_action1, col_action2, col_action3, col_action4, col_action5 = st.columns(5)
                
                with col_action1:
                    if st.button("👁️ Voir Détails", key="voir_devis", use_container_width=True):
                        st.session_state.crm_action = "view_devis_details"
                        st.session_state.crm_selected_id = selected_devis_id
                        st.rerun()
                
                with col_action2:
                    if st.button("📄 Dupliquer", key="dupliquer_devis_liste", use_container_width=True):
                        nouveau_id = crm_manager.dupliquer_devis(selected_devis_id, 1)
                        if nouveau_id:
                            st.success(f"Devis dupliqué avec succès ! Nouveau devis #{nouveau_id}.")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la duplication du devis.")
                
                with col_action3:
                    if st.button("📧 Envoyer", key="send_devis", use_container_width=True):
                        if crm_manager.changer_statut_devis(selected_devis_id, 'ENVOYÉ', 1, "Envoyé par interface"):
                            st.success("Devis marqué comme envoyé !")
                            st.rerun()
                        else:
                            st.error("Erreur lors du changement de statut.")
                
                with col_action4:
                    if st.button("✏️ Modifier", key="edit_devis", use_container_width=True):
                        st.session_state.crm_action = "edit_devis"
                        st.session_state.crm_selected_id = selected_devis_id
                        st.rerun()
                
                with col_action5:
                    if st.button("📑 Export HTML", key="export_html_devis", use_container_width=True):
                        html_content = crm_manager.export_devis_html(selected_devis_id)
                        if html_content:
                            # Afficher un lien de téléchargement
                            st.download_button(
                                label="💾 Télécharger le devis HTML",
                                data=html_content,
                                file_name=f"devis_{selected_devis['numero_document']}.html",
                                mime="text/html",
                                key="download_html_devis"
                            )
                            st.success("✅ Devis HTML généré avec succès !")
                        else:
                            st.error("❌ Erreur lors de l'export HTML.")
                
                # Bouton de suppression si possible
                if peut_supprimer:
                    with col_action6:
                        if st.button("🗑️ Supprimer", key="delete_devis_liste", use_container_width=True, type="secondary"):
                            st.session_state.crm_confirm_delete_devis_id = selected_devis_id
                            st.rerun()
                
                # Gestion de la confirmation de suppression dans la liste
                if 'crm_confirm_delete_devis_id' in st.session_state and st.session_state.crm_confirm_delete_devis_id == selected_devis_id:
                    st.markdown("---")
                    st.error(f"⚠️ Confirmer la suppression du devis #{selected_devis_id}")
                    
                    motif = st.text_input("Motif (optionnel):", key="motif_liste")
                    
                    col_conf, col_ann = st.columns(2)
                    with col_conf:
                        if st.button("🗑️ SUPPRIMER", key="confirm_delete_liste", type="primary"):
                            if crm_manager.supprimer_devis(selected_devis_id, 1, motif):
                                del st.session_state.crm_confirm_delete_devis_id
                                st.rerun()
                    with col_ann:
                        if st.button("❌ Annuler", key="cancel_delete_liste"):
                            del st.session_state.crm_confirm_delete_devis_id
                            st.rerun()
                
                # Afficher un message si le devis ne peut pas être supprimé
                if not peut_supprimer:
                    st.info(f"💡 Ce devis ne peut pas être supprimé car il est au statut '{selected_devis.get('statut') if selected_devis else 'INCONNU'}'. Vous pouvez l'annuler à la place.")
        else:
            st.info("Aucun devis trouvé avec les filtres sélectionnés.")
    
    with tab2:
        st.subheader("Créer un Nouveau Devis")

        # --- PARTIE 1 : AJOUT INTERACTIF DES LIGNES (HORS FORMULAIRE) ---
        st.markdown("##### Étape 1 : Ajouter les lignes du devis")
        
        # Initialisation du conteneur de lignes dans la session
        if 'devis_lignes' not in st.session_state:
            st.session_state.devis_lignes = []

        # Section pour sélectionner un produit existant
        st.markdown("**Option 1: Ajouter depuis le catalogue produits**")
        with st.container(border=True):
            col_prod1, col_prod2, col_prod3 = st.columns([2, 1, 1])
            
            with col_prod1:
                # Sélection d'un produit
                produits_options = [("", "Sélectionner un produit...")] + [(p['id'], f"{p['code_produit']} - {p['nom']}") for p in crm_manager.produits]
                produit_selectionne = st.selectbox(
                    "Produit du catalogue",
                    options=[opt[0] for opt in produits_options],
                    format_func=lambda x: next((opt[1] for opt in produits_options if opt[0] == x), "Sélectionner un produit..."),
                    key="produit_catalogue_select"
                )
            
            with col_prod2:
                quantite_produit = st.number_input("Quantité", min_value=0.01, value=1.0, step=0.1, key="quantite_produit_catalogue", format="%.2f")
            
            with col_prod3:
                st.write("")  # Espacement
                if st.button("➕ Ajouter depuis catalogue", key="add_from_catalog", use_container_width=True):
                    if produit_selectionne:
                        produit_data = crm_manager.get_produit_by_id(produit_selectionne)
                        if produit_data:
                            st.session_state.devis_lignes.append({
                                'description': f"{produit_data['code_produit']} - {produit_data['nom']}",
                                'quantite': quantite_produit,
                                'unite': produit_data['unite_vente'],
                                'prix_unitaire': produit_data['prix_unitaire'],
                                'code_article': produit_data['code_produit']
                            })
                            st.success(f"Produit {produit_data['code_produit']} ajouté au devis!")
                            st.rerun()
                    else:
                        st.warning("Veuillez sélectionner un produit.")

        st.markdown("**Option 2: Saisie manuelle**")
        # Formulaire pour ajouter une ligne manuellement
        with st.container(border=True):
            col_ligne1, col_ligne2, col_ligne3, col_ligne4, col_ligne5 = st.columns([3, 1, 1, 1, 1])
            with col_ligne1:
                description = st.text_input("Description", key="ligne_description")
            with col_ligne2:
                quantite = st.number_input("Qté", min_value=0.01, value=1.0, step=0.1, key="ligne_quantite", format="%.2f")
            with col_ligne3:
                unite = st.selectbox("Unité", options=UNITES_VENTE, key="ligne_unite")
            with col_ligne4:
                prix_unitaire = st.number_input("Prix U.", min_value=0.0, step=0.01, key="ligne_prix", format="%.2f")
            with col_ligne5:
                st.write("") # Espace pour aligner le bouton
                if st.button("➕ Ajouter", key="ajouter_ligne_btn", use_container_width=True):
                    if description and quantite > 0:
                        st.session_state.devis_lignes.append({
                            'description': description,
                            'quantite': quantite,
                            'unite': unite,
                            'prix_unitaire': prix_unitaire
                        })
                        # Pas besoin de rerun ici, Streamlit rafraîchira la partie ci-dessous
                    else:
                        st.warning("La description et la quantité sont requises.")
        
        # Affichage des lignes déjà ajoutées
        if st.session_state.devis_lignes:
            st.markdown("**Lignes du devis :**")
            total_ht_preview = 0
            with st.container(border=True):
                for i, ligne in enumerate(st.session_state.devis_lignes):
                    col_disp, col_del = st.columns([10, 1])
                    with col_disp:
                        montant = ligne['quantite'] * ligne['prix_unitaire']
                        total_ht_preview += montant
                        st.write(f"• {ligne['description']} ({ligne['quantite']} {ligne['unite']} x {ligne['prix_unitaire']:.2f} $) = **{montant:.2f} $**")
                    with col_del:
                        if st.button("🗑️", key=f"remove_ligne_{i}", help="Supprimer la ligne"):
                            st.session_state.devis_lignes.pop(i)
                            st.rerun()
                st.markdown(f"**Total (HT) : {total_ht_preview:,.2f} $**")
        st.markdown("---")

        # --- PARTIE 2 : FORMULAIRE FINAL POUR LES INFORMATIONS GÉNÉRALES ---
        st.markdown("##### Étape 2 : Renseigner les informations générales et créer")

        with st.form("formulaire_nouveau_devis"):
            col_base1, col_base2 = st.columns(2)
            
            with col_base1:
                # Client
                clients = crm_manager.entreprises
                client_options = [(c['id'], c['nom']) for c in clients]
                client_id = st.selectbox("Client *", options=[opt[0] for opt in client_options],
                                         format_func=lambda x: next((opt[1] for opt in client_options if opt[0] == x), ''),
                                         key="nouveau_devis_client")
                
                if crm_manager.use_sqlite:
                    employees = crm_manager.db.execute_query("SELECT id, prenom || ' ' || nom as nom FROM employees WHERE statut = 'ACTIF'")
                    emp_options = [(e['id'], e['nom']) for e in employees] if employees else []
                    responsable_id = st.selectbox("Responsable *", options=[opt[0] for opt in emp_options],
                                                  format_func=lambda x: next((opt[1] for opt in emp_options if opt[0] == x), ''),
                                                  key="nouveau_devis_responsable")
                else:
                    responsable_id = 1

            with col_base2:
                echeance = st.date_input("Date d'échéance *", value=datetime.now().date() + timedelta(days=30),
                                         key="nouveau_devis_echeance")
                
                if crm_manager.use_sqlite:
                    projets = crm_manager.db.execute_query("SELECT id, nom_projet FROM projects WHERE statut != 'TERMINÉ'")
                    projet_options = [("", "Aucun projet")] + [(p['id'], p['nom_projet']) for p in projets] if projets else [("", "Aucun projet")]
                    projet_id = st.selectbox("Projet lié", options=[opt[0] for opt in projet_options],
                                             format_func=lambda x: next((opt[1] for opt in projet_options if opt[0] == x), 'Aucun projet'),
                                             key="nouveau_devis_projet")
                else:
                    projet_id = None
            
            notes = st.text_area("Notes ou conditions", key="nouveau_devis_notes")
            
            # Boutons de soumission
            submitted = st.form_submit_button("💾 Créer le Devis en Brouillon", type="primary", use_container_width=True)
            
            if submitted:
                if not client_id or not responsable_id or not st.session_state.devis_lignes:
                    st.error("Veuillez remplir le client, le responsable et ajouter au moins une ligne au devis.")
                else:
                    devis_data = {
                        'client_company_id': client_id,
                        'employee_id': responsable_id,
                        'project_id': projet_id if projet_id else None,
                        'date_echeance': echeance.strftime('%Y-%m-%d'),
                        'notes': notes,
                        'lignes': st.session_state.devis_lignes
                    }
                    
                    devis_id = crm_manager.create_devis(devis_data)
                    
                    if devis_id:
                        devis_cree = crm_manager.get_devis_complet(devis_id)
                        st.success(f"✅ Devis créé avec succès ! Numéro : {devis_cree.get('numero_document')}")
                        st.session_state.devis_lignes = []  # Vider les lignes pour le prochain devis
                        st.rerun()
                    else:
                        st.error("Erreur lors de la création du devis.")
    
    with tab3:
        st.subheader("Statistiques des Devis")
        
        if stats.get('total_devis', 0) > 0:
            if stats.get('par_statut'):
                statut_data = pd.DataFrame([
                    {'Statut': k, 'Nombre': v['count'], 'Montant HT': v['montant']}
                    for k, v in stats['par_statut'].items() if isinstance(v, dict)
                ])
                
                col_graph1, col_graph2 = st.columns(2)
                
                with col_graph1:
                    st.markdown("**Répartition par Statut (Nombre)**")
                    st.bar_chart(statut_data.set_index('Statut')['Nombre'])
                
                with col_graph2:
                    st.markdown("**Répartition par Statut (Montant HT)**")
                    st.bar_chart(statut_data.set_index('Statut')['Montant HT'])
        else:
            st.info("Aucune donnée de devis disponible pour les statistiques.")

def render_crm_devis_details(crm_manager: GestionnaireCRM, devis_data):
    """Affiche les détails d'un devis avec option de suppression et export HTML"""
    if not devis_data:
        st.error("Devis non trouvé.")
        return

    st.subheader(f"🧾 Détails du Devis: {devis_data.get('numero_document')} (SQLite)")

    # Informations principales
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**ID:** {devis_data.get('id')}")
        st.write(f"**Client:** {devis_data.get('client_nom', 'N/A')}")
        st.write(f"**Responsable:** {devis_data.get('responsable_nom', 'N/A')}")
        st.write(f"**Statut:** {devis_data.get('statut', 'N/A')}")
    with c2:
        date_creation = devis_data.get('date_creation')
        st.write(f"**Date création:** {date_creation[:10] if date_creation else 'N/A'}")
        st.write(f"**Date échéance:** {devis_data.get('date_echeance', 'N/A')}")
        st.write(f"**Projet lié:** {devis_data.get('nom_projet', 'Aucun')}")

    # Adresse du client
    if devis_data.get('client_adresse_complete'):
        st.markdown("### 📍 Adresse du Client")
        st.text_area("client_adresse_devis", value=devis_data['client_adresse_complete'], height=100, disabled=True, label_visibility="collapsed")

    # Totaux
    totaux = devis_data.get('totaux', {})
    st.markdown("### 💰 Totaux")
    col_total1, col_total2, col_total3 = st.columns(3)
    with col_total1:
        st.metric("Total HT", f"{totaux.get('total_ht', 0):,.2f} $")
    with col_total2:
        st.metric("TVA", f"{totaux.get('montant_tva', 0):,.2f} $")
    with col_total3:
        st.metric("Total TTC", f"{totaux.get('total_ttc', 0):,.2f} $")

    # Lignes du devis
    st.markdown("### 📋 Lignes du Devis")
    if devis_data.get('lignes'):
        lignes_df_data = []
        for ligne in devis_data['lignes']:
            lignes_df_data.append({
                "Description": ligne.get('description', ''),
                "Quantité": ligne.get('quantite', 0),
                "Unité": ligne.get('unite', ''),
                "Prix unitaire": f"{ligne.get('prix_unitaire', 0):,.2f} $",
                "Montant": f"{ligne.get('quantite', 0) * ligne.get('prix_unitaire', 0):,.2f} $"
            })
        
        st.dataframe(pd.DataFrame(lignes_df_data), use_container_width=True)
    else:
        st.info("Aucune ligne dans ce devis.")

    # Notes
    st.markdown("### 📝 Notes")
    st.text_area("devis_detail_notes_display", value=devis_data.get('notes', 'Aucune note.'), height=100, disabled=True, label_visibility="collapsed")

    # Historique
    st.markdown("### 📜 Historique")
    if devis_data.get('historique'):
        for hist in devis_data['historique']:
            date_validation = hist.get('date_validation')
            st.markdown(f"**{hist.get('type_validation', 'N/A')}** - {date_validation[:16] if date_validation else 'N/A'} par {hist.get('employee_nom', 'Système')}")
            if hist.get('commentaires'):
                st.caption(hist['commentaires'])
            st.markdown("---")
    else:
        st.info("Aucun historique disponible.")

    # Actions MODIFIÉES avec suppression + export HTML
    st.markdown("### 🔧 Actions")
    
    # Déterminer si le devis peut être supprimé
    statuts_non_supprimables = ['APPROUVÉ', 'TERMINÉ']
    peut_supprimer = devis_data.get('statut') not in statuts_non_supprimables
    
    responsable_id = devis_data.get('employee_id', 1)

    if peut_supprimer:
        # 6 colonnes si suppression possible
        col_action1, col_action2, col_action3, col_action4, col_action5, col_action6 = st.columns(6)
    else:
        # 5 colonnes si pas de suppression
        col_action1, col_action2, col_action3, col_action4, col_action5 = st.columns(5)

    with col_action1:
        if st.button("✅ Accepter", key="accepter_devis"):
            if crm_manager.changer_statut_devis(devis_data['id'], 'APPROUVÉ', responsable_id, "Approuvé via interface"):
                st.success("Devis approuvé !")
                st.rerun()
    
    with col_action2:
        if st.button("❌ Refuser", key="refuser_devis"):
            if crm_manager.changer_statut_devis(devis_data['id'], 'ANNULÉ', responsable_id, "Refusé/Annulé via interface"):
                st.success("Devis annulé.")
                st.rerun()
    
    with col_action3:
        if st.button("📧 Envoyer", key="envoyer_devis"):
            if crm_manager.changer_statut_devis(devis_data['id'], 'ENVOYÉ', responsable_id, "Envoyé via interface"):
                st.success("Devis marqué comme envoyé!")
                st.rerun()
    
    with col_action4:
        if st.button("📄 Dupliquer", key="dupliquer_devis"):
            nouveau_id = crm_manager.dupliquer_devis(devis_data['id'], responsable_id)
            if nouveau_id:
                st.success(f"Devis dupliqué! Nouveau ID: {nouveau_id}")
                st.rerun()

    with col_action5:
        if st.button("📑 Export HTML", key="export_html_devis_details"):
            html_content = crm_manager.export_devis_html(devis_data['id'])
            if html_content:
                # Afficher un lien de téléchargement
                st.download_button(
                    label="💾 Télécharger le devis HTML",
                    data=html_content,
                    file_name=f"devis_{devis_data.get('numero_document')}.html",
                    mime="text/html",
                    key="download_html_devis_details"
                )
                st.success("✅ Devis HTML généré avec succès !")
            else:
                st.error("❌ Erreur lors de l'export HTML.")

    # Bouton de suppression (si possible)
    if peut_supprimer:
        with col_action6:
            if st.button("🗑️ Supprimer", key="supprimer_devis_btn", type="secondary"):
                st.session_state.crm_confirm_delete_devis_id = devis_data['id']
                st.rerun()

    # Gestion de la confirmation de suppression
    if 'crm_confirm_delete_devis_id' in st.session_state and st.session_state.crm_confirm_delete_devis_id == devis_data['id']:
        st.markdown("---")
        st.error(f"⚠️ **ATTENTION : Suppression définitive du devis {devis_data.get('numero_document')}**")
        st.warning("Cette action est irréversible. Le devis et toutes ses données seront définitivement supprimés de la base de données.")
        
        # Champ pour le motif de suppression
        motif_suppression = st.text_input(
            "Motif de suppression (optionnel):", 
            placeholder="Ex: Erreur de saisie, doublon, demande client...",
            key="motif_suppression_devis"
        )
        
        col_confirm, col_cancel = st.columns(2)
        
        with col_confirm:
            if st.button("🗑️ CONFIRMER LA SUPPRESSION", key="confirm_delete_devis", type="primary"):
                if crm_manager.supprimer_devis(devis_data['id'], responsable_id, motif_suppression):
                    # Suppression réussie, nettoyer la session et retourner à la liste
                    del st.session_state.crm_confirm_delete_devis_id
                    st.session_state.crm_action = None
                    st.session_state.crm_selected_id = None
                    st.rerun()
                else:
                    # En cas d'erreur, rester sur la page
                    del st.session_state.crm_confirm_delete_devis_id
        
        with col_cancel:
            if st.button("❌ Annuler la suppression", key="cancel_delete_devis"):
                del st.session_state.crm_confirm_delete_devis_id
                st.rerun()

    if st.button("Retour à la liste des devis", key="back_to_devis_list_from_details"):
        st.session_state.crm_action = None
        st.rerun()

def render_crm_devis_edit_form(crm_manager: GestionnaireCRM, devis_data):
    """Formulaire de modification d'un devis existant"""
    if not devis_data:
        st.error("Devis non trouvé pour modification.")
        return

    st.subheader(f"✏️ Modifier le Devis: {devis_data.get('numero_document')}")
    
    # Vérifier que le devis est modifiable
    statuts_non_modifiables = ['APPROUVÉ', 'TERMINÉ', 'ANNULÉ']
    if devis_data.get('statut') in statuts_non_modifiables:
        st.error(f"Ce devis ne peut pas être modifié car il est au statut '{devis_data.get('statut')}'")
        if st.button("Retour aux détails du devis"):
            st.session_state.crm_action = "view_devis_details"
            st.rerun()
        return

    # Initialiser les lignes dans la session si ce n'est pas déjà fait
    if 'edit_devis_lignes' not in st.session_state or st.session_state.get('edit_devis_id') != devis_data['id']:
        st.session_state.edit_devis_lignes = devis_data.get('lignes', [])
        st.session_state.edit_devis_id = devis_data['id']

    # --- PARTIE 1 : GESTION DES LIGNES (COMME DANS LA CRÉATION) ---
    st.markdown("##### Lignes du devis")
    
    # Section pour sélectionner un produit existant
    st.markdown("**Option 1: Ajouter depuis le catalogue produits**")
    with st.container(border=True):
        col_prod1, col_prod2, col_prod3 = st.columns([2, 1, 1])
        
        with col_prod1:
            produits_options = [("", "Sélectionner un produit...")] + [(p['id'], f"{p['code_produit']} - {p['nom']}") for p in crm_manager.produits]
            produit_selectionne_edit = st.selectbox(
                "Produit du catalogue",
                options=[opt[0] for opt in produits_options],
                format_func=lambda x: next((opt[1] for opt in produits_options if opt[0] == x), "Sélectionner un produit..."),
                key="produit_catalogue_select_edit"
            )
        
        with col_prod2:
            quantite_produit_edit = st.number_input("Quantité", min_value=0.01, value=1.0, step=0.1, key="quantite_produit_catalogue_edit", format="%.2f")
        
        with col_prod3:
            st.write("")
            if st.button("➕ Ajouter depuis catalogue", key="add_from_catalog_edit", use_container_width=True):
                if produit_selectionne_edit:
                    produit_data = crm_manager.get_produit_by_id(produit_selectionne_edit)
                    if produit_data:
                        st.session_state.edit_devis_lignes.append({
                            'description': f"{produit_data['code_produit']} - {produit_data['nom']}",
                            'quantite': quantite_produit_edit,
                            'unite': produit_data['unite_vente'],
                            'prix_unitaire': produit_data['prix_unitaire'],
                            'code_article': produit_data['code_produit']
                        })
                        st.success(f"Produit {produit_data['code_produit']} ajouté au devis!")
                        st.rerun()
                else:
                    st.warning("Veuillez sélectionner un produit.")

    st.markdown("**Option 2: Saisie manuelle**")
    # Formulaire pour ajouter/modifier une ligne
    with st.container(border=True):
        col_ligne1, col_ligne2, col_ligne3, col_ligne4, col_ligne5 = st.columns([3, 1, 1, 1, 1])
        with col_ligne1:
            description = st.text_input("Description", key="edit_ligne_description")
        with col_ligne2:
            quantite = st.number_input("Qté", min_value=0.01, value=1.0, step=0.1, key="edit_ligne_quantite", format="%.2f")
        with col_ligne3:
            unite = st.selectbox("Unité", options=UNITES_VENTE, key="edit_ligne_unite")
        with col_ligne4:
            prix_unitaire = st.number_input("Prix U.", min_value=0.0, step=0.01, key="edit_ligne_prix", format="%.2f")
        with col_ligne5:
            st.write("")
            if st.button("➕ Ajouter", key="edit_ajouter_ligne_btn", use_container_width=True):
                if description and quantite > 0:
                    st.session_state.edit_devis_lignes.append({
                        'description': description,
                        'quantite': quantite,
                        'unite': unite,
                        'prix_unitaire': prix_unitaire
                    })
                    st.rerun()
                else:
                    st.warning("La description et la quantité sont requises.")

    # Affichage des lignes avec possibilité de suppression
    if st.session_state.edit_devis_lignes:
        st.markdown("**Lignes actuelles :**")
        total_ht_preview = 0
        with st.container(border=True):
            for i, ligne in enumerate(st.session_state.edit_devis_lignes):
                col_disp, col_del = st.columns([10, 1])
                with col_disp:
                    montant = ligne['quantite'] * ligne['prix_unitaire']
                    total_ht_preview += montant
                    st.write(f"• {ligne['description']} ({ligne['quantite']} {ligne['unite']} x {ligne['prix_unitaire']:.2f} $) = **{montant:.2f} $**")
                with col_del:
                    if st.button("🗑️", key=f"edit_remove_ligne_{i}", help="Supprimer la ligne"):
                        st.session_state.edit_devis_lignes.pop(i)
                        st.rerun()
            st.markdown(f"**Total (HT) : {total_ht_preview:,.2f} $**")
    
    st.markdown("---")

    # --- PARTIE 2 : FORMULAIRE PRINCIPAL ---
    st.markdown("##### Informations générales")

    with st.form("formulaire_modifier_devis"):
        col_base1, col_base2 = st.columns(2)
        
        with col_base1:
            # Client
            clients = crm_manager.entreprises
            client_options = [(c['id'], c['nom']) for c in clients]
            current_client_id = devis_data.get('company_id')
            client_index = next((i for i, (opt_id, _) in enumerate(client_options) if opt_id == current_client_id), 0)
            
            client_id = st.selectbox("Client *", 
                                   options=[opt[0] for opt in client_options],
                                   format_func=lambda x: next((opt[1] for opt in client_options if opt[0] == x), ''),
                                   index=client_index,
                                   key="edit_devis_client")
            
            # Responsable
            if crm_manager.use_sqlite:
                employees = crm_manager.db.execute_query("SELECT id, prenom || ' ' || nom as nom FROM employees WHERE statut = 'ACTIF'")
                emp_options = [(e['id'], e['nom']) for e in employees] if employees else []
                current_emp_id = devis_data.get('employee_id')
                emp_index = next((i for i, (opt_id, _) in enumerate(emp_options) if opt_id == current_emp_id), 0)
                
                responsable_id = st.selectbox("Responsable *", 
                                            options=[opt[0] for opt in emp_options],
                                            format_func=lambda x: next((opt[1] for opt in emp_options if opt[0] == x), ''),
                                            index=emp_index,
                                            key="edit_devis_responsable")
            else:
                responsable_id = devis_data.get('employee_id', 1)

        with col_base2:
            # Date d'échéance
            try:
                current_echeance = datetime.fromisoformat(devis_data.get('date_echeance')).date()
            except:
                current_echeance = datetime.now().date() + timedelta(days=30)
            
            echeance = st.date_input("Date d'échéance *", 
                                   value=current_echeance,
                                   key="edit_devis_echeance")
            
            # Projet lié
            if crm_manager.use_sqlite:
                projets = crm_manager.db.execute_query("SELECT id, nom_projet FROM projects WHERE statut != 'TERMINÉ'")
                projet_options = [("", "Aucun projet")] + [(p['id'], p['nom_projet']) for p in projets] if projets else [("", "Aucun projet")]
                current_projet_id = devis_data.get('project_id', "")
                projet_index = next((i for i, (opt_id, _) in enumerate(projet_options) if opt_id == current_projet_id), 0)
                
                projet_id = st.selectbox("Projet lié", 
                                       options=[opt[0] for opt in projet_options],
                                       format_func=lambda x: next((opt[1] for opt in projet_options if opt[0] == x), 'Aucun projet'),
                                       index=projet_index,
                                       key="edit_devis_projet")
            else:
                projet_id = devis_data.get('project_id')

        # Notes
        notes = st.text_area("Notes ou conditions", 
                           value=devis_data.get('notes', ''),
                           key="edit_devis_notes")

        # Boutons
        col_submit, col_cancel = st.columns(2)
        with col_submit:
            submitted = st.form_submit_button("💾 Sauvegarder les modifications", type="primary", use_container_width=True)
        with col_cancel:
            if st.form_submit_button("❌ Annuler", use_container_width=True):
                # Nettoyer les variables de session
                if 'edit_devis_lignes' in st.session_state:
                    del st.session_state.edit_devis_lignes
                if 'edit_devis_id' in st.session_state:
                    del st.session_state.edit_devis_id
                st.session_state.crm_action = "view_devis_details"
                st.rerun()

        if submitted:
            if not client_id or not responsable_id or not st.session_state.edit_devis_lignes:
                st.error("Veuillez remplir le client, le responsable et ajouter au moins une ligne au devis.")
            else:
                # Valider les données
                errors = validate_devis_data({
                    'client_company_id': client_id,
                    'employee_id': responsable_id,
                    'date_echeance': echeance.strftime('%Y-%m-%d'),
                    'lignes': st.session_state.edit_devis_lignes
                })
                
                if errors:
                    st.error("Erreurs de validation :")
                    for error in errors:
                        st.write(f"• {error}")
                else:
                    # Construire les données de modification
                    modification_data = {
                        'client_company_id': client_id,
                        'employee_id': responsable_id,
                        'project_id': projet_id if projet_id else None,
                        'date_echeance': echeance.strftime('%Y-%m-%d'),
                        'notes': notes,
                        'lignes': st.session_state.edit_devis_lignes
                    }
                    
                    # Effectuer la modification
                    if crm_manager.modifier_devis(devis_data['id'], modification_data):
                        st.success("✅ Devis modifié avec succès !")
                        
                        # Nettoyer les variables de session
                        if 'edit_devis_lignes' in st.session_state:
                            del st.session_state.edit_devis_lignes
                        if 'edit_devis_id' in st.session_state:
                            del st.session_state.edit_devis_id
                        
                        # Retourner aux détails
                        st.session_state.crm_action = "view_devis_details"
                        st.rerun()
                    else:
                        st.error("Erreur lors de la modification du devis.")

# =========================================================================
# FONCTIONS DE GESTION DES ACTIONS CRM + DEVIS + PRODUITS + EXPORT HTML
# =========================================================================

def handle_crm_actions(crm_manager: GestionnaireCRM, projet_manager=None):
    """Gestionnaire centralisé des actions CRM + Devis + Produits + Export HTML"""
    
    action = st.session_state.get('crm_action')
    selected_id = st.session_state.get('crm_selected_id')
    
    # Actions pour les contacts
    if action == "create_contact":
        render_crm_contact_form(crm_manager)
    elif action == "edit_contact" and selected_id:
        contact_data = crm_manager.get_contact_by_id(selected_id)
        render_crm_contact_form(crm_manager, contact_data)
    elif action == "view_contact_details" and selected_id:
        contact_data = crm_manager.get_contact_by_id(selected_id)
        render_crm_contact_details(crm_manager, projet_manager, contact_data)

    # Actions pour les entreprises
    elif action == "create_entreprise":
        render_crm_entreprise_form(crm_manager)
    elif action == "edit_entreprise" and selected_id:
        entreprise_data = crm_manager.get_entreprise_by_id(selected_id)
        render_crm_entreprise_form(crm_manager, entreprise_data)
    elif action == "view_entreprise_details" and selected_id:
        entreprise_data = crm_manager.get_entreprise_by_id(selected_id)
        render_crm_entreprise_details(crm_manager, projet_manager, entreprise_data)

    # Actions pour les interactions
    elif action == "create_interaction":
        render_crm_interaction_form(crm_manager)
    elif action == "edit_interaction" and selected_id:
        interaction_data = crm_manager.get_interaction_by_id(selected_id)
        render_crm_interaction_form(crm_manager, interaction_data)
    elif action == "view_interaction_details" and selected_id:
        interaction_data = crm_manager.get_interaction_by_id(selected_id)
        render_crm_interaction_details(crm_manager, projet_manager, interaction_data)

    # Actions pour les produits
    elif action == "create_product":
        render_crm_product_form(crm_manager)
    elif action == "edit_product" and selected_id:
        product_data = crm_manager.get_produit_by_id(selected_id)
        render_crm_product_form(crm_manager, product_data)
    elif action == "view_product_details" and selected_id:
        product_data = crm_manager.get_produit_by_id(selected_id)
        render_crm_product_details(crm_manager, product_data)
    elif action == "adjust_stock" and selected_id:
        product_data = crm_manager.get_produit_by_id(selected_id)
        render_crm_stock_adjustment(crm_manager, product_data)

    # Actions pour les devis (AVEC SUPPRESSION + EXPORT HTML)
    elif action == "view_devis_details" and selected_id:
        devis_data = crm_manager.get_devis_complet(selected_id)
        render_crm_devis_details(crm_manager, devis_data)
    elif action == "edit_devis" and selected_id:
        devis_data = crm_manager.get_devis_complet(selected_id)
        render_crm_devis_edit_form(crm_manager, devis_data)

def render_crm_main_interface(crm_manager: GestionnaireCRM, projet_manager=None):
    """Interface principale CRM avec support des devis, produits, suppression et export HTML"""
    
    st.title("📋 Gestion CRM")
    
    # Vérification du mode
    if crm_manager.use_sqlite:
        st.success("✅ Mode SQLite actif - Toutes les fonctionnalités disponibles")
        
        # Bouton de diagnostic (en développement)
        if st.checkbox("🔍 Afficher diagnostic base de données"):
            debug_info = crm_manager.debug_database_structure()
            st.json(debug_info)
    else:
        st.warning("⚠️ Mode JSON (rétrocompatibilité) - Fonctionnalités devis limitées")
    
    # Menu principal avec produits et devis
    if crm_manager.use_sqlite:
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 Contacts", "🏢 Entreprises", "💬 Interactions", "🔧 Produits", "🧾 Devis"])
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["👤 Contacts", "🏢 Entreprises", "💬 Interactions", "🔧 Produits"])
    
    with tab1:
        render_crm_contacts_tab(crm_manager, projet_manager)
    
    with tab2:
        render_crm_entreprises_tab(crm_manager, projet_manager)
    
    with tab3:
        render_crm_interactions_tab(crm_manager)
    
    with tab4:
        render_crm_produits_tab(crm_manager)
    
    if crm_manager.use_sqlite:
        with tab5:
            render_crm_devis_tab(crm_manager)
    
    # Gestionnaire d'actions pour les formulaires et vues détaillées (qui apparaissent en dehors des onglets)
    handle_crm_actions(crm_manager, projet_manager)

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
            'total_devis': 0,
            'montant_devis': 0.0,
            'taux_acceptation_devis': 0.0,
            'valeur_stock': 0.0,
            'produits_stock_bas': 0
        }
        
        # Statistiques produits
        stats_produits = crm_manager.get_statistics_produits()
        stats['valeur_stock'] = stats_produits.get('valeur_stock_total', 0.0)
        stats['produits_stock_bas'] = stats_produits.get('produits_stock_bas', 0)
        
        # Statistiques devis si disponibles
        if crm_manager.use_sqlite:
            devis_stats = crm_manager.get_devis_statistics()
            stats['total_devis'] = devis_stats.get('total_devis', 0)
            stats['montant_devis'] = devis_stats.get('montant_total', 0.0)
            stats['taux_acceptation_devis'] = devis_stats.get('taux_acceptation', 0.0)
        
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
        
        # En production, utiliser pandas.ExcelWriter pour créer un fichier multi-onglets
        # writer = pd.ExcelWriter('export_crm.xlsx', engine='xlsxwriter')
        # contacts_df.to_excel(writer, sheet_name='Contacts', index=False)
        # entreprises_df.to_excel(writer, sheet_name='Entreprises', index=False)
        # interactions_df.to_excel(writer, sheet_name='Interactions', index=False)
        # produits_df.to_excel(writer, sheet_name='Produits', index=False)
        # writer.close()
        
        return {
            'contacts': contacts_df,
            'entreprises': entreprises_df, 
            'interactions': interactions_df,
            'produits': produits_df
        }
    except Exception as e:
        st.error(f"Erreur export Excel: {e}")
        return None

def validate_devis_data(devis_data):
    """Valide les données d'un devis avant création/modification"""
    errors = []
    
    if not devis_data.get('client_company_id'):
        errors.append("Client obligatoire")
    
    if not devis_data.get('employee_id'):
        errors.append("Responsable obligatoire")
    
    if not devis_data.get('date_echeance'):
        errors.append("Date d'échéance obligatoire")
    
    if not devis_data.get('lignes') or len(devis_data['lignes']) == 0:
        errors.append("Au moins une ligne obligatoire")
    
    # Validation des lignes
    for i, ligne in enumerate(devis_data.get('lignes', [])):
        if not ligne.get('description'):
            errors.append(f"Description ligne {i+1} obligatoire")
        if ligne.get('quantite', 0) <= 0:
            errors.append(f"Quantité ligne {i+1} doit être > 0")
        if ligne.get('prix_unitaire', 0) <= 0:
            errors.append(f"Prix unitaire ligne {i+1} doit être > 0")
    
    return errors

def format_currency(amount, currency="CAD"):
    """Formate un montant en devise"""
    try:
        if currency == "CAD":
            return f"{amount:,.2f} $ CAD"
        else:
            return f"{amount:,.2f} {currency}"
    except:
        return "0,00 $"

def calculate_devis_expiration_days(date_echeance):
    """Calcule le nombre de jours avant expiration d'un devis"""
    try:
        if isinstance(date_echeance, str):
            echeance = datetime.fromisoformat(date_echeance).date()
        else:
            echeance = date_echeance
        
        today = datetime.now().date()
        delta = (echeance - today).days
        
        return delta
    except:
        return 0

# =========================================================================
# POINTS D'ENTRÉE PRINCIPAUX
# =========================================================================

def main_crm_interface(db_instance=None, project_manager_instance=None):
    """Point d'entrée principal pour l'interface CRM complète"""
    
    # Initialiser le gestionnaire CRM
    # Le project_manager est nécessaire pour la transformation de devis en projet
    crm_manager = GestionnaireCRM(db=db_instance, project_manager=project_manager_instance)
    
    # Afficher l'interface principale
    render_crm_main_interface(crm_manager, project_manager_instance)
    
    return crm_manager

def demo_crm_with_products_and_devis():
    """Démonstration du système CRM avec produits et devis"""
    
    st.title("🎯 Démonstration CRM + Produits + Devis + Export HTML")
    
    # Note: En production, vous initialiseriez avec votre instance ERPDatabase réelle
    # from erp_database import ERPDatabase
    # from projects import GestionnaireProjetSQL
    # db = ERPDatabase()
    # project_manager = GestionnaireProjetSQL(db=db)
    # crm_manager = GestionnaireCRM(db=db, project_manager=project_manager)
    
    # Pour la démo, utilisation du mode JSON (sans devis)
    crm_manager = GestionnaireCRM()
    
    st.info("💡 Cette démonstration utilise le mode JSON. Pour les devis et l'export HTML, il faut un environnement SQLite avec ERPDatabase et GestionnaireProjetSQL.")
    
    # Afficher les statistiques
    stats = get_crm_statistics_summary(crm_manager)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Contacts", stats['total_contacts'])
    with col2:
        st.metric("Entreprises", stats['total_entreprises'])  
    with col3:
        st.metric("Interactions", stats['total_interactions'])
    with col4:
        st.metric("Produits", stats['total_produits'])
    with col5:
        st.metric("Devis", stats['total_devis'])
    
    # Interface simplifiée (sans project_manager)
    render_crm_main_interface(crm_manager, None)

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

def test_devis_html_export():
    """Test de l'export HTML des devis"""
    
    # Ce test nécessite un environnement SQLite complet
    # En production, créer un devis de test et vérifier l'export HTML
    
    print("💡 Test export HTML : nécessite un environnement SQLite complet")

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
        crm_manager = GestionnaireCRM(db=db, project_manager=project_manager)

        # Afficher l'interface complète
        render_crm_main_interface(crm_manager, project_manager)
        
    except ImportError:
        # Si les autres modules ne sont pas trouvés, lancer la démo en mode JSON
        st.warning("Modules 'erp_database' ou 'projects' non trouvés. Lancement en mode démo JSON.")
        demo_crm_with_products_and_devis()
    except Exception as e:
        st.error(f"Une erreur est survenue lors de l'initialisation: {e}")
        st.info("Lancement en mode démo JSON de secours.")
        demo_crm_with_products_and_devis()
