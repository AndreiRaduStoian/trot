from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings for the Trot research and paper-trading app."""

    model_config = SettingsConfigDict(
        env_prefix="TROT_",
        case_sensitive=False,
        extra="forbid",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    symbol: Literal["BTC/EUR"] = "BTC/EUR"
    timeframe: Literal["1d"] = "1d"
    interval: Literal["1d"] = "1d"
    initial_cash_eur: float = Field(default=500.0, gt=0)
    max_btc_allocation: float = Field(default=0.5, gt=0, le=0.5)
    sma_days: int = Field(default=30, ge=1)
    momentum_days: int = Field(default=14, ge=1)
    volatility_window: int = Field(default=20, ge=1)
    annualization_days: int = Field(default=365, gt=0)
    volatility_target: float = Field(default=0.12, gt=0, le=1)
    min_trade_eur: float = Field(default=25.0, ge=25.0)
    rebalance_threshold: float = Field(default=0.05, gt=0, le=1)
    maker_fee: float = Field(default=0.0005, ge=0)
    taker_fee: float = Field(default=0.001, ge=0)
    spread_bps: float = Field(default=5.0, ge=0)
    slippage_bps: float = Field(default=10.0, ge=0)
    exchange_min_notional_eur: float = Field(default=25.0, gt=0)
    data_dir: str = "data/market"
    db_path: str = "data/bot.db"
    mode: Literal["backtest", "paper"] = "paper"
    exchange_source: Literal["binance", "coinbase", "kraken"] = "binance"
    paper_quote_max_age_hours: int = Field(default=12, gt=0)
    log_level: str = "INFO"

    @field_validator("symbol", "timeframe", "interval")
    @classmethod
    def validate_symbol_and_timeframe(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized == "BTC/EUR":
            return "BTC/EUR"
        if normalized == "1D":
            return "1d"
        raise ValueError("Only BTC/EUR and daily 1d candles are supported in this release.")

    @field_validator("data_dir", "db_path")
    @classmethod
    def ensure_paths_are_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Path values may not be empty.")
        return value

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir)

    @property
    def database_path(self) -> Path:
        return Path(self.db_path)


def get_settings() -> Settings:
    return Settings()
