import { describe, expect, it } from "vitest";
import { homeExample } from "./home-example";

describe("valori dell'esempio Famiglia in città", () => {
  it("usa Decision Score 88", () => expect(homeExample.score).toBe(88));
  it("usa Confidence 76, distinta dallo score", () => {
    expect(homeExample.confidence).toBe(76);
    expect(Number(homeExample.confidence)).not.toBe(homeExample.score);
  });
  it("usa un budget di 35.000 euro", () => expect(homeExample.budget).toBe(35_000));
  it("usa un prezzo indicativo di 34.000 euro", () => expect(homeExample.price).toBe(34_000));
});