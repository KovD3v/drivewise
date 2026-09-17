import { useMemo, useState, type FormEvent } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Check, Send } from "lucide-react";
import { z } from "zod";
import { cn } from "@/lib/utils";
import { ctaVariants } from "@/components/landing/CtaButton";

const REASONS = [
  "Domanda generale",
  "Partnership",
  "Stampa",
  "Privacy e dati",
  "Segnalazione di un problema",
] as const;

const schema = z.object({
  reason: z.string().min(1),
  name: z.string().trim().min(2, "Inserisci il tuo nome").max(100, "Massimo 100 caratteri"),
  email: z.string().trim().email("Inserisci un'email valida").max(255),
  message: z
    .string()
    .trim()
    .min(10, "Scrivi almeno 10 caratteri")
    .max(1000, "Massimo 1000 caratteri"),
});

const field =
  "w-full rounded-2xl border border-border bg-background px-4 py-3 text-[0.95rem] text-foreground placeholder:text-muted-foreground transition-all duration-300 focus:border-primary/50 focus:shadow-[var(--shadow-focus)] focus:outline-none";

export function ContactForm({ email }: { email: string }) {
  const reduce = useReducedMotion();
  const [reason, setReason] = useState<string>(REASONS[0]);
  const [values, setValues] = useState({ name: "", email: "", message: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [sent, setSent] = useState(false);

  const particles = useMemo(
    () =>
      Array.from({ length: 14 }, (_, i) => ({
        id: i,
        angle: (i / 14) * Math.PI * 2,
        delay: i * 0.03,
      })),
    [],
  );

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const parsed = schema.safeParse({ reason, ...values });
    if (!parsed.success) {
      const next: Record<string, string> = {};
      for (const issue of parsed.error.issues) next[String(issue.path[0])] = issue.message;
      setErrors(next);
      return;
    }
    setErrors({});
    setSent(true);
  }

  return (
    <div className="relative overflow-hidden rounded-3xl border border-border/70 bg-card p-7 shadow-[var(--shadow-soft)] sm:p-9">
      <AnimatePresence mode="wait">
        {sent ? (
          <motion.div
            key="ok"
            initial={reduce ? { opacity: 1 } : { opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: reduce ? 0 : 0.5, ease: [0.22, 1, 0.36, 1] }}
            className="flex min-h-[22rem] flex-col items-center justify-center text-center"
          >
            <div className="relative grid size-24 place-items-center">
              {!reduce && (
                <motion.span
                  aria-hidden
                  className="absolute inset-0 rounded-full border border-primary/40"
                  initial={{ scale: 0.6, opacity: 0.8 }}
                  animate={{ scale: 1.6, opacity: 0 }}
                  transition={{ duration: 1.6, repeat: Infinity, ease: "easeOut" }}
                />
              )}
              {!reduce &&
                particles.map((p) => (
                  <motion.span
                    key={p.id}
                    aria-hidden
                    className="absolute size-1 rounded-full bg-primary"
                    initial={{ x: 0, y: 0, opacity: 0 }}
                    animate={{
                      x: Math.cos(p.angle) * 62,
                      y: Math.sin(p.angle) * 62,
                      opacity: [0, 1, 0],
                    }}
                    transition={{ duration: 1.4, delay: p.delay, repeat: Infinity, ease: "easeOut" }}
                  />
                ))}
              <motion.span
                className="grid size-14 place-items-center rounded-full bg-primary text-primary-foreground"
                initial={reduce ? { scale: 1 } : { scale: 0.5 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 260, damping: 16 }}
              >
                <Check className="size-7" strokeWidth={2.6} aria-hidden />
              </motion.span>
            </div>
            <h3 className="font-heading mt-7 text-[1.375rem] font-bold tracking-[-0.02em]">
              Invio simulato.
            </h3>
            <p className="mt-3 max-w-sm text-[0.95rem] leading-relaxed text-muted-foreground">
              Demo: il messaggio non è stato inviato.
            </p>
            <button
              type="button"
              onClick={() => {
                setSent(false);
                setValues({ name: "", email: "", message: "" });
              }}
              className={cn(ctaVariants({ variant: "ghost", size: "sm" }), "mt-7")}
            >
              Scrivi un altro messaggio
            </button>
          </motion.div>
        ) : (
          <motion.form
            key="form"
            onSubmit={handleSubmit}
            noValidate
            initial={reduce ? { opacity: 1 } : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="space-y-7"
          >
            <p className="text-xs text-muted-foreground">Modulo demo: nessun messaggio verrà inviato.</p>
            <fieldset>
              <legend className="text-[0.6875rem] font-semibold tracking-[0.18em] text-muted-foreground uppercase">
                Motivo del contatto
              </legend>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {REASONS.map((r) => (
                  <button
                    key={r}
                    type="button"
                    aria-pressed={reason === r}
                    onClick={() => setReason(r)}
                    className={cn(
                      "rounded-full border px-4 py-2 text-[0.8125rem] transition-all duration-300 motion-safe:hover:scale-[1.03]",
                      reason === r
                        ? "border-primary bg-primary text-primary-foreground shadow-[var(--shadow-soft)]"
                        : "border-border bg-background text-muted-foreground hover:border-foreground/25 hover:text-foreground",
                    )}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </fieldset>

            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label htmlFor="contact-name" className="text-[0.8125rem] font-medium">
                  Nome
                </label>
                <input
                  id="contact-name"
                  className={cn(field, "mt-2")}
                  placeholder="Il tuo nome"
                  maxLength={100}
                  value={values.name}
                  onChange={(e) => setValues((v) => ({ ...v, name: e.target.value }))}
                />
                {errors['name'] && <p className="mt-2 text-[0.75rem] text-destructive">{errors['name']}</p>}
              </div>
              <div>
                <label htmlFor="contact-email" className="text-[0.8125rem] font-medium">
                  Email
                </label>
                <input
                  id="contact-email"
                  type="email"
                  className={cn(field, "mt-2")}
                  placeholder="nome@esempio.it"
                  maxLength={255}
                  value={values.email}
                  onChange={(e) => setValues((v) => ({ ...v, email: e.target.value }))}
                />
                {errors['email'] && (
                  <p className="mt-2 text-[0.75rem] text-destructive">{errors['email']}</p>
                )}
              </div>
            </div>

            <div>
              <label htmlFor="contact-message" className="text-[0.8125rem] font-medium">
                Messaggio
              </label>
              <textarea
                id="contact-message"
                rows={6}
                maxLength={1000}
                className={cn(field, "mt-2 resize-none")}
                placeholder="Raccontaci come possiamo aiutarti."
                value={values.message}
                onChange={(e) => setValues((v) => ({ ...v, message: e.target.value }))}
              />
              <div className="mt-2 flex items-center justify-between gap-3">
                <p className="text-[0.75rem] text-destructive">{errors['message'] ?? ""}</p>
                <p className="shrink-0 text-[0.75rem] text-muted-foreground">
                  {values.message.length}/1000
                </p>
              </div>
            </div>

            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <button type="submit" className={cn(ctaVariants({ variant: "primary", size: "md" }))}>
                Invia messaggio
                <Send className="size-4" aria-hidden />
              </button>
              <p className="text-[0.8125rem] text-muted-foreground">
                Preferisci scriverci via email?{" "}
                <a
                  className="text-foreground underline underline-offset-4"
                  href={`mailto:${email}`}
                >
                  {email}
                </a>
              </p>
            </div>
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  );
}
