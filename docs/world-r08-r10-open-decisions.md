# WORLD R08–R10 未決事項とルミナ決定案

- 作成日: 2026-10-20
- 状態: **ルミナ決定案に基づくWORLD側実装とCORE側source foundation＋runtime loop＋WORLD read client sourceをCORE `origin/main` へmerge済みで、CORE local mainの未コミットWIPも単位別検証後に同一 `main` へ統合・Pushした。CORE OutboxはTask store commitを正本とするstate reconciliation方式、LifePolicyはAgentProfile／Personaからのowner導出方式、COREのWORLD readはexact scope＋Actor allowlist＋cursor resync方式、WORLDのassessmentはbound CORE Actor向けread-only route方式に決定・実装。CORE read bridgeのproduction route、canonical route・実測geometry・production E2Eは未決。**
- 対象: `RenCrow_WORLD` R08 projection inbox、R09/R10 CORE bridge・生活行動、R11/R14前提のgeometry、WORLD runtime route
- 関連: [WORLD R08](../RenCrow_WORLD/docs/R08.md)、[WORLD R07](../RenCrow_WORLD/docs/R07.md)、[WORLD R06](../RenCrow_WORLD/docs/R06.md)、[ID互換性](../RenCrow_WORLD/docs/ID.md)、[v1.4実装仕様](../RenCrow_WORLD/docs/implementation-spec-v1.4.md)

## 0. この文書の位置づけ

R08のWORLD側source foundationに加え、接続契約の補強、復元後のchecked reconcile、R09の意味層、R10の部分的なpresentation/stop planningまで実装・Push・検証した。CORE側もWorkSet v2／LifePolicy payload、HTTP publisher、SQLite durable outbox、durable source revision、内容digest比較でrevision消費を抑えるfull WorkSet projector、`world_projection` configからのruntime loop、Task commit observerによる即時再同期、起動時full再同期を別worktreeで実装・Pushし、実WORLD binaryとのcross-repo E2Eと実Task storeを使うruntime起動テストを確認した。COREのOutboxはTask store transactionを正本とする派生deliveryとし、同一transactionでOutbox行を追記しない方式をD-25として決定した。LifePolicyはCOREのAgentProfile非認知activity envelopeとPersona CharacterProfileのcanonical hashから導出する方式をD-26として決定・実装した。COREのWORLD read clientは、exact World／Timeline／`timeline_epoch` scope、Bearer credential、Snapshotのstate hash、whole-transaction cursor、Actor allowlist、allowlist外Actor Eventのpayload非公開、cursor resync分類をD-27として決定・実装し、実WORLD binaryとのE2Eを確認した。WORLDは、operator-authorized `core_projection_actors`に含まれるActorについて、保存済みWorkSet／LifePolicy headの意味評価をread-only assessment routeで返す方式をD-28として決定・実装し、実WORLD binaryのE2Eを確認した。COREの`feat/world-r08-publisher`は`origin/main` `084fe2af`へconflictなしでmerge・Pushした。CORE local main worktreeが保持していた83件の未コミットWIPは、単位別の検証と`origin/main`との競合8件の両立解消を経てRenCrow_CORE `a20e2a24` で同一 `main` へ統合・Pushし、local mainは `origin/main` と同期した（reset・stash・cleanはしていない）。ただし、CORE read bridgeのproduction route／DTO、WORLD側catalogのR10 controller接続、canonical route、実測geometry、R10の実際の移動・占有、production配備・実network・再起動を含むCORE runtime全体のE2Eは未決のため、受入matrixのAC-004/005/011/012/013/014は `not_run` のままである。

本文書は、ルミナの決定案を既存の未決事項へ対応付けたものである。正式決定ではないため、決定ログで決定・実装・検証を分けて記録する。

### 今回の重要な修正点

1. **ACK・発行者・再同期権限を後回しにしない。** 接続契約の一部としてP0で決める。
2. **復元後の開放を「呼ばれたから開く」処理にしない。** WORLDが必要な投影の実在・版・digest・期限を検査する。
3. **ポートや家具座標の未確定を、無関係な実装まで止める理由にしない。** 接続契約、生活論理、実空間、配備を分離する。

## 1. 決定案サマリ

| ID | 決定案 | 状態 | 主担当 | 優先 |
|---|---|---|---|---|
| D-01 | CORE content / WORLD receive contract / 相互fixture に所有を分ける | WORLD側実装済み / CORE payload・publisher・outbox・projector・runtime loop実装済み（disabled既定）、production未検証 | CORE + WORLD | P0 |
| D-02 | ActorInstance・Publisher・Credential・source_epoch・timeline_epochを分離する | WORLD側実装済み / CORE credential保持・runtime identity config実装済み、production未検証 | CORE + WORLD | P0 |
| D-03 | WORLD ACKは「受信・永続保存」の証拠。生活適用の証拠にしない | WORLD側実装済み / CORE ACK分類・Outbox・runtime loop実装済み、production未検証 | WORLD + CORE | P0 |
| D-04 | source epoch切替は通常投影と別権限にする | WORLD側実装済み / CORE reconcile flag・epoch supersede source実装済み | WORLD + CORE | P0 |
| D-05 | CORE WIPは保持し、別worktreeで実装する | 別worktreeでsource＋runtime loop実装済み・元WIP未変更 | ユーザー | P0 |
| D-06 | 復元後のCommand開放はWORLDが投影実在を検査する | 実装済み：WORLD checked gate＋暫定HTTP route／CORE側epoch切替はreconcile credential分離／canonical route・配備受入は未決 | WORLD + CORE | P1 |
| D-07 | 期限切れWorkSetはunknown。成功・完了・割当なしを推定しない | 意味層実装済み | WORLD | P1 |
| D-08 | 空WorkSetは「現在割当なし」。成功に変換しない | 意味層実装済み | WORLD + CORE | P1 |
| D-09 | LifePolicy期限切れは明示fallbackだけ。なければblocked | 意味層実装済み | WORLD + CORE | P1 |
| D-10 | fallback ⊆ allowed、かつ登録済み非認知活動だけ許可 | 検証・実行時filter実装済み | CORE + WORLD | P1 |
| D-11 | 新規活動の停止と、実行中活動の安全な終了を分ける | 計画層・read-only公開・停止実行ロジック（論理台帳）実装済み / runtime Event・状態配線と運動は未実装 | WORLD | P2 |
| D-12 | queued/running/presenceに応じて移動・姿勢を決める | presentation判定・停止後姿勢・実行ロジック（論理台帳）実装済み / 移動未実装 | WORLD + CORE | P2 |
| D-13 | 通常ChatをWorkSetへ含めず、Chat本文から移動を生成しない | WORLD側は非生成 / CORE builderはTask/Run限定、runtime loop実装済み | CORE | P2 |
| D-14 | URL構造・契約版・認証・healthは先に決め、port番号は配備設定に分ける | health実装 / canonical port未決 | runtime owner | P1 |
| D-15 | 非loopback前にTLS終端・発行者・token交換/失効を決める | 未決 | runtime owner | P3 |
| D-16 | browserへはCORE/PORTALのViewer変換経由で渡す | 未着手 | CORE + PORTAL | P2 |
| D-17 | Geometry PoCの成果物と合格条件を固定する | 未決（実測asset待ち） | HOUSE + WORLD | P2 |
| D-18 | logical_ready / spatial_readyを分離する | healthで分離実装済み / spatialは未実測 | WORLD | P2 |
| D-19 | 現在headの認可付き照会と、epoch拒否情報の保持を用意する | WORLD側実装済み | WORLD | P0 |
| D-20 | Publisher ID / Credential IDを監査記録する | WORLD側実装済み | WORLD | P0 |
| D-21 | macOS実行試験まで三OS受入を主張しない | 未検証 | WORLD | P3 |
| D-22 | CORE / WORLD / 統合担当で受入証拠を分ける | 未着手 | 統合担当 | P3 |
| D-23 | Command本文に送信者の意図する`timeline_epoch`を必須化する | WORLD側実装済み | WORLD | P0 |
| D-24 | healthをlive / store ready / reconciled / spatial readyに分ける | live/store/logical/reconciled分離実装済み / spatialは未実測 | WORLD | P2 |
| D-25 | CORE OutboxはTask store commitを正本とする派生deliveryとし、同一transaction追記をしない | CORE commit observer・起動時full再同期・restart回収テスト実装済み / production未検証 | CORE | P0 |
| D-26 | LifePolicyはAgentProfileの非認知envelopeとPersona／AgentProfileのcanonical hashから導出し、CORE定義IDをWORLDが登録する | CORE導出・projector・runtime配線、WORLD catalog登録、cross-repo E2E実装済み / production未検証 | CORE + WORLD | P1 |
| D-27 | COREはWORLD R07 Snapshot／Eventを認証済みread clientで読み、exact scope・Actor allowlist・cursor resyncをCORE境界で適用する | CORE read client source・実WORLD E2E実装済み / production route未決 | CORE | P1 |
| D-28 | WORLDはbound CORE Actor向けに保存済みWorkSet／LifePolicy headのread-only assessmentを返し、DefaultCatalogで未登録IDを除外する | WORLD assessment route・実WORLD E2E実装済み / 暫定route・CORE未消費 | WORLD | P1 |
| D-29 | 独立ConditionProfile ownerは、独立した体調データのowner・lifecycle・更新経路ができるまで新設せず、`condition_profile_ref`はAgentProfile全体のcanonical hashを維持する | 決定 / 実装変更なし | CORE | P2 |

