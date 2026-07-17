---
name: server-runbook
description: Pair-debugging protocol for remote servers plus per-project infrastructure runbooks (docker compose, nginx, psql, WireGuard, systemd, CI runners). Use whenever the user pastes SSH/terminal output from a server, asks "서버에서 뭐 돌려야 해", reports a deployment/CD problem, or debugs anything on scholar-orient-server, ssunnyserver, or the quant server — even if they just paste an error log with no question.
---

# Server Runbook

The user debugs remote servers by pasting terminal output here and running your suggested commands there. This loop only works if your replies are terse.

## The protocol (this matters most)

When the user pastes server output:

1. Diagnose silently.
2. Reply with **the next command(s) to run, copy-pasteable, in a code block** — nothing that can't be pasted directly into the terminal.
3. At most one short line of context above the block ("nginx 설정 오류 — 재검증:"). No multi-paragraph explanations, no option surveys. The user has explicitly asked: "터미널 명령어들만 말해달라고."
4. If a command is destructive (drops data, restarts prod services during use), flag it in that one line and wait for a go.
5. Longer explanations only when the user asks "왜?" or the fix requires an actual decision.

Batch related commands into one block so the user makes one round-trip, and prefer commands whose output confirms the diagnosis (e.g. `nginx -t && systemctl reload nginx` rather than blind restarts).

## Project infrastructure references

Read the matching reference **before** proposing commands — server names, IPs, ports, and compose file combinations are all documented and guessing them wrong wastes a round-trip:

- **scholar-orient** (two-server setup, WireGuard, embedding pipeline): read `references/scholar-orient.md`
- **ssunny_quant** (trading bot, docker compose, nginx proxy): read `references/ssunny-quant.md`

For other projects, ask which host/stack before suggesting anything.

## Known pitfalls (encountered in real sessions)

- **IPv6 `[::1]` proxying**: nginx `proxy_pass http://localhost:...` can resolve to `[::1]` while the app listens on IPv4 only → use `127.0.0.1` explicitly.
- **exFAT mounts**: no POSIX permissions — chmod/chown silently no-op; don't chase phantom permission fixes there.
- **CORS**: browser-side failures that look like server downtime; check the browser console evidence before touching the server.
- **Rate limiting**: 429s from the app's own limiter can masquerade as infra failure under repeated testing.
