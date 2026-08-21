RenCrow Memory Verification Tool 仕様

Version: 0.1 Draft
対象: RenCrow_CORE
分類: Tools
目的: RenCrowの記憶・想起方式を、再現可能な条件で比較・回帰検証する

1. 目的

RenCrow Memory Verification Tool は、RenCrowの記憶機構そのものではない。

Memory / Recall を外部から検証する開発・評価用Toolとする。

主目的は次の4点。

現行Memory実装の品質を定量評価する

新しいMemory方式を現行方式と同条件で比較する

パラメータ変更による改善・悪化を検出する

「検索できなかった」「RecallPackで落ちた」「LLMが使わなかった」を分離して原因分析する

特に当面は、

Legacy L0
    vs
New L0

を同一データ・同一質問・同一LLM条件で比較できることを最優先とする。

新L0は評価期間中、現行L0を置き換えない。

2. 位置づけ

論理配置は以下とする。

RenCrow
├─ CORE
├─ Memory
├─ Agents
├─ Tools
│   └─ Memory Verification
│       ├─ MemoryAgentBench
│       ├─ RenCrow Adapter
│       ├─ RenCrow Native Tests
│       ├─ Metrics
│       └─ Reports
└─ ...

物理配置はGo/Pythonの一般的な構成に合わせ、

tools/memory_verification/

を推奨する。

MemoryAgentBenchはMemory機構として取り込まない。

外部Benchmark Engineとして扱う。

MemoryAgentBenchは、Accurate Retrieval、Test-Time Learning、Long-Range Understanding、Conflict Resolutionの4能力を評価し、長いデータをchunkに分割して逐次投入したあと複数質問を行う構造になっている。

3. 設計原則

3.1 Production Memoryを汚さない

検証データは、

user:<uid>
char:<persona>
kb:<domain>

など通常のRenCrow名前空間に書き込まない。

検証専用namespaceを設ける。

bench:<run_id>:<variant>:<context_id>

例:

bench:20260817_001:legacy_l0:0032
bench:20260817_001:candidate_l0:0032

検証終了後はnamespace単位で削除可能とする。

3.2 比較対象以外を固定する

Memory方式を比較するときは、

LLM
SystemPrompt
temperature
generation parameter
入力データ
質問
質問順
RecallPack上限

を原則固定する。

変えるのは検証対象のMemory方式または指定パラメータだけとする。

3.3 一つの総合点に潰さない

初期版では、

Memory Score = 83点

のような単一スコアを主評価にしない。

理由は、

検索精度が高い
しかし古い情報を使う

検索精度は少し低い
しかし誤想起が非常に少ない

を同じ数値へ潰すと、RenCrowにとって重要な違いが消えるため。

評価は複数軸で保持する。

これはRenCrow独自追加仕様とする。

4. 検証システム全体構成

                 Test Dataset
                     │
          ┌──────────┴──────────┐
          │                     │
 MemoryAgentBench       RenCrow Native Tests
          │                     │
          └──────────┬──────────┘
                     │
             Benchmark Runner
                     │
             RenCrow Adapter
                     │
         ┌───────────┴───────────┐
         │                       │
     Legacy Memory          Candidate Memory
         │                       │
         └───────────┬───────────┘
                     │
               RenCrow CORE
                     │
               Trace Collector
                     │
              Metrics Engine
                     │
              Diff / Report

MemoryAgentBench自身もcontext chunkを順番に memorizing=True で投入し、記憶構築後に質問を行う。

質問時は memorizing=False で同一contextに対して複数queryを実行する構造である。

したがってRenCrow Adapterとの接続は薄くできる。

5. RenCrow Adapter

Python側に以下を実装する。

RenCrowBenchAdapter

基本インターフェース:

create_session()
memorize()
query()
inspect_recall()
reset()
close()

概念的には、

MemoryAgentBench

send_message(chunk, memorizing=True)
        ↓
RenCrowBenchAdapter.memorize()

send_message(question, memorizing=False)
        ↓
RenCrowBenchAdapter.query()

と変換する。

RenCrow本体へMemoryAgentBench固有コードを入れない。

6. Test Session

各試験contextについて独立したTest Sessionを生成する。

{
  "run_id": "20260817_001",
  "context_id": "0032",
  "variant": "candidate_l0",
  "namespace": "bench:20260817_001:candidate_l0:0032"
}

Session間でMemoryを共有してはならない。

これにより、

前のテストの記憶が次のテストへ漏れる

