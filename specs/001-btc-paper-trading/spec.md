# Feature Specification: BTC Research and Paper Trading

**Feature Branch**: `001-btc-paper-trading`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: Build Trot's first functional research and paper-trading version for conservative BTC/EUR spot decisions, historical evaluation, and simulated portfolio management; live orders are out of scope.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate Data and Evaluate BTC Exposure (Priority: P1)

As a Trot operator, I can load BTC/EUR daily market history and see a reproducible hold-BTC-or-hold-EUR decision with its indicators, proposed allocation, and reasons, so I can check the strategy and risk rules before simulating trades.

**Why this priority**: Valid, time-correct data and safe, inspectable decisions are prerequisites for all research and paper trading.

**Independent Test**: Provide a deterministic BTC/EUR candle history and a portfolio state; verify its validation result, indicators, signal, target allocation, action, and explanation without submitting any order.

**Acceptance Scenarios**:

1. **Given** a complete, valid BTC/EUR daily history with enough indicator warmup, **When** the operator evaluates its latest completed UTC candle, **Then** the decision reports the 30-day average, 14-day return, 20-return annualized volatility, signal, target allocation, current allocation, and action.
2. **Given** the close is above its 30-day average and its 14-day return is positive, **When** volatility is valid, **Then** the strategy signals BTC exposure sized to its volatility target and no more than the configured maximum.
3. **Given** either entry condition is false while BTC is held, **When** the strategy evaluates a completed candle, **Then** it identifies a required exit regardless of the discretionary rebalance threshold.
4. **Given** a candle is incomplete or stale, or the input has duplicate timestamps, a gap, or invalid prices, **When** the operator requests an evaluation, **Then** the result explicitly identifies the data problem and does not increase exposure or fabricate a decision from invalid data.
5. **Given** the strategy lacks sufficient history or valid volatility, **When** the operator evaluates an entry, **Then** the decision explicitly abstains from establishing new exposure and states why.

---

### User Story 2 - Evaluate the Strategy Historically (Priority: P2)

As a researcher, I can replay a validated history and compare the strategy with BTC buy-and-hold and EUR cash after realistic costs, so I can assess its risk-adjusted behavior without mistaking an in-sample result for evidence of future profit.

**Why this priority**: Historical, cost-aware evidence is needed to evaluate whether the research hypothesis merits further paper observation.

**Independent Test**: Run a fixed dataset and configuration twice and verify identical decisions, fills, balances, and reported performance; inspect the results against both benchmarks.

**Acceptance Scenarios**:

1. **Given** valid chronological BTC/EUR candles and a strategy configuration, **When** the researcher runs a backtest, **Then** signals use only information available at each decision time and simulated fills occur no earlier than the next available executable price.
2. **Given** a backtest run, **When** results are reported, **Then** they include net returns, maximum drawdown, annualized volatility, Sharpe ratio, trade count, turnover, total fees, and exposure over time, plus BTC buy-and-hold and EUR-cash comparisons.
3. **Given** a backtest run with configured execution costs, **When** the researcher requests cost stress results, **Then** the report shows outcomes at 1x, 1.5x, and 2x those costs.
4. **Given** the researcher defines chronological out-of-sample or walk-forward periods, **When** a run is evaluated, **Then** parameters are not selected using the final test period and period boundaries are reflected in the results.
5. **Given** identical validated data and configuration, **When** the backtest is run repeatedly, **Then** it produces identical decisions, accounting, and metrics.
6. **Given** a dataset contains an invalid candle sequence or gap in the requested evaluation period, **When** a backtest is requested, **Then** the run reports the validation failure rather than filling the gap or reporting misleading performance.

---

### User Story 3 - Observe Successive Candles in Paper Mode (Priority: P3)

As an operator, I can run the strategy in paper mode over completed candles and inspect simulated balances, decisions, orders, and fills, so I can observe its behavior without risking real funds.

**Why this priority**: Persistent paper observation exercises the shared decision and risk rules over time while ensuring that no live execution is involved.

**Independent Test**: Process successive completed candles, interrupt and resume the run, then verify balances and records match an uninterrupted run and no candle has duplicate decisions or simulated orders.

**Acceptance Scenarios**:

1. **Given** an initial EUR 500 simulated portfolio and valid completed candles, **When** paper mode evaluates successive candles, **Then** it reuses the backtest strategy and risk decisions and updates EUR and BTC balances using explicit simulated costs and fills.
2. **Given** an already processed strategy/configuration/candle, **When** paper mode is restarted or that candle is submitted again, **Then** no duplicate decision, order, or fill is created.
3. **Given** paper mode is interrupted, **When** the operator resumes it, **Then** it restores the prior simulated balances and history and continues without duplicate processing or unexplained accounting changes.
4. **Given** a paper decision, **When** the operator inspects current status or history, **Then** the latest signal, target/current allocation, portfolio state, decision records, simulated orders, fills, and no-action or rejection reasons are available.
5. **Given** any data, configuration, or portfolio state, **When** paper mode evaluates it, **Then** no real order is submitted and the result is clearly labeled simulated.
6. **Given** an exit position is smaller than the applicable minimum order value, **When** paper mode evaluates the exit, **Then** it reports the remaining BTC exposure explicitly rather than hiding or silently discarding it.

