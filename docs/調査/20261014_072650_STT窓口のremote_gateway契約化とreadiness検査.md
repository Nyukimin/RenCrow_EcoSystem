# STT窓口のremote_gateway契約化とreadiness検査（2026-10-14）

## 概要

STT窓口をmacOS音声hostへ移した後、COREホストの`check_deployed_binaries.py --check-readiness`が
毎回失敗していた。停止した旧unitを必須として検査し続けることが原因だった。検査を外さず、
「窓口は音声hostにあり、COREホストでは転送unitが同じloopback portを提供する」配置を
manifestで表し、その配置でreadinessを確認できるようにした。前回の記録
（[20261013_220200](20261013_220200_STT窓口の音声ホスト移設とcatalog反映.md)）の
選択肢(i)(停止unitを対象から外す)でも(ii)(文書化のみ)でもない、第3の方式を採った。
ホスト番号・IP・user名・実pathは公開repoのため記載しない。

## 発生条件

- COREホストの`rencrow-stt.service`はstop／disableで、unit fileとbinaryは残置。
  同じloopback portは`rencrow-stt-tunnel.service`（`ssh -L`、音声hostへ転送）が保持する。
- `components.stt.deployment.user_systemd`は`rencrow-stt.service`を`http_json`契約で宣言していた。

## 手順

1. `check_deployed_binaries.py`の`collect()`／`check_declared_readiness()`／`wait_for_readiness()`、
   `validate_ecosystem.py`の契約検証、既存testを読んだ。
2. 設計案を作り、実装前にアドバイザ（Fable）へ読み取り専用で相談した。
3. testを先に書いて失敗を確認し（Red）、validatorとcheckerを実装して通した（Green）。

## 事実

- readinessの検査対象は「Go binaryからcomponentへ結び付いたunit」に限られる。転送unitは
  `ssh`を実行するため`UNMAPPED`（componentなし）で、契約があっても検査されない。
  契約unitだけを転送unitへ付け替えると、残置された旧unitが契約不足でNGになる。
- 旧binaryを`go_binaries`から外すだけでは足りない。旧unitが列挙され続け、`go_binary_pin()`が
  source pinへfallbackするため、source pinを進めた時点で`MISMATCH`になる。
- 転送unitは複数が同じ`ssh`を共有し、従来は1件の`UNMAPPED`行に束ねられる。
  束ねたままでは宣言済みの転送unitの行に別の転送unitが混ざる。
- `ssh -L`は既定でportのbind失敗を警告にとどめて接続を続ける。旧local gatewayがportを保持していると、
  転送が失敗していてもURLがreadyに見える。
- drift通知の集合は`MISMATCH`／`DIRTY`／`UNSTAMPED`の行だけから作られる。`MATCH`だった旧binaryの行が
  消えても集合は変わらない。

## 結論

- manifest: `http_json`契約に任意キー`remote_gateway: {"replaces": "<退役したlocal unit>"}`を追加した。
  `components.stt`は契約unitを`rencrow-stt-tunnel.service`（URLは従来どおり）へ、`replaces`を
  `rencrow-stt.service`とし、`go_binaries`から`rencrow-stt`（gateway）だけを削除した。COREホストで動く
  owner verifier（`rencrow-stt-verify`）と`files`（`stt.json`）は検査側の配備物として残す。
- checker: `remote_gateway`の転送unitはmanifestでcomponentへ結び付けた`UNMAPPED`行にし、
  binaryのdedupeに入れない。`replaces`のunitは行を作らない（drift・readiness・再配置の対象外）。
  `--check-readiness`は通常の`http_json`検査（転送unitがactiveかつURLがready）に加え、退役unitが
  稼働中または状態不明ならNGにする。
- validator: `remote_gateway`は`http_json`契約のみ、キーは`replaces`のみ、unit形式、自unit不可、
  全component横断で一意、契約unitとの重複不可（宣言順を問わない）。不正はManifestError。
- 旧binaryの扱い: 追跡しない残置物（ロールバック用）。pin比較・通知・再配置の対象にしない。理由は
  現在の配備物ではなく、ここをpinに結び付けておくと、実際に動いている窓口と無関係なdriftを通知するため。
- 不採用: 旧unitのunit file削除を前提に`replaces`を省く案（ホスト操作が前提になり、ロールバック手段を
  先に失う。unit fileを削除した場合は`replaces`を外せる）。`kind`の追加（検査意味論は`http_json`と同一）。
  deployment直下の`retired_units`（契約と二重管理になる）。移設先LaunchDaemonの宣言（検査主体が無い）。
- 未確認: COREホストでの実測（配備担当の完了後に別途実施）。転送unit側の`ExitOnForwardFailure=yes`の有無。

## TTS窓口への適用

TTS窓口もSTTと同じ形（COREホストの`rencrow-tts.service`を停止し、転送unit
`rencrow-tts-gateway-tunnel.service`が`127.0.0.1:7870`を提供する）へ切り替えた後に、同じ
`remote_gateway`契約を適用した。差分は`components.tts`だけである（契約unitの付け替えと
`replaces: rencrow-tts.service`、`go_binaries`から`rencrow-tts`の削除。`rencrow-tts-verify`と
`files`は残す）。validatorとcheckerは変更しない。旧転送unit（別portの音声engine向け）は
manifestに現れない。

## Failure Knowledge

- Failure: 窓口を別hostへ移した結果、`--check-readiness`が常時exit 1になった（前回記録の続報）。
- Problem: 契約が「窓口はこのhostのGo binaryのunitである」前提で、転送unit構成を表せなかった。
- Cause: readiness契約の対応付けがGo build stampに依存し、binaryを持たない転送unitに契約を持てない。
  旧unitを残置すると、binaryとunitがpin比較・readinessの対象に残り続ける。
- Lesson: 窓口の配置を変えるときは、契約が結び付く先（unit／binary／pin）を同じ変更で付け替え、
  退役したunitとbinaryの扱いを明示する。
- Invariant: `remote_gateway`の退役unitは契約unitと重複せず、一意で、検査対象にもpin比較にも入らない。
  退役unitが稼働中なら`--check-readiness`は成功しない。
- Enforcement: `validate_ecosystem.py`（`_validate_remote_gateway`と重複検査）、
  `check_deployed_binaries.py`（`remote_gateway_contracts`、`collect()`、`_retired_units_idle`）。
- Tests: `tests/test_validate_ecosystem.py`（`test_remote_gateway_*`、契約期待値）、
  `tests/test_check_deployed_binaries.py`（`RemoteGatewayReadinessTest`。原因の再現として、実manifestで
  停止した旧unitを必須にしないことを確認する）。

## 関連ファイル

- `ecosystem.yaml`（`components.stt.deployment`）
- `scripts/check_deployed_binaries.py`、`scripts/validate_ecosystem.py`
- `tests/test_check_deployed_binaries.py`、`tests/test_validate_ecosystem.py`
- `docs/binary-redeployment.md`（`remote_gateway`、既知の限界）、`docs/runtime-layers.md`、`docs/binary-placement.md`
