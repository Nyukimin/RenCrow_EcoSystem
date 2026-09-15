# 作業別の追加ルール

[共通AGENTS.md](../AGENTS.md)から、該当する作業の節だけ読む。共通のowner・権限・安全境界はAGENTS.mdを継承する。通常の文書編集のために運用・GUI・委譲手順を一括読込しない。本書は共通ルールを補う正本であり、module内部仕様を複製しない。

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
- 配備はsource→build artifact→installed binary→active config→service PID→socket destination→実request receiptを照合する。active config、backup、example、disabled sectionを区別し、文字列残存だけでlive consumer／削除対象としない。
- port／routeを変更する実装では、固定port drift、旧endpointへのactive consumer/socketが0、全aliasの正規route smoke、credential非漏洩、再起動後のowner/readiness、利用主体からのE2E receiptを機械検査する。時間依存checkは期限・consumer付きで`deferred`にし、未確認のまま全体完了にしない。代替経路の成功を正規route／Agent-owned E2E成功と報告しない。

<a id="decision-gui"></a>
## 利用者固有の判断GUIを作る場合

- GUIは認証済ownerが未処理の判断対象を発見し、一回の明示操作で次状態を確定できるようにする。内部queueや無言の`blocked`へ隠さない。
- 表示内容は判断対象・必要理由・原文／Evidence・現状態・選択肢・推奨と根拠・各選択の影響／リスク・編集可能範囲・実行／拒否／保留・未処理件数／進捗・操作後receipt。任意filesystem path・SQL・owner外dataは公開しない。
- GUI送信は新しい認証済requestとして同期評価し、即時の終端状態とreceipt、CORE正本への反映、実利用経路までE2Eで確認する。policyで決定できる工程をGUI判断へ逃がさず、汎用human gateにしない。

<a id="local-tests"></a>
## ローカル検査を実行・変更する場合

- module固有の検査集合・runner引数・実runtime受入は当該moduleの入口から読む。文書／コメントだけの変更はlink・format・index・指示の適用を検証し、製品のTDD／runtime E2Eを追加しない。
- Windowsの正規入口は各repoの引数なし`scripts/test-local.ps1`。全repoは`RenCrow_CORE/scripts/test-rencrow-system.ps1`。GoのWindows planは`go vet ./...`と`go build ./...`を使い、`.test.exe`を生成・実行する`go test`は含めず、振る舞いtestはGitHub Actions Ubuntuで行う。
- 三OSの契約を保ち、Ubuntuのbehavior testとWindowsのbuild／vetを実行するか、同じ内容のCI結果を確認する。片方だけの成功で全OSの完了としない。宣言済みstepの選択はowner runnerの`-Step <name>`等を使い、検査集合を変更しない。
- `TEMP`／`TMP`／`TMPDIR`／`GOTMPDIR`とGo／Python／Node cacheをowner repoの`Tmp/test-runtime/`へ向け、system temp・user profileへ生成物を出さない。子processは親environmentに変更をmergeする（Python `{**os.environ, ...}`、Go `append(os.Environ(), ...)`、Node `{...process.env, ...}`）。
- 一時clean worktreeと検証済元treeは`git diff`／hashで内容を照合して証拠を再利用する。cold cacheでの重複testを行わない。
- timeout時は残留する当該test processを停止し、cache・network・security software・子processの停止点を診断する。未完了を明記し、ユーザー判断またはGitHub Actionsへ切り替える。`Tmp`内の実行fileもblockされた場合はpathとerrorを記録し、rename／反復で通そうとせずUbuntu CIへ移す。

<a id="paths"></a>
## Windowsの非ASCII path・文字化けを扱う場合

pathをfilesystem API（`pathlib.Path.rglob()`／`Get-ChildItem`等）で列挙し、そのpath objectを操作する。PowerShell／cmdへ非ASCII pathを直書きしない。`PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`、必要なPowerShell出力encodingでUTF-8 I/Oを保つ。表示が崩れても実Unicode名を確認し、本当の置換文字／文字化けと意図する名前が確定した場合だけrenameする。Gitのoctal escapeは破損ではなく、読取り表示にはlocalの`core.quotepath=false`を使える。

- Goでは`filepath.Join()`と`strconv.Quote()`、Pythonでは`pathlib.Path`等を使う。実I/Oの一時pathに`/tmp`や`/home/<user>`を固定せず、owner runnerの環境内で`t.TempDir()`／`tempfile`を使う。設定値として素通しする文字列とは区別する。

<a id="implementation"></a>
## 実装・構造を変更する場合

変更はできるだけ小さく、局所的に行う。

守ること：

- 最小変更を優先する
- 関係ない箇所を触らない
- 既存の命名と設計意図を尊重する
- ハックでごまかさず、根本原因を確認する
- より深い問題を見つけたら、勝手に拡張せず報告する
- 疎結合とモジュール境界を守る
- 既に分かれている処理は、理由なく 1 ファイルや 1 関数へ統合しない
- ファイル分割やモジュール化は段階的に行い、各段階で確認する

避けること：

