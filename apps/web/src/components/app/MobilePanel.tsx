import { useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export function MobilePanel({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <div className="lg:hidden">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          className="flex w-full items-center justify-between rounded-2xl border border-border/70 bg-card px-5 py-4 text-left shadow-[var(--shadow-soft)]"
        >
          <span className="font-heading text-[0.95rem] font-semibold">Profilo decisionale</span>
          <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
        </button>
        <AnimatePresence initial={false}>
          {open && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
              <div className="pt-4">{children}</div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      <div className="hidden lg:sticky lg:top-8 lg:block">{children}</div>
    </>
  );
}
