"""Command line interface for snapgate."""

from __future__ import annotations

import argparse
import sys

from snapgate import __version__
from snapgate.config import ConfigError, load
from snapgate.report import summary_line, to_json
from snapgate.runner import check_case, ordered_normalizers, snapshot_files

EXIT_OK = 0
EXIT_MISMATCH = 1
EXIT_USAGE = 2

_FAILING = {"fail", "missing", "timeout", "error"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="snapgate",
        description="Snapshot (golden file) test runner with output normalizers.",
    )
    parser.add_argument("--version", action="version", version=f"snapgate {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="execute cases and compare against snapshots")
    run.add_argument("-c", "--config", default="snapgate.toml", help="config file (default: snapgate.toml)")
    run.add_argument("--update", action="store_true", help="write snapshots from actual output")
    run.add_argument("--json", action="store_true", help="emit a JSON report on stdout")
    run.add_argument("--only", metavar="SUBSTRING", help="run cases whose name contains SUBSTRING")
    run.add_argument("--list-normalizers", action="store_true", help="print the ordered normalizer chain and exit")

    lst = sub.add_parser("list", help="list cases and snapshot status")
    lst.add_argument("-c", "--config", default="snapgate.toml", help="config file (default: snapgate.toml)")
    return parser


def _select(cases, only: str | None):
    if not only:
        return cases
    return [c for c in cases if only in c.name]


def _cmd_run(args: argparse.Namespace) -> int:
    config = load(args.config)

    if args.list_normalizers:
        for i, norm in enumerate(ordered_normalizers(config), 1):
            print(f"{i:2d}. {norm.name:<16} {norm.pattern} -> {norm.replace!r}")
        return EXIT_OK

    cases = _select(config.cases, args.only)
    if not cases:
        print(f"snapgate: no cases match --only {args.only!r}", file=sys.stderr)
        return EXIT_USAGE

    results = [check_case(case, config, update=args.update) for case in cases]

    failing = sum(1 for r in results if r.status in _FAILING)
    if args.json:
        print(to_json(results))
    else:
        width = max(len(r.name) for r in results)
        for r in results:
            marker = {
                "pass": "PASS ",
                "fail": "FAIL ",
                "missing": "MISS ",
                "timeout": "TIME ",
                "error": "ERR  ",
                "created": "NEW  ",
                "updated": "WRITE",
                "unchanged": "OK   ",
            }.get(r.status, "?    ")
            detail = f"  {r.reason}" if r.reason else ""
            print(f"{marker}{r.name.ljust(width)}{detail}")
            if r.status in _FAILING and not args.update:
                for diff in r.diffs:
                    print(diff.rstrip("\n"))
        print()
        print(summary_line(results))
        if failing and not args.update:
            print("hint: run `snapgate run --update` to accept the new output")

    if args.update:
        return EXIT_MISMATCH if any(r.status == "error" for r in results) else EXIT_OK
    return EXIT_MISMATCH if failing else EXIT_OK


def _cmd_list(args: argparse.Namespace) -> int:
    config = load(args.config)
    width = max(len(c.name) for c in config.cases) if config.cases else 0
    for case in config.cases:
        files = snapshot_files(case, config)
        present = sum(1 for p in files.values() if p.is_file())
        status = "ready" if present == len(files) else f"missing {len(files) - present}/{len(files)}"
        print(f"{case.name.ljust(width)}  {status}")
        print(f"{' ' * width}  $ {' '.join(case.command)}")
    print()
    print(f"{len(config.cases)} case(s), normalizers: {len(ordered_normalizers(config))}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            return _cmd_run(args)
        if args.command == "list":
            return _cmd_list(args)
        parser.error(f"unknown command: {args.command}")
    except ConfigError as exc:
        print(f"snapgate: config error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    return EXIT_USAGE