### 実装状況（2026-10-20）

| 単位 | WORLD commit | 状態 | 証拠 |
|---|---|---|---|
| 接続契約の補強 | `3b491e3` | Linux/Windows source、R07/R08 E2E | epoch必須化、publisher/credential、reconcile scope、head GET |
| 復元checked gate | `3b491e3` | Linux/Windows source | `CompleteReconcileChecked`、期限切れ拒否、health 503 |
| 復元reconcile route | `9ebf057` | Linux/Windows HTTP unit + R08 E2E | 設定由来のrequired set、epoch/revision検証、開放後Command |
| R09意味層・R10部分計画 | `8622551` | Linux/Windows source、R09 integration E2E | WorkSet/LifePolicy評価、fallback subset、presentation、stop plan |
| health段階分離 | `0a9bce3` | R07/R08 E2E | live / store_ready / logical_ready / reconciled / spatial_ready |
| CORE projection source foundation | `dc22d13b`〜`181d19fa`（RenCrow_CORE `feat/world-r08-publisher`） | `go test ./...`、`go test -race`、実WORLD binaryとのcross-repo E2E | WorkSet v2/LifePolicy、source epoch/revision、canonical JSON digest、HTTP publisher、SQLite durable outbox、ACK分類、revision conflict、stale拒否、reconcile supersede、in-flight lease回収、`epoch_unchanged` head照合、Task assignee完全一致 |
| CORE projector / runtime loop | `570aa59a`〜`e9b39848`（RenCrow_CORE `feat/world-r08-publisher`） | `go test ./...`（Git外の検証worktree）、実WORLD binaryとのprojector E2E、実Task storeを使うruntime起動テスト | durable source revision（counter欠落時はcommitted outboxから前進回復）、内容digest比較によるrevision省略、validity更新、projector／outbox／drain loop、`world_projection` config（disabled既定）、graceful shutdown、architecture allowlist更新、Task commit observerによる即時再同期、起動時full再同期、commitと配送の間の停止を再現するrestart回収テスト |
| CORE LifePolicy owner導出 | RenCrow_CORE `6dc61da9` / RenCrow_WORLD `54ad10c` | CORE `go test ./...`（変更package＋Git worktreeで実行中）、実WORLD binaryとのLifePolicy E2E、WORLD `internal/life` | AgentProfileの`NonCognitiveEnvelope`、Persona／AgentProfileのcanonical SHA-256、種別別source revision、内容digest比較、`life_policy_enabled`（既定true）、character bundle欠落時の起動失敗、WORLD `DefaultCatalog`の8 ID登録、persona変更→LifePolicy revision 2 |
| CORE WORLD read client | RenCrow_CORE `1412d8d1` / RenCrow_WORLD `b2010f4` | `go test`／`go test -race`、実WORLD binaryとのread E2E、read scope欠落の制御fault | exact scope、Bearer credential、state hash、whole-transaction cursor、Actor allowlist、top-level `actor_id` Eventのpayload非公開、cursor ahead／history欠落のresync、scope不一致403、token不正401、WORLD ID transport fixture、非ASCII World／Timeline path |
| WORLD assessment route | RenCrow_WORLD `487ad00` | `go test ./...`、`go test -race ./internal/httpapi`、実WORLD binaryのR08 E2E（projection head→assessment、restart、auth） | `GET .../actors/{actor}/assessment`、`read` scope、bound Actor限定、DefaultCatalogによる未登録ID除外、missing/expired/fresh、presentation、`work_success=false`、state_seq不変、403/400/503/500 |
| CORE R08 feature merge | RenCrow_CORE `084fe2af` | CORE full suite（`/var/tmp` clean worktree）、race、実WORLD binaryとのread／LifePolicy E2E | `feat/world-r08-publisher`を`origin/main`へconflictなしでmerge。この時点ではlocal mainは25 commit behind / 83 dirtyで未更新、WIP保持（翌朝の単位別検証で下記`a20e2a24`へ統合） |
| CORE WIP 単位別検証・統合 | RenCrow_CORE `a20e2a24`（CI: `f563ac91`、`e8dbb9b9`） | 単位別test（会話・turn永続化／Mio・orchestrator／routing classifier／Viewer／runtime配線／docs）、統合後のGo full suite exit 0、Viewer Node 288/288、公開docsガード、GitHub Actions Canonical Test Plan（Ubuntu／macOS／Windows＋direct-chat-regression）・build・Public Docs Guard success | 失敗した単位はテスト側の期待値・publication前提・canonical plan登録を正して解消。WIPは保持したまま`main`へ統合し、local mainを`origin/main`と同期 |
| WORLD canonical test plan登録 | RenCrow_WORLD `49f95e9` | GitHub Actions Go source checks（Linux／Windows／macOS）success、`go test ./...`・`go vet ./...`・`go build ./...` exit 0、`scripts/e2e-r06.sh`／`e2e-r07.sh`／`e2e-r08.sh`／`e2e-r09.sh` PASS | `internal/httpapi/assessment_test.go`・`internal/httpapi/projection_test.go`・`internal/life/` 4件・`internal/projection/envelope_test.go`・`internal/store/projection*_test.go` の9件をcanonical planへ登録。12 push（`d0eaa15`〜`487ad00`）にわたり失敗していたCIが復帰 |

CORE側のOutboxはTask store commitを正本とするstate reconciliation方式（D-25）で、同一transaction追記は行わない。LifePolicyはActorごとのAgentProfile非認知envelopeとPersona／AgentProfileのcanonical hashから導出し（D-26）、WorkSetとは独立したsource revisionで投影する。canonical route/port、実測geometry、macOS、受入matrix、production配備・実network・再起動を含むCORE runtime全体のE2Eは未完了である。WORLD側とCORE source foundation＋runtime loopの成功をCORE接続の完了やAC-004/005/011/012/013/014の成立に読み替えない。

## 2. COREとの接続契約

対象: D-01〜D-04、D-19、D-20、D-23

### D-01 契約の所有者をデータと通信で分ける

参照Schemaを土台に正式化する。全面再設計やWORLDだけの暫定運用は避ける。ただし、すべてをCORE所有にしない。

| 契約 | 正本を管理する側 | 相手側の役割 |
|---|---|---|
| WorkSet・LifePolicyの内容と意味 | CORE | WORLDが受信・検証・利用する |
| 宛先、Actor binding、投影の受付条件 | WORLDの受信契約 | COREがその契約に従って送る |
| Projection ACK | WORLD | COREがOutboxの配送結果として解釈する |
| 相互接続の版とfixture | 双方で採用 | 同じ入力・結果で契約試験を行う |

契約ファイルの保存先を一つにすることと、意味の決定権をすべて一方へ渡すことは別である。新しい契約専用repositoryは増やさない。

