import { useEffect, type MouseEvent, type ReactNode } from "react";
import { Link, useRouter, type LinkProps } from "@tanstack/react-router";
import { useReducedMotion } from "framer-motion";
import { startAppTransition } from "@/lib/app-transition";

/**
 * Link verso una route dell'app con transizione di materializzazione a particelle.
 * Precarica la route al mount e non intercetta mai il click: l'overlay parte
 * in parallelo mentre <Link> naviga immediatamente (regola architetturale).
 */
export function AppTransitionLink({
  to,
  params,
  className,
  steps,
  ariaLabel,
  children,
  onNavigate,
}: {
  to: NonNullable<LinkProps["to"]>;
  params?: Record<string, string>;
  className?: string;
  steps?: string[];
  ariaLabel?: string;
  children?: ReactNode;
  onNavigate?: () => void;
}) {
  const router = useRouter();
  const reduce = useReducedMotion();

  useEffect(() => {
    void router.preloadRoute({ to, ...(params ? { params } : {}) } as never).catch(() => {});
  }, [router, to, params]);

  const handleClick = (e: MouseEvent<HTMLAnchorElement>) => {
    if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    onNavigate?.();
    if (reduce) return;
    startAppTransition({ x: e.clientX, y: e.clientY }, steps);
  };

  return (
    <Link
      to={to}
      {...(params ? ({ params } as never) : {})}
      preload="intent"
      className={className}
      {...(ariaLabel ? { "aria-label": ariaLabel } : {})}
      onClick={handleClick}
    >
      {children}
    </Link>
  );
}