### Edge Cases

- The most recent candle has not closed in UTC, is stale, or arrives after an expected evaluation; no signal may use an incomplete candle.
- A candle has a duplicate timestamp, is out of order, has a missing interval, or has non-positive/non-finite prices or inconsistent OHLC values.
- There is insufficient history for the moving average, return, or volatility estimate, or estimated volatility is zero or invalid.
- The target-weight change is below 5 percentage points, the order value is below the applicable minimum, or fees would exceed the available EUR.
- Current simulated account state is missing, inconsistent, or cannot be restored; no action may increase exposure.
- A required exit is below the minimum order value; the decision must report residual exposure.
- The next executable price is unavailable after a signal; the simulation must not invent a fill at the signal candle's close.
- A paper run is repeated or interrupted after persisting a decision but before completing simulated accounting; recovery must preserve a single consistent outcome.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support BTC/EUR spot exposure only, with long BTC or EUR cash; it MUST NOT support leverage, margin, borrowing, short positions, or other trading pairs in this feature.
- **FR-002**: The system MUST provide a configurable initial portfolio value with a conservative default of EUR 500 and a configurable maximum BTC allocation with a default of 50% of portfolio equity.
- **FR-003**: The system MUST retrieve or load BTC/EUR daily OHLCV history, retain source identity and UTC candle timestamps, and validate timestamp ordering, duplicates, expected intervals, candle completion, and price consistency.
- **FR-004**: The system MUST NOT fabricate, silently replace, or silently forward-fill missing or invalid candles. It MUST report data validation failures and MUST block decisions that could increase exposure while required data is unreliable.
- **FR-005**: The system MUST evaluate a strategy decision only from completed daily UTC candles and MUST expose the candle timestamp used for each decision.
- **FR-006**: The strategy MUST signal entry when the completed close is above its 30-day simple moving average and the 14-day price return is positive. It MUST signal exit when either condition is false. These periods and the return threshold MUST be configurable with the specified values as defaults.
- **FR-007**: The system MUST estimate annualized volatility from the most recent 20 daily returns using 365 days per year. The window and annualization basis MUST be configurable with the specified values as defaults.
- **FR-008**: When entry conditions hold and volatility is valid, the system MUST calculate target BTC allocation from the configured annualized volatility target (default 12%) divided by estimated annualized volatility, capped at the configured maximum BTC allocation. The volatility target MUST be configurable.
- **FR-009**: The system MUST NOT establish new BTC exposure if required history, market data, volatility, or account state is insufficient or invalid. Each such abstention MUST be an explicit no-action decision with a reason.
- **FR-010**: The risk rules MUST keep BTC allocation at or below the configured maximum, account for expected fees in order sizing, and never spend more EUR than the available balance.
- **FR-011**: The system MUST suppress discretionary allocation changes smaller than 5 percentage points of portfolio equity by default, while allowing a required strategy exit to bypass that threshold. The threshold MUST be configurable.
- **FR-012**: The system MUST reject order intents below the greater of EUR 25 or the applicable market minimum by default. The EUR threshold MUST be configurable. A required exit below the minimum MUST be reported with its remaining exposure.
- **FR-013**: The system MUST NOT use averaging down, martingale sizing, leverage, borrowing, or discretionary overrides of configured risk limits.
- **FR-014**: Every decision MUST record its candle timestamp, source, relevant indicators, signal, volatility estimate, target and current allocation, action, and validation outcome. No-action and rejected decisions MUST include reasons.
- **FR-015**: The backtester MUST replay validated candles chronologically and MUST prevent look-ahead by calculating each signal only from information available at its decision time.
- **FR-016**: Backtest execution MUST occur no earlier than the next available executable price after signal generation and MUST account for configurable maker and taker fees, spread, and slippage. A passive order MUST NOT be assumed filled solely because a candle touched its limit price.
- **FR-017**: Backtests MUST respect available EUR, BTC allocation limits, fees, and applicable minimum order values. They MUST compare the strategy with BTC buy-and-hold and EUR cash.
- **FR-018**: Backtest reports MUST include net returns, maximum drawdown, annualized volatility, Sharpe ratio, number of trades, turnover, total fees, and exposure over time. They MUST support chronological out-of-sample and walk-forward evaluation and cost stress tests at 1x, 1.5x, and 2x estimated execution costs.
- **FR-019**: Backtest results MUST be deterministic for identical validated historical data and configuration, and MUST identify simulated results as research rather than a guarantee of future performance.
- **FR-020**: Paper mode MUST use the same strategy and risk rules as backtesting, maintain simulated EUR and BTC balances, and account explicitly for simulated execution, fees, spread, and slippage.
- **FR-021**: Paper mode MUST persist decisions, simulated orders, fills, and balances; it MUST resume after interruption and prevent duplicate decisions or simulated orders for the same strategy/configuration and candle.
- **FR-022**: The operator MUST be able to inspect the latest paper signal, target allocation, portfolio state, and decision history, including no-action and rejection reasons.
- **FR-023**: This feature MUST NOT submit real orders. Research/backtest/paper behavior MUST remain clearly distinguishable from any future live execution capability.
- **FR-024**: Critical data-integrity, strategy, risk, accounting, chronology, and restart/idempotency behavior MUST be verifiable with deterministic checks that do not require live credentials or real orders.

