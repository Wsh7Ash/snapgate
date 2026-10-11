# Project Spec — snapgate

| Field | Value |
|---|---|
| Name | snapgate |
| Category | testing-qa |
| Target user | Developers and QA engineers who test CLIs, generators, formatters, compilers, and any command whose output is worth locking down |
| Problem | Golden/snapshot tests rot immediately: output contains timestamps, absolute paths, pids, UUIDs, and hashes, so either the test breaks on every run or the assertion gets weakened until it checks nothing |
| Solution | A dependency-free snapshot runner whose normalizer chain scrubs nondeterministic values *before* comparison, plus an explicit `--update` flow so output changes are accepted deliberately, never silently |
| Core workflow | `snapgate.toml` declares cases → `snapgate run` executes them (no shell) → outputs are normalized → compared with committed `snapshots/<case>/{stdout,stderr,exit}.txt` → PASS/FAIL with a unified diff → `snapgate run --update` accepts intentional changes |
| Must-have features | run/update/diff comparison; exit-code capture; stdin, cwd, env, timeout per case; nine built-in normalizers; custom `[[normalizer]]` rules; `--json` for CI; `--only` filtering; `list`; matrix case expansion; exit codes 0/1/2 |
| Nice-to-have features | parallel case execution, baseline branching, HTML reports |
| Stack | Python 3.11+ standard library only (`tomllib`, `subprocess`, `difflib`, `argparse`); no third-party dependencies |
| Test strategy | `unittest` suite covering normalizers, config validation, runner behaviour (pass/fail/missing/timeout/error/update), CLI exit codes and JSON output, plus a dogfood integration test that runs `snapgate run` against this repository's own snapshots |
| Demo/result strategy | Real artifacts in `results/`: a demo run, a deliberately produced mismatch diff (then restored), and a `--json` report |
| Safety considerations | snapgate executes whatever commands are configured — it must only be pointed at trusted config; commands run without a shell (`shell=False`); no network use; snapshots must never contain machine-specific paths (the path normalizer is dogfooded against this repo) |
| Definition of done | `python -m unittest discover -s tests -v` passes, `python -m snapgate run` exits 0, example snapshots pass, README commands are the commands actually executed, RESULTS.md reflects only observed runs |
