"""The open-data builder runs here against a fake registry; no test touches the network."""

import importlib.util
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from app.ingestion import open_data
from app.ingestion.catalog_v2 import CatalogV2
from app.ingestion.catalog_v2_writer import verify_artifacts

NAMES = {
    "families": [
        {"make": "Fiat", "model": "Panda", "eea": [{"mk": "FIAT", "names": ["PANDA"]}]},
        {"make": "BMW", "model": "X1", "eea": [{"mk": "BMW", "prefixes": ["X1 "]}]},
        {"make": "BMW", "model": "X1 M", "eea": [{"mk": "BMW", "names": ["X1 M35I"]}]},
    ]
}
TWO_WHEELERS = {
    "models": [
        {
            "slug": "piaggio-liberty-125",
            "make": "Piaggio",
            "model": "Liberty 125",
            "vehicle_type": "scooter",
            "rdw_merk": "PIAGGIO",
            "rdw_handelsbenaming": "LIBERTY 125 ABS",
            "displacement_cc": 124,
        },
        {
            "slug": "ghost-125",
            "make": "Ghost",
            "model": "125",
            "vehicle_type": "motorcycle",
            "rdw_merk": "GHOST",
            "rdw_handelsbenaming": "NOT REGISTERED",
            "displacement_cc": 125,
        },
    ]
}


def values(counts: dict, other: int = 0) -> dict:
    return {
        "doc_count_error_upper_bound": 0,
        "sum_other_doc_count": other,
        "buckets": [{"key": k, "doc_count": n} for k, n in counts.items()],
    }


def version(key: list, registrations: int, **fields) -> dict:
    empty = {name: values({}) for name in open_data.EEA_STATS}
    return {"key": key, "doc_count": registrations, **empty, **fields}


PANDA_HYBRID = version(
    ["petrol", "H", "E3*2007/46*0064*72", "PYD1B", "AA4"],
    1000,
    mass=values({1045: 1000}),
    # Eight registrations at twice the power are an entry error, not a second engine.
    power=values({52: 992, 150: 8}),
    displacement=values({999: 1000}),
    co2=values({108: 800, 110: 195, 190: 5}),
    consumption=values({4.800000190734863: 800, 4.900000095367432: 200}),
)
PANDA_LPG = version(
    ["lpg", "B", "E3*2007/46*0064*70", "PYL1B", "BB1"],
    300,
    mass=values({1080: 300}),
    power=values({51: 300}),
    displacement=values({1242: 300}),
    co2=values({115: 300}),
)
PANDA_METHANE = version(["ng", "M", "E3*2007/46*0064*60", "PYM", "C"], 200)
PANDA_RARE_DIESEL = version(["diesel", "M", "E3*2007/46*0064*50", "PYD", "D"], 10)
X1_PLUG_IN = version(
    ["petrol/electric", "P", "E1*2018/858*00153*06", "21EF", "EAW50000"],
    400,
    mass=values({1935: 400}),
    power=values({100: 400}),
    displacement=values({1499: 400}),
    co2=values({16: 300, 22: 100}),
    consumption=values({0.699999988079071: 400}),
    electric_consumption=values({173: 400}),
)
X1_ELECTRIC = version(
    ["electric", "E", "E1*2018/858*00160*03", "61EF", "BEV1"],
    100,
    mass=values({2010: 100}),
    power=values({150: 100}),
    co2=values({0: 100}),
    electric_consumption=values({155: 100}),
    electric_range=values({474: 80, 462: 20}),
)
EEA_FAMILIES = {
    "PANDA": [PANDA_HYBRID, PANDA_LPG, PANDA_METHANE, PANDA_RARE_DIESEL],
    "X1 SDRIVE18I": [X1_PLUG_IN, X1_ELECTRIC],
}
RDW_CARS = {
    "e3*2007/46*0064*72": [
        {
            "merk": "FIAT",
            "lengte": "365",
            "breedte": "164",
            "hoogte_voertuig": "155",
            "aantal_zitplaatsen": "4",
            "n": "787",
        },
        # One registration with the height typed into the width column.
        {
            "merk": "FIAT",
            "lengte": "365",
            "breedte": "155",
            "hoogte_voertuig": "155",
            "aantal_zitplaatsen": "4",
            "n": "1",
        },
    ],
    # The registry lists another make under this approval: never trust it.
    "e3*2007/46*0064*70": [
        {
            "merk": "TESLA",
            "lengte": "500",
            "breedte": "200",
            "hoogte_voertuig": "140",
            "aantal_zitplaatsen": "5",
            "n": "9",
        }
    ],
    "e1*2018/858*00153*06": [
        {
            "merk": "BMW",
            "lengte": "450",
            "breedte": "185",
            "aantal_zitplaatsen": "5",
            "n": "40",
        }
    ],
}


