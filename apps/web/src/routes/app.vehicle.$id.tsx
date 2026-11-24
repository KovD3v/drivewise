import { useEffect, useMemo, useState, type ReactNode } from "react";
import { createFileRoute, Link, notFound, useRouter } from "@tanstack/react-router";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Check, ChevronDown, Minus } from "lucide-react";
import { EASE } from "@/lib/motion";
import { useCountUp } from "@/lib/use-count-up";
import { cn } from "@/lib/utils";
import { Card, KeyValue, VSection } from "@/components/vehicle/primitives";
import { DynamicSections } from "@/components/vehicle/DynamicSections";
import { GarageFit, type GarageInput } from "@/components/vehicle/GarageFit";
import { AppHeader } from "@/components/app/AppHeader";
import { contextualSuggestions, datasetAnswer } from "@/lib/vehicle-ask";
import { loadGuidedDecisionReport, rankVehicles, type ScoredVehicle } from "@/lib/decision-engine";
import type { DecisionProfile } from "@/lib/decision-profile";
import { loadState } from "@/lib/decision-state";
import { buildReportSections } from "@/lib/report-sections";
import { fuelLabel, mm2cm, typeLabel, vehicleName } from "@/lib/vehicle-format";
import { fromApiVehicle, getVehicleDetail, type Vehicle } from "@/services/vehicleService";
import { categoryLabel } from "@/lib/category-labels";
import { ListPricePanel, SourceCredits } from "@/components/vehicle/source-facts";
import { PriceLine } from "@/components/vehicle/PriceLine";
import { isUuid } from "@/lib/uuid";

/** `spec` names the version to show; `s` the guided decision that scored it. */
type VehicleSearch = { spec?: string; s?: string };

export const Route = createFileRoute("/app/vehicle/$id")({
  validateSearch: (search: Record<string, unknown>): VehicleSearch => ({
    spec: typeof search["spec"] === "string" ? search["spec"] : undefined,
    s: typeof search["s"] === "string" ? search["s"] : undefined,
  }),
  loader: async ({ params }) => {
    // A malformed id can never name a vehicle: answer 404 instead of letting the API reject it as an error.
    if (!isUuid(params.id)) throw notFound();
    const detail = await getVehicleDetail(params.id);
    if (!detail) throw notFound();
    return { vehicle: fromApiVehicle(detail), detail };
  },
  head: ({ loaderData, match }) => {
    if (!loaderData && match.status === "error")
      return { meta: [
        { title: "Servizio temporaneamente non disponibile | DriveWise" },
        { name: "robots", content: "noindex" },
      ] };
    if (!loaderData)
      return { meta: [
        { title: "Veicolo non trovato | DriveWise" },
        { name: "description", content: "Questo veicolo non è presente nel catalogo DriveWise." },
        { property: "og:title", content: "Veicolo non trovato | DriveWise" },
        { property: "og:description", content: "Questo veicolo non è presente nel catalogo DriveWise." },
        { property: "og:type", content: "website" },
        { name: "twitter:card", content: "summary_large_image" },
        { name: "robots", content: "noindex" },
      ] };
    const v = loaderData.vehicle;
    const title = `${v.brand} ${v.model} — è adatto a te? | DriveWise`;
    const description = `${v.brand} ${v.model}: i dati del catalogo DriveWise, con le loro fonti.`;
    return {
      meta: [
        { title },
        { name: "description", content: description },
        { property: "og:title", content: title },
        { property: "og:description", content: description },
        { property: "og:type", content: "article" },
        { name: "twitter:card", content: "summary_large_image" },
        { name: "robots", content: "noindex" },
      ],
    };
  },
  component: VehiclePage,
  notFoundComponent: VehicleNotFound,
  errorComponent: VehicleUnavailable,
});

