# --- START OF FILE employees.py ---

import json
import os
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# --- Constantes ---
DEPARTEMENTS = ["DÉVELOPPEMENT", "DESIGN", "MARKETING", "COMMERCIAL", "RH", "FINANCE", "OPÉRATIONS", "DIRECTION"]
STATUTS_EMPLOYE = ["ACTIF", "CONGÉ", "FORMATION", "MALADIE", "INACTIF"]
NIVEAUX_COMPETENCE = ["DÉBUTANT", "INTERMÉDIAIRE", "AVANCÉ", "EXPERT"]
TYPES_CONTRAT = ["CDI", "CDD", "FREELANCE", "STAGE", "ALTERNANCE"]
COMPETENCES_DISPONIBLES = [
    "Python", "JavaScript", "React", "Vue.js", "Node.js", "Django", "Flask",
    "UI/UX Design", "Photoshop", "Figma", "Adobe XD", "Illustrator",
    "Marketing Digital", "SEO", "SEM", "Analytics", "Content Marketing",
    "Vente", "Négociation", "Relation Client", "Présentation",
    "Gestion Projet", "Scrum", "Agile", "Leadership", "Management",
    "Comptabilité", "Finance", "Excel", "PowerBI", "Tableau"
]

class GestionnaireEmployes:
    def __init__(self, data_dir="."):
        self.data_file = os.path.join(data_dir, "employees_data.json")
        self.employes = []
        self.next_id = 1
        self.charger_donnees_employes()

    def _get_next_id(self, entity_list):
        if not entity_list:
            return 1
        return max(item.get('id', 0) for item in entity_list) + 1

    def charger_donnees_employes(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.employes = data.get('employes', [])
                    self.next_id = self._get_next_id(self.employes)
            else:
                self._initialiser_donnees_demo_employes()
        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur lors du chargement des données employés: {e}")
            self._initialiser_donnees_demo_employes()

    def _initialiser_donnees_demo_employes(self):
        now_iso = datetime.now().isoformat()
        self.employes = [
            {
                'id': 1,
                'prenom': 'Jean',
                'nom': 'Dupont',
                'email': 'jean.dupont@company.com',
                'telephone': '0123456789',
                'poste': 'Développeur Senior',
                'departement': 'DÉVELOPPEMENT',
                'statut': 'ACTIF',
                'type_contrat': 'CDI',
                'date_embauche': '2022-01-15',
                'salaire': 55000,
                'manager_id': None,
                'competences': [
                    {'nom': 'Python', 'niveau': 'EXPERT', 'certifie': True},
                    {'nom': 'Django', 'niveau': 'AVANCÉ', 'certifie': False},
                    {'nom': 'JavaScript', 'niveau': 'AVANCÉ', 'certifie': True}
                ],
                'projets_assignes': [1, 2],
                'charge_travail': 85,  # Pourcentage
                'notes': 'Excellent développeur avec forte expertise Python',
                'photo_url': '',
                'date_creation': now_iso,
                'date_modification': now_iso
            },
            {
                'id': 2,
                'prenom': 'Marie',
                'nom': 'Martin',
                'email': 'marie.martin@company.com',
                'telephone': '0123456790',
                'poste': 'Designer UX/UI',
                'departement': 'DESIGN',
                'statut': 'ACTIF',
                'type_contrat': 'CDI',
                'date_embauche': '2021-09-01',
                'salaire': 48000,
                'manager_id': None,
                'competences': [
                    {'nom': 'UI/UX Design', 'niveau': 'EXPERT', 'certifie': True},
                    {'nom': 'Figma', 'niveau': 'EXPERT', 'certifie': True},
                    {'nom': 'Adobe XD', 'niveau': 'AVANCÉ', 'certifie': False}
                ],
                'projets_assignes': [1, 3],
                'charge_travail': 70,
                'notes': 'Designer créative avec œil pour les détails',
                'photo_url': '',
                'date_creation': now_iso,
                'date_modification': now_iso
            },
            {
                'id': 3,
                'prenom': 'Pierre',
                'nom': 'Durand',
                'email': 'pierre.durand@company.com',
                'telephone': '0123456791',
                'poste': 'Chef de Projet',
                'departement': 'OPÉRATIONS',
                'statut': 'ACTIF',
                'type_contrat': 'CDI',
                'date_embauche': '2020-03-10',
                'salaire': 62000,
                'manager_id': None,
                'competences': [
                    {'nom': 'Gestion Projet', 'niveau': 'EXPERT', 'certifie': True},
                    {'nom': 'Scrum', 'niveau': 'AVANCÉ', 'certifie': True},
                    {'nom': 'Leadership', 'niveau': 'AVANCÉ', 'certifie': False}
                ],
                'projets_assignes': [1, 2, 3],
                'charge_travail': 95,
                'notes': 'Manager expérimenté, excellent leadership',
                'photo_url': '',
                'date_creation': now_iso,
                'date_modification': now_iso
            },
            {
                'id': 4,
                'prenom': 'Sophie',
                'nom': 'Leroy',
                'email': 'sophie.leroy@company.com',
                'telephone': '0123456792',
                'poste': 'Développeur Junior',
                'departement': 'DÉVELOPPEMENT',
                'statut': 'FORMATION',
                'type_contrat': 'CDD',
                'date_embauche': '2023-06-01',
                'salaire': 35000,
                'manager_id': 1,
                'competences': [
                    {'nom': 'JavaScript', 'niveau': 'INTERMÉDIAIRE', 'certifie': False},
                    {'nom': 'React', 'niveau': 'DÉBUTANT', 'certifie': False},
                    {'nom': 'Node.js', 'niveau': 'DÉBUTANT', 'certifie': False}
                ],
                'projets_assignes': [2],
                'charge_travail': 60,
                'notes': 'Junior prometteuse, en apprentissage rapide',
                'photo_url': '',
                'date_creation': now_iso,
                'date_modification': now_iso
            }
        ]
        self.next_id = self._get_next_id(self.employes)
        self.sauvegarder_donnees_employes()

    def sauvegarder_donnees_employes(self):
        try:
            data = {
                'employes': self.employes,
                'next_id': self.next_id,
                'last_update': datetime.now().isoformat()
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur lors de la sauvegarde des données employés: {e}")

    # --- Méthodes CRUD ---
    def ajouter_employe(self, data_employe):
        data_employe['id'] = self.next_id
        data_employe['date_creation'] = datetime.now().isoformat()
        data_employe['date_modification'] = datetime.now().isoformat()
        self.employes.append(data_employe)
        self.next_id += 1
        self.sauvegarder_donnees_employes()
        return data_employe['id']

    def modifier_employe(self, id_employe, data_employe):
        for i, emp in enumerate(self.employes):
            if emp['id'] == id_employe:
                updated_employe = {**emp, **data_employe, 'date_modification': datetime.now().isoformat()}
                self.employes[i] = updated_employe
                self.sauvegarder_donnees_employes()
                return True
        return False

    def supprimer_employe(self, id_employe):
        self.employes = [emp for emp in self.employes if emp['id'] != id_employe]
        # Mettre à jour les références manager_id
        for emp in self.employes:
            if emp.get('manager_id') == id_employe:
                emp['manager_id'] = None
        self.sauvegarder_donnees_employes()
        return True

    def get_employe_by_id(self, id_employe):
        return next((emp for emp in self.employes if emp.get('id') == id_employe), None)

    def get_employes_by_departement(self, departement):
        return [emp for emp in self.employes if emp.get('departement') == departement]

    def get_employes_by_projet(self, projet_id):
        return [emp for emp in self.employes if projet_id in emp.get('projets_assignes', [])]

    def get_managers(self):
        return [emp for emp in self.employes if not emp.get('manager_id')]

    def get_subordinates(self, manager_id):
        return [emp for emp in self.employes if emp.get('manager_id') == manager_id]

    # --- Méthodes d'analyse ---
    def get_statistiques_employes(self):
        if not self.employes:
            return {}
        
        stats = {
            'total': len(self.employes),
            'par_departement': {},
            'par_statut': {},
            'par_type_contrat': {},
            'salaire_moyen': 0,
            'charge_moyenne': 0,
            'competences_populaires': {}
        }
        
        total_salaire = 0
        total_charge = 0
        toutes_competences = {}
        
        for emp in self.employes:
            # Départements
            dept = emp.get('departement', 'N/A')
            stats['par_departement'][dept] = stats['par_departement'].get(dept, 0) + 1
            
            # Statuts
            statut = emp.get('statut', 'N/A')
            stats['par_statut'][statut] = stats['par_statut'].get(statut, 0) + 1
            
            # Types de contrat
            contrat = emp.get('type_contrat', 'N/A')
            stats['par_type_contrat'][contrat] = stats['par_type_contrat'].get(contrat, 0) + 1
            
            # Salaires
            if emp.get('salaire'):
                total_salaire += emp['salaire']
            
            # Charge de travail
            if emp.get('charge_travail'):
                total_charge += emp['charge_travail']
            
            # Compétences
            for comp in emp.get('competences', []):
                nom_comp = comp.get('nom')
                if nom_comp:
                    toutes_competences[nom_comp] = toutes_competences.get(nom_comp, 0) + 1
        
        stats['salaire_moyen'] = total_salaire / len(self.employes) if self.employes else 0
        stats['charge_moyenne'] = total_charge / len(self.employes) if self.employes else 0
        
        # Top 5 compétences
        stats['competences_populaires'] = dict(sorted(toutes_competences.items(), key=lambda x: x[1], reverse=True)[:5])
        
        return stats

# --- Fonctions d'affichage Streamlit ---

def render_employes_liste_tab(emp_manager, projet_manager):
    st.subheader("👥 Liste des Employés")
    
    col_create, col_search = st.columns([1, 2])
    with col_create:
        if st.button("➕ Nouvel Employé", key="emp_create_btn", use_container_width=True):
            st.session_state.emp_action = "create_employe"
            st.session_state.emp_selected_id = None
    
    with col_search:
        search_term = st.text_input("Rechercher un employé...", key="emp_search")
    
    # Filtres
    with st.expander("🔍 Filtres avancés", expanded=False):
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            filtre_dept = st.multiselect("Département:", ['Tous'] + DEPARTEMENTS, default=['Tous'])
        with fcol2:
            filtre_statut = st.multiselect("Statut:", ['Tous'] + STATUTS_EMPLOYE, default=['Tous'])
        with fcol3:
            filtre_contrat = st.multiselect("Type contrat:", ['Tous'] + TYPES_CONTRAT, default=['Tous'])
    
    # Filtrage des employés
    employes_filtres = emp_manager.employes
    
    if search_term:
        term = search_term.lower()
        employes_filtres = [
            emp for emp in employes_filtres if
            term in emp.get('prenom', '').lower() or
            term in emp.get('nom', '').lower() or
            term in emp.get('email', '').lower() or
            term in emp.get('poste', '').lower()
        ]
    
    if 'Tous' not in filtre_dept and filtre_dept:
        employes_filtres = [emp for emp in employes_filtres if emp.get('departement') in filtre_dept]
    
    if 'Tous' not in filtre_statut and filtre_statut:
        employes_filtres = [emp for emp in employes_filtres if emp.get('statut') in filtre_statut]
    
    if 'Tous' not in filtre_contrat and filtre_contrat:
        employes_filtres = [emp for emp in employes_filtres if emp.get('type_contrat') in filtre_contrat]
    
    if employes_filtres:
        # Affichage sous forme de tableau
        employes_data_display = []
        for emp in employes_filtres:
            manager = emp_manager.get_employe_by_id(emp.get('manager_id')) if emp.get('manager_id') else None
            manager_nom = f"{manager.get('prenom', '')} {manager.get('nom', '')}" if manager else "N/A"
            
            # Projets assignés
            projets_noms = []
            for proj_id in emp.get('projets_assignes', []):
                projet = next((p for p in projet_manager.projets if p.get('id') == proj_id), None)
                if projet:
                    projets_noms.append(projet.get('nom_projet', f'Projet #{proj_id}'))
            
            employes_data_display.append({
                "ID": emp.get('id'),
                "Nom": f"{emp.get('prenom', '')} {emp.get('nom', '')}",
                "Email": emp.get('email', ''),
                "Poste": emp.get('poste', ''),
                "Département": emp.get('departement', ''),
                "Statut": emp.get('statut', ''),
                "Type": emp.get('type_contrat', ''),
                "Manager": manager_nom,
                "Charge": f"{emp.get('charge_travail', 0)}%",
                "Projets": ", ".join(projets_noms) if projets_noms else "-"
            })
        
        st.dataframe(pd.DataFrame(employes_data_display), use_container_width=True)
        
        # Actions sur employé sélectionné
        st.markdown("---")
        st.markdown("### 🔧 Actions sur un employé")
        selected_emp_id = st.selectbox(
            "Employé:",
            options=[emp['id'] for emp in employes_filtres],
            format_func=lambda eid: f"#{eid} - {next((f\"{emp.get('prenom', '')} {emp.get('nom', '')}\" for emp in employes_filtres if emp.get('id') == eid), '')}",
            key="emp_action_select"
        )
        
        if selected_emp_id:
            col_act1, col_act2, col_act3 = st.columns(3)
            with col_act1:
                if st.button("👁️ Voir Profil", key=f"emp_view_{selected_emp_id}", use_container_width=True):
                    st.session_state.emp_action = "view_employe_details"
                    st.session_state.emp_selected_id = selected_emp_id
            with col_act2:
                if st.button("✏️ Modifier", key=f"emp_edit_{selected_emp_id}", use_container_width=True):
                    st.session_state.emp_action = "edit_employe"
                    st.session_state.emp_selected_id = selected_emp_id
            with col_act3:
                if st.button("🗑️ Supprimer", key=f"emp_delete_{selected_emp_id}", use_container_width=True):
                    st.session_state.emp_confirm_delete_id = selected_emp_id
    else:
        st.info("Aucun employé correspondant aux filtres." if search_term or 'Tous' not in (filtre_dept + filtre_statut + filtre_contrat) else "Aucun employé enregistré.")
    
    # Confirmation de suppression
    if 'emp_confirm_delete_id' in st.session_state and st.session_state.emp_confirm_delete_id:
        emp_to_delete = emp_manager.get_employe_by_id(st.session_state.emp_confirm_delete_id)
        if emp_to_delete:
            st.warning(f"Êtes-vous sûr de vouloir supprimer {emp_to_delete.get('prenom')} {emp_to_delete.get('nom')} ? Cette action est irréversible.")
            col_del1, col_del2 = st.columns(2)
            if col_del1.button("Oui, supprimer", type="primary", key="emp_confirm_delete_final"):
                emp_manager.supprimer_employe(st.session_state.emp_confirm_delete_id)
                st.success("Employé supprimé.")
                del st.session_state.emp_confirm_delete_id
                st.rerun()
            if col_del2.button("Annuler", key="emp_cancel_delete_final"):
                del st.session_state.emp_confirm_delete_id
                st.rerun()

def render_employes_dashboard_tab(emp_manager, projet_manager):
    st.subheader("📊 Dashboard RH")
    
    stats = emp_manager.get_statistiques_employes()
    if not stats:
        st.info("Aucune donnée d'employé disponible.")
        return
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Total Employés", stats['total'])
    with col2:
        st.metric("💰 Salaire Moyen", f"{stats['salaire_moyen']:,.0f}€")
    with col3:
        st.metric("📊 Charge Moyenne", f"{stats['charge_moyenne']:.1f}%")
    with col4:
        employes_surcharges = len([emp for emp in emp_manager.employes if emp.get('charge_travail', 0) > 90])
        st.metric("⚠️ Surchargés", employes_surcharges)
    
    # Graphiques
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        if stats['par_departement']:
            fig_dept = px.pie(
                values=list(stats['par_departement'].values()),
                names=list(stats['par_departement'].keys()),
                title="📊 Répartition par Département"
            )
            fig_dept.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                title_x=0.5
            )
            st.plotly_chart(fig_dept, use_container_width=True)
    
    with col_g2:
        if stats['par_statut']:
            colors_statut = {
                'ACTIF': '#10b981',
                'CONGÉ': '#f59e0b', 
                'FORMATION': '#3b82f6',
                'MALADIE': '#ef4444',
                'INACTIF': '#6b7280'
            }
            fig_statut = px.bar(
                x=list(stats['par_statut'].keys()),
                y=list(stats['par_statut'].values()),
                title="📈 Répartition par Statut",
                color=list(stats['par_statut'].keys()),
                color_discrete_map=colors_statut
            )
            fig_statut.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                showlegend=False,
                title_x=0.5
            )
            st.plotly_chart(fig_statut, use_container_width=True)
    
    # Compétences populaires
    if stats['competences_populaires']:
        st.markdown("---")
        st.markdown("##### 🏆 Top Compétences")
        comp_col1, comp_col2 = st.columns(2)
        
        with comp_col1:
            fig_comp = px.bar(
                x=list(stats['competences_populaires'].values()),
                y=list(stats['competences_populaires'].keys()),
                orientation='h',
                title="🎯 Compétences les plus présentes"
            )
            fig_comp.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                title_x=0.5
            )
            st.plotly_chart(fig_comp, use_container_width=True)
        
        with comp_col2:
            # Charge de travail par employé
            charges_data = []
            for emp in emp_manager.employes:
                if emp.get('statut') == 'ACTIF':
                    charges_data.append({
                        'Employé': f"{emp.get('prenom', '')} {emp.get('nom', '')}",
                        'Charge': emp.get('charge_travail', 0),
                        'Département': emp.get('departement', '')
                    })
            
            if charges_data:
                df_charges = pd.DataFrame(charges_data)
                fig_charges = px.bar(
                    df_charges,
                    x='Employé',
                    y='Charge',
                    color='Département',
                    title="📊 Charge de Travail par Employé"
                )
                fig_charges.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='var(--text-color)'),
                    title_x=0.5,
                    xaxis={'tickangle': 45}
                )
                st.plotly_chart(fig_charges, use_container_width=True)

