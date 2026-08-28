# Full-system verification contract v2

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

## Owner Evidence acquisition contract

### Goal and boundary

`execute-set`は全moduleに共通な4引数だけを渡し、module固有のendpoint、path、PID、認証情報、
fixture、study IDを解決しない。この境界は維持する。owner-specific flagをToolsへ追加して横断runnerを
module知識の第二正本にしてはならない。

各owner verifierは、共通入口だけで呼ばれた場合に次の一方向の経路を実装する。

```text
frozen check request
  -> owner manifest command_id
  -> owner-local acquisition plan
  -> canonical catalog / active config / service manager / owner API
  -> authenticated read-only observation or owner-declared verification-safe request
  -> sanitized bounded Evidence JSON
  -> owner receipt
```

owner-specific flagはmodule単体診断とtest injectionには残せるが、フルチェックの必須経路にしては
ならない。flag指定時と自己収集時は同じvalidator、policy、Evidence schema、receipt判定を通す。

この設計は次を採用しない。

- Toolsがmodule別flag、endpoint、credential pathを持つcentral adapter。
- 監査前に人またはLLMがEvidence fileを手作業でpre-seedする運用。
- stale Evidenceの時刻だけを更新する再利用。
- remote identityをhealth、ping、SSH login、process名だけで推定する短縮経路。
- 全module共通の新しいattestation service／registry。

理由は、いずれもowner、正本、認証、failure domainを横断層へ複製し、同じ変更を複数repoへ同期する
Semantic Duplicationを作るためである。共通層はPlanとschemaだけ、取得と判定はownerだけに置く。

### Input classes

owner checkが必要とする入力は、owner manifestとowner verifierで次の4区分へ固定する。

Owner manifest v3では各checkの`executor`へ次のadditive contractを必須化する。Toolsは構造、enum、
required inputの重複、`verification_safe`とsafety gateの整合だけを検証し、`source`を解決・実行しない。

```json
{
  "executor": {
    "kind": "owner_cli",
    "command_id": "module-canonical-e2e",
    "acquisition": {
      "mode": "owner_self_collect",
      "verification_safe": true,
      "inputs": [
        {
          "id": "canonical_auth",
          "class": "credential_reference",
          "required": true,
          "source": "owner_active_config"
        },
        {
          "id": "media",
          "class": "verification_fixture",
          "required": true,
          "source": "owner_fixed_fixture"
        }
      ]
    }
  }
}
```

`mode`は`owner_self_collect`だけを許す。`source`は
`ecosystem_catalog / owner_active_config / owner_service_manager / owner_operations_api /
owner_fixed_fixture / owner_external_artifact`のいずれかとする。これは取得元の責務を示す識別子であり、
path、URL、shell command、credential値をmanifestへ埋め込まない。`external_prerequisite`をrequiredにしても
Planは実行可能であり、ownerが実体不在を`prerequisite_absent`として観測する。

| Class | Meaning | Common execution behavior |
| --- | --- | --- |
| `discoverable` | catalog pin、active config、installed artifact、service/PID、listener、owner healthなど、正本から決定的に取得できる | owner verifierが自己収集する。未実装なら`evidence_acquisition_not_implemented` |
| `credential_reference` | token値ではなく、ownerが許可したcredential file／service credentialへの参照 | owner verifierがowner policyに従って読む。値をEvidenceへ出さない。不在は`authentication_unavailable` |
| `verification_fixture` | bounded media、音声、browser scenario、isolated snapshotなど、check用に安全に生成またはrepoから決定できる | owner verifierが固定fixture identityを検証して使用する。任意pathや任意shellを受けない |
| `external_prerequisite` | production backup artifact、remote attestation、policyで許可されたstudy等、監査が生成してはならない実体 | 捏造・代替せず`prerequisite_absent`または`policy_blocked` |

分類不能な入力はfail closedにし、文字列類似やLLM推測でpath、endpoint、credential、studyを選ばない。

### Acquisition rules

1. `catalog -> active config -> service manager / owner API`の順で正規identityを解決する。backup、example、
   disabled section、旧generationをactive inputとして採用しない。
2. local processは実行file、完全なcommand line、service/cgroup、config path、listener、起動時刻を照合する。
   remote runtimeはowner moduleの認証済みattestation contractを使い、SSH成功やhealthだけでidentityを
   推定しない。
