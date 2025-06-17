# formulaires/bons_commande/interface_bc.py

"""
Interface utilisateur pour les Bons de Commande.
Contient tous les composants d'affichage et d'interaction.
VERSION COMPLÈTE CORRIGÉE - Fix StreamlitMixedNumericTypesError
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .gestionnaire_bc import GestionnaireBonsCommande
from ..utils.helpers import (
    get_fournisseurs_actifs,
    get_employes_actifs,
    get_projets_actifs,
    search_articles_inventaire,
    formater_montant,
    formater_delai,
    generer_couleur_statut,
    generer_couleur_priorite
)

def render_bons_commande_tab(gestionnaire):
    """Interface principale pour les Bons de Commande."""
    st.markdown("### 📦 Bons de Commande")
    
    # Initialiser le gestionnaire spécialisé
    if 'gestionnaire_bc' not in st.session_state:
        st.session_state.gestionnaire_bc = GestionnaireBonsCommande(gestionnaire)
    
    gestionnaire_bc = st.session_state.gestionnaire_bc
    
    # Alerte pour les BA prêts à être convertis
    bas_convertibles = _get_ba_convertibles(gestionnaire)
    if bas_convertibles:
        st.info(f"💡 {len(bas_convertibles)} Bon(s) d'Achats prêt(s) à être convertis en Bons de Commande")
    
    # Actions rapides avec métriques
    _render_actions_rapides_bc(gestionnaire_bc)
    
    # Affichage selon l'action
    action = st.session_state.get('form_action', 'list_bon_commande')
    
    if action == "create_bon_commande":
        render_bon_commande_form(gestionnaire_bc)
    elif action == "list_bon_commande":
        render_bon_commande_list(gestionnaire_bc)
    elif action == "convert_ba_to_bc":
        render_conversion_ba_bc(gestionnaire_bc)
    elif action == "track_deliveries":
        render_delivery_tracking(gestionnaire_bc)
    elif action == "stats_bon_commande":
        render_bon_commande_stats(gestionnaire_bc)
    elif action == "reception_marchandises":
        render_reception_marchandises(gestionnaire_bc)
    elif action == "templates_bon_commande":
        render_templates_bon_commande(gestionnaire_bc)
    elif action == "rapports_bon_commande":
        render_rapports_bon_commande(gestionnaire_bc)

def _get_ba_convertibles(gestionnaire):
    """Récupère les BA prêts à être convertis."""
    try:
        bas = gestionnaire.get_formulaires('BON_ACHAT')
        return [ba for ba in bas if ba['statut'] in ['VALIDÉ', 'APPROUVÉ']]
    except:
        return []

def _render_actions_rapides_bc(gestionnaire_bc):
    """Actions rapides avec métriques."""
    stats = gestionnaire_bc.get_statistiques_bc()
    
    # Métriques
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    
    with col_m1:
        total = stats.get('total', 0)
        st.metric("📦 Total BCs", total)
    
    with col_m2:
        en_cours = stats.get('bc_envoyes', 0)
        st.metric("🔄 En Cours", en_cours)
    
    with col_m3:
        livres = stats.get('bc_livres', 0)
        st.metric("✅ Livrés", livres)
    
    with col_m4:
        montant_total = stats.get('montant_total', 0)
        st.metric("💰 Montant Total", f"{montant_total:,.0f}$ CAD")
    
    with col_m5:
        taux_livraison = stats.get('taux_livraison', 0)
        st.metric("📈 Taux Livraison", f"{taux_livraison:.1f}%")
    
    # Actions principales
    col_action1, col_action2, col_action3, col_action4 = st.columns(4)
    with col_action1:
        if st.button("➕ Nouveau Bon de Commande", use_container_width=True, key="bc_nouveau"):
            st.session_state.form_action = "create_bon_commande"
            st.rerun()
    with col_action2:
        if st.button("📋 Liste Complète", use_container_width=True, key="bc_liste"):
            st.session_state.form_action = "list_bon_commande"
            st.rerun()
    with col_action3:
        if st.button("🔄 Depuis BA", use_container_width=True, key="bc_depuis_ba"):
            st.session_state.form_action = "convert_ba_to_bc"
            st.rerun()
    with col_action4:
        if st.button("📊 Suivi Livraisons", use_container_width=True, key="bc_suivi"):
            st.session_state.form_action = "track_deliveries"
            st.rerun()
    
    # Actions secondaires
    col_action5, col_action6, col_action7, col_action8 = st.columns(4)
    with col_action5:
        if st.button("📊 Statistiques", use_container_width=True, key="bc_stats"):
            st.session_state.form_action = "stats_bon_commande"
            st.rerun()
    with col_action6:
        if st.button("📥 Réception Marchandises", use_container_width=True, key="bc_reception"):
            st.session_state.form_action = "reception_marchandises"
            st.rerun()
    with col_action7:
        if st.button("📋 Templates BC", use_container_width=True, key="bc_templates"):
            st.session_state.form_action = "templates_bon_commande"
            st.rerun()
    with col_action8:
        if st.button("📈 Rapports", use_container_width=True, key="bc_rapports"):
            st.session_state.form_action = "rapports_bon_commande"
            st.rerun()

def render_bon_commande_form(gestionnaire_bc):
    """Formulaire de création de Bon de Commande - VERSION COMPLÈTE CORRIGÉE."""
    st.markdown("#### ➕ Nouveau Bon de Commande")
    
    with st.form("bon_commande_form", clear_on_submit=True):
        # En-tête du formulaire
        col1, col2 = st.columns(2)
        
        with col1:
            numero_bc = gestionnaire_bc.base.generer_numero_document('BON_COMMANDE')
            st.text_input("N° Bon de Commande", value=numero_bc, disabled=True)
            
            # Sélection fournisseur depuis CRM
            fournisseurs = get_fournisseurs_actifs()
            fournisseur_options = [("", "Sélectionner un fournisseur")] + [(f['id'], f"{f['nom']} - {f['secteur']}") for f in fournisseurs]
            fournisseur_id = st.selectbox(
                "Fournisseur *",
                options=[f[0] for f in fournisseur_options],
                format_func=lambda x: next((f[1] for f in fournisseur_options if f[0] == x), "")
            )
            
            date_creation = st.date_input("Date de Commande", datetime.now().date())
        
        with col2:
            priorite = st.selectbox("Priorité", gestionnaire_bc.base.priorites, index=0)
            
            # Employé responsable
            employes = get_employes_actifs()
            employe_options = [("", "Sélectionner un responsable")] + [(e['id'], f"{e['prenom']} {e['nom']} - {e['poste']}") for e in employes]
            employe_id = st.selectbox(
                "Responsable Commande *",
                options=[e[0] for e in employe_options],
                format_func=lambda x: next((e[1] for e in employe_options if e[0] == x), "")
            )
            
            date_livraison_prevue = st.date_input("Date Livraison Prévue", datetime.now().date() + timedelta(days=14))
        
        # Informations de commande
        description = st.text_area("Description de la Commande *", height=100, 
                                  placeholder="Décrivez l'objet de cette commande...")
        
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
        
        # CONDITIONS COMMERCIALES SPÉCIFIQUES BC
        st.markdown("##### 💼 Conditions Commerciales")
        col_comm1, col_comm2 = st.columns(2)
        
        with col_comm1:
            conditions_paiement = st.selectbox("Conditions Paiement *", 
                ["30 jours net", "15 jours net", "À réception", "60 jours net", "Comptant"])
            garantie_exigee = st.text_input("Garantie Exigée",
                placeholder="Ex: 12 mois pièces et main d'œuvre")
            contact_fournisseur = st.text_input("Contact Fournisseur",
                placeholder="Nom et téléphone du contact")
        
        with col_comm2:
            penalites_retard = st.text_input("Pénalités Retard",
                placeholder="Ex: 0.5% par jour de retard")
            # ✅ CORRECTION CRITIQUE: Tous les paramètres sont int
            delai_livraison_max = st.number_input("Délai Max (jours)", min_value=1, value=14, step=1)
            certification_requise = st.text_input("Certifications Requises",
                placeholder="Ex: ISO 9001, CE, CSA...")
        
        # INFORMATIONS LIVRAISON (OBLIGATOIRES POUR BC)
        st.markdown("##### 🚚 Livraison Obligatoire")
        col_liv1, col_liv2 = st.columns(2)
        
        with col_liv1:
            adresse_livraison = st.text_area("Adresse de Livraison *", 
                                           value="DG Inc.\n123 Rue Industrielle\nMontréal, QC H1A 1A1")
            contact_reception = st.text_input("Contact Réception *", 
                                            placeholder="Responsable réception des marchandises")
        
        with col_liv2:
            horaires_livraison = st.text_input("Horaires de Livraison *",
                                             value="Lundi-Vendredi 8h-16h")
            instructions_livraison = st.text_area("Instructions Livraison",
                                                placeholder="Instructions spéciales pour la livraison...")
            transporteur_prefere = st.text_input("Transporteur Préféré",
                                                placeholder="Ex: Purolator, UPS, Camion du fournisseur")
        
        # Articles à commander
        st.markdown("##### 📦 Articles à Commander")
        
        # Interface pour recherche dans l'inventaire
        col_search, col_add = st.columns([3, 1])
        with col_search:
            search_inventaire = st.text_input("🔍 Rechercher dans l'inventaire", 
                                            placeholder="Nom d'article, type...")
        with col_add:
            if st.form_submit_button("🔍 Rechercher", use_container_width=True):
                if search_inventaire:
                    st.session_state.inventaire_search_results = search_articles_inventaire(search_inventaire)
        
        # Affichage des résultats de recherche
        if st.session_state.get('inventaire_search_results'):
            st.markdown("**Résultats de recherche :**")
            for article in st.session_state.inventaire_search_results[:5]:
                col_art, col_stock, col_btn = st.columns([3, 1, 1])
                with col_art:
                    st.text(f"{article['nom']} ({article['type_produit']})")
                with col_stock:
                    st.text(f"Stock: {article.get('quantite_imperial', 'N/A')}")
                with col_btn:
                    if st.form_submit_button("➕"):
                        # Ajouter l'article aux lignes
                        pass
        
        # Interface pour saisie manuelle des articles
        st.markdown("**Saisie des articles à commander :**")
        
        # Headers
        col_desc, col_qty, col_unit, col_price, col_del, col_ref = st.columns([3, 1, 1, 1.5, 1, 1])
        with col_desc:
            st.markdown("**Description**")
        with col_qty:
            st.markdown("**Quantité**")
        with col_unit:
            st.markdown("**Unité**")
        with col_price:
            st.markdown("**Prix Unit.**")
        with col_del:
            st.markdown("**Délai**")
        with col_ref:
            st.markdown("**Ref.**")
        
        articles_lines = []
        for i in range(8):  # 8 lignes pour BC
            col_desc, col_qty, col_unit, col_price, col_del, col_ref = st.columns([3, 1, 1, 1.5, 1, 1])
            
            with col_desc:
                desc = st.text_input("", key=f"bc_art_desc_{i}", placeholder="Description de l'article")
            with col_qty:
                # ✅ CORRECTION CRITIQUE: Tous les paramètres sont float (min_value=0.0, value=0.0, step=1.0)
                qty = st.number_input("", min_value=0.0, value=0.0, key=f"bc_art_qty_{i}", format="%.2f", step=1.0)
            with col_unit:
                unite = st.selectbox("", ["UN", "KG", "M", "M²", "M³", "L", "T", "BOÎTE", "SAC"], 
                                   key=f"bc_art_unit_{i}", index=0)
            with col_price:
                # ✅ CORRECTION CRITIQUE: Tous les paramètres sont float (min_value=0.0, value=0.0, step=0.01)
                prix = st.number_input("", min_value=0.0, value=0.0, key=f"bc_art_price_{i}", format="%.2f", step=0.01)
            with col_del:
                # ✅ CORRECTION CRITIQUE: Tous les paramètres sont int (min_value=0, value=14, step=1)
                delai = st.number_input("", min_value=0, value=14, key=f"bc_art_delai_{i}", step=1)
            with col_ref:
                ref_art = st.text_input("", key=f"bc_art_ref_{i}", placeholder="Réf.")
            
            if desc and qty > 0:
                articles_lines.append({
                    'description': desc,
                    'quantite': qty,
                    'unite': unite,
                    'prix_unitaire': prix,
                    'delai_livraison': delai,
                    'code_article': ref_art or desc[:10].upper(),
                    'reference_materiau': None
                })
        
        # CONDITIONS SPÉCIALES ET CLAUSES
        st.markdown("##### 📋 Conditions Spéciales")
        
        col_spec1, col_spec2 = st.columns(2)
        with col_spec1:
            clause_force_majeure = st.checkbox("Clause Force Majeure", value=True)
            clause_confidentialite = st.checkbox("Clause de Confidentialité")
            acceptation_partielle = st.checkbox("Livraisons Partielles Acceptées", value=True)
        
        with col_spec2:
            inspection_reception = st.checkbox("Inspection à Réception", value=True)
            emballage_special = st.text_input("Exigences Emballage",
                                            placeholder="Ex: Emballage anti-corrosion")
            assurance_transport = st.checkbox("Assurance Transport Requise", value=True)
        
        # Validité et révision
        st.markdown("##### ⏰ Validité de l'Offre")
        col_valid1, col_valid2 = st.columns(2)
        
        with col_valid1:
            # ✅ CORRECTION CRITIQUE: Tous les paramètres sont int (min_value=1, value=30, step=1)
            validite_offre = st.number_input("Validité Offre (jours)", min_value=1, value=30, step=1)
            clause_revision = st.checkbox("Clause de Révision Prix")
        
        with col_valid2:
            devise = st.selectbox("Devise", ["CAD", "USD", "EUR"], index=0)
            taux_change_fixe = st.checkbox("Taux de Change Fixé")
        
        # Notes et instructions
        notes_speciales = st.text_area("Notes et Instructions Spéciales", height=80,
                                     placeholder="Instructions particulières, notes techniques...")
        
        # Approbations et signatures
        st.markdown("##### ✅ Approbations")
        col_approb1, col_approb2 = st.columns(2)
        
        with col_approb1:
            # ✅ CORRECTION CRITIQUE: Calculer le montant total et s'assurer que tous les paramètres sont float
            montant_total_calcule = float(sum(art['quantite'] * art['prix_unitaire'] for art in articles_lines))
            budget_estime = st.number_input("Budget Total ($)", min_value=0.0, 
                                          value=montant_total_calcule,
                                          format="%.2f", step=0.01)
            centre_cout = st.text_input("Centre de Coût", placeholder="Code centre de coût")
        
        with col_approb2:
            approbation_requise = st.checkbox("Approbation Direction", value=budget_estime > 10000.0)
            signature_electronique = st.checkbox("Signature Électronique Requise")
        
        # Récapitulatif financier
        if montant_total_calcule > 0:
            st.markdown(f"""
            <div style='background:#f0f9ff;padding:1rem;border-radius:8px;border-left:4px solid #3b82f6;'>
                <h5 style='color:#1e40af;margin:0;'>💰 Récapitulatif Financier</h5>
                <p style='margin:0.5rem 0 0 0;'><strong>Montant Total : {montant_total_calcule:,.2f} {devise}</strong></p>
                <p style='margin:0;font-size:0.9em;'>Nombre d'articles : {len(articles_lines)}</p>
                <p style='margin:0;font-size:0.9em;'>Conditions : {conditions_paiement}</p>
                <p style='margin:0;font-size:0.9em;'>Livraison prévue : {date_livraison_prevue.strftime('%d/%m/%Y')}</p>
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
            submit_envoyer = st.form_submit_button("📤 Créer et Envoyer", use_container_width=True)
        
        # Traitement de la soumission
        if submit_brouillon or submit_valide or submit_envoyer:
            # Validation des champs obligatoires
            erreurs = []
            
            if not fournisseur_id:
                erreurs.append("Fournisseur obligatoire")
            if not employe_id:
                erreurs.append("Responsable obligatoire") 
            if not description:
                erreurs.append("Description obligatoire")
            if not articles_lines:
                erreurs.append("Au moins un article doit être ajouté")
            if not adresse_livraison:
                erreurs.append("Adresse de livraison obligatoire")
            if not contact_reception:
                erreurs.append("Contact réception obligatoire")
            if not horaires_livraison:
                erreurs.append("Horaires de livraison obligatoires")
            
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
                    'company_id': fournisseur_id,
                    'employee_id': employe_id,
                    'project_id': projet_id,
                    'statut': statut,
                    'priorite': priorite,
                    'date_creation': date_creation,
                    'date_echeance': date_livraison_prevue,
                    'montant_total': montant_total_calcule,
                    'notes': description,
                    'lignes': articles_lines,
                    # Conditions commerciales
                    'conditions_paiement': conditions_paiement,
                    'garantie_exigee': garantie_exigee,
                    'contact_fournisseur': contact_fournisseur,
                    'penalites_retard': penalites_retard,
                    'delai_livraison_max': delai_livraison_max,
                    'certification_requise': certification_requise,
                    # Livraison
                    'adresse_livraison': adresse_livraison,
                    'contact_reception': contact_reception,
                    'horaires_livraison': horaires_livraison,
                    'transporteur_prefere': transporteur_prefere,
                    'instructions_livraison': instructions_livraison,
                    # Clauses
                    'clause_force_majeure': clause_force_majeure,
                    'clause_confidentialite': clause_confidentialite,
                    'acceptation_partielle': acceptation_partielle,
                    'inspection_reception': inspection_reception,
                    'assurance_transport': assurance_transport,
                    # Validité
                    'validite_offre': validite_offre,
                    'devise': devise,
                    'clause_revision': clause_revision,
                    'taux_change_fixe': taux_change_fixe,
                    # Budget
                    'centre_cout': centre_cout,
                    'approbation_requise': approbation_requise,
                    'signature_electronique': signature_electronique,
                    'emballage_special': emballage_special
                }
                
                # Création du formulaire
                formulaire_id = gestionnaire_bc.creer_bon_commande(data)
                
                if formulaire_id:
                    # Messages de succès personnalisés
                    if submit_envoyer:
                        st.success(f"📤 Bon de Commande {numero_bc} créé et envoyé au fournisseur!")
                        st.info("📧 Le BC a été marqué comme ENVOYÉ et un suivi de livraison a été initialisé.")
                    else:
                        st.success(f"✅ Bon de Commande {numero_bc} créé avec succès!")
                    
                    # Affichage du récapitulatif
                    st.markdown(f"""
                    ### 📋 Récapitulatif du Bon de Commande
                    
                    **N° BC :** {numero_bc}  
                    **Fournisseur :** {next((f[1] for f in fournisseur_options if f[0] == fournisseur_id), 'N/A')}  
                    **Montant :** {montant_total_calcule:,.2f} {devise}  
                    **Livraison prévue :** {date_livraison_prevue.strftime('%d/%m/%Y')}  
                    **Articles :** {len(articles_lines)}  
                    **Statut :** {statut}
                    """)
                    
                    # Proposer actions suivantes
                    col_next1, col_next2, col_next3 = st.columns(3)
                    with col_next1:
                        if st.button("📋 Voir la Liste", use_container_width=True, key="bc_voir_liste_apres_creation"):
                            st.session_state.form_action = "list_bon_commande"
                            st.rerun()
                    with col_next2:
                        if st.button("🚚 Suivi Livraison", use_container_width=True, key="bc_suivi_apres_creation"):
                            st.session_state.form_action = "track_deliveries"
                            st.rerun()
                    with col_next3:
                        if st.button("➕ Créer un Autre", use_container_width=True, key="bc_creer_autre"):
                            st.rerun()
                else:
                    st.error("❌ Erreur lors de la création du Bon de Commande")

