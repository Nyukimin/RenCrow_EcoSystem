# RenCrow TradeGate 実装引継ぎプロンプト

以下をRenCrow_COREの実装担当へそのまま渡す。

---

RenCrow_COREに、金融商品操作のための新サブシステム `RenCrow Trade / TradeGate` を追加してください。

最初に `RenCrow_TradeGate_仕様_v0.1.md` を全文読み、既存の正本仕様、実装仕様、Chat / Worker / Coder境界、Event Log、設定方式、HTTP API、CMD、PORTALの実装規約を確認してください。

## 今回の実装範囲

**STEP 0だけを実装してください。実Broker、Paper Broker、LIVE注文は実装禁止です。**

実装するものは次です。

1. `trade.enabled=false`、`trade.mode=DISABLED` を既定値とする設定
2. Tradeドメイン型
   - TradeProposal
   - RiskReview
   - TradeIntent
   - ApprovalGrant
   - BrokerOrder
   - ExecutionReport
   - TradeEvent
3. 注文状態機械
4. MockBroker Adapter
5. BrokerAdapter interface
6. 決定論的Policy Engineの骨組み
7. Kill Switch
8. SQLiteベースの追記型Trade Ledger
9. idempotency用 `client_order_id`
10. Reconciliation interfaceの骨組み
11. `rencrow trade status` 相当のCMDまたは既存CMDへの追加
12. `/trade/status` 相当のread-only endpoint
13. 単体テストと統合テスト
14. 仕様書を `docs/10_新仕様/` に配置し、実装項目インベントリへ追記

## 厳守事項

- Brokerへのネットワーク通信を追加しない
- Broker名やSDKへ依存しない
- 認証情報の設定項目をまだ追加しない
- LLMからBrokerAdapterを直接呼べる構造にしない
- 自然文をBrokerOrderへ直接変換しない
- Coderはproposal / patchを返し、適用とテストはWorkerの責務とする
- 既存アーキテクチャと命名規則を優先する
- 既存テストを壊さない
- 破壊的変更をしない
- `DISABLED` 時はすべての注文系操作が必ず拒否されることをテストする
- Ledger書込みに失敗した場合は実行処理が進まない設計にする
- 秘密情報が入りうるフィールドをログへ出さない

## 期待する成果物

- 変更ファイル一覧
- アーキテクチャ説明
- 実装した型と状態遷移
- 設定差分
- API / CMD差分
- テスト一覧と結果
- 未実装項目
- STEP 1へ進む際の前提条件

## 完了条件

次をすべて満たした時だけ完了としてください。

- `trade.enabled=false` で起動する
- `DISABLED` と表示される
- MockBroker以外のAdapterが存在しない
- Brokerネットワーク通信がゼロ
- 注文要求が必ず拒否される
- 状態遷移テストが通る
- idempotencyテストが通る
- Kill Switchテストが通る
- Trade Ledgerの追記・読取テストが通る
- 既存テストが通る

実装後に勝手にSTEP 1以降へ進めないでください。
