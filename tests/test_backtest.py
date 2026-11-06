from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from trot.backtest import run_backtest
from trot.models import StrategyConfig


def test_backtest_is_deterministic_and_fills_after_signal(valid_candles):
    first = run_backtest(valid_candles, StrategyConfig(), initial_cash=Decimal(500))
    second = run_backtest(valid_candles, StrategyConfig(), initial_cash=Decimal(500))

    assert first == second
    assert first["label"] == "simulated research"
    assert set(first["cost_stress"]) == {"1x", "1.5x", "2x"}
    assert first["benchmarks"]["eur_cash"] is not None
    assert first["benchmarks"]["btc_buy_and_hold"] is not None
    assert {
        "net_return",
        "max_drawdown",
        "annualized_volatility",
        "sharpe_ratio",
        "trade_count",
        "turnover",
        "total_fees",
        "exposure_over_time",
    } <= first["metrics"].keys()
    for fill in first["fills"]:
        assert fill["execution_timestamp"] > fill["signal_timestamp"]
        signal_candle = next(
            candle
            for candle in valid_candles
            if candle.timestamp == fill["signal_timestamp"]
        )
        assert fill["execution_timestamp"] == signal_candle.timestamp + timedelta(
            days=1
        )


def test_backtest_rejects_gapped_history(valid_candles):
    with pytest.raises(ValueError, match="contiguous"):
        run_backtest([valid_candles[0], valid_candles[2], *valid_candles[3:]])


def test_walk_forward_fold_reports_only_test_window(valid_candles):
    train_end = valid_candles[24].timestamp.date()
    test_start = valid_candles[25].timestamp.date()
    test_end = valid_candles[-1].timestamp.date()
    result = run_backtest(
        valid_candles,
        folds=[(train_end.isoformat(), test_start.isoformat(), test_end.isoformat())],
    )

    fold = result["folds"][0]
    assert fold["test_start"] == test_start.isoformat()
    assert fold["metrics"]["observation_count"] == (test_end - test_start).days + 1