class FakeRegistries:
    def __init__(self):
        self.calls = 0

    def __call__(self, url: str) -> bytes:
        self.calls += 1
        query = parse_qs(urlsplit(url).query)
        if "source" in query:
            return json.dumps(self.eea(json.loads(query["source"][0]))).encode()
        return json.dumps(self.rdw(url, query)).encode()

    def eea(self, source: dict) -> dict:
        if "Cn" in json.dumps(source["aggs"]):
            buckets = [
                {"key": ["FIAT", "PANDA"], "doc_count": 1510},
                {"key": ["BMW", "X1 SDRIVE18I"], "doc_count": 500},
                {"key": ["BMW", "X1 M35I"], "doc_count": 40},
                {"key": ["BMW", "ISETTA"], "doc_count": 7},
            ]
        else:
            names = json.dumps(source["query"])
            groups: dict[tuple, dict] = {}
            for name, versions in EEA_FAMILIES.items():
                for item in versions if f'"{name}"' in names else []:
                    group = groups.setdefault(
                        tuple(item["key"][:2]),
                        {"key": item["key"][:2], "doc_count": 0, "v": {"buckets": []}},
                    )
                    group["doc_count"] += item["doc_count"]
                    group["v"]["buckets"].append({**item, "key": item["key"][2:]})
            return {
                "aggregations": {"g": values({}) | {"buckets": list(groups.values())}}
            }
        return {"aggregations": {"v": {"buckets": buckets}}}

    def rdw(self, url: str, query: dict) -> list:
        where = query["$where"][0]
        if open_data.RDW_APPROVAL_ENERGY in url:
            assert "e13*168/2013*02373*01" in where
            return [
                {
                    "codevarianttgk": "3",
                    "codeuitvoeringtgk": "0",
                    "codeenergiebron": "B",
                    "volgnummerrevisieuitvoering": "0",
                    "maximumnettovermogenogr": "7.00",
                    "maximumnettovermogenbgr": "7.00",
                },
                {
                    "codevarianttgk": "3",
                    "codeuitvoeringtgk": "0",
                    "codeenergiebron": "B",
                    "volgnummerrevisieuitvoering": "1",
                    "maximumnettovermogenogr": "8.10",
                    "maximumnettovermogenbgr": "8.10",
                },
                {
                    "codevarianttgk": "4",
                    "codeuitvoeringtgk": "0",
                    "codeenergiebron": "B",
                    "volgnummerrevisieuitvoering": "0",
                    "maximumnettovermogenogr": "11.00",
                    "maximumnettovermogenbgr": "11.00",
                },
            ]
        if "handelsbenaming='LIBERTY 125 ABS'" in where:
            assert "cilinderinhoud=124" in where
            return [
                {
                    "typegoedkeuringsnummer": "e13*168/2013*02373*01",
                    "variant": "3",
                    "uitvoering": "00",
                    "n": "14",
                },
                {
                    "typegoedkeuringsnummer": "e1*168/2013*00245*03",
                    "variant": "1",
                    "uitvoering": "00",
                    "n": "12",
                },
            ]
        if "handelsbenaming=" in where:
            return []
        if "merk='PIAGGIO'" in where:
            return [
                {
                    "lengte": "195",
                    "breedte": "69",
                    "hoogte_voertuig": "111",
                    "aantal_zitplaatsen": "2",
                    "massa_rijklaar": "128",
                    "cilinderinhoud": "124",
                    "n": "14",
                }
            ]
        return next((rows for tan, rows in RDW_CARS.items() if tan in where), [])


