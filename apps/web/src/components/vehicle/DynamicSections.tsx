import { motion, useReducedMotion } from "framer-motion";
import {
  Fuel,
  Gauge,
  Luggage,
  Package,
  Ruler,
  Users,
  Warehouse,
  Weight,
  type LucideIcon,
} from "lucide-react";
import { EASE, viewportOnce } from "@/lib/motion";
import { Card } from "@/components/vehicle/primitives";
import type { ReportSection } from "@/lib/report-sections";

const icons: Record<string, LucideIcon> = {
  boot: Luggage,
  family: Users,
  garage: Warehouse,
  cost: Fuel,
  seat: Ruler,
  weight: Weight,
  underseat: Package,
  tank: Fuel,
};

/** Card generate dinamicamente: compaiono solo se l'API restituisce il dato. */
export function DynamicSections({ sections }: { sections: ReportSection[] }) {
  const reduce = useReducedMotion();
  if (!sections.length) return null;
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {sections.map((s, i) => {
        const Icon = icons[s.icon] ?? Gauge;
        return (
          <motion.div
            key={s.id}
            initial={reduce ? { opacity: 1 } : { opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={viewportOnce}
            transition={{ duration: 0.5, delay: i * 0.05, ease: EASE }}
          >
            <Card className="h-full p-5">
              <div className="flex items-center gap-3">
                <span className="grid size-9 shrink-0 place-items-center rounded-xl border border-border/70 bg-background">
                  <Icon className="size-4 text-foreground" />
                </span>
                <p className="text-[0.78rem] tracking-[0.1em] text-muted-foreground uppercase">
                  {s.label}
                </p>
              </div>
              <p className="font-heading mt-4 text-[1.35rem] leading-tight font-bold">{s.value}</p>
              {s.detail && <p className="mt-2 text-[0.8rem] text-muted-foreground">{s.detail}</p>}
            </Card>
          </motion.div>
        );
      })}
    </div>
  );
}
