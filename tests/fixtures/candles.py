from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from trot.models import MarketCandle


def utc_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def candle(ts: str, open_: float, high: float, low: float, close: float, volume: float = 1.0, source: str = "binance") -> MarketCandle:
    return MarketCandle(
        symbol="BTC/EUR",
        interval="1d",
        timestamp=utc_iso(ts),
        open=Decimal(str(open_)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(close)),
        volume=Decimal(str(volume)),
        source=source,
    )


def make_valid_series() -> list[MarketCandle]:
    start = utc_iso("2024-01-01T00:00:00Z")
    prices = [100.0, 101.5, 103.0, 104.0, 105.5, 107.0, 108.7, 110.2, 111.8, 113.0, 114.5, 115.8, 117.2, 118.0, 119.1, 120.4, 121.0, 122.3, 123.0, 124.5, 126.0, 127.4, 128.2, 130.0, 131.5, 133.2, 134.0, 135.7, 136.9, 137.5]
    candles: list[MarketCandle] = []
    for idx, price in enumerate(prices):
        day = start + timedelta(days=idx)
        candles.append(
            candle(
                day.strftime("%Y-%m-%dT00:00:00Z"),
                price,
                price * 1.02,
                price * 0.98,
                price * 1.01,
                volume=1.0,
            )
        )
    return candles


def make_invalid_series() -> list[MarketCandle]:
    return [
        candle("2024-01-01T00:00:00Z", 100.0, 101.0, 99.0, 100.5, volume=1.0),
        candle("2024-01-02T00:00:00Z", 101.0, 102.0, 100.0, 100.8, volume=1.0),
        candle("2024-01-02T00:00:00Z", 101.5, 103.0, 100.5, 101.7, volume=1.0),
        candle("2024-01-03T00:00:00Z", 101.0, 100.0, 90.0, 95.0, volume=1.0),
    ]
