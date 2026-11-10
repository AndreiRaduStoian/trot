from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from .config import Settings
from .data import (
    read_candles_parquet,
    validate_candle,
    validate_candle_series,
    write_candles_parquet,
)
from .exchange import fetch_ohlcv, fetch_public_quote
from .execution import build_order_intent
from .models import MarketCandle, PortfolioState, StrategyConfig
from .storage import get_paper_status, load_paper_account, persist_paper_cycle
from .strategy import evaluate_portfolio

logger = logging.getLogger("trot")


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, str(level_name).upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Trot - BTC/EUR research and paper trading"
    )
    parser.add_argument(
        "--version", action="store_true", help="Print installed version and exit"
    )

    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = False

    download_parser = subparsers.add_parser("download", help="Download market data")
    download_parser.add_argument("--start", dest="start", required=True)
    download_parser.add_argument("--end", dest="end", required=True)
    download_parser.add_argument("--output")
    download_parser.add_argument("--exchange")

    backtest_parser = subparsers.add_parser(
        "backtest", help="Run a historical simulation"
    )
    backtest_parser.add_argument("--data", required=True)
    backtest_parser.add_argument("--start")
    backtest_parser.add_argument("--end")
    backtest_parser.add_argument("--fold", action="append", default=[])
    paper_parser = subparsers.add_parser("paper", help="Run paper operations")
    paper_subparsers = paper_parser.add_subparsers(dest="paper_command")
    cycle_parser = paper_subparsers.add_parser(
        "cycle", help="Process unhandled candles"
    )
    cycle_parser.add_argument("--data")
    status_parser = paper_subparsers.add_parser("status", help="Inspect paper state")
    status_parser.add_argument("--recent", type=int, default=10)
    status_parser.add_argument("--account", default="default")
    cycle_parser.add_argument("--account", default="default")
    top_status_parser = subparsers.add_parser("status", help="Inspect paper state")
    top_status_parser.add_argument("--recent", type=int, default=10)
    top_status_parser.add_argument("--account", default="default")

    data_parser = subparsers.add_parser("data", help="Data management commands")
    data_subparsers = data_parser.add_subparsers(dest="data_command")
    data_subparsers.required = False
    data_download_parser = data_subparsers.add_parser(
        "download", help="Download market data"
    )
    data_download_parser.add_argument("--since")
    data_download_parser.add_argument("--until")
    data_download_parser.add_argument("--output")
    data_download_parser.add_argument("--exchange")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print("trot 0.1.0")
        return 0

    settings = Settings()
    _configure_logging(settings.log_level)

    if args.command is None:
        parser.print_help(sys.stdout)
        return 0

    if args.command == "download":
        return _download_history(
            settings,
            args.start,
            args.end,
            args.output,
            args.exchange,
        )

    if args.command == "data":
        if args.data_command != "download":
            parser.print_usage(sys.stderr)
            return 1
        if not args.since or not args.until:
            print("data download requires --since and --until dates", file=sys.stderr)
            return 1
        return _download_history(
            settings,
            args.since,
            args.until,
            args.output,
            args.exchange,
        )

    if args.command == "backtest":
        return _run_backtest(settings, args.data, args.start, args.end, args.fold)

    if args.command == "paper":
        if args.paper_command == "cycle":
            return _run_paper_cycle(settings, args.data, args.account)
        if args.paper_command == "status":
            return _show_paper_status(settings, args.account, args.recent)
        parser.print_usage(sys.stderr)
        return 1

    if args.command == "status":
        return _show_paper_status(settings, args.account, args.recent)

    logger.info("Starting Trot %s command", args.command)
    print(f"{args.command} is not implemented in this phase.", file=sys.stderr)
    return 1


