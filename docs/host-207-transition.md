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
| LLM Gateway | host 207、native Go、loopback 8090。206の旧Gatewayは停止・無効化し、旧loopback入口を207へ転送 |
| 記憶の外部store | host 207のnative Redis 7.4.8／Qdrant 1.17.0。COREのowner境界は変更しない |
| capability service | STT／TTS／Vision／Image／ComfyUI／MuseTalkは207。Imageの保持データも207へ配置 |
| RX6800 LLM | host 206のLLM RuntimeとAka（Mellum）、Ao（Qwen3.5）、Kin（K2）。Gin（Granite）は停止を維持 |
| Strata | host 205のStrataとLLM Runtime。旧Image GatewayとOllamaは停止し、自動起動も解除 |
| その他のapplication | GAMES Observer／TRADE／映画・人物カタログ／歌詞collector／開発用Giteaは207 |
| runtime Workspace | host 207の`<HOME>/.rencrow/workspace`を現行正本とする |
| COREの稼働データ | host 207の明示設定先`<HOME>/RenCrowData/db/core`。旧HDDは変更せず保持 |

利用者の追加指示により、206はRX6800 LLM、205はStrata、それ以外のRenCrow applicationは
207へ集約する。206／205には各computeのRuntime、必要なGPU監視・起動管理を残す。
207のCORE、PORTAL、移設したapplicationと追加の接続tunnelなど21 jobは、
利用者による管理者install後、launchdのsystem LaunchDaemonで監視する。実行userはyukimiを維持し、
旧GUI jobは無効化した。既存のGemma／Qwen／ComfyUI／STT／TTSもsystem LaunchDaemonであり、
GUIログインは起動条件ではない。
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

### 追加集約の確認 — 同日20:44 JST

- Imageは保持object 204件とvideo job 14件を復旧し、ownerのsnapshot検証を通過した。
  COREの画像生成routeから1024×1024のPNGを生成し、CORE経由の取得、保持object、NAS公開copyのSHA-256が一致した。
- CORE停止中に、その時点の接続先204からRedis RDBとQdrant全体snapshotを取得した。
  RDB checksum、9 collectionの名前・point件数・aliasを照合し、207へ復元した。
  204／206の旧store containerは停止し、自動再起動を無効化した。volumeは保持する。
- BGE-M3は同じmodel SHA-256を確認し、207のCPUで起動した。206との比較は1024次元、cosine similarity 0.99982。
- 207のGateway readinessはGinを除く全targetでready。207上のGatewayからMioへの実生成がHTTP 200。
  205／206のRuntimeへは認証済みSSH tunnelを利用し、Backendとmodelの配置は変更しない。
- GAMES Observer、TRADE、映画・人物カタログのhealthはHTTP 200。TRADEはDISABLED／kill switch ONを維持した。
- Gitea 1.26.2は207の3001／2222で起動。SQLite integrity、既存repositoryのgit fsck、Web healthを確認した。
- Gmailは207のCLIと移設済み認証でAPI疎通を確認した。X Bookmarkのexportと既知ID stateは移設したが、
  203から暗号化bridgeで認証を移行し、207の専用browserでBookmark 4件の読み取りを確認した。
  一時鍵と転送bundleは削除済み。旧Linux用のcommand／credential参照pathも修正した。

これらは今回の配置切替の確認であり、全Agentの会話・Task・音声・video生成を通したE2E、
reboot後の復帰、全moduleのMigration Artifact受入を意味しない。

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
件数は未確定。HDD全体の作業用image取得はCORE起動後に完了し、Git外に保持している。
そのimage自体へのjournal replayやfilesystem修復は行っていない。

## 残る受入

- 再構築した履歴の内容照合と、HDD全体imageの復旧受入。
- 新hostでの外部媒体backup、owner export/import、isolated restore、復旧試験。
- 全moduleのConfig／Stateを含むMigration Artifactとcanonical E2Eの受入。
- system LaunchDaemonへの切替は21 jobの所属・実行user・readinessを確認済み。
  reboot後の再接続、実際のGUI logout後の動作、および監視・backup運用の受入は未確認。
- 実ブラウザでの会話、音声、画像生成、Task実行の利用者フロー。

したがって、今回の緊急復旧を全system移行完了、検証済みbackup、三OS互換性確認済みとは扱わない。

## ログイン不要の常駐化

21 jobをsystem domainへ移し、旧gui/501 domainには同じjobがないことを確認した。
Redisと13 HTTP serviceのreadinessに加え、CORE／PORTAL／LLM Gateway／Imageを再確認した。
ImageはMuseTalkのmodel読み込みより先にrestart fenceを評価すると起動時にblockするため、
起動launcherでMuseTalkの実際のidle応答を上限300秒まで待つ。Image自身の安全確認は維持する。
MuseTalkをcold restartし、同時にImageを起動する実試験で正常復帰を確認した。
これはsystem domainへの切替とservice再起動の確認であり、OS reboot試験の代替ではない。
