from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import ccxt
import pyarrow as pa
import pyarrow.parquet as pq

from .models import MarketCandle


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value) / 1000, tz=UTC)

    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp: {value!r}") from exc
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    raise ValueError(f"Unsupported timestamp data: {type(value).__name__}")


def _to_decimal(value: Any, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        result = value
    else:
        try:
            result = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid {field_name}: {value!r}") from exc

    if not math.isfinite(float(result)):
        raise ValueError(f"Non-finite {field_name}: {value!r}")
    return result


def validate_candle(value: dict[str, Any] | MarketCandle) -> MarketCandle:
    if isinstance(value, MarketCandle):
        candle = value
    else:
        candle = MarketCandle(
            symbol=str(value.get("symbol", "BTC/EUR")),
            interval=str(value.get("interval", "1d")),
            timestamp=value.get("timestamp"),
            open=value.get("open"),
            high=value.get("high"),
            low=value.get("low"),
            close=value.get("close"),
            volume=value.get("volume"),
            source=value.get("source"),
            metadata=value.get("metadata", {}),
        )

    if candle.symbol != "BTC/EUR":
        raise ValueError("symbol must be BTC/EUR")
    if candle.interval != "1d":
        raise ValueError("interval must be 1d")
    if candle.source is None or not str(candle.source).strip():
        raise ValueError("source is required")
    if candle.timestamp is None:
        raise ValueError("timestamp is required")

    ts = _parse_timestamp(candle.timestamp)
    if ts.utcoffset() != UTC.utcoffset(ts):
        ts = ts.astimezone(UTC)

    open_price = _to_decimal(candle.open, "open")
    high_price = _to_decimal(candle.high, "high")
    low_price = _to_decimal(candle.low, "low")
    close_price = _to_decimal(candle.close, "close")
    volume = _to_decimal(candle.volume, "volume")

    if volume < 0:
        raise ValueError("volume must be non-negative")
    if open_price <= 0 or high_price <= 0 or low_price <= 0 or close_price <= 0:
        raise ValueError("OHLC prices must be positive")
    if high_price < max(open_price, close_price, low_price):
        raise ValueError("high must be at least max(open, close, low)")
    if low_price > min(open_price, close_price, high_price):
        raise ValueError("low must be at most min(open, close, high)")
    if ts.hour != 0 or ts.minute != 0 or ts.second != 0 or ts.microsecond != 0:
        raise ValueError("timestamp must be UTC interval-start at midnight")

    return MarketCandle(
        symbol="BTC/EUR",
        interval="1d",
        timestamp=ts,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        source=str(candle.source),
        metadata=dict(candle.metadata),
    )


def candle_to_epoch_ms(candle: MarketCandle | dict[str, Any]) -> int:
    normalized = validate_candle(candle)
    timestamp = normalized.timestamp
    assert timestamp is not None
    return int(timestamp.timestamp() * 1000)


def validate_candle_series(
    candles: list[MarketCandle | dict[str, Any]],
    as_of: datetime | None = None,
    require_fresh: bool = False,
) -> bool:
    if not candles:
        raise ValueError("candle series cannot be empty")

    normalised: list[MarketCandle] = []
    seen: set[int] = set()
    previous_ts: datetime | None = None

    for candle in candles:
        validated = validate_candle(candle)
        ts = validated.timestamp
        if ts is None:
            raise ValueError("candle timestamp is required")
        ts_ms = int(ts.timestamp() * 1000)
        if ts_ms in seen:
            raise ValueError("duplicate timestamp detected")
        seen.add(ts_ms)
        normalised.append(validated)
        if previous_ts is not None:
            delta = ts - previous_ts
            if delta != timedelta(days=1):
                raise ValueError("timestamps must be strictly daily and contiguous")
        previous_ts = ts

    if as_of is not None:
        cutoff = _parse_timestamp(as_of)
        for candle in normalised:
            if candle.timestamp + timedelta(days=1) > cutoff:
                raise ValueError(
                    f"incomplete daily candle at {candle.timestamp.isoformat()}"
                )
        if require_fresh:
            latest_expected = cutoff.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=1)
            if normalised[-1].timestamp != latest_expected:
                raise ValueError(
                    "stale candle history: latest completed UTC candle is "
                    f"{latest_expected.isoformat()}"
                )

    if len(normalised) < 2:
        raise ValueError("at least two completed candles are required for validation")

    return True


def write_candles_parquet(
    candles: list[MarketCandle | dict[str, Any]],
    output_path: str | Path,
    source: str,
    requested_start: str,
    requested_end: str,
) -> Path:
    normalized = [validate_candle(candle) for candle in candles]
    validate_candle_series(normalized)
    rows = [
        {
            "timestamp_ms": candle_to_epoch_ms(candle),
            "symbol": candle.symbol,
            "interval": candle.interval,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
            "source": candle.source,
        }
        for candle in normalized
    ]
    normalized_hash = _normalized_hash(rows)
    manifest = {
        "source": source,
        "symbol": "BTC/EUR",
        "interval": "1d",
        "timestamp_semantics": "UTC interval start in epoch milliseconds",
        "requested_start": requested_start,
        "requested_end": requested_end,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "ccxt_version": ccxt.__version__,
        "validation_schema_version": 1,
        "validation": "passed",
        "candle_count": len(rows),
        "normalized_sha256": normalized_hash,
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
    table = pa.Table.from_pylist(rows).replace_schema_metadata(
        {b"trot.manifest": manifest_bytes}
    )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return path


def _normalized_hash(rows: list[dict[str, Any]]) -> str:
    canonical_rows = [
        {
            key: format(value.normalize(), "f") if isinstance(value, Decimal) else value
            for key, value in row.items()
        }
        for row in rows
    ]
    content = json.dumps(
        canonical_rows, sort_keys=True, default=str, separators=(",", ":")
    ).encode()
    return hashlib.sha256(content).hexdigest()


def read_candles_parquet(
    input_path: str | Path,
) -> tuple[list[MarketCandle], dict[str, Any]]:
    path = Path(input_path)
    table = pq.read_table(path)
    metadata = table.schema.metadata or {}
    raw_manifest = metadata.get(b"trot.manifest")
    sidecar_path = path.with_suffix(path.suffix + ".manifest.json")
    if raw_manifest is None or not sidecar_path.is_file():
        raise ValueError("Parquet dataset is missing provenance metadata")
    manifest = json.loads(raw_manifest)
    sidecar = json.loads(sidecar_path.read_text())
    if manifest != sidecar:
        raise ValueError("Parquet provenance metadata does not match its manifest")

    candles = [
        validate_candle(
            {
                "symbol": row["symbol"],
                "interval": row["interval"],
                "timestamp": row["timestamp_ms"],
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
                "source": row["source"],
            }
        )
        for row in table.to_pylist()
    ]
    validate_candle_series(candles)
    if len(candles) != manifest.get("candle_count"):
        raise ValueError("Parquet candle count does not match provenance manifest")
    rows = [
        {
            "timestamp_ms": candle_to_epoch_ms(candle),
            "symbol": candle.symbol,
            "interval": candle.interval,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
            "source": candle.source,
        }
        for candle in candles
    ]
    if _normalized_hash(rows) != manifest.get("normalized_sha256"):
        raise ValueError("Parquet candle content does not match provenance hash")
    return candles, manifest
