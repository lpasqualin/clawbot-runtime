# TOOLS.md — Local Environment Reference

This file is a cheat sheet for this specific machine and setup.
No doctrine, no routing rules, no strategy — just environment facts.

---

## Machine

| Field | Value |
|---|---|
| Model | Venus Series (MS-01) |
| OS | Ubuntu 24.04.4 LTS |
| Hostname | `leo-paz-MS-10-Venus` |
| CPU | 6-core Intel |
| RAM | 32 GB |
| Storage | NVMe SSD |
| Timezone | America/New_York |
| Display | X11 (Wayland disabled) |

## Network

| Name | Address |
|---|---|
| Tailscale — Venus | 100.86.220.59 |
| Tailscale — Windows laptop | 100.78.65.107 |
| RustDesk ID | 379632253 |
| RustDesk relay | Self-hosted Docker (hbbs / hbbr) — currently DOWN |

## Users

| User | Notes |
|---|---|
| `leo-paz` | UID 1000, passwordless sudo, docker + ollama groups. Primary human user. |
| `clawbot` | Service account. Runs OpenClaw and all ClawBot services. |

## Paths

### Binaries
| Binary | Path |
|---|---|
| openclaw | `/home/clawbot/.npm-global/bin/openclaw` |
| gog CLI | `/home/clawbot/gogcli/bin/gog` (symlinked: `/usr/local/bin/gog`) |
| ollama | System PATH via `ollama.service` |

### Config and Data
| Item | Path |
|---|---|
| OpenClaw config | `/home/clawbot/.openclaw/openclaw.json` |
| OpenClaw workspace | `/home/clawbot/.openclaw/workspace/` |
| Skill overrides | `/home/clawbot/.openclaw/workspace/skills/<name>/SKILL.md` |
| Secrets (root-owned) | `/etc/openclaw.env` |
| Failover notify script | `/home/clawbot/.openclaw/failover-notify.sh` |
| Obsidian vault | `/home/leo-paz/obsidian-vault` |
| npm globals root | `/home/clawbot/.npm-global/` |

## Services

| Service | User | Port | Status |
|---|---|---|---|
| `openclaw.service` | clawbot | 18789 | Running |
| `ollama.service` | — | 11434 | Running |
| `postgresql` | — | 5432 | not monitored — known non-critical |
| `clawbot-memory.service` | leo-paz | 9001 | Disabled (parked) |
| `rustdesk.service` | — | — | not monitored — known non-critical |
| Docker: `hbbs` / `hbbr` | — | — | Down (non-blocking) |

## Git

| `clawbot-runtime` | git at `/home/clawbot/.openclaw` | push as clawbot user | live mirror of runtime |

## Ollama Models

`qwen3:14b` (general) · `gemma4:e4b` (fast) · `qwen2.5-coder:14b` (coding) · `nomic-embed-text` (embed)

Installed but NOT in fallback chain:
- `deepseek-r1:14b` — no tool support; unusable in agent mode
- `devstral:24b` — OOM: needs 33 GiB, machine has 31 GiB

## Accounts

### Google OAuth
| Account | Access |
|---|---|
| leo.clawbot.1@gmail.com | Full Workspace: Drive, Docs, Sheets, Gmail, Calendar, Contacts |
| leo.pasqua88@gmail.com | Gmail, Calendar, Contacts only (read+write). No Drive/Docs/Sheets. |

### Telegram
| Field | Value |
|---|---|
| Bot | @L30_Clawbot |
| Leo's user ID | 8376304007 |
| Leo's handle | @L30_paz |

## Obsidian

| Field | Value |
|---|---|
| Vault path | `/home/leo-paz/obsidian-vault` |
| REST API | `https://localhost:27124` (self-signed cert) |
| API key | Stored in `/etc/openclaw.env` |
| Access note | Requires Obsidian running in active GUI session (RustDesk/X11) |
| Folders | `00 Inbox/` · `01 Daily/` · `02 Projects/` (BBS, Siftwise, Agent OS, ClawBot) · `03 Operations/` (Admin, Finance, Health, Home) · `04 Assets/` (About-Leo, Digital Assets) · `90 - Archive/` (removed) |

---

## Registered Skills (ClawBot Workspace)

**HARD RULE: Always check registered skills before attempting any tool call, bash command, or API call. If a skill exists for the task — use it. No exceptions.**

| Skill | Purpose |
|---|---|
| `gog-v2` | Gmail, Calendar, Drive, Contacts, Sheets, Docs via `gog` CLI. Primary tool for all Google Workspace operations. |
| `discord-chat` | Send messages and search history in Discord channels. Use for all Discord delivery. |
| `todoist` | Read and write Todoist tasks, projects, due dates. |
| `obsidian` | Read and write Obsidian vault notes via REST API. |

### Google Account Routing
| Task | Account |
|---|---|
| Gmail read/send, Calendar, Contacts | `leo.pasqua88@gmail.com` |
| Drive, Docs, Sheets | `leo.clawbot.1@gmail.com` |

Set `GOG_ACCOUNT=<account>` before all gog commands.

---

## Fleet Skills (Delegate via Specialist Agents)

These skills live in specialist workspaces. ClawBot does not call them directly — delegate the task to the owning agent.

### Vito (Sales / Outreach)
| Skill | Purpose |
|---|---|
| `attio` / `attio-cli` | CRM — contacts, pipelines, records |
| `apollo` | Lead prospecting |
| `imap-smtp-email` | Email send/receive (fallback only — use gog-v2 first) |
| `linkedin` | LinkedIn outreach |
| `brw-cold-outreach-sequence` | Cold outreach sequences |
| `coordinate-meeting` | Meeting scheduling |
| `lead-scorer` | Score inbound leads |
| `norman-manage-clients` | Client management |
| `markdown-exporter` | Export content to markdown |
| `office-document-editor` | Edit Word/Excel docs |

