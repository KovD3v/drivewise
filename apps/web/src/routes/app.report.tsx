import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { motion, useReducedMotion } from "framer-motion";
import { AlertTriangle, ArrowLeft, ArrowRight, Check, Minus } from "lucide-react";
import { AppHeader } from "@/components/app/AppHeader";
import { ScoreCelebration } from "@/components/app/ScoreCelebration";
import { SaveAnalysisPrompt } from "@/components/app/SaveAnalysisPrompt";
import { DynamicSections } from "@/components/vehicle/DynamicSections";
import { VSection } from "@/components/vehicle/primitives";
import { PriceLine } from "@/components/vehicle/PriceLine";
import { ListPricePanel, SourceCredits } from "@/components/vehicle/source-facts";
import { loadDecisionReport, loadGuidedDecisionReport, topRankingGroup, type RankingGroup, type ScoredVehicle, type VehicleCondition } from "@/lib/decision-engine";
import {
  dnaLabels,
  usageLabels,
  vehicleTypeLabels,
  type DecisionProfile,
} from "@/lib/decision-profile";
import { clearState, loadState } from "@/lib/decision-state";
import { describeAdvisorGaps } from "@/lib/advisor-gaps";
import { safeHttpsUrl } from "@/lib/safe-url";
import { EASE } from "@/lib/motion";
import { buildReportSections } from "@/lib/report-sections";
import { useCountUp } from "@/lib/use-count-up";
import { Button } from "@/components/ui/button";
import { categoryLabel, categoryText } from "@/lib/category-labels";

const title = "Riepilogo della scelta | DriveWise";
const description =
  "Il tuo Riepilogo della scelta DriveWise: punteggio, motivazioni, compromessi e alternative calcolati sul tuo profilo.";

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
  notFoundComponent: ReportNotFound,
});

// TanStack splits each route slot into its own chunk; a slot function must not be referenced elsewhere.
function ReportNotFound() {
  return <ReportMissing />;
}

function ReportUnavailable() {
  return <ReportMissing />;
}

