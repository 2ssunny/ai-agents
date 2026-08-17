# <project> — Server Reference (template)

Copy this to `<project>.md` in the same directory and fill it in. Files here
other than this template are git-ignored, so real infrastructure detail stays on
your machine.

Record only what saves a round trip during debugging. Never put credentials,
private keys, or tokens in this file — reference the secret's *location* instead
(for example, "API key in `/etc/app/.env` as `APP_API_KEY`").

## Topology

| | Host A | Host B |
|---|---|---|
| Hostname | | |
| Address (VPN/LAN) | | |
| Role | | |
| Notable hardware | | |

Describe how traffic flows between hosts (reverse proxy, VPN tunnel, private
network) and which link fails first when the site goes down.

## Ports

| Port | Service | Exposed publicly? |
|---|---|---|
| | | |

## Containers and compose files

Which compose files combine for which environment, and which services must not
be taken down casually (databases, anything holding resumable job state).

```bash
docker compose ls
docker compose -f <base> -f <overlay> ps
```

## Database

Connection method, migration procedure, and how to verify a migration applied.

## Scheduled jobs and deployment

Timers, cron entries, or CI runners that run on the host, and the commands to
inspect their status and logs.

## Incident history

Failures already diagnosed on this project and what the actual cause turned out
to be. This section is usually the highest-value part of the file — it stops the
next session from re-deriving a known answer.
