# Compatibility and ecosystem releases

## Manifest semantics

`ecosystem.yaml` は「その ecosystem release で統合確認した component と
external runtime profileの組み合わせ」を表します。各 module の version を同じ番号に
揃えるものではありません。

現在値:

- ecosystem release: `development`
- compatibility status: `source-pinned`
- 実装済みcomponent version: 40桁のGit commit SHA
- 未実装component version: `planned`

`source-pinned`はsource checkoutの組み合わせを再現するための状態です。
validatorは各実装済みcomponentとruntime profileのversionが完全なcommit SHAであることを検証し、
workspace検証時はlocal HEADとの一致も確認します。release artifact、checksum、
統合互換性はまだ保証しません。

`unpinned`はmanifest作成初期の移行状態としてvalidatorが受理しますが、
現在のmanifestでは使用しません。`verified`はrelease artifactと統合試験まで
完了した組み合わせだけに使用します。

## Development pin update flow

moduleの`main`を更新したら、EcoSystemを完了またはPushする前に、catalog rootで次を実行します。

```bash
make check-pins
make sync-pins
make check-workspace
make check-governance
```

`check-pins`はread-onlyで、manifestと各`workspace_path`のGit HEADに差があればexit 1を返します。
`sync-pins`だけが`ecosystem.yaml`を更新し、`planned` componentと未配置のoptional repositoryは
変更しません。required repositoryの欠落、Git HEAD取得不能、40桁SHAでないversionはfail closedに
します。複数moduleをPushする場合は、moduleとWorkspace snapshotを先に確定し、最後に
`sync-pins`を実行してEcoSystemをPushします。これにより、後続commitでpinが直ちに古くなる順序を
避けます。

## Release flow

1. source-pinned commitでmodule固有testを通す。
2. module repoがimmutable tagとartifactを公開する。
3. `ecosystem.yaml`の対象componentを実在tagに更新する。
4. required CORE flowと選択optional capabilityの統合試験を実行する。
5. command、環境、結果、未確認点をverification recordに残す。
6. compatibility statusを`verified`に変更する。
7. EcoSystemに独立したsemantic version tagを付ける。

例: STT だけが更新された場合、STT module を release して CORE 接続試験を行い、
manifest の STT version を更新してから ecosystem patch release を作ります。

## Minimum acceptance

- `source-pinned`ではmanifestに記載したrepositoryとcommitが実在する。
- `verified`ではmanifestに記載したrepositoryとtagが実在する。
- artifact の checksum が一致する。
- `runtime.primary`のartifact、implementation、statusがmodule releaseと一致する。
- required companionがあるcomponentは、bundled／externalの境界と接続確認結果を記録する。
- runtime profileはowner componentを持ち、ownerの正規routeを迂回しない。
- CORE が clean environment で起動し health check を通る。
- required user flow を最低 1 回 end-to-end で確認する。
- optional component は「install したもの」ごとに接続・失敗時表示を確認する。
- secret、runtime state、生成物を release source に含めない。
- rollback 先となる直前の verified manifest を保持する。

health success だけで音声再生、認識、画像解析、game bridge などの利用可能性を
主張しません。各 capability は実際の入出力まで確認します。

## Persistent DB capability acceptance

全てのpersistent domainは、catalog上のownerだけでなく、次のread／write契約を満たしてから
統合互換性を主張します。詳細なDB仕様は各owner moduleとCOREの正本へ戻します。

- owner moduleがpurpose、role、authenticated scope、相関IDを検証し、bounded read projectionと
  named route／Toolを提供する。取得不能・scope不一致・owner停止は推測せず、`unavailable`、
  `rejected`、または`blocked`でfail-closedにする。
- owner moduleがvalidated write command／workflow、重複防止、結果receiptまたは同等の相関証拠を
  提供する。raw path、SQL、DB driver、別moduleの内部storeを利用する経路は不合格とする。
- 各persistent domainについて、認証済みCORE Agentをactorとするproduction-shaped E2Eを、readと
  writeで少なくとも各1回実行する。証拠にはrequest actor、scope、owner route、projection／write
  receipt、拒否・失敗時のfail-closed結果を記録し、catalog／health／unit testだけでは代用しない。
- CORE catalog上の一つの`investment` storeは、TRADEの`source`、`learning`、`market`、`replay`、
  `portfolio`、`ledger`六domainへ写像する。operationはrecallが`source_record`、`learning_candidate`、
  `market_snapshot`、`replay_decision`、`portfolio_snapshot`、`ledger_outcome_report`、writeが
  `collect_source`、`import_learning_candidate`、`import_market_snapshot`、`record_replay_decision`、
  `ensure_portfolio_initialized`、`record_shadow_observation`で固定する。
- TRADEの互換性は、認証済み実CORE Agentが同一runでwrite→readを完了し、restart後のdurability／idempotent
  replay、raw leakageなし、外部financial executionなしを確認するまで主張しない。2026-08-14に認証済みproduction
  Shiro/WorkerがTRADE六domainでこれらを完了した。
- `RenCrow_TRADE`はprivate API gateway経由だけを受け付け、CORE直読を禁止する。PORTAL、CMD、
  ASSISTANTはCORE Public API clientであり、COREまたは他moduleのDBへ直接アクセスしない。
- `RenCrow_Workspace`のmachine-readable projectionはportable policy／設定の入力であり、
  live DB、認証権限、runtime capabilityの正本ではない。

`source-pinned`はsource組み合わせの再現性だけを示します。上記read/write E2Eとowner境界の
verification evidenceが揃わない限り、statusを`verified`へ変更してはいけません。

## RenCrow_GAMES acceptance

