"""Migration 0016, migration checksums and the session retention purge."""

import hashlib
import importlib.util
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.types.json import Jsonb

from app.db import migrations
from app.db.migrations import MIGRATIONS_PATH
from tests.test_catalog_v2_publication import bundle, conn, publish  # noqa: F401


ROOT = Path(__file__).resolve().parents[3]
PURGE_SCRIPT = ROOT / "apps/api/scripts/purge_expired_sessions.py"
MIGRATION_0016 = MIGRATIONS_PATH / "0016_security_and_integrity_hardening.sql"
NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)


def load_purge_script():
    spec = importlib.util.spec_from_file_location("drivewise_purge_script", PURGE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Dataclasses resolve their annotations through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# --- Migration 0016: static shape ---------------------------------------------------


def test_0016_is_additive_and_names_every_hardening_step():
    text = MIGRATION_0016.read_text()

    for table in ("source_snapshots", "spec_observations", "fact_decisions"):
        assert f"BEFORE TRUNCATE ON {table}" in text
    assert "EXECUTE FUNCTION drivewise_reject_evidence_mutation()" in text
    assert "DROP CONSTRAINT source_snapshots_source_url_check" in text
    assert "CHECK (source_url ~ '^https://" in text
    assert "EXCEPTION WHEN data_exception THEN" in text
    assert "d.actor_kind IN ('human', 'rule')" in text
    assert "idx_fact_decisions_spec_metric" in text
    assert "idx_guided_decisions_updated_at" in text
    # The migration replays under the test search_path: nothing is schema-qualified.
    assert "public." not in text
    for destructive in ("DROP TABLE", "DELETE FROM", "UPDATE "):
        assert destructive not in text


# --- Migration checksums -------------------------------------------------------------


def test_migration_checksum_is_the_sha256_of_its_sql():
    migration = migrations.Migration("9999", "9999_example.sql", "SELECT 1;\n")

    assert migration.checksum == hashlib.sha256(b"SELECT 1;\n").hexdigest()


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="No test database")
def test_edited_applied_migration_fails_and_legacy_rows_are_trusted(monkeypatch):
    url = os.environ["TEST_DATABASE_URL"]
    schema = f"migration_checksum_{uuid4().hex}"
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            admin.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            # A ledger written before checksums existed.
            admin.execute("""CREATE TABLE drivewise_schema_migrations (
                version text PRIMARY KEY, name text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT now())""")
            admin.execute(
                "INSERT INTO drivewise_schema_migrations (version, name) "
                "VALUES ('0001', '0001_legacy.sql')"
            )
            current = [
                migrations.Migration("0001", "0001_legacy.sql", "edited later"),
                migrations.Migration(
                    "0002", "0002_new.sql", "CREATE TABLE checksum_probe (id int)"
                ),
            ]
            monkeypatch.setattr(migrations, "load_migrations", lambda: current)
            scoped_url = make_conninfo(url, options=f"-csearch_path={schema},public")

            assert migrations.run_migrations(scoped_url).applied == ["0002_new.sql"]
            stored = dict(
                admin.execute(
                    "SELECT version, checksum FROM drivewise_schema_migrations"
                ).fetchall()
            )
            # A legacy row keeps NULL and is not verified; a new one is recorded.
            assert stored == {"0001": None, "0002": current[1].checksum}
            assert migrations.run_migrations(scoped_url).already_applied == [
                "0001_legacy.sql",
                "0002_new.sql",
            ]

            current[1] = migrations.Migration(
                "0002", "0002_new.sql", "CREATE TABLE checksum_probe (id bigint)"
            )
            with pytest.raises(ValueError, match="0002_new.sql changed after"):
                migrations.run_migrations(scoped_url)
        finally:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


# --- Migration 0016: behaviour on a database ----------------------------------------


@pytest.mark.parametrize(
    "statement",
    [
        "TRUNCATE source_snapshots CASCADE",
        "TRUNCATE spec_observations CASCADE",
        "TRUNCATE fact_decisions CASCADE",
    ],
)
def test_truncate_cannot_bypass_append_only_evidence(conn, statement):  # noqa: F811
    with pytest.raises(psycopg.errors.CheckViolation, match="append-only"):
        with conn.transaction():
            conn.execute(statement)


