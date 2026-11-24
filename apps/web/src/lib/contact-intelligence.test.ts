import { describe, expect, it } from "vitest";
import { responseDate, suggestedFaqs, safeContactSource } from "./contact-intelligence";
describe("contatti intelligenti", () => {
  it("calcola due giorni lavorativi saltando il weekend", () => {
    expect(responseDate("Stampa", new Date("2026-11-20T16:00:00Z"))).toBe("2026-11-24");
    expect(responseDate("Domanda generale", new Date("2026-11-21T16:00:00Z"))).toBe("2026-11-24");
  });
  it("calcola 30 giorni di calendario per la privacy", () => {
    expect(responseDate("Privacy e dati", new Date("2026-11-21T16:00:00Z"))).toBe("2026-12-21");
  });
  it("cerca nelle domande FAQ solo oltre 20 caratteri e restituisce al massimo due risposte", () => {
    expect(suggestedFaqs("moto scooter")).toEqual([]);
    const results = suggestedFaqs("Vorrei capire se DriveWise vende veicoli e funziona per moto e scooter e su quali dati si basa l’analisi");
    expect(results).toHaveLength(2);
    expect(results.some((faq) => faq.q === "Su quali dati si basa l'analisi?")).toBe(true);
    expect(suggestedFaqs("Vorrei sapere se funziona anche per moto e scooter")[0]?.q).toBe("Funziona anche per moto e scooter?");
  });
  it("non suggerisce domande senza parole in comune", () => {
    expect(suggestedFaqs("Sto cercando un referente commerciale per collaborare")).toEqual([]);
  });
  it("accetta solo provenienze interne senza parametri privati", () => {
    expect(safeContactSource("https://other.com/")).toBe("");
    expect(safeContactSource("//other.com/")).toBe("");
    expect(safeContactSource("/app/start?q=testo")).toBe("/app/start");
  });
});