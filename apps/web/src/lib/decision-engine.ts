import { fetchGuidedDecision, type AdvisorOffer, type GarageCompatibility, type GuidedDecisionResponse } from '@/api/drivewise';
import type { DecisionProfile } from './decision-profile';
import { creditsFrom, fromApiVehicle, type Vehicle, type VehicleTypeKey } from '@/services/vehicleService';

// Advisor v3 ranks cars only (ADR-012). Motorcycles and scooters are a catalogue without a score.
/** `specId` is the version the Advisor scored; a vehicle can have several. */
export type VehicleCondition = 'new' | 'used';
export type ScoredVehicle = {
  vehicle: Vehicle; specId: string; score: number; decisionStatus?: 'complete' | 'insufficient_data'; why: string[]; tradeoffs: string[]; offer?: AdvisorOffer | null;
  /** The condition group the Advisor ranked this item in. */
  condition?: VehicleCondition;
  /** The Advisor's own warnings on this vehicle, kept apart from the profile-wide tradeoffs. */
  warnings?: string[];
  /** Score factors the catalogue lacks data for on this vehicle. */
  missingFactors?: string[];
};
/** One condition group of the Advisor ranking, in the API's own order. */
export type RankingGroup = { condition: VehicleCondition; items: ScoredVehicle[] };

type RecommendationItem = GuidedDecisionResponse['previewRanking']['groups'][number]['items'][number];

function toScoredVehicle(response: GuidedDecisionResponse, item: RecommendationItem, condition: VehicleCondition): ScoredVehicle {
  const vehicle = fromApiVehicle({ ...item.vehicle, vehicle_type: 'car', specs: [{ ...item.selected_spec, list_price: item.list_price }] });
  return {
    // The item's metric provenance names every source the score used.
    vehicle: { ...vehicle, credits: creditsFrom([...(item.provenance ?? []), item.list_price, ...(item.selected_spec.provenance ?? [])]) },
    specId: item.selected_spec.id,
    score: item.score,
    decisionStatus: item.decision_status ?? 'insufficient_data',
    condition,
    offer: item.offer, why: item.positive_factors.map(f => f.message),
    warnings: item.warnings ?? [], missingFactors: item.missing_factors ?? [],
    tradeoffs: [...item.tradeoffs.map(f => f.message), ...response.previewRanking.assumptions, ...response.warnings,
      ...response.garageCompatibility.filter(g => g.vehicleId === item.vehicle.id && g.specId === item.selected_spec.id).map(g => g.message)],
  };
}

const itemKey = (item: ScoredVehicle) => `${item.vehicle.id}:${item.specId}`;

/**
 * The API's rank order across groups: complete assessments first, then the higher score.
 * These are the first two terms of the Advisor's `_stable_rank_key`; a provisional 90 never beats a complete 70.
 */
export function compareRank(a: ScoredVehicle, b: ScoredVehicle): number {
  const status = (item: ScoredVehicle) => (item.decisionStatus === 'complete' ? 0 : 1);
  return status(a) - status(b) || b.score - a.score;
}

/**
 * The Advisor ranks new and used cars in separate groups. Each group keeps its own order, and one
 * vehicle version appears once per group, so a used offer is never hidden behind the same car new.
 */
export function guidedRankingGroups(response: GuidedDecisionResponse): RankingGroup[] {
  return response.previewRanking.groups.flatMap(group => {
    const seen = new Set<string>();
    const items = group.items.map(item => toScoredVehicle(response, item, group.condition))
      .filter(item => { const key = itemKey(item); if (seen.has(key)) return false; seen.add(key); return true; });
    return items.length ? [{ condition: group.condition, items }] : [];
  });
}

/** The group whose best item ranks highest; on a tie the API's group order (new first) wins. */
export function topRankingGroup(groups: RankingGroup[]): RankingGroup | undefined {
  return groups.reduce<RankingGroup | undefined>((best, group) => (!best || compareRank(group.items[0]!, best.items[0]!) < 0 ? group : best), undefined);
}

/**
 * Every group merged in rank order, for views that show one list (preview, vehicle page).
 * A version ranked in both groups keeps its better-ranked entry.
 */
export function guidedRanking(response: GuidedDecisionResponse): ScoredVehicle[] {
  const seen = new Set<string>();
  // Array.prototype.sort is stable: ties keep the API order, within and across groups.
  return guidedRankingGroups(response).flatMap(group => group.items).sort(compareRank)
    .filter(item => { const key = itemKey(item); if (seen.has(key)) return false; seen.add(key); return true; });
}

/** The decision confidence the Guided Decision API returns, in percent. */
export function guidedConfidence(response: GuidedDecisionResponse): number {
  return Math.round(response.decisionConfidence * 100);
}

/** The decision profile a Guided Decision response describes. */
export function guidedProfile(response: GuidedDecisionResponse): DecisionProfile {
  const facts = response.decisionProfile;
  return { vehicleType: 'car', decisionId: response.decisionId,
    budgetMax: typeof facts.budgetEur?.value === 'number' ? facts.budgetEur.value : undefined,
    category: typeof facts.category?.value === 'string' ? facts.category.value : undefined,
    usage: typeof facts.primaryUse?.value === 'string' ? [facts.primaryUse.value] : [],
    priorities: Array.isArray(facts.priorities?.value) ? [...facts.priorities.value] : [],
  };
}

export type DecisionReport = {
  ranking: ScoredVehicle[]; groups: RankingGroup[]; confidence: number | null;
  /** The API's garage verdict per vehicle version; empty when the profile has no garage. */
  garageCompatibility: GarageCompatibility[];
};

function reportFrom(response: GuidedDecisionResponse) {
  return { ranking: guidedRanking(response), groups: guidedRankingGroups(response), confidence: guidedConfidence(response), garageCompatibility: response.garageCompatibility };
}

/** Profile, ranking and confidence of one guided decision, read from the API alone (no local state). */
export async function loadGuidedDecisionReport(decisionId: string): Promise<DecisionReport & { profile: DecisionProfile; confidence: number }> {
  const response = await fetchGuidedDecision(decisionId);
  return { profile: guidedProfile(response), ...reportFrom(response) };
}

/** Ranking and confidence of a stored guided decision; non-car profiles have neither. */
export async function loadDecisionReport(profile: DecisionProfile): Promise<DecisionReport> {
  if (profile.vehicleType !== 'car' || !profile.decisionId) return { ranking: [], groups: [], confidence: null, garageCompatibility: [] };
  return reportFrom(await fetchGuidedDecision(profile.decisionId));
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
