"""Hardening of the open-data builder: make isolation, safe paths, row caps, history.

Every test runs offline against the fake registries of test_open_data."""

import copy
import io
import json
import urllib.request
from datetime import UTC, datetime

import pytest
from test_open_data import (  # noqa: F401
    NAMES,
    TWO_WHEELERS,
    FakeRegistries,
    LaterRegistries,
    cli_build,
    later,
    load_script,
    run,
)

from app.ingestion import open_data
from app.ingestion.catalog_v2 import CatalogV2

PANDA_TAN = "e3*2007/46*0064*72"
PANDA_VERSION = ("E3*2007/46*0064*72", "PYD1B", "AA4")
LIBERTY_TAN = "e13*168/2013*02373*01"
NOW = datetime(2026, 11, 23, tzinfo=UTC)


def fetched(tmp_path, registries, two_wheelers=TWO_WHEELERS) -> open_data.Run:
    stored = open_data.Run(tmp_path / "stored")
    open_data.fetch(stored, NAMES, two_wheelers, registries, now=lambda: NOW)
    return stored


def panda_hybrid(report: dict) -> dict:
    (family,) = [f for f in report["families"] if f["key"] == "it-fiat-panda"]
    (variant,) = [v for v in family["variants"] if v["fuel_mode"] == "H"]
    return variant


def liberty(report: dict) -> dict:
    return next(m for m in report["models"] if m["key"] == "it-piaggio-liberty-125")


def metrics(bundle: dict, variant_key: str) -> dict:
    return {
        o["metric"]: o
        for o in bundle["observations"]
        if o["variant_key"] == variant_key
    }


# --- F-09: one make never lends values or plates to another ------------------------


class SharedApprovalRegistries(FakeRegistries):
    """A second make registers the Panda's approval version, many times over."""

    def __init__(self):
        super().__init__()
        self.plate_queries = []

    def rdw(self, url, query):
        rows = super().rdw(url, query)
        where, select = query["$where"][0], query["$select"][0]
        if select == "kenteken":
            self.plate_queries.append(where)
        if PANDA_TAN in where and "lengte" in select:
            tesla = {
                "merk": "TESLA",
                "lengte": "500",
                "breedte": "200",
                "hoogte_voertuig": "140",
                "aantal_zitplaatsen": "5",
                "n": "5000",
            }
            rows = [tesla, *rows]
        return rows


def test_dimensions_and_hybrid_plates_come_from_the_family_make_only(tmp_path):
    registries = SharedApprovalRegistries()
    stored = fetched(tmp_path, registries)
    bundle, report = open_data.build_cars(stored, NAMES)

    variant = panda_hybrid(report)
    values = metrics(bundle, variant["variant_key"])
    assert (
        values["length_mm"]["value_min"] == values["length_mm"]["value_max"] == "3650"
    )
    assert values["seats"]["value_min"] == "4"
    assert "TESLA" not in values["length_mm"]["evidence_excerpt"]
    # The plate sample is asked for the registry's spelling of the make.
    assert registries.plate_queries
    assert all("merk in ('FIAT')" in where for where in registries.plate_queries)


def test_a_version_complete_only_under_another_make_is_not_chosen(tmp_path):
    stored = open_data.Run(tmp_path / "stored")
    first = {"key": ["petrol", "M", "E1*1", "A", "1"], "doc_count": 10}
    second = {"key": ["petrol", "M", "E1*2", "B", "2"], "doc_count": 5}
    complete = {"lengte": "400", "breedte": "180", "hoogte_voertuig": "150"}
    responses = {
        tuple(first["key"][2:]): [
            {"merk": "OTHER", **complete, "aantal_zitplaatsen": "5", "n": "90"},
            {"merk": "FIAT", "lengte": "400", "n": "3"},
        ],
        tuple(second["key"][2:]): [
            {"merk": "FIAT", **complete, "aantal_zitplaatsen": "5", "n": "4"}
        ],
    }
    for approval, rows in responses.items():
        request = open_data.rdw_car_request(*approval)
        stored.store(request, json.dumps(rows).encode(), NOW)

    bucket, request, missing = open_data.choose_version(
        stored, {"make": "Fiat"}, {"versions": [first, second]}
    )

    assert missing == []
    assert bucket is second
    assert request == open_data.rdw_car_request(*second["key"][2:])


