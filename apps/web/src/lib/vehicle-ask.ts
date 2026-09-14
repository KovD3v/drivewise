import { formatResultLabel } from "@/views/ModelAnalysis";
import { analyzeModel } from "@/api/drivewise";
/** Risposte della Decision Bar contestuale: solo dati presenti nel dataset. */
import type { Vehicle } from "@/services/vehicleService";
import { euro, vehicleName } from "@/lib/vehicle-format";

export const contextualSuggestions = [
  "Quanto costa?",
  "È affidabile?",
  "Quanto è rischioso il furto?",
  "È adatto alla città?",
];

const NO_DATA = "Questo dato non è presente nel dataset DriveWise: preferiamo non stimarlo.";

export async function datasetAnswer(question: string, v: Vehicle): Promise<string> {
  if (!v.mock) {
    const response = await analyzeModel({ vehicle_id: v.id, analysis_scope: ['price', 'maintenance', 'red_flags', 'tco'] });
    const costs = response.estimated_costs;
    return [costs.market_reference_price_eur !== null ? `Prezzo di riferimento: ${euro(costs.market_reference_price_eur)}.` : '',
      ...response.red_flags.map(formatResultLabel), ...response.checklist.map(formatResultLabel), ...response.warnings.map(formatResultLabel), ...response.assumptions, ...(response.missing_data.length ? [`Dati da aggiungere: ${response.missing_data.map(formatResultLabel).join(", ")}.`] : [])].filter(Boolean).join(' ') || NO_DATA;
  }

  const q = question.toLowerCase();
  const name = vehicleName(v);
  const dna = v.vehicle_dna;

  if (q.includes("cost") || q.includes("prezzo") || q.includes("quanto costa"))
    return typeof v.pricing.new_price_estimate === "number"
      ? `${name} ha un prezzo indicativo del nuovo di ${euro(v.pricing.new_price_estimate)}.`
      : NO_DATA;

  if (q.includes("affidab"))
    return typeof dna.reliability === "number"
      ? `L'indice di affidabilità di ${name} nel dataset è ${dna.reliability}/100.`
      : NO_DATA;

  if (q.includes("furt") || q.includes("rubat")) {
    const observed = v.theft_risk.observed_thefts_italy_2024;
    return typeof observed === "number"
      ? `Nel ${v.theft_risk.data_year} in Italia sono stati osservati ${observed.toLocaleString("it-IT")} furti di questo modello${
          typeof v.theft_risk.recovery_rate_pct === "number"
            ? `, con un tasso di ritrovamento del ${v.theft_risk.recovery_rate_pct}%`
            : ""
        }. È un volume osservato, non una probabilità.`
      : "Questo modello non compare nelle statistiche di furto di riferimento: non possiamo dedurne un rischio.";
  }

  if (q.includes("citt"))
    return typeof dna.city === "number"
      ? `L'attitudine urbana di ${name} è ${dna.city}/100.`
      : NO_DATA;

  if (q.includes("viagg"))
    return typeof dna.travel === "number"
      ? `Per i viaggi lunghi ${name} ottiene ${dna.travel}/100.`
      : NO_DATA;

  const best = Object.entries(dna)
    .filter((e): e is [string, number] => typeof e[1] === "number")
    .sort((a, b) => b[1] - a[1])[0];
  return best
    ? `Nel dataset il punto più forte di ${name} è ${best[0]} (${best[1]}/100).`
    : NO_DATA;
}
