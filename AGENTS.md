# RenCrow Project Rules

このファイルが Cursor / Codex / Claude の workspace 常時ルールの唯一の正本である。本文を `~/.codex/AGENTS.md` や `~/.cursor/rules` へ複製しない。モジュール固有の `AGENTS.md`（例: `RenCrow_CORE/AGENTS.md`）は module-local の追加制約であり、本ファイルの複製ではない。矛盾する場合は本ファイルを優先し、module 側は CORE 正本と module 所有範囲だけを扱う。

## Agent 配置

- Cursor: workspace が catalog root のときは本ファイルを直接読む。子 repository だけを workspace にしたときは、`~/.cursor/rules/rencrow-workspace.mdc` が本ファイルへの参照だけを持つ（本文のコピーは禁止）。
- Codex: 子 Git repository 起動では Git root より上を辿らない。`~/.codex/AGENTS.md` は本ファイルへのシンボリックリンクにする。通常ファイルへの全文コピーは禁止。
- Claude: `CLAUDE.md` は入口であり、本ファイルと食い違えば本ファイルが勝つ。
- 補助 Skill（`~/.codex/skills/global-engineering-rules`、`modularization-rules` 等）は判断軸であり、本ファイルの境界・禁止事項を上書きしない。

## 完了整合性

- 編集前に、目的・所有リポジトリ／モジュール・正本・稼働成果物・許可範囲・要求ごとの終端証拠を確定する。不明なら編集せず調査する。
- ユーザー訂正は競合する仮説・証拠を無効化して現行制約へ昇格し、目的変更またはコンテキスト圧縮後は要求と証拠表を再構築する。
- 要求終端条件に未確認が一つでもあれば「完了」「達成(100%)」と報告せず、一部達成と不足境界を示す。サブエージェントの成果は主エージェントが実際の差分・範囲・試験・境界を確認するまで助言扱いとする。

## Operational Outcome Definition of Done

- ユーザーのGoalは、指定された中間成果物ではなく、それによって利用主体が達成したい運用成果として解釈する。仕様、schema、ストア、API、CLI、GUI、コード、unit test、build、deploy、healthの個別成功は部品の完成であり、単独でシステムの完了証拠にしない。
- 着手前に、`source -> owner -> policy -> state -> runtime route -> 実際の利用主体 -> 利用者に見える結果 -> receipt/trace`の終端経路を受入条件として定義する。対象がBacklog由来であっても、「実装項目をDONEにした」ではなく、正規routeで運用目的が達成し、再起動後も維持された証拠を終端とする。
- 対象データの取得、保存、変換、投影が成功しても、本来の運用経路から参照・判断・利用できなければ未完了とする。例えば記憶取込は、原文保存やcandidate生成ではなく、必要な状態確定、Recall投影、CORE Agentによる実際の想起・利用、traceまでを終端とする。
- E2Eは内部function、test double、バックエンド単体で代用せず、本番と同じ認証、policy、owner module、runtime route、実Actorを通して証明する。

## User Decision GUI Requirement

- 運用上ユーザーの意味判断、価値判断、選択、確定が必要な機能は、その判断を完結できるGUIを同じImplementation Unitの必須成果に含める。CLI、API、DB row、log、JSON、手順書だけを渡して利用者の手作業に委ねない。
- 判断GUIは少なくとも、判断対象、必要理由、原文／Evidence、現在状態、選択肢、推奨案と根拠、各選択肢の影響・リスク、編集可能範囲、実行／拒否／保留、未処理件数と進捗、実行後のreceiptを表示する。任意filesystem path、任意SQL、owner外のデータは公開しない。
- 判断対象はサイレントな`blocked`や内部queueに留めず、認証済みownerがGUIから発見して必要情報を読み、一回の明示操作で次状態を確定できるようにする。GUI操作後はCORE正本へ即時反映し、実際の利用経路とreceiptまでE2Eで確認する。
- 認証済みrequest scopeとmachine-readable policyで決定可能な工程は従来どおり直ちに実行・`rejected`・`blocked`を確定し、GUI判断へ不要に逃がさない。GUIはpolicyで代替できない利用者固有の意味・価値判断の操作面であり、ユーザーの返答待ちで内部workflowを解除する汎用human gateにしない。GUI送信は新しい認証済みrequestとして同期評価し、即時に終端状態とreceiptを返す。

