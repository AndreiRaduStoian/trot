from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal


@dataclass(frozen=True)
class OrderIntent:
    action: str
    eur_amount: Decimal = Decimal(0)
    btc_amount: Decimal = Decimal(0)
    fill_price: Decimal | None = None
    fee_eur: Decimal = Decimal(0)
    reason: str = ""


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)


def simulated_fill_price(
    reference_price: Decimal,
    action: str,
    spread_bps: Decimal = Decimal(5),
    slippage_bps: Decimal = Decimal(10),
) -> Decimal:
    half_spread = spread_bps / Decimal(20000)
    slippage = slippage_bps / Decimal(10000)
    adverse_cost = half_spread + slippage
    if action == "buy":
        return reference_price * (Decimal(1) + adverse_cost)
    if action == "sell":
        return reference_price * (Decimal(1) - adverse_cost)
    return reference_price


def build_order_intent(
    current_btc: Decimal,
    cash_eur: Decimal,
    target_btc: Decimal,
    btc_price: Decimal,
    max_btc_allocation: Decimal,
    min_trade_eur: Decimal,
    rebalance_threshold: Decimal,
    maker_fee: Decimal = Decimal("0.0005"),
    taker_fee: Decimal = Decimal("0.001"),
    spread_bps: Decimal = Decimal(5),
    slippage_bps: Decimal = Decimal(10),
    exchange_min_notional_eur: Decimal = Decimal(25),
    mandatory_exit: bool = False,
) -> OrderIntent:
    if not btc_price.is_finite() or btc_price <= 0:
        return OrderIntent(action="abstain", reason="invalid BTC price")

    equity = cash_eur + current_btc * btc_price
    if equity <= 0 or current_btc < 0 or cash_eur < 0:
        return OrderIntent(action="abstain", reason="invalid portfolio balances")
    current_weight = current_btc * btc_price / equity
    cap_value = max_btc_allocation * equity
    cap_btc = cap_value / btc_price
    target_btc = min(max(target_btc, Decimal(0)), cap_btc)
    cap_breach = current_weight > max_btc_allocation
    required_reduction = mandatory_exit or cap_breach
    delta_btc = target_btc - current_btc
    delta_value = delta_btc * btc_price
    min_notional = max(min_trade_eur, exchange_min_notional_eur)

    if delta_btc == 0:
        return OrderIntent(action="hold", reason="allocation already at target")

    if not required_reduction and abs(delta_value) / equity < rebalance_threshold:
        return OrderIntent(
            action="hold",
            reason="discretionary allocation change is below rebalance threshold",
            eur_amount=Decimal(0),
        )

    if delta_btc > 0:
        fill_price = simulated_fill_price(btc_price, "buy", spread_bps, slippage_bps)
        fee_rate = taker_fee
        if fee_rate < 0 or fee_rate >= 1:
            return OrderIntent(action="abstain", reason="invalid taker fee")
        max_by_cash = cash_eur / (fill_price * (Decimal(1) + fee_rate))
        max_by_cap = max(
            Decimal(0),
            (
                max_btc_allocation * (cash_eur + current_btc * fill_price)
                - current_btc * fill_price
            )
            / (fill_price * (Decimal(1) + max_btc_allocation * fee_rate)),
        )
        btc_qty = _q(min(delta_btc, max_by_cash, max_by_cap))
        gross_eur = _q(btc_qty * fill_price)
        fee = _q(gross_eur * fee_rate)
        if btc_qty <= 0 or gross_eur < min_notional:
            if max_by_cap <= 0:
                return OrderIntent(action="hold", reason="BTC allocation cap reached")
            if max_by_cash <= 0:
                return OrderIntent(action="abstain", reason="insufficient EUR cash")
            return OrderIntent(action="hold", reason="trade is below minimum notional")
        if gross_eur + fee > cash_eur:
            return OrderIntent(action="abstain", reason="insufficient EUR cash for buy")
        return OrderIntent(
            action="buy",
            eur_amount=gross_eur,
            btc_amount=btc_qty,
            fill_price=fill_price,
            fee_eur=fee,
            reason="increase BTC exposure within cash and risk limits",
        )

    sell_amount = min(current_btc, max(current_btc - target_btc, Decimal(0)))
    if sell_amount <= 0:
        return OrderIntent(action="hold", reason="no sale required")
    fill_price = simulated_fill_price(btc_price, "sell", spread_bps, slippage_bps)
    proceed_eur = _q(sell_amount * fill_price)
    if proceed_eur < min_notional:
        residual_btc = current_btc
        return OrderIntent(
            action="hold",
            reason=(
                "required exit below minimum; remaining BTC exposure: "
                f"{residual_btc} BTC"
                if mandatory_exit or cap_breach
                else "trade is below the minimum notional threshold"
            ),
        )
    fee = _q(proceed_eur * taker_fee)
    return OrderIntent(
        action="sell",
        eur_amount=_q(proceed_eur),
        btc_amount=_q(sell_amount),
        fill_price=fill_price,
        fee_eur=fee,
        reason="reduce BTC exposure below target",
    )
