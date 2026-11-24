import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { PastelCar, PastelMoto, PastelScooter } from "./PastelVehicles";
import { getStoryPick, subscribeStoryPick, type StoryPick, type StoryVehicle } from "./storyStore";

/**
 * Vignetta 16:9 "Il ciclo di vita" (My DriveWise) — capitolo 2 della storia.
 * Il protagonista è il veicolo scelto nel capitolo 1 (WeightsVignette, via storyStore):
 * station wagon, moto o scooter percorre una strada-timeline dal mese 0 al mese 36 e
 * a ogni tappa si accende una card di My DriveWise.
 * - Se nel capitolo 1 cambia profilo, il nuovo veicolo entra al giro successivo (mai a metà).
 * - Animazione solo CSS, loop di 16 s; in pausa quando non è visibile.
 * - prefers-reduced-motion: scena finale ferma con tutte le card.
 * - Sotto i 640 px: timeline verticale, senza veicolo.
 * Dati illustrativi; le funzioni mostrate sono in arrivo in My DriveWise.
 */

type Vars = CSSProperties & Record<`--${string}`, string | number>;
type Stop = { x: number; month: string; area: string; tone: string; title: string; body: ReactNode; upcoming?: boolean };

const RIDE: Record<
  StoryVehicle,
  { name: string; label: string; art: ReactNode; ar: number; h: number; cost: string; bars: number[]; service: string; rows: [string, string]; offers: string; gain: string; residual: string }
> = {
  auto: {
    name: "Station wagon",
    label: "La tua station wagon",
    art: <PastelCar />,
    ar: 320 / 115,
    h: 5,
    cost: "214 €",
    bars: [38, 62, 45, 70, 52, 58],
    service: "Tagliando tra 1.200 km",
    rows: ["Pneumatici · tra 4 mesi", "Revisione · mar 2027"],
    offers: "3 offerte più convenienti",
    gain: "+17%",
    residual: "21.400 €",
  },
  moto: {
    name: "Naked 700 cc",
    label: "La tua moto",
    art: <PastelMoto />,
    ar: 190 / 124,
    h: 7,
    cost: "92 €",
    bars: [30, 55, 70, 40, 64, 48],
    service: "Tagliando tra 1.000 km",
    rows: ["Kit catena · tra 5 mesi", "Gomme · tra 3.000 km"],
    offers: "4 offerte più convenienti",
    gain: "+9%",
    residual: "5.300 €",
  },
  scooter: {
    name: "Scooter 300 cc",
    label: "Il tuo scooter",
    art: <PastelScooter />,
    ar: 176 / 162,
    h: 7.2,
    cost: "46 €",
    bars: [44, 40, 52, 46, 38, 42],
    service: "Tagliando tra 800 km",
    rows: ["Cinghia · tra 6 mesi", "Revisione · tra 4 anni"],
    offers: "2 offerte più convenienti",
    gain: "+12%",
    residual: "3.100 €",
  },
};

function stopsFor(pick: StoryPick): Stop[] {
  const r = RIDE[pick.vehicle];
  const saved = pick.vehicle === "scooter" ? "salvato" : "salvata";
  return [
    {
      x: 11,
      month: "Mese 0",
      area: "Garage",
      tone: "mint",
      title: `${r.name} ${saved}`,
      body: (
        <span className="lv-score">
          <b>{pick.score}</b> Decision Score
        </span>
      ),
    },
    {
      x: 30.5,
      month: "Mese 2",
      area: "Spese",
      upcoming: true,
      tone: "butter",
      title: `Spesa del mese: ${r.cost}`,
      body: (
        <span className="lv-bars" aria-hidden>
          {r.bars.map((h, i) => (
            <i key={i} style={{ height: `${h}%` }} />
          ))}
        </span>
      ),
    },
    {
      x: 50,
      month: "Mese 11",
      area: "Manutenzione",
      upcoming: true,
      tone: "sky",
      title: r.service,
      body: (
        <span className="lv-rows">
          <em>{r.rows[0]}</em>
          <em>{r.rows[1]}</em>
        </span>
      ),
    },
    {
      x: 69.5,
      month: "Mese 14",
      area: "Assicurazione",
      tone: "peach",
      title: "Polizza RC in scadenza",
      body: (
        <span className="lv-rows">
          <em>{r.offers}</em>
        </span>
      ),
    },
    {
      x: 89,
      month: "Mese 36",
      area: "Mercato",
      upcoming: true,
      tone: "lavender",
      title: "Un nuovo modello ti conviene",
      body: (
        <span className="lv-rows">
          <em>
            <b>{r.gain}</b> sul tuo Decision Score
          </em>
          <em>Valore residuo stimato: {r.residual}</em>
        </span>
      ),
    },
  ];
}

