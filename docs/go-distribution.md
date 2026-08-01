# Go配布方針と実装メモ

Status: in progress。COREの映画カタログsidecar境界とRenCrow_ToolsのGo gatewayは実装済みです。
Vision／ImageのGo Gateway化とrelease artifactの確定は継続課題です。

## 目的

標準インストールの利用者側には、RenCrowのGoバイナリ、設定、必要な静的資産だけを配置する。
Python／Node.jsは標準インストールへ持ち込まず、必要な機能だけをoptional sidecarまたは
外部compute hostへ分離する。Web UIのJavaScriptはブラウザで実行し、Node.js runtimeとは区別する。

## 標準配布に含めるもの

| Component | 配布方針 | 実装状況 |
| --- | --- | --- |
| `RenCrow_CORE` | Go binary | 現行Go。通常runtimeはPython／Nodeを必須にしない |
| `RenCrow_CMD` | Go binary | 現行Go |
| `RenCrow_PORTAL` | Go binary + browser assets | `go:embed`で配布。Node.js不要 |
| `RenCrow_GAMES` | Go extension + browser assets | `go:embed`で配布。Node.js不要 |
| `RenCrow_LLM` | Go Gateway／Runtime binary | 現行Go。Backend／Modelは外部compute |
| `RenCrow_STT` | Go Gateway binary | 現行Go。STT targetは外部compute |
| `RenCrow_TTS` | Go Gateway binary | 現行Go。TTS targetは外部compute |
| `RenCrow_Vision` | Go Gateway binaryへ移行予定 | 現在はPython service |
| `RenCrow_Image` | Go Gateway binaryへ移行予定 | 現在はPython service |

`RenCrow_Vision`はWild backend、`RenCrow_Image`はForgeNeo／ComfyUI／Z-Imageへ接続する
interfaceであり、modelやGPU計算をGo binaryへ同梱する方針ではない。

## 標準配布に含めないもの

- `RenCrow_Tools`の開発、変換、検証ツール
- Browser ActorのNode.js／Playwright sidecar
- WebwrightのPython sidecar
- `rencrow-data`のPython data pipeline
- LLM／STT／TTS／Vision／Imageの物理Backend、Model、weights、GPU runtime

未配置のoptional capabilityは、COREで成功扱いにせず、`disabled`または`unavailable`として
観測・表示する。optional capabilityのために標準installerがPython／Nodeを導入しない。

## 映画カタログの責務

映画カタログはCOREの機能として扱う。ただし、外部サイトの巡回はTool／sidecarへ分離する。

- CORE: catalog domain、SQLiteの正本、検索、評価、好み、Public API、policy、trace、監査、import
- Tool／sidecar: 映画.com巡回、robots.txt、rate limit、再試行、HTML解析、raw artifact生成
- production DB: Toolが直接正本化せず、staging JSONL等をCOREが検証してimportする

COREの映画カタログbackfillは、`MovieCatalogCrawler`契約とsidecar clientへ分離済みです。
CrawlerのGo化はoptional sidecarの実装選択であり、catalog domainをCOREから移動しない。

## 実装メモ

### P0: Go Gateway化

1. `RenCrow_Vision`にGoのserver entrypointを追加する。
2. `RenCrow_Image`にGoのserver entrypointを追加する。
3. 既存のHTTP endpoint、health、error、logging、request ID／trace IDの契約を維持する。
4. Visionの動画処理で使うFFmpeg／FFprobeは、Python依存とは分けて外部実行物として扱う。
5. Python実装は移行期間のcontract test／比較用に残し、標準artifactの起動経路にはしない。

### P1: COREの外部取得境界（完了）

1. `movie_catalog_handler.go`と`moviecatalog/backfill.go`から`python3`直接起動を外した。
2. `MovieCatalogCrawler`のrequest／responseとstaging artifact契約を定義した。
3. COREがstagingを検証し、自分のmovie catalog DBへimportする。
4. sidecar未配置時は明示的な`unavailable`を返す。
5. Browser Actor／Webwrightは既存のoptional sidecar境界を維持し、標準runtimeへ取り込まない。

### P2: 配布・統合

1. Go Gatewayのartifact、checksum、対応OS／architectureが確定してから`ecosystem.yaml`へ反映する。
2. installerは標準profileとoptional profileを分ける。
3. LLM／STT／TTS／Vision／Imageのexternal compute配置とhealth／E2E確認を別host単位で行う。
4. CORE、CMD、PORTAL、GAMESのGo build、Vision／ImageのGo build、sidecarなしの標準起動を受入条件にする。

## 変更しない範囲

- PORTAL／GAMESのブラウザJavaScriptをGoへ書き換えない。
- LLM／STT／TTS Gatewayを別言語へ移植しない。
- Workspaceをruntime serviceへ変更しない。
- Python／Nodeのoptional Toolを標準installerへ同梱しない。
