import { FormEvent, useState } from 'react'
import { Link } from '@tanstack/react-router'

import {
  type AdvisorBodyStyle,
  type AdvisorCondition,
  type AdvisorFactor,
  type AdvisorFuelType,
  type AdvisorMetricProvenance,
  type AdvisorPriority,
  type AdvisorPrimaryUse,
  type AdvisorRecommendationGroup,
  type AdvisorRecommendationItem,
  type AdvisorRecommendationResponse,
  type AdvisorScoreComponent,
  fetchAdvisorRecommendations,
} from '../api/drivewise'

const primaryUseOptions: Array<{ value: AdvisorPrimaryUse; label: string }> = [
  { value: 'city', label: 'Citta' },
  { value: 'highway', label: 'Autostrada' },
  { value: 'family', label: 'Famiglia' },
  { value: 'work', label: 'Lavoro' },
  { value: 'new_driver', label: 'Neopatentato' },
]

const conditionOptions: Array<{ value: AdvisorCondition; label: string }> = [
  { value: 'any', label: 'Nuovo e usato' },
  { value: 'new', label: 'Solo nuovo' },
  { value: 'used', label: 'Solo usato' },
]

const fuelOptions: Array<{ value: AdvisorFuelType; label: string }> = [
  { value: 'petrol', label: 'Benzina' },
  { value: 'diesel', label: 'Diesel' },
  { value: 'mild_hybrid_petrol', label: 'Mild hybrid benzina' },
  { value: 'hybrid_petrol', label: 'Ibrido benzina' },
  { value: 'full_hybrid_petrol', label: 'Full hybrid benzina' },
  { value: 'petrol_lpg', label: 'Benzina / GPL' },
  { value: 'electric', label: 'Elettrico' },
]

const bodyStyleOptions: Array<{ value: AdvisorBodyStyle; label: string }> = [
  { value: 'city_car', label: 'City car' },
  { value: 'small_hatchback', label: 'Compatta' },
  { value: 'hatchback', label: 'Hatchback' },
  { value: 'crossover', label: 'Crossover' },
  { value: 'sedan', label: 'Berlina' },
  { value: 'suv', label: 'SUV' },
  { value: 'wagon', label: 'Station wagon' },
  { value: 'mpv', label: 'Monovolume' },
  { value: 'van', label: 'Van' },
]

const priorityOptions: Array<{ value: AdvisorPriority; label: string }> = [
  { value: 'price', label: 'Prezzo' },
  { value: 'efficiency_range', label: 'Efficienza e autonomia' },
  { value: 'space', label: 'Spazio' },
  { value: 'running_cost', label: 'Costo energia' },
]

const componentOrder: AdvisorScoreComponent[] = [
  'price_fit',
  'use_case_fit',
  'running_cost',
  'space',
  'efficiency_range',
]

const componentLabels: Record<AdvisorScoreComponent, string> = {
  price_fit: 'Prezzo',
  use_case_fit: "Uso e preferenze",
  running_cost: 'Costo energia',
  space: 'Spazio',
  efficiency_range: 'Efficienza e autonomia',
}

const evidenceLabels: Record<string, string> = {
  annual_energy_cost_eur: 'Costo energia annuo',
  annual_km: 'Km annui',
  budget_max_eur: 'Budget massimo',
  budget_overrun_eur: 'Oltre budget',
  budget_overrun_percent: 'Oltre budget',
  cargo_volume_liters: 'Bagagliaio',
  consumption_l_100km: 'Consumo',
  energy_consumption_kwh_100km: 'Consumo elettrico',
  energy_cost_eur_100km: 'Costo energia / 100 km',
  mileage: 'Chilometraggio',
  seats: 'Posti',
  wltp_range_km: 'Autonomia WLTP',
}

const eurFormatter = new Intl.NumberFormat('it-IT', {
  currency: 'EUR',
  maximumFractionDigits: 0,
  style: 'currency',
})

const decimalEurFormatter = new Intl.NumberFormat('it-IT', {
  currency: 'EUR',
  maximumFractionDigits: 2,
  style: 'currency',
})

const integerFormatter = new Intl.NumberFormat('it-IT')
const scoreFormatter = new Intl.NumberFormat('it-IT', {
  maximumFractionDigits: 1,
})

const dateFormatter = new Intl.DateTimeFormat('it-IT', {
  dateStyle: 'medium',
  timeZone: 'UTC',
})