@pytest.fixture
def run(tmp_path):
    run = open_data.Run(tmp_path / "run")
    registries = FakeRegistries()
    fetched = open_data.fetch(
        run,
        NAMES,
        TWO_WHEELERS,
        registries,
        now=lambda: datetime(2026, 11, 23, tzinfo=UTC),
    )
    assert fetched == registries.calls == len(run.manifest)
    return run


def facts(bundle: dict, variant_part: str) -> dict:
    return {
        o["metric"]: o
        for o in bundle["observations"]
        if variant_part in o["variant_key"]
    }


def test_fetch_is_resumable_and_build_never_touches_the_network(run):
    def offline(url):
        raise AssertionError("everything is already stored")

    assert open_data.fetch(run, NAMES, TWO_WHEELERS, offline) == 0
    first = open_data.build_cars(run, NAMES)
    assert first == open_data.build_cars(open_data.Run(run.root), NAMES)
    bundle = CatalogV2.model_validate(first[0])
    verify_artifacts(bundle, run.artifacts)
    assert {s.ranking_permission for s in bundle.sources} == {"manual_validation_only"}


def test_names_map_by_exact_rule_first_and_unmapped_names_are_reported(run):
    families, unmapped = open_data.resolve_families(
        NAMES, run.read(open_data.names_request())
    )
    assert [(f["model"], f["registrations"]) for f in families] == [
        ("Panda", 1510),
        ("X1", 500),
        ("X1 M", 40),
    ]
    assert unmapped == [{"make": "BMW", "name": "ISETTA", "registrations": 7}]


def test_car_values_drop_entry_errors_and_keep_real_spread(run):
    bundle, report = open_data.build_cars(run, NAMES)
    hybrid = facts(bundle, "it-fiat-panda.petrol-h.")
    assert (
        hybrid["engine_power_kw"]["value_min"],
        hybrid["engine_power_kw"]["value_max"],
    ) == ("52", "52")
    assert (hybrid["co2_g_km"]["value_min"], hybrid["co2_g_km"]["value_max"]) == (
        "108",
        "110",
    )
    assert hybrid["co2_g_km"]["context"]["cycle"] == "combined"
    assert hybrid["liquid_consumption_l_100km"]["raw_value"] == "4.8..4.9"
    assert hybrid["mass_kg"]["context"]["method"] == "mass_in_running_order"
    # Centimetres become millimetres; the stray width of one registration is dropped.
    assert (
        hybrid["body_width_mm"]["value_min"]
        == hybrid["body_width_mm"]["value_max"]
        == "1640"
    )
    assert hybrid["body_width_mm"]["raw_value"] == "164"
    assert hybrid["body_width_mm"]["raw_unit"] == "cm"
    assert '"155": 1' in hybrid["body_width_mm"]["evidence_excerpt"]
    assert hybrid["seats"]["value_min"] == "4"
    variants = {v["variant_key"].split(".")[1]: v for v in bundle["variants"]}
    # EEA cannot tell a mild from a full hybrid, so the type stays unknown.
    assert variants["petrol-h"]["powertrain_type"] is None
    assert variants["petrol-h"]["fuel"] == "petrol"
    assert variants["lpg-b"]["fuel"] == "petrol_lpg"
    assert {"namespace": "eu-type-approval", "value": "E3*2007/46*0064*72"} in variants[
        "petrol-h"
    ]["external_references"]
    panda = report["families"][0]
    assert {(s["fuel"], s["reason"]) for s in panda["skipped_powertrains"]} == {
        ("ng", "fuel_unsupported"),
        ("diesel", "below_share_threshold"),
    }
    lpg = next(v for v in panda["variants"] if v["fuel"] == "lpg")
    # The registry row under this approval is another make: no dimensions at all.
    assert lpg["rdw_match"] == "none"
    assert {"metric": "co2_g_km", "reason": "bifuel_value_ambiguous"} in lpg["gaps"]
    assert "length_mm" not in facts(bundle, "it-fiat-panda.lpg-b.")
    assert panda["gaps"] == []


