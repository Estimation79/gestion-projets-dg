# pages/projects.py
"""
Pages de gestion des projets pour l'ERP Production DG Inc.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from models.projects import get_project_statistics
from utils.formatting import format_currency


def show_liste_projets():
    """Affiche la liste des projets avec filtres et actions"""
    st.markdown("## 📋 Liste des Projets")
    gestionnaire = st.session_state.gestionnaire
    crm_manager = st.session_state.gestionnaire_crm

    col_create, _ = st.columns([1, 3])
    with col_create:
        if st.button("➕ Nouveau Projet", use_container_width=True, key="create_btn_liste"):
            st.session_state.show_create_project = True
    
    st.markdown("---")
    
    if not gestionnaire.projets and not st.session_state.get('show_create_project'):
        st.info("Aucun projet. Cliquez sur 'Nouveau Projet' pour commencer.")

    if gestionnaire.projets:
        # Filtres
        with st.expander("🔍 Filtres", expanded=False):
            fcol1, fcol2, fcol3 = st.columns(3)
            statuts_dispo = sorted(list(set([p.get('statut', 'N/A') for p in gestionnaire.projets])))
            priorites_dispo = sorted(list(set([p.get('priorite', 'N/A') for p in gestionnaire.projets])))
            
            with fcol1:
                filtre_statut = st.multiselect("Statut:", ['Tous'] + statuts_dispo, default=['Tous'])
            with fcol2:
                filtre_priorite = st.multiselect("Priorité:", ['Toutes'] + priorites_dispo, default=['Toutes'])
            with fcol3:
                recherche = st.text_input("🔍 Rechercher:", placeholder="Nom, client...")

        # Application des filtres
        projets_filtres = gestionnaire.projets
        if 'Tous' not in filtre_statut and filtre_statut:
            projets_filtres = [p for p in projets_filtres if p.get('statut') in filtre_statut]
        if 'Toutes' not in filtre_priorite and filtre_priorite:
            projets_filtres = [p for p in projets_filtres if p.get('priorite') in filtre_priorite]
        if recherche:
            terme = recherche.lower()
            projets_filtres = [p for p in projets_filtres if
                               terme in str(p.get('nom_projet', '')).lower() or
                               terme in str(p.get('client_nom_cache', '')).lower() or
                               (p.get('client_entreprise_id') and crm_manager.get_entreprise_by_id(p.get('client_entreprise_id')) and terme in crm_manager.get_entreprise_by_id(p.get('client_entreprise_id')).get('nom', '').lower()) or
                               terme in str(p.get('client', '')).lower()
                              ]

        st.markdown(f"**{len(projets_filtres)} projet(s) trouvé(s)**")
        
        if projets_filtres:
            # Tableau des projets
            df_data = []
            for p in projets_filtres:
                client_display_name_df = p.get('client_nom_cache', 'N/A')
                if client_display_name_df == 'N/A' and p.get('client_entreprise_id'):
                    entreprise = crm_manager.get_entreprise_by_id(p.get('client_entreprise_id'))
                    if entreprise:
                        client_display_name_df = entreprise.get('nom', 'N/A')
                elif client_display_name_df == 'N/A':
                    client_display_name_df = p.get('client', 'N/A')

                df_data.append({
                    '🆔': p.get('id', '?'), 
                    '📋 Projet': p.get('nom_projet', 'N/A'), 
                    '👤 Client': client_display_name_df, 
                    '🚦 Statut': p.get('statut', 'N/A'), 
                    '⭐ Priorité': p.get('priorite', 'N/A'), 
                    '📅 Début': p.get('date_soumis', 'N/A'), 
                    '🏁 Fin': p.get('date_prevu', 'N/A'), 
                    '💰 Prix': format_currency(p.get('prix_estime', 0))
                })
            
            st.dataframe(pd.DataFrame(df_data), use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 🔧 Actions sur un projet")
            selected_id_actions = st.selectbox(
                "Projet:", 
                options=[p.get('id') for p in projets_filtres], 
                format_func=lambda pid: f"#{pid} - {next((p.get('nom_projet', '') for p in projets_filtres if p.get('id') == pid), '')}", 
                key="proj_actions_sel"
            )
            sel_proj_action = next((p for p in gestionnaire.projets if p.get('id') == selected_id_actions), None)
            
            if sel_proj_action:
                acol1, acol2, acol3 = st.columns(3)
                with acol1:
                    if st.button("👁️ Voir Détails", use_container_width=True, key=f"view_act_{selected_id_actions}"):
                        st.session_state.selected_project = sel_proj_action
                        st.session_state.show_project_modal = True
                with acol2:
                    if st.button("✏️ Modifier", use_container_width=True, key=f"edit_act_{selected_id_actions}"):
                        st.session_state.edit_project_data = sel_proj_action
                        st.session_state.show_edit_project = True
                with acol3:
                    if st.button("🗑️ Supprimer", use_container_width=True, key=f"del_act_{selected_id_actions}"):
                        st.session_state.delete_project_id = selected_id_actions
                        st.session_state.show_delete_confirmation = True

    # Affichage des formulaires
    if st.session_state.get('show_create_project'):
        render_create_project_form(gestionnaire, crm_manager)
    if st.session_state.get('show_edit_project') and st.session_state.get('edit_project_data'):
        render_edit_project_form(gestionnaire, crm_manager, st.session_state.edit_project_data)
    if st.session_state.get('show_delete_confirmation'):
        render_delete_confirmation(gestionnaire)


def render_create_project_form(gestionnaire, crm_manager):
    """Affiche le formulaire de création de projet"""
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### ➕ Créer Projet")
    
    with st.form("create_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        
        with fc1:
            nom = st.text_input("Nom *:")
            liste_entreprises_crm_form = [("", "Sélectionner ou laisser vide")] + [(e['id'], e['nom']) for e in crm_manager.entreprises]
            selected_entreprise_id_form = st.selectbox(
                "Client (Entreprise) *:",
                options=[e_id for e_id, _ in liste_entreprises_crm_form],
                format_func=lambda e_id: next((nom for id_e, nom in liste_entreprises_crm_form if id_e == e_id), "Sélectionner..."),
                key="project_create_client_select"
            )
            client_nom_direct_form = st.text_input("Ou nom client direct (si non listé):")

            statut = st.selectbox("Statut:", ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON"])
            priorite = st.selectbox("Priorité:", ["BAS", "MOYEN", "ÉLEVÉ"])
        
        with fc2:
            tache = st.selectbox("Type:", ["ESTIMATION", "CONCEPTION", "DÉVELOPPEMENT", "TESTS", "DÉPLOIEMENT", "MAINTENANCE", "FORMATION"])
            d_debut = st.date_input("Début:", datetime.now().date())
            d_fin = st.date_input("Fin Prévue:", datetime.now().date() + timedelta(days=30))
            bd_ft = st.number_input("BD-FT (h):", 0, value=40, step=1)
            prix = st.number_input("Prix ($):", 0.0, value=10000.0, step=100.0, format="%.2f")
        
        desc = st.text_area("Description:")
        
        # Assignation d'employés
        if gestionnaire_employes.employes:
            st.markdown("##### 👥 Assignation d'Employés")
            employes_disponibles = [(emp['id'], f"{emp.get('prenom', '')} {emp.get('nom', '')} ({emp.get('poste', '')})") for emp in gestionnaire_employes.employes if emp.get('statut') == 'ACTIF']
            employes_assignes = st.multiselect(
                "Employés assignés:",
                options=[emp_id for emp_id, _ in employes_disponibles],
                format_func=lambda emp_id: next((nom for id_e, nom in employes_disponibles if id_e == emp_id), ""),
                key="project_create_employes_assign"
            )
        
        st.markdown("<small>* Obligatoire</small>", unsafe_allow_html=True)
        
        s_btn, c_btn = st.columns(2)
        with s_btn:
            submit = st.form_submit_button("💾 Créer", use_container_width=True)
        with c_btn:
            cancel = st.form_submit_button("❌ Annuler", use_container_width=True)
        
        if submit:
            if not nom or (not selected_entreprise_id_form and not client_nom_direct_form):
                st.error("Nom du projet et Client (sélection ou nom direct) obligatoires.")
            elif d_fin < d_debut:
                st.error("Date fin < date début.")
            else:
                client_nom_cache_val = ""
                if selected_entreprise_id_form:
                    entreprise_obj = crm_manager.get_entreprise_by_id(selected_entreprise_id_form)
                    if entreprise_obj:
                        client_nom_cache_val = entreprise_obj.get('nom', '')
                elif client_nom_direct_form:
                    client_nom_cache_val = client_nom_direct_form

                data = {
                    'nom_projet': nom,
                    'client_entreprise_id': selected_entreprise_id_form if selected_entreprise_id_form else None,
                    'client_nom_cache': client_nom_cache_val,
                    'client': client_nom_direct_form if not selected_entreprise_id_form and client_nom_direct_form else "",
                    'statut': statut, 'priorite': priorite, 'tache': tache, 
                    'date_soumis': d_debut.strftime('%Y-%m-%d'), 
                    'date_prevu': d_fin.strftime('%Y-%m-%d'), 
                    'bd_ft_estime': str(bd_ft), 
                    'prix_estime': str(prix), 
                    'description': desc or f"Projet {tache.lower()} pour {client_nom_cache_val}", 
                    'sous_taches': [], 
                    'materiaux': [], 
                    'operations': [], 
                    'employes_assignes': employes_assignes if 'employes_assignes' in locals() else []
                }
                
                pid = gestionnaire.ajouter_projet(data)
                
                # Mettre à jour les assignations des employés
                if 'employes_assignes' in locals() and employes_assignes:
                    for emp_id in employes_assignes:
                        employe = gestionnaire_employes.get_employe_by_id(emp_id)
                        if employe:
                            projets_existants = employe.get('projets_assignes', [])
                            if pid not in projets_existants:
                                projets_existants.append(pid)
                                gestionnaire_employes.modifier_employe(emp_id, {'projets_assignes': projets_existants})
                
                st.success(f"✅ Projet #{pid} créé !")
                st.session_state.show_create_project = False
                st.rerun()
        
        if cancel:
            st.session_state.show_create_project = False
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)


def render_edit_project_form(gestionnaire, crm_manager, project_data):
    """Affiche le formulaire de modification de projet"""
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(f"### ✏️ Modifier Projet #{project_data.get('id')}")
    
    with st.form("edit_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        
        with fc1:
            nom = st.text_input("Nom *:", value=project_data.get('nom_projet', ''))
            
            # Gestion de la liste des entreprises CRM
            liste_entreprises_crm_form = [("", "Sélectionner ou laisser vide")] + [(e['id'], e['nom']) for e in crm_manager.entreprises]
            current_entreprise_id = project_data.get('client_entreprise_id', "")
            selected_entreprise_id_form = st.selectbox(
                "Client (Entreprise) *:",
                options=[e_id for e_id, _ in liste_entreprises_crm_form],
                index=next((i for i, (e_id, _) in enumerate(liste_entreprises_crm_form) if e_id == current_entreprise_id), 0),
                format_func=lambda e_id: next((nom for id_e, nom in liste_entreprises_crm_form if id_e == e_id), "Sélectionner..."),
                key="project_edit_client_select"
            )
            client_nom_direct_form = st.text_input("Ou nom client direct:", value=project_data.get('client', ''))

            # Gestion du statut
            statuts = ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON"]
            current_statut = project_data.get('statut', 'À FAIRE')
            statut = st.selectbox("Statut:", statuts, index=statuts.index(current_statut) if current_statut in statuts else 0)
            
            # Gestion de la priorité
            priorites = ["BAS", "MOYEN", "ÉLEVÉ"]
            current_priorite = project_data.get('priorite', 'MOYEN')
            priorite = st.selectbox("Priorité:", priorites, index=priorites.index(current_priorite) if current_priorite in priorites else 1)
        
        with fc2:
            # Gestion du type de tâche
            taches = ["ESTIMATION", "CONCEPTION", "DÉVELOPPEMENT", "TESTS", "DÉPLOIEMENT", "MAINTENANCE", "FORMATION"]
            current_tache = project_data.get('tache', 'ESTIMATION')
            tache = st.selectbox("Type:", taches, index=taches.index(current_tache) if current_tache in taches else 0)
            
            # Gestion des dates
            try:
                d_debut = st.date_input("Début:", datetime.strptime(project_data.get('date_soumis', ''), '%Y-%m-%d').date())
            except (ValueError, TypeError):
                d_debut = st.date_input("Début:", datetime.now().date())
            
            try:
                d_fin = st.date_input("Fin Prévue:", datetime.strptime(project_data.get('date_prevu', ''), '%Y-%m-%d').date())
            except (ValueError, TypeError):
                d_fin = st.date_input("Fin Prévue:", datetime.now().date() + timedelta(days=30))
            
            # Gestion BD-FT
            try:
                bd_ft_val = int(project_data.get('bd_ft_estime', 0))
            except (ValueError, TypeError):
                bd_ft_val = 0
            bd_ft = st.number_input("BD-FT (h):", 0, value=bd_ft_val, step=1)
            
            # Gestion du prix
            try:
                prix_str = str(project_data.get('prix_estime', '0'))
                prix_str = prix_str.replace(' ', '').replace(',', '').replace('€', '').replace('$', '')
                prix_val = float(prix_str) if prix_str else 0.0
            except (ValueError, TypeError):
                prix_val = 0.0
            
            prix = st.number_input("Prix ($):", 0.0, value=prix_val, step=100.0, format="%.2f")
        
        # Description
        desc = st.text_area("Description:", value=project_data.get('description', ''))
        
        # Assignation d'employés
        if gestionnaire_employes.employes:
            st.markdown("##### 👥 Assignation d'Employés")
            employes_disponibles = [
                (emp['id'], f"{emp.get('prenom', '')} {emp.get('nom', '')} ({emp.get('poste', '')})")
                for emp in gestionnaire_employes.employes 
                if emp.get('statut') == 'ACTIF'
            ]
            current_employes = project_data.get('employes_assignes', [])
            employes_assignes = st.multiselect(
                "Employés assignés:",
                options=[emp_id for emp_id, _ in employes_disponibles],
                default=[emp_id for emp_id in current_employes if emp_id in [e[0] for e in employes_disponibles]],
                format_func=lambda emp_id: next((nom for id_e, nom in employes_disponibles if id_e == emp_id), ""),
                key="project_edit_employes_assign"
            )
        
        st.markdown("<small>* Obligatoire</small>", unsafe_allow_html=True)
        
        # Boutons d'action
        s_btn, c_btn = st.columns(2)
        with s_btn:
            submit = st.form_submit_button("💾 Sauvegarder", use_container_width=True)
        with c_btn:
            cancel = st.form_submit_button("❌ Annuler", use_container_width=True)
        
        # Traitement de la soumission
        if submit:
            if not nom or (not selected_entreprise_id_form and not client_nom_direct_form):
                st.error("Nom du projet et Client obligatoires.")
            elif d_fin < d_debut:
                st.error("Date fin < date début.")
            else:
                # Détermination du nom du client pour cache
                client_nom_cache_val = ""
                if selected_entreprise_id_form:
                    entreprise_obj = crm_manager.get_entreprise_by_id(selected_entreprise_id_form)
                    if entreprise_obj:
                        client_nom_cache_val = entreprise_obj.get('nom', '')
                elif client_nom_direct_form:
                    client_nom_cache_val = client_nom_direct_form

                # Préparation des données de mise à jour
                update_data = {
                    'nom_projet': nom,
                    'client_entreprise_id': selected_entreprise_id_form if selected_entreprise_id_form else None,
                    'client_nom_cache': client_nom_cache_val,
                    'client': client_nom_direct_form if not selected_entreprise_id_form and client_nom_direct_form else "",
                    'statut': statut,
                    'priorite': priorite,
                    'tache': tache,
                    'date_soumis': d_debut.strftime('%Y-%m-%d'),
                    'date_prevu': d_fin.strftime('%Y-%m-%d'),
                    'bd_ft_estime': str(bd_ft),
                    'prix_estime': str(prix),
                    'description': desc,
                    'employes_assignes': employes_assignes if 'employes_assignes' in locals() else []
                }
                
                # Mise à jour du projet
                if gestionnaire.modifier_projet(project_data['id'], update_data):
                    # Mettre à jour les assignations des employés
                    if 'employes_assignes' in locals():
                        # Supprimer l'ancien projet des anciens employés
                        for emp_id in project_data.get('employes_assignes', []):
                            if emp_id not in employes_assignes:
                                employe = gestionnaire_employes.get_employe_by_id(emp_id)
                                if employe:
                                    projets_existants = employe.get('projets_assignes', [])
                                    if project_data['id'] in projets_existants:
                                        projets_existants.remove(project_data['id'])
                                        gestionnaire_employes.modifier_employe(emp_id, {'projets_assignes': projets_existants})
                        
                        # Ajouter le projet aux nouveaux employés
                        for emp_id in employes_assignes:
                            if emp_id not in project_data.get('employes_assignes', []):
                                employe = gestionnaire_employes.get_employe_by_id(emp_id)
                                if employe:
                                    projets_existants = employe.get('projets_assignes', [])
                                    if project_data['id'] not in projets_existants:
                                        projets_existants.append(project_data['id'])
                                        gestionnaire_employes.modifier_employe(emp_id, {'projets_assignes': projets_existants})
                    
                    st.success(f"✅ Projet #{project_data['id']} modifié !")
                    st.session_state.show_edit_project = False
                    st.session_state.edit_project_data = None
                    st.rerun()
                else:
                    st.error("Erreur lors de la modification.")
        
        # Traitement de l'annulation
        if cancel:
            st.session_state.show_edit_project = False
            st.session_state.edit_project_data = None
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)


def render_delete_confirmation(gestionnaire):
    """Affiche la confirmation de suppression"""
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### 🗑️ Confirmation de Suppression")
    project_id = st.session_state.delete_project_id
    project = next((p for p in gestionnaire.projets if p.get('id') == project_id), None)
    
    if project:
        st.warning(f"⚠️ Êtes-vous sûr de vouloir supprimer le projet **#{project.get('id')} - {project.get('nom_projet', 'N/A')}** ?")
        st.markdown("Cette action est **irréversible**.")
        
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            if st.button("🗑️ Confirmer Suppression", use_container_width=True):
                gestionnaire.supprimer_projet(project_id)
                st.success(f"✅ Projet #{project_id} supprimé !")
                st.session_state.show_delete_confirmation = False
                st.session_state.delete_project_id = None
                st.rerun()
        with dcol2:
            if st.button("❌ Annuler", use_container_width=True):
                st.session_state.show_delete_confirmation = False
                st.session_state.delete_project_id = None
                st.rerun()
    else:
        st.error("Projet non trouvé.")
        st.session_state.show_delete_confirmation = False
        st.session_state.delete_project_id = None
    
    st.markdown("</div>", unsafe_allow_html=True)


def show_project_modal():
    """Affichage des détails d'un projet dans un expander"""
    if 'selected_project' not in st.session_state or not st.session_state.get('show_project_modal') or not st.session_state.selected_project:
        return
    
    proj_mod = st.session_state.selected_project
    
    with st.expander(f"📁 Détails Projet #{proj_mod.get('id')} - {proj_mod.get('nom_projet', 'N/A')}", expanded=True):
        if st.button("✖️ Fermer", key="close_modal_details_btn_top"):
            st.session_state.show_project_modal = False
            st.rerun()
        
        st.markdown("---")
        
        mc1, mc2 = st.columns(2)
        with mc1:
            st.markdown(f"""
            <div class='info-card'>
                <h4>📋 {proj_mod.get('nom_projet', 'N/A')}</h4>
                <p><strong>👤 Client:</strong> {proj_mod.get('client', 'N/A')}</p>
                <p><strong>🚦 Statut:</strong> {proj_mod.get('statut', 'N/A')}</p>
                <p><strong>⭐ Priorité:</strong> {proj_mod.get('priorite', 'N/A')}</p>
                <p><strong>✅ Tâche:</strong> {proj_mod.get('tache', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with mc2:
            st.markdown(f"""
            <div class='info-card'>
                <h4>📊 Finances</h4>
                <p><strong>💰 Prix:</strong> {format_currency(proj_mod.get('prix_estime', 0))}</p>
                <p><strong>⏱️ BD-FT:</strong> {proj_mod.get('bd_ft_estime', 'N/A')}h</p>
                <p><strong>📅 Début:</strong> {proj_mod.get('date_soumis', 'N/A')}</p>
                <p><strong>🏁 Fin:</strong> {proj_mod.get('date_prevu', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        if proj_mod.get('description'):
            st.markdown("##### 📝 Description")
            st.markdown(f"<div class='info-card'><p>{proj_mod.get('description', 'Aucune.')}</p></div>", unsafe_allow_html=True)

        tabs_mod = st.tabs(["📝 Sous-tâches", "📦 Matériaux", "🔧 Opérations"])
        
        with tabs_mod[0]:
            sts_mod = proj_mod.get('sous_taches', [])
            if not sts_mod:
                st.info("Aucune sous-tâche.")
            else:
                for st_item in sts_mod:
                    st_color = {
                        'À FAIRE': 'orange', 
                        'EN COURS': 'var(--primary-color)', 
                        'TERMINÉ': 'var(--success-color)'
                    }.get(st_item.get('statut', 'À FAIRE'), 'var(--text-color-muted)')
                    
                    st.markdown(f"""
                    <div class='info-card' style='border-left:4px solid {st_color};margin-top:0.5rem;'>
                        <h5 style='margin:0 0 0.3rem 0;'>ST{st_item.get('id')} - {st_item.get('nom', 'N/A')}</h5>
                        <p style='margin:0 0 0.3rem 0;'>🚦 {st_item.get('statut', 'N/A')}</p>
                        <p style='margin:0;'>📅 {st_item.get('date_debut', 'N/A')} → {st_item.get('date_fin', 'N/A')}</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        with tabs_mod[1]:
            mats_mod = proj_mod.get('materiaux', [])
            if not mats_mod:
                st.info("Aucun matériau.")
            else:
                total_c_mod = 0
                for mat in mats_mod:
                    q, p_u = mat.get('quantite', 0), mat.get('prix_unitaire', 0)
                    tot = q * p_u
                    total_c_mod += tot
                    fournisseur_html = ""
                    if mat.get("fournisseur"):
                        fournisseur_html = f"<p style='margin:0.3rem 0 0 0;font-size:0.9em;'>🏪 {mat.get('fournisseur', 'N/A')}</p>"
                    
                    st.markdown(f"""
                    <div class='info-card' style='margin-top:0.5rem;'>
                        <h5 style='margin:0 0 0.3rem 0;'>{mat.get('code', 'N/A')} - {mat.get('designation', 'N/A')}</h5>
                        <div style='display:flex;justify-content:space-between;font-size:0.9em;'>
                            <span>📊 {q} {mat.get('unite', '')}</span>
                            <span>💳 {format_currency(p_u)}</span>
                            <span>💰 {format_currency(tot)}</span>
                        </div>
                        {fournisseur_html}
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class='info-card' style='background:var(--primary-color-lighter);text-align:center;margin-top:1rem;'>
                    <h5 style='color:var(--primary-color-darker);margin:0;'>💰 Coût Total Mat.: {format_currency(total_c_mod)}</h5>
                </div>
                """, unsafe_allow_html=True)
        
        with tabs_mod[2]:
            ops_mod = proj_mod.get('operations', [])
            if not ops_mod:
                st.info("Aucune opération.")
            else:
                total_t_mod = 0
                for op_item in ops_mod:
                    tps = op_item.get('temps_estime', 0)
                    total_t_mod += tps
                    op_color = {
                        'À FAIRE': 'orange', 
                        'EN COURS': 'var(--primary-color)', 
                        'TERMINÉ': 'var(--success-color)'
                    }.get(op_item.get('statut', 'À FAIRE'), 'var(--text-color-muted)')
                    
                    poste_travail = op_item.get('poste_travail', 'Non assigné')
                    st.markdown(f"""
                    <div class='info-card' style='border-left:4px solid {op_color};margin-top:0.5rem;'>
                        <h5 style='margin:0 0 0.3rem 0;'>{op_item.get('sequence', '?')} - {op_item.get('description', 'N/A')}</h5>
                        <div style='display:flex;justify-content:space-between;font-size:0.9em;'>
                            <span>🏭 {poste_travail}</span>
                            <span>⏱️ {tps}h</span>
                            <span>👨‍🔧 {op_item.get('ressource', 'N/A')}</span>
                            <span>🚦 {op_item.get('statut', 'N/A')}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class='info-card' style='background:var(--primary-color-lighter);text-align:center;margin-top:1rem;'>
                    <h5 style='color:var(--primary-color-darker);margin:0;'>⏱️ Temps Total Est.: {total_t_mod}h</h5>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("✖️ Fermer", use_container_width=True, key="close_modal_details_btn_bottom"):
            st.session_state.show_project_modal = False
            st.rerun()
