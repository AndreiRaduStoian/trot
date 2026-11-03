# Data Model: BTC Research and Paper Trading

This design separates numeric market observations and decisions from financial ledger
amounts. Indicator inputs may use finite float64 values; prices, quantities, fees, and
balances used for order sizing or accounting use decimal-safe values. All persisted
timestamps are UTC.

## Entities

### Market Candle

One BTC/EUR daily OHLCV observation from a named market-data source.

| Field | Type / meaning | Validation |
|---|---|---|
| `symbol` | Text; fixed to `BTC/EUR` in this feature | Reject any other symbol |
| `interval` | Text; fixed to `1d` | Reject unsupported intervals |
| `timestamp` | UTC interval-start instant; stable epoch milliseconds in storage | Unique and strictly increasing within a dataset |
| `open`, `high`, `low`, `close` | Positive finite market prices | `high >= max(open, close, low)` and `low <= min(open, close, high)` |
| `volume` | Finite non-negative base-asset volume | Reject negative or non-finite values |
| `source` | CCXT exchange identifier or input-file provenance | Required and retained |
| `complete` | Whether the interval has ended by evaluation time | Only complete candles enter strategy input |

Daily timestamps denote the UTC start of a 24-hour candle. The expected interval is exactly
86,400,000 milliseconds. Duplicate, unordered, gapped, invalid, or incomplete series are
reported; values are not interpolated, forward-filled, or synthesized.

### Market Dataset Manifest

Provenance for the normalized Parquet history, stored as Arrow schema metadata and a
sidecar manifest. It records source/venue, symbol and interval, UTC interval-start meaning,
retrieval range and timestamp, CCXT version, data/schema-validation version, validation
summary, candle count, and a normalized-record hash. The normalized-data hash is distinct
from a hash of Parquet file bytes, so file metadata/compression changes do not change the
identity of identical candle values.

### Public Execution Quote

A read-only BTC/EUR quote used only to simulate the current paper fill. It records source,
exchange timestamp, local receive time, bid, ask, and derived midpoint. Bid and ask must be
positive, finite, and ordered (`bid <= ask`); the exchange timestamp must be present and no
more than 60 seconds old by default. A quote is never used to calculate indicators or
signals. If a valid, fresh bid/ask pair is unavailable, the paper order is not filled.

### Strategy Configuration

The immutable effective settings for a decision or evaluation. Defaults match the feature
specification: BTC/EUR, daily, initial EUR 500, maximum BTC weight 0.50, SMA 30, momentum
lookback 14, volatility window 20 daily returns, annualization 365, volatility target 0.12,
rebalance threshold 0.05, and minimum intended trade EUR 25.

It also includes exchange ID (read-only data; configurable with Kraken as the initial
default), candle freshness cutoff, maximum paper-quote age (default 60 seconds), maker/taker
fee assumptions, spread, slippage, minimum exchange notional, paths, and mode. All fractions
and periods are validated for valid ranges; financial parameters are represented as decimal
strings at I/O boundaries. A canonical
serialization produces `config_hash`, which is stored with decisions and runs. Secret
configuration is not required by this feature.

### Decision

One auditable result for a strategy, configuration, and completed candle.

| Field | Meaning |
|---|---|
| `decision_id` | Deterministic or durable unique identifier |
| `account_id` / `run_id` | Paper account or backtest context |
| `strategy_id`, `config_hash` | Decision logic identity and effective configuration |
| `candle_timestamp`, `data_source`, `data_hash` | Input provenance and market cutoff |
| `sma`, `return_14`, `volatility_20_annualized` | Indicator values; nullable only when unavailable |
| `signal` | `long`, `cash`, or `unavailable` |
| `target_weight`, `current_weight` | Desired and pre-decision BTC portfolio weights |
| `action` | `buy`, `sell`, `hold`, or `abstain` |
| `reason`, `validation_outcome` | Required explanation for no-action, rejection, or invalid data |
| `cash_after`, `btc_after`, `equity_after` | Resulting simulated portfolio snapshot |
| `created_at` | UTC persistence time; not used as strategy input |

The paper uniqueness key is `(account_id, strategy_id, config_hash, candle_timestamp)`.
Repeated processing returns the existing result and cannot create another order or fill.
After a uniqueness conflict, the cycle skips all associated order, fill, and balance side
effects.

### Portfolio State

The simulated account contains EUR cash and BTC quantity, an immutable account identity,
initial EUR value, effective account configuration, and its last processed candle. Equity
and BTC allocation are derived from balances and the decision valuation price; they are
snapshotted on each decision for inspection and audit. Invariants: balances are non-negative,
no borrowing is possible, and each processed candle's resulting state is committed with its
decision.

### Simulated Order and Fill