### Key Entities *(include if feature involves data)*

- **Market Candle**: A BTC/EUR daily OHLCV observation with its UTC interval, completion status, source, and validation result.
- **Strategy Configuration**: The configurable signal periods, volatility target/window, exposure cap, starting value, rebalancing and minimum-order limits, and execution-cost assumptions used for a run.
- **Decision**: The auditable result for a completed candle, including data cutoff, indicators, signal, volatility, target/current allocation, action, and explanation.
- **Portfolio State**: EUR cash, BTC quantity, equity valuation, allocation, and the time/configuration context used to evaluate a decision.
- **Simulated Order and Fill**: A paper/backtest order intent and its simulated execution details, including price, quantity, fee, spread/slippage cost, status, and associated decision.
- **Evaluation Run**: A deterministic backtest or paper session with input data identity, configuration, chronological evaluation period, and results.
- **Performance Report**: Strategy and benchmark metrics, cost stress results, and exposure history for an evaluation run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a valid BTC/EUR history with adequate warmup, 100% of evaluated decisions identify the exact completed UTC candle and the values used for all required indicators.
- **SC-002**: Across deterministic risk-boundary checks, 100% of generated order intents respect the configured BTC cap, available EUR after fees, rebalancing threshold, and minimum order value, except that a required below-minimum exit is explicitly reported as residual exposure.
- **SC-003**: On a fixed valid dataset and configuration, 100 repeated backtests produce identical decisions, simulated accounting, and reported metrics.
- **SC-004**: Every backtest report includes all eight requested performance measures, both benchmarks, exposure over time, and results at 1x, 1.5x, and 2x costs.
- **SC-005**: In chronology checks, no simulated fill is attributed to the same candle close that generated its signal, and no decision uses candles later than its decision timestamp.
- **SC-006**: In restart and repeated-candle checks, paper trading creates zero duplicate decisions, orders, or fills and restores balances consistent with the uninterrupted run.
- **SC-007**: In invalid, stale, incomplete, or insufficient-data checks, the system creates zero new BTC exposure and records an explicit reason.
- **SC-008**: In paper-mode checks, the number of real orders submitted is zero, and every displayed paper result is identified as simulated.
- **SC-009**: An operator can inspect the most recent signal, target allocation, portfolio balances, and decision history for a paper run without manually reconstructing its decisions from raw candles.

## Assumptions

- Initial portfolio value is EUR 500; the specified parameter values are conservative research defaults, not validated optimal values.
- Target allocation is the lesser of the configured maximum BTC weight and the annualized volatility target divided by estimated annualized volatility, when the strategy entry signal is true.
- The current candle is included in its 30-day simple moving average; a 14-day return compares its close with the close 14 daily intervals earlier. Volatility uses the sample standard deviation of the most recent 20 daily returns, annualized by the square root of 365.
- A historical series with a gap in the requested backtest period is rejected for performance reporting rather than repaired. In paper mode, invalid or missing required data produces an explicit no-action decision until valid history is available.
- A signal generated at a daily close is simulated no earlier than the next candle's open, adjusted adversely for configured spread and slippage; marketable simulated orders use taker fees unless a fill model explicitly establishes another execution type.
- The EUR-cash benchmark remains entirely in cash. The BTC buy-and-hold benchmark invests the starting portfolio value in BTC at the start of the evaluation period, subject to available funds and modeled entry/exit costs, and is a research comparison rather than a risk-limit-compliant strategy.
- Sharpe ratio uses a zero risk-free return and the same 365-day annualization basis. Missing required data or an unavailable next executable price prevents a simulated fill rather than causing a fabricated price.
- For a current decision, market data is stale if it does not include the most recently completed daily UTC candle for the evaluation date. A later or incomplete candle is not treated as completed. After an interruption, paper mode may catch up only by processing unhandled candles chronologically when each required next executable price is available; otherwise it records a no-action reason.
- Paper mode is simulation only and has no path for submitting, signing, or authorizing real exchange orders.
