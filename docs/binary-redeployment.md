# Binary redeployment

## 目的

`ecosystem.yaml`のpinと、hostで実際に動いているbinaryの一致を検証し、ズレたbinaryを
pinへ戻す。[Binary placement](binary-placement.md)が「どのhostへ何を置くか」を定めるのに対し、
この文書は「置かれた物が正しいrevisionか」を定める。

## 背景

manifestの検証は`scripts/validate_ecosystem.py`が担うが、これはmanifestとsource treeの
一致しか見ない。**manifestと配置済みbinaryの一致は、どのcheckも見ていなかった。**

この穴は実害を出した。RenCrow_TTSは2026-08-08の`5754145`で読み辞書の承認契約を
`approved`から`active`へ変更し、`configs/pronunciations.json`も同時に書き換えた。しかし
配置済みbinaryは2026-08-03の`ff3e0e7`のままだった。旧binaryは`active`を知らず、
辞書loaderの`DisallowUnknownFields()`が起動ごとにconfigを拒否し、
`rencrow-tts.service`は13日間で225,468回再起動した。

source側は正しく、CIも通っていた。欠けていたのはdeployだけであり、
それを検出する手段が無かった。

## 責務境界

この仕組みはoperatorが明示的に起動する検証・再配置toolであり、常時processを監視して
自動修復するcontrol planeではない。[Binary placement](binary-placement.md)の
「EcoSystemはruntime control planeにならない」という境界を保つため、次を守る。

- timerやdaemonから自動実行しない。実行はoperatorのcommand invocationに限る。
- 既定動作は報告のみとし、host状態の変更は`--apply`の明示を必要とする。
- 任意のunit名やcommandを受け取らない。対象はmanifestのcomponentへ解決できたunitに限る。
- 所有不明のlistenerやprocessを停止しない。

CORE自身のcapability適用に伴う置換は、binary-placementの
「Capability Apply supervisor（採用済み・未実装）」が所有する別契約である。
そちらはCORE配布物内のsupervisor workerが固定Task`rencrow-core`だけを置換し、
apply APIのreceipt確定を前提とする。この文書のtoolはoperator起点でmodule横断の
pin整合を扱うものであり、supervisor workerを代替しない。

## 導出契約

対応表を人手で維持しない。次の3段で全て導出する。

| 段 | 入力 | 得るもの |
| --- | --- | --- |
| 1 | systemd unitの`ExecStart` | 実際に動いているbinaryのpath |
| 2 | binary内のGo build stamp | main package、module、`vcs.revision`、`vcs.modified` |
| 3 | moduleとcomponentの`repository`の前方一致 | manifest component、すなわちpin |

段2はGoがbuild時に自動で埋め込むため、moduleへの改修を必要としない。

段3はmoduleがrepository直下に無い場合がある（RenCrow_TTSはmoduleが`gateway/`配下）ため
前方一致とし、nested moduleが親repositoryへ誤解決しないよう最長一致を採る。

同一binaryを複数unitが共有する場合（`rencrow-trade`は`rencrow-trade.service`と
`rencrow-trade-learning.service`が共有）、それらを1件へ束ねる。

## 判定

| status | 条件 | 意味 |
| --- | --- | --- |
| `MATCH` | `vcs.revision` == pin かつ `vcs.modified` == false | 検証済み一致 |
| `MISMATCH` | `vcs.revision` != pin | pinとのズレ。何commit前かを併記する |
| `DIRTY` | revisionはpinと同一だが`vcs.modified` == true | SHAは合うが未コミット差分入りでbuildされており、SHAで内容を保証できない |
| `UNSTAMPED` | `vcs.revision`が無い | driftを測定できない |
| `UNMAPPED` | Go binaryでない、またはmanifestに対応componentが無い | 対象外 |

`DIRTY`と`UNSTAMPED`は「壊れている」ではなく「**SHAでは検証できない**」を表す。
検証可能性と正しさを同じ状態へ丸めない。

## 再ビルド契約

再配置は必ずpinのlocal cloneからbuildする。稼働中の作業treeからbuildしない。

```
git clone --local --no-checkout <module> <tmp>/src
git -C <tmp>/src checkout --detach <pin>
go build -o <staged> <target>
```

linked worktree（`git worktree add`）を使ってはならない。**worktreeは`.git`がfileになり、
Goはそれを見るとVCS情報を黙って落とす。** `-buildvcs=true`を明示してもerrorにならず、
stampの無いbinaryが出来上がる。それを配置するとdriftを解消したかどうかを永久に
検証できなくなる。local cloneは実体のある`.git` directoryを持つためstampが機能し、
同時にcheckoutがcleanであることも保証される。

buildしたbinaryは、**hostへ触れる前に**検証する。

- `vcs.revision`がpinと一致すること
- `vcs.modified`がfalseであること

満たさない場合はhost状態を一切変更せず中止する。driftを解消しない再buildの配置は、
何もしないより悪い。

## 配置と再起動契約

検証を通過した後、次の順で行う。

