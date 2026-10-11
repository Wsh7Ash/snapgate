# snapgate

**A dependency-free snapshot (golden file) test runner that scrubs nondeterministic output — timestamps, paths, UUIDs, hashes — before comparing, so golden tests stay green for the right reasons.**

## The problem

Snapshot tests are the fastest way to lock down the behaviour of a CLI, a
code generator, a formatter, or a compiler: run it, save the output, fail
whenever the output changes. In practice they rot on the first run because
the output contains the current time, a temp path, a process id, a random
UUID, or a build hash. Teams respond by deleting the snapshot tests, or by
weakening them until they assert nothing.

snapgate inverts that: nondeterministic values are normalized away *before*
comparison, and the committed snapshots contain the placeholders. What
remains in the diff is the part you actually meant to assert.

## Key features

- **Snapshot comparison** of stdout, stderr, **and** exit code per case, with
  unified diffs on mismatch.
- **Nine built-in normalizers** (timestamp, epoch, pid, UUID, duration, hex
  hash, path, CRLF, trailing whitespace) plus arbitrary custom `[[normalizer]]`
  regex rules.
- **Explicit `--update`**: snapshots only change when a human asks for it.
- **`--json`** report for CI, **`--only`** filtering, **`list`** for status.
- **`matrix` cases** for argument-driven variants (`modes[0]`, `modes[1]`, …).
- **No shell, no dependencies**: Python 3.11+ standard library only; commands
  run as argument lists with `shell=False`.
- **Never hangs**: per-case timeouts are reported as failures.

## Real output

Dogfood run of this repository's own configuration
(`python -m snapgate run`, exit 0):

```text
PASS stable-hello     0.09s
PASS noisy-output     0.20s
PASS stderr-and-exit  0.07s
PASS stdin-roundtrip  0.08s
PASS matrix-args[0]   0.07s
PASS matrix-args[1]   0.07s

6 case(s): 6 pass
```

`noisy-output` prints a live timestamp, an epoch clock, the process id, a
random UUID, a temp path, a duration, and a SHA-256 digest on every run — its
committed snapshot reads:

```text
generated <TIMESTAMP>
epoch <EPOCH>
pid <PID>
uid <UUID>
cache <PATH>
elapsed <DUR>
digest <HASH>
build <BUILD>
```

A deliberately introduced mismatch (`results/demo-diff.txt`, produced for
real and then restored):

```diff
FAIL default-report  output differs from snapshot
--- snapshots/stdout.txt
+++ actual/stdout.txt
@@ -1,4 +1,4 @@
-report for everybody (mode=fast)
+report for world (mode=fast)
 build <HASH> at <TIMESTAMP>
 run id <UUID>
 completed in <DUR>

1 case(s): 1 fail
hint: run `snapgate run --update` to accept the new output
```

## Architecture

```
snapgate.toml ─► config ─► runner.execute (subprocess, no shell)
                              │
                              ▼
                    normalize.apply (builtins → custom)
                              │
                              ▼
                    compare with snapshots/<case>/{stdout,stderr,exit}.txt
                              │
                              ▼
                    report: text diff / --json / summary
```

Modules: `config.py` (strict TOML loading), `runner.py` (execution +
comparison), `normalize.py` (normalizer chain), `report.py` (diffs, JSON),
`cli.py` (argparse, exit codes). See `docs/ARCHITECTURE.md`.

## Requirements

- Python **3.11+** (`tomllib`); developed and tested on Python 3.14, Windows.
- Nothing else — no pip packages, no network.

## Installation

No installation needed (this is the primary route):

```shell
# PowerShell, from the repository root
$env:PYTHONPATH = "src"
python -m snapgate --version
```

```shell
# bash
PYTHONPATH=src python -m snapgate --version
```

Optional, inside a virtualenv:

```shell
pip install -e .
snapgate --version
```

## Quick start

```shell
$env:PYTHONPATH = "src"                     # PowerShell
python -m snapgate run --update             # 1. create the baseline
python -m snapgate run                       # 2. regression check, exit 0/1
```

## Usage

`snapgate.toml`:

```toml
[run]
snapshot_dir = "snapshots"
timeout = 10

[[case]]
name = "default-report"
command = ["python", "sample_cli.py"]

[[case]]
name = "modes"
command = ["python", "sample_cli.py", "--mode"]
matrix = [["fast"], ["safe"]]

[[normalizer]]
name = "build-id"
pattern = "v\\d+\\.\\d+\\.\\d+"
replace = "v<BUILD>"
```

Commands:

| Command | Purpose |
|---|---|
| `snapgate run` | execute and compare |
| `snapgate run --update` | accept current output as the snapshot |
| `snapgate run --json` | JSON report for CI |
| `snapgate run --only NAME` | filter cases |
| `snapgate list` | case + snapshot status |
| `snapgate run --list-normalizers` | show the effective chain |

Exit codes: `0` all pass · `1` mismatch/missing/timeout/error · `2` config or
usage error.

Full reference: `docs/USAGE.md`. Runnable example: `examples/snapgate.toml`.

## Configuration

`[run]` supplies defaults (`snapshot_dir`, `timeout`, `command`, `stdin`,
`cwd`, `env`, `use_builtins`); each `[[case]]` may override any of them and
add `matrix`. Unknown keys are hard errors — a typo never silently disables a
check. Custom `[[normalizer]]` rules run after the built-ins.

## Testing

```shell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v     # 37 tests
python -m snapgate run                      # dogfood: 6 cases
python -m snapgate run -c examples/snapgate.toml   # example: 3 cases
```

CI (`.github/workflows/ci.yml`) runs the unit tests and both snapshot suites
on Ubuntu and Windows, Python 3.11 and 3.13.

## Project structure

```text
snapgate/
├── src/snapgate/         cli, config, runner, normalize, report
├── tests/                unittest suite (incl. dogfood integration test)
├── snapgate.toml         this repo's own cases
├── snapshots/            committed dogfood snapshots
├── examples/             sample CLI + example config + its snapshots
├── docs/                 PROJECT_SPEC, ARCHITECTURE, USAGE
├── results/              real demo run, demo diff, JSON report
├── README.md  RESULTS.md  CHANGELOG.md  CONTRIBUTING.md  LICENSE
└── .github/workflows/ci.yml
```

## Limitations

- Normalizers are regex-based and **can over-match**; review what your rules
  scrub before trusting a green run.
- Comparison is line-based: a structural change to a large output produces a
  large diff.
- Snapshots are committed text — do not let real secrets reach them (run
  `snapgate` only on output you are willing to publish).
- No parallel execution, no baseline branching, no HTML report (see roadmap).

## Roadmap

- Parallel case execution with ordered reporting.
- `--since BRANCH` mode that only runs cases whose snapshots changed.
- Optional JUnit XML output alongside `--json`.
- A `snapgate init` scaffolder.

## Security notes

`snapgate` executes **the commands you configure, on your machine**. Only run
configurations you trust; never execute an untrusted `snapgate.toml`. Commands
are invoked without a shell. The tool itself performs no network I/O.

## License

MIT — see [LICENSE](LICENSE).
