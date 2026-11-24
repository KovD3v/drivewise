import { describe, expect, it } from "vitest";
import { vehicleTypeFromText } from "./wizard-input";

describe("richieste dalla home", () => {
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
});
