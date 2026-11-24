import type { VehicleTypeKey } from "@/services/vehicleService";
import type { Answers, Question } from "./wizard-questions";

/** Infer only explicit information; ambiguous requests keep the type question. */
export function vehicleTypeFromText(text: string): VehicleTypeKey | null {
  const types: VehicleTypeKey[] = [];
  if (/\b(auto|automobile|vettura|suv|station wagon|monovolume)\b/i.test(text)) types.push("car");
  if (/\b(moto|motocicletta)\b/i.test(text)) types.push("motorcycle");
  if (/\bscooter\b/i.test(text)) types.push("scooter");
  return types.length === 1 ? types[0] ?? null : null;
}

export function answersFromText(text: string, questions: Question[], vehicleType?: VehicleTypeKey): Answers {
  if (!text.trim()) return {};
  const answers: Answers = { freeText: text.trim() };
  const experience = experienceFromText(text, vehicleType);
  if (experience && questions.some((q) => q.id === "experience")) answers['experience'] = experience;
  const height = text.match(/(?:altezza\s*[:=]?|alt[oa]|sono(?:\s+alt[oa])?)\s*(1[.,]\d{1,2}|\d{3})\s*(?:m(?:etri)?|cm)?\b/i);
  if (height?.[1] && questions.some((q) => q.id === "rider_height_cm")) {
    const raw = height[1].replace(",", ".");
    const cm = Math.round(Number(raw) * (raw.includes(".") ? 100 : 1));
    if (cm >= 100 && cm <= 250) answers['rider_height_cm'] = String(cm);
  }
  const budget = text.match(/(?:sotto(?:\s+i)?|budget(?:\s+(?:massimo|di))?|fino a|massimo)\s*(\d[\d. ]*)\s*(?:€|euro)/i);
  if (budget?.[1]) {
    const value = Number(budget[1].replace(/[. ]/g, ""));
    if (value > 0 && questions.some((q) => q.id === "budgetMax")) answers['budgetMax'] = String(value);
  }
  const category = questions.find((q) => q.id === "category")?.options
    ?.filter((o) => o.value && [o.label, o.value].some((label) => text.toLocaleLowerCase('it-IT').includes(label.toLocaleLowerCase('it-IT'))))
    .sort((a, b) => b.label.length - a.label.length)[0];
  if (category) answers['category'] = category.value;
  return answers;
}

export function experienceFromText(text: string, vehicleType?: VehicleTypeKey): "beginner" | "experienced" | null {
  const normalized = text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const targetType = vehicleType ?? vehicleTypeFromText(normalized);
  const beginner = /\b(per iniziare|prima moto|neopatentato|principiante|non ho mai guidato una moto)\b/.test(normalized);
  const matchesTarget = (phrase: string) => {
    const mentionedType = vehicleTypeFromText(phrase);
    return !targetType || !mentionedType || mentionedType === targetType;
  };
  const positiveMatch = (match: RegExpMatchArray) => {
    const prefix = normalized.slice(0, match.index ?? 0);
    return !/\bnon\s*$/.test(prefix) && matchesTarget(match[0]);
  };
  // Allow intervening vehicle words, but require an explicit first-person declaration.
  const driving = [...normalized.matchAll(/\bguido(?:\s+(?!(?:da|non)\b)[a-z]+){0,5}\s+da\s+(?:(\d+)\s+)?anni\b/g)]
    .some((match) => positiveMatch(match) && (!match[1] || Number(match[1]) >= 2));
  const ownershipYears = [...normalized.matchAll(/\bho\s+(?:(?:la|una|un|lo|uno|l)\s*['’]?\s*)?(?:moto|motocicletta|scooter|auto|automobile|vettura)\s+da\s+(\d+)\s+anni\b/g)]
    .some((match) => positiveMatch(match) && Number(match[1]) >= 2);
  const previousOwnership = [...normalized.matchAll(/\bho\s+gia\s+(?:avuto|posseduto)(?:\s+(?!(?:non|ma)\b)[a-z]+){0,3}?\s+(?:moto|motociclette?|scooter|auto|automobili?|vetture?)\b/g)]
    .some(positiveMatch);
  const experienced = /\besperto\b/.test(normalized) || driving || ownershipYears || previousOwnership;
  // Negated levels and conflicting declarations must remain a question.
  if (/\bnon\s+(?:sono|mi considero|sono un|sono piu)\s+(?:esperto|principiante)\b/.test(normalized)) return null;
  if (beginner === experienced) return null;
  return beginner ? "beginner" : "experienced";
}

export function summarizeRequest(text: string): string {
  const height = text.match(/(?:altezza\s*[:=]?|alt[oa]|sono(?:\s+alt[oa])?)\s*(1[.,]\d{1,2}|\d{3})\s*(?:m(?:etri)?|cm)?\b/i)?.[1];
  const firstMotorcycle = /\bmoto\b/i.test(text) && /\b(prima|iniziare|principiante)\b/i.test(text);
  if (firstMotorcycle) {
    if (height) {
      const raw = Number(height.replace(",", "."));
      const meters = raw > 3 ? raw / 100 : raw;
      return `Prima moto, altezza ${meters.toFixed(2).replace(".", ",")} m`;
    }
    return "Prima moto";
  }
  return text.trim().replace(/^(?:cerco|vorrei|mi serve|sto cercando)\s+(?:un['’]?|una|uno)?\s*/i, "")
    .split(/\s+/).slice(0, 6).join(" ");
}

export function isAnswered(answers: Answers, id: string): boolean {
  const value = answers[id];
  return Array.isArray(value) ? value.length > 0 : value !== undefined;
}

/** An unloaded questionnaire is never a completed profile. */
export function wizardCompletion(typeSelected: boolean, questions: Question[], answers: Answers): number {
  if (!typeSelected || questions.length === 0) return 0;
  const count = questions.filter((q) => isAnswered(answers, q.id)).length;
  const percentage = Math.round(((count + 1) / (questions.length + 1)) * 100);
  return count === questions.length ? 100 : Math.min(99, percentage);
}

export function chronologicalQuestions(questions: Question[], answers: Answers, currentId?: string, consumedText = false): Question[] {
  const history = Object.keys(answers).flatMap((id) => {
    if (id === currentId || (consumedText && id === "freeText") || !isAnswered(answers, id)) return [];
    const question = questions.find((q) => q.id === id);
    return question ? [question] : [];
  });
  const current = questions.find((q) => q.id === currentId);
  return current ? [...history, current] : history;
}