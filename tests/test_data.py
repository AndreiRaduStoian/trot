from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from trot.data import (
    read_candles_parquet,
    validate_candle,
    validate_candle_series,
    write_candles_parquet,
)


def test_validate_candle_rejects_invalid_ohlcv():
    with pytest.raises(ValueError):
        validate_candle(
            {
                "symbol": "BTC/EUR",
                "interval": "1d",
                "timestamp": "2024-01-01T00:00:00Z",
                "open": 100,
                "high": 95,
                "low": 99,
                "close": 101,
                "volume": 1.0,
                "source": "binance",
            }
        )


def test_validate_candle_series_rejects_duplicate_gap_and_incomplete_data(
    valid_candles, invalid_candles
):
    assert len(valid_candles) >= 30
    assert validate_candle_series(valid_candles) is True

    with pytest.raises(ValueError):
        validate_candle_series(invalid_candles)


def test_series_validation_rejects_incomplete_and_stale_current_history(valid_candles):
    with pytest.raises(ValueError, match="incomplete"):
        validate_candle_series(
            valid_candles,
            as_of=valid_candles[-1].timestamp + timedelta(hours=12),
        )

    expected_latest = datetime(2024, 2, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="stale"):
        validate_candle_series(
            valid_candles,
            as_of=expected_latest + timedelta(days=1),
            require_fresh=True,
        )


def test_parquet_round_trip_preserves_candles_and_manifest(valid_candles, tmp_path):
    output = tmp_path / "history.parquet"
    write_candles_parquet(
        valid_candles,
        output,
        "kraken",
        "2024-01-01",
        "2024-01-30",
    )

    loaded, manifest = read_candles_parquet(output)
    assert loaded == valid_candles
    assert manifest["source"] == "kraken"
    assert manifest["candle_count"] == len(valid_candles)
    assert manifest["normalized_sha256"]
