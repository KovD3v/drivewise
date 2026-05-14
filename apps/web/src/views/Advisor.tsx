import { FormEvent, useMemo, useState } from 'react'
import { Link } from '@tanstack/react-router'

import {
  AdvisorDocumentEvidence,
  AdvisorPriority,
  AdvisorPrimaryUse,
  AdvisorRecommendationResponse,
  fetchAdvisorRecommendations,
} from '../api/drivewise'

const primaryUseOptions: Array<{ value: AdvisorPrimaryUse; label: string }> = [
  { value: 'city', label: 'City' },
  { value: 'highway', label: 'Highway' },
  { value: 'family', label: 'Family' },
  { value: 'work', label: 'Work' },
  { value: 'new_driver', label: 'New driver' },
]

const priorityOptions: Array<{ value: AdvisorPriority; label: string }> = [
  { value: 'price', label: 'Prezzo' },
  { value: 'consumption', label: 'Consumi' },
  { value: 'reliability', label: 'Affidabilita' },
  { value: 'space', label: 'Spazio' },
  { value: 'safety', label: 'Sicurezza' },
  { value: 'range', label: 'Autonomia' },
]

const eurFormatter = new Intl.NumberFormat('it-IT', {
  currency: 'EUR',
  maximumFractionDigits: 0,
  style: 'currency',
})

const integerFormatter = new Intl.NumberFormat('it-IT')

export function AdvisorPage() {
  const [budgetMin, setBudgetMin] = useState('')
  const [budgetMax, setBudgetMax] = useState('')
  const [primaryUse, setPrimaryUse] = useState<AdvisorPrimaryUse>('city')
  const [preferredFuelType, setPreferredFuelType] = useState('')
  const [preferredBodyStyle, setPreferredBodyStyle] = useState('')
  const [maxMileage, setMaxMileage] = useState('')
  const [priorities, setPriorities] = useState<AdvisorPriority[]>([])
  const [response, setResponse] = useState<AdvisorRecommendationResponse | null>(
    null,
  )
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = useMemo(() => Number(budgetMax) > 0 && !isLoading, [
    budgetMax,
    isLoading,
  ])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsLoading(true)
    setError(null)
    setResponse(null)

    try {
      const data = await fetchAdvisorRecommendations({
        budget_min_eur: optionalNumber(budgetMin),
        budget_max_eur: Number(budgetMax),
        primary_use: primaryUse,
        preferred_fuel_type: optionalString(preferredFuelType),
        preferred_body_style: optionalString(preferredBodyStyle),
        max_mileage: optionalNumber(maxMileage),
        priorities,
      })
      setResponse(data)
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Advisor request failed',
      )
    } finally {
      setIsLoading(false)
    }
  }

  function togglePriority(priority: AdvisorPriority) {
    setPriorities((current) =>
      current.includes(priority)
        ? current.filter((item) => item !== priority)
        : [...current, priority],
    )
  }

  return (
    <main className="advisor-shell">
      <header className="advisor-header">
        <Link className="text-link" to="/">
          Drivewise MVP
        </Link>
        <div>
          <p className="eyebrow">Deterministic advisor</p>
          <h1>Advisor MVP</h1>
          <p className="summary">
            Inserisci vincoli e priorita. Il backend calcola raccomandazioni
            spiegabili usando dati veicolo, listing e specifiche europee.
          </p>
        </div>
      </header>

      <section className="advisor-layout">
        <form className="advisor-form" onSubmit={handleSubmit}>
          <div className="form-grid">
            <label>
              Budget minimo
              <input
                inputMode="decimal"
                min="0"
                name="budget_min_eur"
                onChange={(event) => setBudgetMin(event.target.value)}
                placeholder="10000"
                type="number"
                value={budgetMin}
              />
            </label>

            <label>
              Budget massimo
              <input
                inputMode="decimal"
                min="1"
                name="budget_max_eur"
                onChange={(event) => setBudgetMax(event.target.value)}
                placeholder="25000"
                required
                type="number"
                value={budgetMax}
              />
            </label>

            <label>
              Uso principale
              <select
                name="primary_use"
                onChange={(event) =>
                  setPrimaryUse(event.target.value as AdvisorPrimaryUse)
                }
                required
                value={primaryUse}
              >
                {primaryUseOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Fuel type preferito
              <input
                name="preferred_fuel_type"
                onChange={(event) => setPreferredFuelType(event.target.value)}
                placeholder="electric"
                value={preferredFuelType}
              />
            </label>

            <label>
              Body style preferito
              <input
                name="preferred_body_style"
                onChange={(event) => setPreferredBodyStyle(event.target.value)}
                placeholder="city_car"
                value={preferredBodyStyle}
              />
            </label>

            <label>
              Chilometraggio massimo
              <input
                inputMode="numeric"
                min="0"
                name="max_mileage"
                onChange={(event) => setMaxMileage(event.target.value)}
                placeholder="30000"
                type="number"
                value={maxMileage}
              />
            </label>
          </div>

          <fieldset className="priority-fieldset">
            <legend>Priorita</legend>
            <div className="priority-list">
              {priorityOptions.map((priority) => (
                <label className="priority-option" key={priority.value}>
                  <input
                    checked={priorities.includes(priority.value)}
                    onChange={() => togglePriority(priority.value)}
                    type="checkbox"
                  />
                  {priority.label}
                </label>
              ))}
            </div>
          </fieldset>

          <button className="primary-button" disabled={!canSubmit} type="submit">
            {isLoading ? 'Calcolo…' : 'Trova veicoli'}
          </button>

          {error ? <p className="error-message">{error}</p> : null}
        </form>

        <section className="advisor-results" aria-live="polite">
          {isLoading ? <p className="status-message">Caricamento…</p> : null}

          {response ? (
            <>
              <div className="result-heading">
                <p className="eyebrow">Run {response.run_id}</p>
                <h2>Risultati</h2>
              </div>
              <div className="result-list">
                {response.items.map((item) => (
                  <article className="result-card" key={item.vehicle.id}>
                    <div className="result-topline">
                      <div>
                        <h3>
                          {item.vehicle.make} {item.vehicle.model}
                        </h3>
                        <p>
                          {item.vehicle.model_year} · {item.vehicle.body_style}{' '}
                          · {item.vehicle.fuel_type}
                        </p>
                      </div>
                      <strong>Score {item.score}</strong>
                    </div>

                    <p className="rationale">{item.rationale}</p>

                    {item.best_listing ? (
                      <dl className="listing-facts">
                        {item.best_listing.price_eur !== null ? (
                          <div>
                            <dt>Prezzo</dt>
                            <dd>
                              {formatCurrency(item.best_listing.price_eur)}
                            </dd>
                          </div>
                        ) : null}
                        {item.best_listing.mileage !== null ? (
                          <div>
                            <dt>Km</dt>
                            <dd>{formatNumber(item.best_listing.mileage)}</dd>
                          </div>
                        ) : null}
                        {item.best_listing.location_region ? (
                          <div>
                            <dt>Regione</dt>
                            <dd>{item.best_listing.location_region}</dd>
                          </div>
                        ) : null}
                      </dl>
                    ) : null}

                    <EvidenceList evidence={item.evidence} />
                    <DocumentEvidenceList evidence={item.document_evidence ?? []} />
                  </article>
                ))}
              </div>
            </>
          ) : (
            <p className="status-message">
              I risultati appariranno qui dopo la ricerca.
            </p>
          )}
        </section>
      </section>
    </main>
  )
}

