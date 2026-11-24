import { describe, expect, it } from "vitest";
import scenarios from "@/data/drivewise/functional-v1/decision_test_scenarios.json";
import { rankVehicles } from "@/lib/decision-engine";
import { buildReportSections } from "@/lib/report-sections";
import type { DecisionProfile } from "@/lib/decision-profile";
import { getVehicles, getVehiclesByType } from "@/services/vehicleService";

type Scenario = {
  id: string;
  vehicle_type: "car" | "motorcycle" | "scooter";
  profile: Record<string, unknown>;
  expected: Record<string, unknown>;
};

describe("dataset", () => {
  it("contiene 30 veicoli 12/8/10", async () => {
    expect((await getVehicles()).length).toBe(30);
    expect((await getVehiclesByType("car")).length).toBe(12);
    expect((await getVehiclesByType("motorcycle")).length).toBe(8);
    expect((await getVehiclesByType("scooter")).length).toBe(10);
  });
});

describe("scenari di accettazione", () => {
  for (const s of scenarios as Scenario[]) {
    it(s.id, async () => {
      const profile = { vehicleType: s.vehicle_type, ...s.profile } as DecisionProfile;
      if (profile.garage_status === "known")
        profile.garageDimensions = { length: "500", width: "280", height: "230" };
      const ranking = await rankVehicles(profile);
      expect(ranking.length).toBeGreaterThan(0);
      expect(ranking.every((r) => r.vehicle.vehicle_type === s.vehicle_type)).toBe(true);

      const sections = buildReportSections(ranking[0]!.vehicle, profile);
      const ids = sections.map((x) => x.id);

      if ("garage_section" in s.expected)
        expect(ids.includes("garage")).toBe(s.expected["garage_section"]);
      for (const want of (s.expected["report_sections"] as string[] | undefined) ?? [])
        expect(ids).toContain(want);
      if (s.expected["new_session_required"]) {
        // profilo vuoto: nessuna priorità -> nessun dato dichiarato
        expect(Object.keys(s.profile).length).toBe(0);
      }
      if (s.expected["profile_completion"] === 0) expect(profile.priorities).toBeUndefined();
    });
  }
});
