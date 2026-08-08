# Binary placement

## 目的

RenCrowの各binaryを、役割の異なるhostへ重複配置せず、状態と設定の正本を一つに保つ。
EcoSystemは配置規則と検証済み組み合わせを記録するが、processを起動・制御する
runtime control planeにはならない。

## Host role

| host role | 配置する主なbinary | 配置しないもの |
| --- | --- | --- |
| control host | `rencrow`、RenCrow LLM Gateway（`rencrow-llm`）、必要な`rencrow-stt`／`rencrow-tts`／`rencrow-vision`／`rencrow-image` | Model weights、GPU固有Backendを必須にしない |
| compute host | RenCrow LLM Runtime（`rencrow-llm-node`）、Backend、Model | CORE、PORTAL、EcoSystem、Agent Memory |
| interaction host | `rencrowctl`、`rencrow-portal`、将来の`rencrow-assistant` | 物理LLM URL、Model path、provider credential |
| operator workstation | `rencrowctl` | runtime状態の正本 |
| external provider | module-owned adapterから利用するAPI／Agent Runtime | RenCrow binaryの配置を前提にしない |

同じ物理hostが複数roleを兼ねてもよいが、binaryの責務とConfig正本は統合しない。

## Standard topology

```text
control host
  rencrow
  RenCrow LLM Gateway (rencrow-llm)
       |
       +-> compute host A
       |     RenCrow LLM Runtime (rencrow-llm-node)
       |     Backend -> Model
       |
       +-> compute host B
       |     RenCrow LLM Runtime (rencrow-llm-node)
       |     Backend -> Model
       |
       `-> provider-facing RenCrow LLM Runtime
             external API / Agent Runtime Backend -> Model

interaction host
  rencrowctl / rencrow-portal
       -> CORE public API

optional capability host
  rencrow-stt / rencrow-tts / rencrow-vision / rencrow-image
       -> external target / backend
```

RenCrow LLM Gateway（`rencrow-llm`）はRenCrow環境ごとに一つを標準とする。
RenCrow LLM Runtimeの現行binary `rencrow-llm-node`はModel／GPUを持つcompute hostごとに
一つ置く。RuntimeはRenCrow_LLM moduleとrelease contractを共有し、Model別の独立moduleや
repositoryを作らない。

配置とは別に、推論の論理構造は次で固定する。

```text
CORE
  -> RenCrow LLM Gateway
  -> RenCrow LLM Runtime
  -> Backend
  -> Model
```

COREがAgentからExecution Roleへの割り当てを所有し、GatewayがRole profileからRuntimeを、
RuntimeがBackendとModelを解決する。Role profileはRoleに付随するRuntime、thinking、
sandbox、capacity設定であり、独立レイヤーではない。Agent IDとExecution Role identityは
安定contract、Runtime／Backend／ModelとRole profile revisionはdeploymentごとに交換可能な
設定とする。

## Placement rules

### Control host

- `rencrow`をAgent、Persona、Memory、route、同期policy判定の正本として一つ置く。
- `rencrow-llm`をRenCrow LLM Gatewayとして置き、Execution Role profile、
  Runtime mapping、queue／capacity、status集約を所有させる。
- 必要なcapability Gatewayだけを配置する。STT／TTS／Vision／Imageの物理target、Model、
  weights、GPU runtimeは同じhostにある場合でもGatewayの配布artifactへ同梱しない。
- Codex subscription credentialを使う場合は、credentialを保持するtrusted host上で
  Codex runtimeを動かし、別compute hostへcredentialを複製しない。
- 外部API credentialはmoduleのsecret store／environment referenceで管理し、
  EcoSystem manifestや配布Configへ平文保存しない。

### Compute host

- host supervisorが`rencrow-llm-node`を常駐化する。
- RenCrow LLM RuntimeがBackend process、Model readiness、GPU/capacity、
  host-local logを管理する。
- Backendは原則loopback bindとし、Runtimeの認証済みdata planeだけをcontrol hostへ公開する。
- Model weights、Backend binary、runtime dependency、Model pathはcompute hostが所有する。
- control hostからSSH、`taskkill`、`pkill`でBackendを直接管理しない。

WindowsではWindows ServiceまたはTask Scheduler、macOSではlaunchd、Linuxではsystemdを
host supervisorとして使用できる。supervisorはRenCrow LLM Runtimeを監視し、RuntimeがBackendを監視する。

### Interaction host

- PORTALとCMDはCORE Public APIへ接続する。
- Runtime、Backend port、Model名を設定しない。
- PORTALはDebug／Ops／LLM管理を中継しない。
- CMDの管理commandはCOREの認証済みPublic APIだけをfacadeとして呼ぶ。

## Artifact rule

- `runtime.primary`はmanifestで利用可能性とchecksumを検証する配布artifactである。
- planned binaryを存在するrelease artifactとしてmanifestへ登録しない。
- `rencrow-llm-node`はRenCrow_LLMのmodule-owned追加artifactとしてGatewayと同じ
  version、status schema、Backend contractで検証する。
- Model weightsとBackendはGo binaryへ同梱しない。
- 同一moduleのGatewayとRuntimeはversionを揃え、status schemaとBackend contractの
  compatibilityを統合試験する。

## Config ownership

| Config | 配置 |
| --- | --- |
| Agent、Agent -> Execution Role、Persona、Memory、外部送信許可 | CORE control host |
| Execution Role profile、Role -> Runtime、provider secret reference | RenCrow LLM Gateway |
| Runtime endpoint、certificate／token reference | RenCrow LLM Gateway |
| Backend command、Model path、GPU、local port | RenCrow LLM Runtime |
| PORTAL URL、CMD接続先 | interaction host |
| component version、artifact checksum、互換性 | EcoSystem manifest |

## Target配置変更とcutover

- Agent／Role bindingが同じままTarget host、provider、Modelを変更しても、Agent、
  Execution Role、現行execution aliasをrenameしない。
- RenCrow_LLM側で新しいRole profile revisionを作り、cutover前にTarget readinessと
  実生成を確認する。
- Model、tokenizer、chat template、context prefixが変わる場合は旧session／KVを
  再利用しない。
- localからexternalへの変更は外部送信、課金、保持policyを変えるため、CORE正本、binary hard limit、
  deployment policyの機械検証を必要とする。範囲外は人待ちにせず`blocked`にする。
- Agent Persona、会話Session、Memory、RecallはCOREに残し、compute hostやTargetへ
  正本を移さない。
- EcoSystemは検証済みmodule version、Role profile revision、Target mapping、E2E結果、
  rollback先をverification recordへ残すが、runtime Configを複製しない。

## Failure and fallback

- control hostのGateway停止時にclientやCOREがNode／Backendへ直結しない。
- Node停止時に別compute hostや外部APIへ無言fallbackしない。
- localからexternalへの切替は外部送信と課金を変えるため、COREの許可と明示policyを必要とする。
- binaryが起動していること、targetがreadyであること、実生成できることを別々に検証する。
- 未知Agent、未対応Role、Target停止を同じunavailableへ丸めず、観測とrollback判断を分ける。

## Current and planned status

- `rencrow-llm`はmanifest上の`development` primary binaryである。
- `rencrow`、`rencrowctl`、`rencrow-portal`を含む実装済みcomponentのsource versionは
  現在40桁commit SHAへ固定している。release artifactの取得・checksum保証は
  `verified` releaseまで行わない。
- `rencrow-llm-node`はRenCrow LLM Runtimeの現行artifactとして、Gatewayと同じversionおよび
  contractで検証する。
