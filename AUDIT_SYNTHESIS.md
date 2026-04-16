**Last Updated:** 2026-04-15 17:40 UTC

# Audit Synthesis — OpenClaw Mission Control

**Date:** 2026-04-15 17:40 UTC
**Platforms:** Python (FastAPI), Web (Next.js), Homelab, Docker
**Teams run:** Red / Blue / Purple

---

## Verdict

**BLOCK** — 8 Weight 0 findings across Blue Team (5) and Purple Team (3). No P0 security blockers from Red Team, but the product has critical UX ship-blockers (silent crash on first run, missing webhook UI, undefined domain terminology) and critical feature gaps (no data export, no global search, no user notifications). The first-run experience is broken for any new user following the documented setup path.

**Blockers:**
- B-01: `LOCAL_AUTH_TOKEN` blank causes silent crash on first `docker compose up -d`
- B-02: Inbound webhook CRUD has zero frontend UI
- B-03: Outbound webhook management has zero frontend UI
- B-04: "Soul" is undefined domain jargon throughout the API
- B-05: No web UI for agent task operations
- P-01: No data export (CSV/JSON) at any layer
- P-02: No global task search or cross-board query
- P-03: No user-configurable notifications or alerts

---

## Cross-Team Patterns

| Pattern | Findings | Shared Root Cause |
|---------|----------|-------------------|
| Webhook system immaturity | R-02 + B-02 + B-03 + P-07 | The webhook subsystem has a security gap (SSRF in target_url), no frontend UI (inbound or outbound), and outbound dispatch is explicitly not wired to real events. All four findings trace to the same incomplete subsystem. |
| Agent interaction surface | B-05 + P-09 | Agent task operations have no web UI (Blue) and agent health SSE is not consumed by the frontend (Purple). The agent monitoring/interaction layer is API-complete but frontend-absent. |
| First-run journey | B-01 + P-05 | The setup path crashes silently from a blank token (Blue) and the onboarding flow ends at name+timezone with no board/task creation step (Purple). A new user hits both of these sequentially. |

---

## By Priority

