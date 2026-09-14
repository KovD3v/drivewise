/**
 * Domande del wizard generate dal dataset: ogni opzione esiste davvero nei dati.
 * Nessuna domanda viene posta se il campo corrispondente non è coperto
 * per quel vehicle_type (vedi coverage_matrix.csv).
 */
import type { DecisionProfile } from "@/lib/decision-profile";
import {
  getCategories,
  getVehiclesByType,
  type Vehicle,
  type VehicleTypeKey,
} from "@/services/vehicleService";

export type Option = { value: string; label: string };

export type Question = {
  id: string;
  /** tema grafico dello StepStage */
  themeId: "facts" | "km" | "priority" | "garage" | "budget";
  prompt: string;
  hint?: string;
  kind: "single" | "multi" | "text" | "garage";
  options?: Option[];
  max?: number;
  allowCustom?: boolean;
};

const dnaLabelMap: Record<string, string> = {
  reliability: "Affidabilità",
  comfort: "Comfort",
  technology: "Tecnologia",
  city: "Uso in città",
  travel: "Viaggi lunghi",
  running_cost: "Costi di gestione",
  safety: "Sicurezza",
  family: "Famiglia",
  sport: "Sportività",
};

function dnaOptions(vehicles: Vehicle[]): Option[] {
  const keys = new Set<string>();
  vehicles.forEach((v) =>
    Object.entries(v.vehicle_dna).forEach(([k, value]) => {
      if (typeof value === "number") keys.add(k);
    }),
  );
  const options = [...keys].map((k) => ({ value: k, label: dnaLabelMap[k] ?? k }));
  if (vehicles.some((v) => typeof v.theft_risk.observed_thefts_italy_2024 === "number"))
    options.push({ value: "theft_risk", label: "Rischio furto" });
  return options;
}

/** Fasce di budget calcolate sui prezzi realmente presenti nel dataset. */
function budgetOptions(vehicles: Vehicle[]): Option[] {
  const prices = vehicles
    .map((v) => v.pricing.new_price_estimate)
    .filter((p): p is number => typeof p === "number")
    .sort((a, b) => a - b);
  if (prices.length < 2) return [];
  const round = (n: number) => Math.round(n / 500) * 500;
  const quantile = (q: number) => prices[Math.min(prices.length - 1, Math.floor(prices.length * q))]!;
  const steps = [round(quantile(0.25)), round(quantile(0.5)), round(quantile(0.8)), round(prices[prices.length - 1]!)];
  const unique = [...new Set(steps)];
  return unique.map((p) => ({ value: String(p), label: `Fino a ${p.toLocaleString("it-IT")} €` }));
}

const usageOptionsByType: Record<VehicleTypeKey, Option[]> = {
  car: [
    { value: "city", label: "Città" },
    { value: "commute", label: "Casa-lavoro" },
    { value: "travel", label: "Viaggi lunghi" },
    { value: "family", label: "Famiglia" },
  ],
  motorcycle: [
    { value: "city", label: "Città" },
    { value: "commute", label: "Casa-lavoro" },
    { value: "touring", label: "Turismo e viaggi" },
  ],
  scooter: [
    { value: "city", label: "Città" },
    { value: "commute", label: "Casa-lavoro" },
    { value: "ring_road", label: "Tangenziale / extraurbano" },
  ],
};

export const typeOptions: Option[] = [
  { value: "car", label: "Auto" },
  { value: "motorcycle", label: "Moto" },
  { value: "scooter", label: "Scooter" },
];

