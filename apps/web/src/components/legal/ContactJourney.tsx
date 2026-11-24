import { useEffect, useRef } from "react";
import { Check } from "lucide-react";
import { MotionPause } from "@/components/landing/MotionPause";
import type { ContactReason } from "@/lib/contact-validation";
import type { ContactTicketRow } from "@/lib/contact-journey-policy";

export type JourneyCard = { id: string; label: string; version: string };
export function ticketArrival(reason: ContactReason, due: string) {
  return reason === "Privacy e dati" ? "entro 30 giorni" : due ? new Intl.DateTimeFormat("it-IT", { weekday: "long", day: "numeric", month: "long", timeZone: "Europe/Rome" }).format(new Date(`${due}T12:00:00Z`)) : "48 ore lavorative";
}
type TicketProps = { rows: ContactTicketRow[]; arrival: string; cards?: JourneyCard[]; sent: boolean; code: string; compact?: boolean };
export function ContactTicket({ rows, arrival, cards = [], sent, code, compact = false }: TicketProps) {
  return <div className={`cj-ticket ${compact ? "cj-ticket-compact" : ""}`} aria-hidden="true">
    <div className="cj-ticket-header"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M4 16.5c4.5 0 6-11 8-11s3.5 11 8 11" /></svg><span>DriveWise · Richiesta</span></div>
    <dl className="cj-ticket-rows">
      {rows.filter(row => !compact || row.value).map((row, index) => {
        const card = cards.find(item => item.id === row.id);
        return <div className="cj-ticket-row" key={row.id}>
          <dt>{row.label}</dt><dd>{row.value || <span className="cj-empty">—</span>}</dd>
          {card && !compact && <span key={`${card.id}-${card.version}`} className={`cj-data-card cj-tone-${index % 5}`}><Check aria-hidden="true" /><span>{card.label}</span></span>}
        </div>;
      })}
    </dl>
    <p className="cj-due"><span>Risposta entro:</span> <strong>{arrival}</strong></p>
    <p className="cj-team">Ti risponde il team DriveWise</p>
    {sent && <div className="cj-confirmation"><span className="cj-stamp">RICEVUTA <Check /></span><span className="cj-code">{code}</span></div>}
  </div>;
}
export function ContactJourney({ reason, due, rows, cards, sent, code }: { reason: ContactReason; due: string; rows: ContactTicketRow[]; cards: JourneyCard[]; sent: boolean; code: string }) {
  const stage = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = stage.current;
    if (!el) return;
    const observer = new IntersectionObserver(([entry]) => el.classList.toggle("cj-outside", !entry?.isIntersecting), { threshold: 0 });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  const arrival = ticketArrival(reason, due);
  // Announce blur-validated information, not every keystroke in the visual preview.
  return <>
    <p className="sr-only" aria-live="polite" aria-atomic="true">La tua richiesta, in chiaro. Motivo: {reason}. Ti risponde il team DriveWise. Risposta entro: {arrival}. {rows.filter(row => row.id === "collaboration" || row.id === "privacyType").map(row => `${row.label}: ${row.value}. `).join("")}{cards.map(card => card.label).join(". ")}{sent ? `. Richiesta ricevuta. Codice ${code}` : ""}</p>
    <MotionPause className="cj-desktop mb-10">
      <div ref={stage} className={`cj-scene ${sent ? "cj-sent" : ""}`} aria-hidden="true">
        <h2 className="cj-heading">La tua richiesta, in chiaro</h2>
        <ContactTicket rows={rows} arrival={arrival} cards={cards} sent={sent} code={code} />
      </div>
    </MotionPause>
  </>;
}
