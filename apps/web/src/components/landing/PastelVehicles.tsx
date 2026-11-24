import { useId } from "react";

/**
 * Segnaposto pastello dei veicoli (vista laterale).
 * Vanno sostituiti dai render 3D "clay" definitivi: basta impostare `src` in VEHICLES
 * (DecisionPipeline.tsx) e questi componenti non vengono più usati.
 */

const INK = "#334155";
const TIRE = "#3B4458";
const RIM = "#E9EEF4";
const GLASS = "#D9E8F5";

function Wheel({ cx, cy, r, spokes = 10 }: { cx: number; cy: number; r: number; spokes?: number }) {
  const d = Array.from({ length: spokes }, (_, i) => {
    const t = (i * 2 * Math.PI) / spokes;
    return `M${(cx + Math.cos(t) * r * 0.18).toFixed(1)} ${(cy + Math.sin(t) * r * 0.18).toFixed(1)} L${(cx + Math.cos(t) * r * 0.58).toFixed(1)} ${(cy + Math.sin(t) * r * 0.58).toFixed(1)}`;
  }).join(" ");
  return (
    <g>
      <circle cx={cx} cy={cy} r={r} fill={TIRE} />
      <circle cx={cx} cy={cy} r={r * 0.66} fill={RIM} />
      <circle cx={cx} cy={cy} r={r * 0.62} fill="none" stroke="#C9D2DD" strokeWidth={0.8} />
      <path d={d} stroke="#AEB9C7" strokeWidth={r * 0.07} strokeLinecap="round" />
      <circle cx={cx} cy={cy} r={r * 0.14} fill="#C3CDD9" />
    </g>
  );
}

const CAR_BODY =
  "M60 290 L93 287 A25 25 0 1 1 139 287 L266 287 A25 25 0 1 1 312 287 L340 288 Q348 286 349 276 L350 262 Q350 252 344 248 L320 242 Q290 236 256 233 Q228 214 200 205 Q186 202 160 202 Q130 202 98 205 Q80 207 70 214 L56 236 Q52 244 52 256 L53 280 Q54 289 60 290 Z";
const CAR_GLASS =
  "M246 233 Q224 217 202 210 L176 209 L176 235 Z M168 209 L120 209 L118 235 L168 235 Z M112 209 L102 209 Q88 211 80 220 L72 233 Q71 236 76 236 L112 236 Z";

export function PastelCar({ color = "#BFE8DA", shade = "#9ED6C3" }: { color?: string; shade?: string }) {
  const gid = `pc-body-${useId().replace(/:/g, "")}`;
  return (
    <svg viewBox="40 190 320 115" width="100%" height="100%" aria-hidden>
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#FFFFFF" stopOpacity="0.9" />
          <stop offset="0.25" stopColor={color} />
          <stop offset="1" stopColor={shade} />
        </linearGradient>
      </defs>
      <path d={CAR_BODY} fill={`url(#${gid})`} />
      <path d={CAR_GLASS} fill={GLASS} />
      <g fill="none" stroke={INK} strokeOpacity={0.28} strokeWidth={1} strokeLinecap="round">
        <path d="M258 238 Q262 262 258 284 M172 236 L171 286 M110 236 Q118 258 140 266 M58 250 Q200 246 342 252" />
        <path d="M96 201 Q150 196 186 200" strokeWidth={2.4} strokeOpacity={0.35} />
      </g>
      <path d="M246 235 Q254 227 263 229 L263 238 Q254 240 248 238 Z" fill={shade} />
      <path d="M196 247 H212 M120 247 H134" stroke={INK} strokeOpacity={0.35} strokeWidth={1.6} strokeLinecap="round" />
      <path d="M344 248 L320 243 Q318 250 324 254 L346 256 Z" fill="#FFF6D8" />
      <path d="M54 238 L64 236 L62 256 L53 256 Z" fill="#F7B9A8" />
      <path d="M141 281 H264" stroke={shade} strokeWidth={3} strokeLinecap="round" />
      <Wheel cx={116} cy={277} r={21} />
      <Wheel cx={289} cy={277} r={21} />
    </svg>
  );
}

