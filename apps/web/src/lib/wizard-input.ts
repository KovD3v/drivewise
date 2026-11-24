import type { VehicleTypeKey } from "@/services/vehicleService";

/** Infer only explicit information; ambiguous requests keep the type question. */
export function vehicleTypeFromText(text: string): VehicleTypeKey | null {
  const types: VehicleTypeKey[] = [];
  if (/\b(auto|automobile|vettura|suv|station wagon|monovolume)\b/i.test(text)) types.push("car");
  if (/\b(moto|motocicletta)\b/i.test(text)) types.push("motorcycle");
  if (/\bscooter\b/i.test(text)) types.push("scooter");
  return types.length === 1 ? types[0] ?? null : null;
}
