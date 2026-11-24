import type { ReactNode } from "react";
import { DecisionPipeline } from "./DecisionPipeline";
import { MotionPause } from "./MotionPause";

/**
 * Hero a colonna unica: testo centrato in alto, vignetta 16:9 a tutta larghezza sotto.
 * `children` = la colonna di testo esistente (h1, sottotitolo, paragrafo, pulsanti), invariata:
 * qui viene solo centrata.
 */
export function HeroStory({ children }: { children: ReactNode }) {
  return (
    <div className="relative mx-auto w-full max-w-7xl px-6 sm:px-8">
      <div className="mx-auto max-w-4xl text-center [&_p]:mx-auto [&>div>div]:justify-center">{children}</div>
      <div className="mx-auto mt-6 w-full max-w-6xl md:mt-8">
        <MotionPause>
          <DecisionPipeline />
        </MotionPause>
      </div>
    </div>
  );
}
