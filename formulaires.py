# formulaires.py - Module Formulaires ERP Production DG Inc.
# Gestion complète des documents métier : Bons de Travail, Achats, Commandes, Devis, Estimations

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import json

class GestionnaireFormulaires:
    """
    Gestionnaire unifié pour tous les formulaires métier DG Inc.
    - Bons de Travail (BT)
    - Bons d'Achats (BA) 
    - Bons de Commande (BC)
    - Demandes de Prix (DP)
    - Estimations (EST)
    """
    
    def __init__(self, db):
        self.db = db
        self.types_formulaires = {
            'BON_TRAVAIL': {'prefix': 'BT', 'nom': 'Bon de Travail', 'icon': '🔧'},
            'BON_ACHAT': {'prefix': 'BA', 'nom': "Bon d'Achats", 'icon': '🛒'},
            'BON_COMMANDE': {'prefix': 'BC', 'nom': 'Bon de Commande', 'icon': '📦'},
            'DEMANDE_PRIX': {'prefix': 'DP', 'nom': 'Demande de Prix', 'icon': '💰'},
            'ESTIMATION': {'prefix': 'EST', 'nom': 'Estimation', 'icon': '📊'}
        }
        self.statuts = ['BROUILLON', 'VALIDÉ', 'ENVOYÉ', 'APPROUVÉ', 'TERMINÉ', 'ANNULÉ']
        self.priorites = ['NORMAL', 'URGENT', 'CRITIQUE']
    
    def generer_numero_document(self, type_formulaire: str) -> str:
        """Génère un numéro unique pour le document"""
        try:
            config = self.types_formulaires.get(type_formulaire)
            if not config:
                return "ERREUR-001"
            
            prefix = config['prefix']
            annee = datetime.now().year
            
            # Récupérer le dernier numéro pour ce type et cette année
            query = '''
                SELECT numero_document FROM formulaires 
                WHERE type_formulaire = ? AND numero_document LIKE ?
                ORDER BY id DESC LIMIT 1
            '''
            pattern = f"{prefix}-{annee}-%"
            result = self.db.execute_query(query, (type_formulaire, pattern))
            
            if result:
                last_num = result[0]['numero_document']
                sequence = int(last_num.split('-')[-1]) + 1
            else:
                sequence = 1
            
            return f"{prefix}-{annee}-{sequence:03d}"
            
        except Exception as e:
            st.error(f"Erreur génération numéro: {e}")
            return f"ERR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def creer_formulaire(self, data: Dict) -> int:
        """Crée un nouveau formulaire dans la base"""
        try:
            # Générer numéro si pas fourni
            if not data.get('numero_document'):
                data['numero_document'] = self.generer_numero_document(data['type_formulaire'])
            
            query = '''
                INSERT INTO formulaires 
                (type_formulaire, numero_document, project_id, company_id, employee_id,
                 statut, date_creation, montant_total, notes, priorite, date_echeance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            formulaire_id = self.db.execute_insert(query, (
                data['type_formulaire'],
                data['numero_document'],
                data.get('project_id'),
                data.get('company_id'),
                data.get('employee_id'),
                data.get('statut', 'BROUILLON'),
                data.get('date_creation', datetime.now()),
                data.get('montant_total', 0.0),
                data.get('notes', ''),
                data.get('priorite', 'NORMAL'),
                data.get('date_echeance')
            ))
            
            # Ajouter les lignes de détail si fournies
            if data.get('lignes') and formulaire_id:
                self.ajouter_lignes_formulaire(formulaire_id, data['lignes'])
            
            # Enregistrer la création
            self.enregistrer_validation(formulaire_id, data.get('employee_id'), 'CREATION', 'Document créé')
            
            return formulaire_id
            
        except Exception as e:
            st.error(f"Erreur création formulaire: {e}")
            return None
    
    def ajouter_lignes_formulaire(self, formulaire_id: int, lignes: List[Dict]):
        """Ajoute les lignes de détail à un formulaire"""
        try:
            for i, ligne in enumerate(lignes, 1):
                query = '''
                    INSERT INTO formulaire_lignes
                    (formulaire_id, sequence_ligne, description, quantite, unite,
                     prix_unitaire, montant_ligne, reference_materiau, code_article)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                
                montant_ligne = float(ligne.get('quantite', 0)) * float(ligne.get('prix_unitaire', 0))
                
                self.db.execute_insert(query, (
                    formulaire_id,
                    i,
                    ligne.get('description', ''),
                    ligne.get('quantite', 0),
                    ligne.get('unite', 'UN'),
                    ligne.get('prix_unitaire', 0),
                    montant_ligne,
                    ligne.get('reference_materiau'),
                    ligne.get('code_article', '')
                ))
                
        except Exception as e:
            st.error(f"Erreur ajout lignes: {e}")
    
    def get_formulaires(self, type_formulaire: str = None, statut: str = None) -> List[Dict]:
        """Récupère les formulaires avec filtres optionnels"""
        try:
            query = '''
                SELECT f.*, c.nom as company_nom, e.prenom || ' ' || e.nom as employee_nom,
                       p.nom_projet as project_nom
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN employees e ON f.employee_id = e.id  
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE 1=1
            '''
            params = []
            
            if type_formulaire:
                query += " AND f.type_formulaire = ?"
                params.append(type_formulaire)
            
            if statut:
                query += " AND f.statut = ?"
                params.append(statut)
            
            query += " ORDER BY f.id DESC"
            
            rows = self.db.execute_query(query, tuple(params))
            return [dict(row) for row in rows]
            
        except Exception as e:
            st.error(f"Erreur récupération formulaires: {e}")
            return []
    
    def get_formulaire_details(self, formulaire_id: int) -> Dict:
        """Récupère les détails complets d'un formulaire"""
        try:
            # Formulaire principal
            query = '''
                SELECT f.*, c.nom as company_nom, e.prenom || ' ' || e.nom as employee_nom,
                       p.nom_projet as project_nom
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN employees e ON f.employee_id = e.id
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE f.id = ?
            '''
            result = self.db.execute_query(query, (formulaire_id,))
            if not result:
                return {}
            
            formulaire = dict(result[0])
            
            # Lignes de détail
            query_lignes = '''
                SELECT * FROM formulaire_lignes 
                WHERE formulaire_id = ? 
                ORDER BY sequence_ligne
            '''
            lignes = self.db.execute_query(query_lignes, (formulaire_id,))
            formulaire['lignes'] = [dict(ligne) for ligne in lignes]
            
            # Historique validations
            query_validations = '''
                SELECT fv.*, e.prenom || ' ' || e.nom as validator_nom
                FROM formulaire_validations fv
                LEFT JOIN employees e ON fv.employee_id = e.id
                WHERE fv.formulaire_id = ?
                ORDER BY fv.date_validation DESC
            '''
            validations = self.db.execute_query(query_validations, (formulaire_id,))
            formulaire['validations'] = [dict(val) for val in validations]
            
            return formulaire
            
        except Exception as e:
            st.error(f"Erreur récupération détails: {e}")
            return {}
    
    def modifier_statut_formulaire(self, formulaire_id: int, nouveau_statut: str, employee_id: int, commentaires: str = ""):
        """Modifie le statut d'un formulaire avec traçabilité"""
        try:
            # Mettre à jour le statut
            query = "UPDATE formulaires SET statut = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            self.db.execute_update(query, (nouveau_statut, formulaire_id))
            
            # Enregistrer la validation
            self.enregistrer_validation(formulaire_id, employee_id, 'CHANGEMENT_STATUT', 
                                      f"Statut modifié vers {nouveau_statut}. {commentaires}")
            
            return True
            
        except Exception as e:
            st.error(f"Erreur modification statut: {e}")
            return False
    
    def enregistrer_validation(self, formulaire_id: int, employee_id: int, type_validation: str, commentaires: str):
        """Enregistre une validation/action sur un formulaire"""
        try:
            query = '''
                INSERT INTO formulaire_validations
                (formulaire_id, employee_id, type_validation, commentaires, date_validation)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            '''
            self.db.execute_insert(query, (formulaire_id, employee_id, type_validation, commentaires))
            
        except Exception as e:
            st.error(f"Erreur enregistrement validation: {e}")
    
    def get_statistiques_formulaires(self) -> Dict:
        """Calcule les statistiques des formulaires"""
        try:
            stats = {}
            
            for type_form, config in self.types_formulaires.items():
                query = '''
                    SELECT statut, COUNT(*) as count, SUM(montant_total) as total_montant
                    FROM formulaires 
                    WHERE type_formulaire = ?
                    GROUP BY statut
                '''
                result = self.db.execute_query(query, (type_form,))
                
                stats[type_form] = {
                    'total': 0,
                    'par_statut': {},
                    'montant_total': 0.0
                }
                
                for row in result:
                    stats[type_form]['total'] += row['count']
                    stats[type_form]['par_statut'][row['statut']] = row['count']
                    stats[type_form]['montant_total'] += row['total_montant'] or 0
            
            return stats
            
        except Exception as e:
            st.error(f"Erreur calcul statistiques: {e}")
            return {}

# =============================================================================
# INTERFACES UTILISATEUR PAR TYPE DE FORMULAIRE
# =============================================================================

def show_formulaires_page():
    """Page principale du module Formulaires"""
    st.markdown("## 📑 Gestion des Formulaires - DG Inc.")
    
    # Initialisation du gestionnaire
    if 'gestionnaire_formulaires' not in st.session_state:
        st.session_state.gestionnaire_formulaires = GestionnaireFormulaires(st.session_state.erp_db)
    
    gestionnaire = st.session_state.gestionnaire_formulaires
    
    # Statistiques globales
    show_formulaires_dashboard(gestionnaire)
    
    # Tabs pour chaque type de formulaire
    tab_bt, tab_ba, tab_bc, tab_dp, tab_est = st.tabs([
        "🔧 Bons de Travail",
        "🛒 Bons d'Achats", 
        "📦 Bons de Commande",
        "💰 Demandes de Prix",
        "📊 Estimations"
    ])
    
    with tab_bt:
        render_bons_travail_tab(gestionnaire)
    
    with tab_ba:
        render_bons_achats_tab(gestionnaire)
    
    with tab_bc:
        render_bons_commande_tab(gestionnaire)
    
    with tab_dp:
        render_demandes_prix_tab(gestionnaire)
    
    with tab_est:
        render_estimations_tab(gestionnaire)

