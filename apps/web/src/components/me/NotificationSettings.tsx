import { useState } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/** Impostazioni account → Notifiche: unico interruttore, salvataggio immediato. */
export function NotificationSettings({
  optIn,
  onChange,
}: {
  optIn: boolean;
  onChange: (next: boolean) => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = async () => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await onChange(!optIn);
    } catch {
      setError("Non siamo riusciti a salvare la preferenza. Riprova.");
    }
    setBusy(false);
  };

  return (
    <section className="mt-20">
      <h2 className="font-heading text-2xl font-extrabold tracking-tight">Notifiche</h2>
      <div className="mt-6 flex items-start justify-between gap-6 rounded-2xl border border-border/70 bg-card/70 px-5 py-5 backdrop-blur">
        <div className="min-w-0">
          <p id="dw-marketing-label" className="font-medium">
            Aggiornamenti su nuove funzionalità DriveWise
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Ti scriviamo solo quando rilasciamo qualcosa di nuovo che potrebbe interessarti. Puoi
            disattivare in ogni momento.
          </p>
          {error && <p className="mt-2 text-[0.8rem] text-destructive">{error}</p>}
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={optIn}
          aria-labelledby="dw-marketing-label"
          disabled={busy}
          onClick={() => void toggle()}
          className={cn(
            "relative mt-1 grid h-7 w-12 shrink-0 place-items-center rounded-full border transition-colors",
            optIn ? "border-primary/40 bg-primary" : "border-border/70 bg-background",
            busy && "opacity-60",
          )}
        >
          <span
            className={cn(
              "absolute top-1/2 size-5 -translate-y-1/2 rounded-full bg-card shadow-[var(--shadow-soft)] transition-all duration-300",
              optIn ? "left-[1.6rem]" : "left-[0.15rem]",
            )}
          />
          {busy && <Loader2 className="absolute size-3.5 animate-spin text-muted-foreground" />}
        </button>
      </div>
    </section>
  );
}
