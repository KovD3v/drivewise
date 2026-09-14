import { useState } from "react";
import { createFileRoute, notFound, Link } from "@tanstack/react-router";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowLeft, Check } from "lucide-react";
import { MeHeader } from "@/components/me/MeHeader";
import { featureIcon } from "@/components/me/icons";
import { FeaturePreview } from "@/components/me/FeaturePreview";
import { AppTransitionLink } from "@/components/transition/AppTransitionLink";
import { getFeature, existingFeatureRoutes } from "@/lib/mydrivewise";
import { EASE } from "@/lib/motion";

export const Route = createFileRoute("/app/me/$slug")({
  loader: ({ params }) => {
    const feature = getFeature(params.slug);
    if (!feature) throw notFound();
    return { feature };
  },
  head: ({ loaderData }) => {
    if (!loaderData) {
      return { meta: [{ title: "Non disponibile — My DriveWise" }, { name: "robots", content: "noindex" }] };
    }
    const { feature } = loaderData;
    const title = `${feature.title} — My DriveWise`;
    return {
      meta: [
        { title },
        { name: "description", content: feature.short },
        { property: "og:title", content: title },
        { property: "og:description", content: feature.short },
      ],
    };
  },
  component: FeatureDetail,
});

function FeatureDetail() {
  const { feature } = Route.useLoaderData();
  const [requested, setRequested] = useState(false);
  const destination = existingFeatureRoutes[feature.slug as keyof typeof existingFeatureRoutes];
  const Icon = featureIcon(feature.icon);
  const reduce = useReducedMotion();

  const fade = (delay: number) => ({
    initial: reduce ? false : { opacity: 0, y: 16, filter: "blur(6px)" },
    animate: { opacity: 1, y: 0, filter: "blur(0px)" },
    transition: { duration: 0.6, ease: EASE, delay },
  });

  return (
    <div className="min-h-screen bg-background">
      <MeHeader label={feature.title} />

      <main className="mx-auto w-full max-w-[68rem] px-6 pt-10 pb-28 sm:px-8">
        <p className="mb-5 text-xs text-muted-foreground">Area personale demo: dati di esempio e salvataggi solo in questo browser.</p>
        <AppTransitionLink
          to="/app/me"
          steps={["Ritorno a My DriveWise...", "Caricamento dashboard...", "Pronto."]}
          className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          My DriveWise
        </AppTransitionLink>

        <div className="mt-8 grid items-center gap-10 lg:grid-cols-[1.05fr_0.95fr]">
          <div>
            <motion.span
              {...fade(0.05)}
              className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/70 px-3 py-1.5 text-[0.65rem] font-semibold tracking-[0.14em] text-muted-foreground uppercase"
            >
              {destination ? "Disponibile" : "Demo"}
            </motion.span>

            <motion.h1
              {...fade(0.12)}
              className="mt-5 font-heading text-4xl font-extrabold tracking-tight sm:text-5xl"
            >
              {feature.title}
            </motion.h1>
            <motion.p {...fade(0.2)} className="mt-4 text-lg leading-relaxed text-muted-foreground">
              {feature.long}
            </motion.p>

            <ul className="mt-8 space-y-3">
              {feature.benefits.map((b, i) => (
                <motion.li
                  key={b}
                  initial={reduce ? false : { opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.45, ease: EASE, delay: 0.32 + i * 0.09 }}
                  className="flex items-start gap-3 text-[0.95rem] text-foreground/85"
                >
                  <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-primary/12 text-primary">
                    <Check className="size-3.5" strokeWidth={3} />
                  </span>
                  {b}
                </motion.li>
              ))}
            </ul>

            <motion.div {...fade(0.75)} className="mt-10">
              {destination ? <Link to={destination} className="inline-flex h-13 items-center rounded-full bg-primary px-8 py-4 font-medium text-primary-foreground">Apri {feature.title}</Link> : <button
                type="button"
                onClick={() => setRequested(true)}
                className="cta-shine group relative inline-flex h-13 items-center justify-center overflow-hidden rounded-full bg-primary px-8 py-4 font-medium text-primary-foreground shadow-[var(--shadow-soft)] transition-all duration-300 hover:bg-primary-hover hover:shadow-[var(--shadow-lift)] motion-safe:hover:scale-[1.02]"
              >
                {requested ? "Richiesta simulata" : "Richiedi accesso anticipato"}
              </button>}
            </motion.div>
          </div>

          {/* Mockup astratto coerente col brand */}
          <motion.div
            initial={reduce ? false : { opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, ease: EASE, delay: 0.25 }}
            className="relative overflow-hidden rounded-3xl border border-border/70 bg-card/70 p-6 backdrop-blur shadow-[var(--shadow-lift)]"
          >
            <span
              aria-hidden
              className="pointer-events-none absolute inset-0 bg-[radial-gradient(110%_90%_at_20%_0%,color-mix(in_oklab,var(--color-primary)_16%,transparent),transparent_65%)]"
            />
            <span
              aria-hidden
              className="pointer-events-none absolute inset-0 opacity-[0.5] [background-image:linear-gradient(to_right,color-mix(in_oklab,var(--color-primary)_10%,transparent)_1px,transparent_1px),linear-gradient(to_bottom,color-mix(in_oklab,var(--color-primary)_10%,transparent)_1px,transparent_1px)] [background-size:28px_28px]"
            />
            <div className="relative">
              <div className="flex items-center gap-3">
                <span className="grid size-11 place-items-center rounded-full border border-primary/25 bg-primary/10 text-primary shadow-[0_0_26px_-12px_var(--color-primary)]">
                  <Icon className="size-5" strokeWidth={1.8} />
                </span>
                <div>
                  <p className="font-heading text-sm font-bold">{feature.title}</p>
                  <p className="text-[0.72rem] text-muted-foreground">Anteprima interfaccia</p>
                </div>
              </div>

              <div className="mt-6 space-y-3">
                {feature.preview && (
                  <div className="rounded-2xl border border-border/60 bg-background/60 p-4">
                    <FeaturePreview kind={feature.preview} />
                  </div>
                )}
                {[92, 74, 58].map((w, i) => (
                  <motion.div
                    key={w}
                    className="h-3 rounded-full bg-primary/15"
                    initial={reduce ? false : { scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    style={{ width: `${w}%`, transformOrigin: "left" }}
                    transition={{ duration: 0.7, ease: EASE, delay: 0.5 + i * 0.1 }}
                  />
                ))}
                <div className="grid grid-cols-2 gap-3 pt-2">
                  {["Sintesi", "Dettaglio"].map((t) => (
                    <div
                      key={t}
                      className="rounded-2xl border border-border/60 bg-background/60 px-4 py-5 text-center text-xs text-muted-foreground"
                    >
                      {t}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  );
}