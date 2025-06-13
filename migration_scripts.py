# migration_scripts.py - Scripts de Migration JSON → SQLite
# ERP Production DG Inc.

import json
import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from erp_database import ERPDatabase, convertir_pieds_pouces_fractions_en_valeur_decimale, convertir_imperial_vers_metrique

logger = logging.getLogger(__name__)

class MigrationManager:
    """Gestionnaire principal des migrations JSON → SQLite"""
    
    def __init__(self, db: ERPDatabase):
        self.db = db
        self.migration_log = []
    
    def run_full_migration(self) -> Dict[str, Any]:
        """Exécute la migration complète de tous les modules"""
        logger.info("🚀 Début migration complète JSON → SQLite")
        
        # Sauvegarder les fichiers JSON
        self.db.backup_json_files()
        
        migration_results = {
            'start_time': datetime.now().isoformat(),
            'modules': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # 1. Migrer les postes de travail (référence pour les autres)
            result_wc = migrate_work_centers(self.db)
            migration_results['modules']['work_centers'] = result_wc
            
            # 2. Migrer CRM (entreprises et contacts d'abord)
            result_crm = migrate_crm_data(self.db)
            migration_results['modules']['crm'] = result_crm
            
            # 3. Migrer employés
            result_emp = migrate_employees_data(self.db)
            migration_results['modules']['employees'] = result_emp
            
            # 4. Migrer projets (dépend de CRM et employés)
            result_proj = migrate_projects_data(self.db)
            migration_results['modules']['projects'] = result_proj
            
            # 5. Migrer inventaire
            result_inv = migrate_inventory_data(self.db)
            migration_results['modules']['inventory'] = result_inv
            
            # 6. Migrer TimeTracker si existe
            result_tt = migrate_timetracker_data(self.db)
            migration_results['modules']['timetracker'] = result_tt
            
            migration_results['end_time'] = datetime.now().isoformat()
            migration_results['success'] = True
            
            # Validation finale
            integrity_check = self.db.validate_integrity()
            migration_results['integrity_check'] = integrity_check
            
            logger.info("✅ Migration complète terminée avec succès")
            
        except Exception as e:
            migration_results['success'] = False
            migration_results['error'] = str(e)
            migration_results['end_time'] = datetime.now().isoformat()
            logger.error(f"❌ Erreur migration : {e}")
        
        return migration_results

def migrate_work_centers(db: ERPDatabase) -> Dict[str, Any]:
    """Migre les 61 postes de travail dans la base SQLite"""
    logger.info("📋 Migration des postes de travail...")
    
    try:
        # Import des postes depuis postes_travail.py
        from postes_travail import WORK_CENTERS_DG_INC
        
        migrated_count = 0
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            for poste in WORK_CENTERS_DG_INC:
                # Convertir compétences en JSON string
                competences_json = json.dumps(poste.get('competences', []))
                
                cursor.execute('''
                    INSERT OR REPLACE INTO work_centers 
                    (id, nom, departement, categorie, type_machine, capacite_theorique, 
                     operateurs_requis, cout_horaire, competences_requises)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    poste['id'],
                    poste['nom'],
                    poste['departement'],
                    poste['categorie'],
                    poste['type_machine'],
                    poste['capacite_theorique'],
                    poste['operateurs_requis'],
                    poste['cout_horaire'],
                    competences_json
                ))
                migrated_count += 1
            
            conn.commit()
        
        logger.info(f"✅ {migrated_count} postes de travail migrés")
        return {
            'success': True,
            'migrated_count': migrated_count,
            'total_expected': len(WORK_CENTERS_DG_INC)
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur migration postes: {e}")
        return {'success': False, 'error': str(e)}

def migrate_crm_data(db: ERPDatabase) -> Dict[str, Any]:
    """Migre les données CRM (entreprises, contacts, interactions)"""
    logger.info("🤝 Migration des données CRM...")
    
    if not os.path.exists('crm_data.json'):
        logger.warning("⚠️ Fichier crm_data.json non trouvé")
        return {'success': False, 'error': 'crm_data.json non trouvé'}
    
    try:
        with open('crm_data.json', 'r', encoding='utf-8') as f:
            crm_data = json.load(f)
        
        migrated_counts = {
            'companies': 0,
            'contacts': 0,
            'interactions': 0
        }
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Migrer entreprises
            entreprises = crm_data.get('entreprises', [])
            for entreprise in entreprises:
                cursor.execute('''
                    INSERT OR REPLACE INTO companies 
                    (id, nom, secteur, adresse, site_web, contact_principal_id, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entreprise['id'],
                    entreprise['nom'],
                    entreprise.get('secteur'),
                    entreprise.get('adresse'),
                    entreprise.get('site_web'),
                    entreprise.get('contact_principal_id'),
                    entreprise.get('notes'),
                    entreprise.get('date_creation'),
                    entreprise.get('date_modification')
                ))
                migrated_counts['companies'] += 1
            
            # 2. Migrer contacts
            contacts = crm_data.get('contacts', [])
            for contact in contacts:
                cursor.execute('''
                    INSERT OR REPLACE INTO contacts 
                    (id, prenom, nom_famille, email, telephone, company_id, role_poste, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    contact['id'],
                    contact['prenom'],
                    contact['nom_famille'],
                    contact.get('email'),
                    contact.get('telephone'),
                    contact.get('entreprise_id'),  # Mapping vers company_id
                    contact.get('role'),
                    contact.get('notes'),
                    contact.get('date_creation'),
                    contact.get('date_modification')
                ))
                migrated_counts['contacts'] += 1
            
            # 3. Migrer interactions
            interactions = crm_data.get('interactions', [])
            for interaction in interactions:
                cursor.execute('''
                    INSERT OR REPLACE INTO interactions 
                    (id, contact_id, company_id, type_interaction, date_interaction, 
                     resume, details, resultat, suivi_prevu)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    interaction['id'],
                    interaction.get('contact_id'),
                    interaction.get('entreprise_id'),  # Mapping vers company_id
                    interaction.get('type'),
                    interaction.get('date_interaction'),
                    interaction.get('resume'),
                    interaction.get('details'),
                    interaction.get('resultat'),
                    interaction.get('suivi_prevu')
                ))
                migrated_counts['interactions'] += 1
            
            conn.commit()
        
        logger.info(f"✅ CRM migré: {migrated_counts}")
        return {
            'success': True,
            'migrated_counts': migrated_counts
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur migration CRM: {e}")
        return {'success': False, 'error': str(e)}

def migrate_employees_data(db: ERPDatabase) -> Dict[str, Any]:
    """Migre les 21 employés DG Inc. avec leurs compétences"""
    logger.info("👥 Migration des employés DG Inc...")
    
    if not os.path.exists('employees_data.json'):
        logger.warning("⚠️ Fichier employees_data.json non trouvé")
        return {'success': False, 'error': 'employees_data.json non trouvé'}
    
    try:
        with open('employees_data.json', 'r', encoding='utf-8') as f:
            emp_data = json.load(f)
        
        employes = emp_data.get('employes', [])
        migrated_counts = {
            'employees': 0,
            'competences': 0
        }
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            for employe in employes:
                # Insérer employé
                cursor.execute('''
                    INSERT OR REPLACE INTO employees 
                    (id, prenom, nom, email, telephone, poste, departement, statut, 
                     type_contrat, date_embauche, salaire, manager_id, charge_travail, 
                     notes, photo_url, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    employe['id'],
                    employe['prenom'],
                    employe['nom'],
                    employe.get('email'),
                    employe.get('telephone'),
                    employe.get('poste'),
                    employe.get('departement'),
                    employe.get('statut', 'ACTIF'),
                    employe.get('type_contrat', 'CDI'),
                    employe.get('date_embauche'),
                    employe.get('salaire'),
                    employe.get('manager_id'),
                    employe.get('charge_travail', 80),
                    employe.get('notes'),
                    employe.get('photo_url'),
                    employe.get('date_creation'),
                    employe.get('date_modification')
                ))
                migrated_counts['employees'] += 1
                
                # Insérer compétences
                competences = employe.get('competences', [])
                for competence in competences:
                    cursor.execute('''
                        INSERT INTO employee_competences 
                        (employee_id, nom_competence, niveau, certifie)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        employe['id'],
                        competence.get('nom'),
                        competence.get('niveau'),
                        competence.get('certifie', False)
                    ))
                    migrated_counts['competences'] += 1
            
            conn.commit()
        
        logger.info(f"✅ Employés migrés: {migrated_counts}")
        return {
            'success': True,
            'migrated_counts': migrated_counts
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur migration employés: {e}")
        return {'success': False, 'error': str(e)}

def migrate_projects_data(db: ERPDatabase) -> Dict[str, Any]:
    """Migre les projets avec leurs opérations et matériaux"""
    logger.info("🚀 Migration des projets...")
    
    if not os.path.exists('projets_data.json'):
        logger.warning("⚠️ Fichier projets_data.json non trouvé")
        return {'success': False, 'error': 'projets_data.json non trouvé'}
    
    try:
        with open('projets_data.json', 'r', encoding='utf-8') as f:
            proj_data = json.load(f)
        
        projets = proj_data.get('projets', [])
        migrated_counts = {
            'projects': 0,
            'operations': 0,
            'materials': 0,
            'assignments': 0
        }
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            for projet in projets:
                # Insérer projet
                cursor.execute('''
                    INSERT OR REPLACE INTO projects 
                    (id, nom_projet, client_company_id, client_nom_cache, client_legacy,
                     statut, priorite, tache, date_soumis, date_prevu, bd_ft_estime, 
                     prix_estime, description, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    projet['id'],
                    projet['nom_projet'],
                    projet.get('client_entreprise_id'),
                    projet.get('client_nom_cache'),
                    projet.get('client'),  # Legacy field
                    projet.get('statut', 'À FAIRE'),
                    projet.get('priorite', 'MOYEN'),
                    projet.get('tache'),
                    projet.get('date_soumis'),
                    projet.get('date_prevu'),
                    float(projet.get('bd_ft_estime', 0)) if projet.get('bd_ft_estime') else None,
                    float(str(projet.get('prix_estime', 0)).replace('$', '').replace(',', '')) if projet.get('prix_estime') else None,
                    projet.get('description'),
                    datetime.now().isoformat()
                ))
                migrated_counts['projects'] += 1
                
                # Insérer opérations
                operations = projet.get('operations', [])
                for operation in operations:
                    # Trouver work_center_id basé sur le nom du poste
                    work_center_id = None
                    poste_travail = operation.get('poste_travail')
                    if poste_travail:
                        cursor.execute('SELECT id FROM work_centers WHERE nom = ?', (poste_travail,))
                        result = cursor.fetchone()
                        if result:
                            work_center_id = result['id']
                    
                    cursor.execute('''
                        INSERT INTO operations 
                        (project_id, work_center_id, sequence_number, description, 
                         temps_estime, ressource, statut, poste_travail, operation_legacy_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        projet['id'],
                        work_center_id,
                        int(operation.get('sequence', 0)) if operation.get('sequence', '').isdigit() else None,
                        operation.get('description'),
                        operation.get('temps_estime'),
                        operation.get('ressource'),
                        operation.get('statut', 'À FAIRE'),
                        poste_travail,
                        operation.get('id')
                    ))
                    migrated_counts['operations'] += 1
                
                # Insérer matériaux
                materiaux = projet.get('materiaux', [])
                for materiau in materiaux:
                    cursor.execute('''
                        INSERT INTO materials 
                        (project_id, material_legacy_id, code_materiau, designation, 
                         quantite, unite, prix_unitaire, fournisseur)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        projet['id'],
                        materiau.get('id'),
                        materiau.get('code'),
                        materiau.get('designation'),
                        materiau.get('quantite'),
                        materiau.get('unite'),
                        materiau.get('prix_unitaire'),
                        materiau.get('fournisseur')
                    ))
                    migrated_counts['materials'] += 1
                
                # Insérer assignations employés
                employes_assignes = projet.get('employes_assignes', [])
                for emp_id in employes_assignes:
                    cursor.execute('''
                        INSERT OR IGNORE INTO project_assignments 
                        (project_id, employee_id, role_projet)
                        VALUES (?, ?, ?)
                    ''', (
                        projet['id'],
                        emp_id,
                        'Membre équipe'
                    ))
                    migrated_counts['assignments'] += 1
            
            conn.commit()
        
        logger.info(f"✅ Projets migrés: {migrated_counts}")
        return {
            'success': True,
            'migrated_counts': migrated_counts
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur migration projets: {e}")
        return {'success': False, 'error': str(e)}

def migrate_inventory_data(db: ERPDatabase) -> Dict[str, Any]:
    """Migre l'inventaire avec conversion mesures impériales"""
    logger.info("📦 Migration de l'inventaire...")
    
    if not os.path.exists('inventaire_v2.json'):
        logger.warning("⚠️ Fichier inventaire_v2.json non trouvé")
        return {'success': False, 'error': 'inventaire_v2.json non trouvé'}
    
    try:
        with open('inventaire_v2.json', 'r', encoding='utf-8') as f:
            inv_data = json.load(f)
        
        migrated_count = 0
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            for item_id, item_data in inv_data.items():
                # Conversion mesures impériales
                quantite_imperial = item_data.get('quantite', '0\' 0"')
                quantite_metric = convertir_imperial_vers_metrique(quantite_imperial)
                
                limite_imperial = item_data.get('limite_minimale', '0\' 0"')
                limite_metric = convertir_imperial_vers_metrique(limite_imperial)
                
                reservee_imperial = item_data.get('quantite_reservee', '0\' 0"')
                reservee_metric = convertir_imperial_vers_metrique(reservee_imperial)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO inventory_items 
                    (id, nom, type_produit, quantite_imperial, quantite_metric,
                     limite_minimale_imperial, limite_minimale_metric,
                     quantite_reservee_imperial, quantite_reservee_metric,
                     statut, description, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    int(item_id),
                    item_data.get('nom'),
                    item_data.get('type'),
                    quantite_imperial,
                    quantite_metric,
                    limite_imperial,
                    limite_metric,
                    reservee_imperial,
                    reservee_metric,
                    item_data.get('statut'),
                    item_data.get('description'),
                    item_data.get('note'),
                    item_data.get('date_creation'),
                    datetime.now().isoformat()
                ))
                
                # Migrer historique si disponible
                historique = item_data.get('historique', [])
                for hist_entry in historique:
                    cursor.execute('''
                        INSERT INTO inventory_history 
                        (inventory_item_id, action, quantite_avant, quantite_apres, notes, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        int(item_id),
                        hist_entry.get('action'),
                        hist_entry.get('quantite_avant', ''),
                        hist_entry.get('quantite', ''),
                        hist_entry.get('note'),
                        hist_entry.get('date')
                    ))
                
                migrated_count += 1
            
            conn.commit()
        
        logger.info(f"✅ {migrated_count} articles d'inventaire migrés")
        return {
            'success': True,
            'migrated_count': migrated_count
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur migration inventaire: {e}")
        return {'success': False, 'error': str(e)}

def migrate_timetracker_data(db: ERPDatabase) -> Dict[str, Any]:
    """Migre les données TimeTracker existantes si présentes"""
    logger.info("⏱️ Migration TimeTracker...")
    
    if not os.path.exists('timetracker.db'):
        logger.info("ℹ️ Pas de base TimeTracker existante à migrer")
        return {'success': True, 'migrated_count': 0, 'note': 'Aucune donnée TimeTracker existante'}
    
    try:
        # Connexion à l'ancienne base TimeTracker
        old_conn = sqlite3.connect('timetracker.db')
        old_conn.row_factory = sqlite3.Row
        old_cursor = old_conn.cursor()
        
        migrated_count = 0
        
        with db.get_connection() as new_conn:
            new_cursor = new_conn.cursor()
            
            # Migrer les entrées de temps
            try:
                old_cursor.execute('SELECT * FROM time_entries')
                time_entries = old_cursor.fetchall()
                
                for entry in time_entries:
                    # Mapper vers les nouveaux IDs d'employés et projets
                    employee_id = entry.get('employee_id')
                    project_id = entry.get('project_id')
                    
                    new_cursor.execute('''
                        INSERT OR IGNORE INTO time_entries 
                        (employee_id, project_id, punch_in, punch_out, total_hours, 
                         hourly_rate, total_cost, notes, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        employee_id,
                        project_id,
                        entry.get('punch_in'),
                        entry.get('punch_out'),
                        entry.get('total_hours'),
                        entry.get('hourly_rate'),
                        entry.get('total_cost'),
                        entry.get('notes'),
                        entry.get('created_at')
                    ))
                    migrated_count += 1
                
            except sqlite3.OperationalError as e:
                logger.warning(f"Table time_entries non trouvée dans TimeTracker: {e}")
            
            new_conn.commit()
        
        old_conn.close()
        
        logger.info(f"✅ {migrated_count} entrées TimeTracker migrées")
        return {
            'success': True,
            'migrated_count': migrated_count
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur migration TimeTracker: {e}")
        return {'success': False, 'error': str(e)}

# Fonction utilitaire pour validation post-migration
def validate_migration_results(db: ERPDatabase) -> Dict[str, Any]:
    """Valide les résultats de migration"""
    logger.info("🔍 Validation des résultats de migration...")
    
    results = {
        'validation_time': datetime.now().isoformat(),
        'table_counts': db.get_migration_status(),
        'integrity_checks': db.validate_integrity(),
        'schema_info': db.get_schema_info(),
        'warnings': [],
        'recommendations': []
    }
    
    # Vérifications spécifiques
    counts = results['table_counts']
    
    # Vérifier que nous avons les données attendues
    if counts.get('work_centers', 0) != 61:
        results['warnings'].append(f"Postes de travail: attendu 61, trouvé {counts.get('work_centers', 0)}")
    
    if counts.get('employees', 0) < 20:
        results['warnings'].append(f"Employés: moins de 20 trouvés ({counts.get('employees', 0)})")
    
    if counts.get('projects', 0) == 0:
        results['warnings'].append("Aucun projet migré")
    
    # Recommandations
    if all(results['integrity_checks'].values()):
        results['recommendations'].append("✅ Intégrité des données validée")
    else:
        results['recommendations'].append("⚠️ Vérifier l'intégrité des relations")
    
    return results
