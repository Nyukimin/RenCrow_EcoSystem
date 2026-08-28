# Full-system verification contract v1

## Outcome

`システム全体を検証して`は、EcoSystem Coverage Policy、全owner check、5 phaseの
immutable Plan、実I/O receiptを一つのtrackerへ集約するread-only監査である。
health、listener、unit test、代表機能だけを全体成功へ昇格しない。

## Ownership

| Contract | Owner |
| --- | --- |
| component集合、保証分類、必須phase、横断surface | RenCrow EcoSystem |
| Plan合成、coverage検査、receipt schema検証、aggregate-set | RenCrow_Tools |
| check意味論、実行、Evidence、receipt | 各module |
| 認証、policy、実Actor、Viewer/Public API | RenCrow_CORE |
| 自然言語による結果説明 | LLM residual |

EcoSystemとToolsはmodule固有endpoint、payload、DB schema、判定logicを持たない。
各moduleは他ownerのDB、backend、内部routeを直接検査しない。

## Owner manifest v2

必須だがcanonical runtime未実装のcomponentは、Coverage Policyの構造化された
`temporarily_excluded_components`に限り、現行のrequest、Plan、binding、receipt母数から一時的に
除外できます。component宣言と将来のcoverage requirementsは維持し、trackerへ理由と再参加条件を
必ず投影します。ASSISTANTは`required_component_unimplemented`として扱い、
`canonical_runtime_implemented`になった同じImplementation Unitで除外を削除します。

各checkはplanner v1 fieldsに次を加える。

```json
{
  "coverage": ["canonical_e2e", "receipt_trace"],
  "executor": {
    "kind": "owner_cli",
    "command_id": "module-canonical-e2e"
  },
  "receipt_schema": "rencrow.check-receipt.v1",
  "surfaces": ["route_security_exposure"]
}
```

`security_exposure`を含むcheckは`safety_gate=true`でなければならない。
owner manifestは実装されていないcommand_idを成功扱いにしない。

## Owner verifier CLI

各moduleはprimary source tree内にread-only verifierを所有する。binary名は
`RenCrow_<NAME>`から決定的に`rencrow-<name>-verify`へ変換する。全verifierは次の
共通入口を提供する。

```text
rencrow-<name>-verify run
  --manifest <owner-manifest>
  --check-id <declared-id>
  --observed-at <RFC3339-UTC>
  --evidence-dir <bounded-directory>
  [owner-specific read-only inputs]
```

任意shell文字列は受け取らない。`check_id`とmanifestの`executor.command_id`を固定allowlistへ
照合し、全allowlistを実行前に検証する。未実装command、認証不足、正規route不通、必要fixture
不足は代替経路を作らず`blocked` receiptを返す。外部効果が必要なcheckは認証済みscopeと
owner policyを同期評価し、許可されない場合は`blocked`または`not_applicable`にする。

`--observed-at`はfrozen compositionから渡されるRFC3339 UTCの要求時刻であり、owner validatorへ
そのまま伝播する。`passed`を成立させる全EvidenceはRFC3339 UTCの`observed_at`を持ち、次の
両端を含むfreshness windowに入らなければならない。

```text
receipt.observed_at - 5m <= evidence.observed_at <= receipt.observed_at
```

下限・上限ちょうどは有効で、stale、future、欠落、非UTCのEvidenceは`passed`へ昇格しない。
Evidenceのファイルmtimeは補助的な追跡情報にはできるが、明示的な`observed_at`の代わりには
ならない。認証済みlive requestの結果、canonical route、実Actor、生成物を含むEvidenceも同じ
windowで検証する。

exit statusは次に固定する。

| Exit | Meaning |
| ---: | --- |
| 0 | valid receipt emitted (`passed`または根拠付き`not_applicable`) |
| 10 | `failed` receipt emitted |
| 20 | `blocked` receipt emitted |
| 30 | `unverified` receipt emitted |
| 2 | CLI／manifest／schema error。receiptとして集約しない |

## Receipt v1

