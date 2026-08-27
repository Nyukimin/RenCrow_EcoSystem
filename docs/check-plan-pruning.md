# Check Plan pruning specification v1

## Purpose

RenCrowは検査開始前に、要求されたpurposeとphaseに必要なcheckだけを固定します。高コストなcheckを毎回実行して同じtimeoutを未確認として持ち越すこと、より強いEvidenceと同じ保証を重複検査すること、owner外でcheck意味論を再実装することを防ぎます。

本機能はcheck sourceを自動削除しません。現在の実行Planから安全に除外または別phaseへ延期し、理由と代替Evidenceを機械可読receiptとして残します。

全体保証の分類と、各component／cross-system surfaceが要求する分類は
[`config/full-system-coverage.json`](../config/full-system-coverage.json)を正本とします。
このpolicyは保証クラスとcoverageの宣言だけを持ち、module固有のcheck、実行コマンド、
endpoint、port、またはexecutor logicを複製しません。manifestの全componentとの対応は
`scripts/validate_ecosystem.py`で検証します。

## Ownership

| Contract | Owner |
| --- | --- |
| module固有check、保証、consumer、failure action、Evidence receipt | 各owner module |
| 横断的なPlan schema、pruning rule、CLI executable | RenCrow_Tools |
| cross-module責務、acceptance、互換性 | RenCrow EcoSystem |
| Public API／Viewerへ公開する場合の認証・policy・表示 | RenCrow_CORE |

RenCrow_CMDは将来facadeを提供しても判定を所有しません。LLMは自動pruningへ参加せず、意味的類似から同一保証を推測しません。

Owner manifestはCOREの`config/checks/core.json`、その他の各module repositoryの
`config/checks/runtime.json`を正本とします。現在の対象はCORE、PORTAL、ASSISTANT、CMD、LLM、
STT、TTS、Vision、Image、TRADE、GAMES、Tools、Workspaceです。各manifestは実在する軽量
runtime checkと、runtimeでは`wrong_phase`になるdeploy／backup／diagnostic／E2E checkを
分離します。

全体監査ではowner manifest schema v2を使います。planner v1 fieldsに加えて、各checkは
`coverage`、`executor: {kind: owner_cli, command_id}`、
`receipt_schema: rencrow.check-receipt.v1`、必要な場合だけ`surfaces`を宣言します。
RenCrow_Toolsの`rencrow-full-system-verification compose`はv2 extensionを検証してから
planner互換v1 Requestへ投影し、check自体は実行しません。各owner CLIのreceiptを5 phase分
集めた後、`aggregate-set`だけが全体の`all_clear`を決定します。単一phaseの成功、
`wrong_phase` deferred、自然言語要約を全体成功へ昇格しません。

ASSISTANTは常駐server未実装、Workspaceはsnapshot repositoryなので、通常runtime Planの
included checkが0件でも正常です。存在しないhealth routeを作りません。CMDはterminal facadeの
実route、ToolsはTools所有の実在serviceだけをruntime対象にします。manifestを配置してもcheck
実行主体はownerから移らず、横断plannerはcheck自体を実行しません。全moduleの任意checkを実行する
万能runnerは設けず、ownerの既存CLI、test、deployment readinessが固定済みPlanを消費します。

## Input contract

`schema_version`は`1`です。requestは`purpose`、`phase`、`checks`を持ちます。各checkは次を宣言します。

- `check_id`: request内で一意な安定ID
- `guarantee_id`: checkが保証する一つの機械可読な不変条件
- `owner`: checkとreceiptのowner module
- `purpose`: checkを必要とする運用目的
- `target`: 検査対象
- `phase`: `any | startup | runtime | deploy | backup | diagnostic`
- `consumer`: 結果を使う判定
- `failure_action`: `blocked | rejected | degraded | notify`
- `cost`: `low | medium | high`
- `safety_gate`: safety／security／認証／policy gateか
- `replacement_check_id`: 同一保証の明示的な代替check。省略可能
- `evidence`: `status`、`verified_at`、`ttl_seconds`、`receipt_ref`

評価時刻はCLIの必須`--now`でRFC 3339 UTCとして与えます。同じ入力と評価時刻から同じPlan revisionを再現できます。

## Deterministic decision order

1. schema、enum、ID一意性、時刻を検証する。
2. checkを`check_id`順へ正規化する。
3. malformedなsafety check、存在しないreplacement、replacementとのowner／guarantee不一致を検出した場合はPlan全体を`blocked`にする。
4. checkのphaseが要求phaseでも`any`でもなければ`deferred: wrong_phase`にする。
5. 非safety checkにconsumerまたはfailure actionがなければ`excluded: orphan | non_actionable`にする。
6. 明示replacementが同じowner／guaranteeを持ち、そのpassed Evidenceが評価時刻で有効なら`excluded: duplicate`にする。
7. それ以外は`included`にする。高コスト、失敗、timeoutだけでは除外しない。

Planが`blocked`の場合、検査runnerはどのcheckも実行してはいけません。`ready` Planだけを実行できます。

## Output and exit status

出力は`schema_version`、`status`、`purpose`、`phase`、`evaluated_at`、`plan_revision`、`included`、`excluded`、`deferred`、`errors`を持つJSONです。`plan_revision`はrevision自身を除くcanonical outputのSHA-256です。

- exit `0`: `ready`
- exit `2`: request parse／schema error
- exit `3`: fail-closedな`blocked` Plan

## Evidence validity

Evidenceは`status=passed`で、`verified_at + ttl_seconds`が評価時刻以後の場合だけ有効です。期限切れ、failed、blocked、receipt欠落はreplacement Evidenceとして使えません。

## Example: Conversation L1

通常の`runtime`現状確認では、軽量query、owner API、WAL error監視を実行します。完全SQLite integrity checkは`backup` phaseへ`deferred`し、停止中snapshotに対して実行します。live DBのtimeoutを破損や永続的な未確認状態へ変換しません。

## Acceptance

- 入力順に関係なくPlan revisionが同じ。
- wrong-phase checkが実行対象から外れ、理由付きでdeferredになる。
- orphan／non-actionableな非safety checkだけを除外する。
- 明示replacementの有効Evidenceだけがduplicate除外を許可する。
- expired Evidence、高コスト、timeoutだけではcheckを除外しない。
- malformed safety／replacement不整合はfail closedになる。
- CLIはnetwork、DB、module API、LLM、source codeを変更しない。
