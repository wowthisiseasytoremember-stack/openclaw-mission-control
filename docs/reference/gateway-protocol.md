**Last Updated:** 2026-04-10 08:45 UTC

# Gateway Protocol Reference

This document describes the WebSocket RPC protocol used between Mission Control and the
OpenClaw Gateway. The protocol implementation lives in
`backend/app/services/openclaw/gateway_rpc.py`.

---

## Protocol Version

Current negotiated version: **3**

Both `minProtocol` and `maxProtocol` are set to `3` in connect requests. The gateway must
support this version or the connection is rejected.

---

## Transport

- WebSocket (`ws://` or `wss://`)
- All messages are JSON text frames
- No ping frames (disabled on the client: `ping_interval=None`)
- TLS certificate verification can be disabled per gateway via `allow_insecure_tls`

---

## Connection Handshake

Every RPC call requires a fresh connection. The sequence is:

### Step 1 — Wait for challenge (optional)

After the WebSocket opens, the client waits up to 2 seconds for an initial message. If the
gateway sends a `connect.challenge` event, the client extracts its nonce for use in the
connect signature.

```json
// Gateway → Client (optional)
{
  "type": "event",
  "event": "connect.challenge",
  "payload": {
    "nonce": "<random string>"
  }
}
```

If no message arrives within 2 seconds, the client proceeds without a nonce.

### Step 2 — Send connect request

The client sends a `connect` RPC request. The exact payload depends on the connect mode.

```json
// Client → Gateway
{
  "type": "req",
  "id": "<uuid4>",
  "method": "connect",
  "params": {
    "minProtocol": 3,
    "maxProtocol": 3,
    "role": "operator",
    "scopes": [
      "operator.read",
      "operator.admin",
      "operator.approvals",
      "operator.pairing"
    ],
    "client": {
      "id": "gateway-client",
      "version": "1.0.0",
      "platform": "linux",
      "mode": "backend"
    },
    "device": { ... },   // device mode only (see below)
    "auth": {            // when a bearer token is configured
      "token": "<gateway token>"
    }
  }
}
```

### Step 3 — Gateway responds

```json
// Gateway → Client
{
  "type": "res",
  "id": "<same uuid4>",
  "ok": true,
  "payload": { ... }   // gateway hello/session metadata
}
```

If `ok` is `false`, an `error.message` is present and the call raises `OpenClawGatewayError`.

### Step 4 — Send the actual RPC method

After a successful connect, the client immediately sends the intended method call.

```json
// Client → Gateway
{
  "type": "req",
  "id": "<new uuid4>",
  "method": "<method>",
  "params": { ... }
}
```

The client reads frames until it finds a response with a matching `id`, then closes the
connection.

---

## Connect Modes

### Device Mode (default)

Used when `disable_device_pairing` is `false` on the gateway config. The connect params
include a `device` block with an Ed25519 signature.

```json
"device": {
  "id": "<sha256 of raw public key, hex>",
  "publicKey": "<raw Ed25519 public key, base64url, no padding>",
  "signature": "<Ed25519 signature over canonical payload, base64url>",
  "signedAt": 1712345678000,
  "nonce": "<challenge nonce, if present>"
}
```

**Canonical signature payload** (pipe-delimited string):

Without nonce (v1):
```
v1|<device_id>|<client_id>|<client_mode>|<role>|<scopes,comma-joined>|<signed_at_ms>|<token or empty>
```

With nonce (v2):
```
v2|<device_id>|<client_id>|<client_mode>|<role>|<scopes,comma-joined>|<signed_at_ms>|<token or empty>|<nonce>
```

Device identity is stored at `~/.openclaw/identity/device.json` (or the path in
`OPENCLAW_GATEWAY_DEVICE_IDENTITY_PATH`). On first use a new Ed25519 keypair is generated
and persisted with `chmod 600`.

### Control UI Mode

Used when `disable_device_pairing` is `true` on the gateway config. No `device` block is
sent. The `Origin` header is set to match the gateway host, and client identifiers change:

| Field | Value |
|-------|-------|
| `client.id` | `openclaw-control-ui` |
| `client.mode` | `ui` |

This mode is intended for environments where device pairing is not available or not desired.
It relies on the bearer token alone for authentication.

---

## RPC Methods

