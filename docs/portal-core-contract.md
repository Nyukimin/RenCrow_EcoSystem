# PORTAL–CORE integration contract

## Status and scope

この文書は、`RenCrow_PORTAL`と`RenCrow_CORE`を一つの製品として組み合わせるための
ecosystem-level contractです。対象は責務、通信方向、公開境界、失敗時の扱い、
統合試験条件です。

endpointのpayload、内部実装、module固有の設定は複製しません。詳細の正本は次です。

- CORE API: `RenCrow_CORE/docs/06_Public_API仕様.md`
- PORTAL proxyとUI: `RenCrow_PORTAL/README.md`および`internal/portal/`
- TTS／STT Gatewayとtarget: `RenCrow_TTS`／`RenCrow_STT`の各module仕様

現在のecosystem releaseは`development`、compatibilityは`source-pinned`です。
この文書は固定したsource commit間の接続契約を定義しますが、release artifactの
互換性確認済みを主張しません。

## Responsibility boundary

| Concern | Owner | Contract |
| --- | --- | --- |
| Persona、Memory、会話処理、routing、Agent game decision | CORE | PORTALは複製しない |
| `/viewer/*`、SSE、STT WebSocket | CORE | runtime behaviorとpayloadの正本 |
| `Chat`／`IdleChat`／`Games` Web UI | PORTAL | ChatとGamesは各allowlist内の操作、IdleChatは読み取り専用 |
| game world、rules、Executor、Replay、Observer | GAMES | PORTALは同一origin iframeで観戦する |
| Games PuruPuru overlay | PORTAL | iframe外で表示し、盤面を複製しない |
| 外部公開するmethod／path | PORTAL | allowlistに明示したものだけ中継 |
| recipientの選択表示 | PORTAL client | browser tab内のlocal state |
| 実際のmessage宛先 | CORE request | `POST /viewer/send`の`to`で確定 |
| audio／input active owner | CORE | client IDごとのclaim、heartbeat、release |
| TTS／STT公開契約 | RenCrow_TTS／RenCrow_STT | COREは各Gatewayだけを参照 |
| TTS合成とSTT認識 | TTS／STT target | PORTALやCOREへ演算実体を持ち込まない |

PORTALはruntime状態の正本ではありません。TTS／STTのON／OFFはPORTALのUI状態ですが、
実際に操作できるclientはCOREのactive-controlで調停します。

## Runtime topology

```text
Browser
  |
  | HTTPS / SSE / WebSocket
  v
RenCrow_PORTAL
  | allowlisted proxy
  v
RenCrow_CORE
  | TTS contract       | STT contract       | Games bridge
  v                    v                    v
RenCrow_TTS          RenCrow_STT          RenCrow_GAMES
  |                    |                    |
  v                    v                    v
TTS target           STT target           Observer / Executor
```

PORTALはCOREの全APIを透過公開しません。COREはRenCrow_TTS／RenCrow_STT Gatewayだけを
参照し、演算targetや互換runtimeへ直接fallbackしません。

## Mode permissions

| Operation | `IdleChat` | `Chat` | `Games` |
| --- | --- | --- | --- |
| CORE health | allow | allow | allow |
| 会話event、IdleChat status | allow | allow | deny |
| chat recipient、message、IdleChat開始／停止 | deny | allow | deny |
| audio／input、TTS、STT | deny | allow | deny |
| Games status、session、event、Observer read | deny | deny | allow |
| Agent-owned game launch | deny | deny | allow |
| session Retry／Start over | deny | deny | allow |
| game decision／result、Observer launch／ingest | deny | deny | deny |
| Debug、Ops、Repair、LLM管理、設定変更 | deny | deny | deny |

正確なallowlistはPORTALの実装とcontract testを正本とします。COREにendpointを追加しても、
PORTAL側へmethod／pathと拒否testを明示しない限り外部公開しません。

## Recipient selection

1. PORTALはbrowser tabごとの`viewer_client_id`と選択recipientを保持する。
2. 選択変更時、PORTALはCOREへrecipient選択を通知する。
3. COREは`viewer.recipient_selected`を観測eventとして発行する。
4. COREは通知された選択をglobal conversation stateにしない。
5. message送信時は、`POST /viewer/send`の`to`を実際のrouting入力とする。

この分離により、複数のPORTAL clientが別々の相手を選択しても、最後に選択した一台の
状態で全clientの送信先が上書きされません。

## TTS playback flow

```text
PORTAL        CORE                 TTS
  | claim audio |                   |
  |------------>|                   |
  |              | synthesis request|
  |              |------------------->
  |  SSE: tts.audio_chunk           |
  |<-------------|                   |
  | GET audio    |                   |
  |------------->|                   |
  | local playback                   |
  |              |                   |
  | SSE: tts.session_completed       |
  |<-------------|                   |
  | playback ACK |                   |
  |------------->|                   |
```

- PORTALはTTS ON時にaudio ownerをclaimし、稼働中はheartbeatを送る。
- `tts.audio_chunk`と`tts.session_completed`は同じ`session_id`と`response_id`で
  response lifecycleを識別する。
- PORTALはchunkを順番に再生し、全chunkの終了とsession完了を確認してから、
  response単位でplayback ACKを一度だけ送る。