An order intent is associated with one decision and contains side, requested BTC quantity,
reason, and simulated order type. This release models marketable orders only. Each order has
an explicit state (`filled` or `rejected`); rejected intents retain the reason. A filled
market order has one simulated fill at the applicable execution observation with configured
adverse spread and slippage and the applicable taker fee. No order is assumed to fill from a
limit price touch.

The fill records execution timestamp, reference price, adjusted fill price, BTC quantity,
EUR notional, fee, spread cost, slippage cost, and resulting balances. BTC quantity is rounded
down to market precision; fees are charged in EUR and never exceed available cash. A required
exit that cannot satisfy the applicable minimum is not silently discarded; the decision
reports the remaining BTC.

The hard maximum allocation takes precedence over discretionary rebalancing: if
mark-to-market weight is above the configured cap, a risk-reducing trim is not suppressed by
the 5-percentage-point threshold. The threshold applies only to discretionary target changes
that do not correct a strategy exit or a cap breach.

For the current paper cycle, the reference is the mid-price of a public quote no more than
60 seconds old by default, received after the signal candle closes. The quote is execution
input only and is not used to calculate indicators or signals. Historical backtest and paper
catch-up use the next daily candle's open. If the required observation is unavailable or
stale, the order is not filled.

### Evaluation Run

A backtest or paper session records mode, starting/ending candle, source/data hash,
configuration snapshot and hash, software version, and completion/error status. Backtest
result metadata includes metric values and benchmark/cost-scenario identity. Paper session
identity links the per-candle decisions, simulated orders, fills, and account state.

### Performance Report

For the strategy and each benchmark/scenario, report net return, maximum drawdown,
annualized daily-return volatility, Sharpe ratio (zero risk-free rate, sqrt(365)), filled
order count, turnover (sum of absolute traded EUR notional divided by starting equity),
total fees, and daily BTC exposure. Cost scenarios apply 1x, 1.5x, and 2x configured
execution costs. The report identifies the input range, data/configuration hashes, and
out-of-sample or walk-forward boundaries.

Net return is ending marked-to-market equity divided by starting equity minus one; maximum
drawdown is the greatest peak-to-subsequent-trough decline in daily marked equity. Volatility
and Sharpe use sample daily-return standard deviation and 365-day annualization, with a zero
risk-free rate; Sharpe is unavailable when return variance is zero. Trade count is the number
of filled simulated orders. The BTC buy-and-hold baseline invests the starting value at the
first executable price and liquidates at the final valuation, paying modeled costs on both
sides; the EUR cash baseline remains uninvested.

## Relationships

- One validated dataset contains ordered Market Candles from exactly one pair, interval,
  and source.
- One Strategy Configuration is snapshotted by each Decision and Evaluation Run.
- A paper account has many Decisions; a Decision has zero or one Simulated Order; an order
  has zero or one Simulated Fill in the initial all-or-nothing market fill model.
- One Evaluation Run contains the backtest decisions and report, or references one paper
  account's chronological activity.

## SQLite Tables and Atomicity

| Table | Purpose and key constraints |
|---|---|
| `schema_meta` | Current schema version for explicit, ordered migrations. |
| `paper_accounts` | One row per local account; stores starting EUR, current EUR/BTC balances, last processed candle, and active config hash. Monetary values are decimal strings. |
| `paper_decisions` | Immutable per-candle audit decisions and resulting balance snapshots; unique key on `(account_id, strategy_id, config_hash, candle_ts_ms)`. |
| `paper_orders` | Zero or one simulated intent per decision; foreign key to decision; unique `decision_id`; constrained simulated status and side. |
| `paper_fills` | Zero or one fill per order in the initial fill model; foreign key to order; unique `order_id`; fee, quantity, and prices stored as decimal strings. |
| `evaluation_runs` | Backtest/paper run identity, mode, time range, config/data hashes, status, and serialized metrics/report metadata. |

Enable SQLite foreign keys on every connection and use parameterized statements. For each
paper candle, acquire a `BEGIN IMMEDIATE` transaction, check the uniqueness key, write the
decision/order/fill and update account balances, then commit. Do not hold a write transaction
while fetching market data. If a competing process is waiting, it must re-check the unique
key after obtaining the writer lock; lock timeout or transaction errors are visible failures.
An error before commit rolls back the full candle update.

## State Transitions

### Decision and paper cycle

`input received -> validated | rejected`

`validated -> evaluated -> no-action | order-intent`

`order-intent -> filled | rejected`

`no-action | filled | rejected -> atomically persisted with resulting account snapshot`

If input is invalid, an audit decision may be recorded with the explicit validation failure,
but no new exposure or fill may result. An interrupted transaction leaves either the
previous committed state or the complete new candle result; retry is safe through the unique
decision key.

### Backtest run

`created -> validating -> replaying -> completed | failed`

A failed data validation or unavailable required next execution observation is reported;
the engine does not invent a candle or price to complete the run.
