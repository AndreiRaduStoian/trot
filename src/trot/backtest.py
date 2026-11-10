from __future__ import annotations

import hashlib
import json
import math
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from .data import candle_to_epoch_ms, interval_delta, validate_candle_series
from .execution import build_order_intent
from .models import MarketCandle, PortfolioState, StrategyConfig
from .strategy import evaluate_portfolio


def _metrics(
    equities: list[Decimal],
    exposures: list[Decimal],
    fills: list[dict[str, Any]],
    initial: Decimal,
) -> dict[str, Any]:
    returns = [
        float(equities[i] / equities[i - 1] - 1)
        for i in range(1, len(equities))
        if equities[i - 1] > 0
    ]
    mean_return = sum(returns) / len(returns) if returns else 0.0
    variance = (
        sum((value - mean_return) ** 2 for value in returns) / (len(returns) - 1)
        if len(returns) > 1
        else 0.0
    )
    daily_volatility = math.sqrt(variance)
    peak = initial
    max_drawdown = Decimal(0)
    for equity in equities:
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
    traded = sum((Decimal(fill["eur_notional"]) for fill in fills), Decimal(0))
    return {
        "net_return": float(equities[-1] / initial - 1) if initial else 0.0,
        "max_drawdown": float(max_drawdown),
        "annualized_volatility": daily_volatility * math.sqrt(365),
        "sharpe_ratio": mean_return / daily_volatility * math.sqrt(365)
        if daily_volatility > 0
        else None,
        "trade_count": len(fills),
        "turnover": float(traded / initial) if initial else 0.0,
        "total_fees": str(
            sum((Decimal(fill["fee_eur"]) for fill in fills), Decimal(0))
        ),
        "exposure_over_time": [float(value) for value in exposures],
        "observation_count": len(equities),
    }


def _simulate(
    candles: list[MarketCandle],
    config: StrategyConfig,
    initial_cash: Decimal,
    maker_fee: Decimal,
    taker_fee: Decimal,
    spread_bps: Decimal,
    slippage_bps: Decimal,
    min_trade_eur: Decimal,
    cost_multiplier: Decimal = Decimal(1),
    evaluation_start: date | None = None,
) -> dict[str, Any]:
    cash = initial_cash
    btc = Decimal(0)
    decisions: list[dict[str, Any]] = []
    fills: list[dict[str, Any]] = []
    equities: list[Decimal] = []
    exposures: list[Decimal] = []
    effective_fee = taker_fee * cost_multiplier
    effective_spread = spread_bps * cost_multiplier
    effective_slippage = slippage_bps * cost_multiplier

    for index, candle in enumerate(candles):
        if evaluation_start and candle.timestamp.date() < evaluation_start:
            continue
        close = candle.close
        equity = cash + btc * close
        equities.append(equity)
        exposures.append(btc * close / equity if equity > 0 else Decimal(0))
        if index + 1 >= len(candles):
            continue

        next_candle = candles[index + 1]
        decision_time = candle.timestamp + interval_delta(candle.interval)
        decision = evaluate_portfolio(
            candles[: index + 1],
            PortfolioState(cash_eur=cash, btc_balance=btc, total_equity_eur=equity),
            config,
            as_of=decision_time,
        )
        decisions.append(
            {
                "candle_timestamp": candle.timestamp.isoformat(),
                "source": candle.source,
                "signal": decision.signal,
                "action": decision.action,
                "target_allocation": str(decision.target_allocation)
                if decision.target_allocation is not None
                else None,
                "current_allocation": str(decision.current_allocation)
                if decision.current_allocation is not None
                else None,
                "reason": decision.reason,
                "validation_outcome": decision.validation_outcome,
                "indicators": {
                    key: str(value) if value is not None else None
                    for key, value in decision.indicators.items()
                },
            }
        )
        if decision.validation_outcome != "valid" or decision.action not in {
            "buy",
            "sell",
        }:
            continue

        execution_price = next_candle.open
        current_equity = cash + btc * execution_price
        target_weight = decision.target_allocation or Decimal(0)
        target_btc = target_weight * current_equity / execution_price
        intent = build_order_intent(
            current_btc=btc,
            cash_eur=cash,
            target_btc=target_btc,
            btc_price=execution_price,
            max_btc_allocation=config.max_btc_allocation,
            min_trade_eur=min_trade_eur,
            rebalance_threshold=config.rebalance_threshold,
            maker_fee=maker_fee * cost_multiplier,
            taker_fee=effective_fee,
            spread_bps=effective_spread,
            slippage_bps=effective_slippage,
            exchange_min_notional_eur=config.exchange_min_notional_eur,
            mandatory_exit=decision.signal == "cash",
        )
        if intent.action == "buy" and intent.btc_amount > 0:
            total_cost = intent.eur_amount + intent.fee_eur
            if total_cost <= cash:
                cash -= total_cost
                btc += intent.btc_amount
            else:
                continue
        elif intent.action == "sell" and intent.btc_amount > 0:
            if intent.btc_amount <= btc:
                cash += intent.eur_amount - intent.fee_eur
                btc -= intent.btc_amount
            else:
                continue
        else:
            continue
        fills.append(
            {
                "signal_timestamp": candle.timestamp.isoformat(),
                "execution_timestamp": next_candle.timestamp.isoformat(),
                "reference_price": str(next_candle.open),
                "fill_price": str(intent.fill_price),
                "side": intent.action,
                "btc_quantity": str(intent.btc_amount),
                "eur_notional": str(intent.eur_amount),
                "fee_eur": str(intent.fee_eur),
            }
        )

    return {
        "decisions": decisions,
        "fills": fills,
        "metrics": _metrics(equities, exposures, fills, initial_cash),
        "ending_cash_eur": str(cash),
        "ending_btc": str(btc),
        "ending_equity_eur": str(equities[-1]) if equities else str(initial_cash),
    }


