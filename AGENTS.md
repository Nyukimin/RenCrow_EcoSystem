# RenCrow Project Rules

本書はCursor／Codex／Claudeのworkspace共通ルールの唯一の正本。module-localの`AGENTS.md`は所有範囲の追加制約とし、競合時は本書を優先する。補助Skillもこの境界を上書きしない。

- Codexの`~/.codex/AGENTS.md`は本書へのsymlink、Claudeの`CLAUDE.md`と子repo用Cursorルールは本書への参照にする。本文を個人設定へ複製しない。catalog rootを開くCursorは本書を直接読む。
- 本書→対象の`README.md`→`docs/README.md`→`ecosystem.yaml`→影響するmodule正本の順に必要箇所を読む。既読の指示は再読しない。
- 各moduleはworkspace直下の独立した`RenCrow_*` repository。対象module rootで作業し、親全体を一つのsource treeとして扱わない。EcoSystemが子directoryにある環境では、本書の文書リンクはEcoSystem基準、module pathはworkspace基準で解決する。

## Codex efficiency policy — 2026-09-12 v1

この節はCodexだけに適用する。既定は単独での作業と短いコンテキストとし、明示された委譲依頼、または追加コンテキストに見合う効果を示せる独立作業がある場合に委譲する。通常の可逆的な編集では不要なreceipt・台帳を新設しない。必要な安全・認証・policy・配備・外部効果の証拠は残す。指示ファイルは一度読んで適用し、毎回読み直さない。配布と設定の移行手順は[Codex efficiency rules](docs/codex-efficiency.md)を参照する。

Codexの作業効率に関する運用規定。依頼の全体目標・品質・正本・owner・認証・安全境界・既存差分の保護を維持する。RenCrow製品のruntimeや他のコーディングツールの規定へ移植しない。

1. 最初に対象・正本・操作環境・受入条件・依存順を必要な範囲で整理する。元の受入条件に必要な修正は完遂し、目的と独立した改善を終了条件へ勝手に追加しない。明示された予算を守り、予算の新設や途中停止を効率改善と扱わない。
2. 既存の追跡記録を正本にし、残件報告前に照合する。項目IDと受入条件を安定させ、方針決定・実装・検証・配備・運用受入を区別する。後段の未完了で既決方針を未完了へ戻さない。状態の変更箇所だけ更新し、二重台帳を作らない。再開には新しい反証・依頼変更・証拠を無効にする変更を明記する。「念のため」だけで既決判断や巨大履歴を再読しない。
3. Astraは設計・曖昧な判断・原因切り分け・重要差分レビューを担う。確定した取得・整形・集計・検証手順はCLI等でまとめて実行し、一行ずつのモデル往復を避ける。実際のモデルと役割を偽らない。
4. 委譲が有益な独立作業は、Luna maxで完結できる小さく明確な単位へ委譲する。目的・成功条件、対象とowner、現状証拠、許可差分・禁止事項、契約、検証と返却内容を短く指定する。曖昧な設計や全履歴を丸ごと渡さない。委譲時は履歴継承なしを基本に、対象fileと直接依存だけを渡す。完結した責務と独立した仕事を同じ子の履歴へ積み重ねない。独立した割当てはまとめて準備し、共有ファイル・状態への変更や結果依存の仕事は順番に進める。同じ仕事を重ねて割り当てない。子は結論・変更差分・検証証拠・未解決点を返す。
5. 実装担当は、許可範囲内で納品前の短い型・構文・関連最小チェックを実行し、単純な誤りを修正してから返してよい。これは独立検証の代替ではない。既存の親による差分レビューと独立検証を維持し、特に認証・永続化・並行処理・移行・共有契約の保証を省略しない。検証のための外部変更にも既存の許可・操作境界を適用する。
6. 追加割当ては「次の作業／修正／仕様変更／検証／進捗調整」を短く区別する。追加指示数を失敗数と数えない。失敗時は証拠から前提・範囲・手順を見直し、同じ条件の反復や無関係な探索を増やさない。
7. 子やコマンドの実行中は独立した有用な仕事を進め、結果が必要になった時点で通知待機する。ツール制約と必要な進捗連絡の範囲で十分な待機時間を選ぶ。完了通知を基本にし、変化のない確認・一覧取得・短いsleepを連鎖させない。進捗連絡だけを理由に状態を再取得しない。完了・失敗・前提変更・必要な判断に合わせて再開し、待機APIの上限と対話の応答性を守る。
8. 調査は既存証拠→関連検索→必要箇所の順に進める。大量ログは所有CLIで集計し、親へ差分・件数・失敗箇所と参照path／行だけを返す。独立した検索・取得は一回のCLI呼出しへまとめ、同じ生ログを再投入しない。通常の出力は目安2,000トークン以内、詳細は適切なファイルへ保存する。根拠不足や矛盾があれば原文・必要な範囲へ広げる。secretや無関係な会話全文を出力しない。
9. 証拠に対象差分・環境・検証内容・無効化条件を対応させる。commitが同じでも設定・データ・外部環境の変化を確認する。有効な証拠を再利用し、無効になった範囲を再検証する。圧縮後・モデル交代時も既存記録から再開する。作業の区切りで既存記録の現在状態・有効な証拠・次の作業を更新する。要約の追記が既存コンテキストを削減するとは仮定せず、新規タスク作成はれんの依頼に従う。
10. 進捗は閉じた条件・新しい阻害要因・次の実行を短く伝える。既決事項の承認を求め直さず、承認済み作業を報告だけで止めない。低い推論設定が最安とは仮定せず、xhighも比較候補にするが、節約の推測だけでモデルや推論強度を一律変更しない。既存報告と所有CLIで親子合計の使用量・受入結果・修正往復を測り、計測だけのためにモデルを定期起動しない。応答の二重計上を避け、追加指示や待機の件数を無駄の確定値と扱わない。週間使用率はaccount共有の補助指標とし、同程度の成果・品質なしに削減率を断定しない。速度指定のない作業はStandard設定を確認し、未指定をFastと推定しない。

