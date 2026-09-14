import { createFileRoute, Link } from "@tanstack/react-router";
import { AppHeader } from "@/components/app/AppHeader";
import { getVehicleById } from "@/services/vehicleService";

const title = "Confronto veicoli — DriveWise";
const description = "Il confronto affiancato fra veicoli sarà disponibile a breve su DriveWise.";

export const Route = createFileRoute("/app/compare")({
  validateSearch: (search: Record<string, unknown>) => ({
    vehicle: typeof search['vehicle'] === "string" ? (search['vehicle'] as string) : undefined,
  }),
  loaderDeps: ({ search: { vehicle } }) => ({ vehicle }),
  loader: async ({ deps }) => ({
    vehicle: deps.vehicle ? await getVehicleById(deps.vehicle) : null,
  }),
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
      {error.message}
    </div>
  ),
  notFoundComponent: () => (
    <div className="p-10 text-center text-sm text-muted-foreground">Confronto non disponibile.</div>
  ),
});

function ComparePage() {
  const { vehicle: v } = Route.useLoaderData();

  return (
    <div className="min-h-screen bg-background">
      <AppHeader label="Confronto" maxWidth="max-w-[70rem]" />
      <main className="mx-auto w-full max-w-[46rem] px-6 py-24 text-center sm:px-8">
        <h1 className="font-heading text-[2rem] font-extrabold tracking-[-0.03em]">
          Confronto demo.
        </h1>
        <p className="mt-4 text-[0.95rem] text-muted-foreground">
          {v
            ? `${v.brand} ${v.model} è il primo veicolo selezionato. Il confronto è un’anteprima, non ancora un servizio attivo.`
            : "Seleziona un veicolo dalla sua scheda per iniziare un confronto."}
        </p>
        {v && (
          <Link
            to="/app/vehicle/$id"
            params={{ id: v.id }}
            className="mt-8 inline-flex h-12 items-center rounded-full bg-primary px-7 text-[0.95rem] font-medium text-primary-foreground transition-colors hover:bg-primary-hover"
          >
            Torna alla scheda
          </Link>
        )}
      </main>
    </div>
  );
}