def _download_history(
    settings: Settings,
    since_text: str,
    until_text: str,
    output_text: str | None,
    source: str | None,
) -> int:
    try:
        since = date.fromisoformat(since_text)
        until = date.fromisoformat(until_text)
        if until < since:
            raise ValueError("--until must be on or after --since")

        start = datetime.combine(since, datetime.min.time(), tzinfo=UTC)
        end_exclusive = datetime.combine(
            until + timedelta(days=1), datetime.min.time(), tzinfo=UTC
        )
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end_exclusive.timestamp() * 1000) - 1
        exchange_source = source or settings.exchange_source
        output_path = (
            Path(output_text)
            if output_text
            else (settings.data_path / "btc-eur.parquet")
        )

        raw_candles = fetch_ohlcv(
            symbol=settings.symbol,
            timeframe=settings.timeframe,
            start_ms=start_ms,
            end_ms=end_ms,
            source=exchange_source,
        )
        now = datetime.now(UTC)
        candles = []
        for row in raw_candles:
            if len(row) < 6:
                raise ValueError("exchange returned a malformed OHLCV row")
            candle = validate_candle(
                {
                    "symbol": settings.symbol,
                    "interval": settings.timeframe,
                    "timestamp": row[0],
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                    "volume": row[5],
                    "source": exchange_source,
                }
            )
            if (
                start <= candle.timestamp < end_exclusive
                and candle.timestamp + timedelta(days=1) <= now
            ):
                candles.append(candle)

        validate_candle_series(candles)
        write_candles_parquet(
            candles,
            output_path,
            exchange_source,
            since.isoformat(),
            until.isoformat(),
        )
        first_date = candles[0].timestamp.date().isoformat()
        last_date = candles[-1].timestamp.date().isoformat()
        print(
            f"Downloaded {len(candles)} candles (BTC/EUR 1d) from {exchange_source}; "
            f"available range {first_date} to {last_date}; validation passed; "
            f"output: {output_path}"
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"data download failed: {exc}", file=sys.stderr)
        return 1


def _strategy_config(settings: Settings) -> StrategyConfig:
    return StrategyConfig(
        sma_days=settings.sma_days,
        momentum_days=settings.momentum_days,
        volatility_window=settings.volatility_window,
        volatility_target=Decimal(str(settings.volatility_target)),
        max_btc_allocation=Decimal(str(settings.max_btc_allocation)),
        min_trade_eur=Decimal(str(settings.min_trade_eur)),
        rebalance_threshold=Decimal(str(settings.rebalance_threshold)),
        annualization_days=settings.annualization_days,
        exchange_min_notional_eur=Decimal(str(settings.exchange_min_notional_eur)),
    )


def _run_backtest(
    settings: Settings,
    data_path: str,
    start_text: str | None,
    end_text: str | None,
    fold_texts: list[str],
) -> int:
    try:
        from .backtest import run_backtest

        candles, manifest = read_candles_parquet(data_path)
        if start_text:
            start_date = date.fromisoformat(start_text)
            candles = [
                candle for candle in candles if candle.timestamp.date() >= start_date
            ]
        if end_text:
            end_date = date.fromisoformat(end_text)
            candles = [
                candle for candle in candles if candle.timestamp.date() <= end_date
            ]
        if len(candles) < 2:
            raise ValueError(
                "requested backtest range must contain at least two candles"
            )
        folds = []
        for value in fold_texts:
            parts = value.split(":")
            if len(parts) != 3:
                raise ValueError("fold must use TRAIN_END:TEST_START:TEST_END")
            folds.append(tuple(parts))
        result = run_backtest(
            candles,
            _strategy_config(settings),
            initial_cash=Decimal(str(settings.initial_cash_eur)),
            maker_fee=Decimal(str(settings.maker_fee)),
            taker_fee=Decimal(str(settings.taker_fee)),
            spread_bps=Decimal(str(settings.spread_bps)),
            slippage_bps=Decimal(str(settings.slippage_bps)),
            min_trade_eur=Decimal(str(settings.min_trade_eur)),
            folds=folds,
        )
        result["source"] = manifest["source"]
        result["range"] = [
            candles[0].timestamp.isoformat(),
            candles[-1].timestamp.isoformat(),
        ]

        fills = result.pop("fills", [])
        for f in fills:
            print(f)
        print(result["ending_cash_eur"], result["ending_btc"], result["ending_equity_eur"])
        # print(decisions[-1])
        # for d in decisions:
        #     if d['action'] in ['sell', 'buy']:
        #         print(d['action'], d[''])


        #print(json.dumps(result, sort_keys=True, default=str))

        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"backtest failed: {exc}", file=sys.stderr)
        return 1


