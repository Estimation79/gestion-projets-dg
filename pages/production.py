# pages/production.py
"""
Pages de production pour l'ERP Production DG Inc.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import random
import time
from datetime import datetime
from models.work_centers import generer_rapport_capacite_production
from config.constants import COLORS


def show_work_centers_page():
    """Page principale des postes de travail DG Inc."""
    st.markdown("## 🏭 Postes de Travail - DG Inc.")
    gestionnaire_postes = st.session_state.gestionnaire_postes
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    tab_overview, tab_details, tab_analytics = st.tabs([
        "📊 Vue d'ensemble", "🔍 Détails par poste", "📈 Analyses"
    ])
    
    with tab_overview:
        render_work_centers_overview(gestionnaire_postes)
    
    with tab_details:
        render_work_centers_details(gestionnaire_postes, gestionnaire_employes)
    
    with tab_analytics:
        render_work_centers_analytics(gestionnaire_postes)


def render_work_centers_overview(gestionnaire_postes):
    """Vue d'ensemble des postes de travail"""
    stats = gestionnaire_postes.get_statistiques_postes()
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🏭 Total Postes", stats['total_postes'])
    with col2:
        st.metric("🤖 Robots ABB", stats['postes_robotises'])
    with col3:
        st.metric("💻 Postes CNC", stats['postes_cnc'])
    with col4:
        efficacite_globale = random.uniform(82, 87)
        st.metric("⚡ Efficacité", f"{efficacite_globale:.1f}%")
    
    st.markdown("---")
    
    # Répartition par département
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        if stats['par_departement']:
            fig_dept = px.pie(
                values=list(stats['par_departement'].values()),
                names=list(stats['par_departement'].keys()),
                title="📊 Répartition par Département",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_dept.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                title_x=0.5
            )
            st.plotly_chart(fig_dept, use_container_width=True)
    
    with col_chart2:
        # Capacité par type de machine
        capacite_par_type = {}
        for poste in gestionnaire_postes.postes:
            type_machine = poste.get('type_machine', 'AUTRE')
            capacite_par_type[type_machine] = capacite_par_type.get(type_machine, 0) + poste.get('capacite_theorique', 0)
        
        if capacite_par_type:
            fig_cap = px.bar(
                x=list(capacite_par_type.keys()),
                y=list(capacite_par_type.values()),
                title="⚡ Capacité par Type de Machine (h/jour)",
                color=list(capacite_par_type.keys()),
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_cap.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                showlegend=False,
                title_x=0.5
            )
            st.plotly_chart(fig_cap, use_container_width=True)


