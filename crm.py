import json
import os
from datetime import datetime, timedelta, date
import pandas as pd
import streamlit as st
from typing import Dict, List, Optional, Any

# --- Constantes ---
TYPES_INTERACTION = ["Email", "Appel", "Réunion", "Note", "Autre"]
STATUTS_OPPORTUNITE = ["Prospection", "Qualification", "Proposition", "Négociation", "Gagné", "Perdu"]
TYPES_ACTIVITE = ["Email", "Appel", "Réunion", "Tâche", "Note", "Visite", "Présentation", "Suivi"]
PRIORITES_ACTIVITE = ["Basse", "Normale", "Haute", "Critique"]
STATUTS_ACTIVITE = ["Planifié", "En cours", "Terminé", "Annulé", "Reporté"]

# Couleurs pour le Kanban
COULEURS_STATUTS = {
    "Prospection": "#9CA3AF",
    "Qualification": "#3B82F6", 
    "Proposition": "#F59E0B",
    "Négociation": "#8B5CF6",
    "Gagné": "#10B981",
    "Perdu": "#EF4444"
}

class GestionnaireCRM:
    """
    Gestionnaire CRM utilisant SQLite au lieu de JSON
    Compatible avec ERPDatabase pour une architecture unifiée
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
            self.next_contact_id = 1
            self.next_entreprise_id = 1
            self.next_interaction_id = 1
            self.charger_donnees_crm()
        else:
            # Mode SQLite unifié
            self._init_demo_data_if_empty()
    
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

    def debug_database_structure(self):
        """Fonction de diagnostic pour vérifier la structure de la base de données"""
        if not self.use_sqlite:
            return "Mode JSON - pas de structure SQLite à vérifier"
        
        try:
            # Informations sur la table companies
            columns_info = self.db.execute_query("PRAGMA table_info(companies)")
            
            debug_info = {
                'colonnes_companies': [{'nom': col['name'], 'type': col['type']} for col in columns_info],
                'nombre_entreprises': len(self.get_all_companies()),
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
        """Propriété pour maintenir compatibilité avec l'interface existante et appeler la fonction optimisée."""
        if self.use_sqlite:
            # Appelle notre nouvelle fonction optimisée et mise en cache
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

