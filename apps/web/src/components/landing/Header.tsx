import { useEffect, useState } from "react";
import { Menu, X, UserCircle } from "lucide-react";
import { Logo } from "./Logo";
import { AppTransitionLink } from "@/components/transition/AppTransitionLink";
import { CtaButton } from "./CtaButton";
import { cn } from "@/lib/utils";
import { track } from "@/lib/analytics";

const links = [
  { label: "Come funziona", href: "#come-funziona" },
  { label: "Perché DriveWise", href: "#perche" },
  { label: "FAQ", href: "#faq" },
];

export function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Scroll to the section on click and on direct hash navigation.
  const scrollToHash = (hash: string) => {
    const el = document.querySelector(hash);
    if (!el) return false;
    const top = el.getBoundingClientRect().top + window.scrollY - 88;
    window.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
    return true;
  };

  const onNavClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (!href.startsWith("#")) return;
    if (href === "#top") {
      e.preventDefault();
      window.history.replaceState(null, "", href);
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    if (scrollToHash(href)) {
      e.preventDefault();
      window.history.replaceState(null, "", href);
    }
  };

  useEffect(() => {
    if (!window.location.hash) return;
    const hash = window.location.hash;
    const t = window.setTimeout(() => scrollToHash(hash), 150);
    return () => window.clearTimeout(t);
  }, []);

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition-all duration-500",
        scrolled
          ? "border-b border-border bg-card/80 backdrop-blur-md"
          : "border-b border-transparent",
      )}
    >
      <div className="mx-auto flex h-18 w-full max-w-6xl items-center justify-between px-6 py-4 sm:h-20 sm:px-8 sm:py-5">
        <a href="#top" aria-label="DriveWise, torna in cima" onClick={(e) => onNavClick(e, "#top")}>
          <Logo />
        </a>

        <nav aria-label="Principale" className="hidden items-center gap-9 md:flex">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={(e) => onNavClick(e, l.href)}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              {l.label}
            </a>
          ))}
          <AppTransitionLink
            to="/app/me"
            ariaLabel="Vai a My DriveWise"
            steps={["Accesso al tuo profilo...", "Caricamento dashboard...", "Pronto."]}
            className="group relative mr-3 flex items-center justify-center"
          >
            <span className="sr-only">Vai a My DriveWise</span>
            <span
              className={cn(
                "animate-badge-pop relative grid size-9 place-items-center rounded-full",
                "border border-border/60 bg-card/40 backdrop-blur-md",
                "transition-all duration-300 ease-out",
                "group-hover:border-primary/50 group-hover:bg-primary/8 group-hover:shadow-[0_0_24px_-8px_var(--color-primary)]",
              )}
            >
              <UserCircle
                className="size-[1.15rem] text-muted-foreground transition-all duration-300 group-hover:scale-[1.08] group-hover:text-primary"
                strokeWidth={1.8}
              />
              <span
                className={cn(
                  "absolute -right-0.5 -top-0.5 z-10 size-2.5 rounded-full bg-primary",
                  "ring-2 ring-card",
                  "animate-status-pulse",
                )}
                aria-hidden="true"
              />
            </span>
            <span
              className={cn(
                "pointer-events-none absolute left-1/2 top-full z-50 mt-3 -translate-x-1/2 whitespace-nowrap",
                "rounded-md bg-foreground px-2.5 py-1.5 text-[0.7rem] font-medium text-background opacity-0",
                "shadow-lg transition-all duration-200 group-hover:opacity-100",
              )}
            >
              Vai a My DriveWise
              <span className="absolute -top-1 left-1/2 size-2 -translate-x-1/2 rotate-45 bg-foreground" />
            </span>
          </AppTransitionLink>
          <CtaButton
            to="/app/start"
            size="sm"
            onClick={() => track("landing_start_cta_click", { source: "header" })}
          >
            Inizia
          </CtaButton>
        </nav>

        <button
          type="button"
          aria-label={open ? "Chiudi menu" : "Apri menu"}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          className="grid size-10 place-items-center rounded-full border border-border bg-card md:hidden"
        >
          {open ? <X className="size-4" /> : <Menu className="size-4" />}
        </button>
      </div>

      {open && (
        <div className="border-t border-border bg-card px-6 pb-6 md:hidden">
          <nav aria-label="Mobile" className="flex flex-col gap-1 py-2">
            {links.map((l) => (
              <a
                key={l.label}
                href={l.href}
                onClick={(e) => {
                  e.preventDefault();
                  setOpen(false);
                  window.history.replaceState(null, "", l.href);
                  window.setTimeout(() => scrollToHash(l.href), 60);
                }}
                className="rounded-xl px-2 py-3 text-[0.95rem] text-foreground/80 hover:bg-muted"
              >
                {l.label}
              </a>
            ))}
            <AppTransitionLink
              to="/app/me"
              steps={["Accesso al tuo profilo...", "Caricamento dashboard...", "Pronto."]}
              onNavigate={() => setOpen(false)}
              className={cn(
                "flex items-center gap-3 rounded-xl px-2 py-3 text-[0.95rem] text-foreground/80",
                "transition-colors hover:bg-muted",
              )}
            >
              <span className="grid size-8 place-items-center rounded-full border border-border/80 bg-card/80">
                <UserCircle className="size-4 text-muted-foreground" strokeWidth={1.8} />
              </span>
              My DriveWise
            </AppTransitionLink>
          </nav>
          <CtaButton
            to="/app/start"
            className="w-full"
            onClick={() => {
              track("landing_start_cta_click", { source: "header_mobile" });
              setOpen(false);
            }}
          >
            Inizia
          </CtaButton>
        </div>
      )}
    </header>
  );
}