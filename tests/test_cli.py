from __future__ import annotations

import json
from datetime import UTC, datetime

import pyarrow.parquet as pq

from trot.data import write_candles_parquet
from trot.main import main


def test_backtest_cli_accepts_hourly_interval(valid_candles, tmp_path, capsys):
    dataset = tmp_path / "hourly-history.parquet"
    hourly = [
        {**candle.__dict__, "interval": "1h", "timestamp": candle.timestamp.replace(minute=0, second=0, microsecond=0)}
        for candle in valid_candles[:10]
    ]
    write_candles_parquet(
        [
            type(valid_candles[0])(
                symbol=candle["symbol"],
                interval="1h",
                timestamp=candle["timestamp"],
                open=candle["open"],
                high=candle["high"],
                low=candle["low"],
                close=candle["close"],
                volume=candle["volume"],
                source=candle["source"],
            )
            for candle in hourly
        ],
        dataset,
        "kraken",
        hourly[0]["timestamp"].date().isoformat(),
        hourly[-1]["timestamp"].date().isoformat(),
    )

    exit_code = main(["backtest", "--data", str(dataset), "--interval", "1h"])

    assert exit_code == 0
    assert "simulated research" in capsys.readouterr().out


def test_cli_download_command_accepts_hourly_interval(monkeypatch, tmp_path):
    observed = {}
    start_ms = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)
    raw_candles = [
        [start_ms, 100, 102, 99, 101, 1],
        [start_ms + 3_600_000, 101, 103, 100, 102, 1],
    ]

    def fake_fetch(symbol, timeframe, start_ms, end_ms, source):
        observed["timeframe"] = timeframe
        return raw_candles

    monkeypatch.setattr("trot.main.fetch_ohlcv", fake_fetch)

    exit_code = main(
        [
            "download",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-03",
            "--interval",
            "1h",
            "--output",
            str(tmp_path / "hourly.parquet"),
        ]
    )

    assert exit_code == 0
    assert observed["timeframe"] == "1h"


def test_hourly_download_filters_incomplete_bar_and_writes_interval_manifest(
    monkeypatch, tmp_path, capsys
):
    fixed_now = datetime(2024, 1, 1, 2, 30, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr("trot.main.datetime", FrozenDateTime)
    start_ms = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)
    raw_candles = [
        [start_ms + hour * 3_600_000, 100, 102, 99, 101, 1]
        for hour in range(3)
    ]
    fetch_calls = []

    def fake_fetch(symbol, timeframe, start_ms, end_ms, source):
        fetch_calls.append((timeframe, start_ms, end_ms))
        return raw_candles

    monkeypatch.setattr("trot.main.fetch_ohlcv", fake_fetch)
    output_path = tmp_path / "hourly.parquet"

    exit_code = main(
        [
            "data",
            "download",
            "--since",
            "2024-01-01",
            "--until",
            "2024-01-01",
            "--interval",
            "1h",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert fetch_calls == [("1h", start_ms, start_ms + 86_400_000 - 1)]
    assert pq.read_table(output_path).num_rows == 2
    manifest_path = output_path.with_suffix(output_path.suffix + ".manifest.json")
    manifest = json.loads(manifest_path.read_text())
    assert manifest["interval"] == "1h"
    assert manifest["candle_count"] == 2
    assert "1h" in capsys.readouterr().out


def test_hourly_download_reports_no_completed_candles_without_writing(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr("trot.main.fetch_ohlcv", lambda **kwargs: [])
    output_path = tmp_path / "empty-hourly.parquet"

    exit_code = main(
        [
            "data",
            "download",
            "--since",
            "2024-01-01",
            "--until",
            "2024-01-01",
            "--interval",
            "1h",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code != 0
    assert "no completed 1h candles" in capsys.readouterr().err.lower()
    assert not output_path.exists()
    assert not output_path.with_suffix(output_path.suffix + ".manifest.json").exists()


def test_cli_download_command_returns_non_zero_for_invalid_range():
    exit_code = main(["download", "--start", "2024-02-01", "--end", "2024-01-01"])
    assert exit_code != 0


def test_cli_requires_data_command_without_network():
    exit_code = main(["data", "download"])
    assert exit_code != 0


def test_data_download_wires_exchange_validation_and_output(
    monkeypatch, tmp_path, capsys
):
    start_ms = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)
    raw_candles = [
        [start_ms + day * 86_400_000, 100, 102, 99, 101, 1] for day in range(3)
    ]
    fetch_calls = []

    def fake_fetch(symbol, timeframe, start_ms, end_ms, source):
        fetch_calls.append((symbol, timeframe, start_ms, end_ms, source))
        return raw_candles

    monkeypatch.setattr("trot.main.fetch_ohlcv", fake_fetch)

    output_path = tmp_path / "btc-eur.parquet"
    exit_code = main(
        [
            "data",
            "download",
            "--since",
            "2024-01-01",
            "--until",
            "2024-01-03",
            "--exchange",
            "kraken",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert fetch_calls == [
        (
            "BTC/EUR",
            "1d",
            start_ms,
            start_ms + 3 * 86_400_000 - 1,
            "kraken",
        )
    ]
    assert pq.read_table(output_path).num_rows == 3
    manifest_path = output_path.with_suffix(output_path.suffix + ".manifest.json")
    manifest = json.loads(manifest_path.read_text())
    assert manifest["source"] == "kraken"
    assert manifest["requested_start"] == "2024-01-01"
    assert manifest["requested_end"] == "2024-01-03"
    assert "3 candles" in capsys.readouterr().out


def test_data_download_rejects_gaps_without_writing(monkeypatch, tmp_path, capsys):
    first_ms = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)
    raw_candles = [
        [first_ms, 100, 102, 99, 101, 1],
        [first_ms + 2 * 86_400_000, 101, 103, 100, 102, 1],
    ]
    write_calls = []
    monkeypatch.setattr("trot.main.fetch_ohlcv", lambda **kwargs: raw_candles)
    monkeypatch.setattr(
        "trot.main.write_candles_parquet", lambda *args: write_calls.append(args)
    )

    exit_code = main(
        [
            "data",
            "download",
            "--since",
            "2024-01-01",
            "--until",
            "2024-01-03",
            "--output",
            str(tmp_path / "btc-eur.parquet"),
        ]
    )

    assert exit_code != 0
    assert not write_calls
    assert "contiguous" in capsys.readouterr().err


def test_backtest_cli_loads_parquet_and_reports_simulated_metrics(
    valid_candles, tmp_path, capsys
):
    dataset = tmp_path / "history.parquet"
    write_candles_parquet(
        valid_candles,
        dataset,
        "kraken",
        valid_candles[0].timestamp.date().isoformat(),
        valid_candles[-1].timestamp.date().isoformat(),
    )

    exit_code = main(["backtest", "--data", str(dataset)])

    assert exit_code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["label"] == "simulated research"
    assert "btc_buy_and_hold" in result["benchmarks"]
    assert set(result["cost_stress"]) == {"1x", "1.5x", "2x"}
