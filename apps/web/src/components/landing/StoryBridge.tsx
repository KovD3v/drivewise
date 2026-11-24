import { useEffect, useRef, useState, type CSSProperties } from "react";
import { useScrollProgress } from "./useScrollProgress";
import { getStoryPick, subscribeStoryPick, type StoryVehicle } from "./storyStore";

/**
 * Ponte animato tra Capitolo 1 (la scelta) e Capitolo 2 (dopo la scelta).
 * Mentre scorri, la strada tratteggiata si disegna e il veicolo scelto nel capitolo 1
 * (auto, moto o scooter, letto da storyStore) la percorre dall'alto verso il basso.
 * A metà compare "Hai scelto. E poi?". Con "riduci movimento" tutto è già al traguardo.
 */

const NAMES: Record<StoryVehicle, string> = {
  auto: "La tua station wagon",
  moto: "La tua moto",
  scooter: "Il tuo scooter",
};

type Vars = CSSProperties & Record<`--${string}`, string | number>;

/* veicoli visti dall'alto, puntati verso il basso (viewBox 40×80) */
function TopView({ v }: { v: StoryVehicle }) {
  if (v === "auto")
    return (
      <svg viewBox="0 0 40 80" width="100%" height="100%" aria-hidden>
        <rect x="3" y="12" width="5" height="12" rx="2" fill="#3B4458" />
        <rect x="32" y="12" width="5" height="12" rx="2" fill="#3B4458" />
        <rect x="3" y="54" width="5" height="12" rx="2" fill="#3B4458" />
        <rect x="32" y="54" width="5" height="12" rx="2" fill="#3B4458" />
        <rect x="6" y="4" width="28" height="72" rx="11" fill="#BFE8DA" stroke="#9ED6C3" strokeWidth="1.5" />
        <path d="M10 22 Q20 18 30 22 L28 32 H12 Z" fill="#D9E8F5" />
        <path d="M11 58 Q20 62 29 58 L28 52 H12 Z" fill="#D9E8F5" />
        <rect x="12" y="34" width="16" height="16" rx="3" fill="#CFEFE4" />
        <rect x="9" y="72" width="7" height="3" rx="1.5" fill="#FFF6D8" />
        <rect x="24" y="72" width="7" height="3" rx="1.5" fill="#FFF6D8" />
      </svg>
    );
  if (v === "moto")
    return (
      <svg viewBox="0 0 40 80" width="100%" height="100%" aria-hidden>
        <rect x="16" y="2" width="8" height="18" rx="4" fill="#3B4458" />
        <rect x="16" y="60" width="8" height="18" rx="4" fill="#3B4458" />
        <path d="M6 58 L34 58" stroke="#334155" strokeWidth="3" strokeLinecap="round" />
        <rect x="13" y="16" width="14" height="40" rx="7" fill="#D9D1FA" stroke="#BCB0F0" strokeWidth="1.5" />
        <rect x="15" y="20" width="10" height="14" rx="4" fill="#4A5366" />
        <circle cx="20" cy="62" r="4" fill="#FFF6D8" />
      </svg>
    );
  return (
    <svg viewBox="0 0 40 80" width="100%" height="100%" aria-hidden>
      <rect x="16" y="4" width="8" height="14" rx="4" fill="#3B4458" />
      <rect x="16" y="62" width="8" height="14" rx="4" fill="#3B4458" />
      <path d="M8 60 L32 60" stroke="#334155" strokeWidth="3" strokeLinecap="round" />
      <rect x="11" y="10" width="18" height="40" rx="9" fill="#FFD6C4" stroke="#F4B9A0" strokeWidth="1.5" />
      <rect x="13" y="14" width="14" height="18" rx="6" fill="#6E5A52" />
      <path d="M12 50 Q20 66 28 50 Z" fill="#FFD6C4" stroke="#F4B9A0" strokeWidth="1.5" />
      <circle cx="20" cy="64" r="3.5" fill="#FFF6D8" />
    </svg>
  );
}

export function StoryBridge({ className = "" }: { className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [veh, setVeh] = useState<StoryVehicle>(() => getStoryPick().vehicle);
  useScrollProgress(ref, 0.9, 0.3);
  useEffect(() => subscribeStoryPick((p) => setVeh(p.vehicle)), []);

  return (
    <div ref={ref} className={`sb ${className}`} aria-hidden>
      <style>{CSS}</style>
      <span className="sb-tag sb-from">La scelta</span>
      <div className="sb-road">
        <svg viewBox="0 0 40 240" preserveAspectRatio="none">
          <path className="sb-track" d="M20 0 V240" />
          <path className="sb-draw" d="M20 0 V240" pathLength={1} />
        </svg>
        <div className="sb-veh" style={{ "--k": veh } as Vars}>
          <TopView v={veh} />
        </div>
      </div>
      <p className="sb-text">
        Hai scelto. <b>E poi?</b>
        <small>{NAMES[veh]} entra in My DriveWise</small>
      </p>
      <span className="sb-tag sb-to">Dopo la scelta</span>
    </div>
  );
}

const CSS = `
.sb{ --ink:#1F2A44; --muted:#5E6A82; --mint-ink:#257A67;
  position:relative; display:flex; flex-direction:column; align-items:center; padding:12px 0 8px; }
.sb-tag{ font:600 12px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.16em; text-transform:uppercase; color:var(--muted);
  padding:6px 10px; border-radius:99px; background:rgba(255,255,255,.8); box-shadow:inset 0 0 0 1px rgba(31,42,68,.08); }
.sb-to{ color:var(--brand-ink); }
.sb-road{ position:relative; width:40px; height:240px; margin:10px 0; }
.sb-road svg{ position:absolute; inset:0; width:100%; height:100%; overflow:visible; }
.sb-track{ stroke:rgba(31,42,68,.12); stroke-width:2; stroke-dasharray:4 7; fill:none; }
.sb-draw{ stroke:var(--mint-ink); stroke-width:3; fill:none; stroke-linecap:round; stroke-dasharray:1 1;
  stroke-dashoffset:calc(1 - var(--sp, 1)); opacity:.55; }
.sb-veh{ position:absolute; left:50%; top:0; width:32px; height:64px; margin-left:-16px;
  transform:translateY(calc(var(--sp, 1) * 176px)); filter:drop-shadow(0 6px 8px rgba(31,42,68,.18)); }
.sb-text{ margin:0 0 14px; text-align:center; font-size:15px; color:var(--muted);
  transform:translateY(calc((1 - clamp(0, calc((var(--sp, 1) - .35) * 4), 1)) * 8px)); }
.sb-text b{ color:var(--ink); }
.sb-text small{ display:block; margin-top:4px; font-size:13px; color:var(--brand-ink); }
`;
