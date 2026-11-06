# Trot

Trot is a local BTC/EUR research and paper-trading CLI. It reads public market data and
stores simulated account activity locally. It does not submit, sign, or authorize real
orders.

## Setup

Use Python 3.12 or newer and `uv`:

```sh
uv sync --all-groups
uv run pytest
uv run ruff check .
```

Settings use the `TROT_` environment prefix. The default profile is BTC/EUR daily data,
Kraken public market data, EUR 500 starting simulated cash, a 50% maximum BTC allocation,
and a 60-second public-quote age limit. `TROT_DATA_DIR` and `TROT_DB_PATH` select local
market and paper-state paths. No exchange credentials are required or supported for this
feature.

## Download History

Fetch completed UTC daily candles and store validated Parquet plus a JSON provenance
manifest:

```sh
uv run trot data download \
	--exchange kraken \
	--since 2024-01-01 \
	--until 2025-01-01 \
	--output data/market/btc-eur-2024.parquet
```

The requested dates are inclusive. Duplicate, invalid, gapped, or incomplete candles are
reported as errors; Trot does not fill or synthesize missing observations. The manifest
records the source, requested range, schema-validation version, candle count, and normalized
content hash. `uv run trot download --start DATE --end DATE` remains available as a legacy
alias.

## Backtest

Run a deterministic simulation over a downloaded dataset:

```sh
uv run trot backtest \
	--data data/market/btc-eur-2024.parquet \
	--start 2024-01-01 \
	--end 2025-01-01
```

Optional walk-forward windows use repeated `--fold TRAIN_END:TEST_START:TEST_END` arguments.
The output is labeled simulated research and includes strategy metrics, EUR cash and BTC
buy-and-hold comparisons, exposure history, and 1x/1.5x/2x execution-cost scenarios. Signals
use data through each completed close; simulated fills use no earlier than the next candle
open.

## Paper Operations

Process unhandled candles and inspect persisted simulated state:

```sh
uv run trot paper cycle
uv run trot paper status --recent 10
```

`paper cycle --data PATH` selects a local Parquet dataset. The latest history must include
the most recently completed UTC candle. Historical catch-up uses next-candle opens; the
latest simulated execution requires a fresh public quote. Decisions, no-action reasons,
simulated orders/fills, and balances are persisted atomically in SQLite. Repeating a cycle
does not duplicate already-processed candles. Status reads SQLite only and makes no network
calls.

Paper and backtest results are simulations, not evidence of achievable live fills or future
profit. Live trading, authenticated endpoints, leverage, short positions, and other trading
pairs are outside this feature.
