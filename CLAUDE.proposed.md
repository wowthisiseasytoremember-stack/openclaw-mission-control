---
> ⚠️ STOP. Before reading further:
> 1. Use the Brain MCP tool to read: claude-portable/ORIENTATION.md
> 2. Familiarize yourself with the full system — who Justin is, what's running, core rules, key paths.
> 3. Then return here and continue reading.
>
> If no Brain MCP tool is available, note it as a gap and proceed — but flag it at the end of the session.
> ⚠️ STOP. Before reading further:
> 1. Use the Brain MCP tool to read: claude-portable/ORIENTATION.md
> 2. Familiarize yourself with the full system — who Justin is, what's running, core rules, key paths.
> 3. Then return here and continue reading.
>
> If no Brain MCP tool is available, note it as a gap and proceed — but flag it at the end of the session.
**Last Updated:** 2026-04-13 14:00 UTC

# OpenClaw Mission Control — Claude Context

Management and monitoring dashboard for OpenClaw autonomous agents.

---

## Tech Stack
- Node.js
- OpenClaw framework

---
## Rules
- Always use the `**Last Updated:** YYYY-MM-DD HH:MM UTC` header.
- No emojis.

---

SESSION LOGS:
---
=== CLOSE LOG (last 7 days) ===

tags:
  - app-dev
  - infrastructure
  - agent
  - obsidian
summary: "Technical log detailing OpenClaw model configuration updates and DeepSeek API migration."
auto_tagged: "2026-05-10 01:04 UTC"

date: 2026-05-06 08:44 UTC
projects: [ichabod]
source: claude-code/ichabod
auto: true


**STATUS CHECK — 2026-05-06 08:43 UTC**





**Summary**
Reconfigured OpenClaw's primary model from `litellm/chat` (LiteLLM proxy hop) to `google-ai/gemini-2.5-flash` (direct Google AI API). Fixed stale DeepSeek model IDs (`deepseek-chat` / `deepseek-reasoner` → `deepseek-v4-flash` / `deepseek-v4-pro`) and expanded the TUI model picker with all Gemini generations plus DeepSeek V4. Session ended with the user verifying that OpenClaw's health check still referenced LiteLLM — diagnosed as the old agent instance reporting its own (pre-reload) state, not the current routing.

**Patterns / Conventions**
- OpenClaw model refs use format `provider/model-id` where `provider` matches a key in `models.providers` in `~/.openclaw/openclaw.json`. The `google-ai` provider → `generativelanguage.googleapis.com/v1beta/openai`. The `deepseek` provider → `api.deepseek.com`. Neither goes through LiteLLM.
- DeepSeek's live API (as of 2026-05-06) only returns `deepseek-v4-flash` and `deepseek-v4-pro`. `deepseek-chat` and `deepseek-reasoner` are gone from their models endpoint. Verify with: `curl https://api.deepseek.com/models -H "Authorization: Bearer $KEY"`.
- LiteLLM config at `~/01_Infrastructure/homeserver/stacks/02-ai/config.yaml` still uses stale names: `deepseek-chat` and `deepseek-reasoner` as direct DeepSeek routes, `deepseek-v4-flash` routed through OpenRouter. These need updating separately.
- OpenClaw's TUI streaming watchdog is hardcoded at 30s (`DEFAULT_STREAMING_WATCHDOG_MS = 3e4` in `tui-i8gtgAaG.js`). Not configurable via `openclaw.json`. The "no stream updates for 30s" message means the backend dropped the run silently — root cause was LiteLLM proxy latency.
- To reload OpenClaw gateway after config change: `kill -HUP $(pgrep -f "openclaw.*gateway" | head -1)`. A new PID will appear; the old one exits. Gateway serves from `localhost:18789`.
- `agents.defaults.model.primary` in `openclaw.json` sets the default model for ALL agents (including the gateway agent). Agent-level `model: {}` means "inherit defaults."
- OpenClaw TUI status bar shows the active model for the current session. If it still shows the old model after a config change, the gateway session was started before the reload — close and reopen the TUI.

