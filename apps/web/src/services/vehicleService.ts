/**
 * DriveWise data layer — unica sorgente dati del frontend.
 *
 * Oggi legge il dataset locale `DriveWise Functional Coverage Dataset v1`
 * (30 veicoli: 12 auto, 8 moto, 10 scooter).
 * Domani le stesse firme potranno chiamare il Decision Engine / REST API
 * (es. getVehicleById -> GET /api/vehicles/:id) senza toccare i componenti:
 * tutte le funzioni sono già asincrone e restituiscono DTO serializzabili.
 */
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

const VEHICLES = vehiclesJson as unknown as Vehicle[];
export const theftReference = theftReferenceJson as unknown as TheftReference;

export type VehicleFilter = {
  vehicleType?: VehicleTypeKey | undefined;
  category?: string | undefined;
  maxPrice?: number | undefined;
  ids?: string[] | undefined;
};

export async function getVehicles(): Promise<Vehicle[]> {
  return VEHICLES;
}

export async function getVehiclesByType(type: VehicleTypeKey): Promise<Vehicle[]> {
  return VEHICLES.filter((v) => v.vehicle_type === type);
}

export async function getVehicleById(id: string): Promise<Vehicle | null> {
  return VEHICLES.find((v) => v.id === id) ?? null;
}

export async function getVehiclesByIds(ids: string[]): Promise<Vehicle[]> {
  return ids.map((id) => VEHICLES.find((v) => v.id === id)).filter((v): v is Vehicle => Boolean(v));
}

export async function filterVehicles(criteria: VehicleFilter = {}): Promise<Vehicle[]> {
  return VEHICLES.filter((v) => {
    if (criteria.vehicleType && v.vehicle_type !== criteria.vehicleType) return false;
    if (criteria.category && v.category !== criteria.category) return false;
    if (criteria.ids && !criteria.ids.includes(v.id)) return false;
    if (
      typeof criteria.maxPrice === "number" &&
      typeof v.pricing.new_price_estimate === "number" &&
      v.pricing.new_price_estimate > criteria.maxPrice
    )
      return false;
    return true;
  });
}

export async function getCategories(type: VehicleTypeKey): Promise<string[]> {
  const list = await getVehiclesByType(type);
  return [...new Set(list.map((v) => v.category))].sort((a, b) => a.localeCompare(b, "it-IT"));
}

/** Regioni con più furti (reference Italia 2024) per il contesto territoriale. */
export function theftRegionsFor(type: VehicleTypeKey): Record<string, number> {
  return type === "car" ? theftReference.top_regions_all_vehicles : theftReference.top_regions_two_wheels;
}
