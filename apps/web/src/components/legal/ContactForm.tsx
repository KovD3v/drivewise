import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "@tanstack/react-router";
import { Check, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { ctaVariants } from "@/components/landing/CtaButton";
import { cn } from "@/lib/utils";
import { contactDetailSchema, contactRequestSchema, contactReasons, collaborationTypes, privacyTypes, contactSubmissionAllowed, remainingCharacterAnnouncement, type ContactField, type ContactReason } from "@/lib/contact-validation";
import { responseDate } from "@/lib/contact-intelligence";
import { CONTACT_STAMP_MS, contactTicketRows } from "@/lib/contact-journey-policy";
import { submitContactDemo } from "@/lib/contact-demo";
import { useContactContext } from "@/hooks/use-contact-context";
import { ContactChips, ContactInput, contactFieldClass } from "./ContactControls";
import { ContactJourney, ContactTicket, ticketArrival, type JourneyCard } from "./ContactJourney";
import { ContactSuggestions } from "./ContactSuggestions";

const emptyValues = { name: "", email: "", message: "", company: "", siteUrl: "", publication: "", deadline: "", location: "" };
type Receipt = { code: string; responseDate: string; reason: ContactReason; name: string; email: string; message: string };

export function ContactForm({ email, from = "", analysisId = "" }: { email: string; from?: string; analysisId?: string }) {
  const context = useContactContext(from, analysisId);
  const [reason, setReason] = useState<ContactReason>("Domanda generale");
  const [values, setValues] = useState(emptyValues);
  const [collaboration, setCollaboration] = useState<string>(collaborationTypes[0]);
  const [privacyType, setPrivacyType] = useState<string>(privacyTypes[0]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [honeypot, setHoneypot] = useState("");
  const [attachTechnical, setAttachTechnical] = useState(false);
  const [attachAnalysis, setAttachAnalysis] = useState(false);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [resolved, setResolved] = useState(false);
  const [pending, setPending] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [due, setDue] = useState("");
  const [validated, setValidated] = useState<Record<string, string>>({});
  const [departing, setDeparting] = useState(false);
  const [confirmedCode, setConfirmedCode] = useState("");
  const departureTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const receiptHeading = useRef<HTMLHeadingElement>(null);
  const resolvedHeading = useRef<HTMLHeadingElement>(null);
  const locationEdited = useRef(false);
  useEffect(() => () => { if (departureTimer.current) clearTimeout(departureTimer.current); }, []);

  useEffect(() => { setDue(responseDate(reason, new Date())); }, [reason]);
  useEffect(() => {
    if (!locationEdited.current) setValues((v) => ({ ...v, location: context.source }));
  }, [context.source]);
  useEffect(() => {
    if (receipt) receiptHeading.current?.focus();
    if (resolved) resolvedHeading.current?.focus();
  }, [receipt, resolved]);

  const requestData = () => ({ reason, ...values, collaboration, privacyType, website: honeypot,
    attachTechnical, ...(attachTechnical ? { technical: context.technical } : {}),
    attachAnalysis, ...(attachAnalysis && context.analysis ? { analysis: context.analysis } : {}),
  });
  function validateField(key: ContactField) {
    const data = requestData();
    const result = contactRequestSchema.safeParse(data);
    const issue = result.success ? undefined : result.error.issues.find((item) => item.path[0] === key);
    setErrors((current) => ({ ...current, [key]: issue?.message ?? "" }));
    setValidated((current) => ({ ...current, [key]: issue ? "" : values[key].trim() }));
  }
  function change(key: ContactField, value: string) {
    if (key === "location") locationEdited.current = true;
    setValues((v) => ({ ...v, [key]: value }));
  }
  const input = (key: ContactField, label: string, required = false, type = "text", help?: string) => <ContactInput key={key} name={key} label={label} required={required} type={type} value={values[key]} error={errors[key]} onChange={(value) => change(key, value)} onBlur={() => validateField(key)} {...(key === "name" || key === "email" ? { autoComplete: key } : {})} {...(help ? { help } : {})} />;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (pending || !contactSubmissionAllowed(honeypot)) return;
    const parsed = contactRequestSchema.safeParse(requestData());
    if (!parsed.success) {
      const next: Record<string, string> = {};
      for (const issue of parsed.error.issues) next[String(issue.path[0])] = issue.message;
      setErrors(next);
      const first = Array.from(formRef.current?.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>("input,textarea") ?? []).find((el) => next[el.name]);
      first?.focus();
      return;
    }
    setErrors({}); setSubmitError(""); setPending(true);
    try {
      const result = await submitContactDemo(parsed.data);
      if (!result.ok) setSubmitError(result.error);
      else {
        setConfirmedCode(result.receipt.code);
        setDeparting(true);
        const delay = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : CONTACT_STAMP_MS;
        departureTimer.current = setTimeout(() => { setReceipt(result.receipt); setPending(false); }, delay);
      }
    } catch { setSubmitError("Non è stato possibile inviare la richiesta. Riprova più tardi."); }
    finally { if (!departureTimer.current) setPending(false); }
  }
  function resolve() {
    setValues(emptyValues); setErrors({}); setHoneypot(""); setAttachAnalysis(false); setAttachTechnical(false); setResolved(true);
    setCollaboration(collaborationTypes[0]); setPrivacyType(privacyTypes[0]); setReason("Domanda generale");
    setValidated({}); setDeparting(false); setConfirmedCode("");
  }
  const rows = contactTicketRows(reason, values, collaboration, privacyType);
  const cards: JourneyCard[] = rows.flatMap(row => {
    const value = validated[row.id];
    if (!value || value !== values[row.id as ContactField]?.trim()) return [];
    return [{ id: row.id, label: `${row.label} · ${row.value}`, version: value }];
  });
  return <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,11fr)_minmax(0,9fr)] lg:gap-12">
    <div className="min-w-0 lg:sticky lg:top-24">
      <span className="inline-flex rounded-full border border-primary/30 bg-primary/10 px-3.5 py-1.5 text-xs font-semibold text-foreground">CONTATTI</span>
      <h1 className="mt-5 font-heading text-4xl font-extrabold leading-[1.12] sm:text-5xl">Hai una domanda? Parliamone.</h1>
      <p className="mt-4 text-base leading-relaxed text-muted-foreground">Rispondiamo entro 48 ore lavorative. Per le richieste privacy, entro 30 giorni.</p>
      <div className="cj-preview-wrap"><ContactJourney reason={receipt?.reason ?? reason} due={receipt?.responseDate ?? due} rows={rows} cards={cards} sent={departing} code={confirmedCode} /></div>
    </div>
    <div className="min-w-0">
    <p className="mb-6 text-base leading-relaxed text-muted-foreground">Ti risponde il team DriveWise.</p>
    <div className="min-w-0 rounded-3xl border border-border/70 bg-card p-7 shadow-[var(--shadow-soft)] sm:p-9">
      <p className="sr-only" aria-live="polite" aria-atomic="true">{receipt ? `Invio simulato. Codice ${receipt.code}` : resolved ? "Grazie, siamo felici di averti aiutato." : ""}</p>
      {receipt ? <section aria-labelledby="contact-receipt-title">
        <span className="grid size-12 place-items-center rounded-full bg-primary/12 text-brand-ink"><Check className="size-6" aria-hidden /></span>
        <h2 id="contact-receipt-title" ref={receiptHeading} tabIndex={-1} className="mt-5 font-heading text-2xl font-bold">Invio simulato</h2>
        <p className="mt-2 font-medium text-brand-ink">{receipt.code}</p>
        <p className="mt-2 text-sm text-muted-foreground">Demo: il messaggio non è stato inviato.</p>
        <dl className="mt-6 space-y-4 text-sm">
          {[["Motivo", receipt.reason], ["Nome", receipt.name], ["Email", receipt.email]].map(([label, value]) => <div key={label}><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1 break-words font-medium">{value}</dd></div>)}
          <div><dt className="text-xs text-muted-foreground">Messaggio</dt><dd className="mt-1 line-clamp-2 whitespace-pre-line break-words leading-relaxed">{receipt.message}</dd></div>
        </dl>
        <p className="mt-6 border-t border-border pt-5 text-sm leading-relaxed">Per contattarci davvero, scrivici a <a className="break-words font-medium underline underline-offset-4" href={`mailto:${email}`}>{email}</a>.</p>
        <div className="mt-7 flex flex-wrap gap-3"><Link to="/" className={ctaVariants({ variant: "ghost", size: "sm" })}>Torna alla home</Link><Link to="/app/start" className={ctaVariants({ variant: "primary", size: "sm" })}>Inizia la scelta guidata</Link></div>
      </section> : resolved ? <section>
        <h2 ref={resolvedHeading} tabIndex={-1} className="font-heading text-2xl font-bold">Grazie, siamo felici di averti aiutato.</h2>
        <p className="mt-3 text-sm text-muted-foreground">La tua domanda ha trovato risposta.</p>
        <Button variant="link" className="mt-5 px-0" onClick={() => setResolved(false)}>Scrivi un altro messaggio</Button>
      </section> : <form ref={formRef} onSubmit={handleSubmit} noValidate className="space-y-7">
        <p className="text-xs text-muted-foreground">Modulo demo: nessun messaggio verrà inviato o salvato.</p>
        <ContactChips name="reason" legend="Motivo del contatto" options={contactReasons} value={reason} onChange={(value) => { const parsed = contactDetailSchema.shape.reason.safeParse(value); if (parsed.success) { setReason(parsed.data); setErrors({}); } }} />
        <div hidden aria-hidden="true"><input name="website" tabIndex={-1} autoComplete="off" value={honeypot} onChange={(e) => setHoneypot(e.target.value)} /></div>
        <div className="grid gap-5 sm:grid-cols-2">
          {input("name", "Nome", true)}
          {input("email", "Email", true, "email", reason === "Privacy e dati" ? "Usa l’email del tuo account DriveWise." : undefined)}
        </div>
        {reason === "Partnership" && <div className="space-y-5">
          <div className="grid gap-5 sm:grid-cols-2">{input("company", "Azienda", true)}{input("siteUrl", "Sito web", false, "url")}</div>
          <ContactChips name="collaboration" legend="Tipo di collaborazione" options={collaborationTypes} value={collaboration} onChange={setCollaboration} />
          <p className="text-[0.8125rem] leading-relaxed text-muted-foreground">DriveWise è indipendente: nessuna partnership influenza le classifiche.</p>
        </div>}
        {reason === "Stampa" && <div className="grid gap-5 sm:grid-cols-2">{input("publication", "Testata", true)}{input("deadline", "Scadenza", false, "date")}</div>}
        {reason === "Privacy e dati" && <ContactChips name="privacyType" legend="Tipo di richiesta" options={privacyTypes} value={privacyType} onChange={setPrivacyType} />}
        {reason === "Segnalazione di un problema" && <div className="space-y-4">
          {input("location", "Dove è successo")}
          <div className="flex items-start gap-3"><Checkbox id="contact-technical" checked={attachTechnical} onCheckedChange={(value) => setAttachTechnical(value === true)} className="mt-3" /><label htmlFor="contact-technical" className="py-2 text-sm">Allega informazioni tecniche (browser, dispositivo, pagina)</label></div>
          <dl className="space-y-2 border-l-2 border-border pl-4 text-xs text-muted-foreground">
            <div><dt className="font-medium text-foreground">{attachTechnical ? "Informazioni che verranno allegate" : "Informazioni allegabili"}</dt></div>
            {Object.entries(context.technical).map(([key, value]) => <div key={key} className="break-words"><dt className="inline font-medium">{key === "browser" ? "Browser" : key === "device" ? "Dispositivo" : "Pagina"}: </dt><dd className="inline">{value}</dd></div>)}
          </dl>
        </div>}
        <div>
          <label htmlFor="contact-message" className="text-[0.8125rem] font-medium">Messaggio</label>
          <textarea id="contact-message" name="message" required minLength={10} maxLength={1000} rows={6} className={cn(contactFieldClass, "mt-2 resize-none")} placeholder="Raccontaci come possiamo aiutarti." value={values.message} onChange={(e) => change("message", e.target.value)} onBlur={() => validateField("message")} aria-invalid={Boolean(errors['message'])} aria-describedby={errors['message'] ? "contact-message-error contact-privacy" : "contact-privacy"} />
          <div className="mt-2 flex justify-between gap-3"><p id="contact-message-error" className="text-xs text-destructive">{errors['message'] ?? ""}</p><p aria-hidden="true" className="text-xs text-muted-foreground">{values.message.length}/1000</p></div>
          <p aria-live="polite" aria-atomic="true" className="sr-only">{remainingCharacterAnnouncement(values.message.length)}</p>
          <p id="contact-privacy" className="mt-3 text-[0.8125rem] leading-relaxed text-muted-foreground">Usiamo i tuoi dati solo per risponderti. <Link to="/privacy" className="text-foreground underline underline-offset-4">Leggi l’informativa privacy.</Link></p>
          <ContactSuggestions message={values.message} onResolved={resolve} />
        </div>
        {context.analysis && <div className="flex items-center justify-between gap-4 border-t border-border pt-4"><label htmlFor="contact-analysis" className="py-2 text-sm">Allega la mia analisi<span className="mt-1 block text-xs text-muted-foreground">{context.analysis.vehicleName}</span></label><Switch id="contact-analysis" checked={attachAnalysis} onCheckedChange={setAttachAnalysis} /></div>}
        {submitError && <p role="alert" className="text-sm text-destructive">{submitError}</p>}
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <Button disabled={pending} type="submit" className={cn(ctaVariants({ variant: "primary", size: "md" }), "contact-submit")}>{pending ? "Invio in corso…" : "Invia messaggio"}<Send className="size-4" aria-hidden="true" /></Button>
          <div className="cj-mobile"><ContactTicket rows={rows} arrival={ticketArrival(reason, due)} sent={departing} code={confirmedCode} compact /></div>
          <p className="text-[0.8125rem] text-muted-foreground">Preferisci scriverci via email? <a className="break-words text-foreground underline underline-offset-4" href={`mailto:${email}`}>{email}</a></p>
        </div>
      </form>}
    </div>
    </div>
  </div>;
}
