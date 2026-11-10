# Data Model: Timeframe Parameterization

## Entities

### MarketCandle

Represents one completed market bar for a BTC/EUR series.

- symbol: BTC/EUR
- interval: `1d` or `1h`
- timestamp: UTC instant representing the beginning of the bar
- open: first price in the interval
- high: maximum price in the interval
- low: minimum price in the interval
- close: final price in the interval
- volume: traded volume for the interval
- source: market source or provenance label
- metadata: optional provenance details

Validation rules:
- Symbol must be BTC/EUR.
- Interval must be one of the supported values.
- Timestamp must be in UTC and align to the interval boundary.
- Prices and volume must be finite and positive where required.
- For a valid series, timestamps must be strictly ordered and contiguous for the selected interval.

### IntervalProfile

Describes the active bar size used by the run.

- value: `1d` or `1h`
- default: `1d`
- step_size: `24h` for daily, `1h` for hourly
- completion_rule: a bar is complete only after the next interval boundary elapses
- execution_lookup: next valid bar open after signal generation

### StrategyRun

Represents one historical or research execution.

- dataset_hash: stable hash of the input dataset
- config_hash: stable hash of the strategy settings
- interval: selected interval for this run
- start_timestamp: first included observation
- end_timestamp: last included observation
- decisions: generated strategy decisions in chronological order
- fills: executed fills and fees
- metrics: summarised return, volatility, drawdown, benchmark, and turnover results

Relationships:
- A StrategyRun references one IntervalProfile.
- A StrategyRun consumes a contiguous MarketCandle series.
- A StrategyRun emits one or more fills and one summary result.

### ResearchResult

Represents the output reported to the operator.

- label: `simulated research`
- interval: selected interval
- metrics: financial summary
- benchmarks: EUR cash and BTC buy-and-hold baselines
- cost_stress: 1x, 1.5x, and 2x cost scenarios
- folds: walk-forward or out-of-sample validation windows
- dataset_hash: stable dataset identity
- config_hash: stable configuration identity

## State transitions

- Market data is accepted only when it passes interval-aware validation.
- Strategy signals are generated from completed bars only.
- A valid signal may transition to a fill only when the next valid bar open exists and risk constraints still pass.
- Invalid or incomplete data transitions to a rejected run and surfaces a visible error.
