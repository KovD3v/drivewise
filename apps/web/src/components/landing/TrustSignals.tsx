import { SectionAurora, TiltCard, RevealText } from "./DesignEffects";
import { RiseOnScroll } from "./RiseOnScroll";
import { WeightsVignette } from "./WeightsVignette";
import { MotionPause } from "./MotionPause";
import { Section, Eyebrow } from "./Section";
import { RevealGroup, RevealItem } from "./Reveal";

export function TrustSignals() {
  return (
    <Section
      id="analisi"
      className="dw-band dw-band-card relative isolate pt-20 pb-10 md:pt-24 md:pb-10 lg:pt-28 lg:pb-10"
    >
      <SectionAurora variant="mint" />
      <RevealGroup stagger={0.09}>
        <RevealItem>
          <Eyebrow>Capitolo 1 · La scelta</Eyebrow>
        </RevealItem>
        <RevealItem>
          <h2 className="mt-7 max-w-3xl text-4xl leading-[1.08] font-bold sm:text-5xl">
            <RevealText text="Tu hai le domande. Noi verifichiamo ogni risposta." />
          </h2>
        </RevealItem>
        <RevealItem>
          <p className="mt-6 max-w-[40rem] text-[1.0625rem] leading-relaxed text-muted-foreground">
            Partiamo da chi sei e controlliamo ogni dettaglio concreto: misure, patente, costi,
            spazio. Poi pesiamo 9 criteri e oltre 120 parametri sul tuo modo di vivere. Nessuna
            opinione generata al volo.
          </p>
        </RevealItem>
      </RevealGroup>

      <RiseOnScroll className="mt-12">
        <MotionPause>
          <WeightsVignette />
        </MotionPause>
      </RiseOnScroll>
    </Section>
  );
}
