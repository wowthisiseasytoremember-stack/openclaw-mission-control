**Last Updated:** 2026-04-15 17:30 UTC

# Blue Team QoL Audit — OpenClaw Mission Control

**Platforms:** Python (FastAPI), Web (Next.js), Homelab, Docker
**Persona:** Lead Solutions Architect / UX Researcher

**Superpowers claimed (README):**
1. Unified task boards
2. Agent lifecycle management
3. Approval flows
4. Gateway management
5. Audit trail — "all through a single web UI and REST API"

---

## FINDINGS

| ID | Weight | Severity | Confidence | Title | File:Line or Artifact | Cross-Team | Delta |
|----|--------|----------|------------|-------|-----------------------|------------|-------|
| B-01 | 0 | S | 10 | `LOCAL_AUTH_TOKEN` blank in `.env.example` with no generation command — backend crashes silently in `docker compose up -d` mode | .env.example:25, backend/app/core/config.py:101-109 | P-05 | New |
| B-02 | 0 | S | 10 | Inbound webhook CRUD has zero frontend UI — operators must use raw API for a documented feature | frontend/src/app/ (no webhook pages exist) | R-02, P-07 | New |
| B-03 | 0 | S | 10 | Outbound webhook management has zero frontend UI — cannot configure, test, or view from browser | frontend/src/components/ (no webhook components exist) | R-02, P-07 | New |
| B-04 | 0 | S | 9 | "Soul" is an undefined domain term used throughout API and schemas — no UI or doc explanation of what it means | backend/app/api/souls_directory.py:1, backend/app/main.py:88-91 | | New |
| B-05 | 0 | S | 8 | No web UI surface for agent task operations — agent work is API-only; web users can observe task column changes but cannot see which agent is working or why | backend/app/api/agent.py (entire file), frontend (no agent-work UI) | P-09 | New |
| B-06 | 1 | A | 9 | Preflight script fails hard (`exit 1`) for any user without OpenClaw gateway installed — blocks the documented startup path even though the Docker stack runs fine without it | scripts/preflight.sh:6-10, 28-30 | | New |
| B-07 | 1 | A | 10 | ichabod-specific IPs (192.168.1.200) and non-default ports (3088/8088) hardcoded in README with no caveat — confuses new users who expect localhost:3000 defaults | README.md:83-88 | | New |
| B-08 | 1 | A | 9 | Default `DATABASE_URL` in config uses `openclaw_agency` but Compose stack creates `mission_control` — non-Docker developers get silent connection failure | backend/app/core/config.py:40, compose.yml:8 | | New |
| B-09 | 1 | A | 9 | Gateway detail page discards `error` and `main_session_error` fields from status response — offline gateways show a red dot with no diagnosis or recovery action | frontend/src/app/gateways/[gatewayId]/page.tsx:148-150 | | New |
| B-10 | 1 | A | 9 | Gateway token always `null` in status query due to server-side redaction — status indicator gives false "Offline" for token-authenticated gateways | frontend/src/app/gateways/[gatewayId]/page.tsx:117, backend/app/schemas/gateways.py:76 | | New |
| B-11 | 1 | A | 9 | Lead notification failure silently swallowed on approval resolution — reviewer gets 200 OK even if agent was never notified; no retry mechanism | backend/app/api/approvals.py:479-485 | | New |
| B-12 | 1 | A | 9 | Webhook `try_send_agent_message` result discarded — gateway-offline during ingest means board lead never notified, response still returns 202 | backend/app/api/board_webhooks.py:334 | | New |
| B-13 | 1 | A | 9 | All 401 errors return bare `"Unauthorized"` with no `WWW-Authenticate` header and no hint about which auth mode or credential is expected | backend/app/api/deps.py:92,104, backend/app/core/auth.py:444-486 | | New |
| B-14 | 1 | A | 9 | Malformed `since` query param silently discarded — SSE stream starts from "now" with no error, operator trying to replay history gets current events | backend/app/api/board_memory.py:54-67, backend/app/api/board_group_memory.py:116-129 | | New |
| B-15 | 1 | A | 9 | Invalid `NEXT_PUBLIC_AUTH_MODE` (e.g. capital "Local") silently shows Clerk sign-in page on a local-auth deployment — no validation or warning | frontend/src/auth/localAuth.ts:8-10 | | New |
| B-16 | 1 | A | 9 | Missing `AUTH_MODE` env var produces Pydantic `ValidationError` traceback at startup — not a user-friendly "AUTH_MODE is required" message | backend/app/core/config.py:43 | | New |
| B-17 | 1 | A | 9 | Agent-on-user-endpoint raises 403 (Forbidden) instead of 401 — conflates wrong actor type with insufficient permissions | backend/app/services/admin_access.py:21 | | New |
| B-18 | 1 | A | 9 | Auth bootstrap 401 response body doesn't match its own OpenAPI example schema — clients expecting structured `code` field get `{"detail": "Unauthorized"}` | backend/app/api/auth.py:60-61 | | New |
| B-19 | 1 | A | 8 | Agent creation form has no gateway selector — gateway is inferred server-side; if board has no gateway, creation fails with no actionable UI guidance | frontend/src/app/agents/new/page.tsx:101-129 | | New |
| B-20 | 1 | A | 8 | "Board Memory" and "Board Group Memory" conflate note-store and chat-bus under one noun — undocumented that `is_chat=true` triggers live agent notifications vs persistent storage | backend/app/api/board_memory.py:42, backend/app/api/board_group_memory.py:53-61 | | New |
| B-21 | 2 | B | 9 | `cp .env.example .env` step missing from root README — user jumps to `docker compose up` and gets a crash | README.md:49-68 | | New |
| B-22 | 2 | B | 9 | No prerequisites section in README (Docker, Compose v2) — `docker: command not found` on fresh machines | README.md:49 | | New |
| B-23 | 2 | B | 9 | `install.sh` (963-line interactive wizard) not mentioned in README or getting-started doc — most useful tool is invisible | README.md, docs/getting-started/README.md | | New |
| B-24 | 2 | B | 9 | `require_approval_for_done=True` default on boards — tasks can never reach `done` without approval, invisible at board creation | backend/app/schemas/boards.py:32 | | New |
| B-25 | 2 | B | 9 | Gateway main-agent prerequisite for board creation invisible in UI — 422 error with no guidance on how to provision one | backend/app/api/boards.py:105-115, frontend/src/app/boards/new/page.tsx:236-249 | | New |
| B-26 | 2 | B | 9 | SSE approval stream polls DB every 2 seconds per connected client — no pub/sub or backpressure | backend/app/api/approvals.py:54 | | New |
| B-27 | 2 | B | 9 | No standalone audit-trail page in frontend — cross-board activity timeline only accessible via API | frontend/src/app/ (no activity page) | | New |
| B-28 | 2 | B | 9 | `RQ_DISPATCH_THROTTLE_SECONDS=15` hidden from `.env.example` — operators debugging "why is agent slow" have no config pointer | backend/app/core/config.py:79 | | New |
| B-29 | 2 | B | 9 | Empty `event_types` on outbound webhook silently subscribes to all events — undocumented default | backend/app/schemas/board_outbound_webhooks.py:50 | | New |
| B-30 | 2 | B | 8 | Read-only board members see no explanation for missing "Create task" button — it simply disappears | frontend/src/app/boards/[boardId]/page.tsx:4612-4614 | | New |
| B-31 | 2 | B | 8 | Agent detail fetches 200 all-org events then filters client-side — no `agent_id` filter on activity API | frontend/src/app/agents/[agentId]/page.tsx:73-84, backend/app/api/activity.py:245 | | New |
| B-32 | 2 | B | 8 | `LOCAL_AUTH_TOKEN` stored in `sessionStorage` — cleared on browser close, user must re-enter each session, never disclosed on sign-in screen | frontend/src/auth/localAuth.ts:13 | | New |
| B-33 | 2 | B | 8 | `db_auto_migrate` declared `False` in config but silently overridden to `True` in dev environment — mental model mismatch | backend/app/core/config.py:74, 139-140 | | New |
| B-34 | 2 | B | 8 | `log_use_utc` defaults to `False` — server logs use local timezone, surprising for a server application | backend/app/core/config.py:90 | | New |
| B-35 | 2 | B | 8 | No post-creation guidance after agent registration — provisioning state with no hint of what must happen next or how long to wait | frontend/src/app/agents/new/page.tsx:85-88 | | New |
| B-36 | 2 | B | 7 | Per-board approval load errors merged into single undifferentiated string on global approvals page | frontend/src/app/approvals/page.tsx:161-165 | | New |
| B-37 | 2 | B | 7 | Internal board events (`lead_notified`, `lead_notify_failed`) missing from frontend live-feed event set | backend/app/api/boards.py:341-359, frontend/src/app/boards/[boardId]/page.tsx:189-204 | | New |
| B-38 | 2 | B | 7 | `souls_directory.get_markdown` leaks raw exception strings in 502 response body | backend/app/api/souls_directory.py:79-83 | | New |

