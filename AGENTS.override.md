# EcoSystem catalog の作業入口

本書はcatalog自身の固有入口。global指示から[統一ルール](AGENTS.md)を受け取っている場合は再読しない。未取得の場合だけ統一ルールを先に読む。共通本文・モデル役割・権限を再定義しない。

RenCrow全体の構造、moduleの責務、依存方向を扱う質問や作業（初めての作業、横断的な質問、担当moduleが不明なとき）では、最初に`docs/architecture.md`と`docs/modules.md`をtoolで読む。他の全体文書は[docs/README.md](docs/README.md)のRead orderから必要なものだけ読む。`ls -R`や各moduleのREADME巡回で代用せず、module構成を記憶や推測で答えない。

manifest、source pin、横断仕様、導入・release、ルール配布を扱う場合は[catalog固有ルール](rules/catalog.md)を着手前に読む。子moduleの実装を扱う場合は、当該moduleのAGENTS.mdから必要な詳細だけ読む。catalog全体を一つの製品source treeとして扱わない。
