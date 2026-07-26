# CLAUDE.md - RenCrow_EcoSystem working notes

## Purpose of this file

This file is a short entry point for Claude Code or an equivalent AI development environment working in RenCrow_EcoSystem. It is not the authoritative product specification.

Detailed working constraints live in `AGENTS.md`. If this file and `AGENTS.md` disagree, `AGENTS.md` wins.

## Read order

1. `AGENTS.md`
2. `README.md`
3. Relevant specs under `docs/`
4. Related code, tests, and configuration

## Cross-Platform Requirement

This repository must work on Windows, Linux, and macOS. Do not write code or tests that pass on only one of them.

- Join paths with `filepath.Join()` in Go and `pathlib.Path` in Python. Never concatenate `/` or `\` into a path string.
- Escape any path embedded in YAML, JSON, or a shell command. Use `strconv.Quote()` in Go. Windows paths contain `\`, so a raw embed is read as an escape sequence such as `\U` and fails to parse.
- Do not use absolute paths such as `/tmp` or `/home/<user>` as real I/O targets. Use `t.TempDir()` in Go or `tempfile` in Python. Strings only passed through as configuration values are out of scope.
- Do not depend on a specific line ending (LF or CRLF) in comparisons or tests.
- Do not assume executable bits, symlinks, or a case-sensitive filesystem.
- Before calling work complete, run the tests on both Windows and Linux, or check the corresponding CI job. Do not report completion from one platform alone.
