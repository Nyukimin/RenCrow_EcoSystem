# LLM Ops Cursor再開 — ブロッカー（fujitsu-ubunts）

作成: 2026-09-15 17:48 JST  
正本: [20260915_174041_llmfit_Ops統合_Cursor引き継ぎ.md](20260915_174041_llmfit_Ops統合_Cursor引き継ぎ.md)

## 結論

P0（`docs/06` の `llm_capability` 追随）は **このホストでは実行できない**。  
LLM Ops の4コミット（`56501f4d` / `08a31a71` / `cd5baae9` / `656184df`）が **GitHub `origin/main` にも、この CORE checkout にも無い**。未 push の Mac 作業ツリーが唯一のソース。

identity 作業ツリー（`identity/03-dci`）へ docs だけ足すことは、危険地帯の混在になるため行っていない。本番再起動・config 追記もしていない。

## このホストの実測（2026-09-15 17:48 JST）

| 項目 | 値 | 引き継ぎ資料との一致 |
| --- | --- | --- |
| hostname | `fujitsu-ubunts` | 一致（本番 CORE） |
| CORE checkout | `/home/nyukimi/RenCrow/RenCrow_CORE` branch `identity/03-dci` HEAD `d307b0c` | Mac `main`+4 とは別線 |
| `08a31a71` 等 | object 不在 / `origin/main` 先頭は `bd602f9` | 未 push 仮説と一致 |
| `~/.local/bin/rencrow` | 2026-09-14 17:27 / `3022ba2b-worktree-gmail-xlink` / `vcs.modified=true` | 一致 |
| `rencrow.bak.*` | 無し | 一致 |
| `llmfit.service` | `active` | 一致 |
| `GET :8787/health` | `status: ok` | 一致 |
| `core.yaml` | `llm_ops:`（LLM mgmt daemon）あり、`llm_capability:` 無し | 一致 |

## 次に必要な入力

1. Mac 上 CORE を push する、または `656184df` を含む bundle / patch をこのホストへ渡す
2. その tree でだけ `docs/06` の `llm_ops.llmfit.*` → `llm_capability.llmfit.*` を直す
3. その後、確認を取ってから linux amd64 ビルドと本番配置

## 本番配備手順（未実行・確認後）

1. LLM Ops のみの tree（`656184df` 以降、他差分なし）で `GOOS=linux GOARCH=amd64` ビルド
2. `~/.local/bin/rencrow.bak.<日時>` へ現行バイナリ退避 + sha256
3. `~/.rencrow/config/core.yaml` を同形式でバックアップ
4. 新バイナリ配置
5. `llm_capability.llmfit.nodes` を追記（退役 `llm_ops:` は触らない）
6. 既存 `rencrow` user unit で再起動
7. Viewer Ops → LLM Ops を目視
8. push は別途明示指示

```text
目的: 引き継ぎどおり P0 docs/06 を行う
制約: 他差分非混在、未 push ソースを捏造しない、本番は確認後
仮説: ソースは Mac のみ
検証: fetch origin/main、object 検索、本番 binary/config/llmfit
判断: ブロッカー報告。docs 改変・配備は停止
次の一手: Mac 側ソースの到着方法を確認する
```
