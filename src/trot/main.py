from __future__ import annotations

import argparse
import logging
import sys

from trot.config import Settings

logger = logging.getLogger("trot")


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, str(level_name).upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Trot - BTC/EUR research and paper trading"
    )
    parser.add_argument(
        "--version", action="store_true", help="Print installed version and exit"
    )

    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = False

    download_parser = subparsers.add_parser("download", help="Download market data")
    download_parser.add_argument("--start", dest="start", required=True)
    download_parser.add_argument("--end", dest="end", required=True)

    for name in ("backtest", "paper", "status"):
        subparsers.add_parser(name, help=f"Run the {name} workflow")

    data_parser = subparsers.add_parser("data", help="Data management commands")
    data_subparsers = data_parser.add_subparsers(dest="data_command")
    data_subparsers.required = False
    data_subparsers.add_parser("download", help="Download market data")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print("trot 0.1.0")
        return 0

    settings = Settings()
    _configure_logging(settings.log_level)

    if args.command is None:
        parser.print_help(sys.stdout)
        return 0

    if args.command == "download":
        try:
            from datetime import datetime

            start = datetime.fromisoformat(args.start)
            end = datetime.fromisoformat(args.end)
        except ValueError:
            print("invalid date range provided", file=sys.stderr)
            return 1
        if end < start:
            print("invalid date range: end must be after start", file=sys.stderr)
            return 1
        print(
            "download workflow requires upstream market data integration",
            file=sys.stderr,
        )
        return 1

    if args.command == "data":
        print("data download is not implemented in this phase", file=sys.stderr)
        return 1

    logger.info("Starting Trot %s command", args.command)
    print(f"{args.command} is not implemented in this phase.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
