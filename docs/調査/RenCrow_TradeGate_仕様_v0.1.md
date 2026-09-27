# RenCrow TradeGate 仕様書

> **版:** v0.1  
> **日付:** 2026-08-05  
> **状態:** 新仕様案  
> **配置候補:** `docs/10_新仕様/XX_TradeGate仕様.md`  
> **対象:** RenCrow_CORE / PORTAL / CMD / ASSISTANT / 将来の金融系Agent

---

## 0. この仕様を一言で

RenCrowに金融商品を扱わせる。ただし、**LLMやキャラクターが証券APIを直接操作する構造にはしない**。

```text
キャラクターは「考える・説明する・提案する」
TradeGateは「決められたルールを機械的に検査する」
本人だけが「実資金を動かす許可を出す」
```

ユーザー向け機能名は **RenCrow Trade**、実際の注文を守る非LLM実行境界を **TradeGate** と呼ぶ。

---

## 1. 目的

最終的には、RenCrowから本人名義の金融口座を参照し、金融商品の注文、取消、約定確認、ポジション確認を安全に行えるようにする。

最初から完全自律売買を目指さない。次の順で段階的に開放する。

```text
見る
  ↓
注文票を作る
  ↓
模擬口座で練習する
  ↓
本人承認つきで実際に発注する
  ↓
決めたルールの範囲だけ自動化する
  ↓
複数Agentが協議して提案する
```

---

## 2. 最初に固定する原則

### 2.1 絶対条件

1. **初期状態は無効**とする。
2. **本番より先にRead OnlyとPaper Tradingを完成**させる。
3. **証券会社の認証情報をLLM、会話履歴、VectorDBへ渡さない**。
4. **自然文をそのまま証券APIへ送らない**。
5. **実注文は、構造化された注文内容と本人の明示承認が揃った場合だけ送る**。
6. **本人承認後に注文内容が1項目でも変わったら、承認を無効化する**。
7. **APIタイムアウト時に無条件再送しない**。必ず注文照会と突合を行う。
8. **すべての提案、承認、拒否、送信、約定、取消、エラーを追記型ログへ残す**。
9. **Kill Switchで、新規注文を即時停止できる**。
10. **口座残高、ポジション、注文、約定の正本はBrokerまたはTrade Ledger**とし、RenCrowの会話記憶を正本にしない。

### 2.2 初期対象

初期の実注文対象は、本人名義口座の次の範囲に限定する。

- 現物株式
- 現物ETF
- 指値注文
- 当日限り注文
- 明示的な銘柄許可リスト
- 明示的な注文金額上限、日次上限、未約定注文数上限

### 2.3 初期対象外

- 信用取引
- レバレッジ
- 空売り
- オプション
- 先物
- FX
- 暗号資産
- 成行注文
- 時間外取引
- 入出金、振込、出金、資金移動
- 他人や家族の口座
- 他人の認証情報の預かり
- 顧客向け投資助言、コピートレード、資金一任
- Cloudflare Wallet / x402による証券注文

Cloudflare Walletは将来のAPI購入用 `SpendGate` に属し、本仕様の証券注文用 `TradeGate` とは分離する。

---

## 3. 全体構成

```text
本人
  ↓
PORTAL / Mio
  ├─ 注文内容を聞く
  ├─ 正確な注文票を表示する
  ├─ リスク説明を表示する
  └─ 認証済み承認UIを開く
        ↓
TradeProposal / TradeIntent
        ↓
Shiro
  └─ 承認済みIntentをTradeGateへ渡す
        ↓
┌──────────────────────────────┐
│ TradeGate  非LLM・決定論的処理 │
│                              │
│ 1. Mode確認                  │
│ 2. Kill Switch確認           │
│ 3. 口座・商品許可確認         │
│ 4. 数量・金額・回数上限確認   │
│ 5. 市場データ鮮度確認         │
│ 6. 重複注文確認               │
│ 7. Approval署名・期限確認      │
│ 8. BrokerOrder生成            │
└──────────────────────────────┘
        ↓
Broker Adapter
        ↓
証券会社API / Paper Broker / Mock Broker
        ↓
ExecutionReport
        ↓
Trade Ledger + Audit Event
        ↓
Mioが本人へ結果を返す
```