# --- F-10: a slug is one safe file name; the run never writes outside -----------------


@pytest.mark.parametrize(
    "value",
    ["../escape", "a/b", "a\\b", "..", ".", "", "Upper", "-lead", "x\n", None, 7],
)
def test_an_unsafe_two_wheeler_slug_is_refused_before_any_fetch(tmp_path, value):
    models = [{**TWO_WHEELERS["models"][0], "slug": value}]

    def offline(url):
        raise AssertionError("nothing may be fetched")

    with pytest.raises(open_data.OpenDataError, match="slug"):
        open_data.fetch(
            open_data.Run(tmp_path / "run"), NAMES, {"models": models}, offline
        )
    assert not (tmp_path / "run").exists()


def test_a_duplicate_two_wheeler_slug_is_refused():
    entry = TWO_WHEELERS["models"][0]
    with pytest.raises(open_data.OpenDataError, match="twice"):
        open_data.validate_two_wheelers({"models": [entry, dict(entry)]})


@pytest.mark.parametrize(
    "path", ["../outside.json", "rdw/../../outside.json", "/tmp/outside.json", "", "."]
)
def test_the_run_never_writes_outside_its_artifacts_folder(tmp_path, path):
    stored = open_data.Run(tmp_path / "stored")
    request = open_data.Request(path, "https://opendata.rdw.nl/x")
    with pytest.raises(open_data.OpenDataError, match="leaves the artifacts folder"):
        stored.store(request, b"[]", NOW)
    assert not (tmp_path / "outside.json").exists()
    assert not stored.artifacts.exists()
    assert stored.manifest == {}


def test_a_symlink_out_of_the_artifacts_folder_is_refused(tmp_path):
    stored = open_data.Run(tmp_path / "stored")
    stored.artifacts.mkdir(parents=True)
    (tmp_path / "elsewhere").mkdir()
    (stored.artifacts / "rdw").symlink_to(tmp_path / "elsewhere")
    request = open_data.Request("rdw/x.json", "https://opendata.rdw.nl/x")
    with pytest.raises(open_data.OpenDataError, match="leaves the artifacts folder"):
        stored.store(request, b"[]", NOW)
    assert list((tmp_path / "elsewhere").iterdir()) == []


# --- Run: atomic writes, and an interrupted fetch resumes cleanly ------------------


def test_a_damaged_or_missing_artifact_is_fetched_again(run):  # noqa: F811
    request = open_data.motospecdb_request()
    path = run.artifacts / request.artifact_path
    original = path.read_bytes()
    for damage in (lambda: path.write_bytes(original[:10]), path.unlink):
        damage()
        reopened = open_data.Run(run.root)
        assert not reopened.has(request)
        with pytest.raises(open_data.OpenDataError):
            reopened.read(request)
        assert open_data.fetch(reopened, NAMES, TWO_WHEELERS, FakeRegistries()) == 1
        assert path.read_bytes() == original
        assert open_data.Run(run.root).has(request)


def test_an_artifact_stored_without_its_manifest_entry_reads_as_missing(
    tmp_path, monkeypatch
):
    stored = open_data.Run(tmp_path / "stored")
    request = open_data.Request("rdw/x.json", "https://opendata.rdw.nl/x")
    stored.store(request, b"[1]", NOW)
    manifest = stored.manifest_path.read_text()
    real = open_data._replace

    def crash_on_manifest(path, data):
        if path == stored.manifest_path:
            raise OSError("power cut")
        real(path, data)

    monkeypatch.setattr(open_data, "_replace", crash_on_manifest)
    second = open_data.Request("rdw/y.json", "https://opendata.rdw.nl/y")
    with pytest.raises(OSError):
        stored.store(second, b"[2]", NOW)
    # The manifest on disk is the earlier one, whole; the new file is not trusted.
    assert stored.manifest_path.read_text() == manifest
    reopened = open_data.Run(stored.root)
    assert reopened.has(request) and not reopened.has(second)
    assert not list(stored.root.rglob("*.tmp"))


