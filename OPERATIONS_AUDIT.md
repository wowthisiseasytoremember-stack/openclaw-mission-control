**Last Updated:** 2026-04-10 23:00 UTC

# OpenClaw Mission Control — Operations Audit

Audited: 2026-04-10 23:00 UTC
Auditor: Claude (automated audit)

---

## Summary Dashboard

| Area | Status | Critical Issues |
|------|--------|----------------|
| Performance | WARN | Gateway process at 622 MB RAM; 4 zombie brain_mcp processes |
| Configuration | WARN | backend/.env has blank BASE_URL and LOCAL_AUTH_TOKEN; LOG_USE_UTC=false |
| Database Health | WARN | 1 FK column missing index (task_fingerprints.task_id); no backup strategy |
| Log Review | WARN | Bootstrap files truncated on every heartbeat; slow skills/sync endpoints; 422 on marketplace |

**No outright ISSUE-level (service-down) findings. All containers are healthy. Three WARN items require action before load increases.**

---

## Performance

### Container Resource Usage

| Container | CPU % | Memory | Memory % |
|-----------|-------|--------|----------|
| frontend | 0.00% | 72 MB / 15.3 GB | 0.46% |
| backend | 0.19% | 135 MB / 15.3 GB | 0.86% |
| webhook-worker | 0.00% | 76 MB / 15.3 GB | 0.49% |
| db (Postgres) | 0.00% | 24 MB / 15.3 GB | 0.16% |
| redis | 1.09% | 9.4 MB / 15.3 GB | 0.06% |

**Status: OK** — All OpenClaw containers are lightweight. Total stack footprint is ~317 MB RAM. No CPU pressure. Postgres at 24 MB is consistent with the small table sizes observed (all tables under 200 kB).

---

### Gateway Process Memory

```
PID 2049930  0.3%  ~60 MB   openclaw (launcher/supervisor)
PID 2049939  3.9%  ~622 MB  openclaw-gateway (Node.js runtime)
```

**Status: WARN** — The gateway Node process is consuming 622 MB RSS (resident set size — physical RAM actually in use). This is elevated for an idle gateway. Likely cause: Node.js V8 heap has grown during the session and has not been garbage-collected. Not a crisis at 15 GB total RAM, but worth monitoring. If it crosses 1 GB, consider a scheduled nightly restart via systemd (`Restart=on-failure` + a weekly `systemctl --user restart openclaw-gateway`).

**Recommendation:** Add a memory ceiling to the systemd unit (`MemoryMax=1G`) so the OS OOM killer targets this process rather than a critical container if RAM gets tight. Monitor weekly.

---

### brain_mcp_server Child Processes

```
PID 2056030  started 11:25
PID 2095473  started 11:33
PID 2100190  started 11:35
PID 3399902  started 20:00
```

**Status: WARN** — 4 orphaned `brain_mcp_server.py` processes are running simultaneously. These are not the same process — they were spawned at different times and none of them died. Each is consuming ~56 MB RSS, totalling ~225 MB in zombie processes. The MCP server is clearly not being killed when it should be; a new one is spawned on each invocation, leaving the old one behind.

**Recommendation:** Add a PID file or `pkill -f brain_mcp_server.py` to the startup script before launching a new instance. Alternatively, run it as a persistent systemd service (like the gateway) so there is always exactly one. Clean up the current orphans manually: `pkill -f brain_mcp_server.py && sleep 1 && python3 /home/ichabod/scripts/brain_mcp_server.py &`

---

### Database Table Sizes

All tables are under 200 kB. This is a new/lightly-used deployment.

| Table | Size |
|-------|------|
| agents | 192 kB |
| activity_events | 120 kB |
| boards | 112 kB |
| organization_members | 96 kB |
| users | 80 kB |
| tasks | 80 kB |

**Status: OK** — No bloat. No vacuum pressure. Nothing to optimize here yet.

---

### Sequential Scans (Potential Missing Indexes)

```sql
public | agents | seq_scan=325 | seq_tup_read=315 | idx_scan=161
```

**Status: WARN** — The `agents` table has nearly 2x as many sequential scans as index scans. With only ~315 rows read per scan (tiny table), this is not causing visible slowness right now. But it signals that common query patterns on `agents` are not using an index — likely queries filtering by `board_id`, `status`, or `organization_id`. As the table grows, these will become expensive.

**Recommendation:** Run `EXPLAIN ANALYZE` on the most common agent queries to identify which columns need indexing. Likely candidates: `agents.board_id` and `agents.status`.

