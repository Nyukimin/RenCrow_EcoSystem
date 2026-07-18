# Modules

| Repository | Product role | Distribution | Runtime relationship |
| --- | --- | --- | --- |
| `RenCrow_EcoSystem` | 公式入口、構成、互換性、統合 release | metadata/docs | 各 release を参照する。実行されない |
| `RenCrow_CORE` | 中核server、Debug Viewer、Persona、Memory、承認、routing | required binary | runtimeの中心 |
| `RenCrow_ASSISTANT` | 個人・家族向け生活Routine、PUSH、端末配信、COREへのTask移譲 | optional/recommended binary | Device／PORTALとCOREの間で生活アシスタント機能を提供 |
| `RenCrow_PORTAL` | 外部利用者向けview/live/lab Web UI | optional/recommended binary | allowlist内のCORE Public APIだけを中継 |
| `RenCrow_CMD` | 管理・操作CLI (`rencrowctl`) | optional/recommended binary | CORE／ASSISTANT／PORTAL起動と許可されたPublic API操作 |
| `RenCrow_LLM` | AgentをLLM実体へ接続しBackend差を吸収するGo Gateway | optional binary + external compute | COREから契約経由で利用。LLM targetは別途用意 |
| `RenCrow_STT` | 公開音声契約と認識target差を吸収するGo Gateway | optional binary + external compute | COREから音声を受け、STT targetの結果を正規化 |
| `RenCrow_TTS` | character／style／voiceを解決して合成target差を吸収するGo Gateway | optional binary + external compute | COREから発話要求を受け、TTS targetへ接続 |
| `RenCrow_Vision` | 画像・動画解析 | optional service | CORE から解析要求を受ける |
| `RenCrow_GAMES` | world、rules、Replay、Observer | optional extension | RenCrowBridge から CORE に接続 |
| `RenCrow_Tools` | 開発、変換、検証、browser sidecar | tooling | CORE / Worker と開発運用を補助 |
| `RenCrow_Image` | 画像生成と学習素材制作 | offline assets | 承認した成果物を各 module が利用 |
| `RenCrow_Workspace` | 非 secret 設定・prompt template | template | CORE の初期 workspace 候補 |

## Ownership rule

各 repository は自分の source、詳細仕様、build、test、CI、tag、Release を
所有します。EcoSystem はそれらを複製せず、repository と immutable version を
参照します。

## RenCrow_LLM runtime boundary

`RenCrow_LLM`のprimary artifactはGo binary `rencrow-llm`です。Backendは独立moduleではなく、Model、重み、KV、計算資源とともにLLM targetへ付随します。現行Python role proxyはGo移行中のcompatibility runtimeであり、primary binaryへ同梱しません。

## RenCrow_STT / RenCrow_TTS runtime boundary

`RenCrow_STT`のprimary artifactは`rencrow-stt`、`RenCrow_TTS`は`rencrow-tts`です。
認識／合成engine、Model、重み、decoder／codec、音声資産、GPU／CPUはそれぞれの
external compute targetへ付随し、Go binaryへ同梱しません。現行Python serverと
in-process providerは、Go API parityと実機cutoverが終わるまでcompatibility runtime
として残します。

## CORE, PORTAL and CMD

`RenCrow_CORE`がserver behavior、状態、`/viewer/*` API、Debug Viewerの正本です。
`RenCrow_PORTAL`は外部利用者向けの`view`／`live`／`lab`を所有し、debug/admin APIを中継しません。
COREとの接続、active-control、TTS／STT、公開境界は
[PORTAL–CORE contract](portal-core-contract.md)を参照してください。
`RenCrow_CMD`は`rencrowctl`としてCORE、ASSISTANT、PORTALを起動し、許可されたPublic APIをCLIから利用します。ASSISTANT起動はplannedで、現行CLIでは未実装です。PORTALとCMDはruntime状態を別実装として所有しません。

## ASSISTANT, CORE, PORTAL and devices

`RenCrow_ASSISTANT`は生活Routine、personal／family scope、proactive delivery、
acknowledgementを所有するGo serviceです。Agent人格、Agent Memory、Knowledge、複雑な
TaskはCOREへ委譲します。PORTALはASSISTANTの状態を表示・操作するclientであり、
Deviceはcapabilityを申告してPUSHを受ける薄いclientです。横断境界は
[ASSISTANT boundary](assistant-boundary.md)を参照してください。
