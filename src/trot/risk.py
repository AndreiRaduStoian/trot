from __future__ import annotations

import math
from collections.abc import Iterable


def realized_volatility(returns: Iterable[float | int]) -> float:
    values = [float(value) for value in returns if value is not None]
    if any(not math.isfinite(value) for value in values):
        return 0.0
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance) if variance > 0 else 0.0


def target_allocation(
    portfolio_value: float,
    volatility: float,
    target_volatility: float = 0.12,
    max_allocation: float = 0.5,
    annualization_days: int = 365,
) -> float:
    if not math.isfinite(portfolio_value) or portfolio_value <= 0:
        return 0.0
    if not math.isfinite(volatility) or volatility <= 0:
        return 0.0
    if not math.isfinite(target_volatility) or target_volatility <= 0:
        return 0.0
    if not math.isfinite(max_allocation) or max_allocation <= 0:
        return 0.0

    if annualization_days <= 0:
        return 0.0
    annualized = volatility * math.sqrt(float(annualization_days))
    if annualized <= 0:
        return 0.0
    weight = target_volatility / annualized
    return max(0.0, min(weight, max_allocation))
