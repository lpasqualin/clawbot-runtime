# MEMORY.md — ClawBot Durable Memory

_Last updated: 2026-06-04_

---

## MEMORY MAINTENANCE RULE

`ACTIVE SUMMARY` is the boot layer. Keep it short, current, high-signal.

When durable memory changes:
1. Update the relevant durable section.
2. Update `ACTIVE SUMMARY` only if startup-relevant judgment changes.
3. Remove stale items from `ACTIVE SUMMARY`.
4. Move superseded rules to `SUPERSEDED / ARCHIVED` if historical trace matters.

Do not use this file as a session log.
Do not store tasks, drafts, research, or open loops here — those live in Todoist and Obsidian.

---

## ACTIVE SUMMARY

- Primary machine: MS-01 (leo-paz-MS-10-Venus, 100.86.220.59)
- Primary orchestrator: OpenClaw 2026.6.1, model: openrouter/google/gemini-2.5-flash (temporary — Codex OAuth broken on 6.1, missing model.request scope)
- Revenue motion is top priority — BBS client acquisition before more architecture
- Dashboard fully live at http://100.86.220.59:8181 — scripts own data, ClawBot owns judgment via patch workflow only
- Agent OS is active as ClawBot governance layer — Phases A-H, Core Loop Proof Gate blocks expansion
- Siftwise is active — Phase 1 AI Intelligence Layer in progress
- File-based memory is authoritative; pgvector parked
- Todoist: 5 projects, sections auto-map to dashboard cards dynamically via sync_projects.py

---

## Strategic Model

Four lenses — everything maps to at least one:

- **Money** — BBS (revenue, clients, deployments)
- **Position** — Portfolio / Career (proof of work, credibility)
- **Operate** — ClawBot (infrastructure, memory, continuity)
- **Build** — Siftwise (active, Phase 1 AI Intelligence Layer) / future products

Bias toward execution, shipping, revenue, real-world use.
Anti-bias: over-organizing, over-architecting, collecting without acting.

---

## Project Priorities

1. **BBS** — Revenue engine. First client acquisition is the highest-leverage action.
2. **Career / Portfolio** — Proof of work, positioning, case studies.
3. **ClawBot** — Operator layer. Daily ops, memory, continuity.
4. **Farah** — Secondary income path. Content systems.
5. Siftwise — Active. Phase 1 AI Intelligence Layer in progress. Not parked.
6. Agent OS — Active as ClawBot governance layer. Phases A-H roadmap sealed with Ax. Core Loop Proof Gate blocks all expansion phases. Not a standalone product.

---

## Infrastructure

**Primary machine:** MS-01 (leo-paz-MS-10-Venus, Tailscale 100.86.220.59)
Intel i9-13900H, 32GB DDR5, Ubuntu 24.04. ProDesk retained as fallback only.

**MS-01 migration status (completed 2026-04-13):**
- Todoist fixed. Working runtime path uses `TODOIST_API_KEY` as the source value and maps it into `TODOIST_API_TOKEN` for the Todoist skill/CLI.
- systemd `EnvironmentFile` override is in place.
- Obsidian REST API is running as `obsidian-api.service` on port `27124`, with a custom Obsidian `SKILL.md`, against vault `/home/leo-paz/obsidian-vault`.
- `gog` v0.12.0 is installed and authenticated for `leo.pasqua88@gmail.com`.
- All agent memory directories are created and indexed.
- Exec approvals wildcard is enabled for all agents.

**Post-migration setup gaps to resume next session:**
- Skill binary installs still missing: `ripgrep`, `tmux`, `ffmpeg`, `gh`.
- API keys still needed: `RISK_OFFICER_TOKEN`, `NOTION_API_KEY`, `OPENAI_API_KEY`.
- Remaining automation setup: cron jobs being built with Ax, vault git sync cron, Obsidian vault sync to laptop.

**Model stack:**
Primary (temporary): openrouter/google/gemini-2.5-flash
Codex status: OAuth broken on 6.1 — missing model.request scope — awaiting OpenClaw fix
Fallback chain: openai-codex/gpt-5.4-mini → openrouter/google/gemini-2.5-flash → openrouter/moonshotai/kimi-k2.6 → ollama/qwen3:14b → ollama/gemma4:e4b → openrouter/auto (last resort)
OpenRouter weekly budget cap: in place
NEVER edit llmFallbacks in openclaw.json directly — use openclaw models fallbacks add/remove/clear

