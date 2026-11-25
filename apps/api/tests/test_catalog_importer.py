"""F-12: a failed v1 import attempt never hides listings of an earlier completed run."""

import os
from pathlib import Path

import pytest
from psycopg.rows import dict_row

from app.db.migrations import apply_migrations
from app.ingestion import catalog
from app.ingestion.catalog import import_catalog, load_catalog
from tests.test_catalog_import import _cleanup_catalog_test_rows

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = ROOT / "data/fixtures/catalog/catalog-v1.synthetic.json"

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is not configured",
)


def _run(conn, run_id):
    return conn.execute(
        "SELECT status, error_message FROM import_runs WHERE id = %s", (run_id,)
    ).fetchone()


def _listing_run(conn, listing_ref):
    return conn.execute(
        "SELECT import_run_id FROM listings WHERE listing_ref = %s", (listing_ref,)
    ).fetchone()["import_run_id"]


def _visible(conn, listing_ref):
    return conn.execute(
        """SELECT 1 FROM listings l
           JOIN import_runs r ON r.id = l.import_run_id AND r.status = 'completed'
           WHERE l.listing_ref = %s""",
        (listing_ref,),
    ).fetchone() is not None


def test_failed_retry_keeps_the_completed_run_and_its_listings(monkeypatch):
    import psycopg

    database_url = os.environ["TEST_DATABASE_URL"]
    apply_migrations(database_url)
    with psycopg.connect(database_url, row_factory=dict_row, autocommit=True) as conn:
        _cleanup_catalog_test_rows(conn)
        try:
            dataset_a = load_catalog(FIXTURE_PATH).model_copy(deep=True)
            dataset_a.vehicles = dataset_a.vehicles[:1]
            dataset_a.variants = dataset_a.variants[:2]
            dataset_a.listings = dataset_a.listings[:2]
            untouched = dataset_a.listings[1].listing_ref
            first = import_catalog(conn, dataset_a, file_name="pytest-catalog-f12-a.json")

            # Dataset B rewrites only the first listing; the second stays on run A.
            dataset_b = dataset_a.model_copy(deep=True)
            dataset_b.listings = dataset_b.listings[:1]
            dataset_b.listings[0].price_eur += 100
            second = import_catalog(conn, dataset_b, file_name="pytest-catalog-f12-b.json")
            assert second.status == "completed"
            assert _listing_run(conn, untouched) == first.run_id

            # A retry of dataset A fails inside its transaction.
            def broken_listings(*args, **kwargs):
                raise RuntimeError("synthetic failure")

            with monkeypatch.context() as patch:
                patch.setattr(catalog, "_upsert_listings", broken_listings)
                with pytest.raises(RuntimeError, match="synthetic failure"):
                    import_catalog(conn, dataset_a, file_name="pytest-catalog-f12-retry.json")

            assert _run(conn, first.run_id)["status"] == "completed"
            assert _listing_run(conn, untouched) == first.run_id
            assert _visible(conn, untouched)
            failed = conn.execute(
                """SELECT id FROM import_runs
                   WHERE file_name = 'pytest-catalog-f12-retry.json'"""
            ).fetchall()
            assert len(failed) == 1 and failed[0]["id"] != first.run_id
            assert _run(conn, failed[0]["id"])["status"] == "failed"

            # A successful replay takes over the dataset hash and every listing.
            replayed = import_catalog(
                conn, dataset_a, file_name="pytest-catalog-f12-replay.json"
            )
            assert replayed.status == "completed"
            assert replayed.run_id not in {first.run_id, failed[0]["id"]}
            assert _listing_run(conn, untouched) == replayed.run_id
            assert _visible(conn, untouched)
            retired = _run(conn, first.run_id)
            assert retired["status"] == "failed"
            assert retired["error_message"] == (
                f"Superseded by import run {replayed.run_id}."
            )
        finally:
            _cleanup_catalog_test_rows(conn)