## 作業範囲・役割・権限

- 編集前に目的、owner、正本、操作環境、稼働成果物、許可差分、依存順、要求ごとの終端証拠を確定する。不明点は調査し、既存差分を保護する。ユーザー訂正を現行制約に反映し、目的変更・圧縮後は既存記録から要求と証拠の対応を復元する。
- Codex主担当は`gpt-6-astra`。設計・責務判断・分解・差分レビュー・統合・最終検証を所有し、単独で実装・検証してよい。有益な独立作業だけ`gpt-5.6-luna` maxへ委譲し、その際は[委譲手順](docs/agent-task-rules.md#delegation)を読む。実model不明時は報告し、役割を推定・代替しない。このmodel契約はCodex限定。
- 変更scopeはユーザーの指示に基づく。scope拡大・破壊的操作・新branch作成には明示指示が必要。通常は現在branchで継続する。

## 完了と証拠

- 運用機能の終端は`source → owner → policy → state → runtime route → 実際の利用主体 → 利用者に見える結果 → receipt/trace`。仕様・保存・API・test・build・deploy・healthの単独成功を全体完了にしない。対象dataの取得・変換・投影だけで終わらず、正規routeでの実参照・判断・利用、運用成果と再起動後の維持を確認する。
- E2Eは本番同等の認証・policy・owner module・runtime route・実Actorを通す。内部functionやtest doubleで代用しない。子の報告は、親が実差分・範囲・試験・境界を確認するまで助言扱い。要求の未確認があれば部分達成と不足境界を示す。
- 過去のRenCrow操作を確認する場合は、ユーザーへ記憶を尋ねる前に`~/.codex`と`~/.rencrow`両rootのsessions・操作履歴・runtime logs・receipts・旧履歴を期間／module／IDで絞り、読み取り専用で現source・state・active configと照合する。参照path・行・時刻と確定／不明を記録する。履歴や文字列の出現を現行正本・実Actor・成功証拠にせず、欠落／照合不能を明示する。履歴確認を旧操作の再実行許可にしない。

## Conceptual Integrity Guardrail v0.1

要件・安全性・整合性が同等なら、単純で説明しやすい構造を選ぶ。主use caseを入口から判断、保存／外部I/Oへ一方向に追えるようにし、各段の入力・判断・出力・次ownerを明確にする。不要な抽象化・wrapper・registry・互換layer・未使用routeを増やさない。本節全体を実装前と完了前に確認する。

### Hard Invariant

- 一つの責務・知識・仕様・設定・schema・policy・状態に一つのownerと正本を置く。派生data／cache／index／snapshotを独立更新可能な正本にしない。不可避な複製は正本から決定的に生成・検証し、同じ意味の変更を複数箇所へ手修正させない。
- 提案・意味判断・policy判定・状態変更・外部実行の責務を混同せず、owner API・認証・policy・安全境界を迂回しない。置換する旧経路は同じImplementation Unitで削除する。
- 実Actorは認証済userとCORE管理Agent（Mio／Shiro／Kuro／Midori）。Coder・LLM・model・provider・controller・Runtimeは実装機構であり、実行主体／Actor／Agent identity／正本ownerにしない。実Actor・owner module・認証・policy・実行責任を維持する。
- 不変条件は可能な限りAPI・権限・型・schema・lint・CI・architecture testで強制する。機能testだけで完了にせず、未確認・未強制の保証を報告する。

### Architecture SmellとSemantic Duplication

計画確定前と変更後に、既存owner／正本、canonical routeの拡張、例外・新概念の必要性、削除できる旧実装、同期手修正の発生を証拠で確認する。同じ知識の分散、異名同概念、責務侵食、旧新併存、特例・別形式・不要layerの増殖を見逃さない。同じ意味の変更が同じ理由で複数箇所に必要なら`Semantic Duplication`。見た目だけでDRY化せず、owner・変更理由・lifecycle・failure domain・安全性が異なる重複は理由と検証を残して許容する。

### Failure Knowledge

再発防止に必要な失敗はownerの正本仕様・`docs/調査/`・既存testへ`Failure / Problem / Cause / Lesson / Invariant / Enforcement / Tests`を記録し、根拠と機械的な強制を結ぶ。正本仕様と必要なarchitecture／behavioral testも更新する。EcoSystemは横断索引だけを所有できる。

### Architecture Reviewと再構築

大きな追加、cross-module契約・例外の変更、同一領域の反復修正、変更蓄積時は通常reviewと別に構造をreviewする。現仕様・Principle・Failure Knowledge・Invariantから作り直しても同じ構造を選ぶか確認し、Noなら再構築候補を記録する。要件と安全性を保ち、統合・削除・再抽象化・subsystem再実装も選択肢にする。

## CLI・LLM・検査

- 計画確定・編集前に工程を`CLI`（決定的処理）、`LLM`（意味判断等）、`Boundary`（schema・認証・policy・状態変更・保存・外部効果・再試行・監査）へ分け、owner・入力→出力・失敗status・証跡とLLM採用理由を短く提示する。分類・owner・根拠が未確定なら実装・状態変更へ進まない。
- parser／schema／query／state machine／policy／既存APIで決定できる工程はowner CLIで実行する。LLMを呼ぶwrapperだけではCLI化としない。LLMは意味判断の必須性、または同条件の決定的baselineに対する十分な品質優位性で採用し、混在工程は分割する。LLM出力による変更・外部効果はowner CLI／policyが検証して実行または拒否する。CLIはCMDの所有権を意味せず、既存routeを維持する。
- CLI／Boundaryは明示入力、境界付き機械可読出力、終了status、再現可能な証跡で検証する。LLMは入力境界・出力schema・品質・失敗／拒否を検証し、報告文を実行証拠にしない。最終報告で実経路と分類を照合する。品質優位性でLLMを採用する場合は[比較条件](docs/agent-task-rules.md#llm-quality)を読む。
- 検査前に[Check Plan仕様](docs/check-plan-pruning.md)でpurpose・phase・check・consumer・failure actionを固定し、runnerは固定Planだけを消費する。高コスト・timeout・失敗を理由に除外せず、safety／security／認証／policy gateを暗黙に削除しない。曖昧・不正な定義はfail closed。runtimeのpruningでsourceを削除せず、恒久削除は運用証拠・仕様更新・TDD・reviewを伴う別変更とする。

## COREと製品runtime

- 共有Viewer・会話・runtime・route・adapter・利用者向け挙動とcross-module意味論はCORE正本。CMDはCOREのCLI／client入口。該当変更はCOREを先に扱ってからCMDへ同期し、CMD専用なら実装前に理由を示す。正本索引は`RenCrow_CORE/docs/README.md`、Chat境界と標準Go配布境界は同`docs/04_アーキテクチャ概要.md`。
- Viewer／COREは対応moduleを経由する。LLMは`CORE → LLM Gateway → LLM Runtime → Backend → Model`、TTS／STTは各module→backend、画像生成はImage→ForgeNeo／Z-Image、認識はVision→Wild→Vision→CORE。Visionが前処理・正規化を所有し、raw mediaをCOREからWild／LLMへ直送しない。Mio／Shiro／Midori／Kuroによる文章生成の一部としてのCodexExe ImageGen利用だけは既存例外であり、通常Image経路の省略へ広げない。
- 固定portと正規routeは契約。競合・障害・E2E成功のためにport変更、backend直結、代替model／偽server／短縮経路を作らない。許可範囲で正規経路を復旧し、復旧不能なら境界と証拠を報告する。route例外は明示されたtopology変更だけとし、復旧目的の代替は障害・影響を報告してからその明示指示を受ける。process・配備・routeを扱う前に[運用手順](docs/agent-task-rules.md#runtime)を読む。
- 標準runtimeは可能な限りnative Go binaryとし、Ubuntu／Windows／macOSでprotocol・Config・health/readiness・error/unavailableを等価にする。Python・Node・Docker・WSL・外部DB／queue／vector storeを標準起動条件に追加しない。不可避な外部systemはowner境界外へ隔離する。WSLは明示選択したCUDA／GPU external compute限定で、Windows native検証の代用にしない。標準構成の例外は明示指示と対象・理由・OS・影響・失敗挙動・再評価条件の記録が必要。
- Agent-ownedの会話・作業・gameplayは実CORE Agentへ帰属させる。`RuleBasedBrain`／`DummyBrain`はunit・integration・simulation・observer用で、Agent identity・Persona・記憶・経験を称さない。Agent gameplay E2Eでは各playerの全判断を対応CORE Agentへ要求する。

## 利用者判断とNo-Human-Gate

- RenCrow runtimeはCORE正本・machine-readable policy・認証済request scopeを同期評価し、即時に実行／`rejected`／`blocked`を返す。人の返答で解除するstatus・grant・reference・queueを作らない。既定fallback以外は`blocked`を返し、人を待たない。Codexの作業権限を製品へ移植しない。
- policyで決められない利用者固有の意味・価値判断には、同じImplementation Unitで判断GUIを提供する。CLI・JSON・手順書だけに委ねず、[判断GUIの受入条件](docs/agent-task-rules.md#decision-gui)を満たす。操作は待機workflowへの承認印ではなく新しい認証済requestとし、CORE状態・正規利用経路・receiptまで確認する。
- reject理由から前提・分解・route・Tool・設計を再考した新revisionを作る。同案の言い換え、制約弱体化、無限再試行は禁止する。

## EcoSystemとmodule所有範囲

- EcoSystemは構成manifest、source pin、検証済組合せ、横断設計・導入・release文書、統合検証・受入、module正本へのリンクを所有する。module内部のsource・API・build・test・config・roadmap、Persona／Memory／Recall／policy／LLM routing、runtime state・secret・生成物を所有／複製しない。
- moduleは独立Git repo・CI・tag・releaseを維持し、workspace直下に置く。catalogにsourceをコピーせず、Git submoduleを追加しない。子repoは`.gitignore`対象。再利用toolはTools、`ecosystem.yaml`専用検証だけcatalogの`scripts/`に置く。
- manifestの状態は`development`／`source-pinned`／`unpinned`／`verified`。実装済source pinは実在full SHA、未実装optional runtimeだけ`planned`を使う。pinは互換性証拠ではない。互換宣言は統合検査成功と差分説明またはrepo内証拠が必要。現行と明示計画だけを記述し、廃止仕様・架空tag／commitを残さない。
- `.env`・認証情報・runtime log／DB・binary・model・download済archiveをcommitしない。Workspaceは移行用snapshot owner。共通ルールの配布は[Codex効率運用仕様](docs/codex-efficiency.md)に従い、snapshotを独立編集しない。
- module名とrootは`ecosystem.yaml`を参照する。Chat／ViewerはCORE、CLIはCMD。`RenCrow_GPT120B`／`RenCrow_Qwen36_27B`／`RenCrow_Gemma4`はLLM external-runtime profileで、CORE・Agent・routing ownerではない。

## 検証環境と可搬性

- catalog変更は`make check`。宣言済子repoが揃う環境では`make check-workspace`、rules・CI・local test契約・Workspace snapshotは`make check-governance`で確認する。Windowsでは`./scripts/test-local.ps1`または文書化された`make PYTHON=python`を使い、Linux coverageも確認する。
- 検査を実行／変更する際は[ローカル検査手順](docs/agent-task-rules.md#local-tests)を適用する。同じ内容の有効な検証をPushや一時worktreeで繰り返さず、関連変更・失敗・明示依頼時だけ再検証する。timeout延長だけの再試行、security softwareの停止・除外・検査弱体化は禁止する。
- textはUTF-8、pathはUnicodeとして扱い、三OSで同じ契約を守る。Pythonは`pathlib.Path`で結合し、shell／JSON／YAMLに埋め込むpathを適切にescapeする。改行・実行bit・symlink・case-sensitive filesystemを前提にしない。Windowsの非ASCII path／文字化けを扱う場合は[文字とpath](docs/agent-task-rules.md#paths)を読む。
