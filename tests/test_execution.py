from __future__ import annotations

from decimal import Decimal

from trot.execution import build_order_intent


def test_build_order_intent_works_with_fee_and_thresholds():
    order = build_order_intent(
        current_btc=Decimal("0.05"),
        cash_eur=Decimal(500),
        target_btc=Decimal("0.25"),
        btc_price=Decimal(50000),
        max_btc_allocation=Decimal("0.5"),
        min_trade_eur=Decimal(25),
        rebalance_threshold=Decimal("0.05"),
        maker_fee=Decimal("0.0005"),
        taker_fee=Decimal("0.001"),
        spread_bps=Decimal(5),
        slippage_bps=Decimal(10),
    )
    assert order is not None
    assert order.eur_amount >= Decimal(0)


def test_build_order_intent_rejects_undersized_exit():
    order = build_order_intent(
        current_btc=Decimal("0.0001"),
        cash_eur=Decimal(0),
        target_btc=Decimal(0),
        btc_price=Decimal(50000),
        max_btc_allocation=Decimal("0.5"),
        min_trade_eur=Decimal(25),
        rebalance_threshold=Decimal("0.05"),
        maker_fee=Decimal("0.0005"),
        taker_fee=Decimal("0.001"),
        spread_bps=Decimal(5),
        slippage_bps=Decimal(10),
    )
    assert order is not None
    assert order.reason


def test_buy_intent_accounts_for_fees_and_never_exceeds_cash_or_cap():
    cash = Decimal(100)
    current_btc = Decimal(0)
    price = Decimal(100)
    order = build_order_intent(
        current_btc=current_btc,
        cash_eur=cash,
        target_btc=Decimal(10),
        btc_price=price,
        max_btc_allocation=Decimal("0.5"),
        min_trade_eur=Decimal(1),
        rebalance_threshold=Decimal("0.05"),
        taker_fee=Decimal("0.01"),
    )

    assert order.action == "buy"
    assert order.eur_amount + order.fee_eur <= cash
    assert order.btc_amount * order.fill_price <= cash / Decimal("1.01")
    assert order.btc_amount * price <= Decimal(50)
    final_equity = cash - order.eur_amount - order.fee_eur
    final_equity += order.btc_amount * order.fill_price
    assert order.btc_amount * order.fill_price / final_equity <= Decimal("0.5")


def test_small_discretionary_change_is_suppressed_but_required_exit_bypasses():
    common = {
        "current_btc": Decimal("0.1"),
        "cash_eur": Decimal(900),
        "btc_price": Decimal(1000),
        "max_btc_allocation": Decimal("0.5"),
        "min_trade_eur": Decimal(1),
        "rebalance_threshold": Decimal("0.05"),
    }
    small_change = build_order_intent(target_btc=Decimal("0.12"), **common)
    required_exit = build_order_intent(
        target_btc=Decimal(0), mandatory_exit=True, **common
    )

    assert small_change.action == "hold"
    assert required_exit.action == "sell"