# Dans crm.py, à l'intérieur de la classe GestionnaireCRM
    @st.cache_data(ttl=300) # Mise en cache pour 5 minutes
    def get_all_companies(_self):
        """Récupère toutes les entreprises avec contact principal et projets liés en une seule requête."""
        if not _self.use_sqlite:
            return getattr(_self, '_entreprises', [])
        try:
            # === REQUÊTE SQL OPTIMISÉE POUR LES ENTREPRISES ===
            # LEFT JOIN pour le nom du contact principal
            # Sous-requête avec GROUP_CONCAT pour les projets liés
            query = """
                SELECT 
                    c.*, 
                    co.prenom || ' ' || co.nom_famille as contact_principal_nom,
                    (SELECT GROUP_CONCAT(p.nom_projet, '; ') 
                     FROM projects p 
                     WHERE p.client_company_id = c.id) as projets_lies
                FROM companies c
                LEFT JOIN contacts co ON c.contact_principal_id = co.id
                ORDER BY c.nom
            """
            rows = _self.db.execute_query(query)
            
            companies = []
            for row in rows:
                company = dict(row)
                # On conserve le formatage d'adresse
                company['adresse_complete'] = _self.format_adresse_complete(company)
                companies.append(company)
            return companies
        except Exception as e:
            st.error(f"Erreur récupération optimisée des entreprises: {e}")
            return []

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

    @st.cache_data(ttl=300)
    def get_all_contacts(_self):
        """
        Récupère tous les contacts avec leurs projets liés directement en SQL.
        VERSION CORRIGÉE pour correspondre au schéma de la base de données.
        """
        if not _self.use_sqlite:
            return getattr(_self, '_contacts', [])
        
        try:
            # === REQUÊTE SQL DÉFINITIVE ===
            # La sous-requête ne se base plus que sur client_company_id, qui existe bien.
            query = '''
                SELECT 
                    c.*, 
                    co.nom as company_nom,
                    (SELECT GROUP_CONCAT(p.nom_projet, '; ') 
                     FROM projects p 
                     WHERE p.client_company_id = c.company_id) as projets_lies
                FROM contacts c
                LEFT JOIN companies co ON c.company_id = co.id
                ORDER BY c.nom_famille, c.prenom
            '''
            rows = _self.db.execute_query(query)
            
            contacts = []
            for row in rows:
                contact = dict(row)
                # Mapping pour compatibilité
                contact['entreprise_id'] = contact['company_id']
                contact['role'] = contact['role_poste']
                contacts.append(contact)
            
            return contacts
        except Exception as e:
            st.error(f"Erreur récupération optimisée des contacts: {e}")
            # En cas d'erreur, affichez-la pour faciliter le débogage.
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
                    
                    self.next_contact_id = self._get_next_id(self._contacts)
                    self.next_entreprise_id = self._get_next_id(self._entreprises)
                    self.next_interaction_id = self._get_next_id(self._interactions)
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
        """Initialise des données de démonstration JSON avec adresses structurées"""
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
        
        self.next_contact_id = self._get_next_id(self._contacts)
        self.next_entreprise_id = self._get_next_id(self._entreprises)
        self.next_interaction_id = self._get_next_id(self._interactions)
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
                'next_contact_id': self.next_contact_id,
                'next_entreprise_id': self.next_entreprise_id,
                'next_interaction_id': self.next_interaction_id,
                'last_update': datetime.now().isoformat()
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur critique lors de la sauvegarde des données CRM: {e}")

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
    
    # --- Méthodes pour le Pipeline de Vente ---
    
    def get_opportunities(self, filters=None):
        """Récupère toutes les opportunités avec filtres optionnels"""
        if not self.use_sqlite:
            return []
        
        try:
            return self.db.get_opportunities(filters)
        except Exception as e:
            st.error(f"Erreur récupération opportunités: {e}")
            return []
    
    def create_opportunity(self, data):
        """Crée une nouvelle opportunité"""
        if not self.use_sqlite:
            return None
        
        try:
            return self.db.create_opportunity(data)
        except Exception as e:
            st.error(f"Erreur création opportunité: {e}")
            return None
    
    def update_opportunity(self, opp_id, data):
        """Met à jour une opportunité"""
        if not self.use_sqlite:
            return False
        
        try:
            return self.db.update_opportunity(opp_id, data)
        except Exception as e:
            st.error(f"Erreur mise à jour opportunité: {e}")
            return False
    
    def get_opportunity_by_id(self, opp_id):
        """Récupère une opportunité par son ID"""
        if not self.use_sqlite:
            return None
        
        try:
            opportunities = self.db.get_opportunities({'id': opp_id})
            return opportunities[0] if opportunities else None
        except Exception as e:
            st.error(f"Erreur récupération opportunité: {e}")
            return None
    
    def get_pipeline_stats(self):
        """Récupère les statistiques du pipeline"""
        if not self.use_sqlite:
            return {}
        
        try:
            return self.db.get_opportunity_pipeline_stats()
        except Exception as e:
            st.error(f"Erreur récupération stats pipeline: {e}")
            return {}
    
    # --- Méthodes pour les Activités CRM ---
    
    def get_crm_activities(self, filters=None):
        """Récupère toutes les activités CRM avec filtres optionnels"""
        if not self.use_sqlite:
            return []
        
        try:
            return self.db.get_crm_activities(filters)
        except Exception as e:
            st.error(f"Erreur récupération activités: {e}")
            return []
    
    def create_crm_activity(self, data):
        """Crée une nouvelle activité CRM"""
        if not self.use_sqlite:
            return None
        
        try:
            return self.db.create_crm_activity(data)
        except Exception as e:
            st.error(f"Erreur création activité: {e}")
            return None
    
    def update_crm_activity(self, activity_id, data):
        """Met à jour une activité CRM"""
        if not self.use_sqlite:
            return False
        
        try:
            # Construire la requête de mise à jour
            fields = []
            values = []
            
            for field in ['statut', 'description', 'date_activite', 'duree_minutes']:
                if field in data:
                    fields.append(f"{field} = ?")
                    values.append(data[field])
            
            if not fields:
                return True
            
            values.append(activity_id)
            query = f"UPDATE crm_activities SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            
            affected = self.db.execute_update(query, values)
            return affected > 0
            
        except Exception as e:
            st.error(f"Erreur mise à jour activité: {e}")
            return False
    
    def get_activity_by_id(self, activity_id):
        """Récupère une activité par son ID"""
        if not self.use_sqlite:
            return None
        
        try:
            activities = self.db.get_crm_activities({'id': activity_id})
            return activities[0] if activities else None
        except Exception as e:
            st.error(f"Erreur récupération activité: {e}")
            return None

# --- Fonctions d'affichage Streamlit avec adresses structurées ---


