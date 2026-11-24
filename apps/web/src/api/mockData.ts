import type {
  IngestedDocument,
  ListingWithVehicle,
  VehicleDetail,
  VehicleSpec,
  VehicleSummary,
} from './drivewise'

// The API returns many catalog fields these fixtures do not exercise.
// The factories fill them with the values the API sends for a v1 record.
type VehicleDefaults = 'vehicle_type' | 'generation_key' | 'phase_key' | 'catalog_version'
type SpecDefaults =
  | 'catalog_version'
  | 'powertrain_type'
  | 'fuel'
  | 'engine_code'
  | 'valid_from'
  | 'valid_to'
  | 'external_references'
  | 'variant_key'
  | 'is_default'
  | 'body_style'
  | 'fuel_type'
  | 'list_price_eur'
  | 'energy_consumption_kwh_100km'
  | 'consumption_l_100km_basis'
  | 'energy_consumption_kwh_100km_basis'
  | 'provenance'
type ListingDefaults =
  | 'spec_id'
  | 'source_key'
  | 'source_name'
  | 'source_license'
  | 'source_ranking_permission'
  | 'source_url'
  | 'first_seen_at'
  | 'last_seen_at'
  | 'valid_until'
  | 'is_active'
  | 'content_hash'
  | 'spec'

export function mockVehicle(
  vehicle: Omit<VehicleSummary, VehicleDefaults> & Partial<VehicleSummary>,
): VehicleSummary {
  return {
    vehicle_type: 'car',
    generation_key: null,
    phase_key: null,
    catalog_version: 1,
    ...vehicle,
  }
}

export function mockSpec(
  spec: Omit<VehicleSpec, SpecDefaults> & Partial<VehicleSpec>,
): VehicleSpec {
  return {
    catalog_version: 1,
    powertrain_type: null,
    fuel: null,
    engine_code: null,
    valid_from: null,
    valid_to: null,
    external_references: [],
    variant_key: null,
    is_default: true,
    body_style: null,
    fuel_type: null,
    list_price_eur: null,
    energy_consumption_kwh_100km: null,
    consumption_l_100km_basis: null,
    energy_consumption_kwh_100km_basis: null,
    provenance: [],
    ...spec,
  }
}

export function mockListing(
  listing: Omit<ListingWithVehicle, ListingDefaults> & Partial<ListingWithVehicle>,
): ListingWithVehicle {
  return {
    spec_id: null,
    source_key: null,
    source_name: null,
    source_license: null,
    source_ranking_permission: null,
    source_url: null,
    first_seen_at: null,
    last_seen_at: null,
    valid_until: null,
    is_active: true,
    content_hash: null,
    spec: null,
    ...listing,
  }
}

type VehicleSpecDetail = VehicleDetail['specs'][number]

// Builds the nested knowledge profile the detail endpoint returns from the flat
// spec fields; fields the fixture does not know stay null, as in the API.
export function mockSpecDetail(
  spec: Omit<VehicleSpec, SpecDefaults> & Partial<VehicleSpec>,
): VehicleSpecDetail {
  const flat = mockSpec(spec)
  return {
    ...flat,
    identity: { generation_name: null, restyling_label: null, category: null, doors: null },
    dimensions: {
      length_mm: null,
      width_mm: null,
      height_mm: null,
      wheelbase_mm: null,
      curb_weight_kg: null,
      gross_weight_kg: null,
      payload_kg: null,
      seats: flat.seats,
      cargo_volume_liters: flat.cargo_volume_liters,
    },
    powertrain: {
      engine_description: flat.engine,
      engine_code: flat.engine_code,
      displacement_cc: null,
      cylinders: null,
      horsepower: flat.horsepower,
      power_kw: null,
      torque_nm: null,
      fuel_type: flat.fuel_type,
      battery_total_kwh: flat.battery_kwh,
      battery_usable_kwh: null,
      wltp_range_km: flat.wltp_range_km,
    },
    transmission_details: {
      transmission: flat.transmission,
      transmission_type: null,
      gear_count: null,
      drivetrain: flat.drivetrain,
      differential_type: null,
    },
    performance: {
      acceleration_0_100_s: null,
      top_speed_kmh: null,
      braking_100_0_m: null,
      power_to_weight_kw_per_t: null,
    },
    official_efficiency: {
      homologation_cycle: null,
      consumption_l_100km: flat.consumption_l_100km,
      energy_consumption_kwh_100km: flat.energy_consumption_kwh_100km,
      co2_g_km: flat.co2_g_km,
      euro_emission_standard: flat.euro_emission_standard,
    },
    maintenance_schedule: [],
    safety: { ratings: [], adas: [], equipment: [] },
    technology_comfort: [],
    media: [],
    two_wheel: {
      seat_height_mm: null,
      wet_weight_kg: null,
      fuel_tank_capacity_liters: null,
      underseat_storage_liters: null,
    },
    // v1 fixtures have no catalogue list-price terms.
    list_price: null,
  }
}

