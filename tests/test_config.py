import pytest
from pydantic import ValidationError

from trot.config import Settings


def test_default_configuration_values() -> None:
    settings = Settings()

    assert settings.symbol == "BTC/EUR"
    assert settings.timeframe == "1d"
    assert settings.initial_cash_eur == 500.0
    assert settings.max_btc_allocation == 0.5
    assert settings.sma_days == 30
    assert settings.momentum_days == 14
    assert settings.volatility_window == 20
    assert settings.volatility_target == 0.12
    assert settings.rebalance_threshold == 0.05
    assert settings.min_trade_eur == 25.0


def test_invalid_symbol_and_ranges_are_rejected() -> None:
    with pytest.raises((ValidationError, ValueError)):
        Settings(symbol="ETH/EUR")

    with pytest.raises((ValidationError, ValueError)):
        Settings(initial_cash_eur=0)

    with pytest.raises((ValidationError, ValueError)):
        Settings(max_btc_allocation=0.75)

    with pytest.raises((ValidationError, ValueError)):
        Settings(min_trade_eur=10)


def test_environment_overrides_are_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TROT_SYMBOL", "BTC/EUR")
    monkeypatch.setenv("TROT_INITIAL_CASH_EUR", "750")
    monkeypatch.setenv("TROT_MAX_BTC_ALLOCATION", "0.45")
    monkeypatch.setenv("TROT_SMA_DAYS", "40")

    settings = Settings()

    assert settings.initial_cash_eur == 750.0
    assert settings.max_btc_allocation == 0.45
    assert settings.sma_days == 40
