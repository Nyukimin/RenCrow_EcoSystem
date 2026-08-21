# RenCrow Agent / Subagent 定義・採用仕様

**Status:** 設計決定案
**Date:** 2026-08-17
**Scope:** RenCrow CORE における Agent / Subagent の定義、Coder の位置づけ、Subagent Capability の導入方針

---

## 1. 目的

本仕様は、RenCrow における **Agent** と **Subagent** の境界を明確にし、Agent 数の増加、Coder の高度化、外部 Agent Runtime の利用、多段委譲を長期運用しても構造が崩れないようにすることを目的とする。

DeepSeek Harness の Subagent 設計を参考にするが、RenCrow の既存原則を置き換えない。

特に次を固定する。

* Mio、Shiro、Midori、Kuro は並列な Agent である。
* Mio が通常入力の Router を担当することは、他 Agent の親であることを意味しない。
* Aka、Ao、Kin、Gin の Coder も Agent とする。
* Coder を固定 Subagent にはしない。
* Subagent は、Agent が特定作業のために動的生成する Task-scoped な子実行主体とする。
* RenCrow の恒久的な Agent 構造はフラットに保つ。
* 親子関係は恒久的な組織構造ではなく、個別作業の Work Graph 上にだけ存在する。

---

## 2. 基本原則

RenCrow では、次の二つを分離する。

### 2.1 Agent Identity Plane

恒久的な主体を管理する。

```text
Mio
Shiro
Midori
Kuro
Aka
Ao
Kin
Gin
...
```

これらは Agent Registry に登録された並列な Agent である。

Agent 間に恒久的な親子関係を設定しない。

### 2.2 Work Graph

個別の仕事を実行するときだけ、一時的な親子関係を作る。

```text
Shiro
  -> Ao
       -> Subagent A
       -> Subagent B

Kuro
  -> Aka
       -> Subagent C
```

この親子関係は仕事の実行構造であり、Agent の上下関係ではない。

**Routing Graph と Agent Hierarchy を同一視しない。**

---

# 3. Agent の定義

## 3.1 定義

**Agent とは、RenCrow 内で安定した Identity と Agent Contract を持ち、特定の親 Agent に所属せず、複数の相手から独立して仕事または会話を受けられる主体である。**

Agent は長期に存在する。

実行時に利用する LLM、Model、Provider、Execution Role、Agent Runtime は Agent の実装機構であり、Agent Identity そのものではない。

## 3.2 Agent の必須条件

Agent は少なくとも次を持つ。

* 安定した `agent_id`
* `display_name`
* Agent Registry への登録
* versioned `Agent Contract`
* Persona
* 責務
* 得意分野
* 入力契約
* 出力契約
* Capability
* Restriction
* 委譲可能な仕事
* 期待成果物
* 他 Agent から参照可能な Agent Knowledge
* Conversation / Recall への正規アクセス経路
* 独立した実行先選択
* Agent としての監査可能な発話・判断履歴

## 3.3 Agent が持ってよいもの

Agent は必要に応じて次を持つことができる。

* Character Persona
* 長期的な関係性
* Agent 固有の経験
* Agent 固有の成長状態
* 会話参加能力
* User-facing addressability
* 他 Agent からの委譲受付
* Subagent 生成 Capability

ただし、User-facing であることは Agent の必須条件ではない。

## 3.4 User-addressable と Agent Identity は分離する

Agent であっても、通常 UI から直接選択可能である必要はない。

例:

```yaml
agent_id: aka
user_addressable: false
delegation_addressable: true
can_spawn_subagents: true
```

Aka は正式な Agent だが、通常は他 Agent からの委譲だけを受ける運用が可能である。

将来直接会話を許可する場合も、Agent Identity を変更せず `user_addressable` の policy だけを変更する。

---

# 4. 現行 Agent の位置づけ

現時点では次を Agent とする。

| Agent  | 主な役割                                    | Agent扱い |
| ------ | --------------------------------------- | ------- |
| Mio    | Chat、通常入力の Route Owner、最終 user response | Agent   |
| Shiro  | ChatWorker、Worker、OPS 実行                | Agent   |
| Midori | Wild、創作、視覚・横方向探索                        | Agent   |
| Kuro   | Heavy、深い分析、設計、技術作業                      | Agent   |
| Aka    | Coder1、設計・アーキテクチャ                       | Agent   |
| Ao     | Coder2、実装・テスト                           | Agent   |
| Kin    | Coder3 または補助 Coder、比較・仕上げ               | Agent   |
| Gin    | Coder4 または高度 Coder、安全性・エッジケース           | Agent   |

