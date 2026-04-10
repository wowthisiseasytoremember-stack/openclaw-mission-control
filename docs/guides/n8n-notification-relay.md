# n8n Notification Relay — Board Event Webhooks

This guide explains how to connect OpenClaw Mission Control's outbound webhook system to n8n (the workflow automation tool) so that board events like task creation or approval requests are automatically relayed to Telegram, email, Slack, or any other destination n8n supports.

---

## Overview

The flow is:

```
Mission Control board event
  → Outbound webhook POST to your n8n webhook URL
    → n8n routes by event type
      → Telegram message / email / Slack / etc.
```

Mission Control sends a signed JSON envelope to a URL you configure. n8n receives it, inspects the `event` field, and branches to the appropriate notification action.

---

## Step 1 — Create a Webhook node in n8n

1. Open n8n and create a new workflow.
2. Add a **Webhook** node as the trigger.
3. Set the HTTP Method to **POST**.
4. Copy the generated **Production URL** (e.g. `https://n8n.yourdomain.com/webhook/abc123`). You will paste this into Mission Control.
5. Set **Response Mode** to `Immediately` so Mission Control gets a fast 200 OK acknowledgment.

---

## Step 2 — Register the outbound webhook in Mission Control

Call the API to create an outbound webhook pointed at your n8n URL:

```http
POST /api/v1/boards/{board_id}/outbound-webhooks
Authorization: Bearer <your-token>
Content-Type: application/json

{
  "name": "n8n notification relay",
  "target_url": "https://n8n.yourdomain.com/webhook/abc123",
  "secret": "a-strong-random-secret",
  "event_types": ["task.created", "task.done", "approval.pending"],
  "enabled": true
}
```

**Field notes:**

| Field | Notes |
|-------|-------|
| `name` | Human-readable label. Shown in Mission Control UI. |
| `target_url` | The n8n Production webhook URL from Step 1. |
| `secret` | Optional. When set, Mission Control signs every request with HMAC-SHA256 and includes the signature in the `X-OpenClaw-Signature-256` header. Verify this in n8n to prevent spoofed events. |
| `event_types` | List of events to subscribe to. Leave empty (`[]`) to receive all events. |

---

## Step 3 — Verify the HMAC signature in n8n (recommended)

When a secret is configured, every POST includes:

```
X-OpenClaw-Signature-256: sha256=<hex-digest>
```

To verify in n8n, add a **Code** node immediately after the Webhook trigger:

```javascript
const crypto = require('crypto');
const secret = 'a-strong-random-secret';  // must match what you set in Mission Control
const rawBody = $input.first().binary?.data
  ? Buffer.from($input.first().binary.data, 'base64').toString('utf-8')
  : JSON.stringify($input.first().json);
const sig = $input.first().headers['x-openclaw-signature-256'] || '';
const expected = 'sha256=' + crypto
  .createHmac('sha256', secret)
  .update(rawBody)
  .digest('hex');
if (sig !== expected) {
  throw new Error('Signature mismatch — rejecting event.');
}
return $input.all();
```

If signatures don't match the workflow stops and the event is discarded.

---

## Step 4 — Route by event type

Add a **Switch** node after the signature check. Route on the expression `{{ $json.event }}`:

| Value | Route |
|-------|-------|
| `task.created` | Telegram new-task notification |
| `task.done` | Email completion summary |
| `approval.pending` | Telegram approval-needed alert |
| *(default)* | Log to a Google Sheet / discard |

---

## Step 5 — Telegram notification example

For the `approval.pending` branch:

1. Add a **Telegram** node.
2. Connect your Telegram bot credentials.
3. Set **Chat ID** to your operations chat.
4. Set the **Text** field to:

```
🔔 Approval needed on board {{ $json.data.board_id }}

Task: {{ $json.data.task_title }}
Requested by: {{ $json.data.requested_by }}
```

---

## Step 6 — Email notification example

For the `task.done` branch:

1. Add a **Send Email** node (or Gmail / SMTP node).
2. Set **To** to your team address.
3. Set **Subject** to `Task completed: {{ $json.data.title }}`.
4. Set **Body** to:

```
Board: {{ $json.data.board_id }}
Task: {{ $json.data.title }}
Completed at: {{ $json.occurred_at }}
```

---

## Step 7 — Test the integration

Use the Mission Control test endpoint to fire a synthetic event without needing a real task or approval:

```http
POST /api/v1/boards/{board_id}/outbound-webhooks/{webhook_id}/test
Authorization: Bearer <your-token>
```

This sends a `webhook.test` event to the target URL. Verify it arrives in n8n's execution log.

---

## Event type reference

All events share this envelope structure:

```json
{
  "event": "task.created",
  "board_id": "uuid",
  "webhook_id": "uuid",
  "occurred_at": "2026-04-10T12:00:00+00:00",
  "data": { ... }
}
```

