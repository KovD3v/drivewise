"""What the web needs to show a list-price item and credit every source.

Synthetic bundle only (ADR-011): invented makes, example.com URLs.
"""

import hashlib

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_connection
from app.main import app
from tests.test_catalog_storage_readiness import (
    WLTP,
    _fact,
    publish,
    readiness_bundle,
)
from tests.test_catalog_v2_publication import conn  # noqa: F401  (fixture)

LICENCE = "Synthetic fixture only"
MIRROR = "00000000-0000-4000-8000-0000000000a3"


def _with_http_mirror(data, tmp_path):
    """An ICE car's optional electric range, cited by a plain-HTTP page."""
    content = b"Synthetic plain-http mirror"
    (tmp_path / "readiness" / "mirror.html").write_bytes(content)
    data["sources"].append(
        {
            "source_key": "plain-mirror",
            "name": "Plain mirror (synthetic)",
            "source_type": "public_dataset",
            "market": "IT",
            "ranking_permission": "manual_validation_only",
            "url": "http://plain-mirror.example.com/",
            "license": "Synthetic mirror licence",
        }
    )
    data["snapshots"].append(
        {
            "id": MIRROR,
            "source_key": "plain-mirror",
            "url": "http://plain-mirror.example.com/export",
            "retrieved_at": "2026-10-01T08:00:00Z",
            "content_sha256": hashlib.sha256(content).hexdigest(),
            "artifact_path": "readiness/mirror.html",
            "media_type": "text/html",
            "evidence_kind": "sourced",
        }
    )
    _fact(data, "tavo-petrol", "electric_range_km", 40, context=WLTP)
    data["observations"][-1]["snapshot_id"] = MIRROR
    return data


@pytest.fixture
def client(conn, tmp_path):  # noqa: F811
    data = _with_http_mirror(readiness_bundle(tmp_path), tmp_path)
    assert publish(conn, data, tmp_path) == "published"
    conn.execute("UPDATE sources SET ranking_permission = 'permitted'")
    app.dependency_overrides[get_connection] = lambda: conn
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _car(conn):  # noqa: F811
    return conn.execute(
        "SELECT id FROM vehicles WHERE make = %s AND model = %s", ("Zephra", "Tavo")
    ).fetchone()["id"]


def test_vehicle_detail_carries_list_price_terms_basis_and_credits(client, conn):  # noqa: F811
    response = client.get(f"/vehicles/{_car(conn)}")
    assert response.status_code == 200
    specs = {spec["variant_key"]: spec for spec in response.json()["specs"]}
    petrol, electric = specs["tavo-petrol"], specs["tavo-electric"]

    assert petrol["consumption_l_100km_basis"] == "interval_upper"
    price = electric["list_price"]
    assert {
        key: price[key]
        for key in (
            "price_eur", "derivation", "printed_basis", "printed_amount_eur",
            "trim_label", "price_list_valid_from", "substitute_note",
            "source_name", "source_url", "source_license",
        )
    } == {
        "price_eur": 30500.0,
        "derivation": "computed_from_turnkey",
        "printed_basis": "turnkey",
        "printed_amount_eur": 31720.0,
        "trim_label": "Synthetic row",
        "price_list_valid_from": "2026-09-01",
        "substitute_note": None,
        "source_name": "Lumen open vehicle registry (synthetic)",
        "source_url": "https://lumen-registry.example.com/export",
        "source_license": LICENCE,
    }
    assert price["observed_at"].startswith("2026-10-01")
    assert price["price_eur"] == electric["list_price_eur"]

    # A v2 spec is credited with every source behind the values it shows.
    credits = {entry["source_key"]: entry for entry in petrol["provenance"]}
    assert set(credits) == {"lumen-registry", "plain-mirror", "coachwork-notes"}
    registry = credits["lumen-registry"]
    assert registry["source_license"] == LICENCE
    assert registry["source_url"] == "https://lumen-registry.example.com/export"
    assert {"list_price_eur", "consumption_l_100km", "seats"} <= set(
        registry["supported_metrics"]
    )
    # Fuel type comes from the variant's source, body style from the snapshot
    # that states it on the vehicle.
    assert "fuel_type" in registry["supported_metrics"]
    assert "body_style" not in registry["supported_metrics"]
    assert credits["coachwork-notes"]["supported_metrics"] == ["body_style"]
    assert credits["plain-mirror"]["source_url"].startswith("http://")
    # The vehicle's identity, body style included, credits both of its sources.
    vehicle_credits = {e["source_key"]: e for e in response.json()["provenance"]}
    assert set(vehicle_credits) == {"lumen-registry", "coachwork-notes"}
    assert vehicle_credits["coachwork-notes"]["source_license"] == LICENCE


