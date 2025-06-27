# projects.py - Module de gestion des projets pour ERP Production DG Inc.
# ARCHITECTURE MODULAIRE : Gestionnaire de projets utilisant SQLite
# Extrait de app.py pour une meilleure organisation et pour résoudre les problèmes de dépendance.

import streamlit as st
from datetime import datetime, timedelta

class GestionnaireProjetSQL:
    """
    ARCHITECTURE MODULAIRE : Gestionnaire de projets utilisant SQLite
    Extrait de app.py pour une meilleure organisation et pour résoudre les problèmes de dépendance.
    """

    def __init__(self, db):
        self.db = db
        self.next_id = 10000  # Commence à 10000 pour professionnalisme
        self._init_next_id()

    def _init_next_id(self):
        """Initialise le prochain ID basé sur les projets existants"""
        try:
            result = self.db.execute_query("SELECT MAX(id) as max_id FROM projects")
            if result and result[0]['max_id']:
                self.next_id = max(result[0]['max_id'] + 1, 10000)
            else:
                self.next_id = 10000
        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur initialisation next_id: {e}")
            else:
                print(f"Erreur initialisation next_id pour projets: {e}")
            self.next_id = 10000

    @property
    def projets(self):
        """Propriété pour maintenir compatibilité avec l'ancien code"""
        return self.get_all_projects()

    def get_all_projects(self):
        """Récupère tous les projets depuis SQLite"""
        try:
            query = '''
                SELECT p.*, c.nom as client_nom_company
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                ORDER BY p.id DESC
            '''
            rows = self.db.execute_query(query)

            projets = []
            for row in rows:
                projet = dict(row)

                # Récupérer opérations
                operations = self.db.execute_query(
                    "SELECT * FROM operations WHERE project_id = ? ORDER BY sequence_number",
                    (projet['id'],)
                )
                projet['operations'] = [dict(op) for op in operations]

                # Récupérer matériaux
                materiaux = self.db.execute_query(
                    "SELECT * FROM materials WHERE project_id = ?",
                    (projet['id'],)
                )
                projet['materiaux'] = [dict(mat) for mat in materiaux]

                # Récupérer employés assignés
                employes_assignes = self.db.execute_query(
                    "SELECT employee_id FROM project_assignments WHERE project_id = ?",
                    (projet['id'],)
                )
                projet['employes_assignes'] = [row['employee_id'] for row in employes_assignes]

                # Compatibilité avec ancien format
                if not projet.get('client_nom_cache') and projet.get('client_nom_company'):
                    projet['client_nom_cache'] = projet['client_nom_company']

                projets.append(projet)

            return projets

        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur récupération projets: {e}")
            else:
                print(f"Erreur récupération projets: {e}")
            return []

    def ajouter_projet(self, projet_data):
        """Ajoute un nouveau projet en SQLite - VERSION CORRIGÉE avec validation FK"""
        try:
            project_id = self.next_id

            # VALIDATION PRÉALABLE des clés étrangères
            if projet_data.get('client_company_id'):
                company_exists = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM companies WHERE id = ?",
                    (projet_data['client_company_id'],)
                )
                if not company_exists or company_exists[0]['count'] == 0:
                    raise ValueError(f"Entreprise ID {projet_data['client_company_id']} n'existe pas")

            # Validation employés assignés
            employes_assignes = projet_data.get('employes_assignes', [])
            for emp_id in employes_assignes:
                emp_exists = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM employees WHERE id = ?",
                    (emp_id,)
                )
                if not emp_exists or emp_exists[0]['count'] == 0:
                    raise ValueError(f"Employé ID {emp_id} n'existe pas")

            # Insérer projet principal avec gestion NULL
            query = '''
                INSERT INTO projects
                (id, nom_projet, client_company_id, client_nom_cache, client_legacy,
                 statut, priorite, tache, date_soumis, date_prevu, bd_ft_estime,
                 prix_estime, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''

            prix_estime = float(str(projet_data.get('prix_estime', 0)).replace('$', '').replace(',', '')) if projet_data.get('prix_estime') else 0
            bd_ft_estime = float(projet_data.get('bd_ft_estime', 0)) if projet_data.get('bd_ft_estime') else 0

            self.db.execute_update(query, (
                project_id,
                projet_data['nom_projet'],
                projet_data.get('client_company_id'),  # Peut être NULL
                projet_data.get('client_nom_cache'),
                projet_data.get('client_legacy', ''),  # Legacy field
                projet_data.get('statut', 'À FAIRE'),
                projet_data.get('priorite', 'MOYEN'),
                projet_data.get('tache'),
                projet_data.get('date_soumis'),
                projet_data.get('date_prevu'),
                bd_ft_estime,
                prix_estime,
                projet_data.get('description')
            ))

            # Insérer assignations employés (validation déjà faite)
            for emp_id in employes_assignes:
                self.db.execute_update(
                    "INSERT OR IGNORE INTO project_assignments (project_id, employee_id, role_projet) VALUES (?, ?, ?)",
                    (project_id, emp_id, 'Membre équipe')
                )

            self.next_id += 1
            return project_id

        except ValueError as ve:
            if 'st' in globals():
                st.error(f"Erreur validation: {ve}")
            else:
                print(f"Erreur validation projet: {ve}")
            return None
        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur technique ajout projet: {e}")
            else:
                print(f"Erreur technique ajout projet: {e}")
            return None

    def modifier_projet(self, projet_id, projet_data_update):
        """Modifie un projet existant"""
        try:
            # Préparer les champs à mettre à jour
            update_fields = []
            params = []

            for field, value in projet_data_update.items():
                if field in ['nom_projet', 'client_company_id', 'client_nom_cache', 'client_legacy',
                           'statut', 'priorite', 'tache', 'date_soumis', 'date_prevu',
                           'bd_ft_estime', 'prix_estime', 'description']:
                    update_fields.append(f"{field} = ?")

                    # Traitement spécial pour les prix
                    if field == 'prix_estime':
                        value = float(str(value).replace('$', '').replace(',', '')) if value else 0
                    elif field == 'bd_ft_estime':
                        value = float(value) if value else 0

                    params.append(value)

            if update_fields:
                query = f"UPDATE projects SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
                params.append(projet_id)
                self.db.execute_update(query, tuple(params))

            # Mettre à jour assignations employés si fourni
            if 'employes_assignes' in projet_data_update:
                # Supprimer anciennes assignations
                self.db.execute_update("DELETE FROM project_assignments WHERE project_id = ?", (projet_id,))

                # Ajouter nouvelles assignations
                for emp_id in projet_data_update['employes_assignes']:
                    self.db.execute_update(
                        "INSERT INTO project_assignments (project_id, employee_id, role_projet) VALUES (?, ?, ?)",
                        (projet_id, emp_id, 'Membre équipe')
                    )

            return True

        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur modification projet: {e}")
            else:
                print(f"Erreur modification projet: {e}")
            return False

    def supprimer_projet(self, projet_id):
        """Supprime un projet et ses données associées"""
        try:
            # Supprimer en cascade (relations d'abord)
            self.db.execute_update("DELETE FROM project_assignments WHERE project_id = ?", (projet_id,))
            self.db.execute_update("DELETE FROM operations WHERE project_id = ?", (projet_id,))
            self.db.execute_update("DELETE FROM materials WHERE project_id = ?", (projet_id,))
            self.db.execute_update("DELETE FROM time_entries WHERE project_id = ?", (projet_id,))
            self.db.execute_update("DELETE FROM formulaires WHERE project_id = ?", (projet_id,))

            # Supprimer le projet
            self.db.execute_update("DELETE FROM projects WHERE id = ?", (projet_id,))

            return True

        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur suppression projet: {e}")
            else:
                print(f"Erreur suppression projet: {e}")
            return False

    def get_projet_by_id(self, projet_id):
        """Récupère un projet spécifique par son ID"""
        try:
            query = '''
                SELECT p.*, c.nom as client_nom_company
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE p.id = ?
            '''
            rows = self.db.execute_query(query, (projet_id,))
            
            if not rows:
                return None
                
            projet = dict(rows[0])
            
            # Récupérer opérations
            operations = self.db.execute_query(
                "SELECT * FROM operations WHERE project_id = ? ORDER BY sequence_number",
                (projet['id'],)
            )
            projet['operations'] = [dict(op) for op in operations]

            # Récupérer matériaux
            materiaux = self.db.execute_query(
                "SELECT * FROM materials WHERE project_id = ?",
                (projet['id'],)
            )
            projet['materiaux'] = [dict(mat) for mat in materiaux]

            # Récupérer employés assignés
            employes_assignes = self.db.execute_query(
                "SELECT employee_id FROM project_assignments WHERE project_id = ?",
                (projet['id'],)
            )
            projet['employes_assignes'] = [row['employee_id'] for row in employes_assignes]

            # Compatibilité avec ancien format
            if not projet.get('client_nom_cache') and projet.get('client_nom_company'):
                projet['client_nom_cache'] = projet['client_nom_company']

            return projet

        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur récupération projet {projet_id}: {e}")
            else:
                print(f"Erreur récupération projet {projet_id}: {e}")
            return None

    def get_projets_by_client_company_id(self, company_id):
        """Récupère tous les projets d'une entreprise cliente"""
        try:
            query = '''
                SELECT p.*, c.nom as client_nom_company
                FROM projects p
                LEFT JOIN companies c ON p.client_company_id = c.id
                WHERE p.client_company_id = ?
                ORDER BY p.id DESC
            '''
            rows = self.db.execute_query(query, (company_id,))
            
            projets = []
            for row in rows:
                projet = dict(row)
                
                # Récupérer les données associées (simplifié pour la liste)
                operations_count = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM operations WHERE project_id = ?",
                    (projet['id'],)
                )
                projet['operations_count'] = operations_count[0]['count'] if operations_count else 0
                
                materiaux_count = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM materials WHERE project_id = ?",
                    (projet['id'],)
                )
                projet['materiaux_count'] = materiaux_count[0]['count'] if materiaux_count else 0
                
                employes_assignes = self.db.execute_query(
                    "SELECT employee_id FROM project_assignments WHERE project_id = ?",
                    (projet['id'],)
                )
                projet['employes_assignes'] = [row['employee_id'] for row in employes_assignes]
                
                # Compatibilité avec ancien format
                if not projet.get('client_nom_cache') and projet.get('client_nom_company'):
                    projet['client_nom_cache'] = projet['client_nom_company']
                
                projets.append(projet)
            
            return projets

        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur récupération projets pour entreprise {company_id}: {e}")
            else:
                print(f"Erreur récupération projets pour entreprise {company_id}: {e}")
            return []

    def get_project_statistics(self):
        """Récupère les statistiques des projets"""
        try:
            projets = self.get_all_projects()
            
            if not projets:
                return {
                    'total': 0, 
                    'par_statut': {}, 
                    'par_priorite': {}, 
                    'ca_total': 0, 
                    'projets_actifs': 0, 
                    'taux_completion': 0
                }
            
            stats = {
                'total': len(projets), 
                'par_statut': {}, 
                'par_priorite': {}, 
                'ca_total': 0, 
                'projets_actifs': 0
            }
            
            for p in projets:
                # Statistiques par statut
                statut = p.get('statut', 'N/A')
                stats['par_statut'][statut] = stats['par_statut'].get(statut, 0) + 1
                
                # Statistiques par priorité
                priorite = p.get('priorite', 'N/A')
                stats['par_priorite'][priorite] = stats['par_priorite'].get(priorite, 0) + 1
                
                # Calcul du CA total
                try:
                    prix = p.get('prix_estime', '0')
                    s_prix = str(prix).replace(' ', '').replace('€', '').replace('$', '')
                    if ',' in s_prix and ('.' not in s_prix or s_prix.find(',') > s_prix.find('.')):
                        s_prix = s_prix.replace('.', '').replace(',', '.')
                    elif ',' in s_prix and '.' in s_prix and s_prix.find('.') > s_prix.find(','):
                        s_prix = s_prix.replace(',', '')
                    prix_num = float(s_prix)
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

        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur calcul statistiques projets: {e}")
            else:
                print(f"Erreur calcul statistiques projets: {e}")
            return {
                'total': 0, 
                'par_statut': {}, 
                'par_priorite': {}, 
                'ca_total': 0, 
                'projets_actifs': 0, 
                'taux_completion': 0
            }