export const mockVehicles: VehicleSummary[] = [
  {
    id: '00000000-0000-4000-8000-000000000001',
    canonical_key: 'fiat-panda-2024-it',
    model_family_key: 'fiat-panda',
    make: 'Fiat',
    model: 'Panda',
    model_year: 2024,
    body_style: 'city_car',
    fuel_type: 'mild_hybrid_petrol',
    market: 'IT',
    base_price_eur: 15500,
  },
  {
    id: '00000000-0000-4000-8000-000000000002',
    canonical_key: 'toyota-yaris-hybrid-2024-it',
    model_family_key: 'toyota-yaris',
    make: 'Toyota',
    model: 'Yaris Hybrid',
    model_year: 2024,
    body_style: 'hatchback',
    fuel_type: 'hybrid_petrol',
    market: 'IT',
    base_price_eur: 24550,
  },
  {
    id: '00000000-0000-4000-8000-000000000003',
    canonical_key: 'volkswagen-golf-2024-eu',
    model_family_key: 'volkswagen-golf',
    make: 'Volkswagen',
    model: 'Golf',
    model_year: 2024,
    body_style: 'hatchback',
    fuel_type: 'petrol',
    market: 'EU',
    base_price_eur: 30250,
  },
  {
    id: '00000000-0000-4000-8000-000000000004',
    canonical_key: 'dacia-sandero-2024-it',
    model_family_key: 'dacia-sandero',
    make: 'Dacia',
    model: 'Sandero',
    model_year: 2024,
    body_style: 'hatchback',
    fuel_type: 'petrol_lpg',
    market: 'IT',
    base_price_eur: 13750,
  },
  {
    id: '00000000-0000-4000-8000-000000000005',
    canonical_key: 'tesla-model-3-2024-eu',
    model_family_key: 'tesla-model-3',
    make: 'Tesla',
    model: 'Model 3',
    model_year: 2024,
    body_style: 'sedan',
    fuel_type: 'electric',
    market: 'EU',
    base_price_eur: 42990,
  },
].map(mockVehicle)

export const mockVehicleDetails: VehicleDetail[] = [
  {
    ...mockVehicles[0],
    provenance: [],
    specs: [
      mockSpecDetail({
        id: '20000000-0000-4000-8000-000000000001',
        trim: '1.0 FireFly Hybrid',
        drivetrain: 'fwd',
        transmission: '6-speed manual',
        engine: '1.0L mild-hybrid petrol',
        horsepower: 70,
        battery_kwh: null,
        consumption_l_100km: 5,
        wltp_range_km: null,
        co2_g_km: 113,
        euro_emission_standard: 'Euro 6e',
        seats: 4,
        cargo_volume_liters: 225,
      }),
    ],
  },
  {
    ...mockVehicles[1],
    provenance: [],
    specs: [
      mockSpecDetail({
        id: '20000000-0000-4000-8000-000000000002',
        trim: '1.5 Hybrid Active',
        drivetrain: 'fwd',
        transmission: 'ecvt',
        engine: '1.5L full-hybrid petrol',
        horsepower: 116,
        battery_kwh: null,
        consumption_l_100km: 3.8,
        wltp_range_km: null,
        co2_g_km: 87,
        euro_emission_standard: 'Euro 6e',
        seats: 5,
        cargo_volume_liters: 286,
      }),
    ],
  },
  {
    ...mockVehicles[2],
    provenance: [],
    specs: [
      mockSpecDetail({
        id: '20000000-0000-4000-8000-000000000003',
        trim: '1.5 TSI',
        drivetrain: 'fwd',
        transmission: '6-speed manual',
        engine: '1.5L turbo petrol',
        horsepower: 150,
        battery_kwh: null,
        consumption_l_100km: 5.4,
        wltp_range_km: null,
        co2_g_km: 123,
        euro_emission_standard: 'Euro 6e',
        seats: 5,
        cargo_volume_liters: 381,
      }),
    ],
  },
  {
    ...mockVehicles[3],
    provenance: [],
    specs: [
      mockSpecDetail({
        id: '20000000-0000-4000-8000-000000000004',
        trim: 'Eco-G 100',
        drivetrain: 'fwd',
        transmission: '6-speed manual',
        engine: '1.0L turbo petrol/LPG',
        horsepower: 100,
        battery_kwh: null,
        consumption_l_100km: 6.5,
        wltp_range_km: null,
        co2_g_km: 108,
        euro_emission_standard: 'Euro 6e',
        seats: 5,
        cargo_volume_liters: 328,
      }),
    ],
  },
  {
    ...mockVehicles[4],
    provenance: [],
    specs: [
      mockSpecDetail({
        id: '20000000-0000-4000-8000-000000000005',
        trim: 'Rear-Wheel Drive',
        drivetrain: 'rwd',
        transmission: 'single-speed',
        engine: 'single electric motor',
        horsepower: 283,
        battery_kwh: 57.5,
        consumption_l_100km: null,
        wltp_range_km: 513,
        co2_g_km: 0,
        euro_emission_standard: null,
        seats: 5,
        cargo_volume_liters: 594,
      }),
    ],
  },
]

