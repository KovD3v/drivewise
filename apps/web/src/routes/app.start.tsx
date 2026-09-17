import { GuidedCarFlow } from "@/components/app/GuidedCarFlow";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { MobilePanel } from "@/components/app/MobilePanel";
import { AppHeader } from "@/components/app/AppHeader";
import { AnalysisSequence } from "@/components/app/AnalysisSequence";
import { DecisionBar } from "@/components/app/DecisionBar";
import { DecisionMessage, TypingIndicator } from "@/components/app/DecisionMessage";
import { DecisionProfilePanel } from "@/components/app/DecisionProfilePanel";
import { ExtractedFacts } from "@/components/app/ExtractedFacts";
import { GarageDimensions, type GarageValues } from "@/components/app/GarageDimensions";
import { PrioritySelector } from "@/components/app/PrioritySelector";
import { ProgressNarrative } from "@/components/app/ProgressNarrative";
import { QuickChoice } from "@/components/app/QuickChoice";
import { StepStage } from "@/components/app/StepStage";
import { UserMessage } from "@/components/app/UserMessage";
import { VehicleTypeChoice } from "@/components/app/VehicleTypeChoice";
import { takeInitialQuery, track } from "@/lib/analytics";
import {
  decisionConfidence,
  previewRanking,
  rankVehicles,
  toPreview,
  type PreviewVehicle,
} from "@/lib/decision-engine";
import type { Fact, MissingItem } from "@/lib/decision-profile";
import { clearState, saveState } from "@/lib/decision-state";
import { EASE } from "@/lib/motion";
import {
  answersToProfile,
  buildQuestions,
  isQuestionActive,
  typeOptions,
  type Answers,
  type Question,
} from "@/lib/wizard-questions";
import type { VehicleTypeKey } from "@/services/vehicleService";

const title = "DriveWise — Costruisci la tua decisione";
const description =
  "Costruisci un profilo decisionale personale e confronta veicoli reali, pertinenti alle tue esigenze.";

export const Route = createFileRoute("/app/start")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: AppStart,
});

const typeLabels: Record<VehicleTypeKey, string> = {
  car: "Auto",
  motorcycle: "Moto",
  scooter: "Scooter",
};

const suggestionsByType: Record<VehicleTypeKey, string[]> = {
  car: ["Cerco un'auto per la famiglia", "Vorrei spendere poco di gestione", "Sto valutando un'elettrica"],
  motorcycle: ["Cerco una moto per iniziare", "Vorrei viaggiare in due", "Cerco una moto leggera per la città"],
  scooter: ["Cerco uno scooter per la città", "Devo usarlo in tangenziale", "Mi serve spazio per il casco"],
};

