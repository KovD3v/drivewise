/**
 * Composizione dinamica delle sezioni del report per tipo veicolo.
 * Regola: nessuna sezione se il dato sottostante è assente (mai card vuote).
 * Gli id corrispondono a quelli attesi da decision_test_scenarios.json.
 */
import { garageFit, type GarageFitResult } from "@/lib/decision-engine";
import type { DecisionProfile } from "@/lib/decision-profile";
import type { Vehicle } from "@/services/vehicleService";

export type ReportSectionId =
  | "boot"
  | "family"
  | "garage"
  | "comfort"
  | "running_cost"
  | "tco"
  | "seat_height"
  | "wet_weight"
  | "experience_fit"
  | "passenger"
  | "wind_protection"
  | "luggage"
  | "underseat"
  | "agility"
  | "ring_road_fit"
  | "parking"
  | "theft_risk";

export type ReportSection = {
  id: ReportSectionId;
  label: string;
  value: string;
  detail?: string | undefined;
  /** 0-100 quando il dato è un punteggio del dataset. */
  score?: number | undefined;
  icon: string;
};

const garageVerdict: Record<Exclude<GarageFitResult, "unknown">, string> = {
  fits: "Entra comodamente",
  tight: "Entra con margini ridotti",
  no: "Non entra",
};

const experienceLabel: Record<string, string> = {
  beginner: "Principianti",
  beginner_intermediate: "Principianti / intermedi",
  intermediate: "Intermedi",
  experienced: "Esperti",
};

/** TCO indicativo v1: solo se prezzo e running_cost sono presenti nel dataset. */
export function estimatedYearlyCost(v: Vehicle): number | null {
  if (v.mockDetails) return null;
  const price = v.pricing.new_price_estimate;
  const running = v.vehicle_dna.running_cost;
  if (typeof price !== "number" || typeof running !== "number") return null;
  const efficiency = 1 - running / 100;
  const base = v.vehicle_type === "car" ? 0.055 : 0.045;
  return Math.round((price * (base + efficiency * 0.05)) / 10) * 10;
}