def test_facts_name_the_licence_of_their_source(client, conn):  # noqa: F811
    response = client.get(f"/vehicles/{_car(conn)}/facts")
    assert response.status_code == 200
    licences = {
        (fact["variant_key"], fact["metric"]): fact["source_license"]
        for fact in response.json()
    }
    assert licences[("tavo-petrol", "list_price_eur")] == LICENCE
    assert licences[("tavo-petrol", "electric_range_km")] == "Synthetic mirror licence"


def test_recommendations_carry_list_price_credits_and_skip_http_evidence(
    client, conn  # noqa: F811
):
    response = client.post(
        "/advisor/recommendations",
        json={"budget_max_eur": 35000, "primary_use": "family"},
    )
    # The petrol variant's optional electric range cites an http:// page.
    assert response.status_code == 200, response.text
    items = [item for group in response.json()["groups"] for item in group["items"]]
    assert items
    for item in items:
        assert (item["price_basis"], item["offer"]) == ("list_price", None)
        assert item["list_price"]["source_license"] == LICENCE
        assert item["list_price"]["price_list_valid_from"] == "2026-09-01"
        assert all(p["source_url"].startswith("https://") for p in item["provenance"])
        catalogue = [p for p in item["provenance"] if "example.com" in p["source_url"]]
        assert catalogue and all(p["source_license"] == LICENCE for p in catalogue)
        assert "of offer price" not in " ".join(item["evidence"]["assessments"]["tco"]["assumptions"])


def test_recommendations_omit_a_value_whose_only_source_is_http(client):
    response = client.post(
        "/advisor/recommendations",
        json={"budget_max_eur": 25000, "primary_use": "family"},
    )
    assert response.status_code == 200, response.text
    items = [item for group in response.json()["groups"] for item in group["items"]]
    petrol = [i for i in items if i["selected_spec"]["variant_key"] == "tavo-petrol"]
    assert len(petrol) == 1, [i["selected_spec"]["variant_key"] for i in items]
    item = petrol[0]
    # The 40 km range cites only an http:// page, so neither value nor credit is shown.
    assert item["selected_spec"]["wltp_range_km"] is None
    assert "wltp_range_km" not in item["evidence"]
    assert "wltp_range_km" not in {p["metric"] for p in item["provenance"]}
    # A value with an HTTPS source keeps both value and credit.
    assert item["selected_spec"]["consumption_l_100km"] is not None
    assert item["evidence"]["consumption_l_100km"] is not None
    assert "consumption_l_100km" in {p["metric"] for p in item["provenance"]}


def test_model_analysis_credits_the_list_price_it_uses(client, conn):  # noqa: F811
    spec_id = conn.execute(
        "SELECT id FROM vehicle_specs WHERE variant_key = %s", ("tavo-electric",)
    ).fetchone()["id"]
    response = client.post(
        "/advisor/model-analysis",
        json={"vehicle_id": str(_car(conn)), "spec_id": str(spec_id), "analysis_scope": ["price"]},
    )
    assert response.status_code == 200, response.text
    costs = response.json()["estimated_costs"]
    assert costs["market_reference_price_eur"] == 30500.0
    credit = costs["market_reference_list_price"]
    assert credit["price_eur"] == 30500.0
    assert credit["source_name"] == "Lumen open vehicle registry (synthetic)"
    assert credit["source_url"] == "https://lumen-registry.example.com/export"
    assert credit["source_license"] == LICENCE
    assert credit["observed_at"].startswith("2026-10-01")


