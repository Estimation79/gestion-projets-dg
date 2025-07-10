import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Any

# --- Constantes partagées ---
STATUTS_DEVIS = ["BROUILLON", "VALIDÉ", "ENVOYÉ", "APPROUVÉ", "TERMINÉ", "ANNULÉ"]
UNITES_VENTE = ["kg", "tonne", "m", "m²", "m³", "pièce", "lot", "heure"]

class GestionnaireDevis:
    """
    Gestionnaire dédié aux devis, extrait de crm.py pour une meilleure modularité.
    Utilise l'infrastructure 'formulaires' de la base de données unifiée.
    Interagit avec les modules CRM (pour les clients/produits) et Projets (pour la transformation).
    """

    def __init__(self, db, crm_manager, project_manager, product_manager):
        """
        Initialise le gestionnaire de devis.

        Args:
            db: Instance de ERPDatabase.
            crm_manager: Instance de GestionnaireCRM.
            project_manager: Instance de GestionnaireProjetSQL.
            product_manager: Instance de GestionnaireProduits.
        """
        self.db = db
        self.crm_manager = crm_manager
        self.project_manager = project_manager
        self.product_manager = product_manager  # NOUVELLE DÉPENDANCE
        self._init_devis_support()

    def _init_devis_support(self):
        """Initialise le support des devis en vérifiant la contrainte CHECK de la DB."""
        self._devis_compatibility_mode = False
        self._devis_type_db = 'DEVIS'
        
        try:
            # Tente d'insérer une ligne test pour vérifier la contrainte
            test_query = "INSERT INTO formulaires (type_formulaire, numero_document, statut) VALUES ('DEVIS', 'TEST-DEVIS-COMPATIBILITY-UNIQUE', 'BROUILLON')"
            try:
                test_id = self.db.execute_insert(test_query)
                if test_id:
                    self.db.execute_update("DELETE FROM formulaires WHERE id = ?", (test_id,))
                st.success("✅ Support DEVIS natif activé dans le système de formulaires")
            except Exception as e:
                # Si la contrainte échoue, on passe en mode compatibilité
                if "CHECK constraint failed" in str(e):
                    self._devis_compatibility_mode = True
                    self._devis_type_db = 'ESTIMATION'
                    st.warning("⚠️ Mode compatibilité DEVIS activé (via ESTIMATION).")
                else:
                    st.error(f"⚠️ Support devis limité: {e}")
        except Exception as e:
            # En cas d'autre erreur, on active le mode compatibilité par sécurité
            self._devis_compatibility_mode = True
            self._devis_type_db = 'ESTIMATION'
            st.error(f"Erreur initialisation support devis: {e}")

    # --- MÉTHODES MÉTIER (Déplacées de GestionnaireCRM) ---
    
    def generer_numero_devis(self) -> str:
        """Génère un numéro de devis/estimation automatique."""
        try:
            annee = datetime.now().year
            prefix = "EST" if self._devis_compatibility_mode else "DEVIS"
            query = "SELECT numero_document FROM formulaires WHERE numero_document LIKE ? ORDER BY id DESC LIMIT 1"
            pattern = f"{prefix}-{annee}-%"
            result = self.db.execute_query(query, (pattern,))
            
            sequence = 1
            if result:
                last_num = result[0]['numero_document']
                try:
                    sequence = int(last_num.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    sequence = 1
            
            return f"{prefix}-{annee}-{sequence:03d}"
        except Exception as e:
            st.error(f"Erreur génération numéro devis: {e}")
            prefix_fallback = "EST" if self._devis_compatibility_mode else "DEVIS"
            return f"{prefix_fallback}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def create_devis(self, devis_data: Dict[str, Any]) -> Optional[int]:
        """Crée un nouveau devis dans la table formulaires."""
        try:
            numero_devis = self.generer_numero_devis()
            type_formulaire_db = self._devis_type_db
            mode_info = " (mode compatibilité)" if self._devis_compatibility_mode else ""
            
            metadonnees = {
                'type_reel': 'DEVIS', 
                'type_devis': 'STANDARD',
                'tva_applicable': True, 
                'taux_tva': 14.975, 
                'devise': 'CAD', 
                'validite_jours': 30, 
                'created_by_module': 'DEVIS',
                'compatibility_mode': self._devis_compatibility_mode
            }
            
            query = '''
                INSERT INTO formulaires 
                (type_formulaire, numero_document, project_id, company_id, employee_id,
                 statut, priorite, date_echeance, notes, metadonnees_json)
                VALUES (?, ?, ?, ?, ?, 'BROUILLON', 'NORMAL', ?, ?, ?)
            '''
            
            devis_id = self.db.execute_insert(query, (
                type_formulaire_db, numero_devis, devis_data.get('project_id'),
                devis_data['client_company_id'], devis_data['employee_id'],
                devis_data['date_echeance'], devis_data.get('notes', ''), json.dumps(metadonnees)
            ))
            
            if devis_id:
                if devis_data.get('lignes'):
                    for i, ligne in enumerate(devis_data['lignes'], 1):
                        self.ajouter_ligne_devis(devis_id, i, ligne)
                self.enregistrer_validation(devis_id, devis_data['employee_id'], 'CREATION', f"Devis créé: {numero_devis}{mode_info}")
                return devis_id
            return None
        except Exception as e:
            st.error(f"Erreur création devis: {e}")
            return None

    def modifier_devis(self, devis_id: int, devis_data: Dict[str, Any]) -> bool:
        """Modifie un devis existant."""
        try:
            devis_existant = self.get_devis_complet(devis_id)
            if not devis_existant:
                st.error(f"Devis #{devis_id} non trouvé.")
                return False
            
            statuts_non_modifiables = ['APPROUVÉ', 'TERMINÉ', 'ANNULÉ']
            if devis_existant.get('statut') in statuts_non_modifiables:
                st.error(f"Impossible de modifier un devis au statut '{devis_existant.get('statut')}'")
                return False
            
            query = '''
                UPDATE formulaires 
                SET company_id = ?, employee_id = ?, project_id = ?, 
                    date_echeance = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            '''
            
            rows_affected = self.db.execute_update(query, (
                devis_data['client_company_id'], devis_data['employee_id'], devis_data.get('project_id'),
                devis_data['date_echeance'], devis_data.get('notes', ''), devis_id
            ))
            
            if rows_affected > 0:
                # Supprimer les anciennes lignes et ajouter les nouvelles
                self.db.execute_update("DELETE FROM formulaire_lignes WHERE formulaire_id = ?", (devis_id,))
                if devis_data.get('lignes'):
                    for i, ligne in enumerate(devis_data['lignes'], 1):
                        self.ajouter_ligne_devis(devis_id, i, ligne)
                self.enregistrer_validation(devis_id, devis_data['employee_id'], 'MODIFICATION', "Devis modifié via interface")
                return True
            return False
        except Exception as e:
            st.error(f"Erreur modification devis: {e}")
            return False
    
    def supprimer_devis(self, devis_id: int, employee_id: int, motif: str = "") -> bool:
        """Supprime un devis et ses données associées."""
        try:
            devis_existant = self.get_devis_complet(devis_id)
            if not devis_existant:
                st.error(f"Devis #{devis_id} non trouvé.")
                return False
            
            statuts_non_supprimables = ['APPROUVÉ', 'TERMINÉ']
            if devis_existant.get('statut') in statuts_non_supprimables:
                st.error(f"Impossible de supprimer un devis au statut '{devis_existant.get('statut')}'")
                st.info("💡 Conseil: Vous pouvez annuler le devis au lieu de le supprimer.")
                return False
            
            # Enregistrer l'action avant suppression
            self.enregistrer_validation(devis_id, employee_id, 'SUPPRESSION', f"Suppression. Motif: {motif or 'Non spécifié'}")
            
            # Supprimer en cascade
            self.db.execute_update("DELETE FROM formulaire_validations WHERE formulaire_id = ?", (devis_id,))
            self.db.execute_update("DELETE FROM formulaire_lignes WHERE formulaire_id = ?", (devis_id,))
            rows_affected = self.db.execute_update("DELETE FROM formulaires WHERE id = ?", (devis_id,))
            
            if rows_affected > 0:
                st.success(f"✅ Devis #{devis_id} ({devis_existant.get('numero_document')}) supprimé avec succès!")
                return True
            else:
                st.error("Aucune ligne affectée lors de la suppression.")
                return False
        except Exception as e:
            st.error(f"Erreur suppression devis: {e}")
            return False

    def ajouter_ligne_devis(self, devis_id: int, sequence: int, ligne_data: Dict[str, Any]) -> Optional[int]:
        """Ajoute une ligne à un devis."""
        try:
            query = '''
                INSERT INTO formulaire_lignes
                (formulaire_id, sequence_ligne, description, code_article,
                 quantite, unite, prix_unitaire, notes_ligne)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            ligne_id = self.db.execute_insert(query, (
                devis_id, sequence, ligne_data['description'], ligne_data.get('code_article', ''),
                ligne_data['quantite'], ligne_data.get('unite', 'UN'), ligne_data['prix_unitaire'], ligne_data.get('notes', '')
            ))
            
            return ligne_id
        except Exception as e:
            st.error(f"Erreur ajout ligne devis: {e}")
            return None

    def get_devis_complet(self, devis_id: int) -> Dict[str, Any]:
        """Récupère un devis avec tous ses détails."""
        try:
            query = '''
                SELECT f.*, 
                       c.nom as client_nom, 
                       c.adresse, c.ville, c.province, c.code_postal, c.pays,
                       co.prenom || ' ' || co.nom_famille as contact_nom, 
                       co.email as contact_email, co.telephone as contact_telephone,
                       e.prenom || ' ' || e.nom as responsable_nom,
                       p.nom_projet
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN contacts co ON c.contact_principal_id = co.id
                LEFT JOIN employees e ON f.employee_id = e.id
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE f.id = ? AND (f.type_formulaire = 'DEVIS' OR (f.type_formulaire = 'ESTIMATION' AND f.metadonnees_json LIKE '%"type_reel": "DEVIS"%'))
            '''
            
            result = self.db.execute_query(query, (devis_id,))
            if not result:
                return {}
            
            devis = dict(result[0])
            
            # Ajouter l'adresse complète formatée
            if devis.get('client_nom'):
                devis['client_adresse_complete'] = self.crm_manager.format_adresse_complete(devis)
            
            # Récupérer les lignes
            query_lignes = 'SELECT * FROM formulaire_lignes WHERE formulaire_id = ? ORDER BY sequence_ligne'
            lignes = self.db.execute_query(query_lignes, (devis_id,))
            devis['lignes'] = [dict(ligne) for ligne in lignes]
            
            # Calculer les totaux
            devis['totaux'] = self.calculer_totaux_devis(devis_id)
            
            # Récupérer l'historique
            query_historique = '''
                SELECT fv.*, e.prenom || ' ' || e.nom as employee_nom
                FROM formulaire_validations fv
                LEFT JOIN employees e ON fv.employee_id = e.id
                WHERE fv.formulaire_id = ?
                ORDER BY fv.date_validation DESC
            '''
            historique = self.db.execute_query(query_historique, (devis_id,))
            devis['historique'] = [dict(h) for h in historique]
            
            # Parser les métadonnées
            try:
                devis['metadonnees'] = json.loads(devis.get('metadonnees_json', '{}'))
            except:
                devis['metadonnees'] = {}
            
            return devis
        except Exception as e:
            st.error(f"Erreur récupération devis complet: {e}")
            return {}

    def calculer_totaux_devis(self, devis_id: int) -> Dict[str, float]:
        """Calcule les totaux d'un devis (HT, TVA, TTC)."""
        try:
            query = 'SELECT quantite, prix_unitaire FROM formulaire_lignes WHERE formulaire_id = ?'
            lignes = self.db.execute_query(query, (devis_id,))
            
            total_ht = sum((ligne['quantite'] * ligne['prix_unitaire']) for ligne in lignes)
            
            # Récupérer le taux TVA des métadonnées
            devis_info = self.db.execute_query("SELECT metadonnees_json FROM formulaires WHERE id = ?", (devis_id,))
            
            taux_tva = 14.975  # Défaut QC
            if devis_info:
                try:
                    metadonnees = json.loads(devis_info[0]['metadonnees_json'] or '{}')
                    taux_tva = metadonnees.get('taux_tva', 14.975)
                except:
                    pass
            
            tva = total_ht * (taux_tva / 100)
            total_ttc = total_ht + tva
            
            return {
                'total_ht': round(total_ht, 2),
                'taux_tva': taux_tva,
                'montant_tva': round(tva, 2),
                'total_ttc': round(total_ttc, 2)
            }
        except Exception as e:
            st.error(f"Erreur calcul totaux devis: {e}")
            return {'total_ht': 0, 'taux_tva': 0, 'montant_tva': 0, 'total_ttc': 0}

    def changer_statut_devis(self, devis_id: int, nouveau_statut: str, employee_id: int, commentaires: str = "") -> bool:
        """Change le statut d'un devis avec traçabilité."""
        try:
            result = self.db.execute_query("SELECT statut FROM formulaires WHERE id = ?", (devis_id,))
            if not result:
                st.error(f"Devis #{devis_id} non trouvé.")
                return False
            
            ancien_statut = result[0]['statut']
            
            # Mettre à jour le statut
            affected = self.db.execute_update(
                "UPDATE formulaires SET statut = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (nouveau_statut, devis_id)
            )
            
            if affected > 0:
                # Enregistrer le changement
                self.enregistrer_validation(
                    devis_id, employee_id, 'CHANGEMENT_STATUT',
                    f"Statut changé de {ancien_statut} vers {nouveau_statut}. {commentaires}"
                )
                
                # Actions spéciales selon le nouveau statut
                if nouveau_statut == 'APPROUVÉ':
                    self.on_devis_accepte(devis_id)
                elif nouveau_statut == 'EXPIRÉ':
                    self.on_devis_expire(devis_id)
                
                return True
            return False
        except Exception as e:
            st.error(f"Erreur changement statut devis: {e}")
            return False

    def on_devis_accepte(self, devis_id: int):
        """Actions à effectuer quand un devis est accepté. TRANSFORME LE DEVIS EN PROJET."""
        if not self.project_manager:
            st.error("❌ Le gestionnaire de projets n'est pas disponible. Transformation impossible.")
            return

        try:
            devis = self.get_devis_complet(devis_id)
            
            if not devis:
                st.error(f"❌ Devis #{devis_id} non trouvé. Transformation annulée.")
                return
            
            if devis.get('project_id'):
                st.warning(f"ℹ️ Un projet (#{devis['project_id']}) est déjà lié à ce devis. Aucune action effectuée.")
                return

            # Préparation des données pour le nouveau projet
            project_data = {
                'nom_projet': f"Projet - Devis {devis.get('numero_document', devis_id)}",
                'client_company_id': devis.get('company_id'),
                'client_nom_cache': devis.get('client_nom'),
                'statut': 'À FAIRE',
                'priorite': devis.get('priorite', 'MOYEN'),
                'description': f"Projet créé automatiquement suite à l'acceptation du devis {devis.get('numero_document')}.\n\nNotes du devis:\n{devis.get('notes', '')}",
                'prix_estime': devis.get('totaux', {}).get('total_ht', 0.0),
                'date_soumis': datetime.now().strftime('%Y-%m-%d'),
                'date_prevu': (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d'),
                'employes_assignes': [devis.get('employee_id')] if devis.get('employee_id') else [],
                'tache': 'PROJET_CLIENT',
                'bd_ft_estime': 0.0,
                'client_legacy': '',
                # Ces listes sont pour la compatibilité, les données seront ajoutées après
                'operations': [],
                'materiaux': []
            }
            
            # Création du projet via le gestionnaire de projets
            st.info(f"⏳ Transformation du devis #{devis_id} en projet...")
            project_id = self.project_manager.ajouter_projet(project_data)
            
            if project_id:
                # ======================================================================
                # NOUVEAU : Boucle pour transférer les lignes du devis en matériaux
                # ======================================================================
                lignes_devis = devis.get('lignes', [])
                materiaux_ajoutes = 0
                if lignes_devis:
                    for ligne in lignes_devis:
                        material_data = {
                            'code': ligne.get('code_article'),
                            'designation': ligne.get('description'),
                            'quantite': ligne.get('quantite'),
                            'unite': ligne.get('unite'),
                            'prix_unitaire': ligne.get('prix_unitaire'),
                            'fournisseur': None # Peut être enrichi plus tard
                        }
                        # Utilise la nouvelle méthode de erp_database.py
                        if self.db.add_material_to_project(project_id, material_data):
                            materiaux_ajoutes += 1
                
                st.success(f"✅ Devis transformé avec succès en Projet #{project_id} avec {materiaux_ajoutes} matériau(x) ajouté(s) !")
                # ======================================================================
                
                # Lier le nouveau projet au devis
                self.db.execute_update("UPDATE formulaires SET project_id = ? WHERE id = ?", (project_id, devis_id))
                
                # Enregistrer l'action dans l'historique du devis
                self.enregistrer_validation(
                    devis_id, devis.get('employee_id', 1), 'TERMINAISON',
                    f"Devis transformé en Projet #{project_id}."
                )
                st.balloons()
            else:
                st.error("❌ Échec de la création du projet. La transformation a été annulée.")

        except Exception as e:
            st.error(f"Erreur lors de la transformation du devis en projet: {e}")

    def on_devis_expire(self, devis_id: int):
        """Actions à effectuer quand un devis expire."""
        try:
            st.info(f"Le devis #{devis_id} est maintenant marqué comme expiré.")
        except Exception as e:
            st.error(f"Erreur expiration devis: {e}")

    def enregistrer_validation(self, devis_id: int, employee_id: int, type_validation: str, commentaires: str):
        """Enregistre une validation dans l'historique du devis."""
        try:
            query = '''
                INSERT INTO formulaire_validations
                (formulaire_id, employee_id, type_validation, commentaires)
                VALUES (?, ?, ?, ?)
            '''
            self.db.execute_insert(query, (devis_id, employee_id, type_validation, commentaires))
        except Exception as e:
            st.error(f"Erreur enregistrement validation devis: {e}")

    def get_all_devis(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Récupère tous les devis avec filtres optionnels."""
        try:
            query = f'''
                SELECT f.id, f.numero_document, f.statut, f.priorite, f.date_creation, 
                       f.date_echeance,
                       c.nom as client_nom,
                       e.prenom || ' ' || e.nom as responsable_nom,
                       p.nom_projet
                FROM formulaires f
                LEFT JOIN companies c ON f.company_id = c.id
                LEFT JOIN employees e ON f.employee_id = e.id
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE (f.type_formulaire = 'DEVIS' OR (f.type_formulaire = 'ESTIMATION' AND f.metadonnees_json LIKE '%"type_reel": "DEVIS"%'))
            '''
            
            params = []
            
            if filters:
                if filters.get('statut') and filters['statut'] != 'Tous':
                    query += " AND f.statut = ?"
                    params.append(filters['statut'])
                
                if filters.get('client_id'):
                    query += " AND f.company_id = ?"
                    params.append(filters['client_id'])
                
                if filters.get('responsable_id'):
                    query += " AND f.employee_id = ?"
                    params.append(filters['responsable_id'])
                
                if filters.get('date_debut'):
                    query += " AND DATE(f.date_creation) >= ?"
                    params.append(filters['date_debut'])
                
                if filters.get('date_fin'):
                    query += " AND DATE(f.date_creation) <= ?"
                    params.append(filters['date_fin'])
            
            query += " ORDER BY f.date_creation DESC"
            
            rows = self.db.execute_query(query, tuple(params) if params else None)
            
            # Enrichir avec les totaux
            devis_list = []
            for row in rows:
                devis = dict(row)
                devis['totaux'] = self.calculer_totaux_devis(devis['id'])
                devis_list.append(devis)
            
            return devis_list
        except Exception as e:
            st.error(f"Erreur récupération liste devis: {e}")
            return []

    def get_devis_statistics(self) -> Dict[str, Any]:
        """Statistiques des devis."""
        try:
            stats = {
                'total_devis': 0,
                'par_statut': {},
                'montant_total': 0.0,
                'taux_acceptation': 0.0,
                'devis_expires': 0,
                'en_attente': 0
            }
            
            all_devis = self.get_all_devis()
            
            stats['total_devis'] = len(all_devis)
            
            for devis in all_devis:
                statut = devis['statut']
                if statut not in stats['par_statut']:
                    stats['par_statut'][statut] = {'count': 0, 'montant': 0.0}
                
                stats['par_statut'][statut]['count'] += 1
                stats['par_statut'][statut]['montant'] += devis.get('totaux', {}).get('total_ht', 0.0)
                stats['montant_total'] += devis.get('totaux', {}).get('total_ht', 0.0)
            
            # Taux d'acceptation
            accepted_count = stats['par_statut'].get('ACCEPTÉ', {}).get('count', 0)
            refused_count = stats['par_statut'].get('REFUSÉ', {}).get('count', 0)
            expired_count = stats['par_statut'].get('EXPIRÉ', {}).get('count', 0)
            
            total_decides = accepted_count + refused_count + expired_count
            
            if total_decides > 0:
                stats['taux_acceptation'] = (accepted_count / total_decides) * 100
            
            # Devis expirés
            query_expires = '''
                SELECT COUNT(*) as count FROM formulaires 
                WHERE (type_formulaire = 'DEVIS' OR (type_formulaire = 'ESTIMATION' AND metadonnees_json LIKE '%"type_reel": "DEVIS"%'))
                AND date_echeance < DATE('now') 
                AND statut NOT IN ('ACCEPTÉ', 'REFUSÉ', 'EXPIRÉ', 'ANNULÉ')
            '''
            result = self.db.execute_query(query_expires)
            stats['devis_expires'] = result[0]['count'] if result else 0
            
            # En attente
            stats['en_attente'] = stats['par_statut'].get('ENVOYÉ', {}).get('count', 0) + \
                                 stats['par_statut'].get('BROUILLON', {}).get('count', 0)
            
            return stats
        except Exception as e:
            st.error(f"Erreur statistiques devis: {e}")
            return {}

    def dupliquer_devis(self, devis_id: int, employee_id: int) -> Optional[int]:
        """Duplique un devis existant."""
        try:
            devis_original = self.get_devis_complet(devis_id)
            if not devis_original:
                st.error("Devis original non trouvé pour duplication.")
                return None
            
            # Créer nouveau devis basé sur l'original
            nouveau_devis_data = {
                'client_company_id': devis_original['company_id'],
                'client_contact_id': devis_original.get('client_contact_id'),
                'project_id': devis_original.get('project_id'),
                'employee_id': employee_id,
                'date_echeance': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                'notes': f"Copie de {devis_original['numero_document']} - {devis_original.get('notes', '')}",
                'lignes': devis_original['lignes']
            }
            
            nouveau_id = self.create_devis(nouveau_devis_data)
            
            if nouveau_id:
                self.enregistrer_validation(
                    nouveau_id, employee_id, 'CREATION',
                    f"Devis dupliqué depuis #{devis_id} ({devis_original['numero_document']})"
                )
            
            return nouveau_id
        except Exception as e:
            st.error(f"Erreur duplication devis: {e}")
            return None

    # --- EXPORT HTML ---
    
    def export_devis_html(self, devis_id: int) -> Optional[str]:
        """Exporte un devis au format HTML professionnel pour les clients."""
        try:
            devis_data = self.get_devis_complet(devis_id)
            if not devis_data:
                st.error(f"Devis #{devis_id} non trouvé pour export")
                return None
            
            html_content = self.generate_devis_html_template(devis_data)
            return html_content
        except Exception as e:
            st.error(f"Erreur export HTML devis: {e}")
            return None
    
    def generate_devis_html_template(self, devis_data: Dict[str, Any]) -> str:
        """Génère le template HTML pour un devis avec design moderne professionnel."""
        try:
            # Formatage des dates
            date_creation = devis_data.get('date_creation', '')
            if date_creation:
                try:
                    date_creation_formatted = datetime.fromisoformat(date_creation).strftime('%d/%m/%Y')
                except:
                    date_creation_formatted = date_creation[:10] if len(date_creation) >= 10 else date_creation
            else:
                date_creation_formatted = 'N/A'
            
            date_echeance = devis_data.get('date_echeance', '')
            try:
                date_echeance_formatted = datetime.fromisoformat(date_echeance).strftime('%d/%m/%Y') if date_echeance else 'N/A'
            except:
                date_echeance_formatted = date_echeance
            
            # Récupération des totaux
            totaux = devis_data.get('totaux', {})
            total_ht = totaux.get('total_ht', 0)
            taux_tva = totaux.get('taux_tva', 14.975)
            montant_tva = totaux.get('montant_tva', 0)
            total_ttc = totaux.get('total_ttc', 0)
            
            # Formatage du statut pour les badges
            statut = devis_data.get('statut', 'BROUILLON')
            statut_class = {
                'BROUILLON': 'badge-pending',
                'VALIDÉ': 'badge-in-progress',
                'ENVOYÉ': 'badge-in-progress',
                'APPROUVÉ': 'badge-completed',
                'TERMINÉ': 'badge-completed',
                'ANNULÉ': 'badge-on-hold',
                'EXPIRÉ': 'badge-on-hold'
            }.get(statut, 'badge-pending')
            
            priorite = devis_data.get('priorite', 'NORMAL')
            priorite_class = {
                'FAIBLE': 'badge-pending',
                'NORMAL': 'badge-in-progress',
                'ÉLEVÉE': 'badge-on-hold',
                'URGENT': 'badge-on-hold'
            }.get(priorite, 'badge-in-progress')
            
            # Génération des lignes du tableau
            lignes_html = ""
            nb_lignes = 0
            if devis_data.get('lignes'):
                for ligne in devis_data['lignes']:
                    nb_lignes += 1
                    montant_ligne = ligne.get('quantite', 0) * ligne.get('prix_unitaire', 0)
                    code_article = ligne.get('code_article', '')
                    code_display = f"<br><small>Code: {code_article}</small>" if code_article else ""
                    
                    lignes_html += f"""
                    <tr>
                        <td><strong>{ligne.get('description', '')}</strong>{code_display}</td>
                        <td style="text-align: center;">{ligne.get('quantite', 0):,.2f}</td>
                        <td style="text-align: center;">{ligne.get('unite', '')}</td>
                        <td style="text-align: right;">{ligne.get('prix_unitaire', 0):,.2f} $</td>
                        <td style="text-align: right;"><strong>{montant_ligne:,.2f} $</strong></td>
                    </tr>
                    """
            else:
                lignes_html = """
                <tr>
                    <td colspan="5" style="text-align: center; color: #6B7280;">Aucune ligne dans ce devis</td>
                </tr>
                """
            
            # Adresse client formatée
            adresse_client = devis_data.get('client_adresse_complete', f"""
{devis_data.get('client_nom', 'N/A')}<br>
{devis_data.get('adresse', '')}<br>
{devis_data.get('ville', '')}, {devis_data.get('province', '')} {devis_data.get('code_postal', '')}<br>
{devis_data.get('pays', '')}
            """).strip()
            
            # Template HTML modernisé basé sur le design de la demande de prix
            html_template = f"""
            <!DOCTYPE html>
            <html lang="fr">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Devis - {devis_data.get('numero_document', 'N/A')}</title>
                <style>
                    :root {{
                        --primary-color: #00A971;
                        --primary-color-darker: #00673D;
                        --primary-color-darkest: #004C2E;
                        --primary-color-lighter: #DCFCE7;
                        --background-color: #F9FAFB;
                        --secondary-background-color: #FFFFFF;
                        --text-color: #374151;
                        --text-color-light: #6B7280;
                        --border-color: #E5E7EB;
                        --border-radius-md: 0.5rem;
                        --box-shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
                    }}
                    
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: var(--text-color);
                        background-color: var(--background-color);
                        margin: 0;
                        padding: 15px;
                    }}
                    
                    .container {{
                        max-width: 8.5in;
                        margin: 0 auto;
                        background-color: white;
                        border-radius: 12px;
                        box-shadow: var(--box-shadow-md);
                        overflow: hidden;
                        width: 100%;
                    }}
                    
                    .header {{
                        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-color-darker) 100%);
                        color: white;
                        padding: 30px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }}
                    
                    .logo-container {{
                        display: flex;
                        align-items: center;
                        gap: 20px;
                    }}
                    
                    .logo-box {{
                        background-color: white;
                        width: 70px;
                        height: 45px;
                        border-radius: 8px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
                    }}
                    
                    .logo-text {{
                        font-family: 'Segoe UI', sans-serif;
                        font-weight: 800;
                        font-size: 24px;
                        color: var(--primary-color);
                        letter-spacing: 1px;
                    }}
                    
                    .company-info {{
                        text-align: left;
                    }}
                    
                    .company-name {{
                        font-weight: 700;
                        font-size: 28px;
                        margin-bottom: 5px;
                        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                    }}
                    
                    .company-subtitle {{
                        font-size: 16px;
                        opacity: 0.9;
                    }}
                    
                    .contact-info {{
                        text-align: right;
                        font-size: 14px;
                        line-height: 1.4;
                        opacity: 0.95;
                    }}
                    
                    .document-title {{
                        background: var(--primary-color-lighter);
                        padding: 20px 30px;
                        border-left: 5px solid var(--primary-color);
                    }}
                    
                    .document-title h1 {{
                        color: var(--primary-color-darker);
                        font-size: 24px;
                        margin-bottom: 10px;
                    }}
                    
                    .document-meta {{
                        display: flex;
                        justify-content: space-between;
                        color: var(--text-color-light);
                        font-size: 14px;
                    }}
                    
                    .content {{
                        padding: 25px;
                    }}
                    
                    .section {{
                        margin-bottom: 30px;
                    }}
                    
                    .section-title {{
                        color: var(--primary-color-darker);
                        font-size: 18px;
                        font-weight: 600;
                        margin-bottom: 15px;
                        padding-bottom: 8px;
                        border-bottom: 2px solid var(--primary-color-lighter);
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }}
                    
                    .info-grid {{
                        display: grid;
                        grid-template-columns: 1fr 1fr 1fr;
                        gap: 15px;
                        margin-bottom: 20px;
                    }}
                    
                    .info-item {{
                        background: var(--background-color);
                        padding: 15px;
                        border-radius: var(--border-radius-md);
                        border-left: 3px solid var(--primary-color);
                    }}
                    
                    .info-label {{
                        font-weight: 600;
                        color: var(--text-color-light);
                        font-size: 12px;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        margin-bottom: 5px;
                    }}
                    
                    .info-value {{
                        font-size: 16px;
                        color: var(--text-color);
                        font-weight: 500;
                    }}
                    
                    .table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 15px 0;
                        border-radius: var(--border-radius-md);
                        overflow: hidden;
                        box-shadow: var(--box-shadow-md);
                    }}
                    
                    .table th {{
                        background: var(--primary-color);
                        color: white;
                        padding: 12px;
                        text-align: left;
                        font-weight: 600;
                        font-size: 14px;
                    }}
                    
                    .table td {{
                        padding: 12px;
                        border-bottom: 1px solid var(--border-color);
                        vertical-align: top;
                    }}
                    
                    .table tr:nth-child(even) {{
                        background-color: var(--background-color);
                    }}
                    
                    .table tr:hover {{
                        background-color: var(--primary-color-lighter);
                    }}
                    
                    .badge {{
                        padding: 4px 12px;
                        border-radius: 20px;
                        font-size: 11px;
                        font-weight: 600;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        display: inline-block;
                    }}
                    
                    .badge-pending {{ background: #fef3c7; color: #92400e; }}
                    .badge-in-progress {{ background: #dbeafe; color: #1e40af; }}
                    .badge-completed {{ background: #d1fae5; color: #065f46; }}
                    .badge-on-hold {{ background: #fee2e2; color: #991b1b; }}
                    
                    .summary-box {{
                        background: linear-gradient(45deg, var(--primary-color-lighter), white);
                        border: 2px solid var(--primary-color);
                        border-radius: var(--border-radius-md);
                        padding: 20px;
                        margin: 20px 0;
                    }}
                    
                    .summary-grid {{
                        display: grid;
                        grid-template-columns: repeat(3, 1fr);
                        gap: 15px;
                    }}
                    
                    .summary-item {{
                        text-align: center;
                        background: white;
                        padding: 15px;
                        border-radius: var(--border-radius-md);
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    
                    .summary-number {{
                        font-size: 24px;
                        font-weight: 700;
                        color: var(--primary-color-darker);
                        display: block;
                    }}
                    
                    .summary-label {{
                        font-size: 12px;
                        color: var(--text-color-light);
                        text-transform: uppercase;
                        font-weight: 600;
                        letter-spacing: 0.5px;
                    }}
                    
                    .totals-box {{
                        background: var(--primary-color-darkest);
                        color: white;
                        padding: 20px;
                        border-radius: var(--border-radius-md);
                        margin: 20px 0;
                    }}
                    
                    .totals-grid {{
                        display: grid;
                        grid-template-columns: repeat(3, 1fr);
                        gap: 15px;
                    }}
                    
                    .total-item {{
                        text-align: center;
                        background: rgba(255, 255, 255, 0.1);
                        padding: 15px;
                        border-radius: var(--border-radius-md);
                    }}
                    
                    .total-amount {{
                        font-size: 22px;
                        font-weight: 700;
                        display: block;
                        margin-bottom: 5px;
                    }}
                    
                    .total-label {{
                        font-size: 12px;
                        opacity: 0.9;
                        text-transform: uppercase;
                        font-weight: 600;
                        letter-spacing: 0.5px;
                    }}
                    
                    .instructions-box {{
                        background: var(--background-color);
                        border-left: 4px solid var(--primary-color);
                        padding: 20px;
                        border-radius: 0 var(--border-radius-md) var(--border-radius-md) 0;
                        margin: 15px 0;
                    }}
                    
                    .footer {{
                        background: var(--primary-color-darkest);
                        color: white;
                        padding: 20px 30px;
                        text-align: center;
                        font-size: 12px;
                        line-height: 1.4;
                    }}
                    
                    .client-address {{
                        background: var(--background-color);
                        border: 2px solid var(--primary-color-lighter);
                        border-radius: var(--border-radius-md);
                        padding: 15px;
                        margin: 15px 0;
                        font-size: 14px;
                        line-height: 1.4;
                    }}
                    
                    @media print {{
                        body {{ 
                            margin: 0; 
                            padding: 0; 
                        }}
                        .container {{ 
                            box-shadow: none; 
                            max-width: 100%;
                            width: 8.5in;
                        }}
                        .table {{ 
                            break-inside: avoid; 
                            font-size: 12px;
                        }}
                        .section {{ 
                            break-inside: avoid-page; 
                        }}
                        .header {{
                            padding: 20px 25px;
                        }}
                        .content {{
                            padding: 20px;
                        }}
                        @page {{
                            size: letter;
                            margin: 0.5in;
                        }}
                    }}
                    
                    @media screen and (max-width: 768px) {{
                        .container {{
                            max-width: 100%;
                            margin: 0 10px;
                        }}
                        .info-grid {{
                            grid-template-columns: 1fr;
                            gap: 10px;
                        }}
                        .summary-grid, .totals-grid {{
                            grid-template-columns: repeat(2, 1fr);
                        }}
                        .header {{
                            flex-direction: column;
                            text-align: center;
                            gap: 15px;
                        }}
                        .contact-info {{
                            text-align: center;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <!-- En-tête -->
                    <div class="header">
                        <div class="logo-container">
                            <div class="logo-box">
                                <div class="logo-text">DG</div>
                            </div>
                            <div class="company-info">
                                <div class="company-name">Desmarais & Gagné inc.</div>
                                <div class="company-subtitle">Fabrication et Assemblage Métallurgique</div>
                            </div>
                        </div>
                        <div class="contact-info">
                            565 rue Maisonneuve<br>
                            Granby, QC J2G 3H5<br>
                            Tél.: (450) 372-9630<br>
                            Téléc.: (450) 372-8122
                        </div>
                    </div>
                    
                    <!-- Titre du document -->
                    <div class="document-title">
                        <h1>💰 DEVIS COMMERCIAL</h1>
                        <div class="document-meta">
                            <span><strong>N° Devis:</strong> {devis_data.get('numero_document', 'N/A')}</span>
                            <span><strong>Généré le:</strong> {datetime.now().strftime('%d/%m/%Y à %H:%M')}</span>
                        </div>
                    </div>
                    
                    <!-- Contenu principal -->
                    <div class="content">
                        <!-- Informations générales -->
                        <div class="section">
                            <h2 class="section-title">📋 Informations du Devis</h2>
                            <div class="info-grid">
                                <div class="info-item">
                                    <div class="info-label">Client</div>
                                    <div class="info-value">{devis_data.get('client_nom', 'N/A')}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Statut</div>
                                    <div class="info-value">
                                        <span class="badge {statut_class}">
                                            {statut}
                                        </span>
                                    </div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Priorité</div>
                                    <div class="info-value">
                                        <span class="badge {priorite_class}">
                                            {priorite}
                                        </span>
                                    </div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Date Création</div>
                                    <div class="info-value">{date_creation_formatted}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Date Échéance</div>
                                    <div class="info-value">{date_echeance_formatted}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Responsable</div>
                                    <div class="info-value">{devis_data.get('responsable_nom', 'N/A')}</div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Adresse du client -->
                        <div class="section">
                            <h2 class="section-title">📍 Adresse de Facturation</h2>
                            <div class="client-address">
                                {adresse_client}
                            </div>
                        </div>
                        
                        <!-- Résumé -->
                        <div class="summary-box">
                            <h3 style="color: var(--primary-color-darker); margin-bottom: 15px; text-align: center;">📋 Résumé du Devis</h3>
                            <div class="summary-grid">
                                <div class="summary-item">
                                    <span class="summary-number">{nb_lignes}</span>
                                    <span class="summary-label">Articles</span>
                                </div>
                                <div class="summary-item">
                                    <span class="summary-number">{priorite}</span>
                                    <span class="summary-label">Priorité</span>
                                </div>
                                <div class="summary-item">
                                    <span class="summary-number">{date_echeance_formatted}</span>
                                    <span class="summary-label">Échéance</span>
                                </div>
                            </div>
                        </div>
                
                        <!-- Détail des articles -->
                        <div class="section">
                            <h2 class="section-title">📝 Détail des Prestations</h2>
                            <table class="table">
                                <thead>
                                    <tr>
                                        <th>Description</th>
                                        <th style="text-align: center;">Quantité</th>
                                        <th style="text-align: center;">Unité</th>
                                        <th style="text-align: center;">Prix Unit.</th>
                                        <th style="text-align: center;">Montant</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {lignes_html}
                                </tbody>
                            </table>
                        </div>
                
                        <!-- Totaux -->
                        <div class="totals-box">
                            <h3 style="text-align: center; margin-bottom: 15px;">💰 Récapitulatif Financier</h3>
                            <div class="totals-grid">
                                <div class="total-item">
                                    <span class="total-amount">{total_ht:,.2f} $</span>
                                    <span class="total-label">Sous-total HT</span>
                                </div>
                                <div class="total-item">
                                    <span class="total-amount">{montant_tva:,.2f} $</span>
                                    <span class="total-label">TVA ({taux_tva:.3f}%)</span>
                                </div>
                                <div class="total-item">
                                    <span class="total-amount">{total_ttc:,.2f} $</span>
                                    <span class="total-label">Total TTC</span>
                                </div>
                            </div>
                        </div>
                
                        <!-- Notes du devis -->
                        {f'''
                        <div class="section">
                            <h2 class="section-title">📝 Notes et Conditions</h2>
                            <div class="instructions-box">
                                {devis_data.get('notes', 'Aucune note particulière.')}
                            </div>
                        </div>
                        ''' if devis_data.get('notes') and devis_data['notes'].strip() else ''}
                        
                        <!-- Instructions -->
                        <div class="instructions-box">
                            <h4 style="color: var(--primary-color-darker); margin-bottom: 10px;">📋 Conditions Générales</h4>
                            <p><strong>• Validité :</strong> Ce devis est valable 30 jours à compter de la date d'émission</p>
                            <p><strong>• Paiement :</strong> Net 30 jours sur réception de facture</p>
                            <p><strong>• Délais :</strong> Les délais de livraison seront confirmés lors de l'acceptation</p>
                            <p><strong>• Acceptation :</strong> Ce devis engage nos services uniquement après acceptation écrite</p>
                            <p><strong>• Contact :</strong> Pour toute question : (450) 372-9630</p>
                        </div>
                        
                    </div>
                    
                    <!-- Pied de page -->
                    <div class="footer">
                        <div><strong>🏭 Desmarais & Gagné inc.</strong> - Devis Commercial</div>
                        <div>Document généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</div>
                        <div>📞 (450) 372-9630 | 📧 info@dg-inc.com | 🌐 www.dg-inc.com</div>
                        <div style="margin-top: 10px; font-size: 11px; opacity: 0.8;">
                            Merci de mentionner le numéro de devis {devis_data.get('numero_document', 'N/A')} dans votre réponse.
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html_template
        except Exception as e:
            st.error(f"Erreur génération template HTML: {e}")
            return ""


# --- FONCTIONS UI (Déplacées de crm.py) ---

def render_devis_liste(gestionnaire: GestionnaireDevis):
    """Affiche la liste des devis."""
    st.subheader("Liste des Devis")
    
    # Filtres
    col_filtre1, col_filtre2, col_filtre3 = st.columns(3)
    
    with col_filtre1:
        filtre_statut = st.selectbox("Statut", 
            options=["Tous"] + STATUTS_DEVIS,
            key="filtre_statut_devis"
        )
    
    with col_filtre2:
        # Liste des clients
        clients = gestionnaire.crm_manager.entreprises
        client_options = [("", "Tous les clients")] + [(c['id'], c['nom']) for c in clients]
        filtre_client = st.selectbox("Client",
            options=[opt[0] for opt in client_options],
            format_func=lambda x: next((opt[1] for opt in client_options if opt[0] == x), "Tous les clients"),
            key="filtre_client_devis"
        )
    
    with col_filtre3:
        # Période
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            date_debut = st.date_input("Du", value=None, key="date_debut_devis")
        with col_date2:
            date_fin = st.date_input("Au", value=None, key="date_fin_devis")
    
    # Construire les filtres
    filters = {}
    if filtre_statut != "Tous":
        filters['statut'] = filtre_statut
    if filtre_client:
        filters['client_id'] = filtre_client
    if date_debut:
        filters['date_debut'] = date_debut.strftime('%Y-%m-%d')
    if date_fin:
        filters['date_fin'] = date_fin.strftime('%Y-%m-%d')
    
    # Récupérer et afficher les devis
    devis_list = gestionnaire.get_all_devis(filters)
    
    if devis_list:
        # Préparer les données pour l'affichage
        display_data = []
        for devis in devis_list:
            display_data.append({
                "ID": devis['id'],
                "Numéro": devis['numero_document'],
                "Client": devis['client_nom'],
                "Statut": devis['statut'],
                "Date Création": devis['date_creation'][:10] if devis.get('date_creation') else 'N/A',
                "Échéance": devis['date_echeance'],
                "Total TTC": f"{devis['totaux']['total_ttc']:,.2f} $",
                "Responsable": devis.get('responsable_nom', 'N/A')
            })
        
        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True)
        
        # Actions sur devis sélectionné
        st.markdown("---")
        selected_devis_id = st.selectbox(
            "Sélectionner un devis pour actions:",
            options=[d['id'] for d in devis_list],
            format_func=lambda x: f"#{x} - {next((d['numero_document'] for d in devis_list if d['id'] == x), '')}",
            key="selected_devis_action"
        )
        
        if selected_devis_id:
            selected_devis = next((d for d in devis_list if d['id'] == selected_devis_id), None)
            peut_supprimer = selected_devis and selected_devis.get('statut') not in ['APPROUVÉ', 'TERMINÉ']
            
            if peut_supprimer:
                col_action1, col_action2, col_action3, col_action4, col_action5, col_action6 = st.columns(6)
            else:
                col_action1, col_action2, col_action3, col_action4, col_action5 = st.columns(5)
            
            with col_action1:
                if st.button("👁️ Voir Détails", key="voir_devis", use_container_width=True):
                    st.session_state.devis_action = "view_details"
                    st.session_state.devis_selected_id = selected_devis_id
                    st.rerun()
            
            with col_action2:
                if st.button("📄 Dupliquer", key="dupliquer_devis_liste", use_container_width=True):
                    nouveau_id = gestionnaire.dupliquer_devis(selected_devis_id, 1)
                    if nouveau_id:
                        st.success(f"Devis dupliqué avec succès ! Nouveau devis #{nouveau_id}.")
                        st.rerun()
                    else:
                        st.error("Erreur lors de la duplication du devis.")
            
            with col_action3:
                if st.button("📧 Envoyer", key="send_devis", use_container_width=True):
                    if gestionnaire.changer_statut_devis(selected_devis_id, 'ENVOYÉ', 1, "Envoyé par interface"):
                        st.success("Devis marqué comme envoyé !")
                        st.rerun()
                    else:
                        st.error("Erreur lors du changement de statut.")
            
            with col_action4:
                if st.button("✏️ Modifier", key="edit_devis", use_container_width=True):
                    st.session_state.devis_action = "edit"
                    st.session_state.devis_selected_id = selected_devis_id
                    st.rerun()
            
            with col_action5:
                if st.button("📑 Export HTML", key="export_html_devis", use_container_width=True):
                    html_content = gestionnaire.export_devis_html(selected_devis_id)
                    if html_content:
                        st.download_button(
                            label="💾 Télécharger le devis HTML",
                            data=html_content,
                            file_name=f"devis_{selected_devis['numero_document']}.html",
                            mime="text/html",
                            key="download_html_devis"
                        )
                        st.success("✅ Devis HTML généré avec succès !")
                    else:
                        st.error("❌ Erreur lors de l'export HTML.")
            
            # Bouton de suppression si possible
            if peut_supprimer:
                with col_action6:
                    if st.button("🗑️ Supprimer", key="delete_devis_liste", use_container_width=True, type="secondary"):
                        st.session_state.confirm_delete_devis_id = selected_devis_id
                        st.rerun()
            
            # Gestion de la confirmation de suppression
            if 'confirm_delete_devis_id' in st.session_state and st.session_state.confirm_delete_devis_id == selected_devis_id:
                st.markdown("---")
                st.error(f"⚠️ Confirmer la suppression du devis #{selected_devis_id}")
                
                motif = st.text_input("Motif (optionnel):", key="motif_liste")
                
                col_conf, col_ann = st.columns(2)
                with col_conf:
                    if st.button("🗑️ SUPPRIMER", key="confirm_delete_liste", type="primary"):
                        if gestionnaire.supprimer_devis(selected_devis_id, 1, motif):
                            del st.session_state.confirm_delete_devis_id
                            st.rerun()
                with col_ann:
                    if st.button("❌ Annuler", key="cancel_delete_liste"):
                        del st.session_state.confirm_delete_devis_id
                        st.rerun()
    else:
        st.info("Aucun devis trouvé avec les filtres sélectionnés.")

def render_nouveau_devis_form(gestionnaire: GestionnaireDevis):
    """Formulaire pour créer un nouveau devis."""
    st.subheader("Créer un Nouveau Devis")

    # Initialisation du conteneur de lignes dans la session
    if 'devis_lignes' not in st.session_state:
        st.session_state.devis_lignes = []

    # Section pour sélectionner un produit existant
    st.markdown("**Option 1: Ajouter depuis le catalogue produits**")
    with st.container(border=True):
        col_prod1, col_prod2, col_prod3 = st.columns([2, 1, 1])
        
        with col_prod1:
            # Sélection d'un produit
            produits_options = [("", "Sélectionner un produit...")] + [(p['id'], f"{p['code_produit']} - {p['nom']}") for p in gestionnaire.product_manager.get_all_products()]
            produit_selectionne = st.selectbox(
                "Produit du catalogue",
                options=[opt[0] for opt in produits_options],
                format_func=lambda x: next((opt[1] for opt in produits_options if opt[0] == x), "Sélectionner un produit..."),
                key="produit_catalogue_select"
            )
        
        with col_prod2:
            quantite_produit = st.number_input("Quantité", min_value=0.01, value=1.0, step=0.1, key="quantite_produit_catalogue", format="%.2f")
        
        with col_prod3:
            st.write("")  # Espacement
            if st.button("➕ Ajouter depuis catalogue", key="add_from_catalog", use_container_width=True):
                if produit_selectionne:
                    produit_data = gestionnaire.product_manager.get_produit_by_id(produit_selectionne)
                    if produit_data:
                        st.session_state.devis_lignes.append({
                            'description': f"{produit_data['code_produit']} - {produit_data['nom']}",
                            'quantite': quantite_produit,
                            'unite': produit_data['unite_vente'],
                            'prix_unitaire': produit_data['prix_unitaire'],
                            'code_article': produit_data['code_produit']
                        })
                        st.success(f"Produit {produit_data['code_produit']} ajouté au devis!")
                        st.rerun()
                else:
                    st.warning("Veuillez sélectionner un produit.")

    st.markdown("**Option 2: Saisie manuelle**")
    # Formulaire pour ajouter une ligne manuellement
    with st.container(border=True):
        col_ligne1, col_ligne2, col_ligne3, col_ligne4, col_ligne5 = st.columns([3, 1, 1, 1, 1])
        with col_ligne1:
            description = st.text_input("Description", key="ligne_description")
        with col_ligne2:
            quantite = st.number_input("Qté", min_value=0.01, value=1.0, step=0.1, key="ligne_quantite", format="%.2f")
        with col_ligne3:
            unite = st.selectbox("Unité", options=UNITES_VENTE, key="ligne_unite")
        with col_ligne4:
            prix_unitaire = st.number_input("Prix U.", min_value=0.0, step=0.01, key="ligne_prix", format="%.2f")
        with col_ligne5:
            st.write("") # Espace pour aligner le bouton
            if st.button("➕ Ajouter", key="ajouter_ligne_btn", use_container_width=True):
                if description and quantite > 0:
                    st.session_state.devis_lignes.append({
                        'description': description,
                        'quantite': quantite,
                        'unite': unite,
                        'prix_unitaire': prix_unitaire
                    })
                    st.rerun()
                else:
                    st.warning("La description et la quantité sont requises.")
    
    # Affichage des lignes déjà ajoutées
    if st.session_state.devis_lignes:
        st.markdown("**Lignes du devis :**")
        total_ht_preview = 0
        with st.container(border=True):
            for i, ligne in enumerate(st.session_state.devis_lignes):
                col_disp, col_del = st.columns([10, 1])
                with col_disp:
                    montant = ligne['quantite'] * ligne['prix_unitaire']
                    total_ht_preview += montant
                    st.write(f"• {ligne['description']} ({ligne['quantite']} {ligne['unite']} x {ligne['prix_unitaire']:.2f} $) = **{montant:.2f} $**")
                with col_del:
                    if st.button("🗑️", key=f"remove_ligne_{i}", help="Supprimer la ligne"):
                        st.session_state.devis_lignes.pop(i)
                        st.rerun()
            st.markdown(f"**Total (HT) : {total_ht_preview:,.2f} $**")
    
    st.markdown("---")
    st.markdown("##### Informations générales et création")

    with st.form("formulaire_nouveau_devis"):
        col_base1, col_base2 = st.columns(2)
        
        with col_base1:
            # Client
            clients = gestionnaire.crm_manager.entreprises
            client_options = [(c['id'], c['nom']) for c in clients]
            client_id = st.selectbox("Client *", options=[opt[0] for opt in client_options],
                                     format_func=lambda x: next((opt[1] for opt in client_options if opt[0] == x), ''),
                                     key="nouveau_devis_client")
            
            # Responsable
            employees = gestionnaire.db.execute_query("SELECT id, prenom || ' ' || nom as nom FROM employees WHERE statut = 'ACTIF'")
            emp_options = [(e['id'], e['nom']) for e in employees] if employees else []
            responsable_id = st.selectbox("Responsable *", options=[opt[0] for opt in emp_options],
                                          format_func=lambda x: next((opt[1] for opt in emp_options if opt[0] == x), ''),
                                          key="nouveau_devis_responsable")

        with col_base2:
            echeance = st.date_input("Date d'échéance *", value=datetime.now().date() + timedelta(days=30),
                                     key="nouveau_devis_echeance")
            
            projets = gestionnaire.db.execute_query("SELECT id, nom_projet FROM projects WHERE statut != 'TERMINÉ'")
            projet_options = [("", "Aucun projet")] + [(p['id'], p['nom_projet']) for p in projets] if projets else [("", "Aucun projet")]
            projet_id = st.selectbox("Projet lié", options=[opt[0] for opt in projet_options],
                                     format_func=lambda x: next((opt[1] for opt in projet_options if opt[0] == x), 'Aucun projet'),
                                     key="nouveau_devis_projet")
        
        notes = st.text_area("Notes ou conditions", key="nouveau_devis_notes")
        
        # Boutons de soumission
        submitted = st.form_submit_button("💾 Créer le Devis en Brouillon", type="primary", use_container_width=True)
        
        if submitted:
            if not client_id or not responsable_id or not st.session_state.devis_lignes:
                st.error("Veuillez remplir le client, le responsable et ajouter au moins une ligne au devis.")
            else:
                devis_data = {
                    'client_company_id': client_id,
                    'employee_id': responsable_id,
                    'project_id': projet_id if projet_id else None,
                    'date_echeance': echeance.strftime('%Y-%m-%d'),
                    'notes': notes,
                    'lignes': st.session_state.devis_lignes
                }
                
                devis_id = gestionnaire.create_devis(devis_data)
                
                if devis_id:
                    devis_cree = gestionnaire.get_devis_complet(devis_id)
                    st.success(f"✅ Devis créé avec succès ! Numéro : {devis_cree.get('numero_document')}")
                    st.session_state.devis_lignes = []  # Vider les lignes pour le prochain devis
                    st.rerun()
                else:
                    st.error("Erreur lors de la création du devis.")

def render_devis_details(gestionnaire: GestionnaireDevis, devis_data):
    """Affiche les détails d'un devis avec option de suppression et export HTML."""
    if not devis_data:
        st.error("Devis non trouvé.")
        return

    st.subheader(f"🧾 Détails du Devis: {devis_data.get('numero_document')}")

    # Informations principales
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**ID:** {devis_data.get('id')}")
        st.write(f"**Client:** {devis_data.get('client_nom', 'N/A')}")
        st.write(f"**Responsable:** {devis_data.get('responsable_nom', 'N/A')}")
        st.write(f"**Statut:** {devis_data.get('statut', 'N/A')}")
    with c2:
        date_creation = devis_data.get('date_creation')
        st.write(f"**Date création:** {date_creation[:10] if date_creation else 'N/A'}")
        st.write(f"**Date échéance:** {devis_data.get('date_echeance', 'N/A')}")
        st.write(f"**Projet lié:** {devis_data.get('nom_projet', 'Aucun')}")

    # Adresse du client
    if devis_data.get('client_adresse_complete'):
        st.markdown("### 📍 Adresse du Client")
        st.text_area("client_adresse_devis", value=devis_data['client_adresse_complete'], height=100, disabled=True, label_visibility="collapsed")

    # Totaux
    totaux = devis_data.get('totaux', {})
    st.markdown("### 💰 Totaux")
    col_total1, col_total2, col_total3 = st.columns(3)
    with col_total1:
        st.metric("Total HT", f"{totaux.get('total_ht', 0):,.2f} $")
    with col_total2:
        st.metric("TVA", f"{totaux.get('montant_tva', 0):,.2f} $")
    with col_total3:
        st.metric("Total TTC", f"{totaux.get('total_ttc', 0):,.2f} $")

    # Lignes du devis
    st.markdown("### 📋 Lignes du Devis")
    if devis_data.get('lignes'):
        lignes_df_data = []
        for ligne in devis_data['lignes']:
            lignes_df_data.append({
                "Description": ligne.get('description', ''),
                "Quantité": ligne.get('quantite', 0),
                "Unité": ligne.get('unite', ''),
                "Prix unitaire": f"{ligne.get('prix_unitaire', 0):,.2f} $",
                "Montant": f"{ligne.get('quantite', 0) * ligne.get('prix_unitaire', 0):,.2f} $"
            })
        
        st.dataframe(pd.DataFrame(lignes_df_data), use_container_width=True)
    else:
        st.info("Aucune ligne dans ce devis.")

    # Notes
    st.markdown("### 📝 Notes")
    st.text_area("devis_detail_notes_display", value=devis_data.get('notes', 'Aucune note.'), height=100, disabled=True, label_visibility="collapsed")

    # Actions
    st.markdown("### 🔧 Actions")
    
    statuts_non_supprimables = ['APPROUVÉ', 'TERMINÉ']
    peut_supprimer = devis_data.get('statut') not in statuts_non_supprimables
    responsable_id = devis_data.get('employee_id', 1)

    if peut_supprimer:
        col_action1, col_action2, col_action3, col_action4, col_action5, col_action6 = st.columns(6)
    else:
        col_action1, col_action2, col_action3, col_action4, col_action5 = st.columns(5)

    with col_action1:
        if st.button("✅ Accepter", key="accepter_devis"):
            if gestionnaire.changer_statut_devis(devis_data['id'], 'APPROUVÉ', responsable_id, "Approuvé via interface"):
                st.success("Devis approuvé !")
                st.rerun()
    
    with col_action2:
        if st.button("❌ Refuser", key="refuser_devis"):
            if gestionnaire.changer_statut_devis(devis_data['id'], 'ANNULÉ', responsable_id, "Refusé/Annulé via interface"):
                st.success("Devis annulé.")
                st.rerun()
    
    with col_action3:
        if st.button("📧 Envoyer", key="envoyer_devis"):
            if gestionnaire.changer_statut_devis(devis_data['id'], 'ENVOYÉ', responsable_id, "Envoyé via interface"):
                st.success("Devis marqué comme envoyé!")
                st.rerun()
    
    with col_action4:
        if st.button("📄 Dupliquer", key="dupliquer_devis"):
            nouveau_id = gestionnaire.dupliquer_devis(devis_data['id'], responsable_id)
            if nouveau_id:
                st.success(f"Devis dupliqué! Nouveau ID: {nouveau_id}")
                st.rerun()

    with col_action5:
        if st.button("📑 Export HTML", key="export_html_devis_details"):
            html_content = gestionnaire.export_devis_html(devis_data['id'])
            if html_content:
                st.download_button(
                    label="💾 Télécharger le devis HTML",
                    data=html_content,
                    file_name=f"devis_{devis_data.get('numero_document')}.html",
                    mime="text/html",
                    key="download_html_devis_details"
                )
                st.success("✅ Devis HTML généré avec succès !")
            else:
                st.error("❌ Erreur lors de l'export HTML.")

    # Bouton de suppression si possible
    if peut_supprimer:
        with col_action6:
            if st.button("🗑️ Supprimer", key="supprimer_devis_btn", type="secondary"):
                st.session_state.confirm_delete_devis_details = devis_data['id']
                st.rerun()

    # Gestion de la confirmation de suppression
    if 'confirm_delete_devis_details' in st.session_state and st.session_state.confirm_delete_devis_details == devis_data['id']:
        st.markdown("---")
        st.error(f"⚠️ **ATTENTION : Suppression définitive du devis {devis_data.get('numero_document')}**")
        st.warning("Cette action est irréversible. Le devis et toutes ses données seront définitivement supprimés de la base de données.")
        
        motif_suppression = st.text_input(
            "Motif de suppression (optionnel):", 
            placeholder="Ex: Erreur de saisie, doublon, demande client...",
            key="motif_suppression_devis"
        )
        
        col_confirm, col_cancel = st.columns(2)
        
        with col_confirm:
            if st.button("🗑️ CONFIRMER LA SUPPRESSION", key="confirm_delete_devis", type="primary"):
                if gestionnaire.supprimer_devis(devis_data['id'], responsable_id, motif_suppression):
                    del st.session_state.confirm_delete_devis_details
                    st.session_state.devis_action = None
                    st.session_state.devis_selected_id = None
                    st.rerun()
                else:
                    del st.session_state.confirm_delete_devis_details
        
        with col_cancel:
            if st.button("❌ Annuler la suppression", key="cancel_delete_devis"):
                del st.session_state.confirm_delete_devis_details
                st.rerun()

    if st.button("Retour à la liste des devis", key="back_to_devis_list_from_details"):
        st.session_state.devis_action = None
        st.rerun()

def render_devis_statistics(gestionnaire: GestionnaireDevis):
    """Affiche les statistiques des devis."""
    st.subheader("Statistiques des Devis")
    
    stats = gestionnaire.get_devis_statistics()
    
    if stats.get('total_devis', 0) > 0:
        # Affichage des métriques principales
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Devis", stats.get('total_devis', 0))
        with col2:
            st.metric("Taux d'acceptation", f"{stats.get('taux_acceptation', 0):.1f}%")
        with col3:
            montant_total = stats.get('montant_total', 0.0)
            st.metric("Montant Total (HT)", f"{montant_total:,.0f} $")
        with col4:
            st.metric("En Attente", stats.get('en_attente', 0))
        
        # Graphiques
        if stats.get('par_statut'):
            statut_data = pd.DataFrame([
                {'Statut': k, 'Nombre': v['count'], 'Montant HT': v['montant']}
                for k, v in stats['par_statut'].items() if isinstance(v, dict)
            ])
            
            col_graph1, col_graph2 = st.columns(2)
            
            with col_graph1:
                st.markdown("**Répartition par Statut (Nombre)**")
                st.bar_chart(statut_data.set_index('Statut')['Nombre'])
            
            with col_graph2:
                st.markdown("**Répartition par Statut (Montant HT)**")
                st.bar_chart(statut_data.set_index('Statut')['Montant HT'])
    else:
        st.info("Aucune donnée de devis disponible pour les statistiques.")

def handle_devis_actions(gestionnaire: GestionnaireDevis):
    """Gestionnaire centralisé des actions pour les devis."""
    action = st.session_state.get('devis_action')
    selected_id = st.session_state.get('devis_selected_id')
    
    if action == "view_details" and selected_id:
        devis_data = gestionnaire.get_devis_complet(selected_id)
        render_devis_details(gestionnaire, devis_data)
    elif action == "edit" and selected_id:
        # Pour l'édition, on pourrait créer une fonction render_edit_devis_form similaire
        st.info("Fonction d'édition à implémenter")
        if st.button("Retour"):
            st.session_state.devis_action = None
            st.rerun()

def show_devis_page():
    """Point d'entrée principal pour la page des devis."""
    st.title("🧾 Gestion des Devis")
    
    if 'gestionnaire_devis' not in st.session_state:
        st.error("Gestionnaire de devis non initialisé.")
        return
        
    gestionnaire = st.session_state.gestionnaire_devis

    # Vérifier s'il y a une action en cours
    if st.session_state.get('devis_action'):
        handle_devis_actions(gestionnaire)
        return

    # Statistiques en haut
    stats = gestionnaire.get_devis_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Devis", stats.get('total_devis', 0))
    with col2:
        st.metric("Taux d'acceptation", f"{stats.get('taux_acceptation', 0):.1f}%")
    with col3:
        montant_total = stats.get('montant_total', 0.0)
        st.metric("Montant Total (HT)", f"{montant_total:,.0f} $")
    with col4:
        st.metric("En Attente", stats.get('en_attente', 0))

    tab1, tab2, tab3 = st.tabs(["📋 Liste des Devis", "➕ Nouveau Devis", "📊 Statistiques"])
    
    with tab1:
        render_devis_liste(gestionnaire)
    
    with tab2:
        render_nouveau_devis_form(gestionnaire)
    
    with tab3:
        render_devis_statistics(gestionnaire)