現在の受信処理は未知フィールドを拒否する。したがって「将来はフィールドを足すだけ」にはできない。**対応する契約版を明示し、受信側の対応を確認してから送信側を切り替える。** versioning規則を契約に含める。

**決定に必要なもの:** CORE ownerの採用表明、schema revision管理、unknown field追加時のversioning、WorkSet/LifePolicy fixtureの相互検証。

### D-02 Actor・発行者・認証情報を分離する

短期はoperator設定のbindingを継続する。ただし、次を別IDとして扱う。

| 識別対象 | 方針 |
|---|---|
| ActorInstance | 通常のCORE再起動では維持する |
| Publisher | 投影を発行する主体。認証情報が変わっても本人性を維持する |
| Credential / token | 交換・失効できる認証手段 |
| source_epoch | 投影の連番を継続できなくなったときなどに明示的に切り替える |
| timeline_epoch | WORLDの復元で切り替わる宛先側の履歴世代 |

初期実装では、同じActor・投影種別へ同時に書くPublisherを一つに限定する。複数COREの同時書込みや自動主系切替は必須範囲にしない。

**現行コードの注意:** Command経路は認証tokenのIDをそのまま`client_id`に使っている。token交換でIDまで変えると、同じ要求でも冪等性の名前空間が変わる。認証情報の交換で同じ依頼が別依頼になる構造を避け、論理Publisher IDとCredential IDを分ける契約へ寄せる。

### D-03 ACKは受信・永続保存の証拠であり、生活適用の証拠ではない

WORLDのACKをCORE Outboxの受領証拠にする。ただし、意味は次に限定する。

> WORLDの投影受信箱に、この宛先・Actor・種別・版・内容が保存された。

移動開始、仕事姿勢への変更、実仕事の成功を意味しない。現行R08も、投影受信だけではWorldEvent・WorldState・Command Receiptを生成しない。この境界を維持する。

| 応答 | COREの扱い |
|---|---|
| `accepted` | 配送完了 |
| `duplicate` | 宛先・版・digestの一致を確認して配送完了 |
| `stale_revision` | より新しい全量投影に置き換えられた状態。元の投影が届いた証拠にはしない |
| `revision_conflict` | 自動再送では解決しない。ストリームを止めて不整合を報告 |
| `epoch_requires_reconcile` | 通常再送を止め、認可された再同期処理へ移る |
| `epoch_superseded` | 古い送信を打ち切る。新epochへ宛先だけ書き換えて再送しない |
| `epoch_unchanged` | これだけでは配送完了にしない。保存済みheadとの一致確認が必要 |

**現行コードの注意:** 同じsource epochへの再同期要求は、revision/digest比較より前に`epoch_unchanged`を返す。これを無条件の再送成功として扱わない。

`ack_id`は応答ごとの識別子でよい。配送の同一性は、宛先・Actor・投影種別・source epoch・revisionとdigestで判定する。

### D-04 再同期権限を通常投影から分離する

通常の`projection`と別に、source epoch切替用の権限を設ける。WORLD復元後のCommand開放は、さらに別の権限・判定である。

初期案:

- `projection`: 通常のfull投影
- `projection_reconcile`: source epoch切替
- 復元後のCommand開放: `CompleteReconcile`相当の明示操作。COREは要求できるが、最終判定はWORLD

### D-19 head照会と保持

最初から大規模なACK検索機能は作らない。ただし、**現在のheadと版・digestを認可付きで照会できる経路**を用意する。再同期応答を失った場合の確認に使う。

保持期間は一律にしない。詳細な配送試行ログは削減できるが、**古いepochを拒否する情報は日数だけで削除しない。** 宛先の運用終了・廃棄と結び付ける。

### D-20 Publisher / Credentialの監査記録

最初の正式接続に含める。ACKまたは受信履歴にPublisher IDとCredential IDを記録し、token本体は保存しない。

### D-23 Command本文に宛先epochを必須化する

現行HTTP Command本文には`timeline_epoch`がなく、サーバー設定のScopeがそのままCommandへ設定される。認証tokenのepoch束縛は任意である。

この組合せでは、epochに束縛していないtokenを継続利用し、同じURLを復元後のepochへ向ける運用で、古いHTTP要求を新しいepochの要求として扱う経路が残る。

**決定案:** 正式Command契約に送信者が意図する`timeline_epoch`を必須化し、サーバーの現在epochと一致しなければ拒否する。復元後の冪等性はStore内部のキー分離だけでなく、入口で「どの世代への依頼か」を照合して成立させる。

### D-27 COREのWORLD read client

COREはWORLD R07の`GET .../snapshot`と`GET .../events`を、CORE内部の認証済みclientから読む。browserへWORLD reader credential、DB path、private Memory参照を渡さない。WORLDからCOREへのcallbackは作らない。

CORE側の受理条件:

- 設定された1つのWorld／Timeline／`timeline_epoch`とレスポンスscopeが完全一致すること。
- Snapshotの`schema_version`、`state_seq`、canonical lowercase SHA-256 `state_hash`、`state.actors`の存在。
- Event pageがwhole transactionで、`after_seq`の直後から連続し、`next_seq`が最後のEventと一致すること。
- cursorがSnapshotより先、history欠落、sequence gap、transaction分断の場合は部分状態を返さず`resync`にすること。
- Snapshotは設定Actor allowlistだけを返すこと。allowlist外Actorのtop-level `actor_id` Eventはpayloadを返さずcursorだけ進めること。

これはCORE表示scopeの最初の境界であり、private-room redaction、Observation配信、StoryPlayer向けの完全なViewer projectionではない。WORLD R07の`read`はowner-scoped Snapshotを返すため、CORE側でActor allowlistを適用してもWORLDの全stateを公開したことにはならない。

COREのproduction read bridge route／DTOは未決定であり、`internal/adapter/worldread`はsource-level clientに留める。R04 PoCの`GET /viewer/world/snapshot`と`GET /viewer/world/stream`を本番routeへ昇格しない。WORLD R07 routeは暫定契約であり、canonical route／port／TLSは別決定である。

証拠: RenCrow_CORE `1412d8d1`のunit／race test、実WORLD binary `b2010f4`とのread E2E、read scopeを外した制御faultで`ErrForbidden`になること、非ASCII World／Timelineのtransport fixture。

### D-28 WORLDのread-only assessment route

WORLDは、operator-authorized `core_projection_actors`に含まれるActorについて、保存済みWorkSet／LifePolicy headの意味評価を次のrouteで返す。

```text
GET /v1/worlds/{world}/timelines/{timeline}/actors/{actor}/assessment
```

`read` scopeを要求し、`{actor}`はID transportでdecodeする。`core_projection_actors`にないActorは`403 actor_not_bound`、不正なtransportは`400 invalid_actor_id`、Timeline不在は`503 not_ready`、保存headが再parseできない場合は`500 projection_unreadable`でfail closedする。

返却するのは`work_set_state`、`policy_state`、`work_presentation`、`permitted_activity_ids`、`executable_activity_ids`、`new_activity_allowed`、`blocked_reason`、`work_success`、`assessed_at`である。`permitted_activity_ids`は`DefaultCatalog`に登録されたIDだけを昇順で返し、未登録IDは除外する。`executable_activity_ids`はWORLDの活動定義表（D-11）でstop stateを持つIDのうち、現行policyが許可しpresence制約でもその場で実行できるものだけを昇順で返す公開専用の候補集合で、route自身が選択・開始・移動・占有を計画することはない。`work_success`は常に`false`で、空WorkSetを成功に変換しない。routeはActivityを選択・開始せず、移動・占有を計画せず、Event／State／Command Receiptを生成しない。候補は論理名のみで、実在場所・予約・実測geometryの主張は含まない（D-17／D-18未決）。

これはWORLD内の暫定routeであり、COREのproduction read bridge routeでもcanonical cross-module contractでもない。COREは`internal/adapter/worldread`のsource-level read clientでこの契約を消費する（assessment read DTOと`Client.Assessment`。実WORLD binaryとのcross-repo E2Eで実projection route経由の読み戻しを`50942c72`で確認）。production read bridge route／DTOへの配線は未決のまま。Stop planningのHTTP/CLI route、Activity selection、R10 controller、移動・占有は未実装である。

