import { useScrollReveal } from "@/hooks/use-scroll-reveal";
import { wordRevealDelay } from "@/lib/reveal-policy";
import { Fragment, useEffect, useRef, type ReactNode, type PointerEvent } from "react";

/**
 * Effetti di rifinitura della home (stile pastello DriveWise).
 * - <SectionAurora />  macchie pastello sfocate in lento movimento, da mettere come primo figlio di una <section className="relative isolate …">.
 * - <TiltCard>         card che si inclina appena verso il mouse con un alone di luce (solo dispositivi con mouse).
 * - <RevealText />     titolo che entra parola per parola la prima volta che è visibile.
 * Le classi globali (.dw-band, .btn-shine) e i keyframes sono in effects.css.
 * Tutto si disattiva con prefers-reduced-motion.
 */

/* ---------------- 4 · aurora ---------------- */
export function SectionAurora({ variant = "mint" }: { variant?: "mint" | "lavender" | "peach" }) {
  return (
    <div className={`dw-aurora dw-aurora-${variant}`} aria-hidden>
      <span />
      <span />
      <span />
    </div>
  );
}

/* ---------------- 5 · card vive ---------------- */
export function TiltCard({ children, className = "", max = 5 }: { children: ReactNode; className?: string; max?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const enabled = useRef(false);

  useEffect(() => {
    const mq = window.matchMedia("(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)");
    const apply = () => (enabled.current = mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  const move = (e: PointerEvent<HTMLDivElement>) => {
    const el = ref.current;
    if (!el || !enabled.current) return;
    const r = el.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width; // 0 → 1
    const y = (e.clientY - r.top) / r.height;
    el.style.setProperty("--rx", `${((0.5 - y) * max).toFixed(2)}deg`);
    el.style.setProperty("--ry", `${((x - 0.5) * max).toFixed(2)}deg`);
    el.style.setProperty("--mx", `${(x * 100).toFixed(1)}%`);
    el.style.setProperty("--my", `${(y * 100).toFixed(1)}%`);
    el.dataset["hover"] = "1";
  };
  const leave = () => {
    const el = ref.current;
    if (!el) return;
    el.style.setProperty("--rx", "0deg");
    el.style.setProperty("--ry", "0deg");
    delete el.dataset["hover"];
  };

  return (
    <div ref={ref} className={`dw-tilt ${className}`} onPointerMove={move} onPointerLeave={leave}>
      {children}
      <span className="dw-tilt-glow" aria-hidden />
    </div>
  );
}

/* ---------------- 6 · titoli rivelati ---------------- */
export function RevealText({ text, className = "" }: { text: string; className?: string }) {
  const { ref } = useScrollReveal<HTMLSpanElement>();

  const words = text.split(" ");
  return (
    <span ref={ref} className={`dw-reveal ${className}`}>
      <span className="sr-only">{text}</span>
      {words.map((w, i) => (
        <Fragment key={i}>
          <span className="dw-reveal-w" aria-hidden>
            <span style={{ transitionDelay: `${wordRevealDelay(i, words.length)}ms` }}>{w}</span>
          </span>
          {i < words.length - 1 ? " " : null}
        </Fragment>
      ))}
    </span>
  );
}
