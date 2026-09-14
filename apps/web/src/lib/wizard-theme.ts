/**
 * Personalità visiva e narrativa del wizard "Scelta Guidata".
 * Pura configurazione: quando il Decision Engine (FastAPI) fornirà gli step,
 * basterà mappare l'id dello step su questa tabella.
 */
import {
  Activity,
  BadgeEuro,
  Brain,
  Calculator,
  Gauge,
  Layers,
  Lightbulb,
  Ruler,
  Route,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Target,
  Wrench,
  type LucideIcon,
} from "lucide-react";

export type Tint = "primary" | "accent";

export type StepTheme = {
  id: string;
  eyebrow: string;
  icon: LucideIcon;
  tint: Tint;
  /** Motivo grafico di sfondo, discreto. */
  motif: "grid" | "waves" | "rings" | "bars";
  hint: string;
};

export const stepThemes: Record<string, StepTheme> = {
  facts: {
    id: "facts",
    eyebrow: "Comprensione",
    icon: Sparkles,
    tint: "accent",
    motif: "rings",
    hint: "Estratto dal tuo racconto",
  },
  km: {
    id: "km",
    eyebrow: "Utilizzo quotidiano",
    icon: Route,
    tint: "primary",
    motif: "waves",
    hint: "Incide su alimentazione e costi reali",
  },
  priority: {
    id: "priority",
    eyebrow: "Valori e priorità",
    icon: Target,
    tint: "accent",
    motif: "bars",
    hint: "Pesa le variabili del Decision Score",
  },
  garage: {
    id: "garage",
    eyebrow: "Vincoli fisici",
    icon: Ruler,
    tint: "primary",
    motif: "grid",
    hint: "Serve per il Garage Fit",
  },
  budget: {
    id: "budget",
    eyebrow: "Sostenibilità economica",
    icon: BadgeEuro,
    tint: "accent",
    motif: "bars",
    hint: "Costo d'acquisto e di possesso",
  },
};

export const tintClasses: Record<Tint, { ring: string; soft: string; text: string; dot: string }> = {
  primary: {
    ring: "border-primary/30",
    soft: "bg-primary/10",
    text: "text-foreground",
    dot: "bg-primary",
  },
  accent: {
    ring: "border-accent/25",
    soft: "bg-accent/10",
    text: "text-foreground",
    dot: "bg-accent",
  },
};

/** Frasi di progressione: cambiano in base al completamento del profilo. */
export function progressNarrative(completion: number): string {
  if (completion < 25) return "Sto leggendo la tua richiesta e isolo i parametri utili…";
  if (completion < 50) return "Stiamo comprendendo il tuo stile di utilizzo…";
  if (completion < 70) return "Sto pesando le tue priorità sul Decision Score…";
  if (completion < 90) return "Abbiamo quasi completato il tuo Decision Profile…";
  if (completion < 100) return "Le ultime informazioni ci permettono di individuare il veicolo ideale.";
  return "Decision Profile completo: procedo con l'analisi.";
}

export type AnalysisPhase = { label: string; icon: LucideIcon; detail: string };

export const analysisPhases: AnalysisPhase[] = [
  { label: "Analisi del profilo", icon: Brain, detail: "12 parametri dichiarati" },
  { label: "Analisi delle esigenze", icon: Layers, detail: "Uso reale e contesto" },
  { label: "Analisi economica", icon: Calculator, detail: "TCO a 1, 3 e 5 anni" },
  { label: "Analisi tecnica", icon: Wrench, detail: "Affidabilità e manutenzione" },
  { label: "Compatibilità con il tuo utilizzo", icon: Gauge, detail: "Percorrenze e vincoli" },
  { label: "Calcolo Decision Score", icon: Activity, detail: "Pesatura multi-criterio" },
  { label: "Explainability", icon: Lightbulb, detail: "Motivazioni verificabili" },
  { label: "Preparazione del report finale", icon: ScrollText, detail: "Decision Report finale" },
];

export const trustBadgeIcon = ShieldCheck;
