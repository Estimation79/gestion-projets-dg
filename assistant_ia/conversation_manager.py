# conversation_manager.py
import sqlite3
import json
from datetime import datetime
import os

class ConversationManager:
    """Gère la sauvegarde et le chargement des conversations dans une base de données SQLite."""

    def __init__(self, db_path="conversations.db"):
        """Initialise le gestionnaire et crée la table si elle n'existe pas."""
        self.db_path = db_path
        # Assurer que le dossier pour la DB existe si db_path contient un chemin
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            print(f"Création du dossier pour la base de données: {db_dir}")

        print(f"Initialisation ConversationManager avec db: {self.db_path}")
        self._create_table()

    def _connect(self):
        """Établit une connexion à la base de données."""
        try:
            # isolation_level=None pour autocommit simple, ou gérer les transactions manuellement
            conn = sqlite3.connect(self.db_path, isolation_level=None)
            # Retourner les lignes comme des dictionnaires
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"Erreur de connexion à la base de données SQLite ({self.db_path}): {e}")
            raise # Renvoyer l'erreur pour que l'appelant puisse la gérer

    def _create_table(self):
        """Crée la table 'conversations' si elle n'existe pas."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        last_updated_at TEXT NOT NULL,
                        messages TEXT NOT NULL -- Stocke la liste des messages en JSON
                    )
                """)
                # print("Table 'conversations' vérifiée/créée.") # Décommentez pour debug
        except sqlite3.Error as e:
            print(f"Erreur lors de la création de la table 'conversations': {e}")

    def _generate_conversation_name(self, messages):
        """Génère un nom par défaut pour une conversation."""
        # Essayer de prendre les premiers mots du premier message utilisateur
        first_user_message = None
        for msg in messages:
            if msg.get("role") == "user" and msg.get("content"):
                first_user_message = msg["content"]
                break

        if first_user_message:
            # Prend les 5 premiers mots, ou moins s'il y en a moins
            name = " ".join(first_user_message.split()[:5])
            if len(first_user_message.split()) > 5:
                name += "..."
        else:
            # Fallback si pas de message utilisateur ou vide
            name = f"Consultation {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Éviter les noms trop longs
        return name[:80] # Limite arbitraire

    def save_conversation(self, conversation_id, messages, name=None):
        """Sauvegarde ou met à jour une conversation. Retourne l'ID de la conversation."""
        if not messages: # Ne pas sauvegarder une conversation vide
            return conversation_id # Retourner l'ID existant s'il y en avait un

        now_iso = datetime.now().isoformat()
        current_name = name # Initialiser current_name

        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                messages_json = json.dumps(messages) # Convertir la liste en chaîne JSON

                if conversation_id is not None:
                    # Tenter de mettre à jour une conversation existante
                    cursor.execute("SELECT name FROM conversations WHERE id = ?", (conversation_id,))
                    row = cursor.fetchone()

                    if row: # L'ID existe bien
                        if name is None: # Si aucun nom n'est fourni, on garde l'ancien
                            current_name = row['name']
                        else: # Sinon, on utilise le nouveau nom fourni
                            current_name = name

                        cursor.execute("""
                            UPDATE conversations
                            SET messages = ?, last_updated_at = ?, name = ?
                            WHERE id = ?
                        """, (messages_json, now_iso, current_name, conversation_id))
                        # print(f"Conversation {conversation_id} mise à jour.") # Décommentez pour debug
                        return conversation_id
                    else:
                        # L'ID fourni n'existe pas dans la base, on va donc créer une nouvelle entrée
                        print(f"Avertissement: ID {conversation_id} non trouvé pour mise à jour, création d'une nouvelle conversation.")
                        conversation_id = None # Forcer la création

                # Créer une nouvelle conversation si conversation_id est None ou était invalide
                if conversation_id is None:
                    if current_name is None: # Si aucun nom n'a été défini (ni fourni, ni récupéré)
                        current_name = self._generate_conversation_name(messages)
                    created_at = now_iso # Utiliser l'heure actuelle pour la création

                    cursor.execute("""
                        INSERT INTO conversations (name, created_at, last_updated_at, messages)
                        VALUES (?, ?, ?, ?)
                    """, (current_name, created_at, now_iso, messages_json))
                    new_id = cursor.lastrowid
                    # print(f"Nouvelle conversation {new_id} ('{current_name}') créée.") # Décommentez pour debug
                    return new_id

        except sqlite3.Error as e:
            print(f"Erreur SQLite lors de la sauvegarde de la conversation (ID: {conversation_id}): {e}")
            return conversation_id # Retourner l'ID original en cas d'erreur
        except json.JSONDecodeError as e:
            print(f"Erreur JSON lors de la sérialisation des messages pour sauvegarde: {e}")
            return conversation_id # Retourner l'ID original

    def load_conversation(self, conversation_id):
        """Charge les messages d'une conversation par son ID."""
        if conversation_id is None:
            return [] # Retourner une liste vide si aucun ID n'est fourni

        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT messages FROM conversations WHERE id = ?", (conversation_id,))
                row = cursor.fetchone()
                if row:
                    messages_json = row['messages']
                    messages = json.loads(messages_json) # Convertir JSON en liste Python
                    # print(f"Conversation {conversation_id} chargée.") # Décommentez pour debug
                    return messages
                else:
                    print(f"Aucune conversation trouvée avec l'ID {conversation_id}.")
                    return [] # Retourner une liste vide si l'ID n'est pas trouvé
        except sqlite3.Error as e:
            print(f"Erreur SQLite lors du chargement de la conversation {conversation_id}: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Erreur JSON lors du chargement des messages pour la conversation {conversation_id}: {e}")
            return [] # Retourner liste vide si les données sont corrompues

    def list_conversations(self, limit=50):
        """Retourne une liste des conversations récentes (id, name, last_updated_at)."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                # Sélectionner les champs nécessaires et trier par date de mise à jour décroissante
                cursor.execute("""
                    SELECT id, name, last_updated_at
                    FROM conversations
                    ORDER BY last_updated_at DESC
                    LIMIT ?
                """, (limit,))
                conversations = cursor.fetchall()
                # Convertir les objets Row en dictionnaires simples pour une utilisation facile
                return [dict(row) for row in conversations]
        except sqlite3.Error as e:
            print(f"Erreur SQLite lors de la récupération de la liste des conversations: {e}")
            return []

    def delete_conversation(self, conversation_id):
        """Supprime une conversation par son ID."""
        if conversation_id is None:
            return False
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    # print(f"Conversation {conversation_id} supprimée.") # Décommentez pour debug
                    return True
                else:
                    # print(f"Aucune conversation trouvée avec l'ID {conversation_id} à supprimer.") # Décommentez pour debug
                    return False
        except sqlite3.Error as e:
            print(f"Erreur SQLite lors de la suppression de la conversation {conversation_id}: {e}")
            return False
