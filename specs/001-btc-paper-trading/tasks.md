# Tasks: BTC Research and Paper Trading

**Input**: Design documents from `/specs/001-btc-paper-trading/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included because the specification requires deterministic risk/data checks and the
Trot Constitution mandates test-first validation.

**Organization**: Tasks are grouped by user story so each increment can be implemented and
verified at its checkpoint.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable against other tasks in the phase because it edits separate files
  and has no unmet prerequisite.
- **[Story]**: User-story mapping: US1 data and decision, US2 historical evaluation, US3
  paper operations.
- Every task names the file or files it changes.

## Phase 1: Setup

**Purpose**: Align the package and tooling with the planned supported runtime.

- [X] T001 [P] Set `requires-python` to `>=3.12`, add PyArrow as a runtime dependency, place pytest and Ruff in a development dependency group, and set the `trot` console entry point to `trot.main:main` in `pyproject.toml`; regenerate `uv.lock` with Python 3.12.
- [X] T002 [P] Set the repository interpreter to Python 3.12 in `.python-version`.
- [X] T003 [P] Ignore local SQLite databases, downloaded market data, environment files, and generated runtime artifacts in `.gitignore`.
- [X] T004 [P] Add documented safe paper/backtest defaults and storage paths, with no credentials or real-trading settings, to `.env.example`.
- [X] T005 Add a CI workflow at `.github/workflows/tests.yml` that installs from `uv.lock` on Python 3.12 and runs Ruff checks and pytest without network credentials.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define shared data/configuration types and safe CLI foundations required by all
user stories.

- [ ] T006 Add failing configuration tests in `tests/test_config.py` for BTC/EUR, daily candles, EUR 500 starting capital, 50% exposure cap, SMA 30, momentum 14, volatility window 20, annualization 365, 12% target volatility, EUR 25 minimum, 5-percentage-point rebalance threshold, and rejection of invalid/out-of-range values.
- [ ] T007 Define shared typed records and enums in `src/trot/models.py` for Market Candle, Strategy Configuration, Decision, Portfolio State, simulated order/fill, Evaluation Run, and Performance Report; keep `signal` to `long`, `cash`, or `unavailable`, `action` to `buy`, `sell`, `hold`, or `abstain`, indicators nullable only when unavailable, and require a reason and validation outcome for no-action, rejection, or invalid data.
- [ ] T008 Implement validated settings and research defaults in `src/trot/config.py`, including configurable fees, spread, slippage, minimum exchange notional, data/database paths, mode, exchange source, and paper-quote age; reject unsupported symbols/modes and never configure authenticated order submission.
- [ ] T009 Create the synchronous CLI entry point and standard logging setup in `src/trot/main.py`; route errors to stderr, reserve stdout for command results, return non-zero status on operation failures, and expose no live command or real-order route.

**Checkpoint**: Shared contracts and safe settings are ready; user-story work can start.

---

## Phase 3: User Story 1 - Validate Data and Evaluate BTC Exposure (Priority: P1) 🎯 MVP

**Goal**: Load and validate BTC/EUR daily data and produce deterministic, auditable signals,
target weights, and risk-bounded order intents without submitting any order.

**Independent Test**: With deterministic candles and a supplied portfolio state, verify data
validation, SMA/momentum/volatility, signal, target allocation, action/reason, and order-intent
limits without network access or order submission.

### Tests for User Story 1

> Write these checks first and confirm they fail before implementing the corresponding behavior.

- [ ] T010 [US1] Create deterministic valid and invalid BTC/EUR candle builders in `tests/conftest.py` and reusable fixtures under `tests/fixtures/`; keep expected timestamps UTC and all results reproducible.
- [ ] T011 [P] [US1] Add failing market-data tests in `tests/test_data.py` for these Market Candle constraints: "`symbol` fixed to `BTC/EUR`", "`interval` fixed to `1d`", "`timestamp` UTC interval-start instant; stable epoch milliseconds in storage", "`Unique and strictly increasing within a dataset`", "`high >= max(open, close, low)` and `low <= min(open, close, high)`", "`Finite non-negative base-asset volume`", "`source` Required and retained", and "`Only complete candles enter strategy input`"; also assert duplicate, unordered, gapped, stale, and incomplete series are rejected without filling.
- [ ] T012 [P] [US1] Add failing read-only CCXT adapter tests in `tests/test_exchange.py` for BTC/EUR 1d pagination, UTC millisecond boundaries, rate-limit/timeouts, malformed and short responses, unsupported market/timeframe, and the absence of authenticated order calls.
- [ ] T013 [P] [US1] Add failing strategy tests in `tests/test_strategy.py` for SMA over the current 30 completed closes, 14-interval close return, entry/exit transitions, deterministic output, and insufficient warmup.
- [ ] T014 [P] [US1] Add failing volatility and sizing tests in `tests/test_risk.py` for sample standard deviation (`ddof=1`) over 20 returns, `sqrt(365)` annualization, 12% target sizing, 50% cap, and invalid/zero-volatility abstention.
- [ ] T015 [P] [US1] Add failing order-intent/accounting tests in `tests/test_execution.py` for Decimal rounding down, expected fees, available EUR, no negative balance, the 5-percentage-point discretionary threshold, mandatory exit/cap-breach bypass, minimum notional `max(EUR 25, exchange minimum)`, and explicit residual BTC on undersized exit.
- [ ] T016 [US1] Add failing `trot data download` and invalid-data CLI contract tests in `tests/test_cli.py`, asserting visible error details and non-zero status without a real network call.

### Implementation for User Story 1

- [ ] T017 [US1] Implement UTC OHLCV normalization, completeness and interval validation, gap/duplicate/price checks, Parquet read/write, Arrow metadata, and the provenance sidecar manifest in `src/trot/data.py`; do not interpolate or forward-fill.
- [ ] T018 [US1] Implement public CCXT OHLCV retrieval in `src/trot/exchange.py` with enabled rate limiting, bounded UTC-millisecond pagination/retries, BTC/EUR and 1d capability checks, and explicit API failure results; expose no authenticated exchange methods.
- [ ] T019 [US1] Implement pure indicator and long/cash signal functions in `src/trot/strategy.py`; calculate only on validated completed candles, include the current close in SMA(30), use the close 14 daily intervals earlier for momentum, and return explicit unavailable/no-action reasons.
- [ ] T020 [US1] Implement pure realized-volatility and target-allocation functions in `src/trot/risk.py`; use the most recent 20 daily returns, sample standard deviation, `sqrt(365)`, configurable 12% target and 50% maximum, and no new exposure for insufficient/invalid/zero volatility.
- [ ] T021 [US1] Implement Decimal order-intent sizing and simulated fill-price helpers in `src/trot/execution.py`; apply fee/spread/slippage assumptions, balance/cap checks at execution price, conservative quantity rounding, required-exit handling, and minimum-order residual reporting.
- [ ] T022 [US1] Wire `trot data download` in `src/trot/main.py` to `src/trot/config.py`, `src/trot/exchange.py`, and `src/trot/data.py`; report source, date range, candle count, validation, and actionable failures.

**Checkpoint**: User Story 1 is independently testable with fixtures; no command or module
can send real orders.

---

## Phase 4: User Story 2 - Evaluate the Strategy Historically (Priority: P2)

**Goal**: Replay history without look-ahead, account for realistic execution costs, and report
the strategy alongside BTC buy-and-hold and EUR cash.

**Independent Test**: Run a fixed dataset and configuration twice and compare all decisions,
fills, balances, and metrics; verify fill timing, benchmarks, out-of-sample windows, and
1x/1.5x/2x cost reports.

### Tests for User Story 2

> Write these checks first and confirm they fail before implementing the backtester.

- [ ] T023 [US2] Add failing chronological simulation and report tests in `tests/test_backtest.py` for no future inputs, no same-close fills, next-candle-open execution, price-gap risk rechecks, fees/spread/slippage, cash/position/minimum constraints, benchmark results, all required metrics, chronological folds, 1x/1.5x/2x costs, data-gap failure, and identical repeated runs.

### Implementation for User Story 2

- [ ] T024 [US2] Implement the chronological backtest engine in `src/trot/backtest.py`, reusing `src/trot/strategy.py`, `src/trot/risk.py`, and `src/trot/execution.py`; calculate a signal only through each completed close and execute no earlier than the next available candle open after rechecking risk limits.
- [ ] T025 [US2] Add explicit EUR cash and BTC buy-and-hold benchmarks, marked-equity exposure history, net return, maximum drawdown, annualized volatility, Sharpe ratio, filled-order count, turnover, fees, out-of-sample/walk-forward folds, and 1x/1.5x/2x cost scenarios to `src/trot/backtest.py`; identify data/configuration hashes and label results simulated research.
- [ ] T026 [US2] Wire `trot backtest` in `src/trot/main.py` to load and validate Parquet history and call `src/trot/backtest.py`; emit metrics and benchmark/stress results and fail visibly on invalid data or impossible ranges.

**Checkpoint**: User Story 2 runs offline and repeatably from a fixed historical dataset.

---

## Phase 5: User Story 3 - Observe Successive Candles in Paper Mode (Priority: P3)

**Goal**: Persist simulated account decisions, orders, fills, and balances; process candles
idempotently; and safely resume after interruption.

**Independent Test**: Process successive completed candles, repeat a cycle, and simulate a
restart/transaction failure; compare persisted state and balances with an uninterrupted
deterministic run and confirm no duplicate records or real orders.

### Tests for User Story 3

> Write these checks first and confirm they fail before implementing storage or orchestration.

- [ ] T027 [P] [US3] Add failing SQLite persistence tests in `tests/test_storage.py` for foreign-key constraints, parameterized writes, schema versioning, `BEGIN IMMEDIATE` transaction behavior, uniqueness on `(account_id, strategy_id, config_hash, candle_ts_ms)`, atomic rollback, busy timeout, and all-or-nothing balance/order/fill updates; require unique `decision_id` and `order_id` associations as defined in `specs/001-btc-paper-trading/data-model.md`.
- [ ] T028 [P] [US3] Add failing paper-cycle tests in `tests/test_paper.py` for completed-candle processing, fresh timestamped public quote age of at most 60 seconds by default, historical catch-up at next candle open, repeated-run idempotency, interruption recovery, inspectable no-action reasons, and zero real-order submissions.

### Implementation for User Story 3

- [ ] T029 [US3] Implement SQLite schema/versioning and repository functions in `src/trot/storage.py` for `paper_accounts`, `paper_decisions`, `paper_orders`, `paper_fills`, and `evaluation_runs`; use parameterized SQL, foreign keys, decimal-string money values, bounded busy handling, and explicit transactions.
- [ ] T030 [US3] Add read-only public bid/ask quote retrieval and validation in `src/trot/exchange.py`; require positive finite prices, `bid <= ask`, an exchange timestamp, and a configurable freshness limit defaulting to 60 seconds.
- [ ] T031 [US3] Implement one `trot paper cycle` orchestration path in `src/trot/main.py`; fetch and validate before acquiring the SQLite writer lock, process unhandled candles chronologically, use a current fresh quote only as an execution reference, recheck cash/exposure, and atomically persist each decision/order/fill/account update.
- [ ] T032 [US3] Implement `trot paper status` in `src/trot/main.py` using `src/trot/storage.py`; report simulated label, balances, latest signal, target/current allocation, candle, action/reason, and recent decisions/orders/fills without network access.

**Checkpoint**: User Story 3 resumes deterministically, prevents duplicates, and has no
real-order execution path.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Document operations and verify the complete feature against its acceptance
criteria.

- [ ] T033 Document uv/Python setup, configuration, history download, backtesting, paper cycle/status commands, data artifacts, and the explicit no-live-orders limitation in `README.md`.
- [ ] T034 Run all scenarios in `specs/001-btc-paper-trading/quickstart.md` on Python 3.12, then run Ruff and the complete pytest suite; fix failures in the relevant source/test files and confirm CI uses the committed lock.
- [ ] T035 Review the final implementation against `.specify/memory/constitution.md` and `specs/001-btc-paper-trading/spec.md`; verify data provenance, financial invariants, audit records, idempotent recovery, no-look-ahead, simulated labeling, and no real-order path, recording any deviation in the pull request description.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No source prerequisites; T005 CI configuration follows dependency/runtime setup.
- **Foundational (Phase 2)**: Starts after project setup. Shared types, validated settings, and CLI/logging structure block all stories.
- **User Story 1 (Phase 3)**: Depends on Phase 2; delivers the validated data and pure decision/risk core.
- **User Story 2 (Phase 4)**: Depends on User Story 1 because it reuses its validation, strategy, risk, and execution calculations.
- **User Story 3 (Phase 5)**: Depends on User Story 1 for shared decisions and intent calculation; it is independent of User Story 2 after User Story 1 is complete.
- **Polish (Phase 6)**: Depends on all stories selected for release.

### User Story Dependencies

```text
Setup -> Foundational -> US1 (P1) -> US2 (P2)
                              \----> US3 (P3)