### 3.1 論理分離と物理分離

- `RenCrow_CORE` は会話、提案、承認画面、ルーティングを担当する。
- `TradeGate` はポリシー検査、注文生成、Broker呼び出し、突合を担当する。
- STEP 0からSTEP 3までは同一リポジトリ内の独立モジュールでもよい。
- **LIVEモードを有効にする前に、TradeGateを別プロセスとして分離する**。
- Broker認証情報はTradeGateプロセスだけが保持する。

---

## 4. RenCrow内の役割

| 主体 | 金融機能での責務 | 禁止事項 |
|---|---|---|
| 本人 | ポリシー設定、LIVE開放、実注文の最終承認 | 承認情報の使い回し |
| Mio | 対話、注文票表示、モード表示、結果統合 | 証券API直接実行、自然文だけでLIVE承認 |
| Shiro | 承認済みIntentの実行依頼、結果取得、ログ連携 | ポリシー迂回、承認なし実行 |
| Kuro | 前提、損失要因、データ欠損、異常のレビュー | 最終承認、Broker API実行 |
| Aka / Ao / Gin / Kin | TradeGate自体の設計・実装・テスト提案 | 金融注文の直接実行 |
| 将来のFinance Agent | 調査、戦略案、TradeProposal作成 | TradeIntent、Approval、BrokerOrderの生成 |
| TradeGate | 決定論的リスク検査、注文送信、突合、拒否 | 自由文推論、投資判断 |
| Broker Adapter | 証券会社ごとの差分吸収 | 独自判断、ポリシー変更 |
| Trade Ledger | 金融イベントの正本 | 会話要約での置換 |

Kuroのレビューはリスク説明として重要だが、**LLMレビューの通過は安全性の根拠にはしない**。最終的な機械的拒否権はTradeGateが持つ。

---

## 5. 開発STEP

## STEP 0: 土台だけ作る

### 目的

金融機能をRenCrowへ安全に追加できる形を作る。まだ口座へ接続しない。

### 実装

- `trade.enabled=false`
- `trade.mode=DISABLED`
- Tradeドメイン型
- 状態遷移
- Mock Broker Adapter
- Trade Ledger
- Kill Switch
- 設定ファイル
- 単体テスト

### ユーザーから見えるもの

PORTALまたはCMDで次を確認できる。

```text
RenCrow Trade: DISABLED
Broker: MOCK
Live order: BLOCKED
Kill Switch: ON
```

### 完了条件

- Brokerネットワーク通信が存在しない
- 認証情報を扱わない
- DISABLED時はすべての注文操作が拒否される
- テストからMock注文の状態遷移を再現できる

---

## STEP 1: 見るだけ

### 目的

実口座またはPaper口座の状態を、RenCrowから安全に参照する。

### できること

- 口座種別表示
- 現金・買付余力表示
- ポジション表示
- 未約定注文表示
- 約定履歴表示
- 市場データ表示
- Broker接続状態表示

### できないこと

- 新規注文
- 取消
- 訂正
- 入出金

### 実装条件

- 可能な場合はRead Only資格情報を使用する
- 口座番号は画面とログでマスクする
- 取得時刻とデータ元を必ず表示する
- 記憶DBではなくBrokerまたはTrade Ledgerから毎回取得する

### 完了条件

PORTALで表示された残高、ポジション、注文一覧がBroker側と一致する。

---

## STEP 2: 注文票を作るだけ

### 目的

本人の指示を、曖昧さのない注文票へ変換する。まだ送信しない。

### 会話例

```text
本人:
「○○ETFを1口、上限○円の指値で、今日だけ買う」

Mio:
「次の注文票を作りました。まだ送信していません」

口座       PAPER / LIVE
商品       正規化済み商品ID
売買       BUY
数量       1
注文種別   LIMIT
指値       ○円
有効期限   DAY
概算金額   ○円
価格時刻   2026-08-05 13:00:00 JST
```

### 実装

- 自然文から `TradeProposal` を作る
- 不足項目があれば「未確定」とする
- 商品IDをBroker Adapterで正規化する
- TradeGateのPreviewを通す
- 拒否理由を人間向けに表示する
- `PlaceOrder` は呼ばない

### 完了条件

どの入力でも、未確定項目を勝手に補完せず、送信なしで注文票または拒否理由を返す。

