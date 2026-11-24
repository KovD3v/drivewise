import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";
import { PastelCar, PastelMoto, PastelScooter } from "./PastelVehicles";

/**
 * Vignetta 16:9 "La pipeline delle informazioni".
 * Sinistra: un flusso continuo di schede-dato entra nel motore.
 * Centro: il veicolo (auto → moto → scooter, a rotazione) con i dati agganciati alle sue parti.
 * Destra: la card con il Decision Score, i motivi e il compromesso.
 *
 * - Animazione solo CSS, in loop (18 s, 6 s per veicolo); in pausa quando non è visibile.
 * - prefers-reduced-motion: scena dell'auto ferma, completa.
 * - Sotto i 640 px di larghezza il layout diventa verticale (4:5).
 * - Per i render 3D definitivi basta impostare `src` (e, se serve, `aspect` e gli hotspot).
 */

type Tone = "mint" | "sky" | "peach" | "lavender" | "butter";
type Hotspot = { x: number; y: number; label: string; value: string; side?: "left" | "right" };
type Vehicle = {
  key: string;
  name: string;
  kind: string;
  score: number;
  aspect: number; // larghezza / altezza dell'immagine
  src?: string; // render 3D definitivo (WebP/PNG trasparente)
  placeholder: ReactNode;
  hotspots: Hotspot[];
  reasons: string[];
  tradeoff: string;
};

const VEHICLES: Vehicle[] = [
  {
    key: "auto",
    kind: "Auto",
    name: "Station wagon ibrida",
    score: 86,
    aspect: 320 / 115,
    placeholder: <PastelCar />,
    hotspots: [
      { x: 8, y: 40, label: "Bagagliaio", value: "608 L", side: "left" },
      { x: 44, y: 26, label: "Abitacolo", value: "5 posti · Isofix" },
      { x: 88, y: 50, label: "Consumo reale", value: "5,1 l/100 km", side: "left" },
    ],
    reasons: ["Costi d'uso bassi", "Bagagliaio da famiglia", "Entra nel tuo box"],
    tradeoff: "Accelerazione tranquilla",
  },
  {
    key: "moto",
    kind: "Moto",
    name: "Naked 700 cc",
    score: 78,
    aspect: 190 / 124,
    placeholder: <PastelMoto />,
    hotspots: [
      { x: 38, y: 28, label: "Altezza sella", value: "805 mm", side: "left" },
      { x: 66, y: 20, label: "Peso", value: "184 kg" },
      { x: 56, y: 62, label: "Consumo", value: "4,2 l/100 km" },
    ],
    reasons: ["Sella adatta alla tua altezza", "Peso gestibile", "Consumi contenuti"],
    tradeoff: "Poca protezione dal vento",
  },
  {
    key: "scooter",
    kind: "Scooter",
    name: "Scooter 300 cc",
    score: 91,
    aspect: 176 / 162,
    placeholder: <PastelScooter />,
    hotspots: [
      { x: 32, y: 48, label: "Sottosella", value: "1 casco integrale", side: "left" },
      { x: 80, y: 36, label: "Autostrada", value: "sì, oltre 150 cc" },
      { x: 26, y: 82, label: "Consumo", value: "3,1 l/100 km", side: "left" },
    ],
    reasons: ["Casco integrale nel sottosella", "Tangenziale e autostrada", "Agile in città"],
    tradeoff: "Spazio per un solo bagaglio",
  },
];

const DATA: { label: string; value: string; tone: Tone }[] = [
  { label: "Consumo reale", value: "5,1 l/100 km", tone: "mint" },
  { label: "Assicurazione RC", value: "~640 €/anno", tone: "sky" },
  { label: "Furti in Italia", value: "bassi", tone: "peach" },
  { label: "Richiami", value: "0 aperti", tone: "lavender" },
  { label: "Svalutazione 3 anni", value: "−31%", tone: "butter" },
  { label: "Tagliando", value: "280 €", tone: "mint" },
  { label: "Bagagliaio", value: "608 L", tone: "sky" },
  { label: "Lunghezza", value: "4,65 m", tone: "lavender" },
  { label: "Sicurezza", value: "5 stelle", tone: "mint" },
  { label: "Bollo", value: "212 €/anno", tone: "butter" },
  { label: "Recensioni", value: "4,4 / 5", tone: "peach" },
  { label: "Altezza sella", value: "805 mm", tone: "lavender" },
];
const LANES = [27, 37, 47, 57, 67, 77]; // % dall'alto

