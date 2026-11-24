import { CalendarDays, Check, Users } from "lucide-react";
import { contactTeams, responsePromise } from "@/lib/contact-intelligence";
import type { ContactReason } from "@/lib/contact-validation";

export function ContactPanel({ reason, due }: { reason: ContactReason; due: string }) {
  return <aside aria-labelledby="contact-understood" className="rounded-2xl border border-border/70 bg-card p-5 shadow-[var(--shadow-soft)] lg:sticky lg:top-28 lg:p-6">
    <h2 id="contact-understood" className="font-heading text-[0.95rem] font-semibold">Cosa abbiamo capito</h2>
    <dl className="mt-5 grid gap-5 sm:grid-cols-3 lg:grid-cols-1">
      <div><dt className="text-xs text-muted-foreground">Motivo scelto</dt><dd className="mt-2 inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/8 px-3 py-1.5 text-[0.8125rem] text-foreground"><Check className="size-3 shrink-0" aria-hidden />{reason}</dd></div>
      <div><dt className="flex items-center gap-2 text-xs text-muted-foreground"><Users className="size-4" aria-hidden />Chi ti risponderà</dt><dd className="mt-2 text-sm font-medium">{contactTeams[reason]}</dd></div>
      <div><dt className="flex items-center gap-2 text-xs text-muted-foreground"><CalendarDays className="size-4" aria-hidden />Risposta prevista</dt><dd className="mt-2 text-sm leading-relaxed">{due ? responsePromise(reason, due) : reason === "Privacy e dati" ? "Entro 30 giorni, di solito molto prima" : "Entro 48 ore lavorative"}</dd></div>
    </dl>
  </aside>;
}