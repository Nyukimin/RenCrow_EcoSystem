# Modules

| Repository | Product role | Distribution | Runtime relationship |
| --- | --- | --- | --- |
| `RenCrow_EcoSystem` | 公式入口、構成、互換性、統合 release | metadata/docs | 各 release を参照する。実行されない |
| `RenCrow_CORE` | 中核server、Debug Viewer、Persona、Memory、同期policy判定、routing | required binary | runtimeの中心 |
| `RenCrow_ASSISTANT` | 個人・家族向け生活Routine、PUSH、端末配信、COREへのTask移譲 | planned binary | 実装後はDeviceとCOREの間で生活アシスタント機能を提供 |
| `RenCrow_PORTAL` | 外部利用者向けChat／IdleChat／Games Web UI、PuruPuru overlay | optional/recommended binary | allowlist内のCORE Public APIだけを中継 |
| `RenCrow_CMD` | CORE Public API用CLI (`rencrowctl`) | optional/recommended binary | CORE Public API操作とCORE／PORTALのprocess entrypoint |
| `RenCrow_LLM` | Execution RoleをBackend／Modelへ接続するRenCrow LLM Gateway／RenCrow LLM Runtime | optional Gateway binary + Runtime binary + external compute | 正式経路は`CORE -> Gateway -> Runtime -> Backend -> Model`。compute hostへRuntime、Backend、Modelを配置 |
| `RenCrow_STT` | 公開音声契約と認識target差を吸収するGo Gateway | optional binary + external compute | COREから音声を受け、STT targetの結果を正規化 |
| `RenCrow_TTS` | character／style／voiceを解決して合成target差を吸収するGo Gateway | optional binary + external compute | COREから発話要求を受け、TTS targetへ接続 |
| `RenCrow_Vision` | 画像・動画認識interface | optional Go binary + external compute | `rencrow-vision`がCOREからraw mediaを受け、Wildで解析して正規化結果を返す |
| `RenCrow_GAMES` | world、rules、title-local controller、決定論的executor、Replay、Observer | optional extension | COREから起動され、resultとObserverFrameをCOREへ返す |
| `RenCrow_TRADE` | 金融Source、学習、Replay、銘柄選別、撤退契約、Portfolio risk、TradeGate、Ledger | optional Go binary | CORE private contract配下。Broker／Paper／LIVEは未実装 |
| `RenCrow_Tools` | 開発、変換、検証、browser sidecar | tooling | CORE / Worker と開発運用を補助 |
| `RenCrow_Image` | 描画・画像生成interface | optional Go binary + external compute | `rencrow-image`がCOREから生成要求を受け、ForgeNeo／Z-Image等のbackendへ接続 |
| `RenCrow_Workspace` | `~/.rencrow/workspace`のportableな非secret snapshot | snapshot | backup／復旧用。`~/.rencrow/workspace`自体が実行時の正本であり、runtime serviceではない |

## Ownership rule

各 repository は自分の source、詳細仕様、build、test、CI、tag、Release を
所有します。EcoSystem はそれらを複製せず、repository と immutable version を
参照します。

## RenCrow_LLM runtime boundary

`RenCrow_LLM`のprimary artifactはRenCrow LLM Gatewayとしてcontrol hostへ置く
Go binary `rencrow-llm`です。compute hostへ置く`rencrow-llm-node`はRenCrow LLM Runtimeの
現行binaryであり、同じmoduleの追加artifactとして別repositoryにしません。
Backendは独立moduleではなく、Runtime配下でModel、重み、KV、計算資源を使用します。
詳細配置は[Binary placement](binary-placement.md)を参照してください。

AgentからExecution Roleへの割当はCOREが所有します。推論経路は
`CORE -> RenCrow LLM Gateway -> RenCrow LLM Runtime -> Backend -> Model`であり、
GatewayがRoleからRuntime、RuntimeがBackend／Modelへのmappingを所有します。
Execution RoleはCOREとRenCrow_LLM間の論理契約であり、物理Model名ではありません。

`RenCrow_GPT120B`、`RenCrow_Qwen36_27B`、`RenCrow_Gemma4`は、独立Git管理される
host固有のLLM external runtime profileです。`ecosystem.yaml`の`runtime_profiles`で
ownerを`llm`として宣言しますが、独立module、Agent、routing ownerにはしません。

## RenCrow_STT / RenCrow_TTS runtime boundary

`RenCrow_STT`のprimary artifactは`rencrow-stt`、`RenCrow_TTS`は`rencrow-tts`です。
認識／合成engine、Model、重み、decoder／codec、音声資産、GPU／CPUはそれぞれの
external compute targetへ付随し、Go binaryへ同梱しません。
COREはRenCrow_STT／RenCrow_TTS Gatewayだけを参照し、Gatewayが各targetへ接続します。

## CORE, PORTAL, CMD and ASSISTANT

