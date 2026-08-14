# Restreindre l'accès au site (Basic Auth via Cloudflare Worker)

GitHub Pages ne propose aucun contrôle d'accès pour un dépôt public : tout
le monde peut atteindre `https://nicolasberthelot.github.io/test-products/`
sans authentification. `basic-auth-worker.js` est un petit Worker
Cloudflare (gratuit) qui s'intercale devant le site : il exige un couple
identifiant/mot de passe (authentification HTTP Basic, gérée nativement par
le navigateur) avant de transmettre la requête à GitHub Pages.

**Limite importante :** ce Worker protège l'URL `*.workers.dev` que vous
partagez, pas l'origine GitHub Pages elle-même. Si quelqu'un connaît ou
devine l'URL `nicolasberthelot.github.io/test-products/`, il y accède sans
mot de passe — GitHub ne permet pas de bloquer l'origine pour un dépôt
public. `public/robots.txt` et la balise `<meta name="robots" content="noindex, nofollow">`
(voir `src/layouts/Base.astro`) évitent au moins que cette URL directe soit
indexée par les moteurs de recherche. Pour une vraie restriction de
l'origine, il faudrait soit un dépôt privé (plan GitHub payant), soit
migrer l'hébergement (voir README principal, section Grist live).

## Déploiement (dashboard Cloudflare, sans CLI)

1. Créer un compte Cloudflare gratuit sur [dash.cloudflare.com](https://dash.cloudflare.com)
   si vous n'en avez pas déjà un.
2. **Workers & Pages → Create → Create Worker**. Donnez-lui un nom (ex.
   `produits-ign-gate`) puis **Deploy** (crée un Worker "Hello World" par
   défaut, sur `https://produits-ign-gate.<votre-sous-domaine>.workers.dev`).
3. **Edit code** : remplacez tout le contenu par celui de
   [`basic-auth-worker.js`](basic-auth-worker.js) → **Save and Deploy**.
4. Dans les **Settings** du Worker → **Variables and Secrets** → ajoutez
   deux variables de type **Secret** (pas "texte en clair") :
   - `BASIC_AUTH_USER`
   - `BASIC_AUTH_PASSWORD`

   Choisissez un couple simple à partager avec l'équipe (ce n'est pas un
   compte individuel, juste un mot de passe partagé).
5. Le site protégé est accessible à :
   `https://produits-ign-gate.<votre-sous-domaine>.workers.dev/test-products/`
   (le `/test-products/` final est nécessaire — c'est le `base` configuré
   dans `astro.config.mjs`). Le navigateur affichera une popup native
   demandant l'identifiant/mot de passe.
6. Partagez cette URL (et les identifiants, par un canal séparé — pas dans
   le dépôt Git) à l'équipe, à la place du lien GitHub Pages direct.

## Rotation / changement du mot de passe

Modifier les secrets `BASIC_AUTH_USER` / `BASIC_AUTH_PASSWORD` dans les
mêmes réglages du Worker (Settings → Variables and Secrets) — effet
immédiat, aucun redéploiement de code nécessaire.
