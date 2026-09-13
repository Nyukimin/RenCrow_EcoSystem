# 作業別の追加ルール

[AGENTS.md](../AGENTS.md)から、該当する作業の節だけ読む。共通のowner・権限・安全境界はAGENTS.mdを継承する。通常の文書編集のために運用・GUI・委譲手順を一括読込しない。本書は共通ルールを補う正本であり、module内部仕様を複製しない。

<a id="delegation"></a>
## 委譲する場合

- Astraが設計・owner・契約・依存順・受入を確定してから、Luna maxへ一つの完結した責務を渡す。曖昧な設計・正本探索・cross-module判断は渡さない。証拠収集は正確な問い・path／command・出力上限を指定したread-only作業にする。
- packetには目的／成功条件、ownerと対象file、現状証拠、許可差分、禁止事項、契約／不変条件、検証command、返却内容（変更file・差分要約・commandと結果・証拠・阻害要因）を含める。必要な参照だけ渡し、全会話を継承しない。大きければ完結する単位へ分ける。
- 子の読込は指定AGENTSチェーン・対象・直接依存に限定する。不足・矛盾・設計判断・対象外変更・検証不能は証拠を返して停止し、探索・scope・代替routeを拡大しない。
- 独立作業だけ並列化し、共有file・状態・契約・生成物は依存順に処理する。実装／修正後にAstraが実差分・範囲・正本境界・試験・統合影響をreviewし、その後に独立したLuna検証を割り当てる。共有資源がある場合もこの順序を守る。
- 最終責任はAstraに残る。子によるcommit・push・PR・restart・install・delete・破壊的／外部変更は、scope内でも親review後の独立した明示packetが必要。

<a id="llm-quality"></a>
## 決定的手法との品質比較

LLMを「品質優位性」で採用するときは、決定的baselineと同じ入力dataset・品質指標・失敗条件・費用／遅延／再現性／安全制約で比較し、十分な品質差と制約上の不利益を正当化する証拠を残す。差が不明・僅少ならCLIを選ぶ。「便利」「柔軟」「既存がLLM」だけでは採用理由にならない。意味判断による必須性と、数値比較による優位性を混同しない。

<a id="runtime"></a>
## process・配備・routeを扱う場合

- 固定port競合ではlistenerのowner・起動元・期待する正規ownerを特定し、portを動かさずprocess lifecycleを是正する。旧generation判定には実行file、完全なcommand line、service/cgroupまたは親process、設定path、listen endpoint、起動時刻を照合する。
- 同じowner・役割・設定の残留旧generationと確認できた場合だけ、正規service manager／owner CLIから停止する。新generationのreadiness・実request成功と旧generationの消滅まで検証する。owner・役割・設定・実行fileが異なるものは別processとして停止／削除せず、実consumer・競合・影響を報告する。似た名前だけで旧世代と判定しない。
- 変更前に正本仕様とactive configで入口→Gateway→Runtime→Backendのendpoint・認証・streaming・tool call・error契約を固定する。障害時は設定・credentials・module process・network・正規Runtime・Backend readiness・logsを調査してその経路を復旧し、旧proxyや短縮routeを正規へ昇格しない。
- 正規Gateway aliasの実requestで、用途に必要な初回／最終content、tool call、streaming event、typed errorを確認する。proxy前後のraw responseを比較し、field欠落・変換差があれば正常経路に採用しない。listener・HTTP 200・health・backend単体成功をroute互換性に換算しない。
- 配備はsource→build artifact→installed binary→active config→service PID→socket destination→実request receiptを照合する。active config、backup、example、disabled sectionを区別し、文字列残存だけでlive consumer／削除対象としない。
- port／routeを変更する実装では、固定port drift、旧endpointへのactive consumer/socketが0、全aliasの正規route smoke、credential非漏洩、再起動後のowner/readiness、利用主体からのE2E receiptを機械検査する。時間依存checkは期限・consumer付きで`deferred`にし、未確認のまま全体完了にしない。代替経路の成功を正規route／Agent-owned E2E成功と報告しない。

<a id="decision-gui"></a>
## 利用者固有の判断GUIを作る場合

- GUIは認証済ownerが未処理の判断対象を発見し、一回の明示操作で次状態を確定できるようにする。内部queueや無言の`blocked`へ隠さない。
- 表示内容は判断対象・必要理由・原文／Evidence・現状態・選択肢・推奨と根拠・各選択の影響／リスク・編集可能範囲・実行／拒否／保留・未処理件数／進捗・操作後receipt。任意filesystem path・SQL・owner外dataは公開しない。
- GUI送信は新しい認証済requestとして同期評価し、即時の終端状態とreceipt、CORE正本への反映、実利用経路までE2Eで確認する。policyで決定できる工程をGUI判断へ逃がさず、汎用human gateにしない。

<a id="local-tests"></a>
## ローカル検査を実行・変更する場合

- Windowsの正規入口は各repoの引数なし`scripts/test-local.ps1`。全repoは`RenCrow_CORE/scripts/test-rencrow-system.ps1`。GoのWindows planは`go vet ./...`と`go build ./...`を使い、`.test.exe`を生成・実行する`go test`は含めず、振る舞いtestはGitHub Actions Ubuntuで行う。
- `TEMP`／`TMP`／`TMPDIR`／`GOTMPDIR`とGo／Python／Node cacheをowner repoの`Tmp/test-runtime/`へ向け、system temp・user profileへ生成物を出さない。子processは親environmentに変更をmergeする（Python `{**os.environ, ...}`、Go `append(os.Environ(), ...)`、Node `{...process.env, ...}`）。
- 一時clean worktreeと検証済元treeは`git diff`／hashで内容を照合して証拠を再利用する。cold cacheでの重複testを行わない。
- timeout時は残留する当該test processを停止し、cache・network・security software・子processの停止点を診断する。未完了を明記し、ユーザー判断またはGitHub Actionsへ切り替える。`Tmp`内の実行fileもblockされた場合はpathとerrorを記録し、rename／反復で通そうとせずUbuntu CIへ移す。

<a id="paths"></a>
## Windowsの非ASCII path・文字化けを扱う場合

pathをfilesystem API（`pathlib.Path.rglob()`／`Get-ChildItem`等）で列挙し、そのpath objectを操作する。PowerShell／cmdへ非ASCII pathを直書きしない。`PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`、必要なPowerShell出力encodingでUTF-8 I/Oを保つ。表示が崩れても実Unicode名を確認し、本当の置換文字／文字化けと意図する名前が確定した場合だけrenameする。Gitのoctal escapeは破損ではなく、読取り表示にはlocalの`core.quotepath=false`を使える。