事故を防ぐ。

7. Memory Variant

最低限、次のvariantを扱えるようにする。

legacy_l0
candidate_l0

legacy_full
candidate_l0_full

long_context
bm25
vector
hybrid

ただし初期実装では、

legacy_l0
candidate_l0

の2つだけでよい。

他方式は後から追加可能なPlugin型とする。

8. Legacy L0 / New L0 並列評価

今回の中心機能。

会話入力を分岐する。

User / Assistant Turn
        │
        ├────────→ Legacy L0
        │
        └────────→ New L0

両者へ完全に同じturnを投入する。

ただし通常運用中は、

Legacy L0
    ↓
実際の会話

のみを利用する。

New L0は、

Shadow

として記憶・検索結果だけ生成する。

つまり新L0が壊れていても通常会話へ影響しない。

9. 実行モード

9.1 Benchmark Mode

完全に独立した試験。

Dataset
 ↓
Legacy
 ↓
Answer

Dataset
 ↓
Candidate
 ↓
Answer

→ 比較

最も再現性が高い。

9.2 Replay Mode

実際のRenCrow会話ログを再生する。

過去Conversation
      ↓
Turn Replay
      ↓
Legacy / Candidate

実運用データに近い比較ができる。

9.3 Shadow Mode

通常会話中に、

Legacy → 実際に使用
Candidate → 裏で計算のみ

とする。

保存対象:

Legacy Recall
Candidate Recall
差分
Latency
Token

回答生成はLegacyだけでよい。

9.4 Paired Evaluation Mode

LegacyとCandidateの両方から独立して回答を生成する。

same question

      ┌→ Legacy Recall → Same LLM → Answer A
input │
      └→ New Recall    → Same LLM → Answer B

最終的な品質比較用。

10. MemoryAgentBench標準試験

MemoryAgentBenchの4カテゴリーをそのまま保持する。

10.1 Accurate Retrieval

必要な記憶を正確に取り出せるか。

RenCrowでは特に、

L0 hit
対象turn検索
固有名詞
過去の発言

の基本性能を見る。

10.2 Conflict Resolution

矛盾する新旧情報から正しいものを採用できるか。

これはRenCrowでは非常に重要。

例:

Turn 10
好きな色は青

Turn 80
最近は緑の方が好き

質問:

現在好きな色は？

古い「青」が強く残ってしまうMemoryは失敗。

10.3 Long-Range Understanding

離れた場所に存在する複数情報を統合できるか。

L0だけでなく、

L0
L1
L2
L3

を跨ぐ想起評価にも拡張する。

10.4 Test-Time Learning

会話中に与えられたルールや新知識を、その場で学習・利用できるか。

RenCrowでは、

ユーザー固有ルール
用語
プロジェクト内ルール
一時的制約

へ応用する。

11. RenCrow Native Test

ここからはMemoryAgentBenchにはない、RenCrow独自追加試験とする。

RC-01 Online Interleaved Memory

MemoryAgentBenchは基本的に、

記憶投入
記憶投入
記憶投入
質問
質問
質問

である。

RenCrowの実際の会話は、

記憶
質問
記憶
質問
更新
質問

となる。

したがって、

memorize
query
memorize
query
update
query

を混ぜた試験を追加する。

12. RC-02 Temporal Conflict

時間による事実更新を検証する。

例:

T1  A
T2  B
T3  AをBへ変更
T4  Question

評価項目:

最新情報採用率
旧情報誤採用率
更新時刻認識

Conflict ResolutionをRenCrow向けに強化したもの。

13. RC-03 Namespace Isolation

RenCrow専用の重要試験。

user:A
user:B

char:Mio
char:Kuro

thread:A
thread:B

kb:movie
kb:software

を意図的に混在させる。

質問に関係しないnamespaceからMemoryが漏れたら失敗。

指標:

namespace_leak_count
namespace_leak_rate

Critical Testとする。

14. RC-04 Memory Lifecycle

Memory候補について、

observed
 ↓
candidate
 ↓
confirmed

という段階管理を試験対象とする。

さらに、

confirmed
superseded
forgotten

を検証する。

例:

覚えて
↓
想起される

これは違う
↓
superseded

忘れて
↓
想起されない

特に、

forgotten memory recall

はCritical Failureとする。

15. RC-05 L0 Neighbor Retrieval

新L0方式専用。

新L0で検索Hitしたturnだけではなく、

Hit Turn
   ↓
前後Nターン

を取得する方式を評価する。

