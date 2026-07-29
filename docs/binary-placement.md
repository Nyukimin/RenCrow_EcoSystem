# Binary placement

## 目的

RenCrowの各binaryを、役割の異なるhostへ重複配置せず、状態と設定の正本を一つに保つ。
EcoSystemは配置規則と検証済み組み合わせを記録するが、processを起動・制御する
runtime control planeにはならない。

## Host role

| host role | 配置する主なbinary | 配置しないもの |
| --- | --- | --- |
| control host | `rencrow`、`rencrow-llm`、必要なcapability Gateway | Model weights、GPU固有Backendを必須にしない |
| compute host | `rencrow-llm-node`、Backend、Model | CORE、PORTAL、EcoSystem、Agent Memory |
| interaction host | `rencrowctl`、`rencrow-portal`、将来の`rencrow-assistant` | 物理LLM URL、Model path、provider credential |
| operator workstation | `rencrowctl` | runtime状態の正本 |
| external provider | module-owned adapterから利用するAPI／Agent Runtime | RenCrow binaryの配置を前提にしない |

同じ物理hostが複数roleを兼ねてもよいが、binaryの責務とConfig正本は統合しない。

## Standard topology

```text
control host
  rencrow
  rencrow-llm
  trusted Codex subscription runtime
       |
       +-> compute host A
       |     rencrow-llm-node
       |     configured Backend / Model
       |
       +-> compute host B
       |     rencrow-llm-node
       |     configured Backend / Model
       |
       `-> external LLM API

interaction host
  rencrowctl / rencrow-portal
       -> CORE public API
```

`rencrow-llm` central GatewayはRenCrow環境ごとに一つを標準とする。
`rencrow-llm-node`はModel／GPUを持つcompute hostごとに一つ置く。
NodeはRenCrow_LLM moduleとrelease contractを共有し、Model別の独立moduleや
repositoryを作らない。

配置とは別に、推論の論理構造は次の3層を維持する。

```text
Agent -> Execution Role -> Inference Target
```

COREがAgentからExecution Roleへの割り当てを所有し、RenCrow_LLMがRole profileから
Inference Targetを解決する。Role profileはRoleに付随するtarget、thinking、sandbox、
capacity設定であり、独立した第4層ではない。
Agent IDとExecution Role identityは安定contract、TargetとRole profile revisionは
deploymentごとに交換可能な設定とする。

## Placement rules

### Control host

- `rencrow`をAgent、Persona、Memory、route、approvalの正本として一つ置く。
- `rencrow-llm`をExecution Role profile、target mapping、adapter、正規化の中央境界として置く。
- Codex subscription credentialを使う場合は、credentialを保持するtrusted host上で
  Codex runtimeを動かし、別compute hostへcredentialを複製しない。
- 外部API credentialはmoduleのsecret store／environment referenceで管理し、
  EcoSystem manifestや配布Configへ平文保存しない。

### Compute host

- host supervisorが`rencrow-llm-node`を常駐化する。
- NodeがBackend process、Model readiness、GPU/capacity、host-local logを管理する。
- Backendは原則loopback bindとし、Nodeの認証済みdata planeだけをcontrol hostへ公開する。
- Model weights、Backend binary、runtime dependency、Model pathはcompute hostが所有する。
- control hostからSSH、`taskkill`、`pkill`でBackendを直接管理しない。

WindowsではWindows ServiceまたはTask Scheduler、macOSではlaunchd、Linuxではsystemdを
host supervisorとして使用できる。supervisorはNodeを監視し、NodeがBackendを監視する。

### Interaction host

- PORTALとCMDはCORE Public APIへ接続する。
- physical target、Node、Backend port、Model名を設定しない。
- PORTALはDebug／Ops／LLM管理を中継しない。
- CMDの管理commandはCOREの認証済みPublic APIだけをfacadeとして呼ぶ。

## Artifact rule

- `runtime.primary`はmanifestで利用可能性とchecksumを検証する配布artifactである。
- planned binaryを存在するrelease artifactとしてmanifestへ登録しない。
- `rencrow-llm-node`はRenCrow_LLMのmodule-owned追加artifactとしてGatewayと同じ
  version、status schema、Backend contractで検証する。
- Model weightsとBackendはGo binaryへ同梱しない。
- 同一moduleのGatewayとNodeはversionを揃え、status schemaとBackend contractの
  compatibilityを統合試験する。

## Config ownership

| Config | 配置 |
| --- | --- |
| Agent、Agent -> Execution Role、Persona、Memory、外部送信許可 | CORE control host |
| Execution Role profile、Role -> target、provider secret reference | LLM central Gateway |
| Node endpoint、Node certificate／token reference | LLM central Gateway |
| Backend command、Model path、GPU、local port | compute host Node |
| PORTAL URL、CMD接続先 | interaction host |
| component version、artifact checksum、互換性 | EcoSystem manifest |

## Target配置変更とcutover

- Agent／Role bindingが同じままTarget host、provider、Modelを変更しても、Agent、
  Execution Role、現行execution aliasをrenameしない。
- RenCrow_LLM側で新しいRole profile revisionを作り、cutover前にTarget readinessと
  実生成を確認する。
- Model、tokenizer、chat template、context prefixが変わる場合は旧session／KVを
  再利用しない。
- localからexternalへの変更は外部送信、課金、保持policyを変えるため、COREの許可と
  deployment承認を必要とする。
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
- `rencrow-llm-node`はRenCrow_LLMの追加artifactとして、Gatewayと同じversionおよび
  contractで検証する。
