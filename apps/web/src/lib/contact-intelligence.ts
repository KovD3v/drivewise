import { homeFaqs } from "./home-faqs";
import type { ContactReason } from "./contact-validation";
export const CONTACT_SOURCE_KEY = "drivewise_contact_source";

export const contactTeams: Record<ContactReason, string> = {
  "Domanda generale": "Team prodotto", Partnership: "Team partnership", Stampa: "Ufficio stampa",
  "Privacy e dati": "Responsabile privacy", "Segnalazione di un problema": "Supporto tecnico",
};

/** Two working days, Monday–Friday; privacy requests use 30 calendar days. */
export function responseDate(reason: ContactReason, now: Date): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Rome", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(now);
  const part = (name: string) => parts.find((p) => p.type === name)?.value ?? "";
  const date = new Date(`${part("year")}-${part("month")}-${part("day")}T12:00:00Z`);
  let days = reason === "Privacy e dati" ? 30 : 2;
  while (days > 0) {
    date.setUTCDate(date.getUTCDate() + 1);
    if (reason === "Privacy e dati" || (date.getUTCDay() !== 0 && date.getUTCDay() !== 6)) days--;
  }
  return date.toISOString().slice(0, 10);
}
export function responsePromise(reason: ContactReason, date: string): string {
  if (reason === "Privacy e dati") return "Ti rispondiamo entro 30 giorni, come previsto dal GDPR, di solito molto prima";
  const label = new Intl.DateTimeFormat("it-IT", { timeZone: "Europe/Rome", weekday: "long", day: "numeric", month: "long" }).format(new Date(`${date}T12:00:00Z`));
  return `Ti rispondiamo entro ${label}`;
}
const stopWords = new Set("anche avere cosa come della delle dello degli dove essere posso quando quanto quali quale questo quella sono sulla sulle tempo una uno per con che del dei gli una non nel nei alla alle vorrei sapere bisogno domanda informazioni".split(" "));
function words(text: string) {
  return new Set(text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().match(/[a-z0-9]+/g)?.filter((w) => w.length > 2 && !stopWords.has(w)) ?? []);
}
export function suggestedFaqs(message: string) {
  if (message.trim().length <= 20) return [];
  const tokens = words(message);
  return homeFaqs.map((faq) => ({ ...faq, score: [...words(faq.q)].filter((word) => tokens.has(word)).length }))
    .filter((faq) => faq.score > 0).sort((a, b) => b.score - a.score).slice(0, 2);
}
export function safeContactSource(value: unknown): string {
  return typeof value === "string" && value.length <= 500 && /^\/(?!\/)/.test(value) && !/[\\\r\n]/.test(value) ? value.split(/[?#]/)[0] ?? "" : "";
}