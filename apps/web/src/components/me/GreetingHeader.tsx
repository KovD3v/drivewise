import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Moon, Sun, Sunrise } from "lucide-react";
import { METRICS } from "@/lib/mydrivewise";
import { EASE } from "@/lib/motion";

function timeOfDay() {
  const h = new Date().getHours();
  if (h < 13) return "morning" as const;
  if (h < 18) return "afternoon" as const;
  return "evening" as const;
}

const LABEL = {
  morning: "Buongiorno",
  afternoon: "Buon pomeriggio",
  evening: "Buonasera",
};

const ICON = { morning: Sunrise, afternoon: Sun, evening: Moon };

const AMBIENT = {
  morning:
    "radial-gradient(60% 80% at 18% 20%, color-mix(in oklab, var(--color-primary) 16%, transparent), transparent 70%), radial-gradient(50% 70% at 75% 10%, color-mix(in oklab, var(--color-accent) 10%, transparent), transparent 70%)",
  afternoon:
    "radial-gradient(60% 80% at 30% 30%, color-mix(in oklab, var(--color-primary) 13%, transparent), transparent 70%), radial-gradient(50% 70% at 80% 20%, color-mix(in oklab, var(--color-accent) 9%, transparent), transparent 70%)",
  evening:
    "radial-gradient(60% 80% at 22% 35%, color-mix(in oklab, var(--color-accent) 14%, transparent), transparent 70%), radial-gradient(55% 75% at 78% 10%, color-mix(in oklab, var(--color-primary) 10%, transparent), transparent 70%)",
};

function insights() {
  const profile = METRICS.find((m) => m.label === "Decision Profile")?.value ?? 92;
  const decisions = METRICS.find((m) => m.label === "Decisioni effettuate")?.value ?? 3;
  const analyses = METRICS.find((m) => m.label === "Analisi effettuate")?.value ?? 18;
  const saved = METRICS.find((m) => m.label === "Veicoli salvati")?.value ?? 7;
  return [
    `Il tuo Decision Profile è al ${profile}% — tra i più alti degli ultimi 30 giorni.`,
    `Hai preso ${decisions} decisioni informate questo mese.`,
    `${analyses} analisi completate e ${saved} veicoli sotto osservazione.`,
  ];
}

const NAME = "Ciao Andrea";

export function GreetingHeader() {
  const reduce = useReducedMotion();
  const [tod, setTod] = useState<"morning" | "afternoon" | "evening">("morning");
  const Icon = ICON[tod];
  const [insight, setInsight] = useState(() => insights()[0]!);

  useEffect(() => {
    setTod(timeOfDay());
    const list = insights();
    setInsight(list[Math.floor(Math.random() * list.length)]!);
  }, []);

  return (
    <div className="relative isolate overflow-x-clip">
      {/* ambient gradient */}
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -inset-x-16 -top-20 -bottom-10 -z-10 opacity-70"
        style={{ background: AMBIENT[tod], filter: "blur(30px)" }}
        animate={reduce ? {} : { scale: [1, 1.06, 1], x: [0, 14, 0], y: [0, -10, 0] }}
        transition={{ duration: 26, ease: "easeInOut", repeat: Infinity }}
      />
      {/* floating blob */}
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -z-10 right-[8%] top-[-2rem] size-64 rounded-full opacity-[0.09]"
        style={{
          background:
            "radial-gradient(circle at 35% 35%, var(--color-primary), transparent 65%)",
          filter: "blur(18px)",
        }}
        animate={reduce ? {} : { y: [0, 24, 0], x: [0, -18, 0], scale: [1, 1.12, 1] }}
        transition={{ duration: 32, ease: "easeInOut", repeat: Infinity }}
      />

      <motion.p
        initial={reduce ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: EASE, delay: 0.05 }}
        className="inline-flex items-center gap-2 text-[0.72rem] tracking-[0.16em] text-muted-foreground uppercase"
      >
        <Icon className="size-3.5" strokeWidth={1.6} />
        {LABEL[tod]}
      </motion.p>

      <h1 className="mt-3 flex flex-wrap items-center gap-x-4 font-heading text-4xl font-extrabold tracking-tight sm:text-5xl">
        <span className="sr-only">{NAME}</span>
        <span aria-hidden className="flex">
          {NAME.split("").map((c, i) => (
            <motion.span
              key={i}
              className="inline-block whitespace-pre"
              initial={
                reduce
                  ? false
                  : {
                      opacity: 0,
                      filter: "blur(10px)",
                      y: (i % 2 ? 1 : -1) * (6 + (i % 5) * 2),
                      x: (i % 3 ? -1 : 1) * 6,
                    }
              }
              animate={{ opacity: 1, filter: "blur(0px)", y: 0, x: 0 }}
              transition={{ duration: 0.65, ease: EASE, delay: 0.12 + i * 0.035 }}
            >
              {c}
            </motion.span>
          ))}
        </span>
        <PulseRing reduce={!!reduce} />
      </h1>

      <motion.p
        initial={reduce ? false : { opacity: 0, y: 10, filter: "blur(6px)" }}
        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        transition={{ duration: 0.6, ease: EASE, delay: 0.75 }}
        className="mt-4 max-w-xl text-lg text-muted-foreground"
      >
        {insight}
      </motion.p>
    </div>
  );
}

function PulseRing({ reduce }: { reduce: boolean }) {
  return (
    <span className="relative grid size-9 shrink-0 place-items-center" aria-hidden>
      <motion.span
        className="absolute inset-0 rounded-full border border-primary/40"
        animate={reduce ? {} : { scale: [1, 1.45], opacity: [0.5, 0] }}
        transition={{ duration: 2.6, ease: "easeOut", repeat: Infinity }}
      />
      <svg viewBox="0 0 36 36" className="size-9 -rotate-90">
        <circle cx="18" cy="18" r="15" fill="none" stroke="var(--color-primary)" strokeOpacity="0.18" strokeWidth="2.5" />
        <motion.circle
          cx="18"
          cy="18"
          r="15"
          fill="none"
          stroke="var(--color-primary)"
          strokeWidth="2.5"
          strokeLinecap="round"
          initial={reduce ? false : { pathLength: 0 }}
          animate={{ pathLength: 0.92 }}
          transition={{ duration: 1.3, ease: EASE, delay: 0.6 }}
        />
      </svg>
      <motion.span
        className="absolute size-1.5 rounded-full bg-primary"
        animate={reduce ? {} : { opacity: [0.35, 1, 0.35], scale: [0.9, 1.15, 0.9] }}
        transition={{ duration: 2.6, ease: "easeInOut", repeat: Infinity }}
      />
    </span>
  );
}
