---
name: deep
description: Deep mode, up to 10 lookups per turn and read-only subagents, but no edits. Use for "/shipright:deep", "go deeper", or "deep mode".
---

# /shipright:deep

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/shipright_hooks.py" set deep`.
2. Relay the one-line output, including the reminder to switch the model menu to your strongest model.

## Rules while active

- Up to 10 lookups per turn, Agent included.
- Subagents must be read-only: `shipright:scout`, `scout`, `Explore`, `Plan` or `claude-code-guide`. Anything else, and Workflow, is denied.
- No edits (Edit, Write, NotebookEdit are denied). To build, switch with `/shipright:delegate`.
- Reply length and format are unrestricted. Subagent anomalies are reported (see `/shipright:mode`).
- End every reply with the marker `[deep]`.
