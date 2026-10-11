"""Ordered output normalizers.

Built-in normalizers scrub the values that make golden files rot:
timestamps, epoch seconds, UUIDs, durations, hex hashes, absolute paths,
CRLF line endings, and trailing whitespace. Custom normalizers from
``snapgate.toml`` run after the built-ins.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["Normalizer", "builtins", "apply", "compile_pattern", "NormalizeError"]


class NormalizeError(Exception):
    """Raised when a normalizer pattern is not a valid regular expression."""


@dataclass(frozen=True)
class Normalizer:
    name: str
    pattern: str
    replace: str

    def compiled(self) -> re.Pattern[str]:
        return compile_pattern(self)


def compile_pattern(norm: Normalizer) -> re.Pattern[str]:
    try:
        return re.compile(norm.pattern, re.MULTILINE)
    except re.error as exc:  # pragma: no cover - exercised via config tests
        raise NormalizeError(f"normalizer {norm.name!r}: invalid regex: {exc}") from exc


def builtins() -> list[Normalizer]:
    """Built-in normalizers, in their fixed application order."""
    return [
        Normalizer("crlf", r"\r\n", "\n"),
        Normalizer("iso-timestamp", r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?", "<TIMESTAMP>"),
        Normalizer("epoch", r"(?<![\w.])\d{9,13}(?!\.\d)(?![\w.])", "<EPOCH>"),
        Normalizer("pid", r"(\bpid[ =])\d+", r"\1<PID>"),
        Normalizer("uuid", r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "<UUID>"),
        Normalizer("duration", r"(?<![\w.])(?:\d+(?:\.\d+)?)(?:ms|us|µs|ns|s)\b", "<DUR>"),
        Normalizer("hex-hash", r"(?<![\w])\b[0-9a-fA-F]{12,}\b", "<HASH>"),
        Normalizer("path", r"(?:[A-Za-z]:[\\/][^\s\"']+|/(?:[\w.@+-]+/)+[\w.@+-]+)", "<PATH>"),
        Normalizer("trailing-ws", r"[ \t]+$", "", ),
    ]


def apply(text: str, normalizers: list[Normalizer]) -> str:
    """Apply ``normalizers`` in order, returning the normalized text."""
    for norm in normalizers:
        text = compile_pattern(norm).sub(norm.replace, text)
    return text
