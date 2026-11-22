"""Explicit staging and transactional publication of reviewed, self-contained bundles."""

import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4

from psycopg import sql
from psycopg.types.json import Jsonb

from app.ingestion.catalog import CatalogValidationError
from app.ingestion.catalog_v2 import CatalogV2


def verify_artifacts(payload: CatalogV2, artifact_root: Path) -> None:
    root = artifact_root.resolve(strict=True)
    for snapshot in payload.snapshots:
        try:
            path = (root / snapshot.artifact_path).resolve(strict=True)
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if digest != snapshot.content_sha256:
                raise ValueError
        except (OSError, ValueError) as error:
            raise CatalogValidationError(
                f"Missing, unsafe or hash-mismatched artifact for snapshot {snapshot.id}."
            ) from error


def stage_catalog_v2(conn, payload: CatalogV2, *, artifact_root: Path) -> UUID:
    # Revalidate even callers that constructed or mutated Pydantic instances.
    payload = CatalogV2.model_validate(payload.model_dump(mode="json"))
    verify_artifacts(payload, artifact_root)
    data = payload.model_dump(mode="json")
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
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


def _fuel_type(variant) -> str | None:
    if variant.powertrain_type == "BEV":
        return "electric"
    if variant.powertrain_type == "PHEV":
        return "phev"
    if variant.fuel == "petrol":
        return {"MHEV": "mild_hybrid_petrol", "HEV": "full_hybrid_petrol"}.get(
            variant.powertrain_type, "petrol"
        )
    return variant.fuel


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
        for field, value in values.items():
            expected = value.obj if isinstance(value, Jsonb) else value
            if row[field] != expected:
                raise CatalogValidationError(f"Published identity differs at {field}.")
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
    conn, batch_id: UUID, *, artifact_root: Path, adopt_legacy=False
) -> str:
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
        payload = CatalogV2.model_validate(row["payload"])
        verify_artifacts(payload, artifact_root)
        previous_writer = conn.execute(
            "SELECT current_setting('drivewise.catalog_writer', true) AS writer"
        ).fetchone()["writer"]
        conn.execute("SELECT set_config('drivewise.catalog_writer', 'v2', true)")
        source_ids = {}
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
            source_ids[source.source_key] = conn.execute(
                "SELECT id FROM sources WHERE source_key = %s", (source.source_key,)
            ).fetchone()["id"]
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
