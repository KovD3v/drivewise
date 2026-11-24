import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Section({
  id,
  children,
  className,
  surface = false,
}: {
  id?: string;
  children: ReactNode;
  className?: string;
  surface?: boolean;
}) {
  return (
    <section
      id={id}
      className={cn(
        "scroll-mt-28 px-6 py-24 sm:px-8 md:py-32 lg:py-40",
        surface && "bg-card",
        className,
      )}
    >
      <div className="mx-auto w-full max-w-6xl">{children}</div>
    </section>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border border-border bg-card px-3.5 py-1.5 text-xs font-medium tracking-[0.14em] text-muted-foreground uppercase">
      {children}
    </span>
  );
}