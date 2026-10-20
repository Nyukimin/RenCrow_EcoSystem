# WORLD v1.4.0 統合境界と実装順

**状態:** 設計採用・製品未実装。2026-10-20 の統合仕様を、既存 owner の将来設計として取り込む。現行の稼働状態、source pin、配備、作品正史の採用を変更しない。

## 出典と採用範囲

- 入力は 206 の `RenCrow/Tmp/WORLD/WORLD_実装仕様一式_v1.4.0_20261020.zip`。SHA-256 は `f5e69cdca00e3551656dcd5839355802b9cebf03989d778861f176b90907559f`。入口は ZIP 内の `WORLD_v1.4.0/README.md` と `WORLD_Integrated_Spec_v1.4.0.md`。
- 同梱の `inputs/` は原資料 291 ファイルであり、現在の owner 仕様へ一括昇格しない。ZIP の静的検証報告は 84/84 合格、原資料 291 ファイルのハッシュは本作業で目録と照合して一致した。実装受入 `W14-AC-001`〜`024` は全件 `not_run`。
- 採用するのは共通 WORLD Kernel と独立した World/Timeline、WORLD・CORE・StoryPlayer・PORTAL の所有境界、段階的実装順、実機受入条件。作品の候補設定、実験仮定、参考画像、試験 fixture は作者承認や runtime 公開を意味しない。
- WORLD 内部の実装契約は [WORLD の v1.4.0 実装仕様](../RenCrow_WORLD/docs/implementation-spec-v1.4.md)が所有する。既存の [R05 仕様](../RenCrow_WORLD/docs/R05.md) は現在実装された `inspect` の契約として維持する。[StoryPlayer 内部の実装契約](../RenCrow_StoryPlayer/docs/implementation-spec-v1.4.md)は独立した StoryPlayer repository が所有する。CORE と PORTAL の内部契約は各 owner 仕様を参照する。

## Owner と依存方向

| 領域 | 所有する正本・操作 | 統合時の境界 |
| --- | --- | --- |
| WORLD | 世界定義、World/Timeline 内の状態と確定 Event、時間、位置・占有、Command/Receipt、Snapshot | 共通 Kernel は法則や住人を固定せず、各 World Profile と権限を分離する。CORE 人格・記憶・作品原稿を保存しない |
| CORE | 認証済み実 Actor、Persona、意思決定、Task/Run、会話、本人の記憶・認識 | LifePolicy/WorkSet の投影と WORLD の読取を owner 経路で行う。認知結果や実仕事の成功を WORLD の演出から推測しない |
| StoryPlayer | 物語の Authoring/Narrative Manager、Producer/Validator、Renderer/Playback | 世界の事実は固定した WORLD 参照から受け、原稿・配役・演出・作品内正史を管理する。Renderer は世界・記憶へ書き戻さない |
| PORTAL | LCP・仕事場・Main/PinP の描画と同一ブラウザ内の音声再生 | 認証済み CORE read bridge を通し、二視点は同じ状態を表示する。Mock を本番 Snapshot として扱わない |
| EcoSystem | owner 間の接続方向、実装順、統合受入と組合せ状態 | 各 module の DTO、保存形式、内蔵仕様を複製しない |

`rencrow-home` と異世界作品の World は Kernel を共有できるが、WorldID、Timeline、Store、認可、正史、本人の経験記憶を共有しない。同じ人格の定義を作品で参照しても、別 Timeline の経験を自動で本人の Live 記憶へ移さない。公開した世界定義、稼働 Timeline への適用、作品正史採用、Presentation Package 公開はそれぞれ別の操作と証拠を持つ。

