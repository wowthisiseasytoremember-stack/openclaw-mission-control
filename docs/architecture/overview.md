**Last Updated:** 2026-04-10 08:45 UTC

# Architecture Overview

## System Overview

OpenClaw Mission Control is a multi-tenant governance platform for coordinating AI agents.
Human operators and AI agents share a single task board interface. The platform bridges
a Next.js web UI with a FastAPI backend, a PostgreSQL database, and the OpenClaw Gateway —
a separately-deployed WebSocket server that hosts live agent sessions.

**Key design principle:** Mission Control never holds a persistent WebSocket connection to the
gateway. Every gateway interaction is an on-demand connection: open, send one RPC call,
receive the result, close. This keeps the backend stateless and avoids managing connection
pools across requests.

---

## Component Diagram

```
                         ┌──────────────────────────────────────────┐
                         │             Browser (Next.js)            │
                         │  React Query · shadcn/UI · Tailwind CSS  │
                         │   Orval-generated API client / types     │
                         └──────────────┬───────────────────────────┘
                                        │ HTTP REST
                                        ▼
                         ┌──────────────────────────────────────────┐
                         │         FastAPI Backend (Python)         │
                         │                                          │
                         │  /api/v1/*  ──►  Routers                 │
                         │      │                                   │
                         │      ├── AuthMode (Clerk JWT / local)    │
                         │      ├── SecurityHeadersMiddleware       │
                         │      ├── CORSMiddleware                  │
                         │      └── RateLimiter (memory / Redis)    │
                         │                                          │
                         │  Services:                               │
                         │    GatewayDispatchService                │
                         │    GatewaySessionService                 │
                         │    lifecycle_orchestrator                │
                         │    WebhookDispatch (async)               │
                         └──────┬───────────────────┬──────────────┘
                                │                   │
                    SQLModel    │                   │  on-demand WebSocket
                    async ORM   │                   │  (open → call → close)
                                ▼                   ▼
                ┌───────────────────┐   ┌───────────────────────────────┐
                │   PostgreSQL 16   │   │    OpenClaw Gateway (WS)      │
                │                   │   │                               │
                │ boards, tasks,    │   │  Agent sessions               │
                │ agents, gateways, │   │  Chat history                 │
                │ webhooks,         │   │  Skills / cron / config       │
                │ approvals, etc.   │   │  Device pairing               │
                └───────────────────┘   └───────────────────────────────┘
                                                        ▲
                                                        │  persistent WebSocket
                                                        │  (managed by gateway)
                                           ┌────────────────────────┐
                                           │    AI Agent Process    │
                                           │  (Claude / other LLM)  │
                                           └────────────────────────┘

                ┌───────────────────┐
                │    Redis 7        │
                │                   │
                │  RQ webhook queue │
                │  Rate-limit store │
                │  (optional)       │
                └───────────────────┘
                        ▲
                        │ dequeue
                ┌───────────────────┐
                │  webhook-worker   │
                │  (RQ consumer)    │
                └───────────────────┘
```

---

## Services

| Service | Container | Default Port | What It Does |
|---------|-----------|-------------|--------------|
| `db` | postgres:16-alpine | 5432 | Primary data store |
| `redis` | redis:7-alpine | 6379 | Webhook delivery queue; optional rate-limit backend |
| `backend` | FastAPI (Python) | 8000 | REST API, business logic, gateway RPC client |
| `frontend` | Next.js | 3000 | Web UI, served as Next.js app |
| `webhook-worker` | Same image as backend | — | RQ worker that consumes inbound webhook deliveries |

---

## Data Flows

### 1. Webhook Inbound Flow

An external system sends an HTTP POST to a board webhook endpoint.

```
External System
    │
    │  POST /api/v1/boards/{board_id}/webhooks/{webhook_id}/ingest
    │  Headers: X-Hub-Signature-256 (optional HMAC)
    │  Body: arbitrary JSON payload (≤ webhook_max_payload_bytes)
    ▼
Backend: board_webhooks.py
    │
    ├── Validate HMAC signature (if webhook.secret is set)
    ├── Enforce payload size limit
    ├── Write BoardWebhookPayload row to PostgreSQL
    └── Enqueue QueuedInboundDelivery to Redis (RQ queue)

webhook-worker (RQ consumer)
    │
    ├── Dequeue item
    ├── Load Board, BoardWebhook, BoardWebhookPayload from DB
    ├── Identify target agent (webhook.agent_id or board lead)
    ├── Resolve gateway config for board
    ├── Open WebSocket to gateway
    ├── Send formatted WEBHOOK EVENT message to agent's session key
    └── Commit; retry with exponential backoff + jitter on failure
```

### 2. Agent Heartbeat Flow

Agents check in on a schedule to report status and receive instructions.

```
AI Agent
    │
    │  POST /api/v1/agent/heartbeat
    │  Headers: X-Agent-Token: <token>
    ▼
Backend: agent API
    │
    ├── Authenticate agent via X-Agent-Token
    ├── Update agent last_seen timestamp
    ├── Check for pending tasks (in-progress, assigned)
    └── Return instructions, board context, and next-action hints

Lifecycle Orchestrator (backend background/task context)
    │
    ├── Detect agents offline > 10 minutes
    ├── Attempt wake via gateway RPC ("wake" method)
    └── Reconcile provisioned sessions against expected state
```

