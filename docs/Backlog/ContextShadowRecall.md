# RenCrow L0v2 Shadow Recall 仕様書

## 0. 文書情報

文書名：RenCrow L0v2 Shadow Recall 仕様書
対象：RenCrow CORE / Memory / Recall / PORTAL
状態：新規実験仕様
起点：Zero-Mem: Zero-Token Memory Operations for LLM Agents（arXiv:2607.29377）
目的：現行L0を維持したまま、新しい会話想起方式を並行実装・比較評価する

---

# 1. 目的

RenCrowのL0「現在の会話」に対し、原文会話を保持したまま必要な過去発話を検索し、その前後の文脈を動的に復元する新しい想起方式 `L0v2` を実装する。

L0v2は現行L0を置き換えない。

実験期間中の実際の対話は、必ず現行L0を使用する。

L0v2は同一の会話入力をShadowとして受け取り、独立してRecallを生成する。

Legacy L0とL0v2の結果を同時に表示し、人間評価および自動計測によって比較する。

---

# 2. 最上位原則

以下を本仕様の最上位制約とする。

```text
Conversation Authority = Legacy L0

L0v2 = Shadow / Read Only

L0v2 → 実対話Agent = 禁止

L0v2 → Legacy L0 = 禁止

Legacy L0 ← L0v2 = 禁止

Raw Turn Eventのみ両系統で共有する
```

L0v2の障害、誤検索、処理遅延、停止は、通常のRenCrow会話へ影響してはならない。

---

# 3. 背景

現行L0は、現在の会話を扱う短期記憶である。

主に以下を保持・利用している。

```text
現在のthread state
直近メッセージ
rolling summary
interrupt state
その他、現在会話に必要なruntime state
```

現行方式はそのまま保持する。

一方、Zero-Mem論文では、LLMによって生成した要約を記憶の正本にせず、元のinteraction traceを保持したまま、

```text
Lexical Retrieval
Semantic Retrieval
Entity-Context Graph
Temporal Hierarchy
Evidence Closure
Deterministic Calibration
```

を利用して関連記憶を取得している。

本仕様では、この思想をRenCrow L0へ適用する。

ただしZero-Memの完全再実装は行わない。

RenCrowの現在会話に適した簡略構造として独自実装する。

---

# 4. 基本思想

L0v2では、会話を事前に要約して記憶へ置き換えない。

Raw Turnを正本とする。

また、会話をあらかじめ固定ターン数の意味単位やEpisodeへ分割しない。

基本構造は以下とする。

```text
Thread
 └ Raw Turn
```

想起時には、まず現在のユーザー入力に関連するTurnを検索する。

そのTurnを `Anchor` と呼ぶ。

Anchorが見つかった後、その前後のTurnを取得し、必要に応じて別の関連Anchorへ展開する。

基本原則は、

```text
小さく検索して、大きく思い出す
```

とする。

---

# 5. L0v2の対象範囲

初期対象は、ユーザーが「まだ現在の会話の続き」と認識できる程度の会話履歴とする。

主な評価対象は約100ターン程度とする。

ただし実装上100ターンを固定上限とはしない。

200ターン以上についてもストレステストを実施し、L0として実用可能な範囲を測定する。

---

# 6. 非対象

初期L0v2では以下を実装しない。

```text
Episode判定LLM
LLMによる記憶要約
L1の変更
L2の変更
L3の変更
Legacy L0の変更
Legacy L0へのL0v2情報注入
長期Memory Migration
Graph DB導入
複雑なKnowledge Graph生成
L0v2による実対話
```

L0v2実験を理由としてRenCrow全体のMemory Architectureを変更してはならない。

---

# 7. Turnデータ

L0v2はRaw Turnを最小単位とする。

最低限、以下を保持する。

```text
turn_id
thread_id
speaker
timestamp
raw_text
position
embedding
entities[]
```

`turn_id` はLegacy L0とL0v2で共通のTurn Eventを識別できる値とする。

L0v2固有データはLegacy L0内部へ保存しない。

---

# 8. 全体構成

