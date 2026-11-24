import type { components } from './schema.gen'

/**
 * The public base when VITE_API_BASE_URL is unset. A production build serves the API on the
 * same origin under /api; only a local dev run talks to a separate API on 127.0.0.1:8000.
 */
export function defaultPublicApiBaseUrl(prod: boolean): string {
  if (prod) return '/api'
  // Vite folds import.meta.env.DEV to false in a production build, which drops the local URL from its code.
  return import.meta.env.DEV ? 'http://127.0.0.1:8000' : '/api'
}

export type ApiBaseInput = {
  ssr: boolean
  internalUrl?: string | undefined
  publicUrl?: string | undefined
  /** Defaults to the build mode, `import.meta.env.PROD`. */
  prod?: boolean | undefined
}

/**
 * The browser uses the public base (for one origin, "/api"). The server cannot
 * fetch a relative base, so server rendering needs API_INTERNAL_URL, which
 * Vercel injects for the API service and a local run sets by hand.
 */
export function resolveApiBaseUrl({ ssr, internalUrl, publicUrl, prod = Boolean(import.meta.env.PROD) }: ApiBaseInput): string {
  if (ssr && internalUrl) return internalUrl.replace(/\/$/, '')
  const base = (publicUrl || defaultPublicApiBaseUrl(prod)).replace(/\/$/, '')
  if (ssr && base.startsWith('/')) {
    throw new Error(`API_INTERNAL_URL is required for server rendering when VITE_API_BASE_URL is "${base}".`)
  }
  return base
}

function getApiBaseUrl() {
  return resolveApiBaseUrl({
    ssr: Boolean(import.meta.env.SSR),
    internalUrl: import.meta.env.SSR ? process.env.API_INTERNAL_URL : undefined,
    publicUrl: import.meta.env.VITE_API_BASE_URL,
  })
}

// Response and request shapes come from the API's OpenAPI schema.
// Regenerate with `bun run gen:api-types` after changing a FastAPI model.
type Schemas = components['schemas']

export type VehicleSummary = Schemas['VehicleSummary']
export type VehicleDetail = Schemas['VehicleDetail']
export type VehicleSpecDetail = Schemas['VehicleSpecDetail']
export type VehicleType = NonNullable<VehicleSummary['vehicle_type']>

export type ModelAnalysisRequest = Schemas['ModelAnalysisRequest']
export type ModelAnalysisResponse = Schemas['ModelAnalysisResponse']

export interface VehicleFilters {
  vehicle_type?: VehicleType
  limit?: number
  offset?: number
}

export type AdvisorOffer = Schemas['AdvisorOffer']
export type ListPrice = Schemas['ListPrice']
export type SourceProvenance = Schemas['VehicleProvenance']
export type AdvisorMetricProvenance = Schemas['AdvisorMetricProvenance']
export type AdvisorRecommendationItem = Schemas['AdvisorRecommendationItem']
export type AdvisorRecommendationGroup = Schemas['AdvisorRecommendationGroup']

export async function fetchVehicles(filters: VehicleFilters = {}): Promise<VehicleSummary[]> {
  return fetchJson(buildPath('/vehicles', filters))
}

export async function fetchVehicle(vehicleId: string): Promise<VehicleDetail> {
  return fetchJson(`/vehicles/${encodeURIComponent(vehicleId)}`)
}

export async function analyzeModel(request: ModelAnalysisRequest): Promise<ModelAnalysisResponse> {
  return postJson('/advisor/model-analysis', normalizeModelAnalysisRequest(request))
}

/** Server rendering waits at most this long for the API, so a slow API cannot hang a page. */
export const SSR_FETCH_TIMEOUT_MS = 8000

/** An abort signal for a server-rendering fetch; the browser keeps its own timeouts. */
export function ssrFetchSignal(ssr: boolean, timeoutMs = SSR_FETCH_TIMEOUT_MS): AbortSignal | undefined {
  return ssr ? AbortSignal.timeout(timeoutMs) : undefined
}

async function fetchJson<T>(path: string): Promise<T> {
  const signal = ssrFetchSignal(Boolean(import.meta.env.SSR))
  const url = `${getApiBaseUrl()}${path}`
  return readJson(await (signal ? fetch(url, { signal }) : fetch(url)))
}

async function postJson<T>(path: string, body: object): Promise<T> {
  const signal = ssrFetchSignal(Boolean(import.meta.env.SSR))
  return readJson(
    await fetch(`${getApiBaseUrl()}${path}`, {
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
      method: 'POST',
      ...(signal ? { signal } : {}),
    }),
  )
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await readErrorDetail(response)
    throw new ApiResponseError(
      detail || `API request failed with status ${response.status}`,
      response.status,
    )
  }
  return response.json()
}

function buildPath(path: string, filters: VehicleFilters) {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      params.set(key, String(value))
    }
  })
  const query = params.toString()
  return query ? `${path}?${query}` : path
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

// Guided Decision uses the existing persisted backend contract; errors never become mock rankings.
export interface GuidedDecisionResponse {
  contractVersion: 'guided-decision-v1'
  decisionId: string
  profileVersion: number
  status: 'active' | 'completed' | 'abandoned'
  message: string
  decisionProfile: Record<string, { value: string | number | boolean | string[] } | Record<string, { value: number } | null> | null>
  profileCompletion: number
  decisionConfidence: number
  missingInformation: { key: string; reason: string }[]
  nextQuestion: { id: string; type: 'number' | 'boolean' | 'single_select' | 'multi_select' | 'text'; label: string; reason: string; constraints: { minimum: number | null; maximum: number | null; unit: string | null; options: string[] } | null } | null
  previewRanking: { status: 'blocked' | 'provisional' | 'ready' | 'insufficient_inventory'; groups: AdvisorRecommendationGroup[]; assumptions: string[]; blockingReasons: string[] }
  garageCompatibility: { vehicleId: string; specId: string; status: 'comfortable' | 'tight' | 'incompatible' | 'insufficient_data'; message: string }[]
  warnings: string[]
}
export async function createGuidedDecision(message: string): Promise<GuidedDecisionResponse> {
  return postJson('/guided-decisions', { message, locale: 'it-IT', market: 'IT' })
}
export async function addGuidedDecisionTurn(decisionId: string, message: string, expectedProfileVersion: number): Promise<GuidedDecisionResponse> {
  return postJson(`/guided-decisions/${encodeURIComponent(decisionId)}/turns`, { message, expectedProfileVersion })
}
export async function fetchGuidedDecision(decisionId: string): Promise<GuidedDecisionResponse> {
  return fetchJson(`/guided-decisions/${encodeURIComponent(decisionId)}`)
}
