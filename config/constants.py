# config/constants.py
"""
Constantes globales pour l'ERP Production DG Inc.
"""

# Configuration de l'application
APP_CONFIG = {
    "title": "🚀 ERP Production DG Inc.",
    "icon": "🏭",
    "layout": "wide",
    "sidebar_state": "expanded"
}

# Types et statuts
TYPES_INTERACTION = ["Email", "Appel", "Réunion", "Note", "Autre"]
STATUTS_OPPORTUNITE = ["Prospection", "Qualification", "Proposition", "Négociation", "Gagné", "Perdu"]

# Inventaire
UNITES_MESURE = ["IMPÉRIAL", "MÉTRIQUE"]
TYPES_PRODUITS_INVENTAIRE = ["BOIS", "MÉTAL", "QUINCAILLERIE", "OUTILLAGE", "MATÉRIAUX", "ACCESSOIRES", "AUTRE"]
STATUTS_STOCK_INVENTAIRE = ["DISPONIBLE", "FAIBLE", "CRITIQUE", "EN COMMANDE", "ÉPUISÉ", "INDÉTERMINÉ"]

# Projets
STATUTS_PROJET = ["À FAIRE", "EN COURS", "EN ATTENTE", "TERMINÉ", "ANNULÉ", "LIVRAISON"]
PRIORITES_PROJET = ["BAS", "MOYEN", "ÉLEVÉ"]
TYPES_TACHE = ["ESTIMATION", "CONCEPTION", "DÉVELOPPEMENT", "TESTS", "DÉPLOIEMENT", "MAINTENANCE", "FORMATION", "PRODUCTION"]

# Employés
STATUTS_EMPLOYE = ["ACTIF", "INACTIF", "CONGÉ", "FORMATION"]
POSTES_EMPLOYE = ["Opérateur CNC", "Soudeur", "Usineur", "Contrôleur Qualité", "Logisticien", "Programmeur", "Chef d'équipe", "Technicien"]

# Couleurs pour les graphiques
COLORS = {
    'statut': {
        'À FAIRE': '#f59e0b',
        'EN COURS': '#3b82f6', 
        'EN ATTENTE': '#ef4444',
        'TERMINÉ': '#10b981',
        'ANNULÉ': '#6b7280',
        'LIVRAISON': '#8b5cf6'
    },
    'priorite': {
        'ÉLEVÉ': '#ef4444',
        'MOYEN': '#f59e0b', 
        'BAS': '#10b981'
    },
    'departement': {
        'PRODUCTION': '#10b981',
        'USINAGE': '#3b82f6',
        'QUALITE': '#f59e0b',
        'LOGISTIQUE': '#8b5cf6',
        'COMMERCIAL': '#ef4444'
    }
}

# Configuration des graphiques
CHART_CONFIG = {
    'plot_bgcolor': 'rgba(0,0,0,0)',
    'paper_bgcolor': 'rgba(0,0,0,0)',
    'font': {'color': 'var(--text-color)'},
    'title_x': 0.5
}
