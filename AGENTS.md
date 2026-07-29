# AGENTS.md

## Model Roles

- GPT-5.6 sol is the orchestrator. It plans, delegates, monitors progress, reviews results, and coordinates the work.
- GPT-5.5 is the executor. It performs implementation, modification, testing, and other hands-on tasks.

## Branch Policy

- ユーザーが明示的に指示しない限り、新しい Git ブランチを作成してはいけない。
- 作業は現在のブランチで継続する。

## Repository-local test runtime

- ローカルWindowsでは
  `.\scripts\test-local.ps1`
  のようにrunner経由でtestを実行する。
- runnerは一時fileとcacheをrepo内の`Tmp/test-runtime/`へ限定する。
- `Tmp/`はGit管理外とし、security softwareの停止や除外設定は行わない。
- repo内`Tmp`でもblockされた場合は、errorを記録してLinux／CI検証へ切り替える。

## Role

`RenCrow_EcoSystem` is the official entry point and integration catalog for the
RenCrow product family. It describes how independently released RenCrow
repositories form one product.

This repository owns:

- the ecosystem component manifest and compatibility matrix;
- ecosystem-level architecture, installation, and release documentation;
- integration verification policy and release acceptance criteria;
- links to each module's authoritative specification and release.

This repository does not own:

- module implementation source, module-specific APIs, or internal design;
- production Persona, Memory, Recall, approval, or LLM routing behavior;
- reusable tools, generated artifacts, runtime state, or secrets;
- copies of module repositories or Git submodules.

## Read Order

1. `/home/nyukimi/RenCrow/AGENTS.md`
2. This file
3. `README.md`
4. `docs/README.md`
5. `ecosystem.yaml`
6. The authoritative docs in every affected module repository

## Source-of-Truth Rules

- `RenCrow_CORE` is authoritative for shared Viewer, runtime, route, adapter,
  Public API, and user-facing behavior across the RenCrow system.
- `RenCrow_CMD` is the terminal client and command facade for the CORE Public
  API. It is not an independent runtime or API source of truth.
- A module repository is authoritative for its source, API, build, tests,
  configuration, and module-specific roadmap.
- This repository is authoritative for declared source pins, tested release
  combinations, and ecosystem-wide guidance. A source pin alone is not a
  compatibility claim.
- Do not duplicate detailed module specifications here. Link to them and record
  only the cross-module consequence.
- Do not mark a component version as compatible until the declared integration
  checks have passed.
- `development`, `source-pinned`, `unpinned`, and `verified` are explicit states.
  `source-pinned` uses full Git commit SHAs for implemented components and
  `planned` only for an optional runtime that does not exist yet. Never invent a
  release tag or commit to make the matrix look complete.
- Describe only the current architecture and explicitly planned components.
  Remove superseded systems and interfaces from the manifest and documentation
  instead of retaining migration or rejection narratives.

## Repository Rules

- Keep each component as an independent Git repository with its own CI, tags,
  and releases.
- Do not add Git submodules. The manifest identifies repositories and versions.
- Keep cross-module reusable tooling in `RenCrow_Tools`; only validation tightly
  coupled to `ecosystem.yaml` belongs under this repository's `scripts/`.
- Keep examples secret-free. Do not commit `.env`, credentials, runtime logs,
  databases, generated binaries, model files, or downloaded release archives.
- Changes to compatibility claims require evidence in the change description or
  a repo-native verification record.

## Validation

Run before considering a change complete:

```bash
make check
```

When all sibling repositories are available in the standard RenCrow workspace,
also run:

```bash
make check-workspace
```

## Cross-Platform Requirement

This repository must work on Windows, Linux, and macOS. Do not write code or tests that pass on only one of them.

- Join paths with `filepath.Join()` in Go and `pathlib.Path` in Python. Never concatenate `/` or `\` into a path string.
- Escape any path embedded in YAML, JSON, or a shell command. Use `strconv.Quote()` in Go. Windows paths contain `\`, so a raw embed is read as an escape sequence such as `\U` and fails to parse.
- Do not use absolute paths such as `/tmp` or `/home/<user>` as real I/O targets. Use `t.TempDir()` in Go or `tempfile` in Python. Strings only passed through as configuration values are out of scope.
- Do not depend on a specific line ending (LF or CRLF) in comparisons or tests.
- Do not assume executable bits, symlinks, or a case-sensitive filesystem.
- Before calling work complete, run the tests on both Windows and Linux, or check the corresponding CI job. Do not report completion from one platform alone.
