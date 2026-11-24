"""Storage readiness: one synthetic bundle from an invented, non-manufacturer source.

Collection is undecided, so nothing here assumes a collector. Every make, model,
price and URL is invented (ADR-011); the evidence kind is `sourced` only so that the
permission switch, the one thing under test, decides what the read catalogue shows.
"""

import copy
import hashlib
from decimal import Decimal
from uuid import UUID

import pytest

from app.ingestion.catalog import CatalogValidationError
from app.ingestion.catalog_v2 import CatalogV2
from app.ingestion.catalog_v2_writer import publish_catalog_v2, stage_catalog_v2
from app.repositories.advisor import AdvisorRepository
from app.repositories.vehicles import VehiclesRepository
from app.schemas.advisor import AdvisorRecommendationRequest
from app.schemas.vehicles import CatalogFact, VehicleDetail
from app.services.advisor.scoring import build_recommendations
from tests.test_catalog_v2_publication import conn  # noqa: F401  (fixture)

REGISTRY = "00000000-0000-4000-8000-0000000000a1"
COACHWORK = "00000000-0000-4000-8000-0000000000a2"
DECIDED_AT = "2026-10-02T09:00:00Z"
WLTP = {"market": "IT", "procedure": "WLTP", "cycle": "combined"}
UNITS = {
    "seats": "count",
    "cargo_volume_liters": "l",
    "liquid_consumption_l_100km": "l/100km",
    "electric_consumption_kwh_100km": "kWh/100km",
    "electric_range_km": "km",
    "co2_g_km": "g/km",
    "seat_height_mm": "mm",
    "mass_kg": "kg",
    "underseat_storage_liters": "l",
    "list_price_eur": "EUR",
}
# Read-view columns that carry a v2 fact; each must be NULL until the source is permitted.
READ_VALUES = (
    "seats",
    "cargo_volume_liters",
    "consumption_l_100km",
    "consumption_l_100km_basis",
    "energy_consumption_kwh_100km",
    "energy_consumption_kwh_100km_basis",
    "wltp_range_km",
    "co2_g_km",
    "list_price_eur",
)


def _vehicle(key, make, model, vehicle_type, body_style, evidence):
    return {
        "canonical_key": key,
        "model_family_key": key.rsplit("-", 1)[0],
        "make": make,
        "model": model,
        "vehicle_type": vehicle_type,
        "generation_key": None,
        "phase_key": None,
        "body_style": body_style,
        "model_year": 2026,
        "market": "IT",
        "evidence_snapshot_ids": evidence,
    }


def _variant(key, vehicle, powertrain, fuel):
    return {
        "variant_key": key,
        "vehicle_key": vehicle,
        "trim": "Synthetic",
        "powertrain_type": powertrain,
        "fuel": fuel,
        "transmission": "automatic",
        "drivetrain": "FWD",
        "evidence_snapshot_ids": [REGISTRY],
    }


def _fact(data, variant, metric, low, high=None, context=None, list_price=None):
    number = len(data["observations"]) + 1
    observation_id = f"00000000-0000-4000-8000-{number:012d}"
    context = context or {"market": "IT"}
    data["observations"].append(
        {
            "id": observation_id,
            "snapshot_id": REGISTRY,
            "variant_key": variant,
            "metric": metric,
            "raw_value": f"{low}-{high}" if high else str(low),
            "raw_unit": UNITS[metric],
            "value_min": str(low),
            "value_max": str(high or low),
            "unit": UNITS[metric],
            "context": context,
            "evidence_excerpt": f"Synthetic registry row: {metric}",
            "evidence_locator": f"row {number}",
            "extractor_version": "synthetic-readiness-1",
            **({"list_price": list_price} if list_price else {}),
        }
    )
    data["decisions"].append(
        {
            "id": f"00000000-0000-4000-9000-{number:012d}",
            "variant_key": variant,
            "metric": metric,
            "context": context,
            "status": "verified",
            "selected_observation_id": observation_id,
            "evidence_ids": [observation_id],
            "reason": "Synthetic readiness proof",
            "actor_kind": "human",
            "actor_id": "synthetic-reviewer",
            "policy_version": "synthetic-1",
            "decided_at": DECIDED_AT,
        }
    )


def _terms(**terms):
    return {
        "trim_label": "Synthetic row",
        "price_list_valid_from": "2026-09-01",
        **terms,
    }


