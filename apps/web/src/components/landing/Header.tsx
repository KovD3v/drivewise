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

export function Header({ homeNavigation = false }: { homeNavigation?: boolean }) {
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
        homeNavigation && "bg-background duration-200 motion-reduce:transition-none",
        scrolled
          ? "border-b border-border bg-card/80 backdrop-blur-md"
          : "border-b border-transparent",
      )}
    >
      <div className="mx-auto flex h-18 w-full max-w-6xl items-center justify-between px-6 py-4 sm:h-20 sm:px-8 sm:py-5">
        <a href={homeNavigation ? "/" : "#top"} aria-label={homeNavigation ? "DriveWise, torna alla home" : "DriveWise, torna in cima"} onClick={homeNavigation ? undefined : (e) => onNavClick(e, "#top")}>
          <Logo />
        </a>

        <div className="hidden items-center gap-6 md:flex">
          <nav aria-label="Principale" className="flex items-center gap-9">
            {links.map((l) => (
              <a
                key={l.href}
                href={homeNavigation ? `/${l.href}` : l.href}
                onClick={homeNavigation ? undefined : (e) => onNavClick(e, l.href)}
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {l.label}
              </a>
            ))}
          </nav>

          {/* azioni: profilo (secondaria) + Inizia (principale), separate dai link */}
          <div className="flex items-center gap-2.5 border-l border-border/70 pl-6">
            <AppTransitionLink
              to="/app/me"
              ariaLabel="Vai a My DriveWise"
              steps={["Accesso al tuo profilo...", "Caricamento dashboard...", "Pronto."]}
              className={cn(
                "group inline-flex h-9 items-center gap-2 rounded-full pr-3.5 pl-1.5",
                "border border-border/70 bg-card/60 backdrop-blur-md",
                "text-sm text-foreground transition-all duration-300 ease-out",
                "hover:border-primary/50 hover:bg-primary/8 hover:text-foreground",
              )}
            >
              <span className="relative grid size-6 place-items-center rounded-full bg-muted/70 transition-colors group-hover:bg-primary/15">
                <UserCircle
                  className="size-4 text-muted-foreground transition-colors group-hover:text-primary"
                  strokeWidth={1.8}
                />
                <span
                  className="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-primary ring-2 ring-card"
                  aria-hidden="true"
                />
              </span>
              My DriveWise
            </AppTransitionLink>
            <CtaButton
              to="/app/start"
              size="sm"
              onClick={() => track("landing_start_cta_click", { source: "header" })}
            >
              Inizia
            </CtaButton>
          </div>
        </div>

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
                href={homeNavigation ? `/${l.href}` : l.href}
                onClick={(e) => {
                  if (homeNavigation) { setOpen(false); return; }
                  e.preventDefault();
                  setOpen(false);
                  window.history.replaceState(null, "", l.href);
                  window.setTimeout(() => scrollToHash(l.href), 60);
                }}
                className="rounded-xl px-2 py-3 text-[0.95rem] text-foreground hover:bg-muted"
              >
                {l.label}
              </a>
            ))}
            <AppTransitionLink
              to="/app/me"
              steps={["Accesso al tuo profilo...", "Caricamento dashboard...", "Pronto."]}
              onNavigate={() => setOpen(false)}
              className={cn(
                "flex items-center gap-3 rounded-xl px-2 py-3 text-[0.95rem] text-foreground",
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
