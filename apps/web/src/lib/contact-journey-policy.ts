import type { ContactReason } from "./contact-validation";

export type ContactTicketRow = { id: string; label: string; value: string };
export const CONTACT_STAMP_MS = 300;
export function maskContactEmail(email: string): string {
  const [local, domain] = email.trim().split("@");
  return local && domain ? `${local.slice(0, 1)}•••@${domain}` : "";
}
export function contactMessagePreview(message: string): string {
  const text = message.trim();
  return text.length > 60 ? `${text.slice(0, 60)}…` : text;
}
export function contactTicketRows(reason: ContactReason, values: Record<string, string>, collaboration: string, privacyType: string): ContactTicketRow[] {
  const row = (id: string, label: string) => ({ id, label, value: values[id]?.trim() ?? "" });
  return [
    { id: "reason", label: "Motivo", value: reason },
    row("name", "Da"),
    { id: "email", label: "Risposta a", value: maskContactEmail(values['email'] ?? "") },
    { id: "message", label: "Messaggio", value: contactMessagePreview(values['message'] ?? "") },
    ...(reason === "Partnership" ? [row("company", "Azienda"), row("siteUrl", "Sito"), { id: "collaboration", label: "Tipo di collaborazione", value: collaboration }] : []),
    ...(reason === "Stampa" ? [row("publication", "Testata"), row("deadline", "Scadenza")] : []),
    ...(reason === "Privacy e dati" ? [{ id: "privacyType", label: "Tipo di richiesta", value: privacyType }] : []),
    ...(reason === "Segnalazione di un problema" ? [row("location", "Pagina")] : []),
  ];
}
export function journeyRequiredFields(reason: ContactReason) {
  return ["name", "email", "message", ...(reason === "Partnership" ? ["company"] : reason === "Stampa" ? ["publication"] : [])];
}
export function journeyProgress(reason: ContactReason, validated: Record<string, string>, values: Record<string, string>) {
  const required = journeyRequiredFields(reason);
  return Math.round(required.filter((key) => validated[key] && validated[key] === values[key]?.trim()).length / required.length * 100);
}