def readiness_bundle(tmp_path, *, body_style="hatchback"):
    """A car (petrol and electric), a motorcycle and an electric scooter."""
    snapshots = []
    sources = []
    for snapshot_id, key, name in [
        (REGISTRY, "lumen-registry", "Lumen open vehicle registry (synthetic)"),
        (COACHWORK, "coachwork-notes", "Coachwork notes (synthetic)"),
    ]:
        content = f"Synthetic readiness evidence {key}".encode()
        path = tmp_path / "readiness" / f"{key}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        sources.append(
            {
                "source_key": key,
                "name": name,
                "source_type": "public_dataset",
                "market": "IT",
                "ranking_permission": "manual_validation_only",
                "url": f"https://{key}.example.com/",
                "license": "Synthetic fixture only",
            }
        )
        snapshots.append(
            {
                "id": snapshot_id,
                "source_key": key,
                "url": f"https://{key}.example.com/export",
                "retrieved_at": "2026-10-01T08:00:00Z",
                "content_sha256": hashlib.sha256(content).hexdigest(),
                "artifact_path": f"readiness/{key}.html",
                "media_type": "text/html",
                "evidence_kind": "sourced",
            }
        )
    # The registry names the car; a second source states its body style.
    car_evidence = [REGISTRY, COACHWORK] if body_style else [REGISTRY]
    data = {
        "schema_version": 2,
        "sources": sources,
        "snapshots": snapshots,
        "vehicles": [
            _vehicle("zephra-tavo-2026", "Zephra", "Tavo", "car", body_style, car_evidence),
            _vehicle(
                "orvane-strada-2026", "Orvane", "Strada", "motorcycle", "naked", [REGISTRY]
            ),
            _vehicle(
                "pellio-glide-2026", "Pellio", "Glide", "scooter", "scooter", [REGISTRY]
            ),
        ],
        "variants": [
            _variant("tavo-petrol", "zephra-tavo-2026", "ICE", "petrol"),
            _variant("tavo-electric", "zephra-tavo-2026", "BEV", "electricity"),
            _variant("strada-700", "orvane-strada-2026", "ICE", "petrol"),
            _variant("glide-e", "pellio-glide-2026", "BEV", "electricity"),
        ],
        "observations": [],
        "decisions": [],
    }
    cargo = {"market": "IT", "method": "VDA", "seating_configuration": "all_seats_up"}
    wet = {"market": "IT", "method": "wet"}
    for variant in ("tavo-petrol", "tavo-electric"):
        _fact(data, variant, "seats", 5)
        _fact(data, variant, "cargo_volume_liters", 380, context=cargo)
    # ADR-018: interval consumption is published at its upper value.
    _fact(data, "tavo-petrol", "liquid_consumption_l_100km", "5.1", "5.9", WLTP)
    # Any other interval stays out of the scalar reads.
    _fact(data, "tavo-petrol", "co2_g_km", 118, 134, WLTP)
    _fact(data, "tavo-electric", "electric_consumption_kwh_100km", "14.8", "16.2", WLTP)
    _fact(data, "tavo-electric", "electric_range_km", 410, context=WLTP)
    # Three price bases: printed with VAT, printed without VAT, turnkey only.
    _fact(
        data, "tavo-petrol", "list_price_eur", "23450.00",
        list_price=_terms(printed_amount_eur="23450.00", printed_basis="incl_vat"),
    )
    _fact(
        data, "tavo-electric", "list_price_eur", "30500.00",  # 31,720.00 - 1,000.00 x 1.22
        list_price=_terms(
            printed_amount_eur="31720.00",
            printed_basis="turnkey",
            on_road_charge_eur="1000.00",
            on_road_charge_includes_vat=False,
            vat_rate_percent="22",
        ),
    )
    _fact(
        data, "strada-700", "list_price_eur", "9150.00",  # 7,500.00 x 1.22
        list_price=_terms(
            printed_amount_eur="7500.00", printed_basis="excl_vat", vat_rate_percent="22"
        ),
    )
    _fact(
        data, "glide-e", "list_price_eur", "4250.00",  # 4,500.00 - 250.00 with VAT
        list_price=_terms(
            printed_amount_eur="4500.00",
            printed_basis="turnkey",
            on_road_charge_eur="250.00",
            on_road_charge_includes_vat=True,
        ),
    )
    # Two-wheel facts from migration 0010.
    _fact(data, "strada-700", "seat_height_mm", 805)
    _fact(data, "strada-700", "mass_kg", 196, context=wet)
    _fact(data, "glide-e", "seat_height_mm", 770)
    _fact(data, "glide-e", "mass_kg", 112, context=wet)
    _fact(data, "glide-e", "underseat_storage_liters", 31)
    return data


