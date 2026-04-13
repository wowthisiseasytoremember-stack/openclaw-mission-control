#!/bin/bash
if [ -z "$1" ]; then
  echo "Usage: init-skill.sh <skill-name>"
  exit 1
fi
SKILL_DIR="skills/$1"
mkdir -p "$SKILL_DIR/references"
cat > "$SKILL_DIR/SKILL.md" << EOF
---
name: $1
description: TODO — describe what this skill does
---

# $1

## Steps
1. TODO — define workflow steps
EOF
echo "Created $SKILL_DIR/"
ls -la "$SKILL_DIR/"
