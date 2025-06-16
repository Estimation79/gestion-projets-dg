# formulaires/demandes_prix/interface_dp.py

"""
Interface utilisateur pour les Demandes de Prix.
Contient tous les composants d'affichage et d'interaction pour RFQ multi-fournisseurs.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from .gestionnaire_dp import GestionnaireDemandesPrix
from ..utils.helpers import (
    get_fournisseurs_actifs,
    get_employes_actifs,
    get_projets_actifs,
    formater_montant,
    formater_delai,
    generer_couleur_statut,
    generer_couleur_priorite
)

def render_demandes_prix_tab(gestionnaire):
    """Interface principale pour les Demandes de Prix - RFQ Multi-Fournisseurs."""
    st.markdown("### 💰 Demandes de Prix (RFQ)")
    
    # Initialiser le gestionnaire spécialisé
    if 'gestionnaire_demande_prix' not in st.session_state:
        st.session_state.gestionnaire_demande_prix = GestionnaireDemandesPrix(gestionnaire)
    
    gestionnaire_dp = st.session_state.gestionnaire_demande_prix
    
    # Actions rapides avec métriques
    _render_actions_rapides_dp(gestionnaire_dp)
    
    # Affichage selon l'action
    action = st.session_state.get('form_action', 'list_demande_prix')
    
    if action == "create_demande_prix":
        render_demande_prix_form(gestionnaire_dp)
    elif action == "list_demande_prix":
        render_demande_prix_list(gestionnaire_dp)
    elif action == "compare_offers":
        render_compare_offers(gestionnaire_dp)
    elif action == "select_winner":
        render_select_winner(gestionnaire_dp)
    elif action == "stats_demande_prix":
        render_demande_prix_stats(gestionnaire_dp)

def _render_actions_rapides_dp(gestionnaire_dp):
    """Actions rapides avec métriques spécifiques DP."""
    stats = gestionnaire_dp.get_statistiques_demande_prix()
    
    # Métriques principales
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    
    with col_m1:
        total = stats.get('total', 0)
        st.metric("💰 Total RFQs", total)
    
    with col_m2:
        en_cours = stats.get('dp_en_cours', 0)
        st.metric("📤 En Cours", en_cours)
    
    with col_m3:
        terminees = stats.get('dp_terminees', 0)
        taux_success = (terminees / total * 100) if total > 0 else 0
        st.metric("✅ Finalisées", terminees, delta=f"{taux_success:.1f}%")
    
    with col_m4:
        taux_conversion = stats.get('taux_conversion_bc', 0)
        st.metric("🔄 Taux Conversion BC", f"{taux_conversion:.1f}%")
    
    with col_m5:
        delai_moyen = stats.get('delai_moyen_reponse', 7)
        st.metric("⏱️ Délai Moyen Réponse", f"{delai_moyen}j")
    
    # Actions principales
    st.markdown("---")
    col_action1, col_action2, col_action3, col_action4 = st.columns(4)
    
    with col_action1:
        if st.button("➕ Nouvelle RFQ", use_container_width=True, key="dp_nouveau"):
            st.session_state.form_action = "create_demande_prix"
            st.rerun()
    
    with col_action2:
        if st.button("📋 Liste RFQs", use_container_width=True, key="dp_liste"):
            st.session_state.form_action = "list_demande_prix"
            st.rerun()
    
    with col_action3:
        if st.button("📊 Comparer Offres", use_container_width=True, key="dp_comparer"):
            st.session_state.form_action = "compare_offers"
            st.rerun()
    
    with col_action4:
        if st.button("🏆 Sélectionner Gagnant", use_container_width=True, key="dp_selection"):
            st.session_state.form_action = "select_winner"
            st.rerun()

def render_demande_prix_form(gestionnaire_dp):
    """Formulaire de création de Demande de Prix - RFQ Multi-Fournisseurs."""
    st.markdown("#### ➕ Nouvelle Demande de Prix (RFQ)")
    
    with st.form("demande_prix_form", clear_on_submit=True):
        # En-tête du formulaire
        col1, col2 = st.columns(2)
        
        with col1:
            numero_dp = gestionnaire_dp.base.generer_numero_document('DEMANDE_PRIX')
            st.text_input("N° Demande de Prix", value=numero_dp, disabled=True)
            
            # Employé responsable
            employes = get_employes_actifs()
            employe_options = [("", "Sélectionner un responsable")] + [(e['id'], f"{e['prenom']} {e['nom']} - {e['poste']}") for e in employes]
            employe_id = st.selectbox(
                "Responsable RFQ *",
                options=[e[0] for e in employe_options],
                format_func=lambda x: next((e[1] for e in employe_options if e[0] == x), "")
            )
            
            date_creation = st.date_input("Date de Création", datetime.now().date())
        
        with col2:
            priorite = st.selectbox("Priorité", gestionnaire_dp.base.priorites, index=0)
            
            # Projet associé (optionnel)
            projets = get_projets_actifs()
            if projets:
                projet_options = [("", "Aucun projet associé")] + [(p['id'], f"#{p['id']} - {p['nom_projet']}") for p in projets]
                projet_id = st.selectbox(
                    "Projet Associé (optionnel)",
                    options=[p[0] for p in projet_options],
                    format_func=lambda x: next((p[1] for p in projet_options if p[0] == x), "")
                )
            else:
                projet_id = None
            
            date_echeance_reponse = st.date_input("Date Limite Réponses", datetime.now().date() + timedelta(days=7))
        
        # SPÉCIFICITÉS DP - PARAMÈTRES DE L'APPEL D'OFFRES
        st.markdown("##### 🎯 Paramètres de l'Appel d'Offres")
        col_rfq1, col_rfq2 = st.columns(2)
        
        with col_rfq1:
            type_rfq = st.selectbox("Type d'Appel d'Offres", gestionnaire_dp.types_rfq)
            delai_reponse = st.number_input("Délai Réponse (jours)", 
                min_value=1, value=7, max_value=30)
            mode_evaluation = st.selectbox("Mode d'Évaluation",
                ["Prix seul", "Offre économiquement avantageuse", "Qualité-Prix", "Technique"])
        
        with col_rfq2:
            validite_offre = st.number_input("Validité Offre (jours)", 
                min_value=15, value=30, max_value=90)
            conditions_participation = st.text_input("Conditions Participation",
                placeholder="Ex: Certification ISO 9001 requise")
            langue_reponse = st.selectbox("Langue des Réponses", ["Français", "Anglais", "Bilingue"])
        
        # CRITÈRES D'ÉVALUATION AVEC PONDÉRATIONS (SPÉCIFICITÉ UNIQUE DP)
        st.markdown("##### ⚖️ Critères d'Évaluation et Pondérations")
        st.info("💡 Les pondérations doivent totaliser 100%")
        
        criteres_eval = {}
        col_crit1, col_crit2, col_crit3 = st.columns(3)
        
        with col_crit1:
            critere_prix = st.checkbox("Prix", value=True)
            ponderation_prix = st.slider("Pondération Prix (%)", 0, 100, 40, disabled=not critere_prix)
            if critere_prix:
                criteres_eval['prix'] = {'actif': True, 'ponderation': ponderation_prix}
        
        with col_crit2:
            critere_delai = st.checkbox("Délai de Livraison", value=True)
            ponderation_delai = st.slider("Pondération Délai (%)", 0, 100, 30, disabled=not critere_delai)
            if critere_delai:
                criteres_eval['delai'] = {'actif': True, 'ponderation': ponderation_delai}
        
        with col_crit3:
            critere_qualite = st.checkbox("Qualité Fournisseur", value=True)
            ponderation_qualite = st.slider("Pondération Qualité (%)", 0, 100, 30, disabled=not critere_qualite)
            if critere_qualite:
                criteres_eval['qualite'] = {'actif': True, 'ponderation': ponderation_qualite}
        
        # Autres critères optionnels
        col_crit4, col_crit5 = st.columns(2)
        with col_crit4:
            critere_proximite = st.checkbox("Proximité Géographique")
            ponderation_proximite = st.slider("Pondération Proximité (%)", 0, 100, 0, disabled=not critere_proximite)
            if critere_proximite:
                criteres_eval['proximite'] = {'actif': True, 'ponderation': ponderation_proximite}
        
        with col_crit5:
            critere_experience = st.checkbox("Expérience Secteur")
            ponderation_experience = st.slider("Pondération Expérience (%)", 0, 100, 0, disabled=not critere_experience)
            if critere_experience:
                criteres_eval['experience'] = {'actif': True, 'ponderation': ponderation_experience}
        
        # Validation des pondérations
        total_ponderation = sum(crit.get('ponderation', 0) for crit in criteres_eval.values())
        
        if total_ponderation != 100:
            st.error(f"⚠️ Total des pondérations : {total_ponderation}% (doit être 100%)")
        else:
            st.success(f"✅ Total des pondérations : {total_ponderation}%")
        
        # SÉLECTION MULTIPLE FOURNISSEURS (SPÉCIFICITÉ UNIQUE DP)
        st.markdown("##### 🏢 Sélection des Fournisseurs (Multi-sélection)")
        
        fournisseurs_disponibles = get_fournisseurs_actifs()
        
        if not fournisseurs_disponibles:
            st.error("❌ Aucun fournisseur disponible. Veuillez d'abord ajouter des fournisseurs dans le CRM.")
            fournisseurs_selectionnes = []
        else:
            # Interface de sélection avancée
            col_fourn1, col_fourn2 = st.columns(2)
            
            with col_fourn1:
                # Filtre par secteur
                secteurs_disponibles = list(set([f.get('secteur', 'N/A') for f in fournisseurs_disponibles if f.get('secteur')]))
                filtre_secteur = st.multiselect("Filtrer par Secteur", 
                    ['Tous'] + secteurs_disponibles, default=['Tous'])
                
                # Application du filtre
                if 'Tous' in filtre_secteur:
                    fournisseurs_filtres = fournisseurs_disponibles
                else:
                    fournisseurs_filtres = [f for f in fournisseurs_disponibles if f.get('secteur') in filtre_secteur]
            
            with col_fourn2:
                # Sélection recommandée automatique
                if st.button("🎯 Sélection Automatique Recommandée", key="dp_selection_auto"):
                    fournisseurs_auto = _select_fournisseurs_recommandes(fournisseurs_filtres, 4)
                    st.session_state.fournisseurs_auto_selected = [f['id'] for f in fournisseurs_auto]
            
            # Multi-sélection des fournisseurs
            fournisseurs_preselected = st.session_state.get('fournisseurs_auto_selected', [])
            
            fournisseurs_selectionnes = st.multiselect(
                "Fournisseurs Invités (3-5 recommandés) *",
                options=[f['id'] for f in fournisseurs_filtres],
                default=fournisseurs_preselected,
                format_func=lambda x: next((f"{f['nom']} - {f['secteur']} - {_get_note_fournisseur(f)}/10" for f in fournisseurs_filtres if f['id'] == x), ""),
                help="Sélectionnez 3 à 5 fournisseurs pour obtenir des prix compétitifs"
            )
            
            # Validation nombre fournisseurs
            nb_fournisseurs = len(fournisseurs_selectionnes)
            if nb_fournisseurs < 2:
                st.warning("⚠️ Il est recommandé de sélectionner au moins 2 fournisseurs pour la concurrence")
            elif nb_fournisseurs > 6:
                st.warning("⚠️ Plus de 6 fournisseurs peut compliquer l'évaluation des offres")
            else:
                st.success(f"✅ {nb_fournisseurs} fournisseur(s) sélectionné(s) - Configuration optimale")
            
            # Affichage des fournisseurs sélectionnés
            if fournisseurs_selectionnes:
                st.markdown("**Fournisseurs sélectionnés pour cette RFQ :**")
                for fourn_id in fournisseurs_selectionnes:
                    fournisseur = next((f for f in fournisseurs_filtres if f['id'] == fourn_id), None)
                    if fournisseur:
                        col_info, col_note = st.columns([3, 1])
                        with col_info:
                            st.text(f"• {fournisseur['nom']} - {fournisseur.get('secteur', 'N/A')}")
                        with col_note:
                            note = _get_note_fournisseur(fournisseur)
                            color = "🟢" if note >= 8 else "🟡" if note >= 6 else "🔴"
                            st.text(f"{color} {note}/10")
        
        # DESCRIPTION ET SPÉCIFICATIONS TECHNIQUES
        st.markdown("##### 📋 Description et Spécifications")
        
        objet_rfq = st.text_input("Objet de la RFQ *", 
            placeholder="Ex: Fourniture matières premières aluminium - Projet XYZ")
        
        description_detaillee = st.text_area("Description Détaillée *", height=120,
            placeholder="Décrivez précisément les produits/services demandés, les spécifications techniques, les quantités, etc.")
        
        # Spécifications techniques
        col_spec1, col_spec2 = st.columns(2)
        with col_spec1:
            specifications_techniques = st.text_area("Spécifications Techniques",
                placeholder="Normes, dimensions, matériaux, certifications requises...")
        
        with col_spec2:
            documents_joints = st.text_area("Documents à Joindre",
                placeholder="Plans, cahier des charges, échantillons...")
            
            livraison_lieu = st.text_input("Lieu de Livraison",
                value="DG Inc. - 123 Rue Industrielle, Montréal")
        
        # ARTICLES À COMMANDER (similaire BA/BC mais pour RFQ)
        st.markdown("##### 📦 Articles/Services Demandés")
        
        # Interface pour saisie des articles
        col_desc, col_qty, col_unit, col_spec, col_delai = st.columns([3, 1, 1, 2, 1])
        with col_desc:
            st.markdown("**Description**")
        with col_qty:
            st.markdown("**Quantité**")
        with col_unit:
            st.markdown("**Unité**")
        with col_spec:
            st.markdown("**Spécifications**")
        with col_delai:
            st.markdown("**Délai Max**")
        
        articles_rfq = []
        for i in range(6):  # 6 lignes pour RFQ
            col_desc, col_qty, col_unit, col_spec, col_delai = st.columns([3, 1, 1, 2, 1])
            
            with col_desc:
                desc = st.text_input("", key=f"rfq_desc_{i}", placeholder="Description article/service")
            with col_qty:
                qty = st.number_input("", min_value=0.0, key=f"rfq_qty_{i}", format="%.2f", step=1.0)
            with col_unit:
                unite = st.selectbox("", ["UN", "KG", "M", "M²", "M³", "L", "H", "SERVICE"], 
                                   key=f"rfq_unit_{i}", index=0)
            with col_spec:
                spec = st.text_input("", key=f"rfq_spec_{i}", placeholder="Spécifications particulières")
            with col_delai:
                delai_max = st.number_input("", min_value=0, key=f"rfq_delai_{i}", value=14, step=1)
            
            if desc and qty > 0:
                articles_rfq.append({
                    'description': desc,
                    'quantite': qty,
                    'unite': unite,
                    'specifications': spec,
                    'delai_maximum': delai_max,
                    'prix_unitaire': 0.0  # Sera rempli par les fournisseurs
                })
        
        # CONDITIONS COMMERCIALES RFQ
        st.markdown("##### 💼 Conditions Commerciales")
        
        col_comm1, col_comm2 = st.columns(2)
        with col_comm1:
            conditions_paiement_souhaitees = st.selectbox("Conditions Paiement Souhaitées",
                ["30 jours net", "45 jours net", "60 jours net", "15 jours net", "À réception"])
            
            garantie_demandee = st.text_input("Garantie Demandée",
                placeholder="Ex: 12 mois pièces et main d'œuvre")
            
            incoterm = st.selectbox("Incoterm", ["DDP", "DAP", "FCA", "EXW", "CIF", "FOB"])
        
        with col_comm2:
            devise_souhaitee = st.selectbox("Devise", ["CAD", "USD", "EUR"])
            
            validite_prix = st.number_input("Validité Prix (jours)", min_value=30, value=60)
            
            penalites_retard = st.text_input("Pénalités Retard",
                placeholder="Ex: 0.5% par jour de retard")
        
        # PROCÉDURE DE RÉPONSE
        st.markdown("##### 📤 Procédure de Réponse")
        
        col_proc1, col_proc2 = st.columns(2)
        with col_proc1:
            format_reponse = st.selectbox("Format de Réponse", 
                ["Email avec devis PDF", "Plateforme en ligne", "Formulaire structuré", "Présentation"])
            
            visite_site = st.checkbox("Visite du Site Requise")
            
            reunion_clarification = st.checkbox("Réunion de Clarification")
        
        with col_proc2:
            remise_echantillons = st.checkbox("Remise d'Échantillons")
            
            demonstration = st.checkbox("Démonstration/Présentation")
            
            contact_technique = st.text_input("Contact Technique",
                placeholder="Nom et coordonnées pour questions techniques")
        
        # Notes et instructions spéciales
        notes_rfq = st.text_area("Notes et Instructions Spéciales", height=80,
            placeholder="Instructions particulières, contexte du projet, contraintes spécifiques...")
        
        # RÉCAPITULATIF DE LA RFQ
        if articles_rfq and fournisseurs_selectionnes and total_ponderation == 100:
            st.markdown(f"""
            <div style='background:#f0f9ff;padding:1rem;border-radius:8px;border-left:4px solid #3b82f6;'>
                <h5 style='color:#1e40af;margin:0;'>📊 Récapitulatif de la RFQ</h5>
                <p style='margin:0.5rem 0 0 0;'><strong>N° RFQ :</strong> {numero_dp}</p>
                <p style='margin:0;'><strong>Fournisseurs invités :</strong> {len(fournisseurs_selectionnes)}</p>
                <p style='margin:0;'><strong>Articles/Services :</strong> {len(articles_rfq)}</p>
                <p style='margin:0;'><strong>Délai réponse :</strong> {delai_reponse} jours</p>
                <p style='margin:0;'><strong>Évaluation :</strong> Prix({ponderation_prix}%), Délai({ponderation_delai}%), Qualité({ponderation_qualite}%)</p>
                <p style='margin:0;'><strong>Date limite :</strong> {date_echeance_reponse.strftime('%d/%m/%Y')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # BOUTONS DE SOUMISSION
        st.markdown("---")
        col_submit1, col_submit2, col_submit3 = st.columns(3)
        
        with col_submit1:
            submit_brouillon = st.form_submit_button("💾 Sauver comme Brouillon", use_container_width=True, key="dp_submit_brouillon")
        with col_submit2:
            submit_valide = st.form_submit_button("✅ Créer et Valider", use_container_width=True, key="dp_submit_valide")
        with col_submit3:
            submit_envoyer = st.form_submit_button("📤 Créer et Envoyer RFQ", use_container_width=True, key="dp_submit_envoyer")
        
        # TRAITEMENT DE LA SOUMISSION
        if submit_brouillon or submit_valide or submit_envoyer:
            # Validation des champs obligatoires
            erreurs = []
            
            if not employe_id:
                erreurs.append("Responsable RFQ obligatoire")
            if not objet_rfq:
                erreurs.append("Objet de la RFQ obligatoire")
            if not description_detaillee:
                erreurs.append("Description détaillée obligatoire")
            if not fournisseurs_selectionnes:
                erreurs.append("Au moins 1 fournisseur doit être sélectionné")
            if len(fournisseurs_selectionnes) < 2 and not submit_brouillon:
                erreurs.append("Au moins 2 fournisseurs recommandés pour RFQ officielle")
            if not articles_rfq:
                erreurs.append("Au moins un article/service doit être ajouté")
            if total_ponderation != 100:
                erreurs.append("Les pondérations doivent totaliser 100%")
            
            if erreurs:
                st.error("❌ Erreurs de validation :")
                for erreur in erreurs:
                    st.error(f"• {erreur}")
            else:
                # Déterminer le statut selon le bouton
                if submit_brouillon:
                    statut = 'BROUILLON'
                elif submit_envoyer:
                    statut = 'ENVOYÉ'
                else:
                    statut = 'VALIDÉ'
                
                # Préparation des données
                data = {
                    'project_id': projet_id,
                    'employee_id': employe_id,
                    'statut': statut,
                    'priorite': priorite,
                    'date_creation': date_creation,
                    'date_echeance': date_echeance_reponse,
                    'montant_total': 0.0,  # Sera calculé quand les offres arrivent
                    'notes': f"Objet: {objet_rfq}\n\nDescription: {description_detaillee}\n\nNotes: {notes_rfq}",
                    
                    # Données spécifiques DP
                    'fournisseurs_invites': fournisseurs_selectionnes,
                    'type_rfq': type_rfq,
                    'delai_reponse': delai_reponse,
                    'mode_evaluation': mode_evaluation,
                    'validite_offre': validite_offre,
                    'conditions_participation': conditions_participation,
                    'langue_reponse': langue_reponse,
                    'criteres_evaluation': criteres_eval,
                    'lignes': articles_rfq,
                    'generer_offres_demo': submit_envoyer  # Générer offres demo si envoyé
                }
                
                # Création du formulaire
                formulaire_id = gestionnaire_dp.creer_demande_prix(data)
                
                if formulaire_id:
                    # Messages de succès personnalisés
                    if submit_envoyer:
                        st.success(f"📤 Demande de Prix {numero_dp} créée et envoyée à {len(fournisseurs_selectionnes)} fournisseur(s)!")
                        st.info("📧 Les fournisseurs ont été notifiés et le suivi des réponses est activé.")
                    else:
                        st.success(f"✅ Demande de Prix {numero_dp} créée avec succès!")
                    
                    # Proposer actions suivantes
                    col_next1, col_next2, col_next3 = st.columns(3)
                    with col_next1:
                        if st.button("📋 Voir la Liste", use_container_width=True, key="dp_voir_liste_apres_creation"):
                            st.session_state.form_action = "list_demande_prix"
                            st.rerun()
                    with col_next2:
                        if st.button("📊 Suivi Réponses", use_container_width=True, key="dp_suivi_apres_creation"):
                            st.session_state.form_action = "compare_offers"
                            st.rerun()
                    with col_next3:
                        if st.button("➕ Créer Autre RFQ", use_container_width=True, key="dp_creer_autre"):
                            st.rerun()
                else:
                    st.error("❌ Erreur lors de la création de la Demande de Prix")

def render_demande_prix_list(gestionnaire_dp):
    """Liste des Demandes de Prix avec filtres avancés."""
    st.markdown("#### 📋 Liste des Demandes de Prix")
    
    demandes_prix = gestionnaire_dp.get_demandes_prix()
    
    if not demandes_prix:
        st.info("Aucune Demande de Prix créée. Lancez votre première RFQ!")
        
        if st.button("➕ Créer Première RFQ", use_container_width=True, key="dp_premiere"):
            st.session_state.form_action = "create_demande_prix"
            st.rerun()
        return
    
    # Métriques rapides
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    
    with col_m1:
        st.metric("💰 Total RFQs", len(demandes_prix))
    with col_m2:
        en_cours = len([dp for dp in demandes_prix if dp['statut'] in ['VALIDÉ', 'ENVOYÉ']])
        st.metric("📤 En Cours", en_cours)
    with col_m3:
        avec_reponses = len([dp for dp in demandes_prix if dp['statut'] in ['APPROUVÉ', 'TERMINÉ']])
        st.metric("📨 Avec Réponses", avec_reponses)
    with col_m4:
        nb_fournisseurs_total = sum(dp.get('nb_fournisseurs_invites', 0) for dp in demandes_prix)
        st.metric("🏢 Fournisseurs Sollicités", nb_fournisseurs_total)
    with col_m5:
        urgentes = len([dp for dp in demandes_prix if dp['priorite'] == 'CRITIQUE'])
        st.metric("🚨 Urgentes", urgentes)
    
    # Filtres
    with st.expander("🔍 Filtres et Recherche", expanded=False):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            filtre_statut = st.multiselect("Statut", gestionnaire_dp.base.statuts, default=gestionnaire_dp.base.statuts)
        with col_f2:
            filtre_priorite = st.multiselect("Priorité", gestionnaire_dp.base.priorites, default=gestionnaire_dp.base.priorites)
        with col_f3:
            filtre_type_rfq = st.multiselect("Type RFQ", ['Tous'] + gestionnaire_dp.types_rfq, default=['Tous'])
        with col_f4:
            recherche = st.text_input("🔍 Rechercher", placeholder="Numéro, objet, responsable...")
    
    # Application des filtres
    demandes_filtrees = []
    for dp in demandes_prix:
        # Filtre statut
        if dp['statut'] not in filtre_statut:
            continue
        
        # Filtre priorité
        if dp['priorite'] not in filtre_priorite:
            continue
        
        # Filtre type RFQ
        if 'Tous' not in filtre_type_rfq:
            infos_rfq = dp.get('infos_rfq', {})
            if infos_rfq.get('type_rfq', 'N/A') not in filtre_type_rfq:
                continue
        
        # Filtre recherche
        if recherche:
            terme = recherche.lower()
            if not any(terme in str(dp.get(field, '')).lower() for field in ['numero_document', 'notes', 'employee_nom']):
                continue
        
        demandes_filtrees.append(dp)
    
    # Affichage résultats
    st.markdown(f"**{len(demandes_filtrees)} Demande(s) de Prix trouvée(s)**")
    
    if demandes_filtrees:
        # Tableau détaillé
        df_data = []
        for dp in demandes_filtrees:
            # Indicateurs visuels
            priorite_icon = {'CRITIQUE': '🔴', 'URGENT': '🟡', 'NORMAL': '🟢'}.get(dp['priorite'], '⚪')
            statut_icon = {
                'BROUILLON': '📝', 'VALIDÉ': '✅', 'ENVOYÉ': '📤', 
                'APPROUVÉ': '👍', 'TERMINÉ': '✔️', 'ANNULÉ': '❌'
            }.get(dp['statut'], '❓')
            
            infos_rfq = dp.get('infos_rfq', {})
            
            df_data.append({
                'N° RFQ': dp['numero_document'],
                'Type': infos_rfq.get('type_rfq', 'N/A'),
                'Responsable': dp.get('employee_nom', 'N/A'),
                'Fournisseurs': f"👥 {dp.get('nb_fournisseurs_invites', 0)}",
                'Statut': f"{statut_icon} {dp['statut']}",
                'Priorité': f"{priorite_icon} {dp['priorite']}",
                'Date Création': dp['date_creation'][:10] if dp['date_creation'] else 'N/A',
                'Échéance': dp.get('date_echeance', 'N/A'),
                'Statut Offres': dp.get('statut_offres', 'N/A'),
                'Délai Rép.': f"{infos_rfq.get('delai_reponse', 'N/A')}j"
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        # Actions en lot
        st.markdown("---")
        st.markdown("##### ⚡ Actions Rapides")
        
        col_action1, col_action2, col_action3, col_action4 = st.columns(4)
        
        with col_action1:
            dp_selectionne = st.selectbox("Sélectionner une RFQ", 
                                        options=[dp['id'] for dp in demandes_filtrees],
                                        format_func=lambda x: next((dp['numero_document'] for dp in demandes_filtrees if dp['id'] == x), ""))
        
        with col_action2:
            if st.button("👁️ Voir Détails", use_container_width=True, key="dp_voir_details"):
                if dp_selectionne:
                    st.session_state.selected_formulaire_id = dp_selectionne
                    st.session_state.show_formulaire_modal = True
        
        with col_action3:
            if st.button("📊 Comparer Offres", use_container_width=True, key="dp_comparer_action"):
                if dp_selectionne:
                    st.session_state.selected_dp_comparison = dp_selectionne
                    st.session_state.form_action = "compare_offers"
                    st.rerun()
        
        with col_action4:
            if st.button("🏆 Sélectionner Gagnant", use_container_width=True, key="dp_select_winner_action"):
                if dp_selectionne:
                    st.session_state.selected_dp_winner = dp_selectionne
                    st.session_state.form_action = "select_winner"
                    st.rerun()
    else:
        st.info("Aucune Demande de Prix ne correspond aux critères de recherche.")

def render_compare_offers(gestionnaire_dp):
    """Interface de comparaison des offres - SPÉCIFICITÉ UNIQUE DP."""
    st.markdown("#### 📊 Comparaison des Offres Multi-Fournisseurs")
    
    # Sélection de la DP à analyser
    dp_selected_id = st.session_state.get('selected_dp_comparison')
    
    demandes_prix = gestionnaire_dp.get_demandes_prix()
    dp_avec_offres = [dp for dp in demandes_prix if dp['statut'] in ['ENVOYÉ', 'APPROUVÉ', 'TERMINÉ']]
    
    if not dp_avec_offres:
        st.info("Aucune Demande de Prix avec des offres à comparer.")
        return
    
    if not dp_selected_id:
        dp_options = [(dp['id'], f"{dp['numero_document']} - {dp.get('notes', '')[:50]}...") for dp in dp_avec_offres]
        dp_selected_id = st.selectbox(
            "Sélectionner la RFQ à analyser",
            options=[dp[0] for dp in dp_options],
            format_func=lambda x: next((dp[1] for dp in dp_options if dp[0] == x), "")
        )
    
    if dp_selected_id:
        # Comparaison automatique des offres
        resultats_comparaison = gestionnaire_dp.comparer_offres(dp_selected_id)
        
        if resultats_comparaison.get('erreur'):
            st.error(f"Erreur: {resultats_comparaison['erreur']}")
            return
        
        # Affichage des résultats
        offres_analysees = resultats_comparaison.get('offres_analysees', [])
        recommandation = resultats_comparaison.get('recommandation', {})
        criteres_utilises = resultats_comparaison.get('criteres_utilises', {})
        
        if offres_analysees:
            # Tableau comparatif
            st.markdown("##### 📋 Tableau Comparatif Automatique")
            
            df_comparison = _create_comparison_dataframe(offres_analysees)
            st.dataframe(df_comparison, use_container_width=True)
            
            # Recommandation automatique
            if recommandation:
                st.markdown("##### 🏆 Recommandation Automatique")
                
                col_rec1, col_rec2 = st.columns([2, 1])
                
                with col_rec1:
                    fournisseur_gagnant = recommandation.get('fournisseur', {})
                    score_final = recommandation.get('score_final', 0)
                    
                    st.success(f"""
                    **🏆 Fournisseur Recommandé : {fournisseur_gagnant.get('nom', 'N/A')}**
                    
                    **Score Final : {score_final:.1f}/100**
                    
                    **Avantages identifiés :**
                    • Prix compétitif : {recommandation.get('prix_total', 0):,.2f}$ CAD
                    • Délai : {recommandation.get('delai_livraison', 0)} jours
                    • Note qualité : {recommandation.get('note_qualite', 0)}/10
                    """)
                
                with col_rec2:
                    # Graphique radar de la meilleure offre
                    fig_radar = _create_radar_chart(recommandation, criteres_utilises)
                    st.plotly_chart(fig_radar, use_container_width=True)
            
            # Graphiques d'analyse
            st.markdown("##### 📊 Analyse Comparative Détaillée")
            
            col_graph1, col_graph2 = st.columns(2)
            
            with col_graph1:
                # Graphique des scores finaux
                noms_fournisseurs = [offre.get('fournisseur', {}).get('nom', 'N/A') for offre in offres_analysees]
                scores_finaux = [offre.get('score_final', 0) for offre in offres_analysees]
                
                fig_scores = px.bar(
                    x=noms_fournisseurs, 
                    y=scores_finaux,
                    title="Scores Finaux par Fournisseur",
                    labels={'x': 'Fournisseurs', 'y': 'Score (/100)'},
                    color=scores_finaux,
                    color_continuous_scale='RdYlGn'
                )
                fig_scores.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig_scores, use_container_width=True)
            
            with col_graph2:
                # Comparaison prix vs délai
                prix_list = [offre.get('prix_total', 0) for offre in offres_analysees]
                delais_list = [offre.get('delai_livraison', 0) for offre in offres_analysees]
                
                fig_scatter = px.scatter(
                    x=prix_list, 
                    y=delais_list,
                    text=noms_fournisseurs,
                    title="Prix vs Délai de Livraison",
                    labels={'x': 'Prix Total ($)', 'y': 'Délai (jours)'},
                    size=[offre.get('note_qualite', 5) for offre in offres_analysees],
                    color=scores_finaux,
                    color_continuous_scale='RdYlGn'
                )
                fig_scatter.update_traces(textposition="top center")
                fig_scatter.update_layout(height=400)
                st.plotly_chart(fig_scatter, use_container_width=True)
            
            # Actions pour sélection
            st.markdown("---")
            st.markdown("##### ⚡ Actions")
            
            col_action1, col_action2, col_action3 = st.columns(3)
            
            with col_action1:
                if st.button("🏆 Sélectionner le Gagnant Recommandé", use_container_width=True, key="select_recommended"):
                    if recommandation:
                        st.session_state.selected_dp_winner = dp_selected_id
                        st.session_state.winner_details = recommandation
                        st.session_state.form_action = "select_winner"
                        st.rerun()
            
            with col_action2:
                fournisseur_manuel = st.selectbox("Ou sélectionner manuellement",
                    options=[offre.get('fournisseur', {}).get('id', 0) for offre in offres_analysees],
                    format_func=lambda x: next((offre.get('fournisseur', {}).get('nom', 'N/A') for offre in offres_analysees if offre.get('fournisseur', {}).get('id') == x), ""))
                
                if st.button("🎯 Sélectionner Manuellement", use_container_width=True, key="select_manual"):
                    offre_selectionnee = next((offre for offre in offres_analysees if offre.get('fournisseur', {}).get('id') == fournisseur_manuel), None)
                    if offre_selectionnee:
                        st.session_state.selected_dp_winner = dp_selected_id
                        st.session_state.winner_details = offre_selectionnee
                        st.session_state.form_action = "select_winner"
                        st.rerun()
            
            with col_action3:
                if st.button("📋 Retour Liste RFQ", use_container_width=True, key="back_to_list"):
                    st.session_state.form_action = "list_demande_prix"
                    st.rerun()

def render_select_winner(gestionnaire_dp):
    """Interface de sélection du gagnant et conversion DP → BC."""
    st.markdown("#### 🏆 Sélection du Fournisseur Gagnant")
    
    # Récupération de la RFQ sélectionnée
    dp_id = st.session_state.get('selected_dp_winner')
    winner_details = st.session_state.get('winner_details')
    
    if not dp_id:
        st.error("Aucune RFQ sélectionnée pour désignation du gagnant.")
        return
    
    dp_details = gestionnaire_dp.base.get_formulaire_details(dp_id)
    
    if not dp_details:
        st.error("RFQ introuvable.")
        return
    
    # Affichage du gagnant sélectionné
    if winner_details:
        st.markdown("##### 🏆 Fournisseur Gagnant Sélectionné")
        
        col_winner1, col_winner2 = st.columns(2)
        with col_winner1:
            fournisseur_gagnant = winner_details.get('fournisseur', {})
            st.success(f"""
            **Fournisseur Gagnant :** {fournisseur_gagnant.get('nom', 'N/A')}
            **Score Final :** {winner_details.get('score_final', 'N/A')}/100
            **Prix Total :** {winner_details.get('prix_total', 0):,.2f}$ CAD
            **Délai Livraison :** {winner_details.get('delai_livraison', 0)} jours
            """)
        
        with col_winner2:
            st.info(f"""
            **Note Qualité :** {winner_details.get('note_qualite', 0)}/10
            **Conditions Paiement :** {winner_details.get('conditions_paiement', 'N/A')}
            **Garantie :** {winner_details.get('garantie', 'N/A')}
            **Distance :** {winner_details.get('proximite_km', 'N/A')} km
            """)
    
    # Formulaire de finalisation
    with st.form("selection_gagnant_form"):
        st.markdown("##### 🔧 Finalisation de la Sélection")
        
        # Justification de la sélection
        justification_selection = st.text_area("Justification de la Sélection *",
            value=_generer_justification_selection_automatique(winner_details) if winner_details else "",
            height=120,
            help="Expliquez pourquoi ce fournisseur a été choisi")
        
        # Conditions négociées finales
        col_neg1, col_neg2 = st.columns(2)
        
        with col_neg1:
            prix_final_negocie = st.number_input("Prix Final Négocié ($)",
                value=winner_details.get('prix_total', 0) if winner_details else 0.0,
                format="%.2f")
            
            delai_final_negocie = st.number_input("Délai Final Négocié (jours)",
                value=winner_details.get('delai_livraison', 14) if winner_details else 14)
        
        with col_neg2:
            conditions_paiement_finales = st.text_input("Conditions Paiement Finales",
                value=winner_details.get('conditions_paiement', '30 jours net') if winner_details else '30 jours net')
            
            garantie_finale = st.text_input("Garantie Finale",
                value=winner_details.get('garantie', '12 mois') if winner_details else '12 mois')
        
        # Conversion automatique en Bon de Commande
        conversion_automatique = st.checkbox("Conversion Automatique en BC", value=True)
        
        # Validation finale
        st.markdown("---")
        confirmation_selection = st.checkbox("Je confirme la sélection de ce fournisseur")
        
        # Boutons de soumission
        col_submit1, col_submit2 = st.columns(2)
        
        with col_submit1:
            submit_selection = st.form_submit_button("🏆 Finaliser Sélection", 
                                                   use_container_width=True, key="finalize_selection")
        
        with col_submit2:
            submit_annuler = st.form_submit_button("❌ Annuler", use_container_width=True, key="cancel_selection")
        
        # Traitement de la soumission
        if submit_selection and confirmation_selection:
            if not justification_selection:
                st.error("❌ La justification de la sélection est obligatoire")
            elif not winner_details:
                st.error("❌ Aucun fournisseur gagnant sélectionné")
            else:
                try:
                    fournisseur_gagnant_id = winner_details.get('fournisseur', {}).get('id')
                    
                    if conversion_automatique:
                        # Sélection avec conversion automatique
                        bc_id = gestionnaire_dp.selectionner_gagnant(dp_id, fournisseur_gagnant_id, justification_selection)
                        
                        if bc_id:
                            st.success(f"""
                            ✅ **Sélection Finalisée avec Succès !**
                            
                            🏆 **Fournisseur Gagnant :** {winner_details.get('fournisseur', {}).get('nom', 'N/A')}
                            💰 **Prix Final :** {prix_final_negocie:,.2f}$ CAD
                            📦 **Bon de Commande :** BC créé automatiquement (ID: {bc_id})
                            📅 **Délai :** {delai_final_negocie} jours
                            """)
                            
                            # Actions suivantes
                            col_next1, col_next2 = st.columns(2)
                            
                            with col_next1:
                                if st.button("📦 Voir BC Créé", use_container_width=True, key="voir_bc_cree"):
                                    st.session_state.selected_formulaire_id = bc_id
                                    st.session_state.show_formulaire_modal = True
                            
                            with col_next2:
                                if st.button("💰 Nouvelles RFQs", use_container_width=True, key="nouvelles_rfq"):
                                    st.session_state.form_action = "list_demande_prix"
                                    st.rerun()
                        else:
                            st.error("❌ Erreur lors de la création du Bon de Commande")
                    else:
                        # Sélection simple sans conversion
                        success = gestionnaire_dp.base.modifier_statut_formulaire(
                            dp_id, 'TERMINÉ', dp_details.get('employee_id'),
                            f"Fournisseur {fournisseur_gagnant_id} sélectionné. {justification_selection}"
                        )
                        
                        if success:
                            st.success("✅ Fournisseur gagnant sélectionné avec succès!")
                        else:
                            st.error("❌ Erreur lors de la sélection")
                        
                except Exception as e:
                    st.error(f"❌ Erreur lors de la finalisation : {e}")
        
        elif submit_annuler:
            st.session_state.form_action = "compare_offers"
            st.rerun()

def render_demande_prix_stats(gestionnaire_dp):
    """Statistiques détaillées des Demandes de Prix."""
    st.markdown("#### 📊 Statistiques Demandes de Prix")
    
    stats = gestionnaire_dp.get_statistiques_demande_prix()
    
    if not stats.get('total', 0):
        st.info("Aucune donnée pour les statistiques.")
        return
    
    # Métriques principales
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("💰 Total RFQs", stats.get('total', 0))
    with col2:
        finalisees = stats.get('dp_terminees', 0)
        st.metric("✅ Finalisées", finalisees)
    with col3:
        en_cours = stats.get('dp_en_cours', 0)
        st.metric("📤 En Cours", en_cours)
    with col4:
        taux_conversion = stats.get('taux_conversion_bc', 0)
        st.metric("🔄 Taux Conversion BC", f"{taux_conversion:.1f}%")
    with col5:
        delai_moyen = stats.get('delai_moyen_reponse', 7)
        st.metric("⏱️ Délai Moyen Réponse", f"{delai_moyen}j")
    
    # Affichage additionnel des statistiques
    if stats.get('top_fournisseurs'):
        st.markdown("##### 🏆 Top Fournisseurs")
        
        for i, fournisseur in enumerate(stats['top_fournisseurs'][:5], 1):
            st.metric(
                f"{i}. {fournisseur.get('nom', 'N/A')[:20]}",
                f"{fournisseur.get('participations', 0)} participations",
                delta=f"Moy: {fournisseur.get('montant_moyen', 0):,.0f}$ CAD"
            )

# =============================================================================
# FONCTIONS UTILITAIRES SPÉCIFIQUES AUX DEMANDES DE PRIX
# =============================================================================

def _select_fournisseurs_recommandes(fournisseurs, nb_max=4):
    """Sélectionne automatiquement les meilleurs fournisseurs."""
    fournisseurs_notes = []
    for f in fournisseurs:
        note = _get_note_fournisseur(f)
        fournisseurs_notes.append((f, note))
    
    # Tri par note décroissante
    fournisseurs_notes.sort(key=lambda x: x[1], reverse=True)
    
    # Sélection avec diversité
    selectionnes = []
    secteurs_vus = set()
    
    for f, note in fournisseurs_notes:
        if len(selectionnes) >= nb_max:
            break
        
        secteur = f.get('secteur', 'N/A')
        # Privilégier la diversité des secteurs
        if secteur not in secteurs_vus or len(selectionnes) < 2:
            selectionnes.append(f)
            secteurs_vus.add(secteur)
    
    # Compléter si pas assez
    for f, note in fournisseurs_notes:
        if len(selectionnes) >= nb_max:
            break
        if f not in selectionnes:
            selectionnes.append(f)
    
    return selectionnes[:nb_max]

def _get_note_fournisseur(fournisseur):
    """Calcule une note fictive pour un fournisseur."""
    import hashlib
    hash_val = int(hashlib.md5(str(fournisseur['id']).encode()).hexdigest()[:8], 16)
    return (hash_val % 5) + 6  # Note entre 6 et 10

def _create_comparison_dataframe(offres_avec_scores):
    """Crée un DataFrame pour l'affichage comparatif."""
    data = []
    
    for offre in offres_avec_scores:
        fournisseur = offre.get('fournisseur', {})
        row = {
            'Fournisseur': fournisseur.get('nom', 'N/A'),
            'Prix Total ($)': f"{offre.get('prix_total', 0):,.2f}",
            'Délai (jours)': offre.get('delai_livraison', 0),
            'Note Qualité (/10)': offre.get('note_qualite', 0),
            'Distance (km)': offre.get('proximite_km', 0),
            'Expérience (/10)': offre.get('experience_secteur', 0),
            'Conforme': '✅' if offre.get('conforme', True) else '❌',
            'Score Final (/100)': f"{offre.get('score_final', 0):.1f}",
            'Conditions': offre.get('conditions_paiement', 'N/A'),
            'Garantie': offre.get('garantie', 'N/A')
        }
        data.append(row)
    
    return pd.DataFrame(data)

def _create_radar_chart(offre, criteres_utilises):
    """Crée un graphique radar pour une offre."""
    categories = []
    values = []
    
    scores_details = offre.get('scores_details', {})
    
    for critere, data in criteres_utilises.items():
        if data.get('actif'):
            categories.append(critere.title())
            score = scores_details.get(critere, 0)
            values.append(score)
    
    if not categories:
        return px.scatter()  # Graphique vide si pas de critères
    
    # Fermer le radar
    categories.append(categories[0])
    values.append(values[0])
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name=offre.get('fournisseur', {}).get('nom', 'N/A'),
        line_color='rgb(32, 201, 151)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=True,
        title=f"Profil {offre.get('fournisseur', {}).get('nom', 'N/A')}",
        height=300
    )
    
    return fig

def _generer_justification_selection_automatique(winner_details):
    """Génère une justification automatique pour la sélection."""
    if not winner_details:
        return ""
    
    fournisseur = winner_details.get('fournisseur', {})
    
    justification = f"""Sélection du fournisseur {fournisseur.get('nom', 'N/A')} basée sur les critères suivants :

SCORE GLOBAL : {winner_details.get('score_final', 0):.1f}/100 - Meilleure offre parmi les candidats

AVANTAGES IDENTIFIÉS :
• Prix proposé : {winner_details.get('prix_total', 0):,.2f}$ CAD
• Délai de livraison : {winner_details.get('delai_livraison', 0)} jours
• Note qualité fournisseur : {winner_details.get('note_qualite', 0)}/10
• Conditions : {winner_details.get('conditions_paiement', 'N/A')}
• Garantie : {winner_details.get('garantie', 'N/A')}

CONFORMITÉ : Offre conforme à toutes les exigences du cahier des charges

Cette sélection optimise le rapport qualité-prix-délai selon les critères pondérés définis dans la RFQ."""
    
    return justification