`RenCrow_CORE`がserver behavior、状態、`/viewer/*` API、Debug Viewerの正本です。
`RenCrow_PORTAL`は外部利用者向けの`Chat`／`IdleChat`／`Games`を所有し、debug/admin APIを中継しません。
`IdleChat`は読み取り専用、`Chat`と`Games`は各modeの明示allowlist内だけ操作可能です。
COREとの接続、active-control、TTS／STT、公開境界は
[PORTAL–CORE contract](portal-core-contract.md)を参照してください。
`RenCrow_CMD`は`rencrowctl`としてCORE Public APIだけを利用し、COREとPORTALの
process entrypointを提供します。PORTALとCMDはruntime状態を別実装として所有しません。

PORTALはWeb renderer、CMDはterminal clientとして、COREのChat／IdleChat／Games／event等の
共通意味論を利用します。ASSISTANTはproactive triggerとDevice deliveryを加える
plannedのstateful application serviceです。詳細は
[Interaction surfaces](interaction-surfaces.md)を参照してください。

Tool／Skill／MCPの追加反映では、COREがsource検証、policy、Runtime Capability
Snapshot、durable receipt、再起動後検証を所有します。CMDは採用済みの
`rencrowctl capability apply|status`から認証済みCORE Public APIを呼ぶfacadeだけを
所有します。Toolsは再利用可能なexecutable helper、Workspaceはportable sourceを
所有しますが、どちらもCapability control plane、Snapshot、receipt、CORE再起動を
所有しません。詳細はCORE正本の[Capability revisionとapply／restart境界](https://github.com/Nyukimin/RenCrow_CORE/blob/main/docs/04_%E3%82%A2%E3%83%BC%E3%82%AD%E3%83%86%E3%82%AF%E3%83%81%E3%83%A3%E6%A6%82%E8%A6%81.md#capability-revision%E3%81%A8applyrestart%E5%A2%83%E7%95%8C)と
[Capability Applyとstatus](https://github.com/Nyukimin/RenCrow_CORE/blob/main/docs/06_Public_API%E4%BB%95%E6%A7%98.md#capability-apply%E3%81%A8status)を参照します。
CLI、API、receipt store、supervisorは現時点で採用済み・未実装です。

DBをAgent能力として扱うときは、COREがsemantic DB capability catalog、用途別の
`movie_catalog.lookup`／`glossary.lookup`、Debug ViewerのDB Catalogを所有します。
RenCrow_ToolsのMovie Catalog gatewayはoptionalな外部crawl artifact providerであり、
DB query、catalog、control planeの所有者ではありません。詳細契約はCORE正本の
[DB semantic capability境界](https://github.com/Nyukimin/RenCrow_CORE/blob/main/docs/04_%E3%82%A2%E3%83%BC%E3%82%AD%E3%83%86%E3%82%AF%E3%83%81%E3%83%A3%E6%A6%82%E8%A6%81.md#agent-runtime-capability-catalog)
に従います。

## ASSISTANT, CORE, PORTAL and devices

`RenCrow_ASSISTANT`は生活Routine、personal／family scope、proactive delivery、
acknowledgementを所有するplannedのGo serviceです。Agent人格、Agent Memory、
Knowledge、複雑なTaskはCOREへ委譲します。Deviceはcapabilityを申告してPUSHを受ける
薄いclientです。横断境界は
[ASSISTANT boundary](assistant-boundary.md)を参照してください。

## Vision and image boundaries

画像・動画認識は`CORE -> RenCrow_Vision -> Wild backend -> RenCrow_Vision -> CORE`、
画像生成は`CORE -> RenCrow_Image -> ForgeNeo / Z-Image`を正規経路とします。
COREはraw mediaをWild／RenCrow_LLMへ直接送りません。ForgeNeo、ComfyUI、
Z-Image等のbackend endpoint、Model、workflow、生成parameterもCOREへ複製しません。

Vision／Imageの標準artifactは実装済みのGo Gatewayです。Python実装はdevelopment、
contract比較、移行用として残しますが、標準installerの必須runtimeにはしません。
Wild、ForgeNeo、ComfyUI、Z-Image、Model、weights、GPU runtimeはexternal computeとして
Go binaryへ同梱しません。詳細な統合状態は[Go distribution](go-distribution.md)を参照してください。

## CORE and GAMES boundary

ゲーム開始は`CORE Agent -> POST /viewer/games/launch -> GAMES Observer`です。
起動後はCORE上の対象Agentが各turnの行動を決定し、GAMESのdeterministic executorが
検証して実行し、resultとObserverFrameをCOREへ返します。COREは
`/viewer/games/observer`でGAMES Observerをユーザーへproxyし、resultを候補記憶へ
記録します。

CORE／LLMはworld stateを直接変更せず、GAMESは本番LLM provider、Persona、
Recall、confirmed memory、起動意思を所有しません。
