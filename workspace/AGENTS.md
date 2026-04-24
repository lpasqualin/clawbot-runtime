# AGENTS.md — Session Bootstrap

This file is the bootstrap authority for ClawBot's control layer.

---

## Core Stack — Load in This Order Every Session

| Order | File | Purpose |
|-------|------|---------|
| 1 | SOUL.md | How to think, act, and make decisions |
| 2 | ORCHESTRATION.md | Who does the work and how to delegate |
| 3 | ROUTING.md | Where information belongs |
| 4 | AGENT_ROLES.md | Specialist domain ownership |
| 5 | PERMISSIONS.md | What actions require approval |
| 6 | MEMORY.md | Current reality, priorities, constraints |

Load the minimum context needed. Do not read every file every session.

## Session Load Override (Execution Phase)

The load order above is a bootstrap sequence, not a requirement to fully load all file contents.

After initial bootstrap, ClawBot must restrict active context based on task class.

### Context by Task Class

CRUD / LOOKUP:
- Active context: SOUL.md, ROUTING.md only
- Do NOT load MEMORY.md
- Do NOT load additional workspace files unless strictly required by the tool

ROUTING / PLANNING:
- Add ORCHESTRATION.md and AGENT_ROLES.md if needed
- Keep context narrow and relevant

SUMMARY:
- Load only the source being summarized
- Do NOT load full MEMORY.md
- Do NOT load unrelated project files

DEBUGGING:
- Load only logs and relevant system files
- Do NOT load full workspace

DEEP_WORK:
- Load only files directly required by the task
- Never load full workspace by default
- MEMORY.md must be selectively read, not fully loaded

HEARTBEAT / CRON:
- Active context: SOUL.md + HEARTBEAT.md
- Do NOT load MEMORY.md unless the monitoring rule explicitly requires it
- Do NOT load full session history

---

## Hard Rules

- Never load full MEMORY.md by default
- Never load full workspace context
- Never load all files “just in case”
- Always prefer the smallest valid context

If additional context seems needed:
- justify it
- load only that specific file or section

---

## Load On Demand

| File | Load When |
|------|-----------|
| SYSTEMS.md | Routing a system-of-record decision |
| TOOLS.md | Using local machine tools or services |
| IDENTITY.md | Identity or profile context needed |

---

## Delegation Only

| File | Load When |
|------|-----------|
| HANDOFF.md | Creating or reviewing a delegation packet |
| DELEGATION_TEMPLATE.md | Structuring a handoff |

---

## Heartbeat Only

| File | Load When |
|------|-----------|
| HEARTBEAT.md | Running the monitoring/alert cycle |

---

## Memory Authority

ClawBot is the only agent allowed to write to MEMORY.md.
Specialists may propose facts, decisions, risks, or constraints.
ClawBot curates and writes.
