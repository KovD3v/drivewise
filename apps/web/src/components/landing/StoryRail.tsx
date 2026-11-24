import { useEffect, useState, type CSSProperties } from "react";

/**
 * Indice della storia, fisso sul lato destro (solo da 1024 px in su).
 * Un punto per capitolo; il capitolo corrente è evidenziato e la linea si riempie fino a lì.
 * Le etichette compaiono al passaggio del mouse o con la tastiera; il clic porta al capitolo.
 * Sostituisce l'indicatore a pallini già presente sul lato destro della home.
 */

const CHAPTERS = [
  { id: "top", label: "Inizio" },
  { id: "analisi", label: "La scelta" },
  { id: "come-funziona", label: "Esempio" },
  { id: "dopo-la-scelta", label: "Dopo la scelta" },
  { id: "perche", label: "Perché DriveWise" },
  { id: "faq", label: "FAQ" },
];

type Vars = CSSProperties & Record<`--${string}`, string | number>;

export function StoryRail() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    let raf = 0;
    const update = () => {
      raf = 0;
      const line = window.innerHeight * 0.4; // un capitolo è "attivo" quando il suo inizio supera il 40% dello schermo
      let current = 0;
      CHAPTERS.forEach((c, i) => {
        const el = document.getElementById(c.id);
        if (el && el.getBoundingClientRect().top <= line) current = i;
      });
      setActive(current);
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, []);

  return (
    <nav className="sr" aria-label="Capitoli della pagina" style={{ "--fill": active / (CHAPTERS.length - 1) } as Vars}>
      <style>{CSS}</style>
      <span className="sr-line" aria-hidden>
        <i />
      </span>
      <ol>
        {CHAPTERS.map((c, i) => (
          <li key={c.id}>
            <a href={`#${c.id}`} className={i === active ? "is-on" : i < active ? "is-done" : ""} aria-current={i === active ? "true" : undefined}>
              <span className="sr-label">{c.label}</span>
              <span className="sr-dot" aria-hidden />
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

const CSS = `
.sr{ --ink:var(--focus-ink); --muted:var(--muted-foreground); --mint:#CFF1E6; --mint-ink:var(--brand-ink);
  position:fixed; right:22px; top:50%; transform:translateY(-50%); z-index:40; display:none; }
@media (min-width:1024px){ .sr{ display:block; } }
.sr ol{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:22px; position:relative; }
.sr-line{ position:absolute; right:5px; top:6px; bottom:6px; width:2px; border-radius:2px; background:rgba(31,42,68,.1); }
.sr-line i{ position:absolute; left:0; right:0; top:0; height:calc(var(--fill) * 100%); border-radius:2px; background:var(--mint-ink); opacity:.6; transition:height .5s cubic-bezier(.2,.8,.2,1); }
.sr a{ position:relative; display:flex; align-items:center; justify-content:flex-end; gap:10px; text-decoration:none; min-height:24px; min-width:24px; }
.sr-dot{ position:relative; width:12px; height:12px; border-radius:50%; background:#fff; box-shadow:inset 0 0 0 2px rgba(31,42,68,.18); transition:box-shadow .3s, transform .3s; }
.sr a.is-done .sr-dot{ box-shadow:inset 0 0 0 2px var(--mint-ink); }
.sr a.is-on .sr-dot{ background:var(--mint-ink); box-shadow:0 0 0 4px var(--mint); transform:scale(1.1); }
.sr-label{ font-size:12px; font-weight:600; color:var(--ink); white-space:nowrap; padding:5px 10px; border-radius:99px; background:rgba(255,255,255,.92);
  box-shadow:0 4px 14px -6px rgba(31,42,68,.25), inset 0 0 0 1px rgba(31,42,68,.06);
  opacity:0; transform:translateX(6px); pointer-events:none; transition:opacity .25s, transform .25s; }
.sr a:hover .sr-label, .sr a:focus-visible .sr-label{ opacity:1; transform:none; }
.sr:hover .sr-label{ opacity:1; transform:none; }
.sr a.is-on .sr-label{ color:var(--mint-ink); }
.sr a:focus-visible .sr-dot{ box-shadow:0 0 0 3px var(--mint-ink); }
@media (prefers-reduced-motion: reduce){ .sr *{ transition:none !important; } }
`;
