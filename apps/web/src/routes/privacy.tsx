import { createFileRoute, Link } from "@tanstack/react-router";
import { LegalPage, type LegalSection } from "@/components/legal/LegalLayout";

const title = "Privacy | DriveWise";
const description =
  "Come DriveWise raccoglie, usa e protegge i dati della Scelta Guidata: trasparenza su IA, cookie e diritti GDPR.";

export const Route = createFileRoute("/privacy")({
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
  component: PrivacyPage,
});

const contatti = (
  <Link className="text-foreground underline underline-offset-4" to="/contact">
    Contatti
  </Link>
);

const sections: LegalSection[] = [
  {
    id: "titolare",
    title: "Titolare del trattamento",
    body: (
      <p>
        DriveWise tratta i dati che condividi durante la Scelta Guidata al solo scopo di costruire il
        tuo profilo decisionale e generare una raccomandazione. Per richieste relative ai tuoi dati
        puoi scriverci in qualsiasi momento tramite la pagina {contatti}.
      </p>
    ),
  },
  {
    id: "raccolta",
    title: "Cosa raccogliamo",
    body: (
      <p>
        Le informazioni che scrivi nella conversazione (es. budget, utilizzo previsto, priorità), le
        misure del tuo garage se le fornisci, e dati tecnici minimi di navigazione. Non raccogliamo
        dati biometrici, finanziari o sensibili, e non chiediamo mai documenti d'identità o dati di
        pagamento.
      </p>
    ),
  },
  {
    id: "utilizzo",
    title: "Come li usiamo",
    body: (
      <p>
        Esclusivamente per calcolare il tuo Decision Score e le raccomandazioni personalizzate. Non
        li vendiamo, non li condividiamo con concessionari, assicurazioni o inserzionisti, e non li
        usiamo per pubblicità di terzi.
      </p>
    ),
  },
  {
    id: "ia",
    title: "Intelligenza Artificiale e trasparenza",
    body: (
      <p>
        DriveWise utilizza un sistema di intelligenza artificiale per analizzare le tue richieste e
        generare suggerimenti. In conformità al Regolamento UE sull'Intelligenza Artificiale (AI Act,
        Regolamento UE 2024/1689), ti informiamo esplicitamente che le risposte, i punteggi e le
        raccomandazioni che ricevi sono generati da un sistema automatizzato e non da un consulente
        umano. Il sistema è progettato per supporto decisionale, non per sostituire una valutazione
        professionale o legale sull'acquisto di un veicolo.
      </p>
    ),
  },
  {
    id: "conservazione",
    title: "Conservazione dei dati",
    body: (
      <p>
        Conserviamo i dati della tua sessione solo per il tempo necessario a fornirti il servizio,
        salvo tu scelga di salvare il tuo profilo per usi futuri.
      </p>
    ),
  },
  {
    id: "diritti",
    title: "I tuoi diritti",
    body: (
      <p>
        Puoi richiedere accesso, correzione, cancellazione o portabilità dei tuoi dati in qualsiasi
        momento, scrivendoci dalla pagina {contatti}. Rispondiamo entro 30 giorni.
      </p>
    ),
  },
  {
    id: "cookie",
    title: "Cookie",
    body: (
      <p>
        Usiamo solo cookie tecnici necessari al funzionamento del sito; nessun cookie di profilazione
        pubblicitaria.
      </p>
    ),
  },
  {
    id: "modifiche",
    title: "Modifiche",
    body: (
      <p>
        Aggiorniamo questa pagina quando cambia il modo in cui trattiamo i dati; la data di ultimo
        aggiornamento è sempre visibile in fondo alla pagina.
      </p>
    ),
  },
];

function PrivacyPage() {
  return (
    <LegalPage
      badge="Privacy"
      title="La tua privacy, spiegata come tutto il resto."
      subtitle="Nessun dato nascosto, nessuna sorpresa."
      sections={sections}
      updatedAt="12 agosto 2026"
    />
  );
}
