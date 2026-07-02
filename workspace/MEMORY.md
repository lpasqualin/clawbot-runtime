# MEMORY.md — ClawBot Durable Memory

_Last updated: 2026-06-22_

---

## MEMORY MAINTENANCE RULE

`ACTIVE SUMMARY` is the boot layer. Keep it short, current, high-signal.

When durable memory changes:
1. Update the relevant durable section.
2. Update `ACTIVE SUMMARY` only if startup-relevant judgment changes.
3. Remove stale items from `ACTIVE SUMMARY`.

## Open Loops / Risks
- **[JP-2026-06-24-001]** BBS outreach is the stated #1 focus (Land first BBS client) yet has been soft-blocked on website copy for days. Vito has 22 med spa prospects ready. This is a sub-2-hour execution bottleneck with direct revenue implication. If not unblocked today, it becomes a pattern of priority inversion where preparation displaces actual customer contact.
4. Move superseded rules to `SUPERSEDED / ARCHIVED` if historical trace matters.

Do not use this file as a session log.
Do not store tasks, open loops, operational state, or current priorities here.
Do not store model config here — openclaw.json owns that.
Tasks live in Todoist. Plans live in Obsidian. Models live in openclaw.json.

---

## ACTIVE SUMMARY

- Primary machine: MS-01 (leo-paz-MS-10-Venus, 100.86.220.59)
- Primary orchestrator: OpenClaw 2026.6.1
- Revenue motion is top priority — BBS client acquisition before more architecture
- Dashboard fully live at http://100.86.220.59:8181 — scripts own data, ClawBot owns judgment via patch workflow only
- File-based memory is authoritative; pgvector parked
- Todoist sections auto-map to dashboard cards dynamically via sync_projects.py

---

## Strategic Model

Four lenses — everything maps to at least one:

- **Money** — BBS (revenue, clients, deployments)
- **Position** — Portfolio / Career (proof of work, credibility)
- **Operate** — ClawBot (infrastructure, memory, continuity)
- **Build** — Siftwise / future products

Bias toward execution, shipping, revenue, real-world use.
Anti-bias: over-organizing, over-architecting, collecting without acting.

---

## Infrastructure

**Primary machine:** MS-01 (leo-paz-MS-10-Venus, Tailscale 100.86.220.59)
Intel i9-13900H, 32GB DDR5, Ubuntu 24.04. ProDesk is legacy/retired.

**Key services:**
- `openclaw.service` — ports 18789/18791/18792, runs as clawbot user
- `ollama.service` — port 11434
- `obsidian-api.service` — port 27124, vault at `/home/leo-paz/obsidian-vault`
- `openclaw-perms.service` — restores leo-paz ACL after every OpenClaw restart
- `health-check.sh` — system cron, fires Discord alert on CRITICAL/WARNING

**Key paths:**
- OpenClaw runtime: `/home/clawbot/.openclaw/`
- Dashboard: `/home/leo-paz/Dashboard/`
- Dashboard JSON: `/home/leo-paz/Dashboard/dashboard.json`
- Ingest dropzone: `/home/leo-paz/ingest/dropzone/`
- MEMORY.md: `/home/clawbot/.openclaw/workspace/MEMORY.md`
- Memory write script: `/home/clawbot/.openclaw/scripts/memory_write.sh`
- Push script: `/home/leo-paz/scripts/push-all.sh`

**All openclaw commands must use:** `sudo -u clawbot bash -l -c '...'`

**Git repos:**
- `lpasqualin/clawbot-runtime` (private) — ops, scripts, runtime
- `lpasqualin/clawbot-dashboard` (public) — dashboard
- `lpasqualin/obsidian-vault` (private)
- Push both together via `push-all.sh`

**Codex re-auth pattern:**
1. SSH tunnel from Windows: `ssh -L 1455:localhost:1455 leo-paz@100.86.220.59`
2. On MS-01: `sudo -u clawbot bash -l -c 'openclaw configure'`
3. Follow OAuth URL in browser via tunnel
4. Test: `sudo -u clawbot bash -l -c 'openclaw agent --agent main --message "reply with just: ok" --model openai-codex/gpt-5.5 --timeout 30 2>/dev/null'`
5. Never edit `llmFallbacks` directly in `openclaw.json` — use `openclaw models fallbacks add/remove/clear`

**ACL pattern (permanent fix):**
```bash
sudo setfacl -Rm u:leo-paz:rwx /path/to/dir/
sudo setfacl -Rm d:u:leo-paz:rwx /path/to/dir/
sudo setfacl -m m::rwx /path/to/dir/  # if still blocked
```
Applied permanently to `/home/clawbot/.openclaw/` full tree.

---

## Dashboard

**Viewer:** `http://100.86.220.59:8181/dashboard.html`

Write ownership — one writer per domain, no exceptions:
- `sync_dashboard.py` → tasks, calendar — every 15min
- `sync_activity.py` → activity_feed — every 15min+2
- `sync_projects.py` → projects[] cards — every 15min+5
- `health-check.sh` → tool_status, clawbot_status, todays_cost_usd — every 30min
- `apply_judgment_patch.py` → judgment fields only — on morning brief

