# Installation

## Current development setup

初期段階では統合 installer を公開していません。開発者は ecosystem repo と、
必要な module repo だけを sibling directory として clone します。
`source-pinned` manifestのversionはcheckoutするcommit SHAであり、配布artifact名では
ありません。`--check-workspace`検証では各local HEADがこのSHAと一致することを確認します。

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
git clone https://github.com/Nyukimin/RenCrow_Image.git
git clone https://github.com/Nyukimin/RenCrow_GAMES.git
git clone https://github.com/Nyukimin/RenCrow_Tools.git
git clone https://github.com/Nyukimin/RenCrow_Workspace.git
```

外部向けWeb画面を使う場合は`RenCrow_PORTAL`、CORE Public APIのterminal clientを
使う場合は`RenCrow_CMD`を追加します。既定バイナリはそれぞれ`rencrow-portal`と
`rencrowctl`です。`RenCrow_ASSISTANT`はplannedであり、現行のclone対象には含めません。

各 module の build と設定は、その repository の README / AGENTS / docs を
参照してください。EcoSystem 側から未検証の command を複製しません。

Go binaryを標準配布単位とし、Python／Node.jsを標準installerへ持ち込まない境界と
実装待ち項目は、[Go distribution](go-distribution.md)に記載します。映画カタログのCrawler
sidecar化は完了済みです。Vision／ImageのGo Gateway化とrelease artifact確定までは、現行の
Python service構成をdevelopment用として扱い、`ecosystem.yaml`のrelease artifact宣言を先行変更しません。

## Planned release installation

統合 release が成立した後、installer は次を行うものとして別仕様化します。

1. OS / architecture を判定する。
2. `ecosystem.yaml` で固定した release artifact を取得する。
3. checksum と署名を検証する。
4. required component を導入する。
5. optional component は利用者が明示選択する。
6. 選択componentの`runtime.companions`を確認し、外部演算runtimeが必要ならmodule側手順へ案内する。
7. [Binary placement](binary-placement.md)に従いcontrol／compute／interaction hostへ配置する。
8. secret を repository や command line に残さず設定する。
9. CORE health と選択した capability の end-to-end check を行う。

RenCrow_LLM、RenCrow_STT、RenCrow_TTSの場合、installerが取得するprimary artifactは
それぞれ`rencrow-llm`、`rencrow-stt`、`rencrow-tts`です。LLM／STT／TTS targetの
engine、Model、重み、KV、decoder／codec、音声資産、計算資源は自動同梱せず、
各moduleの利用者Configで接続します。

RenCrow LLM Runtimeの現行binary `rencrow-llm-node`は実装・初回配布済みですが、
production Gateway cutoverと
EcoSystem互換試験が成立するまでは統合installer対象にしません。採用時はModel／GPUを持つ
compute hostへ配置し、RenCrow LLM Gatewayの`rencrow-llm`と同一module versionに固定します。

RenCrow_ASSISTANTを選択した場合、installerは`rencrow-assistant`と非secret設定例を
導入します。利用者、家族、端末、Calendar等のcredentialはsourceやcommand lineへ
埋め込まず、初回設定時に利用者環境のsecret storeへ登録します。

artifact、checksum、rollback、Windows 対応が未確定の間は、形だけの
`install.sh` / `install.ps1` を追加しません。
