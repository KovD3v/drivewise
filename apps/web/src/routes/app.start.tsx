import { GuidedCarFlow } from "@/components/app/GuidedCarFlow";
import { useEffect, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { MobilePanel } from "@/components/app/MobilePanel";
import { AppHeader } from "@/components/app/AppHeader";
import { DecisionMessage } from "@/components/app/DecisionMessage";
import { DecisionProfilePanel } from "@/components/app/DecisionProfilePanel";
import { StepStage } from "@/components/app/StepStage";
import { UserMessage } from "@/components/app/UserMessage";
import { VehicleTypeChoice } from "@/components/app/VehicleTypeChoice";
import { takeInitialQuery, track } from "@/lib/analytics";
import { clearState } from "@/lib/decision-state";
import { EASE } from "@/lib/motion";
import { vehicleTypeFromText } from "@/lib/wizard-input";
import type { VehicleTypeKey } from "@/services/vehicleService";

const title = "DriveWise — Costruisci la tua decisione";
const description =
  "Costruisci un profilo decisionale personale e confronta veicoli reali, pertinenti alle tue esigenze.";

export const Route = createFileRoute("/app/start")({
  validateSearch: (search: Record<string, unknown>): { q?: string } =>
    typeof search["q"] === "string" ? { q: search["q"] } : {},
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: AppStart,
});

const typeOptions: { value: VehicleTypeKey; label: string; kind: VehicleTypeKey }[] = [
  { value: "car", label: "Auto", kind: "car" },
  { value: "motorcycle", label: "Moto", kind: "motorcycle" },
  { value: "scooter", label: "Scooter", kind: "scooter" },
];

function AppStart() {
  const navigate = useNavigate();
  const { q: query } = Route.useSearch();
  const [vehicleType, setVehicleType] = useState<VehicleTypeKey | null>(null);
  const [initialQuery, setInitialQuery] = useState("");

  // Advisor v3 ranks cars only: motorcycles and scooters open the catalogue, without a score.
  const choose = (type: VehicleTypeKey) => {
    if (type === "car") setVehicleType("car");
    else void navigate({ to: "/app/catalog", search: { type } });
  };

  useEffect(() => {
    track("app_start_view");
    const text = query?.trim() || takeInitialQuery() || "";
    setInitialQuery(text);
    clearState();
    const inferred = vehicleTypeFromText(text);
    if (inferred) choose(inferred);
  }, [query]);

  if (vehicleType === "car") return <GuidedCarFlow initialQuery={initialQuery} />;

  return (
    <div className="min-h-screen bg-background">
      <AppHeader label="Scelta Guidata" maxWidth="max-w-[86rem]" />
      <main className="mx-auto w-full max-w-[86rem] px-6 py-10 sm:px-8 lg:py-16">
        <div className="grid gap-10 lg:grid-cols-[7fr_3fr] lg:gap-14">
          <div className="min-w-0">
            <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: EASE }}>
              <h1 className="font-heading text-[2.25rem] leading-[1.05] font-extrabold text-foreground sm:text-[3rem]">
                Trova il veicolo perfetto.
              </h1>
              <p className="mt-5 max-w-2xl text-[1.02rem] leading-relaxed text-muted-foreground">
                Le domande cambiano in base a ciò che stai cercando: ti chiediamo solo ciò che i
                dati reali dei veicoli permettono di valutare.
              </p>
            </motion.div>

            <div className="mt-9 space-y-8">
              {initialQuery && <UserMessage>Hai scritto: {initialQuery}</UserMessage>}
              <StepStage themeId="facts" active>
                <DecisionMessage>
                  <h2 tabIndex={-1}>Cosa stai cercando?</h2>
                  <p className="text-muted-foreground">
                    Auto: ti guidiamo fino a un consiglio. Moto e scooter: ti mostriamo il catalogo, senza punteggio.
                  </p>
                </DecisionMessage>
                <div className="pl-[3.125rem]">
                  <VehicleTypeChoice options={typeOptions} onSelect={(value) => choose(value as VehicleTypeKey)} />
                </div>
              </StepStage>
            </div>
          </div>

          <motion.aside
            className="min-w-0"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2, ease: EASE }}
          >
            <MobilePanel>
              <DecisionProfilePanel
                known={[]}
                missing={[{ id: "type", label: "Tipo di veicolo" }]}
                completion={0}
                confidence={null}
                ranking={[]}
              />
            </MobilePanel>
          </motion.aside>
        </div>
      </main>
    </div>
  );
}
