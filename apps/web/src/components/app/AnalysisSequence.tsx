import { useEffect, useMemo, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { EASE } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { analysisPhases } from "@/lib/wizard-theme";
import { useCountUp } from "@/lib/use-count-up";

/** Check che si "disegna" al completamento della fase. */
function DrawnCheck({ active }: { active: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
      <motion.path
        d="M5 12.5 10 17.5 19 7"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: active ? 1 : 0 }}
        transition={{ duration: 0.45, ease: EASE }}
      />
    </svg>
  );
}

/** Anello di avanzamento, stesso linguaggio del Compatibility Score dell'hero. */
function ProgressRing({ value }: { value: number }) {
  const r = 46;
  const c = 2 * Math.PI * r;
  const shown = useCountUp(value, 500);
  return (
    <div className="relative grid size-[7.5rem] shrink-0 place-items-center">
      <svg viewBox="0 0 110 110" className="size-full -rotate-90">
        <circle cx="55" cy="55" r={r} fill="none" stroke="currentColor" strokeWidth="6" className="text-muted" />
        <motion.circle
          cx="55"
          cy="55"
          r={r}
          fill="none"
          stroke="var(--primary)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={c}
          animate={{ strokeDashoffset: c * (1 - value / 100) }}
          transition={{ duration: 0.6, ease: EASE }}
        />
      </svg>
      <div className="absolute text-center">
        <span className="font-heading text-[1.6rem] font-bold tabular-nums text-foreground">{shown}%</span>
        <span className="block text-[0.62rem] tracking-[0.14em] text-muted-foreground uppercase">Analisi</span>
      </div>
    </div>
  );
}

export function AnalysisSequence({
  steps,
  onDone,
}: {
  steps?: string[];
  onDone: () => void;
}) {
  const reduce = useReducedMotion();
  const phases = useMemo(
    () => (steps?.length ? analysisPhases.slice(0, steps.length) : analysisPhases),
    [steps],
  );
  const [done, setDone] = useState(0);
  const doneRef = useRef(onDone);
  doneRef.current = onDone;

  useEffect(() => {
    const total = reduce ? 600 : 6200;
    const each = total / phases.length;
    const timers = phases.map((_, i) =>
      window.setTimeout(() => setDone(i + 1), each * (i + 1)),
    );
    const end = window.setTimeout(() => doneRef.current(), total + 500);
    return () => {
      timers.forEach(clearTimeout);
      clearTimeout(end);
    };
  }, [phases, reduce]);

  const pct = Math.round((done / phases.length) * 100);
  const params = useCountUp(Math.round(done * 148 + (done ? 37 : 0)), 700, !!reduce);

  return (
    <div className="relative overflow-hidden rounded-3xl border border-primary/25 bg-card/80 p-5 shadow-[var(--shadow-object)] backdrop-blur-[2px] sm:p-7">
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -top-24 -right-16 size-64 rounded-full bg-primary/10 blur-3xl"
        animate={reduce ? {} : { opacity: [0.4, 0.8, 0.4], scale: [1, 1.08, 1] }}
        transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center">
        <ProgressRing value={pct} />
        <div className="min-w-0">
          <p className="font-heading text-[1.1rem] font-semibold text-foreground">
            DriveWise sta elaborando la tua decisione
          </p>
          <p className="mt-1 text-[0.85rem] text-muted-foreground">
            <span className="tabular-nums">{params}</span> parametri confrontati su dataset
            tecnici, costi reali e affidabilità.
          </p>
        </div>
      </div>

      <ul className="relative mt-7 space-y-2">
        {phases.map((p, i) => {
          const complete = i < done;
          const current = i === done;
          const Icon = p.icon;
          return (
            <motion.li
              key={p.label}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: complete ? 1 : current ? 0.95 : 0.38, y: 0 }}
              transition={{ duration: 0.4, ease: EASE }}
              className={cn(
                "flex items-center gap-3 rounded-2xl border px-3.5 py-2.5 transition-colors duration-500",
                current
                  ? "border-primary/30 bg-primary/[0.06]"
                  : "border-transparent bg-transparent",
              )}
            >
              <span
                className={cn(
                  "grid size-7 shrink-0 place-items-center rounded-full transition-colors duration-500",
                  complete ? "bg-primary/20 text-foreground" : "bg-muted text-muted-foreground",
                )}
              >
                {complete ? <DrawnCheck active /> : <Icon className="size-3.5" />}
              </span>
              <span className="min-w-0 flex-1">
                <span
                  className={cn(
                    "block truncate text-[0.9rem]",
                    complete || current ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  {p.label}
                </span>
                {current && (
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="block text-[0.72rem] text-muted-foreground"
                  >
                    {p.detail}
                  </motion.span>
                )}
              </span>
              {current && !reduce && (
                <span className="flex items-center gap-1">
                  {[0, 1, 2].map((d) => (
                    <motion.span
                      key={d}
                      className="size-1 rounded-full bg-primary"
                      animate={{ opacity: [0.25, 1, 0.25] }}
                      transition={{ duration: 1, repeat: Infinity, delay: d * 0.16 }}
                    />
                  ))}
                </span>
              )}
            </motion.li>
          );
        })}
      </ul>
    </div>
  );
}