3. authenticationはownerが固定したscopeだけを使う。credential値、Authorization header、private path、
   個人情報をEvidenceへ保存しない。
4. E2E requestはowner manifestで`verification_safe=true`と宣言され、owner policyが同期許可する固定scenario
   だけを実行できる。restart、deploy、restore promotion、取引、任意外部送信を行わない。
5. policyが拒否する場合は迂回、scope弱体化、direct backend、test doubleを使わず`policy_blocked`を返す。
6. owner verifierは取得したEvidenceを`--evidence-dir`直下へexclusive createし、regular／non-symlink、
   mode `0600`、owner/check/command identity、UTC `observed_at`、route、proofを記録する。
7. `passed` Evidenceは必ずbounded fileとしてreceiptから`relative:`参照する。`runner:`参照は
   `failed`／`blocked`／`unverified`の取得失敗境界にだけ使用できる。

### Failure taxonomy

`failure_boundary`は人間向け文章ではなく、少なくとも次の安定した分類を先頭tokenとして返す。
module固有詳細はEvidence内の非機密fieldへ置く。

| Boundary | Meaning | Remediation owner |
| --- | --- | --- |
| `evidence_acquisition_not_implemented` | discoverable／fixture入力の自己収集routeが未実装 | check owner module |
| `prerequisite_absent` | production artifact、study、remote attestation等の実体が存在しない | artifact／runtime owner |
| `authentication_unavailable` | 正規credential referenceまたはscopeがない | authentication owner |
| `policy_blocked` | owner policyがcheckの効果を明示拒否 | policy owner。監査は迂回しない |
| `canonical_route_unavailable` | 正規module routeへ到達できない | runtime owner |
| `identity_mismatch` | source、artifact、publication、process identityが不一致 | deployment owner |
| `evidence_invalid` | stale、future、schema不正、境界外参照 | Evidence producer |

入口未実装を`prerequisite_absent`、認証不足、route不通へ言い換えてはならない。反対に実体がない場合、
fixtureや過去Evidenceを生成して入口実装済みに見せてはならない。

### Required acquisition closure

2026-08-28監査で共通入口から閉じなかったcheckを次の実装単位として固定する。`Target behavior`は
成功の捏造ではなく、正しいEvidenceまたは正しいblocked boundaryを返すことを意味する。

| Owner | Checks | Input class and target behavior |
| --- | --- | --- |
| Workspace | `workspace_portable_snapshot_contract` | `discoverable`: canonical portable snapshot rootをowner規則で解決 |
| Workspace | `workspace_migration_snapshot_e2e` | `verification_fixture`: 2 recipientのisolated stateless artifactをbounded tempで生成・inspect・dry-run restore |
| Workspace | `workspace_deploy_identity_chain` | `discoverable`: catalog、repo、installed binary identityを自己収集 |
| Workspace | `workspace_backup_restore_evidence` | `external_prerequisite`: production state export、暗号化artifact、restore receipt不在なら`prerequisite_absent` |
| TRADE | `trade_deploy_identity_chain`, `trade_runtime_identity_lifecycle_security` | `discoverable` + `credential_reference`: catalog、artifact、service、canonical durable rootをowner境界で収集 |
| TRADE | `trade_canonical_route_e2e`, `trade_ledger_hash_chain_e2e` | `credential_reference` + `external_prerequisite`: policy許可と実在studyをowner APIから選定。不在・拒否を区別 |
| STT | `stt_deploy_identity_chain`, `stt_runtime_identity_lifecycle_security` | `discoverable`: 205のGateway／backend配置をactive configとremote attestationから確認 |
| STT | `stt_transcription_e2e`, `stt_canonical_actor_e2e` | `verification_fixture` + `credential_reference`: 固定音声fixtureを正規Gateway／CORE Actor routeへ送る |
| TTS | `tts_deploy_identity_chain`, `tts_runtime_identity_lifecycle_security` | `discoverable`: 205のGateway／Irodori identityをactive configとremote attestationから確認。204を代用しない |
| TTS | `tts_synthesis_e2e`, `tts_canonical_actor_e2e` | `verification_fixture` + `credential_reference`: 固定文を正規Gateway／CORE Actor routeでWAV receiptまで検証 |
| Vision | `vision_deploy_identity_chain`, `vision_runtime_identity_lifecycle_security` | `discoverable`: local owner service、artifact、config、listenerを自己収集 |
| Vision | `vision_analyze_e2e`, `vision_canonical_actor_e2e` | `verification_fixture` + `credential_reference`: 固定imageをVision／CORE Actor routeへ送る |
| PORTAL | `portal_browser_proxy_e2e`, `portal_canonical_actor_e2e` | `verification_fixture` + `credential_reference`: 固定allowlisted browser scenarioと正規認証scopeをownerが解決 |
| Tools | `tools_execution_boundary_security_lifecycle` | `discoverable`: active Tool server/process、policy、security boundaryをlive Evidenceへ発行 |
| LLM | `llm_runtime_identity_lifecycle_security` | `discoverable` + `credential_reference`: Runtime config、listener、認証済みremote attestationをownerが解決 |

