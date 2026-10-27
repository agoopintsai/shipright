---
name: chat
description: Chat mode, plain text replies with a lookup quota and a word limit. Use for "/shipright:chat", "/shipright:chat 200", "chat mode", or "short answers".
---

# /shipright:chat

1. If `$ARGUMENTS` is a number it is the word limit: run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/shipright_hooks.py" set chat <number>`. Otherwise run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/shipright_hooks.py" set chat` (default 300 words).
2. Relay the one-line output, including the reminder to switch the model menu to a fast, cheap model with low effort.

## Rules while active

- Conclusion first, then only the reasons that matter. The Stop hook sends back replies over the word limit.
- Plain text only: no edits, artifacts, slides or documents (hooks deny them).
- At most 3 lookups per turn; Agent and Workflow are denied. Mark answers "confirmed" or "guessed".
- When the quota is spent, say the question needs `/shipright:deep`.
- End every reply with the marker `[chat]`.
