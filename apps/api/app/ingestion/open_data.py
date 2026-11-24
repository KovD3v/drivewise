"""Build catalog v2 bundles from two open registries: EEA (cars) and RDW (dimensions,
two-wheelers). Fetching saves every raw response once; building is offline and
deterministic, so the same run directory always yields the same bundle."""

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit
from uuid import NAMESPACE_URL, uuid5

from app.ingestion.catalog_v2 import METRIC_UNITS, CatalogV2

VERSION = "open-data-v1"
EEA_YEAR = 2024
EEA_STATUS = "F"  # final data; provisional rows duplicate the same registrations
EEA_URL = "https://co2cars.apps.eea.europa.eu/tools/api"
RDW_URL = "https://opendata.rdw.nl/resource"
RDW_VEHICLES = "m9d7-ebf2"
RDW_APPROVAL_ENERGY = "gr7t-qfnb"
RDW_FUEL = "8ys7-d773"
MOTOSPECDB_URL = "https://motospecdb.com/api/v1/bikes.json"
# Two-wheelers are looked up among the Dutch registrations from this year on.
TWO_WHEEL_SINCE_YEAR = 2024
TOP_FAMILIES = 100
NAME_BUCKETS = 450
POWERTRAIN_BUCKETS = 30
# A version standing for under a tenth of its powertrain is flagged in the register.
SMALL_VERSION_SHARE = Decimal("0.10")
MIN_POWERTRAIN_SHARE = Decimal("0.05")
MAX_POWERTRAINS = 4
MAX_RDW_CANDIDATES = 3
# Type approval knows one class for mild and full hybrids alike. The registry does
# record the net power of the electric motor. On the 2024 Italian top 100 it is 17 kW
# or less for 12 V and 48 V systems and 32 kW or more for high-voltage hybrids;
# nothing lies between. A value between the two limits decides nothing.
HYBRID_SAMPLE = 5
MILD_HYBRID_BELOW_KW = Decimal(20)
FULL_HYBRID_FROM_KW = Decimal(30)
VALUE_BUCKETS = 40
# A value held by under 2% of a version's registrations is treated as an entry error.
RARE_SHARE = Decimal("0.02")
# Values that should be one number per version may differ by this much (trim, options).
MAX_SPREAD = Decimal("0.05")
SINGLE_VALUED = {
    "mass_kg",
    "engine_power_kw",
    "engine_displacement_cc",
    "length_mm",
    "body_width_mm",
    "height_mm",
    "seats",
}
CAR_DIMENSIONS = ("lengte", "breedte", "hoogte_voertuig", "aantal_zitplaatsen")
# RDW records the EU bodywork code ("inrichting"), a legal class, not the body style a
# buyer means. On the 2024 Italian top 100 it calls the Golf hatchback "stationwagen",
# the Panda and the Model Y "MPV", and the Corolla Cross and the Vitara "hatchback".
# Only "sedan" names one of the catalogue's body styles; the other codes stay unknown.
RDW_BODY_STYLES = {"sedan": "sedan"}

SOURCES = [
    {
        "source_key": "eea-co2-cars",
        "name": "EEA: CO2 emissions from new passenger cars",
        "source_type": "public_dataset",
        "market": "EU",
        # Not "permitted" until a person signs docs/source-reviews/eea-co2-cars.md.
        "ranking_permission": "manual_validation_only",
        "url": "https://co2cars.apps.eea.europa.eu/",
        "license": "Free reuse, commercial included, with attribution to the EEA "
        "(EEA legal notice).",
        "notes": f"Italy, registration year {EEA_YEAR}, final data only.",
    },
    {
        "source_key": "rdw-open-data",
        "name": "RDW open data: registered vehicles and type approvals",
        "source_type": "public_dataset",
        "market": "NL",
        "ranking_permission": "manual_validation_only",
        "url": "https://opendata.rdw.nl/",
        "license": "Public domain, as declared in the RDW dataset metadata (CC0).",
        "notes": "Dutch registry; values are matched by EU type-approval version.",
    },
    {
        "source_key": "motospecdb",
        "name": "MotoSpecDB open specification dataset",
        "source_type": "public_dataset",
        "market": "GLOBAL",
        "ranking_permission": "manual_validation_only",
        "url": "https://motospecdb.com/en/open-data/",
        "license": "Creative Commons Attribution 4.0 (CC BY 4.0), commercial reuse "
        "allowed. Attribution: MotoSpecDB (https://motospecdb.com), with a link to "
        "the model page.",
        "notes": "Published by Campdal Studio. Each entry cites an owner's manual; the "
        "values are not verified beyond that citation. Only measured fields are "
        "imported (seat height, wet weight, fuel tank); estimated fields are ignored.",
    },
]

# Gaps that no open source closes. They apply to every model of the given type.
DATASET_GAPS = [
    (
        "car",
        "list_price_eur",
        "no_open_source",
        "No free reusable Italian price source.",
    ),
    ("car", "cargo_volume_liters", "no_open_source", "Only in manufacturer documents."),
    (
        "car",
        "width_with_mirrors_mm",
        "no_open_source",
        "Only in manufacturer documents.",
    ),
    (
        "car",
        "trim, transmission, drivetrain",
        "not_in_source",
        "EEA and RDW do not name them.",
    ),
    (
        "car",
        "generation, model_year",
        "not_in_source",
        "Left unknown, not guessed.",
    ),
    (
        "car",
        "body_style",
        "rdw_body_code_not_catalogue",
        "RDW gives the EU bodywork code; only sedan matches a catalogue body style.",
    ),
    (
        "all",
        "length_mm, body_width_mm, height_mm",
        "centimetre_precision",
        "RDW stores whole centimetres; checked against one brochure only.",
    ),
    (
        "car",
        "variants",
        "one_version_per_powertrain",
        "Each powertrain shows its most-registered version, not every engine or trim.",
    ),
    (
        "two_wheeler",
        "list_price_eur",
        "no_open_source",
        "No free reusable Italian price source.",
    ),
    (
        "two_wheeler",
        "seat_height_mm, fuel_tank_capacity_liters, mass_kg (wet)",
        "unverified_origin",
        "From MotoSpecDB only where one entry fits one model; it cites owner's "
        "manuals and is not otherwise verified.",
    ),
    (
        "two_wheeler",
        "underseat_storage_liters",
        "no_open_source",
        "Only on manufacturer sites.",
    ),
    (
        "two_wheeler",
        "italian_availability",
        "hand_made_list",
        "The model list is hand-made; RDW proves the EU approval, not Italian sale.",
    ),
    ("all", "source_review", "unsigned", "Every source stays manual_validation_only."),
    (
        "all",
        "attribution",
        "no_ui_location",
        "The EEA and MotoSpecDB terms need a visible credit in the product.",
    ),
]


class OpenDataError(ValueError):
    pass


@dataclass(frozen=True)
class Request:
    artifact_path: str
    url: str


def slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-") or "x"