**HARD RULE:** No agent writes dashboard.json directly. ClawBot judgment flows through:
`patches/dashboard_judgment_patch.json → apply_judgment_patch.py → dashboard.json`

**ClawBot judgment fields (only these):**
- `today.primary_focus`, `secondary_focus`, `must_do`, `should_do`, `avoid_today`, `risk_flags`, `agent_note`
- `needs_leo[]`
- `projects[].health`, `blocked`, `blocker`, `current_focus`, `next_action`
- `weekly_metrics.projects_moved`, `bbs_outreach_count`, `followups_sent`

**Never touch (script-owned):** tasks, calendar, tool_status, activity_feed, clawbot_status, projects[].tasks, tasks_open, tasks_done

**Morning brief write pattern:**
1. Read dashboard.json
2. Generate brief and deliver to Discord/Telegram
3. Write dashboard_judgment_patch.json to patches/
4. Run: `python3 /home/leo-paz/Dashboard/scripts/apply_judgment_patch.py`
5. If apply fails, warn but do not retry

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
- Source registry: `/home/clawbot/.openclaw/workspace/config/intelligence_sources.json`
- Output: `/home/clawbot/.openclaw/workspace/intelligence/daily/YYYY-MM-DD.json`

**Oracle Intelligence Digest:** 7:30am daily
- Classifies: AI_SIGNAL / BBS_OPPORTUNITY / CLAWBOT_RELEVANT / STRATEGY / NOISE
- Digest written to: `/home/clawbot/.openclaw/workspace/intelligence/daily/YYYY-MM-DD.digest.md`
- Delivers to Discord `#morning`

**Brief boundary rules:**
- Morning Brief: dashboard.json only — no newsletters, no market scan
- Oracle daily digest: newsletters + AI signals — no crypto/markets
- Belfort scan: crypto/markets/macro only
- Weekly Oracle: synthesis — reads daily digests, minimal fresh search

---

## Todoist Structure

5 projects (at limit). Sections auto-map to dashboard cards via sync_projects.py.
Add a section in Todoist → card appears on next 15min sync. No script edits needed.

Projects and IDs:
- Ventures (`6g6qrJfXm4w3fpFV`) → VENTURES column
- ClawBot & AI (`6g6x3p95vH4GPMcH`) → AI & PROJECTS column
- Career (`6g6qrJmm6hF2hqh7`) → CAREER column
- Personal (`6g6qrJrwQ2HMrWQp`) → FAMILY & HOUSEHOLD column
- Home (`6g6qrJwvp24Q36Hh`) → not on dashboard
- Inbox drop zone: `6g4xCqG2fQXfxXFj`

---

## Decisions

- **Memory architecture:** File-based primary. pgvector parked until dataset justifies it.
- **Memory write authority:** ClawBot only. Specialists produce outputs; ClawBot extracts and writes durable facts.
- **Memory scope:** MEMORY.md stores decisions, rules, constraints, and infrastructure facts only. No tasks, no open loops, no operational state, no model config.
- **Project context model:** Three layers — (A) MEMORY.md global context, (B) Obsidian project depth, (C) task-specific handoff packets.
- **System ownership:** MEMORY.md + Todoist + Calendar + Dashboard → ClawBot. CRM → Vito. Obsidian → Leo/Oracle/Tron. Code/infra → Tron. Content → Harley. Trading journal → Belfort.
- **Dashboard:** Scripts own data writes. ClawBot owns judgment only via patch workflow. No agent writes dashboard.json directly.
- **External actions:** Posting, emailing, messaging, creating accounts — explicit approval required every time.
- **Model spend governance:** Using paid external providers = spending money = requires Leo's explicit approval per session. OpenRouter weekly budget cap in place.
- **Capability model:** Shared read, owned write. Domain ownership determines judgment and write authority.
- **Operating cadence:** Morning Brief → day capture → Evening Review. Daily: ClawBot. 3x/week: Vito. Weekly: Oracle, Tron, Harley, Belfort.
- **Brief delivery:** Discord morning brief channel (`1492262253255200838`). Telegram for direct DMs.
- **OpenClaw:** Swappable orchestrator. All durable value built as external services.
- **Priority balance:** Revenue motion (BBS) is the top priority, but infrastructure, positioning, and tooling that directly enables BBS are valid parallel work. A working website, case studies, and outreach tools are not distractions — they are prerequisites. Vanity architecture with no client impact is the only thing that gets deprioritized.
- **Siftwise:** Active. Phase 1 AI Intelligence Layer in progress. Personal knowledge vault / ingestion layer may later feed it.
- **Agent OS:** Active as ClawBot governance layer only. Not a standalone product.
- **openclaw doctor --fix:** Never run.
- **llmFallbacks:** Never edit directly in openclaw.json — use openclaw models fallbacks commands only.

---

## Proposal / Approval Pattern

For governance workflows, ClawBot separates proposal from execution.

Proposal jobs may inspect system state and generate suggested actions, but must not perform destructive writes or deletions.

Execution requires explicit Leo approval.

Pattern:
1. Generate proposal with stable IDs.
2. Deliver proposal to Leo.
3. Leo approves specific IDs.
4. Executor applies only approved IDs.
5. Executor logs what changed.

Applies to: weekly-memory-governor, weekly-system-hygiene-audit, future cleanup or governance jobs.