"""The open-data builder runs here against a fake registry; no test touches the network."""

import importlib.util
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from test_catalog_v2_publication import conn, publish  # noqa: F401

from app.ingestion import open_data
from app.ingestion.catalog import CatalogValidationError
from app.ingestion.catalog_v2 import CatalogV2
from app.ingestion.catalog_v2_writer import (
    publish_catalog_v2,
    stage_catalog_v2,
    verify_artifacts,
)

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
            "motospecdb": "piaggio-liberty-125-test",
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


def bike(slug: str, model: str, years: str, codes: list, **ergonomics) -> dict:
    return {
        "slug": slug,
        "brand": "Piaggio",
        "model": model,
        "years_covered": years,
        "chassis_codes": codes,
        "ergonomics": ergonomics,
        "manual_source_citation": {"en": f"{model} owner's manual (synthetic)"},
        "urls": {"en": f"https://example.com/bikes/{slug}/"},
    }


MOTOSPECDB = {
    "license": "CC BY 4.0 (synthetic fixture)",
    "bikes": [
        bike(
            "piaggio-liberty-125-test",
            "Liberty 125 (Test Gen)",
            "2021\u2013Present",
            ["TST1"],
            seat_height_mm=790,
            seat_arch_factor="narrow",
            wet_weight_kg=121.5,
            fuel_tank_l=6,
            est_consumption_km_l=40,
        )
    ],
}
# The registered bodywork code per type approval (RDW "inrichting").
RDW_BODIES = {
    "e3*2007/46*0064*72": [
        {"merk": "FIAT", "inrichting": "sedan", "n": "780"},
        # One typing error in eighty is not a second body.
        {"merk": "FIAT", "inrichting": "hatchback", "n": "8"},
    ],
    "e1*2018/858*00153*06": [{"merk": "BMW", "inrichting": "stationwagen", "n": "40"}],
}


class FakeRegistries:
    def __init__(self):
        self.calls = 0

    def __call__(self, url: str) -> bytes:
        self.calls += 1
        if url == open_data.MOTOSPECDB_URL:
            return json.dumps(MOTOSPECDB).encode()
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
        if "inrichting" in query["$select"][0]:
            return next((r for tan, r in RDW_BODIES.items() if tan in where), [])
        if open_data.RDW_FUEL in url:
            # The registry publishes the electric motor per registered vehicle.
            assert "brandstof_omschrijving='Elektriciteit'" in where
            return [
                {"kenteken": plate, "netto_max_vermogen_elektrisch": "2.07"}
                for plate in ("H001AA", "H002AA")
                if plate in where
            ]
        if query["$select"][0] == "kenteken":
            assert "e3*2007/46*0064*72" in where
            return [{"kenteken": "H001AA"}, {"kenteken": "H002AA"}]
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
    verify_artifacts(bundle, run.artifact_root)
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
    # EEA cannot tell a mild from a full hybrid; the registered motor power can.
    assert variants["petrol-h"]["powertrain_type"] == "MHEV"
    assert len(variants["petrol-h"]["evidence_snapshot_ids"]) == 4
    assert report["families"][0]["variants"][0]["electric_motor_kw"] == ["2.07"]
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
    # The hybrid's registrations say sedan, but the LPG variant states no body.
    hybrid = next(v for v in panda["variants"] if v["fuel_mode"] == "H")
    assert hybrid["rdw_body_codes"] == {"hatchback": 8, "sedan": 780}
    assert hybrid["rdw_body_code"] == "sedan"
    assert panda["gaps"] == [{"metric": "body_style", "reason": "rdw_no_exact_version"}]
    assert bundle["vehicles"][0]["body_style"] is None


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
    assert x1["gaps"] == [
        {"metric": "body_style", "reason": "rdw_no_exact_version"},
        {"metric": "generation", "reason": "several_type_approvals"},
    ]


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


@pytest.mark.parametrize(
    ("motors", "expected"),
    [
        (["2.07", "2.07"], "MHEV"),
        (["15.60", None], "MHEV"),
        (["36.00", "51.00"], "HEV"),
        (["24.60"], None),  # between the limits: a person decides
        (["15.60", "32.00"], None),  # the sample disagrees
        ([None], None),
        ([], None),
    ],
)
def test_hybrid_kind_follows_the_registered_motor_power(motors, expected):
    rows = [{"netto_max_vermogen_elektrisch": m} if m else {} for m in motors]
    assert open_data.hybrid_kind(rows)[0] == expected


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
    masses = {
        o["context"]["method"]: o["value_min"]
        for o in bundle["observations"]
        if o["metric"] == "mass_kg"
    }
    assert masses == {"mass_in_running_order": "128", "wet": "121.5"}
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


