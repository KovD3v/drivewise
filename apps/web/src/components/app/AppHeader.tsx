import { Link } from "@tanstack/react-router";
import { Logo } from "@/components/landing/Logo";
import { cn } from "@/lib/utils";

/** Header minimale condiviso da tutte le pagine non-landing: stesso logo della Landing. */
export function AppHeader({
  label,
  maxWidth = "max-w-[74rem]",
  sticky = false,
}: {
  label?: string;
  maxWidth?: string;
  sticky?: boolean;
}) {
  return (
    <header
      className={cn(
        "border-b border-border/60 bg-background/85 backdrop-blur",
        sticky && "sticky top-0 z-40",
      )}
    >
      <div
        className={cn(
          "mx-auto flex h-16 w-full items-center justify-between gap-4 px-6 py-3 sm:h-18 sm:px-8 sm:py-4",
          maxWidth,
        )}
      >
        <Link to="/" aria-label="DriveWise — torna alla home" className="shrink-0">
          <Logo />
        </Link>
        {label && (
          <span className="truncate text-[0.75rem] tracking-[0.14em] text-muted-foreground uppercase">
            {label}
          </span>
        )}
      </div>
    </header>
  );
}
