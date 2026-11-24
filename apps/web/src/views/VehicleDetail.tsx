import { Link } from '@tanstack/react-router'

import type { SourceProvenance, VehicleDetail } from '../api/drivewise'
import {
  formatListDate,
  ListPriceFacts,
  ListPriceNotes,
  SourceCredits,
  withBasis,
} from './sourceFacts'
import { formatCurrency, formatNumber } from './viewUtils'

type VehicleSpecDetail = VehicleDetail['specs'][number]

function consumption(spec: VehicleSpecDetail) {
  if (spec.consumption_l_100km !== null) {
    return withBasis(`${spec.consumption_l_100km} l/100km`, spec.consumption_l_100km_basis)
  }
  if (spec.energy_consumption_kwh_100km !== null) {
    return withBasis(
      `${spec.energy_consumption_kwh_100km} kWh/100km`,
      spec.energy_consumption_kwh_100km_basis,
    )
  }
  return 'Non disponibile'
}

export function VehicleDetailPage({ vehicle }: { vehicle: VehicleDetail }) {
  return (
    <main className="browse-shell">
      <header className="browse-header">
        <Link className="text-link" to="/vehicles">
          Veicoli
        </Link>
        <div>
          <p className="eyebrow">Vehicle detail</p>
          <h1>
            {vehicle.make} {vehicle.model}
          </h1>
          <p className="summary">
            {vehicle.model_year ?? 'Anno non disponibile'} · {vehicle.body_style} · {vehicle.fuel_type}
          </p>
        </div>
      </header>

      <section className="detail-panel">
        <dl className="facts-grid detail-facts">
          <Fact label="Market" value={vehicle.market} />
          <Fact label="Body style" value={vehicle.body_style} />
          <Fact label="Fuel type" value={vehicle.fuel_type} />
          <Fact
            label="Prezzo base"
            value={formatCurrency(vehicle.base_price_eur)}
          />
        </dl>

        <section className="detail-section">
          <h2>Specs</h2>
          {vehicle.specs.length === 0 ? (
            <p className="status-message">Nessuna specifica collegata.</p>
          ) : (
            <div className="card-grid">
              {vehicle.specs.map((spec) => (
                <article className="data-card" key={spec.id}>
                  <div className="card-heading">
                    <h3>{spec.trim ?? 'Allestimento non disponibile'}</h3>
                    <p>{spec.engine ?? 'Motore non disponibile'}</p>
                  </div>
                  <dl className="facts-grid">
                    <Fact label="Drivetrain" value={spec.drivetrain ?? '-'} />
                    <Fact
                      label="Transmission"
                      value={spec.transmission ?? '-'}
                    />
                    <Fact
                      label="Potenza"
                      value={
                        spec.horsepower === null
                          ? 'Non disponibile'
                          : `${spec.horsepower} CV`
                      }
                    />
                    <Fact label="Consumi" value={consumption(spec)} />
                    <Fact
                      label="Range WLTP"
                      value={
                        spec.wltp_range_km === null
                          ? 'Non disponibile'
                          : `${formatNumber(spec.wltp_range_km)} km`
                      }
                    />
                    <Fact
                      label="CO2"
                      value={
                        spec.co2_g_km === null
                          ? 'Non disponibile'
                          : `${spec.co2_g_km} g/km`
                      }
                    />
                    <Fact
                      label="Emissioni"
                      value={spec.euro_emission_standard ?? '-'}
                    />
                    <Fact
                      label="Posti"
                      value={
                        spec.seats === null
                          ? 'Non disponibile'
                          : String(spec.seats)
                      }
                    />
                    <Fact
                      label="Bagagliaio"
                      value={
                        spec.cargo_volume_liters === null
                          ? 'Non disponibile'
                          : `${formatNumber(spec.cargo_volume_liters)} L`
                      }
                    />
                  </dl>
                  {spec.list_price ? (
                    <section className="offer-summary spec-list-price" aria-label="Prezzo di listino">
                      <dl className="facts-grid">
                        <ListPriceFacts price={spec.list_price} />
                      </dl>
                      <ListPriceNotes price={spec.list_price} />
                    </section>
                  ) : null}
                  <SourceList provenance={spec.provenance} />
                </article>
              ))}
            </div>
          )}
        </section>
        <SourceList provenance={vehicle.provenance} title="Fonti del modello" />
      </section>
    </main>
  )
}

function Fact({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value ?? 'Non disponibile'}</dd>
    </div>
  )
}

function SourceList({
  provenance,
  title = 'Fonti dei dati',
}: {
  provenance: SourceProvenance[]
  title?: string
}) {
  const current = provenance.filter((source) => source.is_current)
  if (current.length === 0) {
    return null
  }
  return (
    <section className="provenance-section">
      <h5>{title}</h5>
      <ul className="provenance-list">
        {current.map((source) => (
          <li key={`${source.source_id}-${source.content_hash}`}>
            <span>
              <a href={source.source_url} rel="noreferrer" target="_blank">
                {source.source_name}
              </a>
            </span>
            <small>Consultata il {formatListDate(source.observed_at)}</small>
          </li>
        ))}
      </ul>
      <SourceCredits
        credits={current.map((source) => ({
          name: source.source_name,
          license: source.source_license,
        }))}
      />
    </section>
  )
}
