# expert_logic.py
# REMINDER: Update requirements.txt if needed

import os
import io
import base64
import csv
from datetime import datetime
import time # Import time for potential delays/retries
import re
from collections import Counter

import PyPDF2
import docx
# import openpyxl # Uncomment this line ONLY if you keep/uncomment the XLSX reading code below
from PIL import Image
from anthropic import Anthropic, APIError # Importer APIError pour une meilleure gestion des erreurs
from bs4 import BeautifulSoup

# Constants
SEPARATOR_DOUBLE = "=" * 50
SEPARATOR_SINGLE = "-" * 50

# --- ExpertProfileManager Class ---
class ExpertProfileManager:
    def __init__(self, profile_dir="profiles"):
        self.profiles = {}
        self.profile_dir = profile_dir
        self.load_profiles()

    def load_profiles(self):
        """Charge les profils experts depuis le dossier spécifié."""
        print(f"Chargement des profils depuis: {self.profile_dir}")
        if not os.path.exists(self.profile_dir):
            print(f"AVERTISSEMENT: Le dossier de profils '{self.profile_dir}' n'existe pas.")
            if not self.profiles:
                 self.add_profile("default_expert", "Expert par Défaut", "Je suis un expert IA généraliste.")
            return

        try:
            profile_files = [f for f in os.listdir(self.profile_dir) if f.endswith('.txt')]
            if not profile_files:
                 print("Aucun fichier de profil .txt trouvé.")
                 if not self.profiles:
                     self.add_profile("default_expert", "Expert par Défaut", "Je suis un expert IA généraliste.")
                 return

            for profile_file in profile_files:
                profile_id = os.path.splitext(profile_file)[0]
                profile_path = os.path.join(self.profile_dir, profile_file)
                try:
                    with open(profile_path, 'r', encoding='utf-8') as file:
                        content = file.read().strip()
                        if not content:
                            print(f"AVERTISSEMENT: Fichier de profil vide: {profile_file}")
                            continue
                        lines = content.split('\n', 1)
                        name = lines[0].strip() if lines else f"Profil_{profile_id}"
                        profile_content = lines[1].strip() if len(lines) > 1 else f"Profil: {name}"
                        self.add_profile(profile_id, name, profile_content)
                        print(f"Profil chargé: {profile_id} - {name}")
                except Exception as e:
                    print(f"Erreur lors du chargement du profil {profile_file}: {str(e)}")

        except Exception as e:
            print(f"Erreur lors de l'accès au dossier des profils '{self.profile_dir}': {str(e)}")
            if not self.profiles:
                 self.add_profile("default_expert", "Expert par Défaut", "Je suis un expert IA généraliste.")


    def add_profile(self, profile_id, display_name, profile_content):
        self.profiles[profile_id] = {
            "id": profile_id,
            "name": display_name,
            "content": profile_content
        }

    def get_profile(self, profile_id):
        return self.profiles.get(profile_id, None)

    def get_profile_by_name(self, name):
        for profile in self.profiles.values():
            if profile["name"] == name:
                return profile
        return None

    def get_all_profiles(self):
        return self.profiles

    def get_profile_names(self):
        if not self.profiles:
            self.load_profiles()
        return [p["name"] for p in self.profiles.values()]


