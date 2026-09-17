import { useEffect, useRef } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { EASE } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { stepThemes, tintClasses } from "@/lib/wizard-theme";

/** Motivo di sfondo discreto, diverso per tema della domanda. */
function Motif({ kind, tint }: { kind: string; tint: string }) {
  const stroke = tint === "accent" ? "var(--accent)" : "var(--primary)";
  return (
    <svg
      aria-hidden
      viewBox="0 0 400 160"
      preserveAspectRatio="none"
      className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.09]"
    >
      {kind === "waves" &&
        [0, 1, 2].map((i) => (
          <path
            key={i}
            d={`M0 ${50 + i * 34} C 80 ${20 + i * 34}, 150 ${86 + i * 34}, 240 ${50 + i * 34} S 360 ${18 + i * 34}, 400 ${46 + i * 34}`}
            fill="none"
            stroke={stroke}
            strokeWidth="1"
          />
        ))}
      {kind === "rings" &&
        [30, 56, 82, 108].map((r) => (
          <circle key={r} cx="352" cy="24" r={r} fill="none" stroke={stroke} strokeWidth="1" />
        ))}
      {kind === "grid" &&
        [...Array(10)].map((_, i) => (
          <g key={i}>
            <line x1={i * 44} y1="0" x2={i * 44} y2="160" stroke={stroke} strokeWidth="0.7" />
            <line x1="0" y1={i * 20} x2="400" y2={i * 20} stroke={stroke} strokeWidth="0.7" />
          </g>
        ))}
      {kind === "bars" &&
        [...Array(14)].map((_, i) => (
          <rect
            key={i}
            x={12 + i * 28}
            y={150 - ((i * 37) % 110) - 12}
            width="9"
            height={((i * 37) % 110) + 12}
            fill={stroke}
            opacity="0.7"
          />
        ))}
    </svg>
  );
}

type Props = {
  themeId: keyof typeof stepThemes | string;
  active?: boolean;
  children: React.ReactNode;
};

/**
 * Contenitore di uno step: dà al blocco una identità (eyebrow, icona, tinta,
 * micro-illustrazione) senza cambiare il linguaggio grafico del prodotto.
 */
export function StepStage({ themeId, active = true, children }: Props) {
  const reduce = useReducedMotion();
  const theme = stepThemes[themeId] ?? stepThemes["facts"]!;
  const t = tintClasses[theme.tint];
  const Icon = theme.icon;
  const ref = useRef<HTMLElement | null>(null);

  // La pagina segue il focus della conversazione: quando uno step diventa
  // attivo viene portato in posizione di lettura comoda, con scroll fluido.
  useEffect(() => {
    if (!active) return;
    const node = ref.current;
    if (!node) return;
    const id = window.setTimeout(() => {
      const rect = node.getBoundingClientRect();
      const target = window.scrollY + rect.top - Math.max(96, window.innerHeight * 0.22);
      window.scrollTo({
        top: Math.max(0, target),
        behavior: reduce ? "auto" : "smooth",
      });
    }, 220);
    return () => window.clearTimeout(id);
  }, [active, reduce]);

  return (
    <motion.section
      ref={ref}
      initial={{ opacity: 0, y: 14, filter: reduce ? "none" : "blur(6px)" }}
      animate={{
        opacity: active ? 1 : 0.55,
        y: 0,
        scale: active || reduce ? 1 : 0.97,
        filter: "blur(0px)",
      }}
      transition={{ duration: 0.55, ease: EASE }}
      style={{ transformOrigin: "top center" }}
      className={cn(
        "relative overflow-hidden rounded-3xl border bg-card/70 p-5 backdrop-blur-[2px] transition-all duration-500 sm:p-6",
        active
          ? cn(
              t.ring,
              "shadow-[var(--shadow-object),0_0_0_4px_color-mix(in_oklab,var(--color-primary)_10%,transparent)]",
            )
          : "border-border/60 shadow-[var(--shadow-soft)]",
      )}
    >
      {active && <Motif kind={theme.motif} tint={theme.tint} />}
      <div className="relative">
        <div className="mb-4 flex items-center gap-2.5">
          <span className={cn("grid size-7 place-items-center rounded-full", t.soft)}>
            <Icon className="size-3.5" />
          </span>
          <span className="text-[0.68rem] font-medium tracking-[0.16em] text-muted-foreground uppercase">
            {theme.eyebrow}
          </span>
          <span className="hidden text-[0.75rem] text-muted-foreground sm:inline">
            · {theme.hint}
          </span>
        </div>
        <motion.div
          initial="hidden"
          animate="show"
          variants={{ hidden: {}, show: { transition: { staggerChildren: 0.08 } } }}
          className="space-y-5"
        >
          {children}
        </motion.div>
      </div>
    </motion.section>
  );
}
