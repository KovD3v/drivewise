import { expect, it } from "vitest";
import { contactMessagePreview, contactTicketRows, maskContactEmail, CONTACT_STAMP_MS, journeyProgress } from "./contact-journey-policy";
it("counts only valid completed mandatory fields and includes the company for partnerships", () => {
  const values = { name: "Andrea", email: "nome@example.com", message: "Una domanda completa", company: "Azienda" };
  expect(journeyProgress("Domanda generale", {}, values)).toBe(0);
  expect(journeyProgress("Domanda generale", values, values)).toBe(100);
  expect(journeyProgress("Partnership", { ...values, company: "" }, values)).toBe(75);
  expect(journeyProgress("Partnership", values, values)).toBe(100);
});
it("does not count a field changed after its last valid blur", () => {
  expect(journeyProgress("Domanda generale", { name: "Andrea" }, { name: "", email: "", message: "" })).toBe(0);
});
it("masks the reply email without claiming it was verified", () => {
  expect(maskContactEmail("mario@esempio.it")).toBe("m•••@esempio.it");
  expect(maskContactEmail("mario")).toBe("");
});
it("limits the message preview to the first 60 characters", () => {
  expect(contactMessagePreview("a".repeat(61))).toBe(`${"a".repeat(60)}…`);
  expect(contactMessagePreview("Una domanda")).toBe("Una domanda");
});
it("includes only extras for the selected reason", () => {
  const values = { name: "Mario Test", company: "Azienda", publication: "Testata" };
  expect(contactTicketRows("Partnership", values, "Collaborazione", "Accesso").map(r => r.id)).toEqual(["reason", "name", "email", "message", "company", "siteUrl", "collaboration"]);
  expect(contactTicketRows("Domanda generale", values, "Collaborazione", "Accesso").map(r => r.id)).toEqual(["reason", "name", "email", "message"]);
});
it("uses a 300 millisecond confirmation stamp before the receipt", () => {
  expect(CONTACT_STAMP_MS).toBe(300);
});