from __future__ import annotations

import json
from datetime import UTC, datetime

import pyarrow.parquet as pq

from trot.data import write_candles_parquet
from trot.main import main


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
