# RenCrow EcoSystem documentation

この directory は ecosystem 全体にだけ適用される現行文書を置きます。
module 固有の API、設定、実装、テスト仕様は各 module repo が正本です。

## Read order

1. [Architecture](architecture.md) — 全体構造と依存方向
2. [Interaction surfaces](interaction-surfaces.md) — 現行PORTAL／CMDと段階実装中ASSISTANTの境界
3. [ASSISTANT boundary](assistant-boundary.md) — 段階実装中の生活Routine、CORE、端末の境界
4. [PORTAL–CORE contract](portal-core-contract.md) — 外部UIと中核runtimeの接続・公開境界
5. [Modules](modules.md) — 各 repository の責務
6. [Runtime layers](runtime-layers.md) — primary binaryと外部runtimeの配布境界
7. [Go distribution](go-distribution.md) — CORE正本に従うGo artifact、外部compute、optional sidecarの統合状態
8. [Binary placement](binary-placement.md) — control／compute／interaction hostへの配置規則
9. [Binary redeployment](binary-redeployment.md) — 配置済みbinaryとpinの整合、再build・再配置
10. [Installation](installation.md) — 現在利用できる導入方法
11. [Compatibility](compatibility.md) — version 固定と統合 release 手順
12. [Check Plan pruning](check-plan-pruning.md) — 検査前の不要check除外とEvidence契約
13. [Full-system verification](full-system-verification.md) — 全owner check、5 phase Plan、owner Evidence自己収集、receipt集約契約
14. [Backup and recovery](backup-and-recovery.md) — 通常backup、Migration Artifact、分散owner transport、復旧受入条件

## Documentation boundary

| EcoSystem に置く | 各 module に置く |
| --- | --- |
| 全体の目的と構成 | module の詳細設計 |
| repository 間の責務境界 | API・設定リファレンス |
| module 間の通信方向とsecurity境界 | endpoint payloadと内部実装 |
| 導入順序 | build・test 手順 |
| host roleごとのbinary配置 | Backend固有の起動引数、Model path |
| 配置済みbinaryとpinの整合 | module内部のbuild設定 |
| 動作確認済み version | module 固有 roadmap |
| 統合 acceptance | module 内部の障害調査 |

記述が競合する場合、module 内部の振る舞いは module repo の実装・テスト・
現行仕様を優先し、組み合わせと統合 release の主張は `ecosystem.yaml` と
この repo の検証記録を優先します。
