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
                self.model = "claude-3-opus-20240229"
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
                    results['projets'] = [dict(p) for p in projects]
            
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
            
        except Exception as e:
            logger.error(f"Erreur recherche ERP: {e}")
            results['error'] = str(e)
        
        return results
    
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
        """Récupère spécifiquement les projets en cours"""
        if not self.db:
            return []
        
        try:
            # Requête simple pour les projets en cours
            projects = self.db.execute_query("""
                SELECT 
                    p.nom_projet,
                    p.statut,
                    p.priorite,
                    p.prix_estime,
                    p.description,
                    p.date_prevu,
                    c.nom as client_nom
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE p.statut = 'EN COURS'
                ORDER BY p.priorite DESC, p.updated_at DESC
            """)
            
            return [dict(p) for p in projects] if projects else []
            
        except Exception as e:
            logger.error(f"Erreur récupération projets en cours: {e}")
            # Essai sans jointure si erreur
            try:
                projects = self.db.execute_query("""
                    SELECT nom_projet, statut, priorite, prix_estime, description, date_prevu
                    FROM projects
                    WHERE statut = 'EN COURS'
                    ORDER BY priorite DESC
                """)
                return [dict(p) for p in projects] if projects else []
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
Réponds de manière professionnelle et concise. Utilise les données ERP quand c'est pertinent."""
            
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
                    st.markdown(f"""
                    <div class="message-assistant">
                        <strong>🤖 Assistant:</strong><br>
                        {msg['content']}
                    </div>
                    """, unsafe_allow_html=True)
        
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
            results = self._search_erp_data(query)
            
            # Enrichir avec Claude si disponible
            if self.client and results:
                context = {'recherche_erp': results}
                return self._get_claude_response(
                    f"Présente ces résultats de recherche ERP de manière claire: {json.dumps(results, ensure_ascii=False)}",
                    context
                )
            else:
                return self._format_search_results(results)
        
        # Question normale - utiliser Claude avec contexte ERP
        else:
            # Vérifier si la question concerne l'ERP
            erp_keywords = ['projet', 'stock', 'inventaire', 'employé', 'client', 'production', 'bon de travail']
            
            context = {}
            
            # Si mots-clés ERP détectés, chercher des données pertinentes
            if any(keyword in input_lower for keyword in erp_keywords):
                # Pour les questions sur les projets en cours spécifiquement
                if 'en cours' in input_lower and 'projet' in input_lower:
                    projets_en_cours = self._get_current_projects()
                    if projets_en_cours:
                        context['projets_en_cours'] = projets_en_cours
                
                # Recherche automatique générale
                search_results = self._search_erp_data(user_input)
                if search_results:
                    context['donnees_erp'] = search_results
                
                # Ajouter les stats si demandé
                if any(word in input_lower for word in ['statistique', 'stats', 'nombre', 'combien']):
                    context['statistiques'] = self._get_erp_statistics()
            
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
        """Formate les statistiques pour l'affichage"""
        if not stats:
            return "Aucune statistique disponible."
        
        lines = ["**📊 Statistiques ERP**\n"]
        
        # Projets
        if 'projets' in stats:
            lines.append("**Projets:**")
            total = 0
            for statut, data in stats['projets'].items():
                lines.append(f"- {statut}: {data['nombre']} projets ({data['valeur']:,.0f}$)")
                total += data['nombre']
            lines.append(f"- **Total**: {total} projets\n")
        
        # Autres stats
        if 'stock_faible' in stats:
            lines.append(f"**⚠️ Articles en stock faible:** {stats['stock_faible']}")
        
        if 'employes_disponibles' in stats:
            lines.append(f"**👥 Employés disponibles:** {stats['employes_disponibles']}")
        
        if 'bons_travail_actifs' in stats:
            lines.append(f"**📋 Bons de travail actifs:** {stats['bons_travail_actifs']}")
        
        return "\n".join(lines)
    
    def _format_search_results(self, results: Dict) -> str:
        """Formate les résultats de recherche"""
        if 'error' in results:
            return f"❌ Erreur: {results['error']}"
        
        if not results:
            return "Aucun résultat trouvé."
        
        lines = ["**🔍 Résultats de recherche ERP**\n"]
        
        # Projets
        if 'projets' in results:
            lines.append("**Projets trouvés:**")
            for p in results['projets']:
                lines.append(f"- **{p['nom_projet']}** ({p['statut']})")
                lines.append(f"  Client: {p.get('client_nom', 'N/A')}")
                if p.get('prix_estime'):
                    lines.append(f"  Budget: {p['prix_estime']:,.0f}$")
            lines.append("")
        
        # Inventaire
        if 'inventaire' in results:
            lines.append("**Articles d'inventaire:**")
            for item in results['inventaire']:
                lines.append(f"- **{item['nom']}**")
                lines.append(f"  Quantité: {item['quantite_metric']}")
                lines.append(f"  Statut: {item['statut']}")
            lines.append("")
        
        # Employés
        if 'employes' in results:
            lines.append("**Employés:**")
            for emp in results['employes']:
                lines.append(f"- **{emp['prenom']} {emp['nom']}**")
                lines.append(f"  Poste: {emp['poste']}")
                if emp.get('competences'):
                    lines.append(f"  Compétences: {emp['competences']}")
            lines.append("")
        
        # Entreprises
        if 'entreprises' in results:
            lines.append("**Entreprises:**")
            for comp in results['entreprises']:
                lines.append(f"- **{comp['nom']}**")
                lines.append(f"  Secteur: {comp['secteur']}")
                lines.append(f"  Ville: {comp['ville']}")
        
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