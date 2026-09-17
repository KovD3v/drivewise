import { motion, useReducedMotion } from "framer-motion";
import { EASE } from "@/lib/motion";
import { useCountUp } from "@/lib/use-count-up";
import type { PreviewVehicle } from "@/lib/decision-engine";

export function VehiclePreviewCard({ vehicle, index }: { vehicle: PreviewVehicle; index: number }) {
  const reduce = useReducedMotion();
  const score = useCountUp(vehicle.score, 800, !!reduce);

  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.55, delay: index * 0.08, ease: EASE }}
      className="group rounded-2xl border border-border/70 bg-card p-4 shadow-[var(--shadow-soft)] transition-all duration-300 hover:-translate-y-1 hover:border-primary/35 hover:shadow-[var(--shadow-card-hover)]"
    >
      <div className="block">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-[0.9rem] font-medium text-foreground">{vehicle.name}</p>
          <p className="mt-0.5 text-[0.75rem] text-muted-foreground">{vehicle.segment}</p>
        </div>
        <span className="font-heading text-[1.05rem] font-bold tabular-nums text-foreground">
          {score}%
        </span>
      </div>
      <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full origin-left rounded-full bg-primary"
          animate={{ scaleX: vehicle.score / 100 }}
          initial={{ scaleX: 0 }}
          transition={{ duration: reduce ? 0 : 0.9, ease: EASE }}
          style={{ width: "100%" }}
        />
      </div>
      <p className="mt-2 text-[0.7rem] tracking-[0.1em] text-muted-foreground uppercase">
        {vehicle.decisionStatus === 'insufficient_data' ? 'Valutazione provvisoria: dati insufficienti' : 'Compatibilità'}
      </p>
      </div>
    </motion.li>
  );
}
