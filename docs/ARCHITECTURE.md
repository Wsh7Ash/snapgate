# Architecture

## Pipeline

```
snapgate.toml ──► config.load ──► Config { cases, normalizers, snapshot_root }
                                        │
                                        ▼
                              runner.check_case (per case)
                                        │
                     ┌──────────────────┼──────────────────┐
                     ▼                  ▼                  ▼
               runner.execute     normalize.apply    snapshot files
               (subprocess,       (builtins then     (stdout.txt,
                no shell,          custom rules)      stderr.txt,
                timeout)                              exit.txt)
                     │                  │                  │
                     └──────────► compare ──► report.CaseResult
                                                │
                                     text diff / JSON / summary
```

## Modules

| Module | Responsibility |
|---|---|
| `snapgate/config.py` | `tomllib` load, strict key validation (unknown keys are errors), defaults, matrix expansion, duplicate-name detection. Raises `ConfigError` → exit code 2. |
| `snapgate/runner.py` | Executes one case with `subprocess.run(..., shell=False)` capturing stdout/stderr/exit code; applies the ordered normalizer chain; compares against (or writes) snapshot files; maps timeouts and missing binaries to results instead of crashing. |
| `snapgate/normalize.py` | The `Normalizer` value object, the fixed built-in chain, and `apply()`. Patterns compile with `re.MULTILINE` so line-anchored rules (trailing whitespace) work per line. |
| `snapgate/report.py` | `CaseResult`, `difflib` unified diff construction, JSON serialization, summary line. |
| `snapgate/cli.py` | argparse subcommands `run` / `list`, flag handling, exit-code policy. |

## Design decisions

**Compare normalized output, store normalized output.**
Snapshots on disk are already normalized (`build <HASH> at <TIMESTAMP>`), so a
diff a human reads is a diff of *meaningful* lines only. The alternative —
storing raw output and normalizing both sides at compare time — hides from the
user what is actually committed.

**Ordered, single-pass-per-rule normalizers.**
Rules run in a fixed order: CRLF → ISO timestamp → epoch → pid → UUID →
duration → hex hash → path → trailing whitespace → custom rules. Ordering is
observable and testable; custom rules run last so a project can scrub what the
built-ins deliberately leave alone.

**No shell.**
Commands are argument lists passed to `subprocess.run` with `shell=False`.
This removes quoting bugs and shell injection from the trust boundary.

**Three files per case.**
`stdout.txt`, `stderr.txt`, and `exit.txt` are compared independently so a
failure report shows which channel changed. Exit codes are stored as plain
text for readable diffs.

**Exit-code contract.**

| Code | Meaning |
|---|---|
| 0 | all cases passed (or snapshots were written with `--update`) |
| 1 | at least one mismatch, missing snapshot, timeout, or execution error |
| 2 | configuration or usage error |

## Failure handling

| Condition | Result status | Behaviour |
|---|---|---|
| Output differs | `fail` | unified diff printed, exit 1 |
| Snapshot absent | `missing` | instructions to `--update`, exit 1 |
| Command exceeds `timeout` | `timeout` | reported with reason; never hangs the suite |
| Binary missing / exec error | `error` | reported with reason, exit 1 |
| Invalid config | — | `config error: ...` on stderr, exit 2 |
