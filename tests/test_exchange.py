from __future__ import annotations

from types import SimpleNamespace

from trot.exchange import fetch_ohlcv


class FakeExchange:
    def __init__(self):
        self.calls = []
        self.markets = {"BTC/EUR": {"active": True, "precision": {"price": 2, "amount": 6}}}

    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
        self.calls.append({"symbol": symbol, "timeframe": timeframe, "since": since, "limit": limit})
        return [[1704067200000, 100.0, 101.0, 99.0, 100.5, 1.0]]

    def has(self, key):
        return key in {"fetchOHLCV": True, "watchOHLCV": True}


def test_fetch_ohlcv_is_read_only_and_uses_daily_candles(monkeypatch):
    fake = FakeExchange()

    def factory(*args, **kwargs):
        return fake

    monkeypatch.setattr("trot.exchange.ccxt.binance", factory)
    candles = fetch_ohlcv("BTC/EUR", "1d", start_ms=1704067200000, end_ms=1704153600000)

    assert candles
    assert candles[0][0] == 1704067200000
    assert fake.calls[0]["timeframe"] == "1d"
    assert fake.calls[0]["symbol"] == "BTC/EUR"
