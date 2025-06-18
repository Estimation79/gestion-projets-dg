# employee_timetracker.py - Interface Employé Simple
# ERP Production DG Inc. - Interface de pointage simplifiée pour employés
# Utilise les classes TimeTrackerERP et ERPDatabase existantes

import streamlit as st
import os
from datetime import datetime
from erp_database import ERPDatabase
from timetracker import TimeTrackerERP

# Configuration page Streamlit
st.set_page_config(
    page_title="🏭 Pointage Employés - DG Inc.",
    page_icon="⏱️",
    layout="centered"
)

def init_database():
    """Initialise la connexion à la base ERP existante"""
    if 'erp_db' not in st.session_state:
        # Utiliser le même chemin que l'ERP principal
        st.session_state.erp_db = ERPDatabase("erp_production_dg.db")
    
    if 'timetracker' not in st.session_state:
        st.session_state.timetracker = TimeTrackerERP(st.session_state.erp_db)

def get_employee_list():
    """Récupère la liste des employés actifs"""
    try:
        employees = st.session_state.timetracker.get_all_employees()
        return {emp['id']: f"{emp['name']} - {emp.get('poste', 'N/A')}" 
                for emp in employees}
    except Exception as e:
        st.error(f"Erreur récupération employés: {e}")
        return {}

def get_bt_list_for_employee(employee_id):
    """Récupère les BTs assignés à un employé"""
    try:
        bts_assignes = st.session_state.timetracker.get_bts_assignes_employe(employee_id)
        return {bt['bt_id']: f"{bt['numero_document']} - {bt.get('nom_projet', 'N/A')}" 
                for bt in bts_assignes}
    except Exception as e:
        st.error(f"Erreur récupération BTs: {e}")
        return {}

def display_current_status(employee_id):
    """Affiche le statut de pointage actuel"""
    try:
        current_entry = st.session_state.timetracker.get_employee_current_entry(employee_id)
        
        if current_entry:
            punch_in_time = datetime.fromisoformat(current_entry['punch_in'])
            elapsed_hours = current_entry['elapsed_hours']
            
            # Déterminer si c'est un pointage BT ou projet normal
            if current_entry.get('formulaire_bt_id'):
                # Récupérer les détails du BT
                bt_details = st.session_state.timetracker.get_bt_details_for_timetracker(current_entry['formulaire_bt_id'])
                bt_numero = bt_details.get('numero_document', 'BT Inconnu') if bt_details else 'BT Inconnu'
                
                st.success(f"""
                ✅ **POINTÉ SUR BON DE TRAVAIL**
                - 🔧 BT: {bt_numero}
                - 📋 Projet: {current_entry.get('project_name', 'N/A')}
                - ⏰ Depuis: {punch_in_time.strftime('%H:%M')}
                - 📊 Durée: {elapsed_hours:.1f}h
                - 💰 Coût estimé: {current_entry.get('estimated_cost', 0):.2f}$ CAD
                """)
            else:
                st.success(f"""
                ✅ **POINTÉ ACTUELLEMENT**
                - 📋 Projet: {current_entry.get('project_name', 'N/A')}
                - 🔧 Tâche: {current_entry.get('task_name', 'N/A')}
                - ⏰ Depuis: {punch_in_time.strftime('%H:%M')}
                - 📊 Durée: {elapsed_hours:.1f}h
                - 💰 Coût estimé: {current_entry.get('estimated_cost', 0):.2f}$ CAD
                """)
            return True
        else:
            st.info("🟡 **PAS DE POINTAGE ACTIF**")
            return False
    except Exception as e:
        st.error(f"Erreur vérification statut: {e}")
        return False

def handle_punch_in(employee_id, bt_id):
    """Gère le punch in sur un BT"""
    try:
        entry_id = st.session_state.timetracker.punch_in_sur_bt(
            employee_id, bt_id, notes="Pointage interface employé"
        )
        
        if entry_id:
            st.success(f"✅ Punch in réussi ! ID: {entry_id}")
            st.rerun()
        else:
            st.error("❌ Erreur lors du punch in")
    except Exception as e:
        st.error(f"Erreur punch in: {e}")

def handle_punch_out(employee_id):
    """Gère le punch out"""
    try:
        session_details = st.session_state.timetracker.punch_out(
            employee_id, notes="Fin pointage interface employé"
        )
        
        if session_details:
            st.success(f"""
            ✅ **Punch out réussi !**
            - ⏱️ Durée: {session_details['total_hours']:.2f}h
            - 💰 Coût: {session_details['total_cost']:.2f}$ CAD
            - 📋 Projet: {session_details.get('project_name', 'N/A')}
            """)
            st.rerun()
        else:
            st.error("❌ Erreur lors du punch out")
    except Exception as e:
        st.error(f"Erreur punch out: {e}")

