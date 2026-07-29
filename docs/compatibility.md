# Compatibility and ecosystem releases

## Manifest semantics

`ecosystem.yaml` は「その ecosystem release で統合確認した component の
組み合わせ」を表します。各 module の version を同じ番号に揃えるものでは
ありません。

初期値:

- ecosystem release: `development`
- compatibility status: `unpinned`
- component version: `unpinned`

この状態は repository 関係の定義だけが存在し、互換性をまだ保証しないことを
明示します。

## Release flow

1. module repo が固有 test を通し、immutable tag と artifact を公開する。
2. `ecosystem.yaml` の対象 component を実在 tag に固定する。
3. required CORE flow と選択 optional capability の統合試験を実行する。
4. command、環境、結果、未確認点を verification record に残す。
5. compatibility status を `verified` に変更する。
6. EcoSystem に独立した semantic version tag を付ける。

例: STT だけが更新された場合、STT module を release して CORE 接続試験を行い、
manifest の STT version を更新してから ecosystem patch release を作ります。

## Minimum acceptance

- manifest に記載した repository と tag が実在する。
- artifact の checksum が一致する。
- `runtime.primary`のartifact、implementation、statusがmodule releaseと一致する。
- required companionがあるcomponentは、bundled／externalの境界と接続確認結果を記録する。
- CORE が clean environment で起動し health check を通る。
- required user flow を最低 1 回 end-to-end で確認する。
- optional component は「install したもの」ごとに接続・失敗時表示を確認する。
- secret、runtime state、生成物を release source に含めない。
- rollback 先となる直前の verified manifest を保持する。

health success だけで音声再生、認識、画像解析、game bridge などの利用可能性を
主張しません。各 capability は実際の入出力まで確認します。

## RenCrow_GAMES acceptance

- COREのAgent／LLMから`POST /viewer/games/launch`を実行し、
  GAMES Observerがsessionを起動する。
- GAMESのturn observationが`/viewer/games/decision`を通ってRenCrow_LLMの
  `BrainDecision`になり、GAMES executorが検証後に実行する。
- `/viewer/games/observer`経由でユーザーが実行中の盤面、判断、結果を確認できる。
- `/viewer/games/result`がReplayと相関できるcandidate eventを記録する。
- CORE停止時にGAMESが本番LLMへ直接fallbackせず、world stateを壊さず停止または
  明示したdegraded modeへ移る。

## RenCrow_LLM acceptance

RenCrow_LLMを含む組み合わせでは、一般的なminimum acceptanceに加えて次を確認します。

- client／COREがphysical target、Node、Backend portへ直結していない。
- Agent -> Execution Role -> Inference Targetの3層が維持される。
- Mio／Chat、Shiro／ChatWorker・Worker、Midori／Wild、Kuro／Heavyが意図したtargetへ解決される。
- Role profileがExecution Roleに付随する技術設定であり、独立したAgent層になっていない。
- clientがAgentだけを選び、COREがRole、RenCrow_LLMがTargetを選ぶ責務境界が維持される。
- execution aliasをopaqueなAgent／Role binding contractとして扱い、Agent ID、
  Role ID、Model名へ誤って固定していない。
- Host Node導入後はGatewayとNodeのversion、status schema、認証、Backend contractが一致する。
- Node liveness、Backend readiness、Model readiness、実生成を別checkpointとして確認する。
- Heavy通常推論がside effectなし／read-onlyで、full-access Codex Toolと別監査経路になっている。
- local target停止時にexternal providerへ、Agent Runtime停止時に別Agentへ無言fallbackしない。
- external provider利用時にprovider、Model、課金区分、usage、外部送信許可を追跡できる。
- 運用status／logで`agent_id`、`execution_role`、`execution_alias`、
  `role_profile_revision`、`target_id`、`provider`、`model`を区別でき、取得不能値を
  推測で埋めていない。
- 未知Agent、既知Agentの未対応Role、有効binding先の停止を
  `UNKNOWN_AGENT`、`UNSUPPORTED_ROLE`、`TARGET_UNAVAILABLE`として区別できる。
- Target変更時にModel／tokenizer／chat template／context prefixの互換性を確認し、
  非互換session／KVを再利用せず、直前の検証済みprofile revisionへrollbackできる。

配置規則は[Binary placement](binary-placement.md)、詳細contractはRenCrow_LLMの
`docs/10_Gateway_Node_Target責務仕様.md`を参照してください。

Target mappingを変更したverification recordには、少なくともCORE／LLM module version、
Agent、Execution Role、execution alias、old/new Role profile revision、Target ID、
provider、Model、外部送信／課金区分、E2E結果、rollback先を記録します。secret、credential、
物理Model path、不要なBackend URLは記録しません。EcoSystem manifestは検証済みmodule
releaseの組み合わせを固定し、runtimeのRole profileそのものの正本にはしません。

## PORTAL and CORE acceptance

PORTALを含む組み合わせでは、一般的なminimum acceptanceに加えて次を確認します。

- `IdleChat`のwrite拒否と、`Chat`の明示allowlistを確認する。
- recipient切替通知と、実際のmessage `to`が一致することを確認する。
- TTSのaudio owner取得、SSE audio、音声取得、browser再生、playback ACKを
  別々のcheckpointとして確認する。
- STTのinput owner取得、WebSocket upgrade、音声送信、STT target接続、最終認識を
  別々のcheckpointとして確認する。
- TTS／STT target停止時に失敗表示とowner解放を確認する。
- Debug／admin、cross-origin control、設定外TTS audio hostが拒否されることを確認する。

詳細な接続契約と確認項目は[PORTAL–CORE contract](portal-core-contract.md)を参照してください。

## ASSISTANT acceptance

plannedのASSISTANTをreleaseへ含める段階では、一般的なminimum acceptanceに加えて
次を確認します。

- 生活Routineが指定時刻・条件で一度だけ発火し、重複deliveryを起こさない。
- acknowledgement、snooze、missed、retry、別端末への切替を追跡できる。
- personal data、`family:shared`、別利用者のprivate dataが権限どおりに分離される。
- COREへのTask昇格で利用者scopeと相関IDが維持され、結果が元のdeliveryへ戻る。
- CORE停止時にAgent処理をdegradedとし、決定論的Routineとcache済み情報の状態を区別する。
- 実際のDevice clientでPUSH、表示または発話、利用者応答までend-to-endで確認する。

詳細な境界は[ASSISTANT boundary](assistant-boundary.md)を参照してください。
module固有の仕様と実装状態は、実装repositoryの作成後にその`docs/`を正本とします。

## Interaction profile acceptance

現行のPORTALとCMDを同じ組み合わせへ含める場合は、追加で次を確認します。

- Chatのrecipient、利用者scope、request／response相関がsurface間で一致する。
- IdleChatのevent、開始／停止、拒否、degradedの意味がsurface間で矛盾しない。
- profile、mode、認証scope、device capabilityによる拒否が実際に機能する。
- 再接続と再送でmessage、Task、PUSH、acknowledgementが二重処理されない。
- CMDの`cmd-chat`、`cmd-idlechat`、`cmd-diagnostics`、`cmd-control`が、それぞれ
  CORE Public APIのallowlist内だけを利用する。
- ASSISTANT実装時は、PORTAL停止中もRoutineとPUSHが動き、CORE停止時はAgent処理だけを
  degradedとして区別する。

共通能力と固有差は[Interaction surfaces](interaction-surfaces.md)を参照してください。