例:

Turn 145
質問の前提

Turn 146
対象情報

Turn 147
補足条件

146だけ検索すると意味が壊れる可能性がある。

そこで、

hit_turn
neighbor_before
neighbor_after

をセットで取得する。

設定:

candidate_l0:
  neighbor_before_turns: 20
  neighbor_after_turns: 20

ただし20は固定値ではない。

Parameter Sweep対象にする。

例:

10
20
40
80

ここで、

Recall精度
ノイズ増加
RecallPack Token
Latency

を比較する。

16. RC-06 Negative Recall

Memory評価では「覚えているか」だけでなく、

思い出さなくていいものを思い出さない

性能も評価する。

例えば料理の話をしているのに、

3年前のGPU購入相談

がRecallPackへ混ざれば、検索としてhitしていても会話品質は悪化する。

指標:

irrelevant_recall_rate
false_recall_rate

を追加する。

17. RC-07 Cross-Layer Recall

同じ情報を、

L0
L1
L2
L3

へ異なる形で配置する。

そして、

どのLayerを採用したか
重複したか
古いLayerを優先したか

を見る。

18. 3段階評価

最終回答だけ採点しない。

Memory Retrieval
      ↓
RecallPack
      ↓
LLM Answer

をそれぞれ採点する。

Stage 1 Retrieval

Memoryが正しい情報を見つけたか。

記録:

retrieved_memory_ids
score
layer
turn_range
rank

Stage 2 RecallPack

取得したMemoryのうち、何が実際にLLMへ渡されたか。

記録:

selected_memory_ids
dropped_memory_ids
token_count

Stage 3 Answer

最終的にLLMが正しく利用したか。

これにより、

Memory検索は成功
↓
RecallPack Builderが捨てた
↓
回答失敗

と、

Memory検索成功
↓
RecallPackにも存在
↓
LLMが誤回答

を区別できる。

これを分離しないと、LLMの失敗をMemoryアルゴリズムの失敗だと誤判定する。

19. Metrics

19.1 Answer Quality

MemoryAgentBench公式値を保存する。

substring_exact_match
exact_match
Recall@5
LLM Judge

ただしRenCrowでは自然言語回答が多いため、

official_score
normalized_score

を両方保存する。

公式scoreはBenchmark比較のため変更しない。

19.2 Retrieval Quality

recall@k
precision@k
MRR
evidence_coverage
irrelevant_recall_rate
stale_memory_rate
namespace_leak_rate

19.3 RecallPack Quality

selected_relevant_rate
duplicate_rate
dropped_required_evidence
recall_pack_tokens

19.4 Runtime

memory_ingest_ms
index_build_ms
retrieval_ms
recall_pack_build_ms
generation_ms
end_to_end_ms

input_tokens
recall_tokens
output_tokens

20. Test Result Format

1 queryにつき1レコード保存する。

{
  "run_id": "20260817_001",
  "variant": "candidate_l0",
  "suite": "RC_TEMPORAL",
  "context_id": "ctx_0032",
  "query_id": "q_004",
  "question": "...",
  "expected": "...",

  "answer": "...",

  "retrieval": {
    "hits": [],
    "selected": [],
    "dropped": []
  },

  "metrics": {
    "official_score": 1,
    "normalized_score": 1,
    "recall_at_5": 1.0,
    "irrelevant_recall_rate": 0.0
  },

  "timing": {
    "retrieval_ms": 31,
    "pack_ms": 4,
    "generation_ms": 820
  },

  "tokens": {
    "recall": 850,
    "input": 2100,
    "output": 120
  }
}

JSONLを正本とする。

21. 再現性情報

各runには必ず、

RenCrow commit SHA
MemoryAgentBench commit SHA
dataset revision
model
model revision
SystemPrompt hash
config hash
temperature
seed
timestamp

を保存する。

MemoryAgentBenchは更新されるため、upstreamのcommitを固定しない比較は禁止する。

MemoryAgentBenchはMIT Licenseであるため、RenCrow Tools内へvendorする場合も著作権表示とlicense文を保持する。

22. Report

最低限、以下を生成する。

summary.md
results.jsonl
diff.html

特に diff.html を重視する。

表示例:

Query #48

Expected
────────────────
緑

Legacy L0
────────────────
Answer: 青
Hit: Turn 12
Score: NG
Recall: 320 tokens
Latency: 18ms

New L0
────────────────
Answer: 緑
Hit: Turn 84
Neighbors: 78-90
Score: OK
Recall: 610 tokens
Latency: 25ms

