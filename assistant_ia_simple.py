# assistant_ia_simple.py - Module Assistant IA Expert sans dépendances externes
# Version simplifiée qui utilise uniquement les modules déjà présents dans l'ERP

import streamlit as st
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from anthropic import Anthropic

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AssistantIASimple:
    """
    Assistant IA avec interface élégante et accès à la base de données ERP
    Version simplifiée sans dépendances externes
    """
    
    def __init__(self, db=None, api_key: Optional[str] = None):
        """
        Initialise l'assistant IA
        
        Args:
            db: Instance ERPDatabase pour accéder aux données
            api_key: Clé API Claude
        """
        self.db = db
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('CLAUDE_API_KEY')
        
        if self.api_key:
            try:
                self.client = Anthropic(api_key=self.api_key)
                self.model = "claude-sonnet-4-20250514"
                logger.info("✅ Assistant IA initialisé avec succès")
            except Exception as e:
                logger.error(f"❌ Erreur initialisation Claude: {e}")
                self.client = None
        else:
            logger.warning("⚠️ Clé API Claude non configurée")
            self.client = None
        
        # Initialiser les états de session
        if "ia_messages" not in st.session_state:
            st.session_state.ia_messages = []
        if "ia_conversation_id" not in st.session_state:
            st.session_state.ia_conversation_id = None
    
    # =========================================================================
    # MÉTHODES D'ACCÈS AUX DONNÉES ERP
    # =========================================================================
    
    def _search_erp_data(self, query: str) -> Dict[str, Any]:
        """Recherche dans les données ERP"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        results = {}
        query_lower = query.lower()
        
        try:
            # Recherche projets
            if any(word in query_lower for word in ['projet', 'project', 'chantier']):
                projects = self.db.execute_query("""
                    SELECT p.*, c.nom as client_nom 
                    FROM projects p 
                    LEFT JOIN companies c ON p.client_company_id = c.id 
                    WHERE p.nom_projet LIKE ? OR p.description LIKE ?
                    LIMIT 5
                """, (f'%{query}%', f'%{query}%'))
                
                if projects:
                    # Valider les données avant de les ajouter
                    validated_projects = []
                    for p in projects:
                        if p.get('nom_projet'):  # S'assurer que le projet a un nom
                            validated_projects.append(dict(p))
                    if validated_projects:
                        results['projets'] = validated_projects
            
            # Recherche produits
            if any(word in query_lower for word in ['produit', 'product', 'article', 'référence']):
                produits = self.db.execute_query("""
                    SELECT code_produit, nom, categorie, materiau, nuance, 
                           dimensions, unite_vente, prix_unitaire, 
                           stock_disponible, stock_minimum, fournisseur_principal
                    FROM produits 
                    WHERE actif = 1 AND (
                        nom LIKE ? OR code_produit LIKE ? OR 
                        description LIKE ? OR materiau LIKE ?
                    )
                    LIMIT 5
                """, (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
                
                if produits:
                    results['produits'] = [dict(prod) for prod in produits]
            
            # Recherche inventaire
            if any(word in query_lower for word in ['stock', 'inventaire', 'matériel']):
                items = self.db.execute_query("""
                    SELECT nom, quantite_metric, statut 
                    FROM inventory_items 
                    WHERE nom LIKE ? OR description LIKE ?
                    LIMIT 5
                """, (f'%{query}%', f'%{query}%'))
                
                if items:
                    results['inventaire'] = [dict(item) for item in items]
            
            # Recherche employés
            if any(word in query_lower for word in ['employé', 'personnel', 'équipe']):
                employees = self.db.execute_query("""
                    SELECT e.nom, e.prenom, e.poste, e.departement, e.statut,
                           GROUP_CONCAT(ec.nom_competence || ' (' || ec.niveau || ')', ', ') as competences
                    FROM employees e
                    LEFT JOIN employee_competences ec ON e.id = ec.employee_id
                    WHERE e.nom LIKE ? OR e.prenom LIKE ? OR e.poste LIKE ?
                    GROUP BY e.id, e.nom, e.prenom, e.poste, e.departement, e.statut
                    LIMIT 5
                """, (f'%{query}%', f'%{query}%', f'%{query}%'))
                
                if employees:
                    results['employes'] = [dict(emp) for emp in employees]
            
            # Recherche clients
            if any(word in query_lower for word in ['client', 'entreprise']):
                companies = self.db.execute_query("""
                    SELECT nom, secteur, ville 
                    FROM companies 
                    WHERE nom LIKE ? OR secteur LIKE ?
                    LIMIT 5
                """, (f'%{query}%', f'%{query}%'))
                
                if companies:
                    results['entreprises'] = [dict(comp) for comp in companies]
            
            # Recherche bons de travail
            if any(word in query_lower for word in ['bon', 'bt', 'travail']):
                bts = self.db.execute_query("""
                    SELECT f.numero_document, f.statut, f.priorite, f.created_at, 
                           f.metadonnees_json, f.notes,
                           (SELECT fl.description FROM formulaire_lignes fl 
                            WHERE fl.formulaire_id = f.id 
                            ORDER BY fl.sequence_ligne LIMIT 1) as premiere_ligne
                    FROM formulaires f 
                    WHERE f.type_formulaire = 'BON_TRAVAIL' 
                    AND (f.numero_document LIKE ? OR f.notes LIKE ?)
                    ORDER BY f.created_at DESC
                    LIMIT 5
                """, (f'%{query}%', f'%{query}%'))
                
                if bts:
                    # Traiter les métadonnées JSON pour extraire le titre
                    bons_travail = []
                    for bt in bts:
                        bt_dict = dict(bt)
                        if bt_dict.get('metadonnees_json'):
                            try:
                                meta = json.loads(bt_dict['metadonnees_json'])
                                bt_dict['titre'] = meta.get('project_name', 'Sans titre')
                                bt_dict['client'] = meta.get('client_name', 'N/A')
                            except:
                                bt_dict['titre'] = bt_dict.get('premiere_ligne', 'Sans titre')
                                bt_dict['client'] = 'N/A'
                        else:
                            bt_dict['titre'] = bt_dict.get('premiere_ligne', 'Sans titre')
                            bt_dict['client'] = 'N/A'
                        bons_travail.append(bt_dict)
                    results['bons_travail'] = bons_travail
            
            # Recherche devis
            if any(word in query_lower for word in ['devis', 'quote', 'estimation']):
                devis = self.db.execute_query("""
                    SELECT f.numero_document, f.statut, f.priorite, f.created_at, 
                           f.metadonnees_json, f.notes, f.montant_total,
                           (SELECT fl.description FROM formulaire_lignes fl 
                            WHERE fl.formulaire_id = f.id 
                            ORDER BY fl.sequence_ligne LIMIT 1) as premiere_ligne
                    FROM formulaires f 
                    WHERE f.type_formulaire = 'ESTIMATION' 
                    AND (f.numero_document LIKE ? OR f.notes LIKE ?)
                    ORDER BY f.created_at DESC
                    LIMIT 5
                """, (f'%{query}%', f'%{query}%'))
                
                if devis:
                    # Traiter les métadonnées JSON pour extraire le titre
                    devis_list = []
                    for d in devis:
                        d_dict = dict(d)
                        if d_dict.get('metadonnees_json'):
                            try:
                                meta = json.loads(d_dict['metadonnees_json'])
                                d_dict['titre'] = meta.get('project_name', meta.get('objet', 'Sans titre'))
                                d_dict['client'] = meta.get('client_name', 'N/A')
                            except:
                                d_dict['titre'] = d_dict.get('premiere_ligne', 'Sans titre')
                                d_dict['client'] = 'N/A'
                        else:
                            d_dict['titre'] = d_dict.get('premiere_ligne', 'Sans titre')
                            d_dict['client'] = 'N/A'
                        devis_list.append(d_dict)
                    results['devis'] = devis_list
            
            # Recherche contacts
            if any(word in query_lower for word in ['contact', 'personne', 'responsable']):
                contacts = self.db.execute_query("""
                    SELECT c.*, comp.nom as entreprise_nom
                    FROM contacts c
                    LEFT JOIN companies comp ON c.company_id = comp.id
                    WHERE c.nom_famille LIKE ? OR c.prenom LIKE ? 
                    OR c.email LIKE ? OR comp.nom LIKE ?
                    ORDER BY c.nom_famille, c.prenom
                    LIMIT 10
                """, (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
                
                if contacts:
                    results['contacts'] = [dict(c) for c in contacts]
            
        except Exception as e:
            logger.error(f"Erreur recherche ERP: {e}")
            results['error'] = str(e)
        
        return results
    
    def _get_bt_details(self, numero_bt: str) -> Dict[str, Any]:
        """Récupère les détails complets d'un bon de travail"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            # Récupérer les infos principales du BT
            bt_info = self.db.execute_query("""
                SELECT f.*, p.nom_projet
                FROM formulaires f
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE f.numero_document = ? AND f.type_formulaire = 'BON_TRAVAIL'
            """, (numero_bt,))
            
            if not bt_info:
                return {"error": f"Bon de travail {numero_bt} non trouvé"}
            
            bt = dict(bt_info[0])
            
            # Parser les métadonnées JSON
            if bt.get('metadonnees_json'):
                try:
                    meta = json.loads(bt['metadonnees_json'])
                    bt['titre'] = meta.get('project_name', bt.get('nom_projet', 'Sans titre'))
                    bt['client'] = meta.get('client_name', 'N/A')
                except:
                    bt['titre'] = bt.get('nom_projet', 'Sans titre')
                    bt['client'] = 'N/A'
            
            # Récupérer les lignes/opérations du BT
            lignes = self.db.execute_query("""
                SELECT fl.*, p.nom as nom_produit
                FROM formulaire_lignes fl
                LEFT JOIN produits p ON fl.code_article = p.code_produit
                WHERE fl.formulaire_id = ?
                ORDER BY fl.sequence_ligne
            """, (bt['id'],))
            
            bt['operations'] = [dict(ligne) for ligne in lignes] if lignes else []
            
            # Récupérer les assignations d'employés
            assignations = self.db.execute_query("""
                SELECT ba.*, e.nom, e.prenom, e.poste
                FROM bt_assignations ba
                JOIN employees e ON ba.employe_id = e.id
                WHERE ba.bt_id = ?
            """, (bt['id'],))
            
            bt['assignations'] = [dict(a) for a in assignations] if assignations else []
            
            # Récupérer les réservations de postes
            reservations = self.db.execute_query("""
                SELECT br.*, wc.nom as nom_poste
                FROM bt_reservations_postes br
                JOIN work_centers wc ON br.work_center_id = wc.id
                WHERE br.bt_id = ?
            """, (bt['id'],))
            
            bt['reservations_postes'] = [dict(r) for r in reservations] if reservations else []
            
            # Récupérer l'avancement
            avancement = self.db.execute_query("""
                SELECT ba.*, e.nom, e.prenom
                FROM bt_avancement ba
                LEFT JOIN employees e ON ba.updated_by = e.id
                WHERE ba.bt_id = ?
                ORDER BY ba.updated_at DESC
            """, (bt['id'],))
            
            bt['avancement'] = [dict(a) for a in avancement] if avancement else []
            
            return {"bt_details": bt}
            
        except Exception as e:
            logger.error(f"Erreur récupération détails BT: {e}")
            return {"error": str(e)}
    
    def _get_devis_details(self, numero_devis: str) -> Dict[str, Any]:
        """Récupère les détails complets d'un devis"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            # Récupérer les infos principales du devis
            devis_info = self.db.execute_query("""
                SELECT f.*, c.nom as client_nom
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                WHERE f.numero_document = ? AND f.type_formulaire = 'ESTIMATION'
            """, (numero_devis,))
            
            if not devis_info:
                return {"error": f"Devis {numero_devis} non trouvé"}
            
            devis = dict(devis_info[0])
            
            # Parser les métadonnées JSON
            if devis.get('metadonnees_json'):
                try:
                    meta = json.loads(devis['metadonnees_json'])
                    devis['titre'] = meta.get('objet', meta.get('project_name', 'Sans titre'))
                    devis['client'] = meta.get('client_name', devis.get('client_nom', 'N/A'))
                    devis['validite'] = meta.get('validite_jours', 30)
                    devis['conditions'] = meta.get('conditions_paiement', 'Net 30 jours')
                except:
                    devis['titre'] = 'Sans titre'
                    devis['client'] = devis.get('client_nom', 'N/A')
            
            # Récupérer les lignes/articles du devis
            lignes = self.db.execute_query("""
                SELECT fl.*, p.nom as nom_produit, p.categorie
                FROM formulaire_lignes fl
                LEFT JOIN produits p ON fl.code_article = p.code_produit
                WHERE fl.formulaire_id = ?
                ORDER BY fl.sequence_ligne
            """, (devis['id'],))
            
            devis['lignes'] = [dict(ligne) for ligne in lignes] if lignes else []
            
            # Calculer les totaux
            sous_total = sum(ligne.get('montant_ligne', 0) for ligne in devis['lignes'])
            devis['sous_total'] = sous_total
            
            # Récupérer les validations si existantes
            validations = self.db.execute_query("""
                SELECT v.*, e.nom, e.prenom
                FROM formulaire_validations v
                LEFT JOIN employees e ON v.employee_id = e.id
                WHERE v.formulaire_id = ?
                ORDER BY v.date_validation DESC
            """, (devis['id'],))
            
            devis['validations'] = [dict(v) for v in validations] if validations else []
            
            return {"devis_details": devis}
            
        except Exception as e:
            logger.error(f"Erreur récupération détails devis: {e}")
            return {"error": str(e)}
    
    def _get_projet_details(self, numero_projet: str) -> Dict[str, Any]:
        """Récupère les détails complets d'un projet"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            # Récupérer les infos principales du projet
            projet_info = self.db.execute_query("""
                SELECT p.*, c.nom as client_nom
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE p.id = ?
            """, (numero_projet,))
            
            if not projet_info:
                return {"error": f"Projet {numero_projet} non trouvé"}
            
            projet = dict(projet_info[0])
            
            # Les tables project_etapes, project_assignations et project_ressources n'existent pas
            # On initialise avec des listes vides
            projet['etapes'] = []
            projet['assignations'] = []
            projet['ressources'] = []
            
            # Récupérer les documents associés (BT, Devis, etc.)
            documents = self.db.execute_query("""
                SELECT numero_document, type_formulaire, statut, created_at
                FROM formulaires
                WHERE project_id = ?
                ORDER BY created_at DESC
            """, (projet['id'],))
            
            projet['documents'] = [dict(d) for d in documents] if documents else []
            
            return {"projet_details": projet}
            
        except Exception as e:
            logger.error(f"Erreur récupération détails projet: {e}")
            return {"error": str(e)}
    
    def _get_dp_details(self, numero_dp: str) -> Dict[str, Any]:
        """Récupère les détails complets d'une demande de prix"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            # Récupérer les infos principales de la demande de prix
            dp_info = self.db.execute_query("""
                SELECT f.*, c.nom as fournisseur_nom
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                WHERE f.numero_document = ? AND f.type_formulaire = 'DEMANDE_PRIX'
            """, (numero_dp,))
            
            if not dp_info:
                return {"error": f"Demande de prix {numero_dp} non trouvée"}
            
            dp = dict(dp_info[0])
            
            # Parser les métadonnées JSON
            if dp.get('metadonnees_json'):
                try:
                    meta = json.loads(dp['metadonnees_json'])
                    dp['objet'] = meta.get('objet', 'Sans objet')
                    dp['fournisseur'] = meta.get('fournisseur_name', dp.get('fournisseur_nom', 'N/A'))
                    dp['delai_reponse'] = meta.get('delai_reponse', '15 jours')
                    dp['conditions_livraison'] = meta.get('conditions_livraison', 'À définir')
                except:
                    dp['objet'] = 'Sans objet'
                    dp['fournisseur'] = dp.get('fournisseur_nom', 'N/A')
            
            # Récupérer les lignes de la demande de prix
            lignes = self.db.execute_query("""
                SELECT fl.*, p.nom as nom_produit, p.categorie
                FROM formulaire_lignes fl
                LEFT JOIN produits p ON fl.code_article = p.code_produit
                WHERE fl.formulaire_id = ?
                ORDER BY fl.sequence_ligne
            """, (dp['id'],))
            
            dp['lignes'] = [dict(ligne) for ligne in lignes] if lignes else []
            
            # Les réponses fournisseur ne sont pas stockées dans une table séparée
            # On initialise avec une liste vide
            dp['reponses'] = []
            
            return {"dp_details": dp}
            
        except Exception as e:
            logger.error(f"Erreur récupération détails demande de prix: {e}")
            return {"error": str(e)}
    
    def _get_ba_details(self, numero_ba: str) -> Dict[str, Any]:
        """Récupère les détails complets d'un bon d'achat"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            # Récupérer les infos principales du bon d'achat
            ba_info = self.db.execute_query("""
                SELECT f.*, c.nom as fournisseur_nom, p.nom_projet
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE f.numero_document = ? AND f.type_formulaire = 'BON_ACHAT'
            """, (numero_ba,))
            
            if not ba_info:
                return {"error": f"Bon d'achat {numero_ba} non trouvé"}
            
            ba = dict(ba_info[0])
            
            # Parser les métadonnées JSON
            if ba.get('metadonnees_json'):
                try:
                    meta = json.loads(ba['metadonnees_json'])
                    ba['objet'] = meta.get('objet', 'Sans objet')
                    ba['fournisseur'] = meta.get('fournisseur_name', ba.get('fournisseur_nom', 'N/A'))
                    ba['conditions_paiement'] = meta.get('conditions_paiement', '30 jours net')
                    ba['mode_livraison'] = meta.get('mode_livraison', 'À définir')
                except:
                    ba['objet'] = 'Sans objet'
                    ba['fournisseur'] = ba.get('fournisseur_nom', 'N/A')
            
            # Récupérer les lignes du bon d'achat
            lignes = self.db.execute_query("""
                SELECT fl.*, p.nom as nom_produit, p.categorie
                FROM formulaire_lignes fl
                LEFT JOIN produits p ON fl.code_article = p.code_produit
                WHERE fl.formulaire_id = ?
                ORDER BY fl.sequence_ligne
            """, (ba['id'],))
            
            ba['lignes'] = [dict(ligne) for ligne in lignes] if lignes else []
            
            # Calculer les totaux
            sous_total = sum(ligne.get('montant_ligne', 0) for ligne in ba['lignes'])
            ba['sous_total'] = sous_total
            
            # Récupérer les informations de livraison si existantes
            livraisons = self.db.execute_query("""
                SELECT * FROM approvisionnements
                WHERE formulaire_id = ?
                ORDER BY date_commande DESC
            """, (ba['id'],))
            
            ba['livraisons'] = [dict(l) for l in livraisons] if livraisons else []
            
            return {"ba_details": ba}
            
        except Exception as e:
            logger.error(f"Erreur récupération détails bon d'achat: {e}")
            return {"error": str(e)}
    
    def _get_employee_hours(self, employee_name: str, week_date: str = None) -> Dict[str, Any]:
        """Récupère les heures travaillées d'un employé pour une semaine donnée avec détails complets"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            # D'abord trouver l'employé
            employee = self.db.execute_query("""
                SELECT id, nom, prenom, poste, departement
                FROM employees
                WHERE LOWER(nom || ' ' || prenom) LIKE LOWER(?)
                   OR LOWER(prenom || ' ' || nom) LIKE LOWER(?)
                   OR LOWER(nom) LIKE LOWER(?)
                   OR LOWER(prenom) LIKE LOWER(?)
                LIMIT 1
            """, (f'%{employee_name}%', f'%{employee_name}%', f'%{employee_name}%', f'%{employee_name}%'))
            
            if not employee:
                return {"error": f"Employé '{employee_name}' non trouvé"}
            
            emp = dict(employee[0])
            
            # Déterminer la période (semaine actuelle par défaut)
            if week_date:
                # Parser la date fournie
                from datetime import datetime, timedelta
                try:
                    if week_date.lower() == 'semaine dernière':
                        ref_date = datetime.now() - timedelta(days=7)
                    else:
                        ref_date = datetime.strptime(week_date, '%Y-%m-%d')
                except:
                    ref_date = datetime.now()
            else:
                from datetime import datetime
                ref_date = datetime.now()
            
            # Calculer le début et la fin de la semaine
            from datetime import timedelta
            weekday = ref_date.weekday()
            start_week = ref_date - timedelta(days=weekday)
            end_week = start_week + timedelta(days=6)
            
            # Format pour SQL
            start_str = start_week.strftime('%Y-%m-%d 00:00:00')
            end_str = end_week.strftime('%Y-%m-%d 23:59:59')
            
            # Récupérer les entrées de temps avec tous les détails
            time_entries = self.db.execute_query("""
                SELECT te.*, 
                       p.nom_projet, p.statut as projet_statut, p.client_company_id,
                       comp.nom as client_nom,
                       f.numero_document as bt_numero, f.statut as bt_statut, f.priorite as bt_priorite,
                       te.total_hours,
                       STRFTIME('%H:%M', te.punch_in) as punch_in_time,
                       STRFTIME('%H:%M', te.punch_out) as punch_out_time,
                       DATE(te.punch_in) as work_date
                FROM time_entries te
                LEFT JOIN projects p ON te.project_id = p.id
                LEFT JOIN companies comp ON p.client_company_id = comp.id
                LEFT JOIN formulaires f ON te.formulaire_bt_id = f.id
                WHERE te.employee_id = ?
                  AND te.punch_in >= ?
                  AND te.punch_in <= ?
                ORDER BY te.punch_in
            """, (emp['id'], start_str, end_str))
            
            entries = [dict(e) for e in time_entries] if time_entries else []
            
            # Calculer le total des heures
            total_hours = sum(e.get('total_hours', 0) for e in entries)
            
            # Grouper par jour avec détails
            daily_hours = {}
            project_hours = {}
            bt_hours = {}
            client_hours = {}
            
            for entry in entries:
                if entry.get('punch_in'):
                    # Par jour
                    day = entry['punch_in'][:10]  # YYYY-MM-DD
                    if day not in daily_hours:
                        daily_hours[day] = {
                            'hours': 0, 
                            'projects': set(),
                            'bons_travail': set(),
                            'entries': []
                        }
                    daily_hours[day]['hours'] += entry.get('total_hours', 0)
                    daily_hours[day]['entries'].append(entry)
                    
                    # Par projet
                    if entry.get('nom_projet'):
                        project_name = entry['nom_projet']
                        daily_hours[day]['projects'].add(project_name)
                        
                        if project_name not in project_hours:
                            project_hours[project_name] = {
                                'hours': 0,
                                'statut': entry.get('projet_statut'),
                                'client': entry.get('client_nom'),
                                'bons_travail': set(),
                                'days_worked': set()
                            }
                        project_hours[project_name]['hours'] += entry.get('total_hours', 0)
                        project_hours[project_name]['days_worked'].add(day)
                        
                    # Par bon de travail
                    if entry.get('bt_numero'):
                        bt_numero = entry['bt_numero']
                        daily_hours[day]['bons_travail'].add(bt_numero)
                        
                        if bt_numero not in bt_hours:
                            bt_hours[bt_numero] = {
                                'hours': 0,
                                'statut': entry.get('bt_statut'),
                                'priorite': entry.get('bt_priorite'),
                                'project': entry.get('nom_projet')
                            }
                        bt_hours[bt_numero]['hours'] += entry.get('total_hours', 0)
                        
                        if project_name:
                            project_hours[project_name]['bons_travail'].add(bt_numero)
                    
                    # Par client
                    if entry.get('client_nom'):
                        client = entry['client_nom']
                        if client not in client_hours:
                            client_hours[client] = {'hours': 0, 'projects': set()}
                        client_hours[client]['hours'] += entry.get('total_hours', 0)
                        if project_name:
                            client_hours[client]['projects'].add(project_name)
            
            # Convertir les sets en listes pour JSON
            for day_data in daily_hours.values():
                day_data['projects'] = list(day_data['projects'])
                day_data['bons_travail'] = list(day_data['bons_travail'])
            
            for project_data in project_hours.values():
                project_data['bons_travail'] = list(project_data['bons_travail'])
                project_data['days_worked'] = list(project_data['days_worked'])
            
            for client_data in client_hours.values():
                client_data['projects'] = list(client_data['projects'])
            
            # Calculer des statistiques
            days_worked = len(daily_hours)
            avg_hours_per_day = total_hours / days_worked if days_worked > 0 else 0
            
            # Identifier le jour le plus productif
            most_productive_day = None
            max_hours = 0
            for day, data in daily_hours.items():
                if data['hours'] > max_hours:
                    max_hours = data['hours']
                    most_productive_day = day
            
            return {
                "employee_name": f"{emp['prenom']} {emp['nom']}",
                "employee_id": emp['id'],
                "poste": emp.get('poste', 'N/A'),
                "departement": emp.get('departement', 'N/A'),
                "week_start": start_week.strftime('%Y-%m-%d'),
                "week_end": end_week.strftime('%Y-%m-%d'),
                "total_hours": total_hours,
                "total_days": days_worked,
                "average_hours": avg_hours_per_day,
                "most_productive_day": most_productive_day,
                "max_daily_hours": max_hours,
                "time_entries": entries,
                "hours_by_day": [
                    {
                        'date': day,
                        'day_name': datetime.strptime(day, '%Y-%m-%d').strftime('%A'),
                        'hours': data['hours'],
                        'projects': data['projects'],
                        'bons_travail': data['bons_travail'],
                        'entries_count': len(data['entries'])
                    }
                    for day, data in sorted(daily_hours.items())
                ],
                "hours_by_project": [
                    {
                        'project_name': project,
                        'hours': data['hours'],
                        'percentage': (data['hours'] / total_hours * 100) if total_hours > 0 else 0,
                        'statut': data['statut'],
                        'client': data['client'],
                        'bons_travail': data['bons_travail'],
                        'days_worked': len(data['days_worked'])
                    }
                    for project, data in sorted(project_hours.items(), key=lambda x: x[1]['hours'], reverse=True)
                ],
                "hours_by_bt": [
                    {
                        'bt_numero': bt,
                        'hours': data['hours'],
                        'percentage': (data['hours'] / total_hours * 100) if total_hours > 0 else 0,
                        'statut': data['statut'],
                        'priorite': data['priorite'],
                        'project': data['project']
                    }
                    for bt, data in sorted(bt_hours.items(), key=lambda x: x[1]['hours'], reverse=True)
                ],
                "hours_by_client": [
                    {
                        'client': client,
                        'hours': data['hours'],
                        'percentage': (data['hours'] / total_hours * 100) if total_hours > 0 else 0,
                        'projects': data['projects']
                    }
                    for client, data in sorted(client_hours.items(), key=lambda x: x[1]['hours'], reverse=True)
                ]
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération heures employé: {e}")
            return {"error": str(e)}
    
    def _get_project_report(self, project_id: str) -> Dict[str, Any]:
        """Génère un rapport complet pour un projet avec analyse financière et RH"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            # Récupérer les infos du projet
            project = self.db.execute_query("""
                SELECT p.*, c.nom as client_nom, c.secteur as client_secteur
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE p.id = ?
                LIMIT 1
            """, (project_id,))
            
            if not project:
                return {"error": f"Projet '{project_id}' non trouvé"}
            
            proj = dict(project[0])
            
            # Récupérer tous les bons de travail du projet
            bons_travail = self.db.execute_query("""
                SELECT f.*, 
                       SUM(fl.montant_ligne) as cout_total,
                       COUNT(DISTINCT fl.id) as nb_lignes
                FROM formulaires f
                LEFT JOIN formulaire_lignes fl ON f.id = fl.formulaire_id
                WHERE f.project_id = ? AND f.type_formulaire = 'BON_TRAVAIL'
                GROUP BY f.id
                ORDER BY f.created_at
            """, (proj['id'],))
            
            # Récupérer les heures travaillées sur le projet
            heures_travail = self.db.execute_query("""
                SELECT 
                    e.nom, e.prenom, e.poste, e.salaire,
                    SUM(te.total_hours) as heures_totales,
                    COUNT(DISTINCT DATE(te.punch_in)) as jours_travailles,
                    MIN(DATE(te.punch_in)) as premiere_intervention,
                    MAX(DATE(te.punch_in)) as derniere_intervention
                FROM time_entries te
                JOIN employees e ON te.employee_id = e.id
                WHERE te.project_id = ?
                GROUP BY e.id
                ORDER BY heures_totales DESC
            """, (proj['id'],))
            
            # Calculer les coûts de main d'œuvre
            cout_main_oeuvre = 0
            heures_totales_projet = 0
            employes_details = []
            
            for emp in heures_travail if heures_travail else []:
                emp_dict = dict(emp)
                # Calculer le taux horaire à partir du salaire annuel
                # Basé sur 40h/semaine * 52 semaines = 2080 heures/an
                salaire_annuel = emp_dict.get('salaire', 0) or 50000  # Salaire par défaut si non défini
                taux_horaire = salaire_annuel / 2080  # Taux horaire calculé
                emp_dict['taux_horaire'] = taux_horaire
                
                heures = emp_dict.get('heures_totales', 0)
                cout_emp = taux_horaire * heures
                cout_main_oeuvre += cout_emp
                heures_totales_projet += heures
                
                emp_dict['cout_total'] = cout_emp
                employes_details.append(emp_dict)
            
            # Récupérer les matériaux utilisés
            materiaux = self.db.execute_query("""
                SELECT m.code_materiau as code_article, m.designation as nom_produit,
                       m.quantite as quantite_totale,
                       m.unite, m.prix_unitaire as cout_unitaire,
                       (m.quantite * m.prix_unitaire) as cout_total,
                       m.fournisseur
                FROM materials m
                WHERE m.project_id = ?
                ORDER BY cout_total DESC
            """, (proj['id'],))
            
            cout_materiaux = sum(mat.get('cout_total', 0) for mat in (materiaux if materiaux else []))
            
            # Récupérer les opérations du projet (en lieu d'étapes)
            operations = self.db.execute_query("""
                SELECT o.*, wc.nom as poste_travail
                FROM operations o
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE o.project_id = ?
                ORDER BY o.id
            """, (proj['id'],))
            
            # Calculer l'avancement global basé sur le statut
            if proj.get('statut') == 'TERMINÉ':
                avancement_total = 100
            elif proj.get('statut') == 'EN COURS':
                avancement_total = 50
            elif proj.get('statut') == 'VALIDÉ':
                avancement_total = 25
            else:
                avancement_total = 0
            
            # Récupérer tous les documents associés avec détails
            documents = self.db.execute_query("""
                SELECT f.numero_document, f.type_formulaire, f.statut, 
                       f.montant_total, f.created_at, f.notes,
                       c.nom as fournisseur_nom, c.id as fournisseur_id,
                       f.metadonnees_json
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                WHERE f.project_id = ?
                ORDER BY f.type_formulaire, f.created_at DESC
            """, (proj['id'],))
            
            # Organiser les documents par type
            devis = []
            demandes_prix = []
            bons_achat = []
            fournisseurs_uniques = {}
            
            for doc in documents if documents else []:
                doc_dict = dict(doc)
                type_form = doc_dict.get('type_formulaire')
                
                if type_form == 'ESTIMATION':
                    devis.append(doc_dict)
                elif type_form == 'DEMANDE_PRIX':
                    demandes_prix.append(doc_dict)
                    # Collecter les fournisseurs
                    if doc_dict.get('fournisseur_id') and doc_dict.get('fournisseur_nom'):
                        fournisseurs_uniques[doc_dict['fournisseur_id']] = doc_dict['fournisseur_nom']
                elif type_form == 'BON_ACHAT':
                    bons_achat.append(doc_dict)
                    # Collecter les fournisseurs
                    if doc_dict.get('fournisseur_id') and doc_dict.get('fournisseur_nom'):
                        fournisseurs_uniques[doc_dict['fournisseur_id']] = doc_dict['fournisseur_nom']
            
            # Calculs financiers
            cout_total = cout_main_oeuvre + cout_materiaux
            prix_vente = proj.get('prix_estime', 0) or 0
            profit_brut = prix_vente - cout_total
            marge_profit = (profit_brut / prix_vente * 100) if prix_vente > 0 else 0
            
            # Efficacité (heures réelles vs estimées)
            heures_estimees = proj.get('bd_ft_estime', 0) or 0
            efficacite = (heures_estimees / heures_totales_projet * 100) if heures_totales_projet > 0 else 0
            
            return {
                "project_info": proj,
                "financial_summary": {
                    "prix_vente": prix_vente,
                    "cout_main_oeuvre": cout_main_oeuvre,
                    "cout_materiaux": cout_materiaux,
                    "cout_total": cout_total,
                    "profit_brut": profit_brut,
                    "marge_profit": marge_profit
                },
                "time_summary": {
                    "heures_estimees": heures_estimees,
                    "heures_reelles": heures_totales_projet,
                    "efficacite": efficacite,
                    "nb_employes": len(employes_details),
                    "nb_jours_travailles": max(e.get('jours_travailles', 0) for e in employes_details) if employes_details else 0
                },
                "employees": employes_details,
                "materials": [dict(m) for m in materiaux] if materiaux else [],
                "work_orders": [dict(bt) for bt in bons_travail] if bons_travail else [],
                "operations": [dict(o) for o in operations] if operations else [],
                "documents": [dict(d) for d in documents] if documents else [],
                "devis": devis,
                "demandes_prix": demandes_prix,
                "bons_achat": bons_achat,
                "fournisseurs": list(fournisseurs_uniques.values()),
                "progress": avancement_total
            }
            
        except Exception as e:
            logger.error(f"Erreur génération rapport projet: {e}")
            return {"error": str(e)}
    
    def _get_bt_report(self, bt_numero: str) -> Dict[str, Any]:
        """Génère un rapport complet pour un bon de travail"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            # Récupérer les infos du bon de travail
            bt = self.db.execute_query("""
                SELECT f.*, p.nom_projet, p.prix_estime as projet_budget,
                       c.nom as client_nom
                FROM formulaires f
                LEFT JOIN projects p ON f.project_id = p.id
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE f.numero_document = ? AND f.type_formulaire = 'BON_TRAVAIL'
                LIMIT 1
            """, (bt_numero,))
            
            if not bt:
                return {"error": f"Bon de travail '{bt_numero}' non trouvé"}
            
            bt_info = dict(bt[0])
            
            # Récupérer les lignes du bon de travail
            lignes = self.db.execute_query("""
                SELECT * FROM formulaire_lignes
                WHERE formulaire_id = ?
                ORDER BY sequence_ligne
            """, (bt_info['id'],))
            
            # Récupérer les heures travaillées sur ce BT
            heures_bt = self.db.execute_query("""
                SELECT 
                    e.nom, e.prenom, e.poste, e.salaire,
                    te.punch_in, te.punch_out, te.total_hours,
                    DATE(te.punch_in) as date_travail,
                    te.description
                FROM time_entries te
                JOIN employees e ON te.employee_id = e.id
                WHERE te.formulaire_bt_id = ?
                ORDER BY te.punch_in
            """, (bt_info['id'],))
            
            # Analyser les heures par employé
            heures_par_employe = {}
            heures_totales = 0
            cout_main_oeuvre_total = 0
            
            for h in heures_bt if heures_bt else []:
                h_dict = dict(h)
                emp_key = f"{h_dict['prenom']} {h_dict['nom']}"
                
                if emp_key not in heures_par_employe:
                    # Calculer le taux horaire à partir du salaire annuel
                    salaire_annuel = h_dict.get('salaire', 0) or 50000
                    taux_horaire = salaire_annuel / 2080
                    
                    heures_par_employe[emp_key] = {
                        'poste': h_dict['poste'],
                        'taux_horaire': taux_horaire,
                        'heures_totales': 0,
                        'cout_total': 0,
                        'jours': set(),
                        'entries': []
                    }
                
                heures = h_dict.get('total_hours', 0)
                taux = heures_par_employe[emp_key]['taux_horaire']
                cout = heures * taux
                
                heures_par_employe[emp_key]['heures_totales'] += heures
                heures_par_employe[emp_key]['cout_total'] += cout
                heures_par_employe[emp_key]['jours'].add(h_dict['date_travail'])
                heures_par_employe[emp_key]['entries'].append(h_dict)
                
                heures_totales += heures
                cout_main_oeuvre_total += cout
            
            # Convertir sets en listes
            for emp_data in heures_par_employe.values():
                emp_data['nb_jours'] = len(emp_data['jours'])
                del emp_data['jours']
            
            # Récupérer l'avancement
            avancement = self.db.execute_query("""
                SELECT fa.*, e.nom, e.prenom
                FROM formulaire_avancement fa
                LEFT JOIN employees e ON fa.employee_id = e.id
                WHERE fa.formulaire_id = ?
                ORDER BY fa.updated_at DESC
            """, (bt_info['id'],))
            
            # Calculer le coût total du BT
            cout_lignes = sum(l.get('montant_ligne', 0) for l in (lignes if lignes else []))
            cout_total_bt = cout_lignes + cout_main_oeuvre_total
            
            # Récupérer les assignations
            assignations = self.db.execute_query("""
                SELECT e.nom, e.prenom, e.poste, ea.date_assignation, ea.role_assignation
                FROM employee_assignations ea
                JOIN employees e ON ea.employee_id = e.id
                WHERE ea.formulaire_id = ?
                ORDER BY ea.date_assignation
            """, (bt_info['id'],))
            
            return {
                "bt_info": bt_info,
                "lignes": [dict(l) for l in lignes] if lignes else [],
                "financial_summary": {
                    "cout_lignes": cout_lignes,
                    "cout_main_oeuvre": cout_main_oeuvre_total,
                    "cout_total": cout_total_bt,
                    "budget_alloue": bt_info.get('montant_total', 0)
                },
                "time_summary": {
                    "heures_totales": heures_totales,
                    "nb_employes": len(heures_par_employe),
                    "premiere_intervention": min(h['punch_in'] for h in heures_bt) if heures_bt else None,
                    "derniere_intervention": max(h['punch_out'] for h in heures_bt) if heures_bt else None
                },
                "employees_detail": heures_par_employe,
                "time_entries": [dict(h) for h in heures_bt] if heures_bt else [],
                "progress_history": [dict(a) for a in avancement] if avancement else [],
                "assignations": [dict(a) for a in assignations] if assignations else []
            }
            
        except Exception as e:
            logger.error(f"Erreur génération rapport BT: {e}")
            return {"error": str(e)}
    
    def _get_alertes(self) -> Dict[str, Any]:
        """Récupère toutes les alertes importantes du système"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            alertes = {
                "stocks_faibles": [],
                "projets_echeance": [],
                "bt_urgents": [],
                "devis_a_relancer": []
            }
            
            # Stocks faibles ou en rupture
            stocks_faibles = self.db.execute_query("""
                SELECT p.code_produit, p.nom, p.stock_disponible, p.stock_minimum,
                       p.fournisseur_principal, p.delai_approvisionnement
                FROM produits p
                WHERE p.actif = 1 AND p.stock_disponible <= p.stock_minimum
                ORDER BY (p.stock_disponible - p.stock_minimum) ASC
                LIMIT 20
            """)
            alertes['stocks_faibles'] = [dict(s) for s in stocks_faibles] if stocks_faibles else []
            
            # Projets avec échéance proche (dans les 7 jours)
            projets_echeance = self.db.execute_query("""
                SELECT p.id, p.nom_projet, p.date_prevu, p.statut, c.nom as client_nom
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE p.statut IN ('EN COURS', 'VALIDÉ') 
                  AND p.date_prevu IS NOT NULL
                  AND julianday(p.date_prevu) - julianday('now') BETWEEN 0 AND 7
                ORDER BY p.date_prevu
            """)
            alertes['projets_echeance'] = [dict(p) for p in projets_echeance] if projets_echeance else []
            
            # Bons de travail urgents non terminés
            bt_urgents = self.db.execute_query("""
                SELECT f.numero_document, f.priorite, f.statut, f.created_at,
                       p.nom_projet, f.notes
                FROM formulaires f
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                  AND f.priorite = 'URGENT'
                  AND f.statut NOT IN ('TERMINÉ', 'ANNULÉ')
                ORDER BY f.created_at DESC
            """)
            alertes['bt_urgents'] = [dict(bt) for bt in bt_urgents] if bt_urgents else []
            
            # Devis en attente depuis plus de 15 jours
            devis_anciens = self.db.execute_query("""
                SELECT f.numero_document, f.montant_total, f.created_at, f.statut,
                       c.nom as client_nom
                FROM formulaires f
                LEFT JOIN projects p ON f.project_id = p.id
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE f.type_formulaire = 'ESTIMATION'
                  AND f.statut = 'BROUILLON'
                  AND julianday('now') - julianday(f.created_at) > 15
                ORDER BY f.created_at
            """)
            alertes['devis_a_relancer'] = [dict(d) for d in devis_anciens] if devis_anciens else []
            
            return alertes
            
        except Exception as e:
            logger.error(f"Erreur récupération alertes: {e}")
            return {"error": str(e)}
    
    def _get_employes_disponibles(self) -> Dict[str, Any]:
        """Récupère les employés disponibles"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            # Employés disponibles (pas d'entrée de temps aujourd'hui ou sortie enregistrée)
            employes = self.db.execute_query("""
                SELECT DISTINCT e.id, e.nom, e.prenom, e.poste, e.departement,
                       e.charge_travail,
                       CASE 
                           WHEN te.punch_out IS NOT NULL OR te.id IS NULL THEN 'Disponible'
                           WHEN te.punch_out IS NULL THEN 'En travail'
                           ELSE 'Disponible'
                       END as statut_actuel,
                       te.punch_in as derniere_entree
                FROM employees e
                LEFT JOIN (
                    SELECT employee_id, punch_in, punch_out, id
                    FROM time_entries
                    WHERE DATE(punch_in) = DATE('now')
                    ORDER BY punch_in DESC
                ) te ON e.id = te.employee_id
                WHERE e.statut = 'ACTIF'
                GROUP BY e.id
                HAVING statut_actuel = 'Disponible'
                ORDER BY e.nom, e.prenom
            """)
            
            return {"employes": [dict(e) for e in employes] if employes else []}
            
        except Exception as e:
            logger.error(f"Erreur récupération employés disponibles: {e}")
            return {"error": str(e)}
    
    def _get_bt_en_cours(self) -> Dict[str, Any]:
        """Récupère tous les bons de travail en cours"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            bt_en_cours = self.db.execute_query("""
                SELECT f.numero_document, f.statut, f.priorite, f.created_at,
                       f.montant_total, p.nom_projet, c.nom as client_nom,
                       f.notes,
                       (SELECT COUNT(*) FROM employee_assignations ea WHERE ea.formulaire_id = f.id) as nb_employes,
                       (SELECT MAX(fa.pourcentage_realise) FROM formulaire_avancement fa WHERE fa.formulaire_id = f.id) as avancement
                FROM formulaires f
                LEFT JOIN projects p ON f.project_id = p.id
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE f.type_formulaire = 'BON_TRAVAIL'
                  AND f.statut IN ('VALIDÉ', 'EN_COURS')
                ORDER BY f.priorite = 'URGENT' DESC, f.created_at DESC
            """)
            
            return {"bons_travail": [dict(bt) for bt in bt_en_cours] if bt_en_cours else []}
            
        except Exception as e:
            logger.error(f"Erreur récupération BT en cours: {e}")
            return {"error": str(e)}
    
    def _get_ruptures_stock(self) -> Dict[str, Any]:
        """Récupère les produits en rupture de stock"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            ruptures = self.db.execute_query("""
                SELECT p.code_produit, p.nom, p.categorie, p.stock_disponible,
                       p.stock_minimum, p.stock_reserve, p.stock_commande,
                       p.fournisseur_principal, p.delai_approvisionnement,
                       p.point_commande, p.unite_stock,
                       (p.stock_minimum - p.stock_disponible) as manquant
                FROM produits p
                WHERE p.actif = 1 
                  AND p.stock_disponible < p.stock_minimum
                ORDER BY manquant DESC, p.categorie, p.nom
            """)
            
            return {"ruptures": [dict(r) for r in ruptures] if ruptures else []}
            
        except Exception as e:
            logger.error(f"Erreur récupération ruptures stock: {e}")
            return {"error": str(e)}
    
    def _get_projets_retard(self) -> Dict[str, Any]:
        """Récupère les projets en retard ou à risque"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            projets_retard = self.db.execute_query("""
                SELECT p.id, p.nom_projet, p.statut, p.priorite,
                       p.date_prevu, p.date_soumis, c.nom as client_nom,
                       p.prix_estime, p.bd_ft_estime,
                       julianday(p.date_prevu) - julianday('now') as jours_restants,
                       CASE
                           WHEN p.date_prevu < DATE('now') THEN 'En retard'
                           WHEN julianday(p.date_prevu) - julianday('now') <= 3 THEN 'À risque'
                           ELSE 'Dans les temps'
                       END as statut_delai
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE p.statut IN ('EN COURS', 'VALIDÉ', 'PLANIFIÉ')
                  AND p.date_prevu IS NOT NULL
                  AND (p.date_prevu < DATE('now') 
                       OR julianday(p.date_prevu) - julianday('now') <= 3)
                ORDER BY p.date_prevu
            """)
            
            return {"projets": [dict(p) for p in projets_retard] if projets_retard else []}
            
        except Exception as e:
            logger.error(f"Erreur récupération projets en retard: {e}")
            return {"error": str(e)}
    
    def _get_dashboard_data(self) -> Dict[str, Any]:
        """Récupère les données pour le dashboard général"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            dashboard = {}
            
            # Chiffre d'affaires du mois
            ca_mois = self.db.execute_query("""
                SELECT SUM(f.montant_total) as ca_total
                FROM formulaires f
                WHERE f.type_formulaire = 'FACTURE'
                  AND f.statut = 'PAYÉ'
                  AND strftime('%Y-%m', f.created_at) = strftime('%Y-%m', 'now')
            """)
            dashboard['ca_mois'] = ca_mois[0]['ca_total'] if ca_mois and ca_mois[0]['ca_total'] else 0
            
            # Projets actifs
            projets_actifs = self.db.execute_query("""
                SELECT COUNT(*) as nb_actifs,
                       SUM(prix_estime) as valeur_totale
                FROM projects
                WHERE statut IN ('EN COURS', 'VALIDÉ')
            """)
            dashboard['projets_actifs'] = projets_actifs[0] if projets_actifs else {'nb_actifs': 0, 'valeur_totale': 0}
            
            # Taux occupation employés
            occupation = self.db.execute_query("""
                SELECT COUNT(DISTINCT e.id) as total_employes,
                       COUNT(DISTINCT te.employee_id) as employes_actifs
                FROM employees e
                LEFT JOIN time_entries te ON e.id = te.employee_id 
                    AND DATE(te.punch_in) = DATE('now')
                    AND te.punch_out IS NULL
                WHERE e.statut = 'ACTIF'
            """)
            dashboard['occupation'] = occupation[0] if occupation else {'total_employes': 0, 'employes_actifs': 0}
            
            # Top 5 projets par valeur
            top_projets = self.db.execute_query("""
                SELECT p.nom_projet, p.prix_estime, c.nom as client_nom, p.statut
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE p.statut IN ('EN COURS', 'VALIDÉ')
                ORDER BY p.prix_estime DESC
                LIMIT 5
            """)
            dashboard['top_projets'] = [dict(p) for p in top_projets] if top_projets else []
            
            # Alertes critiques (résumé)
            alertes_count = self.db.execute_query("""
                SELECT 
                    (SELECT COUNT(*) FROM produits WHERE actif = 1 AND stock_disponible = 0) as ruptures_totales,
                    (SELECT COUNT(*) FROM formulaires WHERE type_formulaire = 'BON_TRAVAIL' 
                     AND priorite = 'URGENT' AND statut NOT IN ('TERMINÉ', 'ANNULÉ')) as bt_urgents,
                    (SELECT COUNT(*) FROM projects WHERE statut IN ('EN COURS', 'VALIDÉ') 
                     AND date_prevu < DATE('now')) as projets_retard
            """)
            dashboard['alertes'] = alertes_count[0] if alertes_count else {}
            
            # Tendance CA (3 derniers mois)
            tendance = self.db.execute_query("""
                SELECT strftime('%Y-%m', created_at) as mois,
                       SUM(montant_total) as ca
                FROM formulaires
                WHERE type_formulaire = 'FACTURE'
                  AND statut = 'PAYÉ'
                  AND created_at >= date('now', '-3 months')
                GROUP BY mois
                ORDER BY mois
            """)
            dashboard['tendance_ca'] = [dict(t) for t in tendance] if tendance else []
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Erreur récupération dashboard: {e}")
            return {"error": str(e)}
    
    def _get_factures_impayees(self) -> Dict[str, Any]:
        """Récupère les factures impayées"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            # Note: Adaptation car pas de table factures dédiée
            # On utilise formulaires avec type FACTURE ou les devis validés
            factures = self.db.execute_query("""
                SELECT f.numero_document, f.montant_total, f.created_at,
                       p.nom_projet, c.nom as client_nom, c.id as client_id,
                       julianday('now') - julianday(f.created_at) as jours_retard,
                       CASE 
                           WHEN julianday('now') - julianday(f.created_at) > 90 THEN '90+ jours'
                           WHEN julianday('now') - julianday(f.created_at) > 60 THEN '60-90 jours'
                           WHEN julianday('now') - julianday(f.created_at) > 30 THEN '30-60 jours'
                           ELSE '0-30 jours'
                       END as tranche_age
                FROM formulaires f
                LEFT JOIN projects p ON f.project_id = p.id
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE f.type_formulaire IN ('ESTIMATION', 'FACTURE')
                  AND f.statut = 'VALIDÉ'
                  AND julianday('now') - julianday(f.created_at) > 30
                ORDER BY jours_retard DESC
            """)
            
            # Grouper par client
            par_client = {}
            for f in factures if factures else []:
                f_dict = dict(f)
                client_id = f_dict.get('client_id', 'inconnu')
                if client_id not in par_client:
                    par_client[client_id] = {
                        'client_nom': f_dict.get('client_nom', 'Client inconnu'),
                        'factures': [],
                        'total_impaye': 0,
                        'plus_ancienne': 999
                    }
                par_client[client_id]['factures'].append(f_dict)
                par_client[client_id]['total_impaye'] += f_dict.get('montant_total', 0) or 0
                par_client[client_id]['plus_ancienne'] = min(
                    par_client[client_id]['plus_ancienne'], 
                    f_dict.get('jours_retard', 0)
                )
            
            return {
                "factures": [dict(f) for f in factures] if factures else [],
                "par_client": par_client,
                "total_global": sum(pc['total_impaye'] for pc in par_client.values())
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération factures impayées: {e}")
            return {"error": str(e)}
    
    def _get_charge_travail(self, semaine: str = None) -> Dict[str, Any]:
        """Récupère la charge de travail pour une semaine"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            # Déterminer la semaine
            if semaine:
                # Parser la semaine fournie (format: "2025-01-20" ou "prochaine")
                if semaine.lower() == 'prochaine':
                    from datetime import timedelta
                    ref_date = datetime.now() + timedelta(days=7)
                else:
                    try:
                        ref_date = datetime.strptime(semaine, '%Y-%m-%d')
                    except:
                        ref_date = datetime.now()
            else:
                ref_date = datetime.now()
            
            # Début et fin de semaine
            from datetime import timedelta
            weekday = ref_date.weekday()
            start_week = ref_date - timedelta(days=weekday)
            end_week = start_week + timedelta(days=6)
            
            # Charge par employé
            charge_employes = self.db.execute_query("""
                SELECT e.id, e.nom, e.prenom, e.poste,
                       COUNT(DISTINCT ba.bt_id) as nb_bons_travail,
                       GROUP_CONCAT(DISTINCT p.nom_projet) as projets,
                       COALESCE(SUM(fl.quantite * 
                           CASE 
                               WHEN fl.unite = 'heures' THEN 1
                               WHEN fl.unite = 'jours' THEN 8
                               ELSE 0.5
                           END
                       ), 0) as heures_assignees
                FROM employees e
                LEFT JOIN bt_assignations ba ON e.id = ba.employe_id
                LEFT JOIN formulaires f ON ba.bt_id = f.id 
                    AND f.statut IN ('VALIDÉ', 'EN_COURS', 'EN_PRODUCTION')
                LEFT JOIN formulaire_lignes fl ON f.id = fl.formulaire_id
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE e.statut = 'ACTIF'
                GROUP BY e.id
                ORDER BY heures_assignees DESC
            """)
            
            # Charge par poste de travail
            charge_postes = self.db.execute_query("""
                SELECT wc.nom as poste,
                       COUNT(DISTINCT o.id) as nb_operations,
                       COALESCE(SUM(o.temps_estime), 0) as heures_planifiees
                FROM work_centers wc
                LEFT JOIN operations o ON wc.id = o.work_center_id
                    AND o.statut IN ('PLANIFIÉ', 'EN_COURS')
                GROUP BY wc.id
            """)
            
            return {
                "semaine_debut": start_week.strftime('%Y-%m-%d'),
                "semaine_fin": end_week.strftime('%Y-%m-%d'),
                "charge_employes": [dict(e) for e in charge_employes] if charge_employes else [],
                "charge_postes": [dict(p) for p in charge_postes] if charge_postes else []
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération charge travail: {e}")
            return {"error": str(e)}
    
    def _get_produits_a_commander(self) -> Dict[str, Any]:
        """Récupère les produits à commander"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            # Produits sous le point de commande
            produits = self.db.execute_query("""
                SELECT p.*, 
                       (p.point_commande - p.stock_disponible - p.stock_commande) as qte_suggere,
                       (p.point_commande - p.stock_disponible - p.stock_commande) * p.prix_unitaire as cout_estime
                FROM produits p
                WHERE p.actif = 1
                  AND p.stock_disponible + p.stock_commande < p.point_commande
                  AND p.point_commande > 0
                ORDER BY p.fournisseur_principal, p.categorie, p.nom
            """)
            
            # Grouper par fournisseur
            par_fournisseur = {}
            for p in produits if produits else []:
                p_dict = dict(p)
                fourn = p_dict.get('fournisseur_principal', 'Non défini')
                if fourn not in par_fournisseur:
                    par_fournisseur[fourn] = {
                        'produits': [],
                        'nb_produits': 0,
                        'cout_total': 0
                    }
                par_fournisseur[fourn]['produits'].append(p_dict)
                par_fournisseur[fourn]['nb_produits'] += 1
                par_fournisseur[fourn]['cout_total'] += p_dict.get('cout_estime', 0) or 0
            
            # Suggestions basées sur l'historique
            historique = self.db.execute_query("""
                SELECT p.code_produit, p.nom,
                       AVG(ms.quantite) as conso_moyenne,
                       MAX(ms.date_mouvement) as derniere_sortie
                FROM produits p
                JOIN mouvements_stock ms ON p.id = ms.produit_id
                WHERE ms.type_mouvement = 'SORTIE'
                  AND ms.date_mouvement >= date('now', '-3 months')
                GROUP BY p.id
                HAVING conso_moyenne > 0
            """)
            
            return {
                "produits": [dict(p) for p in produits] if produits else [],
                "par_fournisseur": par_fournisseur,
                "historique_conso": [dict(h) for h in historique] if historique else []
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération produits à commander: {e}")
            return {"error": str(e)}
    
    def _get_performance_mensuelle(self, mois: str = None) -> Dict[str, Any]:
        """Récupère les indicateurs de performance mensuels"""
        if not self.db:
            return {"error": "Base de données non disponible"}
        
        try:
            # Déterminer le mois
            if mois:
                try:
                    # Format: "2025-01" ou "janvier"
                    if '-' in mois:
                        mois_str = mois
                    else:
                        # Convertir nom de mois si nécessaire
                        mois_str = datetime.now().strftime('%Y-%m')
                except:
                    mois_str = datetime.now().strftime('%Y-%m')
            else:
                mois_str = datetime.now().strftime('%Y-%m')
            
            # Rentabilité par projet
            projets_rentabilite = self.db.execute_query("""
                SELECT p.nom_projet, p.prix_estime as revenus,
                       COALESCE(SUM(te.total_hours * e.salaire / 2080), 0) as cout_mo,
                       COALESCE(SUM(m.quantite * m.prix_unitaire), 0) as cout_materiaux,
                       p.statut
                FROM projects p
                LEFT JOIN time_entries te ON p.id = te.project_id
                    AND strftime('%Y-%m', te.punch_in) = ?
                LEFT JOIN employees e ON te.employee_id = e.id
                LEFT JOIN materials m ON p.id = m.project_id
                WHERE strftime('%Y-%m', p.created_at) <= ?
                  AND (p.statut != 'ANNULÉ' OR strftime('%Y-%m', p.updated_at) = ?)
                GROUP BY p.id
                ORDER BY revenus DESC
            """, (mois_str, mois_str, mois_str))
            
            # Efficacité employés
            efficacite_employes = self.db.execute_query("""
                SELECT e.nom, e.prenom, e.poste,
                       COUNT(DISTINCT te.id) as nb_pointages,
                       SUM(te.total_hours) as heures_totales,
                       COUNT(DISTINCT DATE(te.punch_in)) as jours_travailles,
                       COUNT(DISTINCT te.project_id) as nb_projets
                FROM employees e
                JOIN time_entries te ON e.id = te.employee_id
                WHERE strftime('%Y-%m', te.punch_in) = ?
                GROUP BY e.id
                ORDER BY heures_totales DESC
            """, (mois_str,))
            
            # Taux de respect des délais
            respect_delais = self.db.execute_query("""
                SELECT 
                    COUNT(*) as total_projets,
                    SUM(CASE WHEN p.date_prevu >= p.updated_at THEN 1 ELSE 0 END) as dans_delais,
                    SUM(CASE WHEN p.date_prevu < p.updated_at THEN 1 ELSE 0 END) as en_retard
                FROM projects p
                WHERE p.statut = 'TERMINÉ'
                  AND strftime('%Y-%m', p.updated_at) = ?
            """, (mois_str,))
            
            # Comparaison mois précédent
            mois_precedent = (datetime.strptime(mois_str + '-01', '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m')
            
            ca_compare = self.db.execute_query("""
                SELECT 
                    (SELECT SUM(montant_total) FROM formulaires 
                     WHERE type_formulaire = 'FACTURE' AND statut = 'PAYÉ'
                     AND strftime('%Y-%m', created_at) = ?) as ca_actuel,
                    (SELECT SUM(montant_total) FROM formulaires 
                     WHERE type_formulaire = 'FACTURE' AND statut = 'PAYÉ'
                     AND strftime('%Y-%m', created_at) = ?) as ca_precedent
            """, (mois_str, mois_precedent))
            
            return {
                "mois": mois_str,
                "projets_rentabilite": [dict(p) for p in projets_rentabilite] if projets_rentabilite else [],
                "efficacite_employes": [dict(e) for e in efficacite_employes] if efficacite_employes else [],
                "respect_delais": dict(respect_delais[0]) if respect_delais else {},
                "comparaison": dict(ca_compare[0]) if ca_compare else {}
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération performance mensuelle: {e}")
            return {"error": str(e)}
    
    def _get_erp_statistics(self) -> Dict[str, Any]:
        """Récupère les statistiques de l'ERP"""
        if not self.db:
            return {}
        
        try:
            stats = {}
            
            # Projets par statut
            project_stats = self.db.execute_query("""
                SELECT statut, COUNT(*) as count, SUM(prix_estime) as valeur
                FROM projects 
                GROUP BY statut
            """)
            stats['projets'] = {row['statut']: {
                'nombre': row['count'],
                'valeur': row['valeur'] or 0
            } for row in project_stats}
            
            # Stock faible
            low_stock = self.db.execute_query("""
                SELECT COUNT(*) as count 
                FROM inventory_items 
                WHERE quantite_metric <= limite_minimale_metric
            """)
            stats['stock_faible'] = low_stock[0]['count'] if low_stock else 0
            
            # Employés disponibles
            available_emp = self.db.execute_query("""
                SELECT COUNT(*) as count 
                FROM employees 
                WHERE disponible = 1
            """)
            stats['employes_disponibles'] = available_emp[0]['count'] if available_emp else 0
            
            # Bons de travail en cours
            active_bt = self.db.execute_query("""
                SELECT COUNT(*) as count 
                FROM formulaires 
                WHERE type_formulaire = 'BON_TRAVAIL' 
                AND statut IN ('VALIDÉ', 'EN_COURS')
            """)
            stats['bons_travail_actifs'] = active_bt[0]['count'] if active_bt else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur statistiques: {e}")
            return {}
    
    def _get_current_projects(self) -> List[Dict]:
        """Récupère spécifiquement les projets en cours ou actifs"""
        if not self.db:
            return []
        
        try:
            # Requête pour les projets actifs (tous sauf TERMINÉ et ANNULÉ)
            # Note: On récupère tous les projets car il y a des problèmes d'encodage avec les statuts
            projects = self.db.execute_query("""
                SELECT 
                    p.id,
                    p.nom_projet,
                    p.statut,
                    p.priorite,
                    p.prix_estime,
                    p.description,
                    p.date_prevu,
                    p.client_nom_cache,
                    c.nom as client_nom
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                ORDER BY p.priorite DESC, p.updated_at DESC
            """)
            
            # Filtrer manuellement pour contourner les problèmes d'encodage
            if projects:
                active_projects = []
                for p in projects:
                    # Accepter tous les projets sauf ceux marqués comme terminés
                    statut = p.get('statut', '')
                    if statut and 'TERMIN' not in statut.upper() and 'ANNUL' not in statut.upper():
                        # Valider que le projet a bien un nom (éviter les données corrompues)
                        if p.get('nom_projet'):
                            active_projects.append(dict(p))
                return active_projects
            return []
            
        except Exception as e:
            logger.error(f"Erreur récupération projets actifs: {e}")
            # Essai sans jointure si erreur
            try:
                projects = self.db.execute_query("""
                    SELECT id, nom_projet, statut, priorite, prix_estime, description, date_prevu, client_nom_cache
                    FROM projects
                    ORDER BY priorite DESC
                """)
                if projects:
                    # Filtrer manuellement
                    active_projects = []
                    for p in projects:
                        statut = p.get('statut', '')
                        if statut and 'TERMIN' not in statut.upper() and 'ANNUL' not in statut.upper():
                            active_projects.append(dict(p))
                    return active_projects
                return []
            except Exception as e2:
                logger.error(f"Erreur requête simple: {e2}")
                return []
    
    # =========================================================================
    # MÉTHODES CLAUDE
    # =========================================================================
    
    def _get_claude_response(self, prompt: str, context: Dict = None) -> str:
        """Obtient une réponse de Claude"""
        if not self.client:
            return "❌ Assistant IA non configuré. Veuillez définir la clé API Claude."
        
        try:
            # Construire le message système avec contexte ERP
            system_message = """Tu es un assistant expert en gestion ERP pour l'industrie métallurgique.
Tu as accès aux données du système ERP incluant projets, inventaire, employés, clients et production.

RÈGLE ABSOLUE - SOURCE UNIQUE DE VÉRITÉ:
- Tu DOIS te baser EXCLUSIVEMENT sur les données fournies dans le contexte ERP
- Tu ne dois JAMAIS inventer, supposer ou inférer des informations au-delà des données explicites
- Chaque information que tu fournis doit être DIRECTEMENT et EXPLICITEMENT traçable aux données SQLite
- Si une information n'est pas dans les données fournies, réponds: "Cette information n'est pas disponible dans la base de données"
- Ne JAMAIS créer de projets, produits, employés ou autres entités qui n'existent pas dans les données

IMPORTANT - Format de réponse:
- Utilise des tableaux markdown pour présenter des listes de données (projets, inventaire, etc.)
- Utilise des titres avec ## et ### pour structurer les réponses
- Utilise des **gras** pour les éléments importants
- Utilise des emojis pertinents (📁 projets, 📦 inventaire, 👥 employés, etc.)
- Pour les montants, formate avec des espaces: 1 500 $ au lieu de 1500$
- Présente les dates en format lisible: 8 septembre 2025

Exemple de tableau pour projets:
| **Nom du projet** | **Statut** | **Priorité** | **Prix estimé** | **Date prévue** |
|-------------------|------------|--------------|-----------------|-----------------|
| Projet ABC | EN COURS | HAUTE | 25 000 $ | 15 mars 2025 |

Réponds de manière professionnelle et structurée."""
            
            if context:
                system_message += f"\n\nContexte ERP actuel:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
            
            # Historique de conversation
            messages = []
            for msg in st.session_state.ia_messages[-10:]:  # Limiter l'historique
                if msg['role'] != 'system':
                    messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })
            
            # Ajouter le nouveau message
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # Appel API Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.7,
                system=system_message,
                messages=messages
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Erreur Claude: {e}")
            return f"❌ Erreur: {str(e)}"
    
    # =========================================================================
    # MÉTHODES D'INTERFACE
    # =========================================================================
    
    def show_page(self):
        """Affiche la page de l'assistant IA"""
        
        # Styles CSS
        st.markdown("""
        <style>
        .ia-header {
            background: linear-gradient(135deg, #00A971 0%, #00673D 100%);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        
        .ia-header h1 {
            margin: 0;
            font-size: 2.5rem;
        }
        
        .stats-card {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 1rem;
            border-left: 4px solid #00A971;
            margin-bottom: 0.5rem;
        }
        
        .search-result {
            background: #e6f7f1;
            border-radius: 8px;
            padding: 1rem;
            margin: 0.5rem 0;
            border-left: 4px solid #00A971;
        }
        
        .message-user {
            background: #e3f2fd;
            border-radius: 8px;
            padding: 1rem;
            margin: 0.5rem 0;
            margin-left: 20%;
        }
        
        .message-assistant {
            background: #f5f5f5;
            border-radius: 8px;
            padding: 1rem;
            margin: 0.5rem 0;
            margin-right: 20%;
        }
        
        .help-box {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        /* Styles pour les tableaux markdown */
        .message-assistant table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }
        
        .message-assistant table th {
            background: linear-gradient(135deg, #00A971 0%, #00673D 100%);
            color: white;
            padding: 0.75rem;
            text-align: left;
            font-weight: 600;
        }
        
        .message-assistant table td {
            padding: 0.75rem;
            border-bottom: 1px solid #e5e5e5;
        }
        
        .message-assistant table tr:hover {
            background: #f8f9fa;
        }
        
        .message-assistant table tr:last-child td {
            border-bottom: none;
        }
        
        /* Styles pour les titres */
        .message-assistant h2 {
            color: #00673D;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
            font-size: 1.5rem;
        }
        
        .message-assistant h3 {
            color: #00A971;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
            font-size: 1.2rem;
        }
        
        /* Styles pour le code inline */
        .message-assistant code {
            background: #e6f7f1;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            color: #00673D;
            font-size: 0.9em;
        }
        
        /* Amélioration des listes */
        .message-assistant ul, .message-assistant ol {
            margin: 0.5rem 0;
            padding-left: 2rem;
        }
        
        .message-assistant li {
            margin: 0.25rem 0;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header
        st.markdown("""
        <div class="ia-header">
            <h1>🤖 Assistant IA Expert ERP</h1>
            <p>Intelligence artificielle intégrée pour l'analyse de vos données métallurgiques</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Sidebar
        with st.sidebar:
            st.markdown("### 🔧 Options")
            
            if st.button("🔄 Nouvelle conversation", use_container_width=True):
                st.session_state.ia_messages = []
                st.rerun()
            
            st.divider()
            
            # Statistiques ERP
            st.markdown("### 📊 Statistiques ERP")
            stats = self._get_erp_statistics()
            
            if stats:
                # Projets
                if 'projets' in stats:
                    total_projets = sum(v['nombre'] for v in stats['projets'].values())
                    st.metric("Projets totaux", total_projets)
                    
                    if stats['projets'].get('EN COURS'):
                        st.metric("En cours", stats['projets']['EN COURS']['nombre'])
                
                # Autres métriques
                if 'stock_faible' in stats:
                    st.metric("Articles stock faible", stats['stock_faible'])
                
                if 'employes_disponibles' in stats:
                    st.metric("Employés disponibles", stats['employes_disponibles'])
                
                if 'bons_travail_actifs' in stats:
                    st.metric("Bons travail actifs", stats['bons_travail_actifs'])
            
            st.divider()
            
            # Aide
            with st.expander("💡 Aide"):
                st.markdown("""
                **Commandes disponibles:**
                - `/erp [recherche]` - Rechercher dans l'ERP
                - `/stats` - Voir les statistiques
                - `/help` - Afficher l'aide
                
                **Exemples:**
                - `/erp projet chassis`
                - `/erp stock acier`
                - `/erp employé soudeur`
                """)
        
        # Zone de chat
        chat_container = st.container()
        
        # Afficher l'historique
        with chat_container:
            if not st.session_state.ia_messages:
                st.markdown("""
                <div class="help-box">
                    <h4>👋 Bienvenue dans l'Assistant IA ERP!</h4>
                    <p>Je peux vous aider à:</p>
                    <ul>
                        <li>Analyser vos données de production</li>
                        <li>Rechercher dans vos projets, inventaire et ressources</li>
                        <li>Fournir des recommandations basées sur vos données</li>
                        <li>Répondre à vos questions sur la métallurgie</li>
                    </ul>
                    <p><strong>Essayez:</strong> "Montre-moi les projets en cours" ou "/erp stock acier"</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Afficher les messages
            for msg in st.session_state.ia_messages:
                if msg['role'] == 'user':
                    st.markdown(f"""
                    <div class="message-user">
                        <strong>👤 Vous:</strong><br>
                        {msg['content']}
                    </div>
                    """, unsafe_allow_html=True)
                elif msg['role'] == 'assistant':
                    # Convertir le markdown en HTML pour un meilleur rendu
                    content = msg['content']
                    # Le markdown de Streamlit gère déjà bien les tableaux et le formatage
                    with st.container():
                        st.markdown(f"""
                        <div class="message-assistant">
                            <strong>🤖 Assistant:</strong>
                        </div>
                        """, unsafe_allow_html=True)
                        # Utiliser le markdown natif de Streamlit pour le contenu
                        st.markdown(content)
        
        # Input
        user_input = st.chat_input("Posez votre question ou tapez /help...")
        
        if user_input:
            # Ajouter le message utilisateur
            st.session_state.ia_messages.append({
                'role': 'user',
                'content': user_input
            })
            
            # Traiter la commande
            response = self._process_input(user_input)
            
            # Ajouter la réponse
            st.session_state.ia_messages.append({
                'role': 'assistant',
                'content': response
            })
            
            st.rerun()
    
    def _process_input(self, user_input: str) -> str:
        """Traite l'input utilisateur"""
        input_lower = user_input.lower().strip()
        
        # Commande help
        if input_lower == '/help':
            return self._get_help_text()
        
        # Commande debug (pour vérifier la connexion DB)
        elif input_lower == '/debug':
            return self._get_debug_info()
        
        # Commande stats
        elif input_lower == '/stats':
            stats = self._get_erp_statistics()
            return self._format_statistics(stats)
        
        # Commande recherche ERP
        elif input_lower.startswith('/erp '):
            query = user_input[5:].strip()
            
            # Vérifier si c'est une demande de formulaire spécifique (BT ou DEVIS)
            import re
            
            # Pattern pour BT (format BT-XXXX-XXX)
            bt_pattern = re.match(r'(bt[- ]?\d{4}[- ]?\d{3})', query.lower())
            if bt_pattern:
                # Normaliser le numéro de BT
                bt_numero = bt_pattern.group(1).upper().replace(' ', '-')
                if not bt_numero.startswith('BT-'):
                    bt_numero = 'BT-' + bt_numero[2:]
                
                # Récupérer les détails du BT
                bt_details = self._get_bt_details(bt_numero)
                
                if self.client and 'bt_details' in bt_details:
                    context = {
                        'bt_details': bt_details['bt_details'],
                        'instruction_stricte': "IMPORTANT: Présente UNIQUEMENT les informations fournies dans bt_details. N'invente AUCUNE donnée."
                    }
                    return self._get_claude_response(
                        f"Présente de manière détaillée ce bon de travail avec toutes ses opérations, assignations et avancements",
                        context
                    )
                else:
                    return self._format_bt_details(bt_details)
            
            # Pattern pour DEVIS (format EST-XXXX-XXX)
            devis_pattern = re.match(r'(est[- ]?\d{4}[- ]?\d{3})', query.lower())
            if devis_pattern:
                # Normaliser le numéro de devis
                devis_numero = devis_pattern.group(1).upper().replace(' ', '-')
                if not devis_numero.startswith('EST-'):
                    devis_numero = 'EST-' + devis_numero[3:]
                
                # Récupérer les détails du devis
                devis_details = self._get_devis_details(devis_numero)
                
                if self.client and 'devis_details' in devis_details:
                    context = {
                        'devis_details': devis_details['devis_details'],
                        'instruction_stricte': "IMPORTANT: Présente UNIQUEMENT les informations fournies dans devis_details. N'invente AUCUNE donnée."
                    }
                    return self._get_claude_response(
                        f"Présente de manière détaillée ce devis avec toutes ses lignes et informations commerciales",
                        context
                    )
                else:
                    return self._format_devis_details(devis_details)
            
            # Pattern pour PROJET (format PRJ-XX-XXX ou XX-XXX)
            projet_pattern = re.match(r'(?:prj[- ]?)?(\d{2}[- ]?\d{3})', query.lower())
            if projet_pattern:
                # Normaliser le numéro de projet
                projet_numero = projet_pattern.group(0).upper().replace(' ', '-')
                # Enlever le préfixe PRJ- s'il existe
                if projet_numero.startswith('PRJ-'):
                    projet_numero = projet_numero[4:]
                
                # Récupérer les détails du projet
                projet_details = self._get_projet_details(projet_numero)
                
                if self.client and 'projet_details' in projet_details:
                    context = {
                        'projet_details': projet_details['projet_details'],
                        'instruction_stricte': "IMPORTANT: Présente UNIQUEMENT les informations fournies dans projet_details. N'invente AUCUNE donnée."
                    }
                    return self._get_claude_response(
                        f"Présente de manière détaillée ce projet avec toutes ses informations, étapes et ressources associées",
                        context
                    )
                else:
                    return self._format_projet_details(projet_details)
            
            # Pattern pour DEMANDE DE PRIX (format DP-XXXX-XXX)
            dp_pattern = re.match(r'(dp[- ]?\d{4}[- ]?\d{3})', query.lower())
            if dp_pattern:
                # Normaliser le numéro de demande de prix
                dp_numero = dp_pattern.group(1).upper().replace(' ', '-')
                if not dp_numero.startswith('DP-'):
                    dp_numero = 'DP-' + dp_numero[2:]
                
                # Récupérer les détails de la demande de prix
                dp_details = self._get_dp_details(dp_numero)
                
                if self.client and 'dp_details' in dp_details:
                    context = {
                        'dp_details': dp_details['dp_details'],
                        'instruction_stricte': "IMPORTANT: Présente UNIQUEMENT les informations fournies dans dp_details. N'invente AUCUNE donnée."
                    }
                    return self._get_claude_response(
                        f"Présente de manière détaillée cette demande de prix avec toutes ses lignes et informations",
                        context
                    )
                else:
                    return self._format_dp_details(dp_details)
            
            # Pattern pour BON D'ACHAT (format BA-XXXX-XXX)
            ba_pattern = re.match(r'(ba[- ]?\d{4}[- ]?\d{3})', query.lower())
            if ba_pattern:
                # Normaliser le numéro de bon d'achat
                ba_numero = ba_pattern.group(1).upper().replace(' ', '-')
                if not ba_numero.startswith('BA-'):
                    ba_numero = 'BA-' + ba_numero[2:]
                
                # Récupérer les détails du bon d'achat
                ba_details = self._get_ba_details(ba_numero)
                
                if self.client and 'ba_details' in ba_details:
                    context = {
                        'ba_details': ba_details['ba_details'],
                        'instruction_stricte': "IMPORTANT: Présente UNIQUEMENT les informations fournies dans ba_details. N'invente AUCUNE donnée."
                    }
                    return self._get_claude_response(
                        f"Présente de manière détaillée ce bon d'achat avec toutes ses lignes et informations",
                        context
                    )
                else:
                    return self._format_ba_details(ba_details)
            
            # Gérer les commandes spécifiques sans terme de recherche
            elif query.lower() in ['produit', 'produits', 'article', 'articles']:
                # Récupérer directement tous les produits actifs
                try:
                    produits = self.db.execute_query("""
                        SELECT code_produit, nom, categorie, materiau, nuance, 
                               dimensions, unite_vente, prix_unitaire, 
                               stock_disponible, stock_minimum, fournisseur_principal
                        FROM produits 
                        WHERE actif = 1
                        ORDER BY categorie, nom
                        LIMIT 20
                    """)
                    if produits:
                        results = {'produits': [dict(p) for p in produits]}
                    else:
                        results = {}
                except Exception as e:
                    results = {'error': str(e)}
            elif query.lower() in ['projet', 'projets']:
                # Récupérer tous les projets actifs
                projets_actifs = self._get_current_projects()
                if projets_actifs:
                    results = {'projets': projets_actifs}
                else:
                    results = {}
            elif query.lower() in ['stock', 'inventaire']:
                # Récupérer tout l'inventaire
                try:
                    items = self.db.execute_query("""
                        SELECT nom, quantite_metric, statut, description
                        FROM inventory_items 
                        ORDER BY nom
                        LIMIT 20
                    """)
                    if items:
                        results = {'inventaire': [dict(item) for item in items]}
                    else:
                        results = {}
                except Exception as e:
                    results = {'error': str(e)}
            elif query.lower() in ['bt', 'bon', 'bons', 'bon de travail', 'bons de travail']:
                # Récupérer tous les bons de travail
                try:
                    bts = self.db.execute_query("""
                        SELECT f.numero_document, f.statut, f.priorite, f.created_at, 
                               f.metadonnees_json, f.notes,
                               (SELECT fl.description FROM formulaire_lignes fl 
                                WHERE fl.formulaire_id = f.id 
                                ORDER BY fl.sequence_ligne LIMIT 1) as premiere_ligne
                        FROM formulaires f 
                        WHERE f.type_formulaire = 'BON_TRAVAIL'
                        ORDER BY f.created_at DESC
                        LIMIT 20
                    """)
                    
                    if bts:
                        # Traiter les métadonnées JSON pour extraire le titre
                        bons_travail = []
                        for bt in bts:
                            bt_dict = dict(bt)
                            if bt_dict.get('metadonnees_json'):
                                try:
                                    meta = json.loads(bt_dict['metadonnees_json'])
                                    bt_dict['titre'] = meta.get('project_name', 'Sans titre')
                                    bt_dict['client'] = meta.get('client_name', 'N/A')
                                except:
                                    bt_dict['titre'] = bt_dict.get('premiere_ligne', 'Sans titre')
                                    bt_dict['client'] = 'N/A'
                            else:
                                bt_dict['titre'] = bt_dict.get('premiere_ligne', 'Sans titre')
                                bt_dict['client'] = 'N/A'
                            bons_travail.append(bt_dict)
                        results = {'bons_travail': bons_travail}
                    else:
                        results = {}
                except Exception as e:
                    results = {'error': str(e)}
            elif query.lower() in ['devis', 'quote', 'estimation', 'devis']:
                # Récupérer tous les devis
                try:
                    devis = self.db.execute_query("""
                        SELECT f.numero_document, f.statut, f.priorite, f.created_at, 
                               f.metadonnees_json, f.notes, f.montant_total,
                               (SELECT fl.description FROM formulaire_lignes fl 
                                WHERE fl.formulaire_id = f.id 
                                ORDER BY fl.sequence_ligne LIMIT 1) as premiere_ligne
                        FROM formulaires f 
                        WHERE f.type_formulaire = 'ESTIMATION'
                        ORDER BY f.created_at DESC
                        LIMIT 20
                    """)
                    
                    if devis:
                        # Traiter les métadonnées JSON pour extraire le titre
                        devis_list = []
                        for d in devis:
                            d_dict = dict(d)
                            if d_dict.get('metadonnees_json'):
                                try:
                                    meta = json.loads(d_dict['metadonnees_json'])
                                    d_dict['titre'] = meta.get('project_name', meta.get('objet', 'Sans titre'))
                                    d_dict['client'] = meta.get('client_name', 'N/A')
                                except:
                                    d_dict['titre'] = d_dict.get('premiere_ligne', 'Sans titre')
                                    d_dict['client'] = 'N/A'
                            else:
                                d_dict['titre'] = d_dict.get('premiere_ligne', 'Sans titre')
                                d_dict['client'] = 'N/A'
                            devis_list.append(d_dict)
                        results = {'devis': devis_list}
                    else:
                        results = {'info': 'Aucun devis trouvé dans la base de données.'}
                except Exception as e:
                    results = {'error': str(e)}
            elif query.lower() in ['contact', 'contacts']:
                # Récupérer tous les contacts
                try:
                    contacts = self.db.execute_query("""
                        SELECT c.*, comp.nom as entreprise_nom
                        FROM contacts c
                        LEFT JOIN companies comp ON c.company_id = comp.id
                        ORDER BY c.nom_famille, c.prenom
                        LIMIT 50
                    """)
                    
                    if contacts:
                        results = {'contacts': [dict(c) for c in contacts]}
                    else:
                        results = {'info': 'Aucun contact trouvé dans la base de données.'}
                except Exception as e:
                    results = {'error': str(e)}
            elif query.lower() in ['demande de prix', 'demandes de prix', 'dp']:
                # Récupérer toutes les demandes de prix
                try:
                    dps = self.db.execute_query("""
                        SELECT f.numero_document, f.statut, f.created_at, 
                               f.metadonnees_json, f.notes, c.nom as fournisseur_nom,
                               (SELECT fl.description FROM formulaire_lignes fl 
                                WHERE fl.formulaire_id = f.id 
                                ORDER BY fl.sequence_ligne LIMIT 1) as premiere_ligne
                        FROM formulaires f 
                        LEFT JOIN companies c ON f.company_id = c.id
                        WHERE f.type_formulaire = 'DEMANDE_PRIX'
                        ORDER BY f.created_at DESC
                        LIMIT 20
                    """)
                    
                    if dps:
                        # Traiter les métadonnées JSON pour extraire l'objet
                        dp_list = []
                        for dp in dps:
                            dp_dict = dict(dp)
                            if dp_dict.get('metadonnees_json'):
                                try:
                                    meta = json.loads(dp_dict['metadonnees_json'])
                                    dp_dict['objet'] = meta.get('objet', dp_dict.get('premiere_ligne', 'Sans objet'))
                                    dp_dict['fournisseur'] = meta.get('fournisseur_name', dp_dict.get('fournisseur_nom', 'N/A'))
                                except:
                                    dp_dict['objet'] = dp_dict.get('premiere_ligne', 'Sans objet')
                                    dp_dict['fournisseur'] = dp_dict.get('fournisseur_nom', 'N/A')
                            else:
                                dp_dict['objet'] = dp_dict.get('premiere_ligne', 'Sans objet')
                                dp_dict['fournisseur'] = dp_dict.get('fournisseur_nom', 'N/A')
                            dp_list.append(dp_dict)
                        results = {'demandes_prix': dp_list}
                    else:
                        results = {'info': 'Aucune demande de prix trouvée dans la base de données.'}
                except Exception as e:
                    results = {'error': str(e)}
            elif query.lower() in ['bon d\'achat', 'bons d\'achat', 'bon d\'achats', 'bons d\'achats', 'ba']:
                # Récupérer tous les bons d'achat
                try:
                    bas = self.db.execute_query("""
                        SELECT f.numero_document, f.statut, f.created_at, f.montant_total,
                               f.metadonnees_json, f.notes, c.nom as fournisseur_nom,
                               (SELECT fl.description FROM formulaire_lignes fl 
                                WHERE fl.formulaire_id = f.id 
                                ORDER BY fl.sequence_ligne LIMIT 1) as premiere_ligne
                        FROM formulaires f 
                        LEFT JOIN companies c ON f.company_id = c.id
                        WHERE f.type_formulaire = 'BON_ACHAT'
                        ORDER BY f.created_at DESC
                        LIMIT 20
                    """)
                    
                    if bas:
                        # Traiter les métadonnées JSON pour extraire les infos
                        ba_list = []
                        for ba in bas:
                            ba_dict = dict(ba)
                            if ba_dict.get('metadonnees_json'):
                                try:
                                    meta = json.loads(ba_dict['metadonnees_json'])
                                    ba_dict['objet'] = meta.get('objet', ba_dict.get('premiere_ligne', 'Sans objet'))
                                    ba_dict['fournisseur'] = meta.get('fournisseur_name', ba_dict.get('fournisseur_nom', 'N/A'))
                                except:
                                    ba_dict['objet'] = ba_dict.get('premiere_ligne', 'Sans objet')
                                    ba_dict['fournisseur'] = ba_dict.get('fournisseur_nom', 'N/A')
                            else:
                                ba_dict['objet'] = ba_dict.get('premiere_ligne', 'Sans objet')
                                ba_dict['fournisseur'] = ba_dict.get('fournisseur_nom', 'N/A')
                            ba_list.append(ba_dict)
                        results = {'bons_achat': ba_list}
                    else:
                        results = {'info': 'Aucun bon d\'achat trouvé dans la base de données.'}
                except Exception as e:
                    results = {'error': str(e)}
            elif query.lower() in ['employé', 'employés', 'employe', 'employes', 'personnel']:
                # Récupérer tous les employés
                try:
                    employes = self.db.execute_query("""
                        SELECT e.*, 
                               GROUP_CONCAT(ec.nom_competence || ' (' || ec.niveau || ')', ', ') as competences
                        FROM employees e
                        LEFT JOIN employee_competences ec ON e.id = ec.employee_id
                        WHERE e.statut = 'ACTIF'
                        GROUP BY e.id
                        ORDER BY e.nom, e.prenom
                        LIMIT 50
                    """)
                    
                    if employes:
                        results = {'employes': [dict(e) for e in employes]}
                    else:
                        results = {'info': 'Aucun employé trouvé dans la base de données.'}
                except Exception as e:
                    results = {'error': str(e)}
            elif query.lower().startswith('employé') or query.lower().startswith('employe'):
                # Recherche d'employé spécifique
                if query.lower().startswith('employés'):
                    search_term = query[8:].strip() if len(query) > 8 else ''
                elif query.lower().startswith('employé'):
                    search_term = query[7:].strip() if len(query) > 7 else ''
                elif query.lower().startswith('employes'):
                    search_term = query[8:].strip() if len(query) > 8 else ''
                else:
                    search_term = query[7:].strip() if len(query) > 7 else ''
                
                if search_term:
                    try:
                        employes = self.db.execute_query("""
                            SELECT e.*, 
                                   GROUP_CONCAT(ec.nom_competence || ' (' || ec.niveau || ')', ', ') as competences
                            FROM employees e
                            LEFT JOIN employee_competences ec ON e.id = ec.employee_id
                            WHERE LOWER(e.nom) LIKE LOWER(?)
                               OR LOWER(e.prenom) LIKE LOWER(?)
                               OR LOWER(e.nom || ' ' || e.prenom) LIKE LOWER(?)
                               OR LOWER(e.prenom || ' ' || e.nom) LIKE LOWER(?)
                               OR LOWER(e.poste) LIKE LOWER(?)
                               OR LOWER(e.departement) LIKE LOWER(?)
                            GROUP BY e.id
                            ORDER BY e.nom, e.prenom
                            LIMIT 20
                        """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', 
                              f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
                        
                        if employes:
                            results = {'employes': [dict(e) for e in employes]}
                        else:
                            results = {'info': f'Aucun employé trouvé pour "{search_term}".'}
                    except Exception as e:
                        results = {'error': str(e)}
                else:
                    results = self._search_erp_data(query)
            elif query.lower().startswith('contact'):
                # Recherche de contact spécifique
                if query.lower().startswith('contacts'):
                    search_term = query[8:].strip() if len(query) > 8 else ''
                else:
                    search_term = query[7:].strip() if len(query) > 7 else ''
                if search_term:
                    try:
                        contacts = self.db.execute_query("""
                            SELECT c.*, comp.nom as entreprise_nom
                            FROM contacts c
                            LEFT JOIN companies comp ON c.company_id = comp.id
                            WHERE LOWER(c.nom_famille) LIKE LOWER(?) 
                               OR LOWER(c.prenom) LIKE LOWER(?)
                               OR LOWER(c.nom_famille || ' ' || c.prenom) LIKE LOWER(?)
                               OR LOWER(c.prenom || ' ' || c.nom_famille) LIKE LOWER(?)
                               OR LOWER(c.email) LIKE LOWER(?)
                               OR LOWER(comp.nom) LIKE LOWER(?)
                            ORDER BY c.nom_famille, c.prenom
                            LIMIT 20
                        """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', 
                              f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
                        
                        if contacts:
                            results = {'contacts': [dict(c) for c in contacts]}
                        else:
                            results = {'info': f'Aucun contact trouvé pour "{search_term}".'}
                    except Exception as e:
                        results = {'error': str(e)}
                else:
                    results = self._search_erp_data(query)
            elif query.lower() in ['entreprise', 'entreprises', 'company', 'companies', 'societe', 'societes']:
                # Récupérer toutes les entreprises
                try:
                    entreprises = self.db.execute_query("""
                        SELECT c.*, 
                               (SELECT COUNT(*) FROM contacts ct WHERE ct.company_id = c.id) as nb_contacts,
                               (SELECT COUNT(*) FROM projects p WHERE p.client_company_id = c.id) as nb_projets
                        FROM companies c
                        ORDER BY c.nom
                        LIMIT 50
                    """)
                    
                    if entreprises:
                        results = {'entreprises': [dict(e) for e in entreprises]}
                    else:
                        results = {'info': 'Aucune entreprise trouvée dans la base de données.'}
                except Exception as e:
                    results = {'error': str(e)}
            elif query.lower().startswith('entreprise'):
                # Recherche d'entreprise spécifique
                search_term = query[10:].strip() if len(query) > 10 else ''
                if query.lower().startswith('entreprises'):
                    search_term = query[11:].strip() if len(query) > 11 else ''
                
                if search_term:
                    try:
                        entreprises = self.db.execute_query("""
                            SELECT c.*, 
                                   (SELECT COUNT(*) FROM contacts ct WHERE ct.company_id = c.id) as nb_contacts,
                                   (SELECT COUNT(*) FROM projects p WHERE p.client_company_id = c.id) as nb_projets
                            FROM companies c
                            WHERE LOWER(c.nom) LIKE LOWER(?)
                               OR LOWER(c.secteur) LIKE LOWER(?)
                               OR LOWER(c.ville) LIKE LOWER(?)
                            ORDER BY c.nom
                            LIMIT 20
                        """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
                        
                        if entreprises:
                            results = {'entreprises': [dict(e) for e in entreprises]}
                        else:
                            results = {'info': f'Aucune entreprise trouvée pour "{search_term}".'}
                    except Exception as e:
                        results = {'error': str(e)}
                else:
                    results = self._search_erp_data(query)
            elif query.lower() in ['fournisseur', 'fournisseurs', 'supplier', 'suppliers']:
                # Récupérer tous les fournisseurs
                try:
                    fournisseurs = self.db.execute_query("""
                        SELECT f.*, c.nom, c.adresse, c.secteur,
                               (SELECT COUNT(*) FROM approvisionnements a WHERE a.fournisseur_id = f.id) as nb_commandes
                        FROM fournisseurs f
                        JOIN companies c ON f.company_id = c.id
                        WHERE f.est_actif = 1
                        ORDER BY c.nom
                        LIMIT 50
                    """)
                    
                    if fournisseurs:
                        results = {'fournisseurs': [dict(f) for f in fournisseurs]}
                    else:
                        results = {'info': 'Aucun fournisseur trouvé dans la base de données.'}
                except Exception as e:
                    results = {'error': str(e)}
            elif query.lower().startswith('fournisseur'):
                # Recherche de fournisseur spécifique
                search_term = query[11:].strip() if len(query) > 11 else ''
                if query.lower().startswith('fournisseurs'):
                    search_term = query[12:].strip() if len(query) > 12 else ''
                
                if search_term:
                    try:
                        fournisseurs = self.db.execute_query("""
                            SELECT f.*, c.nom, c.adresse, c.secteur,
                                   (SELECT COUNT(*) FROM approvisionnements a WHERE a.fournisseur_id = f.id) as nb_commandes
                            FROM fournisseurs f
                            JOIN companies c ON f.company_id = c.id
                            WHERE f.est_actif = 1
                              AND (LOWER(c.nom) LIKE LOWER(?)
                                   OR LOWER(f.code_fournisseur) LIKE LOWER(?)
                                   OR LOWER(f.categorie_produits) LIKE LOWER(?)
                                   OR LOWER(c.secteur) LIKE LOWER(?))
                            ORDER BY c.nom
                            LIMIT 20
                        """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
                        
                        if fournisseurs:
                            results = {'fournisseurs': [dict(f) for f in fournisseurs]}
                        else:
                            results = {'info': f'Aucun fournisseur trouvé pour "{search_term}".'}
                    except Exception as e:
                        results = {'error': str(e)}
                else:
                    results = self._search_erp_data(query)
            elif query.lower().startswith('heures'):
                # Extraction du nom d'employé et de la période
                parts = query[6:].strip()  # Enlever "heures"
                week_date = None
                employee_name = parts
                
                # Vérifier si une période est spécifiée
                if 'semaine dernière' in parts.lower():
                    employee_name = parts.lower().replace('semaine dernière', '').strip()
                    week_date = 'semaine dernière'
                elif re.search(r'\d{4}-\d{2}-\d{2}', parts):
                    # Extraire la date
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', parts)
                    if date_match:
                        week_date = date_match.group(1)
                        employee_name = parts.replace(week_date, '').strip()
                
                if employee_name:
                    hours_data = self._get_employee_hours(employee_name, week_date)
                    
                    # Utiliser le formatage dédié pour les heures
                    return self._format_employee_hours(hours_data)
                else:
                    return "❌ Veuillez spécifier le nom de l'employé (ex: `/erp heures Denis Jetté`)"
            elif query.lower().startswith('rapport projet'):
                # Extraction de l'identifiant du projet
                project_id = query[14:].strip()  # Enlever "rapport projet"
                
                if project_id:
                    # Accepter différents formats de projet
                    project_id = project_id.upper().replace('PRJ-', '').replace('PRJ', '')
                    report_data = self._get_project_report(project_id)
                    
                    # Utiliser le formatage dédié pour le rapport projet
                    return self._format_project_report(report_data)
                else:
                    return "❌ Veuillez spécifier l'identifiant du projet (ex: `/erp rapport projet 25-251`)"
            elif query.lower().startswith('rapport bt') or query.lower().startswith('rapport bon'):
                # Extraction du numéro de bon de travail
                if query.lower().startswith('rapport bt'):
                    bt_numero = query[10:].strip()  # Enlever "rapport bt"
                else:
                    bt_numero = query[11:].strip()  # Enlever "rapport bon"
                
                if bt_numero:
                    # Normaliser le numéro
                    bt_numero = bt_numero.upper()
                    if not bt_numero.startswith('BT-'):
                        bt_numero = 'BT-' + bt_numero.replace('BT', '')
                    
                    report_data = self._get_bt_report(bt_numero)
                    
                    # Utiliser le formatage dédié pour le rapport BT
                    return self._format_bt_report(report_data)
                else:
                    return "❌ Veuillez spécifier le numéro du bon de travail (ex: `/erp rapport bt BT-2025-001`)"
            elif query.lower() == 'alertes':
                # Récupérer toutes les alertes importantes
                alertes = self._get_alertes()
                return self._format_alertes(alertes)
            elif query.lower() in ['disponibilité', 'disponibilite', 'disponible', 'disponibles']:
                # Récupérer les employés disponibles
                employes_dispo = self._get_employes_disponibles()
                return self._format_employes_disponibles(employes_dispo)
            elif query.lower() == 'en cours':
                # Récupérer tous les bons de travail en cours
                bt_en_cours = self._get_bt_en_cours()
                return self._format_bt_en_cours(bt_en_cours)
            elif query.lower() in ['rupture', 'ruptures']:
                # Récupérer les produits en rupture de stock
                ruptures = self._get_ruptures_stock()
                return self._format_ruptures_stock(ruptures)
            elif query.lower() in ['projets retard', 'projet retard', 'retard', 'retards']:
                # Récupérer les projets en retard
                projets_retard = self._get_projets_retard()
                return self._format_projets_retard(projets_retard)
            elif query.lower() in ['dashboard', 'tableau de bord', 'vue ensemble']:
                # Afficher le dashboard général
                dashboard_data = self._get_dashboard_data()
                return self._format_dashboard(dashboard_data)
            elif query.lower() in ['impayés', 'impayes', 'factures impayées']:
                # Récupérer les factures impayées
                impayes = self._get_factures_impayees()
                return self._format_impayes(impayes)
            elif query.lower().startswith('charge'):
                # Extraction de la semaine (optionnelle)
                parts = query[6:].strip()  # Enlever "charge"
                semaine = parts if parts else None
                charge_data = self._get_charge_travail(semaine)
                return self._format_charge_travail(charge_data)
            elif query.lower() in ['à commander', 'a commander', 'commander', 'réappro', 'reappro']:
                # Récupérer les produits à commander
                a_commander = self._get_produits_a_commander()
                return self._format_a_commander(a_commander)
            elif query.lower().startswith('performance'):
                # Extraction du mois (optionnel)
                parts = query[11:].strip()  # Enlever "performance"
                mois = parts if parts else None
                perf_data = self._get_performance_mensuelle(mois)
                return self._format_performance(perf_data)
            else:
                # Recherche normale avec le terme fourni
                results = self._search_erp_data(query)
            
            # Enrichir avec Claude si disponible
            if self.client and results:
                context = {
                    'recherche_erp': results,
                    'instruction_stricte': "IMPORTANT: Présente UNIQUEMENT les résultats fournis dans recherche_erp. N'ajoute AUCUNE donnée inventée."
                }
                return self._get_claude_response(
                    f"Présente ces résultats de recherche ERP de manière claire: {json.dumps(results, ensure_ascii=False)}",
                    context
                )
            else:
                return self._format_search_results(results)
        
        # Question normale - utiliser Claude avec contexte ERP
        else:
            # Vérifier si la question concerne l'ERP
            erp_keywords = ['projet', 'stock', 'inventaire', 'employé', 'client', 'production', 'bon de travail', 'produit', 'article', 'référence', 'bt', 'bon', 'bons', 'devis', 'quote', 'estimation']
            
            context = {}
            
            # Si mots-clés ERP détectés, chercher des données pertinentes
            if any(keyword in input_lower for keyword in erp_keywords):
                # Pour les questions sur les projets (en cours, actifs, ou tous)
                if 'projet' in input_lower and any(word in input_lower for word in ['en cours', 'actif', 'liste', 'montre', 'affiche', 'tous']):
                    projets_actifs = self._get_current_projects()
                    if projets_actifs:
                        context['projets_actifs'] = projets_actifs
                        context['format_projets'] = "tableau"  # Indication pour formater en tableau
                        context['instruction_stricte'] = "IMPORTANT: Présente UNIQUEMENT les projets fournis dans projets_actifs. N'invente AUCUN autre projet."
                # Aussi pour la commande directe "projets"
                elif input_lower.strip() == 'projets' or input_lower.strip() == 'projet':
                    projets_actifs = self._get_current_projects()
                    if projets_actifs:
                        context['projets_actifs'] = projets_actifs
                        context['format_projets'] = "tableau"
                        context['instruction_stricte'] = "IMPORTANT: Présente UNIQUEMENT les projets fournis dans projets_actifs. N'invente AUCUN autre projet."
                
                # Pour les questions sur les produits
                elif 'produit' in input_lower or any(word in input_lower for word in ['produits', 'article', 'articles', 'référence']):
                    # Récupérer les produits
                    produits = self.db.execute_query("""
                        SELECT code_produit, nom, description, categorie, materiau, nuance, 
                               dimensions, unite_vente, prix_unitaire, 
                               stock_disponible, stock_minimum, fournisseur_principal
                        FROM produits 
                        WHERE actif = 1
                        ORDER BY categorie, nom
                        LIMIT 20
                    """)
                    if produits:
                        context['produits_disponibles'] = [dict(p) for p in produits]
                        context['format_produits'] = "tableau"
                        context['instruction_stricte'] = "IMPORTANT: Présente UNIQUEMENT les produits fournis dans produits_disponibles. N'invente AUCUN produit."
                
                # Pour les questions sur les bons de travail
                elif any(word in input_lower for word in ['bon de travail', 'bons de travail', 'bt']) or (
                    'bon' in input_lower and 'travail' in input_lower):
                    # Vérifier si c'est une demande de BT spécifique
                    import re
                    bt_pattern = re.search(r'(bt[- ]?\d{4}[- ]?\d{3})', input_lower)
                    if bt_pattern:
                        # Normaliser le numéro de BT
                        bt_numero = bt_pattern.group(1).upper().replace(' ', '-')
                        if not bt_numero.startswith('BT-'):
                            bt_numero = 'BT-' + bt_numero[2:]
                        
                        # Récupérer les détails du BT
                        bt_details = self._get_bt_details(bt_numero)
                        if 'bt_details' in bt_details:
                            context['bt_details'] = bt_details['bt_details']
                            context['format_bt_details'] = "détaillé"
                            context['instruction_stricte'] = "IMPORTANT: Présente UNIQUEMENT les informations fournies dans bt_details. N'invente AUCUNE donnée."
                    else:
                        # Récupérer la liste des bons de travail
                        bts = self.db.execute_query("""
                            SELECT f.numero_document, f.statut, f.priorite, f.created_at, 
                                   f.metadonnees_json, f.notes,
                                   (SELECT fl.description FROM formulaire_lignes fl 
                                    WHERE fl.formulaire_id = f.id 
                                    ORDER BY fl.sequence_ligne LIMIT 1) as premiere_ligne
                            FROM formulaires f 
                            WHERE f.type_formulaire = 'BON_TRAVAIL'
                            ORDER BY f.created_at DESC
                            LIMIT 20
                        """)
                        
                        if bts:
                            # Traiter les métadonnées JSON pour extraire le titre
                            bons_travail = []
                            for bt in bts:
                                bt_dict = dict(bt)
                                if bt_dict.get('metadonnees_json'):
                                    try:
                                        meta = json.loads(bt_dict['metadonnees_json'])
                                        bt_dict['titre'] = meta.get('project_name', 'Sans titre')
                                        bt_dict['client'] = meta.get('client_name', 'N/A')
                                    except:
                                        bt_dict['titre'] = bt_dict.get('premiere_ligne', 'Sans titre')
                                        bt_dict['client'] = 'N/A'
                                else:
                                    bt_dict['titre'] = bt_dict.get('premiere_ligne', 'Sans titre')
                                    bt_dict['client'] = 'N/A'
                                bons_travail.append(bt_dict)
                            
                            context['bons_travail'] = bons_travail
                            context['format_bons_travail'] = "tableau"
                            context['instruction_stricte'] = "IMPORTANT: Présente UNIQUEMENT les bons de travail fournis. N'invente AUCUN bon de travail."
                
                # Recherche automatique générale
                search_results = self._search_erp_data(user_input)
                if search_results:
                    context['donnees_erp'] = search_results
                    context['instruction_stricte'] = "IMPORTANT: Base-toi UNIQUEMENT sur les données fournies dans donnees_erp. N'invente AUCUNE information supplémentaire."
                
                # Ajouter les stats si demandé
                if any(word in input_lower for word in ['statistique', 'stats', 'nombre', 'combien']):
                    stats = self._get_erp_statistics()
                    if stats:
                        context['statistiques'] = stats
                        context['instruction_stricte'] = "IMPORTANT: Utilise UNIQUEMENT les statistiques fournies. N'invente AUCUN chiffre ou donnée."
            
            return self._get_claude_response(user_input, context)
    
    def _get_debug_info(self) -> str:
        """Retourne des informations de debug sur la connexion DB"""
        lines = ["**🔧 Debug - Informations de connexion**\n"]
        
        # Info environnement
        lines.append(f"**Environnement:**")
        lines.append(f"- OS: {os.name}")
        lines.append(f"- Répertoire actuel: {os.getcwd()}")
        lines.append(f"- Sur Render: {'OUI' if os.path.exists('/opt/render/project') else 'NON'}")
        lines.append("")
        
        # Vérifier la DB
        if self.db:
            lines.append("**Base de données:**")
            lines.append(f"- Instance DB: ✅ Disponible")
            
            # Afficher le chemin de la DB si disponible
            if hasattr(self.db, 'db_path'):
                lines.append(f"- Chemin DB: {self.db.db_path}")
                # Vérifier si le fichier existe
                if os.path.exists(self.db.db_path):
                    lines.append(f"- Fichier DB existe: ✅")
                    lines.append(f"- Taille: {os.path.getsize(self.db.db_path) / 1024 / 1024:.2f} MB")
                else:
                    lines.append(f"- Fichier DB existe: ❌")
            
            # Tester la connexion
            try:
                # Test simple
                result = self.db.execute_query("SELECT COUNT(*) as count FROM sqlite_master WHERE type='table'")
                if result:
                    lines.append(f"- Tables dans la DB: {result[0]['count']}")
                
                # Compter les projets
                projects_count = self.db.execute_query("SELECT COUNT(*) as count FROM projects")
                if projects_count:
                    lines.append(f"- Nombre total de projets: {projects_count[0]['count']}")
                
                # Projets en cours
                en_cours = self.db.execute_query("SELECT COUNT(*) as count FROM projects WHERE statut = 'EN COURS'")
                if en_cours:
                    lines.append(f"- Projets en cours: {en_cours[0]['count']}")
                
                # Afficher quelques projets
                sample_projects = self.db.execute_query("""
                    SELECT nom_projet, statut 
                    FROM projects 
                    WHERE statut = 'EN COURS' 
                    LIMIT 3
                """)
                
                if sample_projects:
                    lines.append("\n**Exemples de projets en cours:**")
                    for p in sample_projects:
                        lines.append(f"- {p['nom_projet']} ({p['statut']})")
                else:
                    lines.append("- ⚠️ Aucun projet en cours trouvé")
                    
            except Exception as e:
                lines.append(f"- ❌ Erreur lors du test: {str(e)}")
        else:
            lines.append("**Base de données:** ❌ Non disponible")
        
        # Vérifier la clé API
        lines.append("\n**API Claude:**")
        if self.api_key:
            lines.append(f"- Clé configurée: ✅ (commence par {self.api_key[:10]}...)")
            lines.append(f"- Client initialisé: {'✅' if self.client else '❌'}")
        else:
            lines.append("- Clé configurée: ❌")
        
        return "\n".join(lines)
    
    def _get_help_text(self) -> str:
        """Retourne le texte d'aide"""
        return """
**🤖 Assistant IA ERP - Aide**

**Commandes disponibles:**
- `/erp [recherche]` - Rechercher dans vos données ERP
- `/stats` - Afficher les statistiques globales
- `/help` - Afficher cette aide
- `/debug` - Afficher les informations de debug

**Exemples de recherches ERP:**
- `/erp projet automobile` - Recherche de projets
- `/erp stock acier inoxydable` - État des stocks
- `/erp employé soudeur` - Recherche d'employés
- `/erp client quebec` - Recherche de clients
- `/erp heures Denis Jetté` - Heures travaillées cette semaine
- `/erp heures Denis Jetté semaine dernière` - Heures de la semaine dernière
- `/erp heures Denis Jetté 2025-01-13` - Heures d'une semaine spécifique

**Rapports détaillés:**
- `/erp rapport projet 25-251` - Rapport complet d'un projet avec analyse financière
- `/erp rapport bt BT-2025-001` - Rapport détaillé d'un bon de travail

**Tableaux de bord et alertes:**
- `/erp alertes` - Toutes les alertes importantes (stocks, échéances, etc.)
- `/erp disponibilité` - Employés disponibles actuellement
- `/erp en cours` - Bons de travail en cours de production
- `/erp rupture` - Produits en rupture ou stock faible
- `/erp projets retard` - Projets en retard ou à risque
- `/erp dashboard` - Vue d'ensemble avec KPIs principaux
- `/erp impayés` - Factures clients en retard de paiement
- `/erp charge [semaine]` - Charge de travail des employés
- `/erp à commander` - Produits à réapprovisionner
- `/erp performance [mois]` - Indicateurs de performance mensuels

**Questions directes (sans commande):**
- "Quel est l'état du projet AutoTech?"
- "Combien d'employés sont disponibles?"
- "Analyse la charge de travail cette semaine"
- "Quelles sont les meilleures pratiques pour souder l'aluminium?"

**Capacités:**
- Analyse de vos données de production
- Recommandations basées sur votre inventaire
- Expertise en métallurgie et fabrication
- Optimisation des processus

L'assistant a accès à toutes vos données ERP et peut les analyser pour vous fournir des insights pertinents.
"""
    
    def _format_statistics(self, stats: Dict) -> str:
        """Formate les statistiques pour l'affichage avec style amélioré"""
        if not stats:
            return "📊 Aucune statistique disponible."
        
        lines = []
        lines.append("## 📊 **Statistiques ERP**\n")
        
        # Projets avec tableau
        if 'projets' in stats and stats['projets']:
            lines.append("### 📁 **Répartition des projets**\n")
            lines.append("| **Statut** | **Nombre** | **Valeur totale** |")
            lines.append("|------------|------------|-------------------|")
            
            total_nombre = 0
            total_valeur = 0
            
            for statut, data in stats['projets'].items():
                nombre = data['nombre']
                valeur = data['valeur']
                total_nombre += nombre
                total_valeur += valeur
                lines.append(f"| {statut} | {nombre} | {valeur:,.0f} $ |")
            
            lines.append(f"| **TOTAL** | **{total_nombre}** | **{total_valeur:,.0f} $** |")
            lines.append("")
        
        # Autres stats en cartes
        lines.append("### 📈 **Indicateurs clés**\n")
        
        if 'stock_faible' in stats:
            lines.append(f"**⚠️ Stock faible**")
            lines.append(f"- Articles concernés: `{stats['stock_faible']}`")
            lines.append("")
        
        if 'employes_disponibles' in stats:
            lines.append(f"**👥 Ressources humaines**")
            lines.append(f"- Employés disponibles: `{stats['employes_disponibles']}`")
            lines.append("")
        
        if 'bons_travail_actifs' in stats:
            lines.append(f"**📋 Production**")
            lines.append(f"- Bons de travail actifs: `{stats['bons_travail_actifs']}`")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_search_results(self, results: Dict) -> str:
        """Formate les résultats de recherche avec un style amélioré"""
        if 'error' in results:
            return f"❌ **Erreur:** {results['error']}"
        
        if not results:
            return "🔍 Aucun résultat trouvé."
        
        lines = []
        lines.append("## 🔍 Résultats de recherche ERP\n")
        
        # Projets avec tableau
        if 'projets' in results and results['projets']:
            lines.append("### 📁 **Projets trouvés**\n")
            lines.append("| **Nom du projet** | **Statut** | **Client** | **Budget** |")
            lines.append("|-------------------|------------|------------|------------|")
            
            for p in results['projets']:
                nom = p['nom_projet']
                statut = p['statut']
                client = p.get('client_nom', 'N/A')
                budget = f"{p['prix_estime']:,.0f} $" if p.get('prix_estime') else "N/A"
                lines.append(f"| {nom} | {statut} | {client} | {budget} |")
            lines.append("")
        
        # Produits avec tableau
        if 'produits' in results and results['produits']:
            lines.append("### 🔧 **Produits trouvés**\n")
            lines.append("| **Code** | **Nom** | **Catégorie** | **Stock** | **Prix** |")
            lines.append("|----------|---------|---------------|-----------|----------|")
            
            for prod in results['produits']:
                code = prod.get('code_produit', '')
                nom = prod.get('nom', '')
                categorie = prod.get('categorie', '')
                stock = f"{prod.get('stock_disponible', 0)} {prod.get('unite_vente', '')}"
                prix = f"{prod.get('prix_unitaire', 0):.2f} $"
                lines.append(f"| {code} | {nom} | {categorie} | {stock} | {prix} |")
            lines.append("")
        
        # Inventaire avec style carte
        if 'inventaire' in results and results['inventaire']:
            lines.append("### 📦 **Articles d'inventaire**\n")
            for item in results['inventaire']:
                lines.append(f"**➤ {item['nom']}**")
                lines.append(f"- 📊 Quantité: `{item['quantite_metric']}`")
                lines.append(f"- 📈 Statut: `{item['statut']}`")
                lines.append("")
        
        # Employés avec tableau
        if 'employes' in results and results['employes']:
            lines.append("### 👥 **Employés**\n")
            lines.append("| **Nom** | **Poste** | **Compétences** |")
            lines.append("|---------|-----------|-----------------|")
            
            for emp in results['employes']:
                nom_complet = f"{emp['prenom']} {emp['nom']}"
                poste = emp['poste']
                competences = emp.get('competences', 'N/A')
                lines.append(f"| {nom_complet} | {poste} | {competences} |")
            lines.append("")
        
        # Entreprises avec tableau
        if 'entreprises' in results and results['entreprises']:
            lines.append("### 🏢 **Entreprises trouvées**\n")
            lines.append("| **Nom** | **Secteur** | **Ville** | **Email** | **Téléphone** | **Contacts** | **Projets** |")
            lines.append("|----------|-------------|-----------|-----------|---------------|--------------|-------------|")
            
            for comp in results['entreprises']:
                nom = comp.get('nom', '')
                secteur = comp.get('secteur', 'N/A')
                ville = comp.get('ville', 'N/A')
                email = comp.get('email', 'N/A')
                telephone = comp.get('telephone', 'N/A')
                nb_contacts = comp.get('nb_contacts', 0)
                nb_projets = comp.get('nb_projets', 0)
                lines.append(f"| {nom} | {secteur} | {ville} | {email} | {telephone} | {nb_contacts} | {nb_projets} |")
            lines.append("")
        
        # Bons de travail avec tableau
        if 'bons_travail' in results and results['bons_travail']:
            lines.append("### 🔧 **Bons de travail trouvés**\n")
            lines.append("| **Numéro** | **Titre** | **Client** | **Statut** | **Priorité** |")
            lines.append("|------------|-----------|------------|------------|--------------|")
            
            for bt in results['bons_travail']:
                numero = bt.get('numero_document', '')
                titre = bt.get('titre', 'Sans titre')
                client = bt.get('client', 'N/A')
                statut = bt.get('statut', 'N/A')
                priorite = bt.get('priorite', 'NORMALE')
                lines.append(f"| {numero} | {titre} | {client} | {statut} | {priorite} |")
            lines.append("")
        
        # Devis avec tableau
        if 'devis' in results and results['devis']:
            lines.append("### 💰 **Devis trouvés**\n")
            lines.append("| **Numéro** | **Titre/Objet** | **Client** | **Montant** | **Statut** |")
            lines.append("|------------|-----------------|------------|-------------|------------|")
            
            for devis in results['devis']:
                numero = devis.get('numero_document', '')
                titre = devis.get('titre', 'Sans titre')
                client = devis.get('client', 'N/A')
                montant = f"{devis.get('montant_total', 0):,.2f} $" if devis.get('montant_total') else 'N/A'
                statut = devis.get('statut', 'N/A')
                lines.append(f"| {numero} | {titre} | {client} | {montant} | {statut} |")
            lines.append("")
        
        # Contacts avec tableau
        if 'contacts' in results and results['contacts']:
            lines.append("### 👥 **Contacts trouvés**\n")
            lines.append("| **Nom complet** | **Entreprise** | **Email** | **Téléphone** | **Rôle/Poste** |")
            lines.append("|-----------------|----------------|-----------|---------------|----------------|")
            
            for contact in results['contacts']:
                nom_complet = f"{contact.get('prenom', '')} {contact.get('nom_famille', '')}"
                entreprise = contact.get('entreprise_nom', 'N/A')
                email = contact.get('email', 'N/A')
                telephone = contact.get('telephone', 'N/A')
                role = contact.get('role_poste', 'N/A')
                lines.append(f"| {nom_complet} | {entreprise} | {email} | {telephone} | {role} |")
            lines.append("")
        
        # Demandes de prix avec tableau
        if 'demandes_prix' in results and results['demandes_prix']:
            lines.append("### 💰 **Demandes de prix trouvées**\n")
            lines.append("| **Numéro** | **Objet** | **Fournisseur** | **Date création** | **Statut** |")
            lines.append("|------------|-----------|-----------------|-------------------|------------|")
            
            for dp in results['demandes_prix']:
                numero = dp.get('numero_document', '')
                objet = dp.get('objet', 'Sans objet')
                fournisseur = dp.get('fournisseur', 'N/A')
                date = dp.get('created_at', 'N/A')
                statut = dp.get('statut', 'N/A')
                lines.append(f"| {numero} | {objet} | {fournisseur} | {date} | {statut} |")
            lines.append("")
        
        # Fournisseurs avec tableau
        if 'fournisseurs' in results and results['fournisseurs']:
            lines.append("### 🚚 **Fournisseurs trouvés**\n")
            lines.append("| **Nom** | **Code** | **Catégorie** | **Secteur** | **Délai livraison** | **Évaluation** | **Commandes** |")
            lines.append("|---------|----------|---------------|-------------|---------------------|----------------|---------------|")
            
            for fourn in results['fournisseurs']:
                nom = fourn.get('nom', '')
                code = fourn.get('code_fournisseur', 'N/A')
                categorie = fourn.get('categorie_produits', 'N/A')
                secteur = fourn.get('secteur', 'N/A')
                delai = f"{fourn.get('delai_livraison_moyen', 'N/A')} jours" if fourn.get('delai_livraison_moyen') else 'N/A'
                evaluation = f"{fourn.get('evaluation_qualite', 5)}/5" if fourn.get('evaluation_qualite') else '5/5'
                nb_commandes = fourn.get('nb_commandes', 0)
                lines.append(f"| {nom} | {code} | {categorie} | {secteur} | {delai} | {evaluation} | {nb_commandes} |")
            lines.append("")
        
        # Bons d'achat avec tableau
        if 'bons_achat' in results and results['bons_achat']:
            lines.append("### 🛒 **Bons d'achat trouvés**\n")
            lines.append("| **Numéro** | **Objet** | **Fournisseur** | **Montant** | **Date création** | **Statut** |")
            lines.append("|------------|-----------|-----------------|-------------|-------------------|------------|")
            
            for ba in results['bons_achat']:
                numero = ba.get('numero_document', '')
                objet = ba.get('objet', 'Sans objet')
                fournisseur = ba.get('fournisseur', 'N/A')
                montant = f"{ba.get('montant_total', 0):,.2f} $" if ba.get('montant_total') else 'N/A'
                date = ba.get('created_at', 'N/A')
                statut = ba.get('statut', 'N/A')
                lines.append(f"| {numero} | {objet} | {fournisseur} | {montant} | {date} | {statut} |")
            lines.append("")
        
        # Message informatif
        if 'info' in results:
            lines.append(f"ℹ️ **Information**: {results['info']}")
        
        return "\n".join(lines)
    
    def _format_bt_details(self, details: Dict) -> str:
        """Formate les détails complets d'un bon de travail"""
        if 'error' in details:
            return f"❌ **Erreur:** {details['error']}"
        
        if 'bt_details' not in details:
            return "❌ Aucun détail disponible pour ce bon de travail."
        
        bt = details['bt_details']
        lines = []
        
        # En-tête du BT
        lines.append(f"## 🔧 **{bt.get('numero_document', 'N/A')} - {bt.get('titre', 'Sans titre')}**\n")
        
        # Informations générales
        lines.append("### 📋 **Informations générales**")
        lines.append(f"- **Client**: {bt.get('client', 'N/A')}")
        lines.append(f"- **Statut**: `{bt.get('statut', 'N/A')}`")
        lines.append(f"- **Priorité**: `{bt.get('priorite', 'NORMALE')}`")
        lines.append(f"- **Date création**: {bt.get('created_at', 'N/A')}")
        if bt.get('date_echeance'):
            lines.append(f"- **Date échéance**: {bt['date_echeance']}")
        if bt.get('notes'):
            lines.append(f"- **Notes**: {bt['notes']}")
        lines.append("")
        
        # Opérations/Lignes
        if bt.get('operations'):
            lines.append("### 📐 **Opérations du bon de travail**")
            lines.append("| **#** | **Description** | **Quantité** | **Unité** | **Prix unit.** | **Total** |")
            lines.append("|-------|-----------------|--------------|-----------|----------------|-----------|")
            
            for op in bt['operations']:
                seq = op.get('sequence_ligne', '')
                desc = op.get('description', '')
                qte = op.get('quantite', 0)
                unite = op.get('unite', '')
                prix = op.get('prix_unitaire', 0)
                total = op.get('montant_ligne', qte * prix)
                lines.append(f"| {seq} | {desc} | {qte} | {unite} | {prix:.2f} $ | {total:.2f} $ |")
            lines.append("")
        
        # Assignations d'employés
        if bt.get('assignations'):
            lines.append("### 👥 **Employés assignés**")
            lines.append("| **Nom** | **Poste** | **Date assignation** |")
            lines.append("|---------|-----------|---------------------|")
            
            for ass in bt['assignations']:
                nom = f"{ass.get('prenom', '')} {ass.get('nom', '')}"
                poste = ass.get('poste', 'N/A')
                date = ass.get('date_assignation', 'N/A')
                lines.append(f"| {nom} | {poste} | {date} |")
            lines.append("")
        
        # Réservations de postes
        if bt.get('reservations_postes'):
            lines.append("### 🏭 **Postes de travail réservés**")
            lines.append("| **Poste** | **Date réservation** | **Date prévue** | **Statut** |")
            lines.append("|-----------|---------------------|-----------------|------------|")
            
            for res in bt['reservations_postes']:
                poste = res.get('nom_poste', 'N/A')
                date_res = res.get('date_reservation', 'N/A')
                date_prev = res.get('date_prevue', 'N/A')
                statut = res.get('statut', 'N/A')
                lines.append(f"| {poste} | {date_res} | {date_prev} | {statut} |")
            lines.append("")
        
        # Avancement
        if bt.get('avancement'):
            lines.append("### 📊 **Historique d'avancement**")
            lines.append("| **Date** | **Modifié par** | **% Réalisé** | **Temps réel** | **Notes** |")
            lines.append("|----------|-----------------|---------------|----------------|-----------|")
            
            for av in bt['avancement']:
                date = av.get('updated_at', 'N/A')
                emp = f"{av.get('prenom', '')} {av.get('nom', '')}" if av.get('nom') else 'N/A'
                pct = av.get('pourcentage_realise', 0)
                temps = av.get('temps_reel', 0)
                notes = av.get('notes_avancement', '')
                lines.append(f"| {date} | {emp} | {pct}% | {temps}h | {notes} |")
            lines.append("")
        
        # Total
        if bt.get('montant_total'):
            lines.append(f"### 💰 **Montant total**: {bt['montant_total']:.2f} $")
        
        return "\n".join(lines)
    
    def _format_devis_details(self, details: Dict) -> str:
        """Formate les détails complets d'un devis"""
        if 'error' in details:
            return f"❌ **Erreur:** {details['error']}"
        
        if 'devis_details' not in details:
            return "❌ Aucun détail disponible pour ce devis."
        
        devis = details['devis_details']
        lines = []
        
        # En-tête du devis
        lines.append(f"## 💰 **{devis.get('numero_document', 'N/A')} - {devis.get('titre', 'Sans titre')}**\n")
        
        # Informations générales
        lines.append("### 📋 **Informations générales**")
        lines.append(f"- **Client**: {devis.get('client', 'N/A')}")
        lines.append(f"- **Statut**: `{devis.get('statut', 'N/A')}`")
        lines.append(f"- **Date création**: {devis.get('created_at', 'N/A')}")
        lines.append(f"- **Validité**: {devis.get('validite', 30)} jours")
        lines.append(f"- **Conditions**: {devis.get('conditions', 'Net 30 jours')}")
        if devis.get('notes'):
            lines.append(f"- **Notes**: {devis['notes']}")
        lines.append("")
        
        # Lignes du devis
        if devis.get('lignes'):
            lines.append("### 📦 **Articles du devis**")
            lines.append("| **#** | **Description** | **Catégorie** | **Quantité** | **Unité** | **Prix unit.** | **Total** |")
            lines.append("|-------|-----------------|---------------|--------------|-----------|----------------|-----------|")
            
            for ligne in devis['lignes']:
                seq = ligne.get('sequence_ligne', '')
                desc = ligne.get('description', '')
                cat = ligne.get('categorie', '')
                qte = ligne.get('quantite', 0)
                unite = ligne.get('unite', '')
                prix = ligne.get('prix_unitaire', 0)
                total = ligne.get('montant_ligne', qte * prix)
                lines.append(f"| {seq} | {desc} | {cat} | {qte} | {unite} | {prix:.2f} $ | {total:.2f} $ |")
            lines.append("")
        
        # Totaux
        lines.append("### 💵 **Récapitulatif financier**")
        sous_total = devis.get('sous_total', 0)
        lines.append(f"- **Sous-total**: {sous_total:,.2f} $")
        
        # Supposons 15% de taxes (à ajuster selon vos besoins)
        taxes = sous_total * 0.15
        lines.append(f"- **Taxes (15%)**: {taxes:,.2f} $")
        
        total = devis.get('montant_total', sous_total + taxes)
        lines.append(f"- **TOTAL**: **{total:,.2f} $**")
        lines.append("")
        
        # Validations
        if devis.get('validations'):
            lines.append("### ✅ **Historique des validations**")
            lines.append("| **Date** | **Validé par** | **Action** | **Commentaire** |")
            lines.append("|----------|----------------|------------|-----------------|")
            
            for val in devis['validations']:
                date = val.get('date_validation', 'N/A')
                nom = f"{val.get('prenom', '')} {val.get('nom', '')}" if val.get('nom') else 'N/A'
                action = val.get('type_validation', 'Validé')
                comment = val.get('commentaires', '')
                lines.append(f"| {date} | {nom} | {action} | {comment} |")
            lines.append("")
        
        # Pied de page
        lines.append("---")
        lines.append("*Ce devis est valable selon les conditions mentionnées ci-dessus.*")
        
        return "\n".join(lines)
    
    def _format_projet_details(self, details: Dict) -> str:
        """Formate les détails complets d'un projet"""
        if 'error' in details:
            return f"❌ **Erreur:** {details['error']}"
        
        if 'projet_details' not in details:
            return "❌ Aucun détail disponible pour ce projet."
        
        projet = details['projet_details']
        lines = []
        
        # En-tête du projet
        lines.append(f"## 📁 **{projet.get('id', 'N/A')} - {projet.get('nom_projet', 'Sans nom')}**\n")
        
        # Informations générales
        lines.append("### 📋 **Informations générales**")
        lines.append(f"- **Client**: {projet.get('client_nom', 'N/A')}")
        if projet.get('po_client'):
            lines.append(f"- **PO Client**: {projet['po_client']}")
        lines.append(f"- **Statut**: `{projet.get('statut', 'N/A')}`")
        lines.append(f"- **Priorité**: `{projet.get('priorite', 'N/A')}`")
        lines.append(f"- **Tâche**: {projet.get('tache', 'N/A')}")
        lines.append(f"- **Date création**: {projet.get('created_at', 'N/A')}")
        if projet.get('date_soumis'):
            lines.append(f"- **Date soumise**: {projet['date_soumis']}")
        if projet.get('date_prevu'):
            lines.append(f"- **Date prévue**: {projet['date_prevu']}")
        if projet.get('bd_ft_estime'):
            lines.append(f"- **BD-FT estimé**: {projet['bd_ft_estime']} heures")
        if projet.get('prix_estime'):
            lines.append(f"- **Budget estimé**: {projet['prix_estime']:,.2f} $")
        if projet.get('description'):
            lines.append(f"\n**Description**: {projet['description']}")
        lines.append("")
        
        # Étapes du projet
        if projet.get('etapes'):
            lines.append("### 📊 **Étapes du projet**")
            lines.append("| **#** | **Nom** | **Statut** | **Date début** | **Date fin** | **% Complété** |")
            lines.append("|-------|---------|------------|----------------|--------------|----------------|")
            
            for etape in projet['etapes']:
                ordre = etape.get('ordre', '')
                nom = etape.get('nom_etape', '')
                statut = etape.get('statut', 'À FAIRE')
                debut = etape.get('date_debut', 'N/A')
                fin = etape.get('date_fin', 'N/A')
                pct = etape.get('pourcentage_complete', 0)
                lines.append(f"| {ordre} | {nom} | {statut} | {debut} | {fin} | {pct}% |")
            lines.append("")
        
        # Employés assignés
        if projet.get('assignations'):
            lines.append("### 👥 **Équipe du projet**")
            lines.append("| **Nom** | **Poste** | **Rôle dans le projet** | **Date assignation** |")
            lines.append("|---------|-----------|-------------------------|---------------------|")
            
            for ass in projet['assignations']:
                nom = f"{ass.get('prenom', '')} {ass.get('nom', '')}"
                poste = ass.get('poste', 'N/A')
                role = ass.get('role_projet', 'N/A')
                date = ass.get('date_assignation', 'N/A')
                lines.append(f"| {nom} | {poste} | {role} | {date} |")
            lines.append("")
        
        # Ressources du projet
        if projet.get('ressources'):
            lines.append("### 🔧 **Ressources planifiées**")
            lines.append("| **Produit** | **Code** | **Quantité** | **Unité** | **Statut** |")
            lines.append("|-------------|----------|--------------|-----------|------------|")
            
            for res in projet['ressources']:
                nom = res.get('produit_nom', res.get('description', 'N/A'))
                code = res.get('code_produit', 'N/A')
                qte = res.get('quantite_prevue', 0)
                unite = res.get('unite', 'N/A')
                statut = res.get('statut', 'PLANIFIÉ')
                lines.append(f"| {nom} | {code} | {qte} | {unite} | {statut} |")
            lines.append("")
        
        # Documents associés
        if projet.get('documents'):
            lines.append("### 📄 **Documents associés**")
            lines.append("| **Numéro** | **Type** | **Statut** | **Date création** |")
            lines.append("|------------|----------|------------|-------------------|")
            
            for doc in projet['documents']:
                numero = doc.get('numero_document', '')
                type_doc = doc.get('type_formulaire', '')
                statut = doc.get('statut', '')
                date = doc.get('created_at', 'N/A')
                lines.append(f"| {numero} | {type_doc} | {statut} | {date} |")
            lines.append("")
        
        # Avancement global
        if projet.get('pourcentage_complete') is not None:
            lines.append(f"### 📈 **Avancement global**: {projet['pourcentage_complete']}%")
        
        return "\n".join(lines)
    
    def _format_dp_details(self, details: Dict) -> str:
        """Formate les détails complets d'une demande de prix"""
        if 'error' in details:
            return f"❌ **Erreur:** {details['error']}"
        
        if 'dp_details' not in details:
            return "❌ Aucun détail disponible pour cette demande de prix."
        
        dp = details['dp_details']
        lines = []
        
        # En-tête de la demande de prix
        lines.append(f"## 💰 **{dp.get('numero_document', 'N/A')} - Demande de prix**\n")
        
        # Informations générales
        lines.append("### 📋 **Informations générales**")
        lines.append(f"- **Fournisseur**: {dp.get('fournisseur', 'N/A')}")
        lines.append(f"- **Objet**: {dp.get('objet', 'Sans objet')}")
        lines.append(f"- **Statut**: `{dp.get('statut', 'N/A')}`")
        lines.append(f"- **Date création**: {dp.get('created_at', 'N/A')}")
        lines.append(f"- **Délai de réponse**: {dp.get('delai_reponse', '15 jours')}")
        lines.append(f"- **Conditions livraison**: {dp.get('conditions_livraison', 'À définir')}")
        if dp.get('notes'):
            lines.append(f"- **Notes**: {dp['notes']}")
        lines.append("")
        
        # Lignes de la demande
        if dp.get('lignes'):
            lines.append("### 📦 **Articles demandés**")
            lines.append("| **#** | **Description** | **Catégorie** | **Quantité** | **Unité** | **Spécifications** |")
            lines.append("|-------|-----------------|---------------|--------------|-----------|-------------------|")
            
            for ligne in dp['lignes']:
                seq = ligne.get('sequence_ligne', '')
                desc = ligne.get('description', '')
                cat = ligne.get('categorie', 'N/A')
                qte = ligne.get('quantite', 0)
                unite = ligne.get('unite', '')
                specs = ligne.get('specifications', 'Standard')
                lines.append(f"| {seq} | {desc} | {cat} | {qte} | {unite} | {specs} |")
            lines.append("")
        
        # Réponses fournisseur
        if dp.get('reponses'):
            lines.append("### 📝 **Réponses du fournisseur**")
            for reponse in dp['reponses']:
                lines.append(f"\n**Réponse du {reponse.get('date_reponse', 'N/A')}**")
                lines.append(f"- **Prix proposé**: {reponse.get('prix_propose', 0):,.2f} $")
                lines.append(f"- **Délai livraison**: {reponse.get('delai_livraison', 'N/A')}")
                lines.append(f"- **Validité**: {reponse.get('validite_offre', '30 jours')}")
                if reponse.get('conditions'):
                    lines.append(f"- **Conditions**: {reponse['conditions']}")
                if reponse.get('commentaires'):
                    lines.append(f"- **Commentaires**: {reponse['commentaires']}")
            lines.append("")
        else:
            lines.append("### ⏳ **En attente de réponse du fournisseur**")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_ba_details(self, details: Dict) -> str:
        """Formate les détails complets d'un bon d'achat"""
        if 'error' in details:
            return f"❌ **Erreur:** {details['error']}"
        
        if 'ba_details' not in details:
            return "❌ Aucun détail disponible pour ce bon d'achat."
        
        ba = details['ba_details']
        lines = []
        
        # En-tête du bon d'achat
        lines.append(f"## 🛒 **{ba.get('numero_document', 'N/A')} - Bon d'achat**\n")
        
        # Informations générales
        lines.append("### 📋 **Informations générales**")
        lines.append(f"- **Fournisseur**: {ba.get('fournisseur', 'N/A')}")
        lines.append(f"- **Objet**: {ba.get('objet', 'Sans objet')}")
        if ba.get('nom_projet'):
            lines.append(f"- **Projet associé**: {ba.get('nom_projet')}")
        lines.append(f"- **Statut**: `{ba.get('statut', 'N/A')}`")
        lines.append(f"- **Date création**: {ba.get('created_at', 'N/A')}")
        lines.append(f"- **Conditions paiement**: {ba.get('conditions_paiement', '30 jours net')}")
        lines.append(f"- **Mode livraison**: {ba.get('mode_livraison', 'À définir')}")
        if ba.get('notes'):
            lines.append(f"- **Notes**: {ba['notes']}")
        lines.append("")
        
        # Lignes du bon d'achat
        if ba.get('lignes'):
            lines.append("### 📦 **Articles commandés**")
            lines.append("| **#** | **Code** | **Description** | **Catégorie** | **Quantité** | **Unité** | **Prix unit.** | **Total** |")
            lines.append("|-------|----------|-----------------|---------------|--------------|-----------|----------------|-----------|")
            
            for ligne in ba['lignes']:
                seq = ligne.get('sequence_ligne', '')
                code = ligne.get('code_article', 'N/A')
                desc = ligne.get('description', '')
                cat = ligne.get('categorie', 'N/A')
                qte = ligne.get('quantite', 0)
                unite = ligne.get('unite', '')
                prix = ligne.get('prix_unitaire', 0)
                total = ligne.get('montant_ligne', qte * prix)
                lines.append(f"| {seq} | {code} | {desc} | {cat} | {qte} | {unite} | {prix:.2f} $ | {total:.2f} $ |")
            lines.append("")
        
        # Totaux
        lines.append("### 💵 **Récapitulatif financier**")
        sous_total = ba.get('sous_total', 0)
        lines.append(f"- **Sous-total**: {sous_total:,.2f} $")
        
        # Supposons 15% de taxes
        taxes = sous_total * 0.15
        lines.append(f"- **Taxes (15%)**: {taxes:,.2f} $")
        
        total = ba.get('montant_total', sous_total + taxes)
        lines.append(f"- **TOTAL**: **{total:,.2f} $**")
        lines.append("")
        
        # Informations de livraison
        if ba.get('livraisons'):
            lines.append("### 🚚 **Suivi des livraisons**")
            lines.append("| **Date commande** | **Date prévue** | **Date réelle** | **Statut** | **Qté commandée** | **Qté reçue** |")
            lines.append("|-------------------|-----------------|-----------------|------------|-------------------|---------------|")
            
            for liv in ba['livraisons']:
                date_cmd = liv.get('date_commande', 'N/A')
                date_prev = liv.get('date_livraison_prevue', 'N/A')
                date_reel = liv.get('date_livraison_reelle', 'N/A')
                statut = liv.get('statut_livraison', 'EN_ATTENTE')
                qte_cmd = liv.get('quantite_commandee', 0)
                qte_rec = liv.get('quantite_recue', 0)
                lines.append(f"| {date_cmd} | {date_prev} | {date_reel} | {statut} | {qte_cmd} | {qte_rec} |")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_employee_hours(self, details: Dict) -> str:
        """Formate les heures travaillées d'un employé avec rapport complet"""
        if 'error' in details:
            return f"❌ **Erreur:** {details['error']}"
        
        if not details:
            return "❌ Aucune heure travaillée trouvée pour cette période."
        
        lines = []
        employee_name = details.get('employee_name', 'Employé')
        poste = details.get('poste', 'N/A')
        departement = details.get('departement', 'N/A')
        week_start = details.get('week_start', '')
        week_end = details.get('week_end', '')
        
        # En-tête
        lines.append(f"## ⏰ **Rapport d'heures - {employee_name}**")
        lines.append(f"**Poste**: {poste} | **Département**: {departement}\n")
        lines.append(f"### 📅 **Période: {week_start} au {week_end}**\n")
        
        # Résumé avec statistiques
        total_hours = details.get('total_hours', 0)
        total_days = details.get('total_days', 0)
        average_hours = details.get('average_hours', 0)
        most_productive_day = details.get('most_productive_day', 'N/A')
        max_daily_hours = details.get('max_daily_hours', 0)
        
        lines.append("### 📊 **Résumé de la semaine**")
        lines.append(f"- **Total heures travaillées**: `{total_hours:.2f}` heures")
        lines.append(f"- **Jours travaillés**: `{total_days}` jours")
        lines.append(f"- **Moyenne par jour**: `{average_hours:.2f}` heures")
        lines.append(f"- **Jour le plus productif**: {most_productive_day} ({max_daily_hours:.2f}h)")
        lines.append("")
        
        # Répartition par client
        if details.get('hours_by_client'):
            lines.append("### 🏢 **Répartition par client**")
            lines.append("| **Client** | **Heures** | **%** | **Projets** |")
            lines.append("|------------|------------|-------|-------------|")
            
            for client_data in details.get('hours_by_client', []):
                client = client_data.get('client', 'N/A')
                hours = client_data.get('hours', 0)
                percentage = client_data.get('percentage', 0)
                projects = ', '.join(client_data.get('projects', []))
                lines.append(f"| {client} | {hours:.2f}h | {percentage:.1f}% | {projects} |")
            lines.append("")
        
        # Détail par projet avec statut
        if details.get('hours_by_project'):
            lines.append("### 📁 **Heures par projet**")
            lines.append("| **Projet** | **Client** | **Heures** | **%** | **Statut** | **Jours** | **Bons de travail** |")
            lines.append("|------------|------------|------------|-------|------------|-----------|---------------------|")
            
            for project_data in details.get('hours_by_project', []):
                project = project_data.get('project_name', 'Sans projet')
                client = project_data.get('client', 'N/A')
                hours = project_data.get('hours', 0)
                percentage = project_data.get('percentage', 0)
                statut = project_data.get('statut', 'N/A')
                days_worked = project_data.get('days_worked', 0)
                bts = ', '.join(project_data.get('bons_travail', [])) if project_data.get('bons_travail') else 'N/A'
                lines.append(f"| {project} | {client} | {hours:.2f}h | {percentage:.1f}% | {statut} | {days_worked} | {bts} |")
            lines.append("")
        
        # Détail par bon de travail
        if details.get('hours_by_bt'):
            lines.append("### 🔧 **Heures par bon de travail**")
            lines.append("| **Bon de travail** | **Projet** | **Heures** | **%** | **Statut** | **Priorité** |")
            lines.append("|--------------------|------------|------------|-------|------------|--------------|")
            
            for bt_data in details.get('hours_by_bt', []):
                bt = bt_data.get('bt_numero', 'N/A')
                project = bt_data.get('project', 'N/A')
                hours = bt_data.get('hours', 0)
                percentage = bt_data.get('percentage', 0)
                statut = bt_data.get('statut', 'N/A')
                priorite = bt_data.get('priorite', 'N/A')
                lines.append(f"| {bt} | {project} | {hours:.2f}h | {percentage:.1f}% | {statut} | {priorite} |")
            lines.append("")
        
        # Détail par jour
        if details.get('hours_by_day'):
            lines.append("### 📆 **Détail quotidien**")
            lines.append("| **Date** | **Jour** | **Heures** | **Entrées** | **Projets** | **Bons de travail** |")
            lines.append("|----------|----------|------------|-------------|-------------|---------------------|")
            
            days_fr = {
                'Monday': 'Lundi',
                'Tuesday': 'Mardi',
                'Wednesday': 'Mercredi',
                'Thursday': 'Jeudi',
                'Friday': 'Vendredi',
                'Saturday': 'Samedi',
                'Sunday': 'Dimanche'
            }
            
            for day_data in details.get('hours_by_day', []):
                date = day_data.get('date', '')
                day_name = days_fr.get(day_data.get('day_name', ''), day_data.get('day_name', ''))
                hours = day_data.get('hours', 0)
                entries_count = day_data.get('entries_count', 0)
                projects = ', '.join(day_data.get('projects', [])) if day_data.get('projects') else 'N/A'
                bts = ', '.join(day_data.get('bons_travail', [])) if day_data.get('bons_travail') else 'N/A'
                lines.append(f"| {date} | {day_name} | {hours:.2f}h | {entries_count} | {projects} | {bts} |")
            lines.append("")
        
        # Graphique de productivité (représentation textuelle)
        if details.get('hours_by_day'):
            lines.append("### 📈 **Graphique de productivité**")
            lines.append("```")
            max_graph_width = 40
            for day_data in details.get('hours_by_day', []):
                date = day_data.get('date', '')[-5:]  # MM-DD
                hours = day_data.get('hours', 0)
                bar_width = int((hours / max_daily_hours) * max_graph_width) if max_daily_hours > 0 else 0
                bar = '█' * bar_width
                lines.append(f"{date} |{bar} {hours:.1f}h")
            lines.append("```")
            lines.append("")
        
        # Statistiques de performance
        lines.append("### 🎯 **Indicateurs de performance**")
        
        # Productivité (basé sur 8h/jour standard)
        expected_hours = total_days * 8
        productivity = (total_hours / expected_hours * 100) if expected_hours > 0 else 0
        lines.append(f"- **Taux de productivité**: {productivity:.1f}% (base: 8h/jour)")
        
        # Répartition projets vs autres
        project_hours_total = sum(p.get('hours', 0) for p in details.get('hours_by_project', []))
        project_percentage = (project_hours_total / total_hours * 100) if total_hours > 0 else 0
        lines.append(f"- **Temps sur projets**: {project_percentage:.1f}%")
        
        # Nombre de projets différents
        num_projects = len(details.get('hours_by_project', []))
        lines.append(f"- **Projets travaillés**: {num_projects}")
        
        # Nombre de bons de travail
        num_bts = len(details.get('hours_by_bt', []))
        lines.append(f"- **Bons de travail traités**: {num_bts}")
        lines.append("")
        
        # Entrées détaillées (optionnel, si peu nombreuses)
        if details.get('time_entries') and len(details.get('time_entries', [])) <= 20:
            lines.append("### 📝 **Pointages détaillés**")
            lines.append("| **Date** | **Entrée** | **Sortie** | **Durée** | **Projet** | **BT** |")
            lines.append("|----------|------------|------------|-----------|------------|--------|")
            
            for entry in details.get('time_entries', []):
                date = entry.get('work_date', '')
                punch_in = entry.get('punch_in_time', '')
                punch_out = entry.get('punch_out_time', '')
                duration = entry.get('total_hours', 0)
                project = entry.get('nom_projet', 'N/A')
                bt = entry.get('bt_numero', 'N/A')
                lines.append(f"| {date} | {punch_in} | {punch_out} | {duration:.2f}h | {project} | {bt} |")
            lines.append("")
        
        # Note de fin
        lines.append("---")
        lines.append(f"*Rapport généré pour la période du {week_start} au {week_end}*")
        
        return "\n".join(lines)
    
    def _format_project_report(self, report: Dict) -> str:
        """Formate le rapport complet d'un projet avec analyse financière"""
        if 'error' in report:
            return f"❌ **Erreur:** {report['error']}"
        
        if not report or 'project_info' not in report:
            return "❌ Aucune donnée disponible pour ce projet."
        
        lines = []
        proj = report['project_info']
        fin = report['financial_summary']
        time = report['time_summary']
        
        # En-tête
        lines.append(f"## 📁 **Rapport de projet - {proj.get('id', 'N/A')} - {proj.get('nom_projet', 'Sans nom')}**")
        lines.append(f"**Client**: {proj.get('client_nom', 'N/A')} | **Secteur**: {proj.get('client_secteur', 'N/A')}")
        lines.append(f"**Statut**: `{proj.get('statut', 'N/A')}` | **Priorité**: `{proj.get('priorite', 'N/A')}`")
        lines.append(f"**Avancement global**: {report.get('progress', 0):.1f}%\n")
        
        # Analyse financière
        lines.append("✨ 💰 **Analyse financière**")
        lines.append(f"- **Prix de vente**: {fin['prix_vente']:,.2f} $")
        lines.append(f"- **Coût main d'œuvre**: {fin['cout_main_oeuvre']:,.2f} $")
        lines.append(f"- **Coût matériaux**: {fin['cout_materiaux']:,.2f} $")
        lines.append(f"- **Coût total**: {fin['cout_total']:,.2f} $")
        lines.append(f"- **Profit brut**: {fin['profit_brut']:,.2f} $")
        
        # Indicateur visuel de rentabilité
        if fin['marge_profit'] >= 30:
            emoji = "🟢"  # Vert
            status = "Excellente"
        elif fin['marge_profit'] >= 15:
            emoji = "🟡"  # Jaune
            status = "Correcte"
        else:
            emoji = "🔴"  # Rouge
            status = "Faible"
        
        lines.append(f"- **Marge de profit**: {emoji} {fin['marge_profit']:.1f}% ({status})")
        lines.append("")
        
        # Analyse du temps
        lines.append("✨ ⏰ **Analyse du temps**")
        lines.append(f"- **Heures estimées**: {time['heures_estimees']:.1f} h")
        lines.append(f"- **Heures réelles**: {time['heures_reelles']:.1f} h")
        
        # Indicateur d'efficacité
        if time['efficacite'] >= 90:
            eff_emoji = "🎯"  # Excellent
            eff_status = "Excellente efficacité"
        elif time['efficacite'] >= 70:
            eff_emoji = "✅"  # Bon
            eff_status = "Bonne efficacité"
        else:
            eff_emoji = "⚠️"  # Attention
            eff_status = "Efficacité à améliorer"
        
        lines.append(f"- **Efficacité**: {eff_emoji} {time['efficacite']:.1f}% ({eff_status})")
        lines.append(f"- **Nombre d'employés**: {time['nb_employes']}")
        lines.append(f"- **Jours travaillés**: {time['nb_jours_travailles']}")
        lines.append("")
        
        # Détail des employés
        if report.get('employees'):
            lines.append("✨ 👥 **Répartition du travail par employé**")
            lines.append("| **Employé** | **Poste** | **Heures** | **Coût** | **Jours** | **Période** |")
            lines.append("|-------------|-----------|------------|-----------|-----------|-------------|")
            
            for emp in report['employees']:
                nom = f"{emp['prenom']} {emp['nom']}"
                poste = emp.get('poste', 'N/A')
                heures = emp.get('heures_totales', 0)
                cout = emp.get('cout_total', 0)
                jours = emp.get('jours_travailles', 0)
                periode = f"{emp.get('premiere_intervention', 'N/A')} au {emp.get('derniere_intervention', 'N/A')}"
                lines.append(f"| {nom} | {poste} | {heures:.1f}h | {cout:,.2f}$ | {jours} | {periode} |")
            lines.append("")
        
        # Matériaux utilisés
        if report.get('materials'):
            lines.append("✨ 🔧 **Matériaux utilisés**")
            lines.append("| **Code** | **Produit** | **Fournisseur** | **Quantité** | **Coût unit.** | **Coût total** |")
            lines.append("|----------|-------------|-----------------|--------------|-----------------|-----------------|")
            
            for mat in report['materials']:
                code = mat.get('code_article', 'N/A')
                nom = mat.get('nom_produit', 'N/A')
                fourn = mat.get('fournisseur', 'N/A')
                qte = f"{mat.get('quantite_totale', 0)} {mat.get('unite', '')}"
                cout_unit = mat.get('cout_unitaire', 0)
                cout_total = mat.get('cout_total', 0)
                lines.append(f"| {code} | {nom} | {fourn} | {qte} | {cout_unit:.2f}$ | {cout_total:,.2f}$ |")
            lines.append("")
        
        # Bons de travail
        if report.get('work_orders'):
            lines.append("✨ 🔧 **Bons de travail associés**")
            lines.append("| **Numéro** | **Statut** | **Coût** | **Lignes** | **Date création** |")
            lines.append("|------------|----------|----------|-----------|-------------------|")
            
            for bt in report['work_orders']:
                numero = bt.get('numero_document', 'N/A')
                statut = bt.get('statut', 'N/A')
                cout = bt.get('cout_total', 0)
                nb_lignes = bt.get('nb_lignes', 0)
                date = bt.get('created_at', 'N/A')
                lines.append(f"| {numero} | {statut} | {cout:,.2f}$ | {nb_lignes} | {date} |")
            lines.append("")
        
        # Opérations du projet
        if report.get('operations'):
            lines.append("✨ 📊 **Opérations du projet**")
            lines.append("| **ID** | **Description** | **Poste de travail** | **Statut** | **Date création** |")
            lines.append("|--------|-----------------|---------------------|------------|-------------------|")
            
            for op in report['operations']:
                id_op = op.get('id', '')
                desc = op.get('description', 'N/A')
                poste = op.get('poste_travail', 'N/A')
                statut = op.get('statut', 'N/A')
                date = op.get('created_at', 'N/A')
                lines.append(f"| {id_op} | {desc} | {poste} | {statut} | {date} |")
            lines.append("")
        
        # Résumé des indicateurs clés
        lines.append("✨ 🎯 **Indicateurs clés de performance (KPI)**")
        
        # ROI (Retour sur investissement)
        roi = (fin['profit_brut'] / fin['cout_total'] * 100) if fin['cout_total'] > 0 else 0
        lines.append(f"- **ROI**: {roi:.1f}%")
        
        # Coût par heure
        cout_par_heure = fin['cout_total'] / time['heures_reelles'] if time['heures_reelles'] > 0 else 0
        lines.append(f"- **Coût moyen par heure**: {cout_par_heure:.2f} $/h")
        
        # Productivité ($/h facturé)
        productivite = fin['prix_vente'] / time['heures_reelles'] if time['heures_reelles'] > 0 else 0
        lines.append(f"- **Productivité**: {productivite:.2f} $/h facturé")
        lines.append("")
        
        # Devis/Estimations
        if report.get('devis'):
            lines.append("✨ 💰 **Devis/Estimations**")
            lines.append("| **Numéro** | **Statut** | **Montant** | **Date** | **Notes** |")
            lines.append("|------------|----------|-------------|----------|-----------|")
            
            for devis in report['devis']:
                numero = devis.get('numero_document', '')
                statut = devis.get('statut', '')
                montant = f"{devis.get('montant_total', 0):,.2f} $" if devis.get('montant_total') else 'N/A'
                date = devis.get('created_at', 'N/A')[:10] if devis.get('created_at') else 'N/A'
                notes = (devis.get('notes', '')[:30] + '...') if devis.get('notes') and len(devis.get('notes', '')) > 30 else devis.get('notes', 'N/A')
                lines.append(f"| {numero} | {statut} | {montant} | {date} | {notes} |")
            lines.append("")
        
        # Demandes de prix
        if report.get('demandes_prix'):
            lines.append("✨ 📋 **Demandes de prix**")
            lines.append("| **Numéro** | **Fournisseur** | **Statut** | **Date** | **Notes** |")
            lines.append("|------------|-----------------|----------|----------|-----------|")
            
            for dp in report['demandes_prix']:
                numero = dp.get('numero_document', '')
                fournisseur = dp.get('fournisseur_nom', 'N/A')
                statut = dp.get('statut', '')
                date = dp.get('created_at', 'N/A')[:10] if dp.get('created_at') else 'N/A'
                notes = (dp.get('notes', '')[:30] + '...') if dp.get('notes') and len(dp.get('notes', '')) > 30 else dp.get('notes', 'N/A')
                lines.append(f"| {numero} | {fournisseur} | {statut} | {date} | {notes} |")
            lines.append("")
        
        # Bons d'achat
        if report.get('bons_achat'):
            lines.append("✨ 🛒 **Bons d'achat**")
            lines.append("| **Numéro** | **Fournisseur** | **Montant** | **Statut** | **Date** |")
            lines.append("|------------|-----------------|-------------|----------|----------|")
            
            for ba in report['bons_achat']:
                numero = ba.get('numero_document', '')
                fournisseur = ba.get('fournisseur_nom', 'N/A')
                montant = f"{ba.get('montant_total', 0):,.2f} $" if ba.get('montant_total') else 'N/A'
                statut = ba.get('statut', '')
                date = ba.get('created_at', 'N/A')[:10] if ba.get('created_at') else 'N/A'
                lines.append(f"| {numero} | {fournisseur} | {montant} | {statut} | {date} |")
            lines.append("")
        
        # Fournisseurs impliqués
        if report.get('fournisseurs'):
            lines.append("✨ 🏢 **Fournisseurs impliqués dans le projet**")
            lines.append("- " + "\n- ".join(report['fournisseurs']))
            lines.append("")
        
        # Note de fin
        lines.append("---")
        lines.append(f"*Rapport généré pour le projet {proj.get('id')} - {proj.get('nom_projet')}*")
        
        return "\n".join(lines)
    
    def _format_bt_report(self, report: Dict) -> str:
        """Formate le rapport complet d'un bon de travail"""
        if 'error' in report:
            return f"❌ **Erreur:** {report['error']}"
        
        if not report or 'bt_info' not in report:
            return "❌ Aucune donnée disponible pour ce bon de travail."
        
        lines = []
        bt = report['bt_info']
        fin = report['financial_summary']
        time = report['time_summary']
        
        # En-tête
        lines.append(f"## 🔧 **Rapport Bon de Travail - {bt.get('numero_document', 'N/A')}**")
        lines.append(f"**Projet**: {bt.get('nom_projet', 'N/A')} | **Client**: {bt.get('client_nom', 'N/A')}")
        lines.append(f"**Statut**: `{bt.get('statut', 'N/A')}` | **Priorité**: `{bt.get('priorite', 'N/A')}`")
        lines.append(f"**Date création**: {bt.get('created_at', 'N/A')}\n")
        
        # Analyse financière
        lines.append("✨ 💰 **Analyse financière**")
        lines.append(f"- **Budget alloué**: {fin['budget_alloue']:,.2f} $")
        lines.append(f"- **Coût des lignes**: {fin['cout_lignes']:,.2f} $")
        lines.append(f"- **Coût main d'œuvre**: {fin['cout_main_oeuvre']:,.2f} $")
        lines.append(f"- **Coût total réel**: {fin['cout_total']:,.2f} $")
        
        # Indicateur de dépassement budgétaire
        depassement = fin['cout_total'] - fin['budget_alloue']
        if depassement <= 0:
            budget_emoji = "✅"  # Dans le budget
            budget_status = f"Dans le budget ({abs(depassement):,.2f}$ de marge)"
        else:
            budget_emoji = "🔴"  # Dépassement
            budget_status = f"Dépassement de {depassement:,.2f}$ ({(depassement/fin['budget_alloue']*100):.1f}%)"
        
        lines.append(f"- **Statut budgétaire**: {budget_emoji} {budget_status}")
        lines.append("")
        
        # Analyse du temps
        lines.append("✨ ⏰ **Analyse du temps**")
        lines.append(f"- **Heures totales**: {time['heures_totales']:.1f} h")
        lines.append(f"- **Nombre d'employés**: {time['nb_employes']}")
        if time['premiere_intervention']:
            lines.append(f"- **Période d'exécution**: {time['premiere_intervention']} au {time['derniere_intervention']}")
        lines.append("")
        
        # Détail par employé
        if report.get('employees_detail'):
            lines.append("✨ 👥 **Heures par employé**")
            lines.append("| **Employé** | **Poste** | **Heures** | **Taux** | **Coût** | **Jours** |")
            lines.append("|-------------|-----------|------------|----------|-----------|-----------|")
            
            for emp_name, emp_data in report['employees_detail'].items():
                poste = emp_data.get('poste', 'N/A')
                heures = emp_data.get('heures_totales', 0)
                taux = emp_data.get('taux_horaire', 0)
                cout = emp_data.get('cout_total', 0)
                jours = emp_data.get('nb_jours', 0)
                lines.append(f"| {emp_name} | {poste} | {heures:.1f}h | {taux:.2f}$/h | {cout:,.2f}$ | {jours} |")
            lines.append("")
        
        # Lignes du bon de travail
        if report.get('lignes'):
            lines.append("✨ 📝 **Détail des lignes**")
            lines.append("| **#** | **Description** | **Quantité** | **Unité** | **Prix unit.** | **Total** |")
            lines.append("|-------|-----------------|--------------|-----------|----------------|-----------|")
            
            for ligne in report['lignes']:
                seq = ligne.get('sequence_ligne', '')
                desc = ligne.get('description', '')
                qte = ligne.get('quantite', 0)
                unite = ligne.get('unite', '')
                prix = ligne.get('prix_unitaire', 0)
                total = ligne.get('montant_ligne', 0)
                lines.append(f"| {seq} | {desc} | {qte} | {unite} | {prix:.2f}$ | {total:.2f}$ |")
            lines.append("")
        
        # Historique d'avancement
        if report.get('progress_history'):
            lines.append("✨ 📊 **Historique d'avancement**")
            lines.append("| **Date** | **Employé** | **% Réalisé** | **Temps réel** | **Notes** |")
            lines.append("|----------|-------------|---------------|----------------|-----------|")
            
            for av in report['progress_history']:
                date = av.get('updated_at', 'N/A')
                emp = f"{av.get('prenom', '')} {av.get('nom', '')}" if av.get('nom') else 'N/A'
                pct = av.get('pourcentage_realise', 0)
                temps = av.get('temps_reel', 0)
                notes = av.get('notes_avancement', '')
                lines.append(f"| {date} | {emp} | {pct}% | {temps}h | {notes} |")
            lines.append("")
        
        # Pointages détaillés (si peu nombreux)
        if report.get('time_entries') and len(report['time_entries']) <= 15:
            lines.append("✨ 🕑 **Pointages détaillés**")
            lines.append("| **Date** | **Employé** | **Entrée** | **Sortie** | **Durée** | **Description** |")
            lines.append("|----------|-------------|------------|------------|-----------|-----------------|")
            
            for entry in report['time_entries']:
                date = entry.get('date_travail', '')
                emp = f"{entry.get('prenom', '')} {entry.get('nom', '')}"
                punch_in = entry.get('punch_in', '')[-8:-3]  # HH:MM
                punch_out = entry.get('punch_out', '')[-8:-3] if entry.get('punch_out') else 'N/A'
                duree = entry.get('total_hours', 0)
                desc = entry.get('description', 'N/A')
                lines.append(f"| {date} | {emp} | {punch_in} | {punch_out} | {duree:.1f}h | {desc} |")
            lines.append("")
        
        # KPIs
        lines.append("✨ 🎯 **Indicateurs clés**")
        
        # Coût par heure
        cout_par_heure = fin['cout_total'] / time['heures_totales'] if time['heures_totales'] > 0 else 0
        lines.append(f"- **Coût moyen par heure**: {cout_par_heure:.2f} $/h")
        
        # Efficacité budgétaire
        efficacite_budget = (fin['budget_alloue'] / fin['cout_total'] * 100) if fin['cout_total'] > 0 else 100
        lines.append(f"- **Efficacité budgétaire**: {efficacite_budget:.1f}%")
        
        # Moyenne d'heures par employé
        moy_heures_emp = time['heures_totales'] / time['nb_employes'] if time['nb_employes'] > 0 else 0
        lines.append(f"- **Moyenne heures/employé**: {moy_heures_emp:.1f}h")
        lines.append("")
        
        # Note de fin
        lines.append("---")
        lines.append(f"*Rapport généré pour le bon de travail {bt.get('numero_document')}*")
        
        return "\n".join(lines)
    
    def _format_alertes(self, alertes: Dict) -> str:
        """Formate les alertes du système"""
        if 'error' in alertes:
            return f"❌ **Erreur:** {alertes['error']}"
        
        lines = []
        lines.append("## 🚨 **Alertes et notifications importantes**\n")
        
        total_alertes = 0
        
        # Stocks faibles
        if alertes.get('stocks_faibles'):
            nb = len(alertes['stocks_faibles'])
            total_alertes += nb
            lines.append(f"✨ 📦 **Stocks faibles ou en rupture** ({nb} articles)")
            lines.append("| **Code** | **Produit** | **Stock** | **Minimum** | **Fournisseur** | **Délai** |")
            lines.append("|----------|-------------|----------|-------------|-----------------|-----------|")
            
            for stock in alertes['stocks_faibles'][:10]:  # Limiter à 10
                code = stock.get('code_produit', '')
                nom = stock.get('nom', '')
                dispo = stock.get('stock_disponible', 0)
                minimum = stock.get('stock_minimum', 0)
                fourn = stock.get('fournisseur_principal', 'N/A')
                delai = f"{stock.get('delai_approvisionnement', 0)}j"
                
                # Indicateur visuel
                if dispo == 0:
                    emoji = "🔴"  # Rouge - rupture
                elif dispo < minimum / 2:
                    emoji = "🟡"  # Jaune - très bas
                else:
                    emoji = "🟠"  # Orange - bas
                    
                lines.append(f"| {emoji} {code} | {nom} | {dispo} | {minimum} | {fourn} | {delai} |")
            lines.append("")
        
        # Projets avec échéance proche
        if alertes.get('projets_echeance'):
            nb = len(alertes['projets_echeance'])
            total_alertes += nb
            lines.append(f"✨ 📅 **Projets avec échéance proche** ({nb} projets)")
            lines.append("| **Projet** | **Client** | **Date prévue** | **Statut** | **Jours restants** |")
            lines.append("|------------|------------|----------------|------------|---------------------|")
            
            for projet in alertes['projets_echeance']:
                nom = projet.get('nom_projet', '')
                client = projet.get('client_nom', 'N/A')
                date = projet.get('date_prevu', 'N/A')
                statut = projet.get('statut', '')
                jours = int((datetime.strptime(date, '%Y-%m-%d') - datetime.now()).days) if date != 'N/A' else 0
                
                # Indicateur visuel
                if jours <= 1:
                    emoji = "🔴"  # Rouge - très urgent
                elif jours <= 3:
                    emoji = "🟡"  # Jaune - urgent
                else:
                    emoji = "🟠"  # Orange - attention
                    
                lines.append(f"| {emoji} {nom} | {client} | {date} | {statut} | {jours}j |")
            lines.append("")
        
        # Bons de travail urgents
        if alertes.get('bt_urgents'):
            nb = len(alertes['bt_urgents'])
            total_alertes += nb
            lines.append(f"✨ 🔥 **Bons de travail urgents non terminés** ({nb} BT)")
            lines.append("| **Numéro** | **Projet** | **Statut** | **Créé le** | **Notes** |")
            lines.append("|------------|------------|------------|-------------|-----------|")
            
            for bt in alertes['bt_urgents']:
                numero = bt.get('numero_document', '')
                projet = bt.get('nom_projet', 'N/A')
                statut = bt.get('statut', '')
                date = bt.get('created_at', 'N/A')[:10] if bt.get('created_at') else 'N/A'
                notes = (bt.get('notes', '')[:30] + '...') if bt.get('notes') and len(bt.get('notes', '')) > 30 else bt.get('notes', '')
                lines.append(f"| 🔴 {numero} | {projet} | {statut} | {date} | {notes} |")
            lines.append("")
        
        # Devis à relancer
        if alertes.get('devis_a_relancer'):
            nb = len(alertes['devis_a_relancer'])
            total_alertes += nb
            lines.append(f"✨ 💰 **Devis en attente depuis plus de 15 jours** ({nb} devis)")
            lines.append("| **Numéro** | **Client** | **Montant** | **Créé le** | **Jours** |")
            lines.append("|------------|------------|-------------|-------------|-----------|")
            
            for devis in alertes['devis_a_relancer']:
                numero = devis.get('numero_document', '')
                client = devis.get('client_nom', 'N/A')
                montant = f"{devis.get('montant_total', 0):,.2f} $" if devis.get('montant_total') else 'N/A'
                date = devis.get('created_at', 'N/A')
                jours = int((datetime.now() - datetime.strptime(date[:10], '%Y-%m-%d')).days) if date != 'N/A' else 0
                lines.append(f"| {numero} | {client} | {montant} | {date[:10]} | {jours}j |")
            lines.append("")
        
        # Résumé
        if total_alertes == 0:
            lines.append("🎉 **Aucune alerte à signaler - Tout est sous contrôle !**")
        else:
            lines.append(f"✨ 📋 **Résumé**: {total_alertes} alertes actives nécessitant votre attention")
        
        return "\n".join(lines)
    
    def _format_employes_disponibles(self, data: Dict) -> str:
        """Formate la liste des employés disponibles"""
        if 'error' in data:
            return f"❌ **Erreur:** {data['error']}"
        
        lines = []
        lines.append("## 👥 **Employés disponibles**\n")
        
        if data.get('employes'):
            lines.append(f"✨ ✅ **{len(data['employes'])} employés disponibles actuellement**\n")
            lines.append("| **Nom** | **Poste** | **Département** | **Charge** | **Dernière activité** |")
            lines.append("|---------|-----------|-----------------|------------|---------------------|")
            
            for emp in data['employes']:
                nom = f"{emp.get('prenom', '')} {emp.get('nom', '')}"
                poste = emp.get('poste', 'N/A')
                dept = emp.get('departement', 'N/A')
                charge = f"{emp.get('charge_travail', 100)}%"
                derniere = emp.get('derniere_entree', 'Aucune aujourd\'hui')
                if derniere and derniere != 'Aucune aujourd\'hui':
                    derniere = derniere[11:16]  # Heure seulement
                lines.append(f"| {nom} | {poste} | {dept} | {charge} | {derniere} |")
            lines.append("")
            
            # Statistiques par département
            dept_count = {}
            for emp in data['employes']:
                dept = emp.get('departement', 'Autre')
                dept_count[dept] = dept_count.get(dept, 0) + 1
            
            lines.append("✨ 📊 **Répartition par département**")
            for dept, count in sorted(dept_count.items()):
                lines.append(f"- **{dept}**: {count} employé(s)")
        else:
            lines.append("⚠️ **Aucun employé disponible actuellement**")
            lines.append("Tous les employés sont en activité ou non actifs.")
        
        return "\n".join(lines)
    
    def _format_bt_en_cours(self, data: Dict) -> str:
        """Formate la liste des bons de travail en cours"""
        if 'error' in data:
            return f"❌ **Erreur:** {data['error']}"
        
        lines = []
        lines.append("## 🔧 **Bons de travail en cours**\n")
        
        if data.get('bons_travail'):
            # Séparer par priorité
            urgents = [bt for bt in data['bons_travail'] if bt.get('priorite') == 'URGENT']
            normaux = [bt for bt in data['bons_travail'] if bt.get('priorite') != 'URGENT']
            
            # BT Urgents
            if urgents:
                lines.append(f"✨ 🔥 **Urgents** ({len(urgents)})")
                lines.append("| **Numéro** | **Projet** | **Client** | **Employés** | **Avancement** | **Statut** |")
                lines.append("|------------|------------|------------|--------------|----------------|------------|")
                
                for bt in urgents:
                    numero = bt.get('numero_document', '')
                    projet = bt.get('nom_projet', 'N/A')
                    client = bt.get('client_nom', 'N/A')
                    nb_emp = bt.get('nb_employes', 0)
                    avancement = f"{bt.get('avancement', 0)}%" if bt.get('avancement') else '0%'
                    statut = bt.get('statut', '')
                    lines.append(f"| 🔴 {numero} | {projet} | {client} | {nb_emp} | {avancement} | {statut} |")
                lines.append("")
            
            # BT Normaux
            if normaux:
                lines.append(f"✨ 🔨 **Priorité normale** ({len(normaux)})")
                lines.append("| **Numéro** | **Projet** | **Client** | **Employés** | **Avancement** | **Créé le** |")
                lines.append("|------------|------------|------------|--------------|----------------|-------------|")
                
                for bt in normaux[:15]:  # Limiter à 15
                    numero = bt.get('numero_document', '')
                    projet = bt.get('nom_projet', 'N/A')
                    client = bt.get('client_nom', 'N/A')
                    nb_emp = bt.get('nb_employes', 0)
                    avancement = f"{bt.get('avancement', 0)}%" if bt.get('avancement') else '0%'
                    date = bt.get('created_at', 'N/A')[:10] if bt.get('created_at') else 'N/A'
                    lines.append(f"| {numero} | {projet} | {client} | {nb_emp} | {avancement} | {date} |")
                lines.append("")
            
            # Résumé
            lines.append(f"✨ 📋 **Total**: {len(data['bons_travail'])} bons de travail en cours")
            if urgents:
                lines.append(f"- 🔥 {len(urgents)} urgent(s)")
            lines.append(f"- 🔨 {len(normaux)} normal(aux)")
        else:
            lines.append("🎉 **Aucun bon de travail en cours**")
            lines.append("Tous les bons de travail sont terminés ou en attente.")
        
        return "\n".join(lines)
    
    def _format_ruptures_stock(self, data: Dict) -> str:
        """Formate la liste des ruptures de stock"""
        if 'error' in data:
            return f"❌ **Erreur:** {data['error']}"
        
        lines = []
        lines.append("## 📦 **Produits en rupture ou stock faible**\n")
        
        if data.get('ruptures'):
            # Grouper par catégorie
            par_categorie = {}
            for r in data['ruptures']:
                cat = r.get('categorie', 'Autre')
                if cat not in par_categorie:
                    par_categorie[cat] = []
                par_categorie[cat].append(r)
            
            # Afficher par catégorie
            for cat, produits in sorted(par_categorie.items()):
                lines.append(f"✨ 📋 **{cat}** ({len(produits)} produits)")
                lines.append("| **Code** | **Produit** | **Stock** | **Minimum** | **Manquant** | **Commandé** | **Fournisseur** |")
                lines.append("|----------|-------------|----------|-------------|--------------|--------------|-----------------|")
                
                for prod in produits[:10]:  # Limiter à 10 par catégorie
                    code = prod.get('code_produit', '')
                    nom = prod.get('nom', '')
                    stock = prod.get('stock_disponible', 0)
                    minimum = prod.get('stock_minimum', 0)
                    manquant = prod.get('manquant', 0)
                    commande = prod.get('stock_commande', 0)
                    fourn = prod.get('fournisseur_principal', 'N/A')
                    
                    # Indicateur visuel
                    if stock == 0:
                        emoji = "🔴"  # Rouge - rupture totale
                    elif stock < minimum / 2:
                        emoji = "🟡"  # Jaune - très bas
                    else:
                        emoji = "🟠"  # Orange - sous minimum
                    
                    lines.append(f"| {emoji} {code} | {nom} | {stock} | {minimum} | {abs(manquant)} | {commande} | {fourn} |")
                lines.append("")
            
            # Résumé
            total = len(data['ruptures'])
            ruptures_totales = len([r for r in data['ruptures'] if r.get('stock_disponible', 0) == 0])
            lines.append(f"✨ 📋 **Résumé**:")
            lines.append(f"- Total: {total} produits sous le stock minimum")
            lines.append(f"- Ruptures totales: {ruptures_totales} produits")
            lines.append(f"- À commander d'urgence: {ruptures_totales + len([r for r in data['ruptures'] if r.get('stock_disponible', 0) < r.get('stock_minimum', 0) / 2])} produits")
        else:
            lines.append("🎉 **Excellent ! Aucune rupture de stock**")
            lines.append("Tous les produits sont au-dessus du stock minimum.")
        
        return "\n".join(lines)
    
    def _format_projets_retard(self, data: Dict) -> str:
        """Formate la liste des projets en retard"""
        if 'error' in data:
            return f"❌ **Erreur:** {data['error']}"
        
        lines = []
        lines.append("## ⏰ **Projets en retard ou à risque**\n")
        
        if data.get('projets'):
            # Séparer par statut
            en_retard = [p for p in data['projets'] if p.get('statut_delai') == 'En retard']
            a_risque = [p for p in data['projets'] if p.get('statut_delai') == 'À risque']
            
            # Projets en retard
            if en_retard:
                lines.append(f"✨ 🔴 **En retard** ({len(en_retard)} projets)")
                lines.append("| **Projet** | **Client** | **Date prévue** | **Retard** | **Budget** | **Statut** |")
                lines.append("|------------|------------|----------------|------------|------------|------------|")
                
                for proj in en_retard:
                    nom = proj.get('nom_projet', '')
                    client = proj.get('client_nom', 'N/A')
                    date = proj.get('date_prevu', 'N/A')
                    jours = abs(int(proj.get('jours_restants', 0)))
                    budget = f"{proj.get('prix_estime', 0):,.0f}$" if proj.get('prix_estime') else 'N/A'
                    statut = proj.get('statut', '')
                    lines.append(f"| 🔴 {nom} | {client} | {date} | {jours}j | {budget} | {statut} |")
                lines.append("")
            
            # Projets à risque
            if a_risque:
                lines.append(f"✨ 🟡 **À risque** ({len(a_risque)} projets)")
                lines.append("| **Projet** | **Client** | **Date prévue** | **Jours restants** | **Budget** | **Statut** |")
                lines.append("|------------|------------|----------------|---------------------|------------|------------|")
                
                for proj in a_risque:
                    nom = proj.get('nom_projet', '')
                    client = proj.get('client_nom', 'N/A')
                    date = proj.get('date_prevu', 'N/A')
                    jours = int(proj.get('jours_restants', 0))
                    budget = f"{proj.get('prix_estime', 0):,.0f}$" if proj.get('prix_estime') else 'N/A'
                    statut = proj.get('statut', '')
                    lines.append(f"| 🟡 {nom} | {client} | {date} | {jours}j | {budget} | {statut} |")
                lines.append("")
            
            # Résumé
            lines.append("✨ 📋 **Résumé**:")
            lines.append(f"- 🔴 {len(en_retard)} projet(s) en retard")
            lines.append(f"- 🟡 {len(a_risque)} projet(s) à risque (3 jours ou moins)")
            
            # Valeur totale à risque
            valeur_totale = sum(p.get('prix_estime', 0) for p in data['projets'] if p.get('prix_estime'))
            if valeur_totale > 0:
                lines.append(f"- 💰 Valeur totale à risque: {valeur_totale:,.0f} $")
        else:
            lines.append("🎉 **Excellent ! Tous les projets sont dans les temps**")
            lines.append("Aucun projet en retard ou à risque.")
        
        return "\n".join(lines)
    
    def _format_dashboard(self, data: Dict) -> str:
        """Formate le tableau de bord avec KPIs"""
        if 'error' in data:
            return f"❌ **Erreur:** {data['error']}"
        
        lines = []
        lines.append("## 📊 **Tableau de bord ERP**\n")
        
        # KPIs principaux en cartes
        lines.append("### 🎯 **Indicateurs clés de performance**\n")
        
        # Projets
        lines.append("#### 📁 **Projets**")
        lines.append(f"- **Total actifs**: {data.get('projets_actifs', 0)}")
        lines.append(f"- **En retard**: 🔴 {data.get('projets_retard', 0)}")
        lines.append(f"- **À risque**: 🟡 {data.get('projets_risque', 0)}")
        lines.append(f"- **Valeur totale**: {data.get('valeur_projets', 0):,.0f} $")
        lines.append("")
        
        # Production
        lines.append("#### 🏭 **Production**")
        lines.append(f"- **Bons de travail actifs**: {data.get('bt_actifs', 0)}")
        lines.append(f"- **Employés occupés**: {data.get('employes_occupes', 0)}/{data.get('employes_total', 0)}")
        lines.append(f"- **Postes utilisés**: {data.get('postes_occupes', 0)}/{data.get('postes_total', 0)}")
        lines.append("")
        
        # Inventaire
        lines.append("#### 📦 **Inventaire**")
        lines.append(f"- **Articles en rupture**: 🔴 {data.get('rupture_stock', 0)}")
        lines.append(f"- **Stock faible**: 🟡 {data.get('stock_faible', 0)}")
        lines.append(f"- **Valeur inventaire**: {data.get('valeur_inventaire', 0):,.0f} $")
        lines.append("")
        
        # Finances
        lines.append("#### 💰 **Finances**")
        lines.append(f"- **Factures impayées**: {data.get('factures_impayees', 0)}")
        lines.append(f"- **Montant impayé**: {data.get('montant_impaye', 0):,.0f} $")
        lines.append(f"- **Devis en attente**: {data.get('devis_attente', 0)}")
        lines.append(f"- **Valeur devis**: {data.get('valeur_devis', 0):,.0f} $")
        
        return "\n".join(lines)
    
    def _format_impayes(self, data: Dict) -> str:
        """Formate la liste des factures impayées"""
        if 'error' in data:
            return f"❌ **Erreur:** {data['error']}"
        
        lines = []
        lines.append("## 💸 **Factures clients impayées**\n")
        
        if data.get('factures'):
            # Statistiques
            total_impaye = sum(f.get('montant_du', 0) for f in data['factures'])
            nb_factures = len(data['factures'])
            plus_ancienne = min(f.get('jours_retard', 0) for f in data['factures']) if data['factures'] else 0
            
            lines.append(f"### 📊 **Résumé**")
            lines.append(f"- **Total impayé**: {total_impaye:,.2f} $")
            lines.append(f"- **Nombre de factures**: {nb_factures}")
            lines.append(f"- **Plus ancien retard**: {plus_ancienne} jours")
            lines.append("")
            
            # Tableau des factures
            lines.append("### 📋 **Détail des factures**")
            lines.append("| **Facture** | **Client** | **Date** | **Échéance** | **Montant** | **Retard** | **Statut** |")
            lines.append("|-------------|------------|----------|--------------|-------------|------------|------------|")
            
            for facture in sorted(data['factures'], key=lambda x: x.get('jours_retard', 0), reverse=True):
                numero = facture.get('numero_document', '')
                client = facture.get('client_nom', 'N/A')
                date = facture.get('date_facture', 'N/A')
                echeance = facture.get('date_echeance', 'N/A')
                montant = f"{facture.get('montant_du', 0):,.2f} $"
                retard = facture.get('jours_retard', 0)
                
                # Indicateur visuel selon le retard
                if retard > 60:
                    indicateur = "🔴"
                elif retard > 30:
                    indicateur = "🟠"
                elif retard > 15:
                    indicateur = "🟡"
                else:
                    indicateur = "🟢"
                
                lines.append(f"| {numero} | {client} | {date} | {echeance} | {montant} | {indicateur} {retard}j | EN_RETARD |")
            
            lines.append("")
            
            # Répartition par client
            clients_group = {}
            for f in data['factures']:
                client = f.get('client_nom', 'N/A')
                if client not in clients_group:
                    clients_group[client] = {'count': 0, 'total': 0}
                clients_group[client]['count'] += 1
                clients_group[client]['total'] += f.get('montant_du', 0)
            
            lines.append("### 🏢 **Par client**")
            lines.append("| **Client** | **Nb factures** | **Total impayé** | **%** |")
            lines.append("|------------|-----------------|------------------|-------|")
            
            for client, info in sorted(clients_group.items(), key=lambda x: x[1]['total'], reverse=True):
                pct = (info['total'] / total_impaye * 100) if total_impaye > 0 else 0
                lines.append(f"| {client} | {info['count']} | {info['total']:,.2f} $ | {pct:.1f}% |")
        else:
            lines.append("✅ **Excellent ! Aucune facture impayée**")
        
        return "\n".join(lines)
    
    def _format_charge_travail(self, data: Dict) -> str:
        """Formate la charge de travail par employé"""
        if 'error' in data:
            return f"❌ **Erreur:** {data['error']}"
        
        lines = []
        debut = data.get('semaine_debut', '')
        fin = data.get('semaine_fin', '')
        if debut and fin:
            semaine = f"du {debut} au {fin}"
        else:
            semaine = data.get('semaine', 'courante')
        lines.append(f"## 👷 **Charge de travail - Semaine {semaine}**\n")
        
        if data.get('charge_employes'):
            # Statistiques globales
            total_heures = sum(e.get('heures_assignees', 0) for e in data['charge_employes'])
            total_employes = len(data['charge_employes'])
            moy_heures = total_heures / total_employes if total_employes > 0 else 0
            
            lines.append("### 📊 **Vue d'ensemble**")
            lines.append(f"- **Employés assignés**: {total_employes}")
            lines.append(f"- **Total heures planifiées**: {total_heures:.0f}h")
            lines.append(f"- **Moyenne par employé**: {moy_heures:.1f}h")
            lines.append("")
            
            # Tableau de charge
            lines.append("### 📋 **Charge par employé**")
            lines.append("| **Employé** | **Poste** | **Heures** | **Charge** | **BT assignés** | **Projets** | **Statut** |")
            lines.append("|-------------|-----------|------------|------------|-----------------|-------------|------------|")
            
            for emp in sorted(data['charge_employes'], key=lambda x: x.get('heures_assignees', 0), reverse=True):
                nom = f"{emp.get('prenom', '')} {emp.get('nom', '')}"
                poste = emp.get('poste', 'N/A')
                heures = emp.get('heures_assignees', 0)
                
                # Calcul du taux de charge
                charge_pct = (heures / 40) * 100  # Base 40h/semaine
                if charge_pct > 100:
                    indicateur = "🔴"
                    statut = "Surchargé"
                elif charge_pct > 80:
                    indicateur = "🟡"
                    statut = "Chargé"
                elif charge_pct > 50:
                    indicateur = "🟢"
                    statut = "Normal"
                else:
                    indicateur = "⚪"
                    statut = "Disponible"
                
                nb_bt = emp.get('nb_bons_travail', 0)
                projets_str = emp.get('projets', '')
                projets = projets_str.split(',') if projets_str else []
                projets_display = ', '.join(p.strip() for p in projets if p.strip()) if projets else 'N/A'
                
                lines.append(f"| {nom} | {poste} | {heures:.1f}h | {indicateur} {charge_pct:.0f}% | {nb_bt} | {projets_display} | {statut} |")
            
            lines.append("")
            
            # Alertes de surcharge
            surcharges = [e for e in data['charge_employes'] if e.get('heures_assignees', 0) > 40]
            if surcharges:
                lines.append("### ⚠️ **Alertes de surcharge**")
                for emp in surcharges:
                    nom = f"{emp.get('prenom', '')} {emp.get('nom', '')}"
                    heures = emp.get('heures_assignees', 0)
                    surplus = heures - 40
                    lines.append(f"- 🔴 **{nom}**: {heures:.1f}h assignées (+{surplus:.1f}h)")
        else:
            lines.append("ℹ️ Aucune charge de travail pour cette semaine")
        
        return "\n".join(lines)
    
    def _format_a_commander(self, data: Dict) -> str:
        """Formate la liste des produits à commander"""
        if 'error' in data:
            return f"❌ **Erreur:** {data['error']}"
        
        lines = []
        lines.append("## 🛒 **Produits à réapprovisionner**\n")
        
        if data.get('produits'):
            # Séparer par urgence
            rupture = [p for p in data['produits'] if p.get('stock_disponible', 0) <= 0]
            critique = [p for p in data['produits'] if p.get('stock_disponible', 0) > 0 and p.get('stock_disponible', 0) < p.get('seuil_critique', 1)]
            faible = [p for p in data['produits'] if p.get('stock_disponible', 0) >= p.get('seuil_critique', 1)]
            
            # Statistiques
            lines.append("### 📊 **Résumé**")
            lines.append(f"- 🔴 **En rupture**: {len(rupture)} produits")
            lines.append(f"- 🟠 **Stock critique**: {len(critique)} produits")
            lines.append(f"- 🟡 **Stock faible**: {len(faible)} produits")
            
            # Valeur totale à commander
            valeur_totale = sum(p.get('qte_a_commander', 0) * p.get('prix_unitaire', 0) for p in data['produits'])
            lines.append(f"- 💰 **Valeur totale estimée**: {valeur_totale:,.2f} $")
            lines.append("")
            
            # Produits en rupture
            if rupture:
                lines.append("### 🔴 **En rupture de stock**")
                lines.append("| **Code** | **Produit** | **Stock** | **À commander** | **Fournisseur** | **Prix unit.** | **Total** |")
                lines.append("|----------|-------------|----------|-----------------|-----------------|----------------|-----------|")
                
                for prod in rupture:
                    code = prod.get('code_produit', '')
                    nom = prod.get('nom', '')
                    stock = f"{prod.get('stock_disponible', 0)} {prod.get('unite_vente', '')}"
                    qte = f"{prod.get('qte_a_commander', 0)} {prod.get('unite_vente', '')}"
                    fourn = prod.get('fournisseur_principal', 'N/A')
                    prix = f"{prod.get('prix_unitaire', 0):.2f} $"
                    total = f"{prod.get('qte_a_commander', 0) * prod.get('prix_unitaire', 0):.2f} $"
                    lines.append(f"| {code} | {nom} | 🔴 {stock} | {qte} | {fourn} | {prix} | {total} |")
                lines.append("")
            
            # Stock critique
            if critique:
                lines.append("### 🟠 **Stock critique**")
                lines.append("| **Code** | **Produit** | **Stock** | **Seuil** | **À commander** | **Fournisseur** | **Total** |")
                lines.append("|----------|-------------|----------|-----------|-----------------|-----------------|-----------|")
                
                for prod in critique:
                    code = prod.get('code_produit', '')
                    nom = prod.get('nom', '')
                    stock = f"{prod.get('stock_disponible', 0)}"
                    seuil = f"{prod.get('seuil_critique', 0)}"
                    qte = f"{prod.get('qte_a_commander', 0)} {prod.get('unite_vente', '')}"
                    fourn = prod.get('fournisseur_principal', 'N/A')
                    total = f"{prod.get('qte_a_commander', 0) * prod.get('prix_unitaire', 0):.2f} $"
                    lines.append(f"| {code} | {nom} | 🟠 {stock} | {seuil} | {qte} | {fourn} | {total} |")
                lines.append("")
            
            # Regroupement par fournisseur
            fourn_group = {}
            for p in data['produits']:
                fourn = p.get('fournisseur_principal', 'N/A')
                if fourn not in fourn_group:
                    fourn_group[fourn] = {'count': 0, 'total': 0}
                fourn_group[fourn]['count'] += 1
                fourn_group[fourn]['total'] += p.get('qte_a_commander', 0) * p.get('prix_unitaire', 0)
            
            lines.append("### 🚚 **Par fournisseur**")
            lines.append("| **Fournisseur** | **Nb produits** | **Montant total** |")
            lines.append("|-----------------|-----------------|-------------------|")
            
            for fourn, info in sorted(fourn_group.items(), key=lambda x: x[1]['total'], reverse=True):
                lines.append(f"| {fourn} | {info['count']} | {info['total']:,.2f} $ |")
        else:
            lines.append("✅ **Stock optimal - Aucun produit à commander**")
        
        return "\n".join(lines)
    
    def _format_performance(self, data: Dict) -> str:
        """Formate les indicateurs de performance mensuels"""
        if 'error' in data:
            return f"❌ **Erreur:** {data['error']}"
        
        lines = []
        mois = data.get('mois', 'en cours')
        lines.append(f"## 📈 **Performance - {mois}**\n")
        
        # Production
        lines.append("### 🏭 **Indicateurs de production**")
        lines.append(f"- **Bons de travail complétés**: {data.get('bt_completes', 0)}")
        lines.append(f"- **Taux de complétion**: {data.get('taux_completion', 0):.1f}%")
        lines.append(f"- **Temps moyen par BT**: {data.get('temps_moyen_bt', 0):.1f} heures")
        lines.append(f"- **Efficacité**: {data.get('efficacite_production', 0):.1f}%")
        lines.append("")
        
        # Projets
        lines.append("### 📁 **Performance des projets**")
        lines.append(f"- **Projets livrés**: {data.get('projets_livres', 0)}")
        lines.append(f"- **Projets en retard**: {data.get('projets_retard_mois', 0)}")
        lines.append(f"- **Taux de respect des délais**: {data.get('taux_respect_delais', 0):.1f}%")
        lines.append(f"- **Marge moyenne**: {data.get('marge_moyenne', 0):.1f}%")
        lines.append("")
        
        # Finances
        lines.append("### 💰 **Performance financière**")
        lines.append(f"- **Chiffre d'affaires**: {data.get('chiffre_affaires', 0):,.0f} $")
        lines.append(f"- **Coûts de production**: {data.get('couts_production', 0):,.0f} $")
        lines.append(f"- **Profit brut**: {data.get('profit_brut', 0):,.0f} $")
        lines.append(f"- **Taux de profit**: {data.get('taux_profit', 0):.1f}%")
        lines.append("")
        
        # Top employés
        if data.get('top_employes'):
            lines.append("### 🏆 **Top 5 employés du mois**")
            lines.append("| **Rang** | **Employé** | **Heures** | **BT complétés** | **Efficacité** |")
            lines.append("|----------|-------------|------------|------------------|----------------|")
            
            for i, emp in enumerate(data['top_employes'][:5], 1):
                nom = f"{emp.get('prenom', '')} {emp.get('nom', '')}"
                heures = emp.get('heures_travaillees', 0)
                bt = emp.get('bt_completes', 0)
                eff = emp.get('efficacite', 0)
                medaille = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                lines.append(f"| {medaille} | {nom} | {heures:.1f}h | {bt} | {eff:.1f}% |")
            lines.append("")
        
        # Évolution vs mois précédent
        lines.append("### 📊 **Évolution vs mois précédent**")
        evolution_ca = data.get('evolution_ca', 0)
        evolution_prod = data.get('evolution_production', 0)
        evolution_eff = data.get('evolution_efficacite', 0)
        
        lines.append(f"- **Chiffre d'affaires**: {'+' if evolution_ca >= 0 else ''}{evolution_ca:.1f}% {'📈' if evolution_ca > 0 else '📉' if evolution_ca < 0 else '➡️'}")
        lines.append(f"- **Production**: {'+' if evolution_prod >= 0 else ''}{evolution_prod:.1f}% {'📈' if evolution_prod > 0 else '📉' if evolution_prod < 0 else '➡️'}")
        lines.append(f"- **Efficacité**: {'+' if evolution_eff >= 0 else ''}{evolution_eff:.1f}% {'📈' if evolution_eff > 0 else '📉' if evolution_eff < 0 else '➡️'}")
        
        return "\n".join(lines)


def show_assistant_ia_page(db=None):
    """
    Fonction principale pour afficher la page de l'assistant IA
    Appelée depuis app.py
    """
    # Initialiser l'assistant
    if 'assistant_ia_simple' not in st.session_state:
        st.session_state.assistant_ia_simple = AssistantIASimple(db=db)
    
    # Afficher la page
    st.session_state.assistant_ia_simple.show_page()