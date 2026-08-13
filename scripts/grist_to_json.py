"""Récupère la table Produits depuis l'API Grist et génère src/data/produits.json.

Variables d'environnement attendues :
    GRIST_API_KEY   clé API Grist (Profil -> API key, sur grist.numerique.gouv.fr)
    GRIST_DOC_ID    identifiant du document (ex: toCYiKQga5KP)
    GRIST_TABLE     nom de la table (défaut: Produits)
    GRIST_BASE_URL  racine de l'instance Grist (défaut: https://grist.numerique.gouv.fr)

Usage:
    python3 scripts/grist_to_json.py src/data/produits.json
"""
import os
import re
import sys
import json
import unicodedata
from datetime import datetime, timezone

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Colonnes Grist (libellés humains, tels qu'affichés dans l'éditeur Grist)
# -> clé correspondante dans produits.json
LABEL_TO_KEY = {
    "Nom du produit": "nom",
    "Offre": "offre",
    "Promesse": "promesse",
    "Proposition de valeur": "propositionValeur",
    "Problèmes": "problemes",
    "Solutions": "solutions",
    "Canaux de déploiement": "canauxDeploiement",
    "Impact et indicateurs": "impactIndicateurs",
    "Positionnement dans l'écosytème": "positionnementEcosysteme",
    "Site web": "siteWeb",
    "Code source": "codeSource",
    "Statistiques d'usage": "statistiquesUsage",
    "Contact": "contact",
    "RACI": "raci",
    "Budget": "budget",
    "Equipe": "equipe",
    "Dernière mise à jour": "derniereMiseAJour",
    "Dernière mise à jour par": "derniereMiseAJourPar",
    "Vision à 5 ans": "vision5ans",
    "Cibles prioritaires": "ciblesPrioritaires",
    "Principaux objectifs (1 an)": "objectifs1an",
}


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s


def clean(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        # Colonnes de type Date/DateTime : Grist renvoie un timestamp Unix (secondes, UTC).
        try:
            return datetime.fromtimestamp(v, tz=timezone.utc).strftime("%d-%m-%Y")
        except (OverflowError, OSError, ValueError):
            return str(v)
    v = str(v).strip()
    return v if v else None


def fetch_json(url: str, api_key: str):
    resp = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def build_label_to_colid(base_url: str, doc_id: str, table: str, api_key: str) -> dict:
    data = fetch_json(f"{base_url}/api/docs/{doc_id}/tables/{table}/columns", api_key)
    mapping = {}
    for col in data.get("columns", []):
        label = (col.get("fields", {}) or {}).get("label")
        if label:
            mapping[label.strip()] = col["id"]
    return mapping


def main(out_path: str):
    api_key = os.environ["GRIST_API_KEY"]
    doc_id = os.environ.get("GRIST_DOC_ID", "toCYiKQga5KP")
    table = os.environ.get("GRIST_TABLE", "Produits")
    base_url = os.environ.get("GRIST_BASE_URL", "https://grist.numerique.gouv.fr").rstrip("/")

    label_to_colid = build_label_to_colid(base_url, doc_id, table, api_key)

    missing = [label for label in LABEL_TO_KEY if label not in label_to_colid]
    if missing:
        print(f"Attention : colonnes introuvables dans Grist (ignorées) : {missing}", file=sys.stderr)

    records_data = fetch_json(f"{base_url}/api/docs/{doc_id}/tables/{table}/records", api_key)
    records = records_data.get("records", [])

    products = []
    last_offre = None
    for record in records:
        fields = record.get("fields", {})

        def get(label):
            col_id = label_to_colid.get(label)
            return fields.get(col_id) if col_id else None

        nom = clean(get("Nom du produit"))
        if not nom:
            continue

        # L'"Offre" peut être vide sur certaines lignes selon la vue Grist utilisée
        # (cellules groupées) : on propage la dernière valeur connue, comme pour le CSV.
        offre = clean(get("Offre"))
        if offre is None:
            offre = last_offre
        else:
            last_offre = offre

        product = {"slug": slugify(nom), "nom": nom}
        for label, key in LABEL_TO_KEY.items():
            if key == "nom":
                continue
            product[key] = offre if key == "offre" else clean(get(label))

        products.append(product)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"{len(products)} produits écrits dans {out_path} (source: Grist, doc {doc_id}, table {table})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
