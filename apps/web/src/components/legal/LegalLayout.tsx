import { useEffect, useState, type ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { AppHeader } from "@/components/app/AppHeader";
import { Footer } from "@/components/landing/Footer";
import { ScrollWayfinding } from "@/components/nav/ScrollWayfinding";
import { cn } from "@/lib/utils";

export type LegalSection = { id: string; title: string; body: ReactNode };

export function LegalBadge({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border border-primary/30 bg-primary/10 px-3.5 py-1.5 text-[0.6875rem] font-semibold tracking-[0.18em] text-foreground uppercase">
      {children}
    </span>
  );
}

/** Indice sticky: evidenzia la sezione visibile su schermi larghi. */
function TableOfContents({ sections }: { sections: LegalSection[] }) {
  const [active, setActive] = useState(sections[0]?.id ?? "");

  useEffect(() => {
    const els = sections
      .map((s) => document.getElementById(s.id))
      .filter((el): el is HTMLElement => Boolean(el));
    if (!els.length) return;
    const obs = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (visible) setActive(visible.target.id);
      },
      { rootMargin: "-20% 0px -65% 0px", threshold: 0 },
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, [sections]);

  return (
    <nav aria-label="Indice della pagina" className="sticky top-28">
      <p className="text-[0.6875rem] font-semibold tracking-[0.18em] text-muted-foreground uppercase">
        In questa pagina
      </p>
      <ul className="mt-4 space-y-1 border-l border-border/70">
        {sections.map((s) => (
          <li key={s.id}>
            <a
              href={`#${s.id}`}
              className={cn(
                "-ml-px block border-l-2 py-1.5 pl-4 text-[0.8125rem] leading-snug transition-colors duration-300",
                active === s.id
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              {s.title}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function LegalPage({
  badge,
  title,
  subtitle,
  sections,
  children,
  updatedAt,
}: {
  badge: string;
  title: string;
  subtitle?: string;
  sections?: LegalSection[];
  children?: ReactNode;
  updatedAt?: string;
}) {
  const reduce = useReducedMotion();
  const fade = (delay = 0) => ({
    initial: reduce ? { opacity: 1 } : { opacity: 0, y: 16 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: reduce ? 0 : 0.6, delay: reduce ? 0 : delay, ease: [0.22, 1, 0.36, 1] as const },
  });

  return (
    <div className="min-h-screen bg-background">
      <AppHeader label={badge} maxWidth="max-w-[74rem]" sticky />
      <main className="mx-auto w-full max-w-[74rem] px-6 pt-16 pb-24 sm:px-8 sm:pt-24">
        <motion.header {...fade(0)} className="max-w-[46rem]">
          <LegalBadge>{badge}</LegalBadge>
          <h1 className="font-heading mt-6 text-[2.5rem] leading-[1.03] font-extrabold tracking-[-0.035em] sm:text-[3.25rem]">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-5 text-[1.0625rem] leading-relaxed text-muted-foreground">{subtitle}</p>
          )}
        </motion.header>

        <div className="mt-14 grid gap-10 lg:grid-cols-[minmax(0,1fr)_16rem] lg:items-start lg:gap-16">
          <div className="min-w-0 space-y-5">
            {sections?.map((s, i) => (
              <motion.section
                key={s.id}
                id={s.id}
                {...fade(0.05 + i * 0.04)}
                className="scroll-mt-28 rounded-3xl border border-border/70 bg-card p-7 shadow-[var(--shadow-soft)] transition-shadow duration-500 hover:shadow-[var(--shadow-lift)] sm:p-9"
              >
                <h2 className="font-heading text-[1.25rem] font-bold tracking-[-0.02em]">{s.title}</h2>
                <div className="mt-4 space-y-4 text-[0.95rem] leading-relaxed text-muted-foreground">
                  {s.body}
                </div>
              </motion.section>
            ))}
            {children}
            {updatedAt && (
              <p className="pt-2 text-[0.8125rem] text-muted-foreground">
                Ultimo aggiornamento: {updatedAt}
              </p>
            )}
          </div>

          {sections && sections.length > 0 && (
            <aside className="hidden lg:block">
              <TableOfContents sections={sections} />
            </aside>
          )}
        </div>
      </main>
      <Footer />
      <ScrollWayfinding />
    </div>
  );
}