---

## STEP 3: 模擬口座で注文する

### 目的

実資金を使わず、注文ライフサイクルを一周させる。

### 実装対象

- Paper Broker Adapter
- 本人承認UI
- 使い捨てApproval
- 注文送信
- 受付確認
- 未約定
- 部分約定
- 全約定
- 取消
- 拒否
- APIタイムアウト
- UNKNOWN状態
- 再起動後の復元
- Brokerとの突合
- 二重注文防止

### 最初の完成目標

```text
本人がPaper注文を入力
  ↓
Mioが注文票を表示
  ↓
本人が認証済みUIで承認
  ↓
ShiroがTradeGateへ依頼
  ↓
TradeGateが一度だけ送信
  ↓
Broker結果を取得
  ↓
LedgerとBroker状態が一致
  ↓
Mioが結果を返す
```

### 完了条件

- 同じ `client_order_id` で二重発注されない
- タイムアウト後に無条件再送されない
- 部分約定を正しく扱える
- プロセス再起動後も注文状態を復元できる
- BrokerとLedgerの突合結果が一致する
- Kill Switchのテストが通る

**RenCrow Tradeの初期MVPはSTEP 3完了まで**とする。

---

## STEP 4: 本人承認つきで実際に注文する

### 目的

最小範囲で実資金を扱う。

### LIVE開放条件

- STEP 3の全テストが通過済み
- Paperで連続運用する期間が設定・完了済み
- Broker Adapterの仕様と失敗時挙動を確認済み
- 注文金額上限、日次上限、銘柄許可リストが設定済み
- Kill Switchを本人が試験済み
- 秘密情報がログ、会話、DBへ出ていない
- LIVEを有効にする明示操作を本人が行う

### LIVE時の追加条件

- 画面上部へ常時赤い `LIVE` 表示
- チャットでの「はい」だけでは承認しない
- 認証済みの専用承認UIを使用する
- 承認は注文内容のハッシュへ結びつける
- 承認には短い有効期限を設ける
- 注文内容変更後は再承認する
- 初期は現物、指値、DAY、許可銘柄のみ
- 注文ごとに本人承認を要求する

### 完了条件

本人が指定した最小注文を1件だけ送り、注文、約定、手数料、残高、ポジションを突合できる。

---

## STEP 5: 決めたルールの範囲だけ自動化する

### 目的

自由判断ではなく、本人が事前登録したルールだけを自動実行する。

### 許可される形

- `strategy_id` が登録済み
- 対象商品が許可済み
- 注文式が決定論的
- 数量・金額・回数・時間帯の上限が固定
- 日次停止条件が固定
- 変更はバージョン管理され、再承認が必要

### 禁止される形

- LLMが自由文で売買数量を決めて即実行
- ニュースを読んだLLMが独断で発注
- 未登録戦略をその場で作って実行
- 損失後に上限を自動拡大
- Brokerエラー時の無限再試行

### 完了条件

同じ入力と同じ口座状態から、同じ注文結果が再現される。

---

## STEP 6: 複数Agentによる金融協議

### 目的

将来の10人以上の協議基盤へ接続し、複数視点からTradeProposalを作る。

### 協議の出力

各Agentは次だけを返す。

```json
{
  "proposal_id": "tp_...",
  "stance": "support|oppose|abstain",
  "confidence": 0.0,
  "evidence": [],
  "risks": [],
  "invalidation_conditions": [],
  "suggested_action": "hold|watch|create_trade_proposal"
}
```

### 重要な境界

- 協議結果は `TradeProposal` まで
- 多数決や全会一致でもApprovalにはならない
- Agentは `TradeIntent`、`ApprovalGrant`、`BrokerOrder` を作れない
- Mioが意見差分を統合して本人へ提示する
- Kuroは反証と前提監査を担当する
- 本人承認とTradeGate検査は省略できない

---

## 6. 運用モード

| Mode | 口座読取 | 注文票 | 注文送信 | 本人承認 | 自動化 |
|---|---:|---:|---:|---:|---:|
| `DISABLED` | × | × | × | - | × |
| `READ_ONLY` | ○ | × | × | - | × |
| `PREVIEW` | ○ | ○ | × | 任意 | × |
| `PAPER` | ○ | ○ | Paperのみ | 必須 | × |
| `LIVE_APPROVAL` | ○ | ○ | LIVE | 毎回必須 | × |
| `POLICY_AUTO` | ○ | ○ | LIVE | ポリシー定義に従う | 登録戦略のみ |