def publish(db, data, root):
    batch = stage_catalog_v2(db, CatalogV2.model_validate(data), artifact_root=root)
    return publish_catalog_v2(db, batch, artifact_root=root)


def read_specs(db):
    return {
        row["variant_key"]: row
        for row in db.execute(
            "SELECT * FROM catalog_read_specs WHERE catalog_version = 2"
        ).fetchall()
    }


def two_wheel(db, canonical_key):
    """The `two_wheel` block of each spec, as GET /vehicles/{id} returns it."""
    vehicle_id = db.execute(
        "SELECT id FROM vehicles WHERE canonical_key = %s", (canonical_key,)
    ).fetchone()["id"]
    detail = VehicleDetail.model_validate(VehiclesRepository(db).get_vehicle(vehicle_id))
    return {spec.variant_key: spec.two_wheel.model_dump() for spec in detail.specs}


def test_a_synthetic_bundle_is_published_only_once_its_sources_are_permitted(
    conn, tmp_path  # noqa: F811
):
    data = readiness_bundle(tmp_path)
    assert publish(conn, data, tmp_path) == "published"
    specs = read_specs(conn)
    assert set(specs) == {"tavo-petrol", "tavo-electric", "strada-700", "glide-e"}
    types = [
        row["vehicle_type"]
        for row in conn.execute(
            "SELECT vehicle_type FROM vehicles WHERE catalog_version = 2"
        ).fetchall()
    ]
    assert sorted(types) == ["car", "motorcycle", "scooter"]

    # manual_validation_only: every published value is NULL, wherever it is read.
    for spec in specs.values():
        assert {column: spec[column] for column in READ_VALUES} == dict.fromkeys(
            READ_VALUES
        )
    assert conn.execute("SELECT count(*) AS n FROM catalog_scalar_facts").fetchone()[
        "n"
    ] == 0
    assert two_wheel(conn, "orvane-strada-2026")["strada-700"] == {
        "seat_height_mm": None,
        "wet_weight_kg": None,
        "fuel_tank_capacity_liters": None,
        "underseat_storage_liters": None,
    }
    # Body style is identity: the read view shows it, the engine does not use it yet.
    assert specs["tavo-petrol"]["body_style"] == "hatchback"
    analysis = conn.execute(
        "SELECT body_style FROM catalog_analysis_specs WHERE variant_key = 'tavo-petrol'"
    ).fetchone()
    assert analysis["body_style"] is None
    assert AdvisorRepository(conn).list_candidates() == []

    conn.execute(
        "UPDATE sources SET ranking_permission = 'permitted' "
        "WHERE source_key IN ('lumen-registry', 'coachwork-notes')"
    )
    specs = read_specs(conn)
    petrol, electric = specs["tavo-petrol"], specs["tavo-electric"]
    assert (petrol["seats"], petrol["cargo_volume_liters"]) == (5, Decimal("380"))
    assert (petrol["consumption_l_100km"], petrol["consumption_l_100km_basis"]) == (
        Decimal("5.9"),
        "interval_upper",
    )
    assert petrol["co2_g_km"] is None  # an emissions interval is not flattened
    assert (
        electric["energy_consumption_kwh_100km"],
        electric["energy_consumption_kwh_100km_basis"],
        electric["wltp_range_km"],
    ) == (Decimal("16.2"), "interval_upper", 410)
    assert {key: spec["list_price_eur"] for key, spec in specs.items()} == {
        "tavo-petrol": Decimal("23450.00"),
        "tavo-electric": Decimal("30500.00"),
        "strada-700": Decimal("9150.00"),
        "glide-e": Decimal("4250.00"),
    }
    bases = {
        row["variant_key"]: row["basis"]
        for row in conn.execute(
            """SELECT s.variant_key, o.list_price->>'printed_basis' AS basis
               FROM catalog_scalar_facts f
               JOIN vehicle_specs s ON s.id = f.spec_id
               JOIN spec_observations o ON o.id = f.selected_observation_id
               WHERE f.metric = 'list_price_eur'"""
        ).fetchall()
    }
    assert sorted(bases.values()) == ["excl_vat", "incl_vat", "turnkey", "turnkey"]
    assert two_wheel(conn, "orvane-strada-2026")["strada-700"] == {
        "seat_height_mm": 805,
        "wet_weight_kg": 196,
        "fuel_tank_capacity_liters": None,
        "underseat_storage_liters": None,
    }
    assert two_wheel(conn, "pellio-glide-2026")["glide-e"] == {
        "seat_height_mm": 770,
        "wet_weight_kg": 112,
        "fuel_tank_capacity_liters": None,
        "underseat_storage_liters": 31,
    }
    assert conn.execute(
        "SELECT body_style FROM catalog_analysis_specs WHERE variant_key = 'tavo-petrol'"
    ).fetchone()["body_style"] == "hatchback"

    # The facts endpoint and the engine read the same scalar.
    vehicle_id = petrol["vehicle_id"]
    facts = {
        (fact["variant_key"], fact["metric"]): fact
        for fact in VehiclesRepository(conn).list_facts(vehicle_id)
    }
    consumption = facts[("tavo-petrol", "liquid_consumption_l_100km")]
    assert (consumption["value_min"], consumption["value_max"]) == (
        Decimal("5.1"),
        Decimal("5.9"),
    )
    assert (consumption["published_value"], consumption["published_basis"]) == (
        petrol["consumption_l_100km"],
        "interval_upper",
    )
    # The facts response model carries the same pair.
    published = CatalogFact.model_validate(consumption)
    assert (published.published_value, published.published_basis) == (
        5.9,
        "interval_upper",
    )
    assert facts[("tavo-petrol", "co2_g_km")]["published_value"] is None
    assert facts[("tavo-petrol", "seats")]["published_basis"] == "exact"

    # Both car variants rank, each at its list price and its published consumption.
    candidates = AdvisorRepository(conn).list_candidates()
    by_variant = {c["spec"]["variant_key"]: c for c in candidates}
    assert set(by_variant) == {"tavo-petrol", "tavo-electric"}
    assert by_variant["tavo-petrol"]["spec"]["consumption_l_100km"] == Decimal("5.9")
    assert (
        by_variant["tavo-petrol"]["spec"]["consumption_l_100km_basis"]
        == "interval_upper"
    )
    # Ranking keeps one variant per model family, so each is scored on its own.
    request = AdvisorRecommendationRequest(budget_max_eur=35000, primary_use="family")
    items = {
        key: build_recommendations(request, [candidate])
        for key, candidate in by_variant.items()
    }
    assert {key: len(found) for key, found in items.items()} == {
        "tavo-petrol": 1,
        "tavo-electric": 1,
    }
    petrol_item = items["tavo-petrol"][0]
    assert petrol_item.selected_spec.consumption_l_100km_basis == "interval_upper"
    assert petrol_item.list_price.derivation == "printed"
    # A turnkey-only row reaches the response model with its printed terms.
    turnkey = items["tavo-electric"][0].list_price
    assert (
        turnkey.price_eur,
        turnkey.derivation,
        turnkey.printed_basis,
        turnkey.printed_amount_eur,
        turnkey.on_road_charge_eur,
        turnkey.on_road_charge_includes_vat,
        turnkey.vat_rate_percent,
        turnkey.computed_from_excl_vat,
    ) == (30500.0, "computed_from_turnkey", "turnkey", 31720.0, 1000.0, False, 22.0, False)


