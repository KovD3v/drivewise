import { describe, expect, it } from "vitest";
import { answersFromText, chronologicalQuestions, experienceFromText, summarizeRequest, vehicleTypeFromText, wizardCompletion } from "./wizard-input";
import { answersToProfile, buildQuestions, isQuestionActive } from "./wizard-questions";

describe("richieste dalla home", () => {
  for (const text of ["per iniziare", "prima moto", "neopatentato", "principiante", "non ho mai guidato una moto"]) {
    it(`riconosce principiante: ${text}`, () => expect(experienceFromText(text)).toBe("beginner"));
  }
  for (const text of ["guido da anni", "Guido moto da anni", "ho già avuto moto", "ho la moto da 10 anni", "esperto", "HO GIA AVUTO MOTO", "guido la moto da 2 anni", "guido scooter da 3 anni", "ho già posseduto una moto"]) {
    it(`riconosce esperto: ${text}`, () => expect(experienceFromText(text)).toBe("experienced"));
  }
  for (const text of ["cerco una moto", "cerco una moto per andare al lavoro", "non sono esperto", "prima moto ma guido da anni", "guido moto da 1 anni", "ho la moto da 1 anni", "non guido moto da anni", "non ho già avuto moto"]) {
    it(`mantiene la domanda se ambiguo: ${text}`, () => expect(experienceFromText(text)).toBeNull());
  }
  it("non usa il possesso di un tipo diverso per dedurre esperienza", () => {
    expect(experienceFromText("Ho già avuto auto", "motorcycle")).toBeNull();
    expect(experienceFromText("Ho già avuto moto", "motorcycle")).toBe("experienced");
    expect(experienceFromText("Guido scooter da 10 anni", "motorcycle")).toBeNull();
  });
  for (const text of ["guido da anni", "Guido moto da anni", "ho già avuto moto", "ho la moto da 10 anni"]) {
    it(`salva esperto e salta la domanda: ${text}`, async () => {
      const questions = await buildQuestions("motorcycle");
      const answers = answersFromText(text, questions, "motorcycle");
      expect(answersToProfile("motorcycle", answers).experience).toBe("experienced");
      expect(questions.filter((q) => !(q.id in answers)).some((q) => q.id === "experience")).toBe(false);
    });
  }
  it("mantiene Esperienza fra i dati mancanti per una richiesta generica", async () => {
    const questions = await buildQuestions("motorcycle");
    const answers = answersFromText("cerco una moto per andare al lavoro", questions, "motorcycle");
    expect(answers['experience']).toBeUndefined();
    expect(questions.filter((q) => !(q.id in answers)).some((q) => q.id === "experience")).toBe(true);
  });
  it("salva l'esperienza nel profilo e rimuove la domanda da completare", async () => {
    const questions = await buildQuestions("motorcycle");
    const answers = answersFromText("Cerco una moto per iniziare", questions);
    expect(answersToProfile("motorcycle", answers).experience).toBe("beginner");
    expect(questions.filter((q) => !(q.id in answers)).some((q) => q.id === "experience")).toBe(false);
  });
  it("non completa il profilo mentre le domande sono in caricamento", () => {
    expect(wizardCompletion(true, [], {})).toBe(0);
  });
  it("completa il profilo solo dopo tutte le risposte", async () => {
    const questions = await buildQuestions("motorcycle");
    expect(wizardCompletion(true, questions, { category: "" })).toBeLessThan(100);
    const answers = Object.fromEntries(questions.map((q) => [q.id, "risposta"]));
    expect(wizardCompletion(true, questions, answers)).toBe(100);
  });
  it("mantiene le risposte in ordine cronologico sopra la domanda attiva e consuma il testo una sola volta", async () => {
    const questions = await buildQuestions("motorcycle");
    const result = chronologicalQuestions(questions, { freeText: "prima moto", rider_height_cm: "170", budgetMax: "8000", category: "" }, "usage", true);
    expect(result.map((q) => q.id)).toEqual(["rider_height_cm", "budgetMax", "category", "usage"]);
  });
  it("ricava altezza 1,70 m e salta la relativa domanda", async () => {
    const questions = await buildQuestions("motorcycle");
    const answers = answersFromText("Cerco la prima moto, sono alto 1,70 m", questions);
    expect(answersToProfile("motorcycle", answers).rider_height_cm).toBe(170);
    expect(questions.filter((q) => !(q.id in answers)).some((q) => q.id === "rider_height_cm")).toBe(false);
  });
  it("limita il riassunto a sei parole senza cambiare il testo originale", () => {
    const text = "Cerco una prima moto, sono alto 1,70 m, per andare al lavoro ogni giorno";
    expect(summarizeRequest(text).split(/\s+/).length).toBeLessThanOrEqual(6);
    expect(summarizeRequest(text)).not.toBe(text);
    expect(summarizeRequest(text)).toContain("1,70");
  });
  it("ricava Auto e salta la domanda del tipo", () => {
    expect(vehicleTypeFromText("Cerco un'auto affidabile sotto i 30.000 €")).toBe("car");
  });
  it("ricava Moto dal suggerimento", () => {
    expect(vehicleTypeFromText("Vorrei una moto per iniziare")).toBe("motorcycle");
  });
  it("ricava Scooter da testo libero", () => {
    expect(vehicleTypeFromText("Cerco uno scooter per la città")).toBe("scooter");
  });
  it("non decide fra tipi ambigui", () => {
    expect(vehicleTypeFromText("Auto o moto?")).toBeNull();
  });
  it("conserva la richiesta e usa il budget esplicito nel profilo", async () => {
    const text = "Cerco un'auto affidabile sotto i 30.000 €";
    const questions = await buildQuestions("car");
    const answers = answersFromText(text, questions);
    const profile = answersToProfile("car", answers);
    expect(profile.freeText).toBe(text);
    expect(profile.budgetMax).toBe(30_000);
    const remaining = questions.filter((q) => isQuestionActive(q, answers) && !(q.id in answers));
    expect(remaining.some((q) => q.id === "freeText")).toBe(false);
    expect(remaining.some((q) => q.id === "budgetMax")).toBe(false);
  });
});