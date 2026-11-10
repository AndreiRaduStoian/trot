# Quickstart: Timeframe Parameterization

## Prerequisites

- The project environment must be available with the repository dependencies installed.
- A BTC/EUR dataset must exist in Parquet format and contain a contiguous series for the chosen interval.
- Daily remains the default interval; use the interval override only when running hourly analysis.

## Validation scenarios

### 1. Default daily backtest

Run the product’s standard backtest flow without an interval override.

```bash
python -m trot.main backtest --data data/market/btc-eur.parquet
```

Expected outcome:
- The run uses `1d` as the interval.
- The report includes daily metrics and benchmark data.
- The output is deterministic for repeated runs with the same dataset and configuration.

### 2. Hourly backtest

Run the same historical flow with an explicit hourly interval.

```bash
python -m trot.main backtest --data path/to/hourly-btc-eur.parquet --interval 1h
```

Expected outcome:
- The run accepts hourly candles only when the series is valid and contiguous.
- Signals are generated only from completed bars.
- Execution occurs on the next valid hourly bar open after the signal bar.

### 3. Download hourly history

Download hourly candles for an inclusive UTC date range:

```bash
uv run trot data download --since 2025-01-01 --until 2026-10-10 --interval 1h --output data/market/btc-eur-1h.parquet
```

Expected outcome:
- The exchange request uses `1h` and is paginated until the requested historical window is covered or the source reports no more data.
- Only candles inside the requested UTC date window whose hourly interval has completed are saved.
- The Parquet manifest records `interval: 1h` and the requested dates.
- If the requested window contains no completed candles, the command fails with a clear message and writes no dataset.

### 4. Invalid interval handling

```bash
python -m trot.main backtest --data path/to/history.parquet --interval 15m
```

Expected outcome:
- The command fails visibly.
- The user sees a clear validation error for the unsupported interval.

### 5. Gapped or invalid data

Use a series with missing bars, duplicate timestamps, or stale incomplete bars.

Expected outcome:
- The run fails before producing a strategy result.
- No misleading or partial output is reported.

## Notes

- The interval should be considered part of the run metadata and not just a local preference.
- All validation and execution decisions should be based on the same interval definition throughout the run.
