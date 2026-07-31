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
  canonical_key: string
  model_family_key: string
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

export type ModelAnalysisUsageProfile =
  | 'city'
  | 'mixed'
  | 'highway'
  | 'family'
  | 'work'

export type ModelAnalysisScope = 'price' | 'maintenance' | 'red_flags' | 'tco'

export interface ModelAnalysisRequest {
  query?: string
  vehicle_id?: string
  spec_id?: string
  market?: string
  model_year?: number
  fuel_type?: string
  body_style?: string
  asking_price_eur?: number
  current_km?: number
  usage_profile?: ModelAnalysisUsageProfile[]
  analysis_scope?: ModelAnalysisScope[]
}

export interface ModelAnalysisCostSummary {
  market_reference_price_eur: number | null
  estimated_annual_maintenance_eur: number | null
  estimated_monthly_energy_eur: number | null
  estimated_depreciation_3y_eur: number | null
  notes: string[]
}

export interface ModelAnalysisResponse {
  status: 'completed' | 'needs_input' | 'low_confidence' | 'error'
  resolved_vehicle: VehicleSummary | null
  resolved_spec: VehicleSpec | null
  verdict: 'interesting_with_checks' | 'risky_at_price' | 'not_enough_data'
  price_assessment: 'in_range' | 'above_range' | 'below_range' | 'unknown'
  estimated_costs: ModelAnalysisCostSummary
  red_flags: string[]
  checklist: string[]
  confidence: number
  assumptions: string[]
  warnings: string[]
  missing_data: string[]
  next_actions: string[]
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
  | 'efficiency_range'
  | 'space'
  | 'running_cost'

export type AdvisorCondition = 'any' | 'new' | 'used'

export type AdvisorFuelType =
  | 'diesel'
  | 'electric'
  | 'full_hybrid_petrol'
  | 'hybrid_petrol'
  | 'mild_hybrid_petrol'
  | 'petrol'
  | 'petrol_lpg'

export type AdvisorBodyStyle =
  | 'city_car'
  | 'crossover'
  | 'hatchback'
  | 'mpv'
  | 'sedan'
  | 'small_hatchback'
  | 'suv'
  | 'van'
  | 'wagon'

export interface AdvisorRequest {
  budget_min_eur?: number
  budget_max_eur: number
  primary_use: AdvisorPrimaryUse
  condition?: AdvisorCondition
  annual_km?: number
  preferred_fuel_type?: AdvisorFuelType
  preferred_body_style?: AdvisorBodyStyle
  max_mileage?: number
  priorities?: AdvisorPriority[]
}

export type AdvisorScoreComponent =
  | 'price_fit'
  | 'use_case_fit'
  | 'running_cost'
  | 'space'
  | 'efficiency_range'

export interface AdvisorSelectedSpec extends VehicleSpec {
  variant_key: string
  is_default: boolean
  body_style: string
  fuel_type: string
  list_price_eur: number | null
  energy_consumption_kwh_100km: number | null
}

export interface AdvisorOffer {
  id: string
  vehicle_id: string
  spec_id: string
  source_id: string
  listing_ref: string
  title: string
  price_eur: number
  mileage: number | null
  condition: 'new' | 'used' | 'certified'
  location_region: string | null
  source_url: string | null
  listed_at: string | null
  last_seen_at?: string
  valid_until: string | null
  is_active: boolean
}

export interface AdvisorFactor {
  component: AdvisorScoreComponent
  message: string
  metric?: string
  value?: string | number
  threshold?: string | number
  contribution: number
}

export interface AdvisorMetricProvenance {
  metric: string
  source_name: string
  source_url: string | null
  observed_at: string | null
}

export interface AdvisorRecommendationItem {
  vehicle: VehicleSummary
  selected_spec: AdvisorSelectedSpec
  offer: AdvisorOffer
  score: number
  component_scores: Record<AdvisorScoreComponent, number>
  positive_factors: AdvisorFactor[]
  tradeoffs: AdvisorFactor[]
  evidence: Record<string, unknown>
  provenance: AdvisorMetricProvenance[]
}

export interface AdvisorRecommendationGroup {
  condition: Exclude<AdvisorCondition, 'any'>
  items: AdvisorRecommendationItem[]
}

export interface AdvisorRecommendationResponse {
  run_id: string
  scoring_version: string
  assumptions: string[]
  excluded_counts_by_reason: Record<string, number>
  groups: AdvisorRecommendationGroup[]
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
      throw new ApiResponseError('Vehicle not found', 404)
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
      throw new ApiResponseError('Listing not found', 404)
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
      throw new ApiResponseError('Document not found', 404)
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

export async function analyzeModel(
  request: ModelAnalysisRequest,
): Promise<ModelAnalysisResponse> {
  const normalizedRequest = normalizeModelAnalysisRequest(request)
  return postJson(
    '/advisor/model-analysis',
    normalizedRequest,
    () => buildMockModelAnalysisResponse(normalizedRequest),
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
  let response: Response
  try {
    response = await fetch(`${getApiBaseUrl()}${path}`)
  } catch (error) {
    if (canUseMockFallback()) {
      return mockFallback()
    }
    throw error
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response)
    throw new ApiResponseError(
      detail || `API request failed with status ${response.status}`,
      response.status,
    )
  }

  return response.json()
}

async function postJson<T>(
  path: string,
  body: object,
  mockFallback: () => T,
): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${getApiBaseUrl()}${path}`, {
      body: JSON.stringify(body),
      headers: {
        'Content-Type': 'application/json',
      },
      method: 'POST',
    })
  } catch (error) {
    if (canUseMockFallback()) {
      return mockFallback()
    }
    throw error
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response)
    throw new ApiResponseError(
      detail || `API request failed with status ${response.status}`,
      response.status,
    )
  }

  return response.json()
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
  if (query.length > 160) {
    throw new Error('Search query must be 160 characters or fewer')
  }
  if (tokenizeSearchQuery(query).length > 16) {
    throw new Error('Search query must contain 16 terms or fewer')
  }

  return {
    query,
    document_type: request.document_type?.trim() || undefined,
    limit: clampSearchLimit(request.limit ?? 10),
    include_content: request.include_content ?? false,
    mode: request.mode ?? 'text_only',
  }
}

function normalizeModelAnalysisRequest(
  request: ModelAnalysisRequest,
): ModelAnalysisRequest {
  const query = request.query?.trim().replace(/\s+/g, ' ') || undefined
  const vehicleId = request.vehicle_id?.trim() || undefined
  if (!query && !vehicleId) {
    throw new Error('Model query is required')
  }

  return {
    query,
    vehicle_id: vehicleId,
    spec_id: request.spec_id?.trim() || undefined,
    market: (request.market?.trim() || 'IT').toUpperCase(),
    model_year: request.model_year,
    fuel_type: request.fuel_type?.trim() || undefined,
    body_style: request.body_style?.trim() || undefined,
    asking_price_eur: request.asking_price_eur,
    current_km: request.current_km,
    usage_profile: request.usage_profile ?? [],
    analysis_scope: request.analysis_scope ?? [
      'price',
      'maintenance',
      'red_flags',
      'tco',
    ],
  }
}

function buildMockModelAnalysisResponse(
  request: ModelAnalysisRequest,
): ModelAnalysisResponse {
  const vehicle =
    mockVehicles.find((item) => item.id === request.vehicle_id) ??
    mockVehicles.find((item) =>
      normalizeMockText(`${item.make} ${item.model}`).includes(
        normalizeMockText(request.query ?? ''),
      ),
    ) ??
    mockVehicles[0]
  const detail = mockVehicleDetails.find((item) => item.id === vehicle.id)
  const spec = detail?.specs[0] ?? null
  const referenceListing = mockListings.find((item) => item.vehicle_id === vehicle.id)
  const referencePrice =
    referenceListing?.price_eur ??
    vehicle.base_price_eur ??
    request.asking_price_eur ??
    null
  const priceAssessment = assessMockPrice(
    request.asking_price_eur,
    referencePrice,
  )
  const redFlags =
    priceAssessment === 'above_range' ? ['asking_price_above_reference'] : []
  const warnings =
    priceAssessment === 'above_range'
      ? ['asking_price_above_market_reference']
      : []
  const missingData = [
    request.asking_price_eur === undefined ? 'asking_price_eur' : '',
    request.current_km === undefined ? 'current_km' : '',
  ].filter(Boolean)
  const status = missingData.length > 0 ? 'needs_input' : 'completed'

  return {
    status,
    resolved_vehicle: vehicle,
    resolved_spec: spec,
    verdict:
      missingData.length > 0
        ? 'not_enough_data'
        : redFlags.length > 0
          ? 'risky_at_price'
          : 'interesting_with_checks',
    price_assessment: priceAssessment,
    estimated_costs: {
      market_reference_price_eur: referencePrice,
      estimated_annual_maintenance_eur: 560,
      estimated_monthly_energy_eur: spec?.consumption_l_100km
        ? roundScore((12000 * spec.consumption_l_100km * 1.85) / 1200)
        : null,
      estimated_depreciation_3y_eur:
        referencePrice === null ? null : roundScore(referencePrice * 0.28),
      notes: ['annual_km_assumption:12000'],
    },
    red_flags: redFlags,
    checklist: ['verify_service_history', 'inspect_brakes_and_tires'],
    confidence: status === 'completed' ? 0.84 : 0.52,
    assumptions: ['No live market sources are used in Model Analysis V1.'],
    warnings,
    missing_data: missingData,
    next_actions:
      status === 'needs_input'
        ? ['modify_parameters']
        : ['modify_parameters', 'open_checklist', 'compare_alternatives'],
  }
}

function assessMockPrice(
  askingPrice: number | undefined,
  referencePrice: number | null | undefined,
): ModelAnalysisResponse['price_assessment'] {
  if (
    askingPrice === undefined ||
    referencePrice === null ||
    referencePrice === undefined
  ) {
    return 'unknown'
  }
  if (askingPrice > referencePrice * 1.1) {
    return 'above_range'
  }
  if (askingPrice < referencePrice * 0.75) {
    return 'below_range'
  }
  return 'in_range'
}

function normalizeMockText(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
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

class ApiResponseError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiResponseError'
  }
}

export function isApiNotFoundError(error: unknown) {
  return error instanceof ApiResponseError && error.status === 404
}

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
