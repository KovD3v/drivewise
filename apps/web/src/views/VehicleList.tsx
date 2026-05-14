import { FormEvent, useEffect, useState } from 'react'
import { Link } from '@tanstack/react-router'

import { fetchVehicles, VehicleFilters, VehicleSummary } from '../api/drivewise'
import { errorMessage, formatCurrency, optionalNumber } from './viewUtils'

export function VehicleListPage() {
  const [make, setMake] = useState('')
  const [fuelType, setFuelType] = useState('')
  const [bodyStyle, setBodyStyle] = useState('')
  const [market, setMarket] = useState('')
  const [maxPrice, setMaxPrice] = useState('')
  const [filters, setFilters] = useState<VehicleFilters>({})
  const [vehicles, setVehicles] = useState<VehicleSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isCurrent = true
    setIsLoading(true)
    setError(null)

    fetchVehicles(filters)
      .then((data) => {
        if (isCurrent) {
          setVehicles(data)
        }
      })
      .catch((caughtError) => {
        if (isCurrent) {
          setError(errorMessage(caughtError, 'Unable to load vehicles'))
          setVehicles([])
        }
      })
      .finally(() => {
        if (isCurrent) {
          setIsLoading(false)
        }
      })

    return () => {
      isCurrent = false
    }
  }, [filters])

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFilters({
      make: optionalString(make),
      fuel_type: optionalString(fuelType),
      body_style: optionalString(bodyStyle),
      market: optionalString(market),
      max_price_eur: optionalNumber(maxPrice),
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
        <form className="filter-panel" onSubmit={handleSubmit}>
          <div className="form-grid">
            <label>
              Make
              <input
                name="make"
                onChange={(event) => setMake(event.target.value)}
                placeholder="Fiat"
                value={make}
              />
            </label>
            <label>
              Fuel type
              <input
                name="fuel_type"
                onChange={(event) => setFuelType(event.target.value)}
                placeholder="mild_hybrid_petrol"
                value={fuelType}
              />
            </label>
            <label>
              Body style
              <input
                name="body_style"
                onChange={(event) => setBodyStyle(event.target.value)}
                placeholder="city_car"
                value={bodyStyle}
              />
            </label>
            <label>
              Market
              <input
                name="market"
                onChange={(event) => setMarket(event.target.value)}
                placeholder="IT"
                value={market}
              />
            </label>
            <label>
              Prezzo massimo
              <input
                inputMode="decimal"
                min="0"
                name="max_price_eur"
                onChange={(event) => setMaxPrice(event.target.value)}
                placeholder="25000"
                type="number"
                value={maxPrice}
              />
            </label>
          </div>
          <button className="primary-button" type="submit">
            Applica filtri
          </button>
        </form>

        <section className="browse-results" aria-live="polite">
          {isLoading ? <p className="status-message">Caricamento…</p> : null}
          {error ? <p className="error-message">{error}</p> : null}
          {!isLoading && !error && vehicles.length === 0 ? (
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

function optionalString(value: string) {
  return value.trim() === '' ? undefined : value.trim()
}
