# RenCrow Test Execution Policy v0.1

## Purpose and adoption

Small Change, Small Test. Large Risk, Large Test. Unknown Impact, Full Test.
必要な検出力を維持し、変更と無関係な待ち時間を減らす。2026-09-07のユーザー提示全文を採用し、
既存Canonical Test Planと隔離runnerを拡張する。Fullはrepoコードregressionであり、
Full-System Verification、production Agent E2E、配備後検証を代替しない。

## Canonical ownership

| 契約 | owner / 正本 |
| --- | --- |
| テスト一覧、コマンド、対象platform、登録coverage | 各repo `scripts/test-local.plan.json` |
| 子process環境、repo-local temp/cache、テスト実行 | 各repo `scripts/test-local.ps1` |
| Impact解析、固定Plan、scheduler、receipt、集計 | RenCrow_Tools `tools/quality/test_impact/` |
| Shiro実行権限、patch適用、完了判定、Mio報告 | RenCrow_CORE |
| repo横断の方針と受入条件 | 本書 |

別のテスト一覧を作らない。既存のtracked/untracked test file登録検査と未使用pattern検査を残す。
runtime Check Plan pruningとは別schemaだが、保証、consumer、failure action、固定hash、
安全gateの暗黙除外禁止を継承する。Impactの非選択理由は変更との非関連であり、
runtime pruningのduplicateとは呼ばない。

## Tiers and execution

- Fast: format、生成物整合、plan検証、軽量build/vet/unit/contract。外部service、network、GPU、browser不要。
- Related: changed packageとreverse dependency、adapter、feature、静的pathに対応する検査。
- Heavy: browser、LLM、音声、外部API、GPU、service、migration、backup、実機、latency。
- Full: current platformで実行可能な全Canonical Step。Fast/Related/Heavyを包含するmode。

Fast成功後にRelated、その後必要なHeavyを実行する。失敗後は高コストphaseを開始しない。
Fullはdependency、plan/resolver/selector、build共通基盤、serialization/persistence、security/auth、
routing、migration、広域interface、明示指定、unknown impactで必須。
mainへの統合、release、定期regressionのCIではFullを実行する。ローカルの現在branch名がmainであることだけを理由に、各patchへFullを追加しない。
広域riskをmetadataで証明できない領域はunknownからFullへ倒す。
WindowsのGoはvet/buildのみ、Go behaviorはLinuxで実行し、platform deferredをreceiptへ残す。

## Actors and authority

Coderはpatchと`changed_surface / expected_impact / recommended_test_tier /
recommended_test_steps / risk`を提案できる。`test_hint`は任意で決定権を持たない。
Shiroは既存policy付きpatch適用後にowner CLIでresolve→executeし、receiptを完了判定へ渡す。
必要なら広げられるが狭めない。Mioは実行範囲、結果、Full非実行理由、fallback理由、未確認領域を要約する。
model、provider、controllerをActorにしない。任意commandをExecution Planから実行しない。

## Isolation and scheduling

immutable/package/browser cacheだけを共有し、mutable DB、temp、user state、port、process、fixtureは共有しない。
各stepはresourceLocksを宣言し、同一lockを排他する。独立lightだけを有界並列化する。
並列数は環境設定であり、初期既定は直列。固定sleepは原則禁止し、必要なものは理由を記録する。
状態待ちはcondition/event/healthとexplicit timeoutを使う。timeout延長だけの再試行、flaky隠蔽をしない。

## CI and Shadow

PRは初期Shadow（ImpactとFullの独立した結果比較）、main/releaseはFullを維持する。
Shadow比較のための重複は明示的な計測consumerを持つ。同じsuiteを他workflowで無意味に反復しない。
go generate整合性はFastに一度登録し、生成物の差分を検出する。
Impact PASS / Full FAILはEscaped Failureとして記録し、同一revision/platform/planの比較だけを採用する。
Escaped Failureがあれば対象領域をFullへ戻す。観測母数0を安全性証明やflaky率0と呼ばない。
Phase 5への移行は同一dataset/制約でのShadow evidenceとlatency改善が揃ってから別revisionで行う。

## Metrics and acceptance

step、tier、開始終了、duration、exit、result、selected_reason、changed_files、timestamp、Plan hashをreceiptへ保存。
Fast/Related/Heavy/Full duration、p50/p95、slowest、selection ratio、fallback/unknown、failure、flaky、escapedを集計する。
flakyは同条件の再実行evidenceがある場合だけ分類し、失敗を自動retryして隠さない。

受入経路は source → owner plan → hash固定Resolver → owner runner → 実際のCLI/CI/Shiro →
結果receipt → Mio/開発者。機械検査に成功しても、未実行のWindows/macOS、CI、実Shiro、
Heavy、Shadow長期観測を成功にしない。既存ルート統合・旧重複排除・登録coverage維持を確認する。

## Implementation phases

1. 重複の根拠とbaseline timingを記録。
2. plan v2 metadataとschema/coverage検査。
3. Git diff、Go reverse graph、path、unknown Full、固定Execution Plan。
4. Shadow receipt比較とmetrics。
5. 安全性証明後のEnforced Impact CI（初期導入では未昇格）。
6. 実測に基づく並列・fixture・sleep・Heavy隔離改善。

Backlogの7日熟成に基づく最短再評価日は2026-09-14。日付の到来だけではPhase 5へ昇格せず、
実PRのShadow比較、Escaped Failure、品質維持と遅延の実測を判断根拠とする。

具体CLI/schemaは[Tools所有仕様](../RenCrow_Tools/tools/quality/test_impact/README.md)を参照する。
