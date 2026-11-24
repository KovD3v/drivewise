
import { useId } from "react";

/**
 * Vignetta animata in stile "line art + mezzetinte".
 * Loop di 7s: l'auto entra → il ranking si riempie → il Decision Score arriva a 86
 * → il cursore clicca "Inizia". Animazioni in CSS puro (vedi blocco <style> sotto),
 * disattivate con prefers-reduced-motion.
 */
export function DecisionVignette({ className = "" }: { className?: string }) {
  const uid = useId().replace(/:/g, "");
  const dots = `dwv-dots-${uid}`;
  const dotsS = `dwv-dots-s-${uid}`;

  return (
    <svg
      className={`dwv ${className}`}
      viewBox="0 0 400 240"
      role="img"
      aria-label="Illustrazione: DriveWise analizza i veicoli e calcola il Decision Score"
    >
      <style>{VIGNETTE_CSS}</style>
      <defs>
        <pattern id={dots} width="5" height="5" patternUnits="userSpaceOnUse">
          <circle cx="2.5" cy="2.5" r="1.05" fill="#0F172A" />
        </pattern>
        <pattern id={dotsS} width="4" height="4" patternUnits="userSpaceOnUse">
          <circle cx="2" cy="2" r=".7" fill="#0F172A" />
        </pattern>
      </defs>

      <g className="dwv-float">
        <g transform="rotate(-5 200 120)" stroke="#0F172A" strokeLinecap="round" strokeLinejoin="round">
          {/* ombra a mezzetinte */}
          <rect x="80" y="42" width="260" height="176" rx="18" fill={`url(#${dots})`} stroke="none" />
          {/* tablet */}
          <rect x="70" y="30" width="260" height="176" rx="18" fill="#fff" strokeWidth="3" />
          <circle cx="78.5" cy="118" r="2.4" fill="none" strokeWidth="1.8" />
          <rect x="86" y="42" width="232" height="152" rx="9" fill="#F7FCFA" strokeWidth="2" />

          {/* auto che entra */}
          <g className="dwv-anim dwv-car">
            <g transform="translate(98 52)">
              <path
                d="M4 33 V24 Q5 19 12 18 L31 16 L44 6 Q47 4 52 4 H77 Q82 4 85 7 L97 17 Q107 19 108 25 V33 Q108 36 105 36 H7 Q4 36 4 33 Z"
                fill="#BFEDE1"
                strokeWidth="2.4"
              />
              <path d="M47 9 H55 V17 H36 Z" fill="#fff" strokeWidth="1.8" />
              <path d="M59 9 H77 L88 17 H59 Z" fill="#fff" strokeWidth="1.8" />
              <path d="M4 30 Q20 30 22 36" fill={`url(#${dotsS})`} stroke="none" />
              {[25, 85].map((cx) => (
                <g key={cx} className="dwv-anim dwv-wheel">
                  <circle cx={cx} cy="36" r="9" fill="#fff" strokeWidth="2.4" />
                  <circle cx={cx} cy="36" r="3" fill="#0F172A" stroke="none" />
                  <path
                    d={`M${cx} 28.5 V31 M${cx} 41 V43.5 M${cx - 7.5} 36 H${cx - 5} M${cx + 5} 36 H${cx + 7.5}`}
                    strokeWidth="1.6"
                  />
                </g>
              ))}
            </g>
          </g>

          {/* righe di testo */}
          <path d="M222 60 H258 M222 70 H252 M222 80 H244" strokeWidth="2.2" />

          {/* Decision Score */}
          <circle cx="288" cy="74" r="20" fill="#fff" stroke="#BFEDE1" strokeWidth="5" />
          <circle
            className="dwv-anim dwv-ring"
            cx="288"
            cy="74"
            r="20"
            fill="none"
            stroke="#2FA88F"
            strokeWidth="5"
            strokeLinecap="butt"
            transform="rotate(-90 288 74)"
            pathLength={126}
          />
          <text
            className="dwv-anim dwv-score"
            x="288"
            y="78.5"
            textAnchor="middle"
            fontFamily="inherit"
            fontWeight="700"
            fontSize="13"
            fill="#0F172A"
            stroke="none"
          >
            86
          </text>

          {/* ranking */}
          <g strokeWidth="2">
            <rect x="98" y="110" width="150" height="20" rx="6" fill="#fff" />
            <rect className="dwv-anim dwv-best" x="98" y="110" width="150" height="20" rx="6" fill="#BFEDE1" />
            <circle cx="110" cy="120" r="5" fill="#0F172A" stroke="none" />
            <rect className="dwv-anim dwv-bar" x="122" y="116" width="100" height="8" rx="4" fill="#2FA88F" stroke="none" />
            <path className="dwv-anim dwv-best" d="M230 120 l4 4 l8 -8" fill="none" strokeWidth="2.4" />

            <rect x="98" y="136" width="150" height="20" rx="6" fill="#fff" />
            <circle cx="110" cy="146" r="5" fill="none" />
            <rect className="dwv-anim dwv-bar d2" x="122" y="142" width="76" height="8" rx="4" fill={`url(#${dotsS})`} />

            <rect x="98" y="162" width="150" height="20" rx="6" fill="#fff" />
            <circle cx="110" cy="172" r="5" fill="none" />
            <rect className="dwv-anim dwv-bar d3" x="122" y="168" width="54" height="8" rx="4" fill={`url(#${dotsS})`} />
          </g>

          {/* bottone Inizia */}
          <circle className="dwv-anim dwv-ripple" cx="282" cy="166" r="16" fill="none" stroke="#2FA88F" strokeWidth="3" />
          <g className="dwv-anim dwv-btn">
            <rect x="258" y="154" width="48" height="24" rx="12" fill="#0F172A" stroke="none" />
            <text x="282" y="170" textAnchor="middle" fontFamily="inherit" fontWeight="600" fontSize="10" fill="#fff" stroke="none">
              Inizia
            </text>
          </g>
        </g>
      </g>

      {/* cursore */}
      <g className="dwv-anim dwv-cursor">
        <path
          d="M292 172 l0 26 l7 -6 l5 11 l5 -2.3 l-5 -10.7 l9 -.5 Z"
          fill="#fff"
          stroke="#0F172A"
          strokeWidth="2.2"
          strokeLinejoin="round"
        />
      </g>
    </svg>
  );
}