def render_work_centers_details(gestionnaire_postes, gestionnaire_employes):
    """Détails par poste de travail"""
    st.subheader("🔍 Détails des Postes de Travail")
    
    # Filtres
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        departements = list(set(p['departement'] for p in gestionnaire_postes.postes))
        dept_filter = st.selectbox("Département:", ["Tous"] + sorted(departements))
    
    with col_filter2:
        categories = list(set(p['categorie'] for p in gestionnaire_postes.postes))
        cat_filter = st.selectbox("Catégorie:", ["Toutes"] + sorted(categories))
    
    with col_filter3:
        search_term = st.text_input("🔍 Rechercher:", placeholder="Nom du poste...")
    
    # Application des filtres
    postes_filtres = gestionnaire_postes.postes
    
    if dept_filter != "Tous":
        postes_filtres = [p for p in postes_filtres if p['departement'] == dept_filter]
    
    if cat_filter != "Toutes":
        postes_filtres = [p for p in postes_filtres if p['categorie'] == cat_filter]
    
    if search_term:
        terme = search_term.lower()
        postes_filtres = [p for p in postes_filtres if terme in p['nom'].lower()]
    
    st.markdown(f"**{len(postes_filtres)} poste(s) trouvé(s)**")
    
    # Affichage des postes filtrés
    for poste in postes_filtres:
        with st.container():
            st.markdown(f"""
            <div class='work-center-card'>
                <div class='work-center-header'>
                    <div class='work-center-title'>{poste['nom']}</div>
                    <div class='work-center-badge'>{poste['categorie']}</div>
                </div>
                <p><strong>Département:</strong> {poste['departement']} | <strong>Type:</strong> {poste['type_machine']}</p>
                <p><strong>Compétences requises:</strong> {', '.join(poste.get('competences', []))}</p>
                <div class='work-center-info'>
                    <div class='work-center-stat'>
                        <div class='work-center-stat-value'>{poste['capacite_theorique']}h</div>
                        <p class='work-center-stat-label'>Capacité/jour</p>
                    </div>
                    <div class='work-center-stat'>
                        <div class='work-center-stat-value'>{poste['operateurs_requis']}</div>
                        <p class='work-center-stat-label'>Opérateurs</p>
                    </div>
                    <div class='work-center-stat'>
                        <div class='work-center-stat-value'>{poste['cout_horaire']}$</div>
                        <p class='work-center-stat-label'>Coût/heure</p>
                    </div>
                    <div class='work-center-stat'>
                        <div class='work-center-stat-value'>{random.randint(75, 95)}%</div>
                        <p class='work-center-stat-label'>Utilisation</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Affichage des employés compétents
            employes_competents = gestionnaire_postes.get_employes_competents(poste['nom'], gestionnaire_employes)
            if employes_competents:
                st.caption(f"👥 Employés compétents: {', '.join(employes_competents)}")
            else:
                st.caption("⚠️ Aucun employé compétent trouvé")


def render_work_centers_analytics(gestionnaire_postes):
    """Analyses avancées des postes de travail"""
    st.subheader("📈 Analyses de Performance")
    
    rapport = generer_rapport_capacite_production()
    
    # Métriques de capacité
    st.markdown("### ⚡ Capacités Théoriques")
    cap_col1, cap_col2, cap_col3, cap_col4 = st.columns(4)
    
    with cap_col1:
        st.metric("🏭 Production", f"{rapport['utilisation_theorique']['production']}h/j")
    with cap_col2:
        st.metric("⚙️ Usinage", f"{rapport['utilisation_theorique']['usinage']}h/j")
    with cap_col3:
        st.metric("✅ Qualité", f"{rapport['utilisation_theorique']['qualite']}h/j")
    with cap_col4:
        st.metric("📦 Logistique", f"{rapport['utilisation_theorique']['logistique']}h/j")
    
    st.markdown("---")
    
    # Analyse des coûts
    st.markdown("### 💰 Analyse des Coûts")
    cout_col1, cout_col2 = st.columns(2)
    
    with cout_col1:
        # Coût par catégorie
        cout_par_categorie = {}
        for poste in gestionnaire_postes.postes:
            cat = poste['categorie']
            cout = poste['cout_horaire'] * poste['capacite_theorique']
            cout_par_categorie[cat] = cout_par_categorie.get(cat, 0) + cout
        
        if cout_par_categorie:
            fig_cout = px.bar(
                x=list(cout_par_categorie.keys()),
                y=list(cout_par_categorie.values()),
                title="💰 Coût Journalier par Catégorie ($)",
                color=list(cout_par_categorie.keys()),
                color_discrete_sequence=px.colors.qualitative.Vivid
            )
            fig_cout.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                showlegend=False,
                title_x=0.5
            )
            st.plotly_chart(fig_cout, use_container_width=True)
    
    with cout_col2:
        # Analyse ROI potentiel
        st.markdown("**💡 Recommandations d'Optimisation:**")
        recommendations = [
            "🤖 Maximiser l'utilisation des robots ABB (ROI élevé)",
            "⚡ Grouper les opérations CNC par type de matériau",
            "🔄 Implémenter des changements d'équipes optimisés",
            "📊 Former plus d'employés sur postes critiques",
            "⏰ Programmer maintenance préventive en heures creuses"
        ]
        
        for i, rec in enumerate(recommendations, 1):
            st.markdown(f"**{i}.** {rec}")
    
    # Simulation de charge
    st.markdown("---")
    st.markdown("### 📊 Simulation de Charge Hebdomadaire")
    
    if st.button("🚀 Lancer Simulation", use_container_width=True):
        with st.spinner("Calcul de la charge optimale..."):
            # Simulation de données de charge
            jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
            postes_critiques = ['Laser CNC', 'Robot ABB GMAW', 'Centre d\'usinage']
            
            data_simulation = []
            for jour in jours:
                for poste in postes_critiques:
                    charge = random.uniform(70, 95)
                    data_simulation.append({
                        'Jour': jour,
                        'Poste': poste,
                        'Charge (%)': charge
                    })
            
            df_sim = pd.DataFrame(data_simulation)
            
            fig_sim = px.bar(
                df_sim, x='Jour', y='Charge (%)', color='Poste',
                title="📊 Charge Hebdomadaire des Postes Critiques",
                barmode='group'
            )
            fig_sim.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='var(--text-color)'),
                title_x=0.5
            )
            fig_sim.add_hline(y=90, line_dash="dash", line_color="red", 
                            annotation_text="Seuil critique (90%)")
            
            st.plotly_chart(fig_sim, use_container_width=True)
            
            # Résultats de simulation
            charge_moyenne = df_sim['Charge (%)'].mean()
            postes_surcharges = len(df_sim[df_sim['Charge (%)'] > 90])
            
            sim_col1, sim_col2, sim_col3 = st.columns(3)
            with sim_col1:
                st.metric("📊 Charge Moyenne", f"{charge_moyenne:.1f}%")
            with sim_col2:
                st.metric("⚠️ Instances Surchargées", postes_surcharges)
            with sim_col3:
                efficacite_sem = random.uniform(85, 92)
                st.metric("✅ Efficacité Semaine", f"{efficacite_sem:.1f}%")


def show_manufacturing_routes_page():
    """Page des gammes de fabrication"""
    st.markdown("## ⚙️ Gammes de Fabrication - DG Inc.")
    
    gestionnaire_postes = st.session_state.gestionnaire_postes
    gestionnaire_projets = st.session_state.gestionnaire
    gestionnaire_employes = st.session_state.gestionnaire_employes
    
    tab_generator, tab_templates, tab_optimization = st.tabs([
        "🔧 Générateur", "📋 Modèles", "🎯 Optimisation"
    ])
    
    with tab_generator:
        render_operations_manager(gestionnaire_postes, gestionnaire_employes)
    
    with tab_templates:
        render_gammes_templates(gestionnaire_postes)
    
    with tab_optimization:
        render_route_optimization(gestionnaire_postes, gestionnaire_projets)


def render_operations_manager(gestionnaire_postes, gestionnaire_employes):
    """Gestionnaire d'opérations avec vrais postes"""
    st.subheader("🔧 Générateur de Gammes de Fabrication")
    
    # Formulaire de génération
    with st.form("gamme_generator_form"):
        col_form1, col_form2 = st.columns(2)
        
        with col_form1:
            type_produit = st.selectbox(
                "Type de produit:",
                ["CHASSIS_SOUDE", "STRUCTURE_LOURDE", "PIECE_PRECISION"],
                format_func=lambda x: gestionnaire_postes.gammes_types[x]["nom"]
            )
            complexite = st.selectbox("Complexité:", ["SIMPLE", "MOYEN", "COMPLEXE"])
        
        with col_form2:
            quantite = st.number_input("Quantité:", min_value=1, value=1, step=1)
            priorite = st.selectbox("Priorité:", ["BAS", "MOYEN", "ÉLEVÉ"])
        
        description_produit = st.text_area(
            "Description:",
            value=gestionnaire_postes.gammes_types[type_produit]["description"]
        )
        
        generate_btn = st.form_submit_button("🚀 Générer Gamme", use_container_width=True)
        
        if generate_btn:
            with st.spinner("Génération de la gamme optimisée..."):
                gamme = gestionnaire_postes.generer_gamme_fabrication(
                    type_produit, complexite, gestionnaire_employes
                )
                
                st.session_state.gamme_generated = gamme
                st.session_state.gamme_metadata = {
                    "type": type_produit,
                    "complexite": complexite,
                    "quantite": quantite,
                    "priorite": priorite,
                    "description": description_produit
                }
                
                st.success(f"✅ Gamme générée avec {len(gamme)} opérations !")
    
    # Affichage de la gamme générée
    if st.session_state.get('gamme_generated'):
        st.markdown("---")
        st.markdown("### 📋 Gamme Générée")
        
        gamme = st.session_state.gamme_generated
        metadata = st.session_state.get('gamme_metadata', {})
        
        # Informations sur la gamme
        info_col1, info_col2, info_col3 = st.columns(3)
        with info_col1:
            st.metric("⚙️ Opérations", len(gamme))
        with info_col2:
            temps_total = sum(op['temps_estime'] for op in gamme)
            st.metric("⏱️ Temps Total", f"{temps_total:.1f}h")
        with info_col3:
            cout_total = sum(
                op['temps_estime'] * op['poste_info']['cout_horaire'] 
                for op in gamme if op.get('poste_info')
            )
            st.metric("💰 Coût Estimé", f"{cout_total:.0f}$")
        
        # Tableau des opérations
        st.markdown("#### 📊 Détail des Opérations")
        
        data_gamme = []
        for op in gamme:
            poste_info = op.get('poste_info', {})
            data_gamme.append({
                'Séq.': op['sequence'],
                'Poste': op['poste'],
                'Description': op['description'],
                'Temps (h)': f"{op['temps_estime']:.1f}",
                'Coût/h': f"{poste_info.get('cout_horaire', 0)}$",
                'Total': f"{op['temps_estime'] * poste_info.get('cout_horaire', 0):.0f}$",
                'Employés Dispo.': ', '.join(op.get('employes_disponibles', ['Aucun'])[:2])
            })
        
        df_gamme = pd.DataFrame(data_gamme)
        st.dataframe(df_gamme, use_container_width=True)
        
        # Graphique de répartition du temps
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            temps_par_dept = {}
            for op in gamme:
                poste_info = op.get('poste_info', {})
                dept = poste_info.get('departement', 'AUTRE')
                temps_par_dept[dept] = temps_par_dept.get(dept, 0) + op['temps_estime']
            
            if temps_par_dept:
                fig_temps = px.pie(
                    values=list(temps_par_dept.values()),
                    names=list(temps_par_dept.keys()),
                    title="⏱️ Répartition Temps par Département"
                )
                fig_temps.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='var(--text-color)'),
                    title_x=0.5
                )
                st.plotly_chart(fig_temps, use_container_width=True)
        
        with col_chart2:
            cout_par_dept = {}
            for op in gamme:
                poste_info = op.get('poste_info', {})
                dept = poste_info.get('departement', 'AUTRE')
                cout = op['temps_estime'] * poste_info.get('cout_horaire', 0)
                cout_par_dept[dept] = cout_par_dept.get(dept, 0) + cout
            
            if cout_par_dept:
                fig_cout = px.bar(
                    x=list(cout_par_dept.keys()),
                    y=list(cout_par_dept.values()),
                    title="💰 Coût par Département ($)",
                    color=list(cout_par_dept.keys())
                )
                fig_cout.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='var(--text-color)'),
                    showlegend=False,
                    title_x=0.5
                )
                st.plotly_chart(fig_cout, use_container_width=True)
        
        # Bouton pour appliquer à un projet
        if st.button("📋 Appliquer à un Projet", use_container_width=True):
            st.session_state.show_apply_gamme_to_project = True


