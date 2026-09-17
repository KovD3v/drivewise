import { useRef, useState } from "react";
import {
  motion,
  useInView,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform,
} from "framer-motion";
import { Section, Eyebrow } from "./Section";
import { RevealGroup, RevealItem } from "./Reveal";
import { EASE, viewportOnce } from "@/lib/motion";

const cards = [
  {
    kind: "layers" as const,
    title: "Decisioni, non opinioni",
    body: "Eviti una scelta di cui potresti pentirti: ogni consiglio nasce da un'analisi strutturata.",
  },
  {
    kind: "compass" as const,
    title: "Tutto è spiegato",
    body: "Capisci sempre il perché, prima di decidere.",
  },
  {
    kind: "sparkle" as const,
    title: "Pensato per te",
    body: "Troverai il veicolo più adatto al tuo modo di vivere.",
  },
];

/* ---------- animated icons ---------- */

function LayersIcon({ play, reduce }: { play: boolean; reduce: boolean }) {
  const sheets = [
    { d: "M12 4 3.5 8.2 12 12.4l8.5-4.2L12 4Z", off: -3 },
    { d: "M3.5 12 12 16.2 20.5 12", off: 0 },
    { d: "M3.5 15.8 12 20l8.5-4.2", off: 3 },
  ];
  return (
    <svg viewBox="0 0 24 24" fill="none" className="size-5">
      {sheets.map((s, i) => (
        <motion.path
          key={s.d}
          d={s.d}
          stroke="currentColor"
          strokeWidth={1.7}
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ y: 0 }}
          animate={play && !reduce ? { y: [0, s.off, 0] } : { y: 0 }}
          transition={{ duration: 1.1, delay: 0.2 + i * 0.07, ease: EASE }}
        />
      ))}
    </svg>
  );
}

function CompassIcon({ play, reduce }: { play: boolean; reduce: boolean }) {
  return (
    <motion.svg
      viewBox="0 0 24 24"
      fill="none"
      className="size-5"
      animate={play && !reduce ? { rotate: [0, -22, 14, -6, 0] } : { rotate: 0 }}
      transition={{ duration: 1.5, delay: 0.25, ease: EASE }}
    >
      <g stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="9" />
        <path d="m15.2 8.8-1.9 4.5-4.5 1.9 1.9-4.5 4.5-1.9Z" />
      </g>
    </motion.svg>
  );
}

function SparkleIcon({ play, reduce }: { play: boolean; reduce: boolean }) {
  const rays = [0, 60, 120, 180, 240, 300];
  return (
    <span className="relative grid size-5 place-items-center">
      <motion.svg
        viewBox="0 0 24 24"
        fill="none"
        className="size-5"
        animate={play && !reduce ? { scale: [1, 1.18, 0.96, 1], rotate: [0, 8, 0] } : {}}
        transition={{ duration: 1.2, delay: 0.25, ease: EASE }}
      >
        <path
          d="M12 3.5 13.9 9l5.6 2-5.6 2-1.9 5.5L10.1 13 4.5 11l5.6-2L12 3.5Z"
          stroke="currentColor"
          strokeWidth={1.7}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </motion.svg>
      {!reduce &&
        rays.map((deg) => (
          <motion.span
            key={deg}
            aria-hidden
            className="absolute size-[3px] rounded-full bg-primary"
            initial={{ opacity: 0, x: 0, y: 0 }}
            animate={
              play
                ? {
                    opacity: [0, 0.9, 0],
                    x: [0, Math.cos((deg * Math.PI) / 180) * 13],
                    y: [0, Math.sin((deg * Math.PI) / 180) * 13],
                  }
                : { opacity: 0 }
            }
            transition={{ duration: 0.9, delay: 0.4, ease: EASE }}
          />
        ))}
    </span>
  );
}

function CardIcon({ kind, play, reduce }: { kind: string; play: boolean; reduce: boolean }) {
  if (kind === "layers") return <LayersIcon play={play} reduce={reduce} />;
  if (kind === "compass") return <CompassIcon play={play} reduce={reduce} />;
  return <SparkleIcon play={play} reduce={reduce} />;
}

/* ---------- card with 3D tilt ---------- */

