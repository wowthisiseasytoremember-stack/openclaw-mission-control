**Last Updated:** 2026-05-03 23:20 UTC

# Changelog

All notable changes to OpenClaw Mission Control are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## 2026-05-03 23:20 UTC

### Fixed
- Switched primary model from Gemini 2.5 Flash (LiteLLM) to DeepSeek V4 Flash via OpenRouter — Gemini credits exhausted, all 7 cron jobs had 9+ consecutive failures
- Removed hardcoded `gemini/gemini-2.5-flash` model from nightly-memory-consolidation cron job — now inherits default
- Updated fallback chain: DeepSeek V4 Flash (primary) -> Llama 3.3 70B free -> Gemma 4 31B free -> Qwen 2.5 3B local
- Resolved gateway port conflict causing systemd "failed" state after restart

### Changed
- Enabled 30m heartbeat on main and job-agent (previously only mc-gateway had heartbeat)
- Switched rate limiter backend from in-memory to Redis (shared across backend + webhook-worker containers)

### Investigated
- Memory plugin: main workspace healthy, job-agent and mc-gateway have dirty memory dirs (non-blocking)
- Node service: confirmed optional, not required for current installation
- Security audit H-2 (local auth rate limiting) and H-3 (gateway token redaction): already implemented in commit 22c57c3

**For Produce:** OpenClaw hardening session — model switch to DeepSeek V4 Flash, cron jobs unblocked, heartbeats enabled, Redis rate limiter activated. Security H-2/H-3 already shipped.

---

## 2026-04-25 00:00 UTC

### Changed
- Upgraded OpenClaw gateway from v2026.4.9 to v2026.4.23 (14 minor versions)
- Bumped GATEWAY_MIN_VERSION from 2026.02.9 to 2026.4.9 in backend config
- Systemd service description and version env var auto-updated by gateway updater

---

## [Unreleased]

> No git tags have been cut yet. All commits below represent the current unreleased state of `master`.

---

### Features

- Require objective and success metrics when board type is `goal`
- Run-at-boot support via systemd (Linux) and launchd (macOS) with auth token re-sync docs
- Docker watch mode for automatic frontend rebuilds during development
- Make `BASE_URL` a required configuration field with validation
- Add Redis-backed rate limiter with configurable backend (`RATE_LIMIT_BACKEND`)
- Add configurable `signature_header` for webhook HMAC verification
- Add trusted client-IP extraction from proxy headers (`TRUSTED_PROXIES`)
- Make webhook payload size limit configurable (`WEBHOOK_MAX_PAYLOAD_BYTES`)
- Add read-only webhook payload fetch endpoint for agents (`/api/v1/agent/boards/{id}/webhook-payloads/{payload_id}`)
- Add dashboard redesign with improved metrics and activity feed
- Add Cypress end-to-end tests for critical flows (boards, approvals, packs)
- Add mobile-responsive layout for dashboard and board views
- Add security hardening: HMAC webhook verification, rate limiting on agent auth, 1 MB payload cap, non-root Docker containers, security response headers
- Add agent task workflow: wake assignee on assignment, lead can move inbox → in-progress on assignment
- Add onboarding improvements for new boards
- Add macOS support in installer (`install.sh`)

### Fixes

- Replace hardcoded `platform.python` with host OS value in gateway RPC connect params (cross-platform pairing fix)
- Provide `BASE_URL` in Docker bootstrap environment
- Normalize sidebar width to 260px; fix ghost re-open on navigation
- Fix mobile sidebar z-index above sticky page headers
- Fix Dockerfile `chown` to use `COPY --chown` instead of `RUN chown -R` (build performance)
- Fix Alpine-compatible `addgroup`/`adduser` flags in frontend Dockerfile
- Normalize deprecated `postgres://` URLs to `postgresql+psycopg://`
- Fix rate-limit Redis client to use `redis.asyncio`, share a single client per URL
- Redact credentials from Redis URL in rate-limit error messages
- Normalize webhook secret via schema validator; exclude signature and auth headers from payload capture
- Fix `BASE_URL` missing from Makefile migration check environment variables
- Fix fail-open auth vulnerability, streaming payload size bypass, and rate limiter memory leak (security review)
- Redact gateway tokens from API read responses
- Fix agent session message endpoint to require org-admin authorization
- Allow lead to set task `inbox` → `in_progress` when assigning an agent
- Wake assignee online on assignment and transition to in-progress
- Restore `GatewayRead.token` field to avoid frontend breaking change (revert of token redaction from read model)

### Chores

- Bump `next`, `flatted`, and other npm dependencies (Dependabot)
- Add `black`, `isort`, `flake8`, and `pre-commit` to backend toolchain
- Replace `chown -R` with `COPY --chown` in both Dockerfiles

---

## Earlier History (pre-versioning)

The following entries summarize major development phases before the project reached a release cadence.

### Gateway Integration Phase

- Implement OpenClaw gateway WebSocket RPC client (`gateway_rpc.py`) with device pairing and token auth
- Add device identity management using Ed25519 keypairs (`device_identity.py`)
- Add `GatewayDispatchService` for DB-backed gateway config resolution and agent message dispatch
- Add `sessions.list`, `sessions.patch`, `sessions.delete`, `chat.send`, `chat.history` RPC helpers
- Add gateway version compatibility check (`GATEWAY_MIN_VERSION`)
- Add gateway lifecycle orchestration: provisioning, heartbeat, wake, and reconciliation services
- Add agent session key namespace constants (`agent:mc-gateway-{id}:main`)

### Webhook System

- Add board webhooks: registration, HMAC verification, payload storage, and RQ (Redis Queue) dispatch worker
- Add inbound webhook delivery queue with exponential backoff and jitter retry
- Add `webhook-worker` Docker service for background queue processing

### Board & Task System

- Add boards, tasks, board groups, board memory, task comments with reply threading
- Add kanban board view with 5-second live polling
- Add task dependencies and blocked-task 409 error handling
- Add custom fields, tags, and approvals workflow
- Add board onboarding state machine
- Add task trigger button and backend dispatch endpoint for agent notifications

### Agent Management

- Add agent CRUD, provisioning/deprovisioning via OpenClaw gateway
- Add agent board access scoping, lead/worker role differentiation
- Add agent heartbeat tracking and offline detection (10-minute threshold)
- Add skills marketplace: install, update, uninstall, sync

### Auth & Security

- Add dual auth modes: `clerk` (Clerk JWT) and `local` (shared bearer token)
- Add agent authentication via `X-Agent-Token` header
- Add organization-scoped board and agent access policies
- Add security response headers middleware (X-Content-Type-Options, X-Frame-Options, Referrer-Policy)

### Infrastructure

- Scaffold Next.js (React) frontend with Tailwind CSS, shadcn/UI, and Orval-generated API types
- Scaffold FastAPI backend with SQLModel (PostgreSQL), Alembic migrations, and async sessions
- Add Docker Compose stack: `db`, `redis`, `backend`, `frontend`, `webhook-worker`
- Add installer script (`install.sh`) for Linux and macOS
- Add React Query with refetch-on-focus/reconnect for fresh UI data
- Squash Alembic migrations into single baseline
- Add `ruff`, `mypy` type checking, and CI workflows

---

[Unreleased]: https://github.com/abhi1693/openclaw-mission-control/compare/master...HEAD
- [2026-04-18 18:31 UTC] unknown: unknown
