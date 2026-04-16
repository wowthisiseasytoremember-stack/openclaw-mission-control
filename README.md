**Last Updated:** 2026-04-15 19:35 UTC

# OpenClaw Mission Control — ichabod Instance

OpenClaw Mission Control is the centralized governance and operations platform for running OpenClaw (the AI agent orchestration system) across teams. It provides unified task boards, agent lifecycle management, approval flows, gateway management, and an audit trail — all through a single web UI and REST API.

This instance is self-hosted on `ichabod` (Ubuntu 22.04 homelab server).

---

## Directory Structure

```
openclaw-mission-control/
├── backend/              Python (FastAPI) API server + database models
│   ├── app/
│   │   ├── api/          REST endpoints (tasks, agents, gateways, skills, etc.)
│   │   ├── models/       SQLModel ORM models (PostgreSQL via asyncpg)
│   │   ├── schemas/      Pydantic request/response schemas
│   │   └── core/         Logging, config, version utilities
│   ├── migrations/       Alembic database migration files
│   ├── tests/            Pytest test suite
│   └── pyproject.toml    Python dependencies (managed with uv)
├── frontend/             Next.js web UI
│   ├── src/app/          Next.js App Router pages
│   └── src/components/   UI components including skills marketplace
├── docs/                 Reference documentation
│   ├── architecture/     System design and data model overviews
│   ├── deployment/       Docker and production deployment guides
│   ├── operations/       Day-to-day ops and runbooks
│   └── troubleshooting/  Common issues and fixes
├── scripts/              Operational scripts (this directory)
│   ├── preflight.sh      Pre-flight health check — run before starting the stack
│   ├── init-skill.sh     Scaffold a new skill directory with SKILL.md template
│   └── check_markdown_links.py  CI link validator
├── skills/               Symlinks to ~/.claude/skills/* — Claude Code skill library
├── logs/                 Log output directory (gitignored)
├── compose.yml           Docker Compose stack definition
├── .env                  Active environment config (not committed)
├── .env.example          Template — copy to .env to start
├── CHANGELOG.md          Running history of changes to this deployment
├── OPERATIONS_AUDIT.md   Operations audit findings and recommendations
└── SECURITY_AUDIT.md     Security audit findings
```

---

## How to Start

### Pre-flight check first

```bash
/home/ichabod/openclaw-mission-control/scripts/preflight.sh
```

This verifies the config file exists, permissions are correct (600), and detects whether the OpenClaw process is running.

### Start the full stack (Docker)

```bash
cd /home/ichabod/openclaw-mission-control
docker compose -f compose.yml --env-file .env up -d --build
```

### Stop the stack

```bash
cd /home/ichabod/openclaw-mission-control
docker compose -f compose.yml --env-file .env down
```

### After pulling new changes

```bash
docker compose -f compose.yml --env-file .env up -d --build --force-recreate
```

---

## Service URLs (ichabod)

| Service | URL |
|---------|-----|
| Mission Control UI | http://192.168.1.200:3088 |
| Backend API | http://192.168.1.200:8088 |
| Backend health check | http://192.168.1.200:8088/healthz |
| Tailscale | http://100.122.158.123:3088 |

---

## Key Config Files

| File | Purpose |
|------|---------|
| `~/.openclaw/openclaw.json` | OpenClaw gateway config — agents, models, Telegram bot, gateway auth token. Permissions must be 600. |
| `.env` | Docker stack environment — ports, database credentials, AUTH_MODE, LOCAL_AUTH_TOKEN, CORS origins. |
| `.env.example` | Safe template showing all available variables. |

### Token warning

`~/.openclaw/openclaw.json` contains plaintext API keys for OpenRouter, Groq, and Gemini, plus the Telegram bot token and gateway auth token. This file has correct 600 permissions (owner-read only), but the keys are not referenced from environment variables — they are stored directly in the JSON. This is the current design; do not move them without testing that the openclaw process can read from env vars instead.

---

## Available Scripts

### `scripts/preflight.sh`

Checks that the deployment is ready before starting:
- `openclaw.json` exists
- `openclaw.json` has 600 permissions
- An `openclaw` process is running

### `scripts/init-skill.sh <skill-name>`

Scaffolds a new Claude Code skill directory under `skills/`:

```bash
./scripts/init-skill.sh my-new-skill
# Creates: skills/my-new-skill/SKILL.md and skills/my-new-skill/references/
```

---

## Skills

The `skills/` directory contains symlinks pointing to `~/.claude/skills/`. These are Claude Code skills available to the agent running on this machine — not OpenClaw Mission Control skills per se. They cover operations across all projects on ichabod.

To add a new skill scaffold:

```bash
cd /home/ichabod/openclaw-mission-control
./scripts/init-skill.sh <skill-name>
```

---

## Logs

Runtime logs go to `logs/`. This directory is gitignored. If containers are running, follow logs with:

```bash
docker compose -f compose.yml --env-file .env logs -f backend
docker compose -f compose.yml --env-file .env logs -f frontend
```

---

## Authentication

This instance runs in `AUTH_MODE=local` — a shared bearer token set via `LOCAL_AUTH_TOKEN` in `.env`. Token must be at least 50 characters. Do not commit the `.env` file.

---

## Python Backend (uv)

Dependencies are managed with `uv` (fast Python package manager) via `backend/pyproject.toml`. A `backend/uv.lock` lockfile is present. No separate `requirements.txt` is needed.

```bash
cd backend
uv sync          # install deps
uv run pytest    # run tests
```

---

## Hardcoded Versions — Known

`frontend/package.json` has `"version": "0.1.0"` — this is a standard npm package field, not a problem. Backend version is also `0.1.0` in `pyproject.toml`. These are intentional and track the upstream project version. The gateway version (`2026.4.9`) is tracked in `~/.openclaw/openclaw.json` under `meta.lastTouchedVersion`.
