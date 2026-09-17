import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useNavigate } from "@tanstack/react-router";
import { ArrowRight, Mic } from "lucide-react";
import { cn } from "@/lib/utils";
import { EASE } from "@/lib/motion";
import { saveInitialQuery, track } from "@/lib/analytics";

const suggestions = [
  "Cerco un SUV per la famiglia",
  "Vorrei una moto per iniziare",
  "Cerco un'auto affidabile sotto i 30.000 €",
  "Quanto costa davvero mantenere una Tesla?",
];

export function DecisionBar() {
  const [value, setValue] = useState("");
  const [focused, setFocused] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [handoff, setHandoff] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);
  const reduce = useReducedMotion();
  const timers = useRef<number[]>([]);
  const navigate = useNavigate();

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const runSubmit = () => {
    if (analyzing || handoff) return;
    const text = value.trim();
    if (text) {
      saveInitialQuery(text);
      track("landing_decision_bar_submit", { length: text.length });
    } else {
      track("landing_start_cta_click", { source: "decision_bar_empty" });
    }
    // Handoff: la barra resta identica, riceve solo un focus leggerissimo.
    setHandoff(true);
    setFocused(true);
    // La navigazione parte subito: nessun handler può "mangiare" il primo click.
    void navigate({ to: "/app/start" });
  };

  const pickSuggestion = (s: string) => {
    setValue(s);
    setFlash(s);
    timers.current.push(window.setTimeout(() => setFlash(null), 500));
  };

  return (
    <div id="decision-bar" className="relative scroll-mt-28">
      <motion.div
        aria-hidden
        animate={{ opacity: focused || analyzing ? 0.32 : 0 }}
        transition={{ duration: 0.9, ease: EASE }}
        className="pointer-events-none absolute inset-x-10 -inset-y-5 rounded-[4rem] bg-primary/12 blur-[60px]"
      />

      <motion.form
        onSubmit={(e) => {
          e.preventDefault();
          runSubmit();
        }}
        animate={{ scale: handoff && !reduce ? 1.006 : analyzing && !reduce ? 0.99 : 1 }}
        whileHover={{ scale: reduce ? 1 : 1.005 }}
        transition={{ duration: 0.25, ease: EASE }}
        role="search"
        className={cn(
          "relative flex items-center gap-2 rounded-full border bg-card p-3 pl-4 transition-[border-color,box-shadow] duration-700 sm:gap-3 sm:p-3.5 sm:pl-7",
          "before:pointer-events-none before:absolute before:inset-px before:rounded-full before:bg-gradient-to-b before:from-background/70 before:to-transparent before:opacity-60",
          focused || analyzing || handoff
            ? "border-primary/40 shadow-[var(--shadow-focus),var(--shadow-object)]"
            : "border-border/55 shadow-[var(--shadow-object)] hover:border-border/80",
        )}
      >
        <button
          type="button"
          aria-label="Parla con DriveWise"
          onClick={() => window.alert("Demo: input vocale non ancora disponibile.")}
          className="relative z-10 grid size-11 shrink-0 place-items-center rounded-full text-muted-foreground transition-colors duration-300 hover:bg-muted hover:text-foreground"
        >
          <Mic className="size-[1.2rem]" />
        </button>
        <label htmlFor="decision-input" className="sr-only">
          Raccontami cosa stai cercando
        </label>
        <div className="relative z-10 flex h-16 min-w-0 flex-1 items-center sm:h-[4.5rem]">
          <AnimatePresence mode="wait" initial={false}>
            {analyzing ? (
              <motion.div
                key="analyzing"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.3, ease: EASE }}
                className="flex items-center gap-3 text-[1.0625rem] text-muted-foreground sm:text-[1.25rem]"
              >
                <span>Sto analizzando la tua richiesta…</span>
                <AnalysisDots />
              </motion.div>
            ) : (
              <motion.div
                key="input"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25 }}
                className="relative flex h-full w-full min-w-0 items-center"
              >
              {!value && !focused && (
                <span
                  aria-hidden
                  className="pointer-events-none absolute inset-y-0 left-0 flex items-center text-[1.0625rem] text-foreground/45 sm:text-[1.25rem]"
                >
                  Raccontami cosa stai cercando...
                  <span className="caret-blink ml-[3px] inline-block h-[1.1em] w-[2px] translate-y-[0.05em] bg-primary" />
                </span>
              )}
              <input
                id="decision-input"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onFocus={() => setFocused(true)}
                onBlur={() => setFocused(false)}
                placeholder="Raccontami cosa stai cercando..."
                className="relative h-full w-full min-w-0 bg-transparent text-[1.0625rem] text-foreground outline-none placeholder:text-transparent sm:text-[1.25rem]"
              />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <motion.button
          type="submit"
          animate={{
            opacity: value.trim() || analyzing ? 1 : 0.9,
            scale: handoff && !reduce ? 0.985 : value.trim() && !reduce ? 1.02 : 1,
          }}
          whileTap={{ scale: reduce ? 1 : 0.98 }}
          transition={{ duration: 0.3, ease: EASE }}
          className={cn(
            "relative z-10 inline-flex h-16 shrink-0 items-center gap-2 rounded-full bg-primary px-6 text-sm font-medium text-primary-foreground transition-[background-color,box-shadow] duration-300 hover:bg-primary-hover sm:h-[4.5rem] sm:px-9 sm:text-[1rem]",
            (value.trim() || handoff) && "shadow-[var(--shadow-lift)]",
            handoff && "bg-primary-hover",
          )}
        >
          <span className="hidden sm:inline">Inizia</span>
          <motion.span
            animate={handoff && !reduce ? { x: 5 } : value.trim() && !reduce ? { x: [0, 3, 0] } : { x: 0 }}
            transition={{ duration: 0.5, ease: EASE }}
            className="inline-flex"
          >
            <ArrowRight className="size-4" />
          </motion.span>
        </motion.button>
      </motion.form>

      <div className="mt-8 flex flex-wrap justify-center gap-2.5">
        {suggestions.map((s, i) => (
          <motion.button
            key={s}
            type="button"
            onClick={() => pickSuggestion(s)}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            whileTap={{ scale: reduce ? 1 : 0.98 }}
            transition={{ delay: 1 + i * 0.08, duration: 0.6, ease: EASE }}
            className={cn(
              "rounded-full border bg-card/70 px-4 py-2 text-[0.8125rem] backdrop-blur transition-all duration-300 hover:-translate-y-px hover:border-primary/40 hover:text-foreground",
              flash === s
                ? "border-primary/60 text-foreground shadow-[var(--shadow-focus)]"
                : "border-border/70 text-muted-foreground",
            )}
          >
            {s}
          </motion.button>
        ))}
      </div>

      <p className="sr-only" aria-live="polite">
        {analyzing ? "Sto analizzando la tua richiesta" : ""}
      </p>
    </div>
  );
}

/** Three soft indicators used while DriveWise "thinks". Reused by the demo. */
export function AnalysisDots({ className }: { className?: string }) {
  const reduce = useReducedMotion();
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)} aria-hidden>
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="size-1.5 rounded-full bg-primary"
          animate={reduce ? { opacity: 0.6 } : { opacity: [0.25, 1, 0.25] }}
          transition={{ duration: 1.1, repeat: Infinity, delay: i * 0.18, ease: "easeInOut" }}
        />
      ))}
    </span>
  );
}