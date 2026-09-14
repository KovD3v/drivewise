import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { motion, useReducedMotion } from "framer-motion";
import { TrendingUp } from "lucide-react";
import { MeHeader } from "@/components/me/MeHeader";
import { GreetingHeader } from "@/components/me/GreetingHeader";
import { CustomizableFeatureGrid } from "@/components/me/CustomizableFeatureGrid";
import { OnboardingDialog } from "@/components/me/OnboardingDialog";
import { NotificationSettings } from "@/components/me/NotificationSettings";
import { featureIcon } from "@/components/me/icons";
import { METRICS } from "@/lib/mydrivewise";
import { listSavedAnalyses, type SavedAnalysis } from "@/lib/saved-analyses";
import {
  completeOnboarding,
  getMyProfile,
  providerName,
  setMarketingOptIn,
  type Profile,
} from "@/lib/profile";
import { useAuthSession } from "@/hooks/use-auth-session";
import { useCountUp } from "@/lib/use-count-up";
import { EASE } from "@/lib/motion";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/app/me/")({
  head: () => ({
    meta: [
      { title: "My DriveWise — la tua area personale" },
      {
        name: "description",
        content:
          "My DriveWise: garage, costi, manutenzione, documenti e consigli intelligenti per tutto il ciclo di vita del tuo veicolo.",
      },
      { property: "og:title", content: "My DriveWise — la tua area personale" },
      {
        property: "og:description",
        content:
          "Un assistente personale che ti accompagna in tutto il ciclo di vita del veicolo.",
      },
    ],
  }),
  component: MyDriveWise,
});

function MetricCard({
  metric,
  index,
}: {
  metric: (typeof METRICS)[number];
  index: number;
}) {
  const reduce = useReducedMotion();
  const value = useCountUp(metric.value, 1100, !!reduce);
  const Icon = featureIcon(metric.icon);
  const ring = metric.icon === "ring";

  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: EASE, delay: 0.25 + index * 0.07 }}
      className="flex items-center gap-3 rounded-2xl border border-border/70 bg-card/70 px-4 py-4 backdrop-blur transition-shadow duration-500 hover:shadow-[var(--shadow-soft)]"
    >
      {ring ? (
        <span className="relative grid size-11 shrink-0 place-items-center">
          <svg viewBox="0 0 44 44" className="size-11 -rotate-90">
            <circle cx="22" cy="22" r="19" fill="none" stroke="var(--color-primary)" strokeOpacity="0.18" strokeWidth="4" />
            <motion.circle
              cx="22"
              cy="22"
              r="19"
              fill="none"
              stroke="var(--color-primary)"
              strokeWidth="4"
              strokeLinecap="round"
              initial={reduce ? false : { pathLength: 0 }}
              animate={{ pathLength: metric.value / 100 }}
              transition={{ duration: 1.1, ease: EASE, delay: 0.3 }}
            />
          </svg>
        </span>
      ) : (
        <span className="grid size-11 shrink-0 place-items-center rounded-full border border-primary/20 bg-primary/8 text-primary">
          <Icon className="size-[1.05rem]" strokeWidth={1.8} />
        </span>
      )}
      <span className="min-w-0">
        <span className="block font-heading text-xl font-extrabold tracking-tight">
          {value}
          {metric.suffix}
        </span>
        <span className="block truncate text-xs text-muted-foreground">{metric.label}</span>
      </span>
    </motion.div>
  );
}

