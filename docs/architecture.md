# Architecture

## Product model

RenCrow は、Go 製の中核 runtime と、必要に応じて追加する capability service、
extension、tooling、設定 snapshot からなる複数 repository の product です。

```text
                   RenCrow_EcoSystem
             catalog / compatibility / release
                            |
                  references module releases
                            |
        +-------------------+-------------------+-------------------+
        |                   |                   |                   |
  required runtime   interaction layer   optional capability       extension/support
        |                   |                   |                   |
  RenCrow_CORE       PORTAL/CMD             LLM/STT/TTS/Vision/Image  GAMES/Tools + Workspace(snapshot)
                      ASSISTANT (planned)
```

`RenCrow_EcoSystem` は control plane や runtime service ではありません。
shared Viewer、runtime、route、adapter、Public API、user-facing behaviorの正本と
実行時の中心は `RenCrow_CORE` です。

## Dependency direction

```text
EcoSystem --references--> immutable module release artifacts
CMD       --public API--> CORE
PORTAL    --Chat / IdleChat / Games allowlist--> CORE
Device    --HTTP/WebSocket--> ASSISTANT  (planned)
ASSISTANT --public API/task escalation--> CORE  (planned)
CORE      --launch------> GAMES
GAMES     --result / ObserverFrame----> CORE
CORE      --contracts---> LLM / STT / TTS / Vision / Image
User      --PORTAL Games / CORE observer proxy--> GAMES Observer
CORE/Worker --invokes--> Tools
~/.rencrow/workspace --portable non-secret snapshot--> Workspace repository
```

各矢印は source inclusion を意味しません。repository 間連携は、公開 API、CLI、
設定 schema、release artifact などの明示的 contract を使います。

PORTALはCOREのclientであり、runtime状態の正本ではありません。COREが会話処理、
recipient routing、audio／input active owner、TTS／STT bridgeを所有し、PORTALは
読み取り専用`IdleChat`、操作可能な`Chat`、Agent-owned session用`Games`のallowlistで外部操作を制限します。接続フロー、失敗時の
扱い、統合試験条件は[PORTAL–CORE contract](portal-core-contract.md)を参照してください。

ASSISTANTは個人・家族向けの生活Routine、PUSH、delivery、端末応答を所有する
planned serviceです。Deviceは薄い入出力client、COREはAgent・Memory・
Knowledge・複雑なTaskの正本です。生活Routine schedulerとCOREのWorkstream／Task
schedulerを混同しません。横断契約は[ASSISTANT boundary](assistant-boundary.md)を参照してください。

PORTALとCMDはCOREの周囲に置くclient moduleです。Chat、IdleChat、Games、recipient、
event、session、audio、Task、errorの意味はCORE Public APIに従い、Web表示と
terminal表示だけをprofile固有差にします。ASSISTANTはpersonal／family／Routine／
delivery状態を所有するplanned serviceです。詳細は
[Interaction surfaces](interaction-surfaces.md)を参照してください。

Capability moduleは、配布するprimary runtimeと外部演算runtimeを分けられます。
RenCrow_LLMではcontrol host上のRenCrow LLM Gateway（`rencrow-llm`）がprimary、
compute host上のRenCrow LLM Runtime（現行binary `rencrow-llm-node`）が
同梱しないcompanionです。Runtime配下にBackend、Model、KV、計算資源を置き、
Agent、Persona、
Memory、外部provider選択を複製しません。共通契約は[Runtime layers](runtime-layers.md)と
[Binary placement](binary-placement.md)を参照してください。

Capabilityのproduction依存方向は次で固定します。

```text
CORE -> RenCrow LLM Gateway -> RenCrow LLM Runtime -> Backend -> Model
CORE -> RenCrow_STT -> STT target
CORE -> RenCrow_TTS -> TTS target
CORE -> RenCrow_Vision -> Wild backend -> RenCrow_Vision -> CORE
CORE -> RenCrow_Image -> ForgeNeo / Z-Image
```

COREは物理LLM、STT／TTS target、Wild、画像生成backendへ直接fallbackしません。

Game lifecycleは次で固定します。

```text
CORE Agent
  -> POST /viewer/games/launch
  -> GAMES Observer / title process
  -> CORE Agent decision / deterministic GAMES Executor
  -> result / ObserverFrame
  -> CORE observer proxy
  -> User
```

起動方向は`CORE -> GAMES`です。Agent-owned sessionの起動意思と各turnの行動決定は
COREの対象Agent、world、rules、action validation、execution、Replay、Observer描画は
GAMESが正本です。PORTAL Gamesは選択・session・観戦UIとPuruPuru overlayだけを所有します。
COREは起動意思、Persona、Recall、LLM routing、候補記憶、result受信、ユーザー向けproxyを所有します。

LLMの論理依存と実行経路を次で固定します。

```text
Agent -- CORE-owned assignment --> Execution Role
CORE -> RenCrow LLM Gateway -> RenCrow LLM Runtime -> Backend -> Model
```

COREがAgentとExecution Roleを所有し、GatewayがRoleに付随するprofileからRuntimeを、
RuntimeがBackendとModelを解決します。Role profileは技術設定であり、独立した人格層を
追加しません。

Agent IDとExecution Role identityはmodule間の安定contract、Runtime／Backend／Modelと
Role profile revisionは交換可能なdeployment設定です。PORTAL、CMD、および実装後のASSISTANTは
Agentだけを選び、Role、execution alias、Runtime、Backend、Modelを直接選びません。Shiroの`CHAT`を
`ChatWorker`、`OPS`／作業実行を`Worker`へ割り当てる判断はCOREが所有します。

COREからRenCrow_LLMへ渡すexecution aliasは、Agent／Role bindingを表すopaqueな
契約値です。Agent ID、Role ID、Model名のいずれか一つではなく、Target変更だけを
理由に変更しません。

## Why not a monorepo or Git submodules

- module ごとの言語、release cadence、runtime dependency を独立に保てる。
- optional service を CORE の build と切り離せる。
- module 固有変更で ecosystem 全体を再 release する必要がない。
- `ecosystem.yaml` だけで検証済み組み合わせを固定できる。
- submodule checkout、detached HEAD、nested PR 運用を利用者へ要求しない。

multi-repo 構成を変える場合は、実測した CI 負荷、release 障害、access control
などの具体的根拠を ADR として先に残します。