| ID | Team | Weight | Severity | Title | Cross-Team |
|----|------|--------|----------|-------|------------|
| B-01 | Blue | 0 | S | `LOCAL_AUTH_TOKEN` blank causes silent crash in `-d` mode | P-05 |
| B-02 | Blue | 0 | S | Inbound webhook CRUD has zero frontend UI | R-02, P-07 |
| B-03 | Blue | 0 | S | Outbound webhook management has zero frontend UI | R-02, P-07 |
| B-04 | Blue | 0 | S | "Soul" is undefined domain jargon | |
| B-05 | Blue | 0 | S | No web UI for agent task operations | P-09 |
| P-01 | Purple | 0 | G0 | No data export (CSV/JSON) at any layer | |
| P-02 | Purple | 0 | G0 | No global task search | |
| P-03 | Purple | 0 | G0 | No user-configurable notifications/alerts | |
| R-01 | Red | 1 | P1 | SSRF via gateway_url — no allowlist on WebSocket connections | |
| R-02 | Red | 1 | P1 | SSRF via outbound webhook target_url — allows internal IPs | B-02, B-03, P-07 |
| R-03 | Red | 1 | P1 | Frontend port bound to 0.0.0.0 | |
| R-04 | Red | 1 | P1 | CORS allow_credentials with wildcard methods/headers | |
| B-06 | Blue | 1 | A | Preflight blocks new users without OpenClaw gateway | |
| B-07 | Blue | 1 | A | ichabod-specific IPs hardcoded in README | |
| B-08 | Blue | 1 | A | Default DATABASE_URL uses wrong DB name | |
| B-09 | Blue | 1 | A | Gateway error fields discarded by frontend | |
| B-10 | Blue | 1 | A | Gateway token null in status query — false offline | |
| B-11 | Blue | 1 | A | Lead notify failure swallowed on approval resolution | |
| B-12 | Blue | 1 | A | Webhook notify failure discarded silently | |
| B-13 | Blue | 1 | A | All 401s bare "Unauthorized" with no credential hint | |
| B-14 | Blue | 1 | A | Malformed `since` param silently discarded | |
| B-15 | Blue | 1 | A | Invalid AUTH_MODE silently shows Clerk sign-in | |
| B-16 | Blue | 1 | A | Missing AUTH_MODE produces Pydantic traceback | |
| B-17 | Blue | 1 | A | Agent-on-user-endpoint raises 403 not 401 | |
| B-18 | Blue | 1 | A | Bootstrap 401 body doesn't match OpenAPI schema | |
| B-19 | Blue | 1 | A | Agent create form has no gateway selector | |
| B-20 | Blue | 1 | A | Board Memory vs Board Group Memory naming confusion | |
| P-04 | Purple | 1 | G1 | No bulk operations on tasks | |
| P-05 | Purple | 1 | G1 | Onboarding ends at name+timezone — no board creation step | B-01 |
| P-06 | Purple | 1 | G1 | Task filtering limited to 3 dimensions | |
| P-07 | Purple | 1 | G1 | Outbound webhook dispatch not wired to events | R-02, B-02, B-03 |
| R-05 | Red | 2 | P2 | Inbound webhook HMAC skipped when no secret | |
| R-06 | Red | 2 | P2 | Token prefix logged on auth failure | |
| R-07 | Red | 2 | P2 | allow_insecure_tls disables cert verification | |
| R-08 | Red | 2 | P2 | Rate limiter fail-open on Redis outage | |
| R-09 | Red | 2 | P2 | No HSTS/CSP in backend headers | |
| R-10 | Red | 2 | P2 | No security headers for Next.js pages | |
| R-11 | Red | 2 | P2 | uv installer via unverified curl pipe | |
| R-12 | Red | 2 | P2 | Unpinned Docker base images | |
| R-13 | Red | 2 | P2 | Gateway URL no scheme validation | |
| R-14 | Red | 2 | P2 | Developer LAN IP in allowedDevOrigins | |
| R-15 | Red | 2 | P2 | Agent token auth O(n) with PBKDF2 | |
| R-16 | Red | 2 | P2 | is_super_admin never enforced | |
| R-17 | Red | 2 | P2 | dangerouslySetInnerHTML style injection pattern | |
| B-21 | Blue | 2 | B | README missing cp .env.example step | |
| B-22 | Blue | 2 | B | No prerequisites section in README | |
| B-23 | Blue | 2 | B | install.sh not mentioned in README | |
| B-24 | Blue | 2 | B | require_approval_for_done=True default invisible | |
| B-25 | Blue | 2 | B | Gateway main-agent prerequisite invisible in UI | |
| B-26 | Blue | 2 | B | SSE approval stream polls DB every 2s per client | |
| B-27 | Blue | 2 | B | No standalone audit-trail page in frontend | |
| B-28 | Blue | 2 | B | RQ_DISPATCH_THROTTLE_SECONDS hidden from .env.example | |
| B-29 | Blue | 2 | B | Empty event_types silently subscribes to all events | |
| B-30 | Blue | 2 | B | Read-only members see no explanation for missing button | |
| B-31 | Blue | 2 | B | Agent detail fetches all-org events, filters client-side | |
| B-32 | Blue | 2 | B | Token in sessionStorage clears on browser close | |
| B-33 | Blue | 2 | B | db_auto_migrate silently overridden in dev | |
| B-34 | Blue | 2 | B | log_use_utc defaults to False | |
| B-35 | Blue | 2 | B | No post-creation guidance after agent registration | |
| B-36 | Blue | 2 | B | Per-board approval errors merged into one string | |
| B-37 | Blue | 2 | B | Internal board events missing from live-feed set | |
| B-38 | Blue | 2 | B | souls_directory leaks exception strings in 502 | |
| P-08 | Purple | 2 | G2 | Dashboard metrics hardcoded to 7d range | |
| P-09 | Purple | 2 | G2 | Agent health SSE not consumed by frontend | B-05 |
| P-10 | Purple | 2 | G2 | No keyboard shortcuts | |
| P-11 | Purple | 2 | G2 | Dashboard has no empty-state guidance | |

---

## Metrics Summary

| Team | Total | Weight 0 | Weight 1 | Weight 2 | Filtered |
|------|-------|----------|----------|----------|----------|
| Red | 17 | 0 | 4 | 13 | 3 |
| Blue | 38 | 5 | 15 | 18 | 3 |
| Purple | 11 | 3 | 4 | 4 | 1 |
| **Total** | **66** | **8** | **23** | **35** | **7** |

---

## Alerts

- No prior audit files were provided (`--prior-audit` not set). All findings are Delta: New.
- All three teams completed successfully (exit 0).
- Competitors inferred from README for Purple Team — run with `--competitors=CrewAI,LangGraph,AutoGen` for precise parity mapping.
- Cross-team convergence on the webhook subsystem (R-02 + B-02 + B-03 + P-07) — this is the single area flagged by all three teams.
- Positive controls noted by Red Team: no SQL injection, no command injection, no hardcoded secrets, proper .gitignore, non-root Docker users, lock files committed with integrity hashes, no CVEs in current dependency versions.
- Positive controls noted by Blue Team: org switching is complete end-to-end, empty states exist for boards and agents lists, board creation form has good validation UX.
- Positive controls noted by Purple Team: API documentation (Swagger/ReDoc) is complete and well-maintained, organization management is fully functional.