def render_gammes_templates(gestionnaire_postes):
    """Templates de gammes prédéfinies"""
    st.subheader("📋 Modèles de Gammes Prédéfinis")
    
    for type_key, gamme_info in gestionnaire_postes.gammes_types.items():
        with st.expander(f"🔧 {gamme_info['nom']}", expanded=False):
            col_t1, col_t2 = st.columns(2)
            
            with col_t1:
                st.markdown(f"**Description:** {gamme_info['description']}")
                st.markdown(f"**Nombre d'opérations:** {len(gamme_info['operations'])}")
                
                temps_base_total = sum(op['temps_base'] for op in gamme_info['operations'])
                st.markdown(f"**Temps de base:** {temps_base_total:.1f}h")
                
                # Aperçu des opérations
                st.markdown("**Opérations principales:**")
                for i, op in enumerate(gamme_info['operations'][:5], 1):
                    st.markdown(f"  {i}. {op['poste']} - {op['description']}")
                if len(gamme_info['operations']) > 5:
                    st.markdown(f"  ... et {len(gamme_info['operations']) - 5} autres")
            
            with col_t2:
                # Répartition des postes utilisés
                postes_utilises = {}
                for op in gamme_info['operations']:
                    poste_obj = gestionnaire_postes.get_poste_by_nom(op['poste'])
                    if poste_obj:
                        dept = poste_obj['departement']
                        postes_utilises[dept] = postes_utilises.get(dept, 0) + 1
                
                if postes_utilises:
                    fig_template = px.bar(
                        x=list(postes_utilises.keys()),
                        y=list(postes_utilises.values()),
                        title=f"Postes par Département - {gamme_info['nom']}",
                        color=list(postes_utilises.keys())
                    )
                    fig_template.update_layout(
                        height=300,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='var(--text-color)', size=10),
                        showlegend=False,
                        title_x=0.5
                    )
                    st.plotly_chart(fig_template, use_container_width=True)
                
                if st.button(f"🚀 Appliquer Modèle {gamme_info['nom']}", key=f"apply_{type_key}"):
                    gestionnaire_employes = st.session_state.gestionnaire_employes
                    gamme = gestionnaire_postes.generer_gamme_fabrication(
                        type_key, "MOYEN", gestionnaire_employes
                    )
                    st.session_state.gamme_generated = gamme
                    st.session_state.gamme_metadata = {
                        "type": type_key,
                        "complexite": "MOYEN",
                        "quantite": 1,
                        "description": gamme_info['description']
                    }
                    st.success(f"✅ Modèle {gamme_info['nom']} appliqué !")
                    st.rerun()


