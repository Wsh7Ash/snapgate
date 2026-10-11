"""Result reporting: unified diffs and JSON output."""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass, field

__all__ = ["CaseResult", "build_diff", "to_json", "summary_line"]


@dataclass
class CaseResult:
    name: str
    status: str  # pass | fail | missing | created | updated | unchanged | timeout | error
    reason: str = ""
    diffs: list[str] = field(default_factory=list)


def build_diff(label: str, expected: str, actual: str) -> str:
    diff = difflib.unified_diff(
        expected.splitlines(keepends=True),
        actual.splitlines(keepends=True),
        fromfile=f"snapshots/{label}",
        tofile=f"actual/{label}",
    )
    return "".join(diff)


def to_json(results: list[CaseResult]) -> str:
    payload = [
        {"name": r.name, "status": r.status, "reason": r.reason} for r in results
    ]
    return json.dumps(payload, indent=2, sort_keys=True)


def summary_line(results: list[CaseResult]) -> str:
    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    order = ["pass", "fail", "missing", "timeout", "error", "created", "updated", "unchanged"]
    parts = [f"{counts[s]} {s}" for s in order if s in counts]
    return f"{len(results)} case(s): " + (", ".join(parts) if parts else "no results")
