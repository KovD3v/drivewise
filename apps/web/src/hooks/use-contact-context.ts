import { useEffect, useState } from "react";
import { CONTACT_SOURCE_KEY, safeContactSource } from "@/lib/contact-intelligence";
import { loadState } from "@/lib/decision-state";
import { listSavedAnalyses } from "@/lib/saved-analyses";
import { getVehicleById } from "@/services/vehicleService";
import { vehicleTypeLabels } from "@/lib/decision-profile";
import type { AnalysisAttachment } from "@/lib/contact-validation";

export function useContactContext(from: string, analysisId: string) {
  const [context, setContext] = useState<{ source: string; analysis: AnalysisAttachment | null; technical: { browser: string; device: string; page: string } }>({ source: "", analysis: null, technical: { browser: "", device: "", page: "" } });
  useEffect(() => {
    let active = true;
    let source = safeContactSource(from);
    if (!source) {
      try { source = safeContactSource(sessionStorage.getItem(CONTACT_SOURCE_KEY)); } catch { /* storage unavailable */ }
    }
    if (!source && document.referrer) {
      const referrer = new URL(document.referrer);
      if (referrer.origin === window.location.origin) source = safeContactSource(referrer.pathname);
    }
    const technical = { browser: navigator.userAgent.slice(0, 500), device: window.matchMedia("(max-width: 767px)").matches ? "Mobile" : "Computer o tablet", page: window.location.pathname };
    setContext({ source, analysis: null, technical });
    void (async () => {
      let analysis: AnalysisAttachment | null = null;
      if (analysisId || source.startsWith("/app/vehicle/")) {
        const saved = await listSavedAnalyses();
        const row = analysisId ? saved.find((item) => item.id === analysisId) : saved.find((item) => item.vehicleId === source.split("/")[3]);
        if (row) analysis = { vehicleId: row.vehicleId, vehicleName: `${row.brand} ${row.model}`, score: row.score, confidence: row.confidence };
      } else if (source === "/app/start" || source === "/app/report") {
        const state = loadState();
        const id = state?.rankingIds[0];
        const vehicle = id ? await getVehicleById(id) : null;
        if (state) analysis = { vehicleId: vehicle?.id ?? "", vehicleName: vehicle ? `${vehicle.brand} ${vehicle.model}` : `${vehicleTypeLabels[state.profile.vehicleType]} · scelta in corso`, confidence: state.decisionConfidence };
      }
      if (active) setContext({ source, analysis, technical });
    })().catch(() => { /* attachments are optional; the form remains usable */ });
    return () => { active = false; };
  }, [from, analysisId]);
  return context;
}