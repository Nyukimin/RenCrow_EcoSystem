# RenCrow EcoSystem

RenCrow EcoSystem は、独立した RenCrow 各リポジトリを一つの製品として
理解・導入・検証・リリースするための公式入口です。

このリポジトリ自体は実行時サーバではなく、各 module のソースコードも
内包しません。標準 checkout は `RenCrow` という workspace root であり、
全体アーキテクチャ、module の役割、導入順序、動作確認済みの組み合わせを
その root から管理します。

## 基本関係

```text
RenCrow (EcoSystem workspace root) -- release/catalog reference --> module releases

                         RenCrow_CORE
                    ^              ^
                    |              |
                 PORTAL           CMD
                 Web UI    Public API client
                    |              |
                 Browser    Terminal / Script

          RenCrow_ASSISTANT (development)
          Manual PUSH CLI / future Routine / Device delivery

RenCrow_CORE ---- contracts ----> LLM / STT / TTS / Vision / Image
RenCrow_CORE ---- private API ---> TRADE
RenCrow_CORE -- launch ---------> RenCrow_GAMES
RenCrow_GAMES -- result / ObserverFrame --> RenCrow_CORE
Games / Tools / Workspace -------- ecosystem support
```

- 各 module は独立した Git リポジトリです。
- 各 module がソース、詳細仕様、テスト、CI、タグ、Release を所有します。
- EcoSystem は統合確認済みの組み合わせを `ecosystem.yaml` に記録します。
- shared Viewer、runtime、route、adapter、Public API、user-facing behaviorは
  RenCrow_COREを正本とします。
- Atlas / Backlog / Implementation Lifecycle の状態、Evidence gate、singleton WIP lease、
  Viewer/API は RenCrow_CORE が所有し、RenCrow_CMD は一要求をその owner API へ中継する
  terminal facade だけを提供します。詳細契約は CORE 正本を参照します。
- Development Methodologyも同じAtlas owner、Workstream artifact、Skill Registry、Event／Traceを
  拡張し、別WIP、別Delivery state、別ledger DBを作りません。CMDはmethodology stateを所有せず、
  COREのunit／task／Evidence／Ruling／Review投影を読むfacadeだけを提供します。
- module から EcoSystem の実装へ依存しません。
- 実行時連携は HTTP、WebSocket、CLI、設定ファイルなどの公開契約を使います。
- Git submodule は使用しません。
- この repository は workspace root 自身を管理します。標準 clone directory は
  `RenCrow` です。
- `RenCrow_*` は root 直下の独立した Git repository として配置し、この catalog の
  `.gitignore` で除外します。Git submodule や親 repository の管理対象にはしません。
- source checkoutの一括準備は、RenCrow_Toolsの`rencrow-bootstrap`が
  `ecosystem.yaml`を読み、root直下の独立した repository としてcloneします。

## 現在の状態

現在の構成は`development`かつ`source-pinned`です。実装済みcomponentは
現在のGit commit SHAへ固定します。RenCrow_ASSISTANTも手動通知CLIまで実装されたため
実在commitを`development`として固定します。これによりsourceの組み合わせは再現できますが、release artifact、
checksum、統合互換性の検証済みを意味しません。統合試験後に実在するtagと
検証結果を記録してecosystem releaseを作成します。

`ecosystem.yaml` schema v4では、moduleの配布artifactを`runtime.primary`、
利用環境側で別途動かす演算runtimeなどを`runtime.companions`として分離できます。
独立Git管理されるhost固有のBackend profileは`runtime_profiles`へ登録し、owner moduleを
必須にします。runtime profileはAgent、routing owner、独立Public APIではありません。
現在はRenCrow_LLM、RenCrow_STT、RenCrow_TTS、RenCrow_Vision、RenCrow_Imageへ適用し、
Go binaryと各演算targetを
別の配布層として宣言しています。COREのproduction経路は各Gatewayだけを参照し、
物理targetへ直接接続しません。