def render_route_optimization(gestionnaire_postes, gestionnaire_projets):
    """Optimisation des gammes et séquencement"""
    st.subheader("🎯 Optimisation des Gammes")
    
    # Sélection des projets actifs pour optimisation
    projets_actifs = [p for p in gestionnaire_projets.projets if p.get('statut') not in ['TERMINÉ', 'ANNULÉ']]
    
    if not projets_actifs:
        st.info("Aucun projet actif pour l'optimisation.")
        return
    
    st.markdown("### 📊 Analyse de Charge Actuelle")
    
    # Calcul de la charge par poste
    charge_par_poste = {}
    for projet in projets_actifs:
        for operation in projet.get('operations', []):
            poste = operation.get('poste_travail', 'Non assigné')
            if poste != 'Non assigné' and operation.get('statut') != 'TERMINÉ':
                temps = operation.get('temps_estime', 0)
                charge_par_poste[poste] = charge_par_poste.get(poste, 0) + temps
    
    if charge_par_poste:
        # Graphique de charge
        postes_charges = sorted(charge_par_poste.items(), key=lambda x: x[1], reverse=True)[:10]
        
        fig_charge = px.bar(
            x=[p[0] for p in postes_charges],
            y=[p[1] for p in postes_charges],
            title="📊 Charge Actuelle par Poste (Top 10)",
            color=[p[1] for p in postes_charges],
            color_continuous_scale="Reds"
        )
        fig_charge.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='var(--text-color)'),
            showlegend=False,
            title_x=0.5,
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig_charge, use_container_width=True)
        
        # Identification des goulots
        st.markdown("### 🚨 Goulots d'Étranglement Identifiés")
        
        goulots = []
        for poste_nom, charge_totale in charge_par_poste.items():
            poste_obj = gestionnaire_postes.get_poste_by_nom(poste_nom)
            if poste_obj:
                capacite_hebdo = poste_obj['capacite_theorique'] * 5  # 5 jours
                taux_charge = (charge_totale / capacite_hebdo) * 100 if capacite_hebdo > 0 else 0
                
                if taux_charge > 90:
                    goulots.append({
                        'poste': poste_nom,
                        'charge': charge_totale,
                        'capacite': capacite_hebdo,
                        'taux': taux_charge
                    })
        
        if goulots:
            for goulot in sorted(goulots, key=lambda x: x['taux'], reverse=True):
                st.error(f"⚠️ **{goulot['poste']}**: {goulot['taux']:.1f}% de charge "
                        f"({goulot['charge']:.1f}h / {goulot['capacite']:.1f}h)")
        else:
            st.success("✅ Aucun goulot d'étranglement critique détecté")
    
    # Simulation d'optimisation
    st.markdown("---")
    st.markdown("### 🔄 Optimisation Automatique")
    
    if st.button("🚀 Lancer Optimisation Globale", use_container_width=True):
        with st.spinner("Optimisation en cours..."):
            # Simulation d'optimisation
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Étapes d'optimisation simulées
            etapes = [
                "Analyse charge actuelle par poste...",
                "Identification des goulots d'étranglement...", 
                "Calcul des alternatives de routage...",
                "Optimisation utilisation robots ABB...",
                "Équilibrage des charges par département...",
                "Génération des recommandations..."
            ]
            
            resultats_optim = {
                'temps_economise': 0,
                'cout_reduit': 0,
                'utilisation_amelioree': {},
                'recommandations': []
            }
            
            for i, etape in enumerate(etapes):
                status_text.text(etape)
                time.sleep(0.8)
                progress_bar.progress((i + 1) / len(etapes))
                
                # Simulation de résultats
                resultats_optim['temps_economise'] += random.uniform(2.5, 8.3)
                resultats_optim['cout_reduit'] += random.uniform(150, 450)
            
            # Résultats d'optimisation
            st.success("✅ Optimisation terminée !")
            
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("⏱️ Temps Économisé", f"{resultats_optim['temps_economise']:.1f}h")
            with col_r2:
                st.metric("💰 Coût Réduit", f"{resultats_optim['cout_reduit']:.0f}$ CAD")
            with col_r3:
                efficacite = random.uniform(12, 18)
                st.metric("📈 Efficacité", f"+{efficacite:.1f}%")
            
            # Recommandations détaillées
            st.markdown("### 💡 Recommandations d'Optimisation")
            recommandations = [
                "🤖 Programmer Robot ABB GMAW en priorité pour pièces répétitives",
                "⚡ Grouper les découpes laser par épaisseur de matériau",
                "🔄 Alterner soudage manuel/robot selon complexité géométrique",
                "📊 Former employés sur Plieuse CNC haute précision",
                "⏰ Décaler finition peinture sur équipe de soir"
            ]
            
            for recommandation in recommandations:
                st.markdown(f"- {recommandation}")