const VIGNETTE_CSS = `
.dwv-car,.dwv-wheel,.dwv-bar,.dwv-btn,.dwv-ripple,.dwv-cursor{transform-box:fill-box}
.dwv-anim{animation-duration:7s;animation-iteration-count:infinite;animation-timing-function:cubic-bezier(.4,0,.2,1)}
.dwv-car{animation-name:dwv-car;transform-origin:center}
@keyframes dwv-car{0%{transform:translateX(-70px);opacity:0}4%{opacity:1}16%,92%{transform:translateX(0);opacity:1}100%{transform:translateX(0);opacity:0}}
.dwv-wheel{animation-name:dwv-wheel;transform-origin:center}
@keyframes dwv-wheel{0%{transform:rotate(-540deg)}16%,100%{transform:rotate(0)}}
.dwv-bar{animation-name:dwv-bar;transform-origin:left center}
@keyframes dwv-bar{0%,18%{transform:scaleX(0);opacity:1}34%,92%{transform:scaleX(1);opacity:1}100%{transform:scaleX(1);opacity:0}}
.dwv-bar.d2{animation-name:dwv-bar2}
@keyframes dwv-bar2{0%,24%{transform:scaleX(0);opacity:1}40%,92%{transform:scaleX(1);opacity:1}100%{transform:scaleX(1);opacity:0}}
.dwv-bar.d3{animation-name:dwv-bar3}
@keyframes dwv-bar3{0%,30%{transform:scaleX(0);opacity:1}46%,92%{transform:scaleX(1);opacity:1}100%{transform:scaleX(1);opacity:0}}
.dwv-ring{animation-name:dwv-ring;stroke-dasharray:126;stroke-dashoffset:126}
@keyframes dwv-ring{0%,34%{stroke-dashoffset:126;opacity:1}54%,92%{stroke-dashoffset:18;opacity:1}100%{stroke-dashoffset:18;opacity:0}}
.dwv-score{animation-name:dwv-fade}
@keyframes dwv-fade{0%,48%{opacity:0}56%,92%{opacity:1}100%{opacity:0}}
.dwv-best{animation-name:dwv-best}
@keyframes dwv-best{0%,46%{opacity:0}52%,92%{opacity:1}100%{opacity:0}}
.dwv-cursor{animation-name:dwv-cursor}
@keyframes dwv-cursor{0%,56%{transform:translate(70px,60px);opacity:0}60%{opacity:1}70%{transform:translate(0,0)}73%{transform:translate(0,0) scale(.88)}76%,88%{transform:translate(0,0) scale(1);opacity:1}96%,100%{transform:translate(40px,40px);opacity:0}}
.dwv-btn{animation-name:dwv-btn;transform-origin:center}
@keyframes dwv-btn{0%,71%{transform:scale(1)}73.5%{transform:scale(.92)}77%,100%{transform:scale(1)}}
.dwv-ripple{animation-name:dwv-ripple;transform-origin:center}
@keyframes dwv-ripple{0%,72%{transform:scale(.2);opacity:0}74%{opacity:.6}86%,100%{transform:scale(2.4);opacity:0}}
.dwv-float{animation:dwv-float 6s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes dwv-float{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}
@media (prefers-reduced-motion:reduce){
  .dwv-anim,.dwv-float{animation:none!important}
  .dwv-ring{stroke-dashoffset:18}
  .dwv-cursor{transform:none}
}
`;

