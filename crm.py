# --- START OF FILE crm.py -----------------------------------------------------
"""
ERP DG Inc. – Module CRM
Refactor complet (12 juin 2025) incluant :
  • tous les nouveaux champs “enterprise-grade” pour Contacts, Entreprises
  • journal d’Interactions enrichi
  • squelette Opportunités (non exposé dans l’UI pour l’instant)
  • compatibilité descendante : les clés historiques restent inchangées
"""

from __future__ import annotations

import json
import os
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional

import pandas as pd
import streamlit as st


# --------------------------------------------------------------------------- #
# 1)  Constantes de référence
# --------------------------------------------------------------------------- #
TYPES_INTERACTION = [
    "Email", "Appel", "Réunion", "Note", "Whatsapp", "LinkedIn", "Visite",
    "Chat", "SMS", "Autre"
]
STATUTS_OPPORTUNITE = [
    "Prospection", "Qualification", "Proposition", "Négociation",
    "Gagné", "Perdu"
]
STATUTS_LEAD = ["Nouveau", "Qualifié", "Client", "Churn"]

# Liste de tous les champs attendus (sert de “schéma” léger)
DEFAULT_CONTACT: Dict[str, Any] = {
    # Identité
    "id": None, "prenom": "", "nom_famille": "", "photo_url": "",
    # Coordonnées
    "email": "", "telephone": "", "mobile": "", "adresse_postale": "",
    "linkedin_url": "", "twitter": "", "site_web_perso": "",
    # Profil pro
    "intitule_poste": "", "departement": "", "seniority": "", "zone_fuseau": "",
    # Marketing & ventes
    "source_lead": "", "statut_lead": "Nouveau", "score_lead": 0,
    "tags": [], "owner_id": None,
    # Préférences / conformité
    "opt_in_email": False, "opt_in_sms": False, "langue_preferee": "fr",
    # Divers
    "anniversaire": "", "role": "", "entreprise_id": None, "notes": "",
    # Auto
    "date_creation": "", "date_modification": ""
}

DEFAULT_ENTREPRISE: Dict[str, Any] = {
    "id": None, "nom": "", "secteur": "", "site_web": "", "site_web_sec": "",
    # Coordonnées
    "adresse": "", "adresse_facturation": "", "adresse_livraison": "",
    "telephone_principal": "", "email_general": "", "fax": "",
    # Infos légales / financières
    "num_TVA": "", "siren_bn": "", "forme_juridique": "", "date_creation_societe": "",
    "revenu_annuel": "", "effectif": "", "monnaie": "", "capital": "",
    "notation": "", "pays": "", "region": "", "fuseau_horaire": "",
    # Relationnel
    "type_compte": "Prospect", "parent_company_id": None, "ownership": "",
    # Marketing
    "source_acquisition": "", "segment": "", "industries_naics": "",
    # Divers
    "contact_principal_id": None, "notes": "",
    # Auto
    "date_creation": "", "date_modification": ""
}

DEFAULT_INTERACTION: Dict[str, Any] = {
    "id": None, "type": "", "canal": "", "contact_id": None,
    "participants": [], "entreprise_id": None, "date_interaction": "",
    "duree": 0, "resume": "", "details": "", "resultat": "",
    "suivi_prevu": "", "statut_suivi": "", "piece_jointe_urls": []
}

DEFAULT_OPPORTUNITE: Dict[str, Any] = {
    "id": None, "entreprise_id": None, "contact_id": None, "montant_estime": 0.0,
    "probabilite": 0.0, "date_cloture_pred": "", "pipeline": "Standard",
    "etape_pipeline": "Prospection", "source": "", "produits": [],
    "owner_id": None, "notes": "", "date_creation": "", "date_modification": ""
}