Coder の番号や Provider 割当は deployment 設定であり、Agent Identity の定義には含めない。

---

# 5. Mio と Router の関係

Mio は通常入力の Route Owner である。

しかし、これは次を意味しない。

```text
Mio
  -> Shiro
  -> Midori
  -> Kuro
  -> Coder
```

正しい構造は次である。

```text
Agent Registry

Mio
Shiro
Midori
Kuro
Aka
Ao
Kin
Gin
```

Mio は通常入力を受け取ったとき、適切な Agent や Execution Role へ処理を振り分ける。

Mio の Router 機能は **交通整理の責務** であり、Agent の所有関係ではない。

Shiro、Midori、Kuro、Coder は Mio の Subagent ではない。

---

# 6. Coder の正式な扱い

## 6.1 決定

**Aka、Ao、Kin、Gin は固定 Subagent にせず、正式な Agent として維持する。**

## 6.2 固定 Subagent にしない理由

固定 Subagent にすると「誰の子か」を恒久的に決める必要がある。

例えば Ao を Shiro の Subagent に固定すると、

```text
Kuro -> Ao
```

という自然な委譲まで、

```text
Kuro -> Shiro -> Ao
```

に変形される。

Mio の子に固定しても同じ問題が起こる。

呼び出し元ごとに Ao を生成すると、

```text
Shiro -> Ao #1
Kuro  -> Ao #2
Mio   -> Ao #3
```

となり、Ao の Persona、経験、Identity が複数に分裂する。

複数の親から同じ Ao を共有するなら、それは実質的に独立 Agent である。

したがって、Coder は Agent とした方が構造が自然である。

## 6.3 Coder と Subagent の関係

Coder 自身は Agent だが、必要に応じて Subagent を生成できる。

例:

```text
Ao
  -> implementation subagent
  -> test subagent
  -> review subagent

Aka
  -> architecture research subagent
  -> alternative design subagent

Gin
  -> security review subagent
  -> edge-case discovery subagent
```

これにより、Coder の Identity を維持しつつ、内部作業を並列化できる。

---

# 7. Subagent の定義

## 7.1 定義

**Subagent とは、ある Agent が特定の Objective を遂行するために動的生成する、親を一つだけ持つ Task-scoped な子実行主体である。**

Subagent は恒久的な RenCrow Agent Registry のメンバーではない。

## 7.2 Subagent の基本特性

Subagent は次の性質を持つ。

* 動的生成される
* `subagent_instance_id` を持つ
* direct parent Agent を一つだけ持つ
* Objective または Task に所属する
* parent の委譲範囲を越えない
* parent と独立した恒久 Persona を原則持たない
* User-facing Agent として直接発言しない
* 出力は work product として parent または依頼 Agent へ返す
* 長期 Memory を直接更新しない
* Agent Registry の恒久 Agent と同格には扱わない
* 終了後は原則破棄する
* 明示条件を満たす場合のみ Continuable として残せる

---

# 8. Agent と Subagent の比較

| 項目                | Agent              | Subagent                   |
| ----------------- | ------------------ | -------------------------- |
| Identity          | 安定 `agent_id`      | 実行時 `subagent_instance_id` |
| Registry          | Agent Registry     | Subagent Runtime Catalog   |
| 寿命                | 長期                 | Task-scoped                |
| 親                 | なし                 | direct parent 1つ           |
| Persona           | 正式 Persona を持てる    | Task role が基本              |
| User-facing       | policy により可能       | 原則不可                       |
| 長期 Memory         | 正規経路で利用可能          | 直接 write 禁止                |
| 複数 Agent から仕事を受ける | 可能                 | 不可                         |
| Capability        | Agent Contract で定義 | parent の委譲範囲内              |
| Subagent生成        | policy により可能       | depth policy 内で可能          |
| 経験・成長             | Agent の状態として保持可能   | 原則保持しない                    |
| 最終責任              | Agent Contract に従う | parent 側が負う                |
| 公開発話              | Agent として記録        | work product として記録         |

---

# 9. Subagent の帰属と発話

Subagent が生成した結果を、そのまま Agent の発話として記録しない。

```text
Subagent output
  -> Parent Agent validation
  -> Parent Agent adoption
  -> Agent response
```

Subagent の生成物は provenance を維持する。

例:

