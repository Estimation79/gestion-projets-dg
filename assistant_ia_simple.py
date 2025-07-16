# assistant_ia_simple.py - Module Assistant IA Expert sans dépendances externes
# Version simplifiée qui utilise uniquement les modules déjà présents dans l'ERP

import streamlit as st
import os
import json
from datetime import datetime
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
                    SELECT nom, prenom, poste, competences 
                    FROM employees 
                    WHERE nom LIKE ? OR prenom LIKE ? OR competences LIKE ?
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
        
        # Entreprises avec style carte
        if 'entreprises' in results and results['entreprises']:
            lines.append("### 🏢 **Entreprises**\n")
            for comp in results['entreprises']:
                lines.append(f"**➤ {comp['nom']}**")
                lines.append(f"- 🏭 Secteur: `{comp['secteur']}`")
                lines.append(f"- 📍 Ville: `{comp['ville']}`")
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