```text
                    Raw Turn Event
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
        Legacy L0                  L0v2
        現行正系                   Shadow
             │                       │
      Legacy Recall              L0v2 Recall
             │                       │
             ▼                       │
         実対話Agent                  │
             │                       │
             ▼                       │
         実際の回答                    │
             │                       │
             └──────────┬────────────┘
                        ▼
                  L0 Compare Service
                        │
                        ▼
                     PORTAL
```

---

# 9. L0v2内部構成

```text
L0V2
├── TurnStore
│
├── LexicalIndexer
│     └── BM25
│
├── SemanticIndexer
│     └── Embedding
│
├── EntityIndexer
│     ├── NER
│     └── EntityContextGraph
│
├── AnchorRetriever
│
├── ContextExpander
│     ├── TemporalNeighbor
│     └── EntityBridge
│
├── RecallRanker
│
├── RecallPackBuilder
│
└── MetricsCollector
```

比較系はL0v2の外側に置く。

```text
L0CompareService
├── LegacyRecallReader
├── L0V2RecallReader
├── ComparisonLog
└── EvaluationUI
```

---

# 10. Recall処理

ユーザー入力ごとにL0v2は以下を実行する。

```text
User Query
    ↓
Lexical Search
    +
Semantic Search
    +
Recency
    ↓
Anchor候補取得
    ↓
Anchor Ranking
    ↓
上位Anchor選択
    ↓
Temporal Neighbor取得
    ↓
必要に応じEntity Bridge
    ↓
Related Anchor取得
    ↓
必要に応じ再度Neighbor取得
    ↓
Deduplicate
    ↓
Recall Budget適用
    ↓
Recall Pack生成
```

---

# 11. Anchor

現在のQueryと関連度が高い過去TurnをAnchorとする。

初期検索信号は以下とする。

```text
BM25
Embedding Similarity
Recency
```

Entity Graph導入後は以下を追加する。

```text
Entity Relation
Graph Score
```

複数Anchorを許可する。

連続していない会話範囲が最終Recall Packへ含まれることも許可する。

例：

```text
Turn 60-67
Turn 81-97
```

これを正常動作として扱う。

---

# 12. Context Expansion

AnchorがHitした場合、Anchor単体をRecall Packへ渡さない。

まず前後のTurnを取得する。

初期値は、

```text
Anchor ±3 Turn
```

とする。

その後、必要に応じて段階的に広げる。

```text
±3
↓
±6
↓
±12
↓
Related Anchor
```

固定で20ターン、50ターンなどを取得する方式にはしない。

実際に必要な会話範囲を検索結果から動的に決定する。

---

# 13. Entity-Context Graph

初期最小実装ではEntity Graphを使用しなくてもよい。

L0v2-Minの評価後に追加する。

構造は以下を基本とする。

```text
Entity
  ↕
Turn
  ↕
Neighbor Turn
```

同一Entityに関連する別Turnへ移動できるようにする。

例：

```text
Zero-Mem
 ├── Turn 40
 ├── Turn 63
 ├── Turn 84
 └── Turn 92
```

初期Entity Hopは1とする。

2 Hop以上は実測により必要性を判断する。

---

# 14. 段階実装

## 14.1 L0v2-Min

最初に以下だけを実装する。

```text
Raw Turn Store
BM25
Embedding
Temporal Neighbor
Anchor Retrieval
Context Expansion
Recall Pack
Metrics
```

目的は、

```text
関連TurnをHitする
↓
その前後を読む
```

という方式単体の効果測定である。

---

## 14.2 L0v2-Graph

L0v2-Minに以下を追加する。

```text
Entity Extraction
Entity Index
Entity ↔ Turn
Turn ↔ Neighbor Turn
Entity Bridge
Related Anchor
```

目的は、離れた会話位置に存在する同一・関連話題を接続することである。

---

## 14.3 L0v2-Full

必要性を確認した後、以下を追加する。

```text
Personalized PageRank
Query-conditioned Weighting
Evidence Closure
Deterministic Calibration
```

各機能は独立してEnable / Disable可能とする。

