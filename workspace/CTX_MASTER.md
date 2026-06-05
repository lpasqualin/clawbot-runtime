# ClawBot Master Context — Leo Pasqualin
*Last updated: 2026-06-04*

---

## Who Leo Is
Leo Pasqualin is building an AI-powered personal operating system (ClawBot) while running Beacon Bridge Strategies (BBS), a government contracting and digital transformation consultancy. He is in execution phase: primary goal is BBS client acquisition and revenue, with ClawBot as the intelligence/automation layer supporting that goal. He is also developing Siftwise (AI file organization) and Khalixos (autonomous data intelligence) as longer-term product bets.

**Operating philosophy:** Revenue motion first. Execution over planning. Ship, don't architect.

---

## Active Projects (Priority Order)

1. **BBS / Beacon Bridge Strategies** — Government contracting + digital transformation consulting. PRIMARY revenue source. Positioned as "business systems consultancy." bbstrats.com. Client acquisition is the #1 priority before any additional infrastructure work. Vito handles CRM/pipeline reviews (Mon/Wed/Fri 9am).

2. **ClawBot / OpenClaw Infrastructure** — Leo's AI Chief of Staff system running on MS-01. OpenClaw 2026.6.1. 13 active cron jobs. Currently on temporary model (gemini-2.5-flash) due to Codex OAuth issue. Dashboard live at http://100.86.220.59:8181. Memory in MEMORY.md (file-based, pgvector parked).

3. **Siftwise** — AI file organization platform, Phase 1 in progress. Active, not parked.

4. **Khalixos** — Autonomous data intelligence system. In development.

5. **Agent OS** — ClawBot governance framework (Phases A-H). Core Loop Proof Gate active. NOT a standalone product.

---

## Current System State (MS-01)

**Machine:** MS-01 (leo-paz-MS-10-Venus), Tailscale 100.86.220.59, Ubuntu 24.04
**OpenClaw:** 2026.6.1, running as clawbot user on port 18789/18791/18792
**Primary model:** openrouter/google/gemini-2.5-flash (TEMPORARY — Codex OAuth missing model.request scope)
**Codex binary:** Fixed via OPENCLAW_CODEX_APP_SERVER_BIN in /etc/openclaw.env
**Fallback chain:** openai-codex/gpt-5.4-mini → gemini-2.5-flash → kimi-k2.6 → qwen3:14b → gemma4:e4b → openrouter/auto
**Dashboard:** Synced every 15min (sync_dashboard.py, sync_activity.py, sync_projects.py as leo-paz)
**Health check:** Every 30min (health-check.sh v4 as clawbot) → #clawbot-config
**Repos:** clawbot-runtime at lpasqualin/clawbot-runtime (pushed). Dashboard at lpasqualin/clawbot-dashboard (commit done, NOT YET PUSHED — awaiting GitHub repo creation).

**Active agents:** ClawBot (main), Vito, Oracle, Tron
**Disabled:** Belfort (weekly capital review cron disabled)
**Config only:** Harley (no workspace dir yet)

---

## Current Blockers / Open Items

- **Codex OAuth re-auth needed** — openai-codex/gpt-5.5 still shows 401 (missing model.request scope). Re-auth requires interactive browser session via SSH tunnel (ssh -L 1455:localhost:1455) + openclaw configure on ProDesk desktop session.
- **Dashboard GitHub repo** — lpasqualin/clawbot-dashboard needs to be created on GitHub, then: cd /home/leo-paz/Dashboard && git push -u origin main
- **BBS client acquisition** — no active retainer clients documented. This is the top priority.
- **Harley agent** — config exists, workspace dir not yet created.

---

## Business Context
- **BBS:** Government contracting + digital transformation. Federal work, CRM implementation, automation architecture. Mirage/Vintage Hardwood (building materials) is a past employer/client network. JPB and Vector Marketing are background context.
- **Leo's positioning:** Business Systems Architect — "I design and implement the systems that run modern businesses." This is DECIDED — don't re-litigate.
- **Revenue rule:** Every ClawBot capability must serve BBS revenue or Leo's product development. No architecture for architecture's sake.

---

## Recurring Preferences & Hard Rules

**ClawBot must:**
- Run all openclaw commands as: sudo -u clawbot bash -l -c '[command]'
- Run setfacl after file operations: sudo setfacl -R -m u:leo-paz:rX /home/clawbot/.openclaw/
- Never write dashboard.json directly — judgment flows through patches/dashboard_judgment_patch.json
- Never run openclaw doctor --fix (corrupts Codex OAuth routes)
- Never edit llmFallbacks directly in openclaw.json
- Never touch jobs.json or MEMORY.md without explicit instruction
- Always back up files before editing (jobs.json.bak, etc.)
- Use /home/clawbot/gogcli/bin/gog (not /usr/local/bin/gog) for GOG commands
- Sync cron changes: jobs.json → SQLite via Node.js saveCronJobsStore script

**Leo's work style:**
- Prefers execution over planning — get to the action fast
- Wants actual content, not just summaries — include the real code/frameworks/decisions
- Step-by-step with verification at each stage for infrastructure work
- Fail-stop and report on unexpected findings before proceeding
- Back up before destructive operations

---

## Agent Domain Ownership
- **ClawBot (main):** Chief of Staff, orchestration, MEMORY.md, dashboard judgment, morning/evening briefs
- **Vito:** Sales, CRM, BBS pipeline, Attio, outreach
- **Oracle:** Research, intelligence digest, weekly synthesis
- **Tron:** Dev, automation, infrastructure audits
- **Belfort:** Markets, crypto, capital (DISABLED)
- **Harley:** Content, growth, Farah content business (not yet active)

---

## Key File Paths
- OpenClaw config: /home/clawbot/.openclaw/openclaw.json
- MEMORY.md: /home/clawbot/.openclaw/workspace/MEMORY.md
- Jobs: /home/clawbot/.openclaw/cron/jobs.json
- Dashboard: /home/leo-paz/Dashboard/dashboard.json
- Dashboard scripts: /home/leo-paz/Dashboard/scripts/
- ClawBot scripts: /home/clawbot/scripts/
- Health state: /home/clawbot/.openclaw/health-check-state.json
- Secrets: /etc/openclaw.env (root-owned, 600)
- Obsidian vault: /home/leo-paz/obsidian-vault
- GOG binary: /home/clawbot/gogcli/bin/gog
