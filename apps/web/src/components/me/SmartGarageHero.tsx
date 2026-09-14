import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Radar } from "lucide-react";
import { AppTransitionLink } from "@/components/transition/AppTransitionLink";
import { EASE } from "@/lib/motion";
import type { Feature } from "@/lib/mydrivewise";

export function SmartGarageHero({ feature }: { feature: Feature }) {
  const reduce = useReducedMotion();

  return (
    <motion.article
      initial={reduce ? false : { opacity: 0, y: 22 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.6, ease: EASE }}
      className="group relative col-span-full overflow-hidden rounded-3xl border border-primary/30 bg-card/70 p-7 backdrop-blur shadow-[var(--shadow-soft)] transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] hover:shadow-[var(--shadow-lift)] sm:col-span-2 sm:p-9"
    >
      <motion.span
        aria-hidden
        className="pointer-events-none absolute -inset-24 -z-10"
        style={{
          background:
            "radial-gradient(45% 55% at 20% 20%, color-mix(in oklab, var(--color-primary) 16%, transparent), transparent 70%), radial-gradient(40% 50% at 85% 15%, color-mix(in oklab, var(--color-accent) 12%, transparent), transparent 70%)",
          filter: "blur(24px)",
        }}
        animate={reduce ? {} : { x: [0, 22, 0], y: [0, -14, 0], scale: [1, 1.06, 1] }}
        transition={{ duration: 24, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="flex items-start justify-between gap-3">
        <span className="relative grid size-14 place-items-center rounded-full border border-primary/25 bg-primary/10 text-primary shadow-[0_0_30px_-12px_var(--color-primary)]">
          <Radar className="size-6" strokeWidth={1.8} />
          {!reduce && (
            <motion.span
              aria-hidden
              className="absolute inset-0 rounded-full border border-primary/30"
              animate={{ scale: [1, 1.35], opacity: [0.5, 0] }}
              transition={{ duration: 2.6, repeat: Infinity, ease: "easeOut" }}
            />
          )}
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/[0.06] px-2.5 py-1 text-[0.6rem] font-medium tracking-[0.14em] text-muted-foreground uppercase backdrop-blur-sm shadow-[0_0_18px_-12px_var(--color-primary)]">
          <span className="size-1 rounded-full bg-primary/70" />
          Coming Soon
        </span>
      </div>

      <h4 className="mt-6 font-heading text-2xl font-extrabold tracking-tight sm:text-3xl">
        {feature.title}
      </h4>
      <p className="mt-3 max-w-xl text-[0.98rem] leading-relaxed text-muted-foreground">
        DriveWise monitora continuamente il mercato e confronta il tuo profilo con nuovi modelli.
      </p>

      <motion.div
        initial={reduce ? false : { opacity: 0, y: 10 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6, ease: EASE, delay: 0.2 }}
        className="mt-6 max-w-xl rounded-2xl border border-primary/30 bg-primary/8 px-4 py-3.5 text-sm text-foreground/85"
      >
        «Il nuovo <strong className="font-semibold">Tesla Model Y</strong> migliora del{" "}
        <strong className="font-semibold text-primary">17%</strong> il tuo Decision Score.»
      </motion.div>

      <div className="mt-7">
        <AppTransitionLink
          to="/app/me/$slug"
          params={{ slug: feature.slug }}
          steps={["Apertura anteprima...", "Preparazione contenuti...", "Pronto."]}
          className="inline-flex items-center gap-2 rounded-full border border-primary/40 bg-primary/12 px-5 py-3 text-sm font-medium text-primary transition-all duration-300 hover:bg-primary/18 [&_svg]:transition-transform [&_svg]:duration-300 motion-safe:hover:[&_svg]:translate-x-[3px]"
        >
          Scopri di più
          <ArrowRight className="size-4" />
        </AppTransitionLink>
      </div>
    </motion.article>
  );
}