---

### Redis Memory

```
used_memory_human: 1.10 MB
used_memory_rss_human: 5.03 MB
dbsize: 0 keys
keyspace: (empty)
```

**Status: OK** — Redis is essentially idle. No keys, 1.1 MB working memory. The RQ (Redis Queue — the job queue system) has nothing queued, which is expected for a low-traffic deployment.

---

## Configuration

### .env vs .env.example Comparison

The root `.env` (active config) versus `.env.example` (reference template):

| Key | .env.example | .env (active) | Status |
|-----|-------------|--------------|--------|
| FRONTEND_PORT | 3000 | 3088 | OK — intentional override |
| BACKEND_PORT | 8000 | 8088 | OK — intentional override |
| LOCAL_AUTH_TOKEN | (empty placeholder) | (not present in root .env) | WARN — see below |
| CORS_ORIGINS | localhost:3000 only | 4 origins including Tailscale | OK |
| NEXT_PUBLIC_API_URL | `auto` | `http://192.168.1.200:8088` | OK — explicit LAN IP |

**Status: OK** (root .env) — The root `.env` is a valid production override. The missing `LOCAL_AUTH_TOKEN` in the root `.env` is acceptable because it is set in `backend/.env`.

---

### backend/.env Findings

**Status: WARN — Three problems found:**

**1. BASE_URL is blank**
```
BASE_URL=
```
This field is marked REQUIRED. It is the public URL the backend advertises to the gateway for webhook flows and agent heartbeat callback instructions. A blank value means any feature that generates a callback URL (webhook delivery, gateway provisioning instructions) will produce a broken or empty URL. The backend starts without error because the validation is not hard-enforced at startup, but features will silently fail.

**Fix:** Set `BASE_URL=http://192.168.1.200:8088` (or the Tailscale URL if you need remote access: `http://100.122.158.123:8088`).

**2. LOCAL_AUTH_TOKEN is blank**
```
LOCAL_AUTH_TOKEN=
```
Also marked REQUIRED. This is the token users paste into the login form. A blank token means the frontend login page will always reject authentication (token must be at least 50 characters). The fact that the deployment appears functional suggests this may be overridden by an environment variable in the Docker compose file or the root `.env` — but it is not visible there either. This needs verification.

**Fix:** Set a random 64-character token: `openssl rand -hex 32` and paste the result as the value.

**3. LOG_USE_UTC=false**
```
LOG_USE_UTC=false
```
Backend logs use local time. This conflicts with the global requirement (from CLAUDE.md) that all timestamps be in UTC. Correlating logs across services (gateway logs in UTC, backend in local) is harder and error-prone.

**Fix:** Set `LOG_USE_UTC=true`.

---

### CORS Configuration

Root `.env` sets:
```
CORS_ORIGINS=http://localhost:3088,http://192.168.1.200:3088,http://ichabod-linux.tailb1c51c.ts.net:3088,http://100.122.158.123:3088
```

But `backend/.env` overrides with:
```
CORS_ORIGINS=http://localhost:3000
```

**Status: WARN** — The `backend/.env` is likely the authoritative value loaded by the backend process (it is mounted into the container). This means the LAN and Tailscale origins configured in the root `.env` are being ignored, and only `localhost:3000` is allowed. Requests from `192.168.1.200:3088` or Tailscale would be blocked by CORS. This may be why the frontend works (same-host, or the nginx proxy strips CORS headers) but could cause issues with direct API access from other machines.

**Fix:** Update `backend/.env` CORS_ORIGINS to match the root `.env` value, or remove it from `backend/.env` and let compose pass it via environment variable.

---

### NEXT_PUBLIC_API_URL

The frontend is serving correctly at `http://localhost:3088` with the Local Authentication page rendering. The `NEXT_PUBLIC_API_URL` is set to `http://192.168.1.200:8088` (explicit LAN IP, not `auto`).

**Status: OK** — Frontend is loading. Login page renders. The explicit IP is correct for LAN access.

---

### Docker Port Exposure

| Container | Host Binding | Verdict |
|-----------|-------------|---------|
| frontend (3088) | `0.0.0.0:3088` | OK — intentional public access |
| backend (8088) | `0.0.0.0:8088` | WARN — see below |
| db/Postgres (5432) | `127.0.0.1:5432` | OK — localhost only |
| redis (6379) | `127.0.0.1:6379` | OK — localhost only |