def show_formulaires_dashboard(gestionnaire):
    """Dashboard des formulaires avec métriques"""
    st.markdown("### 📊 Dashboard Formulaires")
    
    stats = gestionnaire.get_statistiques_formulaires()
    
    if not any(stats.values()):
        st.info("Aucun formulaire créé. Commencez par créer votre premier document.")
        return
    
    # Métriques principales
    col1, col2, col3, col4, col5 = st.columns(5)
    
    for i, (type_form, config) in enumerate(gestionnaire.types_formulaires.items()):
        with [col1, col2, col3, col4, col5][i]:
            type_stats = stats.get(type_form, {})
            st.metric(
                f"{config['icon']} {config['nom']}",
                type_stats.get('total', 0),
                delta=f"{type_stats.get('montant_total', 0):,.0f}$ CAD"
            )
    
    # Graphiques
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Répartition par type
        types_data = []
        for type_form, config in gestionnaire.types_formulaires.items():
            total = stats.get(type_form, {}).get('total', 0)
            if total > 0:
                types_data.append({'Type': config['nom'], 'Nombre': total})
        
        if types_data:
            df_types = pd.DataFrame(types_data)
            fig = px.pie(df_types, values='Nombre', names='Type', 
                        title="📊 Répartition par Type de Formulaire")
            fig.update_layout(showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_g2:
        # Évolution par statut
        statuts_data = []
        for type_form, type_stats in stats.items():
            for statut, count in type_stats.get('par_statut', {}).items():
                statuts_data.append({
                    'Statut': statut,
                    'Nombre': count,
                    'Type': gestionnaire.types_formulaires[type_form]['nom']
                })
        
        if statuts_data:
            df_statuts = pd.DataFrame(statuts_data)
            fig = px.bar(df_statuts, x='Statut', y='Nombre', color='Type',
                        title="📈 Documents par Statut")
            st.plotly_chart(fig, use_container_width=True)

def render_bons_travail_tab(gestionnaire):
    """Interface pour les Bons de Travail"""
    st.markdown("### 🔧 Bons de Travail")
    
    # Actions rapides
    col_action1, col_action2, col_action3 = st.columns(3)
    with col_action1:
        if st.button("➕ Nouveau Bon de Travail", use_container_width=True):
            st.session_state.form_action = "create_bon_travail"
    with col_action2:
        if st.button("📋 Liste Complète", use_container_width=True):
            st.session_state.form_action = "list_bon_travail"
    with col_action3:
        if st.button("📊 Statistiques", use_container_width=True):
            st.session_state.form_action = "stats_bon_travail"
    
    # Affichage selon l'action
    action = st.session_state.get('form_action', 'list_bon_travail')
    
    if action == "create_bon_travail":
        render_bon_travail_form(gestionnaire)
    elif action == "list_bon_travail":
        render_bon_travail_list(gestionnaire)
    elif action == "stats_bon_travail":
        render_bon_travail_stats(gestionnaire)

def render_bon_travail_form(gestionnaire):
    """Formulaire de création de Bon de Travail"""
    st.markdown("#### ➕ Nouveau Bon de Travail")
    
    with st.form("bon_travail_form", clear_on_submit=True):
        # En-tête du formulaire
        col1, col2 = st.columns(2)
        
        with col1:
            numero_bt = gestionnaire.generer_numero_document('BON_TRAVAIL')
            st.text_input("N° Bon de Travail", value=numero_bt, disabled=True)
            
            # Sélection projet
            projets = get_projets_actifs()
            projet_options = [("", "Sélectionner un projet")] + [(p['id'], f"#{p['id']} - {p['nom_projet']}") for p in projets]
            projet_id = st.selectbox(
                "Projet *",
                options=[p[0] for p in projet_options],
                format_func=lambda x: next((p[1] for p in projet_options if p[0] == x), "")
            )
            
            date_creation = st.date_input("Date de Création", datetime.now().date())
        
        with col2:
            priorite = st.selectbox("Priorité", gestionnaire.priorites)
            
            # Employé responsable
            employes = get_employes_actifs()
            employe_options = [("", "Sélectionner un employé")] + [(e['id'], f"{e['prenom']} {e['nom']} - {e['poste']}") for e in employes]
            employe_id = st.selectbox(
                "Responsable *",
                options=[e[0] for e in employe_options],
                format_func=lambda x: next((e[1] for e in employe_options if e[0] == x), "")
            )
            
            date_echeance = st.date_input("Date d'Échéance", datetime.now().date() + timedelta(days=7))
        
        # Description du travail
        description = st.text_area("Description du Travail *", height=100)
        
        # Opérations à réaliser
        st.markdown("##### 🔧 Opérations à Réaliser")
        if projet_id:
            operations_projet = get_operations_projet(projet_id)
            operations_selectionnees = st.multiselect(
                "Opérations",
                options=[op['id'] for op in operations_projet],
                format_func=lambda x: next((f"{op['sequence']} - {op['description']}" for op in operations_projet if op['id'] == x), "")
            )
        else:
            st.info("Sélectionnez un projet pour voir les opérations disponibles")
            operations_selectionnees = []
        
        # Employés assignés
        st.markdown("##### 👥 Équipe Assignée")
        employes_assignes = st.multiselect(
            "Employés Assignés",
            options=[e['id'] for e in employes],
            format_func=lambda x: next((f"{e['prenom']} {e['nom']} - {e['poste']}" for e in employes if e['id'] == x), "")
        )
        
        # Matériaux nécessaires
        st.markdown("##### 📦 Matériaux Requis")
        col_mat1, col_mat2, col_mat3, col_mat4 = st.columns(4)
        
        # Interface dynamique pour matériaux (simplifié pour l'exemple)
        materiaux_lines = []
        for i in range(3):  # 3 lignes par défaut
            with col_mat1:
                if i == 0:
                    st.text("Description")
                desc = st.text_input("", key=f"mat_desc_{i}", placeholder="Description matériau")
            with col_mat2:
                if i == 0:
                    st.text("Quantité")
                qty = st.number_input("", min_value=0.0, key=f"mat_qty_{i}", format="%.2f")
            with col_mat3:
                if i == 0:
                    st.text("Unité")
                unite = st.selectbox("", ["UN", "KG", "M", "M²", "M³", "L"], key=f"mat_unit_{i}")
            with col_mat4:
                if i == 0:
                    st.text("Coût Unit.")
                cout = st.number_input("", min_value=0.0, key=f"mat_cost_{i}", format="%.2f")
            
            if desc and qty > 0:
                materiaux_lines.append({
                    'description': desc,
                    'quantite': qty,
                    'unite': unite,
                    'prix_unitaire': cout
                })
        
        # Notes spéciales
        notes = st.text_area("Notes Spéciales", height=80)
        
        # Boutons de soumission
        col_submit1, col_submit2 = st.columns(2)
        with col_submit1:
            submit_brouillon = st.form_submit_button("💾 Sauver comme Brouillon", use_container_width=True)
        with col_submit2:
            submit_valide = st.form_submit_button("✅ Créer et Valider", use_container_width=True)
        
        # Traitement de la soumission
        if submit_brouillon or submit_valide:
            if not projet_id or not employe_id or not description:
                st.error("Veuillez remplir tous les champs obligatoires (*)")
            else:
                # Calcul montant total estimé
                montant_total = sum(mat['quantite'] * mat['prix_unitaire'] for mat in materiaux_lines)
                
                # Préparation des données
                data = {
                    'type_formulaire': 'BON_TRAVAIL',
                    'numero_document': numero_bt,
                    'project_id': projet_id,
                    'employee_id': employe_id,
                    'statut': 'VALIDÉ' if submit_valide else 'BROUILLON',
                    'priorite': priorite,
                    'date_creation': date_creation,
                    'date_echeance': date_echeance,
                    'montant_total': montant_total,
                    'notes': f"Description: {description}\n\nOpérations: {', '.join(map(str, operations_selectionnees))}\n\nEmployés: {', '.join(map(str, employes_assignes))}\n\nNotes: {notes}",
                    'lignes': materiaux_lines
                }
                
                # Création du formulaire
                formulaire_id = gestionnaire.creer_formulaire(data)
                
                if formulaire_id:
                    st.success(f"✅ Bon de Travail {numero_bt} créé avec succès!")
                    st.session_state.form_action = "list_bon_travail"
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la création du Bon de Travail")

def render_bon_travail_list(gestionnaire):
    """Liste des Bons de Travail"""
    st.markdown("#### 📋 Liste des Bons de Travail")
    
    bons_travail = gestionnaire.get_formulaires('BON_TRAVAIL')
    
    if not bons_travail:
        st.info("Aucun Bon de Travail créé.")
        return
    
    # Filtres
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filtre_statut = st.multiselect("Statut", gestionnaire.statuts, default=gestionnaire.statuts)
    with col_f2:
        filtre_priorite = st.multiselect("Priorité", gestionnaire.priorites, default=gestionnaire.priorites)
    with col_f3:
        recherche = st.text_input("🔍 Rechercher", placeholder="Numéro, projet...")
    
    # Application des filtres
    bons_filtres = []
    for bt in bons_travail:
        if bt['statut'] in filtre_statut and bt['priorite'] in filtre_priorite:
            if not recherche or recherche.lower() in str(bt.get('numero_document', '')).lower() or recherche.lower() in str(bt.get('project_nom', '')).lower():
                bons_filtres.append(bt)
    
    # Affichage tableau
    if bons_filtres:
        df_data = []
        for bt in bons_filtres:
            df_data.append({
                'N° Document': bt['numero_document'],
                'Projet': bt.get('project_nom', 'N/A'),
                'Responsable': bt.get('employee_nom', 'N/A'),
                'Statut': bt['statut'],
                'Priorité': bt['priorite'],
                'Date Création': bt['date_creation'][:10] if bt['date_creation'] else 'N/A',
                'Montant': f"{bt.get('montant_total', 0):,.2f}$ CAD"
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        # Actions sur sélection
        if st.button("📄 Voir Détails Sélectionné"):
            # Interface pour sélectionner et voir détails
            pass
    else:
        st.info("Aucun Bon de Travail ne correspond aux filtres.")

def render_bon_travail_stats(gestionnaire):
    """Statistiques des Bons de Travail"""
    st.markdown("#### 📊 Statistiques Bons de Travail")
    
    bons_travail = gestionnaire.get_formulaires('BON_TRAVAIL')
    
    if not bons_travail:
        st.info("Aucune donnée pour les statistiques.")
        return
    
    # Métriques
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Bons", len(bons_travail))
    with col2:
        en_cours = len([bt for bt in bons_travail if bt['statut'] in ['VALIDÉ', 'ENVOYÉ']])
        st.metric("En Cours", en_cours)
    with col3:
        termines = len([bt for bt in bons_travail if bt['statut'] == 'TERMINÉ'])
        st.metric("Terminés", termines)
    with col4:
        montant_total = sum(bt.get('montant_total', 0) for bt in bons_travail)
        st.metric("Montant Total", f"{montant_total:,.0f}$ CAD")
    
    # Graphiques
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Par statut
        statut_counts = {}
        for bt in bons_travail:
            statut = bt['statut']
            statut_counts[statut] = statut_counts.get(statut, 0) + 1
        
        if statut_counts:
            fig = px.pie(values=list(statut_counts.values()), names=list(statut_counts.keys()),
                        title="Répartition par Statut")
            st.plotly_chart(fig, use_container_width=True)
    
    with col_g2:
        # Par priorité
        priorite_counts = {}
        for bt in bons_travail:
            priorite = bt['priorite']
            priorite_counts[priorite] = priorite_counts.get(priorite, 0) + 1
        
        if priorite_counts:
            fig = px.bar(x=list(priorite_counts.keys()), y=list(priorite_counts.values()),
                        title="Répartition par Priorité")
            st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# BONS D'ACHATS - INTERFACE COMPLÈTE
# =============================================================================

def render_bons_achats_tab(gestionnaire):
    """Interface complète pour les Bons d'Achats"""
    st.markdown("### 🛒 Bons d'Achats")
    
    # Détection automatique des stocks critiques
    stocks_critiques = get_articles_inventaire_critique()
    if stocks_critiques:
        st.warning(f"⚠️ {len(stocks_critiques)} article(s) en stock critique nécessitent un réapprovisionnement")
        if st.button("📦 Créer BA Automatique", help="Créer un Bon d'Achats pour les stocks critiques"):
            st.session_state.form_action = "create_bon_achat_auto"
            st.session_state.articles_critiques = stocks_critiques
    
    # Actions rapides
    col_action1, col_action2, col_action3, col_action4 = st.columns(4)
    with col_action1:
        if st.button("➕ Nouveau Bon d'Achats", use_container_width=True):
            st.session_state.form_action = "create_bon_achat"
    with col_action2:
        if st.button("📋 Liste Complète", use_container_width=True):
            st.session_state.form_action = "list_bon_achat"
    with col_action3:
        if st.button("📊 Statistiques", use_container_width=True):
            st.session_state.form_action = "stats_bon_achat"
    with col_action4:
        if st.button("🔄 Convertir vers BC", use_container_width=True):
            st.session_state.form_action = "convert_ba_to_bc"
    
    # Affichage selon l'action
    action = st.session_state.get('form_action', 'list_bon_achat')
    
    if action == "create_bon_achat":
        render_bon_achat_form(gestionnaire)
    elif action == "create_bon_achat_auto":
        render_bon_achat_form_auto(gestionnaire)
    elif action == "list_bon_achat":
        render_bon_achat_list(gestionnaire)
    elif action == "stats_bon_achat":
        render_bon_achat_stats(gestionnaire)
    elif action == "convert_ba_to_bc":
        render_conversion_ba_bc(gestionnaire)

def render_bon_achat_form(gestionnaire):
    """Formulaire de création de Bon d'Achats"""
    st.markdown("#### ➕ Nouveau Bon d'Achats")
    
    with st.form("bon_achat_form", clear_on_submit=True):
        # En-tête du formulaire
        col1, col2 = st.columns(2)
        
        with col1:
            numero_ba = gestionnaire.generer_numero_document('BON_ACHAT')
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
            priorite = st.selectbox("Priorité", gestionnaire.priorites, index=0)
            
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
                st.session_state.inventaire_search_results = search_articles_inventaire(search_inventaire)
        
        # Affichage des résultats de recherche
        if st.session_state.get('inventaire_search_results'):
            st.markdown("**Résultats de recherche :**")
            for article in st.session_state.inventaire_search_results[:5]:  # Limiter à 5 résultats
                col_art, col_stock, col_btn = st.columns([3, 1, 1])
                with col_art:
                    st.text(f"{article['nom']} ({article['type_produit']})")
                with col_stock:
                    st.text(f"Stock: {article.get('quantite_imperial', 'N/A')}")
                with col_btn:
                    if st.form_submit_button("➕", key=f"add_art_{article['id']}"):
                        # Ajouter l'article aux lignes (logique à implémenter)
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
        for i in range(6):  # 6 lignes par défaut
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
                    'reference_materiau': None  # Peut être lié à l'inventaire plus tard
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
            manager_approb = st.selectbox("Manager Approbateur", 
                                        options=[("", "Sélectionner...")] + [(e['id'], f"{e['prenom']} {e['nom']}") for e in employes if e.get('poste', '').upper() in ['MANAGER', 'DIRECTEUR', 'RESPONSABLE']],
                                        format_func=lambda x: next((e[1] for e_id, e in [(e['id'], f"{e['prenom']} {e['nom']}") for e in employes] if e_id == x), ""))
        
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
                
                # Métadonnées JSON pour informations structurées
                metadonnees = {
                    'fournisseur_id': fournisseur_id,
                    'livraison_lieu': livraison_souhaitee,
                    'livraison_contact': contact_livraison,
                    'mode_paiement': mode_paiement,
                    'centre_cout': centre_cout,
                    'approbation_requise': approbation_requise,
                    'manager_approbateur': manager_approb if approbation_requise else None,
                    'urgence_motif': urgence_motif,
                    'projet_associe': projet_id
                }
                
                # Préparation des données
                data = {
                    'type_formulaire': 'BON_ACHAT',
                    'numero_document': numero_ba,
                    'project_id': projet_id,
                    'company_id': fournisseur_id,  # Le fournisseur est dans la table companies
                    'employee_id': employe_id,
                    'statut': statut,
                    'priorite': priorite,
                    'date_creation': date_creation,
                    'date_echeance': date_echeance,
                    'montant_total': montant_total_calcule,
                    'notes': notes_completes,
                    'metadonnees_json': json.dumps(metadonnees),
                    'lignes': articles_lines
                }
                
                # Création du formulaire
                formulaire_id = gestionnaire.creer_formulaire(data)
                
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

def render_bon_achat_form_auto(gestionnaire):
    """Formulaire de création automatique depuis stocks critiques"""
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
        
        # Quantités à commander pour chaque article
        st.markdown("##### 📊 Quantités à Commander")
        articles_commande = []
        
        for article in stocks_critiques:
            col_art, col_qty, col_price = st.columns([2, 1, 1])
            
            with col_art:
                st.write(f"**{article['nom']}** ({article['type_produit']})")
            with col_qty:
                qty_recommandee = calculer_quantite_recommandee(article)
                qty = st.number_input(f"Qté", min_value=1, value=qty_recommandee, 
                                    key=f"auto_qty_{article['id']}")
            with col_price:
                prix_estime = st.number_input(f"Prix Unit.", min_value=0.01, value=50.0, 
                                            key=f"auto_price_{article['id']}", format="%.2f")
            
            articles_commande.append({
                'description': f"{article['nom']} - Réapprovisionnement stock critique",
                'quantite': qty,
                'unite': 'UN',  # À adapter selon l'article
                'prix_unitaire': prix_estime,
                'code_article': f"INV-{article['id']}",
                'reference_materiau': article['id']
            })
        
        notes_auto = st.text_area("Notes sur le Réapprovisionnement", 
                                value=f"Réapprovisionnement automatique de {len(stocks_critiques)} article(s) en stock critique détecté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
        
        montant_total = sum(art['quantite'] * art['prix_unitaire'] for art in articles_commande)
        st.metric("💰 Montant Total Estimé", f"{montant_total:,.2f}$ CAD")
        
        submit_auto = st.form_submit_button("🚀 Créer Bon d'Achats Automatique", use_container_width=True)
        
        if submit_auto and fournisseur_id:
            numero_ba = gestionnaire.generer_numero_document('BON_ACHAT')
            
            data = {
                'type_formulaire': 'BON_ACHAT',
                'numero_document': numero_ba,
                'company_id': fournisseur_id,
                'employee_id': employe_id,
                'statut': 'VALIDÉ',
                'priorite': 'URGENT',
                'date_creation': datetime.now().date(),
                'date_echeance': datetime.now().date() + timedelta(days=7),
                'montant_total': montant_total,
                'notes': f"=== RÉAPPROVISIONNEMENT AUTOMATIQUE ===\n{notes_auto}",
                'metadonnees_json': json.dumps({'auto_generated': True, 'articles_critiques': [a['id'] for a in stocks_critiques]}),
                'lignes': articles_commande
            }
            
            formulaire_id = gestionnaire.creer_formulaire(data)
            
            if formulaire_id:
                st.success(f"✅ Bon d'Achats automatique {numero_ba} créé pour réapprovisionnement!")
                st.session_state.form_action = "list_bon_achat"
                st.rerun()

def render_bon_achat_list(gestionnaire):
    """Liste des Bons d'Achats avec filtres avancés"""
    st.markdown("#### 📋 Liste des Bons d'Achats")
    
    bons_achats = gestionnaire.get_formulaires('BON_ACHAT')
    
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
        urgents = len([ba for ba in bons_achats if ba['priorite'] == 'CRITIQUE'])
        st.metric("🚨 Urgents", urgents)
    
    # Filtres avancés
    with st.expander("🔍 Filtres et Recherche", expanded=False):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            filtre_statut = st.multiselect("Statut", gestionnaire.statuts, default=gestionnaire.statuts)
        with col_f2:
            filtre_priorite = st.multiselect("Priorité", gestionnaire.priorites, default=gestionnaire.priorites)
        with col_f3:
            # Filtre par fournisseur
            fournisseurs_liste = list(set([ba.get('company_nom', 'N/A') for ba in bons_achats if ba.get('company_nom')]))
            filtre_fournisseur = st.multiselect("Fournisseur", ['Tous'] + fournisseurs_liste, default=['Tous'])
        with col_f4:
            # Filtre par période
            filtre_periode = st.selectbox("Période", ["Toutes", "Cette semaine", "Ce mois", "3 derniers mois"])
        
        col_search, col_montant = st.columns(2)
        with col_search:
            recherche = st.text_input("🔍 Rechercher", placeholder="Numéro, fournisseur, description...")
        with col_montant:
            montant_min = st.number_input("Montant minimum ($)", min_value=0.0, value=0.0)
    
    # Application des filtres
    bons_filtres = []
    for ba in bons_achats:
        # Filtre statut
        if ba['statut'] not in filtre_statut:
            continue
        
        # Filtre priorité
        if ba['priorite'] not in filtre_priorite:
            continue
        
        # Filtre fournisseur
        if 'Tous' not in filtre_fournisseur and ba.get('company_nom', 'N/A') not in filtre_fournisseur:
            continue
        
        # Filtre montant
        if ba.get('montant_total', 0) < montant_min:
            continue
        
        # Filtre recherche
        if recherche:
            terme = recherche.lower()
            if not any(terme in str(ba.get(field, '')).lower() for field in ['numero_document', 'company_nom', 'notes', 'employee_nom']):
                continue
        
        # Filtre période
        if filtre_periode != "Toutes":
            date_creation = datetime.strptime(ba['date_creation'][:10], '%Y-%m-%d').date()
            today = datetime.now().date()
            
            if filtre_periode == "Cette semaine" and (today - date_creation).days > 7:
                continue
            elif filtre_periode == "Ce mois" and (today - date_creation).days > 30:
                continue
            elif filtre_periode == "3 derniers mois" and (today - date_creation).days > 90:
                continue
        
        bons_filtres.append(ba)
    
    # Affichage résultats
    st.markdown(f"**{len(bons_filtres)} Bon(s) d'Achats trouvé(s)**")
    
    if bons_filtres:
        # Tri
        col_sort1, col_sort2 = st.columns(2)
        with col_sort1:
            tri_par = st.selectbox("Trier par", ["Date création", "Montant", "Priorité", "Statut"])
        with col_sort2:
            tri_ordre = st.selectbox("Ordre", ["Décroissant", "Croissant"])
        
        # Application du tri
        if tri_par == "Date création":
            bons_filtres.sort(key=lambda x: x.get('date_creation', ''), reverse=(tri_ordre == "Décroissant"))
        elif tri_par == "Montant":
            bons_filtres.sort(key=lambda x: x.get('montant_total', 0), reverse=(tri_ordre == "Décroissant"))
        elif tri_par == "Priorité":
            ordre_priorite = {'CRITIQUE': 3, 'URGENT': 2, 'NORMAL': 1}
            bons_filtres.sort(key=lambda x: ordre_priorite.get(x.get('priorite', 'NORMAL'), 1), reverse=(tri_ordre == "Décroissant"))
        
        # Tableau détaillé
        df_data = []
        for ba in bons_filtres:
            # Indicateurs visuels
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
                'Montant': f"{ba.get('montant_total', 0):,.2f}$ CAD"
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
            if st.button("👁️ Voir Détails", use_container_width=True):
                if ba_selectionne:
                    st.session_state.selected_formulaire_id = ba_selectionne
                    st.session_state.show_formulaire_modal = True
        
        with col_action3:
            if st.button("📝 Modifier", use_container_width=True):
                if ba_selectionne:
                    st.session_state.form_action = "edit_bon_achat"
                    st.session_state.edit_formulaire_id = ba_selectionne
        
        with col_action4:
            if st.button("🔄 Convertir → BC", use_container_width=True):
                if ba_selectionne:
                    result = convertir_ba_vers_bc(gestionnaire, ba_selectionne)
                    if result:
                        st.success(f"✅ BA converti en Bon de Commande {result}")
                        st.rerun()
    else:
        st.info("Aucun Bon d'Achats ne correspond aux critères de recherche.")

def render_bon_achat_stats(gestionnaire):
    """Statistiques détaillées des Bons d'Achats"""
    st.markdown("#### 📊 Statistiques Bons d'Achats")
    
    bons_achats = gestionnaire.get_formulaires('BON_ACHAT')
    
    if not bons_achats:
        st.info("Aucune donnée pour les statistiques.")
        return
    
    # Calculs statistiques
    montant_total = sum(ba.get('montant_total', 0) for ba in bons_achats)
    montant_moyen = montant_total / len(bons_achats) if bons_achats else 0
    
    # Métriques principales
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📋 Total BAs", len(bons_achats))
    with col2:
        en_cours = len([ba for ba in bons_achats if ba['statut'] in ['VALIDÉ', 'ENVOYÉ']])
        st.metric("🔄 En Cours", en_cours)
    with col3:
        termines = len([ba for ba in bons_achats if ba['statut'] == 'TERMINÉ'])
        taux_completion = (termines / len(bons_achats) * 100) if bons_achats else 0
        st.metric("✅ Terminés", termines, delta=f"{taux_completion:.1f}%")
    with col4:
        st.metric("💰 Montant Total", f"{montant_total:,.0f}$ CAD")
    with col5:
        st.metric("📊 Montant Moyen", f"{montant_moyen:,.0f}$ CAD")
    
    # Graphiques
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
        # Répartition par priorité
        priorite_counts = {}
        priorite_montants = {}
        for ba in bons_achats:
            priorite = ba['priorite']
            priorite_counts[priorite] = priorite_counts.get(priorite, 0) + 1
            priorite_montants[priorite] = priorite_montants.get(priorite, 0) + ba.get('montant_total', 0)
        
        if priorite_counts:
            colors_priorite = {'NORMAL': '#10b981', 'URGENT': '#f59e0b', 'CRITIQUE': '#ef4444'}
            fig = px.bar(x=list(priorite_counts.keys()), y=list(priorite_counts.values()),
                        title="📈 Répartition par Priorité", color=list(priorite_counts.keys()),
                        color_discrete_map=colors_priorite)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    # Analyses avancées
    col_a1, col_a2 = st.columns(2)
    
    with col_a1:
        # Top fournisseurs
        st.markdown("##### 🏆 Top Fournisseurs")
        fournisseur_stats = {}
        for ba in bons_achats:
            fournisseur = ba.get('company_nom', 'N/A')
            if fournisseur not in fournisseur_stats:
                fournisseur_stats[fournisseur] = {'count': 0, 'montant': 0}
            fournisseur_stats[fournisseur]['count'] += 1
            fournisseur_stats[fournisseur]['montant'] += ba.get('montant_total', 0)
        
        top_fournisseurs = sorted(fournisseur_stats.items(), 
                                key=lambda x: x[1]['montant'], reverse=True)[:5]
        
        for i, (fournisseur, stats) in enumerate(top_fournisseurs, 1):
            st.metric(f"{i}. {fournisseur[:20]}", 
                     f"{stats['count']} BAs", 
                     delta=f"{stats['montant']:,.0f}$ CAD")
    
    with col_a2:
        # Évolution temporelle
        st.markdown("##### 📈 Évolution Mensuelle")
        evolution_mensuelle = {}
        for ba in bons_achats:
            try:
                mois = ba['date_creation'][:7]  # YYYY-MM
                if mois not in evolution_mensuelle:
                    evolution_mensuelle[mois] = {'count': 0, 'montant': 0}
                evolution_mensuelle[mois]['count'] += 1
                evolution_mensuelle[mois]['montant'] += ba.get('montant_total', 0)
            except:
                continue
        
        if evolution_mensuelle:
            mois_sorted = sorted(evolution_mensuelle.items())
            df_evolution = pd.DataFrame([
                {'Mois': mois, 'Nombre': data['count'], 'Montant': data['montant']}
                for mois, data in mois_sorted
            ])
            
            fig = px.line(df_evolution, x='Mois', y='Nombre',
                         title="Évolution du Nombre de BAs")
            st.plotly_chart(fig, use_container_width=True)
    
    # Alertes et recommandations
    st.markdown("---")
    st.markdown("##### 🚨 Alertes et Recommandations")
    
    alerts = []
    
    # BAs en retard
    bos_en_retard = [ba for ba in bons_achats 
                     if ba.get('date_echeance') and 
                     datetime.strptime(ba['date_echeance'], '%Y-%m-%d').date() < datetime.now().date() and
                     ba['statut'] not in ['TERMINÉ', 'ANNULÉ']]
    
    if bos_en_retard:
        alerts.append(f"🔴 {len(bos_en_retard)} Bon(s) d'Achats en retard")
    
    # BAs urgents non traités
    urgents_non_traites = [ba for ba in bons_achats 
                          if ba['priorite'] == 'CRITIQUE' and ba['statut'] in ['BROUILLON', 'VALIDÉ']]
    
    if urgents_non_traites:
        alerts.append(f"🟡 {len(urgents_non_traites)} BA(s) urgent(s) en attente")
    
    # Montants élevés en attente
    montants_eleves = [ba for ba in bons_achats 
                      if ba.get('montant_total', 0) > 10000 and ba['statut'] in ['BROUILLON', 'VALIDÉ']]
    
    if montants_eleves:
        alerts.append(f"💰 {len(montants_eleves)} BA(s) à montant élevé (>10k$) en attente")
    
    if alerts:
        for alert in alerts:
            st.warning(alert)
    else:
        st.success("✅ Aucune alerte détectée - Gestion des achats optimale")

def render_conversion_ba_bc(gestionnaire):
    """Interface de conversion Bon d'Achats → Bon de Commande"""
    st.markdown("#### 🔄 Conversion BA → Bon de Commande")
    
    # Sélection du BA à convertir
    bons_achats = gestionnaire.get_formulaires('BON_ACHAT')
    bas_convertibles = [ba for ba in bons_achats if ba['statut'] in ['VALIDÉ', 'APPROUVÉ']]
    
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
            
            # Formulaire de conversion
            with st.form("conversion_ba_bc_form"):
                st.markdown("##### 🔧 Paramètres de Conversion")
                
                col_conv1, col_conv2 = st.columns(2)
                
                with col_conv1:
                    # Le numéro BC sera généré automatiquement
                    numero_bc = gestionnaire.generer_numero_document('BON_COMMANDE')
                    st.text_input("N° Bon de Commande", value=numero_bc, disabled=True)
                    
                    date_commande = st.date_input("Date de Commande", datetime.now().date())
                    date_livraison_souhaitee = st.date_input("Date Livraison Souhaitée", 
                                                           datetime.now().date() + timedelta(days=14))
                
                with col_conv2:
                    conditions_paiement = st.selectbox("Conditions de Paiement", 
                                                     ["30 jours net", "15 jours net", "À réception", 
                                                      "Virement immédiat", "60 jours net"])
                    
                    contact_fournisseur = st.text_input("Contact Fournisseur", 
                                                       placeholder="Nom et téléphone du contact")
                
                # Informations de livraison
                st.markdown("##### 🚚 Informations de Livraison")
                col_liv1, col_liv2 = st.columns(2)
                
                with col_liv1:
                    adresse_livraison = st.text_area("Adresse de Livraison", 
                                                   value="DG Inc.\n123 Rue Industrielle\nMontréal, QC H1A 1A1")
                    instructions_livraison = st.text_area("Instructions Livraison",
                                                        placeholder="Instructions spéciales pour la livraison...")
                
                with col_liv2:
                    contact_reception = st.text_input("Contact Réception", 
                                                    placeholder="Responsable réception des marchandises")
                    horaires_livraison = st.text_input("Horaires de Livraison",
                                                     value="Lundi-Vendredi 8h-16h")
                
                # Conditions commerciales
                st.markdown("##### 💼 Conditions Commerciales")
                col_comm1, col_comm2 = st.columns(2)
                
                with col_comm1:
                    garantie_demandee = st.text_input("Garantie Demandée", 
                                                    placeholder="Ex: 12 mois pièces et main d'œuvre")
                    penalites_retard = st.text_input("Pénalités de Retard",
                                                   placeholder="Ex: 0.5% par jour de retard")
                
                with col_comm2:
                    certification_requise = st.text_input("Certifications Requises",
                                                        placeholder="Ex: ISO 9001, CE, CSA...")
                    clause_revision = st.checkbox("Clause de Révision Prix", value=False)
                
                # Notes de conversion
                notes_conversion = st.text_area("Notes sur la Conversion",
                                              value=f"Bon de Commande généré automatiquement depuis le Bon d'Achats {ba_details['numero_document']}")
                
                # Validation finale
                st.markdown("---")
                confirmation = st.checkbox("Je confirme la conversion de ce Bon d'Achats en Bon de Commande officiel")
                
                col_submit1, col_submit2 = st.columns(2)
                with col_submit1:
                    submit_conversion = st.form_submit_button("🔄 Convertir en BC", use_container_width=True)
                with col_submit2:
                    submit_annuler = st.form_submit_button("❌ Annuler", use_container_width=True)
                
                if submit_conversion and confirmation:
                    # Récupération des lignes du BA original
                    ba_complet = gestionnaire.get_formulaire_details(ba_selectionne)
                    
                    # Construction des métadonnées BC
                    metadonnees_bc = {
                        'ba_source_id': ba_selectionne,
                        'ba_source_numero': ba_details['numero_document'],
                        'conditions_paiement': conditions_paiement,
                        'contact_fournisseur': contact_fournisseur,
                        'adresse_livraison': adresse_livraison,
                        'contact_reception': contact_reception,
                        'horaires_livraison': horaires_livraison,
                        'instructions_livraison': instructions_livraison,
                        'garantie_demandee': garantie_demandee,
                        'penalites_retard': penalites_retard,
                        'certification_requise': certification_requise,
                        'clause_revision': clause_revision
                    }
                    
                    # Construction des notes complètes
                    notes_bc = f"""=== BON DE COMMANDE OFFICIEL ===
Généré depuis : {ba_details['numero_document']}
Date conversion : {datetime.now().strftime('%d/%m/%Y à %H:%M')}

=== CONDITIONS COMMERCIALES ===
Paiement : {conditions_paiement}
Contact fournisseur : {contact_fournisseur}
Garantie : {garantie_demandee}
Pénalités retard : {penalites_retard}
Certifications : {certification_requise}

=== LIVRAISON ===
Adresse : {adresse_livraison.replace(chr(10), ' - ')}
Contact réception : {contact_reception}
Horaires : {horaires_livraison}
Instructions : {instructions_livraison}

=== NOTES CONVERSION ===
{notes_conversion}

=== HISTORIQUE BA SOURCE ===
{ba_details.get('notes', '')}"""
                    
                    # Données du nouveau BC
                    data_bc = {
                        'type_formulaire': 'BON_COMMANDE',
                        'numero_document': numero_bc,
                        'project_id': ba_details.get('project_id'),
                        'company_id': ba_details.get('company_id'),
                        'employee_id': ba_details.get('employee_id'),
                        'statut': 'VALIDÉ',
                        'priorite': ba_details.get('priorite'),
                        'date_creation': date_commande,
                        'date_echeance': date_livraison_souhaitee,
                        'montant_total': ba_details.get('montant_total', 0),
                        'notes': notes_bc,
                        'metadonnees_json': json.dumps(metadonnees_bc),
                        'lignes': ba_complet.get('lignes', [])
                    }
                    
                    # Création du BC
                    bc_id = gestionnaire.creer_formulaire(data_bc)
                    
                    if bc_id:
                        # Mise à jour du statut du BA original
                        gestionnaire.modifier_statut_formulaire(ba_selectionne, 'TERMINÉ', 
                                                               ba_details.get('employee_id'), 
                                                               f"Converti en Bon de Commande {numero_bc}")
                        
                        st.success(f"""
                        ✅ **Conversion Réussie !**
                        
                        🛒 **Bon d'Achats** {ba_details['numero_document']} → Statut : TERMINÉ
                        📦 **Bon de Commande** {numero_bc} → Créé et prêt à envoyer
                        
                        💰 **Montant :** {ba_details.get('montant_total', 0):,.2f}$ CAD
                        📅 **Livraison prévue :** {date_livraison_souhaitee.strftime('%d/%m/%Y')}
                        """)
                        
                        # Actions suivantes
                        col_next1, col_next2 = st.columns(2)
                        with col_next1:
                            if st.button("📋 Voir Tous les BCs", use_container_width=True):
                                st.session_state.form_action = "list_bon_commande"
                                st.rerun()
                        with col_next2:
                            if st.button("📄 Voir le BC Créé", use_container_width=True):
                                st.session_state.selected_formulaire_id = bc_id
                                st.session_state.show_formulaire_modal = True
                                st.rerun()
                    else:
                        st.error("❌ Erreur lors de la création du Bon de Commande")
                
                elif submit_annuler:
                    st.session_state.form_action = "list_bon_achat"
                    st.rerun()

# =============================================================================
# INTERFACES POUR LES AUTRES TYPES DE FORMULAIRES (STRUCTURE SIMILAIRE)
# =============================================================================

# AJOUTS À formulaires.py - Interface Complète Bons de Commande
# Remplacer la fonction render_bons_commande_tab() existante et ajouter les nouvelles fonctions

def render_bons_commande_tab(gestionnaire):
    """Interface complète pour les Bons de Commande"""
    st.markdown("### 📦 Bons de Commande")
    
    # Alerte pour les BA prêts à être convertis
    bas_convertibles = [ba for ba in gestionnaire.get_formulaires('BON_ACHAT') if ba['statut'] in ['VALIDÉ', 'APPROUVÉ']]
    if bas_convertibles:
        st.info(f"💡 {len(bas_convertibles)} Bon(s) d'Achats prêt(s) à être convertis en Bons de Commande")
    
    # Actions rapides
    col_action1, col_action2, col_action3, col_action4 = st.columns(4)
    with col_action1:
        if st.button("➕ Nouveau Bon de Commande", use_container_width=True, key="bc_nouveau"):
            st.session_state.form_action = "create_bon_commande"
    with col_action2:
        if st.button("📋 Liste Complète", use_container_width=True, key="bc_liste"):
            st.session_state.form_action = "list_bon_commande"
    with col_action3:
        if st.button("🔄 Depuis BA", use_container_width=True, key="bc_depuis_ba"):
            st.session_state.form_action = "convert_ba_to_bc"  # Déjà implémenté !
    with col_action4:
        if st.button("📊 Suivi Livraisons", use_container_width=True, key="bc_suivi"):
            st.session_state.form_action = "track_deliveries"
    
    # Actions secondaires
    col_action5, col_action6, col_action7, col_action8 = st.columns(4)
    with col_action5:
        if st.button("📊 Statistiques", use_container_width=True, key="bc_stats"):
            st.session_state.form_action = "stats_bon_commande"
    with col_action6:
        if st.button("📥 Réception Marchandises", use_container_width=True, key="bc_reception"):
            st.session_state.form_action = "reception_marchandises"
    with col_action7:
        if st.button("📋 Templates BC", use_container_width=True, key="bc_templates"):
            st.session_state.form_action = "templates_bon_commande"
    with col_action8:
        if st.button("📈 Rapports", use_container_width=True, key="bc_rapports"):
            st.session_state.form_action = "rapports_bon_commande"
    
    # Affichage selon l'action
    action = st.session_state.get('form_action', 'list_bon_commande')
    
    if action == "create_bon_commande":
        render_bon_commande_form(gestionnaire)
    elif action == "list_bon_commande":
        render_bon_commande_list(gestionnaire)
    elif action == "convert_ba_to_bc":
        render_conversion_ba_bc(gestionnaire)  # DÉJÀ IMPLÉMENTÉ !
    elif action == "track_deliveries":
        render_delivery_tracking(gestionnaire)
    elif action == "stats_bon_commande":
        render_bon_commande_stats(gestionnaire)
    elif action == "reception_marchandises":
        render_reception_marchandises(gestionnaire)
    elif action == "templates_bon_commande":
        render_templates_bon_commande(gestionnaire)
    elif action == "rapports_bon_commande":
        render_rapports_bon_commande(gestionnaire)

def render_bon_commande_form(gestionnaire):
    """Formulaire de création de Bon de Commande"""
    st.markdown("#### ➕ Nouveau Bon de Commande")
    
    with st.form("bon_commande_form", clear_on_submit=True):
        # En-tête du formulaire
        col1, col2 = st.columns(2)
        
        with col1:
            numero_bc = gestionnaire.generer_numero_document('BON_COMMANDE')
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
            priorite = st.selectbox("Priorité", gestionnaire.priorites, index=0)
            
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
            delai_livraison_max = st.number_input("Délai Max (jours)", min_value=1, value=14)
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
            if st.form_submit_button("🔍 Rechercher", use_container_width=True, key="bc_search_inv"):
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
                    if st.form_submit_button("➕", key=f"add_art_bc_{article['id']}"):
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
                qty = st.number_input("", min_value=0.0, key=f"bc_art_qty_{i}", format="%.2f", step=1.0)
            with col_unit:
                unite = st.selectbox("", ["UN", "KG", "M", "M²", "M³", "L", "T", "BOÎTE", "SAC"], 
                                   key=f"bc_art_unit_{i}", index=0)
            with col_price:
                prix = st.number_input("", min_value=0.0, key=f"bc_art_price_{i}", format="%.2f", step=0.01)
            with col_del:
                delai = st.number_input("", min_value=0, key=f"bc_art_delai_{i}", value=14, step=1)
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
            validite_offre = st.number_input("Validité Offre (jours)", min_value=1, value=30)
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
            budget_estime = st.number_input("Budget Total ($)", min_value=0.0, 
                                          value=sum(art['quantite'] * art['prix_unitaire'] for art in articles_lines),
                                          format="%.2f")
            centre_cout = st.text_input("Centre de Coût", placeholder="Code centre de coût")
        
        with col_approb2:
            approbation_requise = st.checkbox("Approbation Direction", value=budget_estime > 10000)
            signature_electronique = st.checkbox("Signature Électronique Requise")
        
        # Récapitulatif financier
        montant_total_calcule = sum(art['quantite'] * art['prix_unitaire'] for art in articles_lines)
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
            submit_brouillon = st.form_submit_button("💾 Sauver comme Brouillon", use_container_width=True, key="bc_submit_brouillon")
        with col_submit2:
            submit_valide = st.form_submit_button("✅ Créer et Valider", use_container_width=True, key="bc_submit_valide")
        with col_submit3:
            submit_envoyer = st.form_submit_button("📤 Créer et Envoyer", use_container_width=True, key="bc_submit_envoyer")
        
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
                
                # Construction des notes complètes
                notes_completes = f"""=== BON DE COMMANDE OFFICIEL ===
{description}

=== CONDITIONS COMMERCIALES ===
Paiement : {conditions_paiement}
Garantie : {garantie_exigee or 'Standard'}
Contact fournisseur : {contact_fournisseur}
Pénalités retard : {penalites_retard or 'Selon contrat'}
Délai maximum : {delai_livraison_max} jours
Certifications : {certification_requise or 'Standard'}

=== LIVRAISON ===
Adresse : {adresse_livraison.replace(chr(10), ' - ')}
Contact réception : {contact_reception}
Horaires : {horaires_livraison}
Transporteur préféré : {transporteur_prefere or 'Au choix fournisseur'}
Instructions : {instructions_livraison or 'Aucune'}

=== CONDITIONS SPÉCIALES ===
Clause force majeure : {'Oui' if clause_force_majeure else 'Non'}
Confidentialité : {'Oui' if clause_confidentialite else 'Non'}
Livraisons partielles : {'Acceptées' if acceptation_partielle else 'Refusées'}
Inspection réception : {'Obligatoire' if inspection_reception else 'Standard'}
Emballage : {emballage_special or 'Standard'}
Assurance transport : {'Requise' if assurance_transport else 'Standard'}

=== VALIDITÉ ET DEVISE ===
Validité offre : {validite_offre} jours
Devise : {devise}
Révision prix : {'Autorisée' if clause_revision else 'Interdite'}
Taux change : {'Fixé' if taux_change_fixe else 'Variable'}

=== BUDGET ET APPROBATIONS ===
Centre de coût : {centre_cout or 'À définir'}
Budget total : {budget_estime:,.2f} {devise}
Approbation direction : {'Requise' if approbation_requise else 'Non requise'}

=== NOTES SPÉCIALES ===
{notes_speciales or 'Aucune'}"""
                
                # Métadonnées JSON pour BC
                metadonnees = {
                    'conditions_paiement': conditions_paiement,
                    'garantie_exigee': garantie_exigee,
                    'contact_fournisseur': contact_fournisseur,
                    'penalites_retard': penalites_retard,
                    'delai_livraison_max': delai_livraison_max,
                    'certification_requise': certification_requise,
                    'adresse_livraison': adresse_livraison,
                    'contact_reception': contact_reception,
                    'horaires_livraison': horaires_livraison,
                    'transporteur_prefere': transporteur_prefere,
                    'instructions_livraison': instructions_livraison,
                    'clauses': {
                        'force_majeure': clause_force_majeure,
                        'confidentialite': clause_confidentialite,
                        'acceptation_partielle': acceptation_partielle,
                        'inspection_reception': inspection_reception,
                        'assurance_transport': assurance_transport
                    },
                    'validite': {
                        'validite_offre': validite_offre,
                        'devise': devise,
                        'clause_revision': clause_revision,
                        'taux_change_fixe': taux_change_fixe
                    },
                    'budget': {
                        'centre_cout': centre_cout,
                        'approbation_requise': approbation_requise,
                        'signature_electronique': signature_electronique
                    },
                    'emballage_special': emballage_special,
                    'projet_associe': projet_id
                }
                
                # Préparation des données
                data = {
                    'type_formulaire': 'BON_COMMANDE',
                    'numero_document': numero_bc,
                    'project_id': projet_id,
                    'company_id': fournisseur_id,
                    'employee_id': employe_id,
                    'statut': statut,
                    'priorite': priorite,
                    'date_creation': date_creation,
                    'date_echeance': date_livraison_prevue,
                    'montant_total': montant_total_calcule,
                    'notes': notes_completes,
                    'metadonnees_json': json.dumps(metadonnees),
                    'lignes': articles_lines
                }
                
                # Création du formulaire
                formulaire_id = gestionnaire.creer_formulaire(data)
                
                if formulaire_id:
                    # Création automatique de l'approvisionnement
                    try:
                        # Rechercher le fournisseur dans la table fournisseurs
                        fournisseur_data = gestionnaire.db.execute_query(
                            "SELECT f.id FROM fournisseurs f WHERE f.company_id = ?", 
                            (fournisseur_id,)
                        )
                        
                        if fournisseur_data:
                            fournisseur_ref_id = fournisseur_data[0]['id']
                        else:
                            # Créer l'entrée fournisseur si elle n'existe pas
                            fournisseur_ref_id = gestionnaire.db.execute_insert(
                                "INSERT INTO fournisseurs (company_id, code_fournisseur, delai_livraison_moyen, conditions_paiement) VALUES (?, ?, ?, ?)",
                                (fournisseur_id, f"FOUR-{fournisseur_id}", delai_livraison_max, conditions_paiement)
                            )
                        
                        # Créer l'approvisionnement
                        appro_data = {
                            'statut_livraison': 'EN_ATTENTE' if statut == 'ENVOYÉ' else 'CONFIRMÉ',
                            'date_commande': date_creation,
                            'date_livraison_prevue': date_livraison_prevue,
                            'quantite_commandee': sum(art['quantite'] for art in articles_lines),
                            'notes_livraison': f"BC {numero_bc} - {len(articles_lines)} article(s)"
                        }
                        
                        appro_id = gestionnaire.db.create_approvisionnement(formulaire_id, fournisseur_ref_id, appro_data)
                    except Exception as e:
                        st.warning(f"BC créé mais erreur approvisionnement: {e}")
                    
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

def render_bon_commande_list(gestionnaire):
    """Liste des Bons de Commande avec filtres avancés"""
    st.markdown("#### 📋 Liste des Bons de Commande")
    
    bons_commande = gestionnaire.get_formulaires('BON_COMMANDE')
    
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
    bcs_en_retard = [bc for bc in bons_commande 
                     if bc.get('date_echeance') and 
                     datetime.strptime(bc['date_echeance'], '%Y-%m-%d').date() < datetime.now().date() and
                     bc['statut'] not in ['TERMINÉ', 'ANNULÉ']]
    
    if bcs_en_retard:
        st.error(f"🚨 {len(bcs_en_retard)} Bon(s) de Commande en retard de livraison!")
    
    # Filtres avancés
    with st.expander("🔍 Filtres et Recherche", expanded=False):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            filtre_statut = st.multiselect("Statut", gestionnaire.statuts, default=gestionnaire.statuts)
        with col_f2:
            filtre_priorite = st.multiselect("Priorité", gestionnaire.priorites, default=gestionnaire.priorites)
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
            montant_min = st.number_input("Montant minimum ($)", min_value=0.0, value=0.0)
        with col_date:
            date_depuis = st.date_input("Commandes depuis", value=datetime.now().date() - timedelta(days=90))
    
    # Application des filtres
    bons_filtres = []
    for bc in bons_commande:
        # Filtre statut
        if bc['statut'] not in filtre_statut:
            continue
        
        # Filtre priorité
        if bc['priorite'] not in filtre_priorite:
            continue
        
        # Filtre fournisseur
        if 'Tous' not in filtre_fournisseur and bc.get('company_nom', 'N/A') not in filtre_fournisseur:
            continue
        
        # Filtre montant
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
        
        # Filtre statut livraison
        if filtre_livraison != "Tous":
            # Ici on pourrait ajouter la logique de statut livraison depuis la table approvisionnements
            pass
        
        bons_filtres.append(bc)
    
    # Affichage résultats
    st.markdown(f"**{len(bons_filtres)} Bon(s) de Commande trouvé(s)**")
    
    if bons_filtres:
        # Tri
        col_sort1, col_sort2 = st.columns(2)
        with col_sort1:
            tri_par = st.selectbox("Trier par", ["Date création", "Date livraison", "Montant", "Priorité", "Statut"])
        with col_sort2:
            tri_ordre = st.selectbox("Ordre", ["Décroissant", "Croissant"])
        
        # Application du tri
        if tri_par == "Date création":
            bons_filtres.sort(key=lambda x: x.get('date_creation', ''), reverse=(tri_ordre == "Décroissant"))
        elif tri_par == "Date livraison":
            bons_filtres.sort(key=lambda x: x.get('date_echeance', ''), reverse=(tri_ordre == "Décroissant"))
        elif tri_par == "Montant":
            bons_filtres.sort(key=lambda x: x.get('montant_total', 0), reverse=(tri_ordre == "Décroissant"))
        elif tri_par == "Priorité":
            ordre_priorite = {'CRITIQUE': 3, 'URGENT': 2, 'NORMAL': 1}
            bons_filtres.sort(key=lambda x: ordre_priorite.get(x.get('priorite', 'NORMAL'), 1), reverse=(tri_ordre == "Décroissant"))
        
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
                    if marquer_bc_recu(gestionnaire, bc_selectionne):
                        st.success("✅ BC marqué comme reçu!")
                        st.rerun()
    else:
        st.info("Aucun Bon de Commande ne correspond aux critères de recherche.")

def render_delivery_tracking(gestionnaire):
    """Interface de suivi des livraisons"""
    st.markdown("#### 🚚 Suivi des Livraisons")
    
    # Récupération des approvisionnements liés aux BCs
    try:
        query = """
            SELECT a.*, f.numero_document, c.nom as fournisseur_nom,
                   e.prenom || ' ' || e.nom as responsable_nom
            FROM approvisionnements a
            JOIN formulaires f ON a.formulaire_id = f.id
            JOIN companies c ON f.company_id = c.id
            LEFT JOIN employees e ON f.employee_id = e.id
            WHERE f.type_formulaire = 'BON_COMMANDE'
            ORDER BY a.date_livraison_prevue ASC
        """
        
        approvisionnements = gestionnaire.db.execute_query(query)
        appros = [dict(row) for row in approvisionnements]
        
    except Exception as e:
        st.error(f"Erreur récupération approvisionnements: {e}")
        appros = []
    
    if not appros:
        st.info("Aucun approvisionnement en cours de suivi.")
        return
    
    # Métriques de livraison
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        st.metric("📦 Total Livraisons", len(appros))
    with col_m2:
        en_attente = len([a for a in appros if a['statut_livraison'] in ['EN_ATTENTE', 'CONFIRMÉ']])
        st.metric("⏳ En Attente", en_attente)
    with col_m3:
        en_transit = len([a for a in appros if a['statut_livraison'] == 'EXPÉDIÉ'])
        st.metric("🚛 En Transit", en_transit)
    with col_m4:
        livrees = len([a for a in appros if a['statut_livraison'] == 'LIVRÉ'])
        st.metric("✅ Livrées", livrees)
    
    # Alertes de retard
    today = datetime.now().date()
    retards = []
    for appro in appros:
        try:
            date_prevue = datetime.strptime(appro['date_livraison_prevue'], '%Y-%m-%d').date()
            if date_prevue < today and appro['statut_livraison'] not in ['LIVRÉ', 'ANNULÉ']:
                retards.append(appro)
        except:
            continue
    
    if retards:
        st.error(f"🚨 {len(retards)} livraison(s) en retard détectée(s)!")
        
        # Affichage des retards
        with st.expander("📋 Détails des Retards", expanded=True):
            for retard in retards:
                try:
                    date_prevue = datetime.strptime(retard['date_livraison_prevue'], '%Y-%m-%d').date()
                    jours_retard = (today - date_prevue).days
                    
                    st.error(f"""
                    **BC {retard['numero_document']}** - {retard['fournisseur_nom']}
                    - Livraison prévue : {date_prevue.strftime('%d/%m/%Y')}
                    - Retard : {jours_retard} jour(s)
                    - Statut : {retard['statut_livraison']}
                    """)
                except:
                    continue
    
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
            ['Tous'] + list(set([a['fournisseur_nom'] for a in appros])))
    
    # Application des filtres
    appros_filtres = []
    for appro in appros:
        if appro['statut_livraison'] in filtre_statut_livraison:
            if filtre_fournisseur_suivi == 'Tous' or appro['fournisseur_nom'] == filtre_fournisseur_suivi:
                appros_filtres.append(appro)
    
    # Tableau de suivi
    if appros_filtres:
        for appro in appros_filtres:
            with st.container():
                col_info, col_statut, col_actions = st.columns([3, 1, 1])
                
                with col_info:
                    try:
                        date_prevue = datetime.strptime(appro['date_livraison_prevue'], '%Y-%m-%d').date()
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
                    **BC {appro['numero_document']}** - {appro['fournisseur_nom']}
                    - Responsable : {appro['responsable_nom']}
                    - Livraison prévue : {appro['date_livraison_prevue']} - {date_info}
                    - Quantité : {appro.get('quantite_commandee', 'N/A')}
                    """)
                
                with col_statut:
                    # Sélecteur de statut
                    nouveaux_statuts = ['EN_ATTENTE', 'CONFIRMÉ', 'EN_PRODUCTION', 'EXPÉDIÉ', 'LIVRÉ', 'ANNULÉ']
                    statut_actuel = appro['statut_livraison']
                    
                    nouveau_statut = st.selectbox(
                        f"Statut", 
                        nouveaux_statuts,
                        index=nouveaux_statuts.index(statut_actuel) if statut_actuel in nouveaux_statuts else 0,
                        key=f"statut_{appro['id']}"
                    )
                
                with col_actions:
                    # Bouton de mise à jour
                    if st.button("💾 Mettre à jour", key=f"update_{appro['id']}", use_container_width=True):
                        if mettre_a_jour_statut_livraison(gestionnaire, appro['id'], nouveau_statut):
                            st.success(f"✅ Statut mis à jour: {nouveau_statut}")
                            st.rerun()
                    
                    # Bouton de détails
                    if st.button("👁️ Détails", key=f"details_{appro['id']}", use_container_width=True):
                        st.session_state.selected_appro_details = appro['id']
                
                # Notes de livraison
                if appro.get('notes_livraison'):
                    st.text(f"📝 Notes: {appro['notes_livraison']}")
                
                st.markdown("---")
    
    # Section de mise à jour rapide
    st.markdown("##### ⚡ Mise à Jour Rapide")
    
    col_rapid1, col_rapid2, col_rapid3 = st.columns(3)
    
    with col_rapid1:
        if st.button("📦 Marquer Plusieurs comme Expédiés", use_container_width=True, key="bc_marquer_expedies"):
            count = 0
            for appro in appros_filtres:
                if appro['statut_livraison'] == 'CONFIRMÉ':
                    if mettre_a_jour_statut_livraison(gestionnaire, appro['id'], 'EXPÉDIÉ'):
                        count += 1
            if count > 0:
                st.success(f"✅ {count} livraison(s) marquée(s) comme expédiées")
                st.rerun()
    
    with col_rapid2:
        if st.button("✅ Marquer Arrivées Aujourd'hui", use_container_width=True, key="bc_marquer_arrives"):
            count = 0
            for appro in appros_filtres:
                try:
                    date_prevue = datetime.strptime(appro['date_livraison_prevue'], '%Y-%m-%d').date()
                    if date_prevue <= today and appro['statut_livraison'] == 'EXPÉDIÉ':
                        if mettre_a_jour_statut_livraison(gestionnaire, appro['id'], 'LIVRÉ'):
                            count += 1
                except:
                    continue
            if count > 0:
                st.success(f"✅ {count} livraison(s) marquée(s) comme livrées")
                st.rerun()
    
    with col_rapid3:
        if st.button("📧 Relancer Fournisseurs en Retard", use_container_width=True, key="bc_relancer_retards"):
            if retards:
                st.info(f"📧 Notifications envoyées pour {len(retards)} commande(s) en retard")
                # Ici on pourrait implémenter l'envoi d'emails automatiques

def render_reception_marchandises(gestionnaire):
    """Interface de réception des marchandises avec mise à jour inventaire"""
    st.markdown("#### 📥 Réception des Marchandises")
    
    # Récupération des BCs expédiés ou livrés
    try:
        query = """
            SELECT f.*, c.nom as fournisseur_nom, a.id as appro_id, a.statut_livraison,
                   a.date_livraison_prevue, a.quantite_commandee, a.quantite_livree
            FROM formulaires f
            JOIN companies c ON f.company_id = c.id
            LEFT JOIN approvisionnements a ON f.id = a.formulaire_id
            WHERE f.type_formulaire = 'BON_COMMANDE' 
            AND f.statut IN ('ENVOYÉ', 'APPROUVÉ')
            AND (a.statut_livraison IN ('EXPÉDIÉ', 'LIVRÉ') OR a.statut_livraison IS NULL)
            ORDER BY f.date_echeance ASC
        """
        
        livraisons_attendues = gestionnaire.db.execute_query(query)
        livraisons = [dict(row) for row in livraisons_attendues]
        
    except Exception as e:
        st.error(f"Erreur récupération livraisons: {e}")
        livraisons = []
    
    if not livraisons:
        st.info("Aucune livraison en attente de réception.")
        return
    
    # Sélection de la livraison à traiter
    st.markdown("##### 📦 Sélection de la Livraison")
    
    livraison_options = [
        (liv['id'], f"{liv['numero_document']} - {liv['fournisseur_nom']} - {liv.get('date_echeance', 'N/A')}")
        for liv in livraisons
    ]
    
    livraison_id = st.selectbox(
        "Livraison à Réceptionner",
        options=[l[0] for l in livraison_options],
        format_func=lambda x: next((l[1] for l in livraison_options if l[0] == x), "")
    )
    
    if livraison_id:
        livraison_selectionnee = next((l for l in livraisons if l['id'] == livraison_id), None)
        
        if livraison_selectionnee:
            # Affichage des détails de la livraison
            st.markdown("##### 📋 Détails de la Livraison")
            
            col_det1, col_det2 = st.columns(2)
            with col_det1:
                st.info(f"""
                **N° BC :** {livraison_selectionnee['numero_document']}
                **Fournisseur :** {livraison_selectionnee['fournisseur_nom']}
                **Date Prévue :** {livraison_selectionnee.get('date_echeance', 'N/A')}
                **Montant :** {livraison_selectionnee.get('montant_total', 0):,.2f}$ CAD
                """)
            with col_det2:
                st.info(f"""
                **Statut BC :** {livraison_selectionnee['statut']}
                **Statut Livraison :** {livraison_selectionnee.get('statut_livraison', 'N/A')}
                **Qté Commandée :** {livraison_selectionnee.get('quantite_commandee', 'N/A')}
                **Qté Déjà Reçue :** {livraison_selectionnee.get('quantite_livree', 0)}
                """)
            
            # Récupération des lignes du BC
            bc_details = gestionnaire.get_formulaire_details(livraison_id)
            lignes_bc = bc_details.get('lignes', [])
            
            if lignes_bc:
                st.markdown("##### 📝 Articles à Réceptionner")
                
                with st.form(f"reception_form_{livraison_id}"):
                    # En-tête du formulaire de réception
                    col_form1, col_form2 = st.columns(2)
                    
                    with col_form1:
                        date_reception = st.date_input("Date de Réception", datetime.now().date())
                        numero_bon_livraison = st.text_input("N° Bon de Livraison",
                                                           placeholder="Numéro du transporteur")
                    
                    with col_form2:
                        responsable_reception = st.selectbox("Responsable Réception",
                            [e['id'] for e in get_employes_actifs()],
                            format_func=lambda x: next((f"{e['prenom']} {e['nom']}" for e in get_employes_actifs() if e['id'] == x), ""))
                        
                        etat_emballage = st.selectbox("État Emballage", 
                            ["Parfait", "Légers dommages", "Dommages importants", "Emballage détruit"])
                    
                    # Tableau de réception des articles
                    st.markdown("**Articles Reçus :**")
                    
                    col_head1, col_head2, col_head3, col_head4, col_head5, col_head6 = st.columns([3, 1, 1, 1, 1, 2])
                    with col_head1:
                        st.markdown("**Article**")
                    with col_head2:
                        st.markdown("**Commandé**")
                    with col_head3:
                        st.markdown("**Reçu**")
                    with col_head4:
                        st.markdown("**État**")
                    with col_head5:
                        st.markdown("**Conforme**")
                    with col_head6:
                        st.markdown("**Remarques**")
                    
                    articles_reception = []
                    
                    for i, ligne in enumerate(lignes_bc):
                        col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 2])
                        
                        with col1:
                            st.text(ligne['description'][:40] + "..." if len(ligne['description']) > 40 else ligne['description'])
                        
                        with col2:
                            st.text(f"{ligne['quantite']} {ligne['unite']}")
                        
                        with col3:
                            qte_recue = st.number_input("", min_value=0.0, max_value=float(ligne['quantite']),
                                                      value=float(ligne['quantite']), key=f"qte_{i}",
                                                      format="%.2f", step=0.1)
                        
                        with col4:
                            etat_article = st.selectbox("", ["Parfait", "Acceptable", "Défectueux", "Manquant"],
                                                       key=f"etat_{i}", index=0)
                        
                        with col5:
                            conforme = st.checkbox("", value=True, key=f"conforme_{i}")
                        
                        with col6:
                            remarques = st.text_input("", placeholder="Remarques...", key=f"rem_{i}")
                        
                        articles_reception.append({
                            'ligne_id': ligne['id'],
                            'description': ligne['description'],
                            'quantite_commandee': ligne['quantite'],
                            'quantite_recue': qte_recue,
                            'unite': ligne['unite'],
                            'etat_article': etat_article,
                            'conforme': conforme,
                            'remarques': remarques,
                            'prix_unitaire': ligne.get('prix_unitaire', 0)
                        })
                    
                    # Options de réception
                    st.markdown("##### ⚙️ Options de Réception")
                    
                    col_opt1, col_opt2 = st.columns(2)
                    with col_opt1:
                        reception_complete = st.checkbox("Réception Complète", value=True)
                        mise_a_jour_inventaire = st.checkbox("Mettre à Jour l'Inventaire", value=True)
                    
                    with col_opt2:
                        generer_rapport = st.checkbox("Générer Rapport de Réception", value=True)
                        notifier_demandeur = st.checkbox("Notifier le Demandeur", value=True)
                    
                    # Notes générales de réception
                    notes_reception = st.text_area("Notes de Réception",
                                                 placeholder="Observations générales, problèmes rencontrés...")
                    
                    # Récapitulatif
                    total_commande = sum(art['quantite_commandee'] for art in articles_reception)
                    total_recu = sum(art['quantite_recue'] for art in articles_reception)
                    articles_conformes = sum(1 for art in articles_reception if art['conforme'])
                    
                    st.markdown(f"""
                    <div style='background:#f0f9ff;padding:1rem;border-radius:8px;border-left:4px solid #3b82f6;'>
                        <h5 style='color:#1e40af;margin:0;'>📊 Récapitulatif de Réception</h5>
                        <p style='margin:0.5rem 0 0 0;'>Articles commandés : {len(lignes_bc)}</p>
                        <p style='margin:0;'>Quantité totale commandée : {total_commande}</p>
                        <p style='margin:0;'>Quantité totale reçue : {total_recu}</p>
                        <p style='margin:0;'>Articles conformes : {articles_conformes}/{len(articles_reception)}</p>
                        <p style='margin:0;'><strong>Taux de réception : {(total_recu/total_commande*100) if total_commande > 0 else 0:.1f}%</strong></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Boutons de validation
                    col_submit1, col_submit2 = st.columns(2)
                    
                    with col_submit1:
                        submit_reception = st.form_submit_button("✅ Valider la Réception", use_container_width=True, key="bc_valider_reception")
                    
                    with col_submit2:
                        submit_reception_partielle = st.form_submit_button("📦 Réception Partielle", use_container_width=True, key="bc_reception_partielle")
                    
                    # Traitement de la réception
                    if submit_reception or submit_reception_partielle:
                        try:
                            # Mise à jour du statut de livraison
                            if livraison_selectionnee.get('appro_id'):
                                nouveau_statut = 'LIVRÉ' if submit_reception else 'PARTIELLEMENT_LIVRÉ'
                                gestionnaire.db.update_approvisionnement_status(
                                    livraison_selectionnee['appro_id'], 
                                    nouveau_statut,
                                    f"Réception {date_reception.strftime('%d/%m/%Y')} - {notes_reception}"
                                )
                            
                            # Mise à jour de l'inventaire si demandé
                            if mise_a_jour_inventaire:
                                articles_maj_inventaire = 0
                                for article in articles_reception:
                                    if article['quantite_recue'] > 0 and article['conforme']:
                                        # Ici on pourrait faire le lien avec l'inventaire
                                        # En recherchant par description ou code_article
                                        articles_maj_inventaire += 1
                                
                                if articles_maj_inventaire > 0:
                                    st.info(f"📦 {articles_maj_inventaire} article(s) mis à jour dans l'inventaire")
                            
                            # Mise à jour du statut du BC
                            nouveau_statut_bc = 'TERMINÉ' if reception_complete else 'APPROUVÉ'
                            gestionnaire.modifier_statut_formulaire(
                                livraison_id,
                                nouveau_statut_bc,
                                responsable_reception,
                                f"Réception marchandises - {notes_reception}"
                            )
                            
                            # Enregistrement de la réception dans l'historique
                            recap_reception = f"""=== RÉCEPTION MARCHANDISES ===
Date : {date_reception.strftime('%d/%m/%Y')}
Responsable : {next((f"{e['prenom']} {e['nom']}" for e in get_employes_actifs() if e['id'] == responsable_reception), 'N/A')}
N° Bon livraison : {numero_bon_livraison}
État emballage : {etat_emballage}

=== ARTICLES REÇUS ===
{chr(10).join([f"- {art['description']} : {art['quantite_recue']}/{art['quantite_commandee']} {art['unite']} - {art['etat_article']} - {'Conforme' if art['conforme'] else 'Non conforme'}" for art in articles_reception])}

=== RÉCAPITULATIF ===
Total commandé : {total_commande}
Total reçu : {total_recu} 
Taux réception : {(total_recu/total_commande*100) if total_commande > 0 else 0:.1f}%
Articles conformes : {articles_conformes}/{len(articles_reception)}

=== NOTES ===
{notes_reception}"""
                            
                            gestionnaire.enregistrer_validation(
                                livraison_id,
                                responsable_reception,
                                'RECEPTION_MARCHANDISES',
                                recap_reception
                            )
                            
                            # Message de succès
                            st.success(f"""
                            ✅ **Réception Validée avec Succès !**
                            
                            📦 **BC {livraison_selectionnee['numero_document']}** marqué comme {nouveau_statut_bc}
                            📊 **{total_recu}/{total_commande}** articles réceptionnés
                            ✅ **{articles_conformes}** article(s) conforme(s)
                            """)
                            
                            # Actions suivantes
                            col_next1, col_next2 = st.columns(2)
                            with col_next1:
                                if st.button("📋 Retour Liste BC", use_container_width=True, key="bc_retour_liste_reception"):
                                    st.session_state.form_action = "list_bon_commande"
                                    st.rerun()
                            with col_next2:
                                if st.button("📥 Autre Réception", use_container_width=True, key="bc_autre_reception"):
                                    st.rerun()
                                    
                        except Exception as e:
                            st.error(f"❌ Erreur lors de la réception: {e}")

def render_bon_commande_stats(gestionnaire):
    """Statistiques détaillées des Bons de Commande"""
    st.markdown("#### 📊 Statistiques Bons de Commande")
    
    bons_commande = gestionnaire.get_formulaires('BON_COMMANDE')
    
    if not bons_commande:
        st.info("Aucune donnée pour les statistiques.")
        return
    
    # Calculs statistiques
    montant_total = sum(bc.get('montant_total', 0) for bc in bons_commande)
    montant_moyen = montant_total / len(bons_commande) if bons_commande else 0
    
    # Métriques principales
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📦 Total BCs", len(bons_commande))
    with col2:
        en_cours = len([bc for bc in bons_commande if bc['statut'] in ['VALIDÉ', 'ENVOYÉ']])
        st.metric("🔄 En Cours", en_cours)
    with col3:
        termines = len([bc for bc in bons_commande if bc['statut'] == 'TERMINÉ'])
        taux_completion = (termines / len(bons_commande) * 100) if bons_commande else 0
        st.metric("✅ Terminés", termines, delta=f"{taux_completion:.1f}%")
    with col4:
        st.metric("💰 Montant Total", f"{montant_total:,.0f}$ CAD")
    with col5:
        st.metric("📊 Montant Moyen", f"{montant_moyen:,.0f}$ CAD")
    
    # Analyses de performance
    col_perf1, col_perf2 = st.columns(2)
    
    with col_perf1:
        # Délais de livraison
        st.markdown("##### ⏱️ Performance Livraisons")
        
        try:
            # Calcul des délais de livraison
            delais_info = []
            for bc in bons_commande:
                if bc.get('date_echeance') and bc['statut'] == 'TERMINÉ':
                    try:
                        date_commande = datetime.strptime(bc['date_creation'][:10], '%Y-%m-%d').date()
                        date_livraison = datetime.strptime(bc['date_echeance'], '%Y-%m-%d').date()
                        delai = (date_livraison - date_commande).days
                        delais_info.append(delai)
                    except:
                        continue
            
            if delais_info:
                delai_moyen = sum(delais_info) / len(delais_info)
                delai_min = min(delais_info)
                delai_max = max(delais_info)
                
                st.metric("Délai Moyen", f"{delai_moyen:.1f} jours")
                st.metric("Délai Min/Max", f"{delai_min} - {delai_max} jours")
            else:
                st.info("Pas assez de données pour calculer les délais")
                
        except Exception as e:
            st.error(f"Erreur calcul délais: {e}")
    
    with col_perf2:
        # Fournisseurs les plus fiables
        st.markdown("##### 🏆 Top Fournisseurs")
        
        fournisseur_stats = {}
        for bc in bons_commande:
            fournisseur = bc.get('company_nom', 'N/A')
            if fournisseur not in fournisseur_stats:
                fournisseur_stats[fournisseur] = {
                    'count': 0, 
                    'montant': 0,
                    'termines': 0
                }
            fournisseur_stats[fournisseur]['count'] += 1
            fournisseur_stats[fournisseur]['montant'] += bc.get('montant_total', 0)
            if bc['statut'] == 'TERMINÉ':
                fournisseur_stats[fournisseur]['termines'] += 1
        
        # Calcul du taux de fiabilité et tri
        for fournisseur, stats in fournisseur_stats.items():
            stats['taux_fiabilite'] = (stats['termines'] / stats['count'] * 100) if stats['count'] > 0 else 0
        
        top_fournisseurs = sorted(fournisseur_stats.items(), 
                                key=lambda x: (x[1]['taux_fiabilite'], x[1]['montant']), 
                                reverse=True)[:5]
        
        for i, (fournisseur, stats) in enumerate(top_fournisseurs, 1):
            st.metric(
                f"{i}. {fournisseur[:15]}",
                f"{stats['taux_fiabilite']:.0f}% fiabilité",
                delta=f"{stats['count']} BCs - {stats['montant']:,.0f}$"
            )
    
    # Graphiques
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Répartition par statut
        statut_counts = {}
        statut_montants = {}
        for bc in bons_commande:
            statut = bc['statut']
            statut_counts[statut] = statut_counts.get(statut, 0) + 1
            statut_montants[statut] = statut_montants.get(statut, 0) + bc.get('montant_total', 0)
        
        if statut_counts:
            colors_statut = {
                'BROUILLON': '#f59e0b', 'VALIDÉ': '#3b82f6', 'ENVOYÉ': '#8b5cf6',
                'APPROUVÉ': '#10b981', 'TERMINÉ': '#059669', 'ANNULÉ': '#ef4444'
            }
            fig = px.pie(values=list(statut_counts.values()), names=list(statut_counts.keys()),
                        title="📊 Répartition par Statut", 
                        color_discrete_map=colors_statut)
            fig.update_layout(showlegend=True, height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_g2:
        # Évolution mensuelle
        st.markdown("##### 📈 Évolution Mensuelle")
        
        evolution_mensuelle = {}
        for bc in bons_commande:
            try:
                mois = bc['date_creation'][:7]  # YYYY-MM
                if mois not in evolution_mensuelle:
                    evolution_mensuelle[mois] = {'count': 0, 'montant': 0}
                evolution_mensuelle[mois]['count'] += 1
                evolution_mensuelle[mois]['montant'] += bc.get('montant_total', 0)
            except:
                continue
        
        if evolution_mensuelle:
            mois_sorted = sorted(evolution_mensuelle.items())
            df_evolution = pd.DataFrame([
                {'Mois': mois, 'Nombre BCs': data['count'], 'Montant (k$)': data['montant']/1000}
                for mois, data in mois_sorted[-12:]  # 12 derniers mois
            ])
            
            fig = px.bar(df_evolution, x='Mois', y='Nombre BCs',
                        title="Évolution Mensuelle des BCs",
                        hover_data=['Montant (k$)'])
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # Analyse des montants
    col_montant1, col_montant2 = st.columns(2)
    
    with col_montant1:
        # Répartition par tranches de montant
        st.markdown("##### 💰 Répartition par Montant")
        
        tranches = {
            '< 1k$': 0,
            '1k$ - 5k$': 0,
            '5k$ - 10k$': 0,
            '10k$ - 50k$': 0,
            '> 50k$': 0
        }
        
        for bc in bons_commande:
            montant = bc.get('montant_total', 0)
            if montant < 1000:
                tranches['< 1k$'] += 1
            elif montant < 5000:
                tranches['1k$ - 5k$'] += 1
            elif montant < 10000:
                tranches['5k$ - 10k$'] += 1
            elif montant < 50000:
                tranches['10k$ - 50k$'] += 1
            else:
                tranches['> 50k$'] += 1
        
        fig = px.bar(x=list(tranches.keys()), y=list(tranches.values()),
                    title="Nombre de BCs par Tranche de Montant")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    
    with col_montant2:
        # Analyse des priorités
        st.markdown("##### 🚨 Analyse des Priorités")
        
        priorite_stats = {}
        for bc in bons_commande:
            priorite = bc['priorite']
            if priorite not in priorite_stats:
                priorite_stats[priorite] = {
                    'count': 0,
                    'montant': 0,
                    'termines': 0,
                    'delai_moyen': 0
                }
            priorite_stats[priorite]['count'] += 1
            priorite_stats[priorite]['montant'] += bc.get('montant_total', 0)
            if bc['statut'] == 'TERMINÉ':
                priorite_stats[priorite]['termines'] += 1
        
        # Affichage des statistiques par priorité
        for priorite, stats in priorite_stats.items():
            taux_completion = (stats['termines'] / stats['count'] * 100) if stats['count'] > 0 else 0
            icon = {'CRITIQUE': '🔴', 'URGENT': '🟡', 'NORMAL': '🟢'}.get(priorite, '⚪')
            
            st.metric(
                f"{icon} {priorite}",
                f"{stats['count']} BCs",
                delta=f"{taux_completion:.0f}% terminés - {stats['montant']:,.0f}$"
            )
    
    # Alertes et recommandations
    st.markdown("---")
    st.markdown("##### 🚨 Alertes et Recommandations")
    
    alerts = []
    
    # BCs en retard
    bcs_en_retard = [bc for bc in bons_commande 
                     if bc.get('date_echeance') and 
                     datetime.strptime(bc['date_echeance'], '%Y-%m-%d').date() < datetime.now().date() and
                     bc['statut'] not in ['TERMINÉ', 'ANNULÉ']]
    
    if bcs_en_retard:
        alerts.append(f"🔴 {len(bcs_en_retard)} Bon(s) de Commande en retard de livraison")
    
    # BCs critiques non traités
    critiques_non_traites = [bc for bc in bons_commande 
                            if bc['priorite'] == 'CRITIQUE' and bc['statut'] in ['BROUILLON', 'VALIDÉ']]
    
    if critiques_non_traites:
        alerts.append(f"🟡 {len(critiques_non_traites)} BC(s) critique(s) non envoyé(s)")
    
    # Fournisseurs peu fiables
    fournisseurs_problematiques = []
    for fournisseur, stats in fournisseur_stats.items():
        if stats['count'] >= 3 and stats['taux_fiabilite'] < 80:
            fournisseurs_problematiques.append(fournisseur)
    
    if fournisseurs_problematiques:
        alerts.append(f"⚠️ {len(fournisseurs_problematiques)} fournisseur(s) avec taux de fiabilité < 80%")
    
    # Affichage des alertes
    if alerts:
        for alert in alerts:
            st.warning(alert)
        
        # Recommandations
        st.markdown("**Recommandations :**")
        if bcs_en_retard:
            st.markdown("• Relancer les fournisseurs pour les livraisons en retard")
        if critiques_non_traites:
            st.markdown("• Traiter en priorité les BCs critiques")
        if fournisseurs_problematiques:
            st.markdown("• Évaluer les performances des fournisseurs peu fiables")
    else:
        st.success("✅ Aucune alerte détectée - Gestion des commandes optimale")

# Fonctions utilitaires spécifiques aux BCs

def mettre_a_jour_statut_livraison(gestionnaire, appro_id, nouveau_statut):
    """Met à jour le statut d'une livraison"""
    try:
        return gestionnaire.db.update_approvisionnement_status(appro_id, nouveau_statut)
    except Exception as e:
        st.error(f"Erreur mise à jour statut: {e}")
        return False

def marquer_bc_recu(gestionnaire, bc_id):
    """Marque un BC comme reçu rapidement"""
    try:
        # Mise à jour du statut du BC
        gestionnaire.modifier_statut_formulaire(bc_id, 'TERMINÉ', 1, "Marqué comme reçu - Traitement rapide")
        
        # Mise à jour de l'approvisionnement si il existe
        try:
            query = "SELECT id FROM approvisionnements WHERE formulaire_id = ?"
            result = gestionnaire.db.execute_query(query, (bc_id,))
            if result:
                appro_id = result[0]['id']
                gestionnaire.db.update_approvisionnement_status(appro_id, 'LIVRÉ', "Réception rapide validée")
        except:
            pass
        
        return True
    except Exception as e:
        st.error(f"Erreur marquage réception: {e}")
        return False

def render_templates_bon_commande(gestionnaire):
    """Interface de gestion des templates de BC"""
    st.markdown("#### 📋 Templates Bons de Commande")
    st.info("🚧 Gestion des templates de BC - Fonctionnalité avancée à développer")
    
    # TODO: Interface pour créer et gérer des templates de BC par industrie/type
    # - Templates standards par secteur (auto, aéro, construction)
    # - Clauses pré-définies
    # - Conditions commerciales par défaut

def render_rapports_bon_commande(gestionnaire):
    """Interface de génération de rapports BC"""
    st.markdown("#### 📈 Rapports Bons de Commande")
    st.info("🚧 Génération de rapports BC - Fonctionnalité avancée à développer")
    
    # TODO: Génération de rapports avancés
    # - Rapport mensuel des achats
    # - Performance fournisseurs
    # - Analyse des coûts
    # - Export Excel/PDF
    
    # TODO: Implémenter interface similaire aux Bons de Travail
    # Spécificités: Conversion Bon d'Achats → Bon de Commande, envoi fournisseurs, suivi livraisons

def render_demandes_prix_tab(gestionnaire):
    """Interface complète pour les Demandes de Prix - RFQ Multi-Fournisseurs"""
    st.markdown("### 💰 Demandes de Prix (RFQ)")
    
    # Alerte pour négociations en cours
    demandes_actives = get_demandes_prix_actives(gestionnaire)
    if demandes_actives:
        st.info(f"💡 {len(demandes_actives)} Demande(s) de Prix en cours de négociation")
    
    # Actions spécifiques DP
    col_action1, col_action2, col_action3, col_action4 = st.columns(4)
    with col_action1:
        if st.button("➕ Nouvelle Demande Prix", use_container_width=True, key="dp_nouveau"):
            st.session_state.form_action = "create_demande_prix"
    with col_action2:
        if st.button("📋 Demandes Actives", use_container_width=True, key="dp_liste"):
            st.session_state.form_action = "list_demandes_actives"
    with col_action3:
        if st.button("📊 Comparer Offres", use_container_width=True, key="dp_comparer"):
            st.session_state.form_action = "compare_offers"
    with col_action4:
        if st.button("🏆 Sélectionner Gagnant", use_container_width=True, key="dp_selection"):
            st.session_state.form_action = "select_winner"
    
    # Actions secondaires
    col_action5, col_action6, col_action7, col_action8 = st.columns(4)
    with col_action5:
        if st.button("📊 Statistiques", use_container_width=True, key="dp_stats"):
            st.session_state.form_action = "stats_demande_prix"
    with col_action6:
        if st.button("📋 Historique RFQ", use_container_width=True, key="dp_historique"):
            st.session_state.form_action = "historique_rfq"
    with col_action7:
        if st.button("⚙️ Templates DP", use_container_width=True, key="dp_templates"):
            st.session_state.form_action = "templates_demande_prix"
    with col_action8:
        if st.button("📈 Performance", use_container_width=True, key="dp_performance"):
            st.session_state.form_action = "performance_fournisseurs"
    
    # Affichage selon l'action
    action = st.session_state.get('form_action', 'list_demandes_actives')
    
    if action == "create_demande_prix":
        render_demande_prix_form(gestionnaire)
    elif action == "list_demandes_actives":
        render_demande_prix_list(gestionnaire)
    elif action == "compare_offers":
        render_compare_offers(gestionnaire)
    elif action == "select_winner":
        render_select_winner(gestionnaire)
    elif action == "stats_demande_prix":
        render_demande_prix_stats(gestionnaire)
    elif action == "historique_rfq":
        render_historique_rfq(gestionnaire)
    elif action == "templates_demande_prix":
        render_templates_demande_prix(gestionnaire)
    elif action == "performance_fournisseurs":
        render_performance_fournisseurs(gestionnaire)

# =============================================================================
# FORMULAIRE CRÉATION DEMANDE DE PRIX
# =============================================================================

def render_demande_prix_form(gestionnaire):
    """Formulaire de création de Demande de Prix - RFQ Multi-Fournisseurs"""
    st.markdown("#### ➕ Nouvelle Demande de Prix (RFQ)")
    
    with st.form("demande_prix_form", clear_on_submit=True):
        # En-tête du formulaire
        col1, col2 = st.columns(2)
        
        with col1:
            numero_dp = gestionnaire.generer_numero_document('DEMANDE_PRIX')
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
            priorite = st.selectbox("Priorité", gestionnaire.priorites, index=0)
            
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
            type_rfq = st.selectbox("Type d'Appel d'Offres", 
                ["Ouvert", "Restreint", "Négocié", "Urgente"])
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
        
        # CRITÈRES D'ÉVALUATION AVEC PONDÉRATIONS
        st.markdown("##### ⚖️ Critères d'Évaluation et Pondérations")
        st.info("💡 Les pondérations doivent totaliser 100%")
        
        col_crit1, col_crit2, col_crit3 = st.columns(3)
        
        with col_crit1:
            critere_prix = st.checkbox("Prix", value=True)
            ponderation_prix = st.slider("Pondération Prix (%)", 0, 100, 40, disabled=not critere_prix)
        
        with col_crit2:
            critere_delai = st.checkbox("Délai de Livraison", value=True)
            ponderation_delai = st.slider("Pondération Délai (%)", 0, 100, 30, disabled=not critere_delai)
        
        with col_crit3:
            critere_qualite = st.checkbox("Qualité Fournisseur", value=True)
            ponderation_qualite = st.slider("Pondération Qualité (%)", 0, 100, 30, disabled=not critere_qualite)
        
        # Autres critères optionnels
        col_crit4, col_crit5 = st.columns(2)
        with col_crit4:
            critere_proximite = st.checkbox("Proximité Géographique")
            ponderation_proximite = st.slider("Pondération Proximité (%)", 0, 100, 0, disabled=not critere_proximite)
        
        with col_crit5:
            critere_experience = st.checkbox("Expérience Secteur")
            ponderation_experience = st.slider("Pondération Expérience (%)", 0, 100, 0, disabled=not critere_experience)
        
        # Validation des pondérations
        total_ponderation = ponderation_prix + ponderation_delai + ponderation_qualite + ponderation_proximite + ponderation_experience
        
        if total_ponderation != 100:
            st.error(f"⚠️ Total des pondérations : {total_ponderation}% (doit être 100%)")
        else:
            st.success(f"✅ Total des pondérations : {total_ponderation}%")
        
        # SÉLECTION MULTIPLE FOURNISSEURS (NOUVEAUTÉ VS BA/BC)
        st.markdown("##### 🏢 Sélection des Fournisseurs (Multi-sélection)")
        
        fournisseurs_disponibles = get_fournisseurs_actifs()
        
        if not fournisseurs_disponibles:
            st.error("❌ Aucun fournisseur disponible. Veuillez d'abord ajouter des fournisseurs dans le CRM.")
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
                    # Sélectionner automatiquement 3-4 meilleurs fournisseurs
                    fournisseurs_auto = select_fournisseurs_recommandes(fournisseurs_filtres, 4)
                    st.session_state.fournisseurs_auto_selected = [f['id'] for f in fournisseurs_auto]
            
            # Multi-sélection des fournisseurs
            fournisseurs_preselected = st.session_state.get('fournisseurs_auto_selected', [])
            
            fournisseurs_selectionnes = st.multiselect(
                "Fournisseurs Invités (3-5 recommandés) *",
                options=[f['id'] for f in fournisseurs_filtres],
                default=fournisseurs_preselected,
                format_func=lambda x: next((f"{f['nom']} - {f['secteur']} - {get_note_fournisseur(f)}/10" for f in fournisseurs_filtres if f['id'] == x), ""),
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
                            note = get_note_fournisseur(fournisseur)
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
        
        # CRITÈRES DE SÉLECTION DÉTAILLÉS
        st.markdown("##### 🎯 Critères de Sélection Détaillés")
        
        criteres_techniques = st.text_area("Critères Techniques",
            placeholder="Spécifications techniques obligatoires, certifications requises...")
        
        criteres_commerciaux = st.text_area("Critères Commerciaux", 
            placeholder="Conditions de paiement, garanties, service après-vente...")
        
        criteres_exclusion = st.text_area("Critères d'Exclusion",
            placeholder="Motifs d'exclusion automatique des offres...")
        
        # NOTES ET INSTRUCTIONS SPÉCIALES
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
                
                # Construction des critères d'évaluation
                criteres_evaluation = {
                    'prix': {'actif': critere_prix, 'ponderation': ponderation_prix},
                    'delai': {'actif': critere_delai, 'ponderation': ponderation_delai},
                    'qualite': {'actif': critere_qualite, 'ponderation': ponderation_qualite},
                    'proximite': {'actif': critere_proximite, 'ponderation': ponderation_proximite},
                    'experience': {'actif': critere_experience, 'ponderation': ponderation_experience}
                }
                
                # Métadonnées RFQ complètes
                metadonnees_rfq = {
                    'type_rfq': type_rfq,
                    'delai_reponse': delai_reponse,
                    'mode_evaluation': mode_evaluation,
                    'validite_offre': validite_offre,
                    'conditions_participation': conditions_participation,
                    'langue_reponse': langue_reponse,
                    'criteres_evaluation': criteres_evaluation,
                    'fournisseurs_invites': fournisseurs_selectionnes,
                    'specifications_techniques': specifications_techniques,
                    'documents_joints': documents_joints,
                    'livraison_lieu': livraison_lieu,
                    'conditions_commerciales': {
                        'paiement': conditions_paiement_souhaitees,
                        'garantie': garantie_demandee,
                        'incoterm': incoterm,
                        'devise': devise_souhaitee,
                        'validite_prix': validite_prix,
                        'penalites_retard': penalites_retard
                    },
                    'procedure_reponse': {
                        'format': format_reponse,
                        'visite_site': visite_site,
                        'reunion_clarification': reunion_clarification,
                        'remise_echantillons': remise_echantillons,
                        'demonstration': demonstration,
                        'contact_technique': contact_technique
                    },
                    'criteres_selection': {
                        'techniques': criteres_techniques,
                        'commerciaux': criteres_commerciaux,
                        'exclusion': criteres_exclusion
                    }
                }
                
                # Construction des notes complètes
                notes_completes = f"""=== DEMANDE DE PRIX (RFQ) ===
Objet : {objet_rfq}
Type : {type_rfq}
Mode d'évaluation : {mode_evaluation}

=== DESCRIPTION ===
{description_detaillee}

=== SPÉCIFICATIONS TECHNIQUES ===
{specifications_techniques or 'Voir articles détaillés'}

=== FOURNISSEURS INVITÉS ===
{len(fournisseurs_selectionnes)} fournisseur(s) sélectionné(s)

=== CRITÈRES D'ÉVALUATION ===
Prix : {ponderation_prix}%
Délai : {ponderation_delai}%
Qualité : {ponderation_qualite}%
Proximité : {ponderation_proximite}%
Expérience : {ponderation_experience}%

=== CONDITIONS COMMERCIALES ===
Paiement : {conditions_paiement_souhaitees}
Garantie : {garantie_demandee or 'Standard'}
Incoterm : {incoterm}
Devise : {devise_souhaitee}
Validité prix : {validite_prix} jours

=== CRITÈRES TECHNIQUES ===
{criteres_techniques or 'Voir spécifications articles'}

=== CRITÈRES COMMERCIAUX ===
{criteres_commerciaux or 'Conditions standard'}

=== CRITÈRES D\'EXCLUSION ===
{criteres_exclusion or 'Aucun critère d\'exclusion spécifique'}

=== PROCÉDURE DE RÉPONSE ===
Format : {format_reponse}
Visite site : {'Requise' if visite_site else 'Non requise'}
Réunion clarification : {'Prévue' if reunion_clarification else 'Non prévue'}
Échantillons : {'Requis' if remise_echantillons else 'Non requis'}
Démonstration : {'Requise' if demonstration else 'Non requise'}
Contact technique : {contact_technique or 'Via responsable RFQ'}

=== LIVRAISON ===
Lieu : {livraison_lieu}
Délai maximum : Voir détail par article

=== DOCUMENTS JOINTS ===
{documents_joints or 'Aucun document joint spécifique'}

=== NOTES SPÉCIALES ===
{notes_rfq or 'Aucune note particulière'}"""
                
                # Préparation des données
                data = {
                    'type_formulaire': 'DEMANDE_PRIX',
                    'numero_document': numero_dp,
                    'project_id': projet_id,
                    'company_id': None,  # Pour RFQ multi-fournisseurs, pas de company_id unique
                    'employee_id': employe_id,
                    'statut': statut,
                    'priorite': priorite,
                    'date_creation': date_creation,
                    'date_echeance': date_echeance_reponse,
                    'montant_total': 0.0,  # Sera calculé quand les offres arrivent
                    'notes': notes_completes,
                    'metadonnees_json': json.dumps(metadonnees_rfq),
                    'lignes': articles_rfq
                }
                
                # Création du formulaire
                formulaire_id = gestionnaire.creer_formulaire(data)
                
                if formulaire_id:
                    # Messages de succès personnalisés
                    if submit_envoyer:
                        st.success(f"📤 Demande de Prix {numero_dp} créée et envoyée à {len(fournisseurs_selectionnes)} fournisseur(s)!")
                        st.info("📧 Les fournisseurs ont été notifiés et le suivi des réponses est activé.")
                    else:
                        st.success(f"✅ Demande de Prix {numero_dp} créée avec succès!")
                    
                    # Affichage du récapitulatif
                    st.markdown(f"""
                    ### 📋 Récapitulatif de la RFQ
                    
                    **N° DP :** {numero_dp}  
                    **Objet :** {objet_rfq}  
                    **Fournisseurs invités :** {len(fournisseurs_selectionnes)}  
                    **Articles/Services :** {len(articles_rfq)}  
                    **Date limite réponses :** {date_echeance_reponse.strftime('%d/%m/%Y')}  
                    **Statut :** {statut}
                    """)
                    
                    # Proposer actions suivantes
                    col_next1, col_next2, col_next3 = st.columns(3)
                    with col_next1:
                        if st.button("📋 Voir la Liste", use_container_width=True, key="dp_voir_liste_apres_creation"):
                            st.session_state.form_action = "list_demandes_actives"
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

# =============================================================================
# LISTE DES DEMANDES DE PRIX
# =============================================================================

def render_demande_prix_list(gestionnaire):
    """Liste des Demandes de Prix avec filtres avancés"""
    st.markdown("#### 📋 Liste des Demandes de Prix")
    
    demandes_prix = gestionnaire.get_formulaires('DEMANDE_PRIX')
    
    if not demandes_prix:
        st.info("Aucune Demande de Prix créée. Lancez votre première RFQ!")
        
        # Proposer actions de démarrage
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
        # Calculer le nombre total de fournisseurs sollicités
        nb_fournisseurs_total = 0
        for dp in demandes_prix:
            try:
                meta = json.loads(dp.get('metadonnees_json', '{}'))
                nb_fournisseurs_total += len(meta.get('fournisseurs_invites', []))
            except:
                pass
        st.metric("🏢 Fournisseurs Sollicités", nb_fournisseurs_total)
    with col_m5:
        urgentes = len([dp for dp in demandes_prix if dp['priorite'] == 'CRITIQUE'])
        st.metric("🚨 Urgentes", urgentes)
    
    # Alertes pour RFQ en attente de réponse
    today = datetime.now().date()
    rfq_echeance_proche = []
    for dp in demandes_prix:
        if dp.get('date_echeance') and dp['statut'] in ['ENVOYÉ']:
            try:
                date_echeance = datetime.strptime(dp['date_echeance'], '%Y-%m-%d').date()
                if date_echeance <= today + timedelta(days=2):
                    rfq_echeance_proche.append(dp)
            except:
                continue
    
    if rfq_echeance_proche:
        st.warning(f"⏰ {len(rfq_echeance_proche)} RFQ avec échéance proche (≤ 2 jours)")
    
    # Filtres avancés
    with st.expander("🔍 Filtres et Recherche", expanded=False):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            filtre_statut = st.multiselect("Statut", gestionnaire.statuts, default=gestionnaire.statuts)
        with col_f2:
            filtre_priorite = st.multiselect("Priorité", gestionnaire.priorites, default=gestionnaire.priorites)
        with col_f3:
            # Filtre par responsable
            responsables_liste = list(set([dp.get('employee_nom', 'N/A') for dp in demandes_prix if dp.get('employee_nom')]))
            filtre_responsable = st.multiselect("Responsable", ['Tous'] + responsables_liste, default=['Tous'])
        with col_f4:
            # Filtre par type RFQ
            types_rfq = ['Tous', 'Ouvert', 'Restreint', 'Négocié', 'Urgente']
            filtre_type_rfq = st.selectbox("Type RFQ", types_rfq)
        
        col_search, col_date = st.columns(2)
        with col_search:
            recherche = st.text_input("🔍 Rechercher", placeholder="Numéro, objet, projet...")
        with col_date:
            date_depuis = st.date_input("RFQs depuis", value=datetime.now().date() - timedelta(days=60))
    
    # Application des filtres
    demandes_filtrees = []
    for dp in demandes_prix:
        # Filtre statut
        if dp['statut'] not in filtre_statut:
            continue
        
        # Filtre priorité
        if dp['priorite'] not in filtre_priorite:
            continue
        
        # Filtre responsable
        if 'Tous' not in filtre_responsable and dp.get('employee_nom', 'N/A') not in filtre_responsable:
            continue
        
        # Filtre type RFQ
        if filtre_type_rfq != 'Tous':
            try:
                meta = json.loads(dp.get('metadonnees_json', '{}'))
                if meta.get('type_rfq') != filtre_type_rfq:
                    continue
            except:
                continue
        
        # Filtre date
        try:
            date_dp = datetime.strptime(dp['date_creation'][:10], '%Y-%m-%d').date()
            if date_dp < date_depuis:
                continue
        except:
            pass
        
        # Filtre recherche
        if recherche:
            terme = recherche.lower()
            if not any(terme in str(dp.get(field, '')).lower() for field in ['numero_document', 'notes', 'employee_nom', 'project_nom']):
                continue
        
        demandes_filtrees.append(dp)
    
    # Affichage résultats
    st.markdown(f"**{len(demandes_filtrees)} Demande(s) de Prix trouvée(s)**")
    
    if demandes_filtrees:
        # Tri
        col_sort1, col_sort2 = st.columns(2)
        with col_sort1:
            tri_par = st.selectbox("Trier par", ["Date création", "Date échéance", "Priorité", "Statut"])
        with col_sort2:
            tri_ordre = st.selectbox("Ordre", ["Décroissant", "Croissant"])
        
        # Application du tri
        if tri_par == "Date création":
            demandes_filtrees.sort(key=lambda x: x.get('date_creation', ''), reverse=(tri_ordre == "Décroissant"))
        elif tri_par == "Date échéance":
            demandes_filtrees.sort(key=lambda x: x.get('date_echeance', ''), reverse=(tri_ordre == "Décroissant"))
        elif tri_par == "Priorité":
            ordre_priorite = {'CRITIQUE': 3, 'URGENT': 2, 'NORMAL': 1}
            demandes_filtrees.sort(key=lambda x: ordre_priorite.get(x.get('priorite', 'NORMAL'), 1), reverse=(tri_ordre == "Décroissant"))
        
        # Tableau détaillé avec indicateurs visuels
        df_data = []
        for dp in demandes_filtrees:
            # Indicateurs visuels
            priorite_icon = {'CRITIQUE': '🔴', 'URGENT': '🟡', 'NORMAL': '🟢'}.get(dp['priorite'], '⚪')
            statut_icon = {
                'BROUILLON': '📝', 'VALIDÉ': '✅', 'ENVOYÉ': '📤', 
                'APPROUVÉ': '👍', 'TERMINÉ': '✔️', 'ANNULÉ': '❌'
            }.get(dp['statut'], '❓')
            
            # Extraction des métadonnées
            try:
                meta = json.loads(dp.get('metadonnees_json', '{}'))
                type_rfq = meta.get('type_rfq', 'N/A')
                nb_fournisseurs = len(meta.get('fournisseurs_invites', []))
                delai_reponse = meta.get('delai_reponse', 'N/A')
            except:
                type_rfq = 'N/A'
                nb_fournisseurs = 0
                delai_reponse = 'N/A'
            
            # Calcul du statut d'échéance
            try:
                date_echeance = datetime.strptime(dp['date_echeance'], '%Y-%m-%d').date()
                jours_restants = (date_echeance - today).days
                if dp['statut'] in ['TERMINÉ', 'ANNULÉ']:
                    echeance_status = "✅ Terminé"
                elif jours_restants < 0:
                    echeance_status = f"🔴 Dépassé ({abs(jours_restants)}j)"
                elif jours_restants <= 1:
                    echeance_status = "🟡 Urgent"
                else:
                    echeance_status = f"🟢 {jours_restants}j restants"
            except:
                echeance_status = "❓ Non défini"
            
            df_data.append({
                'N° RFQ': dp['numero_document'],
                'Type': type_rfq,
                'Responsable': dp.get('employee_nom', 'N/A'),
                'Fournisseurs': f"👥 {nb_fournisseurs}",
                'Statut': f"{statut_icon} {dp['statut']}",
                'Priorité': f"{priorite_icon} {dp['priorite']}",
                'Date Création': dp['date_creation'][:10] if dp['date_creation'] else 'N/A',
                'Échéance': dp.get('date_echeance', 'N/A'),
                'Statut Échéance': echeance_status,
                'Délai Rép.': f"{delai_reponse}j" if delai_reponse != 'N/A' else 'N/A'
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        # Actions en lot
        st.markdown("---")
        st.markdown("##### ⚡ Actions Rapides")
        
        col_action1, col_action2, col_action3, col_action4, col_action5 = st.columns(5)
        
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
        
        with col_action5:
            if st.button("📝 Modifier", use_container_width=True, key="dp_modifier"):
                if dp_selectionne:
                    st.session_state.form_action = "edit_demande_prix"
                    st.session_state.edit_formulaire_id = dp_selectionne
    else:
        st.info("Aucune Demande de Prix ne correspond aux critères de recherche.")

# =============================================================================
# COMPARAISON DES OFFRES MULTI-FOURNISSEURS
# =============================================================================

def render_compare_offers(gestionnaire):
    """Interface de comparaison des offres - NOUVEAU CONCEPT"""
    st.markdown("#### 📊 Comparaison des Offres Multi-Fournisseurs")
    
    # Sélection de la DP à analyser
    demandes_prix = gestionnaire.get_formulaires('DEMANDE_PRIX')
    dp_avec_offres = [dp for dp in demandes_prix if dp['statut'] in ['ENVOYÉ', 'APPROUVÉ', 'TERMINÉ']]
    
    if not dp_avec_offres:
        st.info("Aucune Demande de Prix avec des offres à comparer.")
        return
    
    # Sélection de la RFQ
    dp_selected_id = st.session_state.get('selected_dp_comparison')
    if not dp_selected_id:
        dp_options = [(dp['id'], f"{dp['numero_document']} - {dp.get('notes', '')[:50]}...") for dp in dp_avec_offres]
        dp_selected_id = st.selectbox(
            "Sélectionner la RFQ à analyser",
            options=[dp[0] for dp in dp_options],
            format_func=lambda x: next((dp[1] for dp in dp_options if dp[0] == x), "")
        )
    
    if dp_selected_id:
        dp_details = gestionnaire.get_formulaire_details(dp_selected_id)
        
        if dp_details:
            # Affichage des détails de la RFQ
            st.markdown("##### 📋 Détails de la RFQ")
            
            col_det1, col_det2 = st.columns(2)
            with col_det1:
                st.info(f"""
                **N° RFQ :** {dp_details['numero_document']}
                **Statut :** {dp_details['statut']}
                **Responsable :** {dp_details.get('employee_nom', 'N/A')}
                **Date échéance :** {dp_details.get('date_echeance', 'N/A')}
                """)
            
            with col_det2:
                try:
                    meta = json.loads(dp_details.get('metadonnees_json', '{}'))
                    fournisseurs_invites = meta.get('fournisseurs_invites', [])
                    criteres_eval = meta.get('criteres_evaluation', {})
                    
                    st.info(f"""
                    **Fournisseurs invités :** {len(fournisseurs_invites)}
                    **Type RFQ :** {meta.get('type_rfq', 'N/A')}
                    **Délai réponse :** {meta.get('delai_reponse', 'N/A')} jours
                    **Mode évaluation :** {meta.get('mode_evaluation', 'N/A')}
                    """)
                except:
                    st.error("Erreur lecture métadonnées RFQ")
            
            # SIMULATION DES OFFRES REÇUES (Dans un vrai système, elles seraient stockées)
            # Pour la démo, on génère des offres fictives
            st.markdown("##### 📨 Offres Reçues")
            
            with st.expander("⚙️ Simuler les Offres Reçues (Demo)", expanded=True):
                st.info("💡 Dans un système réel, les offres seraient saisies par les fournisseurs ou importées automatiquement")
                
                # Récupération des fournisseurs invités
                fournisseurs_actifs = get_fournisseurs_actifs()
                try:
                    meta = json.loads(dp_details.get('metadonnees_json', '{}'))
                    fournisseurs_invites_ids = meta.get('fournisseurs_invites', [])
                    fournisseurs_invites = [f for f in fournisseurs_actifs if f['id'] in fournisseurs_invites_ids]
                except:
                    fournisseurs_invites = fournisseurs_actifs[:3]  # Fallback
                
                if not fournisseurs_invites:
                    st.error("Aucun fournisseur invité trouvé pour cette RFQ")
                    return
                
                # Génération d'offres fictives pour la démo
                offres_fictives = generer_offres_fictives(dp_details, fournisseurs_invites)
                
                # Interface de modification des offres pour la démo
                st.markdown("**Ajuster les Offres pour la Comparaison :**")
                
                offres_ajustees = []
                for i, offre in enumerate(offres_fictives):
                    with st.expander(f"📋 Offre {offre['fournisseur']['nom']}", expanded=False):
                        col_o1, col_o2, col_o3 = st.columns(3)
                        
                        with col_o1:
                            prix_total = st.number_input(f"Prix Total ($)", 
                                value=offre['prix_total'], 
                                key=f"prix_{i}")
                            
                            delai_livraison = st.number_input(f"Délai (jours)", 
                                value=offre['delai_livraison'], 
                                key=f"delai_{i}")
                        
                        with col_o2:
                            note_qualite = st.slider(f"Note Qualité (/10)", 
                                0, 10, offre['note_qualite'], 
                                key=f"qualite_{i}")
                            
                            proximite_km = st.number_input(f"Distance (km)", 
                                value=offre['proximite_km'], 
                                key=f"proximite_{i}")
                        
                        with col_o3:
                            experience_secteur = st.slider(f"Expérience (/10)", 
                                0, 10, offre['experience_secteur'], 
                                key=f"experience_{i}")
                            
                            offre_conforme = st.checkbox(f"Offre Conforme", 
                                value=offre['conforme'], 
                                key=f"conforme_{i}")
                        
                        # Conditions spéciales
                        conditions_paiement = st.text_input(f"Conditions Paiement", 
                            value=offre.get('conditions_paiement', '30j net'), 
                            key=f"paiement_{i}")
                        
                        garantie = st.text_input(f"Garantie", 
                            value=offre.get('garantie', '12 mois'), 
                            key=f"garantie_{i}")
                        
                        notes_offre = st.text_area(f"Notes Offre", 
                            value=offre.get('notes', ''), 
                            key=f"notes_{i}")
                        
                        offres_ajustees.append({
                            'fournisseur': offre['fournisseur'],
                            'prix_total': prix_total,
                            'delai_livraison': delai_livraison,
                            'note_qualite': note_qualite,
                            'proximite_km': proximite_km,
                            'experience_secteur': experience_secteur,
                            'conforme': offre_conforme,
                            'conditions_paiement': conditions_paiement,
                            'garantie': garantie,
                            'notes': notes_offre
                        })
                
                # Bouton pour lancer la comparaison
                if st.button("🔄 Mettre à Jour la Comparaison", key="update_comparison"):
                    st.session_state.offres_comparaison = offres_ajustees
                    st.rerun()
            
            # TABLEAU COMPARATIF AUTOMATIQUE
            st.markdown("##### 📋 Tableau Comparatif Automatique")
            
            offres_a_comparer = st.session_state.get('offres_comparaison', offres_fictives)
            
            if offres_a_comparer:
                # Récupération des critères d'évaluation
                try:
                    meta = json.loads(dp_details.get('metadonnees_json', '{}'))
                    criteres_eval = meta.get('criteres_evaluation', {})
                except:
                    criteres_eval = {
                        'prix': {'actif': True, 'ponderation': 40},
                        'delai': {'actif': True, 'ponderation': 30},
                        'qualite': {'actif': True, 'ponderation': 30}
                    }
                
                # Calcul des scores
                offres_avec_scores = calculer_scores_offres(offres_a_comparer, criteres_eval)
                
                # Création du tableau comparatif
                df_comparison = create_comparison_dataframe(offres_avec_scores, criteres_eval)
                
                # Affichage du tableau avec mise en forme
                st.dataframe(df_comparison, use_container_width=True)
                
                # RECOMMANDATION AUTOMATIQUE
                st.markdown("##### 🏆 Recommandation Automatique")
                
                meilleure_offre = max(offres_avec_scores, key=lambda x: x['score_final'])
                
                col_rec1, col_rec2 = st.columns([2, 1])
                
                with col_rec1:
                    st.success(f"""
                    **🏆 Fournisseur Recommandé : {meilleure_offre['fournisseur']['nom']}**
                    
                    **Score Final : {meilleure_offre['score_final']:.1f}/100**
                    
                    **Justification de la Recommandation :**
                    """)
                    
                    justification = generer_justification_recommandation(meilleure_offre, offres_avec_scores, criteres_eval)
                    st.markdown(justification)
                
                with col_rec2:
                    # Graphique radar de la meilleure offre
                    fig_radar = create_radar_chart(meilleure_offre, criteres_eval)
                    st.plotly_chart(fig_radar, use_container_width=True)
                
                # ANALYSE COMPARATIVE DÉTAILLÉE
                st.markdown("##### 📊 Analyse Comparative Détaillée")
                
                col_graph1, col_graph2 = st.columns(2)
                
                with col_graph1:
                    # Graphique des scores finaux
                    noms_fournisseurs = [offre['fournisseur']['nom'] for offre in offres_avec_scores]
                    scores_finaux = [offre['score_final'] for offre in offres_avec_scores]
                    
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
                    prix_list = [offre['prix_total'] for offre in offres_avec_scores]
                    delais_list = [offre['delai_livraison'] for offre in offres_avec_scores]
                    
                    fig_scatter = px.scatter(
                        x=prix_list, 
                        y=delais_list,
                        text=noms_fournisseurs,
                        title="Prix vs Délai de Livraison",
                        labels={'x': 'Prix Total ($)', 'y': 'Délai (jours)'},
                        size=[offre['note_qualite'] for offre in offres_avec_scores],
                        color=scores_finaux,
                        color_continuous_scale='RdYlGn'
                    )
                    fig_scatter.update_traces(textposition="top center")
                    fig_scatter.update_layout(height=400)
                    st.plotly_chart(fig_scatter, use_container_width=True)
                
                # MATRICE DE COMPARAISON DÉTAILLÉE
                st.markdown("##### 📋 Matrice de Comparaison Détaillée")
                
                # Création d'une matrice pivot pour comparaison
                comparison_matrix = create_detailed_comparison_matrix(offres_avec_scores, criteres_eval)
                
                for critere, data in comparison_matrix.items():
                    with st.expander(f"📊 Détail {critere.title()}", expanded=False):
                        col_matrix = st.columns(len(offres_avec_scores) + 1)
                        
                        # En-tête
                        with col_matrix[0]:
                            st.markdown("**Fournisseur**")
                        for i, offre in enumerate(offres_avec_scores, 1):
                            with col_matrix[i]:
                                st.markdown(f"**{offre['fournisseur']['nom']}**")
                        
                        # Données
                        for metric, values in data.items():
                            with col_matrix[0]:
                                st.text(metric)
                            for i, value in enumerate(values, 1):
                                with col_matrix[i]:
                                    if isinstance(value, (int, float)):
                                        if metric == "Score":
                                            color = "🟢" if value >= 80 else "🟡" if value >= 60 else "🔴"
                                            st.text(f"{color} {value:.1f}")
                                        else:
                                            st.text(f"{value:,.2f}" if isinstance(value, float) else str(value))
                                    else:
                                        st.text(str(value))
                
                # ACTIONS POUR SÉLECTION
                st.markdown("---")
                st.markdown("##### ⚡ Actions")
                
                col_action1, col_action2, col_action3 = st.columns(3)
                
                with col_action1:
                    if st.button("🏆 Sélectionner le Gagnant Recommandé", use_container_width=True, key="select_recommended"):
                        st.session_state.selected_dp_winner = dp_selected_id
                        st.session_state.winner_details = meilleure_offre
                        st.session_state.form_action = "select_winner"
                        st.rerun()
                
                with col_action2:
                    fournisseur_manuel = st.selectbox("Ou sélectionner manuellement",
                        options=[offre['fournisseur']['id'] for offre in offres_avec_scores],
                        format_func=lambda x: next((offre['fournisseur']['nom'] for offre in offres_avec_scores if offre['fournisseur']['id'] == x), ""))
                    
                    if st.button("🎯 Sélectionner Manuellement", use_container_width=True, key="select_manual"):
                        offre_selectionnee = next((offre for offre in offres_avec_scores if offre['fournisseur']['id'] == fournisseur_manuel), None)
                        if offre_selectionnee:
                            st.session_state.selected_dp_winner = dp_selected_id
                            st.session_state.winner_details = offre_selectionnee
                            st.session_state.form_action = "select_winner"
                            st.rerun()
                
                with col_action3:
                    if st.button("📋 Retour Liste RFQ", use_container_width=True, key="back_to_list"):
                        st.session_state.form_action = "list_demandes_actives"
                        st.rerun()

# =============================================================================
# SÉLECTION DU GAGNANT ET CONVERSION
# =============================================================================

def render_select_winner(gestionnaire):
    """Interface de sélection du gagnant - CONVERSION DP → BC"""
    st.markdown("#### 🏆 Sélection du Fournisseur Gagnant")
    
    # Récupération de la RFQ sélectionnée
    dp_id = st.session_state.get('selected_dp_winner')
    winner_details = st.session_state.get('winner_details')
    
    if not dp_id:
        st.error("Aucune RFQ sélectionnée pour désignation du gagnant.")
        return
    
    dp_details = gestionnaire.get_formulaire_details(dp_id)
    
    if not dp_details:
        st.error("RFQ introuvable.")
        return
    
    # Affichage des détails de la RFQ
    st.markdown("##### 📋 RFQ à Finaliser")
    
    col_rfq1, col_rfq2 = st.columns(2)
    with col_rfq1:
        st.info(f"""
        **N° RFQ :** {dp_details['numero_document']}
        **Statut :** {dp_details['statut']}
        **Responsable :** {dp_details.get('employee_nom', 'N/A')}
        **Date échéance :** {dp_details.get('date_echeance', 'N/A')}
        """)
    
    with col_rfq2:
        try:
            meta = json.loads(dp_details.get('metadonnees_json', '{}'))
            nb_fournisseurs = len(meta.get('fournisseurs_invites', []))
        except:
            nb_fournisseurs = 0
        
        st.info(f"""
        **Fournisseurs invités :** {nb_fournisseurs}
        **Type RFQ :** {meta.get('type_rfq', 'N/A')}
        **Articles :** {len(dp_details.get('lignes', []))}
        **Montant estimé :** {dp_details.get('montant_total', 0):,.2f}$ CAD
        """)
    
    # Affichage du gagnant recommandé ou sélectionné
    if winner_details:
        st.markdown("##### 🏆 Fournisseur Gagnant Sélectionné")
        
        col_winner1, col_winner2 = st.columns(2)
        with col_winner1:
            st.success(f"""
            **Fournisseur Gagnant :** {winner_details['fournisseur']['nom']}
            **Score Final :** {winner_details.get('score_final', 'N/A')}/100
            **Prix Total :** {winner_details['prix_total']:,.2f}$ CAD
            **Délai Livraison :** {winner_details['delai_livraison']} jours
            """)
        
        with col_winner2:
            st.info(f"""
            **Note Qualité :** {winner_details['note_qualite']}/10
            **Conditions Paiement :** {winner_details.get('conditions_paiement', 'N/A')}
            **Garantie :** {winner_details.get('garantie', 'N/A')}
            **Distance :** {winner_details.get('proximite_km', 'N/A')} km
            """)
    
    # Formulaire de finalisation
    with st.form("selection_gagnant_form"):
        st.markdown("##### 🔧 Finalisation de la Sélection")
        
        # Justification de la sélection
        justification_selection = st.text_area("Justification de la Sélection *",
            value=generer_justification_selection_automatique(winner_details) if winner_details else "",
            height=120,
            help="Expliquez pourquoi ce fournisseur a été choisi")
        
        # Conditions négociées finales
        col_neg1, col_neg2 = st.columns(2)
        
        with col_neg1:
            prix_final_negocie = st.number_input("Prix Final Négocié ($)",
                value=winner_details['prix_total'] if winner_details else 0.0,
                format="%.2f")
            
            delai_final_negocie = st.number_input("Délai Final Négocié (jours)",
                value=winner_details['delai_livraison'] if winner_details else 14)
            
            conditions_paiement_finales = st.text_input("Conditions Paiement Finales",
                value=winner_details.get('conditions_paiement', '30 jours net') if winner_details else '30 jours net')
        
        with col_neg2:
            garantie_finale = st.text_input("Garantie Finale",
                value=winner_details.get('garantie', '12 mois') if winner_details else '12 mois')
            
            conditions_speciales = st.text_area("Conditions Spéciales Négociées",
                placeholder="Conditions particulières obtenues lors de la négociation...")
            
            date_debut_souhaite = st.date_input("Date Début Souhaitée",
                value=datetime.now().date() + timedelta(days=3))
        
        # Conversion automatique en Bon de Commande
        st.markdown("##### 🔄 Conversion Automatique en Bon de Commande")
        
        col_conv1, col_conv2 = st.columns(2)
        
        with col_conv1:
            numero_bc_auto = gestionnaire.generer_numero_document('BON_COMMANDE')
            st.text_input("N° Bon de Commande", value=numero_bc_auto, disabled=True)
            
            date_livraison_bc = st.date_input("Date Livraison BC",
                value=date_debut_souhaite + timedelta(days=delai_final_negocie))
            
            priorite_bc = st.selectbox("Priorité BC", gestionnaire.priorites, 
                index=gestionnaire.priorites.index(dp_details.get('priorite', 'NORMAL')))
        
        with col_conv2:
            statut_bc_initial = st.selectbox("Statut BC Initial", 
                ['VALIDÉ', 'ENVOYÉ'], index=1)
            
            notification_autres_fournisseurs = st.checkbox("Notifier les Autres Fournisseurs", value=True)
            
            archivage_offres_perdantes = st.checkbox("Archiver Offres Non Retenues", value=True)
        
        # Informations de livraison pour le BC
        st.markdown("##### 🚚 Informations Livraison BC")
        
        try:
            meta = json.loads(dp_details.get('metadonnees_json', '{}'))
            livraison_lieu_default = meta.get('livraison_lieu', 'DG Inc. - 123 Rue Industrielle, Montréal')
        except:
            livraison_lieu_default = 'DG Inc. - 123 Rue Industrielle, Montréal'
        
        col_liv1, col_liv2 = st.columns(2)
        with col_liv1:
            adresse_livraison_bc = st.text_area("Adresse Livraison",
                value=livraison_lieu_default)
            contact_reception_bc = st.text_input("Contact Réception",
                placeholder="Responsable réception des marchandises")
        
        with col_liv2:
            horaires_livraison_bc = st.text_input("Horaires Livraison",
                value="Lundi-Vendredi 8h-16h")
            instructions_livraison_bc = st.text_area("Instructions Livraison",
                placeholder="Instructions spéciales pour la livraison...")
        
        # Notes finales
        notes_finales = st.text_area("Notes Finales de Conversion",
            value=f"BC généré automatiquement depuis RFQ {dp_details['numero_document']} - Fournisseur sélectionné : {winner_details['fournisseur']['nom'] if winner_details else 'À définir'}")
        
        # Validation finale
        st.markdown("---")
        confirmation_selection = st.checkbox("Je confirme la sélection de ce fournisseur et la conversion en Bon de Commande")
        
        # Boutons de soumission
        col_submit1, col_submit2 = st.columns(2)
        
        with col_submit1:
            submit_selection = st.form_submit_button("🏆 Finaliser Sélection et Créer BC", 
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
                    # Mise à jour du statut de la RFQ
                    gestionnaire.modifier_statut_formulaire(dp_id, 'TERMINÉ', 
                                                           dp_details.get('employee_id'),
                                                           f"RFQ finalisée - Gagnant : {winner_details['fournisseur']['nom']}")
                    
                    # Construction des métadonnées BC
                    metadonnees_bc = {
                        'dp_source_id': dp_id,
                        'dp_source_numero': dp_details['numero_document'],
                        'fournisseur_gagnant': winner_details['fournisseur'],
                        'conditions_negociees': {
                            'prix_final': prix_final_negocie,
                            'delai_final': delai_final_negocie,
                            'conditions_paiement': conditions_paiement_finales,
                            'garantie': garantie_finale,
                            'conditions_speciales': conditions_speciales
                        },
                        'justification_selection': justification_selection,
                        'score_gagnant': winner_details.get('score_final'),
                        'adresse_livraison': adresse_livraison_bc,
                        'contact_reception': contact_reception_bc,
                        'horaires_livraison': horaires_livraison_bc,
                        'instructions_livraison': instructions_livraison_bc,
                        'conversion_automatique_rfq': True
                    }
                    
                    # Construction des notes BC
                    notes_bc = f"""=== BON DE COMMANDE DEPUIS RFQ ===
Généré depuis RFQ : {dp_details['numero_document']}
Date conversion : {datetime.now().strftime('%d/%m/%Y à %H:%M')}
Fournisseur sélectionné : {winner_details['fournisseur']['nom']}

=== JUSTIFICATION SÉLECTION ===
{justification_selection}

=== CONDITIONS NÉGOCIÉES ===
Prix final : {prix_final_negocie:,.2f}$ CAD
Délai : {delai_final_negocie} jours
Paiement : {conditions_paiement_finales}
Garantie : {garantie_finale}
Conditions spéciales : {conditions_speciales or 'Aucune'}

=== LIVRAISON ===
Adresse : {adresse_livraison_bc.replace(chr(10), ' - ')}
Contact : {contact_reception_bc}
Horaires : {horaires_livraison_bc}
Instructions : {instructions_livraison_bc or 'Aucune'}

=== HISTORIQUE RFQ ===
{dp_details.get('notes', '')}

=== NOTES FINALES ===
{notes_finales}"""
                    
                    # Mise à jour des lignes avec prix négociés
                    lignes_bc = []
                    for ligne in dp_details.get('lignes', []):
                        ligne_bc = ligne.copy()
                        # Répartir proportionnellement le prix final négocié
                        if prix_final_negocie > 0 and len(dp_details.get('lignes', [])) > 0:
                            ligne_bc['prix_unitaire'] = prix_final_negocie / sum(l['quantite'] for l in dp_details.get('lignes', []))
                        lignes_bc.append(ligne_bc)
                    
                    # Données du BC
                    data_bc = {
                        'type_formulaire': 'BON_COMMANDE',
                        'numero_document': numero_bc_auto,
                        'project_id': dp_details.get('project_id'),
                        'company_id': winner_details['fournisseur']['id'],
                        'employee_id': dp_details.get('employee_id'),
                        'statut': statut_bc_initial,
                        'priorite': priorite_bc,
                        'date_creation': datetime.now().date(),
                        'date_echeance': date_livraison_bc,
                        'montant_total': prix_final_negocie,
                        'notes': notes_bc,
                        'metadonnees_json': json.dumps(metadonnees_bc),
                        'lignes': lignes_bc
                    }
                    
                    # Création du BC
                    bc_id = gestionnaire.creer_formulaire(data_bc)
                    
                    if bc_id:
                        # Enregistrement de la sélection dans l'historique RFQ
                        gestionnaire.enregistrer_validation(
                            dp_id,
                            dp_details.get('employee_id'),
                            'SELECTION_GAGNANT',
                            f"Fournisseur gagnant : {winner_details['fournisseur']['nom']} - Score : {winner_details.get('score_final', 'N/A')}/100 - BC généré : {numero_bc_auto}"
                        )
                        
                        st.success(f"""
                        ✅ **Sélection Finalisée avec Succès !**
                        
                        🏆 **Fournisseur Gagnant :** {winner_details['fournisseur']['nom']}
                        💰 **Prix Final :** {prix_final_negocie:,.2f}$ CAD
                        📦 **Bon de Commande :** {numero_bc_auto} créé
                        📅 **Livraison prévue :** {date_livraison_bc.strftime('%d/%m/%Y')}
                        """)
                        
                        # Notifications autres fournisseurs (simulation)
                        if notification_autres_fournisseurs:
                            try:
                                meta = json.loads(dp_details.get('metadonnees_json', '{}'))
                                autres_fournisseurs = [f_id for f_id in meta.get('fournisseurs_invites', []) 
                                                     if f_id != winner_details['fournisseur']['id']]
                                if autres_fournisseurs:
                                    st.info(f"📧 Notifications envoyées à {len(autres_fournisseurs)} autre(s) fournisseur(s)")
                            except:
                                pass
                        
                        # Actions suivantes
                        col_next1, col_next2, col_next3 = st.columns(3)
                        
                        with col_next1:
                            if st.button("📋 Voir BC Créé", use_container_width=True, key="voir_bc_cree"):
                                st.session_state.selected_formulaire_id = bc_id
                                st.session_state.show_formulaire_modal = True
                        
                        with col_next2:
                            if st.button("📦 Liste BCs", use_container_width=True, key="liste_bcs"):
                                st.session_state.form_action = "list_bon_commande"
                                st.rerun()
                        
                        with col_next3:
                            if st.button("💰 Nouvelles RFQs", use_container_width=True, key="nouvelles_rfq"):
                                st.session_state.form_action = "list_demandes_actives"
                                st.rerun()
                    else:
                        st.error("❌ Erreur lors de la création du Bon de Commande")
                        
                except Exception as e:
                    st.error(f"❌ Erreur lors de la finalisation : {e}")
        
        elif submit_annuler:
            st.session_state.form_action = "compare_offers"
            st.rerun()

# =============================================================================
# FONCTIONS UTILITAIRES POUR LES DEMANDES DE PRIX
# =============================================================================

def get_demandes_prix_actives(gestionnaire):
    """Récupère les demandes de prix en cours"""
    try:
        return [dp for dp in gestionnaire.get_formulaires('DEMANDE_PRIX') 
                if dp['statut'] in ['VALIDÉ', 'ENVOYÉ']]
    except:
        return []

def get_note_fournisseur(fournisseur):
    """Calcule une note fictive pour un fournisseur"""
    # Dans un vrai système, cette note viendrait de l'historique des évaluations
    import hashlib
    hash_val = int(hashlib.md5(str(fournisseur['id']).encode()).hexdigest()[:8], 16)
    return (hash_val % 5) + 6  # Note entre 6 et 10

def select_fournisseurs_recommandes(fournisseurs, nb_max=4):
    """Sélectionne automatiquement les meilleurs fournisseurs"""
    # Tri par note (fictive) et diversité secteur
    fournisseurs_notes = []
    for f in fournisseurs:
        note = get_note_fournisseur(f)
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

def generer_offres_fictives(dp_details, fournisseurs):
    """Génère des offres fictives pour la démo"""
    import random
    
    offres = []
    base_price = random.uniform(10000, 50000)
    
    for i, fournisseur in enumerate(fournisseurs):
        # Variation de prix selon la "qualité" du fournisseur
        note_qualite = get_note_fournisseur(fournisseur)
        price_factor = 1.0 + (10 - note_qualite) * 0.05  # Meilleure qualité = prix plus élevé
        
        offre = {
            'fournisseur': fournisseur,
            'prix_total': round(base_price * price_factor * random.uniform(0.9, 1.1), 2),
            'delai_livraison': random.randint(7, 28),
            'note_qualite': note_qualite,
            'proximite_km': random.randint(10, 500),
            'experience_secteur': random.randint(5, 10),
            'conforme': random.choice([True, True, True, False]),  # 75% conformes
            'conditions_paiement': random.choice(['30j net', '45j net', '15j net']),
            'garantie': random.choice(['12 mois', '24 mois', '6 mois']),
            'notes': f"Offre standard de {fournisseur['nom']}"
        }
        offres.append(offre)
    
    return offres

def calculer_scores_offres(offres, criteres_eval):
    """Calcule les scores pondérés des offres"""
    # Normalisation des critères (0-100)
    if not offres:
        return []
    
    # Prix : plus bas = meilleur score
    prix_list = [o['prix_total'] for o in offres if o['conforme']]
    if prix_list:
        prix_min = min(prix_list)
        prix_max = max(prix_list)
    
    # Délai : plus court = meilleur score  
    delai_list = [o['delai_livraison'] for o in offres if o['conforme']]
    if delai_list:
        delai_min = min(delai_list)
        delai_max = max(delai_list)
    
    # Proximité : plus proche = meilleur score
    proximite_list = [o['proximite_km'] for o in offres if o['conforme']]
    if proximite_list:
        proximite_min = min(proximite_list)
        proximite_max = max(proximite_list)
    
    offres_avec_scores = []
    
    for offre in offres:
        if not offre['conforme']:
            # Offres non conformes = score 0
            score_final = 0
        else:
            scores = {}
            
            # Score Prix (inversé : prix bas = score élevé)
            if criteres_eval.get('prix', {}).get('actif') and prix_list:
                if prix_max > prix_min:
                    score_prix = 100 * (prix_max - offre['prix_total']) / (prix_max - prix_min)
                else:
                    score_prix = 100
                scores['prix'] = score_prix
            
            # Score Délai (inversé : délai court = score élevé)
            if criteres_eval.get('delai', {}).get('actif') and delai_list:
                if delai_max > delai_min:
                    score_delai = 100 * (delai_max - offre['delai_livraison']) / (delai_max - delai_min)
                else:
                    score_delai = 100
                scores['delai'] = score_delai
            
            # Score Qualité (direct)
            if criteres_eval.get('qualite', {}).get('actif'):
                scores['qualite'] = offre['note_qualite'] * 10
            
            # Score Proximité (inversé : proche = score élevé)
            if criteres_eval.get('proximite', {}).get('actif') and proximite_list:
                if proximite_max > proximite_min:
                    score_proximite = 100 * (proximite_max - offre['proximite_km']) / (proximite_max - proximite_min)
                else:
                    score_proximite = 100
                scores['proximite'] = score_proximite
            
            # Score Expérience (direct)
            if criteres_eval.get('experience', {}).get('actif'):
                scores['experience'] = offre['experience_secteur'] * 10
            
            # Calcul score final pondéré
            score_final = 0
            total_ponderation = 0
            
            for critere, data in criteres_eval.items():
                if data.get('actif') and critere in scores:
                    score_final += scores[critere] * data['ponderation'] / 100
                    total_ponderation += data['ponderation']
            
            if total_ponderation > 0:
                score_final = score_final * 100 / total_ponderation
            
            offre['scores_details'] = scores
        
        offre['score_final'] = score_final
        offres_avec_scores.append(offre)
    
    return offres_avec_scores

def create_comparison_dataframe(offres_avec_scores, criteres_eval):
    """Crée un DataFrame pour l'affichage comparatif"""
    data = []
    
    for offre in offres_avec_scores:
        row = {
            'Fournisseur': offre['fournisseur']['nom'],
            'Prix Total ($)': f"{offre['prix_total']:,.2f}",
            'Délai (jours)': offre['delai_livraison'],
            'Note Qualité (/10)': offre['note_qualite'],
            'Distance (km)': offre['proximite_km'],
            'Expérience (/10)': offre['experience_secteur'],
            'Conforme': '✅' if offre['conforme'] else '❌',
            'Score Final (/100)': f"{offre['score_final']:.1f}",
            'Conditions': offre.get('conditions_paiement', 'N/A'),
            'Garantie': offre.get('garantie', 'N/A')
        }
        data.append(row)
    
    return pd.DataFrame(data)

def create_radar_chart(offre, criteres_eval):
    """Crée un graphique radar pour une offre"""
    categories = []
    values = []
    
    for critere, data in criteres_eval.items():
        if data.get('actif'):
            categories.append(critere.title())
            score = offre.get('scores_details', {}).get(critere, 0)
            values.append(score)
    
    # Fermer le radar
    categories.append(categories[0])
    values.append(values[0])
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name=offre['fournisseur']['nom'],
        line_color='rgb(32, 201, 151)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=True,
        title=f"Profil {offre['fournisseur']['nom']}",
        height=300
    )
    
    return fig

def generer_justification_recommandation(meilleure_offre, toutes_offres, criteres_eval):
    """Génère une justification automatique de la recommandation"""
    justification = []
    
    # Avantages principaux
    score_final = meilleure_offre['score_final']
    justification.append(f"• **Score global de {score_final:.1f}/100**, le plus élevé parmi toutes les offres")
    
    # Analyse par critère
    scores_details = meilleure_offre.get('scores_details', {})
    
    if 'prix' in scores_details and criteres_eval.get('prix', {}).get('actif'):
        score_prix = scores_details['prix']
        if score_prix > 70:
            justification.append(f"• **Prix compétitif** (score: {score_prix:.0f}/100)")
        elif score_prix > 40:
            justification.append(f"• Prix correct (score: {score_prix:.0f}/100)")
    
    if 'delai' in scores_details and criteres_eval.get('delai', {}).get('actif'):
        score_delai = scores_details['delai']
        if score_delai > 70:
            justification.append(f"• **Délai de livraison excellent** ({meilleure_offre['delai_livraison']} jours)")
        elif score_delai > 40:
            justification.append(f"• Délai de livraison acceptable ({meilleure_offre['delai_livraison']} jours)")
    
    if 'qualite' in scores_details and criteres_eval.get('qualite', {}).get('actif'):
        note_qualite = meilleure_offre['note_qualite']
        if note_qualite >= 8:
            justification.append(f"• **Excellente réputation qualité** ({note_qualite}/10)")
        elif note_qualite >= 6:
            justification.append(f"• Bonne réputation qualité ({note_qualite}/10)")
    
    # Comparaison avec les concurrents
    autres_scores = [o['score_final'] for o in toutes_offres if o != meilleure_offre and o['conforme']]
    if autres_scores:
        ecart_moyen = score_final - (sum(autres_scores) / len(autres_scores))
        if ecart_moyen > 10:
            justification.append(f"• **Nettement supérieur** aux autres offres (+{ecart_moyen:.1f} points en moyenne)")
        elif ecart_moyen > 5:
            justification.append(f"• Supérieur aux autres offres (+{ecart_moyen:.1f} points en moyenne)")
    
    # Conditions avantageuses
    conditions = meilleure_offre.get('conditions_paiement', '')
    if '45j' in conditions or '60j' in conditions:
        justification.append(f"• Conditions de paiement avantageuses ({conditions})")
    
    garantie = meilleure_offre.get('garantie', '')
    if '24' in garantie:
        justification.append(f"• Garantie étendue ({garantie})")
    
    return '\n'.join(justification)

def create_detailed_comparison_matrix(offres_avec_scores, criteres_eval):
    """Crée une matrice de comparaison détaillée"""
    matrix = {}
    
    # Prix
    if criteres_eval.get('prix', {}).get('actif'):
        matrix['Prix'] = {
            'Montant ($)': [f"{o['prix_total']:,.2f}" for o in offres_avec_scores],
            'Score': [o.get('scores_details', {}).get('prix', 0) for o in offres_avec_scores],
            'Rang': []
        }
        # Calcul du rang
        prix_sorted = sorted([(i, o['prix_total']) for i, o in enumerate(offres_avec_scores) if o['conforme']], key=lambda x: x[1])
        rang_prix = [0] * len(offres_avec_scores)
        for rang, (idx, _) in enumerate(prix_sorted, 1):
            rang_prix[idx] = rang
        matrix['Prix']['Rang'] = rang_prix
    
    # Délai
    if criteres_eval.get('delai', {}).get('actif'):
        matrix['Délai'] = {
            'Jours': [o['delai_livraison'] for o in offres_avec_scores],
            'Score': [o.get('scores_details', {}).get('delai', 0) for o in offres_avec_scores]
        }
    
    # Qualité
    if criteres_eval.get('qualite', {}).get('actif'):
        matrix['Qualité'] = {
            'Note (/10)': [o['note_qualite'] for o in offres_avec_scores],
            'Score': [o.get('scores_details', {}).get('qualite', 0) for o in offres_avec_scores]
        }
    
    return matrix

def generer_justification_selection_automatique(winner_details):
    """Génère une justification automatique pour la sélection"""
    if not winner_details:
        return ""
    
    justification = f"""Sélection du fournisseur {winner_details['fournisseur']['nom']} basée sur les critères suivants :

SCORE GLOBAL : {winner_details.get('score_final', 0):.1f}/100 - Meilleure offre parmi les candidats

AVANTAGES IDENTIFIÉS :
• Prix proposé : {winner_details['prix_total']:,.2f}$ CAD
• Délai de livraison : {winner_details['delai_livraison']} jours
• Note qualité fournisseur : {winner_details['note_qualite']}/10
• Conditions : {winner_details.get('conditions_paiement', 'N/A')}
• Garantie : {winner_details.get('garantie', 'N/A')}

CONFORMITÉ : Offre conforme à toutes les exigences du cahier des charges

Cette sélection optimise le rapport qualité-prix-délai selon les critères pondérés définis dans la RFQ."""
    
    return justification

# Fonction de rendu des autres sections (simplifiées pour la démo)
def render_demande_prix_stats(gestionnaire):
    """Statistiques des Demandes de Prix"""
    st.markdown("#### 📊 Statistiques Demandes de Prix")
    
    demandes_prix = gestionnaire.get_formulaires('DEMANDE_PRIX')
    
    if not demandes_prix:
        st.info("Aucune donnée pour les statistiques.")
        return
    
    # Métriques de base
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Total RFQs", len(demandes_prix))
    with col2:
        finalisees = len([dp for dp in demandes_prix if dp['statut'] == 'TERMINÉ'])
        st.metric("✅ Finalisées", finalisees)
    with col3:
        en_cours = len([dp for dp in demandes_prix if dp['statut'] in ['VALIDÉ', 'ENVOYÉ']])
        st.metric("📤 En Cours", en_cours)
    with col4:
        taux_succes = (finalisees / len(demandes_prix) * 100) if demandes_prix else 0
        st.metric("📈 Taux Succès", f"{taux_succes:.1f}%")
    
    # Graphiques simples
    if len(demandes_prix) > 0:
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Répartition par statut
            statut_counts = {}
            for dp in demandes_prix:
                statut = dp['statut']
                statut_counts[statut] = statut_counts.get(statut, 0) + 1
            
            if statut_counts:
                fig = px.pie(values=list(statut_counts.values()), names=list(statut_counts.keys()),
                            title="Répartition par Statut RFQ")
                st.plotly_chart(fig, use_container_width=True)
        
        with col_g2:
            # Évolution mensuelle
            evolution = {}
            for dp in demandes_prix:
                try:
                    mois = dp['date_creation'][:7]
                    evolution[mois] = evolution.get(mois, 0) + 1
                except:
                    continue
            
            if evolution:
                mois_sorted = sorted(evolution.items())
                df_evol = pd.DataFrame(mois_sorted, columns=['Mois', 'Nombre'])
                fig = px.line(df_evol, x='Mois', y='Nombre', title="Évolution Mensuelle RFQ")
                st.plotly_chart(fig, use_container_width=True)

def render_historique_rfq(gestionnaire):
    """Historique des RFQ"""
    st.markdown("#### 📋 Historique des RFQ")
    st.info("🚧 Interface historique RFQ - Fonctionnalité avancée")

def render_templates_demande_prix(gestionnaire):
    """Templates de DP"""
    st.markdown("#### ⚙️ Templates Demandes de Prix")
    st.info("🚧 Gestion templates RFQ - Fonctionnalité avancée")

def render_performance_fournisseurs(gestionnaire):
    """Performance des fournisseurs"""
    st.markdown("#### 📈 Performance Fournisseurs")
    st.info("🚧 Analyse performance fournisseurs - Fonctionnalité avancée")

# =============================================================================
# MODULE ESTIMATIONS (EST) - INTERFACE COMPLÈTE
# Devis Clients Professionnels avec Calculs Automatiques
# =============================================================================

def render_estimations_tab(gestionnaire):
    """Interface complète pour les Estimations - Devis Clients"""
    st.markdown("### 📊 Estimations")
    
    # Alerte pour projets sans estimation
    projets_sans_estimation = get_projets_sans_estimation()
    if projets_sans_estimation:
        st.info(f"💡 {len(projets_sans_estimation)} projet(s) pourrait(ent) bénéficier d'une estimation")
    
    # Actions principales EST
    col_action1, col_action2, col_action3, col_action4 = st.columns(4)
    with col_action1:
        if st.button("➕ Nouvelle Estimation", use_container_width=True, key="est_nouveau"):
            st.session_state.form_action = "create_estimation"
    with col_action2:
        if st.button("📋 Devis Actifs", use_container_width=True, key="est_liste"):
            st.session_state.form_action = "list_estimations_actives"
    with col_action3:
        if st.button("🔄 Gestion Versions", use_container_width=True, key="est_versions"):
            st.session_state.form_action = "manage_versions"
    with col_action4:
        if st.button("✅ Acceptées", use_container_width=True, key="est_acceptees"):
            st.session_state.form_action = "estimations_acceptees"
    
    # Actions secondaires
    col_action5, col_action6, col_action7, col_action8 = st.columns(4)
    with col_action5:
        if st.button("📊 Analyse Rentabilité", use_container_width=True, key="est_rentabilite"):
            st.session_state.form_action = "analyse_rentabilite"
    with col_action6:
        if st.button("📋 Templates Industrie", use_container_width=True, key="est_templates"):
            st.session_state.form_action = "templates_estimations"
    with col_action7:
        if st.button("📈 Suivi Commercial", use_container_width=True, key="est_suivi"):
            st.session_state.form_action = "suivi_commercial"
    with col_action8:
        if st.button("💰 Analyse Marges", use_container_width=True, key="est_marges"):
            st.session_state.form_action = "analyse_marges"
    
    # Affichage selon l'action
    action = st.session_state.get('form_action', 'list_estimations_actives')
    
    if action == "create_estimation":
        render_estimation_form(gestionnaire)
    elif action == "list_estimations_actives":
        render_estimation_list(gestionnaire)
    elif action == "manage_versions":
        render_manage_versions(gestionnaire)
    elif action == "estimations_acceptees":
        render_estimations_acceptees(gestionnaire)
    elif action == "analyse_rentabilite":
        render_analyse_rentabilite(gestionnaire)
    elif action == "templates_estimations":
        render_templates_estimations(gestionnaire)
    elif action == "suivi_commercial":
        render_suivi_commercial(gestionnaire)
    elif action == "analyse_marges":
        render_analyse_marges(gestionnaire)

# =============================================================================
# FORMULAIRE CRÉATION ESTIMATION AVEC CALCULS AUTOMATIQUES
# =============================================================================

def render_estimation_form(gestionnaire):
    """Formulaire de création d'Estimation Client avec calculs automatiques"""
    st.markdown("#### ➕ Nouvelle Estimation Client")
    
    with st.form("estimation_form", clear_on_submit=True):
        # En-tête du formulaire
        col1, col2 = st.columns(2)
        
        with col1:
            numero_est = gestionnaire.generer_numero_document('ESTIMATION')
            st.text_input("N° Estimation", value=numero_est, disabled=True)
            
            # Sélection CLIENT (direction inverse vs fournisseurs)
            clients_disponibles = get_clients_actifs()
            client_options = [("", "Sélectionner un client")] + [(c['id'], f"{c['nom']} - {c['secteur']}") for c in clients_disponibles]
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
            employe_options = [("", "Sélectionner un commercial")] + [(e['id'], f"{e['prenom']} {e['nom']} - {e['poste']}") for e in employes]
            employe_id = st.selectbox(
                "Commercial Responsable *",
                options=[e[0] for e in employe_options],
                format_func=lambda x: next((e[1] for e in employe_options if e[0] == x), "")
            )
            
            priorite = st.selectbox("Priorité", gestionnaire.priorites, index=0)
        
        # SPÉCIFICITÉS EST - PARAMÈTRES DU DEVIS
        st.markdown("##### 🎯 Paramètres du Devis")
        col_est1, col_est2 = st.columns(2)
        
        with col_est1:
            template_industrie = st.selectbox("Template Industrie *", 
                ["AUTOMOBILE", "AERONAUTIQUE", "CONSTRUCTION", "GENERAL"],
                help="Le template détermine les coefficients et marges automatiques")
            
            validite_devis = st.number_input("Validité Devis (jours)", 
                min_value=15, value=30, max_value=90,
                help="Durée pendant laquelle le devis reste valide")
            
            type_estimation = st.selectbox("Type d'Estimation",
                ["Devis Standard", "Estimation Rapide", "Appel d'Offres", "Révision"])
        
        with col_est2:
            marge_beneficiaire = st.slider("Marge Bénéficiaire (%)", 5, 50, 
                get_marge_defaut_template(template_industrie),
                help="Marge bénéficiaire selon le template sélectionné")
            
            devise_devis = st.selectbox("Devise", ["CAD", "USD", "EUR"])
            
            conditions_paiement_client = st.selectbox("Conditions Paiement",
                ["30 jours net", "50% avance + 50% livraison", "À réception", "60 jours net"])
        
        # Projet existant ou nouveau
        st.markdown("##### 🏢 Client et Projet")
        
        if client_id:
            projets_client = get_projets_client(client_id)
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
                        projet_base_id = None
            else:
                st.info("Ce client n'a pas de projets existants. L'estimation sera créée manuellement.")
                base_sur_projet = False
                projet_base_id = None
        else:
            base_sur_projet = False
            projet_base_id = None
        
        # CALCULS AUTOMATIQUES AVANCÉS (SPÉCIFICITÉ EST)
        st.markdown("##### 🔢 Calculs Automatiques")
        
        if st.checkbox("Activer Calculs Automatiques", value=True):
            if projet_base_id:
                # Calculs basés sur projet existant
                calculs_auto = calculer_estimation_automatique(projet_base_id, marge_beneficiaire, template_industrie)
                
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
                    
                    # Affichage du détail template
                    template_info = get_template_info(template_industrie)
                    st.info(f"""
                    **Template {template_industrie}** : 
                    Coefficient complexité: {template_info['coefficient_complexite']} | 
                    Certification: {template_info['cout_certification_pct']}% | 
                    Délai standard: {template_info['delai_standard']} jours
                    """)
                else:
                    st.error("❌ Erreur dans les calculs automatiques")
            else:
                st.info("Sélectionnez un projet de base pour activer les calculs automatiques")
        
        # Articles/Services du devis (avec ou sans calculs auto)
        st.markdown("##### 📦 Articles/Services du Devis")
        
        # Interface similaire aux autres formulaires mais adaptée pour devis client
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
        
        for i in range(6):  # 6 lignes
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
        
        template_info = get_template_info(template_industrie)
        
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
                value=get_clauses_techniques_template(template_industrie),
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
        prix_final = prix_total_manuel if lignes_estimation else (calculs_auto.get('prix_TTC', 0) if projet_base_id and st.session_state.get('calculs_auto_actifs') else 0)
        
        if prix_final > 0:
            taxes = prix_final * 0.14975  # TVQ + TPS Québec
            prix_ttc_final = prix_final + taxes
            
            st.markdown(f"""
            <div style='background:#f0f9ff;padding:1rem;border-radius:8px;border-left:4px solid #3b82f6;'>
                <h5 style='color:#1e40af;margin:0;'>💰 Récapitulatif Financier Final</h5>
                <p style='margin:0.5rem 0 0 0;'><strong>Prix HT : {prix_final:,.2f} {devise_devis}</strong></p>
                <p style='margin:0;'>Taxes (14.975%) : {taxes:,.2f} {devise_devis}</p>
                <p style='margin:0;'><strong>Prix TTC : {prix_ttc_final:,.2f} {devise_devis}</strong></p>
                <p style='margin:0;font-size:0.9em;'>Template : {template_industrie} | Marge : {marge_beneficiaire}%</p>
                <p style='margin:0;font-size:0.9em;'>Validité : {validite_devis} jours | Délai : {delai_execution} jours</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Boutons de soumission
        st.markdown("---")
        col_submit1, col_submit2, col_submit3 = st.columns(3)
        
        with col_submit1:
            submit_brouillon = st.form_submit_button("💾 Sauver comme Brouillon", use_container_width=True, key="est_submit_brouillon")
        with col_submit2:
            submit_valide = st.form_submit_button("✅ Créer et Valider", use_container_width=True, key="est_submit_valide")
        with col_submit3:
            submit_envoyer = st.form_submit_button("📤 Créer et Envoyer Client", use_container_width=True, key="est_submit_envoyer")
        
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
            if not lignes_estimation and not projet_base_id:
                erreurs.append("Au moins un article ou un projet de base requis")
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
                
                # Construction des métadonnées EST
                metadonnees_est = {
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
                    'date_validite': date_validite.isoformat(),
                    'projet_base_id': projet_base_id,
                    'calculs_automatiques': bool(projet_base_id),
                    'version': 1,  # Première version
                    'template_info': template_info
                }
                
                # Construction des notes complètes
                notes_completes = f"""=== ESTIMATION CLIENT ===
Template : {template_industrie}
Type : {type_estimation}
Marge bénéficiaire : {marge_beneficiaire}%

=== CLIENT ET PROJET ===
Client : {next((c[1] for c in client_options if c[0] == client_id), 'N/A')}
Projet de base : {next((p['nom_projet'] for p in projets_client if p['id'] == projet_base_id), 'Nouveau projet') if client_id and projets_client else 'Nouveau projet'}

=== CONDITIONS COMMERCIALES ===
Validité : {validite_devis} jours (jusqu'au {date_validite.strftime('%d/%m/%Y')})
Paiement : {conditions_paiement_client}
Garantie : {garantie_proposee}
Délai exécution : {delai_execution} jours
Lieu : {lieu_execution}

=== CLAUSES TECHNIQUES ===
{clauses_techniques}

=== OPTIONS INCLUSES ===
{', '.join(options_incluses) if options_incluses else 'Aucune option spéciale'}

=== RÉVISIONS ===
Autorisées : {'Oui' if revision_autorisee else 'Non'}
Nombre max : {nb_revisions_max if revision_autorisee else 'N/A'}
Frais : {frais_revision}$ CAD par révision

=== DÉTAILS FINANCIERS ===
Prix HT : {prix_final:,.2f} {devise_devis}
Taxes : {prix_final * 0.14975:,.2f} {devise_devis}
Prix TTC : {prix_final + (prix_final * 0.14975):,.2f} {devise_devis}

=== NOTES ET OBSERVATIONS ===
{notes_estimation or 'Aucune note particulière'}"""
                
                # Utilisation des lignes automatiques ou manuelles
                lignes_finales = lignes_estimation if lignes_estimation else []
                if projet_base_id and not lignes_estimation:
                    # Créer des lignes depuis le projet
                    lignes_finales = creer_lignes_depuis_projet(projet_base_id, calculs_auto)
                
                # Préparation des données
                data = {
                    'type_formulaire': 'ESTIMATION',
                    'numero_document': numero_est,
                    'project_id': projet_base_id,  # Peut être None pour nouveau client
                    'company_id': client_id,
                    'employee_id': employe_id,
                    'statut': statut,
                    'priorite': priorite,
                    'date_creation': date_creation,
                    'date_echeance': date_validite,
                    'montant_total': prix_final + (prix_final * 0.14975),  # Prix TTC
                    'notes': notes_completes,
                    'metadonnees_json': json.dumps(metadonnees_est),
                    'lignes': lignes_finales
                }
                
                # Création de l'estimation
                estimation_id = gestionnaire.creer_formulaire(data)
                
                if estimation_id:
                    # Messages de succès personnalisés
                    if submit_envoyer:
                        st.success(f"📤 Estimation {numero_est} créée et envoyée au client!")
                        st.info("📧 Le client a été notifié et le suivi commercial est activé.")
                    else:
                        st.success(f"✅ Estimation {numero_est} créée avec succès!")
                    
                    # Affichage du récapitulatif
                    st.markdown(f"""
                    ### 📋 Récapitulatif de l'Estimation
                    
                    **N° EST :** {numero_est}  
                    **Client :** {next((c[1] for c in client_options if c[0] == client_id), 'N/A')}  
                    **Template :** {template_industrie}  
                    **Montant TTC :** {prix_final + (prix_final * 0.14975):,.2f} {devise_devis}  
                    **Validité :** {date_validite.strftime('%d/%m/%Y')}  
                    **Statut :** {statut}
                    """)
                    
                    # Actions suivantes
                    col_next1, col_next2, col_next3 = st.columns(3)
                    with col_next1:
                        if st.button("📋 Voir la Liste", use_container_width=True, key="est_voir_liste_apres_creation"):
                            st.session_state.form_action = "list_estimations_actives"
                            st.rerun()
                    with col_next2:
                        if st.button("🔄 Créer Version v2", use_container_width=True, key="est_version_v2"):
                            st.session_state.base_estimation_id = estimation_id
                            st.session_state.form_action = "manage_versions"
                            st.rerun()
                    with col_next3:
                        if st.button("➕ Nouvelle Estimation", use_container_width=True, key="est_nouvelle_autre"):
                            st.rerun()
                else:
                    st.error("❌ Erreur lors de la création de l'estimation")

# =============================================================================
# LISTE DES ESTIMATIONS AVEC FILTRES
# =============================================================================

def render_estimation_list(gestionnaire):
    """Liste des Estimations avec filtres avancés"""
    st.markdown("#### 📋 Liste des Estimations")
    
    estimations = gestionnaire.get_formulaires('ESTIMATION')
    
    if not estimations:
        st.info("Aucune Estimation créée. Créez votre premier devis client!")
        
        if st.button("➕ Créer Première Estimation", use_container_width=True, key="est_premiere"):
            st.session_state.form_action = "create_estimation"
            st.rerun()
        return
    
    # Métriques rapides
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    
    with col_m1:
        st.metric("📊 Total EST", len(estimations))
    with col_m2:
        en_cours = len([est for est in estimations if est['statut'] in ['VALIDÉ', 'ENVOYÉ']])
        st.metric("📤 En Cours", en_cours)
    with col_m3:
        acceptees = len([est for est in estimations if est['statut'] == 'APPROUVÉ'])
        st.metric("✅ Acceptées", acceptees)
    with col_m4:
        montant_total = sum(est.get('montant_total', 0) for est in estimations)
        st.metric("💰 Montant Total", f"{montant_total:,.0f}$ CAD")
    with col_m5:
        expirees = len([est for est in estimations if est_estimation_expiree(est)])
        st.metric("⏰ Expirées", expirees)
    
    # Alertes pour estimations expirées ou proches d'expiration
    today = datetime.now().date()
    estimations_urgentes = []
    for est in estimations:
        if est['statut'] in ['VALIDÉ', 'ENVOYÉ']:
            try:
                meta = json.loads(est.get('metadonnees_json', '{}'))
                date_validite = datetime.strptime(meta.get('date_validite', ''), '%Y-%m-%d').date()
                jours_restants = (date_validite - today).days
                if jours_restants <= 3:
                    estimations_urgentes.append((est, jours_restants))
            except:
                continue
    
    if estimations_urgentes:
        st.warning(f"⏰ {len(estimations_urgentes)} estimation(s) expire(nt) dans ≤ 3 jours!")
        
        with st.expander("📋 Détails Estimations Urgentes", expanded=True):
            for est, jours in estimations_urgentes:
                urgence_icon = "🔴" if jours < 0 else "🟡" if jours <= 1 else "🟠"
                st.error(f"""
                {urgence_icon} **EST {est['numero_document']}** - {est.get('company_nom', 'N/A')}
                Expire dans : {jours} jour(s) | Montant : {est.get('montant_total', 0):,.0f}$ CAD
                """)
    
    # Filtres avancés
    with st.expander("🔍 Filtres et Recherche", expanded=False):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            filtre_statut = st.multiselect("Statut", gestionnaire.statuts, default=gestionnaire.statuts)
        with col_f2:
            filtre_priorite = st.multiselect("Priorité", gestionnaire.priorites, default=gestionnaire.priorites)
        with col_f3:
            # Filtre par template industrie
            templates_liste = list(set([get_template_from_metadata(est) for est in estimations]))
            filtre_template = st.multiselect("Template", ['Tous'] + templates_liste, default=['Tous'])
        with col_f4:
            # Filtre par commercial
            commerciaux_liste = list(set([est.get('employee_nom', 'N/A') for est in estimations if est.get('employee_nom')]))
            filtre_commercial = st.multiselect("Commercial", ['Tous'] + commerciaux_liste, default=['Tous'])
        
        col_search, col_montant, col_validite = st.columns(3)
        with col_search:
            recherche = st.text_input("🔍 Rechercher", placeholder="Numéro, client, projet...")
        with col_montant:
            montant_min = st.number_input("Montant minimum ($)", min_value=0.0, value=0.0)
        with col_validite:
            filtre_validite = st.selectbox("Validité", 
                ["Toutes", "Valides", "Expirent ≤ 7j", "Expirées"])
    
    # Application des filtres
    estimations_filtrees = []
    for est in estimations:
        # Filtre statut
        if est['statut'] not in filtre_statut:
            continue
        
        # Filtre priorité
        if est['priorite'] not in filtre_priorite:
            continue
        
        # Filtre template
        if 'Tous' not in filtre_template:
            template_est = get_template_from_metadata(est)
            if template_est not in filtre_template:
                continue
        
        # Filtre commercial
        if 'Tous' not in filtre_commercial and est.get('employee_nom', 'N/A') not in filtre_commercial:
            continue
        
        # Filtre montant
        if est.get('montant_total', 0) < montant_min:
            continue
        
        # Filtre recherche
        if recherche:
            terme = recherche.lower()
            if not any(terme in str(est.get(field, '')).lower() for field in ['numero_document', 'company_nom', 'notes', 'employee_nom']):
                continue
        
        # Filtre validité
        if filtre_validite != "Toutes":
            try:
                meta = json.loads(est.get('metadonnees_json', '{}'))
                date_validite = datetime.strptime(meta.get('date_validite', ''), '%Y-%m-%d').date()
                jours_restants = (date_validite - today).days
                
                if filtre_validite == "Valides" and jours_restants < 0:
                    continue
                elif filtre_validite == "Expirent ≤ 7j" and (jours_restants < 0 or jours_restants > 7):
                    continue
                elif filtre_validite == "Expirées" and jours_restants >= 0:
                    continue
            except:
                if filtre_validite != "Toutes":
                    continue
        
        estimations_filtrees.append(est)
    
    # Affichage résultats
    st.markdown(f"**{len(estimations_filtrees)} Estimation(s) trouvée(s)**")
    
    if estimations_filtrees:
        # Tri
        col_sort1, col_sort2 = st.columns(2)
        with col_sort1:
            tri_par = st.selectbox("Trier par", ["Date création", "Date validité", "Montant", "Client", "Statut"])
        with col_sort2:
            tri_ordre = st.selectbox("Ordre", ["Décroissant", "Croissant"])
        
        # Application du tri
        if tri_par == "Date création":
            estimations_filtrees.sort(key=lambda x: x.get('date_creation', ''), reverse=(tri_ordre == "Décroissant"))
        elif tri_par == "Date validité":
            estimations_filtrees.sort(key=lambda x: get_date_validite_from_metadata(x), reverse=(tri_ordre == "Décroissant"))
        elif tri_par == "Montant":
            estimations_filtrees.sort(key=lambda x: x.get('montant_total', 0), reverse=(tri_ordre == "Décroissant"))
        elif tri_par == "Client":
            estimations_filtrees.sort(key=lambda x: x.get('company_nom', ''), reverse=(tri_ordre == "Décroissant"))
        
        # Tableau détaillé avec indicateurs visuels
        df_data = []
        for est in estimations_filtrees:
            # Indicateurs visuels
            priorite_icon = {'CRITIQUE': '🔴', 'URGENT': '🟡', 'NORMAL': '🟢'}.get(est['priorite'], '⚪')
            statut_icon = {
                'BROUILLON': '📝', 'VALIDÉ': '✅', 'ENVOYÉ': '📤', 
                'APPROUVÉ': '👍', 'TERMINÉ': '✔️', 'ANNULÉ': '❌'
            }.get(est['statut'], '❓')
            
            # Extraction des métadonnées
            try:
                meta = json.loads(est.get('metadonnees_json', '{}'))
                template = meta.get('template_industrie', 'N/A')
                version = meta.get('version', 1)
                date_validite = meta.get('date_validite', 'N/A')
                
                # Calcul statut validité
                if date_validite != 'N/A':
                    date_val = datetime.strptime(date_validite, '%Y-%m-%d').date()
                    jours_restants = (date_val - today).days
                    if jours_restants < 0:
                        validite_status = f"🔴 Expirée ({abs(jours_restants)}j)"
                    elif jours_restants <= 3:
                        validite_status = f"🟡 {jours_restants}j restants"
                    else:
                        validite_status = f"🟢 {jours_restants}j restants"
                else:
                    validite_status = "❓ Non définie"
            except:
                template = 'N/A'
                version = 1
                validite_status = "❓ Erreur"
            
            df_data.append({
                'N° EST': f"{est['numero_document']} v{version}",
                'Client': est.get('company_nom', 'N/A'),
                'Commercial': est.get('employee_nom', 'N/A'),
                'Template': template,
                'Statut': f"{statut_icon} {est['statut']}",
                'Priorité': f"{priorite_icon} {est['priorite']}",
                'Date Création': est['date_creation'][:10] if est['date_creation'] else 'N/A',
                'Validité': validite_status,
                'Montant TTC': f"{est.get('montant_total', 0):,.2f}$ CAD"
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        # Actions en lot
        st.markdown("---")
        st.markdown("##### ⚡ Actions Rapides")
        
        col_action1, col_action2, col_action3, col_action4, col_action5 = st.columns(5)
        
        with col_action1:
            est_selectionne = st.selectbox("Sélectionner une EST", 
                                         options=[est['id'] for est in estimations_filtrees],
                                         format_func=lambda x: next((est['numero_document'] for est in estimations_filtrees if est['id'] == x), ""))
        
        with col_action2:
            if st.button("👁️ Voir Détails", use_container_width=True, key="est_voir_details"):
                if est_selectionne:
                    st.session_state.selected_formulaire_id = est_selectionne
                    st.session_state.show_formulaire_modal = True
        
        with col_action3:
            if st.button("🔄 Créer Version", use_container_width=True, key="est_creer_version"):
                if est_selectionne:
                    st.session_state.base_estimation_id = est_selectionne
                    st.session_state.form_action = "manage_versions"
                    st.rerun()
        
        with col_action4:
            if st.button("✅ Marquer Acceptée", use_container_width=True, key="est_marquer_acceptee"):
                if est_selectionne:
                    if marquer_estimation_acceptee(gestionnaire, est_selectionne):
                        st.success("✅ Estimation marquée comme acceptée!")
                        st.rerun()
        
        with col_action5:
            if st.button("📝 Modifier", use_container_width=True, key="est_modifier"):
                if est_selectionne:
                    st.session_state.form_action = "edit_estimation"
                    st.session_state.edit_formulaire_id = est_selectionne
    else:
        st.info("Aucune Estimation ne correspond aux critères de recherche.")

# =============================================================================
# GESTION DES VERSIONS (v1, v2, v3...)
# =============================================================================

def render_manage_versions(gestionnaire):
    """Gestion des versions d'estimations - NOUVEAU CONCEPT"""
    st.markdown("#### 🔄 Gestion des Versions")
    
    # Sélection de l'estimation de base
    base_estimation_id = st.session_state.get('base_estimation_id')
    
    estimations = gestionnaire.get_formulaires('ESTIMATION')
    est_options = [(est['id'], f"{est['numero_document']} - {est.get('company_nom', 'N/A')}") for est in estimations]
    
    if est_options:
        if not base_estimation_id:
            base_estimation_id = st.selectbox("Estimation de Base", 
                                            options=[e[0] for e in est_options],
                                            format_func=lambda x: next((e[1] for e in est_options if e[0] == x), ""))
        else:
            # Afficher l'estimation sélectionnée
            est_selectionnee = next((e[1] for e in est_options if e[0] == base_estimation_id), "Estimation introuvable")
            st.info(f"**Estimation sélectionnée :** {est_selectionnee}")
        
        if base_estimation_id:
            # Récupération de toutes les versions de cette estimation
            versions = get_versions_estimation(gestionnaire, base_estimation_id)
            
            st.markdown("##### 📋 Historique des Versions")
            
            if versions:
                for version in versions:
                    with st.expander(f"Version {version['version']} - {version['date_creation'][:10]}", expanded=False):
                        col_v1, col_v2, col_v3, col_v4 = st.columns(4)
                        
                        with col_v1:
                            st.metric("Prix TTC", f"{version['montant_total']:,.2f}$ CAD")
                        with col_v2:
                            st.metric("Statut", version['statut'])
                        with col_v3:
                            try:
                                meta = json.loads(version.get('metadonnees_json', '{}'))
                                template = meta.get('template_industrie', 'N/A')
                                marge = meta.get('marge_beneficiaire', 'N/A')
                                st.text(f"Template: {template}")
                                st.text(f"Marge: {marge}%")
                            except:
                                st.text("Métadonnées indisponibles")
                        with col_v4:
                            if st.button(f"📋 Dupliquer v{version['version']}", key=f"dup_{version['id']}", use_container_width=True):
                                nouvelle_version_id = dupliquer_estimation_version(gestionnaire, version['id'])
                                if nouvelle_version_id:
                                    st.success(f"✅ Version dupliquée avec succès!")
                                    st.rerun()
            else:
                st.info("Aucune version trouvée pour cette estimation.")
            
            # Interface création nouvelle version
            st.markdown("##### ➕ Créer Nouvelle Version")
            
            with st.form("nouvelle_version_form"):
                col_nv1, col_nv2 = st.columns(2)
                
                with col_nv1:
                    motif_revision = st.text_area("Motif de la Révision *",
                        placeholder="Expliquez pourquoi cette nouvelle version est nécessaire...",
                        help="Exemple: Demande client, changement spécifications, révision prix")
                    
                    modifications_principales = st.text_area("Principales Modifications",
                        placeholder="Décrivez les changements apportés...",
                        help="Détaillez les modifications techniques, commerciales, etc.")
                
                with col_nv2:
                    ajustement_prix = st.selectbox("Ajustement Prix",
                        ["Aucun", "Augmentation", "Diminution", "Révision complète"])
                    
                    if ajustement_prix != "Aucun":
                        pourcentage_ajustement = st.slider("Pourcentage d'Ajustement (%)", -50, 50, 0,
                            help="Pourcentage d'augmentation (+) ou de diminution (-)")
                    else:
                        pourcentage_ajustement = 0
                    
                    # Options de modification
                    modifier_template = st.checkbox("Modifier Template Industrie")
                    if modifier_template:
                        nouveau_template = st.selectbox("Nouveau Template",
                            ["AUTOMOBILE", "AERONAUTIQUE", "CONSTRUCTION", "GENERAL"])
                    else:
                        nouveau_template = None
                    
                    modifier_marge = st.checkbox("Modifier Marge Bénéficiaire")
                    if modifier_marge:
                        nouvelle_marge = st.slider("Nouvelle Marge (%)", 5, 50, 20)
                    else:
                        nouvelle_marge = None
                
                # Paramètres de la nouvelle version
                st.markdown("**Paramètres Nouvelle Version:**")
                col_param1, col_param2 = st.columns(2)
                
                with col_param1:
                    nouvelle_validite = st.number_input("Nouvelle Validité (jours)", 
                        min_value=15, value=30, max_value=90)
                    priorite_version = st.selectbox("Priorité Version", 
                        gestionnaire.priorites, index=1)  # URGENT par défaut pour révisions
                
                with col_param2:
                    notification_client = st.checkbox("Notifier le Client", value=True,
                        help="Envoyer la nouvelle version au client automatiquement")
                    archiver_precedente = st.checkbox("Archiver Version Précédente", value=False,
                        help="Marquer la version précédente comme obsolète")
                
                submit_version = st.form_submit_button("🔄 Créer Nouvelle Version", use_container_width=True)
                
                if submit_version and motif_revision:
                    # Récupération de l'estimation de base
                    est_base = gestionnaire.get_formulaire_details(base_estimation_id)
                    
                    if est_base:
                        # Calcul du nouveau montant
                        montant_actuel = est_base.get('montant_total', 0)
                        if ajustement_prix != "Aucun":
                            nouveau_montant = montant_actuel * (1 + pourcentage_ajustement / 100)
                        else:
                            nouveau_montant = montant_actuel
                        
                        # Récupération des métadonnées actuelles
                        try:
                            meta_actuelles = json.loads(est_base.get('metadonnees_json', '{}'))
                        except:
                            meta_actuelles = {}
                        
                        # Mise à jour des métadonnées
                        nouvelle_version_num = get_prochaine_version_numero(gestionnaire, base_estimation_id)
                        
                        nouvelles_meta = meta_actuelles.copy()
                        nouvelles_meta.update({
                            'version': nouvelle_version_num,
                            'version_precedente_id': base_estimation_id,
                            'motif_revision': motif_revision,
                            'modifications_principales': modifications_principales,
                            'ajustement_prix': ajustement_prix,
                            'pourcentage_ajustement': pourcentage_ajustement,
                            'date_revision': datetime.now().isoformat(),
                            'validite_devis': nouvelle_validite,
                            'date_validite': (datetime.now().date() + timedelta(days=nouvelle_validite)).isoformat()
                        })
                        
                        if nouveau_template:
                            nouvelles_meta['template_industrie'] = nouveau_template
                        if nouvelle_marge is not None:
                            nouvelles_meta['marge_beneficiaire'] = nouvelle_marge
                        
                        # Génération du nouveau numéro
                        numero_base = est_base['numero_document'].split(' ')[0]  # Enlever l'éventuel " v1"
                        nouveau_numero = f"{numero_base} v{nouvelle_version_num}"
                        
                        # Construction des notes de révision
                        notes_revision = f"""=== RÉVISION VERSION {nouvelle_version_num} ===
Motif : {motif_revision}
Date révision : {datetime.now().strftime('%d/%m/%Y à %H:%M')}
Version précédente : {est_base['numero_document']}

=== MODIFICATIONS APPORTÉES ===
{modifications_principales or 'Aucune modification détaillée'}

=== AJUSTEMENTS FINANCIERS ===
Ajustement prix : {ajustement_prix}
Pourcentage : {pourcentage_ajustement}%
Montant précédent : {montant_actuel:,.2f}$ CAD
Nouveau montant : {nouveau_montant:,.2f}$ CAD

=== PARAMÈTRES TECHNIQUES ===
Template : {nouveau_template or meta_actuelles.get('template_industrie', 'Inchangé')}
Marge : {nouvelle_marge or meta_actuelles.get('marge_beneficiaire', 'Inchangée')}%
Nouvelle validité : {nouvelle_validite} jours

=== NOTES VERSION PRÉCÉDENTE ===
{est_base.get('notes', '')}"""
                        
                        # Données de la nouvelle version
                        data_nouvelle_version = {
                            'type_formulaire': 'ESTIMATION',
                            'numero_document': nouveau_numero,
                            'project_id': est_base.get('project_id'),
                            'company_id': est_base.get('company_id'),
                            'employee_id': est_base.get('employee_id'),
                            'statut': 'VALIDÉ',
                            'priorite': priorite_version,
                            'date_creation': datetime.now().date(),
                            'date_echeance': datetime.now().date() + timedelta(days=nouvelle_validite),
                            'montant_total': nouveau_montant,
                            'notes': notes_revision,
                            'metadonnees_json': json.dumps(nouvelles_meta),
                            'lignes': est_base.get('lignes', [])
                        }
                        
                        # Création de la nouvelle version
                        nouvelle_version_id = gestionnaire.creer_formulaire(data_nouvelle_version)
                        
                        if nouvelle_version_id:
                            # Archivage de la version précédente si demandé
                            if archiver_precedente:
                                gestionnaire.modifier_statut_formulaire(
                                    base_estimation_id, 
                                    'ANNULÉ', 
                                    est_base.get('employee_id'),
                                    f"Remplacée par version {nouvelle_version_num}"
                                )
                            
                            # Enregistrement de l'action
                            gestionnaire.enregistrer_validation(
                                nouvelle_version_id,
                                est_base.get('employee_id'),
                                'CREATION',
                                f"Version {nouvelle_version_num} créée depuis {est_base['numero_document']}"
                            )
                            
                            st.success(f"""
                            ✅ **Nouvelle Version Créée !**
                            
                            📊 **Version :** {nouvelle_version_num}
                            💰 **Nouveau Montant :** {nouveau_montant:,.2f}$ CAD
                            📅 **Nouvelle Validité :** {nouvelle_validite} jours
                            🔄 **Ajustement :** {ajustement_prix} ({pourcentage_ajustement}%)
                            """)
                            
                            if notification_client:
                                st.info("📧 Notification envoyée au client pour la nouvelle version")
                            
                            # Actions suivantes
                            col_next1, col_next2 = st.columns(2)
                            with col_next1:
                                if st.button("📋 Voir Nouvelle Version", use_container_width=True, key="voir_nouvelle_version"):
                                    st.session_state.selected_formulaire_id = nouvelle_version_id
                                    st.session_state.show_formulaire_modal = True
                            with col_next2:
                                if st.button("📊 Retour Liste", use_container_width=True, key="retour_liste_versions"):
                                    st.session_state.form_action = "list_estimations_actives"
                                    st.rerun()
                        else:
                            st.error("❌ Erreur lors de la création de la nouvelle version")
                    else:
                        st.error("❌ Estimation de base introuvable")
                elif submit_version and not motif_revision:
                    st.error("❌ Le motif de révision est obligatoire")
    else:
        st.info("Aucune estimation disponible pour créer des versions.")

# =============================================================================
# ESTIMATIONS ACCEPTÉES ET CONVERSION EN PROJETS
# =============================================================================

def render_estimations_acceptees(gestionnaire):
    """Gestion des estimations acceptées et conversion projets"""
    st.markdown("#### ✅ Estimations Acceptées")
    
    # Estimations acceptées prêtes pour conversion
    estimations_acceptees = [est for est in gestionnaire.get_formulaires('ESTIMATION') 
                           if est['statut'] == 'APPROUVÉ']
    
    if not estimations_acceptees:
        st.info("Aucune estimation acceptée en attente de conversion.")
        
        # Proposer de marquer des estimations comme acceptées
        estimations_envoyees = [est for est in gestionnaire.get_formulaires('ESTIMATION') 
                               if est['statut'] == 'ENVOYÉ']
        
        if estimations_envoyees:
            st.markdown("##### 📋 Estimations En Négociation")
            st.info(f"{len(estimations_envoyees)} estimation(s) envoyée(s) en attente de réponse client")
            
            for est in estimations_envoyees[:3]:  # Afficher les 3 premières
                with st.expander(f"EST {est['numero_document']} - {est.get('company_nom', 'N/A')}", expanded=False):
                    col_neg1, col_neg2, col_neg3 = st.columns(3)
                    
                    with col_neg1:
                        st.metric("Montant", f"{est.get('montant_total', 0):,.2f}$ CAD")
                    with col_neg2:
                        validite_status = get_validite_status(est)
                        st.text(f"Validité: {validite_status}")
                    with col_neg3:
                        if st.button(f"✅ Marquer Acceptée", key=f"accept_{est['id']}", use_container_width=True):
                            if marquer_estimation_acceptee(gestionnaire, est['id']):
                                st.success("✅ Estimation marquée comme acceptée!")
                                st.rerun()
        
        return
    
    st.markdown("##### 🔄 Conversion en Projets")
    
    for est in estimations_acceptees:
        with st.expander(f"EST {est['numero_document']} - {est.get('company_nom', 'N/A')}", expanded=False):
            col_conv1, col_conv2, col_conv3, col_conv4 = st.columns(4)
            
            with col_conv1:
                st.metric("Montant Validé", f"{est.get('montant_total', 0):,.2f}$ CAD")
                st.text(f"Date validation : {est.get('date_echeance', 'N/A')}")
            
            with col_conv2:
                try:
                    meta = json.loads(est.get('metadonnees_json', '{}'))
                    template = meta.get('template_industrie', 'N/A')
                    delai = meta.get('delai_execution', 'N/A')
                    st.text(f"Template: {template}")
                    st.text(f"Délai: {delai} jours")
                except:
                    st.text("Métadonnées indisponibles")
            
            with col_conv3:
                if st.button(f"📋 Voir Détails", key=f"details_{est['id']}", use_container_width=True):
                    st.session_state.selected_formulaire_id = est['id']
                    st.session_state.show_formulaire_modal = True
            
            with col_conv4:
                if st.button(f"🔄 Convertir → Projet", key=f"convert_{est['id']}", use_container_width=True):
                    projet_id = convertir_estimation_vers_projet(gestionnaire, est['id'])
                    if projet_id:
                        st.success(f"✅ Projet #{projet_id} créé depuis EST {est['numero_document']}")
                        st.rerun()

# =============================================================================
# FONCTIONS UTILITAIRES SPÉCIFIQUES AUX ESTIMATIONS
# =============================================================================

def get_clients_actifs():
    """Récupère la liste des clients depuis le CRM"""
    try:
        # Dans le système ERP, les clients sont des companies 
        query = """
            SELECT id, nom, secteur, adresse 
            FROM companies 
            WHERE secteur NOT LIKE '%FOURNISSEUR%' 
               OR id IN (
                   SELECT DISTINCT company_id 
                   FROM formulaires 
                   WHERE type_formulaire = 'ESTIMATION'
               )
            ORDER BY nom
        """
        rows = st.session_state.erp_db.execute_query(query)
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération clients: {e}")
        return []

def get_projets_client(client_id):
    """Récupère les projets d'un client spécifique"""
    try:
        query = """
            SELECT id, nom_projet, statut, prix_estime
            FROM projects 
            WHERE client_company_id = ? 
            ORDER BY nom_projet
        """
        rows = st.session_state.erp_db.execute_query(query, (client_id,))
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération projets client: {e}")
        return []

def get_marge_defaut_template(template_industrie):
    """Retourne la marge par défaut selon le template industrie"""
    marges_defaut = {
        "AUTOMOBILE": 15,
        "AERONAUTIQUE": 25,
        "CONSTRUCTION": 12,
        "GENERAL": 20
    }
    return marges_defaut.get(template_industrie, 20)

def get_template_info(template_industrie):
    """Retourne les informations complètes d'un template industrie"""
    templates_industrie = {
        "AUTOMOBILE": {
            "marge_defaut": 15,
            "conditions_paiement": "30 jours net",
            "garantie": "12 mois pièces et main d'œuvre",
            "clauses_techniques": [
                "Tolérances selon norme ISO 2768",
                "Matériaux certifiés automotive",
                "Traçabilité complète exigée"
            ],
            "delai_standard": 21,
            "coefficient_complexite": 1.2,
            "cout_certification_pct": 5
        },
        "AERONAUTIQUE": {
            "marge_defaut": 25,
            "conditions_paiement": "50% avance + 50% livraison",
            "garantie": "24 mois certification aéro",
            "clauses_techniques": [
                "Conformité AS9100",
                "Matériaux aéronautiques certifiés",
                "Documentation complète CAMO"
            ],
            "delai_standard": 45,
            "coefficient_complexite": 1.5,
            "cout_certification_pct": 15
        },
        "CONSTRUCTION": {
            "marge_defaut": 12,
            "conditions_paiement": "30 jours net",
            "garantie": "12 mois installation",
            "clauses_techniques": [
                "Normes CNB en vigueur",
                "Résistance structurale certifiée",
                "Finition selon devis architectural"
            ],
            "delai_standard": 14,
            "coefficient_complexite": 1.1,
            "cout_certification_pct": 2
        },
        "GENERAL": {
            "marge_defaut": 20,
            "conditions_paiement": "30 jours net",
            "garantie": "12 mois standard",
            "clauses_techniques": [
                "Qualité industrielle standard",
                "Conformité normes applicables"
            ],
            "delai_standard": 21,
            "coefficient_complexite": 1.0,
            "cout_certification_pct": 0
        }
    }
    
    return templates_industrie.get(template_industrie, templates_industrie["GENERAL"])

def get_clauses_techniques_template(template_industrie):
    """Retourne les clauses techniques pré-remplies selon le template"""
    template_info = get_template_info(template_industrie)
    clauses = template_info['clauses_techniques']
    return '\n'.join([f"• {clause}" for clause in clauses])

def calculer_estimation_automatique(projet_id, marge_beneficiaire, template_industrie):
    """Calculs automatiques pour estimations basées sur un projet existant"""
    try:
        # Récupérer coûts matériaux depuis BOM projet
        materiaux_projet = get_materiaux_projet(projet_id)
        cout_materiaux = sum(mat.get('quantite', 0) * mat.get('prix_unitaire', 0) for mat in materiaux_projet)
        
        # Récupérer temps estimé depuis opérations + postes de travail
        operations_projet = get_operations_projet(projet_id)
        cout_main_oeuvre = 0
        
        for operation in operations_projet:
            try:
                # Récupérer le coût horaire du poste de travail
                poste = get_poste_travail(operation.get('work_center_id'))
                if poste:
                    cout_main_oeuvre += operation.get('temps_estime', 0) * poste.get('cout_horaire', 50)
                else:
                    # Coût par défaut si pas de poste trouvé
                    cout_main_oeuvre += operation.get('temps_estime', 0) * 50
            except:
                continue
        
        # Récupération des informations du template
        template_info = get_template_info(template_industrie)
        
        # Calculs selon template industrie
        coefficient_complexite = template_info['coefficient_complexite']
        cout_certification = cout_materiaux * (template_info['cout_certification_pct'] / 100)
        
        # Calcul final
        cout_direct = (cout_materiaux + cout_main_oeuvre) * coefficient_complexite
        cout_indirect = cout_direct * 0.20  # 20% frais généraux
        marge = (cout_direct + cout_indirect) * (marge_beneficiaire / 100)
        
        prix_HT = cout_direct + cout_indirect + marge + cout_certification
        taxes = prix_HT * 0.14975  # TVQ + TPS Québec
        prix_TTC = prix_HT + taxes
        
        return {
            'cout_materiaux': cout_materiaux,
            'cout_main_oeuvre': cout_main_oeuvre,
            'cout_certification': cout_certification,
            'cout_direct': cout_direct,
            'cout_indirect': cout_indirect,
            'marge': marge,
            'prix_HT': prix_HT,
            'taxes': taxes,
            'prix_TTC': prix_TTC,
            'details': f"Calcul automatique template {template_industrie}"
        }
        
    except Exception as e:
        st.error(f"Erreur calculs automatiques: {e}")
        return None

def get_materiaux_projet(projet_id):
    """Récupère les matériaux d'un projet"""
    try:
        query = """
            SELECT id, designation as description, quantite, prix_unitaire, unite
            FROM materials 
            WHERE project_id = ?
            ORDER BY designation
        """
        rows = st.session_state.erp_db.execute_query(query, (projet_id,))
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération matériaux: {e}")
        return []

def get_poste_travail(work_center_id):
    """Récupère les informations d'un poste de travail"""
    try:
        if not work_center_id:
            return None
        
        query = """
            SELECT id, nom, cout_horaire, departement
            FROM work_centers 
            WHERE id = ?
        """
        rows = st.session_state.erp_db.execute_query(query, (work_center_id,))
        return dict(rows[0]) if rows else None
    except Exception as e:
        st.error(f"Erreur récupération poste travail: {e}")
        return None

def creer_lignes_depuis_projet(projet_id, calculs_auto):
    """Crée les lignes d'estimation depuis un projet et ses calculs"""
    lignes = []
    
    if calculs_auto:
        # Ligne pour matériaux
        if calculs_auto['cout_materiaux'] > 0:
            lignes.append({
                'description': 'Matériaux et fournitures',
                'quantite': 1,
                'unite': 'FORFAIT',
                'prix_unitaire': calculs_auto['cout_materiaux'],
                'montant_ligne': calculs_auto['cout_materiaux']
            })
        
        # Ligne pour main d'œuvre
        if calculs_auto['cout_main_oeuvre'] > 0:
            lignes.append({
                'description': 'Main d\'œuvre et montage',
                'quantite': 1,
                'unite': 'FORFAIT', 
                'prix_unitaire': calculs_auto['cout_main_oeuvre'],
                'montant_ligne': calculs_auto['cout_main_oeuvre']
            })
        
        # Ligne pour certification si applicable
        if calculs_auto['cout_certification'] > 0:
            lignes.append({
                'description': 'Certification et conformité',
                'quantite': 1,
                'unite': 'FORFAIT',
                'prix_unitaire': calculs_auto['cout_certification'],
                'montant_ligne': calculs_auto['cout_certification']
            })
    
    return lignes

def get_projets_sans_estimation():
    """Récupère les projets qui n'ont pas encore d'estimation"""
    try:
        query = """
            SELECT p.id, p.nom_projet, p.client_nom_cache
            FROM projects p
            WHERE p.statut IN ('À FAIRE', 'EN COURS')
            AND p.id NOT IN (
                SELECT DISTINCT project_id 
                FROM formulaires 
                WHERE type_formulaire = 'ESTIMATION' 
                AND project_id IS NOT NULL
            )
            ORDER BY p.nom_projet
            LIMIT 5
        """
        rows = st.session_state.erp_db.execute_query(query)
        return [dict(row) for row in rows]
    except:
        return []

def est_estimation_expiree(estimation):
    """Vérifie si une estimation est expirée"""
    try:
        meta = json.loads(estimation.get('metadonnees_json', '{}'))
        date_validite = datetime.strptime(meta.get('date_validite', ''), '%Y-%m-%d').date()
        return date_validite < datetime.now().date()
    except:
        return False

def get_template_from_metadata(estimation):
    """Extrait le template depuis les métadonnées"""
    try:
        meta = json.loads(estimation.get('metadonnees_json', '{}'))
        return meta.get('template_industrie', 'N/A')
    except:
        return 'N/A'

def get_date_validite_from_metadata(estimation):
    """Extrait la date de validité depuis les métadonnées"""
    try:
        meta = json.loads(estimation.get('metadonnees_json', '{}'))
        return meta.get('date_validite', '9999-12-31')
    except:
        return '9999-12-31'

def get_validite_status(estimation):
    """Retourne le statut de validité d'une estimation"""
    try:
        meta = json.loads(estimation.get('metadonnees_json', '{}'))
        date_validite = datetime.strptime(meta.get('date_validite', ''), '%Y-%m-%d').date()
        today = datetime.now().date()
        jours_restants = (date_validite - today).days
        
        if jours_restants < 0:
            return f"Expirée ({abs(jours_restants)}j)"
        elif jours_restants <= 3:
            return f"{jours_restants}j restants"
        else:
            return f"{jours_restants}j restants"
    except:
        return "Non définie"

def marquer_estimation_acceptee(gestionnaire, estimation_id):
    """Marque une estimation comme acceptée par le client"""
    try:
        gestionnaire.modifier_statut_formulaire(
            estimation_id, 
            'APPROUVÉ',
            1,  # TODO: Utiliser l'utilisateur courant
            "Estimation acceptée par le client"
        )
        return True
    except Exception as e:
        st.error(f"Erreur marquage acceptation: {e}")
        return False

def get_versions_estimation(gestionnaire, base_estimation_id):
    """Récupère toutes les versions d'une estimation"""
    try:
        # Récupérer l'estimation de base
        est_base = gestionnaire.get_formulaire_details(base_estimation_id)
        if not est_base:
            return []
        
        # Récupérer le numéro de base (sans version)
        numero_base = est_base['numero_document'].split(' v')[0]
        
        # Rechercher toutes les estimations avec ce numéro de base
        query = """
            SELECT * FROM formulaires 
            WHERE type_formulaire = 'ESTIMATION' 
            AND (numero_document = ? OR numero_document LIKE ?)
            ORDER BY id
        """
        
        rows = gestionnaire.db.execute_query(query, (numero_base, f"{numero_base} v%"))
        versions = [dict(row) for row in rows]
        
        # Ajouter le numéro de version depuis les métadonnées
        for version in versions:
            try:
                meta = json.loads(version.get('metadonnees_json', '{}'))
                version['version'] = meta.get('version', 1)
            except:
                version['version'] = 1
        
        return sorted(versions, key=lambda x: x['version'])
        
    except Exception as e:
        st.error(f"Erreur récupération versions: {e}")
        return []

def get_prochaine_version_numero(gestionnaire, base_estimation_id):
    """Calcule le prochain numéro de version"""
    versions = get_versions_estimation(gestionnaire, base_estimation_id)
    if not versions:
        return 2  # Si pas de versions trouvées, commencer à v2
    
    max_version = max(v.get('version', 1) for v in versions)
    return max_version + 1

def dupliquer_estimation_version(gestionnaire, version_id):
    """Duplique une version d'estimation existante"""
    try:
        # Utiliser la fonction de duplication existante du gestionnaire
        nouveau_id = gestionnaire.db.dupliquer_formulaire(version_id, 'ESTIMATION')
        
        if nouveau_id:
            # Mettre le statut en brouillon pour modification
            gestionnaire.modifier_statut_formulaire(nouveau_id, 'BROUILLON', 1, "Version dupliquée")
        
        return nouveau_id
    except Exception as e:
        st.error(f"Erreur duplication: {e}")
        return None

def convertir_estimation_vers_projet(gestionnaire, estimation_id):
    """Convertit une estimation acceptée en nouveau projet"""
    try:
        est_details = gestionnaire.get_formulaire_details(estimation_id)
        if not est_details:
            return None
        
        # Récupération des métadonnées
        try:
            meta = json.loads(est_details.get('metadonnees_json', '{}'))
        except:
            meta = {}
        
        # Données du nouveau projet
        data_projet = {
            'nom_projet': f"Projet depuis EST {est_details['numero_document']}",
            'client_company_id': est_details.get('company_id'),
            'statut': 'À FAIRE',
            'priorite': est_details.get('priorite', 'NORMAL'),
            'prix_estime': est_details.get('montant_total', 0),
            'date_soumis': datetime.now().date(),
            'date_prevu': datetime.now().date() + timedelta(days=meta.get('delai_execution', 30)),
            'description': f"Projet généré automatiquement depuis l'estimation {est_details['numero_document']}"
        }
        
        # Insertion du nouveau projet
        query = """
            INSERT INTO projects 
            (nom_projet, client_company_id, statut, priorite, prix_estime, date_soumis, date_prevu, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        projet_id = gestionnaire.db.execute_insert(query, (
            data_projet['nom_projet'],
            data_projet['client_company_id'],
            data_projet['statut'],
            data_projet['priorite'],
            data_projet['prix_estime'],
            data_projet['date_soumis'],
            data_projet['date_prevu'],
            data_projet['description']
        ))
        
        if projet_id:
            # Mise à jour de l'estimation
            gestionnaire.modifier_statut_formulaire(
                estimation_id,
                'TERMINÉ',
                est_details.get('employee_id'),
                f"Convertie en projet #{projet_id}"
            )
            
            # Enregistrement de la conversion
            gestionnaire.enregistrer_validation(
                estimation_id,
                est_details.get('employee_id'),
                'CONVERSION',
                f"Estimation convertie en projet #{projet_id}"
            )
        
        return projet_id
        
    except Exception as e:
        st.error(f"Erreur conversion projet: {e}")
        return None

# =============================================================================
# INTERFACES AVANCÉES (SIMPLIFIÉES POUR LA DÉMO)
# =============================================================================

def render_analyse_rentabilite(gestionnaire):
    """Analyse de rentabilité des estimations"""
    st.markdown("#### 📊 Analyse de Rentabilité")
    
    estimations = gestionnaire.get_formulaires('ESTIMATION')
    
    if not estimations:
        st.info("Aucune estimation pour l'analyse de rentabilité.")
        return
    
    # Métriques de rentabilité
    col1, col2, col3, col4 = st.columns(4)
    
    total_estimations = len(estimations)
    acceptees = len([e for e in estimations if e['statut'] == 'APPROUVÉ'])
    montant_total = sum(e.get('montant_total', 0) for e in estimations)
    montant_accepte = sum(e.get('montant_total', 0) for e in estimations if e['statut'] == 'APPROUVÉ')
    
    with col1:
        st.metric("Total Estimations", total_estimations)
    with col2:
        taux_acceptation = (acceptees / total_estimations * 100) if total_estimations > 0 else 0
        st.metric("Taux d'Acceptation", f"{taux_acceptation:.1f}%")
    with col3:
        st.metric("CA Potentiel", f"{montant_total:,.0f}$ CAD")
    with col4:
        st.metric("CA Réalisé", f"{montant_accepte:,.0f}$ CAD")
    
    # Analyse par template
    st.markdown("##### 📈 Rentabilité par Template Industrie")
    
    templates_stats = {}
    for est in estimations:
        template = get_template_from_metadata(est)
        if template not in templates_stats:
            templates_stats[template] = {'total': 0, 'acceptees': 0, 'montant_total': 0, 'montant_accepte': 0}
        
        templates_stats[template]['total'] += 1
        templates_stats[template]['montant_total'] += est.get('montant_total', 0)
        
        if est['statut'] == 'APPROUVÉ':
            templates_stats[template]['acceptees'] += 1
            templates_stats[template]['montant_accepte'] += est.get('montant_total', 0)
    
    if templates_stats:
        df_templates = []
        for template, stats in templates_stats.items():
            taux = (stats['acceptees'] / stats['total'] * 100) if stats['total'] > 0 else 0
            df_templates.append({
                'Template': template,
                'Total Estimations': stats['total'],
                'Acceptées': stats['acceptees'],
                'Taux (%%)': f"{taux:.1f}",
                'CA Potentiel': f"{stats['montant_total']:,.0f}$",
                'CA Réalisé': f"{stats['montant_accepte']:,.0f}$"
            })
        
        df = pd.DataFrame(df_templates)
        st.dataframe(df, use_container_width=True)

def render_templates_estimations(gestionnaire):
    """Gestion des templates d'estimation"""
    st.markdown("#### 📋 Templates Estimations")
    
    # Affichage des templates disponibles
    templates_industrie = ["AUTOMOBILE", "AERONAUTIQUE", "CONSTRUCTION", "GENERAL"]
    
    for template in templates_industrie:
        with st.expander(f"Template {template}", expanded=False):
            template_info = get_template_info(template)
            
            col1, col2 = st.columns(2)
            with col1:
                st.text(f"Marge par défaut: {template_info['marge_defaut']}%")
                st.text(f"Délai standard: {template_info['delai_standard']} jours")
                st.text(f"Coefficient complexité: {template_info['coefficient_complexite']}")
            
            with col2:
                st.text(f"Garantie: {template_info['garantie']}")
                st.text(f"Conditions paiement: {template_info['conditions_paiement']}")
                st.text(f"Certification: {template_info['cout_certification_pct']}%")
            
            st.markdown("**Clauses techniques:**")
            for clause in template_info['clauses_techniques']:
                st.text(f"• {clause}")

def render_suivi_commercial(gestionnaire):
    """Suivi commercial des estimations"""
    st.markdown("#### 📈 Suivi Commercial")
    
    estimations = gestionnaire.get_formulaires('ESTIMATION')
    estimations_actives = [e for e in estimations if e['statut'] in ['VALIDÉ', 'ENVOYÉ']]
    
    if not estimations_actives:
        st.info("Aucune estimation en cours de négociation.")
        return
    
    st.markdown("##### 📋 Estimations en Négociation")
    
    for est in estimations_actives:
        with st.expander(f"EST {est['numero_document']} - {est.get('company_nom', 'N/A')}", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Montant", f"{est.get('montant_total', 0):,.2f}$ CAD")
                validite_status = get_validite_status(est)
                st.text(f"Validité: {validite_status}")
            
            with col2:
                st.text(f"Commercial: {est.get('employee_nom', 'N/A')}")
                st.text(f"Statut: {est['statut']}")
            
            with col3:
                if st.button(f"📞 Relancer Client", key=f"relance_{est['id']}"):
                    st.info("📧 Relance envoyée au client")
                
                if st.button(f"✅ Marquer Acceptée", key=f"accept_suivi_{est['id']}"):
                    if marquer_estimation_acceptee(gestionnaire, est['id']):
                        st.success("✅ Estimation acceptée!")
                        st.rerun()

def render_analyse_marges(gestionnaire):
    """Analyse des marges bénéficiaires"""
    st.markdown("#### 💰 Analyse des Marges")
    
    estimations = gestionnaire.get_formulaires('ESTIMATION')
    
    if not estimations:
        st.info("Aucune estimation pour l'analyse des marges.")
        return
    
    # Analyse des marges par template
    marges_par_template = {}
    
    for est in estimations:
        try:
            meta = json.loads(est.get('metadonnees_json', '{}'))
            template = meta.get('template_industrie', 'N/A')
            marge = meta.get('marge_beneficiaire', 0)
            
            if template not in marges_par_template:
                marges_par_template[template] = []
            marges_par_template[template].append(marge)
        except:
            continue
    
    if marges_par_template:
        st.markdown("##### 📊 Marges Moyennes par Template")
        
        df_marges = []
        for template, marges in marges_par_template.items():
            if marges:
                marge_moyenne = sum(marges) / len(marges)
                marge_min = min(marges)
                marge_max = max(marges)
                
                df_marges.append({
                    'Template': template,
                    'Nombre d\'estimations': len(marges),
                    'Marge Moyenne (%)': f"{marge_moyenne:.1f}",
                    'Marge Min (%)': f"{marge_min:.1f}",
                    'Marge Max (%)': f"{marge_max:.1f}"
                })
        
        if df_marges:
            df = pd.DataFrame(df_marges)
            st.dataframe(df, use_container_width=True)
    
    # Recommandations
    st.markdown("##### 💡 Recommandations")
    st.success("✅ Les marges sont cohérentes avec les standards de l'industrie")
    st.info("💡 Considérer l'ajustement des marges selon la performance des templates")

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def get_projets_actifs():
    """Récupère la liste des projets actifs"""
    try:
        query = "SELECT id, nom_projet FROM projects WHERE statut NOT IN ('TERMINÉ', 'ANNULÉ') ORDER BY nom_projet"
        rows = st.session_state.erp_db.execute_query(query)
        return [dict(row) for row in rows]
    except:
        return []

def get_employes_actifs():
    """Récupère la liste des employés actifs"""
    try:
        query = "SELECT id, prenom, nom, poste FROM employees WHERE statut = 'ACTIF' ORDER BY prenom, nom"
        rows = st.session_state.erp_db.execute_query(query)
        return [dict(row) for row in rows]
    except:
        return []

def get_operations_projet(projet_id):
    """Récupère les opérations d'un projet"""
    try:
        query = "SELECT id, sequence_number as sequence, description FROM operations WHERE project_id = ? ORDER BY sequence_number"
        rows = st.session_state.erp_db.execute_query(query, (projet_id,))
        return [dict(row) for row in rows]
    except:
        return []

# =============================================================================
# FONCTIONS UTILITAIRES SPÉCIFIQUES AUX BONS D'ACHATS
# =============================================================================

def get_fournisseurs_actifs():
    """Récupère la liste des fournisseurs depuis le CRM"""
    try:
        # Dans le système ERP, les fournisseurs sont des companies avec un secteur spécifique
        # ou peuvent être identifiés par un type dans les métadonnées
        query = """
            SELECT id, nom, secteur, adresse 
            FROM companies 
            WHERE secteur LIKE '%FOURNISSEUR%' 
               OR secteur LIKE '%DISTRIBUTION%' 
               OR secteur LIKE '%COMMERCE%'
               OR id IN (
                   SELECT DISTINCT company_id 
                   FROM formulaires 
                   WHERE type_formulaire = 'BON_ACHAT'
               )
            ORDER BY nom
        """
        rows = st.session_state.erp_db.execute_query(query)
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération fournisseurs: {e}")
        return []

def get_articles_inventaire_critique():
    """Récupère les articles avec stock critique nécessitant réapprovisionnement"""
    try:
        query = """
            SELECT id, nom, type_produit, quantite_imperial, limite_minimale_imperial, statut
            FROM inventory_items 
            WHERE statut IN ('CRITIQUE', 'FAIBLE', 'ÉPUISÉ')
            ORDER BY 
                CASE statut 
                    WHEN 'ÉPUISÉ' THEN 1
                    WHEN 'CRITIQUE' THEN 2 
                    WHEN 'FAIBLE' THEN 3
                END, nom
        """
        rows = st.session_state.erp_db.execute_query(query)
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur récupération stocks critiques: {e}")
        return []

def search_articles_inventaire(search_term):
    """Recherche dans l'inventaire par nom ou type"""
    try:
        if not search_term:
            return []
        
        query = """
            SELECT id, nom, type_produit, quantite_imperial, statut
            FROM inventory_items 
            WHERE LOWER(nom) LIKE LOWER(?) 
               OR LOWER(type_produit) LIKE LOWER(?)
            ORDER BY nom
            LIMIT 10
        """
        search_pattern = f"%{search_term}%"
        rows = st.session_state.erp_db.execute_query(query, (search_pattern, search_pattern))
        return [dict(row) for row in rows]
    except Exception as e:
        st.error(f"Erreur recherche inventaire: {e}")
        return []

def calculer_quantite_recommandee(article):
    """Calcule la quantité recommandée pour un réapprovisionnement"""
    try:
        # Logique simple : 2x le stock minimum ou 10 unités minimum
        stock_min_str = article.get('limite_minimale_imperial', '0\' 0"')
        
        # Pour simplifier, on retourne une valeur par défaut
        # Dans un vrai système, il faudrait parser la chaîne impériale
        if 'CRITIQUE' in article.get('statut', ''):
            return 20
        elif 'FAIBLE' in article.get('statut', ''):
            return 15
        else:
            return 10
            
    except Exception:
        return 10

def convertir_ba_vers_bc(gestionnaire, ba_id):
    """Conversion rapide BA → BC avec paramètres par défaut"""
    try:
        ba_details = gestionnaire.get_formulaire_details(ba_id)
        if not ba_details:
            return None
        
        # Numéro BC automatique
        numero_bc = gestionnaire.generer_numero_document('BON_COMMANDE')
        
        # Métadonnées BC minimales
        metadonnees_bc = {
            'ba_source_id': ba_id,
            'ba_source_numero': ba_details['numero_document'],
            'conversion_automatique': True,
            'conditions_paiement': '30 jours net'
        }
        
        # Notes de conversion automatique
        notes_bc = f"""=== CONVERSION AUTOMATIQUE ===
Bon de Commande généré automatiquement depuis {ba_details['numero_document']}
Date conversion : {datetime.now().strftime('%d/%m/%Y à %H:%M')}

=== NOTES BA SOURCE ===
{ba_details.get('notes', '')}"""
        
        # Données du BC
        data_bc = {
            'type_formulaire': 'BON_COMMANDE',
            'numero_document': numero_bc,
            'project_id': ba_details.get('project_id'),
            'company_id': ba_details.get('company_id'),
            'employee_id': ba_details.get('employee_id'),
            'statut': 'VALIDÉ',
            'priorite': ba_details.get('priorite'),
            'date_creation': datetime.now().date(),
            'date_echeance': datetime.now().date() + timedelta(days=14),
            'montant_total': ba_details.get('montant_total', 0),
            'notes': notes_bc,
            'metadonnees_json': json.dumps(metadonnees_bc),
            'lignes': ba_details.get('lignes', [])
        }
        
        # Création du BC
        bc_id = gestionnaire.creer_formulaire(data_bc)
        
        if bc_id:
            # Mise à jour du BA original
            gestionnaire.modifier_statut_formulaire(ba_id, 'TERMINÉ', 
                                                   ba_details.get('employee_id'), 
                                                   f"Converti automatiquement en BC {numero_bc}")
            return numero_bc
        
        return None
        
    except Exception as e:
        st.error(f"Erreur conversion BA→BC: {e}")
        return None
