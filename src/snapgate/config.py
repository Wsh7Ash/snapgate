"""Load and validate ``snapgate.toml``."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from snapgate.normalize import Normalizer

__all__ = ["ConfigError", "Case", "Config", "load"]

DEFAULT_TIMEOUT = 30.0
DEFAULT_SNAPSHOT_DIR = "snapshots"

_TOP_KEYS = {"run", "case", "normalizer"}
_RUN_KEYS = {"snapshot_dir", "command", "stdin", "cwd", "timeout", "env", "use_builtins"}
_CASE_KEYS = {"name", "command", "matrix", "stdin", "cwd", "timeout", "env", "snapshot_dir"}
_NORM_KEYS = {"name", "pattern", "replace"}


class ConfigError(Exception):
    """Invalid configuration. Maps to exit code 2."""


@dataclass
class Case:
    name: str
    command: list[str]
    stdin: str | None = None
    cwd: str | None = None
    timeout: float = DEFAULT_TIMEOUT
    env: dict[str, str] | None = None
    snapshot_dir: str | None = None


@dataclass
class Config:
    base_dir: Path
    snapshot_dir: str = DEFAULT_SNAPSHOT_DIR
    use_builtins: bool = True
    normalizers: list[Normalizer] = field(default_factory=list)
    cases: list[Case] = field(default_factory=list)

    @property
    def snapshot_root(self) -> Path:
        root = Path(self.snapshot_dir)
        return root if root.is_absolute() else self.base_dir / root


def _check_keys(table: dict[str, Any], allowed: set[str], where: str) -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise ConfigError(f"{where}: unknown key(s): {', '.join(unknown)}")


def _str_list(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"{where}: expected a list of strings")
    if not value:
        raise ConfigError(f"{where}: must not be empty")
    return list(value)


def _opt_str(table: dict[str, Any], key: str, where: str) -> str | None:
    value = table.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigError(f"{where}.{key}: expected a string")
    return value


def _env(table: dict[str, Any], where: str) -> dict[str, str] | None:
    value = table.get("env")
    if value is None:
        return None
    if not isinstance(value, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    ):
        raise ConfigError(f"{where}.env: expected a table of string values")
    return dict(value)


def _timeout(table: dict[str, Any], where: str, default: float) -> float:
    value = table.get("timeout", default)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"{where}.timeout: expected a positive number")
    return float(value)


def _cases(raw: Any, run: dict[str, Any]) -> list[Case]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ConfigError("'case' must be an array of tables")

    run_command = run.get("command")
    run_stdin = run.get("stdin")
    run_cwd = run.get("cwd")
    run_timeout = _timeout(run, "run", DEFAULT_TIMEOUT)
    run_env = _env(run, "run")

    cases: list[Case] = []
    seen: set[str] = set()
    for index, entry in enumerate(raw):
        where = f"case[{index}]"
        if not isinstance(entry, dict):
            raise ConfigError(f"{where}: expected a table")
        _check_keys(entry, _CASE_KEYS, where)

        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise ConfigError(f"{where}.name: expected a non-empty string")

        command = entry.get("command", run_command)
        if command is None:
            raise ConfigError(f"{where}: no command (case and run both lack 'command')")
        command = _str_list(command, f"{where}.command")

        stdin = entry.get("stdin", run_stdin)
        if stdin is not None and not isinstance(stdin, str):
            raise ConfigError(f"{where}.stdin: expected a string")
        cwd = _opt_str(entry, "cwd", where) or run_cwd
        env = _env(entry, where) or run_env
        timeout = _timeout(entry, where, run_timeout)
        snap_sub = _opt_str(entry, "snapshot_dir", where)

        matrix = entry.get("matrix")
        if matrix is None:
            variants: list[list[str]] = [[]]
        else:
            if not isinstance(matrix, list) or not matrix:
                raise ConfigError(f"{where}.matrix: expected a non-empty array of argument lists")
            variants = [_str_list(v, f"{where}.matrix[{i}]") for i, v in enumerate(matrix)]

        for i, args in enumerate(variants):
            case_name = name if len(variants) == 1 else f"{name}[{i}]"
            if case_name in seen:
                raise ConfigError(f"duplicate case name: {case_name!r}")
            seen.add(case_name)
            cases.append(
                Case(
                    name=case_name,
                    command=command + args,
                    stdin=stdin,
                    cwd=cwd,
                    timeout=timeout,
                    env=env,
                    snapshot_dir=snap_sub,
                )
            )
    return cases


def _normalizers(raw: Any) -> list[Normalizer]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ConfigError("'normalizer' must be an array of tables")
    out: list[Normalizer] = []
    for index, entry in enumerate(raw):
        where = f"normalizer[{index}]"
        if not isinstance(entry, dict):
            raise ConfigError(f"{where}: expected a table")
        _check_keys(entry, _NORM_KEYS, where)
        name = entry.get("name")
        pattern = entry.get("pattern")
        replace = entry.get("replace")
        if not isinstance(name, str) or not name:
            raise ConfigError(f"{where}.name: expected a non-empty string")
        if not isinstance(pattern, str) or not pattern:
            raise ConfigError(f"{where}.pattern: expected a non-empty regex string")
        if not isinstance(replace, str):
            raise ConfigError(f"{where}.replace: expected a string")
        out.append(Normalizer(name, pattern, replace))
    return out


def load(path: str | Path) -> Config:
    """Load ``snapgate.toml`` from ``path``; raise :class:`ConfigError` on problems."""
    cfg_path = Path(path)
    if not cfg_path.is_file():
        raise ConfigError(f"config file not found: {cfg_path}")
    try:
        with cfg_path.open("rb") as handle:
            raw = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {cfg_path}: {exc}") from exc
    if not isinstance(raw, dict):  # pragma: no cover - tomllib always returns dict
        raise ConfigError("config root must be a table")

    _check_keys(raw, _TOP_KEYS, "config")

    run = raw.get("run", {})
    if not isinstance(run, dict):
        raise ConfigError("'run' must be a table")
    _check_keys(run, _RUN_KEYS, "run")

    snapshot_dir = run.get("snapshot_dir", DEFAULT_SNAPSHOT_DIR)
    if not isinstance(snapshot_dir, str) or not snapshot_dir:
        raise ConfigError("run.snapshot_dir: expected a non-empty string")

    use_builtins = run.get("use_builtins", True)
    if not isinstance(use_builtins, bool):
        raise ConfigError("run.use_builtins: expected a boolean")

    if "command" in run:
        _str_list(run["command"], "run.command")
    if "stdin" in run and run["stdin"] is not None and not isinstance(run["stdin"], str):
        raise ConfigError("run.stdin: expected a string")
    _opt_str(run, "cwd", "run")
    _env(run, "run")
    _timeout(run, "run", DEFAULT_TIMEOUT)

    config = Config(
        base_dir=cfg_path.parent.resolve(),
        snapshot_dir=snapshot_dir,
        use_builtins=use_builtins,
        normalizers=_normalizers(raw.get("normalizer")),
        cases=_cases(raw.get("case"), run),
    )
    if not config.cases:
        raise ConfigError("config defines no cases")
    return config
