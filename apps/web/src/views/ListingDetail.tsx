import { useEffect, useState } from 'react'
import { Link } from '@tanstack/react-router'

import { fetchListing, ListingWithVehicle } from '../api/drivewise'
import { errorMessage, formatCurrency, formatNumber } from './viewUtils'

export function ListingDetailPage({ listingId }: { listingId: string }) {
  const [listing, setListing] = useState<ListingWithVehicle | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isCurrent = true
    setIsLoading(true)
    setError(null)

    fetchListing(listingId)
      .then((data) => {
        if (isCurrent) {
          setListing(data)
        }
      })
      .catch((caughtError) => {
        if (isCurrent) {
          setError(errorMessage(caughtError, 'Unable to load listing'))
          setListing(null)
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
  }, [listingId])

  return (
    <main className="browse-shell">
      <header className="browse-header">
        <Link className="text-link" to="/listings">
          Annunci
        </Link>
        <div>
          <p className="eyebrow">Listing detail</p>
          <h1>{listing ? listing.title : 'Dettaglio annuncio'}</h1>
          {listing ? (
            <p className="summary">
              {listing.vehicle.make} {listing.vehicle.model} ·{' '}
              {listing.location_region ?? 'Regione non disponibile'}
            </p>
          ) : null}
        </div>
      </header>

      <section className="detail-panel" aria-live="polite">
        {isLoading ? <p className="status-message">Caricamento…</p> : null}
        {error ? <p className="error-message">{error}</p> : null}

        {listing ? (
          <>
            <dl className="facts-grid detail-facts">
              <Fact label="Prezzo" value={formatCurrency(listing.price_eur)} />
              <Fact label="Km" value={formatNumber(listing.mileage)} />
              <Fact label="Condition" value={listing.condition} />
              <Fact label="Regione" value={listing.location_region ?? '-'} />
              <Fact label="Listing ref" value={listing.listing_ref} />
              <Fact label="Listed at" value={listing.listed_at ?? '-'} />
            </dl>

            <section className="detail-section">
              <h2>Veicolo collegato</h2>
              <article className="data-card">
                <div className="card-heading">
                  <h3>
                    {listing.vehicle.make} {listing.vehicle.model}
                  </h3>
                  <p>
                    {listing.vehicle.model_year} · {listing.vehicle.body_style}
                  </p>
                </div>
                <dl className="facts-grid">
                  <Fact label="Fuel" value={listing.vehicle.fuel_type} />
                  <Fact label="Market" value={listing.vehicle.market} />
                  <Fact
                    label="Prezzo base"
                    value={formatCurrency(listing.vehicle.base_price_eur)}
                  />
                </dl>
                <Link
                  className="text-link"
                  params={{ vehicleId: listing.vehicle.id }}
                  to="/vehicles/$vehicleId"
                >
                  Dettaglio veicolo
                </Link>
              </article>
            </section>
          </>
        ) : null}
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