def _paper_config_hash(settings: Settings) -> str:
    values = {
        "symbol": settings.symbol,
        "timeframe": settings.timeframe,
        "sma_days": settings.sma_days,
        "momentum_days": settings.momentum_days,
        "volatility_window": settings.volatility_window,
        "annualization_days": settings.annualization_days,
        "volatility_target": settings.volatility_target,
        "max_btc_allocation": settings.max_btc_allocation,
        "rebalance_threshold": settings.rebalance_threshold,
        "min_trade_eur": settings.min_trade_eur,
        "maker_fee": settings.maker_fee,
        "taker_fee": settings.taker_fee,
        "spread_bps": settings.spread_bps,
        "slippage_bps": settings.slippage_bps,
        "exchange_min_notional_eur": settings.exchange_min_notional_eur,
        "exchange_source": settings.exchange_source,
    }
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def _paper_history(
    settings: Settings, data_path: str | None
) -> tuple[list[MarketCandle], str]:
    path = Path(data_path) if data_path else settings.data_path / "btc-eur.parquet"
    if path.is_file():
        candles, manifest = read_candles_parquet(path)
        validate_candle_series(candles, as_of=datetime.now(UTC), require_fresh=True)
        return candles, str(manifest["source"])

    now = datetime.now(UTC)
    start = now - timedelta(days=400)
    start_ms = int(
        start.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000
    )
    raw = fetch_ohlcv(
        settings.symbol,
        settings.timeframe,
        start_ms=start_ms,
        end_ms=int(now.timestamp() * 1000),
        source=settings.exchange_source,
    )
    candles = []
    for row in raw:
        if len(row) < 6:
            raise ValueError("exchange returned a malformed OHLCV row")
        candles.append(
            validate_candle(
                {
                    "symbol": settings.symbol,
                    "interval": settings.timeframe,
                    "timestamp": row[0],
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                    "volume": row[5],
                    "source": settings.exchange_source,
                }
            )
        )
    candles = [
        candle for candle in candles if candle.timestamp + timedelta(days=1) <= now
    ]
    validate_candle_series(candles, as_of=now, require_fresh=True)
    write_candles_parquet(
        candles,
        path,
        settings.exchange_source,
        start.date().isoformat(),
        now.date().isoformat(),
    )
    return candles, settings.exchange_source


