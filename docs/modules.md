# Modules

| Repository | Product role | Distribution | Runtime relationship |
| --- | --- | --- | --- |
| `RenCrow_EcoSystem` | 公式入口、構成、互換性、統合 release | metadata/docs | 各 release を参照する。実行されない |
| `RenCrow_CORE` | 中核server、Debug Viewer、Persona、Memory、承認、routing | required binary | runtimeの中心 |
| `RenCrow_ASSISTANT` | 個人・家族向け生活Routine、PUSH、端末配信、COREへのTask移譲 | optional/recommended binary | Device／PORTALとCOREの間で生活アシスタント機能を提供 |
| `RenCrow_PORTAL` | 外部利用者向けChat／IdleChat Web UI | optional/recommended binary | allowlist内のCORE Public APIだけを中継。旧view／live／labは拒否 |
| `RenCrow_CMD` | 管理・操作CLI (`rencrowctl`) | optional/recommended binary | CORE／ASSISTANT／PORTAL起動と許可されたPublic API操作 |
| `RenCrow_LLM` | Execution Role profileとInference Targetを接続するcentral Gateway／Host Node | optional binary + node + external compute | COREはAgentからRoleを選びcentral Gatewayを利用。compute hostはNodeとtargetを配置 |
| `RenCrow_STT` | 公開音声契約と認識target差を吸収するGo Gateway | optional binary + external compute | COREから音声を受け、STT targetの結果を正規化 |
| `RenCrow_TTS` | character／style／voiceを解決して合成target差を吸収するGo Gateway | optional binary + external compute | COREから発話要求を受け、TTS targetへ接続 |
| `RenCrow_Vision` | 画像・動画認識interface | optional service | COREからraw mediaを受け、Wildで解析して正規化結果を返す |
| `RenCrow_GAMES` | world、rules、決定論的executor、Replay、Observer | optional extension | COREから起動され、ターン判断と結果だけをRenCrowBridgeでCOREへcallback |
| `RenCrow_Tools` | 開発、変換、検証、browser sidecar | tooling | CORE / Worker と開発運用を補助 |
| `RenCrow_Image` | 描画・画像生成interface | optional service | COREから生成要求を受け、ForgeNeo／Z-Image等のbackendへ接続 |
| `RenCrow_Workspace` | Ubuntu runtime workspaceの非secret snapshot | snapshot | backup／復旧用。runtime workspace自体が正本 |

## Ownership rule

各 repository は自分の source、詳細仕様、build、test、CI、tag、Release を
所有します。EcoSystem はそれらを複製せず、repository と immutable version を
参照します。

## RenCrow_LLM runtime boundary

`RenCrow_LLM`の現行primary artifactはcontrol hostへ置くGo binary`rencrow-llm`です。
compute hostへ置く実装済み`rencrow-llm-node`は同じmoduleの追加artifactとし、別repositoryに
しません。RTX5060／Macへの初回配布は完了し、production GatewayのNode cutoverは移行中です。
Backendは独立moduleではなく、Model、重み、KV、計算資源とともにLLM targetへ付随します。
現行Python role proxy／management runtimeは移行用compatibility runtimeであり、
primary binaryへ同梱しません。詳細配置は[Binary placement](binary-placement.md)を参照してください。

論理構造は`Agent -> Execution Role -> Inference Target`の3層です。AgentからRoleへの
割当はCORE、Role profileとRoleからTargetへのmappingはRenCrow_LLMが所有します。
Chat、ChatWorker、Worker、Wild、Heavyは廃止対象の旧port名ではなくExecution Roleです。

## RenCrow_STT / RenCrow_TTS runtime boundary

`RenCrow_STT`のprimary artifactは`rencrow-stt`、`RenCrow_TTS`は`rencrow-tts`です。
認識／合成engine、Model、重み、decoder／codec、音声資産、GPU／CPUはそれぞれの
external compute targetへ付随し、Go binaryへ同梱しません。現行Python serverと
in-process providerが残っていても、COREのproduction経路には使用しません。
COREはRenCrow_STT／RenCrow_TTS Gatewayだけを参照し、Gatewayが各targetへ接続します。

## CORE, PORTAL, CMD and ASSISTANT

`RenCrow_CORE`がserver behavior、状態、`/viewer/*` API、Debug Viewerの正本です。
`RenCrow_PORTAL`は外部利用者向けの`Chat`／`IdleChat`を所有し、debug/admin APIを中継しません。
`IdleChat`は読み取り専用、`Chat`は明示allowlist内だけ操作可能です。旧`view`／`live`／`lab`
は受理しません。
COREとの接続、active-control、TTS／STT、公開境界は
[PORTAL–CORE contract](portal-core-contract.md)を参照してください。
`RenCrow_CMD`は`rencrowctl`としてCORE、ASSISTANT、PORTALを起動し、許可されたPublic APIをCLIから利用します。ASSISTANT起動はplannedで、現行CLIでは未実装です。PORTALとCMDはruntime状態を別実装として所有しません。

PORTALはWeb renderer、CMDはterminal renderer、ASSISTANTはproactive triggerとDevice
deliveryを加えたInteraction profileとして、COREのChat／IdleChat／event等の共通意味論を
利用します。ASSISTANTだけは生活領域のstateful application serviceであり、単なるrenderer
ではありません。詳細は[Interaction surfaces](interaction-surfaces.md)を参照してください。

## ASSISTANT, CORE, PORTAL and devices

`RenCrow_ASSISTANT`は生活Routine、personal／family scope、proactive delivery、
acknowledgementを所有するGo serviceです。Agent人格、Agent Memory、Knowledge、複雑な
TaskはCOREへ委譲します。PORTALはASSISTANTの状態を表示・操作するclientであり、
Deviceはcapabilityを申告してPUSHを受ける薄いclientです。横断境界は
[ASSISTANT boundary](assistant-boundary.md)を参照してください。

## Vision and image boundaries

画像・動画認識は`CORE -> RenCrow_Vision -> Wild backend -> RenCrow_Vision -> CORE`、
画像生成は`CORE -> RenCrow_Image -> ForgeNeo / Z-Image`を正規経路とします。
COREはraw mediaをWild／RenCrow_LLMへ直接送りません。ForgeNeo、ComfyUI、
Z-Image等のbackend endpoint、Model、workflow、生成parameterもCOREへ複製しません。

## CORE and GAMES boundary

ゲーム開始は`CORE Agent / LLM -> POST /viewer/games/launch -> GAMES Observer`、
ターン判断は`GAMES -> RenCrowBridge -> CORE -> RenCrow_LLM -> GAMES`です。
GAMESは返された`BrainDecision`を検証して決定論的に実行し、ObserverFrameと
TurnResultを生成します。COREは`/viewer/games/observer`でGAMES Observerを
ユーザーへproxyし、resultを候補記憶へ記録します。

CORE／LLMはworld stateを直接変更せず、GAMESは本番LLM provider、Persona、
Recall、confirmed memory、起動意思を所有しません。
