import { useEffect, useState } from "react";
import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Check, ChevronDown, Minus } from "lucide-react";
import { EASE } from "@/lib/motion";
import { useCountUp } from "@/lib/use-count-up";
import { cn } from "@/lib/utils";
import { Card, KeyValue, VSection } from "@/components/vehicle/primitives";
import { DynamicSections } from "@/components/vehicle/DynamicSections";
import { ReliabilityPanel } from "@/components/vehicle/ReliabilityPanel";
import { SecurityRisk } from "@/components/vehicle/SecurityRisk";
import { GarageFit, type GarageInput } from "@/components/vehicle/GarageFit";
import { AppHeader } from "@/components/app/AppHeader";
import { contextualSuggestions, datasetAnswer } from "@/lib/vehicle-ask";
import { rankVehicles, type ScoredVehicle } from "@/lib/decision-engine";
import { experienceLabels, type DecisionProfile } from "@/lib/decision-profile";
import { loadState } from "@/lib/decision-state";
import { buildReportSections } from "@/lib/report-sections";
import { euro, fuelLabel, mm2cm, typeLabel, vehicleName } from "@/lib/vehicle-format";
import { getVehicleById, getVehiclesByType, type Vehicle } from "@/services/vehicleService";

export const Route = createFileRoute("/app/vehicle/$id")({
  loader: async ({ params }) => {
    const vehicle = await getVehicleById(params.id);
    if (!vehicle) throw notFound();
    const siblings = (await getVehiclesByType(vehicle.vehicle_type)).filter((v) => v.id !== vehicle.id);
    return { vehicle, siblings };
  },
  head: ({ loaderData }) => {
    if (!loaderData)
      return { meta: [{ title: "Veicolo non trovato | DriveWise" }, { name: "robots", content: "noindex" }] };
    const v = loaderData.vehicle;
    const title = `${v.brand} ${v.model} — è adatto a te? | DriveWise`;
    const description = `Dati reali su ${v.brand} ${v.model}: profilo tecnico, affidabilità, furti osservati e compatibilità con il tuo profilo decisionale.`;
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
  errorComponent: VehicleNotFound,
});

function VehicleNotFound() {
  return (
    <div className="min-h-screen bg-background">
      <AppHeader label="Dettaglio veicolo" />
      <main className="mx-auto w-full max-w-[46rem] px-6 py-24 text-center sm:px-8">
        <h1 className="font-heading text-[2rem] font-extrabold tracking-[-0.03em]">Veicolo non trovato.</h1>
        <p className="mt-4 text-[0.95rem] text-muted-foreground">
          Questo veicolo non è presente nel catalogo DriveWise.
        </p>
        <Link
          to="/app/start"
          className="mt-8 inline-flex h-12 items-center rounded-full bg-primary px-7 text-[0.95rem] font-medium text-primary-foreground transition-colors hover:bg-primary-hover"
        >
          Torna alla Scelta Guidata
        </Link>
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
  const { vehicle: v, siblings } = Route.useLoaderData();
  const reduce = useReducedMotion();
  const [profile, setProfile] = useState<DecisionProfile | null>(null);

  useEffect(() => {
    const state = loadState();
    if (state?.profile.vehicleType === v.vehicle_type) setProfile(state.profile);
  }, [v.vehicle_type]);

  const activeProfile: DecisionProfile = profile ?? { vehicleType: v.vehicle_type };
  const [ranked, setRanked] = useState<ScoredVehicle[]>([]);
  useEffect(() => {
    let alive = true;
    if (profile) void rankVehicles(profile).then(items => { if (alive) setRanked(items); }).catch(() => { if (alive) setRanked([]); });
    return () => { alive = false; };
  }, [profile]);
  const scored = ranked.find(item => item.vehicle.id === v.id);

  const score = useCountUp(scored?.score ?? 0, reduce ? 0 : 1300, !!reduce);
  const sections = buildReportSections(v, activeProfile);
  const garage = garageInputFrom(profile);

  const alternatives = ranked.filter(item => item.vehicle.id !== v.id).slice(0, 3);

  const specs: { label: string; value: string }[] = [
    { label: "Tipo", value: typeLabel[v.vehicle_type] },
    { label: "Categoria", value: v.category },
    ...(v.pricing.new_price_estimate
      ? [{ label: "Prezzo indicativo nuovo", value: euro(v.pricing.new_price_estimate) }]
      : []),
    ...(v.powertrain?.fuel ? [{ label: "Alimentazione", value: fuelLabel(v.powertrain.fuel) }] : []),
    ...(v.powertrain?.engine_cc ? [{ label: "Cilindrata", value: `${v.powertrain.engine_cc} cc` }] : []),
    ...(v.dimensions?.length_mm ? [{ label: "Lunghezza", value: mm2cm(v.dimensions.length_mm)! }] : []),
    ...(v.dimensions?.width_with_mirrors_mm
      ? [{ label: "Larghezza con specchietti", value: mm2cm(v.dimensions.width_with_mirrors_mm)! }]
      : []),
    ...(v.dimensions?.height_mm ? [{ label: "Altezza", value: mm2cm(v.dimensions.height_mm)! }] : []),
    ...(v.dimensions?.boot_liters ? [{ label: "Bagagliaio", value: `${v.dimensions.boot_liters} l` }] : []),
    ...(v.motorcycle_specific?.seat_height_mm
      ? [{ label: "Altezza sella", value: `${v.motorcycle_specific.seat_height_mm} mm` }]
      : []),
    ...(v.motorcycle_specific?.wet_weight_kg
      ? [{ label: "Peso in ordine di marcia", value: `${v.motorcycle_specific.wet_weight_kg} kg` }]
      : []),
    ...(v.motorcycle_specific?.recommended_experience
      ? [
          {
            label: "Esperienza consigliata",
            value:
              experienceLabels[v.motorcycle_specific.recommended_experience] ??
              v.motorcycle_specific.recommended_experience,
          },
        ]
      : []),
    ...(v.scooter_specific?.wet_weight_kg
      ? [{ label: "Peso in ordine di marcia", value: `${v.scooter_specific.wet_weight_kg} kg` }]
      : []),
    ...(v.scooter_specific?.underseat_storage_l
      ? [{ label: "Sottosella", value: `${v.scooter_specific.underseat_storage_l} l` }]
      : []),
    ...(typeof v.scooter_specific?.helmet_storage_full_face === "boolean"
      ? [
          {
            label: "Casco integrale sotto la sella",
            value: v.scooter_specific.helmet_storage_full_face ? "Sì" : "No",
          },
        ]
      : []),
  ];

  return (
    <div className="min-h-screen bg-background">
      <AppHeader label="Scheda veicolo" maxWidth="max-w-[70rem]" />
      {v.mock && <p className="mx-auto max-w-[70rem] px-8 pt-5 text-xs text-muted-foreground">Demo: dati e punteggi simulati.</p>}
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
                {typeLabel[v.vehicle_type]} · {v.category}
              </p>
              <h1 className="font-heading mt-3 text-[2rem] leading-tight font-extrabold tracking-[-0.03em] sm:text-[2.6rem]">
                {vehicleName(v)}
              </h1>
              {v.pricing.new_price_estimate && (
                <p className="mt-3 text-[0.95rem] text-muted-foreground">
                  Prezzo indicativo del nuovo {euro(v.pricing.new_price_estimate)}
                </p>
              )}
            </div>
            {scored && (
              <div className="shrink-0 text-left sm:text-right">
                <p className="font-heading text-[3.5rem] leading-none font-extrabold tabular-nums">
                  {score}
                </p>
                <p className="mt-2 text-[0.7rem] tracking-[0.18em] text-muted-foreground uppercase">
                  Compatibilità con il tuo profilo
                </p>
              </div>
            )}
          </div>

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
          <VSection title="I dati che contano" intro="Dati del catalogo e anteprime demo indicate nelle schede.">
            <DynamicSections sections={sections} />
          </VSection>
        )}

        <VSection title="Affidabilità" intro="Profilo tecnico DriveWise, scala 0-100.">
          <ReliabilityPanel vehicle={v} />
        </VSection>

        <VSection title="Sicurezza e furti" intro="Anteprima del servizio di statistiche sui furti.">
          <SecurityRisk vehicle={v} />
        </VSection>

        {v.vehicle_type === "car" && v.dimensions?.length_mm && (
          <VSection title="Compatibilità garage" intro="Confronto fra le misure reali del veicolo e quelle del tuo garage.">
            <GarageFit vehicle={v} garage={garage} />
          </VSection>
        )}

        <VSection title="Chiedi a DriveWise" intro="Risposte costruite solo sui dati di questo veicolo.">
          <AskDriveWise vehicle={v} />
        </VSection>

        <VSection title="Specifiche" intro="Tutti i campi disponibili nel dataset.">
          <TechSpecs specs={specs} />
        </VSection>

        {alternatives.length > 0 && (
          <VSection title="Alternative dello stesso tipo" intro="Ordinate sul tuo profilo, quando disponibile.">
            <ul className="grid gap-3 sm:grid-cols-3">
              {alternatives.map((a) => (
                <li key={a.vehicle.id}>
                  <Link
                    to="/app/vehicle/$id"
                    params={{ id: a.vehicle.id }}
                    className="block h-full rounded-2xl border border-border/70 bg-card p-4 transition-colors hover:border-primary/40"
                  >
                    <p className="truncate text-[0.9rem] font-medium">{vehicleName(a.vehicle)}</p>
                    <p className="mt-1 text-[0.78rem] text-muted-foreground">{a.vehicle.category}</p>
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

function AskDriveWise({ vehicle }: { vehicle: Vehicle }) {
  const [value, setValue] = useState("");
  const [thread, setThread] = useState<{ q: string; a: string }[]>([]);

  const ask = async (q: string) => {
    const text = q.trim();
    if (!text) return;
    try { const answer = await datasetAnswer(text, vehicle); setThread(t => [...t, { q: text, a: answer }]); }
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
