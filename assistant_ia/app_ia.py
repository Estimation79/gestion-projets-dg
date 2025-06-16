# app.py
import streamlit as st
import os
import io
import html
import markdown
import json
import base64
from datetime import datetime
from dotenv import load_dotenv

# Importer les classes logiques et le gestionnaire de conversation
try:
   from expert_logic import ExpertAdvisor, ExpertProfileManager
   from conversation_manager import ConversationManager
except ImportError as e:
   st.error(f"Erreur d'importation des modules locaux: {e}")
   st.error("Assurez-vous que les fichiers 'expert_logic.py' et 'conversation_manager.py' existent dans le même dossier.")
   st.stop()


# --- Fonction pour charger le CSS local (utilisée avant et après login) ---
def local_css(file_name):
   """Charge les styles CSS depuis un fichier local."""
   try:
       css_path = os.path.join(os.path.dirname(__file__), file_name)
       with open(css_path, "r", encoding="utf-8") as f:
           st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
   except FileNotFoundError:
       st.warning(f"Fichier CSS '{file_name}' non trouvé dans {os.path.dirname(__file__)}.")
   except Exception as e:
       st.error(f"Erreur lors du chargement du CSS '{file_name}': {e}")

# --- Helper Function pour lire le CSS pour l'intégration HTML (utilisée plus tard) ---
@st.cache_data
def load_css_content(file_name):
   """Charge le contenu brut d'un fichier CSS."""
   try:
       css_path = os.path.join(os.path.dirname(__file__), file_name)
       with open(css_path, "r", encoding="utf-8") as f:
           return f.read()
   except FileNotFoundError:
       st.warning(f"Fichier CSS '{file_name}' non trouvé pour l'intégration HTML.")
       return "/* CSS non trouvé */"
   except Exception as e:
       st.error(f"Erreur lors de la lecture du CSS '{file_name}' pour l'intégration : {e}")
       return f"/* Erreur lecture CSS: {e} */"

# --- Fonction helper pour convertir image en base64 ---
def get_image_base64(image_path):
   """Convertit une image en base64 pour l'incorporation HTML."""
   # base64 est déjà importé en haut du fichier
   try:
       with open(image_path, "rb") as img_file:
           return base64.b64encode(img_file.read()).decode()
   except Exception as e:
       st.error(f"Erreur lors de la lecture de l'image: {e}")
       return ""

# --- Fonction pour détecter si on est sur mobile ---
def is_mobile_device():
   """Estimation si l'appareil est mobile basée sur la largeur de viewport."""
   if 'is_mobile' not in st.session_state:
       st.session_state.is_mobile = False

   st.markdown("""
   <script>
   const checkIfMobile = function() {
       const isMobile = window.innerWidth < 768;
       localStorage.setItem('streamlit_is_mobile', isMobile);
       return isMobile;
   };
   checkIfMobile();
   window.addEventListener('resize', checkIfMobile);
   window.addEventListener('message', function(event) {
       if (event.data.type === 'streamlit:render') {
           setTimeout(function() {
               const buttons = document.querySelectorAll('button[data-baseweb="button"]');
               if (buttons.length > 0) {
                   buttons.forEach(function(button) {
                       button.setAttribute('data-is-mobile', checkIfMobile());
                   });
               }
           }, 500);
       }
   });
   </script>
   """, unsafe_allow_html=True)
   return st.session_state.is_mobile

# --- Fonction pour adapter la mise en page en fonction de la détection mobile ---
def adapt_layout_for_mobile(is_mobile):
   """Adapte la mise en page en fonction de la détection mobile."""
   if is_mobile:
       st.markdown("""
       <style>
       .block-container {
           padding-left: 1rem !important;
           padding-right: 1rem !important;
           max-width: 100% !important;
       }
       div.stButton > button {
           min-height: 44px !important;
           font-size: 16px !important;
           width: 100% !important;
       }
       div.stChatMessage {
           padding: 12px !important;
           margin-bottom: 12px !important;
       }
       .main-header {
           padding: 15px !important;
           margin-bottom: 15px !important;
       }
       [data-testid="stSidebar"][aria-expanded="true"] {
           width: 85vw !important;
       }
       </style>
       """, unsafe_allow_html=True)
   else:
       pass

# --- Fonction pour afficher le résultat d'analyse avec un style amélioré ---
def display_analysis_result(analysis_response, analysis_details):
   """Affiche le résultat d'analyse avec un style amélioré."""
   st.markdown("""
   <style>
   .analysis-container {
       animation: fadeIn 0.6s ease-out;
       background: linear-gradient(to right, #f0f7ff, #e6f3ff);
       border-radius: 12px;
       padding: 20px;
       box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
       margin-bottom: 25px;
       border-left: 5px solid #3B82F6;
   }
   .analysis-header {
       display: flex;
       align-items: center;
       margin-bottom: 15px;
       color: #1e40af;
   }
   .analysis-header h2 {
       margin: 0;
       font-size: 22px;
       font-weight: 600;
   }
   .analysis-header h2::before {
       content: "🔍 ";
       margin-right: 8px;
   }
   .analysis-section {
       background-color: white;
       border-radius: 8px;
       padding: 15px;
       margin-bottom: 15px;
       box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
       border-left: 3px solid #60A5FA;
   }
   .analysis-section h3 {
       color: #3B82F6;
       font-size: 18px;
       margin-top: 0;
       margin-bottom: 10px;
   }
   </style>
   <div class="analysis-container">
       <div class="analysis-header">
           <h2>Analyse des documents</h2>
       </div>
   """, unsafe_allow_html=True)

   content = analysis_response
   sections = content.split("**")

   for i in range(1, len(sections), 2):
       if i + 1 < len(sections):
           section_title = sections[i].strip(":** ")
           section_content = sections[i+1]
           st.markdown(f"""
           <div class="analysis-section">
               <h3>{html.escape(section_title)}</h3>
               <div>{markdown.markdown(section_content)}</div>
           </div>
           """, unsafe_allow_html=True)
   st.markdown("</div>", unsafe_allow_html=True)

