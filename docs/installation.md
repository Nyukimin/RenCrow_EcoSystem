# Installation

## Current development setup

初期段階では統合 installer を公開していません。開発者は ecosystem repo と、
必要な module repo だけを sibling directory として clone します。

```bash
mkdir -p RenCrow
cd RenCrow
git clone https://github.com/Nyukimin/RenCrow_EcoSystem.git
git clone https://github.com/Nyukimin/RenCrow_CORE.git
```

音声、視覚、CLI、ゲームなどが必要な場合だけ対応 repository を追加します。

```bash
git clone https://github.com/Nyukimin/RenCrow_PORTAL.git
git clone https://github.com/Nyukimin/RenCrow_CMD.git
git clone https://github.com/Nyukimin/RenCrow_LLM.git
git clone https://github.com/Nyukimin/RenCrow_STT.git
git clone https://github.com/Nyukimin/RenCrow_TTS.git
git clone https://github.com/Nyukimin/RenCrow_Vision.git
```

外部向けWeb画面を使う場合は`RenCrow_PORTAL`、管理CLIを使う場合は`RenCrow_CMD`を追加します。既定バイナリはそれぞれ`rencrow-portal`と`rencrowctl`です。

各 module の build と設定は、その repository の README / AGENTS / docs を
参照してください。EcoSystem 側から未検証の command を複製しません。

## Planned release installation

統合 release が成立した後、installer は次を行うものとして別仕様化します。

1. OS / architecture を判定する。
2. `ecosystem.yaml` で固定した release artifact を取得する。
3. checksum と署名を検証する。
4. required component を導入する。
5. optional component は利用者が明示選択する。
6. secret を repository や command line に残さず設定する。
7. CORE health と選択した capability の end-to-end check を行う。

artifact、checksum、rollback、Windows 対応が未確定の間は、形だけの
`install.sh` / `install.ps1` を追加しません。