## Workspace Module Roots

Work in the specific module root instead of treating the parent directory as one source tree.

| Module | Root |
| ------ | ---- |
| CORE / Chat / Viewer | `RenCrow_CORE` |
| CMD / CLI | `RenCrow_CMD` |
| PORTAL | `RenCrow_PORTAL` |
| ASSISTANT | `RenCrow_ASSISTANT` |
| LLM | `RenCrow_LLM` |
| STT | `RenCrow_STT` |
| TTS | `RenCrow_TTS` |
| Vision | `RenCrow_Vision` |
| Image | `RenCrow_Image` |
| TRADE | `RenCrow_TRADE` |
| GAMES | `RenCrow_GAMES` |
| Tools | `RenCrow_Tools` |
| Workspace snapshot | `RenCrow_Workspace` |
| Ecosystem catalog | catalog root（本リポジトリ） |

Model-specific repositories such as `RenCrow_GPT120B`, `RenCrow_Qwen36_27B`, and `RenCrow_Gemma4` are LLM external-runtime profiles. They are not CORE, Agent, or independent routing owners.

## Model Roles

- GPT-5.6 sol (max reasoning effort) is the orchestrator. It plans, delegates, monitors progress, reviews results, and coordinates the work.
- GPT Luna (max reasoning effort) is the executor. It performs implementation, modification, testing, and other hands-on tasks.

## Read Order

1. `AGENTS.md`
2. `README.md`
3. `docs/README.md`
4. `ecosystem.yaml`
5. The authoritative docs in every affected module repository

## RenCrow EcoSystem Role

`RenCrow_EcoSystem` is the official entry point and integration catalog for the
RenCrow product family. This repository is also the workspace-root management
repository, normally cloned as `RenCrow`; independently released child
repositories remain direct children and are never copied into this repository.

This repository owns:

- the ecosystem component manifest and compatibility matrix;
- ecosystem-level architecture, installation, and release documentation;
- integration verification policy and release acceptance criteria;
- links to each module's authoritative specification and release.

This repository does not own:

- module implementation source, module-specific APIs, or internal design;
- production Persona, Memory, Recall, synchronous policy decisions, or LLM routing behavior;
- reusable tools, generated artifacts, runtime state, or secrets;
- copies of module repositories or Git submodules.

## EcoSystem Source-of-Truth Rules

- A module repository is authoritative for its source, API, build, tests,
  configuration, and module-specific roadmap.
- This repository is authoritative for declared source pins, tested release
  combinations, and ecosystem-wide guidance. A source pin alone is not a
  compatibility claim.
- Do not duplicate detailed module specifications here. Link to them and record
  only the cross-module consequence.
- Do not mark a component version as compatible until the declared integration
  checks have passed.
- `development`, `source-pinned`, `unpinned`, and `verified` are explicit states.
  `source-pinned` uses full Git commit SHAs for implemented components and
  `planned` only for an optional runtime that does not exist yet. Never invent
  a release tag or commit to make the matrix look complete.
- Describe only the current architecture and explicitly planned components.
  Remove superseded systems and interfaces from the manifest and documentation
  instead of retaining migration or rejection narratives.

## EcoSystem Repository Rules

- Keep each component as an independent Git repository with its own CI, tags,
  and releases.
- Do not add Git submodules. The manifest identifies repositories and versions.
- Keep cross-module reusable tooling in `RenCrow_Tools`; only validation tightly
  coupled to `ecosystem.yaml` belongs under this repository's `scripts/`.