# --- Fonction de vérification du mot de passe ET affichage page d'accueil/login ---
def display_login_or_app():
   """
   Affiche la page d'accueil statique et le formulaire de connexion si non connecté.
   Retourne True si l'utilisateur EST connecté, False sinon.
   """
   if "logged_in" not in st.session_state:
       st.session_state.logged_in = False

   if st.session_state.logged_in:
       return True

   st.set_page_config(
       page_title="Connexion - Desmarais & Gagné",
       page_icon="🏗️",
       layout="wide",
       initial_sidebar_state="collapsed"
   )
   local_css("style.css")

   _ , center_col, _ = st.columns([0.5, 3, 0.5], gap="large")

   with center_col:
       try:
           logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
           if os.path.exists(logo_path):
               st.markdown(
                   f"""
                   <div style='display: flex; justify-content: center; align-items: center; width: 100%;'>
                       <img src='data:image/png;base64,{get_image_base64(logo_path)}' style='width: 200px; height: auto;'>
                   </div>
                   """,
                   unsafe_allow_html=True
               )
           else:
               st.warning("Logo 'assets/logo.png' non trouvé.")
       except Exception as e:
           st.error(f"Erreur logo: {e}")

       st.markdown("<br>", unsafe_allow_html=True)
       st.markdown("""
           <div class="main-header">
               <h1>🏗️ Desmarais & Gagné</h1>
               <p>La plateforme intelligente qui révolutionne vos projets de fabrication métallique.</p>
           </div>
       """, unsafe_allow_html=True)

       st.markdown("""
           <h2 style="text-align: center; margin-bottom: 20px;">Nos Solutions Clés</h2>
           <div class="solutions-container">
               <div class="solution-card">
                   <h3>🔧 Fabrication métallique</h3>
                   <p>Solutions complètes et de qualité pour tous besoins en poinçonnage, coupage, découpage à froid et pliage hydraulique.</p>
               </div>
               <div class="solution-card">
                   <h3>🔥 Expertise en soudure</h3>
                   <p>Soudure MIG, TIG, par points et robotisée sur acier, aluminium et autres matériaux soudables.</p>
               </div>
               <div class="solution-card">
                   <h3>🚚 Diables DG-600</h3>
                   <p>Diables en aluminium ultralégers et robustes avec accessoires pour diverses applications.</p>
               </div>
               <div class="solution-card">
                   <h3>🏗️ Environnements contrôlés</h3>
                   <p>Conception et fabrication de cabines insonorisées et bâtiments modulaires préfabriqués.</p>
               </div>
           </div>
       """, unsafe_allow_html=True)

       st.divider()
       st.markdown("<h2 style='text-align: center;'>Notre mission</h2>", unsafe_allow_html=True)
       st.markdown("<h3 style='text-align: center; font-weight: normal;'>Excellence en fabrication métallique depuis quatre décennies</h3>", unsafe_allow_html=True)
       st.markdown("<p style='text-align: center; color: var(--text-color-light);'>Notre objectif est de fournir des solutions complètes de qualité pour tous vos besoins en fabrication métallique</p>", unsafe_allow_html=True)
       st.markdown(" ")
       col1, col2, col3 = st.columns(3)
       with col1:
           st.markdown("""
           <div class="info-card" style="--delay: 1">
               <h4>⚡ Expertise métallique</h4>
               <p>Utilisation de l'Intelligence Artificielle pour fournir une expertise en fabrication métallique, poinçonnage, coupage et assemblage.</p>
           </div>
           """, unsafe_allow_html=True)
       with col2:
           st.markdown("""
           <div class="info-card" style="--delay: 2">
               <h4>📄 Solutions personnalisées</h4>
               <p>Une équipe passionnée avec plus de 40 ans d'expérience dans le secteur de la fabrication métallique.</p>
           </div>
           """, unsafe_allow_html=True)
       with col3:
           st.markdown("""
           <div class="info-card" style="--delay: 3">
               <h4>🛡️ Qualité supérieure</h4>
               <p>Conformité stricte aux normes de qualité et certifications (ISO 9001, CWB et soudure robotisée).</p>
           </div>
           """, unsafe_allow_html=True)
       st.markdown(" ")

       st.divider()
       st.markdown("<p style='text-align: center; text-transform: uppercase; color: var(--text-color-light);'>Fonctionnalités Détaillées</p>", unsafe_allow_html=True)
       st.markdown("<h2 style='text-align: center;'>La plateforme intelligente pour la fabrication métallique</h2>", unsafe_allow_html=True)
       st.markdown("<p style='text-align: center; color: var(--text-color-light);'>Gagnez du temps et optimisez vos projets grâce à notre IA conçue pour la fabrication métallique. Une plateforme complète pour vous assister dans vos besoins.</p>", unsafe_allow_html=True)
       st.markdown(" ")
       fcol1, fcol2, fcol3 = st.columns(3)
       with fcol1:
           st.markdown("""
           <div class="info-card" style="--delay: 1">
               <h4>🧑‍🤝‍🧑 Espaces de travail collaboratif</h4>
               <p>Collaborez efficacement avec vos équipes, partagez et gérez vos informations en un seul endroit.</p>
           </div>
           """, unsafe_allow_html=True)
       with fcol2:
           st.markdown("""
           <div class="info-card" style="--delay: 2">
               <h4>💡 AI Assistance</h4>
               <p>Obtenez des informations techniques en quelques secondes sur la base de notre expertise interne.</p>
           </div>
           """, unsafe_allow_html=True)
       with fcol3:
           st.markdown("""
           <div class="info-card" style="--delay: 3">
               <h4>💬 Assistant spécialisé</h4>
               <p>Un assistant IA spécialisé en fabrication métallique répondant à vos questions techniques en temps réel.</p>
           </div>
           """, unsafe_allow_html=True)
       st.markdown(" ")
       fcol4, fcol5, fcol6 = st.columns(3)
       with fcol4:
           st.markdown("""
           <div class="info-card" style="--delay: 4">
               <h4>✅ Conformité aux normes</h4>
               <p>Assurez la conformité de vos projets aux normes de qualité grâce à notre vérification automatique.</p>
           </div>
           """, unsafe_allow_html=True)
       with fcol5:
           st.markdown("""
           <div class="info-card" style="--delay: 5">
               <h4>📖 Documentation technique</h4>
               <p>Base de connaissances complète sur nos produits et services de fabrication métallique.</p>
           </div>
           """, unsafe_allow_html=True)
       with fcol6:
           st.markdown("""
           <div class="info-card" style="--delay: 6">
               <h4>💰 Analyse technique</h4>
               <p>Outils d'analyse et d'optimisation des processus basés sur notre expertise en fabrication métallique.</p>
           </div>
           """, unsafe_allow_html=True)
       st.markdown(" ")
       fcol7, fcol8, fcol9 = st.columns(3)
       with fcol7:
           st.markdown("""
           <div class="info-card" style="--delay: 7">
               <h4>⏱️ Réponses rapides</h4>
               <p>Obtenez des informations précises et rapides pour mieux planifier vos projets de fabrication.</p>
           </div>
           """, unsafe_allow_html=True)
       with fcol8:
           st.markdown("""
           <div class="info-card" style="--delay: 8">
               <h4>📄 Exportation facile</h4>
               <p>Exportez vos conversations au format PDF en un seul clic.</p>
           </div>
           """, unsafe_allow_html=True)
       with fcol9:
           st.markdown("""
           <div class="info-card" style="--delay: 9">
               <h4>📈 Analyse</h4>
               <p>Analysez vos documents et plans techniques (fichiers PDF, DOCX, CSV et images).</p>
           </div>
           """, unsafe_allow_html=True)

       st.divider()
       st.markdown("<h2 style='text-align: center;'>Certifications et expertise</h2>", unsafe_allow_html=True)
       st.markdown("<p style='text-align: center; color: var(--text-color-light);'>Desmarais & Gagné se conforme aux principales certifications du secteur de la fabrication métallique</p>", unsafe_allow_html=True)
       st.markdown(" ")

       reg_col1, reg_col2 = st.columns(2, gap="medium")
       with reg_col1:
           with st.container():
               st.markdown("""
                <div class="info-card" style="--delay: 1">
                   <p style='text-align: center; font-weight: 500;'>🏢 Certification ISO 9001</p>
                </div>
                """, unsafe_allow_html=True)
       with reg_col2:
           with st.container():
               st.markdown("""
                <div class="info-card" style="--delay: 2">
                   <p style='text-align: center; font-weight: 500;'>🏢 Certification CWB</p>
                </div>
                """, unsafe_allow_html=True)

       st.markdown(" ")
       reg_col3, reg_col4 = st.columns(2, gap="medium")
       with reg_col3:
           with st.container():
               st.markdown("""
                <div class="info-card" style="--delay: 3">
                   <p style='text-align: center; font-weight: 500;'>🏢 Certification Soudure Robotisée</p>
                </div>
                """, unsafe_allow_html=True)
       with reg_col4:
           with st.container():
               st.markdown("""
                <div class="info-card" style="--delay: 4">
                   <p style='text-align: center; font-weight: 500;'>📄 Expertise en fabrication sur mesure</p>
                </div>
                """, unsafe_allow_html=True)

       st.markdown(" ")
       st.divider()
       st.markdown("<h2 style='text-align: center;'>Contactez-nous</h2>", unsafe_allow_html=True)
       st.markdown("<p style='text-align: center; color: var(--text-color-light);'>N'hésitez pas à nous contacter pour toute question ou information supplémentaire.</p>", unsafe_allow_html=True)
       st.markdown("<p style='text-align: center;'>Pour plus d'informations, n'hésitez pas à nous contacter</p>", unsafe_allow_html=True)
       st.markdown("<p style='text-align: center; font-weight: 500;'>📧 info@dg-inc.qc.ca</p>", unsafe_allow_html=True)
       st.markdown("<p style='text-align: center; font-weight: 500;'>🌐 https://www.dg-inc.qc.ca</p>", unsafe_allow_html=True)
       st.markdown("<p style='text-align: center; font-weight: 500;'>📞 Tél.: (450) 372-9630</p>", unsafe_allow_html=True)

   st.divider()
   st.markdown("<h2 style='text-align: center;'>Connexion</h2>", unsafe_allow_html=True)
   st.markdown("<p style='text-align: center;'>Veuillez entrer le mot de passe pour accéder à l'application.</p>", unsafe_allow_html=True)

   correct_password = os.environ.get("APP_PASSWORD")
   if not correct_password:
       try:
           correct_password = st.secrets.get("APP_PASSWORD")
       except Exception: # StreamlitAPIException or AttributeError if secrets not set
           pass
   
   if not correct_password:
       st.error("Erreur de configuration: Mot de passe non défini. Veuillez définir la variable d'environnement 'APP_PASSWORD'.")
       st.info("Pour configurer dans Render, allez dans Dashboard > Votre app > Environment > Environment Variables")
       return False

   _, login_col, _ = st.columns([1, 1.5, 1])
   with login_col:
       password_attempt = st.text_input(
           "Mot de passe", type="password", key="password_input_login",
           label_visibility="collapsed", placeholder="Entrez votre mot de passe"
       )
       login_button = st.button("Se connecter", key="login_button", use_container_width=True)

   if login_button:
       if password_attempt == correct_password:
           st.session_state.logged_in = True
           st.rerun()
       else:
           st.error("Mot de passe incorrect.")
   return False


# --- Exécution Principale ---
if not display_login_or_app():
   st.stop()

# --- SI CONNECTÉ, LE SCRIPT CONTINUE ICI ---
st.set_page_config(
   page_title="Desmarais & Gagné",
   page_icon="🏗️",
   layout="wide",
   initial_sidebar_state="expanded"
)