def render_crm_contacts_tab(crm_manager: GestionnaireCRM, projet_manager):
    """Affiche l'onglet des contacts de manière optimisée."""
    
    st.subheader("👤 Liste des Contacts")

    col_create_contact, col_search_contact = st.columns([1, 2])
    with col_create_contact:
        if st.button("➕ Nouveau Contact", key="crm_create_contact_btn", use_container_width=True):
            st.session_state.crm_action = "create_contact"
            st.session_state.crm_selected_id = None

    with col_search_contact:
        search_contact_term = st.text_input("Rechercher un contact...", key="crm_contact_search")

    # La fonction get_all_contacts est maintenant mise en cache et optimisée
    filtered_contacts = crm_manager.contacts
    if search_contact_term:
        term = search_contact_term.lower()
        filtered_contacts = [
            c for c in filtered_contacts if
            term in c.get('prenom', '').lower() or
            term in c.get('nom_famille', '').lower() or
            term in c.get('email', '').lower() or
            (c.get('company_nom') and term in c.get('company_nom','').lower())
        ]

    if filtered_contacts:
        contacts_data_display = []
        # La boucle est maintenant très rapide car il n'y a plus de calculs complexes à l'intérieur.
        for contact in filtered_contacts:
            nom_entreprise = contact.get('company_nom', "N/A")
            
            # === MODIFICATION CLÉ ===
            # On récupère directement la chaîne de caractères pré-calculée par la requête SQL.
            # Plus besoin de la boucle "for p in projet_manager.projets" qui était la cause de la lenteur.
            projets_lies_str = contact.get('projets_lies')
            
            contacts_data_display.append({
                "ID": contact.get('id'),
                "Prénom": contact.get('prenom'),
                "Nom": contact.get('nom_famille'),
                "Email": contact.get('email'),
                "Téléphone": contact.get('telephone'),
                "Entreprise": nom_entreprise,
                "Rôle": contact.get('role') or contact.get('role_poste'),
                "Projets Liés": projets_lies_str if projets_lies_str else "-" # Utilisation de la nouvelle donnée
            })
            
        st.dataframe(pd.DataFrame(contacts_data_display), use_container_width=True)

        # La suite de la fonction (actions sur un contact) reste inchangée
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

    # La gestion de la confirmation de suppression reste également inchangée
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
    """Affiche l'onglet des entreprises de manière optimisée."""
    
    st.subheader("🏢 Liste des Entreprises (SQLite)")

    col_create_entreprise, col_search_entreprise = st.columns([1, 2])
    with col_create_entreprise:
        if st.button("➕ Nouvelle Entreprise", key="crm_create_entreprise_btn", use_container_width=True):
            st.session_state.crm_action = "create_entreprise"
            st.session_state.crm_selected_id = None

    with col_search_entreprise:
        search_entreprise_term = st.text_input("Rechercher une entreprise...", key="crm_entreprise_search")

    # crm_manager.entreprises appelle maintenant notre fonction optimisée et mise en cache
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
        # La boucle est maintenant très rapide !
        for entreprise_item in filtered_entreprises:
            # === MODIFICATION CLÉ ===
            # Plus besoin de chercher le contact et les projets, ils sont déjà là !
            nom_contact_principal = entreprise_item.get('contact_principal_nom', "N/A")
            projets_lies_str = entreprise_item.get('projets_lies')

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
                "Projets Liés": projets_lies_str if projets_lies_str else "-"
            })
            
        st.dataframe(pd.DataFrame(entreprises_data_display), use_container_width=True)

        # La suite de la fonction (actions sur une entreprise) reste inchangée
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

    # La gestion de la confirmation de suppression reste également inchangée
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
# FONCTIONS DE GESTION DES ACTIONS CRM
# =========================================================================

