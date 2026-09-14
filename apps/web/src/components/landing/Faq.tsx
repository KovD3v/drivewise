import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Section, Eyebrow } from "./Section";
import { Reveal } from "./Reveal";
import { EASE } from "@/lib/motion";

const faqs = [
  {
    q: "DriveWise vende veicoli?",
    a: "No. DriveWise non vende e non intermedia: analizza e spiega. L'obiettivo è farti arrivare alla decisione giusta, non a un annuncio.",
  },
  {
    q: "In cosa è diverso da un'IA generica?",
    a: "Ogni risposta è una decisione strutturata: Decision Score, livello di confidenza, alternative valutate e compromessi espliciti.",
  },
  {
    q: "Su quali dati si basa l'analisi?",
    a: "Costi reali di possesso, affidabilità, consumi, sicurezza, dimensioni e caratteristiche tecniche, pesati sul tuo profilo d'uso.",
  },
  {
    q: "Funziona anche per moto e scooter?",
    a: "Sì. Auto, moto e scooter vengono valutati con lo stesso modello di decisione, adattato alla categoria.",
  },
  {
    q: "Quanto tempo serve per avere una risposta?",
    a: "Pochi minuti. Racconti cosa ti serve, rispondi a qualche domanda mirata e ricevi il tuo Decision Report.",
  },
];

/** Progressive "typing" of an answer, character by character. */
function Typewriter({ text, enabled }: { text: string; enabled: boolean }) {
  const [count, setCount] = useState(enabled ? 0 : text.length);

  useEffect(() => {
    if (!enabled) {
      setCount(text.length);
      return;
    }
    setCount(0);
    let i = 0;
    const id = setInterval(() => {
      i = Math.min(text.length, i + 2);
      setCount(i);
      if (i >= text.length) clearInterval(id);
    }, 16);
    return () => clearInterval(id);
  }, [text, enabled]);

  const done = count >= text.length;
  return (
    <span>
      {text.slice(0, count)}
      {!done && (
        <span className="ml-0.5 inline-block h-[1em] w-[2px] translate-y-[0.15em] animate-pulse bg-primary align-middle" />
      )}
    </span>
  );
}

function PlusIcon({ open }: { open: boolean }) {
  return (
    <span
      aria-hidden
      className="relative grid size-7 shrink-0 place-items-center rounded-full border border-border transition-colors duration-300 group-hover:border-primary/50"
      style={{
        transform: `rotate(${open ? 45 : 0}deg)`,
        transition: "transform 420ms cubic-bezier(0.22,1,0.36,1), border-color 300ms",
      }}
    >
      <span className="absolute h-[1.5px] w-3 rounded-full bg-foreground/70" />
      <span className="absolute h-3 w-[1.5px] rounded-full bg-foreground/70" />
    </span>
  );
}

export function Faq() {
  const reduce = !!useReducedMotion();
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const [seen, setSeen] = useState<number[]>([]);

  const toggle = (i: number) => {
    setOpenIndex((p) => (p === i ? null : i));
    setSeen((p) => (p.includes(i) ? p : [...p, i]));
  };

  const progress = seen.length / faqs.length;

  return (
    <Section id="faq">
      <div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:items-start lg:gap-20">
        <Reveal className="lg:sticky lg:top-32">
          <Eyebrow>FAQ</Eyebrow>
          <h2 className="mt-7 text-4xl leading-[1.08] font-bold sm:text-5xl">
            Domande frequenti.
          </h2>
        </Reveal>

        <Reveal delay={0.06}>
          <div className="relative pl-6">
            {/* vertical completion bar */}
            <div aria-hidden className="absolute top-0 bottom-0 left-0 w-px bg-border">
              <motion.div
                className="absolute inset-x-0 top-0 origin-top bg-primary"
                initial={{ height: "0%" }}
                animate={{ height: `${progress * 100}%` }}
                transition={{ duration: reduce ? 0 : 0.6, ease: EASE }}
              />
            </div>

            <ul>
              {faqs.map((f, i) => {
                const open = openIndex === i;
                const dimmed = openIndex !== null && !open;
                return (
                  <motion.li
                    key={f.q}
                    animate={{ scale: dimmed && !reduce ? 0.98 : 1, opacity: dimmed ? 0.72 : 1 }}
                    transition={{ duration: 0.4, ease: EASE }}
                    className="group relative border-b border-border"
                  >
                    {/* magnetic left bar */}
                    <span
                      aria-hidden
                      className={`absolute top-0 -left-6 w-[2px] origin-top rounded-full bg-primary transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] ${
                        open ? "h-full opacity-100" : "h-0 opacity-0 group-hover:h-full group-hover:opacity-70"
                      }`}
                    />
                    {open && !reduce && (
                      <motion.span
                        aria-hidden
                        className="pointer-events-none absolute inset-y-0 -left-6 w-16 rounded-r-2xl bg-primary/10 blur-lg"
                        animate={{ opacity: [0.35, 0.7, 0.35] }}
                        transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
                      />
                    )}

                    <button
                      type="button"
                      onClick={() => toggle(i)}
                      aria-expanded={open}
                      aria-controls={`faq-panel-${i}`}
                      className="relative flex w-full items-center gap-4 py-6 text-left"
                    >
                      <span
                        className={`font-heading text-xs font-semibold tabular-nums transition-colors duration-300 ${
                          open || seen.includes(i) ? "text-primary" : "text-muted-foreground"
                        }`}
                      >
                        0{i + 1}
                      </span>
                      <span className="flex-1 text-[1.0625rem] font-semibold">{f.q}</span>
                      <PlusIcon open={open} />
                    </button>

                    <AnimatePresence initial={false}>
                      {open && (
                        <motion.div
                          id={`faq-panel-${i}`}
                          key="panel"
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: reduce ? 0 : 0.55, ease: EASE }}
                          className="relative overflow-hidden"
                        >
                          <p className="max-w-prose pb-7 pl-9 text-[0.95rem] leading-relaxed text-muted-foreground">
                            <Typewriter text={f.a} enabled={!reduce} />
                          </p>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.li>
                );
              })}
            </ul>

            <a
              href="#decision-bar"
              className="group mt-8 inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition-colors duration-300 hover:text-foreground"
            >
              Altre domande? Inizia la scelta guidata
              <ArrowRight className="size-4 transition-transform duration-300 group-hover:translate-x-1" />
            </a>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}