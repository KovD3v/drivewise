import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { PastelCar, PastelMoto, PastelScooter } from "./PastelVehicles";
import { setStoryPick } from "./storyStore";

/**
 * Vignetta 16:9 "Dalle tue domande alla scelta": una sola storia, ripetuta per 3 profili.
 * 1) chi sei: il profilo si accende (o lo scegli tu con un clic);
 * 2) cosa ti chiederesti: 9 domande concrete per quel profilo, una scansione le verifica
 *    e ogni "?" si gira nella risposta (✓ ok, ! attenzione);
 * 3) le righe si ribaltano come un tabellone delle partenze e diventano i 9 criteri,
 *    con il peso giusto per quel profilo;
 * 4) la classifica si riordina e in cima va il mezzo giusto.
 * - Orologio interno che avanza solo quando la vignetta è visibile (le animazioni CSS si
 *   mettono in pausa insieme), e si ferma 15 s dopo un clic su "Domande"/"Criteri".
 * - prefers-reduced-motion: niente loop né animazioni, si parte dai criteri; profili e
 *   interruttore Domande/Criteri restano cliccabili.
 * - Sotto i 640 px di larghezza il layout diventa verticale.
 * - Capitolo 1 della storia: il veicolo in cima viene passato a LifecycleVignette (capitolo 2)
 *   tramite storyStore.
 * Domande, risposte, pesi e punteggi sono esempi illustrativi.
 */

type Key =
  | "costi"
  | "sicurezza"
  | "manutenzione"
  | "comfort"
  | "affidabilita"
  | "richiami"
  | "svalutazione"
  | "dna"
  | "compat";
type VKey = "auto" | "moto" | "scooter";
type Check = { q: string; a: string; warn?: boolean };
type Phase = "ask" | "weigh";

const CRITERIA: { key: Key; name: string; desc: string }[] = [
  {
    key: "costi",
    name: "Costi reali",
    desc: "Acquisto, consumi, assicurazione e bollo su base annua",
  },
  { key: "sicurezza", name: "Sicurezza", desc: "Dotazioni attive e passive, esiti nei test" },
  { key: "manutenzione", name: "Manutenzione", desc: "Intervalli, costi dei tagliandi e ricambi" },
  { key: "comfort", name: "Comfort", desc: "Ergonomia, rumorosità e uso quotidiano" },
  {
    key: "affidabilita",
    name: "Affidabilità",
    desc: "Guasti ricorrenti e comportamento nel tempo",
  },
  { key: "richiami", name: "Richiami", desc: "Campagne ufficiali registrate sul modello" },
  { key: "svalutazione", name: "Svalutazione", desc: "Tenuta del valore residuo nel tempo" },
  { key: "dna", name: "Carta d'identità del veicolo", desc: "Identità tecnica e vocazione d'uso" },
  { key: "compat", name: "Compatibilità", desc: "Quanto aderisce al tuo profilo reale" },
];

type Profile = {
  id: string;
  name: string;
  tone: string;
  chips: string[];
  checks: Check[];
  weights: Record<Key, number>;
  scores: Record<VKey, number>;
  why: string[];
};

const PROFILES: [Profile, ...Profile[]] = [
  {
    id: "famiglia",
    name: "Famiglia in città",
    tone: "var(--wv-mint)",
    chips: ["2 bambini", "Box 4,8 m", "12.000 km/anno"],
    checks: [
      { q: "Entra nel tuo box, specchietti compresi?", a: "Sì · 12 cm di margine" },
      { q: "Il passeggino entra senza smontarlo?", a: "Sì · 608 L di bagagliaio" },
      { q: "Tre seggiolini affiancati dietro?", a: "Solo 2 + 1 stretto", warn: true },
      { q: "Quanti posti Isofix ci sono davvero?", a: "3 posti" },
      { q: "Potrà entrare in città nei prossimi anni?", a: "Sì · Euro 6e" },
      { q: "Quanto paghi di bollo nella tua regione?", a: "212 €/anno" },
      { q: "Ci sono richiami aperti su questo anno?", a: "Nessuno aperto" },
      { q: "Quanto consuma davvero in città?", a: "5,1 l/100 km reali" },
      { q: "Quanto costa il tagliando fuori garanzia?", a: "≈ 260 €" },
    ],
    weights: {
      costi: 80,
      sicurezza: 92,
      manutenzione: 55,
      comfort: 72,
      affidabilita: 86,
      richiami: 50,
      svalutazione: 45,
      dna: 38,
      compat: 95,
    },
    scores: { auto: 88, scooter: 54, moto: 41 },
    why: [
      "5 posti e bagagliaio da 608 L",
      "Entra nel box da 4,8 m",
      "Sicurezza al top della categoria",
    ],
  },
  {
    id: "pendolare",
    name: "Pendolare in tangenziale",
    tone: "var(--wv-peach)",
    chips: ["Da solo", "25 km al giorno", "Parcheggio difficile"],
    checks: [
      { q: "Puoi fare tangenziale e autostrada?", a: "Sì · oltre i 150 cc" },
      { q: "Ti basta la patente B?", a: "No · serve la A2", warn: true },
      { q: "Ci sta un casco integrale nel sottosella?", a: "Sì · uno integrale" },
      { q: "Il parabrezza ti ripara d'inverno?", a: "Basso · meglio quello alto", warn: true },
      { q: "Le ruote reggono le buche in città?", a: "Sì · anteriore da 15″" },
      { q: "C'è una presa per il navigatore?", a: "Sì · USB-C nel retroscudo" },
      { q: "Quanto consuma nel tuo tragitto?", a: "≈ 0,9 l al giorno" },
      { q: "Quanto costano tagliando e cinghia?", a: "≈ 190 € ogni 10.000 km" },
      { q: "Quanto paghi di RC alla tua età?", a: "≈ 210 €/anno" },
    ],
    weights: {
      costi: 92,
      sicurezza: 62,
      manutenzione: 74,
      comfort: 55,
      affidabilita: 76,
      richiami: 40,
      svalutazione: 52,
      dna: 66,
      compat: 90,
    },
    scores: { scooter: 91, auto: 72, moto: 66 },
    why: [
      "Costi d'uso più bassi del gruppo",
      "Parcheggia ovunque",
      "Oltre 150 cc: ok in tangenziale",
    ],
  },
  {
    id: "weekend",
    name: "Motociclista nel weekend",
    tone: "var(--wv-lavender)",
    chips: ["Patente A", "Gite fuori porta", "Alto 1,78 m"],
    checks: [
      { q: "Arrivi a terra con entrambi i piedi?", a: "Sì · sella a 805 mm" },
      { q: "La sposti a mano in garage?", a: "189 kg · serve attenzione", warn: true },
      { q: "Il passeggero regge 200 km?", a: "Sella posteriore corta", warn: true },
      { q: "Ha ABS in curva e controllo di trazione?", a: "Entrambi di serie" },
      { q: "Quanta strada fai con un pieno?", a: "≈ 300 km" },
      { q: "Quanto costa un treno di gomme?", a: "≈ 280 €" },
      { q: "Ogni quanto il controllo valvole?", a: "Ogni 24.000 km" },
      { q: "Si montano le borse laterali?", a: "Sì · telaietti originali" },
      { q: "Quanto vale tra 3 anni?", a: "≈ 68% del prezzo" },
    ],
    weights: {
      costi: 48,
      sicurezza: 76,
      manutenzione: 44,
      comfort: 60,
      affidabilita: 70,
      richiami: 55,
      svalutazione: 62,
      dna: 96,
      compat: 92,
    },
    scores: { moto: 87, scooter: 63, auto: 49 },
    why: [
      "Vocazione da strade extraurbane",
      "Sella adatta a 1,78 m",
      "Tiene bene il valore nel tempo",
    ],
  },
];

