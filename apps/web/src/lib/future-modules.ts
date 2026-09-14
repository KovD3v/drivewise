/**
 * Aggancio architetturale per le sezioni future del report.
 * NON implementate: nessuna UI, solo firme e tipi pronti per il Decision Engine.
 * Quando i dati saranno disponibili basterà implementare queste funzioni
 * (o puntarle a un endpoint REST) e montare i componenti corrispondenti.
 */
import type { Vehicle } from "@/services/vehicleService";

export type Recall = { year: number; component: string; severity: string; status: string };
export type KnownIssue = { title: string; severity: string; frequency?: string };
export type InsuranceCost = { yearly_estimate: number; currency: string; profile?: string };
export type MaintenanceCost = { yearly_estimate: number; service_interval_km?: number };
export type Depreciation = { value_3y_estimate: number; value_5y_estimate: number };
export type UsedValue = { price_estimate: number; currency: string; sample_size?: number };

export type FutureVehicleModules = {
  recalls: Recall[] | null;
  knownIssues: KnownIssue[] | null;
  insurance: InsuranceCost | null;
  maintenance: MaintenanceCost | null;
  depreciation: Depreciation | null;
  usedValue: UsedValue | null;
};

/** v1: il dataset funzionale non copre questi campi -> sempre null. */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function getFutureModules(_vehicle: Vehicle): Promise<FutureVehicleModules> {
  return {
    recalls: null,
    knownIssues: null,
    insurance: null,
    maintenance: null,
    depreciation: null,
    usedValue: null,
  };
}
