/** Salvataggio delle analisi (Decision Report) nel profilo My DriveWise. */
import { supabase } from "@/integrations/supabase/client";
import type { DecisionProfile } from "./decision-profile";

export type AnalysisDraft = {
  sessionId?: string | undefined;
  vehicleId: string;
  brand: string;
  model: string;
  category?: string | undefined;
  vehicleType?: string | undefined;
  score: number;
  confidence: number;
  tags: string[];
  profile: DecisionProfile;
};

export type SavedAnalysis = AnalysisDraft & { id: string; createdAt: string };

const PENDING_KEY = "drivewise_pending_analysis";

export function setPendingAnalysis(draft: AnalysisDraft) {
  try {
    localStorage.setItem(PENDING_KEY, JSON.stringify(draft));
  } catch {
    /* storage unavailable */
  }
}

export function getPendingAnalysis(): AnalysisDraft | null {
  try {
    const raw = localStorage.getItem(PENDING_KEY);
    return raw ? (JSON.parse(raw) as AnalysisDraft) : null;
  } catch {
    return null;
  }
}

export function clearPendingAnalysis() {
  try {
    localStorage.removeItem(PENDING_KEY);
  } catch {
    /* storage unavailable */
  }
}

export async function saveAnalysis(draft: AnalysisDraft, userId: string) {
  const { error } = await supabase.from("saved_analyses").insert({
    user_id: userId,
    session_id: draft.sessionId ?? null,
    vehicle_id: draft.vehicleId,
    brand: draft.brand,
    model: draft.model,
    category: draft.category ?? null,
    vehicle_type: draft.vehicleType ?? null,
    score: draft.score,
    confidence: draft.confidence,
    tags: draft.tags,
    profile: JSON.parse(JSON.stringify(draft.profile)) as never,
  });
  if (error) throw new Error(error.message);
}

export async function listSavedAnalyses(): Promise<SavedAnalysis[]> {
  const { data, error } = await supabase
    .from("saved_analyses")
    .select("*")
    .order("created_at", { ascending: false });
  if (error || !data) return [];
  return data.map((r) => ({
    id: r.id,
    createdAt: r.created_at,
    sessionId: r.session_id ?? undefined,
    vehicleId: r.vehicle_id,
    brand: r.brand,
    model: r.model,
    category: r.category ?? undefined,
    vehicleType: r.vehicle_type ?? undefined,
    score: r.score,
    confidence: r.confidence,
    tags: r.tags ?? [],
    profile: (r.profile ?? {}) as unknown as DecisionProfile,
  }));
}