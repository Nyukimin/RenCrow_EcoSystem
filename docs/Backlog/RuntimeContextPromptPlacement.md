# Runtime Context の prompt 配置と KV prefix 安定性 仕様

**Status:** 設計決定案（未実装）
**Date:** 2026-09-18
**Scope:** RenCrow_CORE の LLM middleware、RenCrow_LLM Gateway の system message normalization
**Owner:** RenCrow_CORE（変更本体）／RenCrow_LLM（契約の被参照側、変更なし）

---

## 1. 目的

現在時刻のような **runtime 可変コンテキスト**を prompt のどこへ置くかを固定し、
物理 LLM の KV prefix cache を壊さないことを構造で保証する。

対象は「毎 request 値が変わるが、意味としては付随情報でしかない」文字列すべてであり、
現時点の唯一の実体は現在時刻だが、本仕様は将来同種のものが追加されても同じ配置規則に従わせる。

---

## 2. 背景 — 観測された事実

2026-09-18 に Worker 高速化の調査中、`~/.rencrow/logs/llm_prompt_debug.jsonl`
（7,916 件の `target_sent`）を解析して次を確認した。

### 2.1 秒単位の時刻が先頭 system ブロックに入っている

人物関連カタログの要約翻訳（`caller: core.unattributed`）の実 payload:

```
--- system ---
作品概要の本文だけを自然な日本語へ翻訳してください。…

【重要】現在時刻（JST）: 2026-09-09 13:11:46 JST。この日時を正確な現在時刻として扱ってください。…
--- user ---
source_language=en
description_original=1999 studio album by Tomoyo Harada
```

### 2.2 実装が自身の設計意図と食い違っている

`RenCrow_CORE/internal/infrastructure/llm/middleware/datetime.go` の doc comment:

```go
// Generate は安定した履歴prefixを保ったまま、最新user messageへ現在日時を注入する。
// 動的な日時を先頭へ置くと、日時が変わるたびに物理LLMのprompt cacheが全失効するため、
// 既存contextを削らず末尾側だけを変化させる。
```

意図は「**最新 user message へ**注入」だが、`injectGenerateDateTime` /
`injectChatDateTime` は `Role: "system"` の独立メッセージを生成し、
最後の user message の直前へ挿入している。

### 2.3 Gateway の正常動作が意図を打ち消している

`shiro_worker` / `shiro_chatworker` / `coder_pool` には
`system_message_mode: "single_leading_instruction"` が設定されている。
`RenCrow_LLM/gateway/internal/messagewire/system_messages.go` は仕様どおり

```go
leading["content"] = strings.Join(instructionParts, "\n\n")
payload["messages"] = append([]any{leading}, nonSystem...)
```

で **全 system メッセージを連結して先頭へ移す**。CORE が末尾へ置いた時刻は
ここで先頭へ引き戻される。Gateway 側に誤りは無い。

### 2.4 alias 別の実測

| alias | 件数 | 時刻注入 | 最大 msgs | 最大 KiB |
| --- | ---: | ---: | ---: | ---: |
| shiro (ChatWorker) | 5,285 | 3,121 | 3 | 24.8 |
| worker | 2,072 | 488 | 201 | 382.9 |
| mio | 42 | 11 | 22 | 22.6 |
| coder1 | 141 | 0 | 6 | 70.2 |
| midori | 24 | 0 | 33 | 138.3 |
| coder2 | 50 | 2 | 31 | 132.0 |

Codex 経路（`worker` の 201 メッセージ級）は CORE を通らないため時刻注入を受けない。
system prompt の hash は 726 request にわたり一定（`992aa58c`）であることを確認済み。

---

## 3. 機構

```text
CORE が組むもの:
  [system:指示] [履歴...] [system:時刻] [user:最新]
                             ↑ 末尾寄り。意図どおり

Gateway (single_leading_instruction) 通過後:
  [system:"指示\n\n時刻"] [履歴...] [user:最新]
   └─ 安定 ─┘└ 毎秒変化 ┘ └─ ここから後ろが全部 cache 不可 ─┘
```