### `task.created`

```json
{
  "event": "task.created",
  "board_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "webhook_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "occurred_at": "2026-04-10T12:00:00+00:00",
  "data": {
    "task_id": "...",
    "title": "Write release notes",
    "status": "todo",
    "assigned_agent_id": null,
    "created_at": "2026-04-10T12:00:00+00:00"
  }
}
```

### `task.updated`

```json
{
  "event": "task.updated",
  "data": {
    "task_id": "...",
    "title": "Write release notes",
    "status": "in_progress",
    "changes": ["status"]
  }
}
```

### `task.done`

```json
{
  "event": "task.done",
  "data": {
    "task_id": "...",
    "title": "Write release notes",
    "completed_at": "2026-04-10T13:30:00+00:00"
  }
}
```

### `task.deleted`

```json
{
  "event": "task.deleted",
  "data": {
    "task_id": "...",
    "title": "Write release notes"
  }
}
```

### `approval.pending`

```json
{
  "event": "approval.pending",
  "data": {
    "approval_id": "...",
    "task_id": "...",
    "task_title": "Deploy to production",
    "requested_by": "agent-name",
    "requested_at": "2026-04-10T14:00:00+00:00"
  }
}
```

### `approval.approved`

```json
{
  "event": "approval.approved",
  "data": {
    "approval_id": "...",
    "task_id": "...",
    "reviewed_by": "agent-name",
    "reviewed_at": "2026-04-10T14:05:00+00:00"
  }
}
```

### `approval.rejected`

```json
{
  "event": "approval.rejected",
  "data": {
    "approval_id": "...",
    "task_id": "...",
    "reason": "Not enough context.",
    "reviewed_by": "agent-name",
    "reviewed_at": "2026-04-10T14:05:00+00:00"
  }
}
```

### `board.updated`

```json
{
  "event": "board.updated",
  "data": {
    "board_id": "...",
    "changes": ["name", "description"]
  }
}
```

### `webhook.test`

Sent by the `/test` endpoint. Use this to validate your n8n wiring without triggering a real board action.

```json
{
  "event": "webhook.test",
  "data": {
    "message": "This is a test delivery from OpenClaw Mission Control.",
    "board_id": "...",
    "webhook_id": "..."
  }
}
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| n8n shows no executions | Webhook URL wrong or n8n not activated | Activate the workflow; verify URL matches exactly |
| `signature mismatch` error | Secret mismatch | Confirm secret in Mission Control matches the one in your n8n Code node |
| `connection refused` / timeout | n8n not reachable from Mission Control | Check firewall / Cloudflare Tunnel / port binding |
| Events arrive but routing is wrong | Switch node expression typo | Use `{{ $json.event }}` (not `{{ $json.body.event }}`) |

---

## Full workflow JSON (import into n8n)

Save the following as `openclaw-relay.json` and import via **File → Import from file** in n8n.

```json
{
  "name": "OpenClaw Board Event Relay",
  "nodes": [
    {
      "id": "webhook-trigger",
      "name": "Board Event Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [250, 300],
      "parameters": {
        "httpMethod": "POST",
        "path": "openclaw-board-events",
        "responseMode": "onReceived",
        "responseData": "allEntries"
      }
    },
    {
      "id": "verify-signature",
      "name": "Verify HMAC Signature",
      "type": "n8n-nodes-base.code",
      "typeVersion": 1,
      "position": [500, 300],
      "parameters": {
        "jsCode": "const crypto = require('crypto');\nconst secret = process.env.OPENCLAW_WEBHOOK_SECRET || '';\nif (!secret) return $input.all();\nconst body = JSON.stringify($input.first().json);\nconst sig = $input.first().headers['x-openclaw-signature-256'] || '';\nconst expected = 'sha256=' + crypto.createHmac('sha256', secret).update(body).digest('hex');\nif (sig !== expected) throw new Error('Signature mismatch');\nreturn $input.all();"
      }
    },
    {
      "id": "route-by-event",
      "name": "Route by Event Type",
      "type": "n8n-nodes-base.switch",
      "typeVersion": 1,
      "position": [750, 300],
      "parameters": {
        "dataPropertyName": "event",
        "rules": {
          "rules": [
            {"value": "task.created"},
            {"value": "task.done"},
            {"value": "approval.pending"}
          ]
        }
      }
    }
  ],
  "connections": {
    "Board Event Webhook": {"main": [[{"node": "Verify HMAC Signature", "type": "main", "index": 0}]]},
    "Verify HMAC Signature": {"main": [[{"node": "Route by Event Type", "type": "main", "index": 0}]]}
  }
}
```

Add Telegram and email nodes to each branch of the Switch node, configure credentials, and activate the workflow.
