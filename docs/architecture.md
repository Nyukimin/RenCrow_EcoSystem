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
  RenCrow_CORE       PORTAL/CMD             LLM/STT/TTS/Vision/Image  GAMES/Tools/Workspace
                      ASSISTANT (planned)
```

`RenCrow_EcoSystem` は control plane や runtime service ではありません。
shared Viewer、runtime、route、adapter、Public API、user-facing behaviorの正本と
実行時の中心は `RenCrow_CORE` です。

## Dependency direction

```text
EcoSystem --references--> immutable module release artifacts
CMD       --public API--> CORE
PORTAL    --allowlisted public API--> CORE
Device    --HTTP/WebSocket--> ASSISTANT  (planned)
ASSISTANT --public API/task escalation--> CORE  (planned)
CORE      --launch------> GAMES
GAMES     --decision/result callback--> CORE
CORE      --contracts---> LLM / STT / TTS / Vision / Image
User      --CORE observer proxy-------> GAMES Observer
CORE/Worker --invokes--> Tools
Ubuntu runtime workspace --snapshot--> Workspace repository
```

各矢印は source inclusion を意味しません。repository 間連携は、公開 API、CLI、
設定 schema、release artifact などの明示的 contract を使います。

PORTALはCOREのclientであり、runtime状態の正本ではありません。COREが会話処理、
recipient routing、audio／input active owner、TTS／STT bridgeを所有し、PORTALは
読み取り専用`IdleChat`と操作可能な`Chat`のallowlistで外部操作を制限します。接続フロー、失敗時の
扱い、統合試験条件は[PORTAL–CORE contract](portal-core-contract.md)を参照してください。

ASSISTANTは個人・家族向けの生活Routine、PUSH、delivery、端末応答を所有する
planned serviceです。Deviceは薄い入出力client、COREはAgent・Memory・
Knowledge・複雑なTaskの正本です。生活Routine schedulerとCOREのWorkstream／Task
schedulerを混同しません。横断契約は[ASSISTANT boundary](assistant-boundary.md)を参照してください。

PORTALとCMDはCOREの周囲に置くclient moduleです。Chat、IdleChat、recipient、
event、session、audio、Task、errorの意味はCORE Public APIに従い、Web表示と
terminal表示だけをprofile固有差にします。ASSISTANTはpersonal／family／Routine／
delivery状態を所有するplanned serviceです。詳細は
[Interaction surfaces](interaction-surfaces.md)を参照してください。

Capability moduleは、配布するprimary runtimeと外部演算runtimeを分けられます。
RenCrow_LLMではcontrol host上の`rencrow-llm` central Gatewayがprimary、
Backend＋Model＋KV＋計算資源からなるLLM targetが同梱しないcompanionです。
compute hostには`rencrow-llm-node`とBackend／Modelを置き、Agent、Persona、
Memory、外部provider選択を複製しません。共通契約は[Runtime layers](runtime-layers.md)と
[Binary placement](binary-placement.md)を参照してください。

Capabilityのproduction依存方向は次で固定します。

```text
CORE -> RenCrow_LLM -> LLM target
CORE -> RenCrow_STT -> STT target
CORE -> RenCrow_TTS -> TTS target
CORE -> RenCrow_Vision -> Wild backend -> RenCrow_Vision -> CORE
CORE -> RenCrow_Image -> ForgeNeo / Z-Image
```

COREは物理LLM、STT／TTS target、Wild、画像生成backendへ直接fallbackしません。

Game lifecycleは次で固定します。

```text
CORE Agent / LLM
  -> GAMES launch
  -> deterministic Game Executor
  -> CORE / RenCrow_LLM decision callback
  -> GAMES execution and ObserverFrame
  -> CORE observer proxy
  -> User
```

起動方向は`CORE -> GAMES`です。現在の`GAMES -> CORE -> RenCrow_LLM`は、
起動後のターン判断callbackであり、GAMESがruntimeやLLM providerを所有する意味では
ありません。world、rules、action validation、execution、Replay、Observer描画は
GAMESが正本です。COREは起動意思、Persona、Recall、LLM routing、候補記憶、
ユーザー向けproxyを所有します。

LLMの論理依存は次の3層とします。

```text
Agent -- CORE-owned assignment --> Execution Role
Execution Role -- RenCrow_LLM-owned mapping --> Inference Target
```

COREがAgentとExecution Roleを所有し、RenCrow_LLMがRoleに付随するprofileから
Inference Targetを解決します。Role profileは技術設定であり、AgentとTargetの間へ
独立した人格層を追加しません。

Agent IDとExecution Role identityはmodule間の安定contract、Inference Targetと
Role profile revisionは交換可能なdeployment設定です。PORTAL、CMD、および実装後のASSISTANTは
Agentだけを選び、Role、execution alias、Targetを直接選びません。Shiroの`CHAT`を
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
