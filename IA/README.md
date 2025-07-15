---
title: Desmarais & Gagné AI
emoji: 🔧
colorFrom: green
colorTo: gray
sdk: streamlit
sdk_version: 1.30.0 # Assurez-vous que c'est cohérent avec requirements.txt
app_file: ia_app.py
pinned: false
---

# Desmarais & Gagné AI - Assistant Expert en Fabrication Métallique

Interface Web pour le système expert Desmarais & Gagné AI, construite avec Streamlit. Elle intègre l'API Anthropic Claude pour des conversations expertes et la recherche web intégrée.

## Fonctionnalités

*   Dialogue interactif avec un expert IA spécialisé (Anthropic Claude) dans la fabrication métallique.
*   **Recherche Web Intégrée:** Utilisez la commande `/search [votre requête]` pour obtenir des informations via la recherche web intégrée de Claude.
*   **Sélection de Profils:** Choisissez parmi différents profils d'experts (Expert en Fabrication Métallique, Expert en Soudure, etc.) pour adapter les réponses de Claude.
*   **Analyse de Documents:** Téléversez et analysez divers formats de fichiers (PDF, DOCX, CSV, TXT) et d'images (JPG, PNG, WEBP). L'expert Claude fournit des résumés, analyses et recommandations.
*   **Historique Persistant:** Sauvegarde et chargement des conversations via une base de données SQLite locale (`conversations.db`).
*   **Export HTML:** Générez un rapport HTML autonome de la conversation en cours, incluant les messages utilisateur, les réponses de l'expert et les résultats de recherche web synthétisés.
*   *(Note: Le support des fichiers Excel .xlsx dépend de l'inclusion de la bibliothèque `openpyxl` et de l'activation du code correspondant dans `expert_logic.py` pour rester sous les limites de taille de Hugging Face Spaces).*

## Setup et Lancement Local

1.  **Cloner le dépôt (si vous travaillez localement):**
    *   Depuis GitHub : `git clone <votre-repo-github-url>`
    *   Ou depuis Hugging Face : `git clone https://huggingface.co/spaces/<votre-user>/<votre-space-name>`
    *   `cd <nom-du-dossier>`

2.  **Créer un environnement virtuel (recommandé):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Sur Windows: venv\Scripts\activate
    ```

3.  **Installer les dépendances:**
    *   Assurez-vous que votre fichier `requirements.txt` est à jour.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurer les Clés API (Local):**
    *   Créez un dossier `.streamlit` à la racine du projet s'il n'existe pas.
    *   Dedans, créez un fichier `secrets.toml`.
    *   Ajoutez vos clés API dans `secrets.toml`:
        ```toml
        # .streamlit/secrets.toml

        # Clé API pour Anthropic Claude
        ANTHROPIC_API_KEY = "sk-ant-api03-VOTRE_CLE_API_ANTHROPIC_COMPLETE_ICI"

        # Mot de passe pour accéder à l'application
        APP_PASSWORD = "votre_mot_de_passe_ici"
        ```
    *   **Important:** Remplacez les valeurs par vos clés et ID réels.
    *   **Sécurité:** Assurez-vous que `.streamlit/secrets.toml` est bien listé dans votre `.gitignore` pour ne pas le partager accidentellement.

5.  **Lancer l'application Streamlit localement:**
    ```bash
    streamlit run ia_app.py
    ```
    L'application devrait s'ouvrir dans votre navigateur web.

## Déploiement sur Hugging Face Spaces

Ce dépôt est configuré pour être déployé automatiquement sur Hugging Face Spaces.

1.  **Prérequis :**
    *   Un compte Hugging Face.
    *   Le code poussé sur ce dépôt Hugging Face (ou un dépôt GitHub lié).

2.  **Configuration du Space :**
    *   Assurez-vous que le SDK sélectionné dans les paramètres du Space est "Streamlit".
    *   Vérifiez que `app_file` dans le bloc YAML en haut de ce README pointe bien vers `app.py`.
    *   Assurez-vous que `requirements.txt` contient toutes les dépendances nécessaires.

3.  **Configuration des Secrets :**
    *   Allez dans l'onglet "Settings" de votre Space sur Hugging Face.
    *   Naviguez jusqu'à la section "Repository secrets".
    *   Ajoutez **deux** secrets distincts :
        *   Secret 1:
            *   **Name:** `ANTHROPIC_API_KEY`
            *   **Secret value:** Collez votre clé API Anthropic complète (`sk-ant-...`).
        *   Secret 2:
            *   **Name:** `APP_PASSWORD`
            *   **Secret value:** Mot de passe pour accéder à l'application.
    *   Sauvegardez chaque secret. Le Space devrait redémarrer automatiquement pour prendre en compte les nouvelles variables d'environnement.

4.  **Lancement :**
    *   Hugging Face installera les dépendances depuis `requirements.txt` et lancera l'application `app.py`.
    *   Suivez le build dans les logs du Space. L'application sera accessible via l'URL publique de votre Space une fois le build terminé.

## Structure du Projet

*   `ia_app.py`: Interface utilisateur principale avec Streamlit. Gère le flux de l'application, l'état de session et les interactions utilisateur.
*   `expert_logic.py`: Contient la logique métier, notamment les classes `ExpertAdvisor` (interaction avec l'API Claude, traitement des fichiers et recherche web) et `ExpertProfileManager` (gestion des profils experts).
*   `conversation_manager.py`: Gère la persistance des conversations dans une base de données SQLite (`conversations.db`).
*   `profiles/`: Dossier contenant les fichiers `.txt` définissant les différents profils experts pour Claude.
*   `assets/`: Dossier pour les ressources statiques (ex: `logo.png`).
*   `requirements.txt`: Liste des dépendances Python nécessaires pour exécuter l'application.
*   `README.md`: Ce fichier (incluant la configuration Hugging Face YAML).
*   `style.css`: Fichier CSS externe pour personnaliser l'apparence de l'application Streamlit.
*   `.streamlit/secrets.toml`: (Local uniquement, doit être dans `.gitignore`) Stocke les clés API pour le développement local.
*   `.gitignore`: Spécifie les fichiers et dossiers ignorés par Git (essentiel pour ne pas commiter les secrets).
*   `conversations.db`: (Créé à l'exécution) La base de données SQLite où les conversations sont sauvegardées.
