import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { AppTransitionLink } from "@/components/transition/AppTransitionLink";
import { featureIcon } from "./icons";
import { FeaturePreview } from "./FeaturePreview";
import { EASE } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { type Feature } from "@/lib/mydrivewise";

export function FeatureCard({
  feature,
  index,
  inGrid,
}: {
  feature: Feature;
  index: number;
  inGrid?: boolean;
}) {
  const Icon = featureIcon(feature.icon);
  const reduce = useReducedMotion();
  const hero = feature.hero;

  return (
    <motion.article
      initial={reduce ? false : { opacity: 0, y: 22 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5, ease: EASE, delay: Math.min(index, 6) * 0.05 }}
      className={cn(
        "group relative flex flex-col overflow-hidden rounded-3xl border border-border/70 bg-card/70 p-6 backdrop-blur",
        "shadow-[var(--shadow-soft)] transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]",
        "motion-safe:hover:-translate-y-1.5 hover:border-primary/35 hover:shadow-[var(--shadow-lift)]",
        hero && "border-primary/30",
        hero && !inGrid && "sm:col-span-2 sm:row-span-2",
        inGrid && "h-full",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-700 group-hover:opacity-100",
          "bg-[radial-gradient(120%_100%_at_0%_0%,color-mix(in_oklab,var(--color-primary)_12%,transparent),transparent_62%)]",
        )}
      />
      {hero && (
        <span
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(90%_80%_at_100%_0%,color-mix(in_oklab,var(--color-primary)_14%,transparent),transparent_65%)]"
        />
      )}

      <div className="relative flex items-start justify-between gap-3">
        <span
          className={cn(
            "grid place-items-center rounded-full border border-primary/25 bg-primary/10 text-primary",
            "shadow-[0_0_26px_-12px_var(--color-primary)] transition-transform duration-500 group-hover:scale-105",
            hero ? "size-14" : "size-11",
            hero && !reduce && "animate-status-pulse",
          )}
        >
          <Icon className={hero ? "size-6" : "size-5"} strokeWidth={1.8} />
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/[0.06] px-2.5 py-1 text-[0.6rem] font-medium tracking-[0.14em] text-muted-foreground uppercase backdrop-blur-sm shadow-[0_0_18px_-12px_var(--color-primary)]">
          <span className="size-1 rounded-full bg-primary/70" />
          Coming Soon
        </span>
      </div>

      <h4
        className={cn(
          "relative mt-5 font-heading font-extrabold tracking-tight text-foreground",
          hero ? "text-2xl sm:text-3xl" : "text-lg",
        )}
      >
        {feature.title}
      </h4>
      <p
        className={cn(
          "relative mt-2 text-muted-foreground",
          hero ? "max-w-xl text-[0.98rem] leading-relaxed" : "text-sm leading-relaxed",
        )}
      >
        {feature.short}
      </p>

      {feature.preview && (
        <div className="relative mt-5">
          <FeaturePreview kind={feature.preview} />
        </div>
      )}

      <div className="relative mt-auto pt-6">
        <AppTransitionLink
          to="/app/me/$slug"
          params={{ slug: feature.slug }}
          steps={["Apertura anteprima...", "Preparazione contenuti...", "Pronto."]}
          className={cn(
            "inline-flex items-center gap-2 rounded-full border border-border bg-background/70 px-4 py-3 text-sm font-medium",
            "transition-all duration-300 hover:border-primary/45 hover:text-primary",
            "[&_svg]:transition-transform [&_svg]:duration-300 motion-safe:hover:[&_svg]:translate-x-[3px]",
          )}
        >
          Scopri di più
          <ArrowRight className="size-4" />
        </AppTransitionLink>
      </div>
    </motion.article>
  );
}