function DocumentEvidenceList({
  evidence,
}: {
  evidence: AdvisorDocumentEvidence[]
}) {
  if (evidence.length === 0) {
    return null
  }

  return (
    <section className="document-evidence">
      <h4>Evidence documentale</h4>
      <div className="document-evidence-list">
        {evidence.map((item) => (
          <article className="document-evidence-card" key={item.document_id}>
            <div>
              <h5>{item.title}</h5>
              <p>
                {item.document_type} · score {item.score}
              </p>
            </div>
            <p>{item.snippet}</p>
            <Link
              className="text-link"
              params={{ documentId: item.document_id }}
              to="/documents/$documentId"
            >
              Apri documento evidence
            </Link>
          </article>
        ))}
      </div>
    </section>
  )
}

function EvidenceList({ evidence }: { evidence: Record<string, unknown> }) {
  const visibleEvidence: Array<{ label: string; value: string }> = [
    { label: 'Dentro budget', value: formatEvidenceValue(evidence.within_budget) },
    { label: 'Prezzo', value: formatMaybeCurrency(evidence.price_eur) },
    { label: 'Budget max', value: formatMaybeCurrency(evidence.budget_max_eur) },
    {
      label: 'Consumi l/100km',
      value: formatEvidenceValue(evidence.consumption_l_100km),
    },
    { label: 'Range WLTP km', value: formatEvidenceValue(evidence.wltp_range_km) },
    { label: 'CO2 g/km', value: formatEvidenceValue(evidence.co2_g_km) },
    { label: 'Posti', value: formatEvidenceValue(evidence.seats) },
    {
      label: 'Bagagliaio L',
      value: formatEvidenceValue(evidence.cargo_volume_liters),
    },
  ].filter((item) => item.value !== '')

  return (
    <dl className="evidence-list">
      {visibleEvidence.map(({ label, value }) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}

function optionalNumber(value: string) {
  return value.trim() === '' ? undefined : Number(value)
}

function optionalString(value: string) {
  return value.trim() === '' ? undefined : value.trim()
}

function formatCurrency(value: number) {
  return eurFormatter.format(value)
}

function formatMaybeCurrency(value: unknown) {
  return typeof value === 'number' ? formatCurrency(value) : formatEvidenceValue(value)
}

function formatEvidenceValue(value: unknown) {
  if (value === null || value === undefined || value === '') {
    return ''
  }
  if (typeof value === 'boolean') {
    return value ? 'Si' : 'No'
  }
  return String(value)
}

function formatNumber(value: number) {
  return integerFormatter.format(value)
}
