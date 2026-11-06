from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trot.data import write_candles_parquet
from trot.exchange import validate_public_quote
from trot.main import main
from trot.models import MarketCandle


def test_public_quote_requires_fresh_ordered_prices():
    now = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    quote = validate_public_quote(
        {"timestamp": now.timestamp() * 1000, "bid": 99, "ask": 101},
        "kraken",
        now=now,
    )
    assert quote["mid"] == 100

    with pytest.raises(ValueError, match="stale"):
        validate_public_quote(
            {
                "timestamp": (now - timedelta(seconds=61)).timestamp() * 1000,
                "bid": 99,
                "ask": 101,
            },
            "kraken",
            now=now,
        )


def test_paper_cycle_persists_and_repeat_does_not_duplicate(
    monkeypatch, tmp_path, capsys
):
    now = datetime.now(UTC)
    last_open = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=1
    )
    candles = []
    price = Decimal(100)
    changes = [Decimal("0.004"), Decimal("0.012"), Decimal("0.002"), Decimal("0.018")]
    for index in range(35):
        timestamp = last_open - timedelta(days=34 - index)
        price *= Decimal(1) + changes[index % len(changes)]
        candles.append(
            MarketCandle(
                timestamp=timestamp,
                open=price,
                high=price * Decimal("1.02"),
                low=price * Decimal("0.98"),
                close=price,
                volume=Decimal(1),
                source="kraken",
            )
        )
    market_path = tmp_path / "history.parquet"
    write_candles_parquet(
        candles,
        market_path,
        "kraken",
        candles[0].timestamp.date().isoformat(),
        candles[-1].timestamp.date().isoformat(),
    )
    monkeypatch.setenv("TROT_DB_PATH", str(tmp_path / "paper.db"))
    monkeypatch.setattr(
        "trot.main.fetch_public_quote",
        lambda *args, **kwargs: {
            "source": "kraken",
            "timestamp": datetime.now(UTC),
            "mid": price,
        },
    )

    assert main(["paper", "cycle", "--data", str(market_path)]) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["simulated"] is True
    assert first["processed_candles"] == len(candles)

    assert main(["paper", "cycle", "--data", str(market_path)]) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["processed_candles"] == 0
    assert main(["paper", "status", "--recent", "2"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["simulated"] is True
    assert len(status["decisions"]) == 2
    with pytest.raises(ValueError, match="bid"):
        validate_public_quote(
            {"timestamp": now.timestamp() * 1000, "bid": 102, "ask": 101},
            "kraken",
            now=now,
        )
