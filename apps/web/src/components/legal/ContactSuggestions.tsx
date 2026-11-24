import { useMemo, useState, useId } from "react";
import { Plus } from "lucide-react";
import { suggestedFaqs } from "@/lib/contact-intelligence";
import { Button } from "@/components/ui/button";

export function ContactSuggestions({ message, onResolved }: { message: string; onResolved: () => void }) {
  const [openQuestion, setOpenQuestion] = useState<string | null>(null);
  const id = useId();
  const results = useMemo(() => suggestedFaqs(message), [message]);
  return <>
    <p aria-live="polite" aria-atomic="true" className="sr-only">{results.length ? `${results.length} ${results.length === 1 ? "risposta che potrebbe aiutarti" : "risposte che potrebbero aiutarti"}` : ""}</p>
    {results.length > 0 && <section aria-labelledby="contact-suggestions" className="mt-5 border-t border-border pt-5">
      <h2 id="contact-suggestions" className="font-heading text-sm font-semibold">Forse ti basta questo</h2>
      <div className="mt-2">{results.map((faq, index) => {
        const open = openQuestion === faq.q;
        const panelId = `${id}-${index}`;
        return <div key={faq.q} className="group border-b border-border">
          <h3 className="font-normal">
            <Button type="button" variant="ghost" aria-expanded={open} aria-controls={panelId} onClick={() => setOpenQuestion(open ? null : faq.q)} className="h-auto min-h-11 w-full justify-start gap-4 rounded-none px-0 py-6 text-left whitespace-normal hover:bg-transparent">
              <span aria-hidden="true" className="font-heading text-xs font-semibold tabular-nums text-brand-ink">{String(index + 1).padStart(2, "0")}</span>
              <span className="min-w-0 flex-1 text-sm font-semibold">{faq.q}</span>
              <span className="grid size-7 shrink-0 place-items-center rounded-full border border-border"><Plus aria-hidden="true" className={`size-3.5 transition-transform duration-300 ${open ? "rotate-45" : ""}`} /></span>
            </Button>
          </h3>
          <div id={panelId} hidden={!open} className="pb-4 pl-8">
            <p className="text-[0.8125rem] leading-relaxed text-muted-foreground">{faq.a}</p>
            <Button type="button" variant="link" className="h-11 px-0 text-brand-ink" onClick={onResolved}>Sì, mi basta</Button>
          </div>
        </div>;
      })}</div>
    </section>}
  </>;
}