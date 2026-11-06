from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS paper_accounts (
    account_id TEXT PRIMARY KEY,
    starting_cash_eur TEXT NOT NULL,
    cash_eur TEXT NOT NULL,
    btc_balance TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    last_processed_candle_ms INTEGER
);
CREATE TABLE IF NOT EXISTS paper_decisions (
    decision_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES paper_accounts(account_id),
    strategy_id TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    candle_ts_ms INTEGER NOT NULL,
    source TEXT NOT NULL,
    decision_json TEXT NOT NULL,
    cash_after TEXT NOT NULL,
    btc_after TEXT NOT NULL,
    equity_after TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(account_id, strategy_id, config_hash, candle_ts_ms)
);
CREATE TABLE IF NOT EXISTS paper_orders (
    order_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL UNIQUE REFERENCES paper_decisions(decision_id),
    side TEXT NOT NULL,
    status TEXT NOT NULL,
    order_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS paper_fills (
    fill_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL UNIQUE REFERENCES paper_orders(order_id),
    execution_ts_ms INTEGER NOT NULL,
    fill_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evaluation_runs (
    run_id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    start_ts_ms INTEGER,
    end_ts_ms INTEGER,
    config_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);
"""


def _connect(database_path: str | Path) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def initialize_database(database_path: str | Path) -> None:
    with _connect(database_path) as connection:
        connection.executescript(_SCHEMA)
        row = connection.execute("SELECT version FROM schema_meta LIMIT 1").fetchone()
        if row is None:
            connection.execute("INSERT INTO schema_meta(version) VALUES (1)")


def _stable_id(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def persist_paper_cycle(
    database_path: str | Path,
    account_id: str,
    strategy_id: str,
    config_hash: str,
    candle_timestamp: datetime,
    source: str,
    decision: dict[str, Any],
    initial_cash: Decimal,
    cash_after: Decimal,
    btc_after: Decimal,
    order: dict[str, Any] | None = None,
    fill: dict[str, Any] | None = None,
) -> bool:
    if candle_timestamp.tzinfo is None:
        raise ValueError("paper candle timestamp must be timezone-aware")
    if initial_cash <= 0 or cash_after < 0 or btc_after < 0:
        raise ValueError(
            "paper balances must be non-negative and initial cash positive"
        )
    initialize_database(database_path)
    timestamp_ms = int(candle_timestamp.astimezone(UTC).timestamp() * 1000)
    decision_key = f"{account_id}|{strategy_id}|{config_hash}|{timestamp_ms}"
    decision_id = _stable_id(decision_key)
    current_equity = cash_after + btc_after * Decimal(
        str(decision.get("valuation_price", 0))
    )

    with _connect(database_path) as connection:
        connection.execute(
            """INSERT OR IGNORE INTO paper_accounts
               (account_id, starting_cash_eur, cash_eur, btc_balance, config_hash)
               VALUES (?, ?, ?, ?, ?)""",
            (account_id, str(initial_cash), str(initial_cash), "0", config_hash),
        )

    with _connect(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        duplicate = connection.execute(
            """SELECT decision_id FROM paper_decisions
               WHERE account_id=? AND strategy_id=? AND config_hash=? AND candle_ts_ms=?""",
            (account_id, strategy_id, config_hash, timestamp_ms),
        ).fetchone()
        if duplicate:
            return False
        connection.execute(
            """INSERT INTO paper_decisions
               (decision_id, account_id, strategy_id, config_hash, candle_ts_ms,
                source, decision_json, cash_after, btc_after, equity_after, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                decision_id,
                account_id,
                strategy_id,
                config_hash,
                timestamp_ms,
                source,
                json.dumps(decision, sort_keys=True, default=str),
                str(cash_after),
                str(btc_after),
                str(current_equity),
                datetime.now(UTC).isoformat(),
            ),
        )
        if order is not None:
            order_id = str(order.get("order_id") or _stable_id(decision_id + "|order"))
            connection.execute(
                "INSERT INTO paper_orders(order_id, decision_id, side, status, order_json) VALUES (?, ?, ?, ?, ?)",
                (
                    order_id,
                    decision_id,
                    str(order.get("side", decision.get("action", "hold"))),
                    str(order.get("status", "rejected")),
                    json.dumps(order, sort_keys=True, default=str),
                ),
            )
        if fill is not None:
            order_id = str(fill["order_id"])
            fill_id = str(fill.get("fill_id") or _stable_id(order_id + "|fill"))
            connection.execute(
                "INSERT INTO paper_fills(fill_id, order_id, execution_ts_ms, fill_json) VALUES (?, ?, ?, ?)",
                (
                    fill_id,
                    order_id,
                    int(fill["execution_ts_ms"]),
                    json.dumps(fill, sort_keys=True, default=str),
                ),
            )
        connection.execute(
            """UPDATE paper_accounts SET cash_eur=?, btc_balance=?, config_hash=?,
               last_processed_candle_ms=? WHERE account_id=?""",
            (str(cash_after), str(btc_after), config_hash, timestamp_ms, account_id),
        )
        return True


def load_paper_account(
    database_path: str | Path, account_id: str, initial_cash: Decimal
) -> dict[str, Any]:
    initialize_database(database_path)
    with _connect(database_path) as connection:
        connection.execute(
            """INSERT OR IGNORE INTO paper_accounts
               (account_id, starting_cash_eur, cash_eur, btc_balance, config_hash)
               VALUES (?, ?, ?, ?, ?)""",
            (account_id, str(initial_cash), str(initial_cash), "0", ""),
        )
        row = connection.execute(
            "SELECT * FROM paper_accounts WHERE account_id=?", (account_id,)
        ).fetchone()
        return dict(row)


def get_paper_status(
    database_path: str | Path, account_id: str, recent: int = 10
) -> dict[str, Any]:
    initialize_database(database_path)
    with _connect(database_path) as connection:
        account_row = connection.execute(
            "SELECT * FROM paper_accounts WHERE account_id=?", (account_id,)
        ).fetchone()
        if account_row is None:
            return {"account": None, "decisions": []}
        decision_rows = connection.execute(
            """SELECT d.*, o.order_json, f.fill_json
               FROM paper_decisions d
               LEFT JOIN paper_orders o ON o.decision_id=d.decision_id
               LEFT JOIN paper_fills f ON f.order_id=o.order_id
               WHERE d.account_id=? ORDER BY d.candle_ts_ms DESC LIMIT ?""",
            (account_id, max(0, recent)),
        ).fetchall()
        decisions = []
        for row in decision_rows:
            entry = dict(row)
            entry["decision"] = json.loads(entry.pop("decision_json"))
            if entry.get("order_json"):
                entry["order"] = json.loads(entry.pop("order_json"))
            else:
                entry.pop("order_json", None)
            if entry.get("fill_json"):
                entry["fill"] = json.loads(entry.pop("fill_json"))
            else:
                entry.pop("fill_json", None)
            decisions.append(entry)
        return {"account": dict(account_row), "decisions": decisions}