def render_employe_form(emp_manager, employe_data=None):
    form_title = "➕ Ajouter un Nouvel Employé" if employe_data is None else f"✏️ Modifier {employe_data.get('prenom')} {employe_data.get('nom')}"
    
    with st.expander(form_title, expanded=True):
        with st.form("emp_form", clear_on_submit=False):
            # Informations personnelles
            st.markdown("##### 👤 Informations Personnelles")
            col1, col2 = st.columns(2)
            
            with col1:
                prenom = st.text_input("Prénom *", value=employe_data.get('prenom', '') if employe_data else "")
                email = st.text_input("Email *", value=employe_data.get('email', '') if employe_data else "")
                telephone = st.text_input("Téléphone", value=employe_data.get('telephone', '') if employe_data else "")
            
            with col2:
                nom = st.text_input("Nom *", value=employe_data.get('nom', '') if employe_data else "")
                photo_url = st.text_input("Photo URL", value=employe_data.get('photo_url', '') if employe_data else "")
            
            # Informations professionnelles
            st.markdown("##### 💼 Informations Professionnelles")
            col3, col4 = st.columns(2)
            
            with col3:
                poste = st.text_input("Poste *", value=employe_data.get('poste', '') if employe_data else "")
                departement = st.selectbox(
                    "Département *",
                    DEPARTEMENTS,
                    index=DEPARTEMENTS.index(employe_data.get('departement')) if employe_data and employe_data.get('departement') in DEPARTEMENTS else 0
                )
                statut = st.selectbox(
                    "Statut *",
                    STATUTS_EMPLOYE,
                    index=STATUTS_EMPLOYE.index(employe_data.get('statut')) if employe_data and employe_data.get('statut') in STATUTS_EMPLOYE else 0
                )
                type_contrat = st.selectbox(
                    "Type de contrat *",
                    TYPES_CONTRAT,
                    index=TYPES_CONTRAT.index(employe_data.get('type_contrat')) if employe_data and employe_data.get('type_contrat') in TYPES_CONTRAT else 0
                )
            
            with col4:
                date_embauche = st.date_input(
                    "Date d'embauche *",
                    value=datetime.strptime(employe_data.get('date_embauche'), '%Y-%m-%d').date() if employe_data and employe_data.get('date_embauche') else datetime.now().date()
                )
                salaire = st.number_input(
                    "Salaire annuel (€)",
                    min_value=0,
                    value=employe_data.get('salaire', 30000) if employe_data else 30000,
                    step=1000
                )
                
                # Manager
                managers_options = [("", "Aucun manager")] + [(emp['id'], f"{emp.get('prenom', '')} {emp.get('nom', '')}") for emp in emp_manager.get_managers()]
                current_manager_id = employe_data.get('manager_id') if employe_data else ""
                manager_id = st.selectbox(
                    "Manager",
                    options=[mid for mid, _ in managers_options],
                    format_func=lambda mid: next((name for id_m, name in managers_options if id_m == mid), "Aucun"),
                    index=next((i for i, (mid, _) in enumerate(managers_options) if mid == current_manager_id), 0)
                )
                
                charge_travail = st.slider(
                    "Charge de travail (%)",
                    0, 100,
                    value=employe_data.get('charge_travail', 80) if employe_data else 80
                )
            
            # Compétences
            st.markdown("##### 🎯 Compétences")
            
            # Initialiser les compétences en session
            if 'competences_form' not in st.session_state:
                st.session_state.competences_form = employe_data.get('competences', []) if employe_data else []
            
            # Ajouter une compétence
            col_comp1, col_comp2, col_comp3, col_comp4 = st.columns([3, 2, 1, 1])
            with col_comp1:
                nouvelle_comp = st.selectbox("Ajouter compétence:", [""] + COMPETENCES_DISPONIBLES)
            with col_comp2:
                niveau_comp = st.selectbox("Niveau:", NIVEAUX_COMPETENCE)
            with col_comp3:
                certifie_comp = st.checkbox("Certifié")
            with col_comp4:
                if st.button("➕", key="add_comp_btn"):
                    if nouvelle_comp:
                        # Vérifier si la compétence n'existe pas déjà
                        existing = next((comp for comp in st.session_state.competences_form if comp['nom'] == nouvelle_comp), None)
                        if not existing:
                            st.session_state.competences_form.append({
                                'nom': nouvelle_comp,
                                'niveau': niveau_comp,
                                'certifie': certifie_comp
                            })
                            st.rerun()
            
            # Afficher les compétences actuelles
            if st.session_state.competences_form:
                st.markdown("**Compétences actuelles:**")
                for i, comp in enumerate(st.session_state.competences_form):
                    col_c1, col_c2, col_c3, col_c4 = st.columns([3, 2, 1, 1])
                    with col_c1:
                        st.text(comp['nom'])
                    with col_c2:
                        st.text(comp['niveau'])
                    with col_c3:
                        st.text("✅" if comp['certifie'] else "❌")
                    with col_c4:
                        if st.button("🗑️", key=f"del_comp_{i}"):
                            st.session_state.competences_form.pop(i)
                            st.rerun()
            
            # Notes
            notes = st.text_area("Notes", value=employe_data.get('notes', '') if employe_data else "")
            
            st.caption("* Champs obligatoires")
            
            # Boutons
            col_submit, col_cancel = st.columns(2)
            with col_submit:
                submitted = st.form_submit_button("💾 Enregistrer", use_container_width=True)
            with col_cancel:
                if st.form_submit_button("❌ Annuler", use_container_width=True):
                    if 'competences_form' in st.session_state:
                        del st.session_state.competences_form
                    st.session_state.emp_action = None
                    st.session_state.emp_selected_id = None
                    st.rerun()
            
            if submitted:
                if not prenom or not nom or not email or not poste:
                    st.error("Les champs marqués * sont obligatoires.")
                else:
                    new_employe_data = {
                        'prenom': prenom,
                        'nom': nom,
                        'email': email,
                        'telephone': telephone,
                        'poste': poste,
                        'departement': departement,
                        'statut': statut,
                        'type_contrat': type_contrat,
                        'date_embauche': date_embauche.strftime('%Y-%m-%d'),
                        'salaire': salaire,
                        'manager_id': manager_id if manager_id else None,
                        'charge_travail': charge_travail,
                        'competences': st.session_state.competences_form,
                        'projets_assignes': employe_data.get('projets_assignes', []) if employe_data else [],
                        'notes': notes,
                        'photo_url': photo_url
                    }
                    
                    if employe_data:  # Modification
                        emp_manager.modifier_employe(employe_data['id'], new_employe_data)
                        st.success(f"Employé {prenom} {nom} mis à jour !")
                    else:  # Création
                        new_id = emp_manager.ajouter_employe(new_employe_data)
                        st.success(f"Nouvel employé {prenom} {nom} ajouté (ID: {new_id}) !")
                    
                    # Nettoyage
                    if 'competences_form' in st.session_state:
                        del st.session_state.competences_form
                    st.session_state.emp_action = None
                    st.session_state.emp_selected_id = None
                    st.rerun()

