import { motion } from "framer-motion";
import { EASE } from "@/lib/motion";
import { cn } from "@/lib/utils";

export function DecisionMessage({
  children,
  muted = false,
  delay = 0,
}: {
  children: React.ReactNode;
  muted?: boolean;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay, ease: EASE }}
      className="flex gap-3.5"
    >
      <span
        aria-hidden
        className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-full border border-primary/25 bg-primary/10 text-foreground"
      >
        <svg
          viewBox="0 0 24 24"
          className="size-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
        >
          <path d="M4 16.5c4.5 0 6-11 8-11s3.5 11 8 11" />
        </svg>
      </span>
      <div
        className={cn(
          "max-w-[85%] space-y-1.5 text-[0.98rem] leading-relaxed",
          muted ? "text-muted-foreground" : "text-foreground",
        )}
      >
        {children}
      </div>
    </motion.div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 py-1" aria-label="DriveWise sta scrivendo">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="size-1.5 rounded-full bg-primary"
          animate={{ opacity: [0.25, 1, 0.25] }}
          transition={{ duration: 1.1, repeat: Infinity, delay: i * 0.18, ease: "easeInOut" }}
        />
      ))}
    </div>
  );
}