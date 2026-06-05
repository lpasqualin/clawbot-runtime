# AUTOMATION & SYSTEMS Context — Leo's Current State
*Updated 2026-06-04*

## ClawBot Infrastructure Scripts (ACTIVE)
All scripts at /home/clawbot/scripts/ and /home/leo-paz/Dashboard/scripts/.

**Health check:** /home/clawbot/scripts/health-check.sh (v4)
- Runs every 30min via system-health-check cron job
- Checks: openclaw.service, ollama.service, obsidian-api.service, ollama models, obsidian REST, cron failures, GOG auth (calendar + gmail), disk usage
- GOG auth uses: /home/clawbot/gogcli/bin/gog with GOG_KEYRING_PASSWORD=ClawBot123 GOG_ACCOUNT=leo.pasqua88@gmail.com
- Consecutive failure tracking: state file at /home/clawbot/.openclaw/health-check-state.json
- 1 failure = WARN, 2+ consecutive = CRITICAL
- Delivers to #clawbot-config (Discord channel 1492265696850346086)

**Dashboard sync scripts (leo-paz user, every 15min):**
- sync_dashboard.py — tasks, calendar, OpenClaw version, Attio connectivity, Gmail connectivity
- sync_activity.py — activity_feed from cron run logs (dynamic JOB_MAP from jobs.json)
- sync_projects.py — project cards from Todoist sections

**File retention:** /home/clawbot/scripts/file-retention.sh
- Runs Monday 3am via weekly-file-retention cron
- Archives: staging files (>30d), proposals/session logs (>45d), judgment patches (>30d)
- Archive dir: /home/clawbot/.openclaw/workspace/memory/archive/

**Judgment patch workflow:**
- apply_judgment_patch.py at /home/clawbot/.openclaw/scripts/ and /home/leo-paz/Dashboard/scripts/
- Morning brief → patches/dashboard_judgment_patch.json → apply_judgment_patch.py → MEMORY.md
- Patch format: {date, source, patches:[{id, section, action, note}]}
- IDs: JP-YYYY-MM-DD-NNN
- Actions: append, update, close

## GOG CLI (Google Workspace)
- Binary: /home/clawbot/gogcli/bin/gog (symlinked at /usr/local/bin/gog)
- Accounts: leo.pasqua88@gmail.com (Gmail, Calendar, Contacts) and leo.clawbot.1@gmail.com (full Workspace)
- GOG_KEYRING_PASSWORD=ClawBot123 required for clawbot user
- Calendar command: gog calendar events -a leo.pasqua88@gmail.com --from today --to today --json
- Gmail command: gog gmail search "query" -a leo.pasqua88@gmail.com --max N --json

## Todoist Integration
- API key via TODOIST_API_KEY env var from /etc/openclaw.env
- 5 projects: Ventures, ClawBot & AI, Career, Personal, Home
- Sections auto-map to dashboard cards via slugify() — add section in Todoist, card appears on next 15min sync
- Project IDs in MEMORY.md

## Telegram
- Bot: @L30_Clawbot
- Leo's ID: 8376304007 / @L30_paz

## n8n
- Mentioned in sessions but not currently a primary active system — may be superseded by ClawBot direct integrations

## Key System Rules
- Write ownership in dashboard: one writer per domain, no exceptions
- All clawbot commands: sudo -u clawbot bash -l -c '[command]'
- Secrets in /etc/openclaw.env (root-owned, 600 perms, injected via systemd)
- After file ops in /home/clawbot/.openclaw/: sudo setfacl -R -m u:leo-paz:rX /home/clawbot/.openclaw/
- Default ACLs now set on .openclaw/ — new files inherit leo-paz:rX automatically

## ClawBot Behavior Notes
- Dashboard write ownership is strict — ClawBot never writes dashboard.json directly
- GOG binary is /home/clawbot/gogcli/bin/gog — NOT /usr/local/bin/gog (symlink may be stale)
- health-check.sh v4 is current — has consecutive failure tracking and Gmail ping
- Cron jobs.json is source of truth; changes must be synced to SQLite via Node.js saveCronJobsStore