証拠: RenCrow_WORLD `487ad00`の`TestAssessment...`（auth、missing head、catalog filter、expired fallback、presentation、state不変、GET限定）、`go test ./...`、`go test -race ./internal/httpapi`、実WORLD binaryを使う`scripts/e2e-r08.sh`のassessment assertion。候補公開は`5dcb6e1`の`TestAssessmentPublishesExecutableActivityCandidates`／`TestAssessmentPublishedCandidatesAreDefinedAndPermitted`、`go test ./...`、`scripts/e2e-r08.sh`／`e2e-r09.sh` PASS、GitHub Actions Go source checks（Linux／Windows／macOS）successで確認。

### D-29 ConditionProfile ownerを現時点で新設しない

COREの`AgentProfile`は`NonCognitiveEnvelope`を持つが、体調・稼働可否について、独立したデータ項目、更新主体、保存場所、期限、削除、監査の契約はまだない。`condition_profile_ref`はAgentProfile全体のcanonical SHA-256であり、「どのAgentProfile内容を参照したか」を示すcontent-addressed referenceであって、健康状態そのものの表明ではない。

**決定:** 独立したConditionProfile ownerを新設せず、`condition_profile_ref`をAgentProfile全体のcanonical hashとして維持する。独立ownerを先に作ると、同じAgentProfile内容を二つのownerが別々に更新・検証するsemantic duplicationになり、現在のLifePolicy導出より強い契約を根拠なく追加することになる。

再評価条件は、次のいずれかが実際に必要になった時点とする。

- 体調データをAgentProfile以外の主体が更新する。
- Persona／AgentProfileと異なる更新頻度、期限、削除、監査が必要になる。
- 体調をViewerやWORLDへ独立提示する契約が必要になる。
- 体調に基づく許可判定が、`NonCognitiveEnvelope`だけでは表現できない。

それまでは、`condition_profile_ref`の変更はAgentProfile内容の変更として扱い、独立したConditionProfile revisionやownerを推測で作らない。

証拠: CORE `internal/domain/agentprofile.Profile`、`internal/application/worldprojection/life_policy_source.go`の`agent-profile-sha256:`導出、D-26の実装・E2E。実装変更なし。

## 3. 復元後の再同期

対象: D-06、D-23

### D-06 「何が揃ったか」をWORLDが検査する

旧`CompleteReconcile`はepoch状態を確認して再同期済みフラグを立てるだけで、WorkSetやLifePolicyが実際に揃っているかは検査しなかった。現在は`CompleteReconcileChecked`が宛先・binding・版・期限を検査し、superseded・未bound ActorInstance・head欠落・期限切れ・required重複を同一transactionで閉じ、検査したheadを`epoch_reconcile_projection`へ記録してからreconciledを立てる。暫定HTTP routeはrequired Actor／kind集合をoperator設定から導出し、callerは縮められない。成功前はCommandが`epoch_not_reconciled`でrejectされ、読み取りは可能（RenCrow_WORLD `3b491e3`／`9ebf057`、検証`988a352`）。旧形式はR06互換test専用で、外部のrestore openには使わない。

### 「再同期」という二つの処理を分ける

- **CORE側のsource epoch切替:** 既存投影headに対して発行世代を変更する処理。
- **WORLD復元後の再同期:** 新しいtimeline epochに必要な現在情報を入れ直し、世界の行動を再開可能にする処理。

現行コードでは、headがない状態への`ReconcileProjection`は拒否される。WORLD復元後の新しい宛先に、最初から一律で`?reconcile=true`を付けない。新しい宛先にheadがなければ、認可された通常のfull投影で初期化する。

### 復元手順

```text
WORLDを新しいtimeline_epochへ復元
  ↓
Commandは閉じたまま、読取と必要な投影受付を可能にする
  ↓
今回の復旧に必要なActor・投影種別を固定する
  ↓
COREが現在のLifePolicy・WorkSetを全量送信する
  ↓
WORLDが宛先・binding・版・digest・期限を検査する
  ↓
検査したheadを参照する再同期完了記録を保存する
  ↓
Commandを開放する
```

「全Actor」は将来の登場人物や不在のVisitorまで含めない。**今回復旧する生活インスタンスに必要なActor集合**を明示する。不在Actorの投影待ちで家全体を止めない。

初期版は、必要集合が揃うまで一括で閉じる方式を推奨する。Actor単位の段階開放は、共有家具や相手Actorとの整合条件が増えるため後回しにする。

完了要求を受けた時点で再検査し、投影が途中で失効・置換されていたら開放しない。COREは完了を要求できるが、**最終的に開けてよいかはWORLDが判定する。**

### Command入口のepoch確認

D-23を併用し、Store内部のepoch分離と入口のepoch照合の両方で古い要求を拒否する。

## 4. 生活の意味論

対象: D-07〜D-13

### D-07 / D-08 stale・空Set・期限切れを分ける

| 入力状態 | 意味 | WORLDの扱い |
|---|---|---|
| freshな非空WorkSet | 現在の割当がある | 状態と在席要件に従って表現する |
| freshな空WorkSet | 現在、対象の割当がない | 仕事表現を解除できる。成功とは記録しない |
| 期限切れWorkSet | 現在の割当は不明 | 成功・完了・割当なしを推定しない |
| freshなLifePolicy | 現在有効な生活許可 | 許可と世界条件を満たす活動を選ぶ |
| 期限切れLifePolicy | 通常の活動許可は失効 | 明示された期限切れ用fallbackだけを評価する |
| 未着・失効したbinding | 行動主体の権限を確認できない | fallbackと混同せず、新規活動を認めない |

「仕事が不明」と「身体を一切動かせない」は同義にしない。仕事状態をunknownとして維持しながら、許可された安全な非認知動作へ移る余地を残す。

同じ投影を再受信しただけで有効期限を延ばさない。期限を延ばすならCOREが新しいrevisionを発行する。

### D-09 / D-10 fallbackはsubset。期限後の特別許可として扱う

```text
expired_fallback_activity_ids ⊆ allowed_non_cognitive_activity_ids
```

この部分集合条件に加え、fallbackの各活動が実際に登録された非認知活動であることをWORLDが検査する。LLMやToolを呼ぶ活動をfallbackとして実行しない。

LifePolicyは「通常時の許可」と「期限後に限って残る縮小許可」を明示する。権限そのものの明示的取消しは期限切れと別に扱い、fallbackで覆さない。

fallbackが空なら新規生活活動は`blocked`。ただし、既に始めた活動を安全に停止する後処理まで禁止しない。

### D-26 LifePolicyのowner入力とactivity ID

LifePolicyの許可内容を、Persona本文やLLMの推測から生成しない。COREの既存owner dataから決定的に導出する。

| 項目 | 決定 |
|---|---|
| 許可activity | CORE `agentprofile.Profile.NonCognitive.Allowed`。Actorごとの明示set |
| 期限後fallback | `NonCognitive.ExpiredFallback`。allowedのsubsetでなければ拒否 |
| activity ID | COREが8個の非認知ID（`change_clothes`, `exercise`, `idle`, `read`, `rest`, `sit`, `sleep`, `walk`）を定義し、WORLDが`internal/life.DefaultCatalog`へ登録する。未登録IDはWORLDで除外 |
| `persona_revision` | Persona `CharacterProfile`のcanonical JSON SHA-256。本文・Memoryは送らない |
| `condition_profile_ref` | AgentProfileのcanonical JSON SHA-256。現在のprofile内容への参照であり、体調そのもののownerを新設した意味ではない（D-29） |
| 投影単位 | WorkSetとLifePolicyは別kind・別source revision。内容digestが同じでvalidityが十分ならrevisionを消費しない |
| 起動条件 | `world_projection.life_policy_enabled`は既定true。有効時、設定Actorの`characters/<actor>/` bundleがなければ起動を失敗させる |