def test_plug_in_and_electric_cars_carry_their_own_context(run):
    bundle, report = open_data.build_cars(run, NAMES)
    plug_in = facts(bundle, "it-bmw-x1.petrol-electric-p.")
    context = plug_in["co2_g_km"]["context"]
    assert (context["procedure"], context["cycle"], context["battery_condition"]) == (
        "WLTP",
        "weighted_combined",
        "weighted",
    )
    assert "electric_consumption_kwh_100km" not in plug_in
    assert "height_mm" not in plug_in
    electric = facts(bundle, "it-bmw-x1.electric-e.")
    assert electric["co2_g_km"]["value_max"] == "0"
    assert (
        electric["electric_range_km"]["value_min"],
        electric["electric_range_km"]["value_max"],
    ) == ("462", "474")
    assert electric["electric_consumption_kwh_100km"]["value_min"] == "15.5"
    assert electric["electric_consumption_kwh_100km"]["raw_unit"] == "Wh/km"
    assert "engine_power_kw" not in electric and "system_power_kw" not in electric
    x1 = report["families"][1]
    gaps = {
        (v["fuel_mode"], g["metric"], g["reason"])
        for v in x1["variants"]
        for g in v["gaps"]
    }
    assert ("P", "height_mm", "rdw_field_empty") in gaps
    assert ("E", "system_power_kw", "bev_power_definition_unknown") in gaps
    assert ("E", "length_mm", "rdw_no_exact_version") in gaps
    # Two approvals under one name may be two generations: a person must look.
    assert x1["gaps"] == [{"metric": "generation", "reason": "several_type_approvals"}]


@pytest.mark.parametrize(
    "counts,unlisted,single,expected",
    [
        ({}, 0, True, "empty"),
        ({Decimal(74): 1026, Decimal(150): 8}, 0, True, (Decimal(74), Decimal(74))),
        ({Decimal(100): 60, Decimal(150): 40}, 0, True, "registry_values_disagree"),
        ({Decimal(100): 60, Decimal(150): 40}, 0, False, (Decimal(100), Decimal(150))),
        ({Decimal(100): 60, Decimal(104): 40}, 0, True, (Decimal(100), Decimal(104))),
        ({Decimal(100): 60}, 40, False, "too_many_values"),
        ({Decimal(v): 1 for v in range(100, 200)}, 0, False, "too_many_values"),
    ],
)
def test_settle(counts, unlisted, single, expected):
    assert open_data.settle(counts, unlisted=unlisted, single_valued=single) == expected


def test_two_wheelers_match_approval_codes_without_leading_zeros(run):
    bundle, report = open_data.build_two_wheelers(run, TWO_WHEELERS)
    CatalogV2.model_validate(bundle)
    assert [v["canonical_key"] for v in bundle["vehicles"]] == [
        "it-piaggio-liberty-125"
    ]
    assert bundle["vehicles"][0]["vehicle_type"] == "scooter"
    liberty = facts(bundle, "it-piaggio-liberty-125.")
    # Version "00" in the registrations is "0" in the approvals; the last revision wins.
    assert liberty["engine_power_kw"]["value_min"] == "8.1"
    assert liberty["length_mm"]["value_min"] == "1950"
    assert liberty["mass_kg"]["value_min"] == "128"
    assert bundle["variants"][0]["fuel"] == "petrol"
    assert report["models"][1]["gaps"] == [
        {"metric": "identity", "reason": "rdw_not_found"}
    ]


def test_gap_register_lists_every_missing_field(run):
    _, cars = open_data.build_cars(run, NAMES)
    _, two_wheelers = open_data.build_two_wheelers(run, TWO_WHEELERS)
    register = open_data.gap_register(run, cars, two_wheelers)
    assert register["scope"] == {
        "market": "IT",
        "eea_year": open_data.EEA_YEAR,
        "car_families": 3,
        "car_variants": 4,
        "two_wheelers": 2,
    }
    gaps = {
        (g["model"], g["variant"], g["field"], g["reason"]) for g in register["gaps"]
    }
    assert ("Fiat Panda", "ng (M)", "powertrain", "fuel_unsupported") in gaps
    assert ("BMW X1", None, "generation", "several_type_approvals") in gaps
    assert ("BMW X1 M", None, "identity", "no_supported_powertrain") in gaps
    assert ("Ghost 125", None, "identity", "rdw_not_found") in gaps
    assert register["unmapped_names"][0]["name"] == "ISETTA"
    assert {g["reason"] for g in register["gaps"]} <= open_data.GAP_REASONS.keys()
    assert {
        g["reason"] for g in register["dataset_gaps"]
    } <= open_data.GAP_REASONS.keys()
    markdown = open_data.gap_register_markdown(register)
    assert "| car | Fiat Panda | ng (M) | powertrain | fuel_unsupported |" in markdown
    assert "| BMW | ISETTA | 7 |" in markdown


