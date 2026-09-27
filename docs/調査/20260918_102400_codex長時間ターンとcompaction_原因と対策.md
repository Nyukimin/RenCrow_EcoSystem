# Codex 長時間ターンと compaction 23回 — 原因と対策（2026-09-18）

## 文書情報

- 日付: 2026-09-18 10:24 JST（01:24 UTC）
- きっかけ: 無人監視の監査で「長い調査ターン（最大約4時間）と compaction 23回」をコストと報告したことへの原因究明・対策提案
- 対象 thread: `01a0a770-26e0-78d3-9d75-407cf4fe01c3`（tmux `rencrow-codex` / codex-switch）
- 検出／根拠 path:
  - rollout: `~/.codex/sessions/2026/09/15/rollout-2026-09-15T23-39-00-01a0a770-26e0-78d3-9d75-407cf4fe01c3.jsonl`
  - nudge: `artifacts/codex-auto-nudge.log` / `artifacts/codex-auto-nudge.state.json`
  - 設定: `~/.codex/config.toml`（`model=gpt-6-astra`, `model_reasoning_effort=xhigh`）
  - 契約: [AGENTS.md](../AGENTS.md) Codex efficiency policy、[docs/codex-efficiency.md](../codex-efficiency.md)
- 本ファイルは調査・提案のみ。**実装・config 変更・commit/push は行っていない。**

## 結論

1. **compaction 23回は「故障」ではなく、同一 thread 上の tool 大量投入による自動要約の定期発火**である。直前の `last_token_usage.input_tokens` は毎回おおよそ **65k–72k（宣言 context 124,518 の約 52–58%）** で揃い、間隔は中央値 **約 30分**。
2. **最大約4時間ターン（246分）の主因は「受入条件を超えて同一 turn で探索を続けたこと」**である。当該 turn は tool **414**（うち `exec_command` 382）、分類上 **slice_read（`sed -n` / `head`）222** が支配的で、context を細切れ読取で満たし compaction を **7回** 誘発した。
3. **運用上の増幅器は auto-nudge による同一 thread の無人継続**である。`task_complete` のたびに同じ履歴へ「続けて」が入り、Step14系 → 全体監査 → mount/pin/llm と **目的が変わっても thread を切り替えない**ため、長時間・高 compaction が構造的に続く。
4. 異常な無限ループや stream error ではない。コストの本丸は **(A) 同一 thread に複数ゴールを積み重ねる運用** と **(B) 細切れ読取・xhigh での高頻度 tool 往復**。

## 実測

### 期間と規模（2026-09-17 11:00Z 以降）

| 指標 | 値 |
| --- | --- |
| rollout イベント（当該期間） | 約 8,199 行 |
| `task_started` / `task_complete` | 12 / 9（+ abort 2 + ongoing 1） |
| `compacted` | **23** |
| compaction 間隔 | min 11.6 / **median 29.6** / max 82.0 分 |
| compaction 直前 input fill | **52.2–57.8%** of 124,518（中央 ≈56%） |
| 宣言 `model_context_window` | 毎回 **124518** |
| auto-nudge 実体 | **8回**（ログ上は二重記録で 16） |
| `model_reasoning_effort` | **xhigh** |

### Turn 別（長いもの）

| 分 | 終端 | tools / exec | compacted | 作業の性質（cmd 先頭） |
| --- | ---: | --- | ---: | --- |
| **246.0** | complete | 414 / 382 | **7** | check-plan-runner schema / Step14 周辺の深い実装・検証 |
| **135.5** | complete | 338 / 315 | **6** | core-verify / checks manifest 登録・配備 |
| 91.4 | complete | 172 / 146 | 3 | complexity sqlite orphan 強制の実装・test |
| 45.9 | complete | 84 / 70 | 1 | Step14 commit 後ビルド・配備 |
| 43.8 | complete | 57 / 54 | 1 | 全体監査 MD・systemd/mount 調査 |
| 36.2 | aborted | 63 / 58 | 1 | trade/image/mount 調査（中断） |
| 27.1–60+ | complete/ongoing | — | 1–2 | pin / llm readiness / drop-in 調査 |

最長 turn（`01a0b074-…`）の tool 引数合計 ≈ **185 KiB**、中央長 269B、最大 9.6KB。コマンド種別は `slice_read` 222 / other 98 / build_test 41 / grep 25。

### Compaction の正体

`type=compacted` の payload 先頭は毎回同型:

> Another language model started to solve this problem and produced a summary…

＝ **host 側の自動 context compaction**（別要約モデルが履歴を潰す）。故障ログではない。AGENTS.md §9 の「要約の追記が既存コンテキストを削減するとは仮定せず」と整合するコスト源。

### 因果連鎖（要約）

```
同一 thread を一晩維持（auto-nudge）
  → ゴール切替でも履歴・prefix を引きずる
  → turn 内で sed/head 細切れ読取 + xhigh 推理 + 大量 exec
  → input ≈ 70k（~55% of 124k）で auto-compact（~30分ごと）
  → 要約損失・再探索が増え、さらに長い turn になりやすい
  → 「次は〜」で早期 task_complete → nudge → また同じ thread
```

## Failure Knowledge

