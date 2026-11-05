from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal

Signal = Literal["long", "cash", "unavailable"]
DecisionAction = Literal["buy", "sell", "hold", "abstain"]


@dataclass(frozen=True)
class MarketCandle:
    symbol: str = "BTC/EUR"
    interval: str = "1d"
    timestamp: datetime | None = None
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    volume: Decimal | None = None
    source: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyConfig:
    sma_days: int = 30
    momentum_days: int = 14
    volatility_window: int = 20
    volatility_target: Decimal = Decimal("0.12")
    max_btc_allocation: Decimal = Decimal("0.5")
    min_trade_eur: Decimal = Decimal(25)
    rebalance_threshold: Decimal = Decimal("0.05")
    annualization_days: int = 365
    exchange_min_notional_eur: Decimal = Decimal(25)


@dataclass(frozen=True)
class PortfolioState:
    cash_eur: Decimal = Decimal(0)
    btc_balance: Decimal = Decimal(0)
    total_equity_eur: Decimal = Decimal(0)


@dataclass(frozen=True)
class Decision:
    candle_timestamp: datetime | None = None
    symbol: str | None = None
    signal: Signal = "unavailable"
    action: DecisionAction = "abstain"
    reason: str = ""
    validation_outcome: str = "pending"
    target_allocation: Decimal | None = None
    current_allocation: Decimal | None = None
    volatility: Decimal | None = None
    indicators: dict[str, Decimal | int | None] = field(default_factory=dict)


@dataclass(frozen=True)
class SimulatedOrder:
    order_id: str
    candle_timestamp: datetime | None
    order_type: str
    eur_amount: Decimal | None = None
    btc_amount: Decimal | None = None
    status: str = "pending"
    reason: str = ""


@dataclass(frozen=True)
class SimulatedFill:
    order_id: str
    candle_timestamp: datetime | None
    fill_price: Decimal | None = None
    eur_paid: Decimal | None = None
    btc_received: Decimal | None = None
    fee_eur: Decimal | None = None


@dataclass(frozen=True)
class EvaluationRun:
    run_id: str
    mode: str
    start_timestamp: datetime | None = None
    end_timestamp: datetime | None = None
    notes: str = ""


@dataclass(frozen=True)
class PerformanceReport:
    total_return: Decimal | None = None
    max_drawdown: Decimal | None = None
    volatility: Decimal | None = None
    sharpe_ratio: Decimal | None = None
    trades: int = 0
    turnover: Decimal | None = None
    total_fees: Decimal | None = None
    exposure: Decimal | None = None
