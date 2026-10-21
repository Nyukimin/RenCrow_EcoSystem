# WORLD R08–R10 未決事項とルミナ決定案

- 作成日: 2026-10-20
- 状態: **ルミナ決定案に基づくWORLD側実装とCORE側source foundation＋runtime loop＋WORLD read client sourceを反映。CORE OutboxはTask store commitを正本とするstate reconciliation方式、LifePolicyはAgentProfile／Personaからのowner導出方式、COREのWORLD readはexact scope＋Actor allowlist＋cursor resync方式、WORLDのassessmentはbound CORE Actor向けread-only route方式に決定・実装。CORE read bridgeのproduction route、canonical route・実測geometry・production E2Eは未決。**
- 対象: `RenCrow_WORLD` R08 projection inbox、R09/R10 CORE bridge・生活行動、R11/R14前提のgeometry、WORLD runtime route
- 関連: [WORLD R08](../RenCrow_WORLD/docs/R08.md)、[WORLD R07](../RenCrow_WORLD/docs/R07.md)、[WORLD R06](../RenCrow_WORLD/docs/R06.md)、[ID互換性](../RenCrow_WORLD/docs/ID.md)、[v1.4実装仕様](../RenCrow_WORLD/docs/implementation-spec-v1.4.md)

## 0. この文書の位置づけ

R08のWORLD側source foundationに加え、接続契約の補強、復元後のchecked reconcile、R09の意味層、R10の部分的なpresentation/stop planningまで実装・Push・検証した。CORE側もWorkSet v2／LifePolicy payload、HTTP publisher、SQLite durable outbox、durable source revision、内容digest比較でrevision消費を抑えるfull WorkSet projector、`world_projection` configからのruntime loop、Task commit observerによる即時再同期、起動時full再同期を別worktreeで実装・Pushし、実WORLD binaryとのcross-repo E2Eと実Task storeを使うruntime起動テストを確認した。COREのOutboxはTask store transactionを正本とする派生deliveryとし、同一transactionでOutbox行を追記しない方式をD-25として決定した。LifePolicyはCOREのAgentProfile非認知activity envelopeとPersona CharacterProfileのcanonical hashから導出する方式をD-26として決定・実装した。COREのWORLD read clientは、exact World／Timeline／`timeline_epoch` scope、Bearer credential、Snapshotのstate hash、whole-transaction cursor、Actor allowlist、allowlist外Actor Eventのpayload非公開、cursor resync分類をD-27として決定・実装し、実WORLD binaryとのE2Eを確認した。WORLDは、operator-authorized `core_projection_actors`に含まれるActorについて、保存済みWorkSet／LifePolicy headの意味評価をread-only assessment routeで返す方式をD-28として決定・実装し、実WORLD binaryのE2Eを確認した。ただし、CORE read bridgeのproduction route／DTO、WORLD側catalogのR10 controller接続、canonical route、実測geometry、R10の実際の移動・占有、production配備・実network・再起動を含むCORE runtime全体のE2Eは未決のため、受入matrixのAC-004/005/011/012/013/014は `not_run` のままである。

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
| D-06 | 復元後のCommand開放はWORLDが投影実在を検査する | WORLD側実装済み / 暫定HTTP公開済み | WORLD + CORE | P1 |
| D-07 | 期限切れWorkSetはunknown。成功・完了・割当なしを推定しない | 意味層実装済み | WORLD | P1 |
| D-08 | 空WorkSetは「現在割当なし」。成功に変換しない | 意味層実装済み | WORLD + CORE | P1 |
| D-09 | LifePolicy期限切れは明示fallbackだけ。なければblocked | 意味層実装済み | WORLD + CORE | P1 |
| D-10 | fallback ⊆ allowed、かつ登録済み非認知活動だけ許可 | 検証・実行時filter実装済み | CORE + WORLD | P1 |
| D-11 | 新規活動の停止と、実行中活動の安全な終了を分ける | 計画層実装済み / 運動未実装 | WORLD | P2 |
| D-12 | queued/running/presenceに応じて移動・姿勢を決める | presentation判定実装済み / 移動未実装 | WORLD + CORE | P2 |
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

返却するのは`work_set_state`、`policy_state`、`work_presentation`、`permitted_activity_ids`、`new_activity_allowed`、`blocked_reason`、`work_success`、`assessed_at`である。`permitted_activity_ids`は`DefaultCatalog`に登録されたIDだけを昇順で返し、未登録IDは除外する。`work_success`は常に`false`で、空WorkSetを成功に変換しない。routeはActivityを選択・開始せず、移動・占有を計画せず、Event／State／Command Receiptを生成しない。

これはWORLD内の暫定routeであり、COREのproduction read bridge routeでもcanonical cross-module contractでもない。COREはまだこのrouteを消費しない。Stop planningのHTTP/CLI route、Activity selection、R10 controller、移動・占有は未実装である。

証拠: RenCrow_WORLD `487ad00`の`TestAssessment...`（auth、missing head、catalog filter、expired fallback、presentation、state不変、GET限定）、`go test ./...`、`go test -race ./internal/httpapi`、実WORLD binaryを使う`scripts/e2e-r08.sh`のassessment assertion。

## 3. 復元後の再同期

対象: D-06、D-23

