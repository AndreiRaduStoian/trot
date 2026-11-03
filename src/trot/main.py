from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trot - BTC/EUR research and paper trading")
    parser.add_argument("--version", action="store_true", help="Print installed version and exit")
    args = parser.parse_args(argv)

    if args.version:
        print("trot 0.1.0")
        return 0

    print("Trot research mode is initialized; no live execution routes are enabled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
