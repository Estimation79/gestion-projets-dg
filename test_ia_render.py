#!/usr/bin/env python
"""
Test spécifique pour la connexion IA sur Render
"""
import os
import sys

print("=== Test IA + Base de données sur Render ===\n")

# 1. Test du module database_config
print("1. TEST database_config.py:")
try:
    from database_config import DATABASE_PATH, get_database_path
    print(f"   ✓ Import réussi")
    print(f"   - DATABASE_PATH: {DATABASE_PATH}")
    print(f"   - Existe: {os.path.exists(DATABASE_PATH)}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

# 2. Test ERPDatabase
print("\n2. TEST ERPDatabase:")
try:
    from erp_database import ERPDatabase
    db = ERPDatabase(DATABASE_PATH)
    print(f"   ✓ Connexion établie")
    
    # Test requête
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM projects")
        count = cursor.fetchone()[0]
        print(f"   - Nombre de projets: {count}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

# 3. Simuler l'environnement Streamlit pour tester ERPContextProvider
print("\n3. TEST ERPContextProvider (simulation Streamlit):")

# Mock Streamlit
class MockSessionState:
    def __init__(self):
        self.data = {}
    def get(self, key, default=None):
        return self.data.get(key, default)
    def __setitem__(self, key, value):
        self.data[key] = value
    def __contains__(self, key):
        return key in self.data

class MockStreamlit:
    session_state = MockSessionState()

sys.modules['streamlit'] = MockStreamlit()

# Maintenant tester
try:
    from ia_erp_context import ERPContextProvider, create_erp_context_for_ai
    
    print("   ✓ Import réussi")
    
    # Créer le provider
    provider = ERPContextProvider()
    print(f"   - Mode démo: {provider.demo_mode}")
    print(f"   - Base de données connectée: {provider.erp_db is not None}")
    
    # Tester le contexte
    context = provider.get_context_summary()
    print(f"   - Modules disponibles: {context.get('modules_available', [])}")
    print(f"   - Statut DB: {context.get('database_status', 'Inconnu')}")
    
    # Tester une recherche
    projects = provider.search_projects(limit=5)
    if projects.get('success'):
        print(f"   - Projets trouvés: {projects.get('count', 0)}")
    else:
        print(f"   - Erreur recherche: {projects.get('error', 'Erreur inconnue')}")
        
    # Générer le contexte IA
    print("\n4. CONTEXTE IA GÉNÉRÉ:")
    ai_context = create_erp_context_for_ai()
    print(ai_context[:500] + "..." if len(ai_context) > 500 else ai_context)
    
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Fin du test IA ===")