# Host 207 transition — 2026-10-25

利用者の指示により、COREとPORTALのメインhostをUbuntu host 206からmacOSのM5 Mac
host 207へ移設した。本文は配置と観測結果の記録であり、各ownerの製品契約やMigration
Artifactの受入を置き換えない。host固有の設定、認証情報、DB、復旧image、runtime logはGit外に保持する。

## 現行配置

| 対象 | 配置・接続 |
| --- | --- |
| CORE | host 207、native Go darwin/arm64、port 18790 |
| PORTAL | host 207、native Go darwin/arm64、loopback port 18791。Tailscale Serve経由の認証境界を維持 |
| 旧CORE入口 | host 206の18790を207へ転送。旧CORE serviceの自動起動は無効化 |
| 旧PORTAL入口 | host 206のloopback 18791をSSH reverse tunnelで207へ転送。旧PORTAL serviceは停止・無効化 |
| LLM Gateway | host 206を維持し、207のloopback 8090からSSH tunnel経由で利用 |
| 記憶の外部store | host 206のRedis／QdrantをSSH tunnel経由で利用。COREのowner境界は変更しない |
| capability service | STT／TTSは207上の既存Gateway、Vision等の206上のserviceはSSH tunnelで接続 |
| runtime Workspace | host 207の`<HOME>/.rencrow/workspace`を現行正本とする |
| COREの稼働データ | host 207の明示設定先`<HOME>/RenCrowData/db/core`。旧HDDは変更せず保持 |

207のCORE、PORTAL、追加の接続tunnelはlaunchdのGUI LaunchAgentで監視する。
旧206の入口は互換用であり、第二のCOREやPORTAL instanceではない。旧アドレスを使うclientも
207の同じruntimeへ到達する。203、204、205、206には新しい配置とreadiness確認先の案内を保存した。

## 確認結果

2026-10-25 15:39 JST時点で次を確認した。

- COREの`/health`はHTTP 200、`ok: true`、`service: rencrow-core`。
- 203、204、205、206から207のCOREへ接続し、すべて`status: ok`。
- 206の旧CORE入口も同じCOREのhealthを返す。
- 新旧のTailscale PORTAL入口は`/health/ready`でHTTP 200、`status: ready`。
- 新PORTALのChat pageはHTTP 200。認証なしのloopback page要求はHTTP 401。
- Mio、Shiro、Kuro、Midori、WorkerのLLM Gateway readiness、Vision、永続化queue、Action storeはCORE healthで正常。
- 配置binaryのGo build情報はCORE `f5373182e692abbf7be3fb872d1f5dadce4ec1bd`、
  PORTAL `3bde947713a74581214a7b8a72f0d32a3d4ae589`、いずれも`vcs.modified=false`。

これらはservice readinessの証拠であり、実会話・音声再生・生成・全AgentのTask実行を通した
canonical E2E成功ではない。設定、source revision、接続先、認証、データの変更時は関連項目を再確認する。

## HDD復旧とデータの受入境界

Ubuntuで使用していた2 TBのExt4媒体2基を207へ移した。データ媒体にはjournal回復要求があり、
元媒体を読み取り専用で参照してCOREの既存DB、現在のsession、記憶の参照元を取り出した。
元媒体のformat、filesystem修復、上書きは行っていない。未完了更新の破棄は利用者の指示による。

- 設定済みDBは21個。19個はそのままSQLite整合性検査を通過した。
- 人格ログと作業履歴の2 DBはコピー上で再構築し、再構築後の整合性検査を通過した。
  元媒体、取り出した原本、再構築前の作業用コピーはGit外に保持した。
- 現在のsession JSON 43ファイルをparseでき、記憶の参照元1770 objectは保存名とSHA-256が一致した。
- 稼働Workspaceのportable non-secret allowlistは、Workspace所有CLIで207から取得した。
  既存のGit snapshotと内容が一致し、runtime StateやsecretをGitへ取り込んでいない。

DB整合性検査は履歴の完全性を保証しない。特に再構築した2 DBについて、失われたrecordの有無や
件数は未確定。HDD全体の作業用image取得は別工程であり、CORE起動時点では進行中だった。

## 残る受入

- 再構築した履歴の内容照合と、HDD全体の取得・検証。
- 新hostでの外部媒体backup、owner export/import、isolated restore、復旧試験。
- 全moduleのConfig／Stateを含むMigration Artifactとcanonical E2Eの受入。
- reboot後の再接続、ログイン前の常駐化、および監視・backup運用の受入。
- 実ブラウザでの会話、音声、画像生成、Task実行の利用者フロー。

したがって、今回の緊急復旧を全system移行完了、検証済みbackup、三OS互換性確認済みとは扱わない。
