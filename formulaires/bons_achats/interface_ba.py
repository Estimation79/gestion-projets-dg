# formulaires/bons_achats/interface_ba.py

"""
Interface utilisateur pour les Bons d'Achats.
Contient tous les composants d'affichage et d'interaction.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .gestionnaire_ba import GestionnaireBonsAchats
from ..utils.helpers import (
    get_fournisseurs_actifs,
    get_employes_actifs,
    get_projets_actifs,
    search_articles_inventaire,
    get_articles_inventaire_critique,
    formater_montant,
    formater_delai,
    generer_couleur_statut,
    generer_couleur_priorite
)

def render_bons_achats_tab(gestionnaire):
    """Interface principale pour les Bons d'Achats."""
    st.markdown("### 🛒 Bons d'Achats")
    
    # Initialiser le gestionnaire spécialisé
    if 'gestionnaire_ba' not in st.session_state:
        st.session_state.gestionnaire_ba = GestionnaireBonsAchats(gestionnaire)
    
    gestionnaire_ba = st.session_state.gestionnaire_ba
    
    # Détection automatique des stocks critiques
    stocks_critiques = get_articles_inventaire_critique()
    if stocks_critiques:
        st.warning(f"⚠️ {len(stocks_critiques)} article(s) en stock critique nécessitent un réapprovisionnement")
        if st.button("📦 Créer BA Automatique", help="Créer un Bon d'Achats pour les stocks critiques"):
            st.session_state.form_action = "create_bon_achat_auto"
            st.session_state.articles_critiques = stocks_critiques
    
    # Actions rapides avec métriques
    _render_actions_rapides_ba(gestionnaire_ba)
    
    # Affichage selon l'action
    action = st.session_state.get('form_action', 'list_bon_achat')
    
    if action == "create_bon_achat":
        render_bon_achat_form(gestionnaire_ba)
    elif action == "create_bon_achat_auto":
        render_bon_achat_form_auto(gestionnaire_ba)
    elif action == "list_bon_achat":
        render_bon_achat_list(gestionnaire_ba)
    elif action == "stats_bon_achat":
        render_bon_achat_stats(gestionnaire_ba)
    elif action == "convert_ba_to_bc":
        render_conversion_ba_bc(gestionnaire_ba)

def _render_actions_rapides_ba(gestionnaire_ba):
    """Actions rapides avec métriques."""
    stats = gestionnaire_ba.get_statistiques_ba()
    
    # Métriques
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        total = stats.get('total', 0)
        st.metric("🛒 Total BAs", total)
    
    with col_m2:
        en_attente = stats.get('ba_urgents', 0)
        st.metric("⏳ Urgents", en_attente)
    
    with col_m3:
        montant_total = stats.get('montant_total', 0)
        st.metric("💰 Montant Total", f"{montant_total:,.0f}$ CAD")
    
    with col_m4:
        taux_conversion = stats.get('taux_conversion_bc', 0)
        st.metric("🔄 Taux Conversion BC", f"{taux_conversion:.1f}%")
    
    # Actions
    col_action1, col_action2, col_action3, col_action4 = st.columns(4)
    
    with col_action1:
        if st.button("➕ Nouveau Bon d'Achats", use_container_width=True, key="ba_nouveau"):
            st.session_state.form_action = "create_bon_achat"
            st.rerun()
    
    with col_action2:
        if st.button("📋 Liste Complète", use_container_width=True, key="ba_liste"):
            st.session_state.form_action = "list_bon_achat"
            st.rerun()
    
    with col_action3:
        if st.button("🔄 Convertir vers BC", use_container_width=True, key="ba_convert"):
            st.session_state.form_action = "convert_ba_to_bc"
            st.rerun()
    
    with col_action4:
        if st.button("📊 Statistiques", use_container_width=True, key="ba_stats"):
            st.session_state.form_action = "stats_bon_achat"
            st.rerun()