function makeSessionId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `dw-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function factsFromAnswers(type: VehicleTypeKey, answers: Answers, questions: Question[]): Fact[] {
  const facts: Fact[] = [{ id: "type", label: "Tipo veicolo", value: typeLabels[type] }];
  questions.forEach((q) => {
    const value = answers[q.id];
    if (!value) return;
    if (q.id === "garageDimensions") {
      const g = value as Record<string, string>;
      if (g["length"] && g["width"])
        facts.push({ id: q.id, label: "Garage", value: `${g["length"]} × ${g["width"]} cm` });
      return;
    }
    const label = labelFor(q, value);
    if (label) facts.push({ id: q.id, label: shortLabel(q.id), value: label });
  });
  return facts;
}

function shortLabel(id: string) {
  const map: Record<string, string> = {
    category: "Categoria",
    freeText: "Esigenza",
    usage: "Utilizzo",
    priorities: "Priorità",
    budgetMax: "Budget",
    garage_status: "Parcheggio",
    family_profile: "Passeggeri",
    experience: "Esperienza",
    rider_height_cm: "Altezza pilota",
    passenger_frequent: "Passeggero",
    helmet_storage_required: "Casco integrale",
  };
  return map[id] ?? id;
}

function labelFor(q: Question, value: string | string[] | Record<string, string>): string {
  const find = (v: string) => q.options?.find((o) => o.value === v)?.label ?? v;
  if (Array.isArray(value)) return value.map(find).join(", ");
  if (typeof value === "string") return value ? find(value) : "";
  return "";
}

/** Testo del recap laterale: copre anche le risposte "vuote" e le misure garage. */
function recapValue(q: Question, value: Answers[string]): string {
  if (q.kind === "garage") {
    const g = (value ?? {}) as Record<string, string>;
    const parts = [g["length"], g["width"], g["height"]].filter((n) => n && Number(n) > 0);
    return parts.length ? `${parts.join(" × ")} cm` : "—";
  }
  if (typeof value === "string" && value === "") {
    const empty = q.options?.find((o) => o.value === "");
    if (empty) return empty.label;
  }
  return labelFor(q, (value ?? "") as string) || "—";
}

function isAnswered(answers: Answers, id: string) {
  if (!(id in answers)) return false;
  const v = answers[id];
  return Array.isArray(v) ? v.length > 0 : v !== undefined;
}

function AppStart() {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState("");
  const [vehicleType, setVehicleType] = useState<VehicleTypeKey | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Answers>({});
  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState<"type" | "questions" | "typing" | "result" | "analysis">("type");
  const [ranking, setRanking] = useState<PreviewVehicle[]>([]);
  const [initialQuery, setInitialQuery] = useState("");
  const timers = useRef<number[]>([]);

  useEffect(() => {
    track("app_start_view");
    setSessionId(makeSessionId());
    setInitialQuery(takeInitialQuery() ?? "");
    clearState();
    return () => timers.current.forEach(clearTimeout);
  }, []);

  const later = useCallback((fn: () => void, ms: number) => {
    timers.current.push(window.setTimeout(fn, ms));
  }, []);

  const activeQuestions = useMemo(
    () => questions.filter((q) => isQuestionActive(q, answers)),
    [questions, answers],
  );
  const answeredCount = activeQuestions.filter((q) => isAnswered(answers, q.id)).length;
  const totalCount = activeQuestions.length + 1; // + selezione tipo
  const completion = vehicleType
    ? Math.round(((answeredCount + 1) / totalCount) * 100)
    : 0;

  const profile = useMemo(
    () => (vehicleType ? answersToProfile(vehicleType, answers) : null),
    [vehicleType, answers],
  );
  const confidence = profile ? decisionConfidence(profile) : 0;

  const known = useMemo(
    () => (vehicleType ? factsFromAnswers(vehicleType, answers, questions).map((f) => `${f.label}: ${f.value}`) : []),
    [vehicleType, answers, questions],
  );
  const missing: MissingItem[] = useMemo(() => {
    if (!vehicleType) return [{ id: "type", label: "Tipo di veicolo" }];
    return activeQuestions
      .filter((q) => !isAnswered(answers, q.id))
      .map((q) => ({ id: q.id, label: shortLabel(q.id) }));
  }, [vehicleType, activeQuestions, answers]);

  // Anteprima ranking: solo dataset, solo dal tipo scelto.
  useEffect(() => {
    if (!profile || profile.vehicleType === "car" || confidence <= 45) {
      setRanking([]);
      return;
    }
    let alive = true;
    void previewRanking(profile, 3).then((list) => {
      if (alive) setRanking(list.map(toPreview));
    }).catch(() => { if (alive) setRanking([]); });
    return () => {
      alive = false;
    };
  }, [profile, confidence]);

  useEffect(() => {
    if (!profile || profile.vehicleType === "car" || !sessionId) return;
    saveState({
      sessionId,
      status: phase === "analysis" ? "analysing" : phase === "result" ? "ready" : "collecting",
      currentStep: activeQuestions[index]?.id ?? phase,
      profile,
      answers,
      profileCompletion: completion,
      decisionConfidence: confidence,
      rankingIds: ranking.map((r) => r.id),
      updatedAt: Date.now(),
    });
  }, [profile, answers, sessionId, phase, index, activeQuestions, completion, confidence, ranking]);

  const selectType = (value: string) => {
    const type = value as VehicleTypeKey;
    setVehicleType(type);
    if (type === "car") return;
    setPhase("typing");
    void buildQuestions(type).then((list) => {
      setQuestions(list);
      setIndex(0);
      setPhase("questions");
    });
  };

  const advance = useCallback(
    (nextAnswers: Answers) => {
      const remaining = questions.filter((q) => isQuestionActive(q, nextAnswers));
      const nextIndex = remaining.findIndex((q) => !isAnswered(nextAnswers, q.id));
      setPhase("typing");
      later(() => {
        if (nextIndex === -1) {
          setPhase("result");
        } else {
          setIndex(nextIndex);
          setPhase("questions");
        }
      }, 650);
    },
    [questions, later],
  );

  const answer = (id: string, value: string | string[] | Record<string, string>) => {
    const next = { ...answers, [id]: value };
    setAnswers(next);
    advance(next);
  };

  const skipEmpty = (id: string) => answer(id, "");

  const showReport = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setPhase("analysis");
  };
  const finishAnalysis = useCallback(() => {
    void (async () => {
      if (profile && sessionId) {
        // Scrive lo stato finale (ranking incluso) PRIMA di navigare:
        // il report non deve mai leggere una sessione precedente.
        try {
          const list = await rankVehicles(profile);
          saveState({
            sessionId,
            status: "ready",
            currentStep: "report",
            profile,
            answers,
            profileCompletion: completion,
            decisionConfidence: confidence,
            rankingIds: list.map((r) => r.vehicle.id),
            updatedAt: Date.now(),
          });
        } catch {
          /* il report ricalcola comunque dal profilo persistito */
        }
        await navigate({ to: "/app/report", search: { s: sessionId } });
        return;
      }
      await navigate({ to: "/app/report", search: { s: undefined } });
    })();
  }, [navigate, profile, sessionId, answers, completion, confidence]);
  const restart = () => {
    clearState();
    window.location.reload();
  };

  const facts = vehicleType ? factsFromAnswers(vehicleType, answers, questions) : [];
  const currentQuestion = phase === "questions" ? activeQuestions[index] : undefined;

  if (vehicleType === "car") return <GuidedCarFlow initialQuery={initialQuery} />;

  return (
    <div className="min-h-screen bg-background">
      <AppHeader label="Scelta Guidata" maxWidth="max-w-[86rem]" />
      {vehicleType && <p className="mx-auto max-w-[86rem] px-8 pt-5 text-xs text-muted-foreground">Demo {typeLabels[vehicleType]}: catalogo e ranking simulati.</p>}
      <main className="mx-auto w-full max-w-[86rem] px-6 py-10 sm:px-8 lg:py-16">
        <div className="grid gap-10 lg:grid-cols-[7fr_3fr] lg:gap-14">
          <div className="min-w-0">
            <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: EASE }}>
              <h1 className="font-heading text-[2.25rem] leading-[1.05] font-extrabold text-foreground sm:text-[3rem]">
                Trova il veicolo perfetto.
              </h1>
              <p className="mt-5 max-w-2xl text-[1.02rem] leading-relaxed text-muted-foreground">
                Le domande cambiano in base a ciò che stai cercando: ti chiediamo solo ciò che i
                dati reali dei veicoli permettono di valutare.
              </p>
            </motion.div>

            <div className="mt-9 space-y-8">
              <StepStage themeId="facts" active={phase === "type"}>
                <DecisionMessage>
                  <p>Cosa stai cercando?</p>
                  <p className="text-muted-foreground">Auto, moto o scooter: da qui cambia tutto il percorso.</p>
                </DecisionMessage>
                <div className="pl-[3.125rem]">
                  {phase === "type" ? (
                    <VehicleTypeChoice
                      options={typeOptions.map((o) => ({
                        value: o.value,
                        label: o.label,
                        kind: o.value as "car" | "motorcycle" | "scooter",
                      }))}
                      onSelect={selectType}
                    />
                  ) : (
                    <AnsweredChip value={vehicleType ? typeLabels[vehicleType] : undefined} />
                  )}
                </div>
              </StepStage>

              {vehicleType && phase !== "type" && <ProgressNarrative completion={completion} />}

              {activeQuestions.map((q) => {
                const answered = answers[q.id];
                const isCurrent = currentQuestion?.id === q.id;
                const isPast = !isCurrent && isAnswered(answers, q.id);
                if (!isCurrent && !isPast) return null;
                return (
                  <div key={q.id} className="space-y-4">
                    {q.id === "freeText" && isPast && typeof answered === "string" && answered && (
                      <UserMessage>{answered}</UserMessage>
                    )}
                    <StepStage themeId={q.themeId} active={isCurrent}>
                      <DecisionMessage>
                        <p>{q.prompt}</p>
                        {q.hint && <p className="text-muted-foreground">{q.hint}</p>}
                      </DecisionMessage>
                      <div className="pl-[3.125rem]">
                        {isCurrent ? (
                          q.kind === "text" ? (
                            <DecisionBar
                              key={q.id}
                              initialValue={initialQuery}
                              placeholder="Descrivi liberamente cosa cerchi"
                              suggestions={vehicleType ? suggestionsByType[vehicleType] : []}
                              onSubmit={(text) => answer(q.id, text)}
                            />
                          ) : q.kind === "multi" ? (
                            <PrioritySelector
                              options={(q.options ?? []).map((o) => o.label)}
                              confirmLabel={q.id === "priorities" ? "Conferma priorità" : "Conferma utilizzi"}
                              onConfirm={(picked) =>
                                answer(
                                  q.id,
                                  picked.map((label) => q.options?.find((o) => o.label === label)?.value ?? label),
                                )
                              }
                            />
                          ) : q.kind === "garage" ? (
                            <GarageDimensions onConfirm={(values: GarageValues) => answer(q.id, values)} />
                          ) : (
                            <QuickChoice
                              options={(q.options ?? []).map((o) => o.label)}
                              allowCustom={q.allowCustom ?? false}
                              onSelect={(label) => {
                                const found = q.options?.find((o) => o.label === label);
                                if (found && found.value === "") skipEmpty(q.id);
                                else answer(q.id, found ? found.value : label);
                              }}
                            />
                          )
                        ) : (
                          <AnsweredChip value={recapValue(q, answered)} />
                        )}
                      </div>
                    </StepStage>
                  </div>
                );
              })}

              {phase === "typing" && (
                <DecisionMessage>
                  <TypingIndicator />
                </DecisionMessage>
              )}

              {phase === "result" && (
                <>
                  <StepStage themeId="facts" active>
                    <DecisionMessage>
                      <p>Ho abbastanza elementi per consigliarti.</p>
                      <p className="text-muted-foreground">Questo è il profilo che userò per il Decision Report.</p>
                    </DecisionMessage>
                    <div className="pl-[3.125rem]">
                      <ExtractedFacts facts={facts} delay={0.1} />
                    </div>
                  </StepStage>
                  <div className="flex flex-col gap-3 pl-[3.125rem] sm:flex-row">
                    <button
                      type="button"
                      onClick={showReport}
                      className="inline-flex h-12 items-center justify-center rounded-full bg-primary px-7 text-[0.95rem] font-medium text-primary-foreground transition-colors hover:bg-primary-hover"
                    >
                      Mostrami il Decision Report
                    </button>
                    <button
                      type="button"
                      onClick={restart}
                      className="inline-flex h-12 items-center justify-center rounded-full border border-border bg-card px-7 text-[0.95rem]"
                    >
                      Ricomincia
                    </button>
                  </div>
                </>
              )}

              {phase === "analysis" && (
                <div className="pl-[3.125rem]">
                  <AnalysisSequence onDone={finishAnalysis} />
                </div>
              )}
            </div>
          </div>

          <motion.aside
            className="min-w-0"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2, ease: EASE }}
          >
            <MobilePanel>
              <DecisionProfilePanel
                known={known}
                missing={missing}
                completion={completion}
                confidence={confidence}
                ranking={ranking}
              />
            </MobilePanel>

          </motion.aside>
        </div>
      </main>
    </div>
  );
}

function AnsweredChip({ value }: { value: string | undefined }) {
  return value ? (
    <span className="inline-flex items-center rounded-full border border-primary/35 bg-primary/10 px-4 py-2 text-[0.85rem] text-foreground">
      {value}
    </span>
  ) : null;
}