type Vars = CSSProperties & Record<`--${string}`, string | number>;

export function DecisionPipeline({ className = "" }: { className?: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => el.classList.toggle("dp-paused", !e?.isIntersecting));
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`dp ${className}`}
      role="img"
      aria-label="DriveWise incrocia decine di informazioni (consumi, costi, sicurezza, furti, richiami, misure, svalutazione) su auto, moto e scooter e le trasforma in un Decision Score con i motivi della scelta."
    >
      <style>{CSS}</style>
      <div className="dp-stage">
        {/* fondo */}
        <div className="dp-bg" aria-hidden />

        {/* intestazione */}
        <div className="dp-head" aria-hidden>
          <span className="dp-live" />
          DriveWise Motore decisionale
        </div>

        {/* linee della pipeline */}
        <svg className="dp-lines" viewBox="0 0 1600 900" preserveAspectRatio="none" aria-hidden>
          {LANES.map((y) => (
            <path key={y} d={`M0 ${y * 9} C 280 ${y * 9}, 400 470, 560 470`} />
          ))}
          <path className="dp-out" d="M1125 440 H1172" />
        </svg>

        {/* flusso di dati */}
        <div className="dp-flow" aria-hidden="true">
          {DATA.map((d, i) => {
            const lane = LANES[i % LANES.length] ?? 50;
            const style: Vars = {
              "--lane": `${lane}%`,
              "--dy": `${((55 - lane) / 100) * 56.25}cqw`,
              "--delay": `${-(i * 7) / DATA.length}s`,
              "--mdelay": `${-(i / 3) * 4}s`,
            };
            return (
              <div key={d.label} className={`dp-card dp-${d.tone}`} style={style} aria-hidden="true">
                <i />
                <span>{d.label}</span>
                <b>{d.value}</b>
              </div>
            );
          })}
        </div>

        {/* scene: una per veicolo */}
        {VEHICLES.map((veh, i) => (
          <div key={veh.key} className="dp-scene" data-i={i} style={{ "--delay": `${i * 6}s` } as Vars} aria-hidden>
            {/* contatore */}
            <div className="dp-count">
              <strong style={{ "--to": 120 } as Vars} />
              <span>
                parametri analizzati
                <br />
                per ogni {veh.kind.toLowerCase()}
              </span>
            </div>

            {/* veicolo */}
            <div className="dp-veh">
              <div className="dp-podium" />
              <div className="dp-img" style={{ "--ar": veh.aspect } as Vars}>
                {veh.src ? <img src={veh.src} alt="" draggable={false} /> : veh.placeholder}
                {veh.hotspots.map((h, k) => (
                  <div
                    key={h.label}
                    className={`dp-hot ${h.side === "left" ? "dp-hot-l" : ""} ${h.x < 20 ? "dp-hot-edge" : ""}`}
                    style={{ left: `${h.x}%`, top: `${h.y}%`, "--k": k } as Vars}
                  >
                    <i />
                    <div>
                      <span>{h.label}</span>
                      <b>{h.value}</b>
                    </div>
                  </div>
                ))}
              </div>
              <div className="dp-kind">{veh.kind}</div>
            </div>

            {/* decisione */}
            <div className="dp-card-out">
              <div className="dp-label">Decision Score</div>
              <p className="mt-1 text-xs text-muted-foreground">Punteggio DriveWise</p>
              <div className="dp-ring">
                <svg viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="42" pathLength={100} className="dp-track" />
                  <circle cx="50" cy="50" r="42" pathLength={100} className="dp-arc" style={{ "--to": veh.score } as Vars} />
                </svg>
                <strong style={{ "--to": veh.score } as Vars} />
              </div>
              <div className="dp-name">{veh.name}</div>
              <ul>
                {veh.reasons.map((r, k) => (
                  <li key={r} style={{ "--k": k } as Vars}>
                    <i>✓</i>
                    {r}
                  </li>
                ))}
                <li className="dp-trade" style={{ "--k": 3 } as Vars}>
                  <i>~</i>
                  {veh.tradeoff}
                </li>
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Stile. Unità in cqw (1cqw = 1% della larghezza della vignetta).     */
/* ------------------------------------------------------------------ */
const CSS = `
@property --dp-n { syntax: "<integer>"; inherits: false; initial-value: 0; }

.dp{
  --ink:#1F2A44; --muted:#5E6A82; --line:#CBD5E1;
  --mint:#CFF1E6; --mint-ink:#257A67; --sky:#DCEEFF; --sky-ink:#336AA8;
  --peach:#FFE1D3; --peach-ink:#A4532F; --lavender:#E6E0FF; --lavender-ink:#6B5BD6;
  --butter:#FFF2C6; --butter-ink:#A07A12;
  container-type:inline-size; position:relative; width:100%;
  color:var(--ink); font-family:inherit;
}
/* scena "aperta": nessuna cornice, si fonde con lo sfondo dell'hero; le schede entrano sfumando dal bordo sinistro */
.dp-stage{ position:relative; aspect-ratio:16/9; overflow:hidden; background:transparent;
  -webkit-mask-image:linear-gradient(90deg, transparent 0, #000 9%, #000 96%, transparent 100%);
  mask-image:linear-gradient(90deg, transparent 0, #000 9%, #000 96%, transparent 100%); }
.dp-bg{ position:absolute; inset:0;
  background:
    radial-gradient(40% 50% at 47% 62%, rgba(207,241,230,.9), transparent 70%),
    radial-gradient(30% 40% at 86% 30%, rgba(230,224,255,.7), transparent 70%),
    radial-gradient(30% 40% at 8% 85%, rgba(255,225,211,.6), transparent 70%);
}
.dp-bg::after{ content:""; position:absolute; inset:0;
  background-image:radial-gradient(rgba(31,42,68,.07) 1px, transparent 1.2px); background-size:1.6cqw 1.6cqw;
  -webkit-mask-image:radial-gradient(45% 55% at 50% 55%, #000, transparent 75%); mask-image:radial-gradient(45% 55% at 50% 55%, #000, transparent 75%); }

/* intestazione e contatore centrati, sull'asse del titolo dell'hero */
.dp-head{ position:absolute; left:50%; top:3.5%; transform:translateX(-50%); display:flex; align-items:center; gap:.7cqw; white-space:nowrap;
  font:600 .9cqw/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.16em; text-transform:uppercase; color:var(--muted); }
.dp-head::before{ content:""; position:absolute; left:50%; bottom:calc(100% + .8cqw); height:2.2cqw; border-left:1.5px dashed rgba(31,42,68,.2); }
.dp-live{ width:.7cqw; height:.7cqw; border-radius:50%; background:var(--mint-ink); box-shadow:0 0 0 .35cqw rgba(47,143,122,.18); animation:dp-pulse 1.6s ease-in-out infinite; }

.dp-lines{ position:absolute; inset:0; width:100%; height:100%; fill:none; }
.dp-lines path{ stroke:#B9C6D6; stroke-width:1.4; stroke-dasharray:2 10; stroke-linecap:round; animation:dp-dash 1.2s linear infinite; vector-effect:non-scaling-stroke; opacity:.7; }
.dp-lines .dp-out{ stroke:var(--mint-ink); opacity:.5; }

/* schede-dato in ingresso */
.dp-flow{ position:absolute; inset:0; overflow:hidden;
  -webkit-mask-image:linear-gradient(90deg, transparent 0%, #000 14%, #000 92%, transparent 100%);
  mask-image:linear-gradient(90deg, transparent 0%, #000 14%, #000 92%, transparent 100%); }
.dp-card{ position:absolute; top:var(--lane); left:-18%; display:grid; grid-template-columns:auto 1fr; column-gap:.7cqw; align-items:center;
  padding:.65cqw .9cqw; min-width:12.5cqw; border-radius:.9cqw; background:#fff;
  box-shadow:0 .5cqw 1.6cqw -.6cqw rgba(31,42,68,.18), 0 0 0 1px rgba(31,42,68,.04);
  transform:translateY(-50%); opacity:0; animation:dp-flow 7s linear infinite; animation-delay:var(--delay); }
.dp-card i{ grid-row:span 2; width:1.7cqw; height:1.7cqw; border-radius:.5cqw; background:var(--tone); }
.dp-card span{ font-size:.78cqw; color:var(--muted); line-height:1.2; }
.dp-card b{ font-size:1.02cqw; font-weight:700; line-height:1.2; }
.dp-mint{--tone:var(--mint)} .dp-sky{--tone:var(--sky)} .dp-peach{--tone:var(--peach)} .dp-lavender{--tone:var(--lavender)} .dp-butter{--tone:var(--butter)}

/* scene */
.dp-scene{ position:absolute; inset:0; opacity:0; animation:dp-scene 18s ease-in-out infinite both; animation-delay:var(--delay); }
.dp-scene *{ animation-delay:var(--delay); }

.dp-count{ position:absolute; left:50%; top:8.5%; transform:translateX(-50%); display:flex; align-items:flex-end; gap:1cqw; white-space:nowrap; }
.dp-count strong{ font-family:var(--font-heading,inherit); font-weight:800; font-size:3.4cqw; line-height:.9; letter-spacing:-.03em;
  counter-reset:n var(--dp-n); --dp-n:var(--to); animation:dp-count 18s ease-out infinite both; animation-delay:var(--delay); }
.dp-count strong::after{ content:counter(n) "+"; }
.dp-count span{ font-size:.95cqw; color:var(--muted); line-height:1.3; padding-bottom:.3cqw; }

.dp-veh{ position:absolute; left:30%; width:40%; top:12%; height:70%; }
.dp-podium{ position:absolute; left:6%; right:6%; bottom:6%; height:12%; border-radius:50%;
  background:radial-gradient(closest-side, rgba(31,42,68,.16), rgba(31,42,68,.05) 60%, transparent); }
.dp-img{ position:absolute; left:50%; bottom:11%; aspect-ratio:var(--ar);
  width:min(100%, calc(36cqw * var(--ar) * .62)); max-height:78%; transform:translateX(-50%);
  animation:dp-car 18s cubic-bezier(.2,.8,.2,1) infinite both; animation-delay:var(--delay); }
.dp-img > svg, .dp-img > img{ position:absolute; inset:0; width:100%; height:100%; object-fit:contain; filter:drop-shadow(0 1.2cqw 1.2cqw rgba(31,42,68,.14)); }
.dp-kind{ position:absolute; left:50%; bottom:0; transform:translateX(-50%); font:600 .85cqw/1 ui-monospace,Menlo,monospace; letter-spacing:.18em; text-transform:uppercase; color:var(--muted);
  padding:.5cqw 1cqw; border-radius:99px; background:rgba(255,255,255,.7); }

.dp-hot{ position:absolute; width:0; height:0; opacity:0; animation:dp-hot 18s ease-out infinite both; animation-delay:calc(var(--delay) + var(--k) * .45s); }
.dp-hot > i{ position:absolute; left:-.6cqw; top:-.6cqw; width:1.2cqw; height:1.2cqw; border-radius:50%; background:#fff; box-shadow:0 0 0 .3cqw var(--mint-ink), 0 0 0 .9cqw rgba(47,143,122,.18); }
.dp-hot > div{ position:absolute; left:1.4cqw; top:-4.4cqw; white-space:nowrap; padding:.55cqw .8cqw; border-radius:.8cqw; background:#fff;
  box-shadow:0 .5cqw 1.4cqw -.6cqw rgba(31,42,68,.25); display:flex; flex-direction:column; }
.dp-hot-l > div{ left:auto; right:1.4cqw; }
.dp-hot span{ font-size:.72cqw; color:var(--muted); }
.dp-hot b{ font-size:.98cqw; }

.dp-card-out{ position:absolute; left:73.5%; width:22.5%; top:16%; padding:1.6cqw 1.5cqw; border-radius:1.6cqw; background:#fff;
  box-shadow:0 1.4cqw 3cqw -1.4cqw rgba(31,42,68,.22), 0 0 0 1px rgba(31,42,68,.05);
  animation:dp-out 18s cubic-bezier(.2,.8,.2,1) infinite both; animation-delay:var(--delay); }
.dp-label{ font:600 .78cqw/1 ui-monospace,Menlo,monospace; letter-spacing:.16em; text-transform:uppercase; color:var(--muted); }
.dp-ring{ position:relative; width:9cqw; height:9cqw; margin:1.1cqw auto .8cqw; }
.dp-ring svg{ width:100%; height:100%; transform:rotate(-90deg); }
.dp-track{ fill:none; stroke:var(--mint); stroke-width:9; }
.dp-arc{ fill:none; stroke:var(--mint-ink); stroke-width:9; stroke-linecap:round; stroke-dasharray:100; --dp-n:var(--to);
  stroke-dashoffset:calc((100 - var(--dp-n)) * 1px); animation:dp-score 18s ease-out infinite both; animation-delay:var(--delay); }
.dp-ring strong{ position:absolute; inset:0; display:grid; place-items:center; font-family:var(--font-heading,inherit); font-weight:800; font-size:2.9cqw;
  counter-reset:n var(--dp-n); --dp-n:var(--to); animation:dp-score 18s ease-out infinite both; animation-delay:var(--delay); }
.dp-ring strong::after{ content:counter(n); }
.dp-name{ text-align:center; font-weight:700; font-size:1.15cqw; margin-bottom:1cqw; }
.dp-card-out ul{ list-style:none; margin:0; padding:0; display:grid; gap:.55cqw; }
.dp-card-out li{ display:flex; align-items:center; gap:.6cqw; font-size:.9cqw; line-height:1.25; padding:.5cqw .6cqw; border-radius:.7cqw; background:#F6FAF8;
  opacity:0; animation:dp-li 18s ease-out infinite both; animation-delay:calc(var(--delay) + var(--k) * .35s); }
.dp-card-out li i{ flex:none; display:grid; place-items:center; width:1.4cqw; height:1.4cqw; border-radius:50%; font-style:normal; font-size:.8cqw; font-weight:800;
  background:var(--mint); color:var(--mint-ink); }
.dp-card-out li.dp-trade{ background:#FFF7F2; }
.dp-card-out li.dp-trade i{ background:var(--peach); color:var(--peach-ink); }

/* pausa fuori schermo */
.dp-paused, .dp-paused *, .dp-paused *::after{ animation-play-state:paused !important; }

/* ------------ keyframes (ciclo 18 s, ogni scena vive nel primo terzo) ------------ */
@keyframes dp-pulse{ 0%,100%{opacity:1} 50%{opacity:.35} }
@keyframes dp-dash{ to{ stroke-dashoffset:-12; } }
@keyframes dp-flow{
  0%{ left:-18%; opacity:0; transform:translateY(-50%) scale(1); }
  10%{ opacity:1; }
  50%{ opacity:1; transform:translateY(calc(-50% + var(--dy) * .45)) scale(.95); }
  72%{ left:21%; opacity:0; transform:translateY(calc(-50% + var(--dy) * .9)) scale(.7); }
  100%{ left:21%; opacity:0; }
}
@keyframes dp-scene{ 0%{opacity:0} 2.5%{opacity:1} 31%{opacity:1} 33.3%,100%{opacity:0} }
@keyframes dp-car{ 0%{ transform:translateX(-38%); opacity:0 } 5%{ transform:translateX(-50%); opacity:1 } 30%{ transform:translateX(-50%); opacity:1 } 33.3%,100%{ transform:translateX(-62%); opacity:0 } }
@keyframes dp-hot{ 0%,7%{ opacity:0; transform:scale(.6) } 9%,31%{ opacity:1; transform:scale(1) } 33.3%,100%{ opacity:0 } }
@keyframes dp-count{ 0%,2%{ --dp-n:0 } 14%,100%{ --dp-n:var(--to) } }
@keyframes dp-out{ 0%,8%{ opacity:0; transform:translateY(1.5cqw) } 11%,31%{ opacity:1; transform:none } 33.3%,100%{ opacity:0; transform:translateY(-1cqw) } }
@keyframes dp-score{ 0%,9%{ --dp-n:0 } 17%,100%{ --dp-n:var(--to) } }
@keyframes dp-li{ 0%,14%{ opacity:0; transform:translateX(1cqw) } 16%,31%{ opacity:1; transform:none } 33.3%,100%{ opacity:0 } }

/* ------------ mobile: 4:5 verticale ------------ */
@container (max-width: 640px){
  .dp-stage{ aspect-ratio:4/5; -webkit-mask-image:none; mask-image:none; }
  .dp-head{ font-size:2.4cqw; top:4%; left:5%; transform:none; }
  .dp-live{ width:1.8cqw; height:1.8cqw; }
  .dp-head::before{ display:none; }
  .dp-lines{ display:none; }
  .dp-card{ top:15%; padding:1.6cqw 2.2cqw; min-width:34cqw; border-radius:2.4cqw; column-gap:1.8cqw; animation-name:dp-flow-m; animation-duration:16s; animation-delay:var(--mdelay); }
  .dp-card:not(:nth-child(3n+1)){ display:none; }
  .dp-card i{ width:4.4cqw; height:4.4cqw; border-radius:1.2cqw; }
  .dp-card span{ font-size:2.2cqw; } .dp-card b{ font-size:2.8cqw; }
  .dp-count{ left:auto; right:5%; top:3%; gap:1.6cqw; transform:none; }
  .dp-count strong{ font-size:6cqw; } .dp-count span{ display:none; }
  .dp-veh{ left:5%; width:90%; top:24%; height:36%; }
  .dp-img{ width:min(100%, calc(30cqw * var(--ar))); }
  .dp-kind{ font-size:2.2cqw; padding:1cqw 2.4cqw; }
  .dp-hot > i{ width:2.6cqw; height:2.6cqw; left:-1.3cqw; top:-1.3cqw; }
  .dp-hot > div{ top:-9cqw; left:2.6cqw; padding:1.2cqw 1.8cqw; border-radius:2cqw; }
  .dp-hot-l > div{ left:auto; right:2.6cqw; }
  .dp-hot-edge > div{ left:2.6cqw; right:auto; }
  .dp-hot span{ font-size:2cqw; } .dp-hot b{ font-size:2.5cqw; }
  .dp-card-out{ left:5%; width:90%; top:62%; padding:3cqw 4cqw; border-radius:4cqw; display:grid; grid-template-columns:auto 1fr; column-gap:4cqw; align-items:center; }
  .dp-label{ grid-column:1 / -1; font-size:2.1cqw; }
  .dp-ring{ width:20cqw; height:20cqw; margin:2cqw 0; grid-row:span 2; }
  .dp-ring strong{ font-size:7cqw; }
  .dp-name{ text-align:left; font-size:3.2cqw; margin:0; align-self:end; }
  .dp-card-out ul{ gap:1.2cqw; align-self:start; margin-top:1.6cqw; }
  .dp-card-out li{ font-size:2.5cqw; padding:1cqw 1.4cqw; border-radius:1.8cqw; gap:1.6cqw; }
  .dp-card-out li:nth-child(n+3):not(.dp-trade){ display:none; }
  .dp-card-out li i{ width:3.6cqw; height:3.6cqw; font-size:2cqw; }
}
@keyframes dp-flow-m{
  0%{ left:100%; opacity:0; transform:translateY(-50%); }
  8%{ opacity:1; } 85%{ opacity:1; }
  100%{ left:-40%; opacity:0; transform:translateY(-50%); }
}

/* ------------ riduci movimento: auto ferma, completa ------------ */
@media (prefers-reduced-motion: reduce){
  .dp *, .dp *::after{ animation:none !important; }
  .dp-scene{ opacity:0; } .dp-scene[data-i="0"]{ opacity:1; }
  .dp-card{ opacity:1; left:3%; }
  .dp-card:nth-child(n+7){ display:none; }
  .dp-hot, .dp-card-out li{ opacity:1; }
}

/* leggibilità: nessun testo sotto i 12 px */
.dp-head{ font-size:max(12px, .9cqw); }
.dp-card span, .dp-label{ font-size:max(12px, .78cqw); }
.dp-card b, .dp-hot b{ font-size:max(13px, 1.02cqw); }
.dp-count span, .dp-card-out li{ font-size:max(13px, .95cqw); }
.dp-kind{ font-size:max(12px, .85cqw); }
.dp-hot span{ font-size:max(12px, .72cqw); }
@container (max-width: 640px){
  .dp-head, .dp-card span, .dp-kind, .dp-hot span, .dp-label{ font-size:max(12px, 2.2cqw); }
  .dp-card b, .dp-hot b, .dp-card-out li{ font-size:max(13px, 2.8cqw); }
  .dp-name{ font-size:max(13px, 3.2cqw); }
}
`;
