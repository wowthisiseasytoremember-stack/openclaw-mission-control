> ⚠️ STOP. Before reading further:
> 1. Use the Brain MCP tool to read: claude-portable/ORIENTATION.md
> 2. Familiarize yourself with the full system — who Justin is, what's running, core rules, key paths.
> 3. Then return here and continue reading.
>
> If no Brain MCP tool is available, note it as a gap and proceed — but flag it at the end of the session.
**Last Updated:** 2026-05-19 23:41 UTC

# OpenClaw Mission Control — Claude Context

Management and monitoring dashboard for OpenClaw autonomous agents. Provides centralized governance, task boards, agent lifecycle management, approval flows, gateway management, and audit trail via a web UI (Next.js) and REST API (FastAPI).

---

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLModel/asyncpg, Alembic, Redis (RQ queue), psycopg
- **Frontend:** Next.js (App Router), TypeScript, React, Tailwind CSS
- **Database:** PostgreSQL (primary), Redis (queue/rate-limits)
- **Gateway Protocol:** WebSocket RPC (protocol v3) to OpenClaw gateway
- **Auth:** Local bearer token or Clerk (configurable via AUTH_MODE)

---

## Project Structure

| Directory | Purpose |
|-----------|---------|
| `backend/app/api/` | REST endpoints: agents, gateways, boards, board_groups, skills, tasks, webhooks, approvals |
| `backend/app/models/` | SQLModel ORM: Agent, Gateway, Board, BoardGroup, BoardGroupMemory, Task, Skill, etc. |
| `backend/app/schemas/` | Pydantic request/response schemas (includes gateway coordination schemas) |
| `backend/app/services/openclaw/` | Core gateway integration: gateway_rpc (WebSocket client), provisioning, session_service, admin_service |
| `backend/app/services/` | Business logic: board_group_snapshot, organizations, etc. |
| `backend/app/core/` | Config, auth, rate limiting, logging, security headers, agent_tokens, agent_auth |
| `backend/app/db/` | CRUD utilities, query manager, pagination, session |
| `frontend/src/app/` | Next.js App Router pages |
| `frontend/src/api/generated/` | Auto-generated API client (orval) |
| `docs/` | Architecture, deployment, operations, troubleshooting docs |
| `scripts/` | Preflight check, skill scaffolding |
| `skills/` | Symlinks to ~/.claude/skills/ |

---

## Multi-Agent Orchestration

The system orchestrates multiple agents across boards via a gateway-main / board-lead architecture:

- **Gateway model** (`Gateway`): External OpenClaw gateway endpoint + auth. Each organization has one or more gateways.
- **Agent model** (`Agent`): Autonomous actors assigned to boards. Key fields: board_id, gateway_id, status, heartbeat_config, identity_profile, is_board_lead.
- **Board Group model** (`BoardGroup`): Logical grouping of boards within an org. Supports heartbeats and snapshots.
- **Board Group Memory** (`BoardGroupMemory`): Context memory shared across agents in a board group; supports tags/mentions for agent routing.
- **Lead routing:** Gateway lead message/broadcast endpoints allow the main agent to direct messages to specific board leads or broadcast to groups.
- **Human escalation:** `GatewayMainAskUserRequest`/`Response` payloads for escalating decisions to end users.
- **Device pairing:** Gateway device CRUD with public-key authentication for secure gateway connections.
- **Provisioning lifecycle:** `AgentLifecycleService` manages agent create/update/heartbeat/delete with gateway RPC synchronization.

---

## Telegram Gateway Integration

Telegram is integrated as a **gateway channel** on the OpenClaw gateway (not a standalone bot in this repo):

- Telegram bot token and configuration live in `~/.openclaw/openclaw.json` under the gateway's channel config, not in this repo's codebase.
- The OpenClaw gateway handles Telegram webhook ingress/egress; Mission Control talks to the gateway via WebSocket RPC (chat.send, sessions.list, sessions.preview, etc.).
- Gateway session endpoints (`/api/v1/gateways/sessions/*`) expose Telegram chat sessions through Mission Control's API for inspection and message sending.
- No Telegram Python library is required in the backend — all Telegram traffic flows through the OpenClaw gateway WebSocket protocol.

---

## MCP Integration

MCP (Model Context Protocol) integration exists at the infrastructure level, not in this repo's code:

- **Brain MCP server:** `/home/ichabod/mcp-brain/server.py` — runs as systemd service (`brain-mcp.service`) exposed via Cloudflare Tunnel at `brain.scoreapp.pro:8094`.
- **Multi-server overlap:** 3 brain MCP servers were running simultaneously (ports 8091 SSE, 8094 HTTP, basic-memory stdio at 1.2GB). Consolidation is pending.
- **Orval MCP:** `@orval/mcp` 8.3.0 dependency exists in `frontend/package-lock.json` for generating API client code.
- Mission Control's API itself is designed to be consumed by LLM agents via the agent-auth endpoints (bearer tokens, `/api/v1/agent/*` routes) — effectively making this an MCP-compatible tool surface.

---

## Rules
- Always use the `**Last Updated:** YYYY-MM-DD HH:MM UTC` header.
- No emojis.
- Read AGENTS.md for repository conventions (build/test commands, coding style, PR guidelines).
- For operations and deployment docs, start at `docs/README.md`.
- Session logs and detailed session history go in CLAUDE.proposed.md, not here.
