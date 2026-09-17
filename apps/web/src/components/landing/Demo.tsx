import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Check } from "lucide-react";
import { Section, Eyebrow } from "./Section";
import { RevealGroup, RevealItem } from "./Reveal";
import { DecisionReport } from "./DecisionReport";
import { AnalysisDots } from "./DecisionBar";
import { EASE } from "@/lib/motion";

type Turn = { from: "user" | "ai"; text: string };

const turns: Turn[] = [
  { from: "user", text: "Cerco un SUV per una famiglia di quattro persone." },
  { from: "ai", text: "Perfetto. Qual è il tuo budget?" },
  { from: "user", text: "35.000 €" },
  { from: "ai", text: "Per te conta di più comfort, affidabilità o contenimento dei costi?" },
  { from: "user", text: "Affidabilità e costi." },
];

const analysis = [
  "Analizzo il tuo utilizzo…",
  "Confronto i costi…",
  "Verifico l'affidabilità…",
  "Valuto sicurezza e manutenzione…",
  "Confronto le alternative…",
  "Calcolo il Decision Score…",
];

export function Demo() {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const [started, setStarted] = useState(false);
  const [step, setStep] = useState(0);
  const [typing, setTyping] = useState(false);
  const [phase, setPhase] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setStarted(true);
          io.disconnect();
        }
      },
      // Il blocco è più alto del viewport: soglia bassa, così parte sempre.
      { threshold: 0, rootMargin: "-15% 0px -15% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    if (!started) return;
    if (reduce) {
      setStep(turns.length);
      setPhase(analysis.length);
      setDone(true);
      return;
    }
    const timers: number[] = [];
    let t = 450;
    turns.forEach((turn, i) => {
      if (turn.from === "ai") {
        const at = t;
        timers.push(window.setTimeout(() => setTyping(true), at));
        // Longer "thinking" for longer answers — feels like a real recording.
        t += 480 + Math.min(turn.text.length * 11, 760);
      } else {
        t += Math.min(turn.text.length * 8, 480);
      }
      const show = t;
      timers.push(
        window.setTimeout(() => {
          setTyping(false);
          setStep(i + 1);
        }, show),
      );
      t += turn.from === "ai" ? 760 : 520;
    });
    const base = t + 340;
    const stepMs = 420;
    analysis.forEach((_, i) => {
      timers.push(window.setTimeout(() => setPhase(i + 1), base + i * stepMs));
    });
    timers.push(window.setTimeout(() => setDone(true), base + analysis.length * stepMs + 340));
    return () => timers.forEach(clearTimeout);
  }, [started, reduce]);

  return (
    <Section id="demo" className="pb-16 md:pb-20 lg:pb-24">
      <RevealGroup>
        <RevealItem>
          <Eyebrow>Esempio</Eyebrow>
        </RevealItem>
        <RevealItem>
          <h2 className="mt-7 max-w-2xl text-4xl leading-[1.08] font-bold sm:text-5xl">
            Una conversazione che finisce con una decisione.
          </h2>
        </RevealItem>
        <RevealItem>
          <p className="mt-6 max-w-xl text-[1.0625rem] leading-relaxed text-muted-foreground">
            Poche domande mirate, poi una risposta che puoi difendere.
          </p>
        </RevealItem>
      </RevealGroup>

      <div ref={ref} className="mt-16 grid gap-10 lg:grid-cols-2 lg:items-start">
        <div className="space-y-4">
          {turns.slice(0, step).map((t) => (
            <motion.div
              key={t.text}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: EASE }}
              className={t.from === "user" ? "flex justify-end" : "flex justify-start"}
            >
              <p
                className={
                  t.from === "user"
                    ? "max-w-md rounded-[1.5rem] rounded-br-lg bg-foreground px-6 py-4 text-[0.95rem] leading-relaxed text-background"
                    : "max-w-md rounded-[1.5rem] rounded-bl-lg border border-border bg-card px-6 py-4 text-[0.95rem] leading-relaxed"
                }
              >
                {t.text}
              </p>
            </motion.div>
          ))}

          <AnimatePresence>
            {typing && (
              <motion.div
                key="typing"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.3, ease: EASE }}
                className="flex justify-start"
              >
                <span className="rounded-[1.5rem] rounded-bl-lg border border-border bg-card px-6 py-5">
                  <AnalysisDots />
                </span>
              </motion.div>
            )}
          </AnimatePresence>

          {phase > 0 && (
            <div className="rounded-[1.5rem] border border-border bg-card px-6 py-5">
              <ul className="space-y-2.5">
                {analysis.slice(0, phase).map((a, i) => {
                  const complete = i < phase - 1 || done;
                  return (
                    <motion.li
                      key={a}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.35, ease: EASE }}
                      className="flex items-center gap-3 text-[0.9375rem] text-muted-foreground"
                    >
                      <span className="grid size-5 shrink-0 place-items-center">
                        {complete ? (
                          <motion.span
                            initial={{ scale: 0.5, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            transition={{ duration: 0.3, ease: EASE }}
                            className="grid size-5 place-items-center rounded-full bg-primary/15"
                          >
                            <Check className="size-3 text-foreground" />
                          </motion.span>
                        ) : (
                          <motion.span
                            animate={{ opacity: [0.3, 1, 0.3] }}
                            transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
                            className="size-1.5 rounded-full bg-primary"
                          />
                        )}
                      </span>
                      <span className={complete ? "text-muted-foreground" : "text-foreground"}>
                        {a}
                      </span>
                    </motion.li>
                  );
                })}
              </ul>
            </div>
          )}

          {done && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <span className="rounded-[1.5rem] rounded-bl-lg border border-primary/40 bg-card px-6 py-4 text-[0.95rem] font-medium">
                Ecco la tua decisione.
              </span>
            </motion.p>
          )}

          <p className="sr-only" aria-live="polite">
            {done ? "Decision Report pronto" : ""}
          </p>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.98 }}
          animate={done ? { opacity: 1, y: 0, scale: 1 } : { opacity: 0, y: 20, scale: 0.98 }}
          transition={{ duration: 0.75, ease: EASE }}
        >
          <DecisionReport active={done} />
        </motion.div>
      </div>
    </Section>
  );
}