st.markdown("""
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
   <style>
       .sidebar-subheader {
           margin-top: 1.5rem; margin-bottom: 0.5rem; font-size: 0.875rem;
           font-weight: 500; color: var(--text-color-light);
           text-transform: uppercase; letter-spacing: 0.05em;
       }
       div[data-testid="stHorizontalBlock"] > div:nth-child(1) button[kind="secondary"] {
            text-align: left; justify-content: flex-start !important;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
            font-size: 0.9rem; padding: 0.4rem 0.6rem;
            border: 1px solid transparent; background-color: transparent;
            color: var(--text-color); transition: background-color 0.2s ease, border-color 0.2s ease;
       }
        div[data-testid="stHorizontalBlock"] > div:nth-child(1) button[kind="secondary"]:hover {
             background-color: var(--border-color-light); border-color: var(--border-color);
        }
        div[data-testid="stHorizontalBlock"] > div:nth-child(2) button[kind="secondary"] {
            background: none; border: none; color: var(--text-color-light); cursor: pointer;
            padding: 0.4rem 0.3rem; font-size: 0.9rem; line-height: 1;
        }
        div[data-testid="stHorizontalBlock"] > div:nth-child(2) button[kind="secondary"]:hover {
            color: #EF4444; background-color: rgba(239, 68, 68, 0.1);
        }
       /* Styles pour export messages individuels */
       .export-message-card {
           background: linear-gradient(to right, #f0f7ff, #e6f3ff);
           border-radius: 8px;
           padding: 12px;
           margin-bottom: 8px;
           border-left: 3px solid #3B82F6;
           transition: all 0.3s ease;
       }
       .export-message-card:hover {
           transform: translateY(-2px);
           box-shadow: 0 4px 8px rgba(59, 130, 246, 0.2);
       }
       .export-preview {
           font-size: 0.85rem;
           color: #6B7280;
           font-style: italic;
           margin-top: 4px;
       }
       /* Amélioration sélecteur */
       div[data-testid="stSelectbox"] > div > div {
           background-color: #f8f9fa;
           border-radius: 6px;
           border: 1px solid #e5e7eb;
       }
       /* Boutons export */
       div.stButton > button:has(span:contains("Exporter en HTML")) {
           background: linear-gradient(90deg, #60A5FA 0%, #3B82F6 100%) !important;
           color: white !important;
           font-weight: 600 !important;
       }
       div.stButton > button:has(span:contains("Exporter en HTML"))::before {
           content: "📄 " !important;
       }
       div.stButton > button:has(span:contains("Afficher pour Copie")) {
           background: linear-gradient(90deg, #F3F4F6 0%, #E5E7EB 100%) !important;
           color: #374151 !important;
           border: 1px solid #D1D5DB !important;
       }
       div.stButton > button:has(span:contains("Afficher pour Copie"))::before {
           content: "📋 " !important;
       }
   </style>
""", unsafe_allow_html=True)
local_css("style.css")

is_mobile = is_mobile_device()
adapt_layout_for_mobile(is_mobile)

load_dotenv()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
   try:
       ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY")
   except Exception:
       pass

APP_PASSWORD = os.environ.get("APP_PASSWORD") # Already loaded once, but can be re-checked
if not APP_PASSWORD:
   try:
       APP_PASSWORD = st.secrets.get("APP_PASSWORD")
   except Exception:
       pass

if 'profile_manager' not in st.session_state:
   try:
       profile_dir_path = "profiles"
       if not os.path.exists(profile_dir_path):
           os.makedirs(profile_dir_path, exist_ok=True)
           print(f"Dossier '{profile_dir_path}' créé.")
           default_profile_path = os.path.join(profile_dir_path, "default_expert.txt")
           if not os.path.exists(default_profile_path):
               with open(default_profile_path, "w", encoding="utf-8") as f:
                   f.write("Expert par Défaut\nJe suis un expert IA généraliste.")
               print("Profil par défaut créé.")
       st.session_state.profile_manager = ExpertProfileManager(profile_dir=profile_dir_path)
       print("ProfileManager initialisé.")
   except Exception as e:
       st.error(f"Erreur critique: Init ProfileManager: {e}")
       st.stop()

if 'expert_advisor' not in st.session_state:
   if not ANTHROPIC_API_KEY:
       st.error("Erreur critique: ANTHROPIC_API_KEY non configurée.")
       st.stop()
   try:
       st.session_state.expert_advisor = ExpertAdvisor(api_key=ANTHROPIC_API_KEY)
       st.session_state.expert_advisor.profile_manager = st.session_state.profile_manager
       print("ExpertAdvisor initialisé.")
       available_profiles = st.session_state.profile_manager.get_profile_names()
       if available_profiles:
           initial_profile_name = available_profiles[0]
           st.session_state.selected_profile_name = initial_profile_name
           st.session_state.expert_advisor.set_current_profile_by_name(initial_profile_name)
           print(f"Profil initial chargé: {initial_profile_name}")
       else:
           st.warning("Aucun profil expert trouvé. Utilisation profil par défaut.")
           default_profile = st.session_state.expert_advisor.get_current_profile()
           st.session_state.selected_profile_name = default_profile.get("name", "Expert (Défaut)")
   except Exception as e:
       st.error(f"Erreur critique: Init ExpertAdvisor: {e}")
       st.exception(e)
       st.stop()

if 'conversation_manager' not in st.session_state:
   try:
       db_file_path = "conversations.db"
       st.session_state.conversation_manager = ConversationManager(db_path=db_file_path)
       print(f"ConversationManager initialisé avec DB: {os.path.abspath(db_file_path)}")
   except Exception as e:
       st.error(f"Erreur: Init ConversationManager: {e}")
       st.exception(e)
       st.session_state.conversation_manager = None
       st.warning("Historique désactivé.")

if "messages" not in st.session_state: st.session_state.messages = []
if "current_conversation_id" not in st.session_state: st.session_state.current_conversation_id = None
if "processed_messages" not in st.session_state: st.session_state.processed_messages = set()


