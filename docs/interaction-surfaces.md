# Interaction surfaces

## 目的と位置づけ

この文書は、`RenCrow_PORTAL`、`RenCrow_CMD`、`RenCrow_ASSISTANT`を、
別々の会話システムではなく、RenCrowの共通Interaction能力を利用する兄弟moduleとして
組み合わせるためのecosystem-level contractです。

共通化するのは機能の**意味と失敗条件**です。単一process、共有database、共通UI、
同一transport、または現時点で存在しない共通SDKを要求するものではありません。
endpoint、payload、command、画面、永続化の詳細は各module repositoryを正本とします。

```text
                         RenCrow_CORE
                  Agent / Chat / IdleChat / Task
                         Public API
                    ^          ^          ^
                    |          |          |
            RenCrow_PORTAL  RenCrow_CMD  RenCrow_ASSISTANT
            Web profile     CLI profile  Proactive profile
                                           |
                                           v
                                     Device clients
```

3moduleは並列ですが、同じ種類ではありません。PORTALとCMDは状態を所有しないclient
surfaceであり、ASSISTANTは共通Interaction能力を利用しながら生活領域の状態を所有する
常駐application serviceです。

## 共通Interaction意味論

各surfaceは、利用者、権限、端末能力に応じて、次の同じ意味論を利用します。

| capability | 共通条件 | 正本 |
| --- | --- | --- |
| Chat | 明示recipient、利用者scope、送受信相関を維持する | CORE Public API |
| IdleChat | 状態・eventを購読し、開始・停止などの操作権限を分ける | CORE Public API |
| recipient / Agent選択 | 表示上の選択と実message宛先を混同しない | CORE Public APIと各client local state |
| event購読 | 再接続、重複、順序、degradedを扱う | event発行module |
| session / trace | request、response、task、deliveryを必須`trace_id`で追跡できる | 処理を所有するmodule |
| STT / TTS | 入力、合成、取得、端末再生を別々の成功条件にする | COREとSTT／TTS contract |
| Task | 通常会話と複雑な継続作業を区別し、statusを追跡する | CORE |
| acknowledgement | idempotencyを保ち、再送を二重処理しない | eventまたはdeliveryの所有module |
| error | unavailable、degraded、denied、expired、failedを成功へ丸めない | 各処理の所有module |

すべてのsurfaceが全capabilityを同じ見た目で公開する必要はありません。能力を別実装へ
分岐させる代わりに、profile、認証scope、mode、device capabilityで公開可否と表現を
決めます。

## Profileごとの差

```text
RenCrow_PORTAL
  = RenCrow Interaction Client + Web Renderer

RenCrow_CMD
  = RenCrow Interaction Client + Terminal Renderer + Automation / Operations

RenCrow_ASSISTANT
  = RenCrow Interaction Client + Proactive Trigger + Device Delivery
    + personal / family / routine state
```

| profile | 固有差 | 所有しないもの |
| --- | --- | --- |
| PORTAL | Chat／IdleChatのWeb表示・入力、Web renderer | Persona、会話、Task、Routine、deliveryの正本 |
| CMD | terminal表示、scriptable command、process起動、診断・管理操作 | CORE／PORTAL／ASSISTANTのruntime状態 |
| ASSISTANT | 時刻・条件発火、PUSH、利用者・家族・端末、ack／snooze／retry | Agent人格、Agent Memory、CORE Task、PORTAL画面 |

権限は個別の隠れ機能ではなく、capability profileとして扱います。CORE Interactionの
現行wire profileは次です。

| profile | capability |
| --- | --- |
| `portal-chat` | PORTAL Chat allowlist |
| `portal-idlechat` | PORTAL IdleChat読み取り |
| `cmd-chat` | CMD Chat送信とevent購読 |
| `cmd-idlechat` | CMD IdleChat status／event／start／stop |
| `assistant-core` | ASSISTANTからCOREへのChat送信とevent購読 |

