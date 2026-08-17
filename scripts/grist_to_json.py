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
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter, Retry

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Le job GitHub Actions tourne toutes les heures sans supervision : on absorbe
# les aléas réseau transitoires (reset TLS, timeout, 5xx) plutôt que de faire
# échouer tout le déploiement pour un simple hoquet de connexion.
_session = requests.Session()
_retries = Retry(total=4, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
_session.mount("https://", HTTPAdapter(max_retries=_retries))
_session.mount("http://", HTTPAdapter(max_retries=_retries))

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
    "Dernière mise à jour": "derniereMiseAJour",
    "Dernière mise à jour par": "derniereMiseAJourPar",
    "Vision à 5 ans": "vision5ans",
    "Cibles prioritaires": "ciblesPrioritaires",
    "Principaux objectifs (1 an)": "objectifs1an",
}

DATE_FIELDS = {"Dernière mise à jour"}

# Colonnes "Image" (table Produits) et "Photo" (table Equipes), facultatives :
# URL texte directe, ou pièce jointe Grist téléchargée au moment du build et
# re-hébergée dans public/images/ ou public/agents/.
PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
IMAGES_DIR = PUBLIC_DIR / "images"
AGENTS_DIR = PUBLIC_DIR / "agents"


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s


def clean_scalar(v, label: str = ""):
    """Nettoie une valeur déjà résolue en texte/nombre (pas une référence)."""
    if v is None:
        return None
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        if label in DATE_FIELDS:
            # Colonne Date/DateTime : Grist renvoie un timestamp Unix (secondes, UTC).
            try:
                return datetime.fromtimestamp(v, tz=timezone.utc).strftime("%d-%m-%Y")
            except (OverflowError, OSError, ValueError):
                return str(v)
        # Une valeur numérique sur un champ censé être du texte indique en général
        # une colonne mal identifiée plutôt qu'une vraie donnée : on l'ignore.
        print(f"Attention : valeur numérique inattendue pour '{label}' ({v!r}), ignorée", file=sys.stderr)
        return None
    v = str(v).strip()
    return v if v else None


def fetch_json(url: str, api_key: str):
    resp = _session.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_columns(base_url: str, doc_id: str, table: str, api_key: str) -> list:
    return fetch_json(f"{base_url}/api/docs/{doc_id}/tables/{table}/columns", api_key).get("columns", [])


def build_label_to_column(base_url: str, doc_id: str, table: str, api_key: str) -> dict:
    """label -> {"colId": ..., "type": ...} (type ex: 'Text', 'Ref:Offre', 'RefList:Equipe', 'Date')."""
    mapping = {}
    for col in fetch_columns(base_url, doc_id, table, api_key):
        fields = col.get("fields", {}) or {}
        label = fields.get("label")
        if not label:
            continue
        label = label.strip()
        if label in mapping and mapping[label]["colId"] != col["id"]:
            print(
                f"Attention : plusieurs colonnes Grist portent le libellé '{label}' "
                f"({mapping[label]['colId']!r} et {col['id']!r}) — la première trouvée est utilisée.",
                file=sys.stderr,
            )
            continue
        mapping[label] = {"colId": col["id"], "type": fields.get("type", "Text")}
    return mapping


def build_reference_map(base_url: str, doc_id: str, ref_table: str, api_key: str) -> dict:
    """{row_id: texte affiché} pour une table de référence simple (ex: table Offre)."""
    columns = fetch_columns(base_url, doc_id, ref_table, api_key)
    text_columns = [
        col for col in columns
        if (col.get("fields", {}) or {}).get("type", "Text") in ("Text", "Choice")
    ]

    text_col_id = None
    # Convention Grist courante : la colonne d'affichage d'une table de référence
    # porte souvent le même nom que la table (ex: colonne "Offre" dans la table "Offre").
    for col in text_columns:
        label = (col.get("fields", {}) or {}).get("label", "")
        if label.strip().lower() == ref_table.strip().lower():
            text_col_id = col["id"]
            break
    if text_col_id is None and text_columns:
        text_col_id = text_columns[0]["id"]
    if text_col_id is None and columns:
        text_col_id = columns[0]["id"]

    records = fetch_json(f"{base_url}/api/docs/{doc_id}/tables/{ref_table}/records", api_key).get("records", [])
    ref_map = {}
    for r in records:
        value = (r.get("fields", {}) or {}).get(text_col_id) if text_col_id else None
        ref_map[r["id"]] = clean_scalar(value, ref_table)
    return ref_map