KV prefix cache は **先頭からの一致長**でのみ効く。
時刻トークンより後ろは、内容が同一でも再 prefill になる。

---

## 4. 影響範囲

### 4.1 現状は軽微である

マージ後の順序が `[安定した指示] → [時刻]` なので、**安定部分は現在も cache できている**。
壊れるのは時刻より後ろだけで、CORE の呼び出しは実測で最大 3 メッセージと短く、
時刻の後ろにほとんど何も続かない。**現時点で体感速度は変わらない。**

件数は関係しない。短い翻訳を何万件流しても本件では遅くならない。

### 4.2 刺さるのは「時刻の後ろに大きな安定ブロックが続く」形

```text
[system:指示] [履歴100件] [system:時刻] [user:最新]
   → [system:"指示\n\n時刻"] [履歴100件] [user:最新]
                              ↑ 履歴100件が毎 request 再 prefill
```

Chat / IdleChat が CORE 経由で長い履歴を送る構成になった時点で顕在化する。
計測済みの prefill 速度は約 1,850 tok/s なので、64K トークンの履歴で 1 request あたり
**約 35 秒**の再計算に相当する。

**本仕様は予防的修正である。** 現在の遅さの原因ではない。

---

## 5. 不変条件

`docs/agent-task-rules.md` が既に定めている次を、CORE 側の実装で機械的に満たす。

> System／Tools 領域への additionalContext／動的プロンプト積み増しは禁止（KV prefix を壊す）

追加で本仕様が固定するもの。

- **I1**: prompt は `[不変] → [低頻度変化] → [高頻度変化]` の順に並べる。
  runtime 可変コンテキストは常に最も後ろ側へ置く。
- **I2**: runtime 可変コンテキストを `system` / `developer` ロールで送らない。
  これらのロールは Gateway の `single_leading_instruction` / `single_leading` が
  先頭へ集約する契約であり、集約自体は正しい動作である。
- **I3**: 配置規則は送信側（CORE）が守る。Gateway の normalization を
  例外化して回避しない。

---

## 6. 変更方針

### 6.1 変更する場所

**`RenCrow_CORE/internal/infrastructure/llm/middleware/datetime.go` の 1 ファイルのみ。**

`injectGenerateDateTime` / `injectChatDateTime` が生成する時刻メッセージを、
doc comment が既に宣言しているとおり **最新 user message 側**へ移す。
`Role: "system"` を使わないことで I2 を満たし、Gateway の集約対象から外れる。

冪等性チェック `generateRequestHasCurrentJSTTime` / `chatRequestHasCurrentJSTTime` は
現在 `SystemPrompt` と system ロールのみを走査しているため、新しい配置に合わせて更新する。
これを怠ると retry 時に二重注入が起きる。

### 6.2 変更しない場所

- **RenCrow_LLM の `messagewire`**: 仕様どおり動作しており、変更する理由が無い。
  `single_leading_instruction` は「後続 system ロールを受け付けない target」への
  正しい wire 正規化である。
- **`system_message_mode` の設定値**: `preserve` へ逃がすと、Backend の
  chat template 契約を壊す。
- **Codex 経路**: CORE を通らないため対象外。

### 6.3 ブランチ

`RenCrow_CORE` の `main` で実施する。対象 3 ファイル
（`datetime.go`、`runtime_person_related_summary_translation.go`、
`runtime_person_related_summary_worker.go`）は 2026-09-18 時点で
`main` と作業ブランチ `identity/03-dci` の差分が 0 行であり、衝突しない。

`make check-workspace` は「CORE worktree HEAD == component source pin」を要求するため、
作業ブランチの worktree で `main` を checkout してはならない。
`Tmp/worktrees/` に `main` の worktree を切って作業する
（既存例: `Tmp/worktrees/core-development-methodology-v1`）。