clientは`X-RenCrow-Client`と`X-RenCrow-Interaction-Profile`を組で送ります。これは
capability policyの入力であり、認証credentialではありません。

## PUSHと出力event

PUSHは第二の会話systemを作りません。ASSISTANTが生活Routineから生成した通知も、
COREから戻った会話・Task結果も、利用者、source、category、本文、必須`trace_id`、delivery方針を
持つInteraction outputとして扱えます。同じ意味の出力をsurfaceごとに表現します。

| surface / device | 表現例 |
| --- | --- |
| PORTAL | messageまたはcard |
| CMD | terminal textまたはstructured output |
| Apple Watch | 通知、振動、一画面の要点 |
| Stack-chan | 音声、表情、首振り |
| iPhone | 通知と詳細画面 |

共通event envelopeのwire schemaは、実callerと実装が揃う段階で所有moduleのcontractへ
固定します。EcoSystemは必須fieldの意味を揃えますが、module固有APIを複製しません。

## 独立性と接続方向

- COREはPORTAL、CMD、ASSISTANTがなくても起動・稼働できる。
- ASSISTANTの目覚まし、決定論的Routine、cache済みPUSHは、PORTALが閉じていても動く。
- CORE停止時も、ASSISTANTはCOREを必要としないRoutineを可能な範囲で継続する。
- ASSISTANTからCOREへの移譲は、Agent会話、生成、深い調査、複数工程Taskなど必要時だけ行う。
- PORTALはCOREとASSISTANTのallowlisted APIを表示・操作できるが、どちらの状態も正本にしない。
- CMDは各serviceを起動・管理し、許可されたAPIをCLIから利用できるが、状態を複製しない。
- Device clientはASSISTANT Device Contractへ接続する。固定alarm音や端末内蔵発話はCOREを
  通さず配信でき、動的なAgent会話はCORE／TTS contractを利用できる。

## ニュースの分担

一般ニュースの収集結果、provenance、重複排除、時系列、共通知識・検索への昇格は、
COREの共通知識基盤または将来の専用News moduleが正本になります。利用者ごとの選定、
既読、件数、時刻、PUSH、deliveryはASSISTANTが所有し、PORTAL／CMD／Deviceは表示します。

現行COREのIdleChat向けRSS／Reddit／X cacheは、IdleChatの話題候補を作るconsumer固有機能
であり、共通ニュースDBではありません。共通News contractを実装する際は、同じsourceを
各moduleが別々に取得する構成へ固定せず、provenance付き取得結果を再利用できる境界へ
段階的に収束させます。

## 現在の実装状態

| 能力 | 現在状態 |
| --- | --- |
| CORE Chat／IdleChat Public API | 実装済み |
| PORTAL Chat／IdleChat Web profile | 実装済み |
| CMD Chat CLI profile | 実装済み |
| CMD IdleChat `watch`／`start`／`stop` | 実装済み |
| ASSISTANT Interaction profile／Device delivery renderer | foundation実装済み |
| ASSISTANT runtime／Routine／PUSH | 採用済み・未実装 |
| profile名を使うcapability guard | 実装済み |
| 共通Interaction SDK | 未採用。実callerと重複が確認されるまで先行作成しない |

## 統合acceptance

1. 同じChat requestが、許可されたPORTAL／CMD／ASSISTANT clientから同じrecipientと
   利用者scopeでCOREへ到達する。
2. IdleChat eventの意味、開始・停止、拒否、degradedがsurface間で矛盾しない。
3. profileまたはmodeで許可されない操作がclient側とserver側の両方で拒否される。
4. 再接続や再送でmessage、Task、PUSH、acknowledgementが二重処理されない。
5. 同じ出力のsource、category、`trace_id`を保ったまま、surface／deviceごとに表現を変えられる。
6. PORTAL停止、CORE停止、Device切断を分けて試験し、ASSISTANTの継続・degraded・retryが
   仕様どおりになる。
7. personal、family、adminのscopeがsurface変更によって拡大しない。