- Keep examples secret-free. Do not commit `.env`, credentials, runtime logs,
  databases, generated binaries, model files, or downloaded release archives.
- Changes to compatibility claims require evidence in the change description or
  a repo-native verification record.
- Child `RenCrow_*` repositories belong directly under this catalog root and
  are ignored by this repository's `.gitignore`.

## EcoSystem Validation

Run before considering a catalog change complete:

```bash
make check
```

When all declared child repositories are available at the catalog root, also run:

```bash
make check-workspace
```

To verify repository rules, local test contracts, CI, and the Workspace root
snapshot, run:

```bash
make check-governance
```

On Windows use `.\scripts\test-local.ps1` or the repository's documented
`make PYTHON=python` command, and confirm Linux coverage through `make check`
or the corresponding CI job.

## EcoSystem Cross-Platform Requirement

This repository must work on Windows, Linux, and macOS. Do not write code or
tests that pass on only one of them.

- Join paths with `pathlib.Path` in Python. Never concatenate `/` or `\\` into a
  path string.
- Escape any path embedded in YAML, JSON, or a shell command. Windows paths
  contain `\\`, so a raw embed is read as an escape sequence such as `\\U` and
  fails to parse.
- Do not depend on a specific line ending (LF or CRLF) in comparisons or tests.
- Do not assume executable bits, symlinks, or a case-sensitive filesystem.

## Simplicity and Top-Down Traceability

- Requirements, safety, and consistency being equal, always choose the simpler and easier-to-explain design.
- Layers and modules exist to help humans understand the system. A primary use case must be traceable in one direction from entrypoint through orchestration and domain decisions to storage or external I/O.
- Each step must make its input, decision, output, and next owner apparent. A design that requires repeated cross-file backtracking to understand is not acceptable.
- Do not add unnecessary abstractions, interfaces, registries, wrappers, forwarding layers, or speculative extension points. Prefer integration when it is easier to read than separation.

## CLI-First / LLM-Residual Rule

- システム構築の各フローでは、まず各工程がCLIで決定的に完了できるかを分類する。
- 取得、検証、変換、計算、状態遷移、オーケストレーション、外部操作のうち決定的に完了できるものは、LLMに任せず所有モジュールのCLIで完了させる。
- CLIの契約は、明示的な入力、機械可読で境界のある出力、終了ステータス／失敗、再現可能なreceipt／証跡を公開する。
- LLMは曖昧さの解消、意味判断、選択・計画、言語・創作生成を要する残余だけを扱う。LLMの決定的な仕事をCLIで包むだけのwrapperをCLI-firstとは呼ばない。
- LLM出力が状態変更または外部効果を起こし得る場合は、所有CLI／policyが検証し、決定的に実行または拒否する。
- RenCrowでの`CLI`は実行・契約の形を示すもので、`RenCrow_CMD`の自動的な所有権を意味しない。実際の所有モジュール、認証／policy、canonical runtime routeを維持し、CLI-firstのためにmodule routeを短縮／迂回しない。
- 検証では、決定的CLIの動作と、該当する場合は境界付きLLM残余の動作を分けて証明する。

### Check Plan Pruning Rule

- 検査を実行する前に、対象purposeとphaseに対するmachine-readable Check Planを確定する。各checkは最低限、`check_id`、保証対象、owner、実行phase、結果consumer、failure actionを宣言する。
- checkの高コスト、timeout、失敗、都合の悪い結果だけを理由に除外してはいけない。safety／security／認証／policy gateは、より強い同一保証の正本Evidenceがあっても暗黙に削除しない。
- 現在phaseと異なるcheckは`deferred`、consumerまたはfailure actionを持たない非safety checkは`excluded`、同じ保証を持つ明示replacementの有効なpassed receiptがあるcheckだけを`duplicate`として除外できる。意味的類似をLLMや文字列類似で推測して削除しない。
- malformedなsafety check、存在しないreplacement、保証不一致、曖昧な定義はfail closedでPlanを`blocked`にする。除外できないcheckは実行対象へ残す。
- Planは入力、評価時刻、included／excluded／deferred、理由、replacement receiptをcanonical JSONとhashで固定する。検査runnerは固定Planだけを消費し、Plan作成と検査実行の間でcheckを再解釈しない。
- runtimeのPlan pruningはsource codeを削除しない。恒久削除は運用Evidenceを確認し、仕様更新、TDD、通常のreviewを通す別の実装変更として扱う。
- 横断planner executableとschema validationは`RenCrow_Tools`、module固有checkとreceiptは各owner module、cross-module契約はEcoSystemが所有する。EcoSystemやCOREへ各moduleのcheck判定ロジックを複製しない。

