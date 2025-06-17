# formulaires/estimations/interface_estimation.py

"""
Interface utilisateur pour les Estimations.
Contient tous les composants d'affichage et d'interaction pour les devis clients.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from .gestionnaire_estimation import GestionnaireEstimations
from ..utils.helpers import (
    get_projets_actifs,
    get_employes_actifs,
    get_clients_actifs,
    formater_montant,
    formater_delai,
    generer_couleur_statut,
    generer_couleur_priorite
)

def render_estimations_tab(gestionnaire):
    """Interface principale pour les Estimations."""
    st.markdown("### 📊 Estimations")
    
    # Initialiser le gestionnaire spécialisé
    if 'gestionnaire_estimation' not in st.session_state:
        st.session_state.gestionnaire_estimation = GestionnaireEstimations(gestionnaire)
    
    gestionnaire_estimation = st.session_state.gestionnaire_estimation
    
    # Actions rapides avec métriques
    _render_actions_rapides_estimation(gestionnaire_estimation)
    
    # Affichage selon l'action
    action = st.session_state.get('form_action', 'list_estimations')
    
    if action == "create_estimation":
        render_estimation_form(gestionnaire_estimation)
    elif action == "list_estimations":
        render_estimation_list(gestionnaire_estimation)
    elif action == "manage_versions":
        render_manage_versions(gestionnaire_estimation)
    elif action == "estimations_acceptees":
        render_estimations_acceptees(gestionnaire_estimation)
    elif action == "analyse_rentabilite":
        render_analyse_rentabilite(gestionnaire_estimation)
    elif action == "stats_estimation":
        render_estimation_stats(gestionnaire_estimation)

def _render_actions_rapides_estimation(gestionnaire_estimation):
    """Actions rapides avec métriques pour les estimations."""
    try:
        stats = gestionnaire_estimation.get_statistiques_estimation()
        
        # Métriques principales avec gestion des valeurs None
        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        
        with col_m1:
            total = stats.get('total', 0) or 0
            st.metric("📊 Total EST", total)
        
        with col_m2:
            acceptees = stats.get('acceptees', 0) or 0
            taux = stats.get('taux_acceptation', 0) or 0
            st.metric("✅ Acceptées", acceptees, delta=f"{taux:.1f}%")
        
        with col_m3:
            en_negociation = stats.get('en_negociation', 0) or 0
            st.metric("📤 En Négociation", en_negociation)
        
        with col_m4:
            ca_realise = stats.get('ca_realise', 0) or 0
            st.metric("💰 CA Réalisé", f"{ca_realise:,.0f}$ CAD")
        
        with col_m5:
            expirees = stats.get('expirees', 0) or 0
            st.metric("⏰ Expirées", expirees)
        
        # Alertes pour estimations bientôt expirées
        try:
            estimations_urgentes = gestionnaire_estimation.get_estimations_expirees()
            if estimations_urgentes:
                st.warning(f"⚠️ {len(estimations_urgentes)} estimation(s) expire(nt) dans ≤ 3 jours!")
        except Exception as e:
            st.warning(f"Erreur vérification expirations: {e}")
        
        # Actions principales
        col_action1, col_action2, col_action3, col_action4 = st.columns(4)
        
        with col_action1:
            if st.button("➕ Nouvelle Estimation", use_container_width=True, key="est_nouveau"):
                st.session_state.form_action = "create_estimation"
                st.rerun()
        
        with col_action2:
            if st.button("📋 Liste Estimations", use_container_width=True, key="est_liste"):
                st.session_state.form_action = "list_estimations"
                st.rerun()
        
        with col_action3:
            if st.button("🔄 Gestion Versions", use_container_width=True, key="est_versions"):
                st.session_state.form_action = "manage_versions"
                st.rerun()
        
        with col_action4:
            if st.button("✅ Acceptées", use_container_width=True, key="est_acceptees"):
                st.session_state.form_action = "estimations_acceptees"
                st.rerun()
                
    except Exception as e:
        st.error(f"Erreur affichage métriques estimations: {e}")
        st.info("Module Estimations en cours d'initialisation...")

def render_estimation_form(gestionnaire_estimation):
    """Formulaire de création d'estimation avec calculs automatiques."""
    st.markdown("#### ➕ Nouvelle Estimation Client")
    
    try:
        with st.form("estimation_form", clear_on_submit=True):
            # En-tête du formulaire
            col1, col2 = st.columns(2)
            
            with col1:
                numero_est = gestionnaire_estimation.base.generer_numero_document('ESTIMATION')
                st.text_input("N° Estimation", value=numero_est, disabled=True)
                
                # Sélection CLIENT
                clients_disponibles = get_clients_actifs()
                client_options = [("", "Sélectionner un client")] + [(c['id'], f"{c['nom']} - {c.get('secteur', 'N/A')}") for c in clients_disponibles]
                client_id = st.selectbox(
                    "Client *",
                    options=[c[0] for c in client_options],
                    format_func=lambda x: next((c[1] for c in client_options if c[0] == x), ""),
                    help="Client pour lequel établir le devis"
                )
                
                date_creation = st.date_input("Date de Création", datetime.now().date())
            
            with col2:
                # Commercial responsable
                employes = get_employes_actifs()
                employe_options = [("", "Sélectionner un commercial")] + [(e['id'], f"{e['prenom']} {e['nom']} - {e.get('poste', '')}") for e in employes]
                employe_id = st.selectbox(
                    "Commercial Responsable *",
                    options=[e[0] for e in employe_options],
                    format_func=lambda x: next((e[1] for e in employe_options if e[0] == x), "")
                )
                
                priorite = st.selectbox("Priorité", ['NORMAL', 'URGENT', 'CRITIQUE'], index=0)
            
            # SPÉCIFICITÉS EST - PARAMÈTRES DU DEVIS
            st.markdown("##### 🎯 Paramètres du Devis")
            col_est1, col_est2 = st.columns(2)
            
            with col_est1:
                template_industrie = st.selectbox("Template Industrie *", 
                    ["AUTOMOBILE", "AERONAUTIQUE", "CONSTRUCTION", "GENERAL"],
                    help="Le template détermine les coefficients et marges automatiques")
                
                # Récupération des paramètres du template
                template_info = gestionnaire_estimation.TEMPLATES_INDUSTRIE.get(template_industrie)
                marge_defaut = template_info['marge_defaut']
                
                validite_devis = st.number_input("Validité Devis (jours)", 
                    min_value=15, value=30, max_value=90,
                    help="Durée pendant laquelle le devis reste valide")
                
                type_estimation = st.selectbox("Type d'Estimation",
                    ["Devis Standard", "Estimation Rapide", "Appel d'Offres", "Révision"])
            
            with col_est2:
                marge_beneficiaire = st.slider("Marge Bénéficiaire (%)", 5, 50, marge_defaut,
                    help=f"Marge par défaut pour {template_industrie}: {marge_defaut}%")
                
                devise_devis = st.selectbox("Devise", ["CAD", "USD", "EUR"])
                
                conditions_paiement_client = st.selectbox("Conditions Paiement",
                    [template_info['conditions_paiement'], "30 jours net", "À réception", "60 jours net"])
            
            # Projet existant ou nouveau
            st.markdown("##### 🏢 Client et Projet")
            
            base_sur_projet = False
            projet_base_id = None
            calculs_auto = None
            
            if client_id:
                projets_client = _get_projets_client(client_id)
                if projets_client:
                    col_proj1, col_proj2 = st.columns(2)
                    with col_proj1:
                        base_sur_projet = st.checkbox("Baser sur Projet Existant",
                            help="Utiliser un projet existant pour les calculs automatiques")
                    with col_proj2:
                        if base_sur_projet:
                            projet_base_id = st.selectbox("Projet de Base",
                                options=[p['id'] for p in projets_client],
                                format_func=lambda x: next((f"{p['nom_projet']}" for p in projets_client if p['id'] == x), ""))
                else:
                    st.info("Ce client n'a pas de projets existants. L'estimation sera créée manuellement.")
            
            # CALCULS AUTOMATIQUES AVANCÉS
            st.markdown("##### 🔢 Calculs Automatiques")
            
            activer_calculs_auto = st.checkbox("Activer Calculs Automatiques", value=bool(projet_base_id))
            
            if activer_calculs_auto and projet_base_id:
                # Calculs basés sur projet existant
                try:
                    calculs_auto = gestionnaire_estimation.calculer_estimation_automatique(
                        projet_base_id, template_industrie, marge_beneficiaire
                    )
                    
                    if calculs_auto:
                        col_calc1, col_calc2, col_calc3 = st.columns(3)
                        with col_calc1:
                            st.metric("Coût Matériaux", f"{calculs_auto['cout_materiaux']:,.2f}$ {devise_devis}")
                            st.metric("Coût Main d'Œuvre", f"{calculs_auto['cout_main_oeuvre']:,.2f}$ {devise_devis}")
                        with col_calc2:
                            st.metric("Coût Direct", f"{calculs_auto['cout_direct']:,.2f}$ {devise_devis}")
                            st.metric("Frais Généraux (20%)", f"{calculs_auto['cout_indirect']:,.2f}$ {devise_devis}")
                        with col_calc3:
                            st.metric("Marge Bénéficiaire", f"{calculs_auto['marge']:,.2f}$ {devise_devis}")
                            st.metric("Prix HT", f"{calculs_auto['prix_HT']:,.2f}$ {devise_devis}")
                        
                        st.success(f"💰 **PRIX TOTAL TTC : {calculs_auto['prix_TTC']:,.2f}$ {devise_devis}**")
                        
                        # Affichage détail template
                        st.info(f"""
                        **Template {template_industrie}** : 
                        Coefficient complexité: {template_info['coefficient_complexite']} | 
                        Certification: {template_info['cout_certification_pct']}% | 
                        Délai standard: {template_info['delai_standard']} jours
                        """)
                    else:
                        st.error("❌ Erreur dans les calculs automatiques")
                except Exception as e:
                    st.error(f"❌ Erreur calculs automatiques: {e}")
                    calculs_auto = None
            elif activer_calculs_auto and not projet_base_id:
                st.info("Sélectionnez un projet de base pour activer les calculs automatiques")
            
            # Articles/Services du devis
            st.markdown("##### 📦 Articles/Services du Devis")
            
            col_desc, col_qty, col_unit, col_price, col_marge = st.columns([3, 1, 1, 1.5, 1])
            with col_desc:
                st.markdown("**Description**")
            with col_qty:
                st.markdown("**Quantité**")
            with col_unit:
                st.markdown("**Unité**")
            with col_price:
                st.markdown("**Prix Unit. HT**")
            with col_marge:
                st.markdown("**Marge %**")
            
            lignes_estimation = []
            prix_total_manuel = 0
            
            nb_lignes = 6 if not calculs_auto else 3  # Moins de lignes si calculs auto
            
            for i in range(nb_lignes):
                col_desc, col_qty, col_unit, col_price, col_marge = st.columns([3, 1, 1, 1.5, 1])
                
                with col_desc:
                    desc = st.text_input("", key=f"est_desc_{i}", placeholder="Description article/service")
                with col_qty:
                    qty = st.number_input("", min_value=0.0, key=f"est_qty_{i}", format="%.2f", step=1.0)
                with col_unit:
                    unite = st.selectbox("", ["UN", "H", "J", "M²", "KG", "SERVICE"], key=f"est_unit_{i}")
                with col_price:
                    prix_ht = st.number_input("", min_value=0.0, key=f"est_price_{i}", format="%.2f", step=0.01)
                with col_marge:
                    marge_ligne = st.number_input("", min_value=0, max_value=100, key=f"est_marge_{i}", value=marge_beneficiaire)
                
                if desc and qty > 0:
                    prix_avec_marge = prix_ht * (1 + marge_ligne / 100)
                    montant_ligne = qty * prix_avec_marge
                    prix_total_manuel += montant_ligne
                    
                    lignes_estimation.append({
                        'description': desc,
                        'quantite': qty,
                        'unite': unite,
                        'prix_unitaire': prix_avec_marge,
                        'prix_unitaire_ht': prix_ht,
                        'marge_pct': marge_ligne,
                        'montant_ligne': montant_ligne
                    })
            
            # Conditions spéciales selon template industrie
            st.markdown("##### 📋 Conditions Spéciales par Industrie")
            
            col_cond1, col_cond2 = st.columns(2)
            with col_cond1:
                garantie_proposee = st.text_input("Garantie Proposée",
                    value=template_info['garantie'],
                    help="Garantie selon le template industrie")
                
                delai_execution = st.number_input("Délai d'Exécution (jours)",
                    value=template_info['delai_standard'],
                    help="Délai standard selon l'industrie")
                
                lieu_execution = st.text_input("Lieu d'Exécution",
                    value="Ateliers DG Inc., Montréal")
            
            with col_cond2:
                # Clauses techniques automatiques selon template
                clauses_techniques = st.text_area("Clauses Techniques",
                    value='\n'.join([f"• {clause}" for clause in template_info['clauses_techniques']]),
                    height=100,
                    help="Clauses techniques pré-remplies selon l'industrie")
                
                options_incluses = st.multiselect("Options Incluses",
                    ["Transport", "Installation", "Formation", "Maintenance 1 an", "Support technique"],
                    default=["Support technique"])
            
            # Validité et révisions
            st.markdown("##### ⏰ Validité et Révisions")
            
            col_valid1, col_valid2 = st.columns(2)
            with col_valid1:
                date_validite = st.date_input("Date Limite Validité",
                    value=datetime.now().date() + timedelta(days=validite_devis))
                
                revision_autorisee = st.checkbox("Révisions Autorisées", value=True,
                    help="Le client peut-il demander des modifications?")
            
            with col_valid2:
                nb_revisions_max = st.number_input("Nombre Révisions Max", 
                    min_value=0, value=3, disabled=not revision_autorisee)
                
                frais_revision = st.number_input("Frais Révision ($)", 
                    min_value=0.0, value=0.0, format="%.2f",
                    disabled=not revision_autorisee)
            
            # Notes et observations
            notes_estimation = st.text_area("Notes et Observations", height=80,
                placeholder="Contexte du projet, exigences particulières, conditions spéciales...")
            
            # Récapitulatif financier final
            prix_final = prix_total_manuel if lignes_estimation else (calculs_auto.get('prix_TTC', 0) if calculs_auto else 0)
            
            if prix_final > 0:
                taxes = prix_final * 0.14975 if not calculs_auto else calculs_auto.get('taxes', 0)
                prix_ttc_final = prix_final + taxes if not calculs_auto else prix_final
                
                st.markdown(f"""
                <div style='background:#f0f9ff;padding:1rem;border-radius:8px;border-left:4px solid #3b82f6;'>
                    <h5 style='color:#1e40af;margin:0;'>💰 Récapitulatif Financier Final</h5>
                    <p style='margin:0.5rem 0 0 0;'><strong>Prix TTC : {prix_ttc_final:,.2f} {devise_devis}</strong></p>
                    <p style='margin:0;'>Template : {template_industrie} | Marge : {marge_beneficiaire}%</p>
                    <p style='margin:0;font-size:0.9em;'>Validité : {validite_devis} jours | Délai : {delai_execution} jours</p>
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
                submit_envoyer = st.form_submit_button("📤 Créer et Envoyer Client", use_container_width=True)
            
            # Traitement de la soumission
            if submit_brouillon or submit_valide or submit_envoyer:
                # Validation des champs obligatoires
                erreurs = []
                
                if not client_id:
                    erreurs.append("Client obligatoire")
                if not employe_id:
                    erreurs.append("Commercial responsable obligatoire")
                if not template_industrie:
                    erreurs.append("Template industrie obligatoire")
                if not lignes_estimation and not calculs_auto:
                    erreurs.append("Au moins un article ou des calculs automatiques requis")
                if prix_final <= 0:
                    erreurs.append("Le montant de l'estimation doit être supérieur à 0")
                
                if erreurs:
                    st.error("❌ Erreurs de validation :")
                    for erreur in erreurs:
                        st.error(f"• {erreur}")
                else:
                    # Déterminer le statut
                    if submit_brouillon:
                        statut = 'BROUILLON'
                    elif submit_envoyer:
                        statut = 'ENVOYÉ'
                    else:
                        statut = 'VALIDÉ'
                    
                    # Préparation des données
                    data = {
                        'numero_document': numero_est,
                        'project_id': projet_base_id,
                        'company_id': client_id,
                        'employee_id': employe_id,
                        'statut': statut,
                        'priorite': priorite,
                        'date_creation': date_creation,
                        'date_echeance': date_validite,
                        'montant_total': prix_final,
                        'notes': f"Estimation {template_industrie} - {notes_estimation}",
                        'template_industrie': template_industrie,
                        'marge_beneficiaire': marge_beneficiaire,
                        'devise_devis': devise_devis,
                        'validite_devis': validite_devis,
                        'type_estimation': type_estimation,
                        'conditions_paiement': conditions_paiement_client,
                        'garantie_proposee': garantie_proposee,
                        'delai_execution': delai_execution,
                        'lieu_execution': lieu_execution,
                        'options_incluses': options_incluses,
                        'revision_autorisee': revision_autorisee,
                        'nb_revisions_max': nb_revisions_max,
                        'frais_revision': frais_revision,
                        'date_validite': date_validite,
                        'projet_base_id': projet_base_id,
                        'calculs_automatiques': bool(calculs_auto),
                        'lignes': lignes_estimation or _creer_lignes_depuis_calculs(calculs_auto)
                    }
                    
                    # Création de l'estimation
                    try:
                        estimation_id = gestionnaire_estimation.creer_estimation(data)
                        
                        if estimation_id:
                            # Messages de succès personnalisés
                            if submit_envoyer:
                                st.success(f"📤 Estimation {numero_est} créée et envoyée au client!")
                                st.info("📧 Le client a été notifié et le suivi commercial est activé.")
                            else:
                                st.success(f"✅ Estimation {numero_est} créée avec succès!")
                            
                            # Actions suivantes
                            col_next1, col_next2, col_next3 = st.columns(3)
                            with col_next1:
                                if st.button("📋 Voir la Liste", use_container_width=True, key="est_voir_liste"):
                                    st.session_state.form_action = "list_estimations"
                                    st.rerun()
                            with col_next2:
                                if st.button("🔄 Créer Version v2", use_container_width=True, key="est_version_v2"):
                                    st.session_state.base_estimation_id = estimation_id
                                    st.session_state.form_action = "manage_versions"
                                    st.rerun()
                            with col_next3:
                                if st.button("➕ Nouvelle Estimation", use_container_width=True, key="est_nouvelle"):
                                    st.rerun()
                        else:
                            st.error("❌ Erreur lors de la création de l'estimation")
                    except Exception as e:
                        st.error(f"❌ Erreur création estimation: {e}")
    except Exception as e:
        st.error(f"Erreur formulaire estimation: {e}")
        st.info("💡 Vérifiez que tous les modules requis sont initialisés")

def render_estimation_list(gestionnaire_estimation):
    """Liste des Estimations avec filtres avancés."""
    st.markdown("#### 📋 Liste des Estimations")
    
    try:
        estimations = gestionnaire_estimation.get_estimations()
        
        if not estimations:
            st.info("Aucune Estimation créée. Créez votre premier devis client!")
            if st.button("➕ Créer Première Estimation", use_container_width=True):
                st.session_state.form_action = "create_estimation"
                st.rerun()
            return
        
        # Métriques rapides
        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        
        with col_m1:
            st.metric("📊 Total EST", len(estimations))
        with col_m2:
            acceptees = len([e for e in estimations if e['statut'] == 'APPROUVÉ'])
            st.metric("✅ Acceptées", acceptees)
        with col_m3:
            en_cours = len([e for e in estimations if e['statut'] in ['VALIDÉ', 'ENVOYÉ']])
            st.metric("📤 En Cours", en_cours)
        with col_m4:
            montant_total = sum(e.get('montant_total', 0) or 0 for e in estimations)
            st.metric("💰 CA Potentiel", f"{montant_total:,.0f}$ CAD")
        with col_m5:
            expirees = len([e for e in estimations if 'Expirée' in str(e.get('statut_validite', ''))])
            st.metric("⏰ Expirées", expirees)
        
        # Interface de liste simplifiée pour éviter les erreurs
        st.markdown("##### 📋 Estimations Disponibles")
        
        if estimations:
            for est in estimations[:10]:  # Limiter l'affichage
                with st.expander(f"EST {est.get('numero_document', 'N/A')} - {est.get('company_nom', 'N/A')}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Statut:** {est.get('statut', 'N/A')}")
                        st.write(f"**Template:** {est.get('template_industrie', 'N/A')}")
                    with col2:
                        montant = est.get('montant_total', 0) or 0
                        st.write(f"**Montant:** {montant:,.2f}$ CAD")
                        st.write(f"**Priorité:** {est.get('priorite', 'N/A')}")
                    with col3:
                        if st.button("👁️ Détails", key=f"detail_{est.get('id')}", use_container_width=True):
                            st.info("Fonctionnalité de détails en cours d'implémentation")
        else:
            st.info("Aucune estimation trouvée")
            
    except Exception as e:
        st.error(f"Erreur affichage liste estimations: {e}")
        st.info("Module en cours d'initialisation...")

def render_manage_versions(gestionnaire_estimation):
    """Interface de gestion des versions d'estimations."""
    st.markdown("#### 🔄 Gestion des Versions")
    st.info("Fonctionnalité de gestion des versions en cours d'implémentation...")

def render_estimations_acceptees(gestionnaire_estimation):
    """Interface des estimations acceptées et conversion en projets."""
    st.markdown("#### ✅ Estimations Acceptées")
    st.info("Fonctionnalité de conversion en projets en cours d'implémentation...")

def render_analyse_rentabilite(gestionnaire_estimation):
    """Interface d'analyse de rentabilité des estimations."""
    st.markdown("#### 📊 Analyse de Rentabilité")
    st.info("Fonctionnalité d'analyse de rentabilité en cours d'implémentation...")

def render_estimation_stats(gestionnaire_estimation):
    """Interface des statistiques détaillées."""
    st.markdown("#### 📊 Statistiques Estimations")
    st.info("Fonctionnalité de statistiques détaillées en cours d'implémentation...")

# Fonctions utilitaires
def _get_projets_client(client_id):
    """Récupère les projets d'un client spécifique."""
    try:
        query = "SELECT id, nom_projet FROM projects WHERE client_company_id = ? ORDER BY nom_projet"
        rows = st.session_state.erp_db.execute_query(query, (client_id,))
        return [dict(row) for row in rows]
    except:
        return []

def _creer_lignes_depuis_calculs(calculs_auto):
    """Crée les lignes d'estimation depuis les calculs automatiques."""
    if not calculs_auto:
        return []
    
    lignes = []
    if calculs_auto.get('cout_materiaux', 0) > 0:
        lignes.append({
            'description': 'Matériaux et fournitures',
            'quantite': 1,
            'unite': 'FORFAIT',
            'prix_unitaire': calculs_auto['cout_materiaux']
        })
    
    if calculs_auto.get('cout_main_oeuvre', 0) > 0:
        lignes.append({
            'description': 'Main d\'œuvre et montage',
            'quantite': 1,
            'unite': 'FORFAIT',
            'prix_unitaire': calculs_auto['cout_main_oeuvre']
        })
    
    return lignes