初期リリースは `DISABLED`、`READ_ONLY`、`PREVIEW`、`PAPER` までとする。

---

## 7. 注文状態

```text
DRAFT
  ↓
REVIEWED
  ↓
AWAITING_APPROVAL
  ├─ REJECTED_BY_USER
  └─ APPROVED
       ↓
VALIDATING
  ├─ REJECTED_BY_POLICY
  └─ SUBMITTING
       ↓
OPEN
  ├─ PARTIALLY_FILLED
  ├─ FILLED
  ├─ CANCELLED
  ├─ REJECTED_BY_BROKER
  └─ UNKNOWN
       ↓
RECONCILED
```

### 状態ルール

- `APPROVED` 後に商品、売買、数量、価格、期限、口座が変わったら `AWAITING_APPROVAL` へ戻す。
- `SUBMITTING` 中のタイムアウトは `UNKNOWN` とする。
- `UNKNOWN` では同一注文を再送しない。
- Broker照会で結果を確認してから `OPEN`、`FILLED`、`REJECTED_BY_BROKER` などへ進める。
- `RECONCILED` はBrokerとLedgerの一致確認済みを表す。

---

## 8. データオブジェクト

### 8.1 MarketSnapshot

```json
{
  "instrument_id": "broker-normalized-id",
  "bid": null,
  "ask": null,
  "last": null,
  "currency": "JPY",
  "source": "broker-or-market-data-provider",
  "observed_at": "2026-08-05T04:00:00Z"
}
```

### 8.2 TradeProposal

Agentまたは本人の指示から作る、まだ実行不能な候補。

```json
{
  "proposal_id": "tp_...",
  "mode": "PAPER",
  "account_ref": "masked-account-ref",
  "instrument_id": "normalized-id",
  "side": "BUY",
  "quantity": "1",
  "order_type": "LIMIT",
  "limit_price": "REQUIRED",
  "time_in_force": "DAY",
  "rationale": "本人が入力した目的、またはAgent提案",
  "evidence_refs": [],
  "market_snapshot_id": "ms_...",
  "expires_at": "...",
  "created_by": "user|agent-id"
}
```

### 8.3 RiskReview

```json
{
  "review_id": "rr_...",
  "proposal_id": "tp_...",
  "reviewer": "kuro|policy-engine",
  "result": "PASS|WARN|BLOCK",
  "reasons": [],
  "missing_data": [],
  "created_at": "..."
}
```

`policy-engine` の `BLOCK` は実行不可。Kuroの結果は本人向けの説明・警告として扱う。

### 8.4 TradeIntent

本人に提示する、項目が確定した実行候補。

```json
{
  "intent_id": "ti_...",
  "proposal_id": "tp_...",
  "exact_order": {},
  "payload_hash": "sha256:...",
  "approval_required": true,
  "expires_at": "..."
}
```

### 8.5 ApprovalGrant

```json
{
  "approval_id": "ap_...",
  "intent_id": "ti_...",
  "payload_hash": "sha256:...",
  "approved_by": "user-id",
  "approved_at": "...",
  "expires_at": "...",
  "single_use": true,
  "auth_context": "passkey|reauth|other"
}
```

### 8.6 ExecutionReport

```json
{
  "client_order_id": "co_...",
  "broker_order_id": "masked-or-encrypted",
  "status": "OPEN|PARTIALLY_FILLED|FILLED|CANCELLED|REJECTED|UNKNOWN",
  "submitted_at": "...",
  "last_checked_at": "...",
  "filled_quantity": "0",
  "average_fill_price": null,
  "fees": null,
  "broker_message": null
}
```

---

## 9. TradeGateの必須検査

TradeGateは次の順で検査する。1件でも失敗したらBrokerへ送らない。

