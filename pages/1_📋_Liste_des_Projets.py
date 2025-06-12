# pages/1_📋_Liste_des_Projets.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# ==============================================================================
# FONCTIONS UTILITAIRES ET DE RENDU
# Note: Ces fonctions étaient dans le fichier app.py principal.
# Elles sont incluses ici pour que cette page soit autonome.
# À terme, elles pourraient être déplacées dans un dossier utils/.
# ==============================================================================

def format_currency(value):
    """Formate une valeur numérique en une chaîne de caractères monétaire."""
    if value is None:
        return "$0.00"
    try:
        # Nettoyage de la chaîne d'entrée
        s_value = str(value).replace(' ', '').replace('€', '').replace('$', '')
        if ',' in s_value and ('.' not in s_value or s_value.find(',') > s_value.find('.')):
            # Gère les formats comme "1,234.56" ou "1234,56"
            s_value = s_value.replace('.', '').replace(',', '.')
        elif ',' in s_value and '.' in s_value and s_value.find('.') > s_value.find(','):
             # Gère les formats comme "1,234.56" (la virgule est un séparateur de milliers)
            s_value = s_value.replace(',', '')

        num_value = float(s_value)
        if num_value == 0:
            return "$0.00"
        return f"${num_value:,.2f}"
    except (ValueError, TypeError):
        if isinstance(value, (int, float)):
            return f"${value:,.2f}"
        return str(value) + " $ (Err)"

