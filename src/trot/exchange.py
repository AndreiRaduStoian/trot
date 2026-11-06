from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import ccxt


def _make_exchange(source: str = "binance") -> Any:
    exchange_name = source.lower()
    if exchange_name == "binance":
        return ccxt.binance({"enableRateLimit": True, "timeout": 10000})
    if exchange_name == "coinbase":
        return ccxt.coinbase({"enableRateLimit": True, "timeout": 10000})
    if exchange_name == "kraken":
        return ccxt.kraken({"enableRateLimit": True, "timeout": 10000})
    raise ValueError(f"Unsupported exchange source: {source}")


def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    start_ms: int | None = None,
    end_ms: int | None = None,
    source: str = "binance",
    limit: int = 1000,
) -> list[list[Any]]:
    if symbol != "BTC/EUR":
        raise ValueError("Only BTC/EUR is supported in this feature")
    if timeframe != "1d":
        raise ValueError("Only 1d candles are supported in this feature")

    exchange = _make_exchange(source)
    has_fetch_ohlcv = False
    if hasattr(exchange, "has"):
        has_attr = exchange.has
        if callable(has_attr):
            has_fetch_ohlcv = bool(has_attr("fetchOHLCV"))
        elif isinstance(has_attr, dict):
            has_fetch_ohlcv = bool(has_attr.get("fetchOHLCV"))
    if not has_fetch_ohlcv:
        raise ValueError(f"Exchange {source} does not support OHLCV fetching")

    candles: list[list[Any]] = []
    since = start_ms
    while True:
        batch = exchange.fetch_ohlcv(
            symbol=symbol, timeframe=timeframe, since=since, limit=limit
        )
        if not batch:
            break

        for bar in batch:
            ts = int(bar[0])
            if end_ms is not None and ts > end_ms:
                continue
            candles.append(bar)

        last_ts = int(batch[-1][0])
        if end_ms is not None and last_ts >= end_ms:
            break
        since = last_ts + 86_400_000
        if since is None or since <= 0:
            break
        if len(batch) < limit:
            break

    return candles


def validate_public_quote(
    ticker: dict[str, Any],
    source: str,
    max_age_seconds: int = 60,
    now: datetime | None = None,
) -> dict[str, Any]:
    timestamp_ms = ticker.get("timestamp")
    if timestamp_ms is None:
        raise ValueError("public quote is missing an exchange timestamp")
    try:
        timestamp = datetime.fromtimestamp(float(timestamp_ms) / 1000, tz=UTC)
        bid = Decimal(str(ticker.get("bid")))
        ask = Decimal(str(ticker.get("ask")))
    except (TypeError, ValueError, InvalidOperation, OverflowError) as exc:
        raise ValueError("public quote contains invalid timestamp or prices") from exc
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        raise ValueError("quote validation time must be timezone-aware")
    if not bid.is_finite() or not ask.is_finite() or bid <= 0 or ask <= 0:
        raise ValueError("public quote bid and ask must be positive finite prices")
    if bid > ask:
        raise ValueError("public quote bid must not exceed ask")
    age = (current_time.astimezone(UTC) - timestamp).total_seconds()
    if age < 0 or age > max_age_seconds:
        raise ValueError(f"public quote is stale or future-dated (age {age:.1f}s)")
    received_at = current_time.astimezone(UTC)
    return {
        "source": source,
        "timestamp": timestamp,
        "received_at": received_at,
        "bid": bid,
        "ask": ask,
        "mid": (bid + ask) / Decimal(2),
    }


def fetch_public_quote(
    source: str = "kraken",
    symbol: str = "BTC/EUR",
    max_age_seconds: int = 60,
) -> dict[str, Any]:
    if symbol != "BTC/EUR":
        raise ValueError("Only BTC/EUR is supported in this feature")
    exchange = _make_exchange(source)
    if not hasattr(exchange, "fetch_ticker"):
        raise ValueError(f"Exchange {source} does not support public ticker retrieval")
    ticker = exchange.fetch_ticker(symbol)
    return validate_public_quote(ticker, source, max_age_seconds=max_age_seconds)