- COREのAgentから`POST /viewer/games/launch`を実行し、
  GAMES Observerがsessionを起動する。
- GAMESのObservationRequestを対象のCORE Agentが判断し、GAMESのdeterministic executorが
  検証後に実行する。RuleBasedBrainはtest／simulationに限定する。
- `/viewer/games/observer`経由でユーザーが実行中の盤面、判断、結果を確認できる。
- GAMESがresultとObserverFrameをCOREへ返し、`/viewer/games/result`がReplayと
  相関できるcandidate eventを記録する。
- CORE停止時にGAMESが本番LLMへ直接fallbackせず、world stateを壊さず停止または
  明示したdegraded modeへ移る。

## RenCrow_LLM acceptance

RenCrow_LLMを含む組み合わせでは、一般的なminimum acceptanceに加えて次を確認します。

- client／COREがRuntime、Backend、Modelへ直結していない。
- `CORE -> RenCrow LLM Gateway -> RenCrow LLM Runtime -> Backend -> Model`が維持される。
- Mio／Chat、Shiro／ChatWorker・Worker、Midori／Wild、Kuro／Heavyが意図したtargetへ解決される。
- Role profileがExecution Roleに付随する技術設定であり、独立したAgent層になっていない。
- clientがAgentだけを選び、COREがRole、GatewayがRuntime、RuntimeがBackend／Modelを
  選ぶ責務境界が維持される。
- execution aliasをopaqueなAgent／Role binding contractとして扱い、Agent ID、
  Role ID、Model名へ誤って固定していない。
- RenCrow LLM Runtime導入後はGatewayとRuntimeのversion、status schema、認証、
  Backend contractが一致する。
- Runtime liveness、Backend readiness、Model readiness、実生成を別checkpointとして確認する。
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
`docs/10_Gateway_Runtime_Backend_Model責務仕様.md`を参照してください。

Target mappingを変更したverification recordには、少なくともCORE／LLM module version、
Agent、Execution Role、execution alias、old/new Role profile revision、Target ID、
provider、Model、外部送信／課金区分、E2E結果、rollback先を記録します。secret、credential、
物理Model path、不要なBackend URLは記録しません。EcoSystem manifestは検証済みmodule
releaseの組み合わせを固定し、runtimeのRole profileそのものの正本にはしません。

## PORTAL and CORE acceptance

PORTALを含む組み合わせでは、一般的なminimum acceptanceに加えて次を確認します。

- `IdleChat`のwrite拒否と、`Chat`／`Games`の明示allowlistを確認する。
- recipient切替通知と、実際のmessage `to`が一致することを確認する。
- GamesでNetHackとAgentを選択し、`personas[]`付きlaunch、session一覧、
  同一origin Observer、`decision.agent_id`までを実Agent E2Eで確認する。
- Gamesからdecision／result／Observer ingest／debugが拒否され、sessionの
  Retry／Start overだけが許可されることを確認する。
- GamesのPuruPuru overlayがiframe外でゲーム入力を遮らず、
  `bridge.decision_mode=agent`かつAgent identity一致の`result.speech`だけを発話候補にする。
- TTSのaudio owner取得、SSE audio、音声取得、browser再生、playback ACKを
  別々のcheckpointとして確認する。
- STTのinput owner取得、WebSocket upgrade、音声送信、STT target接続、最終認識を
  別々のcheckpointとして確認する。
- TTS／STT target停止時に失敗表示とowner解放を確認する。
- Debug／admin、cross-origin control、設定外TTS audio hostが拒否されることを確認する。

詳細な接続契約と確認項目は[PORTAL–CORE contract](portal-core-contract.md)を参照してください。

## ASSISTANT acceptance

ASSISTANTの常駐serviceをreleaseへ含める段階では、一般的なminimum acceptanceに加えて
次を確認します。

- 生活Routineが指定時刻・条件で一度だけ発火し、重複deliveryを起こさない。
- acknowledgement、snooze、missed、retry、別端末への切替を追跡できる。
- personal data、`family:shared`、別利用者のprivate dataが権限どおりに分離される。
- COREへのTask昇格で利用者scopeと相関IDが維持され、結果が元のdeliveryへ戻る。
- CORE停止時にAgent処理をdegradedとし、決定論的Routineとcache済み情報の状態を区別する。
- 実際のDevice clientでPUSH、表示または発話、利用者応答までend-to-endで確認する。

詳細な境界は[ASSISTANT boundary](assistant-boundary.md)を参照してください。
module固有の仕様と実装状態は、ASSISTANT repositoryの`docs/`を正本とします。

## Interaction profile acceptance

現行のPORTALとCMDを同じ組み合わせへ含める場合は、追加で次を確認します。

- Chatのrecipient、利用者scope、request／response相関がsurface間で一致する。
- IdleChatのevent、開始／停止、拒否、degradedの意味がsurface間で矛盾しない。
- profile、mode、認証scope、device capabilityによる拒否が実際に機能する。
- 再接続と再送でmessage、Task、PUSH、acknowledgementが二重処理されない。
- CMDの`cmd-chat`、`cmd-idlechat`、`cmd-diagnostics`、`cmd-control`が、それぞれ
  CORE Public APIのallowlist内だけを利用する。
- `rencrowctl chat --audio`がCOREの`/stt/chat-input`を経由し、
  `--audio-direct`がCOREの`/viewer/send`添付経路を利用する。CMDが
  RenCrow_STT targetやRenCrow_LLMへ直接接続しない。
- ASSISTANT実装時は、PORTAL停止中もRoutineとPUSHが動き、CORE停止時はAgent処理だけを
  degradedとして区別する。

共通能力と固有差は[Interaction surfaces](interaction-surfaces.md)を参照してください。
