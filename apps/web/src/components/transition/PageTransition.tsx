import { useEffect, useMemo } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { EASE } from "@/lib/motion";
import { endAppTransition, useAppTransition } from "@/lib/app-transition";

const DEFAULT_STEPS = ["Analisi in corso...", "Preparazione profilo...", "Pronto."];
// 260ms cover, route swap behind the opaque layer, then destination reveal.
const DURATION = 1380;

/** Particelle luminose che si propagano dal punto premuto. */
function Particles({ x, y }: { x: number; y: number }) {
  const parts = useMemo(
    () =>
      Array.from({ length: 26 }, (_, i) => {
        const angle = (i / 26) * Math.PI * 2 + Math.random() * 0.4;
        const dist = 120 + Math.random() * 280;
        return {
          i,
          dx: Math.cos(angle) * dist,
          dy: Math.sin(angle) * dist,
          size: 3 + Math.random() * 4,
          delay: Math.random() * 0.12,
        };
      }),
    [],
  );

  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-[95]">
      {parts.map((p) => (
        <motion.span
          key={p.i}
          className="absolute rounded-full bg-primary"
          style={{
            left: x,
            top: y,
            width: p.size,
            height: p.size,
            boxShadow: "0 0 12px var(--color-primary)",
          }}
          initial={{ opacity: 0.9, x: 0, y: 0, scale: 1 }}
          animate={{ opacity: 0, x: p.dx, y: p.dy, scale: 0.3 }}
          transition={{ duration: 0.55, delay: p.delay, ease: "easeOut" }}
        />
      ))}
    </div>
  );
}

export function PageTransition() {
  const { active, origin, id, steps } = useAppTransition();
  const messages = steps?.length ? steps : DEFAULT_STEPS;
  const reduce = useReducedMotion();

  useEffect(() => {
    if (!active) return;
    const t = window.setTimeout(endAppTransition, DURATION);
    return () => window.clearTimeout(t);
  }, [active, id]);

  if (reduce) return null;

  return (
    <AnimatePresence>
      {active && (
        <motion.div
          key={id}
          className="pointer-events-none fixed inset-0 z-[90]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{
            duration: 0.24,
            ease: EASE,
          }}
        >
          {origin && <Particles x={origin.x} y={origin.y} />}

          <div className="absolute inset-0 bg-foreground/95" />
          <div className="absolute inset-0 bg-[radial-gradient(110%_110%_at_50%_45%,color-mix(in_oklab,var(--color-primary)_35%,transparent),transparent_70%)]" />

          <div className="absolute inset-0 grid place-items-center">
            <div className="flex flex-col items-center gap-5">
              <div className="relative size-24">
                <svg viewBox="0 0 100 100" className="size-full -rotate-90">
                  <circle
                    cx="50"
                    cy="50"
                    r="44"
                    fill="none"
                    stroke="var(--color-primary)"
                    strokeOpacity="0.2"
                    strokeWidth="4"
                  />
                  <motion.circle
                    cx="50"
                    cy="50"
                    r="44"
                    fill="none"
                    stroke="var(--color-primary)"
                    strokeWidth="4"
                    strokeLinecap="round"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 1.08, ease: "easeInOut" }}
                    style={{ filter: "drop-shadow(0 0 8px var(--color-primary))" }}
                  />
                </svg>
              </div>

              <div className="relative h-5 w-56 overflow-hidden text-center">
                {messages.map((s, i) => (
                  <motion.span
                    key={s}
                    className="absolute inset-x-0 text-[0.78rem] tracking-[0.14em] text-background uppercase"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: [0, 1, 1, 0], y: [8, 0, 0, -6] }}
                    transition={{
                      duration: 0.52,
                      delay: i * 0.36,
                      times: [0, 0.25, 0.7, 1],
                      ease: EASE,
                    }}
                  >
                    {s}
                  </motion.span>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
