import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowLeft, ArrowRight, Check, Minus } from "lucide-react";
import { ScoreCelebration } from "@/components/app/ScoreCelebration";
import { EASE } from "@/lib/motion";
import { useCountUp } from "@/lib/use-count-up";
import VEHICLES from "@/data/drivewise/functional-v1/vehicles.json";

/** Esempio costruito dal dataset reale: nessun veicolo hardcoded. */
const showcase = (() => {
  const cars = VEHICLES.filter((v) => v.vehicle_type === "car");
  const avg = (v: (typeof cars)[number]) => {
    const values = Object.values(v.vehicle_dna).filter((x): x is number => typeof x === "number");
    return values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
  };
  const sorted = [...cars].sort((a, b) => avg(b) - avg(a));
  const hero = sorted[0]!;
  const dna = Object.entries(hero.vehicle_dna).filter(
    (e): e is [string, number] => typeof e[1] === "number",
  );
  const labels: Record<string, string> = {
    reliability: "Affidabilità elevata",
    running_cost: "Costi di gestione contenuti",
    comfort: "Comfort di riferimento",
    safety: "Sicurezza ai vertici del segmento",
    technology: "Dotazione tecnologica completa",
    family: "Spazio adeguato alla famiglia",
    city: "Agilità in città",
    travel: "Ottimo nei viaggi lunghi",
    sport: "Guida coinvolgente",
  };
  const weak: Record<string, string> = {
    reliability: "Affidabilità non al vertice del segmento",
    running_cost: "Costi di gestione sopra la media",
    comfort: "Comfort inferiore alle alternative premium",
    safety: "Dotazioni di sicurezza essenziali",
    technology: "Tecnologia di bordo essenziale",
    family: "Spazio per la famiglia limitato",
    city: "Meno agile nel traffico urbano",
    travel: "Meno adatta ai viaggi lunghi",
    sport: "Guida poco sportiva",
  };
  const sortedDna = [...dna].sort((a, b) => b[1] - a[1]);
  return {
    id: hero.id,
    brand: hero.brand,
    model: hero.model,
    name: `${hero.brand} ${hero.model}`,
    category: hero.category,
    price: hero.pricing?.new_price_estimate ?? null,
    score: Math.round(avg(hero)),
    strengths: sortedDna.slice(0, 3).map(([k]) => labels[k] ?? k),
    tradeoffs: sortedDna.slice(-2).map(([k]) => weak[k] ?? k),
  };
})();

const chips = [
  "Auto",
  showcase.category,
  "Budget 35.000 €",
  "Città",
  "Famiglia",
  "Affidabilità",
  "Sicurezza",
];

export function DecisionReport({ active = true }: { active?: boolean }) {
  const reduce = useReducedMotion();
  const [celebrated, setCelebrated] = useState(false);
  const confidence = useCountUp(active ? 91 : 0, reduce ? 0 : 1400, !!reduce);

  return (
    <article className="relative overflow-hidden rounded-[2.25rem] border border-border/70 bg-card p-8 shadow-[var(--shadow-object)] sm:p-12">
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -top-28 -right-20 size-64 rounded-full bg-primary/12 blur-3xl"
        animate={celebrated && !reduce ? { opacity: [1, 1.8, 1], scale: [1, 1.14, 1] } : {}}
        transition={{ duration: 0.9, ease: EASE }}
      />

      <div className="relative flex flex-col items-center text-center">
        {active ? (
          <ScoreCelebration
            score={showcase.score}
            onCelebrate={() => setCelebrated(true)}
            className="font-heading text-[5rem] leading-[0.9] font-extrabold tracking-[-0.05em] tabular-nums sm:text-[6.5rem]"
          />
        ) : (
          <p
            aria-hidden
            className="font-heading text-[5rem] leading-[0.9] font-extrabold tracking-[-0.05em] tabular-nums sm:text-[6.5rem]"
          >
            0
          </p>
        )}
        <p className="mt-4 text-[0.6875rem] tracking-[0.2em] text-muted-foreground uppercase">
          Decision Score · {showcase.score}/100
        </p>
        <h3 className="font-heading mt-6 text-2xl font-semibold tracking-[-0.02em] sm:text-3xl">
          {showcase.name}
        </h3>
        <p className="mt-2 text-sm text-muted-foreground">
          {showcase.category}
          {showcase.price ? ` · ${showcase.price.toLocaleString("it-IT")} €` : ""}
        </p>
        <p className="mt-3 text-sm text-muted-foreground">Decision Confidence {confidence}%</p>

        <ul className="mt-7 flex flex-wrap justify-center gap-2">
          {chips.map((c) => (
            <li
              key={c}
              className="rounded-full border border-border/70 bg-background px-3.5 py-1.5 text-[0.78rem] text-muted-foreground first-letter:uppercase"
            >
              {c}
            </li>
          ))}
        </ul>
      </div>

      <div className="relative mt-12 grid gap-8 border-t border-border/70 pt-10 sm:grid-cols-2">
        <div>
          <h4 className="text-sm font-semibold">Perché te la consigliamo</h4>
          <ul className="mt-4 space-y-3">
            {showcase.strengths.map((s) => (
              <li key={s} className="flex gap-3 text-sm text-muted-foreground">
                <Check className="mt-0.5 size-4 shrink-0 text-primary" />
                {s}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="text-sm font-semibold">Compromessi</h4>
          <ul className="mt-4 space-y-3">
            {showcase.tradeoffs.map((s) => (
              <li key={s} className="flex gap-3 text-sm text-muted-foreground">
                <Minus className="mt-0.5 size-4 shrink-0 text-accent" />
                {s}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="relative mt-12 flex flex-col gap-3 sm:flex-row">
        <Link
          to="/app/vehicle/$id"
          params={{ id: showcase.id }}
          className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-full bg-primary px-7 text-[0.95rem] font-medium text-primary-foreground shadow-[var(--shadow-soft)] transition-all duration-300 hover:bg-primary-hover sm:w-auto"
        >
          Apri la scheda {showcase.model}
          <ArrowRight className="size-4" />
        </Link>
        <Link
          to="/app/start"
          className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-full border border-border/70 bg-card px-7 text-[0.95rem] font-medium transition-colors duration-300 hover:border-primary/40 sm:w-auto"
        >
          <ArrowLeft className="size-4" />
          Rifai la Scelta Guidata
        </Link>
      </div>
    </article>
  );
}
