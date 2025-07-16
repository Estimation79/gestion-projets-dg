# auth_config.py - Configuration d'Authentification
# ERP Production DG Inc. - Gestion des mots de passe administrateurs

import hashlib
import os
from typing import Dict, Optional

# ===============================================
# CONFIGURATION DES MOTS DE PASSE ADMINISTRATEURS
# ===============================================

# Mots de passe par défaut (à changer en production !)
DEFAULT_ADMIN_PASSWORDS = {
    "admin": "admin123",           # Compte admin principal
    "dg_admin": "dg2024!",        # Compte DG Inc spécifique
    "superviseur": "super2024",    # Compte superviseur
    "direction": "direction!123",  # Compte direction
}

# Récupérer les mots de passe depuis les variables d'environnement ou utiliser les défauts
ADMIN_PASSWORDS = {
    "admin": os.environ.get("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORDS["admin"]),
    "dg_admin": os.environ.get("DG_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORDS["dg_admin"]),
    "superviseur": os.environ.get("SUPERVISEUR_PASSWORD", DEFAULT_ADMIN_PASSWORDS["superviseur"]),
    "direction": os.environ.get("DIRECTION_PASSWORD", DEFAULT_ADMIN_PASSWORDS["direction"]),
}

# ===============================================
# FONCTIONS DE HACHAGE ET VÉRIFICATION
# ===============================================

def hash_password(password: str) -> str:
    """
    Hache un mot de passe avec SHA-256 et un salt
    
    Args:
        password (str): Mot de passe en clair
        
    Returns:
        str: Mot de passe haché
    """
    # Salt fixe (en production, utilisez un salt aléatoire par utilisateur)
    salt = "dg_inc_erp_2024_salt"
    
    # Combiner mot de passe et salt
    salted_password = password + salt
    
    # Hacher avec SHA-256
    hashed = hashlib.sha256(salted_password.encode()).hexdigest()
    
    return hashed

def verify_password(username: str, password: str) -> bool:
    """
    Vérifie si le mot de passe correspond pour un utilisateur donné
    
    Args:
        username (str): Nom d'utilisateur
        password (str): Mot de passe fourni
        
    Returns:
        bool: True si le mot de passe est correct, False sinon
    """
    # Vérifier si l'utilisateur existe
    if username not in ADMIN_PASSWORDS:
        return False
    
    # Récupérer le mot de passe attendu
    expected_password = ADMIN_PASSWORDS[username]
    
    # Vérification directe (pour simplicité)
    # En production, vous devriez comparer les hashs
    return password == expected_password

def get_user_permissions(username: str) -> Dict[str, bool]:
    """
    Retourne les permissions d'un utilisateur
    
    Args:
        username (str): Nom d'utilisateur
        
    Returns:
        Dict[str, bool]: Dictionnaire des permissions
    """
    # Permissions par défaut
    default_permissions = {
        "view_projects": True,
        "edit_projects": True,
        "delete_projects": False,
        "manage_employees": False,
        "view_financials": True,
        "admin_settings": False,
        "manage_users": False,
        "view_timetracker": True,
        "manage_formulaires": True,
        "manage_fournisseurs": True,
        "use_assistant_ia": True,
    }
    
    # Permissions spécifiques par utilisateur
    user_permissions = {
        "admin": {
            **default_permissions,
            "delete_projects": True,
            "manage_employees": True,
            "admin_settings": True,
            "manage_users": True,
        },
        "dg_admin": {
            **default_permissions,
            "delete_projects": True,
            "manage_employees": True,
            "admin_settings": True,
        },
        "superviseur": {
            **default_permissions,
            "manage_employees": True,
        },
        "direction": {
            **default_permissions,
            "delete_projects": True,
            "manage_employees": True,
            "view_financials": True,
            "admin_settings": True,
        }
    }
    
    return user_permissions.get(username, default_permissions)

def is_admin_user(username: str) -> bool:
    """
    Vérifie si un utilisateur est administrateur
    
    Args:
        username (str): Nom d'utilisateur
        
    Returns:
        bool: True si l'utilisateur est admin
    """
    return username in ADMIN_PASSWORDS

def get_user_display_name(username: str) -> str:
    """
    Retourne le nom d'affichage d'un utilisateur
    
    Args:
        username (str): Nom d'utilisateur
        
    Returns:
        str: Nom d'affichage
    """
    display_names = {
        "admin": "Administrateur Principal",
        "dg_admin": "Admin DG Inc.",
        "superviseur": "Superviseur Production",
        "direction": "Direction Générale"
    }
    
    return display_names.get(username, username.title())

# ===============================================
# FONCTIONS DE SÉCURITÉ ADDITIONNELLES
# ===============================================

def check_password_strength(password: str) -> Dict[str, bool]:
    """
    Vérifie la force d'un mot de passe
    
    Args:
        password (str): Mot de passe à vérifier
        
    Returns:
        Dict[str, bool]: Critères de sécurité
    """
    checks = {
        "min_length": len(password) >= 8,
        "has_uppercase": any(c.isupper() for c in password),
        "has_lowercase": any(c.islower() for c in password),
        "has_digit": any(c.isdigit() for c in password),
        "has_special": any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password),
    }
    
    checks["is_strong"] = all(checks.values())
    
    return checks

def generate_session_token(username: str) -> str:
    """
    Génère un token de session unique
    
    Args:
        username (str): Nom d'utilisateur
        
    Returns:
        str: Token de session
    """
    import time
    import random
    
    # Combinaison utilisateur + timestamp + random
    session_data = f"{username}_{int(time.time())}_{random.randint(1000, 9999)}"
    
    # Hacher le token
    return hashlib.md5(session_data.encode()).hexdigest()

# ===============================================
# CONFIGURATION DE SÉCURITÉ
# ===============================================

# Nombre maximum de tentatives de connexion
MAX_LOGIN_ATTEMPTS = 3

# Durée de blocage après échec (en secondes)
LOCKOUT_DURATION = 300  # 5 minutes

# Durée de validité d'une session (en secondes)
SESSION_TIMEOUT = 3600  # 1 heure

# ===============================================
# CONFIGURATION API CLAUDE IA
# ===============================================

# Clé API Claude pour l'assistant IA
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")

# Modèle Claude à utiliser
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# Paramètres de l'assistant IA
IA_CONFIG = {
    "model": CLAUDE_MODEL,
    "max_tokens": 1500,
    "temperature": 0.7,
    "enabled": bool(CLAUDE_API_KEY),
    "max_history": 50,  # Nombre max de messages dans l'historique
    "timeout": 30,      # Timeout en secondes
}

def get_claude_api_key() -> str:
    """Récupère la clé API Claude"""
    return CLAUDE_API_KEY

def is_ia_enabled() -> bool:
    """Vérifie si l'assistant IA est activé"""
    return IA_CONFIG["enabled"]

def get_ia_config() -> Dict[str, Any]:
    """Retourne la configuration de l'assistant IA"""
    return IA_CONFIG.copy()

# ===============================================
# FONCTIONS D'AUDIT ET LOGGING
# ===============================================

def log_login_attempt(username: str, success: bool, ip_address: str = "unknown") -> None:
    """
    Enregistre une tentative de connexion
    
    Args:
        username (str): Nom d'utilisateur
        success (bool): Succès ou échec
        ip_address (str): Adresse IP
    """
    import datetime
    
    timestamp = datetime.datetime.now().isoformat()
    status = "SUCCESS" if success else "FAILED"
    
    # En production, écrire dans un fichier de log ou base de données
    log_entry = f"[{timestamp}] LOGIN {status}: user={username}, ip={ip_address}"
    
    # Pour l'instant, juste print (à remplacer par vraie gestion de logs)
    print(log_entry)

def get_login_history(username: Optional[str] = None, limit: int = 100) -> list:
    """
    Récupère l'historique des connexions
    
    Args:
        username (str, optional): Filtrer par utilisateur
        limit (int): Nombre maximum d'entrées
        
    Returns:
        list: Historique des connexions
    """
    # Placeholder - en production, lire depuis fichier de log ou BDD
    return []

# ===============================================
# VALIDATION AU DÉMARRAGE
# ===============================================

def validate_auth_config() -> bool:
    """
    Valide la configuration d'authentification
    
    Returns:
        bool: True si la configuration est valide
    """
    errors = []
    
    # Vérifier qu'il y a au moins un admin
    if not ADMIN_PASSWORDS:
        errors.append("Aucun mot de passe administrateur configuré")
    
    # Vérifier la force des mots de passe par défaut
    for username, password in ADMIN_PASSWORDS.items():
        if password in DEFAULT_ADMIN_PASSWORDS.values():
            if len(password) < 8:
                errors.append(f"Mot de passe trop faible pour {username}")
    
    # Afficher les erreurs
    if errors:
        print("⚠️ AVERTISSEMENTS SÉCURITÉ:")
        for error in errors:
            print(f"  - {error}")
        print("🔒 Recommandation: Configurez des mots de passe forts via variables d'environnement")
        return False
    
    return True

# ===============================================
# MESSAGES D'INFORMATION
# ===============================================

def get_security_info() -> Dict[str, str]:
    """
    Retourne des informations sur la configuration de sécurité
    
    Returns:
        Dict[str, str]: Informations de sécurité
    """
    return {
        "total_admins": str(len(ADMIN_PASSWORDS)),
        "default_passwords": "OUI" if any(pwd in DEFAULT_ADMIN_PASSWORDS.values() for pwd in ADMIN_PASSWORDS.values()) else "NON",
        "env_configured": "OUI" if any(key.endswith("_PASSWORD") for key in os.environ.keys()) else "NON",
        "session_timeout": f"{SESSION_TIMEOUT // 60} minutes",
        "max_attempts": str(MAX_LOGIN_ATTEMPTS),
    }

# Validation automatique au chargement du module
if __name__ == "__main__":
    print("🔐 Configuration d'authentification ERP DG Inc.")
    print("=" * 50)
    
    # Validation
    is_valid = validate_auth_config()
    
    # Informations de sécurité
    security_info = get_security_info()
    print("\n📊 Informations de sécurité:")
    for key, value in security_info.items():
        print(f"  {key}: {value}")
    
    # Test des fonctions
    print("\n🧪 Test des fonctions:")
    test_password = "test123"
    hashed = hash_password(test_password)
    print(f"  Hash de '{test_password}': {hashed[:20]}...")
    
    # Test de vérification
    print(f"  Vérification admin/admin123: {verify_password('admin', 'admin123')}")
    print(f"  Vérification admin/wrong: {verify_password('admin', 'wrong')}")
    
    print("\n✅ Configuration chargée avec succès!")
else:
    # Validation silencieuse lors de l'import
    validate_auth_config()
