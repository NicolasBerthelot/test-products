/**
 * Worker Cloudflare : ajoute une authentification HTTP Basic devant le site
 * GitHub Pages, qui n'a lui-même aucun mécanisme d'accès restreint sur un
 * dépôt public.
 *
 * Déploiement : voir README.md, section "Restreindre l'accès (Basic Auth)".
 * Ce fichier est une copie de référence, à coller manuellement dans
 * l'éditeur Cloudflare Workers (pas de déploiement automatisé pour l'instant).
 *
 * Variables d'environnement à définir comme "secrets" sur le Worker :
 *   BASIC_AUTH_USER
 *   BASIC_AUTH_PASSWORD
 */

const ORIGIN_HOST = "nicolasberthelot.github.io";

export default {
  async fetch(request, env) {
    const expected = "Basic " + btoa(`${env.BASIC_AUTH_USER}:${env.BASIC_AUTH_PASSWORD}`);
    const provided = request.headers.get("Authorization");

    if (provided !== expected) {
      return new Response("Authentification requise.", {
        status: 401,
        headers: { "WWW-Authenticate": 'Basic realm="Produits IGN", charset="UTF-8"' },
      });
    }

    const url = new URL(request.url);
    const originUrl = new URL(url.pathname + url.search, `https://${ORIGIN_HOST}`);
    const originRequest = new Request(originUrl.toString(), request);
    originRequest.headers.delete("Authorization");

    return fetch(originRequest);
  },
};
