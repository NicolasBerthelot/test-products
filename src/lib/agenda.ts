import { renderMarkdown } from "./markdown";

// Agenda du mode produit : document Grist privé de l'organisation
// mode-produit-ign, lu au moment de la construction du site avec la même
// clé API que les fiches produits (secret GRIST_API_KEY en CI, .env en local).
const GRIST_BASE_URL = "https://grist.numerique.gouv.fr";
const DOC_ID = "fDwUxVHDoVqQ";
const TABLE = "Evenements";
export const TIME_ZONE = "Europe/Paris";

export interface AgendaEvent {
  id: number;
  titre: string;
  type: string | null;
  typeColors: { fill: string; text: string } | null;
  debut: Date;
  fin: Date | null;
  lieu: string | null;
  public: string | null;
  descriptionHtml: string | null;
  capacite: number | null;
  placesRestantes: number | null;
  etat: string | null;
  annule: boolean;
  complet: boolean;
  lienInscription: string | null;
  inscriptionPossible: boolean;
}

export interface Agenda {
  aVenir: AgendaEvent[];
  passes: AgendaEvent[];
  indisponible: boolean;
}

type GristFields = Record<string, unknown>;

async function getJson(url: string, apiKey: string): Promise<any> {
  let lastError: unknown;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const resp = await fetch(url, { headers: { Authorization: `Bearer ${apiKey}` } });
      if (resp.ok) return await resp.json();
      lastError = new Error(`HTTP ${resp.status} sur ${url}`);
      if (resp.status < 500 && resp.status !== 429) break;
    } catch (e) {
      lastError = e;
    }
    await new Promise((r) => setTimeout(r, 2000 * (attempt + 1)));
  }
  throw lastError;
}

function text(v: unknown): string | null {
  if (typeof v !== "string") return null;
  const t = v.trim();
  return t ? t : null;
}

function int(v: unknown): number | null {
  return typeof v === "number" ? v : null;
}

function date(v: unknown): Date | null {
  return typeof v === "number" ? new Date(v * 1000) : null;
}

export async function loadAgenda(): Promise<Agenda> {
  const apiKey = import.meta.env.GRIST_API_KEY ?? process.env.GRIST_API_KEY;
  if (!apiKey) {
    console.warn("[agenda] GRIST_API_KEY absente : l'agenda sera vide.");
    return { aVenir: [], passes: [], indisponible: true };
  }

  const tableUrl = `${GRIST_BASE_URL}/api/docs/${DOC_ID}/tables/${TABLE}`;
  let columns: { id: string; fields: GristFields }[];
  let records: { id: number; fields: GristFields }[];
  try {
    [{ columns }, { records }] = await Promise.all([
      getJson(`${tableUrl}/columns`, apiKey),
      getJson(`${tableUrl}/records`, apiKey),
    ]);
  } catch (e) {
    console.warn(`[agenda] Lecture Grist impossible, l'agenda sera vide : ${e}`);
    return { aVenir: [], passes: [], indisponible: true };
  }

  // Les couleurs des types (Formation, Atelier...) sont celles choisies dans
  // Grist : un nouveau type ajouté dans le tableur a sa couleur sans toucher au code.
  const typeColumn = columns.find((c) => c.id === "Type");
  const choiceOptions: Record<string, { fillColor?: string; textColor?: string }> = (() => {
    try {
      return JSON.parse(String(typeColumn?.fields.widgetOptions ?? "{}")).choiceOptions ?? {};
    } catch {
      return {};
    }
  })();

  const now = new Date();
  const events: AgendaEvent[] = [];
  for (const { id, fields: f } of records) {
    const debut = date(f.Debut);
    const titre = text(f.Titre);
    if (f.Publie !== true || !debut || !titre) continue;

    const type = text(f.Type);
    const colors = type ? choiceOptions[type] : undefined;
    const fin = date(f.Fin);
    const annule = f.Annule === true;
    const complet = f.Complet === true;
    const lienInscription = text(f.Lien_inscription);
    const description = text(f.Description);

    events.push({
      id,
      titre,
      type,
      typeColors: colors?.fillColor ? { fill: colors.fillColor, text: colors.textColor ?? "#fff" } : null,
      debut,
      fin,
      lieu: text(f.Lieu),
      public: text(f.Public),
      descriptionHtml: description ? renderMarkdown(description) : null,
      capacite: int(f.Capacite),
      placesRestantes: int(f.Places_restantes),
      etat: annule ? "Annulé" : text(f.Etat),
      annule,
      complet,
      lienInscription,
      inscriptionPossible:
        Boolean(lienInscription) && f.Inscription_requise === true && f.Inscriptions_ouvertes === true && !complet && !annule,
    });
  }

  events.sort((a, b) => a.debut.getTime() - b.debut.getTime());
  const isPast = (e: AgendaEvent) => (e.fin ?? e.debut) < now;
  return {
    aVenir: events.filter((e) => !isPast(e)),
    passes: events.filter(isPast).reverse(),
    indisponible: false,
  };
}