### 3. Task Dispatch Flow

A human or lead agent assigns a task to a worker agent.

```
User / Lead Agent
    │
    │  PATCH /api/v1/tasks/{task_id}  (assign agent, set status)
    │  or POST /api/v1/tasks/{task_id}/trigger
    ▼
Backend: tasks.py / dispatch endpoint
    │
    ├── Update task in DB
    ├── Resolve gateway config for board
    ├── Open WebSocket to gateway
    ├── Send actionable instruction message to agent session
    └── Mark agent as online (wake if offline)
```

---

## Auth Modes

The backend supports two mutually exclusive authentication modes set via `AUTH_MODE`.

### `clerk` Mode

- User tokens are Clerk JWTs (JSON Web Tokens — signed bearer tokens issued by Clerk, a third-party auth provider).
- The backend validates token signature, issuer, and expiry against `CLERK_SECRET_KEY`.
- IAT (issued-at time) verification is configurable via `CLERK_VERIFY_IAT`.
- User roles and organization membership are stored in the Mission Control database, not in Clerk.

### `local` Mode

- All users share a single `LOCAL_AUTH_TOKEN` bearer token.
- Token must be at least 50 characters and must not be a placeholder value.
- Intended for self-hosted, single-operator deployments.

### Agent Auth

Agents authenticate separately from users using the `X-Agent-Token` header. Agent tokens are scoped to a specific agent record in the database and grant access only to that agent's assigned boards. Rate limiting applies to the agent auth path.

---

## Gateway RPC Overview

Mission Control communicates with the OpenClaw Gateway using a WebSocket-based RPC protocol.
The client lives in `backend/app/services/openclaw/gateway_rpc.py`.

### Connect Sequence

1. Backend opens a WebSocket connection to the gateway URL.
2. Gateway optionally sends a `connect.challenge` event containing a nonce.
3. Backend sends a `connect` RPC request with:
   - Protocol version negotiation (`minProtocol`/`maxProtocol` = 3)
   - Role (`operator`) and scopes (`operator.read`, `operator.admin`, `operator.approvals`, `operator.pairing`)
   - Client identity block (`id`, `version`, `platform`, `mode`)
   - Device auth block (Ed25519 signature over canonical payload, only in `device` mode)
   - Optional bearer token (`auth.token`)
4. Gateway responds with a connect result (session/hello payload).
5. Backend sends the actual RPC method call.
6. Backend reads the response and closes the connection.

### Connect Modes

| Mode | When Used | Auth Mechanism |
|------|-----------|----------------|
| `device` | Default | Ed25519 device keypair + optional bearer token |
| `control_ui` | `disable_device_pairing = true` on gateway config | Bearer token only; `Origin` header set |

Device identity is persisted at `~/.openclaw/identity/device.json` (or `OPENCLAW_GATEWAY_DEVICE_IDENTITY_PATH`). The device ID is the SHA-256 hash of the raw Ed25519 public key.

### RPC Message Format

All messages are JSON. Requests use type `req`; responses use type `res`.

```json
// Request
{
  "type": "req",
  "id": "<uuid4>",
  "method": "sessions.list",
  "params": {}
}

// Response
{
  "type": "res",
  "id": "<uuid4>",
  "ok": true,
  "payload": { ... }
}
```

---

## Key Configuration Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH_MODE` | Yes | — | `clerk` or `local` |
| `LOCAL_AUTH_TOKEN` | If `local` | — | Shared bearer token (min 50 chars) |
| `CLERK_SECRET_KEY` | If `clerk` | — | Clerk backend secret for JWT validation |
| `BASE_URL` | Yes | — | Absolute HTTP(S) URL for the backend (e.g. `http://localhost:8000`) |
| `DATABASE_URL` | Yes | `postgresql+psycopg://postgres:postgres@localhost:5432/openclaw_agency` | PostgreSQL connection string |
| `CORS_ORIGINS` | No | `""` | Comma-separated allowed origins |
| `RATE_LIMIT_BACKEND` | No | `memory` | `memory` or `redis` |
| `RATE_LIMIT_REDIS_URL` | If redis | Falls back to `RQ_REDIS_URL` | Redis URL for rate limiter |
| `RQ_REDIS_URL` | No | `redis://localhost:6379/0` | Redis URL for webhook delivery queue |
| `RQ_QUEUE_NAME` | No | `default` | RQ queue name |
| `RQ_DISPATCH_THROTTLE_SECONDS` | No | `15.0` | Sleep between webhook dispatch batches |
| `RQ_DISPATCH_MAX_RETRIES` | No | `3` | Max webhook delivery retry attempts |
| `WEBHOOK_MAX_PAYLOAD_BYTES` | No | `1048576` (1 MB) | Max webhook ingest payload size |
| `GATEWAY_MIN_VERSION` | No | `2026.02.9` | Minimum compatible gateway version |
| `DB_AUTO_MIGRATE` | No | `true` in dev | Run Alembic migrations at startup |
| `TRUSTED_PROXIES` | No | `""` | Comma-separated proxy IPs/CIDRs for X-Forwarded-For extraction |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `LOG_FORMAT` | No | `text` | `text` or `json` |
| `ENVIRONMENT` | No | `dev` | Deployment environment label |