export async function buildQuestions(type: VehicleTypeKey): Promise<Question[]> {
  const vehicles = await getVehiclesByType(type);
  const categories = await getCategories(type);

  const questions: Question[] = [
    {
      id: "category",
      themeId: "facts",
      prompt: "Quale categoria stai considerando?",
      hint: "Le categorie disponibili nel catalogo DriveWise per questa scelta.",
      kind: "single",
      options: [
        ...categories.map((c) => ({ value: c, label: c })),
        { value: "", label: "Non lo so ancora" },
      ],
    },
    {
      id: "freeText",
      themeId: "facts",
      prompt: "Raccontami cosa cerchi.",
      hint: "Scrivi liberamente: userò le tue parole per pesare la scelta.",
      kind: "text",
    },
    {
      id: "usage",
      themeId: "km",
      prompt: "Come lo userai principalmente?",
      hint: "Puoi indicare più utilizzi.",
      kind: "multi",
      max: 3,
      options: usageOptionsByType[type],
    },
    {
      id: "priorities",
      themeId: "priority",
      prompt: "Cosa conta davvero per te?",
      hint: "Fino a tre priorità, in ordine di importanza.",
      kind: "multi",
      max: 3,
      options: dnaOptions(vehicles),
    },
  ];

  const budget = budgetOptions(vehicles);
  if (budget.length)
    questions.push({
      id: "budgetMax",
      themeId: "budget",
      prompt: "Qual è il tuo budget massimo?",
      hint: "Le fasce derivano dai prezzi reali dei veicoli in catalogo.",
      kind: "single",
      options: budget,
      allowCustom: true,
    });

  if (type === "car") {
    questions.push({
      id: "garage_status",
      themeId: "garage",
      prompt: "Dove lo parcheggerai?",
      hint: "Con le misure esatte posso verificare la compatibilità reale.",
      kind: "single",
      options: [
        { value: "known", label: "Garage con misure note" },
        { value: "unknown_dimensions", label: "Garage, ma non conosco le misure" },
        { value: "none", label: "Nessun garage" },
      ],
    });
    questions.push({ id: "garageDimensions", themeId: "garage", prompt: "Le misure del tuo garage", kind: "garage" });
    questions.push({
      id: "family_profile",
      themeId: "priority",
      prompt: "Chi viaggia di solito con te?",
      kind: "single",
      options: [
        { value: "solo", label: "Quasi sempre da solo" },
        { value: "couple", label: "In due" },
        { value: "family", label: "Famiglia con bambini" },
      ],
    });
  }

  if (type === "motorcycle") {
    questions.push({
      id: "experience",
      themeId: "priority",
      prompt: "Qual è la tua esperienza in sella?",
      hint: "Determina il peso e la potenza gestibili in sicurezza.",
      kind: "single",
      options: [
        { value: "beginner", label: "Principiante" },
        { value: "beginner_intermediate", label: "Principiante / intermedio" },
        { value: "intermediate", label: "Intermedio" },
        { value: "experienced", label: "Esperto" },
      ],
    });
    questions.push({
      id: "rider_height_cm",
      themeId: "garage",
      prompt: "Quanto sei alto?",
      hint: "Serve per valutare l'altezza sella.",
      kind: "single",
      allowCustom: true,
      options: [
        { value: "160", label: "Fino a 160 cm" },
        { value: "170", label: "165-170 cm" },
        { value: "180", label: "175-180 cm" },
        { value: "190", label: "Oltre 185 cm" },
      ],
    });
    questions.push({
      id: "passenger_frequent",
      themeId: "km",
      prompt: "Porterai spesso un passeggero?",
      kind: "single",
      options: [
        { value: "yes", label: "Sì, spesso" },
        { value: "no", label: "Raramente o mai" },
      ],
    });
  }

  if (type === "scooter") {
    questions.push({
      id: "helmet_storage_required",
      themeId: "garage",
      prompt: "Ti serve il sottosella da casco integrale?",
      hint: "Nel dataset è un dato osservato, non una stima.",
      kind: "single",
      options: [
        { value: "yes", label: "Sì, indispensabile" },
        { value: "no", label: "Non è necessario" },
      ],
    });
    questions.push({
      id: "passenger_frequent",
      themeId: "km",
      prompt: "Viaggerai spesso in due?",
      kind: "single",
      options: [
        { value: "yes", label: "Sì, spesso" },
        { value: "no", label: "Raramente o mai" },
      ],
    });
  }

  return questions;
}

export type Answers = Record<string, string | string[] | Record<string, string> | undefined>;

/** Mappa le risposte del wizard sul DecisionProfile condiviso. */
export function answersToProfile(type: VehicleTypeKey, answers: Answers): DecisionProfile {
  const str = (id: string) => (typeof answers[id] === "string" ? (answers[id] as string) : undefined);
  const arr = (id: string) => (Array.isArray(answers[id]) ? (answers[id] as string[]) : undefined);
  const garage = answers["garageDimensions"];
  const profile: DecisionProfile = { vehicleType: type };
  const category = str("category");
  if (category) profile.category = category;
  const free = str("freeText");
  if (free) profile.freeText = free;
  const usage = arr("usage");
  if (usage?.length) profile.usage = usage;
  const priorities = arr("priorities");
  if (priorities?.length) profile.priorities = priorities;
  const budget = str("budgetMax");
  if (budget) {
    const n = Number(budget.replace(/[^0-9]/g, ""));
    if (Number.isFinite(n) && n > 0) profile.budgetMax = n;
  }
  if (type === "car") {
    const status = str("garage_status");
    if (status === "known" || status === "unknown_dimensions" || status === "none")
      profile.garage_status = status;
    if (garage && typeof garage === "object" && !Array.isArray(garage))
      profile.garageDimensions = garage as DecisionProfile["garageDimensions"];
    const family = str("family_profile");
    if (family) profile.family_profile = family;
  }
  if (type === "motorcycle") {
    const exp = str("experience");
    if (exp) profile.experience = exp as DecisionProfile["experience"];
    const h = Number(str("rider_height_cm")?.replace(/[^0-9]/g, ""));
    if (Number.isFinite(h) && h > 0) profile.rider_height_cm = h;
  }
  if (type === "scooter") {
    const helmet = str("helmet_storage_required");
    if (helmet) profile.helmet_storage_required = helmet === "yes";
  }
  const passenger = str("passenger_frequent");
  if (passenger) profile.passenger_frequent = passenger === "yes";
  return profile;
}

/** Le domande realmente da porre, saltando quelle non pertinenti alle risposte già date. */
export function isQuestionActive(q: Question, answers: Answers): boolean {
  if (q.id === "garageDimensions") return answers["garage_status"] === "known";
  return true;
}
