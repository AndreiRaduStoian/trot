# Implementation Plan: BTC Research and Paper Trading

**Branch**: `001-btc-paper-trading` | **Date**: 2026-11-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-btc-paper-trading/spec.md`

## Summary

Build a CLI-first, single-process BTC/EUR research and paper-trading application. The
implementation will use a functional core for validated market data, deterministic signal
and volatility calculations, risk sizing, and simulated order intents. A thin imperative
shell will provide read-only CCXT data access, Parquet history, transactional SQLite paper
state, and user commands. Backtest and paper modes will share strategy, risk, and order-intent
logic; neither mode will contain a real-order submission path.

## Technical Context

**Language/Version**: Python 3.12 minimum; maintain type annotations for public functions and
shared models. The repository currently declares Python >=3.14 and `.python-version` 3.14;
implementation must deliberately lower and validate the supported floor, then regenerate
the lock file for Python 3.12-compatible dependency releases.

**Primary Dependencies**: uv; pandas and NumPy for time-series data and indicator
calculations; CCXT for read-only OHLCV and public quote retrieval; pyarrow for Parquet;
pydantic-settings for validated configuration; pytest and Ruff for tests, lint, and
formatting. Standard-library `sqlite3`, `decimal`, `logging`, `argparse` (or an equivalently
small CLI parser), and `dataclasses` cover persistence, financial values, logging, command
parsing, and simple models. PyArrow and Ruff must be added explicitly; they are not current
project dependencies. Put pytest and Ruff in a uv development dependency group rather than
the runtime dependency set.

**Storage**: Parquet files for downloaded BTC/EUR candles and provenance metadata; SQLite
for paper account state, decisions, simulated orders/fills, and evaluation metadata. Use
parameterized SQL and explicit transactions; no ORM.

**Testing**: pytest with deterministic candle fixtures and no network/credentials in unit
and backtest tests. CCXT tests use mocks or recorded responses. Ruff runs as the formatter
and linter; CI runs Ruff and pytest.

**Target Platform**: Local Linux, macOS, or Windows; one synchronous process, suitable for
later use on a small Linux VPS. No daemon or always-running server.

**Project Type**: Python CLI application / modular monolith.

**Performance Goals**: No throughput target is required for daily BTC/EUR data. A normal
backtest over locally available daily history must complete as a user-invoked batch
operation; correctness and bounded memory use for one pair take precedence over optimizing
runtime.

**Constraints**: BTC/EUR spot long/cash only; starting paper capital EUR 500; maximum BTC
weight 50%; decisions on completed UTC daily candles; no live orders. Reject invalid or
gapped input rather than repairing it. Use Decimal at monetary and quantity boundaries.
Paper processing must be idempotent and safe under concurrent invocation. The spec's
financial limits and formula defaults remain authoritative.

**Scale/Scope**: One instrument, daily history, one local paper account, small research
datasets, one developer, and four operator workflows: download history, backtest, one
paper-cycle invocation, and inspect paper state/history.

## Constitution Check

| Principle | Plan compliance |
|---|---|
| I. Data Integrity and Evidence First | UTC daily candle intervals have explicit open-time semantics; validation rejects bad order, duplicates, gaps, incomplete candles, and invalid OHLCV. Decisions retain source, input cutoff, candle, configuration identity, and validation outcome. |
| II. Risk Controls Are Non-Negotiable | Only BTC/EUR long/cash simulation exists in this feature. Risk sizing and order intents enforce the 50% cap, available cash after costs, minimums, and rebalancing threshold. No live execution module or authenticated order API is planned. |
| III. Test-First and Reproducible Validation | Pure calculations receive deterministic tests and fixtures first. Tests run without network or credentials; fixed-data backtests must be byte-for-byte/value reproducible at the result level. |
| IV. Explainability and Observability | Decisions, no-action reasons, simulated orders/fills, balances, costs, and provenance are persisted; standard logging reports cycle outcomes without secrets. |
| V. Simplicity and Conservative Defaults | One Python CLI process and small functional modules; no service framework, ORM, server, background queue, or generic execution plugin. Research defaults are configurable and paper is explicit. |
| VI. Execution Integrity and Recovery | The feature has simulated-only execution. A unique strategy/configuration/candle key and one SQLite transaction per candle make repeat runs idempotent and recovery atomic; SQLite's writer lock prevents simultaneous writers from applying the same cycle twice. |
| VII. Honest Backtesting and Live Parity | One chronological engine uses signal-close/next-candle-open timing, explicit costs, cash constraints, benchmarks, out-of-sample periods, and cost stress. Results are labeled simulated research, never profit evidence. |

**Pre-design gate**: PASS. No constitutional violation is required. The request to keep live
execution out of scope is stricter than the constitution's future live-mode safety provisions
and is fully compatible with them. Lowering the project's current declared Python floor from
3.14 to the explicitly requested 3.12 is a planned project configuration change, not a
constitutional change.

## Project Structure

### Documentation (this feature)

```text
specs/001-btc-paper-trading/
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── cli.md
├── quickstart.md
└── tasks.md              # generated by /speckit-tasks, not this command
```

### Source Code (repository root)

```text
.env.example
.github/
└── workflows/
    └── tests.yml
