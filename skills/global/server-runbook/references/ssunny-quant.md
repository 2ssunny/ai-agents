# ssunny_quant — Server Reference

Trading bot stack, single host, docker compose.

## Stack

- **docker compose** runs the bot and supporting services — check `docker compose ps` for the live service list before assuming names.
- **nginx** reverse-proxies to the app on port **18000** (`proxy_pass http://127.0.0.1:18000` — keep IPv4 explicit, see the IPv6 pitfall in SKILL.md).
- **Cloudflare tunnel** fronts public access. There is an issue history here: when the site is unreachable but local `curl http://127.0.0.1:18000` works, suspect the tunnel before nginx:

```bash
systemctl status cloudflared
journalctl -u cloudflared -n 50 --no-pager
```

## Standard triage order

```bash
docker compose ps
docker compose logs --tail 100 <service>
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:18000/
sudo nginx -t
systemctl status cloudflared
```

Work inside-out: container → local port → nginx → tunnel. Most past incidents were at the tunnel or nginx layer while the bot itself was healthy.

## Bot state

The bot exports `bot_state_*.json` snapshots (analyzed via the `bot-log` project skill on the dev machine, not on the server). Don't edit state files on the server.
