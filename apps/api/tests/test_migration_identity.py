import os
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from app.db import migrations


def test_duplicate_versions_fail_before_connecting(tmp_path, monkeypatch):
    for name in ("0005_catalog.sql", "0005_knowledge.sql"):
        (tmp_path / name).write_text("SELECT 1")
    monkeypatch.setattr(
        migrations, "iter_migration_files", lambda _: sorted(tmp_path.glob("*.sql"))
    )
    with pytest.raises(ValueError, match="Duplicate migration version 0005"):
        migrations.run_migrations("not a database URL")


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="No test database")
def test_renamed_history_is_preserved_and_collisions_roll_back(monkeypatch):
    url = os.environ["TEST_DATABASE_URL"]
    schema = f"migration_identity_{uuid4().hex}"
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            conn.execute("""CREATE TABLE drivewise_schema_migrations (
                version text PRIMARY KEY, name text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT now())""")
            for old in migrations.RENAMED_MIGRATIONS:
                conn.execute(
                    "INSERT INTO drivewise_schema_migrations (version, name) VALUES (%s, %s)",
                    (old.split("_", 1)[0], old),
                )
            before = conn.execute(
                "SELECT applied_at FROM drivewise_schema_migrations ORDER BY version"
            ).fetchall()
            current = [
                migrations.Migration(new.split("_", 1)[0], new, "INVALID SQL")
                for new in migrations.RENAMED_MIGRATIONS.values()
            ]
            monkeypatch.setattr(migrations, "load_migrations", lambda: current)
            scoped_url = make_conninfo(url, options=f"-csearch_path={schema},public")
            assert migrations.run_migrations(scoped_url).applied == []
            assert migrations.run_migrations(scoped_url).already_applied == [
                m.name for m in current
            ]
            assert conn.execute(
                "SELECT applied_at FROM drivewise_schema_migrations ORDER BY version"
            ).fetchall() == before
            current.insert(0, migrations.Migration("0000", "0000_pending.sql", "CREATE TABLE pending (id int)"))
            current.append(migrations.Migration(current[-1].version, "collision.sql", "SELECT 1"))
            with pytest.raises(ValueError, match="already belongs to"):
                migrations.run_migrations(scoped_url)
            assert conn.execute("SELECT to_regclass('pending')").fetchone()[0] is None
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
