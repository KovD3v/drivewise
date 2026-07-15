import { FormEvent } from 'react'
import { Link } from '@tanstack/react-router'

import { ListingFilters, ListingWithVehicle } from '../api/drivewise'
import { formatCurrency, formatNumber, optionalNumber } from './viewUtils'

export function ListingListPage({
  filters,
  listings,
  onFiltersChange,
}: {
  filters: ListingFilters
  listings: ListingWithVehicle[]
  onFiltersChange: (filters: ListingFilters) => void
}) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    onFiltersChange({
      make: optionalString(form.get('make')),
      model: optionalString(form.get('model')),
      max_price_eur: optionalNumber(String(form.get('max_price_eur') ?? '')),
      max_mileage: optionalNumber(String(form.get('max_mileage') ?? '')),
      location_region: optionalString(form.get('location_region')),
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
              Model
              <input
                name="model"
                defaultValue={filters.model}
                placeholder="Panda"
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
            <label>
              Chilometraggio massimo
              <input
                inputMode="numeric"
                min="0"
                name="max_mileage"
                defaultValue={filters.max_mileage}
                placeholder="30000"
                type="number"
              />
            </label>
            <label>
              Regione
              <input
                name="location_region"
                defaultValue={filters.location_region}
                placeholder="Piemonte"
              />
            </label>
          </div>
          <button className="primary-button" type="submit">
            Applica filtri
          </button>
        </form>

        <section className="browse-results" aria-live="polite">
          {listings.length === 0 ? (
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

function optionalString(value: FormDataEntryValue | null) {
  if (typeof value !== 'string') {
    return undefined
  }
  return value.trim() || undefined
}
