import { createFileRoute } from "@tanstack/react-router";
import { LegalPage } from "@/components/legal/LegalLayout";
import { ContactForm } from "@/components/legal/ContactForm";

const title = "Contatti | DriveWise";
const description =
  "Scrivi al team DriveWise per domande, partnership, stampa o richieste privacy. Rispondiamo entro 48 ore lavorative.";

export const Route = createFileRoute("/contact")({
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
  return (
    <LegalPage
      badge="Contatti"
      title="Hai una domanda? Parliamone."
      subtitle="Rispondiamo sempre, entro 48 ore lavorative."
    >
      <ContactForm email="hello@drivewise-italia.com" />
    </LegalPage>
  );
}
