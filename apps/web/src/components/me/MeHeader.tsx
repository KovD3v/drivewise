import { Link } from "@tanstack/react-router";
import { UserCircle } from "lucide-react";
import { Logo } from "@/components/landing/Logo";
import { cn } from "@/lib/utils";

/** Header interno di My DriveWise: logo cliccabile verso il sito + badge stato utente. */
export function MeHeader({ label = "My DriveWise" }: { label?: string }) {
  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 w-full max-w-[78rem] items-center justify-between gap-4 px-6 py-3 sm:h-18 sm:px-8 sm:py-4">
        <Link to="/" aria-label="DriveWise — torna al sito" className="shrink-0">
          <Logo />
        </Link>
        <div className="flex items-center gap-4">
          <span className="hidden text-[0.72rem] tracking-[0.14em] text-muted-foreground uppercase sm:inline">
            {label}
          </span>
          <span
            className={cn(
              "relative grid size-9 place-items-center rounded-full",
              "border border-border/60 bg-card/40 backdrop-blur-md",
            )}
          >
            <UserCircle className="size-[1.15rem] text-primary" strokeWidth={1.8} />
            <span
              aria-hidden
              className="animate-status-pulse absolute -top-0.5 -right-0.5 size-2.5 rounded-full bg-primary ring-2 ring-card"
            />
          </span>
        </div>
      </div>
    </header>
  );
}