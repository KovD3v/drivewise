import type { ListPrice } from '@/api/drivewise'

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

/** "5,9 l/100 km" plus the ADR-018 note when the figure tops an interval. */
export function withBasis(text: string, basis: ScalarBasis) {
  return basis === 'interval_upper' ? `${text} (${UPPER_VALUE_NOTE})` : text
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

export function ListPriceFacts({ price }: { price: ListPrice }) {
  return (
    <>
      <div>
        <dt>Prezzo di listino</dt>
        <dd>{formatListEur(price.price_eur)}</dd>
      </div>
      <div>
        <dt>Versione in listino</dt>
        <dd>{price.trim_label}</dd>
      </div>
      <div>
        <dt>Listino valido dal</dt>
        <dd>{formatListDate(price.price_list_valid_from)}</dd>
      </div>
    </>
  )
}

export function ListPriceNotes({ price }: { price: ListPrice }) {
  return (
    <div className="list-price-notes">
      <ul>
        {listPriceNotes(price).map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
      <a className="text-link source-link" href={price.source_url} rel="noreferrer" target="_blank">
        Apri il listino
      </a>
    </div>
  )
}

export type Credit = { name: string; license?: string | null }

/** One line per licensed source, with the licence or attribution text it requires. */
export function SourceCredits({ credits }: { credits: Credit[] }) {
  const unique = new Map<string, Credit>()
  for (const credit of credits) {
    if (!credit.license) continue
    const key = `${credit.name}|${credit.license ?? ''}`
    if (!unique.has(key)) unique.set(key, credit)
  }
  if (unique.size === 0) {
    return null
  }
  return (
    <div className="source-credits">
      <h5>Crediti delle fonti</h5>
      <ul>
        {[...unique.values()].map((credit) => (
          <li key={`${credit.name}|${credit.license ?? ''}`}>
            <strong>{credit.name}</strong>
            <span>{credit.license}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
