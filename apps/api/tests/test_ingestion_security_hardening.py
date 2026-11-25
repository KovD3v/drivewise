"""F-23 and F-30: Catalog v2 source trust, staged-batch integrity and artifact reads."""

import copy
import importlib.util
import json
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.ingestion.catalog import CatalogValidationError
from app.ingestion.catalog_v2 import CatalogV2
from app.ingestion.catalog_v2_writer import (
    SyntheticSourceError,
    check_synthetic_sources,
    publish_catalog_v2,
    stage_catalog_v2,
    synthetic_ranking_snapshots,
    verify_artifacts,
)
from tests.test_catalog_v2_publication import bundle, conn, publish  # noqa: F401

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "data/fixtures/catalog"
SCRIPT_PATH = ROOT / "apps/api/scripts/import_catalog_v2.py"
needs_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)


def load_import_script():
    spec = importlib.util.spec_from_file_location(
        "drivewise_import_catalog_v2_hardening", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unpublished_source(conn):  # noqa: F811
    return conn.execute(
        "SELECT 1 FROM sources WHERE source_key = 'synthetic-v2'"
    ).fetchone()


def ranked(data):
    """The synthetic fixture as a ranking, sourced bundle."""
    data["sources"][0]["ranking_permission"] = "permitted"
    for snapshot in data["snapshots"]:
        snapshot["evidence_kind"] = "sourced"
    return data


def real_origin(data):
    """The same bundle as if it came from a real, non-synthetic origin."""
    source = data["sources"][0]
    source["url"] = "https://registry.drivewise-origin.it/catalog"
    source["license"] = "Reviewed public licence"
    for snapshot in data["snapshots"]:
        snapshot["url"] = "https://registry.drivewise-origin.it/catalog/metro"
    return data


# --- https-only provenance (F-23, L4) ---------------------------------------


def test_snapshot_urls_must_use_https(tmp_path):
    data = bundle(tmp_path)
    data["snapshots"][0]["url"] = "http://example.test/catalog/metro"
    with pytest.raises(ValidationError, match="snapshot url must use https"):
        CatalogV2.model_validate(data)


# --- synthetic sources cannot rank by accident (F-23) -----------------------


def test_synthetic_detection_covers_test_hosts_and_licences(tmp_path):
    demo = json.loads((FIXTURES / "catalog-v2.demo.synthetic.json").read_text())
    assert synthetic_ranking_snapshots(CatalogV2.model_validate(demo))
    # The plain fixture neither ranks nor claims sourced evidence.
    plain = CatalogV2.model_validate(bundle(tmp_path))
    assert synthetic_ranking_snapshots(plain) == []
    # A stored permission wins over the bundle's declared one.
    data = bundle(tmp_path)
    for snapshot in data["snapshots"]:
        snapshot["evidence_kind"] = "sourced"
    payload = CatalogV2.model_validate(data)
    assert synthetic_ranking_snapshots(payload) == []
    assert synthetic_ranking_snapshots(payload, {"synthetic-v2": "permitted"})
    # A synthetic licence alone is enough, on a real-looking host.
    licensed = real_origin(ranked(bundle(tmp_path)))
    licensed["sources"][0]["license"] = "Synthetic fixture only"
    assert synthetic_ranking_snapshots(CatalogV2.model_validate(licensed))
    # A real origin with a real licence passes.
    real = CatalogV2.model_validate(real_origin(ranked(bundle(tmp_path))))
    assert synthetic_ranking_snapshots(real) == []
    check_synthetic_sources(real, allow_synthetic=False)


def test_cli_refuses_the_demo_bundle_unless_explicitly_allowed(capsys):
    module = load_import_script()
    args = [
        "--check",
        str(FIXTURES / "catalog-v2.demo.synthetic.json"),
        "--artifact-root",
        str(FIXTURES / "artifacts"),
    ]
    assert module.main(args) == 1
    assert "--allow-synthetic" in capsys.readouterr().err
    assert module.main([*args, "--allow-synthetic"]) == 0
    assert "valid" in capsys.readouterr().out


def test_cli_stage_refuses_before_touching_the_database(tmp_path, capsys):
    module = load_import_script()
    env = tmp_path / ".env"
    env.write_text("")
    args = [
        "--stage",
        str(FIXTURES / "catalog-v2.demo.synthetic.json"),
        "--artifact-root",
        str(FIXTURES / "artifacts"),
    ]
    assert module.main(args, env_path=env) == 1
    assert "refused" in capsys.readouterr().err


@needs_db
def test_publish_refuses_synthetic_ranking_evidence_when_asked(conn, tmp_path):  # noqa: F811
    data = ranked(bundle(tmp_path))
    batch = stage_catalog_v2(conn, CatalogV2.model_validate(data), artifact_root=tmp_path)
    with pytest.raises(SyntheticSourceError):
        publish_catalog_v2(conn, batch, artifact_root=tmp_path, allow_synthetic=False)
    assert not unpublished_source(conn)
    # The library default keeps test fixtures publishable.
    assert publish_catalog_v2(conn, batch, artifact_root=tmp_path) == "published"


# --- staged batch integrity (F-30, L10) -------------------------------------


@needs_db
def test_publish_rejects_a_staged_payload_changed_after_staging(conn, tmp_path):  # noqa: F811
    data = bundle(tmp_path)
    batch = stage_catalog_v2(conn, CatalogV2.model_validate(data), artifact_root=tmp_path)
    conn.execute(
        """UPDATE catalog_v2_batches
           SET payload = jsonb_set(payload, '{sources,0,ranking_permission}', '"permitted"')
           WHERE id = %s""",
        (batch,),
    )
    with pytest.raises(CatalogValidationError, match="differs from its hash"):
        publish_catalog_v2(conn, batch, artifact_root=tmp_path)
    assert not unpublished_source(conn)


# --- source key collisions (F-23) -------------------------------------------


@needs_db
@pytest.mark.parametrize(
    "field, value",
    [
        ("url", "https://other-origin.example.test/catalog"),
        ("market", "FR"),
        ("source_type", "public_dataset"),
    ],
)
def test_existing_source_key_cannot_lend_its_permission_to_another_origin(
    conn, tmp_path, field, value  # noqa: F811
):
    data = bundle(tmp_path)
    publish(conn, data, tmp_path)
    conn.execute("UPDATE sources SET ranking_permission = 'permitted'")
    other = copy.deepcopy(data)
    other["sources"][0][field] = value
    batch = stage_catalog_v2(
        conn, CatalogV2.model_validate(other), artifact_root=tmp_path
    )
    with pytest.raises(CatalogValidationError, match="differs from the stored source"):
        publish_catalog_v2(conn, batch, artifact_root=tmp_path)


# --- artifact reads never follow links or block (F-23) ----------------------


def test_artifacts_behind_a_symlinked_directory_fail_closed(tmp_path):
    data = bundle(tmp_path)
    payload = CatalogV2.model_validate(data)
    verify_artifacts(payload, tmp_path)
    first = Path(data["snapshots"][0]["artifact_path"])
    assert len(first.parts) > 1
    # Move the real directory and replace it with a link to the same content,
    # still inside the root: the read must not follow it.
    directory = tmp_path / first.parts[0]
    moved = tmp_path / "moved-elsewhere"
    directory.rename(moved)
    directory.symlink_to(moved, target_is_directory=True)
    with pytest.raises(CatalogValidationError, match="unsafe"):
        verify_artifacts(payload, tmp_path)


def test_artifact_that_is_a_fifo_fails_without_blocking(tmp_path):
    data = bundle(tmp_path)
    payload = CatalogV2.model_validate(data)
    path = tmp_path / data["snapshots"][0]["artifact_path"]
    path.unlink()
    os.mkfifo(path)
    with pytest.raises(CatalogValidationError, match="unsafe"):
        verify_artifacts(payload, tmp_path)


def test_artifact_root_may_itself_be_a_link(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    data = bundle(real)
    (tmp_path / "root-link").symlink_to(real, target_is_directory=True)
    verify_artifacts(CatalogV2.model_validate(data), tmp_path / "root-link")
