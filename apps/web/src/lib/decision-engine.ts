import { fetchGuidedDecision, type AdvisorOffer, type GuidedDecisionResponse } from '@/api/drivewise';
import type { DecisionProfile } from './decision-profile';
import { getVehiclesByType, fromApiVehicle, type Vehicle, type VehicleTypeKey } from '@/services/vehicleService';
export type ScoredVehicle = { vehicle: Vehicle; score: number; decisionStatus?: 'complete' | 'insufficient_data'; why: string[]; tradeoffs: string[]; offer?: AdvisorOffer };

export function guidedRanking(response: GuidedDecisionResponse): ScoredVehicle[] {
  const seen = new Set<string>();
  return response.previewRanking.groups.flatMap(g => g.items)
    .filter(item => { if (seen.has(item.vehicle.id)) return false; seen.add(item.vehicle.id); return true; })
    .map(item => ({ vehicle: fromApiVehicle({ ...item.vehicle, specs: [item.selected_spec] }), score: item.score,
      decisionStatus: item.decision_status ?? 'insufficient_data',
      offer: item.offer, why: item.positive_factors.map(f => f.message),
      tradeoffs: [...item.tradeoffs.map(f => f.message), ...response.previewRanking.assumptions, ...response.warnings,
        ...response.garageCompatibility.filter(g => g.vehicleId === item.vehicle.id && g.specId === item.selected_spec.id).map(g => g.message)] }));
}

export async function rankVehicles(profile: DecisionProfile): Promise<ScoredVehicle[]> {
  if (profile.vehicleType === 'car') {
    if (!profile.decisionId) return [];
    return guidedRanking(await fetchGuidedDecision(profile.decisionId));
  }
  // ponytail: fixed two-wheel preview scores, replace when the backend supports motorcycles/scooters.
  return (await getVehiclesByType(profile.vehicleType)).map((vehicle, index) => ({
    vehicle, score: Math.max(40, 85 - index * 3), why: ['Esempio dimostrativo: ranking simulato.'],
    tradeoffs: ['Dati e punteggi mock, non una raccomandazione.'],
  }));
}
export async function previewRanking(profile: DecisionProfile, limit = 3) { return (await rankVehicles(profile)).slice(0, limit); }
export function decisionConfidence(profile: DecisionProfile) {
  return Math.round([profile.category, profile.freeText, profile.usage?.length, profile.priorities?.length, profile.budgetMax].filter(Boolean).length / 5 * 100);
}
export type GarageFitResult = 'fits' | 'tight' | 'no' | 'unknown';
// Exact garage checks already belong to the Guided Decision API, never infer missing measurements here.
export function garageFit(_v: Vehicle, _profile: DecisionProfile): GarageFitResult { return 'unknown'; }
export type PreviewVehicle = { id: string; name: string; segment: string; score: number; decisionStatus?: ScoredVehicle['decisionStatus']; vehicleType: VehicleTypeKey };
export function toPreview(s: ScoredVehicle): PreviewVehicle {
  return { id: s.vehicle.id, name: `${s.vehicle.brand} ${s.vehicle.model}`, segment: s.vehicle.category,
    score: s.score, decisionStatus: s.decisionStatus, vehicleType: s.vehicle.vehicle_type };
}
export type { VehicleTypeKey };
