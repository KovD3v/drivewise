import type { ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { EASE, viewportOnce } from "@/lib/motion";
import { cn } from "@/lib/utils";

export function VSection({
  id,
  title,
  intro,
  children,
  className,
}: {
  id?: string;
  title: string;
  intro?: string;
  children: ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.section
      id={id}
      initial={reduce ? { opacity: 1 } : { opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={viewportOnce}
      transition={{ duration: 0.6, ease: EASE }}
      className={cn("scroll-mt-24", className)}
    >
      <h2 className="font-heading text-[1.35rem] font-bold tracking-[-0.02em] sm:text-[1.6rem]">
        {title}
      </h2>
      {intro && <p className="mt-2 max-w-2xl text-[0.9rem] text-muted-foreground">{intro}</p>}
      <div className="mt-6">{children}</div>
    </motion.section>
  );
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "rounded-3xl border border-border/70 bg-card p-6 shadow-[var(--shadow-soft)]",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function Bar({ value, label, suffix }: { value: number; label: string; suffix?: string }) {
  const reduce = useReducedMotion();
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[0.875rem] text-foreground">{label}</span>
        <span className="font-heading text-[0.875rem] font-semibold tabular-nums text-muted-foreground">
          {value}
          {suffix ?? ""}
        </span>
      </div>
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <motion.div
          initial={{ scaleX: 0 }}
          whileInView={{ scaleX: value / 100 }}
          viewport={viewportOnce}
          transition={{ duration: reduce ? 0 : 0.9, ease: EASE }}
          className="h-full w-full origin-left rounded-full bg-primary"
        />
      </div>
    </div>
  );
}

export function KeyValue({ rows }: { rows: { label: string; value: string }[] }) {
  return (
    <dl className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
      {rows.map((r) => (
        <div key={r.label} className="flex items-baseline justify-between gap-4 border-b border-border/60 pb-3">
          <dt className="text-[0.85rem] text-muted-foreground">{r.label}</dt>
          <dd className="text-right text-[0.9rem] font-medium text-foreground">{r.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function SeverityBadge({ value }: { value: string }) {
  const tone =
    value === "Alta"
      ? "border-destructive/40 text-destructive"
      : value === "Media"
        ? "border-accent/40 text-accent"
        : "border-primary/40 text-primary";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border bg-background px-2.5 py-1 text-[0.7rem] font-medium tracking-[0.08em] uppercase",
        tone,
      )}
    >
      {value}
    </span>
  );
}

export function MockNote() {
  return null;
}

export const euro = (n: number) => `€${n.toLocaleString("it-IT")}`;
