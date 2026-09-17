import { useDialogFocus } from "@/hooks/use-dialog-focus";
import { useEffect, useState, type ReactNode } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Loader2, Mail, X } from "lucide-react";
import { signInMock } from "@/lib/mock-account";
import { EASE } from "@/lib/motion";
import { AppleMark, GoogleMark } from "./ProviderIcons";

/**
 * Modale di accesso: compare in dissolvenza sopra il contenuto sfocato,
 * così l'utente vede ancora ciò che sta per salvare.
 */
export function AuthDialog({
  open,
  onClose,
  title = "Accedi per salvare questa analisi",
  subtitle = "Il salvataggio riprende automaticamente subito dopo l'accesso.",
  preview,
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  preview?: ReactNode;
}) {
  const dialogRef = useDialogFocus(open);
  const reduce = useReducedMotion();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [emailMode, setEmailMode] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const enterDemo = () => {
    try { signInMock(); onClose(); }
    catch { setError("Il browser non consente il salvataggio locale."); }
  };
  const social = async (_provider: "google" | "apple") => enterDemo();
  const withEmail = async (_mode: "in" | "up") => enterDemo();

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
          aria-label={title}
        >
          <button
            type="button"
            aria-label="Chiudi"
            onClick={onClose}
            className="absolute inset-0 cursor-default bg-background/70 backdrop-blur-md"
          />
          <motion.div
            initial={reduce ? { opacity: 0 } : { opacity: 0, y: 22, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, y: 12, scale: 0.98 }}
            transition={{ duration: 0.45, ease: EASE }}
            className="relative w-full max-w-[26rem] overflow-hidden rounded-3xl border border-border/70 bg-card/95 p-7 shadow-[var(--shadow-object)] backdrop-blur"
          >
            <button
              type="button"
              onClick={onClose}
              aria-label="Chiudi"
              className="absolute top-4 right-4 grid size-8 place-items-center rounded-full border border-border/70 text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
            >
              <X className="size-4" />
            </button>

            <h2 className="font-heading pr-8 text-[1.2rem] font-extrabold tracking-tight">
              {title}
            </h2>
            <p className="mt-2 text-[0.85rem] text-muted-foreground">{subtitle}</p>
            <p className="mt-2 text-xs text-muted-foreground">Demo locale: accesso simulato, nessun account creato. Non inserire credenziali reali.</p>

            {preview && <div className="mt-5">{preview}</div>}

            <div className="mt-6 space-y-2.5">
              <ProviderButton
                onClick={() => void social("google")}
                busy={busy === "google"}
                icon={<GoogleMark />}
                label="Continua con Google"
              />
              <ProviderButton
                onClick={() => void social("apple")}
                busy={busy === "apple"}
                icon={<AppleMark />}
                label="Continua con Apple"
              />
              {!emailMode && (
                <ProviderButton
                  onClick={() => setEmailMode(true)}
                  busy={false}
                  icon={<Mail className="size-[1.05rem] text-muted-foreground" />}
                  label="Continua con email"
                />
              )}
            </div>

            {emailMode && (
              <div className="mt-4 space-y-2.5">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="La tua email"
                  autoComplete="email"
                  className="h-11 w-full rounded-2xl border border-border/70 bg-background px-4 text-sm outline-none transition-colors focus:border-primary/50"
                />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  autoComplete="current-password"
                  className="h-11 w-full rounded-2xl border border-border/70 bg-background px-4 text-sm outline-none transition-colors focus:border-primary/50"
                />
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={busy === "email" || !email || !password}
                    onClick={() => void withEmail("in")}
                    className="inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-2xl bg-primary text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-hover disabled:opacity-50"
                  >
                    {busy === "email" && <Loader2 className="size-4 animate-spin" />}
                    Accedi
                  </button>
                  <button
                    type="button"
                    disabled={busy === "email" || !email || !password}
                    onClick={() => void withEmail("up")}
                    className="inline-flex h-11 flex-1 items-center justify-center rounded-2xl border border-border/70 text-sm font-medium transition-colors hover:border-primary/40 disabled:opacity-50"
                  >
                    Crea account
                  </button>
                </div>
              </div>
            )}

            {error && <p className="mt-4 text-[0.8rem] text-destructive">{error}</p>}
            {info && <p className="mt-4 text-[0.8rem] text-muted-foreground">{info}</p>}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function ProviderButton({
  onClick,
  busy,
  icon,
  label,
}: {
  onClick: () => void;
  busy: boolean;
  icon: ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      className="inline-flex h-12 w-full items-center justify-center gap-3 rounded-full border border-border/70 bg-background px-5 text-[0.92rem] font-medium transition-all duration-300 hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-[var(--shadow-soft)] disabled:opacity-60"
    >
      {busy ? <Loader2 className="size-4 animate-spin" /> : icon}
      {label}
    </button>
  );
}
