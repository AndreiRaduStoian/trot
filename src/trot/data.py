from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from .models import MarketCandle


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value) / 1000, tz=UTC)

    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp: {value!r}") from exc
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    raise ValueError(f"Unsupported timestamp data: {type(value).__name__}")


def _to_decimal(value: Any, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        result = value
    else:
        try:
            result = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid {field_name}: {value!r}") from exc

    if not math.isfinite(float(result)):
        raise ValueError(f"Non-finite {field_name}: {value!r}")
    return result


def validate_candle(value: dict[str, Any] | MarketCandle) -> MarketCandle:
    if isinstance(value, MarketCandle):
        candle = value
    else:
        candle = MarketCandle(
            symbol=str(value.get("symbol", "BTC/EUR")),
            interval=str(value.get("interval", "1d")),
            timestamp=value.get("timestamp"),
            open=value.get("open"),
            high=value.get("high"),
            low=value.get("low"),
            close=value.get("close"),
            volume=value.get("volume"),
            source=value.get("source"),
            metadata=value.get("metadata", {}),
        )

    if candle.symbol != "BTC/EUR":
        raise ValueError("symbol must be BTC/EUR")
    if candle.interval != "1d":
        raise ValueError("interval must be 1d")
    if candle.source is None or not str(candle.source).strip():
        raise ValueError("source is required")
    if candle.timestamp is None:
        raise ValueError("timestamp is required")

    ts = _parse_timestamp(candle.timestamp)
    if ts.utcoffset() != UTC.utcoffset(ts):
        ts = ts.astimezone(UTC)

    open_price = _to_decimal(candle.open, "open")
    high_price = _to_decimal(candle.high, "high")
    low_price = _to_decimal(candle.low, "low")
    close_price = _to_decimal(candle.close, "close")
    volume = _to_decimal(candle.volume, "volume")

    if volume < 0:
        raise ValueError("volume must be non-negative")
    if open_price <= 0 or high_price <= 0 or low_price <= 0 or close_price <= 0:
        raise ValueError("OHLC prices must be positive")
    if high_price < max(open_price, close_price, low_price):
        raise ValueError("high must be at least max(open, close, low)")
    if low_price > min(open_price, close_price, high_price):
        raise ValueError("low must be at most min(open, close, high)")
    if ts.hour != 0 or ts.minute != 0 or ts.second != 0 or ts.microsecond != 0:
        raise ValueError("timestamp must be UTC interval-start at midnight")

    return MarketCandle(
        symbol="BTC/EUR",
        interval="1d",
        timestamp=ts,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        source=str(candle.source),
        metadata=dict(candle.metadata),
    )


def candle_to_epoch_ms(candle: MarketCandle | dict[str, Any]) -> int:
    normalized = validate_candle(candle)
    timestamp = normalized.timestamp
    assert timestamp is not None
    return int(timestamp.timestamp() * 1000)


def validate_candle_series(candles: list[MarketCandle | dict[str, Any]]) -> bool:
    if not candles:
        raise ValueError("candle series cannot be empty")

    normalised: list[MarketCandle] = []
    seen: set[int] = set()
    previous_ts: datetime | None = None

    for candle in candles:
        validated = validate_candle(candle)
        ts = validated.timestamp
        if ts is None:
            raise ValueError("candle timestamp is required")
        ts_ms = int(ts.timestamp() * 1000)
        if ts_ms in seen:
            raise ValueError("duplicate timestamp detected")
        seen.add(ts_ms)
        normalised.append(validated)
        if previous_ts is not None:
            delta = ts - previous_ts
            if delta != timedelta(days=1):
                raise ValueError("timestamps must be strictly daily and contiguous")
        previous_ts = ts

    if len(normalised) < 2:
        raise ValueError("at least two completed candles are required for validation")

    return True
