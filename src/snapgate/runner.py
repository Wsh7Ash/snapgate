"""Execute configured commands and compare against snapshots."""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from snapgate.config import Case, Config
from snapgate.normalize import Normalizer, apply
from snapgate.report import CaseResult, build_diff

__all__ = ["ExecResult", "execute", "snapshot_files", "check_case", "ordered_normalizers"]


@dataclass
class ExecResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration: float = 0.0
    timed_out: bool = False
    failure: str | None = None


def ordered_normalizers(config: Config) -> list[Normalizer]:
    from snapgate.normalize import builtins

    return (builtins() if config.use_builtins else []) + list(config.normalizers)


def _decode(data: object) -> str:
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return str(data)


def execute(case: Case, config: Config) -> ExecResult:
    """Run one case's command without a shell."""
    cwd = case.cwd or str(config.base_dir)
    if not Path(cwd).is_absolute():
        cwd = str(config.base_dir / cwd)
    env = dict(os.environ)
    if case.env:
        env.update(case.env)

    started = time.perf_counter()
    try:
        proc = subprocess.run(
            case.command,
            input=case.stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=case.timeout,
            cwd=cwd,
            env=env,
            shell=False,
        )
    except FileNotFoundError:
        return ExecResult(failure=f"command not found: {case.command[0]}")
    except subprocess.TimeoutExpired as exc:
        return ExecResult(
            stdout=_decode(exc.stdout),
            stderr=_decode(exc.stderr),
            exit_code=-1,
            duration=time.perf_counter() - started,
            timed_out=True,
            failure=f"timed out after {case.timeout:g}s",
        )
    except OSError as exc:
        return ExecResult(failure=f"could not execute command: {exc}")

    return ExecResult(
        stdout=proc.stdout,
        stderr=proc.stderr,
        exit_code=proc.returncode,
        duration=time.perf_counter() - started,
    )


def snapshot_files(case: Case, config: Config) -> dict[str, Path]:
    root = config.snapshot_root
    if case.snapshot_dir:
        sub = Path(case.snapshot_dir)
        root = sub if sub.is_absolute() else config.base_dir / sub
    case_dir = root / case.name
    return {
        "stdout": case_dir / "stdout.txt",
        "stderr": case_dir / "stderr.txt",
        "exit": case_dir / "exit.txt",
    }


def check_case(case: Case, config: Config, update: bool = False) -> CaseResult:
    """Run one case and compare (or refresh) its snapshot."""
    normalizers = ordered_normalizers(config)
    result = execute(case, config)

    if result.failure and not result.timed_out:
        return CaseResult(name=case.name, status="error", reason=result.failure)

    actual = {
        "stdout": apply(result.stdout, normalizers),
        "stderr": apply(result.stderr, normalizers),
        "exit": str(result.exit_code),
    }

    if result.timed_out:
        files = snapshot_files(case, config)
        if update:
            _write(files, actual)
            return CaseResult(name=case.name, status="updated", reason=result.failure)
        diffs: list[str] = []
        if files["exit"].is_file():
            expected_exit = files["exit"].read_text(encoding="utf-8")
            if expected_exit.strip() != actual["exit"]:
                diffs.append(
                    build_diff("exit.txt", expected_exit, actual["exit"])
                )
        reason = result.failure
        if diffs:
            reason = f"{reason}; exit code mismatch"
        return CaseResult(name=case.name, status="timeout", reason=reason, diffs=diffs)

    files = snapshot_files(case, config)
    missing = [key for key, path in files.items() if not path.is_file()]

    if update:
        changed = _write(files, actual)
        if missing:
            return CaseResult(
                name=case.name,
                status="created",
                reason=f"created {len(missing)} snapshot file(s)",
            )
        if changed:
            return CaseResult(name=case.name, status="updated", reason="snapshot updated")
        return CaseResult(name=case.name, status="unchanged", reason="snapshot already current")

    if missing:
        names = ", ".join(f"{case.name}/{key}.txt" for key in missing)
        return CaseResult(
            name=case.name,
            status="missing",
            reason=f"snapshot missing ({names}); run with --update to create it",
        )

    diffs = []
    expected_exit = files["exit"].read_text(encoding="utf-8")
    if expected_exit != actual["exit"]:
        diffs.append(build_diff("exit.txt", expected_exit, actual["exit"]))
    for key in ("stdout", "stderr"):
        expected = files[key].read_text(encoding="utf-8")
        if expected != actual[key]:
            diffs.append(build_diff(f"{key}.txt", expected, actual[key]))

    if diffs:
        streams = []
        for key in ("stdout", "stderr", "exit"):
            if f"--- snapshots/{case.name}/{key}.txt" in "".join(diffs):
                streams.append(key)
        detail = ", ".join(streams) if streams else "output"
        return CaseResult(
            name=case.name,
            status="fail",
            reason=f"{detail} differs from snapshot",
            diffs=diffs,
        )
    return CaseResult(name=case.name, status="pass", reason=f"{result.duration:.2f}s")


def _write(files: dict[str, Path], actual: dict[str, str], only: list[str] | None = None) -> bool:
    changed = False
    for key, path in files.items():
        if only is not None and key not in only:
            continue
        text = actual[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        old = path.read_text(encoding="utf-8") if path.is_file() else None
        if old != text:
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            changed = True
    return changed
