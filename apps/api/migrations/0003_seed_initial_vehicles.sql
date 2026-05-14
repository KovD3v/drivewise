INSERT INTO sources (id, name, source_type, url, license, notes)
VALUES (
  '10000000-0000-4000-8000-000000000001',
  'Drivewise Synthetic EU Seed',
  'manual_seed',
  NULL,
  'Synthetic test data',
  'Synthetic seed data for local development in the Italian and European market. Values are illustrative and not authoritative.'
)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  source_type = EXCLUDED.source_type,
  url = EXCLUDED.url,
  license = EXCLUDED.license,
  notes = EXCLUDED.notes;

INSERT INTO vehicles (
  id,
  make,
  model,
  model_year,
  body_style,
  fuel_type,
  market,
  base_price_eur
)
VALUES
  (
    '00000000-0000-4000-8000-000000000001',
    'Fiat',
    'Panda',
    2024,
    'city_car',
    'mild_hybrid_petrol',
    'IT',
    15500.00
  ),
  (
    '00000000-0000-4000-8000-000000000002',
    'Toyota',
    'Yaris Hybrid',
    2024,
    'hatchback',
    'hybrid_petrol',
    'IT',
    24550.00
  ),
  (
    '00000000-0000-4000-8000-000000000003',
    'Volkswagen',
    'Golf',
    2024,
    'hatchback',
    'petrol',
    'EU',
    30250.00
  ),
  (
    '00000000-0000-4000-8000-000000000004',
    'Dacia',
    'Sandero',
    2024,
    'hatchback',
    'petrol_lpg',
    'IT',
    13750.00
  ),
  (
    '00000000-0000-4000-8000-000000000005',
    'Tesla',
    'Model 3',
    2024,
    'sedan',
    'electric',
    'EU',
    42990.00
  )
ON CONFLICT (id) DO UPDATE SET
  make = EXCLUDED.make,
  model = EXCLUDED.model,
  model_year = EXCLUDED.model_year,
  market = EXCLUDED.market,
  body_style = EXCLUDED.body_style,
  fuel_type = EXCLUDED.fuel_type,
  base_price_eur = EXCLUDED.base_price_eur,
  updated_at = now();

INSERT INTO vehicle_specs (
  id,
  vehicle_id,
  trim,
  drivetrain,
  transmission,
  engine,
  horsepower,
  battery_kwh,
  consumption_l_100km,
  wltp_range_km,
  co2_g_km,
  euro_emission_standard,
  seats,
  cargo_volume_liters,
  metadata
)
VALUES
  (
    '20000000-0000-4000-8000-000000000001',
    '00000000-0000-4000-8000-000000000001',
    '1.0 FireFly Hybrid',
    'fwd',
    '6-speed manual',
    '1.0L mild-hybrid petrol',
    70,
    NULL,
    5.00,
    NULL,
    113,
    'Euro 6e',
    4,
    225.00,
    '{"synthetic": true, "market_context": "IT"}'::jsonb
  ),
  (
    '20000000-0000-4000-8000-000000000002',
    '00000000-0000-4000-8000-000000000002',
    '1.5 Hybrid Active',
    'fwd',
    'ecvt',
    '1.5L full-hybrid petrol',
    116,
    NULL,
    3.80,
    NULL,
    87,
    'Euro 6e',
    5,
    286.00,
    '{"synthetic": true, "market_context": "IT"}'::jsonb
  ),
  (
    '20000000-0000-4000-8000-000000000003',
    '00000000-0000-4000-8000-000000000003',
    '1.5 TSI',
    'fwd',
    '6-speed manual',
    '1.5L turbo petrol',
    150,
    NULL,
    5.40,
    NULL,
    123,
    'Euro 6e',
    5,
    381.00,
    '{"synthetic": true, "market_context": "EU"}'::jsonb
  ),
  (
    '20000000-0000-4000-8000-000000000004',
    '00000000-0000-4000-8000-000000000004',
    'Eco-G 100',
    'fwd',
    '6-speed manual',
    '1.0L turbo petrol/LPG',
    100,
    NULL,
    6.50,
    NULL,
    108,
    'Euro 6e',
    5,
    328.00,
    '{"synthetic": true, "market_context": "IT"}'::jsonb
  ),
  (
    '20000000-0000-4000-8000-000000000005',
    '00000000-0000-4000-8000-000000000005',
    'Rear-Wheel Drive',
    'rwd',
    'single-speed',
    'single electric motor',
    283,
    57.50,
    NULL,
    513,
    0,
    NULL,
    5,
    594.00,
    '{"synthetic": true, "market_context": "EU"}'::jsonb
  )