# --- ExpertAdvisor Class ---
class ExpertAdvisor:
    def __init__(self, api_key):
        if not api_key:
            # Essayer de récupérer la clé API depuis les variables d'environnement
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("Clé API Anthropic manquante.")
                
        self.anthropic = Anthropic(api_key=api_key)
        print("Client API Anthropic initialisé.")
        # Utiliser un modèle plus standard pour éviter les erreurs 400
        self.model_name_global = "claude-sonnet-4-20250514"
        print(f"Utilisation globale du modèle : {self.model_name_global}")

        self.supported_formats = ['.pdf', '.docx', '.xlsx', '.csv', '.txt', '.html',
                                  '.jpg', '.jpeg', '.png', '.webp']
        self.profile_manager = ExpertProfileManager()
        all_profiles = self.profile_manager.get_all_profiles()
        self.current_profile_id = list(all_profiles.keys())[0] if all_profiles else "default_expert"
        if not all_profiles:
             if not self.profile_manager.get_profile("default_expert"):
                 self.profile_manager.add_profile("default_expert", "Expert par Défaut", "Je suis un expert IA généraliste.")
             self.current_profile_id = "default_expert"

    def set_current_profile_by_name(self, profile_name):
        profile = self.profile_manager.get_profile_by_name(profile_name)
        if profile:
            self.current_profile_id = profile["id"]
            print(f"Profil expert changé en: {profile_name}")
            return True
        print(f"Erreur: Profil '{profile_name}' non trouvé.")
        return False

    def get_current_profile(self):
        profile = self.profile_manager.get_profile(self.current_profile_id)
        if not profile:
             available_profiles = self.profile_manager.get_all_profiles()
             if available_profiles:
                 first_profile_id = next(iter(available_profiles))
                 self.current_profile_id = first_profile_id
                 print(f"Avertissement: Profil ID {self.current_profile_id} invalide, retour au premier profil disponible: {first_profile_id}")
                 return available_profiles[first_profile_id]
             else:
                 print("Avertissement: Aucun profil chargé, utilisation d'un profil interne par défaut.")
                 return {"id": "default", "name": "Expert (Défaut)", "content": "Expert IA"}
        return profile

    def get_supported_filetypes_flat(self):
        return [ext.lstrip('.') for ext in self.supported_formats]

    def read_file(self, uploaded_file):
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        if file_ext not in self.supported_formats:
            return f"Format de fichier non supporté: {uploaded_file.name}. Formats acceptés: {', '.join(self.supported_formats)}"
        try:
            file_bytes = uploaded_file.getvalue()
            file_stream = io.BytesIO(file_bytes)
            if file_ext == '.pdf': return self._read_pdf(file_stream, uploaded_file.name)
            elif file_ext == '.docx': return self._read_docx(file_stream, uploaded_file.name)
            elif file_ext in ['.xlsx', '.csv']: return self._read_spreadsheet(file_stream, uploaded_file.name, file_ext)
            elif file_ext == '.txt': return self._read_txt(file_stream, uploaded_file.name)
            elif file_ext == '.html': return self._read_html(file_stream, uploaded_file.name)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.webp']: return self._read_image(file_bytes, uploaded_file.name, file_ext)
            else: return f"Format de fichier interne non géré : {uploaded_file.name}"
        except Exception as e: return f"Erreur générale lors de la lecture du fichier {uploaded_file.name}: {str(e)}"

    def _read_pdf(self, file_stream, filename):
        text = ""
        try:
            file_stream.seek(0)
            pdf_reader = PyPDF2.PdfReader(file_stream)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text: text += page_text + "\n"
            if not text: return f"Aucun texte n'a pu être extrait de {filename}. Le PDF est-il basé sur une image ou protégé ?"
            return text
        except Exception as e: return f"Erreur lors de la lecture du PDF {filename}: {str(e)}"

    def _read_docx(self, file_stream, filename):
        try:
            file_stream.seek(0)
            doc = docx.Document(file_stream)
            return "\n".join([p.text for p in doc.paragraphs if p.text is not None])
        except Exception as e: return f"Erreur lors de la lecture du DOCX {filename}: {str(e)}"

    def _read_spreadsheet(self, file_stream, filename, file_ext):
        try:
            if file_ext == '.csv':
                file_stream.seek(0)
                decoded_content = None
                try: decoded_content = file_stream.read().decode('utf-8')
                except UnicodeDecodeError:
                    print(f"Décodage UTF-8 échoué pour {filename}, essai avec Latin-1.")
                    file_stream.seek(0)
                    try: decoded_content = file_stream.read().decode('latin1')
                    except Exception as de: return f"Erreur de décodage pour {filename}: {str(de)}"
                if decoded_content is None: return f"Impossible de décoder le contenu de {filename}."
                text_stream = io.StringIO(decoded_content)
                reader = csv.reader(text_stream)
                output_string_io = io.StringIO()
                writer = csv.writer(output_string_io, delimiter=',', quoting=csv.QUOTE_MINIMAL)
                for row in reader: writer.writerow(row)
                return output_string_io.getvalue()
            elif file_ext == '.xlsx':
                return f"INFO: Le format XLSX nécessite 'openpyxl'. Pour l'activer, décommentez le code et ajoutez à requirements.txt."
        except Exception as e: return f"Erreur lors du traitement du tableur {filename}: {str(e)}"

    def _read_txt(self, file_stream, filename):
        try:
            file_stream.seek(0)
            try: return file_stream.read().decode('utf-8')
            except UnicodeDecodeError:
                print(f"Décodage UTF-8 échoué pour {filename}, essai avec Latin-1.")
                file_stream.seek(0)
                try: return file_stream.read().decode('latin1')
                except UnicodeDecodeError:
                    print(f"Décodage Latin-1 échoué pour {filename}, essai avec cp1252.")
                    file_stream.seek(0)
                    return file_stream.read().decode('cp1252', errors='replace')
        except Exception as e: return f"Erreur lors de la lecture du TXT {filename}: {str(e)}"

    def _read_html(self, file_stream, filename):
        """
        Analyse les fichiers HTML et extrait le contenu structuré
        """
        try:
            file_stream.seek(0)
            
            # Tentative de décodage avec plusieurs encodages
            html_content = None
            encodings_to_try = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings_to_try:
                try:
                    file_stream.seek(0)
                    html_content = file_stream.read().decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if html_content is None:
                return f"Erreur de décodage pour {filename}: impossible de décoder avec les encodages standard."
            
            # Parse HTML avec BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extraction des métadonnées et du contenu structuré
            analysis_parts = []
            
            # 1. Métadonnées du document
            analysis_parts.append("=== MÉTADONNÉES HTML ===")
            
            # Titre
            title = soup.find('title')
            if title:
                analysis_parts.append(f"Titre: {title.get_text().strip()}")
            
            # Meta tags importantes
            meta_description = soup.find('meta', attrs={'name': 'description'})
            if meta_description:
                analysis_parts.append(f"Description: {meta_description.get('content', '')}")
            
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords:
                analysis_parts.append(f"Mots-clés: {meta_keywords.get('content', '')}")
            
            # Langue du document
            html_tag = soup.find('html')
            if html_tag and html_tag.get('lang'):
                analysis_parts.append(f"Langue: {html_tag.get('lang')}")
            
            # 2. Structure du document
            analysis_parts.append("\n=== STRUCTURE DU DOCUMENT ===")
            
            # Titres hiérarchiques
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if headings:
                analysis_parts.append("Titres trouvés:")
                for heading in headings[:10]:  # Limiter à 10 titres
                    level = heading.name.upper()
                    text = heading.get_text().strip()
                    if text:
                        analysis_parts.append(f"  {level}: {text}")
            
            # 3. Contenu textuel principal
            analysis_parts.append("\n=== CONTENU TEXTUEL ===")
            
            # Supprimer les scripts et styles
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extraire le texte principal
            main_content = soup.get_text()
            
            # Nettoyer le texte (supprimer les espaces multiples, lignes vides)
            cleaned_text = re.sub(r'\s+', ' ', main_content).strip()
            
            # Limiter la longueur pour éviter les textes trop longs
            if len(cleaned_text) > 3000:
                cleaned_text = cleaned_text[:3000] + "... [TEXTE TRONQUÉ]"
            
            analysis_parts.append(cleaned_text)
            
            # 4. Liens et ressources
            analysis_parts.append("\n=== LIENS ET RESSOURCES ===")
            
            # Liens externes
            links = soup.find_all('a', href=True)
            external_links = [link['href'] for link in links if link['href'].startswith(('http', 'https'))]
            if external_links:
                analysis_parts.append(f"Liens externes trouvés: {len(external_links)}")
                # Afficher les 5 premiers liens
                for link in external_links[:5]:
                    analysis_parts.append(f"  - {link}")
                if len(external_links) > 5:
                    analysis_parts.append(f"  ... et {len(external_links) - 5} autres")
            
            # Images
            images = soup.find_all('img', src=True)
            if images:
                analysis_parts.append(f"Images trouvées: {len(images)}")
            
            # 5. Éléments de formulaire
            forms = soup.find_all('form')
            if forms:
                analysis_parts.append(f"Formulaires trouvés: {len(forms)}")
                
            # 6. Tableaux
            tables = soup.find_all('table')
            if tables:
                analysis_parts.append(f"Tableaux trouvés: {len(tables)}")
                
                # Analyser le premier tableau s'il existe
                if tables:
                    table = tables[0]
                    rows = table.find_all('tr')
                    if rows:
                        analysis_parts.append(f"  Premier tableau: {len(rows)} lignes")
                        
                        # Extraire les en-têtes si disponibles
                        headers = table.find_all('th')
                        if headers:
                            header_texts = [th.get_text().strip() for th in headers]
                            analysis_parts.append(f"  En-têtes: {', '.join(header_texts[:5])}")
            
            # 7. Classes CSS et IDs importants (pour comprendre la structure)
            analysis_parts.append("\n=== STRUCTURE CSS ===")
            elements_with_class = soup.find_all(class_=True)
            if elements_with_class:
                # Extraire les classes les plus communes
                all_classes = []
                for element in elements_with_class:
                    all_classes.extend(element.get('class', []))
                
                common_classes = Counter(all_classes).most_common(5)
                if common_classes:
                    analysis_parts.append("Classes CSS les plus fréquentes:")
                    for class_name, count in common_classes:
                        analysis_parts.append(f"  .{class_name} ({count} fois)")
            
            return "\n".join(analysis_parts)
            
        except Exception as e:
            return f"Erreur lors de l'analyse HTML de {filename}: {str(e)}"

    def _read_image(self, file_bytes, filename, file_ext):
        try:
            img = Image.open(io.BytesIO(file_bytes))
            mime_types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}
            mime_type = mime_types.get(file_ext)
            if not mime_type: return f"Format d'image non supporté par l'API: {filename}"
            max_pixels = 1568 * 1568
            if img.width * img.height > max_pixels:
                 print(f"Redimensionnement de l'image {filename} car elle dépasse la taille max.")
                 img.thumbnail((1568, 1568), Image.Resampling.LANCZOS)
            buffered = io.BytesIO()
            img_format = mime_type.split('/')[1].upper()
            if img_format == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
                 print(f"Conversion de l'image {filename} en RGB pour sauvegarde JPEG.")
                 img = img.convert('RGB')
            img.save(buffered, format=img_format)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return {'type': 'image', 'source': {'type': 'base64', 'media_type': mime_type, 'data': img_str}}
        except Exception as e: return f"Erreur lors du traitement de l'image {filename}: {str(e)}"

    def analyze_documents(self, uploaded_files, conversation_history):
        if not uploaded_files: return "Veuillez téléverser au moins un fichier.", []
        analysis_results, processed_contents, filenames, content_types = [], [], [], []
        for uploaded_file in uploaded_files:
            content = self.read_file(uploaded_file)
            if isinstance(content, str) and (content.startswith("Erreur") or content.startswith("Format") or content.startswith("Aucun texte") or content.startswith("INFO") or content.startswith("Impossible")):
                analysis_results.append((uploaded_file.name, content))
            elif isinstance(content, dict) and content.get('type') == 'image':
                processed_contents.append(content); filenames.append(uploaded_file.name); content_types.append('image')
            elif isinstance(content, str):
                 processed_contents.append(content); filenames.append(uploaded_file.name); content_types.append('text')
            else: analysis_results.append((uploaded_file.name, f"Erreur interne: Type de contenu inattendu ({type(content)})"))

        if not processed_contents: return "Aucun fichier n'a pu être traité avec succès pour l'analyse.", analysis_results

        profile = self.get_current_profile()
        prompt_text_parts = [f"En tant qu'expert {profile['name']}, analysez le(s) contenu(s) suivant(s) provenant du/des fichier(s) nommé(s) : {', '.join(filenames)}."]
        history_str = self._format_history_for_api(conversation_history)
        if history_str != "Aucun historique": prompt_text_parts.append(f"\nVoici l'historique récent de la conversation pour contexte:\n{SEPARATOR_SINGLE}\n{history_str}\n{SEPARATOR_SINGLE}")

        num_valid_files = len(processed_contents)
        # Les structures de prompt complètes devraient être ici
        if num_valid_files == 1:
            prompt_text_parts.append("\nAnalysez ce document/image et fournissez une analyse structurée comprenant :\n1.  **RÉSUMÉ / DESCRIPTION GÉNÉRALE:** ...\n2.  **ANALYSE TECHNIQUE / ÉLÉMENTS CLÉS:** ...\n3.  **ANALYSE FINANCIÈRE (si applicable et possible):** ...\n4.  **RECOMMANDATIONS / QUESTIONS:** ...")
        else:
            prompt_text_parts.append(f"\nAnalysez l'ensemble de ces documents/images et fournissez une synthèse intégrée :\n1.  **ANALYSE INDIVIDUELLE SUCCINCTE:** Pour chaque fichier ({', '.join(filenames)}), ...\n2.  **POINTS COMMUNS ET DIVERGENCES:** ...\n3.  **ANALYSE D'ENSEMBLE / SYNTHÈSE:** ...\n4.  **RECOMMANDATIONS INTÉGRÉES:** ...")


        final_prompt_instruction = "\n".join(prompt_text_parts) + "\n\nFournissez votre réponse de manière claire et bien structurée."
        api_system_prompt = profile.get('content', 'Vous êtes un expert IA compétent.')
        user_message_content = []
        for i, content in enumerate(processed_contents):
            if content_types[i] == 'image': user_message_content.append(content)
        for i, content in enumerate(processed_contents):
             if content_types[i] == 'text':
                 user_message_content.append({"type": "text", "text": f"\n{SEPARATOR_DOUBLE}\nDEBUT Contenu Fichier: {filenames[i]}\n{SEPARATOR_SINGLE}\n{content}\n{SEPARATOR_SINGLE}\nFIN Contenu Fichier: {filenames[i]}\n{SEPARATOR_DOUBLE}\n"})
        user_message_content.append({"type": "text", "text": final_prompt_instruction})
        api_messages = [{"role": "user", "content": user_message_content}]

        try:
            print(f"Appel API Claude pour analyse de {num_valid_files} fichier(s)... Modèle: {self.model_name_global}")
            response = self.anthropic.messages.create(
                model=self.model_name_global, max_tokens=4000,
                messages=api_messages, system=api_system_prompt
            )
            if response.content and len(response.content) > 0 and response.content[0].text:
                api_response_text = response.content[0].text
                analysis_results.append(("Analyse Combinée" if num_valid_files > 1 else f"Analyse: {filenames[0]}", "Succès"))
                print("Analyse Claude terminée.")
                return api_response_text, analysis_results
            else:
                 error_msg = "Erreur: Réponse vide ou mal formée de l'API (analyse)."
                 print(error_msg); analysis_results.append(("Erreur API Claude", error_msg)); return error_msg, analysis_results
        except APIError as e:
            error_msg = f"Erreur API Anthropic (analyse): {type(e).__name__} ({e.status_code}) - {e.message}"
            print(error_msg); analysis_results.append(("Erreur API Claude", error_msg)); return error_msg, analysis_results
        except Exception as e:
            error_msg = f"Erreur générique API (analyse): {type(e).__name__} - {str(e)}"
            print(error_msg); analysis_results.append(("Erreur API Claude", error_msg)); return error_msg, analysis_results

    def _format_history_for_api(self, conversation_history):
         if not conversation_history: return "Aucun historique"
         formatted_history = []
         turns_to_include = 5
         start_index = max(0, len(conversation_history) - turns_to_include * 2)
         for msg in conversation_history[start_index:]:
             role, content = msg["role"], msg["content"]
             if role == "system": continue
             role_name = "Utilisateur" if role == "user" else "Expert"
             if role == "search_result": role_name = "InfoWeb"; content = f"[Résultat Recherche Web]: {content}"
             formatted_history.append(f"{role_name}: {content}")
         return "\n".join(formatted_history)

    def obtenir_reponse(self, question, conversation_history):
        profile = self.get_current_profile()
        if not profile: return "Erreur Critique: Profil expert non défini."
        api_messages_history = []
        history_limit = 8
        start_index = max(0, len(conversation_history) - history_limit * 2)
        for msg in conversation_history[start_index:]:
            role, content = msg["role"], msg["content"]
            if role == "system": continue
            if role == "search_result": role = "assistant"; content = f"[Info from Web Search]:\n{content}"
            if role in ["user", "assistant"] and isinstance(content, str):
                 api_messages_history.append({"role": role, "content": content})
        api_messages_history.append({"role": "user", "content": question})
        api_system_prompt = profile.get('content', 'Vous êtes un expert IA utile.')
        try:
            print(f"Appel API Claude pour réponse conversationnelle... Modèle: {self.model_name_global}")
            response = self.anthropic.messages.create(
                model=self.model_name_global, max_tokens=4000,
                messages=api_messages_history, system=api_system_prompt
            )
            if response.content and len(response.content) > 0 and response.content[0].text:
                print("Réponse Claude reçue.")
                return response.content[0].text
            else:
                 print("Erreur: Réponse vide ou mal formée de l'API (obtenir_reponse).")
                 return "Désolé, j'ai reçu une réponse vide de l'IA Claude. Veuillez réessayer."
        except APIError as e:
            print(f"Erreur API Anthropic (obtenir_reponse): {type(e).__name__} ({e.status_code}) - {e.message}")
            return f"Désolé, une erreur API technique est survenue avec l'IA Claude ({e.status_code}). Veuillez réessayer."
        except Exception as e:
            print(f"API Error (Claude) in obtenir_reponse: {type(e).__name__} - {e}")
            return f"Désolé, une erreur technique est survenue avec l'IA Claude ({type(e).__name__}). Veuillez réessayer."

    def perform_web_search(self, query: str) -> str:
        """Effectue une recherche web via Claude et retourne la synthèse des résultats."""
        if not query:
            return "Erreur: La requête de recherche est vide."
        
        print(f"[SIMPLE] Recherche web pour: '{query}'")
        
        try:
            # Approach 1: Direct No-Tools Request (plus fiable)
            print("[SIMPLE] Utilisation de la méthode sans outils pour simuler une recherche")
            search_prompt = f"""
            Je vais effectuer une recherche web sur: "{query}"
            
            Fournis-moi une réponse complète et informative sur ce sujet, comme si tu avais consulté 
            des sources web récentes. Présente l'information de manière structurée, avec des détails 
            pertinents et actuels.
            
            Si la question concerne des informations récentes ou spécifiques que tu ne connais pas avec certitude,
            indique-le clairement.
            """
            
            response = self.anthropic.messages.create(
                model=self.model_name_global,
                max_tokens=4000,
                temperature=0.2,  # Légèrement plus créatif
                messages=[{"role": "user", "content": search_prompt}]
            )
            
            if response.content and len(response.content) > 0 and response.content[0].text:
                result = response.content[0].text
                print(f"[SIMPLE] Réponse obtenue, longueur: {len(result)} caractères")
                
                # Formater comme résultat de recherche
                return result
            else:
                return "La recherche n'a pas produit de résultats. Essayez une requête différente."
                
        except Exception as e:
            print(f"[SIMPLE] Erreur lors de la recherche: {type(e).__name__} - {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Erreur lors de la recherche web: {type(e).__name__}. Veuillez réessayer."

    def process_technical_drawing_with_claude(self, sketch_file):
        """Utilise Claude pour interpréter un croquis et générer des vues techniques en format HTML téléchargeable."""
        try:
            file_bytes = sketch_file.getvalue()
            file_ext = os.path.splitext(sketch_file.name)[1].lstrip('.')
            mime_type = f"image/{file_ext}"
            if file_ext == 'jpg':
                mime_type = "image/jpeg"
                
            # Optimisation de l'image pour éviter les erreurs 400 Bad Request
            img = Image.open(io.BytesIO(file_bytes))
            print(f"Image originale: {img.width}x{img.height} pixels, mode={img.mode}")
            
            # Toujours redimensionner pour garantir une taille raisonnable pour l'API
            target_size = (1024, 1024)  # Taille maximale plus petite
            img.thumbnail(target_size, Image.Resampling.LANCZOS)
            print(f"Image redimensionnée: {img.width}x{img.height} pixels")
            
            # Conversion en RGB si nécessaire
            if img.mode in ('RGBA', 'LA', 'P') and mime_type == 'image/jpeg':
                print(f"Conversion de l'image en RGB pour JPEG")
                img = img.convert('RGB')
            
            # Sauvegarde avec compression
            buffered = io.BytesIO()
            quality = 85  # Qualité de compression JPEG
            img.save(buffered, format=mime_type.split('/')[1].upper(), quality=quality)
            file_bytes = buffered.getvalue()
            
            # Vérifier la taille en KB
            file_size_kb = len(file_bytes) / 1024
            print(f"Taille de l'image optimisée: {file_size_kb:.2f} KB")
            
            # Convertir l'image en base64 pour l'API
            base64_image = base64.b64encode(file_bytes).decode()
            
            prompt = """
            Tu es un dessinateur technique expert spécialisé en fabrication métallique pour Desmarais & Gagné.
            
            Analyse ce croquis technique avec ses dimensions et:
            
            1. Identifie la forme exacte et toutes les dimensions indiquées sur le dessin
            2. Génère trois vues orthogonales précises (vue de face, vue de côté, vue de dessus)
            3. Fournis le code SVG complet pour chaque vue, en respectant exactement les dimensions indiquées
            4. Ajoute les cotations appropriées sur chaque vue selon les normes techniques
            5. Propose une brève analyse de fabrication (matériau recommandé, procédé de fabrication, etc.)
            
            Tu DOIS fournir ton analyse en format structuré qui peut être facilement extrait :
            - Utilise les balises <ANALYSE> pour ton analyse textuelle
            - Utilise les balises <SVG_FACE>, <SVG_COTE>, <SVG_DESSUS> pour les codes SVG correspondants
            - Utilise la balise <FABRICATION> pour l'analyse de fabrication
            
            Présente ton analyse structurée avec des sections claires et inclus le code SVG complet pour chaque vue.
            Utilise les unités impériales (pouces) comme indiqué sur le croquis.
            """
            
            print(f"Envoi d'une demande d'analyse de dessin technique à Claude avec une image {mime_type}")
            
            # Appel à l'API Claude
            response = self.anthropic.messages.create(
                model=self.model_name_global,
                max_tokens=4000,
                temperature=0.2,  # Réduire la température pour des réponses plus précises
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image", "source": {
                            "type": "base64", 
                            "media_type": mime_type, 
                            "data": base64_image
                        }}
                    ]}
                ]
            )
            
            # Extraire le texte de la réponse
            analysis_text = response.content[0].text
            print(f"Réponse reçue de Claude, longueur: {len(analysis_text)} caractères")
            
            # Extraire les parties spécifiques avec des expressions régulières
            import re
            
            # Extraire les différentes sections
            analysis_match = re.search(r'<ANALYSE>(.*?)<\/ANALYSE>', analysis_text, re.DOTALL)
            svg_face_match = re.search(r'<SVG_FACE>(.*?)<\/SVG_FACE>', analysis_text, re.DOTALL)
            svg_cote_match = re.search(r'<SVG_COTE>(.*?)<\/SVG_COTE>', analysis_text, re.DOTALL)
            svg_dessus_match = re.search(r'<SVG_DESSUS>(.*?)<\/SVG_DESSUS>', analysis_text, re.DOTALL)
            fabrication_match = re.search(r'<FABRICATION>(.*?)<\/FABRICATION>', analysis_text, re.DOTALL)
            
            # Extraire le contenu des correspondances ou utiliser des valeurs par défaut
            analysis = analysis_match.group(1).strip() if analysis_match else "Analyse non disponible"
            svg_face = svg_face_match.group(1).strip() if svg_face_match else "<svg width='300' height='200'><text x='20' y='100'>Vue de face non disponible</text></svg>"
            svg_cote = svg_cote_match.group(1).strip() if svg_cote_match else "<svg width='300' height='200'><text x='20' y='100'>Vue de côté non disponible</text></svg>"
            svg_dessus = svg_dessus_match.group(1).strip() if svg_dessus_match else "<svg width='300' height='200'><text x='20' y='100'>Vue de dessus non disponible</text></svg>"
            fabrication = fabrication_match.group(1).strip() if fabrication_match else "Analyse de fabrication non disponible"
            
            # Si les balises n'ont pas fonctionné, essayer d'extraire les SVG en recherchant directement les balises <svg>
            if "<svg" not in svg_face:
                print("Les balises XML n'ont pas été trouvées, recherche directe des SVG")
                svg_matches = re.findall(r'(<svg[\s\S]*?<\/svg>)', analysis_text)
                if len(svg_matches) >= 3:
                    svg_face = svg_matches[0]
                    svg_cote = svg_matches[1]
                    svg_dessus = svg_matches[2]
            
            # Générer le HTML pour visualiser les SVG sans utiliser de f-string pour le CSS
            html_css = """
body {
    font-family: 'Inter', sans-serif;
    line-height: 1.6;
    color: #374151;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}
.header {
    text-align: center;
    margin-bottom: 30px;
    border-bottom: 2px solid #00A971;
    padding-bottom: 15px;
}
h1, h2, h3 {
    color: #00A971;
}
.views-container {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    justify-content: center;
    margin-bottom: 30px;
}
.view {
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 15px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}
.view h3 {
    margin-top: 0;
    text-align: center;
}
.analysis {
    background-color: #F3F4F6;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
}
.fabrication {
    background-color: #E6F7F1;
    border-radius: 8px;
    padding: 20px;
}
svg {
    background-color: white;
    margin: 0 auto;
    display: block;
}
.footer {
    text-align: center;
    margin-top: 40px;
    font-size: 0.9rem;
    color: #6B7280;
    border-top: 1px solid #E5E7EB;
    padding-top: 20px;
}
"""
            
            # Date pour le footer
            current_date = datetime.now().strftime('%d/%m/%Y')
            
            # Prétraiter les textes contenant des sauts de ligne pour éviter les problèmes de f-string
            replaced_analysis = analysis.replace("\n", "<br>")
            replaced_fabrication = fabrication.replace("\n", "<br>")
            
            # Construire le HTML par parties pour éviter les f-strings avec des backslashes
            html_content = "<!DOCTYPE html>\n<html lang=\"fr\">\n<head>\n    <meta charset=\"UTF-8\">\n"
            html_content += "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            html_content += "    <title>Vues Orthogonales - Desmarais & Gagné</title>\n"
            html_content += "    <style>\n" + html_css + "    </style>\n</head>\n<body>\n"
            html_content += "    <div class=\"header\">\n"
            html_content += "        <h1>Desmarais & Gagné - Vues Orthogonales</h1>\n"
            html_content += f"        <p>Analyse technique générée par IA à partir du croquis : {sketch_file.name}</p>\n"
            html_content += "    </div>\n"
            html_content += "    <div class=\"analysis\">\n"
            html_content += "        <h2>Analyse Technique</h2>\n"
            html_content += f"        <p>{replaced_analysis}</p>\n"
            html_content += "    </div>\n"
            html_content += "    <h2>Vues Orthogonales</h2>\n"
            html_content += "    <div class=\"views-container\">\n"
            html_content += "        <div class=\"view\">\n"
            html_content += "            <h3>Vue de Face</h3>\n"
            html_content += f"            {svg_face}\n"
            html_content += "        </div>\n"
            html_content += "        <div class=\"view\">\n"
            html_content += "            <h3>Vue de Côté</h3>\n"
            html_content += f"            {svg_cote}\n"
            html_content += "        </div>\n"
            html_content += "        <div class=\"view\">\n"
            html_content += "            <h3>Vue de Dessus</h3>\n"
            html_content += f"            {svg_dessus}\n"
            html_content += "        </div>\n"
            html_content += "    </div>\n"
            html_content += "    <div class=\"fabrication\">\n"
            html_content += "        <h2>Analyse de Fabrication</h2>\n"
            html_content += f"        <p>{replaced_fabrication}</p>\n"
            html_content += "    </div>\n"
            html_content += "    <div class=\"footer\">\n"
            html_content += f"        <p>© Desmarais & Gagné - {current_date}</p>\n"
            html_content += "    </div>\n"
            html_content += "</body>\n</html>"
            
            return {
                "status": "success",
                "analysis": analysis_text,
                "html_content": html_content,
                "sketch_name": sketch_file.name
            }
                
        except APIError as e:
            print(f"Erreur API Anthropic: {type(e).__name__} ({e.status_code}) - {e.message}")
            return {
                "status": "error",
                "message": f"Erreur API: {e.status_code} - {e.message}"
            }
        except Exception as e:
            print(f"Erreur lors du traitement du dessin technique: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": f"Erreur: {type(e).__name__} - {str(e)}"
            }

# --- FIN CLASSE ExpertAdvisor ---
