# products.py - Module de Gestion des Produits Finis pour ERP Production DG Inc.
# Permet de définir des produits standards avec leur nomenclature (BOM) et leur gamme de fabrication (Routing).

import streamlit as st
import pandas as pd
import json
from erp_database import ERPDatabase

class GestionnaireProduits:
    """
    Gestionnaire pour la logique métier des produits finis.
    """
    def __init__(self, db: ERPDatabase):
        self.db = db

    def get_all_products_summary(self):
        """Récupère un résumé de tous les produits pour la vue liste."""
        query = """
            SELECT 
                p.id, p.product_code, p.name, p.category, p.status, p.standard_price,
                (SELECT COUNT(*) FROM product_bom pb WHERE pb.product_id = p.id) as bom_item_count,
                (SELECT COUNT(*) FROM product_routing pr WHERE pr.product_id = p.id) as routing_step_count,
                (SELECT COALESCE(SUM(i.last_cost * pb.quantity), 0) 
                 FROM product_bom pb 
                 JOIN inventory_items i ON pb.inventory_item_id = i.id 
                 WHERE pb.product_id = p.id) as calculated_cost
            FROM products p
            ORDER BY p.name
        """
        try:
            results = self.db.execute_query(query)
            return [dict(row) for row in results]
        except Exception as e:
            st.error(f"Erreur de récupération des produits : {e}")
            return []

    def get_full_product_details(self, product_id: int):
        """Récupère toutes les informations d'un produit, y compris BOM et Routing."""
        product_details = {}
        product_info = self.db.execute_query("SELECT * FROM products WHERE id = ?", (product_id,))
        if not product_info:
            return None
        product_details['info'] = dict(product_info[0])

        # Récupérer la Nomenclature (BOM)
        bom_query = """
            SELECT pb.id as bom_id, i.id as item_id, i.nom as item_name, i.code_interne, pb.quantity, pb.unit
            FROM product_bom pb
            JOIN inventory_items i ON pb.inventory_item_id = i.id
            WHERE pb.product_id = ?
            ORDER BY i.nom
        """
        product_details['bom'] = [dict(row) for row in self.db.execute_query(bom_query, (product_id,))]

        # Récupérer la Gamme (Routing)
        routing_query = """
            SELECT pr.id as routing_id, wc.id as center_id, wc.nom as center_name, pr.sequence_number, pr.description, pr.standard_time
            FROM product_routing pr
            JOIN work_centers wc ON pr.work_center_id = wc.id
            WHERE pr.product_id = ?
            ORDER BY pr.sequence_number
        """
        product_details['routing'] = [dict(row) for row in self.db.execute_query(routing_query, (product_id,))]
        
        return product_details

    def save_product(self, product_data, bom_data, routing_data):
        """Sauvegarde un produit (création ou mise à jour)."""
        product_id = product_data.get('id')
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                if product_id: # Mise à jour
                    cursor.execute("""
                        UPDATE products SET product_code=?, name=?, description=?, category=?, status=?, standard_price=?, unit_of_measure=?, image_url=?, updated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    """, (
                        product_data['product_code'], product_data['name'], product_data['description'],
                        product_data['category'], product_data['status'], product_data['standard_price'],
                        product_data['unit_of_measure'], product_data.get('image_url'), product_id
                    ))
                    # Nettoyer l'ancienne BOM et Routing
                    cursor.execute("DELETE FROM product_bom WHERE product_id = ?", (product_id,))
                    cursor.execute("DELETE FROM product_routing WHERE product_id = ?", (product_id,))
                else: # Création
                    cursor.execute("""
                        INSERT INTO products (product_code, name, description, category, status, standard_price, unit_of_measure, image_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        product_data['product_code'], product_data['name'], product_data['description'],
                        product_data['category'], product_data['status'], product_data['standard_price'],
                        product_data['unit_of_measure'], product_data.get('image_url')
                    ))
                    product_id = cursor.lastrowid
                
                # Insérer la nouvelle BOM
                for item in bom_data:
                    if item.get('inventory_item_id') and item.get('quantity') > 0:
                        cursor.execute("""
                            INSERT INTO product_bom (product_id, inventory_item_id, quantity, unit)
                            VALUES (?, ?, ?, ?)
                        """, (product_id, item['inventory_item_id'], item['quantity'], item['unit']))

                # Insérer la nouvelle Gamme
                for step in routing_data:
                     if step.get('work_center_id') and step.get('sequence_number') > 0:
                        cursor.execute("""
                            INSERT INTO product_routing (product_id, work_center_id, sequence_number, description, standard_time)
                            VALUES (?, ?, ?, ?, ?)
                        """, (product_id, step['work_center_id'], step['sequence_number'], step['description'], step['standard_time']))
                
                conn.commit()
            return product_id
        except Exception as e:
            st.error(f"Erreur de sauvegarde du produit : {e}")
            return None

    def delete_product(self, product_id):
        """Supprime un produit et ses dépendances."""
        # Vérification des dépendances (projets, lignes de formulaires, etc.)
        project_deps = self.db.execute_query("SELECT COUNT(*) as count FROM projects WHERE product_id = ?", (product_id,))[0]['count']
        if project_deps > 0:
            st.error(f"Impossible de supprimer : ce produit est utilisé dans {project_deps} projet(s).")
            return False

        try:
            # La suppression en cascade est gérée par les FK de la DB
            self.db.execute_update("DELETE FROM products WHERE id = ?", (product_id,))
            return True
        except Exception as e:
            st.error(f"Erreur lors de la suppression : {e}")
            return False

def render_product_form(gestionnaire: GestionnaireProduits, product_id=None):
    """Affiche le formulaire de création/modification d'un produit."""
    
    # Charger les données si en mode édition
    if product_id:
        details = gestionnaire.get_full_product_details(product_id)
        if not details:
            st.error("Produit non trouvé.")
            return
        product_info = details['info']
        bom_data = details['bom']
        routing_data = details['routing']
        st.subheader(f"Modifier le Produit : {product_info['name']}")
    else:
        product_info = {}
        bom_data = []
        routing_data = []
        st.subheader("Créer un Nouveau Produit")

    with st.form("product_form"):
        # --- Informations Générales ---
        st.markdown("#### Informations Générales")
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Nom du produit *", value=product_info.get("name", ""))
            product_code = st.text_input("Code produit *", value=product_info.get("product_code", ""))
            category = st.text_input("Catégorie", value=product_info.get("category", ""))
        with c2:
            status = st.selectbox("Statut", ["ACTIF", "DEVELOPPEMENT", "OBSOLETE"], index=["ACTIF", "DEVELOPPEMENT", "OBSOLETE"].index(product_info.get("status", "ACTIF")))
            standard_price = st.number_input("Prix de vente standard", min_value=0.0, value=float(product_info.get("standard_price", 0.0)), format="%.2f")
            unit_of_measure = st.text_input("Unité de mesure", value=product_info.get("unit_of_measure", "pièce"))

        description = st.text_area("Description", value=product_info.get("description", ""))
        
        # --- Nomenclature (BOM) ---
        st.markdown("---")
        st.markdown("#### Nomenclature (Bill of Materials)")
        
        # Charger les articles d'inventaire pour la sélection
        inventory_items = gestionnaire.db.execute_query("SELECT id, nom, code_interne FROM inventory_items ORDER BY nom")
        inventory_options = {item['id']: f"{item['nom']} ({item['code_interne']})" for item in inventory_items}

        if 'form_bom' not in st.session_state or st.session_state.product_form_id != product_id:
            st.session_state.form_bom = [{'inventory_item_id': b['item_id'], 'quantity': b['quantity'], 'unit': b['unit']} for b in bom_data]
            st.session_state.product_form_id = product_id

        for i, item in enumerate(st.session_state.form_bom):
            c1, c2, c3, c4 = st.columns([4, 2, 1, 1])
            with c1:
                item['inventory_item_id'] = c1.selectbox(f"Article {i+1}", options=list(inventory_options.keys()), format_func=lambda x: inventory_options.get(x, "Sélectionner..."), key=f"bom_item_{i}", index=list(inventory_options.keys()).index(item['inventory_item_id']) if item.get('inventory_item_id') in inventory_options else 0)
            with c2:
                item['quantity'] = c2.number_input("Quantité", min_value=0.0, value=float(item.get('quantity', 1.0)), key=f"bom_qty_{i}", format="%.4f")
            with c3:
                item['unit'] = c3.text_input("Unité", value=item.get("unit", "pcs"), key=f"bom_unit_{i}")
            with c4:
                if c4.button("🗑️", key=f"del_bom_{i}"):
                    st.session_state.form_bom.pop(i)
                    st.rerun()

        if st.button("➕ Ajouter un article à la nomenclature"):
            st.session_state.form_bom.append({})
            st.rerun()

        # --- Gamme de Fabrication (Routing) ---
        st.markdown("---")
        st.markdown("#### Gamme de Fabrication (Routing)")
        
        work_centers = gestionnaire.db.execute_query("SELECT id, nom FROM work_centers WHERE status = 'ACTIF' ORDER BY nom")
        wc_options = {wc['id']: wc['nom'] for wc in work_centers}

        if 'form_routing' not in st.session_state or st.session_state.product_form_id != product_id:
             st.session_state.form_routing = [{'sequence_number': r['sequence_number'], 'work_center_id': r['center_id'], 'description': r['description'], 'standard_time': r['standard_time']} for r in routing_data]
        
        for i, step in enumerate(st.session_state.form_routing):
            c1, c2, c3, c4, c5 = st.columns([1, 3, 4, 2, 1])
            with c1:
                step['sequence_number'] = c1.number_input("Seq.", min_value=10, step=10, value=int(step.get('sequence_number', (i + 1) * 10)), key=f"rt_seq_{i}")
            with c2:
                step['work_center_id'] = c2.selectbox("Poste", options=list(wc_options.keys()), format_func=lambda x: wc_options.get(x, "Sélectionner..."), key=f"rt_wc_{i}", index=list(wc_options.keys()).index(step['work_center_id']) if step.get('work_center_id') in wc_options else 0)
            with c3:
                step['description'] = c3.text_input("Description", value=step.get("description", ""), key=f"rt_desc_{i}")
            with c4:
                step['standard_time'] = c4.number_input("Temps (h)", min_value=0.0, value=float(step.get('standard_time', 0.0)), key=f"rt_time_{i}", format="%.2f")
            with c5:
                 if c5.button("🗑️", key=f"del_rt_{i}"):
                    st.session_state.form_routing.pop(i)
                    st.rerun()
        
        if st.button("➕ Ajouter une étape à la gamme"):
            st.session_state.form_routing.append({})
            st.rerun()

        # --- Actions ---
        st.markdown("---")
        submitted = st.form_submit_button("💾 Sauvegarder le Produit", type="primary")

        if submitted:
            if not name or not product_code:
                st.error("Le nom et le code du produit sont obligatoires.")
            else:
                product_payload = {
                    'id': product_id,
                    'name': name,
                    'product_code': product_code,
                    'category': category,
                    'status': status,
                    'standard_price': standard_price,
                    'unit_of_measure': unit_of_measure,
                    'description': description
                }
                new_id = gestionnaire.save_product(product_payload, st.session_state.form_bom, st.session_state.form_routing)
                if new_id:
                    st.success(f"Produit '{name}' sauvegardé avec succès (ID: {new_id}).")
                    st.session_state.product_action = "list"
                    st.session_state.product_form_id = None # Reset form state
                    st.rerun()
                # Erreur gérée dans la méthode save_product

def show_products_page():
    """Page principale du module Produits."""
    st.title("📦 Gestion des Produits")
    st.markdown("Définissez ici vos produits standards, leur nomenclature et leur gamme de fabrication.")

    if 'erp_db' not in st.session_state:
        st.error("La base de données n'est pas initialisée.")
        return
        
    gestionnaire = GestionnaireProduits(st.session_state.erp_db)

    # Initialiser l'état de la session pour ce module
    if 'product_action' not in st.session_state:
        st.session_state.product_action = "list"
    if 'selected_product_id' not in st.session_state:
        st.session_state.selected_product_id = None

    # Barre de navigation du module
    c1, c2, c3 = st.columns([1,1,2])
    if c1.button("📋 Liste des produits", use_container_width=True):
        st.session_state.product_action = "list"
        st.rerun()
    if c2.button("➕ Créer un produit", use_container_width=True):
        st.session_state.product_action = "create"
        st.session_state.selected_product_id = None
        st.rerun()
    
    # Routage de l'action
    if st.session_state.product_action == "list":
        st.subheader("Liste des Produits Standards")
        products = gestionnaire.get_all_products_summary()
        if not products:
            st.info("Aucun produit défini. Cliquez sur 'Créer un produit' pour commencer.")
        else:
            df = pd.DataFrame(products)
            st.dataframe(df, use_container_width=True, hide_index=True, column_config={
                "id": "ID", "product_code": "Code", "name": "Nom", "category": "Catégorie",
                "status": "Statut", "standard_price": st.column_config.NumberColumn("Prix Vente", format="$%.2f"),
                "bom_item_count": "Nb Articles BOM", "routing_step_count": "Nb Étapes Gamme",
                "calculated_cost": st.column_config.NumberColumn("Coût Standard", format="$%.2f"),
            })

            selected_id = st.selectbox("Sélectionner un produit pour le modifier :", options=[""] + [p['id'] for p in products], format_func=lambda x: f"#{x} - {next((p['name'] for p in products if p['id']==x), 'Choisir...')}" if x else "Choisir...")
            if selected_id:
                st.session_state.product_action = "edit"
                st.session_state.selected_product_id = selected_id
                st.rerun()

    elif st.session_state.product_action == "create":
        render_product_form(gestionnaire)

    elif st.session_state.product_action == "edit":
        if st.session_state.selected_product_id:
            render_product_form(gestionnaire, st.session_state.selected_product_id)
        else:
            st.warning("Aucun produit sélectionné. Retour à la liste.")
            st.session_state.product_action = "list"
            st.rerun()
