import {
  mockDocumentDetails,
  mockDocuments,
  mockListings,
  mockSearchableDocuments,
  mockVehicleDetails,
  mockVehicles,
} from './mockData'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'

function getApiBaseUrl() {
  return import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
}

export interface VehicleSummary {
  id: string
  make: string
  model: string
  model_year: number
  body_style: string
  fuel_type: string
  market: string
  base_price_eur: number | null
}

export interface VehicleSpec {
  id: string
  trim: string
  drivetrain: string | null
  transmission: string | null
  engine: string | null
  horsepower: number | null
  battery_kwh: number | null
  consumption_l_100km: number | null
  wltp_range_km: number | null
  co2_g_km: number | null
  euro_emission_standard: string | null
  seats: number | null
  cargo_volume_liters: number | null
}

export interface VehicleDetail extends VehicleSummary {
  specs: VehicleSpec[]
}

export interface ListingWithVehicle {
  id: string
  vehicle_id: string
  source_id: string
  listing_ref: string
  title: string
  price_eur: number | null
  mileage: number | null
  condition: string
  location_region: string | null
  listed_at: string | null
  vehicle: VehicleSummary
}

export interface IngestedDocument {
  id: string
  source_id: string
  vehicle_id: string | null
  listing_id: string | null
  document_type: string
  title: string
  content: string
  metadata: Record<string, unknown>
  created_at: string
}

export interface VehicleFilters {
  make?: string
  model?: string
  fuel_type?: string
  body_style?: string
  market?: string
  max_price_eur?: number
  limit?: number
  offset?: number
}

export interface ListingFilters {
  vehicle_id?: string
  make?: string
  model?: string
  max_price_eur?: number
  max_mileage?: number
  location_region?: string
  limit?: number
  offset?: number
}

export interface DocumentFilters {
  source_id?: string
  vehicle_id?: string
  listing_id?: string
  q?: string
  document_type?: string
  limit?: number
  offset?: number
}

export type DocumentSearchMode = 'text_only' | 'vector_fake'

export interface DocumentSearchRequest {
  query: string
  document_type?: string
  limit?: number
  include_content?: boolean
  mode?: DocumentSearchMode
}

export interface DocumentSearchItem {
  id: string
  title: string
  document_type: string
  score: number
  snippet: string
  metadata: {
    source_id: string | null
    vehicle_id: string | null
    listing_id: string | null
    created_at: string | null
  }
  content?: string
}

export interface DocumentSearchResponse {
  query: string
  mode: DocumentSearchMode
  items: DocumentSearchItem[]
}

interface NormalizedDocumentSearchRequest {
  query: string
  document_type?: string
  limit: number
  include_content: boolean
  mode: DocumentSearchMode
}

export type AdvisorPrimaryUse =
  | 'city'
  | 'highway'
  | 'family'
  | 'work'
  | 'new_driver'

export type AdvisorPriority =
  | 'price'
  | 'consumption'
  | 'reliability'
  | 'space'
  | 'safety'
  | 'range'

export interface AdvisorRequest {
  budget_min_eur?: number
  budget_max_eur: number
  primary_use: AdvisorPrimaryUse
  preferred_fuel_type?: string
  preferred_body_style?: string
  max_mileage?: number
  priorities?: AdvisorPriority[]
}

export interface AdvisorDocumentEvidence {
  document_id: string
  title: string
  document_type: string
  score: number
  snippet: string
}

interface AdvisorRecommendationItem {
  vehicle: VehicleSummary
  best_listing: Omit<ListingWithVehicle, 'vehicle'> | null
  score: number
  rationale: string
  evidence: Record<string, unknown>
  document_evidence: AdvisorDocumentEvidence[]
}

export interface AdvisorRecommendationResponse {
  run_id: string
  items: AdvisorRecommendationItem[]
}

export async function fetchVehicles(
  filters: VehicleFilters = {},
): Promise<VehicleSummary[]> {
  const path = buildPath('/vehicles', filters)
  return fetchJson(path, () => filterMockVehicles(filters))
}

export async function fetchVehicle(vehicleId: string): Promise<VehicleDetail> {
  return fetchJson(`/vehicles/${vehicleId}`, () => {
    const vehicle = mockVehicleDetails.find((item) => item.id === vehicleId)
    if (!vehicle) {
      throw new Error('Vehicle not found')
    }
    return vehicle
  })
}