- audio取得成功、browser再生成功、playback ACK成功は別々の成功条件である。
- autoplay拒否、decode失敗、音声device失敗はerror ACKとしてCOREへ返す。
- TTS OFF、owner移譲、client終了時は再生を止め、ownerをreleaseするかTTL失効させる。

COREのremote TTS audio proxyは、設定済みTTS base URLと同一hostの音声だけを取得します。
任意のprivate hostをPORTAL経由で取得できる構成にしません。

## STT input flow

```text
PORTAL        CORE              STT Gateway / target
  | claim input |                       |
  |------------>|                       |
  | WebSocket /stt                      |
  |------------>| bridge                |
  |              |---------------------->|
  | PCM16 16 kHz |                       |
  |------------>|---------------------->|
  | partial / final / error              |
  |<------------|<----------------------|
  | release input                        |
  |------------>|                       |
```

- PORTALはSTT ON時にinput ownerをclaimし、browser microphoneを取得する。
- browser音声はmono PCM16、16 kHzへ変換し、PORTAL経由のWebSocketでCOREへ送る。
- COREはRenCrow_STT Gatewayの`POST /v1/audio/transcriptions`だけへ接続する。
- `partial`／`draft`は入力欄へ反映し、`final`は選択中recipientへのmessage入力として扱う。
- WebSocket、CORE bridge、STT Gateway、STT targetの各層を別々にhealth判定する。
- backend未到達、認識error、owner移譲、microphone取得失敗ではSTTをOFFへ戻し、
  input ownerをreleaseする。

WebSocket upgradeが成功しても、STT targetへの接続と実際の文字起こしが成功していなければ、
STT利用可能とは判定しません。

## Security boundary

- `IdleChat`は読み取り専用とし、write／control requestを拒否する。
- `Chat`も明示allowlist外のendpointを拒否する。
- `Games`は`portal-games` allowlist外を拒否し、Agent decision／resultとObserver ingestを公開しない。
- browserからのwriteとSTT WebSocketはsame-originを要求する。
- Observer responseだけをsame-origin frame可能にし、PORTAL pageとPuruPuru assetはframe不可を維持する。
- Observer HTMLは外部assetを同一origin proxyし、title描画の動的style属性だけを
  Observer responseで許可する。inline scriptとPORTAL本体の`unsafe-inline`は許可しない。
- PORTALはrequest bodyに上限を設ける。
- Debug、Ops、Repair、admin、LLM管理、設定変更をPORTALから公開しない。
- TTS audio proxyは設定済みhost以外を拒否する。
- token、credential、runtime stateをURL、文書、repositoryへ保存しない。
- PORTALをネットワーク公開する場合はloopback bindとtailnet-only Tailscale Serveを使い、PORTALの`auth_mode=tailscale_serve`で固定identity headerを検証する。Funnel、PORTALの直接bind、`X-RenCrow-Client`／interaction profileを認証の代用にしない。
- Tailscaleのタグ付きsourceではuser identity headerを得られない。owner browser E2Eはタグなしの認証済みuser deviceから実行し、server自身のタグ付きbrowserやheader注入で代用しない。

## Failure semantics

| Failure | Required behavior |
| --- | --- |
| CORE unreachable | PORTALは接続失敗を表示し、操作成功にしない |
| recipient通知失敗 | 切替失敗を表示し、messageの`to`で誤送信を防ぐ |
| TTS audio取得失敗 | 再生成功にせずerror ACKを返す |
| browser playback失敗 | fetch成功と区別しerror ACKを返す |
| STT backend unreachable | WebSocket接続成功と区別しSTTをOFFへ戻す |
| active owner移譲 | 旧ownerはlocal再生／入力を停止する |
| unknown／admin endpoint | PORTALで拒否しCOREへ到達させない |

## Integration acceptance

PORTALとCOREの組み合わせをcompatibleと記録する前に、最低限次を確認します。

1. CORE healthとPORTAL readinessが成功する。
2. `IdleChat`からwrite／control操作が拒否される。
3. `Chat`のrecipient切替がCORE eventへ到達し、messageの`to`と一致する。
4. `Games`でNetHackとAgentを選び、`personas[]`付きlaunchから同一origin Observerへ到達する。
5. ObserverFrameの`decision.agent_id`が選択Agentと一致し、RuleBasedBrainをAgent E2Eへ使っていない。
6. Gamesからdecision／result／Observer ingest／debugが拒否され、Retry／Start overだけがsession操作として通る。
7. TTS ONでaudio ownerを取得し、実応答のaudio取得とplayback ACKまで到達する。
8. TTS再生成功と再生errorの両方が正しいACK statusになる。
9. STT WebSocket upgrade、start／stop、実音声の`final`認識まで到達する。
10. STT target停止時にerrorが表示され、input ownerが解放される。
11. Debug／admin endpointとcross-origin controlが拒否される。
12. 設定外hostのTTS audio取得が拒否される。
13. client終了後にaudio／input ownerが残留しないか、TTLで失効する。
14. tailnet-only公開の未認証requestが401で拒否され、タグなしuser deviceの実browserがPORTAL send、CORE `job_id`、実AgentのDOM表示まで到達する。
確認command、対象version、実行環境、結果、未確認点をverification recordへ残してから、
`ecosystem.yaml`のCORE／PORTAL versionとcompatibility statusを更新します。
