# Pull前変更の仕様化と現行実装への再適用

2026-09-12。対象はPull前に退避した10 repository、54 fileの変更意図。
stashは履歴証拠として保持し、旧tree、旧ID、旧schemaを復元する入力にはしない。
この文書は再実装の追跡表であり、module内部仕様の別正本ではない。

## 正本と不変条件

標準Go配布、Ubuntu／Windows／macOS、外部compute、CUDA用WSL、共通healthは
[COREの標準Go配布境界](https://github.com/Nyukimin/RenCrow_CORE/blob/main/docs/04_アーキテクチャ概要.md#標準go配布境界)
にすでに定義されている。その仕様と現行module実装の不足を埋める。

- 現行のAgent、execution alias、Role profile、request／trace／task／session IDを維持する。
  healthの追加を理由にID生成、変換、binding、認証、attestation、migration、予約PORTを変更しない。
- Gatewayからのprobeも、設定済みowner Runtime経路と現在の認証方法を使う。
  Backendへの短絡、別model、fake成功、暗黙fallbackを追加しない。
- manifestのschema v4、source pin、runtime profile、deployment、coverage policyを維持する。
  runtime policyの追加は統合互換性の合格を意味しない。
- 実装と検証の対象はsource checkout。active config、service、稼働binaryへの配備は別工程。

## 要求と採用判断

| 要求 | stashの意図 | 現行仕様への実装判断・受入条件 |
| --- | --- | --- |
| R1 | 3 OS native Go配布 | 各owner READMEはCORE正本を参照する。既存Ubuntu test／Windows buildを維持し、不足するmacOS build/vetを追加する。Image／VisionはWindowsも追加する。CI定義と実際の各OS合格を区別する。 |
| R2 | 配布方針の機械検証 | EcoSystemのruntime policyに3 OS、Go primary、module境界、health、CUDA WSL制約を宣言する。binary／extensionにGo primaryの宣言を必須化。現行component情報は保持する。旧`exception_approval=ren-explicit`は採用せず、CORE正本とdeployment policyで定義する現行契約に合わせる。READMEの単語出現だけを適合証拠にはしない。 |
| R3 | livenessとreadinessの分離 | GAMES observer、Image、LLM Gateway／Runtime、STT、映画カタログsidecar、TTS、Visionに共通endpoint／JSONを実装する。対象停止時もlive=200、ready=503・unavailable。既存aliasの意味とmodule固有payloadを保つ。 |
| R4 | STT旧起動設定の維持 | 先頭`--config`／`-config`の旧CLIだけを現行`serve --config --listen`へ変換し、非推奨警告を返す。portは1..65535、不正引数はexit 2。現行migration-hook／config validate／serveは維持する。旧製品IDの互換層は追加しない。 |
| R5 | Vision設定の可搬化 | source defaultと配布sampleを`http://127.0.0.1:8084`へ揃える。明示されたprovider URL／token file／model aliasを優先し、既存hostのactive configは書き換えない。Go／比較用Pythonのdefaultと設定overrideを試験する。 |
| R6 | Workspaceの配置説明 | snapshotのUbuntu正本とWindows保管側の区別を維持。`wan-ubunts`は接続aliasとして残し、host表示名と混同しない。3 OSの可搬性とWSLの限定境界はCORE正本を参照する。 |

## healthのmodule別受入境界

| owner | readinessが証明する対象 | 最新版で保護する境界 |
| --- | --- | --- |
| GAMES | 初期化済みObserverとStoreが受付可能 | CORE Agentによるgameplay完了の証拠にはしない。game/session IDとlaunch経路はそのまま。 |
| Image | 設定済みForge側healthが成立 | 現行profile、保存先、生成ID、request検証を維持。 |
| LLM Gateway | 設定済みnetwork targetのmodels endpoint到達、またはCodex CLI配置 | 認証はenv/file双方を既存adapterで解決。CLI配置はloginや生成成功を証明しない。alias/Role binding、queue、streamingを維持。 |
| LLM Runtime | 設定済みBackendの既存probeが成立 | readinessは既存bearer認証内。公開liveは状態のみ。compat ingressとattestationの認証を維持。 |
| STT | default targetのHTTP成功かつready=true | targetの非2xx＋ready=trueもunavailable。転写payloadとID伝播を維持。 |
| 映画カタログ | 初期化済みsidecarがcrawl requestを受付可能 | 外部サイトの将来の成功やCORE DBへのimportを証明しない。 |
| TTS | 設定済みtarget群のhealth/readyが成立 | ready=false時のstartingをunavailableへ統一。owner認証、WAV経路、pronunciation stateを維持。 |
| Vision | 現行Provider.Healthの判定 | provider認証、公開alias、request ID、media制約を維持。Goだけを標準起動手順にする。 |

## 工程と検証

- CLI: Git差分・stash照合、schema検証、format、build／vet、既存runner。入力は現行treeと固定stash ID、
  出力は差分とexit status。失敗はlogへ残し、成功へ丸めない。各owner moduleで実行する。
- LLM: 旧変更の目的と現行契約の意味照合、採否・設計判断。ID変更と旧仕様の意味判断が必要なため使用する。
  出力は本追跡表とowner仕様。判断不能なら未確定とし、CLI結果で実装を照合する。
- Boundary: 現行ID／認証／route／schemaと変更範囲の差分確認。対象外への変更、stash削除、配備は行わない。

Windowsはrepository-local runnerを使用し、Goはvet/build、Pythonは対象suiteを実行する。
Goの振る舞いは既存Ubuntu CI、追加したmacOS jobは実行結果をもって確認する。
未pushのローカル差分を既存mainのCI合格で代用しない。配備・実ActorのE2Eはsource検証と分けて報告する。

現行runnerの事前検査で、LLMのadvisor Python test、GAMESのinstaller契約test、
Visionの一部Go testがtest planの対象から漏れていることを確認した。
既存testを削除・skipせず、各owner planへ正しい実行step／対象を追加して検証入口を整合させる。

LLM advisorの既存PID生存確認は`os.kill(pid, 0)`を使用していた。
Windowsでは照会にならず終了操作になるため、query-onlyのprocess handleによる確認へ分岐する。
自processと別processを終了させない回帰testを追加する。認証、LLM呼出し、lockの所有境界は変更しない。
このOS差は[Python公式のos.kill仕様](https://docs.python.org/3/library/os.html#os.kill)で確認した。
Windowsのlock file読込／削除競合は、所有PIDを再確認した短いsharing-violation retryと
既存acquisition deadline内の待機で扱う。権限変更、security除外、無期限retryは追加しない。

## ローカル検証結果

2026-09-12、Windows source checkoutで確認。

| owner | 確認結果 |
| --- | --- |
| CMD | repository-local runnerのGo vet/build成功 |
| EcoSystem | Python 109 test成功、schema v4 manifest validator成功 |
| GAMES | installer contract、Go vet/build成功 |
| Image | installer contract、Python 7 test、Go vet/build成功 |
| LLM | advisor Python 53 test、Go vet/build成功 |
| STT | Go vet/build成功 |
| 映画カタログsidecar | Tools runnerの対象stepでGo vet/build成功 |
| TTS | Go vet/build成功 |
| Vision | Python 17 test成功・既存live E2E 1件skip、Go vet/build成功 |
| Workspace | READMEのみ。実装／稼働snapshotの変更なし |

8 workflowのYAML構造と追加jobの所属、全repositoryの`git diff --check`、
manifestの既存ID／pin／runtime profile／deploymentの保持、10件のstashの保持を確認。
CORE／PORTALのsource変更はない。COREの既存未追跡dataは保持した。

UbuntuのGo behavior test、macOS CI、実backendと実Actorを通すE2E、配備と再起動後確認は未実施。
従って、ここで示すのはローカルsource検証までであり、3 OS互換性や運用受入の完了ではない。
