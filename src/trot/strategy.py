from __future__ import annotations

from decimal import Decimal, InvalidOperation

from .models import Decision, MarketCandle, StrategyConfig


def _as_decimal(value: Decimal | float | str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def evaluate_signal(
    candles: list[MarketCandle], config: StrategyConfig | None = None
) -> Decision:
    strategy = config or StrategyConfig()
    if len(candles) < max(strategy.sma_days, strategy.momentum_days + 1):
        return Decision(
            symbol="unavailable",
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
