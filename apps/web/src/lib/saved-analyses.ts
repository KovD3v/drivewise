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
export async function saveAnalysis(draft: AnalysisDraft, userId: string) {
  const key = `drivewise_mock_analyses_${userId}`;
  const rows: SavedAnalysis[] = JSON.parse(localStorage.getItem(key) ?? '[]');
  rows.unshift({ ...draft, id: crypto.randomUUID(), createdAt: new Date().toISOString() });
  localStorage.setItem(key, JSON.stringify(rows));
}
export async function listSavedAnalyses(): Promise<SavedAnalysis[]> {
  const user = readMockUser();
  return user ? JSON.parse(localStorage.getItem(`drivewise_mock_analyses_${user.id}`) ?? '[]') : [];
}