def render_crm_opportunity_form(crm_manager: GestionnaireCRM, opportunity=None):
    """Formulaire pour créer ou modifier une opportunité"""
    
    st.subheader("💼 " + ("Modifier l'Opportunité" if opportunity else "Nouvelle Opportunité"))
    
    with st.form("opportunity_form"):
        # Nom de l'opportunité
        nom = st.text_input("Nom de l'opportunité *", 
                           value=opportunity.get('nom', '') if opportunity else '')
        
        # Sélection de l'entreprise et du contact
        col1, col2 = st.columns(2)
        
        with col1:
            companies = crm_manager.entreprises
            company_options = {c['id']: c['nom'] for c in companies}
            company_id = st.selectbox(
                "Entreprise",
                options=[None] + list(company_options.keys()),
                format_func=lambda x: "Sélectionner..." if x is None else company_options[x],
                index=0 if not opportunity else (
                    list(company_options.keys()).index(opportunity['company_id']) + 1 
                    if opportunity.get('company_id') in company_options else 0
                )
            )
        
        with col2:
            contacts = crm_manager.contacts
            contact_options = {c['id']: f"{c['prenom']} {c['nom_famille']}" for c in contacts}
            contact_id = st.selectbox(
                "Contact",
                options=[None] + list(contact_options.keys()),
                format_func=lambda x: "Sélectionner..." if x is None else contact_options[x],
                index=0 if not opportunity else (
                    list(contact_options.keys()).index(opportunity['contact_id']) + 1 
                    if opportunity.get('contact_id') in contact_options else 0
                )
            )
        
        # Montant et probabilité
        col1, col2, col3 = st.columns(3)
        
        with col1:
            montant = st.number_input("Montant estimé ($)", 
                                     min_value=0.0,
                                     value=float(opportunity.get('montant_estime', 0)) if opportunity else 0.0,
                                     step=100.0)
        
        with col2:
            probabilite = st.slider("Probabilité (%)", 
                                   min_value=0, 
                                   max_value=100,
                                   value=opportunity.get('probabilite', 50) if opportunity else 50,
                                   step=10)
        
        with col3:
            statut = st.selectbox("Statut",
                                 options=STATUTS_OPPORTUNITE,
                                 index=STATUTS_OPPORTUNITE.index(opportunity['statut']) if opportunity else 0)
        
        # Dates et source
        col1, col2 = st.columns(2)
        
        with col1:
            date_cloture = st.date_input("Date de clôture prévue",
                                        value=datetime.fromisoformat(opportunity['date_cloture_prevue']).date() 
                                        if opportunity and opportunity.get('date_cloture_prevue') else None)
        
        with col2:
            source = st.text_input("Source",
                                  value=opportunity.get('source', '') if opportunity else '')
        
        # Notes
        notes = st.text_area("Notes",
                            value=opportunity.get('notes', '') if opportunity else '')
        
        # Assignation
        if crm_manager.use_sqlite and crm_manager.db:
            employees = crm_manager.db.execute_query("SELECT id, prenom, nom FROM employees WHERE statut = 'ACTIF'")
            employee_options = {e['id']: f"{e['prenom']} {e['nom']}" for e in employees}
            assigned_to = st.selectbox(
                "Assigné à",
                options=[None] + list(employee_options.keys()),
                format_func=lambda x: "Non assigné" if x is None else employee_options[x],
                index=0 if not opportunity else (
                    list(employee_options.keys()).index(opportunity['assigned_to']) + 1 
                    if opportunity and opportunity.get('assigned_to') in employee_options else 0
                )
            )
        else:
            assigned_to = None
        
        # Boutons d'action
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button(
                "💾 Enregistrer", 
                type="primary",
                use_container_width=True
            )
        
        with col2:
            if st.form_submit_button("❌ Annuler", use_container_width=True):
                st.session_state.crm_action = None
                st.session_state.crm_selected_id = None
                st.rerun()
        
        if submitted:
            if not nom:
                st.error("Le nom de l'opportunité est obligatoire")
            else:
                data = {
                    'nom': nom,
                    'company_id': company_id,
                    'contact_id': contact_id,
                    'montant_estime': montant,
                    'probabilite': probabilite,
                    'statut': statut,
                    'date_cloture_prevue': date_cloture.isoformat() if date_cloture else None,
                    'source': source,
                    'notes': notes,
                    'assigned_to': assigned_to
                }
                
                if opportunity:
                    # Mise à jour
                    if crm_manager.update_opportunity(opportunity['id'], data):
                        st.success("✅ Opportunité mise à jour avec succès")
                        st.session_state.crm_action = None
                        st.session_state.crm_selected_id = None
                        st.rerun()
                else:
                    # Création
                    data['created_by'] = assigned_to  # Pour simplifier, créateur = assigné
                    opp_id = crm_manager.create_opportunity(data)
                    if opp_id:
                        st.success("✅ Opportunité créée avec succès")
                        st.session_state.crm_action = None
                        st.rerun()