export async function fetchListings(
  filters: ListingFilters = {},
): Promise<ListingWithVehicle[]> {
  const path = buildPath('/listings', filters)
  return fetchJson(path, () => filterMockListings(filters))
}

export async function fetchListing(listingId: string): Promise<ListingWithVehicle> {
  return fetchJson(`/listings/${listingId}`, () => {
    const listing = mockListings.find((item) => item.id === listingId)
    if (!listing) {
      throw new Error('Listing not found')
    }
    return listing
  })
}

export async function fetchDocuments(
  filters: DocumentFilters = {},
): Promise<IngestedDocument[]> {
  const path = buildPath('/documents', filters)
  return fetchJson(path, () => filterMockDocuments(filters))
}

export async function fetchDocument(documentId: string): Promise<IngestedDocument> {
  return fetchJson(`/documents/${documentId}`, () => {
    const document = mockDocumentDetails.find((item) => item.id === documentId)
    if (!document) {
      throw new Error('Document not found')
    }
    return document
  })
}

export async function searchDocuments(
  request: DocumentSearchRequest,
): Promise<DocumentSearchResponse> {
  const normalizedRequest = normalizeDocumentSearchRequest(request)
  return postJson(
    '/search/documents',
    normalizedRequest,
    () => buildMockDocumentSearchResponse(normalizedRequest),
  )
}

