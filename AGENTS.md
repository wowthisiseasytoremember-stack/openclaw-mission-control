**Last Updated:** 2026-05-19 23:41 UTC

# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI service. Main app code lives in `backend/app/` with API routes in `backend/app/api/` (agents, gateways, boards, board_groups, skills, tasks, webhooks, approvals), data models in `backend/app/models/` (SQLModel ORM: Agent, Gateway, Board, BoardGroup, BoardGroupMemory, Task, Skill, etc.), schemas in `backend/app/schemas/` (Pydantic request/response schemas, includes gateway coordination schemas), service logic in `backend/app/services/` (business logic: board_group_snapshot, organizations, etc.; core OpenClaw gateway RPC and provisioning in `backend/app/services/openclaw/` including gateway_rpc (WebSocket client), provisioning, session_service, admin_service), and DB utilities in `backend/app/db/` (CRUD utilities, query manager, pagination, session). Core config, auth, rate limiting, logging, security headers, agent_tokens, agent_auth are in `backend/app/core/`.
- `backend/migrations/`: Alembic migrations (`backend/migrations/versions/` for generated revisions).
- `backend/tests/`: pytest suite (`test_*.py` naming).
- `backend/templates/`: backend-shipped templates used by gateway flows.
- `frontend/`: Next.js app. Routes under `frontend/src/app/`, shared components under `frontend/src/components/`, utilities under `frontend/src/lib/`.
- `frontend/src/api/generated/`: generated API client (orval); regenerate instead of editing by hand.
- `docs/`: contributor and operations docs (start at `docs/README.md`).
- `scripts/`: Preflight check, skill scaffolding.
- `skills/`: Symlinks to `~/.claude/skills/`.

## Build, Test, and Development Commands
- `make setup`: install/sync backend and frontend dependencies.
- `make check`: closest CI parity run (lint, typecheck, tests/coverage, frontend build).
- `docker compose -f compose.yml --env-file .env up -d --build`: run full stack.
- Fast local loop:
  - `docker compose -f compose.yml --env-file .env up -d db`
  - `cd backend && uv run uvicorn app.main:app --reload --port 8000`
  - `cd frontend && npm run dev`
- `make api-gen`: regenerate frontend API client (backend must be on `127.00.1:8000`).

## Coding Style & Naming Conventions
- Python: Black + isort + flake8 + strict mypy. Max line length is 100. Use `snake_case`.
- TypeScript/React: ESLint + Prettier. Components use `PascalCase`; variables/functions use `camelCase`.
- For intentionally unused destructured TS variables, prefix with `_` to satisfy lint config.

## Testing Guidelines
- Backend: pytest via `make backend-test`; coverage policy via `make backend-coverage` (writes `backend/coverage.xml` and `backend/coverage.json`).
- Frontend: vitest + Testing Library via `make frontend-test` (coverage in `frontend/coverage/`).
- Add or update tests whenever behavior changes.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (seen in history), e.g. `feat: ...`, `fix: ...`, `docs: ...`, `test(core): ...`.
- Keep PRs focused and based on latest `master`.
- Include: what changed, why, test evidence (`make check` or targeted commands), linked issue, and screenshots/logs when UI or operator workflow changes.

## Security & Configuration Tips
- Never commit secrets. Copy from `.env.example` and keep real values in local `.env`.
- Report vulnerabilities privately via GitHub security advisories, not public issues.

## Hardening Rules
- **Closeout Sync (inviolable):** Always write a per-session closeout entry to `~/brain/memory/ichabod/_close-log.md` and append a matching structured JSON line to `~/brain/memory/ichabod/_close-log.jsonl` using the closeout schema. Ensure you include the correct `linear.issue_key` so the watcher syncs it to the Linear board.
- Always use the `**Last Updated:** YYYY-MM-DD HH:MM UTC` header.
- No emojis.
- For operations and deployment docs, start at `docs/README.md`.
- Session logs and detailed session history go in CLAUDE.proposed.md, not here.