def test_snapshot_url_must_be_https(conn):  # noqa: F811
    source_id = conn.execute("SELECT id FROM sources LIMIT 1").fetchone()["id"]

    def insert(url):
        conn.execute(
            """INSERT INTO source_snapshots (id, source_id, source_url, retrieved_at,
                 content_sha256, artifact_path, media_type, evidence_kind)
               VALUES (%s, %s, %s, now(), %s, 'evidence/page.html', 'text/html',
                 'sourced')""",
            (uuid4(), source_id, url, "a" * 64),
        )

    with pytest.raises(psycopg.errors.CheckViolation):
        with conn.transaction():
            insert("http://example.test/page")
    with conn.transaction(force_rollback=True):
        insert("https://example.test/page")


def test_iso_date_helper_is_false_never_an_error(conn):  # noqa: F811
    cases = {
        "2024-02-29": True,
        "2026-02-30": False,
        "2026-13-01": False,
        "0000-01-01": False,
        "26-01-01": False,
        "2026-01-01T00:00": False,
        "tomorrow": False,
    }
    for value, expected in cases.items():
        row = conn.execute("SELECT catalog_iso_date_valid(%s) AS ok", (value,)).fetchone()
        assert row["ok"] is expected, value
    assert conn.execute("SELECT catalog_iso_date_valid(NULL) AS ok").fetchone()["ok"] is False


@pytest.mark.parametrize(
    ("context", "accepted"),
    [
        ({"market": "IT", "valid_from": "2024-01-01", "valid_to": "2024-12-31"}, True),
        ({"market": "IT", "valid_from": None}, True),
        ({"market": "IT", "valid_from": "2026-02-30"}, False),
        ({"market": "IT", "valid_to": "31/12/2024"}, False),
        ({"market": "IT", "valid_to": 20241231}, False),
    ],
)
def test_decision_validity_dates_must_be_calendar_dates(conn, context, accepted):  # noqa: F811
    spec_id = conn.execute("SELECT id FROM vehicle_specs LIMIT 1").fetchone()["id"]

    def insert():
        conn.execute(
            """INSERT INTO fact_decisions (id, spec_id, metric, context, status,
                 reason, actor_kind, actor_id, policy_version, decided_at)
               VALUES (%s, %s, 'seats', %s, 'unknown', 'date check', 'human',
                 'tester', 'test-policy', now())""",
            (uuid4(), spec_id, Jsonb(context)),
        )

    if accepted:
        with conn.transaction(force_rollback=True):
            insert()
    else:
        with pytest.raises(psycopg.errors.CheckViolation):
            with conn.transaction():
                insert()


def _supersede(db, decision_id, *, actor_kind, seconds):
    new_id = uuid4()
    db.execute(
        """INSERT INTO fact_decisions (id, spec_id, metric, context, status,
             selected_observation_id, evidence_ids, supersedes_id, reason,
             actor_kind, actor_id, policy_version, decided_at)
           SELECT %s, spec_id, metric, context, status, selected_observation_id,
             evidence_ids, id, 'revision', %s, 'tester', policy_version,
             decided_at + make_interval(secs => %s)
           FROM fact_decisions WHERE id = %s""",
        (new_id, actor_kind, seconds, decision_id),
    )
    return new_id


def _eligible(db, decision_id):
    return db.execute(
        "SELECT eligible FROM catalog_current_facts WHERE id = %s", (decision_id,)
    ).fetchone()["eligible"]


def test_agent_decision_needs_human_or_rule_sign_off_to_rank(conn, tmp_path):  # noqa: F811
    data = bundle(tmp_path)
    for snapshot in data["snapshots"]:
        snapshot["evidence_kind"] = "sourced"
    publish(conn, data, tmp_path)
    conn.execute(
        "UPDATE sources SET ranking_permission = 'permitted' "
        "WHERE source_key = 'synthetic-v2'"
    )
    fact = conn.execute(
        """SELECT id FROM catalog_current_facts
           WHERE eligible AND actor_kind = 'human' ORDER BY spec_id, metric LIMIT 1"""
    ).fetchone()
    assert fact is not None

    agent = _supersede(conn, fact["id"], actor_kind="agent", seconds=1)
    assert _eligible(conn, agent) is False
    assert not conn.execute(
        "SELECT 1 FROM catalog_scalar_facts WHERE id = %s", (agent,)
    ).fetchone()

    signed_off = _supersede(conn, agent, actor_kind="rule", seconds=2)
    assert _eligible(conn, signed_off) is True


# --- F-13: session retention purge --------------------------------------------------


def test_purge_parses_days_and_defaults_to_a_dry_run():
    script = load_purge_script()

    args = script.parse_args([])
    assert (args.days, args.execute) == (30, False)
    assert script.parse_args(["--days", "7", "--execute"]).execute is True
    for bad in ("0", "-1", "ten"):
        with pytest.raises(SystemExit):
            script.parse_args(["--days", bad])
    with pytest.raises(ValueError):
        script.purge_expired_sessions(object(), days=0, execute=False)


