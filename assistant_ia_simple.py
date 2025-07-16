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
                        context['format_projets'] = "tableau"  # Indication pour formater en tableau
                
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