def render_bon_achat_form(gestionnaire_ba):
    """Formulaire de création de Bon d'Achats."""
    st.markdown("#### ➕ Nouveau Bon d'Achats")
    
    with st.form("bon_achat_form", clear_on_submit=True):
        # En-tête du formulaire
        col1, col2 = st.columns(2)
        
        with col1:
            numero_ba = gestionnaire_ba.base.generer_numero_document('BON_ACHAT')
            st.text_input("N° Bon d'Achats", value=numero_ba, disabled=True)
            
            # Sélection fournisseur depuis CRM
            fournisseurs = get_fournisseurs_actifs()
            fournisseur_options = [("", "Sélectionner un fournisseur")] + [(f['id'], f"{f['nom']} - {f['secteur']}") for f in fournisseurs]
            fournisseur_id = st.selectbox(
                "Fournisseur *",
                options=[f[0] for f in fournisseur_options],
                format_func=lambda x: next((f[1] for f in fournisseur_options if f[0] == x), "")
            )
            
            date_creation = st.date_input("Date de Création", datetime.now().date())
        
        with col2:
            priorite = st.selectbox("Priorité", gestionnaire_ba.base.priorites, index=0)
            
            # Employé demandeur
            employes = get_employes_actifs()
            employe_options = [("", "Sélectionner un demandeur")] + [(e['id'], f"{e['prenom']} {e['nom']} - {e['poste']}") for e in employes]
            employe_id = st.selectbox(
                "Demandeur *",
                options=[e[0] for e in employe_options],
                format_func=lambda x: next((e[1] for e in employe_options if e[0] == x), "")
            )
            
            date_echeance = st.date_input("Date Souhaitée", datetime.now().date() + timedelta(days=14))
        
        # Description du besoin
        description = st.text_area("Description du Besoin *", height=100, 
                                  placeholder="Décrivez le contexte et la raison de cet achat...")
        
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
        
        # Articles à commander avec recherche inventaire
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
                    # CORRECTION: Suppression du paramètre 'key' pour form_submit_button
                    if st.form_submit_button("➕"):
                        # Logique pour ajouter l'article aux lignes
                        pass
        
        # Interface pour saisie manuelle des articles
        st.markdown("**Saisie manuelle des articles :**")
        
        # Headers
        col_desc, col_qty, col_unit, col_price, col_ref = st.columns([3, 1, 1, 1.5, 1])
        with col_desc:
            st.markdown("**Description**")
        with col_qty:
            st.markdown("**Quantité**")
        with col_unit:
            st.markdown("**Unité**")
        with col_price:
            st.markdown("**Prix Unit. Estimé**")
        with col_ref:
            st.markdown("**Ref. Inv.**")
        
        articles_lines = []
        for i in range(6):
            col_desc, col_qty, col_unit, col_price, col_ref = st.columns([3, 1, 1, 1.5, 1])
            
            with col_desc:
                desc = st.text_input("", key=f"art_desc_{i}", placeholder="Description de l'article")
            with col_qty:
                qty = st.number_input("", min_value=0.0, key=f"art_qty_{i}", format="%.2f", step=1.0)
            with col_unit:
                unite = st.selectbox("", ["UN", "KG", "M", "M²", "M³", "L", "T", "BOÎTE", "SAC"], 
                                   key=f"art_unit_{i}", index=0)
            with col_price:
                prix = st.number_input("", min_value=0.0, key=f"art_price_{i}", format="%.2f", step=0.01)
            with col_ref:
                ref_inv = st.text_input("", key=f"art_ref_{i}", placeholder="ID")
            
            if desc and qty > 0:
                articles_lines.append({
                    'description': desc,
                    'quantite': qty,
                    'unite': unite,
                    'prix_unitaire': prix,
                    'code_article': ref_inv or desc[:10].upper(),
                    'reference_materiau': None
                })
        
        # Justification de l'achat
        justification = st.text_area("Justification de l'Achat *", height=80,
                                   placeholder="Expliquez pourquoi cet achat est nécessaire...")
        
        # Conditions spéciales
        st.markdown("##### 📋 Conditions et Notes")
        
        col_cond1, col_cond2 = st.columns(2)
        with col_cond1:
            livraison_souhaitee = st.text_input("Lieu de Livraison", 
                                              placeholder="Adresse de livraison si différente")
            contact_livraison = st.text_input("Contact Livraison", 
                                            placeholder="Nom et téléphone")
        with col_cond2:
            mode_paiement = st.selectbox("Mode de Paiement Souhaité", 
                                       ["30 jours net", "15 jours net", "À réception", 
                                        "Virement", "Chèque", "À définir"])
            urgence_motif = st.text_input("Motif si Urgent", 
                                        placeholder="Raison de l'urgence")
        
        notes_speciales = st.text_area("Notes Spéciales", height=60,
                                     placeholder="Instructions particulières pour le fournisseur...")
        
        # Approbation budgétaire
        st.markdown("##### 💰 Budget et Approbation")
        col_budget1, col_budget2 = st.columns(2)
        with col_budget1:
            budget_estime = st.number_input("Budget Estimé Total ($)", min_value=0.0, 
                                          value=sum(art['quantite'] * art['prix_unitaire'] for art in articles_lines),
                                          format="%.2f")
            centre_cout = st.text_input("Centre de Coût", placeholder="Code centre de coût")
        with col_budget2:
            approbation_requise = st.checkbox("Approbation Managériale Requise", 
                                            value=budget_estime > 5000)
            if approbation_requise:
                manager_approb = st.selectbox("Manager Approbateur", 
                                            options=[("", "Sélectionner...")] + [(e['id'], f"{e['prenom']} {e['nom']}") for e in employes if 'MANAGER' in e.get('poste', '').upper()],
                                            format_func=lambda x: next((e[1] for e_id, e in [(e['id'], f"{e['prenom']} {e['nom']}") for e in employes] if e_id == x), ""))
            else:
                manager_approb = None
        
        # Récapitulatif des montants
        montant_total_calcule = sum(art['quantite'] * art['prix_unitaire'] for art in articles_lines)
        if montant_total_calcule > 0:
            st.markdown(f"""
            <div style='background:#f0f9ff;padding:1rem;border-radius:8px;border-left:4px solid #3b82f6;'>
                <h5 style='color:#1e40af;margin:0;'>💰 Récapitulatif Financier</h5>
                <p style='margin:0.5rem 0 0 0;'><strong>Montant Total Estimé : {montant_total_calcule:,.2f}$ CAD</strong></p>
                <p style='margin:0;font-size:0.9em;'>Nombre d'articles : {len(articles_lines)}</p>
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
            submit_urgent = st.form_submit_button("🚨 Urgent - Validation Immédiate", use_container_width=True)
        
        # Traitement de la soumission
        if submit_brouillon or submit_valide or submit_urgent:
            # Validation des champs obligatoires
            erreurs = []
            
            if not fournisseur_id:
                erreurs.append("Fournisseur obligatoire")
            if not employe_id:
                erreurs.append("Demandeur obligatoire") 
            if not description:
                erreurs.append("Description du besoin obligatoire")
            if not justification:
                erreurs.append("Justification obligatoire")
            if not articles_lines:
                erreurs.append("Au moins un article doit être ajouté")
            if submit_urgent and priorite != 'CRITIQUE':
                erreurs.append("Les demandes urgentes doivent avoir la priorité CRITIQUE")
            
            if erreurs:
                st.error("❌ Erreurs de validation :")
                for erreur in erreurs:
                    st.error(f"• {erreur}")
            else:
                # Déterminer le statut selon le bouton
                if submit_brouillon:
                    statut = 'BROUILLON'
                elif submit_urgent:
                    statut = 'VALIDÉ'
                    priorite = 'CRITIQUE'
                else:
                    statut = 'VALIDÉ'
                
                # Construction des notes complètes
                notes_completes = f"""=== DESCRIPTION DU BESOIN ===
{description}

=== JUSTIFICATION ===
{justification}

=== CONDITIONS DE LIVRAISON ===
Lieu: {livraison_souhaitee or 'Adresse standard'}
Contact: {contact_livraison or 'À définir'}
Mode paiement: {mode_paiement}

=== INFORMATIONS BUDGÉTAIRES ===
Centre de coût: {centre_cout or 'À définir'}
Budget estimé: {budget_estime:,.2f}$ CAD
Approbation requise: {'Oui' if approbation_requise else 'Non'}

=== NOTES SPÉCIALES ===
{notes_speciales or 'Aucune'}

=== URGENCE ===
{urgence_motif or 'Non urgent'}"""
                
                # Préparation des données
                data = {
                    'company_id': fournisseur_id,
                    'employee_id': employe_id,
                    'project_id': projet_id,
                    'statut': statut,
                    'priorite': priorite,
                    'date_creation': date_creation,
                    'date_echeance': date_echeance,
                    'montant_total': montant_total_calcule,
                    'notes': notes_completes,
                    'lignes': articles_lines,
                    'livraison_lieu': livraison_souhaitee,
                    'livraison_contact': contact_livraison,
                    'mode_paiement': mode_paiement,
                    'centre_cout': centre_cout,
                    'approbation_requise': approbation_requise,
                    'manager_approbateur': manager_approb,
                    'urgence_motif': urgence_motif
                }
                
                # Création du formulaire
                formulaire_id = gestionnaire_ba.creer_bon_achat(data)
                
                if formulaire_id:
                    # Messages de succès personnalisés
                    if submit_urgent:
                        st.success(f"🚨 Bon d'Achats URGENT {numero_ba} créé et marqué pour traitement prioritaire!")
                        st.info("📧 Une notification a été envoyée au service achats pour traitement immédiat.")
                    else:
                        st.success(f"✅ Bon d'Achats {numero_ba} créé avec succès!")
                    
                    # Proposer actions suivantes
                    col_next1, col_next2 = st.columns(2)
                    with col_next1:
                        if st.button("📋 Voir la Liste", use_container_width=True):
                            st.session_state.form_action = "list_bon_achat"
                            st.rerun()
                    with col_next2:
                        if st.button("➕ Créer un Autre", use_container_width=True):
                            st.rerun()
                else:
                    st.error("❌ Erreur lors de la création du Bon d'Achats")

def render_bon_achat_form_auto(gestionnaire_ba):
    """Formulaire de création automatique depuis stocks critiques."""
    st.markdown("#### 📦 Bon d'Achats Automatique - Réapprovisionnement")
    
    stocks_critiques = st.session_state.get('articles_critiques', [])
    
    if not stocks_critiques:
        st.error("Aucun article critique détecté.")
        return
    
    st.info(f"Création automatique d'un Bon d'Achats pour {len(stocks_critiques)} article(s) en stock critique")
    
    # Affichage des articles critiques
    st.markdown("##### 📋 Articles Nécessitant un Réapprovisionnement")
    for article in stocks_critiques:
        with st.expander(f"🔴 {article['nom']} - Stock Critique"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Stock Actuel", article.get('quantite_imperial', 'N/A'))
            with col2:
                st.metric("Stock Minimum", article.get('limite_minimale_imperial', 'N/A'))
            with col3:
                st.metric("À Commander", "À définir")
    
    with st.form("bon_achat_auto_form"):
        # Fournisseur unique pour tous les articles
        fournisseurs = get_fournisseurs_actifs()
        fournisseur_options = [("", "Sélectionner un fournisseur")] + [(f['id'], f"{f['nom']} - {f['secteur']}") for f in fournisseurs]
        fournisseur_id = st.selectbox(
            "Fournisseur pour Réapprovisionnement *",
            options=[f[0] for f in fournisseur_options],
            format_func=lambda x: next((f[1] for f in fournisseur_options if f[0] == x), "")
        )
        
        # Employé demandeur
        employes = get_employes_actifs()
        employe_id = st.selectbox("Demandeur", [e['id'] for e in employes], 
                                format_func=lambda x: next((f"{e['prenom']} {e['nom']}" for e in employes if e['id'] == x), ""))
        
        # ✅ CORRECTION: Séparer le formatage de date
        date_detection = datetime.now().strftime('%d/%m/%Y à %H:%M')
        notes_auto_default = f"Réapprovisionnement automatique de {len(stocks_critiques)} article(s) en stock critique détecté le {date_detection}"
        
        notes_auto = st.text_area("Notes sur le Réapprovisionnement", 
                                value=notes_auto_default)
        
        submit_auto = st.form_submit_button("🚀 Créer Bon d'Achats Automatique", use_container_width=True)
        
        if submit_auto and fournisseur_id:
            formulaire_id = gestionnaire_ba.creer_ba_automatique_stocks_critiques(
                fournisseur_id, employe_id, stocks_critiques, notes_auto
            )
            
            if formulaire_id:
                numero_ba = gestionnaire_ba.base.generer_numero_document('BON_ACHAT')
                st.success(f"✅ Bon d'Achats automatique {numero_ba} créé pour réapprovisionnement!")
                st.session_state.form_action = "list_bon_achat"
                st.rerun()

def render_bon_achat_list(gestionnaire_ba):
    """Liste des Bons d'Achats avec filtres avancés."""
    st.markdown("#### 📋 Liste des Bons d'Achats")
    
    bons_achats = gestionnaire_ba.get_bons_achats()
    
    if not bons_achats:
        st.info("Aucun Bon d'Achats créé. Créez votre premier BA pour commencer!")
        return
    
    # Métriques rapides
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("📋 Total BAs", len(bons_achats))
    with col_m2:
        en_attente = len([ba for ba in bons_achats if ba['statut'] in ['BROUILLON', 'VALIDÉ']])
        st.metric("⏳ En Attente", en_attente)
    with col_m3:
        montant_total = sum(ba.get('montant_total', 0) for ba in bons_achats)
        st.metric("💰 Montant Total", f"{montant_total:,.0f}$")
    with col_m4:
        urgents = len([ba for ba in bons_achats if ba['priorité'] == 'CRITIQUE'])
        st.metric("🚨 Urgents", urgents)
    
    # Filtres
    with st.expander("🔍 Filtres et Recherche", expanded=False):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            filtre_statut = st.multiselect("Statut", gestionnaire_ba.base.statuts, default=gestionnaire_ba.base.statuts)
        with col_f2:
            filtre_priorite = st.multiselect("Priorité", gestionnaire_ba.base.priorites, default=gestionnaire_ba.base.priorites)
        with col_f3:
            fournisseurs_liste = list(set([ba.get('company_nom', 'N/A') for ba in bons_achats if ba.get('company_nom')]))
            filtre_fournisseur = st.multiselect("Fournisseur", ['Tous'] + fournisseurs_liste, default=['Tous'])
        with col_f4:
            filtre_periode = st.selectbox("Période", ["Toutes", "Cette semaine", "Ce mois", "3 derniers mois"])
        
        col_search, col_montant = st.columns(2)
        with col_search:
            recherche = st.text_input("🔍 Rechercher", placeholder="Numéro, fournisseur, description...")
        with col_montant:
            montant_min = st.number_input("Montant minimum ($)", min_value=0.0, value=0.0)
    
    # Application des filtres
    bons_filtres = []
    for ba in bons_achats:
        if ba['statut'] not in filtre_statut:
            continue
        if ba['priorite'] not in filtre_priorite:
            continue
        if 'Tous' not in filtre_fournisseur and ba.get('company_nom', 'N/A') not in filtre_fournisseur:
            continue
        if ba.get('montant_total', 0) < montant_min:
            continue
        if recherche:
            terme = recherche.lower()
            if not any(terme in str(ba.get(field, '')).lower() for field in ['numero_document', 'company_nom', 'notes', 'employee_nom']):
                continue
        bons_filtres.append(ba)
    
    st.markdown(f"**{len(bons_filtres)} Bon(s) d'Achats trouvé(s)**")
    
    if bons_filtres:
        # Tableau détaillé
        df_data = []
        for ba in bons_filtres:
            priorite_icon = {'CRITIQUE': '🔴', 'URGENT': '🟡', 'NORMAL': '🟢'}.get(ba['priorite'], '⚪')
            statut_icon = {'BROUILLON': '📝', 'VALIDÉ': '✅', 'ENVOYÉ': '📤', 'APPROUVÉ': '👍', 'TERMINÉ': '✔️', 'ANNULÉ': '❌'}.get(ba['statut'], '❓')
            
            df_data.append({
                'N° Document': ba['numero_document'],
                'Fournisseur': ba.get('company_nom', 'N/A'),
                'Demandeur': ba.get('employee_nom', 'N/A'),
                'Statut': f"{statut_icon} {ba['statut']}",
                'Priorité': f"{priorite_icon} {ba['priorite']}",
                'Date Création': ba['date_creation'][:10] if ba['date_creation'] else 'N/A',
                'Date Échéance': ba.get('date_echeance', 'N/A'),
                'Montant': f"{ba.get('montant_total', 0):,.2f}$ CAD",
                'Articles': ba.get('nb_articles', 0),
                'Statut Livraison': ba.get('statut_livraison', 'En attente')
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        # Actions en lot
        st.markdown("---")
        st.markdown("##### ⚡ Actions Rapides")
        
        col_action1, col_action2, col_action3, col_action4 = st.columns(4)
        
        with col_action1:
            ba_selectionne = st.selectbox("Sélectionner un BA", 
                                        options=[ba['id'] for ba in bons_filtres],
                                        format_func=lambda x: next((ba['numero_document'] for ba in bons_filtres if ba['id'] == x), ""))
        
        with col_action2:
            if st.button("👁️ Voir Détails", use_container_width=True, key="ba_voir_details"):
                if ba_selectionne:
                    st.session_state.selected_formulaire_id = ba_selectionne
                    st.session_state.show_formulaire_modal = True
        
        with col_action3:
            if st.button("🔄 Convertir → BC", use_container_width=True, key="ba_convertir"):
                if ba_selectionne:
                    result = gestionnaire_ba.convertir_vers_bc(ba_selectionne)
                    if result:
                        st.success(f"✅ BA converti en Bon de Commande {result}")
                        st.rerun()
        
        with col_action4:
            if st.button("✅ Marquer Reçu", use_container_width=True, key="ba_marquer_recu"):
                if ba_selectionne:
                    if gestionnaire_ba.marquer_ba_recu(ba_selectionne, 1):  # TODO: Utiliser employé courant
                        st.success("✅ BA marqué comme reçu!")
                        st.rerun()

def render_bon_achat_stats(gestionnaire_ba):
    """Statistiques détaillées des Bons d'Achats."""
    st.markdown("#### 📊 Statistiques Bons d'Achats")
    
    stats = gestionnaire_ba.get_statistiques_ba()
    
    if not stats or stats.get('total', 0) == 0:
        st.info("Aucune donnée pour les statistiques.")
        return
    
    # Métriques principales
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📋 Total BAs", stats.get('total', 0))
    with col2:
        en_cours = stats.get('total', 0) - stats.get('ba_convertis', 0)
        st.metric("🔄 En Cours", en_cours)
    with col3:
        st.metric("✅ Convertis BC", stats.get('ba_convertis', 0))
    with col4:
        st.metric("💰 Montant Total", f"{stats.get('montant_total', 0):,.0f}$ CAD")
    with col5:
        taux_conversion = stats.get('taux_conversion_bc', 0)
        st.metric("📈 Taux Conversion", f"{taux_conversion:.1f}%")
    
    # Graphiques
    bons_achats = gestionnaire_ba.get_bons_achats()
    
    if len(bons_achats) > 0:
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Répartition par statut
            statut_counts = {}
            for ba in bons_achats:
                statut = ba['statut']
                statut_counts[statut] = statut_counts.get(statut, 0) + 1
            
            if statut_counts:
                colors_statut = {
                    'BROUILLON': '#f59e0b', 'VALIDÉ': '#3b82f6', 'ENVOYÉ': '#8b5cf6',
                    'APPROUVÉ': '#10b981', 'TERMINÉ': '#059669', 'ANNULÉ': '#ef4444'
                }
                fig = px.pie(values=list(statut_counts.values()), names=list(statut_counts.keys()),
                            title="📊 Répartition par Statut", color_discrete_map=colors_statut)
                fig.update_layout(showlegend=True)
                st.plotly_chart(fig, use_container_width=True)
        
        with col_g2:
            # Top fournisseurs
            fournisseur_stats = {}
            for ba in bons_achats:
                fournisseur = ba.get('company_nom', 'N/A')
                if fournisseur not in fournisseur_stats:
                    fournisseur_stats[fournisseur] = {'count': 0, 'montant': 0}
                fournisseur_stats[fournisseur]['count'] += 1
                fournisseur_stats[fournisseur]['montant'] += ba.get('montant_total', 0)
            
            if fournisseur_stats:
                top_fournisseurs = sorted(fournisseur_stats.items(), 
                                        key=lambda x: x[1]['montant'], reverse=True)[:5]
                
                fournisseurs_noms = [f[0] for f in top_fournisseurs]
                fournisseurs_montants = [f[1]['montant'] for f in top_fournisseurs]
                
                fig = px.bar(x=fournisseurs_noms, y=fournisseurs_montants,
                            title="🏆 Top Fournisseurs par Montant")
                fig.update_layout(xaxis_title="Fournisseurs", yaxis_title="Montant ($)")
                st.plotly_chart(fig, use_container_width=True)

def render_conversion_ba_bc(gestionnaire_ba):
    """Interface de conversion Bon d'Achats → Bon de Commande."""
    st.markdown("#### 🔄 Conversion BA → Bon de Commande")
    
    # Récupération des BA convertibles
    bas_convertibles = gestionnaire_ba.get_ba_convertibles()
    
    if not bas_convertibles:
        st.warning("Aucun Bon d'Achats validé disponible pour conversion.")
        return
    
    ba_options = [(ba['id'], f"{ba['numero_document']} - {ba.get('company_nom', 'N/A')} - {ba.get('montant_total', 0):,.0f}$ CAD") for ba in bas_convertibles]
    ba_selectionne = st.selectbox("Sélectionner le BA à convertir", 
                                options=[ba[0] for ba in ba_options],
                                format_func=lambda x: next((ba[1] for ba in ba_options if ba[0] == x), ""))
    
    if ba_selectionne:
        ba_details = next((ba for ba in bas_convertibles if ba['id'] == ba_selectionne), None)
        
        if ba_details:
            # Affichage des détails du BA
            st.markdown("##### 📋 Détails du Bon d'Achats Sélectionné")
            
            col_det1, col_det2 = st.columns(2)
            with col_det1:
                st.info(f"""
                **N° BA :** {ba_details['numero_document']}
                **Fournisseur :** {ba_details.get('company_nom', 'N/A')}
                **Demandeur :** {ba_details.get('employee_nom', 'N/A')}
                **Montant :** {ba_details.get('montant_total', 0):,.2f}$ CAD
                """)
            with col_det2:
                st.info(f"""
                **Statut :** {ba_details['statut']}
                **Priorité :** {ba_details['priorite']}
                **Date Création :** {ba_details['date_creation'][:10] if ba_details['date_creation'] else 'N/A'}
                **Date Échéance :** {ba_details.get('date_echeance', 'N/A')}
                """)
            
            # Interface de conversion simplifiée
            col_conv1, col_conv2 = st.columns(2)
            
            with col_conv1:
                if st.button("🔄 Conversion Rapide", use_container_width=True, 
                           help="Conversion automatique avec paramètres par défaut"):
                    result = gestionnaire_ba.convertir_vers_bc(ba_selectionne)
                    if result:
                        st.success(f"✅ BA converti en Bon de Commande {result}")
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la conversion")
            
            with col_conv2:
                if st.button("⚙️ Conversion Avancée", use_container_width=True,
                           help="Conversion avec paramètres personnalisés"):
                    st.session_state.conversion_avancee_ba_id = ba_selectionne
                    st.info("💡 Fonctionnalité de conversion avancée à implémenter")
    
    # Historique des conversions récentes
    st.markdown("---")
    st.markdown("##### 📊 Conversions Récentes")
    
    # Récupérer les BC créés depuis des BA
    try:
        query = """
            SELECT f.numero_document as bc_numero, f.date_creation,
                   JSON_EXTRACT(f.metadonnees_json, '$.ba_source_numero') as ba_source
            FROM formulaires f
            WHERE f.type_formulaire = 'BON_COMMANDE'
            AND f.metadonnees_json LIKE '%ba_source_id%'
            ORDER BY f.date_creation DESC
            LIMIT 5
        """
        conversions = gestionnaire_ba.db.execute_query(query)
        
        if conversions:
            for conv in conversions:
                st.text(f"✅ {conv.get('ba_source', 'N/A')} → {conv.get('bc_numero', 'N/A')} ({conv.get('date_creation', 'N/A')[:10]})")
        else:
            st.info("Aucune conversion récente.")
            
    except Exception as e:
        st.warning(f"Erreur récupération historique: {e}")
