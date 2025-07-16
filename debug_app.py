import streamlit as st
import os
import sys

st.set_page_config(
    page_title="🔧 Debug ERP",
    layout="wide"
)

st.title("🔧 Debug ERP - Test de Base")

# Test 1: Streamlit de base
st.success("✅ Streamlit fonctionne!")

# Test 2: Variables d'environnement
st.subheader("🌍 Variables d'environnement")
env_vars = ['RENDER', 'PYTHONPATH', 'PORT']
for var in env_vars:
    value = os.environ.get(var, 'Non définie')
    st.write(f"**{var}:** {value}")

# Test 3: Modules critiques
st.subheader("📦 Test des imports critiques")
try:
    import sqlite3
    st.success("✅ sqlite3 disponible")
except ImportError as e:
    st.error(f"❌ sqlite3: {e}")

try:
    from erp_database import ERPDatabase
    st.success("✅ erp_database importé")
except ImportError as e:
    st.error(f"❌ erp_database: {e}")
    st.code(str(e))

# Test 4: Création de base de données simple
try:
    db_path = "test_debug.db"
    if os.path.exists(db_path):
        st.info(f"📁 Base test existe: {os.path.getsize(db_path)} bytes")
    else:
        st.warning("⚠️ Aucune base test trouvée")
except Exception as e:
    st.error(f"❌ Erreur test DB: {e}")

st.subheader("🎯 Actions recommandées")
if st.button("🚀 Tester l'app principale"):
    st.info("Redirection vers l'app principale...")
    st.rerun()