Ablation Testを可能にするためである。

---

# 15. Legacy L0との比較表示

PORTALまたはMemory Inspector上で、Legacy L0とL0v2を同時表示できるようにする。

Legacy側には最低限以下を表示する。

```text
Legacy Recall内容
現行Summary
現行Context
Recall Token数
Recall処理時間
```

L0v2側には最低限以下を表示する。

```text
Anchor
Anchor Score
BM25 Score
Semantic Score
Entity情報
Initial Neighbor
Expanded Range
Related Anchor
Final Recall Range
Recall Token数
Recall処理時間
```

表示例：

```text
Anchor #1
Turn 92

BM25       0.74
Semantic   0.87
Entity     Zero-Mem / L0

Initial
Turn 89-95

Expanded
Turn 81-97

Related Anchor
Turn 63
Turn 84

Final Recall
Turn 60-67
Turn 81-97
```

L0v2では「何をRecallしたか」だけでなく「なぜRecallしたか」を確認可能にする。

---

# 16. 人間評価

実会話でLegacy L0とL0v2を並べて確認する。

最低限以下の4択を提供する。

```text
Legacy L0が良い
L0v2が良い
同等
どちらも悪い
```

必要に応じて以下の補助評価を追加する。

```text
必要な記憶を拾った
0 / 1 / 2

文脈が十分だった
0 / 1 / 2

不要な記憶が少ない
0 / 1 / 2
```

評価操作はできるだけ軽くする。

複雑な多段階評価UIは初期実装では作らない。

---

# 17. 自動評価指標

## 17.1 Recall Coverage

必要な過去TurnがRecall Packに含まれた割合。

---

## 17.2 Noise Ratio

RecallされたTurnのうち不要だったものの割合。

---

## 17.3 Context Completeness

Anchorだけではなく、そのAnchorを理解するために必要な前後文脈まで取得できたかを評価する。

L0v2の主要評価指標とする。

---

## 17.4 Recall Token Cost

Recall Packとして最終的にAgentへ渡す場合に必要となるToken量を測定する。

実験期間中は実Agentへ投入しなくてもToken換算値を記録する。

---

## 17.5 Latency

以下を個別に計測する。

```text
index_update_ms
anchor_search_ms
graph_expansion_ms
context_expansion_ms
recall_pack_build_ms
total_recall_ms
```

論文値そのものを性能目標とはしない。

RenCrow Legacy L0との差分で評価する。

---

# 18. Hidden Answer Test

Shadow Recall評価が進んだ後、Legacy L0とL0v2それぞれのRecallを使用して回答を生成するHidden Testを追加する。

```text
同一User Query
    │
    ├── Legacy Recall
    │       ↓
    │    Same LLM
    │       ↓
    │    Answer A
    │       ↓
    │     ユーザー表示
    │
    └── L0v2 Recall
            ↓
         Same LLM
            ↓
         Answer B
            ↓
          非表示
```

以下を同一条件とする。

```text
LLM
System Prompt
Persona
temperature
その他Generation Parameters
User Query
```

差分はL0 Recallのみとする。

これによりRecall Packそのものだけでなく、最終回答品質への影響を比較する。

---

# 19. 初期パラメータ

以下は最適値ではなく実験開始値である。

## 19.1 Anchor候補数

```text
top_k = 5
```

---

## 19.2 Initial Neighbor

```text
anchor_neighbor = ±3 turns
```

---

## 19.3 Expansion

```text
3
6
12
Related Anchor
```

の段階Expansionを基本とする。

---

## 19.4 Entity Hop

```text
entity_hop = 1
```

---

## 19.5 Retrieval Signal

L0v2-Min：

```text
BM25
Embedding
Recency
```

L0v2-Graph以降：

```text
BM25
Embedding
Recency
Entity Relation
Graph Score
```

---

# 20. Recall Budget

固定Turn数だけでは制御しない。

最低限以下の二つを持つ。

```text
max_turns
max_tokens
```

探索は必要な範囲まで行い、最後に安全上限としてBudgetを適用する。

