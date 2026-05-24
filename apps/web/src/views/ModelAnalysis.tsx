import { FormEvent, useMemo, useState } from 'react'
import { Link } from '@tanstack/react-router'

import { analyzeModel } from '../api/drivewise'
import type {
  ModelAnalysisResponse,
  ModelAnalysisScope,
  ModelAnalysisUsageProfile,
} from '../api/drivewise'

const usageOptions: Array<{ value: ModelAnalysisUsageProfile; label: string }> = [
  { value: 'city', label: 'City' },
  { value: 'mixed', label: 'Mixed' },
  { value: 'highway', label: 'Highway' },
  { value: 'family', label: 'Family' },
  { value: 'work', label: 'Work' },
]

const defaultScope: ModelAnalysisScope[] = [
  'price',
  'maintenance',
  'red_flags',
  'tco',
]

const eurFormatter = new Intl.NumberFormat('it-IT', {
  currency: 'EUR',
  maximumFractionDigits: 0,
  style: 'currency',
})

export function ModelAnalysisPage() {
  const [query, setQuery] = useState('')
  const [market, setMarket] = useState('IT')
  const [askingPrice, setAskingPrice] = useState('')
  const [currentKm, setCurrentKm] = useState('')
  const [usageProfile, setUsageProfile] = useState<ModelAnalysisUsageProfile[]>([])
  const [response, setResponse] = useState<ModelAnalysisResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = useMemo(
    () => query.trim().length >= 2 && !isLoading,
    [query, isLoading],
  )

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsLoading(true)
    setError(null)
    setResponse(null)

    try {
      const data = await analyzeModel({
        query,
        market,
        asking_price_eur: optionalNumber(askingPrice),
        current_km: optionalNumber(currentKm),
        usage_profile: usageProfile,
        analysis_scope: defaultScope,
      })
      setResponse(data)
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Model analysis request failed',
      )
    } finally {
      setIsLoading(false)
    }
  }

  function toggleUsage(usage: ModelAnalysisUsageProfile) {
    setUsageProfile((current) =>
      current.includes(usage)
        ? current.filter((item) => item !== usage)
        : [...current, usage],
    )
  }

  return (
    <main className="advisor-shell">
      <header className="advisor-header">
        <Link className="text-link" to="/">
          Drivewise MVP
        </Link>
        <div>
          <p className="eyebrow">Model analysis</p>
          <h1>Analisi modello</h1>
          <p className="summary">
            Valuta un modello scelto con resolver canonico, prezzo, km, costi
            stimati e controlli principali.
          </p>
        </div>
      </header>

      <section className="advisor-layout">
        <form className="advisor-form" onSubmit={handleSubmit}>
          <div className="form-grid">
            <label>
              Modello
              <input
                name="query"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="fiat panda 1.0 firefly hybrid 2024"
                required
                value={query}
              />
            </label>

            <label>
              Mercato
              <input
                maxLength={3}
                name="market"
                onChange={(event) => setMarket(event.target.value.toUpperCase())}
                placeholder="IT"
                value={market}
              />
            </label>

            <label>
              Prezzo richiesto
              <input
                inputMode="decimal"
                min="0"
                name="asking_price_eur"
                onChange={(event) => setAskingPrice(event.target.value)}
                placeholder="14500"
                type="number"
                value={askingPrice}
              />
            </label>

            <label>
              Km attuali
              <input
                inputMode="numeric"
                min="0"
                name="current_km"
                onChange={(event) => setCurrentKm(event.target.value)}
                placeholder="6400"
                type="number"
                value={currentKm}
              />
            </label>
          </div>

          <fieldset className="priority-fieldset">
            <legend>Utilizzo</legend>
            <div className="priority-list">
              {usageOptions.map((usage) => (
                <label className="priority-option" key={usage.value}>
                  <input
                    checked={usageProfile.includes(usage.value)}
                    onChange={() => toggleUsage(usage.value)}
                    type="checkbox"
                  />
                  {usage.label}
                </label>
              ))}
            </div>
          </fieldset>

          <button className="primary-button" disabled={!canSubmit} type="submit">
            {isLoading ? 'Analisi…' : 'Analizza modello'}
          </button>

          {error ? <p className="error-message">{error}</p> : null}
        </form>

        <section className="advisor-results" aria-live="polite">
          {isLoading ? <p className="status-message">Analisi in corso…</p> : null}

          {response ? (
            <ModelAnalysisResult response={response} />
          ) : (
            <p className="status-message">
              Il risultato apparira qui dopo l'analisi.
            </p>
          )}
        </section>
      </section>
    </main>
  )
}

function ModelAnalysisResult({ response }: { response: ModelAnalysisResponse }) {
  const vehicle = response.resolved_vehicle

  return (
    <>
      <div className="result-heading">
        <p className="eyebrow">Status {response.status}</p>
        <h2>{vehicle ? `${vehicle.make} ${vehicle.model}` : 'Modello non risolto'}</h2>
      </div>

      <div className="result-card analysis-result-card">
        <div className="result-topline">
          <div>
            <h3>{response.verdict}</h3>
            <p>
              <span>{response.price_assessment}</span>
              {response.resolved_spec ? ` · ${response.resolved_spec.trim}` : ''}
            </p>
          </div>
          <strong>{`Confidence ${response.confidence}`}</strong>
        </div>

        <dl className="evidence-list">
          <Fact
            label="Prezzo riferimento"
            value={formatMaybeCurrency(
              response.estimated_costs.market_reference_price_eur,
            )}
          />
          <Fact
            label="Manutenzione annua"
            value={formatMaybeCurrency(
              response.estimated_costs.estimated_annual_maintenance_eur,
            )}
          />
          <Fact
            label="Energia mensile"
            value={formatMaybeCurrency(
              response.estimated_costs.estimated_monthly_energy_eur,
            )}
          />
          <Fact
            label="Deprezzamento 3 anni"
            value={formatMaybeCurrency(
              response.estimated_costs.estimated_depreciation_3y_eur,
            )}
          />
        </dl>

        <div className="analysis-sections">
          <TokenSection title="Red flags" items={response.red_flags} empty="Nessuna" />
          <TokenSection title="Checklist" items={response.checklist} />
          <TokenSection title="Warning" items={response.warnings} empty="Nessuno" />
          <TokenSection
            title="Dati mancanti"
            items={response.missing_data}
            empty="Nessuno"
          />
          <TokenSection title="Assunzioni" items={response.assumptions} />
        </div>

        <div className="next-actions">
          {response.next_actions.map((action) => (
            <button className="secondary-link" key={action} type="button">
              {action}
            </button>
          ))}
        </div>
      </div>
    </>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  if (!value) {
    return null
  }
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}

function TokenSection({
  title,
  items,
  empty,
}: {
  title: string
  items: string[]
  empty?: string
}) {
  return (
    <section className="analysis-section">
      <h4>{title}</h4>
      {items.length > 0 ? (
        <ul className="token-list">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p>{empty ?? 'Non disponibile'}</p>
      )}
    </section>
  )
}

function optionalNumber(value: string) {
  return value.trim() === '' ? undefined : Number(value)
}

function formatMaybeCurrency(value: number | null) {
  return typeof value === 'number' ? eurFormatter.format(value) : ''
}