def _benchmark(
    candles: list[MarketCandle],
    initial_cash: Decimal,
    fee: Decimal,
    spread: Decimal,
    slippage: Decimal,
) -> dict[str, Any]:
    first_price = candles[0].open
    last_price = candles[-1].close
    entry_price = first_price * (
        Decimal(1) + spread / Decimal(20000) + slippage / Decimal(10000)
    )
    exit_price = last_price * (
        Decimal(1) - spread / Decimal(20000) - slippage / Decimal(10000)
    )
    quantity = initial_cash / (entry_price * (Decimal(1) + fee))
    entry_fee = quantity * entry_price * fee
    exit_notional = quantity * exit_price
    exit_fee = exit_notional * fee
    ending_value = exit_notional - exit_fee
    return {
        "net_return": float(ending_value / initial_cash - 1) if initial_cash else 0.0,
        "trade_count": 2,
        "total_fees": str(entry_fee + exit_fee),
        "eur_cash_net_return": 0.0,
    }


def run_backtest(
    candles: list[MarketCandle],
    config: StrategyConfig | None = None,
    initial_cash: Decimal = Decimal(500),
    maker_fee: Decimal = Decimal("0.0005"),
    taker_fee: Decimal = Decimal("0.001"),
    spread_bps: Decimal = Decimal(5),
    slippage_bps: Decimal = Decimal(10),
    min_trade_eur: Decimal = Decimal(25),
    folds: list[tuple[str, str, str]] | None = None,
) -> dict[str, Any]:
    validate_candle_series(candles)
    if initial_cash <= 0:
        raise ValueError("initial cash must be positive")
    strategy = config or StrategyConfig()
    base = _simulate(
        candles,
        strategy,
        initial_cash,
        maker_fee,
        taker_fee,
        spread_bps,
        slippage_bps,
        min_trade_eur,
    )
    stress = {
        label: _simulate(
            candles,
            strategy,
            initial_cash,
            maker_fee,
            taker_fee,
            spread_bps,
            slippage_bps,
            min_trade_eur,
            Decimal(multiplier),
        )["metrics"]
        for label, multiplier in (("1x", "1"), ("1.5x", "1.5"), ("2x", "2"))
    }
    dataset_payload = [
        {
            "timestamp_ms": candle_to_epoch_ms(candle),
            "symbol": candle.symbol,
            "interval": candle.interval,
            "open": str(candle.open),
            "high": str(candle.high),
            "low": str(candle.low),
            "close": str(candle.close),
            "volume": str(candle.volume),
            "source": candle.source,
        }
        for candle in candles
    ]
    dataset_hash = hashlib.sha256(
        json.dumps(dataset_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    config_data = {
        "sma_days": strategy.sma_days,
        "momentum_days": strategy.momentum_days,
        "volatility_window": strategy.volatility_window,
        "annualization_days": strategy.annualization_days,
        "volatility_target": str(strategy.volatility_target),
        "max_btc_allocation": str(strategy.max_btc_allocation),
        "rebalance_threshold": str(strategy.rebalance_threshold),
        "exchange_min_notional_eur": str(strategy.exchange_min_notional_eur),
        "initial_cash": str(initial_cash),
        "maker_fee": str(maker_fee),
        "taker_fee": str(taker_fee),
        "spread_bps": str(spread_bps),
        "slippage_bps": str(slippage_bps),
        "min_trade_eur": str(min_trade_eur),
    }
    config_hash = hashlib.sha256(
        json.dumps(config_data, sort_keys=True).encode()
    ).hexdigest()
    result = {
        **base,
        "interval": candles[0].interval if candles else "1d",
        "label": "simulated research",
        "dataset_hash": dataset_hash,
        "config_hash": config_hash,
        "benchmarks": {
            "eur_cash": {"net_return": 0.0, "trade_count": 0, "total_fees": "0"},
            "btc_buy_and_hold": _benchmark(
                candles, initial_cash, taker_fee, spread_bps, slippage_bps
            ),
        },
        "cost_stress": stress,
        "folds": [],
    }
    if folds:
        previous_test_end: date | None = None
        for train_end_text, test_start_text, test_end_text in folds:
            train_end = date.fromisoformat(train_end_text)
            test_start = date.fromisoformat(test_start_text)
            test_end = date.fromisoformat(test_end_text)
            if not train_end < test_start <= test_end:
                raise ValueError(
                    "fold dates must satisfy train_end < test_start <= test_end"
                )
            if previous_test_end is not None and test_start <= previous_test_end:
                raise ValueError("folds must be chronological and non-overlapping")
            previous_test_end = test_end
            fold_candles = [c for c in candles if c.timestamp.date() <= test_end]
            if not fold_candles or not any(
                c.timestamp.date() >= test_start for c in fold_candles
            ):
                raise ValueError("fold test range is outside available candles")
            fold_result = _simulate(
                fold_candles,
                strategy,
                initial_cash,
                maker_fee,
                taker_fee,
                spread_bps,
                slippage_bps,
                min_trade_eur,
                evaluation_start=test_start,
            )
            result["folds"].append(
                {
                    "training_end": train_end.isoformat(),
                    "test_start": test_start.isoformat(),
                    "test_end": test_end.isoformat(),
                    "metrics": fold_result["metrics"],
                }
            )
    return result