export async function fetchAdvisorRecommendations(
  request: AdvisorRequest,
): Promise<AdvisorRecommendationResponse> {
  const response = await fetch(`${getApiBaseUrl()}/advisor/recommendations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const detail = await readErrorDetail(response)
    throw new Error(detail || `Advisor request failed with status ${response.status}`)
  }

  return response.json()
}

async function fetchJson<T>(path: string, mockFallback: () => T): Promise<T> {
  try {
    const response = await fetch(`${getApiBaseUrl()}${path}`)

    if (!response.ok) {
      const detail = await readErrorDetail(response)
      throw new ApiResponseError(
        detail || `API request failed with status ${response.status}`,
      )
    }

    return response.json()
  } catch (error) {
    if (!(error instanceof ApiResponseError) && canUseMockFallback()) {
      return mockFallback()
    }
    throw error
  }
}

async function postJson<T>(
  path: string,
  body: object,
  mockFallback: () => T,
): Promise<T> {
  try {
    const response = await fetch(`${getApiBaseUrl()}${path}`, {
      body: JSON.stringify(body),
      headers: {
        'Content-Type': 'application/json',
      },
      method: 'POST',
    })

    if (!response.ok) {
      const detail = await readErrorDetail(response)
      throw new ApiResponseError(
        detail || `API request failed with status ${response.status}`,
      )
    }

    return response.json()
  } catch (error) {
    if (!(error instanceof ApiResponseError) && canUseMockFallback()) {
      return mockFallback()
    }
    throw error
  }
}

function buildPath(
  path: string,
  filters: VehicleFilters | ListingFilters | DocumentFilters,
) {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      params.set(key, String(value))
    }
  })

  const query = params.toString()
  return query ? `${path}?${query}` : path
}

function canUseMockFallback() {
  return import.meta.env.VITE_USE_MOCK_API === 'true'
}

function filterMockVehicles(filters: VehicleFilters) {
  return paginate(
    mockVehicles.filter((vehicle) => {
      return (
        matchesText(vehicle.make, filters.make) &&
        matchesText(vehicle.model, filters.model) &&
        matchesExact(vehicle.fuel_type, filters.fuel_type) &&
        matchesExact(vehicle.body_style, filters.body_style) &&
        matchesExact(vehicle.market, filters.market) &&
        matchesMax(vehicle.base_price_eur, filters.max_price_eur)
      )
    }),
    normalizeCollectionLimit(filters.limit, 50),
    filters.offset,
  )
}

function filterMockListings(filters: ListingFilters) {
  return paginate(
    mockListings.filter((listing) => {
      return (
        matchesExact(listing.vehicle_id, filters.vehicle_id) &&
        matchesText(listing.vehicle.make, filters.make) &&
        matchesText(listing.vehicle.model, filters.model) &&
        matchesMax(listing.price_eur, filters.max_price_eur) &&
        matchesMax(listing.mileage, filters.max_mileage) &&
        matchesText(listing.location_region, filters.location_region)
      )
    }),
    normalizeCollectionLimit(filters.limit, 50),
    filters.offset,
  )
}

function filterMockDocuments(filters: DocumentFilters) {
  return paginate(
    mockDocuments.filter((document) => {
      const query = filters.q?.toLowerCase()
      const matchesQuery = query
        ? document.title.toLowerCase().includes(query) ||
          document.content.toLowerCase().includes(query)
        : true

      return (
        matchesQuery &&
        matchesExact(document.source_id, filters.source_id) &&
        matchesExact(document.vehicle_id, filters.vehicle_id) &&
        matchesExact(document.listing_id, filters.listing_id) &&
        matchesExact(document.document_type, filters.document_type)
      )
    }),
    normalizeCollectionLimit(filters.limit, 20),
    filters.offset,
  )
}

function buildMockDocumentSearchResponse(
  request: NormalizedDocumentSearchRequest,
): DocumentSearchResponse {
  const query = request.query.toLowerCase()
  const tokens = tokenizeSearchQuery(query)
  if (request.mode === 'vector_fake') {
    return buildMockVectorSearchResponse(request, tokens)
  }

  const scoredDocuments = mockSearchableDocuments
    .filter((document) => matchesExact(document.document_type, request.document_type))
    .map((document) => {
      const score = scoreMockSearchDocument(document, query, tokens)
      return { document, score }
    })
    .filter(({ score }) => score > 0)
  const recencyBounds = getRecencyBounds(
    scoredDocuments.map(({ document }) => document),
  )
  const items = scoredDocuments
    .map(({ document, score }) => ({
      document,
      score: roundScore(score + recencyBoost(document, recencyBounds)),
    }))
    .sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score
      }
      const titleComparison = left.document.title
        .toLowerCase()
        .localeCompare(right.document.title.toLowerCase())
      if (titleComparison !== 0) {
        return titleComparison
      }
      return left.document.id.localeCompare(right.document.id)
    })
    .slice(0, request.limit)
    .map(({ document, score }) =>
      toMockSearchItem(document, score, request, tokens),
    )

  return {
    query: request.query,
    mode: request.mode,
    items,
  }
}

function buildMockVectorSearchResponse(
  request: NormalizedDocumentSearchRequest,
  tokens: string[],
): DocumentSearchResponse {
  const items = mockSearchableDocuments
    .filter((document) => matchesExact(document.document_type, request.document_type))
    .map((document) => ({
      document,
      score: mockVectorScore(request.query, document.id),
    }))
    .sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score
      }
      return left.document.id.localeCompare(right.document.id)
    })
    .slice(0, request.limit)
    .map(({ document, score }) =>
      toMockSearchItem(document, score, request, tokens),
    )

  return {
    query: request.query,
    mode: request.mode,
    items,
  }
}

function normalizeDocumentSearchRequest(
  request: DocumentSearchRequest,
): NormalizedDocumentSearchRequest {
  const query = request.query.trim().replace(/\s+/g, ' ')
  if (!query) {
    throw new Error('Search query is required')
  }

  return {
    query,
    document_type: request.document_type?.trim() || undefined,
    limit: clampSearchLimit(request.limit ?? 10),
    include_content: request.include_content ?? false,
    mode: request.mode ?? 'text_only',
  }
}

function clampSearchLimit(limit: number) {
  if (!Number.isFinite(limit)) {
    return 10
  }
  return Math.min(Math.max(limit, 1), 50)
}

function tokenizeSearchQuery(query: string) {
  return Array.from(
    new Set(
      query.match(/[a-z0-9]+/gi)?.map((token) => token.toLowerCase()) ?? [],
    ),
  )
}

function scoreMockSearchDocument(
  document: IngestedDocument,
  query: string,
  tokens: string[],
) {
  const title = document.title.toLowerCase()
  const content = document.content.toLowerCase()
  let score = 0

  if (title.includes(query)) {
    score += 8
  }
  if (content.includes(query)) {
    score += 4
  }

  tokens.forEach((token) => {
    if (title.includes(token)) {
      score += 2
    }
    if (content.includes(token)) {
      score += 1
    }
  })

  return score
}

function mockVectorScore(query: string, documentId: string) {
  const seed = `${query}:${documentId}`
  let hash = 0
  for (const char of seed) {
    hash = (hash * 31 + char.charCodeAt(0)) % 10000
  }
  return roundScore(0.5 + hash / 20000)
}

function toMockSearchItem(
  document: IngestedDocument,
  score: number,
  request: NormalizedDocumentSearchRequest,
  tokens: string[],
): DocumentSearchItem {
  const item: DocumentSearchItem = {
    id: document.id,
    title: document.title,
    document_type: document.document_type,
    score,
    snippet: buildSnippet(document.title, document.content, request.query, tokens),
    metadata: {
      source_id: document.source_id,
      vehicle_id: document.vehicle_id,
      listing_id: document.listing_id,
      created_at: document.created_at,
    },
  }

  if (request.include_content) {
    item.content = document.content
  }

  return item
}

function buildSnippet(
  title: string,
  content: string,
  query: string,
  tokens: string[],
) {
  const needles = [query, ...tokens]
  const contentMatch = firstMatchIndex(content, needles)
  if (contentMatch !== null) {
    return snippetFrom(content, contentMatch)
  }

  const titleMatch = firstMatchIndex(title, needles)
  if (titleMatch !== null) {
    return snippetFrom(title, titleMatch)
  }

  return snippetFrom(content, 0)
}

function firstMatchIndex(text: string, needles: string[]) {
  const normalizedText = text.toLowerCase()
  for (const needle of needles) {
    if (!needle) {
      continue
    }
    const index = normalizedText.indexOf(needle.toLowerCase())
    if (index >= 0) {
      return index
    }
  }
  return null
}

function snippetFrom(text: string, matchIndex: number) {
  const start = matchIndex > 40 ? matchIndex - 40 : 0
  const snippet = text.slice(start, start + 180).trim()
  return `${start > 0 ? '...' : ''}${snippet}${
    start + 180 < text.length ? '...' : ''
  }`
}

function matchesText(value: string | null, filter?: string) {
  if (!filter) {
    return true
  }
  return value?.toLowerCase().includes(filter.toLowerCase()) ?? false
}

function matchesExact(value: string | null, filter?: string) {
  if (!filter) {
    return true
  }
  return value === filter
}

function matchesMax(value: number | null, max?: number) {
  if (max === undefined) {
    return true
  }
  return value !== null && value <= max
}

function normalizeCollectionLimit(limit: number | undefined, defaultLimit: number) {
  const candidate = limit ?? defaultLimit
  if (!Number.isFinite(candidate)) {
    return defaultLimit
  }
  return Math.min(Math.max(candidate, 1), 100)
}

function paginate<T>(items: T[], limit: number, offset = 0) {
  const start = Math.max(0, offset)
  return items.slice(start, start + limit)
}

function getRecencyBounds(documents: IngestedDocument[]) {
  const dates = documents
    .map((document) => parseDate(document.created_at))
    .filter((date): date is Date => date !== null)

  if (dates.length === 0) {
    return null
  }

  return {
    oldest: new Date(Math.min(...dates.map((date) => date.getTime()))),
    newest: new Date(Math.max(...dates.map((date) => date.getTime()))),
  }
}

function recencyBoost(
  document: IngestedDocument,
  bounds: { oldest: Date; newest: Date } | null,
) {
  const createdAt = parseDate(document.created_at)
  if (!createdAt || !bounds) {
    return 0
  }

  const totalMs = bounds.newest.getTime() - bounds.oldest.getTime()
  if (totalMs <= 0) {
    return 0.05
  }

  return ((createdAt.getTime() - bounds.oldest.getTime()) / totalMs) * 0.25
}

function parseDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function roundScore(score: number) {
  return Number(score.toFixed(4))
}

class ApiResponseError extends Error {}

async function readErrorDetail(response: Response) {
  try {
    const payload = await response.json()
    if (payload && typeof payload.detail === 'string') {
      return payload.detail
    }
  } catch {
    return null
  }
  return null
}
