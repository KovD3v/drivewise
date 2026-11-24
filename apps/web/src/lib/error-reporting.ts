/**
 * Placeholder client-side error reporting. No provider is integrated on
 * purpose — wire Sentry, Bugsnag, or similar here when one is chosen.
 */
export function reportError(error: unknown, context: Record<string, unknown> = {}) {
  if (typeof window === "undefined") return;
  console.error("[error]", error, {
    route: window.location.pathname,
    ...context,
  });
}