export const mockListings: ListingWithVehicle[] = [
  {
    id: '30000000-0000-4000-8000-000000000001',
    vehicle_id: mockVehicles[0].id,
    source_id: '10000000-0000-4000-8000-000000000001',
    listing_ref: 'seed-fiat-panda-2024-it',
    title: 'Fiat Panda 1.0 FireFly Hybrid',
    price_eur: 14200,
    mileage: 6400,
    condition: 'used',
    location_region: 'Piemonte',
    listed_at: '2026-01-15',
    vehicle: mockVehicles[0],
  },
  {
    id: '30000000-0000-4000-8000-000000000002',
    vehicle_id: mockVehicles[1].id,
    source_id: '10000000-0000-4000-8000-000000000001',
    listing_ref: 'seed-toyota-yaris-hybrid-2024-it',
    title: 'Toyota Yaris Hybrid 1.5 Active',
    price_eur: 23200,
    mileage: 11800,
    condition: 'used',
    location_region: 'Lombardia',
    listed_at: '2026-01-18',
    vehicle: mockVehicles[1],
  },
  {
    id: '30000000-0000-4000-8000-000000000003',
    vehicle_id: mockVehicles[2].id,
    source_id: '10000000-0000-4000-8000-000000000001',
    listing_ref: 'seed-volkswagen-golf-2024-eu',
    title: 'Volkswagen Golf 1.5 TSI',
    price_eur: 28900,
    mileage: 9500,
    condition: 'used',
    location_region: 'Veneto',
    listed_at: '2026-01-20',
    vehicle: mockVehicles[2],
  },
  {
    id: '30000000-0000-4000-8000-000000000004',
    vehicle_id: mockVehicles[3].id,
    source_id: '10000000-0000-4000-8000-000000000001',
    listing_ref: 'seed-dacia-sandero-2024-it',
    title: 'Dacia Sandero Eco-G 100',
    price_eur: 12800,
    mileage: 14300,
    condition: 'used',
    location_region: 'Lazio',
    listed_at: '2026-01-22',
    vehicle: mockVehicles[3],
  },
  {
    id: '30000000-0000-4000-8000-000000000005',
    vehicle_id: mockVehicles[4].id,
    source_id: '10000000-0000-4000-8000-000000000001',
    listing_ref: 'seed-tesla-model-3-2024-eu',
    title: 'Tesla Model 3 Rear-Wheel Drive',
    price_eur: 39700,
    mileage: 17600,
    condition: 'used',
    location_region: 'Emilia-Romagna',
    listed_at: '2026-01-24',
    vehicle: mockVehicles[4],
  },
].map(mockListing)