実装証拠はCORE `6dc61da9`、WORLD `54ad10c`。COREの`TestRealWorldProjectorProjectsDerivedLifePolicy`は実WORLD binaryへWorkSetとLifePolicyを送り、LifePolicy headのrevision/digest一致、再同期時のskip、Persona変更後のLifePolicy revision 2を確認する。CORE runtime testは実Task storeとcharacter bundleからLifePolicyを生成し、character bundle欠落時の起動失敗も確認する。WORLDの`TestDefaultCatalogRegistersCOREActivityVocabulary`と`TestAssessAcceptsRegisteredLifePolicyVocabulary`は8 IDの登録とassessmentを確認する。

未完了は、WORLD catalogをR10 controllerへ接続すること、Persona／AgentProfile変更のruntime中reload、production configでのcharacter bundle配備である。体調・稼働可否はD-29で独立ownerの新設を見送り、再評価条件を記録した。`condition_profile_ref`は現時点でAgentProfile全体のhashであり、ConditionProfile ownerの実装を意味しない。

### D-11 新規活動の停止と、実行中活動の安全な終了を分ける

- 新しい活動を始める許可
- 始まっている活動を安全に止める処理

を分離する。階段移動中に許可が失効しても、位置を不連続に変えたり、経路予約だけを先に外したりしない。

各Activityに、中断可能な点、停止後の状態、後処理の上限、予約の扱いを定義する。定義がない活動は実行可能カタログへ公開しない。

椅子は、仕事姿勢をやめても身体が座っているなら占有中である。**活動の取消しと物理的占有の解放を同じ操作にしない。**

この中断はWORLDの出来事であり、COREの仕事を失敗・取消し・完了にする根拠にしない。

### D-12 / D-13 queued・running・Chat

| 状態 | 移動・姿勢 |
|---|---|
| queued / Runなし | それだけでは仕事場へ移動しない |
| running / Runあり / presence必要 | 一つの生活Controllerが移動・着席を計画する |
| running / presence不要 | 仕事を理由とする強制移動はしない |
| waiting / blocked | 新規作業を開始せず、現在位置と中断規則に応じて待機する |
| 通常Chat | COREがWorkSetへ含めず、WORLDもChat本文から移動を生成しない |

複数の仕事があっても、身体と移動Controllerは一つ。一件が終わっても、残る仕事の在席要件があれば維持する。

WORLDが仕事場への移動に失敗しても、COREの実仕事まで止めない。仕事の実行と、その仕事をHOUSEでどう見せるかは別。

現行受信コードの`running`のRun必須、`assigned_work`限定、presence指定必須は再実装せず、生活側の意味付けを追加する。

生活側の提示はWORLDのassessment routeがtask IDで公開する（`0d40047`）。`queued_task_ids`はqueued作業、`waiting_task_ids`はwaiting／blocked作業、`running_task_ids`／`presence_task_ids`は実行中作業で、`kind`が`presence`のときだけ一つのControllerが在席移動を計画しうる。queued作業だけでは移動せず、waiting／blockedは新規作業を開始しない。通常Chatは投影契約が`assigned_work`のみを通すためWORLDへ届かず、routeは場所・予約・実測geometryを主張しない。それを消費して実際に移動・占有を決定するR10 controllerは未接続のまま。

## 5. Route・認証・health

対象: D-14〜D-16、D-24

### D-14 URL構造とportを分ける

接続方向は既存方針のまま。

```text
CORE → WORLD：認証付きの投影・行動要求
CORE ← WORLD：状態・Event・観測情報の読取
PORTAL / ブラウザ → COREのViewer用経路
```

WORLD内部APIのURL構造、契約版、認証、healthの意味は先に決める。現在の`/v1/worlds/.../timelines/...`を基礎としてよい。

productionの固定port番号は配備設定であり、契約の意味論とは分ける。正式portが未決でも、loopbackの明示configで実COREを含む隔離接続試験を設計できる。production routeを採用したこととは区別する。

loopbackの明示configで実CORE projection loopと実WORLD binaryを使う隔離接続試験を実装・検証した（RenCrow_CORE `20b4d996`の`cmd/rencrow/runtime_world_projection_loopback_realworld_test.go`、build tag `realworld`）。listen設定から得たloopback addressだけで起動し、WorkSet／LifePolicy投影→assessment読み戻し→health段階→scope拒否（projection-only tokenのread route 403）→未bound Actor 403→127.0.0.1確認までを通す。port番号は試験側で固定せず、production read bridge routeも所有しない。port番号の正式決定とcanonical route採用は引き続き未決である。

なお`20b4d996`のCORE `Canonical Test Plan`（run `39720915514`）は3 OSで失敗したが、失敗stepは`viewer-browser-e2e`（`npm run test:e2e:viewer:to-be`）だけで、同じstepが先行コミット`a10ab79f`（画像画面で服装参照モードを常時表示。`imageMode`をselectからradioへ変更）でも失敗している。ローカル再現では`image_video_idempotency.mjs`が`#imageOptionsStatus`の待機でtimeoutする（テストfixtureが`select#imageMode`前提で、`a10ab79f`以降の実装がradio前提のため`activeMode()`が`''`を返す）。D-14の追加はbuild tag `realworld`のtest fileのみで、canonical planの`go test`ではコンパイルされない。よってこの失敗はViewer所有の既存破綻としてD-14単位とは分離して記録する（Viewerとブラウザテストは並行作業中のため編集しない）。D-14の検証証拠はbuild `39720915712`／Public Docs Guard `39720915520`のsuccessと、ローカルでの当該テストPASS・`go vet -tags realworld` exit 0とする。
`6a2369ac`では`Canonical Test Plan`（run `39734589561`）が3 OSでsuccessであり、この失敗は再現していない。実WORLD loopback試験の成功（build tag `realworld`）と`viewer-browser-e2e`の既存破綻は別件事象として扱い、D-14単位は閉じた状態で確定する。

### D-15 非loopback配備の条件

TLS終端、発行者、token交換・失効手順を決める。ただし、Publisher IDや再同期scopeは非loopback化まで後回しにしない。

### D-16 ViewerはCORE/PORTAL経由

単なる中継では足りない。現在のWORLD読取APIはowner向けで、Viewer向けの私室・公開範囲の除外は未実装である。CORE側で公開可能なSnapshot・Deltaへ変換したものだけをブラウザへ渡す。

### D-24 healthを段階に分ける

| health | 意味 |
|---|---|
| live | プロセス生存 |
| store ready | StoreとTimelineが読める |
| reconciled | 復元後の必要投影が揃い、Commandを開ける |
| spatial ready | 実測geometryに基づく移動・占有が可能 |

`ready`が200だったことだけで「生活再開可能」と判断しない契約にする。

## 6. Geometry

対象: D-17、D-18

### 実測geometryなしで進める部分

- 期限判定
- 活動候補の選択
- WorkSetによる優先度
- 取消し規則
- stale時の処理
- 仮の空間インターフェースを使う単体試験

### 実測geometryが必要な部分

- 実際のHOUSE上での移動
- 家具占有
- 階段
- 通行可否
- 座標と表示の整合

`logical_ready`と`spatial_ready`を分ける。論理試験に使った仮座標を実測済み座標へ昇格させない。

### D-17 Geometry PoCの成果物

| 成果物 | 確認すること |
|---|---|
| 元アセットの版・hash、単位、軸、原点 | どの空間を測ったか再現できる |
| 部屋・扉・階段・家具のID対応 | 論理空間と実空間が結び付く |
| 通行領域と着席・作業アンカー | 到達・利用できる位置が定義される |
| 同じ座標を使う二視点の確認 | カメラを変えても配置が矛盾しない |
| 境界・一人用席・通行不能の試験 | 侵入、重複占有、壁抜けを検出できる |

ここで確認するのは幾何学的な成立である。可愛さや温かさの合格は別のArtGate。美術未受入でもKernelの実装は進められるが、HOUSE完成とは呼ばない。

## 7. WIP・OS・受入証拠

対象: D-05、D-21、D-22

### D-05 CORE WIPは別worktreeで扱う

既存WIPを残した別worktreeで進める。ただし、worktreeを作っただけで安全に独立したとは限らない。

