# attachments_manager.py - Gestionnaire de Pièces Jointes pour Projets ERP DG Inc.
# VERSION COMPLÈTE CORRIGÉE POUR RENDER PERSISTENT DISK + CLÉS BOUTONS UNIQUES

import streamlit as st
import os
import uuid
import mimetypes
from datetime import datetime
from pathlib import Path
import hashlib
import shutil
from typing import List, Dict, Optional, Tuple
import base64
from PIL import Image
import io

class AttachmentsManager:
    """
    Gestionnaire de pièces jointes pour les projets ERP DG Inc.
    VERSION CORRIGÉE pour utiliser le persistent disk Render + clés boutons uniques
    """
    
    def __init__(self, db, storage_manager=None):
        self.db = db
        self.storage_manager = storage_manager
        
        # CORRIGÉ : Configuration robuste pour Render
        self.base_upload_dir = self._get_upload_directory()
        self._ensure_upload_directory()
        self._init_database_table()
        
        # NOUVEAU : Diagnostic au démarrage
        self._run_startup_diagnostic()
        
        # NOUVEAU : Nettoyer les liens brisés
        self._cleanup_broken_attachments()
        
        # Types de fichiers autorisés avec leurs catégories
        self.allowed_file_types = {
            # Documents
            'pdf': 'DOCUMENT',
            'doc': 'DOCUMENT', 'docx': 'DOCUMENT',
            'xls': 'DOCUMENT', 'xlsx': 'DOCUMENT',
            'txt': 'DOCUMENT', 'rtf': 'DOCUMENT',
            'odt': 'DOCUMENT', 'ods': 'DOCUMENT',
            'csv': 'DOCUMENT', 'json': 'DOCUMENT',
            'xml': 'DOCUMENT', 'md': 'DOCUMENT',
            
            # Images
            'jpg': 'IMAGE', 'jpeg': 'IMAGE', 'png': 'IMAGE',
            'gif': 'IMAGE', 'bmp': 'IMAGE', 'tiff': 'IMAGE',
            'svg': 'IMAGE', 'webp': 'IMAGE',
            
            # Techniques
            'dwg': 'TECHNIQUE', 'dxf': 'TECHNIQUE',
            'step': 'TECHNIQUE', 'stp': 'TECHNIQUE',
            'iges': 'TECHNIQUE', 'igs': 'TECHNIQUE',
            'stl': 'TECHNIQUE', 'obj': 'TECHNIQUE',
            
            # Archives
            'zip': 'ARCHIVE', 'rar': 'ARCHIVE',
            '7z': 'ARCHIVE', 'tar': 'ARCHIVE',
            
            # Vidéo/Audio
            'mp4': 'MEDIA', 'avi': 'MEDIA', 'mov': 'MEDIA',
            'mp3': 'MEDIA', 'wav': 'MEDIA'
        }
        
        # Taille maximale par fichier (50 MB)
        self.max_file_size = 50 * 1024 * 1024
        
        # Catégories avec icônes
        self.categories = {
            'DOCUMENT': {'icon': '📄', 'label': 'Document'},
            'IMAGE': {'icon': '📷', 'label': 'Image'},
            'TECHNIQUE': {'icon': '📐', 'label': 'Technique'},
            'ARCHIVE': {'icon': '📦', 'label': 'Archive'},
            'MEDIA': {'icon': '🎬', 'label': 'Média'},
            'AUTRE': {'icon': '📎', 'label': 'Autre'}
        }
        
        # Types de fichiers prévisualisables
        self.previewable_types = {
            # Images
            'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp',
            # Texte
            'txt', 'md', 'csv', 'json', 'xml',
            # PDF (via Streamlit)
            'pdf'
        }
    
    def _get_upload_directory(self) -> str:
        """CORRIGÉ : Utilise le répertoire persistant Render configuré"""
        
        # PRIORITÉ 1 : Variable ATTACHMENTS_DIR explicite
        attachments_dir = os.environ.get('ATTACHMENTS_DIR')
        if attachments_dir:
            print(f"✅ Utilisation ATTACHMENTS_DIR: {attachments_dir}")
            return attachments_dir
        
        # PRIORITÉ 2 : Variable DATA_PATH + attachments
        data_path = os.environ.get('DATA_PATH')
        if data_path and os.path.exists(data_path):
            attachments_dir = os.path.join(data_path, 'attachments')
            print(f"✅ Utilisation DATA_PATH: {attachments_dir}")
            return attachments_dir
        
        # PRIORITÉ 3 : Variable RENDER_PERSISTENT_DISK_PATH existante
        persistent_path = os.environ.get('RENDER_PERSISTENT_DISK_PATH')
        if persistent_path and os.path.exists(persistent_path):
            attachments_dir = os.path.join(persistent_path, 'attachments')
            print(f"✅ Utilisation RENDER_PERSISTENT_DISK_PATH: {attachments_dir}")
            return attachments_dir
        
        # PRIORITÉ 4 : Détection automatique Render avec persistent disk
        if os.path.exists('/opt/render/project/data'):
            attachments_dir = '/opt/render/project/data/attachments'
            print(f"✅ Détection auto Render persistent: {attachments_dir}")
            return attachments_dir
        
        # PRIORITÉ 5 : Storage manager (si disponible)
        if self.storage_manager:
            storage_info = self.storage_manager.get_storage_info()
            base_dir = storage_info.get('data_dir', 'data')
            attachments_dir = os.path.join(base_dir, 'attachments')
            print(f"✅ Storage manager: {attachments_dir}")
            return attachments_dir
        
        # PRIORITÉ 6 : Render temporaire (PROBLÉMATIQUE)
        if os.path.exists('/opt/render/project'):
            attachments_dir = '/tmp/attachments'
            print(f"⚠️ RENDER SANS PERSISTENT DISK: {attachments_dir}")
            print("🚨 LES FICHIERS SERONT PERDUS AU REDÉPLOIEMENT")
            return attachments_dir
        
        # FALLBACK : Développement local
        attachments_dir = os.path.join('data', 'attachments')
        print(f"💻 Développement local: {attachments_dir}")
        return attachments_dir
    
    def _run_startup_diagnostic(self):
        """NOUVEAU : Diagnostic complet au démarrage"""
        print("\n" + "="*60)
        print("📎 ATTACHMENTS MANAGER - DIAGNOSTIC DÉMARRAGE")
        print("="*60)
        
        # Informations environnement
        print(f"🖥️  Environnement Render: {os.path.exists('/opt/render/project')}")
        print(f"💾 Persistent disk disponible: {os.path.exists('/opt/render/project/data')}")
        print(f"📁 Répertoire configuré: {self.base_upload_dir}")
        print(f"📁 Répertoire existe: {os.path.exists(self.base_upload_dir)}")
        
        # Variables d'environnement critiques
        env_vars = ['ATTACHMENTS_DIR', 'DATA_PATH', 'RENDER_PERSISTENT_DISK_PATH', 'USE_PERSISTENT_STORAGE']
        print(f"\n🔧 Variables d'environnement:")
        for var in env_vars:
            value = os.environ.get(var, 'NON DÉFINI')
            print(f"   {var}: {value}")
        
        # Test de création et écriture
        try:
            os.makedirs(self.base_upload_dir, exist_ok=True)
            test_file = os.path.join(self.base_upload_dir, 'test_startup.txt')
            with open(test_file, 'w') as f:
                f.write(f'Test démarrage - {datetime.now()}')
            
            # Vérifier lecture
            with open(test_file, 'r') as f:
                content = f.read()
            
            os.remove(test_file)
            print("✅ Test écriture/lecture: RÉUSSI")
            
            # Vérifier permissions
            write_access = os.access(self.base_upload_dir, os.W_OK)
            print(f"✅ Permissions écriture: {'RÉUSSI' if write_access else 'ÉCHEC'}")
            
        except Exception as e:
            print(f"❌ Test écriture: ÉCHEC - {e}")
        
        # Évaluation configuration
        if '/opt/render/project/data' in self.base_upload_dir:
            print("🎉 CONFIGURATION OPTIMALE - Stockage persistant Render")
        elif '/tmp' in self.base_upload_dir:
            print("🚨 CONFIGURATION PROBLÉMATIQUE - Stockage temporaire")
            print("   → Configurez les variables d'environnement:")
            print("     ATTACHMENTS_DIR=/opt/render/project/data/attachments")
            print("     DATA_PATH=/opt/render/project/data")
        else:
            print("💻 Configuration développement local")
        
        print("="*60)
    
    def _ensure_upload_directory(self):
        """Crée le répertoire d'upload s'il n'existe pas"""
        try:
            Path(self.base_upload_dir).mkdir(parents=True, exist_ok=True)
            # Créer sous-répertoires par année/mois pour organisation
            current_year = datetime.now().year
            current_month = datetime.now().month
            monthly_dir = os.path.join(self.base_upload_dir, str(current_year), f"{current_month:02d}")
            Path(monthly_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"❌ Erreur création répertoire upload: {e}")
            st.error(f"❌ Erreur création répertoire upload: {e}")
    
    def _init_database_table(self):
        """Initialise la table des pièces jointes"""
        try:
            create_table_query = """
            CREATE TABLE IF NOT EXISTS project_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                file_type TEXT NOT NULL,
                file_extension TEXT,
                category TEXT NOT NULL,
                description TEXT,
                file_path TEXT NOT NULL,
                file_hash TEXT,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                uploaded_by TEXT,
                is_active BOOLEAN DEFAULT 1,
                download_count INTEGER DEFAULT 0,
                preview_count INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
            )
            """
            
            self.db.execute_update(create_table_query)
            
            # Ajouter la colonne preview_count si elle n'existe pas (migration)
            try:
                self.db.execute_update("ALTER TABLE project_attachments ADD COLUMN preview_count INTEGER DEFAULT 0")
            except:
                pass  # Colonne existe déjà
            
            # Index pour performance
            index_queries = [
                "CREATE INDEX IF NOT EXISTS idx_project_attachments_project_id ON project_attachments(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_attachments_category ON project_attachments(category)",
                "CREATE INDEX IF NOT EXISTS idx_project_attachments_upload_date ON project_attachments(upload_date)"
            ]
            
            for query in index_queries:
                self.db.execute_update(query)
                
        except Exception as e:
            print(f"❌ Erreur initialisation table pièces jointes: {e}")
            st.error(f"❌ Erreur initialisation table pièces jointes: {e}")
    
    def _cleanup_broken_attachments(self):
        """NOUVEAU : Nettoie les références aux fichiers inexistants"""
        try:
            query = "SELECT id, file_path, original_filename FROM project_attachments WHERE is_active = 1"
            attachments = self.db.execute_query(query)
            
            if not attachments:
                print("📎 Aucun attachment à vérifier")
                return
            
            broken_count = 0
            migrated_count = 0
            
            for attachment in attachments:
                file_path = attachment['file_path']
                
                if not os.path.exists(file_path):
                    # Essayer de trouver le fichier dans d'anciens répertoires
                    filename = os.path.basename(file_path)
                    
                    # Chemins potentiels de migration
                    potential_paths = [
                        f"/tmp/attachments/{filename}",
                        f"/opt/render/project/src/data/attachments/{filename}",
                        f"data/attachments/{filename}",
                        f"/opt/render/project/{filename}"
                    ]
                    
                    file_migrated = False
                    for old_path in potential_paths:
                        if os.path.exists(old_path):
                            try:
                                # Créer le nouveau répertoire si nécessaire
                                new_path = os.path.join(self.base_upload_dir, filename)
                                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                                
                                # Copier le fichier
                                shutil.copy2(old_path, new_path)
                                
                                # Mettre à jour le chemin en base
                                self.db.execute_update(
                                    "UPDATE project_attachments SET file_path = ? WHERE id = ?",
                                    (new_path, attachment['id'])
                                )
                                
                                migrated_count += 1
                                file_migrated = True
                                print(f"🔄 Fichier migré: {attachment['original_filename']}")
                                break
                                
                            except Exception as e:
                                print(f"⚠️ Erreur migration {filename}: {e}")
                    
                    if not file_migrated:
                        # Marquer comme inactif si fichier introuvable
                        self.db.execute_update(
                            "UPDATE project_attachments SET is_active = 0 WHERE id = ?",
                            (attachment['id'],)
                        )
                        broken_count += 1
                        print(f"❌ Fichier perdu: {attachment['original_filename']}")
            
            # Résumé
            if migrated_count > 0:
                print(f"🔄 {migrated_count} fichier(s) migré(s) vers stockage persistant")
                if migrated_count > 0:
                    st.success(f"🔄 {migrated_count} fichier(s) migré(s) vers stockage persistant")
            
            if broken_count > 0:
                print(f"⚠️ {broken_count} fichier(s) définitivement perdu(s)")
                if broken_count > 0:
                    st.warning(f"⚠️ {broken_count} fichier(s) de pièces jointes non trouvé(s) - probablement perdus lors du redéploiement")
            
            if migrated_count == 0 and broken_count == 0:
                print("✅ Tous les fichiers sont accessibles")
                
        except Exception as e:
            print(f"❌ Erreur nettoyage: {e}")
    
    def _calculate_file_hash(self, file_content: bytes) -> str:
        """Calcule le hash MD5 du fichier pour détecter les doublons"""
        return hashlib.md5(file_content).hexdigest()
    
    def _get_file_category(self, file_extension: str) -> str:
        """Détermine la catégorie d'un fichier selon son extension"""
        ext = file_extension.lower().lstrip('.')
        return self.allowed_file_types.get(ext, 'AUTRE')
    
    def _generate_unique_filename(self, original_filename: str, project_id: int) -> str:
        """Génère un nom de fichier unique pour éviter les conflits"""
        # Extraire l'extension
        file_stem = Path(original_filename).stem
        file_extension = Path(original_filename).suffix
        
        # Créer un identifiant unique
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Format: PRJ{project_id}_{timestamp}_{unique_id}_{original_name}{extension}
        safe_filename = f"PRJ{project_id}_{timestamp}_{unique_id}_{file_stem}{file_extension}"
        
        # Nettoyer le nom de fichier (caractères dangereux)
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
        safe_filename = ''.join(c if c in safe_chars else '_' for c in safe_filename)
        
        return safe_filename
    
    def _get_file_storage_path(self, filename: str) -> str:
        """Génère le chemin de stockage du fichier"""
        current_year = datetime.now().year
        current_month = datetime.now().month
        monthly_dir = os.path.join(self.base_upload_dir, str(current_year), f"{current_month:02d}")
        return os.path.join(monthly_dir, filename)
    
    def is_file_allowed(self, filename: str) -> Tuple[bool, str]:
        """Vérifie si un fichier est autorisé"""
        file_extension = Path(filename).suffix.lower().lstrip('.')
        
        if not file_extension:
            return False, "Fichier sans extension non autorisé"
        
        if file_extension not in self.allowed_file_types:
            allowed_extensions = ', '.join(sorted(self.allowed_file_types.keys()))
            return False, f"Extension .{file_extension} non autorisée. Extensions autorisées: {allowed_extensions}"
        
        return True, "Fichier autorisé"
    
    def is_file_previewable(self, file_extension: str) -> bool:
        """Vérifie si un fichier peut être prévisualisé"""
        ext = file_extension.lower().lstrip('.')
        return ext in self.previewable_types
    
    def upload_file(self, uploaded_file, project_id: int, description: str = "", uploaded_by: str = "Utilisateur") -> Optional[int]:
        """
        Upload un fichier et l'associe à un projet
        
        Args:
            uploaded_file: Fichier uploadé via Streamlit
            project_id: ID du projet associé
            description: Description optionnelle
            uploaded_by: Nom de l'utilisateur qui upload
            
        Returns:
            ID de l'attachment créé ou None si erreur
        """
        try:
            # Vérifications préliminaires
            if uploaded_file.size > self.max_file_size:
                st.error(f"Fichier trop volumineux. Taille max: {self.max_file_size / (1024*1024):.0f} MB")
                return None
            
            is_allowed, message = self.is_file_allowed(uploaded_file.name)
            if not is_allowed:
                st.error(message)
                return None
            
            # Lire le contenu du fichier
            file_content = uploaded_file.read()
            file_hash = self._calculate_file_hash(file_content)
            
            # Vérifier si le fichier existe déjà pour ce projet
            existing_file = self.db.execute_query(
                "SELECT id, original_filename FROM project_attachments WHERE project_id = ? AND file_hash = ? AND is_active = 1",
                (project_id, file_hash)
            )
            
            if existing_file:
                st.warning(f"Fichier identique déjà attaché: {existing_file[0]['original_filename']}")
                return existing_file[0]['id']
            
            # Générer nom de fichier unique et chemin
            safe_filename = self._generate_unique_filename(uploaded_file.name, project_id)
            file_path = self._get_file_storage_path(safe_filename)
            
            # S'assurer que le répertoire existe
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Sauvegarder le fichier
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Déterminer catégorie et type MIME
            file_extension = Path(uploaded_file.name).suffix.lower()
            category = self._get_file_category(file_extension)
            mime_type, _ = mimetypes.guess_type(uploaded_file.name)
            
            # Insérer en base de données
            insert_query = """
                INSERT INTO project_attachments 
                (project_id, filename, original_filename, file_size, file_type, file_extension,
                 category, description, file_path, file_hash, uploaded_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            attachment_id = self.db.execute_insert(insert_query, (
                project_id, safe_filename, uploaded_file.name, uploaded_file.size,
                mime_type or 'application/octet-stream', file_extension,
                category, description, file_path, file_hash, uploaded_by
            ))
            
            if attachment_id:
                st.success(f"✅ Fichier '{uploaded_file.name}' attaché avec succès!")
                return attachment_id
            else:
                st.error("Erreur lors de l'enregistrement en base")
                # Nettoyer le fichier uploadé en cas d'erreur DB
                if os.path.exists(file_path):
                    os.remove(file_path)
                return None
                
        except Exception as e:
            st.error(f"Erreur upload fichier: {e}")
            return None
    
    def get_project_attachments(self, project_id: int) -> List[Dict]:
        """Récupère toutes les pièces jointes d'un projet"""
        try:
            query = """
                SELECT id, filename, original_filename, file_size, file_type, file_extension,
                       category, description, upload_date, uploaded_by, download_count, preview_count
                FROM project_attachments 
                WHERE project_id = ? AND is_active = 1 
                ORDER BY upload_date DESC
            """
            
            attachments = self.db.execute_query(query, (project_id,))
            return [dict(attachment) for attachment in attachments] if attachments else []
            
        except Exception as e:
            st.error(f"Erreur récupération pièces jointes: {e}")
            return []
    
    def get_attachment_by_id(self, attachment_id: int) -> Optional[Dict]:
        """Récupère une pièce jointe par son ID"""
        try:
            query = """
                SELECT * FROM project_attachments 
                WHERE id = ? AND is_active = 1
            """
            
            result = self.db.execute_query(query, (attachment_id,))
            return dict(result[0]) if result else None
            
        except Exception as e:
            st.error(f"Erreur récupération pièce jointe: {e}")
            return None
    
    def preview_attachment(self, attachment_id: int) -> Optional[Dict]:
        """
        Génère un aperçu du fichier selon son type
        
        Returns:
            Dict avec les informations d'aperçu ou None si impossible
        """
        try:
            attachment = self.get_attachment_by_id(attachment_id)
            if not attachment:
                return None
            
            file_path = attachment['file_path']
            if not os.path.exists(file_path):
                st.error("Fichier physique non trouvé")
                return None
            
            file_extension = attachment['file_extension'].lower().lstrip('.')
            
            # Mettre à jour le compteur de prévisualisations
            self.db.execute_update(
                "UPDATE project_attachments SET preview_count = preview_count + 1 WHERE id = ?",
                (attachment_id,)
            )
            
            preview_data = {
                'attachment': attachment,
                'preview_type': None,
                'content': None,
                'error': None
            }
            
            # Gestion selon le type de fichier
            if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                preview_data['preview_type'] = 'image'
                preview_data['content'] = file_path
                
            elif file_extension in ['txt', 'md', 'csv', 'json', 'xml']:
                preview_data['preview_type'] = 'text'
                try:
                    # Lire le fichier texte (limité à 10KB pour éviter les problèmes)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(10240)  # 10KB max
                        if len(content) == 10240:
                            content += "\n\n... (fichier tronqué pour l'aperçu)"
                        preview_data['content'] = content
                except Exception as e:
                    preview_data['error'] = f"Erreur lecture fichier texte: {e}"
                    
            elif file_extension == 'pdf':
                preview_data['preview_type'] = 'pdf'
                # Pour PDF, on retourne le chemin du fichier pour téléchargement/affichage
                preview_data['content'] = file_path
                
            else:
                preview_data['preview_type'] = 'unsupported'
                preview_data['error'] = f"Aperçu non supporté pour les fichiers .{file_extension}"
            
            return preview_data
            
        except Exception as e:
            st.error(f"Erreur génération aperçu: {e}")
            return None
    
    def download_attachment(self, attachment_id: int) -> Optional[Tuple[bytes, str, str]]:
        """
        Télécharge une pièce jointe
        
        Returns:
            Tuple (contenu_fichier, nom_original, type_mime) ou None si erreur
        """
        try:
            attachment = self.get_attachment_by_id(attachment_id)
            if not attachment:
                st.error("Pièce jointe non trouvée")
                return None
            
            file_path = attachment['file_path']
            if not os.path.exists(file_path):
                st.error("Fichier physique non trouvé")
                return None
            
            # Lire le fichier
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Mettre à jour le compteur de téléchargements
            self.db.execute_update(
                "UPDATE project_attachments SET download_count = download_count + 1 WHERE id = ?",
                (attachment_id,)
            )
            
            return file_content, attachment['original_filename'], attachment['file_type']
            
        except Exception as e:
            st.error(f"Erreur téléchargement: {e}")
            return None
    
    def delete_attachment(self, attachment_id: int) -> bool:
        """Supprime une pièce jointe (soft delete)"""
        try:
            # Récupérer infos du fichier avant suppression
            attachment = self.get_attachment_by_id(attachment_id)
            if not attachment:
                return False
            
            # Soft delete en base
            self.db.execute_update(
                "UPDATE project_attachments SET is_active = 0 WHERE id = ?",
                (attachment_id,)
            )
            
            # Optionnel: supprimer le fichier physique
            # (commenté pour conserver une trace)
            # if os.path.exists(attachment['file_path']):
            #     os.remove(attachment['file_path'])
            
            st.success(f"Pièce jointe '{attachment['original_filename']}' supprimée")
            return True
            
        except Exception as e:
            st.error(f"Erreur suppression: {e}")
            return False
    
    def get_attachments_statistics(self, project_id: Optional[int] = None) -> Dict:
        """Récupère des statistiques sur les pièces jointes"""
        try:
            base_query = "FROM project_attachments WHERE is_active = 1"
            params = ()
            
            if project_id:
                base_query += " AND project_id = ?"
                params = (project_id,)
            
            # Nombre total
            total_query = f"SELECT COUNT(*) as total {base_query}"
            total_result = self.db.execute_query(total_query, params)
            total_attachments = total_result[0]['total'] if total_result else 0
            
            # Taille totale
            size_query = f"SELECT SUM(file_size) as total_size {base_query}"
            size_result = self.db.execute_query(size_query, params)
            total_size = size_result[0]['total_size'] if size_result and size_result[0]['total_size'] else 0
            
            # Par catégorie
            category_query = f"SELECT category, COUNT(*) as count {base_query} GROUP BY category"
            category_result = self.db.execute_query(category_query, params)
            by_category = {row['category']: row['count'] for row in category_result} if category_result else {}
            
            return {
                'total_attachments': total_attachments,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'by_category': by_category
            }
            
        except Exception as e:
            st.error(f"Erreur statistiques: {e}")
            return {'total_attachments': 0, 'total_size_bytes': 0, 'total_size_mb': 0, 'by_category': {}}
    
    def get_project_attachments_by_category(self, project_id: int) -> Dict[str, List[Dict]]:
        """Récupère les pièces jointes d'un projet groupées par catégorie"""
        attachments = self.get_project_attachments(project_id)
        
        grouped = {}
        for attachment in attachments:
            category = attachment['category']
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(attachment)
        
        return grouped
    
    def format_file_size(self, size_bytes: int) -> str:
        """Formate une taille de fichier en format lisible"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def get_storage_health_info(self) -> dict:
        """NOUVEAU : Diagnostique de santé du stockage"""
        health_info = {
            'upload_directory': self.base_upload_dir,
            'directory_exists': os.path.exists(self.base_upload_dir),
            'is_persistent': False,
            'render_env': os.path.exists('/opt/render/project'),
            'persistent_disk': os.path.exists('/opt/render/project/data'),
            'recommendations': []
        }
        
        # Déterminer si le stockage est persistant
        if '/opt/render/project/data' in self.base_upload_dir:
            health_info['is_persistent'] = True
            health_info['recommendations'].append("✅ Configuration optimale - Stockage persistant")
        elif '/tmp' in self.base_upload_dir or '/opt/render/project/src' in self.base_upload_dir:
            health_info['is_persistent'] = False
            health_info['recommendations'].append("🚨 URGENT: Configurez le Persistent Disk sur Render")
            health_info['recommendations'].append("📋 Variables: ATTACHMENTS_DIR=/opt/render/project/data/attachments")
        else:
            health_info['is_persistent'] = True  # Développement local
            health_info['recommendations'].append("💻 Mode développement local")
        
        # Statistiques des fichiers
        try:
            query = "SELECT COUNT(*) as total, COUNT(CASE WHEN is_active = 1 THEN 1 END) as active FROM project_attachments"
            stats = self.db.execute_query(query)
            if stats:
                health_info['total_attachments'] = stats[0]['total']
                health_info['active_attachments'] = stats[0]['active']
                health_info['broken_attachments'] = stats[0]['total'] - stats[0]['active']
        except:
            health_info['total_attachments'] = 0
            health_info['active_attachments'] = 0
            health_info['broken_attachments'] = 0
        
        return health_info
    
    def cleanup_orphaned_files(self):
        """Nettoie les fichiers orphelins (non référencés en base)"""
        try:
            # Récupérer tous les chemins de fichiers en base
            query = "SELECT file_path FROM project_attachments WHERE is_active = 1"
            db_files = self.db.execute_query(query)
            db_file_paths = {row['file_path'] for row in db_files} if db_files else set()
            
            # Scanner le répertoire d'upload
            orphaned_count = 0
            for root, dirs, files in os.walk(self.base_upload_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if file_path not in db_file_paths:
                        # Fichier orphelin trouvé
                        st.warning(f"Fichier orphelin détecté: {file_path}")
                        orphaned_count += 1
                        # Optionnel: supprimer automatiquement
                        # os.remove(file_path)
            
            if orphaned_count == 0:
                st.success("Aucun fichier orphelin détecté")
            else:
                st.info(f"{orphaned_count} fichier(s) orphelin(s) détecté(s)")
                
        except Exception as e:
            st.error(f"Erreur nettoyage: {e}")


def show_file_preview_modal(attachments_manager: AttachmentsManager, attachment_id: int):
    """
    Affiche l'aperçu d'un fichier dans une modal - CORRIGÉ avec clé unique
    """
    preview_data = attachments_manager.preview_attachment(attachment_id)
    
    if not preview_data:
        st.error("Impossible de générer l'aperçu")
        return
    
    attachment = preview_data['attachment']
    preview_type = preview_data['preview_type']
    content = preview_data['content']
    error = preview_data['error']
    
    # En-tête de l'aperçu
    st.markdown(f"### 👁️ Aperçu: {attachment['original_filename']}")
    
    # Informations du fichier
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**📊 Taille:** {attachments_manager.format_file_size(attachment['file_size'])}")
    with col2:
        st.markdown(f"**📂 Catégorie:** {attachment['category']}")
    with col3:
        preview_count = attachment.get('preview_count', 0)
        st.markdown(f"**👁️ Vues:** {preview_count}")
    
    if attachment['description']:
        st.markdown(f"**📝 Description:** {attachment['description']}")
    
    st.markdown("---")
    
    # Affichage selon le type
    if error:
        st.error(f"❌ {error}")
        
    elif preview_type == 'image':
        try:
            st.image(content, caption=attachment['original_filename'], use_column_width=True)
        except Exception as e:
            st.error(f"Erreur affichage image: {e}")
            
    elif preview_type == 'text':
        st.markdown("**📄 Contenu du fichier:**")
        
        # Déterminer le langage pour la coloration syntaxique
        file_ext = attachment['file_extension'].lower().lstrip('.')
        language_map = {
            'json': 'json',
            'xml': 'xml',
            'csv': 'csv',
            'md': 'markdown',
            'txt': 'text'
        }
        language = language_map.get(file_ext, 'text')
        
        st.code(content, language=language)
        
    elif preview_type == 'pdf':
        st.markdown("**📄 Aperçu du fichier PDF:**")
        
        try:
            # Lire le fichier PDF
            with open(content, 'rb') as pdf_file:
                pdf_content = pdf_file.read()
            
            # Encoder en base64 pour l'affichage
            import base64
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            # Afficher le PDF dans un iframe
            pdf_display = f"""
            <iframe 
                src="data:application/pdf;base64,{pdf_base64}" 
                width="100%" 
                height="600px" 
                style="border: none;">
                <p>Votre navigateur ne supporte pas l'affichage des PDFs. 
                   <a href="data:application/pdf;base64,{pdf_base64}" target="_blank">Cliquez ici pour ouvrir le PDF</a>
                </p>
            </iframe>
            """
            
            st.markdown(pdf_display, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Erreur lors de l'affichage du PDF: {e}")
            st.info("💡 Utilisez le bouton de téléchargement ci-dessous pour ouvrir le PDF")
        
        # Bouton de téléchargement en secours - CORRIGÉ avec clé unique
        download_result = attachments_manager.download_attachment(attachment_id)
        if download_result:
            file_content, original_filename, mime_type = download_result
            st.download_button(
                "📄 Télécharger PDF",
                data=file_content,
                file_name=original_filename,
                mime=mime_type,
                use_container_width=True,
                key=f"download_pdf_preview_{attachment_id}"  # CORRIGÉ: clé unique
            )
            
    elif preview_type == 'unsupported':
        st.warning("🚫 Aperçu non disponible pour ce type de fichier")
        
        # Afficher des métadonnées à la place
        st.markdown("**📋 Informations du fichier:**")
        st.markdown(f"- **Type MIME:** {attachment['file_type']}")
        st.markdown(f"- **Extension:** {attachment['file_extension']}")
        st.markdown(f"- **Uploadé le:** {attachment['upload_date']}")
        st.markdown(f"- **Par:** {attachment['uploaded_by']}")
        
        download_count = attachment.get('download_count', 0)
        if download_count > 0:
            st.markdown(f"- **Téléchargements:** {download_count}")
    
    # Boutons d'action
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        # Bouton de téléchargement - CORRIGÉ avec clé unique
        download_result = attachments_manager.download_attachment(attachment_id)
        if download_result:
            file_content, original_filename, mime_type = download_result
            st.download_button(
                "⬇️ Télécharger",
                data=file_content,
                file_name=original_filename,
                mime=mime_type,
                use_container_width=True,
                key=f"download_preview_{attachment_id}"  # CORRIGÉ: clé unique
            )
    
    with col2:
        # CORRIGÉ: Clé unique pour le bouton de fermeture
        if st.button("✖️ Fermer l'aperçu", use_container_width=True, key=f"close_preview_{attachment_id}"):
            if f'show_preview_{attachment_id}' in st.session_state:
                del st.session_state[f'show_preview_{attachment_id}']
            st.rerun()


def show_project_attachments_interface(attachments_manager: AttachmentsManager, project_id: int):
    """
    Interface Streamlit pour gérer les pièces jointes d'un projet - CORRIGÉ avec clés uniques
    """
    st.markdown("### 📎 Pièces Jointes")
    
    # Statistiques rapides
    stats = attachments_manager.get_attachments_statistics(project_id)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📁 Fichiers", stats['total_attachments'])
    with col2:
        st.metric("💾 Taille", f"{stats['total_size_mb']} MB")
    with col3:
        categories_count = len(stats['by_category'])
        st.metric("📂 Catégories", categories_count)
    
    # Zone d'upload
    with st.expander("📤 Ajouter des Fichiers", expanded=False):
        st.markdown("#### Upload de Fichiers")
        
        # Informations sur les types autorisés
        allowed_exts = sorted(attachments_manager.allowed_file_types.keys())
        st.info(f"**Types autorisés:** {', '.join(allowed_exts)}")
        st.info(f"**Taille max:** {attachments_manager.max_file_size / (1024*1024):.0f} MB par fichier")
        
        # Types prévisualisables
        previewable_exts = sorted(attachments_manager.previewable_types)
        st.success(f"**👁️ Aperçu disponible pour:** {', '.join(previewable_exts)}")
        
        # Upload multiple
        uploaded_files = st.file_uploader(
            "Choisir des fichiers",
            accept_multiple_files=True,
            help="Sélectionnez un ou plusieurs fichiers à attacher au projet",
            key=f"file_uploader_{project_id}"  # CORRIGÉ: clé unique
        )
        
        description = st.text_input(
            "Description (optionnelle)",
            placeholder="Ex: Plans d'exécution version finale",
            key=f"file_description_{project_id}"  # CORRIGÉ: clé unique
        )
        
        # CORRIGÉ: Clé unique pour le bouton d'upload
        if uploaded_files and st.button("📤 Upload Fichiers", type="primary", key=f"upload_files_{project_id}"):
            upload_success = 0
            upload_errors = 0
            
            for uploaded_file in uploaded_files:
                result = attachments_manager.upload_file(
                    uploaded_file, 
                    project_id, 
                    description,
                    st.session_state.get('admin_username', 'Utilisateur')
                )
                
                if result:
                    upload_success += 1
                else:
                    upload_errors += 1
            
            if upload_success > 0:
                st.success(f"✅ {upload_success} fichier(s) uploadé(s) avec succès!")
                st.rerun()
            
            if upload_errors > 0:
                st.error(f"❌ {upload_errors} erreur(s) d'upload")
    
    # Affichage des pièces jointes par catégorie
    st.markdown("---")
    attachments_by_category = attachments_manager.get_project_attachments_by_category(project_id)
    
    if not attachments_by_category:
        st.info("📎 Aucune pièce jointe pour ce projet")
        return
    
    # Onglets par catégorie
    categories = list(attachments_by_category.keys())
    if len(categories) == 1:
        # Une seule catégorie, pas besoin d'onglets
        category = categories[0]
        show_attachments_category(attachments_manager, category, attachments_by_category[category])
    else:
        # Plusieurs catégories, utiliser des onglets
        category_labels = []
        for cat in categories:
            cat_info = attachments_manager.categories.get(cat, {'icon': '📎', 'label': cat})
            count = len(attachments_by_category[cat])
            category_labels.append(f"{cat_info['icon']} {cat_info['label']} ({count})")
        
        # CORRIGÉ: Clé unique pour le selectbox
        selected_tab = st.selectbox("Catégorie", category_labels, key=f"category_select_{project_id}")
        selected_category = categories[category_labels.index(selected_tab)]
        
        show_attachments_category(
            attachments_manager, 
            selected_category, 
            attachments_by_category[selected_category]
        )


def show_attachments_category(attachments_manager: AttachmentsManager, category: str, attachments: List[Dict]):
    """Affiche les pièces jointes d'une catégorie avec bouton d'aperçu - CORRIGÉ avec clés uniques"""
    
    category_info = attachments_manager.categories.get(category, {'icon': '📎', 'label': category})
    st.markdown(f"#### {category_info['icon']} {category_info['label']} ({len(attachments)})")
    
    for attachment in attachments:
        attachment_id = attachment['id']
        
        # Vérifier si on doit afficher l'aperçu pour ce fichier
        show_preview_key = f'show_preview_{attachment_id}'
        
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1.5])
            
            with col1:
                st.markdown(f"**{attachment['original_filename']}**")
                if attachment['description']:
                    st.caption(f"📝 {attachment['description']}")
            
            with col2:
                size_formatted = attachments_manager.format_file_size(attachment['file_size'])
                st.markdown(f"📊 {size_formatted}")
                
                # Afficher les compteurs
                download_count = attachment.get('download_count', 0)
                preview_count = attachment.get('preview_count', 0)
                st.caption(f"⬇️ {download_count} • 👁️ {preview_count}")
            
            with col3:
                upload_date = datetime.fromisoformat(attachment['upload_date'].replace('Z', '+00:00'))
                st.markdown(f"📅 {upload_date.strftime('%d/%m/%Y')}")
                st.caption(f"👤 {attachment['uploaded_by']}")
            
            with col4:
                # Boutons d'action
                button_col1, button_col2, button_col3 = st.columns(3)
                
                # Bouton d'aperçu - CORRIGÉ avec clé unique
                with button_col1:
                    file_ext = attachment['file_extension'].lower().lstrip('.')
                    can_preview = attachments_manager.is_file_previewable(file_ext)
                    
                    if can_preview:
                        if st.button("👁️", key=f"preview_{attachment_id}", help="Aperçu", use_container_width=True):
                            st.session_state[show_preview_key] = True
                            st.rerun()
                    else:
                        st.button("🚫", key=f"no_preview_{attachment_id}", help="Aperçu non disponible", 
                                disabled=True, use_container_width=True)
                
                # Bouton de téléchargement - CORRIGÉ avec clé unique
                with button_col2:
                    download_result = attachments_manager.download_attachment(attachment_id)
                    if download_result:
                        file_content, original_filename, mime_type = download_result
                        st.download_button(
                            "⬇️",
                            data=file_content,
                            file_name=original_filename,
                            mime=mime_type,
                            help="Télécharger",
                            key=f"download_{attachment_id}",
                            use_container_width=True
                        )
                
                # Bouton de suppression - CORRIGÉ avec clé unique
                with button_col3:
                    if st.button("🗑️", key=f"delete_{attachment_id}", help="Supprimer", use_container_width=True):
                        if attachments_manager.delete_attachment(attachment_id):
                            st.rerun()
            
            # Affichage de l'aperçu si demandé
            if st.session_state.get(show_preview_key, False):
                with st.expander(f"👁️ Aperçu: {attachment['original_filename']}", expanded=True):
                    show_file_preview_modal(attachments_manager, attachment_id)
            
            st.markdown("---")


# NOUVEAU : Fonctions d'administration et diagnostic - CORRIGÉES avec clés uniques
def show_attachments_health_dashboard(attachments_manager):
    """Affiche le tableau de bord de santé des pièces jointes - CORRIGÉ avec clés uniques"""
    
    st.markdown("### 🏥 Diagnostic Pièces Jointes")
    
    health = attachments_manager.get_storage_health_info()
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📁 Total Fichiers", health['total_attachments'])
    
    with col2:
        st.metric("✅ Fichiers Actifs", health['active_attachments'])
    
    with col3:
        broken = health['broken_attachments']
        st.metric("❌ Fichiers Perdus", broken, delta=f"-{broken}" if broken > 0 else None)
    
    with col4:
        persistent_status = "✅ OUI" if health['is_persistent'] else "❌ NON"
        st.metric("💾 Persistant", persistent_status)
    
    # Informations détaillées
    with st.expander("📋 Détails Configuration", expanded=broken > 0):
        st.markdown(f"**📁 Répertoire stockage:** `{health['upload_directory']}`")
        st.markdown(f"**🖥️ Environnement Render:** {'✅' if health['render_env'] else '❌'}")
        st.markdown(f"**💾 Persistent Disk:** {'✅' if health['persistent_disk'] else '❌'}")
        
        # Recommandations
        st.markdown("#### 💡 Recommandations")
        for rec in health['recommendations']:
            if rec.startswith('🚨'):
                st.error(rec)
            elif rec.startswith('⚠️'):
                st.warning(rec)
            elif rec.startswith('✅'):
                st.success(rec)
            else:
                st.info(rec)
    
    # Actions correctives
    if broken > 0:
        st.markdown("#### 🔧 Actions Correctives")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CORRIGÉ: Clé unique pour le bouton de nettoyage
            if st.button("🧹 Nettoyer Références Cassées", 
                        help="Supprime les références aux fichiers inexistants", 
                        key="cleanup_broken_refs"):
                try:
                    # Supprimer définitivement les références cassées
                    query = """
                        DELETE FROM project_attachments 
                        WHERE is_active = 0 
                        AND id IN (
                            SELECT id FROM project_attachments 
                            WHERE is_active = 0 
                            ORDER BY upload_date DESC
                        )
                    """
                    result = attachments_manager.db.execute_update(query)
                    st.success(f"✅ {broken} référence(s) cassée(s) nettoyée(s)")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erreur nettoyage: {e}")
        
        with col2:
            # CORRIGÉ: Clé unique pour le bouton de rapport
            if st.button("📊 Rapport Détaillé", 
                        help="Affiche la liste des fichiers perdus", 
                        key="detailed_report"):
                try:
                    broken_files = attachments_manager.db.execute_query("""
                        SELECT original_filename, upload_date, project_id 
                        FROM project_attachments 
                        WHERE is_active = 0 
                        ORDER BY upload_date DESC
                    """)
                    
                    if broken_files:
                        st.markdown("##### 📋 Fichiers Perdus")
                        for file in broken_files:
                            st.markdown(f"- **{file['original_filename']}** (Projet #{file['project_id']}) - {file['upload_date']}")
                    
                except Exception as e:
                    st.error(f"Erreur rapport: {e}")


# Fonctions utilitaires pour intégration dans app.py

def init_attachments_manager(db, storage_manager=None):
    """Initialise le gestionnaire de pièces jointes"""
    if 'attachments_manager' not in st.session_state:
        st.session_state.attachments_manager = AttachmentsManager(db, storage_manager)
    return st.session_state.attachments_manager

def show_attachments_tab_in_project_modal(project):
    """Onglet pièces jointes dans la modal de détail projet"""
    if 'attachments_manager' not in st.session_state:
        st.error("Gestionnaire de pièces jointes non initialisé")
        return
    
    attachments_manager = st.session_state.attachments_manager
    project_id = project.get('id')
    
    if project_id:
        show_project_attachments_interface(attachments_manager, project_id)
    else:
        st.error("ID du projet non valide")

print("✅ AttachmentsManager VERSION COMPLÈTE CORRIGÉE - CLÉS BOUTONS UNIQUES")
print("📎 Fonctionnalités : Upload, Download, Aperçu, Catégorisation, Sécurité, Diagnostic")
print("👁️ Types prévisualisables : Images, Texte, PDF, JSON, CSV, XML, Markdown")
print("🔧 Correction : Utilisation automatique du persistent disk Render")
print("🔑 NOUVEAU : Toutes les clés de boutons sont uniques pour éviter les conflits")
print("🏥 Nouveau : Diagnostic de santé et migration automatique des fichiers")
print("🔗 Prêt pour utilisation avec les variables d'environnement Render")
