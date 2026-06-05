"""
Apply versioned SQL migrations on application startup (Flyway-style).

Migration files live in data/migrations/sql/ as V{version}__{description}.sql.
Applied versions are recorded in schema_migrations (V001 creates that table).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import psycopg

from data.db import connect
from data.migrations import queries
from exceptions import MigrationError

logger = logging.getLogger(__name__)

MIGRATION_FILENAME_PATTERN = re.compile(r"^V(\d+)__(.+)\.sql$")
DEFAULT_MIGRATIONS_DIR = Path(__file__).parent / "sql"


def _parse_migration_path(path: Path) -> tuple[str, str]:
    """
    Parse a migration filename into version and description.

    Args:
        path: Path to a V###__name.sql file.

    Returns:
        Tuple of (version, description) where version is zero-padded digits.

    Raises:
        MigrationError: If the filename does not match the naming convention.
    """
    match = MIGRATION_FILENAME_PATTERN.match(path.name)
    if not match:
        raise MigrationError(
            f"Invalid migration filename: {path.name}. " f"Expected format: V001__description.sql"
        )
    version_number, description = match.groups()
    return version_number.zfill(3), description.replace("_", " ")


def _list_pending_migrations(
    migrations_dir: Path,
    applied_versions: set[str],
) -> list[tuple[str, str, Path]]:
    """
    List migration files not yet applied, sorted by version.

    Args:
        migrations_dir: Directory containing V*.sql files.
        applied_versions: Versions already recorded in schema_migrations.

    Returns:
        List of (version, description, path) tuples in ascending version order.
    """
    pending: list[tuple[str, str, Path, int]] = []
    for path in migrations_dir.glob("V*.sql"):
        version, description = _parse_migration_path(path)
        if version not in applied_versions:
            pending.append((version, description, path, int(version)))
    pending.sort(key=lambda item: item[3])
    return [(v, d, p) for v, d, p, _ in pending]


def run_migrations(
    migrations_dir: Path | None = None,
    conn: psycopg.Connection | None = None,
) -> int:
    """
    Apply all pending SQL migrations in version order.

    Safe to call on every application startup: already-applied versions are skipped.
    The first migration (V001) creates the schema_migrations history table.

    Args:
        migrations_dir: Override path to SQL files (defaults to data/migrations/sql).
        conn: Optional existing connection.

    Returns:
        Number of migrations applied in this run (0 if database is up to date).

    Raises:
        MigrationError: On invalid filenames or SQL execution failures.
        FileNotFoundError: If the migrations directory does not exist.
    """
    sql_dir = migrations_dir or DEFAULT_MIGRATIONS_DIR
    if not sql_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found: {sql_dir}")

    own_conn = conn is None
    if own_conn:
        conn = connect()

    applied_count = 0
    try:
        applied_versions = _load_applied_versions(conn)
        pending = _list_pending_migrations(sql_dir, applied_versions)

        if not pending and applied_versions:
            logger.debug("Database migrations are up to date")
            return 0

        for version, description, path in pending:
            sql = path.read_text(encoding="utf-8").strip()
            if not sql:
                raise MigrationError(f"Migration file is empty: {path.name}")

            logger.info("Applying migration V%s: %s", version, description)
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    queries.INSERT_APPLIED_MIGRATION,
                    (f"V{version}", description),
                )
            conn.commit()
            applied_count += 1
            logger.info("Applied migration V%s", version)

        if applied_count == 0 and not applied_versions:
            logger.info("Database schema initialized (no pending migrations)")
    finally:
        if own_conn:
            conn.close()

    return applied_count


def _load_applied_versions(conn: psycopg.Connection) -> set[str]:
    """
    Load applied migration versions from schema_migrations.

    Returns an empty set when the history table does not exist yet (first startup).
    """
    try:
        with conn.cursor() as cur:
            cur.execute(queries.SELECT_APPLIED_VERSIONS)
            rows = cur.fetchall()
        return {row[0].replace("V", "") for row in rows}
    except psycopg.errors.UndefinedTable:
        conn.rollback()
        return set()
