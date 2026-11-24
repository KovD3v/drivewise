import { createFileRoute } from "@tanstack/react-router";
import { Header } from "@/components/landing/Header";
import { Footer } from "@/components/landing/Footer";
import { ContactForm } from "@/components/legal/ContactForm";
import { safeContactSource } from "@/lib/contact-intelligence";

const title = "Contatti | DriveWise";
const description =
  "Scrivi al team DriveWise per domande, partnership, stampa o richieste privacy. Rispondiamo entro 48 ore lavorative.";

export const Route = createFileRoute("/contact")({
  validateSearch: (search: Record<string, unknown>): { from?: string; analysis?: string } => {
    const from = safeContactSource(search['from']);
    const analysis = typeof search['analysis'] === "string" && /^[0-9a-f-]{36}$/i.test(search['analysis']) ? search['analysis'] : "";
    return { ...(from ? { from } : {}), ...(analysis ? { analysis } : {}) };
  },
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ContactPage,
});

function ContactPage() {
  const { from, analysis } = Route.useSearch();
  return (
    <div className="min-h-screen bg-background">
      <Header homeNavigation />
      <main className="mx-auto max-w-6xl px-6 pt-28 pb-16 sm:px-8 sm:pt-32">
      <ContactForm email="hello@drivewise-italia.com" from={from ?? ""} analysisId={analysis ?? ""} />
      </main>
      <Footer />
    </div>
  );
}