ON CONFLICT (id) DO UPDATE SET
  vehicle_id = EXCLUDED.vehicle_id,
  trim = EXCLUDED.trim,
  drivetrain = EXCLUDED.drivetrain,
  transmission = EXCLUDED.transmission,
  engine = EXCLUDED.engine,
  horsepower = EXCLUDED.horsepower,
  battery_kwh = EXCLUDED.battery_kwh,
  consumption_l_100km = EXCLUDED.consumption_l_100km,
  wltp_range_km = EXCLUDED.wltp_range_km,
  co2_g_km = EXCLUDED.co2_g_km,
  euro_emission_standard = EXCLUDED.euro_emission_standard,
  seats = EXCLUDED.seats,
  cargo_volume_liters = EXCLUDED.cargo_volume_liters,
  metadata = EXCLUDED.metadata,
  updated_at = now();

INSERT INTO listings (
  id,
  vehicle_id,
  source_id,
  listing_ref,
  title,
  price_eur,
  mileage,
  condition,
  location_region,
  listed_at,
  raw_payload
)
VALUES
  (
    '30000000-0000-4000-8000-000000000001',
    '00000000-0000-4000-8000-000000000001',
    '10000000-0000-4000-8000-000000000001',
    'seed-fiat-panda-2024-it',
    'Fiat Panda 1.0 FireFly Hybrid',
    14200.00,
    6400,
    'used',
    'Piemonte',
    DATE '2026-01-15',
    '{"synthetic": true, "currency": "EUR", "odometer_unit": "km"}'::jsonb
  ),
  (
    '30000000-0000-4000-8000-000000000002',
    '00000000-0000-4000-8000-000000000002',
    '10000000-0000-4000-8000-000000000001',
    'seed-toyota-yaris-hybrid-2024-it',
    'Toyota Yaris Hybrid 1.5 Active',
    23200.00,
    11800,
    'used',
    'Lombardia',
    DATE '2026-01-18',
    '{"synthetic": true, "currency": "EUR", "odometer_unit": "km"}'::jsonb
  ),
  (
    '30000000-0000-4000-8000-000000000003',
    '00000000-0000-4000-8000-000000000003',
    '10000000-0000-4000-8000-000000000001',
    'seed-volkswagen-golf-2024-eu',
    'Volkswagen Golf 1.5 TSI',
    28900.00,
    9500,
    'used',
    'Veneto',
    DATE '2026-01-20',
    '{"synthetic": true, "currency": "EUR", "odometer_unit": "km"}'::jsonb
  ),
  (
    '30000000-0000-4000-8000-000000000004',
    '00000000-0000-4000-8000-000000000004',
    '10000000-0000-4000-8000-000000000001',
    'seed-dacia-sandero-2024-it',
    'Dacia Sandero Eco-G 100',
    12800.00,
    14300,
    'used',
    'Lazio',
    DATE '2026-01-22',
    '{"synthetic": true, "currency": "EUR", "odometer_unit": "km"}'::jsonb
  ),
  (
    '30000000-0000-4000-8000-000000000005',
    '00000000-0000-4000-8000-000000000005',
    '10000000-0000-4000-8000-000000000001',
    'seed-tesla-model-3-2024-eu',
    'Tesla Model 3 Rear-Wheel Drive',
    39700.00,
    17600,
    'used',
    'Emilia-Romagna',
    DATE '2026-01-24',
    '{"synthetic": true, "currency": "EUR", "odometer_unit": "km"}'::jsonb
  )
