export type FeatureKey =
  | "garage"
  | "decision-history"
  | "wishlist"
  | "compare-later"
  | "cost-tracker"
  | "smart-maintenance"
  | "vehicle-health"
  | "document-wallet"
  | "ai-advisor"
  | "family-garage"
  | "finance"
  | "insurance-center"
  | "community"
  | "value-prediction"
  | "upgrade-advisor"
  | "smart-garage"
  | "insights"
  | "achievement";

export type Feature = {
  slug: FeatureKey;
  title: string;
  short: string;
  long: string;
  icon: string;
  benefits: string[];
  hero?: boolean;
  preview?:
    | "bars"
    | "timeline"
    | "vs"
    | "typewriter"
    | "line"
    | "badges"
    | "stats"
    | "bell"
    | "smart"
    | "maintenance"
    | "health"
    | "docs"
    | "wishlist";
};

export const FEATURES: Feature[] = [
  {
    slug: "garage",
    title: "My Garage",
    short: "Gestisci tutti i tuoi veicoli in un unico posto.",
    long: "Auto possedute, moto, scooter, cronologia, chilometri, bollo, assicurazione, revisione, tagliandi, pneumatici e valore usato: tutto il tuo parco veicoli in una sola vista, sempre aggiornata.",
    icon: "car",
    benefits: [
      "Tutti i veicoli in una vista unica",
      "Scadenze di bollo, assicurazione e revisione sempre sotto controllo",
      "Storico chilometri, tagliandi e pneumatici",
      "Valore usato stimato e aggiornato nel tempo",
    ],
  },
  {
    slug: "decision-history",
    title: "Decision History",
    short: "La cronologia di tutte le decisioni effettuate.",
    long: "Ogni analisi che fai con DriveWise resta consultabile e confrontabile nel tempo, in una timeline verticale che racconta come sono cambiate le tue esigenze.",
    icon: "history",
    preview: "timeline",
    benefits: [
      "Timeline verticale di ogni analisi",
      "Confronto fra decisioni passate",
      "Motivazioni sempre riconsultabili",
      "Esportazione del Decision Report",
    ],
  },
  {
    slug: "wishlist",
    title: "Wishlist",
    short: "Salva i veicoli preferiti e ricevi aggiornamenti.",
    long: "Metti da parte i veicoli che ti interessano e lascia che DriveWise ti avvisi su cambio prezzo, restyling, nuovi richiami, recensioni e miglioramenti del Decision Score.",
    icon: "bell",
    preview: "wishlist",
    benefits: [
      "Notifiche su cambio prezzo e restyling",
      "Avvisi su nuovi richiami ufficiali",
      "Nuove recensioni e affidabilità",
      "Decision Score aggiornato nel tempo",
    ],
  },
  {
    slug: "compare-later",
    title: "Compare Later",
    short: "Confronta in qualsiasi momento i veicoli salvati.",
    long: "Metti a confronto i veicoli della tua wishlist con lo stesso rigore del Decision Engine: costi, spazio, affidabilità e compatibilità con il tuo profilo.",
    icon: "compare",
    preview: "vs",
    benefits: [
      "Confronto fino a tre veicoli",
      "Differenze evidenziate, non solo elencate",
      "Costo reale a 1, 3 e 5 anni",
      "Verdetto sintetico e spiegato",
    ],
  },
  {
    slug: "cost-tracker",
    title: "Cost Tracker",
    short: "Tutti i costi del tuo veicolo, in chiaro.",
    long: "Carburante, assicurazione, bollo, tagliandi, gomme e svalutazione: DriveWise raccoglie tutto e ti mostra il costo totale annuale, senza sorprese.",
    icon: "wallet",
    preview: "bars",
    benefits: [
      "Costo totale annuale calcolato",
      "Suddivisione per categoria di spesa",
      "Confronto con la media della categoria",
      "Proiezione dei costi futuri",
    ],
  },
  {
    slug: "smart-maintenance",
    title: "Smart Maintenance",
    short: "Promemoria automatici per ogni scadenza.",
    long: "Tagliandi, olio, gomme, cinghia, pastiglie, revisione e scadenze amministrative: ricevi il promemoria giusto al momento giusto, calcolato sui tuoi chilometri reali.",
    icon: "wrench",
    preview: "maintenance",
    benefits: [
      "Promemoria basati su km reali",
      "Checklist per ogni intervento",
      "Storico manutenzione completo",
      "Stima del costo prima di prenotare",
    ],
  },
  {
    slug: "vehicle-health",
    title: "Vehicle Health",
    short: "Il tuo veicolo connesso, in tempo reale.",
    long: "Con la futura connessione API/OBD, DriveWise legge stato batteria, errori, autonomia, usura e diagnostica, traducendoli in linguaggio comprensibile.",
    icon: "pulse",
    preview: "health",
    benefits: [
      "Stato batteria e autonomia reale",
      "Errori diagnostici tradotti in italiano",
      "Usura di freni e pneumatici stimata",
      "Avvisi preventivi prima del guasto",
    ],
  },
  {
    slug: "document-wallet",
    title: "Document Wallet",
    short: "Tutti i documenti del veicolo, sempre con te.",
    long: "Libretto, assicurazione, bollo, garanzia, fatture, contratti e revisioni in un archivio ordinato e ricercabile, disponibile quando serve davvero.",
    icon: "folder",
    preview: "docs",
    benefits: [
      "Archivio ordinato e ricercabile",
      "Scadenze collegate ai documenti",
      "Accesso rapido anche offline",
      "Condivisione sicura in caso di vendita",
    ],
  },
  {
    slug: "ai-advisor",
    title: "AI Advisor",
    short: "Fai una domanda, ricevi una decisione spiegata.",
    long: "Un consulente che conosce il tuo profilo, il tuo veicolo e i tuoi costi, e risponde con numeri e motivazioni, non con opinioni.",
    icon: "spark",
    preview: "typewriter",
    benefits: [
      "Risposte basate sui tuoi dati reali",
      "Ogni consiglio è spiegato",
      "Scenari alternativi a confronto",
      "Nessuna pubblicità, nessun consiglio interessato",
    ],
  },
  {
    slug: "family-garage",
    title: "Family Garage",
    short: "Più veicoli, più persone, un solo posto.",
    long: "Gestisci i veicoli della famiglia, le auto aziendali, le moto e gli scooter, con profili e scadenze separati ma una visione d'insieme.",
    icon: "users",
    benefits: [
      "Profili separati per ogni persona",
      "Scadenze condivise e notifiche mirate",
      "Costo complessivo della famiglia",
      "Suggerimenti sull'uso ottimale dei veicoli",
    ],
  },
  {
    slug: "finance",
    title: "Finance",
    short: "Prestiti, leasing, noleggio e calcolo rata.",
    long: "Capisci quale formula conviene davvero al tuo utilizzo, con il costo totale reale e non solo la rata mensile in vetrina.",
    icon: "euro",
    benefits: [
      "Confronto acquisto, leasing e noleggio",
      "Calcolo della rata e del costo totale",
      "Impatto sul tuo budget mensile",
      "Simulazioni salvate nel profilo",
    ],
  },
  {
    slug: "insurance-center",
    title: "Insurance Center",
    short: "Confronta RC, furto, incendio e kasko.",
    long: "Le coperture spiegate senza gergo, confrontate sul tuo profilo di guida e sul valore reale del veicolo.",
    icon: "shield",
    benefits: [
      "Confronto trasparente delle coperture",
      "Consigli sulla franchigia giusta",
      "Promemoria di rinnovo",
      "Stima del risparmio annuale",
    ],
  },
  {
    slug: "community",
    title: "Community",
    short: "Recensioni, esperienze, guide e discussioni.",
    long: "L'esperienza reale di chi guida quel veicolo ogni giorno, filtrata e organizzata per essere utile alla tua decisione.",
    icon: "chat",
    benefits: [
      "Recensioni verificate di proprietari",
      "Guide pratiche per ogni modello",
      "Discussioni moderate e utili",
      "Segnalazione di difetti ricorrenti",
    ],
  },
  {
    slug: "value-prediction",
    title: "Value Prediction",
    short: "Quanto varrà il tuo veicolo domani.",
    long: "Una previsione del valore futuro basata su modello, chilometri, stato e andamento del mercato, per scegliere il momento giusto per vendere.",
    icon: "trend",
    preview: "line",
    benefits: [
      "Curva di svalutazione personalizzata",
      "Finestra ottimale di vendita",
      "Impatto dei chilometri sul valore",
      "Confronto con modelli simili",
    ],
  },
  {
    slug: "upgrade-advisor",
    title: "Upgrade Advisor",
    short: "Quando conviene davvero cambiare veicolo.",
    long: "DriveWise incrocia costi, usura, valore residuo e nuove offerte per dirti se cambiare è un vero miglioramento o solo una spesa.",
    icon: "arrowup",
    benefits: [
      "Analisi costo di tenere vs cambiare",
      "Valore residuo aggiornato",
      "Alternative realmente migliori",
      "Nessun consiglio senza numeri",
    ],
  },
  {
    slug: "smart-garage",
    title: "Smart Garage",
    short:
      "DriveWise conosce garage, stile di guida, budget, famiglia e chilometri, e ti avvisa quando un nuovo veicolo è un reale miglioramento.",
    long: "Il tuo profilo decisionale continua a lavorare anche quando non stai cercando. Quando esce un veicolo che migliora davvero la tua situazione, lo sai per primo — con la spiegazione del perché.",
    icon: "smart",
    hero: true,
    preview: "smart",
    benefits: [
      "Monitoraggio continuo del mercato",
      "Notifica solo quando il miglioramento è reale",
      "Compatibilità garage verificata",
      "Confronto diretto con il tuo veicolo attuale",
    ],
  },
  {
    slug: "insights",
    title: "Insights",
    short: "I tuoi numeri, letti nel tempo.",
    long: "Km percorsi, spesa totale, costo mensile, svalutazione e Decision Score medio: una fotografia chiara di come guidi e di quanto ti costa.",
    icon: "chart",
    preview: "stats",
    benefits: [
      "Andamento mensile dei costi",
      "Km percorsi e utilizzo reale",
      "Svalutazione cumulata",
      "Decision Score medio nel tempo",
    ],
  },
  {
    slug: "achievement",
    title: "Achievement",
    short: "Le tue decisioni migliori, riconosciute.",
    long: "Badge e medaglie sobri che raccontano i risparmi ottenuti e le decisioni corrette prese con DriveWise.",
    icon: "medal",
    preview: "badges",
    benefits: [
      "Badge per ogni traguardo raggiunto",
      "Risparmio complessivo certificato",
      "Storico delle decisioni corrette",
      "Obiettivi personali per il prossimo anno",
    ],
  },
];

