from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trot.storage import get_paper_status, initialize_database, persist_paper_cycle


def test_paper_cycle_is_atomic_and_idempotent(tmp_path):
    database = tmp_path / "paper.db"
    initialize_database(database)
    candle_time = datetime(2024, 1, 1, tzinfo=UTC)
    decision = {
        "signal": "cash",
        "action": "hold",
        "reason": "no entry conditions",
        "validation_outcome": "valid",
    }
    arguments = {
        "database_path": database,
        "account_id": "default",
        "strategy_id": "trend-volatility-v1",
        "config_hash": "config-hash",
        "candle_timestamp": candle_time,
        "source": "kraken",
        "decision": decision,
        "initial_cash": Decimal(500),
        "cash_after": Decimal(500),
        "btc_after": Decimal(0),
    }

    assert persist_paper_cycle(**arguments) is True
    assert persist_paper_cycle(**arguments) is False
    state = get_paper_status(database, "default", 10)
    assert state["account"]["cash_eur"] == "500"
    assert len(state["decisions"]) == 1


def test_paper_cycle_rolls_back_invalid_order_association(tmp_path):
    database = tmp_path / "paper.db"
    initialize_database(database)
    with pytest.raises(sqlite3.IntegrityError):
        persist_paper_cycle(
            database_path=database,
            account_id="default",
            strategy_id="trend-volatility-v1",
            config_hash="config-hash",
            candle_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            source="kraken",
            decision={"signal": "long", "action": "buy", "reason": "entry"},
            initial_cash=Decimal(500),
            cash_after=Decimal(400),
            btc_after=Decimal("0.01"),
            fill={
                "order_id": "missing-order",
                "fee_eur": "1",
                "execution_ts_ms": 1_704_067_200_000,
            },
        )
    state = get_paper_status(database, "default", 10)
    assert state["decisions"] == []
    assert state["account"]["cash_eur"] == "500"