ON CONFLICT (id) DO UPDATE SET
  vehicle_id = EXCLUDED.vehicle_id,
  source_id = EXCLUDED.source_id,
  listing_ref = EXCLUDED.listing_ref,
  title = EXCLUDED.title,
  price_eur = EXCLUDED.price_eur,
  mileage = EXCLUDED.mileage,
  condition = EXCLUDED.condition,
  location_region = EXCLUDED.location_region,
  listed_at = EXCLUDED.listed_at,
  raw_payload = EXCLUDED.raw_payload,
  updated_at = now();

INSERT INTO documents (
  id,
  source_id,
  vehicle_id,
  listing_id,
  document_type,
  title,
  content,
  embedding,
  embedding_model,
  metadata
)
VALUES
  (
    '40000000-0000-4000-8000-000000000001',
    '10000000-0000-4000-8000-000000000001',
    '00000000-0000-4000-8000-000000000001',
    '30000000-0000-4000-8000-000000000001',
    'seed_note',
    'Synthetic profile: Fiat Panda',
    'Synthetic seed note for a compact Italian city car with mild-hybrid petrol power, low running costs, and urban-friendly dimensions.',
    NULL,
    NULL,
    '{"synthetic": true, "market_context": "IT"}'::jsonb
  ),
  (
    '40000000-0000-4000-8000-000000000002',
    '10000000-0000-4000-8000-000000000001',
    '00000000-0000-4000-8000-000000000002',
    '30000000-0000-4000-8000-000000000002',
    'seed_note',
    'Synthetic profile: Toyota Yaris Hybrid',
    'Synthetic seed note for a hybrid hatchback popular in Italian cities, with low WLTP consumption and practical daily usability.',
    NULL,
    NULL,
    '{"synthetic": true, "market_context": "IT"}'::jsonb
  ),
  (
    '40000000-0000-4000-8000-000000000003',
    '10000000-0000-4000-8000-000000000001',
    '00000000-0000-4000-8000-000000000003',
    '30000000-0000-4000-8000-000000000003',
    'seed_note',
    'Synthetic profile: Volkswagen Golf',
    'Synthetic seed note for a European compact hatchback with balanced motorway comfort, petrol efficiency, and broad parts availability.',
    NULL,
    NULL,
    '{"synthetic": true, "market_context": "EU"}'::jsonb
  ),
  (
    '40000000-0000-4000-8000-000000000004',
    '10000000-0000-4000-8000-000000000001',
    '00000000-0000-4000-8000-000000000004',
    '30000000-0000-4000-8000-000000000004',
    'seed_note',
    'Synthetic profile: Dacia Sandero',
    'Synthetic seed note for an affordable hatchback with petrol/LPG availability, simple maintenance, and strong value positioning.',
    NULL,
    NULL,
    '{"synthetic": true, "market_context": "IT"}'::jsonb
  ),
  (
    '40000000-0000-4000-8000-000000000005',
    '10000000-0000-4000-8000-000000000001',
    '00000000-0000-4000-8000-000000000005',
    '30000000-0000-4000-8000-000000000005',
    'seed_note',
    'Synthetic profile: Tesla Model 3',
    'Synthetic seed note for an electric sedan with WLTP range, zero tailpipe CO2, and charging-dependent ownership fit in Europe.',
    NULL,
    NULL,
    '{"synthetic": true, "market_context": "EU"}'::jsonb
  )
ON CONFLICT (id) DO UPDATE SET
  source_id = EXCLUDED.source_id,
  vehicle_id = EXCLUDED.vehicle_id,
  listing_id = EXCLUDED.listing_id,
  document_type = EXCLUDED.document_type,
  title = EXCLUDED.title,
  content = EXCLUDED.content,
  embedding = EXCLUDED.embedding,
  embedding_model = EXCLUDED.embedding_model,
  metadata = EXCLUDED.metadata;
