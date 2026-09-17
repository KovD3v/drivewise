import { useEffect, useState, useId } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Mic } from "lucide-react";
import { cn } from "@/lib/utils";
import { EASE } from "@/lib/motion";

type Props = {
  suggestions?: string[];
  placeholder?: string;
  disabled?: boolean;
  /** Testo che arriva dalla Decision Bar della Landing: mantiene la continuità visiva. */
  initialValue?: string;
  onSubmit: (value: string) => void;
};

export function DecisionBar({
  suggestions = [],
  placeholder,
  disabled,
  initialValue = "",
  onSubmit,
}: Props) {
  const inputId = useId();
  const [value, setValue] = useState(initialValue);
  const [focused, setFocused] = useState(false);
  const reduce = useReducedMotion();

  // Il testo ereditato dalla Landing resta visibile finché la conversazione non lo assorbe.
  useEffect(() => {
    if (initialValue) setValue(initialValue);
  }, [initialValue]);

  useEffect(() => {
    if (disabled) setValue("");
  }, [disabled]);

  const submit = (v: string) => {
    const text = v.trim();
    if (!text || disabled) return;
    setValue("");
    onSubmit(text);
  };

  return (
    <div className="relative">
      <motion.div
        aria-hidden
        animate={{ opacity: focused || (!!initialValue && !disabled) ? 0.3 : 0 }}
        transition={{ duration: 0.9, ease: EASE }}
        className="pointer-events-none absolute inset-x-10 -inset-y-5 rounded-[4rem] bg-primary/12 blur-[60px]"
      />
      <motion.form
        onSubmit={(e) => {
          e.preventDefault();
          submit(value);
        }}
        whileHover={{ scale: reduce ? 1 : 1.004 }}
        transition={{ duration: 0.3, ease: EASE }}
        role="search"
        className={cn(
          "relative flex items-center gap-2 rounded-full border bg-card p-2.5 pl-3 transition-[border-color,box-shadow] duration-700 sm:gap-3 sm:p-3 sm:pl-6",
          "before:pointer-events-none before:absolute before:inset-px before:rounded-full before:bg-gradient-to-b before:from-background/70 before:to-transparent before:opacity-60",
          focused
            ? "border-primary/40 shadow-[var(--shadow-focus),var(--shadow-object)]"
            : "border-border/55 shadow-[var(--shadow-object)] hover:border-border/80",
          disabled && "opacity-60",
        )}
      >
        <button
          type="button"
          aria-label="Parla con DriveWise"
          onClick={() => window.alert("Demo: input vocale non ancora disponibile.")}
          className="relative z-10 grid size-11 shrink-0 place-items-center rounded-full text-muted-foreground transition-colors duration-300 hover:bg-muted hover:text-foreground"
        >
          <Mic className="size-[1.15rem]" />
        </button>
        <label htmlFor={inputId} className="sr-only">
          Raccontami cosa stai cercando
        </label>
        <input
          id={inputId}
          value={value}
          disabled={disabled}
          onChange={(e) => setValue(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={placeholder}
          className="relative z-10 h-14 min-w-0 flex-1 bg-transparent text-[0.98rem] text-foreground outline-none placeholder:text-foreground/45 sm:h-16 sm:text-[1.05rem]"
        />
        <motion.button
          type="button"
          aria-label="Invia risposta"
          onClick={() => submit(value)}
          disabled={disabled}
          whileTap={{ scale: reduce ? 1 : 0.98 }}
          transition={{ duration: 0.3, ease: EASE }}
          className={cn(
            "relative z-10 inline-flex h-14 shrink-0 items-center gap-2 rounded-full bg-primary px-5 text-sm font-medium text-primary-foreground transition-[background-color,box-shadow] duration-300 hover:bg-primary-hover sm:h-16 sm:px-8",
            value.trim() && "shadow-[var(--shadow-lift)]",
          )}
        >
          <span className="hidden sm:inline">Inizia</span>
          <ArrowRight className="size-4" />
        </motion.button>
      </motion.form>

      {suggestions.length > 0 && (
        <div className="mt-6 flex flex-wrap gap-2.5">
          {suggestions.map((s, i) => (
            <motion.button
              key={s}
              type="button"
              onClick={() => submit(s)}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 + i * 0.07, duration: 0.6, ease: EASE }}
              className="rounded-full border border-border/70 bg-card/70 px-4 py-2 text-[0.8125rem] text-muted-foreground backdrop-blur transition-all duration-300 hover:-translate-y-px hover:border-primary/40 hover:text-foreground"
            >
              {s}
            </motion.button>
          ))}
        </div>
      )}
    </div>
  );
}