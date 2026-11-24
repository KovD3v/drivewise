
import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { DecisionVignette } from "./DecisionVignette";

/**
 * CTA finale della home, ispirata al blocco "Get started" di Keyvo.
 * Card verde acqua, puntini a mezzetinte che sfumano in basso a sinistra,
 * titolo a sinistra; vignetta animata + testo + due pulsanti a destra.
 */
export function FinalCta() {
  return (
    <section className="px-4 py-16 sm:px-6 md:py-24">
      <div className="relative mx-auto grid max-w-6xl items-center gap-8 overflow-hidden rounded-[28px] bg-primary px-6 py-11 text-[#0F172A] md:grid-cols-[1.1fr_1fr] md:gap-12 md:px-16 md:py-[72px]">
        {/* puntini a mezzetinte */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage: "radial-gradient(circle, rgba(15,23,42,.22) 1.3px, transparent 1.8px)",
            backgroundSize: "11px 11px",
            maskImage: "radial-gradient(ellipse 55% 75% at 0% 100%, #000 25%, transparent 75%)",
            WebkitMaskImage: "radial-gradient(ellipse 55% 75% at 0% 100%, #000 25%, transparent 75%)",
          }}
        />

        <div className="relative">
          <span className="inline-block rounded bg-[#E6F7F2] px-3 py-2 font-mono text-[13px] font-semibold uppercase leading-none tracking-[0.22em]">
            Inizia ora
          </span>
          <h2 className="mt-5 text-[clamp(2.25rem,4.2vw,3.5rem)] font-extrabold leading-[1.05] tracking-[-0.03em] text-balance">
            La tua prossima scelta parte da qui.
          </h2>
        </div>

        <div className="relative">
          <DecisionVignette className="block aspect-[5/3] w-full rounded-[18px] border-[1.5px] border-[#0F172A] bg-[#E6F7F2]" />
          <p className="my-5 max-w-md text-[17px] leading-relaxed">
            Rispondi a poche domande: in pochi minuti hai una classifica motivata dei veicoli più adatti a te, con punti
            di forza e compromessi.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/app/start"
              className="dw-focus-inverse btn-shine overflow-hidden inline-flex items-center gap-2.5 rounded-full bg-cta-ink px-6 py-4 font-medium text-focus-inverse transition-transform hover:-translate-y-0.5"
            >
              Inizia la scelta guidata <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              to="/app/me"
              className="inline-flex items-center rounded-full bg-white px-6 py-4 font-medium text-[#0F172A] transition-transform hover:-translate-y-0.5"
            >
              Vai a My DriveWise
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
