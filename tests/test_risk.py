from __future__ import annotations

from trot.risk import realized_volatility, target_allocation


def test_realized_volatility_and_target_allocation_use_daily_returns():
    returns = [0.01, -0.02, 0.015, 0.03, -0.01, 0.02, 0.025, 0.005, -0.015, 0.01]
    vol = realized_volatility(returns)
    assert vol > 0

    allocation = target_allocation(500.0, vol, 0.12, 0.5)
    assert 0.0 <= allocation <= 0.5


def test_zero_or_invalid_volatility_abstains():
    assert target_allocation(500.0, 0.0, 0.12, 0.5) == 0.0