export function AdvisorPage() {
  const [budgetMin, setBudgetMin] = useState('')
  const [budgetMax, setBudgetMax] = useState('')
  const [primaryUse, setPrimaryUse] = useState<AdvisorPrimaryUse>('city')
  const [condition, setCondition] = useState<AdvisorCondition>('any')
  const [annualKm, setAnnualKm] = useState('')
  const [preferredFuelType, setPreferredFuelType] = useState<
    AdvisorFuelType | ''
  >('')
  const [preferredBodyStyle, setPreferredBodyStyle] = useState<
    AdvisorBodyStyle | ''
  >('')
  const [maxMileage, setMaxMileage] = useState('')
  const [priorities, setPriorities] = useState<AdvisorPriority[]>([])
  const [response, setResponse] = useState<AdvisorRecommendationResponse | null>(
    null,
  )
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = Number(budgetMax) > 0 && !isLoading

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
        condition,
        annual_km: optionalNumber(annualKm),
        preferred_fuel_type: preferredFuelType || undefined,
        preferred_body_style: preferredBodyStyle || undefined,
        max_mileage:
          condition === 'new' ? undefined : optionalNumber(maxMileage),
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
          <p className="eyebrow">Advisor deterministico</p>
          <h1>Trova l'auto adatta</h1>
          <p className="summary">
            Confronta offerte italiane nuove e usate. Ogni risultato mostra il
            motivo del punteggio, i compromessi e la provenienza dei dati.
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
              Condizione
              <select
                name="condition"
                onChange={(event) =>
                  setCondition(event.target.value as AdvisorCondition)
                }
                value={condition}
              >
                {conditionOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Km annui
              <input
                inputMode="numeric"
                min="1"
                name="annual_km"
                onChange={(event) => setAnnualKm(event.target.value)}
                placeholder="Default in base all'uso"
                type="number"
                value={annualKm}
              />
            </label>

            <label>
              Alimentazione preferita
              <select
                name="preferred_fuel_type"
                onChange={(event) =>
                  setPreferredFuelType(event.target.value as AdvisorFuelType | '')
                }
                value={preferredFuelType}
              >
                <option value="">Nessuna preferenza</option>
                {fuelOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Carrozzeria preferita
              <select
                name="preferred_body_style"
                onChange={(event) =>
                  setPreferredBodyStyle(event.target.value as AdvisorBodyStyle | '')
                }
                value={preferredBodyStyle}
              >
                <option value="">Nessuna preferenza</option>
                {bodyStyleOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Chilometraggio massimo usato
              <input
                disabled={condition === 'new'}
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

          {error ? (
            <p className="error-message" role="alert">
              {error}
            </p>
          ) : null}
        </form>

        <section className="advisor-results" aria-live="polite">
          {isLoading ? (
            <p className="status-message" role="status">
              Analisi delle offerte in corso…
            </p>
          ) : null}

          {response ? (
            <AdvisorResults response={response} />
          ) : !isLoading ? (
            <p className="status-message">
              I risultati appariranno qui dopo la ricerca.
            </p>
          ) : null}
        </section>
      </section>
    </main>
  )
}

function AdvisorResults({ response }: { response: AdvisorRecommendationResponse }) {
  return (
    <>
      <div className="result-heading">
        <p className="eyebrow">Run {response.run_id}</p>
        <h2>Risultati</h2>
        <p className="result-meta">Scoring {response.scoring_version}</p>
      </div>

      <RunContext response={response} />

      <div className="advisor-groups">
        {response.groups.map((group) => (
          <RecommendationGroup group={group} key={group.condition} />
        ))}
      </div>
    </>
  )
}

function RunContext({ response }: { response: AdvisorRecommendationResponse }) {
  const exclusions = Object.entries(response.excluded_counts_by_reason).filter(
    ([, count]) => count > 0,
  )

  const insufficientData = Object.entries(response.insufficient_data_counts_by_reason).filter(
    ([, count]) => count > 0,
  )

  if (response.assumptions.length === 0 && exclusions.length === 0 && insufficientData.length === 0) {
    return null
  }

  return (
    <aside className="run-context" aria-label="Contesto del calcolo">
      {response.assumptions.length > 0 ? (
        <section>
          <h3>Assunzioni</h3>
          <ul className="token-list">
            {response.assumptions.map((assumption) => (
              <li key={assumption}>{assumption}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {exclusions.length > 0 ? (
        <section>
          <h3>Offerte escluse</h3>
          <dl className="compact-facts">
            {exclusions.map(([reason, count]) => (
              <div key={reason}>
                <dt>{humanizeKey(reason)}</dt>
                <dd>{formatNumber(count)}</dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}

      {insufficientData.length > 0 ? (
        <section>
          <h3>Dati mancanti nei risultati</h3>
          <dl className="compact-facts">
            {insufficientData.map(([reason, count]) => (
              <div key={reason}>
                <dt>{humanizeKey(reason)}</dt>
                <dd>{formatNumber(count)}</dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}
    </aside>
  )
}

function RecommendationGroup({ group }: { group: AdvisorRecommendationGroup }) {
  const heading = group.condition === 'new' ? 'Nuovo' : 'Usato'

  return (
    <section className="recommendation-group" aria-labelledby={`${group.condition}-title`}>
      <div className="group-heading">
        <h3 id={`${group.condition}-title`}>{heading}</h3>
        <span>{group.items.length} risultati</span>
      </div>

      {group.items.length === 0 ? (
        <p className="empty-guidance">
          {group.condition === 'new'
            ? 'Nessuna offerta nuova soddisfa i vincoli e i requisiti di qualita. Prova ad aumentare il budget o a rimuovere una preferenza.'
            : 'Nessuna offerta usata soddisfa i vincoli e i requisiti di qualita. Prova ad aumentare il chilometraggio massimo o il budget.'}
        </p>
      ) : (
        <div className="result-list">
          {group.items.slice(0, 5).map((item) => (
            <RecommendationCard item={item} key={item.offer.id} />
          ))}
        </div>
      )}
    </section>
  )
}

function RecommendationCard({ item }: { item: AdvisorRecommendationItem }) {
  const provisional = item.decision_status === 'insufficient_data'
  const displayScore = item.decision_score ?? item.score

  return (
    <article className="result-card">
      <div className="result-topline">
        <div>
          <p className="result-rank-label">{item.selected_spec.trim}</p>
          <h4>
            {item.vehicle.make} {item.vehicle.model}
          </h4>
          <p>
            {item.vehicle.model_year} · {humanizeKey(item.selected_spec.body_style)} ·{' '}
            {humanizeKey(item.selected_spec.fuel_type)}
          </p>
        </div>
        <strong className="score-badge">
          <span>{provisional ? 'Structural Fit provvisorio' : 'Decision Score'}</span>{' '}
          {formatScore(displayScore)} <span>su 100</span>
        </strong>
      </div>

      {provisional ? (
        <p className="status-message" role="status">
          Risultato provvisorio: il punteggio usa lo Structural Fit finché non sono
          disponibili {item.missing_factors.length > 0 ? item.missing_factors.map(humanizeKey).join(', ') : 'tutti i dati mancanti'}.
        </p>
      ) : null}

      <OfferFacts item={item} />
      <ComponentScores scores={item.component_scores} />
      <FactorSection
        className="positive-factors"
        factors={item.positive_factors}
        title="Punti forti"
      />
      <FactorSection
        className="tradeoffs"
        factors={item.tradeoffs}
        title="Compromessi"
      />
      <EvidenceFacts evidence={item.evidence} />
      <ProvenanceList provenance={item.provenance} />
    </article>
  )
}

function OfferFacts({ item }: { item: AdvisorRecommendationItem }) {
  const { offer } = item
  const freshness = offer.last_seen_at ?? offer.listed_at

  return (
    <section className="offer-summary" aria-label="Offerta selezionata">
      <dl className="listing-facts">
        <Fact label="Prezzo" value={formatCurrency(offer.price_eur)} />
        <Fact
          label="Condizione"
          value={offer.condition === 'new' ? 'Nuovo' : offer.condition === 'certified' ? 'Usato certificato' : 'Usato'}
        />
        {offer.mileage !== null ? (
          <Fact label="Km" value={formatNumber(offer.mileage)} />
        ) : null}
        {offer.location_region ? (
          <Fact label="Regione" value={offer.location_region} />
        ) : null}
        <Fact label="Aggiornata" value={formatDate(freshness)} />
      </dl>
      {offer.source_url ? (
        <a
          className="text-link source-link"
          href={offer.source_url}
          rel="noreferrer"
          target="_blank"
        >
          Apri la fonte dell'offerta
        </a>
      ) : (
        <p className="source-unavailable">URL fonte non disponibile</p>
      )}
    </section>
  )
}

function ComponentScores({
  scores,
}: {
  scores: Record<AdvisorScoreComponent, number | null>
}) {
  return (
    <section className="component-scores" aria-label="Punteggi per componente">
      <h5>Punteggi</h5>
      <div className="score-list">
        {componentOrder.map((component) => {
          const score = scores[component]
          const boundedScore = score === null ? undefined : Math.min(100, Math.max(0, score))
          return (
            <div className="score-row" key={component}>
              <div>
                <span>{componentLabels[component]}</span>
                <strong>{score === null ? 'n/d' : formatScore(score)}</strong>
              </div>
              <progress
                aria-label={`${componentLabels[component]}: ${score === null ? 'dati mancanti' : `${formatScore(score)} su 100`}`}
                max="100"
                value={boundedScore}
              />
            </div>
          )
        })}
      </div>
    </section>
  )
}

function FactorSection({
  className,
  factors,
  title,
}: {
  className: string
  factors: AdvisorFactor[]
  title: string
}) {
  if (factors.length === 0) {
    return null
  }

  return (
    <section className={`factor-section ${className}`}>
      <h5>{title}</h5>
      <ul>
        {factors.map((factor) => (
          <li key={`${factor.component}-${factor.metric ?? factor.message}`}>
            <span>{factor.message}</span>
            <FactorDetails factor={factor} />
          </li>
        ))}
      </ul>
    </section>
  )
}

function FactorDetails({ factor }: { factor: AdvisorFactor }) {
  const details = [
    factor.metric ? `${humanizeKey(factor.metric)}: ${factor.value ?? 'n/d'}` : null,
    factor.threshold !== undefined ? `soglia ${factor.threshold}` : null,
    `contributo ${formatSigned(factor.contribution)}`,
  ].filter((detail): detail is string => detail !== null)

  return <small>{details.join(' · ')}</small>
}

function EvidenceFacts({ evidence }: { evidence: Record<string, unknown> }) {
  const facts = Object.entries(evidence)
    .filter((entry): entry is [string, string | number | boolean] =>
      ['boolean', 'number', 'string'].includes(typeof entry[1]),
    )
    .map(([key, value]) => ({
      key,
      label: evidenceLabels[key] ?? humanizeKey(key),
      value: formatEvidence(key, value),
    }))

  if (facts.length === 0) {
    return null
  }

  return (
    <section className="evidence-facts">
      <h5>Dati del calcolo</h5>
      <dl className="evidence-list">
        {facts.map((fact) => (
          <div key={fact.key}>
            <dt>{fact.label}</dt>
            <dd>{fact.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

function ProvenanceList({
  provenance,
}: {
  provenance: AdvisorMetricProvenance[]
}) {
  if (provenance.length === 0) {
    return null
  }

  return (
    <section className="provenance-section">
      <h5>Fonti dei dati</h5>
      <ul className="provenance-list">
        {provenance.map((source, index) => (
          <li key={`${source.metric}-${source.source_name}-${index}`}>
            <span>
              <strong>{humanizeKey(source.metric)}</strong> ·{' '}
              {source.source_url ? (
                <a href={source.source_url} rel="noreferrer" target="_blank">
                  {source.source_name}
                </a>
              ) : (
                source.source_name
              )}
            </span>
            <small>Osservato: {formatDate(source.observed_at)}</small>
          </li>
        ))}
      </ul>
    </section>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}

function optionalNumber(value: string) {
  return value.trim() === '' ? undefined : Number(value)
}

function formatCurrency(value: number) {
  return eurFormatter.format(value)
}

function formatNumber(value: number) {
  return integerFormatter.format(value)
}

function formatScore(value: number) {
  return scoreFormatter.format(value)
}

function formatSigned(value: number) {
  return `${value >= 0 ? '+' : ''}${formatScore(value)}`
}

function formatEvidence(key: string, value: string | number | boolean) {
  if (typeof value === 'boolean') {
    return value ? 'Si' : 'No'
  }
  if (typeof value !== 'number') {
    return value
  }
  if (key === 'energy_cost_eur_100km') {
    return decimalEurFormatter.format(value)
  }
  if (key.endsWith('_eur')) {
    return formatCurrency(value)
  }
  if (key.endsWith('_percent')) {
    return `${formatScore(value)}%`
  }
  if (key === 'consumption_l_100km') {
    return `${formatScore(value)} l/100 km`
  }
  if (key === 'energy_consumption_kwh_100km') {
    return `${formatScore(value)} kWh/100 km`
  }
  if (key.endsWith('_km') || key === 'mileage' || key === 'annual_km') {
    return `${formatNumber(value)} km`
  }
  if (key === 'cargo_volume_liters') {
    return `${formatNumber(value)} l`
  }
  return formatNumber(value)
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return 'Data non disponibile'
  }
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : dateFormatter.format(date)
}

function humanizeKey(value: string) {
  return value.replaceAll('_', ' ')
}
