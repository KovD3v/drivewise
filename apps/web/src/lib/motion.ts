export const EASE = [0.22, 1, 0.36, 1] as const;

/** Standard scroll-reveal transition used across the landing page. */
export const revealTransition = { duration: 0.6, ease: EASE };

/** Viewport config: reveal once, slightly before the element is fully visible. */
export const viewportOnce = { once: true, margin: "-80px" } as const;

/** Container that staggers its direct motion children. */
export const staggerContainer = (stagger = 0.09, delayChildren = 0) => ({
  hidden: {},
  show: {
    transition: { staggerChildren: stagger, delayChildren },
  },
});

/** Standard child item: fade + small translateY. */
export const fadeUpItem = (y = 18) => ({
  hidden: { opacity: 0, y },
  show: { opacity: 1, y: 0, transition: revealTransition },
});

export const reducedItem = {
  hidden: { opacity: 1, y: 0 },
  show: { opacity: 1, y: 0 },
};