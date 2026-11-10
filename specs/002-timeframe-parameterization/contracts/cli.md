# CLI Contract: Interval-aware Backtest

## Command

`trot backtest --data <path> [--interval <1d|1h>] [--start <date>] [--end <date>] [--fold <TRAIN_END:TEST_START:TEST_END>]`

## Purpose

Run a historical BTC/EUR strategy simulation using a selected market interval while preserving deterministic, repeatable reporting.

## Input contract

- `--data`: path to a valid Parquet dataset containing BTC/EUR candle history.
- `--interval`: optional interval override; defaults to `1d`.
- `--start`: optional lower bound for included history.
- `--end`: optional upper bound for included history.
- `--fold`: optional walk-forward configuration tuple using `TRAIN_END:TEST_START:TEST_END`.

## Validation rules

- `--interval` must be supported: `1d` or `1h`.
- The dataset must contain a contiguous, valid series for the selected interval.
- The selected range must include valid completed bars.
- The command must fail visibly on gaps, duplicates, unsupported intervals, or impossible ranges.

## Output contract

A successful run emits a JSON object containing at least:

- `interval`
- `label`
- `dataset_hash`
- `config_hash`
- `metrics`
- `benchmarks`
- `cost_stress`
- `folds`
- `ending_cash_eur`
- `ending_btc`
- `ending_equity_eur`

## Failure behavior

If validation fails, the CLI must print a clear error to stderr and return a non-zero exit code without reporting misleading results.
