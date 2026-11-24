/**
 * Decision engine locale (v1).
 * Legge esclusivamente il dataset funzionale: nessun veicolo hardcoded.
 * Sostituibile in futuro dal Decision Engine Python mantenendo queste firme.
 */
import type { DecisionProfile } from "@/lib/decision-profile";
import {
  filterVehicles,
  type Vehicle,
  type VehicleTypeKey,
} from "@/services/vehicleService";

export type ScoredVehicle = {
  vehicle: Vehicle;
  score: number;
  why: string[];
  tradeoffs: string[];
};

const clamp = (n: number) => Math.max(0, Math.min(100, Math.round(n)));

const dnaWeightsByUsage: Record<string, Partial<Record<string, number>>> = {
  city: { city: 3, running_cost: 2 },
  commute: { running_cost: 3, reliability: 2 },
  travel: { travel: 3, comfort: 2 },
  touring: { travel: 3, comfort: 2 },
  ring_road: { travel: 2 },
  family: { family: 3, safety: 2, comfort: 1 },
};

function dnaAverage(v: Vehicle): number {
  const values = Object.values(v.vehicle_dna).filter((x): x is number => typeof x === "number");
  if (!values.length) return 50;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

/** Punteggio 0-100 di compatibilità profilo/veicolo. Solo dati presenti nel dataset. */
export function scoreVehicle(v: Vehicle, profile: DecisionProfile): ScoredVehicle {
  const why: string[] = [];
  const tradeoffs: string[] = [];

  let weighted = 0;
  let weightSum = 0;
  const add = (key: string, weight: number) => {
    const value = v.vehicle_dna[key as keyof typeof v.vehicle_dna];
    if (typeof value !== "number") return;
    weighted += value * weight;
    weightSum += weight;
  };

  (profile.priorities ?? []).forEach((key, index) => add(key, 4 - index));
  (profile.usage ?? []).forEach((u) => {
    const weights = dnaWeightsByUsage[u] ?? {};
    Object.entries(weights).forEach(([key, w]) => add(key, w ?? 1));
  });

  const base = weightSum > 0 ? weighted / weightSum : dnaAverage(v);
  let score = base;

  // Priorità soddisfatte -> motivazioni concrete
  (profile.priorities ?? []).forEach((key) => {
    const value = v.vehicle_dna[key as keyof typeof v.vehicle_dna];
    if (typeof value === "number" && value >= 80) why.push(`${labelOf(key)} ${value}/100`);
    if (typeof value === "number" && value < 60) tradeoffs.push(`${labelOf(key)} solo ${value}/100`);
  });

  // Budget
  const price = v.pricing.new_price_estimate;
  if (typeof profile.budgetMax === "number" && typeof price === "number") {
    if (price <= profile.budgetMax) {
      score += 4;
      why.push(`Rientra nel budget (${price.toLocaleString("it-IT")} €)`);
    } else {
      const over = (price - profile.budgetMax) / profile.budgetMax;
      score -= Math.min(30, over * 60);
      tradeoffs.push(`Sopra budget di ${Math.round(price - profile.budgetMax).toLocaleString("it-IT")} €`);
    }
  }

  if (profile.category && v.category === profile.category) {
    score += 5;
    why.push(`Categoria ${v.category} come richiesto`);
  }

  // Moto
  const m = v.motorcycle_specific;
  if (v.vehicle_type === "motorcycle" && m) {
    if (profile.experience && m.recommended_experience) {
      const fits = m.recommended_experience.includes(profile.experience) ||
        profile.experience.includes(m.recommended_experience) ||
        (profile.experience === "experienced" && m.recommended_experience !== "experienced");
      if (fits) {
        score += 6;
        why.push("Adatta al tuo livello di esperienza");
      } else {
        score -= 12;
        tradeoffs.push("Richiede più esperienza di quella dichiarata");
      }
    }
    if (profile.rider_height_cm && typeof m.seat_height_mm === "number") {
      const comfortableSeat = profile.rider_height_cm * 5 - 40; // mm, stima ergonomica
      if (m.seat_height_mm <= comfortableSeat) {
        score += 4;
        why.push(`Sella a ${m.seat_height_mm} mm, gestibile con la tua altezza`);
      } else {
        score -= Math.min(14, (m.seat_height_mm - comfortableSeat) / 6);
        tradeoffs.push(`Sella alta (${m.seat_height_mm} mm) per la tua altezza`);
      }
    }
    if (profile.passenger_frequent && typeof m.passenger_comfort_score === "number") {
      score += (m.passenger_comfort_score - 60) / 5;
      if (m.passenger_comfort_score >= 75) why.push("Buon comfort per il passeggero");
      else if (m.passenger_comfort_score < 60) tradeoffs.push("Comfort passeggero limitato");
    }
    if ((profile.usage ?? []).includes("touring") && typeof m.wind_protection_score === "number") {
      score += (m.wind_protection_score - 60) / 5;
      if (m.wind_protection_score >= 75) why.push("Protezione aerodinamica adeguata ai viaggi");
    }
    if (profile.experience === "beginner" && typeof m.wet_weight_kg === "number" && m.wet_weight_kg > 210) {
      score -= 8;
      tradeoffs.push(`Peso in ordine di marcia elevato (${m.wet_weight_kg} kg)`);
    }
  }

  // Scooter
  const s = v.scooter_specific;
  if (v.vehicle_type === "scooter" && s) {
    if (profile.helmet_storage_required) {
      if (s.helmet_storage_full_face) {
        score += 8;
        why.push("Sottosella da casco integrale");
      } else {
        score -= 12;
        tradeoffs.push("Il casco integrale non entra sotto la sella");
      }
    }
    if ((profile.usage ?? []).includes("ring_road") && typeof s.ring_road_fit_score === "number") {
      score += (s.ring_road_fit_score - 60) / 4;
      if (s.ring_road_fit_score >= 80) why.push("Adatto a tangenziale e superstrada");
      else if (s.ring_road_fit_score < 55) tradeoffs.push("Poco adatto ai percorsi extraurbani");
    }
    if ((profile.usage ?? []).includes("city") && typeof s.urban_agility_score === "number") {
      score += (s.urban_agility_score - 70) / 5;
    }
    if (profile.passenger_frequent && typeof s.passenger_comfort_score === "number") {
      score += (s.passenger_comfort_score - 60) / 6;
    }
  }

  // Auto
  if (v.vehicle_type === "car") {
    if (profile.family_profile === "family" && typeof v.vehicle_dna.family === "number") {
      score += (v.vehicle_dna.family - 65) / 4;
      if (v.vehicle_dna.family >= 85) why.push("Ottima attitudine familiare");
    }
    if (profile.garage_status === "known" && profile.garageDimensions && v.dimensions) {
      const fit = garageFit(v, profile);
      if (fit === "fits") {
        score += 4;
        why.push("Compatibile con le misure del tuo garage");
      } else if (fit === "tight") {
        tradeoffs.push("Entra in garage con margini ridotti");
      } else if (fit === "no") {
        score -= 20;
        tradeoffs.push("Non entra nel tuo garage");
      }
    }
  }

  // Rischio furto: solo dato osservato, mai probabilità.
  if ((profile.priorities ?? []).includes("theft_risk")) {
    const observed = v.theft_risk.observed_thefts_italy_2024;
    if (typeof observed === "number") {
      const band = v.theft_risk.observed_volume_band;
      const penalty = band === "very_high" ? 10 : band === "high" ? 7 : band === "medium" ? 4 : 2;
      score -= penalty;
      tradeoffs.push(`${observed.toLocaleString("it-IT")} furti osservati in Italia nel ${v.theft_risk.data_year}`);
    } else {
      why.push("Nessun volume di furti osservato nel dataset");
    }
  }

  // I bonus positivi vengono compressi in funzione della base: senza questo,
  // più veicoli con DNA diverso saturavano tutti a 100% (tipico caso Auto).
  if (score > base) score = base + (score - base) * ((100 - base) / 100);

  return { vehicle: v, score: clamp(score), why: why.slice(0, 4), tradeoffs: tradeoffs.slice(0, 3) };
}

export type GarageFitResult = "fits" | "tight" | "no" | "unknown";

export function garageFit(v: Vehicle, profile: DecisionProfile): GarageFitResult {
  if (profile.garage_status !== "known" || !profile.garageDimensions || !v.dimensions) return "unknown";
  const g = profile.garageDimensions;
  const toMm = (value?: string) => {
    const n = Number((value ?? "").replace(",", "."));
    return Number.isFinite(n) && n > 0 ? n * 10 : null;
  };
  const gl = toMm(g.length);
  const gw = toMm(g.width);
  const gh = toMm(g.height);
  const { length_mm: l, width_with_mirrors_mm: w, height_mm: h } = v.dimensions;
  if (!gl || !gw || !l || !w) return "unknown";
  const marginL = gl - l;
  const marginW = gw - w;
  const marginH = gh && h ? gh - h : 500;
  if (marginL < 0 || marginW < 0 || marginH < 0) return "no";
  if (marginL < 400 || marginW < 300 || marginH < 100) return "tight";
  return "fits";
}

function labelOf(key: string) {
  const labels: Record<string, string> = {
    reliability: "Affidabilità",
    comfort: "Comfort",
    technology: "Tecnologia",
    city: "Attitudine urbana",
    travel: "Attitudine ai viaggi",
    running_cost: "Economia di gestione",
    safety: "Sicurezza",
    family: "Praticità familiare",
    sport: "Sportività",
    theft_risk: "Rischio furto",
  };
  return labels[key] ?? key;
}

/** Ranking completo per un profilo. */
export async function rankVehicles(profile: DecisionProfile): Promise<ScoredVehicle[]> {
  const pool = await filterVehicles({ vehicleType: profile.vehicleType });
  return pool
    .map((v) => scoreVehicle(v, profile))
    .sort((a, b) => b.score - a.score || a.vehicle.id.localeCompare(b.vehicle.id));
}

export async function previewRanking(
  profile: DecisionProfile,
  limit = 3,
): Promise<ScoredVehicle[]> {
  return (await rankVehicles(profile)).slice(0, limit);
}

export function decisionConfidence(profile: DecisionProfile): number {
  const checks: boolean[] = [
    Boolean(profile.vehicleType),
    Boolean(profile.category),
    Boolean(profile.freeText),
    Boolean(profile.usage?.length),
    Boolean(profile.priorities?.length),
    profile.vehicleType === "car"
      ? Boolean(profile.garage_status)
      : profile.vehicleType === "motorcycle"
        ? Boolean(profile.experience)
        : profile.helmet_storage_required !== undefined,
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

export type { VehicleTypeKey };

/** Proiezione leggera usata dal pannello di anteprima del wizard. */
export type PreviewVehicle = {
  id: string;
  name: string;
  segment: string;
  score: number;
  vehicleType: VehicleTypeKey;
};

export function toPreview(s: ScoredVehicle): PreviewVehicle {
  const price = s.vehicle.pricing.new_price_estimate;
  return {
    id: s.vehicle.id,
    name: `${s.vehicle.brand} ${s.vehicle.model}`,
    segment: price
      ? `${s.vehicle.category} · ${Math.round(price).toLocaleString("it-IT")} €`
      : s.vehicle.category,
    score: s.score,
    vehicleType: s.vehicle.vehicle_type,
  };
}
