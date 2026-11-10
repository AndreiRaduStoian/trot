# Research: Timeframe Parameterization

## Decision

Support a configurable interval parameter with a default of `1d` and explicit support for `1h` in research, validation, and backtest execution. All interval-aware logic will use a single normalized interval description and reject unsupported values instead of silently special-casing them.

## Rationale

The current codebase hard-codes daily semantics in configuration, validation, and strategy timing. The feature objective is to preserve the existing daily workflow while enabling a second, supported interval without rewriting the strategy logic itself. A single interval parameter keeps the behavior consistent across data ingestion, validation, and execution timing, and it aligns with the project constitution’s requirement for data integrity and deterministic historical output.

## Alternatives considered

### 1. Hard-code hourly checks in a few functions

Rejected because it would duplicate validation and timing rules and leave daily assumptions scattered through the app. That approach would increase configuration drift and make future intervals harder to support.

### 2. Treat interval as a free-form string with no validation

Rejected because it weakens the safety guarantees already required by the constitution. The app must reject unsupported intervals and incomplete bars instead of guessing or repairing data.

### 3. Separate interval logic for data and execution

Rejected because execution timing and data validation must follow the same interval semantics; otherwise a dataset and a signal can disagree about when the next valid bar exists.

## Key findings

- The feature should keep the default daily cadence intact unless an operator explicitly chooses hourly data.
- A normalized interval value should drive validation behavior, including timestamp spacing, contiguity, and completion checks.
- The strategy must evaluate only completed bars; trade execution must occur on the next valid open bar after the signal is generated.
- Results must include the active interval metadata so comparisons between daily and hourly runs remain interpretable.
- Deterministic runs require the same interval, dataset, and configuration to be captured in metadata and backtest output.

## Open decisions resolved

- Supported intervals: `1d` (default), `1h`.
- Unsupported interval values are rejected with a clear validation error.
- Historical validation checks must use interval-specific duration rules rather than a daily-only assumption.
- Trade execution uses next-bar-open semantics for the selected interval.