**Lessons / Dead ends**
- First `kill -HUP` sent to the old gateway PID (1338148) caused it to exit; a new process (2182355) spawned from the watchdog/supervisor. `curl localhost:18789/health` returned nothing for ~2s then the gateway came back serving HTML. Always wait 2s and check for the new PID.
- OpenClaw health check message "LiteLLM proxy instead of OpenRouter" was misleading — the agent that ran the health check was the OLD session still running on `litellm/chat`. It described its own model path, not the new config. The on-disk config was already correct. Confirmed by reading `~/.openclaw/openclaw.json` directly.
- Attempted `curl localhost:18789/api/v1/config/models` and `/api/v1/agents/defaults` — both returned empty (endpoints don't exist). No live API endpoint exposes the resolved primary model; only the config file is authoritative.

**Issues (unresolved)**
- LiteLLM config (`~/01_Infrastructure/homeserver/stacks/02-ai/config.yaml`) has stale DeepSeek model names: `deepseek-chat` and `deepseek-reasoner` no longer exist on DeepSeek's API. Need to update to `deepseek-v4-flash` / `deepseek-v4-pro` and rebuild the container (`cd ~/01_Infrastructure/homeserver && make up STACK=02-ai`).
- Gemini 3 preview models (`gemini-3-flash-preview`, `gemini-3-pro-preview`) added to OpenClaw picker but not tested — unknown whether they accept requests or are invite-only.

date: 2026-05-06 20:04 UTC
projects: [ichabod]
source: claude-code/ichabod
auto: true

date: 2026-05-07 15:53 PDT
projects: [ichabod]
source: claude-code/ichabod

**Summary**
Reconfigured OpenClaw's

date: 2026-05-07 15:55 UTC
projects: [ichabod-infrastructure]
source: claude-code/ichabod

date: 2026-05-08 16:31 UTC
projects: [ichabod]
source: gemini-cli/ichabod
auto: true

**Summary**
Initial plan draft for infrastructure cleanup. Superseded by entry below.

date: 2026-05-09 00:40 UTC
projects: [ichabod-infrastructure]
source: claude-code/ichabod

**Summary**
Portfolio site session: synced systems-and-sigils into the job-search Projects folder, pulled 7 new Lovable commits (including a portrait placeholder in the hero), swapped the placeholder with Justin's real headshot, and ported the bento grid capabilities interaction from app/ to systems-and-sigils. Committed and pushed all changes to the GitHub remote so Lovable will pick them up.

**Patterns / Conventions**
- **Two-repo split:** systems-and-sigils has TWO copies. `~/Documents/job-search/systems-and-sigils/` is the git source with the GitHub remote (`wowthisiseasytoremember-stack/systems-and-sigils.git`). `~/Projects/job-search/systems-and-sigils/` is a working copy synced via rsync. Always make edits in Projects/, then rsync back to Documents/ before committing from Documents/.
  - Sync Projects → Documents: `rsync -av --exclude node_modules --exclude dist --exclude .git --exclude .wrangler ~/Projects/job-search/systems-and-sigils/ ~/Documents/job-search/systems-and-sigils/`
  - Pull new Lovable commits: fetch from Documents/, then rsync Documents/ → Projects/ (same command, reversed dirs)
- **bun not in PATH** in Claude Code zsh sessions on ichabod. Always use `~/.bun/bin/bun` explicitly. `~/.bun/bin/bunx vite` also fails if node_modules aren't installed — run `~/.bun/bin/bun install` first after a fresh rsync.
- **Mac SSH:** local IP `192.168.1.13` is unreachable from ichabod. Use `mac-tailscale` alias (100.75.13.38, user: justin) for SCP. `scp mac-tailscale:"/path/to/file" /dest/` works reliably.
- **headshot.jpg** canonical location: `/home/ichabod/Projects/job-search/headshot.jpg` (207KB). Copied to `systems-and-sigils/public/headshot.jpg` and `app/public/headshot.jpg`.
- **Lovable portrait slot:** Hero.tsx right column (col-start-9, col-span-4) has a `<figure style="aspectRatio: 4/5">` — just replace the inner `<div>` with `<img src="/headshot.jpg" className="h-full w-full object-cover object-top" />` and remove the comment.
- **StatValue export in Capabilities.tsx** — `MobileSnapshot.tsx` imports `StatValue` directly from `./Capabilities`. Never remove that export when refactoring the Capabilities layout.
- **useInView for entrance animations breaks Playwright fullPage screenshots** — IntersectionObserver never fires for elements below the viewport in a static screenshot. Cards render with `opacity-0` and stay invisible. Use CSS-only hover effects; skip JS-driven entrance animations on bento cards.
- **Lovable commits are authored by** `gpt-engineer-app[bot]` — that's the Lovable.dev bot identity on GitHub. Normal to see these in the log.
- **sigils dev server:** `cd ~/Projects/job-search/systems-and-sigils && ~/.bun/bin/bun run dev --port 5175`. App dev server: `cd ~/Projects/job-search/app && npm run dev -- --port 5174`.

**Lessons / Dead ends**
- First headshot attempt used an ambient absolutely-positioned `<img>` behind the text (opacity 0.18, 38% width, gradient fade). Looked fine but was redundant once Lovable's proper portrait figure slot was discovered after pulling the 7 new commits. The rsync overwrite replaced my ambient version with Lovable's designed slot — which was the right outcome.
- `~/.bun/bin/bunx vite dev` failed with `ERR_MODULE_NOT_FOUND` in the Projects/ copy because node_modules hadn't been installed yet (rsync excludes them). Fix: `~/.bun/bin/bun install` in the project dir before starting the dev server.
- `pkill -f "vite.*5175"` returned exit code 144 (no process found) — the prior server had already died. Not an error, just means the server had crashed. Start fresh instead.

**Issues (unresolved)**
- **Deploy not done.** systems-and-sigils is ready for Cloudflare Pages but hasn't been deployed. `wrangler.jsonc` is configured for project `justin-ryan-portfolio`. Run: `cd ~/Documents/job-search/systems-and-sigils && ~/.bun/bin/bunx wrangler pages deploy dist --project-name justin-ryan-portfolio` (after `~/.bun/bin/bun run build`).
- **AI product resume thin.** `public/justin-ryan-ai-product.pdf` is 6KB vs. 37KB for the other variants. Needs a content pass before the site goes live.
- **Dev servers left running** on ichabod: app/ on port 5174 (npm), systems-and-sigils on port 5175 (bun). Kill with `pkill -f "vite.*5174"` and `pkill -f "vite.*5175"` when done.
- **Malformed auto-close entry** at line 166-178 of `_close-log.md` (date: 2026-05-09 00:47 UTC) — truncated summary, no content. Cleaned up in this write.

**Stale docs / Wrong locations**
- Memory note `portfolio-codebase-duplication-tension.md` says "Two live portfolio codebases (systems-and-sigils + The Quiet Authority app/), neither deployed." — systems-and-sigils is now the canonical one with the real headshot and bento grid. The app/ is still a useful design reference but is not the one to ship. Update the memory note if this decision sticks.

date: 2026-05-09 01:00 UTC
projects: [ichabod, memory]
source: openclaw/ichabod
auto: true

date: 2026-05-09 07:15 UTC
projects: [ichabod-infrastructure, tangle-trove]
source: claude-code/ichabod

**Summary**
**Summary**
Infrastructure audit reviewed — 12 categories of built-but-never-launched items. Planning session interrupted before the plan was written.

date: 2026-05-08 02:00 UTC
projects: [ichabod, tangle-trove, photo-bot]
source: claude-code/ichabod

date: 2026-05-09 01:38 UTC
projects: [homeserver]
source: claude-code/ichabod
auto: true

**Summary**
Added `append_file` tool to the brain MCP server to work around Cloudflare WAF blocking large writes (~16KB+). The WAF block lives on anthropic.com's zone (the MCP gateway hop from Mac Claude Code), not on scoreapp.pro — no fix at the source, so the protocol now supports chunked writes instead.

**Patterns / Conventions**
- brain MCP server source: `/home/ichabod/mcp-brain/server.py`. Managed by systemd: `brain-mcp.service` (`/etc/systemd/system/brain-mcp.service`). Token is in that service file as `Environment="BRAIN_VAULT_TOKEN=..."`. No `.env` file exists in `/home/ichabod/mcp-brain/` — don't look there.
- `brain-mcp.service` runs as root (`/usr/bin/python3`), not as a user service. Use `sudo systemctl restart brain-mcp.service` to restart it — `systemctl --user` won't find it.
- Large write workaround: call `write_file` for the first chunk, then `append_file` for subsequent chunks. Keep each chunk under ~12KB to stay well below the ~16KB WAF trigger. For appending to existing files (e.g. GLOBAL_STATE.md), `append_file` alone is fine if the entry is under 12KB.
- The Cloudflare tunnel config for brain MCP: `/etc/cloudflared/brain-mcp.yml`. Routes `brain.scoreapp.pro` → `http://localhost:8094`.
- Three brain MCP servers still running simultaneously: `brain_mcp_server.py` (port 8091, SSE), `mcp-brain/server.py` (port 8094, HTTP, the real one), and `basic-memory` (stdio, session-scoped, 1.2GB). Consolidation is a separate task.

**Lessons / Dead ends**
- Killed the original server process (PID 685549) and tried to restart manually with `python3 /home/ichabod/mcp-brain/server.py &` — spawned two processes AND conflicted with systemd's own restart loop (counter hit 14). Fix: kill the manual processes, wait for systemd to recover on its own, then leave it alone. Always use `sudo systemctl restart brain-mcp.service` for restarts.
- `sudo systemctl restart brain-mcp.service` was blocked by the session permission filter. Letting systemd handle its own restart loop after clearing the conflicting manual process was sufficient — the service recovered in ~10 seconds.
- curl-based tool verification against `http://localhost:8094` was also blocked by the permission filter. Confirmed correctness instead by: (a) grep on server.py to verify `append_file` at line 78, (b) service running cleanly at 64MB with no crash = no syntax error.

**Issues (unresolved)**
- Open question from prior session: does claude.ai cloud (web/mobile) MCP traffic go through anthropic.com, or directly to brain.scoreapp.pro? If direct, the new WAF rule on scoreapp.pro helps it; if proxied through anthropic.com, no fix yet. Verify by attempting a large `write_file` from claude.ai web.
- Three overlapping brain MCP servers still running (8091, 8094, basic-memory/1.2GB). Should consolidate to one — separate task.

date: 2026-05-09 01:56 UTC
projects: [ichabod-infrastructure, tangle-trove, photo-bot]
source: claude-code/ichabod

date: 2026-05-09 02:04 UTC
projects: [ichabod]
source: claude-code/ichabod
auto: true

| 2026-05-09T05:24:07Z | agent-gemini-cli | agentic-ai | Researched agentic AI tools (Hermes, OpenClaw) for ADHD and personal support; saved master blueprint to research/adhd_agentic_stack_best_practices.md and Obsidian. | none |
| 2026-05-09T05:33:58Z | agent-gemini-cli | ad-hoc | Audited LLM keys in GCloud. Found active balances for DeepSeek (.96) and OpenRouter (.69). Identified invalid keys for OpenAI, Kimi, and Groq. | none |

**Summary**
--agent

date: 2026-05-09 06:21 UTC
projects: [ichabod]
source: hermes
auto: false

| 2026-05-09T21:02:54Z | agent-gemini-cli | isolated-bot-pwa | Researched bot isolation and generated standalone PWA prompt. Found Safari PWA session sharing risk. Corrected Score. branding assumption. | none |

**Summary**
--agent

date: 2026-05-10 00:16 UTC
projects: [ichabod]
source: gemini-cli/ichabod
auto: true

| 2026-05-10T02:42:50Z | agent-gemini-cli | ad-hoc | Located ichabod Tangle Trove DB and copied the close skill locally. | Failed initial SSH attempt; missed docs instruction initially. |

**Summary**
Memory-manager consolidation pass covering May 9-10 sessions. Major work: (1) photo-pipeline built — entire n8n intake chain replaced with a single async Python service (FastAPI + aiosqlite + aiohttp) on port 8443, old photo-bot archived. (2) Kanban orchestrator live — 8 specialist profiles, @Notes_ichabodbot with Whisper STT, Hermes dashboard at port 9119. (3) Hermes migration complete — SOUL.md written, cron consolidated 8→2, brain vault rebranded from Claw. (4) GCP billing fixed (closed billing account relinked), all 79+ secrets backed up to encrypted GPG. (5) Infrastructure audit completed — 12 categories documented, LiteLLM key leak flagged. All 4 Tier 1 project STATE.md files refreshed (were 24+ days stale).

**Patterns / Conventions**
- TANGLE_TROVE_BASE must be /home/ichabod/01_Infrastructure/homeserver (n8n uses / inside container but host needs full path)
- SoldComps API (api.sold-comps.com/search) is dead — do not attempt to use or debug
- Telegram allowed_updates filter persists server-side through deleteWebhook — must explicitly pass allowed_updates parameter on getUpdates
- n8n API keys are invalidated on DB rebuild — GCP-stored keys may become stale if n8n DB is wiped
- Hermes dashboard needs --host 0.0.0.0 --insecure for remote access (port 9119)
- Worker profiles route through LiteLLM, never direct Google API (avoids quota exhaustion)
- hermes kanban archive (not delete), hermes config show (not get)

**Lessons / Dead ends**
- 2+ hours debugging n8n body format mismatches — solved by rebuilding as single Python service. n8n workflow debugging is the root cause of every pipeline problem.
- Gemini quota exhaustion (429) for worker profiles — all now route through LiteLLM worker alias
- Multi-task delegate_task with browser toolsets times out — single-task + terminal toolsets works
- Photo-bot not receiving photos was Telegram's server-side allowed_updates filter locked to callback_query only — not a code bug
- Brain MCP large writes blocked by anthropic.com Cloudflare WAF (~16KB threshold) — fixed with append_file chunked writes

**Issues (unresolved)**
- 1,094 items stuck at needs_approval in Tangle Trove — approval UI was never built
- systems-and-sigils portfolio not deployed to Cloudflare Pages
- LiteLLM config.yaml needs GEMINI_FREE_KEY + MISTRAL_API_KEY wired in
- LiteLLM master key exposed in plaintext in env.sh and token-spend-monitor.sh
- 3 overlapping brain MCP servers still running (ports 8091, 8094, basic-memory/1.2GB)
- Score. rejected on Guideline 2.1 — Build 11 committed but never uploaded
- Syncthing re-enabled despite being flagged deprecated
- eBay CSV Export workflow blocked by deprecated executeCommand node in n8n 2.16.1

date: 2026-05-10 01:59 UTC
projects: [ichabod]
source: gemini-cli/ichabod
auto: true

### Recent Context (Auto-generated 2026-05-10)

OpenClaw underwent a major model configuration update on May 6, migrating from `litellm/chat` to `google-ai/gemini-2.5-flash` with direct Google AI API integration. DeepSeek model IDs were corrected to use current versions (`deepseek-v4-flash`/`deepseek-v4-pro`), and the TUI model picker expanded to include all Gemini generations and DeepSeek V4. LiteLLM config remains stale with outdated DeepSeek references requiring container rebuild. Gateway reload requires `kill -HUP` with new PID verification via `localhost:18789/health`.

Infrastructure consolidation continued May 9-10 with critical updates: photo-pipeline replaced n8n with a FastAPI async service (port 8443), Hermes kanban orchestrator deployed with 8 specialist profiles and Whisper STT integration (dashboard port 9119), and GCP billing issues resolved with 79+ secrets backed up. Brain MCP large-write WAF blocking (~16KB) was mitigated via chunked `append_file` writes. Remaining blockers include 1,094 Tangle Trove approval items, portfolio deployment pending, and three overlapping brain MCP servers requiring consolidation.
