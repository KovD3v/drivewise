import { useEffect, useState } from "react";
import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { Play } from "lucide-react";
import { CtaButton } from "./CtaButton";
import { DecisionBar } from "./DecisionBar";
import { DecisionNetwork } from "./DecisionNetwork";
import { HeroVision } from "./HeroVision";
import { EASE as ease } from "@/lib/motion";
import { track } from "@/lib/analytics";

const words = ["Trova", "il veicolo", "perfetto."];
const SUBTITLE = "La scelta giusta, spiegata.";

/** Stable subtitle: one complete DOM node, with no timer, mask or resettable state. */
function SubtitleReveal({ text }: { text: string }) {
  return (
    <span className="inline-block whitespace-pre" role="text">
      {text}
    </span>
  );
}

export function Hero() {
  const reduce = useReducedMotion();
  const { scrollY } = useScroll();
  const [enabled, setEnabled] = useState(false);
  useEffect(() => setEnabled(!reduce), [reduce]);
  const textY = useTransform(scrollY, [0, 600], [0, enabled ? 18 : 0]);

  return (
    <section
      id="top"
      className="relative flex min-h-[100svh] flex-col justify-center overflow-hidden pt-44 pb-28 sm:pt-52 md:pb-40"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute top-[-18rem] left-1/2 size-[46rem] -translate-x-1/2 rounded-full bg-primary/10 blur-[140px]"
      />
      <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
        <div
          className="absolute top-[12%] -left-[10%] size-[34rem] rounded-full bg-primary/[0.07] blur-[120px] motion-safe:[animation:hero-blob_26s_ease-in-out_infinite]"
        />
        <div
          className="absolute right-[-8%] bottom-[6%] size-[30rem] rounded-full bg-accent/[0.05] blur-[130px] motion-safe:[animation:hero-blob_34s_ease-in-out_infinite_reverse]"
        />
      </div>
      <DecisionNetwork className="pointer-events-none absolute inset-0 size-full" />

      <div className="relative mx-auto grid w-full max-w-7xl gap-16 px-6 sm:px-8 lg:grid-cols-[0.62fr_1fr] lg:items-center lg:gap-14 xl:gap-16">
        <motion.div style={{ y: textY }}>
          <h1 className="text-[3.25rem] leading-[0.95] font-extrabold tracking-[-0.045em] sm:text-[4.75rem] lg:text-[4rem] xl:text-[4.5rem]">
            {words.map((w, i) => (
              <motion.span
                key={w}
                className="inline-block"
                initial={
                  reduce
                    ? { opacity: 1 }
                    : { opacity: 0, y: 20, filter: "blur(6px)" }
                }
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                transition={{ duration: reduce ? 0 : 0.7, delay: reduce ? 0 : i * 0.16, ease }}
              >
                {w}
                {i < words.length - 1 ? "\u00A0" : ""}
              </motion.span>
            ))}
          </h1>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.55, ease }}
            className="font-heading mt-7 text-2xl font-medium tracking-[-0.015em] text-foreground/65 sm:text-[2rem] lg:text-[1.6rem]"
          >
            <SubtitleReveal text={SUBTITLE} />
          </motion.p>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.65, ease }}
            className="mt-8 max-w-xl text-[1.0625rem] leading-[1.7] text-muted-foreground"
          >
            DriveWise analizza migliaia di informazioni per aiutarti a scegliere il veicolo più
            adatto alle tue esigenze, spiegandoti sempre il perché.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.75, ease }}
            className="mt-10 flex flex-wrap gap-3"
          >
            <CtaButton
              to="/app/start"
              size="lg"
              className="cta-shine"
              onClick={() => track("landing_start_cta_click", { source: "hero" })}
            >
              Inizia la scelta guidata
            </CtaButton>
            <CtaButton
              href="#demo"
              variant="ghost"
              size="lg"
              onClick={() => track("landing_example_click")}
            >
              <Play className="size-4 fill-current" />
              Guarda un esempio
            </CtaButton>
          </motion.div>
        </motion.div>

        <HeroVision />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 26 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.85, ease }}
        className="relative mx-auto mt-32 w-full max-w-4xl px-6 sm:px-8"
      >
        <DecisionBar />
      </motion.div>
    </section>
  );
}