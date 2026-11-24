export const REVEAL_DURATION_MS = 350;
export const REVEAL_OBSERVER_OPTIONS = { threshold: 0, rootMargin: "0px 0px -10% 0px" };
export const CHAT_MESSAGE_INTERVAL_MS = 500;
export function wordRevealDelay(index: number, count: number) {
  return index * Math.min(30, 150 / Math.max(1, count - 1));
}
export function revealImmediately(top: number, destination: boolean, reduced: boolean) {
  return top < 0 || destination || reduced;
}