1. `trade.enabled` が有効か
2. Modeが注文送信を許可しているか
3. Kill Switchが解除されているか
4. 対象口座が本人の許可リスト内か
5. 商品クラスが許可されているか
6. 商品IDが許可リスト内か
7. 売買方向が許可されているか
8. 注文種別と有効期限が許可されているか
9. 数量が正数か
10. 指値が有効な刻みか
11. 1注文あたり上限以内か
12. 日次上限以内か
13. 未約定注文数上限以内か
14. 余力があるか
15. MarketSnapshotが存在するか
16. MarketSnapshotが鮮度上限以内か
17. ProposalとIntentの期限が切れていないか
18. Approvalが必要なModeか
19. Approvalの本人、期限、使い捨て状態が正しいか
20. Approvalのpayload hashと現在の注文が一致するか
21. `client_order_id` が未使用か
22. 同一内容の重複注文がないか
23. Broker接続が正常か
24. 監査ログへ事前イベントを書けるか

---

## 10. Broker Adapter

言語実装はRenCrow_COREに合わせ、Goのinterfaceとして定義する。

```go
type BrokerAdapter interface {
    Capabilities(ctx context.Context) (Capabilities, error)
    Health(ctx context.Context) error

    GetAccounts(ctx context.Context) ([]AccountSnapshot, error)
    GetPositions(ctx context.Context, accountRef string) ([]PositionSnapshot, error)
    GetOrders(ctx context.Context, accountRef string) ([]OrderSnapshot, error)
    GetExecutions(ctx context.Context, accountRef string) ([]ExecutionSnapshot, error)
    GetMarketSnapshot(ctx context.Context, instrumentID string) (MarketSnapshot, error)

    NormalizeInstrument(ctx context.Context, input InstrumentInput) (Instrument, error)
    ValidateOrder(ctx context.Context, order BrokerOrder) (BrokerValidation, error)
    PlaceOrder(ctx context.Context, order BrokerOrder) (BrokerAck, error)
    CancelOrder(ctx context.Context, accountRef, brokerOrderID string) (BrokerAck, error)
    GetOrder(ctx context.Context, accountRef, brokerOrderID string) (OrderSnapshot, error)
    FindByClientOrderID(ctx context.Context, accountRef, clientOrderID string) (OrderSnapshot, error)
}
```

### Adapter実装順

```text
MockBroker
  ↓
PaperBroker
  ↓
ReadOnlyLiveBroker
  ↓
LiveBroker
```

Brokerごとに対応商品、注文種別、注文ID仕様、取消仕様、レート制限が異なるため、Capabilitiesを必ず返す。

---

## 11. 設定ファイル

`config/trade.yaml` の例。

```yaml
version: 1

trade:
  enabled: false
  mode: DISABLED
  broker_adapter: mock

  human_approval:
    live: always
    paper: always
    approval_ttl_seconds: REQUIRED
    require_reauthentication: true

  allowed:
    account_refs: []
    asset_classes:
      - cash_equity
      - cash_etf
    instruments: []
    sides:
      - BUY
      - SELL_OWNED
    order_types:
      - LIMIT
    time_in_force:
      - DAY

  prohibited:
    transfer: true
    withdrawal: true
    margin: true
    short_selling: true
    derivatives: true
    fx: true
    crypto: true
    market_order: true
    after_hours: true

  limits:
    max_notional_per_order_jpy: REQUIRED
    max_notional_per_day_jpy: REQUIRED
    max_orders_per_day: REQUIRED
    max_open_orders: REQUIRED
    max_open_positions: REQUIRED

  safety:
    kill_switch: true
    quote_max_age_seconds: REQUIRED
    duplicate_detection: true
    idempotency_required: true
    reconcile_after_submit: true
    reconcile_on_startup: true
    block_on_unknown_state: true
    log_payload_hash: true
    log_secrets: false

  live_gate:
    paper_soak_min_trading_days: REQUIRED
    require_manual_go_live: true
    require_kill_switch_test: true
    require_reconciliation_test: true
    require_secret_scan: true
```

`REQUIRED` は実装時に本人が決める必須項目であり、暗黙の既定値を置かない。

---

## 12. Trade Ledger

金融情報は会話メモリやVectorDBとは分離する。

### 必須テーブル

- `trade_proposals`
- `risk_reviews`
- `trade_intents`
- `approval_grants`
- `broker_orders`
- `execution_reports`
- `position_snapshots`
- `account_snapshots`
- `trade_events`
- `reconciliation_runs`

