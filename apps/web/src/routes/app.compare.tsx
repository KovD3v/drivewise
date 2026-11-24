import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { AppHeader } from "@/components/app/AppHeader";
import { Card, KeyValue } from "@/components/vehicle/primitives";
import { PriceLine } from "@/components/vehicle/PriceLine";
import { ListPricePanel, SourceCredits } from "@/components/vehicle/source-facts";
import { categoryLabel } from "@/lib/category-labels";
import { compareRows } from "@/lib/compare-rows";
import { typeLabel, vehicleName } from "@/lib/vehicle-format";
import { getVehicleById, getVehiclesByType, type Vehicle } from "@/services/vehicleService";

const title = "Confronto veicoli — DriveWise";
const description = "Due veicoli del catalogo DriveWise affiancati, con prezzo di listino, consumi e fonti.";

type CompareSearch = { vehicle?: string; with?: string };

export const Route = createFileRoute("/app/compare")({
  validateSearch: (search: Record<string, unknown>): CompareSearch => ({
    vehicle: typeof search["vehicle"] === "string" ? search["vehicle"] : undefined,
    with: typeof search["with"] === "string" ? search["with"] : undefined,
  }),
  loaderDeps: ({ search }) => ({ vehicle: search.vehicle, with: search.with }),
  loader: async ({ deps }) => {
    const first = deps.vehicle ? await getVehicleById(deps.vehicle) : null;
    const second = first && deps.with ? await getVehicleById(deps.with) : null;
    // Only vehicles of the same type are comparable: their facts share the same fields.
    const options = first ? (await getVehiclesByType(first.vehicle_type)).filter((v) => v.id !== first.id) : [];
    return { first, second: second?.vehicle_type === first?.vehicle_type ? second : null, options };
  },
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
  component: ComparePage,
  errorComponent: ({ error }) => (
    <div role="alert" className="p-10 text-center text-sm text-muted-foreground">
      {error instanceof Error ? error.message : "Confronto non disponibile."}
    </div>
  ),
  notFoundComponent: () => (
    <div className="p-10 text-center text-sm text-muted-foreground">Confronto non disponibile.</div>
  ),
});

function ComparePage() {
  const { first, second, options } = Route.useLoaderData();
  const navigate = useNavigate();

  if (!first)
    return (
      <div className="min-h-screen bg-background">
        <AppHeader label="Confronto" maxWidth="max-w-[70rem]" />
        <main className="mx-auto w-full max-w-[46rem] px-6 py-24 text-center sm:px-8">
          <h1 className="font-heading text-[2rem] font-extrabold tracking-[-0.03em]">Scegli un veicolo da confrontare.</h1>
          <p className="mt-4 text-[0.95rem] text-muted-foreground">
            Apri la scheda di un veicolo e scegli “Confronta”.
          </p>
          <Link
            to="/app/start"
            className="mt-8 inline-flex h-12 items-center rounded-full bg-primary px-7 text-[0.95rem] font-medium text-primary-foreground transition-colors hover:bg-primary-hover"
          >
            Vai alla Scelta Guidata
          </Link>
        </main>
      </div>
    );

  const shown = second ? [first, second] : [first];

  return (
    <div className="min-h-screen bg-background">
      <AppHeader label="Confronto" maxWidth="max-w-[70rem]" />
      <main className="mx-auto w-full max-w-[70rem] space-y-10 px-6 py-12 sm:px-8 lg:py-20">
        <header>
          <p className="text-[0.7rem] tracking-[0.2em] text-muted-foreground uppercase">{typeLabel[first.vehicle_type]}</p>
          <h1 className="font-heading mt-3 text-[2rem] leading-tight font-extrabold tracking-[-0.03em] sm:text-[2.6rem]">
            {second ? `${vehicleName(first)} e ${vehicleName(second)}` : `Confronta ${vehicleName(first)}`}
          </h1>
          <p className="mt-3 max-w-2xl text-[0.95rem] text-muted-foreground">
            Solo i dati del catalogo, con le loro fonti. Il prezzo di listino non è un’offerta di un venditore.
          </p>
          <label className="mt-6 flex max-w-md flex-col gap-2 text-[0.85rem] text-muted-foreground">
            Confronta con
            <select
              value={second?.id ?? ""}
              onChange={(e) =>
                void navigate({ to: "/app/compare", search: { vehicle: first.id, with: e.target.value || undefined } })
              }
              className="h-12 rounded-full border border-border/70 bg-card px-5 text-[0.95rem] text-foreground"
            >
              <option value="">Scegli un veicolo</option>
              {options.map((v) => (
                <option key={v.id} value={v.id}>
                  {vehicleName(v)}
                </option>
              ))}
            </select>
          </label>
        </header>

        <div className="grid gap-6 md:grid-cols-2">
          {shown.map((v) => (
            <CompareColumn key={v.id} vehicle={v} />
          ))}
        </div>
      </main>
    </div>
  );
}

function CompareColumn({ vehicle: v }: { vehicle: Vehicle }) {
  return (
    <section className="min-w-0 space-y-5">
      <Card>
        <p className="text-[0.7rem] tracking-[0.2em] text-muted-foreground uppercase">{categoryLabel(v.category)}</p>
        <h2 className="font-heading mt-2 text-[1.35rem] font-bold tracking-[-0.02em]">
          <Link to="/app/vehicle/$id" params={{ id: v.id }} className="underline-offset-4 hover:underline">
            {vehicleName(v)}
          </Link>
        </h2>
        <PriceLine vehicle={v} className="mt-1 text-[0.9rem] text-muted-foreground" />
        <div className="mt-6">
          <KeyValue rows={compareRows(v)} columns={1} />
        </div>
      </Card>
      {v.list_price && <ListPricePanel price={v.list_price} />}
      {v.credits.length > 0 && (
        <Card>
          <SourceCredits credits={v.credits} />
        </Card>
      )}
    </section>
  );
}
