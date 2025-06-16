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
# INTERFACES POUR LES AUTRES TYPES DE FORMULAIRES (STRUCTURE SIMILAIRE)
# =============================================================================

def render_bons_achats_tab(gestionnaire):
    """Interface pour les Bons d'Achats - Structure similaire aux BT"""
    st.markdown("### 🛒 Bons d'Achats")
    st.info("🚧 Interface Bons d'Achats - En développement")
    
    # TODO: Implémenter interface similaire aux Bons de Travail
    # Spécificités: Lien avec inventaire, gestion fournisseurs, approbations budgétaires

def render_bons_commande_tab(gestionnaire):
    """Interface pour les Bons de Commande"""
    st.markdown("### 📦 Bons de Commande")
    st.info("🚧 Interface Bons de Commande - En développement")
    
    # TODO: Conversion Bon d'Achats → Bon de Commande
    # Spécificités: Gestion fournisseurs, termes de paiement, suivi livraisons

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
