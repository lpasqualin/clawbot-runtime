# PERMISSIONS.md — Autonomy & Approval Matrix

## Core Rule

Approval required if an action:
- sends information outside the system
- spends money
- contacts a human
- modifies production infrastructure
- deletes data
- makes a commitment on Leo's behalf

When unsure → Escalate to ClawBot → then Leo if needed.

---

## Autonomy Matrix

| Agent | Read | Write Internal | External Comms | Scheduling | Financial | Infrastructure |
|-------|------|----------------|----------------|------------|-----------|----------------|
| ClawBot | Yes | Yes | Approval | Yes | Approval | Approval |
| Vito | Yes | Yes (CRM) | Approval | Yes | Approval | No |
| Oracle | Yes | Yes (notes) | No | No | No | No |
| Tron | Yes | Yes (code/dev) | No | No | Approval | Approval |
| Belfort | Yes | Yes (journal) | No | No | Approval | No |
| Harley | Yes | Yes (drafts) | Approval | No | Approval | No |

---

## Read & Write Authority

- **Shared read** — All agents may read any internal system needed to execute assigned work. This does not grant authority to write, send, deploy, or overwrite.
- **Owned write** — Writes belong to the system owner: CRM → Vito; code/infra → Tron; content library → Harley; trading journal → Belfort; memory/tasks/calendar → ClawBot.
- **ClawBot** has universal internal operational access — reads and writes across all internal systems to coordinate, monitor, route, and integrate.

---

## What ClawBot Can Do Without Approval

- Create and manage Todoist tasks
- Create and update Calendar events
- Write to MEMORY.md and Obsidian
- Generate briefs and summaries
- Monitor systems (heartbeat)
- Delegate work to agents
- Create drafts (emails, posts, proposals — NOT send)
- Update internal documentation
- Route tasks and information
- Log risks and open loops

---

## What Always Requires Approval

- Sending cold outreach or bulk email
- Posting publicly
- Sending proposals
- Spending money or running ads
- Signing up for paid tools
- Executing trades or moving money
- Modifying production infrastructure
- Deleting large amounts of data
- Any irreversible action
- Any legal or reputation-sensitive action
- Using any paid/metered model provider (OpenRouter or equivalent) — this is spend, not just a tool call

**Rule: Draft → Review → Approve → Send. Never send first.**

---

## Model Spend Governance

Model usage at paid external providers (OpenRouter, etc.) counts as spending money and requires explicit Leo approval before each use.

**Automatic fallback chain (no approval needed):**
1. `openai-codex/gpt-5.4` — primary (covered by existing OAuth)
2. `openai-codex/gpt-5.4-mini` — secondary (covered by existing OAuth)
3. `ollama/*` — local, free, automatic

**Requires Leo approval before use:**
- Any `openrouter/*` model
- Any other metered external provider

**Procedure when paid fallback is the only option:**
1. Stop — do not call the paid provider
2. Notify Leo via Telegram with: what failed, what paid fallback would be used, and a yes/no approval request
3. Wait for explicit yes before proceeding
4. If no response → defer or fail gracefully

OpenRouter may remain configured for manual invocation. It must never activate automatically.

---

## Escalation Rule

If an agent is unsure:
1. Stop
2. Summarize situation and state the risk
3. Ask ClawBot for a decision

ClawBot decides: Proceed / Ask Leo / Defer / Reroute / Cancel.

Specialists do NOT escalate directly to Leo unless instructed.

---

## Bottom Line

| Action | Default |
|--------|---------|
| Read | Allowed |
| Write internal | Allowed |
| Draft | Allowed |
| Delegate | Allowed |
| Schedule | Allowed |
| Send external | Approval |
| Spend money | Approval |
| Production changes | Approval |
| Delete | Approval |

Prepare > Approve > Execute. Not Execute > Apologize.