function AdvantageCard({
  card,
  index,
  featured,
  pointer,
}: {
  card: (typeof cards)[number];
  index: number;
  featured: boolean;
  pointer: { x: ReturnType<typeof useSpring>; y: ReturnType<typeof useSpring> };
}) {
  const reduce = useReducedMotion() ?? false;
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, viewportOnce);
  const [hover, setHover] = useState(false);

  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const rx = useSpring(useTransform(my, [-0.5, 0.5], [5, -5]), { stiffness: 180, damping: 18 });
  const ry = useSpring(useTransform(mx, [-0.5, 0.5], [-5, 5]), { stiffness: 180, damping: 18 });
  const shadowX = useTransform(ry, (v: number) => `${-v * 2.4}px`);
  const shadowY = useTransform(rx, (v: number) => `${18 + v * 2.4}px`);

  const parallaxX = useTransform(pointer.x, (v: number) => v * (10 + index * 4));
  const parallaxY = useTransform(pointer.y, (v: number) => v * 8);

  function onMove(e: React.MouseEvent<HTMLDivElement>) {
    if (reduce) return;
    const r = e.currentTarget.getBoundingClientRect();
    mx.set((e.clientX - r.left) / r.width - 0.5);
    my.set((e.clientY - r.top) / r.height - 0.5);
  }

  return (
    <motion.div
      ref={ref}
      className="relative [perspective:1100px]"
      initial={reduce ? { opacity: 1 } : { opacity: 0, y: 26, scale: 0.95 }}
      animate={inView ? { opacity: 1, y: 0, scale: 1 } : {}}
      transition={{ duration: reduce ? 0 : 0.7, delay: reduce ? 0 : index * 0.15, ease: EASE }}
    >
      {/* watermark number */}
      <motion.span
        aria-hidden
        style={{ x: parallaxX, y: parallaxY }}
        className="pointer-events-none absolute -top-6 right-3 z-0 font-heading text-[6rem] leading-none font-bold text-foreground/[0.045] select-none"
      >
        {index + 1}
      </motion.span>

      <motion.article
        onMouseMove={onMove}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => {
          setHover(false);
          mx.set(0);
          my.set(0);
        }}
        style={
          reduce
            ? {}
            : {
                rotateX: rx,
                rotateY: ry,
                transformStyle: "preserve-3d",
                boxShadow: hover
                  ? `${shadowX.get()} ${shadowY.get()} 48px -22px oklch(0.21 0.034 264 / 0.22)`
                  : "var(--shadow-soft)",
              }
        }
        className={`group relative z-10 h-full rounded-[1.75rem] border border-border/70 bg-card p-9 transition-shadow duration-500 ${
          featured
            ? "shadow-[var(--shadow-lift)] md:-translate-y-2"
            : "shadow-[var(--shadow-soft)]"
        } hover:border-border hover:shadow-[var(--shadow-card-hover)]`}
      >
        <motion.span
          className="grid size-11 place-items-center rounded-2xl bg-primary/12 text-foreground"
          animate={
            hover && !reduce
              ? { scale: 1.08, boxShadow: "0 0 0 6px oklch(0.759 0.114 180.5 / 0.14)" }
              : { scale: 1, boxShadow: "0 0 0 0px oklch(0.759 0.114 180.5 / 0)" }
          }
          transition={{ type: "spring", stiffness: 320, damping: 18 }}
        >
          <CardIcon kind={card.kind} play={inView} reduce={reduce} />
        </motion.span>
        <h3 className="mt-8 text-xl font-bold">{card.title}</h3>
        <p className="mt-3 leading-relaxed text-muted-foreground">{card.body}</p>
      </motion.article>
    </motion.div>
  );
}

export function WhyDriveWise() {
  const reduce = useReducedMotion() ?? false;
  const px = useSpring(useMotionValue(0), { stiffness: 60, damping: 20 });
  const py = useSpring(useMotionValue(0), { stiffness: 60, damping: 20 });

  function onSectionMove(e: React.MouseEvent<HTMLDivElement>) {
    if (reduce) return;
    const r = e.currentTarget.getBoundingClientRect();
    px.set((e.clientX - r.left) / r.width - 0.5);
    py.set((e.clientY - r.top) / r.height - 0.5);
  }

  return (
    <Section>
      <RevealGroup>
        <RevealItem>
          <Eyebrow>Il tuo vantaggio</Eyebrow>
        </RevealItem>
        <RevealItem>
          <h2 className="mt-7 max-w-2xl text-4xl leading-[1.08] font-bold sm:text-5xl">
            Decision intelligence, non un motore di ricerca.
          </h2>
        </RevealItem>
        <RevealItem>
          <p className="mt-6 max-w-2xl text-[1.0625rem] leading-relaxed text-muted-foreground">
            Non ti diciamo solo quale veicolo: ti spieghiamo perché — con numeri, non impressioni.
          </p>
        </RevealItem>
      </RevealGroup>

      <div
        onMouseMove={onSectionMove}
        onMouseLeave={() => {
          px.set(0);
          py.set(0);
        }}
        className="relative mt-16"
      >
        {/* connective line */}
        <svg
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-[5.5rem] hidden h-6 w-full md:block"
          viewBox="0 0 1000 20"
          preserveAspectRatio="none"
        >
          <motion.path
            d="M60 10 H940"
            stroke="currentColor"
            className="text-primary/35"
            strokeWidth={1}
            strokeDasharray="6 10"
            initial={{ pathLength: 0, opacity: 0 }}
            whileInView={{ pathLength: 1, opacity: 1 }}
            viewport={viewportOnce}
            transition={{ duration: reduce ? 0 : 1.4, ease: EASE }}
          />
          <path
            d="M60 10 H940"
            stroke="currentColor"
            className="dw-dash-drift text-primary/35"
            strokeWidth={1}
            strokeDasharray="6 10"
          />
        </svg>

        <div className="relative grid gap-6 md:grid-cols-3">
          {cards.map((c, i) => (
            <AdvantageCard
              key={c.title}
              card={c}
              index={i}
              featured={i === 1}
              pointer={{ x: px, y: py }}
            />
          ))}
        </div>
      </div>
    </Section>
  );
}