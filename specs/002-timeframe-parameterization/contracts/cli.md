# CLI Contract: Interval-aware Data and Backtest Commands

## Command

`trot backtest --data <path> [--interval <1d|1h>] [--start <date>] [--end <date>] [--fold <TRAIN_END:TEST_START:TEST_END>]`

`trot data download --since <date> --until <date> [--interval <1d|1h>] [--exchange <name>] [--output <path>]`

`trot download --start <date> --end <date> [--interval <1d|1h>] [--exchange <name>] [--output <path>]`

## Purpose

Download validated BTC/EUR history or run a historical strategy simulation using a selected market interval while preserving deterministic, repeatable reporting.

## Input contract

- `--data`: path to a valid Parquet dataset containing BTC/EUR candle history.
- `--interval`: optional interval override; defaults to `1d`.
- `--start`: optional lower bound for included history.
- `--end`: optional upper bound for included history.
- `--fold`: optional walk-forward configuration tuple using `TRAIN_END:TEST_START:TEST_END`.
- `--since` / `--start`: inclusive UTC calendar start date for downloads.
- `--until` / `--end`: inclusive UTC calendar end date for downloads; the exclusive request boundary is 00:00 UTC on the following day.
- Download `--interval`: optional interval override; defaults to `1d`.

## Validation rules

- `--interval` must be supported: `1d` or `1h`.
- The dataset must contain a contiguous, valid series for the selected interval.
- The selected range must include valid completed bars.
- The command must fail visibly on gaps, duplicates, unsupported intervals, or impossible ranges.
- Download requests and timestamp filtering must use the selected interval and requested UTC date window.
- A downloaded bar is retained only when its interval-start timestamp is in the requested window and its interval has fully elapsed by the current UTC time.
- Historical exchange pagination must make progress toward the requested start and must not silently return a different, newer page when the requested window is older.
- If no completed candles are returned for the requested window, the command must report that condition clearly and must not write Parquet data or a manifest.

## Output contract

A successful backtest emits a JSON object containing at least:

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

A successful download writes Parquet data and a matching provenance manifest whose `interval`, requested dates, candle count, and normalized content hash match the downloaded dataset. The existing download status line reports the selected interval and available range.

## Failure behavior

If validation fails, the CLI must print a clear error to stderr and return a non-zero exit code without reporting misleading results.
