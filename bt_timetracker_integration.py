# bt_timetracker_integration.py - Extensions Bons de Travail pour intégration TimeTracker
# Fonctions à ajouter au gestionnaire et interface BT pour intégration complète

"""
Extensions Bons de Travail pour intégration TimeTracker
Ces fonctions enrichissent le gestionnaire BT avec les données TimeTracker
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Any

# =========================================================================
# NOUVELLES MÉTHODES À AJOUTER À LA CLASSE GestionnaireBonsTravail
# =========================================================================

def get_bt_avec_temps_reel(self, **filters) -> List[Dict]:
    """
    Récupère les BT enrichis avec les temps réels TimeTracker
    INTÉGRATION : BT + données TimeTracker complètes
    
    Args:
        **filters: Filtres pour les BT
        
    Returns:
        List[Dict]: BT avec temps réels et statistiques TimeTracker
    """
    try:
        # Récupérer les BT de base
        bts = self.get_bons_travail(**filters)
        
        # Enrichir chaque BT avec données TimeTracker
        for bt in bts:
            # Temps réels depuis TimeTracker
            temps_reel_data = self.db.get_temps_reel_bt_operations(bt['id'])
            bt['temps_reel_timetracker'] = temps_reel_data
            
            # Employés actuellement en pointage sur ce BT
            bt['pointages_actifs'] = self._get_pointages_actifs_bt(bt['id'])
            
            # Statistiques de productivité
            bt['stats_productivite'] = self._calculer_stats_productivite_bt(bt['id'])
            
            # Alertes spécifiques au BT
            bt['alertes_integration'] = self._generer_alertes_bt_timetracker(bt['id'], temps_reel_data)
        
        return bts
        
    except Exception as e:
        st.error(f"Erreur récupération BT avec temps réels: {e}")
        return []

def _get_pointages_actifs_bt(self, bt_id: int) -> List[Dict]:
    """
    Récupère les pointages actuellement actifs sur un BT
    
    Args:
        bt_id: ID du BT
        
    Returns:
        List[Dict]: Pointages actifs avec détails employés
    """
    try:
        query = """
            SELECT 
                te.id as time_entry_id,
                te.punch_in,
                te.hourly_rate,
                e.prenom || ' ' || e.nom as employe_nom,
                e.poste as employe_poste,
                o.description as operation_desc,
                o.sequence_number,
                (julianday('now') - julianday(te.punch_in)) * 24 as heures_depuis_debut,
                te.hourly_rate * ((julianday('now') - julianday(te.punch_in)) * 24) as cout_estime_actuel
            FROM time_entries te
            JOIN employees e ON te.employee_id = e.id
            JOIN operations o ON te.operation_id = o.id
            JOIN formulaires f ON o.project_id = f.project_id
            WHERE f.id = ? 
            AND te.punch_out IS NULL
            ORDER BY te.punch_in DESC
        """
        
        rows = self.db.execute_query(query, (bt_id,))
        
        pointages_actifs = []
        for row in rows:
            pointage = dict(row)
            
            # Formatage des données
            punch_in = datetime.fromisoformat(pointage['punch_in'])
            pointage['punch_in_formatted'] = punch_in.strftime('%H:%M')
            pointage['duree_formatee'] = f"{pointage['heures_depuis_debut']:.1f}h"
            
            # Alertes sur durée
            if pointage['heures_depuis_debut'] > 12:
                pointage['alerte_duree'] = 'CRITIQUE'
            elif pointage['heures_depuis_debut'] > 8:
                pointage['alerte_duree'] = 'ATTENTION'
            else:
                pointage['alerte_duree'] = 'NORMAL'
            
            pointages_actifs.append(pointage)
        
        return pointages_actifs
        
    except Exception as e:
        print(f"❌ Erreur pointages actifs BT {bt_id}: {e}")
        return []

def _calculer_stats_productivite_bt(self, bt_id: int) -> Dict[str, Any]:
    """
    Calcule les statistiques de productivité d'un BT basées sur TimeTracker
    
    Args:
        bt_id: ID du BT
        
    Returns:
        Dict: Statistiques de productivité
    """
    try:
        stats = {
            'efficacite_globale': 0,
            'variance_temps': 0,
            'taux_utilisation': 0,
            'cout_par_heure': 0,
            'performance_vs_estime': 'NEUTRE',
            'recommandations': []
        }
        
        # Récupérer les temps réels
        temps_data = self.db.get_temps_reel_bt_operations(bt_id)
        
        if not temps_data or not temps_data.get('synthese'):
            return stats
        
        synthese = temps_data['synthese']
        
        # Efficacité globale (temps estimé / temps réel)
        if synthese['temps_total_reel'] > 0:
            stats['efficacite_globale'] = (synthese['temps_total_estime'] / synthese['temps_total_reel']) * 100
        
        # Variance de temps
        stats['variance_temps'] = synthese['variance_globale']
        
        # Coût par heure
        if synthese['temps_total_reel'] > 0:
            stats['cout_par_heure'] = synthese['cout_total'] / synthese['temps_total_reel']
        
        # Performance vs estimé
        if synthese['progression_globale'] >= 100:
            if synthese['efficacite_globale'] >= 90:
                stats['performance_vs_estime'] = 'EXCELLENTE'
            elif synthese['efficacite_globale'] >= 70:
                stats['performance_vs_estime'] = 'BONNE'
            else:
                stats['performance_vs_estime'] = 'DÉPASSEMENT'
        elif synthese['progression_globale'] >= 80:
            stats['performance_vs_estime'] = 'EN_COURS'
        else:
            stats['performance_vs_estime'] = 'RETARD'
        
        # Recommandations basées sur les données
        recommandations = []
        
        if stats['efficacite_globale'] < 70:
            recommandations.append("⚠️ Efficacité faible - Réviser les estimations ou la planification")
        
        if abs(stats['variance_temps']) > synthese['temps_total_estime'] * 0.2:  # Variance > 20%
            recommandations.append("📊 Grande variance temps - Améliorer la précision des estimations")
        
        if synthese['operations_en_cours'] > synthese['operations_totales'] * 0.5:  # Plus de 50% en cours
            recommandations.append("🔄 Beaucoup d'opérations en parallèle - Prioriser les tâches")
        
        if not recommandations:
            recommandations.append("✅ Performance dans les normes")
        
        stats['recommandations'] = recommandations
        
        return stats
        
    except Exception as e:
        print(f"❌ Erreur stats productivité BT {bt_id}: {e}")
        return {}

def _generer_alertes_bt_timetracker(self, bt_id: int, temps_data: Dict) -> List[Dict]:
    """
    Génère des alertes basées sur l'intégration BT/TimeTracker
    
    Args:
        bt_id: ID du BT
        temps_data: Données des temps réels
        
    Returns:
        List[Dict]: Alertes avec niveaux et actions
    """
    try:
        alertes = []
        
        if not temps_data or not temps_data.get('synthese'):
            return alertes
        
        synthese = temps_data['synthese']
        
        # Alerte dépassement temps
        if synthese['variance_globale'] > synthese['temps_total_estime'] * 0.3:  # >30% dépassement
            alertes.append({
                'niveau': 'CRITIQUE',
                'type': 'DEPASSEMENT_TEMPS',
                'titre': 'Dépassement de temps important',
                'message': f"Dépassement de {synthese['variance_globale']:.1f}h ({synthese['variance_globale']/synthese['temps_total_estime']*100:.0f}%)",
                'action': 'Revoir la planification et ajuster les estimations'
            })
        
        # Alerte opérations bloquées
        operations_non_demarrees = synthese['nb_operations'] - synthese['operations_terminees'] - synthese['operations_en_cours']
        if operations_non_demarrees > 0 and synthese['operations_en_cours'] == 0:
            alertes.append({
                'niveau': 'ATTENTION',
                'type': 'OPERATIONS_BLOQUEES',
                'titre': 'Opérations en attente',
                'message': f"{operations_non_demarrees} opération(s) non démarrée(s)",
                'action': 'Vérifier les prérequis et assigner les tâches'
            })
        
        # Alerte faible progression
        if synthese['progression_globale'] < 20 and synthese['pointages_totaux'] > 5:  # Beaucoup de pointages mais peu de progression
            alertes.append({
                'niveau': 'ATTENTION',
                'type': 'FAIBLE_PROGRESSION',
                'titre': 'Progression lente',
                'message': f"Seulement {synthese['progression_globale']:.0f}% malgré {synthese['pointages_totaux']} pointages",
                'action': 'Analyser les obstacles et optimiser les processus'
            })
        
        # Alerte coût élevé
        if synthese['cout_total'] > 0:
            cout_par_heure = synthese['cout_total'] / synthese['temps_total_reel'] if synthese['temps_total_reel'] > 0 else 0
            if cout_par_heure > 120:  # >120$/h
                alertes.append({
                    'niveau': 'INFO',
                    'type': 'COUT_ELEVE',
                    'titre': 'Coût horaire élevé',
                    'message': f"Coût moyen: {cout_par_heure:.0f}$/h",
                    'action': 'Vérifier si justifié par la complexité des tâches'
                })
        
        return alertes
        
    except Exception as e:
        print(f"❌ Erreur génération alertes BT {bt_id}: {e}")
        return []

def demarrer_pointage_depuis_bt_interface(self, bt_id: int, employee_id: int, 
                                         operation_id: int, notes: str = "") -> Optional[int]:
    """
    Démarre un pointage depuis l'interface BT avec validations complètes
    INTÉGRATION : Interface BT → TimeTracker
    
    Args:
        bt_id: ID du BT
        employee_id: ID de l'employé
        operation_id: ID de l'opération
        notes: Notes de démarrage
        
    Returns:
        Optional[int]: ID du time_entry créé
    """
    try:
        # Vérifications préalables
        if not self._peut_demarrer_pointage_bt(bt_id, employee_id):
            return None
        
        # Utiliser la méthode d'intégration de la base
        time_entry_id = self.db.demarrer_pointage_depuis_bt(employee_id, bt_id, operation_id, notes)
        
        if time_entry_id:
            # Actions post-démarrage
            self._post_demarrage_pointage_bt(bt_id, employee_id, time_entry_id)
            
            logger.info(f"✅ Pointage démarré depuis BT {bt_id}: time_entry {time_entry_id}")
        
        return time_entry_id
        
    except Exception as e:
        st.error(f"Erreur démarrage pointage: {e}")
        logger.error(f"❌ Erreur démarrage pointage BT {bt_id}: {e}")
        return None

def _peut_demarrer_pointage_bt(self, bt_id: int, employee_id: int) -> bool:
    """
    Vérifie si un employé peut démarrer un pointage sur un BT
    
    Args:
        bt_id: ID du BT
        employee_id: ID de l'employé
        
    Returns:
        bool: True si le pointage peut être démarré
    """
    try:
        # Vérifier que l'employé est assigné au BT
        assignations = self._get_assignations_bt(bt_id)
        employes_assignes = [a['employe_id'] for a in assignations if a.get('statut') == 'ASSIGNÉ']
        
        if employee_id not in employes_assignes:
            st.error("❌ Employé non assigné à ce BT")
            return False
        
        # Vérifier qu'il n'y a pas déjà un pointage actif
        query_active = """
            SELECT COUNT(*) as count FROM time_entries 
            WHERE employee_id = ? AND punch_out IS NULL
        """
        result = self.db.execute_query(query_active, (employee_id,))
        
        if result and result[0]['count'] > 0:
            st.error("❌ Employé a déjà un pointage actif")
            return False
        
        # Vérifier le statut du BT
        bt_details = self.base.get_formulaire_details(bt_id)
        if not bt_details or bt_details['statut'] in ['TERMINÉ', 'ANNULÉ']:
            st.error("❌ BT terminé ou annulé")
            return False
        
        return True
        
    except Exception as e:
        st.error(f"Erreur vérification pointage: {e}")
        return False

def _post_demarrage_pointage_bt(self, bt_id: int, employee_id: int, time_entry_id: int):
    """
    Actions post-démarrage de pointage depuis BT
    
    Args:
        bt_id: ID du BT
        employee_id: ID de l'employé
        time_entry_id: ID du time_entry créé
    """
    try:
        # Enregistrer l'action dans l'historique BT
        self._enregistrer_validation(
            bt_id, employee_id, 'POINTAGE_DEMARRE',
            f"Pointage TimeTracker démarré - Entry {time_entry_id}"
        )
        
        # Notification aux autres assignés (optionnel)
        # self._notifier_equipe_pointage_demarre(bt_id, employee_id)
        
    except Exception as e:
        logger.error(f"❌ Erreur post-démarrage pointage BT {bt_id}: {e}")

def get_rapport_integration_bt_timetracker(self, periode_jours: int = 30) -> Dict[str, Any]:
    """
    Génère un rapport d'intégration spécifique BT/TimeTracker
    INTÉGRATION : Rapport de performance croisée
    
    Args:
        periode_jours: Période d'analyse
        
    Returns:
        Dict: Rapport d'intégration détaillé
    """
    try:
        # Utiliser la méthode d'intégration de la base
        rapport_base = self.db.get_rapport_productivite_integre(periode_jours)
        
        # Enrichir avec données spécifiques BT
        rapport_bt = {
            **rapport_base,
            'bt_specifique': {
                'bt_avec_integration': 0,
                'bt_sans_pointage': 0,
                'taux_integration_bt': 0,
                'top_bt_productifs': [],
                'alertes_bt': []
            }
        }
        
        # Analyse spécifique BT
        date_debut = (datetime.now() - timedelta(days=periode_jours)).strftime('%Y-%m-%d')
        
        query_bt_analysis = """
            SELECT 
                f.id as bt_id,
                f.numero_document,
                f.statut as bt_statut,
                f.priorite,
                p.nom_projet,
                COUNT(DISTINCT te.id) as pointages_period,
                COALESCE(SUM(te.total_hours), 0) as heures_period,
                COALESCE(SUM(te.total_cost), 0) as revenus_period,
                COUNT(DISTINCT te.employee_id) as employes_uniques,
                COALESCE(AVG(btav.pourcentage_realise), 0) as avancement_moyen
            FROM formulaires f
            JOIN projects p ON f.project_id = p.id
            LEFT JOIN time_entries te ON p.id = te.project_id 
                AND DATE(te.punch_in) >= ? AND te.total_cost IS NOT NULL
            LEFT JOIN bt_avancement btav ON f.id = btav.bt_id
            WHERE f.type_formulaire = 'BON_TRAVAIL'
            GROUP BY f.id
            ORDER BY revenus_period DESC
        """
        
        bt_analysis = self.db.execute_query(query_bt_analysis, (date_debut,))
        
        bt_avec_pointages = len([bt for bt in bt_analysis if dict(bt)['pointages_period'] > 0])
        bt_sans_pointages = len([bt for bt in bt_analysis if dict(bt)['pointages_period'] == 0])
        
        rapport_bt['bt_specifique'].update({
            'bt_avec_integration': bt_avec_pointages,
            'bt_sans_pointage': bt_sans_pointages,
            'taux_integration_bt': (bt_avec_pointages / len(bt_analysis) * 100) if bt_analysis else 0,
            'top_bt_productifs': [dict(bt) for bt in bt_analysis[:5]]
        })
        
        # Alertes BT spécifiques
        alertes_bt = []
        
        if bt_sans_pointages > 0:
            alertes_bt.append({
                'niveau': 'ATTENTION',
                'message': f"{bt_sans_pointages} BT sans pointage TimeTracker",
                'action': 'Vérifier l\'assignation et démarrer les pointages'
            })
        
        if rapport_bt['bt_specifique']['taux_integration_bt'] < 50:
            alertes_bt.append({
                'niveau': 'CRITIQUE',
                'message': f"Faible taux d'intégration BT/TimeTracker ({rapport_bt['bt_specifique']['taux_integration_bt']:.0f}%)",
                'action': 'Former les équipes à l\'utilisation intégrée'
            })
        
        rapport_bt['bt_specifique']['alertes_bt'] = alertes_bt
        
        return rapport_bt
        
    except Exception as e:
        st.error(f"Erreur rapport intégration: {e}")
        return {}


# =========================================================================
# NOUVELLES INTERFACES À AJOUTER AU MODULE BONS DE TRAVAIL
# =========================================================================

def render_bt_avec_timetracker_integration():
    """
    Interface BT enrichie avec intégration TimeTracker complète
    NOUVEAU : Vue BT avec données temps réel
    """
    
    st.markdown("#### 🔧 Bons de Travail avec TimeTracker")
    
    if 'gestionnaire_bt' not in st.session_state:
        st.error("❌ Gestionnaire BT non initialisé")
        return
    
    gestionnaire_bt = st.session_state.gestionnaire_bt
    
    # Récupérer BT avec temps réels
    bts_enrichis = gestionnaire_bt.get_bt_avec_temps_reel()
    
    if not bts_enrichis:
        st.info("Aucun BT trouvé")
        return
    
    # Filtres enrichis
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        statut_filter = st.selectbox("Statut BT:", 
                                   ["Tous"] + list(set(bt['statut'] for bt in bts_enrichis)))
    
    with col_filter2:
        priorite_filter = st.selectbox("Priorité:", 
                                     ["Toutes"] + list(set(bt.get('priorite', 'NORMAL') for bt in bts_enrichis)))
    
    with col_filter3:
        avec_pointage_filter = st.selectbox("Pointages:", 
                                          ["Tous", "Avec pointages actifs", "Sans pointage"])
    
    # Appliquer filtres
    bts_filtered = bts_enrichis
    
    if statut_filter != "Tous":
        bts_filtered = [bt for bt in bts_filtered if bt['statut'] == statut_filter]
    
    if priorite_filter != "Toutes":
        bts_filtered = [bt for bt in bts_filtered if bt.get('priorite') == priorite_filter]
    
    if avec_pointage_filter == "Avec pointages actifs":
        bts_filtered = [bt for bt in bts_filtered if bt.get('pointages_actifs')]
    elif avec_pointage_filter == "Sans pointage":
        bts_filtered = [bt for bt in bts_filtered if not bt.get('pointages_actifs')]
    
    st.markdown(f"#### 📊 {len(bts_filtered)} BT affiché(s)")
    
    # Affichage enrichi des BT
    for bt in bts_filtered:
        with st.expander(f"🔧 BT {bt['numero_document']} - {bt.get('project_nom', 'N/A')}", expanded=False):
            
            # En-tête avec métriques intégrées
            col_header1, col_header2, col_header3, col_header4 = st.columns(4)
            
            with col_header1:
                statut_color = "#059669" if bt['statut'] == 'TERMINÉ' else "#3b82f6"
                st.markdown(f"**Statut:** <span style='color:{statut_color};'>{bt['statut']}</span>", unsafe_allow_html=True)
                
                priorite_color = "#ef4444" if bt.get('priorite') == 'CRITIQUE' else "#f59e0b"
                st.markdown(f"**Priorité:** <span style='color:{priorite_color};'>{bt.get('priorite', 'NORMAL')}</span>", unsafe_allow_html=True)
            
            with col_header2:
                temps_data = bt.get('temps_reel_timetracker', {}).get('synthese', {})
                st.metric("⏱️ Temps Réel", f"{temps_data.get('temps_total_reel', 0):.1f}h")
                st.metric("💰 Coût Réel", f"{temps_data.get('cout_total', 0):.0f}$ CAD")
            
            with col_header3:
                st.metric("📊 Progression", f"{temps_data.get('progression_globale', 0):.0f}%")
                st.metric("⚡ Efficacité", f"{temps_data.get('efficacite_globale', 0):.0f}%")
            
            with col_header4:
                pointages_actifs = bt.get('pointages_actifs', [])
                st.metric("🟢 Pointages Actifs", len(pointages_actifs))
                st.metric("👥 Employés Assignés", len(bt.get('assignations', [])))
            
            # Alertes d'intégration
            alertes = bt.get('alertes_integration', [])
            if alertes:
                st.markdown("**🚨 Alertes:**")
                for alerte in alertes:
                    if alerte['niveau'] == 'CRITIQUE':
                        st.error(f"🔴 {alerte['titre']}: {alerte['message']}")
                    elif alerte['niveau'] == 'ATTENTION':
                        st.warning(f"🟡 {alerte['titre']}: {alerte['message']}")
                    else:
                        st.info(f"🔵 {alerte['titre']}: {alerte['message']}")
                    st.markdown(f"   *Action: {alerte['action']}*")
            
            # Pointages actifs détaillés
            if pointages_actifs:
                st.markdown("**🟢 Pointages en Cours:**")
                
                for pointage in pointages_actifs:
                    alerte_style = ""
                    if pointage['alerte_duree'] == 'CRITIQUE':
                        alerte_style = "background-color: #fee2e2; border-left: 4px solid #ef4444; padding: 10px;"
                    elif pointage['alerte_duree'] == 'ATTENTION':
                        alerte_style = "background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 10px;"
                    else:
                        alerte_style = "background-color: #d1fae5; border-left: 4px solid #10b981; padding: 10px;"
                    
                    st.markdown(f"""
                    <div style="{alerte_style} margin: 5px 0; border-radius: 6px;">
                        <strong>{pointage['employe_nom']}</strong> ({pointage['employe_poste']})<br>
                        📋 {pointage['operation_desc']} • ⏱️ {pointage['duree_formatee']} depuis {pointage['punch_in_formatted']}<br>
                        💰 Coût estimé: {pointage['cout_estime_actuel']:.0f}$ CAD
                    </div>
                    """, unsafe_allow_html=True)
            
            # Opérations avec temps réels
            operations_data = bt.get('temps_reel_timetracker', {}).get('operations', [])
            if operations_data:
                st.markdown("**📋 Détail des Opérations (TimeTracker):**")
                
                # Tableau des opérations avec progression
                df_operations = []
                for op in operations_data:
                    df_operations.append({
                        'Séq.': f"OP{op['sequence_number']:02d}",
                        'Description': op['description'][:30] + "..." if len(op['description']) > 30 else op['description'],
                        'Estimé': f"{op['temps_estime']:.1f}h",
                        'Réel': f"{op['temps_reel']:.1f}h",
                        'Progression': f"{op['progression']:.0f}%",
                        'Statut': op['statut_progression'],
                        'Coût': f"{op['cout_reel']:.0f}$",
                        'Employés': op['nb_employes'],
                        'Pointages': op['nb_pointages']
                    })
                
                if df_operations:
                    st.dataframe(pd.DataFrame(df_operations), use_container_width=True)
            
            # Actions intégrées
            st.markdown("**🎯 Actions Intégrées:**")
            
            col_action1, col_action2, col_action3, col_action4 = st.columns(4)
            
            with col_action1:
                if st.button("🟢 Démarrer Pointage", key=f"start_pointage_{bt['id']}"):
                    # Interface de démarrage de pointage
                    show_demarrage_pointage_modal(gestionnaire_bt, bt)
            
            with col_action2:
                if st.button("🔄 Sync Avancement", key=f"sync_{bt['id']}"):
                    if gestionnaire_bt.db.synchroniser_avancement_bt_depuis_timetracker(bt['id']):
                        st.success("✅ Avancement synchronisé!")
                        st.rerun()
                    else:
                        st.error("❌ Erreur synchronisation")
            
            with col_action3:
                if st.button("📊 Voir TimeTracker", key=f"view_tt_{bt['id']}"):
                    st.session_state.timetracker_filter_project = bt.get('project_id')
                    st.session_state.active_tab = 'timetracker'
                    st.info("🔗 Redirection vers TimeTracker avec filtrage automatique")
            
            with col_action4:
                if st.button("✅ Marquer Terminé", key=f"complete_{bt['id']}"):
                    # Vérifier progression avant terminer
                    if temps_data.get('progression_globale', 0) >= 100:
                        if gestionnaire_bt.marquer_bt_termine(bt['id'], 1, "Marqué terminé depuis interface intégrée"):
                            st.success("✅ BT terminé!")
                            st.rerun()
                    else:
                        st.warning(f"⚠️ BT seulement à {temps_data.get('progression_globale', 0):.0f}% - Confirmer?")


def show_demarrage_pointage_modal(gestionnaire_bt, bt_data: Dict):
    """
    Modal de démarrage de pointage depuis un BT
    NOUVEAU : Interface de pointage direct depuis BT
    
    Args:
        gestionnaire_bt: Instance du gestionnaire BT
        bt_data: Données du BT
    """
    
    st.markdown("---")
    st.markdown(f"### 🟢 Démarrer Pointage - BT {bt_data['numero_document']}")
    
    # Employés assignés
    assignations = bt_data.get('assignations', [])
    employes_assignes = [a for a in assignations if a.get('statut') == 'ASSIGNÉ']
    
    if not employes_assignes:
        st.error("❌ Aucun employé assigné à ce BT")
        return
    
    # Sélection employé
    emp_options = {a['employe_id']: f"{a['employe_nom']} ({a['employe_poste']})" for a in employes_assignes}
    selected_emp_id = st.selectbox(
        "👤 Employé:",
        options=list(emp_options.keys()),
        format_func=lambda x: emp_options[x],
        key=f"pointage_emp_{bt_data['id']}"
    )
    
    if not selected_emp_id:
        return
    
    # Opérations disponibles
    operations_data = bt_data.get('temps_reel_timetracker', {}).get('operations', [])
    operations_pointables = [op for op in operations_data if op['statut_progression'] not in ['TERMINÉ']]
    
    if not operations_pointables:
        st.warning("❌ Aucune opération disponible pour pointage")
        return
    
    # Sélection opération
    op_options = {
        op['operation_id']: f"OP{op['sequence_number']:02d} - {op['description']} ({op['progression']:.0f}%)"
        for op in operations_pointables
    }
    
    selected_op_id = st.selectbox(
        "🎯 Opération:",
        options=list(op_options.keys()),
        format_func=lambda x: op_options[x],
        key=f"pointage_op_{bt_data['id']}"
    )
    
    # Notes de démarrage
    notes_start = st.text_area(
        "📝 Notes de démarrage:",
        placeholder="Objectifs, outils nécessaires, consignes particulières...",
        key=f"pointage_notes_{bt_data['id']}"
    )
    
    # Actions
    col_start1, col_start2 = st.columns(2)
    
    with col_start1:
        if st.button("🟢 Confirmer Démarrage", key=f"confirm_start_{bt_data['id']}", use_container_width=True):
            time_entry_id = gestionnaire_bt.demarrer_pointage_depuis_bt_interface(
                bt_data['id'], selected_emp_id, selected_op_id, notes_start
            )
            
            if time_entry_id:
                st.success(f"✅ Pointage démarré! TimeEntry ID: {time_entry_id}")
                
                # Synchroniser automatiquement
                if gestionnaire_bt.db.synchroniser_avancement_bt_depuis_timetracker(bt_data['id']):
                    st.info("🔄 Avancement BT automatiquement synchronisé")
                
                st.rerun()
            else:
                st.error("❌ Impossible de démarrer le pointage")
    
    with col_start2:
        if st.button("❌ Annuler", key=f"cancel_start_{bt_data['id']}", use_container_width=True):
            st.rerun()


def render_dashboard_integration_bt_timetracker():
    """
    Dashboard spécialisé pour l'intégration BT/TimeTracker
    NOUVEAU : Vue d'ensemble complète de l'intégration
    """
    
    st.markdown("#### 🔗 Dashboard Intégration BT/TimeTracker")
    
    if 'gestionnaire_bt' not in st.session_state or 'timetracker_erp' not in st.session_state:
        st.error("❌ Gestionnaires non initialisés")
        return
    
    gestionnaire_bt = st.session_state.gestionnaire_bt
    
    # Générer rapport d'intégration
    rapport = gestionnaire_bt.get_rapport_integration_bt_timetracker()
    
    if not rapport:
        st.warning("Impossible de générer le rapport d'intégration")
        return
    
    # Métriques principales d'intégration
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    
    with col_m1:
        st.metric("🔧 BT Total", len(rapport.get('employes', [])) or rapport.get('bt_specifique', {}).get('bt_avec_integration', 0))
    
    with col_m2:
        bt_avec_integration = rapport.get('bt_specifique', {}).get('bt_avec_integration', 0)
        st.metric("🔗 BT Intégrés", bt_avec_integration)
    
    with col_m3:
        taux_integration = rapport.get('bt_specifique', {}).get('taux_integration_bt', 0)
        st.metric("📈 Taux Intégration", f"{taux_integration:.0f}%")
    
    with col_m4:
        total_heures = rapport.get('synthese', {}).get('heures_totales', 0)
        st.metric("⏱️ Heures Totales", f"{total_heures:.0f}h")
    
    with col_m5:
        total_revenus = rapport.get('synthese', {}).get('revenus_totaux', 0)
        st.metric("💰 Revenus Totaux", f"{total_revenus:.0f}$ CAD")
    
    # Graphiques d'intégration
    col_graph1, col_graph2 = st.columns(2)
    
    with col_graph1:
        # Performance par employé
        employes_data = rapport.get('employes', [])
        if employes_data:
            df_employes = pd.DataFrame(employes_data)
            
            fig_employes = px.scatter(
                df_employes, 
                x='heures_periode', 
                y='revenus_periode',
                size='bt_assignes',
                color='score_performance',
                hover_name='nom_employe',
                title="Performance Employés (BT vs TimeTracker)",
                labels={'heures_periode': 'Heures TimeTracker', 'revenus_periode': 'Revenus ($)'}
            )
            fig_employes.update_layout(height=400)
            st.plotly_chart(fig_employes, use_container_width=True)
    
    with col_graph2:
        # BT par niveau d'intégration
        bt_integration_data = {
            'Avec pointages': rapport.get('bt_specifique', {}).get('bt_avec_integration', 0),
            'Sans pointages': rapport.get('bt_specifique', {}).get('bt_sans_pointage', 0)
        }
        
        fig_integration = px.pie(
            values=list(bt_integration_data.values()),
            names=list(bt_integration_data.keys()),
            title="Répartition Intégration BT"
        )
        fig_integration.update_layout(height=400)
        st.plotly_chart(fig_integration, use_container_width=True)
    
    # Top BT productifs
    top_bt = rapport.get('bt_specifique', {}).get('top_bt_productifs', [])
    if top_bt:
        st.markdown("#### 🏆 Top BT Productifs")
        
        df_top_bt = pd.DataFrame(top_bt)
        df_top_bt = df_top_bt.head(5)  # Top 5
        
        # Graphique en barres
        fig_top_bt = px.bar(
            df_top_bt,
            x='numero_document',
            y='revenus_period',
            color='avancement_moyen',
            title="Top 5 BT par Revenus TimeTracker",
            labels={'revenus_period': 'Revenus ($)', 'numero_document': 'Numéro BT'}
        )
        fig_top_bt.update_layout(height=350)
        st.plotly_chart(fig_top_bt, use_container_width=True)
        
        # Tableau détaillé
        st.dataframe(df_top_bt[['numero_document', 'nom_projet', 'heures_period', 'revenus_period', 'avancement_moyen']], use_container_width=True)
    
    # Alertes d'intégration
    alertes_bt = rapport.get('bt_specifique', {}).get('alertes_bt', [])
    if alertes_bt:
        st.markdown("#### 🚨 Alertes Intégration")
        
        for alerte in alertes_bt:
            if alerte['niveau'] == 'CRITIQUE':
                st.error(f"🔴 **{alerte['message']}** - {alerte['action']}")
            elif alerte['niveau'] == 'ATTENTION':
                st.warning(f"🟡 **{alerte['message']}** - {alerte['action']}")
            else:
                st.info(f"🔵 **{alerte['message']}** - {alerte['action']}")
    
    # Recommandations d'amélioration
    recommandations = rapport.get('recommandations', [])
    if recommandations:
        st.markdown("#### 💡 Recommandations d'Amélioration")
        
        for rec in recommandations:
            st.info(f"💡 {rec}")
    
    # Actions rapides d'intégration
    st.markdown("#### ⚡ Actions Rapides")
    
    col_action1, col_action2, col_action3, col_action4 = st.columns(4)
    
    with col_action1:
        if st.button("🔄 Synchroniser Tous BT", use_container_width=True):
            # Synchroniser tous les BT actifs
            bts_actifs = gestionnaire_bt.get_bons_travail(statut=['VALIDÉ', 'EN COURS'])
            synced_count = 0
            
            for bt in bts_actifs:
                if gestionnaire_bt.db.synchroniser_avancement_bt_depuis_timetracker(bt['id']):
                    synced_count += 1
            
            st.success(f"✅ {synced_count}/{len(bts_actifs)} BT synchronisés")
            st.rerun()
    
    with col_action2:
        if st.button("📊 Export Rapport", use_container_width=True):
            # Générer export du rapport
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rapport_integration_bt_timetracker_{timestamp}.json"
            
            rapport_json = json.dumps(rapport, ensure_ascii=False, indent=2)
            
            st.download_button(
                label="💾 Télécharger JSON",
                data=rapport_json,
                file_name=filename,
                mime="application/json"
            )
    
    with col_action3:
        if st.button("🔍 Analyser Problèmes", use_container_width=True):
            # Analyser les problèmes d'intégration
            problemes = []
            
            # BT sans pointage depuis longtemps
            bts_sans_pointage = gestionnaire_bt.db.execute_query("""
                SELECT f.numero_document, f.date_creation
                FROM formulaires f
                LEFT JOIN time_entries te ON f.project_id = te.project_id
                WHERE f.type_formulaire = 'BON_TRAVAIL' 
                AND f.statut IN ('VALIDÉ', 'EN COURS')
                AND te.id IS NULL
                AND f.date_creation < DATE('now', '-7 days')
            """)
            
            if bts_sans_pointage:
                problemes.append(f"🔴 {len(bts_sans_pointage)} BT sans pointage depuis >7 jours")
            
            # Pointages longs sans BT
            pointages_orphelins = gestionnaire_bt.db.execute_query("""
                SELECT COUNT(*) as count
                FROM time_entries te
                LEFT JOIN operations o ON te.operation_id = o.id
                LEFT JOIN formulaires f ON o.project_id = f.project_id AND f.type_formulaire = 'BON_TRAVAIL'
                WHERE te.punch_out IS NULL
                AND f.id IS NULL
            """)
            
            if pointages_orphelins and pointages_orphelins[0]['count'] > 0:
                problemes.append(f"🟡 {pointages_orphelins[0]['count']} pointage(s) sans BT associé")
            
            if problemes:
                for probleme in problemes:
                    st.warning(probleme)
            else:
                st.success("✅ Aucun problème d'intégration détecté")
    
    with col_action4:
        if st.button("📈 Tendances", use_container_width=True):
            # Afficher tendances d'intégration
            st.info("📈 Analyse des tendances d'intégration sur les dernières semaines")
            
            # Récupérer données de tendance
            tendances = gestionnaire_bt.db.execute_query("""
                SELECT 
                    strftime('%Y-%W', te.punch_in) as semaine,
                    COUNT(DISTINCT f.id) as bt_actifs,
                    COUNT(te.id) as pointages,
                    SUM(te.total_hours) as heures_total
                FROM time_entries te
                JOIN operations o ON te.operation_id = o.id
                LEFT JOIN formulaires f ON o.project_id = f.project_id AND f.type_formulaire = 'BON_TRAVAIL'
                WHERE DATE(te.punch_in) >= DATE('now', '-8 weeks')
                AND te.total_cost IS NOT NULL
                GROUP BY semaine
                ORDER BY semaine
            """)
            
            if tendances:
                df_tendances = pd.DataFrame([dict(row) for row in tendances])
                
                fig_tendances = px.line(
                    df_tendances,
                    x='semaine',
                    y=['bt_actifs', 'pointages'],
                    title="Évolution Intégration BT/TimeTracker (8 semaines)"
                )
                st.plotly_chart(fig_tendances, use_container_width=True)