export const mockDocuments: IngestedDocument[] = [
  {
    id: '40000000-0000-4000-8000-000000000001',
    source_id: '10000000-0000-4000-8000-000000000001',
    vehicle_id: mockVehicles[0].id,
    listing_id: mockListings[0].id,
    document_type: 'seed_note',
    title: 'Synthetic profile: Fiat Panda',
    content:
      'Synthetic seed note for a compact Italian city car with mild-hybrid petrol power, low running costs, and urban-friendly dimensions.',
    metadata: {
      synthetic: true,
      market_context: 'IT',
    },
    created_at: '2026-01-15T00:00:00Z',
  },
  {
    id: '40000000-0000-4000-8000-000000000002',
    source_id: '10000000-0000-4000-8000-000000000001',
    vehicle_id: mockVehicles[1].id,
    listing_id: mockListings[1].id,
    document_type: 'seed_note',
    title: 'Synthetic profile: Toyota Yaris Hybrid',
    content:
      'Synthetic seed note for a hybrid hatchback popular in Italian cities, with low WLTP consumption and practical daily usability.',
    metadata: {
      synthetic: true,
      market_context: 'IT',
    },
    created_at: '2026-01-18T00:00:00Z',
  },
  {
    id: '40000000-0000-4000-8000-000000000003',
    source_id: '10000000-0000-4000-8000-000000000001',
    vehicle_id: mockVehicles[2].id,
    listing_id: mockListings[2].id,
    document_type: 'seed_note',
    title: 'Synthetic profile: Volkswagen Golf',
    content:
      'Synthetic seed note for a European compact hatchback with balanced motorway comfort, petrol efficiency, and broad parts availability.',
    metadata: {
      synthetic: true,
      market_context: 'EU',
    },
    created_at: '2026-01-20T00:00:00Z',
  },
  {
    id: '40000000-0000-4000-8000-000000000004',
    source_id: '10000000-0000-4000-8000-000000000001',
    vehicle_id: mockVehicles[3].id,
    listing_id: mockListings[3].id,
    document_type: 'seed_note',
    title: 'Synthetic profile: Dacia Sandero',
    content:
      'Synthetic seed note for an affordable hatchback with petrol/LPG availability, simple maintenance, and strong value positioning.',
    metadata: {
      synthetic: true,
      market_context: 'IT',
    },
    created_at: '2026-01-22T00:00:00Z',
  },
  {
    id: '40000000-0000-4000-8000-000000000005',
    source_id: '10000000-0000-4000-8000-000000000001',
    vehicle_id: mockVehicles[4].id,
    listing_id: mockListings[4].id,
    document_type: 'seed_note',
    title: 'Synthetic profile: Tesla Model 3',
    content:
      'Synthetic seed note for an electric sedan with WLTP range, zero tailpipe CO2, and charging-dependent ownership fit in Europe.',
    metadata: {
      synthetic: true,
      market_context: 'EU',
    },
    created_at: '2026-01-24T00:00:00Z',
  },
  {
    id: '41000000-0000-4000-8000-000000000001',
    source_id: '10000000-0000-4000-8000-000000000010',
    vehicle_id: null,
    listing_id: null,
    document_type: 'listing_snapshot',
    title: 'Fiat Panda local listing',
    content:
      'Title: Fiat Panda 1.0 FireFly Hybrid\nMake: Fiat\nModel: Panda\nYear: 2024\nPrice EUR: 14200\nMileage km: 6400\nFuel type: mild_hybrid_petrol\nCondition: used\nLocation region: Piemonte\n\nFixture sintetica di listing locale. Non deriva da fonti web.',
    metadata: {
      content_hash: 'hash-fiat-panda-listing',
      local_path: 'data/fixtures/ingestion/fiat-panda-listing.txt',
      proposed_vehicle: {
        make: 'Fiat',
        model: 'Panda',
      },
      proposed_listing: {
        price_eur: 14200,
        mileage: 6400,
      },
      unparsed_fields: {
        free_text: 'fixture sintetica locale',
      },
    },
    created_at: '2026-01-15T00:00:00Z',
  },
  {
    id: '41000000-0000-4000-8000-000000000002',
    source_id: '10000000-0000-4000-8000-000000000010',
    vehicle_id: null,
    listing_id: null,
    document_type: 'vehicle_profile',
    title: 'Toyota Yaris Hybrid local profile',
    content:
      '# Toyota Yaris Hybrid 2024\n\nFixture sintetica per ingestion locale Drivewise. Non deriva da fonti web.\n\nMake: Toyota\nModel: Yaris Hybrid\nYear: 2024\nFuel type: hybrid_petrol\nIndicative price EUR: 24550\n\nNota: utilitaria ibrida per contesto urbano e suburbano.',
    metadata: {
      content_hash: 'hash-toyota-yaris',
      local_path: 'data/fixtures/ingestion/toyota-yaris-hybrid.md',
      proposed_vehicle: {
        make: 'Toyota',
        model: 'Yaris Hybrid',
        model_year: 2024,
        fuel_type: 'hybrid_petrol',
      },
      proposed_listing: {},
      unparsed_fields: {},
    },
    created_at: '2026-01-15T00:00:00Z',
  },
  {
    id: '41000000-0000-4000-8000-000000000003',
    source_id: '10000000-0000-4000-8000-000000000010',
    vehicle_id: null,
    listing_id: null,
    document_type: 'vehicle_profile',
    title: 'Fiat Panda local profile',
    content:
      '# Fiat Panda 2024\n\nFixture sintetica per ingestion locale Drivewise. Non deriva da fonti web.\n\nMake: Fiat\nModel: Panda\nYear: 2024\nFuel type: mild_hybrid_petrol\nIndicative price EUR: 15500\n\nNota: city car compatta per uso urbano, con dati volutamente minimi.',
    metadata: {
      content_hash: 'hash-fiat-panda',
      local_path: 'data/fixtures/ingestion/fiat-panda.md',
      proposed_vehicle: {
        make: 'Fiat',
        model: 'Panda',
        model_year: 2024,
        fuel_type: 'mild_hybrid_petrol',
      },
      proposed_listing: {},
      unparsed_fields: {},
    },
    created_at: '2026-01-15T00:00:00Z',
  },
]

export const mockDocumentDetails: IngestedDocument[] = mockDocuments

export const mockSearchableDocuments: IngestedDocument[] = mockDocuments