US2 and US3 may proceed independently after US1, subject to shared-file coordination in
src/trot/main.py. The preferred single-developer sequence is US1, then US2, then US3.
```

### Within Each User Story

- Tests are written first and confirmed failing before implementing the behavior they cover.
- US1 data validation precedes exchange integration; pure strategy, risk, and execution work
  can proceed in parallel once shared models exist.
- US2 engine and metrics precede CLI wiring.
- US3 storage and quote validation precede paper-cycle orchestration; status inspection uses
  the completed persistence layer.
- Complete each story checkpoint before relying on its code in a later story.

### Parallel Opportunities

- **Setup**: T001-T004 touch separate configuration/documentation paths and can run in parallel; T005 follows the project dependency setup.
- **US1 tests**: T011-T015 use separate test modules after T010 supplies shared fixtures; T016 is a separate CLI test path.
- **US1 implementation**: T019-T021 touch distinct pure-calculation modules and can proceed in parallel after models and their tests; T018 follows T017 because exchange normalization uses data validation.
- **US2**: Core implementation and CLI wiring are sequential in `src/trot/backtest.py` then `src/trot/main.py`.
- **US3 tests**: T027 and T028 touch separate test modules and can run in parallel.
- **US3 implementation**: T029 and T030 touch separate storage/exchange modules and can proceed in parallel; T031/T032 both touch `src/trot/main.py` and should be implemented sequentially.

## Parallel Examples

### User Story 1

```text
After T010:
Task: T011 market-data validation tests in tests/test_data.py
Task: T012 read-only exchange tests in tests/test_exchange.py
Task: T013 strategy tests in tests/test_strategy.py
Task: T014 volatility/risk tests in tests/test_risk.py
Task: T015 order-intent tests in tests/test_execution.py
Task: T016 data-download CLI tests in tests/test_cli.py