export function LifecycleVignette({ className = "" }: { className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [pick, setPick] = useState<StoryPick>(getStoryPick);
  const visible = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    const io = new IntersectionObserver(([e]) => {
      if (!e) return;
      visible.current = e.isIntersecting;
      el.classList.toggle("lv-paused", !e.isIntersecting);
      if (e.isIntersecting) setPick(getStoryPick()); // entra in scena col veicolo scelto
    });
    io.observe(el);
    // fuori schermo (o senza animazioni) il cambio è immediato; altrimenti aspetta il giro successivo
    const unsub = subscribeStoryPick((p) => {
      if (!visible.current || reduce.matches) setPick(p);
    });
    return () => {
      io.disconnect();
      unsub();
    };
  }, []);

  const r = RIDE[pick.vehicle];
  const stops = stopsFor(pick);

  return (
    <div
      ref={ref}
      className={`lv ${className}`}
      role="img"
      aria-label={`Dopo la scelta, My DriveWise accompagna ${r.label.toLowerCase()} nel tempo: lo salva nel Garage, tiene traccia delle spese, ricorda tagliandi e scadenze, confronta le polizze e avvisa quando un nuovo modello conviene di più.`}
    >
      <style>{CSS}</style>
      {/* key: a ogni cambio di veicolo l'animazione riparte da capo */}
      <div className="lv-stage" key={`${pick.vehicle}-${pick.score}`}>
        {/* orologio invisibile: a fine giro prende l'eventuale nuovo veicolo dal capitolo 1 */}
        <span className="lv-clock" aria-hidden onAnimationIteration={() => setPick(getStoryPick())} />

        <div className="lv-head" aria-hidden>
          <div>
            <span className="lv-brand">My DriveWise</span>
            <span className="lv-hello">
              {r.label}, nel tempo · <em>profilo {pick.profile}</em>
            </span>
          </div>
          <div className="lv-month">
            <small>Mese</small>
            <strong />
          </div>
        </div>

        {stops.map((s, i) => (
          <div key={s.area} className={`lv-card lv-${s.tone} lv-t${i}`} style={{ "--x": `${s.x}%` } as Vars} aria-hidden>
            <div className="lv-ctop">
              <span className="lv-area">{s.area}</span>
              <span className="lv-m">{s.month}</span>
            </div>
            {s.upcoming && <span className="self-start rounded-full border border-border bg-background px-2 py-0.5 text-xs font-semibold text-muted-foreground">In arrivo</span>}
            <b className="lv-title">{s.title}</b>
            {s.body}
          </div>
        ))}

        <div className="lv-road" aria-hidden>
          <span className="lv-lane" />
          <span className="lv-fill" />
          {stops.map((s, i) => (
            <span key={s.area} className={`lv-dot lv-${s.tone} lv-t${i}`} style={{ "--x": `${s.x}%` } as Vars} />
          ))}
        </div>
        <div className="lv-car" style={{ "--ar": r.ar, "--h": `${r.h}cqw` } as Vars} aria-hidden>
          {r.art}
        </div>
      </div>
    </div>
  );
}