const VEHICLES: Record<VKey, { name: string; kind: string; art: ReactNode }> = {
  auto: { name: "Station wagon", kind: "Auto", art: <PastelCar /> },
  moto: { name: "Naked 700 cc", kind: "Moto", art: <PastelMoto /> },
  scooter: { name: "Scooter 300 cc", kind: "Scooter", art: <PastelScooter /> },
};

type Vars = CSSProperties & Record<`--${string}`, string | number>;
const TICK = 100;
const WEIGH_AT = 5800; // ms: le domande diventano criteri
const CYCLE = 12500; // ms: durata di un profilo

/**
 * Copione del cursore "finto" che usa la vignetta come un utente (effetto navigazione):
 * gli istanti sono allineati all'orologio, così il clic arriva un attimo prima del cambio.
 * `to`: p:active / p:next = profilo, q1..q8 = riga domanda, sw = interruttore "Criteri",
 * top = punteggio del primo in classifica (lì si apre il tooltip).
 */
type Frame = { t: number; to: string; click?: boolean; tip?: boolean };
const SCRIPT: Frame[] = [
  { t: 0, to: "p:active" },
  { t: 1300, to: "q1" },
  { t: 2300, to: "q3" },
  { t: 3300, to: "q5" },
  { t: 4300, to: "q7" },
  { t: 5000, to: "sw" },
  { t: 5600, to: "sw", click: true },
  { t: 7300, to: "top" },
  { t: 8000, to: "top", tip: true },
  { t: 11100, to: "p:next" },
  { t: 12100, to: "p:next", click: true },
];
// punto da indicare dentro ogni bersaglio, in frazioni della sua larghezza/altezza
const AIM: Record<string, [number, number]> = {
  p: [0.78, 0.38],
  q: [0.7, 0.55],
  sw: [0.5, 0.6],
  top: [0.9, 0.16],
};

