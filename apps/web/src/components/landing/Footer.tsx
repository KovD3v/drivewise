import { motion, useReducedMotion } from "framer-motion";
import { Link } from "@tanstack/react-router";
import { Logo } from "./Logo";
import { viewportOnce } from "@/lib/motion";

const routeLinks = [
  { label: "Privacy", to: "/privacy" as const },
  { label: "Termini", to: "/terms" as const },
  { label: "Contatti", to: "/contact" as const },
];

export function Footer() {
  const reduce = useReducedMotion();
  return (
    <motion.footer
      initial={reduce ? { opacity: 1 } : { opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={viewportOnce}
      transition={{ duration: reduce ? 0 : 0.6 }}
      className="border-t border-border/60 px-6 py-20 sm:px-8"
    >
      <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-10 sm:flex-row">
        <Logo />
        <nav aria-label="Footer" className="flex flex-wrap justify-center gap-9">
          {routeLinks.map((l) => (
            <Link
              key={l.label}
              to={l.to}
              className="inline-flex min-h-11 items-center py-3 text-[0.8125rem] text-muted-foreground transition-colors duration-300 hover:text-foreground sm:min-h-[1.5rem] sm:py-1"
            >
              {l.label}
            </Link>
          ))}
          <a
            href="#faq"
            className="inline-flex min-h-11 items-center py-3 text-[0.8125rem] text-muted-foreground transition-colors duration-300 hover:text-foreground sm:min-h-[1.5rem] sm:py-1"
          >
            FAQ
          </a>
        </nav>
        <p className="text-[0.75rem] text-muted-foreground">
          © {new Date().getFullYear()} DriveWise
        </p>
      </div>
    </motion.footer>
  );
}