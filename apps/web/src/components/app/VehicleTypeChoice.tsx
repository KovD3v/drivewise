import { useState } from "react";
import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { EASE } from "@/lib/motion";
import { cn } from "@/lib/utils";

/**
 * Primo step del wizard: tre card con icona outline dedicata, micro-movimento
 * continuo (CSS puro) e selezione celebrativa. Nessun colore o font nuovo.
 */

type Kind = "car" | "motorcycle" | "scooter";

/** Tratto principale marcato (silhouette) e tratto sottile (dettagli interni). */
const bold = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2.1,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};
const thin = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.05,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  opacity: 0.7,
};

type IconProps = { drawKey: number };

function Svg({ children, drawKey }: { children: React.ReactNode; drawKey: number }) {
  return (
    <svg
      key={drawKey}
      viewBox="0 0 56 34"
      aria-hidden
      className="dw-draw size-10 text-foreground"
    >
      {children}
    </svg>
  );
}

/* SUV moderno: cofano basso, tetto affusolato, passaruota marcati. */
function CarIcon({ drawKey }: IconProps) {
  return (
    <Svg drawKey={drawKey}>
      <g {...bold}>
        <path
          pathLength={1}
          d="M3.5 25.5v-5.2c0-2.1 1.1-3.4 3.2-3.9l4.8-1.1 4.6-6.4c1.3-1.8 2.8-2.6 5-2.6h11.6c2.1 0 3.8.8 5.2 2.3l5.6 6.1 5.4 1.4c2.3.6 3.4 2 3.4 4.2v5.2"
        />
        <path pathLength={1} d="M20.5 25.5h15" />
        {/* passaruota */}
        <path pathLength={1} d="M10.6 25.5c0-2.7 2.2-4.9 4.9-4.9s4.9 2.2 4.9 4.9" />
        <path pathLength={1} d="M35.6 25.5c0-2.7 2.2-4.9 4.9-4.9s4.9 2.2 4.9 4.9" />
      </g>
      <g {...thin}>
        <path pathLength={1} d="M19.9 9.4l-4.2 5.8h10.2V9.4z" />
        <path pathLength={1} d="M28.4 9.4v5.8h11.2l-5.2-5.8z" />
        <path pathLength={1} d="M26.9 15.8v9.7" />
        <path pathLength={1} d="M7.6 20.4h4.2" />
      </g>
      <g className="text-primary" stroke="currentColor" fill="none" strokeLinecap="round">
        <circle pathLength={1} cx="15.5" cy="25.6" r="4.6" strokeWidth={2.2} className="dw-wheel" />
        <circle pathLength={1} cx="40.5" cy="25.6" r="4.6" strokeWidth={2.2} className="dw-wheel" />
        <path pathLength={1} d="M48.4 20.6h4.1" strokeWidth={1.7} />
      </g>
    </Svg>
  );
}

/* Moto: manubrio alto, sella arretrata, terminale di scarico. */
function MotorcycleIcon({ drawKey }: IconProps) {
  return (
    <Svg drawKey={drawKey}>
      <g {...bold}>
        {/* carena + serbatoio + codone */}
        <path
          pathLength={1}
          d="M15 13.4l5.2-2.4c1.8-.8 3.4-.6 4.6.8l2.4 2.8h6.6c2 0 3.3.7 4.4 2.3l3.6 5.4"
        />
        <path pathLength={1} d="M27.2 14.6c-2.6 2.4-5.6 3.6-9 3.6" />
        {/* sella e codone rialzato */}
        <path pathLength={1} d="M33.8 14.2c2.4-.2 4-1.4 4.8-3.6" />
        {/* forcella anteriore */}
        <path pathLength={1} d="M17.4 12.6L14 23.4" />
        {/* manubrio */}
        <path pathLength={1} d="M13.6 9.4l4.6 1.6" />
      </g>
      <g {...thin}>
        <path pathLength={1} d="M18.2 18.2l3.4 5.2" />
        <path pathLength={1} d="M27.4 17.8l1.6 5.6" />
        <path pathLength={1} d="M38.4 10.4l3 .6" />
      </g>
      <g className="text-primary" stroke="currentColor" fill="none" strokeLinecap="round">
        <circle pathLength={1} cx="13.6" cy="23.6" r="6.4" strokeWidth={2.2} className="dw-wheel" />
        <circle pathLength={1} cx="41.6" cy="23.6" r="6.4" strokeWidth={2.2} className="dw-wheel" />
        {/* scarico */}
        <path pathLength={1} d="M31.6 21.6h8.6" strokeWidth={2} />
      </g>
    </Svg>
  );
}

