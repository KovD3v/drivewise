/** Rows for the side-by-side comparison: the same labels for both vehicles, NA when the catalogue has no value. */
import { basisLabel } from "@/components/vehicle/source-facts";
import { fuelLabel, mm2cm, NA } from "@/lib/vehicle-format";
import type { Vehicle } from "@/services/vehicleService";

const decimal = (n: number) => n.toLocaleString("it-IT", { maximumFractionDigits: 1 });
const maybe = (value: number | null | undefined, unit: string) => (typeof value === "number" ? `${decimal(value)} ${unit}` : NA);

export function consumptionText(v: Vehicle): string {
  const c = v.consumption;
  if (typeof c.liquid_l_100km === "number") return `${decimal(c.liquid_l_100km)} l/100 km (${basisLabel(c.liquid_basis)})`;
  if (typeof c.energy_kwh_100km === "number") return `${decimal(c.energy_kwh_100km)} kWh/100 km (${basisLabel(c.energy_basis)})`;
  return NA;
}

export function compareRows(v: Vehicle): { label: string; value: string }[] {
  const rows = [
    { label: "Alimentazione", value: fuelLabel(v.powertrain.fuel) },
    { label: "Consumo dichiarato", value: consumptionText(v) },
  ];
  if (v.vehicle_type === "car")
    return [
      ...rows,
      { label: "Posti", value: v.seats ? String(v.seats) : NA },
      { label: "Bagagliaio", value: maybe(v.dimensions.boot_liters, "l") },
      { label: "Lunghezza", value: mm2cm(v.dimensions.length_mm) ?? NA },
      { label: "Altezza", value: mm2cm(v.dimensions.height_mm) ?? NA },
    ];
  const t = v.two_wheel;
  return [
    ...rows,
    { label: "Altezza sella", value: maybe(t?.seat_height_mm, "mm") },
    { label: "Peso in ordine di marcia", value: maybe(t?.wet_weight_kg, "kg") },
    { label: "Serbatoio", value: maybe(t?.fuel_tank_capacity_liters, "l") },
    { label: "Sottosella", value: maybe(t?.underseat_storage_liters, "l") },
  ];
}
