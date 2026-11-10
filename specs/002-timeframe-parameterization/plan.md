# Implementation Plan: Timeframe Parameterization

**Branch**: `002-timeframe-parameterization` | **Date**: 2026-11-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-timeframe-parameterization/spec.md`

## Summary

Parameterize the BTC/EUR market interval and execution cadence so the trading app supports the existing daily default and an explicit hourly mode without hard-coded 1d assumptions. The design keeps the deterministic backtest workflow, validates interval-aware data integrity, and enforces next-bar-open execution semantics for both supported intervals.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: PyArrow, pandas, NumPy, pydantic-settings, CCXT, pytest, Ruff

**Storage**: Local Parquet market history and SQLite for paper execution state when needed

**Testing**: pytest with deterministic fixture data and validation-focused regressions

**Target Platform**: Local Linux/macOS/Windows CLI use

**Project Type**: Python CLI application / modular monolith

**Performance Goals**: Support small research datasets and user-invoked backtests without introducing throughput or memory problems

**Constraints**: BTC/EUR only; daily remains default; hourly support is explicit and validated; no live trading or unsupported intervals

**Scale/Scope**: One instrument, interval-aware history validation, deterministic historical simulation, no new asset classes or live execution paths

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Data Integrity and Evidence First | PASS | The feature explicitly requires validated interval-aware timestamps, contiguity checks, and completed-bar rules. |
| II. Risk Controls Are Non-Negotiable | PASS | No live risk expansion or leverage change is introduced; the feature remains BTC/EUR and simulation-only. |
| III. Test-First and Reproducible Validation | PASS | Deterministic output and validation tests remain required for hourly and daily behavior. |
| IV. Explainability and Observability | PASS | Interval metadata and run provenance remain part of the output contract. |
| V. Simplicity and Conservative Defaults | PASS | The feature uses the existing single-module CLI structure and keeps daily as the default. |
| VI. Execution Integrity and Recovery | PASS | The design preserves next-bar-open execution semantics and rejects invalid range data. |
| VII. Honest Backtesting and Live Parity | PASS | The run remains research-only and avoids same-close fills/look-ahead bias. |

## Project Structure

### Documentation (this feature)

```text
specs/002-timeframe-parameterization/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cli.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── trot/
│   ├── config.py
│   ├── data.py
│   ├── backtest.py
│   ├── main.py
│   ├── models.py
│   ├── strategy.py
│   ├── execution.py
│   └── risk.py
└── tests/
    ├── test_backtest.py
    ├── test_cli.py
    └── ...
```

**Structure Decision**: Keep the current single-package CLI architecture and extend interval validation and run metadata in the existing modules instead of creating a parallel code path. The feature is an internal parameterization change, not a product rewrite.

## Complexity Tracking

No constitution violations require formal exceptions for this feature.
