"""
Tests for backtest fill and cost models.
"""

from backtest.fills import CostModel, FillModel
from backtest.types import CommissionConfig


def test_long_entry_slippage_raises_fill_above_open() -> None:
    """Long entry with 10 bps slippage fills above the raw open."""
    fill_model = FillModel(slippage_bps=10.0)
    raw_open = 100.0
    fill = fill_model.apply(raw_open, "long", is_entry=True)
    assert fill == 100.1


def test_long_exit_slippage_lowers_fill_below_price() -> None:
    """Long exit with slippage receives less than the raw price."""
    fill_model = FillModel(slippage_bps=10.0)
    fill = fill_model.apply(100.0, "long", is_entry=False)
    assert fill == 99.9


def test_percent_commission_scales_with_notional() -> None:
    """Percent commission is proportional to fill notional."""
    cost_model = CostModel(CommissionConfig(type="percent", rate=0.001))
    assert cost_model.compute(10_000.0) == 10.0


def test_flat_commission_is_fixed_per_fill() -> None:
    """Flat commission returns a constant amount."""
    cost_model = CostModel(CommissionConfig(type="flat", amount=1.5))
    assert cost_model.compute(10_000.0) == 1.5
