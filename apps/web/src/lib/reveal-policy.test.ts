import { describe, expect, it } from "vitest";
import { CHAT_MESSAGE_INTERVAL_MS, REVEAL_DURATION_MS, REVEAL_OBSERVER_OPTIONS, revealImmediately, wordRevealDelay } from "./reveal-policy";

describe("reveal readability rules", () => {
  it("caps each reveal at 400ms", () => expect(REVEAL_DURATION_MS).toBeLessThanOrEqual(400));
  it("caps word gaps at 30ms and the whole title at 500ms", () => {
    for (const count of [1, 3, 10, 50]) {
      expect(wordRevealDelay(1, count)).toBeLessThanOrEqual(30);
      expect(wordRevealDelay(count - 1, count) + REVEAL_DURATION_MS).toBeLessThanOrEqual(500);
    }
  });
  it("observes at threshold zero and a ten-percent bottom margin", () => {
    expect(REVEAL_OBSERVER_OPTIONS).toEqual({ threshold: 0, rootMargin: "0px 0px -10% 0px" });
  });
  it("shows passed elements immediately", () => { expect(revealImmediately(-1, false, false)).toBe(true); expect(revealImmediately(100, false, false)).toBe(false); });
  it("shows hash destinations immediately", () => expect(revealImmediately(100, true, false)).toBe(true));
  it("shows reduced-motion content immediately", () => expect(revealImmediately(100, false, true)).toBe(true));
  it("caps chat message intervals at 600ms", () => expect(CHAT_MESSAGE_INTERVAL_MS).toBeLessThanOrEqual(600));
});