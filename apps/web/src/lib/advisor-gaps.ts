/**
 * Italian wording for the codes the Advisor puts in an item's `missing_factors` and `warnings`
 * (apps/api/app/services/advisor/scoring.py). A code without a label is counted, never shown raw.
 */
const gapLabels: Record<string, string> = {
  budget: "budget",
  category_fit: "adattamento alla categoria",
  comfort: "comfort",
  driving: "piacere di guida",
  economics: "costi",
  efficiency_range: "efficienza e autonomia",
  family: "uso familiare",
  family_fit: "uso familiare",
  garage_fit: "compatibilità con il garage",
  invalid_safety_rating: "valutazione di sicurezza valida",
  issue_applicability: "difetti noti applicabili a questa versione",
  performance: "prestazioni",
  powertrain_fit: "adattamento dell'alimentazione",
  practicality: "praticità",
  price: "prezzo",
  price_fit: "prezzo rispetto al budget",
  reliability: "affidabilità",
  reliability_assessment: "affidabilità",
  reliability_safety: "affidabilità e sicurezza",
  running_cost: "costi di gestione",
  safety: "sicurezza",
  safety_ratings: "valutazioni di sicurezza",
  space: "spazio",
  sport: "sportività",
  tax: "tasse di possesso",
  tco: "costo totale di possesso",
  technology: "tecnologia",
  travel: "viaggi",
  usage_fit: "adattamento all'uso",
  use_case_fit: "adattamento all'uso principale",
  vehicle_dna_assessment: "profilo del veicolo",
  vehicle_dna_usage: "profilo d'uso del veicolo",
};

/** `request.*` codes are answers the profile lacks, not catalogue gaps. */
const profileGapLabels: Record<string, string> = {
  "request.garage": "misure del garage",
};

function labelled(codes: string[], labels: Record<string, string>) {
  const known = [...new Set(codes.map((code) => labels[code]).filter((l): l is string => Boolean(l)))];
  const unknown = codes.filter((code) => !labels[code]).length;
  return { known, unknown };
}

function sentence(prefix: string, { known, unknown }: { known: string[]; unknown: number }) {
  if (!known.length && !unknown) return null;
  const rest = unknown ? `${known.length ? " e " : ""}${unknown === 1 ? "un altro dato" : `altri ${unknown} dati`}` : "";
  return `${prefix}: ${known.join(", ")}${rest}.`;
}

/** Plain Italian lines for what the Advisor could not check on one vehicle. */
export function describeAdvisorGaps(missingFactors: string[], warnings: string[]): string[] {
  const profileCodes = missingFactors.filter((code) => code.startsWith("request."));
  const catalogueCodes = missingFactors.filter((code) => !code.startsWith("request."));
  return [
    sentence("Dati mancanti nel catalogo", labelled(catalogueCodes, gapLabels)),
    sentence("Dati da aggiungere al tuo profilo", labelled(profileCodes, profileGapLabels)),
    sentence("Verifiche non complete", labelled(warnings, gapLabels)),
  ].filter((line): line is string => line !== null);
}