class LaterRegistries(FakeRegistries):
    """A later download: every EEA answer differs in its timing, one Panda grew."""

    def __call__(self, url: str) -> bytes:
        data = json.loads(super().__call__(url))
        if isinstance(data, dict):
            data["took"] = self.calls
        for row in data if isinstance(data, list) else []:
            if row.get("merk") == "FIAT":
                row["lengte"] = "368"
        return json.dumps(data).encode()


@pytest.fixture
def later(run):
    later = open_data.Run(run.root.parent / "run-later")
    open_data.fetch(
        later,
        NAMES,
        TWO_WHEELERS,
        LaterRegistries(),
        now=lambda: datetime(2026, 12, 23, tzinfo=UTC),
    )
    return later


def test_a_later_run_continues_the_earlier_bundle(run, later):
    first, _ = open_data.build_cars(run, NAMES)
    fresh, _ = open_data.build_cars(later, NAMES)
    # Rebuilt alone, the later bundle rests every identity on new evidence.
    assert fresh["vehicles"] != first["vehicles"]

    merged, update = open_data.continue_bundle(first, fresh)

    assert merged["vehicles"] == first["vehicles"]
    assert merged["variants"] == first["variants"]
    assert merged["decisions"][:-1] == first["decisions"]
    revised = merged["decisions"][-1]
    (old,) = [
        d
        for d in first["decisions"]
        if d["metric"] == "length_mm" and "it-fiat-panda.petrol-h." in d["variant_key"]
    ]
    assert revised["supersedes_id"] == old["id"]
    assert update["revised"] == [
        {
            "variant_key": old["variant_key"],
            "metric": "length_mm",
            "from": "365",
            "to": "368",
        }
    ]
    assert update["unchanged"] == len(first["decisions"]) - 1
    assert update["new_variants"] == update["identity_differs"] == []
    # Evidence of both runs resolves from their common folder.
    verify_artifacts(CatalogV2.model_validate(merged), run.artifact_root)
    assert open_data.continue_bundle(merged, fresh)[0] == merged
    # A model that enters the list later is added next to the published ones.
    panda_only, _ = open_data.build_cars(run, {"families": NAMES["families"][:1]})
    grown, update = open_data.continue_bundle(panda_only, fresh)
    assert update["new_vehicles"] == ["it-bmw-x1"]
    assert [v["canonical_key"] for v in grown["vehicles"]] == [
        "it-fiat-panda",
        "it-bmw-x1",
    ]


def test_a_continued_bundle_publishes_over_the_earlier_one(conn, run, later):  # noqa: F811
    first, _ = open_data.build_cars(run, NAMES)
    fresh, _ = open_data.build_cars(later, NAMES)
    merged, _ = open_data.continue_bundle(first, fresh)
    root = run.artifact_root
    publish(conn, first, root)

    def length():
        return conn.execute(
            "SELECT f.value_min FROM catalog_current_facts f "
            "JOIN vehicle_specs s ON s.id = f.spec_id "
            "WHERE f.metric = 'length_mm' "
            "AND s.variant_key LIKE 'it-fiat-panda.petrol-h.%'"
        ).fetchone()["value_min"]

    assert length() == 3650
    # The rebuilt bundle alone is refused: it would rewrite published identities.
    batch = stage_catalog_v2(conn, CatalogV2.model_validate(fresh), artifact_root=root)
    with pytest.raises(CatalogValidationError, match="Published identity differs"):
        publish_catalog_v2(conn, batch, artifact_root=root)
    assert length() == 3650

    publish(conn, merged, root)
    assert length() == 3680
    batch = stage_catalog_v2(conn, CatalogV2.model_validate(merged), artifact_root=root)
    assert publish_catalog_v2(conn, batch, artifact_root=root) == "unchanged"


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


# --- Body style from the registered EU bodywork code -------------------------------

LUMO_NAMES = {
    "families": [
        {"make": "Lumo", "model": "Arc", "eea": [{"mk": "LUMO", "names": ["ARC"]}]}
    ]
}
LUMO_ARC = version(
    ["petrol", "M", "E9*2018/858*00901*01", "AR1", "A1"], 900, mass=values({1200: 900})
)