These are the base gateway methods known to Mission Control. The gateway may expose
additional methods at runtime via channel plugins.

### health / status

| Method | Description |
|--------|-------------|
| `health` | Gateway liveness check |
| `status` | Full gateway status summary |
| `usage.status` | Current usage statistics |
| `usage.cost` | Cost tracking data |
| `last-heartbeat` | Timestamp of last agent heartbeat |
| `set-heartbeats` | Configure heartbeat parameters |
| `wake` | Wake a sleeping agent session |
| `system-presence` | System presence state |
| `system-event` | Emit a system event |

### logs

| Method | Description |
|--------|-------------|
| `logs.tail` | Stream recent gateway log lines |

### channels

| Method | Description |
|--------|-------------|
| `channels.status` | Status of all active channels |
| `channels.logout` | Disconnect a channel |

### config

| Method | Description |
|--------|-------------|
| `config.get` | Read current gateway configuration |
| `config.set` | Replace gateway configuration |
| `config.apply` | Apply and activate a configuration change |
| `config.patch` | Patch specific configuration keys |
| `config.schema` | Return the config JSON schema |

### exec / approvals

| Method | Description |
|--------|-------------|
| `exec.approvals.get` | Get current exec-approval policy |
| `exec.approvals.set` | Set exec-approval policy |
| `exec.approvals.node.get` | Get node-level exec-approval policy |
| `exec.approvals.node.set` | Set node-level exec-approval policy |
| `exec.approval.request` | Request approval for a pending exec |
| `exec.approval.resolve` | Resolve (approve/reject) a pending exec |

### wizard

| Method | Description |
|--------|-------------|
| `wizard.start` | Start a guided setup wizard |
| `wizard.next` | Advance to the next wizard step |
| `wizard.cancel` | Cancel the current wizard |
| `wizard.status` | Get current wizard state |

### talk / TTS

| Method | Description |
|--------|-------------|
| `talk.mode` | Get or set talk mode |
| `tts.status` | Text-to-speech subsystem status |
| `tts.providers` | List available TTS providers |
| `tts.enable` | Enable TTS |
| `tts.disable` | Disable TTS |
| `tts.convert` | Convert text to speech |
| `tts.setProvider` | Select active TTS provider |

### models

| Method | Description |
|--------|-------------|
| `models.list` | List available AI models on the gateway |

### agents

| Method | Description |
|--------|-------------|
| `agents.list` | List all agents registered on the gateway |
| `agents.create` | Create a new agent definition |
| `agents.update` | Update an existing agent definition |
| `agents.delete` | Delete an agent |
| `agents.files.list` | List files in an agent's workspace |
| `agents.files.get` | Read a file from an agent's workspace |
| `agents.files.set` | Write a file to an agent's workspace |

### skills

| Method | Description |
|--------|-------------|
| `skills.status` | Status of installed skills |
| `skills.bins` | List skill binary paths |
| `skills.install` | Install a skill |
| `skills.update` | Update an installed skill |

### update

| Method | Description |
|--------|-------------|
| `update.run` | Trigger a gateway self-update |

### voicewake

| Method | Description |
|--------|-------------|
| `voicewake.get` | Get voice-wake configuration |
| `voicewake.set` | Set voice-wake configuration |

### sessions

| Method | Description |
|--------|-------------|
| `sessions.list` | List all active sessions on the gateway |
| `sessions.preview` | Preview a session without loading full history |
| `sessions.patch` | Create or update a session (by key); used to ensure a session exists |
| `sessions.reset` | Reset a session's context |
| `sessions.delete` | Delete a session by key |
| `sessions.compact` | Compact session history |

### node (multi-node networking)

| Method | Description |
|--------|-------------|
| `node.pair.request` | Request pairing with a remote node |
| `node.pair.list` | List pending pair requests |
| `node.pair.approve` | Approve a node pair request |
| `node.pair.reject` | Reject a node pair request |
| `node.pair.verify` | Verify a completed pairing |
| `node.rename` | Rename a node |
| `node.list` | List known nodes |
| `node.describe` | Describe a specific node |
| `node.invoke` | Invoke a method on a remote node |
| `node.invoke.result` | Retrieve the result of a remote invocation |
| `node.event` | Send an event to a remote node |

### device pairing

