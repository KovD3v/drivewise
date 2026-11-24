import { fetchGuidedDecision, type AdvisorOffer, type GuidedDecisionResponse } from '@/api/drivewise';
import type { DecisionProfile } from './decision-profile';
import { creditsFrom, fromApiVehicle, type Vehicle, type VehicleTypeKey } from '@/services/vehicleService';

// Advisor v3 ranks cars only (ADR-012). Motorcycles and scooters are a catalogue without a score.
export type ScoredVehicle = { vehicle: Vehicle; score: number; decisionStatus?: 'complete' | 'insufficient_data'; why: string[]; tradeoffs: string[]; offer?: AdvisorOffer | null };

export function guidedRanking(response: GuidedDecisionResponse): ScoredVehicle[] {
  const seen = new Set<string>();
  return response.previewRanking.groups.flatMap(g => g.items)
    .filter(item => { if (seen.has(item.vehicle.id)) return false; seen.add(item.vehicle.id); return true; })
    .map(item => {
      const vehicle = fromApiVehicle({ ...item.vehicle, vehicle_type: 'car', specs: [{ ...item.selected_spec, list_price: item.list_price }] });
      return {
        // The item's metric provenance names every source the score used.
        vehicle: { ...vehicle, credits: creditsFrom([...(item.provenance ?? []), item.list_price, ...(item.selected_spec.provenance ?? [])]) },
        score: item.score,
        decisionStatus: item.decision_status ?? 'insufficient_data',
        offer: item.offer, why: item.positive_factors.map(f => f.message),
        tradeoffs: [...item.tradeoffs.map(f => f.message), ...response.previewRanking.assumptions, ...response.warnings,
          ...response.garageCompatibility.filter(g => g.vehicleId === item.vehicle.id && g.specId === item.selected_spec.id).map(g => g.message)],
      };
    });
}

/** The decision confidence the Guided Decision API returns, in percent. */
export function guidedConfidence(response: GuidedDecisionResponse): number {
  return Math.round(response.decisionConfidence * 100);
}

export type DecisionReport = { ranking: ScoredVehicle[]; confidence: number | null };

/** Ranking and confidence of a stored guided decision; non-car profiles have neither. */
export async function loadDecisionReport(profile: DecisionProfile): Promise<DecisionReport> {
  if (profile.vehicleType !== 'car' || !profile.decisionId) return { ranking: [], confidence: null };
  const response = await fetchGuidedDecision(profile.decisionId);
  return { ranking: guidedRanking(response), confidence: guidedConfidence(response) };
}

export async function rankVehicles(profile: DecisionProfile): Promise<ScoredVehicle[]> {
  return (await loadDecisionReport(profile)).ranking;
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