- 大規模リファクタリング
- 無関係な cleanup
- 推測による仕様追加
- 責務をまたぐロジック移動

AI エージェントは、実装や調査の成果をその場限りの回答で終わらせない。

- うまくいった手順、プロンプト、コマンド、検証観点、失敗から得た教訓は、必要に応じて docs / rules / prompts / skills / runbook へ残す。
- 「どうやったか」を説明するときは、抽象論だけでなく、実際に再利用できるプロンプト、コマンド、差分、チェックリストを添える。
- 回答は個別ユーザーだけでなく、後続の Worker / Coder / 人間が再利用できる形を意識する。
- 共有のための文書化は重くしすぎず、短いメモ、実例、検証済みコマンド、失敗時の見方から始める。
- ただし、安全制約、責務境界、検証条件はプロンプトだけに閉じず、コード、テスト、ログ、ルールへ落とす。

既存コードの流儀、明示的な命名、小さい関数と読みやすい分岐、必要最小限のコメントを保つ。不要な抽象化、賢すぎる書き方、その場しのぎの分岐、仮置きロジックの放置を避ける。commit messageは日本語とする。

コーディング作業は、次の2形態を区別する。

- **Safe Build Mode**: 既存コード、既存DB、既存環境、設定、運用系に触る作業。既存システムを壊さず、小さい差分、影響範囲、テスト、ログを優先する。
- **Tool Build Mode**: 新規ツール、小物スクリプト、補助アプリ、検証用CLIなどを、`<workspace>/RenCrow_Tools`、`experiments/`、`sandbox/` 配下で既存本体から切り離して作る作業。

横断的に再利用するツール、ブラウザ sidecar、データ変換、検証用 CLI は `RenCrow_Tools` を正本とする。`RenCrow_CORE/tools/` は既存互換または本体密結合の残置場所であり、新規の横断ツール置き場にしない。

判断に迷う場合は Safe Build Mode に倒す。Tool Build Mode でも、既存本体、DB、設定、運用、Source Registry、memory、validator に踏み込む場合は Safe Build Mode として扱う。

<a id="investigation"></a>
## 回帰・仕様不明・過去の操作を調査する場合

0. **仕様なし報告を禁止する**  
   「仕様がない」「未定義」「以前からそうだっただけ」と報告する前に、必ず正本仕様、関連 docs、rules、直近テスト、直近差分を検索する。ユーザーが「さっきまでできていた」「前に決めた」「仕様にあったはず」と指摘した場合は、仕様存在または回帰の強い証拠として扱い、実装側・テスト側・自分の確認漏れを先に疑う。確認できていない場合は「未確認」と報告し、「仕様なし」と断言してはいけない。

1. **ユーザー観測を Ground Truth とする**  
   ユーザーの実機観測は、AI の推測、局所テスト、ログ解釈より優先する。観測と分析が矛盾したら、分析側を疑って調査をやり直す。

観測された不具合は既存記録の安定したIDで全件の状態を追跡する。優先度は作業順であり、事象を削除したり代表例だけで完了にしたりしない。

- 過去のRenCrow操作を確認する場合は、ユーザーへ記憶を尋ねる前に`~/.codex`と`~/.rencrow`両rootのsessions・操作履歴・runtime logs・receipts・旧履歴を期間／module／IDで絞り、読み取り専用で現source・state・active configと照合する。参照path・行・時刻と確定／不明を記録する。履歴や文字列の出現を現行正本・実Actor・成功証拠にせず、欠落／照合不能を明示する。履歴確認を旧操作の再実行許可にしない。

<a id="change-boundary"></a>
## 導入・削除・CI・配備・secret取扱いを変更する場合

以下は高リスク操作として扱う。

- 依存関係の追加・更新
- 外部ツール、CLI、MCP、ブラウザ自動化ツール、補助スクリプト実行基盤の新規インストール
- ファイル削除
- CI / build / deploy 設定変更
- 大規模な横断修正
- セーフガードの無効化
- API キーやシークレットの取り扱い変更

これらは独断で進めず、確認を前提に扱うこと。

ただし、ユーザーが「危険性を確認した上でインストールしてよい」と明示した作業では、AI は次を満たす場合に限りインストールしてよい。

- 目的、導入元、実行権限、ネットワークアクセス、ファイル書き込み範囲を確認する
- 既存のインストール済みツール、自作ツール、`<workspace>/RenCrow_Tools`、リポジトリ内 `scripts/`、`experiments/`、`sandbox/` で代替できないか先に確認する
- 新規ツール作成より、既存ツールの再利用・拡張を優先する
- インストールまたは作成したツールは、場所、用途、起動方法を記録し、次回以降は再利用を優先する
- 危険性が高い、出所が不明、シークレットが必要、既存環境を壊す可能性がある場合は実行前に停止して報告する

また、以下は禁止：

- API キーを設定ファイルへ平文保存する
- 保護ファイルパターンや Git auto-commit を無効化する

既に得たユーザーの具体的な許可を再要求しない。secretはsource・docs・log・trace・artifactへ出さない。保護fileとGit auto-commitの無効化を行わない。
