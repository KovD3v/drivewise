import { useEffect, useRef, useState } from "react";
import { motion, useMotionValue, useReducedMotion, useSpring } from "framer-motion";
import heroVision from "@/assets/hero-ai-vision.jpg";
import { EASE as ease } from "@/lib/motion";
import { useCountUp } from "@/lib/use-count-up";

/** Wireframe vehicles already present in the artwork (% of frame). */
const detections = [
  { id: "auto-tr", label: "Auto rilevata", left: 65, top: 12.5, width: 30, height: 11, at: 0.18 },
  { id: "moto", label: "Moto rilevata", left: 7, top: 37.5, width: 18, height: 12, at: 0.43 },
  {
    id: "scooter",
    label: "Scooter rilevato",
    left: 75,
    top: 39.5,
    width: 20,
    height: 13,
    at: 0.46,
  },
];

/** Circular "Compatibility Score" ring baked into the artwork (% of frame). */
const RING = { left: 28, top: 9.1, size: 46 };
const TARGET_SCORE = 92;

const SCAN_DURATION = 8.0;
const START_DELAY = 500;
const ANALYZE_MS = 900;
const HOLD_MS = 4000;
const FADE_MS = 1100;

export function HeroVision() {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const [phase, setPhase] = useState<"idle" | "scanning" | "analyzing" | "done">(
    reduce ? "done" : "idle",
  );
  const [cycle, setCycle] = useState(0);

  // Pointer parallax (desktop pointers only).
  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const sx = useSpring(mx, { stiffness: 90, damping: 20, mass: 0.4 });
  const sy = useSpring(my, { stiffness: 90, damping: 20, mass: 0.4 });

  useEffect(() => {
    if (reduce) {
      setPhase("done");
      return;
    }
    const t: number[] = [];
    const delay = cycle === 0 ? START_DELAY : FADE_MS;
    t.push(window.setTimeout(() => setPhase("scanning"), delay));
    t.push(window.setTimeout(() => setPhase("analyzing"), delay + SCAN_DURATION * 1000));
    t.push(window.setTimeout(() => setPhase("done"), delay + SCAN_DURATION * 1000 + ANALYZE_MS));
    // Fade out and restart the whole sequence.
    t.push(
      window.setTimeout(
        () => setPhase("idle"),
        delay + SCAN_DURATION * 1000 + ANALYZE_MS + HOLD_MS,
      ),
    );
    t.push(
      window.setTimeout(
        () => setCycle((c) => c + 1),
        delay + SCAN_DURATION * 1000 + ANALYZE_MS + HOLD_MS + 200,
      ),
    );
    return () => t.forEach(clearTimeout);
  }, [reduce, cycle]);

  useEffect(() => {
    if (reduce) return;
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    const onMove = (e: PointerEvent) => {
      const el = ref.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const px = (e.clientX - (r.left + r.width / 2)) / r.width;
      const py = (e.clientY - (r.top + r.height / 2)) / r.height;
      mx.set(Math.max(-1, Math.min(1, px)) * -6);
      my.set(Math.max(-1, Math.min(1, py)) * -6);
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, [reduce, mx, my]);

  const scanning = phase === "scanning";
  const done = phase === "done";
  const active = scanning || phase === "analyzing" || done;
  const score = useCountUp(active ? TARGET_SCORE : 0, SCAN_DURATION * 1000, !!reduce);

  return (
    <div ref={ref} className="relative">
      <motion.div
        initial={reduce ? { opacity: 1 } : { opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 1, delay: 0.2, ease }}
        className="relative aspect-[896/1098] w-full overflow-hidden rounded-[2.25rem] shadow-[var(--shadow-lift)]"
      >
        <motion.img
          src={heroVision}
          width={896}
          height={1098}
          fetchPriority="high"
          alt="Persona di spalle attraversata da un fascio di luce, circondata da auto, moto e scooter in wireframe olografico e da un anello Compatibility Score"
          style={{ x: reduce ? 0 : sx, y: reduce ? 0 : sy }}
          className="size-full scale-[1.04] object-cover"
        />

        {/* Scan sweep */}
        {!reduce && (
          <motion.div
            key={`scan-${cycle}`}
            aria-hidden
            className="pointer-events-none absolute inset-x-0 top-0 h-full"
            initial={{ opacity: 0 }}
            animate={scanning ? { opacity: 1 } : { opacity: 0 }}
            transition={{ duration: 0.6 }}
          >
            <motion.div
              className="absolute inset-x-0 h-32"
              initial={{ top: "-12%" }}
              animate={scanning ? { top: "100%" } : { top: "-12%" }}
              transition={{ duration: scanning ? SCAN_DURATION : 0, ease: "linear" }}
            >
              <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-b from-transparent via-primary/12 to-primary/25" />
              <div className="absolute inset-x-0 bottom-0 h-0.5 bg-primary shadow-[0_0_28px_4px_var(--color-primary)]" />
            </motion.div>
          </motion.div>
        )}

        {/* Wireframe vehicle detection */}
        {!reduce &&
          detections.map((d) => (
            <motion.div
              key={`${d.id}-${cycle}`}
              aria-hidden
              className="pointer-events-none absolute"
              style={{
                left: `${d.left}%`,
                top: `${d.top}%`,
                width: `${d.width}%`,
                height: `${d.height}%`,
              }}
              initial={{ opacity: 0, scale: 0.96 }}
              animate={
                scanning
                  ? { opacity: [0, 1, 1, 0], scale: [0.96, 1, 1, 1] }
                  : { opacity: 0, scale: 0.96 }
              }
              transition={{
                duration: scanning ? SCAN_DURATION * 0.5 : 0.5,
                delay: scanning ? SCAN_DURATION * d.at : 0,
                times: [0, 0.12, 0.78, 1],
                ease,
              }}
            >
              <div className="relative size-full rounded-md bg-primary/[0.06] ring-2 ring-primary/80 backdrop-blur-[1px]">
                {[
                  "-top-px -left-px",
                  "-top-px -right-px",
                  "-bottom-px -left-px",
                  "-bottom-px -right-px",
                ].map((pos) => (
                  <span
                    key={pos}
                    className={`absolute ${pos} size-2 rounded-[1px] bg-primary shadow-[0_0_6px_var(--color-primary)]`}
                  />
                ))}
                <span className="absolute -top-6 left-0 rounded bg-foreground/90 px-2 py-0.5 text-[0.6rem] font-semibold tracking-[0.06em] whitespace-nowrap text-background uppercase shadow-sm backdrop-blur">
                  {d.label}
                </span>
              </div>
            </motion.div>
          ))}

        {/* Animated Compatibility Score ring, aligned to the ring in the artwork */}
        <div
          className="pointer-events-none absolute"
          style={{ left: `${RING.left}%`, top: `${RING.top}%`, width: `${RING.size}%` }}
        >
          <div className="relative aspect-square w-full">
            <svg viewBox="0 0 100 100" className="size-full -rotate-90">
              <circle
                cx="50"
                cy="50"
                r="46"
                fill="none"
                stroke="var(--color-primary)"
                strokeOpacity="0.18"
                strokeWidth="3.2"
              />
              <motion.circle
                key={`ring-${cycle}`}
                cx="50"
                cy="50"
                r="46"
                fill="none"
                stroke="var(--color-primary)"
                strokeWidth="3.2"
                strokeLinecap="round"
                initial={{ pathLength: reduce ? TARGET_SCORE / 100 : 0 }}
                animate={{ pathLength: active ? TARGET_SCORE / 100 : 0 }}
                transition={{ duration: reduce ? 0 : SCAN_DURATION, ease: "linear" }}
                style={{ filter: "drop-shadow(0 0 6px var(--color-primary))" }}
              />
            </svg>

            <div className="absolute top-[13%] left-1/2 -translate-x-1/2 text-center">
              <div className="rounded-[1.75rem] bg-foreground/45 px-5 py-3 shadow-[0_8px_30px_-8px_rgba(0,0,0,0.55)] ring-1 ring-background/10 backdrop-blur-md">
                <div className="text-[0.44rem] font-semibold tracking-[0.24em] whitespace-nowrap text-background/90 uppercase sm:text-[0.55rem]">
                  Compatibility score
                </div>
                <div className="font-heading mt-1 text-[1.75rem] leading-none font-bold text-primary tabular-nums sm:text-[2.15rem]">
                  {score}%
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Border glow */}
        <motion.span
          aria-hidden
          animate={reduce ? { opacity: 0.45 } : { opacity: [0.25, 0.6, 0.25] }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
          className="pointer-events-none absolute inset-0 rounded-[2.25rem] ring-1 ring-primary/40 ring-inset"
        />
      </motion.div>
    </div>
  );
}
