import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowLeft, ArrowRight, Check, Minus } from "lucide-react";
import { AppHeader } from "@/components/app/AppHeader";
import { ScoreCelebration } from "@/components/app/ScoreCelebration";
import { SaveAnalysisPrompt } from "@/components/app/SaveAnalysisPrompt";
import { DynamicSections } from "@/components/vehicle/DynamicSections";
import { ReliabilityPanel } from "@/components/vehicle/ReliabilityPanel";
import { SecurityRisk } from "@/components/vehicle/SecurityRisk";
import { VSection } from "@/components/vehicle/primitives";
import { rankVehicles, type ScoredVehicle } from "@/lib/decision-engine";
import {
  dnaLabels,
  usageLabels,
  vehicleTypeLabels,
  type DecisionProfile,
} from "@/lib/decision-profile";
import { loadState } from "@/lib/decision-state";
import { EASE } from "@/lib/motion";
import { buildReportSections } from "@/lib/report-sections";
import { useCountUp } from "@/lib/use-count-up";

const title = "Decision Report | DriveWise";
const description =
  "Il tuo Decision Report DriveWise: punteggio, motivazioni, compromessi e alternative calcolati sul tuo profilo.";

export const Route = createFileRoute("/app/report")({
  validateSearch: (search: Record<string, unknown>) => ({
    s: typeof search['s'] === "string" ? (search['s'] as string) : undefined,
  }),
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:type", content: "article" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: ReportPage,
  errorComponent: ReportUnavailable,
  notFoundComponent: ReportUnavailable,
});

function ReportUnavailable() {
  return (
    <div className="min-h-screen bg-background">
      <AppHeader label="Decision Report" maxWidth="max-w-[70rem]" />
      <main className="mx-auto w-full max-w-[46rem] px-6 py-24 text-center sm:px-8">
        <h1 className="font-heading text-[2rem] font-extrabold tracking-[-0.03em]">
          Nessun profilo decisionale attivo.
        </h1>
        <p className="mt-4 text-[0.95rem] text-muted-foreground">
          Completa la Scelta Guidata: il report viene calcolato sulle tue risposte.
        </p>
        <Link
          to="/app/start"
          className="mt-8 inline-flex h-12 items-center rounded-full bg-primary px-7 text-[0.95rem] font-medium text-primary-foreground transition-colors hover:bg-primary-hover"
        >
          Vai alla Scelta Guidata
        </Link>
      </main>
    </div>
  );
}

function ReportPage() {
  const { s } = Route.useSearch();
  const [profile, setProfile] = useState<DecisionProfile | null>(null);
  const [confidence, setConfidence] = useState(0);
  const [error, setError] = useState("");
  const [ranking, setRanking] = useState<ScoredVehicle[] | null>(null);

  useEffect(() => {
    let alive = true;
    let tries = 0;

    const run = () => {
      const state = loadState();
      // Se il wizard ha passato un sessionId, aspetta che lo stato scritto
      // corrisponda esattamente a quella sessione (mai dati stantii).
      if (!state || (s && state.sessionId !== s)) {
        if (s && tries < 40) {
          tries += 1;
          window.setTimeout(() => {
            if (alive) run();
          }, 50);
          return;
        }
        if (alive) setRanking([]);
        return;
      }
      setProfile(state.profile);
      setConfidence(state.decisionConfidence);
      void rankVehicles(state.profile).then((list) => {
        if (alive) setRanking(list);
      }).catch(e => { if (alive) { setError(e instanceof Error ? e.message : 'Report non disponibile.'); setRanking([]); } });
    };

    run();
    return () => {
      alive = false;
    };
  }, [s]);

  if (ranking === null) {
    return (
      <div className="min-h-screen bg-background">
        <AppHeader label="Decision Report" maxWidth="max-w-[70rem]" />
        <main className="mx-auto w-full max-w-[46rem] px-6 py-24 text-center sm:px-8">
          <p className="text-sm text-muted-foreground">Calcolo il tuo Decision Report…</p>
        </main>
      </div>
    );
  }

  if (error || (profile && ranking.length === 0)) return <div className="min-h-screen bg-background"><AppHeader label="Decision Report" /><main className="mx-auto max-w-2xl px-8 py-24"><h1 className="font-heading text-3xl">Report non disponibile</h1><p role="alert" className="mt-5">{error || 'Nessuna offerta verificata corrisponde al profilo.'}</p><Link to="/app/start" className="mt-6 inline-block underline">Rivedi la Scelta Guidata</Link></main></div>;
  if (!profile) return <ReportUnavailable />;

  return <ReportContent profile={profile} ranking={ranking} confidence={confidence} />;
}

