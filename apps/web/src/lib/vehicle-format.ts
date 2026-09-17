/** Formatter condivisi per il dataset funzionale v1. */
import type { Vehicle } from "@/services/vehicleService";

export const NA = "Informazione non disponibile";

export const euro = (n: number) => `€ ${Math.round(n).toLocaleString("it-IT")}`;

export const mm2cm = (mm?: number | null) => (typeof mm === "number" ? `${Math.round(mm / 10)} cm` : null);

export const vehicleName = (v: Vehicle) => `${v.brand} ${v.model}`;

export const typeLabel: Record<Vehicle["vehicle_type"], string> = {
  car: "Auto",
  motorcycle: "Moto",
  scooter: "Scooter",
};

export const fuelLabel = (f?: string | null) => {
  const k = (f ?? "").toLowerCase();
  if (!k) return NA;
  if (k === "electric") return "Elettrico";
  if (k === "mild_hybrid" || k === "mild hybrid") return "Mild hybrid";
  if (k === "full_hybrid" || k === "hybrid" || k === "full hybrid") return "Full hybrid";
  if (k === "plug_in_hybrid" || k === "phev" || k === "plug-in hybrid") return "Plug-in hybrid";
  if (k === "diesel") return "Diesel";
  if (k === "petrol" || k === "gasoline" || k === "benzina") return "Benzina";
  return f ?? NA;
};

export const isElectric = (v: Vehicle) => (v.powertrain?.fuel ?? "").toLowerCase().includes("electric");
