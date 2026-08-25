# Installation

## Current development setup

初期段階ではrelease artifact用の統合 installer を公開していません。開発者は
EcoSystem repositoryを`RenCrow`というworkspace rootとして取得し、Toolsと必要なmoduleを
root直下の独立したchild repositoryとしてcloneします。module repoは親のGit管理対象や
Git submoduleにしません。root checkoutはこのcatalog自身が管理し、別の薄い親repositoryを
用意しません。
`source-pinned` manifestのversionはcheckoutするcommit SHAであり、配布artifact名では
ありません。`--check-workspace`検証では各local HEADがこのSHAと一致することを確認します。

```bash
git clone https://github.com/Nyukimin/RenCrow_EcoSystem.git RenCrow
cd RenCrow
git clone https://github.com/Nyukimin/RenCrow_Tools.git
```

RenCrow_Toolsのsource checkout用bootstrapは、この`ecosystem.yaml`だけを読み、
未存在repositoryをcloneしてsource-pinned SHAへcheckoutします。最初にread-only planを
確認し、その後applyします。

```bash
go -C ./RenCrow_Tools/tools/workspace/ecosystem_bootstrap \
  run ./cmd/rencrow-bootstrap plan \
  --manifest ../../../../ecosystem.yaml \
  --workspace ../../../..
go -C ./RenCrow_Tools/tools/workspace/ecosystem_bootstrap \
  run ./cmd/rencrow-bootstrap apply \
  --manifest ../../../../ecosystem.yaml \
  --workspace ../../../..
```

特定moduleだけを取得する場合は`--include core`のようにIDを指定し、複数回指定できます。
`planned` entryは取得しません。既存repositoryは自動checkoutせず、originとHEADがmanifestに
一致しない場合は変更せず停止します。bootstrapはmanifestを書き換えず、互換性を主張しません。

外部向けWeb画面を使う場合は`RenCrow_PORTAL`、CORE Public APIのterminal clientを
使う場合は`RenCrow_CMD`を追加します。既定バイナリはそれぞれ`rencrow-portal`と
`rencrowctl`です。`RenCrow_ASSISTANT`は手動通知CLIまで実装されたdevelopment componentとして
source-pinned clone対象ですが、常駐serviceとしては起動しません。

各 module の build と設定は、その repository の README / AGENTS / docs を
参照してください。EcoSystem 側から未検証の command を複製しません。

Go binaryを標準配布単位とし、Python／Node.jsを標準installerへ持ち込まない境界と
統合待ち項目は、[Go distribution](go-distribution.md)に記載します。映画カタログCrawler、
Vision、ImageのGo化は完了済みです。各primary artifactは`development`としてmanifestへ記録し、
checksum付きreleaseと統合installerが確定するまで`available`とは扱いません。

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

RenCrow_LLM、RenCrow_STT、RenCrow_TTS、RenCrow_Vision、RenCrow_Imageの場合、installerが
取得するprimary artifactはそれぞれ`rencrow-llm`、`rencrow-stt`、`rencrow-tts`、
`rencrow-vision`、`rencrow-image`です。各target／backendのengine、Model、重み、KV、
decoder／codec、音声資産、FFmpeg／FFprobe、計算資源は自動同梱せず、
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
