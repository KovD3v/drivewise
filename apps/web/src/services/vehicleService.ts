/**
 * DriveWise data layer: every vehicle comes from the API (ADR-008).
 * The mapper keeps only fields the API returns; a missing value stays null and
 * the screens hide it. Nothing here scores, estimates or fills a gap.
 */
import {
  fetchVehicle,
  fetchVehicles,
  isApiNotFoundError,
  type AdvisorMetricProvenance,
  type ListPrice,
  type SourceProvenance,
  type VehicleSummary,
} from "@/api/drivewise";
import type { Credit, ScalarBasis } from "@/components/vehicle/source-facts";

export type { Credit };

export type VehicleTypeKey = "car" | "motorcycle" | "scooter";

/** Base price of a legacy catalogue row. Never a list price and never an offer. */
export type Pricing = { new_price_estimate: number | null; currency: string | null };
export type Powertrain = { fuel?: string | null };

export type CarDimensions = {
  length_mm?: number | null;
  width_with_mirrors_mm?: number | null;
  height_mm?: number | null;
  boot_liters?: number | null;
};

export type TwoWheelFacts = {
  seat_height_mm: number | null;
  wet_weight_kg: number | null;
  fuel_tank_capacity_liters: number | null;
  underseat_storage_liters: number | null;
};

export type Consumption = {
  liquid_l_100km: number | null;
  liquid_basis: ScalarBasis;
  energy_kwh_100km: number | null;
  energy_basis: ScalarBasis;
};

export type Vehicle = {
  id: string;
  vehicle_type: VehicleTypeKey;
  brand: string;
  model: string;
  category: string;
  pricing: Pricing;
  /** Public list price of the shown version (ADR-015), when the catalogue has one. */
  list_price: ListPrice | null;
  powertrain: Powertrain;
  seats: number | null;
  dimensions: CarDimensions;
  consumption: Consumption;
  two_wheel: TwoWheelFacts | null;
  credits: Credit[];
};

// Catalog v2 leaves an unreviewed body style empty; show it, but never offer it as a filter.
const UNKNOWN_CATEGORY = "Categoria non indicata";

const EMPTY_CONSUMPTION: Consumption = {
  liquid_l_100km: null,
  liquid_basis: null,
  energy_kwh_100km: null,
  energy_basis: null,
};

type SpecInput = {
  cargo_volume_liters?: number | null;
  seats?: number | null;
  consumption_l_100km?: number | null;
  consumption_l_100km_basis?: ScalarBasis;
  energy_consumption_kwh_100km?: number | null;
  energy_consumption_kwh_100km_basis?: ScalarBasis;
  list_price?: ListPrice | null;
  provenance?: SourceProvenance[];
  dimensions?: { length_mm: number | null; height_mm: number | null };
  two_wheel?: TwoWheelFacts;
};

/** A list item, a detail or a ranked vehicle; detail and ranking add one spec. */
export type ApiVehicleInput = Omit<VehicleSummary, "vehicle_type"> & {
  vehicle_type?: VehicleSummary["vehicle_type"];
  provenance?: SourceProvenance[];
  specs?: SpecInput[];
};

/** Credits for every licensed source named by the facts a screen shows. */
type SourceRef = Pick<SourceProvenance | AdvisorMetricProvenance | ListPrice, "source_name" | "source_url" | "source_license">;

export function creditsFrom(sources: (SourceRef | null | undefined)[]): Credit[] {
  const byName = new Map<string, Credit>();
  for (const source of sources) {
    if (!source || byName.has(source.source_name)) continue;
    byName.set(source.source_name, {
      name: source.source_name,
      url: source.source_url || null,
      license: source.source_license,
    });
  }
  return [...byName.values()];
}

export function fromApiVehicle(v: ApiVehicleInput): Vehicle {
  const spec = v.specs?.[0];
  const twoWheel = spec?.two_wheel;
  const hasTwoWheelFact = twoWheel && Object.values(twoWheel).some((value) => value !== null);
  return {
    id: v.id,
    // Legacy rows without a type are the car catalogue the Advisor already ranks.
    vehicle_type: v.vehicle_type ?? "car",
    brand: v.make,
    model: v.model,
    category: v.body_style ?? UNKNOWN_CATEGORY,
    pricing: { new_price_estimate: v.base_price_eur, currency: "EUR" },
    list_price: spec?.list_price ?? null,
    powertrain: { fuel: v.fuel_type },
    seats: spec?.seats ?? null,
    dimensions: {
      boot_liters: spec?.cargo_volume_liters ?? null,
      length_mm: spec?.dimensions?.length_mm ?? null,
      height_mm: spec?.dimensions?.height_mm ?? null,
    },
    consumption: spec
      ? {
          liquid_l_100km: spec.consumption_l_100km ?? null,
          liquid_basis: spec.consumption_l_100km_basis ?? null,
          energy_kwh_100km: spec.energy_consumption_kwh_100km ?? null,
          energy_basis: spec.energy_consumption_kwh_100km_basis ?? null,
        }
      : EMPTY_CONSUMPTION,
    two_wheel: hasTwoWheelFact ? twoWheel : null,
    credits: creditsFrom([...(v.provenance ?? []), ...(spec?.provenance ?? []), spec?.list_price]),
  };
}

const PAGE = 100;

export async function getVehiclesByType(type: VehicleTypeKey): Promise<Vehicle[]> {
  const result: Vehicle[] = [];
  for (let offset = 0; ; offset += PAGE) {
    const page = await fetchVehicles({ vehicle_type: type, limit: PAGE, offset });
    // The API counts untyped legacy rows as cars; keep only what was asked for.
    result.push(...page.map(fromApiVehicle).filter((v) => v.vehicle_type === type));
    if (page.length < PAGE) return result;
  }
}

export async function getVehicleById(id: string): Promise<Vehicle | null> {
  try {
    return fromApiVehicle(await fetchVehicle(id));
  } catch (error) {
    if (isApiNotFoundError(error)) return null;
    throw error;
  }
}

export async function getVehiclesByIds(ids: string[]): Promise<Vehicle[]> {
  return (await Promise.all(ids.map(getVehicleById))).filter((v): v is Vehicle => v !== null);
}
