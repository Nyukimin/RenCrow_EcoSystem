# WORLD redesign R00–R04 integration record (2026-10-15)

This is cross-module integration evidence, not a WORLD/CORE/PORTAL contract or an Atlas lifecycle state. Owner contracts remain in their module repositories. R04 source commits have been pushed, but no R04 production deploy has been made.

| Work package | Current result | Remaining boundary |
| --- | --- | --- |
| R00 | CORE `38f87d02b3abc00f1c6baf335fc5c518f2c9a438`, PORTAL `1a4f2870731390435cfa47aa733d40215bf71b06` were the source baselines; the existing CORE runtime remained healthy after the Atlas remediation. | `ecosystem.yaml` still pins CORE `83f07bf11c2514bca4ddba774d6e7431eda58b4a` and PORTAL `cc7b418fe82f7ae465cd0cef7682cec9e801a28d`; these pins predate the pushed R04 commits. Do not claim a verified pin. |
| Atlas prerequisite | Five invalid Step18 retry freezes were explicitly cancelled through the authenticated CORE owner route. Active freezes and acquired leases were both zero after restart. The underlying five items remain `BLOCKED`; cancellation did not repair their failed work. | No new implementation lease or `DONE` claim is inferred. |
| R01 | Existing CORE `mio` AgentProfile and the distinction between Run-less queued Task creation and `CreateAndStartRun` were confirmed. | WorkSet V2 contract tests and the full identity/life mapping are not yet complete. |
| R02/R03 | The required house Blender file, nine-actor assets, and reference illustrations were not available in this workspace. No coordinates or final renderer were invented. | ArtGate and two-view visual quality acceptance are blocked on real assets. |
| R04 | Mock-only CORE reader/bridge and a default-off PORTAL page were source-implemented. The loopback fixture → PORTAL proxy → one WorldStore → both simulated DOM views passed, including 20 view switches without extra requests. | Production CORE route, real WORLD state, native-browser visual acceptance, and three-OS acceptance are not claimed. |

## R04 evidence

- CORE implementation: `RenCrow_CORE/internal/adapter/viewer/world_poc.go`, its tests, and `RenCrow_CORE/cmd/rencrow-world-poc-fixture/`. The fixture binds numeric loopback IPs only and is not part of the normal CORE runtime.
- PORTAL implementation: `RenCrow_PORTAL/internal/portal/server.go`, `internal/portal/web/world-poc.*`, and `internal/portal/webtest/world-poc*.test.js`. `enable_world_poc` defaults to false. Only explicit GET snapshot/stream paths proxy to the fixture.
- Pushed source commits: CORE `855b1f0a15faa0ce22f262b5300f2e84949a8df9` (Atlas remediation and R04 bridge/fixture), PORTAL `45a70ec77c6853b1959570fe91dfa1260afee90f` (R04 proxy and shared two-view store). Neither commit is a WORLD production acceptance receipt.
- The last local fixture binary SHA-256 was `48d124f44cda843a16758b743365ae38273291cb69964466bbede9c5599341b6`; the last PORTAL test binary SHA-256 was `1e14fb7eb484251e90aca8a48fec8fdb33ed11bbe600f549b1cfcf95f6ecb1e2`. Neither was installed as a production service.
- Loopback HTTP returned snapshot `world_revision=1`, `actor_id=mio`, `position=null`, `spatial_revision=unverified`; stream `after_revision=0` returned `snapshot` then `caught_up`, and `after_revision=1` returned only `caught_up`. POST snapshot returned 405; an unknown PoC route returned 404.
- `RENCROW_WORLD_POC_INTEGRATION_BASE=http://127.0.0.1:18795 node --test internal/portal/webtest/world-poc-integration.test.js` passed against the running fixture and PORTAL. Both DOM projections showed the actual HTTP revision and Mio. The test uses a fake DOM and HTTP-backed EventSource adapter, not a native browser.
- Independent checks passed: CORE `go test ./...` (251 passing packages, zero failures), focused `go vet`/build/format checks; PORTAL `go test ./...` (6 passing packages), `go vet ./...`, Node WorldStore tests (18), and `git diff --check`. Astra's final read-only review found no remaining source-level blocking issue after the BFCache pause/resume correction.
- Agent assignments used `gpt-6-luna` (`xhigh`) for the bounded CORE, PORTAL, fixture, and integration-test edits, and `gpt-6-astra` (`high`) for read-only reviews. The primary session's actual model is not attested by the available CLI; `gpt-6.1-sol` was not exposed as an agent override. Codex CLI reported version `0.162.1`. No model substitution is claimed to be equivalent.

## Operational boundary and next unit

The Atlas remediation, unlike R04, was deployed to the existing CORE runtime. Its active binary SHA-256 was `08ddd13de07d0fbe4de97251cebd92970dd0c26ea6f8cfa27c16ee756e5857fa` after restart; evidence remains under `RenCrow_CORE/Tmp/test-runtime/atlas-freeze-deploy-guard-20261015T154335Z`. This binary predates the combined R04 source commit and must not be identified as that commit's build. The cancellation is a withdrawal of invalid retries, not a successful Step18 retry.

R04's mock PoC is locally accepted and its source is pushed, but it does not satisfy Atlas's full specification-to-deploy lifecycle. Do not use this record to release the Atlas WIP gate or assert production acceptance. The next dependency is R05's independent Go WORLD kernel setup, after reconciling the R04 lifecycle and catalog module declaration; R03 remains independently blocked on art assets.

On 2026-10-15, `Nyukimin/RenCrow_WORLD` was created as an empty public GitHub repository and cloned at `RenCrow_WORLD/`. Its local unborn HEAD is `main`, matching GitHub's default branch. No source, commit, release, or EcoSystem source pin exists yet; this repository creation alone does not start or complete R05.
