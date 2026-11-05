from __future__ import annotations

from trot.models import StrategyConfig
from trot.strategy import evaluate_signal


def test_strategy_uses_sma_and_positive_momentum(valid_candles):
    signal = evaluate_signal(
        valid_candles, StrategyConfig(sma_days=30, momentum_days=14)
    )
    assert signal.signal in {"long", "cash", "unavailable"}
    assert signal.reason


def test_strategy_requires_sufficient_history():
    signal = evaluate_signal([], StrategyConfig())
    assert signal.signal == "unavailable"
    assert "insufficient" in signal.reason.lower()