# --- Fonction de Génération HTML ---
def generate_html_report(messages, profile_name, conversation_id=None, client_name=""):
   dg_primary_color = "#00A971"
   dg_primary_darker = "#00673D"
   dg_background_color = "#F9FAFB"
   dg_secondary_background = "#FFFFFF"
   dg_text_color = "#374151"
   dg_text_light = "#6B7280"
   dg_border_color = "#E5E7EB"
   dg_border_light = "#F3F4F6"
   dg_green_very_pale = "#e6f7f1"
   dg_green_pale_user_bubble_start = "#f0f7f1"
   dg_green_pale_user_bubble_end = "#e6f3ee"
   dg_search_result_border = "#22c55e"

   base_css = load_css_content("style.css")
   now = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
   conv_id_display = f" (ID: {conversation_id})" if conversation_id else ""
   client_display = f"<p><strong>Client :</strong> {html.escape(client_name)}</p>" if client_name else ""
   messages_html = ""
   md_converter = markdown.Markdown(extensions=['tables', 'fenced_code', 'codehilite'])

   custom_css = f"""
   {base_css}
   body {{
       font-family: 'Inter', sans-serif, Arial, sans-serif;
       line-height: 1.6;
       color: {dg_text_color};
       background-color: {dg_background_color};
       padding: 2rem;
       max-width: 1200px;
       margin: 20px auto;
       box-shadow: 0 2px 10px rgba(0,0,0,.1);
       border-radius: 8px;
   }}
   .report-header {{
       background: linear-gradient(135deg, {dg_green_very_pale} 0%, #d0f0e6 100%);
       padding: 2rem;
       border-radius: 12px 12px 0 0;
       margin-bottom: 0;
       box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
       text-align: center;
   }}
   .report-header h1 {{
       margin: 0;
       color: {dg_primary_darker};
       font-size: 2.2rem;
       font-weight: 600;
   }}
   .report-info {{
       background: {dg_green_very_pale};
       border-radius: 0 0 12px 12px;
       padding: 1.5rem;
       margin-bottom: 2rem;
       box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
       border-left: 5px solid {dg_primary_color};
       font-size: 0.9rem;
       color: {dg_text_light};
   }}
   .report-info p {{ margin: 5px 0; }}
   .conversation-history {{ padding-top: 1.5rem; }}
   .stChatMessage {{
       margin-bottom: 1.5rem;
       padding: 1rem 1.2rem;
       border-radius: 0.5rem;
       box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
       animation: fadeIn 0.5s ease-out;
       position: relative;
       max-width: 85%;
   }}
   .stChatMessage.user-bubble {{
       background: linear-gradient(to right, {dg_green_pale_user_bubble_start}, {dg_green_pale_user_bubble_end});
       border-left: 4px solid {dg_primary_color};
       margin-left: auto;
       margin-right: 0;
   }}
   .stChatMessage.user-bubble::after {{
       content: "";
       position: absolute;
       top: 15px;
       right: -10px;
       border-width: 10px 0 10px 10px;
       border-style: solid;
       border-color: transparent transparent transparent {dg_green_pale_user_bubble_end};
   }}
   .stChatMessage.assistant-bubble {{
       background: linear-gradient(to right, {dg_secondary_background}, #fdfdfd);
       border-left: 4px solid {dg_primary_darker};
       margin-left: 0;
       margin-right: auto;
   }}
   .stChatMessage.assistant-bubble::after {{
       content: "";
       position: absolute;
       top: 15px;
       left: -10px;
       border-width: 10px 10px 10px 0;
       border-style: solid;
       border-color: transparent {dg_secondary_background} transparent transparent;
   }}
   .stChatMessage.search-bubble {{
       background: linear-gradient(to right, #f0fdf4, #e6f7ec);
       border-left: 4px solid {dg_search_result_border};
       margin-right: 4rem;
       color: #14532D;
   }}
   .stChatMessage.search-bubble .msg-content p,
   .stChatMessage.search-bubble .msg-content ul,
   .stChatMessage.search-bubble .msg-content ol {{
       color: #14532D;
   }}
   .stChatMessage.other-bubble {{
       background-color: {dg_border_light};
       border-left: 4px solid {dg_text_light};
   }}
   .msg-content strong {{ font-weight: 600; }}
   .msg-content table {{
       font-size: 0.9em;
       width: 100%;
       border-collapse: collapse;
       margin: 1em 0;
       box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
       border-radius: 0.375rem;
       overflow: hidden;
   }}
   .msg-content th, .msg-content td {{
       border: 1px solid {dg_border_color};
       padding: 0.6em 0.9em;
       text-align: left;
   }}
   .msg-content th {{
       background-color: {dg_border_light};
       font-weight: 500;
       color: {dg_text_color};
   }}
   .msg-content tr:nth-child(even) {{ background-color: {dg_background_color}; }}
   .msg-content pre {{
       background-color: #1F2937;
       color: #F9FAFB;
       padding: 1em;
       border-radius: 0.5rem;
       overflow-x: auto;
       border: 1px solid #4B5563;
       margin: 1em 0;
       font-size: 0.85rem;
       line-height: 1.5;
   }}
   .msg-content pre code {{
       background-color: transparent;
       color: inherit;
       padding: 0;
       margin: 0;
       font-size: inherit;
       border-radius: 0;
       font-family: "monospace", monospace;
       display: block;
       white-space: pre;
   }}
   section[data-testid=stSidebar],
   div[data-testid=stChatInput],
   .stButton,
   div[data-testid="stToolbar"],
   div[data-testid="stDecoration"] {{
       display: none !important;
   }}
   @keyframes fadeIn {{
       from {{ opacity: 0; transform: translateY(10px); }}
       to {{ opacity: 1; transform: translateY(0); }}
   }}
   """

   for msg in messages:
       role = msg.get("role", "unknown")
       content = msg.get("content", "*Message vide*")
       if role == "system": continue

       try:
           md_converter.reset()
           content_str = str(content) if not isinstance(content, str) else content
           content_html = md_converter.convert(content_str)
       except Exception as e:
           print(f"Erreur conversion Markdown: {e}")
           content_html = f"<p>{html.escape(str(content)).replace(chr(10), '<br/>')}</p>"

       bubble_class = ""
       avatar_text = ""
       if role == "user":
           bubble_class = "user-bubble"
           avatar_text = "Utilisateur"
       elif role == "assistant":
           bubble_class = "assistant-bubble"
           avatar_text = f"Expert ({html.escape(profile_name)})"
       elif role == "search_result":
           bubble_class = "search-bubble"
           avatar_text = "Résultat Recherche Web"
       else:
           bubble_class = "other-bubble"
           avatar_text = html.escape(role.capitalize())

       messages_html += f'<div class="stChatMessage {bubble_class}"><strong>{avatar_text} :</strong><div class="msg-content">{content_html}</div></div>\n'

   html_output = f"""<!DOCTYPE html>
<html lang="fr">
<head>
   <meta charset="UTF-8">
   <meta name="viewport" content="width=device-width, initial-scale=1.0">
   <title>Rapport Desmarais & Gagné - {html.escape(profile_name)}{conv_id_display}</title>
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
   <style>{custom_css}</style>
</head>
<body>
   <div class="report-header"><h1>Rapport Desmarais & Gagné</h1></div>
   <div class="report-info">
       <p><strong>Expert :</strong> {html.escape(profile_name)}</p>
       {client_display}
       <p><strong>Date :</strong> {now}</p>
       <p><strong>ID Conversation :</strong> {html.escape(str(conversation_id)) if conversation_id else 'N/A'}</p>
   </div>
   <div class="conversation-history">{messages_html}</div>
</body>
</html>"""
   return html_output

# --- Fonction pour exporter un message individuel ---
def generate_single_message_html(message_content, message_role, profile_name, message_index=0, timestamp=None):
   """Génère HTML pour un message individuel avec style amélioré."""
   
   if not timestamp:
       timestamp = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
   
   base_css = load_css_content("style.css")
   
   if message_role == "user":
       role_display = "Utilisateur"
       bubble_class = "user-bubble"
       avatar_icon = "👤"
       header_color = "#3B82F6"
   elif message_role == "search_result":
       role_display = "Résultat Recherche Web"
       bubble_class = "search-bubble"
       avatar_icon = "🔎"
       header_color = "#22c55e"
   else:
       role_display = f"Expert ({profile_name})"
       bubble_class = "assistant-bubble"
       avatar_icon = "🏗️"
       header_color = "#00A971"
   
   # Conversion markdown avec gestion d'erreurs robuste
   try:
       md_converter = markdown.Markdown(extensions=['tables', 'fenced_code', 'codehilite'])
       md_converter.reset()
       content_html = md_converter.convert(str(message_content))
   except Exception as e:
       print(f"Erreur conversion Markdown: {e}")
       # Fallback sécurisé
       escaped_content = html.escape(str(message_content))
       content_html = f"<p>{escaped_content.replace(chr(10), '<br/>')}</p>"
   
   specialized_css = f"""
   {base_css}
   
   body {{
       max-width: 900px;
       margin: 20px auto;
       padding: 20px;
       background-color: #F9FAFB;
       font-family: 'Inter', sans-serif;
   }}
   
   .single-message-container {{
       background: white;
       border-radius: 12px;
       box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
       padding: 0;
       overflow: hidden;
   }}
   
   .message-header {{
       background: linear-gradient(135deg, {header_color}15 0%, {header_color}08 100%);
       padding: 20px;
       border-bottom: 1px solid #E5E7EB;
       border-left: 5px solid {header_color};
   }}
   
   .message-header h1 {{
       margin: 0;
       color: {header_color};
       font-size: 1.8rem;
       display: flex;
       align-items: center;
       gap: 10px;
       font-weight: 600;
   }}
   
   .message-meta {{
       margin-top: 10px;
       font-size: 0.9rem;
       color: #6B7280;
       display: flex;
       gap: 20px;
       flex-wrap: wrap;
   }}
   
   .meta-item {{
       display: flex;
       align-items: center;
       gap: 5px;
   }}
   
   .message-content {{ 
       padding: 25px; 
       line-height: 1.6;
   }}
   
   .export-footer {{
       text-align: center; 
       padding: 20px; 
       border-top: 1px solid #E5E7EB;
       background-color: #F9FAFB; 
       font-size: 0.85rem; 
       color: #6B7280;
   }}
   
   .export-footer .logo {{
       color: #00A971;
       font-weight: 600;
       font-size: 1rem;
   }}
   
   /* Responsive */
   @media (max-width: 768px) {{
       body {{ padding: 10px; }}
       .message-header {{ padding: 15px; }}
       .message-header h1 {{ font-size: 1.5rem; }}
       .message-content {{ padding: 20px; }}
   }}
   """
   
   html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
   <meta charset="UTF-8">
   <meta name="viewport" content="width=device-width, initial-scale=1.0">
   <title>Message Desmarais & Gagné - {role_display}</title>
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
   <style>{specialized_css}</style>
</head>
<body>
   <div class="single-message-container">
       <div class="message-header">
           <h1>{avatar_icon} {html.escape(role_display)}</h1>
           <div class="message-meta">
               <div class="meta-item">
                   <span>📅</span>
                   <span>Exporté le {timestamp}</span>
               </div>
               <div class="meta-item">
                   <span>#️⃣</span>
                   <span>Message #{message_index + 1}</span>
               </div>
               <div class="meta-item">
                   <span>📏</span>
                   <span>{len(str(message_content))} caractères</span>
               </div>
           </div>
       </div>
       <div class="message-content">
           {content_html}
       </div>
       <div class="export-footer">
           <div class="logo">🏗️ Desmarais & Gagné</div>
           <p>Assistant IA Spécialisé en Fabrication Métallique</p>
           <p>📧 info@dg-inc.qc.ca | 🌐 https://www.dg-inc.qc.ca | 📞 (450) 372-9630</p>
       </div>
   </div>
