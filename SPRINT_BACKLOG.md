**Last Updated:** 2026-05-04 08:00 UTC

# OpenClaw Frontend Sprint Backlog

**Logged:** 2026-05-04 08:00 UTC  
**Source:** AUDIT_SYNTHESIS.md — Weight-0 ship-blockers deferred from 2026-05-04 Haiku audit  
**Intent:** Bundle into a dedicated frontend sprint session when OpenClaw is ready for wider use

---

## P1 — High Priority (Frontend UI Gaps)

### B-02: Inbound Webhook CRUD — No Frontend UI
Inbound webhook create/read/update/delete operations exist in the backend API but have zero frontend UI. Users cannot manage inbound webhooks without hitting the API directly via curl or Postman.

### B-03: Outbound Webhook Management — No Frontend UI
Outbound webhook management has the same gap. Backend routes exist, no UI.

### B-05: No Web UI for Agent Task Operations
Agent task operations (create, assign, complete, cancel) are API-only. No web interface for managing tasks on a board without the API.

---

## P2 — Medium Priority

### B-04: "Soul" Is Undefined Domain Jargon
The term "Soul" appears throughout the API without definition or in-UI documentation. Any new user sees it and has no idea what it means. Fix: rename in the UI layer or add contextual tooltips.

### P-01: No Data Export
No CSV or JSON export exists at any layer — tasks, webhooks, agents, or activity logs. Needed before treating this as production infrastructure.

### P-02: No Global Task Search
No cross-board task search or query. Users cannot find tasks across multiple boards without knowing which board to look in.

---

## P3 — Lower Priority

### P-03: No User-Configurable Notifications
No in-app notification system. Users cannot configure alerts for task events, webhook failures, or agent status changes.

---

## Sprint Notes

These were explicitly deferred in favor of:
- DeepSeek/OpenRouter evaluation as Ollama replacement (in progress 2026-05-04)
- B-01 fix (blank LOCAL_AUTH_TOKEN silent crash) — completed 2026-05-04

**Do not start this sprint until the DeepSeek evaluation is settled** — the model routing architecture may affect how task events and notifications are wired.
