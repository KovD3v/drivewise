/**
 * Site-wide notice for a build that serves the synthetic demo catalogue.
 * One public build variable decides it: VITE_SYNTHETIC_DATA=true. The API exposes
 * no source list before a vehicle loads, so the notice cannot come from the data.
 */
export function isSyntheticDemo(env: Record<string, unknown> = import.meta.env): boolean {
  return env["VITE_SYNTHETIC_DATA"] === "true";
}

export function DemoNotice({ show = isSyntheticDemo() }: { show?: boolean }) {
  if (!show) return null;
  return (
    <p
      role="note"
      className="border-b border-border/70 bg-muted px-6 py-2 text-center text-[0.8rem] text-muted-foreground"
    >
      Versione dimostrativa: marche, modelli, prezzi e consumi sono inventati e non descrivono veicoli reali.
    </p>
  );
}