標準Go配布、optional sidecar、外部computeの意味は
[RenCrow_COREの正本](https://github.com/Nyukimin/RenCrow_CORE/blob/main/docs/04_アーキテクチャ概要.md#標準go配布境界)
に従います。このrepositoryはartifact、配置、互換性を記録し、module間責務を再定義しません。

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
Task移譲を所有する段階実装中のGo componentです。現在は手動通知CLIまでで、Mio等のAgentやPORTALのWeb画面を
所有するmoduleではありません。

PORTALはCOREのChat、IdleChat、Gamesを提供するWeb clientです。CMDはCORE Public APIだけを
利用するterminal client兼command facadeで、COREとPORTALのprocess entrypointも提供します。
ASSISTANTはproactive triggerとDevice deliveryを担うcomponentであり、現在の手動通知CLIも将来の常駐serviceも
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

RenCrow_TRADEは金融Source、学習、Replay、Portfolio risk、TradeGate、Ledgerを所有します。
現時点ではCORE連携、Broker、Paper、LIVEは未実装で、LIVE取引は禁止です。

## Durable Data Store topology

Ubuntu productionの基準では、利用可能なlocal durable媒体を2 TB HDD 2基に限定し、live dataを
`/srv/rencrow/db`、別媒体backupを`/srv/rencrow/backup`へ配置します。追加のlocal HDDをKnowledge、
staging、backup、fallbackに使用しません。各moduleは同名subtreeだけを所有し、EcoSystemは配置と
互換性を記録するだけでDBやbackupを所有しません。

| subtree | owner | 主な内容 |
| --- | --- | --- |
| `core/` | RenCrow_CORE | 会話Memory、Knowledge、映画・趣味catalog、CORE DB／artifact |
| `trade/` | RenCrow_TRADE | Raw Source、Dataset、Learning Run、Portfolio、Ledger |
| `image/` | RenCrow_Image | 保持対象の生成画像とmanifest |
| `games/` | RenCrow_GAMES | Replay、world／session export |
| `tools/` | RenCrow_Tools | 未import artifact、staging、再取得可能cache |

RenCrow_STT、Vision、LLM Gatewayは共通DBを所有せず、保持が必要な成果物は依頼元domainまたは
専用所有moduleへ渡します。RenCrow_TTSも共通DBは持ちませんが、ownerが採用した発音辞書は
TTS固有のdurable stateとしてowner exportの対象です。RenCrow_Workspaceはportable snapshotと
owner-onlyの非圧縮Migration Artifactを扱いますが、
live storeや通常backupの代替ではありません。format、mount、fail-closed、backup整合性は
[RenCrow_COREの正本](https://github.com/Nyukimin/RenCrow_CORE/blob/main/docs/05_設定リファレンス.md#db物理配置とbackup)
および[Backup and recovery](docs/backup-and-recovery.md)に従い、このREADMEでは再定義しません。

## Persistent DB capability boundary

物理配置の表は保存先の所有権を示すだけで、AgentがDBへ直接アクセスできることを意味しません。
永続データをAgent能力として提供する場合は、必ずowner moduleの認証済みAPI／Tool境界を通し、
purpose、role、authenticated scope、相関IDを持つbounded read projectionと、ownerが検証する
named write command／workflowを提供します。raw path、SQL、DB driver、別moduleの内部storeへの
直接アクセスと、ownerを迂回するmodule間read/writeは禁止です。

- RenCrow_COREはCORE semantic DB capability catalogと、CORE所有のConversation／Memory／Knowledge／
  Catalogおよび各種運用DBのread projection、validated write workflowを所有します。具体的なschema、
  path、payloadはCORE正本を参照し、このrepositoryへ複製しません。
- RenCrow_TRADEはSource／Learning／Replay／Portfolio／Ledgerを所有し、`CORE -> RenCrow_TRADE private API gateway`
  のみを公開境界とします。COREはTRADEの物理DBを直読・直書きしません。
- RenCrow_GAMES、RenCrow_Image、RenCrow_ASSISTANTは、それぞれのowner serviceがReplay／world、
  生成artifact、Routine／delivery状態を管理します。PORTAL、CMD、DeviceなどのclientはDBへ直結しません。
- RenCrow_Toolsは再取得可能なstaging／cache／変換artifactだけを扱い、semantic Memory、catalog、
  control planeのownerではありません。RenCrow_Workspaceはmachine-readableなportable policy／設定
  projectionであり、live DB、認証権限、runtime capabilityの正本ではありません。
- RenCrow_LLM、STT、TTS、Visionは共通product DBを所有せず、成果物を依頼元または専用ownerへ返します。
  PORTAL、CMD、ASSISTANTはCORE Public API clientであり、COREまたは他moduleのDBへ直接アクセスしません。

Catalogや`restricted`表示だけでは統合互換性を主張しません。`verified`には、各persistent domainの
authenticated Agent-owned read/write production E2Eと、owner route、scope、projection／receipt、
fail-closed結果を記録したverification evidenceが必要です。[Modules](docs/modules.md)と
[Compatibility](docs/compatibility.md)に共通境界とgateを示します。

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
├── tests/
│   └── test_validate_ecosystem.py
├── RenCrow_CORE/       # ignored independent repository
├── RenCrow_Tools/      # ignored independent repository
└── RenCrow_*/           # other ignored independent repositories
```

workspace rootには、manifestで宣言した各 child repositoryを同じ形式で配置します。

`ecosystem.yaml` は外部 YAML dependency を不要にするため、YAML 1.2 で有効な
JSON-compatible syntax を採用しています。schema v4 の `workspace_path` は
`./OneDirectChild` 形式の root 直下だけを指します。

source checkout用bootstrapの実装はRenCrow_Toolsが所有します。このrepositoryは
repository、workspace path、versionの正本と検証を所有し、clone処理を複製しません。
root checkout後は `RenCrow_Tools` から `ecosystem.yaml` を読み、各 child repository を
`RenCrow` workspace root直下へ配置します。

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

moduleごとのルール入口、標準test plan、CI、およびworkspace rootの
`AGENTS.md` snapshot一致まで監査する場合:

```bash
make check-governance
```

Windows workspaceでは`make PYTHON=python check-workspace`を使用します。

## Documentation

読む順番と正本境界は [docs/README.md](docs/README.md) を参照してください。

## License

[MIT License](LICENSE)
