import { marked } from "marked";
import sanitizeHtml from "sanitize-html";

// Les fiches produits sont saisies via l'éditeur Markdown de l'admin (voir
// admin/src/components/ProductForm.astro) par des utilisateurs internes,
// puis affichées publiquement : on décale les titres Markdown (h1/h2 ->
// h3+) pour ne pas casser la hiérarchie de la page (h1 = nom du produit,
// h2 = titre de section), et on assainit le HTML généré avant affichage.
marked.use({
  breaks: true,
  renderer: {
    heading({ tokens, depth }) {
      const level = Math.min(depth + 2, 6);
      const text = this.parser.parseInline(tokens);
      return `<h${level}>${text}</h${level}>\n`;
    },
  },
});

const ALLOWED_TAGS = [
  ...sanitizeHtml.defaults.allowedTags.filter((tag) => tag !== "h1" && tag !== "h2"),
  "img",
];

export function renderMarkdown(input: string): string {
  const html = marked.parse(input, { async: false }) as string;
  return sanitizeHtml(html, {
    allowedTags: ALLOWED_TAGS,
    allowedAttributes: {
      ...sanitizeHtml.defaults.allowedAttributes,
      a: ["href", "name"],
    },
    transformTags: {
      a: sanitizeHtml.simpleTransform("a", { target: "_blank", rel: "noopener noreferrer" }),
    },
  });
}