### CLI / LLM Classification Gate

- 調査、仕様作成、設計、実装、修正、運用フローの各案件では、編集または実装計画を確定する前に、対象工程を最低限次の3区分へ分類してユーザーへ提示する。
  - `CLI`: 入力と規則が明示され、同じ入力から再現可能な結果、終了status、receipt／証跡を決定的に生成できる工程。
  - `LLM`: 曖昧な意味の復元、複数の妥当案からの選択、自然言語理解・計画・創作など、決定規則だけでは完了できない工程。
  - `Boundary`: LLM出力のschema検証、policy判定、認証、状態変更、外部効果、保存、再試行、監査など、LLMの前後を決定的に拘束する所有CLI／runtime工程。
- 分類結果には、工程、区分、所有module、入力、出力、失敗時status、証跡、LLMを使う場合はその採用理由を記録する。採用理由は、意味判断等によりLLMが不可欠な`必須性`、または同一の評価dataset・品質指標・制約下で決定的手法より有意かつ十分に高い品質を示す`品質優位性`のいずれかで立証する。「便利」「柔軟」「既存がLLMを使う」だけでは採用理由にならない。
- `LLM`へ分類する前に、parser、schema、query、state machine、policy、既存API／CLIで決定可能かを確認する。決定可能でもLLMの品質優位性を採用理由にする場合は、決定的baselineとLLM方式を同じ入力、評価指標、失敗条件、費用・遅延・再現性・安全制約で比較し、評価結果を証跡として残す。品質差が不明、僅少、または制約上の不利益を正当化できない場合は`CLI`を選ぶ。
- 決定可能な部分と意味判断または品質優位性を必要とする部分が混在する場合は工程を分割し、前者を`CLI`または`Boundary`、後者だけを`LLM`へ分類する。LLMを採用してもschema検証、policy、状態変更、外部効果、保存、監査は`Boundary`から移さない。
- 分類が未完了、所有moduleが未確定、またはLLMの必須性／品質優位性を説明できない状態では、仕様確定、実装、state変更、外部操作へ進まない。追加調査または比較評価を行い、未確定境界を報告する。
- 受入条件と試験も区分ごとに分ける。`CLI`／`Boundary`は再現可能なcommand、機械可読出力、exit status、receiptで検証し、`LLM`は入力境界、出力schema、品質基準、失敗・拒否経路を検証する。LLMの自然言語報告を決定的工程の証跡にしない。
- 最終報告では、当初の分類と実装後の実経路を照合し、決定的にCLI化できた工程、残ったLLM必須工程、未解決境界を明示する。

## Sol-Orchestrated Bounded Luna Execution

- Sol owns the whole-system plan, canonical module and contract identification,
  design decisions, dependency ordering, delegation, monitoring, direct diff
  review, integration, and final validation. Delegation does not transfer
  Sol's final responsibility.
- Delegate a `bounded execution unit`, not merely a small number of lines. The
  unit must have closed responsibility, inputs, outputs, allowed file scope,
  and machine-checkable success criteria. Do not delegate an ambiguous problem,
  an unresolved source-of-truth question, or a cross-module design decision.
