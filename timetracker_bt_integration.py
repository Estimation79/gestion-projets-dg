# timetracker_bt_integration.py - Extensions TimeTracker pour intégration BT
# Fonctions à ajouter/modifier dans timetracker.py pour intégration complète avec Bons de Travail

"""
Extensions TimeTracker pour intégration Bons de Travail
Ces fonctions doivent être ajoutées à la classe TimeTrackerERP existante
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Any

# =========================================================================
# NOUVELLES MÉTHODES À AJOUTER À LA CLASSE TimeTrackerERP
# =========================================================================

def get_bt_assignes_employe_timetracker(self, employee_id: int) -> List[Dict]:
    """
    Récupère les BT assignés à un employé avec détails pour TimeTracker
    INTÉGRATION : Voir ses BT depuis TimeTracker
    
    Args:
        employee_id: ID de l'employé
        
    Returns:
        List[Dict]: BT assignés avec possibilités de pointage
    """
    try:
        # Utiliser la nouvelle méthode d'intégration de la base
        bt_assignes = self.db.get_bt_assignes_employe(employee_id)
        
        # Enrichir avec informations TimeTracker spécifiques
        for bt in bt_assignes:
            # Vérifier s'il y a un pointage actif sur ce BT
            bt['pointage_actif'] = self._has_active_timetracking_on_bt(employee_id, bt['bt_id'])
            
            # Calculer le temps total de l'employé sur ce BT
            bt['mes_heures_bt'] = self._get_employee_hours_on_bt(employee_id, bt['bt_id'])
            
            # Statut de disponibilité pour pointage
            bt['peut_pointer'] = (
                bt['bt_statut'] not in ['TERMINÉ', 'ANNULÉ'] and
                bt['assignation_statut'] == 'ASSIGNÉ' and
                len(bt.get('operations_pointage', [])) > 0
            )
        
        return bt_assignes
        
    except Exception as e:
        logger.error(f"❌ Erreur BT assignés employé TimeTracker {employee_id}: {e}")
        return []

def _has_active_timetracking_on_bt(self, employee_id: int, bt_id: int) -> Dict:
    """
    Vérifie s'il y a un pointage actif sur un BT spécifique
    
    Args:
        employee_id: ID de l'employé
        bt_id: ID du BT
        
    Returns:
        Dict: Informations du pointage actif ou {}
    """
    try:
        query = """
            SELECT te.*, o.description as operation_desc, o.sequence_number
            FROM time_entries te
            JOIN operations o ON te.operation_id = o.id
            JOIN formulaires f ON o.project_id = f.project_id
            WHERE te.employee_id = ? 
            AND f.id = ? 
            AND te.punch_out IS NULL
            ORDER BY te.punch_in DESC
            LIMIT 1
        """
        
        result = self.db.execute_query(query, (employee_id, bt_id))
        
        if result:
            entry = dict(result[0])
            punch_in_time = datetime.fromisoformat(entry['punch_in'])
            entry['elapsed_hours'] = (datetime.now() - punch_in_time).total_seconds() / 3600
            entry['estimated_cost'] = entry['elapsed_hours'] * entry['hourly_rate']
            return entry
        
        return {}
        
    except Exception as e:
        logger.error(f"❌ Erreur vérification pointage actif BT {bt_id}: {e}")
        return {}

def _get_employee_hours_on_bt(self, employee_id: int, bt_id: int) -> Dict:
    """
    Calcule les heures totales d'un employé sur un BT spécifique
    
    Args:
        employee_id: ID de l'employé
        bt_id: ID du BT
        
    Returns:
        Dict: Statistiques des heures de l'employé sur ce BT
    """
    try:
        query = """
            SELECT 
                COUNT(*) as nb_pointages,
                COALESCE(SUM(te.total_hours), 0) as heures_totales,
                COALESCE(SUM(te.total_cost), 0) as cout_total,
                MIN(te.punch_in) as premier_pointage,
                MAX(te.punch_out) as dernier_pointage,
                COUNT(DISTINCT te.operation_id) as operations_pointees
            FROM time_entries te
            JOIN operations o ON te.operation_id = o.id
            JOIN formulaires f ON o.project_id = f.project_id
            WHERE te.employee_id = ? 
            AND f.id = ? 
            AND te.total_cost IS NOT NULL
        """
        
        result = self.db.execute_query(query, (employee_id, bt_id))
        
        if result:
            return dict(result[0])
        
        return {
            'nb_pointages': 0, 'heures_totales': 0, 'cout_total': 0,
            'premier_pointage': None, 'dernier_pointage': None, 'operations_pointees': 0
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur heures employé BT {bt_id}: {e}")
        return {}

def demarrer_pointage_bt(self, employee_id: int, bt_id: int, operation_id: int, 
                        notes: str = "") -> Optional[int]:
    """
    Démarre un pointage TimeTracker depuis un BT avec intégration complète
    INTÉGRATION : Pointage direct depuis BT
    
    Args:
        employee_id: ID de l'employé
        bt_id: ID du BT
        operation_id: ID de l'opération
        notes: Notes de démarrage
        
    Returns:
        Optional[int]: ID du time_entry créé
    """
    try:
        # Utiliser la méthode d'intégration de la base
        time_entry_id = self.db.demarrer_pointage_depuis_bt(employee_id, bt_id, operation_id, notes)
        
        if time_entry_id:
            # Synchroniser automatiquement l'avancement du BT
            self.db.synchroniser_avancement_bt_depuis_timetracker(bt_id)
            
            logger.info(f"✅ Pointage BT démarré: employee {employee_id}, BT {bt_id}, entry {time_entry_id}")
        
        return time_entry_id
        
    except Exception as e:
        logger.error(f"❌ Erreur démarrage pointage BT {bt_id}: {e}")
        return None

def terminer_pointage_avec_sync_bt(self, employee_id: int, notes: str = "") -> Dict:
    """
    Termine un pointage avec synchronisation automatique des BT
    INTÉGRATION : Synchronisation automatique BT lors des punch out
    
    Args:
        employee_id: ID de l'employé
        notes: Notes de fin
        
    Returns:
        Dict: Détails de la session avec synchronisation BT
    """
    try:
        # Récupérer l'entrée active avant de la terminer
        current_entry = self.get_employee_current_entry(employee_id)
        if not current_entry:
            raise ValueError("Aucun pointage actif trouvé")
        
        # Identifier les BT impactés
        bt_impacts = []
        if current_entry.get('operation_id'):
            query_bt = """
                SELECT DISTINCT f.id as bt_id, f.numero_document
                FROM formulaires f
                JOIN operations o ON f.project_id = o.project_id
                WHERE o.id = ? AND f.type_formulaire = 'BON_TRAVAIL'
            """
            result_bt = self.db.execute_query(query_bt, (current_entry['operation_id'],))
            bt_impacts = [dict(row) for row in result_bt]
        
        # Terminer le pointage normalement
        session_details = self.punch_out(employee_id, notes)
        
        # Synchroniser tous les BT impactés
        bts_synchronises = []
        for bt in bt_impacts:
            if self.db.synchroniser_avancement_bt_depuis_timetracker(bt['bt_id']):
                bts_synchronises.append(bt['numero_document'])
        
        # Enrichir les détails de session
        session_details['bt_impacts'] = bt_impacts
        session_details['bt_synchronises'] = bts_synchronises
        session_details['integration_success'] = len(bts_synchronises) == len(bt_impacts)
        
        logger.info(f"✅ Pointage terminé avec sync BT: {len(bts_synchronises)} BT mis à jour")
        return session_details
        
    except Exception as e:
        logger.error(f"❌ Erreur fin pointage avec sync BT: {e}")
        # Fallback vers punch_out normal si erreur d'intégration
        return self.punch_out(employee_id, notes)

def get_dashboard_bt_integration(self) -> Dict[str, Any]:
    """
    Dashboard TimeTracker avec intégration BT
    INTÉGRATION : Vue unifiée TimeTracker/BT
    
    Returns:
        Dict: Données du dashboard intégré
    """
    try:
        # Utiliser la méthode d'intégration de la base
        dashboard_data = self.db.get_dashboard_integration_bt_timetracker()
        
        # Enrichir avec données TimeTracker spécifiques
        stats_tt = self.get_timetracker_statistics()
        
        dashboard_enrichi = {
            **dashboard_data,
            'timetracker_stats': stats_tt,
            'integration_ratio': self._calculate_integration_ratio(),
            'tendances': self._get_tendances_integration(),
            'prochaines_actions': self._get_prochaines_actions_bt()
        }
        
        return dashboard_enrichi
        
    except Exception as e:
        logger.error(f"❌ Erreur dashboard BT intégration: {e}")
        return {}

def _calculate_integration_ratio(self) -> Dict[str, float]:
    """
    Calcule les ratios d'intégration BT/TimeTracker
    
    Returns:
        Dict: Ratios d'intégration
    """
    try:
        # Ratio de pointages sur BT vs pointages totaux
        query_integration = """
            SELECT 
                COUNT(*) as total_pointages,
                COUNT(CASE WHEN f.type_formulaire = 'BON_TRAVAIL' THEN 1 END) as pointages_bt
            FROM time_entries te
            LEFT JOIN operations o ON te.operation_id = o.id
            LEFT JOIN formulaires f ON o.project_id = f.project_id
            WHERE DATE(te.punch_in) >= DATE('now', '-30 days')
            AND te.total_cost IS NOT NULL
        """
        
        result = self.db.execute_query(query_integration)
        
        if result and result[0]['total_pointages'] > 0:
            total = result[0]['total_pointages']
            bt_pointages = result[0]['pointages_bt']
            
            return {
                'ratio_pointages_bt': (bt_pointages / total) * 100,
                'pointages_hors_bt': total - bt_pointages,
                'integration_rate': (bt_pointages / total) * 100
            }
        
        return {'ratio_pointages_bt': 0, 'pointages_hors_bt': 0, 'integration_rate': 0}
        
    except Exception as e:
        logger.error(f"❌ Erreur calcul ratio intégration: {e}")
        return {}

def _get_tendances_integration(self) -> List[Dict]:
    """
    Récupère les tendances d'intégration BT/TimeTracker
    
    Returns:
        List[Dict]: Tendances par semaine/mois
    """
    try:
        query = """
            SELECT 
                strftime('%Y-%W', te.punch_in) as semaine,
                COUNT(*) as pointages_total,
                COUNT(CASE WHEN f.type_formulaire = 'BON_TRAVAIL' THEN 1 END) as pointages_bt,
                COALESCE(SUM(te.total_hours), 0) as heures_total,
                COALESCE(SUM(CASE WHEN f.type_formulaire = 'BON_TRAVAIL' THEN te.total_hours END), 0) as heures_bt
            FROM time_entries te
            LEFT JOIN operations o ON te.operation_id = o.id
            LEFT JOIN formulaires f ON o.project_id = f.project_id
            WHERE DATE(te.punch_in) >= DATE('now', '-8 weeks')
            AND te.total_cost IS NOT NULL
            GROUP BY semaine
            ORDER BY semaine DESC
        """
        
        rows = self.db.execute_query(query)
        
        tendances = []
        for row in rows:
            semaine_data = dict(row)
            
            if semaine_data['pointages_total'] > 0:
                semaine_data['ratio_bt'] = (semaine_data['pointages_bt'] / semaine_data['pointages_total']) * 100
                semaine_data['ratio_heures_bt'] = (semaine_data['heures_bt'] / semaine_data['heures_total']) * 100 if semaine_data['heures_total'] > 0 else 0
            else:
                semaine_data['ratio_bt'] = 0
                semaine_data['ratio_heures_bt'] = 0
            
            tendances.append(semaine_data)
        
        return tendances
        
    except Exception as e:
        logger.error(f"❌ Erreur tendances intégration: {e}")
        return []

def _get_prochaines_actions_bt(self) -> List[Dict]:
    """
    Récupère les prochaines actions recommandées pour l'intégration BT
    
    Returns:
        List[Dict]: Actions recommandées
    """
    try:
        actions = []
        
        # BT assignés sans pointage récent
        query_bt_sans_pointage = """
            SELECT 
                f.numero_document,
                f.priorite,
                f.date_echeance,
                p.nom_projet,
                COUNT(bta.employe_id) as employes_assignes
            FROM formulaires f
            JOIN bt_assignations bta ON f.id = bta.bt_id
            JOIN projects p ON f.project_id = p.id
            LEFT JOIN time_entries te ON p.id = te.project_id 
                AND DATE(te.punch_in) >= DATE('now', '-7 days')
                AND te.total_cost IS NOT NULL
            WHERE f.type_formulaire = 'BON_TRAVAIL'
            AND f.statut IN ('VALIDÉ', 'EN COURS')
            AND bta.statut = 'ASSIGNÉ'
            GROUP BY f.id
            HAVING COUNT(te.id) = 0
            ORDER BY f.priorite DESC, f.date_echeance ASC
            LIMIT 5
        """
        
        bt_sans_pointage = self.db.execute_query(query_bt_sans_pointage)
        
        for bt in bt_sans_pointage:
            actions.append({
                'type': 'BT_SANS_POINTAGE',
                'priorite': bt['priorite'],
                'titre': f"BT {bt['numero_document']} sans pointage",
                'description': f"Projet: {bt['nom_projet']} - {bt['employes_assignes']} employé(s) assigné(s)",
                'echeance': bt['date_echeance'],
                'action_recommandee': "Vérifier avec l'équipe et démarrer les pointages"
            })
        
        # Pointages longs à terminer
        query_pointages_longs = """
            SELECT 
                te.id,
                e.prenom || ' ' || e.nom as employe_nom,
                p.nom_projet,
                o.description as operation_desc,
                te.punch_in,
                (julianday('now') - julianday(te.punch_in)) * 24 as heures_depuis_debut
            FROM time_entries te
            JOIN employees e ON te.employee_id = e.id
            LEFT JOIN projects p ON te.project_id = p.id
            LEFT JOIN operations o ON te.operation_id = o.id
            WHERE te.punch_out IS NULL
            AND te.punch_in < datetime('now', '-8 hours')
            ORDER BY heures_depuis_debut DESC
            LIMIT 3
        """
        
        pointages_longs = self.db.execute_query(query_pointages_longs)
        
        for pointage in pointages_longs:
            actions.append({
                'type': 'POINTAGE_LONG',
                'priorite': 'URGENT' if pointage['heures_depuis_debut'] > 12 else 'NORMAL',
                'titre': f"Pointage long - {pointage['employe_nom']}",
                'description': f"Actif depuis {pointage['heures_depuis_debut']:.1f}h sur {pointage['projet'] or 'Projet non défini'}",
                'action_recommandee': "Contacter l'employé pour terminer le pointage"
            })
        
        return actions
        
    except Exception as e:
        logger.error(f"❌ Erreur prochaines actions BT: {e}")
        return []


# =========================================================================
# NOUVELLES INTERFACES À AJOUTER AU MODULE TIMETRACKER
# =========================================================================

def show_bt_integration_interface():
    """
    Interface d'intégration BT dans TimeTracker
    NOUVEAU : Onglet dédié à l'intégration BT
    """
    
    st.markdown("### 🔧 Intégration Bons de Travail")
    
    if 'timetracker_erp' not in st.session_state:
        st.error("❌ TimeTracker non initialisé")
        return
    
    tt = st.session_state.timetracker_erp
    
    # Dashboard intégré
    dashboard_data = tt.get_dashboard_bt_integration()
    
    if not dashboard_data:
        st.warning("Impossible de charger les données d'intégration")
        return
    
    # Métriques d'intégration
    st.markdown("#### 📊 Vue d'Ensemble Intégrée")
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    bt_metrics = dashboard_data.get('bt_metrics', {})
    tt_metrics = dashboard_data.get('timetracker_metrics', {})
    integration_metrics = dashboard_data.get('integration_metrics', {})
    
    with col_m1:
        st.metric("🔧 BT Total", bt_metrics.get('total_bt', 0))
        st.metric("⚡ BT En Cours", bt_metrics.get('bt_en_cours', 0))
    
    with col_m2:
        st.metric("⏱️ Pointages Jour", tt_metrics.get('total_pointages_jour', 0))
        st.metric("🟢 Actifs", tt_metrics.get('pointages_actifs', 0))
    
    with col_m3:
        st.metric("🔗 BT avec Pointages", integration_metrics.get('bt_avec_pointages', 0))
        st.metric("👥 Employés BT+TT", integration_metrics.get('employes_bt_timetracker', 0))
    
    with col_m4:
        ratio_integration = dashboard_data.get('integration_ratio', {}).get('integration_rate', 0)
        st.metric("📈 Taux Intégration", f"{ratio_integration:.1f}%")
        st.metric("💰 Revenus BT", f"{integration_metrics.get('revenus_bt_total', 0):.0f}$")
    
    # Alertes d'intégration
    alertes = dashboard_data.get('alertes', [])
    if alertes:
        st.markdown("#### 🚨 Alertes")
        for alerte in alertes:
            if alerte['niveau'] == 'CRITIQUE':
                st.error(f"🔴 **{alerte['message']}** - {alerte['action']}")
            elif alerte['niveau'] == 'ATTENTION':
                st.warning(f"🟡 **{alerte['message']}** - {alerte['action']}")
            else:
                st.info(f"🔵 **{alerte['message']}** - {alerte['action']}")
    
    # Top performers intégrés
    top_performers = dashboard_data.get('top_performers', [])
    if top_performers:
        st.markdown("#### 🏆 Top Performers (BT + TimeTracker)")
        
        df_performers = pd.DataFrame(top_performers)
        
        # Graphique des top performers
        if len(df_performers) > 0:
            fig = px.bar(df_performers, 
                        x='nom_employe', 
                        y='revenus_mois',
                        color='bt_assignes',
                        title="Revenus Mensuels par Employé",
                        labels={'revenus_mois': 'Revenus ($)', 'nom_employe': 'Employé'})
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Tableau détaillé
        st.dataframe(df_performers, use_container_width=True)
    
    # Prochaines actions
    prochaines_actions = dashboard_data.get('prochaines_actions', [])
    if prochaines_actions:
        st.markdown("#### 📋 Actions Recommandées")
        
        for action in prochaines_actions:
            if action['priorite'] == 'URGENT':
                st.error(f"🚨 **{action['titre']}**")
            elif action['priorite'] == 'CRITIQUE':
                st.warning(f"⚠️ **{action['titre']}**")
            else:
                st.info(f"💡 **{action['titre']}**")
            
            st.markdown(f"   - {action['description']}")
            st.markdown(f"   - *Action: {action['action_recommandee']}*")


def show_mes_bt_interface():
    """
    Interface "Mes BT" dans TimeTracker
    NOUVEAU : Voir ses BT assignés depuis TimeTracker
    """
    
    st.markdown("### 🔧 Mes Bons de Travail")
    
    if 'timetracker_erp' not in st.session_state:
        st.error("❌ TimeTracker non initialisé")
        return
    
    tt = st.session_state.timetracker_erp
    
    # Sélection d'employé (pour demo - en prod, utiliser l'employé connecté)
    employees = tt.get_all_employees()
    if not employees:
        st.warning("Aucun employé trouvé")
        return
    
    emp_options = {emp['id']: emp['full_name_with_role'] for emp in employees}
    selected_emp_id = st.selectbox(
        "👤 Employé:",
        options=list(emp_options.keys()),
        format_func=lambda x: emp_options[x],
        key="bt_mes_bt_employe"
    )
    
    if not selected_emp_id:
        return
    
    # Récupérer les BT assignés
    mes_bt = tt.get_bt_assignes_employe_timetracker(selected_emp_id)
    
    if not mes_bt:
        st.info("✅ Aucun BT assigné actuellement")
        return
    
    st.markdown(f"#### 📋 {len(mes_bt)} BT Assigné(s)")
    
    # Affichage des BT avec actions de pointage
    for bt in mes_bt:
        with st.expander(f"🔧 BT {bt['numero_document']} - {bt['nom_projet']}", expanded=True):
            
            # Informations du BT
            col_info1, col_info2, col_info3 = st.columns(3)
            
            with col_info1:
                statut_color = "#059669" if bt['bt_statut'] == 'TERMINÉ' else "#3b82f6"
                st.markdown(f"**Statut:** <span style='color:{statut_color};font-weight:600;'>{bt['bt_statut']}</span>", unsafe_allow_html=True)
                
                priorite_color = "#ef4444" if bt['priorite'] == 'CRITIQUE' else "#f59e0b" if bt['priorite'] == 'URGENT' else "#10b981"
                st.markdown(f"**Priorité:** <span style='color:{priorite_color};font-weight:600;'>{bt['priorite']}</span>", unsafe_allow_html=True)
            
            with col_info2:
                st.markdown(f"**Client:** {bt.get('client_nom', 'N/A')}")
                st.markdown(f"**Échéance:** {bt.get('date_echeance', 'N/A')}")
                
                if bt.get('jours_restants') is not None:
                    jours = bt['jours_restants']
                    if jours < 0:
                        st.markdown(f"**⚠️ Retard:** {abs(jours)} jour(s)")
                    elif jours <= 3:
                        st.markdown(f"**🟡 Urgent:** {jours} jour(s) restant(s)")
                    else:
                        st.markdown(f"**📅 Délai:** {jours} jour(s)")
            
            with col_info3:
                avancement = bt.get('avancement_moyen', 0)
                st.metric("📊 Avancement", f"{avancement:.0f}%")
                
                mes_heures = bt.get('mes_heures_bt', {})
                st.metric("⏱️ Mes Heures", f"{mes_heures.get('heures_totales', 0):.1f}h")
            
            # Pointage actif sur ce BT
            pointage_actif = bt.get('pointage_actif', {})
            if pointage_actif:
                st.warning(f"🟢 **Pointage en cours** sur {pointage_actif.get('operation_desc', 'opération')} depuis {pointage_actif.get('elapsed_hours', 0):.1f}h")
                
                if st.button(f"🔴 Terminer Pointage", key=f"stop_bt_{bt['bt_id']}"):
                    session_details = tt.terminer_pointage_avec_sync_bt(selected_emp_id, "Terminé depuis Mes BT")
                    
                    if session_details.get('integration_success'):
                        st.success(f"✅ Pointage terminé et BT synchronisé!")
                        if session_details.get('bt_synchronises'):
                            st.info(f"🔄 BT mis à jour: {', '.join(session_details['bt_synchronises'])}")
                    else:
                        st.success("✅ Pointage terminé")
                        if session_details.get('bt_impacts'):
                            st.warning("⚠️ Synchronisation BT partielle")
                    
                    st.rerun()
            
            # Actions de pointage
            elif bt['peut_pointer']:
                operations = bt.get('operations_pointage', [])
                
                if operations:
                    st.markdown("**🎯 Démarrer un pointage:**")
                    
                    # Sélection d'opération
                    op_options = {
                        op['operation_id']: f"{op['description_pointage']} ({op['progression_temps']:.0f}% - {op['temps_reel_timetracker']:.1f}h)"
                        for op in operations if op['peut_pointer']
                    }
                    
                    if op_options:
                        selected_op_id = st.selectbox(
                            "Opération:",
                            options=list(op_options.keys()),
                            format_func=lambda x: op_options[x],
                            key=f"bt_op_select_{bt['bt_id']}"
                        )
                        
                        notes_start = st.text_input(
                            "Notes de démarrage (optionnel):",
                            key=f"bt_notes_{bt['bt_id']}",
                            placeholder="Détails du travail à effectuer..."
                        )
                        
                        if st.button(f"🟢 Démarrer Pointage", key=f"start_bt_{bt['bt_id']}"):
                            time_entry_id = tt.demarrer_pointage_bt(
                                selected_emp_id, bt['bt_id'], selected_op_id, notes_start
                            )
                            
                            if time_entry_id:
                                st.success(f"✅ Pointage démarré! Entry ID: {time_entry_id}")
                                st.info("🔄 Avancement BT automatiquement synchronisé")
                                st.rerun()
                            else:
                                st.error("❌ Erreur lors du démarrage du pointage")
                    else:
                        st.info("📋 Toutes les opérations sont terminées ou non disponibles")
                else:
                    st.info("📋 Aucune opération définie pour ce BT")
            else:
                st.info("🔒 BT non disponible pour pointage (terminé ou non assigné)")
            
            # Historique mes pointages sur ce BT
            if mes_heures.get('nb_pointages', 0) > 0:
                with st.expander(f"📈 Mon Historique ({mes_heures['nb_pointages']} pointages)", expanded=False):
                    col_hist1, col_hist2, col_hist3 = st.columns(3)
                    
                    with col_hist1:
                        st.metric("⏱️ Total Heures", f"{mes_heures['heures_totales']:.1f}h")
                    with col_hist2:
                        st.metric("💰 Total Coût", f"{mes_heures['cout_total']:.0f}$ CAD")
                    with col_hist3:
                        st.metric("🔧 Opérations", mes_heures['operations_pointees'])
                    
                    if mes_heures.get('premier_pointage'):
                        st.markdown(f"**Premier pointage:** {mes_heures['premier_pointage']}")
                    if mes_heures.get('dernier_pointage'):
                        st.markdown(f"**Dernier pointage:** {mes_heures['dernier_pointage']}")


def show_pointage_bt_rapide():
    """
    Interface de pointage rapide depuis BT
    NOUVEAU : Widget de pointage rapide BT
    """
    
    st.markdown("### ⚡ Pointage Rapide BT")
    
    if 'timetracker_erp' not in st.session_state:
        st.error("❌ TimeTracker non initialisé")
        return
    
    tt = st.session_state.timetracker_erp
    
    # Sélection employé
    employees = tt.get_all_employees()
    if not employees:
        st.warning("Aucun employé trouvé")
        return
    
    emp_options = {emp['id']: emp['name'] for emp in employees}
    selected_emp_id = st.selectbox(
        "👤 Employé:",
        options=list(emp_options.keys()),
        format_func=lambda x: emp_options[x],
        key="pointage_rapide_employe"
    )
    
    if not selected_emp_id:
        return
    
    # Vérifier pointage actif
    current_entry = tt.get_employee_current_entry(selected_emp_id)
    
    if current_entry:
        # Employé déjà en pointage
        st.warning(f"🟢 **Pointage actif** depuis {current_entry['punch_in_formatted']}")
        st.markdown(f"**Projet:** {current_entry['project_name']}")
        st.markdown(f"**Tâche:** {current_entry['task_name']}")
        st.markdown(f"**Durée:** {current_entry['elapsed_hours']:.1f}h")
        st.markdown(f"**Coût estimé:** {current_entry['estimated_cost']:.0f}$ CAD")
        
        if st.button("🔴 Terminer Pointage", use_container_width=True):
            session_details = tt.terminer_pointage_avec_sync_bt(selected_emp_id, "Terminé depuis pointage rapide")
            
            if session_details:
                st.success(f"✅ Pointage terminé: {session_details['total_hours']:.2f}h")
                if session_details.get('bt_synchronises'):
                    st.info(f"🔄 BT synchronisés: {', '.join(session_details['bt_synchronises'])}")
                st.rerun()
    
    else:
        # Employé libre - proposer BT assignés
        mes_bt = tt.get_bt_assignes_employe_timetracker(selected_emp_id)
        
        if mes_bt:
            bt_disponibles = [bt for bt in mes_bt if bt['peut_pointer']]
            
            if bt_disponibles:
                st.success(f"✅ {len(bt_disponibles)} BT disponible(s) pour pointage")
                
                # Sélection BT rapide
                bt_options = {
                    bt['bt_id']: f"BT {bt['numero_document']} - {bt['nom_projet']} ({bt['priorite']})"
                    for bt in bt_disponibles
                }
                
                selected_bt_id = st.selectbox(
                    "🔧 BT à pointer:",
                    options=list(bt_options.keys()),
                    format_func=lambda x: bt_options[x],
                    key="pointage_rapide_bt"
                )
                
                if selected_bt_id:
                    selected_bt = next(bt for bt in bt_disponibles if bt['bt_id'] == selected_bt_id)
                    operations = selected_bt.get('operations_pointage', [])
                    
                    operations_disponibles = [op for op in operations if op['peut_pointer']]
                    
                    if operations_disponibles:
                        # Sélection opération
                        op_options = {
                            op['operation_id']: f"{op['description_pointage']} ({op['progression_temps']:.0f}%)"
                            for op in operations_disponibles
                        }
                        
                        selected_op_id = st.selectbox(
                            "🎯 Opération:",
                            options=list(op_options.keys()),
                            format_func=lambda x: op_options[x],
                            key="pointage_rapide_operation"
                        )
                        
                        if st.button("🟢 Démarrer Pointage", use_container_width=True):
                            time_entry_id = tt.demarrer_pointage_bt(selected_emp_id, selected_bt_id, selected_op_id, "Pointage rapide BT")
                            
                            if time_entry_id:
                                st.success(f"✅ Pointage BT démarré! Entry: {time_entry_id}")
                                st.rerun()
                            else:
                                st.error("❌ Erreur démarrage pointage")
                    else:
                        st.info("📋 Aucune opération disponible pour ce BT")
            else:
                st.info("📋 Aucun BT disponible pour pointage")
        else:
            st.info("🔧 Aucun BT assigné à cet employé")
            
            # Fallback vers pointage normal
            st.markdown("---")
            st.markdown("**Alternative: Pointage normal**")
            
            if st.button("🟢 Pointage Projet Standard", use_container_width=True):
                st.info("Utilisez l'onglet 'Pointage Employés' pour un pointage projet standard")


# =========================================================================
# MODIFICATION DE L'INTERFACE PRINCIPALE TIMETRACKER
# Ajout des nouveaux onglets d'intégration BT
# =========================================================================

def show_timetracker_interface_with_bt_integration():
    """
    Interface TimeTracker modifiée avec intégration BT complète
    VERSION MODIFIÉE de show_timetracker_interface()
    """
    
    # Vérifier l'accès à la base ERP
    if 'erp_db' not in st.session_state:
        st.error("❌ Accès TimeTracker nécessite une session ERP active")
        st.info("Veuillez redémarrer l'application ERP.")
        return
    
    # Initialiser le TimeTracker ERP unifié
    if 'timetracker_erp' not in st.session_state:
        st.session_state.timetracker_erp = TimeTrackerERP(st.session_state.erp_db)
    
    tt = st.session_state.timetracker_erp
    
    # En-tête TimeTracker avec intégration BT
    st.markdown("""
    <div class='project-header' style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h2 style='margin: 0; text-align: center;'>⏱️ TimeTracker Pro + 🔧 Bons de Travail</h2>
        <p style='margin: 5px 0 0 0; text-align: center; opacity: 0.9;'>🗄️ Architecture SQLite Unifiée • Intégration Complète BT</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Statistiques enrichies avec données BT
    dashboard_data = tt.get_dashboard_bt_integration()
    
    if dashboard_data:
        # Métriques intégrées
        col1, col2, col3, col4, col5 = st.columns(5)
        
        tt_metrics = dashboard_data.get('timetracker_metrics', {})
        bt_metrics = dashboard_data.get('bt_metrics', {})
        integration_metrics = dashboard_data.get('integration_metrics', {})
        
        with col1:
            st.metric("👥 Employés ERP", len(tt.get_all_employees()))
        with col2:
            st.metric("🟢 Pointages Actifs", tt_metrics.get('pointages_actifs', 0))
        with col3:
            st.metric("🔧 BT Assignés", bt_metrics.get('bt_en_cours', 0))
        with col4:
            st.metric("⏱️ Heures Jour", f"{tt_metrics.get('heures_jour', 0):.1f}h")
        with col5:
            ratio_integration = dashboard_data.get('integration_ratio', {}).get('integration_rate', 0)
            st.metric("🔗 Intégration BT", f"{ratio_integration:.0f}%")
    
    # Navigation TimeTracker ÉTENDUE avec BT
    tab_pointage, tab_mes_bt, tab_pointage_rapide, tab_integration, tab_analytics, tab_productivity, tab_admin, tab_system = st.tabs([
        "🕐 Pointage Employés", 
        "🔧 Mes BT",
        "⚡ Pointage Rapide BT",
        "🔗 Intégration BT", 
        "📊 Analytics & Rapports", 
        "🏭 Productivité", 
        "⚙️ Administration", 
        "ℹ️ Système"
    ])
    
    with tab_pointage:
        # Interface de pointage existante (inchangée)
        show_employee_timetracking_interface(tt)
    
    with tab_mes_bt:
        # NOUVEAU: Interface Mes BT
        show_mes_bt_interface()
    
    with tab_pointage_rapide:
        # NOUVEAU: Pointage rapide BT
        show_pointage_bt_rapide()
    
    with tab_integration:
        # NOUVEAU: Dashboard d'intégration
        show_bt_integration_interface()
    
    with tab_analytics:
        # Interface analytics existante (peut être enrichie avec données BT)
        show_analytics_interface(tt)
    
    with tab_productivity:
        # Interface productivité existante
        show_productivity_interface(tt)
    
    with tab_admin:
        # Interface admin existante
        show_admin_interface(tt)
    
    with tab_system:
        # Interface système existante
        show_system_interface()
