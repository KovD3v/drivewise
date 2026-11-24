import { describe, expect, it } from "vitest";
import { contactSchema, contactRequestSchema, contactPayload, contactSubmissionAllowed, remainingCharacterAnnouncement } from "./contact-validation";

const valid = { reason: "Domanda generale", name: "A", email: "nome@example.com", message: "0123456789" };
describe("regole del modulo contatti", () => {
  it("richiede l’azienda solo per partnership", () => {
    expect(contactRequestSchema.safeParse({ ...valid, reason: "Partnership" }).success).toBe(false);
    expect(contactRequestSchema.safeParse({ ...valid, reason: "Partnership", company: "DriveWise" }).success).toBe(true);
    expect(contactRequestSchema.safeParse(valid).success).toBe(true);
  });
  it("richiede la testata solo per stampa", () => {
    expect(contactRequestSchema.safeParse({ ...valid, reason: "Stampa" }).success).toBe(false);
    expect(contactRequestSchema.safeParse({ ...valid, reason: "Stampa", publication: "Giornale" }).success).toBe(true);
  });
  it("non invia allegati senza consenso e non invia dettagli di altri motivi", () => {
    const data = contactRequestSchema.parse({ ...valid, company: "Azienda precedente", technical: { browser: "Browser", device: "Mobile", page: "/contact" }, analysis: { vehicleId: "car", vehicleName: "Auto" } });
    expect(contactPayload(data)).not.toHaveProperty("technical");
    expect(contactPayload(data)).not.toHaveProperty("analysis");
    expect(contactPayload(data)).not.toHaveProperty("company");
  });
  it("invia gli allegati selezionati", () => {
    const data = contactRequestSchema.parse({ ...valid, reason: "Segnalazione di un problema", attachTechnical: true, technical: { browser: "Browser", device: "Mobile", page: "/contact" }, attachAnalysis: true, analysis: { vehicleId: "car", vehicleName: "Auto" } });
    expect(contactPayload(data)).toHaveProperty("technical.device", "Mobile");
    expect(contactPayload(data)).toHaveProperty("analysis.vehicleName", "Auto");
  });
  it("richiede il nome", () => {
    expect(contactSchema.safeParse({ ...valid, name: " " }).success).toBe(false);
    expect(contactSchema.safeParse(valid).success).toBe(true);
  });
  it("richiede un indirizzo email valido", () => {
    expect(contactSchema.safeParse({ ...valid, email: "" }).success).toBe(false);
    expect(contactSchema.safeParse({ ...valid, email: "non-valida" }).success).toBe(false);
  });
  it("richiede almeno 10 caratteri nel messaggio", () => {
    expect(contactSchema.safeParse({ ...valid, message: "123456789" }).success).toBe(false);
    expect(contactSchema.safeParse(valid).success).toBe(true);
  });
  it("limita il messaggio a 1000 caratteri", () => {
    expect(contactSchema.safeParse({ ...valid, message: "x".repeat(1000) }).success).toBe(true);
    expect(contactSchema.safeParse({ ...valid, message: "x".repeat(1001) }).success).toBe(false);
  });
  it("blocca un campo trappola compilato", () => {
    expect(contactSubmissionAllowed("bot")).toBe(false);
    expect(contactSubmissionAllowed("")).toBe(true);
  });
  it("annuncia solo quando restano meno di 100 caratteri", () => {
    expect(remainingCharacterAnnouncement(900)).toBe("");
    expect(remainingCharacterAnnouncement(901)).toBe("Caratteri disponibili: 99");
    expect(remainingCharacterAnnouncement(1000)).toBe("Caratteri disponibili: 0");
  });
});