def render_crm_activity_form(crm_manager: GestionnaireCRM, activity=None):
    """Formulaire pour créer ou modifier une activité CRM"""
    
    st.subheader("📅 " + ("Modifier l'Activité" if activity else "Nouvelle Activité"))
    
    with st.form("activity_form"):
        # Type d'activité et sujet
        col1, col2 = st.columns([1, 2])
        
        with col1:
            type_activite = st.selectbox("Type d'activité *",
                                        options=TYPES_ACTIVITE,
                                        index=TYPES_ACTIVITE.index(activity['type_activite']) 
                                        if activity else 0)
        
        with col2:
            sujet = st.text_input("Sujet *",
                                 value=activity.get('sujet', '') if activity else '')
        
        # Date et heure
        col1, col2, col3 = st.columns(3)
        
        with col1:
            date_activite = st.date_input("Date",
                                         value=datetime.fromisoformat(activity['date_activite']).date() 
                                         if activity and activity.get('date_activite') else date.today())
        
        with col2:
            heure_activite = st.time_input("Heure",
                                          value=datetime.fromisoformat(activity['date_activite']).time() 
                                          if activity and activity.get('date_activite') else datetime.now().time())
        
        with col3:
            duree = st.number_input("Durée (minutes)",
                                   min_value=15,
                                   value=activity.get('duree_minutes', 30) if activity else 30,
                                   step=15)
        
        # Statut et priorité
        col1, col2 = st.columns(2)
        
        with col1:
            statut = st.selectbox("Statut",
                                 options=STATUTS_ACTIVITE,
                                 index=STATUTS_ACTIVITE.index(activity['statut']) 
                                 if activity else 0)
        
        with col2:
            priorite = st.selectbox("Priorité",
                                   options=PRIORITES_ACTIVITE,
                                   index=PRIORITES_ACTIVITE.index(activity['priorite']) 
                                   if activity else 1)
        
        # Liens avec opportunité, contact et entreprise
        col1, col2, col3 = st.columns(3)
        
        with col1:
            opportunities = crm_manager.get_opportunities({'statut': ['Prospection', 'Qualification', 'Proposition', 'Négociation']})
            opp_options = {o['id']: o['nom'] for o in opportunities}
            opportunity_id = st.selectbox(
                "Opportunité",
                options=[None] + list(opp_options.keys()),
                format_func=lambda x: "Aucune" if x is None else opp_options[x],
                index=0 if not activity else (
                    list(opp_options.keys()).index(activity['opportunity_id']) + 1 
                    if activity and activity.get('opportunity_id') in opp_options else 0
                )
            )
        
        with col2:
            contacts = crm_manager.contacts
            contact_options = {c['id']: f"{c['prenom']} {c['nom_famille']}" for c in contacts}
            contact_id = st.selectbox(
                "Contact",
                options=[None] + list(contact_options.keys()),
                format_func=lambda x: "Aucun" if x is None else contact_options[x],
                index=0 if not activity else (
                    list(contact_options.keys()).index(activity['contact_id']) + 1 
                    if activity and activity.get('contact_id') in contact_options else 0
                )
            )
        
        with col3:
            companies = crm_manager.entreprises
            company_options = {c['id']: c['nom'] for c in companies}
            company_id = st.selectbox(
                "Entreprise",
                options=[None] + list(company_options.keys()),
                format_func=lambda x: "Aucune" if x is None else company_options[x],
                index=0 if not activity else (
                    list(company_options.keys()).index(activity['company_id']) + 1 
                    if activity and activity.get('company_id') in company_options else 0
                )
            )
        
        # Lieu (pour réunions/visites)
        if type_activite in ['Réunion', 'Visite', 'Présentation']:
            lieu = st.text_input("Lieu",
                                value=activity.get('lieu', '') if activity else '')
        else:
            lieu = None
        
        # Description
        description = st.text_area("Description",
                                  value=activity.get('description', '') if activity else '')
        
        # Assignation
        if crm_manager.use_sqlite and crm_manager.db:
            employees = crm_manager.db.execute_query("SELECT id, prenom, nom FROM employees WHERE statut = 'ACTIF'")
            employee_options = {e['id']: f"{e['prenom']} {e['nom']}" for e in employees}
            assigned_to = st.selectbox(
                "Assigné à",
                options=[None] + list(employee_options.keys()),
                format_func=lambda x: "Non assigné" if x is None else employee_options[x],
                index=0 if not activity else (
                    list(employee_options.keys()).index(activity['assigned_to']) + 1 
                    if activity and activity.get('assigned_to') in employee_options else 0
                )
            )
        else:
            assigned_to = None
        
        # Boutons d'action
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button(
                "💾 Enregistrer", 
                type="primary",
                use_container_width=True
            )
        
        with col2:
            if st.form_submit_button("❌ Annuler", use_container_width=True):
                st.session_state.crm_action = None
                st.session_state.crm_selected_id = None
                st.rerun()
        
        if submitted:
            if not sujet:
                st.error("Le sujet est obligatoire")
            else:
                # Combiner date et heure
                datetime_activite = datetime.combine(date_activite, heure_activite)
                
                data = {
                    'type_activite': type_activite,
                    'sujet': sujet,
                    'date_activite': datetime_activite.isoformat(),
                    'duree_minutes': duree,
                    'statut': statut,
                    'priorite': priorite,
                    'opportunity_id': opportunity_id,
                    'contact_id': contact_id,
                    'company_id': company_id,
                    'lieu': lieu,
                    'description': description,
                    'assigned_to': assigned_to
                }
                
                if activity:
                    # Mise à jour
                    if crm_manager.update_crm_activity(activity['id'], data):
                        st.success("✅ Activité mise à jour avec succès")
                        st.session_state.crm_action = None
                        st.session_state.crm_selected_id = None
                        st.rerun()
                else:
                    # Création
                    data['created_by'] = assigned_to  # Pour simplifier
                    activity_id = crm_manager.create_crm_activity(data)
                    if activity_id:
                        st.success("✅ Activité créée avec succès")
                        st.session_state.crm_action = None
                        st.rerun()