- **Failure**: 無人継続中に単一 Codex thread が数時間 turn と数十回 compaction を出し、トークン・時間コストが膨らむ。
- **Problem**: 監視は `stuck_loop`/`dead` だけを見ており、「健全だが高コスト」を止めない。
- **Cause**:
  1. auto-nudge が **thread 切替なし**で完了後も同一履歴へ継続指示する。
  2. 実装／調査が **細切れ読取**で context を早く満杯にする。
  3. `xhigh` + context ~124k で、tool 往復ごとに圧力が溜まり **~55% で compact** する。
  4. 受入条件達成後も「全体を直し切る」方向へ **scope が自然拡大**する（Step14 → 全体監査 → mount/pin）。
- **Lesson**: 長時間セッションのコストは「エラー率」ではなく **thread 寿命 × turn 内 tool 密度 × reasoning 強度** の積で決まる。
- **Invariant（提案）**: 1 thread = 1 完了可能な受入条件セット。条件達成または目的変更で thread を閉じ、再開は短い brief + 正本 path のみ。
- **Enforcement（提案）**: 下記「対策」の監視指標と nudge 条件。
- **Tests（提案）**: compaction 回数／turn 分／slice_read 比率を watch JSON に載せ、閾値超で短報に出す（自動中断は別承認）。

## 対策提案（優先順）

### P0 — 運用（すぐ効く・実装小）

1. **ゴール変更で thread を切る**  
   Step14 完了・全体監査開始・mount 恒久対策など、目的が変わったら `resume` 継続ではなく **新 thread + 短い brief**（現状証拠 path・受入条件・禁止事項のみ）。auto-nudge は「同一受入条件の継続」に限定。
2. **auto-nudge にガードを足す**  
   - 同一 `task_complete` 系列で nudge 上限（例: 2回）  
   - turn 経過 > N 分 または compacted ≥ K なら nudge せず `blocked` 相当をファイルに書いて停止  
   - nudge メッセージに「新 scope 禁止・受入条件外は別 thread」を明示
3. **watch にコスト指標を追加**  
   現行の alive/stuck に加え: `turn_age_min`, `compacted_in_turn`, `recent_slice_read_ratio`, `last_input_tokens`。閾値超過は短報で「高コスト」と出す（即 interrupt は任意）。

### P1 — エージェント行動（ルール／hook）

4. **細切れ読取の抑制**  
   loop-brake または専用 hook: 同一 file への `sed -n`/`head` 連続 N 回を拒否し、「1コマンドで必要範囲をまとめて読む／owner CLI で集計」へ誘導（既に細切れ `/tmp` probe で hook 拒否が出ている）。
5. **受入条件チェックポイント強制**  
   実装ターンは「test/build/receipt まで」で一度 `task_complete` し、配備・横断監査は **別 turn/thread**。AGENTS efficiency §1–4（短いコンテキスト・委譲単位）に合わせる。
6. **独立調査は Luna 委譲**  
   「grep して一覧」「manifest と実体の差分表」など決定的／単純集計は `gpt-5.6-luna` max へ短く委譲し、Astra turn を設計・差分レビューに薄くする。

### P2 — 設定・製品（要判断）

7. **無人夜間だけ reasoning を下げる**（例: `high`）— 品質トレードオフの明示承認が必要。  
8. **Codex host の compact 閾値／context**は製品側制約（`docs/codex-efficiency.md` も「host スケジューラやコンテキスト保持を強制変更できない」）。こちらでいじれない前提で、P0/P1 で圧力を下げる。  
9. **thread 予算**: 例) compaction 累計 8 または wall 3h で「強制 handoff MD を書いて停止」。

### やらない方がよいこと

- compaction 自体を「バグ」として無効化しようとする（未確認・host 非公開）。  
- stuck_loop 誤検知で長い健全 turn を切る（以前の false positive と同型の損失）。  
- 同じ thread に「全体を直す」夜間プロンプトを載せ続ける。

## 未確認

- compaction が **正確に何 % / 何トークン** で発火するかの Codex 製品仕様（実測は常に ~55% 付近だが閾値文書は未確認）。
- `cached_input_tokens=0` の compaction 直前サンプルが、cache 無効化を意味するか（通常 turn 中は cache が高い例もある）。
- 新 thread 切替を auto-nudge から自動化する場合の、tmux/codex-switch 手順の既存正本。
- reasoning を夜間だけ下げた場合の Step 系実装品質への影響。

## 優先順位の提案

1. 今すぐ: nudge に **nudge 上限 + 高コスト停止**、watch にコスト指標（P0）。  
2. 次: 細切れ読取 hook 強化と「受入条件で turn を閉じる」運用（P1）。  
3. 承認後: 夜間 reasoning 強度・強制 handoff 予算（P2）。

## 実装記録（2026-09-18）

P0/P1 を実装済み（本記録の提案どおり。P2 は未実施）。

| 項目 | 変更 |
| --- | --- |
| P0 nudge | `artifacts/codex-auto-nudge-once.sh`：累計上限・高コスト停止（turn≥120分 or compaction≥5）・blocked JSON。MSG に受入条件区切り／別thread／Luna委譲 |
| P0 watch | `artifacts/codex-watch-once.sh`：`cost`（turn_age_min / compacted_in_turn / slice_read_ratio / last_input_tokens / high_cost） |
| P1 hook | `RenCrow_LLM/gateway/internal/codexloopbrake`：同一ファイルへの sed -n/head を 3 回超で deny。`rencrow-llm` 再配備済み（vcs.modified=true のローカルビルド） |
| docs | `artifacts/codex-auto-nudge.md` 更新 |

**注意**: 高コスト停止後は同一 thread への auto-nudge を止める。再開は新 thread + 短い brief、または `codex-auto-nudge.state.json` の高コスト欄クリア（明示時のみ）。
