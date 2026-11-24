import { fetchGuidedDecision, type AdvisorOffer, type GuidedDecisionResponse } from '@/api/drivewise';
import type { DecisionProfile } from './decision-profile';
import { creditsFrom, fromApiVehicle, type Vehicle, type VehicleTypeKey } from '@/services/vehicleService';

// Advisor v3 ranks cars only (ADR-012). Motorcycles and scooters are a catalogue without a score.
/** `specId` is the version the Advisor scored; a vehicle can have several. */
export type ScoredVehicle = {
  vehicle: Vehicle; specId: string; score: number; decisionStatus?: 'complete' | 'insufficient_data'; why: string[]; tradeoffs: string[]; offer?: AdvisorOffer | null;
  /** The Advisor's own warnings on this vehicle, kept apart from the profile-wide tradeoffs. */
  warnings?: string[];
  /** Score factors the catalogue lacks data for on this vehicle. */
  missingFactors?: string[];
};

export function guidedRanking(response: GuidedDecisionResponse): ScoredVehicle[] {
  const seen = new Set<string>();
  return response.previewRanking.groups.flatMap(g => g.items)
    .filter(item => { if (seen.has(item.vehicle.id)) return false; seen.add(item.vehicle.id); return true; })
    .map(item => {
      const vehicle = fromApiVehicle({ ...item.vehicle, vehicle_type: 'car', specs: [{ ...item.selected_spec, list_price: item.list_price }] });
      return {
        // The item's metric provenance names every source the score used.
        vehicle: { ...vehicle, credits: creditsFrom([...(item.provenance ?? []), item.list_price, ...(item.selected_spec.provenance ?? [])]) },
        specId: item.selected_spec.id,
        score: item.score,
        decisionStatus: item.decision_status ?? 'insufficient_data',
        offer: item.offer, why: item.positive_factors.map(f => f.message),
        warnings: item.warnings ?? [], missingFactors: item.missing_factors ?? [],
        tradeoffs: [...item.tradeoffs.map(f => f.message), ...response.previewRanking.assumptions, ...response.warnings,
          ...response.garageCompatibility.filter(g => g.vehicleId === item.vehicle.id && g.specId === item.selected_spec.id).map(g => g.message)],
      };
    });
}

/** The decision confidence the Guided Decision API returns, in percent. */
export function guidedConfidence(response: GuidedDecisionResponse): number {
  return Math.round(response.decisionConfidence * 100);
}

/** The decision profile a Guided Decision response describes. */
export function guidedProfile(response: GuidedDecisionResponse): DecisionProfile {
  const value = (key: string) => response.decisionProfile[key]?.value;
  return { vehicleType: 'car', decisionId: response.decisionId,
    budgetMax: typeof value('budgetEur') === 'number' ? value('budgetEur') as number : undefined,
    category: typeof value('category') === 'string' ? value('category') as string : undefined,
    usage: typeof value('primaryUse') === 'string' ? [value('primaryUse') as string] : [],
    priorities: Array.isArray(value('priorities')) ? value('priorities') as string[] : [],
  };
}

export type DecisionReport = { ranking: ScoredVehicle[]; confidence: number | null };

/** Profile, ranking and confidence of one guided decision, read from the API alone (no local state). */
export async function loadGuidedDecisionReport(decisionId: string): Promise<DecisionReport & { profile: DecisionProfile; confidence: number }> {
  const response = await fetchGuidedDecision(decisionId);
  return { profile: guidedProfile(response), ranking: guidedRanking(response), confidence: guidedConfidence(response) };
}

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