**Status: WARN** — The backend API at port 8088 is bound to `0.0.0.0`, meaning it is accessible from any network interface, including external ones. Anyone on the LAN (or beyond, if the router forwards this port) can reach the raw API directly without going through the frontend. The database and Redis are correctly locked to localhost-only.

**Recommendation:** If nginx proxy manager is in front of this, lock the backend to `127.0.0.1:8088` so only the proxy can reach it. If direct LAN access to the API is needed, at minimum confirm `LOCAL_AUTH_TOKEN` is properly set so unauthenticated requests are rejected.

---

### Ollama Status

```json
Models available:
- qwen2.5-coder:7b-instruct  (7.6B params, Q4_K_M, ~4.7 GB)
- gemma3:4b                  (4.3B params, Q4_K_M, ~3.3 GB)
- moondream:latest            (1B vision model, ~1.7 GB)
- qwen2.5:3b                  (3.1B params, Q4_K_M, ~1.9 GB)
```

**Status: OK** — Ollama is running and responsive at `http://localhost:11434`. 4 models loaded totalling ~11.6 GB on disk. The gateway systemd drop-in correctly wires `OLLAMA_BASE_URL=http://127.0.0.1:11434` and `OLLAMA_API_KEY=ollama-local`.

**Note:** `OLLAMA_DISABLE_STREAMING=true` is set in the gateway drop-in. This is a known workaround for the tool-calling reliability issue documented in memory (`openclaw-local-lm-tool-calling-unreliable.md`). Correct to leave it.

---

### Gateway Systemd Drop-in

`~/.config/systemd/user/openclaw-gateway.service.d/ollama.conf` also contains the `N8N_API_KEY` and `N8N_BASE_URL` in plain text in a systemd drop-in file.

**Status: WARN** — The N8N API key is a JWT stored in a plaintext systemd drop-in. This is visible to any process running as the `ichabod` user via `systemctl --user cat openclaw-gateway`. It is not stored in Vaultwarden or GCP Secret Manager as the global CLAUDE.md conventions require. This is low-risk on a single-user machine but violates the documented secret hygiene policy.

**Recommendation:** Consider whether this is acceptable for a homelab-only key. If n8n is exposed externally, rotate this key and store it in Vaultwarden; pull it via a wrapper script at service start.

---

## Database Health

### Alembic Migration State

```
version_num: a9b1c2d3e4f7
```

**Status: OK** — Migrations ran successfully at startup (`DB_AUTO_MIGRATE=true` in root .env). The backend logs confirm: "Database migrations complete."

---

### FK Integrity

All foreign key relationships were inspected. Schema looks clean:

- Organizations → boards → agents → tasks chain is properly constrained
- `activity_events` FK to both `agents` and `tasks`
- `approvals` FK to `agent_id`, `board_id`, `task_id`

**Status: OK** — No orphaned FK violations found in the schema definition. The schema reflects a well-structured relational model.

---

### Missing FK Index

```
table_fingerprints.task_id → tasks (no index on the FK column)
```

**Status: WARN** — The `task_fingerprints` table has a foreign key to `tasks.id` with no index on the `task_id` column. Any query joining or filtering `task_fingerprints` by `task_id` (which is the primary access pattern for a fingerprint table) will do a full sequential scan. This will become a performance problem as tasks accumulate.

**Recommendation:** Add the index in the next Alembic migration:
```sql
CREATE INDEX ix_task_fingerprints_task_id ON task_fingerprints (task_id);
```

---

### Backup Strategy

**Status: ISSUE** — No backup for the Postgres data volume was found.

- Postgres data lives in Docker volume `openclaw-mission-control_postgres_data` at `/var/lib/docker/volumes/openclaw-mission-control_postgres_data/_data`
- No cron job exists that dumps or snapshots this volume
- No reference to a backup script in `~/scripts/` for this database
- Redis has 0 keys so is not a concern, but Postgres holds all board configs, agent registrations, tasks, and org data

**Recommendation:** Add a nightly pg_dump cron. Simple approach:
```bash
# Add to crontab -e
30 2 * * * docker exec openclaw-mission-control-db-1 pg_dump -U postgres mission_control | gzip > ~/backups/mission_control_$(date +\%Y\%m\%d).sql.gz && find ~/backups/ -name "mission_control_*.sql.gz" -mtime +7 -delete
```
This runs at 02:30 UTC (after n8n nightly automation), keeps 7 days of backups, and auto-purges old ones. Create `~/backups/` first.

