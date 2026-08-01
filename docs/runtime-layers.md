# Runtime layers

EcoSystem manifestは、module repositoryとversionだけでなく、利用者へ配布するprimary runtimeと、利用環境側で別途用意するcompanion runtimeを区別します。

## Contract

```text
module release
  `- runtime.primary
       implementation: Goなど
       artifact: 配布artifact名
       status: planned / development / available

user environment
  `- runtime.companions[]
       external compute、system serviceなど
```

- `primary`はEcoSystem releaseが取得・checksum検証する配布単位です。
- `companions`はprimaryと連携しますが、別process、別runtime、別計算資源として扱います。
- `external-compute`はmodule releaseへbundleしません。
- companionを独立したRenCrow moduleとして登録するかは、独立repository、release、公開contractを持つ場合だけ別途判断します。
- module内部の配置、API、Config詳細は各module repositoryを正本とします。

## RenCrow_LLM

```text
primary
  rencrow-llm             RenCrow LLM Gateway / control host
       |
       `-> rencrow-llm-node  RenCrow LLM Runtime / compute host
             |-> local Backend -> Model + weights + KV + compute
             `-> provider / Agent Runtime Backend -> Model
```

BackendとModelはRenCrow LLM Runtimeに付随し、EcoSystemの独立componentにはしません。
`rencrow-llm-node`もRenCrow_LLMとBackend契約、status schema、release cadenceを共有するため、
別moduleにしません。EcoSystemはGateway／Runtimeの同一module version、認証、
status schema、Backend contract、実生成を組み合わせて互換性を記録します。

## RenCrow_STT

```text
primary
  rencrow-stt             Go binary
       |
       v
companion: stt-target     bundled=false / required=true
  transcription engine + Model + weights + decoder + compute

```

Go Gatewayは公開HTTP `POST /v1/audio/transcriptions`、音声入力validation、
target adapter、文字起こし結果とerrorの正規化を所有します。Viewer向けWebSocket
`/stt`はCOREが所有し、受け取った音声chunkをGatewayのHTTP公開APIへ中継します。
Model load、decode、warmup、GPU最適化はSTT targetの責務です。COREは
RenCrow_STT Gatewayの公開HTTP APIだけを使用し、物理targetへ直接接続しません。

## RenCrow_TTS

```text
primary
  rencrow-tts             Go binary
       |
       v
companion: tts-target     bundled=false / required=true
  synthesis engine + Model + weights + voice assets + codec + compute

```

Go Gatewayは文章整形、character／style／voice routing、target adapter、WAV中継を
所有します。reference音声、seed、engine parameter、Model load、合成演算はTTS target
の責務です。現行の`RenCrow_Irodori_TTS` deploymentはこのtargetに該当します。

## RenCrow_Vision

```text
primary
  rencrow-vision          Go binary
       |
       v
companion: vision-backend bundled=false / required=true
  Wild backend + Model + weights + GPU + optional FFmpeg/FFprobe
```

`RenCrow_Vision`はCOREとWild backendの間の必須認識interfaceです。media検証、
動画frame sampling、Wild request、結果正規化を所有します。COREはVisionのbase URLだけを
持ち、Wild endpoint、Model、media変換parameterを持ちません。標準primaryはGo binaryで、
Python serviceはdevelopment／移行用です。

## RenCrow_Image

```text
primary
  rencrow-image           Go binary
       |
       v
companion: image-backend  bundled=false / required=true
  ForgeNeo / ComfyUI / Z-Image + Model + weights + GPU + output storage
```

`RenCrow_Image`はCOREとForgeNeo／Z-Image等のbackendの間の必須画像生成interfaceです。
公開HTTP contract、backend profile、Model／workflow／生成parameterの所有境界を持ちます。
標準primaryはGo binaryで、Python Gatewayはdevelopment／移行用です。
