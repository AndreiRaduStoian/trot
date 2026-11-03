# Quickstart: BTC Research and Paper Trading

This guide is the end-to-end validation target for the implementation. It assumes the
repository has been implemented according to [plan.md](./plan.md). All validation can be
performed without exchange credentials or real orders.

## Prerequisites

- Python 3.12 or newer and uv.
- The project dependencies installed from the committed lock file.
- For offline validation: the committed deterministic BTC/EUR fixture under
  `tests/fixtures/`.
- For market-history download only: network access to the configured public market-data
  exchange endpoint. No authenticated credentials are required.

## Setup and Static Validation

From the repository root:

```sh
uv sync --all-groups
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Expected: dependencies resolve from `uv.lock`, Ruff reports no findings, and deterministic
tests pass without network access or secrets.

## Validate History Download

```sh
uv run trot data download \
  --exchange kraken \
  --since 2024-01-01 \
  --until 2025-01-01 \
  --output data/market/btc-eur-2024.parquet
```

Expected: a UTC-normalized Parquet dataset with source and interval metadata, and a summary
of candle count and validation. Missing intervals or malformed candles are surfaced and not
filled. The exact exchange date-bound convention is reported so the user can identify the
first and last included daily intervals.

## Validate Deterministic Strategy and Backtest

Run unit checks against the fixed fixture:

```sh
uv run pytest tests/test_data.py tests/test_strategy.py tests/test_risk.py tests/test_execution.py
```

Run an offline backtest:

```sh
uv run trot backtest \
  --data tests/fixtures/btc_eur_sample.parquet \
  --start 2024-01-01 \
  --end 2025-01-01
```

Expected: strategy, BTC buy-and-hold, EUR cash, and 1x/1.5x/2x cost reports contain all
specified metrics and exposure history. The same command with the same data and settings
produces identical decisions, fills, balances, and metrics. Each signal uses only history
through its completed close; its simulated execution cannot occur before the next candle's
open. Walk-forward report behavior is covered by repeated ordered fold definitions in
`tests/test_backtest.py`; fold boundaries are chronological and no parameter tuning occurs.

## Validate Paper Persistence and Recovery

Use an isolated temporary database path in test configuration:

```sh
uv run pytest tests/test_storage.py tests/test_cli.py
uv run trot paper cycle
uv run trot paper status
```

Expected: paper commands use read-only market access and persist only simulated state.
Running the same cycle again does not add a duplicate decision/order/fill. Restart and
transaction-failure tests show either the prior committed state or one complete candle
update, never a partial balance update. Status shows the latest signal, balances,
allocation, action, and reason.

## Manual Review Gate

Before accepting the feature, verify:

1. Invalid/stale/incomplete/gapped data causes visible validation failure and zero new BTC
   exposure.
2. No order exceeds 50% target BTC allocation, available EUR after fees, or applicable
   precision/minimum rules; required exits bypass the rebalance threshold.
3. There is no live mode or authenticated order submission path.
4. Output and documentation label paper/backtest performance as simulated, not a guarantee
   of future results.
