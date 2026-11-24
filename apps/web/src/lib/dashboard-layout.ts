import { useCallback, useEffect, useState } from "react";
import { FEATURES, type FeatureKey } from "@/lib/mydrivewise";

const KEY = "drivewise_me_layout_v1";

export type DashboardLayout = { order: FeatureKey[]; hidden: FeatureKey[] };

const ALL = FEATURES.map((f) => f.slug);

export const defaultLayout = (): DashboardLayout => ({ order: [...ALL], hidden: [] });

function normalize(raw: Partial<DashboardLayout> | null): DashboardLayout {
  if (!raw) return defaultLayout();
  const order = (raw.order ?? []).filter((s) => ALL.includes(s));
  const hidden = (raw.hidden ?? []).filter((s) => ALL.includes(s));
  for (const s of ALL) if (!order.includes(s)) order.push(s);
  return { order, hidden };
}

export function useDashboardLayout() {
  const [layout, setLayout] = useState<DashboardLayout>(defaultLayout);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) setLayout(normalize(JSON.parse(raw)));
    } catch {
      /* ignore */
    }
    setHydrated(true);
  }, []);

  const persist = useCallback((next: DashboardLayout) => {
    setLayout(next);
    try {
      localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      /* ignore */
    }
  }, []);

  return { layout, setLayout: persist, hydrated };
}
