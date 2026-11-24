import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { OptionCheck } from "./OptionCheck";
import { EASE } from "@/lib/motion";
import { cn } from "@/lib/utils";

const ordinals = ["1°", "2°", "3°"];

export function PrioritySelector({
  options,
  onConfirm,
  confirmLabel = "Conferma selezione",
}: {
  options: string[];
  onConfirm: (picked: string[]) => void;
  confirmLabel?: string;
}) {
  const [picked, setPicked] = useState<string[]>([]);

  const toggle = (o: string) => {
    setPicked((prev) =>
      prev.includes(o) ? prev.filter((p) => p !== o) : prev.length < 3 ? [...prev, o] : prev,
    );
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
                picked.length > 0 && !active && "opacity-55",
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
                    <span className="text-[0.7rem] font-bold">{ordinals[rank]}</span>
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
        <span className="text-[0.8rem] text-muted-foreground">{picked.length}/3 selezionate</span>
      </div>
    </motion.div>
  );
}