**Model aliases:**
- `premium` → openai-codex/gpt-5.4
- `emergency` → openai-codex/gpt-5.4-mini
- `general` → ollama/qwen3:14b
- `fast` → ollama/gemma4:e4b
- `coding` → ollama/qwen2.5-coder:14b
- `embed` → ollama/nomic-embed-text

**clawbot-runtime repo:** Git initialized directly at `/home/clawbot/.openclaw` (runs as clawbot user). Push pattern: `sudo -u clawbot bash -l -c 'cd /home/clawbot/.openclaw && git add -A && git commit -m "msg" && git push'`. Old `/home/leo-paz/repos/clawbot-runtime` is deprecated and deleted.

---

## Dashboard

**File:** `/home/leo-paz/Dashboard/dashboard.json`
**Viewer:** `http://100.86.220.59:8181/dashboard.html`

Folder structure:
- `scripts/` — sync_dashboard.py, sync_activity.py, sync_projects.py, webhook.py, apply_judgment_patch.py
- `patches/` — dashboard_judgment_patch.json (overwritten daily, never accumulated)
- `backups/` — auto-backups, last 7 kept
- `logs/` — sync.log

Write ownership — one writer per domain, no exceptions:
- sync_dashboard.py → tasks, calendar — every 15min
- sync_activity.py → activity_feed — every 15min+2
- sync_projects.py → projects[] cards (dynamic Todoist sections) — every 15min+5
- health-check.sh → tool_status, clawbot_status, todays_cost_usd — every 30min
- apply_judgment_patch.py → judgment fields only — on morning brief

HARD RULE: No agent writes dashboard.json directly.
ClawBot judgment flows through: patches/dashboard_judgment_patch.json → apply_judgment_patch.py → dashboard.json

ClawBot judgment fields (only these):
- today.primary_focus, secondary_focus, must_do, should_do, avoid_today, risk_flags, agent_note
- needs_leo[]
- projects[].health, blocked, blocker, current_focus, next_action
- weekly_metrics.projects_moved, bbs_outreach_count, followups_sent

Never touch (script-owned):
- tasks, calendar, tool_status, activity_feed, clawbot_status
- projects[].tasks, tasks_open, tasks_done

Morning brief write pattern:
1. Read dashboard.json
2. Generate brief and deliver to Discord/Telegram
3. Write dashboard_judgment_patch.json to patches/
4. Run: python3 /home/leo-paz/Dashboard/scripts/apply_judgment_patch.py
5. If apply fails, warn but do not retry

Project card IDs are auto-generated from Todoist section names via slugify(). Current IDs:
bbs-pre-launch, bbs-marketing, bbs-outreach, certificates, portfolio-positioning, job-search-income, parked, side-projects, clawbot-agent-operator, future-ideas, clawbot-agent-dashboard, worth-exploring, siftwise-v4, tool-research, personal-admin, personal-finance, personal-other, home-maintenance, home-renovations, home-upgrades-someday

---

## Cron Jobs (current — 13 total)

| Job | Agent | Schedule | Delivery |
|-----|-------|----------|----------|
| daily-morning-brief-discord | main | 7am ET daily | #today |
| daily-midday-checkin-discord | main | 12pm ET daily | #today |
| daily-evening-review-discord | main | 9pm ET daily | #today |
| oracle-intelligence-digest | oracle | 7:30am ET daily | #today |
| system-health-check | main | every 12h | #clawbot-config |
| tron-systems-review | tron | TBD | #clawbot-config |
| oracle-weekly-brief | oracle | Sunday 9am ET | #clawbot-intelligence |
| daily-memory-staging | main | nightly | none |
| weekly-memory-governor | main | weekly | #clawbot-config |
| weekly-system-hygiene-audit | main | weekly | #clawbot-config |
| vito-weekly-pipeline-review | vito | Mon/Wed/Fri 9am ET | #clawbot-config |
| belfort-weekly-capital-review | belfort | Sunday 10am ET (disabled) | #clawbot-config |
| weekly-file-retention | main | Monday 3am ET | #clawbot-config |

Morning brief now writes judgment patches to MEMORY.md via apply_judgment_patch.py.
File retention archives session logs/staging/proposals/judgment after 30-45 days.
SQLite is OpenClaw 6.1's internal cron store — jobs.json is source of truth, synced to SQLite on deploy.

