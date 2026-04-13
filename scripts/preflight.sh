#!/bin/bash
echo "=== OpenClaw Pre-Flight Check ==="
ERRORS=0

# Check config exists
if [ ! -f "$HOME/.openclaw/openclaw.json" ]; then
  echo "FAIL: openclaw.json not found"
  ERRORS=$((ERRORS + 1))
else
  echo "OK: openclaw.json exists"
fi

# Check permissions
PERMS=$(stat -c "%a" "$HOME/.openclaw/openclaw.json" 2>/dev/null)
if [ "$PERMS" != "600" ]; then
  echo "WARN: openclaw.json permissions are $PERMS (should be 600)"
else
  echo "OK: openclaw.json permissions correct"
fi

# Check if gateway process is running
if pgrep -f "openclaw" > /dev/null 2>&1; then
  echo "OK: OpenClaw process running"
else
  echo "WARN: No OpenClaw process detected"
fi

if [ "$ERRORS" -gt 0 ]; then
  echo "PRE-FLIGHT FAILED: $ERRORS error(s)"
  exit 1
else
  echo "PRE-FLIGHT PASSED"
  exit 0
fi