</body>
</html>"""
   
   return html_content

# --- Helper Functions (Application Logic) ---
def start_new_consultation():
   st.session_state.messages = []
   st.session_state.current_conversation_id = None
   st.session_state.processed_messages = set()
   profile_name = "par défaut"
   if 'expert_advisor' in st.session_state:
       profile = st.session_state.expert_advisor.get_current_profile()
       profile_name = profile.get('name', 'par défaut') if profile else "par défaut"
   st.session_state.messages.append({
       "role": "assistant",
       "content": f"Bonjour! Je suis votre expert {profile_name}. Comment puis-je vous aider aujourd'hui?\n\n"
                  f"Pour effectuer une recherche web, tapez simplement `/search votre question`\n"
                  f"Exemple: `/search normes construction Quebec 2025`"
   })
   if 'html_download_data' in st.session_state: del st.session_state.html_download_data
   if 'single_message_download' in st.session_state: del st.session_state.single_message_download
   if 'show_copy_content' in st.session_state: del st.session_state.show_copy_content
   if "files_to_analyze" in st.session_state: del st.session_state.files_to_analyze
   st.rerun()

def load_selected_conversation(conv_id):
   if st.session_state.conversation_manager:
       messages = st.session_state.conversation_manager.load_conversation(conv_id)
       if messages is not None:
           st.session_state.messages = messages
           st.session_state.current_conversation_id = conv_id
           st.session_state.processed_messages = set()
           if 'html_download_data' in st.session_state: del st.session_state.html_download_data
           if 'single_message_download' in st.session_state: del st.session_state.single_message_download
           if 'show_copy_content' in st.session_state: del st.session_state.show_copy_content
           if "files_to_analyze" in st.session_state: del st.session_state.files_to_analyze
           st.success(f"Consultation {conv_id} chargée.")
           st.rerun()
       else:
           st.error(f"Erreur lors du chargement de la conversation {conv_id}.")
   else:
       st.error("Gestionnaire de conversations indisponible.")

def delete_selected_conversation(conv_id):
   if st.session_state.conversation_manager:
       print(f"Tentative suppression conv {conv_id}")
       success = st.session_state.conversation_manager.delete_conversation(conv_id)
       if success:
           st.success(f"Consultation {conv_id} supprimée.")
           if st.session_state.current_conversation_id == conv_id:
               start_new_consultation()
           else:
               if 'html_download_data' in st.session_state: del st.session_state.html_download_data
               if 'single_message_download' in st.session_state: del st.session_state.single_message_download
               if 'show_copy_content' in st.session_state: del st.session_state.show_copy_content
               st.rerun()
       else:
           st.error(f"Impossible de supprimer conv {conv_id}.")
   else:
       st.error("Gestionnaire de conversations indisponible.")

def save_current_conversation():
   should_save = True
   if st.session_state.conversation_manager and st.session_state.messages:
       is_initial_greeting_only = (
           len(st.session_state.messages) == 1 and
           st.session_state.messages[0].get("role") == "assistant" and
           st.session_state.messages[0].get("content", "").startswith("Bonjour!") and
           st.session_state.current_conversation_id is None
       )
       if is_initial_greeting_only: should_save = False

       if should_save:
           try:
               new_id = st.session_state.conversation_manager.save_conversation(
                   st.session_state.current_conversation_id,
                   st.session_state.messages
               )
               if new_id is not None and st.session_state.current_conversation_id is None:
                   st.session_state.current_conversation_id = new_id
           except Exception as e:
               st.warning(f"Erreur sauvegarde auto: {e}")
               st.exception(e)

# --- Fonction Export Sidebar Section ---
def create_export_sidebar_section():
   """Section d'export complète pour la sidebar."""
   
   st.markdown('<div class="sidebar-subheader">📥 EXPORT</div>', unsafe_allow_html=True)
   
   # Export conversation complète (conserver l'existant)
   client_name_export = st.text_input("Nom client (optionnel)", key="client_name_export", placeholder="Pour rapport HTML")
   
   st.markdown("""
   <style>
   div.stButton > button:has(span:contains("Rapport HTML")) {
       background: linear-gradient(90deg, #93c5fd 0%, #60a5fa 100%) !important;
       color: white !important; font-weight: 600 !important; border: none !important;
   }
   div.stButton > button:has(span:contains("Rapport HTML"))::before { content: "📄 " !important; }
   div.stButton > button:has(span:contains("Rapport HTML")):hover {
       background: linear-gradient(90deg, #60a5fa 0%, #3b82f6 100%) !important;
       transform: translateY(-2px) !important; box-shadow: 0 4px 8px rgba(59, 130, 246, 0.2) !important;
   }
   div.stButton > button:has(span:contains("Télécharger HTML")) {
       background: linear-gradient(90deg, #bbf7d0 0%, #86efac 100%) !important;
       color: #166534 !important; font-weight: 600 !important; border: none !important;
   }
   div.stButton > button:has(span:contains("Télécharger HTML"))::before { content: "⬇️ " !important; }
   div.stButton > button:has(span:contains("Télécharger HTML")):hover {
       background: linear-gradient(90deg, #86efac 0%, #4ade80 100%) !important;
       transform: translateY(-2px) !important; box-shadow: 0 4px 8px rgba(22, 101, 52, 0.2) !important;
   }
   </style>
   """, unsafe_allow_html=True)
  
   if st.button("Rapport HTML", key="gen_html_btn", use_container_width=True, help="Générer rapport HTML"):
       st.session_state.html_download_data = None
       can_generate = True
       if not st.session_state.messages or (len(st.session_state.messages) == 1 and st.session_state.messages[0].get("role") == "assistant" and st.session_state.messages[0].get("content", "").startswith("Bonjour!")):
           can_generate = False
       if not can_generate:
           st.warning("Conversation vide ou initiale.")
       else:
           with st.spinner("Génération HTML..."):
               try:
                   profile_name = "Expert"
                   current_profile = st.session_state.expert_advisor.get_current_profile() if 'expert_advisor' in st.session_state else None
                   if current_profile: profile_name = current_profile.get('name', 'Expert')
                   conv_id = st.session_state.current_conversation_id
                   html_string = generate_html_report(st.session_state.messages, profile_name, conv_id, client_name_export)
                   if html_string:
                       id_part = f"Conv{conv_id}" if conv_id else datetime.now().strftime('%Y%m%d_%H%M')
                       filename = f"Rapport_Desmarais_&_Gagné_{id_part}.html"
                       st.session_state.html_download_data = {"data": html_string, "filename": filename}
                       st.success("Rapport prêt.")
                   else:
                       st.error("Échec génération HTML.")
               except Exception as e:
                   st.error(f"Erreur génération HTML: {e}")
                   st.exception(e)
       st.rerun() # Rerun après la tentative de génération ou l'avertissement
       
   if st.session_state.get('html_download_data'):
       download_info = st.session_state.html_download_data
       st.download_button(
           label="⬇️ Télécharger HTML",
           data=download_info["data"].encode("utf-8"),
           file_name=download_info["filename"],
           mime="text/html",
           key="dl_html",
           use_container_width=True,
           on_click=lambda: st.session_state.update(html_download_data=None)
       )
   
   # === NOUVELLE SECTION : EXPORT MESSAGES INDIVIDUELS ===
   st.markdown("---")
   st.markdown('<div class="sidebar-subheader">📤 MESSAGES INDIVIDUELS</div>', unsafe_allow_html=True)
   
   if not st.session_state.messages:
       st.caption("Aucun message à exporter.")
       return
   
   # Filtrer les messages exportables
   exportable_messages = []
   for i, msg in enumerate(st.session_state.messages):
       if msg.get("role") in ["assistant", "search_result"] and msg.get("content", "").strip():
           role_display = "🏗️ Expert" if msg["role"] == "assistant" else "🔎 Recherche"
           content_preview = str(msg["content"])[:40] + "..." if len(str(msg["content"])) > 40 else str(msg["content"])
           exportable_messages.append({
               "index": i,
               "display": f"{role_display}: {content_preview}",
               "role": msg["role"],
               "content": msg["content"]
           })
   
   if not exportable_messages:
       st.caption("Aucun message expert à exporter.")
       return
   
   # Sélecteur de message
   selected_msg = st.selectbox(
       "Message à exporter:",
       options=exportable_messages,
       format_func=lambda x: x["display"],
       key="export_message_selector",
       label_visibility="collapsed"
   )
   
   if selected_msg:
       # Aperçu condensé
       with st.expander("👀 Aperçu", expanded=False):
           content_preview = str(selected_msg['content'])
           if len(content_preview) > 150:
               st.markdown(content_preview[:150] + "...")
               st.caption(f"Total: {len(content_preview)} caractères")
           else:
               st.markdown(content_preview)
       
       # Boutons d'export
       if st.button("📄 Exporter en HTML", key="export_single_html", use_container_width=True):
           try:
               profile = st.session_state.expert_advisor.get_current_profile()
               profile_name = profile.get('name', 'Expert') if profile else 'Expert'
               
               html_content = generate_single_message_html(
                   selected_msg['content'], 
                   selected_msg['role'], 
                   profile_name, 
                   selected_msg['index']
               )
               
               timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
               filename = f"Message_DG_{selected_msg['role']}_{selected_msg['index']}_{timestamp}.html"
               
               # Stocker pour téléchargement
               st.session_state.single_message_download = {
                   "data": html_content,
                   "filename": filename
               }
               
               st.success("✅ Fichier prêt pour téléchargement")
               st.rerun()
               
           except Exception as e:
               st.error(f"Erreur lors de l'export: {e}")
       
       # Bouton de téléchargement si prêt
       if st.session_state.get('single_message_download'):
           download_data = st.session_state.single_message_download
           st.download_button(
               label="⬇️ Télécharger HTML",
               data=download_data["data"].encode('utf-8'),
               file_name=download_data["filename"],
               mime="text/html",
               key="download_single_message",
               use_container_width=True,
               on_click=lambda: st.session_state.pop('single_message_download', None)
           )
       
       # Option copie texte
       if st.button("📋 Afficher pour Copie", key="show_for_copy", use_container_width=True):
           st.session_state.show_copy_content = selected_msg['content']
           st.rerun()
       
       # Affichage pour copie si demandé
       if st.session_state.get('show_copy_content'):
           st.text_area(
               "Contenu à copier:",
               value=st.session_state.show_copy_content,
               height=150,
               key="copy_content_area"
           )
           if st.button("❌ Fermer", key="close_copy"):
               st.session_state.pop('show_copy_content', None)
               st.rerun()

