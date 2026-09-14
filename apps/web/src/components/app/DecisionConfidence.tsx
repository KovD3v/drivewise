import { motion, useReducedMotion } from "framer-motion";
import { Info } from "lucide-react";
import { EASE } from "@/lib/motion";
import { useCountUp } from "@/lib/use-count-up";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function DecisionConfidence({ value }: { value: number }) {
  const reduce = useReducedMotion();
  const shown = useCountUp(value, 1200, !!reduce);

  return (
    <div className="rounded-2xl border border-primary/25 bg-card p-5 shadow-[var(--shadow-soft)]">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <h3 className="font-heading text-[0.95rem] font-semibold text-foreground">
            Decision Confidence
          </h3>
          <TooltipProvider delayDuration={120}>
            <Tooltip>
              <TooltipTrigger
                aria-label="Cos'è la Decision Confidence"
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                <Info className="size-3.5" />
              </TooltipTrigger>
              <TooltipContent className="max-w-xs text-[0.8rem] leading-relaxed">
                Prima dell’analisi indica la completezza delle informazioni iniziali.
                Dopo l’analisi viene fornita dal motore decisionale. Non è una probabilità.
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        <span className="font-heading text-[1.35rem] font-bold tabular-nums text-foreground">
          {shown}%
        </span>
      </div>
      <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full origin-left rounded-full bg-accent/70"
          initial={{ scaleX: 0 }}
          animate={{ scaleX: value / 100 }}
          transition={{ duration: reduce ? 0 : 1.3, ease: EASE }}
          style={{ width: "100%" }}
        />
      </div>
    </div>
  );
}