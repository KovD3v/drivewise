import type { ListPrice } from '@/api/drivewise'
import { Card, KeyValue } from '@/components/vehicle/primitives'

// Copy and blocks shared by the Advisor result and the vehicle detail for a
// price taken from a public price list instead of a seller's offer (ADR-013).

const wholeEurFormatter = new Intl.NumberFormat('it-IT', {
  currency: 'EUR',
  maximumFractionDigits: 0,
  style: 'currency',
})

const centsEurFormatter = new Intl.NumberFormat('it-IT', {
  currency: 'EUR',
  minimumFractionDigits: 2,
  style: 'currency',
})

/** "12.200 €" for a whole amount, "12.200,01 €" when the price list has cents. */
export function formatListEur(value: number) {
  return (Number.isInteger(value) ? wholeEurFormatter : centsEurFormatter).format(value)
}

const dateFormatter = new Intl.DateTimeFormat('it-IT', {
  day: '2-digit',
  month: 'short',
  timeZone: 'UTC',
  year: 'numeric',
})

export const UPPER_VALUE_NOTE = 'valore più alto dichiarato'

export type ScalarBasis = 'exact' | 'interval_upper' | null | undefined

export function formatListDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : dateFormatter.format(date)
}

/** The plain notes a list price needs: never an offer, and how it was obtained. */
export function listPriceNotes(price: ListPrice): string[] {
  const notes = ['È il prezzo del listino ufficiale, non un\'offerta di un venditore.']
  if (price.derivation === 'computed_from_excl_vat') {
    notes.push(
      price.vat_rate_percent != null
        ? `Il listino indica il prezzo senza IVA: abbiamo aggiunto l'IVA al ${price.vat_rate_percent}%.`
        : "Il listino indica il prezzo senza IVA: abbiamo aggiunto l'IVA.",
    )
  }
  if (price.derivation === 'computed_from_turnkey') {
    notes.push(
      `Il listino indica il prezzo chiavi in mano (${formatListEur(price.printed_amount_eur)}): abbiamo tolto i costi di messa su strada.`,
    )
  }
  if (price.substitute_note) {
    notes.push(
      'Questa versione non è più in listino. Il prezzo è quello della versione attuale più simile.',
    )
  }
  return notes
}

/** How the catalogue obtained a consumption figure, in words a buyer reads. */
export function basisLabel(basis: ScalarBasis) {
  if (basis === 'exact') return 'valore dichiarato dalla fonte'
  if (basis === 'interval_upper') return `${UPPER_VALUE_NOTE}: la fonte indica un intervallo`
  return 'base del valore non indicata'
}

/** Rows for KeyValue: the list price, its version and the date the price list is valid from. */
export function listPriceRows(price: ListPrice) {
  return [
    { label: 'Prezzo di listino', value: formatListEur(price.price_eur) },
    { label: 'Versione in listino', value: price.trim_label },
    { label: 'Listino valido dal', value: formatListDate(price.price_list_valid_from) },
  ]
}

/** The list price with its date, notes and a link to the price list. Never an offer. */
export function ListPricePanel({ price }: { price: ListPrice }) {
  return (
    <Card>
      <KeyValue rows={listPriceRows(price)} />
      <ul className="mt-5 space-y-2 text-[0.85rem] text-muted-foreground">
        {listPriceNotes(price).map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
      <a
        className="mt-4 inline-flex text-[0.85rem] font-medium text-foreground underline underline-offset-4"
        href={price.source_url}
        rel="noopener noreferrer"
        target="_blank"
      >
        Apri il listino di {price.source_name}
      </a>
    </Card>
  )
}

/** One licensed source behind the facts on a screen. */
export type Credit = { name: string; url: string | null; license: string | null }

/** One line per licensed source: its name, a link when there is one, and its licence. */
export function SourceCredits({ credits, className }: { credits: Credit[]; className?: string }) {
  const unique = new Map<string, Credit>()
  for (const credit of credits) {
    if (credit.license && !unique.has(credit.name)) unique.set(credit.name, credit)
  }
  if (unique.size === 0) return null
  return (
    <div className={className}>
      <h3 className="text-[0.8rem] font-semibold tracking-[0.12em] text-muted-foreground uppercase">
        Fonti dei dati
      </h3>
      <ul className="mt-3 space-y-2 text-[0.85rem]">
        {[...unique.values()].map((credit) => (
          <li key={credit.name} className="flex flex-wrap gap-x-2">
            {credit.url ? (
              <a
                className="font-medium text-foreground underline underline-offset-4"
                href={credit.url}
                rel="noopener noreferrer"
                target="_blank"
              >
                {credit.name}
              </a>
            ) : (
              <span className="font-medium text-foreground">{credit.name}</span>
            )}
            <span className="text-muted-foreground">Licenza: {credit.license}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