def _short(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def _eea_url(source: dict) -> str:
    url = (
        EEA_URL
        + "?"
        + urlencode(
            {
                "source": json.dumps(source, separators=(",", ":"), sort_keys=True),
                "source_content_type": "application/json",
            }
        )
    )
    if len(url) > 2000:
        raise OpenDataError("EEA request URL exceeds the snapshot URL limit.")
    return url


def _eea_filter() -> list[dict]:
    return [
        {"term": {"MS": "IT"}},
        {"term": {"year": EEA_YEAR}},
        {"term": {"Status": EEA_STATUS}},
    ]


def names_request() -> Request:
    source = {
        "size": 0,
        "query": {"bool": {"filter": _eea_filter()}},
        "aggs": {
            "v": {
                "multi_terms": {
                    "terms": [{"field": "Mk"}, {"field": "Cn"}],
                    "size": NAME_BUCKETS,
                }
            }
        },
    }
    return Request("eea/names.json", _eea_url(source))


EEA_STATS = {
    "mass": "m__kg_",
    "co2": "Ewltp__g_km_",
    "displacement": "ec__cm3_",
    "power": "ep__KW_",
    "consumption": "Fc",
    "electric_consumption": "z__Wh_km_",
    "electric_range": "Zr",
}


def _approval_prefixes(approvals: list[str]) -> list[dict]:
    return [{"prefix": {"TAN": f"{approval}*"}} for approval in sorted(approvals)]


def family_request(family: dict) -> Request:
    by_make: dict[str, list[str]] = {}
    split = family.get("approvals", {})
    for make, name in family["names"]:
        if (make, name) not in split:
            by_make.setdefault(make, []).append(name)
    should = [
        {"bool": {"filter": [{"term": {"Mk": make}}, {"terms": {"Cn": sorted(names)}}]}}
        for make, names in sorted(by_make.items())
    ]
    # A name shared by two models is split by type approval (see resolve_families).
    for (make, name), (kind, approvals) in sorted(split.items()):
        clause = {"filter": [{"term": {"Mk": make}}, {"term": {"Cn": name}}]}
        if kind == "only":
            clause["filter"].append(
                {
                    "bool": {
                        "should": _approval_prefixes(approvals),
                        "minimum_should_match": 1,
                    }
                }
            )
        else:
            clause["must_not"] = _approval_prefixes(approvals)
        should.append({"bool": clause})
    source = {
        "size": 0,
        "query": {
            "bool": {
                "filter": [
                    *_eea_filter(),
                    {"bool": {"should": should, "minimum_should_match": 1}},
                ]
            }
        },
        # Powertrains first, so their totals are exact however many versions exist:
        # one Audi Q3 powertrain is spread over hundreds of approval versions.
        "aggs": {
            "g": {
                "multi_terms": {
                    "terms": [{"field": "Ft"}, {"field": "Fm"}],
                    "size": POWERTRAIN_BUCKETS,
                },
                "aggs": {
                    "v": {
                        "multi_terms": {
                            "terms": [{"field": f} for f in ("TAN", "Va", "Ve")],
                            "size": MAX_RDW_CANDIDATES,
                        },
                        "aggs": {
                            k: {"terms": {"field": f, "size": VALUE_BUCKETS}}
                            for k, f in EEA_STATS.items()
                        },
                    }
                },
            }
        },
    }
    return Request(f"eea/family-{family['key']}.json", _eea_url(source))


def _soql(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _rdw_url(dataset: str, params: dict) -> str:
    return f"{RDW_URL}/{dataset}.json?" + urlencode(params, quote_via=quote)


def _version_where(tan: str, variant: str, version: str) -> str:
    return (
        f"typegoedkeuringsnummer={_soql(tan.lower())} AND variant={_soql(variant)} "
        f"AND uitvoering={_soql(version)}"
    )


def rdw_car_request(tan: str, variant: str, version: str) -> Request:
    fields = "merk,handelsbenaming," + ",".join(CAR_DIMENSIONS)
    return Request(
        f"rdw/car-{_short('|'.join((tan, variant, version)))}.json",
        _rdw_url(
            RDW_VEHICLES,
            {
                "$select": fields + ",count(*) as n",
                "$where": _version_where(tan, variant, version),
                "$group": fields,
                "$order": "n desc",
                "$limit": 50,
            },
        ),
    )


def rdw_body_request(tan: str, variant: str, version: str) -> Request:
    """The registered body style of one version: RDW records the EU bodywork code."""
    return Request(
        f"rdw/car-body-{_short('|'.join((tan, variant, version)))}.json",
        _rdw_url(
            RDW_VEHICLES,
            {
                "$select": "merk,inrichting,count(*) as n",
                "$where": _version_where(tan, variant, version),
                "$group": "merk,inrichting",
                "$order": "n desc,inrichting",
                "$limit": 50,
            },
        ),
    )


def hybrid_plates_request(tan: str, variant: str, version: str) -> Request:
    """A few registered vehicles of one version: fuel data is published per vehicle."""
    return Request(
        f"rdw/hybrid-plates-{_short('|'.join((tan, variant, version)))}.json",
        _rdw_url(
            RDW_VEHICLES,
            {
                "$select": "kenteken",
                "$where": _version_where(tan, variant, version),
                "$order": "kenteken",
                "$limit": HYBRID_SAMPLE,
            },
        ),
    )


def hybrid_motor_request(
    tan: str, variant: str, version: str, plates: list[str]
) -> Request:
    listed = ",".join(_soql(plate) for plate in plates)
    return Request(
        f"rdw/hybrid-motor-{_short('|'.join((tan, variant, version)))}.json",
        _rdw_url(
            RDW_FUEL,
            {
                "$select": "kenteken,klasse_hybride_elektrisch_voertuig,"
                "netto_max_vermogen_elektrisch",
                "$where": f"kenteken in ({listed}) "
                "AND brandstof_omschrijving='Elektriciteit'",
                "$order": "kenteken",
                "$limit": 50,
            },
        ),
    )


def two_wheel_versions_request(entry: dict) -> Request:
    fields = "typegoedkeuringsnummer,variant,uitvoering"
    where = (
        "voertuigsoort in ('Motorfiets','Bromfiets') "
        f"AND merk={_soql(entry['rdw_merk'])} "
        f"AND handelsbenaming={_soql(entry['rdw_handelsbenaming'])} "
        f"AND cilinderinhoud={int(entry['displacement_cc'])} "
        f"AND datum_eerste_toelating>'{TWO_WHEEL_SINCE_YEAR}0101' "
        "AND typegoedkeuringsnummer IS NOT NULL AND variant IS NOT NULL "
        "AND uitvoering IS NOT NULL"
    )
    return Request(
        f"rdw/two-wheel-versions-{entry['slug']}.json",
        _rdw_url(
            RDW_VEHICLES,
            {
                "$select": fields + ",count(*) as n",
                "$where": where,
                "$group": fields,
                "$order": "n desc," + fields,
                "$limit": 10,
            },
        ),
    )


TWO_WHEEL_FIELDS = (
    "lengte",
    "breedte",
    "hoogte_voertuig",
    "aantal_zitplaatsen",
    "massa_rijklaar",
    "cilinderinhoud",
)


def two_wheel_values_request(
    entry: dict, tan: str, variant: str, version: str
) -> Request:
    fields = ",".join(TWO_WHEEL_FIELDS)
    return Request(
        f"rdw/two-wheel-values-{entry['slug']}.json",
        _rdw_url(
            RDW_VEHICLES,
            {
                "$select": fields + ",count(*) as n",
                "$where": _version_where(tan, variant, version)
                + f" AND merk={_soql(entry['rdw_merk'])}",
                "$group": fields,
                "$order": "n desc",
                "$limit": 50,
            },
        ),
    )


def two_wheel_power_request(
    entry: dict, tan: str, variant: str, version: str
) -> Request:
    return Request(
        f"rdw/two-wheel-power-{entry['slug']}.json",
        _rdw_url(
            RDW_APPROVAL_ENERGY,
            {
                # The approval dataset drops leading zeros of the codes ("00" is "0"),
                # so the whole approval is fetched and the version is matched offline.
                "$select": "codevarianttgk,codeuitvoeringtgk,volgnummerrevisieuitvoering,"
                "codeenergiebron,maximumnettovermogenogr,maximumnettovermogenbgr",
                "$where": f"typegoedkeuringsnummer={_soql(tan.lower())}",
                "$order": "codevarianttgk,codeuitvoeringtgk,"
                "volgnummerrevisieuitvoering,volgnummerenergiebron",
                "$limit": 1000,
            },
        ),
    )


def motospecdb_request() -> Request:
    """The whole MotoSpecDB open dataset, one JSON file, fetched once per run."""
    return Request("motospecdb/bikes.json", MOTOSPECDB_URL)


# Measured MotoSpecDB fields only (ADR-016): est_* and seat_arch_factor are estimates.
MOTOSPECDB_FACTS = (
    ("seat_height_mm", "seat_height_mm", "mm", None),
    ("mass_kg", "wet_weight_kg", "kg", {"method": "wet"}),
    ("fuel_tank_capacity_liters", "fuel_tank_l", "l", None),
)
_YEARS = re.compile(r"^\s*(\d{4})\s*[\u2013-]\s*(\d{4}|Present)\s*$")


# A person links a two-wheeler to one MotoSpecDB entry after reading it. The link keeps
# what the entry said then, so a later change of the entry needs a new review.
MOTOSPECDB_REVIEWED = ("model", "years_covered", "chassis_codes")


def motospecdb_entry(
    entry: dict, bikes: list[dict], until_year: int
) -> tuple[dict | None, str | None]:
    """The MotoSpecDB entry a person matched to this model, if it passes the rules.

    The link must still describe the entry as reviewed (model, years, chassis codes).
    The entry must describe one variant of one generation: a name joining variants
    ("A / B") or several chassis codes is refused. Its years must cover every year of
    the Dutch registrations read. CC BY needs the model page, and the decision cites
    the owner's manual, so an entry without both is refused."""
    link = entry.get("motospecdb")
    if link is not None and not isinstance(link, dict):
        return None, "motospecdb_link_unbound"
    wanted = (link or {}).get("slug")
    found = next((b for b in bikes if wanted and b.get("slug") == wanted), None)
    if found is None:
        return None, "motospecdb_no_entry"
    if found.get("brand", "").casefold() != entry["make"].casefold():
        return None, "motospecdb_brand_differs"
    if any(found.get(field) != link.get(field) for field in MOTOSPECDB_REVIEWED):
        return None, "motospecdb_link_changed"
    codes = found.get("chassis_codes") or []
    if "/" in found.get("model", "") or len(codes) > 1:
        return None, "motospecdb_combined_entry"
    years = _YEARS.match(found.get("years_covered") or "")
    if not years or not (
        int(years[1]) <= TWO_WHEEL_SINCE_YEAR
        and (years[2] == "Present" or int(years[2]) >= until_year)
    ):
        return None, "motospecdb_years_differ"
    if not (found.get("urls") or {}).get("en") or not (
        found.get("manual_source_citation") or {}
    ).get("en"):
        return None, "motospecdb_attribution_missing"
    return found, None


class Run:
    """A run directory: raw responses under artifacts/, described by manifest.json.

    Runs sit side by side in one folder, the artifact root. Evidence paths start with
    the run's folder name, so a later run never collides with a published one."""

    def __init__(self, root: Path):
        self.root = root
        self.artifact_root = root.resolve().parent
        self.artifacts = root / "artifacts"
        self.manifest_path = root / "manifest.json"
        self.manifest: dict[str, dict] = (
            json.loads(self.manifest_path.read_text())
            if self.manifest_path.exists()
            else {}
        )

    def has(self, request: Request) -> bool:
        entry = self.manifest.get(request.artifact_path)
        return entry is not None and entry["url"] == request.url

    def read(self, request: Request):
        entry = self.manifest.get(request.artifact_path)
        if entry is None or entry["url"] != request.url:
            raise OpenDataError(
                f"Missing or outdated artifact {request.artifact_path}; fetch first."
            )
        data = (self.artifacts / request.artifact_path).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise OpenDataError(f"Artifact {request.artifact_path} changed on disk.")
        return json.loads(data)

    def evidence_path(self, request: Request) -> str:
        return f"{self.root.resolve().name}/artifacts/{request.artifact_path}"

    def store(self, request: Request, data: bytes, retrieved_at: datetime) -> None:
        json.loads(data)  # a non-JSON error page must never become evidence
        path = self.artifacts / request.artifact_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.manifest[request.artifact_path] = {
            "url": request.url,
            "retrieved_at": retrieved_at.astimezone(UTC).isoformat(timespec="seconds"),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        self.manifest_path.write_text(
            json.dumps(self.manifest, indent=1, sort_keys=True) + "\n"
        )


def resolve_families(
    name_map: dict, names_response: dict
) -> tuple[list[dict], list[dict]]:
    """Map EEA (make, commercial name) pairs to hand-reviewed families.

    A rule with `type_approvals` takes only the registrations under those approval
    numbers: EEA and RDW both call the Corolla Cross "TOYOTA COROLLA". The family
    holding the same name without that list then takes the other approvals. The
    names list does not count approvals, so each part of a split name is ranked at
    the name's total; powertrain_groups uses the exact total of its own response.

    Returns the top families by registrations and every unmapped name."""
    exact: dict[tuple, dict] = {}
    restricted: dict[tuple, list[tuple[dict, list[str]]]] = {}
    prefixes = []
    for family in name_map["families"]:
        for rule in family["eea"]:
            for name in rule.get("names", []):
                if rule.get("type_approvals"):
                    restricted.setdefault((rule["mk"], name), []).append(
                        (family, rule["type_approvals"])
                    )
                else:
                    exact[(rule["mk"], name)] = family
            if rule.get("prefixes") and rule.get("type_approvals"):
                raise OpenDataError("type_approvals apply to exact names only.")
            for prefix in rule.get("prefixes", []):
                prefixes.append((rule["mk"], prefix, family))
    totals: dict[str, dict] = {}
    unmapped = []
    for bucket in names_response["aggregations"]["v"]["buckets"]:
        make, name = bucket["key"]
        family = exact.get((make, name))
        if family is None:
            matches = [
                (len(prefix), target)
                for mk, prefix, target in prefixes
                if mk == make and name.startswith(prefix)
            ]
            family = max(matches, key=lambda m: m[0])[1] if matches else None
        parts = [
            (target, ("only", approvals))
            for target, approvals in restricted.get((make, name), [])
        ]
        if family is not None and parts:
            taken = sorted({a for _, (_, approvals) in parts for a in approvals})
            parts.append((family, ("except", taken)))
        elif family is not None:
            parts = [(family, None)]
        if not parts:
            unmapped.append(
                {"make": make, "name": name, "registrations": bucket["doc_count"]}
            )
            continue
        for target, approvals in parts:
            key = slug(f"{target['make']}-{target['model']}")
            total = totals.setdefault(
                key,
                {
                    "key": key,
                    "make": target["make"],
                    "model": target["model"],
                    "registrations": 0,
                    "names": [],
                },
            )
            total["registrations"] += bucket["doc_count"]
            total["names"].append((make, name))
            if approvals:
                total.setdefault("approvals", {})[(make, name)] = approvals
    ranked = sorted(totals.values(), key=lambda f: (-f["registrations"], f["key"]))
    return ranked[:TOP_FAMILIES], unmapped


FUELS = {
    "petrol": "petrol",
    "diesel": "diesel",
    "lpg": "petrol_lpg",
    "electric": "electricity",
    "petrol/electric": "petrol",
    "diesel/electric": "diesel",
}
# EEA fuel mode: M mono-fuel, B bi-fuel, H hybrid without plug, P plug-in, E electric.
# "H" covers mild and full hybrids alike; hybrid_kind() tells them apart where it can.
POWERTRAINS = {"M": "ICE", "B": "ICE", "H": None, "P": "PHEV", "E": "BEV"}


def powertrain_groups(family: dict, response: dict) -> tuple[list[dict], list[dict]]:
    """Keep the powertrains that matter, each with its most-registered versions."""
    groups = response["aggregations"]["g"]
    if groups["sum_other_doc_count"] or groups["doc_count_error_upper_bound"]:
        raise OpenDataError(f"EEA lists too many powertrains for {family['key']}.")
    if family.get("approvals"):
        # A split name: its ranking total covers both models, this response one.
        family["registrations"] = sum(group["doc_count"] for group in groups["buckets"])
    skipped, kept = [], []
    for group in groups["buckets"]:
        fuel, mode = group["key"]
        registrations = group["doc_count"]
        info = {"fuel": fuel, "mode": mode, "registrations": registrations}
        versions = [
            {**b, "key": [fuel, mode, *b["key"]]}
            for b in group["v"]["buckets"]
            if all(b["key"])
        ]
        if fuel not in FUELS or mode not in POWERTRAINS:
            skipped.append({**info, "reason": "fuel_unsupported"})
        elif Decimal(registrations) / family["registrations"] < MIN_POWERTRAIN_SHARE:
            skipped.append({**info, "reason": "below_share_threshold"})
        elif not versions:
            skipped.append({**info, "reason": "no_type_approval_version"})
        else:
            versions.sort(key=lambda b: (-b["doc_count"], b["key"]))
            kept.append({**info, "versions": versions})
    kept.sort(key=lambda g: (-g["registrations"], g["fuel"], g["mode"]))
    for group in kept[MAX_POWERTRAINS:]:
        skipped.append(
            {k: group[k] for k in ("fuel", "mode", "registrations")}
            | {"reason": "beyond_powertrain_limit"}
        )
    return kept[:MAX_POWERTRAINS], skipped


def settle(
    counts: dict[Decimal, int], *, unlisted: int = 0, single_valued: bool
) -> tuple[Decimal, Decimal] | str:
    """Turn the registrations per value into one value, an interval, or a gap reason.

    Registries hold entry errors: 8 of 1,034 cars of one version at twice the power."""
    total = sum(counts.values()) + unlisted
    if not total:
        return "empty"
    kept = [value for value, n in counts.items() if n >= total * RARE_SHARE]
    if not kept or unlisted >= total * RARE_SHARE:
        return "too_many_values"
    low, high = min(kept), max(kept)
    if single_valued and high - low > low * MAX_SPREAD:
        return "registry_values_disagree"
    return low, high


def _rdw_counts(rows: list[dict], field: str) -> dict[Decimal, int]:
    counts: dict[Decimal, int] = {}
    for row in rows:
        if row.get(field):
            value = _number(row[field])
            counts[value] = counts.get(value, 0) + int(row["n"])
    return counts


def _same_make(family_make: str, rdw_rows: list[dict]) -> bool:
    """Exact after normalisation: one approval version can be registered by two makes."""
    wanted = slug(family_make)
    return any(slug(row.get("merk") or "") == wanted for row in rdw_rows)


def _complete(rows: list[dict]) -> bool:
    return any(all(row.get(field) for field in CAR_DIMENSIONS) for row in rows)


def choose_version(
    run: Run, family: dict, group: dict
) -> tuple[dict, Request | None, list]:
    """The most-registered version with exact, complete RDW data; else the top one.

    Returns (EEA bucket, RDW request or None, RDW requests still to fetch)."""
    fallback = None
    for bucket in group["versions"]:
        request = rdw_car_request(*bucket["key"][2:])
        if not run.has(request):
            return bucket, None, [request]
        rows = run.read(request)
        if rows and _same_make(family["make"], rows):
            if _complete(rows):
                return bucket, request, []
            fallback = fallback or (bucket, request)
    if fallback:
        return *fallback, []
    return group["versions"][0], None, []


def plan_hybrid(
    run: Run, bucket: dict, rdw_request: Request | None
) -> tuple[list[Request], list[Request]]:
    """(stored requests that tell the hybrid kind, requests still to fetch)."""
    if rdw_request is None:
        return [], []
    approval = bucket["key"][2:]
    plates_request = hybrid_plates_request(*approval)
    if not run.has(plates_request):
        return [], [plates_request]
    plates = [row["kenteken"] for row in run.read(plates_request)]
    if not plates:
        return [], []
    motor_request = hybrid_motor_request(*approval, plates)
    if not run.has(motor_request):
        return [], [motor_request]
    return [plates_request, motor_request], []


def hybrid_kind(rows: list[dict]) -> tuple[str | None, list[Decimal]]:
    """Mild or full hybrid, when every sampled motor lies on one side of the limits."""
    field = "netto_max_vermogen_elektrisch"
    powers = sorted({_number(row[field]) for row in rows if row.get(field)})
    if powers and powers[-1] < MILD_HYBRID_BELOW_KW:
        return "MHEV", powers
    if powers and powers[0] >= FULL_HYBRID_FROM_KW:
        return "HEV", powers
    return None, powers


def plan_two_wheeler(run: Run, entry: dict) -> tuple[dict | None, list[Request]]:
    versions = two_wheel_versions_request(entry)
    if not run.has(versions):
        return None, [versions]
    rows = run.read(versions)
    if not rows:
        return None, []
    top = rows[0]
    key = (top["typegoedkeuringsnummer"], top["variant"], top["uitvoering"])
    requests = {
        "versions": versions,
        "values": two_wheel_values_request(entry, *key),
        "power": two_wheel_power_request(entry, *key),
    }
    missing = [r for r in requests.values() if not run.has(r)]
    return {"version": top, "requests": requests}, missing


def plan(run: Run, name_map: dict, two_wheelers: dict) -> Iterator[Request]:
    """Yield every request still missing, given what the run already holds."""
    names = names_request()
    if not run.has(names):
        yield names
    else:
        families, _ = resolve_families(name_map, run.read(names))
        for family in families:
            request = family_request(family)
            if not run.has(request):
                yield request
                continue
            groups, _ = powertrain_groups(family, run.read(request))
            for group in groups:
                bucket, rdw_request, missing = choose_version(run, family, group)
                yield from missing
                if rdw_request is not None:
                    body = rdw_body_request(*bucket["key"][2:])
                    if not run.has(body):
                        yield body
                if not missing and group["mode"] == "H":
                    yield from plan_hybrid(run, bucket, rdw_request)[1]
    for entry in two_wheelers["models"]:
        yield from plan_two_wheeler(run, entry)[1]
    if not run.has(motospecdb_request()):
        yield motospecdb_request()


def fetch(
    run: Run,
    name_map: dict,
    two_wheelers: dict,
    http_get: Callable[[str], bytes],
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> int:
    """Download what is missing. Safe to repeat: stored responses are never refetched."""
    fetched = 0
    while True:
        # Two powertrains or two families can share one type-approval version.
        missing = {r.artifact_path: r for r in plan(run, name_map, two_wheelers)}
        if not missing:
            return fetched
        for request in missing.values():
            run.store(request, http_get(request.url), now())
            fetched += 1


def _uuid(*parts: str) -> str:
    return str(uuid5(NAMESPACE_URL, "|".join((VERSION, *parts))))


def _number(value) -> Decimal:
    return Decimal(str(value))


def _code(value: str | None) -> str:
    """Approval codes compare without leading zeros: RDW writes "00" and "0" alike."""
    return (value or "").lstrip("0") or "0"


def _plain(value: Decimal) -> str:
    """Shortest plain form: 100, never 1E+2 or 100.0."""
    return format(value.normalize(), "f")


class _Bundle:
    def __init__(self, run: Run):
        if not run.manifest:
            raise OpenDataError("The run directory holds no responses; fetch first.")
        self.run = run
        self.vehicles, self.variants = [], []
        self.snapshots: dict[str, dict] = {}
        self.observations, self.decisions = [], []
        self.decided_at = max(e["retrieved_at"] for e in run.manifest.values())

    def snapshot(self, request: Request, source_key: str) -> str:
        entry = self.run.manifest[request.artifact_path]
        path = self.run.evidence_path(request)
        snapshot_id = _uuid("snapshot", path, entry["sha256"])
        self.snapshots[snapshot_id] = {
            "id": snapshot_id,
            "source_key": source_key,
            "url": request.url,
            "retrieved_at": entry["retrieved_at"],
            "content_sha256": entry["sha256"],
            "artifact_path": path,
            "media_type": "application/json",
            "evidence_kind": "sourced",
        }
        return snapshot_id

    def observe(
        self,
        *,
        variant_key: str,
        metric: str,
        snapshot_id: str,
        low,
        high,
        raw_unit: str,
        factor: Decimal = Decimal(1),
        context: dict | None = None,
        excerpt: dict,
        locator: str,
        reason: str = "One official open-registry value for this exact "
        "type-approval version, accepted by rule.",
    ) -> None:
        """Record one registry value and accept it by rule.

        Different values across registrations of one version are an interval."""
        low, high = _number(low), _number(high)
        raw = _plain(low) if low == high else f"{_plain(low)}..{_plain(high)}"
        context = {"market": "IT", **(context or {})}
        observation_id = _uuid(
            "observation",
            variant_key,
            metric,
            json.dumps(context, sort_keys=True),
            snapshot_id,
        )
        self.observations.append(
            {
                "id": observation_id,
                "snapshot_id": snapshot_id,
                "variant_key": variant_key,
                "metric": metric,
                "raw_value": raw,
                "raw_unit": raw_unit,
                "value_min": _plain(low * factor),
                "value_max": _plain(high * factor),
                "unit": METRIC_UNITS[metric],
                "context": context,
                "evidence_excerpt": json.dumps(
                    excerpt, sort_keys=True, ensure_ascii=False
                ),
                "evidence_locator": locator,
                "extractor_version": VERSION,
            }
        )
        self.decisions.append(
            {
                "id": _uuid("decision", observation_id),
                "variant_key": variant_key,
                "metric": metric,
                "context": context,
                "status": "verified",
                "selected_observation_id": observation_id,
                "evidence_ids": [observation_id],
                "reason": reason,
                "actor_kind": "rule",
                "actor_id": "open-data-builder",
                "policy_version": VERSION,
                "decided_at": self.decided_at,
            }
        )

    def result(self) -> dict | None:
        if not self.vehicles:
            return None
        used = {s for o in self.observations for s in [o["snapshot_id"]]}
        for record in [*self.vehicles, *self.variants]:
            used.update(record["evidence_snapshot_ids"])
        source_keys = {self.snapshots[s]["source_key"] for s in used}
        bundle = {
            "schema_version": 2,
            "sources": [s for s in SOURCES if s["source_key"] in source_keys],
            "vehicles": self.vehicles,
            "variants": self.variants,
            "snapshots": [self.snapshots[s] for s in sorted(used)],
            "observations": self.observations,
            "decisions": self.decisions,
        }
        # Validating here means a bundle on disk has always passed the contract.
        return CatalogV2.model_validate(bundle).model_dump(mode="json")


BUNDLE_PARTS = (
    "sources",
    "vehicles",
    "variants",
    "snapshots",
    "observations",
    "decisions",
)


def _scope(record: dict) -> tuple:
    context = json.dumps(record["context"], sort_keys=True)
    return record["variant_key"], record["metric"], context


def _interval(observation: dict) -> tuple:
    return _number(observation["value_min"]), _number(observation["value_max"])


def continue_bundle(previous: dict, fresh: dict | None) -> tuple[dict, dict]:
    """Continue an earlier bundle with the bundle of a later run.

    Catalog v2 freezes a published vehicle or variant together with its evidence, and
    wants the whole history of a fact in one chain. So every earlier record is kept as
    it is, new vehicles and variants are added, and a fresh value becomes a decision
    that supersedes the earlier one only where the value changed. The one identity
    change catalog v2 accepts is a body style filled where it was unknown: the
    earlier evidence stays first and the snapshots that state the body follow it."""
    fresh = fresh or {part: [] for part in BUNDLE_PARTS}
    merged = {"schema_version": 2}
    merged.update({part: list(previous[part]) for part in BUNDLE_PARTS})
    all_snapshots = {s["id"]: s for s in [*previous["snapshots"], *fresh["snapshots"]]}
    report = {
        "new_vehicles": [],
        "new_variants": [],
        "body_style_filled": [],
        "identity_differs": [],
        "revised": [],
        "unchanged": 0,
        "kept_without_fresh_value": 0,
    }
    for part, key in (("vehicles", "canonical_key"), ("variants", "variant_key")):
        published = {record[key]: record for record in previous[part]}
        for record in fresh[part]:
            earlier = published.get(record[key])
            if earlier is None:
                merged[part].append(record)
                report[f"new_{part}"].append(record[key])
            elif _fills_body_style(earlier, record) and (
                filled := _with_body_style(earlier, record, all_snapshots)
            ):
                merged[part][merged[part].index(earlier)] = filled
                report["body_style_filled"].append(record[key])
            elif {**earlier, "evidence_snapshot_ids": None} != {
                **record,
                "evidence_snapshot_ids": None,
            }:
                # The earlier identity wins; a person decides whether it needs a migration.
                report["identity_differs"].append(record[key])
    observations = {o["id"]: o for o in previous["observations"]}
    heads = {_scope(decision): decision for decision in previous["decisions"]}
    fresh_observations = {o["id"]: o for o in fresh["observations"]}
    refreshed = set()
    for decision in fresh["decisions"]:
        scope = _scope(decision)
        refreshed.add(scope)
        observation = fresh_observations[decision["selected_observation_id"]]
        head = heads.get(scope)
        if head is not None:
            selected = observations.get(head["selected_observation_id"])
            if selected and _interval(selected) == _interval(observation):
                report["unchanged"] += 1
                continue
            decision = {**decision, "supersedes_id": head["id"]}
            report["revised"].append(
                {
                    "variant_key": scope[0],
                    "metric": scope[1],
                    "from": selected and selected["raw_value"],
                    "to": observation["raw_value"],
                }
            )
        merged["observations"].append(observation)
        merged["decisions"].append(decision)
    report["kept_without_fresh_value"] = len(set(heads) - refreshed)
    used = {o["snapshot_id"] for o in merged["observations"]}
    for record in [*merged["vehicles"], *merged["variants"]]:
        used.update(record["evidence_snapshot_ids"])
    snapshots = {s["id"]: s for s in [*previous["snapshots"], *fresh["snapshots"]]}
    merged["snapshots"] = [snapshots[snapshot_id] for snapshot_id in sorted(used)]
    sources = {s["source_key"]: s for s in [*fresh["sources"], *previous["sources"]]}
    merged["sources"] = [sources[key] for key in sorted(sources)]
    return CatalogV2.model_validate(merged).model_dump(mode="json"), report


def _fills_body_style(earlier: dict, record: dict) -> bool:
    """True when the fresh record differs from the earlier one only by a body style
    the earlier one left unknown."""
    ignored = {"evidence_snapshot_ids": None, "body_style": None}
    return (
        "body_style" in earlier
        and earlier["body_style"] is None
        and record.get("body_style") is not None
        and {**earlier, **ignored} == {**record, **ignored}
    )


def _with_body_style(earlier: dict, record: dict, snapshots: dict) -> dict | None:
    """The earlier record with the body style, its evidence kept as the prefix.

    Snapshot IDs carry the run folder, so the evidence of the later run is new by
    ID even for an identical response. Only responses the earlier record does not
    already rest on (by URL and hash) are appended: the ones that state the body."""
    known = {
        (snapshots[i]["url"], snapshots[i]["content_sha256"])
        for i in earlier["evidence_snapshot_ids"]
    }
    added = [
        i
        for i in record["evidence_snapshot_ids"]
        if (snapshots[i]["url"], snapshots[i]["content_sha256"]) not in known
    ]
    if not added:
        return None  # catalog v2 wants the snapshot that states the body appended
    return {
        **earlier,
        "body_style": record["body_style"],
        "evidence_snapshot_ids": [*earlier["evidence_snapshot_ids"], *added],
    }


def _measured(mode: str) -> dict:
    """WLTP context. Plug-in values are utility-factor weighted in the EEA data."""
    if mode == "P":
        return {
            "procedure": "WLTP",
            "cycle": "weighted_combined",
            "battery_condition": "weighted",
        }
    return {"procedure": "WLTP", "cycle": "combined"}


def _record(bundle, gaps, *, metric, counts, unlisted=0, empty_reason, **observation):
    outcome = settle(counts, unlisted=unlisted, single_valued=metric in SINGLE_VALUED)
    if isinstance(outcome, str):
        reason = empty_reason if outcome == "empty" else outcome
        gaps.append({"metric": metric, "reason": reason})
        return
    bundle.observe(metric=metric, low=outcome[0], high=outcome[1], **observation)


def _shown(counts: dict[Decimal, int]) -> dict[str, int]:
    return {_plain(value): counts[value] for value in sorted(counts)}


def build_cars(run: Run, name_map: dict) -> tuple[dict | None, dict]:
    bundle = _Bundle(run)
    families, unmapped = resolve_families(name_map, run.read(names_request()))
    report = {"families": [], "unmapped_names": unmapped}
    for family in families:
        request = family_request(family)
        response = run.read(request)
        eea_snapshot = bundle.snapshot(request, "eea-co2-cars")
        vehicle_key = f"it-{family['key']}"
        groups, skipped = powertrain_groups(family, response)
        entry = {
            "key": vehicle_key,
            "make": family["make"],
            "model": family["model"],
            "registrations": family["registrations"],
            "eea_names": [name for _, name in sorted(family["names"])],
            "skipped_powertrains": skipped,
            "gaps": [],
            "variants": [],
        }
        report["families"].append(entry)
        if not groups:
            continue
        bundle.vehicles.append(
            {
                "canonical_key": vehicle_key,
                "model_family_key": family["key"],
                "make": family["make"],
                "model": family["model"],
                "vehicle_type": "car",
                "generation_key": None,
                "phase_key": None,
                "body_style": None,
                "model_year": None,
                "market": "IT",
                "evidence_snapshot_ids": [eea_snapshot],
            }
        )
        for group in groups:
            bucket, rdw_request, missing = choose_version(run, family, group)
            if missing:
                raise OpenDataError("RDW responses are missing; fetch first.")
            entry["variants"].append(
                _car_variant(
                    bundle,
                    vehicle_key,
                    family["make"],
                    group,
                    bucket,
                    rdw_request,
                    eea_snapshot,
                )
            )
        _vehicle_body(bundle.vehicles[-1], entry)
        approvals = {v["type_approval"][0].rsplit("*", 1)[0] for v in entry["variants"]}
        if len(approvals) > 1:
            # One commercial name can cover two generations sold in the same year.
            entry["gaps"].append(
                {"metric": "generation", "reason": "several_type_approvals"}
            )
    return bundle.result(), report


def registered_body(family_make: str, rows: list[dict]) -> tuple[str | None, dict]:
    """The one EU bodywork code of a version's registrations, or None.

    Codes held by under 2% of the registrations are entry errors, as for values."""
    counts: dict[str, int] = {}
    for row in rows:
        if row.get("inrichting") and _same_make(family_make, [row]):
            counts[row["inrichting"]] = counts.get(row["inrichting"], 0) + int(row["n"])
    total = sum(counts.values())
    kept = sorted(code for code, n in counts.items() if n >= total * RARE_SHARE)
    return (kept[0] if len(kept) == 1 else None), dict(sorted(counts.items()))


def _vehicle_body(vehicle: dict, entry: dict) -> None:
    """Fill the body style when every variant's registrations name the same one.

    Body style belongs to the vehicle, so one variant without an exact registry
    match, or two variants with different bodies (a hatchback and its estate under
    one name), leave it unknown: the vehicle is not split by guess."""
    variants = entry["variants"]
    codes = {v["rdw_body_code"] for v in variants}
    if any(len(v["rdw_body_codes"]) and v["rdw_body_code"] is None for v in variants):
        reason = "rdw_body_styles_differ"
    elif any(v["rdw_match"] == "none" for v in variants):
        reason = "rdw_no_exact_version"
    elif None in codes:
        reason = "rdw_field_empty"
    elif len(codes) > 1:
        reason = "rdw_body_styles_differ"
    elif RDW_BODY_STYLES.get(next(iter(codes))) is None:
        reason = "rdw_body_code_not_catalogue"
    else:
        vehicle["body_style"] = RDW_BODY_STYLES[next(iter(codes))]
        # Appended last: the read provenance credits the body style to that snapshot.
        for variant in variants:
            if variant["rdw_body_snapshot"] not in vehicle["evidence_snapshot_ids"]:
                vehicle["evidence_snapshot_ids"].append(variant["rdw_body_snapshot"])
        entry["body_style"] = vehicle["body_style"]
        return
    entry["body_style"] = None
    entry["gaps"].append({"metric": "body_style", "reason": reason})


def _car_variant(
    bundle, vehicle_key, make, group, bucket, rdw_request, eea_snapshot
) -> dict:
    fuel, mode, tan, variant, version = bucket["key"]
    variant_key = f"{vehicle_key}.{slug(fuel)}-{mode.lower()}.{_short('|'.join((tan, variant, version)))}"
    gaps = []
    evidence = [eea_snapshot]
    locator = (
        f"aggregations.g.buckets[key={json.dumps(bucket['key'][:2])}]"
        f".v.buckets[key={json.dumps(bucket['key'][2:])}]"
    )
    if bucket["doc_count"] < group["registrations"] * SMALL_VERSION_SHARE:
        # The values below are real, but they describe a small slice of the powertrain.
        gaps.append({"metric": "variant", "reason": "version_covers_small_share"})

    def eea(metric, stat, raw_unit, *, context=None, factor=Decimal(1), places=None):
        values = bucket[stat]
        counts: dict[Decimal, int] = {}
        for item in values["buckets"]:
            value = _number(item["key"])
            if places is not None:  # EEA stores some decimals as 32-bit floats
                value = round(value, places)
            if value or metric == "co2_g_km":  # elsewhere a zero means "not filled in"
                counts[value] = counts.get(value, 0) + item["doc_count"]
        unlisted = values["sum_other_doc_count"] + values["doc_count_error_upper_bound"]
        _record(
            bundle,
            gaps,
            metric=metric,
            counts=counts,
            unlisted=unlisted,
            empty_reason="eea_field_empty",
            variant_key=variant_key,
            snapshot_id=eea_snapshot,
            raw_unit=raw_unit,
            factor=factor,
            context=context,
            excerpt={
                "key": bucket["key"],
                "registrations": bucket["doc_count"],
                EEA_STATS[stat]: _shown(counts),
                "unlisted": unlisted,
            },
            locator=f"{locator}.{stat}",
        )

    eea("mass_kg", "mass", "kg", context={"method": "mass_in_running_order"})
    if mode == "E":
        # EEA does not say whether "ep" is peak or 30-minute power for electric cars.
        gaps.append(
            {"metric": "system_power_kw", "reason": "bev_power_definition_unknown"}
        )
    else:
        eea("engine_power_kw", "power", "kW")
        eea("engine_displacement_cc", "displacement", "cm3")
    if mode == "B":
        # A bi-fuel car has one value per fuel; EEA publishes one without naming the fuel.
        for metric in ("co2_g_km", "liquid_consumption_l_100km"):
            gaps.append({"metric": metric, "reason": "bifuel_value_ambiguous"})
    else:
        eea("co2_g_km", "co2", "g/km", context=_measured(mode))
        if mode != "E":
            eea(
                "liquid_consumption_l_100km",
                "consumption",
                "l/100km",
                context=_measured(mode),
                places=1,
            )
    if mode == "E":
        eea(
            "electric_consumption_kwh_100km",
            "electric_consumption",
            "Wh/km",
            context=_measured(mode),
            factor=Decimal("0.1"),
        )
        eea("electric_range_km", "electric_range", "km", context=_measured(mode))
    elif mode == "P":
        # EEA does not say whether a plug-in's electric values are weighted or not.
        for metric in ("electric_consumption_kwh_100km", "electric_range_km"):
            gaps.append(
                {"metric": metric, "reason": "phev_electric_definition_unknown"}
            )
    rdw_match, body_code, body_codes, body_snapshot = "none", None, {}, None
    if rdw_request is None:
        for metric in ("length_mm", "body_width_mm", "height_mm", "seats"):
            gaps.append({"metric": metric, "reason": "rdw_no_exact_version"})
    else:
        rows = bundle.run.read(rdw_request)
        rdw_snapshot = bundle.snapshot(rdw_request, "rdw-open-data")
        evidence.append(rdw_snapshot)
        rdw_match = "exact"
        for metric, field, unit, factor in (
            ("length_mm", "lengte", "cm", 10),
            ("body_width_mm", "breedte", "cm", 10),
            ("height_mm", "hoogte_voertuig", "cm", 10),
            ("seats", "aantal_zitplaatsen", None, 1),
        ):
            counts = _rdw_counts(rows, field)
            _record(
                bundle,
                gaps,
                metric=metric,
                counts=counts,
                empty_reason="rdw_field_empty",
                variant_key=variant_key,
                snapshot_id=rdw_snapshot,
                raw_unit=unit or "count",
                factor=Decimal(factor),
                excerpt={
                    "typegoedkeuringsnummer": tan.lower(),
                    "variant": variant,
                    "uitvoering": version,
                    field: _shown(counts),
                },
                locator=f"rows[*].{field}",
            )
        body_request = rdw_body_request(tan, variant, version)
        if not bundle.run.has(body_request):
            raise OpenDataError("RDW body-style responses are missing; fetch first.")
        body_code, body_codes = registered_body(make, bundle.run.read(body_request))
        body_snapshot = bundle.snapshot(body_request, "rdw-open-data")
    powertrain, motor_kw = POWERTRAINS[mode], []
    if mode == "H":
        requests, missing = plan_hybrid(bundle.run, bucket, rdw_request)
        if missing:
            raise OpenDataError("RDW hybrid responses are missing; fetch first.")
        if requests:
            powertrain, motor_kw = hybrid_kind(bundle.run.read(requests[-1]))
        if powertrain:
            # The kind is part of the identity, so its evidence is identity evidence.
            evidence += [bundle.snapshot(r, "rdw-open-data") for r in requests]
        else:
            gaps.append({"metric": "powertrain_type", "reason": "hybrid_type_unknown"})
    bundle.variants.append(
        {
            "variant_key": variant_key,
            "vehicle_key": vehicle_key,
            "trim": None,
            "powertrain_type": powertrain,
            "fuel": FUELS[fuel],
            "transmission": None,
            "drivetrain": None,
            "external_references": [
                {"namespace": "eu-type-approval", "value": tan},
                {"namespace": "eu-type-approval-variant", "value": variant},
                {"namespace": "eu-type-approval-version", "value": version},
            ],
            "evidence_snapshot_ids": evidence,
        }
    )
    return {
        "variant_key": variant_key,
        "fuel": fuel,
        "fuel_mode": mode,
        "powertrain_type": powertrain,
        "electric_motor_kw": [_plain(power) for power in motor_kw],
        "type_approval": [tan, variant, version],
        "registrations_of_version": bucket["doc_count"],
        "registrations_of_powertrain": group["registrations"],
        "rdw_match": rdw_match,
        "rdw_body_code": body_code,
        "rdw_body_codes": body_codes,
        "rdw_body_snapshot": body_snapshot,
        "gaps": gaps,
    }


def build_two_wheelers(run: Run, two_wheelers: dict) -> tuple[dict | None, dict]:
    bundle = _Bundle(run)
    report = {"models": []}
    bikes = run.read(motospecdb_request())["bikes"]
    for entry in two_wheelers["models"]:
        planned, missing = plan_two_wheeler(run, entry)
        if missing:
            raise OpenDataError("RDW responses are missing; fetch first.")
        vehicle_key = f"it-{entry['slug']}"
        item = {
            "key": vehicle_key,
            "make": entry["make"],
            "model": entry["model"],
            "vehicle_type": entry["vehicle_type"],
            "gaps": [],
        }
        report["models"].append(item)
        if planned is None:
            item["gaps"].append({"metric": "identity", "reason": "rdw_not_found"})
            continue
        top, requests = planned["version"], planned["requests"]
        tan, variant, version = (
            top["typegoedkeuringsnummer"],
            top["variant"],
            top["uitvoering"],
        )
        versions_snapshot = bundle.snapshot(requests["versions"], "rdw-open-data")
        values_snapshot = bundle.snapshot(requests["values"], "rdw-open-data")
        variant_key = f"{vehicle_key}.{_short('|'.join((tan, variant, version)))}"
        item.update(
            variant_key=variant_key,
            type_approval=[tan, variant, version],
            dutch_registrations_of_version=int(top["n"]),
        )
        rows = run.read(requests["values"])
        for metric, field, unit, factor, context in (
            ("engine_displacement_cc", "cilinderinhoud", "cm3", 1, None),
            ("mass_kg", "massa_rijklaar", "kg", 1, {"method": "mass_in_running_order"}),
            ("length_mm", "lengte", "cm", 10, None),
            ("body_width_mm", "breedte", "cm", 10, None),
            ("height_mm", "hoogte_voertuig", "cm", 10, None),
            ("seats", "aantal_zitplaatsen", "count", 1, None),
        ):
            counts = _rdw_counts(rows, field)
            _record(
                bundle,
                item["gaps"],
                metric=metric,
                counts=counts,
                empty_reason="rdw_field_empty",
                variant_key=variant_key,
                snapshot_id=values_snapshot,
                raw_unit=unit,
                factor=Decimal(factor),
                context=context,
                excerpt={
                    "typegoedkeuringsnummer": tan,
                    "variant": variant,
                    "uitvoering": version,
                    field: _shown(counts),
                },
                locator=f"rows[*].{field}",
            )
        power_rows = [
            r
            for r in run.read(requests["power"])
            if _code(r.get("codevarianttgk")) == _code(variant)
            and _code(r.get("codeuitvoeringtgk")) == _code(version)
        ]
        evidence = [versions_snapshot, values_snapshot]
        petrol = False
        if power_rows:
            latest = max(int(r["volgnummerrevisieuitvoering"]) for r in power_rows)
            current = [
                r for r in power_rows if int(r["volgnummerrevisieuitvoering"]) == latest
            ]
            petrol = {r.get("codeenergiebron") for r in current} == {"B"}
            bounds = [
                _number(r[f])
                for r in current
                for f in ("maximumnettovermogenogr", "maximumnettovermogenbgr")
                if r.get(f)
            ]
        if not power_rows or not bounds or not petrol:
            item["gaps"].append(
                {"metric": "engine_power_kw", "reason": "rdw_field_empty"}
            )
        else:
            power_snapshot = bundle.snapshot(requests["power"], "rdw-open-data")
            evidence.append(power_snapshot)
            bundle.observe(
                variant_key=variant_key,
                metric="engine_power_kw",
                snapshot_id=power_snapshot,
                low=min(bounds),
                high=max(bounds),
                raw_unit="kW",
                excerpt={
                    "typegoedkeuringsnummer": tan,
                    "codevarianttgk": variant,
                    "codeuitvoeringtgk": version,
                    "revision": latest,
                    "maximumnettovermogen": sorted({str(b) for b in bounds}),
                },
                locator="rows[latest revision].maximumnettovermogen",
            )
        _motospecdb_facts(bundle, item, entry, bikes, variant_key, requests)
        bundle.vehicles.append(
            {
                "canonical_key": vehicle_key,
                "model_family_key": entry["slug"],
                "make": entry["make"],
                "model": entry["model"],
                "vehicle_type": entry["vehicle_type"],
                "generation_key": None,
                "phase_key": None,
                "body_style": None,
                "model_year": None,
                "market": "IT",
                "evidence_snapshot_ids": [versions_snapshot],
            }
        )
        bundle.variants.append(
            {
                "variant_key": variant_key,
                "vehicle_key": vehicle_key,
                "trim": None,
                # Petrol is read from the approval's energy code, never assumed.
                "powertrain_type": "ICE" if petrol else None,
                "fuel": "petrol" if petrol else None,
                "transmission": None,
                "drivetrain": None,
                "external_references": [
                    {"namespace": "eu-type-approval", "value": tan},
                    {"namespace": "eu-type-approval-variant", "value": variant},
                    {"namespace": "eu-type-approval-version", "value": version},
                ],
                "evidence_snapshot_ids": evidence,
            }
        )
    return bundle.result(), report


def _motospecdb_facts(bundle, item, entry, bikes, variant_key, requests) -> None:
    """Seat height, wet weight and fuel tank from the one MotoSpecDB entry that fits."""
    until = int(
        bundle.run.manifest[requests["versions"].artifact_path]["retrieved_at"][:4]
    )
    found, refused = motospecdb_entry(entry, bikes, until)
    link = entry.get("motospecdb")
    item["motospecdb"] = link.get("slug") if isinstance(link, dict) else link
    if found is None:
        for metric, *_ in MOTOSPECDB_FACTS:
            item["gaps"].append({"metric": metric, "reason": refused})
        return
    snapshot = bundle.snapshot(motospecdb_request(), "motospecdb")
    for metric, field, unit, context in MOTOSPECDB_FACTS:
        value = (found.get("ergonomics") or {}).get(field)
        if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
            item["gaps"].append({"metric": metric, "reason": "motospecdb_field_empty"})
            continue
        bundle.observe(
            variant_key=variant_key,
            metric=metric,
            snapshot_id=snapshot,
            low=value,
            high=value,
            raw_unit=unit,
            context=context,
            excerpt={
                "slug": found["slug"],
                "model": found.get("model"),
                "years_covered": found.get("years_covered"),
                "chassis_codes": found.get("chassis_codes"),
                field: value,
                "manual_source_citation": (
                    found.get("manual_source_citation") or {}
                ).get("en"),
                "model_page": (found.get("urls") or {}).get("en"),
            },
            locator=f"bikes[slug={found['slug']}].ergonomics.{field}",
            reason="One MotoSpecDB value for this model and years, matched by a "
            "reviewed link and accepted by rule; the publisher cites the owner's "
            "manual.",
        )


GAP_REASONS = {
    "no_open_source": "No free source with a reuse licence publishes this field.",
    "no_verified_source": "A free dataset has it, but its origin is not verified.",
    "not_in_source": "EEA and RDW do not carry this field.",
    "hand_made_list": "The model list is hand-made, not an official ranking.",
    "unsigned": "A person has not signed the source review yet.",
    "no_ui_location": "The product has no place to show the required credit yet.",
    "eea_field_empty": "EEA has no value for this version.",
    "rdw_no_exact_version": "No Dutch registration of this exact type-approval version.",
    "rdw_field_empty": "RDW has the version but not this value.",
    "rdw_not_found": "RDW has no registration under this name and displacement.",
    "bev_power_definition_unknown": "EEA does not say which electric power it reports.",
    "bifuel_value_ambiguous": "EEA gives one value without naming the fuel.",
    "phev_electric_definition_unknown": "EEA does not say whether a plug-in's electric "
    "consumption and range are weighted or pure-electric values.",
    "hybrid_type_unknown": "No registry value tells whether this hybrid is mild or full.",
    "registry_values_disagree": "Registrations of this version disagree by over 5%.",
    "rdw_body_code_not_catalogue": "RDW's EU bodywork code does not tell the "
    "catalogue's body styles apart (only sedan does).",
    "rdw_body_styles_differ": "The registrations name more than one body, within a "
    "version or across the variants of the model; not split by guess.",
    "too_many_values": "Too many different values to tell real ones from errors.",
    "several_type_approvals": "Variants come from several type approvals: the name may "
    "cover two generations or bodies. Review before treating it as one car.",
    "centimetre_precision": "The registry stores whole centimetres.",
    "one_version_per_powertrain": "Only the most-registered version is imported.",
    "version_covers_small_share": "The imported version is under 10% of its "
    "powertrain's registrations; other versions can differ.",
    "no_type_approval_version": "EEA has no complete type-approval codes for it.",
    "fuel_unsupported": "The catalog has no code for this fuel (methane, E85).",
    "below_share_threshold": "Under 5% of the model's registrations.",
    "beyond_powertrain_limit": "Beyond the four most-registered powertrains.",
    "no_supported_powertrain": "No powertrain of this model could be imported.",
    "motospecdb_no_entry": "MotoSpecDB has no entry for this model.",
    "motospecdb_brand_differs": "The linked MotoSpecDB entry names another make.",
    "motospecdb_combined_entry": "The MotoSpecDB entry joins several variants or "
    "generations, so its values may belong to another one.",
    "motospecdb_years_differ": "The MotoSpecDB entry's years do not cover the "
    "registrations read.",
    "motospecdb_link_unbound": "The link names the entry only by slug; it does not "
    "record the model, years and chassis codes that were reviewed.",
    "motospecdb_link_changed": "The MotoSpecDB entry no longer says what was "
    "reviewed (model, years or chassis codes); review the link again.",
    "motospecdb_attribution_missing": "The MotoSpecDB entry lacks its model page or "
    "its owner's manual citation, which the credit and the decision need.",
    "motospecdb_field_empty": "The MotoSpecDB entry has no value for this field.",
    "unverified_origin": "The source cites owner's manuals; its values are not "
    "otherwise verified.",
}


def retrieval(run: Run) -> list[dict]:
    """Per host and day, how many stored responses were retrieved.

    A run folder may start as a copy of an earlier one, so its responses can carry
    the earlier retrieval time; the manifest keeps each one's own."""
    counts: dict[tuple[str, str], int] = {}
    for entry in run.manifest.values():
        key = (urlsplit(entry["url"]).hostname or "", entry["retrieved_at"][:10])
        counts[key] = counts.get(key, 0) + 1
    return [
        {"host": host, "date": day, "responses": n}
        for (host, day), n in sorted(counts.items())
    ]


def coverage(bundle: dict | None) -> dict:
    """How many variants have a current value per metric, and vehicles a body style."""
    if not bundle:
        return {}
    heads = {d["id"]: d for d in bundle["decisions"]}
    for decision in bundle["decisions"]:
        heads.pop(decision.get("supersedes_id"), None)
    per_metric: dict[str, set] = {}
    for decision in heads.values():
        if decision["status"] == "verified":
            metric = decision["metric"]
            if metric == "mass_kg":  # a wet mass is another fact than the registry's
                metric += f" ({decision['context'].get('method')})"
            per_metric.setdefault(metric, set()).add(decision["variant_key"])
    result = {"variants": len(bundle["variants"]), "vehicles": len(bundle["vehicles"])}
    result["body_style"] = sum(1 for v in bundle["vehicles"] if v["body_style"])
    result.update({m: len(keys) for m, keys in sorted(per_metric.items())})
    return result


def gap_register(
    run: Run, cars: dict, two_wheelers: dict, covered: dict | None = None
) -> dict:
    """Everything the import could not fill, per model and field, with a reason."""
    rows = []
    for family in cars["families"]:
        label = f"{family['make']} {family['model']}"
        if not family["variants"]:
            rows.append(("car", label, None, "identity", "no_supported_powertrain"))
        for gap in family["gaps"]:
            rows.append(("car", label, None, gap["metric"], gap["reason"]))
        for variant in family["variants"]:
            name = f"{variant['fuel']} ({variant['fuel_mode']})"
            for gap in variant["gaps"]:
                rows.append(("car", label, name, gap["metric"], gap["reason"]))
        for skipped in family["skipped_powertrains"]:
            name = f"{skipped['fuel']} ({skipped['mode']})"
            rows.append(("car", label, name, "powertrain", skipped["reason"]))
    for model in two_wheelers["models"]:
        label = f"{model['make']} {model['model']}"
        for gap in model["gaps"]:
            rows.append(
                (model["vehicle_type"], label, None, gap["metric"], gap["reason"])
            )
    by_field: dict[tuple, int] = {}
    for kind, _, _, metric, reason in rows:
        kind = "car" if kind == "car" else "two_wheeler"
        by_field[(kind, metric, reason)] = by_field.get((kind, metric, reason), 0) + 1
    return {
        "version": VERSION,
        "data_retrieved_at": max(e["retrieved_at"] for e in run.manifest.values()),
        "scope": {
            "market": "IT",
            "eea_year": EEA_YEAR,
            "car_families": len(cars["families"]),
            "car_variants": sum(len(f["variants"]) for f in cars["families"]),
            "two_wheelers": len(two_wheelers["models"]),
        },
        "retrieval": retrieval(run),
        "coverage": covered or {},
        "dataset_gaps": [
            {"applies_to": a, "field": f, "reason": r, "detail": d}
            for a, f, r, d in DATASET_GAPS
        ],
        "summary": [
            {"applies_to": kind, "field": metric, "reason": reason, "count": count}
            for (kind, metric, reason), count in sorted(by_field.items())
        ],
        "gaps": [
            {
                "type": kind,
                "model": label,
                "variant": variant,
                "field": metric,
                "reason": reason,
            }
            for kind, label, variant, metric, reason in rows
        ],
        "unmapped_names": sorted(
            cars["unmapped_names"],
            key=lambda n: (-n["registrations"], n["make"], n["name"]),
        ),
    }


def gap_register_markdown(register: dict) -> str:
    scope = register["scope"]
    lines = [
        "# Open-data import: what is missing",
        "",
        "Generated by `apps/api/scripts/build_open_data_catalog.py build`. Do not edit by hand:",
        "rerun the build, and the diff of this file shows what changed.",
        "",
        f"- Data retrieved: {register['data_retrieved_at']}",
        f"- Scope: Italy, EEA registration year {scope['eea_year']}, "
        f"{scope['car_families']} car models with {scope['car_variants']} variants, "
        f"{scope['two_wheelers']} two-wheelers.",
        f"- Builder version: `{register['version']}`",
        "",
        "## Responses by host and retrieval day",
        "",
        "A run folder can start as a copy of an earlier one: these dates are each",
        "response's own, from the manifest.",
        "",
        "| Host | Retrieved | Responses |",
        "| --- | --- | --- |",
    ]
    lines += [
        f"| {r['host']} | {r['date']} | {r['responses']} |"
        for r in register.get("retrieval", [])
    ]
    for kind, covered in register.get("coverage", {}).items():
        lines += [
            "",
            f"## Values present: {kind}",
            "",
            f"{covered.get('variants', 0)} variants of {covered.get('vehicles', 0)} "
            f"vehicles; vehicles with a body style: {covered.get('body_style', 0)}.",
            "",
            "| Metric | Variants with a value |",
            "| --- | --- |",
        ]
        lines += [
            f"| {metric} | {n} |"
            for metric, n in covered.items()
            if metric not in {"variants", "vehicles", "body_style"}
        ]
    lines += [
        "",
        "## Missing for every model",
        "",
        "| Applies to | Field | Reason | Detail |",
        "| --- | --- | --- | --- |",
    ]
    lines += [
        f"| {g['applies_to']} | {g['field']} | {g['reason']} | {g['detail']} |"
        for g in register["dataset_gaps"]
    ]
    lines += [
        "",
        "## Missing per field",
        "",
        "| Applies to | Field | Reason | Variants |",
        "| --- | --- | --- | --- |",
    ]
    lines += [
        f"| {s['applies_to']} | {s['field']} | {s['reason']} | {s['count']} |"
        for s in register["summary"]
    ]
    lines += ["", "## Reason codes", ""]
    used = {g["reason"] for g in register["gaps"]} | {
        g["reason"] for g in register["dataset_gaps"]
    }
    lines += [
        f"- `{code}`: {text}" for code, text in GAP_REASONS.items() if code in used
    ]
    lines += [
        "",
        "## Missing per model",
        "",
        "| Type | Model | Variant | Field | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {g['type']} | {g['model']} | {g['variant'] or ''} | {g['field']} | {g['reason']} |"
        for g in register["gaps"]
    ]
    lines += [
        "",
        "## EEA names not mapped to a model",
        "",
        "These names are never imported. Add a rule to `data/open-data/car-names.it.json`",
        "to include one.",
        "",
        "| Make | EEA commercial name | Registrations |",
        "| --- | --- | --- |",
    ]
    lines += [
        f"| {n['make']} | {n['name']} | {n['registrations']} |"
        for n in register["unmapped_names"]
    ]
    return "\n".join(lines) + "\n"
