import { motion, useReducedMotion } from "framer-motion";
import { EASE } from "@/lib/motion";
import { useCountUp } from "@/lib/use-count-up";

export function ProfileCompletion({ value }: { value: number }) {
  const reduce = useReducedMotion();
  const shown = useCountUp(value, 900, !!reduce);

  return (
    <div className="rounded-2xl border border-border/70 bg-card p-5 shadow-[var(--shadow-soft)]">
      <div className="flex items-baseline justify-between">
        <h3 className="font-heading text-[0.95rem] font-semibold text-foreground">
          Profilo Decisionale
        </h3>
        <span className="font-heading text-[1.35rem] font-bold tabular-nums text-foreground">
          {shown}%
        </span>
      </div>
      <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full origin-left rounded-full bg-primary"
          initial={{ scaleX: 0 }}
          animate={{ scaleX: value / 100 }}
          transition={{ duration: reduce ? 0 : 1.1, ease: EASE }}
          style={{ width: "100%" }}
        />
      </div>
      <p className="mt-3 text-[0.8125rem] text-muted-foreground">
        Stiamo affinando la tua scelta.
      </p>
    </div>
  );
}