# Feature Specification: Timeframe Parameterization

**Feature Branch**: `[002-timeframe-parameterization]`

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "Parameterize the BTC/EUR timeframe and execution interval so the app supports daily and hourly candles. Remove hard-coded 1d assumptions from config, validation, backtesting, and CLI logic while preserving daily as the default. Validate interval-specific timestamps, contiguity, and completed-bar rules; ensure trade execution occurs on the next valid bar open after signal generation; and keep historical results deterministic and repeatable across runs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run research with the default daily cadence (Priority: P1)

An operator wants to run the BTC/EUR research workflow with the existing daily pattern and expect the same behavior as before unless they explicitly choose a different interval.

**Why this priority**: Daily candles are the current baseline and must remain stable while the feature expands support to additional interval choices.

**Independent Test**: An operator can run a historical strategy on a daily dataset without changing any defaults and receive the same valid outputs for the same inputs.

**Acceptance Scenarios**:

1. **Given** a valid BTC/EUR daily dataset and no interval override, **When** the operator starts a backtest, **Then** the system uses the daily interval by default.
2. **Given** a valid daily dataset and configuration, **When** the same backtest is run twice, **Then** the system produces identical decisions, fills, balances, and summary metrics.

---

### User Story 2 - Select hourly candles for analysis and execution (Priority: P1)

An operator wants to evaluate the strategy on hourly candles and execute trades only after the next valid bar open, while preserving the same operational rules used for daily history.

**Why this priority**: Hourly support unlocks more granular market analysis and must behave consistently with the daily mode without introducing look-ahead bias or inconsistent fill timing.

**Independent Test**: A known hourly dataset can be loaded, a strategy can be evaluated, and the system can report results without relying on future information.

**Acceptance Scenarios**:

1. **Given** a valid hourly BTC/EUR dataset, **When** the operator selects the hourly interval, **Then** the system accepts the dataset and evaluates strategy decisions using completed bars only.
2. **Given** a signal generated on a completed bar, **When** the next valid hourly bar open is available, **Then** the system executes against that next bar open rather than the signal bar itself.
3. **Given** a selected interval that is not supported, **When** the operator runs the analysis, **Then** the system rejects the request with a clear validation error.

---

### User Story 3 - Detect invalid or incomplete interval data before a run (Priority: P2)

An operator wants the system to reject invalid history clearly and early so the strategy is not run against incomplete or manipulated market data.

**Why this priority**: Gaps, duplicate timestamps, stale bars, and impossible ranges are high-risk conditions that can invalidate strategy results.

**Independent Test**: A dataset with missing, duplicate, or out-of-order bars fails before the simulation begins and does not produce a misleading result.

**Acceptance Scenarios**:

1. **Given** a market series with missing bars or duplicate timestamps, **When** the operator starts a run, **Then** the system fails visibly and explains the data issue.
2. **Given** a time range that does not include a completed bar at the selected interval, **When** the operator requests the run, **Then** the system rejects the request instead of fabricating or backfilling data.

---

### Edge Cases

- What happens when the chosen interval is unsupported or misspelled?
- How does the system handle a dataset with a valid daily default but a conflicting hourly override?
- What happens when a signal is created but no next valid bar exists for execution?
- How does the system handle repeated runs using the same fixed dataset and configuration?
- What happens when a dataset is contiguous within one interval but contains an impossible requested range?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow operators to choose the BTC/EUR market interval for research and execution without changing the core product scope.
- **FR-002**: The system MUST default to the daily interval when no interval is specified, preserving current operator behavior.
- **FR-003**: The system MUST accept at least the supported daily and hourly interval selections and reject unsupported values with a clear error.
- **FR-004**: The system MUST validate interval-specific timestamps, contiguity, and completed-bar rules before running a strategy or reporting results.
- **FR-005**: The system MUST use only completed candles in strategy evaluation and must never rely on information from the current or future bar to produce a signal.
- **FR-006**: The system MUST execute trades no earlier than the next valid bar open after the signal bar, preserving chronological fairness and avoiding same-close fills.
- **FR-007**: The system MUST reject incomplete, duplicated, out-of-order, stale, or impossible historical ranges instead of repairing or guessing missing values.
- **FR-008**: The system MUST include interval information in run metadata and result output so operators can distinguish daily and hourly analysis runs.
- **FR-009**: The system MUST produce deterministic results for the same dataset, interval, and configuration when executed repeatedly.
- **FR-010**: The system MUST present clear, actionable failures when validation or range selection prevents execution.

### Key Entities *(include if feature involves data)*

- **Market History**: A sequence of BTC/EUR candles for a chosen interval, including timestamp, open, high, low, close, volume, and source provenance.
- **Execution Interval**: The bar size used to evaluate signals and determine when trades can occur, such as daily or hourly.
- **Strategy Run**: A historical scenario using a dataset, selected interval, and configuration to generate decisions, fills, and summary metrics.
- **Research Result**: A deterministic report containing the strategy outcome, benchmark comparisons, and validation metadata for the selected interval.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators can run the project’s BTC/EUR research workflow using either the default daily interval or a valid hourly interval without changing the feature’s core scope.
- **SC-002**: A run using the same dataset, interval, and configuration produces identical decisions, fills, balances, and summary metrics on repeated executions.
- **SC-003**: Invalid intervals, missing bars, duplicate timestamps, or impossible requested ranges are rejected before simulation output is reported.
- **SC-004**: A decision generated from a completed bar executes only on the next valid bar open, preventing same-close fills and future-looking behavior.
- **SC-005**: Results clearly identify the active interval and remain understandable to operators evaluating daily versus hourly performance.

## Assumptions

- The system continues to focus on BTC/EUR research and paper trading without expanding into additional markets or live execution.
- Daily candles remain the default interval unless an operator explicitly selects another supported interval.
- A single interval is used per run; mixed interval datasets are not merged or inferred.
- The market data source and configuration remain fixed for a given run, allowing deterministic historical comparison.
- Unsupported intervals are rejected rather than silently converted or approximated.
