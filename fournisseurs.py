# fournisseurs.py - Module Fournisseurs pour ERP Production DG Inc.
# Version nettoyée - Suppression complète de la logique d'activation/désactivation
# + NOUVEAUX FORMULAIRES : Demande de Prix et Bon d'Achat intégrés
# + NETTOYAGE : Suppression complète du système est_actif
# + SIMPLIFICATION : Code Fournisseur automatique + Catégorie optionnelle

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import json
from typing import Dict, List, Optional, Any

class GestionnaireFournisseurs:
    """
    Gestionnaire complet pour les fournisseurs de l'ERP Production DG Inc.
    Intégré avec la base de données SQLite unifiée
    + NOUVEAUX : Formulaires Demande de Prix et Bon d'Achat
    + NETTOYAGE : Suppression complète du système d'activation/désactivation
    + SIMPLIFICATION : Code Fournisseur automatique + Catégorie optionnelle
    """
    
    def __init__(self, db):
        self.db = db
        # Nettoyer la base de données au démarrage si nécessaire
        self._cleanup_database()
    
    def _cleanup_database(self):
        """Nettoie la base de données en supprimant la colonne est_actif si elle existe"""
        try:
            # Vérifier si la colonne existe
            check_query = "PRAGMA table_info(fournisseurs)"
            columns = self.db.execute_query(check_query)
            
            has_est_actif = any(col['name'] == 'est_actif' for col in columns)
            
            if has_est_actif:
                st.info("🔧 Nettoyage de la base de données en cours...")
                
                # Désactiver les contraintes de clé étrangère temporairement
                self.db.execute_update("PRAGMA foreign_keys=OFF")
                
                # Créer une nouvelle table sans la colonne est_actif
                self.db.execute_update("""
                    CREATE TABLE IF NOT EXISTS fournisseurs_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company_id INTEGER NOT NULL,
                        code_fournisseur TEXT UNIQUE,
                        categorie_produits TEXT,
                        delai_livraison_moyen INTEGER DEFAULT 14,
                        conditions_paiement TEXT DEFAULT '30 jours net',
                        evaluation_qualite INTEGER DEFAULT 5,
                        contact_commercial TEXT,
                        contact_technique TEXT,
                        certifications TEXT,
                        notes_evaluation TEXT,
                        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (company_id) REFERENCES companies (id)
                    )
                """)
                
                # Copier les données (sans est_actif)
                self.db.execute_update("""
                    INSERT INTO fournisseurs_new 
                    (id, company_id, code_fournisseur, categorie_produits, delai_livraison_moyen,
                     conditions_paiement, evaluation_qualite, contact_commercial, contact_technique,
                     certifications, notes_evaluation, date_creation, date_modification)
                    SELECT id, company_id, code_fournisseur, categorie_produits, delai_livraison_moyen,
                           conditions_paiement, evaluation_qualite, contact_commercial, contact_technique,
                           certifications, notes_evaluation, 
                           COALESCE(date_creation, created_at, CURRENT_TIMESTAMP),
                           COALESCE(date_modification, created_at, CURRENT_TIMESTAMP)
                    FROM fournisseurs
                """)
                
                # Supprimer l'ancienne table et renommer la nouvelle
                self.db.execute_update("DROP TABLE fournisseurs")
                self.db.execute_update("ALTER TABLE fournisseurs_new RENAME TO fournisseurs")
                
                # Réactiver les contraintes de clé étrangère
                self.db.execute_update("PRAGMA foreign_keys=ON")
                
                st.success("✅ Base de données nettoyée - Colonne est_actif supprimée")
                
        except Exception as e:
            print(f"Info: Nettoyage DB pas nécessaire ou erreur: {e}")
            # Réactiver les contraintes en cas d'erreur
            try:
                self.db.execute_update("PRAGMA foreign_keys=ON")
            except:
                pass
    
    def get_all_fournisseurs(self) -> List[Dict]:
        """Récupère tous les fournisseurs avec leurs statistiques et company_id"""
        try:
            # Requête simplifiée pour éviter les problèmes de GROUP BY
            query = '''
                SELECT f.*, c.nom, c.secteur, c.adresse, c.site_web
                FROM fournisseurs f
                JOIN companies c ON f.company_id = c.id
                ORDER BY c.nom
            '''
            rows = self.db.execute_query(query)
            fournisseurs = [dict(row) for row in rows] if rows else []
            
            # Ajouter les statistiques de commande séparément pour éviter les conflits
            for fournisseur in fournisseurs:
                try:
                    stats_query = '''
                        SELECT 
                            COUNT(form.id) as nombre_commandes,
                            COALESCE(SUM(form.montant_total), 0) as montant_total_commandes
                        FROM formulaires form
                        WHERE form.company_id = ?
                        AND form.type_formulaire IN ('BON_ACHAT', 'BON_COMMANDE')
                    '''
                    stats_result = self.db.execute_query(stats_query, (fournisseur['company_id'],))
                    if stats_result:
                        stats = dict(stats_result[0])
                        fournisseur.update(stats)
                    else:
                        fournisseur['nombre_commandes'] = 0
                        fournisseur['montant_total_commandes'] = 0.0
                except Exception as stats_error:
                    print(f"Erreur stats pour fournisseur {fournisseur.get('id')}: {stats_error}")
                    fournisseur['nombre_commandes'] = 0
                    fournisseur['montant_total_commandes'] = 0.0
            
            return fournisseurs
            
        except Exception as e:
            print(f"Erreur dans get_all_fournisseurs: {e}")
            # Fallback: récupération simple avec company_id garanti
            try:
                fallback_query = '''
                    SELECT f.*, c.nom
                    FROM fournisseurs f
                    JOIN companies c ON f.company_id = c.id
                    ORDER BY c.nom
                '''
                rows = self.db.execute_query(fallback_query)
                return [dict(row) for row in rows] if rows else []
            except Exception as e2:
                st.error(f"Erreur récupération fournisseurs: {e2}")
                return []
    
    def get_fournisseur_by_id(self, fournisseur_id: int) -> Dict:
        """Récupère un fournisseur par ID avec détails complets"""
        try:
            query = '''
                SELECT f.*, c.nom, c.secteur, c.adresse, c.site_web, c.notes as company_notes
                FROM fournisseurs f
                JOIN companies c ON f.company_id = c.id
                WHERE f.id = ?
            '''
            result = self.db.execute_query(query, (fournisseur_id,))
            return dict(result[0]) if result else {}
        except Exception as e:
            st.error(f"Erreur récupération fournisseur: {e}")
            return {}
    
    def get_fournisseurs_by_category(self, category: str = None) -> List[Dict]:
        """Récupère les fournisseurs par catégorie"""
        try:
            if category:
                query = '''
                    SELECT f.*, c.nom, c.secteur
                    FROM fournisseurs f
                    JOIN companies c ON f.company_id = c.id
                    WHERE f.categorie_produits LIKE ?
                    ORDER BY c.nom
                '''
                rows = self.db.execute_query(query, (f"%{category}%",))
            else:
                query = '''
                    SELECT f.*, c.nom, c.secteur
                    FROM fournisseurs f
                    JOIN companies c ON f.company_id = c.id
                    ORDER BY c.nom
                '''
                rows = self.db.execute_query(query)
            
            return [dict(row) for row in rows]
        except Exception as e:
            st.error(f"Erreur récupération par catégorie: {e}")
            return []
    
    def generate_fournisseur_code(self) -> str:
        """Génère un code fournisseur automatique"""
        try:
            annee = datetime.now().year
            
            # Requête pour récupérer le dernier numéro
            query = '''
                SELECT code_fournisseur FROM fournisseurs 
                WHERE code_fournisseur IS NOT NULL 
                AND code_fournisseur LIKE ?
                ORDER BY id DESC 
                LIMIT 10
            '''
            pattern = f"FOUR-{annee}-%"
            
            try:
                result = self.db.execute_query(query, (pattern,))
            except Exception:
                result = []
            
            # Traitement des résultats avec validation
            sequence = 1
            if result:
                for row in result:
                    code = row['code_fournisseur']
                    if code and isinstance(code, str):
                        # Validation du format : FOUR-YYYY-NNN
                        parts = code.split('-')
                        if len(parts) == 3 and parts[0] == 'FOUR' and parts[1] == str(annee):
                            try:
                                current_seq = int(parts[2])
                                if current_seq >= sequence:
                                    sequence = current_seq + 1
                                    break  # Premier résultat valide trouvé
                            except (ValueError, IndexError):
                                continue
            
            # Génération du nouveau code
            nouveau_code = f"FOUR-{annee}-{sequence:03d}"
            
            # Vérification d'unicité (sécurité supplémentaire)
            verification_query = "SELECT COUNT(*) as count FROM fournisseurs WHERE code_fournisseur = ?"
            verification_result = self.db.execute_query(verification_query, (nouveau_code,))
            
            if verification_result and verification_result[0]['count'] > 0:
                # Si le code existe déjà, incrémenter jusqu'à trouver un code libre
                while True:
                    sequence += 1
                    nouveau_code = f"FOUR-{annee}-{sequence:03d}"
                    verification_result = self.db.execute_query(verification_query, (nouveau_code,))
                    if not verification_result or verification_result[0]['count'] == 0:
                        break
                    if sequence > 999:  # Sécurité pour éviter une boucle infinie
                        raise Exception("Impossible de générer un code unique (limite atteinte)")
            
            return nouveau_code
            
        except Exception as e:
            print(f"Erreur dans generate_fournisseur_code: {e}")
            # En cas d'erreur, générer un code basé sur timestamp
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            fallback_code = f"FOUR-{timestamp[-8:]}"
            return fallback_code
    
    def create_fournisseur(self, company_id: int, fournisseur_data: Dict) -> int:
        """Crée un nouveau fournisseur"""
        try:
            return self.db.add_fournisseur(company_id, fournisseur_data)
        except Exception as e:
            st.error(f"Erreur création fournisseur: {e}")
            return None
    
    def update_fournisseur(self, fournisseur_id: int, fournisseur_data: Dict) -> bool:
        """Met à jour un fournisseur existant"""
        try:
            # Construire la requête de mise à jour
            update_fields = []
            params = []
            
            for field in ['code_fournisseur', 'categorie_produits', 'delai_livraison_moyen', 
                         'conditions_paiement', 'evaluation_qualite', 'contact_commercial',
                         'contact_technique', 'certifications', 'notes_evaluation']:
                if field in fournisseur_data:
                    update_fields.append(f"{field} = ?")
                    params.append(fournisseur_data[field])
            
            if update_fields:
                query = f"UPDATE fournisseurs SET {', '.join(update_fields)} WHERE id = ?"
                params.append(fournisseur_id)
                
                affected = self.db.execute_update(query, tuple(params))
                return affected > 0
            
            return False
            
        except Exception as e:
            st.error(f"Erreur mise à jour fournisseur: {e}")
            return False
    
    def delete_fournisseur(self, fournisseur_id: int) -> bool:
        """Supprime définitivement un fournisseur"""
        try:
            query = "DELETE FROM fournisseurs WHERE id = ?"
            affected = self.db.execute_update(query, (fournisseur_id,))
            return affected > 0
        except Exception as e:
            st.error(f"Erreur suppression fournisseur: {e}")
            return False
    
    def get_fournisseur_performance(self, fournisseur_id: int, days: int = 365) -> Dict:
        """Calcule les performances d'un fournisseur"""
        try:
            # Statistiques commandes
            query_commandes = '''
                SELECT 
                    COUNT(*) as total_commandes,
                    SUM(f.montant_total) as montant_total,
                    AVG(f.montant_total) as montant_moyen,
                    MIN(f.date_creation) as premiere_commande,
                    MAX(f.date_creation) as derniere_commande
                FROM formulaires f
                JOIN companies c ON f.company_id = c.id
                JOIN fournisseurs fou ON c.id = fou.company_id
                WHERE fou.id = ? 
                AND f.type_formulaire IN ('BON_ACHAT', 'BON_COMMANDE')
                AND f.date_creation >= DATE('now', '-{} days')
            '''.format(days)
            
            result = self.db.execute_query(query_commandes, (fournisseur_id,))
            performance = dict(result[0]) if result else {}
            
            # Statistiques livraisons
            query_livraisons = '''
                SELECT 
                    COUNT(*) as total_livraisons,
                    COUNT(CASE WHEN a.date_livraison_reelle <= a.date_livraison_prevue THEN 1 END) as livraisons_temps,
                    AVG(JULIANDAY(a.date_livraison_reelle) - JULIANDAY(a.date_livraison_prevue)) as retard_moyen_jours
                FROM approvisionnements a
                JOIN formulaires f ON a.formulaire_id = f.id
                JOIN companies c ON f.company_id = c.id
                JOIN fournisseurs fou ON c.id = fou.company_id
                WHERE fou.id = ? 
                AND a.date_livraison_reelle IS NOT NULL
                AND a.date_commande >= DATE('now', '-{} days')
            '''.format(days)
            
            result_livr = self.db.execute_query(query_livraisons, (fournisseur_id,))
            if result_livr:
                livraisons_data = dict(result_livr[0])
                performance.update(livraisons_data)
                
                # Calcul taux de ponctualité
                if livraisons_data.get('total_livraisons', 0) > 0:
                    performance['taux_ponctualite'] = (
                        livraisons_data.get('livraisons_temps', 0) / 
                        livraisons_data['total_livraisons'] * 100
                    )
            
            return performance
            
        except Exception as e:
            st.error(f"Erreur calcul performance: {e}")
            return {}
    
    def get_categories_disponibles(self) -> List[str]:
        """Récupère toutes les catégories de produits disponibles"""
        try:
            query = '''
                SELECT DISTINCT categorie_produits 
                FROM fournisseurs 
                WHERE categorie_produits IS NOT NULL 
                AND categorie_produits != ''
                ORDER BY categorie_produits
            '''
            rows = self.db.execute_query(query)
            return [row['categorie_produits'] for row in rows]
        except Exception as e:
            st.error(f"Erreur récupération catégories: {e}")
            return []
    
    def get_fournisseurs_statistics(self) -> Dict:
        """Retourne des statistiques globales sur les fournisseurs"""
        try:
            stats = {
                'total_fournisseurs': 0,
                'par_categorie': {},
                'evaluation_moyenne': 0.0,
                'delai_moyen': 0,
                'montant_total_commandes': 0.0,
                'top_performers': [],
                'certifications_count': {}
            }
            
            # Statistiques de base
            query_base = '''
                SELECT 
                    COUNT(*) as total,
                    AVG(evaluation_qualite) as eval_moy,
                    AVG(delai_livraison_moyen) as delai_moy
                FROM fournisseurs
            '''
            result = self.db.execute_query(query_base)
            if result:
                row = result[0]
                stats['total_fournisseurs'] = row['total']
                stats['evaluation_moyenne'] = round(row['eval_moy'] or 0, 1)
                stats['delai_moyen'] = round(row['delai_moy'] or 0)
            
            # Par catégorie
            query_cat = '''
                SELECT categorie_produits, COUNT(*) as count
                FROM fournisseurs
                WHERE categorie_produits IS NOT NULL
                GROUP BY categorie_produits
                ORDER BY count DESC
            '''
            rows_cat = self.db.execute_query(query_cat)
            for row in rows_cat:
                if row['categorie_produits']:
                    stats['par_categorie'][row['categorie_produits']] = row['count']
            
            # Montant total commandes
            query_montant = '''
                SELECT SUM(f.montant_total) as total_montant
                FROM formulaires f
                JOIN companies c ON f.company_id = c.id
                JOIN fournisseurs fou ON c.id = fou.company_id
                WHERE f.type_formulaire IN ('BON_ACHAT', 'BON_COMMANDE')
            '''
            result_montant = self.db.execute_query(query_montant)
            if result_montant:
                stats['montant_total_commandes'] = result_montant[0]['total_montant'] or 0.0
            
            # Top performers (par évaluation et volume)
            query_top = '''
                SELECT c.nom, f.evaluation_qualite, COUNT(form.id) as nb_commandes,
                       SUM(form.montant_total) as montant_total
                FROM fournisseurs f
                JOIN companies c ON f.company_id = c.id
                LEFT JOIN formulaires form ON c.id = form.company_id 
                    AND form.type_formulaire IN ('BON_ACHAT', 'BON_COMMANDE')
                GROUP BY f.id, c.nom, f.evaluation_qualite
                ORDER BY f.evaluation_qualite DESC, montant_total DESC
                LIMIT 5
            '''
            rows_top = self.db.execute_query(query_top)
            stats['top_performers'] = [dict(row) for row in rows_top]
            
            return stats
            
        except Exception as e:
            st.error(f"Erreur statistiques fournisseurs: {e}")
            return {}

    # =========================================================================
    # MÉTHODES POUR FORMULAIRES DEMANDE DE PRIX ET BON D'ACHAT
    # =========================================================================
    
    def get_inventory_items_for_selection(self, search_term: str = None) -> List[Dict]:
        """Récupère les articles d'inventaire pour sélection dans formulaires"""
        try:
            query = '''
                SELECT id, nom, type_produit, quantite_imperial, quantite_metric,
                       statut, description, fournisseur_principal, code_interne
                FROM inventory_items
            '''
            params = []
            
            if search_term:
                query += " WHERE nom LIKE ? OR code_interne LIKE ? OR description LIKE ?"
                pattern = f"%{search_term}%"
                params = [pattern, pattern, pattern]
            
            query += " ORDER BY nom"
            
            rows = self.db.execute_query(query, tuple(params) if params else None)
            return [dict(row) for row in rows]
            
        except Exception as e:
            st.error(f"Erreur récupération articles: {e}")
            return []
    
    def generate_document_number(self, type_formulaire: str) -> str:
        """Génère un numéro de document automatique"""
        try:
            prefixes = {
                'DEMANDE_PRIX': 'DP',
                'BON_ACHAT': 'BA'
            }
            
            prefix = prefixes.get(type_formulaire, 'DOC')
            annee = datetime.now().year
            
            # Récupérer le dernier numéro pour ce type et cette année
            query = '''
                SELECT numero_document FROM formulaires 
                WHERE type_formulaire = ? AND numero_document LIKE ?
                ORDER BY id DESC LIMIT 1
            '''
            pattern = f"{prefix}-{annee}-%"
            result = self.db.execute_query(query, (type_formulaire, pattern))
            
            if result:
                last_num = result[0]['numero_document']
                sequence = int(last_num.split('-')[-1]) + 1
            else:
                sequence = 1
            
            return f"{prefix}-{annee}-{sequence:03d}"
            
        except Exception as e:
            st.error(f"Erreur génération numéro: {e}")
            return f"ERR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def create_formulaire_with_lines(self, formulaire_data: Dict, lignes_data: List[Dict]) -> int:
        """Crée un formulaire avec ses lignes de détail"""
        try:
            # Vérifier que la company existe avant de créer le formulaire
            check_company_query = "SELECT id FROM companies WHERE id = ?"
            company_exists = self.db.execute_query(check_company_query, (formulaire_data['company_id'],))
            
            if not company_exists:
                st.error(f"❌ Erreur: L'entreprise ID {formulaire_data['company_id']} n'existe pas.")
                return None
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Créer le formulaire principal
                query_formulaire = '''
                    INSERT INTO formulaires 
                    (type_formulaire, numero_document, company_id, employee_id, statut, 
                     priorite, date_echeance, notes, metadonnees_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                
                cursor.execute(query_formulaire, (
                    formulaire_data['type_formulaire'],
                    formulaire_data['numero_document'],
                    formulaire_data['company_id'],
                    formulaire_data.get('employee_id'),
                    formulaire_data.get('statut', 'BROUILLON'),
                    formulaire_data.get('priorite', 'NORMAL'),
                    formulaire_data.get('date_echeance'),
                    formulaire_data.get('notes', ''),
                    formulaire_data.get('metadonnees_json', '{}')
                ))
                
                formulaire_id = cursor.lastrowid
                
                # Créer les lignes de détail
                query_ligne = '''
                    INSERT INTO formulaire_lignes
                    (formulaire_id, sequence_ligne, description, code_article,
                     quantite, unite, prix_unitaire, notes_ligne)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                '''
                
                for i, ligne in enumerate(lignes_data, 1):
                    cursor.execute(query_ligne, (
                        formulaire_id,
                        i,
                        ligne['description'],
                        ligne.get('code_article', ''),
                        ligne['quantite'],
                        ligne.get('unite', 'UN'),
                        ligne.get('prix_unitaire', 0.0),
                        ligne.get('notes_ligne', '')
                    ))
                
                # Enregistrer la création dans l'historique
                try:
                    cursor.execute('''
                        INSERT INTO formulaire_validations
                        (formulaire_id, employee_id, type_validation, commentaires)
                        VALUES (?, ?, 'CREATION', ?)
                    ''', (formulaire_id, formulaire_data.get('employee_id'), f"Création {formulaire_data['type_formulaire']}"))
                except Exception as validation_error:
                    # L'historique n'est pas critique, continuer même en cas d'erreur
                    print(f"Avertissement: Impossible d'enregistrer l'historique: {validation_error}")
                
                conn.commit()
                return formulaire_id
                
        except Exception as e:
            error_msg = str(e)
            if "FOREIGN KEY constraint failed" in error_msg:
                st.error(f"❌ Erreur de contrainte: Vérifiez que l'entreprise sélectionnée existe toujours.")
            else:
                st.error(f"❌ Erreur création formulaire: {e}")
            return None
    
    def get_formulaires_fournisseur(self, company_id: int, type_formulaire: str = None) -> List[Dict]:
        """Récupère les formulaires d'un fournisseur"""
        try:
            query = '''
                SELECT f.*, 
                       COUNT(fl.id) as nombre_lignes,
                       COALESCE(SUM(fl.montant_ligne), 0) as montant_calcule
                FROM formulaires f
                LEFT JOIN formulaire_lignes fl ON f.id = fl.formulaire_id
                WHERE f.company_id = ?
            '''
            params = [company_id]
            
            if type_formulaire:
                query += " AND f.type_formulaire = ?"
                params.append(type_formulaire)
            
            query += '''
                GROUP BY f.id
                ORDER BY f.date_creation DESC
            '''
            
            rows = self.db.execute_query(query, tuple(params))
            return [dict(row) for row in rows]
            
        except Exception as e:
            st.error(f"Erreur récupération formulaires: {e}")
            return []
    
    def get_formulaire_details_with_lines(self, formulaire_id: int) -> Dict:
        """Récupère un formulaire avec ses lignes de détail"""
        try:
            # Récupérer le formulaire
            query_formulaire = '''
                SELECT f.*, c.nom as company_nom
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                WHERE f.id = ?
            '''
            result = self.db.execute_query(query_formulaire, (formulaire_id,))
            
            if not result:
                return {}
            
            formulaire = dict(result[0])
            
            # Récupérer les lignes
            query_lignes = '''
                SELECT * FROM formulaire_lignes 
                WHERE formulaire_id = ? 
                ORDER BY sequence_ligne
            '''
            lignes = self.db.execute_query(query_lignes, (formulaire_id,))
            formulaire['lignes'] = [dict(ligne) for ligne in lignes]
            
            return formulaire
            
        except Exception as e:
            st.error(f"Erreur récupération détails formulaire: {e}")
            return {}

def show_fournisseurs_page():
    """Page principale du module Fournisseurs - VERSION NETTOYÉE"""
    st.markdown("## 🏪 Gestion des Fournisseurs DG Inc.")
    
    # Initialisation du gestionnaire
    if 'gestionnaire_fournisseurs' not in st.session_state:
        st.session_state.gestionnaire_fournisseurs = GestionnaireFournisseurs(st.session_state.erp_db)
    
    gestionnaire = st.session_state.gestionnaire_fournisseurs
    
    # Variables de session
    if 'fournisseur_action' not in st.session_state:
        st.session_state.fournisseur_action = None
    if 'selected_fournisseur_id' not in st.session_state:
        st.session_state.selected_fournisseur_id = None
    if 'fournisseur_filter_category' not in st.session_state:
        st.session_state.fournisseur_filter_category = 'TOUS'
    if 'form_lines_data' not in st.session_state:
        st.session_state.form_lines_data = []
    
    # Onglets simplifiés
    tab_dashboard, tab_liste, tab_performance, tab_categories, tab_demande_prix, tab_bon_achat = st.tabs([
        "📊 Dashboard", "📋 Liste Fournisseurs", "📈 Performances", 
        "🏷️ Catégories", "📋 Demande de Prix", "🛒 Bon d'Achat"
    ])
    
    with tab_dashboard:
        render_fournisseurs_dashboard(gestionnaire)
    
    with tab_liste:
        render_fournisseurs_liste(gestionnaire)
    
    with tab_performance:
        render_fournisseurs_performance(gestionnaire)
    
    with tab_categories:
        render_fournisseurs_categories(gestionnaire)
    
    with tab_demande_prix:
        render_demande_prix_tab(gestionnaire)
    
    with tab_bon_achat:
        render_bon_achat_tab(gestionnaire)
    
    # Formulaires modaux existants
    action = st.session_state.get('fournisseur_action')
    selected_id = st.session_state.get('selected_fournisseur_id')
    
    if action == "create_fournisseur":
        render_fournisseur_form(gestionnaire, fournisseur_data=None)
    elif action == "edit_fournisseur" and selected_id:
        fournisseur_data = gestionnaire.get_fournisseur_by_id(selected_id)
        render_fournisseur_form(gestionnaire, fournisseur_data=fournisseur_data)
    elif action == "view_fournisseur_details" and selected_id:
        fournisseur_data = gestionnaire.get_fournisseur_by_id(selected_id)
        render_fournisseur_details(gestionnaire, fournisseur_data)

# =========================================================================
# ONGLETS POUR FORMULAIRES DEMANDE DE PRIX ET BON D'ACHAT
# =========================================================================

def render_demande_prix_tab(gestionnaire):
    """Onglet pour gestion des Demandes de Prix"""
    st.markdown("### 📋 Demandes de Prix (DP)")
    
    # Sous-onglets pour organiser
    sub_tab_create, sub_tab_list, sub_tab_view = st.tabs([
        "➕ Nouvelle Demande", "📋 Liste des DP", "👁️ Consulter DP"
    ])
    
    with sub_tab_create:
        render_create_demande_prix_form(gestionnaire)
    
    with sub_tab_list:
        render_list_demandes_prix(gestionnaire)
    
    with sub_tab_view:
        render_view_demande_prix(gestionnaire)

def render_bon_achat_tab(gestionnaire):
    """Onglet pour gestion des Bons d'Achat"""
    st.markdown("### 🛒 Bons d'Achat (BA)")
    
    # Sous-onglets pour organiser
    sub_tab_create, sub_tab_list, sub_tab_view = st.tabs([
        "➕ Nouveau Bon d'Achat", "📋 Liste des BA", "👁️ Consulter BA"
    ])
    
    with sub_tab_create:
        render_create_bon_achat_form(gestionnaire)
    
    with sub_tab_list:
        render_list_bons_achat(gestionnaire)
    
    with sub_tab_view:
        render_view_bon_achat(gestionnaire)

def render_create_demande_prix_form(gestionnaire):
    """Formulaire de création de Demande de Prix - VERSION CORRIGÉE"""
    st.markdown("#### ➕ Nouvelle Demande de Prix")
    
    # Vérification des fournisseurs
    fournisseurs = gestionnaire.get_all_fournisseurs()
    
    # DEBUG TEMPORAIRE - Afficher la structure des données
    if fournisseurs and len(fournisseurs) > 0:
        with st.expander("🔍 DEBUG - Structure des données fournisseurs", expanded=False):
            st.write("**Premier fournisseur (exemple):**")
            st.json(fournisseurs[0])
            st.write("**Clés disponibles:**", list(fournisseurs[0].keys()))
            
            # Vérifier si la colonne est_actif existe encore
            if 'est_actif' in fournisseurs[0]:
                st.warning("⚠️ La colonne 'est_actif' existe encore dans les données")
                if st.button("🔧 Forcer le nettoyage de la DB", key="force_cleanup_ba"):
                    gestionnaire._cleanup_database()
                    st.success("Nettoyage forcé terminé - Rechargez la page")
                    st.rerun()
            
            # Vérifier si la colonne est_actif existe encore
            if 'est_actif' in fournisseurs[0]:
                st.warning("⚠️ La colonne 'est_actif' existe encore dans les données")
                if st.button("🔧 Forcer le nettoyage de la DB", key="force_cleanup_dp"):
                    gestionnaire._cleanup_database()
                    st.success("Nettoyage forcé terminé - Rechargez la page")
                    st.rerun()
    
    if not fournisseurs:
        st.warning("⚠️ Aucun fournisseur disponible.")
        st.info("💡 Créez d'abord un fournisseur dans l'onglet 'Liste Fournisseurs' pour pouvoir créer une demande de prix.")
        
        if st.button("➕ Aller créer un fournisseur", use_container_width=True, key="dp_goto_create_fournisseur"):
            st.session_state.fournisseur_action = "create_fournisseur"
            st.rerun()
        return
    
    # Initialiser les lignes si nécessaire
    if 'dp_lines' not in st.session_state:
        st.session_state.dp_lines = []
    
    # Section pour ajouter des articles (HORS du formulaire)
    st.markdown("#### 📦 Articles à chiffrer")
    
    with st.expander("➕ Ajouter un article", expanded=len(st.session_state.dp_lines) == 0):
        add_col1, add_col2, add_col3 = st.columns(3)
        
        with add_col1:
            # Recherche d'article dans l'inventaire
            search_term = st.text_input("🔍 Rechercher article:", key="dp_search_article")
            articles = gestionnaire.get_inventory_items_for_selection(search_term)
            
            if articles:
                selected_article = st.selectbox(
                    "Article inventaire:",
                    options=[None] + articles,
                    format_func=lambda x: "-- Sélectionner --" if x is None else f"{x.get('nom', '')} ({x.get('code_interne', '')})",
                    key="dp_selected_article"
                )
            else:
                selected_article = None
                st.info("Aucun article trouvé ou saisie manuelle")
            
            description_article = st.text_input(
                "Description:",
                value=selected_article.get('nom', '') if selected_article else '',
                key="dp_description"
            )
        
        with add_col2:
            code_article = st.text_input(
                "Code article:",
                value=selected_article.get('code_interne', '') if selected_article else '',
                key="dp_code"
            )
            
            quantite = st.number_input(
                "Quantité:",
                min_value=0.01,
                value=1.0,
                step=0.01,
                key="dp_quantite"
            )
        
        with add_col3:
            unite = st.selectbox(
                "Unité:",
                options=['UN', 'M', 'M²', 'M³', 'KG', 'L', 'H'],
                key="dp_unite"
            )
            
            notes_ligne = st.text_input(
                "Notes ligne:",
                key="dp_notes_ligne"
            )
        
        if st.button("➕ Ajouter à la demande", use_container_width=True, key="dp_add_line"):
            if description_article and quantite > 0:
                nouvelle_ligne = {
                    'description': description_article,
                    'code_article': code_article,
                    'quantite': quantite,
                    'unite': unite,
                    'notes_ligne': notes_ligne
                }
                st.session_state.dp_lines.append(nouvelle_ligne)
                st.success("Article ajouté !")
                st.rerun()
            else:
                st.error("Description et quantité sont obligatoires.")
    
    # Affichage des lignes ajoutées (HORS du formulaire)
    if st.session_state.dp_lines:
        st.markdown("**Articles dans la demande:**")
        
        for i, ligne in enumerate(st.session_state.dp_lines):
            col_desc, col_qty, col_action = st.columns([3, 1, 1])
            
            with col_desc:
                st.markdown(f"**{ligne['description']}** ({ligne['code_article']})")
                if ligne['notes_ligne']:
                    st.caption(f"📝 {ligne['notes_ligne']}")
            
            with col_qty:
                st.markdown(f"{ligne['quantite']} {ligne['unite']}")
            
            with col_action:
                if st.button("🗑️", key=f"dp_remove_{i}", help="Supprimer cette ligne"):
                    st.session_state.dp_lines.pop(i)
                    st.rerun()
    else:
        st.info("Aucun article ajouté. Ajoutez au moins un article pour créer la demande.")
    
    # Actions rapides pour vider la liste
    if st.session_state.dp_lines:
        if st.button("🗑️ Vider tous les articles", key="dp_clear_all"):
            st.session_state.dp_lines = []
            st.rerun()
    
    st.markdown("---")
    
    # Formulaire principal (SANS la gestion des lignes)
    with st.form("demande_prix_form", clear_on_submit=False):
        st.markdown("#### 📋 Informations de la Demande")
        
        # En-tête du formulaire
        col1, col2 = st.columns(2)
        
        with col1:
            # Pré-sélection si définie depuis un autre onglet
            preselected_id = st.session_state.get('preselected_fournisseur_id')
            default_index = 0
            
            if preselected_id:
                for i, f in enumerate(fournisseurs):
                    if f.get('id') == preselected_id:
                        default_index = i
                        break
                # Réinitialiser après utilisation
                if 'preselected_fournisseur_id' in st.session_state:
                    del st.session_state.preselected_fournisseur_id
            
            selected_fournisseur = st.selectbox(
                "Fournisseur *:",
                options=fournisseurs,
                format_func=lambda f: f.get('nom', 'N/A'),
                index=default_index,
                help="Sélectionnez le fournisseur pour la demande de prix"
            )
            
            priorite = st.selectbox(
                "Priorité:",
                options=['NORMAL', 'URGENT', 'CRITIQUE'],
                index=0
            )
        
        with col2:
            numero_dp = gestionnaire.generate_document_number('DEMANDE_PRIX')
            st.text_input("Numéro DP:", value=numero_dp, disabled=True)
            
            date_echeance = st.date_input(
                "Date limite réponse:",
                value=datetime.now().date() + timedelta(days=7),
                help="Date limite pour la réponse du fournisseur"
            )
        
        # Notes
        notes = st.text_area(
            "Notes / Instructions:",
            placeholder="Instructions spéciales, conditions particulières...",
            help="Notes qui apparaîtront sur la demande de prix"
        )
        
        # Boutons de soumission
        st.markdown("---")
        submit_col1, submit_col2 = st.columns(2)
        
        with submit_col1:
            submitted = st.form_submit_button("📋 Créer Demande de Prix", use_container_width=True)
        
        with submit_col2:
            save_draft = st.form_submit_button("💾 Sauver Brouillon", use_container_width=True)
        
        # Traitement du formulaire
        if (submitted or save_draft):
            if not st.session_state.dp_lines:
                st.error("❌ Ajoutez au moins un article avant de créer la demande.")
            else:
                # Vérification de la validité du fournisseur sélectionné
                if not selected_fournisseur or 'company_id' not in selected_fournisseur:
                    st.error("❌ Erreur avec le fournisseur sélectionné. Veuillez réessayer.")
                    st.rerun()
                    return
                
                # DEBUG AVANCÉ - Diagnostic du problème de contrainte
                company_id = selected_fournisseur['company_id']
                fournisseur_id = selected_fournisseur.get('id')
                
                with st.expander("🔍 DIAGNOSTIC CONTRAINTE", expanded=True):
                    st.write(f"**Fournisseur sélectionné:** {selected_fournisseur.get('nom')}")
                    st.write(f"**Fournisseur ID:** {fournisseur_id}")
                    st.write(f"**Company ID récupéré:** {company_id}")
                    
                    # Vérifier si la company existe
                    check_company = gestionnaire.db.execute_query("SELECT id, nom FROM companies WHERE id = ?", (company_id,))
                    if check_company:
                        st.success(f"✅ Company trouvée: {check_company[0]['nom']} (ID: {check_company[0]['id']})")
                    else:
                        st.error(f"❌ Company ID {company_id} n'existe PAS dans la table companies!")
                    
                    # Vérifier si le fournisseur existe
                    check_fournisseur = gestionnaire.db.execute_query("SELECT id, company_id FROM fournisseurs WHERE id = ?", (fournisseur_id,))
                    if check_fournisseur:
                        st.success(f"✅ Fournisseur trouvé: ID {check_fournisseur[0]['id']}, Company ID: {check_fournisseur[0]['company_id']}")
                    else:
                        st.error(f"❌ Fournisseur ID {fournisseur_id} n'existe PAS!")
                    
                    # Lister toutes les companies disponibles
                    all_companies = gestionnaire.db.execute_query("SELECT id, nom FROM companies ORDER BY nom")
                    st.write("**Companies disponibles:**")
                    for comp in all_companies:
                        st.write(f"- ID {comp['id']}: {comp['nom']}")
                
                # Continuer avec la création si les vérifications passent
                if check_company:
                    formulaire_data = {
                        'type_formulaire': 'DEMANDE_PRIX',
                        'numero_document': numero_dp,
                        'company_id': company_id,
                        'employee_id': 1,  # À adapter selon l'utilisateur connecté
                        'statut': 'VALIDÉ' if submitted else 'BROUILLON',
                        'priorite': priorite,
                        'date_echeance': date_echeance.isoformat(),
                        'notes': notes,
                        'metadonnees_json': json.dumps({
                            'fournisseur_nom': selected_fournisseur.get('nom', 'N/A'),
                            'type_document': 'demande_prix'
                        })
                    }
                    
                    formulaire_id = gestionnaire.create_formulaire_with_lines(formulaire_data, st.session_state.dp_lines)
                    
                    if formulaire_id:
                        action_text = "créée et envoyée" if submitted else "sauvée en brouillon"
                        st.success(f"✅ Demande de Prix {numero_dp} {action_text} ! (ID: {formulaire_id})")
                        st.session_state.dp_lines = []  # Vider les lignes
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la création de la demande.")
                else:
                    st.error("❌ Impossible de créer la demande - problème de contrainte détecté ci-dessus.")

def render_create_bon_achat_form(gestionnaire):
    """Formulaire de création de Bon d'Achat - VERSION CORRIGÉE"""
    st.markdown("#### 🛒 Nouveau Bon d'Achat")
    
    # Vérification des fournisseurs
    fournisseurs = gestionnaire.get_all_fournisseurs()
    
    # DEBUG TEMPORAIRE - Afficher la structure des données
    if fournisseurs and len(fournisseurs) > 0:
        with st.expander("🔍 DEBUG - Structure des données fournisseurs", expanded=False):
            st.write("**Premier fournisseur (exemple):**")
            st.json(fournisseurs[0])
            st.write("**Clés disponibles:**", list(fournisseurs[0].keys()))
    
    if not fournisseurs:
        st.warning("⚠️ Aucun fournisseur disponible.")
        st.info("💡 Créez d'abord un fournisseur dans l'onglet 'Liste Fournisseurs' pour pouvoir créer un bon d'achat.")
        
        if st.button("➕ Aller créer un fournisseur", use_container_width=True, key="ba_goto_create_fournisseur"):
            st.session_state.fournisseur_action = "create_fournisseur"
            st.rerun()
        return
    
    # Initialiser les lignes si nécessaire
    if 'ba_lines' not in st.session_state:
        st.session_state.ba_lines = []
    
    # Section pour ajouter des articles (HORS du formulaire)
    st.markdown("#### 🛒 Articles à commander")
    
    with st.expander("➕ Ajouter un article", expanded=len(st.session_state.ba_lines) == 0):
        add_col1, add_col2, add_col3, add_col4 = st.columns(4)
        
        with add_col1:
            # Recherche d'article dans l'inventaire
            search_term = st.text_input("🔍 Rechercher article:", key="ba_search_article")
            articles = gestionnaire.get_inventory_items_for_selection(search_term)
            
            if articles:
                selected_article = st.selectbox(
                    "Article inventaire:",
                    options=[None] + articles,
                    format_func=lambda x: "-- Sélectionner --" if x is None else f"{x.get('nom', '')} ({x.get('code_interne', '')})",
                    key="ba_selected_article"
                )
            else:
                selected_article = None
                st.info("Aucun article trouvé")
            
            description_article = st.text_input(
                "Description *:",
                value=selected_article.get('nom', '') if selected_article else '',
                key="ba_description"
            )
        
        with add_col2:
            code_article = st.text_input(
                "Code article:",
                value=selected_article.get('code_interne', '') if selected_article else '',
                key="ba_code"
            )
            
            quantite = st.number_input(
                "Quantité *:",
                min_value=0.01,
                value=1.0,
                step=0.01,
                key="ba_quantite"
            )
        
        with add_col3:
            unite = st.selectbox(
                "Unité:",
                options=['UN', 'M', 'M²', 'M³', 'KG', 'L', 'H'],
                key="ba_unite"
            )
            
            prix_unitaire = st.number_input(
                "Prix unitaire $ *:",
                min_value=0.0,
                value=0.0,
                step=0.01,
                key="ba_prix"
            )
        
        with add_col4:
            montant_ligne = quantite * prix_unitaire
            st.metric("💰 Montant ligne:", f"{montant_ligne:.2f} $")
            
            notes_ligne = st.text_input(
                "Notes ligne:",
                key="ba_notes_ligne"
            )
        
        if st.button("➕ Ajouter au bon d'achat", use_container_width=True, key="ba_add_line"):
            if description_article and quantite > 0 and prix_unitaire >= 0:
                nouvelle_ligne = {
                    'description': description_article,
                    'code_article': code_article,
                    'quantite': quantite,
                    'unite': unite,
                    'prix_unitaire': prix_unitaire,
                    'notes_ligne': notes_ligne
                }
                st.session_state.ba_lines.append(nouvelle_ligne)
                st.success("Article ajouté !")
                st.rerun()
            else:
                st.error("Description, quantité et prix sont obligatoires.")
    
    # Affichage des lignes ajoutées avec calcul du total (HORS du formulaire)
    if st.session_state.ba_lines:
        st.markdown("**Articles dans le bon d'achat:**")
        
        total_montant = 0
        for i, ligne in enumerate(st.session_state.ba_lines):
            montant_ligne = ligne['quantite'] * ligne['prix_unitaire']
            total_montant += montant_ligne
            
            with st.container():
                col_desc, col_qty, col_prix, col_montant, col_action = st.columns([3, 1, 1, 1, 1])
                
                with col_desc:
                    st.markdown(f"**{ligne['description']}** ({ligne['code_article']})")
                    if ligne['notes_ligne']:
                        st.caption(f"📝 {ligne['notes_ligne']}")
                
                with col_qty:
                    st.markdown(f"{ligne['quantite']} {ligne['unite']}")
                
                with col_prix:
                    st.markdown(f"{ligne['prix_unitaire']:.2f} $")
                
                with col_montant:
                    st.markdown(f"**{montant_ligne:.2f} $**")
                
                with col_action:
                    if st.button("🗑️", key=f"ba_remove_{i}", help="Supprimer cette ligne"):
                        st.session_state.ba_lines.pop(i)
                        st.rerun()
        
        # Affichage du total
        st.markdown("---")
        st.markdown(f"### 💰 **Total Bon d'Achat: {total_montant:.2f} $ CAD**")
    else:
        st.info("Aucun article ajouté. Ajoutez au moins un article pour créer le bon d'achat.")
    
    # Actions rapides pour vider la liste
    if st.session_state.ba_lines:
        if st.button("🗑️ Vider tous les articles", key="ba_clear_all"):
            st.session_state.ba_lines = []
            st.rerun()
    
    st.markdown("---")
    
    # Formulaire principal (SANS la gestion des lignes)
    with st.form("bon_achat_form", clear_on_submit=False):
        st.markdown("#### 🛒 Informations du Bon d'Achat")
        
        # En-tête du formulaire
        col1, col2 = st.columns(2)
        
        with col1:
            # Pré-sélection si définie depuis un autre onglet
            preselected_id = st.session_state.get('preselected_fournisseur_id')
            default_index = 0
            
            if preselected_id:
                for i, f in enumerate(fournisseurs):
                    if f.get('id') == preselected_id:
                        default_index = i
                        break
                # Réinitialiser après utilisation
                if 'preselected_fournisseur_id' in st.session_state:
                    del st.session_state.preselected_fournisseur_id
            
            selected_fournisseur = st.selectbox(
                "Fournisseur *:",
                options=fournisseurs,
                format_func=lambda f: f.get('nom', 'N/A'),
                index=default_index,
                help="Sélectionnez le fournisseur pour le bon d'achat"
            )
            
            priorite = st.selectbox(
                "Priorité:",
                options=['NORMAL', 'URGENT', 'CRITIQUE'],
                index=0
            )
        
        with col2:
            numero_ba = gestionnaire.generate_document_number('BON_ACHAT')
            st.text_input("Numéro BA:", value=numero_ba, disabled=True)
            
            date_echeance = st.date_input(
                "Date livraison souhaitée:",
                value=datetime.now().date() + timedelta(days=14),
                help="Date de livraison souhaitée"
            )
        
        # Notes
        notes = st.text_area(
            "Notes / Instructions:",
            placeholder="Instructions de livraison, conditions particulières...",
            help="Notes qui apparaîtront sur le bon d'achat"
        )
        
        # Boutons de soumission
        st.markdown("---")
        submit_col1, submit_col2 = st.columns(2)
        
        with submit_col1:
            submitted = st.form_submit_button("🛒 Créer Bon d'Achat", use_container_width=True)
        
        with submit_col2:
            save_draft = st.form_submit_button("💾 Sauver Brouillon", use_container_width=True)
        
        # Traitement du formulaire
        if (submitted or save_draft):
            if not st.session_state.ba_lines:
                st.error("❌ Ajoutez au moins un article avant de créer le bon d'achat.")
            else:
                # Vérification de la validité du fournisseur sélectionné
                if not selected_fournisseur or 'company_id' not in selected_fournisseur:
                    st.error("❌ Erreur avec le fournisseur sélectionné. Veuillez réessayer.")
                    st.rerun()
                    return
                
                formulaire_data = {
                    'type_formulaire': 'BON_ACHAT',
                    'numero_document': numero_ba,
                    'company_id': selected_fournisseur['company_id'],
                    'employee_id': 1,  # À adapter selon l'utilisateur connecté
                    'statut': 'VALIDÉ' if submitted else 'BROUILLON',
                    'priorite': priorite,
                    'date_echeance': date_echeance.isoformat(),
                    'notes': notes,
                    'metadonnees_json': json.dumps({
                        'fournisseur_nom': selected_fournisseur.get('nom', 'N/A'),
                        'type_document': 'bon_achat',
                        'total_calcule': sum(l['quantite'] * l['prix_unitaire'] for l in st.session_state.ba_lines)
                    })
                }
                
                formulaire_id = gestionnaire.create_formulaire_with_lines(formulaire_data, st.session_state.ba_lines)
                
                if formulaire_id:
                    action_text = "créé et envoyé" if submitted else "sauvé en brouillon"
                    st.success(f"✅ Bon d'Achat {numero_ba} {action_text} ! (ID: {formulaire_id})")
                    st.session_state.ba_lines = []  # Vider les lignes
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la création du bon d'achat.")

def render_list_demandes_prix(gestionnaire):
    """Liste des demandes de prix"""
    st.markdown("#### 📋 Liste des Demandes de Prix")
    
    # Récupérer toutes les demandes de prix
    try:
        query = '''
            SELECT f.*, c.nom as company_nom,
                   COUNT(fl.id) as nombre_lignes
            FROM formulaires f
            LEFT JOIN companies c ON f.company_id = c.id
            LEFT JOIN formulaire_lignes fl ON f.id = fl.formulaire_id
            WHERE f.type_formulaire = 'DEMANDE_PRIX'
            GROUP BY f.id
            ORDER BY f.date_creation DESC
        '''
        demandes = gestionnaire.db.execute_query(query)
        
        if not demandes:
            st.info("Aucune demande de prix créée.")
            return
        
        # Affichage sous forme de tableau
        df_data = []
        for dp in demandes:
            statut_icon = {
                'BROUILLON': '📝',
                'VALIDÉ': '✅',
                'ENVOYÉ': '📤',
                'APPROUVÉ': '👍',
                'TERMINÉ': '✅',
                'ANNULÉ': '❌'
            }.get(dp['statut'], '❓')
            
            priorite_icon = {
                'NORMAL': '🟢',
                'URGENT': '🟡',
                'CRITIQUE': '🔴'
            }.get(dp['priorite'], '⚪')
            
            df_data.append({
                '🆔': dp['id'],
                '📋 Numéro': dp['numero_document'],
                '🏪 Fournisseur': dp['company_nom'],
                '📊 Statut': f"{statut_icon} {dp['statut']}",
                '⚡ Priorité': f"{priorite_icon} {dp['priorite']}",
                '📦 Nb Articles': dp['nombre_lignes'],
                '📅 Créé le': pd.to_datetime(dp['date_creation']).strftime('%d/%m/%Y'),
                '⏰ Échéance': pd.to_datetime(dp['date_echeance']).strftime('%d/%m/%Y') if dp['date_echeance'] else 'N/A'
            })
        
        st.dataframe(pd.DataFrame(df_data), use_container_width=True)
        
        # Sélection pour actions
        if demandes:
            st.markdown("---")
            selected_dp_id = st.selectbox(
                "Sélectionner une demande pour action:",
                options=[dp['id'] for dp in demandes],
                format_func=lambda id: next((dp['numero_document'] for dp in demandes if dp['id'] == id), ''),
                key="select_dp_for_action"
            )
            
            if selected_dp_id:
                action_col1, action_col2, action_col3 = st.columns(3)
                
                with action_col1:
                    if st.button("👁️ Voir Détails", use_container_width=True, key="view_dp_details"):
                        st.session_state.selected_formulaire_id = selected_dp_id
                        st.session_state.selected_formulaire_type = 'DEMANDE_PRIX'
                
                with action_col2:
                    if st.button("📤 Marquer Envoyé", use_container_width=True, key="mark_dp_sent"):
                        # Mettre à jour le statut
                        gestionnaire.db.execute_update(
                            "UPDATE formulaires SET statut = 'ENVOYÉ' WHERE id = ?",
                            (selected_dp_id,)
                        )
                        st.success("Statut mis à jour !")
                        st.rerun()
                
                with action_col3:
                    if st.button("🛒 Convertir en BA", use_container_width=True, key="convert_dp_to_ba"):
                        st.info("💡 Consultez l'onglet 'Bon d'Achat' pour créer un nouveau BA basé sur cette DP.")
        
    except Exception as e:
        st.error(f"Erreur récupération demandes: {e}")

def render_list_bons_achat(gestionnaire):
    """Liste des bons d'achat"""
    st.markdown("#### 🛒 Liste des Bons d'Achat")
    
    # Récupérer tous les bons d'achat
    try:
        query = '''
            SELECT f.*, c.nom as company_nom,
                   COUNT(fl.id) as nombre_lignes,
                   COALESCE(SUM(fl.montant_ligne), 0) as montant_total_calcule
            FROM formulaires f
            LEFT JOIN companies c ON f.company_id = c.id
            LEFT JOIN formulaire_lignes fl ON f.id = fl.formulaire_id
            WHERE f.type_formulaire = 'BON_ACHAT'
            GROUP BY f.id
            ORDER BY f.date_creation DESC
        '''
        bons_achat = gestionnaire.db.execute_query(query)
        
        if not bons_achat:
            st.info("Aucun bon d'achat créé.")
            return
        
        # Affichage sous forme de tableau
        df_data = []
        for ba in bons_achat:
            statut_icon = {
                'BROUILLON': '📝',
                'VALIDÉ': '✅',
                'ENVOYÉ': '📤',
                'APPROUVÉ': '👍',
                'TERMINÉ': '✅',
                'ANNULÉ': '❌'
            }.get(ba['statut'], '❓')
            
            priorite_icon = {
                'NORMAL': '🟢',
                'URGENT': '🟡',
                'CRITIQUE': '🔴'
            }.get(ba['priorite'], '⚪')
            
            df_data.append({
                '🆔': ba['id'],
                '🛒 Numéro': ba['numero_document'],
                '🏪 Fournisseur': ba['company_nom'],
                '📊 Statut': f"{statut_icon} {ba['statut']}",
                '⚡ Priorité': f"{priorite_icon} {ba['priorite']}",
                '📦 Nb Articles': ba['nombre_lignes'],
                '💰 Montant': f"{ba['montant_total_calcule']:,.2f} $",
                '📅 Créé le': pd.to_datetime(ba['date_creation']).strftime('%d/%m/%Y'),
                '📦 Livraison': pd.to_datetime(ba['date_echeance']).strftime('%d/%m/%Y') if ba['date_echeance'] else 'N/A'
            })
        
        st.dataframe(pd.DataFrame(df_data), use_container_width=True)
        
        # Statistiques rapides
        if bons_achat:
            st.markdown("---")
            st.markdown("#### 📊 Statistiques Rapides")
            
            total_montant = sum(ba['montant_total_calcule'] for ba in bons_achat)
            nb_fournisseurs = len(set(ba['company_nom'] for ba in bons_achat))
            
            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
            
            with stat_col1:
                st.metric("📊 Total BA", len(bons_achat))
            with stat_col2:
                st.metric("💰 Montant Total", f"{total_montant:,.0f} $")
            with stat_col3:
                st.metric("🏪 Fournisseurs", nb_fournisseurs)
            with stat_col4:
                moyenne = total_montant / len(bons_achat) if bons_achat else 0
                st.metric("📈 BA Moyen", f"{moyenne:,.0f} $")
        
        # Sélection pour actions
        if bons_achat:
            st.markdown("---")
            selected_ba_id = st.selectbox(
                "Sélectionner un bon d'achat pour action:",
                options=[ba['id'] for ba in bons_achat],
                format_func=lambda id: next((ba['numero_document'] for ba in bons_achat if ba['id'] == id), ''),
                key="select_ba_for_action"
            )
            
            if selected_ba_id:
                action_col1, action_col2, action_col3 = st.columns(3)
                
                with action_col1:
                    if st.button("👁️ Voir Détails", use_container_width=True, key="view_ba_details"):
                        st.session_state.selected_formulaire_id = selected_ba_id
                        st.session_state.selected_formulaire_type = 'BON_ACHAT'
                
                with action_col2:
                    if st.button("📤 Marquer Envoyé", use_container_width=True, key="mark_ba_sent"):
                        gestionnaire.db.execute_update(
                            "UPDATE formulaires SET statut = 'ENVOYÉ' WHERE id = ?",
                            (selected_ba_id,)
                        )
                        st.success("Statut mis à jour !")
                        st.rerun()
                
                with action_col3:
                    if st.button("✅ Marquer Livré", use_container_width=True, key="mark_ba_delivered"):
                        gestionnaire.db.execute_update(
                            "UPDATE formulaires SET statut = 'TERMINÉ' WHERE id = ?",
                            (selected_ba_id,)
                        )
                        st.success("Bon d'achat marqué comme livré !")
                        st.rerun()
        
    except Exception as e:
        st.error(f"Erreur récupération bons d'achat: {e}")

def render_view_demande_prix(gestionnaire):
    """Consultation détaillée d'une demande de prix"""
    st.markdown("#### 👁️ Consulter Demande de Prix")
    
    if 'selected_formulaire_id' not in st.session_state or st.session_state.get('selected_formulaire_type') != 'DEMANDE_PRIX':
        st.info("Sélectionnez une demande de prix dans la liste pour la consulter.")
        return
    
    formulaire_id = st.session_state.selected_formulaire_id
    dp_details = gestionnaire.get_formulaire_details_with_lines(formulaire_id)
    
    if not dp_details:
        st.error("Demande de prix non trouvée.")
        return
    
    # En-tête
    st.markdown(f"### 📋 {dp_details['numero_document']}")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.markdown(f"""
        **🏪 Fournisseur:** {dp_details['company_nom']}
        
        **📊 Statut:** {dp_details['statut']}
        
        **⚡ Priorité:** {dp_details['priorite']}
        """)
    
    with info_col2:
        st.markdown(f"""
        **📅 Créé le:** {pd.to_datetime(dp_details['date_creation']).strftime('%d/%m/%Y')}
        
        **⏰ Échéance:** {pd.to_datetime(dp_details['date_echeance']).strftime('%d/%m/%Y') if dp_details['date_echeance'] else 'N/A'}
        
        **📦 Nb Articles:** {len(dp_details.get('lignes', []))}
        """)
    
    # Notes
    if dp_details.get('notes'):
        st.markdown("---")
        st.markdown("**📝 Notes:**")
        st.markdown(f"_{dp_details['notes']}_")
    
    # Liste des articles
    st.markdown("---")
    st.markdown("#### 📦 Articles Demandés")
    
    lignes = dp_details.get('lignes', [])
    if lignes:
        df_lignes = []
        for ligne in lignes:
            df_lignes.append({
                '📦 Description': ligne['description'],
                '🔗 Code': ligne.get('code_article', ''),
                '📊 Quantité': f"{ligne['quantite']} {ligne.get('unite', 'UN')}",
                '📝 Notes': ligne.get('notes_ligne', '')
            })
        
        st.dataframe(pd.DataFrame(df_lignes), use_container_width=True)
    else:
        st.info("Aucun article dans cette demande.")
    
    # Actions
    st.markdown("---")
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("🔙 Retour à la liste", use_container_width=True, key="return_to_dp_list"):
            del st.session_state.selected_formulaire_id
            del st.session_state.selected_formulaire_type
            st.rerun()
    
    with action_col2:
        if st.button("📄 Générer PDF", use_container_width=True, key="generate_dp_pdf"):
            st.info("🚧 Fonctionnalité à développer - Génération PDF")
    
    with action_col3:
        if st.button("🛒 Créer BA basé sur DP", use_container_width=True, key="create_ba_from_dp"):
            # Préparer les données pour un nouveau BA
            st.session_state.ba_lines = [
                {
                    'description': ligne['description'],
                    'code_article': ligne.get('code_article', ''),
                    'quantite': ligne['quantite'],
                    'unite': ligne.get('unite', 'UN'),
                    'prix_unitaire': 0.0,  # À remplir
                    'notes_ligne': ligne.get('notes_ligne', '')
                }
                for ligne in lignes
            ]
            st.success("📋 Articles copiés vers nouveau BA ! Consultez l'onglet 'Bon d'Achat'.")

def render_view_bon_achat(gestionnaire):
    """Consultation détaillée d'un bon d'achat"""
    st.markdown("#### 👁️ Consulter Bon d'Achat")
    
    if 'selected_formulaire_id' not in st.session_state or st.session_state.get('selected_formulaire_type') != 'BON_ACHAT':
        st.info("Sélectionnez un bon d'achat dans la liste pour le consulter.")
        return
    
    formulaire_id = st.session_state.selected_formulaire_id
    ba_details = gestionnaire.get_formulaire_details_with_lines(formulaire_id)
    
    if not ba_details:
        st.error("Bon d'achat non trouvé.")
        return
    
    # En-tête
    st.markdown(f"### 🛒 {ba_details['numero_document']}")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.markdown(f"""
        **🏪 Fournisseur:** {ba_details['company_nom']}
        
        **📊 Statut:** {ba_details['statut']}
        
        **⚡ Priorité:** {ba_details['priorite']}
        """)
    
    with info_col2:
        st.markdown(f"""
        **📅 Créé le:** {pd.to_datetime(ba_details['date_creation']).strftime('%d/%m/%Y')}
        
        **📦 Livraison:** {pd.to_datetime(ba_details['date_echeance']).strftime('%d/%m/%Y') if ba_details['date_echeance'] else 'N/A'}
        
        **💰 Montant Total:** {ba_details.get('montant_total', 0):,.2f} $ CAD
        """)
    
    # Notes
    if ba_details.get('notes'):
        st.markdown("---")
        st.markdown("**📝 Notes:**")
        st.markdown(f"_{ba_details['notes']}_")
    
    # Liste des articles avec prix
    st.markdown("---")
    st.markdown("#### 🛒 Articles Commandés")
    
    lignes = ba_details.get('lignes', [])
    if lignes:
        df_lignes = []
        total_montant = 0
        
        for ligne in lignes:
            montant_ligne = ligne['quantite'] * ligne.get('prix_unitaire', 0)
            total_montant += montant_ligne
            
            df_lignes.append({
                '📦 Description': ligne['description'],
                '🔗 Code': ligne.get('code_article', ''),
                '📊 Quantité': f"{ligne['quantite']} {ligne.get('unite', 'UN')}",
                '💵 Prix Unit.': f"{ligne.get('prix_unitaire', 0):.2f} $",
                '💰 Montant': f"{montant_ligne:.2f} $",
                '📝 Notes': ligne.get('notes_ligne', '')
            })
        
        st.dataframe(pd.DataFrame(df_lignes), use_container_width=True)
        
        # Total
        st.markdown(f"### 💰 **Total Commande: {total_montant:,.2f} $ CAD**")
    else:
        st.info("Aucun article dans ce bon d'achat.")
    
    # Actions
    st.markdown("---")
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("🔙 Retour à la liste", use_container_width=True, key="return_to_ba_list"):
            del st.session_state.selected_formulaire_id
            del st.session_state.selected_formulaire_type
            st.rerun()
    
    with action_col2:
        if st.button("📄 Générer PDF", use_container_width=True, key="generate_ba_pdf"):
            st.info("🚧 Fonctionnalité à développer - Génération PDF")
    
    with action_col3:
        if st.button("📦 Suivi Livraison", use_container_width=True, key="track_ba_delivery"):
            st.info("🚧 Fonctionnalité à développer - Suivi livraison")

# =========================================================================
# FONCTIONS D'AFFICHAGE SIMPLIFIÉES (sans logique d'activation)
# =========================================================================

def render_fournisseurs_dashboard(gestionnaire):
    """Dashboard principal des fournisseurs - VERSION SIMPLIFIÉE"""
    st.markdown("### 📊 Vue d'Ensemble Fournisseurs")
    
    # Récupération des statistiques
    stats = gestionnaire.get_fournisseurs_statistics()
    
    if not stats:
        st.info("Aucune donnée fournisseur disponible.")
        if st.button("➕ Ajouter Premier Fournisseur", use_container_width=True, key="dashboard_add_first_fournisseur"):
            st.session_state.fournisseur_action = "create_fournisseur"
            st.rerun()
        return
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🏪 Total Fournisseurs", stats['total_fournisseurs'])
    with col2:
        st.metric("⭐ Éval. Moyenne", f"{stats['evaluation_moyenne']}/10")
    with col3:
        st.metric("📦 Délai Moyen", f"{stats['delai_moyen']} jours")
    with col4:
        montant_formate = f"{stats['montant_total_commandes']:,.0f} $ CAD"
        st.metric("💰 Volume Total", montant_formate)
    
    st.markdown("---")
    
    # Graphiques
    if stats['par_categorie'] or stats['top_performers']:
        graph_col1, graph_col2 = st.columns(2)
        
        with graph_col1:
            # Répartition par catégorie
            if stats['par_categorie']:
                st.markdown("#### 🏷️ Fournisseurs par Catégorie")
                categories = list(stats['par_categorie'].keys())
                valeurs = list(stats['par_categorie'].values())
                
                fig_cat = px.pie(
                    values=valeurs, 
                    names=categories, 
                    title="Répartition par Catégorie"
                )
                fig_cat.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', 
                    paper_bgcolor='rgba(0,0,0,0)',
                    title_x=0.5
                )
                st.plotly_chart(fig_cat, use_container_width=True)
        
        with graph_col2:
            # Top performers
            if stats['top_performers']:
                st.markdown("#### 🏆 Top Fournisseurs")
                df_top = pd.DataFrame(stats['top_performers'])
                if not df_top.empty:
                    fig_top = px.bar(
                        df_top, 
                        x='nom', 
                        y='montant_total',
                        color='evaluation_qualite',
                        title="Top Fournisseurs (Volume & Qualité)",
                        color_continuous_scale='Viridis'
                    )
                    fig_top.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)', 
                        paper_bgcolor='rgba(0,0,0,0)',
                        title_x=0.5,
                        xaxis_title="Fournisseur",
                        yaxis_title="Montant Total ($)",
                        showlegend=False
                    )
                    st.plotly_chart(fig_top, use_container_width=True)
    
    # Actions rapides
    st.markdown("---")
    st.markdown("#### ⚡ Actions Rapides")
    
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    
    with action_col1:
        if st.button("➕ Nouveau Fournisseur", use_container_width=True, key="dashboard_new_fournisseur"):
            st.session_state.fournisseur_action = "create_fournisseur"
            st.rerun()
    
    with action_col2:
        if st.button("📋 Nouvelle Demande Prix", use_container_width=True, key="dashboard_new_dp"):
            st.info("💡 Consultez l'onglet 'Demande de Prix' pour créer une nouvelle DP.")
    
    with action_col3:
        if st.button("🛒 Nouveau Bon d'Achat", use_container_width=True, key="dashboard_new_ba"):
            st.info("💡 Consultez l'onglet 'Bon d'Achat' pour créer un nouveau BA.")
    
    with action_col4:
        if st.button("🔄 Actualiser Stats", use_container_width=True, key="dashboard_refresh"):
            st.rerun()

def render_fournisseurs_liste(gestionnaire):
    """Liste et gestion des fournisseurs - VERSION SIMPLIFIÉE"""
    st.markdown("### 📋 Liste des Fournisseurs")
    
    # Bouton d'ajout
    col_add, _ = st.columns([1, 3])
    with col_add:
        if st.button("➕ Nouveau Fournisseur", use_container_width=True, key="liste_create_fournisseur_btn"):
            st.session_state.fournisseur_action = "create_fournisseur"
            st.rerun()
    
    # Filtres simplifiés
    with st.expander("🔍 Filtres et Recherche", expanded=False):
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            categories = ['TOUS'] + gestionnaire.get_categories_disponibles()
            category_filter = st.selectbox(
                "Catégorie:", 
                categories,
                index=categories.index(st.session_state.fournisseur_filter_category) if st.session_state.fournisseur_filter_category in categories else 0,
                key="fournisseur_category_filter"
            )
            st.session_state.fournisseur_filter_category = category_filter
        
        with filter_col2:
            recherche = st.text_input("🔍 Rechercher:", placeholder="Nom, code, secteur...", key="fournisseur_search")
    
    # Récupération et filtrage des données
    fournisseurs = gestionnaire.get_all_fournisseurs()
    
    if category_filter != 'TOUS':
        fournisseurs = [f for f in fournisseurs if f.get('categorie_produits', '').upper() == category_filter.upper()]
    
    if recherche:
        terme = recherche.lower()
        fournisseurs = [f for f in fournisseurs if
            terme in str(f.get('nom', '')).lower() or
            terme in str(f.get('code_fournisseur', '')).lower() or
            terme in str(f.get('secteur', '')).lower() or
            terme in str(f.get('categorie_produits', '')).lower()
        ]
    
    if not fournisseurs:
        st.info("Aucun fournisseur ne correspond aux critères de recherche.")
        return
    
    st.markdown(f"**{len(fournisseurs)} fournisseur(s) trouvé(s)**")
    
    # Tableau des fournisseurs simplifié
    df_data = []
    for f in fournisseurs:
        evaluation_display = f"⭐ {f.get('evaluation_qualite', 0)}/10"
        
        df_data.append({
            '🆔': f.get('id', ''),
            '🏪 Nom': f.get('nom', 'N/A'),
            '📋 Code': f.get('code_fournisseur', 'N/A'),
            '🏷️ Catégorie': f.get('categorie_produits', 'N/A'),
            '⭐ Évaluation': evaluation_display,
            '📦 Délai (j)': f.get('delai_livraison_moyen', 0),
            '💰 Total Commandes': f"{f.get('montant_total_commandes', 0):,.0f} $",
            '📊 Nb Commandes': f.get('nombre_commandes', 0)
        })
    
    st.dataframe(pd.DataFrame(df_data), use_container_width=True)
    
    # Actions sur un fournisseur
    if fournisseurs:
        st.markdown("---")
        st.markdown("#### 🔧 Actions sur un Fournisseur")
        
        selected_fournisseur_id = st.selectbox(
            "Sélectionner un fournisseur:",
            options=[f.get('id') for f in fournisseurs],
            format_func=lambda fid: next((f.get('nom', 'N/A') for f in fournisseurs if f.get('id') == fid), ''),
            key="fournisseur_action_select"
        )
        
        if selected_fournisseur_id:
            action_col1, action_col2, action_col3, action_col4, action_col5 = st.columns(5)
            
            with action_col1:
                if st.button("👁️ Voir Détails", use_container_width=True, key=f"liste_view_fournisseur_{selected_fournisseur_id}"):
                    st.session_state.selected_fournisseur_id = selected_fournisseur_id
                    st.session_state.fournisseur_action = "view_fournisseur_details"
                    st.rerun()
            
            with action_col2:
                if st.button("✏️ Modifier", use_container_width=True, key=f"liste_edit_fournisseur_{selected_fournisseur_id}"):
                    st.session_state.selected_fournisseur_id = selected_fournisseur_id
                    st.session_state.fournisseur_action = "edit_fournisseur"
                    st.rerun()
            
            with action_col3:
                if st.button("📋 Demande Prix", use_container_width=True, key=f"liste_dp_fournisseur_{selected_fournisseur_id}"):
                    # Pré-sélectionner le fournisseur dans l'onglet DP
                    st.session_state.preselected_fournisseur_id = selected_fournisseur_id
                    st.info("💡 Consultez l'onglet 'Demande de Prix' - Fournisseur pré-sélectionné !")
            
            with action_col4:
                if st.button("🛒 Bon d'Achat", use_container_width=True, key=f"liste_ba_fournisseur_{selected_fournisseur_id}"):
                    # Pré-sélectionner le fournisseur dans l'onglet BA
                    st.session_state.preselected_fournisseur_id = selected_fournisseur_id
                    st.info("💡 Consultez l'onglet 'Bon d'Achat' - Fournisseur pré-sélectionné !")
            
            with action_col5:
                if st.button("🗑️ Supprimer", use_container_width=True, key=f"liste_delete_fournisseur_{selected_fournisseur_id}"):
                    # Demander confirmation avant suppression
                    if st.session_state.get(f'confirm_delete_{selected_fournisseur_id}', False):
                        if gestionnaire.delete_fournisseur(selected_fournisseur_id):
                            st.success("Fournisseur supprimé avec succès !")
                            if f'confirm_delete_{selected_fournisseur_id}' in st.session_state:
                                del st.session_state[f'confirm_delete_{selected_fournisseur_id}']
                            st.rerun()
                        else:
                            st.error("Erreur lors de la suppression.")
                    else:
                        st.session_state[f'confirm_delete_{selected_fournisseur_id}'] = True
                        st.warning("⚠️ Cliquez à nouveau pour confirmer la suppression définitive.")
                        st.rerun()

def render_fournisseurs_performance(gestionnaire):
    """Analyse des performances des fournisseurs - VERSION SIMPLIFIÉE"""
    st.markdown("### 📈 Analyse des Performances")
    
    fournisseurs = gestionnaire.get_all_fournisseurs()
    
    if not fournisseurs:
        st.info("Aucun fournisseur disponible pour l'analyse.")
        return
    
    # Sélection du fournisseur et période
    perf_col1, perf_col2 = st.columns(2)
    
    with perf_col1:
        selected_fournisseur_id = st.selectbox(
            "Fournisseur à analyser:",
            options=[f.get('id') for f in fournisseurs],
            format_func=lambda fid: next((f.get('nom', 'N/A') for f in fournisseurs if f.get('id') == fid), ''),
            key="performance_fournisseur_select"
        )
    
    with perf_col2:
        periode_jours = st.selectbox(
            "Période d'analyse:",
            options=[30, 90, 180, 365, 730],
            format_func=lambda d: f"{d} jours" if d < 365 else f"{d//365} an(s)",
            index=3,  # 365 jours par défaut
            key="performance_periode_select"
        )
    
    if selected_fournisseur_id:
        # Récupération des données de performance
        performance = gestionnaire.get_fournisseur_performance(selected_fournisseur_id, periode_jours)
        fournisseur_info = gestionnaire.get_fournisseur_by_id(selected_fournisseur_id)
        
        if not performance:
            st.warning("Aucune donnée de performance disponible pour cette période.")
            return
        
        # Affichage du nom du fournisseur
        st.markdown(f"#### 🏪 {fournisseur_info.get('nom', 'N/A')} - {periode_jours} derniers jours")
        
        # Métriques de performance
        perf_met_col1, perf_met_col2, perf_met_col3, perf_met_col4 = st.columns(4)
        
        with perf_met_col1:
            st.metric("📦 Total Commandes", performance.get('total_commandes', 0))
        with perf_met_col2:
            montant_total = performance.get('montant_total', 0) or 0
            st.metric("💰 Montant Total", f"{montant_total:,.0f} $")
        with perf_met_col3:
            montant_moyen = performance.get('montant_moyen', 0) or 0
            st.metric("📊 Commande Moyenne", f"{montant_moyen:,.0f} $")
        with perf_met_col4:
            taux_ponctualite = performance.get('taux_ponctualite', 0) or 0
            couleur_ponctualite = "normal" if taux_ponctualite >= 90 else "inverse" if taux_ponctualite >= 70 else "off"
            st.metric("⏰ Ponctualité", f"{taux_ponctualite:.1f}%", delta_color=couleur_ponctualite)
        
        # Détails supplémentaires
        if performance.get('total_livraisons', 0) > 0:
            st.markdown("---")
            st.markdown("#### 📊 Détails Livraisons")
            
            detail_col1, detail_col2, detail_col3 = st.columns(3)
            
            with detail_col1:
                st.metric("🚚 Total Livraisons", performance.get('total_livraisons', 0))
            with detail_col2:
                livraisons_temps = performance.get('livraisons_temps', 0)
                st.metric("✅ Livrées à Temps", livraisons_temps)
            with detail_col3:
                retard_moyen = performance.get('retard_moyen_jours', 0) or 0
                if retard_moyen > 0:
                    st.metric("⏱️ Retard Moyen", f"{retard_moyen:.1f} jours", delta_color="inverse")
                else:
                    st.metric("⏱️ Retard Moyen", "0 jour", delta_color="normal")
        
        # Évaluation et notes
        st.markdown("---")
        st.markdown("#### ⭐ Évaluation Qualité")
        
        eval_col1, eval_col2 = st.columns(2)
        
        with eval_col1:
            evaluation_actuelle = fournisseur_info.get('evaluation_qualite', 5)
            st.metric("Note Actuelle", f"{evaluation_actuelle}/10")
            
            # Barre de progression pour l'évaluation
            progress_value = evaluation_actuelle / 10
            st.progress(progress_value)
            
            if evaluation_actuelle >= 8:
                st.success("🏆 Excellent fournisseur")
            elif evaluation_actuelle >= 6:
                st.info("👍 Bon fournisseur")
            else:
                st.warning("⚠️ Fournisseur à surveiller")
        
        with eval_col2:
            if fournisseur_info.get('notes_evaluation'):
                st.markdown("**📝 Notes d'évaluation:**")
                st.markdown(f"_{fournisseur_info['notes_evaluation']}_")
            
            if fournisseur_info.get('certifications'):
                st.markdown("**🏅 Certifications:**")
                st.markdown(f"_{fournisseur_info['certifications']}_")
        
        # Recommandations automatiques
        st.markdown("---")
        st.markdown("#### 💡 Recommandations")
        
        recommendations = []
        
        if taux_ponctualite < 70:
            recommendations.append("🚨 Ponctualité faible - Renégocier les délais de livraison")
        elif taux_ponctualite < 90:
            recommendations.append("⚠️ Ponctualité moyenne - Suivre de près les prochaines livraisons")
        
        if evaluation_actuelle < 6:
            recommendations.append("📉 Note qualité faible - Prévoir une évaluation approfondie")
        
        if performance.get('total_commandes', 0) == 0:
            recommendations.append("📦 Aucune commande récente - Évaluer la pertinence du partenariat")
        
        if not recommendations:
            recommendations.append("✅ Performance satisfaisante - Continuer le partenariat")
        
        for rec in recommendations:
            st.markdown(f"• {rec}")

def render_fournisseurs_categories(gestionnaire):
    """Gestion par catégories de fournisseurs - VERSION SIMPLIFIÉE"""
    st.markdown("### 🏷️ Gestion par Catégories")
    
    categories = gestionnaire.get_categories_disponibles()
    
    if not categories:
        st.info("Aucune catégorie de fournisseurs définie.")
        st.markdown("💡 Les catégories sont créées automatiquement lors de l'ajout de fournisseurs.")
        return
    
    # Statistiques par catégorie
    cat_col1, cat_col2 = st.columns(2)
    
    with cat_col1:
        st.markdown("#### 📊 Répartition par Catégorie")
        
        cat_stats = {}
        for category in categories:
            fournisseurs_cat = gestionnaire.get_fournisseurs_by_category(category)
            cat_stats[category] = len(fournisseurs_cat)
        
        # Graphique en barres
        if cat_stats:
            fig_cat_bar = px.bar(
                x=list(cat_stats.keys()),
                y=list(cat_stats.values()),
                title="Nombre de Fournisseurs par Catégorie",
                labels={'x': 'Catégorie', 'y': 'Nombre de Fournisseurs'}
            )
            fig_cat_bar.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                title_x=0.5
            )
            st.plotly_chart(fig_cat_bar, use_container_width=True)
    
    with cat_col2:
        st.markdown("#### 🔍 Explorer par Catégorie")
        
        selected_category = st.selectbox(
            "Sélectionner une catégorie:",
            categories,
            key="category_explorer_select"
        )
        
        if selected_category:
            fournisseurs_cat = gestionnaire.get_fournisseurs_by_category(selected_category)
            
            st.markdown(f"**{len(fournisseurs_cat)} fournisseur(s) dans '{selected_category}'**")
            
            for fournisseur in fournisseurs_cat:
                with st.container():
                    st.markdown(f"""
                    <div style='border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin: 0.5rem 0; background-color: #f9f9f9;'>
                        <h5 style='margin: 0 0 0.5rem 0;'>🏪 {fournisseur.get('nom', 'N/A')}</h5>
                        <p style='margin: 0; color: #666;'>
                            <strong>Secteur:</strong> {fournisseur.get('secteur', 'N/A')} | 
                            <strong>Évaluation:</strong> ⭐ {fournisseur.get('evaluation_qualite', 0)}/10
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Liste détaillée des catégories
    st.markdown("---")
    st.markdown("#### 📋 Vue d'Ensemble des Catégories")
    
    categories_data = []
    for category in categories:
        fournisseurs_cat = gestionnaire.get_fournisseurs_by_category(category)
        
        if fournisseurs_cat:
            evaluations = [f.get('evaluation_qualite', 0) for f in fournisseurs_cat if f.get('evaluation_qualite')]
            eval_moyenne = sum(evaluations) / len(evaluations) if evaluations else 0
            
            delais = [f.get('delai_livraison_moyen', 0) for f in fournisseurs_cat if f.get('delai_livraison_moyen')]
            delai_moyen = sum(delais) / len(delais) if delais else 0
            
            categories_data.append({
                '🏷️ Catégorie': category,
                '🏪 Nb Fournisseurs': len(fournisseurs_cat),
                '⭐ Éval. Moyenne': f"{eval_moyenne:.1f}/10",
                '📦 Délai Moyen': f"{delai_moyen:.0f} jours"
            })
    
    if categories_data:
        st.dataframe(pd.DataFrame(categories_data), use_container_width=True)

def render_fournisseur_form(gestionnaire, fournisseur_data=None):
    """Formulaire de création/modification d'un fournisseur - VERSION NETTOYÉE"""
    is_edit = fournisseur_data is not None
    title = "✏️ Modifier Fournisseur" if is_edit else "➕ Nouveau Fournisseur"
    
    st.markdown(f"<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(f"### {title}")
    
    with st.form("fournisseur_form", clear_on_submit=not is_edit):
        # Sélection de l'entreprise (obligatoire)
        companies = st.session_state.erp_db.get_companies_by_type()
        
        if is_edit:
            current_company_id = fournisseur_data.get('company_id')
            company_options = [(c['id'], c['nom']) for c in companies]
            default_index = next((i for i, (cid, _) in enumerate(company_options) if cid == current_company_id), 0)
        else:
            company_options = [(c['id'], c['nom']) for c in companies]
            default_index = 0
        
        if not company_options:
            st.error("Aucune entreprise disponible. Créez d'abord une entreprise dans le module CRM.")
            st.stop()
        
        selected_company_id = st.selectbox(
            "Entreprise *:",
            options=[cid for cid, _ in company_options],
            format_func=lambda cid: next((nom for id_c, nom in company_options if id_c == cid), ""),
            index=default_index,
            help="Sélectionnez l'entreprise à associer comme fournisseur"
        )
        
        # Informations fournisseur
        col1, col2 = st.columns(2)
        
        with col1:
            # CODE FOURNISSEUR AUTOMATIQUE
            if is_edit:
                code_fournisseur = fournisseur_data.get('code_fournisseur', '')
                st.text_input(
                    "Code Fournisseur:",
                    value=code_fournisseur,
                    disabled=True,
                    help="Code généré automatiquement lors de la création"
                )
            else:
                code_fournisseur = gestionnaire.generate_fournisseur_code()
                st.text_input(
                    "Code Fournisseur:",
                    value=code_fournisseur,
                    disabled=True,
                    help="Code généré automatiquement"
                )
            
            # CATÉGORIE NON OBLIGATOIRE
            categorie_produits = st.text_input(
                "Catégorie de Produits:",
                value=fournisseur_data.get('categorie_produits', '') if is_edit else '',
                help="Ex: Métallurgie, Électronique, Consommables... (Optionnel)"
            )
            
            delai_livraison = st.number_input(
                "Délai de Livraison (jours):",
                min_value=1,
                max_value=365,
                value=fournisseur_data.get('delai_livraison_moyen', 14) if is_edit else 14,
                help="Délai moyen de livraison en jours"
            )
            
            evaluation_qualite = st.slider(
                "Évaluation Qualité:",
                min_value=1,
                max_value=10,
                value=fournisseur_data.get('evaluation_qualite', 5) if is_edit else 5,
                help="Note sur 10 pour la qualité du fournisseur"
            )
        
        with col2:
            conditions_paiement = st.text_input(
                "Conditions de Paiement:",
                value=fournisseur_data.get('conditions_paiement', '30 jours net') if is_edit else '30 jours net',
                help="Ex: 30 jours net, Comptant, 60 jours fin de mois..."
            )
            
            contact_commercial = st.text_input(
                "Contact Commercial:",
                value=fournisseur_data.get('contact_commercial', '') if is_edit else '',
                help="Nom du contact commercial principal"
            )
            
            contact_technique = st.text_input(
                "Contact Technique:",
                value=fournisseur_data.get('contact_technique', '') if is_edit else '',
                help="Nom du contact technique principal"
            )
        
        # Champs texte longs
        certifications = st.text_area(
            "Certifications:",
            value=fournisseur_data.get('certifications', '') if is_edit else '',
            help="Liste des certifications du fournisseur (ISO, etc.)"
        )
        
        notes_evaluation = st.text_area(
            "Notes d'Évaluation:",
            value=fournisseur_data.get('notes_evaluation', '') if is_edit else '',
            help="Notes et commentaires sur le fournisseur"
        )
        
        # Boutons
        st.markdown("---")
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            submit_label = "💾 Sauvegarder" if is_edit else "➕ Créer Fournisseur"
            submitted = st.form_submit_button(submit_label, use_container_width=True)
        
        with btn_col2:
            cancelled = st.form_submit_button("❌ Annuler", use_container_width=True)
        
        # Traitement du formulaire
        if submitted:
            if not code_fournisseur:
                st.error("Erreur de génération du code fournisseur.")
            else:
                # Préparation des données (sans est_actif)
                fournisseur_form_data = {
                    'code_fournisseur': code_fournisseur,
                    'categorie_produits': categorie_produits if categorie_produits else None,
                    'delai_livraison_moyen': delai_livraison,
                    'conditions_paiement': conditions_paiement,
                    'evaluation_qualite': evaluation_qualite,
                    'contact_commercial': contact_commercial,
                    'contact_technique': contact_technique,
                    'certifications': certifications,
                    'notes_evaluation': notes_evaluation
                }
                
                # Création ou modification
                if is_edit:
                    success = gestionnaire.update_fournisseur(fournisseur_data['id'], fournisseur_form_data)
                    if success:
                        st.success("✅ Fournisseur modifié avec succès !")
                        st.session_state.fournisseur_action = None
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la modification.")
                else:
                    new_id = gestionnaire.create_fournisseur(selected_company_id, fournisseur_form_data)
                    if new_id:
                        st.success(f"✅ Fournisseur créé avec succès ! (ID: {new_id}, Code: {code_fournisseur})")
                        st.session_state.fournisseur_action = None
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la création.")
        
        if cancelled:
            st.session_state.fournisseur_action = None
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

def render_fournisseur_details(gestionnaire, fournisseur_data):
    """Affichage détaillé d'un fournisseur - VERSION NETTOYÉE"""
    if not fournisseur_data:
        st.error("Fournisseur non trouvé.")
        return
    
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(f"### 🏪 {fournisseur_data.get('nom', 'N/A')}")
    
    # Bouton fermer
    if st.button("✖️ Fermer", key="close_fournisseur_details"):
        st.session_state.fournisseur_action = None
        st.rerun()
    
    # Informations générales
    st.markdown("#### 📋 Informations Générales")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.markdown(f"""
        **🆔 ID Fournisseur:** {fournisseur_data.get('id', 'N/A')}
        
        **📋 Code:** {fournisseur_data.get('code_fournisseur', 'N/A')}
        
        **🏷️ Catégorie:** {fournisseur_data.get('categorie_produits', 'N/A')}
        
        **🏢 Secteur:** {fournisseur_data.get('secteur', 'N/A')}
        """)
    
    with info_col2:
        st.markdown(f"""
        **⭐ Évaluation:** {fournisseur_data.get('evaluation_qualite', 0)}/10
        
        **📦 Délai Livraison:** {fournisseur_data.get('delai_livraison_moyen', 0)} jours
        
        **💳 Conditions Paiement:** {fournisseur_data.get('conditions_paiement', 'N/A')}
        
        **👨‍💼 Contact Commercial:** {fournisseur_data.get('contact_commercial', 'N/A')}
        
        **🔧 Contact Technique:** {fournisseur_data.get('contact_technique', 'N/A')}
        """)
    
    # Informations entreprise
    st.markdown("---")
    st.markdown("#### 🏢 Informations Entreprise")
    
    entreprise_col1, entreprise_col2 = st.columns(2)
    
    with entreprise_col1:
        st.markdown(f"""
        **🏢 Nom:** {fournisseur_data.get('nom', 'N/A')}
        
        **📍 Adresse:** {fournisseur_data.get('adresse', 'N/A')}
        """)
    
    with entreprise_col2:
        st.markdown(f"""
        **🌐 Site Web:** {fournisseur_data.get('site_web', 'N/A')}
        
        **📝 Notes Entreprise:** {fournisseur_data.get('company_notes', 'N/A')}
        """)
    
    # Certifications et évaluations
    if fournisseur_data.get('certifications') or fournisseur_data.get('notes_evaluation'):
        st.markdown("---")
        st.markdown("#### 🏅 Certifications et Évaluations")
        
        if fournisseur_data.get('certifications'):
            st.markdown("**🏅 Certifications:**")
            st.markdown(f"_{fournisseur_data['certifications']}_")
        
        if fournisseur_data.get('notes_evaluation'):
            st.markdown("**📝 Notes d'Évaluation:**")
            st.markdown(f"_{fournisseur_data['notes_evaluation']}_")
    
    # Performance rapide
    st.markdown("---")
    st.markdown("#### 📊 Performance (365 derniers jours)")
    
    performance = gestionnaire.get_fournisseur_performance(fournisseur_data['id'], 365)
    
    if performance:
        perf_col1, perf_col2, perf_col3 = st.columns(3)
        
        with perf_col1:
            st.metric("📦 Commandes", performance.get('total_commandes', 0))
        with perf_col2:
            montant = performance.get('montant_total', 0) or 0
            st.metric("💰 Montant Total", f"{montant:,.0f} $")
        with perf_col3:
            ponctualite = performance.get('taux_ponctualite', 0) or 0
            st.metric("⏰ Ponctualité", f"{ponctualite:.1f}%")
    else:
        st.info("Aucune donnée de performance disponible.")
    
    # Actions rapides
    st.markdown("---")
    st.markdown("#### ⚡ Actions Rapides")
    
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    
    with action_col1:
        if st.button("✏️ Modifier", use_container_width=True, key="details_edit_from_details"):
            st.session_state.fournisseur_action = "edit_fournisseur"
            st.rerun()
    
    with action_col2:
        if st.button("📊 Voir Performance", use_container_width=True, key="details_perf_from_details"):
            st.info("💡 Consultez l'onglet 'Performances' pour l'analyse complète.")
    
    with action_col3:
        if st.button("📋 Créer Demande Prix", use_container_width=True, key="details_create_dp_from_details"):
            st.session_state.preselected_fournisseur_id = fournisseur_data.get('id')
            st.info("💡 Consultez l'onglet 'Demande de Prix' - Fournisseur pré-sélectionné !")
    
    with action_col4:
        if st.button("🛒 Créer Bon d'Achat", use_container_width=True, key="details_create_ba_from_details"):
            st.session_state.preselected_fournisseur_id = fournisseur_data.get('id')
            st.info("💡 Consultez l'onglet 'Bon d'Achat' - Fournisseur pré-sélectionné !")
    
    st.markdown("</div>", unsafe_allow_html=True)
