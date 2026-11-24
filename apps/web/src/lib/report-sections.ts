/**
 * Composizione dinamica delle sezioni del report per tipo veicolo.
 * Regola: solo dati restituiti dall'API, nessuna sezione se il dato è assente
 * (mai card vuote) e nessun indice o costo calcolato nel sito.
 */
import { withBasis } from "@/components/vehicle/source-facts";
import { garageFit, type GarageFitResult } from "@/lib/decision-engine";
import type { DecisionProfile } from "@/lib/decision-profile";
import { fuelLabel } from "@/lib/vehicle-format";
import type { Vehicle } from "@/services/vehicleService";

export type ReportSectionId =
  | "boot"
  | "seats"
  | "garage"
  | "consumption"
  | "seat_height"
  | "wet_weight"
  | "fuel_tank"
  | "underseat";

export type ReportSection = {
  id: ReportSectionId;
  label: string;
  value: string;
  detail?: string | undefined;
  icon: string;
};

const garageVerdict: Record<Exclude<GarageFitResult, "unknown">, string> = {
  fits: "Entra comodamente",
  tight: "Entra con margini ridotti",
  no: "Non entra",
};

const decimal = (n: number) => n.toLocaleString("it-IT", { maximumFractionDigits: 1 });

export function buildReportSections(v: Vehicle, profile: DecisionProfile): ReportSection[] {
  const out: ReportSection[] = [];
  const num = (x: unknown): x is number => typeof x === "number";

  if (v.vehicle_type === "car") {
    const d = v.dimensions;
    if (num(d.boot_liters)) out.push({ id: "boot", label: "Bagagliaio", value: `${d.boot_liters} litri`, icon: "boot" });
    if (num(v.seats)) out.push({ id: "seats", label: "Posti", value: String(v.seats), icon: "family" });
    if (profile.garage_status === "known") {
      const fit = garageFit(v, profile);
      if (fit !== "unknown" && num(d.length_mm) && num(d.width_with_mirrors_mm))
        out.push({
          id: "garage",
          label: "Garage",
          value: garageVerdict[fit],
          detail: `${Math.round(d.length_mm / 10)} × ${Math.round(d.width_with_mirrors_mm / 10)} cm con specchietti`,
          icon: "garage",
        });
    }
    const c = v.consumption;
    if (num(c.liquid_l_100km))
      out.push({
        id: "consumption",
        label: "Consumo dichiarato",
        value: withBasis(`${decimal(c.liquid_l_100km)} l/100 km`, c.liquid_basis),
        detail: `${fuelLabel(v.powertrain.fuel)} · ciclo WLTP combinato`,
        icon: "cost",
      });
    else if (num(c.energy_kwh_100km))
      out.push({
        id: "consumption",
        label: "Consumo dichiarato",
        value: withBasis(`${decimal(c.energy_kwh_100km)} kWh/100 km`, c.energy_basis),
        detail: `${fuelLabel(v.powertrain.fuel)} · ciclo WLTP combinato`,
        icon: "cost",
      });
  }

  const t = v.two_wheel;
  if (v.vehicle_type !== "car" && t) {
    if (num(t.seat_height_mm))
      out.push({
        id: "seat_height",
        label: "Altezza sella",
        value: `${t.seat_height_mm} mm`,
        detail: profile.rider_height_cm ? `Altezza pilota ${profile.rider_height_cm} cm` : undefined,
        icon: "seat",
      });
    if (num(t.wet_weight_kg))
      out.push({ id: "wet_weight", label: "Peso in ordine di marcia", value: `${t.wet_weight_kg} kg`, icon: "weight" });
    if (num(t.underseat_storage_liters))
      out.push({ id: "underseat", label: "Sottosella", value: `${t.underseat_storage_liters} litri`, icon: "underseat" });
    if (num(t.fuel_tank_capacity_liters))
      out.push({ id: "fuel_tank", label: "Serbatoio", value: `${decimal(t.fuel_tank_capacity_liters)} litri`, icon: "tank" });
  }

  return out;
}
