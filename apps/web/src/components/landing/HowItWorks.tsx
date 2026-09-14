import { useEffect, useRef, useState } from "react";
import { motion, useInView, useMotionValue, useReducedMotion, useSpring } from "framer-motion";
import { Section, Eyebrow } from "./Section";
import { RevealGroup, RevealItem } from "./Reveal";
import { EASE, viewportOnce } from "@/lib/motion";

const steps = [
  { title: "Raccontaci cosa ti serve", body: "Bastano poche frasi, nel tuo linguaggio." },
  { title: "DriveWise analizza", body: "Costi reali, affidabilità, uso quotidiano." },
  { title: "Ricevi una decisione motivata", body: "Con punteggio, alternative e compromessi." },
];

const STEP_DELAY = 0.75;

/* ---------- live icons ---------- */

function ChatIcon({ active, reduce }: { active: boolean; reduce: boolean }) {
  return (
    <span className="relative grid size-[1.15rem] place-items-center">
      <svg viewBox="0 0 24 24" fill="none" className="size-[1.15rem]">
        <path
          d="M20 15a2 2 0 0 1-2 2H8l-4 3V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2Z"
          stroke="currentColor"
          strokeWidth={1.7}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="absolute top-[42%] left-1/2 flex -translate-x-1/2 -translate-y-1/2 gap-[2px]">
        {[0, 1, 2].map((d) => (
          <motion.span
            key={d}
            className="size-[2.5px] rounded-full bg-current"
            animate={
              active && !reduce
                ? { opacity: [0.25, 1, 0.25], y: [0, -1.5, 0] }
                : { opacity: active ? 0.75 : 0.25, y: 0 }
            }
            transition={
              active && !reduce
                ? { duration: 1.1, repeat: Infinity, delay: d * 0.15, ease: "easeInOut" }
                : { duration: 0.3 }
            }
          />
        ))}
      </span>
    </span>
  );
}

function ScanIcon({ active, reduce }: { active: boolean; reduce: boolean }) {
  return (
    <span className="relative grid size-[1.15rem] place-items-center overflow-hidden">
      <svg viewBox="0 0 24 24" fill="none" className="size-[1.15rem]">
        <g stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 8V5a2 2 0 0 1 2-2h3M16 3h3a2 2 0 0 1 2 2v3M21 16v3a2 2 0 0 1-2 2h-3M8 21H5a2 2 0 0 1-2-2v-3" />
          <circle cx="11.5" cy="11.5" r="3" />
          <path d="m14 14 2 2" />
        </g>
      </svg>
      <motion.span
        aria-hidden
        className="absolute inset-x-0 h-[1.5px] bg-primary"
        animate={
          active && !reduce
            ? { top: ["12%", "84%", "12%"], opacity: [0, 0.9, 0] }
            : { opacity: 0, top: "12%" }
        }
        transition={
          active && !reduce
            ? { duration: 2.2, repeat: Infinity, ease: "easeInOut" }
            : { duration: 0.3 }
        }
      />
    </span>
  );
}

function DocIcon({ active, reduce }: { active: boolean; reduce: boolean }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="size-[1.15rem]">
      <path
        d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z M14 3v5h5"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <motion.path
        d="m9 14.5 2.1 2.1L15.4 12"
        stroke="currentColor"
        strokeWidth={1.9}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={false}
        animate={{ pathLength: active || reduce ? 1 : 0 }}
        transition={{ duration: reduce ? 0 : 0.55, ease: EASE, delay: active && !reduce ? 0.15 : 0 }}
      />
    </svg>
  );
}