def test_a_refetch_of_cited_evidence_must_return_the_same_bytes(run, tmp_path):  # noqa: F811
    assert cli_build(tmp_path, run.root, NAMES) == 0
    request = open_data.rdw_car_request(*PANDA_VERSION)
    path = run.artifacts / request.artifact_path
    path.write_bytes(b"[]")
    # The registry now answers differently: the bundle's hash would break.
    with pytest.raises(open_data.OpenDataError, match="evidence of a bundle"):
        open_data.fetch(open_data.Run(run.root), NAMES, TWO_WHEELERS, LaterRegistries())
    # The same answer as before restores the evidence.
    assert (
        open_data.fetch(open_data.Run(run.root), NAMES, TWO_WHEELERS, FakeRegistries())
        == 1
    )


# --- Row caps: a full answer is a gap, never verified ------------------------------


class CappedRegistries(FakeRegistries):
    def rdw(self, url, query):
        rows = super().rdw(url, query)
        where, select = query["$where"][0], query["$select"][0]
        if PANDA_TAN in where and ("lengte" in select or "inrichting" in select):
            return [rows[0]] * open_data.RDW_GROUP_LIMIT
        if open_data.RDW_APPROVAL_ENERGY in url:
            return [rows[0]] * open_data.RDW_APPROVAL_LIMIT
        if "merk='PIAGGIO'" in where and "massa_rijklaar" in select:
            return [rows[0]] * open_data.RDW_GROUP_LIMIT
        return rows


def test_a_capped_rdw_answer_records_gaps_instead_of_values(tmp_path):
    stored = fetched(tmp_path, CappedRegistries())
    cars, car_report = open_data.build_cars(stored, NAMES)
    variant = panda_hybrid(car_report)
    values = metrics(cars, variant["variant_key"])
    for metric in ("length_mm", "body_width_mm", "height_mm", "seats"):
        assert metric not in values
        assert {"metric": metric, "reason": "rdw_rows_truncated"} in variant["gaps"]
    family = next(f for f in car_report["families"] if f["key"] == "it-fiat-panda")
    assert {"metric": "body_style", "reason": "rdw_rows_truncated"} in family["gaps"]

    bikes, bike_report = open_data.build_two_wheelers(stored, TWO_WHEELERS)
    item = liberty(bike_report)
    assert {"metric": "engine_power_kw", "reason": "rdw_rows_truncated"} in item["gaps"]
    assert {"metric": "length_mm", "reason": "rdw_rows_truncated"} in item["gaps"]
    (bike_variant,) = [
        v for v in bikes["variants"] if v["variant_key"] == item["variant_key"]
    ]
    # Rows past the cap could hold a later revision: the fuel is not read either.
    assert bike_variant["fuel"] is None
    assert set(metrics(bikes, item["variant_key"])) == {
        "seat_height_mm",
        "mass_kg",
        "fuel_tank_capacity_liters",
    }
    assert "rdw_rows_truncated" in open_data.GAP_REASONS


# --- Two-wheeler approval codes and fuel evidence ----------------------------------


class ApprovalRegistries(FakeRegistries):
    def __init__(self, rows):
        super().__init__()
        self.rows = rows

    def rdw(self, url, query):
        if open_data.RDW_APPROVAL_ENERGY in url:
            return self.rows
        return super().rdw(url, query)


def approval_row(**fields) -> dict:
    return {"codeenergiebron": "B", "volgnummerrevisieuitvoering": "0", **fields}


@pytest.mark.parametrize(
    ("left", "right", "same"),
    [
        ("00", "0", True),
        ("03", "3", True),
        (None, "0", False),
        ("", "00", False),
        ("  ", "0", False),
        ("0", None, False),
        ("1", "10", False),
    ],
)
def test_approval_codes_match_only_when_both_are_present(left, right, same):
    assert open_data._same_code(left, right) is same


def test_a_missing_approval_code_never_matches_a_zero_code(tmp_path):
    # The Liberty's version is "00"; a row without a version code is not it.
    rows = [approval_row(codevarianttgk="3", maximumnettovermogenogr="99")]
    stored = fetched(tmp_path, ApprovalRegistries(rows))
    bikes, report = open_data.build_two_wheelers(stored, TWO_WHEELERS)
    item = liberty(report)
    assert "engine_power_kw" not in metrics(bikes, item["variant_key"])
    assert {"metric": "engine_power_kw", "reason": "rdw_field_empty"} in item["gaps"]