src/
└── trot/
    ├── __init__.py
    ├── main.py            # CLI parsing and orchestration only
    ├── config.py          # validated settings and safe defaults
    ├── models.py          # small shared dataclasses and type aliases
    ├── data.py            # UTC candles, validation, Parquet
    ├── exchange.py        # read-only CCXT OHLCV/public-quote adapter
    ├── strategy.py        # indicators and deterministic signal
    ├── risk.py            # volatility target and allocation bounds
    ├── execution.py       # Decimal order-intent and simulated fill model
    ├── storage.py         # SQLite schema, transactions, idempotency
    └── backtest.py        # chronological simulation and metrics
tests/
├── conftest.py
├── fixtures/
├── test_data.py
├── test_exchange.py
├── test_strategy.py
├── test_risk.py
├── test_execution.py
├── test_storage.py
├── test_backtest.py
└── test_cli.py
data/                      # local-only, ignored by git
├── market/
└── bot.db
```

**Structure Decision**: Use one `src/trot` package rather than the suggested `src/bot`,
because the existing distribution and console script are named `trot`. Point the installed
command to `trot.main:main`. Keep CLI commands in one entry point and responsibilities in
the small modules above; add no separate live adapter. Keep deterministic fixture files small
and checked in, while excluding downloaded market files, SQLite state, environment secrets,
and generated reports from version control.

## Architecture and Data Flow

1. **Download**: CLI validates requested BTC/EUR/date range and settings; the read-only CCXT
   adapter fetches paginated OHLCV with bounded retry/rate-limit handling. Normalize exchange
   timestamps to UTC open times, validate completed daily candles and intervals, then write
   validated records and source metadata to Parquet. Fail visibly on malformed responses,
   unresolved gaps, or incomplete data; never synthesize candles.
2. **Decision core**: Given a valid history ending at a completed candle and a portfolio
   snapshot, the strategy calculates SMA(30), 14-interval close return, and long/cash signal.
   The risk function calculates 20-return sample standard deviation annualized by sqrt(365),
   then target weight `min(max_weight, volatility_target / annualized_volatility)`. Invalid
   or zero volatility cannot create new exposure. Decision output retains indicator values
   and explicit abstention reasons.
3. **Order intent**: Compare target and current weights at the signal close and apply the
   5-percentage-point discretionary threshold; a mandatory signal exit and any risk-reducing
   action needed to restore the hard maximum allocation bypass that threshold. At the next
   available execution observation, revalue the portfolio and
   recompute or safely reduce the intent using that executable price, so a price gap cannot
   breach the maximum allocation or available-cash limit. Apply minimum notional, fees,
   Decimal arithmetic, and configured rounding. A rejected or below-minimum exit returns an
   explicit reason and residual BTC amount.
4. **Backtest**: Walk candles in ascending UTC order. At each completed close, calculate a
   decision from data through that close; execute an eligible simulated market intent no
   earlier than the next candle open. At that open, re-check cash and exposure constraints
   before creating the fill. Apply configured taker fees, spread, and slippage adversely and
   update Decimal cash/quantity accounting. Mark equity to candle closes; compute
   performance and benchmark results from the same observation schedule. No order is filled
   at the close which generated its signal, and unavailable next prices do not produce fills.
5. **Paper**: Fetch/validate read-only current history and identify the latest eligible
   closed candle. Strategy inputs are exclusively completed daily candles. For a current
   cycle, obtain a timestamped public quote after the candle close and use its mid-price as
   the simulated execution reference; apply configured adverse spread/slippage and taker
   fee. For missed cycles, replay historical next-candle opens chronologically. Reject a
   stale/unavailable execution observation. For each candle, derive signal/risk/intent using
   the shared core, recheck cash/exposure at the execution price, then atomically persist
   decision, order/fill (if any), and resulting balances. Unique constraints make retries
   idempotent. Inspect commands read persisted state and history; they do not call trading
   APIs.

## Key Decisions and Trade-offs

- **Pure core / imperative edges**: data, configuration, state, and execution are passed into
  calculation functions. This keeps strategy and risk independently testable; it avoids
  abstractions that have no current second implementation.
- **Daily open-time candle semantics**: a timestamp denotes the UTC start of its daily
  interval; it is complete only after the next UTC midnight. This matches CCXT OHLCV
  convention and makes close-to-next-open backtesting boundaries unambiguous.
- **Paper execution observation**: the current paper cycle may read a public timestamped
  quote after a completed candle close; the quote is an execution reference only and never
  an input to the signal. Require quote age <= 60 seconds by default (configurable).
  Historical catch-up uses next daily candle opens. If no fresh quote/next price exists, the
  simulation does not fabricate a fill.
- **Parquet for market history, SQLite for account state**: efficient local time-series
  snapshots stay separate from small transactional state. Store Arrow schema metadata and
  a JSON sidecar manifest with venue, pair, timeframe, UTC interval semantics, retrieval
  range/time, CCXT and validation/schema versions, and a normalized-data hash. A run records
  that stable data identity/hash and its configuration snapshot so historical output is
  reproducible.
- **Explicit time-series semantics**: compute returns without implicit filling
  (`pct_change(fill_method=None)`); use float64 indicators and explicitly select sample
  standard deviation (`ddof=1`) rather than relying on library defaults.
- **Decimal only at financial boundaries**: pandas/NumPy floats serve indicators; conversion
  using string representations happens before calculating monetary order amounts, fees,
  balances, and rounded quantities.
- **Single-writer paper state**: one `BEGIN IMMEDIATE` transaction per candle plus a unique
  `(account_id, strategy_id, config_hash, candle_ts)` decision key prevents duplicate updates
  across retries and competing invocations. Do not hold a write lock during network calls.
- **Conservative simple fill model**: only marketable simulated orders are needed initially.
  Treat configured spread as the full relative bid/ask spread and apply half adversely to
  the mid/reference price; apply configured slippage additionally in the adverse direction.
  Apply the taker fee to the resulting notional. Keep maker/taker rates configurable; the
  initial marketable-order model uses taker only and makes no passive-fill assumption.
  Re-check cash/exposure at the reference price before creating a fill. More elaborate
  partial-fill models are deferred until required by evidence.
- **No parameter search**: operators specify chronological evaluation windows. Out-of-sample
  and walk-forward reports separate context from test results; code does not tune on test
  outcomes.
- **Configuration from settings plus CLI overrides**: environment settings are validated
  centrally; secret fields are not needed for this read-only feature. An explicit `paper` or
  `backtest` command selects the mode; there is no default live mode or live credential path.

## Testing Strategy

- **Data/exchange**: deterministic tests cover UTC open-time conversion, complete-candle
  cutoff, duplicate/unordered/gapped timestamps, OHLCV invariants, malformed CCXT responses,
  pagination boundaries, and visible rate-limit/API failures. Exchange tests use mocked
  responses and never require credentials.
- **Strategy/risk**: fixed candle fixtures assert SMA and 14-day return boundaries,
  insufficient warmup, entry/exit transitions, sample volatility over 20 returns with
  sqrt(365) annualization, invalid/zero volatility abstention, target sizing, and the 50%
  cap.
- **Order intent/accounting**: Decimal boundary tests assert no negative balance, fees fit
  available cash, quantities round down, minimum notional is enforced, small discretionary
  changes are suppressed, required exits bypass the rebalance threshold, and an undersized
  exit exposes residual BTC. Price-gap tests re-check caps and cash at the next open.
- **Backtest**: deterministic datasets assert chronological replay, no future input, no
  same-close fills, execution no earlier than the next available open, realistic adverse
  costs, no fabricated fills, benchmark treatment, all required metrics, out-of-sample and
  walk-forward boundaries, and identical results on repeat runs and cost stress scenarios.
- **Persistence/paper**: temporary SQLite databases exercise foreign keys, atomic rollback,
  unique decision/order/fill constraints, repeated invocations, contention, crash recovery,
  and balance parity with an uninterrupted run. No test invokes a real-order API.
- **CLI/CI**: subprocess tests validate command results, exit codes, visible failures, and
  status output. Run Ruff and pytest in CI on Python 3.12; at least one additional supported
  runtime may be tested where available. Unit and backtest tests are offline by default.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Exchange history APIs vary in pagination, rate limits, timestamp units, or missing intervals. | Isolate CCXT handling; bound retries, validate returned ranges and candle intervals, and test with fixtures/mocks. |
| A signal-close/next-open fill is still an approximation of achievable execution. | Apply configurable spread/slippage/fees and cost stress; label outputs simulated and avoid passive-fill assumptions. |
| Floating calculations leak into balances and violate caps at rounding boundaries. | Keep indicator calculations separate; use Decimal for all order and ledger values, conservative rounding, and invariant tests. |
| SQLite process interruption occurs near a paper fill. | Commit decision, order/fill, and account update in a single transaction; enforce unique keys and verify retry/restart tests. |
| Python 3.12 has different wheel/dependency availability from the current configured 3.14 environment. | Resolve compatible dependency bounds and regenerate `uv.lock`; run CI and the supported test suite on Python 3.12 before declaring the floor supported. |
| Historical gaps or inconsistent exchange data create false performance. | Reject backtest input with gaps or invalid candles; preserve source and validation report; do not forward-fill. |

## Open Questions

No product or scope clarification blocks implementation. The exchange is configurable, with
Kraken as the initial public-data default; the implementation must verify the selected
venue's BTC/EUR market, daily history support, fee/precision/minimum metadata, pagination
limits, and timestamped quote behavior at runtime. Unsupported or unavailable market rules
must stop the affected download or order simulation visibly rather than fall back to guessed
values.

## Constitution Check (Post-design)

**Post-design gate**: PASS. Module boundaries keep pure signals, risk, and intent separate
from network and persistence. The chosen simulated fill model and chronology satisfy the
no-look-ahead and cost-aware backtesting rules. The schema and transaction boundary preserve
auditability and retry safety. There is no live mode, authenticated order method, or code
path to real orders. No complexity-tracking exception is needed.