function MyDriveWise() {
  const reduce = useReducedMotion();
  const { user, ready } = useAuthSession();
  const [saved, setSaved] = useState<SavedAnalysis[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null);

  useEffect(() => {
    if (!ready || !user) {
      setProfile(null);
      return;
    }
    let alive = true;
    void getMyProfile(user.id)
      .then((p) => {
        if (alive) setProfile(p);
      })
      .catch(() => {
        /* il profilo si ricarica al prossimo accesso */
      });
    return () => {
      alive = false;
    };
  }, [ready, user]);

  useEffect(() => {
    if (!ready) return;
    if (!user) {
      setSaved([]);
      setLoaded(true);
      return;
    }
    let alive = true;
    void listSavedAnalyses().then((list) => {
      if (!alive) return;
      setSaved(list);
      setLoaded(true);
    });
    return () => {
      alive = false;
    };
  }, [ready, user]);

  // I contatori includono le analisi realmente salvate dall'utente.
  const metrics = METRICS.map((m) =>
    m.label === "Analisi effettuate" || m.label === "Decisioni effettuate"
      ? { ...m, value: m.value + saved.length }
      : m,
  );

  const fade = (delay: number) => ({
    initial: reduce ? false : { opacity: 0, y: 16, filter: "blur(6px)" },
    animate: { opacity: 1, y: 0, filter: "blur(0px)" },
    transition: { duration: 0.6, ease: EASE, delay },
  });

  const needsOnboarding = !!user && !!profile && !profile.privacyConsentAt;

  const confirmOnboarding = async (displayName: string) => {
    if (!user) return;
    const next = await completeOnboarding(user.id, displayName);
    setProfile(next);
  };

  const changeOptIn = async (value: boolean) => {
    if (!user) return;
    const next = await setMarketingOptIn(user.id, value);
    setProfile(next);
  };

  return (
    <div className="min-h-screen overflow-x-clip bg-background">
      <MeHeader />

      {profile && (
        <OnboardingDialog
          open={needsOnboarding}
          initialName={profile.displayName ?? providerName(user?.user_metadata)}
          onConfirm={confirmOnboarding}
        />
      )}

      <main className="mx-auto w-full max-w-[78rem] overflow-x-clip px-6 pt-12 pb-28 sm:px-8">
        <GreetingHeader />

        <motion.div
          {...fade(0.3)}
          className="mt-6 inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/8 px-4 py-2 text-sm text-foreground/80"
        >
          <TrendingUp className="size-4 text-primary" />
          Il tuo Decision Score medio è migliorato del 4% questo mese
        </motion.div>

        <div className="mt-10 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {metrics.map((m, i) => (
            <MetricCard key={`${m.label}-${loaded ? saved.length : "x"}`} metric={m} index={i} />
          ))}
        </div>

        {saved.length > 0 && (
          <section className="mt-16">
            <motion.h2
              {...fade(0.4)}
              className="font-heading text-2xl font-extrabold tracking-tight"
            >
              Decision History
            </motion.h2>
            <motion.p {...fade(0.44)} className="mt-2 text-muted-foreground">
              Le analisi che hai salvato dal tuo Decision Report.
            </motion.p>
            <ul className="mt-6 space-y-3">
              {saved.map((a, i) => (
                <motion.li
                  key={a.id}
                  initial={reduce ? false : { opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, ease: EASE, delay: 0.1 + i * 0.05 }}
                >
                  <Link
                    to="/app/vehicle/$id"
                    params={{ id: a.vehicleId }}
                    className="flex items-center gap-4 rounded-2xl border border-border/70 bg-card/70 px-4 py-4 backdrop-blur transition-colors hover:border-primary/40"
                  >
                    <span className="font-heading shrink-0 text-2xl font-extrabold tabular-nums text-primary">
                      {a.score}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium">
                        {a.brand} {a.model}
                      </span>
                      <span className="mt-1 flex flex-wrap gap-1.5">
                        {a.tags.slice(0, 4).map((t) => (
                          <span
                            key={t}
                            className="rounded-full border border-border/70 px-2 py-0.5 text-[0.68rem] text-muted-foreground"
                          >
                            {t}
                          </span>
                        ))}
                      </span>
                    </span>
                    <span className="shrink-0 text-[0.72rem] text-muted-foreground">
                      {new Date(a.createdAt).toLocaleDateString("it-IT")}
                    </span>
                  </Link>
                </motion.li>
              ))}
            </ul>
          </section>
        )}

        <motion.h2
          {...fade(0.45)}
          className="mt-20 font-heading text-2xl font-extrabold tracking-tight sm:text-3xl"
        >
          Tutto il ciclo di vita del tuo veicolo
        </motion.h2>
        <motion.p {...fade(0.5)} className="mt-2 max-w-2xl text-muted-foreground">
          Le funzioni che stiamo costruendo, nell'ordine in cui ti serviranno.
        </motion.p>

        <CustomizableFeatureGrid />

        {profile && (
          <NotificationSettings optIn={profile.marketingEmailsOptIn} onChange={changeOptIn} />
        )}
      </main>
    </div>
  );
}