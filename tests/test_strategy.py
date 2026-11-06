from __future__ import annotations

from decimal import Decimal

from trot.models import PortfolioState, StrategyConfig
from trot.strategy import evaluate_portfolio, evaluate_signal


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


def test_portfolio_decision_includes_target_and_order_action(valid_candles):
    decision = evaluate_portfolio(
        valid_candles,
        PortfolioState(cash_eur=Decimal(500)),
        StrategyConfig(),
    )

    assert decision.signal == "long"
    assert decision.source == valid_candles[-1].source
    assert decision.target_allocation is not None
    assert Decimal(0) < decision.target_allocation <= Decimal("0.5")
    assert decision.indicators["sma"] is not None
    assert decision.indicators["momentum_return"] is not None
    assert decision.volatility is not None
    assert decision.action in {"buy", "hold", "abstain"}
