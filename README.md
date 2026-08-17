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
  data/produits.json        ← données produits (synchronisées depuis l'API Grist)
  layouts/Base.astro         ← header/footer DSFR, styles communs
  pages/index.astro          ← page d'accueil : hero + filtres + grille de cartes
  pages/produits/[slug].astro ← fiche produit (une page par produit)
```

Le DSFR est chargé via CDN (jsDelivr, version 1.15.2) dans `Base.astro` — pas de
build DSFR à gérer, mais possibilité de passer au package npm officiel
(`@gouvfr/dsfr`) si besoin d'un contrôle plus fin ou d'un usage hors-ligne.

## Données : synchronisation live avec Grist

Les données produits viennent du document Grist
[Fiches produits](https://grist.numerique.gouv.fr/o/docs/toCYiKQga5KP/Fiches-produits/p/1)
(table `Produits`). `src/data/produits.json` est **régénéré automatiquement
à chaque déploiement** (voir `.github/workflows/deploy.yml`) :

- déclenchement toutes les heures (`schedule: cron`), sur chaque push sur
  `main`, ou manuellement depuis l'onglet Actions du dépôt ;
- le job récupère les enregistrements via l'API REST Grist
  (`scripts/grist_to_json.py`), régénère `produits.json`, puis build et
  déploie le site. Rien n'est commité dans le dépôt : la donnée est
  toujours régénérée à la volée dans la CI.

Le site reste 100% statique (Astro `output: 'static'`, hébergement GitHub
Pages) — c'est un *rebuild périodique*, pas du server-side rendering :
les données affichées ont donc jusqu'à une heure de retard sur Grist, pas
un accès temps réel à chaque visite. Pour du temps réel, il faudrait passer
Astro en mode `server` (SSR) sur un hébergeur qui exécute du Node (Vercel,
Netlify, Cloudflare...) — GitHub Pages ne le permet pas.

### Configurer le secret GitHub

Dans le dépôt GitHub : `Settings → Secrets and variables → Actions → New
repository secret`, créer `GRIST_API_KEY` avec une clé API Grist (Profil
Grist → API key sur grist.numerique.gouv.fr). Ne jamais commiter cette clé.

### Tester la synchronisation en local

```bash
cp .env.example .env        # puis renseigner GRIST_API_KEY dans .env
pip install -r scripts/requirements.txt
python scripts/grist_to_json.py src/data/produits.json
```

### Illustrer un produit

Ajouter une colonne **"Image"** dans la table Grist `Produits` (facultative,
ignorée si absente) :

- soit une colonne **Texte** contenant une URL d'image directe (la plus
  simple : hébergez l'image où vous voulez et collez le lien) ;
- soit une colonne **Pièces jointes** Grist : le fichier est alors
  téléchargé par `grist_to_json.py` au moment du build et re-hébergé dans
  `public/images/{slug}.ext` (ce dossier est généré, pas commité — voir
  `.gitignore`). Une image direct-URL n'a pas cette dépendance et reste
  visible même sans relancer le script de synchronisation.

### Équipe : photos, rôles et services des agents

La table Grist `Equipes` (colonnes `Prenom`, `Nom`, `Fonction`, `Service`,
et la `ReferenceList` `Produits` qui relie chaque agent à ses fiches
produits) alimente la section "Équipe" en bas de chaque fiche produit :

- **`Photo`** (facultative) : URL texte directe, ou pièce jointe Grist
  téléchargée au build et re-hébergée dans `public/agents/agent-{id}.ext`
  (généré, pas commité — comme `public/images/`). Sans photo, l'image par
  défaut `public/agent.png` (commitée, celle-ci) est utilisée à la place.
- **`Fonction`** (facultative) : affichée sous le nom de l'agent.
- **`Service`** (facultative, ex. `"DP/SPP"`, `"Prestataire"`) : affichée
  sous forme de tag coloré. La couleur est dérivée du préfixe avant le
  `/` (la "direction") par une fonction de hash vers une palette fixe
  (`serviceColor` dans `[slug].astro`) : une même direction a toujours la
  même couleur, et toute nouvelle direction en obtient une automatiquement,
  sans modification de code.

### Solution de secours : régénérer depuis un export CSV

Si l'API Grist est indisponible, `scripts/csv_to_json.py` reproduit la même
transformation à partir d'un export CSV manuel (il remplit les cellules
"Offre" vides des vues groupées avant de normaliser chaque ligne) :

```bash
python3 scripts/csv_to_json.py chemin/vers/export.csv src/data/produits.json
```

## Prochaines étapes suggérées

- Ajouter une page "Offres" listant les grandes familles de produits.
- Notifier (issue GitHub, webhook) en cas d'échec répété du sync horaire.
- Widget d'édition Grist custom pour une saisie plus légère que le tableur.
- Brancher un vrai hébergement (Vercel, Netlify, ou infra interne IGN/DINUM) si le temps réel devient nécessaire.