def resolve_attachment_or_url(
    raw, col_type: str, dest_dir: Path, dest_stem: str, base_url: str, doc_id: str, api_key: str, label: str
):
    """Résout une colonne Image/Photo : URL texte directe telle quelle, ou
    pièce jointe Grist téléchargée au moment du build et re-hébergée sous
    public/<dest_dir.name>/<dest_stem>.<ext>."""
    if raw is None:
        return None

    if col_type != "Attachments":
        return clean_scalar(raw, label)

    if not isinstance(raw, list) or len(raw) < 2:
        return None
    attachment_id = raw[1]

    try:
        meta = fetch_json(f"{base_url}/api/docs/{doc_id}/attachments/{attachment_id}", api_key)
        resp = _session.get(
            f"{base_url}/api/docs/{doc_id}/attachments/{attachment_id}/download",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Attention : téléchargement impossible pour '{label}' ({dest_stem}, pièce jointe {attachment_id}) : {e}", file=sys.stderr)
        return None

    filename = (meta.get("fields", meta) or {}).get("fileName") or str(attachment_id)
    ext = os.path.splitext(filename)[1] or ".jpg"
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / f"{dest_stem}{ext}").write_bytes(resp.content)
    return f"{dest_dir.name}/{dest_stem}{ext}"


def resolve_image(fields: dict, label_to_column: dict, slug: str, base_url: str, doc_id: str, api_key: str):
    """URL d'illustration produit (colonne "Image" de la table Produits)."""
    col = label_to_column.get("Image")
    if not col:
        return None
    raw = fields.get(col["colId"])
    return resolve_attachment_or_url(raw, col["type"], IMAGES_DIR, slug, base_url, doc_id, api_key, "Image")


def build_team_by_product(base_url: str, doc_id: str, api_key: str) -> dict:
    """{produit_row_id: [{"nom": ..., "photo": ...}, ...]} à partir de la
    table Equipes (Prenom, Nom, Photo, et la ReferenceList "Produits" qui
    relie chaque agent aux fiches produits sur lesquelles il travaille).

    On identifie les colonnes par colId (Prenom, Nom, Photo, Produits) et
    non par libellé affiché : contrairement à la table Produits (dont les
    libellés humains sont fixés par la spec), cette table est la nôtre et
    son libellé affiché peut différer du colId (ex. "Prénom" accentué pour
    un colId "Prenom", qui ne peut pas contenir d'accent) — matcher sur le
    colId, stable, évite de dépendre de ce libellé.
    """
    col_types = {col["id"]: (col.get("fields", {}) or {}).get("type", "Text") for col in fetch_columns(base_url, doc_id, "Equipes", api_key)}
    required = ["Prenom", "Nom", "Produits"]
    missing = [col_id for col_id in required if col_id not in col_types]
    if missing:
        print(f"Attention : colonnes introuvables dans la table Equipes (ignorées) : {missing}", file=sys.stderr)
        return {}

    records = fetch_json(f"{base_url}/api/docs/{doc_id}/tables/Equipes/records", api_key).get("records", [])

    team_by_product: dict = {}
    for r in records:
        fields = r.get("fields", {})
        prenom = clean_scalar(fields.get("Prenom"), "Prenom")
        nom_famille = clean_scalar(fields.get("Nom"), "Nom")
        full_name = " ".join(part for part in (prenom, nom_famille) if part)
        if not full_name:
            continue

        photo = None
        if "Photo" in col_types:
            photo = resolve_attachment_or_url(
                fields.get("Photo"), col_types["Photo"], AGENTS_DIR, f"agent-{r['id']}", base_url, doc_id, api_key, "Photo"
            )

        fonction = clean_scalar(fields.get("Fonction"), "Fonction") if "Fonction" in col_types else None

        raw_produits = fields.get("Produits")
        product_ids = raw_produits[1:] if isinstance(raw_produits, list) and raw_produits[:1] == ["L"] else []
        for pid in product_ids:
            team_by_product.setdefault(pid, []).append({"nom": full_name, "photo": photo, "fonction": fonction})

    return team_by_product


