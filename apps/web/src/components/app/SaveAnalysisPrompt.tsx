import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import { AuthDialog } from "@/components/auth/AuthDialog";
import { useAuthSession } from "@/hooks/use-auth-session";
import { EASE } from "@/lib/motion";
import {
  clearPendingAnalysis,
  getPendingAnalysis,
  saveAnalysis,
  setPendingAnalysis,
  type AnalysisDraft,
} from "@/lib/saved-analyses";
import { cn } from "@/lib/utils";

/** Check che si disegna alla conferma di salvataggio. */
function DoneCheck() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
      <motion.path d="M5 12.5 10 17.5 19 7" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.45, ease: EASE }} />
    </svg>
  );
}

/** Anteprima compatta dell'analisi: veicolo, punteggio, tag chiave. */
function AnalysisPreview({ draft, className }: { draft: AnalysisDraft; className?: string }) {
  return (
    <div className={cn("flex items-center gap-4 rounded-2xl border border-border/70 bg-background/70 px-4 py-3", className)}>
      <span className="font-heading shrink-0 text-[1.6rem] leading-none font-extrabold tabular-nums text-primary">
        {draft.score}
      </span>
      <span className="min-w-0">
        <span className="block truncate text-[0.9rem] font-medium">
          {draft.brand} {draft.model}
        </span>
        <span className="mt-1 flex flex-wrap gap-1.5">
          {draft.tags.slice(0, 3).map((t) => (
            <span
              key={t}
              className="rounded-full border border-border/70 px-2 py-0.5 text-[0.68rem] text-muted-foreground first-letter:uppercase"
            >
              {t}
            </span>
          ))}
        </span>
      </span>
    </div>
  );
}

/** Anteprima "ghost" del contatore analisi: 18 → 19. */
function GhostCounter({ from }: { from: number }) {
  const reduce = useReducedMotion();
  return (
    <span className="inline-flex items-center gap-1.5 text-[0.72rem] text-muted-foreground">
      Analisi effettuate
      <span className="tabular-nums text-foreground/80">{from}</span>
      <motion.span
        className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/8 px-1.5 py-0.5 text-primary tabular-nums"
        animate={reduce ? {} : { opacity: [0.45, 1, 0.45], y: [0.5, -1, 0.5] }}
        transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
      >
        <ArrowRight className="size-3" />
        {from + 1}
      </motion.span>
    </span>
  );
}

export function SaveAnalysisPrompt({
  draft,
  baseCount = 18,
  delayMs = 5200,
}: {
  draft: AnalysisDraft;
  baseCount?: number;
  delayMs?: number;
}) {
  const reduce = useReducedMotion();
  const { user, ready } = useAuthSession();
  const [visible, setVisible] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [authOpen, setAuthOpen] = useState(false);
  const saving = useRef(false);

  useEffect(() => {
    const t = window.setTimeout(() => setVisible(true), reduce ? 800 : delayMs);
    return () => window.clearTimeout(t);
  }, [delayMs, reduce]);

  const persist = useCallback(
    async (userId: string, payload: AnalysisDraft) => {
      if (saving.current) return;
      saving.current = true;
      setState("saving");
      try {
        await saveAnalysis(payload, userId);
        clearPendingAnalysis();
        setState("saved");
        window.setTimeout(() => setDismissed(true), 2600);
      } catch {
        setState("error");
      }
      saving.current = false;
    },
    [],
  );

  // Dopo il login l'analisi in sospeso si salva da sola.
  useEffect(() => {
    if (!ready || !user || state !== "idle") return;
    const pending = getPendingAnalysis();
    if (!pending) return;
    setAuthOpen(false);
    setVisible(true);
    void persist(user.id, pending);
  }, [ready, user, state, persist]);

  const onSave = () => {
    if (!user) {
      setPendingAnalysis(draft);
      setAuthOpen(true);
      return;
    }
    void persist(user.id, draft);
  };

  return (
    <>
      <AnimatePresence>
        {visible && !dismissed && (
          <motion.div
            initial={reduce ? { opacity: 0 } : { opacity: 0, y: 60 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, y: 40 }}
            transition={{ duration: 0.6, ease: EASE }}
            className="fixed inset-x-0 bottom-0 z-50 flex justify-center px-4 pb-5"
          >
            <div className="relative w-full max-w-[38rem] overflow-hidden rounded-[1.75rem] border border-primary/25 bg-card/80 p-5 shadow-[var(--shadow-object)] backdrop-blur-xl sm:p-6">
              <p className="mb-2 text-xs text-muted-foreground">Salvataggio demo, solo in questo browser.</p>
              <motion.span
                aria-hidden
                className="pointer-events-none absolute -top-20 -right-14 size-52 rounded-full bg-primary/12 blur-3xl"
                animate={reduce ? {} : { opacity: [0.5, 0.9, 0.5], scale: [1, 1.08, 1] }}
                transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
              />

              {state === "saved" ? (
                <div className="relative flex items-center gap-3">
                  <motion.span
                    initial={{ scale: 0.85 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 0.45, ease: EASE }}
                    className="grid size-9 shrink-0 place-items-center rounded-full bg-primary/18 text-primary shadow-[0_0_30px_-8px_var(--color-primary)]"
                  >
                    <DoneCheck />
                  </motion.span>
                  <span className="min-w-0">
                    <span className="block text-[0.95rem] font-medium">Analisi salvata nel tuo profilo.</span>
                    <span className="block text-[0.8rem] text-muted-foreground">
                      La trovi in My DriveWise → Decision History.
                    </span>
                  </span>
                </div>
              ) : (
                <div className="relative">
                  <div className="flex items-start gap-2.5">
                    <Sparkles className="mt-0.5 size-4 shrink-0 text-primary" />
                    <p className="text-[0.95rem] leading-relaxed">
                      Vuoi salvare questa analisi nel tuo profilo?{" "}
                      <span className="text-muted-foreground">
                        Continuerà a migliorare i tuoi consigli futuri.
                      </span>
                    </p>
                  </div>

                  <AnalysisPreview draft={draft} className="mt-4" />

                  <div className="mt-3">
                    <GhostCounter from={baseCount} />
                  </div>

                  {state === "error" && (
                    <p className="mt-3 text-[0.78rem] text-destructive">
                      Salvataggio non riuscito. Riprova fra un istante.
                    </p>
                  )}

                  <div className="mt-5 flex items-center gap-4">
                    <button
                      type="button"
                      onClick={onSave}
                      disabled={state === "saving"}
                      className="inline-flex h-11 items-center gap-2 rounded-full bg-primary px-6 text-[0.92rem] font-medium text-primary-foreground shadow-[var(--shadow-soft)] transition-all duration-300 hover:bg-primary-hover disabled:opacity-60"
                    >
                      {state === "saving" && <Loader2 className="size-4 animate-spin" />}
                      Salva analisi
                    </button>
                    <button
                      type="button"
                      onClick={() => setDismissed(true)}
                      className="text-[0.85rem] text-muted-foreground transition-colors hover:text-foreground"
                    >
                      Non ora
                    </button>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AuthDialog
        open={authOpen}
        onClose={() => setAuthOpen(false)}
        preview={<AnalysisPreview draft={draft} />}
      />
    </>
  );
}