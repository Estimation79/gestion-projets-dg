# assistant_ia_expert.py - Module Assistant IA Expert intégré
# ERP Production DG Inc. - Intelligence Artificielle avec interface élégante
# Basé sur ai_expert_app.py avec intégration base de données ERP

import streamlit as st
import os
import io
import html
import markdown
import json
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import logging

# Importer les classes logiques
try:
    from expert_logic import ExpertAdvisor, ExpertProfileManager
    from conversation_manager import ConversationManager
    from cache_config import CacheOptimizer
except ImportError as e:
    st.error(f"Erreur d'importation des modules: {e}")
    st.stop()

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AssistantIAExpert:
    """
    Assistant IA Expert avec interface élégante et accès à la base de données ERP
    Remplace complètement assistant_ia.py avec une meilleure interface
    """
    
    def __init__(self, db=None, api_key: Optional[str] = None):
        """
        Initialise l'assistant IA Expert
        
        Args:
            db: Instance ERPDatabase pour accéder aux données
            api_key: Clé API Anthropic (ou depuis variable d'environnement)
        """
        self.db = db
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('CLAUDE_API_KEY')
        self.cache_optimizer = CacheOptimizer()
        
        # Initialisation des gestionnaires
        self._init_profile_manager()
        self._init_expert_advisor()
        self._init_conversation_manager()
        
        # Initialisation des états de session
        self._init_session_states()
        
        logger.info("✅ Assistant IA Expert initialisé avec succès")
    
    def _init_profile_manager(self):
        """Initialise le gestionnaire de profils"""
        try:
            profile_dir_path = "profiles"
            if not os.path.exists(profile_dir_path):
                os.makedirs(profile_dir_path, exist_ok=True)
                # Créer un profil par défaut pour l'ERP
                default_profile_path = os.path.join(profile_dir_path, "expert_erp.txt")
                if not os.path.exists(default_profile_path):
                    with open(default_profile_path, "w", encoding="utf-8") as f:
                        f.write("""Expert ERP Métallurgie
Je suis un expert spécialisé dans la gestion ERP pour l'industrie métallurgique. 
J'ai accès aux données de votre système ERP incluant:
- Projets et opérations de production
- Inventaire et gestion des stocks
- CRM et gestion des clients/fournisseurs
- Ressources humaines et compétences
- Bons de travail et suivi de production
- Analyses et statistiques de performance

Je peux vous aider à analyser vos données, optimiser vos processus, et répondre à toutes vos questions concernant votre activité.""")
                    logger.info("Profil expert ERP créé")
            
            if 'profile_manager' not in st.session_state:
                st.session_state.profile_manager = ExpertProfileManager(profile_dir=profile_dir_path)
                
        except Exception as e:
            logger.error(f"Erreur init ProfileManager: {e}")
            raise
    
    def _init_expert_advisor(self):
        """Initialise l'advisor expert"""
        if 'expert_advisor' not in st.session_state:
            if not self.api_key:
                st.error("❌ Clé API Claude non configurée")
                st.info("Configurez la variable d'environnement ANTHROPIC_API_KEY ou CLAUDE_API_KEY")
                st.stop()
            
            try:
                st.session_state.expert_advisor = ExpertAdvisor(api_key=self.api_key)
                st.session_state.expert_advisor.profile_manager = st.session_state.profile_manager
                
                # Charger le profil ERP par défaut
                available_profiles = st.session_state.profile_manager.get_profile_names()
                if available_profiles:
                    # Préférer le profil ERP s'il existe
                    erp_profile = next((p for p in available_profiles if 'ERP' in p), available_profiles[0])
                    st.session_state.selected_profile_name = erp_profile
                    st.session_state.expert_advisor.set_current_profile_by_name(erp_profile)
                    
            except Exception as e:
                logger.error(f"Erreur init ExpertAdvisor: {e}")
                raise
    
    def _init_conversation_manager(self):
        """Initialise le gestionnaire de conversations"""
        if 'conversation_manager' not in st.session_state:
            try:
                db_file_path = "conversations_erp.db"
                st.session_state.conversation_manager = ConversationManager(db_path=db_file_path)
                logger.info(f"ConversationManager initialisé: {os.path.abspath(db_file_path)}")
            except Exception as e:
                logger.error(f"Erreur init ConversationManager: {e}")
                st.session_state.conversation_manager = None
    
    def _init_session_states(self):
        """Initialise les états de session nécessaires"""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "current_conversation_id" not in st.session_state:
            st.session_state.current_conversation_id = None
        if "processed_messages" not in st.session_state:
            st.session_state.processed_messages = set()
    
    # =========================================================================
    # MÉTHODES D'ACCÈS AUX DONNÉES ERP
    # =========================================================================
    
    def _get_erp_context(self) -> str:
        """Récupère le contexte ERP actuel pour enrichir les réponses"""
        if not self.db:
            return ""
        
        context_parts = []
        
        try:
            # Statistiques générales
            stats = self._get_erp_statistics()
            if stats:
                context_parts.append(f"Statistiques ERP actuelles: {json.dumps(stats, ensure_ascii=False)}")
            
            # Projets actifs
            active_projects = self.db.execute_query("""
                SELECT nom_projet, statut, prix_estime, date_echeance 
                FROM projects 
                WHERE statut IN ('EN COURS', 'À FAIRE') 
                LIMIT 5
            """)
            if active_projects:
                context_parts.append(f"Projets actifs: {len(active_projects)}")
            
            # Alertes inventaire
            low_stock = self.db.execute_query("""
                SELECT COUNT(*) as count 
                FROM inventory_items 
                WHERE quantite_metric <= limite_minimale_metric
            """)
            if low_stock and low_stock[0]['count'] > 0:
                context_parts.append(f"Articles en rupture de stock: {low_stock[0]['count']}")
            
        except Exception as e:
            logger.error(f"Erreur récupération contexte ERP: {e}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def _get_erp_statistics(self) -> Dict[str, Any]:
        """Récupère les statistiques globales de l'ERP"""
        if not self.db:
            return {}
        
        try:
            stats = {}
            
            # Nombre de projets par statut
            project_stats = self.db.execute_query("""
                SELECT statut, COUNT(*) as count 
                FROM projects 
                GROUP BY statut
            """)
            stats['projets'] = {row['statut']: row['count'] for row in project_stats}
            
            # Valeur totale inventaire
            inventory_value = self.db.execute_query("""
                SELECT SUM(quantite_metric * 50) as valeur_totale 
                FROM inventory_items
            """)
            stats['valeur_inventaire'] = inventory_value[0]['valeur_totale'] if inventory_value else 0
            
            # Nombre d'employés actifs
            employees = self.db.execute_query("SELECT COUNT(*) as count FROM employees WHERE disponible = 1")
            stats['employes_actifs'] = employees[0]['count'] if employees else 0
            
            # Nombre de clients
            clients = self.db.execute_query("SELECT COUNT(*) as count FROM companies")
            stats['nombre_clients'] = clients[0]['count'] if clients else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur récupération statistiques: {e}")
            return {}
    
    def _search_erp_data(self, query: str) -> str:
        """Recherche dans les données ERP selon la requête"""
        if not self.db:
            return "Accès à la base de données ERP non disponible."
        
        results = []
        query_lower = query.lower()
        
        try:
            # Recherche dans les projets
            if any(word in query_lower for word in ['projet', 'project', 'chantier']):
                projects = self.db.execute_query("""
                    SELECT p.*, c.nom as client_nom 
                    FROM projects p 
                    LEFT JOIN companies c ON p.client_id = c.id 
                    WHERE p.nom_projet LIKE ? OR p.description LIKE ?
                    LIMIT 10
                """, (f'%{query}%', f'%{query}%'))
                
                if projects:
                    results.append("**Projets trouvés:**")
                    for p in projects:
                        results.append(f"- {p['nom_projet']} ({p['statut']}) - Client: {p['client_nom']}")
            
            # Recherche dans l'inventaire
            if any(word in query_lower for word in ['stock', 'inventaire', 'matériel', 'pièce']):
                items = self.db.execute_query("""
                    SELECT nom, quantite_metric, quantite_imperial, statut 
                    FROM inventory_items 
                    WHERE nom LIKE ? OR description LIKE ?
                    LIMIT 10
                """, (f'%{query}%', f'%{query}%'))
                
                if items:
                    results.append("\n**Articles d'inventaire trouvés:**")
                    for item in items:
                        results.append(f"- {item['nom']}: {item['quantite_metric']} ({item['statut']})")
            
            # Recherche dans les employés
            if any(word in query_lower for word in ['employé', 'employee', 'personnel', 'équipe']):
                employees = self.db.execute_query("""
                    SELECT nom, prenom, poste, competences 
                    FROM employees 
                    WHERE nom LIKE ? OR prenom LIKE ? OR competences LIKE ?
                    LIMIT 10
                """, (f'%{query}%', f'%{query}%', f'%{query}%'))
                
                if employees:
                    results.append("\n**Employés trouvés:**")
                    for emp in employees:
                        results.append(f"- {emp['prenom']} {emp['nom']} - {emp['poste']}")
            
            # Recherche dans les entreprises
            if any(word in query_lower for word in ['client', 'fournisseur', 'entreprise', 'company']):
                companies = self.db.execute_query("""
                    SELECT nom, secteur, ville, telephone 
                    FROM companies 
                    WHERE nom LIKE ? OR secteur LIKE ?
                    LIMIT 10
                """, (f'%{query}%', f'%{query}%'))
                
                if companies:
                    results.append("\n**Entreprises trouvées:**")
                    for comp in companies:
                        results.append(f"- {comp['nom']} ({comp['secteur']}) - {comp['ville']}")
            
        except Exception as e:
            logger.error(f"Erreur recherche ERP: {e}")
            return f"Erreur lors de la recherche: {str(e)}"
        
        return "\n".join(results) if results else "Aucun résultat trouvé dans l'ERP pour cette recherche."
    
    # =========================================================================
    # MÉTHODES D'INTERFACE
    # =========================================================================
    
    def show_page(self):
        """Affiche la page principale de l'assistant IA Expert"""
        # CSS et styles
        self._apply_styles()
        
        # Header principal
        self._show_header()
        
        # Sidebar
        with st.sidebar:
            self._show_sidebar()
        
        # Zone de chat principale
        self._show_chat_area()
        
        # Input de chat
        self._handle_chat_input()
        
        # Footer
        self._show_footer()
    
    def _apply_styles(self):
        """Applique les styles CSS personnalisés"""
        st.markdown("""
        <style>
        /* Import de la police moderne */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Styles spécifiques pour l'assistant IA */
        .ia-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }
        
        .ia-header h1 {
            margin: 0;
            font-size: 2.5rem;
            font-weight: 700;
        }
        
        .ia-header p {
            margin: 0.5rem 0 0 0;
            opacity: 0.9;
            font-size: 1.1rem;
        }
        
        /* Messages de chat améliorés */
        div[data-testid="stChatMessage"] {
            border-radius: 12px;
            margin-bottom: 1rem;
            padding: 1rem;
            animation: fadeIn 0.5s ease-out;
        }
        
        /* Message utilisateur */
        div[data-testid="stChatMessage"]:has(div[data-testid^="chatAvatarIcon-user"]) {
            background: linear-gradient(to right, #f0f7ff, #e6f3ff);
            border-left: 4px solid #3B82F6;
            margin-left: 20%;
        }
        
        /* Message assistant */
        div[data-testid="stChatMessage"]:has(div[data-testid^="chatAvatarIcon-assistant"]) {
            background: linear-gradient(to right, #f7f9fc, #ffffff);
            border-left: 4px solid #8B5CF6;
            margin-right: 20%;
        }
        
        /* Message recherche web */
        div[data-testid="stChatMessage"]:has(div[data-testid^="chatAvatarIcon-search"]) {
            background: linear-gradient(to right, #f0fdf4, #e6f7ec);
            border-left: 4px solid #22c55e;
        }
        
        /* Animation */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Zone d'analyse */
        .analysis-container {
            background: linear-gradient(to right, #f0f7ff, #e6f3ff);
            border-radius: 12px;
            padding: 20px;
            margin: 1rem 0;
            border-left: 5px solid #3B82F6;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }
        
        .analysis-section {
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        }
        
        /* Sidebar améliorée */
        section[data-testid="stSidebar"] {
            background: linear-gradient(to bottom, #f8fafc, #f1f5f9);
        }
        
        .sidebar-section {
            background: white;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        }
        
        /* Input de chat */
        div[data-testid="stChatInput"] {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-top: 1px solid #e5e7eb;
            padding: 1rem;
        }
        
        div[data-testid="stChatInput"] textarea {
            border-radius: 12px;
            border: 2px solid #e5e7eb;
            transition: all 0.3s;
        }
        
        div[data-testid="stChatInput"] textarea:focus {
            border-color: #8B5CF6;
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.2);
        }
        </style>
        """, unsafe_allow_html=True)
    
    def _show_header(self):
        """Affiche l'en-tête de l'assistant"""
        profile = st.session_state.expert_advisor.get_current_profile()
        profile_name = profile.get('name', 'Assistant IA') if profile else 'Assistant IA'
        
        st.markdown(f"""
        <div class="ia-header">
            <h1>🤖 {html.escape(profile_name)}</h1>
            <p>Intelligence Artificielle intégrée à votre ERP • Analyse de données • Support expert</p>
        </div>
        """, unsafe_allow_html=True)
    
    def _show_sidebar(self):
        """Affiche la barre latérale avec les options"""
        # Nouvelle consultation
        if st.button("✨ Nouvelle Consultation", use_container_width=True, type="primary"):
            self._start_new_consultation()
        
        st.divider()
        
        # Sélection du profil
        st.markdown("### 👤 Profil Expert")
        profile_names = st.session_state.profile_manager.get_profile_names()
        if profile_names:
            current_profile = st.session_state.get("selected_profile_name", profile_names[0])
            selected_profile = st.selectbox(
                "Profil actif:",
                profile_names,
                index=profile_names.index(current_profile) if current_profile in profile_names else 0,
                label_visibility="collapsed"
            )
            
            if selected_profile != st.session_state.get("selected_profile_name"):
                st.session_state.expert_advisor.set_current_profile_by_name(selected_profile)
                st.session_state.selected_profile_name = selected_profile
                self._start_new_consultation()
        
        # Recherche ERP
        st.divider()
        st.markdown("### 🔍 Recherche ERP")
        with st.expander("💡 Aide recherche"):
            st.markdown("""
            **Recherche dans vos données ERP:**
            - Tapez `/erp` suivi de votre recherche
            - Ex: `/erp projets en cours`
            - Ex: `/erp stock acier`
            - Ex: `/erp employés soudure`
            
            **Recherche web:**
            - Tapez `/search` suivi de votre recherche
            - Ex: `/search normes ISO métallurgie`
            """)
        
        # Analyse de fichiers
        st.divider()
        st.markdown("### 📄 Analyse de documents")
        
        uploaded_files = st.file_uploader(
            "Téléverser des fichiers:",
            type=['pdf', 'docx', 'xlsx', 'csv', 'txt', 'jpg', 'png'],
            accept_multiple_files=True,
            key="file_uploader",
            label_visibility="collapsed"
        )
        
        if uploaded_files:
            if st.button("🔍 Analyser", use_container_width=True):
                self._analyze_files(uploaded_files)
        
        # Export
        st.divider()
        st.markdown("### 📥 Export")
        
        if st.button("📄 Générer rapport HTML", use_container_width=True):
            self._generate_html_report()
        
        if st.session_state.get('html_download_data'):
            st.download_button(
                label="⬇️ Télécharger",
                data=st.session_state.html_download_data['data'],
                file_name=st.session_state.html_download_data['filename'],
                mime="text/html",
                use_container_width=True
            )
        
        # Historique
        if st.session_state.conversation_manager:
            st.divider()
            st.markdown("### 🕒 Historique")
            
            conversations = st.session_state.conversation_manager.list_conversations(limit=10)
            if conversations:
                for conv in conversations:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        if st.button(
                            conv['name'][:30] + "..." if len(conv['name']) > 30 else conv['name'],
                            key=f"load_{conv['id']}",
                            use_container_width=True
                        ):
                            self._load_conversation(conv['id'])
                    with col2:
                        if st.button("🗑️", key=f"del_{conv['id']}", help="Supprimer"):
                            self._delete_conversation(conv['id'])
        
        # Statistiques cache
        st.divider()
        st.markdown("### 📊 Performance")
        cache_stats = self.cache_optimizer.get_performance_report()
        st.metric("Taux de cache", f"{cache_stats['cache_hit_rate']*100:.1f}%")
        st.caption(f"Économies: ${cache_stats['total_cost_saved']:.2f}")
    
    def _show_chat_area(self):
        """Affiche la zone de chat principale"""
        # Message d'accueil si nécessaire
        if not st.session_state.messages:
            self._add_welcome_message()
        
        # Afficher tous les messages
        for message in st.session_state.messages:
            role = message.get("role", "assistant")
            content = message.get("content", "")
            
            if role == "system":
                continue
            
            avatar = "👤" if role == "user" else "🤖" if role == "assistant" else "🔎"
            
            with st.chat_message(role, avatar=avatar):
                if message.get("is_analysis"):
                    self._display_analysis_result(content)
                else:
                    st.markdown(content)
    
    def _handle_chat_input(self):
        """Gère l'input de chat et les commandes"""
        prompt = st.chat_input("Posez votre question ou tapez /help pour l'aide...")
        
        if prompt:
            # Ajouter le message utilisateur
            st.session_state.messages.append({
                "role": "user",
                "content": prompt
            })
            
            # Traiter la commande
            if prompt.strip().lower() == "/help":
                self._show_help()
            elif prompt.strip().lower().startswith("/erp "):
                query = prompt[5:].strip()
                self._search_erp(query)
            elif prompt.strip().lower().startswith("/search "):
                query = prompt[8:].strip()
                self._search_web(query)
            else:
                self._get_ai_response(prompt)
            
            # Sauvegarder la conversation
            self._save_current_conversation()
            
            st.rerun()
    
    def _show_footer(self):
        """Affiche le footer"""
        st.markdown("""
        <div style='text-align: center; padding: 2rem; color: #6B7280; border-top: 1px solid #E5E7EB; margin-top: 3rem;'>
            <p>🏭 ERP Production DG Inc. • Assistant IA Expert • Powered by Claude</p>
        </div>
        """, unsafe_allow_html=True)
    
    # =========================================================================
    # MÉTHODES UTILITAIRES
    # =========================================================================
    
    def _start_new_consultation(self):
        """Démarre une nouvelle consultation"""
        st.session_state.messages = []
        st.session_state.current_conversation_id = None
        st.session_state.processed_messages = set()
        self._add_welcome_message()
        st.rerun()
    
    def _add_welcome_message(self):
        """Ajoute le message d'accueil"""
        profile = st.session_state.expert_advisor.get_current_profile()
        profile_content = profile.get('content', '') if profile else ''
        
        welcome = f"""Bonjour! {profile_content}

**Commandes disponibles:**
- `/erp [recherche]` - Rechercher dans vos données ERP
- `/search [recherche]` - Rechercher sur le web
- `/help` - Afficher l'aide

Comment puis-je vous aider aujourd'hui?"""
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": welcome
        })
    
    def _show_help(self):
        """Affiche l'aide détaillée"""
        help_content = """
**🤖 Assistant IA Expert - Aide**

**Recherche dans l'ERP:**
- `/erp projets` - Voir tous les projets
- `/erp projets en cours` - Projets actifs
- `/erp stock [article]` - Rechercher dans l'inventaire
- `/erp employés [compétence]` - Trouver des employés
- `/erp clients [nom]` - Rechercher des clients

**Recherche web:**
- `/search [terme]` - Recherche générale
- `/search normes ISO` - Recherche spécifique

**Analyse de documents:**
- Utilisez le bouton dans la barre latérale
- Formats: PDF, Word, Excel, CSV, Images

**Questions générales:**
- Posez directement vos questions sur la métallurgie
- Demandez des analyses ou des recommandations
- L'IA a accès à vos données ERP

**Export:**
- Générez des rapports HTML de vos conversations
- Exportez pour partage ou archivage
"""
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": help_content
        })
    
    def _search_erp(self, query: str):
        """Effectue une recherche dans l'ERP"""
        with st.spinner(f"Recherche dans l'ERP: '{query}'..."):
            results = self._search_erp_data(query)
            
            # Enrichir avec l'IA
            context = f"Résultats de recherche ERP pour '{query}':\n{results}"
            
            try:
                response = st.session_state.expert_advisor.obtenir_reponse(
                    f"Voici les résultats de recherche dans l'ERP. Présente-les de manière claire et propose des actions si pertinent:\n{context}",
                    []
                )
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })
            except Exception as e:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": results
                })
    
    def _search_web(self, query: str):
        """Effectue une recherche web"""
        try:
            with st.spinner(f"Recherche web: '{query}'..."):
                result = st.session_state.expert_advisor.perform_web_search(query)
                
                st.session_state.messages.append({
                    "role": "search_result",
                    "content": result
                })
        except Exception as e:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Erreur lors de la recherche: {str(e)}"
            })
    
    def _get_ai_response(self, prompt: str):
        """Obtient une réponse de l'IA"""
        with st.spinner("L'expert réfléchit..."):
            try:
                # Ajouter le contexte ERP si disponible
                erp_context = self._get_erp_context()
                
                if erp_context:
                    system_context = f"Contexte ERP actuel:\n{erp_context}\n\nUtilise ces informations si pertinent pour ta réponse."
                    history = [{"role": "system", "content": system_context}] + st.session_state.messages[:-1]
                else:
                    history = st.session_state.messages[:-1]
                
                response = st.session_state.expert_advisor.obtenir_reponse(prompt, history)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })
                
            except Exception as e:
                logger.error(f"Erreur IA: {e}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Désolé, une erreur s'est produite: {str(e)}"
                })
    
    def _analyze_files(self, files):
        """Analyse les fichiers téléversés"""
        with st.spinner("Analyse des documents..."):
            try:
                history = [m for m in st.session_state.messages if m.get("role") != "system"]
                response, details = st.session_state.expert_advisor.analyze_documents(files, history)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "is_analysis": True
                })
                
                st.rerun()
                
            except Exception as e:
                st.error(f"Erreur analyse: {e}")
    
    def _display_analysis_result(self, content: str):
        """Affiche un résultat d'analyse avec style"""
        st.markdown("""
        <div class="analysis-container">
            <h3>🔍 Analyse des documents</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Parser le contenu pour l'affichage structuré
        sections = content.split("**")
        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                title = sections[i].strip(":** ")
                body = sections[i + 1]
                
                st.markdown(f"""
                <div class="analysis-section">
                    <h4>{html.escape(title)}</h4>
                    <div>{markdown.markdown(body)}</div>
                </div>
                """, unsafe_allow_html=True)
    
    def _generate_html_report(self):
        """Génère un rapport HTML de la conversation"""
        if not st.session_state.messages:
            st.warning("Aucune conversation à exporter")
            return
        
        try:
            # Utiliser le générateur HTML de ai_expert_app
            from ai_expert_app import generate_html_report
            
            profile = st.session_state.expert_advisor.get_current_profile()
            profile_name = profile.get('name', 'Expert') if profile else 'Expert'
            
            html_content = generate_html_report(
                st.session_state.messages,
                profile_name,
                st.session_state.current_conversation_id,
                "ERP Production DG Inc."
            )
            
            filename = f"Rapport_IA_ERP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            
            st.session_state.html_download_data = {
                "data": html_content.encode('utf-8'),
                "filename": filename
            }
            
            st.success("Rapport généré avec succès!")
            
        except Exception as e:
            st.error(f"Erreur génération rapport: {e}")
    
    def _save_current_conversation(self):
        """Sauvegarde la conversation actuelle"""
        if st.session_state.conversation_manager and st.session_state.messages:
            try:
                new_id = st.session_state.conversation_manager.save_conversation(
                    st.session_state.current_conversation_id,
                    st.session_state.messages
                )
                if new_id and not st.session_state.current_conversation_id:
                    st.session_state.current_conversation_id = new_id
            except Exception as e:
                logger.error(f"Erreur sauvegarde: {e}")
    
    def _load_conversation(self, conv_id: int):
        """Charge une conversation"""
        if st.session_state.conversation_manager:
            messages = st.session_state.conversation_manager.load_conversation(conv_id)
            if messages:
                st.session_state.messages = messages
                st.session_state.current_conversation_id = conv_id
                st.rerun()
    
    def _delete_conversation(self, conv_id: int):
        """Supprime une conversation"""
        if st.session_state.conversation_manager:
            if st.session_state.conversation_manager.delete_conversation(conv_id):
                if st.session_state.current_conversation_id == conv_id:
                    self._start_new_consultation()
                else:
                    st.rerun()


def show_assistant_ia_page(db=None):
    """
    Fonction principale pour afficher la page de l'assistant IA
    Appelée depuis app.py
    """
    # Initialiser l'assistant si nécessaire
    if 'assistant_ia_expert' not in st.session_state:
        try:
            st.session_state.assistant_ia_expert = AssistantIAExpert(db=db)
        except Exception as e:
            st.error(f"Erreur initialisation Assistant IA: {e}")
            st.stop()
    
    # Afficher la page
    st.session_state.assistant_ia_expert.show_page()