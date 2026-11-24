import { Button } from "@/components/ui/button";
import { ArrowLeft, ArrowRight, Check, Minus } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { PastelCar } from "./PastelVehicles";
import { homeExample as showcase } from "@/lib/home-example";

const chips = [
  "Auto",
  showcase.category,
  `Budget ${showcase.budget.toLocaleString("it-IT")} €`,
  "Città",
  "Famiglia",
  "Affidabilità",
  "Costi",
];

export function DecisionReport({ active: _active = true }: { active?: boolean }) {
  return (
    <article className="relative overflow-hidden rounded-[2.25rem] border border-border/70 bg-card p-8 shadow-[var(--shadow-object)] sm:p-12">
      <div
        aria-hidden
        className="pointer-events-none absolute -top-28 -right-20 size-64 rounded-full bg-primary/12 blur-3xl"
      />

      <div className="relative flex flex-col items-center text-center">
        <p className="font-heading text-[5rem] leading-[0.9] font-extrabold tracking-[-0.05em] tabular-nums sm:text-[6.5rem]">
          {showcase.score}
        </p>
        <p className="mt-4 text-xs tracking-[0.2em] text-muted-foreground uppercase">
          Decision Score · {showcase.score}/100
        </p>
        <p className="mt-1 text-xs text-muted-foreground">Punteggio DriveWise</p>
        <div className="mt-7 w-full max-w-2xl overflow-hidden rounded-lg border border-border/70 bg-background">
          <div role="img" aria-label="Illustrazione della station wagon ibrida, vista laterale" className="flex aspect-[3/2] w-full items-center">
            <PastelCar />
          </div>
        </div>
        <p className="font-heading mt-6 text-2xl font-semibold tracking-[-0.02em] sm:text-3xl">
          {showcase.name}
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          {showcase.category}
          {` · circa ${showcase.price.toLocaleString("it-IT")} €`}
        </p>
        <p className="mt-3 text-sm text-muted-foreground">Affidabilità della scelta {showcase.confidence}%</p>
        <p className="mt-1 text-[13px] text-muted-foreground">
          quanto è completo il tuo profilo: più è alto, più il consiglio è solido
        </p>

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
          <p className="text-sm font-semibold">Perché te la consigliamo</p>
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
          <p className="text-sm font-semibold">Compromessi</p>
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

      <div className="relative mt-8 border-t border-border/70 pt-8">
        <p className="text-sm font-semibold">Alternative valutate</p>
        <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
          <li>2ª · SUV compatto ibrido · 84 — più alto, bagagliaio più piccolo</li>
          <li>3ª · Monovolume · 81 — più spazio, costi d'uso più alti</li>
        </ul>
      </div>

      <div className="relative mt-12 flex flex-col gap-3">
        <Button
          asChild
          className="h-auto min-h-14 w-full gap-3 whitespace-nowrap rounded-full px-6 py-3 text-[0.95rem] font-semibold leading-snug disabled:opacity-70"
        >
          <Link to="/app/start">
            <span className="min-w-0 text-center">Prova con il tuo profilo</span>
            <ArrowRight className="size-4 shrink-0" aria-hidden />
          </Link>
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled
          className="h-auto min-h-14 w-full gap-3 whitespace-nowrap rounded-full border-border/70 bg-card px-6 py-3 text-[0.95rem] font-semibold leading-snug disabled:opacity-70"
        >
          <ArrowLeft className="size-4 shrink-0" aria-hidden />
          <span className="min-w-0 text-center">Rifai la scelta guidata</span>
        </Button>
      </div>
    </article>
  );
}
