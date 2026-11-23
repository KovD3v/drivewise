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
from urllib.parse import quote, urlencode
from uuid import NAMESPACE_URL, uuid5

from app.ingestion.catalog_v2 import METRIC_UNITS, CatalogV2

VERSION = "open-data-v1"
EEA_YEAR = 2024
EEA_STATUS = "F"  # final data; provisional rows duplicate the same registrations
EEA_URL = "https://co2cars.apps.eea.europa.eu/tools/api"
RDW_URL = "https://opendata.rdw.nl/resource"
RDW_VEHICLES = "m9d7-ebf2"
RDW_APPROVAL_ENERGY = "gr7t-qfnb"
TOP_FAMILIES = 100
NAME_BUCKETS = 450
VERSION_BUCKETS = 60
MIN_POWERTRAIN_SHARE = Decimal("0.05")
MAX_POWERTRAINS = 4
MAX_RDW_CANDIDATES = 3
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
        "(EEA legal notice; CC BY 4.0).",
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
        "body_style, generation, model_year",
        "not_in_source",
        "Left unknown, not guessed.",
    ),
    (
        "all",
        "length_mm, body_width_mm, height_mm",
        "centimetre_precision",
        "RDW stores whole centimetres; a brochure can differ by a few centimetres.",
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
        "seat_height_mm, fuel_tank_capacity_liters",
        "no_verified_source",
        "One open dataset has them but its origin is unverified.",
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
    ("all", "source_review", "unsigned", "Both sources stay manual_validation_only."),
    (
        "all",
        "attribution",
        "no_ui_location",
        "CC BY needs a visible EEA credit in the product.",
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


def family_request(family: dict) -> Request:
    by_make: dict[str, list[str]] = {}
    for make, name in family["names"]:
        by_make.setdefault(make, []).append(name)
    should = [
        {"bool": {"filter": [{"term": {"Mk": make}}, {"terms": {"Cn": sorted(names)}}]}}
        for make, names in sorted(by_make.items())
    ]
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
        "aggs": {
            "v": {
                "multi_terms": {
                    "terms": [{"field": f} for f in ("Ft", "Fm", "TAN", "Va", "Ve")],
                    "size": VERSION_BUCKETS,
                },
                "aggs": {
                    k: {"terms": {"field": f, "size": VALUE_BUCKETS}}
                    for k, f in EEA_STATS.items()
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


def two_wheel_versions_request(entry: dict) -> Request:
    fields = "typegoedkeuringsnummer,variant,uitvoering"
    where = (
        "voertuigsoort in ('Motorfiets','Bromfiets') "
        f"AND merk={_soql(entry['rdw_merk'])} "
        f"AND handelsbenaming={_soql(entry['rdw_handelsbenaming'])} "
        f"AND cilinderinhoud={int(entry['displacement_cc'])} "
        "AND datum_eerste_toelating>'20240101' "
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


class Run:
    """A run directory: raw responses under artifacts/, described by manifest.json."""

    def __init__(self, root: Path):
        self.root = root
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

    Returns the top families by registrations and every unmapped name."""
    exact, prefixes = {}, []
    for family in name_map["families"]:
        for rule in family["eea"]:
            for name in rule.get("names", []):
                exact[(rule["mk"], name)] = family
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
        if family is None:
            unmapped.append(
                {"make": make, "name": name, "registrations": bucket["doc_count"]}
            )
            continue
        key = slug(f"{family['make']}-{family['model']}")
        total = totals.setdefault(
            key,
            {
                "key": key,
                "make": family["make"],
                "model": family["model"],
                "registrations": 0,
                "names": [],
            },
        )
        total["registrations"] += bucket["doc_count"]
        total["names"].append((make, name))
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
# "H" covers mild and full hybrids alike, so the hybrid type stays unknown.
POWERTRAINS = {"M": "ICE", "B": "ICE", "H": None, "P": "PHEV", "E": "BEV"}


def powertrain_groups(family: dict, response: dict) -> tuple[list[dict], list[dict]]:
    """Group registered versions by powertrain and keep the groups that matter."""
    groups: dict[tuple, list[dict]] = {}
    skipped = []
    for bucket in response["aggregations"]["v"]["buckets"]:
        fuel, mode, tan, variant, version = bucket["key"]
        if not (tan and variant and version):
            continue
        groups.setdefault((fuel, mode), []).append(bucket)
    kept = []
    for (fuel, mode), buckets in groups.items():
        registrations = sum(b["doc_count"] for b in buckets)
        info = {"fuel": fuel, "mode": mode, "registrations": registrations}
        if fuel not in FUELS or mode not in POWERTRAINS:
            skipped.append({**info, "reason": "fuel_unsupported"})
        elif Decimal(registrations) / family["registrations"] < MIN_POWERTRAIN_SHARE:
            skipped.append({**info, "reason": "below_share_threshold"})
        else:
            buckets.sort(key=lambda b: (-b["doc_count"], b["key"]))
            kept.append({**info, "versions": buckets[:MAX_RDW_CANDIDATES]})
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
    wanted = slug(family_make)
    return any(
        slug(row.get("merk", "")) in wanted or wanted in slug(row.get("merk", ""))
        for row in rdw_rows
    )


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
                yield from choose_version(run, family, group)[2]
    for entry in two_wheelers["models"]:
        yield from plan_two_wheeler(run, entry)[1]


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
        self.run = run
        self.vehicles, self.variants = [], []
        self.snapshots: dict[str, dict] = {}
        self.observations, self.decisions = [], []
        self.decided_at = max(e["retrieved_at"] for e in run.manifest.values())

    def snapshot(self, request: Request, source_key: str) -> str:
        entry = self.run.manifest[request.artifact_path]
        snapshot_id = _uuid("snapshot", request.artifact_path, entry["sha256"])
        self.snapshots[snapshot_id] = {
            "id": snapshot_id,
            "source_key": source_key,
            "url": request.url,
            "retrieved_at": entry["retrieved_at"],
            "content_sha256": entry["sha256"],
            "artifact_path": request.artifact_path,
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
                "reason": "One official open-registry value for this exact "
                "type-approval version, accepted by rule.",
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
                    bundle, vehicle_key, group, bucket, rdw_request, eea_snapshot
                )
            )
        approvals = {v["type_approval"][0].rsplit("*", 1)[0] for v in entry["variants"]}
        if len(approvals) > 1:
            # One commercial name can cover two generations sold in the same year.
            entry["gaps"].append(
                {"metric": "generation", "reason": "several_type_approvals"}
            )
    return bundle.result(), report


def _car_variant(bundle, vehicle_key, group, bucket, rdw_request, eea_snapshot) -> dict:
    fuel, mode, tan, variant, version = bucket["key"]
    variant_key = f"{vehicle_key}.{slug(fuel)}-{mode.lower()}.{_short('|'.join((tan, variant, version)))}"
    gaps = []
    evidence = [eea_snapshot]
    locator = f"aggregations.v.buckets[key={json.dumps(bucket['key'])}]"

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
    if mode in {"E", "P"}:
        eea(
            "electric_consumption_kwh_100km",
            "electric_consumption",
            "Wh/km",
            context=_measured(mode),
            factor=Decimal("0.1"),
        )
    if mode == "E":
        eea("electric_range_km", "electric_range", "km", context=_measured(mode))
    elif mode == "P":
        gaps.append(
            {"metric": "electric_range_km", "reason": "phev_range_definition_unknown"}
        )
    if POWERTRAINS[mode] is None:
        gaps.append({"metric": "powertrain_type", "reason": "hybrid_type_unknown"})

    rdw_match = "none"
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
    bundle.variants.append(
        {
            "variant_key": variant_key,
            "vehicle_key": vehicle_key,
            "trim": None,
            "powertrain_type": POWERTRAINS[mode],
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
        "type_approval": [tan, variant, version],
        "registrations_of_version": bucket["doc_count"],
        "registrations_of_powertrain": group["registrations"],
        "rdw_match": rdw_match,
        "gaps": gaps,
    }


def build_two_wheelers(run: Run, two_wheelers: dict) -> tuple[dict | None, dict]:
    bundle = _Bundle(run)
    report = {"models": []}
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
    "phev_range_definition_unknown": "EEA does not say which electric range it reports.",
    "hybrid_type_unknown": "EEA does not separate mild from full hybrids.",
    "registry_values_disagree": "Registrations of this version disagree by over 5%.",
    "too_many_values": "Too many different values to tell real ones from errors.",
    "several_type_approvals": "Variants come from several type approvals: the name may "
    "cover two generations or bodies. Review before treating it as one car.",
    "centimetre_precision": "The registry stores whole centimetres.",
    "one_version_per_powertrain": "Only the most-registered version is imported.",
    "fuel_unsupported": "The catalog has no code for this fuel (methane, E85).",
    "below_share_threshold": "Under 5% of the model's registrations.",
    "beyond_powertrain_limit": "Beyond the four most-registered powertrains.",
    "no_supported_powertrain": "No powertrain of this model could be imported.",
}


def gap_register(run: Run, cars: dict, two_wheelers: dict) -> dict:
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
