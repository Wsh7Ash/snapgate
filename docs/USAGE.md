# Usage

All examples run from the repository root.

```shell
# PowerShell
$env:PYTHONPATH = "src"
python -m snapgate run
```

```shell
# bash
PYTHONPATH=src python -m snapgate run
```

After `pip install -e .` in a virtualenv, the same commands work as
`snapgate run`.

## Commands

| Command | Purpose |
|---|---|
| `snapgate run` | execute cases, compare with snapshots |
| `snapgate run --update` | write snapshots from actual output |
| `snapgate run --json` | print a JSON report instead of text |
| `snapgate run --only SUB` | run cases whose name contains `SUB` |
| `snapgate run --list-normalizers` | print the ordered normalizer chain |
| `snapgate list` | show cases and snapshot completeness |
| `snapgate -c PATH` | use a config other than `snapgate.toml` |

## Configuration reference

```toml
[run]                          # defaults inherited by every case
snapshot_dir = "snapshots"     # relative to the config file
timeout = 30                   # seconds, per case
use_builtins = true            # include the built-in normalizers
command = ["python", "-c", "print('default')"]
stdin = "optional default stdin"
cwd = "optional working directory"
[run.env]
MODE = "ci"

[[case]]
name = "greet"                 # required, unique
command = ["python", "cli.py", "hi"]   # falls back to [run].command
stdin = "input text"
cwd = "subdir"
timeout = 5
env = { EXTRA = "1" }
snapshot_dir = "special/greet" # optional override

[[case]]                       # matrix: one entry per argument list
name = "modes"
command = ["python", "cli.py", "--mode"]
matrix = [["fast"], ["safe"]]  # -> modes[0], modes[1]

[[normalizer]]                 # custom rule, runs after the built-ins
name = "build-id"
pattern = "build-\\d+"
replace = "build-<ID>"
```

Unknown keys anywhere are configuration errors (exit 2) — a typo should never
silently disable a check.

## Built-in normalizers (in order)

| # | Name | Scrubs | Becomes |
|---|---|---|---|
| 1 | `crlf` | `\r\n` | `\n` |
| 2 | `iso-timestamp` | `2026-10-10T12:34:56Z`, `2026-10-10 12:34:56.789+02:00` | `<TIMESTAMP>` |
| 3 | `epoch` | 9–13 digit epoch values | `<EPOCH>` |
| 4 | `pid` | `pid 1234`, `pid=1234` | `pid <PID>` |
| 5 | `uuid` | UUID v1–v5 strings | `<UUID>` |
| 6 | `duration` | `123ms`, `1.25s`, `42ns` | `<DUR>` |
| 7 | `hex-hash` | hex runs of 12+ chars | `<HASH>` |
| 8 | `path` | `C:\...` and `/a/b/c` paths | `<PATH>` |
| 9 | `trailing-ws` | trailing spaces/tabs per line | removed |

Run `snapgate run --list-normalizers` to see the effective chain including
custom rules.

## Typical flow

```shell
# 1. first run: snapshots do not exist yet
$ snapgate run
MISS default-report  snapshot missing (default-report/stdout.txt, ...); run with --update to create it
...
1 case(s): 1 missing
hint: run `snapgate run --update` to accept the new output

# 2. accept the baseline
$ snapgate run --update
NEW  default-report  created 3 snapshot file(s)

# 3. every later run is a regression check
$ snapgate run
PASS default-report  0.69s
1 case(s): 1 pass

# 4. an intentional output change is reviewed, then accepted
$ snapgate run
FAIL default-report  output differs from snapshot
--- snapshots/stdout.txt
+++ actual/stdout.txt
@@ -1,4 +1,4 @@
-report for everybody (mode=fast)
+report for world (mode=fast)
$ snapgate run --update
```

Commit `snapgate.toml` together with `snapshots/`. A pull request that changes
a snapshot shows exactly which observable behaviour changed.
