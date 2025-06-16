# formulaires/bons_travail/interface_bt.py
# Interface utilisateur pour les Bons de Travail

"""
Interface utilisateur pour les Bons de Travail.
Contient tous les composants d'affichage et d'interaction pour les BT.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .gestionnaire_bt import GestionnaireBonsTravail
from ..utils.helpers import (
    get_projets_actifs,
    get_employes_actifs,
    get_operations_projet,
    formater_montant,
    formater_delai,
    generer_couleur_statut,
    generer_couleur_priorite
)
from ..core.types_formulaires import UNITES_MESURE


def render_bons_travail_tab(gestionnaire):
    """
    Interface principale pour les Bons de Travail.
    
    Args:
        gestionnaire: Instance du gestionnaire de formulaires de base
    """
    st.markdown("### 🔧 Bons de Travail")
    
    # Initialiser le gestionnaire spécialisé
    if 'gestionnaire_bt' not in st.session_state:
        st.session_state.gestionnaire_bt = GestionnaireBonsTravail(gestionnaire)
    
    gestionnaire_bt = st.session_state.gestionnaire_bt
    
    # Actions rapides avec métriques
    _render_actions_rapides_bt(gestionnaire_bt)
    
    # Affichage selon l'action sélectionnée
    action = st.session_state.get('form_action', 'list_bon_travail')
    
    if action == "create_bon_travail":
        render_bon_travail_form(gestionnaire_bt)
    elif action == "list_bon_travail":
        render_bon_travail_list(gestionnaire_bt)
    elif action == "stats_bon_travail":
        render_bon_travail_stats(gestionnaire_bt)
    elif action == "productivite_bt":
        render_rapport_productivite(gestionnaire_bt)


def _render_actions_rapides_bt(gestionnaire_bt):
    """
    Affiche les actions rapides avec métriques en temps réel.
    
    Args:
        gestionnaire_bt: Instance du gestionnaire BT
    """
    # Métriques rapides
    stats = gestionnaire_bt.get_statistiques_bt()
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        total_bt = stats.get('total', 0)
        st.metric("🔧 Total BT", total_bt)
    
    with col_m2:
        en_cours = stats.get('en_cours', 0)
        st.metric("⚡ En Cours", en_cours)
    
    with col_m3:
        termines = stats.get('par_statut', {}).get('TERMINÉ', 0)
        st.metric("✅ Terminés", termines)
    
    with col_m4:
        montant_total = stats.get('montant_total', 0)
        st.metric("💰 Montant Total", formater_montant(montant_total))
    
    # Actions rapides
    col_action1, col_action2, col_action3, col_action4 = st.columns(4)
    
    with col_action1:
        if st.button("➕ Nouveau BT", use_container_width=True, key="bt_nouveau"):
            st.session_state.form_action = "create_bon_travail"
            st.rerun()
    
    with col_action2:
        if st.button("📋 Liste Complète", use_container_width=True, key="bt_liste"):
            st.session_state.form_action = "list_bon_travail"
            st.rerun()
    
    with col_action3:
        if st.button("📊 Statistiques", use_container_width=True, key="bt_stats"):
            st.session_state.form_action = "stats_bon_travail"
            st.rerun()
    
    with col_action4:
        if st.button("📈 Productivité", use_container_width=True, key="bt_productivite"):
            st.session_state.form_action = "productivite_bt"
            st.rerun()


def render_bon_travail_form(gestionnaire_bt):
    """
    Formulaire de création de Bon de Travail avec logique métier BT.
    
    Args:
        gestionnaire_bt: Instance du gestionnaire BT spécialisé
    """
    st.markdown("#### ➕ Nouveau Bon de Travail")
    
    with st.form("bon_travail_form", clear_on_submit=True):
        # En-tête du formulaire
        col1, col2 = st.columns(2)
        
        with col1:
            numero_bt = gestionnaire_bt.base.generer_numero_document('BON_TRAVAIL')
            st.text_input("N° Bon de Travail", value=numero_bt, disabled=True)
            
            # Sélection projet (OBLIGATOIRE pour BT)
            projets = get_projets_actifs()
            if not projets:
                st.error("❌ Aucun projet actif. Créez d'abord un projet dans le module Projets.")
                return
            
            projet_options = [("", "Sélectionner un projet")] + [(p['id'], f"#{p['id']} - {p['nom_projet']}") for p in projets]
            projet_id = st.selectbox(
                "Projet *",
                options=[p[0] for p in projet_options],
                format_func=lambda x: next((p[1] for p in projet_options if p[0] == x), ""),
                help="Projet obligatoire pour les Bons de Travail"
            )
            
            date_creation = st.date_input("Date de Création", datetime.now().date())
        
        with col2:
            priorite = st.selectbox("Priorité", gestionnaire_bt.base.priorites, index=0)
            
            # Employé responsable
            employes = get_employes_actifs()
            employe_options = [("", "Sélectionner un responsable")] + [(e['id'], f"{e['prenom']} {e['nom']} - {e['poste']}") for e in employes]
            employe_id = st.selectbox(
                "Responsable *",
                options=[e[0] for e in employe_options],
                format_func=lambda x: next((e[1] for e in employe_options if e[0] == x), "")
            )
            
            date_echeance = st.date_input("Date d'Échéance", datetime.now().date() + timedelta(days=7))
        
        # Description du travail
        description = st.text_area("Description du Travail *", height=100,
                                  placeholder="Décrivez précisément le travail à effectuer...")
        
        # SPÉCIFICITÉ BT : Opérations à réaliser depuis le projet
        st.markdown("##### 🔧 Opérations à Réaliser")
        
        operations_selectionnees = []
        if projet_id:
            operations_projet = get_operations_projet(projet_id)
            
            if operations_projet:
                st.info(f"📋 {len(operations_projet)} opération(s) disponible(s) pour ce projet")
                
                operations_selectionnees = st.multiselect(
                    "Opérations à inclure dans ce BT",
                    options=[op['id'] for op in operations_projet],
                    format_func=lambda x: next((f"#{op['sequence']} - {op['description']}" for op in operations_projet if op['id'] == x), ""),
                    help="Sélectionnez les opérations que ce BT doit couvrir"
                )
                
                # Affichage détaillé des opérations sélectionnées
                if operations_selectionnees:
                    st.markdown("**Opérations sélectionnées :**")
                    temps_total_estime = 0
                    
                    for op_id in operations_selectionnees:
                        operation = next((op for op in operations_projet if op['id'] == op_id), None)
                        if operation:
                            col_op1, col_op2, col_op3 = st.columns([2, 1, 1])
                            with col_op1:
                                st.text(f"#{operation['sequence']} - {operation['description']}")
                            with col_op2:
                                temps_estime = operation.get('temps_estime', 0)
                                st.text(f"{temps_estime}h estimées")
                                temps_total_estime += temps_estime
                            with col_op3:
                                st.text(f"Statut: {operation.get('statut', 'À FAIRE')}")
                    
                    st.success(f"⏱️ Temps total estimé: {temps_total_estime}h")
            else:
                st.info("Ce projet n'a pas encore d'opérations définies. Le BT sera créé sans opérations spécifiques.")
        else:
            st.info("Sélectionnez un projet pour voir les opérations disponibles")
        
        # SPÉCIFICITÉ BT : Équipe assignée
        st.markdown("##### 👥 Équipe Assignée")
        
        employes_assignes = st.multiselect(
            "Employés Assignés à ce BT",
            options=[e['id'] for e in employes],
            format_func=lambda x: next((f"{e['prenom']} {e['nom']} - {e['poste']}" for e in employes if e['id'] == x), ""),
            help="Employés qui travailleront sur ce BT (en plus du responsable)"
        )
        
        # Affichage de l'équipe
        if employes_assignes:
            st.markdown("**Équipe assignée :**")
            for emp_id in employes_assignes:
                employe = next((e for e in employes if e['id'] == emp_id), None)
                if employe:
                    st.text(f"• {employe['prenom']} {employe['nom']} ({employe['poste']})")
        
        # SPÉCIFICITÉ BT : Matériaux requis
        st.markdown("##### 📦 Matériaux Requis")
        
        # Interface dynamique pour matériaux
        col_mat_header = st.columns([3, 1, 1, 1.5])
        with col_mat_header[0]:
            st.markdown("**Description**")
        with col_mat_header[1]:
            st.markdown("**Quantité**")
        with col_mat_header[2]:
            st.markdown("**Unité**")
        with col_mat_header[3]:
            st.markdown("**Coût Unit. Estimé**")
        
        materiaux_lines = []
        montant_total_estime = 0
        
        for i in range(5):  # 5 lignes de matériaux
            col_mat = st.columns([3, 1, 1, 1.5])
            
            with col_mat[0]:
                desc = st.text_input("", key=f"bt_mat_desc_{i}", placeholder="Description matériau")
            with col_mat[1]:
                qty = st.number_input("", min_value=0.0, key=f"bt_mat_qty_{i}", format="%.2f", step=0.1)
            with col_mat[2]:
                unite = st.selectbox("", UNITES_MESURE, key=f"bt_mat_unit_{i}", index=0)
            with col_mat[3]:
                cout = st.number_input("", min_value=0.0, key=f"bt_mat_cost_{i}", format="%.2f", step=0.01)
            
            if desc and qty > 0:
                montant_ligne = qty * cout
                montant_total_estime += montant_ligne
                
                materiaux_lines.append({
                    'description': desc,
                    'quantite': qty,
                    'unite': unite,
                    'prix_unitaire': cout,
                    'montant_ligne': montant_ligne
                })
        
        # Affichage du montant total estimé
        if montant_total_estime > 0:
            st.success(f"💰 Coût matériaux estimé: {formater_montant(montant_total_estime)}")
        
        # Notes spéciales et instructions
        notes_speciales = st.text_area("Notes et Instructions Spéciales", height=80,
                                      placeholder="Consignes de sécurité, instructions particulières, contraintes...")
        
        # Récapitulatif avant soumission
        if projet_id and employe_id and description:
            projet_selectionne = next((p for p in projets if p['id'] == projet_id), None)
            responsable_selectionne = next((e for e in employes if e['id'] == employe_id), None)
            
            st.markdown(f"""
            <div style='background:#f0f9ff;padding:1rem;border-radius:8px;border-left:4px solid #3b82f6;'>
                <h5 style='color:#1e40af;margin:0;'>📋 Récapitulatif BT</h5>
                <p style='margin:0.5rem 0 0 0;'><strong>N° BT:</strong> {numero_bt}</p>
                <p style='margin:0;'><strong>Projet:</strong> {projet_selectionne['nom_projet'] if projet_selectionne else 'N/A'}</p>
                <p style='margin:0;'><strong>Responsable:</strong> {f"{responsable_selectionne['prenom']} {responsable_selectionne['nom']}" if responsable_selectionne else 'N/A'}</p>
                <p style='margin:0;'><strong>Équipe:</strong> {len(employes_assignes)} employé(s) assigné(s)</p>
                <p style='margin:0;'><strong>Opérations:</strong> {len(operations_selectionnees)} opération(s)</p>
                <p style='margin:0;'><strong>Matériaux:</strong> {len(materiaux_lines)} ligne(s) - {formater_montant(montant_total_estime)}</p>
                <p style='margin:0;'><strong>Échéance:</strong> {date_echeance.strftime('%d/%m/%Y')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Boutons de soumission
        st.markdown("---")
        col_submit1, col_submit2, col_submit3 = st.columns(3)
        
        with col_submit1:
            submit_brouillon = st.form_submit_button("💾 Sauver comme Brouillon", use_container_width=True)
        with col_submit2:
            submit_valide = st.form_submit_button("✅ Créer et Valider", use_container_width=True)
        with col_submit3:
            submit_urgent = st.form_submit_button("🚨 Urgent - Démarrer Immédiatement", use_container_width=True)
        
        # Traitement de la soumission
        if submit_brouillon or submit_valide or submit_urgent:
            # Validation
            if not projet_id or not employe_id or not description:
                st.error("❌ Veuillez remplir tous les champs obligatoires (*)")
                return
            
            # Déterminer le statut
            if submit_brouillon:
                statut = 'BROUILLON'
            elif submit_urgent:
                statut = 'VALIDÉ'
                priorite = 'CRITIQUE'
            else:
                statut = 'VALIDÉ'
            
            # Construction des notes complètes avec contexte BT
            notes_completes = f"""=== BON DE TRAVAIL ===
Description : {description}

=== OPÉRATIONS SÉLECTIONNÉES ===
{len(operations_selectionnees)} opération(s) : {', '.join(map(str, operations_selectionnees)) if operations_selectionnees else 'Aucune opération spécifique'}

=== ÉQUIPE ASSIGNÉE ===
Responsable : {next((f"{e['prenom']} {e['nom']}" for e in employes if e['id'] == employe_id), 'N/A')}
Équipe : {len(employes_assignes)} employé(s) assigné(s)

=== MATÉRIAUX REQUIS ===
{len(materiaux_lines)} ligne(s) de matériaux
Coût estimé : {formater_montant(montant_total_estime)}

=== NOTES ET INSTRUCTIONS ===
{notes_speciales or 'Aucune instruction particulière'}"""
            
            # Préparation des données BT
            data = {
                'type_formulaire': 'BON_TRAVAIL',
                'numero_document': numero_bt,
                'project_id': projet_id,
                'employee_id': employe_id,
                'statut': statut,
                'priorite': priorite,
                'date_creation': date_creation,
                'date_echeance': date_echeance,
                'montant_total': montant_total_estime,
                'notes': notes_completes,
                'lignes': materiaux_lines,
                # Données spécifiques BT
                'operations_selectionnees': operations_selectionnees,
                'employes_assignes': employes_assignes,
                'description': description,  # Pour validation
                'temps_estime_total': sum(op.get('temps_estime', 0) for op in get_operations_projet(projet_id) if op['id'] in operations_selectionnees)
            }
            
            # Création du BT via le gestionnaire spécialisé
            bt_id = gestionnaire_bt.creer_bon_travail(data)
            
            if bt_id:
                # Messages de succès personnalisés
                if submit_urgent:
                    st.success(f"🚨 Bon de Travail URGENT {numero_bt} créé et prêt à démarrer!")
                    st.info("⚡ L'équipe assignée a été notifiée pour démarrage immédiat.")
                else:
                    st.success(f"✅ Bon de Travail {numero_bt} créé avec succès!")
                
                # Actions suivantes
                col_next1, col_next2, col_next3 = st.columns(3)
                with col_next1:
                    if st.button("📋 Voir la Liste", use_container_width=True, key="bt_voir_liste"):
                        st.session_state.form_action = "list_bon_travail"
                        st.rerun()
                with col_next2:
                    if st.button("👁️ Voir Détails", use_container_width=True, key="bt_voir_details"):
                        st.session_state.selected_formulaire_id = bt_id
                        st.session_state.show_formulaire_modal = True
                with col_next3:
                    if st.button("➕ Créer un Autre", use_container_width=True, key="bt_creer_autre"):
                        st.rerun()


def render_bon_travail_list(gestionnaire_bt):
    """
    Liste des Bons de Travail avec fonctionnalités avancées BT.
    
    Args:
        gestionnaire_bt: Instance du gestionnaire BT spécialisé
    """
    st.markdown("#### 📋 Liste des Bons de Travail")
    
    bons_travail = gestionnaire_bt.get_bons_travail()
    
    if not bons_travail:
        st.info("Aucun Bon de Travail créé.")
        if st.button("➕ Créer le Premier BT", use_container_width=True, key="bt_premier"):
            st.session_state.form_action = "create_bon_travail"
            st.rerun()
        return
    
    # Métriques rapides de la liste
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        st.metric("📋 Total BT", len(bons_travail))
    with col_m2:
        en_cours = len([bt for bt in bons_travail if bt['statut'] in ['VALIDÉ', 'EN COURS']])
        st.metric("⚡ En Cours", en_cours)
    with col_m3:
        termines = len([bt for bt in bons_travail if bt['statut'] == 'TERMINÉ'])
        st.metric("✅ Terminés", termines)
    with col_m4:
        montant_total = sum(bt.get('montant_total', 0) for bt in bons_travail)
        st.metric("💰 Montant Total", formater_montant(montant_total))
    
    # Filtres spécifiques BT
    with st.expander("🔍 Filtres Avancés", expanded=False):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            filtre_statut = st.multiselect("Statut", gestionnaire_bt.base.statuts, default=gestionnaire_bt.base.statuts)
        with col_f2:
            filtre_priorite = st.multiselect("Priorité", gestionnaire_bt.base.priorites, default=gestionnaire_bt.base.priorites)
        with col_f3:
            # Filtre par projet
            projets_liste = list(set([bt.get('project_nom', 'N/A') for bt in bons_travail if bt.get('project_nom')]))
            filtre_projet = st.multiselect("Projet", ['Tous'] + projets_liste, default=['Tous'])
        with col_f4:
            # Filtre par responsable
            responsables_liste = list(set([bt.get('employee_nom', 'N/A') for bt in bons_travail if bt.get('employee_nom')]))
            filtre_responsable = st.multiselect("Responsable", ['Tous'] + responsables_liste, default=['Tous'])
        
        col_search, col_avancement = st.columns(2)
        with col_search:
            recherche = st.text_input("🔍 Rechercher", placeholder="Numéro, projet, description...")
        with col_avancement:
            filtre_avancement = st.selectbox("Avancement", ["Tous", "0%", "1-50%", "51-99%", "100%"])
    
    # Application des filtres
    bts_filtres = []
    for bt in bons_travail:
        # Filtres de base
        if bt['statut'] not in filtre_statut:
            continue
        if bt['priorite'] not in filtre_priorite:
            continue
        
        # Filtre projet
        if 'Tous' not in filtre_projet and bt.get('project_nom', 'N/A') not in filtre_projet:
            continue
        
        # Filtre responsable
        if 'Tous' not in filtre_responsable and bt.get('employee_nom', 'N/A') not in filtre_responsable:
            continue
        
        # Filtre recherche
        if recherche:
            terme = recherche.lower()
            if not any(terme in str(bt.get(field, '')).lower() for field in ['numero_document', 'project_nom', 'notes', 'employee_nom']):
                continue
        
        # Filtre avancement
        if filtre_avancement != "Tous":
            avancement = bt.get('avancement', {}).get('pourcentage', 0)
            if filtre_avancement == "0%" and avancement != 0:
                continue
            elif filtre_avancement == "1-50%" and not (1 <= avancement <= 50):
                continue
            elif filtre_avancement == "51-99%" and not (51 <= avancement <= 99):
                continue
            elif filtre_avancement == "100%" and avancement != 100:
                continue
        
        bts_filtres.append(bt)
    
    # Affichage des résultats
    st.markdown(f"**{len(bts_filtres)} Bon(s) de Travail trouvé(s)**")
    
    if bts_filtres:
        # Tri
        col_sort1, col_sort2 = st.columns(2)
        with col_sort1:
            tri_par = st.selectbox("Trier par", ["Date création", "Priorité", "Avancement", "Projet", "Responsable"])
        with col_sort2:
            tri_ordre = st.selectbox("Ordre", ["Décroissant", "Croissant"])
        
        # Application du tri
        if tri_par == "Date création":
            bts_filtres.sort(key=lambda x: x.get('date_creation', ''), reverse=(tri_ordre == "Décroissant"))
        elif tri_par == "Priorité":
            ordre_priorite = {'CRITIQUE': 3, 'URGENT': 2, 'NORMAL': 1}
            bts_filtres.sort(key=lambda x: ordre_priorite.get(x.get('priorite', 'NORMAL'), 1), reverse=(tri_ordre == "Décroissant"))
        elif tri_par == "Avancement":
            bts_filtres.sort(key=lambda x: x.get('avancement', {}).get('pourcentage', 0), reverse=(tri_ordre == "Décroissant"))
        
        # Affichage liste enrichie BT
        for bt in bts_filtres:
            with st.container():
                col_info, col_avancement, col_equipe, col_actions = st.columns([3, 1, 1, 1])
                
                with col_info:
                    # Indicateurs visuels
                    priorite_color = generer_couleur_priorite(bt['priorite'])
                    statut_color = generer_couleur_statut(bt['statut'])
                    
                    st.markdown(f"""
                    **BT {bt['numero_document']}** 
                    <span style='color:{priorite_color}'>●</span> {bt['priorite']} | 
                    <span style='color:{statut_color}'>●</span> {bt['statut']}
                    
                    **Projet:** {bt.get('project_nom', 'N/A')}  
                    **Responsable:** {bt.get('employee_nom', 'N/A')}  
                    **Échéance:** {bt.get('date_echeance', 'N/A')}
                    """, unsafe_allow_html=True)
                
                with col_avancement:
                    avancement = bt.get('avancement', {})
                    pourcentage = avancement.get('pourcentage', 0)
                    
                    # Barre de progression
                    st.progress(pourcentage / 100)
                    st.text(f"{pourcentage}%")
                    st.text(f"{avancement.get('operations_terminees', 0)}/{avancement.get('operations_totales', 0)} ops")
                
                with col_equipe:
                    assignations = bt.get('assignations', [])
                    st.text(f"👥 {len(assignations)} assigné(s)")
                    
                    reservations = bt.get('reservations_postes', [])
                    if reservations:
                        st.text(f"🏭 {len(reservations)} poste(s)")
                
                with col_actions:
                    if st.button("👁️ Détails", key=f"bt_details_{bt['id']}", use_container_width=True):
                        st.session_state.selected_formulaire_id = bt['id']
                        st.session_state.show_formulaire_modal = True
                    
                    if bt['statut'] in ['VALIDÉ', 'EN COURS'] and pourcentage == 100:
                        if st.button("✅ Terminer", key=f"bt_terminer_{bt['id']}", use_container_width=True):
                            if gestionnaire_bt.marquer_bt_termine(bt['id'], 1, "Marqué terminé depuis la liste"):
                                st.success("✅ BT terminé!")
                                st.rerun()
                
                st.markdown("---")
    
    else:
        st.info("Aucun Bon de Travail ne correspond aux critères de recherche.")


def render_bon_travail_stats(gestionnaire_bt):
    """
    Statistiques détaillées spécifiques aux BT.
    
    Args:
        gestionnaire_bt: Instance du gestionnaire BT spécialisé
    """
    st.markdown("#### 📊 Statistiques Bons de Travail")
    
    stats = gestionnaire_bt.get_statistiques_bt()
    bons_travail = gestionnaire_bt.get_bons_travail()
    
    if not bons_travail:
        st.info("Aucune donnée pour les statistiques.")
        return
    
    # Métriques principales
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📋 Total BT", len(bons_travail))
    with col2:
        en_cours = stats.get('en_cours', 0)
        st.metric("⚡ En Cours", en_cours)
    with col3:
        termines = len([bt for bt in bons_travail if bt['statut'] == 'TERMINÉ'])
        taux_completion = (termines / len(bons_travail) * 100) if bons_travail else 0
        st.metric("✅ Terminés", termines, delta=f"{taux_completion:.1f}%")
    with col4:
        duree_moyenne = stats.get('duree_moyenne', 0)
        st.metric("⏱️ Durée Moyenne", formater_delai(int(duree_moyenne)))
    with col5:
        projets_concernes = stats.get('projets_concernes', 0)
        st.metric("🏗️ Projets Concernés", projets_concernes)
    
    # Graphiques spécifiques BT
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Répartition par statut avec couleurs
        statut_counts = {}
        for bt in bons_travail:
            statut = bt['statut']
            statut_counts[statut] = statut_counts.get(statut, 0) + 1
        
        if statut_counts:
            colors_statut = {
                'BROUILLON': '#f59e0b', 'VALIDÉ': '#3b82f6', 'EN COURS': '#8b5cf6',
                'TERMINÉ': '#059669', 'ANNULÉ': '#ef4444'
            }
            fig = px.pie(values=list(statut_counts.values()), names=list(statut_counts.keys()),
                        title="📊 Répartition par Statut", 
                        color_discrete_map=colors_statut)
            fig.update_layout(showlegend=True, height=350)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_g2:
        # Analyse par projet
        projet_stats = {}
        for bt in bons_travail:
            projet = bt.get('project_nom', 'Projet non défini')
            if projet not in projet_stats:
                projet_stats[projet] = {'total': 0, 'termines': 0}
            projet_stats[projet]['total'] += 1
            if bt['statut'] == 'TERMINÉ':
                projet_stats[projet]['termines'] += 1
        
        if projet_stats:
            projets_data = []
            for projet, stats_p in projet_stats.items():
                taux = (stats_p['termines'] / stats_p['total'] * 100) if stats_p['total'] > 0 else 0
                projets_data.append({
                    'Projet': projet[:20] + "..." if len(projet) > 20 else projet,
                    'Total BT': stats_p['total'],
                    'Taux Completion': taux
                })
            
            df_projets = pd.DataFrame(projets_data)
            fig = px.bar(df_projets, x='Projet', y='Total BT', color='Taux Completion',
                        title="📈 BT par Projet", color_continuous_scale='RdYlGn')
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
    
    # Analyse de productivité
    st.markdown("##### 📈 Analyse de Productivité")
    
    col_prod1, col_prod2 = st.columns(2)
    
    with col_prod1:
        # BT par responsable
        responsable_stats = {}
        for bt in bons_travail:
            responsable = bt.get('employee_nom', 'Non assigné')
            if responsable not in responsable_stats:
                responsable_stats[responsable] = {'total': 0, 'termines': 0}
            responsable_stats[responsable]['total'] += 1
            if bt['statut'] == 'TERMINÉ':
                responsable_stats[responsable]['termines'] += 1
        
        st.markdown("**Top Responsables BT :**")
        top_responsables = sorted(responsable_stats.items(), 
                                key=lambda x: x[1]['total'], reverse=True)[:5]
        
        for i, (responsable, stats_r) in enumerate(top_responsables, 1):
            taux = (stats_r['termines'] / stats_r['total'] * 100) if stats_r['total'] > 0 else 0
            st.metric(f"{i}. {responsable[:15]}", 
                     f"{stats_r['total']} BT", 
                     delta=f"{taux:.0f}% terminés")
    
    with col_prod2:
        # Évolution mensuelle
        evolution_mensuelle = {}
        for bt in bons_travail:
            try:
                mois = bt['date_creation'][:7]  # YYYY-MM
                if mois not in evolution_mensuelle:
                    evolution_mensuelle[mois] = 0
                evolution_mensuelle[mois] += 1
            except:
                continue
        
        if evolution_mensuelle:
            mois_sorted = sorted(evolution_mensuelle.items())[-6:]  # 6 derniers mois
            df_evolution = pd.DataFrame(mois_sorted, columns=['Mois', 'Nombre BT'])
            
            fig = px.line(df_evolution, x='Mois', y='Nombre BT',
                         title="Évolution Mensuelle des BT",
                         markers=True)
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)