// TanStack splits each route slot into its own chunk; a slot function must not be referenced elsewhere.
function VehicleUnavailable() {
  const router = useRouter();
  return (
    <VehicleMessage
      title="Servizio temporaneamente non disponibile."
      body="Non riusciamo a leggere il catalogo DriveWise in questo momento. Riprova tra qualche istante."
      action={
        <button
          type="button"
          // A loader error needs the router to reload the route; invalidate also resets the error boundary.
          onClick={() => void router.invalidate()}
          className="mt-8 inline-flex h-12 items-center rounded-full bg-primary px-7 text-[0.95rem] font-medium text-primary-foreground transition-colors hover:bg-primary-hover"
        >
          Riprova
        </button>
      }
    />
  );
}

function VehicleNotFound() {
  return (
    <VehicleMessage
      title="Veicolo non trovato."
      body="Questo veicolo non è presente nel catalogo DriveWise."
      action={
        <Link
          to="/app/start"
          className="mt-8 inline-flex h-12 items-center rounded-full bg-primary px-7 text-[0.95rem] font-medium text-primary-foreground transition-colors hover:bg-primary-hover"
        >
          Torna alla Scelta Guidata
        </Link>
      }
    />
  );
}

function VehicleMessage({ title, body, action }: { title: string; body: string; action: ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <AppHeader label="Dettaglio veicolo" />
      <main className="mx-auto w-full max-w-[46rem] px-6 py-24 text-center sm:px-8">
        <h1 className="font-heading text-[2rem] font-extrabold tracking-[-0.03em]">{title}</h1>
        <p className="mt-4 text-[0.95rem] text-muted-foreground">{body}</p>
        {action}
      </main>
    </div>
  );
}

function garageInputFrom(profile: DecisionProfile | null): GarageInput | undefined {
  if (!profile || profile.garage_status !== "known" || !profile.garageDimensions) return undefined;
  const g = profile.garageDimensions;
  const mm = (value?: string) => {
    const n = Number((value ?? "").replace(",", "."));
    return Number.isFinite(n) && n > 0 ? n * 10 : undefined;
  };
  return {
    garage_length_mm: mm(g.length),
    garage_width_mm: mm(g.width),
    garage_height_mm: mm(g.height),
    door_width_mm: mm(g.doorWidth),
    door_height_mm: mm(g.doorHeight),

  };
}

