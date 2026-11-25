"""Explicit staging and transactional publication of reviewed, self-contained bundles."""

import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from psycopg import sql
from psycopg.types.json import Jsonb

from app.ingestion.catalog import CatalogValidationError
from app.ingestion.catalog_v2 import CatalogV2

# Never follow a symlink, never block on a FIFO or device, never leak the fd.
_OPEN_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)


def _open_beneath(root_fd: int, relative: str) -> int:
    """Open a regular file below root_fd, walking each component without symlinks.

    O_NOFOLLOW guards only the last component, so every directory is opened
    relative to its parent's descriptor: a swapped-in symlink fails closed.
    """
    parts = PurePosixPath(relative).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("unsafe artifact path")
    current = root_fd
    try:
        for part in parts[:-1]:
            child = os.open(part, _OPEN_FLAGS | os.O_DIRECTORY, dir_fd=current)
            if current != root_fd:
                os.close(current)
            current = child
        fd = os.open(parts[-1], _OPEN_FLAGS, dir_fd=current)
    finally:
        if current != root_fd:
            os.close(current)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise ValueError("artifact is not a regular file")
    return fd


def verify_artifacts(payload: CatalogV2, artifact_root: Path) -> None:
    root = artifact_root.resolve(strict=True)
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0))
    try:
        for snapshot in payload.snapshots:
            try:
                fd = _open_beneath(root_fd, snapshot.artifact_path)
                with os.fdopen(fd, "rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                if digest != snapshot.content_sha256:
                    raise ValueError
            except (OSError, ValueError) as error:
                raise CatalogValidationError(
                    f"Missing, unsafe or hash-mismatched artifact for snapshot {snapshot.id}."
                ) from error
    finally:
        os.close(root_fd)


# Reserved names (RFC 2606, RFC 6761) never host real evidence.
_RESERVED_SUFFIXES = (".test", ".example", ".invalid", ".localhost")
_RESERVED_DOMAINS = ("example.com", "example.net", "example.org")


def _reserved_host(url: str) -> bool:
    host = (urlsplit(str(url)).hostname or "").rstrip(".").casefold()
    return (
        host in {"test", "example", "invalid", "localhost"}
        or host.endswith(_RESERVED_SUFFIXES)
        or any(host == d or host.endswith("." + d) for d in _RESERVED_DOMAINS)
    )


def synthetic_ranking_snapshots(
    payload: CatalogV2, permissions: dict[str, str] | None = None
) -> list[UUID]:
    """Sourced snapshots that would rank but come from a test host or synthetic licence.

    `permissions` maps source keys to the stored permission, which wins over the
    bundle's: publication never rewrites an existing source.
    """
    sources = {source.source_key: source for source in payload.sources}
    flagged = []
    for snapshot in payload.snapshots:
        source = sources[snapshot.source_key]
        permission = (permissions or {}).get(
            source.source_key, source.ranking_permission
        )
        if snapshot.evidence_kind != "sourced" or permission != "permitted":
            continue
        if (
            _reserved_host(snapshot.url)
            or _reserved_host(source.url)
            or "synthetic" in source.license.casefold()
        ):
            flagged.append(snapshot.id)
    return flagged


class SyntheticSourceError(CatalogValidationError):
    """Our own message, with no source content: safe to print."""


def check_synthetic_sources(
    payload: CatalogV2,
    *,
    allow_synthetic: bool,
    permissions: dict[str, str] | None = None,
) -> None:
    if allow_synthetic:
        return
    if synthetic_ranking_snapshots(payload, permissions):
        raise SyntheticSourceError(
            "Sourced evidence from a test host or synthetic licence would rank; "
            "pass --allow-synthetic only for a demo or test database."
        )


def dataset_hash(data: dict) -> str:
    """SHA-256 of the canonical JSON; absent optional terms are omitted, not null."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def stage_catalog_v2(conn, payload: CatalogV2, *, artifact_root: Path) -> UUID:
    # Revalidate even callers that constructed or mutated Pydantic instances.
    payload = CatalogV2.model_validate(payload.model_dump(mode="json"))
    verify_artifacts(payload, artifact_root)
    data = payload.model_dump(mode="json")
    digest = dataset_hash(data)
    with conn.transaction():
        conn.execute(
            """INSERT INTO catalog_v2_batches (id, dataset_hash, payload)
               VALUES (%s, %s, %s) ON CONFLICT (dataset_hash) DO NOTHING""",
            (uuid4(), digest, Jsonb(data)),
        )
        return conn.execute(
            "SELECT id FROM catalog_v2_batches WHERE dataset_hash = %s", (digest,)
        ).fetchone()["id"]


def _insert_immutable(conn, table: str, values: dict) -> None:
    """A retry may reuse an ID, never change what that ID means."""
    columns = list(values)
    adapted = [Jsonb(v) if isinstance(v, (dict, list)) else v for v in values.values()]
    # Evidence UUID arrays are native SQL arrays, not JSON.
    for index, column in enumerate(columns):
        if column == "evidence_ids":
            adapted[index] = [UUID(v) for v in values[column]]
    conn.execute(
        sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT (id) DO NOTHING").format(
            sql.Identifier(table),
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.SQL(", ").join(sql.Placeholder() for _ in columns),
        ),
        adapted,
    )
    same = conn.execute(
        sql.SQL("SELECT {} AS same FROM {} WHERE id = %s").format(
            sql.SQL(" AND ").join(
                sql.SQL("{} IS NOT DISTINCT FROM %s").format(sql.Identifier(k))
                for k in columns
            ),
            sql.Identifier(table),
        ),
        [*adapted, values["id"]],
    ).fetchone()
    if not same or not same["same"]:
        raise CatalogValidationError(f"Immutable {table} ID has different content.")


# Plug-in hybrids get the Advisor's own fuel names. Only the petrol one is scored;
# a diesel plug-in keeps its fuel in the name and is counted as unsupported.
_PLUG_IN_FUEL_TYPES = {
    "petrol": "plug_in_hybrid_petrol",
    "diesel": "plug_in_hybrid_diesel",
}


def _fuel_type(variant) -> str | None:
    if variant.powertrain_type == "BEV":
        return "electric"
    if variant.powertrain_type == "PHEV":
        # An unknown or unusual plug-in fuel stays the generic, unscored "phev".
        return _PLUG_IN_FUEL_TYPES.get(variant.fuel, "phev")
    if variant.fuel == "petrol":
        return {"MHEV": "mild_hybrid_petrol", "HEV": "full_hybrid_petrol"}.get(
            variant.powertrain_type, "petrol"
        )
    return variant.fuel


def _fills_body_style(row, values, differing, *, table) -> bool:
    """True when a bundle only turns an unknown body style into a known one.

    The stored identity evidence must stay a prefix of the bundle's: evidence is
    appended, never replaced, so eligibility can only become stricter. A vehicle
    must append the snapshot that states the body style; its variants inherit it.
    """
    if set(differing) - {"body_style", "identity_evidence"}:
        return False
    if row["body_style"] is not None or values["body_style"] is None:
        return False
    stored, bundled = list(row["identity_evidence"]), list(values["identity_evidence"])
    if bundled[: len(stored)] != stored:
        return False
    # A repeated snapshot is no new source. Read provenance credits the body style to
    # the last snapshot, so the last one must be new to the stored evidence.
    return table == "vehicle_specs" or (
        len(bundled) > len(stored) and bundled[-1] not in stored
    )


def _publish_identity(conn, table, key_column, key, values, *, adopt_legacy):
    row = conn.execute(
        sql.SQL("SELECT * FROM {} WHERE {} = %s FOR UPDATE").format(
            sql.Identifier(table), sql.Identifier(key_column)
        ),
        (key,),
    ).fetchone()
    if row is None:
        columns = ["id", key_column, *values]
        record_id = uuid4()
        conn.execute(
            sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(table),
                sql.SQL(", ").join(map(sql.Identifier, columns)),
                sql.SQL(", ").join(sql.Placeholder() for _ in columns),
            ),
            [record_id, key, *values.values()],
        )
        return record_id
    if row["catalog_version"] == 1:
        if not adopt_legacy:
            raise CatalogValidationError(
                "Legacy identity requires --adopt-legacy with stable keys."
            )
        # An adoption is an explicit mapping by stable key, not a merge or reparenting.
        for field in ("make", "model", "market", "model_year", "vehicle_id"):
            if field in values and row[field] != values[field]:
                raise CatalogValidationError(
                    "Legacy mapping changes identity; split/mapping review required."
                )
        values["legacy_record"] = Jsonb(json.loads(json.dumps(row, default=str)))
    else:
        # Identity corrections need a reviewed migration; scraping cannot rewrite identity.
        # One exception: an unknown body style may be filled, with its evidence appended.
        differing = [
            field
            for field, value in values.items()
            if row[field] != (value.obj if isinstance(value, Jsonb) else value)
        ]
        if not differing:
            return row["id"]
        if not _fills_body_style(row, values, differing, table=table):
            raise CatalogValidationError(
                f"Published identity differs at {differing[0]}."
            )
        conn.execute(
            sql.SQL(
                "UPDATE {} SET body_style = %s, identity_evidence = %s WHERE id = %s"
            ).format(sql.Identifier(table)),
            (values["body_style"], values["identity_evidence"], row["id"]),
        )
        return row["id"]
    conn.execute(
        sql.SQL("UPDATE {} SET {} WHERE id = %s").format(
            sql.Identifier(table),
            sql.SQL(", ").join(
                sql.SQL("{} = %s").format(sql.Identifier(k)) for k in values
            ),
        ),
        [*values.values(), row["id"]],
    )
    provenance_table, entity_column = (
        ("vehicle_provenance", "vehicle_id")
        if table == "vehicles"
        else ("vehicle_spec_provenance", "spec_id")
    )
    conn.execute(
        sql.SQL("UPDATE {} SET is_current = false WHERE {} = %s").format(
            sql.Identifier(provenance_table), sql.Identifier(entity_column)
        ),
        (row["id"],),
    )
    return row["id"]


def publish_catalog_v2(
    conn,
    batch_id: UUID,
    *,
    artifact_root: Path,
    adopt_legacy=False,
    allow_synthetic: bool = True,
) -> str:
    """Publish a staged batch in one transaction.

    The library default keeps synthetic fixtures publishable for tests; the
    import CLI passes allow_synthetic=False unless --allow-synthetic is given.
    """
    with conn.transaction():
        # ponytail: serialize local batch publishers; use per-variant locks at higher throughput.
        conn.execute("SELECT pg_advisory_xact_lock(742021, 2)")
        row = conn.execute(
            "SELECT * FROM catalog_v2_batches WHERE id = %s FOR UPDATE", (batch_id,)
        ).fetchone()
        if row is None:
            raise CatalogValidationError("Unknown staged batch.")
        if row["published_at"] is not None:
            return "unchanged"
        # The staged payload must still be the reviewed one: hash it exactly as stored.
        if dataset_hash(row["payload"]) != row["dataset_hash"]:
            raise CatalogValidationError("Staged batch payload differs from its hash.")
        payload = CatalogV2.model_validate(row["payload"])
        verify_artifacts(payload, artifact_root)
        previous_writer = conn.execute(
            "SELECT current_setting('drivewise.catalog_writer', true) AS writer"
        ).fetchone()["writer"]
        conn.execute("SELECT set_config('drivewise.catalog_writer', 'v2', true)")
        source_ids, permissions = {}, {}
        for source in payload.sources:
            # Replaying a bundle must never restore a revoked source permission.
            conn.execute(
                """INSERT INTO sources (id, source_key, name, source_type, market,
                   ranking_permission, url, license, notes)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (source_key) DO NOTHING""",
                (
                    uuid4(),
                    source.source_key,
                    source.name,
                    source.source_type,
                    source.market,
                    source.ranking_permission,
                    source.url,
                    source.license,
                    source.notes,
                ),
            )
            stored = conn.execute(
                """SELECT id, source_type, market, url, ranking_permission
                   FROM sources WHERE source_key = %s""",
                (source.source_key,),
            ).fetchone()
            # A key collision must not borrow another origin's permission.
            if (stored["source_type"], stored["market"], stored["url"]) != (
                source.source_type,
                source.market,
                source.url,
            ):
                raise CatalogValidationError(
                    f"Source {source.source_key} differs from the stored source "
                    "(type, market or URL)."
                )
            source_ids[source.source_key] = stored["id"]
            permissions[source.source_key] = stored["ranking_permission"]
        check_synthetic_sources(
            payload, allow_synthetic=allow_synthetic, permissions=permissions
        )
        for snapshot in payload.snapshots:
            values = snapshot.model_dump()
            values["source_id"] = source_ids[values.pop("source_key")]
            values["source_url"] = str(values.pop("url"))
            # Native timestamps compare through PostgreSQL, including equivalent offsets.
            _insert_immutable(conn, "source_snapshots", values)
        vehicles = {}
        for vehicle in payload.vehicles:
            values = vehicle.model_dump(
                exclude={"canonical_key", "evidence_snapshot_ids"}
            )
            values.update(
                catalog_version=2,
                identity_evidence=vehicle.evidence_snapshot_ids,
                fuel_type=None,
                base_price_eur=None,
            )
            vehicles[vehicle.canonical_key] = _publish_identity(
                conn,
                "vehicles",
                "canonical_key",
                vehicle.canonical_key,
                values,
                adopt_legacy=adopt_legacy,
            )
        variants = {}
        by_key = {v.canonical_key: v for v in payload.vehicles}
        for variant in payload.variants:
            values = variant.model_dump(
                exclude={
                    "variant_key",
                    "vehicle_key",
                    "evidence_snapshot_ids",
                    "external_references",
                }
            )
            values.update(
                vehicle_id=vehicles[variant.vehicle_key],
                catalog_version=2,
                body_style=by_key[variant.vehicle_key].body_style,
                fuel_type=_fuel_type(variant),
                identity_evidence=variant.evidence_snapshot_ids,
                external_references=Jsonb(
                    [r.model_dump() for r in variant.external_references]
                ),
            )
            variants[variant.variant_key] = _publish_identity(
                conn,
                "vehicle_specs",
                "variant_key",
                variant.variant_key,
                values,
                adopt_legacy=adopt_legacy,
            )
        # A filled body style must reach every published variant of its vehicle.
        unfilled = conn.execute(
            """SELECT 1 FROM vehicle_specs s JOIN vehicles v ON v.id = s.vehicle_id
               WHERE v.id = ANY(%s) AND s.catalog_version = 2
                 AND s.body_style IS DISTINCT FROM v.body_style LIMIT 1""",
            (list(vehicles.values()),),
        ).fetchone()
        if unfilled:
            raise CatalogValidationError(
                "Include every published variant when filling a body style."
            )
        # Adopting a vehicle requires an explicit mapping for all its existing variants.
        remaining = conn.execute(
            "SELECT 1 FROM vehicle_specs WHERE vehicle_id = ANY(%s) AND catalog_version = 1 LIMIT 1",
            (list(vehicles.values()),),
        ).fetchone()
        if remaining:
            raise CatalogValidationError(
                "Include every legacy variant when adopting a vehicle."
            )
        for observation in payload.observations:
            values = observation.model_dump(mode="json")
            key = values.pop("variant_key")
            values["spec_id"] = variants[key] if key else None
            _insert_immutable(conn, "spec_observations", values)
        for decision in payload.decisions:
            values = decision.model_dump(mode="json")
            values["spec_id"] = variants[values.pop("variant_key")]
            _insert_immutable(conn, "fact_decisions", values)
        conn.execute(
            "UPDATE catalog_v2_batches SET published_at = now() WHERE id = %s",
            (batch_id,),
        )
        conn.execute(
            "SELECT set_config('drivewise.catalog_writer', %s, true)",
            (previous_writer or "",),
        )
    return "published"
