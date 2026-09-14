import { AnimatePresence, motion } from "framer-motion";
import { Check } from "lucide-react";
import { EASE } from "@/lib/motion";
import { ProfileCompletion } from "./ProfileCompletion";
import { DecisionConfidence } from "./DecisionConfidence";
import { PreviewRanking } from "./PreviewRanking";
import type { MissingItem } from "@/lib/decision-profile";
import type { PreviewVehicle } from "@/lib/decision-engine";

type Props = {
  known: string[];
  missing: MissingItem[];
  completion: number;
  confidence: number;
  ranking: PreviewVehicle[];
};

export function DecisionProfilePanel({ known, missing, completion, confidence, ranking }: Props) {
  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border/70 bg-card p-5 shadow-[var(--shadow-soft)]">
        <div className="flex items-baseline justify-between gap-2">
          <h3 className="font-heading text-[0.95rem] font-semibold text-foreground">
            DriveWise conosce già…
          </h3>
          <span className="text-[0.72rem] tabular-nums text-muted-foreground">
            {known.length} dati
          </span>
        </div>
        <ul className="mt-4 flex flex-wrap gap-2">
          <AnimatePresence initial={false}>
            {known.map((k, i) => (
              <motion.li
                key={k}
                layout
                initial={{ opacity: 0, y: 6, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ duration: 0.45, delay: i * 0.06, ease: EASE }}
                className="inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/[0.08] px-3 py-1.5 text-[0.8125rem] text-foreground"
              >
                <Check className="size-3 shrink-0" />
                {k}
              </motion.li>
            ))}
          </AnimatePresence>
          {known.length === 0 && (
            <li className="text-[0.8125rem] text-muted-foreground">
              Ancora nulla. Inizia raccontando cosa cerchi.
            </li>
          )}
        </ul>

        <div className="mt-6 border-t border-border/70 pt-5">
          <h3 className="font-heading text-[0.95rem] font-semibold text-foreground">
            Ci serve ancora…
          </h3>
          <ul className="mt-4 space-y-2.5">
            {missing.map((m) => (
              <motion.li
                key={m.id}
                layout
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-2.5 text-[0.875rem] text-muted-foreground"
              >
                <span className="size-5 shrink-0 rounded-full border border-border" />
                {m.label}
              </motion.li>
            ))}
            {missing.length === 0 && (
              <li className="text-[0.8125rem] text-muted-foreground">
                Nulla: il profilo è completo.
              </li>
            )}
          </ul>
        </div>
      </div>

      <ProfileCompletion value={completion} />
      <DecisionConfidence value={confidence} />
      {confidence > 45 && ranking.length > 0 && <PreviewRanking ranking={ranking} />}
    </div>
  );
}