- 開始点のcommitを固定する
- 既存WIPに依存する変更がないか確認する
- テスト用DB、config、portを本番と分ける
- 元の作業ツリーをreset・stash・cleanしない
- 別worktreeの変更を自動統合しない

2026-10-20にCORE/CMDのWIPを読み取り確認した。CORE mainは58 modified / 46 untracked（重複排除後104 path）で、`origin/main`より10 commit遅れており、12 pathが上流変更と重なる。元worktreeはreset・stash・cleanせず、`origin/main` `7de8891a` から `Tmp/worktrees/core-r08-publisher`（branch `feat/world-r08-publisher`）を作成してsource foundationを実装した。CORE/CMDのWIPは変更・統合していない。この確認時点では未統合で、CORE local mainのWIPは2026-10-21に単位別検証へ付して`a20e2a24`で`origin/main`へ統合した。ユーザーの「おまかせ」をD-05の別worktree実装の許可として扱い、他の未決事項の決定とは分離した。

### D-21 macOS

macOS実行試験が終わるまで三OS受入を主張しない。ただし、macOS待ちを理由に、既に対象とする環境でのCORE接続実装まで止めない。

### D-22 受入証拠の分担

| 担当 | 提供するもの |
|---|---|
| CORE側 | 実Outbox、Publisher、再送・復旧・仕事分類の証拠 |
| WORLD側 | 永続受信、順序、権限、epoch、開放条件の証拠 |
| 統合担当 | 両方のbinary/config/fixtureのhashと試験結果の対応表 |

R08文書にはWORLD側のLinux・Windows試験成功が記録されている。実COREとの契約採用・Outbox連携は未完了であり、今回のレビューはこれらの試験を再実行したものではない。

## 8. 実装順序

| 順序 | 先に確定・実装するもの |
|---|---|
| 1. 接続契約 | D-01/02/03/04/20、D-19の最小head照会、D-23のCommand epoch確認 |
| 2. 復元試験 | D-06。新epochへの初期投影、再同期再送、実データ検査、古い要求の拒否 |
| 3. 生活の論理 | D-07〜D-13。実geometryなしで試験できる範囲を先に作る |
| 4. 実空間と表示 | D-17/18、D-16。移動・占有・Viewer用の情報制限を接続する |
| 5. 配備受入 | D-14/15/21/22。正式endpoint、TLS、OS、実行環境ごとの証拠 |

## 9. 最初の接続受入に入れる異常系

通常の成功経路だけでは境界を確認できないため、少なくとも次を含める。

1. WORLDが保存した直後にACKが失われる
2. 片方の投影だけ届いた状態で復元開放を要求する
3. 再同期完了直前に投影が期限切れになる
4. 古いHTTP Commandを復元後に再送する
5. token交換後に同じ依頼を再送する
6. source epoch切替要求と通常投影が競合する
7. `epoch_unchanged` の応答だけで配送完了と誤認しない
8. 同一revision・同一digestの再送で生活効果が重複しない
9. CORE read cursorがSnapshotより先、history欠落、sequence gap、transaction分断のいずれでも部分状態を返さない
10. read scopeなし、token不正、scope不一致のCORE readを認証境界で拒否する
11. allowlist外ActorのEvent payloadをCOREへ返さず、cursorだけ進める

## 10. R08時点との差分

| 項目 | R08時点 | 現在 |
|---|---|---|
| WorkSet/LifePolicy検証 | 実装済み | 維持 |
| 順序・digest・epoch切替 | 実装済み | 維持 |
| projectionのEvent/State非生成 | 実装済み | 維持 |
| Publisher ID / Credential ID | 未記録 | ACKに記録 |
| 再同期scope | `projection`と同一 | `projection_reconcile`へ分離 |
| head照会 | Store内部のみ | 認可付きGET |
| ACKのCORE Outbox解釈 | 未契約 | COREがaccepted/duplicate/epoch_unchanged/conflict/reconcileを分類し、SQLite Outboxへ保存。`world_projection` configでruntime loopを起動（disabled既定） |
| CORE publisher / outbox | 未実装 | WorkSet v2/LifePolicy、AgentProfile／PersonaからのLifePolicy導出、HTTP publisher、SQLite durable outbox、durable source revision、full WorkSet／LifePolicy projector、runtime loopを実装。Task store commitを正本とし、commit observer＋起動時full再同期でOutboxを導出（同一transaction追記なし）。production E2Eは未実装 |
| CORE WORLD read client | 未実装 | 認証済みR07 Snapshot／Event read clientを実装。exact scope、state hash、whole-transaction cursor、Actor allowlist、top-level `actor_id` Eventのscope判定、resync分類、実WORLD E2Eを確認。さらにsource-level read clientがassessment routeを消費（`50942c72`、実WORLD binary E2Eで読み戻し）。production CORE route／DTOは未決 |
| WORLD assessment route | 未実装 | bound CORE Actor向けのread-only assessment routeを実装。`read` scope、missing／expired／fresh、DefaultCatalogによる未登録ID除外、presentation、`work_success=false`、state不変、実WORLD binary E2Eを確認。さらにWORLD活動定義表とpolicy／presence制約から今の候補を`executable_activity_ids`として公開（`5dcb6e1`）。候補の公開のみで選択・開始・移動はせず、暫定routeでCORE未消費 |
| D-13の生活側提示 | 未実装 | assessment routeがqueued／waiting・blocked／running／presenceのtask IDを公開（`0d40047`、実WORLD binaryのE2E assertion含む）。queuedだけでは移動せず、waiting／blockedは新規作業を開始せず、通常Chatは投影契約で除外されWORLDへ届かない。実際の移動・占有・controllerは未実装 |
| ConditionProfile owner | 未決 | 独立ownerを新設せず、`condition_profile_ref`をAgentProfile全体のcanonical hashとして維持（D-29）。再評価条件を記録 |
| 復元後のCommand開放 | `CompleteReconcile`は投影未検査 | `CompleteReconcileChecked`を実装 |
| Commandの宛先epoch | 本文にない | 必須化 |
| health | Store/Timeline中心 | live / store_ready / logical_ready / reconciled / spatial_readyを分離。spatialは未実測 |
| fallback subset | 未強制 | 検証時と実行時に強制 |
| 生活行動・中断 | 未実装 | 意味層とstop planに加え、実行中活動の継続/安全停止/その場保持、公開候補の選別、単一候補のadmissionを決める論理計画層を実装（`8959ca1`）。さらにCORE登録8 IDへ論理占有名・移動要否・中断規則を割り当てたWORLD ownerの活動定義表を実装（`da6762b`）。全活動にstop stateの定義があり、占有解放は全件`false`。consumerとなるR10 controllerは未接続で、実資源・実空間へのバインドと移動・占有は未実装 |

## 11. 決定ログ

決定したら、以下の形式で追記する。決定と実装・検証を混同しない。