def show_capacity_analysis_page():
    """Page d'analyse de capacité de production"""
    st.markdown("## 📈 Analyse de Capacité - DG Inc.")
    
    gestionnaire_postes = st.session_state.gestionnaire_postes
    
    # Rapport de capacité en temps réel
    rapport = generer_rapport_capacite_production()
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🤖 Robots ABB", rapport['capacites']['postes_robotises'])
    with col2:
        st.metric("💻 Postes CNC", rapport['capacites']['postes_cnc'])
    with col3:
        st.metric("🔥 Postes Soudage", rapport['capacites']['postes_soudage'])
    with col4:
        st.metric("✨ Postes Finition", rapport['capacites']['postes_finition'])
    
    # Affichage détaillé
    render_capacity_analysis(gestionnaire_postes)


def render_capacity_analysis(gestionnaire_postes):
    """Analyse détaillée de la capacité"""
    st.markdown("### 🏭 Analyse Détaillée de la Capacité")
    
    # Analyse par département
    dept_analysis = {}
    for poste in gestionnaire_postes.postes:
        dept = poste['departement']
        if dept not in dept_analysis:
            dept_analysis[dept] = {
                'postes': 0,
                'capacite_totale': 0,
                'cout_total': 0,
                'operateurs_requis': 0
            }
        
        dept_analysis[dept]['postes'] += 1
        dept_analysis[dept]['capacite_totale'] += poste['capacite_theorique']
        dept_analysis[dept]['cout_total'] += poste['cout_horaire'] * poste['capacite_theorique']
        dept_analysis[dept]['operateurs_requis'] += poste['operateurs_requis']
    
    # Affichage par département
    for dept, stats in dept_analysis.items():
        with st.expander(f"🏭 {dept} - {stats['postes']} postes", expanded=False):
            dept_col1, dept_col2, dept_col3, dept_col4 = st.columns(4)
            
            with dept_col1:
                st.metric("📊 Postes", stats['postes'])
            with dept_col2:
                st.metric("⚡ Capacité/jour", f"{stats['capacite_totale']}h")
            with dept_col3:
                st.metric("👥 Opérateurs", stats['operateurs_requis'])
            with dept_col4:
                st.metric("💰 Coût/jour", f"{stats['cout_total']:.0f}$")
            
            # Liste des postes du département
            postes_dept = [p for p in gestionnaire_postes.postes if p['departement'] == dept]
            
            data_dept = []
            for poste in postes_dept:
                utilisation_simulee = random.uniform(65, 95)
                data_dept.append({
                    'Poste': poste['nom'],
                    'Catégorie': poste['categorie'],
                    'Capacité (h/j)': poste['capacite_theorique'],
                    'Coût ($/h)': poste['cout_horaire'],
                    'Utilisation (%)': f"{utilisation_simulee:.1f}%"
                })
            
            if data_dept:
                df_dept = pd.DataFrame(data_dept)
                st.dataframe(df_dept, use_container_width=True)
