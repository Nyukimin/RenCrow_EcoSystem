# RenCrow EcoSystem documentation

この directory は ecosystem 全体にだけ適用される現行文書を置きます。
module 固有の API、設定、実装、テスト仕様は各 module repo が正本です。

## Read order

1. [Architecture](architecture.md) — 全体構造と依存方向
2. [Modules](modules.md) — 各 repository の責務
3. [Installation](installation.md) — 現在利用できる導入方法
4. [Compatibility](compatibility.md) — version 固定と統合 release 手順

## Documentation boundary

| EcoSystem に置く | 各 module に置く |
| --- | --- |
| 全体の目的と構成 | module の詳細設計 |
| repository 間の責務境界 | API・設定リファレンス |
| 導入順序 | build・test 手順 |
| 動作確認済み version | module 固有 roadmap |
| 統合 acceptance | module 内部の障害調査 |

記述が競合する場合、module 内部の振る舞いは module repo の実装・テスト・
現行仕様を優先し、組み合わせと統合 release の主張は `ecosystem.yaml` と
この repo の検証記録を優先します。
