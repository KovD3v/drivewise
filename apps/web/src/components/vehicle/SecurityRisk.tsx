import { motion, useReducedMotion } from "framer-motion";
import { ShieldAlert, ShieldCheck, ShieldQuestion, MapPin } from "lucide-react";
import { EASE, viewportOnce } from "@/lib/motion";
import { Card } from "@/components/vehicle/primitives";
import { theftBandLabels } from "@/lib/report-sections";
import { theftReference, theftRegionsFor, type Vehicle } from "@/services/vehicleService";

/**
 * Security & Risk: mostra solo dati osservati (furti rilevati, tasso di ritrovamento).
 * Mai una probabilità calcolata: senza il circolante il rischio non è normalizzabile.
 */
export function SecurityRisk({ vehicle: v }: { vehicle: Vehicle }) {
  const reduce = useReducedMotion();
  const observed = v.theft_risk.observed_thefts_italy_2024;
  const recovery = v.theft_risk.recovery_rate_pct;
  const band = v.theft_risk.observed_volume_band;
  const regions = Object.entries(theftRegionsFor(v.vehicle_type)).slice(0, 5);
  const hasData = typeof observed === "number";

  return (
    <Card className="relative overflow-hidden">
      <p className="mb-4 text-xs text-muted-foreground">Demo: statistiche di esempio, servizio non ancora collegato.</p>
      <div
        aria-hidden
        className="pointer-events-none absolute -top-24 -right-16 size-56 rounded-full bg-accent/10 blur-3xl"
      />
      <div className="relative flex items-start gap-4">
        <span className="grid size-11 shrink-0 place-items-center rounded-2xl border border-border/70 bg-background">
          {hasData ? (
            <ShieldAlert className="size-5 text-accent" />
          ) : (
            <ShieldQuestion className="size-5 text-muted-foreground" />
          )}
        </span>
        <div className="min-w-0">
          <h3 className="font-heading text-[1.05rem] font-semibold">Sicurezza e furti</h3>
          <p className="mt-1 text-[0.85rem] text-muted-foreground">
            {hasData
              ? `Dati osservati in Italia nel ${v.theft_risk.data_year}. Nessuna probabilità stimata.`
              : "Non sono disponibili statistiche verificate per questo modello."}
          </p>
        </div>
      </div>

      {hasData ? (
        <div className="relative mt-6 grid gap-4 sm:grid-cols-3">
          <Metric
            value={observed.toLocaleString("it-IT")}
            label="Furti osservati"
            hint={v.theft_risk.source ?? undefined}
          />
          <Metric
            value={typeof recovery === "number" ? `${recovery}%` : "n.d."}
            label="Tasso di ritrovamento"
            hint={typeof recovery === "number" ? "Sui casi rilevati" : "Dato non presente"}
          />
          <Metric
            value={band ? (theftBandLabels[band] ?? band) : "n.d."}
            label="Fascia di volume"
            hint="Volume assoluto, non rischio"
          />
        </div>
      ) : (
        <p className="relative mt-6 rounded-2xl border border-dashed border-border/70 bg-background px-4 py-3 text-[0.85rem] text-muted-foreground">
          Assenza di dati non significa assenza di rischio: significa che non abbiamo osservazioni
          per questo modello e preferiamo non inventarle.
        </p>
      )}

      <div className="relative mt-6 border-t border-border/70 pt-5">
        <p className="flex items-center gap-2 text-[0.78rem] tracking-[0.12em] text-muted-foreground uppercase">
          <MapPin className="size-3.5" /> Aree con più furti
        </p>
        <ul className="mt-3 space-y-2">
          {regions.map(([region, count], i) => {
            const max = Math.max(...regions.map(([, c]) => c), 1);
            return (
              <li key={region} className="flex items-center gap-3">
                <span className="w-28 shrink-0 truncate text-[0.82rem] text-foreground">{region}</span>
                <span className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <motion.span
                    className="block h-full origin-left rounded-full bg-accent/70"
                    initial={{ scaleX: 0 }}
                    whileInView={{ scaleX: count / max }}
                    viewport={viewportOnce}
                    transition={{ duration: reduce ? 0 : 0.8, delay: i * 0.06, ease: EASE }}
                  />
                </span>
                <span className="w-16 shrink-0 text-right text-[0.78rem] tabular-nums text-muted-foreground">
                  {count.toLocaleString("it-IT")}
                </span>
              </li>
            );
          })}
        </ul>
        <p className="mt-4 flex items-start gap-2 text-[0.72rem] leading-relaxed text-muted-foreground">
          <ShieldCheck className="mt-0.5 size-3.5 shrink-0" />
          {theftReference.warning}
        </p>
      </div>
    </Card>
  );
}

function Metric({ value, label, hint }: { value: string; label: string; hint?: string | undefined }) {
  return (
    <div className="rounded-2xl border border-border/70 bg-background p-4">
      <p className="font-heading text-[1.5rem] leading-none font-bold tabular-nums">{value}</p>
      <p className="mt-2 text-[0.8rem] text-foreground">{label}</p>
      {hint && <p className="mt-1 text-[0.7rem] text-muted-foreground">{hint}</p>}
    </div>
  );
}
