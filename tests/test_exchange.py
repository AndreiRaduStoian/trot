from __future__ import annotations

from trot.exchange import fetch_ohlcv


class FakeExchange:
    def __init__(self):
        self.calls = []
        self.markets = {
            "BTC/EUR": {"active": True, "precision": {"price": 2, "amount": 6}}
        }

    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
        self.calls.append(
            {"symbol": symbol, "timeframe": timeframe, "since": since, "limit": limit}
        )
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


def test_fetch_ohlcv_ignores_newer_candles_outside_requested_range(monkeypatch):
    class LatestOnlyExchange:
        def __init__(self):
            self.calls = []

        def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
            self.calls.append(since)
            if since == 1703980800000:
                return [[1704153600000, 101.0, 102.0, 100.0, 101.5, 1.0]]
            return []

        def has(self, key):
            return key in {"fetchOHLCV": True, "watchOHLCV": True}

    fake = LatestOnlyExchange()

    def factory(*args, **kwargs):
        return fake

    monkeypatch.setattr("trot.exchange.ccxt.binance", factory)
    candles = fetch_ohlcv(
        "BTC/EUR",
        "1d",
        start_ms=1703980800000,
        end_ms=1704153599999,
    )

    assert candles == []
    assert fake.calls[0] == 1703980800000
    assert len(fake.calls) == 1


def test_fetch_ohlcv_paginates_forward_through_requested_hourly_range(monkeypatch):
    first_ms = 1704067200000
    rows = [
        [first_ms + hour * 3_600_000, 100.0, 101.0, 99.0, 100.5, 1.0]
        for hour in range(4)
    ]

    class PagedExchange:
        def __init__(self):
            self.calls = []

        def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
            self.calls.append(since)
            return [row for row in rows if row[0] >= since][:limit]

        def has(self, key):
            return key == "fetchOHLCV"

    fake = PagedExchange()
    monkeypatch.setattr("trot.exchange.ccxt.binance", lambda *args, **kwargs: fake)

    candles = fetch_ohlcv(
        "BTC/EUR",
        "1h",
        start_ms=first_ms,
        end_ms=first_ms + 4 * 3_600_000 - 1,
        limit=2,
    )

    assert [row[0] for row in candles] == [row[0] for row in rows]
    assert fake.calls == [first_ms, first_ms + 2 * 3_600_000]