def render_create_project_form(gestionnaire, crm_manager):
    """Affiche le formulaire de création d'un nouveau projet."""
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### ➕ Créer un Nouveau Projet")
    with st.form("create_project_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        with fc1:
            nom = st.text_input("Nom du Projet *:")
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
            tache = st.selectbox("Type de Tâche:", ["ESTIMATION", "CONCEPTION", "DÉVELOPPEMENT", "TESTS", "DÉPLOIEMENT", "MAINTENANCE", "FORMATION", "PRODUCTION"])
            d_debut = st.date_input("Date de Début:", datetime.now().date())
            d_fin = st.date_input("Date de Fin Prévue:", datetime.now().date() + timedelta(days=30))
            bd_ft = st.number_input("Budget-Temps (h):", min_value=0, value=40, step=1)
            prix = st.number_input("Prix Estimé ($):", min_value=0.0, value=10000.0, step=100.0, format="%.2f")
        
        desc = st.text_area("Description du Projet:")
        
        if gestionnaire_employes.employes:
            st.markdown("##### 👥 Assignation d'Employés")
            employes_disponibles = [(emp['id'], f"{emp.get('prenom', '')} {emp.get('nom', '')} ({emp.get('poste', '')})") for emp in gestionnaire_employes.employes if emp.get('statut') == 'ACTIF']
            employes_assignes = st.multiselect(
                "Sélectionner les employés à assigner:",
                options=[emp_id for emp_id, _ in employes_disponibles],
                format_func=lambda emp_id: next((nom for id_e, nom in employes_disponibles if id_e == emp_id), ""),
                key="project_create_employes_assign"
            )
        
        st.markdown("<small>* Champs obligatoires</small>", unsafe_allow_html=True)
        s_btn, c_btn = st.columns(2)
        with s_btn:
            submit = st.form_submit_button("💾 Créer le Projet", use_container_width=True)
        with c_btn:
            cancel = st.form_submit_button("❌ Annuler", use_container_width=True)

        if submit:
            if not nom or (not selected_entreprise_id_form and not client_nom_direct_form):
                st.error("Le nom du projet et le client (sélectionné ou nom direct) sont obligatoires.")
            elif d_fin < d_debut:
                st.error("La date de fin ne peut pas être antérieure à la date de début.")
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
                    'statut': statut, 
                    'priorite': priorite, 
                    'tache': tache, 
                    'date_soumis': d_debut.strftime('%Y-%m-%d'), 
                    'date_prevu': d_fin.strftime('%Y-%m-%d'), 
                    'bd_ft_estime': str(bd_ft), 
                    'prix_estime': str(prix), 
                    'description': desc or f"Projet de {tache.lower()} pour {client_nom_cache_val}", 
                    'sous_taches': [], 
                    'materiaux': [], 
                    'operations': [], 
                    'employes_assignes': employes_assignes if 'employes_assignes' in locals() else []
                }
                pid = gestionnaire.ajouter_projet(data)
                
                if 'employes_assignes' in locals() and employes_assignes:
                    for emp_id in employes_assignes:
                        gestionnaire_employes.assigner_projet_a_employe(emp_id, pid)
                
                st.success(f"✅ Le projet #{pid} a été créé avec succès !")
                st.session_state.show_create_project = False
                st.rerun()
        if cancel:
            st.session_state.show_create_project = False
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def render_edit_project_form(gestionnaire, crm_manager, project_data):
    """Affiche le formulaire d'édition pour un projet existant."""
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(f"### ✏️ Modifier le Projet #{project_data.get('id')}")
    
    with st.form("edit_project_form", clear_on_submit=False):
        fc1, fc2 = st.columns(2)
        
        with fc1:
            nom = st.text_input("Nom du Projet *:", value=project_data.get('nom_projet', ''))
            
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

            statuts = ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "LIVRAISON"]
            current_statut = project_data.get('statut', 'À FAIRE')
            statut = st.selectbox("Statut:", statuts, index=statuts.index(current_statut) if current_statut in statuts else 0)
            
            priorites = ["BAS", "MOYEN", "ÉLEVÉ"]
            current_priorite = project_data.get('priorite', 'MOYEN')
            priorite = st.selectbox("Priorité:", priorites, index=priorites.index(current_priorite) if current_priorite in priorites else 1)
        
        with fc2:
            taches = ["ESTIMATION", "CONCEPTION", "DÉVELOPPEMENT", "TESTS", "DÉPLOIEMENT", "MAINTENANCE", "FORMATION", "PRODUCTION"]
            current_tache = project_data.get('tache', 'ESTIMATION')
            tache = st.selectbox("Type de Tâche:", taches, index=taches.index(current_tache) if current_tache in taches else 0)
            
            try:
                d_debut = st.date_input("Date de Début:", datetime.strptime(project_data.get('date_soumis', ''), '%Y-%m-%d').date())
            except (ValueError, TypeError):
                d_debut = st.date_input("Date de Début:", datetime.now().date())
            
            try:
                d_fin = st.date_input("Date de Fin Prévue:", datetime.strptime(project_data.get('date_prevu', ''), '%Y-%m-%d').date())
            except (ValueError, TypeError):
                d_fin = st.date_input("Date de Fin Prévue:", datetime.now().date() + timedelta(days=30))
            
            try:
                bd_ft_val = int(project_data.get('bd_ft_estime', 0))
            except (ValueError, TypeError):
                bd_ft_val = 0
            bd_ft = st.number_input("Budget-Temps (h):", min_value=0, value=bd_ft_val, step=1)
            
            try:
                prix_str = str(project_data.get('prix_estime', '0')).replace(' ', '').replace(',', '').replace('€', '').replace('$', '')
                prix_val = float(prix_str) if prix_str else 0.0
            except (ValueError, TypeError):
                prix_val = 0.0
            prix = st.number_input("Prix Estimé ($):", min_value=0.0, value=prix_val, step=100.0, format="%.2f")
        
        desc = st.text_area("Description du Projet:", value=project_data.get('description', ''))
        
        if gestionnaire_employes.employes:
            st.markdown("##### 👥 Assignation d'Employés")
            employes_disponibles = [(emp['id'], f"{emp.get('prenom', '')} {emp.get('nom', '')} ({emp.get('poste', '')})") for emp in gestionnaire_employes.employes if emp.get('statut') == 'ACTIF']
            current_employes = project_data.get('employes_assignes', [])
            employes_assignes = st.multiselect(
                "Modifier les employés assignés:",
                options=[emp_id for emp_id, _ in employes_disponibles],
                default=[emp_id for emp_id in current_employes if emp_id in [e[0] for e in employes_disponibles]],
                format_func=lambda emp_id: next((nom for id_e, nom in employes_disponibles if id_e == emp_id), ""),
                key="project_edit_employes_assign"
            )
        
        st.markdown("<small>* Champs obligatoires</small>", unsafe_allow_html=True)
        s_btn, c_btn = st.columns(2)
        with s_btn:
            submit = st.form_submit_button("💾 Sauvegarder les Modifications", use_container_width=True)
        with c_btn:
            cancel = st.form_submit_button("❌ Annuler", use_container_width=True)
        
        if submit:
            if not nom or (not selected_entreprise_id_form and not client_nom_direct_form):
                st.error("Le nom du projet et le client sont obligatoires.")
            elif d_fin < d_debut:
                st.error("La date de fin ne peut pas être antérieure à la date de début.")
            else:
                client_nom_cache_val = ""
                if selected_entreprise_id_form:
                    entreprise_obj = crm_manager.get_entreprise_by_id(selected_entreprise_id_form)
                    if entreprise_obj:
                        client_nom_cache_val = entreprise_obj.get('nom', '')
                elif client_nom_direct_form:
                    client_nom_cache_val = client_nom_direct_form

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
                
                if gestionnaire.modifier_projet(project_data['id'], update_data):
                    if 'employes_assignes' in locals():
                        gestionnaire_employes.mettre_a_jour_assignations_projet(project_data['id'], project_data.get('employes_assignes', []), employes_assignes)
                    
                    st.success(f"✅ Projet #{project_data['id']} modifié avec succès !")
                    st.session_state.show_edit_project = False
                    st.session_state.edit_project_data = None
                    st.rerun()
                else:
                    st.error("Une erreur est survenue lors de la modification du projet.")
        
        if cancel:
            st.session_state.show_edit_project = False
            st.session_state.edit_project_data = None
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

