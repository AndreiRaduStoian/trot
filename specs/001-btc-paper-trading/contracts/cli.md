# CLI Contract

The application is a local, synchronous CLI. Every command uses validated settings and
explicitly reports errors; logs and diagnostics go to stderr, while command results go to
stdout. Exit status is zero only when the requested operation completed successfully.
No command submits, signs, or authorizes a real order.

## Commands

### `trot data download`

Fetches historical BTC/EUR daily OHLCV from the configured read-only CCXT exchange, validates
it, and writes a Parquet data file.

Inputs: exchange identifier (default Kraken), start and end UTC dates, and output path. Pair
and interval remain fixed to BTC/EUR and daily in this feature.

Successful result: output path, symbol, source, requested/available date range, candle count,
and data validation summary. Missing intervals, malformed responses, unsupported history,
rate-limit exhaustion, or invalid candles produce a visible error and non-zero status; the
command does not repair the data.

### `trot backtest`

Runs a deterministic simulation over a validated local Parquet dataset.

Inputs: data path, chronological start/end boundaries, validated strategy/cost settings, and
optional chronological fold definitions. Each fold identifies its training-end, test-start,
and test-end dates using `--fold TRAIN_END:TEST_START:TEST_END`; repeat `--fold` for
successive walk-forward windows. Each test start must be after its training end, and folds
must be chronologically ordered and non-overlapping. Strategy settings are supplied
directly and are not tuned by the command.

Successful result: strategy metrics, BTC buy-and-hold and EUR cash comparisons, 1x/1.5x/2x
cost results, and exposure history. Results identify the data and configuration hashes and
are labeled simulated research. Invalid input or an impossible evaluation range fails
visibly rather than emitting plausible metrics.

### `trot paper cycle`

Fetches/loads current read-only market history, validates it, and processes unhandled
completed candles chronologically for the persistent simulated paper account. The latest
signal uses a completed candle only; its simulated execution uses a fresh public quote
obtained after the close, while historical catch-up uses the next candle open. Exactly one
invocation performs the required cycle work and exits. Repeating an invocation is safe;
already processed candles are not duplicated.

Successful result: latest processed candle, signal, target/current weight, action/reason,
simulated balance snapshot, and fill details if an order filled. A stale/invalid input or
unavailable execution observation is explicitly reported and cannot increase exposure.

### `trot paper status`

Reads the local SQLite paper account without network access.

Inputs: optional number of recent decisions to display.

Successful result: current EUR and BTC balances, latest completed candle, current/target
allocation, latest signal/action/reason, and recent decisions/orders/fills. Empty or
unavailable state is reported explicitly.

## Configuration and Safety

Validated settings are centralized and may be supplied by environment variables and documented
CLI overrides. Research parameters, cost assumptions, data/database paths, mode, and exchange
source are explicit. `backtest` and `paper` are separate user commands; there is no `live`
mode, order endpoint, exchange credential, or mode fallback in this feature.

## Exit Behavior

- `0`: successful operation (including a valid no-action decision).
- Non-zero: invalid settings, data validation failure, inaccessible storage, exchange/API
  failure, failed backtest, or paper recovery/transaction failure.
- A no-action/rejected trading decision is a successfully evaluated result only when its
  reason is reported; it is not represented as a successful fill.
