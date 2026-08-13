"""Convertit un export CSV Grist (table Produits) en src/data/produits.json.

Usage:
    python3 scripts/csv_to_json.py chemin/vers/export.csv src/data/produits.json
"""
import sys
import re
import json
import unicodedata
import pandas as pd


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s


def clean(v):
    if pd.isna(v):
        return None
    v = str(v).strip()
    return v if v else None


def main(csv_path: str, out_path: str):
    df = pd.read_csv(csv_path)
    # "Offre" n'est renseigné que sur la première ligne de chaque groupe
    # dans l'export Grist : on propage la dernière valeur connue.
    df["Offre"] = df["Offre"].ffill()

    products = []
    for _, row in df.iterrows():
        nom = clean(row["Nom du produit"])
        if not nom:
            continue
        products.append({
            "slug": slugify(nom),
            "offre": clean(row["Offre"]),
            "nom": nom,
            "promesse": clean(row["Promesse"]),
            "propositionValeur": clean(row["Proposition de valeur"]),
            "problemes": clean(row["Problèmes"]),
            "solutions": clean(row["Solutions"]),
            "canauxDeploiement": clean(row["Canaux de déploiement"]),
            "impactIndicateurs": clean(row["Impact et indicateurs"]),
            "positionnementEcosysteme": clean(row["Positionnement dans l'écosytème"]),
            "siteWeb": clean(row["Site web"]),
            "codeSource": clean(row["Code source"]),
            "statistiquesUsage": clean(row["Statistiques d'usage"]),
            "contact": clean(row["Contact"]),
            "raci": clean(row["RACI"]),
            "budget": clean(row["Budget"]),
            "equipe": clean(row["Equipe"]),
            "derniereMiseAJour": clean(row["Dernière mise à jour"]),
            "derniereMiseAJourPar": clean(row["Dernière mise à jour par"]),
            "vision5ans": clean(row["Vision à 5 ans"]),
            "ciblesPrioritaires": clean(row["Cibles prioritaires"]),
            "objectifs1an": clean(row["Principaux objectifs (1 an)"]),
        })

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"{len(products)} produits écrits dans {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
