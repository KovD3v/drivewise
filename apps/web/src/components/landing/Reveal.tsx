import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";
import { EASE, viewportOnce } from "@/lib/motion";

type RevealProps = {
  children: ReactNode;
  delay?: number;
  className?: string;
  y?: number;
};

export function Reveal({ children, delay = 0, className, y = 18 }: RevealProps) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? { opacity: 1, y: 0 } : { opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={viewportOnce}
      transition={{ duration: reduce ? 0 : 0.8, delay: reduce ? 0 : delay, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

/**
 * Staggered reveal container: animates eyebrow → headline → description → content
 * in sequence. Children should be <RevealItem> elements.
 */
export function RevealGroup({
  children,
  className,
  stagger = 0.14,
  delayChildren = 0,
  as,
}: {
  children: ReactNode;
  className?: string;
  stagger?: number;
  delayChildren?: number;
  as?: "div" | "ul" | "ol";
}) {
  const reduce = useReducedMotion();
  const Comp = motion[as ?? "div"];
  return (
    <Comp
      className={className}
      initial="hidden"
      whileInView="show"
      viewport={viewportOnce}
      variants={{
        hidden: {},
        show: {
          transition: reduce
            ? {}
            : { staggerChildren: stagger, delayChildren },
        },
      }}
    >
      {children}
    </Comp>
  );
}

export function RevealItem({
  children,
  className,
  y = 18,
  as,
}: {
  children: ReactNode;
  className?: string;
  y?: number;
  as?: "div" | "li" | "span" | "p";
}) {
  const reduce = useReducedMotion();
  const Comp = motion[as ?? "div"];
  return (
    <Comp
      className={className}
      variants={{
        hidden: reduce ? { opacity: 1, y: 0 } : { opacity: 0, y },
        show: { opacity: 1, y: 0, transition: { duration: reduce ? 0 : 0.75, ease: EASE } },
      }}
    >
      {children}
    </Comp>
  );
}