| Method | Description |
|--------|-------------|
| `device.pair.list` | List pending device pair requests |
| `device.pair.approve` | Approve a device pair request |
| `device.pair.reject` | Reject a device pair request |
| `device.token.rotate` | Rotate the device bearer token |
| `device.token.revoke` | Revoke the device bearer token |

### cron

| Method | Description |
|--------|-------------|
| `cron.list` | List registered cron jobs |
| `cron.status` | Status of all cron jobs |
| `cron.add` | Add a new cron job |
| `cron.update` | Update an existing cron job |
| `cron.remove` | Remove a cron job |
| `cron.run` | Manually trigger a cron job |
| `cron.runs` | List recent cron run history |

### browser

| Method | Description |
|--------|-------------|
| `browser.request` | Execute a browser automation request |

### chat / messaging

| Method | Description |
|--------|-------------|
| `chat.history` | Fetch chat history for a session |
| `chat.abort` | Abort the current chat response |
| `chat.send` | Send a message to a session |
| `send` | Low-level message send (raw) |
| `agent` | Direct agent invocation |
| `agent.identity.get` | Get the identity of the active agent |
| `agent.wait` | Wait for an agent to become ready |

---

## Gateway Events (Server → Client Push)

These are unsolicited event frames the gateway may push to connected clients. Mission Control
does not currently subscribe to events (connections are short-lived), but these are part of
the protocol contract.

| Event | Description |
|-------|-------------|
| `connect.challenge` | Nonce challenge sent at connection open |
| `agent` | Agent state change or message |
| `chat` | Incoming chat message |
| `presence` | Presence state change |
| `tick` | Periodic heartbeat tick from gateway |
| `talk.mode` | Talk mode changed |
| `shutdown` | Gateway is shutting down |
| `health` | Health status update |
| `heartbeat` | Agent heartbeat received |
| `cron` | Cron job fired |
| `node.pair.requested` | New node pair request arrived |
| `node.pair.resolved` | Node pair request resolved |
| `node.invoke.request` | Remote node invocation request |
| `device.pair.requested` | New device pair request arrived |
| `device.pair.resolved` | Device pair request resolved |
| `voicewake.changed` | Voice-wake configuration changed |
| `exec.approval.requested` | Exec approval needed |
| `exec.approval.resolved` | Exec approval resolved |

---

## Session Key Format

Session keys are scoped string identifiers used to address agent sessions on the gateway.

### Agent Session Keys

General agent sessions use the prefix `agent`:

```
agent:<identifier>
```

### Gateway Main Agent Session Keys

Mission Control creates one "main" gateway agent per registered gateway. Its session key is:

```
agent:mc-gateway-<gateway_uuid>:main
```

Example:
```
agent:mc-gateway-550e8400-e29b-41d4-a716-446655440000:main
```

### OpenClaw Agent ID

The internal OpenClaw agent identifier for the gateway main agent is:

```
mc-gateway-<gateway_uuid>
```

### Board Agent Session Keys

Agent sessions linked to specific boards are provisioned by Mission Control using the agent's
`openclaw_session_id` field. This is typically set during agent provisioning and follows the
format the gateway accepted during `sessions.patch`.

---

## High-Level RPC Helpers (Python)

These functions in `gateway_rpc.py` are the primary interface used by Mission Control services:

| Function | Gateway Method | Description |
|----------|---------------|-------------|
| `openclaw_call(method, params, config)` | any | Generic RPC call |
| `openclaw_connect_metadata(config)` | `connect` | Connect and return hello payload |
| `send_message(message, session_key, config)` | `chat.send` | Send a chat message to a session |
| `get_chat_history(session_key, config)` | `chat.history` | Fetch session chat history |
| `delete_session(session_key, config)` | `sessions.delete` | Delete a session |
| `ensure_session(session_key, config, label)` | `sessions.patch` | Create or update a session |

All functions raise `OpenClawGatewayError` on gateway-level errors and transport exceptions.

---

## Error Handling

| Error Class | Raised When |
|-------------|-------------|
| `OpenClawGatewayError` | Gateway returns `ok: false`; transport failures (timeout, connection refused, WebSocket protocol errors) |

Transient errors (connection refused, timeout, HTTP 502/503/504) are distinguished from
non-transient errors (unsupported file, auth failures) in `constants.py` for retry policy
decisions in the lifecycle orchestrator.
