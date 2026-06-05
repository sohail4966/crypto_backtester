"""
Tests that candle DML SQL is centralized in the repository queries module.
"""

from data.repository import queries


def test_queries_module_defines_candle_dml_statements() -> None:
    """Every expected native DML query constant exists and is non-empty."""
    expected = (
        "UPSERT_CANDLE",
        "SELECT_CANDLES_BY_RANGE",
        "COUNT_CANDLES",
    )
    for name in expected:
        sql = getattr(queries, name)
        assert isinstance(sql, str)
        assert sql.strip(), f"{name} must not be empty"


def test_queries_module_has_no_ddl_constants() -> None:
    """Table DDL is owned by data/migrations/sql, not repository queries."""
    assert not hasattr(queries, "CREATE_CANDLES_TABLE")
    assert not hasattr(queries, "CREATE_CANDLES_HYPERTABLE")