After the tests and shared models:
Task: T019 signal calculations in src/trot/strategy.py
Task: T020 volatility sizing in src/trot/risk.py
Task: T021 order-intent calculations in src/trot/execution.py
```

### User Story 2

```text
Task: T023 backtest and report tests in tests/test_backtest.py
Then complete T024 and T025 in src/trot/backtest.py before T026 in src/trot/main.py.
```

### User Story 3

```text
After US1:
Task: T027 SQLite atomicity/idempotency tests in tests/test_storage.py
Task: T028 paper-cycle/recovery tests in tests/test_paper.py

After tests:
Task: T029 SQLite persistence in src/trot/storage.py
Task: T030 read-only quote handling in src/trot/exchange.py
```

## Implementation Strategy

### MVP First (User Story 1)

1. Complete setup and foundational tasks.
2. Complete US1 tests before implementing its data, strategy, risk, and order-intent modules.
3. Validate US1 offline with deterministic fixtures and confirm its download boundary is
   read-only.
4. Stop at the US1 checkpoint if a minimal usable research core is the immediate goal.

### Incremental Delivery

1. Add US2 after US1 and verify deterministic backtest/benchmark/stress outputs.
2. Add US3 after US1 and verify persistence, restart safety, and no duplicate processing.
3. Complete documentation, Python 3.12 CI, and constitutional acceptance checks.

## Notes

- `[P]` indicates separate-file work with no unmet dependency; tasks sharing `src/trot/main.py`
  are intentionally sequential.
- Every task includes an explicit file path and story-phase tasks carry the matching story
  label.
- No live execution, multiple pairs, parameter optimization, web service, or external database
  belongs in this task set.
