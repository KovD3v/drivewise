import { useEffect, useState } from 'react'
import { Link } from '@tanstack/react-router'

import { fetchVehicle, VehicleDetail } from '../api/drivewise'
import { errorMessage, formatCurrency, formatNumber } from './viewUtils'

export function VehicleDetailPage({ vehicleId }: { vehicleId: string }) {
  const [vehicle, setVehicle] = useState<VehicleDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isCurrent = true
    setIsLoading(true)
    setError(null)

    fetchVehicle(vehicleId)
      .then((data) => {
        if (isCurrent) {
          setVehicle(data)
        }
      })
      .catch((caughtError) => {
        if (isCurrent) {
          setError(errorMessage(caughtError, 'Unable to load vehicle'))
          setVehicle(null)
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
  }, [vehicleId])

  return (
    <main className="browse-shell">
      <header className="browse-header">
        <Link className="text-link" to="/vehicles">
          Veicoli
        </Link>
        <div>
          <p className="eyebrow">Vehicle detail</p>
          <h1>{vehicle ? `${vehicle.make} ${vehicle.model}` : 'Dettaglio veicolo'}</h1>
          {vehicle ? (
            <p className="summary">
              {vehicle.model_year} · {vehicle.body_style} · {vehicle.fuel_type}
            </p>
          ) : null}
        </div>
      </header>

      <section className="detail-panel" aria-live="polite">
        {isLoading ? <p className="status-message">Caricamento…</p> : null}
        {error ? <p className="error-message">{error}</p> : null}

        {vehicle ? (
          <>
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
                            spec.seats === null ? 'Non disponibile' : String(spec.seats)
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
