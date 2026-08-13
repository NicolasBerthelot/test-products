# Produits IGN — prototype

Site vitrine des produits numériques de l'IGN, sur le modèle de [beta.gouv.fr/startups](https://beta.gouv.fr/startups) et utilisant le [Système de Design de l'État (DSFR)](https://www.systeme-de-design.gouv.fr/).

## Démarrer

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # génère le site statique dans dist/
npm run preview  # prévisualise le build
```

## Structure

```
src/
  data/produits.json        ← données produits (générées depuis le CSV Grist)
  layouts/Base.astro         ← header/footer DSFR, styles communs
  pages/index.astro          ← page d'accueil : hero + filtres + grille de cartes
  pages/produits/[slug].astro ← fiche produit (une page par produit)
```

Le DSFR est chargé via CDN (jsDelivr, version 1.15.2) dans `Base.astro` — pas de
build DSFR à gérer, mais possibilité de passer au package npm officiel
(`@gouvfr/dsfr`) si besoin d'un contrôle plus fin ou d'un usage hors-ligne.

## Régénérer les données depuis un nouvel export CSV

Le fichier `scripts/csv_to_json.py` reproduit la transformation utilisée pour
générer `src/data/produits.json` : il remplit les cellules "Offre" vides
(fusionnées dans Grist) et normalise chaque ligne en un objet JSON avec un
slug pour l'URL.

```bash
python3 scripts/csv_to_json.py chemin/vers/export.csv src/data/produits.json
```

## Passer à une connexion live avec l'API Grist

Pour remplacer l'export CSV manuel par une synchronisation automatique :

1. Récupérer une clé API Grist (paramètres du compte Grist) et l'ID du
   document + de la table `Produits`.
2. Appeler l'API REST Grist au moment du build :
   `GET https://{votre-instance}.getgrist.com/api/docs/{docId}/tables/Produits/records`
3. Remplacer la lecture de `src/data/produits.json` par un fetch vers cette
   API dans `getStaticPaths()` (page produit) et dans `index.astro`, en
   gardant la même forme de données pour ne pas casser les templates.
4. Si vous voulez des mises à jour sans redéploiement complet, envisager le
   mode `server` d'Astro (SSR) plutôt que `static`, ou un rebuild périodique
   déclenché par un cron / webhook Grist.

## Prochaines étapes suggérées

- Ajouter une recherche texte libre en plus des filtres par offre.
- Illustrer chaque produit (capture d'écran, logo).
- Ajouter une page "Offres" listant les grandes familles de produits.
- Brancher un vrai hébergement (Vercel, Netlify, ou infra interne IGN/DINUM).