# --- Sidebar UI (App Principale) ---
with st.sidebar:
   try:
       logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
       if os.path.exists(logo_path):
           st.markdown(
               f"""
               <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; 
                          width: 100%; margin-bottom: 1.5rem; transition: all 0.3s;">
                   <div style="background: linear-gradient(135deg, #e0f7fa 0%, #e8f5e9 100%); 
                              border-radius: 50%; padding: 10px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
                              transition: all 0.3s;" onmouseover="this.style.transform='scale(1.05)'"
                              onmouseout="this.style.transform='scale(1)'">
                       <img src="data:image/png;base64,{get_image_base64(logo_path)}" 
                           style="width: 120px; height: auto;">
                   </div>
                   <span style="font-size: 1.5rem; font-weight: 500; margin-top: 10px;">
                       <span style="color: #00A971; font-weight: 600;">Desmarais</span>
                       <span style="color: #000000; font-weight: 700;">& Gagné</span>
                   </span>
               </div>
               """,
               unsafe_allow_html=True
           )
       else:
           st.warning("Logo 'assets/logo.png' non trouvé.")
   except Exception as e:
       st.error(f"Erreur logo: {e}")

   st.markdown("""
   <style>
   div.stButton > button:has(span:contains("Nouvelle Consultation")) {
       background: linear-gradient(90deg, #60A5FA 0%, #3B82F6 100%) !important;
       color: white !important;
       font-weight: 600 !important;
       padding: 10px 15px !important;
       position: relative !important;
   }
   div.stButton > button:has(span:contains("Nouvelle Consultation"))::before {
       content: "✨ " !important;
   }
   div.stButton > button:has(span:contains("Nouvelle Consultation")):hover {
       background: linear-gradient(90deg, #3B82F6 0%, #2563EB 100%) !important;
       transform: translateY(-2px) !important;
       box-shadow: 0 6px 12px rgba(59, 130, 246, 0.2) !important;
   }
   </style>
   """, unsafe_allow_html=True)

   if st.button("Nouvelle Consultation", key="new_consult_button_top", use_container_width=True):
       save_current_conversation()
       start_new_consultation()
   st.markdown('<hr style="margin: 1rem 0; border-top: 1px solid var(--border-color);">', unsafe_allow_html=True)

   st.markdown('<div class="sidebar-subheader">👤 PROFIL EXPERT</div>', unsafe_allow_html=True)
   if 'expert_advisor' in st.session_state and st.session_state.expert_advisor.profile_manager:
       profile_names = st.session_state.expert_advisor.profile_manager.get_profile_names()
       if profile_names:
           try:
               selected_profile_name_ref = st.session_state.get("selected_profile_name", profile_names[0])
               current_index = profile_names.index(selected_profile_name_ref) if selected_profile_name_ref in profile_names else 0
           except ValueError:
               current_index = 0
           selected_profile = st.selectbox("Profil:", profile_names, index=current_index, key="profile_select", label_visibility="collapsed")
           if selected_profile != st.session_state.get("selected_profile_name"):
               print(f"Changement profil: '{st.session_state.get('selected_profile_name')}' -> '{selected_profile}'")
               save_current_conversation()
               with st.spinner(f"Changement vers {selected_profile}..."):
                   success = st.session_state.expert_advisor.set_current_profile_by_name(selected_profile)
                   if success:
                       st.session_state.selected_profile_name = selected_profile
                       st.success(f"Profil changé. Nouvelle consultation.")
                       start_new_consultation()
                   else:
                       st.error(f"Impossible de charger profil '{selected_profile}'.")
       else:
           st.warning("Aucun profil expert trouvé.")
   else:
       st.error("Module Expert non initialisé.")

   st.markdown('<div class="sidebar-subheader">📄 ANALYSE FICHIERS</div>', unsafe_allow_html=True)
   uploaded_files_sidebar = []
   if 'expert_advisor' in st.session_state:
       supported_types = st.session_state.expert_advisor.get_supported_filetypes_flat()
       uploaded_files_sidebar = st.file_uploader(
           "Téléverser fichiers:",
           type=supported_types if supported_types else None,
           accept_multiple_files=True,
           key="file_uploader_sidebar",
           label_visibility="collapsed"
       )
       is_disabled = not bool(uploaded_files_sidebar)
       st.markdown("""
       <style>
       div.stButton > button:has(span:contains("Analyser")) {
           background: linear-gradient(90deg, #c5e1a5 0%, #aed581 100%) !important;
           color: #33691e !important;
           border: none !important;
           animation: pulse 2s infinite;
       }
       div.stButton > button:has(span:contains("Analyser"))::before {
           content: "🔍 " !important;
       }
       div.stButton > button:has(span:contains("Analyser")):hover {
           background: linear-gradient(90deg, #aed581 0%, #9ccc65 100%) !important;
           transform: translateY(-2px) !important;
           box-shadow: 0 4px 8px rgba(51, 105, 30, 0.2) !important;
       }
       </style>
       """, unsafe_allow_html=True)

       if st.button("🔍 Analyser Fichiers", key="analyze_button", use_container_width=True, disabled=is_disabled):
           if not is_disabled:
               num_files = len(uploaded_files_sidebar)
               file_names_str = ', '.join([f.name for f in uploaded_files_sidebar])
               user_analysis_prompt = f"J'ai téléversé {num_files} fichier(s) ({file_names_str}) pour analyse. Peux-tu les examiner ?"
               action_id = f"analyze_{datetime.now().isoformat()}"
               st.session_state.files_to_analyze = uploaded_files_sidebar
               st.session_state.messages.append({"role": "user", "content": user_analysis_prompt, "id": action_id})
               save_current_conversation()
               st.rerun()

   st.markdown('<hr style="margin: 1rem 0; border-top: 1px solid var(--border-color);">', unsafe_allow_html=True)
   st.markdown('<div class="sidebar-subheader">🔎 RECHERCHE WEB</div>', unsafe_allow_html=True)
   with st.expander("Comment utiliser la recherche web"):
       st.markdown("""
       Pour effectuer une recherche web via Claude:
       1. Tapez `/search` suivi de votre question ou requête
       2. Exemple: `/search normes électriques Québec`
       3. Pour rechercher des informations sur un site spécifique:
          `/search règlement construction site:rbq.gouv.qc.ca`
       4. Attendez quelques secondes pour les résultats

       **Remarque:** Pour obtenir les meilleurs résultats, formulez des questions précises et utilisez des mots-clés pertinents.
       """)

   if st.session_state.get('conversation_manager'):
       st.markdown('<hr style="margin: 1rem 0; border-top: 1px solid var(--border-color);">', unsafe_allow_html=True)
       st.markdown('<div class="sidebar-subheader">🕒 HISTORIQUE</div>', unsafe_allow_html=True)
       try:
           conversations = st.session_state.conversation_manager.list_conversations(limit=100)
           if not conversations: st.caption("Aucune consultation sauvegardée.")
           else:
               st.markdown("""
               <style>
               div[data-testid="stHorizontalBlock"] > div:nth-child(1) button[kind="secondary"] {
                   text-align: left; justify-content: flex-start !important;
                   overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
                   font-size: 0.9rem; padding: 0.4rem 0.6rem;
                   border: 1px solid transparent; background-color: transparent;
                   color: var(--text-color); transition: all 0.3s; border-radius: 6px;
               }
               div[data-testid="stHorizontalBlock"] > div:nth-child(1) button[kind="secondary"]:hover {
                   background-color: #f0f7ff; border-color: #dbeafe; transform: translateX(3px);
               }
               div[data-testid="stHorizontalBlock"] > div:nth-child(2) button[kind="secondary"] {
                   background: none; border: none; color: var(--text-color-light);
                   cursor: pointer; padding: 0.4rem 0.3rem; font-size: 0.9rem;
                   line-height: 1; transition: all 0.2s; border-radius: 6px;
               }
               div[data-testid="stHorizontalBlock"] > div:nth-child(2) button[kind="secondary"]:hover {
                   color: #EF4444; background-color: rgba(239, 68, 68, 0.1); transform: scale(1.1);
               }
               </style>
               """, unsafe_allow_html=True)
               with st.container(height=300):
                   for conv in conversations:
                       col1, col2 = st.columns([0.85, 0.15])
                       with col1:
                           if st.button(conv['name'], key=f"load_conv_{conv['id']}", use_container_width=True, type="secondary", help=f"Charger '{conv['name']}' (màj: {conv['last_updated_at']})"):
                               save_current_conversation()
                               load_selected_conversation(conv['id'])
                       with col2:
                           if st.button("🗑️", key=f"delete_conv_{conv['id']}", help=f"Supprimer '{conv['name']}'", use_container_width=True, type="secondary"):
                               delete_selected_conversation(conv['id'])
       except Exception as e:
           st.error(f"Erreur historique: {e}")
           st.exception(e)
   else:
       st.caption("Module historique inactif.")

   st.markdown('<hr style="margin: 1rem 0; border-top: 1px solid var(--border-color);">', unsafe_allow_html=True)
   
   # === NOUVELLE SECTION EXPORT ===
   create_export_sidebar_section()

   st.markdown('<hr style="margin: 1rem 0; border-top: 1px solid var(--border-color);">', unsafe_allow_html=True)
   st.markdown('<div class="sidebar-subheader">🔗 OUTILS & MANUELS</div>', unsafe_allow_html=True)
   st.markdown("""
   <style>
   .program-link {
       display: flex; align-items: center; padding: 8px 12px; margin-bottom: 8px;
       background: linear-gradient(to right, #ffffff, #f7f9fc);
       border-radius: 8px; transition: all 0.3s; text-decoration: none;
       color: #3b82f6; border: 1px solid #e5e7eb;
   }
   .program-link:hover {
       background: linear-gradient(to right, #f0f7ff, #e6f3ff);
       transform: translateX(3px); border-color: #dbeafe;
       box-shadow: 0 2px 4px rgba(59, 130, 246, 0.1);
   }
   .program-link::before { content: "🔗"; margin-right: 8px; }
   
   /* Style spécial pour les outils principaux */
   .tool-link {
       display: flex; align-items: center; padding: 10px 14px; margin-bottom: 10px;
       background: linear-gradient(135deg, #e6f7f1 0%, #d0f0e6 100%);
       border-radius: 8px; transition: all 0.3s; text-decoration: none;
       color: #00673D; border: 1px solid #a5e9d0;
       font-weight: 500;
   }
   .tool-link:hover {
       background: linear-gradient(135deg, #d0f0e6 0%, #a5e9d0 100%);
       transform: translateX(4px) translateY(-1px); border-color: #00A971;
       box-shadow: 0 3px 8px rgba(0, 169, 113, 0.2);
   }
   .tool-link.formulaires::before { content: "📋"; margin-right: 8px; }
   .tool-link.manuel::before { content: "📖"; margin-right: 8px; }
   </style>
   """, unsafe_allow_html=True)
  
   # Liens vers les outils principaux avec style spécial
   outils_links = {
       "Formulaire": {
           "url": "https://formulaires-dg.onrender.com/",
           "class": "formulaires",
           "style": "tool-link"
       }
   }

   # Affichage des outils principaux
   for tool_name, tool_info in outils_links.items():
       st.markdown(f"""<a href="{tool_info['url']}" target="_blank" class="{tool_info['style']} {tool_info['class']}">{tool_name}</a>""", unsafe_allow_html=True)
   
   # Séparateur subtil
   st.markdown('<div style="border-top: 1px solid #e5e7eb; margin: 15px 0;"></div>', unsafe_allow_html=True)
   
   # Manuel d'instruction avec style standard
   manuel_links = {"Manuel d'instruction": "https://estimation79.github.io/MANUEL_UTILISATION/"}
   for program_name, link_url in manuel_links.items():
       if link_url and link_url != "#" and link_url.strip(): 
           st.markdown(f"""<a href="{link_url}" target="_blank" class="program-link manuel">{program_name}</a>""", unsafe_allow_html=True)
       else:
           st.markdown(f"""<div class="program-link" style="color: var(--text-color-light); opacity: 0.7;">{program_name} <span style="font-size: 0.8rem;">(lien non disponible)</span></div>""", unsafe_allow_html=True)
   
   st.caption("Propriété intellectuelle de Desmarais & Gagné. info@dg-inc.qc.ca")

   st.markdown('<hr style="margin: 1rem 0; border-top: 1px solid var(--border-color);">', unsafe_allow_html=True)
   st.markdown("""
   <style>
   div.stButton > button:has(span:contains("Déconnexion")) {
       background: linear-gradient(90deg, #fee2e2 0%, #fecaca 100%) !important;
       color: #b91c1c !important; border: none !important;
       font-weight: 500 !important; transition: all 0.3s !important;
   }
   div.stButton > button:has(span:contains("Déconnexion"))::before { content: "🚪 " !important; }
   div.stButton > button:has(span:contains("Déconnexion")):hover {
       background: linear-gradient(90deg, #fecaca 0%, #fca5a5 100%) !important;
       transform: translateY(-2px) !important;
       box-shadow: 0 4px 8px rgba(220, 38, 38, 0.15) !important;
   }
   </style>
   """, unsafe_allow_html=True)
  
   if st.button("Déconnexion", key="logout_button", use_container_width=True):
       st.session_state.logged_in = False
       keys_to_clear = ["messages", "current_conversation_id", "processed_messages", "html_download_data", "single_message_download", "show_copy_content", "selected_profile_name", "files_to_analyze"]
       for key in keys_to_clear:
           if key in st.session_state: del st.session_state[key]
       if 'expert_advisor' in st.session_state: del st.session_state['expert_advisor']
       if 'profile_manager' in st.session_state: del st.session_state['profile_manager']
       if 'conversation_manager' in st.session_state: del st.session_state['conversation_manager']
       st.rerun()

