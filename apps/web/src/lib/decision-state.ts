/** Persistenza locale della sessione di Scelta Guidata. */
import type { DecisionProfile } from "./decision-profile";
import type { Answers } from "./wizard-questions";

export type FlowStatus = "collecting" | "analysing" | "ready";

export type PersistedState = {
  sessionId: string;
  status: FlowStatus;
  currentStep: string;
  profile: DecisionProfile;
  answers: Answers;
  profileCompletion: number;
  decisionConfidence: number;
  /** Solo id: la fonte dei dati resta il dataset. */
  rankingIds: string[];
  updatedAt: number;
};

export const DECISION_STATE_KEY = "drivewise_decision_state";

export function saveState(state: PersistedState) {
  try {
    localStorage.setItem(DECISION_STATE_KEY, JSON.stringify(state));
  } catch {
    /* storage unavailable */
  }
}

export function loadState(): PersistedState | null {
  try {
    const raw = localStorage.getItem(DECISION_STATE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedState;
    if (!parsed?.profile?.vehicleType) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function clearState() {
  try {
    localStorage.removeItem(DECISION_STATE_KEY);
  } catch {
    /* storage unavailable */
  }
}