def render_bon_commande_list(gestionnaire_bc):
    """Liste des Bons de Commande avec filtres avancés."""
    st.markdown("#### 📋 Liste des Bons de Commande")
    
    bons_commande = gestionnaire_bc.get_bons_commande()
    
    if not bons_commande:
        st.info("Aucun Bon de Commande créé. Créez votre premier BC ou convertissez un Bon d'Achats!")
        
        # Proposer actions de démarrage
        col_start1, col_start2 = st.columns(2)
        with col_start1:
            if st.button("➕ Créer Premier BC", use_container_width=True, key="bc_premier"):
                st.session_state.form_action = "create_bon_commande"
                st.rerun()
        with col_start2:
            if st.button("🔄 Convertir depuis BA", use_container_width=True, key="bc_convert_start"):
                st.session_state.form_action = "convert_ba_to_bc"
                st.rerun()
        return
    
    # Métriques rapides
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    with col_m1:
        st.metric("📦 Total BCs", len(bons_commande))
    with col_m2:
        en_cours = len([bc for bc in bons_commande if bc['statut'] in ['VALIDÉ', 'ENVOYÉ']])
        st.metric("🔄 En Cours", en_cours)
    with col_m3:
        livres = len([bc for bc in bons_commande if bc['statut'] == 'TERMINÉ'])
        st.metric("✅ Livrés", livres)
    with col_m4:
        montant_total = sum(bc.get('montant_total', 0) for bc in bons_commande)
        st.metric("💰 Montant Total", f"{montant_total:,.0f}$")
    with col_m5:
        urgents = len([bc for bc in bons_commande if bc['priorite'] == 'CRITIQUE'])
        st.metric("🚨 Urgents", urgents)
    
    # Alertes de livraison
    bcs_en_retard = gestionnaire_bc.get_bc_en_retard()
    if bcs_en_retard:
        st.error(f"🚨 {len(bcs_en_retard)} Bon(s) de Commande en retard de livraison!")
    
    # Filtres avancés
    with st.expander("🔍 Filtres et Recherche", expanded=False):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            filtre_statut = st.multiselect("Statut", gestionnaire_bc.base.statuts, default=gestionnaire_bc.base.statuts)
        with col_f2:
            filtre_priorite = st.multiselect("Priorité", gestionnaire_bc.base.priorites, default=gestionnaire_bc.base.priorites)
        with col_f3:
            # Filtre par fournisseur
            fournisseurs_liste = list(set([bc.get('company_nom', 'N/A') for bc in bons_commande if bc.get('company_nom')]))
            filtre_fournisseur = st.multiselect("Fournisseur", ['Tous'] + fournisseurs_liste, default=['Tous'])
        with col_f4:
            # Filtre par statut livraison
            filtre_livraison = st.selectbox("Statut Livraison", 
                ["Tous", "En attente", "Confirmé", "Expédié", "Livré", "En retard"])
        
        col_search, col_montant, col_date = st.columns(3)
        with col_search:
            recherche = st.text_input("🔍 Rechercher", placeholder="Numéro, fournisseur, description...")
        with col_montant:
            # ✅ CORRECTION: Tous les paramètres sont float
            montant_min = st.number_input("Montant minimum ($)", min_value=0.0, value=0.0, step=0.01)
        with col_date:
            date_depuis = st.date_input("Commandes depuis", value=datetime.now().date() - timedelta(days=90))
    
    # Application des filtres
    bons_filtres = []
    for bc in bons_commande:
        if bc['statut'] not in filtre_statut:
            continue
        if bc['priorite'] not in filtre_priorite:
            continue
        if 'Tous' not in filtre_fournisseur and bc.get('company_nom', 'N/A') not in filtre_fournisseur:
            continue
        if bc.get('montant_total', 0) < montant_min:
            continue
        
        # Filtre date
        try:
            date_bc = datetime.strptime(bc['date_creation'][:10], '%Y-%m-%d').date()
            if date_bc < date_depuis:
                continue
        except:
            pass
        
        # Filtre recherche
        if recherche:
            terme = recherche.lower()
            if not any(terme in str(bc.get(field, '')).lower() for field in ['numero_document', 'company_nom', 'notes', 'employee_nom']):
                continue
        
        bons_filtres.append(bc)
    
    # Affichage résultats
    st.markdown(f"**{len(bons_filtres)} Bon(s) de Commande trouvé(s)**")
    
    if bons_filtres:
        # Tableau détaillé avec indicateurs visuels
        df_data = []
        for bc in bons_filtres:
            # Indicateurs visuels
            priorite_icon = {'CRITIQUE': '🔴', 'URGENT': '🟡', 'NORMAL': '🟢'}.get(bc['priorite'], '⚪')
            statut_icon = {
                'BROUILLON': '📝', 'VALIDÉ': '✅', 'ENVOYÉ': '📤', 
                'APPROUVÉ': '👍', 'TERMINÉ': '✔️', 'ANNULÉ': '❌'
            }.get(bc['statut'], '❓')
            
            # Calcul du statut livraison
            try:
                date_livraison = datetime.strptime(bc['date_echeance'], '%Y-%m-%d').date()
                today = datetime.now().date()
                if bc['statut'] == 'TERMINÉ':
                    livraison_status = "✅ Livré"
                elif date_livraison < today:
                    livraison_status = "🔴 En retard"
                elif (date_livraison - today).days <= 3:
                    livraison_status = "🟡 Imminent"
                else:
                    livraison_status = "🟢 Dans les temps"
            except:
                livraison_status = "❓ Non défini"
            
            df_data.append({
                'N° BC': bc['numero_document'],
                'Fournisseur': bc.get('company_nom', 'N/A'),
                'Responsable': bc.get('employee_nom', 'N/A'),
                'Statut': f"{statut_icon} {bc['statut']}",
                'Priorité': f"{priorite_icon} {bc['priorite']}",
                'Date Commande': bc['date_creation'][:10] if bc['date_creation'] else 'N/A',
                'Livraison Prévue': bc.get('date_echeance', 'N/A'),
                'Statut Livraison': livraison_status,
                'Montant': f"{bc.get('montant_total', 0):,.2f}$ CAD"
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        # Actions en lot
        st.markdown("---")
        st.markdown("##### ⚡ Actions Rapides")
        
        col_action1, col_action2, col_action3, col_action4, col_action5 = st.columns(5)
        
        with col_action1:
            bc_selectionne = st.selectbox("Sélectionner un BC", 
                                        options=[bc['id'] for bc in bons_filtres],
                                        format_func=lambda x: next((bc['numero_document'] for bc in bons_filtres if bc['id'] == x), ""))
        
        with col_action2:
            if st.button("👁️ Voir Détails", use_container_width=True, key="bc_voir_details"):
                if bc_selectionne:
                    st.session_state.selected_formulaire_id = bc_selectionne
                    st.session_state.show_formulaire_modal = True
        
        with col_action3:
            if st.button("📝 Modifier", use_container_width=True, key="bc_modifier"):
                if bc_selectionne:
                    st.session_state.form_action = "edit_bon_commande"
                    st.session_state.edit_formulaire_id = bc_selectionne
        
        with col_action4:
            if st.button("🚚 Suivi Livraison", use_container_width=True, key="bc_suivi_action"):
                if bc_selectionne:
                    st.session_state.selected_bc_livraison = bc_selectionne
                    st.session_state.form_action = "track_deliveries"
                    st.rerun()
        
        with col_action5:
            if st.button("📥 Marquer Reçu", use_container_width=True, key="bc_marquer_recu"):
                if bc_selectionne:
                    if gestionnaire_bc.marquer_bc_recu(bc_selectionne, 1):  # TODO: Utiliser employé courant
                        st.success("✅ BC marqué comme reçu!")
                        st.rerun()
    else:
        st.info("Aucun Bon de Commande ne correspond aux critères de recherche.")

def render_delivery_tracking(gestionnaire_bc):
    """Interface de suivi des livraisons."""
    st.markdown("#### 🚚 Suivi des Livraisons")
    
    # Récupération des livraisons en cours
    livraisons = gestionnaire_bc.get_livraisons_en_cours()
    
    if not livraisons:
        st.info("Aucune livraison en cours de suivi.")
        return
    
    # Métriques de livraison
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        st.metric("📦 Total Livraisons", len(livraisons))
    with col_m2:
        en_attente = len([l for l in livraisons if l['statut_livraison'] in ['EN_ATTENTE', 'CONFIRMÉ']])
        st.metric("⏳ En Attente", en_attente)
    with col_m3:
        en_transit = len([l for l in livraisons if l['statut_livraison'] == 'EXPÉDIÉ'])
        st.metric("🚛 En Transit", en_transit)
    with col_m4:
        livrees = len([l for l in livraisons if l['statut_livraison'] == 'LIVRÉ'])
        st.metric("✅ Livrées", livrees)
    
    # Alertes de retard
    today = datetime.now().date()
    retards = []
    for livraison in livraisons:
        try:
            date_prevue = datetime.strptime(livraison['date_livraison_prevue'], '%Y-%m-%d').date()
            if date_prevue < today and livraison['statut_livraison'] not in ['LIVRÉ', 'ANNULÉ']:
                retards.append(livraison)
        except:
            continue
    
    if retards:
        st.error(f"🚨 {len(retards)} livraison(s) en retard détectée(s)!")
    
    # Interface de suivi principal
    st.markdown("##### 📋 Tableau de Suivi")
    
    # Filtres
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtre_statut_livraison = st.multiselect("Statut Livraison", 
            ['EN_ATTENTE', 'CONFIRMÉ', 'EN_PRODUCTION', 'EXPÉDIÉ', 'LIVRÉ', 'ANNULÉ'],
            default=['EN_ATTENTE', 'CONFIRMÉ', 'EN_PRODUCTION', 'EXPÉDIÉ'])
    with col_f2:
        filtre_fournisseur_suivi = st.selectbox("Fournisseur", 
            ['Tous'] + list(set([l['fournisseur_nom'] for l in livraisons])))
    
    # Application des filtres
    livraisons_filtrees = []
    for livraison in livraisons:
        if livraison['statut_livraison'] in filtre_statut_livraison:
            if filtre_fournisseur_suivi == 'Tous' or livraison['fournisseur_nom'] == filtre_fournisseur_suivi:
                livraisons_filtrees.append(livraison)
    
    # Tableau de suivi
    if livraisons_filtrees:
        for livraison in livraisons_filtrees:
            with st.container():
                col_info, col_statut, col_actions = st.columns([3, 1, 1])
                
                with col_info:
                    try:
                        date_prevue = datetime.strptime(livraison['date_livraison_prevue'], '%Y-%m-%d').date()
                        jours_restants = (date_prevue - today).days
                        
                        if jours_restants < 0:
                            date_info = f"🔴 En retard de {abs(jours_restants)} jour(s)"
                        elif jours_restants <= 2:
                            date_info = f"🟡 Imminent ({jours_restants} jour(s))"
                        else:
                            date_info = f"🟢 Dans {jours_restants} jour(s)"
                    except:
                        date_info = "❓ Date invalide"
                    
                    st.markdown(f"""
                    **BC {livraison['numero_document']}** - {livraison['fournisseur_nom']}
                    - Responsable : {livraison['responsable_nom']}
                    - Livraison prévue : {livraison['date_livraison_prevue']} - {date_info}
                    - Quantité : {livraison.get('quantite_commandee', 'N/A')}
                    """)
                
                with col_statut:
                    # Sélecteur de statut
                    nouveaux_statuts = ['EN_ATTENTE', 'CONFIRMÉ', 'EN_PRODUCTION', 'EXPÉDIÉ', 'LIVRÉ', 'ANNULÉ']
                    statut_actuel = livraison['statut_livraison']
                    
                    nouveau_statut = st.selectbox(
                        f"Statut", 
                        nouveaux_statuts,
                        index=nouveaux_statuts.index(statut_actuel) if statut_actuel in nouveaux_statuts else 0,
                        key=f"statut_{livraison['id']}"
                    )
                
                with col_actions:
                    # Bouton de mise à jour
                    if st.button("💾 Mettre à jour", key=f"update_{livraison['id']}", use_container_width=True):
                        if gestionnaire_bc.mettre_a_jour_statut_livraison(livraison['formulaire_id'], nouveau_statut):
                            st.success(f"✅ Statut mis à jour: {nouveau_statut}")
                            st.rerun()
                
                # Notes de livraison
                if livraison.get('notes_livraison'):
                    st.text(f"📝 Notes: {livraison['notes_livraison']}")
                
                st.markdown("---")

def render_bon_commande_stats(gestionnaire_bc):
    """Statistiques détaillées des Bons de Commande."""
    st.markdown("#### 📊 Statistiques Bons de Commande")
    
    stats = gestionnaire_bc.get_statistiques_bc()
    
    if not stats or stats.get('total', 0) == 0:
        st.info("Aucune donnée pour les statistiques.")
        return
    
    # Métriques principales
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📦 Total BCs", stats.get('total', 0))
    with col2:
        en_cours = stats.get('bc_envoyes', 0)
        st.metric("🔄 En Cours", en_cours)
    with col3:
        termines = stats.get('bc_livres', 0)
        taux_completion = stats.get('taux_livraison', 0)
        st.metric("✅ Livrés", termines, delta=f"{taux_completion:.1f}%")
    with col4:
        st.metric("💰 Montant Total", f"{stats.get('montant_total', 0):,.0f}$ CAD")
    with col5:
        montant_moyen = stats.get('montant_moyen_bc', 0)
        st.metric("📊 Montant Moyen", f"{montant_moyen:,.0f}$ CAD")
    
    # Graphiques
    bons_commande = gestionnaire_bc.get_bons_commande()
    
    if len(bons_commande) > 0:
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Répartition par statut
            statut_counts = {}
            for bc in bons_commande:
                statut = bc['statut']
                statut_counts[statut] = statut_counts.get(statut, 0) + 1
            
            if statut_counts:
                colors_statut = {
                    'BROUILLON': '#f59e0b', 'VALIDÉ': '#3b82f6', 'ENVOYÉ': '#8b5cf6',
                    'APPROUVÉ': '#10b981', 'TERMINÉ': '#059669', 'ANNULÉ': '#ef4444'
                }
                fig = px.pie(values=list(statut_counts.values()), names=list(statut_counts.keys()),
                            title="📊 Répartition par Statut", color_discrete_map=colors_statut)
                fig.update_layout(showlegend=True, height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        with col_g2:
            # Évolution mensuelle
            evolution_mensuelle = {}
            for bc in bons_commande:
                try:
                    mois = bc['date_creation'][:7]  # YYYY-MM
                    evolution_mensuelle[mois] = evolution_mensuelle.get(mois, 0) + 1
                except:
                    continue
            
            if evolution_mensuelle:
                mois_sorted = sorted(evolution_mensuelle.items())[-12:]  # 12 derniers mois
                df_evolution = pd.DataFrame(mois_sorted, columns=['Mois', 'Nombre BCs'])
                
                fig = px.bar(df_evolution, x='Mois', y='Nombre BCs',
                            title="📈 Évolution Mensuelle des BCs")
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
    
    # Alertes et recommandations
    st.markdown("---")
    st.markdown("##### 🚨 Alertes et Recommandations")
    
    alerts = []
    
    # BCs en retard
    bcs_en_retard = gestionnaire_bc.get_bc_en_retard()
    if bcs_en_retard:
        alerts.append(f"🔴 {len(bcs_en_retard)} Bon(s) de Commande en retard de livraison")
    
    # BCs critiques non traités
    critiques_non_traites = [bc for bc in bons_commande 
                            if bc['priorite'] == 'CRITIQUE' and bc['statut'] in ['BROUILLON', 'VALIDÉ']]
    if critiques_non_traites:
        alerts.append(f"🟡 {len(critiques_non_traites)} BC(s) critique(s) non envoyé(s)")
    
    if alerts:
        for alert in alerts:
            st.warning(alert)
    else:
        st.success("✅ Aucune alerte détectée - Gestion des commandes optimale")

def render_conversion_ba_bc(gestionnaire_bc):
    """Interface de conversion Bon d'Achats → Bon de Commande."""
    st.markdown("#### 🔄 Conversion BA → Bon de Commande")
    st.info("💡 Cette fonctionnalité utilise la conversion depuis le module Bons d'Achats")
    
    # Redirection vers la fonction de conversion des BAs
    if st.button("🔄 Aller à la Conversion BA → BC", use_container_width=True):
        st.session_state.form_action = "convert_ba_to_bc"
        st.info("Redirection vers le module Bons d'Achats pour la conversion...")

def render_reception_marchandises(gestionnaire_bc):
    """Interface de réception des marchandises."""
    st.markdown("#### 📥 Réception des Marchandises")
    
    # Récupération des BCs expédiés ou livrés
    livraisons_attendues = gestionnaire_bc.get_livraisons_en_cours()
    livraisons_reception = [l for l in livraisons_attendues if l['statut_livraison'] in ['EXPÉDIÉ', 'LIVRÉ']]
    
    if not livraisons_reception:
        st.info("Aucune livraison en attente de réception.")
        return
    
    st.markdown("##### 📦 Livraisons à Réceptionner")
    
    for livraison in livraisons_reception:
        with st.expander(f"BC {livraison['numero_document']} - {livraison['fournisseur_nom']}", expanded=False):
            col_det1, col_det2, col_action = st.columns([2, 2, 1])
            
            with col_det1:
                st.info(f"""
                **Statut :** {livraison['statut_livraison']}
                **Date prévue :** {livraison['date_livraison_prevue']}
                **Quantité :** {livraison.get('quantite_commandee', 'N/A')}
                """)
            
            with col_det2:
                st.info(f"""
                **Responsable :** {livraison['responsable_nom']}
                **Notes :** {livraison.get('notes_livraison', 'Aucune')}
                """)
            
            with col_action:
                if st.button(f"✅ Marquer Reçu", key=f"reception_{livraison['id']}", use_container_width=True):
                    if gestionnaire_bc.marquer_bc_recu(livraison['formulaire_id'], 1):  # TODO: Utiliser employé courant
                        st.success("✅ Livraison réceptionnée!")
                        st.rerun()

def render_templates_bon_commande(gestionnaire_bc):
    """Interface de gestion des templates de BC."""
    st.markdown("#### 📋 Templates Bons de Commande")
    st.info("🚧 Gestion des templates de BC - Fonctionnalité avancée à développer")
    
    # TODO: Interface pour créer et gérer des templates de BC par industrie/type
    # - Templates standards par secteur (auto, aéro, construction)
    # - Clauses pré-définies
    # - Conditions commerciales par défaut

def render_rapports_bon_commande(gestionnaire_bc):
    """Interface de génération de rapports BC."""
    st.markdown("#### 📈 Rapports Bons de Commande")
    st.info("🚧 Génération de rapports BC - Fonctionnalité avancée à développer")
    
    # TODO: Génération de rapports avancés
    # - Rapport mensuel des achats
    # - Performance fournisseurs
    # - Analyse des coûts
    # - Export Excel/PDF
