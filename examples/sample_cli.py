"""Tiny sample CLI used by examples/snapgate.toml.

Usage: python sample_cli.py [--mode fast|safe] [name]

Prints a report containing values that change between runs so the
normalizer chain has something real to scrub.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import sys
import uuid


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="sample report generator")
    parser.add_argument("--mode", choices=["fast", "safe"], default="fast")
    parser.add_argument("name", nargs="?", default="world")
    args = parser.parse_args(argv)

    if args.name == "boom":
        print("error: requested failure", file=sys.stderr)
        return 3

    build = hashlib.sha256(b"sample-cli").hexdigest()[:12]
    print(f"report for {args.name} (mode={args.mode})")
    print(f"build {build} at {datetime.datetime(2026, 10, 10, 9, 30, 0).isoformat()}Z")
    print(f"run id {uuid.uuid4()}")
    print("completed in 12.50ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
