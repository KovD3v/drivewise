import { cn } from "@/lib/utils";
import { useEffect, useRef, useState } from "react";
import type { ContactField } from "@/lib/contact-validation";

export const contactFieldClass = "w-full rounded-2xl border border-border bg-background px-4 py-3 text-[0.95rem] text-foreground placeholder:text-muted-foreground transition-all duration-150 motion-reduce:transition-none focus:-translate-y-0.5 motion-reduce:focus:translate-y-0 focus:border-primary/50 focus:shadow-[var(--shadow-focus)]";
export function ContactInput({ name, label, value, error, onChange, onBlur, required = false, type = "text", autoComplete, help }: {
  name: ContactField; label: string; value: string; error?: string | undefined; onChange: (value: string) => void; onBlur: () => void;
  required?: boolean; type?: string; autoComplete?: string; help?: string | undefined;
}) {
  return <div>
    <label htmlFor={`contact-${name}`} className="text-[0.8125rem] font-medium">{label}{required ? "" : " (facoltativo)"}</label>
    <input id={`contact-${name}`} name={name} type={type} value={value} required={required} autoComplete={autoComplete} maxLength={name === "name" ? 100 : name === "email" ? 255 : name === "siteUrl" || name === "location" ? 500 : 200}
      className={cn(contactFieldClass, "mt-2")} onChange={(e) => onChange(e.target.value)} onBlur={onBlur} aria-invalid={Boolean(error)}
      aria-describedby={[error ? `contact-${name}-error` : "", help ? `contact-${name}-help` : ""].filter(Boolean).join(" ") || undefined} />
    {help && <p id={`contact-${name}-help`} className="mt-2 text-[0.8125rem] text-muted-foreground">{help}</p>}
    {error && <p id={`contact-${name}-error`} className="mt-2 text-xs text-destructive">{error}</p>}
  </div>;
}

export function ContactChips({ name, legend, options, value, onChange }: {
  name: string; legend: string; options: readonly string[]; value: string; onChange: (value: string) => void;
}) {
  const group = useRef<HTMLDivElement>(null);
  const [pill, setPill] = useState({ x: 0, y: 0, width: 0, height: 0 });
  useEffect(() => {
    const el = group.current;
    if (!el) return;
    const measure = () => {
      const radio = el.querySelector<HTMLInputElement>('input:checked');
      const label = radio?.closest("label");
      if (label) setPill({ x: label.offsetLeft, y: label.offsetTop, width: label.offsetWidth, height: label.offsetHeight });
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, [value, options]);
  return <fieldset>
    <legend className="text-xs font-semibold tracking-[0.14em] text-muted-foreground uppercase">{legend}</legend>
    <div ref={group} className="relative mt-4 flex flex-wrap gap-2.5">
      <span aria-hidden="true" className="contact-chip-pill absolute rounded-full bg-primary" style={{ transform: `translate(${pill.x}px, ${pill.y}px)`, width: pill.width, height: pill.height }} />
      {options.map((option, index) => <label key={option} htmlFor={`contact-${name}-${index}`} className={cn(
        "relative flex min-h-11 cursor-pointer items-center rounded-full border px-4 py-2 text-[0.8125rem] transition-colors duration-200 motion-reduce:transition-none sm:min-h-9 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-focus-ink has-[:focus-visible]:outline-offset-2",
        value === option ? "border-primary bg-transparent text-primary-foreground shadow-[var(--shadow-soft)]" : "border-border bg-background text-muted-foreground hover:border-foreground/25 hover:text-foreground",
      )}>
        <input className="sr-only" type="radio" name={name} id={`contact-${name}-${index}`} checked={value === option} value={option} onChange={() => onChange(option)} />{option}
      </label>)}
    </div>
  </fieldset>;
}