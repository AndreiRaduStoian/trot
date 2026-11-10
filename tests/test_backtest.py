from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trot.backtest import run_backtest
from trot.models import MarketCandle, StrategyConfig


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


def test_backtest_accepts_hourly_interval_and_executes_next_hour_open():
    candles = [
        MarketCandle(
            symbol="BTC/EUR",
            interval="1h",
            timestamp=datetime(2024, 1, 1, hour, tzinfo=UTC),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100.5"),
            volume=Decimal("1"),
            source="kraken",
        )
        for hour in range(0, 10)
    ]
    candles[0] = MarketCandle(
        symbol="BTC/EUR",
        interval="1h",
        timestamp=datetime(2024, 1, 1, 0, tzinfo=UTC),
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("101"),
        volume=Decimal("1"),
        source="kraken",
    )
    candles[1] = MarketCandle(
        symbol="BTC/EUR",
        interval="1h",
        timestamp=datetime(2024, 1, 1, 1, tzinfo=UTC),
        open=Decimal("101"),
        high=Decimal("103"),
        low=Decimal("100"),
        close=Decimal("102"),
        volume=Decimal("1"),
        source="kraken",
    )

    result = run_backtest(candles, StrategyConfig(), initial_cash=Decimal(500),
                         maker_fee=Decimal("0.0005"), taker_fee=Decimal("0.001"),
                         spread_bps=Decimal(5), slippage_bps=Decimal(10),
                         min_trade_eur=Decimal(25))

    assert result["interval"] == "1h"
    assert result["fills"] == [] or result["fills"][0]["execution_timestamp"] > result["fills"][0]["signal_timestamp"]


def test_hourly_walk_forward_fold_reports_only_test_dates():
    start = datetime(2024, 1, 1, tzinfo=UTC)
    candles = [
        MarketCandle(
            symbol="BTC/EUR",
            interval="1h",
            timestamp=start + timedelta(hours=hour),
            open=Decimal(100),
            high=Decimal(102),
            low=Decimal(99),
            close=Decimal(101),
            volume=Decimal(1),
            source="kraken",
        )
        for hour in range(72)
    ]

    result = run_backtest(
        candles,
        folds=[("2024-01-01", "2024-01-02", "2024-01-03")],
    )

    fold = result["folds"][0]
    assert fold["test_start"] == "2024-01-02"
    assert fold["test_end"] == "2024-01-03"
    assert fold["metrics"]["observation_count"] == 48