---

## Todoist Structure

5 projects (at limit). Sections auto-map to dashboard cards via sync_projects.py.
Add a section in Todoist → card appears on next 15min sync. Remove → disappears. No script edits needed.

Projects and IDs:
- Ventures (6g6qrJfXm4w3fpFV) → VENTURES column → sections: Beacon Bridge Strategies, Farah
- ClawBot & AI (6g6x3p95vH4GPMcH) → AI & PROJECTS column → sections: ClawBot, Siftwise, Agent OS
- Career (6g6qrJmm6hF2hqh7) → CAREER column → sections: Portfolio & Positioning, Certifications, Job Search
- Personal (6g6qrJrwQ2HMrWQp) → FAMILY & HOUSEHOLD column → sections: Admin, Finance, Other
- Home (6g6qrJwvp24Q36Hh) → not on dashboard

Todoist section deep links not supported — cards link to project root.

---

## Agent Org Structure

- **ClawBot** — Chief of Staff / Orchestrator
- **Vito** — Sales / CRM / Outreach / Pipeline
- **Oracle** — Research / Intelligence / Analysis
- **Tron** — Dev / Automation / Infrastructure
- **Belfort** — Markets / Capital / Risk
- **Harley** — Content / Growth / Monetization

---

## Intelligence Pipeline

**Architecture:** Deterministic fetch → Oracle synthesis → Discord delivery

**Fetch script:** `/home/clawbot/.openclaw/scripts/fetch_intelligence.py`
- Runs at 7:15am daily as clawbot user
- Reads source registry from `/home/clawbot/.openclaw/workspace/config/intelligence_sources.json`
- Writes staged JSON to `/home/clawbot/.openclaw/workspace/intelligence/daily/YYYY-MM-DD.json`
- Only fetches sources with `subscribed: true`

**Source registry:** `/home/clawbot/.openclaw/workspace/config/intelligence_sources.json`
- Three lanes: `oracle_tier1`, `oracle_radar`, `belfort`
- Add new sources here — no prompt rewrites needed
- Set `subscribed: true` when email is confirmed arriving

**Oracle Intelligence Digest:** runs at 7:30am daily via OpenClaw cron
- Agent: oracle
- Reads today's staged JSON
- Classifies items: AI_SIGNAL / BBS_OPPORTUNITY / CLAWBOT_RELEVANT / STRATEGY / NOISE
- Writes digest to `/home/clawbot/.openclaw/workspace/intelligence/daily/YYYY-MM-DD.digest.md`
- Delivers to Discord `#morning` channel

**Weekly Oracle brief:** runs Sunday 9am — update pending
- Currently does 1–3 targeted web searches
- Future: reads last 7 daily digests + max 2 targeted searches

**Brief boundary rules:**
- Morning Brief: dashboard.json only — no newsletters, no market scan
- Oracle daily digest: newsletters + AI signals — no crypto/markets
- Belfort scan: crypto/markets/macro only — not built yet
- Weekly Oracle: synthesis layer — reads daily digests, minimal fresh search

---

## Codex Re-auth Pattern

When `openai-codex/gpt-5.5` returns `livenessState: blocked`:
1. Open SSH tunnel from Windows: `ssh -L 1455:localhost:1455 leo-paz@100.86.220.59`
2. On MS-01: `sudo -u clawbot bash -l -c 'openclaw configure'`
3. Follow the OAuth URL it provides — opens in browser via tunnel
4. After configure completes, test: `sudo -u clawbot bash -l -c 'openclaw agent --agent main --message "reply with just: ok" --model openai-codex/gpt-5.5 --timeout 30 2>/dev/null'`
5. If `ok` returns, switch default back: use `openclaw models fallbacks` commands, not direct JSON edits

**Never edit `llmFallbacks` directly in `openclaw.json`** — use `openclaw models fallbacks add/remove/clear`

---

## Fallback Chain (current)

Primary (temporary): `openrouter/google/gemini-2.5-flash`
Reason: openai-codex OAuth broken on 6.1 — missing model.request scope — awaiting OpenClaw patch

