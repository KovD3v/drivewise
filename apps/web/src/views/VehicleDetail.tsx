import { Link } from '@tanstack/react-router'

import type { VehicleDetail } from '../api/drivewise'
import { formatCurrency, formatNumber } from './viewUtils'

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
            {vehicle.model_year} · {vehicle.body_style} · {vehicle.fuel_type}
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
                    <h3>{spec.trim}</h3>
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
                    <Fact
                      label="Consumi"
                      value={
                        spec.consumption_l_100km === null
                          ? 'Non disponibile'
                          : `${spec.consumption_l_100km} l/100km`
                      }
                    />
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
                </article>
              ))}
            </div>
          )}
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
