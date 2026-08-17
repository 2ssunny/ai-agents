---
name: server-runbook
description: Pair-debugging protocol for remote servers and deployments, backed by local per-project infrastructure references. Use when the user pastes SSH or terminal output from a server, asks what command to run next on a host, or reports a deployment, container, proxy, or CI-runner problem.
---

# Server Runbook

The user debugs remote servers by pasting terminal output here and running the
suggested commands there. Every extra paragraph costs them a round trip, so the
value of this skill is almost entirely in how terse the reply is.

## Reply protocol

When the user pastes server output:

1. Diagnose silently.
2. Reply with the next command or command set in a **copy-pasteable code block**.
   Nothing in that block should require editing before it runs.
3. At most one short line of context above it ("nginx 설정 오류 — 재검증:").
   No option surveys, no multi-paragraph explanations.
4. Flag destructive commands (data loss, restarting a production service in use)
   in that one line and wait for the user to confirm.
5. Explain at length only when the user asks why, or when the fix needs a real
   decision from them.

Batch related commands into one block so the user makes a single round trip, and
prefer commands whose output confirms or refutes the diagnosis
(`nginx -t && systemctl reload nginx` rather than a blind restart).

## Project infrastructure references

Server topology, ports, service layout, and deployment specifics live in
`references/<project>.md` next to this file. These files are **local to each
machine and not distributed with this repository**, since infrastructure detail
is not something to publish.

- If `references/<project>.md` exists for the current project, read it before
  proposing any command. Guessing a hostname, port, or compose-file combination
  wastes exactly the round trip this skill exists to save.
- If it does not exist, ask the user for the topology you need, then offer to
  record it using `references/TEMPLATE.md` so the next session already knows.

## Diagnosis order

Work outward from the process, since most incidents are misattributed to the
layer the user noticed rather than the layer that failed:

```
container/process → local port → reverse proxy → tunnel/DNS → client
```

Confirm each layer before moving out: `docker compose ps` and service logs, then
`curl` against the local port, then `nginx -t` and the proxy config, then the
tunnel or DNS service status.

## Recurring pitfalls

- **IPv6 loopback**: `proxy_pass http://localhost:PORT` can resolve to `[::1]`
  while the app listens only on IPv4. Use `127.0.0.1` explicitly.
- **exFAT mounts**: no POSIX permissions, so `chmod`/`chown` silently do nothing.
  Do not chase permission fixes there.
- **CORS**: browser-side failures look like server downtime. Check the browser
  console evidence before touching the server.
- **Rate limiting**: an application's own limiter returning 429 under repeated
  testing can masquerade as an infrastructure failure.
- **Tunnel vs. origin**: when the public URL fails but `curl` against the local
  port succeeds, the fault is in the tunnel or proxy, not the application.
