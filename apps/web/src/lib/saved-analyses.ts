/** Salvataggio delle analisi (Decision Report) nel profilo My DriveWise. */
import { readMockUser } from "./mock-account";
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

// ponytail: saved reports stay in this browser until a user library API exists.
function readSaved(key: string): SavedAnalysis[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(key) ?? "[]");
    return Array.isArray(parsed) ? (parsed as SavedAnalysis[]) : [];
  } catch {
    // Corrupted or unavailable storage: start from an empty library instead of crashing the page.
    return [];
  }
}

export async function saveAnalysis(draft: AnalysisDraft, userId: string) {
  const key = `drivewise_mock_analyses_${userId}`;
  const rows = readSaved(key);
  rows.unshift({ ...draft, id: crypto.randomUUID(), createdAt: new Date().toISOString() });
  // A failed write throws on purpose: SaveAnalysisPrompt shows its error state instead of "saved".
  localStorage.setItem(key, JSON.stringify(rows));
}
export async function listSavedAnalyses(): Promise<SavedAnalysis[]> {
  const user = readMockUser();
  return user ? readSaved(`drivewise_mock_analyses_${user.id}`) : [];
}
