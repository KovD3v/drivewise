import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID, uuid5

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from psycopg.types.json import Jsonb


SCHEMA_VERSION = 1
KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SOURCE_NAMESPACE = UUID("c122e817-2f48-4ea9-8648-b115bc791fb5")
VEHICLE_NAMESPACE = UUID("e98062b5-c1e1-43bc-95d3-d5fb5ef042bc")
VARIANT_NAMESPACE = UUID("71b24cbd-74bb-4642-8a10-529085772138")
LISTING_NAMESPACE = UUID("a057c2aa-7b3f-4d87-91cb-b3e68318d9bf")
PROVENANCE_NAMESPACE = UUID("90eae936-2713-4238-b508-3189252f640e")
MAINTENANCE_ITEM_NAMESPACE = UUID("b4cbf797-413c-4ee5-b152-1e483fa73572")
SAFETY_RATING_NAMESPACE = UUID("ac53e762-849a-49fa-9ef1-3dc003379119")
FEATURE_NAMESPACE = UUID("422e3e4d-2895-49a5-9b3a-fc2e93c31e21")
MEDIA_ASSET_NAMESPACE = UUID("d18a36ee-6e46-4379-90d1-93cbb1ed30b9")
CatalogFuelType = Literal[
    "diesel",
    "electric",
    "full_hybrid_petrol",
    "hybrid_petrol",
    "mild_hybrid_petrol",
    "petrol",
    "petrol_lpg",
]
CatalogBodyStyle = Literal[
    "city_car",
    "small_hatchback",
    "hatchback",
    "crossover",
    "sedan",
    "wagon",
    "suv",
    "mpv",
    "van",
]
RankingPermission = Literal[
    "permitted",
    "not_permitted",
    "manual_validation_only",
]
VEHICLE_PROVENANCE_FIELDS = (
    "canonical_key",
    "model_family_key",
    "make",
    "model",
    "model_year",
    "market",
)
VARIANT_PROVENANCE_FIELDS = (
    "variant_key",
    "vehicle_key",
    "trim",
    "is_default",
    "body_style",
    "fuel_type",
    "list_price_eur",
    "drivetrain",
    "transmission",
    "engine",
    "horsepower",
    "battery_kwh",
    "energy_consumption_kwh_100km",
    "consumption_l_100km",
    "wltp_range_km",
    "co2_g_km",
    "euro_emission_standard",
    "seats",
    "cargo_volume_liters",
    "generation_name",
    "restyling_label",
    "category",
    "doors",
    "length_mm",
    "width_mm",
    "height_mm",
    "wheelbase_mm",
    "curb_weight_kg",
    "gross_weight_kg",
    "payload_kg",
    "engine_code",
    "displacement_cc",
    "cylinders",
    "power_kw",
    "torque_nm",
    "battery_usable_kwh",
    "transmission_type",
    "gear_count",
    "differential_type",
    "acceleration_0_100_s",
    "top_speed_kmh",
    "braking_100_0_m",
    "homologation_cycle",
)
PROFILE_COLLECTION_FIELDS = (
    "maintenance_schedule",
    "safety_ratings",
    "features",
    "media",
)


class CatalogValidationError(ValueError):
    pass


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRecord(StrictModel):
    source_key: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    source_type: Literal["manual_seed", "public_dataset", "curated_internal"]
    market: str = Field(default="IT", min_length=2, max_length=8)
    ranking_permission: RankingPermission
    url: str
    license: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("source_key")
    @classmethod
    def validate_source_key(cls, value: str) -> str:
        return _validate_key(value, "source_key")

    @field_validator("market")
    @classmethod
    def normalize_market(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return _validate_url(value)


class ProvenanceClaim(StrictModel):
    source_key: str = Field(min_length=1, max_length=120)
    source_url: str
    observed_at: datetime
    supported_metrics: list[str] = Field(min_length=1)

    @field_validator("source_key")
    @classmethod
    def validate_source_key(cls, value: str) -> str:
        return _validate_key(value, "source_key")

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        return _validate_url(value)

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value

    @field_validator("supported_metrics")
    @classmethod
    def require_unique_metrics(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("supported_metrics must not contain duplicates")
        return value


class ProvenancedRecord(StrictModel):
    source_key: str = Field(min_length=1, max_length=120)
    source_url: str
    observed_at: datetime

    @field_validator("source_key")
    @classmethod
    def validate_source_key(cls, value: str) -> str:
        return _validate_key(value, "source_key")

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        return _validate_url(value)

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value


class ChildSourceRecord(StrictModel):
    source_key: str = Field(min_length=1, max_length=160)
    source_url: str
    observed_at: datetime

    @field_validator("source_key")
    @classmethod
    def validate_source_key(cls, value: str) -> str:
        return _validate_key(value, "source_key")

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        url = _validate_url(value)
        if not url.startswith("https://"):
            raise ValueError("child source URL must use https")
        return url

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value


class MaintenanceRecord(ChildSourceRecord):
    operation_code: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=240)
    interval_km: int | None = Field(default=None, gt=0)
    interval_months: int | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_interval(self):
        if self.interval_km is None and self.interval_months is None:
            raise ValueError("maintenance item requires an interval")
        return self


class SafetyRatingRecord(ChildSourceRecord):
    assessment_system: str = Field(min_length=1, max_length=80)
    assessment_year: int = Field(ge=1990, le=2100)
    overall_stars: int | None = Field(default=None, ge=0, le=5)
    adult_occupant_percent: int | None = Field(default=None, ge=0, le=100)
    child_occupant_percent: int | None = Field(default=None, ge=0, le=100)
    vulnerable_road_users_percent: int | None = Field(default=None, ge=0, le=100)
    safety_assist_percent: int | None = Field(default=None, ge=0, le=100)


class FeatureRecord(ChildSourceRecord):
    feature_key: str = Field(min_length=1, max_length=160)
    category: Literal["adas", "safety", "technology", "comfort"]
    name: str = Field(min_length=1, max_length=240)
    availability: Literal["standard", "optional"]
    notes: str | None = Field(default=None, max_length=500)


class MediaRecord(ChildSourceRecord):
    asset_key: str = Field(min_length=1, max_length=160)
    asset_type: Literal["photo", "brochure", "manual"]
    title: str = Field(min_length=1, max_length=240)
    url: str
    mime_type: str | None = Field(default=None, max_length=120)
    locale: str | None = Field(default=None, max_length=20)

    @field_validator("url")
    @classmethod
    def require_https(cls, value: str) -> str:
        url = _validate_url(value)
        if not url.startswith("https://"):
            raise ValueError("media URL must use https")
        return url


class VehicleRecord(ProvenancedRecord):
    canonical_key: str = Field(min_length=1, max_length=200)
    model_family_key: str = Field(min_length=1, max_length=160)
    make: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=120)
    model_year: int = Field(ge=1980, le=2100)
    market: str = Field(default="IT", min_length=2, max_length=8)
    provenance_claims: list[ProvenanceClaim] = Field(default_factory=list)

    @field_validator("canonical_key", "model_family_key")
    @classmethod
    def validate_keys(cls, value: str, info) -> str:
        return _validate_key(value, info.field_name)

    @field_validator("market")
    @classmethod
    def normalize_market(cls, value: str) -> str:
        return value.strip().upper()


class VariantRecord(ProvenancedRecord):
    variant_key: str = Field(min_length=1, max_length=240)
    vehicle_key: str = Field(min_length=1, max_length=200)
    trim: str = Field(min_length=1, max_length=200)
    is_default: bool = False
    body_style: CatalogBodyStyle
    fuel_type: CatalogFuelType
    list_price_eur: float | None = Field(default=None, ge=0)
    drivetrain: str | None = Field(default=None, max_length=80)
    transmission: str | None = Field(default=None, max_length=120)
    engine: str | None = Field(default=None, max_length=200)
    horsepower: int | None = Field(default=None, gt=0)
    battery_kwh: float | None = Field(default=None, gt=0)
    energy_consumption_kwh_100km: float | None = Field(default=None, gt=0)
    consumption_l_100km: float | None = Field(default=None, gt=0)
    wltp_range_km: int | None = Field(default=None, gt=0)
    co2_g_km: int | None = Field(default=None, ge=0)
    euro_emission_standard: str | None = Field(default=None, max_length=80)
    seats: int = Field(gt=0, le=20)
    cargo_volume_liters: float = Field(ge=0)
    generation_name: str | None = Field(default=None, max_length=120)
    restyling_label: str | None = Field(default=None, max_length=120)
    category: str | None = Field(default=None, max_length=80)
    doors: int | None = Field(default=None, gt=0)
    length_mm: int | None = Field(default=None, gt=0)
    width_mm: int | None = Field(default=None, gt=0)
    height_mm: int | None = Field(default=None, gt=0)
    wheelbase_mm: int | None = Field(default=None, gt=0)
    curb_weight_kg: int | None = Field(default=None, gt=0)
    gross_weight_kg: int | None = Field(default=None, gt=0)
    payload_kg: int | None = Field(default=None, gt=0)
    engine_code: str | None = Field(default=None, max_length=120)
    displacement_cc: int | None = Field(default=None, gt=0)
    cylinders: int | None = Field(default=None, gt=0)
    power_kw: float | None = Field(default=None, gt=0)
    torque_nm: int | None = Field(default=None, gt=0)
    battery_usable_kwh: float | None = Field(default=None, gt=0)
    transmission_type: str | None = Field(default=None, max_length=80)
    gear_count: int | None = Field(default=None, gt=0)
    differential_type: str | None = Field(default=None, max_length=80)
    acceleration_0_100_s: float | None = Field(default=None, gt=0)
    top_speed_kmh: int | None = Field(default=None, gt=0)
    braking_100_0_m: float | None = Field(default=None, gt=0)
    homologation_cycle: str | None = Field(default=None, max_length=80)
    maintenance_schedule: list[MaintenanceRecord] = Field(default_factory=list)
    safety_ratings: list[SafetyRatingRecord] = Field(default_factory=list)
    features: list[FeatureRecord] = Field(default_factory=list)
    media: list[MediaRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance_claims: list[ProvenanceClaim] = Field(default_factory=list)

    @field_validator("variant_key", "vehicle_key")
    @classmethod
    def validate_keys(cls, value: str, info) -> str:
        return _validate_key(value, info.field_name)


class ListingRecord(ProvenancedRecord):
    listing_ref: str = Field(min_length=1, max_length=240)
    variant_key: str = Field(min_length=1, max_length=240)
    title: str = Field(min_length=1, max_length=300)
    price_eur: float = Field(ge=0)
    mileage: int | None = Field(default=None, ge=0)
    condition: Literal["new", "used", "certified"]
    location_region: str | None = Field(default=None, max_length=120)
    listed_at: date | None = None
    valid_until: datetime | None = None
    is_active: bool = True
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("variant_key")
    @classmethod
    def validate_variant_key(cls, value: str) -> str:
        return _validate_key(value, "variant_key")

    @field_validator("valid_until")
    @classmethod
    def require_valid_until_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("valid_until must include a timezone")
        return value


class CatalogPayload(StrictModel):
    schema_version: Literal[1]
    sources: list[SourceRecord] = Field(min_length=1)
    vehicles: list[VehicleRecord] = Field(min_length=1)
    variants: list[VariantRecord] = Field(min_length=1)
    listings: list[ListingRecord] = Field(default_factory=list)


@dataclass(frozen=True)
class CatalogSummary:
    sources: int
    vehicles: int
    variants: int
    listings: int


@dataclass
class ImportCounts:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    deactivated: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "inserted": self.inserted,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "deactivated": self.deactivated,
        }


@dataclass(frozen=True)
class CatalogImportResult:
    run_id: UUID
    dataset_hash: str
    status: Literal["completed", "unchanged"]
    counts: ImportCounts


def load_catalog(path: str | Path) -> CatalogPayload:
    catalog_path = Path(path)
    if not catalog_path.is_file():
        raise CatalogValidationError(f"Catalog path is not a file: {catalog_path}")
    try:
        raw_payload = json.loads(catalog_path.read_text())
    except json.JSONDecodeError as error:
        raise CatalogValidationError(
            f"Catalog JSON is invalid at line {error.lineno}, column {error.colno}."
        ) from error

    try:
        payload = CatalogPayload.model_validate(raw_payload)
    except ValidationError as error:
        raise CatalogValidationError(_format_validation_error(error)) from error

    validate_catalog(payload)
    return payload


def validate_catalog(payload: CatalogPayload) -> CatalogSummary:
    source_keys = _require_unique(
        "source_key", [source.source_key for source in payload.sources]
    )
    _require_unique("source name", [source.name for source in payload.sources])
    vehicle_keys = _require_unique(
        "canonical_key", [vehicle.canonical_key for vehicle in payload.vehicles]
    )
    _require_unique(
        "model identity",
        [
            f"{vehicle.market}:{vehicle.make}:{vehicle.model}:{vehicle.model_year}".lower()
            for vehicle in payload.vehicles
        ],
    )
    variant_keys = _require_unique(
        "variant_key", [variant.variant_key for variant in payload.variants]
    )
    _require_unique(
        "source/listing_ref",
        [f"{listing.source_key}:{listing.listing_ref}" for listing in payload.listings],
    )

    for record_type, records in (
        ("vehicle", payload.vehicles),
        ("variant", payload.variants),
        ("listing", payload.listings),
    ):
        for record in records:
            if record.source_key not in source_keys:
                raise CatalogValidationError(
                    f"{record_type} references unknown source_key: {record.source_key}"
                )

    for record_type, records, fields in (
        ("vehicle", payload.vehicles, VEHICLE_PROVENANCE_FIELDS),
        ("variant", payload.variants, VARIANT_PROVENANCE_FIELDS),
    ):
        for record in records:
            _validate_provenance_claims(
                record_type,
                record,
                fields,
                source_keys,
            )

    variants_by_vehicle: dict[str, list[VariantRecord]] = {
        vehicle_key: [] for vehicle_key in vehicle_keys
    }
    for variant in payload.variants:
        if variant.vehicle_key not in vehicle_keys:
            raise CatalogValidationError(
                f"variant references unknown vehicle_key: {variant.vehicle_key}"
            )
        variants_by_vehicle[variant.vehicle_key].append(variant)

    for variant in payload.variants:
        child_groups = [
            ("maintenance operation_code", variant.maintenance_schedule, "operation_code"),
            ("safety assessment", variant.safety_ratings, None),
            ("feature_key", variant.features, "feature_key"),
            ("media asset_key", variant.media, "asset_key"),
        ]
        for label, records, key_name in child_groups:
            for record in records:
                if record.source_key not in source_keys:
                    raise CatalogValidationError(
                        f"{label} references unknown source_key: {record.source_key}"
                    )
            if key_name is not None:
                _require_unique(
                    f"{variant.variant_key} {label}",
                    [getattr(record, key_name) for record in records],
                )
        _require_unique(
            f"{variant.variant_key} safety assessment",
            [
                f"{record.assessment_system}:{record.assessment_year}"
                for record in variant.safety_ratings
            ],
        )

    for vehicle_key, variants in variants_by_vehicle.items():
        default_count = sum(variant.is_default for variant in variants)
        if default_count != 1:
            raise CatalogValidationError(
                f"vehicle {vehicle_key} must have exactly one default variant; "
                f"found {default_count}"
            )

    for listing in payload.listings:
        if listing.variant_key not in variant_keys:
            raise CatalogValidationError(
                f"listing references unknown variant_key: {listing.variant_key}"
            )
        if listing.condition in {"used", "certified"} and listing.mileage is None:
            raise CatalogValidationError(
                f"{listing.condition} listing {listing.listing_ref} requires mileage"
            )
        if listing.valid_until is not None and listing.valid_until < listing.observed_at:
            raise CatalogValidationError(
                f"listing {listing.listing_ref} valid_until precedes observed_at"
            )

    return CatalogSummary(
        sources=len(payload.sources),
        vehicles=len(payload.vehicles),
        variants=len(payload.variants),
        listings=len(payload.listings),
    )


def compute_catalog_hash(payload: CatalogPayload) -> str:
    return _content_hash(
        {
            "payload": payload.model_dump(mode="json"),
            "variant_profile_collection_presence": {
                variant.variant_key: _profile_collection_presence(variant)
                for variant in payload.variants
            },
        }
    )


def import_catalog(
    conn,
    payload: CatalogPayload,
    *,
    file_name: str,
) -> CatalogImportResult:
    summary = validate_catalog(payload)
    dataset_hash = compute_catalog_hash(payload)
    existing_run = conn.execute(
        """
        SELECT id
        FROM import_runs
        WHERE dataset_hash = %s AND status = 'completed'
        ORDER BY completed_at DESC
        LIMIT 1
        """,
        (dataset_hash,),
    ).fetchone()
    if existing_run is not None:
        return CatalogImportResult(
            run_id=_row_value(existing_run, "id"),
            dataset_hash=dataset_hash,
            status="unchanged",
            counts=ImportCounts(
                unchanged=summary.vehicles + summary.variants + summary.listings
            ),
        )

    run_id = uuid5(LISTING_NAMESPACE, f"import:{dataset_hash}")
    input_counts = {
        "sources": summary.sources,
        "vehicles": summary.vehicles,
        "variants": summary.variants,
        "listings": summary.listings,
    }
    conn.execute(
        """
        INSERT INTO import_runs (
          id, schema_version, dataset_hash, file_name, status, record_counts
        )
        VALUES (%s, %s, %s, %s, 'running', %s)
        ON CONFLICT (id) DO UPDATE SET
          file_name = EXCLUDED.file_name,
          status = 'running',
          record_counts = EXCLUDED.record_counts,
          error_message = NULL,
          started_at = now(),
          completed_at = NULL
        """,
        (
            run_id,
            SCHEMA_VERSION,
            dataset_hash,
            Path(file_name).name,
            Jsonb(input_counts),
        ),
    )
    _commit_if_needed(conn)

    counts = ImportCounts()
    try:
        with conn.transaction():
            source_ids = _upsert_sources(conn, payload.sources)
            vehicle_ids = _upsert_vehicles(
                conn,
                payload.vehicles,
                payload.variants,
                source_ids,
                run_id,
                counts,
            )
            variant_ids = _upsert_variants(
                conn,
                payload.variants,
                vehicle_ids,
                source_ids,
                run_id,
                counts,
            )
            _sync_vehicle_mirrors(conn, payload.variants, vehicle_ids, variant_ids)
            _upsert_listings(
                conn,
                payload.listings,
                variant_ids,
                vehicle_ids,
                payload.variants,
                source_ids,
                run_id,
                counts,
            )
            completed_counts = {**input_counts, **counts.as_dict()}
            conn.execute(
                """
                UPDATE import_runs
                SET status = 'completed',
                    record_counts = %s,
                    completed_at = now()
                WHERE id = %s
                """,
                (Jsonb(completed_counts), run_id),
            )
    except Exception as error:
        _rollback_if_needed(conn)
        conn.execute(
            """
            UPDATE import_runs
            SET status = 'failed', error_message = %s, completed_at = now()
            WHERE id = %s
            """,
            (f"{error.__class__.__name__}: {str(error)[:400]}", run_id),
        )
        _commit_if_needed(conn)
        raise

    _commit_if_needed(conn)
    return CatalogImportResult(
        run_id=run_id,
        dataset_hash=dataset_hash,
        status="completed",
        counts=counts,
    )


def _upsert_sources(conn, sources: list[SourceRecord]) -> dict[str, UUID]:
    source_ids: dict[str, UUID] = {}
    for source in sources:
        source_id = uuid5(SOURCE_NAMESPACE, source.source_key)
        row = conn.execute(
            """
            INSERT INTO sources (
              id, source_key, name, source_type, market, ranking_permission,
              url, license, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_key) DO UPDATE SET
              name = EXCLUDED.name,
              source_type = EXCLUDED.source_type,
              market = EXCLUDED.market,
              ranking_permission = EXCLUDED.ranking_permission,
              url = EXCLUDED.url,
              license = EXCLUDED.license,
              notes = EXCLUDED.notes
            RETURNING id
            """,
            (
                source_id,
                source.source_key,
                source.name,
                source.source_type,
                source.market,
                source.ranking_permission,
                source.url,
                source.license,
                source.notes,
            ),
        ).fetchone()
        source_ids[source.source_key] = _row_value(row, "id")
    return source_ids


def _upsert_vehicles(
    conn,
    vehicles: list[VehicleRecord],
    variants: list[VariantRecord],
    source_ids: dict[str, UUID],
    run_id: UUID,
    counts: ImportCounts,
) -> dict[str, UUID]:
    default_variants = {
        variant.vehicle_key: variant for variant in variants if variant.is_default
    }
    vehicle_ids: dict[str, UUID] = {}
    for vehicle in vehicles:
        default_variant = default_variants[vehicle.canonical_key]
        content_hash = _content_hash(vehicle.model_dump(mode="json"))
        existing = conn.execute(
            """
            SELECT
              v.id,
              current_provenance.content_hash,
              current_provenance.record_observed_at
            FROM vehicles v
            LEFT JOIN LATERAL (
              SELECT content_hash, record_observed_at
              FROM vehicle_provenance
              WHERE vehicle_id = v.id AND is_current
              ORDER BY record_observed_at DESC, id
              LIMIT 1
            ) AS current_provenance ON true
            WHERE v.canonical_key = %s
            """,
            (vehicle.canonical_key,),
        ).fetchone()
        _reject_stale_record(
            "vehicle",
            vehicle.canonical_key,
            vehicle.observed_at,
            existing,
            "record_observed_at",
        )
        vehicle_id = (
            _row_value(existing, "id")
            if existing is not None
            else uuid5(VEHICLE_NAMESPACE, vehicle.canonical_key)
        )
        _track_status(existing, content_hash, counts)
        row = conn.execute(
            """
            INSERT INTO vehicles (
              id, canonical_key, model_family_key, make, model, model_year,
              body_style, fuel_type, market, base_price_eur
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (canonical_key) DO UPDATE SET
              model_family_key = EXCLUDED.model_family_key,
              make = EXCLUDED.make,
              model = EXCLUDED.model,
              model_year = EXCLUDED.model_year,
              body_style = EXCLUDED.body_style,
              fuel_type = EXCLUDED.fuel_type,
              market = EXCLUDED.market,
              base_price_eur = EXCLUDED.base_price_eur,
              updated_at = now()
            RETURNING id
            """,
            (
                vehicle_id,
                vehicle.canonical_key,
                vehicle.model_family_key,
                vehicle.make,
                vehicle.model,
                vehicle.model_year,
                default_variant.body_style,
                default_variant.fuel_type,
                vehicle.market,
                default_variant.list_price_eur,
            ),
        ).fetchone()
        vehicle_id = _row_value(row, "id")
        vehicle_ids[vehicle.canonical_key] = vehicle_id
        _replace_provenance_set(
            conn,
            table="vehicle_provenance",
            entity_column="vehicle_id",
            entity_id=vehicle_id,
            content_hash=content_hash,
            import_run_id=run_id,
            record=vehicle,
            fields=VEHICLE_PROVENANCE_FIELDS,
            source_ids=source_ids,
        )
    return vehicle_ids


def _upsert_variants(
    conn,
    variants: list[VariantRecord],
    vehicle_ids: dict[str, UUID],
    source_ids: dict[str, UUID],
    run_id: UUID,
    counts: ImportCounts,
) -> dict[str, UUID]:
    for vehicle_id in set(vehicle_ids.values()):
        conn.execute(
            "UPDATE vehicle_specs SET is_default = false WHERE vehicle_id = %s",
            (vehicle_id,),
        )

    variant_ids: dict[str, UUID] = {}
    for variant in variants:
        content_hash = _content_hash(
            {
                "variant": variant.model_dump(mode="json"),
                "profile_collection_presence": _profile_collection_presence(variant),
            }
        )
        existing = conn.execute(
            """
            SELECT
              spec.id,
              current_provenance.content_hash,
              current_provenance.record_observed_at
            FROM vehicle_specs spec
            LEFT JOIN LATERAL (
              SELECT content_hash, record_observed_at
              FROM vehicle_spec_provenance
              WHERE spec_id = spec.id AND is_current
              ORDER BY record_observed_at DESC, id
              LIMIT 1
            ) AS current_provenance ON true
            WHERE spec.variant_key = %s
            """,
            (variant.variant_key,),
        ).fetchone()
        _reject_stale_record(
            "variant",
            variant.variant_key,
            variant.observed_at,
            existing,
            "record_observed_at",
        )
        variant_id = (
            _row_value(existing, "id")
            if existing is not None
            else uuid5(VARIANT_NAMESPACE, variant.variant_key)
        )
        _track_status(existing, content_hash, counts)
        row = conn.execute(
            """
            INSERT INTO vehicle_specs (
              id, vehicle_id, variant_key, is_default, trim, body_style,
              fuel_type, list_price_eur, drivetrain, transmission, engine,
              horsepower, battery_kwh, energy_consumption_kwh_100km,
              consumption_l_100km, wltp_range_km, co2_g_km,
              euro_emission_standard, seats, cargo_volume_liters,
              generation_name, restyling_label, category, doors, length_mm,
              width_mm, height_mm, wheelbase_mm, curb_weight_kg,
              gross_weight_kg, payload_kg, engine_code, displacement_cc,
              cylinders, power_kw, torque_nm, battery_usable_kwh,
              transmission_type, gear_count, differential_type,
              acceleration_0_100_s, top_speed_kmh, braking_100_0_m,
              homologation_cycle, metadata
            )
            VALUES (
              %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (variant_key) DO UPDATE SET
              vehicle_id = EXCLUDED.vehicle_id,
              is_default = EXCLUDED.is_default,
              trim = EXCLUDED.trim,
              body_style = EXCLUDED.body_style,
              fuel_type = EXCLUDED.fuel_type,
              list_price_eur = EXCLUDED.list_price_eur,
              drivetrain = EXCLUDED.drivetrain,
              transmission = EXCLUDED.transmission,
              engine = EXCLUDED.engine,
              horsepower = EXCLUDED.horsepower,
              battery_kwh = EXCLUDED.battery_kwh,
              energy_consumption_kwh_100km = EXCLUDED.energy_consumption_kwh_100km,
              consumption_l_100km = EXCLUDED.consumption_l_100km,
              wltp_range_km = EXCLUDED.wltp_range_km,
              co2_g_km = EXCLUDED.co2_g_km,
              euro_emission_standard = EXCLUDED.euro_emission_standard,
              seats = EXCLUDED.seats,
              cargo_volume_liters = EXCLUDED.cargo_volume_liters,
              generation_name = EXCLUDED.generation_name,
              restyling_label = EXCLUDED.restyling_label,
              category = EXCLUDED.category,
              doors = EXCLUDED.doors,
              length_mm = EXCLUDED.length_mm,
              width_mm = EXCLUDED.width_mm,
              height_mm = EXCLUDED.height_mm,
              wheelbase_mm = EXCLUDED.wheelbase_mm,
              curb_weight_kg = EXCLUDED.curb_weight_kg,
              gross_weight_kg = EXCLUDED.gross_weight_kg,
              payload_kg = EXCLUDED.payload_kg,
              engine_code = EXCLUDED.engine_code,
              displacement_cc = EXCLUDED.displacement_cc,
              cylinders = EXCLUDED.cylinders,
              power_kw = EXCLUDED.power_kw,
              torque_nm = EXCLUDED.torque_nm,
              battery_usable_kwh = EXCLUDED.battery_usable_kwh,
              transmission_type = EXCLUDED.transmission_type,
              gear_count = EXCLUDED.gear_count,
              differential_type = EXCLUDED.differential_type,
              acceleration_0_100_s = EXCLUDED.acceleration_0_100_s,
              top_speed_kmh = EXCLUDED.top_speed_kmh,
              braking_100_0_m = EXCLUDED.braking_100_0_m,
              homologation_cycle = EXCLUDED.homologation_cycle,
              metadata = EXCLUDED.metadata,
              updated_at = now()
            RETURNING id
            """,
            (
                variant_id,
                vehicle_ids[variant.vehicle_key],
                variant.variant_key,
                variant.is_default,
                variant.trim,
                variant.body_style,
                variant.fuel_type,
                variant.list_price_eur,
                variant.drivetrain,
                variant.transmission,
                variant.engine,
                variant.horsepower,
                variant.battery_kwh,
                variant.energy_consumption_kwh_100km,
                variant.consumption_l_100km,
                variant.wltp_range_km,
                variant.co2_g_km,
                variant.euro_emission_standard,
                variant.seats,
                variant.cargo_volume_liters,
                variant.generation_name,
                variant.restyling_label,
                variant.category,
                variant.doors,
                variant.length_mm,
                variant.width_mm,
                variant.height_mm,
                variant.wheelbase_mm,
                variant.curb_weight_kg,
                variant.gross_weight_kg,
                variant.payload_kg,
                variant.engine_code,
                variant.displacement_cc,
                variant.cylinders,
                variant.power_kw,
                variant.torque_nm,
                variant.battery_usable_kwh,
                variant.transmission_type,
                variant.gear_count,
                variant.differential_type,
                variant.acceleration_0_100_s,
                variant.top_speed_kmh,
                variant.braking_100_0_m,
                variant.homologation_cycle,
                Jsonb(variant.metadata),
            ),
        ).fetchone()
        variant_id = _row_value(row, "id")
        variant_ids[variant.variant_key] = variant_id
        _sync_variant_profile_children(conn, variant, variant_id, source_ids)
        _replace_provenance_set(
            conn,
            table="vehicle_spec_provenance",
            entity_column="spec_id",
            entity_id=variant_id,
            content_hash=content_hash,
            import_run_id=run_id,
            record=variant,
            fields=VARIANT_PROVENANCE_FIELDS,
            source_ids=source_ids,
        )
    return variant_ids


def _sync_variant_profile_children(
    conn,
    variant: VariantRecord,
    spec_id: UUID,
    source_ids: dict[str, UUID],
) -> None:
    configurations = (
        (
            "maintenance_schedule",
            "vehicle_maintenance_items",
            variant.maintenance_schedule,
            lambda record: record.operation_code,
            _upsert_maintenance_item,
        ),
        (
            "safety_ratings",
            "vehicle_safety_ratings",
            variant.safety_ratings,
            lambda record: f"{record.assessment_system}:{record.assessment_year}",
            _upsert_safety_rating,
        ),
        (
            "features",
            "vehicle_features",
            variant.features,
            lambda record: record.feature_key,
            _upsert_feature,
        ),
        (
            "media",
            "vehicle_media_assets",
            variant.media,
            lambda record: record.asset_key,
            _upsert_media_asset,
        ),
    )
    for field_name, table, records, _key_function, upsert in configurations:
        if field_name not in variant.model_fields_set:
            continue
        retained_ids = [
            upsert(conn, spec_id, record, source_ids[record.source_key])
            for record in records
        ]
        if retained_ids:
            conn.execute(
                f"DELETE FROM {table} WHERE spec_id = %s AND id <> ALL(%s)",
                (spec_id, retained_ids),
            )
        else:
            conn.execute(f"DELETE FROM {table} WHERE spec_id = %s", (spec_id,))


def _upsert_maintenance_item(
    conn,
    spec_id: UUID,
    record: MaintenanceRecord,
    source_id: UUID,
) -> UUID:
    item_id = uuid5(
        MAINTENANCE_ITEM_NAMESPACE,
        f"{spec_id}:{record.operation_code}",
    )
    conn.execute(
        """
        INSERT INTO vehicle_maintenance_items (
          id, spec_id, operation_code, title, interval_km, interval_months,
          notes, source_id, source_url, observed_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (spec_id, operation_code) DO UPDATE SET
          title = EXCLUDED.title,
          interval_km = EXCLUDED.interval_km,
          interval_months = EXCLUDED.interval_months,
          notes = EXCLUDED.notes,
          source_id = EXCLUDED.source_id,
          source_url = EXCLUDED.source_url,
          observed_at = EXCLUDED.observed_at,
          updated_at = now()
        """,
        (
            item_id,
            spec_id,
            record.operation_code,
            record.title,
            record.interval_km,
            record.interval_months,
            record.notes,
            source_id,
            record.source_url,
            record.observed_at,
        ),
    )
    return item_id


def _upsert_safety_rating(
    conn,
    spec_id: UUID,
    record: SafetyRatingRecord,
    source_id: UUID,
) -> UUID:
    rating_id = uuid5(
        SAFETY_RATING_NAMESPACE,
        f"{spec_id}:{record.assessment_system}:{record.assessment_year}",
    )
    conn.execute(
        """
        INSERT INTO vehicle_safety_ratings (
          id, spec_id, assessment_system, assessment_year, overall_stars,
          adult_occupant_percent, child_occupant_percent,
          vulnerable_road_users_percent, safety_assist_percent, source_id,
          source_url, observed_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (spec_id, assessment_system, assessment_year) DO UPDATE SET
          overall_stars = EXCLUDED.overall_stars,
          adult_occupant_percent = EXCLUDED.adult_occupant_percent,
          child_occupant_percent = EXCLUDED.child_occupant_percent,
          vulnerable_road_users_percent = EXCLUDED.vulnerable_road_users_percent,
          safety_assist_percent = EXCLUDED.safety_assist_percent,
          source_id = EXCLUDED.source_id,
          source_url = EXCLUDED.source_url,
          observed_at = EXCLUDED.observed_at,
          updated_at = now()
        """,
        (
            rating_id,
            spec_id,
            record.assessment_system,
            record.assessment_year,
            record.overall_stars,
            record.adult_occupant_percent,
            record.child_occupant_percent,
            record.vulnerable_road_users_percent,
            record.safety_assist_percent,
            source_id,
            record.source_url,
            record.observed_at,
        ),
    )
    return rating_id


def _upsert_feature(
    conn,
    spec_id: UUID,
    record: FeatureRecord,
    source_id: UUID,
) -> UUID:
    feature_id = uuid5(FEATURE_NAMESPACE, f"{spec_id}:{record.feature_key}")
    conn.execute(
        """
        INSERT INTO vehicle_features (
          id, spec_id, feature_key, category, name, availability, notes,
          source_id, source_url, observed_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (spec_id, feature_key) DO UPDATE SET
          category = EXCLUDED.category,
          name = EXCLUDED.name,
          availability = EXCLUDED.availability,
          notes = EXCLUDED.notes,
          source_id = EXCLUDED.source_id,
          source_url = EXCLUDED.source_url,
          observed_at = EXCLUDED.observed_at,
          updated_at = now()
        """,
        (
            feature_id,
            spec_id,
            record.feature_key,
            record.category,
            record.name,
            record.availability,
            record.notes,
            source_id,
            record.source_url,
            record.observed_at,
        ),
    )
    return feature_id


def _upsert_media_asset(
    conn,
    spec_id: UUID,
    record: MediaRecord,
    source_id: UUID,
) -> UUID:
    asset_id = uuid5(MEDIA_ASSET_NAMESPACE, f"{spec_id}:{record.asset_key}")
    conn.execute(
        """
        INSERT INTO vehicle_media_assets (
          id, spec_id, asset_key, asset_type, title, url, mime_type, locale,
          source_id, source_url, observed_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (spec_id, asset_key) DO UPDATE SET
          asset_type = EXCLUDED.asset_type,
          title = EXCLUDED.title,
          url = EXCLUDED.url,
          mime_type = EXCLUDED.mime_type,
          locale = EXCLUDED.locale,
          source_id = EXCLUDED.source_id,
          source_url = EXCLUDED.source_url,
          observed_at = EXCLUDED.observed_at,
          updated_at = now()
        """,
        (
            asset_id,
            spec_id,
            record.asset_key,
            record.asset_type,
            record.title,
            record.url,
            record.mime_type,
            record.locale,
            source_id,
            record.source_url,
            record.observed_at,
        ),
    )
    return asset_id


def _sync_vehicle_mirrors(
    conn,
    variants: list[VariantRecord],
    vehicle_ids: dict[str, UUID],
    _variant_ids: dict[str, UUID],
) -> None:
    for variant in variants:
        if not variant.is_default:
            continue
        conn.execute(
            """
            UPDATE vehicles
            SET body_style = %s,
                fuel_type = %s,
                base_price_eur = %s,
                updated_at = now()
            WHERE id = %s
            """,
            (
                variant.body_style,
                variant.fuel_type,
                variant.list_price_eur,
                vehicle_ids[variant.vehicle_key],
            ),
        )


def _upsert_listings(
    conn,
    listings: list[ListingRecord],
    variant_ids: dict[str, UUID],
    vehicle_ids: dict[str, UUID],
    variants: list[VariantRecord],
    source_ids: dict[str, UUID],
    run_id: UUID,
    counts: ImportCounts,
) -> None:
    vehicle_key_by_variant = {
        variant.variant_key: variant.vehicle_key for variant in variants
    }
    for listing in listings:
        source_id = source_ids[listing.source_key]
        content_hash = _content_hash(listing.model_dump(mode="json"))
        existing = conn.execute(
            """
            SELECT id, content_hash, is_active, last_seen_at
            FROM listings
            WHERE source_id = %s AND listing_ref = %s
            """,
            (source_id, listing.listing_ref),
        ).fetchone()
        _reject_stale_record(
            "listing",
            f"{listing.source_key}:{listing.listing_ref}",
            listing.observed_at,
            existing,
            "last_seen_at",
        )
        listing_id = (
            _row_value(existing, "id")
            if existing is not None
            else uuid5(LISTING_NAMESPACE, f"{listing.source_key}:{listing.listing_ref}")
        )
        _track_status(existing, content_hash, counts)
        if (
            existing is not None
            and _row_value(existing, "is_active")
            and not listing.is_active
        ):
            counts.deactivated += 1
        conn.execute(
            """
            INSERT INTO listings (
              id, vehicle_id, spec_id, source_id, listing_ref, title, price_eur,
              mileage, condition, location_region, listed_at, source_url,
              first_seen_at, last_seen_at, valid_until, is_active, content_hash,
              import_run_id, raw_payload
            )
            VALUES (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (source_id, listing_ref) DO UPDATE SET
              vehicle_id = EXCLUDED.vehicle_id,
              spec_id = EXCLUDED.spec_id,
              title = EXCLUDED.title,
              price_eur = EXCLUDED.price_eur,
              mileage = EXCLUDED.mileage,
              condition = EXCLUDED.condition,
              location_region = EXCLUDED.location_region,
              listed_at = EXCLUDED.listed_at,
              source_url = EXCLUDED.source_url,
              first_seen_at = LEAST(listings.first_seen_at, EXCLUDED.first_seen_at),
              last_seen_at = GREATEST(listings.last_seen_at, EXCLUDED.last_seen_at),
              valid_until = EXCLUDED.valid_until,
              is_active = EXCLUDED.is_active,
              content_hash = EXCLUDED.content_hash,
              import_run_id = EXCLUDED.import_run_id,
              raw_payload = EXCLUDED.raw_payload,
              updated_at = now()
            """,
            (
                listing_id,
                vehicle_ids[vehicle_key_by_variant[listing.variant_key]],
                variant_ids[listing.variant_key],
                source_id,
                listing.listing_ref,
                listing.title,
                listing.price_eur,
                listing.mileage,
                listing.condition,
                listing.location_region,
                listing.listed_at,
                listing.source_url,
                listing.observed_at,
                listing.observed_at,
                listing.valid_until,
                listing.is_active,
                content_hash,
                run_id,
                Jsonb(listing.raw_payload),
            ),
        )


def _replace_provenance_set(
    conn,
    *,
    table: Literal["vehicle_provenance", "vehicle_spec_provenance"],
    entity_column: Literal["vehicle_id", "spec_id"],
    entity_id: UUID,
    content_hash: str,
    import_run_id: UUID,
    record: VehicleRecord | VariantRecord,
    fields: tuple[str, ...],
    source_ids: dict[str, UUID],
) -> None:
    conn.execute(
        f"""
        UPDATE {table}
        SET is_current = false, updated_at = now()
        WHERE {entity_column} = %s AND is_current
        """,
        (entity_id,),
    )
    for claim in _provenance_claims(record, fields):
        _upsert_provenance(
            conn,
            table=table,
            entity_column=entity_column,
            entity_id=entity_id,
            source_id=source_ids[claim.source_key],
            source_url=claim.source_url,
            observed_at=claim.observed_at,
            record_observed_at=record.observed_at,
            content_hash=content_hash,
            import_run_id=import_run_id,
            supported_metrics=claim.supported_metrics,
        )


def _upsert_provenance(
    conn,
    *,
    table: Literal["vehicle_provenance", "vehicle_spec_provenance"],
    entity_column: Literal["vehicle_id", "spec_id"],
    entity_id: UUID,
    source_id: UUID,
    source_url: str,
    observed_at: datetime,
    record_observed_at: datetime,
    content_hash: str,
    import_run_id: UUID,
    supported_metrics: list[str],
) -> None:
    provenance_id = uuid5(
        PROVENANCE_NAMESPACE,
        f"{table}:{entity_id}:{source_id}",
    )
    conn.execute(
        f"""
        INSERT INTO {table} (
          id, {entity_column}, source_id, source_url, observed_at,
          record_observed_at, content_hash, import_run_id, is_current, metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true, %s)
        ON CONFLICT ({entity_column}, source_id) DO UPDATE SET
          source_url = EXCLUDED.source_url,
          observed_at = EXCLUDED.observed_at,
          record_observed_at = EXCLUDED.record_observed_at,
          content_hash = EXCLUDED.content_hash,
          import_run_id = EXCLUDED.import_run_id,
          is_current = true,
          metadata = EXCLUDED.metadata,
          updated_at = now()
        """,
        (
            provenance_id,
            entity_id,
            source_id,
            source_url,
            observed_at,
            record_observed_at,
            content_hash,
            import_run_id,
            Jsonb(
                {
                    "schema_version": SCHEMA_VERSION,
                    "supported_metrics": supported_metrics,
                }
            ),
        ),
    )


def _track_status(existing: Any, content_hash: str, counts: ImportCounts) -> None:
    if existing is None:
        counts.inserted += 1
    elif _row_value(existing, "content_hash") == content_hash:
        counts.unchanged += 1
    else:
        counts.updated += 1


def _reject_stale_record(
    record_type: str,
    record_key: str,
    incoming_observed_at: datetime,
    existing: Any,
    existing_observed_key: str,
) -> None:
    if existing is None:
        return
    current_observed_at = _row_value(existing, existing_observed_key)
    if (
        current_observed_at is not None
        and incoming_observed_at < current_observed_at
    ):
        raise CatalogValidationError(
            f"{record_type} {record_key} observed_at {incoming_observed_at.isoformat()} "
            f"is older than current {current_observed_at.isoformat()}"
        )


def _supported_metrics(record: BaseModel, fields: tuple[str, ...]) -> list[str]:
    return [field for field in fields if getattr(record, field) is not None]


def _provenance_claims(
    record: VehicleRecord | VariantRecord,
    fields: tuple[str, ...],
) -> list[ProvenanceClaim]:
    if record.provenance_claims:
        return record.provenance_claims
    return [
        ProvenanceClaim(
            source_key=record.source_key,
            source_url=record.source_url,
            observed_at=record.observed_at,
            supported_metrics=_supported_metrics(record, fields),
        )
    ]


def _validate_provenance_claims(
    record_type: str,
    record: VehicleRecord | VariantRecord,
    fields: tuple[str, ...],
    source_keys: set[str],
) -> None:
    claims = _provenance_claims(record, fields)
    claim_source_keys = [claim.source_key for claim in claims]
    _require_unique(f"{record_type} provenance source", claim_source_keys)
    claimed_metrics: set[str] = set()
    allowed_metrics = set(fields)
    for claim in claims:
        if claim.source_key not in source_keys:
            raise CatalogValidationError(
                f"{record_type} provenance references unknown source_key: "
                f"{claim.source_key}"
            )
        for metric in claim.supported_metrics:
            if metric not in allowed_metrics:
                raise CatalogValidationError(
                    f"{record_type} provenance contains unsupported metric: {metric}"
                )
            if getattr(record, metric) is None:
                raise CatalogValidationError(
                    f"{record_type} provenance claims null metric: {metric}"
                )
            if metric in claimed_metrics:
                raise CatalogValidationError(
                    f"{record_type} provenance metric has multiple current owners: "
                    f"{metric}"
                )
            claimed_metrics.add(metric)


def _content_hash(value: Any) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=_json_default,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _profile_collection_presence(variant: VariantRecord) -> dict[str, bool]:
    return {
        field_name: field_name in variant.model_fields_set
        for field_name in PROFILE_COLLECTION_FIELDS
    }


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime, UUID)):
        return value.isoformat() if not isinstance(value, UUID) else str(value)
    raise TypeError(f"Unsupported catalog value: {type(value).__name__}")


def _validate_key(value: str, field_name: str) -> str:
    normalized = value.strip().lower()
    if not KEY_PATTERN.fullmatch(normalized):
        raise ValueError(
            f"{field_name} must contain only lowercase letters, digits, '.', '_', or '-'"
        )
    return normalized


def _validate_url(value: str) -> str:
    normalized = value.strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must be an absolute http(s) URL")
    return normalized


def _require_unique(label: str, values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicate: str | None = None
    for value in values:
        if value in seen:
            duplicate = value
            break
        seen.add(value)
    if duplicate is not None:
        raise CatalogValidationError(f"duplicate {label}: {duplicate}")
    return seen


def _format_validation_error(error: ValidationError) -> str:
    first = error.errors()[0]
    location = ".".join(str(part) for part in first["loc"])
    return f"Catalog validation failed at {location}: {first['msg']}"


def _row_value(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row[key]
    return getattr(row, key)


def _commit_if_needed(conn) -> None:
    if not getattr(conn, "autocommit", False):
        conn.commit()


def _rollback_if_needed(conn) -> None:
    if not getattr(conn, "autocommit", False):
        conn.rollback()