def test_a_later_bundle_fills_an_unknown_body_style_with_its_evidence(
    conn, tmp_path  # noqa: F811
):
    # A registry-only identity is published without a body style.
    first = readiness_bundle(tmp_path, body_style=None)
    assert publish(conn, first, tmp_path) == "published"
    later = readiness_bundle(tmp_path)
    assert publish(conn, later, tmp_path) == "published"
    vehicle = conn.execute(
        "SELECT id, body_style, identity_evidence FROM vehicles WHERE canonical_key = %s",
        ("zephra-tavo-2026",),
    ).fetchone()
    assert vehicle["body_style"] == "hatchback"
    assert vehicle["identity_evidence"] == [UUID(REGISTRY), UUID(COACHWORK)]
    assert {
        row["body_style"]
        for row in conn.execute(
            "SELECT body_style FROM vehicle_specs WHERE vehicle_id = %s",
            (vehicle["id"],),
        ).fetchall()
    } == {"hatchback"}
    # Eligibility now also needs the body-style source: it became stricter, not looser.
    conn.execute(
        "UPDATE sources SET ranking_permission = 'permitted' WHERE source_key = 'lumen-registry'"
    )
    assert conn.execute(
        """SELECT bool_or(eligible) AS any FROM catalog_identity_eligibility e
           JOIN vehicle_specs s ON s.id = e.spec_id WHERE s.vehicle_id = %s""",
        (vehicle["id"],),
    ).fetchone()["any"] is False
    conn.execute(
        "UPDATE sources SET ranking_permission = 'permitted' WHERE source_key = 'coachwork-notes'"
    )
    assert {c["spec"]["variant_key"] for c in AdvisorRepository(conn).list_candidates()} == {
        "tavo-petrol",
        "tavo-electric",
    }
    # The body style is credited to the snapshot that states it, the fuel to the
    # variant's own identity evidence.
    credited = {
        (metric, row["source_key"])
        for row in conn.execute(
            """SELECT p.metadata->'supported_metrics' AS metrics, src.source_key
               FROM catalog_read_provenance p
               JOIN sources src ON src.id = p.source_id
               JOIN vehicle_specs s ON s.id = p.spec_id
               WHERE s.variant_key = 'tavo-petrol'
                 AND p.metadata ? 'supported_metrics'
                 AND NOT p.metadata ? 'decision_id'"""
        ).fetchall()
        for metric in row["metrics"]
    }
    assert credited == {
        ("body_style", "coachwork-notes"),
        ("fuel_type", "lumen-registry"),
    }


