"""
Tests for migration filename parsing and ordering.
"""

from pathlib import Path

import pytest

from data.migrations.migrator import (
    DEFAULT_MIGRATIONS_DIR,
    _list_pending_migrations,
    _parse_migration_path,
)
from exceptions import MigrationError


def test_parse_migration_filename_extracts_version_and_description() -> None:
    """V001__schema_migrations.sql parses to version 001 and a readable description."""
    path = Path("V001__schema_migrations.sql")
    version, description = _parse_migration_path(path)
    assert version == "001"
    assert description == "schema migrations"


def test_parse_migration_filename_rejects_invalid_name() -> None:
    """Non-conforming filenames raise MigrationError."""
    with pytest.raises(MigrationError):
        _parse_migration_path(Path("001_schema.sql"))


def test_list_pending_migrations_sorts_by_version() -> None:
    """Pending migrations are returned in ascending version order."""
    pending = _list_pending_migrations(DEFAULT_MIGRATIONS_DIR, applied_versions=set())
    versions = [item[0] for item in pending]
    assert versions == sorted(versions)
    assert versions[0] == "001"


def test_list_pending_migrations_skips_applied() -> None:
    """Already-applied versions are not returned as pending."""
    pending = _list_pending_migrations(
        DEFAULT_MIGRATIONS_DIR,
        applied_versions={"001", "002"},
    )
    versions = [item[0] for item in pending]
    assert "001" not in versions
    assert "002" not in versions
    if versions:
        assert versions[0] >= "003"


def test_v018_backtest_runs_fk_uses_on_delete_cascade() -> None:
    """BE-L2-001: V018 must rewire the backtest_runs FK to ON DELETE CASCADE."""
    sql = (DEFAULT_MIGRATIONS_DIR / "V018__backtest_runs_fk_cascade.sql").read_text()
    lower = sql.lower()
    assert "backtest_runs_user_id_fkey" in lower
    assert "on delete cascade" in lower
    assert "drop constraint" in lower


def test_v019_data_gaps_no_overlap_uses_exclude_gist() -> None:
    """BE-L2-015: V019 must add an EXCLUDE USING gist range constraint."""
    sql = (DEFAULT_MIGRATIONS_DIR / "V019__data_gaps_no_overlap.sql").read_text()
    lower = sql.lower()
    assert "exclude using gist" in lower
    assert "btree_gist" in lower
    assert "tstzrange" in lower


def test_migrator_advisory_lock_is_scoped_per_database() -> None:
    """BE-L2-020: advisory lock must be keyed by ``hashtext(current_database())``."""
    from data.migrations import migrator

    source = __import__("inspect").getsource(migrator)
    assert "hashtext(current_database())" in source
    # And explicitly used for both lock and unlock.
    assert "pg_advisory_lock(hashtext(current_database())" in source
    assert "pg_advisory_unlock(hashtext(current_database())" in source