function ResultPreview({ active, reduce }: { active: boolean; reduce: boolean }) {
  return (
    <motion.div
      aria-label="Anteprima del Decision Score"
      initial={reduce ? false : { opacity: 0, y: 8, scale: 0.97 }}
      animate={active ? { opacity: 1, y: 0, scale: 1 } : { opacity: 0.55, y: 4, scale: 0.98 }}
      transition={{ duration: reduce ? 0 : 0.55, ease: EASE }}
      className="relative mt-6 rounded-xl border border-border/80 bg-background/80 p-4 shadow-[var(--shadow-soft)]"
    >
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-[0.6rem] font-semibold tracking-[0.12em] text-muted-foreground uppercase">Decision Score</p>
          <p className="mt-1 font-heading text-3xl font-extrabold tabular-nums">94<span className="text-sm text-muted-foreground">/100</span></p>
        </div>
        <span className="rounded-full bg-primary/12 px-2.5 py-1 text-[0.65rem] font-semibold text-foreground">Scelta consigliata</span>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full origin-left rounded-full bg-primary"
          initial={{ scaleX: reduce ? 0.94 : 0 }}
          animate={active ? { scaleX: 0.94 } : { scaleX: 0.25 }}
          transition={{ duration: reduce ? 0 : 0.8, delay: reduce ? 0 : 0.15, ease: EASE }}
        />
      </div>
      <div className="mt-3 flex items-center gap-2 text-[0.68rem] text-muted-foreground">
        <span className="text-primary">✓</span>
        <span>Costi coerenti con il tuo utilizzo</span>
      </div>
    </motion.div>
  );
}

const icons = [ChatIcon, ScanIcon, DocIcon];

/* ---------- step card with 3D tilt ---------- */

