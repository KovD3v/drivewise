import { useState } from "react";
import { motion } from "framer-motion";
import { EASE } from "@/lib/motion";

const fields = [
  { id: "length", label: "Lunghezza", unit: "cm" },
  { id: "width", label: "Larghezza", unit: "cm" },
  { id: "height", label: "Altezza", unit: "cm" },
  { id: "doorWidth", label: "Larghezza ingresso", unit: "cm" },
  { id: "doorHeight", label: "Altezza ingresso", unit: "cm" },
] as const;

export type GarageValues = Record<(typeof fields)[number]["id"], string>;

export function GarageDimensions({ onConfirm }: { onConfirm: (values: GarageValues) => void }) {
  const [values, setValues] = useState<GarageValues>({
    length: "",
    width: "",
    height: "",
    doorWidth: "",
    doorHeight: "",
  });

  return (
    <motion.form
      initial={{ opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.6, ease: EASE }}
      onSubmit={(e) => {
        e.preventDefault();
        onConfirm(values);
      }}
      className="rounded-3xl border border-border/70 bg-card p-5 shadow-[var(--shadow-object)] sm:p-6"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        {fields.map((f, i) => (
          <motion.div
            key={f.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.08 * i, ease: EASE }}
          >
            <label
              htmlFor={`garage-${f.id}`}
              className="block text-[0.7rem] tracking-[0.12em] text-muted-foreground uppercase"
            >
              {f.label}
            </label>
            <div className="mt-1.5 flex items-center gap-2 rounded-xl border border-border/70 bg-background px-3.5 transition-colors duration-300 focus-within:border-primary/45">
              <input
                id={`garage-${f.id}`}
                inputMode="numeric"
                value={values[f.id]}
                onChange={(e) => setValues((v) => ({ ...v, [f.id]: e.target.value }))}
                className="h-11 w-full bg-transparent text-[0.95rem] outline-none placeholder:text-foreground/35"
                placeholder="0"
              />
              <span className="text-[0.75rem] text-muted-foreground">{f.unit}</span>
            </div>
          </motion.div>
        ))}
      </div>
      <p className="mt-4 text-[0.8125rem] leading-relaxed text-muted-foreground">
        Queste informazioni ci permettono di verificare se il veicolo è realmente compatibile con il
        tuo spazio.
      </p>
      <button
        type="submit"
        className="mt-5 inline-flex h-11 items-center rounded-full bg-primary px-6 text-sm font-medium text-primary-foreground transition-all duration-300 hover:bg-primary-hover hover:shadow-[var(--shadow-lift)]"
      >
        Conferma misure
      </button>
    </motion.form>
  );
}