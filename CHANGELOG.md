# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-10-10

### Added
- `snapgate run`: execute configured cases and compare stdout, stderr, and exit
  code against committed snapshots; unified diffs via `difflib`.
- `snapgate run --update`: create or refresh snapshots deliberately.
- `snapgate run --json`: machine-readable report for CI.
- `snapgate run --only SUBSTRING`: filter cases by name.
- `snapgate list`: show cases and snapshot completeness.
- `snapgate run --list-normalizers`: print the ordered normalizer chain.
- Nine built-in normalizers: CRLF, ISO timestamp, epoch, pid, UUID, duration,
  hex hash, absolute path, trailing whitespace.
- Custom `[[normalizer]]` regex rules declared in `snapgate.toml`.
- `matrix` case expansion for argument-driven variants.
- Per-case `command`, `stdin`, `cwd`, `timeout`, `env`, `snapshot_dir`.
- Dogfood suite: this repository validates its own snapshots.
