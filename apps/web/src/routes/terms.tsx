import { createFileRoute, Link } from "@tanstack/react-router";
import { LegalPage, type LegalSection } from "@/components/legal/LegalLayout";

const title = "Termini | DriveWise";
const description =
  "Le regole d'uso di DriveWise: natura dei suggerimenti generati da IA, limiti di responsabilità e legge applicabile.";

export const Route = createFileRoute("/terms")({
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
  component: TermsPage,
});

const sections: LegalSection[] = [
  {
    id: "cos-e",
    title: "Cos'è DriveWise",
    body: (
      <p>
        DriveWise è uno strumento di decision intelligence che aiuta a scegliere un veicolo (auto,
        moto, scooter) in base alle tue esigenze reali. Non vendiamo veicoli, non siamo un
        concessionario e non riceviamo commissioni per suggerirti un modello piuttosto che un altro.
      </p>
    ),
  },
  {
    id: "suggerimenti",
    title: "Natura dei suggerimenti",
    body: (
      <p>
        Le raccomandazioni sono generate da un sistema di intelligenza artificiale sulla base delle
        informazioni che fornisci e di dati pubblici disponibili su costi, affidabilità e
        caratteristiche dei veicoli. Non costituiscono consulenza professionale, legale o
        finanziaria, e vanno sempre verificate prima di un acquisto (es. presso il concessionario o
        con un meccanico di fiducia).
      </p>
    ),
  },
  {
    id: "trasparenza-ia",
    title: "Trasparenza sull'IA",
    body: (
      <p>
        Ai sensi dell'AI Act (Regolamento UE 2024/1689), dichiariamo che stai interagendo con un
        sistema automatizzato. Puoi sempre richiedere di parlare con un essere umano del nostro team
        scrivendo in{" "}
        <Link className="text-foreground underline underline-offset-4" to="/contact">
          Contatti
        </Link>
        .
      </p>
    ),
  },
  {
    id: "responsabilita",
    title: "Limiti di responsabilità",
    body: (
      <p>
        Facciamo del nostro meglio per garantire dati accurati e aggiornati, ma non possiamo
        garantire che ogni informazione (prezzi, disponibilità, specifiche) sia sempre precisa al
        100%. L'utente resta responsabile della decisione finale d'acquisto.
      </p>
    ),
  },
  {
    id: "proprieta",
    title: "Proprietà intellettuale",
    body: (
      <p>
        Contenuti, design e algoritmi di DriveWise sono di proprietà di DriveWise e non possono
        essere copiati o ridistribuiti senza autorizzazione.
      </p>
    ),
  },
  {
    id: "modifiche",
    title: "Modifiche al servizio",
    body: (
      <p>
        Possiamo aggiornare funzionalità o questi termini nel tempo; ti avviseremo dei cambiamenti
        sostanziali.
      </p>
    ),
  },
  {
    id: "legge",
    title: "Legge applicabile",
    body: <p>Questi termini sono regolati dalla legge italiana ed europea.</p>,
  },
];

function TermsPage() {
  return (
    <LegalPage
      badge="Termini"
      title="Le regole del gioco, in breve."
      subtitle="Cosa fa DriveWise, cosa non fa, e cosa resta nelle tue mani."
      sections={sections}
      updatedAt="12 agosto 2026"
    />
  );
}
