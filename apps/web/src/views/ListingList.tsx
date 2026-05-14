import { FormEvent, useEffect, useState } from 'react'
import { Link } from '@tanstack/react-router'

import { fetchListings, ListingFilters, ListingWithVehicle } from '../api/drivewise'
import { errorMessage, formatCurrency, formatNumber, optionalNumber } from './viewUtils'

export function ListingListPage() {
  const [make, setMake] = useState('')
  const [model, setModel] = useState('')
  const [maxPrice, setMaxPrice] = useState('')
  const [maxMileage, setMaxMileage] = useState('')
  const [locationRegion, setLocationRegion] = useState('')
  const [filters, setFilters] = useState<ListingFilters>({})
  const [listings, setListings] = useState<ListingWithVehicle[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isCurrent = true
    setIsLoading(true)
    setError(null)

    fetchListings(filters)
      .then((data) => {
        if (isCurrent) {
          setListings(data)
        }
      })
      .catch((caughtError) => {
        if (isCurrent) {
          setError(errorMessage(caughtError, 'Unable to load listings'))
          setListings([])
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
      model: optionalString(model),
      max_price_eur: optionalNumber(maxPrice),
      max_mileage: optionalNumber(maxMileage),
      location_region: optionalString(locationRegion),
    })
  }

  return (
    <main className="browse-shell">
      <header className="browse-header">
        <Link className="text-link" to="/">
          Drivewise MVP
        </Link>
        <div>
          <p className="eyebrow">Listing explorer</p>
          <h1>Annunci</h1>
          <p className="summary">
            Esplora i listing sintetici del seed MVP con filtri per prezzo,
            chilometraggio e regione.
          </p>
        </div>
      </header>

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
              Model
              <input
                name="model"
                onChange={(event) => setModel(event.target.value)}
                placeholder="Panda"
                value={model}
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
            <label>
              Regione
              <input
                name="location_region"
                onChange={(event) => setLocationRegion(event.target.value)}
                placeholder="Piemonte"
                value={locationRegion}
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
          {!isLoading && !error && listings.length === 0 ? (
            <p className="status-message">Nessun annuncio trovato.</p>
          ) : null}

          <div className="card-grid">
            {listings.map((listing) => (
              <article className="data-card" key={listing.id}>
                <div className="card-heading">
                  <h2>{listing.title}</h2>
                  <p>
                    {listing.vehicle.make} {listing.vehicle.model}
                  </p>
                </div>
                <dl className="facts-grid">
                  <Fact label="Prezzo" value={formatCurrency(listing.price_eur)} />
                  <Fact label="Km" value={formatNumber(listing.mileage)} />
                  <Fact label="Condition" value={listing.condition} />
                  <Fact label="Regione" value={listing.location_region ?? '-'} />
                </dl>
                <Link
                  className="text-link"
                  params={{ listingId: listing.id }}
                  to="/listings/$listingId"
                >
                  Dettaglio annuncio
                </Link>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
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
