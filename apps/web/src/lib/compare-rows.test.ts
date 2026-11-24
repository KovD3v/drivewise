import { expect, test } from "vitest";
import carDetail from "@/test/fixtures/car-detail.synthetic.json";
import scooterDetail from "@/test/fixtures/scooter-detail.synthetic.json";
import type { VehicleDetail } from "@/api/drivewise";
import { fromApiVehicle } from "@/services/vehicleService";
import { compareRows, consumptionText } from "./compare-rows";
import { priceText } from "@/components/vehicle/PriceLine";
import { listPriceRows } from "@/components/vehicle/source-facts";

const car = fromApiVehicle(carDetail as VehicleDetail);
const scooter = fromApiVehicle(scooterDetail as VehicleDetail);

test("consumption names the basis the catalogue gives", () => {
  expect(consumptionText(car)).toMatch(/l\/100 km \(valore dichiarato dalla fonte\)$/);
  expect(consumptionText({ ...car, consumption: { ...car.consumption, liquid_basis: "interval_upper" } })).toContain("valore più alto dichiarato");
});

test("both vehicles of a comparison share the same row labels", () => {
  const other = { ...car, seats: null, dimensions: {} };
  expect(compareRows(other).map((r) => r.label)).toEqual(compareRows(car).map((r) => r.label));
  expect(compareRows(other).find((r) => r.label === "Posti")?.value).toBe("Informazione non disponibile");
  expect(compareRows(scooter).map((r) => r.label)).toContain("Altezza sella");
});

test("a list price reads as a list price with its date, never as an offer", () => {
  expect(car.list_price).not.toBeNull();
  const text = priceText(car)!;
  expect(text).toMatch(/^Prezzo di listino .* · listino valido dal /);
  expect(text).not.toMatch(/offerta/i);
  expect(listPriceRows(car.list_price!).map((r) => r.label)).toEqual(["Prezzo di listino", "Versione in listino", "Listino valido dal"]);
});

test("without a list price the base price stays an indication", () => {
  expect(priceText({ ...car, list_price: null, pricing: { new_price_estimate: 20000, currency: "EUR" } })).toBe("Prezzo indicativo del nuovo € 20.000");
  expect(priceText({ ...car, list_price: null, pricing: { new_price_estimate: null, currency: "EUR" } })).toBeNull();
});

test("credits carry the source link and licence", () => {
  expect(car.credits.length).toBeGreaterThan(0);
  expect(car.credits.every((c) => c.license && c.url?.startsWith("https://"))).toBe(true);
});