### Oracle (Research / Intelligence)
| Skill | Purpose |
|---|---|
| `ddg-web-search` | Web search via DuckDuckGo |
| `web-search-plus` | Enhanced web search |
| `deep-research-pro` | Deep multi-source research |
| `market-research` | Market and competitive research |
| `competitor-analysis` | Competitor profiling |
| `trend-watcher` | Trend monitoring |
| `rss-reader` | RSS feed monitoring |
| `ai-news-oracle` | AI news aggregation |
| `macro-monitor` | Macro economic monitoring |
| `fact-check` | Fact verification |
| `summarize-pro` | Content summarization |
| `data-analysis` | Data analysis |

### Tron (Dev / Automation)
| Skill | Purpose |
|---|---|
| `git-essentials` | Git operations |
| `docker` | Docker container management |
| `sysadmin-handbook` | System administration |
| `ssh-essentials` | SSH operations |
| `api-tester` | API testing |
| `webhook-send` | Send webhook payloads |
| `deep-debugging` | Debug complex issues |
| `security-audit-toolkit` | Security audits |
| `website` | Website operations |
| `playwright-mcp` | Browser automation |

### Belfort (Trading / Capital)
| Skill | Purpose |
|---|---|
| `crypto-market-data` | Crypto prices and data |
| `finance-radar` | Financial market monitoring |
| `stock-analysis` | Stock analysis |
| `market-news` | Market news aggregation |
| `market-sentiment-pulse` | Sentiment analysis |
| `fred-navigator` | Federal Reserve economic data |
| `coingecko` | Crypto data via CoinGecko |
| `polymarket-odds` | Prediction market odds |
| `sec-watcher` | SEC filing monitoring |

### Harley (Content / Social)
| Skill | Purpose |
|---|---|
| `copywriting-pro` | Copywriting |
| `ai-social-media-content` | Social media content generation |
| `tweet-writer` | Twitter/X content |
| `tiktok-growth` | TikTok strategy |
| `content-repurposing-engine` | Repurpose content across formats |
| `email-marketing-2` | Email marketing copy |
| `social-media-scheduler` | Schedule social posts |
| `landing-page-roast` | Landing page critique |
| `lead-magnets` | Lead magnet creation |

## Operations Cheat Sheet

### Always run as clawbot
```bash
sudo -u clawbot bash -l -c '<command>'
```

### OpenClaw binary (not in system PATH)
```bash
OC=/home/clawbot/.npm-global/bin/openclaw
```

### File transfer from Windows laptop → MS-01 → execute
```bash
# From Windows (PowerShell)
scp "C:\Users\leopa\Documents\Dev and Tech\Code Projects\<file>" leo-paz@100.86.220.59:/tmp/

# Then on MS-01
sudo cp /tmp/<file> /home/clawbot/.openclaw/<dest>/
sudo chown clawbot:clawbot /home/clawbot/.openclaw/<dest>/<file>
```

### OpenClaw — common commands
```bash
# Status
sudo -u clawbot bash -l -c 'OC=/home/clawbot/.npm-global/bin/openclaw && $OC status'

# Skills
sudo -u clawbot bash -l -c '$OC skills list'
sudo -u clawbot bash -l -c '$OC skills list --eligible'

# Cron jobs
sudo -u clawbot bash -l -c '$OC cron list'
sudo -u clawbot bash -l -c '$OC cron runs --limit 5'
sudo -u clawbot bash -l -c '$OC cron runs --id <job-id> --limit 3 --json'
sudo -u clawbot bash -l -c '$OC cron enable <job-id>'
sudo -u clawbot bash -l -c '$OC cron disable <job-id>'

# Agents
sudo -u clawbot bash -l -c '$OC agents list'

# Send a message (scripted / shell)
sudo -u clawbot bash -l -c '$OC message send --channel discord --target channel:<id> --message "text"'

# Config patch (use inline Python, NOT heredocs, NOT openclaw doctor --fix)
sudo -u clawbot bash -l -c 'python3 /tmp/patch_script.py'

# Restart service
sudo systemctl restart openclaw.service
sudo journalctl -u openclaw.service -n 50 --no-pager
```

### Git ops (always as clawbot)
```bash
sudo -u clawbot bash -l -c 'cd /home/clawbot/.openclaw && git add -A && git commit -m "message" && git push'
```

### Permissions (reset after every openclaw restart)
```bash
# .openclaw resets to 700/clawbot:clawbot on restart
# Durable fix: openclaw-perms.service handles ACL restoration
# Manual reset if needed:
sudo chmod 750 /home/clawbot/.openclaw
sudo chown clawbot:clawbot /home/clawbot/.openclaw
```

### Codex binary (recreate after any OC upgrade)
```bash
CODEX_DIR="/home/clawbot/.openclaw/extensions/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl"
sudo mkdir -p "$CODEX_DIR/codex"
sudo ln -sf "$CODEX_DIR/bin/codex" "$CODEX_DIR/codex/codex"
sudo chown -h clawbot:clawbot "$CODEX_DIR/codex/codex"
```

### When in doubt — discover flags
```bash
sudo -u clawbot bash -l -c '$OC <subcommand> --help'
# e.g. $OC cron --help, $OC skills --help, $OC message --help
```

# ACL fix — leo-paz write access to .openclaw (survives restarts via openclaw-perms.service)
sudo setfacl -m u:leo-paz:rwx /home/clawbot/.openclaw/workspace
sudo setfacl -m u:leo-paz:rw /home/clawbot/.openclaw/workspace/<file>
``` 