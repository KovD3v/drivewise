import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { AppHeader } from "@/components/app/AppHeader";
import { VSection } from "@/components/vehicle/primitives";
import { categoryLabel } from "@/lib/category-labels";
import { fuelLabel, vehicleName } from "@/lib/vehicle-format";
import { getVehiclesByType } from "@/services/vehicleService";

type TwoWheelType = "motorcycle" | "scooter";

const titles: Record<TwoWheelType, string> = { motorcycle: "Moto", scooter: "Scooter" };

export const Route = createFileRoute("/app/catalog")({
  validateSearch: (search: Record<string, unknown>): { type: TwoWheelType } => ({
    type: search["type"] === "scooter" ? "scooter" : "motorcycle",
  }),
  loaderDeps: ({ search: { type } }) => ({ type }),
  loader: async ({ deps }) => ({ vehicles: await getVehiclesByType(deps.type) }),
  head: () => ({
    meta: [
      { title: "Catalogo moto e scooter | DriveWise" },
      { name: "description", content: "Moto e scooter del catalogo DriveWise, con i dati e le fonti restituiti dall'API." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: CatalogPage,
  errorComponent: CatalogUnavailable,
});

// TanStack splits each route slot into its own chunk; a slot function must not be referenced elsewhere.
function CatalogUnavailable() {
  return (
    <div className="min-h-screen bg-background">
      <AppHeader label="Catalogo" />
      <main className="mx-auto w-full max-w-[46rem] px-6 py-24 text-center sm:px-8">
        <h1 className="font-heading text-[2rem] font-extrabold tracking-[-0.03em]">Catalogo non disponibile.</h1>
        <p role="alert" className="mt-4 text-[0.95rem] text-muted-foreground">Il catalogo non risponde. Riprova tra poco.</p>
      </main>
    </div>
  );
}

function CatalogPage() {
  const { type } = Route.useSearch();
  const { vehicles } = Route.useLoaderData();
  const other: TwoWheelType = type === "motorcycle" ? "scooter" : "motorcycle";

  return (
    <div className="min-h-screen bg-background">
      <AppHeader label="Catalogo" maxWidth="max-w-[70rem]" />
      <main className="mx-auto w-full max-w-[70rem] space-y-10 px-6 py-12 sm:px-8 lg:py-20">
        <header>
          <p className="text-[0.7rem] tracking-[0.2em] text-muted-foreground uppercase">Catalogo DriveWise</p>
          <h1 className="font-heading mt-3 text-[2.25rem] leading-[1.05] font-extrabold sm:text-[3rem]">{titles[type]}</h1>
          <p className="mt-5 max-w-2xl text-[1.02rem] leading-relaxed text-muted-foreground">
            Il motore decisionale valuta solo le auto. Per moto e scooter mostriamo il catalogo, senza punteggio:
            apri una scheda per vedere i dati e le loro fonti.
          </p>
          <nav className="mt-6 flex flex-wrap gap-2" aria-label="Tipo di veicolo">
            <span aria-current="page" className="rounded-full border border-primary/35 bg-primary/10 px-4 py-2 text-[0.85rem]">
              {titles[type]}
            </span>
            <Link
              to="/app/catalog"
              search={{ type: other }}
              className="rounded-full border border-border/70 bg-card px-4 py-2 text-[0.85rem] text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
            >
              {titles[other]}
            </Link>
          </nav>
        </header>

        <VSection title={`${vehicles.length} modelli`}>
          {vehicles.length === 0 ? (
            <p className="text-sm text-muted-foreground">Il catalogo non contiene ancora veicoli di questo tipo.</p>
          ) : (
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {vehicles.map((v) => (
                <li key={v.id}>
                  <Link
                    to="/app/vehicle/$id"
                    params={{ id: v.id }}
                    className="flex h-full min-h-11 items-center justify-between gap-4 rounded-2xl border border-border/70 bg-card p-4 transition-colors hover:border-primary/40"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-[0.95rem] font-medium">{vehicleName(v)}</span>
                      <span className="mt-1 block truncate text-[0.8rem] text-muted-foreground">
                        {categoryLabel(v.category)}
                        {v.powertrain.fuel ? ` · ${fuelLabel(v.powertrain.fuel)}` : ""}
                      </span>
                    </span>
                    <ArrowRight className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </VSection>
      </main>
    </div>
  );
}
