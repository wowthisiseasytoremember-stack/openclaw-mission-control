**Last Updated:** 2026-04-15 17:35 UTC

# Purple Team Audit — OpenClaw Mission Control

**Platforms:** Python (FastAPI), Web (Next.js), Homelab, Docker
**Components triggered:** JTBD Workflow Validator / Competitor Feature Mapper (inferred) / Segment Gap Detector
**Cross-component promotions:** 1 (data export: JTBD G0 + Segment G0)

**Value proposition (README):** "Centralized governance and operations platform for running OpenClaw across teams. Provides unified task boards, agent lifecycle management, approval flows, gateway management, and an audit trail — all through a single web UI and REST API."

---

## FINDINGS

| ID | Weight | Severity | Confidence | Title | File:Line or Artifact | Cross-Team | Delta |
|----|--------|----------|------------|-------|-----------------------|------------|-------|
| P-01 | 0 | G0 | 10 | No data export (CSV/JSON) at any layer — no /export endpoint, no download button, no serialization logic (cross-component: JTBD + Segment) | backend/app/api/tasks.py (no export route), frontend/src/ (no download/csv/blob matches) | | New |
| P-02 | 0 | G0 | 10 | No global task search — all task queries are board-scoped with no `q`/`search` param; no frontend search UI exists | backend/app/api/tasks.py:1462-1477 (only status_filter, assigned_agent_id, unassigned), frontend/src/ (no SearchBar component) | | New |
| P-03 | 0 | G0 | 10 | No user-configurable notifications or alerts — no notification model, no alert rules, no settings UI, no email/Slack delivery | backend/app/api/ (zero notification endpoints), frontend/src/app/settings/page.tsx (only name/timezone/delete) | | New |
| P-04 | 1 | G1 | 10 | No bulk operations on tasks — no bulk delete, bulk status change, or bulk assignment; zero "bulk"/"batch" matches in API layer | backend/app/api/tasks.py (zero bulk matches), frontend/src/ (no multi-select row patterns on tasks) | | New |
| P-05 | 1 | G1 | 9 | Onboarding path ends at name+timezone — no board creation step, no task submission step, no guided tour; user lands on empty dashboard with no next-step prompt | frontend/src/app/onboarding/page.tsx (2-field form only), frontend/src/app/dashboard/page.tsx (no empty-state get-started banner) | B-01 | New |
| P-06 | 1 | G1 | 9 | Task filtering limited to 3 dimensions (status, assigned_agent, unassigned) — no tag, custom field, date range, title/text, or priority filters despite backend having generic QuerySet primitives | backend/app/api/tasks.py:1462-1477, backend/app/api/queryset.py (filter primitives exist but not exposed) | | New |
| P-07 | 1 | G1 | 9 | Outbound webhook dispatch not wired to real events — source explicitly states "intentionally NOT wired into task/approval handlers yet" | backend/app/services/outbound_webhooks/dispatch.py:22-25 | R-02, B-02, B-03 | New |
| P-08 | 2 | G2 | 9 | Dashboard metrics hardcoded to 7d range — backend supports 8 time ranges but frontend has no range picker; no per-agent or per-board drill-down | frontend/src/app/dashboard/page.tsx (DASHBOARD_RANGE = "7d"), backend/app/api/metrics.py (supports 24h through 1y) | | New |
| P-09 | 2 | G2 | 9 | Agent health SSE stream not consumed by frontend — backend has /agents/stream endpoint but UI polls at 30s via REST; no real-time push indicators | backend/app/api/agents.py (/agents/stream), frontend/src/app/agents/[agentId]/page.tsx:refetchInterval:30000 | B-05 | New |
| P-10 | 2 | G2 | 9 | No keyboard shortcuts — cmdk command palette component present but not wired to global hotkey; no useHotkeys or keydown listeners anywhere in frontend | frontend/src/components/ui/command.tsx (unused as palette), frontend/src/ (zero hotkey matches) | | New |
| P-11 | 2 | G2 | 9 | Dashboard has no empty-state guidance — new user with zero boards/agents/tasks sees zeroed metric cards with no call to action or "get started" prompt | frontend/src/app/dashboard/page.tsx (no empty-state branch) | | New |

---

## METRICS

- Total findings: 11
- G0 (critical gap): 3
- G1 (high gap): 4
- G2 (low gap): 4
- Filtered (confidence < 7): 1
- Components triggered: JTBD / Competitor (inferred) / Segment
- Cross-component promotions: 1 (P-01 data export appeared in both JTBD and Segment)

---

## FILTERED

| ID | Reason | Original Confidence |
|----|--------|---------------------|
| P-F1 | Speculative — competitor parity for "real-time collaboration" (e.g. multi-cursor, live co-editing); no README claim or codebase evidence that this was intended | 5 |

---

## ALERTS

- Competitors inferred from README — not explicitly specified. Run with `--competitors=X,Y` for precise mapping. Inferred category: AI agent orchestration / task management platforms (comparable to CrewAI, LangGraph Studio, AutoGen Studio, AgentOps).
- The "single web UI" promise in the README is partially unmet: webhooks (inbound CRUD and outbound management) have no frontend pages; outbound dispatch is explicitly not wired to events.
- Organization management (Job 5) is COMPLETE end-to-end — board creation, org switching, member invites all work.
- API documentation (Swagger/ReDoc) is COMPLETE and well-maintained with auto-generated examples across 28 tag groups.
- The board-scoped onboarding flow (`board_onboarding.py`) is a sophisticated agent-assisted setup system, but it is post-board — it does not substitute for a pre-board new-user guide.