### trade_events 最小項目

```text
event_id
correlation_id
proposal_id
intent_id
client_order_id
mode
actor_type
actor_id
action
result
reason_code
payload_hash
created_at
```

### 保存原則

- 追記型を基本にする
- 口座IDとBroker Order IDはマスクまたは暗号化する
- 認証情報、アクセストークン、秘密鍵を保存しない
- 会話履歴には注文の要約とLedger参照IDだけを残す
- 残高、ポジション、注文状態をVectorDBから復元しない

MVPではSQLiteを使用してよい。複数ユーザー化または複数TradeGate化する段階でPostgreSQL等へ移行する。

---

## 13. UI仕様

## 13.1 PORTAL

RenCrow Trade画面を追加する。

### 常時表示

- Mode: DISABLED / READ ONLY / PAPER / LIVE
- Broker接続状態
- 取得データ時刻
- Kill Switch状態
- 口座種別

### 注文確認カード

```text
【PAPER / LIVE】
商品
売買
数量
注文種別
指値
有効期限
概算注文金額
概算手数料  取得可能な場合
価格情報の時刻
許可ポリシー
Kuroの警告
TradeGate Preview結果
```

### 承認

- PAPERでも初期は承認を要求する
- LIVEではチャット入力だけで承認しない
- 専用ボタンと再認証を使う
- 承認直前に全項目を再表示する
- 承認後に変更があれば再承認する

## 13.2 CMD

```text
rencrow trade status
rencrow trade accounts
rencrow trade positions
rencrow trade orders
rencrow trade reconcile
rencrow trade audit --correlation-id ...
rencrow trade kill on
rencrow trade kill off
```

`kill off` は強い認証と確認を要求する。

## 13.3 ASSISTANT

初期は通知専用とする。

- 注文受付
- 約定
- 部分約定
- 取消
- 拒否
- UNKNOWN
- Kill Switch発動
- 上限到達

ASSISTANT上でのLIVE承認は初期対象外。PORTALの認証済み承認画面へ誘導する。

---

## 14. セキュリティ要件

1. Broker認証情報はTradeGateの秘密ストアだけに置く。
2. LLMプロンプト、会話ログ、Trace、Errorへ秘密を出さない。
3. TradeGateを専用OSユーザーまたはコンテナで動かす。
4. ネットワーク送信先をBrokerと必要なMarket Dataへ限定する。
5. COREからTradeGateへは構造化APIだけを公開する。
6. TradeGate APIはローカルまたはプライベートネットワークに限定する。
7. LIVE操作は認証済みユーザーだけに許可する。
8. Approvalは使い捨て、期限つき、payload hash固定とする。
9. ログへの秘密混入を自動テストする。
10. サーバ時計のずれを監視する。
11. 起動時に未突合注文を自動検出し、新規注文を必要に応じて停止する。
12. Kill SwitchはLLMを経由せず直接操作できるようにする。

---

## 15. 必須テスト

### Modeと権限

- DISABLEDで全注文拒否
- READ_ONLYで注文・取消拒否
- PAPERがLIVEへ誤送信しない
- LIVE設定がなければLiveBrokerを生成しない

### 注文検査

- 未許可口座
- 未許可商品
- 未許可商品クラス
- 未許可注文種別
- 数量0、負数、形式不正
- 指値なし
- 価格刻み不正
- 注文上限超過
- 日次上限超過
- 余力不足
- 古いMarketSnapshot
- 期限切れProposal / Intent / Approval
- Approval hash不一致

### 注文ライフサイクル

- 正常受付
- Broker拒否
- 未約定
- 部分約定
- 全約定
- 取消
- 取消失敗
- 送信前タイムアウト
- 送信後タイムアウト
- UNKNOWNからの突合
- プロセス再起動
- Brokerとの状態不一致

### 二重発注防止

- 同一client_order_id再送
- 同一Approval再利用
- 連打
- ネットワーク再送
- Worker再試行
- TradeGate再起動後の再実行

### 安全停止

- Kill Switch ON時の拒否
- 注文承認後、送信前にKill Switch ON
- UNKNOWN状態中の新規注文制限
- Ledger書込み失敗時の送信拒否

---

## 16. ディレクトリ案

### RenCrow_CORE

