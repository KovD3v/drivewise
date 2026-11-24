import { createFileRoute } from "@tanstack/react-router";
import { Header } from "@/components/landing/Header";
import { Hero } from "@/components/landing/Hero";
import { TrustSignals } from "@/components/landing/TrustSignals";
import { MyDriveWiseSection } from "@/components/landing/MyDriveWiseSection";
import { Demo } from "@/components/landing/Demo";
import { Difference } from "@/components/landing/Difference";
import { Faq } from "@/components/landing/Faq";
import { FinalCta } from "@/components/landing/FinalCta";
import { Footer } from "@/components/landing/Footer";
import { StoryRail } from "@/components/landing/StoryRail";

const title = "DriveWise — Auto, moto e scooter: la scelta giusta, spiegata";
const url = "https://drivewise-italia.com/";
const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://drivewise-italia.com/#organization",
      name: "DriveWise",
      url,
    },
    {
      "@type": "WebSite",
      "@id": "https://drivewise-italia.com/#website",
      name: "DriveWise",
      url,
      inLanguage: "it-IT",
      publisher: { "@id": "https://drivewise-italia.com/#organization" },
    },
  ],
};
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
      { property: "og:url", content: url },
      { property: "og:locale", content: "it_IT" },
      { property: "og:site_name", content: "DriveWise" },
      { property: "og:image", content: new URL("/drivewise-social.png", url).href },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:image", content: new URL("/drivewise-social.png", url).href },
      { name: "twitter:title", content: title },
      { name: "twitter:description", content: description },
    ],
    links: [{ rel: "canonical", href: url }],
    scripts: [{ type: "application/ld+json", children: JSON.stringify(jsonLd) }],
  }),
  component: Index,
});

function Index() {
  return (
    <div className="dw-home min-h-screen bg-background">
      <a
        href="#contenuto"
        className="sr-only z-[60] rounded-full bg-card text-sm font-medium shadow-lg focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:px-4 focus:py-2"
      >
        Salta al contenuto
      </a>
      <Header />
      <main id="contenuto" tabIndex={-1} className="outline-none">
        <Hero />
        <TrustSignals />
        <Demo />
        <MyDriveWiseSection />
        <Difference />
        <Faq />
        <FinalCta />
      </main>
      <Footer />
      <StoryRail />
    </div>
  );
}
