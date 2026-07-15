import type {
  DocumentFilters,
  ListingFilters,
  VehicleFilters,
} from '../api/drivewise'

type RawSearch = Record<string, unknown>

export function validateVehicleSearch(search: RawSearch): VehicleFilters {
  return compact({
    make: optionalString(search.make),
    fuel_type: optionalString(search.fuel_type),
    body_style: optionalString(search.body_style),
    market: optionalString(search.market)?.toUpperCase(),
    max_price_eur: optionalNumber(search.max_price_eur),
  })
}

export function validateListingSearch(search: RawSearch): ListingFilters {
  return compact({
    make: optionalString(search.make),
    model: optionalString(search.model),
    max_price_eur: optionalNumber(search.max_price_eur),
    max_mileage: optionalInteger(search.max_mileage),
    location_region: optionalString(search.location_region),
  })
}

export function validateDocumentSearch(search: RawSearch): DocumentFilters {
  return compact({
    q: optionalString(search.q),
    document_type: optionalString(search.document_type),
    limit: optionalInteger(search.limit, { minimum: 1, maximum: 100 }),
  })
}

function optionalString(value: unknown) {
  if (typeof value !== 'string') {
    return undefined
  }
  const normalized = value.trim()
  return normalized || undefined
}

function optionalNumber(value: unknown) {
  if (value === '' || value === undefined || value === null) {
    return undefined
  }
  const normalized = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(normalized) && normalized >= 0 ? normalized : undefined
}

function optionalInteger(
  value: unknown,
  bounds: { minimum?: number; maximum?: number } = {},
) {
  const normalized = optionalNumber(value)
  if (normalized === undefined || !Number.isInteger(normalized)) {
    return undefined
  }
  if (bounds.minimum !== undefined && normalized < bounds.minimum) {
    return undefined
  }
  if (bounds.maximum !== undefined && normalized > bounds.maximum) {
    return undefined
  }
  return normalized
}

function compact<T extends Record<string, unknown>>(value: T): T {
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => item !== undefined),
  ) as T
}
