"""
Module d'intégration IA pour l'ERP DG Inc.
Ce module permet d'intégrer le système d'experts IA dans l'ERP principal
"""

import streamlit as st
import sys
import os
import json
from datetime import datetime
from ia_erp_context import ERPContextProvider, create_erp_context_for_ai, enhance_ai_prompt_with_erp

# Ajouter le chemin du module IA au path Python
IA_PATH = os.path.join(os.path.dirname(__file__), 'IA')
if IA_PATH not in sys.path:
    sys.path.insert(0, IA_PATH)

def show_ia_expert_page():
    """
    Affiche la page du module IA Expert dans l'ERP
    """
    # Vérifier d'abord si on peut utiliser le module complet
    try:
        import anthropic
        has_anthropic = True
    except ImportError:
        has_anthropic = False
    
    # Si Anthropic n'est pas disponible, utiliser la version démo
    if not has_anthropic:
        from ia_integration_simple import show_ia_expert_demo
        show_ia_expert_demo()
        return
    
    try:
        # Importer les modules IA
        from expert_logic import ExpertAdvisor, ExpertProfileManager
        from conversation_manager import ConversationManager
        
        # Charger le CSS du module IA
        css_path = os.path.join(IA_PATH, 'style.css')
        if os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        
        # Initialiser les composants IA dans session_state
        if 'ia_profile_manager' not in st.session_state:
            profile_dir = os.path.join(IA_PATH, 'profiles')
            st.session_state.ia_profile_manager = ExpertProfileManager(profile_dir=profile_dir)
        
        if 'ia_conversation_manager' not in st.session_state:
            st.session_state.ia_conversation_manager = ConversationManager()
        
        # Initialiser une conversation si nécessaire
        if 'ia_current_conversation_id' not in st.session_state:
            st.session_state.ia_current_conversation_id = None
        
        if 'ia_messages' not in st.session_state:
            st.session_state.ia_messages = []
        
        # MODIFICATION: Forcer le profil ANALYSTE_ERP uniquement
        if 'ia_expert_advisor' not in st.session_state or 'ia_selected_profile' not in st.session_state:
            st.session_state.ia_selected_profile = 'ANALYSTE_ERP'
            # Obtenir la clé API depuis les secrets ou l'environnement
            api_key = None
            
            # Essayer de charger depuis un fichier .env s'il existe
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                # python-dotenv n'est pas installé, continuer
                pass
            
            # Essayer d'abord les variables d'environnement
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            
            # Si pas trouvé, essayer st.secrets (avec gestion d'erreur)
            if not api_key:
                try:
                    api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
                except Exception:
                    # Si st.secrets n'est pas disponible, continuer
                    pass
            
            if api_key:
                st.session_state.ia_expert_advisor = ExpertAdvisor(api_key)
                st.session_state.ia_expert_advisor.profile_manager = st.session_state.ia_profile_manager
            else:
                st.error("🔑 Clé API Anthropic non configurée.")
                st.info("""
                **Pour configurer la clé API, choisissez une option :**
                
                1. **Variable d'environnement** (recommandé) :
                   ```bash
                   export ANTHROPIC_API_KEY="votre-clé-api"
                   ```
                
                2. **Fichier .streamlit/secrets.toml** :
                   ```toml
                   ANTHROPIC_API_KEY = "votre-clé-api"
                   ```
                
                3. **Fichier .env** à la racine :
                   ```
                   ANTHROPIC_API_KEY=votre-clé-api
                   ```
                """)
                
                # Proposer d'utiliser le mode démo
                if st.button("🎮 Utiliser le mode démonstration", key="use_demo_mode"):
                    from ia_integration_simple import show_ia_expert_demo
                    show_ia_expert_demo()
                return
        
        # Titre et description
        st.markdown("# 📊 Analyste ERP Intelligent")
        st.markdown("### Analyse de données et optimisation de votre système de production")
        
        # Afficher des exemples de questions si connecté à l'ERP
        if 'erp_db' in st.session_state:
            with st.expander("💡 Exemples de questions avec données ERP"):
                st.markdown("""
                **Projets et Production:**
                - "Quel est le statut du projet AutoTech?"
                - "Montre-moi les projets en cours"
                - "Quelle est la charge de production actuelle?"
                
                **Devis et Clients:**
                - "Affiche les derniers devis créés"
                - "Quelles sont les informations sur le client BâtiTech?"
                - "Quel est le taux de conversion des devis?"
                
                **Inventaire:**
                - "Quel est le niveau de stock actuel?"
                - "Y a-t-il des articles en rupture?"
                - "Montre-moi l'inventaire des poutres"
                
                **Analyse et Conseils:**
                - "Analyse la rentabilité des projets récents"
                - "Quels clients sont les plus actifs?"
                - "Recommande des optimisations de production"
                """)
        else:
            st.info("💡 Connectez-vous à l'ERP pour accéder aux données en temps réel")
        
        # Sidebar pour la sélection du profil
        with st.sidebar:
            st.markdown("### 📊 Analyste ERP")
            
            # MODIFICATION: Utiliser uniquement le profil ANALYSTE_ERP
            selected_profile_id = 'ANALYSTE_ERP'
            profiles = st.session_state.ia_profile_manager.get_all_profiles()
            profile_names = {pid: profile['name'] for pid, profile in profiles.items()}
            
            # Afficher la description du profil ANALYSTE_ERP
            if selected_profile_id in profiles:
                profile = profiles.get(selected_profile_id, {})
                st.markdown("#### 📋 Expert en analyse de données")
                st.info("Analyste ERP spécialisé dans l'optimisation des systèmes de gestion pour l'industrie métallurgique. Expert en analyse de rentabilité, optimisation de production et recommandations basées sur les données réelles de l'ERP.")
                
                # Définir le profil ANALYSTE_ERP dans l'expert advisor
                if 'ia_expert_advisor' in st.session_state:
                    st.session_state.ia_expert_advisor.set_current_profile_by_name(profile.get('name', 'ANALYSTE_ERP'))
            
            # Bouton pour réinitialiser la conversation
            if st.button("🔄 Nouvelle Conversation", key="ia_new_conversation"):
                st.session_state.ia_messages = []
                st.session_state.ia_current_conversation_id = None
                st.rerun()
        
        # Zone principale de chat
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Historique de la conversation
            messages = st.session_state.ia_messages
            
            # Conteneur pour l'historique
            chat_container = st.container()
            
            with chat_container:
                for msg in messages:
                    if msg['role'] == 'user':
                        st.markdown(f"""
                        <div class="message user-message">
                            <div class="message-header">👤 Vous</div>
                            <div class="message-content">{msg['content']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="message assistant-message">
                            <div class="message-header">📊 Analyste ERP</div>
                            <div class="message-content">{msg['content']}</div>
                        </div>
                        """, unsafe_allow_html=True)
            
            # Zone de saisie
            user_input = st.text_area(
                "Posez votre question à l'expert",
                key="ia_user_input",
                height=100,
                placeholder="Tapez votre message ici..."
            )
            
            col_send, col_upload = st.columns([1, 1])
            
            with col_send:
                send_button = st.button("📤 Envoyer", key="ia_send", use_container_width=True)
            
            with col_upload:
                uploaded_file = st.file_uploader(
                    "📎 Joindre un fichier",
                    key="ia_file_upload",
                    label_visibility="collapsed"
                )
            
            # Traitement de l'envoi
            if send_button and (user_input or uploaded_file):
                with st.spinner("🤔 L'expert réfléchit..."):
                    try:
                        # Cas 1: Analyse de fichier
                        if uploaded_file:
                            # Ajouter le message utilisateur
                            user_msg = user_input if user_input else f"Analyse du fichier {uploaded_file.name}"
                            st.session_state.ia_messages.append({
                                'role': 'user',
                                'content': user_msg
                            })
                            
                            # Analyser le fichier
                            response_text, analysis_details = st.session_state.ia_expert_advisor.analyze_documents(
                                [uploaded_file],
                                st.session_state.ia_messages[-6:-1]  # Historique sans le dernier message
                            )
                            
                            # Formater la réponse
                            response = f"📄 **Analyse de {uploaded_file.name}**\n\n{response_text}"
                            
                        # Cas 2: Question simple
                        else:
                            # Ajouter le message utilisateur
                            st.session_state.ia_messages.append({
                                'role': 'user',
                                'content': user_input
                            })
                            
                            # Enrichir le contexte avec les données ERP si disponible
                            enriched_messages = st.session_state.ia_messages[:-1].copy()
                            
                            # TOUJOURS créer le provider et le contexte ERP
                            provider = ERPContextProvider()
                            
                            # TOUJOURS ajouter le contexte ERP en début
                            erp_context = create_erp_context_for_ai()
                            
                            # Vérifier si le contexte n'est pas déjà présent
                            has_erp_context = any(
                                msg.get('role') == 'system' and 'Contexte ERP' in msg.get('content', '')
                                for msg in enriched_messages[:3]  # Vérifier les 3 premiers messages
                            )
                            
                            if not has_erp_context:
                                enriched_messages.insert(0, {
                                    'role': 'system',
                                    'content': erp_context
                                })
                            
                            # Analyser la requête pour enrichir avec des données spécifiques
                            if not provider.demo_mode:
                                
                                # Détection automatique des besoins de données
                                query_lower = user_input.lower()
                                additional_context = []
                                
                                # Recherche automatique selon le contexte
                                if 'projet' in query_lower or 'project' in query_lower or 'combien' in query_lower:
                                    # Récupérer TOUS les projets pour les questions de comptage
                                    all_projects = provider.search_projects(limit=100)
                                    if all_projects.get('success'):
                                        # Compter par statut
                                        projects_by_status = {}
                                        for p in all_projects.get('projects', []):
                                            status = p.get('statut', 'INCONNU')
                                            projects_by_status[status] = projects_by_status.get(status, 0) + 1
                                        
                                        content = f"Données projets ERP:\n"
                                        content += f"Total projets: {all_projects.get('count', 0)}\n"
                                        content += f"Par statut:\n"
                                        for status, count in projects_by_status.items():
                                            content += f"  - {status}: {count} projet(s)\n"
                                        
                                        # Ajouter quelques projets récents
                                        content += "\nProjets récents:\n"
                                        for p in all_projects.get('projects', [])[:3]:
                                            content += f"  - {p.get('nom_projet', 'N/A')} ({p.get('statut', 'N/A')}) - Client: {p.get('client_name', 'N/A')}\n"
                                        
                                        additional_context.append({
                                            'role': 'system',
                                            'content': content
                                        })
                                
                                if 'devis' in query_lower or 'estimation' in query_lower:
                                    devis = provider.search_devis(limit=3)
                                    if devis.get('success'):
                                        additional_context.append({
                                            'role': 'system',
                                            'content': f"Données devis ERP:\n{provider.format_for_ai(devis)}"
                                        })
                                
                                if 'client' in query_lower:
                                    # Essayer d'extraire un nom de client
                                    words = user_input.split()
                                    for word in words:
                                        if word.istitle() and len(word) > 3:
                                            client_info = provider.get_client_info(client_name=word)
                                            if client_info.get('success'):
                                                additional_context.append({
                                                    'role': 'system',
                                                    'content': f"Données client ERP:\n{provider.format_for_ai(client_info)}"
                                                })
                                                break
                                
                                if 'stock' in query_lower or 'inventaire' in query_lower:
                                    inventory = provider.get_inventory_status(limit=5)
                                    if inventory.get('success'):
                                        additional_context.append({
                                            'role': 'system',
                                            'content': f"Données inventaire ERP:\n{provider.format_for_ai(inventory)}"
                                        })
                                
                                # Ajouter le contexte additionnel
                                enriched_messages.extend(additional_context)
                            
                            # Obtenir la réponse
                            response = st.session_state.ia_expert_advisor.obtenir_reponse(
                                user_input,
                                enriched_messages
                            )
                        
                        # Ajouter la réponse
                        st.session_state.ia_messages.append({
                            'role': 'assistant',
                            'content': response
                        })
                        
                        # Sauvegarder la conversation
                        if st.session_state.ia_messages:
                            st.session_state.ia_current_conversation_id = st.session_state.ia_conversation_manager.save_conversation(
                                st.session_state.ia_current_conversation_id,
                                st.session_state.ia_messages,
                                name=f"Consultation {profile_names.get(selected_profile_id, 'Expert')}"
                            )
                        
                        # Rafraîchir la page
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Erreur: {str(e)}")
        
        with col2:
            # Statistiques et options
            st.markdown("### 📊 Statistiques")
            total_messages = len(messages)
            st.metric("Messages", total_messages)
            
            # Indicateur d'intégration ERP
            st.markdown("### 🔗 Intégration ERP")
            
            # TOUJOURS créer le provider pour vérifier la connexion
            provider = ERPContextProvider()
            
            if not provider.demo_mode:
                st.success("✅ Connecté à l'ERP")
                
                # Afficher les modules accessibles
                modules = provider._get_available_modules()
                if modules:
                    st.info(f"Modules accessibles: {', '.join(modules)}")
                else:
                    st.warning("Aucun module ERP accessible")
                
                # Recherche rapide
                with st.expander("🔍 Recherche rapide ERP"):
                    search_type = st.selectbox(
                        "Type de recherche",
                        ["Projets", "Devis", "Clients", "Inventaire"],
                        key="ia_erp_search_type"
                    )
                    
                    search_query = st.text_input(
                        "Rechercher...",
                        key="ia_erp_search_query"
                    )
                    
                    if st.button("🔎 Rechercher", key="ia_erp_search_btn"):
                        if search_query:
                            if search_type == "Projets":
                                results = provider.search_projects(query=search_query, limit=3)
                            elif search_type == "Devis":
                                results = provider.search_devis(query=search_query, limit=3)
                            elif search_type == "Clients":
                                results = provider.get_client_info(client_name=search_query)
                            else:  # Inventaire
                                results = provider.get_inventory_status(item_name=search_query)
                            
                            if results.get('success'):
                                # Ajouter à la conversation
                                search_msg = f"Recherche {search_type}: {search_query}"
                                st.session_state.ia_messages.append({
                                    'role': 'user',
                                    'content': search_msg
                                })
                                
                                response_msg = f"Résultats de recherche {search_type}:\n{provider.format_for_ai(results)}"
                                st.session_state.ia_messages.append({
                                    'role': 'assistant',
                                    'content': response_msg
                                })
                                
                                st.rerun()
            else:
                st.warning("⚠️ Mode démo - Base de données non trouvée")
            
            # Historique des conversations
            st.markdown("### 📚 Historique")
            try:
                conversations = st.session_state.ia_conversation_manager.list_conversations(limit=5)
                if conversations:
                    for conv in conversations:
                        if st.button(f"📝 {conv['name'][:20]}...", key=f"load_conv_{conv['id']}"):
                            # Charger la conversation
                            loaded_conv = st.session_state.ia_conversation_manager.load_conversation(conv['id'])
                            if loaded_conv:
                                st.session_state.ia_messages = loaded_conv['messages']
                                st.session_state.ia_current_conversation_id = conv['id']
                                st.rerun()
                else:
                    st.info("Aucune conversation sauvegardée")
            except Exception as e:
                st.caption("Historique non disponible")
            
            # Export de la conversation
            if st.button("💾 Exporter", key="ia_export"):
                export_data = {
                    "expert": profile_names.get(selected_profile_id, "Expert"),
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "messages": messages,
                    "conversation_id": st.session_state.ia_current_conversation_id
                }
                st.download_button(
                    "📥 Télécharger JSON",
                    data=json.dumps(export_data, indent=2, ensure_ascii=False),
                    file_name=f"conversation_ia_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                    mime="application/json"
                )
    
    except ImportError as e:
        st.error(f"❌ Erreur d'importation du module IA: {e}")
        st.info("Vérifiez que tous les fichiers du module IA sont présents dans le dossier 'IA'")
    except Exception as e:
        st.error(f"❌ Erreur inattendue: {e}")
        if st.checkbox("Afficher les détails de débogage"):
            st.exception(e)

