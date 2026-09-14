/** Check con stroke-draw, usato in tutte le opzioni selezionate del wizard. */
export function OptionCheck({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 16 16"
      aria-hidden
      className={`dw-check-draw size-3.5 shrink-0 ${className}`}
      fill="none"
      stroke="currentColor"
      strokeWidth={2.2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M3 8.6 6.4 12 13 4.6" pathLength={1} />
    </svg>
  );
}
