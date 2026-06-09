"""
Tests for the run_poc compatibility wrapper.
"""

import run_backtest
import run_poc


def test_run_poc_reexports_backtest_entrypoints() -> None:
    """Legacy module keeps the same call targets after rename."""
    assert run_poc.main is run_backtest.main
    assert run_poc.ensure_data is run_backtest.ensure_data