def check_ia_dependencies():
    """
    Vérifie que toutes les dépendances du module IA sont installées
    """
    missing_deps = []
    optional_deps = []
    
    # Dépendances critiques (obligatoires)
    critical_packages = {
        'anthropic': 'anthropic'
    }
    
    # Dépendances optionnelles (pour les fonctionnalités avancées)
    optional_packages = {
        'PyPDF2': 'PyPDF2',
        'python-docx': 'docx',
        'pillow': 'PIL',
        'beautifulsoup4': 'bs4',
        'python-dotenv': 'dotenv'
    }
    
    # Vérifier les dépendances critiques
    for package_name, import_name in critical_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_deps.append(package_name)
    
    # Vérifier les dépendances optionnelles
    for package_name, import_name in optional_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            optional_deps.append(package_name)
    
    # Si des dépendances critiques manquent, on ne peut pas continuer
    if missing_deps:
        st.error(f"❌ Dépendances critiques manquantes: {', '.join(missing_deps)}")
        st.info("Installez-les avec: pip install " + " ".join(missing_deps))
        return False
    
    # Si des dépendances optionnelles manquent, on affiche juste un avertissement
    if optional_deps:
        st.warning(f"⚠️ Fonctionnalités limitées - Dépendances optionnelles manquantes: {', '.join(optional_deps)}")
        with st.expander("ℹ️ Pour activer toutes les fonctionnalités"):
            st.info(f"Installez avec: pip install {' '.join(optional_deps)}")
            st.markdown("""
            **Fonctionnalités affectées:**
            - PyPDF2: Lecture de fichiers PDF
            - python-docx: Lecture de fichiers Word
            - pillow: Traitement d'images
            - beautifulsoup4: Analyse HTML
            - python-dotenv: Chargement de variables d'environnement
            """)
    
    return True

# Styles CSS additionnels pour l'intégration
def apply_ia_integration_styles():
    """
    Applique des styles CSS spécifiques pour l'intégration IA
    """
    st.markdown("""
    <style>
    /* Styles pour les messages de chat */
    .message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        animation: fadeIn 0.3s ease-in;
    }
    
    .user-message {
        background: linear-gradient(135deg, rgba(0, 169, 113, 0.1), rgba(0, 169, 113, 0.05));
        border-left: 4px solid #00A971;
        margin-left: 2rem;
    }
    
    .assistant-message {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(59, 130, 246, 0.05));
        border-left: 4px solid #3B82F6;
        margin-right: 2rem;
    }
    
    .message-header {
        font-weight: bold;
        margin-bottom: 0.5rem;
        color: #1F2937;
    }
    
    .message-content {
        color: #4B5563;
        line-height: 1.6;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Styles pour le sélecteur d'expert */
    .stSelectbox > div > div {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 169, 113, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)