---

## 7. 受入条件

1. CORE が Gateway へ送る payload で、時刻文字列が**先頭 system ブロックに含まれない**。
2. 同一会話・同一時刻以外の条件で連続 2 request を送ったとき、
   **先頭 system ブロックが byte 一致**する。
3. 時刻情報がモデルへ届いており、時刻を問う質問へ正しく答えられる（機能の非退行）。
4. retry / 再送で時刻が二重注入されない。
5. `single_leading_instruction` 以外の target（`preserve` 系）でも順序が壊れない。
6. 既存の datetime middleware の unit test が通り、配置を検証する test が追加されている。

---

## 8. 検証手順

### 8.1 実装前後で共通の観測コマンド

`RENCROW_LLM_PROMPT_DEBUG_LOG` が有効な状態で CORE 経由の呼び出しを発生させ、
先頭 system ブロックの hash 分布を見る。

```bash
python3 - /home/nyukimi/.rencrow/logs/llm_prompt_debug.jsonl <<'EOF'
import sys,json,hashlib,collections
c=collections.Counter(); ng=0
for line in open(sys.argv[1],encoding='utf-8',errors='replace'):
    try: d=json.loads(line)
    except: continue
    if d.get('stage')!='target_sent': continue
    if not (d.get('metadata') or {}).get('caller','').startswith('core'): continue
    try: ms=json.loads(d.get('payload_text') or '{}').get('messages') or []
    except: continue
    if not ms or ms[0].get('role')!='system': continue
    s=ms[0].get('content')
    if not isinstance(s,str): continue
    c[hashlib.sha256(s.encode()).hexdigest()[:8]]+=1
    if '現在時刻（JST）' in s: ng+=1
print('core起点 request:',sum(c.values()))
print('先頭systemに時刻が入っていた件数:',ng)
print('先頭systemのユニーク版数:',len(c))
EOF
```

実装前のベースライン（2026-09-18 実測、上記コマンドを実行して取得）:

```text
core起点 request: 5394
先頭systemに時刻が入っていた件数: 3234
先頭systemのユニーク版数: 2945
```

**期待**: 受入条件 1・2 を満たす場合、「先頭systemに時刻が入っていた件数」が **0** になり、
ユニーク版数が呼び出し種別の数（persona／用途の数程度）まで縮む。

### 8.2 非退行の確認

正規 route（Gateway alias 経由、CORE 起点）で時刻を問い、現在時刻が返ることを確認する。
Backend 直叩きや internal function での代用は受入としない。

### 8.3 module 検査

`RenCrow_CORE` の既存ローカル検査に従う。関連 Go test、`go vet ./...`、`go build ./...`。

---

## 9. 非目標

- 現在の Codex 体感速度の改善。本仕様は寄与しない。
- `model_reasoning_effort`、`--ctx-size`、`--prefix-cache-mem` 等のパラメータ調整。
- `worker` alias を複数ワークロードで共有している構成の是正（別件）。
- `caller: core.unattributed` / `purpose: unattributed` という provenance 欠落の是正（別件）。

---

## 10. 参照

- `RenCrow_CORE/internal/infrastructure/llm/middleware/datetime.go` — 変更対象
- `RenCrow_LLM/gateway/internal/messagewire/system_messages.go` — 被参照側契約
- `RenCrow_CORE/cmd/rencrow/runtime_person_related_summary_translation.go` — 観測に使った実 caller
- `docs/agent-task-rules.md` — KV prefix に関する既存の禁止事項
- `RenCrow_LLM/docs/調査/20260918_061500_Worker_MTP未使用による低速化.md` — 本件を発見した調査
- `docs/調査/20260918_102400_codex長時間ターンとcompaction_原因と対策.md` — Codex 側のコスト構造（別要因）
