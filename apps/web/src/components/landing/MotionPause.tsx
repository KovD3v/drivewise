import { useState, type ReactNode } from "react";
import { Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Avvolge una vignetta in loop e aggiunge un pulsante "Metti in pausa / Riprendi" (WCAG 2.2.2).
 * In pausa la classe .dw-user-paused ferma tutte le animazioni CSS dentro (regola in styles.css);
 * le vignette con un orologio JavaScript controllano la stessa classe.
 * Con "riduci movimento" le vignette sono già ferme e il pulsante si nasconde.
 */
export function MotionPause({ children, className = "" }: { children: ReactNode; className?: string }) {
  const [paused, setPaused] = useState(false);
  return (
    <div className={`dw-motion relative ${paused ? "dw-user-paused" : ""} ${className}`}>
      {children}
      <Button
        variant="ghost"
        type="button"
        aria-pressed={paused}
        onClick={() => setPaused((p) => !p)}
        className="dw-motion-btn absolute top-full right-1 z-10 mt-2 inline-flex h-8 items-center gap-1.5 rounded-full border border-border/70 bg-card/85 px-3 text-xs font-medium text-muted-foreground backdrop-blur transition-colors hover:text-foreground"
      >
        {paused ? (
          <Play className="size-3.5" aria-hidden strokeWidth={2} />
        ) : (
          <Pause className="size-3.5" aria-hidden strokeWidth={2} />
        )}
        {paused ? "Riprendi" : "Metti in pausa"}
        <span className="sr-only"> l&apos;animazione</span>
      </Button>
    </div>
  );
}