def test_an_unknown_body_style_gets_no_credit(conn, tmp_path):  # noqa: F811
    assert publish(conn, readiness_bundle(tmp_path, body_style=None), tmp_path) == "published"
    conn.execute(
        "UPDATE sources SET ranking_permission = 'permitted' WHERE source_key = 'lumen-registry'"
    )
    credited = {
        metric
        for row in conn.execute(
            """SELECT p.metadata->'supported_metrics' AS metrics
               FROM catalog_read_provenance p
               JOIN vehicle_specs s ON s.id = p.spec_id
               WHERE s.variant_key = 'tavo-petrol' AND NOT p.metadata ? 'decision_id'"""
        ).fetchall()
        for metric in row["metrics"]
    }
    assert credited == {"fuel_type"}


@pytest.mark.parametrize(
    ("first_body_style", "change", "message"),
    [
        # A known body style is identity: it is never overwritten by an import.
        (
            "hatchback",
            lambda d: d["vehicles"][0].update(body_style="wagon"),
            "differs at body_style",
        ),
        # The fill must bring the evidence that states it.
        (
            None,
            lambda d: d["vehicles"][0].update(evidence_snapshot_ids=[REGISTRY]),
            "differs at body_style",
        ),
        # Evidence is appended, never replaced.
        (
            None,
            lambda d: d["vehicles"][0].update(evidence_snapshot_ids=[COACHWORK]),
            "differs at body_style",
        ),
        # Repeating a stored snapshot brings no new source for the body style.
        (
            None,
            lambda d: d["vehicles"][0].update(
                evidence_snapshot_ids=[REGISTRY, REGISTRY]
            ),
            "differs at body_style",
        ),
        # Read provenance credits the last snapshot, so it must be the new one.
        (
            None,
            lambda d: d["vehicles"][0].update(
                evidence_snapshot_ids=[REGISTRY, COACHWORK, REGISTRY]
            ),
            "differs at body_style",
        ),
        # Every published variant must carry the filled body style.
        (
            None,
            lambda d: (
                d["variants"].pop(1),
                d.update(
                    observations=[
                        o for o in d["observations"] if o["variant_key"] != "tavo-electric"
                    ],
                    decisions=[
                        x for x in d["decisions"] if x["variant_key"] != "tavo-electric"
                    ],
                ),
            ),
            "every published variant",
        ),
    ],
)
def test_a_body_style_fill_is_refused_unless_it_only_adds_knowledge(
    conn, tmp_path, first_body_style, change, message  # noqa: F811
):
    first = readiness_bundle(tmp_path, body_style=first_body_style)
    assert publish(conn, first, tmp_path) == "published"
    later = copy.deepcopy(readiness_bundle(tmp_path))
    change(later)
    with pytest.raises(CatalogValidationError, match=message):
        with conn.transaction():
            publish(conn, later, tmp_path)