TTS `tts_gateway_readiness`はこの24件に含めない。Evidence入口ではなく、owner verifierがactive configから
205の正規Gateway URLを解決せずlocalhost既定値を使用するconfiguration defectとして別に扱う。

### Remote runtime attestation

LLM／STT／TTS等の別host runtime identityは、公開healthやSSH shellをdeploy identity Evidenceにしない。
各owner moduleは既存の認証済みoperations routeを拡張し、少なくとも次を返すread-only attestationを
所有する。新しい横断attestation serviceは作らない。

```json
{
  "schema_version": "rencrow.runtime-attestation/v1",
  "owner": "RenCrow_MODULE",
  "observed_at": "RFC3339-UTC",
  "artifact": {"revision": "full-sha", "sha256": "sha256"},
  "service": {"identity": "owner-unit", "pid": 123, "started_at": "RFC3339-UTC"},
  "config": {"identity": "sha256"},
  "listeners": [{"address": "host:fixed-port", "protected": true}],
  "request_id": "bounded-correlation-id"
}
```

responseはowner認証・read scopeを必須とし、secret、環境変数値、任意filesystem path、完全なcommand lineを
remoteへ公開しない。verifierはcatalog pin、active config、attestation、実request receiptを照合する。

### Implementation ordering and acceptance

実装はWIP=1でowner moduleごとに行い、共有contract変更を並列編集しない。

1. owner verifierへcommon-args-onlyのRED testを追加する。
2. acquisition planをowner module内へ実装し、owner-specific flag経路と同じvalidatorへ合流させる。
3. bounded Evidence、failure taxonomy、credential非漏洩をunit／architecture testで強制する。
4. owner checkをcommon argsだけで実行し、正規Evidenceまたは正確なblocked boundaryを確認する。
5. source、artifact、publication、active runtimeを照合して配備後checkを行う。
6. 全owner完了後にだけ5 phaseを再composeし、`execute-set`を一度実行する。

受入条件は「24件がすべてpassed」ではない。各checkがcommon argsだけで自己収集経路へ到達し、実体・認証・
policy不足を入口未実装と混同せず、bounded owner receiptを返すことを第一条件とする。そのうえで
`all_clear=true`にはproduction backup、remote attestation、TRADE policyを含む全保証の実成立が必要である。

manifest v3移行はowner verifier実装と同じImplementation Unitで行う。v2 checkをv3として黙示補完せず、
Coverage Policyがv3を必須化した後にv2が残っていればcomposeをfail closedにする。

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
- owner manifest v3で`acquisition.mode`欠落、未知input class／source、input ID重複を拒否。
- `verification_safe=true`の外部効果checkで`safety_gate=false`を拒否。
- common argsだけのowner contract testで、全`discoverable`／`verification_fixture`入力が
  `evidence_acquisition_not_implemented`にならないこと。
- credential、任意path、任意URL、任意shellがmanifestまたはbounded Evidenceへ漏れないこと。
- Evidenceのstale、future、欠落、非UTC`observed_at`を拒否し、5分windowの両端だけを受理。
- `passed`／`not_applicable`の空`evidence_refs`を拒否し、`failed`／`blocked`／`unverified`の
  空Evidenceを許す場合は`failure_boundary`必須とする。
- 5 phaseの一つ、またはincluded receipt一つの欠落でaggregate-set失敗。
- failed／blocked／deferred／unverifiedが一つでもあれば`all_clear=false`。