### D-06 「何が揃ったか」をWORLDが検査する

現在の`CompleteReconcile`はepoch状態を確認して再同期済みフラグを立てるが、WorkSetやLifePolicyが実際に揃っているかは検査していない。基礎APIとしては理解できるが、そのまま外部へ開放しない。

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
| `condition_profile_ref` | AgentProfileのcanonical JSON SHA-256。現在のprofile内容への参照であり、体調そのもののownerを新設した意味ではない |
| 投影単位 | WorkSetとLifePolicyは別kind・別source revision。内容digestが同じでvalidityが十分ならrevisionを消費しない |
| 起動条件 | `world_projection.life_policy_enabled`は既定true。有効時、設定Actorの`characters/<actor>/` bundleがなければ起動を失敗させる |

実装証拠はCORE `6dc61da9`、WORLD `54ad10c`。COREの`TestRealWorldProjectorProjectsDerivedLifePolicy`は実WORLD binaryへWorkSetとLifePolicyを送り、LifePolicy headのrevision/digest一致、再同期時のskip、Persona変更後のLifePolicy revision 2を確認する。CORE runtime testは実Task storeとcharacter bundleからLifePolicyを生成し、character bundle欠落時の起動失敗も確認する。WORLDの`TestDefaultCatalogRegistersCOREActivityVocabulary`と`TestAssessAcceptsRegisteredLifePolicyVocabulary`は8 IDの登録とassessmentを確認する。

未完了は、WORLD catalogをR10 controllerへ接続すること、Persona／AgentProfile変更のruntime中reload、production configでのcharacter bundle配備、体調・稼働可否を独立ownerとして扱うかどうかである。`condition_profile_ref`は現時点でAgentProfile全体のhashであり、ConditionProfile ownerの実装を意味しない。

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

2026-10-20にCORE/CMDのWIPを読み取り確認した。CORE mainは58 modified / 46 untracked（重複排除後104 path）で、`origin/main`より10 commit遅れており、12 pathが上流変更と重なる。元worktreeはreset・stash・cleanせず、`origin/main` `7de8891a` から `Tmp/worktrees/core-r08-publisher`（branch `feat/world-r08-publisher`）を作成してsource foundationを実装した。CORE/CMDのWIPは変更・統合していない。ユーザーの「おまかせ」をD-05の別worktree実装の許可として扱い、他の未決事項の決定とは分離した。

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
| CORE WORLD read client | 未実装 | 認証済みR07 Snapshot／Event read clientを実装。exact scope、state hash、whole-transaction cursor、Actor allowlist、top-level `actor_id` Eventのscope判定、resync分類、実WORLD E2Eを確認。production CORE route／DTOは未決 |
| WORLD assessment route | 未実装 | bound CORE Actor向けのread-only assessment routeを実装。`read` scope、missing／expired／fresh、DefaultCatalogによる未登録ID除外、presentation、`work_success=false`、state不変、実WORLD binary E2Eを確認。暫定routeでCORE未消費 |
| 復元後のCommand開放 | `CompleteReconcile`は投影未検査 | `CompleteReconcileChecked`を実装 |
| Commandの宛先epoch | 本文にない | 必須化 |
| health | Store/Timeline中心 | live / store_ready / logical_ready / reconciled / spatial_readyを分離。spatialは未実測 |
| fallback subset | 未強制 | 検証時と実行時に強制 |
| 生活行動・中断 | 未実装 | 意味層とstop planを実装。移動・占有は未実装 |

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
|  |  |  |  |  | decided / implemented / verified |

## 12. 残る決定・確認項目

1. **D-05（解消済み）:** `RenCrow_CORE` のWIPを保持したまま、別worktreeでR08 CORE側source foundationとruntime loopを実装・Pushした。production配線・受入証拠は別作業。
2. **D-01 / D-02:** 契約所有の分担と、Publisher/Credential/ActorInstanceの分離
3. **D-03 / D-04 / D-19 / D-20:** ACK意味論、再同期権限、head照会、監査記録
4. **D-23:** Command本文の`timeline_epoch`必須化
5. **D-06:** 復元後のCommand開放を投影実在検査付きにするか
6. **D-07〜D-13:** 生活意味論（stale、空Set、fallback subset、安全終了、queued/running/Chat）
7. **D-14:** URL/version/auth/healthの契約を先に固定し、portは配備設定に分けること
8. **D-27:** CORE read bridgeのproduction route／DTO、private-room redaction、Observation配信、CORE側Stream route
9. **D-28:** assessment routeのcross-repo契約採用、Activity selection／R10 controller、stop planning route、移動・占有

D-05は解消した。D-25としてCORE Outboxのstate reconciliation方式を、D-26としてLifePolicyのowner入力とactivity ID登録を、D-27としてCOREのWORLD read clientを、D-28としてWORLDのread-only assessment routeを決定・実装した。D-02のproduction identity検証、D-06のCORE側接続、D-07〜D-13の実生活適用、D-14のcanonical route、D-27のCORE read bridge production route、D-28のcross-repo契約採用とR10 controller、production配備・再起動E2Eが残る間、R08の受入とR09/R10の本実装は「LifePolicy導出＋runtime loop＋source-level read client＋WORLD assessment」の範囲を超えない。
