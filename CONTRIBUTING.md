# Contributing to snapgate

Thanks for considering a contribution.

## Development setup

No dependencies to install. From the repository root:

```shell
# PowerShell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m snapgate run          # dogfood: validates this repo's snapshots
```

```shell
# bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m snapgate run
```

Python 3.11+ is required (for `tomllib`).

## Ground rules

1. All tests and the dogfood run must pass before a PR is opened.
2. Do not commit snapshot changes without an explanation in the PR: a changed
   snapshot means observable behaviour changed.
3. New normalizers must include a test showing both what they scrub and what
   they deliberately leave alone (over-matching is a bug).
4. Keep the project dependency-free. A contribution that needs a third-party
   runtime dependency must justify it in the PR description.
5. No absolute machine paths in fixtures, snapshots, or docs.

## Reporting bugs

Open an issue with the exact command, the config that produced it, and the
actual output. Please strip secrets from the config before pasting it —
`snapgate` executes whatever commands you configure.
