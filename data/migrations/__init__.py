"""
Database migrations applied on application startup (Flyway-style versioned SQL).
"""

from data.migrations.migrator import run_migrations
from exceptions import MigrationError

__all__ = ["MigrationError", "run_migrations"]
