import { formatAssumption, formatResultLabel } from "@/lib/model-analysis-labels";
import { analyzeModel } from "@/api/drivewise";
/** Risposte della Decision Bar contestuale: solo ciò che restituisce l'analisi modello dell'API. */
import type { Vehicle } from "@/services/vehicleService";
import { euro } from "@/lib/vehicle-format";

export const contextualSuggestions = [
  "Quanto costa?",
  "Quanto costa mantenerla?",
  "Cosa devo controllare?",
];

const NO_DATA = "Questo dato non è presente nel catalogo DriveWise: preferiamo non stimarlo.";

export async function datasetAnswer(_question: string, v: Vehicle): Promise<string> {
  const response = await analyzeModel({ vehicle_id: v.id, analysis_scope: ["price", "maintenance", "red_flags", "tco"] });
  const costs = response.estimated_costs;
  return [
    costs.market_reference_price_eur !== null ? `Prezzo di riferimento: ${euro(costs.market_reference_price_eur)}.` : "",
    ...response.red_flags.map(formatResultLabel),
    ...response.checklist.map(formatResultLabel),
    ...response.warnings.map(formatResultLabel),
    ...response.assumptions.map(formatAssumption),
    ...(response.missing_data.length ? [`Dati da aggiungere: ${response.missing_data.map(formatResultLabel).join(", ")}.`] : []),
  ].filter(Boolean).join(" ") || NO_DATA;
}