def test_a_petrol_code_without_power_keeps_its_approval_evidence(tmp_path):
    rows = [approval_row(codevarianttgk="3", codeuitvoeringtgk="0")]
    stored = fetched(tmp_path, ApprovalRegistries(rows))
    bikes, report = open_data.build_two_wheelers(stored, TWO_WHEELERS)
    item = liberty(report)
    (variant,) = [
        v for v in bikes["variants"] if v["variant_key"] == item["variant_key"]
    ]
    assert variant["fuel"] == "petrol" and variant["powertrain_type"] == "ICE"
    power = open_data.two_wheel_power_request(
        TWO_WHEELERS["models"][0], LIBERTY_TAN, "3", "00"
    )
    approval_snapshots = [
        s["id"]
        for s in bikes["snapshots"]
        if s["artifact_path"].endswith(power.artifact_path)
    ]
    assert approval_snapshots
    assert approval_snapshots[0] in variant["evidence_snapshot_ids"]
    assert {"metric": "engine_power_kw", "reason": "rdw_field_empty"} in item["gaps"]


def test_a_motospecdb_slug_listed_twice_is_a_gap():
    entry = TWO_WHEELERS["models"][0]
    bike = {"slug": entry["motospecdb"]["slug"], "brand": "Piaggio"}
    found, reason = open_data.motospecdb_entry(entry, [bike, dict(bike)], 2026)
    assert found is None
    assert reason == "motospecdb_duplicate_slug"
    assert reason in open_data.GAP_REASONS


# --- History: owners by make and approval, and A then B then A ---------------------


def test_every_published_owner_of_an_approval_is_checked():
    refs = [
        {"namespace": "eu-type-approval", "value": "E3*1"},
        {"namespace": "eu-type-approval-variant", "value": "A"},
        {"namespace": "eu-type-approval-version", "value": "1"},
    ]
    previous = {
        "vehicles": [
            {"canonical_key": "it-fiat-panda", "make": "Fiat", "body_style": None},
            # Another make, listed last, shares the approval.
            {"canonical_key": "it-lancia-y", "make": "Lancia", "body_style": None},
        ],
        "variants": [
            {
                "variant_key": "it-fiat-panda.a",
                "vehicle_key": "it-fiat-panda",
                "external_references": refs,
            },
            {
                "variant_key": "it-lancia-y.a",
                "vehicle_key": "it-lancia-y",
                "external_references": refs,
            },
        ],
    }
    fresh = {
        "vehicles": [{"canonical_key": "it-fiat-600", "make": "FIAT"}],
        "variants": [
            {
                "variant_key": "it-fiat-600.a",
                "vehicle_key": "it-fiat-600",
                "external_references": list(reversed(refs)),
            },
        ],
    }
    report = {"identity_review": []}

    held = open_data._held_back(previous, fresh, {}, report)

    assert held == {"it-fiat-600.a"}
    assert report["identity_review"] == [
        {
            "variant_key": "it-fiat-600.a",
            "published_variant_key": "it-fiat-panda.a",
            "reason": "approval_published_under_other_model",
        }
    ]


def test_a_value_may_return_to_an_earlier_observation(run, later):  # noqa: F811
    a, _ = open_data.build_cars(run, NAMES)
    b, _ = open_data.build_cars(later, NAMES)
    ab, _ = open_data.continue_bundle(a, b)

    aba, update = open_data.continue_bundle(ab, a)

    CatalogV2.model_validate(aba)
    assert [r["to"] for r in update["revised"]] == ["365"]
    returned = aba["decisions"][-1]
    assert returned["supersedes_id"] == ab["decisions"][-1]["id"]
    (first_length,) = [
        d
        for d in a["decisions"]
        if d["metric"] == "length_mm" and d["variant_key"] == returned["variant_key"]
    ]
    assert (
        returned["selected_observation_id"] == first_length["selected_observation_id"]
    )
    assert returned["id"] != first_length["id"]
    # The observation is kept once: it is immutable evidence, not a new fact.
    assert aba["observations"] == ab["observations"]
    assert open_data.coverage(aba) == open_data.coverage(ab)
    # And back again: B's observation and every decision stay unique.
    abab, _ = open_data.continue_bundle(aba, b)
    CatalogV2.model_validate(abab)
    assert len(abab["decisions"]) == len(aba["decisions"]) + 1


