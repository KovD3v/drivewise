import { useRef, type ReactNode } from "react";
import { useScrollProgress } from "./useScrollProgress";

/**
 * Effetto "Keyvo": entrando nello schermo il contenuto passa dal 92% al 100%,
 * sale di qualche decina di pixel e passa da semi-trasparente a pieno. Legato allo scroll (torna indietro se risali).
 * Avvolge le vignette 16:9 della home. Non cambia la larghezza del layout (usa solo transform).
 */
export function ScaleOnScroll({
  children,
  className = "",
  start = 1,
  end = 0.4,
}: {
  children: ReactNode;
  className?: string;
  /** per una vignetta già visibile al caricamento (hero) usa start≈1.6, così parte già a 100% */
  start?: number;
  end?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useScrollProgress(ref, start, end);
  return (
    <div
      ref={ref}
      className={className}
      style={{
        // --sp: 0 → 1 (vedi useScrollProgress); easing "out" applicato in CSS
        transform:
          "translateY(calc((1 - var(--sp, 1)) * 56px)) scale(calc(0.92 + 0.08 * (1 - (1 - var(--sp, 1)) * (1 - var(--sp, 1)))))",
        transformOrigin: "50% 0%",
        opacity: "calc(0.55 + 0.45 * var(--sp, 1))",
        willChange: "transform",
      }}
    >
      {children}
    </div>
  );
}
