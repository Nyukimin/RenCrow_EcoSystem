# 共通・module固有ルールの配置

## 正本と読込条件

| 種類 | 正本 | 読込条件 |
|---|---|---|
| 全repository共通の作業方針 | EcoSystem `AGENTS.md` | 常時。global／workspace入口から一度 |
| 共通の作業別手順 | EcoSystem `docs/agent-task-rules.md` | 共通入口の条件に一致する節だけ |
| moduleの所有範囲と索引 | 各repository `AGENTS.md` | 対象moduleを扱うとき |
| module固有の制約・手順 | 各repository `rules/task-rules.md`と既存domain rules | module入口の条件に一致する節だけ、着手前 |
| catalog自身の固有制約 | EcoSystem `rules/catalog.md` | manifest／pin／配布／release作業時 |
| Codexのcatalog固有入口 | EcoSystem `AGENTS.override.md` | catalogを起動位置にしたとき。globalの共通本文を再投入しない |
| Claude／Cursorの入口 | 正本への参照 | 本文を複製しない |

「共通か固有か」は適用対象で決める。同じ文章をmoduleごとに持たない。固有詳細を共通AGENTSへ詰め込まず、共通手順をmodule側で再定義しない。文書全体を毎回読む運用へ戻さず、入口に「何をするときに、どの節を読むか」を残す。横断変更は対象ownerと必要な依存先の規定だけを読む。

製品仕様の正本と作業ルールは分ける。moduleの現行仕様索引を複製しない。旧model役割は残さず、Codexの分担は共通正本だけで決める。モデル・推論強度・委譲量・検査集合の最適化は本変更の対象外。

## 配布と検証

既存の`rencrow-bootstrap rules`で共通snapshotを同期し、端末のglobal参照を確認する。各moduleの入口・詳細は当該repositoryの同じ変更単位で配布する。snapshot単体を全ルールの配布完了としない。

catalogがworkspace rootの配置と、workspace直下にEcoSystemを置く配置を区別する。moduleの`../AGENTS.md`が共通正本を指さない場合はglobal設定／manifestに隣接するEcoSystemの正本へ解決する。Codexではglobal参照がmodule単独起動でも有効なことを`debug prompt-input`で検証する。既存タスクの古い履歴の置換は、新processの検査と分けて扱う。

catalog直下ではglobal参照とlocal AGENTSから同じ共通本文が重複し得るため、local入口に`AGENTS.override.md`を使う。共通の正本は引き続きAGENTS.mdであり、配布CLIのsourceやsnapshot契約を変更しない。overrideはcatalogのcheckoutに含め、global未設定なら共通正本を先に読む条件を残す。moduleの入口をoverrideで置き換えたり、globalの人格指示を無断で上書きしたりしない。

検証は、旧規定の移動先・共通への統合先、条件付き参照とanchor、旧モデル指示の不存在、snapshot一致、実起動位置での入力を確認する。byte数の減少を週間利用枠や作業成果当たりの削減率へ換算しない。