| 日付 | ID | 決定 | 決定者 | 証拠 / 実装 | 状態 |
|---|---|---|---|---|---|
| 2026-10-20 | D-01〜D-24 | ルミナ決定案として整理 | Lumina | 本文書 | proposed |
| 2026-10-20 | D-01〜D-04, D-19, D-20, D-23 | WORLD側の接続契約を実装 | Ren | `3b491e3` | implemented |
| 2026-10-20 | D-06 | checked reconcile gateを実装 | Ren | `3b491e3` | implemented |
| 2026-10-20 | D-06 | checked reconcileを暫定HTTP routeで公開 | Ren | `9ebf057` | implemented |
| 2026-10-20 | D-07〜D-12 | R09意味層とR10部分計画を実装 | Ren | `8622551` | implemented |
| 2026-10-20 | D-18, D-24 | healthのreadiness段階を分離 | Ren | `0a9bce3` | implemented |
| 2026-10-20 | D-06 | Windows clean cloneでreconcile routeとR09を検証 | Ren | `988a352` | verified |
| 2026-10-20 | D-05 | CORE WIPを保持し、`origin/main`から別worktreeを作成 | Ren | `Tmp/worktrees/core-r08-publisher` | implemented |
| 2026-10-20 | D-01, D-03, D-04, D-13 | CORE projection source foundationを実装・Push | Ren | RenCrow_CORE `e66c82b2` | implemented |
| 2026-10-20 | D-01, D-03 | 実WORLD binaryとのcross-repo E2Eでpublisher/outboxを検証 | Ren | CORE `e66c82b2` + WORLD `1ca2c21` | verified |
| 2026-10-21 | D-01, D-03, D-04, D-13 | CORE durable source revision、full WorkSet projector、`epoch_unchanged` head照合、Task assignee分離を実装・Push | Ren | RenCrow_CORE `570aa59a` | implemented |
| 2026-10-21 | D-01, D-03 | CORE runtimeへprojector/outbox/drain loopを配線し、実Task store起動テストを追加 | Ren | RenCrow_CORE `3d9aa875`, `23bad8bb` | implemented |
| 2026-10-21 | D-01, D-03 | 実WORLD binaryとのprojector E2E、CORE full suite、architecture allowlistを検証 | Ren | CORE `c191a27f` + WORLD `27b3363` | verified |
| 2026-10-21 | D-25 | CORE OutboxをTask store commitから導出するstate reconciliation方式に決定し、commit observer・起動時full再同期・restart回収テストを実装・Push | Ren | RenCrow_CORE `e9b39848` | implemented / verified |
| 2026-10-21 | D-26 | LifePolicyをAgentProfileの非認知envelopeとPersona／AgentProfileのcanonical hashから導出し、CORE定義8 IDをWORLDが登録。CORE projector／runtimeとWORLD catalogを実装・Push | Ren | RenCrow_CORE `6dc61da9` + RenCrow_WORLD `54ad10c` | implemented / verified |
| 2026-10-21 | D-27 | COREのWORLD read clientをexact scope・Actor allowlist・cursor resync方式で実装・Push | Ren | RenCrow_CORE `1412d8d1` + RenCrow_WORLD `b2010f4` | implemented / verified |
| 2026-10-21 | D-28 | WORLDのbound CORE Actor向けread-only assessment routeとDefaultCatalog消費を実装・Push | Ren | RenCrow_WORLD `487ad00` | implemented / verified |
| 2026-10-21 | D-29 | 独立ConditionProfile ownerを新設せず、`condition_profile_ref`をAgentProfile全体のcanonical hashとして維持 | Ren | 本文書 / 実装変更なし | decided |
| 2026-10-21 | D-25〜D-27 | CORE `feat/world-r08-publisher` を `origin/main` へmerge・Push | Ren | RenCrow_CORE `084fe2af` | merged / verified |
| 2026-10-21 | D-05 | CORE local mainの未コミットWIPを単位別検証し、`origin/main`との競合を両立解消して同一 `main` へ統合・Push | Ren | RenCrow_CORE `a20e2a24`（CI: `f563ac91`、`e8dbb9b9`） | merged / verified |
| 2026-10-22 | D-07, D-09, D-11, D-12 | Assessmentから実行中活動の継続/安全停止/その場保持、公開候補の選別、単一候補のadmissionを決める決定的な生活計画層を、論理占有名のみで実装・Push。presence必須作業はその場と物理占有を保持し、期限切れWorkSetは選択肢を減らさない。移動・占有・実測geometryは扱わない | Ren | RenCrow_WORLD `8959ca1`（CI: `39700320599`） | implemented / verified |
| 2026-10-22 | D-11 | CORE登録8 IDへの論理占有名・移動要否・中断規則をWORLD ownerの活動定義表として実装・Push。全活動にstop stateを定義し、占有解放と後処理は実測移動routeが無いため全件不可。実在場所・予約の主張はしない | Ren | RenCrow_WORLD `da6762b`（CI: `39709175871`） | implemented / verified |
| 2026-10-22 | D-11, D-28 | assessment routeが活動定義表と現行policy／presence制約から「今計画できる候補」を`executable_activity_ids`として公開するよう拡張・Push。公開のみで選択・開始・移動・占有はせず、実在場所・予約・実測geometryの主張なし。production配備、正式port／TLS、実空間の受入（spatial_ready、AC-004／005／011〜014）は未決のまま | Ren | RenCrow_WORLD `5dcb6e1`（CI: `39710368165`） | implemented / verified |
| 2026-10-22 | D-13, D-28 | assessment routeの`work_presentation`へqueued／waiting・blockedのtask IDを公開するよう拡張・Push。queued作業だけでは移動せず、waiting／blockedは新規作業を開始せず、通常Chatは`assigned_work`限定の投影契約でWORLDへ届かない。場所・予約・実測geometryの主張はなし。実空間の受入とR10 controllerは未決のまま | Ren | RenCrow_WORLD `0d40047`（CI: `39711374325`） | implemented / verified |
| 2026-10-22 | D-27, D-28 | COREのsource-level read client（`internal/adapter/worldread`）にassessment route消費を追加・Push：source-level read DTO（`Assessment`／`WorkPresentation`）と`Client.Assessment`を実装し、実WORLD binaryとのcross-repo E2Eで実projection route経由のWorkSet／LifePolicy head送信後にassessmentを読み戻して公開値と一致を確認。候補集合はplanning input専用で、WORLD所有のenum／state値はコピーせず、production read bridge route／DTOへの配線はしない。実在場所・予約・実測geometryの主張なし。併せて`e87f0799`でviewer.js版へ追記トークンが入り既存赤くなっていたViewer版pin testを、STT align35マーカーを保持したまま追記トークン許容へ修正（viewer-node 298/298）。production配備、正式port／TLS、実空間の受入（spatial_ready、AC-004／005／011〜014）は未決のまま | Ren | RenCrow_CORE `50942c72` / `d7de20db`（CI: canonical `39717717288`、build `39717717442`。CORE full `go test ./...` 293/293 packages FAIL 0） | implemented / verified |
| 2026-10-22 | D-14 | 正式port未決のまま、loopbackの明示configで実CORE projection loopと実WORLD binaryを使う隔離接続試験を実装・Push。listen設定由来のloopback addressだけでWorkSet／LifePolicy投影→assessment読み戻し→health段階→projection-only tokenのread route 403→未bound Actor 403→127.0.0.1確認までを検証。port番号は固定せず、production read bridge routeもcanonical routeも採用しない | Ren | RenCrow_CORE `20b4d996`（CI: build `39720915712` success、Public Docs Guard `39720915520` success。ローカルで当該テストPASS、`go vet -tags realworld ./cmd/rencrow` exit 0） | implemented / verified |
| 2026-10-22 | D-06 | CORE側のsource epoch切替をreconcile credentialで分離して実装・Push。`reconcile_enabled`／`reconcile_token_env`は既定closedで、空・`token_env`と同一・参照env空は起動失敗（fail closed）。reconcile送信だけWORLD側`projection_reconcile` scopeのcredentialを使い、projection credentialの流用・fallbackはしない。認可済み切替は旧epochのrevisionを消費せず新epoch revision 1から採番し直し、record IDにepochを含めて衝突回避。未認可のepoch不一致は`ErrSourceEpochSwitchNotAuthorized`で停止しsilent switchしない。現在epochはoutboxのdurable counterが所有し認可済み切替enqueueと同じtransactionで進める。実WORLD binaryとのloopback隔離試験（build tag `realworld`）で通常routeのsilent switch拒否・projection専用credentialの403・reconcile credentialでのrevision 1再baselineとhead読み戻しを確認。WORLD側の投影実在検査（`CompleteReconcileChecked`と`projection_reconcile` scopeのHTTP route）は既存実装済みで、canonical route採用・production配備・restore受入はD-14と共有の未決境界のまま | Ren | RenCrow_CORE `6a2369ac`（CI: canonical `39734589561` 3 OS success、build `39734589582` success、Public Docs Guard `39734589507` success、direct-chat-regression success） | implemented / verified |
| 2026-10-22 | D-11, D-12, D-18 | 論理場所・資源名だけを持つ仮空間インターフェースで停止・取消し規則の単体試験をPush。`PlanContinuation`／`PlanStop`の決定だけを流し込み、活動の取消しでstudy_seat／pathの占有が残る（取消しと占有解放は別操作）、sleep取消ではposition・占有が一切揺るがない、占有解放はstop actionの後の別capabilityでstop／cleanup actionへ混入しない、いかなる決定もpositionを変えない（移動はR10）を機械的に固定。仮空間は座標・部屋graph・移動operationを持たず、実測geometry（D-17）へ昇格しない。productionコード変更なし | Ren | RenCrow_WORLD `605c6bf`（CI: `39735397687` 3 OS green） | implemented / verified |
| 2026-10-22 | D-11, D-12, D-28 | 保存済みheadの意味評価だけを入力とする純関数`life.StopPlanning`を追加・Push。既存ownerの活動定義表（`StopState`＝`stop_after_completion`／`refuse_stop`）と照合し、`PlanStop`許可／拒否と停止後姿勢を決定するのみで、停止の実行・占有解放・移動はしない（実行はR10 controller）。`GET .../assessment?stop_planning_activity_id=<id>`でread-only公開し、未登録activity IDは拒否、state hash非変更を確認。実WORLD binaryのE2E（`e2e-r08.sh`）にstop-planning blockを追加してPASS。production配備、正式port／TLS、実空間の受入（spatial_ready、AC-004／005／011〜014）とR10 controller実行は未決のまま | Ren | RenCrow_WORLD `ce1ed64`（CI: `39738161818` 3 OS success。ローカルで`go test ./...`・`go vet`・gofmt clean） | implemented / verified |
| 2026-10-22 | D-11, D-12 | 計画決定を消費するR10 controllerロジックを`internal/life`に追加・Push。`ExecuteContinuation`は許可済みstopのactionとowner規則の姿勢だけを論理台帳（活動・論理占有名・姿勢・receipt log）へ適用し、拒否済み／姿勢なし決定はmutationなし、占有解放とPosition変更はしない。`ReleaseOccupancy`はstop action実行後にのみ許可される別capability（実行前解放・二重解放は拒否）。`ExecuteAdmission`はadmit済み一致候補をidle台帳で開始するのみで、拒否候補・実行中・移動要請（D-17未決のためfail closed）・保持中占有の乗っ取りを拒否。runtime route／Event／WORLD State配線はせず、Position不変はテストで固定。`2d8aefc`のCIは新testファイルがcanonical plan未登録で3 OS失敗（`39739409072`）→`2c79f91`で`scripts/test-local.plan.json`へ登録して解決 | Ren | RenCrow_WORLD `2d8aefc` / `2c79f91`（CI: `39739733254` 3 OS success。ローカルで`go test ./...`・`go vet`・gofmt clean、plan全testファイル被覆を照合） | implemented / verified |
| 2026-10-22 | D-11, D-12 | 提示開始・中断・安全停止のEvent／Receipt規則をcanonicalなCommand→Handler→Receipt route上へ実装・Push。`life.activity.start`／`life.activity.stop`／`life.occupancy.release`の3 actionが各自1 Eventと1 State遷移だけをcommitし、payloadは`actor_id`／`activity_id`のみ（姿勢・論理占有名・cleanup actionはWORLD ownerの活動定義表から決まり、呼び出し側にState deltaを選ばせない）。startはidleなActor・登録済みactivity・論理占有名が現行roomと一致するときだけcommitし、移動を要する開始は拒否（D-17）。stopは活動自身の中断規則だけを通し、物理占有は保持したまま（活動の取消しと占有解放は別操作）。解放はstop commit済みを要求される別capabilityで、実行中・保持無し・解放済みの解放は拒否。全ての拒否はtxn・Event・State変更を伴わない`rejected` Receipt、同一idempotency key／bodyは拒否Receiptも含め同一Receiptを再生し第二の効果は出ない。実資源・予約のbind（R10 item 2）は使わず、COREの仕事結果を主張するEventも作らない。runtime routeへのregisterは未実施で、この境界はdocs/R10.mdに文書化のみで機械的強制はない。新test fileは同一commitでcanonical planへ登録済み | Ren | RenCrow_WORLD `86b2fb1`（CI: `39756496598` 3 OS success。ローカルで`go test ./...`・`go vet`・gofmt clean、plan被覆照合でuncovered・duplicate・staleなし） | implemented / verified |
|  |  |  |  |  | decided / implemented / verified |