export function buildReportSections(v: Vehicle, profile: DecisionProfile): ReportSection[] {
  const out: ReportSection[] = [];
  const push = (s: ReportSection | null) => {
    if (s) out.push(s);
  };
  const num = (x: unknown): x is number => typeof x === "number";

  if (v.vehicle_type === "car") {
    const d = v.dimensions;
    if (num(d?.boot_liters))
      push({ id: "boot", label: "Bagagliaio", value: `${d.boot_liters} litri`, icon: "boot" });
    if (num(v.vehicle_dna.family))
      push({
        id: "family",
        label: "Famiglia",
        value: `${v.vehicle_dna.family}/100`,
        score: v.vehicle_dna.family,
        icon: "family",
      });
    if (profile.garage_status === "known") {
      const fit = garageFit(v, profile);
      if (fit !== "unknown" && num(d?.length_mm) && num(d?.width_with_mirrors_mm))
        push({
          id: "garage",
          label: "Garage",
          value: garageVerdict[fit],
          detail: `${Math.round(d.length_mm / 10)} × ${Math.round(d.width_with_mirrors_mm / 10)} cm con specchietti`,
          icon: "garage",
        });
    }
    if (num(v.vehicle_dna.comfort))
      push({
        id: "comfort",
        label: "Comfort",
        value: `${v.vehicle_dna.comfort}/100`,
        score: v.vehicle_dna.comfort,
        icon: "comfort",
      });
    if (num(v.vehicle_dna.running_cost))
      push({
        id: "running_cost",
        label: "Consumi e costi",
        value: `${v.vehicle_dna.running_cost}/100`,
        detail: v.powertrain?.fuel ?? undefined,
        score: v.vehicle_dna.running_cost,
        icon: "cost",
      });
    const tco = estimatedYearlyCost(v);
    if (tco !== null)
      push({
        id: "tco",
        label: "Costo annuo stimato",
        value: `${tco.toLocaleString("it-IT")} €`,
        detail: "Stima indicativa derivata da prezzo ed economia di gestione",
        icon: "tco",
      });
  }

  if (v.vehicle_type === "motorcycle") {
    const m = v.motorcycle_specific;
    if (num(m?.wet_weight_kg))
      push({ id: "wet_weight", label: "Peso", value: `${m.wet_weight_kg} kg`, icon: "weight" });
    if (num(m?.seat_height_mm))
      push({
        id: "seat_height",
        label: "Altezza sella",
        value: `${m.seat_height_mm} mm`,
        detail: profile.rider_height_cm ? `Altezza pilota ${profile.rider_height_cm} cm` : undefined,
        icon: "seat",
      });
    if (m?.recommended_experience)
      push({
        id: "experience_fit",
        label: "Esperienza consigliata",
        value: experienceLabel[m.recommended_experience] ?? m.recommended_experience,
        icon: "experience",
      });
    if (num(m?.passenger_comfort_score))
      push({
        id: "passenger",
        label: "Comfort passeggero",
        value: `${m.passenger_comfort_score}/100`,
        score: m.passenger_comfort_score,
        icon: "passenger",
      });
    if (num(m?.wind_protection_score))
      push({
        id: "wind_protection",
        label: "Protezione aerodinamica",
        value: `${m.wind_protection_score}/100`,
        score: m.wind_protection_score,
        icon: "wind",
      });
    if (num(m?.wet_weight_kg) && num(m?.wind_protection_score))
      push({
        id: "luggage",
        label: "Capacità bagagli",
        value:
          m.wind_protection_score >= 75
            ? "Predisposizione da viaggio"
            : "Adatta a carichi leggeri",
        detail: "Valutata su protezione aerodinamica e peso",
        icon: "luggage",
      });
  }

  if (v.vehicle_type === "scooter") {
    const s = v.scooter_specific;
    if (num(s?.underseat_storage_l))
      push({
        id: "underseat",
        label: "Sottosella",
        value: `${s.underseat_storage_l} litri`,
        detail:
          s.helmet_storage_full_face === true
            ? "Casco integrale: sì"
            : s.helmet_storage_full_face === false
              ? "Casco integrale: no"
              : undefined,
        icon: "underseat",
      });
    if (num(s?.urban_agility_score))
      push({
        id: "agility",
        label: "Agilità urbana",
        value: `${s.urban_agility_score}/100`,
        score: s.urban_agility_score,
        icon: "agility",
      });
    if (num(s?.ring_road_fit_score))
      push({
        id: "ring_road_fit",
        label: "Tangenziale",
        value: `${s.ring_road_fit_score}/100`,
        score: s.ring_road_fit_score,
        icon: "ringroad",
      });
    if (num(s?.wet_weight_kg))
      push({
        id: "parking",
        label: "Parcheggio",
        value: `${s.wet_weight_kg} kg`,
        detail: num(s.urban_agility_score) ? `Agilità ${s.urban_agility_score}/100` : undefined,
        icon: "parking",
      });
  }

  const theftObserved = v.theft_risk.observed_thefts_italy_2024;
  const theftRequested = (profile.priorities ?? []).includes("theft_risk");
  if (typeof theftObserved === "number")
    push({
      id: "theft_risk",
      label: "Furti osservati",
      value: theftObserved.toLocaleString("it-IT"),
      detail: v.theft_risk.data_year ? `Italia ${v.theft_risk.data_year}` : undefined,
      icon: "theft",
    });
  else if (theftRequested)
    push({
      id: "theft_risk",
      label: "Furti osservati",
      value: "Nessun dato osservato",
      detail: "Il modello non compare nelle statistiche di riferimento",
      icon: "theft",
    });

  return v.mockDetails ? out.map(s => ["family", "comfort", "running_cost"].includes(s.id) ? { ...s, detail: "Demo: indice simulato, non una valutazione del veicolo." } : s) : out;
}

/** Blocchi di affidabilità sempre letti da vehicle_dna. */
export function reliabilityMetrics(v: Vehicle) {
  const keys: [keyof Vehicle["vehicle_dna"], string][] = [
    ["reliability", "Affidabilità"],
    ["running_cost", "Costo di gestione"],
    ["technology", "Tecnologia"],
    ["comfort", "Comfort"],
    ["safety", "Sicurezza"],
  ];
  return keys
    .map(([key, label]) => ({ key, label, value: v.vehicle_dna[key] }))
    .filter((m): m is { key: keyof Vehicle["vehicle_dna"]; label: string; value: number } =>
      typeof m.value === "number",
    );
}

export const theftBandLabels: Record<string, string> = {
  low: "Basso",
  medium: "Medio",
  high: "Alto",
  very_high: "Molto Alto",
};
