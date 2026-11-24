import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Bell } from "lucide-react";
import { EASE } from "@/lib/motion";

const QUESTIONS = [
  "Mi conviene venderla?",
  "Quanto spenderò il prossimo anno?",
  "Qual è il momento migliore per cambiarla?",
  "Mi conviene fare il tagliando in concessionaria?",
];

function Typewriter() {
  const reduce = useReducedMotion();
  const [i, setI] = useState(0);
  const [n, setN] = useState(reduce ? QUESTIONS[0]!.length : 0);

  useEffect(() => {
    if (reduce) return;
    const full = QUESTIONS[i]!;
    if (n < full.length) {
      const t = window.setTimeout(() => setN((v) => v + 1), 55);
      return () => window.clearTimeout(t);
    }
    const t = window.setTimeout(() => {
      setN(0);
      setI((v) => (v + 1) % QUESTIONS.length);
    }, 2200);
    return () => window.clearTimeout(t);
  }, [i, n, reduce]);

  return (
    <div className="rounded-2xl border border-border/70 bg-background/70 px-4 py-3 text-sm text-foreground/80">
      <span>{QUESTIONS[i]!.slice(0, n)}</span>
      <span className="caret-blink ml-0.5 inline-block h-4 w-[2px] translate-y-[2px] bg-primary" />
    </div>
  );
}

