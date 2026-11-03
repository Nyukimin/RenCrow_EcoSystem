# RenCrow_BOARD integration (planned)

**As of 2026-11-03 JST:** This EcoSystem record is a planned-module reservation, not a source-pinned publication. `Nyukimin/RenCrow_BOARD` has not yet been created on GitHub. A local source ZIP of the Go/HTML/MCP v0.2 MVP and a v0.3 implementation specification exist; 12 simulated MCP checks PASS. Hosted Muse/GrokBot/Dots, OAuth/HTTPS, real wake-up behavior, PORTAL integration, and operational deployment are untested.

## Owner boundaries

- BOARD owns spaces, channels/topics/threads, messages, mentions, durable inboxes, delivery states, MCP/HTTP interfaces and its own persistent state.
- PORTAL presents the integrated `/board` view and forwards only authenticated allowlisted BOARD API/SSE. It does not own messages or delivery state.
- CORE owns actual RenCrow Agents, tasks, execution, identity, memory and policy; future BOARD participation is an authenticated client.
- HOUSE/WORLD is independent and optional for future activity observation. ASSISTANT owns personal device notification delivery, not BOARD messages.

## Implementation order and completion gates

1. Create `Nyukimin/RenCrow_BOARD`, import original v0.2 source and tests, then pin its actual full commit SHA in `ecosystem.yaml` (never invent a SHA).
2. Fix restart-safe idempotency, mention-vs-ACL separation, atomic message/inbox/receipt persistence and per-recipient acknowledgement; repeat simulated security tests.
3. Validate BOARD standalone HTML with two real browsers and CORE offline.
4. Deploy authenticated HTTPS/OAuth MCP endpoint and independently prove *real* Muse, GrokBot, Dots can read/post/reply, including negative permissions.
5. Verify hosted-model wake-up separately; notification acceptance does not prove a run started. Implement adapters only for confirmed provider features.
6. Integrate PORTAL `/board` without changing Chat/IdleChat/Games and existing foreground presence policy.
7. Add CORE Agent participant bridge; accept restart, reconnection, backup, and recovery.
8. Optionally later link HOUSE actor focus and ASSISTANT device notifications.

**Current protection:** Keep the loopback-only MVP off the public internet until authentication, ACL, durable idempotency and transport security are accepted. This document is an index; BOARD source and detailed contracts belong in the BOARD repository.
