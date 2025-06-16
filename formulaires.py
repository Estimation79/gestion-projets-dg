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

def render_bons_commande_tab(gestionnaire):
    """Interface pour les Bons de Commande - Structure similaire aux BT"""
    st.markdown("### 📦 Bons de Commande")
    st.info("🚧 Interface Bons de Commande - En développement")
    
    # TODO: Implémenter interface similaire aux Bons de Travail
    # Spécificités: Conversion Bon d'Achats → Bon de Commande, envoi fournisseurs, suivi livraisons

def render_demandes_prix_tab(gestionnaire):
    """Interface pour les Demandes de Prix"""
    st.markdown("### 💰 Demandes de Prix")
    st.info("🚧 Interface Demandes de Prix - En développement")
    
    # TODO: RFQ vers multiples fournisseurs
    # Spécificités: Comparaison offres, négociation, validation technique

def render_estimations_tab(gestionnaire):
    """Interface pour les Estimations"""
    st.markdown("### 📊 Estimations")
    st.info("🚧 Interface Estimations - En développement")
    
    # TODO: Devis clients professionnels
    # Spécificités: Calculs automatiques, templates, conversion en projets

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
