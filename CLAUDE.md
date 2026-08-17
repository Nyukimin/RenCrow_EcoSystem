# CLAUDE.md - RenCrow_EcoSystem 入口

## このファイルの役割

Claude Code または同等の AI 開発環境が RenCrow_EcoSystem（catalog root）で作業するための
短い入口です。製品仕様の正本でも、作業ルールの正本でもありません。

workspace 常時ルールの唯一の正本は同ディレクトリの `AGENTS.md` です。このファイルへ
正本の policy 本文を複製しません。両者が食い違う場合は `AGENTS.md` が勝ちます。

## 参照方法

- 読む順番は `AGENTS.md` の Read Order に従う。
- 作業対象の module root は `AGENTS.md` の Workspace Module Roots で確認し、
  catalog root を一つの source tree として扱わない。
- cross-platform 要件、validation command、branch policy、runtime routing、
  Sol/Luna 委譲、No-Human-Gate、完了整合性は `AGENTS.md` を直接参照する。
  ここへ写さない。
