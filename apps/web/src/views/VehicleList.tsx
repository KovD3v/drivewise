import { FormEvent } from 'react'
import { Link } from '@tanstack/react-router'

import { VehicleFilters, VehicleSummary } from '../api/drivewise'
import { formatCurrency, optionalNumber } from './viewUtils'

export function VehicleListPage({
  filters,
  onFiltersChange,
  vehicles,
}: {
  filters: VehicleFilters
  onFiltersChange: (filters: VehicleFilters) => void
  vehicles: VehicleSummary[]
}) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    onFiltersChange({
      make: optionalString(form.get('make')),
      fuel_type: optionalString(form.get('fuel_type')),
      body_style: optionalString(form.get('body_style')),
      market: optionalString(form.get('market'))?.toUpperCase(),
      max_price_eur: optionalNumber(String(form.get('max_price_eur') ?? '')),
    })
  }

  return (
    <main className="browse-shell">
      <BrowseHeader
        eyebrow="Vehicle explorer"
        title="Veicoli"
        summary="Esplora il catalogo veicoli del seed MVP con filtri semplici e dati Italia/EU."
      />

      <section className="browse-layout">
        <form className="filter-panel" key={JSON.stringify(filters)} onSubmit={handleSubmit}>
          <div className="form-grid">
            <label>
              Make
              <input
                name="make"
                defaultValue={filters.make}
                placeholder="Fiat"
              />
            </label>
            <label>
              Fuel type
              <input
                name="fuel_type"
                defaultValue={filters.fuel_type}
                placeholder="mild_hybrid_petrol"
              />
            </label>
            <label>
              Body style
              <input
                name="body_style"
                defaultValue={filters.body_style}
                placeholder="city_car"
              />
            </label>
            <label>
              Market
              <input
                name="market"
                defaultValue={filters.market}
                placeholder="IT"
              />
            </label>
            <label>
              Prezzo massimo
              <input
                inputMode="decimal"
                min="0"
                name="max_price_eur"
                defaultValue={filters.max_price_eur}
                placeholder="25000"
                type="number"
              />
            </label>
          </div>
          <button className="primary-button" type="submit">
            Applica filtri
          </button>
        </form>

        <section className="browse-results" aria-live="polite">
          {vehicles.length === 0 ? (
            <p className="status-message">Nessun veicolo trovato.</p>
          ) : null}

          <div className="card-grid">
            {vehicles.map((vehicle) => (
              <article className="data-card" key={vehicle.id}>
                <div className="card-heading">
                  <h2>
                    {vehicle.make} {vehicle.model}
                  </h2>
                  <p>
                    {vehicle.model_year} · {vehicle.body_style}
                  </p>
                </div>
                <dl className="facts-grid">
                  <Fact label="Fuel" value={vehicle.fuel_type} />
                  <Fact label="Market" value={vehicle.market} />
                  <Fact
                    label="Prezzo base"
                    value={formatCurrency(vehicle.base_price_eur)}
                  />
                </dl>
                <Link
                  className="text-link"
                  params={{ vehicleId: vehicle.id }}
                  to="/vehicles/$vehicleId"
                >
                  Dettaglio veicolo
                </Link>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  )
}

function BrowseHeader({
  eyebrow,
  title,
  summary,
}: {
  eyebrow: string
  title: string
  summary: string
}) {
  return (
    <header className="browse-header">
      <Link className="text-link" to="/">
        Drivewise MVP
      </Link>
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="summary">{summary}</p>
      </div>
    </header>
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

function optionalString(value: FormDataEntryValue | null) {
  if (typeof value !== 'string') {
    return undefined
  }
  return value.trim() || undefined
}