Fallbacks (in order):
1. `openai-codex/gpt-5.4-mini`
2. `openrouter/google/gemini-2.5-flash`
3. `openrouter/moonshotai/kimi-k2.6`
4. `ollama/qwen3:14b`
5. `ollama/gemma4:e4b`
6. `openrouter/auto` — last resort only, expensive

OpenRouter weekly budget cap in place.

---

## ACL Pattern (permanent fix)

When VS Code or scripts can't access clawbot-owned paths:
```bash
sudo setfacl -Rm u:leo-paz:rwx /path/to/dir/
sudo setfacl -Rm d:u:leo-paz:rwx /path/to/dir/
# if still blocked, fix the mask:
sudo setfacl -m m::rwx /path/to/dir/
```

Applied permanently to:
- `/home/clawbot/.openclaw/` — full tree
- `/home/clawbot/.openclaw/workspace/` — full tree
- `/home/clawbot/.openclaw/cron/` — read access for leo-paz scripts

## Decisions

- **Memory architecture:** File-based primary. pgvector parked until dataset justifies it.
- **Memory write authority:** ClawBot only. Specialists produce outputs; ClawBot extracts and writes durable facts.
- **Project context model:** Three layers — (A) MEMORY.md global context, (B) Obsidian project depth, (C) task-specific handoff packets.
- **System ownership:** MEMORY.md + Todoist + Calendar + Dashboard → ClawBot. CRM → Vito. Obsidian → Leo/Oracle/Tron. Code/infra → Tron. Content → Harley. Trading journal → Belfort.
- **Dashboard:** scripts own data writes, ClawBot owns judgment only via patch workflow. No agent writes dashboard.json directly.
- **External actions:** Posting, emailing, messaging, creating accounts — explicit approval required every time.
- **Model spend governance:** Using paid external model providers (OpenRouter, etc.) = spending money = requires Leo's explicit approval per session. Fallback chain hits gemini and kimi (OpenRouter) before Ollama. OpenRouter weekly budget cap in place.
- **Capability model:** Shared read, owned write. Domain ownership determines judgment and write authority.
- **Operating cadence:** Morning Brief → day capture → Evening Review. Daily: ClawBot. 3x/week: Vito. Weekly: Oracle, Tron, Harley, Belfort.
- **Brief delivery:** Telegram + Obsidian daily note + Discord morning brief channel (`1492262253255200838`). Dashboard snapshot written at morning brief time.
- **Data source priority:** Todoist → Google Calendar → Git → Email.
- **OpenClaw:** Swappable orchestrator. All durable value built as external services. Public repo = proof-of-work surface.
- **Revenue motion first:** Until BBS has paying clients, agent work supports revenue — not content, branding, or architecture.
- **Siftwise inheritance:** The ClawBot personal knowledge vault / ingestion layer may later feed Siftwise, but Siftwise remains non-primary unless directly tied to the shared ingestion work.
- **Agent OS:** Active as ClawBot governance layer. Phases A-H roadmap sealed with Ax. Core Loop Proof Gate blocks all expansion phases.

---

## Proposal / Approval Pattern

For governance workflows, ClawBot separates proposal from execution.

Proposal jobs may inspect system state and generate suggested actions, but they must not perform destructive writes or deletions.

Execution requires explicit Leo approval.

Pattern:
1. Generate proposal with stable IDs.
2. Deliver proposal to Leo.
3. Leo approves specific IDs.
4. Executor applies only approved IDs.
5. Executor logs what changed.

Applies to:
- weekly-memory-governor
- weekly-system-hygiene-audit
- future cleanup or governance jobs

---

## SUPERSEDED / ARCHIVED

- **Agent OS as standalone project** — paarked post-vacation 2026-05. Correct call given competitive realities. Foundations preserved in Obsidian `40 - Agent OS/`.
- **TRELLO_API_KEY / TRELLO_API_TOKEN** — removed from pending API keys. Notion is the knowledge base. Trello not in use.
- **pgvector** — parked. File-based memory is sufficient at current scale.
- **ClawBot as direct dashboard writer** — superseded 2026-06-03. ClawBot now writes only dashboard_judgment_patch.json; apply_judgment_patch.py handles the merge. Direct dashboard.json writes by agents are prohibited.
- **Siftwise as parked** — superseded 2026-06-03. Siftwise is active, Phase 1 AI Intelligence Layer in progress.
- **Agent OS as scrapped standalone project** — superseded 2026-06-03. Agent OS is active as ClawBot governance layer.