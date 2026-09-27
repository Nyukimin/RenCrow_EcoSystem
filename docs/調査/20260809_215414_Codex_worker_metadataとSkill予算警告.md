---
title: 調査 — Codex worker metadataとSkill予算警告
date: 2026-08-09 21:54 JST
status: confirmed
skill: debug-investigate
symptom: codex-gpt120b起動時にworkerのmodel metadata fallback警告とSkill説明短縮警告が表示される
frequency: codex-gpt120bの新規セッション起動時
inputs: ユーザー貼付画面、ローカルCodex設定、Codex CLI 0.147.0、公式openai/codexソース
related: なし
---

## 概要

`codex-gpt120b` はカスタムモデル名 `worker` を選ぶが、Codexのモデルカタログにそのslugがないため、Codex CLI 0.147.0は汎用metadataを適用する。応答通信は成功するが、並列Tool呼び出し等の能力が保守的に無効扱いとなる。Skill警告は、モデル可視の60 Skillのmetadataが割当予算を超え、説明だけが短縮されたことを示す。

## 調査経緯

### 仮説1: カスタムモデル名workerがCodexモデルカタログにない

- **根拠**: `codex-gpt120b` が `codex -p rencrow-gpt120b` を起動し、同profileが `model = "worker"` を指定する。
- **検証結果**: 確認
- **証拠**:
  - `/home/nyukimi/.local/bin/codex-gpt120b:4` は `exec codex -p rencrow-gpt120b "$@"`。
  - `/home/nyukimi/.codex/rencrow-gpt120b.config.toml:1-2` は `model = "worker"`、`model_provider = "rencrow"`。
  - `/home/nyukimi/.codex/models_cache.json` の9モデルに `worker` は存在しない。
  - Codex CLIバイナリには、未知モデルにfallback metadataを適用する同一警告文が埋め込まれている。
  - 反証: 標準profileの `model = "gpt-5.6-sol"` はカタログに存在し、今回の `worker` 警告の原因ではない。
- **チェックリスト結果**:
  - [x] 確証バイアス: profile、モデルキャッシュ、CLIバイナリの3経路を照合した。
  - [x] 頻度制約: `worker` profileを選ぶ新規セッションで成立する条件と観測が一致する。
  - [x] ライフサイクル: start/stopや資源解放を伴わない起動時metadata解決であり、ペア操作は非該当。
  - [x] 既存知見: `docs/調査/` とmemory registryに同じCodex警告の既存調査はなかった。

### 仮説2: Skill個別破損ではなく、全Skill metadataが予算を超えている

- **根拠**: 警告は「全Skillは見えているが一部descriptionを短縮した」と明記する。
- **検証結果**: 確認
- **証拠**:
  - `codex -p rencrow-gpt120b debug prompt-input` の実効一覧は60件。
  - 内訳は `.agents/skills` 33件、`.codex/skills` 21件、codex plugin 3件、sites plugin 2件、visualize plugin 1件。
  - Skill節を含むdeveloper inputは19,760文字。
  - 公式 `openai/codex` の `codex-rs/ext/skills/src/render.rs` はmetadata予算をcontext windowの2%、個別description上限を1,024文字、fallback予算を8,000文字と定義し、同じ警告文を生成する。
  - 反証: 警告はSkill omissionではなくdescription shorteningであり、実効一覧でも60件すべてにlocatorが残っている。
- **チェックリスト結果**:
  - [x] 確証バイアス: install済み総数ではなく、`debug prompt-input` の実効モデル入力を確認した。
  - [x] 頻度制約: 読み込まれるSkill集合が同じ新規セッションでは再発する。
  - [x] ライフサイクル: Skill catalogの起動時レンダリングであり、ペア操作は非該当。
  - [x] 既存知見: 関連する過去調査はなかった。

## 根本原因

- **原因1**: RenCrow用profileがCodexの既知slugではない `worker` を指定している。
- **メカニズム1**: Codexは未知slugに汎用ModelInfoを生成する。現行公式ソースのfallbackはcontext window 272,000、effective 95%を持つ一方、parallel tool calls、verbosity、model specialty、tool mode等を未対応として扱う。
- **原因2**: モデル可視Skillが60件あり、説明metadataの合計がCodexのSkill予算を超える。
- **メカニズム2**: CodexはSkill自体を除外する前にdescriptionを短縮する。今回の文言はこの第一段階に対応する。
- **影響範囲**: `codex-gpt120b` の全セッション。Skill警告は同じSkill集合をロードする他profileでも発生し得る。

## 修正案

1. Codex側でカスタムmodel metadataを宣言できる正式設定があるなら、`worker` の実契約に合わせて登録する。現行config referenceとCLI helpでは、その公開設定項目を確認できていない。
2. 登録手段がない場合は、警告を消すためだけに既知OpenAI slugへ偽装しない。能力誤認とGateway契約不一致を招くため、Codex側のcustom-provider metadata対応を待つか上流へ要望する。
3. Skill警告は、通常使わない大群から削る。優先候補は `.agents/skills` のApify 12件、Understand Anything 8件、重複している `skill-creator`、`skill-installer`、`idlechat-story-tuning`、`launch-readiness-qa-loop`。
4. plugin単位では、利用しないセッションで `codex` 3件、`sites` 2件、`visualize` 1件を無効化できる。ただし主因はpluginだけでなくlocal/agents Skillの多さである。

## 関連ソースファイル

- `/home/nyukimi/.local/bin/codex-gpt120b:4` - RenCrow profileを選ぶwrapper。
- `/home/nyukimi/.codex/rencrow-gpt120b.config.toml:1` - 未知slug `worker` の指定。
- `/home/nyukimi/.codex/models_cache.json` - 現在の既知モデルカタログ。
- `openai/codex:codex-rs/models-manager/src/model_info.rs` - 未知slug用fallback ModelInfo。
- `openai/codex:codex-rs/ext/skills/src/render.rs` - Skill metadata予算、短縮、警告判定。

## 教訓（将来の調査への知見）

- カスタムproviderへの応答成功と、Codexがmodel capabilityを正しく理解していることは別に検証する。
- Skill警告はinstall済み件数ではなく、`codex debug prompt-input` の実効モデル入力で判定する。
- 警告を消す目的でmodel slugを偽装せず、backend実契約とCodex metadataを一致させる。