## 12. 残る決定・確認項目

1. **D-05（解消済み）:** `RenCrow_CORE` のWIPを保持したまま、別worktreeでR08 CORE側source foundationとruntime loopを実装・Pushし、`origin/main` `084fe2af`へmergeした。CORE local main worktreeの83件の未コミットWIPも単位別検証後に`a20e2a24`で統合し、local mainは`origin/main`と同期済み。production配線・受入証拠は別作業。
2. **D-01 / D-02:** 契約所有の分担と、Publisher/Credential/ActorInstanceの分離
3. **D-03 / D-04 / D-19 / D-20:** ACK意味論、再同期権限、head照会、監査記録
4. **D-23:** Command本文の`timeline_epoch`必須化
5. **D-06:** WORLD側の投影実在検査（`CompleteReconcileChecked`と暫定HTTP route、RenCrow_WORLD `3b491e3`／`9ebf057`／`988a352`）と、CORE側のsource epoch切替のreconcile credential分離（RenCrow_CORE `6a2369ac`、loopback隔離試験）は実装済み。残るはcanonical route採用とproduction配備・実障害復帰の受入で、D-14の未決境界と共有する
6. **D-07〜D-13:** 生活意味論と計画層（stale、空Set、期限切れ、fallback subset、安全終了、継続/その場保持、候補選別、admission）、D-13の提示（queued／waiting・blocked／running／presenceのtask ID公開、Chatは投影契約で除外）、stop planningのread-only公開（RenCrow_WORLD `ce1ed64`）、決定を消費して論理台帳（活動・論理占有名・姿勢・receipt）だけを実行するR10 controllerロジック（RenCrow_WORLD `2d8aefc`）は実装済み。残るはruntimeのEvent／WORLD State配線、活動と実資源・予約のバインド、移動（D-17）、実生活適用
7. **D-14:** URL/version/auth/healthの契約を先に固定し、portは配備設定に分けること。loopbackの隔離接続試験は実装・検証済み（RenCrow_CORE `20b4d996`、build tag `realworld`）。port番号の正式決定、canonical route採用、production read bridgeへの配線、正式port／TLSは未決のまま
8. **D-27:** CORE read bridgeのproduction route／DTO、private-room redaction、Observation配信、CORE側Stream route
9. **D-28:** `executable_activity_ids`を消費するR10 controllerとstop planning route、活動と実資源・予約のバインド、移動・占有。assessment routeのcross-repo契約採用はCORE source-level read clientの消費として実装済み（RenCrow_CORE `50942c72`）で、production read bridge routeへの配線は未決
10. **CORE local main（解消済み）:** 83件の未コミットWIPは単位別検証後に`a20e2a24`で`origin/main`へ統合・Pushし、reset・stash・cleanは行っていない。併せて新規test file 9件をWORLD canonical test planへ登録し（RenCrow_WORLD `49f95e9`）、3 OS CIは緑。WIP由来でない間接依存の失敗が残る場合は該当単位として切り分ける。

D-05は解消した。D-25としてCORE Outboxのstate reconciliation方式を、D-26としてLifePolicyのowner入力とactivity ID登録を、D-27としてCOREのWORLD read clientを、D-28としてWORLDのread-only assessment routeを決定・実装し、D-29として独立ConditionProfile ownerの新設を見送り、再評価条件を記録した。COREの`feat/world-r08-publisher`は`origin/main` `084fe2af`へmerge済みである。D-02のproduction identity検証、D-06のCORE側接続、D-07〜D-13の実生活適用、D-14のcanonical route、D-27のCORE read bridge production route、D-28のR10 controllerとproduction read bridge routeへの配線、D-29の再評価条件に該当する体調データownerが現れた場合の分離、production配備・再起動E2Eが残る間、R08の受入とR09/R10の本実装は「LifePolicy導出＋runtime loop＋source-level read client（assessment消費含む）＋WORLD assessment」の範囲を超えない。
