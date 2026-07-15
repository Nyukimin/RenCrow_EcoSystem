# AGENTS.md

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

- A module repository is authoritative for its source, API, build, tests,
  configuration, and module-specific roadmap.
- This repository is authoritative only for the tested combination of module
  releases and ecosystem-wide guidance.
- Do not duplicate detailed module specifications here. Link to them and record
  only the cross-module consequence.
- Do not mark a component version as compatible until the declared integration
  checks have passed.
- `development` and `unpinned` are explicit states. Never invent a release tag
  to make the matrix look complete.

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