```json
{
  "generated_by": "subagent_instance_id",
  "parent_agent_id": "ao",
  "adopted_by": "ao",
  "published_as_agent_message": true
}
```

Agent が採用していない Subagent 出力は、Agent の発言、判断、経験として扱わない。

---

# 10. Subagent Capability Seam

DeepSeek Harness から最も積極的に取り込む仕様は、**Subagent を Agent Loop 固有処理にせず独立 Capability とする考え方**である。

RenCrow では次の論理 Capability を用意する。

```text
SubagentRuntime
  -> Provider Registry
       -> internal
       -> fork
       -> Codex
       -> Claude Code
       -> external Agent Runtime
       -> future provider
```

Agent 側は Provider 固有処理を直接実装しない。

---

# 11. Provider 抽象化

各 Subagent Provider は共通 Contract を実装する。

想定 Provider:

* `internal`
* `fork`
* `codex`
* `claude_code`
* `external_runtime`
* 将来の追加 Provider

Agent は次のように要求する。

```text
start_subagent(request)
```

Codex や Claude Code の具体的な起動方法を Agent 実装へ埋め込まない。

これにより、将来 Provider が増えても Agent 側のコードを変更しない。

---

# 12. Capability Advertisement と Fail Loud

Provider は起動前に対応 Capability を宣言する。

例:

```yaml
provider: codex
capabilities:
  structured_output: true
  tool_filter: true
  continuable: true
  depth_limit: true
  task_prompt: true
```

要求された Capability を Provider が持たない場合は、起動後に無視するのではなく、**起動前に明示的に失敗させる。**

暗黙 fallback は行わない。

RenCrow の既存 policy である `disabled / unavailable / blocked` の明示とも整合させる。

---

# 13. Subagent Start Contract

最低限、次を要求する。

```yaml
subagent_request_id:
trace_id:
parent_agent_id:
parent_session_id:
objective:
work_type:
provider:
mode: one_shot
input:
expected_output:
output_schema:
tool_filter:
data_scope:
max_depth:
timeout:
retention_policy:
contract_revision:
```

`parent_agent_id` は必須とする。

Subagent は自分で親を選べない。

---

# 14. Capability の継承規則

Subagent は parent より強い権限を持たない。

有効 Capability は次の積集合とする。

```text
Parent Delegation Envelope
∩ Provider Capability
∩ Execution Policy
∩ Tool Policy
∩ Data Scope
∩ Sandbox Policy
```

いずれかが拒否すれば、その Capability は利用不可とする。

LLM や Provider の自己申告によって権限を拡張しない。

---

# 15. One-shot と Continuable

## 15.1 デフォルト

Subagent は原則 `one_shot` とする。

```text
start
 -> execute
 -> report
 -> settle
 -> dispose
```

これは短い実装、調査、比較、レビュー、テストなどに使用する。

## 15.2 Continuable

長時間作業や継続的な探索では `continuable` を選択できる。

```text
Persistent Child Session
  -> Activation
  -> Work
  -> Quiescent
  -> Cold Resume
```

ただし、Continuable を全 Subagent の標準にはしない。

## 15.3 Continuable の再開条件

Cold Resume 時には、過去 Context をそのまま信用しない。

最低限、次を再検証する。

* Parent Agent identity
* Agent Contract revision
* Workspace revision
* Repository revision
* Capability revision
* Tool revision
* Data Scope
* Sandbox policy
* Objective validity

重大な差分がある場合は resume を拒否するか、新しい Subagent を生成する。

---

# 16. Continuable の保持と清掃

Continuable Subagent を無期限保存しない。

最低限、次を持つ。

```yaml
created_at:
last_active_at:
ttl:
state:
parent_agent_id:
objective_id:
workspace_revision:
contract_revision:
```

終了済み、長期未使用、Objective 消滅、親 Contract 不整合の場合は cleanup 対象とする。

---

# 17. Subagent Control API

RenCrow 内部 Contract として、少なくとも次を用意する。

```text
start()
followup()
interrupt()
list_children()
list_descendants()
report()
dispose()
```

### start

新しい Subagent を生成する。

### followup

Continuable Subagent に追加作業を送る。

### interrupt

現在実行中の Turn を停止する。

### list_children

direct child を列挙する。

### list_descendants

多段委譲時の Work Graph 全体を確認する。

### report

Subagent から direct parent へ作業結果を返す。

### dispose

明示的に Subagent を終了し、runtime 資源を解放する。