export function WeightsVignette({
  ctaHref = "/app/start",
  nextHref = "#dopo-la-scelta",
  className = "",
}: {
  ctaHref?: string;
  nextHref?: string;
  className?: string;
}) {
  const [active, setActive] = useState(0); // profilo acceso
  const [weighed, setWeighed] = useState(0); // profilo di cui mostriamo criteri e classifica
  const [phase, setPhase] = useState<Phase>("ask");
  const [cycle, setCycle] = useState(0); // fa ripartire barre e animazioni
  const ref = useRef<HTMLDivElement>(null);
  const elapsed = useRef(0);
  const holdUntil = useRef(0);
  const visible = useRef(false);
  const still = useRef(false);
  const activeRef = useRef(0);
  const cursorRef = useRef<HTMLSpanElement>(null);
  const frameRef = useRef(-1);
  const cursorOffUntil = useRef(0);
  const [hoverRow, setHoverRow] = useState(-1);
  const [tip, setTip] = useState(false);

  const aimAt = (to: string) => {
    const root = ref.current;
    const cur = cursorRef.current;
    const stage = root?.querySelector<HTMLElement>(".wv-stage");
    if (!root || !cur || !stage) return;
    const n = PROFILES.length;
    const key =
      to === "p:active"
        ? `p${activeRef.current}`
        : to === "p:next"
          ? `p${(activeRef.current + 1) % n}`
          : to;
    const target = root.querySelector<HTMLElement>(`[data-cur="${key}"]`);
    if (!target) return;
    const sr = stage.getBoundingClientRect();
    const tr = target.getBoundingClientRect();
    const k = sr.width / (stage.offsetWidth || 1); // tiene conto dello scale dello scroll
    const [fx, fy] = AIM[key.replace(/\d+$/, "")] ?? [0.5, 0.5];
    const x = (tr.left - sr.left + tr.width * fx) / k;
    const y = (tr.top - sr.top + tr.height * fy) / k;
    cur.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
  };

  const runScript = (ms: number) => {
    const cur = cursorRef.current;
    let i = -1;
    for (let j = 0; j < SCRIPT.length; j++) if ((SCRIPT[j]?.t ?? Infinity) <= ms) i = j;
    if (i === frameRef.current) return;
    frameRef.current = i;
    const f = SCRIPT[i];
    if (!f || !cur) return;
    aimAt(f.to);
    setHoverRow(f.to.startsWith("q") ? Number(f.to.slice(1)) : -1);
    setTip(f.tip === true);
    if (f.click) {
      cur.classList.remove("is-click");
      void cur.offsetWidth; // fa ripartire l'animazione del clic
      cur.classList.add("is-click");
    }
  };

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    still.current = reduce.matches;
    if (reduce.matches) setPhase("weigh");
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e) return;
        // il racconto parte (e si ferma) quando la vignetta è visibile per almeno un terzo
        visible.current = e.intersectionRatio >= 0.35;
        el.classList.toggle("wv-paused", !visible.current);
      },
      { threshold: [0, 0.35, 0.6] },
    );
    io.observe(el);
    const t = window.setInterval(() => {
      const held = Date.now() < holdUntil.current;
      el.classList.toggle("wv-held", held);
      const cursorOn = !still.current && !held && Date.now() >= cursorOffUntil.current;
      cursorRef.current?.classList.toggle("is-on", cursorOn);
      if (still.current || !visible.current || held || el.closest(".dw-user-paused")) return;
      const before = elapsed.current;
      elapsed.current += TICK;
      if (before < WEIGH_AT && elapsed.current >= WEIGH_AT) {
        setPhase("weigh");
        setWeighed(activeRef.current);
      }
      if (elapsed.current >= CYCLE) {
        elapsed.current = 0;
        activeRef.current = (activeRef.current + 1) % PROFILES.length;
        setActive(activeRef.current);
        setPhase("ask");
        setCycle((c) => c + 1);
        frameRef.current = -1;
      }
      runScript(elapsed.current);
    }, TICK);
    const ro = new ResizeObserver(() => {
      const f = SCRIPT[frameRef.current];
      if (f) aimAt(f.to);
    });
    ro.observe(el);
    return () => {
      io.disconnect();
      ro.disconnect();
      window.clearInterval(t);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- usa solo ref e setter stabili

  const userTook = () => {
    cursorOffUntil.current = Date.now() + 15000;
    cursorRef.current?.classList.remove("is-on");
    setTip(false);
    setHoverRow(-1);
  };

  const pickProfile = (i: number) => {
    userTook();
    activeRef.current = i;
    setActive(i);
    setCycle((c) => c + 1);
    holdUntil.current = 0;
    if (still.current) {
      setWeighed(i);
      return;
    }
    elapsed.current = 0;
    frameRef.current = -1;
    setPhase("ask");
  };

  const pickPhase = (next: Phase) => {
    userTook();
    setPhase(next);
    if (next === "weigh") setWeighed(activeRef.current);
    if (next === "ask") setCycle((c) => c + 1);
    elapsed.current = next === "weigh" ? WEIGH_AT : 0;
    holdUntil.current = still.current ? 0 : Date.now() + 15000;
  };

  const a = (PROFILES[active] ?? PROFILES[0]);
  const p = (PROFILES[weighed] ?? PROFILES[0]);
  const order = (Object.keys(p.scores) as VKey[]).sort((x, y) => p.scores[y] - p.scores[x]);

  // passa il vincitore al capitolo 2
  useEffect(() => {
    setStoryPick({ vehicle: (order[0] ?? "auto"), score: p.scores[(order[0] ?? "auto")], profile: p.name });
  }, [weighed]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div ref={ref} className={`wv ${className}`}>
      <style>{CSS}</style>
      <div className="wv-stage">
        {/* 1 · profili */}
        <div className="wv-col wv-profiles">
          <div className="wv-label">1 · Chi sei</div>
          <div className="wv-plist" role="group" aria-label="Profili di esempio">
            {PROFILES.map((pr, i) => (
              <button
                key={pr.id}
                type="button"
                aria-pressed={i === active}
                className={`wv-profile ${i === active ? "is-on" : ""}`}
                style={{ "--tone": pr.tone } as Vars}
                data-cur={`p${i}`}
                onClick={() => pickProfile(i)}
              >
                <span className="wv-avatar" aria-hidden>
                  {pr.name.charAt(0)}
                </span>
                <span className="wv-pname">{pr.name}</span>
                <span className="wv-chips">
                  {pr.chips.map((c) => (
                    <em key={c}>{c}</em>
                  ))}
                </span>
                {i === active && <span key={cycle} className="wv-progress" aria-hidden />}
              </button>
            ))}
          </div>
          <p className="wv-note">
            Nella scelta guidata domande e pesi nascono dalle tue risposte: utilizzo, budget,
            spazio, esperienza.
          </p>
        </div>

        {/* 2 · domande che diventano criteri */}
        <div className={`wv-col wv-weights ${phase === "weigh" ? "is-weigh" : "is-ask"}`}>
          <div className="wv-label wv-lrow">
            <span key={phase} className="wv-ltext">
              {phase === "ask" ? "2 · Cosa ti chiederesti" : "2 · I 9 criteri pesati per te"}
            </span>
            <span className="wv-switch" role="group" aria-label="Vista: domande o criteri">
              <button
                type="button"
                aria-pressed={phase === "ask"}
                aria-label="Domande verificate"
                className={phase === "ask" ? "is-on" : ""}
                onClick={() => pickPhase("ask")}
              >
                Domande{" "}
                <b key={`n-${cycle}`} style={{ "--wv-to": a.checks.length } as Vars} aria-hidden />/
                {a.checks.length}
              </button>
              <button
                type="button"
                data-cur="sw"
                aria-pressed={phase === "weigh"}
                className={phase === "weigh" ? "is-on" : ""}
                onClick={() => pickPhase("weigh")}
              >
                Criteri
              </button>
            </span>
          </div>
          <div className="wv-qwrap">
            {phase === "ask" && (
              <span key={`scan-${cycle}`} className="wv-scanbox" aria-hidden>
                <i />
              </span>
            )}
            <ul>
              {CRITERIA.map((c, i) => {
                const w = p.weights[c.key];
                const ch = a.checks[i];
                return (
                  <li
                    key={c.key}
                    data-cur={`q${i}`}
                    className={phase === "ask" && hoverRow === i ? "is-hover" : ""}
                    style={{ "--i": i } as Vars}
                  >
                    <div className="wv-flap">
                      <div
                        key={`q-${cycle}`}
                        className={`wv-face wv-q ${ch?.warn ? "is-warn" : ""}`}
                        aria-hidden={phase !== "ask"}
                      >
                        <span className="wv-badge" aria-hidden>
                          <span className="wv-bq">?</span>
                          <span className="wv-ba">{ch?.warn ? "!" : "✓"}</span>
                        </span>
                        <span className="wv-ctext">
                          <b>{ch?.q}</b>
                          <span className="wv-ans">{ch?.a}</span>
                        </span>
                      </div>
                      <div className="wv-face wv-c" aria-hidden={phase !== "weigh"}>
                        <div className="wv-ctext">
                          <b>{c.name}</b>
                          <span>{c.desc}</span>
                        </div>
                        <div
                          className="wv-bar"
                          role="meter"
                          aria-valuemin={0}
                          aria-valuemax={100}
                          aria-valuenow={w}
                          aria-label={`Peso ${c.name}`}
                        >
                          <i
                            style={{
                              width: `${phase === "weigh" ? w : 0}%`,
                              background:
                                w >= 80 ? "var(--wv-mint-ink)" : w >= 60 ? "#7CC9B5" : "#C9D6E2",
                            }}
                          />
                        </div>
                        <em className="wv-w">{w >= 80 ? "alto" : w >= 60 ? "medio" : "basso"}</em>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>

        {/* 3 · classifica */}
        <div className="wv-col wv-rank">
          <div className="wv-label">3 · La classifica per te</div>
          <div className="wv-rlist" data-cur="top">
            {(Object.keys(VEHICLES) as VKey[]).map((k) => {
              const pos = order.indexOf(k);
              const v = VEHICLES[k];
              return (
                <div
                  key={k}
                  className={`wv-rcard ${pos === 0 ? "is-top" : ""}`}
                  style={{ "--pos": pos } as Vars}
                >
                  <span className="wv-pos">{pos + 1}</span>
                  <span className="wv-thumb">{v.art}</span>
                  <span className="wv-rtext">
                    <small>{pos === 0 ? "Scelta consigliata" : v.kind}</small>
                    <b>{v.name}</b>
                  </span>
                  <strong
                    style={{ "--wv-n": p.scores[k] } as Vars}
                    aria-label={`Decision Score ${p.scores[k]}`}
                  />
                </div>
              );
            })}
          </div>
          <div className={`wv-tip ${tip ? "is-on" : ""}`} aria-hidden={!tip}>
            <span className="wv-tip-h">
              <b>Scelta consigliata</b>
              <em>● {p.scores[(order[0] ?? "auto")]}</em>
            </span>
            <span className="wv-tip-p">
              Il miglior equilibrio tra le tue verifiche e i 9 criteri pesati per te.
            </span>
            <span className="wv-tip-b">Vedi il report</span>
          </div>
          <div className="wv-why" key={p.id}>
            <small>Perché è in cima per te</small>
            <ul>
              {p.why.map((w) => (
                <li key={w}>
                  <i>✓</i>
                  {w}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <span ref={cursorRef} className="wv-cursor" aria-hidden>
          <i className="wv-ring" />
          <svg viewBox="0 0 24 24" width="100%" height="100%">
            <path
              d="M5 2.5 L5 19.5 L9.4 15.4 L12.3 21.6 L15.4 20.2 L12.5 14 L18.6 14 Z"
              fill="#1F2A44"
              stroke="#fff"
              strokeWidth="1.6"
              strokeLinejoin="round"
            />
          </svg>
        </span>

        {/* frase finale */}
        <div className="wv-foot">
          <span>
            Stessi dati. Priorità diverse. <b>Scelta diversa.</b>
          </span>
          <span className="wv-links">
            <a className="wv-next" href={nextHref}>
              E dopo la scelta? ↓
            </a>
            <a href={ctaHref}>Prova con il tuo profilo →</a>
          </span>
        </div>
      </div>
    </div>
  );
}

/* Tempi della fase "domande": t0 1 s, una riga ogni 0,38 s (scansione 3,4 s). */
const CSS = `
@property --wv-n { syntax: "<integer>"; inherits: false; initial-value: 0; }
@property --wv-q { syntax: "<integer>"; inherits: false; initial-value: 0; }
.wv{ --ink:#1F2A44; --muted:#5E6A82;
  --wv-mint:#CFF1E6; --wv-mint-ink:var(--brand-ink); --wv-peach:#FFE1D3; --wv-peach-ink:#9A5530;
  --wv-lavender:#E6E0FF; --wv-lav-ink:#6A5BC7; --wv-sky:#DCEEFF;
  --t0:1s; --step:.38s;
  container-type:inline-size; position:relative; width:100%; color:var(--ink); font-family:inherit; }
.wv-stage{ position:relative; aspect-ratio:16/9; overflow:hidden; border-radius:2.2cqw; padding:3cqw 3cqw 0;
  display:grid; grid-template-columns:25fr 41fr 28fr; grid-template-rows:1fr auto; column-gap:2.4cqw;
  background:
    radial-gradient(35% 45% at 12% 30%, rgba(207,241,230,.8), transparent 70%),
    radial-gradient(35% 45% at 88% 35%, rgba(230,224,255,.7), transparent 70%),
    radial-gradient(40% 40% at 55% 100%, rgba(255,225,211,.55), transparent 70%),
    linear-gradient(135deg,#F7FAF9,#F8F7FC 60%,#FCF7F3);
  box-shadow:0 2cqw 6cqw -3cqw rgba(31,42,68,.18), inset 0 0 0 1px rgba(31,42,68,.06); }
.wv-label{ font:600 .82cqw/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); margin-bottom:1.4cqw; }
.wv-col{ min-width:0; display:flex; flex-direction:column; }

/* profili */
.wv-plist{ display:grid; gap:1cqw; }
.wv-profile{ all:unset; cursor:pointer; position:relative; overflow:hidden; display:grid; grid-template-columns:auto 1fr; column-gap:.9cqw; row-gap:.5cqw; align-items:center;
  padding:1.1cqw 1.2cqw; border-radius:1.3cqw; background:rgba(255,255,255,.45); box-shadow:inset 0 0 0 1px rgba(31,42,68,.06);
  transition:background .4s, box-shadow .4s, transform .4s; }
.wv-profile:hover{ background:rgba(255,255,255,.75); }
.wv-profile:focus-visible{ outline:2px solid var(--focus-ink); outline-offset:2px; }
.wv-profile.is-on{ background:#fff; box-shadow:0 1cqw 2.4cqw -1.2cqw rgba(31,42,68,.25), inset 0 0 0 1.5px var(--wv-mint-ink); transform:translateX(.4cqw); }
.wv-avatar{ display:grid; place-items:center; width:2.6cqw; height:2.6cqw; border-radius:50%; background:var(--tone); font-weight:800; font-size:1.1cqw; }
.wv-pname{ font-weight:700; font-size:1.1cqw; line-height:1.2; }
.wv-chips{ grid-column:1 / -1; display:flex; flex-wrap:wrap; gap:.4cqw; }
.wv-chips em{ font-style:normal; font-size:.78cqw; padding:.3cqw .6cqw; border-radius:99px; background:var(--tone); color:var(--ink); }
.wv-profile:not(.is-on) .wv-chips em{ background:rgba(31,42,68,.05); color:var(--muted); }
.wv-progress{ position:absolute; left:0; bottom:0; height:.25cqw; width:100%; background:var(--wv-mint-ink); opacity:.5; transform-origin:left; animation:wv-progress ${CYCLE}ms linear both; }
@keyframes wv-progress{ from{ transform:scaleX(0) } to{ transform:scaleX(1) } }

/* colonna centrale: intestazione con interruttore */
.wv-lrow{ display:flex; align-items:center; justify-content:space-between; gap:1cqw; }
.wv-ltext{ animation:wv-in .45s ease-out both; white-space:nowrap; }
.wv-switch{ display:flex; gap:.3cqw; padding:.25cqw; border-radius:99px; background:rgba(255,255,255,.7); box-shadow:inset 0 0 0 1px rgba(31,42,68,.06); }
.wv-switch button{ all:unset; cursor:pointer; font:inherit; letter-spacing:.08em; padding:6px .8cqw; min-height:24px; display:inline-flex; align-items:center; box-sizing:border-box; border-radius:99px; color:var(--muted); transition:background .3s, color .3s; white-space:nowrap; }
.wv-switch button.is-on{ background:#fff; color:var(--ink); box-shadow:0 .3cqw .9cqw -.5cqw rgba(31,42,68,.3); }
.wv-switch button:focus-visible{ outline:2px solid var(--focus-ink); outline-offset:2px; }
.wv-switch b{ color:var(--wv-mint-ink); counter-reset:q var(--wv-q); --wv-q:var(--wv-to);
  animation:wv-count calc(var(--step) * 9) steps(9,jump-start) calc(var(--t0) + var(--step) * .5) both; }
.wv-switch b::after{ content:counter(q); }
@keyframes wv-count{ from{ --wv-q:0; } to{ --wv-q:var(--wv-to); } }

/* righe a ribalta: domanda davanti, criterio dietro */
.wv-qwrap{ position:relative; flex:1; display:flex; padding-bottom:1.6cqw; }
.wv-weights ul{ list-style:none; margin:0; padding:0; display:grid; gap:.55cqw; flex:1; align-content:space-between; }
.wv-weights li{ perspective:50cqw; }
.wv-flap{ display:grid; transform-style:preserve-3d; transition:transform .7s cubic-bezier(.3,.7,.2,1) calc(var(--i) * 55ms); }
.is-weigh .wv-flap{ transform:rotateX(180deg); }
.wv-face{ grid-area:1 / 1; min-width:0; display:grid; align-items:center; column-gap:1cqw; padding:.55cqw .9cqw; border-radius:.9cqw;
  background:rgba(255,255,255,.7); box-shadow:inset 0 0 0 1px rgba(31,42,68,.05);
  backface-visibility:hidden; -webkit-backface-visibility:hidden; }
.wv-c{ grid-template-columns:1fr 10cqw 3.4cqw; transform:rotateX(180deg); }
.wv-q{ grid-template-columns:auto 1fr; background:#fff;
  --d:calc(var(--t0) + var(--i) * var(--step) + var(--step) * .5);
  animation:wv-lit .9s ease-out var(--d) both; }
.wv-q.is-warn{ animation-name:wv-lit-w; }
@keyframes wv-lit{ 0%,100%{ box-shadow:inset 0 0 0 1px rgba(31,42,68,.05); } 30%{ box-shadow:0 .6cqw 1.6cqw -.8cqw rgba(47,143,122,.45), inset 0 0 0 1.5px var(--wv-mint-ink); } }
@keyframes wv-lit-w{ 0%,100%{ box-shadow:inset 0 0 0 1px rgba(31,42,68,.05); } 30%{ box-shadow:0 .6cqw 1.6cqw -.8cqw rgba(181,105,63,.4), inset 0 0 0 1.5px var(--wv-peach-ink); } }

.wv-ctext{ min-width:0; display:flex; flex-direction:column; }
.wv-ctext b{ font-size:.98cqw; line-height:1.2; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.wv-ctext span{ font-size:.74cqw; color:var(--muted); line-height:1.25; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.wv-ctext .wv-ans{ font:600 .74cqw/1.25 ui-monospace,SFMono-Regular,Menlo,monospace; color:var(--wv-mint-ink);
  animation:wv-ans .45s ease-out calc(var(--d) + .2s) both; }
.is-warn .wv-ans{ color:var(--wv-peach-ink); }
@keyframes wv-ans{ from{ opacity:0; transform:translateX(-.5cqw); filter:blur(2px); } to{ opacity:1; transform:none; filter:none; } }

.wv-badge{ position:relative; width:1.9cqw; height:1.9cqw; perspective:12cqw; }
.wv-badge > span{ position:absolute; inset:0; display:grid; place-items:center; border-radius:50%; backface-visibility:hidden; -webkit-backface-visibility:hidden;
  font:800 .9cqw/1 var(--font-heading,inherit); }
.wv-bq{ background:var(--wv-lavender); color:var(--wv-lav-ink); transform:rotateY(180deg); animation:wv-flip-q .5s ease-in-out var(--d) both; }
.wv-ba{ background:var(--wv-mint); color:var(--wv-mint-ink); animation:wv-flip-a .5s ease-in-out var(--d) both; }
.is-warn .wv-ba{ background:var(--wv-peach); color:var(--wv-peach-ink); }
@keyframes wv-flip-q{ from{ transform:rotateY(0); } to{ transform:rotateY(180deg); } }
@keyframes wv-flip-a{ from{ transform:rotateY(-180deg); } to{ transform:rotateY(0); } }

.wv-scanbox{ position:absolute; left:-.6cqw; right:-.6cqw; top:0; bottom:1.6cqw; pointer-events:none; z-index:5; }
.wv-scanbox i{ position:absolute; left:0; right:0; top:0; height:.22cqw; border-radius:99px;
  background:linear-gradient(90deg, transparent, var(--wv-mint-ink) 15%, var(--wv-mint-ink) 85%, transparent);
  box-shadow:0 0 1.4cqw .25cqw rgba(47,143,122,.35);
  animation:wv-scan calc(var(--step) * 9) cubic-bezier(.45,0,.55,1) var(--t0) both; }
@keyframes wv-scan{ 0%{ top:0; opacity:0; } 6%{ opacity:1; } 94%{ opacity:1; } 100%{ top:100%; opacity:0; } }

.wv-bar{ height:.7cqw; border-radius:99px; background:rgba(31,42,68,.07); overflow:hidden; }
.wv-bar i{ display:block; height:100%; border-radius:99px; transition:width .9s cubic-bezier(.2,.8,.2,1) calc(.35s + var(--i) * 55ms), background .9s; }
.wv-w{ font-style:normal; font-size:.74cqw; color:var(--muted); text-align:right; }

/* classifica */
.wv-rlist{ position:relative; height:calc(3 * 7.6cqw + 2 * 1cqw); }
.wv-rcard{ position:absolute; left:0; right:0; top:0; height:7.6cqw; display:grid; grid-template-columns:auto 7.4cqw 1fr auto; align-items:center; column-gap:.9cqw;
  padding:0 1.2cqw; border-radius:1.3cqw; background:#fff; box-shadow:0 .8cqw 2cqw -1.2cqw rgba(31,42,68,.22), inset 0 0 0 1px rgba(31,42,68,.05);
  transform:translateY(calc(var(--pos) * 8.6cqw)); transition:transform .9s cubic-bezier(.2,.8,.2,1) .7s, box-shadow .6s .7s; }
.wv-rcard.is-top{ box-shadow:0 1.2cqw 2.6cqw -1.2cqw rgba(47,143,122,.45), inset 0 0 0 1.5px var(--wv-mint-ink); z-index:1; }
.wv-pos{ display:grid; place-items:center; width:1.8cqw; height:1.8cqw; border-radius:50%; background:#F1F4F8; font-weight:800; font-size:.9cqw; transition:background .6s .7s; }
.wv-rcard.is-top .wv-pos{ background:var(--wv-mint); color:var(--wv-mint-ink); }
.wv-thumb{ height:5cqw; display:block; }
.wv-thumb svg{ width:100%; height:100%; }
.wv-rtext{ min-width:0; display:flex; flex-direction:column; }
.wv-rtext small{ font-size:.72cqw; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; }
.wv-rcard.is-top .wv-rtext small{ color:var(--wv-mint-ink); font-weight:700; }
.wv-rtext b{ font-size:1cqw; line-height:1.2; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.wv-rcard strong{ font-family:var(--font-heading,inherit); font-weight:800; font-size:2cqw; counter-reset:n var(--wv-n); transition:--wv-n .9s ease-out .7s; }
.wv-rcard strong::after{ content:counter(n); }

/* piede */
.wv-foot{ grid-column:1 / -1; display:flex; justify-content:space-between; align-items:center; gap:2cqw; margin:0 -3cqw; padding:1.5cqw 3cqw;
  border-top:1px solid rgba(31,42,68,.06); background:rgba(255,255,255,.55); }
.wv-foot span{ font-size:1.25cqw; color:var(--muted); }
.wv-foot span b{ color:var(--ink); }
.wv-foot a{ font-weight:600; font-size:1.05cqw; color:var(--ink); text-decoration:none; padding:.8cqw 1.5cqw; border-radius:99px; background:var(--wv-mint); transition:background .3s; }
.wv-foot a:hover{ background:#B8E8D8; }
.wv-links{ display:flex; align-items:center; gap:1.2cqw; }
.wv-foot a.wv-next{ background:transparent; color:var(--muted); padding:.8cqw .4cqw; }
.wv-foot a.wv-next:hover{ color:var(--ink); background:transparent; }

.wv-note{ margin:auto 0 1.6cqw; font-size:.82cqw; line-height:1.45; color:var(--muted); padding:1cqw 1.2cqw; border-radius:1cqw; background:rgba(255,255,255,.5); border:1px dashed rgba(31,42,68,.12); }
.wv-why{ margin:1.4cqw 0 1.6cqw; padding:1.2cqw 1.3cqw; border-radius:1.3cqw; background:rgba(207,241,230,.55); animation:wv-in .7s ease-out 1.2s both; }
.wv-why small{ display:block; font:600 .72cqw/1 ui-monospace,Menlo,monospace; letter-spacing:.12em; text-transform:uppercase; color:var(--wv-mint-ink); margin-bottom:.8cqw; }
.wv-why ul{ list-style:none; margin:0; padding:0; display:grid; gap:.5cqw; }
.wv-why li{ display:flex; gap:.6cqw; align-items:center; font-size:.88cqw; }
.wv-why li i{ font-style:normal; display:grid; place-items:center; width:1.3cqw; height:1.3cqw; border-radius:50%; background:#fff; color:var(--wv-mint-ink); font-size:.72cqw; font-weight:800; }
@keyframes wv-in{ from{ opacity:0; transform:translateY(.6cqw) } to{ opacity:1; transform:none } }

/* pausa fuori schermo e dopo un clic sull'interruttore */
.wv-paused *, .wv-paused *::before, .wv-paused *::after{ animation-play-state:paused !important; }
.wv-held .wv-progress{ animation-play-state:paused; }

/* cursore che "naviga" la vignetta */
.wv-cursor{ position:absolute; left:0; top:0; z-index:20; width:1.9cqw; height:1.9cqw; margin:-.25cqw 0 0 -.45cqw; pointer-events:none;
  opacity:0; transform:translate(70%, 60%); transition:transform .85s cubic-bezier(.55,.05,.25,1), opacity .35s;
  filter:drop-shadow(0 .3cqw .5cqw rgba(31,42,68,.28)); }
.wv-cursor.is-on{ opacity:1; }
.wv-cursor svg{ position:relative; display:block; transform-origin:20% 10%; }
.wv-ring{ position:absolute; left:-.9cqw; top:-.9cqw; width:2.4cqw; height:2.4cqw; border-radius:50%; background:rgba(47,143,122,.35); opacity:0; transform:scale(.2); }
.wv-cursor.is-click .wv-ring{ animation:wv-ring .55s ease-out both; }
.wv-cursor.is-click svg{ animation:wv-press .3s ease-out both; }
@keyframes wv-ring{ from{ opacity:.9; transform:scale(.2); } to{ opacity:0; transform:scale(1.5); } }
@keyframes wv-press{ 0%,100%{ transform:scale(1); } 45%{ transform:scale(.82); } }

/* riga sotto il cursore e tooltip sul primo in classifica */
.wv-weights li.is-hover .wv-q{ background:#ECF8F3; box-shadow:inset 0 0 0 1px rgba(47,143,122,.25); }
.wv-rank{ position:relative; }
.wv-tip{ position:absolute; z-index:6; right:.4cqw; top:calc(1.4cqw + .82cqw + 7.6cqw + .2cqw); width:15.5cqw; display:grid; gap:.7cqw;
  padding:1.1cqw 1.2cqw; border-radius:1.1cqw; background:#fff;
  box-shadow:0 1.4cqw 3cqw -1.2cqw rgba(31,42,68,.35), inset 0 0 0 1px rgba(31,42,68,.06);
  opacity:0; transform:translateY(-.6cqw) scale(.97); transform-origin:85% 0; pointer-events:none; transition:opacity .3s, transform .35s cubic-bezier(.2,.8,.2,1); }
.wv-tip.is-on{ opacity:1; transform:none; }
.wv-tip-h{ display:flex; align-items:center; gap:.6cqw; }
.wv-tip-h b{ font:800 1cqw/1.1 var(--font-heading,inherit); }
.wv-tip-h em{ font-style:normal; font-weight:700; font-size:.78cqw; padding:.2cqw .55cqw; border-radius:99px; color:var(--wv-mint-ink); box-shadow:inset 0 0 0 1px rgba(31,42,68,.1); }
.wv-tip-p{ font-size:.8cqw; line-height:1.35; color:var(--muted); }
.wv-tip-b{ display:block; text-align:center; font-weight:600; font-size:.8cqw; padding:.6cqw; border-radius:.6cqw; box-shadow:inset 0 0 0 1px rgba(31,42,68,.14); }

/* mobile: verticale */
@container (max-width: 640px){
  .wv-stage{ --step:.3s; aspect-ratio:auto; display:flex; flex-direction:column; gap:6cqw; padding:6cqw 5cqw 0; border-radius:5cqw; }
  .wv-label{ font-size:2.6cqw; margin-bottom:3cqw; }
  .wv-plist{ grid-auto-flow:column; grid-auto-columns:72%; overflow-x:auto; scroll-snap-type:x mandatory; gap:3cqw; padding-bottom:1cqw; }
  .wv-profile{ scroll-snap-align:start; padding:3.2cqw; border-radius:3.5cqw; column-gap:2.4cqw; row-gap:1.6cqw; }
  .wv-profile.is-on{ transform:none; }
  .wv-avatar{ width:7cqw; height:7cqw; font-size:3cqw; }
  .wv-pname{ font-size:3.4cqw; }
  .wv-chips em{ font-size:2.4cqw; padding:.8cqw 1.8cqw; }
  .wv-progress{ height:.8cqw; }
  .wv-lrow{ flex-wrap:wrap; row-gap:2cqw; }
  .wv-switch{ padding:.8cqw; gap:1cqw; }
  .wv-switch button{ padding:1.4cqw 2.4cqw; }
  .wv-qwrap{ padding-bottom:0; }
  .wv-scanbox{ bottom:0; }
  .wv-weights ul{ gap:1.6cqw; }
  .wv-face{ padding:2cqw 2.6cqw; border-radius:2.6cqw; column-gap:2.4cqw; }
  .wv-c{ grid-template-columns:1fr 24cqw 9cqw; }
  .wv-ctext b{ font-size:3.2cqw; white-space:normal; } .wv-ctext span{ font-size:2.4cqw; white-space:normal; }
  .wv-ctext .wv-ans{ font-size:2.5cqw; }
  .wv-badge{ width:6cqw; height:6cqw; } .wv-badge > span{ font-size:2.8cqw; }
  .wv-bar{ height:2cqw; } .wv-w{ font-size:2.4cqw; }
  .wv-rlist{ height:calc(3 * 20cqw + 2 * 2.6cqw); }
  .wv-rcard{ height:20cqw; grid-template-columns:auto 20cqw 1fr auto; padding:0 3.4cqw; border-radius:3.6cqw; column-gap:2.6cqw; transform:translateY(calc(var(--pos) * 22.6cqw)); }
  .wv-pos{ width:5cqw; height:5cqw; font-size:2.6cqw; }
  .wv-thumb{ height:13cqw; }
  .wv-rtext small{ font-size:2.2cqw; } .wv-rtext b{ font-size:3.2cqw; }
  .wv-rcard strong{ font-size:6cqw; }
  .wv-note{ font-size:2.6cqw; padding:2.6cqw 3cqw; border-radius:2.6cqw; margin:3cqw 0 0; }
  .wv-why{ margin:3cqw 0 4cqw; padding:3.4cqw; border-radius:3.4cqw; }
  .wv-why small{ font-size:2.3cqw; margin-bottom:2cqw; } .wv-why li{ font-size:3cqw; gap:2cqw; } .wv-why ul{ gap:1.6cqw; }
  .wv-why li i{ width:4cqw; height:4cqw; font-size:2.2cqw; }
  .wv-foot{ flex-direction:column; align-items:flex-start; margin:0 -5cqw; padding:4.5cqw 5cqw; gap:3cqw; }
  .wv-foot span{ font-size:3.6cqw; } .wv-foot a{ font-size:3.4cqw; padding:2.6cqw 4.4cqw; }
  .wv-links{ flex-direction:column-reverse; align-items:flex-start; gap:2cqw; }
  .wv-cursor{ display:none; }
  .wv-tip{ right:2cqw; top:calc(2.6cqw + 3cqw + 20cqw - 1cqw); width:62cqw; gap:2cqw; padding:3.4cqw; border-radius:3.4cqw; }
  .wv-tip-h b{ font-size:3.4cqw; } .wv-tip-h em{ font-size:2.6cqw; padding:.6cqw 1.6cqw; }
  .wv-tip-p, .wv-tip-b{ font-size:2.8cqw; } .wv-tip-b{ padding:2cqw; border-radius:2cqw; }
}

/* Labels stay at 12px; informative copy is at least 13px at every width. */
.wv-label, .wv-avatar, .wv-pos, .wv-rtext small, .wv-why small, .wv-badge > span, .wv-w { font-size:12px; }
.wv-pname, .wv-chips em, .wv-ctext b, .wv-ctext span, .wv-ctext .wv-ans,
.wv-rtext b, .wv-note, .wv-why li, .wv-tip-h b, .wv-tip-h em, .wv-tip-p, .wv-tip-b { font-size:13px; }
.wv-ctext span, .wv-chips em { opacity:1; }
.wv-why small { color:var(--brand-ink); line-height:1.3; }
.wv-ltext { white-space:normal; line-height:1.4; }
.wv-lrow { flex-wrap:wrap; }
.wv-stage { aspect-ratio:auto; min-height:56.25cqw; }
.wv-foot a { min-height:24px; min-width:24px; display:inline-flex; align-items:center; box-sizing:border-box; font-size:13px; }
@media (max-width:767px) {
  .wv-switch button, .wv-foot a { min-height:44px; padding-top:12px; padding-bottom:12px; }
}
@container (max-width:640px) {
  .wv-foot span { font-size:13px; }
  .wv-ctext b, .wv-rtext b, .wv-why li { font-size:13px; }
}

@media (prefers-reduced-motion: reduce){
  .wv *, .wv *::after{ transition:none !important; animation:none !important; }
  .wv-progress, .wv-scanbox, .wv-cursor{ display:none; }
}
`;
