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
  rencrow-llm             Go binary
       |
       v
companion: llm-target     bundled=false / required=true
  Backend + Model + weights + KV + compute

companion: python-compat  bundled=false / required=false
  Go移行中の現行Python role proxy / management runtime
```

BackendはLLM targetに付随し、EcoSystemの独立componentにはしません。EcoSystemは`rencrow-llm` binaryのreleaseと、検証したLLM target構成・適合levelを組み合わせて互換性を記録します。

同じ分離形がSTT、TTS、Visionにも必要になった場合は、各module側でprimary binaryと外部演算runtimeの境界を正本化してからmanifestへ追加します。未確認の言語やartifact名を先行登録しません。
