const eurFormatter = new Intl.NumberFormat('it-IT', {
  currency: 'EUR',
  maximumFractionDigits: 0,
  style: 'currency',
})

const integerFormatter = new Intl.NumberFormat('it-IT')

export function formatCurrency(value: number | null) {
  return value === null ? 'Non disponibile' : eurFormatter.format(value)
}

export function formatNumber(value: number | null) {
  return value === null ? 'Non disponibile' : integerFormatter.format(value)
}

export function optionalNumber(value: string) {
  return value.trim() === '' ? undefined : Number(value)
}

export function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}
