from __future__ import annotations

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
        batch = exchange.fetch_ohlcv(symbol=symbol, timeframe=timeframe, since=since, limit=limit)
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
