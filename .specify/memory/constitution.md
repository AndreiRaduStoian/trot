# Trot Constitution

## Core Principles

### I. Data Integrity and Evidence First

Market data, indicators, account state, and strategy assumptions MUST come from explicit,
validated inputs. The bot MUST reject or quarantine missing, duplicate, out-of-order, stale,
non-finite, or otherwise inconsistent data; it MUST NOT replace invalid observations with a
plausible signal or silently forward-fill data used for execution.

Market timestamps MUST be normalized to UTC. Strategy decisions MUST use only information
available at decision time, including fully closed candles; historical and live code MUST
apply the same candle-completion and indicator-warmup rules. Exchange-specific market,
precision, fee, and minimum-order information MUST be validated before placing an order.

Each decision MUST be attributable to the input snapshot, source/exchange, candle timestamp,
strategy/configuration version, and validation outcome. If required inputs are unavailable,
the bot MUST abstain from creating new exposure and report why.

Rationale: Incorrect or future-leaking market data can create fictitious signals and real
financial losses.

### II. Risk Controls Are Non-Negotiable

Trot's initial live scope MUST be unlevered, long-only BTC/EUR spot trading with EUR cash as
the alternative position. Shorting, margin, borrowing, derivatives, and transfers or
withdrawals MUST NOT be part of the initial live execution path. Strategy logic MUST NOT
bypass the risk engine or place exchange orders directly.

Before live trading is enabled, configuration MUST specify and validate maximum asset
exposure, maximum order value, minimum usable order value, volatility-sizing limits,
rebalancing thresholds, drawdown/operational halt thresholds, and the action taken when each
limit is hit. Initial exposure MUST be capped at 50% of portfolio equity; raising that cap
requires an explicit, reviewed configuration change. Risk sizing MUST be bounded and MUST
NOT use leverage to reach a volatility target.

Risk checks MUST be applied to the latest reconciled balances, outstanding orders, and
proposed order together, including trading fees and available EUR. If risk inputs or
exchange state are uncertain, Trot MUST block orders that increase exposure. Risk-reducing
orders MAY proceed only when their size, asset availability, and execution context can be
verified. A kill switch MUST stop new risk-increasing orders, cancel eligible open orders
where safe, alert the operator, and require explicit re-enablement; it MUST NOT claim that
all positions were liquidated or that losses are capped.

Rationale: Circuit breakers, stops, and volatility targets reduce or constrain intended
risk but cannot guarantee execution prices or prevent losses during gaps and outages.

### III. Test-First and Reproducible Validation

Each behavior change MUST begin with a failing automated test or an explicitly documented,
deterministic verification fixture. Signal, sizing, accounting, order-intent, and failure
handling logic MUST be testable without network access, credentials, or mutable exchange
state. Tests MUST cover insufficient data, stale candles, numerical edge cases, fee and
precision boundaries, minimum orders, duplicate execution, partial fills, API failures,
and recovery after interruption where applicable.

The runtime, dependencies, test datasets, configuration, and random seeds (if any) MUST be
reproducible. CI MUST run deterministic unit and backtest checks without live API keys. A
change MUST NOT be declared validated solely because a historical return curve improved.

Rationale: A deterministic failure is debuggable; an unreproducible trading result is not.

### IV. Explainability and Observability

Each trading cycle MUST record a unique decision identifier, data cutoff, strategy inputs,
computed signal, volatility estimate, proposed weight, risk adjustments, intended order,
execution outcome, and no-trade or halt reason. Records MUST distinguish simulated orders,
submitted orders, accepted orders, partial fills, final fills, cancellations, and rejections.

Trot MUST preserve a durable audit trail across restarts and MUST monitor account exposure,
order status, realized fees, execution slippage, strategy turnover, drawdown, rejected
orders, stale data, and exchange/API failures. Critical operational failures MUST generate
an actionable alert. Secrets and sensitive authentication material MUST NOT appear in logs,
error messages, reports, or test fixtures.

Rationale: P&L alone does not explain whether a decision or its execution was correct.

### V. Simplicity and Conservative Defaults

Trot MUST begin as a single Python application with separate, focused modules for signal
generation, risk sizing, exchange access, execution, storage, and backtesting. Signal and
risk calculations SHOULD be pure functions with explicit inputs and outputs. The same core
decision functions MUST be used in backtest, paper, and live modes; only data, state, and
execution adapters may differ by mode.

Live execution MUST be disabled by default. A single instrument, completed daily candles,
and infrequent rebalancing are the initial baseline. Additional assets, shorter timeframes,
ML, market making, distributed services, and new infrastructure MUST be justified by a
measured need and reviewed costs, not anticipated complexity. Prefer plain functions and
small modules over speculative object hierarchies or frameworks.

Rationale: A small, inspectable system is easier to verify and safer to operate.

### VI. Execution Integrity and Recovery

Order execution MUST be separated from signal generation and risk decisions. Every intended
live order MUST have a durable, unique client-side identifier and persisted intent before
submission. Repeated scheduler runs, timeouts, process restarts, and uncertain API responses
MUST NOT cause blind order resubmission. After an ambiguous response, Trot MUST reconcile
exchange orders, fills, balances, and outstanding exposure before any retry that could
increase risk.

