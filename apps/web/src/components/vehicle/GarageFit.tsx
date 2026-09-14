import { useEffect, useRef, useState } from "react";
import { motion, useInView, useReducedMotion } from "framer-motion";
import { AlertTriangle, Check, DoorOpen, Info, Ruler } from "lucide-react";
import { EASE, viewportOnce } from "@/lib/motion";
import { useCountUp } from "@/lib/use-count-up";
import { cn } from "@/lib/utils";
import { Card } from "@/components/vehicle/primitives";
import { mm2cm, vehicleName } from "@/lib/vehicle-format";
import type { Vehicle } from "@/services/vehicleService";

type Tone = "green" | "yellow" | "red";

const toneText: Record<Tone, string> = {
  green: "text-primary",
  yellow: "text-accent",
  red: "text-destructive",
};
const toneBorder: Record<Tone, string> = {
  green: "border-primary/40",
  yellow: "border-accent/40",
  red: "border-destructive/40",
};
const toneBg: Record<Tone, string> = {
  green: "bg-primary",
  yellow: "bg-accent",
  red: "bg-destructive",
};
const toneSoft: Record<Tone, string> = {
  green: "bg-primary/12",
  yellow: "bg-accent/12",
  red: "bg-destructive/12",
};

const label: Record<Tone, string> = {
  green: "Entra comodamente",
  yellow: "Entra ma con poco margine",
  red: "Non è compatibile",
};

const cm = (mm: number) => `${Math.round(mm / 10)} cm`;

function PreviewBadge() {
  const reduce = useReducedMotion();
  return (
    <span className="relative inline-flex items-center overflow-hidden rounded-full border border-border/70 bg-background px-2.5 py-1 text-[0.65rem] font-medium tracking-[0.14em] text-muted-foreground uppercase shadow-[0_0_0_1px_color-mix(in_oklab,var(--primary)_10%,transparent)]">
      Preview MVP
      {!reduce && (
        <motion.span
          aria-hidden
          className="pointer-events-none absolute inset-y-0 w-1/3 bg-linear-to-r from-transparent via-primary/25 to-transparent"
          initial={{ x: "-140%" }}
          animate={{ x: "340%" }}
          transition={{ duration: 1.6, repeat: Infinity, repeatDelay: 3.4, ease: "easeInOut" }}
        />
      )}
    </span>
  );
}

/** Numero che conta da 0 al valore, quando entra in viewport. */
function CountNumber({ value, delay = 0 }: { value: number; delay?: number }) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });
  const [start, setStart] = useState(false);
  useEffect(() => {
    if (!inView || start) return;
    const t = window.setTimeout(() => setStart(true), delay);
    return () => window.clearTimeout(t);
  }, [inView, start, delay]);
  const n = useCountUp(reduce || start ? value : 0, 900, Boolean(reduce));
  return (
    <span ref={ref} className="tabular-nums">
      {n}
    </span>
  );
}

