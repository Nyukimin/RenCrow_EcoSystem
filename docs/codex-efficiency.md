# Codex効率運用仕様と配布

## 正本と適用範囲

運用ルールの唯一の正本は[AGENTS.mdのCodex efficiency policy](../AGENTS.md#codex-efficiency-policy--2026-09-12-v1)。2026-09-12の直接適用版を基に、2026-09-13に待機、情報取得、委譲、証拠再利用、測定を具体化した。Astraを主担当とし、有益な独立作業だけLuna maxへ委譲する。作業の完遂、親による差分レビュー、独立検証、owner・認証・安全境界を維持する。

この節はCodexの開発作業にだけ適用する。RenCrow製品のAgent、runtime、model routingや、Cursor／Claudeの規定へ移植しない。ルールは運用指示であり、使用量の削減率や推論設定を強制する仕組みではない。

## シリーズへの配布

1. `RenCrow_EcoSystem/AGENTS.md`が正本。標準配置ではEcoSystemを`RenCrow`というworkspace rootへcloneする。
2. `RenCrow_Workspace/project-root/AGENTS.md`は正本から生成する配布snapshot。独立編集せず、正本をバイト単位でコピーして同期する。snapshotの相対参照は、配置先のcatalog rootで解決する。
3. Codexの`~/.codex/AGENTS.md`は、Agent配置規定どおり正本へのシンボリックリンクで参照する。通常ファイルへの全文複製は禁止する。
4. `make check-governance`の既存検査は、workspace rootとsnapshotの一致を確認する。snapshot単体はruntimeの起動設定ではなく、PushやPullだけで各端末のリンク・Codex設定は書き換わらない。

配布操作のownerはToolsの既存[ecosystem bootstrap](https://github.com/Nyukimin/RenCrow_Tools/tree/main/tools/workspace/ecosystem_bootstrap)。`rules plan`で事前確認し、`rules apply`で反映、`rules check`で一致を確認する。通常のrepository取得用`plan`／`apply`とは明示的に分け、clone時に端末の設定を変更しない。

標準配置のworkspace rootから実行する例（GoとGit、Codexの設定directoryを事前に用意する）:

```bash
go -C ./RenCrow_Tools/tools/workspace/ecosystem_bootstrap run ./cmd/rencrow-bootstrap rules plan --manifest ../../../../ecosystem.yaml --workspace ../../../.. --sync-snapshot --codex-home "$HOME/.codex"
go -C ./RenCrow_Tools/tools/workspace/ecosystem_bootstrap run ./cmd/rencrow-bootstrap rules apply --manifest ../../../../ecosystem.yaml --workspace ../../../.. --sync-snapshot --codex-home "$HOME/.codex"
go -C ./RenCrow_Tools/tools/workspace/ecosystem_bootstrap run ./cmd/rencrow-bootstrap rules check --manifest ../../../../ecosystem.yaml --workspace ../../../.. --sync-snapshot --codex-home "$HOME/.codex"
```

PowerShellでは同じcommandの`--codex-home`を`"$env:USERPROFILE/.codex"`に置き換える。EcoSystemがこのMacのようにworkspace直下の`RenCrow_EcoSystem`にある配置では、`--manifest ../../../../RenCrow_EcoSystem/ecosystem.yaml`とする。正本は常に指定manifestの隣の`AGENTS.md`であり、親の入口文書を配布本文と誤認しない。

配布元でsnapshotだけを更新するときは`--codex-home`を省略する。配布先端末でリンクだけを設定するときは`--sync-snapshot`を省略する。少なくとも一方を明示する。各repositoryの`AGENTS.md`へ共通本文をコピーせず、module固有の内容を保持する。旧model規定等が共通規定と競合する場合は、正本の優先順位に従う。

`rules`はsource hash、対象ごとの変更とhash、manifestに記載されたrepositoryの存在状況をJSONで返す。未取得のmoduleは一覧に残し、勝手にcloneしない。source pinとの一致やruntime互換性をこの一覧から主張しない。成功した`check`は配布file／linkの一致であり、Codexが新しい指示を実際に読むことと削減効果は、後述の適用確認と実運用で別に確認する。

snapshotの未commit変更、別の通常file・誤ったlink、優先される`AGENTS.override.md`、危険なpathは事前検査で拒否する。snapshotは正本から生成する指定fileだけを更新し、config、module本文、runtime promptは書き換えない。全対象の事前検査後に更新し、途中のI/O失敗では反映済み対象を報告する。複数file全体を一つのtransactionとは扱わない。

Windows等でsymlink作成権限がなければ、コピーへのfallbackや権限昇格を行わず失敗を返す。端末側でsymlinkが利用できる状態を整えてから再適用する。既存の通常fileや誤ったlinkの整理は、内容・用途を確認して別途行う。snapshotを元へ戻す場合も、採用する正本revisionを確定してから同じcommandで同期する。

更新した正本とsnapshotは各owner repositoryでcommit・pushし、各端末で取得後に再度`rules check`を実行する。Tools CLIの詳細な引数、終了code、回帰試験はTools READMEが所有する。これにより配布手順のための別installerや常駐processを増やさない。

## Codex設定と直接適用版の移行

ルール本文とCodex設定の値は別に扱う。既存の主modelと推論強度は維持し、low／xhighへ一律変更しない。明示的な個別指定がある場合はそれを維持する。直接適用版で採用した値は以下。設定schemaは使用中のCLI／appで検証してから有効化する。既存の`config.toml`へ同じtableを重複追加しない。

```toml
# rootの既存キーを更新する。tableの内側に追加しない。
service_tier = "default"
project_doc_max_bytes = 65536

[agents]
default_subagent_model = "gpt-5.6-luna"
default_subagent_reasoning_effort = "max"
```

共通`AGENTS.md`は32 KiBを超えるため、`project_doc_max_bytes`は少なくとも65536にする。既存値がそれより大きければ維持する。効率規定は前方へ配置し、読込上限で末尾の規定が欠落していないことも`debug prompt-input`で確認する。rootとmoduleの指示の合計が上限を超える場合は、その実測量に合わせる。

MacのCLI 0.143.0では、`agents.default_subagent_model`と`agents.default_subagent_reasoning_effort`を設定すると`expected struct AgentRoleToml`で起動に失敗した。非対応版にはこの2キーを入れず、委譲packetでmodel／effortを明示する。schema検査失敗時は対象変更だけを戻し、元の設定を維持する。Standardの反映と子model既定値の対応状況を別判定にする。

これらは[公式のCodex構成リファレンス](https://learn.chatgpt.com/docs/config-file/config-reference)にある設定項目を使う。`AGENTS.md`を読むことは`config.toml`を書き換える操作ではない。

Windows／Ubuntuへ先に適用した版では、`developer_instructions`に同じ10項目が入っている。新しい正本をリンクから読めることを確認してから、設定のバックアップを取り、旧版の本文だけを取り除く。旧版は見出し`# Codex efficiency policy — 2026-09-12 v1`、LF・UTF-8本文のSHA-256 `07b9022898f22c5d3b60162aa824ef1b469ba6ed55ddfaa5812a8d0ca63f0d2b`で識別する。別の指示が併記されていれば、その指示は残す。参照先未更新の端末から先に旧本文を除去しない。

移行後は実際のworkspace起動位置でCodexの`debug prompt-input`を使い、正本の効率規定が一度だけ含まれること、既存の人格・module制約が保持されることを確認する。生のpromptやconfig全体をGitへ保存しない。起動済みタスクへの反映は別に確認する。

Macの子directory配置では`RenCrow/`を起動入口にする。この入口での新process検査は効率規定1回・末尾規定あり。`RenCrow_EcoSystem/`を直接起動するとglobal symlinkとlocal正本の両方から同じ本文が2回入ることを観測した。本文の複製・削除で対応せず、workspace入口から起動し、作業commandのcwdだけを対象moduleへ向ける。

この変更のPushは、配布元とsnapshotの公開までを対象とする。各端末へのPull、リンクの変更、直接適用版の除去、Codex再起動は別の適用工程であり、実施した端末と未適用の端末を区別して報告する。


## 2026-09-13 Implementation Unit

目的は、同じ品質・受入条件を保ちながら、判断を必要としないモデル往復と重複入力を減らすこと。
既存の10項目を正本として更新する。常時ルールの全文を増殖させず、手順・受入は本書、
集計formatとparserは[Tools CLI](https://github.com/Nyukimin/RenCrow_Tools/tree/main/tools/observability/codex_efficiency)が所有する。
日次集計は任意の日付区間をCLIで一括処理する意味であり、今回schedulerやLLM定期起動は追加しない。

### 工程分類と責務

| 工程 | 区分／owner | 入力 → 出力 | 失敗status／証跡 | LLM採用理由 |
| --- | --- | --- | --- | --- |
| 履歴取得・使用量・直接tool集計 | CLI／Tools | 明示sessions root・時刻区間 → bounded JSON | input error／partial、参照とhash | 不使用。parserと計算で確定 |
| 設定監査 | CLI／Tools | 指定TOML → 許可fieldの監査結果 | error／未設定、対象hash | 不使用。値比較で確定 |
| 作業分解・追加指示の区分・証拠無効化判断 | LLM／Codex主担当 | 要求・既存追跡記録・変更差分 → 範囲付き判断 | 根拠不足は未確定、既存記録 | 必須性：意味・責務・変更影響の判断。hash一致等の決定的判定はCLI |
| config反映・権限・Planと検査・snapshot同期 | Boundary／各ownerのCLIとCodex host | 承認済scope・差分・固定Plan → 結果と証拠 | blocked／非zero、差分hashと終了code | 不使用。変更と実行を所有境界で拘束 |
| 成果当たりの改善評価 | LLM／Codex主担当 | CLI集計と既存受入結果 → 比較と限界 | 比較不能なら効果未確定 | 必須性：異なる仕事の成果・品質の比較。同一入力の数値比較はCLI |

Codexの開発運用だけが対象。CORE Agent、LLM Gateway、製品の判断GUI、DB、runtimeには変更しない。
利用者に固有の新たな意味判断機能は作らず、既に指示された設定反映はCodexの既存権限面で実施する。

### 要求と受入条件

| ID | 要求／既存規定 | 終端証拠 |
| --- | --- | --- |
| CE-01 | 入力肥大：項目3・8。必要範囲をCLIで集計、原文は矛盾の解消時だけ取得 | 実sessionsから本文を含まない集計を生成し、Astraがその結果を使って報告 |
| CE-02 | 長期履歴：項目2・9。既存記録から再開、新規台帳や自動タスク分割を作らない | 本Unitでは本表を再利用。タスク切替は利用者依頼時のみ |
| CE-03 | 待機：項目7。通知と独立作業を基本とし、状態不変のpollを連鎖させない | 直接wait／sleep／listの観測件数。必要性は件数だけで断定しない |
| CE-04 | 追加指示：項目4〜6。初回packetを完結させ、子の最小検査後に親review・独立検証 | packet、差分、検査結果。追加指示は次作業／修正／仕様変更／検証／進捗に区分 |
| CE-05 | 子の入力肥大：項目4。限定範囲、履歴継承なし、完結後の別責務を積み重ねない | spawnの実model・effort・forkと子の入力分布 |
| CE-06 | 再検討・再検証：項目2・9。対象・環境・無効化条件を照合 | 根拠を変える変更がある範囲だけ再検証。safety gateは既存Check Plan契約に従う |
| CE-07 | Standard：既存端末設定を最小変更し、主model・effortと認証は保存 | private backup、TOML検証、新processのprompt検査。既存threadと他hostの反映は別判定 |
| CE-08 | 測定：項目10。応答二重計上と親子・モデル混同を防ぐ | CLIの回帰試験と実ログ集計。週間使用率をtokenや料金へ換算しない |

規定の読込み、CLIの正しさ、端末への反映、長期の改善効果を別々に判定する。
規定はCodex hostのスケジューラやコンテキスト保持を強制変更できない。
context要約を追記しただけで入力が減ったとは報告しない。自己報告や完了eventを
運用受入に換算せず、成果と修正往復は既存の追跡記録を参照する。

### 検証と再利用

検査前にTools既存Check Plan CLIでpurpose・phase・check・consumer・failure actionを固定する。
module側の既存test planへ関連testを登録し、owner runner／既存CIが実行する。
入力、Plan、source差分、設定変更の非secret要約、終了codeはGit外の`Tmp/`へ保存する。
ログやconfigの生本文はcommitしない。catalogは`make check`、配置がある場合は
`make check-workspace`と`make check-governance`を実行する。異なる配置や既存失敗は証拠を残す。
Windows／LinuxのCIは同じ変更内容への結果だけを採用する。

Evidenceの無効化条件は、対象source／test、parser入力schema、選択したログprefix、設定layer、
Codex version、実行環境の関連変更。単なる時刻経過や無関係な差分だけでsource試験を繰り返さない。
ログの追記は次の期間の集計対象であり、保存済prefixの過去集計を勝手に書き換えない。

### Failure Knowledge

- Failure / Problem：長大な入力を伴う親の反復起動と再調査が消費を増幅し、キャッシュ率だけでは説明できなかった。
- Cause：状態確認・既決事項・生ログを毎回モデルへ戻し、累積token／応答／親子／共有quotaの母数も混同しやすい。
- Lesson / Invariant：判断が変わる入力だけを戻す。応答は一度だけ数え、証拠と無効化条件を再利用する。
- Enforcement：Toolsの決定的集計と設定監査、既存Check Plan、snapshot一致検査。待機の必要性と意味判断は運用規定であり、hostによる機械的強制は未実装。
- Tests：二重event・複製log・期間境界・model変更・累積reset・壊れたlog・secret非出力・入力不変の回帰試験。

### 適用状況

2026-09-13の作業対象はMacのsource、配布snapshot、Codex設定と実sessions。
MacはStandardだけを反映し、非対応のagentsキーを除去した。この作業の変更はStandardだけで、主model・effort・認証は保持した。監査中に`approval_policy`と`sandbox_mode`の別変更も観測したため、開始時との全設定一致は主張せず、その変更へは介入しない。Windows／Ubuntuの端末操作と、既存threadの実行tierは未確認。日次の削減率・一週間の持続は
比較可能な成果と将来の観測を必要とするため、この実装の成功から推定しない。


ローカル検証ではcatalogの109 test、CLIの18回帰testが成功し、実sessionsに対する
CLI実行（exit 0）のmodel別使用量は別計算と一致した。実行結果はToolsのGit外
`Tmp/codex-efficiency/cli-e2e-result.json`、固定Planは同directoryの`check-plan.json`にある。
これらは当該source差分とログprefixに限る証拠であり、将来の節約率は保証しない。
`make check-workspace`／`make check-governance`はこのMacの兄弟directory配置を既存runnerが
解決できず、`RenCrow_EcoSystem/RenCrow_CORE`探索で失敗した。snapshot単体の一致は確認済みだが、
この結果をworkspace全体のgovernance成功へ昇格しない。配布commitのCIも確認済み。検証対象は、[Tools d78d3dd（Windows／Ubuntu contract suite、macOS build／vet）](https://github.com/Nyukimin/RenCrow_Tools/actions/runs/34746487939)、
[Workspace 76104c4（Windows／macOS build／vet、Ubuntu test）](https://github.com/Nyukimin/RenCrow_Workspace/actions/runs/34746503648)、
[EcoSystem 5a6ed79（三OSのcatalog test）](https://github.com/Nyukimin/RenCrow_EcoSystem/actions/runs/34746531419)。
いずれもsuccessで、当該配布時点のsource pinはこのTools／Workspace commitを参照した。
この結果追記は仕様の検証状態だけを更新し、検証済みCLI・test・規定・manifest・端末設定を変更しない。


### シリーズ配布CLIの受入

`rules`コマンドの追加により、配布snapshot同期と端末の参照link設定を同じTools CLIから
実行できる。正本・module本文・Codex configは今回の変更対象に含めない。
Macでは実バイナリによる初回plan／apply／check、再適用、既存fileとの競合拒否と、
実workspaceの照合が成功した。sourceと17個のmodule指示file、Codex configの変更前後の
hashは一致した。固定Check Planと検証結果はToolsのGit外`Tmp/rules-distribution/`に保存する。
使用量の削減効果は、利用者の方針どおり実践で確認する。

カタログ109件は成功。既存の`check-workspace`／`check-governance`はこのMacの配置不一致で
引き続き失敗し、配布CLIの受入をworkspace全体のgovernance成功と同一視しない。
他端末への適用と、起動済みCodexタスクの再読込は、この配布可能化の検証に含まない。