def handle_crm_actions(crm_manager: GestionnaireCRM, projet_manager=None):
    """Gestionnaire centralisé des actions CRM."""
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
    
    # Actions pour les opportunités
    elif action == "create_opportunity":
        render_crm_opportunity_form(crm_manager)
    elif action == "edit_opportunity" and selected_id:
        render_crm_opportunity_form(crm_manager, crm_manager.get_opportunity_by_id(selected_id))
    
    # Actions pour les activités
    elif action == "create_activity":
        render_crm_activity_form(crm_manager)
    elif action == "edit_activity" and selected_id:
        render_crm_activity_form(crm_manager, crm_manager.get_activity_by_id(selected_id))

def render_crm_pipeline_tab(crm_manager: GestionnaireCRM):
    """Affiche l'onglet Pipeline avec vue Kanban des opportunités"""
    
    # Statistiques du pipeline
    col1, col2, col3, col4 = st.columns(4)
    stats = crm_manager.get_pipeline_stats()
    
    with col1:
        st.metric("Pipeline Total", f"${stats.get('valeurs', {}).get('pipeline', 0):,.0f}")
    with col2:
        st.metric("Valeur Pondérée", f"${stats.get('valeurs', {}).get('pondere', 0):,.0f}")
    with col3:
        st.metric("Affaires Gagnées", f"${stats.get('valeurs', {}).get('gagne', 0):,.0f}")
    with col4:
        st.metric("Taux de Conversion", f"{stats.get('taux_conversion', 0):.1f}%")
    
    st.markdown("---")
    
    # Bouton pour créer une nouvelle opportunité
    if st.button("➕ Nouvelle Opportunité", key="create_opportunity"):
        st.session_state.crm_action = "create_opportunity"
    
    # Vue Kanban
    st.subheader("Pipeline de Vente")
    
    # Récupérer toutes les opportunités
    opportunities = crm_manager.get_opportunities()
    
    # Créer les colonnes pour le Kanban
    cols = st.columns(len(STATUTS_OPPORTUNITE))
    
    for idx, statut in enumerate(STATUTS_OPPORTUNITE):
        with cols[idx]:
            # En-tête de colonne avec couleur
            color = COULEURS_STATUTS.get(statut, "#9CA3AF")
            st.markdown(f"""
                <div style='background-color: {color}; color: white; padding: 10px; 
                           border-radius: 5px; text-align: center; margin-bottom: 10px;'>
                    <b>{statut}</b>
                </div>
            """, unsafe_allow_html=True)
            
            # Filtrer les opportunités pour ce statut
            statut_opps = [opp for opp in opportunities if opp.get('statut') == statut]
            
            # Afficher les cartes d'opportunités
            for opp in statut_opps:
                with st.container():
                    st.markdown(f"""
                        <div style='border: 1px solid #E5E7EB; border-radius: 8px; 
                                   padding: 12px; margin-bottom: 8px; background-color: white;
                                   box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
                            <div style='font-weight: bold; margin-bottom: 4px;'>{opp.get('nom')}</div>
                            <div style='color: #6B7280; font-size: 14px;'>{opp.get('company_name', 'N/A')}</div>
                            <div style='margin-top: 8px; display: flex; justify-content: space-between;'>
                                <span style='font-weight: bold; color: #10B981;'>
                                    ${opp.get('montant_estime', 0):,.0f}
                                </span>
                                <span style='color: #9CA3AF; font-size: 12px;'>
                                    {opp.get('probabilite', 0)}%
                                </span>
                            </div>
                            <div style='margin-top: 4px; color: #9CA3AF; font-size: 12px;'>
                                {opp.get('assigned_to_name', 'Non assigné')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Boutons d'action
                    col_edit, col_next = st.columns(2)
                    with col_edit:
                        if st.button("✏️", key=f"edit_opp_{opp['id']}", help="Modifier"):
                            st.session_state.crm_action = "edit_opportunity"
                            st.session_state.crm_selected_id = opp['id']
                    
                    with col_next:
                        # Bouton pour passer au statut suivant
                        if idx < len(STATUTS_OPPORTUNITE) - 1 and statut not in ['Gagné', 'Perdu']:
                            if st.button("→", key=f"next_opp_{opp['id']}", help="Statut suivant"):
                                next_statut = STATUTS_OPPORTUNITE[idx + 1]
                                crm_manager.update_opportunity(opp['id'], {'statut': next_statut})
                                st.rerun()
            
            # Message si aucune opportunité
            if not statut_opps:
                st.caption("Aucune opportunité")


def render_crm_calendar_tab(crm_manager: GestionnaireCRM):
    """Affiche l'onglet Calendrier avec les activités CRM"""
    import calendar
    from datetime import datetime, date, timedelta
    
    st.subheader("📅 Calendrier des Activités")
    
    # Sélection du mois
    col1, col2, col3 = st.columns([2, 2, 1])
    
    today = date.today()
    with col1:
        selected_month = st.selectbox(
            "Mois",
            range(1, 13),
            index=today.month - 1,
            format_func=lambda x: calendar.month_name[x]
        )
    
    with col2:
        selected_year = st.number_input(
            "Année",
            min_value=2020,
            max_value=2030,
            value=today.year
        )
    
    with col3:
        if st.button("➕ Nouvelle Activité"):
            st.session_state.crm_action = "create_activity"
    
    # Récupérer les activités du mois
    first_day = date(selected_year, selected_month, 1)
    if selected_month == 12:
        last_day = date(selected_year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(selected_year, selected_month + 1, 1) - timedelta(days=1)
    
    activities = crm_manager.get_crm_activities({
        'date_debut': first_day.isoformat(),
        'date_fin': last_day.isoformat()
    })
    
    # Créer un dictionnaire des activités par jour
    activities_by_day = {}
    for activity in activities:
        activity_date = datetime.fromisoformat(activity['date_activite']).date()
        day = activity_date.day
        if day not in activities_by_day:
            activities_by_day[day] = []
        activities_by_day[day].append(activity)
    
    # Afficher le calendrier
    cal = calendar.monthcalendar(selected_year, selected_month)
    days = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
    
    # En-tête des jours
    cols = st.columns(7)
    for idx, day_name in enumerate(days):
        with cols[idx]:
            st.markdown(f"<div style='text-align: center; font-weight: bold;'>{day_name}</div>", 
                       unsafe_allow_html=True)
    
    # Afficher les semaines
    for week in cal:
        cols = st.columns(7)
        for idx, day in enumerate(week):
            with cols[idx]:
                if day == 0:
                    st.write("")
                else:
                    # Conteneur pour le jour
                    day_date = date(selected_year, selected_month, day)
                    is_today = day_date == today
                    
                    # Style du jour
                    day_style = "background-color: #E5F2FF;" if is_today else "background-color: #F9FAFB;"
                    
                    st.markdown(f"""
                        <div style='border: 1px solid #E5E7EB; border-radius: 8px; 
                                   padding: 8px; min-height: 100px; {day_style}'>
                            <div style='font-weight: bold; margin-bottom: 4px;'>{day}</div>
                    """, unsafe_allow_html=True)
                    
                    # Afficher les activités du jour
                    if day in activities_by_day:
                        for activity in activities_by_day[day][:3]:  # Limiter à 3 activités visibles
                            # Couleur selon le type d'activité
                            type_colors = {
                                'Email': '#6B7280',
                                'Appel': '#3B82F6',
                                'Réunion': '#8B5CF6',
                                'Tâche': '#F59E0B',
                                'Note': '#10B981',
                                'Visite': '#EF4444',
                                'Présentation': '#EC4899',
                                'Suivi': '#14B8A6'
                            }
                            color = type_colors.get(activity['type_activite'], '#6B7280')
                            
                            st.markdown(f"""
                                <div style='background-color: {color}; color: white; 
                                           padding: 2px 6px; border-radius: 4px; 
                                           margin-bottom: 2px; font-size: 12px;
                                           white-space: nowrap; overflow: hidden;
                                           text-overflow: ellipsis;'>
                                    {datetime.fromisoformat(activity['date_activite']).strftime('%H:%M')} - 
                                    {activity['sujet']}
                                </div>
                            """, unsafe_allow_html=True)
                        
                        # Indiquer s'il y a plus d'activités
                        if len(activities_by_day[day]) > 3:
                            st.markdown(f"""
                                <div style='font-size: 11px; color: #9CA3AF; text-align: center;'>
                                    +{len(activities_by_day[day]) - 3} autres
                                </div>
                            """, unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
    
    # Liste des activités du jour sélectionné
    st.markdown("---")
    st.subheader("Activités du Jour")
    
    # Sélection du jour
    selected_day = st.date_input(
        "Sélectionner une date",
        value=today,
        min_value=date(2020, 1, 1),
        max_value=date(2030, 12, 31)
    )
    
    # Filtrer les activités pour le jour sélectionné
    day_activities = crm_manager.get_crm_activities({
        'date_debut': selected_day.isoformat(),
        'date_fin': selected_day.isoformat()
    })
    
    if day_activities:
        for activity in day_activities:
            with st.expander(f"{activity['type_activite']} - {activity['sujet']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Heure:** {datetime.fromisoformat(activity['date_activite']).strftime('%H:%M')}")
                    st.write(f"**Durée:** {activity.get('duree_minutes', 30)} minutes")
                    st.write(f"**Statut:** {activity['statut']}")
                    st.write(f"**Priorité:** {activity['priorite']}")
                
                with col2:
                    if activity.get('opportunity_name'):
                        st.write(f"**Opportunité:** {activity['opportunity_name']}")
                    if activity.get('contact_name'):
                        st.write(f"**Contact:** {activity['contact_name']}")
                    if activity.get('company_name'):
                        st.write(f"**Entreprise:** {activity['company_name']}")
                    st.write(f"**Assigné à:** {activity.get('assigned_to_name', 'Non assigné')}")
                
                if activity.get('description'):
                    st.write("**Description:**")
                    st.write(activity['description'])
                
                # Boutons d'action
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("✏️ Modifier", key=f"edit_activity_{activity['id']}"):
                        st.session_state.crm_action = "edit_activity"
                        st.session_state.crm_selected_id = activity['id']
                
                with col2:
                    if activity['statut'] != 'Terminé':
                        if st.button("✅ Terminer", key=f"complete_activity_{activity['id']}"):
                            crm_manager.update_crm_activity(activity['id'], {'statut': 'Terminé'})
                            st.rerun()
                
                with col3:
                    if st.button("🗑️ Supprimer", key=f"delete_activity_{activity['id']}"):
                        crm_manager.db.execute_update(
                            "DELETE FROM crm_activities WHERE id = ?", 
                            (activity['id'],)
                        )
                        st.rerun()
    else:
        st.info("Aucune activité prévue pour ce jour")


def render_crm_main_interface(crm_manager: GestionnaireCRM, projet_manager=None):
    """Interface principale CRM."""
    st.title("📋 Gestion des Ventes")
    
    if crm_manager.use_sqlite:
        st.success("✅ Mode SQLite actif - Données centralisées.")
    else:
        st.warning("⚠️ Mode JSON (rétrocompatibilité).")
    
    # Interface principale avec 5 onglets
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["👤 Contacts", "🏢 Entreprises", "💬 Interactions", "📊 Pipeline", "📅 Calendrier"])
    
    with tab1:
        render_crm_contacts_tab(crm_manager, projet_manager)
    with tab2:
        render_crm_entreprises_tab(crm_manager, projet_manager)
    with tab3:
        render_crm_interactions_tab(crm_manager)
    with tab4:
        render_crm_pipeline_tab(crm_manager)
    with tab5:
        render_crm_calendar_tab(crm_manager)
    
    # Gestionnaire d'actions
    handle_crm_actions(crm_manager, projet_manager)

# =========================================================================
# POINTS D'ENTRÉE PRINCIPAUX
# =========================================================================

def main_crm_interface(db_instance=None, project_manager_instance=None):
    """Point d'entrée principal pour l'interface CRM."""
    
    crm_manager = GestionnaireCRM(db=db_instance)
    
    # Afficher l'interface principale
    render_crm_main_interface(crm_manager, project_manager_instance)
    
    return crm_manager

def demo_crm_contacts():
    """Démonstration du système CRM pour contacts, entreprises et interactions"""
    
    st.title("🎯 Démonstration CRM - Contacts & Entreprises")
    
    # Pour la démo, utilisation du mode JSON
    crm_manager = GestionnaireCRM()
    
    st.info("💡 Cette démonstration utilise le mode JSON. Pour une version complète avec SQLite, il faut un environnement avec ERPDatabase.")
    
    # Afficher les statistiques
    stats = get_crm_statistics_summary(crm_manager)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Contacts", stats['total_contacts'])
    with col2:
        st.metric("Entreprises", stats['total_entreprises'])  
    with col3:
        st.metric("Interactions", stats['total_interactions'])
    
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
        }
        
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
        
        return {
            'contacts': contacts_df,
            'entreprises': entreprises_df, 
            'interactions': interactions_df
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
        demo_crm_contacts()
    except Exception as e:
        st.error(f"Une erreur est survenue lors de l'initialisation: {e}")
        st.info("Lancement en mode démo JSON de secours.")
        demo_crm_contacts()