def render_delete_confirmation(gestionnaire):
    """Affiche la confirmation avant de supprimer un projet."""
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("### 🗑️ Confirmation de Suppression")
    project_id = st.session_state.delete_project_id
    project = next((p for p in gestionnaire.projets if p.get('id') == project_id), None)
    
    if project:
        st.warning(f"⚠️ Êtes-vous certain de vouloir supprimer le projet **#{project.get('id')} - {project.get('nom_projet', 'N/A')}** ?")
        st.markdown("Cette action est **irréversible** et supprimera également l'assignation de ce projet pour tous les employés liés.")
        
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            if st.button("🗑️ Confirmer la Suppression", use_container_width=True):
                # Retirer l'assignation des employés avant de supprimer le projet
                employes_assignes = project.get('employes_assignes', [])
                if employes_assignes:
                    gestionnaire_employes = st.session_state.gestionnaire_employes
                    for emp_id in employes_assignes:
                        gestionnaire_employes.retirer_projet_a_employe(emp_id, project_id)

                # Supprimer le projet
                gestionnaire.supprimer_projet(project_id)
                st.success(f"✅ Le projet #{project_id} a été supprimé.")
                st.session_state.show_delete_confirmation = False
                st.session_state.delete_project_id = None
                st.rerun()
        with dcol2:
            if st.button("❌ Annuler", use_container_width=True):
                st.session_state.show_delete_confirmation = False
                st.session_state.delete_project_id = None
                st.rerun()
    else:
        st.error("Projet à supprimer non trouvé.")
        st.session_state.show_delete_confirmation = False
        st.session_state.delete_project_id = None
    st.markdown("</div>", unsafe_allow_html=True)