「50ターンまで」などを会話意味上の固定値として扱わない。

---

# 21. パラメータ調整順序

パラメータは以下の順番で調整する。

```text
Recall
↓
Context
↓
Precision
↓
Token
↓
Speed
```

## Step 1 Recall

必要情報を取りこぼさないことを優先する。

調整対象：

```text
top_k
BM25 threshold
embedding threshold
```

この段階では多少Noiseが増えても許容する。

---

## Step 2 Context

Anchor周囲の展開範囲を評価する。

比較候補：

```text
±2
±3
±5
±10
Dynamic Expansion
```

特に以下を記録する。

```text
Anchorから平均何Turn前まで必要だったか
Anchorから平均何Turn後まで必要だったか
```

実会話から適切なContext Expansionを学ぶための基礎データとする。

---

## Step 3 Precision

Recallを維持したままNoiseを減らす。

調整対象：

```text
Entity Threshold
Graph Hop
Recency Weight
Dedupe Threshold
```

---

## Step 4 Token

回答品質を維持したままRecall Packを縮小する。

---

## Step 5 Speed

最後に処理速度を最適化する。

検索品質が確立する前に高速化を優先してはならない。

---

# 22. 自動テスト

## T01 直近参照

約10ターン前の情報を質問する。

Legacy L0が得意な領域であるため、L0v2が悪化していないことを確認する。

---

## T02 遠距離参照

約80ターン前の具体情報を質問する。

---

## T03 言い換え

過去の表現：

```text
会話の前後も読みたい
```

Query：

```text
周辺文脈も復元する話、どうなった？
```

Semantic Retrievalを評価する。

---

## T04 固有名詞

以下のような固有名詞を利用する。

```text
Zero-Mem
RenCrow_CORE
Mio
```

Lexical RetrievalおよびEntity Retrievalを評価する。

---

## T05 話題復帰

```text
GPU
↓
Zero-Mem
↓
映画
↓
GPU
```

のような会話を作る。

離れたAnchor間を接続できるか評価する。

---

## T06 同一Entity多発

同じEntityを多数登場させる。

例：

```text
Mio × 50
```

現在のQueryに必要なMio関連Turnを適切に選べるか評価する。

---

## T07 訂正

```text
Turn 20
Aで進める

Turn 60
AをやめてBにする

Turn 90
現在どうなっている？
```

古い情報だけをRecallしないことを確認する。

---

## T08 複数Agent

以下のような複数Speakerを利用する。

```text
Mio
Shiro
Kuro
その他Agent
```

Speaker情報を維持したままRecallできることを確認する。

---

## T09 100 Turn

本仕様の主要想定領域。

実会話相当の100ターンで評価する。

---

## T10 200 Turn以上

L0v2の性能劣化点を確認するストレステスト。

---

# 23. 評価フェーズ

## Phase A Offline Replay

既存会話ログをL0v2へReplayする。

Legacy L0と同条件でRecall結果を比較する。

---

## Phase B Live Shadow

通常のRenCrow会話へShadow接続する。

```text
User Experience = Legacy L0

L0v2 = Shadow Only
```

L0v2の結果はCompare UIにのみ表示する。

---

## Phase C Hidden Answer

L0v2 Recallを使った回答を裏で生成し、Legacy回答と比較する。

ユーザーへの通常回答は引き続きLegacy版のみとする。

---

## Phase D Canary

十分な評価データが蓄積し、L0v2の優位性が確認された場合のみ実施する。

一部ターンでL0v2を実回答に利用する。

Phase Dへの移行は別途承認を必要とする。

---

# 24. 採用判断

L0v2は以下を満たした場合のみLegacy L0の代替候補とする。

```text
必要情報の取りこぼし
L0v2 <= Legacy

人間による選好
L0v2 > Legacy

Noise
実用範囲内

Token
Legacyと同等以下
または増加分以上の品質改善

Latency
通常会話を阻害しない
```

L0v2がLegacyより多くの情報をRecallしたという理由だけでは採用しない。

評価対象は、

```text
必要な記憶を
必要な文脈付きで
必要な量だけ
思い出せるか
```

