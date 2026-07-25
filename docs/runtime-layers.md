# Runtime layers

EcoSystem manifestは、module repositoryとversionだけでなく、利用者へ配布するprimary runtimeと、利用環境側で別途用意するcompanion runtimeを区別します。

## Contract

```text
module release
  `- runtime.primary
       implementation: Goなど
       artifact: 配布artifact名
       status: planned / development / available / compatibility

user environment
  `- runtime.companions[]
       external compute、system service、compatibility runtimeなど
```

- `primary`はEcoSystem releaseが取得・checksum検証する配布単位です。
- `companions`はprimaryと連携しますが、別process、別runtime、別計算資源として扱います。
- `external-compute`はmodule releaseへbundleしません。
- companionを独立したRenCrow moduleとして登録するかは、独立repository、release、公開contractを持つ場合だけ別途判断します。
- module内部の配置、API、Config詳細は各module repositoryを正本とします。

## RenCrow_LLM

```text
primary
  rencrow-llm             Go central Gateway / control host
       |
       +-> planned module artifact
       |     rencrow-llm-node  Go Host Node / compute host
       |
       +-> companion: llm-target     bundled=false / required=true
       |     Backend + Model + weights + KV + compute
       |
       `-> external API / trusted Agent Runtime

companion: python-compat  bundled=false / required=false
  Go移行中の現行Python role proxy / management runtime
```

BackendはLLM targetに付随し、EcoSystemの独立componentにはしません。
`rencrow-llm-node`もRenCrow_LLMとBackend契約、status schema、release cadenceを共有するため、
別moduleにしません。Nodeがbuild／release可能になるまではplannedであり、存在するartifactとして
manifestへ登録しません。EcoSystemは`rencrow-llm`、将来のNode artifact、検証したLLM target
構成・適合levelを組み合わせて互換性を記録します。

## RenCrow_STT

```text
primary
  rencrow-stt             Go binary
       |
       v
companion: stt-target     bundled=false / required=true
  transcription engine + Model + weights + decoder + compute

companion: python-compat  bundled=false / required=false
  Go移行中の現行Python HTTP／WebSocket serverとin-process providers
```

Go Gatewayは公開HTTP／WebSocket契約、音声入力validation、target adapter、文字起こし
結果とerror／fallbackの正規化を所有します。Model load、decode、warmup、GPU最適化は
STT targetの責務です。現行Python providerはまだ同一processに演算を含むため、
compatibility runtimeとして記録します。

## RenCrow_TTS

```text
primary
  rencrow-tts             Go binary
       |
       v
companion: tts-target     bundled=false / required=true
  synthesis engine + Model + weights + voice assets + codec + compute

companion: python-compat  bundled=false / required=false
  Go移行中の現行Python TTS APIとIrodori連携
```

Go Gatewayは文章整形、character／style／voice routing、target adapter、WAV中継を
所有します。reference音声、seed、engine parameter、Model load、合成演算はTTS target
の責務です。現行の`RenCrow_Irodori_TTS` deploymentはこのtargetに該当します。

Visionへ同じ分離形を適用する場合も、module側でprimary binaryと外部演算runtimeの
境界を正本化してからmanifestへ追加します。未確認の言語やartifact名は先行登録しません。
