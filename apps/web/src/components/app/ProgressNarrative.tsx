import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { EASE } from "@/lib/motion";
import { progressNarrative } from "@/lib/wizard-theme";

/** Frase contestuale che si "digita" e cambia con l'avanzare del profilo. */
export function ProgressNarrative({ completion }: { completion: number }) {
  const reduce = useReducedMotion();
  const full = progressNarrative(completion);

  return (
    <div className="flex items-center gap-2.5" aria-live="polite">
      <motion.span
        className="size-1.5 shrink-0 rounded-full bg-primary"
        animate={reduce ? {} : { opacity: [0.3, 1, 0.3], scale: [1, 1.25, 1] }}
        transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
      />
      <AnimatePresence mode="wait">
        <motion.p
          key={full}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.35, ease: EASE }}
          className="text-[0.82rem] text-muted-foreground"
        >
          {full}
        </motion.p>
      </AnimatePresence>
    </div>
  );
}