class BodyRegistries(FakeRegistries):
    """One invented car, whose registrations name the given bodywork code."""

    def __init__(self, body: str):
        super().__init__()
        self.body = body

    def eea(self, source: dict) -> dict:
        if "Cn" in json.dumps(source["aggs"]):
            buckets = [{"key": ["LUMO", "ARC"], "doc_count": 900}]
            return {"aggregations": {"v": {"buckets": buckets}}}
        group = {
            "key": ["petrol", "M"],
            "doc_count": 900,
            "v": {"buckets": [{**LUMO_ARC, "key": LUMO_ARC["key"][2:]}]},
        }
        return {"aggregations": {"g": values({}) | {"buckets": [group]}}}

    def rdw(self, url: str, query: dict) -> list:
        if "e9*2018/858*00901*01" not in query["$where"][0]:
            return super().rdw(url, query)
        if "inrichting" in query["$select"][0]:
            return [{"merk": "LUMO", "inrichting": self.body, "n": "50"}]
        dimensions = {"lengte": "430", "breedte": "180", "hoogte_voertuig": "150"}
        return [{"merk": "LUMO", **dimensions, "aantal_zitplaatsen": "5", "n": "50"}]


def lumo(tmp_path, folder: str, body: str, day: int) -> open_data.Run:
    run = open_data.Run(tmp_path / folder)
    open_data.fetch(
        run,
        LUMO_NAMES,
        TWO_WHEELERS,
        BodyRegistries(body),
        now=lambda: datetime(2026, 11, day, tzinfo=UTC),
    )
    return run


@pytest.mark.parametrize(
    "rows,expected",
    [
        ([{"merk": "FIAT", "inrichting": "sedan", "n": "99"}], "sedan"),
        # Under 2% of the registrations is a typing error, not a second body.
        (
            [
                {"merk": "FIAT", "inrichting": "sedan", "n": "99"},
                {"merk": "FIAT", "inrichting": "hatchback", "n": "1"},
            ],
            "sedan",
        ),
        # One version registered as two bodies: not guessed.
        (
            [
                {"merk": "FIAT", "inrichting": "sedan", "n": "60"},
                {"merk": "FIAT", "inrichting": "stationwagen", "n": "40"},
            ],
            None,
        ),
        # Rows of another make under the same approval do not count.
        ([{"merk": "TESLA", "inrichting": "sedan", "n": "9"}], None),
        ([], None),
    ],
)
def test_registered_body_drops_rare_codes_and_other_makes(rows, expected):
    assert open_data.registered_body("Fiat", rows)[0] == expected


def body_variant(code, match="exact", codes=None, snapshot="s-body"):
    return {
        "rdw_match": match,
        "rdw_body_code": code,
        "rdw_body_codes": {code: 1} if codes is None and code else (codes or {}),
        "rdw_body_snapshot": snapshot,
    }


@pytest.mark.parametrize(
    "variants,reason",
    [
        ([body_variant("sedan"), body_variant("sedan", snapshot="s-2")], None),
        (
            [body_variant("sedan"), body_variant(None, match="none")],
            "rdw_no_exact_version",
        ),
        (
            [body_variant("sedan"), body_variant("stationwagen")],
            "rdw_body_styles_differ",
        ),
        (
            [body_variant(None, codes={"sedan": 60, "stationwagen": 40})],
            "rdw_body_styles_differ",
        ),
        # The EU code for a hatchback also covers crossovers: no catalogue body.
        ([body_variant("hatchback")], "rdw_body_code_not_catalogue"),
        ([body_variant(None)], "rdw_field_empty"),
    ],
)
def test_a_vehicle_gets_a_body_only_when_every_variant_states_the_same(
    variants, reason
):
    vehicle = {"body_style": None, "evidence_snapshot_ids": ["s-eea"]}
    entry = {"variants": variants, "gaps": []}
    open_data._vehicle_body(vehicle, entry)
    if reason is None:
        assert vehicle["body_style"] == entry["body_style"] == "sedan"
        # The snapshots that state the body follow the identity evidence.
        assert vehicle["evidence_snapshot_ids"] == ["s-eea", "s-body", "s-2"]
        assert entry["gaps"] == []
    else:
        assert vehicle == {"body_style": None, "evidence_snapshot_ids": ["s-eea"]}
        assert entry["gaps"] == [{"metric": "body_style", "reason": reason}]