## Architectural Notes
- **Tech Stack:**
    - **Backend:** Python 3.12, FastAPI, SQLModel/asyncpg, Alembic, Redis (RQ queue), psycopg
    - **Frontend:** Next.js (App Router), TypeScript, React, Tailwind CSS
    - **Database:** PostgreSQL (primary), Redis (queue/rate-limits)
    - **Gateway Protocol:** WebSocket RPC (protocol v3) to OpenClaw gateway
    - **Auth:** Local bearer token or Clerk (configurable via AUTH_MODE)
- **Multi-Agent Orchestration:** The system orchestrates multiple agents across boards via a gateway-main / board-lead architecture:
    - **Gateway model** (`Gateway`): External OpenClaw gateway endpoint + auth. Each organization has one or more gateways.
    - **Agent model** (`Agent`): Autonomous actors assigned to boards. Key fields: board_id, gateway_id, status, heartbeat_config, identity_profile, is_board_lead.
    - **Board Group model** (`BoardGroup`): Logical grouping of boards within an org. Supports heartbeats and snapshots.
    - **Board Group Memory** (`BoardGroupMemory`): Context memory shared across agents in a board group; supports tags/mentions for agent routing.
    - **Lead routing:** Gateway lead message/broadcast endpoints allow the main agent to direct messages to specific board leads or broadcast to groups.
    - **Human escalation:** `GatewayMainAskUserRequest`/`Response` payloads for escalating decisions to end users.
    - **Device pairing:** Gateway device CRUD with public-key authentication for secure gateway connections.
    - **Provisioning lifecycle:** `AgentLifecycleService` manages agent create/update/heartbeat/delete with gateway RPC synchronization.
- **Telegram Gateway Integration:** Telegram is integrated as a **gateway channel** on the OpenClaw gateway (not a standalone bot in this repo):
    - Telegram bot token and configuration live in `~/.openclaw/openclaw.json` under the gateway's channel config, not in this repo's codebase.
    - The OpenClaw gateway handles Telegram webhook ingress/egress; Mission Control talks to the gateway via WebSocket RPC (chat.send, sessions.list, sessions.preview, etc.).
    - Gateway session endpoints (`/api/v1/gateways/sessions/*`) expose Telegram chat sessions through Mission Control's API for inspection and message sending.
    - No Telegram Python library is required in the backend — all Telegram traffic flows through the OpenClaw gateway WebSocket protocol.
- **MCP Integration:** MCP (Model Context Protocol) integration exists at the infrastructure level, not in this repo's code:
    - **Brain MCP server:** `/home/ichabod/mcp-brain/server.py` — runs as systemd service (`brain-mcp.service`) exposed via Cloudflare Tunnel at `brain.scoreapp.pro:8094`.
    - **Orval MCP:** `@orval/mcp` 8.3.0 dependency exists in `frontend/package-lock.json` for generating API client code.
    - Mission Control's API itself is designed to be consumed by LLM agents via the agent-auth endpoints (bearer tokens, `/api/v1/agent/*` routes) — effectively making this an MCP-compatible tool surface.

## Audit Notes
- **Contradictions:**
    - CLAUDE.md explicitly states "Database: PostgreSQL (primary), Redis (queue/rate-limits)", while AGENTS.md does not specify the database type, but `SQLModel/asyncpg` and `psycopg` in the tech stack imply PostgreSQL. No explicit contradiction, but good to confirm.
- **TODOs/WIP:**
    - "Multi-server overlap: 3 brain MCP servers were running simultaneously (ports 8091 SSE, 8094 HTTP, basic-memory stdio at 1.2GB). Consolidation is pending." This indicates a pending task for MCP server consolidation.
    - "If no Brain MCP tool is available, note it as a gap and proceed — but flag it at the end of the session." This implies a potential gap in tooling availability.
