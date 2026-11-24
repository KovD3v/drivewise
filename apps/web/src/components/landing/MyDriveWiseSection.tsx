import { ScaleOnScroll } from "./ScaleOnScroll";
import { StoryBridge } from "./StoryBridge";
import { SectionAurora, RevealText } from "./DesignEffects";
import { Link } from "@tanstack/react-router";
import { Section, Eyebrow } from "./Section";
import { LifecycleVignette } from "./LifecycleVignette";
import { MotionPause } from "./MotionPause";

export function MyDriveWiseSection() {
  return (
    <>
      <div className="flex justify-center py-4">
        <StoryBridge />
      </div>
      <Section id="dopo-la-scelta" className="dw-band dw-band-card relative isolate scroll-mt-24 pt-4 md:pt-4 lg:pt-4">
        <SectionAurora variant="lavender" />
        <div className="text-center">
          <Eyebrow>Capitolo 2 · Dopo la scelta</Eyebrow>
          <h2 className="mx-auto mt-7 max-w-3xl text-4xl leading-[1.08] font-bold sm:text-5xl">
            <RevealText text="La scelta è solo l'inizio." />
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-[1.0625rem] leading-relaxed text-muted-foreground">
            Il veicolo che hai appena visto scegliere entra in My DriveWise: costi, scadenze,
            manutenzione e mercato, in un unico posto.
          </p>
        </div>
        <div className="mx-auto mt-12 w-full max-w-6xl">
          <ScaleOnScroll>
            <MotionPause>
              <LifecycleVignette />
            </MotionPause>
          </ScaleOnScroll>
        </div>
        <div className="mt-10 flex justify-center sm:justify-end">
          <Link
            to="/app/me"
            className="btn-shine overflow-hidden inline-flex min-h-11 items-center rounded-full bg-primary px-6 font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Scopri My DriveWise →
          </Link>
        </div>
      </Section>
    </>
  );
}