/* Ciclo di 16 s. L'auto si ferma sotto ogni tappa; le card restano accese fino alla fine. */
const CSS = `
@property --lv-m { syntax: "<integer>"; inherits: false; initial-value: 0; }
.lv{ --ink:#1F2A44; --muted:#5E6A82;
  --mint:#CFF1E6; --mint-ink:#257A67; --sky:#DCEEFF; --sky-ink:#336AA8; --peach:#FFE1D3; --peach-ink:#A4532F;
  --lavender:#E6E0FF; --lavender-ink:#6B5BD6; --butter:#FFF2C6; --butter-ink:#A07A12;
  container-type:inline-size; position:relative; width:100%; color:var(--ink); font-family:inherit; }
.lv-stage{ position:relative; aspect-ratio:16/9; overflow:hidden; border-radius:2.2cqw;
  background:
    radial-gradient(35% 40% at 15% 25%, rgba(207,241,230,.8), transparent 70%),
    radial-gradient(35% 40% at 85% 25%, rgba(230,224,255,.75), transparent 70%),
    radial-gradient(50% 40% at 50% 100%, rgba(255,242,198,.55), transparent 70%),
    linear-gradient(180deg,#F7FAF9,#FAF8F4);
  box-shadow:0 2cqw 6cqw -3cqw rgba(31,42,68,.18), inset 0 0 0 1px rgba(31,42,68,.06); }

.lv-head{ position:absolute; left:3%; right:3%; top:5%; display:flex; justify-content:space-between; align-items:flex-start; }
.lv-brand{ display:block; font-family:var(--font-heading,inherit); font-weight:800; font-size:1.6cqw; }
.lv-hello{ display:block; font-size:.95cqw; color:var(--muted); margin-top:.3cqw; }
.lv-hello em{ font-style:normal; color:var(--mint-ink); }
.lv-clock{ position:absolute; width:0; height:0; animation:lv-clock 16s linear infinite; }
@keyframes lv-clock{ to{ opacity:1 } }
.lv-month{ text-align:right; }
.lv-month small{ display:block; font:600 .8cqw/1 ui-monospace,Menlo,monospace; letter-spacing:.16em; text-transform:uppercase; color:var(--muted); }
.lv-month strong{ font-family:var(--font-heading,inherit); font-weight:800; font-size:3.4cqw; line-height:1; counter-reset:m var(--lv-m); --lv-m:36; animation:lv-month 16s linear infinite both; }
.lv-month strong::after{ content:counter(m); }

/* card */
.lv-card{ position:absolute; top:21%; left:calc(var(--x) - 8.6%); width:17.2%; min-height:30%; padding:1.2cqw 1.2cqw 1.3cqw; border-radius:1.4cqw; background:#fff;
  box-shadow:0 1cqw 2.6cqw -1.2cqw rgba(31,42,68,.22), 0 0 0 1px rgba(31,42,68,.05);
  display:flex; flex-direction:column; gap:.7cqw;
  animation:lv-card 16s cubic-bezier(.2,.8,.2,1) infinite both; }
.lv-card::after{ content:""; position:absolute; left:50%; top:100%; width:0; height:16cqw; border-left:1.5px dashed rgba(31,42,68,.18); }
.lv-ctop{ display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:.5cqw; }
.lv-area{ font-size:.72cqw; font-weight:700; padding:.3cqw .6cqw; border-radius:99px; background:var(--tone); color:var(--tone-ink); white-space:nowrap; }
.lv-m{ font:600 .7cqw/1 ui-monospace,Menlo,monospace; color:var(--muted); white-space:nowrap; }
.lv-title{ font-size:1.05cqw; line-height:1.25; }
.lv-score{ display:flex; align-items:baseline; gap:.5cqw; font-size:.85cqw; color:var(--muted); }
.lv-score b{ font-family:var(--font-heading,inherit); font-size:2.2cqw; color:var(--mint-ink); }
.lv-bars{ display:flex; align-items:flex-end; gap:.35cqw; height:3cqw; }
.lv-bars i{ flex:1; border-radius:.3cqw .3cqw 0 0; background:var(--tone); }
.lv-bars i:last-child{ background:var(--tone-ink); opacity:.7; }
.lv-rows{ display:grid; gap:.4cqw; }
.lv-rows em{ font-style:normal; font-size:.8cqw; color:var(--muted); padding:.4cqw .6cqw; border-radius:.6cqw; background:#F6F8FA; }
.lv-rows em b{ color:var(--tone-ink); }
.lv-mint{ --tone:var(--mint); --tone-ink:var(--mint-ink); } .lv-sky{ --tone:var(--sky); --tone-ink:var(--sky-ink); }
.lv-peach{ --tone:var(--peach); --tone-ink:var(--peach-ink); } .lv-lavender{ --tone:var(--lavender); --tone-ink:var(--lavender-ink); }
.lv-butter{ --tone:var(--butter); --tone-ink:var(--butter-ink); }

/* strada */
.lv-road{ position:absolute; left:3%; right:3%; top:78%; height:7%; border-radius:99px; background:rgba(255,255,255,.75); box-shadow:inset 0 0 0 1px rgba(31,42,68,.06); }
.lv-lane{ position:absolute; left:2%; right:2%; top:50%; border-top:2px dashed rgba(31,42,68,.14); }
.lv-fill{ position:absolute; left:0; top:0; bottom:0; border-radius:99px; background:linear-gradient(90deg, rgba(207,241,230,.9), rgba(230,224,255,.9)); animation:lv-fill 16s cubic-bezier(.45,0,.2,1) infinite both; }
.lv-dot{ position:absolute; top:50%; left:calc((var(--x) - 3%) / .94); width:1.4cqw; height:1.4cqw; margin:-.7cqw 0 0 -.7cqw; border-radius:50%; background:#fff;
  box-shadow:0 0 0 .3cqw var(--tone-ink), 0 0 0 .9cqw var(--tone); animation:lv-dot 16s ease-out infinite both; }
.lv-car{ position:absolute; top:auto; bottom:calc(100% - 82.5%); height:var(--h); aspect-ratio:var(--ar); margin-left:calc(var(--h) * var(--ar) / -2); left:11%; filter:drop-shadow(0 .8cqw .8cqw rgba(31,42,68,.14)); animation:lv-car 16s cubic-bezier(.45,0,.2,1) infinite both; }
.lv-car svg{ width:100%; height:100%; display:block; }

.lv-paused, .lv-paused *, .lv-paused *::after{ animation-play-state:paused !important; }

/* tempi delle card e dei punti: ognuno si accende quando arriva l'auto */
.lv-t0{ animation-name:lv-on-3; }
.lv-t1{ animation-name:lv-on-21; }
.lv-t2{ animation-name:lv-on-39; }
.lv-t3{ animation-name:lv-on-57; }
.lv-t4{ animation-name:lv-on-75; }
@keyframes lv-on-3 { 0%,2%{opacity:0; transform:translateY(1cqw) scale(.96)} 6%,92%{opacity:1; transform:none} 98%,100%{opacity:0} }
@keyframes lv-on-21{ 0%,20%{opacity:0; transform:translateY(1cqw) scale(.96)} 24%,92%{opacity:1; transform:none} 98%,100%{opacity:0} }
@keyframes lv-on-39{ 0%,38%{opacity:0; transform:translateY(1cqw) scale(.96)} 42%,92%{opacity:1; transform:none} 98%,100%{opacity:0} }
@keyframes lv-on-57{ 0%,56%{opacity:0; transform:translateY(1cqw) scale(.96)} 60%,92%{opacity:1; transform:none} 98%,100%{opacity:0} }
@keyframes lv-on-75{ 0%,74%{opacity:0; transform:translateY(1cqw) scale(.96)} 78%,92%{opacity:1; transform:none} 98%,100%{opacity:0} }

/* auto: ferma a ogni tappa (x = 11, 30.5, 50, 69.5, 89) */
@keyframes lv-car{
  0%{ left:-10%; opacity:0 } 3%{ left:11%; opacity:1 }
  12%{ left:11% } 20%{ left:30.5% }
  30%{ left:30.5% } 38%{ left:50% }
  48%{ left:50% } 56%{ left:69.5% }
  66%{ left:69.5% } 74%{ left:89%; opacity:1 }
  92%{ left:89%; opacity:1 } 100%{ left:89%; opacity:0 }
}
@keyframes lv-fill{
  0%,3%{ width:8.5% } 12%{ width:8.5% } 20%{ width:29% } 30%{ width:29% } 38%{ width:50% }
  48%{ width:50% } 56%{ width:71% } 66%{ width:71% } 74%,92%{ width:91.5%; opacity:1 } 100%{ width:91.5%; opacity:0 }
}
@keyframes lv-month{
  0%,12%{ --lv-m:0 } 20%,30%{ --lv-m:2 } 38%,48%{ --lv-m:11 } 56%,66%{ --lv-m:14 } 74%,100%{ --lv-m:36 }
}

/* mobile: timeline verticale */
@container (max-width: 640px){
  .lv-stage{ aspect-ratio:auto; padding:6cqw 5cqw 6cqw 5cqw; border-radius:5cqw; display:flex; flex-direction:column; gap:3.4cqw; }
  .lv-head{ position:static; margin-bottom:2cqw; }
  .lv-brand{ font-size:5cqw; } .lv-hello{ font-size:3cqw; }
  .lv-month small{ font-size:2.4cqw; } .lv-month strong{ font-size:9cqw; }
  .lv-card{ position:relative; top:auto; left:auto; width:auto; min-height:0; margin-left:9cqw; padding:3.4cqw; border-radius:3.6cqw; gap:2cqw; }
  .lv-card::after{ display:none; }
  .lv-card::before{ content:""; position:absolute; left:-7cqw; top:4.2cqw; width:3.6cqw; height:3.6cqw; border-radius:50%; background:#fff; box-shadow:0 0 0 .8cqw var(--tone-ink), 0 0 0 2.2cqw var(--tone); }
  .lv-stage::before{ content:""; position:absolute; left:calc(5cqw + 3.8cqw); top:30cqw; bottom:10cqw; border-left:2px dashed rgba(31,42,68,.16); }
  .lv-area{ font-size:2.4cqw; padding:1cqw 2cqw; } .lv-m{ font-size:2.3cqw; }
  .lv-title{ font-size:3.6cqw; }
  .lv-score{ font-size:2.8cqw; } .lv-score b{ font-size:7cqw; }
  .lv-bars{ height:9cqw; gap:1.2cqw; }
  .lv-rows{ gap:1.4cqw; } .lv-rows em{ font-size:2.8cqw; padding:1.4cqw 2cqw; border-radius:2cqw; }
  .lv-road, .lv-car{ display:none; }
}

@media (prefers-reduced-motion: reduce){
  .lv *, .lv *::after{ animation:none !important; }
  .lv-car{ left:89%; }
  .lv-fill{ width:91.5%; }
}

/* leggibilità: nessun testo sotto i 12 px */
.lv-hello, .lv-score, .lv-rows em{ font-size:max(13px, .9cqw); }
.lv-month small, .lv-area, .lv-m{ font-size:max(12px, .78cqw); }
.lv-title{ font-size:max(13px, 1.05cqw); }
@container (max-width: 640px){
  .lv-hello, .lv-month small, .lv-area, .lv-m, .lv-score, .lv-rows em{ font-size:max(12px, 2.8cqw); }
  .lv-hello, .lv-score, .lv-rows em{ font-size:max(13px, 2.8cqw); }
}
`;