def resolve_value(raw, col_type: str, label: str, base_url: str, doc_id: str, api_key: str, ref_cache: dict):
    """Résout une valeur brute Grist en texte, en suivant les colonnes Reference/RefList."""
    if raw is None:
        return None

    if col_type.startswith("Ref:"):
        ref_table = col_type.split(":", 1)[1]
        if not isinstance(raw, (int, float)) or raw == 0:
            return None
        if ref_table not in ref_cache:
            ref_cache[ref_table] = build_reference_map(base_url, doc_id, ref_table, api_key)
        text = ref_cache[ref_table].get(int(raw))
        if text is None:
            print(f"Attention : référence introuvable pour '{label}' (table {ref_table}, id={raw!r})", file=sys.stderr)
        return text

    if col_type.startswith("RefList:"):
        ref_table = col_type.split(":", 1)[1]
        if not isinstance(raw, list) or len(raw) < 2:
            return None
        if ref_table not in ref_cache:
            ref_cache[ref_table] = build_reference_map(base_url, doc_id, ref_table, api_key)
        texts = [ref_cache[ref_table].get(int(rid)) for rid in raw[1:]]
        texts = [t for t in texts if t]
        return ", ".join(texts) if texts else None

    if isinstance(raw, list):
        # ChoiceList (et listes similaires) : Grist encode ["L", valeur1, valeur2, ...],
        # les valeurs sont déjà du texte, pas des id à résoudre.
        items = raw[1:] if raw[:1] == ["L"] else raw
        texts = [clean_scalar(v, label) for v in items]
        texts = [t for t in texts if t]
        return ", ".join(texts) if texts else None

    return clean_scalar(raw, label)


def main(out_path: str):
    api_key = os.environ["GRIST_API_KEY"]
    doc_id = os.environ.get("GRIST_DOC_ID", "toCYiKQga5KP")
    table = os.environ.get("GRIST_TABLE", "Produits")
    base_url = os.environ.get("GRIST_BASE_URL", "https://grist.numerique.gouv.fr").rstrip("/")

    label_to_column = build_label_to_column(base_url, doc_id, table, api_key)

    missing = [label for label in LABEL_TO_KEY if label not in label_to_column]
    if missing:
        print(f"Attention : colonnes introuvables dans Grist (ignorées) : {missing}", file=sys.stderr)

    records_data = fetch_json(f"{base_url}/api/docs/{doc_id}/tables/{table}/records", api_key)
    records = records_data.get("records", [])

    team_by_product = build_team_by_product(base_url, doc_id, api_key)

    ref_cache: dict = {}

    def get(label, fields):
        col = label_to_column.get(label)
        if not col:
            return None
        raw = fields.get(col["colId"])
        return resolve_value(raw, col["type"], label, base_url, doc_id, api_key, ref_cache)

    products = []
    last_offre = None
    for record in records:
        fields = record.get("fields", {})

        nom = get("Nom du produit", fields)
        if not nom:
            continue
        slug = slugify(nom)

        # L'"Offre" peut être vide sur certaines lignes selon la vue Grist utilisée
        # (cellules groupées) : on propage la dernière valeur connue, comme pour le CSV.
        offre = get("Offre", fields)
        if offre is None:
            offre = last_offre
        else:
            last_offre = offre

        product = {"slug": slug, "nom": nom}
        for label, key in LABEL_TO_KEY.items():
            if key == "nom":
                continue
            product[key] = offre if key == "offre" else get(label, fields)
        product["image"] = resolve_image(fields, label_to_column, slug, base_url, doc_id, api_key)
        product["equipe"] = team_by_product.get(record["id"], [])

        products.append(product)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"{len(products)} produits écrits dans {out_path} (source: Grist, doc {doc_id}, table {table})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