/* Scooter: pedana bassa e continua, scudo frontale, ruote piccole. */
function ScooterIcon({ drawKey }: IconProps) {
  return (
    <Svg drawKey={drawKey}>
      <g {...bold}>
        {/* scudo frontale che scende sulla pedana bassa */}
        <path pathLength={1} d="M18.6 12c-3.4 2.4-5.2 5.6-5.4 10" />
        <path pathLength={1} d="M15.6 25.2h11.6" />
        {/* pedana bassa continua verso il corpo posteriore */}
        <path
          pathLength={1}
          d="M13.6 22.4c0 1.9.8 2.8 2.6 2.8h11.4c1.5 0 2.4-.7 2.9-2.1l2.6-7.6c.8-2.3 2.2-3.4 4.6-3.4h4.2c2.6 0 4.1 1.3 4.6 3.8l1 4.8"
        />
        {/* sella */}
        <path pathLength={1} d="M32 17.6h9.6" />
        {/* manubrio */}
        <path pathLength={1} d="M16.4 11.6l5-3.2" />
      </g>
      <g {...thin}>
        <path pathLength={1} d="M18.8 25.2v-2.4h9" />
        <path pathLength={1} d="M20.4 10.8l2.6 1.2" />
      </g>
      <g className="text-primary" stroke="currentColor" fill="none" strokeLinecap="round">
        <circle pathLength={1} cx="17.8" cy="24.6" r="4.4" strokeWidth={2.2} className="dw-wheel" />
        <circle pathLength={1} cx="41.4" cy="24.6" r="4.4" strokeWidth={2.2} className="dw-wheel" />
        {/* faro nello scudo */}
        <path pathLength={1} d="M14.6 15.2c1-1 2-1.7 3.2-2.2" strokeWidth={2} />
      </g>
    </Svg>
  );
}

const icons: Record<Kind, (p: IconProps) => React.ReactElement> = {
  car: CarIcon,
  motorcycle: MotorcycleIcon,
  scooter: ScooterIcon,
};

export type TypeCardOption = { value: string; label: string; kind: Kind };

export function VehicleTypeChoice({
  options,
  onSelect,
}: {
  options: TypeCardOption[];
  onSelect: (value: string) => void;
}) {
  const [picked, setPicked] = useState<string | null>(null);

  const choose = (value: string) => {
    if (picked) return;
    setPicked(value);
    window.setTimeout(() => onSelect(value), 560);
  };

  return (
    <motion.div
      initial="hidden"
      animate="show"
      variants={{ hidden: {}, show: { transition: { staggerChildren: 0.12 } } }}
      className="grid gap-3 sm:grid-cols-3"
    >
      {options.map((o, i) => {
        const Icon = icons[o.kind];
        const active = picked === o.value;
        return (
          <motion.button
            key={o.value}
            type="button"
            onClick={() => choose(o.value)}
            disabled={!!picked}
            aria-pressed={active}
            variants={{
              hidden: { opacity: 0, y: 14 },
              show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE } },
            }}
            whileHover={{ y: picked ? 0 : -3 }}
            whileTap={{ scale: 0.98 }}
            animate={
              picked && !active ? { opacity: 0.45, scale: 0.97 } : { opacity: 1, scale: 1 }
            }
            transition={{ duration: 0.35, ease: EASE }}
            className={cn(
              "group relative flex flex-col items-center gap-3 overflow-hidden rounded-2xl border bg-card px-5 py-6 text-[0.95rem] shadow-[var(--shadow-soft)] transition-all duration-300",
              active
                ? "border-primary/60 shadow-[var(--shadow-focus)]"
                : "border-border/70 hover:border-primary/45 hover:shadow-[var(--shadow-lift)]",
            )}
          >
            <span
              className="relative grid size-14 place-items-center overflow-hidden rounded-full bg-primary/10 transition-transform duration-300 group-hover:scale-105"
              style={{ ["--dw-draw-delay" as string]: `${140 + i * 120}ms` }}
            >
              {active && (
                <span className="dw-ring-pulse absolute inset-0 rounded-full border border-primary/60" />
              )}
              <span className="dw-shine pointer-events-none absolute inset-y-0 -left-2 w-6 bg-gradient-to-r from-transparent via-primary/45 to-transparent" />
              <motion.span
                animate={active ? { scale: [1, 1.18, 1] } : { scale: 1 }}
                transition={{ duration: 0.45, ease: EASE }}
                className="grid place-items-center"
              >
                <Icon drawKey={i} />
              </motion.span>
              {active && (
                <motion.span
                  initial={{ scale: 0.4, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ duration: 0.3, ease: EASE }}
                  className="absolute -right-1 -bottom-1 grid size-5 place-items-center rounded-full bg-primary text-primary-foreground"
                >
                  <Check className="size-3" />
                </motion.span>
              )}
            </span>
            <span className="font-heading font-semibold text-foreground">{o.label}</span>
          </motion.button>
        );
      })}
    </motion.div>
  );
}