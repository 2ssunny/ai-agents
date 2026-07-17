# scholar-orient — Server Reference

Two-server deployment connected over WireGuard.

## Topology

| | Server A | Server B |
|---|---|---|
| Hostname | `scholar-orient-server` | `ssunnyserver` |
| WireGuard IP | `10.10.0.2` | `10.10.0.3` |
| Role | PostgreSQL DB, embedding worker, backend API | Web frontend, nginx reverse proxy, WireGuard hub |
| GPU | GTX 1060 (embedding inference) | — |

Server B's nginx proxies public traffic to Server A's API over the WireGuard tunnel. If A↔B connectivity fails, check WireGuard first: `wg show`, then ping the peer's `10.10.0.x` address.

## Ports

| Port | Service |
|------|---------|
| 3001 | Backend API |
| 3002 | Frontend/web |
| 18081 | Proxied service port on nginx side |

## Docker compose

Services are split across multiple compose files; they are combined with `-f` flags. Check which combination is in use before restarting:

```bash
docker compose ls
docker compose -f docker-compose.yml -f docker-compose.<variant>.yml ps
```

Never `docker compose down` the DB service casually — the embedding pipeline resumes from DB state.

## PostgreSQL migrations

Applied manually via psql on Server A:

```bash
docker compose exec db psql -U <user> -d <db> -f /path/to/migration.sql
# or from host:
psql -h 127.0.0.1 -U <user> -d <db> -f migration.sql
```

Verify schema after applying (`\d <table>`) before declaring success.

## Ingest / pipeline scheduling

Data ingest runs on a **systemd timer** on Server A:

```bash
systemctl list-timers | grep ingest
systemctl status <ingest-unit>
journalctl -u <ingest-unit> -n 100 --no-pager
```

## CI/CD

GitHub Actions **self-hosted runner** on the server handles deployment. If CD stalls:

```bash
# runner status
systemctl status actions.runner.* 2>/dev/null || ps aux | grep Runner.Listener
# recent workflow runs (from dev machine)
gh run list --limit 5
```
