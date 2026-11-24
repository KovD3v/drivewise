import { Reveal, RevealItem } from "./Reveal";
import { RevealText } from "./DesignEffects";
import { useEffect, useState } from "react";
import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { Play } from "lucide-react";
import { CtaButton } from "./CtaButton";
import { DecisionBar } from "./DecisionBar";
import { DecisionNetwork } from "./DecisionNetwork";
import { HeroStory } from "./HeroStory";
import { track } from "@/lib/analytics";

const SUBTITLE = "La scelta giusta di auto, moto e scooter, spiegata.";

/** Stable subtitle: one complete DOM node, with no timer, mask or resettable state. */
function SubtitleReveal({ text }: { text: string }) {
  return (
    <span className="inline-block text-balance">
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
      className="relative scroll-mt-24 flex flex-col overflow-clip pt-32 pb-12 sm:pt-36 md:pb-16"
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

      <HeroStory>
        <motion.div style={{ y: textY }}>
          <h1 className="text-[3.25rem] leading-[0.95] font-extrabold tracking-[-0.045em] sm:text-[4.75rem] lg:text-[4rem] xl:text-[4.5rem]">
            <RevealText text="Trova il veicolo perfetto." />
          </h1>

          <RevealItem as="p"
            className="font-heading mt-7 text-2xl font-medium tracking-[-0.015em] text-muted-foreground sm:text-[2rem] lg:text-[1.6rem]"
          >
            <SubtitleReveal text={SUBTITLE} />
          </RevealItem>

          <RevealItem as="p"
            className="mt-8 max-w-xl text-[1.0625rem] leading-[1.7] text-muted-foreground"
          >
            DriveWise analizza migliaia di informazioni per aiutarti a scegliere il veicolo più
            adatto alle tue esigenze, spiegandoti sempre il perché.
          </RevealItem>

          <Reveal
            className="mt-10 flex flex-wrap gap-3"
          >
            <CtaButton
              to="/app/start"
              size="lg"
              className="btn-shine overflow-hidden"
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
          </Reveal>
        </motion.div>

      </HeroStory>

      <Reveal
        className="relative mx-auto mt-4 w-full max-w-4xl px-6 sm:px-8 md:mt-6"
      >
        <p className="font-heading text-center text-2xl font-bold tracking-[-0.015em] text-foreground sm:text-[2rem] lg:text-[1.6rem]">
          Ora tocca a te: raccontaci cosa cerchi.
        </p>
        <div className="mt-4">
          <DecisionBar />
        </div>
      </Reveal>
    </section>
  );
}