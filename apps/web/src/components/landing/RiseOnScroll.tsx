import { useRef, type ReactNode } from "react";
import { useScrollProgress } from "./useScrollProgress";

/**
 * Ingresso "a finestra di prodotto" legato allo scroll (stile sezione Platform di Keyvo):
 * la vignetta entra più piccola e spostata in alto, così passa sopra al titolo, poi mentre
 * scorri si allarga oltre la colonna del testo e scivola al suo posto.
 * - Si misura il contenitore esterno (fermo) e si trasforma solo quello interno: niente
 *   effetto a catena tra misura e trasformazione.
 * - Torna indietro se risali. Con "riduci movimento" resta nella posizione finale.
 */
export function RiseOnScroll({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useScrollProgress(ref, 1.1, 0.3);
  return (
    <div ref={ref} className={`dw-rise ${className}`}>
      <style>{CSS}</style>
      <div className="dw-rise-in">{children}</div>
    </div>
  );
}

const CSS = `
.dw-rise{ --lift:clamp(48px, 10vw, 150px); --s0:.8;
  position:relative; z-index:2; width:min(1320px, calc(100vw - 32px)); margin-left:calc(50% - min(660px, 50vw - 16px)); }
.dw-rise-in{ --e:calc(1 - (1 - var(--sp, 1)) * (1 - var(--sp, 1)));
  transform:translateY(calc((1 - var(--sp, 1)) * var(--lift) * -1)) scale(calc(var(--s0) + (1 - var(--s0)) * var(--e)));
  transform-origin:50% 0; will-change:transform; }
@media (max-width: 640px){ .dw-rise{ --lift:32px; --s0:.94; } }
@media (prefers-reduced-motion: reduce){ .dw-rise-in{ transform:none; } }
`;