- Luna may receive only these task types:
  - `read-only evidence collection`: specify the exact question, target paths
    or commands, and an output limit; Luna returns concise facts and unknowns.
  - `implementation/verification`: Sol must first settle the design, scope,
    contract, and acceptance criteria before issuing the task.
- Every delegation packet must state: purpose and acceptance criteria; owning
  module and exact files; observed evidence and current behavior; exact allowed
  changes; forbidden changes; contracts and invariants; validation commands;
  and the expected return of changed files, diff summary, commands and results,
  and unresolved blockers.
- Luna reads only the specified `AGENTS.md` chain, target files, and their
  direct dependencies. Workspace-wide exploration and scope expansion are
  forbidden. If information is insufficient or contradictory, a design choice
  is required, another module or file is needed, or validation is impossible,
  Luna must not guess, use an alternate route, or expand scope; it stops and
  returns evidence to Sol.
- Luna's output is advisory. Completion requires Sol to review the actual diff,
  scope, canonical boundary, tests and results, and integration impact. Sol
  directly rechecks important facts when needed.
- Parallel delegation is allowed only when files, state, and contracts do not
  overlap and each task is independently verifiable. Shared contracts,
  generated artifacts, runtime state, or the same file require dependency-
  ordered serial execution.
- Keep delegation token-efficient: Luna returns concise evidence, diffs, and
  test results, not large source dumps or general discussion. Sol consolidates
  only necessary evidence and does not repeatedly delegate workspace-wide
  rediscovery. After failure, Sol redesigns the assumptions, decomposition, or
  route; it does not repeat the same ambiguous task.
- Even when included in the user's scope, Luna may not perform commit, push,
  PR, restart, install, delete, destructive, or other external mutation without
  an independent explicit packet issued after Sol has reviewed Luna's diff.

## Codex User Authorization / RenCrow No-Human-Gate

- Codexがrepository、runtime、host、外部systemへ変更を加えるには、ユーザーの明示指示を作業scopeの根拠にする。scope拡大や破壊的操作は新しい明示指示なしに行わない。
- このCodex実行権限をRenCrow製品へ移植しない。RenCrow runtimeは人の判断待ちを作らず、CORE正本、machine-readable policy、認証済みrequest scopeを同期評価して、直ちに実行、`rejected`、`blocked`を確定する。
- RenCrowのAgent、workflow、API、DBへ、人の返答で解除するstatus、grant、reference、queueを追加しない。利用者の発話は新しい目的・制約・事実を持つrequestであり、待機artifactへの判子ではない。
- このNo-Human-Gateは`User Decision GUI Requirement`を禁止しない。policyで決められない利用者固有の判断が機能上必要なら、判断材料と操作をGUIで提供する。その操作は待機中workflowへの承認印ではなく、COREが即時評価する新しい認証済みrequestとする。
- RenCrow内で案が`rejected`になった場合は、reject理由を証拠として、前提、分解、route、Tool、設計、必要なら思想まで再考した新revisionを作る。同案の言い換え、安全制約の弱体化、無限再試行は禁止する。

## Branch Policy

- ユーザーが明示的に指示しない限り、新しい Git ブランチを作成してはいけない。
- 作業は現在のブランチで継続する。

## Repository-local test runtime

- ローカルWindowsでRenCrow各repoのtestを実行するときは、各repoの引数なし
  `scripts/test-local.ps1`を正規入口にする。全repoの一括実行は
  `RenCrow_CORE/scripts/test-rencrow-system.ps1`を使う。
- testは実装内容を検証する工程であり、Push操作そのものの必須hookではない。同一内容で
  relevant checkがすでに成功している場合、Push時に同じtestを再実行しない。
- 一時clean worktreeは差分分離とCommit作成に使い、元の作業ツリーで検証済みの内容と
  `git diff`／hashが一致する場合、その一時worktreeでcold cacheのtestを重複実行しない。
  relevant fileが検証後に変わった場合、成功結果がない場合、またはRenが明示した場合だけ
  relevant checkを再実行する。
