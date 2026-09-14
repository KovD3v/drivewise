/** Profilo decisionale dell'utente: unica struttura condivisa da wizard, report e scheda veicolo. */
import type { VehicleTypeKey } from "@/services/vehicleService";

export type GarageStatus = "known" | "unknown_dimensions" | "none";

export type RiderExperience = "beginner" | "beginner_intermediate" | "intermediate" | "experienced";

export type GarageDimensionsCm = {
  length: string;
  width: string;
  height: string;
  doorWidth?: string;
  doorHeight?: string;
};

export type DecisionProfile = {
  vehicleType: VehicleTypeKey;
  decisionId?: string;
  category?: string | undefined;
  budgetMax?: number | undefined;
  /** Chiavi di vehicle_dna + "theft_risk". */
  priorities?: string[] | undefined;
  usage?: string[] | undefined;
  region?: string | undefined;
  freeText?: string | undefined;
  // car
  garage_status?: GarageStatus | undefined;
  garageDimensions?: GarageDimensionsCm | undefined;
  family_profile?: string | undefined;
  // motorcycle
  experience?: RiderExperience | undefined;
  rider_height_cm?: number | undefined;
  passenger_frequent?: boolean | undefined;
  // scooter
  helmet_storage_required?: boolean | undefined;
};

export const vehicleTypeLabels: Record<VehicleTypeKey, string> = {
  car: "Auto",
  motorcycle: "Moto",
  scooter: "Scooter",
};

export const experienceLabels: Record<string, string> = {
  beginner: "Principiante",
  beginner_intermediate: "Principiante / intermedio",
  intermediate: "Intermedio",
  experienced: "Esperto",
};

export const dnaLabels: Record<string, string> = {
  reliability: "Affidabilità",
  comfort: "Comfort",
  technology: "Tecnologia",
  city: "Città",
  travel: "Viaggi",
  running_cost: "Costo di gestione",
  safety: "Sicurezza",
  family: "Famiglia",
  sport: "Sportività",
  theft_risk: "Rischio furto",
};

export const usageLabels: Record<string, string> = {
  city: "Città",
  commute: "Casa-lavoro",
  travel: "Viaggi lunghi",
  touring: "Turismo",
  ring_road: "Tangenziale / extraurbano",
  family: "Famiglia",
};

/** Fatto estratto dal racconto dell'utente, mostrato nel wizard. */
export type Fact = { id: string; label: string; value: string };

/** Informazione ancora mancante nel profilo. */
export type MissingItem = { id: string; label: string };