def render_employe_details(emp_manager, projet_manager, employe_data):
    if not employe_data:
        st.error("Employé non trouvé.")
        return
    
    st.subheader(f"👤 Profil: {employe_data.get('prenom')} {employe_data.get('nom')}")
    
    # Informations principales
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"""
        <div class='info-card'>
            <h4>📋 Informations Personnelles</h4>
            <p><strong>Email:</strong> {employe_data.get('email', 'N/A')}</p>
            <p><strong>Téléphone:</strong> {employe_data.get('telephone', 'N/A')}</p>
            <p><strong>Poste:</strong> {employe_data.get('poste', 'N/A')}</p>
            <p><strong>Département:</strong> {employe_data.get('departement', 'N/A')}</p>
            <p><strong>Statut:</strong> {employe_data.get('statut', 'N/A')}</p>
            <p><strong>Type contrat:</strong> {employe_data.get('type_contrat', 'N/A')}</p>
            <p><strong>Date embauche:</strong> {employe_data.get('date_embauche', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='info-card'>
            <h4>💰 Informations Financières</h4>
            <p><strong>Salaire:</strong> {employe_data.get('salaire', 0):,}€/an</p>
            <p><strong>Charge travail:</strong> {employe_data.get('charge_travail', 0)}%</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Manager
        manager = emp_manager.get_employe_by_id(employe_data.get('manager_id')) if employe_data.get('manager_id') else None
        manager_nom = f"{manager.get('prenom', '')} {manager.get('nom', '')}" if manager else "Aucun"
        
        # Subordonnés
        subordinates = emp_manager.get_subordinates(employe_data['id'])
        
        st.markdown(f"""
        <div class='info-card'>
            <h4>👥 Hiérarchie</h4>
            <p><strong>Manager:</strong> {manager_nom}</p>
            <p><strong>Subordonnés:</strong> {len(subordinates)}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Compétences
    st.markdown("---")
    st.markdown("##### 🎯 Compétences")
    competences = employe_data.get('competences', [])
    if competences:
        comp_cols = st.columns(min(3, len(competences)))
        for i, comp in enumerate(competences):
            col_idx = i % 3
            with comp_cols[col_idx]:
                certif_icon = "🏆" if comp.get('certifie') else "📚"
                niveau_color = {
                    'DÉBUTANT': '#f59e0b',
                    'INTERMÉDIAIRE': '#3b82f6', 
                    'AVANCÉ': '#10b981',
                    'EXPERT': '#8b5cf6'
                }.get(comp.get('niveau'), '#6b7280')
                
                st.markdown(f"""
                <div class='info-card' style='border-left: 4px solid {niveau_color}; margin-bottom: 0.5rem;'>
                    <h6 style='margin: 0 0 0.2rem 0;'>{certif_icon} {comp.get('nom', 'N/A')}</h6>
                    <p style='margin: 0; font-size: 0.9em;'>{comp.get('niveau', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Aucune compétence renseignée.")
    
    # Projets assignés
    st.markdown("---")
    st.markdown("##### 🚀 Projets Assignés")
    projets_assignes = employe_data.get('projets_assignes', [])
    if projets_assignes:
        for proj_id in projets_assignes:
            projet = next((p for p in projet_manager.projets if p.get('id') == proj_id), None)
            if projet:
                statut_color = {
                    'À FAIRE': '#f59e0b',
                    'EN COURS': '#3b82f6',
                    'EN ATTENTE': '#ef4444', 
                    'TERMINÉ': '#10b981',
                    'LIVRAISON': '#8b5cf6'
                }.get(projet.get('statut'), '#6b7280')
                
                st.markdown(f"""
                <div class='info-card' style='border-left: 4px solid {statut_color}; margin-bottom: 0.5rem;'>
                    <h6 style='margin: 0 0 0.2rem 0;'>#{projet.get('id')} - {projet.get('nom_projet', 'N/A')}</h6>
                    <p style='margin: 0; font-size: 0.9em;'>📊 {projet.get('statut', 'N/A')} • 💰 {projet.get('prix_estime', 0)}€</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Aucun projet assigné.")
    
    # Notes
    if employe_data.get('notes'):
        st.markdown("---")
        st.markdown("##### 📝 Notes")
        st.markdown(f"<div class='info-card'><p>{employe_data.get('notes', '')}</p></div>", unsafe_allow_html=True)
    
    # Bouton retour
    if st.button("Retour à la liste", key="back_to_emp_list"):
        st.session_state.emp_action = None
        st.rerun()

# --- END OF FILE employees.py ---
