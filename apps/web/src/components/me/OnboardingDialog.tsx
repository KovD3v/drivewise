import { useDialogFocus } from "@/hooks/use-dialog-focus";
import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Link } from "@tanstack/react-router";
import { Loader2, Pencil } from "lucide-react";
import { EASE } from "@/lib/motion";

/**
 * Conferma post-login: nome mostrato + accettazione di termini e privacy.
 * Appare una sola volta per utente (finché privacy_consent_at è vuoto).
 */
export function OnboardingDialog({
  open,
  initialName,
  onConfirm,
}: {
  open: boolean;
  initialName: string;
  onConfirm: (displayName: string) => Promise<void>;
}) {
  const dialogRef = useDialogFocus(open);
  const reduce = useReducedMotion();
  const [name, setName] = useState(initialName);
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = accepted && name.trim().length > 1 && !busy;

  const submit = async () => {
    if (!canSubmit) return;
    setBusy(true);
    setError(null);
    try {
      await onConfirm(name.trim());
    } catch {
      setError("Non siamo riusciti a salvare. Riprova.");
    }
    setBusy(false);
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[70] grid place-items-center px-5"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.35, ease: EASE }}
          ref={dialogRef}
          role="dialog"
          aria-modal="true"
          aria-label="Completa il tuo profilo"
        >
          <div aria-hidden className="absolute inset-0 bg-background/70 backdrop-blur-md" />
          <motion.div
            initial={reduce ? { opacity: 0 } : { opacity: 0, y: 22, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, y: 12, scale: 0.98 }}
            transition={{ duration: 0.45, ease: EASE }}
            className="relative w-full max-w-[26rem] overflow-hidden rounded-3xl border border-border/70 bg-card/95 p-7 shadow-[var(--shadow-object)] backdrop-blur"
          >
            <h2 className="font-heading text-[1.2rem] font-extrabold tracking-tight">
              Benvenuto in My DriveWise
            </h2>
            <p className="mt-2 text-[0.85rem] text-muted-foreground">
              Ancora un passaggio e la tua area personale è pronta.
            </p>

            <label
              htmlFor="dw-display-name"
              className="mt-6 block text-[0.72rem] tracking-[0.14em] text-muted-foreground uppercase"
            >
              Come vuoi essere chiamato
            </label>
            <div className="relative mt-2">
              <input
                id="dw-display-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Come vuoi essere chiamato?"
                autoComplete="name"
                className="h-11 w-full rounded-2xl border border-border/70 bg-background px-4 pr-10 text-sm outline-none transition-colors focus:border-primary/50"
              />
              <Pencil
                aria-hidden
                className="pointer-events-none absolute top-1/2 right-3.5 size-4 -translate-y-1/2 text-muted-foreground"
              />
            </div>

            <label className="mt-5 flex cursor-pointer items-start gap-3 text-[0.85rem] leading-relaxed">
              <input
                type="checkbox"
                checked={accepted}
                onChange={(e) => setAccepted(e.target.checked)}
                className="mt-0.5 size-4 shrink-0 accent-[var(--color-primary)]"
              />
              <span className="text-muted-foreground">
                Ho letto e accetto i{" "}
                <Link to="/terms" className="text-primary underline underline-offset-2">
                  Termini di servizio
                </Link>{" "}
                e l&apos;
                <Link to="/privacy" className="text-primary underline underline-offset-2">
                  Informativa sulla privacy
                </Link>
                .
              </span>
            </label>

            <button
              type="button"
              disabled={!canSubmit}
              onClick={() => void submit()}
              className="mt-6 inline-flex h-12 w-full items-center justify-center gap-2 rounded-full bg-primary text-[0.95rem] font-medium text-primary-foreground transition-colors hover:bg-primary-hover disabled:opacity-50"
            >
              {busy && <Loader2 className="size-4 animate-spin" />}
              Continua
            </button>

            {error && <p className="mt-4 text-[0.8rem] text-destructive">{error}</p>}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