export function PastelMoto({ color = "#D9D1FA", shade = "#BCB0F0" }: { color?: string; shade?: string }) {
  return (
    <svg viewBox="28 178 190 124" width="100%" height="100%" aria-hidden>
      <path d="M58 268 L118 252 L120 262 L62 274 Z" fill="#9AA5B6" />
      <path d="M156 252 Q166 274 140 276 L104 272" fill="none" stroke="#B5BFCC" strokeWidth={4} strokeLinecap="round" />
      <path d="M104 268 L82 265 L78 274 L104 277 Z" fill="#C6CEDA" />
      <path d="M118 252 L138 214 L170 205 M120 240 L168 212" stroke={shade} strokeWidth={4} strokeLinecap="round" fill="none" />
      <path d="M112 236 L150 230 L160 252 L150 266 L120 266 L110 252 Z" fill="#8E99AB" />
      <path d="M132 234 L140 252 M140 232 L148 250" stroke="#B9C2CF" strokeWidth={1.6} />
      <path d="M160 222 L168 222 L166 246 L158 246 Z" fill="#7C8799" />
      <path d="M128 212 Q140 191 166 195 L175 206 L170 214 L132 218 Z" fill={color} stroke={shade} strokeWidth={1.4} />
      <path d="M80 216 Q102 209 130 213 L130 220 L86 222 Z" fill="#4A5366" />
      <path d="M80 216 L62 210 L64 216 L84 222 Z" fill={color} />
      <path d="M170 204 L184 271 M176 202 L190 270" stroke="#C9A35A" strokeWidth={3.2} strokeLinecap="round" />
      <path d="M164 192 L178 186 L185 190" stroke={INK} strokeWidth={2.4} strokeLinecap="round" fill="none" />
      <path d="M180 206 Q193 203 195 214 Q189 223 180 218 Z" fill="#FFF6D8" stroke={shade} />
      <path d="M162 252 Q186 239 207 252" stroke={shade} strokeWidth={3} fill="none" strokeLinecap="round" />
      <Wheel cx={60} cy={271} r={27} spokes={6} />
      <Wheel cx={186} cy={271} r={27} spokes={6} />
    </svg>
  );
}

export function PastelScooter({ color = "#FFD6C4", shade = "#F4B9A0" }: { color?: string; shade?: string }) {
  return (
    <svg viewBox="0 140 176 162" width="100%" height="100%" aria-hidden>
      <path d="M40 282 L70 278 L72 286 L42 288 Z" fill="#C6CEDA" />
      <path d="M28 266 L64 266 L60 280 L36 282 Z" fill="#8E99AB" />
      <path d="M10 262 Q2 236 26 226 Q60 220 86 222 Q100 224 98 240 L94 258 Q90 266 80 266 L22 266 Q12 266 10 262 Z" fill={color} stroke={shade} strokeWidth={1.4} />
      <path d="M18 220 Q50 207 96 214 L94 222 L22 226 Z" fill="#6E5A52" />
      <path d="M94 260 L124 260 L124 266 L94 266 Z" fill="#B5BFCC" />
      <path d="M122 264 Q124 236 130 214 L141 209 Q138 236 134 264 Z" fill={color} stroke={shade} strokeWidth={1.4} />
      <path d="M140 210 L148 276 M136 211 L140 199" stroke="#9AA5B6" strokeWidth={3} strokeLinecap="round" />
      <path d="M126 194 Q140 188 158 194 L156 200 L128 200 Z" fill={color} stroke={shade} />
      <path d="M150 194 L160 196 L158 202 L150 200 Z" fill="#FFF6D8" />
      <path d="M132 191 L128 180 M124 178 L132 180" stroke={INK} strokeWidth={1.6} strokeLinecap="round" />
      <path d="M126 272 Q148 248 170 268 L166 270 Q148 256 130 274 Z" fill={color} stroke={shade} />
      <path d="M8 240 L4 244 L10 248 Z" fill="#F7B9A8" />
      <Wheel cx={30} cy={276} r={22} spokes={5} />
      <Wheel cx={148} cy={276} r={22} spokes={5} />
    </svg>
  );
}