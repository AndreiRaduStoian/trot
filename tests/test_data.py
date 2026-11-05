from __future__ import annotations

import pytest

from trot.data import validate_candle, validate_candle_series


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
