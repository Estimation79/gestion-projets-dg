# --- START OF FILE projects.py ---
# Module de gestion des projets pour ERP Production DG Inc.

import streamlit as st
from datetime import datetime

# Assure-toi que la classe ERPDatabase est importable si elle est utilisée
# Normalement, elle est déjà passée en argument, donc pas besoin d'import direct.
# from erp_database import ERPDatabase

class GestionnaireProjetSQL:
    """
    ARCHITECTURE MODULAIRE : Gestionnaire de projets utilisant SQLite
    Extrait de app.py pour une meilleure organisation et pour résoudre les problèmes de dépendance.
    """

    def __init__(self, db): # db est une instance de ERPDatabase
        self.db = db
        self.next_id = 10000
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
            # Utiliser st.error si dans un contexte Streamlit, sinon print
            if 'st' in globals():
                st.error(f"Erreur initialisation next_id pour projets: {e}")
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
            projets = [dict(row) for row in rows] if rows else []
            return projets

        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur récupération projets: {e}")
            return []

    def ajouter_projet(self, projet_data):
        """Ajoute un nouveau projet en SQLite"""
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

            # Insérer projet principal
            query = '''
                INSERT INTO projects
                (id, nom_projet, client_company_id, client_nom_cache, statut, priorite, tache, date_soumis, date_prevu, bd_ft_estime, prix_estime, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            prix_estime = float(str(projet_data.get('prix_estime', 0)).replace('$', '').replace(',', '')) if projet_data.get('prix_estime') else 0
            bd_ft_estime = float(projet_data.get('bd_ft_estime', 0)) if projet_data.get('bd_ft_estime') else 0

            self.db.execute_insert(query, (
                project_id,
                projet_data.get('nom_projet'),
                projet_data.get('client_company_id'),
                projet_data.get('client_nom_cache'),
                projet_data.get('statut', 'À FAIRE'),
                projet_data.get('priorite', 'MOYEN'),
                projet_data.get('tache'),
                projet_data.get('date_soumis'),
                projet_data.get('date_prevu'),
                bd_ft_estime,
                prix_estime,
                projet_data.get('description')
            ))
            
            # Insérer assignations employés
            employes_assignes = projet_data.get('employes_assignes', [])
            for emp_id in employes_assignes:
                self.db.execute_update(
                    "INSERT OR IGNORE INTO project_assignments (project_id, employee_id, role_projet) VALUES (?, ?, ?)",
                    (project_id, emp_id, 'Membre équipe')
                )

            self.next_id += 1
            return project_id

        except ValueError as ve:
            if 'st' in globals():
                st.error(f"Erreur validation projet: {ve}")
            return None
        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur technique ajout projet: {e}")
            return None

    def modifier_projet(self, projet_id, projet_data_update):
        """Modifie un projet existant"""
        try:
            update_fields = []
            params = []

            for field, value in projet_data_update.items():
                if field in ['nom_projet', 'client_company_id', 'client_nom_cache', 'statut', 'priorite', 'tache', 'date_soumis', 'date_prevu', 'bd_ft_estime', 'prix_estime', 'description']:
                    update_fields.append(f"{field} = ?")
                    params.append(value)
            
            if not update_fields:
                return True # Rien à modifier sur le projet principal
            
            query = f"UPDATE projects SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            params.append(projet_id)
            self.db.execute_update(query, tuple(params))
            return True

        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur modification projet: {e}")
            return False

    def supprimer_projet(self, projet_id):
        """Supprime un projet et ses données associées"""
        try:
            self.db.execute_update("DELETE FROM project_assignments WHERE project_id = ?", (projet_id,))
            self.db.execute_update("DELETE FROM operations WHERE project_id = ?", (projet_id,))
            self.db.execute_update("DELETE FROM materials WHERE project_id = ?", (projet_id,))
            self.db.execute_update("DELETE FROM time_entries WHERE project_id = ?", (projet_id,))
            self.db.execute_update("DELETE FROM formulaires WHERE project_id = ?", (projet_id,))
            self.db.execute_update("DELETE FROM projects WHERE id = ?", (projet_id,))
            return True
        except Exception as e:
            if 'st' in globals():
                st.error(f"Erreur suppression projet: {e}")
            return False

# --- END OF FILE projects.py ---