---

# 18. Parent Authority

Subagent の操作権限は direct parent を基準とする。

少なくとも次を区別する。

```text
identity attribution
```

と

```text
authority
```

`sender_agent_id` が記録されているだけでは操作権限を与えない。

followup、interrupt、dispose などは、CORE が direct-parent 関係と policy を検証して許可する。

---

# 19. Delegation Depth

Subagent がさらに Subagent を生成できる場合は、最大深度を設ける。

例:

```yaml
max_depth: 2
```

```text
Agent
  -> Subagent depth 1
       -> Subagent depth 2
```

depth 3 の生成は拒否する。

最大値は Provider ではなく CORE policy が上限を決める。

---

# 20. Memory Policy

Subagent は長期 Memory の直接 writer にしない。

Subagent が発見した内容は、

```text
Subagent
  -> report
  -> Parent Agent
  -> Memory Candidate
  -> existing validator
  -> Memory
```

の順に扱う。

これにより、一時的な調査 Agent が UserMemory や Character Memory を汚染することを防ぐ。

---

# 21. Observability

Subagent の全実行には既存の RenCrow 相関 ID を利用する。

最低限:

* `trace_id`
* `request_id`
* `job_id` または task execution id
* `parent_agent_id`
* `subagent_instance_id`
* `provider`
* `objective_id`
* `parent_session_id`
* `child_session_id`
* `contract_revision`

Agent 間委譲と Subagent 委譲をログ上で区別する。

---

# 22. Model-visible 情報の記録方針

DeepSeek Harness の `Model-visible means logged` は、そのままコピーしない。

RenCrow では、長期的なログ肥大、Memory 削除との衝突、個人情報の複製を避けるため、**Model-visible means receipted** を採用する。

モデルへ渡した全文を永久複製するのではなく、参照した正本 ID と revision を記録する。

例:

```yaml
model_request_receipt:
  trace_id:
  request_id:
  agent_id:
  execution_role:
  runtime_revision:
  model_revision:
  character_prompt_revision:
  agent_contract_revision:
  runtime_context_revision:
  message_ids:
  recall_item_ids:
  knowledge_item_ids:
  toolset_revision:
  tool_schema_hash:
  prompt_hash:
  response_message_id:
  created_at:
```

必要なデバッグ期間だけ materialized prompt を短期保持することは許可する。

永久保存の正本にはしない。

---

# 23. Prompt Assembly

DeepSeek Harness の自由な Prompt Plugin Registry はそのまま導入しない。

RenCrow の既存 Prompt 階層を維持し、共通化が必要な場合は固定 Slot 型 `PromptAssembler` を使用する。

```text
00 Character SystemPrompt
10 Agent Contract
20 Interaction Contract
30 Tool / Capability Boundary
40 RecallPack
50 Variable RuntimeContext
60 User Message
```

各 Slot に Owner を設定する。

任意 Plugin が自由な順序で SystemPrompt へ割り込む構造にはしない。

---

# 24. 取り込む仕様

DeepSeek Harness から RenCrow へ取り込む価値が高いものを次に限定する。

## 必須候補

1. **Subagent Capability Seam**
2. **複数 Subagent Provider の共通 Registry**
3. **Provider Capability Advertisement**
4. **Unsupported Capability の Fail Loud**
5. **direct parent / lineage の明示**
6. **One-shot と Continuable の分離**
7. **followup / interrupt / list / report の共通 Contract**
8. **delegation depth limit**
9. **Subagent Tool / Data Scope restriction**
10. **Cold Resume 時の再検証**
11. **Subagent provenance と work product の明示**
12. **Subagent の長期 Memory direct-write 禁止**
13. **Model Request Receipt**

---

# 25. 取り込まない仕様

次は RenCrow には採用しない。

## Everything is a Plugin

RenCrow CORE の Owner、正本、policy 境界を弱めるため採用しない。

## No Privileged Core

RenCrow では CORE が Agent identity、Agent Contract、routing、Memory、policy、Execution Role、話者帰属の正本を所有する。

## Coder を固定 Subagent 化

Agent identity と委譲関係を不自然にするため採用しない。

## 全 Subagent の Continuable 化

古い Session の大量残存と stale context を招くため採用しない。

## Session Log を Memory の唯一の正本にする

Conversation、UserMemory、Knowledge Memory、Common Raw Data の既存 Owner 境界を維持する。

## 自由な Prompt Plugin Registry

