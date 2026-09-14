import { motion } from "framer-motion";
import { EASE } from "@/lib/motion";

export function UserMessage({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: EASE }}
      className="flex justify-end"
    >
      <p className="max-w-[80%] rounded-3xl rounded-br-lg border border-border/60 bg-card px-5 py-3.5 text-[0.95rem] text-foreground shadow-[var(--shadow-soft)]">
        {children}
      </p>
    </motion.div>
  );
}