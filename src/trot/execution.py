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
) -> OrderIntent:
    if btc_price <= 0:
        return OrderIntent(action="abstain", reason="invalid BTC price")

    target_value = target_btc * btc_price
    current_value = current_btc * btc_price
    delta_value = target_value - current_value
    min_notional = max(min_trade_eur, exchange_min_notional_eur)

    if abs(delta_value) <= Decimal(0):
        return OrderIntent(action="hold", reason="allocation already at target")

    if abs(delta_value) < min_notional:
        return OrderIntent(
            action="hold",
            reason="trade is below the minimum notional threshold",
            eur_amount=Decimal(0),
        )

    if target_btc > current_btc:
        max_buy = cash_eur
        if max_buy <= 0:
            return OrderIntent(action="abstain", reason="insufficient EUR cash for buy")

        gross_eur = min(delta_value, max_buy)
        fee = gross_eur * maker_fee
        if gross_eur + fee > cash_eur:
            gross_eur = max(Decimal(0), cash_eur - fee)
        btc_qty = gross_eur / btc_price
        if btc_qty <= 0:
            return OrderIntent(
                action="abstain", reason="resulting BTC quantity is zero"
            )
        return OrderIntent(
            action="buy",
            eur_amount=_q(gross_eur),
            btc_amount=_q(btc_qty),
            fill_price=btc_price,
            fee_eur=_q(fee),
            reason="increase BTC exposure within cash and risk limits",
        )

    sell_amount = max(current_btc - target_btc, Decimal(0))
    if sell_amount <= 0:
        return OrderIntent(action="hold", reason="no sale required")
    if cash_eur <= 0 and target_btc == 0:
        return OrderIntent(
            action="sell",
            eur_amount=Decimal(0),
            btc_amount=_q(sell_amount),
            reason="forced exit required despite small residual size",
        )
    proceed_eur = sell_amount * btc_price
    if proceed_eur < min_notional:
        return OrderIntent(
            action="sell",
            eur_amount=Decimal(0),
            btc_amount=_q(sell_amount),
            reason="residual BTC remains after undersized exit threshold",
        )
    return OrderIntent(
        action="sell",
        eur_amount=_q(proceed_eur),
        btc_amount=_q(sell_amount),
        fill_price=btc_price,
        fee_eur=Decimal(0),
        reason="reduce BTC exposure below target",
    )
