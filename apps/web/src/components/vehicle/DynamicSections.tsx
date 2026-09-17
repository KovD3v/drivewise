import { motion, useReducedMotion } from "framer-motion";
import {
  Backpack,
  Bike,
  Building2,
  Gauge,
  Luggage,
  Package,
  ParkingSquare,
  Ruler,
  ShieldAlert,
  Sofa,
  Users,
  Wallet,
  Warehouse,
  Weight,
  Wind,
  type LucideIcon,
} from "lucide-react";
import { EASE, viewportOnce } from "@/lib/motion";
import { Card } from "@/components/vehicle/primitives";
import type { ReportSection } from "@/lib/report-sections";

const icons: Record<string, LucideIcon> = {
  boot: Luggage,
  family: Users,
  garage: Warehouse,
  comfort: Sofa,
  cost: Wallet,
  tco: Wallet,
  seat: Ruler,
  weight: Weight,
  experience: Bike,
  passenger: Users,
  wind: Wind,
  luggage: Backpack,
  underseat: Package,
  agility: Building2,
  ringroad: Gauge,
  parking: ParkingSquare,
  theft: ShieldAlert,
};

/** Card generate dinamicamente: compaiono solo se il dato esiste nel dataset. */
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
              {typeof s.score === "number" && (
                <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <motion.div
                    className="h-full origin-left rounded-full bg-primary"
                    initial={{ scaleX: 0 }}
                    whileInView={{ scaleX: s.score / 100 }}
                    viewport={viewportOnce}
                    transition={{ duration: reduce ? 0 : 0.9, ease: EASE }}
                    style={{ width: "100%" }}
                  />
                </div>
              )}
            </Card>
          </motion.div>
        );
      })}
    </div>
  );
}
