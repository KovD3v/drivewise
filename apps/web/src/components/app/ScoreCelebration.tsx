import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { motion, useReducedMotion } from "framer-motion";
import { useCountUp } from "@/lib/use-count-up";

type Particle = {
  x: number;
  y: number;
  gravity: number;
  size: number;
  delay: number;
  duration: number;
  color: string;
};

/** Intensità dell'effetto in base al punteggio. */
function intensityFor(score: number) {
  if (score >= 85) return { particles: 38, spread: 175, glow: 1 } as const;
  if (score >= 60) return { particles: 20, spread: 130, glow: 0.55 } as const;
  return { particles: 0, spread: 0, glow: 0 } as const;
}

/** Toni brand + scintille chiare/dorate per contrasto. */
const TONES = [
  "var(--primary)",
  "var(--primary-hover, var(--primary))",
  "var(--accent)",
  "color-mix(in oklab, var(--primary) 45%, var(--foreground))",
  "#F3D9A4",
];

export function ScoreCelebration({
  score,
  duration = 1300,
  className,
  onCelebrate,
}: {
  score: number;
  duration?: number;
  className?: string;
  onCelebrate?: () => void;
}) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  /** Incrementa ad ogni ingresso in viewport: riavvia count-up ed effetto. */
  const [run, setRun] = useState(0);
  const [burst, setBurst] = useState<{ x: number; y: number; run: number } | null>(null);
  const value = useCountUp(visible ? score : 0, reduce ? 0 : duration, !!reduce);
  const intensity = intensityFor(score);
  const onCelebrateRef = useRef(onCelebrate);
  onCelebrateRef.current = onCelebrate;

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry) return;
        if (entry.isIntersecting) {
          setVisible(true);
          setRun((r) => r + 1);
        } else {
          setVisible(false);
          setBurst(null);
        }
      },
      { threshold: 0.35 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  /** Il burst scatta esattamente alla fine del count-up. */
  useEffect(() => {
    if (!visible) return;
    const t = window.setTimeout(
      () => {
        const r = ref.current?.getBoundingClientRect();
        setBurst({ x: r ? r.left + r.width / 2 : 0, y: r ? r.top + r.height / 2 : 0, run });
        onCelebrateRef.current?.();
      },
      reduce ? 0 : duration,
    );
    return () => window.clearTimeout(t);
  }, [visible, run, reduce, duration]);

  const clear = useCallback(() => setBurst(null), []);
  useEffect(() => {
    if (!burst) return;
    const t = window.setTimeout(clear, 1300);
    return () => window.clearTimeout(t);
  }, [burst, clear]);

  const particles = useMemo<Particle[]>(() => {
    const n = intensity.particles;
    return Array.from({ length: n }, (_, i) => {
      const angle = (i / Math.max(n, 1)) * Math.PI * 2 + (i % 3) * 0.12;
      const speed = intensity.spread * (0.5 + ((i * 37) % 100) / 190);
      return {
        x: Math.cos(angle) * speed,
        y: Math.sin(angle) * speed * 0.82,
        gravity: 34 + ((i * 23) % 46),
        size: 3 + ((i * 13) % 3),
        delay: ((i * 17) % 9) / 100,
        duration: 0.62 + ((i * 29) % 30) / 100,
        color: TONES[i % TONES.length]!,
      };
    });
  }, [intensity.particles, intensity.spread]);

  const showFx = !!burst && !reduce && typeof document !== "undefined";

  return (
    <div ref={ref} className="relative flex items-center justify-center">
      {showFx &&
        createPortal(
          <div
            aria-hidden
            className="pointer-events-none fixed z-[80]"
            style={{ left: burst!.x, top: burst!.y }}
          >
            {particles.map((p, i) => (
              <span
                key={`${burst!.run}-${i}`}
                className="dw-fx-fly absolute"
                style={
                  {
                    "--fx-x": `${p.x}px`,
                    "--fx-y": `${p.y}px`,
                    "--fx-dur": `${p.duration}s`,
                    "--fx-delay": `${p.delay}s`,
                  } as React.CSSProperties
                }
              >
                <span
                  className="dw-fx-fall block rounded-full"
                  style={
                    {
                      width: p.size,
                      height: p.size,
                      backgroundColor: p.color,
                      boxShadow: `0 0 10px ${p.color}`,
                      "--fx-g": `${p.gravity}px`,
                      "--fx-dur": `${p.duration}s`,
                      "--fx-delay": `${p.delay}s`,
                    } as React.CSSProperties
                  }
                />
              </span>
            ))}
            {intensity.glow > 0 && (
              <span
                className="dw-fx-shock absolute size-20 rounded-full border border-primary/60"
                style={
                  {
                    marginLeft: "-2.5rem",
                    marginTop: "-2.5rem",
                    "--fx-o": `${0.6 * intensity.glow}`,
                  } as React.CSSProperties
                }
              />
            )}
          </div>,
          document.body,
        )}

      <motion.p
        className={className}
        animate={burst && !reduce ? { scale: [1, 1.08, 0.99, 1] } : { scale: 1 }}
        transition={{ duration: 0.55, times: [0, 0.32, 0.7, 1], ease: [0.34, 1.56, 0.64, 1] }}
      >
        {value}
      </motion.p>
    </div>
  );
}
