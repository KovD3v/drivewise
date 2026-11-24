import { useScrollReveal } from "@/hooks/use-scroll-reveal";
import { CHAT_MESSAGE_INTERVAL_MS } from "@/lib/reveal-policy";
import { TiltCard, RevealText } from "./DesignEffects";
import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Check } from "lucide-react";
import { Section, Eyebrow } from "./Section";
import { RevealGroup, RevealItem } from "./Reveal";
import { DecisionReport } from "./DecisionReport";
import { EASE } from "@/lib/motion";
import { homeExample } from "@/lib/home-example";

type Turn = { from: "user" | "ai"; text: string };

const turns: Turn[] = [
  { from: "user", text: "Cerco un'auto per una famiglia di quattro persone. Viviamo in città e il box è di 4,8 m." },
  { from: "ai", text: "Perfetto. Qual è il tuo budget?" },
  { from: "user", text: `${homeExample.budget.toLocaleString("it-IT")} €` },
  { from: "ai", text: "Per te conta di più comfort, affidabilità o contenimento dei costi?" },
  { from: "user", text: "Affidabilità e costi." },
];

const steps = [
  { title: "Raccontaci cosa ti serve", body: "Bastano poche frasi, nel tuo linguaggio." },
  { title: "DriveWise analizza", body: "Costi reali, affidabilità, uso quotidiano." },
  { title: "Ricevi una decisione motivata", body: "Con punteggio, alternative e compromessi." },
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
  const { ref, revealed: started, immediate } = useScrollReveal<HTMLDivElement>();
  const reduce = useReducedMotion();
  // SSR/no-JS render the complete story; JS progressively refines ordinary arrivals.
  const [step, setStep] = useState(1);
  const [phase, setPhase] = useState(0);
  const [done, setDone] = useState(false);
  const showAll = !started || immediate || reduce;
  const visibleStep = showAll ? turns.length : step;
  const visiblePhase = showAll ? analysis.length : phase;
  const completeStory = Boolean(showAll || done);

  useEffect(() => {
    if (!started) return;
    if (reduce || immediate) {
      setStep(turns.length);
      setPhase(analysis.length);
      setDone(true);
      return;
    }
    setStep(1);
    setPhase(0);
    setDone(false);
    const timers: number[] = [];
    turns.slice(1).forEach((_, i) => {
      timers.push(window.setTimeout(() => setStep(i + 2), (i + 1) * CHAT_MESSAGE_INTERVAL_MS));
    });
    const base = (turns.length - 1) * CHAT_MESSAGE_INTERVAL_MS;
    analysis.forEach((_, i) => {
      timers.push(window.setTimeout(() => setPhase(i + 1), base + (i + 1) * 200));
    });
    timers.push(window.setTimeout(() => setDone(true), base + analysis.length * 200));
    return () => timers.forEach(clearTimeout);
  }, [started, reduce, immediate]);

  return (
    <Section id="come-funziona" className="dw-band scroll-mt-24 pb-4 md:pb-6 lg:pb-8">
      <span id="demo" className="block -translate-y-24" aria-hidden />
      <RevealGroup>
        <RevealItem>
          <Eyebrow>Esempio</Eyebrow>
        </RevealItem>
        <RevealItem>
          <h2 className="mt-7 max-w-2xl text-4xl leading-[1.08] font-bold sm:text-5xl">
            <RevealText text="Una conversazione che finisce con una decisione." />
          </h2>
        </RevealItem>
        <RevealItem>
          <p className="mt-6 max-w-xl text-[1.0625rem] leading-relaxed text-muted-foreground">
            Poche domande mirate, poi una risposta che puoi difendere.
          </p>
        </RevealItem>
      </RevealGroup>

      <ol className="mt-12 grid gap-6 md:grid-cols-3">
        {steps.map((s, i) => (
          <li key={s.title} className="rounded-[1.5rem] border border-border/70 bg-card p-6">
            <span className="font-heading text-sm font-bold text-brand-ink">0{i + 1}</span>
            <h3 className="mt-2 text-lg font-bold">{s.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{s.body}</p>
          </li>
        ))}
      </ol>

      <div ref={ref} className="dw-scroll-reveal mt-16 grid gap-10 lg:grid-cols-2 lg:items-start">
        <div className="space-y-4">
          {turns.slice(0, visibleStep).map((t) => (
            <motion.div
              key={t.text}
              initial={false}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, ease: EASE }}
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

          {visiblePhase > 0 && (
            <div className="rounded-[1.5rem] border border-border bg-card px-6 py-5">
              <ul className="space-y-2.5">
                {analysis.slice(0, visiblePhase).map((a, i) => {
                  const complete = i < visiblePhase - 1 || completeStory;
                  return (
                    <motion.li
                      key={a}
                      initial={false}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.35, ease: EASE }}
                      className="flex items-center gap-3 text-[0.9375rem] text-muted-foreground"
                    >
                      <span className="grid size-5 shrink-0 place-items-center">
                        {complete ? (
                          <motion.span
                            initial={false}
                            animate={{ scale: 1, opacity: 1 }}
                            transition={{ duration: 0.3, ease: EASE }}
                            className="grid size-5 place-items-center rounded-full bg-primary/15"
                          >
                            <Check className="size-3 text-foreground" />
                          </motion.span>
                        ) : (
                          <span
                            className="dw-pulse-soft size-1.5 rounded-full bg-primary"
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

          {completeStory && (
            <motion.p
              initial={false}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <span className="rounded-[1.5rem] rounded-bl-lg border border-primary/40 bg-card px-6 py-4 text-[0.95rem] font-medium">
                Ecco la tua decisione.
              </span>
            </motion.p>
          )}

          <p className="sr-only" aria-live="polite">
            {completeStory ? "Riepilogo della scelta pronto" : ""}
          </p>
        </div>

        <motion.div
          initial={false}
        >
          <TiltCard className="rounded-[2.25rem]"><DecisionReport active={completeStory} /></TiltCard>
        </motion.div>
      </div>
    </Section>
  );
}