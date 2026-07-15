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
- CORE が clean environment で起動し health check を通る。
- required user flow を最低 1 回 end-to-end で確認する。
- optional component は「install したもの」ごとに接続・失敗時表示を確認する。
- secret、runtime state、生成物を release source に含めない。
- rollback 先となる直前の verified manifest を保持する。

health success だけで音声再生、認識、画像解析、game bridge などの利用可能性を
主張しません。各 capability は実際の入出力まで確認します。
