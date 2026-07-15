# Architecture

## Product model

RenCrow は、Go 製の中核 runtime と、必要に応じて追加する capability service、
extension、tooling、設定 template からなる複数 repository の product です。

```text
                   RenCrow_EcoSystem
             catalog / compatibility / release
                            |
                  references module releases
                            |
        +-------------------+-------------------+
        |                   |                   |
  required runtime   optional capability   extension / support
        |                   |                   |
  RenCrow_CORE       LLM / STT / TTS       GAMES / Tools
  RenCrow_CMD        Vision                 Image / Workspace
```

`RenCrow_EcoSystem` は control plane や runtime service ではありません。
実行時の中心は `RenCrow_CORE` です。

## Dependency direction

```text
EcoSystem --references--> immutable module release artifacts
CMD       --public API--> CORE
CORE      --contracts---> LLM / STT / TTS / Vision
GAMES     --bridge API--> CORE
CORE/Worker --invokes--> Tools
Workspace --templates--> CORE runtime configuration
Image     --offline outputs--> approved consuming module
```

各矢印は source inclusion を意味しません。repository 間連携は、公開 API、CLI、
設定 schema、release artifact などの明示的 contract を使います。

## Why not a monorepo or Git submodules

- module ごとの言語、release cadence、runtime dependency を独立に保てる。
- optional service を CORE の build と切り離せる。
- module 固有変更で ecosystem 全体を再 release する必要がない。
- `ecosystem.yaml` だけで検証済み組み合わせを固定できる。
- submodule checkout、detached HEAD、nested PR 運用を利用者へ要求しない。

multi-repo 構成を変える場合は、実測した CI 負荷、release 障害、access control
などの具体的根拠を ADR として先に残します。