class FakeResult:
    def __init__(self, row=None, rowcount=-1):
        self.row = row
        self.rowcount = rowcount

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self):
        self.calls = []

    def execute(self, query, params=None):
        self.calls.append((query, params))
        if query.lstrip().startswith("SELECT"):
            return FakeResult(
                {
                    "guided_decisions": 2,
                    "guided_decision_turns": 5,
                    "recommendation_runs": 1,
                    "recommendation_items": 3,
                }
            )
        return FakeResult(rowcount=2 if "guided_decisions" in query else 1)


def test_purge_dry_run_only_counts_and_execute_deletes_with_one_cutoff():
    script = load_purge_script()

    dry = FakeConnection()
    report = script.purge_expired_sessions(dry, days=30, execute=False, now=NOW)
    assert len(dry.calls) == 1
    assert report.cutoff == NOW - timedelta(days=30)
    assert report.counts["guided_decision_turns"] == 5
    assert "Would delete 2 guided_decisions" in script.format_report(report)
    assert "Dry run" in script.format_report(report)

    live = FakeConnection()
    report = script.purge_expired_sessions(live, days=30, execute=True, now=NOW)
    assert [query.split()[0] for query, _ in live.calls] == ["SELECT", "DELETE", "DELETE"]
    assert {params["cutoff"] for _, params in live.calls} == {NOW - timedelta(days=30)}
    assert "Deleted 3 recommendation_items" in script.format_report(report)


def test_purge_requires_a_database_url(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    script = load_purge_script()

    assert script.main([], env_path=tmp_path / ".env") == 1
    assert "DATABASE_URL is not set" in capsys.readouterr().err


def test_purge_deletes_only_expired_sessions_and_their_children(conn):  # noqa: F811
    script = load_purge_script()
    vehicle_id = conn.execute("SELECT id FROM vehicles LIMIT 1").fetchone()["id"]
    ids = {}
    for label, age in (("old", 31), ("fresh", 29)):
        stamp = NOW - timedelta(days=age)
        decision_id, run_id = uuid4(), uuid4()
        ids[label] = (decision_id, run_id)
        conn.execute(
            """INSERT INTO guided_decisions (id, locale, market, created_at, updated_at)
               VALUES (%s, 'it-IT', 'IT', %s, %s)""",
            (decision_id, stamp, stamp),
        )
        conn.execute(
            """INSERT INTO guided_decision_turns (id, decision_id, profile_version,
                 user_message, assistant_message, profile_snapshot, response_payload)
               VALUES (%s, %s, 1, 'ciao', 'ciao', '{}', '{}')""",
            (uuid4(), decision_id),
        )
        conn.execute(
            "INSERT INTO recommendation_runs (id, created_at) VALUES (%s, %s)",
            (run_id, stamp),
        )
        conn.execute(
            """INSERT INTO recommendation_items (id, run_id, vehicle_id, rank)
               VALUES (%s, %s, %s, 1)""",
            (uuid4(), run_id, vehicle_id),
        )

    def remaining(table, column, value):
        return conn.execute(
            sql.SQL("SELECT count(*) AS n FROM {} WHERE {} = %s").format(
                sql.Identifier(table), sql.Identifier(column)
            ),
            (value,),
        ).fetchone()["n"]

    dry = script.purge_expired_sessions(conn, days=30, execute=False, now=NOW)
    assert dry.counts == {
        "guided_decisions": 1,
        "guided_decision_turns": 1,
        "recommendation_runs": 1,
        "recommendation_items": 1,
    }
    assert remaining("guided_decisions", "id", ids["old"][0]) == 1

    done = script.purge_expired_sessions(conn, days=30, execute=True, now=NOW)
    assert done.counts == dry.counts
    old_decision, old_run = ids["old"]
    fresh_decision, fresh_run = ids["fresh"]
    assert remaining("guided_decisions", "id", old_decision) == 0
    assert remaining("guided_decision_turns", "decision_id", old_decision) == 0
    assert remaining("recommendation_runs", "id", old_run) == 0
    assert remaining("recommendation_items", "run_id", old_run) == 0
    assert remaining("guided_decisions", "id", fresh_decision) == 1
    assert remaining("guided_decision_turns", "decision_id", fresh_decision) == 1
    assert remaining("recommendation_runs", "id", fresh_run) == 1
    assert remaining("recommendation_items", "run_id", fresh_run) == 1