Live execution MUST enforce exchange symbol, precision, minimum notional, available balance,
and fee constraints. Partial fills, cancellations, and unfilled limit orders MUST be modeled
as distinct states; a candle touching a limit price MUST NOT count as a guaranteed fill.
At most one trading cycle for the same account/strategy MAY submit orders concurrently.
After restart, the bot MUST reconcile real exchange state rather than assume its local
state is authoritative. If reconciliation fails, it MUST stop opening risk and alert.

Rationale: Duplicate orders and incorrect recovery can cause larger losses than a bad
forecast, especially with unattended execution.

### VII. Honest Backtesting and Live Parity

Backtests MUST model decision-time availability, indicator warmup, next-available
execution, maker/taker fees, spreads, slippage, order-size constraints, and cash balances.
They MUST avoid look-ahead bias, same-close fills when the close produced the signal,
survivorship-biased asset selection, and unrealistically certain limit-order fills.
The strategy MUST be evaluated after costs against relevant buy-and-hold and cash baselines.

Research MUST use chronological training/validation/test separation or walk-forward
evaluation. Parameters MUST be chosen on training/validation data, not by repeatedly
inspecting the final out-of-sample period. Performance MUST include net returns,
maximum drawdown, turnover, and cost sensitivity (at least base, 1.5x, and 2x cost
assumptions). Paper results MUST be labeled simulated and MUST NOT be presented as proof
of achievable live fills or profit.

Rationale: Backtest profitability without executable prices and independent validation is
not sufficient evidence for risking capital.

## Additional Constraints

- **Initial operating profile:** EUR-denominated portfolio with approximately EUR 500 of
  starting capital; BTC/EUR only; spot long/cash; no leverage; maximum 50% BTC exposure.
  Capital, order-size, and risk parameters MUST be configuration values rather than
  hard-coded assumptions. Changes to this profile require documented review before live use.
- **Implementation:** Python with an explicit supported version and locked dependencies.
  SQLite and local files/Parquet are sufficient initially; extra services MUST have a
  demonstrated requirement. External exchange integrations MUST be isolated behind a
  small adapter and tested with deterministic substitutes.
- **Credentials:** API keys MUST come from environment variables or an approved secrets
  mechanism and MUST NOT enter version control. Live trading credentials MUST have only
  required permissions; withdrawal and transfer permissions MUST remain disabled.
- **Trading modes:** `backtest`, `paper`, and `live` MUST be explicit, mutually exclusive
  runtime modes. The default MUST NOT send live orders. Live mode MUST require a deliberate,
  documented opt-in and successful preflight checks of credentials, symbol, balances,
  market rules, clock/data freshness, persistent storage, and the kill switch.
- **Operational controls:** A live scheduler MUST have single-instance protection,
  persistent order state, bounded retries, API rate-limit handling, and a documented manual
  stop/recovery procedure. A network or exchange outage MUST NOT trigger uncontrolled retries.
- **Scope of guarantees:** No design document, dashboard, or report MAY imply that
  targeted volatility, stop orders, risk thresholds, or backtest results guarantee profit
  or a maximum realized loss.

## Development Workflow

1. **Specify:** State the behavior, inputs, outputs, error cases, financial invariants,
   and which constitution principles apply.
2. **Verify first:** Add a failing unit/integration test or deterministic fixture,
   including negative paths and edge cases for risk-affecting changes.
3. **Implement minimally:** Keep calculations pure where feasible, execution isolated,
   configuration explicit, and side effects auditable.
4. **Validate research changes:** Run chronological out-of-sample evaluation, baseline
   comparisons, and fee/slippage stress tests before claiming a strategy improvement.
5. **Validate execution changes:** Exercise mocks and paper mode for accepted, rejected,
   partially filled, timed-out, cancelled, and recovered orders. Confirm no duplicate
   submissions under restart or retry.
6. **Gate live use:** Review the risk configuration, observe paper behavior, complete
   live preflight checks, document the operator's approval, and begin with deliberately
   small orders. No automatic promotion from paper to live is permitted.
7. **Review deployment:** Record affected assumptions, configuration diffs, test
   results, monitoring changes, and a rollback/disable plan in the pull request or
   equivalent change record. Verify post-deployment account and order reconciliation.

Changes involving data sourcing, signal interpretation, trading costs, sizing, order
submission, credentials, or recovery MUST be explicitly reviewed before merge and before
live activation. Exceptions to a MUST requirement cannot be used to bypass live-trading
safety gates.

## Governance

This constitution is the authoritative source for Trot's data integrity, research,
risk, execution, testing, and operational standards. It supersedes conflicting informal
practices. Every relevant specification, implementation plan, and pull request MUST include
a constitution check; unresolved MUST violations block live release.

Amendments MUST document their rationale, affected principles, migration implications,
and maintainer approval. The Sync Impact Report records the version change and follow-up
items. Versioning follows Semantic Versioning: MAJOR for backward-incompatible principle
or governance changes; MINOR for new principles or materially expanded requirements;
PATCH for non-semantic clarifications. Configuration changes do not automatically require
amending this constitution unless they alter its governing rules.

Reviewers MUST check that a change preserves data provenance, financial invariants,
execution recovery, and auditability. Any justified, time-bounded exception MUST identify
an owner, scope, expiry, and mitigation; exceptions MUST NOT silently enable live trading
or override the explicit safety requirements above.