Prompt の責務と順序を追跡しづらくするため採用しない。

---

# 26. Agent Contract への追加候補

既存 Agent Contract に次を追加することを検討する。

```yaml
user_addressable:
delegation_addressable:
can_spawn_subagents:
allowed_subagent_providers:
max_subagent_depth:
default_subagent_mode:
subagent_data_scope:
subagent_tool_policy:
continuable_allowed:
```

これらは Persona ではなく Agent Contract / runtime policy に属する。

---

# 27. Subagent Descriptor

起動後は immutable な Descriptor を保持する。

```yaml
subagent_instance_id:
provider:
parent_agent_id:
parent_session_id:
objective_id:
trace_id:
request_id:
mode:
created_at:
contract_revision:
workspace_revision:
tool_policy_revision:
data_scope:
max_depth:
```

Continuation 時はこの Descriptor と現在の環境を比較する。

---

# 28. 受け入れ条件

最低限、次のテストを通す。

### Agent identity

* Mio が Router でも Shiro / Midori / Kuro の parent として記録されない。
* Aka / Ao / Kin / Gin が Agent Registry の恒久 Agent として維持される。
* User-addressable false の Coder も他 Agent から委譲可能である。

### Subagent

* Parent Agent なしでは起動できない。
* Provider が非対応 Capability を要求された場合に起動前失敗する。
* Parent より広い Tool / Data Scope を取得できない。
* Subagent output が自動的に Agent 発話として公開されない。
* Subagent が UserMemory / Character Memory を直接変更できない。
* One-shot 終了後に runtime 資源が解放される。

### Continuable

* 同じ Child Session へ followup できる。
* Cold Resume で Contract / Workspace revision を再確認する。
* stale な環境では resume を拒否できる。
* TTL 後に cleanup される。
* interrupt 後も状態が不明な成功へ丸められない。

### Multi-level delegation

* depth limit を超えた生成が拒否される。
* `list_descendants()` で Work Graph を追跡できる。
* 子から親への report の provenance が維持される。

---

# 29. 最終決定

本仕様では次を決定とする。

1. RenCrow の恒久 Agent 構造はフラットとする。
2. Mio、Shiro、Midori、Kuro は並列 Agent とする。
3. Mio の Router 責務を Agent 親子関係として扱わない。
4. Aka、Ao、Kin、Gin は正式な Agent とする。
5. Coder を固定 Subagent にしない。
6. Agent は必要に応じて Subagent を動的生成できる。
7. Subagent は direct parent を一つだけ持つ Task-scoped 実行主体とする。
8. Agent Identity Plane と Work Graph を分離する。
9. Subagent Capability は Agent Loop や特定 Provider から独立させる。
10. One-shot を標準とし、Continuable は明示的に選択する。
11. Subagent は長期 Memory を直接変更しない。
12. DeepSeek Harness の Plugin Architecture 全体は採用せず、Subagent に関する有効な設計だけを選択導入する。
13. 完全 Prompt 保存ではなく Model Request Receipt を基本とする。
14. Prompt 構造は自由 Registry ではなく固定 Slot を維持する。

---

# 30. 設計要約

```text
                    Agent Registry

 Mio   Shiro   Midori   Kuro   Aka   Ao   Kin   Gin   ...
  |      |       |       |      |    |    |     |
  +------+------+-------+------+----+----+-----+
                         |
                  Flat Agent Plane
                         |
                     Delegation
                         |
                    Work Graph
                         |
          +--------------+--------------+
          |              |              |
      Subagent        Subagent       Subagent
      one-shot       continuable      one-shot
          |              |              |
       Provider       Provider       Provider
       internal        Codex       Claude Code
```

RenCrow では、**Agent は恒久的な主体、Subagent は仕事のための一時的な子**とする。

Agent の世界はフラットに保ち、仕事だけを必要に応じて木構造へ展開する。

---

## 参考

本仕様は次の現行設計・実装を基礎としている。

* RenCrow CORE `docs/03_キャラクター・エージェント仕様.md`
* RenCrow CORE `internal/domain/agent/coder.go`
* RenCrow CORE の Agent Contract / Agent Knowledge / Interaction Policy
* DeepSeek Harness `docs/architecture.md`
* DeepSeek Harness `docs/subsystems/subagent.md`

DeepSeek Harness の仕様は参照実装として利用し、RenCrow の Agent Identity、CORE ownership、Memory ownership、Go-first runtime 方針を上書きしない。
::: 