function VehiclePage() {
  const { vehicle: loaded, detail } = Route.useLoaderData();
  const reduce = useReducedMotion();
  const { spec, s: decisionId } = Route.useSearch();
  const [profile, setProfile] = useState<DecisionProfile | null>(null);
  const [ranked, setRanked] = useState<ScoredVehicle[]>([]);

  useEffect(() => {
    let alive = true;
    setProfile(null);
    setRanked([]);
    if (decisionId && loaded.vehicle_type === "car") {
      // The link names the decision: read it from the API, so the score shows in any browser.
      void loadGuidedDecisionReport(decisionId)
        .then((report) => { if (alive) { setProfile(report.profile); setRanked(report.ranking); } })
        .catch(() => { /* no score without the decision; the catalogue facts still show */ });
    } else {
      const state = loadState();
      if (state?.profile.vehicleType === loaded.vehicle_type) {
        setProfile(state.profile);
        void rankVehicles(state.profile)
          .then((items) => { if (alive) setRanked(items); })
          .catch(() => { if (alive) setRanked([]); });
      }
    }
    return () => { alive = false; };
  }, [decisionId, loaded.vehicle_type]);

  const activeProfile: DecisionProfile = profile ?? { vehicleType: loaded.vehicle_type };
  const rankedHere = ranked.find(item => item.vehicle.id === loaded.id);
  // The version shown: the one the link names, else the one the Advisor scored, else the default.
  const activeSpecId = useMemo(() => {
    const known = (id: string | undefined) => (id && detail.specs?.some((candidate) => candidate.id === id) ? id : undefined);
    return known(spec) ?? known(rankedHere?.specId) ?? detail.specs?.[0]?.id;
  }, [spec, rankedHere, detail]);
  // The score belongs to one version: show it only next to that version's facts.
  const scored = rankedHere && rankedHere.specId === activeSpecId ? rankedHere : undefined;
  const v = useMemo(() => (activeSpecId ? fromApiVehicle(detail, activeSpecId) : loaded), [activeSpecId, detail, loaded]);

  const score = useCountUp(scored?.score ?? 0, reduce ? 0 : 1300, !!reduce);
  const sections = buildReportSections(v, activeProfile);
  const garage = garageInputFrom(profile);

  const alternatives = ranked.filter(item => item.vehicle.id !== v.id).slice(0, 3);

  const t = v.two_wheel;
  const specs: { label: string; value: string }[] = [
    { label: "Tipo", value: typeLabel[v.vehicle_type] },
    { label: "Categoria", value: categoryLabel(v.category) },
    ...(v.powertrain.fuel ? [{ label: "Alimentazione", value: fuelLabel(v.powertrain.fuel) }] : []),
    ...(v.seats ? [{ label: "Posti", value: String(v.seats) }] : []),
    ...(v.dimensions.length_mm ? [{ label: "Lunghezza", value: mm2cm(v.dimensions.length_mm)! }] : []),
    ...(v.dimensions.height_mm ? [{ label: "Altezza", value: mm2cm(v.dimensions.height_mm)! }] : []),
    ...(v.dimensions.boot_liters ? [{ label: "Bagagliaio", value: `${v.dimensions.boot_liters} l` }] : []),
    ...(t?.seat_height_mm ? [{ label: "Altezza sella", value: `${t.seat_height_mm} mm` }] : []),
    ...(t?.wet_weight_kg ? [{ label: "Peso in ordine di marcia", value: `${t.wet_weight_kg} kg` }] : []),
    ...(t?.fuel_tank_capacity_liters ? [{ label: "Serbatoio", value: `${t.fuel_tank_capacity_liters} l` }] : []),
    ...(t?.underseat_storage_liters ? [{ label: "Sottosella", value: `${t.underseat_storage_liters} l` }] : []),
  ];

  return (
    <div className="min-h-screen bg-background">
      <AppHeader label="Scheda veicolo" maxWidth="max-w-[70rem]" />
      <main className="mx-auto w-full max-w-[70rem] space-y-14 px-6 py-12 sm:px-8 lg:py-20">
        <motion.header
          initial={reduce ? { opacity: 1 } : { opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: EASE }}
          className="relative overflow-hidden rounded-[2.25rem] border border-border/70 bg-card p-8 shadow-[var(--shadow-object)] sm:p-12"
        >
          <div
            aria-hidden
            className="pointer-events-none absolute -top-24 -right-16 size-64 rounded-full bg-primary/12 blur-3xl"
          />
          <div className="relative flex flex-col gap-8 sm:flex-row sm:items-end sm:justify-between">
            <div className="min-w-0">
              <p className="text-[0.7rem] tracking-[0.2em] text-muted-foreground uppercase">
                {typeLabel[v.vehicle_type]} · {categoryLabel(v.category)}
              </p>
              <h1 className="font-heading mt-3 text-[2rem] leading-tight font-extrabold tracking-[-0.03em] sm:text-[2.6rem]">
                {vehicleName(v)}
              </h1>
              <PriceLine vehicle={v} />
            </div>
            {scored && (
              <div className="shrink-0 text-left sm:text-right">
                <p className="font-heading text-[3.5rem] leading-none font-extrabold tabular-nums">
                  {score}
                </p>
                <p className="mt-2 text-[0.7rem] tracking-[0.18em] text-muted-foreground uppercase">
                  {scored.decisionStatus === 'insufficient_data' ? 'Valutazione provvisoria: dati insufficienti' : 'Compatibilità con il tuo profilo'}
                </p>
              </div>
            )}
          </div>

          <Link
            to="/app/compare"
            search={{ vehicle: v.id, spec: activeSpecId }}
            className="relative mt-6 inline-flex h-11 items-center rounded-full border border-border/70 bg-background px-5 text-[0.875rem] font-medium transition-colors hover:border-primary/40"
          >
            Confronta
          </Link>

          {scored ? (
            <div className="relative mt-10 grid gap-8 border-t border-border/70 pt-8 sm:grid-cols-2">
              <div>
                <h2 className="text-sm font-semibold">Perché è adatto a te</h2>
                <ul className="mt-4 space-y-3">
                  {scored.why.length ? (
                    scored.why.map((s) => (
                      <li key={s} className="flex gap-3 text-sm text-muted-foreground">
                        <Check className="mt-0.5 size-4 shrink-0 text-primary" />
                        {s}
                      </li>
                    ))
                  ) : (
                    <li className="text-sm text-muted-foreground">
                      Nessun punto di forza specifico rispetto alle tue priorità dichiarate.
                    </li>
                  )}
                </ul>
              </div>
              <div>
                <h2 className="text-sm font-semibold">Compromessi</h2>
                <ul className="mt-4 space-y-3">
                  {scored.tradeoffs.length ? (
                    scored.tradeoffs.map((s) => (
                      <li key={s} className="flex gap-3 text-sm text-muted-foreground">
                        <Minus className="mt-0.5 size-4 shrink-0 text-accent" />
                        {s}
                      </li>
                    ))
                  ) : (
                    <li className="text-sm text-muted-foreground">
                      Nessun compromesso rilevante nei dati disponibili.
                    </li>
                  )}
                </ul>
              </div>
            </div>
          ) : rankedHere ? (
            <p className="relative mt-10 border-t border-border/70 pt-8 text-sm text-muted-foreground">
              Il punteggio della tua Scelta Guidata riguarda un'altra versione di questo veicolo.{" "}
              <Link
                to="/app/vehicle/$id"
                params={{ id: v.id }}
                search={{ spec: rankedHere.specId, s: decisionId ?? profile?.decisionId }}
                className="text-foreground underline underline-offset-4"
              >
                Vedi la versione valutata
              </Link>
            </p>
          ) : v.vehicle_type !== "car" ? (
            <p className="relative mt-10 border-t border-border/70 pt-8 text-sm text-muted-foreground">
              Per moto e scooter DriveWise mostra il catalogo senza punteggio: il motore decisionale valuta solo le auto.{" "}
              <Link to="/app/catalog" search={{ type: v.vehicle_type }} className="text-foreground underline underline-offset-4">
                Torna al catalogo
              </Link>
            </p>
          ) : (
            <p className="relative mt-10 border-t border-border/70 pt-8 text-sm text-muted-foreground">
              Completa la{" "}
              <Link to="/app/start" className="text-foreground underline underline-offset-4">
                Scelta Guidata
              </Link>{" "}
              per vedere quanto questo veicolo è compatibile con il tuo profilo.
            </p>
          )}
        </motion.header>

        {sections.length > 0 && (
          <VSection title="I dati che contano" intro="Dati del catalogo DriveWise, con le fonti in fondo alla pagina.">
            <DynamicSections sections={sections} />
          </VSection>
        )}

        {v.vehicle_type === "car" && v.dimensions?.length_mm && (
          <VSection title="Compatibilità garage" intro="Confronto fra le misure reali del veicolo e quelle del tuo garage.">
            <GarageFit vehicle={v} garage={garage} />
          </VSection>
        )}

        {v.vehicle_type === "car" && (
          <VSection title="Chiedi a DriveWise" intro="Risposte costruite solo sui dati di questo veicolo.">
            <AskDriveWise vehicle={v} specId={activeSpecId} />
          </VSection>
        )}

        {v.list_price && (
          <VSection title="Prezzo di listino" intro="Il prezzo pubblicato nel listino ufficiale: non è un'offerta di un venditore.">
            <ListPricePanel price={v.list_price} />
          </VSection>
        )}

        <VSection title="Specifiche" intro="Tutti i campi che il catalogo restituisce per questo veicolo.">
          <TechSpecs specs={specs} />
        </VSection>

        {v.credits.length > 0 && (
          <Card>
            <SourceCredits credits={v.credits} />
          </Card>
        )}

        {alternatives.length > 0 && (
          <VSection title="Alternative dello stesso tipo" intro="Ordinate sul tuo profilo, quando disponibile.">
            <ul className="grid gap-3 sm:grid-cols-3">
              {alternatives.map((a) => (
                <li key={a.vehicle.id}>
                  <Link
                    to="/app/vehicle/$id"
                    params={{ id: a.vehicle.id }}
                    search={{ spec: a.specId, s: decisionId ?? profile?.decisionId }}
                    className="block h-full rounded-2xl border border-border/70 bg-card p-4 transition-colors hover:border-primary/40"
                  >
                    <p className="truncate text-[0.9rem] font-medium">{vehicleName(a.vehicle)}</p>
                    <p className="mt-1 text-[0.78rem] text-muted-foreground">{a.decisionStatus === 'insufficient_data' ? 'Valutazione provvisoria: dati insufficienti' : categoryLabel(a.vehicle.category)}</p>
                    {scored && (
                      <p className="font-heading mt-3 text-[1.1rem] font-bold tabular-nums">{a.score}%</p>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          </VSection>
        )}
      </main>
    </div>
  );
}

function AskDriveWise({ vehicle, specId }: { vehicle: Vehicle; specId: string | undefined }) {
  const [value, setValue] = useState("");
  const [thread, setThread] = useState<{ q: string; a: string }[]>([]);

  const ask = async (q: string) => {
    const text = q.trim();
    if (!text) return;
    try { const answer = await datasetAnswer(text, vehicle, specId); setThread(t => [...t, { q: text, a: answer }]); }
    catch (error) { setThread(t => [...t, { q: text, a: error instanceof Error ? error.message : 'Analisi non disponibile. Riprova.' }]); }
    setValue("");
  };

  return (
    <div id="chiedi" className="scroll-mt-24">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(value);
        }}
        className="flex items-center gap-2 rounded-full border border-border/70 bg-card p-2 pl-5 shadow-[var(--shadow-object)] transition-colors focus-within:border-primary/40"
      >
        <label htmlFor="ask-drivewise" className="sr-only">
          Chiedi qualcosa su questo veicolo
        </label>
        <input
          id="ask-drivewise"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={`Chiedi qualcosa su ${vehicleName(vehicle)}…`}
          className="h-12 w-full min-w-0 bg-transparent text-[0.95rem] outline-none placeholder:text-foreground/45"
        />
        <button
          type="submit"
          className="grid size-12 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground transition-colors hover:bg-primary-hover"
          aria-label="Invia domanda"
        >
          <ArrowRight className="size-4" />
        </button>
      </form>

      <div className="mt-4 flex flex-wrap gap-2">
        {contextualSuggestions.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => ask(s)}
            className="rounded-full border border-border/70 bg-card px-4 py-2 text-[0.8125rem] text-muted-foreground transition-all duration-300 hover:-translate-y-px hover:border-primary/40 hover:text-foreground"
          >
            {s}
          </button>
        ))}
      </div>

      <div className="mt-6 space-y-4">
        <AnimatePresence initial={false}>
          {thread.map((t, i) => (
            <motion.div
              key={`${t.q}-${i}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: EASE }}
              className="rounded-3xl border border-border/70 bg-card p-5"
            >
              <p className="text-[0.85rem] font-medium">{t.q}</p>
              <p className="mt-2 text-[0.9rem] text-muted-foreground">{t.a}</p>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

function TechSpecs({ specs }: { specs: { label: string; value: string }[] }) {
  const [open, setOpen] = useState(false);
  return (
    <Card className="p-0">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left"
      >
        <span className="text-[0.95rem] font-medium">Tutte le specifiche disponibili</span>
        <ChevronDown className={cn("size-4 transition-transform duration-300", open && "rotate-180")} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.4, ease: EASE }}
            className="overflow-hidden"
          >
            <div className="border-t border-border/70 px-6 py-6">
              <KeyValue rows={specs} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
