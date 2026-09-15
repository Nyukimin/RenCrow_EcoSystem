# EcoSystem catalog 固有ルール

manifest、source pin、横断仕様、導入・release、ルール配布を扱う場合だけ読む。本書中のpathはcatalog root基準。全moduleの共通方針は[共通AGENTS.md](../AGENTS.md)が所有する。

- EcoSystemは構成manifest、source pin、検証済組合せ、横断設計・導入・release文書、統合検証・受入、module正本へのリンクを所有する。module内部のsource・API・build・test・config・roadmap、Persona／Memory／Recall／policy／LLM routing、runtime state・secret・生成物を所有／複製しない。
- moduleは独立Git repo・CI・tag・releaseを維持し、workspace直下に置く。catalogにsourceをコピーせず、Git submoduleを追加しない。子repoは`.gitignore`対象。再利用toolはTools、`ecosystem.yaml`専用検証だけcatalogの`scripts/`に置く。
- manifestの状態は`development`／`source-pinned`／`unpinned`／`verified`。実装済source pinは実在full SHA、未実装optional runtimeだけ`planned`を使う。pinは互換性証拠ではない。互換宣言は統合検査成功と差分説明またはrepo内証拠が必要。現行と明示計画だけを記述し、廃止仕様・架空tag／commitを残さない。
- `.env`・認証情報・runtime log／DB・binary・model・download済archiveをcommitしない。Workspaceは移行用snapshot owner。共通ルールの配布は[Codex効率運用仕様](../docs/codex-efficiency.md)に従い、snapshotを独立編集しない。
- module名とrootは`ecosystem.yaml`を参照する。Chat／ViewerはCORE、CLIはCMD。`RenCrow_GPT120B`／`RenCrow_Qwen36_27B`／`RenCrow_Gemma4`はLLM external-runtime profileで、CORE・Agent・routing ownerではない。

## 検証

- catalog変更は`make check`。宣言済子repoが揃う環境では`make check-workspace`、rules・CI・local test契約・Workspace snapshotは`make check-governance`で確認する。Windowsでは`./scripts/test-local.ps1`または文書化された`make PYTHON=python`を使い、Linux coverageも確認する。

共通指示の配置変更は[指示配置仕様](../docs/rule-layout.md)、配布は[既存配布手順](../docs/codex-efficiency.md)に従う。