```text
RenCrow_CORE/
├─ config/
│  └─ trade.yaml
├─ docs/10_新仕様/
│  └─ XX_TradeGate仕様.md
├─ internal/domain/trade/
│  ├─ proposal.go
│  ├─ intent.go
│  ├─ approval.go
│  ├─ order.go
│  ├─ execution.go
│  ├─ policy.go
│  └─ state.go
├─ internal/application/trade/
│  ├─ preview_service.go
│  ├─ approval_service.go
│  ├─ execution_client.go
│  └─ query_service.go
├─ internal/interface/http/trade/
│  ├─ handlers.go
│  └─ dto.go
└─ internal/interface/cmd/trade/
   └─ commands.go
```

### TradeGate

```text
RenCrow_TRADE_GATE/
├─ cmd/tradegate/
├─ internal/policy/
├─ internal/approval/
├─ internal/idempotency/
├─ internal/reconciliation/
├─ internal/ledger/
├─ internal/broker/
│  ├─ adapter.go
│  ├─ mock/
│  ├─ paper/
│  └─ live/
├─ internal/api/
├─ config/
└─ tests/
```

STEP 0からSTEP 3までは、`RenCrow_CORE/internal/tradegate/` として実装してもよい。LIVE前に別プロセスへ切り出せるinterface境界を維持する。

---

## 17. API案

```text
GET  /trade/status
GET  /trade/accounts
GET  /trade/positions
GET  /trade/orders
GET  /trade/executions

POST /trade/proposals
POST /trade/proposals/{id}/preview
POST /trade/proposals/{id}/create-intent
POST /trade/intents/{id}/approve
POST /trade/intents/{id}/execute
POST /trade/orders/{id}/cancel
POST /trade/reconcile
POST /trade/kill-switch
```

### API原則

- `execute` はApproval IDを必須とする
- Approvalの内容とIntent hashを再検証する
- `execute` はidempotentにする
- `execute` の応答が不明でも再送せず、照会APIへ移る
- Modeをすべての応答へ含める

---

## 18. 正本と記憶の関係

```text
金融の正本
  Broker + Trade Ledger

会話の正本
  RenCrowの会話・記憶基盤
```

RenCrowのL0からL3へ保存してよいのは、次のような要約だけとする。

```text
「2026-08-05、Paper口座で注文テストを実施。client_order_id=co_xxx。結果はFILLED。詳細はTrade Ledger参照。」
```

保存してはいけないもの。

- Broker秘密情報
- 完全な口座番号
- 認証トークン
- Approval秘密
- Ledgerの代替となる残高やポジションのコピー

---

## 19. 実装の最初の一区切り

最初に実装するのはSTEP 0からSTEP 3まで。

```text
第1区切り
  STEP 0  Tradeドメイン、Mock、Ledger、Kill Switch

第2区切り
  STEP 1  Read Only口座・ポジション表示

第3区切り
  STEP 2  注文票作成とPreview

第4区切り
  STEP 3  Paper注文、取消、部分約定、突合
```

ここまで完成してから、STEP 4のLIVE接続を別のGo / No-Go判断として扱う。

---

## 20. 未決事項

次は実装前または該当STEP到達時に決める。

| 項目 | 決定時期 |
|---|---|
| 最初のBroker / Paper環境 | STEP 1前 |
| 最初の対象市場・商品クラス | STEP 1前 |
| 1注文上限、日次上限、注文回数上限 | STEP 3前 |
| Approvalの再認証方式 | STEP 3前 |
| MarketSnapshot鮮度上限 | STEP 3前 |
| Paper連続運用日数 | STEP 4前 |
| LIVE用TradeGate配置先 | STEP 4前 |
| Trade LedgerをSQLiteから移行する条件 | 複数ユーザー化前 |
| Finance Agentの役割と協議方式 | STEP 6前 |

---

## 21. この仕様の最終判断

RenCrowへ金融商品操作を追加する際、中心に置くのは「儲かるAI」ではない。

最初の完成形は、次を保証するシステムである。

```text
本人が内容を確認した
正確に同じ内容が承認された
TradeGateが機械的に検査した
一度だけBrokerへ送られた
結果がLedgerへ記録された
BrokerとLedgerが一致した
```

この一本道が完成してから、戦略、協議、自動化を載せる。
