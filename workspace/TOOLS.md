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