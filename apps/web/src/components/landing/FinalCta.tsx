import { Section } from "./Section";
import { Reveal } from "./Reveal";
import { CtaButton } from "./CtaButton";
import { track } from "@/lib/analytics";

export function FinalCta() {
  return (
    <Section>
      <Reveal>
        <div className="rounded-[2.5rem] border border-border bg-card px-8 py-20 text-center sm:px-16 sm:py-28">
          <h2 className="mx-auto max-w-3xl text-4xl leading-[1.06] font-extrabold sm:text-6xl">
            La tua prossima scelta parte da qui.
          </h2>
          <CtaButton
            to="/app/start"
            size="lg"
            className="mt-12"
            onClick={() => track("landing_start_cta_click", { source: "final_cta" })}
          >
            Inizia la scelta guidata
          </CtaButton>
        </div>
      </Reveal>
    </Section>
  );
}