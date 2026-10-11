# Results

## Environment
- OS: Microsoft Windows NT 10.0.19044.0 (Windows 10/11, PowerShell 7)
- Runtime/compiler: Python 3.14.3 (MSYS2 build), no compilation step
- Dependency manager: none — standard library only (`tomllib`, `subprocess`, `difflib`, `argparse`); `pip install` not required or used

## Validation performed
- install: N/A (project runs without installation via `PYTHONPATH=src python -m snapgate`; a PEP 668 managed Python refused `pip install` in this environment, so no install path was exercised)
- build: N/A (pure Python, no build step)
- unit tests: PASS — 37 tests, 0 failures, 0 errors
- integration tests: PASS — dogfood `snapgate run` (6 cases) and example config `snapgate run -c examples/snapgate.toml` (3 cases), both exit 0
- lint: N/A (no linter installed in this environment)
- type check: N/A (no type checker installed in this environment)
- demo run: PASS — demo baseline created, demo run green, deliberate mismatch diff captured, JSON report parsed

## Commands executed
```shell
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
python -m snapgate run --update                 # create dogfood baseline
python -m snapgate run                          # exit 0
python -m snapgate run -c examples/snapgate.toml --update
python -m snapgate run -c examples/snapgate.toml
python -m snapgate run -c examples/snapgate.toml --json
python -m snapgate run -c examples/snapgate.toml --only default   # after mutating a snapshot
python -m snapgate list
python -m snapgate run --list-normalizers
python -m snapgate --version
```

## Observed result

Unit tests:

```text
Ran 37 tests in 3.107s

OK
```

Dogfood (`python -m snapgate run`, exit 0):

```text
PASS stable-hello     0.09s
PASS noisy-output     0.20s
PASS stderr-and-exit  0.07s
PASS stdin-roundtrip  0.08s
PASS matrix-args[0]   0.07s
PASS matrix-args[1]   0.07s

6 case(s): 6 pass
```

Example project (`python -m snapgate run -c examples/snapgate.toml`, exit 0):

```text
PASS default-report  0.69s
PASS safe-mode       1.62s
PASS failure-path    1.54s

3 case(s): 3 pass
```

Deliberate mismatch (snapshot edited, run captured, snapshot restored):

```text
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
(exit 1, restored afterwards — the subsequent run was 3 pass again.)

`snapgate --version` → `snapgate 0.1.0`.
`snapgate list` → 6 cases, all `ready`, normalizers: 10 (9 built-in + 1 custom).

Dogfooding found and fixed a real gap during development: the first baseline
committed a raw `pid` because no normalizer covered it; the `pid` rule was
added, the baseline regenerated, and the suite has been green since.

## Generated artifacts
- `results/demo-run.txt` — real example run output (3 pass)
- `results/demo-update.txt` — real `--update` output creating example snapshots
- `results/demo-diff.txt` — real unified diff from the deliberate mismatch
- `results/report.json` — real `--json` report of the example run
- `snapshots/` — committed dogfood snapshots (6 cases)
- `examples/snapshots/` — committed example snapshots (3 cases)

## Known limitations
- `pip install -e .` was not verified in this environment (PEP 668 managed
  Python, no offline build backend); the documented no-install route is the
  one exercised. The console-script entry point is declared but unproven here.
- Lint and type checking were not run because no linter/type checker is
  installed; no claim is made about their status.
- Normalizer regexes are deliberately simple and may over-match on unusual
  output; users should inspect `--list-normalizers` and add custom rules.
- CI workflow is written to run the exact commands verified locally but was
  not executed on GitHub from this machine.