# --------------------------------------------------------------------------- #
# 2)  Gestionnaire CRM
# --------------------------------------------------------------------------- #
class GestionnaireCRM:
    def __init__(self, data_dir: str = ".") -> None:
        self.data_file = os.path.join(data_dir, "crm_data.json")

        # Entités en mémoire
        self.contacts: List[Dict[str, Any]] = []
        self.entreprises: List[Dict[str, Any]] = []
        self.interactions: List[Dict[str, Any]] = []
        self.opportunites: List[Dict[str, Any]] = []

        # Compteurs auto-incrément
        self.next_contact_id = 1
        self.next_entreprise_id = 1
        self.next_interaction_id = 1
        self.next_opportunite_id = 1

        self.charger_donnees_crm()

    # --------------------------------------------------------------------- #
    # Utilitaires internes
    # --------------------------------------------------------------------- #
    def _get_next_id(self, entity_list: List[Dict[str, Any]]) -> int:
        return (max((item.get("id", 0) for item in entity_list), default=0) + 1)

    def _now_iso(self) -> str:
        return datetime.now().isoformat()

    # --------------------------------------------------------------------- #
    # Chargement / sauvegarde
    # --------------------------------------------------------------------- #
    def charger_donnees_crm(self) -> None:
        if not os.path.exists(self.data_file):
            self._initialiser_donnees_demo_crm()
            return

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.contacts = data.get("contacts", [])
            self.entreprises = data.get("entreprises", [])
            self.interactions = data.get("interactions", [])
            self.opportunites = data.get("opportunites", [])

            # Recalcul des *next_id*
            self.next_contact_id = self._get_next_id(self.contacts)
            self.next_entreprise_id = self._get_next_id(self.entreprises)
            self.next_interaction_id = self._get_next_id(self.interactions)
            self.next_opportunite_id = self._get_next_id(self.opportunites)

        except Exception as e:  # noqa: BLE001
            st.error(f"Erreur chargement CRM : {e}")
            self._initialiser_donnees_demo_crm()

    def sauvegarder_donnees_crm(self) -> None:
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "contacts": self.contacts,
                        "entreprises": self.entreprises,
                        "interactions": self.interactions,
                        "opportunites": self.opportunites,
                        "next_contact_id": self.next_contact_id,
                        "next_entreprise_id": self.next_entreprise_id,
                        "next_interaction_id": self.next_interaction_id,
                        "next_opportunite_id": self.next_opportunite_id,
                        "last_update": self._now_iso(),
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:  # noqa: BLE001
            st.error(f"Erreur sauvegarde CRM : {e}")

    def _initialiser_donnees_demo_crm(self) -> None:
        """Jeu de données minimaliste pour premier démarrage."""
        now = self._now_iso()
        self.contacts = [
            {
                **DEFAULT_CONTACT,
                "id": 1,
                "prenom": "Alice",
                "nom_famille": "Martin",
                "email": "alice@techcorp.com",
                "telephone": "0102030405",
                "entreprise_id": 101,
                "role": "Responsable Marketing",
                "date_creation": now,
                "date_modification": now,
            },
            {
                **DEFAULT_CONTACT,
                "id": 2,
                "prenom": "Bob",
                "nom_famille": "Durand",
                "email": "bob@startupxyz.com",
                "mobile": "+33607080910",
                "entreprise_id": 102,
                "role": "CTO",
                "date_creation": now,
                "date_modification": now,
            },
        ]
        self.entreprises = [
            {
                **DEFAULT_ENTREPRISE,
                "id": 101,
                "nom": "TechCorp Inc.",
                "secteur": "Technologie",
                "adresse": "1 Rue de la Paix, Paris",
                "site_web": "techcorp.com",
                "contact_principal_id": 1,
                "date_creation": now,
                "date_modification": now,
            },
            {
                **DEFAULT_ENTREPRISE,
                "id": 102,
                "nom": "StartupXYZ",
                "secteur": "Logiciel",
                "adresse": "Silicon Valley",
                "site_web": "startup.xyz",
                "contact_principal_id": 2,
                "type_compte": "Client",
                "date_creation": now,
                "date_modification": now,
            },
        ]
        self.interactions = [
            {
                **DEFAULT_INTERACTION,
                "id": 1001,
                "type": "Réunion",
                "canal": "Visite",
                "contact_id": 1,
                "entreprise_id": 101,
                "date_interaction": (datetime.now() - timedelta(days=10)).isoformat(),
                "resume": "Kick-off projet E-commerce",
                "resultat": "Positif",
                "suivi_prevu": (datetime.now() - timedelta(days=3)).isoformat(),
            }
        ]

        # Réinitialiser les compteurs
        self.next_contact_id = self._get_next_id(self.contacts)
        self.next_entreprise_id = self._get_next_id(self.entreprises)
        self.next_interaction_id = self._get_next_id(self.interactions)
        self.next_opportunite_id = self._get_next_id(self.opportunites)

        self.sauvegarder_donnees_crm()

    # --------------------------------------------------------------------- #
    # 3)  CRUD – Contacts
    # --------------------------------------------------------------------- #
    def ajouter_contact(self, data: Dict[str, Any]) -> int:
        new_contact = {**DEFAULT_CONTACT, **data}
        new_contact.update(
            id=self.next_contact_id,
            date_creation=self._now_iso(),
            date_modification=self._now_iso(),
        )
        self.contacts.append(new_contact)
        self.next_contact_id += 1
        self.sauvegarder_donnees_crm()
        return new_contact["id"]

    def modifier_contact(self, contact_id: int, data_update: Dict[str, Any]) -> bool:
        contact = self.get_contact_by_id(contact_id)
        if not contact:
            return False
        contact.update(**data_update, date_modification=self._now_iso())
        self.sauvegarder_donnees_crm()
        return True

    def supprimer_contact(self, contact_id: int) -> bool:
        if not self.get_contact_by_id(contact_id):
            return False
        # Retrait des liens
        self.contacts = [c for c in self.contacts if c["id"] != contact_id]
        self.interactions = [
            i for i in self.interactions if i.get("contact_id") != contact_id
        ]
        for entreprise in self.entreprises:
            if entreprise.get("contact_principal_id") == contact_id:
                entreprise["contact_principal_id"] = None
        self.sauvegarder_donnees_crm()
        return True

    def get_contact_by_id(self, contact_id: int) -> Optional[Dict[str, Any]]:
        return next((c for c in self.contacts if c["id"] == contact_id), None)

    def get_contacts_by_entreprise_id(self, entreprise_id: int) -> List[Dict[str, Any]]:
        return [c for c in self.contacts if c.get("entreprise_id") == entreprise_id]

    # --------------------------------------------------------------------- #
    # 4)  CRUD – Entreprises
    # --------------------------------------------------------------------- #
    def ajouter_entreprise(self, data: Dict[str, Any]) -> int:
        new_ent = {**DEFAULT_ENTREPRISE, **data}
        new_ent.update(
            id=self.next_entreprise_id,
            date_creation=self._now_iso(),
            date_modification=self._now_iso(),
        )
        self.entreprises.append(new_ent)
        self.next_entreprise_id += 1
        self.sauvegarder_donnees_crm()
        return new_ent["id"]

    def modifier_entreprise(
        self, entreprise_id: int, data_update: Dict[str, Any]
    ) -> bool:
        ent = self.get_entreprise_by_id(entreprise_id)
        if not ent:
            return False
        ent.update(**data_update, date_modification=self._now_iso())
        self.sauvegarder_donnees_crm()
        return True

    def supprimer_entreprise(self, entreprise_id: int) -> bool:
        if not self.get_entreprise_by_id(entreprise_id):
            return False
        # Nettoyer les contacts liés
        for c in self.contacts:
            if c.get("entreprise_id") == entreprise_id:
                c["entreprise_id"] = None
        # Nettoyer les interactions liées
        self.interactions = [
            i
            for i in self.interactions
            if i.get("entreprise_id") != entreprise_id
        ]
        self.entreprises = [e for e in self.entreprises if e["id"] != entreprise_id]
        self.sauvegarder_donnees_crm()
        return True

    def get_entreprise_by_id(
        self, entreprise_id: int
    ) -> Optional[Dict[str, Any]]:
        return next((e for e in self.entreprises if e["id"] == entreprise_id), None)

    # --------------------------------------------------------------------- #
    # 5)  CRUD – Interactions
    # --------------------------------------------------------------------- #
    def ajouter_interaction(self, data: Dict[str, Any]) -> int:
        inter = {**DEFAULT_INTERACTION, **data}
        inter.update(
            id=self.next_interaction_id,
            date_interaction=data.get("date_interaction") or self._now_iso(),
        )
        self.interactions.append(inter)
        self.next_interaction_id += 1
        self.sauvegarder_donnees_crm()
        return inter["id"]

    def modifier_interaction(
        self, interaction_id: int, data_update: Dict[str, Any]
    ) -> bool:
        inter = self.get_interaction_by_id(interaction_id)
        if not inter:
            return False
        inter.update(**data_update)
        self.sauvegarder_donnees_crm()
        return True

    def supprimer_interaction(self, interaction_id: int) -> bool:
        self.interactions = [
            i for i in self.interactions if i["id"] != interaction_id
        ]
        self.sauvegarder_donnees_crm()
        return True

    def get_interaction_by_id(
        self, interaction_id: int
    ) -> Optional[Dict[str, Any]]:
        return next((i for i in self.interactions if i["id"] == interaction_id), None)

    def get_interactions_for_contact(
        self, contact_id: int
    ) -> List[Dict[str, Any]]:
        return sorted(
            (i for i in self.interactions if i.get("contact_id") == contact_id),
            key=lambda x: x.get("date_interaction"),
            reverse=True,
        )

    def get_interactions_for_entreprise(
        self, entreprise_id: int
    ) -> List[Dict[str, Any]]:
        return sorted(
            (i for i in self.interactions if i.get("entreprise_id") == entreprise_id),
            key=lambda x: x.get("date_interaction"),
            reverse=True,
        )

    # --------------------------------------------------------------------- #
    # 6)  CRUD – Opportunités  (API prête ; UI à venir)
    # --------------------------------------------------------------------- #
    def ajouter_opportunite(self, data: Dict[str, Any]) -> int:
        opp = {**DEFAULT_OPPORTUNITE, **data}
        opp.update(
            id=self.next_opportunite_id,
            date_creation=self._now_iso(),
            date_modification=self._now_iso(),
        )
        self.opportunites.append(opp)
        self.next_opportunite_id += 1
        self.sauvegarder_donnees_crm()
        return opp["id"]

    def modifier_opportunite(self, opp_id: int, data_update: Dict[str, Any]) -> bool:
        opp = self.get_opportunite_by_id(opp_id)
        if not opp:
            return False
        opp.update(**data_update, date_modification=self._now_iso())
        self.sauvegarder_donnees_crm()
        return True

    def supprimer_opportunite(self, opp_id: int) -> bool:
        self.opportunites = [o for o in self.opportunites if o["id"] != opp_id]
        self.sauvegarder_donnees_crm()
        return True

    def get_opportunite_by_id(self, opp_id: int) -> Optional[Dict[str, Any]]:
        return next((o for o in self.opportunites if o["id"] == opp_id), None)


# --------------------------------------------------------------------------- #
# 7)  Helpers optionnels (exploités par la partie UI Streamlit)
# --------------------------------------------------------------------------- #
def contacts_as_dataframe(gestionnaire: GestionnaireCRM) -> pd.DataFrame:
    """Conversion pratique pour affichage Streamlit."""
    df = pd.DataFrame(gestionnaire.contacts)
    if df.empty:
        return df
    # Colonnes majeures en premier
    main_cols = [
        "id", "prenom", "nom_famille", "email", "telephone",
        "mobile", "entreprise_id", "intitule_poste", "statut_lead",
        "date_creation"
    ]
    return df[[c for c in main_cols if c in df.columns] + [c for c in df.columns if c not in main_cols]]


def entreprises_as_dataframe(gestionnaire: GestionnaireCRM) -> pd.DataFrame:
    df = pd.DataFrame(gestionnaire.entreprises)
    if df.empty:
        return df
    main_cols = [
        "id", "nom", "secteur", "type_compte", "pays",
        "revenu_annuel", "effectif", "date_creation"
    ]
    return df[[c for c in main_cols if c in df.columns] + [c for c in df.columns if c not in main_cols]]


# --- END OF FILE crm.py -------------------------------------------------------
