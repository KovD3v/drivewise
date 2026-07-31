import { Link } from '@tanstack/react-router'

import type { ListingWithVehicle } from '../api/drivewise'
import { formatCurrency, formatNumber } from './viewUtils'

export function ListingDetailPage({ listing }: { listing: ListingWithVehicle }) {
  return (
    <main className="browse-shell">
      <header className="browse-header">
        <Link className="text-link" to="/listings">
          Annunci
        </Link>
        <div>
          <p className="eyebrow">Listing detail</p>
          <h1>{listing.title}</h1>
          <p className="summary">
            {listing.vehicle.make} {listing.vehicle.model} ·{' '}
            {listing.location_region ?? 'Regione non disponibile'}
          </p>
        </div>
      </header>

      <section className="detail-panel">
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
