import { Bar, Card } from "@/components/vehicle/primitives";
import { reliabilityMetrics } from "@/lib/report-sections";
import type { Vehicle } from "@/services/vehicleService";

/** Affidabilità e indici correlati: sempre letti da vehicle_dna. */
export function ReliabilityPanel({ vehicle }: { vehicle: Vehicle }) {
  const metrics = reliabilityMetrics(vehicle);
  if (!metrics.length) return null;
  return (
    <Card>
      <h3 className="font-heading text-[1.05rem] font-semibold">Affidabilità e qualità percepita</h3>
      <p className="mt-1 text-[0.85rem] text-muted-foreground">
        {vehicle.mockDetails || vehicle.mock ? "Demo: indici simulati, non valutazioni del veicolo." : "Indici del profilo tecnico DriveWise, su scala 0-100."}
      </p>
      <div className="mt-5 space-y-4">
        {metrics.map((m) => (
          <Bar key={String(m.key)} label={m.label} value={m.value} suffix="/100" />
        ))}
      </div>
    </Card>
  );
}