def test_changed_or_non_json_evidence_is_rejected(run):
    request = open_data.names_request()
    (run.artifacts / request.artifact_path).write_text("{}")
    with pytest.raises(open_data.OpenDataError, match="changed on disk"):
        open_data.Run(run.root).read(request)
    with pytest.raises(json.JSONDecodeError):
        run.store(request, b"<html>Access Denied</html>", datetime.now(UTC))


def test_a_version_that_is_a_small_slice_of_its_powertrain_is_flagged():
    family = {"key": "audi-q3", "registrations": 1000}
    fragmented = version(
        ["E1*2007/46*1900*34", "SDXPAF1", "A"], 60, mass=values({1600: 60})
    )
    whole = version(
        ["E1*2007/46*1900*34", "SDXDBF1", "B"], 300, mass=values({1500: 300})
    )
    response = {
        "aggregations": {
            "g": values({})
            | {
                "buckets": [
                    # 700 registrations, yet the best-selling version has only 60.
                    {
                        "key": ["diesel", "M"],
                        "doc_count": 700,
                        "v": {"buckets": [fragmented]},
                    },
                    {
                        "key": ["petrol", "M"],
                        "doc_count": 300,
                        "v": {"buckets": [whole]},
                    },
                    {"key": ["petrol", "H"], "doc_count": 80, "v": {"buckets": []}},
                ]
            }
        }
    }
    kept, skipped = open_data.powertrain_groups(family, response)
    assert [(g["fuel"], g["registrations"]) for g in kept] == [
        ("diesel", 700),
        ("petrol", 300),
    ]
    assert kept[0]["versions"][0]["key"] == [
        "diesel",
        "M",
        "E1*2007/46*1900*34",
        "SDXPAF1",
        "A",
    ]
    assert skipped == [
        {
            "fuel": "petrol",
            "mode": "H",
            "registrations": 80,
            "reason": "no_type_approval_version",
        }
    ]
    truncated = {"aggregations": {"g": values({}, other=5) | {"buckets": []}}}
    with pytest.raises(open_data.OpenDataError, match="too many powertrains"):
        open_data.powertrain_groups(family, truncated)


def test_cli_builds_bundles_and_the_register_from_a_stored_run(run, tmp_path, capsys):
    path = Path(__file__).resolve().parents[1] / "scripts/build_open_data_catalog.py"
    spec = importlib.util.spec_from_file_location("build_open_data_catalog", path)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    names, two_wheelers = tmp_path / "names.json", tmp_path / "two-wheelers.json"
    names.write_text(json.dumps(NAMES))
    two_wheelers.write_text(json.dumps(TWO_WHEELERS))
    arguments = ["--run-dir", str(run.root), "--names", str(names)]
    arguments += [
        "--two-wheelers",
        str(two_wheelers),
        "--register-dir",
        str(tmp_path / "docs"),
    ]
    assert script.main(["build", *arguments]) == 0
    assert "cars: 2 vehicles, 4 variants" in capsys.readouterr().out
    CatalogV2.model_validate_json((run.root / "cars.catalog-v2.json").read_text())
    CatalogV2.model_validate_json(
        (run.root / "two-wheelers.catalog-v2.json").read_text()
    )
    register = json.loads((tmp_path / "docs/open-data-gaps.json").read_text())
    assert register["scope"]["car_variants"] == 4
    assert (
        (tmp_path / "docs/open-data-gaps.md")
        .read_text()
        .startswith("# Open-data import")
    )
    # A run with nothing stored fails with one clear line instead of a traceback.
    assert (
        script.main(["build", "--run-dir", str(tmp_path / "empty"), *arguments[2:]])
        == 1
    )
    assert "fetch first" in capsys.readouterr().err