# --- Main Chat Area (App Principale) ---
main_container = st.container()
with main_container:
   if 'expert_advisor' in st.session_state:
       current_profile = st.session_state.expert_advisor.get_current_profile()
       profile_name_main = "Assistant Desmarais & Gagné"
       profile_name_main = current_profile.get('name', profile_name_main) if current_profile else profile_name_main
       
       st.markdown(f"""
       <div class="main-header">
           <h1>🏗️ Assistant: {html.escape(profile_name_main)}</h1>
           <p>Votre expert en métallurgie - Posez vos questions ou téléversez des documents</p>
       </div>
       """, unsafe_allow_html=True)
       
       if not current_profile or current_profile.get('id') == 'default_expert': 
           st.info("*Profil expert par défaut actif. Vous pouvez changer de profil dans le menu latéral.*")
   else: 
       st.markdown("""
       <div class="main-header">
           <h1>🏗️ Assistant Desmarais & Gagné</h1>
           <p>Erreur: Module expert non initialisé</p>
       </div>
       """, unsafe_allow_html=True)
       st.error("Erreur: Module expert non initialisé.")

   if not st.session_state.messages and 'expert_advisor' in st.session_state:
       profile = st.session_state.expert_advisor.get_current_profile()
       prof_name = profile.get('name', 'par défaut') if profile else "par défaut"
       st.session_state.messages.append({
           "role": "assistant",
           "content": f"Bonjour! Je suis votre expert {prof_name}. Comment puis-je vous aider aujourd'hui?\n\n"
                      f"Pour effectuer une recherche web, tapez simplement `/search votre question`\n"
                      f"Exemple: `/search normes construction Quebec 2025`"
       })

   st.markdown("""
   <style>
   div[data-testid="stChatMessage"]:has(div[data-testid^="chatAvatarIcon-user"]) {
       background: linear-gradient(to right, #f0f7ff, #e6f3ff);
       border-left: 4px solid #60A5FA; margin-left: auto; margin-right: 0;
       width: 85%; position: relative; animation: fadeIn 0.5s ease-out;
   }
   div[data-testid="stChatMessage"]:has(div[data-testid^="chatAvatarIcon-user"])::after {
       content: ""; position: absolute; top: 20px; right: -10px;
       border-width: 10px 0 10px 10px; border-style: solid;
       border-color: transparent transparent transparent #e6f3ff;
   }
   div[data-testid="stChatMessage"]:has(div[data-testid^="chatAvatarIcon-assistant"]) {
       background: linear-gradient(to right, #f7f9fc, #ffffff);
       border-left: 4px solid #3B82F6; margin-left: 0; margin-right: auto;
       width: 85%; position: relative; animation: fadeIn 0.5s ease-out;
   }
   div[data-testid="stChatMessage"]:has(div[data-testid^="chatAvatarIcon-assistant"])::after {
       content: ""; position: absolute; top: 20px; left: -10px;
       border-width: 10px 10px 10px 0; border-style: solid;
       border-color: transparent #f7f9fc transparent transparent;
   }
   div[data-testid="stChatMessage"]:has(div[data-testid^="chatAvatarIcon-search_result"]) {
       background: linear-gradient(to right, #f0fdf4, #e6f7ec);
       border-left: 4px solid #22c55e; animation: fadeIn 0.5s ease-out;
   }
   .chat-avatar {
       display: flex; align-items: center; justify-content: center;
       width: 36px; height: 36px; border-radius: 50%;
       font-size: 18px; margin-right: 10px;
   }
   .avatar-user { background-color: #dbeafe; color: #2563eb; }
   .avatar-assistant { background-color: #3B82F6; color: white; }
   .avatar-search { background-color: #dcfce7; color: #16a34a; }
   </style>
   """, unsafe_allow_html=True)

   for i, message in enumerate(st.session_state.messages):
       role = message.get("role", "unknown")
       content = message.get("content", "*Message vide*")
       if role == "system": 
           continue
       
       avatar = "🤖"
       if role == "user": avatar = "👤"
       elif role == "assistant": avatar = "🏗️"
       elif role == "search_result": avatar = "🔎"
       
       with st.chat_message(role, avatar=avatar):
           display_content = str(content) if not isinstance(content, str) else content
           # Vérifier si c'est un message d'analyse pour un affichage spécial
           # (Note: Ceci est une simplification. L'idéal serait un type de message dédié)
           if "Résultats de l'analyse des documents" in display_content or "Analyse des documents" in display_content and role == "assistant" and "analysis_response" in message:
                # Si on veut réutiliser display_analysis_result, il faudrait le modifier pour
                # prendre le contenu et le rendre, ou stocker le HTML pré-rendu.
                # Pour l'instant, on affiche le markdown brut qui contient des **.
                st.markdown(display_content, unsafe_allow_html=False) # ou True si le contenu est déjà HTML
           else:
               st.markdown(display_content, unsafe_allow_html=False)