def _run_paper_cycle(settings: Settings, data_path: str | None, account_id: str) -> int:
    try:
        candles, source = _paper_history(settings, data_path)
        initial_cash = Decimal(str(settings.initial_cash_eur))
        account = load_paper_account(settings.database_path, account_id, initial_cash)
        cash = Decimal(account["cash_eur"])
        btc = Decimal(account["btc_balance"])
        last_processed = account["last_processed_candle_ms"]
        config_hash = _paper_config_hash(settings)
        config = _strategy_config(settings)
        processed = 0

        for index, candle in enumerate(candles):
            timestamp_ms = int(candle.timestamp.timestamp() * 1000)
            if last_processed is not None and timestamp_ms <= last_processed:
                continue
            price = candle.close
            equity = cash + btc * price
            decision = evaluate_portfolio(
                candles[: index + 1],
                PortfolioState(cash_eur=cash, btc_balance=btc, total_equity_eur=equity),
                config,
                as_of=candle.timestamp + timedelta(days=1),
            )
            order_record = None
            fill_record = None
            cash_after = cash
            btc_after = btc

            if decision.validation_outcome == "valid" and decision.action in {
                "buy",
                "sell",
            }:
                execution_timestamp = candle.timestamp + timedelta(days=1)
                reference_price = None
                if index + 1 < len(candles):
                    reference_price = candles[index + 1].open
                    execution_timestamp = candles[index + 1].timestamp
                else:
                    try:
                        quote = fetch_public_quote(
                            settings.exchange_source,
                            settings.symbol,
                            max_age_seconds=settings.paper_quote_max_age_seconds,
                        )
                        if quote["timestamp"] < execution_timestamp:
                            raise ValueError(
                                "public quote predates the completed signal candle"
                            )
                        reference_price = quote["mid"]
                        execution_timestamp = quote["timestamp"]
                    except Exception as exc:  # noqa: BLE001
                        decision = replace(
                            decision,
                            action="abstain",
                            reason=f"paper execution unavailable: {exc}",
                            validation_outcome="invalid",
                        )

                if reference_price is not None:
                    execution_equity = cash + btc * reference_price
                    target_weight = decision.target_allocation or Decimal(0)
                    intent = build_order_intent(
                        current_btc=btc,
                        cash_eur=cash,
                        target_btc=target_weight * execution_equity / reference_price,
                        btc_price=reference_price,
                        max_btc_allocation=config.max_btc_allocation,
                        min_trade_eur=config.min_trade_eur,
                        rebalance_threshold=config.rebalance_threshold,
                        maker_fee=Decimal(str(settings.maker_fee)),
                        taker_fee=Decimal(str(settings.taker_fee)),
                        spread_bps=Decimal(str(settings.spread_bps)),
                        slippage_bps=Decimal(str(settings.slippage_bps)),
                        exchange_min_notional_eur=config.exchange_min_notional_eur,
                        mandatory_exit=decision.signal == "cash",
                    )
                    decision = replace(
                        decision, action=intent.action, reason=intent.reason
                    )
                    order_id = hashlib.sha256(
                        f"{account_id}|{config_hash}|{timestamp_ms}|order".encode()
                    ).hexdigest()
                    if intent.action in {"buy", "sell"}:
                        order_record = {
                            "order_id": order_id,
                            "side": intent.action,
                            "status": "filled",
                            "reference_price": str(reference_price),
                            "fill_price": str(intent.fill_price),
                            "btc_quantity": str(intent.btc_amount),
                            "eur_notional": str(intent.eur_amount),
                            "fee_eur": str(intent.fee_eur),
                            "reason": intent.reason,
                        }
                        if intent.action == "buy":
                            cash_after -= intent.eur_amount + intent.fee_eur
                            btc_after += intent.btc_amount
                        else:
                            cash_after += intent.eur_amount - intent.fee_eur
                            btc_after -= intent.btc_amount
                        fill_record = {
                            **order_record,
                            "execution_ts_ms": int(
                                execution_timestamp.timestamp() * 1000
                            ),
                        }
                    else:
                        order_record = {
                            "order_id": order_id,
                            "side": "buy" if decision.signal == "long" else "sell",
                            "status": "rejected",
                            "reason": intent.reason,
                        }

            decision_data = asdict(decision)
            decision_data["valuation_price"] = str(price)
            decision_data["simulated"] = True
            if order_record and order_record["status"] == "rejected":
                order_record["side"] = "buy" if decision.signal == "long" else "sell"
            persisted = persist_paper_cycle(
                database_path=settings.database_path,
                account_id=account_id,
                strategy_id="trend-volatility-v1",
                config_hash=config_hash,
                candle_timestamp=candle.timestamp,
                source=source,
                decision=decision_data,
                initial_cash=initial_cash,
                cash_after=cash_after,
                btc_after=btc_after,
                order=order_record,
                fill=fill_record,
            )
            if persisted:
                cash, btc = cash_after, btc_after
                last_processed = timestamp_ms
                processed += 1
            else:
                account = load_paper_account(
                    settings.database_path, account_id, initial_cash
                )
                cash = Decimal(account["cash_eur"])
                btc = Decimal(account["btc_balance"])
                last_processed = account["last_processed_candle_ms"]

        print(
            json.dumps(
                {
                    "simulated": True,
                    "processed_candles": processed,
                    "cash_eur": str(cash),
                    "btc_balance": str(btc),
                    "latest_candle": candles[-1].timestamp.isoformat(),
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"paper cycle failed: {exc}", file=sys.stderr)
        return 1


def _show_paper_status(settings: Settings, account_id: str, recent: int) -> int:
    try:
        result = get_paper_status(settings.database_path, account_id, recent)
        result["simulated"] = True
        print(json.dumps(result, sort_keys=True, default=str))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"paper status failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
