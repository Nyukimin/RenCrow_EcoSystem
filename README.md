# RenCrow EcoSystem

RenCrow EcoSystem は、独立した RenCrow 各リポジトリを一つの製品として
理解・導入・検証・リリースするための公式入口です。

このリポジトリ自体は実行時サーバではなく、各 module のソースコードも
内包しません。全体アーキテクチャ、module の役割、導入順序、動作確認済みの
組み合わせを管理します。

## 基本関係

```text
RenCrow_EcoSystem  -- release/catalog reference --> module releases

                         RenCrow_CORE
                    ^              ^
                    |              |
                 PORTAL           CMD
                 Web UI    Public API client
                    |              |
                 Browser    Terminal / Script

          RenCrow_ASSISTANT (planned)
          Routine / PUSH / Device delivery

RenCrow_CORE ---- contracts ----> LLM / STT / TTS / Vision / Image
RenCrow_CORE -- launch ---------> RenCrow_GAMES
RenCrow_GAMES -- result / ObserverFrame --> RenCrow_CORE
Games / Tools / Workspace -------- ecosystem support
```

- 各 module は独立した Git リポジトリです。
- 各 module がソース、詳細仕様、テスト、CI、タグ、Release を所有します。
- EcoSystem は統合確認済みの組み合わせを `ecosystem.yaml` に記録します。
- shared Viewer、runtime、route、adapter、Public API、user-facing behaviorは
  RenCrow_COREを正本とします。
- module から EcoSystem の実装へ依存しません。
- 実行時連携は HTTP、WebSocket、CLI、設定ファイルなどの公開契約を使います。
- Git submodule は使用しません。

## 現在の状態

現在の構成は`development`かつ`source-pinned`です。実装済みcomponentは
現在のGit commit SHAへ固定し、未実装のRenCrow_ASSISTANTだけを`planned`として
明示します。これによりsourceの組み合わせは再現できますが、release artifact、
checksum、統合互換性の検証済みを意味しません。統合試験後に実在するtagと
検証結果を記録してecosystem releaseを作成します。

`ecosystem.yaml` schema v2では、moduleの配布artifactを`runtime.primary`、
利用環境側で別途動かす演算runtimeなどを`runtime.companions`として分離できます。
現在はRenCrow_LLM、RenCrow_STT、RenCrow_TTSへ適用し、Go binaryと各演算targetを
別の配布層として宣言しています。COREのproduction経路は各Gatewayだけを参照し、
物理targetへ直接接続しません。

RenCrow_LLMはRenCrow LLM Gatewayと、compute hostごとのRenCrow LLM Runtimeへ
deployment roleを分けます。正式経路は
`CORE -> RenCrow LLM Gateway -> RenCrow LLM Runtime -> Backend -> Model`です。
配置先、supervisor、Model／Backendの所有境界は
[Binary placement](docs/binary-placement.md)を正本とします。

COREはAgentからExecution Roleへの割り当てを所有します。推論実行は
`CORE -> RenCrow LLM Gateway -> RenCrow LLM Runtime -> Backend -> Model`で固定し、
GatewayがRole profileからRuntimeを、RuntimeがBackendとModelを解決します。
Role profileはExecution Roleに付随する設定レコードであり、独立した人格層ではありません。

RenCrow_ASSISTANTは、個人・家族向けの生活Routine、PUSH、端末配信、COREへの
Task移譲を所有するplannedのGo serviceです。Mio等のAgentやPORTALのWeb画面を
所有するmoduleではありません。

PORTALはCOREのChat、IdleChat、Gamesを提供するWeb clientです。CMDはCORE Public APIだけを
利用するterminal client兼command facadeで、COREとPORTALのprocess entrypointも提供します。
ASSISTANTはproactive triggerとDevice deliveryを担うplanned serviceであり、実装後も
COREの公開契約を利用します。

RenCrow_Visionは画像・動画認識の必須interface、RenCrow_Imageは描画・画像生成の
必須interfaceです。COREはWild、ForgeNeo、ComfyUI、Z-Imageなどの物理backendへ
直接接続しません。RenCrow_WorkspaceはUbuntu runtime workspaceを正本とする
非secret snapshotであり、Windows checkoutやこのcatalogをruntime正本にしません。

RenCrow_GAMESはworld、rules、決定論的executor、Replay、Observer UIの正本です。
ゲームの起動と各turn判断の主体はCOREのAgentです。Agent E2Eでlocal controllerや
RuleBasedBrainを代用しません。GAMESの決定論的executorが検証・実行し、
resultとObserverFrameをCOREへ返します。実行画面はGAMES ObserverをCOREが
same-origin proxyし、PORTAL Gamesが選択・session・観戦UIを提供します。
PuruPuru overlayはPORTAL、盤面はGAMES、Agent identityと判断はCOREが所有します。

## Repository layout

```text
.
├── AGENTS.md
├── README.md
├── ecosystem.yaml
├── Makefile
├── docs/
│   ├── README.md
│   ├── assistant-boundary.md
│   ├── architecture.md
│   ├── binary-placement.md
│   ├── compatibility.md
│   ├── installation.md
│   ├── interaction-surfaces.md
│   ├── modules.md
│   ├── portal-core-contract.md
│   └── runtime-layers.md
├── scripts/
│   └── validate_ecosystem.py
└── tests/
    └── test_validate_ecosystem.py
```

`ecosystem.yaml` は外部 YAML dependency を不要にするため、YAML 1.2 で有効な
JSON-compatible syntax を採用しています。

## Validation

```bash
make check
```

Windowsで`python3` aliasがない場合:

```powershell
.\scripts\test-local.ps1
.\scripts\test-local.ps1 python -- scripts/validate_ecosystem.py ecosystem.yaml
```

標準 workspace (`/home/nyukimi/RenCrow`) に全 sibling repo がある場合:

```bash
make check-workspace
```

Windows workspaceでは`make PYTHON=python check-workspace`を使用します。

## Documentation

読む順番と正本境界は [docs/README.md](docs/README.md) を参照してください。

## License

[MIT License](LICENSE)
