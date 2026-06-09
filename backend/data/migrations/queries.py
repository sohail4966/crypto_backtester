"""
Native SQL for the schema_migrations history table.

DDL for application tables lives in data/migrations/sql/*.sql, not here.
"""

SELECT_APPLIED_VERSIONS = """
SELECT version FROM schema_migrations ORDER BY version
"""

INSERT_APPLIED_MIGRATION = """
INSERT INTO schema_migrations (version, description)
VALUES (%s, %s)
"""
