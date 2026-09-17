import {
  useEffect,
  useState,
  type ComponentPropsWithoutRef,
  type MouseEvent,
  type ReactNode,
} from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Link, useRouter, useRouterState, type LinkProps } from "@tanstack/react-router";
import { useReducedMotion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { startAppTransition } from "@/lib/app-transition";

export const ctaVariants = cva(
  "group inline-flex items-center justify-center gap-2 rounded-full font-medium transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] will-change-transform disabled:opacity-50 motion-safe:hover:scale-[1.02] motion-safe:active:scale-[0.98] [&_svg]:transition-transform [&_svg]:duration-300 motion-safe:hover:[&_svg]:translate-x-[3px]",
  {
    variants: {
      variant: {
        primary:
          "bg-primary text-primary-foreground shadow-[var(--shadow-soft)] hover:bg-primary-hover hover:shadow-[var(--shadow-lift)]",
        ghost:
          "border border-border bg-card text-foreground hover:border-foreground/25 hover:shadow-[var(--shadow-soft)]",
        quiet: "text-muted-foreground hover:text-foreground",
      },
      size: {
        sm: "h-10 px-4 text-sm",
        md: "h-12 px-6 text-[0.95rem]",
        lg: "h-14 px-8 text-base",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

type Props = ComponentPropsWithoutRef<"a"> &
  VariantProps<typeof ctaVariants> & { to?: LinkProps["to"] };

export function CtaButton({ className, variant, size, to, ...props }: Props) {
  const classes = cn(ctaVariants({ variant, size }), className);
  if (to) {
    const { children, onClick, ...rest } = props;
    void rest;
    return (
      <CtaLink to={to} className={classes} {...(onClick ? { onClick } : {})}>
        {children}
      </CtaLink>
    );
  }
  return <a className={classes} {...props} />;
}

/**
 * Link verso una route dell'app: precarica il chunk (hover/focus + al mount),
 * mostra uno spinner se la navigazione richiede tempo e avvia la transizione.
 *
 * REGOLA ARCHITETTURALE — la navigazione non viene MAI intercettata:
 * l'overlay è puramente decorativo e parte in parallelo, mentre <Link>
 * esegue la navigazione al primo click. Nessun preventDefault, nessun
 * setTimeout, nessun flag "pronto a navigare".
 */
function CtaLink({
  to,
  className,
  children,
  onClick,
}: {
  to: NonNullable<LinkProps["to"]>;
  className: string;
  children?: ReactNode;
  onClick?: (e: MouseEvent<HTMLAnchorElement>) => void;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const reduceMotion = useReducedMotion();
  const isLoading = useRouterState({ select: (s) => s.isLoading || s.isTransitioning });

  // Precarica il bundle della route subito: il primo click non deve mai attendere.
  useEffect(() => {
    void router.preloadRoute({ to }).catch(() => {});
  }, [router, to]);

  useEffect(() => {
    if (!busy || isLoading) return;
    const t = window.setTimeout(() => setBusy(false), 800);
    return () => window.clearTimeout(t);
  }, [busy, isLoading]);

  const handleClick = (e: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(e);
    if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;

    const isAppEntry = String(to).startsWith("/app");
    if (!isAppEntry || reduceMotion) return;

    // Solo effetto visivo: <Link> naviga comunque, subito, al primo click.
    setBusy(true);
    startAppTransition({ x: e.clientX, y: e.clientY });
  };

  return (
    <Link to={to} preload="intent" className={className} onClick={handleClick}>
      {busy && isLoading && <Loader2 className="size-4 animate-spin" aria-hidden />}
      {children}
    </Link>
  );
}