---

## Log Review

### Backend Errors

No ERROR-level log entries found in the last 100 lines of backend logs.

**Status: OK** — Clean error log.

---

### Backend Warnings

Two categories of warnings were found:

**1. Skills marketplace returning 422 (Unprocessable Entity)**
```
GET /api/v1/skills/marketplace — 422 — 75ms
GET /api/v1/skills/marketplace — 422 — 4ms (repeated)
```
A 422 means the request was malformed or missing a required parameter. The marketplace endpoint is being called without required query parameters. This likely means the frontend is sending an incomplete request on page load. Not a crash, but the feature is non-functional.

**2. Slow skill pack sync requests**
```
POST /api/v1/skills/packs/{id}/sync — 4111ms (threshold: 1000ms)
POST /api/v1/skills/packs/{id}/sync — 1383ms (threshold: 1000ms)
```
Skill pack sync is taking 1.4–4 seconds. This is an external network call (fetching from clawhub.ai or another registry). The slow request logger is correctly flagging these. Acceptable for an infrequent background sync, but worth noting if it becomes a user-visible hang.

---

### Webhook Worker Logs

```
2026-04-10 21:59:11 INFO queue.worker.batch_started throttle_seconds=2.0
```

**Status: OK** — Worker started cleanly, no errors, no retries in the last 100 lines.

---

### Gateway Logs — Bootstrap File Truncation (Recurring)

This warning fires every 10 minutes like clockwork:

```
[agent] workspace bootstrap file AGENTS.md is 4119 chars (limit 4096); truncating
[agent] workspace bootstrap file SOUL.md is 2475 chars (limit 303); truncating
```

**Status: WARN — Two problems:**

**AGENTS.md** is 4,119 characters — 23 bytes over the 4,096-character limit. Every heartbeat cycle injects a truncated version of this file into the agent context. The truncation is near the end of the file, so it is probably cutting off the last instruction or closing section. This is a low-cost fix.

**Fix:** Trim 23+ characters from `AGENTS.md`. The easiest approach is to remove any trailing blank lines or tighten a verbose section.

**SOUL.md** is 2,475 characters against a limit of only 303 characters. This is an 8x overflow — it is being truncated to roughly 12% of its content on every heartbeat. Whatever behavioral/identity instructions are in `SOUL.md` beyond the first ~300 characters are never reaching the agent context.

**Fix (choose one):**
1. Radically condense `SOUL.md` to fit in 303 characters (a short mission statement / persona summary)
2. If the limit is configurable in the gateway, raise it for `SOUL.md` specifically
3. Move the full content into `AGENTS.md` (which has a larger limit) and keep `SOUL.md` as a one-line pointer

This is the highest-priority fix in this audit — agent behavior is being silently degraded on every heartbeat.

---

### Auth Rejections / Failed Heartbeats

No authentication failures or heartbeat rejections found in the backend logs.

**Status: OK** — Gateway is authenticating successfully. Heartbeat loop is healthy (logs show regular 10-minute heartbeat cycles in gateway journal).

---

## Action Priority List

| Priority | Finding | Effort |
|----------|---------|--------|
| P1 | SOUL.md truncated to 12% on every heartbeat — agent context degraded | 15 min |
| P1 | `backend/.env` BASE_URL blank — webhook/callback URLs will be broken | 2 min |
| P1 | No Postgres backup — all mission control data is unprotected | 10 min |
| P2 | AGENTS.md 23 bytes over limit — minor truncation each heartbeat | 5 min |
| P2 | `backend/.env` LOCAL_AUTH_TOKEN blank — verify auth is working | 5 min |
| P2 | `backend/.env` CORS_ORIGINS overrides root .env — LAN/Tailscale blocked | 5 min |
| P2 | LOG_USE_UTC=false — log timestamps are local time, not UTC | 2 min |
| P3 | 4 orphaned brain_mcp_server processes (~225 MB wasted RAM) | 10 min |
| P3 | Missing index on task_fingerprints.task_id — add in next migration | 10 min |
| P3 | Backend port 8088 bound to 0.0.0.0 — consider locking to 127.0.0.1 | 5 min |
| P3 | Gateway process at 622 MB — add MemoryMax= to systemd unit | 5 min |
| P4 | N8N API key in plaintext systemd drop-in | 15 min |
| P4 | Skills marketplace returning 422 — investigate missing query param | 30 min |
