# Research: BTC Research and Paper Trading

## Python 3.12 and Dependency Compatibility

**Decision**: Adopt Python 3.12 as the supported minimum, as requested. Keep the requested
dependency set and explicitly add PyArrow and Ruff; regenerate and validate `uv.lock` with
Python 3.12 before claiming support.

**Rationale**: Release metadata checked for CCXT, NumPy, pandas, pydantic-settings, pytest,
uv-build, PyArrow, Ruff, and uv supports Python 3.12. The current repository configuration
still requires/selects Python 3.14 in `pyproject.toml`, `uv.lock`, and `.python-version`, and
does not yet declare PyArrow or Ruff. The lock and interpreter selection are therefore
implementation prerequisites, not proof that the project already supports 3.12.

**Alternatives considered**: Keep the existing 3.14 floor (rejected because it conflicts
with the explicit feature requirement); rely on an undeclared Parquet engine (rejected
because Parquet support must be reproducible and explicit).

## SQLite Paper-State Atomicity and Idempotency

**Decision**: Use standard-library `sqlite3`, parameterized SQL, explicit transactions,
foreign keys, a unique account/strategy/configuration/candle key, and one
`BEGIN IMMEDIATE` transaction per candle. Perform network work before opening the
transaction. After acquiring the writer lock, re-check the uniqueness key; on a duplicate,
skip the entire set of order/fill/balance side effects. Use a bounded busy timeout and
surface lock/transaction failures rather than silently continuing.

**Rationale**: A local single-process application needs crash atomicity and retry safety, not
an ORM or database service. SQLite serializes writers; the unique key and transaction
boundary prevent duplicate paper state when rerun or interrupted.

**Alternatives considered**: PostgreSQL and an ORM add operational/dependency complexity
without a current multi-writer or query requirement. An uncoordinated sequence of writes
would permit partial account updates and is rejected.

## Candle Time Semantics and Indicator Calculations

**Decision**: Treat exchange daily timestamps as UTC interval-open times and a candle as
complete only after the following UTC midnight. Validate and order intervals before indicator
calculation; reject gaps rather than fill them. Calculate the 30-close mean including the
current completed close, the 14-interval return, and sample standard deviation (`ddof=1`)
over the most recent 20 daily returns, annualized by `sqrt(365)`. Use explicit
`pct_change(fill_method=None)` semantics.

**Rationale**: These conventions align with the feature spec and prevent implicit filling,
ambiguous interval boundaries, and differences caused by library defaults. Twenty daily
returns require 21 closing prices.

**Alternatives considered**: Population standard deviation (`ddof=0`) and a 252-day
annualization change the research hypothesis; aggregating intraday data introduces
unnecessary candle-boundary decisions.

## CCXT Read-Only Market Data

**Decision**: Use CCXT's public unified OHLCV retrieval with rate limiting enabled,
UTC-millisecond pagination, bounded requests/retries, and explicit runtime checks that the
configured venue supports BTC/EUR and daily candles. Use a timestamped public quote only as
the current paper fill reference, never as a strategy input. Treat short pages, overlaps,
gaps, malformed responses, unsupported markets, or stale quotes as explicit errors/no-action
conditions.

**Rationale**: CCXT provides a small unified adapter while venue history limits and missing
candle behavior remain exchange-specific. Explicit checks avoid assumptions about default
history size or completeness. The initial configurable default venue is Kraken; its actual
market/timeframe support and current API behavior must be checked at runtime and tested with
recorded/mocked responses.

**Alternatives considered**: A venue-specific adapter offers finer API control but duplicates
the unified interface for one data source. Assuming a complete default response or filling
gaps is rejected.

## Parquet and Data Provenance

**Decision**: Store normalized market history as Parquet with PyArrow declared and locked.
Add Arrow schema metadata and a JSON sidecar manifest recording venue, symbol, timeframe,
UTC timestamp meaning, retrieval range/time, CCXT version, validation/schema version,
validation summary, candle count, and normalized-record hash. Store data/configuration
identity with each evaluation run.

**Rationale**: Pandas needs an explicit Parquet engine; declaring PyArrow prevents reliance on
an accidental local install. A normalized-record hash distinguishes identical candle
content from differences in Parquet byte layout or compression and preserves reproducibility.

**Alternatives considered**: CSV is simpler to inspect but lacks typed column/schema metadata.
Storing candle history in SQLite couples immutable research inputs to transactional paper
state. Both remain possible for later evidence-based needs, not this implementation.

## Sources

- [CCXT Manual: OHLCV and rate limiting](https://github.com/ccxt/ccxt/wiki/Manual#ohlcv-candlestick-charts)
- [CCXT Manual: rate limiting](https://github.com/ccxt/ccxt/wiki/Manual#rate-limit)
- [Python 3.12 sqlite3 transaction control](https://docs.python.org/3.12/library/sqlite3.html#transaction-control)
- [SQLite transactions](https://www.sqlite.org/lang_transaction.html)
- [SQLite table constraints](https://www.sqlite.org/lang_createtable.html)
- [SQLite UPSERT](https://www.sqlite.org/lang_upsert.html)
- [pandas `to_datetime`](https://pandas.pydata.org/docs/reference/api/pandas.to_datetime.html)
- [pandas `pct_change`](https://pandas.pydata.org/docs/reference/api/pandas.Series.pct_change.html)
- [pandas `to_parquet`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_parquet.html)
- [NumPy `std`](https://numpy.org/doc/stable/reference/generated/numpy.std.html)
- [Arrow schema metadata](https://arrow.apache.org/docs/python/generated/pyarrow.Schema.html)
- [Parquet file metadata](https://parquet.apache.org/docs/file-format/metadata/)
- [PyPI release metadata: CCXT 4.5.91](https://pypi.org/project/ccxt/4.5.91/)
- [PyPI release metadata: NumPy 2.5.4](https://pypi.org/project/numpy/2.5.4/)
- [PyPI release metadata: pandas 3.1.0](https://pypi.org/project/pandas/3.1.0/)
- [PyPI release metadata: pydantic-settings 2.16.2](https://pypi.org/project/pydantic-settings/2.16.2/)
- [PyPI release metadata: pytest 9.2.0](https://pypi.org/project/pytest/9.2.0/)
- [PyPI release metadata: PyArrow 26.0.1](https://pypi.org/project/pyarrow/26.0.1/)
- [PyPI release metadata: Ruff 0.17.3](https://pypi.org/project/ruff/0.17.3/)
- [PyPI release metadata: uv-build 0.13.5](https://pypi.org/project/uv-build/0.13.5/)
- [PyPI release metadata: uv 0.13.7](https://pypi.org/project/uv/0.13.7/)