StoryPlayer の独立 owner はユーザー指定の [`RenCrow_StoryPlayer`](../RenCrow_StoryPlayer/README.md) で、catalog manifest に planned module として登録する。`appendices/02_StoryPlayer_Integration.md` と `contracts/storyplayer_contract.md` の内部 Authoring・Package・Playback 仕様は同 repository の実装仕様へ採用し、WORLD または catalog に第二正本を作らない。旧 v0.1 の「表出専用」は Renderer/Playback 層の制約として継承し、StoryPlayer 全体の制作責務には広げない。runtime source、配備、正式 Package の完成は未確認である。

## 現行実装との境界

- WORLD は R05 の純 Go domain と単発 `inspect` まで source 実装済み。R05 の 8 resident ID、Unicode を許す入力 ID、`world_revision=0`、`spatial_ready=false` はそのまま保持する。v1.4.0 の通信 ID、`world_spec_revision`、`timeline_epoch`、`event_seq/state_seq`、閲覧用 `view_cursor` は将来の別版契約であり、R05 出力を本番 Snapshot に読み替えない。
- HOUSE の `mio/shiro/kuro/midori/aka/ao/kin/gin` は WORLD 内の住人・個体として区別する。CORE の実 Actor は現行仕様どおり Mio/Shiro/Kuro/Midori。四神を WORLD に表示することは、Coder slot に認証済み CORE Actor 権限や独立した意思決定・発話権限を与えない。ZIP 付録の「四神が独立 Actor」と現行 CORE 仕様の差は、実 Actor 権限を拡張する前に CORE owner で解決する。
- CORE/PORTAL の R04 `r04.mock.v1` は別の Mock PoC。正式な WORLD 認証 API、CORE の投影・read bridge、PORTAL の本番 view へ暗黙に昇格させない。Viewer は権限別の不透明な cursor と投影差分で私的 Event を隠す。
- `docs/world-redesign-r04-integration.md` の 2026-10-16 記録は当時の証拠として保持する。その時点の「両 PoC まで永続 DB を開始しない」は、後続の ZIP 内 `inputs/rencrow_final_20261019/docs/09_実装手順.md` §Gate A に従い、**独立した幾何 PoC が成立した後なら EventStore Unit に着手でき、最終美術 ArtGate は R14 に残す**という計画へ更新する。本書は幾何 PoC の合格や R06 着手可能を認定しない。

## 実装と受入の順序

1. R00/R01: 現行 HEAD、稼働物、既存差分、owner DTO、認証・policy、幾何 PoC の証拠を照合する。R04/R05 は再作成せず回帰を保護する。
2. R06: WORLD が Event/State/Receipt/予約を一つの確定境界で永続化し、再生・Snapshot・crash 復旧を実装する。続いて R07 の認証 API と lifecycle を実装する。
3. R08/R09: CORE が自分の正本から LifePolicy/WorkSet を投影し、WORLD を read bridge で参照する。実 Actor、Task、Memory と WORLD の事実を混同しない。
4. R10/R11: WORLD が許可済み非認知生活と HOUSE 空間・占有を進める。CORE 停止時も架空の会話・仕事成功を生成しない。
5. R12 以降: PORTAL の同一状態二視点と StoryPlayer の最小 Package 接続を owner 別に実装する。R14 美術、R20〜R22 配備・復旧・実機 E2E は独立 Gate とする。

受入 ID は ZIP の `contracts/acceptance_matrix.json` を固定参照する。`W14-AC-001`〜`010` は WORLD Kernel/保存・競合、`011`〜`014` は CORE 連携と生活、`015`〜`020` は配信・観測・分岐隔離、`021`〜`024` は報告・StoryPlayer・PORTAL/HOUSE を横断する。各 owner の関連 test に加え、認証済み実 Actor と正規 route、restart 後の状態、利用者に見える結果まで確認して初めて運用受入とする。静的 Schema 合格や Mock 表示は代用にならない。

原資料にある実装担当モデル名や作業指示は設計出典としてのみ扱う。現在の開発役割・権限・Check Plan は repository の `AGENTS.md` と owner の現行手順に従う。製品 runtime に人の承認待ち queue を新設せず、作者による採用は認証済みの新しい操作として記録する。
