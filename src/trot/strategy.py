from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from .data import validate_candle_series
from .execution import build_order_intent
from .models import Decision, MarketCandle, PortfolioState, StrategyConfig
from .risk import realized_volatility, target_allocation


def _as_decimal(value: Decimal | float | str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def evaluate_signal(
    candles: list[MarketCandle],
    config: StrategyConfig | None = None,
    as_of: datetime | None = None,
    require_fresh: bool = False,
) -> Decision:
    strategy = config or StrategyConfig()
    if len(candles) >= 2:
        try:
            validate_candle_series(
                candles,
                as_of=as_of or datetime.now(UTC),
                require_fresh=require_fresh,
            )
        except ValueError as exc:
            return Decision(
                signal="unavailable",
                action="abstain",
                reason=str(exc),
                validation_outcome="invalid",
            )
    if len(candles) < max(strategy.sma_days, strategy.momentum_days + 1):
        return Decision(
            candle_timestamp=candles[-1].timestamp if candles else None,
            symbol="unavailable",
            source=candles[-1].source if candles else None,
            signal="unavailable",
            action="abstain",
            reason=(
                "insufficient history for SMA and momentum evaluation: "
                f"need at least {max(strategy.sma_days, strategy.momentum_days + 1)} candles"
            ),
            validation_outcome="invalid",
            indicators={},
        )

    closes: list[Decimal] = []
    for candle in candles:
        value = _as_decimal(candle.close)
        if value is None:
            return Decision(
                signal="unavailable",
                action="abstain",
                reason="invalid candle data before signal evaluation",
                validation_outcome="invalid",
                indicators={},
            )
        closes.append(value)

    latest_close = closes[-1]
    sma_window = closes[-strategy.sma_days :]
    sma = sum(sma_window) / Decimal(len(sma_window))
    momentum_idx = strategy.momentum_days
    if len(closes) <= momentum_idx:
        return Decision(
            candle_timestamp=candles[-1].timestamp if candles else None,
            source=candles[-1].source if candles else None,
            signal="unavailable",
            action="abstain",
            reason="insufficient history for momentum calculation",
            validation_outcome="invalid",
            indicators={"sma": sma, "close": latest_close},
        )

    historic_close = closes[-strategy.momentum_days - 1]
    momentum = (latest_close / historic_close) - Decimal(1)
    signal = "long" if latest_close > sma and momentum > 0 else "cash"
    action = "buy" if signal == "long" else "sell"
    reason = (
        "close exceeds trailing SMA and 14-day return is positive"
        if signal == "long"
        else "close below trend condition or momentum turned non-positive"
    )

    return Decision(
        candle_timestamp=candles[-1].timestamp,
        source=candles[-1].source,
        signal=signal,
        action=action,
        reason=reason,
        validation_outcome="valid",
        target_allocation=None,
        current_allocation=None,
        volatility=None,
        indicators={
            "sma": sma,
            "momentum_return": momentum,
            "close": latest_close,
            "latest_close": latest_close,
        },
    )


def evaluate_portfolio(
    candles: list[MarketCandle],
    portfolio: PortfolioState,
    config: StrategyConfig | None = None,
    as_of: datetime | None = None,
    require_fresh: bool = False,
) -> Decision:
    strategy = config or StrategyConfig()
    signal = evaluate_signal(
        candles, strategy, as_of=as_of, require_fresh=require_fresh
    )
    if signal.validation_outcome != "valid":
        return signal

    latest_close = _as_decimal(candles[-1].close)
    if latest_close is None or latest_close <= 0:
        return Decision(
            candle_timestamp=signal.candle_timestamp,
            signal="unavailable",
            action="abstain",
            reason="invalid latest close; no exposure increase permitted",
            validation_outcome="invalid",
        )

    equity = portfolio.cash_eur + portfolio.btc_balance * latest_close
    if (
        portfolio.cash_eur < 0
        or portfolio.btc_balance < 0
        or equity <= 0
        or not equity.is_finite()
    ):
        return Decision(
            candle_timestamp=signal.candle_timestamp,
            signal="unavailable",
            action="abstain",
            reason="invalid portfolio state; no exposure increase permitted",
            validation_outcome="invalid",
        )

    current_weight = portfolio.btc_balance * latest_close / equity
    return_window = strategy.volatility_window
    closes = [_as_decimal(candle.close) for candle in candles]
    if any(close is None or close <= 0 for close in closes):
        return Decision(
            candle_timestamp=signal.candle_timestamp,
            signal="unavailable",
            action="abstain",
            reason="invalid close in volatility history",
            validation_outcome="invalid",
        )
    if len(closes) < return_window + 1:
        return Decision(
            candle_timestamp=signal.candle_timestamp,
            signal="unavailable",
            action="abstain",
            reason=f"insufficient history for {return_window} daily returns",
            validation_outcome="invalid",
            current_allocation=current_weight,
            indicators=signal.indicators,
        )

    recent_closes = closes[-(return_window + 1) :]
    returns = [
        float(recent_closes[index] / recent_closes[index - 1] - Decimal(1))
        for index in range(1, len(recent_closes))
    ]
    daily_volatility = realized_volatility(returns)
    annualized_volatility = daily_volatility * math.sqrt(strategy.annualization_days)
    if signal.signal == "long" and (
        not math.isfinite(annualized_volatility) or annualized_volatility <= 0
    ):
        return Decision(
            candle_timestamp=signal.candle_timestamp,
            signal="unavailable",
            action="abstain",
            reason="volatility is invalid or zero; no new BTC exposure permitted",
            validation_outcome="invalid",
            current_allocation=current_weight,
            indicators=signal.indicators,
        )

    if signal.signal == "long":
        target_weight = Decimal(
            str(
                target_allocation(
                    float(equity),
                    daily_volatility,
                    float(strategy.volatility_target),
                    float(strategy.max_btc_allocation),
                    strategy.annualization_days,
                )
            )
        )
    else:
        target_weight = Decimal(0)

    target_btc = target_weight * equity / latest_close
    intent = build_order_intent(
        current_btc=portfolio.btc_balance,
        cash_eur=portfolio.cash_eur,
        target_btc=target_btc,
        btc_price=latest_close,
        max_btc_allocation=strategy.max_btc_allocation,
        min_trade_eur=strategy.min_trade_eur,
        rebalance_threshold=strategy.rebalance_threshold,
        exchange_min_notional_eur=strategy.exchange_min_notional_eur,
        mandatory_exit=signal.signal == "cash",
    )
    return Decision(
        candle_timestamp=signal.candle_timestamp,
        symbol="BTC/EUR",
        source=candles[-1].source,
        signal=signal.signal,
        action=intent.action,
        reason=intent.reason,
        validation_outcome="valid",
        target_allocation=target_weight,
        current_allocation=current_weight,
        volatility=Decimal(str(annualized_volatility)),
        indicators={
            **signal.indicators,
            "volatility_daily": Decimal(str(daily_volatility)),
            "volatility_annualized": Decimal(str(annualized_volatility)),
            "target_btc": target_btc,
        },
    )
