import { AnimatePresence, motion } from "framer-motion";
import { EASE } from "@/lib/motion";
import { VehiclePreviewCard } from "./VehiclePreviewCard";
import type { PreviewVehicle } from "@/lib/decision-engine";

export function PreviewRanking({ ranking }: { ranking: PreviewVehicle[] }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: EASE }}
      className="space-y-3"
    >
      <div>
        <h3 className="font-heading text-[0.95rem] font-semibold text-foreground">
          Prime valutazioni
        </h3>
        <p className="mt-1 text-[0.78rem] leading-relaxed text-muted-foreground">
          Cambieranno mentre ti conosciamo meglio.
        </p>
      </div>
      <ul className="space-y-3">
        <AnimatePresence mode="popLayout" initial={false}>
          {ranking.map((v, i) => (
            <VehiclePreviewCard key={v.id} vehicle={v} index={i} />
          ))}
        </AnimatePresence>
      </ul>
    </motion.div>
  );
}