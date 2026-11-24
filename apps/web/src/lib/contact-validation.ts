import { z } from "zod";

export const CONTACT_MESSAGE_LIMIT = 1000;
export const contactReasons = ["Domanda generale", "Partnership", "Stampa", "Privacy e dati", "Segnalazione di un problema"] as const;
export const collaborationTypes = ["Dati e integrazioni", "Media e contenuti", "Altro"] as const;
export const privacyTypes = ["Accesso ai miei dati", "Correzione", "Cancellazione", "Opposizione", "Portabilità"] as const;
export type ContactReason = typeof contactReasons[number];
export const contactSchema = z.object({
  reason: z.enum(contactReasons),
  name: z.string().trim().min(1, "Inserisci il tuo nome").max(100, "Massimo 100 caratteri"),
  email: z.string().trim().email("Inserisci un indirizzo email valido").max(255, "Massimo 255 caratteri"),
  message: z.string().trim().min(10, "Scrivi almeno 10 caratteri").max(CONTACT_MESSAGE_LIMIT, "Massimo 1000 caratteri"),
});

const detail = z.string().trim().max(200, "Massimo 200 caratteri").default("");
export const contactDetailSchema = contactSchema.extend({
  company: detail,
  siteUrl: z.string().trim().max(500, "Massimo 500 caratteri").default(""),
  collaboration: z.enum(collaborationTypes).default("Dati e integrazioni"),
  publication: detail,
  deadline: z.string().max(10).default(""),
  privacyType: z.enum(privacyTypes).default("Accesso ai miei dati"),
  location: z.string().trim().max(500, "Massimo 500 caratteri").default(""),
});
export const analysisAttachmentSchema = z.object({
  vehicleId: z.string().max(100),
  vehicleName: z.string().min(1).max(200),
  score: z.number().min(0).max(100).optional(),
  confidence: z.number().min(0).max(100).optional(),
});
export type AnalysisAttachment = z.infer<typeof analysisAttachmentSchema>;
export const contactRequestSchema = contactDetailSchema.extend({
  website: z.string().max(500).default(""),
  attachTechnical: z.boolean().default(false),
  technical: z.object({ browser: z.string().max(500), device: z.string().max(100), page: z.string().max(500) }).optional(),
  attachAnalysis: z.boolean().default(false),
  analysis: analysisAttachmentSchema.optional(),
}).superRefine((data, ctx) => {
  if (data.reason === "Partnership") {
    if (!data.company) ctx.addIssue({ code: "custom", path: ["company"], message: "Inserisci il nome dell’azienda" });
    if (data.siteUrl) {
      const url = z.string().url().safeParse(data.siteUrl);
      if (!url.success || !/^https?:\/\//i.test(data.siteUrl)) ctx.addIssue({ code: "custom", path: ["siteUrl"], message: "Inserisci un sito web valido (https://…)" });
    }
  }
  if (data.reason === "Stampa") {
    if (!data.publication) ctx.addIssue({ code: "custom", path: ["publication"], message: "Inserisci il nome della testata" });
    if (data.deadline && (!/^\d{4}-\d{2}-\d{2}$/.test(data.deadline) || Number.isNaN(Date.parse(data.deadline)) || new Date(data.deadline).toISOString().slice(0, 10) !== data.deadline)) ctx.addIssue({ code: "custom", path: ["deadline"], message: "Inserisci una data valida" });
  }
});
export type ContactRequest = z.infer<typeof contactRequestSchema>;
export function contactPayload(data: ContactRequest) {
  return {
    reason: data.reason, name: data.name, email: data.email, message: data.message,
    ...(data.reason === "Partnership" ? { company: data.company, siteUrl: data.siteUrl, collaboration: data.collaboration } : {}),
    ...(data.reason === "Stampa" ? { publication: data.publication, deadline: data.deadline } : {}),
    ...(data.reason === "Privacy e dati" ? { privacyType: data.privacyType } : {}),
    ...(data.reason === "Segnalazione di un problema" ? { location: data.location, ...(data.attachTechnical && data.technical ? { technical: data.technical } : {}) } : {}),
    ...(data.attachAnalysis && data.analysis ? { analysis: data.analysis } : {}),
  };
}

export type ContactField = "name" | "email" | "message" | "company" | "siteUrl" | "publication" | "deadline" | "location";
export const contactFields: ContactField[] = ["name", "email", "message"];
export function contactSubmissionAllowed(honeypot: string) {
  return honeypot.length === 0;
}
export function remainingCharacterAnnouncement(length: number) {
  const remaining = CONTACT_MESSAGE_LIMIT - length;
  return remaining < 100 ? `Caratteri disponibili: ${remaining}` : "";
}