function ReportMissing() {
  return (
    <div className="min-h-screen bg-background">
      <AppHeader label="Riepilogo della scelta" maxWidth="max-w-[70rem]" />
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
  const [confidence, setConfidence] = useState<number | null>(null);
  const [error, setError] = useState("");
  // The Advisor's condition groups (new, used), each in its own rank order.
  const [ranking, setRanking] = useState<RankingGroup[] | null>(null);

  useEffect(() => {
    let alive = true;
    // A new decision id starts from a clean slate: no result or error of the previous one lingers.
    setError("");
    setRanking(null);
    setConfidence(null);
    setProfile(null);
    const fail = (e: unknown) => {
      if (!alive) return;
      setError(e instanceof Error ? e.message : "Report non disponibile.");
      setRanking([]);
    };

    if (s) {
      // The URL names the decision: the Guided Decision API alone describes it, so a shared or
      // reopened link works in any browser, with or without local state.
      void loadGuidedDecisionReport(s).then((report) => {
        if (!alive) return;
        setProfile(report.profile);
        setConfidence(report.confidence);
        setRanking(report.groups);
      }).catch(fail);
    } else {
      // Without ?s= the last decision saved in this browser is the only fallback.
      const state = loadState();
      if (!state) {
        setRanking([]);
      } else {
        setProfile(state.profile);
        // Ranking and confidence come from the Guided Decision API, never from local storage.
        void loadDecisionReport(state.profile).then((report) => {
          if (!alive) return;
          setConfidence(report.confidence);
          setRanking(report.groups);
        }).catch(fail);
      }
    }

    return () => {
      alive = false;
    };
  }, [s]);

  if (ranking === null) {
    return (
      <div className="min-h-screen bg-background">
        <AppHeader label="Riepilogo della scelta" maxWidth="max-w-[70rem]" />
        <main className="mx-auto w-full max-w-[46rem] px-6 py-24 text-center sm:px-8">
          <p className="text-sm text-muted-foreground">Calcolo il tuo Riepilogo della scelta…</p>
        </main>
      </div>
    );
  }

  if (error || (profile && ranking.length === 0)) return <div className="min-h-screen bg-background"><AppHeader label="Decision Report" /><main className="mx-auto max-w-2xl px-8 py-24"><h1 className="font-heading text-3xl">Report non disponibile</h1><p role="alert" className="mt-5">{error || 'Nessun veicolo del catalogo corrisponde al profilo.'}</p><Link to="/app/start" className="mt-6 inline-block underline">Rivedi la Scelta Guidata</Link></main></div>;
  // A ranking only exists for a guided car decision, which always carries the API confidence.
  if (!profile || confidence === null) return <ReportMissing />;

  return <ReportContent profile={profile} groups={ranking} confidence={confidence} />;
}

const conditionLabels: Record<VehicleCondition, string> = { new: "Nuove", used: "Usate" };

/**
 * The Advisor ranks new and used cars apart. With both groups the report opens on the group whose
 * winner ranks highest and lets the user switch; with one group it shows no extra control.
 */
function ReportContent({
  profile,
  groups,
  confidence,
}: {
  profile: DecisionProfile;
  groups: RankingGroup[];
  confidence: number;
}) {
  const [picked, setPicked] = useState<VehicleCondition | null>(null);
  const selected = groups.find((g) => g.condition === picked) ?? topRankingGroup(groups)!;
  const winner = selected.items[0]!;
  const { s: searchSessionId } = Route.useSearch();
  const sessionId = searchSessionId ?? profile.decisionId;
  const chips = [
    vehicleTypeLabels[profile.vehicleType],
    profile.category ? categoryLabel(profile.category) : null,
    profile.budgetMax ? `Budget ${profile.budgetMax.toLocaleString("it-IT")} €` : null,
    ...(profile.usage ?? []).map((u) => usageLabels[u] ?? u),
    ...(profile.priorities ?? []).map((p) => dnaLabels[p] ?? p),
  ].filter((x): x is string => Boolean(x));

  return (
    <div className="min-h-screen bg-background">
      <AppHeader label="Riepilogo della scelta" maxWidth="max-w-[70rem]" />
      <main className="mx-auto w-full max-w-[70rem] space-y-14 px-6 py-12 sm:px-8 lg:py-20">
        {groups.length > 1 && (
          <div className="flex flex-col items-center gap-3 text-center">
            <div role="group" aria-label="Classifica per condizione" className="inline-flex rounded-full border border-border/70 bg-card p-1">
              {groups.map((g) => (
                <button
                  key={g.condition}
                  type="button"
                  aria-pressed={g.condition === selected.condition}
                  onClick={() => setPicked(g.condition)}
                  className="min-h-11 rounded-full px-5 text-[0.9rem] font-medium transition-colors aria-pressed:bg-primary aria-pressed:text-primary-foreground"
                >
                  {conditionLabels[g.condition]} · {g.items[0]!.score}
                </button>
              ))}
            </div>
            <p className="max-w-xl text-sm text-muted-foreground">
              DriveWise valuta separatamente auto nuove e usate: ogni classifica ha il suo vincitore.
            </p>
          </div>
        )}
        <ReportRanking key={selected.condition} profile={profile} ranking={selected.items} confidence={confidence} sessionId={sessionId} chips={chips} />
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

/** Winner, reasons and alternatives of one condition group; keyed by condition so its animations restart. */
function ReportRanking({
  profile,
  ranking,
  confidence,
  sessionId,
  chips,
}: {
  profile: DecisionProfile;
  ranking: ScoredVehicle[];
  confidence: number;
  sessionId: string | undefined;
  chips: string[];
}) {
  const reduce = useReducedMotion();
  const winner = ranking[0]!;
  const offerUrl = safeHttpsUrl(winner.offer?.source_url);
  const checks = describeAdvisorGaps(winner.missingFactors ?? [], winner.warnings ?? []);
  const shownConfidence = useCountUp(confidence, reduce ? 0 : 1400, !!reduce);
  const [celebrated, setCelebrated] = useState(false);
  const alternatives = ranking.slice(1, 5);
  const sections = buildReportSections(winner.vehicle, profile);

  return (
    <>
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
              {winner.decisionStatus === 'insufficient_data' ? 'Punteggio provvisorio: dati insufficienti' : 'Decision Score'} · {winner.score}/100
            </p>
            <p className="mt-1 text-xs text-muted-foreground">Punteggio DriveWise</p>
            <h1 className="font-heading mt-6 text-2xl font-semibold tracking-[-0.02em] sm:text-3xl">
              {winner.vehicle.brand} {winner.vehicle.model}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">{categoryLabel(winner.vehicle.category)}</p>
            <PriceLine vehicle={winner.vehicle} className="mt-1 text-sm text-muted-foreground" />
            {winner.offer && <p className="mt-3 text-sm text-muted-foreground">{winner.offer.title} · {winner.offer.condition === 'new' ? 'Nuova' : 'Usata'} · {winner.offer.price_eur.toLocaleString('it-IT')} €{offerUrl && <> · <a href={offerUrl} target="_blank" rel="noopener noreferrer" className="underline">Vedi offerta</a></>}</p>}
            <p className="mt-3 text-sm text-muted-foreground">
              Affidabilità della scelta {shownConfidence}%
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

          {checks.length > 0 && (
            <div className="relative mt-8 rounded-2xl border border-border/70 bg-background p-5 text-left">
              <h2 className="text-sm font-semibold">Da verificare su questo veicolo</h2>
              <ul className="mt-3 space-y-2">
                {checks.map((c) => (
                  <li key={c} className="flex gap-3 text-sm text-muted-foreground first-letter:uppercase">
                    <AlertTriangle className="mt-0.5 size-4 shrink-0 text-accent" aria-hidden />
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {winner.vehicle.list_price && (
            <div className="relative mt-10 text-left">
              <h2 className="mb-4 text-sm font-semibold">Prezzo di listino</h2>
              <ListPricePanel price={winner.vehicle.list_price} />
            </div>
          )}

          <SourceCredits credits={winner.vehicle.credits} className="relative mt-8 text-left" />

          <div className="relative mt-12 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Button
              asChild
              className="h-auto min-h-14 w-full gap-3 whitespace-normal rounded-full px-6 py-3 text-[0.95rem] font-semibold leading-snug"
            >
              <Link
                to="/app/vehicle/$id"
                params={{ id: winner.vehicle.id }}
                search={{ spec: winner.specId, s: sessionId }}
              >
                <span className="min-w-0 text-center">Apri la scheda {winner.vehicle.model}</span>
                <ArrowRight className="size-4 shrink-0" aria-hidden />
              </Link>
            </Button>
            <Button
              asChild
              variant="outline"
              className="h-auto min-h-14 w-full gap-3 whitespace-normal rounded-full border-border/70 bg-card px-6 py-3 text-[0.95rem] font-semibold leading-snug"
            >
              <Link to="/app/start" onClick={clearState}>
                <ArrowLeft className="size-4 shrink-0" aria-hidden />
                <span className="min-w-0 text-center">Rifai la Scelta Guidata</span>
              </Link>
            </Button>
          </div>
        </motion.article>

        {sections.length > 0 && (
          <VSection
            title="Cosa cambia davvero per te"
            intro="Solo dati presenti nel catalogo DriveWise."
          >
            <DynamicSections sections={sections} />
          </VSection>
        )}

        {alternatives.length > 0 && (
          <VSection title="Alternative valutate" intro="Stesso profilo, punteggi diversi.">
            <ul className="grid w-full grid-cols-[minmax(0,1fr)] gap-3">
              {alternatives.map((a) => (
                <li key={a.vehicle.id} className="w-full min-w-0">
                  <Link
                    to="/app/vehicle/$id"
                    params={{ id: a.vehicle.id }}
                    search={{ spec: a.specId, s: sessionId }}
                    className="flex w-full min-h-11 min-w-0 items-center justify-between gap-4 rounded-2xl border border-border/70 bg-card px-4 py-3.5 text-sm transition-colors hover:border-primary/40"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-foreground">
                        {a.vehicle.brand} {a.vehicle.model}
                      </span>
                      <span className="mt-0.5 block truncate text-[0.8rem] text-muted-foreground">
                        {a.decisionStatus === 'insufficient_data' ? 'Valutazione provvisoria: dati insufficienti' : categoryText(a.why[0] ?? a.vehicle.category)}
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
    </>
  );
}