```json
{
  "schema_version": 1,
  "receipt_schema": "rencrow.check-receipt.v1",
  "check_id": "module-check",
  "guarantee_id": "module-guarantee",
  "owner": "RenCrow_MODULE",
  "status": "passed",
  "observed_at": "2026-08-27T00:00:01Z",
  "route_or_target": "canonical owner route",
  "evidence_refs": ["relative:evidence.json"],
  "failure_boundary": ""
}
```

`observed_at`はRFC3339 UTCで、要求された`--observed-at`より未来になってはならない。owner
validatorは要求時刻をEvidence検証へ伝播し、receiptを後から再生してfreshnessを回避しない。
Evidenceはcredential、token、個人情報を含めず、監査directoryから追跡できる形式にする。
`passed`と`not_applicable`は空でない`evidence_refs`を必須とする。`failed`、`blocked`、
`unverified`は`evidence_refs`を空にできるが、その場合は空でない`failure_boundary`を必須とする。
空の`evidence_refs`と空の`failure_boundary`の組み合わせは無効であり、Evidenceを返す場合も
bounded directory内の参照だけを使う。
LLMの自然言語はreceiptにならない。

## Full execution

1. catalog validationを通す。
2. Coverage Policyの全required phaseを同一評価時刻でcomposeし、5つのfrozen composition出力を
   `composition-dir/<phase>.json`へ保存する。component、check、endpointの集合はcatalog、
   policy、owner manifestから動的に決め、Skillへ固定値を複製しない。
3. Planが1つでもblocked、coverage missing、unexpected exclusionならcheckを開始しない。
4. 5つのcomposition出力を保存した後、Toolsの`execute-set`を一度だけ実行する。実行前に
   `owner-bin-dir`、`workspace-root`、bounded `evidence-dir`、`receipt-dir`を明示し、
   owner binary、参照manifest、compositionのregular/non-symlink境界をpreflightする。bounded
   `evidence-dir`とEvidence参照の境界はowner CLIでも検証する。

   ```bash
   go -C /home/nyukimi/RenCrow/RenCrow_Tools/tools/quality/full_system_verification \
     run ./cmd/rencrow-full-system-verification execute-set \
     --composition-dir /path/to/compositions \
     --owner-bin-dir /path/to/owner-verifiers \
     --workspace-root /home/nyukimi/RenCrow \
     --evidence-dir /path/to/evidence \
     --receipt-dir /path/to/receipts \
     --pretty
   ```

   `execute-set`はfrozen bindingから決まるowner CLIだけへ共通引数を渡すdeterministic executor
   であり、shell、endpoint解決、owner-specific flag、restart、fixを行わない。owner binaryまたは
   manifestが欠けていればpreflight errorとして停止し、Toolsはowner receiptをfabricateしない。
   `blocked`と`unverified`を発行できるのはowner CLIだけであり、Tools、CORE、LLMがそれらのreceiptを
   代作してはならない。
5. `execute-set`が書いたphase別receiptとaggregate trackerを、同じfrozen compositionに対する
   `aggregate-set`契約として検証する。`all_clear=true`は全checkが`passed`または根拠付き
   `not_applicable`の場合だけ成立する。

監査はrestart、fix、build、deploy、pushを行わない。是正と配備は別Implementation Unitで行い、
再起動後に監査を最初から再実行する。

## Tests

- Policyとmanifest componentの完全一致。
- 必須phaseが空ならcompose失敗。
- component／surface coverage欠落ならcompose失敗。
- security checkの`safety_gate=false`を拒否。
- 未知、重複、owner不一致のcommand／receiptを拒否。
- owner binary／manifestの欠落をexecute-setのpreflight errorとし、Toolsがreceiptを作らないこと。
- owner CLI以外が`blocked`／`unverified` receiptを作る経路を拒否。
- Evidenceのstale、future、欠落、非UTC`observed_at`を拒否し、5分windowの両端だけを受理。
- `passed`／`not_applicable`の空`evidence_refs`を拒否し、`failed`／`blocked`／`unverified`の
  空Evidenceを許す場合は`failure_boundary`必須とする。
- 5 phaseの一つ、またはincluded receipt一つの欠落でaggregate-set失敗。
- failed／blocked／deferred／unverifiedが一つでもあれば`all_clear=false`。
