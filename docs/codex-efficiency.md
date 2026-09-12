# Codex効率ルールの配布

## 正本と適用範囲

運用ルールの唯一の正本は[AGENTS.mdのCodex efficiency policy](../AGENTS.md#codex-efficiency-policy--2026-09-12-v1)。2026-09-12にWindowsとUbuntuのCodexへ直接適用した10項目を、そのまま収録する。Astraを主担当とし、有益な独立作業だけLuna maxへ委譲する。作業の完遂、親による差分レビュー、独立検証、owner・認証・安全境界を維持する。

この節はCodexの開発作業にだけ適用する。RenCrow製品のAgent、runtime、model routingや、Cursor／Claudeの規定へ移植しない。ルールは運用指示であり、使用量の削減率や推論設定を強制する仕組みではない。

## 既存の配布経路

1. `RenCrow_EcoSystem/AGENTS.md`が正本。標準配置ではEcoSystemを`RenCrow`というworkspace rootへcloneする。
2. `RenCrow_Workspace/project-root/AGENTS.md`は正本から生成する配布snapshot。独立編集せず、正本をバイト単位でコピーして同期する。snapshotの相対参照は、配置先のcatalog rootで解決する。
3. Codexの`~/.codex/AGENTS.md`は、Agent配置規定どおり正本へのシンボリックリンクで参照する。通常ファイルへの全文複製は禁止する。
4. `make check-governance`の既存検査は、workspace rootとsnapshotの一致を確認する。snapshot単体はruntimeの起動設定ではなく、PushやPullだけで各端末のリンク・Codex設定は書き換わらない。

正本を更新した端末では、現在の配置に合わせてsnapshotを同期する。PowerShell例:

```powershell
$catalogRoot = 'C:\path\to\RenCrow'
Copy-Item -LiteralPath (Join-Path $catalogRoot 'AGENTS.md') `
  -Destination (Join-Path $catalogRoot 'RenCrow_Workspace/project-root/AGENTS.md')
```

EcoSystemが親rootではなく`RenCrow_EcoSystem`という子directoryにある場合、コピー元はそのcheckoutの`AGENTS.md`とする。親に残る古い通常ファイルを正本と誤認しない。両repositoryをそれぞれcommit・pushし、配置先ではリンクの実際の参照先と内容を照合する。

## Codex設定と直接適用版の移行

ルール本文とCodex設定の値は別に扱う。既存の主modelと推論強度は維持し、low／xhighへ一律変更しない。明示的な個別指定がある場合はそれを維持する。今回の直接適用版で採用した値は以下。既存の`config.toml`へ同じtableを重複追加しない。

```toml
# rootの既存キーを更新する。tableの内側に追加しない。
service_tier = "default"
project_doc_max_bytes = 65536

[agents]
default_subagent_model = "gpt-5.6-luna"
default_subagent_reasoning_effort = "max"
```

共通`AGENTS.md`は32 KiBを超えるため、`project_doc_max_bytes`は少なくとも65536にする。既存値がそれより大きければ維持する。効率規定は前方へ配置し、読込上限で末尾の規定が欠落していないことも`debug prompt-input`で確認する。rootとmoduleの指示の合計が上限を超える場合は、その実測量に合わせる。

これらは[公式のCodex構成リファレンス](https://learn.chatgpt.com/docs/config-file/config-reference)にある設定項目を使う。`AGENTS.md`を読むことは`config.toml`を書き換える操作ではない。

Windows／Ubuntuへ先に適用した版では、`developer_instructions`に同じ10項目が入っている。新しい正本をリンクから読めることを確認してから、設定のバックアップを取り、旧版の本文だけを取り除く。旧版は見出し`# Codex efficiency policy — 2026-09-12 v1`、LF・UTF-8本文のSHA-256 `07b9022898f22c5d3b60162aa824ef1b469ba6ed55ddfaa5812a8d0ca63f0d2b`で識別する。別の指示が併記されていれば、その指示は残す。参照先未更新の端末から先に旧本文を除去しない。

移行後はCodexの`debug prompt-input`で、正本の効率規定が一度だけ含まれること、既存の人格・module制約が保持されることを確認する。生のpromptやconfig全体をGitへ保存しない。起動済みタスクへの反映は別に確認する。

この変更のPushは、配布元とsnapshotの公開までを対象とする。各端末へのPull、リンクの変更、直接適用版の除去、Codex再起動は別の適用工程であり、実施した端末と未適用の端末を区別して報告する。