def test_a_changed_observation_under_a_published_id_is_refused(run):  # noqa: F811
    a, _ = open_data.build_cars(run, NAMES)
    changed = copy.deepcopy(a)
    (observation,) = [
        o
        for o in changed["observations"]
        if o["metric"] == "length_mm" and ".petrol-h." in o["variant_key"]
    ]
    observation.update(value_min="3700", value_max="3700", raw_value="370")

    with pytest.raises(open_data.OpenDataError, match="bump the builder VERSION"):
        open_data.continue_bundle(a, changed)


# --- The build script: safe downloads and publication ------------------------------


def test_redirects_stay_on_https_and_approved_hosts():
    script = load_script()
    handler = script.ApprovedRedirects()
    request = urllib.request.Request("https://opendata.rdw.nl/resource/a.json")
    for target in (
        "http://opendata.rdw.nl/resource/a.json",
        "https://attacker.example/a.json",
        "https://opendata.rdw.nl.attacker.example/a.json",
        "file:///etc/passwd",
    ):
        with pytest.raises(script.UnsafeResponse):
            handler.redirect_request(request, None, 302, "Found", {}, target)
    allowed = handler.redirect_request(
        request, None, 302, "Found", {}, "https://motospecdb.com/api/v1/bikes.json"
    )
    assert allowed.full_url == "https://motospecdb.com/api/v1/bikes.json"
    assert script.ALLOWED_HOSTS == {
        "co2cars.apps.eea.europa.eu",
        "opendata.rdw.nl",
        "motospecdb.com",
    }


def test_the_opener_follows_redirects_only_through_the_approved_handler():
    script = load_script()
    redirects = [
        h
        for h in script._opener().handlers
        if isinstance(h, urllib.request.HTTPRedirectHandler)
    ]
    assert [type(h) for h in redirects] == [script.ApprovedRedirects]


class FakeResponse(io.BytesIO):
    def __init__(self, data, url, headers=None):
        super().__init__(data)
        self.url, self.headers = url, headers or {}

    def geturl(self):
        return self.url


class FakeOpener:
    def __init__(self, response):
        self.response, self.calls = response, 0

    def open(self, request, timeout):
        self.calls += 1
        return self.response


def test_http_get_caps_the_body_and_checks_the_final_address(monkeypatch):
    script = load_script()
    monkeypatch.setattr(script.time, "sleep", lambda seconds: None)
    url = "https://opendata.rdw.nl/resource/a.json"

    def get(response, limit=None):
        opener = FakeOpener(response)
        monkeypatch.setattr(script, "_opener", lambda: opener)
        if limit is not None:
            monkeypatch.setattr(script, "MAX_RESPONSE_BYTES", limit)
        return opener, lambda: script.http_get(url)

    _, call = get(FakeResponse(b"[1]", url))
    assert call() == b"[1]"
    opener, call = get(FakeResponse(b"x" * 11, url), limit=10)
    with pytest.raises(script.UnsafeResponse, match="exceeds"):
        call()
    assert opener.calls == 1  # never retried
    _, call = get(FakeResponse(b"[]", url, {"Content-Length": "999"}), limit=10)
    with pytest.raises(script.UnsafeResponse, match="declares"):
        call()
    _, call = get(FakeResponse(b"[]", "http://opendata.rdw.nl/resource/a.json"))
    with pytest.raises(script.UnsafeResponse):
        call()
    with pytest.raises(script.UnsafeResponse):
        script.http_get("http://opendata.rdw.nl/resource/a.json")


def test_previous_must_hold_a_published_bundle(run, tmp_path, capsys):  # noqa: F811
    assert cli_build(tmp_path, run.root, NAMES, previous=tmp_path / "missing") == 1
    assert "not a run folder" in capsys.readouterr().err
    (tmp_path / "empty-run").mkdir()
    assert cli_build(tmp_path, run.root, NAMES, previous=tmp_path / "empty-run") == 1
    assert "holds no" in capsys.readouterr().err
    assert not (run.root / "cars.catalog-v2.json").exists()


def test_a_rebuild_without_cars_removes_the_obsolete_car_bundle(run, tmp_path):  # noqa: F811
    assert cli_build(tmp_path, run.root, NAMES) == 0
    assert (run.root / "cars.catalog-v2.json").exists()

    assert cli_build(tmp_path, run.root, {"families": []}) == 0

    assert not (run.root / "cars.catalog-v2.json").exists()
    assert (run.root / "two-wheelers.catalog-v2.json").exists()
    assert not list(run.root.glob(".*.tmp"))
