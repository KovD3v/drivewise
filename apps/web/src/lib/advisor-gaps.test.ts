import { expect, test } from "vitest";
import { describeAdvisorGaps } from "./advisor-gaps";

test("advisor gap codes become Italian lines, never raw codes", () => {
  const lines = describeAdvisorGaps(
    ["tco", "garage_fit", "request.garage", "reliability", "reliability_assessment", "module_error:KeyError"],
    ["issue_applicability"],
  );
  expect(lines).toEqual([
    "Dati mancanti nel catalogo: costo totale di possesso, compatibilità con il garage, affidabilità e un altro dato.",
    "Dati da aggiungere al tuo profilo: misure del garage.",
    "Verifiche non complete: difetti noti applicabili a questa versione.",
  ]);
  expect(lines.join(" ")).not.toMatch(/[a-z]+_[a-z]+|request\./);
  expect(describeAdvisorGaps([], [])).toEqual([]);
});
