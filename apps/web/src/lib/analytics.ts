/** Placeholder analytics layer. No provider is integrated on purpose. */
export type AnalyticsEvent =
  | "landing_start_cta_click"
  | "landing_decision_bar_submit"
  | "landing_example_click"
  | "app_start_view";

export function track(event: AnalyticsEvent, payload?: Record<string, unknown>) {
  if (typeof window === "undefined") return;
  // Intentionally a no-op placeholder: wire a provider here later.
  (window as unknown as { dataLayer?: unknown[] }).dataLayer?.push({ event, ...payload });
  if (import.meta.env.DEV) console.debug("[analytics]", event, payload ?? {});
}

export const INITIAL_QUERY_KEY = "drivewise_initial_query";

export function saveInitialQuery(text: string) {
  try {
    sessionStorage.setItem(INITIAL_QUERY_KEY, text);
  } catch {
    /* storage unavailable */
  }
}

export function takeInitialQuery(): string | null {
  try {
    const v = sessionStorage.getItem(INITIAL_QUERY_KEY);
    if (v) sessionStorage.removeItem(INITIAL_QUERY_KEY);
    return v && v.trim() ? v : null;
  } catch {
    return null;
  }
}
