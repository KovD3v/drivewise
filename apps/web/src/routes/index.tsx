import { createFileRoute } from "@tanstack/react-router";
import { Header } from "@/components/landing/Header";
import { Hero } from "@/components/landing/Hero";
import { TrustSignals } from "@/components/landing/TrustSignals";
import { WhyDriveWise } from "@/components/landing/WhyDriveWise";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { Demo } from "@/components/landing/Demo";
import { Difference } from "@/components/landing/Difference";
import { Faq } from "@/components/landing/Faq";
import { FinalCta } from "@/components/landing/FinalCta";
import { Footer } from "@/components/landing/Footer";
import { ScrollWayfinding } from "@/components/nav/ScrollWayfinding";

const title = "DriveWise — Trova il veicolo perfetto";
const description =
  "DriveWise analizza dati, costi, affidabilità e caratteristiche reali per aiutarti a scegliere auto, moto o scooter con una decisione motivata.";

export const Route = createFileRoute("/")({
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
  component: Index,
});

function Index() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main>
        <Hero />
        <TrustSignals />
        <WhyDriveWise />
        <HowItWorks />
        <Demo />
        <Difference />
        <Faq />
        <FinalCta />
      </main>
      <Footer />
      <ScrollWayfinding />
    </div>
  );
}
