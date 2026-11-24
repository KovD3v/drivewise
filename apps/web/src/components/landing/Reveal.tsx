import type { ReactNode } from "react";
import { useScrollReveal } from "@/hooks/use-scroll-reveal";

type RevealProps = { children: ReactNode; delay?: number; className?: string; y?: number };
export function Reveal({ children, className = "" }: RevealProps) {
  const { ref } = useScrollReveal<HTMLDivElement>();
  return <div ref={ref} className={`dw-scroll-reveal ${className}`}>{children}</div>;
}
export function RevealGroup({ children, className = "", as: Comp = "div" }: {
  children: ReactNode; className?: string; stagger?: number; delayChildren?: number; as?: "div" | "ul" | "ol";
}) {
  return <Comp className={className}>{children}</Comp>;
}
export function RevealItem({ children, className = "", as: Comp = "div" }: {
  children: ReactNode; className?: string; y?: number; as?: "div" | "li" | "span" | "p";
}) {
  const { ref } = useScrollReveal<HTMLElement>();
  // Callback ref supports all semantic element choices without casting their DOM types.
  return <Comp ref={(el: HTMLElement | null) => { ref.current = el; }} className={`dw-scroll-reveal ${className}`}>{children}</Comp>;
}
