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

## PORTAL and CORE acceptance

PORTALを含む組み合わせでは、一般的なminimum acceptanceに加えて次を確認します。

- `view`／`live`のwrite拒否と、`lab`の明示allowlistを確認する。
- recipient切替通知と、実際のmessage `to`が一致することを確認する。
- TTSのaudio owner取得、SSE audio、音声取得、browser再生、playback ACKを
  別々のcheckpointとして確認する。
- STTのinput owner取得、WebSocket upgrade、音声送信、STT target接続、最終認識を
  別々のcheckpointとして確認する。
- TTS／STT target停止時に失敗表示とowner解放を確認する。
- Debug／admin、cross-origin control、設定外TTS audio hostが拒否されることを確認する。

詳細な接続契約と確認項目は[PORTAL–CORE contract](portal-core-contract.md)を参照してください。

## ASSISTANT acceptance

ASSISTANTを含む組み合わせでは、一般的なminimum acceptanceに加えて次を確認します。

- 生活Routineが指定時刻・条件で一度だけ発火し、重複deliveryを起こさない。
- acknowledgement、snooze、missed、retry、別端末への切替を追跡できる。
- personal data、`family:shared`、別利用者のprivate dataが権限どおりに分離される。
- COREへのTask昇格で利用者scopeと相関IDが維持され、結果が元のdeliveryへ戻る。
- CORE停止時にAgent処理をdegradedとし、決定論的Routineとcache済み情報の状態を区別する。
- 実際のDevice clientでPUSH、表示または発話、利用者応答までend-to-endで確認する。

詳細な境界は[ASSISTANT boundary](assistant-boundary.md)、module固有の仕様と実装状態は
`Nyukimin/RenCrow_ASSISTANT`の`docs/`を参照してください。
