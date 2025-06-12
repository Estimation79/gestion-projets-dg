# models/projects.py
"""
Gestionnaire de projets pour l'ERP Production DG Inc.
"""

import json
import os
from datetime import datetime, timedelta


class GestionnaireProjetIA:
    """Gestionnaire pour les projets avec IDs commençant à 10000"""
    
    def __init__(self):
        self.data_file = "projets_data.json"
        self.projets = []
        self.next_id = 10000  # IDs commencent à 10000
        self.charger_projets()

    def charger_projets(self):
        """Charge les projets depuis le fichier JSON"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.projets = data.get('projets', [])
                    # Calculer le prochain ID en tenant compte du minimum 10000
                    if self.projets:
                        max_id = max(p.get('id', 10000) for p in self.projets)
                        self.next_id = max(max_id + 1, 10000)
                    else:
                        self.next_id = 10000
            else:
                self.projets = self._get_demo_data()
                self.next_id = 10003  # Après les 3 projets de démo
        except Exception as e:
            print(f"Erreur chargement projets: {e}")
            self.projets = self._get_demo_data()
            self.next_id = 10003

    def sauvegarder_projets(self):
        """Sauvegarde les projets dans le fichier JSON"""
        try:
            data = {
                'projets': self.projets, 
                'next_id': self.next_id, 
                'last_update': datetime.now().isoformat()
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur sauvegarde projets: {e}")

    def _get_demo_data(self):
        """Données de démonstration avec IDs à partir de 10000"""
        now_iso = datetime.now().isoformat()
        return [
            {
                'id': 10000,
                'nom_projet': 'Châssis Automobile', 
                'client_entreprise_id': 101, 
                'client_nom_cache': 'AutoTech Corp.', 
                'statut': 'EN COURS', 
                'priorite': 'ÉLEVÉ', 
                'tache': 'PRODUCTION', 
                'date_soumis': '2024-01-15', 
                'date_prevu': '2024-03-15', 
                'bd_ft_estime': '120', 
                'prix_estime': '35000', 
                'description': 'Châssis soudé pour véhicule électrique', 
                'sous_taches': [
                    {'id': 1, 'nom': 'Programmation CNC', 'statut': 'TERMINÉ', 'date_debut': '2024-01-15', 'date_fin': '2024-01-20'}, 
                    {'id': 2, 'nom': 'Découpe laser', 'statut': 'EN COURS', 'date_debut': '2024-01-21', 'date_fin': '2024-02-05'}, 
                    {'id': 3, 'nom': 'Soudage robotisé', 'statut': 'À FAIRE', 'date_debut': '2024-02-06', 'date_fin': '2024-02-20'}
                ], 
                'materiaux': [
                    {'id': 1, 'code': 'ACR-001', 'designation': 'Acier haute résistance', 'quantite': 250, 'unite': 'kg', 'prix_unitaire': 8.5, 'fournisseur': 'Aciers DG'}, 
                    {'id': 2, 'code': 'SOD-001', 'designation': 'Fil de soudage GMAW', 'quantite': 15, 'unite': 'bobines', 'prix_unitaire': 125, 'fournisseur': 'Soudage Pro'}
                ], 
                'operations': [
                    {'id': 1, 'sequence': '10', 'description': 'Programmation Bureau', 'temps_estime': 2.5, 'ressource': 'Programmeur CNC', 'statut': 'TERMINÉ', 'poste_travail': 'Programmation Bureau'}, 
                    {'id': 2, 'sequence': '20', 'description': 'Découpe laser des tôles', 'temps_estime': 4.2, 'ressource': 'Opérateur laser', 'statut': 'EN COURS', 'poste_travail': 'Laser CNC'}, 
                    {'id': 3, 'sequence': '30', 'description': 'Soudage robotisé GMAW', 'temps_estime': 8.5, 'ressource': 'Programmeur robot', 'statut': 'À FAIRE', 'poste_travail': 'Robot ABB GMAW'}
                ], 
                'employes_assignes': [1, 2]
            },
            {
                'id': 10001,
                'nom_projet': 'Structure Industrielle', 
                'client_entreprise_id': 102, 
                'client_nom_cache': 'BâtiTech Inc.', 
                'statut': 'À FAIRE', 
                'priorite': 'MOYEN', 
                'tache': 'ESTIMATION', 
                'date_soumis': '2024-02-01', 
                'date_prevu': '2024-05-01', 
                'bd_ft_estime': '180', 
                'prix_estime': '58000', 
                'description': 'Charpente métallique pour entrepôt industriel', 
                'sous_taches': [], 
                'materiaux': [], 
                'operations': [], 
                'employes_assignes': [2, 3]
            },
            {
                'id': 10002,
                'nom_projet': 'Pièce Aéronautique', 
                'client_entreprise_id': 103, 
                'client_nom_cache': 'AeroSpace Ltd', 
                'statut': 'TERMINÉ', 
                'priorite': 'ÉLEVÉ', 
                'tache': 'LIVRAISON', 
                'date_soumis': '2023-10-01', 
                'date_prevu': '2024-01-31', 
                'bd_ft_estime': '95', 
                'prix_estime': '75000', 
                'description': 'Composant haute précision pour train d\'atterrissage', 
                'sous_taches': [], 
                'materiaux': [], 
                'operations': [], 
                'employes_assignes': [3, 4]
            }
        ]

    def ajouter_projet(self, projet_data):
        """Ajoute un nouveau projet"""
        projet_data['id'] = self.next_id
        self.projets.append(projet_data)
        self.next_id += 1
        self.sauvegarder_projets()
        return projet_data['id']

    def modifier_projet(self, projet_id, projet_data_update):
        """Modifie un projet existant"""
        for i, p in enumerate(self.projets):
            if p['id'] == projet_id:
                self.projets[i].update(projet_data_update)
                self.sauvegarder_projets()
                return True
        return False

    def supprimer_projet(self, projet_id):
        """Supprime un projet"""
        self.projets = [p for p in self.projets if p['id'] != projet_id]
        self.sauvegarder_projets()

    def get_projet_by_id(self, projet_id):
        """Récupère un projet par son ID"""
        return next((p for p in self.projets if p.get('id') == projet_id), None)

    def get_projets_by_statut(self, statut):
        """Récupère les projets par statut"""
        return [p for p in self.projets if p.get('statut') == statut]

    def get_projets_actifs(self):
        """Récupère les projets actifs"""
        statuts_actifs = ['À FAIRE', 'EN COURS', 'EN ATTENTE']
        return [p for p in self.projets if p.get('statut') in statuts_actifs]


def migrer_ids_projets(gestionnaire):
    """Migre tous les projets vers des IDs commençant à 10000"""
    # Trier les projets par ID pour maintenir l'ordre
    projets_tries = sorted(gestionnaire.projets, key=lambda x: x.get('id', 0))
    
    # Réassigner les IDs
    for i, projet in enumerate(projets_tries):
        nouveau_id = 10000 + i
        projet['id'] = nouveau_id
    
    # Mettre à jour le prochain ID
    gestionnaire.next_id = 10000 + len(gestionnaire.projets)
    gestionnaire.sauvegarder_projets()
    
    return len(projets_tries)


def get_project_statistics(gestionnaire):
    """Calcule les statistiques des projets"""
    if not gestionnaire.projets:
        return {
            'total': 0, 
            'par_statut': {}, 
            'par_priorite': {}, 
            'ca_total': 0, 
            'projets_actifs': 0, 
            'taux_completion': 0
        }
    
    stats = {
        'total': len(gestionnaire.projets), 
        'par_statut': {}, 
        'par_priorite': {}, 
        'ca_total': 0, 
        'projets_actifs': 0
    }
    
    for p in gestionnaire.projets:
        # Statistiques par statut
        statut = p.get('statut', 'N/A')
        stats['par_statut'][statut] = stats['par_statut'].get(statut, 0) + 1
        
        # Statistiques par priorité
        priorite = p.get('priorite', 'N/A')
        stats['par_priorite'][priorite] = stats['par_priorite'].get(priorite, 0) + 1
        
        # Calcul CA total
        try:
            prix = p.get('prix_estime', '0')
            prix_str = str(prix).replace(' ', '').replace('€', '').replace('$', '')
            if ',' in prix_str and ('.' not in prix_str or prix_str.find(',') > prix_str.find('.')):
                prix_str = prix_str.replace('.', '').replace(',', '.')
            elif ',' in prix_str and '.' in prix_str and prix_str.find('.') > prix_str.find(','):
                prix_str = prix_str.replace(',', '')
            prix_num = float(prix_str)
            stats['ca_total'] += prix_num
        except (ValueError, TypeError):
            pass
        
        # Projets actifs
        if statut not in ['TERMINÉ', 'ANNULÉ', 'FERMÉ']:
            stats['projets_actifs'] += 1
    
    # Taux de completion
    termines = stats['par_statut'].get('TERMINÉ', 0)
    stats['taux_completion'] = (termines / stats['total'] * 100) if stats['total'] > 0 else 0
    
    return stats
