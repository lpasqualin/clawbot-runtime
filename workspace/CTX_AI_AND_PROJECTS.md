# AI & PROJECTS Context — Leo's Current State
*Updated 2026-06-04*

## ClawBot / OpenClaw Infrastructure (PRIMARY ACTIVE SYSTEM)
Leo runs ClawBot as his personal AI Chief of Staff on MS-01 (leo-paz-MS-10-Venus, Tailscale 100.86.220.59). OpenClaw 2026.6.1 is the orchestration layer.

**Current model status:**
- Primary (TEMPORARY): openrouter/google/gemini-2.5-flash
- Reason: openai-codex OAuth broken on 6.1 — missing model.request scope — awaiting re-auth
- Codex binary fix applied: OPENCLAW_CODEX_APP_SERVER_BIN set in /etc/openclaw.env
- Fallback chain: openai-codex/gpt-5.4-mini → gemini-2.5-flash → kimi-k2.6 → ollama/qwen3:14b → ollama/gemma4:e4b → openrouter/auto

**Cron jobs (13 active):**
- Daily: morning brief (7am), intelligence digest (7:30am), midday check-in (12pm), evening review (9pm), memory staging (11:45pm)
- Weekly: Oracle brief (Sun 9am), Tron review (Sun 10am), system hygiene (Mon 10am), memory governor (Sun 9pm), Vito pipeline (Mon/Wed/Fri 9am), file retention (Mon 3am)
- Every 30min: system health check → #clawbot-config
- Belfort: DISABLED

**Dashboard:** Live at http://100.86.220.59:8181 — scripts own data, ClawBot owns judgment via patch workflow only. sync_dashboard.py, sync_activity.py, sync_projects.py run every 15min as leo-paz user.

**Memory:** File-based primary. MEMORY.md at /home/clawbot/.openclaw/workspace/MEMORY.md. pgvector PARKED. Judgment patches via apply_judgment_patch.py.

**Agents:**
- main (ClawBot) — Chief of Staff / Orchestrator
- vito — Sales/CRM/Pipeline (enabled, Mon/Wed/Fri)
- oracle — Research/Intelligence (weekly brief + daily digest)
- tron — Dev/Infrastructure (weekly review)
- belfort — Markets/Capital (DISABLED — workspace exists, no dir yet)
- harley — Content/Growth (config only, no dir yet)

## Siftwise
AI-powered file organization platform. Phase 1 AI Intelligence Layer in progress. NOT parked — active development. May feed into ClawBot's personal knowledge vault.

## Khalixos
Autonomous data intelligence system. In development alongside Siftwise.

## Agent OS
Active as ClawBot governance framework (Phases A-H roadmap). Core Loop Proof Gate blocks expansion phases. NOT a standalone product — it's the governance layer for ClawBot.

## Obsidian Vault
Running as obsidian-api.service on port 27124 (self-signed cert). Vault at /home/leo-paz/obsidian-vault. REST API active via xvfb-obsidian.service.

## Key Architecture Decisions
- OpenClaw is a SWAPPABLE orchestrator — all durable value is in external services
- clawbot-runtime repo: git initialized at /home/clawbot/.openclaw — push pattern: sudo -u clawbot bash -l -c 'cd /home/clawbot/.openclaw && git add -A && git commit -m "msg" && git push'
- Dashboard repo: /home/leo-paz/Dashboard — git initialized, commit done, NOT YET PUSHED (awaiting lpasqualin/clawbot-dashboard creation on GitHub)
- NEVER edit llmFallbacks directly in openclaw.json — use openclaw models fallbacks commands
- NEVER run openclaw doctor --fix — corrupts openai-codex OAuth routes

## ClawBot Behavior Notes
- ClawBot does NOT write dashboard.json directly — judgment flows through patches/dashboard_judgment_patch.json → apply_judgment_patch.py
- Morning brief writes judgment patches via apply_judgment_patch.py at /home/clawbot/.openclaw/scripts/
- sudo -u clawbot bash -l -c is the required pattern for all openclaw commands
- setfacl -R -m u:leo-paz:rX /home/clawbot/.openclaw/ must run after file operations in that directory