/** Anima ogni numero contenuto in una stringa tipo "240 x 200 cm". */
function AnimatedMeasure({ value, delay = 0 }: { value: string; delay?: number }) {
  const parts = value.split(/(\d+)/);
  return (
    <>
      {parts.map((part, i) =>
        /^\d+$/.test(part) ? (
          <CountNumber key={i} value={Number(part)} delay={delay} />
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}

function DimRow({ label: l, value, delay = 0 }: { label: string; value: string; delay?: number }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-border/60 py-2.5 last:border-0">
      <span className="text-[0.85rem] text-muted-foreground">{l}</span>
      <span className="text-[0.9rem] font-medium tabular-nums text-foreground">
        <AnimatedMeasure value={value} delay={delay} />
      </span>
    </div>
  );
}

/** Diagramma dall'alto: garage + manovra di parcheggio + margini. */
function TopView({
  garageL,
  garageW,
  carL,
  carW,
  mirrorsW,
  tone,
  reduce,
  mirrorsActive,
  critical,
}: {
  garageL: number;
  garageW: number;
  carL: number;
  carW: number;
  mirrorsW?: number;
  tone: Tone;
  reduce: boolean | null;
  mirrorsActive: boolean;
  critical: "length" | "width";
}) {
  const pad = 26;
  const W = 520;
  const H = Math.round(((W - pad * 2) * garageW) / garageL) + pad * 2;
  const iw = W - pad * 2;
  const ih = H - pad * 2;
  const cw = (iw * carL) / garageL;
  const ch = (ih * carW) / garageW;
  const mw = mirrorsW ? (ih * mirrorsW) / garageW : null;
  const cx = pad + (iw - cw) / 2;
  const cy = pad + (ih - ch) / 2;

  const stroke =
    tone === "green" ? "var(--primary)" : tone === "yellow" ? "var(--accent)" : "var(--destructive)";

  const park = reduce
    ? { x: 0, y: 0, rotate: 0 }
    : {
        x: [W * 0.85, cw * 0.42, cw * 0.08, 0],
        y: [ch * 0.28, -ch * 0.1, ch * 0.03, 0],
        rotate: [4.5, -2.2, 0.6, 0],
      };

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="mx-auto w-full max-w-xl overflow-visible"
      role="img"
      aria-label="Vista dall'alto del garage con il veicolo e i margini liberi"
    >
      <defs>
        <pattern id="gf-hatch" width="8" height="8" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
          <line x1="0" y1="0" x2="0" y2="8" stroke="var(--border)" strokeWidth="4" />
        </pattern>
        <clipPath id="gf-clip">
          <rect x={pad - 2} y={pad - 2} width={iw + 4} height={ih + 4} rx="12" />
        </clipPath>
      </defs>

      {/* area garage */}
      <rect x={pad} y={pad} width={iw} height={ih} rx="10" fill="url(#gf-hatch)" opacity="0.5" />
      <rect
        x={pad}
        y={pad}
        width={iw}
        height={ih}
        rx="10"
        fill="none"
        stroke="var(--foreground)"
        strokeOpacity="0.25"
        strokeWidth="2"
      />

      <g clipPath="url(#gf-clip)">
        {/* ingombro specchietti */}
        {mw && (
          <motion.rect
            x={cx}
            y={pad + (ih - mw) / 2}
            width={cw}
            height={mw}
            rx="8"
            fill={stroke}
            animate={
              mirrorsActive && !reduce
                ? { opacity: [0.18, 0.42, 0.18] }
                : { opacity: mirrorsActive ? 0.34 : 0.12 }
            }
            transition={
              mirrorsActive && !reduce
                ? { duration: 1.4, repeat: Infinity, ease: "easeInOut" }
                : { duration: 0.3 }
            }
            stroke={stroke}
            strokeOpacity={mirrorsActive ? 0.6 : 0}
            strokeWidth="1.5"
          />
        )}

        {/* veicolo: manovra di parcheggio */}
        <motion.g
          initial={reduce ? { opacity: 1 } : { opacity: 0 }}
          whileInView={{ opacity: 1, ...park }}
          viewport={viewportOnce}
          transition={{
            duration: reduce ? 0 : 2.4,
            ease: [0.16, 0.8, 0.28, 1],
            ...(reduce ? {} : { times: [0, 0.42, 0.78, 1] }),
            opacity: { duration: 0.4, ease: EASE },
          }}
          style={{ transformOrigin: `${cx + cw / 2}px ${cy + ch / 2}px` }}
        >
          <rect x={cx} y={cy} width={cw} height={ch} rx="9" fill={stroke} opacity="0.85" />
          <rect
            x={cx + cw * 0.22}
            y={cy + ch * 0.16}
            width={cw * 0.36}
            height={ch * 0.68}
            rx="5"
            fill="var(--card)"
            opacity="0.35"
          />
        </motion.g>
      </g>

      {/* margine lunghezza */}
      <motion.g
        animate={
          critical === "length" && !reduce ? { opacity: [0.55, 1, 0.55] } : { opacity: 1 }
        }
        transition={
          critical === "length" && !reduce
            ? { duration: 1.8, repeat: Infinity, ease: "easeInOut", delay: 2.4 }
            : { duration: 0 }
        }
      >
        <line x1={pad} y1={H - 12} x2={cx} y2={H - 12} stroke={stroke} strokeWidth={critical === "length" ? 3 : 2} />
        <line x1={cx + cw} y1={H - 12} x2={W - pad} y2={H - 12} stroke={stroke} strokeWidth={critical === "length" ? 3 : 2} />
        <text
          x={(pad + cx) / 2}
          y={H - 16}
          textAnchor="middle"
          fontSize={critical === "length" ? 12 : 11}
          fontWeight={critical === "length" ? 700 : 400}
          fill={critical === "length" ? stroke : "var(--muted-foreground)"}
        >
          {cm(garageL - carL)}
        </text>
      </motion.g>

      {/* margine larghezza */}
      <motion.g
        animate={critical === "width" && !reduce ? { opacity: [0.55, 1, 0.55] } : { opacity: 1 }}
        transition={
          critical === "width" && !reduce
            ? { duration: 1.8, repeat: Infinity, ease: "easeInOut", delay: 2.4 }
            : { duration: 0 }
        }
      >
        <line x1={12} y1={pad} x2={12} y2={cy} stroke={stroke} strokeWidth={critical === "width" ? 3 : 2} />
        <line x1={12} y1={cy + ch} x2={12} y2={H - pad} stroke={stroke} strokeWidth={critical === "width" ? 3 : 2} />
        <text
          x={16}
          y={(pad + cy) / 2 + 4}
          fontSize={critical === "width" ? 12 : 11}
          fontWeight={critical === "width" ? 700 : 400}
          fill={critical === "width" ? stroke : "var(--muted-foreground)"}
        >
          {cm(garageW - carW)}
        </text>
      </motion.g>
    </svg>
  );
}

/** Misure del garage dichiarate dall'utente nella Scelta Guidata (mm). */
export type GarageInput = {
  garage_length_mm?: number | undefined;
  garage_width_mm?: number | undefined;
  garage_height_mm?: number | undefined;
  door_width_mm?: number | undefined;
  door_height_mm?: number | undefined;
  result?: "fits_comfortably" | "fits_tight" | "does_not_fit" | undefined;
};

export function GarageFit({ vehicle, garage }: { vehicle: Vehicle; garage?: GarageInput | undefined }) {
  const reduce = useReducedMotion();
  const g = garage;
  const d = vehicle.dimensions ?? {};
  const [target, setTarget] = useState(0);
  const score = useCountUp(target, 1400, Boolean(reduce));
  const [verdict, setVerdict] = useState(Boolean(reduce));
  const [mirrorsActive, setMirrorsActive] = useState(false);
  useEffect(() => {
    if (!target || verdict) return;
    const t = window.setTimeout(() => setVerdict(true), 1500);
    return () => window.clearTimeout(t);
  }, [target, verdict]);

  const vehicleRows = [
    d.length_mm ? { label: "Lunghezza", value: mm2cm(d.length_mm)! } : null,
    d.width_with_mirrors_mm
      ? { label: "Larghezza con specchietti", value: mm2cm(d.width_with_mirrors_mm)! }
      : null,
    d.height_mm ? { label: "Altezza", value: mm2cm(d.height_mm)! } : null,
  ].filter((r): r is { label: string; value: string } => Boolean(r));

  if (!g?.result || !g.garage_length_mm || !g.garage_width_mm) {
    return (
      <Card>
        <div className="flex items-start justify-between gap-4">
          <p className="max-w-md text-[0.9rem] text-muted-foreground">
            Indica le dimensioni del tuo garage nella Scelta Guidata per vedere la compatibilità.
          </p>
          <PreviewBadge />
        </div>
        <div className="mt-6">
          {vehicleRows.map((r) => (
            <DimRow key={r.label} label={r.label} value={r.value} />
          ))}
        </div>
      </Card>
    );
  }

  const carL = d.length_mm ?? 0;
  const mirrors = d.width_with_mirrors_mm ?? null;
  const carW = mirrors ?? 0;
  const carH = d.height_mm ?? 0;

  const marginL = g.garage_length_mm - carL;
  const marginW = g.garage_width_mm - carW;
  const marginMirrors = mirrors ? g.garage_width_mm - mirrors : null;
  const marginH = g.garage_height_mm ? g.garage_height_mm - carH : null;
  const doorMargin = g.door_width_mm ? g.door_width_mm - (mirrors ?? carW) : null;

  const tone: Tone =
    g.result === "does_not_fit" ? "red" : g.result === "fits_tight" ? "yellow" : "green";

  // Garage Fit Score 0-100 dai margini reali
  const norm = (v: number, ideal: number) => Math.max(0, Math.min(1, v / ideal));
  const rawScore =
    tone === "red"
      ? Math.round(28 * norm(marginL, 600))
      : Math.round(
          100 *
            (0.4 * norm(marginL, 600) +
              0.35 * norm(marginW, 700) +
              0.15 * norm(marginH ?? 300, 400) +
              0.1 * norm(doorMargin ?? 200, 300)),
        );
  const finalScore =
    tone === "green"
      ? Math.min(98, Math.max(80, rawScore))
      : tone === "yellow"
        ? Math.min(72, Math.max(48, rawScore))
        : Math.min(30, Math.max(5, rawScore));

  const name = vehicleName(vehicle);
  const narrative =
    tone === "red"
      ? `La ${name} non è compatibile con il tuo garage: mancano ${cm(Math.abs(Math.min(marginL, marginW)))} nella dimensione più critica.`
      : tone === "yellow"
        ? `La ${name} entra nel tuo garage, ma con poco margine: circa ${cm(marginL)} in lunghezza e ${cm(marginW)} in larghezza. Le manovre richiedono attenzione.`
        : `La ${name} è compatibile con il tuo garage. Hai circa ${cm(marginL)} di margine in lunghezza e ${cm(marginW)} in larghezza, sufficienti per parcheggiare con facilità.`;

  const insights: { icon: "ok" | "warn" | "info"; text: string }[] = [];
  if (marginW >= 500)
    insights.push({ icon: "ok", text: "Puoi aprire comodamente le portiere su entrambi i lati." });
  else if (marginW >= 350)
    insights.push({ icon: "info", text: "Le portiere si aprono, ma conviene parcheggiare centrato." });
  else insights.push({ icon: "warn", text: "Lo spazio laterale limita l'apertura delle portiere." });

  if (marginH !== null)
    insights.push(
      marginH >= 250
        ? { icon: "ok", text: `L'altezza è pienamente compatibile: ${cm(marginH)} liberi sopra il tetto.` }
        : marginH >= 80
          ? { icon: "info", text: `Restano ${cm(marginH)} sopra il tetto: attenzione a box da tetto o barre.` }
          : { icon: "warn", text: "L'altezza è al limite: verifica portellone e struttura del soffitto." },
    );

  if (marginMirrors !== null)
    insights.push(
      marginMirrors >= 400
        ? { icon: "ok", text: "Anche con gli specchietti aperti il margine laterale resta ampio." }
        : { icon: "warn", text: "Con gli specchietti aperti il margine laterale è ridotto." },
    );

  if (doorMargin !== null)
    insights.push(
      doorMargin >= 150
        ? { icon: "ok", text: `L'ingresso lascia ${cm(doorMargin)} di gioco totale in larghezza.` }
        : { icon: "warn", text: "L'ingresso è stretto: l'accesso richiede una manovra precisa." },
    );

  if (marginL < 400)
    insights.push({ icon: "warn", text: "Un SUV di segmento superiore probabilmente non sarebbe compatibile." });

  const garageRows = [
    { label: "Lunghezza", value: cm(g.garage_length_mm) },
    { label: "Larghezza", value: cm(g.garage_width_mm) },
    g.garage_height_mm ? { label: "Altezza", value: cm(g.garage_height_mm) } : null,
    g.door_width_mm
      ? {
          label: "Porta",
          value: g.door_height_mm
            ? `${cm(g.door_width_mm)} × ${cm(g.door_height_mm)}`
            : cm(g.door_width_mm),
        }
      : null,
  ].filter((r): r is { label: string; value: string } => Boolean(r));

  return (
    <div className="space-y-4">
      {/* 1. Hero */}
      <motion.div
        initial={reduce ? { opacity: 1 } : { opacity: 0, y: 14, scale: 0.98 }}
        whileInView={{ opacity: 1, y: 0, scale: 1 }}
        viewport={viewportOnce}
        transition={{ duration: 0.6, ease: EASE }}
        onViewportEnter={() => setTarget(finalScore)}
        className={cn(
          "relative overflow-hidden rounded-3xl border bg-card p-6 shadow-[var(--shadow-lift)] sm:p-8",
          "before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-linear-to-r before:from-transparent before:via-primary/50 before:to-transparent",
          toneBorder[tone],
        )}
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className={cn("size-2.5 rounded-full", toneBg[tone])} />
            <span className="text-[0.72rem] tracking-[0.14em] text-muted-foreground uppercase">
              Garage Fit Score
            </span>
          </div>
          <PreviewBadge />
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-x-8 gap-y-5">
          {/* Gauge circolare */}
          <div className="relative size-[8.5rem] shrink-0">
            <svg viewBox="0 0 120 120" className="size-full -rotate-90">
              <circle
                cx="60"
                cy="60"
                r="52"
                fill="none"
                stroke="currentColor"
                className="text-muted"
                strokeWidth="9"
              />
              <motion.circle
                cx="60"
                cy="60"
                r="52"
                fill="none"
                stroke={
                  tone === "green"
                    ? "var(--primary)"
                    : tone === "yellow"
                      ? "var(--accent)"
                      : "var(--destructive)"
                }
                strokeWidth="9"
                strokeLinecap="round"
                initial={{ pathLength: 0 }}
                whileInView={{ pathLength: finalScore / 100 }}
                viewport={viewportOnce}
                transition={{ duration: reduce ? 0 : 1.4, ease: EASE }}
                style={{
                  filter: `drop-shadow(0 0 ${tone === "green" ? 4 : 8}px currentColor)`,
                  opacity: tone === "green" ? 0.9 : 1,
                }}
              />
            </svg>
            <div className="absolute inset-0 grid place-items-center">
              <div className="text-center">
                <span
                  className={cn(
                    "font-heading text-[2.6rem] leading-[0.9] font-bold tabular-nums tracking-[-0.04em]",
                    toneText[tone],
                  )}
                >
                  {score}
                </span>
                <div className="text-[0.7rem] text-muted-foreground">/100</div>
              </div>
            </div>
          </div>

          <div className="min-w-[12rem] flex-1">
            <motion.p
              initial={false}
              animate={
                verdict ? { opacity: 1, y: 0 } : { opacity: reduce ? 1 : 0, y: reduce ? 0 : 8 }
              }
              transition={{ duration: 0.5, ease: EASE }}
              className="font-heading text-[1.15rem] font-semibold tracking-[-0.02em] sm:text-[1.3rem]"
            >
              {label[tone]}
            </motion.p>
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <motion.div
                initial={{ scaleX: 0 }}
                whileInView={{ scaleX: finalScore / 100 }}
                viewport={viewportOnce}
                transition={{ duration: reduce ? 0 : 1.4, ease: EASE }}
                className={cn("h-full w-full origin-left rounded-full", toneBg[tone])}
              />
            </div>
          </div>
        </div>

        {/* 2. Testo generato */}
        <p className="mt-6 max-w-2xl text-[0.95rem] leading-relaxed text-foreground/85">
          {narrative}
        </p>
      </motion.div>

      {/* 3. Diagramma */}
      <motion.div
        {...(reduce ? {} : { whileHover: { y: -3 } })}
        transition={{ duration: 0.3, ease: EASE }}
        className="rounded-3xl border border-border/70 bg-card p-5 shadow-[var(--shadow-soft)] transition-shadow duration-300 hover:border-primary/30 hover:shadow-[var(--shadow-lift)] sm:p-6"
      >
        <div className="flex items-center gap-2">
          <Ruler className="size-4 text-muted-foreground" />
          <p className="text-[0.72rem] tracking-[0.14em] text-muted-foreground uppercase">
            Vista dall'alto
          </p>
        </div>
        <div className="mt-4">
          <TopView
            garageL={g.garage_length_mm}
            garageW={g.garage_width_mm}
            carL={carL}
            carW={carW}
            {...(mirrors ? { mirrorsW: mirrors } : {})}
            tone={tone}
            reduce={reduce}
            mirrorsActive={mirrorsActive}
            critical={marginL <= marginW ? "length" : "width"}
          />
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-2 text-[0.75rem] text-muted-foreground">
          <span className="inline-flex items-center gap-2">
            <span className={cn("size-2.5 rounded-[3px]", toneBg[tone])} /> Veicolo
          </span>
          {mirrors && (
            <button
              type="button"
              onMouseEnter={() => setMirrorsActive(true)}
              onMouseLeave={() => setMirrorsActive(false)}
              onFocus={() => setMirrorsActive(true)}
              onBlur={() => setMirrorsActive(false)}
              className={cn(
                "inline-flex items-center gap-2 rounded-full px-2 py-1 transition-colors",
                mirrorsActive ? "bg-muted text-foreground" : "hover:bg-muted/60",
              )}
            >
              <span className={cn("size-2.5 rounded-[3px]", toneSoft[tone])} /> Ingombro specchietti
            </button>
          )}
          <span className="inline-flex items-center gap-2">
            <span className="size-2.5 rounded-[3px] bg-muted" /> Spazio libero
          </span>
        </div>
      </motion.div>

      {/* 4. Due card affiancate */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="p-5 sm:p-6">
          <div className="flex items-center gap-2">
            <DoorOpen className="size-4 text-muted-foreground" />
            <p className="text-[0.72rem] tracking-[0.14em] text-muted-foreground uppercase">
              Il tuo garage
            </p>
          </div>
          <div className="mt-3">
            {garageRows.map((r, i) => (
              <DimRow key={r.label} label={r.label} value={r.value} delay={i * 120} />
            ))}
          </div>
        </Card>
        <Card className="p-5 sm:p-6">
          <div className="flex items-center gap-2">
            <Ruler className="size-4 text-muted-foreground" />
            <p className="text-[0.72rem] tracking-[0.14em] text-muted-foreground uppercase">
              Il veicolo
            </p>
          </div>
          <div className="mt-3">
            {vehicleRows.map((r, i) => (
              <DimRow key={r.label} label={r.label} value={r.value} delay={i * 120} />
            ))}
          </div>
        </Card>
      </div>

      {/* 5. Insight */}
      <Card className="p-5 sm:p-6">
        <p className="text-[0.72rem] tracking-[0.14em] text-muted-foreground uppercase">
          Insight DriveWise
        </p>
        <motion.ul
          initial="hidden"
          whileInView="show"
          viewport={viewportOnce}
          variants={{ hidden: {}, show: { transition: { staggerChildren: reduce ? 0 : 0.09 } } }}
          className="mt-4 grid gap-3 sm:grid-cols-2"
        >
          {insights.slice(0, 4).map((it) => (
            <motion.li
              key={it.text}
              variants={{
                hidden: reduce ? { opacity: 1 } : { opacity: 0, y: 10, scale: 0.97 },
                show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.5, ease: EASE } },
              }}
              className="flex items-start gap-3 rounded-2xl border border-border/70 bg-background/60 p-3.5"
            >
              <span
                className={cn(
                  "mt-0.5 grid size-7 shrink-0 place-items-center rounded-full",
                  it.icon === "ok"
                    ? "bg-primary/15 text-primary"
                    : it.icon === "warn"
                      ? "bg-accent/15 text-accent"
                      : "bg-muted text-muted-foreground",
                )}
              >
                {it.icon === "ok" ? (
                  <Check className="size-3.5" />
                ) : it.icon === "warn" ? (
                  <AlertTriangle className="size-3.5" />
                ) : (
                  <Info className="size-3.5" />
                )}
              </span>
              <span className="text-[0.875rem] leading-relaxed text-foreground/90">{it.text}</span>
            </motion.li>
          ))}
        </motion.ul>
      </Card>
    </div>
  );
}