---

## METRICS

- Total findings: 38
- S-tier (ship-blocker friction): 5
- A-tier (high friction): 15
- B-tier (low friction): 18
- Filtered (out of scope, low confidence): 3
- CUJs traced: 3 (Install/first run, Task/agent management, Gateway/approvals/webhooks)
- Claims validated: 5 (task boards, agent lifecycle, approval flows, gateway management, audit trail)
- Mental model breaks found: 7 (Soul terminology, Board Memory duality, require_approval_for_done default, db_auto_migrate override, AUTH_MODE case sensitivity, 403-vs-401 actor confusion, sessionStorage token persistence)

---

## FILTERED

| ID | Reason | Original Confidence |
|----|--------|---------------------|
| B-F1 | Purple Team scope — outbound webhook `dispatch_board_event` not wired to any real task/approval events (explicitly documented as "next integration step") | 10 |
| B-F2 | Purple Team scope — no `REDIS_PORT` in `.env.example` despite compose.yml using it — missing config surface, not friction on existing feature | 7 |
| B-F3 | Red Team scope — `souls_directory` exception leakage is an information disclosure vulnerability | 8 |

---

## ALERTS

- The README's promise of "a single web UI and REST API" is only partially fulfilled: webhooks (inbound and outbound) have no UI at all. Agent task operations are API-only. The audit trail has no dedicated page.
- Claim validation for "audit trail" partially fails: the backend records thorough activity events, but the frontend has no standalone audit page — only embedded panels in board and agent detail views.
- CUJ #1 (first run) has the highest concentration of friction: 3 S-tier and 6 A-tier findings in the setup path alone.
- The preflight script and the README's startup instructions are misaligned: preflight checks for the OpenClaw gateway process (not needed for the Docker stack), while the README omits the `cp .env.example .env` step that IS needed.
- 7 mental model breaks identified — the highest-impact is the "Soul" terminology which pervades the API surface with no user-facing explanation.