def show_project_modal():
    """Affiche les détails d'un projet dans un expander (modale simulée)."""
    if 'selected_project' not in st.session_state or not st.session_state.get('show_project_modal') or not st.session_state.selected_project:
        return
    
    proj_mod = st.session_state.selected_project
    
    with st.expander(f"📁 Détails du Projet #{proj_mod.get('id')} - {proj_mod.get('nom_projet', 'N/A')}", expanded=True):
        if st.button("✖️ Fermer", key="close_modal_details_btn_top"):
            st.session_state.show_project_modal = False
            st.rerun()
        
        st.markdown("---")
        
        mc1, mc2 = st.columns(2)
        with mc1:
            st.markdown(f"""
            <div class='info-card'>
                <h4>📋 Informations Générales</h4>
                <p><strong>Projet:</strong> {proj_mod.get('nom_projet', 'N/A')}</p>
                <p><strong>Client:</strong> {proj_mod.get('client_nom_cache', proj_mod.get('client', 'N/A'))}</p>
                <p><strong>🚦 Statut:</strong> {proj_mod.get('statut', 'N/A')}</p>
                <p><strong>⭐ Priorité:</strong> {proj_mod.get('priorite', 'N/A')}</p>
                <p><strong>✅ Tâche:</strong> {proj_mod.get('tache', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with mc2:
            st.markdown(f"""
            <div class='info-card'>
                <h4>📊 Finances et Délais</h4>
                <p><strong>💰 Prix Estimé:</strong> {format_currency(proj_mod.get('prix_estime', 0))}</p>
                <p><strong>⏱️ Budget-Temps:</strong> {proj_mod.get('bd_ft_estime', 'N/A')}h</p>
                <p><strong>📅 Début:</strong> {proj_mod.get('date_soumis', 'N/A')}</p>
                <p><strong>🏁 Fin Prévue:</strong> {proj_mod.get('date_prevu', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        if proj_mod.get('description'):
            st.markdown("<h5>📝 Description</h5>", unsafe_allow_html=True)
            st.markdown(f"<div class='info-card'><p>{proj_mod.get('description', 'Aucune description fournie.')}</p></div>", unsafe_allow_html=True)

        tabs_mod = st.tabs(["📝 Sous-tâches", "📦 Matériaux (BOM)", "🔧 Opérations (Gamme)"])
        
        with tabs_mod[0]:
            sts_mod = proj_mod.get('sous_taches', [])
            if not sts_mod:
                st.info("Aucune sous-tâche n'est définie pour ce projet.")
            else:
                for st_item in sts_mod:
                    st_color = {'À FAIRE': 'orange', 'EN COURS': 'var(--primary-color)', 'TERMINÉ': 'green'}.get(st_item.get('statut', 'À FAIRE'), 'gray')
                    st.markdown(f"""
                    <div class='info-card' style='border-left:4px solid {st_color};margin-bottom:0.5rem;'>
                        <h5 style='margin:0 0 0.3rem 0;'>ST{st_item.get('id')} - {st_item.get('nom', 'N/A')}</h5>
                        <p style='margin:0 0 0.3rem 0;'>🚦 Statut: {st_item.get('statut', 'N/A')}</p>
                        <p style='margin:0;'>📅 Période: {st_item.get('date_debut', 'N/A')} → {st_item.get('date_fin', 'N/A')}</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        with tabs_mod[1]:
            mats_mod = proj_mod.get('materiaux', [])
            if not mats_mod:
                st.info("Aucun matériau n'est listé pour ce projet.")
            else:
                total_c_mod = 0
                for mat in mats_mod:
                    q, p_u = mat.get('quantite', 0) or 0, mat.get('prix_unitaire', 0) or 0
                    tot = q * p_u
                    total_c_mod += tot
                    fournisseur_html = f"<p style='margin:0.3rem 0 0 0;font-size:0.9em;'>🏪 Fournisseur: {mat.get('fournisseur', 'N/A')}</p>" if mat.get("fournisseur") else ""
                    st.markdown(f"""
                    <div class='info-card' style='margin-bottom:0.5rem;'>
                        <h5 style='margin:0 0 0.3rem 0;'>{mat.get('code', 'N/A')} - {mat.get('designation', 'N/A')}</h5>
                        <div style='display:flex;justify-content:space-between;font-size:0.9em;'>
                            <span>📊 Quantité: {q} {mat.get('unite', '')}</span>
                            <span>💳 Coût Unitaire: {format_currency(p_u)}</span>
                            <span>💰 Coût Total: {format_currency(tot)}</span>
                        </div>
                        {fournisseur_html}
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"<div class='info-card' style='background:var(--primary-color-lighter);text-align:center;margin-top:1rem;'><h5 style='color:var(--primary-color-darker);margin:0;'>💰 Coût Total des Matériaux: {format_currency(total_c_mod)}</h5></div>", unsafe_allow_html=True)
        
        with tabs_mod[2]:
            ops_mod = proj_mod.get('operations', [])
            if not ops_mod:
                st.info("Aucune opération de fabrication n'est définie pour ce projet.")
            else:
                total_t_mod = 0
                for op_item in ops_mod:
                    tps = op_item.get('temps_estime', 0) or 0
                    total_t_mod += tps
                    op_color = {'À FAIRE': 'orange', 'EN COURS': 'var(--primary-color)', 'TERMINÉ': 'green'}.get(op_item.get('statut', 'À FAIRE'), 'gray')
                    poste_travail = op_item.get('poste_travail', 'Non assigné')
                    st.markdown(f"""
                    <div class='info-card' style='border-left:4px solid {op_color};margin-bottom:0.5rem;'>
                        <h5 style='margin:0 0 0.3rem 0;'>Séquence {op_item.get('sequence', '?')} - {op_item.get('description', 'N/A')}</h5>
                        <div style='display:flex;justify-content:space-between;font-size:0.9em;'>
                            <span>🏭 Poste: {poste_travail}</span>
                            <span>⏱️ Temps: {tps:.1f}h</span>
                            <span>👨‍🔧 Ressource: {op_item.get('ressource', 'N/A')}</span>
                            <span>🚦 Statut: {op_item.get('statut', 'N/A')}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"<div class='info-card' style='background:var(--primary-color-lighter);text-align:center;margin-top:1rem;'><h5 style='color:var(--primary-color-darker);margin:0;'>⏱️ Temps Total Estimé des Opérations: {total_t_mod:.1f}h</h5></div>", unsafe_allow_html=True)

        st.markdown("---")
        if st.button("✖️ Fermer", use_container_width=True, key="close_modal_details_btn_bottom"):
            st.session_state.show_project_modal = False
            st.rerun()


# ==============================================================================
# LOGIQUE PRINCIPALE DE LA PAGE
# ==============================================================================

st.markdown("## 📋 Liste des Projets")
st.markdown("Gérez, filtrez et visualisez tous les projets de l'entreprise. Utilisez les actions pour créer, modifier ou supprimer des projets.")

# Accéder aux gestionnaires initialisés dans app.py via st.session_state
# C'est la clé de la communication entre les pages dans une app multi-pages.
gestionnaire = st.session_state.gestionnaire
crm_manager = st.session_state.gestionnaire_crm

# --- Bouton de création ---
col_create, _ = st.columns([1, 3])
with col_create:
    if st.button("➕ Nouveau Projet", use_container_width=True, key="create_btn_liste"):
        st.session_state.show_create_project = True
        st.session_state.show_edit_project = False # S'assurer que les autres modales sont fermées

st.markdown("---")

# --- Affichage conditionnel (si aucun projet ou si un formulaire est actif) ---
if not gestionnaire.projets and not st.session_state.get('show_create_project'):
    st.info("Aucun projet n'existe actuellement. Cliquez sur '➕ Nouveau Projet' pour commencer.")

# --- Affichage de la liste et des filtres ---
if gestionnaire.projets:
    with st.expander("🔍 Filtres et Recherche", expanded=False):
        fcol1, fcol2, fcol3 = st.columns(3)
        statuts_dispo = sorted(list(set([p.get('statut', 'N/A') for p in gestionnaire.projets])))
        priorites_dispo = sorted(list(set([p.get('priorite', 'N/A') for p in gestionnaire.projets])))
        
        with fcol1:
            filtre_statut = st.multiselect("Filtrer par Statut:", options=['Tous'] + statuts_dispo, default=['Tous'])
        with fcol2:
            filtre_priorite = st.multiselect("Filtrer par Priorité:", options=['Toutes'] + priorites_dispo, default=['Toutes'])
        with fcol3:
            recherche = st.text_input("🔍 Rechercher par nom, client...", placeholder="Ex: Châssis, AutoTech...")

    projets_filtres = gestionnaire.projets
    if 'Tous' not in filtre_statut and filtre_statut:
        projets_filtres = [p for p in projets_filtres if p.get('statut') in filtre_statut]
    if 'Toutes' not in filtre_priorite and filtre_priorite:
        projets_filtres = [p for p in projets_filtres if p.get('priorite') in filtre_priorite]
    if recherche:
        terme = recherche.lower()
        projets_filtres = [
            p for p in projets_filtres if
            terme in str(p.get('id', '')).lower() or
            terme in str(p.get('nom_projet', '')).lower() or
            terme in str(p.get('client_nom_cache', '')).lower() or
            (p.get('client_entreprise_id') and crm_manager.get_entreprise_by_id(p.get('client_entreprise_id')) and terme in crm_manager.get_entreprise_by_id(p.get('client_entreprise_id')).get('nom', '').lower()) or
            terme in str(p.get('client', '')).lower()
        ]

    st.markdown(f"**{len(projets_filtres)} projet(s) trouvé(s)**")
    
    if projets_filtres:
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
                '🏁 Fin Prévue': p.get('date_prevu', 'N/A'), 
                '💰 Prix': format_currency(p.get('prix_estime', 0))
            })
        st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)
        st.markdown("---")
        
        # --- Section d'actions sur un projet sélectionné ---
        st.markdown("### 🔧 Actions sur un Projet")
        selected_id_actions = st.selectbox(
            "Sélectionner un projet pour effectuer une action:", 
            options=[p.get('id') for p in projets_filtres], 
            format_func=lambda pid: f"#{pid} - {next((p.get('nom_projet', '') for p in projets_filtres if p.get('id') == pid), '')}",
            key="proj_actions_sel"
        )
        
        sel_proj_action = next((p for p in gestionnaire.projets if p.get('id') == selected_id_actions), None)
        
        if sel_proj_action:
            acol1, acol2, acol3 = st.columns(3)
            with acol1:
                if st.button("👁️ Voir les Détails", use_container_width=True, key=f"view_act_{selected_id_actions}"):
                    st.session_state.selected_project = sel_proj_action
                    st.session_state.show_project_modal = True
                    st.session_state.show_create_project = False
                    st.session_state.show_edit_project = False
            with acol2:
                if st.button("✏️ Modifier le Projet", use_container_width=True, key=f"edit_act_{selected_id_actions}"):
                    st.session_state.edit_project_data = sel_proj_action
                    st.session_state.show_edit_project = True
                    st.session_state.show_create_project = False
                    st.session_state.show_project_modal = False
            with acol3:
                if st.button("🗑️ Supprimer le Projet", use_container_width=True, key=f"del_act_{selected_id_actions}"):
                    st.session_state.delete_project_id = selected_id_actions
                    st.session_state.show_delete_confirmation = True
                    st.session_state.show_create_project = False
                    st.session_state.show_edit_project = False

# --- Contrôle de l'affichage des formulaires/modales ---
# Ces appels sont faits à la fin pour que les formulaires apparaissent sous la liste.

if st.session_state.get('show_create_project'):
    render_create_project_form(gestionnaire, crm_manager)

if st.session_state.get('show_edit_project') and st.session_state.get('edit_project_data'):
    render_edit_project_form(gestionnaire, crm_manager, st.session_state.edit_project_data)

if st.session_state.get('show_delete_confirmation'):
    render_delete_confirmation(gestionnaire)

# La modale de détails est un expander, elle peut cohabiter avec la liste.
if st.session_state.get('show_project_modal'):
    show_project_modal()
