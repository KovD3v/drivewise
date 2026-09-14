import { useRef } from "react";
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import { AlignLeft, CircleUser, HelpCircle, ListX, Radio } from "lucide-react";
import { Section } from "./Section";
import { Reveal } from "./Reveal";
import { EASE, viewportOnce } from "@/lib/motion";

const generic = [
  { label: "risposta testuale", Icon: AlignLeft },
  { label: "nessun ranking", Icon: ListX },
  { label: "nessuna spiegazione", Icon: HelpCircle },
  { label: "nessun profilo", Icon: CircleUser },
];
const drivewise = [
  "Decision Score",
  "Decision Confidence",
  "Vehicle DNA",
  "Decision Profile",
  "Alternative",
  "Compromessi",
  "Motivazioni",
];

function StrokeCheck({ reduce }: { reduce: boolean | null }) {
  return (
    <svg viewBox="0 0 24 24" className="size-3.5" fill="none" aria-hidden>
      <motion.path
        d="M5 12.5 10 17.5 19 7"
        stroke="currentColor"
        strokeWidth={2.6}
        strokeLinecap="round"
        strokeLinejoin="round"
        variants={{
          hidden: reduce ? { pathLength: 1 } : { pathLength: 0 },
          show: {
            pathLength: 1,
            transition: { duration: reduce ? 0 : 0.45, delay: reduce ? 0 : 0.1, ease: EASE },
          },
        }}
      />
    </svg>
  );
}

