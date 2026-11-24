import { useEffect, useRef, useState } from "react";

/** Smoothly animates a number toward `target`. Respects reduced motion via `instant`. */
export function useCountUp(target: number, duration = 900, instant = false) {
  const [value, setValue] = useState(target);
  const from = useRef(target);

  useEffect(() => {
    if (instant) {
      from.current = target;
      setValue(target);
      return;
    }

    const start = performance.now();
    const origin = from.current;
    let raf = 0;
    let done = false;

    const finish = () => {
      if (done) return;
      done = true;
      from.current = target;
      setValue(target);
    };

    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      if (t >= 1) {
        finish();
        return;
      }
      const eased = 1 - Math.pow(1 - t, 3);
      from.current = Math.round(origin + (target - origin) * eased);
      setValue(from.current);
      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    // Rete di sicurezza: se il rAF viene sospeso (scroll rapido su mobile,
    // tab in background) il valore finale viene comunque applicato.
    const safety = window.setTimeout(finish, duration + 300);

    return () => {
      cancelAnimationFrame(raf);
      window.clearTimeout(safety);
    };
  }, [target, duration, instant]);

  return value;
}
