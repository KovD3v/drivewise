import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import {
  AlertTriangle,
  Armchair,
  Dna,
  Euro,
  Puzzle,
  Shield,
  ShieldCheck,
  TrendingDown,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { Section, Eyebrow } from "./Section";
import { RevealGroup, RevealItem } from "./Reveal";
import { EASE, viewportOnce } from "@/lib/motion";
import { useCountUp } from "@/lib/use-count-up";
import { useIsMobile } from "@/hooks/use-mobile";

type Factor = { label: string; detail: string; icon: LucideIcon; ring: 0 | 1 };

const factors: Factor[] = [
  { label: "Costi reali", detail: "Acquisto, consumi, assicurazione e bollo su base annua.", icon: Euro, ring: 0 },
  { label: "Affidabilità", detail: "Guasti ricorrenti e comportamento nel tempo.", icon: Shield, ring: 1 },
  { label: "Sicurezza", detail: "Dotazioni attive e passive, esiti nei test.", icon: ShieldCheck, ring: 0 },
  { label: "Richiami", detail: "Campagne ufficiali registrate sul modello.", icon: AlertTriangle, ring: 1 },
  { label: "Manutenzione", detail: "Intervalli, costi tagliandi e ricambi.", icon: Wrench, ring: 0 },
  { label: "Svalutazione", detail: "Tenuta del valore residuo nel tempo.", icon: TrendingDown, ring: 1 },
  { label: "Comfort", detail: "Ergonomia, rumorosità e uso quotidiano.", icon: Armchair, ring: 0 },
  { label: "Vehicle DNA", detail: "Identità tecnica del veicolo e vocazione d'uso.", icon: Dna, ring: 1 },
  {
    label: "Compatibilità con il tuo utilizzo",
    detail: "Quanto il veicolo aderisce al tuo profilo reale.",
    icon: Puzzle,
    ring: 1,
  },
];

/** Durata di una rotazione completa del raggio. */
const SWEEP = 16;
const R_DESKTOP = 40;
const R_MOBILE = 35;
const R_MOBILE_NARROW = 41;

/**
 * Unica funzione di posizionamento: tutti i nodi sono distribuiti in modo
 * uniforme su una sola orbita (angolo = 360° / n * indice), così a qualunque
 * dimensione del diagramma la distanza fra nodi adiacenti resta identica.
 */
function geometry(f: Factor, mobile: boolean, narrow = false) {
  const i = factors.indexOf(f);
  const radius = mobile ? (narrow ? R_MOBILE_NARROW : R_MOBILE) : R_DESKTOP;
  return { angle: (360 / factors.length) * i, radius };
}

const pos = (angle: number, radius: number) => ({
  left: `${(50 + radius * Math.sin((angle * Math.PI) / 180)).toFixed(4)}%`,
  top: `${(50 - radius * Math.cos((angle * Math.PI) / 180)).toFixed(4)}%`,
});

/**
 * Il tooltip si apre sempre verso l'esterno del diagramma: lateralmente per i
 * nodi ai fianchi, sopra/sotto per quelli in alto o in basso, così da non
 * coprire mai le etichette dei nodi adiacenti.
 */
function tooltipPlacement(angle: number) {
  const rad = (angle * Math.PI) / 180;
  const dx = Math.sin(rad);
  const dy = -Math.cos(rad);
  if (Math.abs(dx) > 0.62) {
    return dx > 0
      ? "left-full ml-5 top-1/2 -translate-y-1/2"
      : "right-full mr-5 top-1/2 -translate-y-1/2";
  }
  return dy < 0 ? "bottom-full mb-5" : "top-full mt-20";
}

function Orbit({ radius, lit }: { radius: number; lit: boolean }) {
  return (
    <div
      aria-hidden
      className="absolute rounded-full border transition-colors duration-500"
      style={{
        left: `${50 - radius}%`,
        top: `${50 - radius}%`,
        width: `${radius * 2}%`,
        height: `${radius * 2}%`,
        borderColor: lit
          ? "color-mix(in oklab, var(--primary) 55%, transparent)"
          : "color-mix(in oklab, var(--primary) 18%, transparent)",
      }}
    />
  );
}

/** Particelle che scorrono lungo un'orbita in senso opposto al raggio. */
function OrbitParticles({ radius, count, dur }: { radius: number; count: number; dur: number }) {
  return (
    <div
      aria-hidden
      className="dw-radar-spin-rev pointer-events-none absolute inset-0"
      style={{ "--dw-radar-dur": `${dur}s` } as React.CSSProperties}
    >
      {Array.from({ length: count }, (_, i) => {
        const a = (360 / count) * i + 12;
        return (
          <span
            key={i}
            className="absolute size-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/45"
            style={pos(a, radius)}
          />
        );
      })}
    </div>
  );
}

function StatConnections() {
  return (
    <svg
      aria-hidden
      className="pointer-events-none absolute inset-0 z-[1] size-full"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id="stat-line-tl" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.38" />
          <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="stat-line-tr" x1="1" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.38" />
          <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="stat-line-bl" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.38" />
          <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="stat-line-br" x1="1" y1="1" x2="0" y2="0">
          <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.38" />
          <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d="M 18 19 L 41 42" stroke="url(#stat-line-tl)" strokeWidth="0.18" />
      <path d="M 82 19 L 59 42" stroke="url(#stat-line-tr)" strokeWidth="0.18" />
      <path d="M 18 81 L 41 58" stroke="url(#stat-line-bl)" strokeWidth="0.18" />
      <path d="M 82 81 L 59 58" stroke="url(#stat-line-br)" strokeWidth="0.18" />
    </svg>
  );
}

type StatPosition = "top-left" | "top-right" | "bottom-left" | "bottom-right";

function StatBubble({
  value,
  suffix = "",
  label,
  sublabel,
  variant = "mint",
  position,
  delay = 0,
}: {
  value: number;
  suffix?: string;
  label: string;
  sublabel?: string;
  variant?: "mint" | "amber";
  position: StatPosition;
  delay?: number;
}) {
  const reduce = useReducedMotion();
  const [visible, setVisible] = useState(false);
  const count = useCountUp(visible ? value : 0, 1400, !!reduce);

  const posClasses = {
    "top-left": "top-0 left-[1%] sm:top-[3%] sm:left-[3%] items-start text-left",
    "top-right": "top-0 right-[1%] sm:top-[3%] sm:right-[3%] items-end text-right",
    "bottom-left": "bottom-0 left-[1%] sm:bottom-[3%] sm:left-[3%] items-start text-left",
    "bottom-right": "bottom-0 right-[1%] sm:bottom-[3%] sm:right-[3%] items-end text-right",
  }[position];

  const colorClass = variant === "amber" ? "text-amber-700" : "text-primary";
  const glowStyle =
    variant === "amber" && !reduce
      ? { textShadow: "0 0 22px rgba(180, 83, 9, 0.32)" }
      : undefined;

  return (
    <motion.div
      className={`absolute z-10 flex w-[46%] flex-col sm:w-48 ${posClasses}`}
      initial={{ opacity: 0, y: position.startsWith("top") ? -18 : 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={viewportOnce}
      transition={{ duration: 0.7, ease: EASE, delay }}
      onViewportEnter={() => setVisible(true)}
    >
      <span
        className={`whitespace-nowrap text-[2.15rem] leading-none font-bold tracking-tight sm:text-5xl ${colorClass}`}
        style={glowStyle}
      >
        {reduce ? value : count}
        {suffix}
      </span>
      <span className="mt-4 max-w-[10rem] text-[0.62rem] leading-snug font-semibold uppercase tracking-wide text-foreground sm:mt-5 sm:max-w-[12rem] sm:text-[0.7rem]">
        {label}
      </span>
      {sublabel && (
        <span className="mt-1.5 max-w-[10rem] text-[0.6rem] leading-tight text-muted-foreground sm:max-w-[12rem] sm:text-[0.65rem]">
          {sublabel}
        </span>
      )}
    </motion.div>
  );
}

/** true sotto i 400px di larghezza: radar più arioso, nodi più piccoli. */
function useNarrowScreen() {
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia("(max-width: 399px)");
    const on = () => setNarrow(mql.matches);
    on();
    mql.addEventListener("change", on);
    return () => mql.removeEventListener("change", on);
  }, []);
  return narrow;
}

export function TrustSignals() {
  const reduce = useReducedMotion();
  const mobile = useIsMobile();
  const narrow = useNarrowScreen();
  const [hovered, setHovered] = useState<number | null>(null);
  const hoveredFactor = hovered !== null ? factors[hovered]! : null;
  const lock = hoveredFactor ? geometry(hoveredFactor, mobile, narrow).angle : null;

  return (
    <Section id="analisi" surface className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 h-[70%] opacity-[0.55]"
      >
        <div
          className="absolute inset-0 [mask-image:radial-gradient(70%_60%_at_50%_70%,black,transparent)]"
          style={{
            backgroundImage: "radial-gradient(currentColor 1px, transparent 1px)",
            backgroundSize: "22px 22px",
            color: "color-mix(in oklab, var(--primary) 22%, transparent)",
          }}
        />
      </div>

      <RevealGroup stagger={0.09}>
        <RevealItem>
          <Eyebrow>Analisi strutturata</Eyebrow>
        </RevealItem>
        <RevealItem>
          <h2 className="mt-7 max-w-3xl text-4xl leading-[1.08] font-bold sm:text-5xl">
            Ogni decisione considera:
          </h2>
        </RevealItem>
        <RevealItem>
          <p className="mt-6 max-w-xl text-[1.0625rem] leading-relaxed text-muted-foreground">
            Nessuna opinione generata al volo. Solo criteri misurabili, pesati sul tuo modo di
            vivere.
          </p>
        </RevealItem>
      </RevealGroup>

      <div className="relative mx-auto mt-14 h-[42rem] w-full max-w-[min(92vw,44rem)] sm:h-[68rem]">
        <StatConnections />

        <div className="absolute top-1/2 left-1/2 aspect-square w-full -translate-x-1/2 -translate-y-1/2 scale-[0.62] sm:scale-[0.78]">
          {/* orbite */}
          <Orbit
            radius={mobile ? (narrow ? R_MOBILE_NARROW : R_MOBILE) : R_DESKTOP}
            lit={hovered !== null}
          />

        {/* particelle di flusso dati */}
        {!reduce && (
          <OrbitParticles
            radius={mobile ? (narrow ? R_MOBILE_NARROW : R_MOBILE) : R_DESKTOP}
            count={9}
            dur={46}
          />
        )}

        {/* raggio di scansione */}
        {!reduce && (
          <div
            aria-hidden
            className={[
              "pointer-events-none absolute inset-0",
              lock === null ? "dw-radar-spin" : "transition-transform duration-500 ease-out",
            ].join(" ")}
            style={
              {
                "--dw-radar-dur": `${SWEEP}s`,
                ...(lock === null ? {} : { transform: `rotate(${lock}deg)` }),
              } as React.CSSProperties
            }
          >
            <div
              className="absolute inset-0 rounded-full"
              style={{
                background:
                  "conic-gradient(from 336deg at 50% 50%, transparent 0deg, color-mix(in oklab, var(--primary) 16%, transparent) 22deg, transparent 24deg)",
              }}
            />
            <div
              className="absolute top-[8%] left-1/2 h-[42%] w-px origin-bottom -translate-x-1/2"
              style={{
                background:
                  "linear-gradient(to bottom, transparent, color-mix(in oklab, var(--primary) 85%, transparent))",
                boxShadow: "0 0 10px color-mix(in oklab, var(--primary) 60%, transparent)",
              }}
            />
          </div>
        )}

        {/* centro */}
        <motion.div
          initial={reduce ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.85 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={viewportOnce}
          transition={{ duration: 0.6, ease: EASE }}
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
        >
          <div
            className={[
              "grid size-36 place-items-center rounded-full border border-primary/40 bg-background text-center shadow-[var(--shadow-soft)] sm:size-48",
              reduce ? "" : "dw-radar-breath",
            ].join(" ")}
          >
            <div>
              <Dna className="mx-auto size-7 text-primary sm:size-8" />
              <span className="mt-1 block text-[0.7rem] font-medium tracking-[0.14em] text-muted-foreground uppercase sm:text-[0.75rem]">
                Decision
              </span>
              <span className="block text-[1.05rem] font-semibold sm:text-[1.3rem]">Engine</span>
            </div>
          </div>
        </motion.div>

        {/* nodi */}
        <motion.ul
          initial="hidden"
          whileInView="show"
          viewport={viewportOnce}
          variants={{
            hidden: {},
            show: { transition: { staggerChildren: reduce ? 0 : 0.08, delayChildren: reduce ? 0 : 0.2 } },
          }}
          className="absolute inset-0"
        >
          {[...factors]
            .map((f, i) => ({ f, i }))
            .sort((a, b) => a.f.ring - b.f.ring)
            .map(({ f, i }) => {
              const g = geometry(f, mobile, narrow);
              const Icon = f.icon;
              const delay = `${(g.angle / 360) * SWEEP}s`;
              const active = hovered === i;
              return (
                <motion.li
                  key={f.label}
                  variants={{
                    hidden: reduce ? { opacity: 1 } : { opacity: 0, scale: 0.6 },
                    show: {
                      opacity: 1,
                      scale: 1,
                      transition: reduce
                        ? { duration: 0 }
                        : { type: "spring", stiffness: 340, damping: 22 },
                    },
                  }}
                  onHoverStart={() => setHovered(i)}
                  onHoverEnd={() => setHovered(null)}
                  onFocus={() => setHovered(i)}
                  onBlur={() => setHovered(null)}
                  tabIndex={0}
                  className="group absolute -translate-x-1/2 -translate-y-1/2 outline-none"
                  style={pos(g.angle, g.radius)}
                >
                  <div className="relative grid place-items-center">
                    {/* ping radar */}
                    {!reduce && (
                      <span
                        aria-hidden
                        className={`dw-radar-ping absolute ${narrow ? "size-11" : "size-15"} rounded-full border border-primary/70 sm:size-17`}
                        style={
                          { "--dw-radar-dur": `${SWEEP}s`, "--dw-radar-delay": delay } as React.CSSProperties
                        }
                      />
                    )}
                    <span
                      className={[
                        `grid ${narrow ? "size-10" : "size-14"} place-items-center rounded-full border bg-background shadow-[var(--shadow-soft)] transition-[transform,border-color,background-color,box-shadow] duration-300 sm:size-16`,
                        reduce ? "" : "dw-radar-hit",
                        active
                          ? "scale-110 border-primary bg-primary/20 shadow-[0_0_0_8px_color-mix(in_oklab,var(--primary)_12%,transparent)]"
                          : "border-primary/35",
                      ].join(" ")}
                      style={
                        { "--dw-radar-dur": `${SWEEP}s`, "--dw-radar-delay": delay } as React.CSSProperties
                      }
                    >
                      <Icon className={`${narrow ? "size-4" : "size-5"} text-foreground sm:size-[1.6rem]`} />
                    </span>

                    {/* badge "letto in tempo reale" */}
                    {!reduce && (
                      <span
                        role="status"
                        aria-label={`${f.label}: verificato`}
                        className="dw-radar-badge pointer-events-none absolute -top-2 -right-3 rounded-full bg-primary px-1.5 py-px text-[0.62rem] font-semibold text-primary-foreground opacity-0"
                        style={
                          { "--dw-radar-dur": `${SWEEP}s`, "--dw-radar-delay": delay } as React.CSSProperties
                        }
                      >
                        OK
                      </span>
                    )}

                    <span
                      className={`pointer-events-none absolute top-full mt-2 block text-center leading-tight font-medium text-muted-foreground transition-colors duration-300 group-hover:text-foreground group-focus:text-foreground sm:w-44 sm:text-[1.3rem] ${narrow ? "w-20 text-[0.82rem]" : "w-24 text-[0.95rem]"}`}
                    >
                      {f.label}
                    </span>

                    {/* tooltip */}
                    <span
                      className={[
                        "pointer-events-none absolute z-30 w-48 rounded-xl border border-primary/25 bg-card px-3.5 py-2.5 text-[0.9rem] leading-snug text-muted-foreground shadow-[var(--shadow-object)] transition-opacity duration-200",
                        tooltipPlacement(g.angle),
                        active ? "opacity-100" : "opacity-0",
                      ].join(" ")}
                    >
                      {f.detail}
                    </span>
                  </div>
                </motion.li>
              );
            })}
          </motion.ul>
        </div>

        {/* numeri fluttuanti attorno al radar */}
        <StatBubble
          value={120}
          suffix="+"
          label="parametri analizzati"
          position="top-left"
          delay={0.2}
        />
        <StatBubble
          value={40}
          suffix="+ milioni"
          label="veicoli circolanti in Italia"
          sublabel="il mercato che analizziamo"
          variant="amber"
          position="top-right"
          delay={0.35}
        />
        <StatBubble
          value={9}
          label="categorie di analisi"
          position="bottom-left"
          delay={0.5}
        />
        <StatBubble
          value={3}
          label="tipologie di veicolo"
          sublabel="Auto, Moto, Scooter"
          position="bottom-right"
          delay={0.65}
        />
      </div>
    </Section>
  );
}