def test_vehicle_detail_credits_identity_before_ranking_permission(conn, tmp_path):  # noqa: F811
    # No source is permitted yet: facts stay hidden, but body style and fuel type
    # are shown, so their sources are credited.
    assert publish(conn, readiness_bundle(tmp_path), tmp_path) == "published"
    app.dependency_overrides[get_connection] = lambda: conn
    try:
        response = TestClient(app).get(f"/vehicles/{_car(conn)}")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    for spec in response.json()["specs"]:
        assert spec["fuel_type"] is not None
        credited = {
            (metric, entry["source_key"])
            for entry in spec["provenance"]
            for metric in entry["supported_metrics"]
        }
        assert credited == {
            ("fuel_type", "lumen-registry"),
            ("body_style", "coachwork-notes"),
        }


def test_vehicle_detail_gives_no_credit_for_an_unknown_fuel(conn, tmp_path):  # noqa: F811
    data = readiness_bundle(tmp_path)
    petrol = next(v for v in data["variants"] if v["variant_key"] == "tavo-petrol")
    petrol["fuel"] = None
    assert publish(conn, data, tmp_path) == "published"
    app.dependency_overrides[get_connection] = lambda: conn
    try:
        response = TestClient(app).get(f"/vehicles/{_car(conn)}")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    spec = next(s for s in response.json()["specs"] if s["variant_key"] == "tavo-petrol")
    assert spec["fuel_type"] is None
    assert {m for e in spec["provenance"] for m in e["supported_metrics"]} == {"body_style"}


def test_model_analysis_leaves_out_a_list_price_it_cannot_cite(conn, tmp_path):  # noqa: F811
    data = _with_http_mirror(readiness_bundle(tmp_path), tmp_path)
    for observation in data["observations"]:
        if (observation["variant_key"], observation["metric"]) == (
            "tavo-electric",
            "list_price_eur",
        ):
            observation["snapshot_id"] = MIRROR
    assert publish(conn, data, tmp_path) == "published"
    conn.execute("UPDATE sources SET ranking_permission = 'permitted'")
    spec_id = conn.execute(
        "SELECT id FROM vehicle_specs WHERE variant_key = %s", ("tavo-electric",)
    ).fetchone()["id"]
    app.dependency_overrides[get_connection] = lambda: conn
    try:
        response = TestClient(app).post(
            "/advisor/model-analysis",
            json={
                "vehicle_id": str(_car(conn)),
                "spec_id": str(spec_id),
                "analysis_scope": ["price"],
            },
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    costs = response.json()["estimated_costs"]
    assert costs["market_reference_list_price"] is None
    assert costs["market_reference_price_eur"] is None


def test_guided_preview_carries_the_same_list_price_item(client):
    created = client.post(
        "/guided-decisions",
        json={"message": "Auto per la famiglia, budget 35.000 euro"},
    )
    assert created.status_code == 200, created.text
    preview = created.json()["previewRanking"]
    items = [item for group in preview["groups"] for item in group["items"]]
    assert preview["status"] == "provisional", preview["status"]
    assert items
    for item in items:
        assert (item["price_basis"], item["offer"]) == ("list_price", None)
        price = item["list_price"]
        assert price["source_license"] == LICENCE
        assert price["source_url"].startswith("https://")
        assert price["trim_label"] and price["price_list_valid_from"] == "2026-09-01"
        assert all("source_license" in p for p in item["provenance"])
