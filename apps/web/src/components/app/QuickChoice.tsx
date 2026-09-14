import { useState } from "react";
import { motion } from "framer-motion";
import { OptionCheck } from "./OptionCheck";
import { EASE } from "@/lib/motion";
import { cn } from "@/lib/utils";

type Props = {
  options: string[];
  allowCustom?: boolean;
  customLabel?: string;
  onSelect: (value: string) => void;
  disabled?: boolean;
};

export function QuickChoice({
  options,
  allowCustom = false,
  customLabel = "Scrivi un valore",
  onSelect,
  disabled,
}: Props) {
  const [custom, setCustom] = useState(false);
  const [value, setValue] = useState("");
  const [picked, setPicked] = useState<string | null>(null);

  /** Feedback immediato: il bordo si illumina e il check si disegna prima di avanzare. */
  const choose = (v: string) => {
    if (picked) return;
    setPicked(v);
    window.setTimeout(() => onSelect(v), 420);
  };

  return (
    <motion.div
      initial="hidden"
      animate="show"
      variants={{ hidden: {}, show: { transition: { staggerChildren: 0.07 } } }}
      className="flex flex-col gap-2.5 sm:flex-row sm:flex-wrap"
    >
      {options.map((o) => {
        const active = picked === o;
        return (
          <motion.button
            key={o}
            type="button"
            disabled={disabled || !!picked}
            onClick={() => choose(o)}
            aria-pressed={active}
            whileTap={{ scale: 0.97 }}
            animate={active ? { scale: [1, 1.05, 1] } : { scale: 1 }}
            transition={{ duration: 0.35, ease: EASE }}
            variants={{
              hidden: { opacity: 0, y: 8 },
              show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: EASE } },
            }}
            className={cn(
              "inline-flex w-full items-center justify-center gap-2 rounded-full border px-5 py-3 text-[0.9rem] shadow-[var(--shadow-soft)] transition-all duration-300 sm:w-auto",
              active
                ? "border-primary bg-primary text-primary-foreground shadow-[var(--shadow-lift)]"
                : "border-border/70 bg-card text-foreground hover:-translate-y-0.5 hover:border-primary hover:bg-primary/8 hover:shadow-[var(--shadow-lift)]",
              picked && !active && "opacity-40",
            )}
          >
            {active && <OptionCheck />}
            {o}
          </motion.button>
        );
      })}

      {allowCustom &&
        !picked &&
        (custom ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (value.trim()) choose(value.trim());
            }}
            className="flex w-full gap-2 sm:w-auto"
          >
            <input
              autoFocus
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder={customLabel}
              className="h-11 w-full rounded-full border border-primary/40 bg-card px-5 text-[0.9rem] outline-none placeholder:text-foreground/40 focus:shadow-[var(--shadow-focus)] sm:w-52"
            />
            <button
              type="submit"
              className="h-11 shrink-0 rounded-full bg-primary px-5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-hover"
            >
              Conferma
            </button>
          </form>
        ) : (
          <motion.button
            type="button"
            disabled={disabled}
            onClick={() => setCustom(true)}
            variants={{
              hidden: { opacity: 0, y: 8 },
              show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: EASE } },
            }}
            className="w-full rounded-full px-5 py-3 text-[0.9rem] text-muted-foreground transition-colors duration-300 hover:text-foreground sm:w-auto"
          >
            {customLabel}
          </motion.button>
        ))}
    </motion.div>
  );
}
