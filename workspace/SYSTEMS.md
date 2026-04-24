# SYSTEMS.md — Systems of Record

## Purpose

Defines where information belongs. Route to exactly one authoritative system.
Do not duplicate across systems.

---

## Primary Systems of Record

| Information Type | System | Owner |
|------------------|--------|-------|
| Tasks / Action items | Todoist | ClawBot |
| Events / Time commitments | Google Calendar | ClawBot |
| Durable facts / Decisions | MEMORY.md | ClawBot |
| Project knowledge / Notes | Obsidian | Leo + Oracle + Tron |
| Contacts / Pipeline | CRM (Attio) | Vito |
| Code / Scripts / Infra | Codebase | Tron |
| Trading / Portfolio | Trading Journal | Belfort |
| Content / Assets | Content Library | Harley |
| Temporary work | Workspace | Task owner |

---

## System Definitions

### Todoist — Tasks
- Tasks, to-dos, follow-ups, delegated items
- NOT for events with times, durable facts, or long notes

### Google Calendar — Events
- Meetings, calls, appointments, time-blocked work, timed deadlines
- NOT for general tasks, notes, or durable information

### MEMORY.md — Durable Memory
- Decisions, priorities, constraints, preferences, risks, role definitions, architecture decisions
- NOT for tasks, events, long documents, research, or drafts
- ClawBot is the only writer

### Obsidian — Project Knowledge
- Project plans, research, strategy, architecture, meeting notes, documentation, daily notes
- NOT for tasks, quick facts, or calendar events

**Vault structure:**

| Folder | Purpose |
|--------|---------|
| 00 Inbox | Quick capture, rough notes, ideas |
| 01 Daily | Daily notes, meeting notes, logs |
| 02 Projects | Plans, research, architecture, strategy |
| 03 Operations | Admin, finance, health, home |
| 04 Assets | About Leo, digital assets, reference |

### Workspace — Temporary Work
- Scratch work, draft exports, intermediate files, experiments
- Anything important must be moved to a real system of record
- Workspace is temporary

### CRM (Attio) — Sales Pipeline
- Contacts, companies, leads, pipeline stages, follow-up state, sales notes
- Owned by Vito

### Codebase — Technical Systems
- Scripts, automations, integrations, infrastructure configs, technical docs
- Owned by Tron

### Trading Journal
- Trades, portfolio tracking, risk analysis, trade notes
- Owned by Belfort

### Content Library
- Content ideas, posts, scripts, assets, funnels, email content
- Owned by Harley

---

## Information Lifecycle

| Stage | System |
|-------|--------|
| Idea | Obsidian |
| Research | Obsidian |
| Plan | Obsidian |
| Decision | MEMORY.md |
| Tasks | Todoist |
| Scheduled time | Calendar |
| Execution output | Workspace → then moved |
| Results / Notes | Obsidian |
| Lessons / Rules | MEMORY.md |

---

## Core Principle

Put information in the system where it will be used and maintained.
Correct routing > storing more information.

_Update this file when a system is added or routing rules change — not when projects change._