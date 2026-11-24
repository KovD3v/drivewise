import { useEffect, useRef, useState } from "react";
import { REVEAL_DURATION_MS, REVEAL_OBSERVER_OPTIONS, revealImmediately } from "@/lib/reveal-policy";

/** Visible SSR baseline; only unseen, below-fold elements are armed after mount. */
export function useScrollReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [state, setState] = useState({ revealed: false, immediate: false });
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    document.documentElement.classList.add("js-reveal");
    el.style.setProperty("--dw-reveal-duration", `${REVEAL_DURATION_MS}ms`);
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    let finished = false;
    const isDestination = (hash: string) => {
      if (!hash) return false;
      let id: string;
      try { id = decodeURIComponent(hash.slice(1)); } catch { return false; }
      const target = document.getElementById(id);
      const section = target?.closest("section") ?? target;
      return Boolean(section && (section.contains(el) || el.contains(section)));
    };
    const show = (immediate: boolean) => {
      if (finished && !immediate) return;
      finished = true;
      if (immediate) el.classList.add("dw-reveal-instant");
      el.classList.remove("dw-reveal-pending");
      el.classList.add("is-in");
      setState({ revealed: true, immediate });
      observer.disconnect();
    };
    const observer = new IntersectionObserver(([entry]) => {
      if (entry?.isIntersecting) show(entry.boundingClientRect.top < 0);
    }, REVEAL_OBSERVER_OPTIONS);
    const checkAbove = () => {
      if (!finished && el.getBoundingClientRect().top < 0) show(true);
    };
    const onHash = () => { if (isDestination(window.location.hash)) show(true); };
    const onClick = (event: MouseEvent) => {
      const anchor = event.target instanceof Element ? event.target.closest("a[href]") : null;
      if (!anchor) return;
      const url = new URL(anchor.getAttribute("href") ?? "", window.location.href);
      if (url.origin === window.location.origin && url.pathname === window.location.pathname && isDestination(url.hash)) show(true);
    };
    const onPreference = () => { if (mq.matches) show(true); };
    const top = el.getBoundingClientRect().top;
    if (revealImmediately(top, isDestination(window.location.hash), mq.matches)) show(true);
    else {
      el.classList.add("dw-reveal-pending");
      observer.observe(el);
    }
    document.addEventListener("click", onClick, true);
    window.addEventListener("hashchange", onHash);
    window.addEventListener("scroll", checkAbove, { passive: true });
    mq.addEventListener("change", onPreference);
    return () => {
      observer.disconnect();
      document.removeEventListener("click", onClick, true);
      window.removeEventListener("hashchange", onHash);
      window.removeEventListener("scroll", checkAbove);
      mq.removeEventListener("change", onPreference);
    };
  }, []);
  return { ref, ...state };
}