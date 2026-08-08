# ASSISTANT boundary

## Product role

`RenCrow_ASSISTANT`はplannedの、PUSH機能を持つ個人・家族向け生活アシスタント
serviceです。実装後は利用者ごとの生活Routineを実行し、端末へ届け、複雑な仕事だけを
`RenCrow_CORE`へ移譲します。

```text
Stack-chan / Apple Watch / iPhone / Web
                    |
                    v
          RenCrow_ASSISTANT
 personal / family / routine / PUSH
           |                 |
           v                 v
     RenCrow_CORE       RenCrow_PORTAL
 Agent / Task / Memory  Viewer / 操作UI
```

## Ownership

| 領域 | 正本module |
| --- | --- |
| personal / family scope、生活Routine、PUSH、delivery、ack / snooze / retry | `RenCrow_ASSISTANT` |
| Mio等のAgent、Agent routing、Memory、Recall、Knowledge、複雑なTask | `RenCrow_CORE` |
| Web表示、履歴・設定画面、許可された操作UI | `RenCrow_PORTAL` |
| 端末共通protocol、capability、delivery形式 | `RenCrow_ASSISTANT` |
| Stack-chan firmware/MOD、watchOS app等 | ASSISTANT contractを利用するdevice client artifact |

COREにもWorkstream、Task、Scheduler、Heartbeatがありますが、ASSISTANTの生活Routine
schedulerとは用途を分けます。目覚まし、朝の予定、天気、交通、ニュース配信は
ASSISTANTが所有し、複数工程、生成、継続調査、同期policy判定を伴うside effectはCOREへ昇格します。

## Runtime relationship

- `rencrow-assistant`はplannedのGo binaryです。
- Device clientはHTTPとWebSocketでASSISTANTへ接続します。
- ASSISTANTはCORE Public APIを利用し、debug/admin APIを利用しません。
- plannedのPORTAL連携はASSISTANT公開APIのallowlistを必要とし、読み取りsurfaceから
  writeしません。
- ASSISTANTが未実装の現在、manifestのversionとruntime statusはともに`planned`です。
  実在しないcommitやrelease artifactを割り当てません。
- ASSISTANTは実装後にPORTALやCMDと共通のInteraction意味論を利用しますが、時刻・条件発火、
  PUSH、Device deliveryと生活領域の状態だけはASSISTANT固有です。
- PUSHを別の会話systemにせず、CORE応答と生活通知を共通のInteraction outputとして
  相関可能にします。wire schemaはASSISTANT実装時にmodule側の正本へ固定します。

## Privacy boundary

- personal dataは利用者ごとに分離します。
- `family:shared`は明示的に共有された予定・Task・情報だけを持ちます。
- COREの全Agent共通記憶は、同じ認証済み利用者・許可scope内のAgent切替を指し、
  別利用者のprivate memoryを共有する意味ではありません。
- Device、PORTAL、COREへ渡すcontextは、利用者とscopeを確定して最小化します。

ASSISTANT固有の機能、data、API、設定、MVPは、実装repositoryの作成後にその`docs/`を
正本とします。
PORTAL、CMDとの共通能力とprofile差は[Interaction surfaces](interaction-surfaces.md)を
参照してください。