def test_a_later_run_fills_an_unknown_body_style_on_published_data(conn, tmp_path):  # noqa: F811
    first, first_report = open_data.build_cars(
        lumo(tmp_path, "run", "stationwagen", 23), LUMO_NAMES
    )
    assert first["vehicles"][0]["body_style"] is None
    assert first_report["families"][0]["gaps"] == [
        {"metric": "body_style", "reason": "rdw_body_code_not_catalogue"}
    ]
    later = lumo(tmp_path, "run-later", "sedan", 24)
    fresh, _ = open_data.build_cars(later, LUMO_NAMES)
    assert fresh["vehicles"][0]["body_style"] == "sedan"

    merged, update = open_data.continue_bundle(first, fresh)

    assert update["body_style_filled"] == ["it-lumo-arc"]
    assert update["identity_differs"] == []
    (vehicle,) = merged["vehicles"]
    body = later.evidence_path(
        open_data.rdw_body_request("E9*2018/858*00901*01", "AR1", "A1")
    )
    snapshots = {s["id"]: s["artifact_path"] for s in merged["snapshots"]}
    # The published evidence stays first; only the snapshot stating the body is new.
    assert (
        vehicle["evidence_snapshot_ids"][:-1]
        == first["vehicles"][0]["evidence_snapshot_ids"]
    )
    assert snapshots[vehicle["evidence_snapshot_ids"][-1]] == body
    assert merged["variants"] == first["variants"]
    # Once known, a body style is never overwritten by a later run.
    other = {**fresh, "vehicles": [{**fresh["vehicles"][0], "body_style": "wagon"}]}
    assert open_data.continue_bundle(merged, other)[1]["identity_differs"] == [
        "it-lumo-arc"
    ]

    root = tmp_path
    publish(conn, first, root)
    publish(conn, merged, root)
    row = conn.execute(
        "SELECT body_style, identity_evidence FROM vehicles "
        "WHERE canonical_key = 'it-lumo-arc'"
    ).fetchone()
    assert row["body_style"] == "sedan"
    assert str(row["identity_evidence"][-1]) == vehicle["evidence_snapshot_ids"][-1]
    batch = stage_catalog_v2(conn, CatalogV2.model_validate(merged), artifact_root=root)
    assert publish_catalog_v2(conn, batch, artifact_root=root) == "unchanged"


# --- Two-wheel facts from MotoSpecDB ----------------------------------------------


def test_motospecdb_supplies_measured_two_wheel_facts_only(run):
    bundle, report = open_data.build_two_wheelers(run, TWO_WHEELERS)
    liberty = [
        o
        for o in bundle["observations"]
        if o["snapshot_id"]
        in {s["id"] for s in bundle["snapshots"] if s["source_key"] == "motospecdb"}
    ]
    assert {
        (o["metric"], o["value_min"], o["context"].get("method")) for o in liberty
    } == {
        ("seat_height_mm", "790", None),
        ("mass_kg", "121.5", "wet"),
        ("fuel_tank_capacity_liters", "6", None),
    }
    # Estimated fields never enter: ADR-016 scores measured facts only.
    assert all("est_" not in o["evidence_excerpt"] for o in liberty)
    assert all("seat_arch" not in o["evidence_excerpt"] for o in liberty)
    excerpt = json.loads(liberty[0]["evidence_excerpt"])
    assert (
        excerpt["model_page"] == "https://example.com/bikes/piaggio-liberty-125-test/"
    )
    assert "owner's manual" in excerpt["manual_source_citation"]
    reasons = {
        d["reason"]
        for d in bundle["decisions"]
        if d["selected_observation_id"] in {o["id"] for o in liberty}
    }
    assert len(reasons) == 1 and "MotoSpecDB" in reasons.pop()
    (source,) = [s for s in bundle["sources"] if s["source_key"] == "motospecdb"]
    assert source["ranking_permission"] == "manual_validation_only"
    assert "CC BY 4.0" in source["license"]
    # MotoSpecDB states no identity: it never joins the identity evidence.
    motospecdb = {
        s["id"] for s in bundle["snapshots"] if s["source_key"] == "motospecdb"
    }
    for record in [*bundle["vehicles"], *bundle["variants"]]:
        assert not motospecdb & set(record["evidence_snapshot_ids"])
    assert report["models"][0]["motospecdb"] == "piaggio-liberty-125-test"


