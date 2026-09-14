import { useEffect, useRef } from "react";
import { useReducedMotion } from "framer-motion";
import { useIsMobile } from "@/hooks/use-mobile";

type Node = { x: number; y: number; vx: number; vy: number; glow: number };

/**
 * Extremely discreet "decision engine" layer: a few nodes, hairline links and
 * slow travelling pulses. Disabled on mobile and with reduced motion.
 */
export function DecisionNetwork({ className }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const reduce = useReducedMotion();
  const isMobile = useIsMobile();
  const active = !reduce && !isMobile;

  useEffect(() => {
    if (!active) return;
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let w = 0;
    let h = 0;
    let raf = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const nodes: Node[] = [];
    const pulses: { a: number; b: number; t: number; speed: number }[] = [];

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();
    const count = 16;
    for (let i = 0; i < count; i++) {
      nodes.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.025,
        vy: (Math.random() - 0.5) * 0.025,
        glow: 0,
      });
    }

    const LINK = 150;
    let last = performance.now();
    let nextPulse = 900;

    const frame = (now: number) => {
      const dt = Math.min(now - last, 48);
      last = now;
      ctx.clearRect(0, 0, w, h);

      for (const n of nodes) {
        n.x += n.vx * (dt / 16);
        n.y += n.vy * (dt / 16);
        if (n.x < 0 || n.x > w) n.vx *= -1;
        if (n.y < 0 || n.y > h) n.vy *= -1;
        n.glow = Math.max(0, n.glow - dt / 2200);
      }

      ctx.lineWidth = 1;
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i]!;
          const b = nodes[j]!;
          const d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d > LINK) continue;
          ctx.strokeStyle = `rgba(17, 24, 39, ${(1 - d / LINK) * 0.032})`;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }

      for (const n of nodes) {
        ctx.fillStyle = `rgba(59, 199, 180, ${0.06 + n.glow * 0.18})`;
        ctx.beginPath();
        ctx.arc(n.x, n.y, 1.6 + n.glow * 1.2, 0, Math.PI * 2);
        ctx.fill();
      }

      nextPulse -= dt;
      if (nextPulse <= 0 && pulses.length < 2) {
        nextPulse = 2600 + Math.random() * 2600;
        const a = Math.floor(Math.random() * nodes.length);
        const candidates = nodes
          .map((n, i) => ({ i, d: Math.hypot(n.x - nodes[a]!.x, n.y - nodes[a]!.y) }))
          .filter((c) => c.i !== a && c.d < LINK);
        const pick = candidates[Math.floor(Math.random() * candidates.length)];
        if (pick) pulses.push({ a, b: pick.i, t: 0, speed: 0.00026 });
      }

      for (let p = pulses.length - 1; p >= 0; p--) {
        const pulse = pulses[p]!;
        pulse.t += pulse.speed * dt * 16;
        const a = nodes[pulse.a]!;
        const b = nodes[pulse.b]!;
        const x = a.x + (b.x - a.x) * pulse.t;
        const y = a.y + (b.y - a.y) * pulse.t;
        ctx.fillStyle = "rgba(59, 199, 180, 0.28)";
        ctx.beginPath();
        ctx.arc(x, y, 1.8, 0, Math.PI * 2);
        ctx.fill();
        if (pulse.t >= 1) {
          b.glow = 1;
          pulses.splice(p, 1);
        }
      }

      raf = requestAnimationFrame(frame);
    };

    raf = requestAnimationFrame(frame);
    window.addEventListener("resize", resize);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, [active]);

  if (!active) return null;

  return (
    <canvas
      ref={ref}
      aria-hidden
      className={className}
      style={{ opacity: 0.5 }}
    />
  );
}