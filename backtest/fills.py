"""
Fill and cost models for backtest execution (D-38, D-39).
"""

from __future__ import annotations

from dataclasses import dataclass

from backtest.types import CommissionConfig, PositionSide


@dataclass(frozen=True)
class FillModel:
    """Applies adverse slippage in basis points to raw fill prices."""

    slippage_bps: float = 0.0

    def apply(self, price: float, side: PositionSide, *, is_entry: bool) -> float:
        """
        Return the fill price after slippage.

        Long entry pays more; long exit receives less. Short is inverse.
        """
        slip = self.slippage_bps / 10_000.0
        if side == "long":
            return price * (1.0 + slip) if is_entry else price * (1.0 - slip)
        return price * (1.0 - slip) if is_entry else price * (1.0 + slip)


@dataclass(frozen=True)
class CostModel:
    """Computes commission per fill from notional."""

    commission: CommissionConfig

    def compute(self, notional: float) -> float:
        """
        Compute commission for a single fill.

        Args:
            notional: Quote-currency value of the fill.

        Returns:
            Commission amount in quote currency.
        """
        if self.commission.type == "percent":
            return notional * self.commission.rate
        return self.commission.amount
