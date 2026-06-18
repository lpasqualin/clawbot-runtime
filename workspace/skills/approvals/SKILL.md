---
name: approvals
description: List, review, approve, or reject pending ClawBot decisions.
user-invocable: true
---

# Approval Review Skill

## Purpose

Approvals are pending decisions stored in SQLite at `/home/clawbot/.openclaw/state/approvals.db`. ClawBot is the approval **clerk**, not the authority — `approval_handler.py` is the authority. All state changes go through it.

This skill covers exactly five commands and no others:

- `list pending`
- `show <id>`
- `review <id>` (alias for `show <id>`)
- `approve <id>`
- `reject <id> [reason]`

Rules:

- Never approve or reject without an explicit ID from the operator.
- Never infer approval intent from vague language ("looks good", "ship it", "that one"). If the operator doesn't give an explicit ID, ask for one.
- If the command is ambiguous, ask for the explicit ID — do not guess.

## Command routing

### `list pending`

```bash
python3 /home/clawbot/.openclaw/scripts/approval_handler.py \
  --command "list pending"
```

Report the output verbatim. No actor required — this is a read-only command.

### `show <id>`

Run two commands and combine their output:

```bash
python3 /home/clawbot/.openclaw/scripts/approval_handler.py \
  --command "show <id>"

python3 /home/clawbot/.openclaw/scripts/approval_store.py show-brief <id>
```

Present the `show-brief` output first as the decision summary, then the `show` output as the full detail below a separator (`---`). No actor required — this is a read-only command.

### `review <id>`

`review <id>` is an alias for `show <id>`. Use either — they do the same thing.

This is the preferred operator-facing command because notification cards use `review`.

When the operator types `review <id>`, execute identically to `show <id>`:

```bash
python3 /home/clawbot/.openclaw/scripts/approval_handler.py \
  --command "show <id>"

python3 /home/clawbot/.openclaw/scripts/approval_store.py show-brief <id>
```

Present `show-brief` output first as the decision summary, then `show` output as full detail below a separator. No actor required — this is a read-only command.

### `approve <id>`

Requires the sender's actual user ID from session context — see **Actor identity** below.

```bash
python3 /home/clawbot/.openclaw/scripts/approval_handler.py \
  --actor <platform>:<sender_user_id> \
  --command "approve <id>"
```

### `reject <id> [reason]`

Requires the sender's actual user ID from session context — see **Actor identity** below.

```bash
python3 /home/clawbot/.openclaw/scripts/approval_handler.py \
  --actor <platform>:<sender_user_id> \
  --command "reject <id> [reason]"
```

## Actor identity

For `approve` and `reject` commands:

- If OpenClaw exposes the sender's user ID in session context, use it as the actor:
  - Discord: `--actor discord:<sender_user_id>`
  - Telegram: `--actor telegram:<sender_user_id>`
- If sender identity is not available in context, do NOT attempt to approve or reject.
  Instead respond: "Cannot execute approval — sender identity unavailable. Use the dashboard or CLI directly."
- Do NOT hardcode any user ID.
- Do NOT invent or guess an actor ID.

For `list`, `show`, and `review` commands:
- No actor required. These are read-only and work without authentication.

## Refused commands

Do **not** do any of the following:

- `approve all` — not supported. Tell the operator to use an explicit ID.
- `approve all <type>` — not supported yet. Tell the operator to use an explicit ID.
- Approving based on notification text alone, without operator confirmation.
- Running `approval_store.py` write operations directly — only `approval_handler.py` may mutate state.
- Editing `MEMORY.md` or any file as part of approval execution — that is a separate apply step, not part of this skill.

## Error handling

- If the handler returns `Not authorized` → report it verbatim. Do not retry with a different actor.
- If the handler returns `No pending approvals` → report it. Do not invent pending items.
- If the approval ID doesn't exist → report the handler output verbatim.

## Notification Template

Cron jobs use this format when posting pending approvals to Discord. ClawBot should also use this format when summarizing pending items unprompted.

```
---
**APPROVAL REQUIRED**

**ID:** {id}
**Type:** {type} | **Risk:** {risk_level}
**Source:** {source_job}

**Decision:**
{decision_brief.decision}

**Why proposed:**
{decision_brief.why_proposed}

**If approved:**
{decision_brief.changes_if_approved as bullet list}

**Risk:**
{decision_brief.risk}

**Recommended:** {decision_brief.recommended_action} *(confidence: {decision_brief.confidence})*

---
Commands:
`show {id}` — full detail
`approve {id}` — approve this proposal
`reject {id}` — reject this proposal
---
```

For batches (multiple pending items), post one card per item. Do not collapse into a table.
