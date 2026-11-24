/**
 * Filo della storia tra le vignette della home.
 * Capitolo 1 (WeightsVignette) pubblica il veicolo in cima alla classifica per il profilo attivo;
 * Capitolo 2 (LifecycleVignette) lo usa come protagonista della timeline di My DriveWise.
 */
export type StoryVehicle = "auto" | "moto" | "scooter";
export type StoryPick = { vehicle: StoryVehicle; score: number; profile: string };

let current: StoryPick = { vehicle: "auto", score: 88, profile: "Famiglia in città" };
const listeners = new Set<(p: StoryPick) => void>();

export function getStoryPick(): StoryPick {
  return current;
}

export function setStoryPick(next: StoryPick) {
  if (next.vehicle === current.vehicle && next.score === current.score && next.profile === current.profile) return;
  current = next;
  listeners.forEach((l) => l(current));
}

export function subscribeStoryPick(listener: (p: StoryPick) => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