- test commandが設定したtimeoutへ達した場合、同じstepをtimeout延長だけで自動再実行しない。
  残留processを停止し、cache、network、security software、child processのどこで止まったかを
  先に診断する。Push時はtest未完了を明記し、Renの判断またはGitHub Actionsへ切り替える。
- Go repoのローカルWindows planは`go vet ./...`と`go build ./...`を使い、
  `.test.exe`を生成・実行する`go test`は含めない。Goの振る舞いtestは
  GitHub ActionsのUbuntu jobで実行する。
- runnerは`TEMP`、`TMP`、`TMPDIR`、`GOTMPDIR`、Go／Python／Nodeのcacheを
  各repo内の`Tmp/test-runtime/`へ向ける。
- testが子processを起動するときは親environmentを置換せずmergeする。
  Pythonは`{**os.environ, ...}`、Goは`append(os.Environ(), ...)`、
  Nodeは`{...process.env, ...}`を使う。
- system tempやuser profileのcacheへtest生成物を書かない。
- security softwareは有効なまま維持し、停止、除外設定、testのskip・弱体化を行わない。
- repo内`Tmp`でも実行fileがblockされた場合は、renameや繰り返し実行で通そうとせず、
  pathとerrorを記録してGitHub ActionsのUbuntu testへ切り替える。

## Repository Relationship

`RenCrow_CORE` is the main server and source repository for shared Viewer,
runtime, route, adapter, and user-facing behavior in this project.

`RenCrow_CMD` is the CLI/client/entrypoint for `RenCrow_CORE`.
It must not be treated as an independent product fork unless Ren explicitly says so.

When changing shared Viewer, CLI, runtime, route, adapter, or user-facing behavior:

1. Check whether the source of truth belongs in `RenCrow_CORE`.
2. Apply or port the change to `RenCrow_CORE` first when applicable.
3. Mirror or sync the corresponding change into `RenCrow_CMD` only after the upstream-side change is handled.
4. Do not leave behavior implemented only in `RenCrow_CMD` when it should exist in the upstream source.

If a change is intentionally `RenCrow_CMD`-only, state that reason clearly before implementation.

Cross-module input/output semantics and responsibility boundaries are canonical
in `RenCrow_CORE/docs/README.md` and the specifications listed there. Sibling
module documentation may refine module-internal implementation but must not
override the CORE canon. The CORE/RenCrow_LLM Chat boundary is defined in
`RenCrow_CORE/docs/04_アーキテクチャ概要.md`.

## Standard Runtime and OS Portability Rule

- `RenCrow_CORE/docs/04_アーキテクチャ概要.md`の「標準Go配布境界」を、
  Go primary runtime、外部system、三OS共通契約、CUDA用WSLの最上位正本とする。
- RenCrowは可能な限りnative Go binaryだけで動かし、Ubuntu、Windows、macOSで
  同じmodule-facing protocol、Config、health／readiness、error／unavailableを提供する。
- 標準profileの起動条件へPython、Node.js、Docker、WSL、外部database、queue、
  vector storeを追加しない。外部systemが不可避な場合は所有moduleの境界外へ隔離し、
  三OSで同等のcontractと失敗時挙動を提供する。
- WindowsのWSLは、明示的に選択したCUDA／GPU external computeだけに使う。
  CORE、module Gateway、database、news収集、storage、browser、一般sidecarをWSLへ置かない。
- WSL内の成功をWindows native runtimeの検証結果として扱わない。両者を別に検証する。
- Codexが標準構成の例外を実装する場合はユーザーがその変更を明示指示したときだけ有効とし、対象、理由、OS、影響、失敗時挙動、
  再評価条件を記録する。

## World Actor Rule

- The actors in the RenCrow world are authenticated users and CORE-managed
  Agents. Mio, Shiro, Kuro, and Midori are Agent identities.
- An LLM, model, provider, Agent Runtime, Execution Role, controller, or brain
  adapter is an implementation mechanism, not an actor and not an Agent
  identity.
