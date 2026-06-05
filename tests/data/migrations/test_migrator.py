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