# --- Chat Input ---
st.markdown("""
<style>
div[data-testid="stChatInput"] {
   background-color: var(--secondary-background-color);
   border-top: 1px solid var(--border-color); padding: 0.5rem 1rem;
   box-shadow: 0 -2px 5px rgba(0,0,0,0.03);
   border-radius: 12px 12px 0 0; margin-top: 20px;
}
div[data-testid="stChatInput"] textarea {
   border-radius: 12px; border: 1px solid var(--border-color);
   background-color: var(--background-color); padding: 0.8rem 1rem;
   font-family: var(--font-family) !important; transition: all 0.3s;
   resize: none; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
div[data-testid="stChatInput"] textarea:focus {
   border-color: var(--primary-color);
   box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3); transform: translateY(-1px);
}
div[data-testid="stChatInput"] button {
   background-color: var(--primary-color) !important;
   border-radius: 12px !important; fill: white !important;
   padding: 0.7rem !important; box-shadow: var(--box-shadow-sm);
   transition: all 0.3s; border: none !important;
}
div[data-testid="stChatInput"] button:hover {
   background-color: var(--primary-color-darker) !important;
   transform: translateY(-2px); box-shadow: 0 3px 6px rgba(59, 130, 246, 0.2);
}
div[data-testid="stChatInput"] button:disabled {
   background-color: #9CA3AF !important; transform: none; box-shadow: none;
}
</style>
""", unsafe_allow_html=True)

prompt = st.chat_input("Posez votre question ou tapez /search [recherche web]...")

# --- Traitement du nouveau prompt ---
if prompt:
   user_msg = {"role": "user", "content": prompt, "id": datetime.now().isoformat()}
   st.session_state.messages.append(user_msg)
   save_current_conversation()
   if 'html_download_data' in st.session_state: del st.session_state.html_download_data
   if 'single_message_download' in st.session_state: del st.session_state.single_message_download
   if 'show_copy_content' in st.session_state: del st.session_state.show_copy_content
   st.rerun()

# --- LOGIQUE DE RÉPONSE / RECHERCHE / ANALYSE ---
action_to_process = None
if st.session_state.messages and 'expert_advisor' in st.session_state:
   last_message = st.session_state.messages[-1]
   msg_id = last_message.get("id", str(last_message.get("content")))
   if msg_id not in st.session_state.processed_messages:
       action_to_process = last_message

if action_to_process and action_to_process.get("role") == "user":
   msg_id = action_to_process.get("id", str(action_to_process.get("content")))
   st.session_state.processed_messages.add(msg_id)
   user_content = action_to_process.get("content", "")

   is_search_command = False
   search_query = ""
   if user_content.strip().lower().startswith("/search "):
       is_search_command = True
       search_query = user_content[len("/search "):].strip()
   elif user_content.strip().lower() == "/search":
       is_search_command = True
       search_query = ""

   files_for_analysis = st.session_state.get("files_to_analyze", [])
   is_analysis_request = action_to_process.get("id", "").startswith("analyze_") and files_for_analysis

   if is_analysis_request:
       with st.chat_message("assistant", avatar="🏗️"):
           # Le message utilisateur pour l'analyse est déjà affiché.
           # On affiche ici directement le résultat.
           with st.spinner("Analyse des documents..."):
               try:
                   history_context = [m for m in st.session_state.messages[:-1] if m.get("role") != "system"]
                   analysis_response_text, analysis_details_obj = st.session_state.expert_advisor.analyze_documents(files_for_analysis, history_context)
                   
                   # Utiliser la fonction display_analysis_result pour l'affichage
                   display_analysis_result(analysis_response_text, analysis_details_obj)
                   
                   # Sauvegarder la réponse textuelle brute dans l'historique
                   st.session_state.messages.append({
                       "role": "assistant", 
                       "content": analysis_response_text,
                       "analysis_response": True # Marqueur pour potentiel rendu spécial
                   })
                   st.success("Analyse terminée.")
                   if "files_to_analyze" in st.session_state:
                       del st.session_state.files_to_analyze
               except Exception as e:
                   error_msg = f"Erreur durant l'analyse des fichiers: {e}"
                   st.error(error_msg)
                   st.exception(e)
                   st.session_state.messages.append({"role": "assistant", "content": f"Désolé, une erreur s'est produite lors de l'analyse: {type(e).__name__}"})
                   if "files_to_analyze" in st.session_state:
                       del st.session_state.files_to_analyze
       save_current_conversation()
       st.rerun()

   elif is_search_command:
       query = search_query.strip()
       if not query:
           error_msg = "Commande `/search` vide. Veuillez fournir un terme de recherche."
           with st.chat_message("assistant", avatar="⚠️"): # ou "🏗️"
               st.warning(error_msg)
           st.session_state.messages.append({"role": "assistant", "content": error_msg})
           save_current_conversation()
           st.rerun()
       else:
           with st.chat_message("assistant", avatar="🔎"):
               with st.spinner(f"Recherche web pour: '{html.escape(query)}'"):
                   try:
                       search_result = st.session_state.expert_advisor.perform_web_search(query)
                       st.markdown(f"""
                       <div class="search-result-container" style="animation: fadeIn 0.6s ease-out;">
                           <div style="display: flex; align-items: center; margin-bottom: 10px; color: #16a34a; font-weight: 600;">
                               <span style="margin-right: 8px; font-size: 1.2em;">🔎</span>
                               <span>Résultats de recherche</span>
                           </div>
                       """, unsafe_allow_html=True)
                       st.markdown(search_result, unsafe_allow_html=False) # search_result est déjà en Markdown
                       st.markdown("</div>", unsafe_allow_html=True)
                       st.session_state.messages.append({
                           "role": "search_result", # ou "assistant" mais "search_result" est plus spécifique
                           "content": search_result,
                           "id": f"search_result_{datetime.now().isoformat()}"
                       })
                   except Exception as e:
                       error_msg = f"Erreur lors de la recherche web: {str(e)}"
                       st.error(error_msg)
                       st.session_state.messages.append({
                           "role": "assistant",
                           "content": f"Désolé, une erreur s'est produite lors de la recherche web: {type(e).__name__}",
                           "id": f"search_error_{datetime.now().isoformat()}"
                       })
       save_current_conversation()
       st.rerun()

   else: # Traiter comme chat normal
       with st.chat_message("assistant", avatar="🏗️"):
           placeholder = st.empty()
           with st.spinner("L'expert réfléchit..."):
               try:
                   history_for_claude = [
                       msg for msg in st.session_state.messages[:-1]
                       if msg.get("role") in ["user", "assistant", "search_result"]
                   ]
                   response_content = st.session_state.expert_advisor.obtenir_reponse(user_content, history_for_claude)
                   placeholder.markdown(response_content, unsafe_allow_html=False)
                   st.session_state.messages.append({"role": "assistant", "content": response_content})
                   save_current_conversation()
                   st.rerun()
               except Exception as e:
                   error_msg = f"Erreur lors de l'obtention de la réponse de Claude: {e}"
                   print(error_msg)
                   st.exception(e)
                   placeholder.error(f"Désolé, une erreur technique s'est produite avec l'IA ({type(e).__name__}).")
                   st.session_state.messages.append({"role": "assistant", "content": f"Erreur technique avec l'IA ({type(e).__name__})."})
                   save_current_conversation()
                   st.rerun()

# --- Footer --- 
st.markdown("""
<div class="footer-container">
   <div class="copyright">© 2025 Desmarais & Gagné - Développé par Sylvain Leduc</div>
</div>
""", unsafe_allow_html=True)
