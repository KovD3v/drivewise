import { useEffect, type RefObject } from "react";

/**
 * Scrive su `el.style` la variabile CSS `--sp` (0 → 1) in base a quanto l'elemento è entrato nello schermo.
 * - `start`: frazione dell'altezza della finestra in cui inizia (1 = bordo inferiore).
 * - `end`:   frazione in cui arriva a 1 (es. 0.45 = quando il bordo superiore è al 45% dello schermo).
 * Un solo listener passivo, aggiornato con requestAnimationFrame. Con "riduci movimento" resta a 1.
 */
export function useScrollProgress(ref: RefObject<HTMLElement | null>, start = 1, end = 0.45) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    let raf = 0;
    const update = () => {
      raf = 0;
      if (reduce.matches) {
        el.style.setProperty("--sp", "1");
        return;
      }
      const vh = window.innerHeight;
      const top = el.getBoundingClientRect().top;
      const p = (vh * start - top) / (vh * (start - end));
      el.style.setProperty("--sp", Math.min(1, Math.max(0, p)).toFixed(4));
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    reduce.addEventListener("change", update);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      reduce.removeEventListener("change", update);
    };
  }, [ref, start, end]);
}