とする。

---

# 25. 障害時動作

L0v2で以下が発生した場合、

```text
Index生成失敗
Embedding失敗
Entity抽出失敗
検索失敗
Graph処理失敗
Timeout
例外
Process停止
```

通常会話へ影響させてはならない。

L0v2処理のみを失敗として記録し、Legacy L0による会話を継続する。

---

# 26. ログ

最低限以下を記録する。

```text
event_id
thread_id
query_turn_id
timestamp

legacy_recall
legacy_recall_tokens
legacy_latency_ms

l0v2_anchor_ids
l0v2_anchor_scores
l0v2_bm25_scores
l0v2_semantic_scores
l0v2_entities
l0v2_initial_ranges
l0v2_expanded_ranges
l0v2_related_anchors
l0v2_final_ranges
l0v2_recall_tokens
l0v2_latency_ms

user_evaluation
coverage_score
noise_score
context_completeness_score

l0v2_version
parameter_set_id
```

L0v2のVersionおよびParameter Setを必ず残す。

パラメータ変更前後の比較を可能にするためである。

---

# 27. 設定管理

L0v2のパラメータをコードへ固定しない。

設定ファイルまたはRegistryから変更可能にする。

例：

```yaml
l0v2:
  enabled: true
  mode: shadow

  lexical:
    enabled: true

  semantic:
    enabled: true

  entity:
    enabled: false
    max_hops: 1

  anchor:
    top_k: 5

  expansion:
    initial_neighbor: 3
    stages:
      - 3
      - 6
      - 12
    related_anchor: true

  budget:
    max_turns: null
    max_tokens: null

  compare:
    enabled: true

  hidden_answer:
    enabled: false
```

初期値はL0v2-Min相当とする。

---

# 28. 実装順序

以下の順序で実装する。

```text
1. Legacy L0への非干渉確認

2. 共通Raw Turn Eventの取得

3. L0v2 TurnStore

4. BM25 Index

5. Embedding Index

6. Anchor Retriever

7. Temporal Neighbor

8. Recall Pack Builder

9. Metrics Collector

10. L0CompareService

11. Compare UI

12. Offline Replay Test

13. Live Shadow

14. Entity Index

15. Entity Bridge

16. Ablation Test

17. Hidden Answer Test

18. 必要ならL0v2-Full
```

Legacy L0の修正は実装手順に含めない。

---

# 29. 初期完了条件

L0v2-Minの初期実装完了条件は以下とする。

```text
Legacy L0が従来通り動作する

同一Raw TurnをL0v2が受信できる

L0v2がBM25検索できる

L0v2がEmbedding検索できる

Anchorを取得できる

Anchor前後を取得できる

Recall Packを生成できる

Legacy / L0v2を並列表示できる

評価を記録できる

Latency / Tokenを記録できる

L0v2停止時にも通常会話が継続する
```

---

# 30. 本仕様の核心

L0v2は、

```text
履歴を圧縮して覚える方式
```

ではない。

```text
必要になった会話位置を見つけ
そこから前後へ会話を再展開して
必要な文脈を思い出す方式
```

である。

Zero-Memから、

```text
原文を正本にする

LexicalとSemanticを併用する

Entityから離れた会話へ移動する

Hitした会話断片の周辺文脈を復元する
```

という考え方を採用する。

一方、RenCrow独自の判断として、

```text
Episodeを事前判定しない

固定ターン数で会話を意味分割しない

Anchorを先に発見する

Anchorから必要な範囲だけ動的に展開する
```

方式へ変更する。

---

# 31. 最終要求

本仕様の実装では、L0v2の性能向上よりもLegacy L0への非干渉を優先する。

実対話の正系はLegacy L0とする。

L0v2は十分な実会話データが蓄積し、比較評価によって優位性が確認されるまでShadowから昇格させない。

本実験の目的はZero-Mem論文の再現ではない。

**RenCrowの実際の長い会話において、「必要になった場所から会話を再展開して思い出す」という方式が、現行L0より有効かを実測することを目的とする。**

