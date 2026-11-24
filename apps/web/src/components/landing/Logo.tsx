import { cn } from "@/lib/utils";

export function Logo({
  compact,
  className,
}: {
  compact?: boolean;
  className?: string;
}) {
  return (
    <span className={cn("flex items-center gap-2.5 sm:gap-3", className)}>
      <span className="relative inline-flex">
        <span
          aria-hidden
          className="grid size-9 place-items-center rounded-[11px] bg-primary text-primary-foreground sm:size-10 sm:rounded-[13px]"
        >
          <svg
            viewBox="0 0 24 24"
            className="size-4 sm:size-[1.15rem]"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
          >
            <path d="M4 16.5c4.5 0 6-11 8-11s3.5 11 8 11" />
          </svg>
        </span>
        <span
          aria-hidden
          className="absolute -right-1.5 -bottom-1.5 grid size-4 place-items-center rounded-full bg-foreground text-background ring-[3px] ring-background sm:size-[18px]"
        >
          <span className="text-[7px] font-extrabold leading-none sm:text-[8px]">IT</span>
        </span>
      </span>

      {!compact && (
        <span className="flex flex-col leading-none">
          <span className="font-heading text-[1.125rem] font-extrabold tracking-tight sm:text-[1.25rem]">
            DriveWise
          </span>
          <span className="hidden text-[0.75rem] font-medium text-muted-foreground sm:block sm:text-[0.8rem]">
            Italia
          </span>
        </span>
      )}
    </span>
  );
}
