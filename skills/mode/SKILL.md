---
name: mode
description: Show or switch the session mode (chat, deep, delegate, or off). Modes are enforced by hooks, not just by instructions. Use for "/shipright:mode", "what mode am I in", or "switch mode".
---

# /shipright:mode

Three mutually exclusive modes. The current mode lives in a per-session flag file; hooks inject a banner each turn and check every tool call. It persists until you switch it or the session ends. No mode set means no quotas.

| Mode | Lookups per turn | What is blocked |
|---|---|---|
| chat | 3 (Read, Grep, Glob, Bash, WebFetch, WebSearch) | Replies of more than 300 words are sent back for a rewrite (`chat 200` changes the limit). Agent, Workflow, edits and artifact or document tools are denied. |
| deep | 10 (the same tools plus Agent) | Only read-only subagents (`shipright:scout`, `scout`, `Explore`, `Plan`, `claude-code-guide`). Workflow and edits are denied. |
| delegate | 5 personal lookups | Edits ask first. Agent is not limited but is monitored: more than 4 at once, more than 8 per turn, or one running over 10 minutes raises an alert and a "Subagent status:" line in the reply. |

Skill, AskUserQuestion, ToolSearch, `mcp__ccd_*`, SendMessage, ListAgents and ScheduleWakeup are never counted. Tool calls made inside subagents are not counted either, but edits stay denied in chat and deep.

The red-zone gate (see `/shipright:grill`) is independent of modes and always applies.

## How

- `/shipright:mode <chat|deep|delegate>`: run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/shipright_hooks.py" set <mode>` (for chat, an optional word limit may follow: `set chat 200`).
- `/shipright:mode off`: run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/shipright_hooks.py" clear`.
- Status: run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/shipright_hooks.py" status`.
- Relay the one-line output to the user. Claude cannot change the model itself: remind the user to switch the model and effort in the model menu to match the mode.
- Modes only work in a project with a valid `shipright.yaml`; otherwise the hooks stay inert.

Arguments: `$ARGUMENTS`
