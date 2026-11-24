import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { EASE } from "@/lib/motion";
import { cn } from "@/lib/utils";

type SectionMark = { top: number; label: string; ratio: number };

/**
 * Wayfinding di lettura condiviso da tutto il portale:
 * 1. binario verticale con progresso e punti per ogni sezione (desktop);
 * 2. "sliver" in fondo alla viewport che lascia intravedere il contenuto successivo;
 * 3. indicatore discreto che compare solo dopo un paio di secondi di inattività.
 *
 * Tutti gli agganci sono basati sul montaggio reale del componente e su
 * misurazioni del DOM: funzionano sia in hard load sia in navigazione SPA.
 */
export function ScrollWayfinding() {
  const reduce = useReducedMotion();
  const [marks, setMarks] = useState<SectionMark[]>([]);
  const [progress, setProgress] = useState(0);
  const [atEnd, setAtEnd] = useState(false);
  const [idle, setIdle] = useState(false);
  const idleTimer = useRef<number | null>(null);

  const measure = useCallback(() => {
    const nodes = Array.from(document.querySelectorAll<HTMLElement>("main section"));
    const docHeight = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    const next = nodes
      .filter((n) => n.offsetHeight > 120)
      .map((n) => {
        const top = n.getBoundingClientRect().top + window.scrollY;
        const heading = n.querySelector("h1, h2");
        return {
          top,
          label: heading?.textContent?.trim().slice(0, 42) ?? "Sezione",
          ratio: Math.min(1, Math.max(0, top / docHeight)),
        };
      });
    setMarks(next);
  }, []);

  useEffect(() => {
    measure();
    const ro = new ResizeObserver(() => measure());
    ro.observe(document.body);
    return () => ro.disconnect();
  }, [measure]);

  useEffect(() => {
    const armIdle = () => {
      if (idleTimer.current) window.clearTimeout(idleTimer.current);
      idleTimer.current = window.setTimeout(() => setIdle(true), 2200);
    };

    const onScroll = () => {
      const docHeight = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      const y = window.scrollY;
      setProgress(Math.min(1, Math.max(0, y / docHeight)));
      setAtEnd(docHeight - y < 120);
      setIdle(false);
      armIdle();
    };

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (idleTimer.current) window.clearTimeout(idleTimer.current);
    };
  }, []);

  const activeIndex = useMemo(() => {
    let idx = 0;
    marks.forEach((m, i) => {
      if (m.ratio <= progress + 0.001) idx = i;
    });
    return idx;
  }, [marks, progress]);

  const jump = (top: number) => {
    window.scrollTo({ top: Math.max(0, top - 88), behavior: reduce ? "auto" : "smooth" });
  };

  return (
    <>
      {/* 1 — binario di lettura */}
      {marks.length > 1 && (
        <div className="pointer-events-none fixed top-1/2 right-5 z-40 hidden -translate-y-1/2 lg:block">
          <div className="pointer-events-auto relative flex h-[42vh] w-6 justify-center">
            <span className="absolute inset-y-0 w-px bg-border" aria-hidden />
            <motion.span
              aria-hidden
              className="absolute inset-y-0 w-px origin-top bg-primary"
              style={{ scaleY: progress }}
              transition={{ duration: 0 }}
            />
            {marks.map((m, i) => (
              <button
                key={`${m.label}-${i}`}
                type="button"
                onClick={() => jump(m.top)}
                title={m.label}
                aria-label={`Vai a ${m.label}`}
                className="absolute -translate-y-1/2 p-1.5"
                style={{ top: `${m.ratio * 100}%` }}
              >
                <span
                  className={cn(
                    "block rounded-full transition-all duration-300",
                    i === activeIndex
                      ? "size-2 bg-primary shadow-[0_0_0_4px_color-mix(in_oklab,var(--color-primary)_16%,transparent)]"
                      : "size-1.5 bg-border hover:bg-foreground/40",
                  )}
                />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 2 — sliver: accenno del contenuto che continua */}
      <div
        aria-hidden
        className={cn(
          "pointer-events-none fixed inset-x-0 bottom-0 z-30 h-16 bg-gradient-to-t from-foreground/[0.07] to-transparent transition-opacity duration-500",
          atEnd ? "opacity-0" : "opacity-100",
        )}
      />

      {/* 3 — promemoria discreto dopo qualche secondo di inattività */}
      <AnimatePresence>
        {idle && !atEnd && (
          <motion.div
            aria-hidden
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.4, ease: EASE }}
            className="pointer-events-none fixed inset-x-0 bottom-7 z-40 flex justify-center"
          >
            <span className="dw-pulse-soft grid size-8 place-items-center rounded-full border border-border/70 bg-card/85 text-muted-foreground backdrop-blur-sm">
              <ChevronDown className="size-4" />
            </span>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