@pytest.mark.parametrize(
    "found,link,reason",
    [
        (bike("x", "Aster 300", "2021–Present", ["AS3"]), "x", None),
        # Variants or generations joined in one entry: refused.
        (
            bike("x", "Aster 300 / Aster 300 S", "2021–Present", ["AS3"]),
            "x",
            "motospecdb_combined_entry",
        ),
        (
            bike("x", "Aster 300", "2017–Present", ["AS1", "AS3"]),
            "x",
            "motospecdb_combined_entry",
        ),
        # Years that miss the registrations read, unless the chassis code is the name.
        (
            bike("x", "Aster 300", "2025–Present", ["AS3"]),
            "x",
            "motospecdb_years_differ",
        ),
        (bike("x", "Aster 300", "2018-2023", ["AS3"]), "x", "motospecdb_years_differ"),
        (bike("x", "Aster 300", "2025–Present", ["ASTER 300"]), "x", None),
        (
            {**bike("x", "Aster 300", "2021–Present", ["AS3"]), "brand": "Other"},
            "x",
            "motospecdb_brand_differs",
        ),
        # A name match without a reviewed link is never made.
        (bike("x", "Aster 300", "2021–Present", ["AS3"]), None, "motospecdb_no_entry"),
    ],
)
def test_a_motospecdb_entry_must_fit_one_model(found, link, reason):
    entry = {"make": "Piaggio", "rdw_handelsbenaming": "ASTER 300", "motospecdb": link}
    match, refused = open_data.motospecdb_entry(entry, [found], 2026)
    assert refused == reason
    assert (match is found) == (reason is None)


# --- One EEA name shared by two models ---------------------------------------------


def test_a_name_shared_by_two_models_is_split_by_type_approval(run):
    split = {
        "families": [
            *NAMES["families"],
            {
                "make": "Fiat",
                "model": "Panda Gas",
                "eea": [
                    {
                        "mk": "FIAT",
                        "names": ["PANDA"],
                        "type_approvals": ["E3*2007/46*0064*70"],
                    }
                ],
            },
        ]
    }
    names = run.read(open_data.names_request())
    before = {f["key"]: f for f in open_data.resolve_families(NAMES, names)[0]}
    after = {f["key"]: f for f in open_data.resolve_families(split, names)[0]}
    # Each part ranks at the name's total: the names list does not count approvals.
    assert after["fiat-panda-gas"]["registrations"] == 1510
    assert after["fiat-panda"]["approvals"] == {
        ("FIAT", "PANDA"): ("except", ["E3*2007/46*0064*70"])
    }
    assert after["fiat-panda-gas"]["approvals"] == {
        ("FIAT", "PANDA"): ("only", ["E3*2007/46*0064*70"])
    }
    # A family without a split asks EEA exactly what it asked before.
    assert open_data.family_request(after["bmw-x1"]) == open_data.family_request(
        before["bmw-x1"]
    )
    query = json.loads(
        parse_qs(urlsplit(open_data.family_request(after["fiat-panda"]).url).query)[
            "source"
        ][0]
    )["query"]
    (clause,) = query["bool"]["filter"][-1]["bool"]["should"]
    assert clause["bool"]["must_not"] == [{"prefix": {"TAN": "E3*2007/46*0064*70*"}}]
    gas = json.dumps(open_data.family_request(after["fiat-panda-gas"]).url)
    assert "prefix" in gas and "must_not" not in gas
    # Inside a split family, shares use the exact total of its own response.
    response = {
        "aggregations": {
            "g": values({})
            | {
                "buckets": [
                    {
                        "key": ["lpg", "B"],
                        "doc_count": 300,
                        "v": {"buckets": [{**PANDA_LPG, "key": PANDA_LPG["key"][2:]}]},
                    }
                ]
            }
        }
    }
    family = after["fiat-panda-gas"]
    kept, _ = open_data.powertrain_groups(family, response)
    assert family["registrations"] == 300 and len(kept) == 1
    with pytest.raises(open_data.OpenDataError, match="exact names only"):
        open_data.resolve_families(
            {
                "families": [
                    {
                        "make": "A",
                        "model": "B",
                        "eea": [
                            {"mk": "A", "prefixes": ["B"], "type_approvals": ["E1*1"]}
                        ],
                    }
                ]
            },
            names,
        )


def test_the_register_dates_every_response_and_counts_the_values(run):
    bundle, cars = open_data.build_cars(run, NAMES)
    bikes, two_wheelers = open_data.build_two_wheelers(run, TWO_WHEELERS)
    covered = {
        "cars": open_data.coverage(bundle),
        "two_wheelers": open_data.coverage(bikes),
    }
    register = open_data.gap_register(run, cars, two_wheelers, covered)
    hosts = {(r["host"], r["date"]) for r in register["retrieval"]}
    assert ("motospecdb.com", "2026-11-23") in hosts
    assert sum(r["responses"] for r in register["retrieval"]) == len(run.manifest)
    assert covered["two_wheelers"]["mass_kg (wet)"] == 1
    assert covered["two_wheelers"]["mass_kg (mass_in_running_order)"] == 1
    assert covered["cars"]["body_style"] == 0
    markdown = open_data.gap_register_markdown(register)
    assert "| motospecdb.com | 2026-11-23 | 1 |" in markdown
    assert "| seat_height_mm | 1 |" in markdown