さらに、

Legacy RecallPack
New RecallPack

を横並びで見られるようにする。

人間の目でも「なぜこちらが良かったか」を追跡できることを重視する。

23. Parameter Sweep

New L0はパラメータを固定せず、一括比較可能にする。

例:

sweep:

  neighbor_turns:
    - 10
    - 20
    - 40
    - 80

  top_k:
    - 1
    - 3
    - 5

  recall_token_budget:
    - 500
    - 1000
    - 2000

組み合わせごとにRunを分離する。

24. Winner判定

単純加重平均にはしない。

優先順位を設ける。

1. Critical Error
2. Answer Correctness
3. Retrieval Quality
4. Recall Noise
5. Token Cost
6. Latency

例えば、

Candidate A
Accuracy 95%
Leak 1件

Candidate B
Accuracy 93%
Leak 0件

なら、Aを単純に勝者にはしない。

Namespace leakage、forgotten memory recallなどは安全側のHard Gateとして扱う。

25. L0移行判定

新L0はBenchmarkで勝っただけではProductionへ昇格しない。

段階を踏む。

Benchmark
   ↓
Replay
   ↓
Shadow
   ↓
Paired Evaluation
   ↓
Production Candidate

つまり、

実験室では強い
↓
実際の長期会話では弱い

を防ぐ。

26. 実装ディレクトリ

初期案。

tools/
└─ memory_verification/
   ├─ README.md
   │
   ├─ third_party/
   │  └─ MemoryAgentBench/
   │
   ├─ adapter/
   │  └─ rencrow_adapter.py
   │
   ├─ runner/
   │  ├─ benchmark.py
   │  ├─ replay.py
   │  └─ shadow.py
   │
   ├─ suites/
   │  ├─ memory_agent_bench/
   │  └─ rencrow_native/
   │     ├─ online/
   │     ├─ temporal/
   │     ├─ namespace/
   │     ├─ lifecycle/
   │     ├─ negative_recall/
   │     └─ l0_neighbor/
   │
   ├─ metrics/
   │  ├─ retrieval.py
   │  ├─ recall_pack.py
   │  ├─ answer.py
   │  └─ runtime.py
   │
   ├─ configs/
   │  ├─ legacy_l0.yaml
   │  ├─ candidate_l0.yaml
   │  └─ sweep.yaml
   │
   ├─ results/
   └─ reports/

Benchmark部分はPythonのまま使う。

RenCrow_COREをMemoryAgentBenchへ合わせてPython化したり、MemoryAgentBenchをGoへ移植したりしない。

27. 実装Phase

Phase 1

MemoryAgentBench導入
RenCrow Adapter
Legacy L0接続
Candidate L0接続
JSONL結果保存

ここまでで、

同じ試験を旧L0と新L0へ流せる

状態にする。

Phase 2

Retrieval Trace
RecallPack Trace
左右比較Report
Parameter Sweep

ここで新L0の調整を開始できる。

Phase 3

Temporal Conflict
Namespace Isolation
Negative Recall
Lifecycle
Online Interleaved

RenCrow固有試験を追加する。

Phase 4

Replay Mode
Shadow Mode

実際の会話で評価する。

Phase 5

回帰テスト化する。

memory-bench-smoke
memory-bench-full

軽量版は変更時に実行。

Full Benchmarkは手動または定期実行とする。

28. 最終的な思想

このToolsの目的は、

「新しいMemoryのスコアが高かった」

だけを確認することではない。

RenCrowとして知りたいのは、

ちゃんと思い出したか
        ↓
正しい記憶を選んだか
        ↓
余計なものを思い出さなかったか
        ↓
RecallPackへ正しく入ったか
        ↓
LLMが正しく使ったか
        ↓
そのために何ms・何token使ったか

である。

そのため、

MemoryAgentBenchを共通試験として利用し、その上にRenCrow専用の「時間・名前空間・忘却・オンライン会話・RecallPack」の試験を被せる。

この構造により、今回の新L0だけでなく、将来的な以下の変更も同一Toolsで検証できる。

L1変更
L2圧縮方式変更
L3 Vector検索変更
BM25追加
Hybrid Search
Knowledge Recall変更
RecallPack Mixer変更

つまり、

「MemoryAgentBenchを入れる」のではなく、「RenCrow Memoryの試験場を作り、その標準試験の一つとしてMemoryAgentBenchを使う」

ことを基本方針とする。
