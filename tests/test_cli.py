from __future__ import annotations

from trot.main import main


def test_cli_download_command_returns_non_zero_for_invalid_range():
    exit_code = main(["download", "--start", "2024-02-01", "--end", "2024-01-01"])
    assert exit_code != 0


def test_cli_requires_data_command_without_network():
    exit_code = main(["data", "download"])
    assert exit_code != 0
