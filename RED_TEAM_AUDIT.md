**Last Updated:** 2026-04-15 17:25 UTC

# Red Team Audit — OpenClaw Mission Control

**Platforms:** Python (FastAPI), Web (Next.js), Homelab, Docker
**Phases executed:** Secrets / Auth / Injection / Network / Dependencies

---

## FINDINGS

| ID | Weight | Severity | Confidence | Title | File:Line or Artifact | Cross-Team | Delta |
|----|--------|----------|------------|-------|-----------------------|------------|-------|
| R-01 | 1 | P1 | 9 | SSRF via admin-controlled `gateway_url` query parameter — no allowlist, connects to arbitrary WebSocket | backend/app/api/gateway.py:38, backend/app/services/openclaw/session_service.py:107-143 | | New |
| R-02 | 1 | P1 | 9 | SSRF via outbound webhook `target_url` — AnyHttpUrl allows internal IPs (169.254.x, 10.x, 192.168.x) | backend/app/schemas/board_outbound_webhooks.py:48, backend/app/services/outbound_webhooks/dispatch.py:117-122 | B-02, B-03, P-07 | New |
| R-03 | 1 | P1 | 9 | Frontend port bound to 0.0.0.0 — reachable on all interfaces without reverse proxy | compose.yml:74 | | New |
| R-04 | 1 | P1 | 8 | CORS `allow_credentials=True` with `allow_methods=["*"]` and `allow_headers=["*"]` — no guard against `CORS_ORIGINS=*` misconfiguration | backend/app/main.py:475-480 | | New |
| R-05 | 2 | P2 | 8 | Inbound webhook endpoint unauthenticated by design — HMAC skipped when webhook has no `secret`, stores payloads as agent memory | backend/app/api/board_webhooks.py:516-576 | | New |
| R-06 | 2 | P2 | 8 | Token prefix (6 chars) logged on failed agent auth — reduces brute-force search space by 36 bits if logs leak | backend/app/core/agent_auth.py:136-138, 182-184 | | New |
| R-07 | 2 | P2 | 8 | `allow_insecure_tls` disables cert verification (ssl.CERT_NONE + check_hostname=False) per gateway — compounds SSRF (R-01) | backend/app/services/openclaw/gateway_rpc.py:201-216 | | New |
| R-08 | 2 | P2 | 8 | Rate limiter fail-open on Redis errors — Redis outage eliminates rate limiting on auth endpoints | backend/app/core/rate_limit.py:164-171 | | New |
| R-09 | 2 | P2 | 9 | No HSTS or CSP headers in backend SecurityHeadersMiddleware | backend/app/core/config.py:56-59 | | New |
| R-10 | 2 | P2 | 9 | No security headers (CSP, HSTS) for Next.js-served pages — frontend next.config.ts has no headers() block | frontend/next.config.ts | | New |
| R-11 | 2 | P2 | 9 | `uv` installer piped from internet at build time via `curl \| sh` — no pinned version or checksum | backend/Dockerfile:16-17 | | New |
| R-12 | 2 | P2 | 9 | Unpinned Docker base images (`python:3.12-slim`, `node:20-alpine`) — floating tags, no digest pinning | backend/Dockerfile:3, frontend/Dockerfile:1,9,23 | | New |
| R-13 | 2 | P2 | 9 | Gateway `url` field typed as plain `str` — no scheme, hostname, or IP validation in Pydantic schema | backend/app/schemas/gateways.py:18 | | New |
| R-14 | 2 | P2 | 9 | Developer LAN IP `192.168.1.101` hard-coded in `allowedDevOrigins` — copied into production Docker image | frontend/next.config.ts:8 | | New |
| R-15 | 2 | P2 | 7 | Agent token auth is O(n) full table scan with PBKDF2 (200k iterations) per agent — timing oracle and DoS under load | backend/app/core/agent_auth.py:51-57 | | New |
| R-16 | 2 | P2 | 7 | `is_super_admin` field exists in User model but is never enforced in any gate — latent privilege-confusion risk | backend/app/models/users.py:26, backend/app/services/admin_access.py:18 | | New |
| R-17 | 2 | P2 | 7 | `dangerouslySetInnerHTML` style injection with server-derived chart config — currently safe (static colors) but fragile pattern | frontend/src/components/charts/chart.tsx:132-149 | | New |

---

## METRICS

- Total findings: 17
- P0 (ship-blocker): 0
- P1 (high): 4
- P2 (low): 13
- Filtered (confidence < 7 or hard-excluded): 3
- Phases executed: Secrets / Auth / Injection / Network / Dependencies

---

## FILTERED

| ID | Reason | Original Confidence |
|----|--------|---------------------|
| R-F1 | Hard-excluded: auth rate limiting exists (20/min per-IP) — weakness is design gap (per-IP only, no account lockout), not absence | 7 |
| R-F2 | Hard-excluded: no Docker network isolation is informational — requires container compromise first, no direct external attack path | 9 |
| R-F3 | Hard-excluded: CI test token in .github/workflows/ci.yml:106 is intentional test fixture with sequential digits — test file exclusion | 10 |

---

## ALERTS

- No SQL injection, command injection, path traversal, or SSTI found — ORM parameterized queries used throughout, no subprocess/eval/exec in app code.
- No hardcoded secrets found in tracked source files — .env properly gitignored, compose.yml uses variable substitution.
- Lock files (uv.lock, package-lock.json) committed with integrity hashes — supply chain controls are sound.
- No CVEs with known public exploits found in current dependency versions.
- Positive controls noted: non-root Docker users, no docker.sock mount, no privileged containers, proper open-redirect validation in frontend auth flow.