export function Difference() {
  const reduce = useReducedMotion();
  const sectionRef = useRef<HTMLDivElement>(null);

  // Parallax: la posizione del cursore inclina leggermente le due card.
  const px = useMotionValue(0);
  const py = useMotionValue(0);
  const sx = useSpring(px, { stiffness: 90, damping: 18, mass: 0.5 });
  const sy = useSpring(py, { stiffness: 90, damping: 18, mass: 0.5 });
  const rotYA = useTransform(sx, [-1, 1], [4.5, -1.5]);
  const rotYB = useTransform(sx, [-1, 1], [1.5, -4.5]);
  const rotX = useTransform(sy, [-1, 1], [-3, 3]);

  const onMove = (e: React.MouseEvent) => {
    if (reduce) return;
    const r = sectionRef.current?.getBoundingClientRect();
    if (!r) return;
    px.set(((e.clientX - r.left) / r.width) * 2 - 1);
    py.set(((e.clientY - r.top) / r.height) * 2 - 1);
  };
  const onLeave = () => {
    px.set(0);
    py.set(0);
  };

  const list = (stagger: number, delayChildren: number) => ({
    hidden: {},
    show: {
      transition: reduce ? {} : { staggerChildren: stagger, delayChildren },
    },
  });
  const item = {
    hidden: reduce ? { opacity: 1, x: 0 } : { opacity: 0, x: -14 },
    show: { opacity: 1, x: 0, transition: { duration: 0.5, ease: EASE } },
  };

  const enter = (from: number) => ({
    hidden: reduce ? { opacity: 1, x: 0 } : { opacity: 0, x: from },
    show: {
      opacity: 1,
      x: reduce ? 0 : [from, from * -0.06, 0],
      transition: { duration: reduce ? 0 : 0.85, ease: EASE },
    },
  });

  return (
    <Section id="perche" surface className="overflow-x-clip pt-16 md:pt-20 lg:pt-24">
      <Reveal>
        <h2 className="max-w-2xl text-4xl leading-[1.08] font-bold sm:text-5xl">
          Perché DriveWise è diverso.
        </h2>
        <p className="mt-6 max-w-xl text-[1.0625rem] leading-relaxed text-muted-foreground">
          Capisci sempre il perché di ogni consiglio, non solo la risposta.
        </p>
      </Reveal>

      <motion.div
        ref={sectionRef}
        onMouseMove={onMove}
        onMouseLeave={onLeave}
        initial="hidden"
        whileInView="show"
        viewport={viewportOnce}
        className="relative mt-16 grid items-center gap-10 md:grid-cols-2 md:gap-10"
        style={{ perspective: 1200 }}
      >
        {/* VS badge — impatto al centro */}
        <motion.div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-1/2 z-10 flex -translate-y-1/2 justify-center md:inset-y-6 md:inset-x-auto md:top-0 md:left-1/2 md:-translate-x-1/2 md:translate-y-0 md:flex-col md:items-center"
        >
          <motion.span
            className="hidden w-px flex-1 origin-top bg-gradient-to-b from-transparent via-border to-transparent md:block"
            variants={{
              hidden: reduce ? { scaleY: 1 } : { scaleY: 0 },
              show: { scaleY: 1, transition: { duration: reduce ? 0 : 0.7, ease: EASE } },
            }}
          />
          <motion.span
            className="dw-vs-pulse my-3 grid size-11 place-items-center rounded-full border border-primary/30 bg-card text-[0.7rem] font-bold tracking-[0.12em] text-foreground shadow-[var(--shadow-soft)]"
            variants={{
              hidden: reduce ? { scale: 1, opacity: 1 } : { scale: 0.5, opacity: 0 },
              show: {
                scale: reduce ? 1 : [0.5, 1.28, 1],
                opacity: 1,
                transition: { duration: reduce ? 0 : 0.55, delay: reduce ? 0 : 0.6, ease: EASE },
              },
            }}
          >
            VS
            <motion.span
              aria-hidden
              className="pointer-events-none absolute inset-0 rounded-full bg-primary/50"
              variants={{
                hidden: { opacity: 0, scale: 1 },
                show: {
                  opacity: reduce ? 0 : [0, 0.55, 0],
                  scale: reduce ? 1 : [1, 2.1],
                  transition: { duration: reduce ? 0 : 0.7, delay: reduce ? 0 : 0.68, ease: EASE },
                },
              }}
            />
          </motion.span>
          <motion.span
            className="hidden w-px flex-1 origin-bottom bg-gradient-to-b from-transparent via-border to-transparent md:block"
            variants={{
              hidden: reduce ? { scaleY: 1 } : { scaleY: 0 },
              show: { scaleY: 1, transition: { duration: reduce ? 0 : 0.7, ease: EASE } },
            }}
          />
        </motion.div>

        {/* Card "spenta" */}
        <motion.div variants={enter(-90)} style={{ rotateY: rotYA, rotateX: rotX }} className="md:pt-10">
          <div className="group h-full rounded-[1.75rem] border border-border/60 bg-muted/40 p-9 saturate-[0.35] transition-all duration-500 md:scale-[0.975]">
            <h3 className="text-lg font-bold text-muted-foreground">Una IA generica</h3>
            <motion.ul className="mt-7 space-y-4" variants={list(0.08, 0.85)}>
              {generic.map(({ label, Icon }) => (
                <motion.li
                  key={label}
                  variants={item}
                  className="flex items-center gap-3 text-muted-foreground"
                >
                  <span className="grid size-6 shrink-0 place-items-center rounded-full border border-border/70 bg-background/70 text-muted-foreground">
                    <Icon className="size-3.5" />
                  </span>
                  {label}
                </motion.li>
              ))}
            </motion.ul>
          </div>
        </motion.div>

        {/* Card vibrante */}
        <motion.div variants={enter(90)} style={{ rotateY: rotYB, rotateX: rotX }}>
          <div className="group relative h-full rounded-[1.85rem] p-px shadow-[var(--shadow-card-hover)] transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] hover:shadow-[0_28px_70px_-28px_color-mix(in_oklab,var(--color-primary)_55%,transparent)] motion-safe:md:-translate-y-4 motion-safe:hover:scale-[1.015]">
            <div
              aria-hidden
              className="dw-spin-slow pointer-events-none absolute inset-0 rounded-[1.85rem] bg-[conic-gradient(from_0deg,transparent_0deg,var(--color-primary)_60deg,transparent_140deg,transparent_220deg,var(--color-accent)_290deg,transparent_360deg)] opacity-45 transition-opacity duration-500 group-hover:opacity-80"
              style={{ maskImage: "linear-gradient(#000,#000)" }}
            />
            <div className="relative h-full overflow-hidden rounded-[1.8rem] border border-primary/30 bg-card p-9 backdrop-blur-xl">
              <div
                aria-hidden
                className="pointer-events-none absolute -top-24 -right-16 size-56 rounded-full bg-primary/12 blur-3xl transition-all duration-500 group-hover:bg-primary/20"
              />
              <div className="relative flex items-center gap-3">
                <h3 className="text-lg font-bold">DriveWise</h3>
                <span className="inline-flex translate-y-1 items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[0.68rem] font-semibold tracking-[0.08em] text-foreground opacity-0 transition-all duration-300 group-hover:translate-y-0 group-hover:opacity-100">
                  <Radio className="size-3 text-primary" />
                  In tempo reale
                </span>
              </div>
              <motion.ul className="relative mt-7 space-y-4" variants={list(0.12, 1)}>
                {drivewise.map((d) => (
                  <motion.li
                    key={d}
                    variants={item}
                    className="flex items-center gap-3 font-medium transition-transform duration-300 hover:translate-x-1"
                  >
                    <motion.span
                      variants={{
                        hidden: reduce ? { scale: 1, opacity: 1 } : { scale: 0.5, opacity: 0 },
                        show: {
                          scale: reduce ? 1 : [0.5, 1.18, 1],
                          opacity: 1,
                          transition: { duration: 0.4, delay: reduce ? 0 : 0.12, ease: EASE },
                        },
                      }}
                      className="grid size-6 shrink-0 place-items-center rounded-full bg-primary/20 text-primary shadow-[0_0_0_4px_color-mix(in_oklab,var(--color-primary)_12%,transparent)]"
                    >
                      <StrokeCheck reduce={reduce} />
                    </motion.span>
                    {d}
                  </motion.li>
                ))}
              </motion.ul>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </Section>
  );
}
