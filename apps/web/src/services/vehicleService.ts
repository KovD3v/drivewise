/**
 * DriveWise data layer — unica sorgente dati del frontend.
 *
 * Oggi legge il dataset locale `DriveWise Functional Coverage Dataset v1`
 * (30 veicoli: 12 auto, 8 moto, 10 scooter).
 * Domani le stesse firme potranno chiamare il Decision Engine / REST API
 * (es. getVehicleById -> GET /api/vehicles/:id) senza toccare i componenti:
 * tutte le funzioni sono già asincrone e restituiscono DTO serializzabili.
 */
import { fetchVehicles, fetchVehicle, isApiNotFoundError, type VehicleSummary, type VehicleDetail } from "@/api/drivewise";
import vehiclesJson from "@/data/drivewise/functional-v1/vehicles.json";
import theftReferenceJson from "@/data/drivewise/functional-v1/theft_reference_italy_2024.json";

export type VehicleTypeKey = "car" | "motorcycle" | "scooter";

export type Pricing = { new_price_estimate: number | null; currency: string | null };
export type Powertrain = { fuel?: string | null; engine_cc?: number | null };

/** Solo auto (vedi coverage_matrix.csv). */
export type CarDimensions = {
  length_mm?: number | null;
  width_with_mirrors_mm?: number | null;
  height_mm?: number | null;
  boot_liters?: number | null;
};

/** Solo moto. */
export type MotorcycleSpecific = {
  seat_height_mm?: number | null;
  wet_weight_kg?: number | null;
  recommended_experience?: string | null;
  passenger_comfort_score?: number | null;
  wind_protection_score?: number | null;
};

/** Solo scooter. */
export type ScooterSpecific = {
  wet_weight_kg?: number | null;
  underseat_storage_l?: number | null;
  urban_agility_score?: number | null;
  passenger_comfort_score?: number | null;
  helmet_storage_full_face?: boolean | null;
  ring_road_fit_score?: number | null;
};

/** safety / family / sport sono presenti solo sulle auto. */
export type VehicleDna = {
  reliability?: number | null;
  comfort?: number | null;
  technology?: number | null;
  city?: number | null;
  travel?: number | null;
  running_cost?: number | null;
  safety?: number | null;
  family?: number | null;
  sport?: number | null;
};

export type TheftRisk = {
  observed_thefts_italy_2024: number | null;
  recovery_rate_pct: number | null;
  observed_volume_band: string | null;
  /** Sempre null in v1: senza denominatore di circolante non è calcolabile. */
  normalized_theft_risk_index: number | null;
  normalized_risk_status: string | null;
  source: string | null;
  data_year: number | null;
};

export type Vehicle = {
  id: string;
  mock?: boolean;
  mockDetails?: boolean;
  vehicle_type: VehicleTypeKey;
  brand: string;
  model: string;
  category: string;
  pricing: Pricing;
  powertrain?: Powertrain;
  dimensions?: CarDimensions;
  motorcycle_specific?: MotorcycleSpecific;
  scooter_specific?: ScooterSpecific;
  vehicle_dna: VehicleDna;
  theft_risk: TheftRisk;
};

export type TheftReference = {
  scope: string;
  data_year: number;
  vehicle_thefts_total: number;
  two_wheel_thefts_total: number;
  two_wheel_recovery_rate_pct: number;
  top_regions_all_vehicles: Record<string, number>;
  top_regions_two_wheels: Record<string, number>;
  model_observed_counts: Record<string, number>;
  model_recovery_rates_pct: Record<string, number>;
  warning: string;
  source: string;
};

// ponytail: two-wheel catalog mock until the existing API supports those vehicle types.
const VEHICLES = (vehiclesJson as unknown as Vehicle[]).filter(v => v.vehicle_type !== "car").map(v => ({ ...v, mock: true }));
export const theftReference = theftReferenceJson as unknown as TheftReference;

export function fromApiVehicle(v: VehicleSummary | VehicleDetail): Vehicle {
  const spec = 'specs' in v ? v.specs[0] : undefined;
  return {
    id: v.id, vehicle_type: 'car', brand: v.make, model: v.model, category: v.body_style,
    pricing: { new_price_estimate: v.base_price_eur, currency: 'EUR' },
    powertrain: { fuel: v.fuel_type }, dimensions: { boot_liters: spec?.cargo_volume_liters },
    // ponytail: presentation-only mock metrics until the API exposes reliability data. Never used for ranking.
    mockDetails: true,
    vehicle_dna: { reliability: 72, comfort: 78, technology: 70, safety: 75 },
    theft_risk: { observed_thefts_italy_2024: null, recovery_rate_pct: null, observed_volume_band: null, normalized_theft_risk_index: null, normalized_risk_status: null, source: null, data_year: null },
  };
}

export type VehicleFilter = {
  vehicleType?: VehicleTypeKey | undefined;
  category?: string | undefined;
  maxPrice?: number | undefined;
  ids?: string[] | undefined;
};

export async function getVehicles(): Promise<Vehicle[]> {
  return [...await getVehiclesByType('car'), ...VEHICLES];
}
export async function getVehiclesByType(type: VehicleTypeKey): Promise<Vehicle[]> {
  if (type !== 'car') return VEHICLES.filter(v => v.vehicle_type === type);
  const result: Vehicle[] = [];
  for (let offset = 0; ; offset += 100) {
    const page = await fetchVehicles({ limit: 100, offset });
    result.push(...page.map(fromApiVehicle));
    if (page.length < 100) return result;
  }
}
export async function getVehicleById(id: string): Promise<Vehicle | null> {
  const mock = VEHICLES.find(v => v.id === id);
  if (mock) return mock;
  try { return fromApiVehicle(await fetchVehicle(id)); }
  catch (error) { if (isApiNotFoundError(error)) return null; throw error; }
}
export async function getVehiclesByIds(ids: string[]): Promise<Vehicle[]> {
  return (await Promise.all(ids.map(getVehicleById))).filter((v): v is Vehicle => v !== null);
}
export async function filterVehicles(criteria: VehicleFilter = {}): Promise<Vehicle[]> {
  const vehicles = criteria.vehicleType ? await getVehiclesByType(criteria.vehicleType) : await getVehicles();
  return vehicles.filter(v => (!criteria.category || v.category === criteria.category) &&
    (!criteria.ids || criteria.ids.includes(v.id)) &&
    (criteria.maxPrice === undefined || (v.pricing.new_price_estimate !== null && v.pricing.new_price_estimate <= criteria.maxPrice)));
}

export async function getCategories(type: VehicleTypeKey): Promise<string[]> {
  const list = await getVehiclesByType(type);
  return [...new Set(list.map((v) => v.category))].sort((a, b) => a.localeCompare(b, "it-IT"));
}

/** Regioni con più furti (reference Italia 2024) per il contesto territoriale. */
export function theftRegionsFor(type: VehicleTypeKey): Record<string, number> {
  return type === "car" ? theftReference.top_regions_all_vehicles : theftReference.top_regions_two_wheels;
}
