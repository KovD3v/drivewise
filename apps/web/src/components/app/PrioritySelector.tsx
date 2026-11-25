import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { OptionCheck } from "./OptionCheck";
import { EASE } from "@/lib/motion";
import { cn } from "@/lib/utils";

export function PrioritySelector({
  options,
  onConfirm,
  confirmLabel = "Conferma selezione",
  max = 3,
  exclusive = [],
  ranked = true,
}: {
  options: string[];
  onConfirm: (picked: string[]) => void;
  confirmLabel?: string;
  /** How many options one answer may hold. */
  max?: number;
  /** Options that stand alone, such as "none": picking one clears the others, and the reverse. */
  exclusive?: string[];
  /** Whether the pick order is a ranking, shown as 1°, 2°, 3°. */
  ranked?: boolean;
}) {
  const [picked, setPicked] = useState<string[]>([]);

  const toggle = (o: string) => {
    setPicked((prev) => {
      if (prev.includes(o)) return prev.filter((p) => p !== o);
      if (exclusive.includes(o)) return [o];
      const others = prev.filter((p) => !exclusive.includes(p));
      return others.length < max ? [...others, o] : others;
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: EASE }}
      className="rounded-3xl border border-border/70 bg-card p-5 shadow-[var(--shadow-object)] sm:p-6"
    >
      <div className="flex flex-wrap gap-2.5">
        {options.map((o) => {
          const rank = picked.indexOf(o);
          const active = rank >= 0;
          return (
            <motion.button
              key={o}
              type="button"
              onClick={() => toggle(o)}
              aria-pressed={active}
              whileTap={{ scale: 0.97 }}
              animate={active ? { scale: [1, 1.05, 1] } : { scale: 1 }}
              transition={{ duration: 0.35, ease: EASE }}
              className={cn(
                "relative inline-flex items-center gap-2 rounded-full border px-5 py-2.5 text-[0.9rem] transition-all duration-300",
                active
                  ? "border-primary bg-primary text-primary-foreground shadow-[var(--shadow-lift)]"
                  : "border-border/70 bg-background text-muted-foreground hover:-translate-y-0.5 hover:border-primary hover:bg-primary/8 hover:text-foreground hover:shadow-[var(--shadow-lift)]",
                // Dim only the options that can no longer be added.
                !active && picked.length >= max && !exclusive.includes(o) && "opacity-55",
              )}
            >
              <AnimatePresence initial={false}>
                {active && (
                  <motion.span
                    initial={{ opacity: 0, scale: 0.7 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.7 }}
                    transition={{ duration: 0.25, ease: EASE }}
                    className="flex items-center gap-1.5"
                  >
                    <OptionCheck />
                    {ranked && <span className="text-[0.7rem] font-bold">{rank + 1}°</span>}
                  </motion.span>
                )}
              </AnimatePresence>
              {o}
            </motion.button>
          );
        })}
      </div>
      <div className="mt-5 flex items-center gap-4">
        <button
          type="button"
          disabled={picked.length === 0}
          onClick={() => onConfirm(picked)}
          className="inline-flex h-11 items-center rounded-full bg-primary px-6 text-sm font-medium text-primary-foreground transition-all duration-300 hover:bg-primary-hover hover:shadow-[var(--shadow-lift)] disabled:opacity-40"
        >
          {confirmLabel}
        </button>
        <span className="text-[0.8rem] text-muted-foreground">{picked.length}/{max} selezionate</span>
      </div>
    </motion.div>
  );
}