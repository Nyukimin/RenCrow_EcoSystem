# RenCrow EcoSystem

RenCrow EcoSystem は、独立した RenCrow 各リポジトリを一つの製品として
理解・導入・検証・リリースするための公式入口です。

このリポジトリ自体は実行時サーバではなく、各 module のソースコードも
内包しません。全体アーキテクチャ、module の役割、導入順序、動作確認済みの
組み合わせを管理します。

## 基本関係

```text
RenCrow_EcoSystem  -- release/catalog reference --> module releases

User / RenCrow_PORTAL / rencrowctl
                 |
                 v
           RenCrow_CORE
          /   |   \
         v    v    v
       LLM   STT  TTS / Vision
              |
              +---- Games / Tools / Workspace
```

- 各 module は独立した Git リポジトリです。
- 各 module がソース、詳細仕様、テスト、CI、タグ、Release を所有します。
- EcoSystem は統合確認済みの組み合わせを `ecosystem.yaml` に記録します。
- module から EcoSystem の実装へ依存しません。
- 実行時連携は HTTP、WebSocket、CLI、設定ファイルなどの公開契約を使います。
- Git submodule は使用しません。

## 現在の状態

初期構成は `development` です。各 component の release version はまだ
`unpinned` であり、互換性確認済みリリースを意味しません。最初の統合試験後に、
実在する tag と検証結果を記録して ecosystem release を作成します。

`ecosystem.yaml` schema v2では、moduleの配布artifactを`runtime.primary`、
利用環境側で別途動かす演算runtimeなどを`runtime.companions`として分離できます。
現在はRenCrow_LLM、RenCrow_STT、RenCrow_TTSへ適用し、Go binaryと各演算targetを
別の配布層として宣言しています。いずれもGo Gatewayはdevelopment状態であり、
現行Python APIを置き換えたという意味ではありません。

## Repository layout

```text
.
├── AGENTS.md
├── README.md
├── ecosystem.yaml
├── Makefile
├── docs/
│   ├── README.md
│   ├── architecture.md
│   ├── compatibility.md
│   ├── installation.md
│   ├── modules.md
│   └── runtime-layers.md
├── scripts/
│   └── validate_ecosystem.py
└── tests/
    └── test_validate_ecosystem.py
```

`ecosystem.yaml` は外部 YAML dependency を不要にするため、YAML 1.2 で有効な
JSON-compatible syntax を採用しています。

## Validation

```bash
make check
```

標準 workspace (`/home/nyukimi/RenCrow`) に全 sibling repo がある場合:

```bash
make check-workspace
```

## Documentation

読む順番と正本境界は [docs/README.md](docs/README.md) を参照してください。

## License

[MIT License](LICENSE)