1. 旧binaryを`~/.rencrow/backups/<name>.replaced-<sha>`へ退避する。
2. 入れ替え前に各unitの`ActiveState`を記録する。
3. 全unitを停止し、binaryを差し替える。
4. **入れ替え前にactiveだったunitだけ**を起動する。
5. manifestのreadiness契約を満たすまで確認する。
6. 異常なら旧binaryへ戻し、再度起動して復帰を確認する。

### 停止中unitを起動しない

binaryを共有するunitには、timerを持たない`Type=oneshot`が混ざる。
`rencrow-trade-learning.service`はoffline学習ジョブ、`rencrow-resilience.service`は
reconcileであり、再配置の巻き添えで起動すると誰も依頼していない処理が走る。
停止していたunitは停止したまま据え置く。

### manifest-owned readiness

`Type=simple`はprocessをforkした時点で起動成功を返す。configを拒否して即座に終了する
binaryも「起動した」ように見える。**TTSが13日間「配置済み」であり続けたのはこの性質による。**

各 production unit の契約は`ecosystem.yaml`の
`components.<id>.deployment.user_systemd`が正本である。契約の`unit`は実際の
systemd unitと完全一致し、同じunitを複数componentで宣言できない。

- `kind: http_json`は`url`へGETを行い、契約の`timeout_seconds`（1--600秒）内に
  HTTP 2xx、JSON、指定されたdotted `expect.path`とscalar `expect.equals`の一致を要求する。
- `kind: oneshot`は`ActiveState=inactive`かつ`SubState=dead`、`Result=success`、
  `ExecMainStatus=0`を要求する。timeoutはcheckerの固定上限600秒である。
- どちらもsystemdの`failed`または`auto-restart`を即時失敗とする。process生存だけでは成功にしない。
- 稼働中unitの契約がmanifestに無い場合は、build、backup、stop、copyを行わずfail closedする。

### rollback

readiness確認に失敗した場合、退避したbinaryへ戻し、同じ稼働unitへ同じ契約を適用して
復帰を確認する。復帰しない場合は退避先のpathを明示して報告する。

### 配置receipt

dry-runを除く再配置試行は、既定で
`~/.rencrow/receipts/binary-redeployment.jsonl`へ1試行1行のUTF-8 JSONLを残す。
各recordはschema version、receipt ID、UTC開始・終了時刻、component、binary、配置前後の
revision、再起動対象unit、最終phase、成功／失敗、backup path、readiness失敗unit、
rollback結果を持つ。receipt logを事前に作成・fsyncできない場合は、build、backup、stop、
copyを始めずfail closedする。dry-runはreceiptを作らない。

## Guard

| 対象 | 既定 | 理由 |
| --- | --- | --- |
| `core` | `--only core`で明示した時だけ再配置する | 再起動でViewer、Agent、Chat、IdleChat、Memoryが同時に落ちる |
| `UNSTAMPED` | `--only <component>`で明示した時だけ再build対象にする | 検出された不一致ではなく、検証可能にするための判断 |

## 運用

```bash
# 報告のみ
python3 scripts/check_deployed_binaries.py ecosystem.yaml

# 実行計画の確認
python3 scripts/check_deployed_binaries.py ecosystem.yaml --apply --dry-run

# 再配置
python3 scripts/check_deployed_binaries.py ecosystem.yaml --apply --only vision,stt

# COREもmanifestのreadiness timeout（300秒）で確認する
python3 scripts/check_deployed_binaries.py ecosystem.yaml --apply --only core

# unitを変更せず現在のreadinessだけを確認する
python3 scripts/check_deployed_binaries.py ecosystem.yaml --check-readiness
```

| option | 既定 | 意味 |
| --- | --- | --- |
| `--json` | off | 機械可読出力 |
| `--apply` | off | 再build・再配置を実行する |
| `--check-readiness` | off | unitを変更せずmanifest readinessを確認する |
| `--dry-run` | off | `--apply`の計画だけを表示する |
| `--only` | 空 | 対象componentをカンマ区切りで限定する |
| `--receipt-log` | `~/.rencrow/receipts/binary-redeployment.jsonl` | 再配置receiptのJSONL path |
| `--prefix` | `rencrow` | 対象とするsystemd unitの接頭辞 |
| `--workspace` | manifestのdirectory | catalog root |

| exit code | 意味 |
| --- | --- |
| 0 | `MATCH`／対象外の`UNMAPPED`のみ、または`--apply`が全件成功 |
| 1 | `MISMATCH`、`DIRTY`、`UNSTAMPED`を検出、または`--apply`に失敗があった |
| 2 | manifestが無い、対象unitが無い |

pinを更新したら配置も追随させる。pinだけを進めるとMATCHだったbinaryがMISMATCHへ変わる。

## 既知の限界

- **`vcs.modified`はbuild時点の作業treeの状態であり、現在の状態ではない。**
  `DIRTY`はSHAで内容を保証できないことのみを示し、差分の中身は分からない。
- **Go以外のbinaryは対象外。** shell script、docker、llama-server等は`UNMAPPED`として
  素通りする。これらのversion管理は別の手段を必要とする。
- **hostの`go`に依存する。** buildだけでなくstampの読み取りにも`go version -m`を使う。

## 未実装

- Linux user systemd以外のhost adapter。Windows service、launchdは未対応。
- pinへの追随を促す通知。現状はoperatorがcommandを実行した時にだけ分かる。
