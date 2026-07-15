# Modules

| Repository | Product role | Distribution | Runtime relationship |
| --- | --- | --- | --- |
| `RenCrow_EcoSystem` | 公式入口、構成、互換性、統合 release | metadata/docs | 各 release を参照する。実行されない |
| `RenCrow_CORE` | 中核server、Debug Viewer、Persona、Memory、承認、routing | required binary | runtimeの中心 |
| `RenCrow_PORTAL` | 外部利用者向けview/lab Web UI | optional/recommended binary | allowlist内のCORE Public APIだけを中継 |
| `RenCrow_CMD` | 管理・操作CLI (`rencrowctl`) | optional/recommended binary | CORE／PORTAL起動とCORE Public API操作 |
| `RenCrow_LLM` | LLM model / role connection | optional service | CORE から契約経由で利用 |
| `RenCrow_STT` | 音声認識 | optional service | 認識結果を CORE に返す |
| `RenCrow_TTS` | 音声合成 | optional service | CORE から発話要求を受ける |
| `RenCrow_Vision` | 画像・動画解析 | optional service | CORE から解析要求を受ける |
| `RenCrow_GAMES` | world、rules、Replay、Observer | optional extension | RenCrowBridge から CORE に接続 |
| `RenCrow_Tools` | 開発、変換、検証、browser sidecar | tooling | CORE / Worker と開発運用を補助 |
| `RenCrow_Image` | 画像生成と学習素材制作 | offline assets | 承認した成果物を各 module が利用 |
| `RenCrow_Workspace` | 非 secret 設定・prompt template | template | CORE の初期 workspace 候補 |

## Ownership rule

各 repository は自分の source、詳細仕様、build、test、CI、tag、Release を
所有します。EcoSystem はそれらを複製せず、repository と immutable version を
参照します。

## CORE, PORTAL and CMD

`RenCrow_CORE`がserver behavior、状態、`/viewer/*` API、Debug Viewerの正本です。
`RenCrow_PORTAL`は外部利用者向けの`view`／`lab`だけを所有し、debug/admin APIを中継しません。
`RenCrow_CMD`は`rencrowctl`としてCOREとPORTALを起動し、CORE APIをCLIから利用します。PORTALとCMDはruntime状態を別実装として所有しません。