function ReportContent({
  profile,
  ranking,
  confidence,
}: {
  profile: DecisionProfile;
  ranking: ScoredVehicle[];
  confidence: number;
}) {
  const reduce = useReducedMotion();
  const winner = ranking[0]!;
  const { s: sessionId } = Route.useSearch();
  const shownConfidence = useCountUp(confidence, reduce ? 0 : 1400, !!reduce);
  const [celebrated, setCelebrated] = useState(false);
  const alternatives = ranking.slice(1, 5);
  const sections = buildReportSections(winner.vehicle, profile);

  const chips = [
    vehicleTypeLabels[profile.vehicleType],
    profile.category,
    profile.budgetMax ? `Budget ${profile.budgetMax.toLocaleString("it-IT")} €` : null,
    ...(profile.usage ?? []).map((u) => usageLabels[u] ?? u),
    ...(profile.priorities ?? []).map((p) => dnaLabels[p] ?? p),
  ].filter((x): x is string => Boolean(x));

  return (
    <div className="min-h-screen bg-background">
      <AppHeader label="Decision Report" maxWidth="max-w-[70rem]" />
      {winner.vehicle.mock && <p className="mx-auto max-w-[70rem] px-8 pt-5 text-xs text-muted-foreground">Demo: catalogo e ranking simulati.</p>}
      <main className="mx-auto w-full max-w-[70rem] space-y-14 px-6 py-12 sm:px-8 lg:py-20">
        <motion.article
          initial={reduce ? { opacity: 1 } : { opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: EASE }}
          className="relative overflow-hidden rounded-[2.25rem] border border-border/70 bg-card p-8 shadow-[var(--shadow-object)] sm:p-12"
        >
          <motion.div
            aria-hidden
            className="pointer-events-none absolute -top-28 -right-20 size-64 rounded-full bg-primary/12 blur-3xl"
            animate={
              celebrated && !reduce ? { opacity: [1, 1.8, 1], scale: [1, 1.14, 1] } : {}
            }
            transition={{ duration: 0.9, ease: EASE }}
          />
          <div className="relative flex flex-col items-center text-center">
            <ScoreCelebration
              score={winner.score}
              onCelebrate={() => setCelebrated(true)}
              className="font-heading text-[5rem] leading-[0.9] font-extrabold tracking-[-0.05em] tabular-nums sm:text-[6.5rem]"
            />
            <p className="mt-4 text-[0.6875rem] tracking-[0.2em] text-muted-foreground uppercase">
              Decision Score · {winner.score}/100
            </p>
            <h1 className="font-heading mt-6 text-2xl font-semibold tracking-[-0.02em] sm:text-3xl">
              {winner.vehicle.brand} {winner.vehicle.model}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {winner.vehicle.category}
              {winner.vehicle.pricing.new_price_estimate
                ? ` · ${winner.vehicle.pricing.new_price_estimate.toLocaleString("it-IT")} €`
                : ""}
            </p>
            {winner.offer && <p className="mt-3 text-sm text-muted-foreground">{winner.offer.title} · {winner.offer.condition === 'new' ? 'Nuova' : 'Usata'} · {winner.offer.price_eur.toLocaleString('it-IT')} €{winner.offer.source_url && <> · <a href={winner.offer.source_url} target="_blank" rel="noopener noreferrer" className="underline">Vedi offerta</a></>}</p>}
            <p className="mt-3 text-sm text-muted-foreground">
              Decision Confidence {shownConfidence}%
            </p>
            {chips.length > 0 && (
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
            )}
          </div>

          <div className="relative mt-12 grid gap-8 border-t border-border/70 pt-10 sm:grid-cols-2">
            <div>
              <h2 className="text-sm font-semibold">Perché te lo consigliamo</h2>
              <ul className="mt-4 space-y-3">
                {winner.why.length ? (
                  winner.why.map((s) => (
                    <li key={s} className="flex gap-3 text-sm text-muted-foreground">
                      <Check className="mt-0.5 size-4 shrink-0 text-primary" />
                      {s}
                    </li>
                  ))
                ) : (
                  <li className="text-sm text-muted-foreground">
                    È il profilo tecnico più equilibrato fra quelli compatibili con la tua scelta.
                  </li>
                )}
              </ul>
            </div>
            <div>
              <h2 className="text-sm font-semibold">Compromessi</h2>
              <ul className="mt-4 space-y-3">
                {winner.tradeoffs.length ? (
                  winner.tradeoffs.map((s) => (
                    <li key={s} className="flex gap-3 text-sm text-muted-foreground">
                      <Minus className="mt-0.5 size-4 shrink-0 text-accent" />
                      {s}
                    </li>
                  ))
                ) : (
                  <li className="text-sm text-muted-foreground">
                    Nessun compromesso rilevante rispetto ai dati del tuo profilo.
                  </li>
                )}
              </ul>
            </div>
          </div>

          <div className="relative mt-12 flex flex-col gap-3 sm:flex-row">
            <Link
              to="/app/vehicle/$id"
              params={{ id: winner.vehicle.id }}
              className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-full bg-primary px-7 text-[0.95rem] font-medium text-primary-foreground shadow-[var(--shadow-soft)] transition-all duration-300 hover:bg-primary-hover sm:w-auto"
            >
              Apri la scheda {winner.vehicle.model}
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
        </motion.article>

        {sections.length > 0 && (
          <VSection
            title="Cosa cambia davvero per te"
            intro="Dati del catalogo e anteprime demo indicate nelle schede."
          >
            <DynamicSections sections={sections} />
          </VSection>
        )}

        <VSection title="Affidabilità" intro="Profilo tecnico del veicolo consigliato.">
          <ReliabilityPanel vehicle={winner.vehicle} />
        </VSection>

        <VSection
          title="Sicurezza e furti"
          intro="Anteprima del servizio di statistiche sui furti."
        >
          <SecurityRisk vehicle={winner.vehicle} />
        </VSection>

        {alternatives.length > 0 && (
          <VSection title="Alternative valutate" intro="Stesso profilo, punteggi diversi.">
            <ul className="grid w-full grid-cols-[minmax(0,1fr)] gap-3">
              {alternatives.map((a) => (
                <li key={a.vehicle.id} className="w-full min-w-0">
                  <Link
                    to="/app/vehicle/$id"
                    params={{ id: a.vehicle.id }}
                    className="flex w-full min-h-11 min-w-0 items-center justify-between gap-4 rounded-2xl border border-border/70 bg-card px-4 py-3.5 text-sm transition-colors hover:border-primary/40"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-foreground">
                        {a.vehicle.brand} {a.vehicle.model}
                      </span>
                      <span className="mt-0.5 block truncate text-[0.8rem] text-muted-foreground">
                        {a.why[0] ?? a.vehicle.category}
                      </span>
                    </span>
                    <span className="font-heading shrink-0 font-semibold tabular-nums">
                      {a.score}%
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </VSection>
        )}
      </main>

      <SaveAnalysisPrompt
        draft={{
          sessionId,
          vehicleId: winner.vehicle.id,
          brand: winner.vehicle.brand,
          model: winner.vehicle.model,
          category: winner.vehicle.category,
          vehicleType: profile.vehicleType,
          score: winner.score,
          confidence,
          tags: chips.slice(0, 6),
          profile,
        }}
      />
    </div>
  );
}
