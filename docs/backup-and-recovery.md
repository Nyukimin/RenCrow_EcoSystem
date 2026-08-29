# Backup and Recovery

本書は、RenCrow全体のbackup分類、owner境界、分散host間transport、横断受入条件の正本である。
module内部のdata schema、export/import実装、retentionは各owner repositoryが所有し、本書へ複製しない。

## 目的と二つの成果物

通常backupは同一installationの事故復旧とRPO/RTOを目的とし、世代snapshotを
`/srv/rencrow/backup/snapshots`へ保存する。Migration Artifactは別machineへの再構成を目的とし、
ownerが発行したConfigとStateを`/srv/rencrow/backup/recovery`の単一`uncompressed-tar`へ格納する。
一方の成功receiptを他方の成功証拠として代用しない。同じowner snapshot primitiveを内部利用する場合も、
storage policy、retention、restore acceptance、receipt contractを分離する。

完成Migration ArtifactはGit管理外とし、regular、非symlink、Unixでは`0600`、親directoryはowner管理とする。
secret実値を含み得るが暗号化を必須にせず、外部HDDのowner-only境界、ACL、credential rotation、監査で保護する。

## Owner分類

| Owner | State | Migration対象 |
| --- | --- | --- |
| RenCrow_CORE | durable | Memory、Conversation、Knowledge、CORE所有DB・registry |
| RenCrow_TTS | durable | ownerが採用した発音辞書。共通DBを持たないことと、owner固有fileがdurableであることを区別する |
| RenCrow_Image | durable | 採用済み生成PNGとowner manifest |
| RenCrow_GAMES | durable | Replay、world/session export、Leaderboard。0件でも有効な空exportを発行する |
| RenCrow_TRADE | durable | Source、Dataset、Learning、Portfolio、Ledger。実装未達でも分類から除外しない |
| RenCrow_LLM | state:none | Gateway/RuntimeはConfigとartifact identityから再構成し、model weight/cacheを含めない |
| RenCrow_STT | state:none | 現時点では永続辞書・学習状態を持たず、一時音声/cacheを含めない |
| RenCrow_Vision | state:none | 一時mediaと解析cacheを含めない |
| RenCrow_PORTAL | state:none | UI/proxyはsourceとConfigから再構成する |
| RenCrow_CMD、RenCrow_Tools | state:none | CLI/tool sourceはGit、再取得可能な生成物は正本にしない |

将来ownerが再生成不能なstateを追加する場合、保存機能と同じImplementation Unitでdurable manifest、
owner export/restore hook、retention、通常backup、isolated restore testを追加する。dataがまだ0件でも
owner分類を`none`へ落とさない。

## Owner contract

Workspaceはlive DB path、table、schema、writer停止方法を知らない。各ownerがactive Configから正本を解決し、
application-consistent packageとbounded receiptを発行する。必要operationは`state_describe`、`state_export`、
`state_validate_restore`、`state_import:dry-run`である。production restoreに限り、認証済みrequestとpolicyの下で
`state_import:apply`と`state_import:rollback`を使用する。

owner receiptはowner、operation、request ID、state class、schema revision、consistency mode、logical artifact ID、
size、SHA-256、record count、failure boundaryだけを返す。secret、absolute source path、state本文、完全なcommand lineを
返さない。live file copy、WAL/SHMの単独copy、opaque通常backupをowner exportとして扱わない。

## Local and distributed acquisition

Workspace orchestration Configはownerごとに次のtransportだけを許可する。

- `local_exec`: 同一hostのallowlist済みowner executableを固定引数`migration-hook`で呼び、最大64 KiBのstrict JSONをstdin/stdoutで交換する。
- `owner_operations_api`: 別hostの既存owner Gatewayが所有する認証済みoperations routeを使う。Configはendpointと`credential_reference`だけを持ち、token実値、任意header、任意command、owner DB pathを持たない。

remote exportはowner host上でlocal hookと同じdomain serviceを使って整合packageを作り、receiptでhashとsizeを固定してから
bounded streamとして転送する。Workspaceは受信中と受信後にsize/hashを検査し、不一致・切断・再利用をfail closedにする。
restore validationはisolated packageをownerの認証済みrouteへ提示し、owner receiptを得る。SSH shell、network share、
remote filesystem path、公開health、attestation単体をState export/importの正規経路にしない。

read-only runtime attestationはartifact/service/config/listener identity確認に利用できるが、State内容の整合性、export認可、
restore可能性の代用にはならない。operations routeはowner認証、purpose/scope、request ID、同時実行上限、size/time上限、
one-shot package lifecycleを強制する。

## Secrets and Config

portable ConfigはWorkspaceへ、host-bound Configはtarget overlayへ、secret値はGit外のowner-only Migration Artifactまたは
別のsecret recovery境界へ置く。orchestration Configは`credential_reference`のみを保持し、credential本文をArtifact、
receipt、log、Viewer、repositoryへ複製しない。model/backendはID、revision、checksum、capabilityだけを保存し、weightや
CUDA runtimeをMigration Artifactへ含めない。

## Failure boundaries

- `owner_hook_unavailable`: owner executableまたはoperations API入口がない
- `authentication_unavailable`: credential referenceまたは認証scopeがない
- `policy_blocked`: owner policyが操作を拒否した
- `state_export_failed`: 整合点またはpackage生成が失敗した
- `artifact_integrity_failed`: size/hash/schema/tar/pathが不一致
- `artifact_storage_prerequisite_absent`: 外部HDD、mount、permission、capacityが不足した
- `restore_validation_failed`: isolated restoreをownerが拒否した
- `canonical_route_unavailable`: 正規owner routeへ到達できない

fixture、SSH、直接copy、別backend、古いreceiptで境界を越えない。TRADE実装を作業対象外にしても、全体結果では
`owner_hook_unavailable`として残し、Workspace production backupをall clearにしない。

## Check Plan and terminal evidence

実行前にowner、phase、consumer、failure actionを持つ固定Check Planをcanonical JSONとhashで確定する。高コスト、空data、
remote host、未実装を理由にrequired ownerを除外しない。終端証拠は次である。

```text
canonical source -> owner -> authentication/policy -> consistent state export
  -> verified transfer -> external-HDD uncompressed tar -> isolated restore
  -> owner restore validation -> bounded receipt chain
```

source test、health、listener、artifact existence、generic tar inspect、通常backup成功だけでは完了しない。ownerごとのTDD、
正規E2E、Push、pinned build/deploy、必要なservice restart、配備後同一checkを閉じた後に全system checkを再composeする。

