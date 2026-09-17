import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { EASE } from "@/lib/motion";
import type { Fact } from "@/lib/decision-profile";

export function ExtractedFacts({ facts, delay = 0 }: { facts: Fact[]; delay?: number }) {
  return (
    <motion.ul
      initial="hidden"
      animate="show"
      variants={{ hidden: {}, show: { transition: { staggerChildren: 0.22, delayChildren: delay } } }}
      className="grid gap-3 sm:grid-cols-2"
    >
      {facts.map((f) => (
        <motion.li
          key={f.id}
          variants={{
            hidden: { opacity: 0, y: 12, scale: 0.97 },
            show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.55, ease: EASE } },
          }}
          className="group flex items-center gap-3 rounded-2xl border border-border/70 bg-card p-4 shadow-[var(--shadow-soft)] transition-all duration-300 hover:-translate-y-1 hover:border-primary/35 hover:shadow-[var(--shadow-card-hover)]"
        >
          <span className="grid size-8 shrink-0 place-items-center rounded-full bg-primary/15 text-foreground transition-colors duration-300 group-hover:bg-primary/25">
            <Check className="size-4" />
          </span>
          <span className="min-w-0">
            <span className="block text-[0.7rem] tracking-[0.12em] text-muted-foreground uppercase">
              {f.label}
            </span>
            <span className="block truncate text-[0.95rem] font-medium text-foreground">{f.value}</span>
          </span>
        </motion.li>
      ))}
    </motion.ul>
  );
}