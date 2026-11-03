from __future__ import annotations

from decimal import Decimal

from trot.execution import build_order_intent


def test_build_order_intent_works_with_fee_and_thresholds():
    order = build_order_intent(
        current_btc=Decimal("0.05"),
        cash_eur=Decimal("500"),
        target_btc=Decimal("0.25"),
        btc_price=Decimal("50000"),
        max_btc_allocation=Decimal("0.5"),
        min_trade_eur=Decimal("25"),
        rebalance_threshold=Decimal("0.05"),
        maker_fee=Decimal("0.0005"),
        taker_fee=Decimal("0.001"),
        spread_bps=Decimal("5"),
        slippage_bps=Decimal("10"),
    )
    assert order is not None
    assert order.eur_amount >= Decimal("0")


def test_build_order_intent_rejects_undersized_exit():
    order = build_order_intent(
        current_btc=Decimal("0.0001"),
        cash_eur=Decimal("0"),
        target_btc=Decimal("0"),
        btc_price=Decimal("50000"),
        max_btc_allocation=Decimal("0.5"),
        min_trade_eur=Decimal("25"),
        rebalance_threshold=Decimal("0.05"),
        maker_fee=Decimal("0.0005"),
        taker_fee=Decimal("0.001"),
        spread_bps=Decimal("5"),
        slippage_bps=Decimal("10"),
    )
    assert order is not None
    assert order.reason