- Production conversation, work, and gameplay must be attributable to a user or
  an actual CORE Agent. A test double must not claim Agent identity, Persona,
  memory, experience, or an Agent-owned E2E result.
- `RuleBasedBrain` and `DummyBrain` are valid for unit tests, integration tests,
  deterministic simulation, and local observer checks. Agent gameplay E2E must
  request every player decision from the corresponding CORE Agent.

## Runtime Routing Rule

Runtime requests from `RenCrow_CORE` must go through the corresponding
`RenCrow_XXX` module. Do not call model backends or tool backends directly from
the Viewer or CORE server. Codex may implement an exception only when the user
explicitly instructs that topology change; RenCrow runtime never asks for it.

Default routing:

- LLM: `RenCrow_CORE -> RenCrow LLM Gateway -> RenCrow LLM Runtime -> Backend -> Model`
- TTS: `RenCrow_CORE -> RenCrow_TTS -> TTS backend`
- STT: `RenCrow_CORE -> RenCrow_STT -> STT backend`
- Vision/camera analysis: `RenCrow_CORE -> RenCrow_Vision -> Wild backend -> RenCrow_Vision -> RenCrow_CORE`
- Image generation: `RenCrow_CORE -> RenCrow_Image -> ForgeNeo / Z-Image`

Module notes:

- `RenCrow_CMD` is a CLI operation surface, not an independent runtime fork.
- `RenCrow_Image` is the mandatory interface module for drawing and image generation.
  `RenCrow_CORE` must not call ForgeNeo, ComfyUI, or another image backend directly.
- `RenCrow_Vision` is the mandatory interface module for image and video recognition.
  `RenCrow_CORE` must not send raw image or video data directly to Wild,
  `RenCrow_LLM`, or another recognition backend. `RenCrow_Vision` owns the
  Wild request, media preprocessing, and result normalization.
- As a narrow exception, Mio, Shiro, Midori, and Kuro may use ImageGen through
  CodexExe as part of text generation. This exception does not permit a normal
  CORE image-generation route to bypass `RenCrow_Image`.

## Canonical Runtime Recovery Rule

- When the canonical runtime path is unavailable, first restore that exact path:
  verify its configuration, credentials, module process, network reachability,
  RenCrow LLM Runtime, Backend readiness, and logs.
- Do not create or start a direct-backend route, local substitute, fake server,
  test double, alternate model, or shortened module chain merely to make an E2E
  test pass.
- Codex may create a fallback or alternate topology only when the user explicitly
  instructs that specific change after the canonical-path failure and impact are
  reported. RenCrow runtime uses only fallbacks already defined by the CORE canon
  and deployment policy; otherwise it returns `blocked` without waiting for a person.
- If the canonical path still cannot run after safe in-scope recovery attempts,
  stop and report the exact failing boundary and evidence. Never describe an
  alternate-path result as canonical runtime or Agent-owned E2E success.

## UTF-8 and Path Handling

All source code, docs, config, JSON, and JSONL files in RenCrow should be treated
as UTF-8 text unless they are explicitly binary files.

When handling file names across Windows, Linux, and macOS:

- Treat file names as Unicode paths, not as locale-specific byte strings.
- Do not pass Japanese or other non-ASCII paths as hard-coded string literals
  through PowerShell or cmd when a script can discover them with filesystem APIs.
- Prefer path enumeration APIs such as Python `pathlib.Path.rglob()` or
  PowerShell `Get-ChildItem` objects, then operate on the returned path objects.
- On Windows, set UTF-8 process I/O for scripts when printing or parsing paths
  (`PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`, and PowerShell output encoding when
  needed).
- If a file name appears garbled, verify the actual filesystem Unicode name
  before renaming. Only rename when the real name contains replacement
  characters or clear mojibake and the intended UTF-8 name can be determined.
- Git octal-escaped path display is not filename corruption. Use local
  `git config core.quotepath false` for readable non-ASCII paths.