export function FeaturePreview({ kind }: { kind: NonNullable<import("@/lib/mydrivewise").Feature["preview"]> }) {
  const reduce = useReducedMotion();
  const grow = (w: number, d: number) => ({
    initial: reduce ? false : { scaleX: 0 },
    whileInView: { scaleX: 1 },
    viewport: { once: true },
    transition: { duration: 0.8, ease: EASE, delay: d },
    style: { width: `${w}%`, transformOrigin: "left" },
  });

  if (kind === "typewriter") return <Typewriter />;

  if (kind === "bars")
    return (
      <div className="flex h-16 items-end gap-1.5">
        {[38, 62, 45, 78, 54, 88, 66].map((h, i) => (
          <motion.span
            key={i}
            className="flex-1 rounded-t-md bg-primary/35"
            initial={reduce ? false : { height: 4 }}
            whileInView={{ height: `${h}%` }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, ease: EASE, delay: i * 0.06 }}
          />
        ))}
      </div>
    );

  if (kind === "timeline")
    return (
      <div className="relative space-y-3 pl-5">
        <span className="absolute top-1 bottom-1 left-[5px] w-px bg-border" />
        {["Tesla Model Y · Score 86", "Kia Sportage · Score 86", "Volvo XC40 · Score 85"].map(
          (t, i) => (
            <motion.div
              key={t}
              className="relative text-xs text-muted-foreground"
              initial={reduce ? false : { opacity: 0, x: -8 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.45, ease: EASE, delay: i * 0.1 }}
            >
              <span className="absolute top-1 -left-5 size-[11px] rounded-full border-2 border-primary bg-card" />
              {t}
            </motion.div>
          ),
        )}
      </div>
    );

  if (kind === "vs")
    return (
      <div className="flex items-center justify-between gap-2">
        {["Tesla", "Kia", "Volvo"].map((b, i) => (
          <div key={b} className="flex flex-1 items-center gap-2">
            <span className="flex-1 rounded-xl border border-border/70 bg-background/70 py-2 text-center text-xs font-semibold">
              {b}
            </span>
            {i < 2 && (
              <motion.span
                className="text-[0.6rem] font-extrabold tracking-widest text-primary-foreground"
                animate={reduce ? {} : { opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 2.2, repeat: Infinity, delay: i * 0.4 }}
              >
                VS
              </motion.span>
            )}
          </div>
        ))}
      </div>
    );

  if (kind === "bell")
    return (
      <div className="flex items-center gap-2 rounded-2xl border border-border/70 bg-background/70 px-3 py-2.5 text-xs text-muted-foreground">
        <motion.span
          className="text-primary"
          animate={reduce ? {} : { rotate: [0, -12, 10, -6, 0] }}
          transition={{ duration: 1.6, repeat: Infinity, repeatDelay: 2.6 }}
        >
          <Bell className="size-4" />
        </motion.span>
        Prezzo in calo su 2 veicoli salvati
      </div>
    );

  if (kind === "line")
    return (
      <svg viewBox="0 0 200 64" className="h-16 w-full">
        <motion.path
          d="M4 14 C 50 22, 80 34, 110 40 S 170 54, 196 58"
          fill="none"
          stroke="var(--color-primary)"
          strokeWidth="2.5"
          strokeLinecap="round"
          initial={reduce ? false : { pathLength: 0 }}
          whileInView={{ pathLength: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1.2, ease: EASE }}
        />
        <path
          d="M4 14 C 50 22, 80 34, 110 40 S 170 54, 196 58"
          fill="none"
          stroke="var(--color-primary)"
          strokeOpacity="0.18"
          strokeWidth="2.5"
        />
      </svg>
    );

  if (kind === "maintenance")
    return (
      <div className="space-y-2">
        {[
          ["Tagliando", "tra 1.200 km"],
          ["Pneumatici", "tra 4 mesi"],
          ["Revisione", "mar 2027"],
        ].map(([a, b], i) => (
          <motion.div
            key={a}
            className="flex items-center gap-2 text-[0.7rem] text-muted-foreground"
            initial={reduce ? false : { opacity: 0, x: -6 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45, ease: EASE, delay: i * 0.09 }}
          >
            <span className="size-1.5 rounded-full bg-primary" />
            <span className="font-medium text-foreground/80">{a}</span>
            <span className="h-px flex-1 bg-border" />
            <span>{b}</span>
          </motion.div>
        ))}
      </div>
    );

  if (kind === "health")
    return (
      <div className="relative rounded-2xl border border-border/70 bg-background/70 px-3 py-3">
        {/* Icona a doppio tratto, coerente con le icone veicolo dello step 1. */}
        <svg viewBox="0 0 56 34" className="h-14 w-full text-foreground" aria-hidden>
          {[
            /* contorno marcato */
            {
              d: "M3.5 25.5v-5.2c0-2.1 1.1-3.4 3.2-3.9l4.8-1.1 4.6-6.4c1.3-1.8 2.8-2.6 5-2.6h11.6c2.1 0 3.8.8 5.2 2.3l5.6 6.1 5.4 1.4c2.3.6 3.4 2 3.4 4.2v5.2",
              w: 1.5,
              o: 1,
              delay: 0,
              color: "currentColor",
            },
            { d: "M20.5 25.5h15", w: 1.5, o: 1, delay: 0.1, color: "currentColor" },
            { d: "M10.6 25.5c0-2.7 2.2-4.9 4.9-4.9s4.9 2.2 4.9 4.9", w: 1.5, o: 1, delay: 0.18, color: "currentColor" },
            { d: "M35.6 25.5c0-2.7 2.2-4.9 4.9-4.9s4.9 2.2 4.9 4.9", w: 1.5, o: 1, delay: 0.24, color: "currentColor" },
            /* dettagli sottili: finestrini e montante */
            { d: "M19.9 9.4l-4.2 5.8h10.2V9.4z", w: 0.75, o: 0.6, delay: 0.5, color: "currentColor" },
            { d: "M28.4 9.4v5.8h11.2l-5.2-5.8z", w: 0.75, o: 0.6, delay: 0.58, color: "currentColor" },
            { d: "M26.9 15.8v9.7", w: 0.75, o: 0.6, delay: 0.66, color: "currentColor" },
            /* accento verde acqua: fari e segnale batteria */
            { d: "M7.6 20.4h4.2", w: 1.4, o: 1, delay: 0.74, color: "var(--color-primary)" },
            { d: "M48.4 20.6h4.1", w: 1.4, o: 1, delay: 0.8, color: "var(--color-primary)" },
          ].map((p, i) => (
            <motion.path
              key={i}
              d={p.d}
              fill="none"
              stroke={p.color}
              strokeWidth={p.w}
              strokeOpacity={p.o}
              strokeLinecap="round"
              strokeLinejoin="round"
              initial={reduce ? false : { pathLength: 0, opacity: 0.2 }}
              whileInView={{ pathLength: 1, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.85, ease: EASE, delay: p.delay }}
            />
          ))}
          {[15.5, 40.5].map((cx, i) => (
            <motion.circle
              key={cx}
              cx={cx}
              cy={25.6}
              r={4.6}
              fill="var(--color-card)"
              stroke="var(--color-primary)"
              strokeWidth={1.5}
              initial={reduce ? false : { pathLength: 0, opacity: 0.2 }}
              whileInView={{ pathLength: 1, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, ease: EASE, delay: 0.3 + i * 0.08 }}
            />
          ))}
          {[15.5, 40.5].map((cx) => (
            <circle key={`h-${cx}`} cx={cx} cy={25.6} r={1.7} fill="none" stroke="currentColor" strokeOpacity={0.4} strokeWidth={0.7} />
          ))}
        </svg>
        <div className="mt-1 flex items-center gap-2 text-[0.68rem] text-muted-foreground">
          <motion.span
            className="size-1.5 rounded-full bg-primary"
            animate={reduce ? {} : { opacity: [1, 0.25, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
          Stato generale ottimo · batteria 94%
        </div>
      </div>
    );

  if (kind === "docs")
    return (
      <div className="space-y-1.5">
        {["Libretto di circolazione", "Polizza RC 2026", "Fattura tagliando"].map((d, i) => (
          <motion.div
            key={d}
            className="flex items-center gap-2 rounded-xl border border-border/70 bg-background/70 px-2.5 py-1.5 text-[0.7rem] text-muted-foreground"
            initial={reduce ? false : { opacity: 0, y: 6 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, ease: EASE, delay: i * 0.08 }}
          >
            <span className="grid size-5 shrink-0 place-items-center rounded-md border border-primary/25 bg-primary/10 text-[0.55rem] font-bold text-primary-foreground">
              PDF
            </span>
            <span className="truncate">{d}</span>
          </motion.div>
        ))}
      </div>
    );

  if (kind === "wishlist")
    return (
      <div className="space-y-2">
        <div className="flex gap-2">
          {["Tesla Model Y", "Kia Sportage", "Volvo XC40"].map((v, i) => (
            <motion.span
              key={v}
              className="flex-1 truncate rounded-xl border border-border/70 bg-background/70 px-2 py-2 text-center text-[0.66rem] font-medium"
              initial={reduce ? false : { opacity: 0, y: 8 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, ease: EASE, delay: i * 0.08 }}
            >
              {v}
            </motion.span>
          ))}
        </div>
        <div className="flex items-center gap-2 text-[0.68rem] text-muted-foreground">
          <motion.span
            className="text-primary"
            animate={reduce ? {} : { rotate: [0, -12, 10, -6, 0] }}
            transition={{ duration: 1.6, repeat: Infinity, repeatDelay: 2.6 }}
          >
            <Bell className="size-3.5" />
          </motion.span>
          Prezzo in calo su 2 veicoli salvati
        </div>
      </div>
    );

  if (kind === "badges")
    return (
      <div className="flex flex-wrap gap-2">
        {["Prima decisione", "-1.240 € risparmiati", "3 analisi"].map((b) => (
          <span
            key={b}
            className="rounded-full border border-primary/25 bg-primary/8 px-3 py-1 text-[0.68rem] font-medium text-primary-foreground"
          >
            {b}
          </span>
        ))}
      </div>
    );

  if (kind === "stats")
    return (
      <div className="space-y-2">
        {[
          ["Km percorsi", 72],
          ["Spesa totale", 54],
          ["Decision Score medio", 88],
        ].map(([label, w], i) => (
          <div key={label as string} className="space-y-1">
            <div className="flex justify-between text-[0.68rem] text-muted-foreground">
              <span>{label as string}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-border/70">
              <motion.div className="h-full rounded-full bg-primary" {...grow(w as number, i * 0.1)} />
            </div>
          </div>
        ))}
      </div>
    );

  // smart
  return (
    <motion.div
      className="rounded-2xl border border-primary/30 bg-primary/8 px-4 py-3 text-sm text-foreground/85"
      initial={reduce ? false : { opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6, ease: EASE, delay: 0.25 }}
    >
      «Il nuovo <strong className="font-semibold">Tesla Model Y</strong> migliora del{" "}
      <strong className="font-semibold text-primary">17%</strong> il tuo Decision Score rispetto al
      tuo attuale veicolo.»
    </motion.div>
  );
}