"""
Module d'intégration IA simplifié pour l'ERP DG Inc.
Version sans dépendances externes pour démonstration
"""

import streamlit as st
import json
from datetime import datetime

def show_ia_expert_demo():
    """
    Affiche une version de démonstration du module IA sans dépendances externes
    """
    # Titre et description
    st.markdown("# 🤖 Assistant Expert IA - Mode Démonstration")
    st.info("⚠️ Mode démonstration - Pour activer le module complet, installez: `pip install anthropic`")
    
    # Sidebar pour la sélection du profil
    with st.sidebar:
        st.markdown("### 👤 Experts Disponibles")
        
        experts = {
            "erp": "Expert ERP - Spécialiste des systèmes de gestion",
            "controle_qualite": "Expert Contrôle Qualité - Normes et procédures",
            "estimateur": "Expert Estimateur - Calcul de coûts et devis",
            "ingenieur": "Ingénieur Métallurgie - Procédés et matériaux",
            "programmeur_cnc": "Programmeur CNC - Usinage et fabrication"
        }
        
        selected_expert = st.selectbox(
            "Choisir un expert",
            options=list(experts.keys()),
            format_func=lambda x: experts[x].split(" - ")[0],
            key="ia_demo_expert"
        )
        
        st.markdown("#### 📋 Description")
        st.info(experts[selected_expert])
        
        if st.button("🔄 Réinitialiser", key="ia_demo_reset"):
            if 'ia_demo_messages' in st.session_state:
                del st.session_state.ia_demo_messages
            st.rerun()
    
    # Initialiser l'historique des messages
    if 'ia_demo_messages' not in st.session_state:
        st.session_state.ia_demo_messages = []
    
    # Zone principale
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Afficher l'historique
        chat_container = st.container()
        
        with chat_container:
            for msg in st.session_state.ia_demo_messages:
                if msg['role'] == 'user':
                    st.markdown(f"""
                    <div style="background-color: #E8F5E9; padding: 10px; border-radius: 10px; margin: 5px 0; margin-left: 20%;">
                        <strong>👤 Vous:</strong><br>{msg['content']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background-color: #E3F2FD; padding: 10px; border-radius: 10px; margin: 5px 0; margin-right: 20%;">
                        <strong>🤖 {experts[selected_expert].split(' - ')[0]}:</strong><br>{msg['content']}
                    </div>
                    """, unsafe_allow_html=True)
        
        # Zone de saisie
        user_input = st.text_area(
            "Posez votre question à l'expert",
            key="ia_demo_input",
            height=100,
            placeholder="Tapez votre message ici..."
        )
        
        if st.button("📤 Envoyer", key="ia_demo_send", use_container_width=True):
            if user_input:
                # Ajouter le message utilisateur
                st.session_state.ia_demo_messages.append({
                    'role': 'user',
                    'content': user_input
                })
                
                # Générer une réponse de démonstration
                demo_responses = {
                    "erp": [
                        "Pour optimiser votre flux de production dans l'ERP, je recommande d'utiliser la vue Kanban pour visualiser l'état de vos projets en temps réel.",
                        "Les bons de travail sont essentiels pour tracer vos opérations. Créez-les depuis le module Production pour un suivi optimal.",
                        "Le module TimeTracker vous permet de suivre précisément le temps passé sur chaque opération, améliorant ainsi vos estimations futures."
                    ],
                    "controle_qualite": [
                        "Pour assurer la conformité ISO 9001, documentez chaque étape de votre processus de production dans l'ERP.",
                        "Je recommande d'implémenter des points de contrôle à chaque changement de poste de travail.",
                        "La traçabilité est cruciale : utilisez les numéros de lot dans votre gestion d'inventaire."
                    ],
                    "estimateur": [
                        "Pour un devis précis, considérez : matériaux (40%), main d'œuvre (35%), frais généraux (15%), et marge (10%).",
                        "N'oubliez pas d'inclure les temps de setup machine dans vos estimations de production.",
                        "Le module Devis de l'ERP calcule automatiquement la TVA québécoise à 14.975%."
                    ],
                    "ingenieur": [
                        "Pour l'acier inoxydable 316L, utilisez une vitesse de coupe de 80-120 m/min en tournage.",
                        "Le traitement thermique T6 pour l'aluminium 6061 améliore significativement ses propriétés mécaniques.",
                        "Pour le soudage MIG de l'acier, un mélange 75% Ar / 25% CO2 offre un bon compromis pénétration/aspect."
                    ],
                    "programmeur_cnc": [
                        "Pour optimiser vos parcours d'outil, utilisez des stratégies de fraisage adaptatif pour réduire l'usure.",
                        "Les vitesses d'avance peuvent être augmentées de 20-30% avec des outils carbure modernes.",
                        "Pensez à utiliser G54-G59 pour gérer efficacement vos origines pièce multiples."
                    ]
                }
                
                # Sélectionner une réponse
                import random
                responses = demo_responses.get(selected_expert, ["Je suis là pour vous aider avec vos questions."])
                response = random.choice(responses)
                
                # Ajouter la réponse
                st.session_state.ia_demo_messages.append({
                    'role': 'assistant',
                    'content': response
                })
                
                # Rafraîchir
                st.rerun()
    
    with col2:
        # Informations et statistiques
        st.markdown("### 📊 Informations")
        st.metric("Messages", len(st.session_state.ia_demo_messages))
        st.metric("Expert actuel", experts[selected_expert].split(" - ")[0])
        
        st.markdown("### 🚀 Version Complète")
        st.markdown("""
        Pour accéder à la version complète avec:
        - IA Claude d'Anthropic
        - Support de fichiers PDF/Word
        - Analyse d'images
        - Conversations contextuelles
        
        **Installez:**
        ```bash
        pip install anthropic
        ```
        """)
        
        # Export démo
        if st.button("💾 Exporter Démo", key="ia_demo_export"):
            export_data = {
                "mode": "demo",
                "expert": selected_expert,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "messages": st.session_state.ia_demo_messages
            }
            st.download_button(
                "📥 Télécharger JSON",
                data=json.dumps(export_data, indent=2, ensure_ascii=False),
                file_name=f"conversation_demo_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )