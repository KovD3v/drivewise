"""F-16 bounds, F-26 candidate snapshot and Model Analysis parity."""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.dependencies import get_advisor_repository, get_vehicles_repository
from app.main import app
from app.repositories.advisor import AdvisorRepository
from app.schemas.advisor import AdvisorRecommendationRequest, ModelAnalysisRequest
from app.schemas.vehicles import VehicleResolveResponse
from app.services.advisor.model_analysis import build_model_analysis


VEHICLE_ID = UUID("00000000-0000-4000-8000-000000000101")
OTHER_VEHICLE_ID = UUID("00000000-0000-4000-8000-000000000102")
DEFAULT_SPEC_ID = UUID("20000000-0000-4000-8000-000000000101")
SECOND_SPEC_ID = UUID("20000000-0000-4000-8000-000000000102")
OTHER_SPEC_ID = UUID("20000000-0000-4000-8000-000000000103")
HUGE = "1" + "0" * 400


class RecordingResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def fetchall(self):
        return self.rows


class RecordingConnection:
    def __init__(self, rows=None) -> None:
        self.calls = []
        self.rows = rows or []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return RecordingResult(self.rows)


# --- F-26: one snapshot for offers and list prices -------------------------------


def test_offer_and_list_price_branches_share_one_statement():
    conn = RecordingConnection()

    assert AdvisorRepository(conn).list_candidates() == []

    assert len(conn.calls) == 1
    sql, params = conn.calls[0]
    assert len(params) == 4
    offers, list_prices = sql.split("UNION ALL", 1)
    assert "FROM listings AS l" in offers
    assert "'offer' AS candidate_price_basis" in offers
    assert "'list_price' AS candidate_price_basis" in list_prices
    assert "s.catalog_version = 2" in list_prices
    # The list-price branch asks for "no eligible offer" inside the same statement.
    assert "AND NOT EXISTS" in list_prices
    assert sql.rstrip().endswith("sort_id")


def test_rows_are_mapped_by_their_price_basis():
    shared = _candidate_row()
    offer_row = {**shared, "candidate_price_basis": "offer"}
    list_price_row = {
        **shared,
        **dict.fromkeys(
            (
                "listing_id", "source_id", "listing_ref", "title", "price_eur",
                "mileage", "condition", "location_region", "source_url",
                "listed_at", "last_seen_at", "valid_until", "is_active",
                "listing_source_name", "listing_source_license",
                "listing_source_ranking_permission", "import_status",
            )
        ),
        "candidate_price_basis": "list_price",
        "list_price_decision_id": UUID("40000000-0000-4000-8000-000000000001"),
        "list_price_source_url": "https://example.test/price-list",
        "list_price_terms": {"printed_basis": "incl_vat"},
    }
    conn = RecordingConnection()
    conn.rows = [offer_row, list_price_row]

    offer, list_price = AdvisorRepository(conn).list_candidates()

    assert offer["price_basis"] == "offer"
    assert offer["offer"]["id"] == shared["listing_id"]
    assert list_price["price_basis"] == "list_price"
    assert list_price["offer"] is None
    assert list_price["list_price"]["source_url"] == "https://example.test/price-list"


def test_legacy_child_rows_are_read_for_v1_specs_only():
    conn = RecordingConnection()
    AdvisorRepository(conn).list_candidates()
    sql = conn.calls[0][0]

    for alias in (
        "maintenance_items",
        "safety_ratings",
        "safety_features",
        "technology_comfort_features",
    ):
        end = sql.index(f") AS {alias}")
        fragment = sql[sql.rfind("COALESCE(", 0, end) : end]
        assert "AND s.catalog_version = 1" in fragment, alias
    provenance_end = sql.index(") AS spec_provenance")
    provenance = sql[sql.rfind("COALESCE(", 0, provenance_end) : provenance_end]
    assert "catalog_version" not in provenance


def test_model_analysis_query_drops_used_offers_without_mileage():
    conn = RecordingConnection()
    AdvisorRepository(conn).list_model_analysis_candidates()
    sql = conn.calls[0][0]
    start = sql.index("LEFT JOIN catalog_usable_listings")
    join = sql[start : sql.index("WHERE", start)]
    assert "l.condition = 'new'" in join
    assert "l.mileage IS NOT NULL" in join


# --- F-26: Model Analysis honours an explicit spec_id ----------------------------


def _vehicle(vehicle_id=VEHICLE_ID):
    return {
        "id": vehicle_id,
        "make": "Fiat",
        "model": "Panda",
        "model_year": 2024,
        "body_style": "city_car",
        "fuel_type": "petrol",
        "market": "IT",
        "base_price_eur": 15_000,
    }


def _spec(spec_id, *, is_default, list_price):
    return {
        "id": spec_id,
        "variant_key": f"variant-{spec_id}",
        "is_default": is_default,
        "trim": "Trim",
        "body_style": "city_car",
        "fuel_type": "petrol",
        "list_price_eur": list_price,
        "consumption_l_100km": 5.0,
        "seats": 5,
        "cargo_volume_liters": 300,
    }


def _candidate(listings=()):
    return {
        "vehicle": _vehicle(),
        "specs": [
            _spec(DEFAULT_SPEC_ID, is_default=True, list_price=18_000),
            _spec(SECOND_SPEC_ID, is_default=False, list_price=24_000),
        ],
        "listings": list(listings),
    }


def _resolved_default_spec():
    return VehicleResolveResponse.model_validate(
        {
            "query": "fiat panda",
            "normalized_query": "fiat panda",
            "status": "matched",
            "matches": [
                {
                    "confidence": 0.95,
                    "match_level": "spec",
                    "vehicle": _vehicle(),
                    "spec": _spec(DEFAULT_SPEC_ID, is_default=True, list_price=18_000),
                    "matched_fields": ["make", "model"],
                    "warnings": [],
                }
            ],
        }
    )


def _analyse(spec_id, candidate=None):
    return build_model_analysis(
        ModelAnalysisRequest(
            query="fiat panda",
            spec_id=spec_id,
            asking_price_eur=20_000,
            current_km=10_000,
            analysis_scope=["price"],
        ),
        [candidate or _candidate()],
        _resolved_default_spec(),
    )


def test_query_with_explicit_spec_keeps_the_callers_spec():
    response = _analyse(SECOND_SPEC_ID)

    assert response.resolved_spec is not None
    assert response.resolved_spec.id == SECOND_SPEC_ID
    assert response.estimated_costs.market_reference_price_eur == 24_000


def test_query_without_spec_uses_the_resolvers_spec():
    response = _analyse(None)

    assert response.resolved_spec is not None
    assert response.resolved_spec.id == DEFAULT_SPEC_ID


def test_explicit_spec_of_another_vehicle_is_reported_not_replaced():
    response = _analyse(OTHER_SPEC_ID)

    assert response.resolved_spec is None
    assert "requested_spec_not_found" in response.warnings
    assert "resolved_spec" in response.missing_data


# --- F-26: Model Analysis uses the Advisor offer rule -------------------------------


def _listing(price, *, condition, mileage, spec_id=DEFAULT_SPEC_ID):
    return {
        "id": UUID(int=price),
        "vehicle_id": VEHICLE_ID,
        "spec_id": spec_id,
        "price_eur": price,
        "condition": condition,
        "mileage": mileage,
    }


def test_used_offer_without_mileage_never_sets_the_reference_price():
    candidate = _candidate(
        [
            _listing(50_000, condition="used", mileage=None),
            _listing(19_000, condition="new", mileage=None),
            _listing(17_000, condition="used", mileage=30_000),
        ]
    )

    response = _analyse(None, candidate)

    assert response.estimated_costs.market_reference_price_eur == 18_000


def test_only_unknown_mileage_offers_fall_back_to_the_list_price():
    candidate = _candidate(
        [
            _listing(50_000, condition="used", mileage=None),
            _listing(40_000, condition="certified", mileage=None),
        ]
    )

    response = _analyse(None, candidate)

    assert response.estimated_costs.market_reference_price_eur == 18_000
    assert any("list price" in sentence for sentence in response.assumptions)


# --- F-16: realistic upper bounds -------------------------------------------------


@pytest.mark.parametrize(
    ("field", "limit"),
    [
        ("budget_max_eur", 10_000_000),
        ("budget_min_eur", 10_000_000),
        ("annual_km", 500_000),
        ("max_mileage", 5_000_000),
        ("passengers_usual", 20),
        ("children_count", 20),
    ],
)
def test_advisor_request_accepts_the_limit_and_rejects_one_more(field, limit):
    base = {"budget_max_eur": 10_000_000, "primary_use": "city"}
    AdvisorRecommendationRequest.model_validate({**base, field: limit})
    with pytest.raises(ValidationError):
        AdvisorRecommendationRequest.model_validate({**base, field: limit + 1})


@pytest.mark.parametrize(
    ("field", "limit"),
    [("asking_price_eur", 10_000_000), ("current_km", 5_000_000)],
)
def test_model_analysis_request_accepts_the_limit_and_rejects_one_more(field, limit):
    base = {"vehicle_id": str(VEHICLE_ID)}
    ModelAnalysisRequest.model_validate({**base, field: limit})
    with pytest.raises(ValidationError):
        ModelAnalysisRequest.model_validate({**base, field: limit + 1})


@pytest.fixture
def unreachable_repositories():
    class Unreachable:
        def __getattr__(self, name):
            raise AssertionError(f"validation must fail before {name} is used")

    app.dependency_overrides[get_advisor_repository] = Unreachable
    app.dependency_overrides[get_vehicles_repository] = Unreachable
    yield
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("path", "body"),
    [
        (
            "/advisor/recommendations",
            '{"budget_max_eur": 20000, "primary_use": "city", "annual_km": %s}',
        ),
        (
            "/advisor/recommendations",
            '{"budget_max_eur": %s, "primary_use": "city"}',
        ),
        (
            "/advisor/recommendations",
            '{"budget_max_eur": 20000, "primary_use": "city", "max_mileage": %s}',
        ),
        ("/advisor/model-analysis", '{"vehicle_id": "%s", "current_km": %%s}' % VEHICLE_ID),
        (
            "/advisor/model-analysis",
            '{"vehicle_id": "%s", "asking_price_eur": %%s}' % VEHICLE_ID,
        ),
    ],
)
def test_four_hundred_digit_numbers_are_a_clean_422(
    unreachable_repositories, path, body
):
    response = TestClient(app).post(
        path,
        content=body % HUGE,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]


def _candidate_row():
    return {
        "vehicle_id": VEHICLE_ID,
        "canonical_key": "it-fiat-panda-2024",
        "model_family_key": "it-fiat-panda",
        "make": "Fiat",
        "model": "Panda",
        "model_year": 2024,
        "vehicle_body_style": "city_car",
        "vehicle_fuel_type": "petrol",
        "market": "IT",
        "base_price_eur": 15_000,
        "spec_id": DEFAULT_SPEC_ID,
        "variant_key": "it-fiat-panda-2024-city",
        "is_default": True,
        "trim": "City",
        "spec_body_style": "city_car",
        "spec_fuel_type": "petrol",
        "list_price_eur": 18_000,
        "drivetrain": "fwd",
        "transmission": "manual",
        "engine": "1.0",
        "horsepower": 70,
        "battery_kwh": None,
        "energy_consumption_kwh_100km": None,
        "consumption_l_100km": 5.0,
        "wltp_range_km": None,
        "co2_g_km": 110,
        "euro_emission_standard": "Euro 6e",
        "seats": 4,
        "cargo_volume_liters": 225,
        "generation_name": None,
        "restyling_label": None,
        "category": None,
        "length_mm": None,
        "width_mm": None,
        "height_mm": None,
        "curb_weight_kg": None,
        "engine_code": None,
        "power_kw": None,
        "transmission_type": None,
        "acceleration_0_100_s": None,
        "top_speed_kmh": None,
        "braking_100_0_m": None,
        "maintenance_items": [],
        "safety_ratings": [],
        "safety_features": [],
        "technology_comfort_features": [],
        "spec_provenance": [],
        "listing_id": UUID("30000000-0000-4000-8000-000000000101"),
        "source_id": UUID("10000000-0000-4000-8000-000000000101"),
        "listing_ref": "panda-1",
        "title": "Fiat Panda",
        "price_eur": 17_500,
        "mileage": None,
        "condition": "new",
        "location_region": "Piemonte",
        "source_url": "https://example.test/offers/1",
        "listed_at": None,
        "last_seen_at": None,
        "valid_until": None,
        "is_active": True,
        "listing_source_name": "Reviewed catalog",
        "listing_source_license": "Synthetic test data",
        "listing_source_ranking_permission": "permitted",
        "import_status": "completed",
    }