export function getFeature(slug: string): Feature | undefined {
  return FEATURES.find((f) => f.slug === slug);
}

export const METRICS = [
  { label: "Decision Profile", value: 92, suffix: "%", icon: "ring" as const },
  { label: "Decisioni effettuate", value: 3, suffix: "", icon: "check" as const },
  { label: "Veicoli salvati", value: 7, suffix: "", icon: "heart" as const },
  { label: "Auto nel Garage", value: 1, suffix: "", icon: "car" as const },
  { label: "Analisi effettuate", value: 18, suffix: "", icon: "spark" as const },
];
export type SectionId = "garage" | "management" | "ai" | "services";

export const SECTIONS: {
  id: SectionId;
  icon: "garage" | "wrench" | "brain" | "globe";
  title: string;
  subtitle: string;
  items: FeatureKey[];
}[] = [
  {
    id: "garage",
    icon: "garage",
    title: "Il tuo Garage",
    subtitle: "Tutto ci\u00f2 che riguarda i tuoi veicoli.",
    items: ["garage", "decision-history", "wishlist", "compare-later"],
  },
  {
    id: "management",
    icon: "wrench",
    title: "Gestione del veicolo",
    subtitle: "Monitora costi, documenti e manutenzione.",
    items: ["cost-tracker", "smart-maintenance", "vehicle-health", "document-wallet"],
  },
  {
    id: "ai",
    icon: "brain",
    title: "DriveWise AI",
    subtitle:
      "L'intelligenza artificiale che ti accompagna durante tutto il ciclo di vita del veicolo.",
    items: ["smart-garage", "ai-advisor", "insights"],
  },
  {
    id: "services",
    icon: "globe",
    title: "Servizi",
    subtitle: "Tutto ci\u00f2 che semplificher\u00e0 la gestione del tuo veicolo.",
    items: [
      "insurance-center",
      "finance",
      "community",
      "value-prediction",
      "upgrade-advisor",
      "achievement",
      "family-garage",
    ],
  },
];

export function sectionOf(slug: FeatureKey): SectionId {
  return SECTIONS.find((s) => s.items.includes(slug))?.id ?? "services";
}

export const existingFeatureRoutes = { 'ai-advisor': '/advisor', 'document-wallet': '/documents', 'decision-history': '/app/me' } as const;