function StepCard({
  index,
  active,
  reduce,
}: {
  index: number;
  active: boolean;
  reduce: boolean;
}) {
  const s = steps[index]!;
  const Icon = icons[index]!;
  const ref = useRef<HTMLDivElement>(null);
  const rx = useSpring(useMotionValue(0), { stiffness: 180, damping: 18 });
  const ry = useSpring(useMotionValue(0), { stiffness: 180, damping: 18 });
  const px = useSpring(useMotionValue(0), { stiffness: 90, damping: 20 });

  const onMove = (e: React.MouseEvent) => {
    if (reduce || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const nx = (e.clientX - r.left) / r.width - 0.5;
    const ny = (e.clientY - r.top) / r.height - 0.5;
    ry.set(nx * 9);
    rx.set(-ny * 9);
    px.set(nx * 14);
  };
  const onLeave = () => {
    rx.set(0);
    ry.set(0);
    px.set(0);
  };

  return (
    <motion.li
      variants={{
        hidden: reduce ? { opacity: 1, y: 0 } : { opacity: 0, y: 26 },
        show: {
          opacity: 1,
          y: 0,
          transition: reduce
            ? { duration: 0 }
            : { type: "spring", stiffness: 260, damping: 14, mass: 0.8 },
        },
      }}
      className="group relative"
      style={{ perspective: 900 }}
    >
      <motion.div
        ref={ref}
        onMouseMove={onMove}
        onMouseLeave={onLeave}
        style={{ rotateX: rx, rotateY: ry, transformStyle: "preserve-3d" }}
        className="relative overflow-hidden rounded-2xl px-1 pt-8 pb-2 transition-shadow duration-300 hover:shadow-[0_24px_50px_-28px_rgba(17,24,39,0.28)] md:px-4 md:pb-6"
      >
        {/* giant watermark number */}
        <motion.span
          aria-hidden
          style={{ x: px }}
          className="font-heading pointer-events-none absolute -top-2 right-2 text-[7rem] leading-none font-extrabold text-foreground/[0.045] select-none md:text-[8.5rem]"
        >
          0{index + 1}
        </motion.span>

        <div className="relative flex items-center gap-4">
          <span
            className={`font-heading text-sm font-semibold tabular-nums transition-colors duration-500 ${
              active ? "text-foreground" : "text-muted-foreground"
            }`}
          >
            0{index + 1}
          </span>
          <motion.span
            className="relative grid size-10 place-items-center rounded-xl bg-background transition-[color,box-shadow,background-color] duration-500"
            animate={
              active
                ? {
                    boxShadow:
                      "0 0 0 1px color-mix(in oklab, var(--primary) 45%, transparent), 0 8px 22px -12px color-mix(in oklab, var(--primary) 60%, transparent)",
                    color: "var(--primary)",
                  }
                : { boxShadow: "0 0 0 1px var(--border)", color: "var(--muted-foreground)" }
            }
            transition={{ duration: 0.5, ease: EASE }}
          >
            {active && !reduce && (
              <motion.span
                aria-hidden
                className="absolute inset-0 rounded-xl ring-1 ring-primary/50"
                initial={{ opacity: 0.6, scale: 1 }}
                animate={
                  index === 2
                    ? { opacity: [0.7, 0, 0.7, 0], scale: [1, 1.5, 1, 1.5] }
                    : { opacity: [0.5, 0], scale: [1, 1.35] }
                }
                transition={
                  index === 2
                    ? { duration: 2.6, times: [0, 0.4, 0.5, 1], ease: "easeOut" }
                    : { duration: 1, ease: "easeOut" }
                }
              />
            )}
            <Icon active={active} reduce={!!reduce} />
          </motion.span>
        </div>
        <h3 className="relative mt-7 text-xl font-bold">{s.title}</h3>
        <p className="relative mt-3 leading-relaxed text-muted-foreground">{s.body}</p>
        {index === 2 && <ResultPreview active={active} reduce={reduce} />}
      </motion.div>
    </motion.li>
  );
}

export function HowItWorks() {
  const reduce = !!useReducedMotion();
  const listRef = useRef<HTMLDivElement>(null);
  const inView = useInView(listRef, { once: true, margin: "-120px" });
  const [activeStep, setActiveStep] = useState(reduce ? 2 : -1);

  useEffect(() => {
    if (!inView) return;
    if (reduce) {
      setActiveStep(2);
      return;
    }
    const timers = steps.map((_, i) =>
      setTimeout(() => setActiveStep((p) => Math.max(p, i)), (i * STEP_DELAY + 0.45) * 1000),
    );
    return () => timers.forEach(clearTimeout);
  }, [inView, reduce]);

  return (
    <Section id="come-funziona" surface>
      <RevealGroup>
        <RevealItem>
          <Eyebrow>Come funziona</Eyebrow>
        </RevealItem>
        <RevealItem>
          <h2 className="mt-7 max-w-2xl text-4xl leading-[1.08] font-bold sm:text-5xl">
            Tre passaggi, zero rumore.
          </h2>
        </RevealItem>
      </RevealGroup>

      <div ref={listRef} className="relative mt-16">
        {/* continuous progress line */}
        <div aria-hidden className="absolute inset-x-0 top-0 hidden h-px md:block">
          <div className="absolute inset-0 bg-border" />
          <motion.div
            className="absolute inset-y-0 left-0 overflow-hidden"
            initial={{ width: reduce ? "100%" : "0%" }}
            animate={inView ? { width: "100%" } : {}}
            transition={{ duration: reduce ? 0 : STEP_DELAY * 3, ease: "easeInOut" }}
          >
            <div className="absolute inset-0 bg-primary/60" />
            <motion.div
              className="absolute inset-y-0 left-0 w-[200vw]"
              style={{
                backgroundImage:
                  "repeating-linear-gradient(90deg, color-mix(in oklab, var(--primary) 90%, transparent) 0 10px, transparent 10px 24px)",
              }}
              animate={reduce ? {} : { x: [0, 24] }}
              transition={{ duration: 1.1, repeat: Infinity, ease: "linear" }}
            />
          </motion.div>
        </div>

        <motion.ol
          className="grid gap-12 md:grid-cols-3 md:gap-8"
          initial="hidden"
          whileInView="show"
          viewport={viewportOnce}
          variants={{
            hidden: {},
            show: { transition: { staggerChildren: reduce ? 0 : STEP_DELAY } },
          }}
        >
          {steps.map((s, i) => (
            <StepCard key={s.title} index={i} active={activeStep >= i} reduce={reduce} />
          ))}
        </motion.ol>
      </div>
    </Section>
  );
}