def main():
    # Initialisation
    init_database()
    
    # En-tête
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;
                text-align: center;'>
        <h2>🏭 Pointage Employés - DG Inc.</h2>
        <p>Interface simplifiée pour les employés</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sélection employé
    employees = get_employee_list()
    if not employees:
        st.error("❌ Aucun employé trouvé")
        st.info("Veuillez vérifier la connexion à la base de données ERP.")
        return
    
    selected_employee_id = st.selectbox(
        "👤 Sélectionner votre nom:",
        options=list(employees.keys()),
        format_func=lambda x: employees[x],
        key="employee_select"
    )
    
    if not selected_employee_id:
        return
    
    # Affichage statut actuel
    is_clocked_in = display_current_status(selected_employee_id)
    
    st.markdown("---")
    
    if not is_clocked_in:
        # Interface Punch In
        st.markdown("### 🟢 Démarrer Pointage")
        
        # Choix entre BT et projet général
        mode_pointage = st.radio(
            "Type de pointage:",
            ["🔧 Bon de Travail assigné", "📋 Projet général"],
            horizontal=True
        )
        
        if mode_pointage == "🔧 Bon de Travail assigné":
            # Pointage sur BT
            bts_list = get_bt_list_for_employee(selected_employee_id)
            if not bts_list:
                st.warning("❌ Aucun Bon de Travail assigné")
                st.info("Contactez votre superviseur pour obtenir des assignations de BT.")
                return
            
            selected_bt_id = st.selectbox(
                "🔧 Sélectionner le Bon de Travail:",
                options=list(bts_list.keys()),
                format_func=lambda x: bts_list[x],
                key="bt_select"
            )
            
            # Afficher détails du BT sélectionné
            if selected_bt_id:
                bt_details = st.session_state.timetracker.get_bt_details_for_timetracker(selected_bt_id)
                if bt_details:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📋 Projet", bt_details.get('nom_projet', 'N/A'))
                    with col2:
                        statut_icon = {'VALIDÉ': '✅', 'EN COURS': '⚡', 'TERMINÉ': '🎯'}.get(bt_details.get('statut', ''), '📋')
                        st.metric("🚦 Statut", f"{statut_icon} {bt_details.get('statut', 'N/A')}")
                    with col3:
                        priorite_icon = {'CRITIQUE': '🔴', 'URGENT': '🟡', 'NORMAL': '🟢'}.get(bt_details.get('priorite', ''), '⚪')
                        st.metric("⚡ Priorité", f"{priorite_icon} {bt_details.get('priorite', 'N/A')}")
            
            if st.button("🟢 DÉMARRER POINTAGE BT", use_container_width=True, type="primary"):
                handle_punch_in(selected_employee_id, selected_bt_id)
        
        else:
            # Pointage projet général (mode fallback)
            st.info("🔧 Mode projet général - Pour pointer sur un projet sans BT spécifique")
            
            # Récupérer les projets actifs
            projects = st.session_state.timetracker.get_active_projects()
            if not projects:
                st.warning("❌ Aucun projet actif disponible")
                return
            
            project_options = {p['id']: f"{p['project_name']} - {p['client_name']}" for p in projects}
            selected_project_id = st.selectbox(
                "📋 Sélectionner le projet:",
                options=list(project_options.keys()),
                format_func=lambda x: project_options[x],
                key="project_select"
            )
            
            if st.button("🟢 DÉMARRER POINTAGE PROJET", use_container_width=True):
                try:
                    entry_id = st.session_state.timetracker.punch_in(
                        selected_employee_id, 
                        selected_project_id, 
                        notes="Pointage interface employé - projet général"
                    )
                    st.success(f"✅ Pointage projet démarré ! ID: {entry_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur punch in projet: {e}")
    
    else:
        # Interface Punch Out
        st.markdown("### 🔴 Terminer Pointage")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔴 TERMINER POINTAGE", use_container_width=True, type="secondary"):
                handle_punch_out(selected_employee_id)
        
        with col2:
            if st.button("⏸️ PAUSE DÉJEUNER", use_container_width=True):
                try:
                    session_details = st.session_state.timetracker.punch_out(
                        selected_employee_id, notes="Pause déjeuner - interface employé"
                    )
                    if session_details:
                        st.info(f"⏸️ Pause déjeuner enregistrée. Durée: {session_details['total_hours']:.2f}h")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erreur pause: {e}")
    
    # Informations supplémentaires
    st.markdown("---")
    
    with st.expander("ℹ️ Informations", expanded=False):
        st.markdown("""
        ### 📋 Guide d'utilisation
        
        **🟢 Pour commencer un pointage:**
        1. Sélectionnez votre nom dans la liste
        2. Choisissez un Bon de Travail assigné ou un projet général
        3. Cliquez sur "DÉMARRER POINTAGE"
        
        **🔴 Pour terminer un pointage:**
        1. Cliquez sur "TERMINER POINTAGE" 
        2. Ou "PAUSE DÉJEUNER" pour une pause
        
        **💡 Conseils:**
        - Privilégiez toujours les Bons de Travail assignés
        - N'oubliez pas de terminer vos pointages
        - Contactez votre superviseur en cas de problème
        """)
        
        # Afficher quelques statistiques simples si demandé
        if st.button("📊 Mes statistiques du jour"):
            try:
                today = datetime.now().strftime('%Y-%m-%d')
                entries_today = st.session_state.timetracker.get_employee_time_entries(
                    selected_employee_id, limit=50, date_filter=today
                )
                
                completed_today = [e for e in entries_today if e.get('total_hours')]
                total_hours_today = sum(e['total_hours'] for e in completed_today)
                total_cost_today = sum(e['total_cost'] for e in completed_today)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("⏱️ Heures aujourd'hui", f"{total_hours_today:.1f}h")
                with col2:
                    st.metric("💰 Revenus générés", f"{total_cost_today:.0f}$ CAD")
                with col3:
                    st.metric("📝 Pointages", len(completed_today))
                
            except Exception as e:
                st.error(f"Erreur récupération statistiques: {e}")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        🏭 ERP Production DG Inc. - Interface Employé TimeTracker v1.0<br>
        Données synchronisées en temps réel avec la base ERP principale
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