def render_rapport_productivite(gestionnaire_bt):
    """
    Rapport de productivité détaillé pour les BT.
    
    Args:
        gestionnaire_bt: Instance du gestionnaire BT spécialisé
    """
    st.markdown("#### 📈 Rapport de Productivité BT")
    
    # Sélection de la période
    col_periode1, col_periode2 = st.columns(2)
    
    with col_periode1:
        periode = st.selectbox("Période d'analyse", [7, 15, 30, 60, 90], index=2, format_func=lambda x: f"{x} derniers jours")
    
    with col_periode2:
        if st.button("🔄 Générer Rapport", use_container_width=True, key="bt_generer_rapport"):
            rapport = gestionnaire_bt.generer_rapport_productivite(periode)
            
            if rapport:
                st.success(f"✅ Rapport généré pour {rapport['periode']}")
                
                # Affichage du rapport
                col_r1, col_r2 = st.columns(2)
                
                with col_r1:
                    st.metric("Total BT Terminés", rapport['total_bt_termines'])
                    st.metric("Durée Moyenne", f"{rapport['duree_moyenne_globale']:.1f} jours")
                
                with col_r2:
                    st.metric("Date Génération", rapport['date_generation'][:10])
                    st.metric("Employés Actifs", len(rapport['employes']))
                
                # Détail par employé
                if rapport['employes']:
                    st.markdown("##### 👥 Détail par Employé")
                    
                    df_employes = pd.DataFrame(rapport['employes'])
                    df_employes['duree_moyenne'] = df_employes['duree_moyenne'].round(1)
                    df_employes['montant_total_travaux'] = df_employes['montant_total_travaux'].apply(lambda x: f"{x:,.0f}$")
                    
                    st.dataframe(df_employes, use_container_width=True)
            else:
                st.warning("Aucune donnée disponible pour cette période")
    
    # Conseils d'optimisation
    st.markdown("##### 💡 Conseils d'Optimisation")
    
    conseils = [
        "📊 Suivez régulièrement l'avancement des BT en cours",
        "👥 Équilibrez la charge de travail entre les employés",
        "⏱️ Identifiez les BT qui prennent plus de temps que prévu",
        "🔧 Optimisez l'assignation des postes de travail",
        "📋 Assurez-vous que les opérations sont bien définies dans les projets"
    ]
    
    for conseil in conseils:
        st.info(conseil)
