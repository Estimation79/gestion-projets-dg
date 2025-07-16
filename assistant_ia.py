# assistant_ia.py - Module Assistant IA Claude
# ERP Production DG Inc. - Intelligence Artificielle intégrée
# Analyse intelligente des données métier avec Claude API

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from anthropic import Anthropic
import plotly.graph_objects as go
import plotly.express as px

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AssistantIAClaude:
    """
    Assistant IA utilisant Claude pour analyser les données ERP
    Fournit des insights, recommandations et analyses prédictives
    """
    
    def __init__(self, db, api_key: Optional[str] = None):
        """
        Initialise l'assistant IA
        
        Args:
            db: Instance ERPDatabase pour accéder aux données
            api_key: Clé API Claude (ou depuis variable d'environnement)
        """
        self.db = db
        self.api_key = api_key or os.environ.get('CLAUDE_API_KEY')
        
        if self.api_key:
            try:
                self.client = Anthropic(api_key=self.api_key)
                self.model = "claude-sonnet-4-20250514"
                logger.info("✅ Assistant IA Claude initialisé avec succès")
            except Exception as e:
                logger.error(f"❌ Erreur initialisation Claude: {e}")
                self.client = None
        else:
            logger.warning("⚠️ Clé API Claude non configurée")
            self.client = None
    
    # =========================================================================
    # COLLECTE ET PRÉPARATION DES DONNÉES
    # =========================================================================
    
    def _collecter_donnees_projets(self) -> Dict[str, Any]:
        """Collecte les données projets pour analyse"""
        try:
            # Projets actifs
            projets_actifs = self.db.execute_query("""
                SELECT p.*, 
                       COUNT(DISTINCT o.id) as nb_operations,
                       COUNT(DISTINCT te.id) as nb_pointages,
                       SUM(te.heures) as heures_totales
                FROM projects p
                LEFT JOIN operations o ON p.id = o.project_id
                LEFT JOIN time_entries te ON p.id = te.project_id
                WHERE p.statut IN ('EN COURS', 'À FAIRE')
                GROUP BY p.id
            """)
            
            # Statistiques globales
            stats = self.db.execute_query("""
                SELECT 
                    COUNT(CASE WHEN statut = 'TERMINÉ' THEN 1 END) as projets_termines,
                    COUNT(CASE WHEN statut = 'EN COURS' THEN 1 END) as projets_en_cours,
                    COUNT(CASE WHEN statut = 'À FAIRE' THEN 1 END) as projets_a_faire,
                    AVG(CASE WHEN statut = 'TERMINÉ' AND date_fin_reel IS NOT NULL 
                        THEN julianday(date_fin_reel) - julianday(date_debut_reel) END) as duree_moy_jours,
                    AVG(prix_estime) as budget_moyen
                FROM projects
                WHERE created_at >= date('now', '-6 months')
            """)
            
            return {
                'projets_actifs': [dict(p) for p in projets_actifs],
                'statistiques': dict(stats[0]) if stats else {},
                'nb_projets_actifs': len(projets_actifs)
            }
        except Exception as e:
            logger.error(f"Erreur collecte données projets: {e}")
            return {}
    
    def _collecter_donnees_inventaire(self) -> Dict[str, Any]:
        """Collecte les données d'inventaire pour analyse"""
        try:
            # Articles en alerte
            alertes = self.db.execute_query("""
                SELECT * FROM inventory_items 
                WHERE quantite_metric <= limite_minimale_metric
                ORDER BY (quantite_metric / NULLIF(limite_minimale_metric, 0))
            """)
            
            # Mouvements récents
            mouvements = self.db.execute_query("""
                SELECT 
                    item_id,
                    COUNT(*) as nb_mouvements,
                    SUM(CASE WHEN type_mouvement = 'ENTREE' THEN quantite_metric ELSE 0 END) as total_entrees,
                    SUM(CASE WHEN type_mouvement = 'SORTIE' THEN quantite_metric ELSE 0 END) as total_sorties
                FROM inventory_history
                WHERE created_at >= date('now', '-30 days')
                GROUP BY item_id
                ORDER BY nb_mouvements DESC
                LIMIT 10
            """)
            
            # Valeur totale inventaire (estimation)
            valeur_totale = self.db.execute_query("""
                SELECT 
                    COUNT(*) as nb_articles,
                    SUM(quantite_metric) as quantite_totale
                FROM inventory_items
            """)
            
            return {
                'alertes_stock': [dict(a) for a in alertes],
                'mouvements_frequents': [dict(m) for m in mouvements],
                'valeur_inventaire': dict(valeur_totale[0]) if valeur_totale else {},
                'nb_alertes': len(alertes)
            }
        except Exception as e:
            logger.error(f"Erreur collecte données inventaire: {e}")
            return {}
    
    def _collecter_donnees_crm(self) -> Dict[str, Any]:
        """Collecte les données CRM pour analyse"""
        try:
            # Opportunités par statut
            opportunites = self.db.execute_query("""
                SELECT 
                    statut,
                    COUNT(*) as nombre,
                    SUM(montant) as montant_total,
                    AVG(montant) as montant_moyen
                FROM crm_opportunities
                WHERE created_at >= date('now', '-3 months')
                GROUP BY statut
            """)
            
            # Top clients par CA
            top_clients = self.db.execute_query("""
                SELECT 
                    c.nom as client,
                    COUNT(DISTINCT p.id) as nb_projets,
                    SUM(p.prix_estime) as ca_total,
                    MAX(p.created_at) as dernier_projet
                FROM companies c
                JOIN projects p ON c.id = p.client_company_id
                GROUP BY c.id
                ORDER BY ca_total DESC
                LIMIT 10
            """)
            
            # Activité commerciale récente
            activite_recente = self.db.execute_query("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as nb_interactions
                FROM crm_interactions
                WHERE created_at >= date('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)
            
            return {
                'opportunites': [dict(o) for o in opportunites] if opportunites else [],
                'top_clients': [dict(c) for c in top_clients],
                'activite_commerciale': [dict(a) for a in activite_recente] if activite_recente else []
            }
        except Exception as e:
            logger.error(f"Erreur collecte données CRM: {e}")
            return {}
    
    def _collecter_donnees_production(self) -> Dict[str, Any]:
        """Collecte les données de production pour analyse"""
        try:
            # Charge par poste de travail
            charge_postes = self.db.execute_query("""
                SELECT 
                    wc.nom as poste,
                    COUNT(o.id) as nb_operations,
                    SUM(o.temps_estime) as heures_prevues,
                    SUM(CASE WHEN o.statut = 'EN COURS' THEN 1 ELSE 0 END) as operations_en_cours
                FROM work_centers wc
                LEFT JOIN operations o ON wc.id = o.work_center_id
                WHERE o.statut IN ('À FAIRE', 'EN COURS')
                GROUP BY wc.id
                ORDER BY heures_prevues DESC
            """)
            
            # Performance employés (30 derniers jours)
            performance_employes = self.db.execute_query("""
                SELECT 
                    e.prenom || ' ' || e.nom as employe,
                    COUNT(DISTINCT te.id) as nb_pointages,
                    SUM(te.heures) as heures_totales,
                    COUNT(DISTINCT te.project_id) as nb_projets
                FROM employees e
                LEFT JOIN time_entries te ON e.id = te.employee_id
                WHERE date(te.punch_in) >= date('now', '-30 days')
                GROUP BY e.id
                ORDER BY heures_totales DESC
                LIMIT 10
            """)
            
            return {
                'charge_postes': [dict(c) for c in charge_postes],
                'performance_employes': [dict(p) for p in performance_employes]
            }
        except Exception as e:
            logger.error(f"Erreur collecte données production: {e}")
            return {}
    
    # =========================================================================
    # ANALYSE IA AVEC CLAUDE
    # =========================================================================
    
    def analyser_situation_globale(self) -> Dict[str, Any]:
        """Analyse globale de la situation de l'entreprise"""
        if not self.client:
            return {
                'success': False,
                'error': "Assistant IA non configuré. Veuillez ajouter votre clé API Claude."
            }
        
        try:
            # Collecter toutes les données
            donnees = {
                'projets': self._collecter_donnees_projets(),
                'inventaire': self._collecter_donnees_inventaire(),
                'crm': self._collecter_donnees_crm(),
                'production': self._collecter_donnees_production(),
                'date_analyse': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
            
            # Préparer le contexte pour Claude
            contexte = f"""
            Analyse ERP du {donnees['date_analyse']}:
            
            PROJETS:
            - {donnees['projets']['nb_projets_actifs']} projets actifs
            - Durée moyenne: {donnees['projets']['statistiques'].get('duree_moy_jours', 0):.1f} jours
            - Budget moyen: ${donnees['projets']['statistiques'].get('budget_moyen', 0):,.2f}
            
            INVENTAIRE:
            - {donnees['inventaire']['nb_alertes']} articles en alerte stock
            - {donnees['inventaire']['valeur_inventaire'].get('nb_articles', 0)} articles totaux
            
            CRM:
            - {len(donnees['crm']['top_clients'])} clients actifs
            - Opportunités en cours: {sum(o['nombre'] for o in donnees['crm']['opportunites'] if o['statut'] != 'Perdu')}
            
            PRODUCTION:
            - {len(donnees['production']['charge_postes'])} postes de travail actifs
            - {sum(p['heures_totales'] for p in donnees['production']['performance_employes'])} heures travaillées (30j)
            """
            
            # Appel à Claude pour analyse
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": f"""En tant qu'expert en gestion d'entreprise et ERP, analysez ces données et fournissez:

1. **Résumé exécutif** (3-4 points clés)
2. **Points forts** identifiés
3. **Alertes et risques** à surveiller
4. **Recommandations prioritaires** (3-5 actions)
5. **Indicateurs à suivre**

Données détaillées:
{contexte}

Détails supplémentaires:
{json.dumps(donnees, indent=2, default=str)}

Répondez de manière structurée et professionnelle."""
                }]
            )
            
            return {
                'success': True,
                'analyse': response.content[0].text,
                'donnees_analysees': donnees,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse IA: {e}")
            return {
                'success': False,
                'error': f"Erreur lors de l'analyse: {str(e)}"
            }
    
    def analyser_projet_specifique(self, project_id: str) -> Dict[str, Any]:
        """Analyse approfondie d'un projet spécifique"""
        if not self.client:
            return {'success': False, 'error': "Assistant IA non configuré"}
        
        try:
            # Récupérer les données du projet
            projet = self.db.execute_query("""
                SELECT p.*, c.nom as client_nom
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE p.id = ?
            """, (project_id,))
            
            if not projet:
                return {'success': False, 'error': "Projet non trouvé"}
            
            projet_data = dict(projet[0])
            
            # Opérations du projet
            operations = self.db.execute_query("""
                SELECT o.*, wc.nom as poste_travail
                FROM operations o
                LEFT JOIN work_centers wc ON o.work_center_id = wc.id
                WHERE o.project_id = ?
                ORDER BY o.sequence_number
            """, (project_id,))
            
            # Temps pointés
            temps = self.db.execute_query("""
                SELECT 
                    te.*,
                    e.prenom || ' ' || e.nom as employe_nom
                FROM time_entries te
                LEFT JOIN employees e ON te.employee_id = e.id
                WHERE te.project_id = ?
                ORDER BY te.punch_in DESC
            """, (project_id,))
            
            # Matériaux
            materiaux = self.db.execute_query("""
                SELECT * FROM materials
                WHERE project_id = ?
            """, (project_id,))
            
            # Calculs de performance
            heures_prevues = sum(o['temps_estime'] for o in operations)
            heures_reelles = sum(t['heures'] for t in temps)
            taux_avancement = len([o for o in operations if o['statut'] == 'TERMINÉ']) / len(operations) * 100 if operations else 0
            
            # Contexte pour Claude
            contexte = f"""
            Projet: {projet_data['nom_projet']}
            Client: {projet_data['client_nom']}
            Statut: {projet_data['statut']}
            Budget: ${projet_data.get('prix_estime', 0):,.2f}
            
            Performance:
            - Heures prévues: {heures_prevues:.1f}h
            - Heures réelles: {heures_reelles:.1f}h
            - Écart: {((heures_reelles/heures_prevues - 1) * 100 if heures_prevues > 0 else 0):.1f}%
            - Avancement: {taux_avancement:.1f}%
            
            Opérations: {len(operations)} étapes
            Employés impliqués: {len(set(t['employe_nom'] for t in temps))}
            Matériaux: {len(materiaux)} items
            """
            
            # Analyse par Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": f"""Analysez ce projet de production et fournissez:

1. **État du projet** (santé globale)
2. **Risques identifiés** 
3. **Optimisations possibles**
4. **Prochaines étapes recommandées**

{contexte}

Soyez précis et orienté action."""
                }]
            )
            
            return {
                'success': True,
                'analyse': response.content[0].text,
                'metriques': {
                    'heures_prevues': heures_prevues,
                    'heures_reelles': heures_reelles,
                    'taux_avancement': taux_avancement,
                    'budget': projet_data.get('prix_estime', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse projet: {e}")
            return {'success': False, 'error': str(e)}
    
    def generer_rapport_previsionnel(self, horizon_jours: int = 30) -> Dict[str, Any]:
        """Génère un rapport prévisionnel pour les prochains jours"""
        if not self.client:
            return {'success': False, 'error': "Assistant IA non configuré"}
        
        try:
            date_fin = datetime.now() + timedelta(days=horizon_jours)
            
            # Projets à livrer
            projets_a_livrer = self.db.execute_query("""
                SELECT * FROM projects
                WHERE date_prevu <= ? AND statut != 'TERMINÉ'
                ORDER BY date_prevu
            """, (date_fin.strftime('%Y-%m-%d'),))
            
            # Charge prévisionnelle
            charge_prevue = self.db.execute_query("""
                SELECT 
                    wc.nom as poste,
                    SUM(o.temps_estime) as heures_totales
                FROM operations o
                JOIN work_centers wc ON o.work_center_id = wc.id
                JOIN projects p ON o.project_id = p.id
                WHERE p.date_prevu <= ? AND o.statut != 'TERMINÉ'
                GROUP BY wc.id
            """, (date_fin.strftime('%Y-%m-%d'),))
            
            # Capacité disponible (estimation)
            nb_employes_actifs = len(self.db.execute_query("SELECT id FROM employees WHERE statut = 'ACTIF'"))
            capacite_totale = nb_employes_actifs * 8 * (horizon_jours * 5/7)  # 8h/jour, 5j/7
            
            contexte = f"""
            Analyse prévisionnelle sur {horizon_jours} jours:
            
            - {len(projets_a_livrer)} projets à terminer
            - Charge totale: {sum(c['heures_totales'] for c in charge_prevue):.0f} heures
            - Capacité disponible: {capacite_totale:.0f} heures ({nb_employes_actifs} employés)
            
            Répartition par poste:
            {json.dumps([dict(c) for c in charge_prevue], indent=2)}
            """
            
            # Analyse prévisionnelle par Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1200,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": f"""En tant qu'expert en planification de production, analysez cette situation prévisionnelle:

{contexte}

Fournissez:
1. **Analyse de capacité** (suffisante ou non?)
2. **Goulots d'étranglement** identifiés
3. **Plan d'action** pour respecter les délais
4. **Ressources additionnelles** nécessaires
5. **Risques majeurs** à anticiper

Soyez pragmatique et orienté solutions."""
                }]
            )
            
            return {
                'success': True,
                'analyse': response.content[0].text,
                'donnees': {
                    'projets_a_livrer': len(projets_a_livrer),
                    'charge_totale': sum(c['heures_totales'] for c in charge_prevue),
                    'capacite_disponible': capacite_totale,
                    'taux_charge': (sum(c['heures_totales'] for c in charge_prevue) / capacite_totale * 100) if capacite_totale > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur rapport prévisionnel: {e}")
            return {'success': False, 'error': str(e)}
    
    # =========================================================================
    # INTERFACE CONVERSATIONNELLE
    # =========================================================================
    
    def repondre_question(self, question: str, contexte_additionnel: Optional[Dict] = None) -> str:
        """Répond à une question libre de l'utilisateur"""
        if not self.client:
            return "❌ Assistant IA non configuré. Veuillez configurer votre clé API Claude."
        
        try:
            # Collecter un contexte minimal pour aider Claude
            stats_rapides = {
                'nb_projets_actifs': self.db.execute_query("SELECT COUNT(*) as nb FROM projects WHERE statut = 'EN COURS'")[0]['nb'],
                'nb_employes': self.db.execute_query("SELECT COUNT(*) as nb FROM employees WHERE statut = 'ACTIF'")[0]['nb'],
                'nb_clients': self.db.execute_query("SELECT COUNT(*) as nb FROM companies")[0]['nb'],
                'nb_articles_inventaire': self.db.execute_query("SELECT COUNT(*) as nb FROM inventory_items")[0]['nb']
            }
            
            contexte_erp = f"""
            Contexte ERP actuel:
            - Projets en cours: {stats_rapides['nb_projets_actifs']}
            - Employés actifs: {stats_rapides['nb_employes']}
            - Clients: {stats_rapides['nb_clients']}
            - Articles inventaire: {stats_rapides['nb_articles_inventaire']}
            """
            
            if contexte_additionnel:
                contexte_erp += f"\n\nContexte additionnel:\n{json.dumps(contexte_additionnel, indent=2, default=str)}"
            
            # Appel à Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": f"""En tant qu'assistant IA de l'ERP Production DG Inc., répondez à cette question:

Question: {question}

{contexte_erp}

Répondez de manière claire, concise et professionnelle. Si la question nécessite des données spécifiques que vous n'avez pas, suggérez comment les obtenir."""
                }]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Erreur réponse question: {e}")
            return f"❌ Erreur: {str(e)}"
    
    # =========================================================================
    # SUGGESTIONS AUTOMATIQUES
    # =========================================================================
    
    def generer_suggestions_quotidiennes(self) -> List[Dict[str, str]]:
        """Génère des suggestions d'actions quotidiennes"""
        suggestions = []
        
        try:
            # Vérifier les stocks bas
            stocks_bas = self.db.execute_query("""
                SELECT nom, quantite_metric, limite_minimale_metric
                FROM inventory_items
                WHERE quantite_metric <= limite_minimale_metric * 1.2
                ORDER BY (quantite_metric / NULLIF(limite_minimale_metric, 0))
                LIMIT 5
            """)
            
            if stocks_bas:
                suggestions.append({
                    'type': 'inventaire',
                    'priorite': 'haute',
                    'titre': f"🚨 {len(stocks_bas)} articles en stock critique",
                    'description': f"Articles à réapprovisionner: {', '.join(s['nom'] for s in stocks_bas[:3])}...",
                    'action': 'Voir l\'inventaire'
                })
            
            # Projets en retard
            projets_retard = self.db.execute_query("""
                SELECT nom_projet, date_prevu
                FROM projects
                WHERE date_prevu < date('now') AND statut != 'TERMINÉ'
                LIMIT 3
            """)
            
            if projets_retard:
                suggestions.append({
                    'type': 'projet',
                    'priorite': 'critique',
                    'titre': f"⏰ {len(projets_retard)} projets en retard",
                    'description': f"Projets à réviser: {', '.join(p['nom_projet'] for p in projets_retard)}",
                    'action': 'Voir les projets'
                })
            
            # Opportunités CRM à suivre
            opportunites_chaudes = self.db.execute_query("""
                SELECT COUNT(*) as nb
                FROM crm_opportunities
                WHERE statut IN ('Proposition', 'Négociation')
                AND updated_at < date('now', '-7 days')
            """)
            
            if opportunites_chaudes and opportunites_chaudes[0]['nb'] > 0:
                suggestions.append({
                    'type': 'crm',
                    'priorite': 'moyenne',
                    'titre': f"💼 {opportunites_chaudes[0]['nb']} opportunités à relancer",
                    'description': "Des opportunités commerciales nécessitent un suivi",
                    'action': 'Voir le CRM'
                })
            
            # Employés sans pointage récent
            employes_inactifs = self.db.execute_query("""
                SELECT COUNT(DISTINCT e.id) as nb
                FROM employees e
                WHERE e.statut = 'ACTIF'
                AND e.id NOT IN (
                    SELECT DISTINCT employee_id 
                    FROM time_entries 
                    WHERE date(punch_in) >= date('now', '-3 days')
                )
            """)
            
            if employes_inactifs and employes_inactifs[0]['nb'] > 0:
                suggestions.append({
                    'type': 'rh',
                    'priorite': 'basse',
                    'titre': f"👥 {employes_inactifs[0]['nb']} employés sans pointage récent",
                    'description': "Vérifier les pointages de temps",
                    'action': 'Voir le timetracker'
                })
            
        except Exception as e:
            logger.error(f"Erreur génération suggestions: {e}")
        
        return sorted(suggestions, key=lambda x: {'critique': 0, 'haute': 1, 'moyenne': 2, 'basse': 3}[x['priorite']])
    
    # =========================================================================
    # VISUALISATIONS INTELLIGENTES
    # =========================================================================
    
    def creer_dashboard_insights(self) -> Dict[str, Any]:
        """Crée un dashboard avec visualisations et insights"""
        try:
            # Evolution CA sur 6 mois
            evolution_ca = self.db.execute_query("""
                SELECT 
                    strftime('%Y-%m', created_at) as mois,
                    COUNT(*) as nb_projets,
                    SUM(prix_estime) as ca_total
                FROM projects
                WHERE created_at >= date('now', '-6 months')
                GROUP BY strftime('%Y-%m', created_at)
                ORDER BY mois
            """)
            
            # Répartition charge par poste
            charge_postes = self.db.execute_query("""
                SELECT 
                    wc.nom as poste,
                    COUNT(o.id) as nb_operations,
                    SUM(o.temps_estime) as heures_totales
                FROM work_centers wc
                LEFT JOIN operations o ON wc.id = o.work_center_id AND o.statut != 'TERMINÉ'
                GROUP BY wc.id
                HAVING heures_totales > 0
                ORDER BY heures_totales DESC
            """)
            
            # Top 5 clients
            top_clients = self.db.execute_query("""
                SELECT 
                    c.nom as client,
                    COUNT(p.id) as nb_projets,
                    SUM(p.prix_estime) as ca_total
                FROM companies c
                JOIN projects p ON c.id = p.client_company_id
                WHERE p.created_at >= date('now', '-12 months')
                GROUP BY c.id
                ORDER BY ca_total DESC
                LIMIT 5
            """)
            
            # Créer les graphiques Plotly
            fig_ca = go.Figure(data=[
                go.Bar(
                    x=[e['mois'] for e in evolution_ca],
                    y=[e['ca_total'] for e in evolution_ca],
                    text=[f"${e['ca_total']:,.0f}" for e in evolution_ca],
                    textposition='auto',
                    marker_color='#00A971'
                )
            ])
            fig_ca.update_layout(
                title="Évolution du CA (6 derniers mois)",
                xaxis_title="Mois",
                yaxis_title="Chiffre d'affaires ($)",
                showlegend=False
            )
            
            fig_charge = go.Figure(data=[
                go.Pie(
                    labels=[c['poste'] for c in charge_postes],
                    values=[c['heures_totales'] for c in charge_postes],
                    hole=0.4
                )
            ])
            fig_charge.update_layout(
                title="Répartition de la charge par poste"
            )
            
            fig_clients = go.Figure(data=[
                go.Bar(
                    y=[c['client'] for c in top_clients],
                    x=[c['ca_total'] for c in top_clients],
                    orientation='h',
                    text=[f"${c['ca_total']:,.0f}" for c in top_clients],
                    textposition='auto',
                    marker_color='#1F2937'
                )
            ])
            fig_clients.update_layout(
                title="Top 5 clients (12 derniers mois)",
                xaxis_title="Chiffre d'affaires ($)",
                yaxis_title="Client",
                showlegend=False
            )
            
            return {
                'success': True,
                'graphiques': {
                    'evolution_ca': fig_ca,
                    'charge_postes': fig_charge,
                    'top_clients': fig_clients
                },
                'donnees': {
                    'evolution_ca': evolution_ca,
                    'charge_postes': charge_postes,
                    'top_clients': top_clients
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur création dashboard: {e}")
            return {'success': False, 'error': str(e)}


def show_assistant_ia_page(db):
    """Interface Streamlit pour l'assistant IA"""
    st.title("🤖 Assistant IA Claude")
    st.markdown("---")
    
    # Vérifier la configuration
    api_key = os.environ.get('CLAUDE_API_KEY') or st.session_state.get('claude_api_key')
    
    if not api_key:
        st.warning("⚠️ Configuration requise")
        st.info("""
        Pour utiliser l'assistant IA, vous devez configurer votre clé API Claude :
        
        1. Obtenez une clé API sur [console.anthropic.com](https://console.anthropic.com/)
        2. Ajoutez la variable d'environnement `CLAUDE_API_KEY`
        3. Ou entrez-la ci-dessous (temporaire)
        """)
        
        temp_key = st.text_input("Clé API Claude (temporaire)", type="password")
        if temp_key:
            st.session_state['claude_api_key'] = temp_key
            st.rerun()
        return
    
    # Initialiser l'assistant
    assistant = AssistantIAClaude(db, api_key)
    
    # Onglets principaux
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Tableau de bord IA",
        "💬 Chat Assistant", 
        "📈 Analyses",
        "🔮 Prévisions",
        "💡 Suggestions"
    ])
    
    with tab1:
        st.header("Tableau de bord intelligent")
        
        # Métriques rapides avec IA
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            projets_actifs = db.execute_query("SELECT COUNT(*) as nb FROM projects WHERE statut = 'EN COURS'")[0]['nb']
            st.metric("Projets actifs", projets_actifs)
        
        with col2:
            alertes_stock = db.execute_query("SELECT COUNT(*) as nb FROM inventory_items WHERE quantite_metric <= limite_minimale_metric")[0]['nb']
            st.metric("Alertes stock", alertes_stock, delta=None if alertes_stock == 0 else f"+{alertes_stock}", delta_color="inverse")
        
        with col3:
            ca_mois = db.execute_query("SELECT SUM(prix_estime) as ca FROM projects WHERE created_at >= date('now', 'start of month')")[0]['ca'] or 0
            st.metric("CA du mois", f"${ca_mois:,.0f}")
        
        with col4:
            employes_actifs = db.execute_query("SELECT COUNT(*) as nb FROM employees WHERE statut = 'ACTIF'")[0]['nb']
            st.metric("Employés actifs", employes_actifs)
        
        # Dashboard visuel
        with st.spinner("Création du dashboard intelligent..."):
            dashboard = assistant.creer_dashboard_insights()
            
            if dashboard['success']:
                # Graphiques
                col1, col2 = st.columns(2)
                
                with col1:
                    st.plotly_chart(dashboard['graphiques']['evolution_ca'], use_container_width=True)
                
                with col2:
                    st.plotly_chart(dashboard['graphiques']['charge_postes'], use_container_width=True)
                
                st.plotly_chart(dashboard['graphiques']['top_clients'], use_container_width=True)
                
                # Analyse IA globale
                if st.button("🧠 Générer analyse IA complète", type="primary"):
                    with st.spinner("Claude analyse vos données..."):
                        analyse = assistant.analyser_situation_globale()
                        
                        if analyse['success']:
                            st.success("✅ Analyse complétée")
                            
                            # Afficher l'analyse dans un container stylé
                            with st.container():
                                st.markdown("""
                                <div style='background-color: #f0f8ff; padding: 20px; border-radius: 10px; border-left: 5px solid #00A971;'>
                                """, unsafe_allow_html=True)
                                
                                st.markdown(analyse['analyse'])
                                
                                st.markdown("</div>", unsafe_allow_html=True)
                                
                                # Bouton pour télécharger l'analyse
                                st.download_button(
                                    label="📥 Télécharger le rapport",
                                    data=analyse['analyse'],
                                    file_name=f"analyse_ia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                    mime="text/plain"
                                )
                        else:
                            st.error(f"❌ {analyse['error']}")
    
    with tab2:
        st.header("Chat avec l'assistant IA")
        
        # Historique des conversations
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # Zone de chat
        chat_container = st.container()
        
        with chat_container:
            # Afficher l'historique
            for message in st.session_state.chat_history:
                if message['role'] == 'user':
                    st.markdown(f"**Vous:** {message['content']}")
                else:
                    with st.container():
                        st.markdown(f"**Claude:** {message['content']}")
                        st.markdown("---")
        
        # Zone de saisie
        col1, col2 = st.columns([5, 1])
        
        with col1:
            question = st.text_input("Posez votre question...", placeholder="Ex: Quel est le projet le plus rentable ce mois-ci?")
        
        with col2:
            if st.button("Envoyer", type="primary"):
                if question:
                    # Ajouter la question à l'historique
                    st.session_state.chat_history.append({'role': 'user', 'content': question})
                    
                    # Obtenir la réponse
                    with st.spinner("Claude réfléchit..."):
                        reponse = assistant.repondre_question(question)
                    
                    # Ajouter la réponse à l'historique
                    st.session_state.chat_history.append({'role': 'assistant', 'content': reponse})
                    
                    # Recharger pour afficher
                    st.rerun()
        
        # Bouton pour effacer l'historique
        if st.button("🗑️ Effacer la conversation"):
            st.session_state.chat_history = []
            st.rerun()
        
        # Questions suggérées
        st.subheader("💡 Questions suggérées")
        
        suggestions = [
            "Quels sont les projets les plus en retard?",
            "Analyse la performance de production de ce mois",
            "Quels articles d'inventaire nécessitent un réapprovisionnement urgent?",
            "Quelle est la charge de travail prévue pour les 2 prochaines semaines?",
            "Quels sont nos meilleurs clients en termes de rentabilité?"
        ]
        
        cols = st.columns(2)
        for i, suggestion in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(suggestion, key=f"sugg_{i}"):
                    st.session_state.chat_history.append({'role': 'user', 'content': suggestion})
                    with st.spinner("Claude réfléchit..."):
                        reponse = assistant.repondre_question(suggestion)
                    st.session_state.chat_history.append({'role': 'assistant', 'content': reponse})
                    st.rerun()
    
    with tab3:
        st.header("Analyses approfondies")
        
        # Sélection du type d'analyse
        type_analyse = st.selectbox(
            "Type d'analyse",
            ["Projet spécifique", "Portefeuille clients", "Performance production", "Santé inventaire"]
        )
        
        if type_analyse == "Projet spécifique":
            # Liste des projets actifs
            projets = db.execute_query("""
                SELECT id, nom_projet, statut, client_nom_cache
                FROM projects
                WHERE statut IN ('EN COURS', 'À FAIRE')
                ORDER BY created_at DESC
            """)
            
            if projets:
                projet_selectionne = st.selectbox(
                    "Sélectionnez un projet",
                    options=projets,
                    format_func=lambda p: f"{p['nom_projet']} - {p['client_nom_cache']} ({p['statut']})"
                )
                
                if st.button("🔍 Analyser ce projet"):
                    with st.spinner("Analyse en cours..."):
                        analyse = assistant.analyser_projet_specifique(projet_selectionne['id'])
                        
                        if analyse['success']:
                            # Métriques du projet
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("Heures prévues", f"{analyse['metriques']['heures_prevues']:.1f}h")
                            
                            with col2:
                                st.metric("Heures réelles", f"{analyse['metriques']['heures_reelles']:.1f}h")
                            
                            with col3:
                                ecart = ((analyse['metriques']['heures_reelles'] / analyse['metriques']['heures_prevues'] - 1) * 100) if analyse['metriques']['heures_prevues'] > 0 else 0
                                st.metric("Écart", f"{ecart:+.1f}%", delta=f"{ecart:.1f}%")
                            
                            with col4:
                                st.metric("Avancement", f"{analyse['metriques']['taux_avancement']:.0f}%")
                            
                            # Analyse IA
                            st.markdown("### 🧠 Analyse Claude")
                            st.markdown(analyse['analyse'])
                        else:
                            st.error(analyse['error'])
    
    with tab4:
        st.header("Analyses prévisionnelles")
        
        # Paramètres de prévision
        col1, col2 = st.columns(2)
        
        with col1:
            horizon = st.slider("Horizon de prévision (jours)", 7, 90, 30)
        
        with col2:
            st.info(f"Analyse sur {horizon} jours ({horizon/7:.1f} semaines)")
        
        if st.button("🔮 Générer prévisions", type="primary"):
            with st.spinner("Génération des prévisions..."):
                previsions = assistant.generer_rapport_previsionnel(horizon)
                
                if previsions['success']:
                    # Métriques prévisionnelles
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Projets à livrer", previsions['donnees']['projets_a_livrer'])
                    
                    with col2:
                        st.metric("Charge totale", f"{previsions['donnees']['charge_totale']:.0f}h")
                    
                    with col3:
                        st.metric("Capacité disponible", f"{previsions['donnees']['capacite_disponible']:.0f}h")
                    
                    with col4:
                        taux = previsions['donnees']['taux_charge']
                        color = "normal" if taux < 80 else "inverse" if taux < 100 else "off"
                        st.metric("Taux de charge", f"{taux:.0f}%", delta=None, delta_color=color)
                    
                    # Rapport IA
                    st.markdown("### 📊 Analyse prévisionnelle")
                    st.markdown(previsions['analyse'])
                    
                    # Graphique de charge
                    if taux > 0:
                        fig = go.Figure(go.Indicator(
                            mode="gauge+number+delta",
                            value=taux,
                            title={'text': "Taux de charge prévisionnel"},
                            domain={'x': [0, 1], 'y': [0, 1]},
                            gauge={
                                'axis': {'range': [None, 120]},
                                'bar': {'color': "#00A971" if taux < 80 else "#F59E0B" if taux < 100 else "#EF4444"},
                                'steps': [
                                    {'range': [0, 80], 'color': "#E8F5E9"},
                                    {'range': [80, 100], 'color': "#FFF3E0"},
                                    {'range': [100, 120], 'color': "#FFEBEE"}
                                ],
                                'threshold': {
                                    'line': {'color': "red", 'width': 4},
                                    'thickness': 0.75,
                                    'value': 100
                                }
                            }
                        ))
                        
                        fig.update_layout(height=300)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error(previsions['error'])
    
    with tab5:
        st.header("Suggestions et recommandations")
        
        # Générer les suggestions
        suggestions = assistant.generer_suggestions_quotidiennes()
        
        if suggestions:
            st.info(f"🎯 {len(suggestions)} suggestions identifiées")
            
            for i, suggestion in enumerate(suggestions):
                # Couleur selon priorité
                couleur = {
                    'critique': '#EF4444',
                    'haute': '#F59E0B',
                    'moyenne': '#3B82F6',
                    'basse': '#6B7280'
                }[suggestion['priorite']]
                
                # Afficher la suggestion
                with st.container():
                    st.markdown(f"""
                    <div style='background-color: {couleur}22; border-left: 4px solid {couleur}; 
                                padding: 15px; margin: 10px 0; border-radius: 5px;'>
                        <h4 style='margin: 0; color: {couleur};'>{suggestion['titre']}</h4>
                        <p style='margin: 5px 0;'>{suggestion['description']}</p>
                        <small style='color: #666;'>Priorité: {suggestion['priorite'].upper()}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(suggestion['action'], key=f"action_{i}"):
                        st.info(f"Redirection vers {suggestion['type']}...")
        else:
            st.success("✅ Aucune action urgente requise!")
            st.balloons()
        
        # Section insights automatiques
        st.subheader("🎯 Insights automatiques")
        
        if st.button("Générer de nouveaux insights"):
            with st.spinner("Recherche d'insights..."):
                # Ici on pourrait ajouter plus d'analyses automatiques
                st.info("Cette fonctionnalité sera enrichie avec plus d'analyses automatiques.")